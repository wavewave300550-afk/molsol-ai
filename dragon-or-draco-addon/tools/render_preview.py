#!/usr/bin/env python3
"""
Software preview of the add-on's real files (geometry + texture + animations).

    python3 tools/render_preview.py            -> docs/preview/*.png
    python3 tools/render_preview.py --quick    -> scratch views + measurements only

Everything drawn here is read back from the resource pack: bone pivots / rest rotations,
per-face UVs, the emissive alpha convention and the keyframes of the animation files
(sampled with tools/kinematics.py).  The flame jet is drawn from red_dragon_fire.geo.json
with additive blending.  This is a preview of the files, not a capture from the game.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kinematics as K  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "dragon_or_draco")
OUT = os.path.join(ROOT, "docs", "preview")

GEO = K.load_json(os.path.join(RP, "models", "entity", "red_dragon.geo.json"))["minecraft:geometry"][0]
FGEO = K.load_json(os.path.join(RP, "models", "entity", "red_dragon_fire.geo.json"))["minecraft:geometry"][0]
TEX = np.array(Image.open(os.path.join(RP, "textures", "entity", "red_dragon.png")).convert("RGBA"))
FTEX = np.array(Image.open(os.path.join(RP, "textures", "entity", "red_dragon_fire.png")).convert("RGBA"))


def load_anims():
    anims = {}
    d = os.path.join(RP, "animations")
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.endswith(".json"):
                anims.update(K.load_json(os.path.join(d, f))["animations"])
    return anims


ANIMS = load_anims()


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def background(w, h):
    y = np.linspace(0, 1, h)[:, None, None]
    top = np.array([0.10, 0.06, 0.07])
    bot = np.array([0.30, 0.13, 0.08])
    img = top * (1 - y) + bot * y
    return np.broadcast_to(img, (h, w, 3)).copy()


def draw(cam, pose=None, fire=False, bg=None, ground=True):
    W, H = cam.size
    img = background(W, H) if bg is None else bg
    zbuf = np.full((H, W), np.inf)
    if ground:
        # simple ground grid (1 block squares) at y = 0
        g = []
        for i in range(-12, 13):
            g.append(((i * 16, 0, -12 * 16), (i * 16, 0, 12 * 16)))
            g.append(((-12 * 16, 0, i * 16), (12 * 16, 0, i * 16)))
    faces = list(K.world_faces(GEO, pose))
    img, zbuf, glow, _ = K.render(faces, TEX, cam, image=img, zbuf=zbuf)
    if fire:
        ff = list(K.world_faces(FGEO, pose))
        _, _, fglow, _ = K.render(ff, FTEX, cam, image=img.copy(), zbuf=zbuf.copy(), additive_bones=("fire_",))
        glow = glow + fglow
        img = img + fglow
    pil = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    if glow.max() > 0:
        gl = Image.fromarray((np.clip(glow, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
        pil = Image.fromarray(np.clip(np.array(pil).astype(int) + (np.array(gl).astype(int) * 0.8).astype(int), 0, 255)
                              .astype(np.uint8))
    if ground:
        d = ImageDraw.Draw(pil, "RGBA")
        for a, b in g:
            P = cam.project(np.array([a, b], dtype=float))
            if (P[:, 2] > 1).all():
                d.line([(P[0, 0], P[0, 1]), (P[1, 0], P[1, 1])], fill=(255, 200, 160, 28), width=1)
    return pil


def pose_of(names, t, env=None, weights=None):
    env = dict(env or {})
    env.setdefault("q.life_time", t)
    anims = [ANIMS[n] for n in names]
    weights = weights or [1.0] * len(names)
    return K.sample_pose(anims, weights, [t] * len(names), env)


def extents(pose=None):
    pts = np.concatenate([P for _, _, P, _, _ in K.world_faces(GEO, pose)])
    return pts.min(0), pts.max(0)


def measurements(pose=None, label="rest"):
    lo, hi = extents(pose)
    print(f"[{label}] x {lo[0]:.0f}..{hi[0]:.0f}  y {lo[1]:.0f}..{hi[1]:.0f}  z {lo[2]:.0f}..{hi[2]:.0f}  ->"
          f" length {(hi[2] - lo[2]) / 16:.1f} b, width {(hi[0] - lo[0]) / 16:.1f} b, height {(hi[1] - lo[1]) / 16:.1f} b")
    return lo, hi


def foot_report(pose=None):
    mats = K.bone_matrices(GEO, pose)
    for b in GEO["bones"]:
        if b["name"].startswith("foot_"):
            ys = []
            for c in b.get("cubes", []):
                lo, hi = K.cube_corners(c)
                for q in K.face_quads(lo, hi).values():
                    for p in q:
                        ys.append((mats[b["name"]] @ np.array(list(p) + [1]))[1])
            print(f"  {b['name']}: min y {min(ys):.1f}")


def quick():
    os.makedirs(OUT, exist_ok=True)
    measurements(None, "rest (wings spread)")
    foot_report(None)
    views = [("front", 0, 8), ("left", 90, 8), ("three_quarter", 140, 22), ("top", 180, 80)]
    tiles = []
    for name, yaw, pitch in views:
        cam = K.Camera((0, 48, 10), yaw, pitch, scale=1.55, size=(720, 480))
        tiles.append(draw(cam))
    sheet = Image.new("RGB", (1440, 960))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 2) * 720, (i // 2) * 480))
    p = os.path.join(OUT, "_quick_rest.png")
    sheet.save(p)
    print("wrote", p)


if __name__ == "__main__":
    if "--quick" in sys.argv:
        quick()
    else:
        import preview_sheets  # noqa: F401  (full sheets, written once animations exist)
        preview_sheets.main()
