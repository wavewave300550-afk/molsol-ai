#!/usr/bin/env python3
"""
Secondary art for Extra Super Boss: Da Vinci.

  RP models/entity/brass_gear.geo.json + textures/entity/brass_gear.png        (gear projectile)
  RP models/entity/vitruvian_sigil.geo.json + textures/entity/vitruvian_sigil.png (ground sigil)
  RP textures/items/esb_da_vinci_blueprint.png, esb_leonardo_codex.png        (32 px icons)
  RP textures/particle/esb_fx.png                                              (particle atlas)
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "extra_super_boss")


def save_json(rel, data):
    p = os.path.join(RP, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=1)


def save_png(rel, im):
    p = os.path.join(RP, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    im.save(p)


# ------------------------------------------------------------------------------ brass gear projectile

def gear():
    """A flat brass saw-gear (10 units across) that spins around Y.  Faces: 'up'/'down' carry the
    gear art, the thin sides are brass.  Tilted 18 degrees so it reads from the side too."""
    S = 64  # texture is 64 x 64: gear face 0..40, side strip below
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = 20
    # teeth + rim (glowing amber edge: alpha < 255 is emissive)
    for k in range(12):
        a = k * math.pi / 6
        pts = []
        for da, r in ((-0.13, 15), (-0.09, 19.5), (0.09, 19.5), (0.13, 15)):
            pts.append((c + math.cos(a + da) * r, c + math.sin(a + da) * r))
        d.polygon(pts, fill=(255, 196, 92, 170))
    d.ellipse([c - 16, c - 16, c + 16, c + 16], fill=(196, 146, 62, 255))
    d.ellipse([c - 13, c - 13, c + 13, c + 13], fill=(160, 112, 44, 255))
    for k in range(6):
        a = k * math.pi / 3
        d.line([c, c, c + math.cos(a) * 13, c + math.sin(a) * 13], fill=(232, 192, 110, 255), width=3)
    for k in range(6):
        a = k * math.pi / 3 + math.pi / 6
        x, y = c + math.cos(a) * 8, c + math.sin(a) * 8
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(70, 46, 18, 255))
    d.ellipse([c - 5, c - 5, c + 5, c + 5], fill=(236, 200, 120, 255))
    d.ellipse([c - 2, c - 2, c + 2, c + 2], fill=(255, 238, 170, 40))  # glowing hub
    # side strip (brass)
    d.rectangle([0, 44, 63, 47], fill=(200, 150, 64, 255))
    d.line([0, 44, 63, 44], fill=(245, 210, 130, 255))
    save_png("textures/entity/brass_gear.png", im)
    face = {"up": {"uv": [0, 0], "uv_size": [40, 40]}, "down": {"uv": [0, 0], "uv_size": [40, 40]}}
    side = {f: {"uv": [0, 44], "uv_size": [40, 4]} for f in ("north", "south", "east", "west")}
    geo = {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {"identifier": "geometry.esb.brass_gear", "texture_width": 64, "texture_height": 64,
                            "visible_bounds_width": 2, "visible_bounds_height": 2, "visible_bounds_offset": [0, 0.5, 0]},
            "bones": [
                {"name": "root", "pivot": [0, 4, 0]},
                {"name": "tilt", "parent": "root", "pivot": [0, 4, 0], "rotation": [18, 0, 0]},
                {"name": "spin", "parent": "tilt", "pivot": [0, 4, 0],
                 "cubes": [{"origin": [-5, 3.5, -5], "size": [10, 1, 10], "uv": {**face, **side}}],
                 "locators": {"loc_gear": [0, 4, 0]}},
            ],
        }],
    }
    save_json("models/entity/brass_gear.geo.json", geo)


# ------------------------------------------------------------------------------ vitruvian sigil

def sigil():
    """Additive ground sigil: outer ring (circle, square, measuring ticks, mirror script) and an inner
    disc with the Vitruvian figure.  Black = invisible under the additive material."""
    W, H = 512, 256
    S = 2  # draw at 2x and downsample for clean lines
    big = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    gold = (255, 205, 110, 255)
    soft = (200, 140, 60, 255)
    dim = (120, 80, 30, 255)

    # outer art in [0..256)
    cx, cy, R = 128 * S, 128 * S, 122 * S
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=gold, width=4 * S)
    d.ellipse([cx - R * 0.93, cy - R * 0.93, cx + R * 0.93, cy + R * 0.93], outline=soft, width=2 * S)
    for k in range(72):
        a = k * math.pi / 36
        r0 = R * (0.86 if k % 6 == 0 else 0.90)
        d.line([cx + math.cos(a) * r0, cy + math.sin(a) * r0, cx + math.cos(a) * R * 0.93, cy + math.sin(a) * R * 0.93],
               fill=soft, width=S * (2 if k % 6 == 0 else 1))
    # the square of the Vitruvian proportions
    q = R * 0.70
    d.rectangle([cx - q, cy - q, cx + q, cy + q], outline=gold, width=3 * S)
    d.line([cx - q, cy - q, cx + q, cy + q], fill=dim, width=S)
    d.line([cx - q, cy + q, cx + q, cy - q], fill=dim, width=S)
    # mirror-script glyph bands between ring and square
    rng = np.random.default_rng(5)
    for k in range(40):
        a = k * math.pi / 20 + 0.04
        for j in range(3):
            r = R * (0.80 - j * 0.02)
            L = rng.uniform(0.02, 0.06)
            d.arc([cx - r, cy - r, cx + r, cy + r], math.degrees(a), math.degrees(a + L), fill=soft, width=S)
    # inner art in [256..512): Vitruvian figure in a circle
    cx2 = 384 * S
    r2 = 116 * S
    d.ellipse([cx2 - r2, cy - r2, cx2 + r2, cy + r2], outline=gold, width=4 * S)
    d.rectangle([cx2 - r2 * 0.74, cy - r2 * 0.62, cx2 + r2 * 0.74, cy + r2 * 0.86], outline=soft, width=2 * S)
    lw = 5 * S
    hy = cy - r2 * 0.62
    d.ellipse([cx2 - 14 * S, hy - 10 * S, cx2 + 14 * S, hy + 18 * S], outline=gold, width=lw)
    d.line([cx2, hy + 18 * S, cx2, cy + r2 * 0.15], fill=gold, width=lw)
    sh = hy + 34 * S
    d.line([cx2 - r2 * 0.74, sh, cx2 + r2 * 0.74, sh], fill=gold, width=lw)  # arms level
    d.line([cx2, sh, cx2 - r2 * 0.80, sh - r2 * 0.40], fill=soft, width=lw - S)  # arms raised
    d.line([cx2, sh, cx2 + r2 * 0.80, sh - r2 * 0.40], fill=soft, width=lw - S)
    hip = cy + r2 * 0.15
    d.line([cx2, hip, cx2 - 16 * S, cy + r2 * 0.86], fill=gold, width=lw)  # legs together
    d.line([cx2, hip, cx2 + 16 * S, cy + r2 * 0.86], fill=gold, width=lw)
    d.line([cx2, hip, cx2 - r2 * 0.55, cy + r2 * 0.80], fill=soft, width=lw - S)  # legs apart
    d.line([cx2, hip, cx2 + r2 * 0.55, cy + r2 * 0.80], fill=soft, width=lw - S)
    im = big.resize((W, H), Image.LANCZOS)
    a = np.array(im).astype(float)
    a[..., :3] *= a[..., 3:4] / 255.0  # premultiply: transparent areas are black
    a[..., 3] = np.where(a[..., 3] > 0, 255, 0)
    save_png("textures/entity/vitruvian_sigil.png", Image.fromarray(a.astype(np.uint8), "RGBA"))
    geo = {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {"identifier": "geometry.esb.vitruvian_sigil", "texture_width": W, "texture_height": H,
                            "visible_bounds_width": 30, "visible_bounds_height": 3, "visible_bounds_offset": [0, 0.5, 0]},
            "bones": [
                {"name": "root", "pivot": [0, 0, 0]},
                {"name": "outer", "parent": "root", "pivot": [0, 0.2, 0],
                 "cubes": [{"origin": [-32, 0.2, -32], "size": [64, 0, 64],
                            "uv": {"up": {"uv": [0, 0], "uv_size": [256, 256]}, "down": {"uv": [0, 0], "uv_size": [256, 256]}}}]},
                {"name": "inner", "parent": "root", "pivot": [0, 0.35, 0],
                 "cubes": [{"origin": [-18, 0.35, -18], "size": [36, 0, 36],
                            "uv": {"up": {"uv": [256, 0], "uv_size": [256, 256]}, "down": {"uv": [256, 0], "uv_size": [256, 256]}}}]},
            ],
        }],
    }
    save_json("models/entity/vitruvian_sigil.geo.json", geo)


# ------------------------------------------------------------------------------ item icons (32 px)

def icon_blueprint():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # rolled parchment, diagonal
    d.polygon([(5, 22), (22, 5), (27, 10), (10, 27)], fill=(220, 198, 150, 255))
    d.line([(5, 22), (22, 5)], fill=(245, 230, 190, 255), width=2)
    d.line([(10, 27), (27, 10)], fill=(170, 140, 95, 255), width=2)
    for k in range(3):
        d.line([(9 + k * 3, 21 - k * 3), (14 + k * 3, 26 - k * 3)], fill=(90, 60, 30, 255), width=1)
    d.ellipse([2, 19, 10, 27], fill=(200, 175, 125, 255), outline=(120, 90, 55, 255))
    d.ellipse([22, 3, 30, 11], fill=(200, 175, 125, 255), outline=(120, 90, 55, 255))
    # gold ribbon and red wax seal with a compass mark
    d.line([(10, 13), (20, 23)], fill=(214, 170, 80, 255), width=3)
    d.ellipse([11, 12, 21, 22], fill=(150, 28, 36, 255), outline=(95, 15, 22, 255))
    d.line([(16, 14), (14, 20)], fill=(240, 200, 110, 255), width=1)
    d.line([(16, 14), (18, 20)], fill=(240, 200, 110, 255), width=1)
    d.point((16, 14), fill=(255, 235, 170, 255))
    save_png("textures/items/esb_da_vinci_blueprint.png", im)


def icon_codex():
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([6, 4, 26, 28], fill=(110, 40, 30, 255), outline=(60, 20, 15, 255))  # cover
    d.rectangle([24, 6, 27, 27], fill=(235, 220, 185, 255))  # page edges
    for y in range(7, 27, 2):
        d.line([(24, y), (27, y)], fill=(200, 180, 140, 255))
    d.rectangle([6, 4, 9, 28], fill=(80, 28, 20, 255))  # spine
    d.rectangle([11, 7, 22, 25], outline=(210, 165, 80, 255))
    cx, cy = 16.5, 16
    d.ellipse([cx - 4.5, cy - 4.5, cx + 4.5, cy + 4.5], outline=(235, 195, 105, 255))
    for k in range(8):
        a = k * math.pi / 4
        L = 6 if k % 2 == 0 else 3.5
        d.line([cx, cy, cx + math.sin(a) * L, cy - math.cos(a) * L], fill=(240, 205, 120, 255))
    # brass clasp
    d.rectangle([22, 14, 26, 18], fill=(200, 150, 64, 255), outline=(120, 85, 30, 255))
    save_png("textures/items/esb_leonardo_codex.png", im)


# ------------------------------------------------------------------------------ particle atlas (64 x 64)

def particle_atlas():
    S = 4
    big = Image.new("RGBA", (64 * S, 64 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    W = (255, 255, 255, 255)

    def cell(i, j):
        return i * 16 * S, j * 16 * S

    # (0,0) four-point spark
    x, y = cell(0, 0)
    c = 8 * S
    d.polygon([(x + c, y + 1 * S), (x + c + 1.5 * S, y + c - 1.5 * S), (x + 15 * S, y + c), (x + c + 1.5 * S, y + c + 1.5 * S),
               (x + c, y + 15 * S), (x + c - 1.5 * S, y + c + 1.5 * S), (x + 1 * S, y + c), (x + c - 1.5 * S, y + c - 1.5 * S)], fill=W)
    # (1,0) soft glow dot
    x, y = cell(1, 0)
    for r in range(7, 0, -1):
        a = int(255 * (1 - r / 8) ** 1.5)
        d.ellipse([x + (8 - r) * S, y + (8 - r) * S, x + (8 + r) * S, y + (8 + r) * S], fill=(255, 255, 255, a))
    # (2,0) tiny gear
    x, y = cell(2, 0)
    for k in range(8):
        a = k * math.pi / 4
        d.ellipse([x + c + math.cos(a) * 5.5 * S - 1.6 * S, y + c + math.sin(a) * 5.5 * S - 1.6 * S,
                   x + c + math.cos(a) * 5.5 * S + 1.6 * S, y + c + math.sin(a) * 5.5 * S + 1.6 * S], fill=W)
    d.ellipse([x + 3 * S, y + 3 * S, x + 13 * S, y + 13 * S], fill=W)
    d.ellipse([x + 6.5 * S, y + 6.5 * S, x + 9.5 * S, y + 9.5 * S], fill=(0, 0, 0, 0))
    # (3,0) page with writing (keeps its own colours)
    x, y = cell(3, 0)
    d.rectangle([x + 2 * S, y + 1 * S, x + 14 * S, y + 15 * S], fill=(232, 214, 170, 255), outline=(150, 120, 80, 255))
    for k in range(5):
        d.line([x + 4 * S, y + (4 + k * 2.2) * S, x + 12 * S, y + (4 + k * 2.2) * S], fill=(110, 75, 40, 255), width=S // 2)
    # (0,1) smoke puff
    x, y = cell(0, 1)
    rng = np.random.default_rng(3)
    for _ in range(9):
        px, py, r = rng.uniform(5, 11), rng.uniform(5, 11), rng.uniform(2.5, 4.5)
        d.ellipse([x + (px - r) * S, y + (py - r) * S, x + (px + r) * S, y + (py + r) * S], fill=(255, 255, 255, 150))
    # (1,1) ring
    x, y = cell(1, 1)
    d.ellipse([x + 1 * S, y + 1 * S, x + 15 * S, y + 15 * S], outline=W, width=2 * S)
    # (2,1) ink blot
    x, y = cell(2, 1)
    for _ in range(7):
        px, py, r = rng.uniform(5, 11), rng.uniform(5, 11), rng.uniform(1.5, 3.5)
        d.ellipse([x + (px - r) * S, y + (py - r) * S, x + (px + r) * S, y + (py + r) * S], fill=W)
    # (3,1) streak
    x, y = cell(3, 1)
    d.polygon([(x + 7 * S, y), (x + 9 * S, y), (x + 8.6 * S, y + 16 * S), (x + 7.4 * S, y + 16 * S)], fill=W)
    im = big.resize((64, 64), Image.LANCZOS)
    save_png("textures/particle/esb_fx.png", im)


if __name__ == "__main__":
    gear()
    sigil()
    icon_blueprint()
    icon_codex()
    particle_atlas()
    print("art: gear, sigil, icons, particle atlas")
