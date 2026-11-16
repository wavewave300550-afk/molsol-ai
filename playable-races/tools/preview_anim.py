"""Preview a race's model AND animation set straight from its Python modules - no pack build.

    python3 tools/preview_anim.py <race> --out DIR [--variant base] [--clips idle,walk,sprint,jump,attack,hurt]
                                  [--sheet] [--fidgets name,name,...] [--seconds 3]

Writes <race>_<variant>_anim.gif (clips side by side), with --sheet a white-background
turnaround <race>_sheet.png (front / three-quarter / side / back for every variant), and with
--fidgets one GIF per idle behaviour.  The attachable is assembled in memory exactly the way
tools/build.py writes it (same animate list, pre_animation, controllers, Molang
canonicalisation) and played by kit/animrt.py on the vanilla player skeleton, so what you see
is what the pack will contain.  Safe to run in parallel: it never touches packs/ or dist/.
"""
from __future__ import annotations

import argparse
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from PIL import Image  # noqa: E402

from anims import core as acore  # noqa: E402
from anims import life  # noqa: E402
from anim_gifs import CLIPS, HIDE, _label, _warm_input, grid, save_gif  # noqa: E402
from kit import animrt  # noqa: E402
from kit.playersim import DT, FPS, Sim, vanilla_skeleton  # noqa: E402
from kit.render import render, sheet  # noqa: E402
from kit.tex import paint  # noqa: E402

NS = "plrace"


class MemActor:
    """An attachable assembled in memory from models.<race> + anims.<race>."""

    def __init__(self, race: str, variant: str, built=None):
        self.race, self.variant = race, variant
        mod = importlib.import_module(f"models.{race}")
        am = importlib.import_module(f"anims.{race}")
        self.model = built[0] if built else mod.build()
        tv = mod.VARIANT_TEXTURE[variant]
        self.texture = built[1][tv] if built else paint(self.model, mod.materials(), mod.TEXTURES[tv])
        A = built[2] if built else am.anims(self.model)
        files = acore.canon_tree(life.compact(acore.file(A["anims"])))
        anims = {n: animrt.Animation(n, d) for n, d in files["animations"].items()}
        ctrls = acore.canon_tree(life.compact(acore.controller_file(A["controllers"])))["animation_controllers"] if A["controllers"] else {}
        short = {a.name.split(f"animation.{NS}.{race}.")[1]: a.name for a in A["anims"]}
        for cid in A["controllers"]:
            short[cid.split(".")[-1]] = cid
        animate = []
        for nm, cond in A["animate"][variant]:
            if nm not in short:
                raise KeyError(f"{race}/{variant}: animation {nm} missing")
            animate.append(nm if cond is None else {nm: cond})
        desc = acore.canon_tree({"animations": short, "particle_effects": A["particles"],
                                 "scripts": {"pre_animation": A["pre"], "animate": [life.compact(e) for e in animate]}})
        self.rt = animrt.Runtime(desc, anims, ctrls)
        self.animations = anims
        self.names = {bn.lower(): bn for bn in self.model.order}
        self.vars = {}
        self.missing = set()

    def pose(self, sim: Sim, time_of_day: float = 0.3):
        env = sim.env(time_of_day)
        self.vars["attack_time"] = sim.attack_time
        env.v = self.vars
        p = self.rt.step(sim.life, env)
        self.missing |= env.missing
        base = vanilla_skeleton(sim)
        for bn, d in p.ch.items():
            for ch, v in d.items():
                base.add(bn, ch, v)
        return base.for_render(self.names)


def frame(actor, sim, pose, yaw, scale, cy, size, label=None, bg=(255, 255, 255)):
    follow = max(0.0, sim.y * 16.0 - 2.0)
    im = render(actor.model, actor.texture, variant=actor.variant, pose=pose, yaw=yaw, pitch=7, size=size, scale=scale,
                center=(0, cy + follow, 1), ss=2, hide=HIDE, ground=True, bg=bg, bloom=True)
    return _label(im, label) if label else im


def run_clip(actor_args, clip, seconds, scale, cy, size=(240, 290), warmup=5.0):
    script, yaw, label = CLIPS[clip]
    actor = MemActor(*actor_args)
    sim = Sim()
    out = []
    for i in range(-int(warmup * FPS), int(round(seconds * FPS))):
        t = i * DT
        sim.tick(script(t) if i >= 0 else _warm_input(script, clip))
        pose = actor.pose(sim)
        if i >= 0:
            out.append(frame(actor, sim, pose, yaw, scale, cy, size, label))
    if actor.missing:
        print(f"  [{clip}] queries not simulated: {sorted(actor.missing)}")
    return out


def run_named(actor_args, anim_short, seconds, scale, cy, size=(240, 290), label=None):
    """Play one animation (e.g. a fidget or a form loop) on top of the idle stack."""
    actor = MemActor(*actor_args)
    full = f"animation.{NS}.{actor.race}.{anim_short}"
    anim = actor.animations[full]
    sim = Sim()
    out = []
    for i in range(int(2.0 * FPS)):
        sim.tick({})
        actor.pose(sim)
    for i in range(int(round(seconds * FPS))):
        sim.tick({})
        env = sim.env(0.3)
        actor.vars["attack_time"] = 0.0
        env.v = actor.vars
        p = actor.rt.step(sim.life, env)
        anim.apply(i * DT, 1.0, env, p)
        base = vanilla_skeleton(sim)
        for bn, d in p.ch.items():
            for ch, v in d.items():
                base.add(bn, ch, v)
        out.append(frame(actor, sim, base.for_render(actor.names), 32, scale, cy, size, label or anim_short))
    return out


def turnaround(race, scale, cy, out_path):
    mod = importlib.import_module(f"models.{race}")
    m = mod.build()
    texs = {tv: paint(m, mod.materials(), params) for tv, params in mod.TEXTURES.items()}
    imgs, labels = [], []
    for v in mod.VARIANTS:
        tex = texs[mod.VARIANT_TEXTURE[v]]
        views = [(0, "front"), (35, "three-quarter"), (90, "side"), (180, "back")] if v == "base" else [(35, "three-quarter")]
        for yaw, name in views:
            imgs.append(render(m, tex, variant=v, yaw=yaw, pitch=8, size=(300, 380), scale=scale, center=(0, cy, 0),
                               ss=2, hide=HIDE, ground=True, bg=(255, 255, 255), bloom=True))
            labels.append(f"{v} - {name}")
    sheet(imgs, 4, labels, title=f"{race} - turnaround and forms (white background)", bg=(255, 255, 255)).save(out_path)
    nb, nc = m.stats("base")
    print(f"{race}: base form {nb} bones / {nc} cubes, atlas {m.tex_w}x{m.tex_h} -> {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("race")
    ap.add_argument("--out", required=True)
    ap.add_argument("--variant", default="base")
    ap.add_argument("--clips", default="idle,walk,sprint,jump")
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--scale", type=float, default=5.0)
    ap.add_argument("--cy", type=float, default=17.0)
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--fidgets", default="", help="comma list of animation short names to play one by one")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.sheet:
        turnaround(a.race, a.scale, a.cy, os.path.join(a.out, f"{a.race}_sheet.png"))
    if a.clips:
        cols = [run_clip((a.race, a.variant), c, a.seconds, a.scale, a.cy) for c in a.clips.split(",") if c]
        if cols:
            path = os.path.join(a.out, f"{a.race}_{a.variant}_anim.gif")
            save_gif(grid(cols, f"{a.race} ({a.variant})"), path)
            print("->", path)
    for nm in [x for x in a.fidgets.split(",") if x]:
        frames = run_named((a.race, a.variant), nm, a.seconds, a.scale, a.cy)
        path = os.path.join(a.out, f"{a.race}_{nm}.gif")
        save_gif(frames, path)
        print("->", path)


if __name__ == "__main__":
    main()
