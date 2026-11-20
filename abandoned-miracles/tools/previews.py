"""
Render model turnarounds, action poses and short animation previews.

    python3 tools/previews.py [boss ...]

Images are produced by the project's own software renderer (tools/kit/render.py)
from the SAME geometry, textures and animation data that ship in the packs.
They are previews of the assets, not screenshots of the game.
"""
from __future__ import annotations

import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from kit import render                    # noqa: E402
from kit.anim import combine              # noqa: E402

OUT = os.path.join(ROOT, "docs", "previews")


def build(key: str) -> None:
    mod = importlib.import_module(f"bosses.{key}")
    spec = mod.PREVIEW
    model = importlib.import_module(f"bosses.{key}.model").build()
    model.paint()
    T = json.load(open(os.path.join(ROOT, "shared", f"{key}.timings.json")))
    anims, _, ce = importlib.import_module(f"bosses.{key}.anims").build_all(T)
    by = {a.name.split(".")[-1]: a for a in anims}
    out = os.path.join(OUT, key)
    os.makedirs(out, exist_ok=True)
    lo, hi = model.extent()
    pad = spec.get("pad", 26)
    bounds = (lo - pad, hi + pad)

    def pose(names, t, phase=1, dist=0.0, extra_env=None):
        env = {"q.life_time": 2.0 + t, "q.anim_time": t, "q.modified_distance_moved": dist * 4,      # limb-swing units: four per block
               "q.modified_move_speed": 1.0 if dist else 0.0, "q.body_y_rotation": 0.0,
               "p.abm:phase": phase, "p.abm:variant": 0}
        env.update(extra_env or {})
        env = ce.env(env)
        base = list(spec["base"]) + list(spec.get("base_p2" if phase == 2 else "base_p1", []))
        ps = [by[n].sample(2.0 + t, env) for n in base if n in by]
        ps += [by[n].sample(t, env) for n in names if n in by]
        return combine(*ps)

    hidden1 = spec.get("hidden", [])
    hidden2 = spec.get("hidden_p2", hidden1)
    # turnarounds
    render.turnaround(model, f"{spec['title']} - Phase I", pose([], 0), hidden1, bounds=bounds).save(os.path.join(out, "turnaround_phase1.png"))
    render.turnaround(model, f"{spec['title']} - Phase II", pose([], 0, 2), hidden2, bounds=bounds).save(os.path.join(out, "turnaround_phase2.png"))
    # phase comparison
    a = render.label(render.render(model, pose([], 0), yaw=30, pitch=14, size=(640, 640), bounds=bounds, hidden=hidden1), "Phase I")
    b = render.label(render.render(model, pose([], 0, 2), yaw=30, pitch=14, size=(640, 640), bounds=bounds, hidden=hidden2), "Phase II - " + spec.get("phase2", ""))
    render.sheet([a, b], 2).save(os.path.join(out, "phases.png"))
    # action poses
    ims = []
    for names, t, phase, caption in spec["actions"]:
        ims.append(render.label(render.render(model, pose(names, t, phase), yaw=spec.get("action_yaw", 32), pitch=14, size=(440, 440), bounds=bounds,
                                              hidden=hidden2 if phase == 2 else hidden1, scale_figure=False), caption))
    render.sheet(ims, 4).save(os.path.join(out, "actions.png"))
    # animation previews
    for name, names, t0, t1, phase, speed in spec["gifs"]:
        frames = []
        n = max(2, int((t1 - t0) * 10))
        for i in range(n):
            t = t0 + (t1 - t0) * i / n
            frames.append(render.render(model, pose(names, t, phase, dist=speed * t), yaw=32, pitch=14, size=(380, 380), bounds=bounds,
                                        hidden=hidden2 if phase == 2 else hidden1, scale_figure=False, ss=1))
        frames[0].save(os.path.join(out, f"{name}.gif"), save_all=True, append_images=frames[1:], duration=100, loop=0, optimize=True)
    # demonstration arena (layout preview in flat colours)
    try:
        from kit import iso
        arena = importlib.import_module(f"bosses.{key}.arena").build()
        iso.render(arena).save(os.path.join(out, "arena.png"))
    except Exception as e:                                # noqa: BLE001 - previews must not stop on an arena problem
        print(f"[previews] {key}: arena preview skipped ({e})")
    print(f"[previews] {key}: {len(os.listdir(out))} files in docs/previews/{key}")


if __name__ == "__main__":
    keys = sys.argv[1:] or [k for k in ("vesperra", "cantor", "nomos", "orison")
                            if os.path.exists(os.path.join(HERE, "bosses", k, "__init__.py"))]
    for k in keys:
        build(k)
