#!/usr/bin/env python3
"""
Pose sheets and animated GIFs rendered from the real pack files.

    python3 tools/preview_sheets.py            -> docs/preview/poses.png, docs/preview/anim/*.gif
    python3 tools/preview_sheets.py --sheet    -> only the pose sheet (fast)

Layers are combined the way the client entity does: idle + walk + look + wings layer + action.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kinematics as K  # noqa: E402
import render_preview as R  # noqa: E402
import spec  # noqa: E402

P = "animation.esb.da_vinci."
ANIM_DIR = os.path.join(R.OUT, "anim")


def layered_pose(action=None, t=0.0, phase=1, wings=None, speed=0.0, dist=0.0, life=None):
    env = {"q.modified_move_speed": speed, "q.modified_distance_moved": dist, "q.target_x_rotation": 0,
           "q.target_y_rotation": 0, "q.life_time": life if life is not None else t,
           "q.property('esb:phase')": phase, "q.delta_time": 0.05}
    names, times = [P + "idle", P + "walk"], [env["q.life_time"], 0.0]
    if wings is None:
        wings = "wings_hidden" if phase == 1 else "wings_folded"
    names.append(P + wings)
    times.append(t if wings in ("wings_unfold", "wings_swept") else env["q.life_time"])
    if action:
        names.append(P + action)
        times.append(t)
    anims = [R.ANIMS[n] for n in names]
    return K.sample_pose(anims, [1.0] * len(anims), times, env)


SHEET = [
    ("idle", None, 0.0, 1, None),
    ("intro: kneel", "intro", 0.6, 1, None),
    ("intro: signature pose", "intro", 3.0, 1, None),
    ("slash: wind-up", "slash", 0.27, 1, None),
    ("slash: strike", "slash", 0.45, 1, None),
    ("gear volley: aim", "gear_volley", 1.3, 1, None),
    ("quake: raise", "quake", 0.62, 1, None),
    ("quake: impact", "quake", 0.95, 1, None),
    ("vitruvian", "vitruvian", 1.3, 1, None),
    ("vitruvian: slam", "vitruvian", 2.8, 1, None),
    ("transform: clutch", "transform", 0.9, 2, "wings_unfold"),
    ("transform: burst", "transform", 2.25, 2, "wings_unfold"),
    ("phase 2 idle", None, 0.0, 2, None),
    ("dive: hover", "dive_hover", 0.3, 2, "wings_flap"),
    ("dive: strike", "dive_strike", 0.12, 2, "wings_swept"),
    ("flourish", "flourish", 0.7, 1, None),
    ("death: kneel", "death", 1.6, 1, None),
    ("death: slump", "death", 4.2, 1, None),
]


def sheet(views=((30, 8),), cols=6, size=(300, 380), scale=6.2, name="poses.png"):
    tiles = []
    for label, action, t, phase, wings in SHEET:
        pose = layered_pose(action, t, phase, wings)
        for yaw, pitch in views:
            cam = K.Camera((0, 19, 0), yaw, pitch, scale=scale, size=size)
            img = R.draw(cam, pose)
            ImageDraw.Draw(img).text((8, 6), label, fill=(245, 225, 190), font=R.font(15))
            tiles.append(img)
    rows = (len(tiles) + cols - 1) // cols
    out = Image.new("RGB", (cols * size[0], rows * size[1]))
    for i, tl in enumerate(tiles):
        out.paste(tl, ((i % cols) * size[0], (i // cols) * size[1]))
    p = os.path.join(R.OUT, name)
    out.save(p)
    print("wrote", p)


GIFS = [
    # name, action, phase, wings layer, duration, walk speed
    ("idle", None, 1, None, 3.2, 0.0),
    ("walk", None, 1, None, 1.6, 1.0),
    ("intro", "intro", 1, None, spec.ACTIONS["intro"]["length"], 0.0),
    ("slash", "slash", 1, None, spec.SLASH["length"], 0.0),
    ("gear_volley", "gear_volley", 1, None, spec.ACTIONS["gear_volley"]["length"], 0.0),
    ("quake", "quake", 1, None, spec.ACTIONS["quake"]["length"], 0.0),
    ("vitruvian", "vitruvian", 1, None, spec.ACTIONS["vitruvian"]["length"], 0.0),
    ("transform", "transform", 2, "wings_unfold", spec.ACTIONS["transform"]["length"], 0.0),
    ("dive_rise", "dive_rise", 2, "wings_flap", spec.ACTIONS["dive_rise"]["length"], 0.0),
    ("dive_hover", "dive_hover", 2, "wings_flap", 1.0, 0.0),
    ("dive_strike", "dive_strike", 2, "wings_swept", spec.ACTIONS["dive_strike"]["length"], 0.0),
    ("flourish", "flourish", 1, None, spec.ACTIONS["flourish"]["length"], 0.0),
    ("death", "death", 1, None, spec.ACTIONS["death"]["length"] + 0.4, 0.0),
    ("phase2_walk", None, 2, None, 1.6, 1.0),
]


def flat_bg(size):
    return np.broadcast_to(np.array([0.16, 0.10, 0.09]), (size[1], size[0], 3)).copy()


def gifs(only=None, fps=12, size=(256, 320), scale=5.1):
    os.makedirs(ANIM_DIR, exist_ok=True)
    for name, action, phase, wings, dur, speed in GIFS:
        if only and name not in only:
            continue
        frames = []
        n = max(2, int(round(dur * fps)))
        for i in range(n):
            t = i / fps
            dist = t * 4.0 * speed * 1.4  # ~ modified distance at walking speed
            pose = layered_pose(action, t, phase, wings, speed=speed, dist=dist, life=t + 0.5)
            cam = K.Camera((0, 21, 0), 32, 10, scale=scale, size=size)
            img = R.draw(cam, pose, bg=flat_bg(size), ground=False)
            ImageDraw.Draw(img).text((8, 6), name, fill=(245, 225, 190), font=R.font(14))
            frames.append(img)
        pal = frames[len(frames) // 2].convert("P", palette=Image.ADAPTIVE, colors=128)
        frames = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
        p = os.path.join(ANIM_DIR, f"{name}.gif")
        frames[0].save(p, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0, disposal=2)
        print("wrote", p)


if __name__ == "__main__":
    if "--sheet" in sys.argv:
        sheet()
    elif "--gif" in sys.argv:
        gifs([a for a in sys.argv[2:]] or None)
    else:
        sheet()
        gifs()
