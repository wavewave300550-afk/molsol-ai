"""Animated previews of the shipped race animations (GIF).

    python3 tools/anim_gifs.py                      # all races -> docs/images/anim_<race>.gif
    python3 tools/anim_gifs.py --out DIR --races golem --clips idle,walk --variant base

The attachable exactly as written to packs/PlayableRaces_RP (animate list,
blend conditions, Molang, keyframes, animation controllers) is played by
kit/animrt.py on top of the vanilla player skeleton motion (walk swing, arm bob,
head look, attack swing, sneak - formulas from Mojang's player.animation.json),
driven by a small 20 Hz movement simulation (Java/Bedrock limb-swing model:
modified_move_speed = min(1, 4 * blocks per tick), distance += speed per tick).

The renderer is the same software renderer as previews.py, so what you see is
the shipped geometry + texture + animation data, not a hand-made mock-up.
"""
from __future__ import annotations

import argparse
import glob
import math
import os
import sys
from typing import Callable, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from kit import animrt, ljson, molang  # noqa: E402
from kit.render import render  # noqa: E402
from models import golem, jackalope, salamander  # noqa: E402

RP = os.path.join(ROOT, "packs", "PlayableRaces_RP")
HIDE = ["r_arm_fp", "l_arm_fp"]
MODS = {"salamander": salamander, "golem": golem, "jackalope": jackalope}


from kit.playersim import DT, FPS, Sim, vanilla_skeleton  # noqa: E402


# ----------------------------------------------------------------------------- scenarios

def clip_idle(t: float) -> dict:
    return {"look_y": 18 * math.sin(t * 0.9), "look_x": 6 * math.sin(t * 0.6 + 1)}


def clip_walk(t: float) -> dict:
    return {"move": 0.86}


def clip_sprint(t: float) -> dict:
    return {"move": 1.0, "sprint": True}


def clip_jump(t: float) -> dict:
    tt = math.fmod(t, 2.0)
    return {"jump": 0.2 <= tt < 0.26}


def clip_turn(t: float) -> dict:
    s = math.sin(t * 2.4)
    return {"move": 0.86, "yaw_rate": 160 * s, "look_y": 38 * math.sin(t * 2.4 + 0.5)}


def clip_attack(t: float) -> dict:
    tt = math.fmod(t, 1.0)
    return {"attack": tt < 0.06}


def clip_hurt(t: float) -> dict:
    tt = math.fmod(t, 1.6)
    return {"hurt": tt < 0.06}


def clip_sneak(t: float) -> dict:
    return {"sneak": True}


CLIPS: Dict[str, tuple] = {   # name -> (input script, camera yaw, label)
    "idle": (clip_idle, 32, "idle"),
    "walk": (clip_walk, 68, "walk"),
    "sprint": (clip_sprint, 68, "sprint"),
    "jump": (clip_jump, 40, "jump + land"),
    "turn": (clip_turn, 20, "walk + turning"),
    "attack": (clip_attack, 35, "melee swing"),
    "hurt": (clip_hurt, 35, "hurt"),
    "sneak": (clip_sneak, 60, "sneak / still"),
}
CAMERA = {  # race -> (scale, center y)
    "salamander": (6.0, 17.0),
    "golem": (4.7, 20.0),
    "jackalope": (6.2, 17.0),
}


# ----------------------------------------------------------------------------- driver

class Actor:
    def __init__(self, race: str, variant: str):
        self.race = race
        self.variant = variant
        mod = MODS[race]
        self.model = mod.build()
        tv = mod.VARIANT_TEXTURE[variant]
        self.texture = Image.open(os.path.join(RP, "textures/plrace/races", race, f"{race}_{tv}.png")).convert("RGBA")
        att = ljson.load(os.path.join(RP, "attachables/plrace", f"form_{race}_{variant}.json"))
        desc = att["minecraft:attachable"]["description"]
        anims = animrt.load_animations(glob.glob(os.path.join(RP, "animations/plrace/*.json")))
        ctrls = animrt.load_controllers(glob.glob(os.path.join(RP, "animation_controllers/plrace/*.json")))
        self.rt = animrt.Runtime(desc, anims, ctrls)
        self.names = {bn.lower(): bn for bn in self.model.order}
        self.vars: Dict[str, float] = {}
        self.missing: set = set()

    def pose(self, sim: Sim, time_of_day: float) -> Dict[str, dict]:
        env = sim.env(time_of_day)
        self.vars["attack_time"] = sim.attack_time      # the player's public variable, read by the attachable
        env.v = self.vars
        p = self.rt.step(sim.life, env)
        self.missing |= env.missing
        base = vanilla_skeleton(sim)
        for bn, d in p.ch.items():
            for ch, v in d.items():
                if ch == "scale":
                    base.add(bn, ch, v)
                else:
                    base.add(bn, ch, v)
        return base.for_render(self.names)


def run_clip(race: str, variant: str, clip: str, seconds: float, size=(220, 270), warmup: float = 6.0,
             time_of_day: float = 0.3, record: bool = True) -> List[Image.Image]:
    script, yaw, label = CLIPS[clip]
    actor = Actor(race, variant)
    sim = Sim(jump_boost=2 if race == "jackalope" else 0)
    scale, cy = CAMERA[race]
    frames = []
    n_warm = int(warmup * FPS)
    n = int(round(seconds * FPS))
    for i in range(-n_warm, n):
        t = i * DT
        inp = script(t) if i >= 0 else _warm_input(script, clip)
        sim.tick(inp)
        pose = actor.pose(sim, time_of_day)
        if i < 0 or not record:
            continue
        follow = max(0.0, sim.y * 16.0 - 2.0)
        im = render(actor.model, actor.texture, variant=variant, pose=pose, yaw=yaw, pitch=7, size=size, scale=scale,
                    center=(0, cy + follow, 1), ss=2, hide=HIDE, ground=False, bg=(236, 234, 230), bloom=True,
                    backdrop=_ground(sim, yaw, scale, cy + follow, size))
        frames.append(_label(im, label))
    if actor.missing:
        print(f"  [{race}/{variant}/{clip}] queries not simulated: {sorted(actor.missing)}")
    return frames


FIDGETS = {
    "salamander": [("fidget_taste", "tastes the air"), ("fidget_shake", "head shake"), ("fidget_tail", "admires its flower"),
                   ("fidget_stretch", "stretch & yawn")],
    "golem": [("fidget_settle", "stones re-seat"), ("fidget_crack", "neck grind"), ("fidget_core", "core flare"),
              ("fidget_inspect", "inspects a fist")],
    "jackalope": [("fidget_groom", "ear wash"), ("fidget_sentinel", "sentinel"), ("fidget_thump", "warning thump"),
                  ("fidget_stretch", "stretch & shake")],
}


def run_fidget(race: str, variant: str, name: str, label: str, period: float, size=(220, 270)) -> List[Image.Image]:
    """One idle behaviour on loop (the fidget controller is replaced by a timed trigger)."""
    actor = Actor(race, variant)
    length = actor.rt.animations[f"animation.plrace.{race}.{name}"].length
    t0 = 300.0
    actor.rt.entries = [(nm, c) for nm, c in actor.rt.entries if nm != "fidget"]
    actor.rt.entries.append((name, f"math.mod(q.life_time - {t0}, {period:.3f}) < {length:.3f}"))
    sim = Sim()
    sim.life = t0 - 1.0
    scale, cy = CAMERA[race]
    frames = []
    for i in range(-20, int(round(period * FPS))):
        sim.tick({})
        pose = actor.pose(sim, 0.3)
        if i < 0:
            continue
        im = render(actor.model, actor.texture, variant=variant, pose=pose, yaw=32, pitch=7, size=size, scale=scale,
                    center=(0, cy, 1), ss=2, hide=HIDE, ground=False, bg=(236, 234, 230), bloom=True,
                    backdrop=_ground(sim, 32, scale, cy, size))
        frames.append(_label(im, label))
    return frames


def _warm_input(script: Callable, clip: str) -> dict:
    # settle into the clip's steady state (moving clips keep moving, others stand still)
    inp = script(0.0)
    return {k: v for k, v in inp.items() if k in ("move", "sprint", "sneak", "look_x", "look_y")}


def _ground(sim: Sim, yaw: float, scale: float, cy: float, size) -> Callable:
    """Ground line at the true ground height (y = 0) with ticks that scroll with ground speed, and a contact shadow."""
    def draw(img: Image.Image, ss: int) -> None:
        d = ImageDraw.Draw(img)
        W, H = img.size
        gy = H / 2 + cy * scale * ss * math.cos(math.radians(7))
        d.line([(8 * ss, gy), (W - 8 * ss, gy)], fill=(200, 197, 190), width=ss)
        side = math.sin(math.radians(yaw))
        off = (sim.dist / 4.0 * 16 * scale * ss) % (24 * ss)
        for k in range(-2, W // (24 * ss) + 3):
            x = k * 24 * ss - off * side
            d.line([(x, gy), (x - 4 * ss, gy + 4 * ss)], fill=(208, 205, 198), width=ss)
        h = sim.y * 16 * scale * ss
        rw = max(8.0 * ss, (40 * scale / 6) * ss - h * 0.06)
        d.ellipse([W / 2 - rw, gy - 3 * ss, W / 2 + rw, gy + 3 * ss], fill=(214, 211, 204))
    return draw


def _label(im: Image.Image, label: str) -> Image.Image:
    im = im.convert("RGB")
    ImageDraw.Draw(im).text((8, 6), label, fill=(60, 60, 66))
    return im


def save_gif(frames: List[Image.Image], path: str, fps: int = FPS) -> None:
    pal = frames[len(frames) // 2].quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    q[0].save(path, save_all=True, append_images=q[1:], duration=int(1000 / fps), loop=0, optimize=True, disposal=1)


def grid(cols: List[List[Image.Image]], title: str = "") -> List[Image.Image]:
    n = min(len(c) for c in cols)
    w, h = cols[0][0].size
    th = 22 if title else 0
    out = []
    for i in range(n):
        im = Image.new("RGB", (w * len(cols) + 6 * (len(cols) - 1), h + th), (245, 244, 241))
        if title:
            ImageDraw.Draw(im).text((8, 5), title, fill=(30, 30, 34))
        for k, c in enumerate(cols):
            im.paste(c[i], (k * (w + 6), th))
        out.append(im)
    return out


TITLES = {"salamander": "001 Aberrant Flora Salamander", "golem": "002 Runic Titan Golem", "jackalope": "003 Blood Moon Jackalope"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "images"))
    ap.add_argument("--races", default="salamander,golem,jackalope")
    ap.add_argument("--clips", default="idle,walk,sprint,jump")
    ap.add_argument("--variant", default="base")
    ap.add_argument("--seconds", type=float, default=4.0)
    ap.add_argument("--name", default="anim_{race}.gif")
    ap.add_argument("--fidgets", action="store_true", help="render the idle behaviours instead (fidgets_<race>.gif)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    if args.fidgets:
        for race in args.races.split(","):
            actor = Actor(race, args.variant)
            period = max(actor.rt.animations[f"animation.plrace.{race}.{nm}"].length for nm, _ in FIDGETS[race]) + 0.6
            cols = []
            for nm, label in FIDGETS[race]:
                print(f"{race}: {nm}")
                cols.append(run_fidget(race, args.variant, nm, label, period))
            frames = grid(cols, f"{TITLES[race]} - idle behaviours (played when standing still)")
            path = os.path.join(args.out, f"fidgets_{race}.gif")
            save_gif(frames, path)
            print("  ->", os.path.relpath(path, ROOT), f"{os.path.getsize(path) // 1024} KB")
        return
    for race in args.races.split(","):
        cols = []
        for clip in args.clips.split(","):
            print(f"{race}: {clip}")
            cols.append(run_clip(race, args.variant, clip, args.seconds))
        frames = grid(cols, f"{TITLES[race]} - animation preview (shipped animation data, 20 fps)")
        path = os.path.join(args.out, args.name.format(race=race, variant=args.variant))
        save_gif(frames, path)
        print("  ->", os.path.relpath(path, ROOT), f"{os.path.getsize(path) // 1024} KB")


if __name__ == "__main__":
    main()
