#!/usr/bin/env python3
"""
Software preview of the add-on's real files (geometry + texture + animations).

    python3 tools/render_preview.py --quick     -> docs/preview/_quick.png (rest pose, 4 views)

Everything drawn is read back from the resource pack (bone pivots, per-face UVs, emissive alpha,
animation keyframes sampled with tools/kinematics.py).  It is a preview of the files, not a
capture from the game.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kinematics as K  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "extra_super_boss")
OUT = os.path.join(ROOT, "docs", "preview")


def load_geo(name):
    return K.load_json(os.path.join(RP, "models", "entity", f"{name}.geo.json"))["minecraft:geometry"][0]


def load_tex(name):
    return np.array(Image.open(os.path.join(RP, "textures", "entity", f"{name}.png")).convert("RGBA"))


GEO = load_geo("da_vinci")
TEX = load_tex("da_vinci")


def load_anims():
    anims = {}
    d = os.path.join(RP, "animations")
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith(".json"):
                anims.update(K.load_json(os.path.join(d, f))["animations"])
    return anims


ANIMS = load_anims()


def font(size, bold=True):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def background(w, h):
    """Dark sepia vignette like the reference art."""
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx - w / 2) / (w * 0.6), (yy - h * 0.45) / (h * 0.6))
    inner = np.array([0.36, 0.24, 0.20])
    outer = np.array([0.06, 0.04, 0.04])
    t = np.clip(r, 0, 1)[..., None]
    return inner * (1 - t) + outer * t


def draw(cam, pose=None, bg=None, ground=True, extra=()):
    """extra: list of (geo, tex, pose, additive) drawn into the same z-buffer."""
    W, H = cam.size
    img = background(W, H) if bg is None else bg
    zbuf = np.full((H, W), np.inf)
    faces = list(K.world_faces(GEO, pose))
    img, zbuf, glow, _ = K.render(faces, TEX, cam, image=img, zbuf=zbuf)
    for geo, tex, epose, additive in extra:
        ff = list(K.world_faces(geo, epose))
        if additive:
            _, _, eg, _ = K.render(ff, tex, cam, image=img.copy(), zbuf=zbuf.copy(), additive_bones=("",))
            glow = glow + eg
            img = img + eg
        else:
            img, zbuf, eg, _ = K.render(ff, tex, cam, image=img, zbuf=zbuf)
            glow = glow + eg
    pil = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    if glow.max() > 0:
        gl = Image.fromarray((np.clip(glow, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))
        pil = Image.fromarray(np.clip(np.array(pil).astype(int) + (np.array(gl).astype(int) * 0.9).astype(int), 0, 255)
                              .astype(np.uint8))
    if ground:
        d = ImageDraw.Draw(pil, "RGBA")
        for i in range(-6, 7):
            for a, b in (((i * 16, 0, -96), (i * 16, 0, 96)), ((-96, 0, i * 16), (96, 0, i * 16))):
                P = cam.project(np.array([a, b], dtype=float))
                d.line([(P[0, 0], P[0, 1]), (P[1, 0], P[1, 1])], fill=(255, 220, 170, 26), width=1)
    return pil


def pose_of(names, t, env=None, weights=None):
    env = dict(env or {})
    env.setdefault("q.life_time", t)
    anims = [ANIMS[n] for n in names]
    weights = weights or [1.0] * len(names)
    return K.sample_pose(anims, weights, [t] * len(names), env)


def extents(pose=None, hidden=()):
    pts = np.concatenate([P for _, _, P, _, _ in K.world_faces(GEO, pose, hidden)])
    return pts.min(0), pts.max(0)


def quick(pose=None, name="_quick.png", views=None, size=(520, 680), scale=7.5, target=(0, 19, 0)):
    os.makedirs(OUT, exist_ok=True)
    views = views or [("front", 0, 4), ("three_quarter", 35, 8), ("left side", 90, 4), ("back", 180, 6)]
    tiles = []
    for label, yaw, pitch in views:
        cam = K.Camera(target, yaw, pitch, scale=scale, size=size)
        t = draw(cam, pose)
        ImageDraw.Draw(t).text((12, 10), label, fill=(240, 220, 190), font=font(18))
        tiles.append(t)
    sheet = Image.new("RGB", (size[0] * len(tiles), size[1]))
    for i, t in enumerate(tiles):
        sheet.paste(t, (i * size[0], 0))
    p = os.path.join(OUT, name)
    sheet.save(p)
    print("wrote", p)
    return p


if __name__ == "__main__":
    lo, hi = extents(None, hidden=("wing_l", "wing_l_mid", "wing_l_tip", "wing_r", "wing_r_mid", "wing_r_tip"))
    print(f"rest bounds (no wings): x {lo[0]:.1f}..{hi[0]:.1f}  y {lo[1]:.1f}..{hi[1]:.1f}  z {lo[2]:.1f}..{hi[2]:.1f}")
    if "--face" in sys.argv:
        quick(None, "_face.png", [("face", 0, 0), ("face 3/4", 30, 0)], size=(420, 420), scale=34, target=(0, 32, 0))
    else:
        quick()
