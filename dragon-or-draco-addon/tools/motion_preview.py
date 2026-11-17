#!/usr/bin/env python3
"""
Motion previews rendered from the add-on's REAL baked files (geometry + texture + animation JSON).

    python3 tools/motion_preview.py                  -> docs/preview/anim/<name>.gif (all clips)
    python3 tools/motion_preview.py walk_loop run_loop
    python3 tools/motion_preview.py --reel           -> also docs/preview/showreel.mp4 (ffmpeg)

Each GIF shows four views (front / side / back / three-quarter).  For locomotion the ground grid
scrolls at the clip's nominal travel speed, so planted feet must look glued to the grid.
Layers are composed exactly like the animation controllers do (absolute state clip + additive
overlays), sampling keyframes with Bedrock's catmull-rom (tools/kinematics.py).
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kinematics as K  # noqa: E402
import render_preview as R  # noqa: E402

P = "animation.dod.red_dragon."
OUT = os.path.join(R.OUT, "anim")
SPEC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview_spec.json")
VIEWS = [("front", 0, 8), ("side", 90, 6), ("back", 180, 10), ("3/4", 135, 20)]
TW, TH = 300, 190
FPS = 12


def anims():
    return K.load_json(os.path.join(R.RP, "animations", "red_dragon.animation.json"))["animations"]


def grid_lines(cam, offset_z, size=10):
    lines = []
    for i in range(-size, size + 1):
        z = i * 16 + (offset_z % 16)
        lines.append(((-size * 16, 0, z), (size * 16, 0, z)))
        lines.append(((i * 16, 0, -size * 16 + offset_z % 16), (i * 16, 0, size * 16 + offset_z % 16)))
    return lines


def draw_view(cam, pose, fire, ground_off):
    W, H = cam.size
    img = R.background(W, H)
    zbuf = np.full((H, W), np.inf)
    faces = list(K.world_faces(R.GEO, pose))
    img, zbuf, glow, _ = K.render(faces, R.TEX, cam, image=img, zbuf=zbuf)
    if fire:
        ff = list(K.world_faces(R.FGEO, pose))
        _, _, fg, _ = K.render(ff, R.FTEX, cam, image=img.copy(), zbuf=zbuf.copy(), additive_bones=("fire_",))
        img = img + fg
        glow = glow + fg
    pil = Image.fromarray((np.clip(img + glow * 0.35, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(pil, "RGBA")
    for a, b in grid_lines(cam, ground_off):
        S = cam.project(np.array([a, b], float))
        if (S[:, 2] > 1).all():
            d.line([(S[0, 0], S[0, 1]), (S[1, 0], S[1, 1])], fill=(255, 210, 170, 40), width=1)
    return pil


def render_spec(spec):
    A = anims()
    name = spec["name"]
    layers = spec["layers"]  # [[anim_short_name, weight], ...]
    length = spec.get("length") or max(A[P + l]["animation_length"] for l, _ in layers)
    frames = max(2, int(round(length * FPS)))
    speed = spec.get("speed", 0.0)  # blocks / s of ground travel (grid scroll)
    env0 = spec.get("env", {})
    out = []
    for f in range(frames):
        t = f / FPS
        env = dict(env0)
        env["q.life_time"] = t
        pose = K.sample_pose([A[P + l] for l, _ in layers], [w for _, w in layers], [t] * len(layers), env)
        sheet = Image.new("RGB", (TW * 2, TH * 2 + 26), (14, 9, 10))
        for i, (vn, yaw, pitch) in enumerate(VIEWS):
            cam = K.Camera(spec.get("target", (0, 46, 6)), yaw, pitch, scale=spec.get("scale", 0.9), size=(TW, TH))
            tile = draw_view(cam, pose, spec.get("fire", False), speed * 16 * t)
            ImageDraw.Draw(tile).text((6, 4), vn, fill=(230, 200, 180), font=R.font(12))
            sheet.paste(tile, ((i % 2) * TW, 26 + (i // 2) * TH))
        dr = ImageDraw.Draw(sheet)
        dr.text((8, 5), f"{spec['title']}   t={t:4.2f}s", fill=(255, 205, 87), font=R.font(15))
        out.append(sheet)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{name}.gif")
    pal = [fr.convert("P", palette=Image.ADAPTIVE, colors=160) for fr in out]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=int(1000 / FPS), loop=0, optimize=True)
    return name, path, frames


def reel(names):
    """MP4 showreel: three-quarter view, larger, every clip in order (needs ffmpeg)."""
    A = anims()
    specs = {s["name"]: s for s in json.load(open(SPEC_FILE))}
    tmp = os.path.join(R.OUT, ".reel")
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    k = 0
    for n in names:
        s = specs[n]
        layers = s["layers"]
        length = s.get("length") or max(A[P + l]["animation_length"] for l, _ in layers)
        reps = 2 if length < 1.6 else 1
        for f in range(int(round(length * 24)) * reps):
            t = (f / 24) % length
            env = dict(s.get("env", {}))
            env["q.life_time"] = t
            pose = K.sample_pose([A[P + l] for l, _ in layers], [w for _, w in layers], [t] * len(layers), env)
            cam = K.Camera(s.get("target", (0, 46, 6)), 140, 16, scale=s.get("scale", 0.9) * 1.55, size=(960, 540))
            img = draw_view(cam, pose, s.get("fire", False), s.get("speed", 0.0) * 16 * (f / 24))
            ImageDraw.Draw(img).text((18, 14), s["title"], fill=(255, 205, 87), font=R.font(26))
            img.save(os.path.join(tmp, f"{k:05d}.png"))
            k += 1
    mp4 = os.path.join(R.OUT, "showreel.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", os.path.join(tmp, "%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26", "-preset", "veryfast", mp4], check=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    return mp4


def main(argv):
    specs = json.load(open(SPEC_FILE))
    want = [a for a in argv if not a.startswith("--")]
    todo = [s for s in specs if not want or s["name"] in want]
    with Pool(min(4, os.cpu_count() or 1)) as pool:
        for name, path, frames in pool.imap_unordered(render_spec, todo):
            print(f"  {name}: {frames} frames -> {os.path.relpath(path, R.ROOT)}")
    if "--reel" in argv:
        print("showreel:", reel([s["name"] for s in specs if s.get("reel", True)]))


if __name__ == "__main__":
    main(sys.argv[1:])
