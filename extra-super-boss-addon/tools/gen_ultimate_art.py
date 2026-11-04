#!/usr/bin/env python3
"""
Art for the ULTIMATES (every boss has one).

  Da Vinci  "Opus Magnum"         models/entity/da_vinci_halo.geo.json   (giant Vitruvian halo behind his back,
                                  uses textures/entity/vitruvian_sigil.png, additive, only rendered during the ultimate)
  Edison    "Let There Be Light"  models/entity/edison_aura.geo.json + textures/entity/edison_aura.png (sun aura)
                                  models/entity/volt_marker.geo.json + textures/entity/volt_marker.png (strike telegraph)
                                  models/entity/arc_bolt.geo.json + textures/entity/arc_bolt.png (lightning strike)
  The halo / aura geometries repeat the root > body > torso chain of the boss (same pivots), so the boss's own
  animations move them together with the body.
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


def plane_uv(u, v, w, h, faces=("north", "south")):
    return {f: {"uv": [u, v], "uv_size": [w, h]} for f in faces}


def chain(torso_y=18):
    return [{"name": "root", "pivot": [0, 0, 0]},
            {"name": "body", "parent": "root", "pivot": [0, 17, 0]},
            {"name": "torso", "parent": "body", "pivot": [0, torso_y, 0]}]


def geometry(ident, w, h, bones, vb=(6, 6, [0, 2, 0])):
    return {"format_version": "1.12.0", "minecraft:geometry": [{
        "description": {"identifier": ident, "texture_width": w, "texture_height": h,
                        "visible_bounds_width": vb[0], "visible_bounds_height": vb[1], "visible_bounds_offset": vb[2]},
        "bones": bones}]}


# ------------------------------------------------------------------------------ Da Vinci halo

def halo():
    bones = chain() + [
        {"name": "halo", "parent": "torso", "pivot": [0, 30, 7],
         "cubes": [{"origin": [-30, 0, 7], "size": [60, 60, 0], "uv": plane_uv(0, 0, 256, 256)}]},
        {"name": "halo_inner", "parent": "torso", "pivot": [0, 30, 6.5],
         "cubes": [{"origin": [-19, 11, 6.5], "size": [38, 38, 0], "uv": plane_uv(256, 0, 256, 256)}]},
    ]
    save_json("models/entity/da_vinci_halo.geo.json", geometry("geometry.esb.da_vinci_halo", 512, 256, bones, (8, 8, [0, 2, 0])))


# ------------------------------------------------------------------------------ Edison sun aura

def aura():
    W, H = 128, 64
    S = 4
    im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # left: soft glow blob (additive: colour = brightness)
    for r in range(32 * S, 0, -S):
        k = 1 - r / (32 * S)
        col = (int(255 * min(1, 0.25 + k)), int(220 * min(1, 0.15 + k)), int(140 * k), 255)
        d.ellipse([32 * S - r, 32 * S - r, 32 * S + r, 32 * S + r], fill=col)
    # right: starburst rays
    cx, cy = 96 * S, 32 * S
    for k in range(16):
        a = k * math.pi / 8
        L = (30 if k % 2 == 0 else 20) * S
        w = (3 if k % 2 == 0 else 2) * S
        d.line([cx, cy, cx + math.cos(a) * L, cy + math.sin(a) * L], fill=(255, 236, 170, 255), width=w)
    d.ellipse([cx - 7 * S, cy - 7 * S, cx + 7 * S, cy + 7 * S], fill=(255, 250, 230, 255))
    img = np.array(im.resize((W, H), Image.LANCZOS)).astype(float)
    img[..., :3] *= img[..., 3:4] / 255.0
    img[..., 3] = 255
    save_png("textures/entity/edison_aura.png", Image.fromarray(img.astype(np.uint8), "RGBA"))
    glow = {f: {"uv": [0, 0], "uv_size": [64, 64]} for f in ("north", "south", "east", "west", "up", "down")}
    bones = chain() + [
        {"name": "aura", "parent": "torso", "pivot": [0, 24, 0],
         "cubes": [{"origin": [-8, 15, -6], "size": [16, 18, 12], "uv": glow}]},
        {"name": "aura_rays", "parent": "aura", "pivot": [0, 24, 0],
         "cubes": [{"origin": [-20, 4, 0], "size": [40, 40, 0], "uv": plane_uv(64, 0, 64, 64)},
                   {"origin": [0, 4, -20], "size": [0, 40, 40], "uv": plane_uv(64, 0, 64, 64, ("east", "west"))}]},
    ]
    save_json("models/entity/edison_aura.geo.json", geometry("geometry.esb.edison_aura", W, H, bones, (6, 6, [0, 2, 0])))


# ------------------------------------------------------------------------------ volt marker (strike telegraph)

def marker():
    W, H = 256, 128
    S = 2
    im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hot = (150, 220, 255, 255)
    warm = (255, 210, 110, 255)
    cx, cy, R = 64 * S, 64 * S, 60 * S
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=warm, width=4 * S)
    d.ellipse([cx - R * 0.82, cy - R * 0.82, cx + R * 0.82, cy + R * 0.82], outline=warm, width=2 * S)
    rng = np.random.default_rng(9)
    pts = []
    for k in range(48):  # zigzag lightning ring between the two circles
        a = k * 2 * math.pi / 48
        r = R * (0.86 if k % 2 == 0 else 0.97)
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    d.line(pts + [pts[0]], fill=hot, width=2 * S)
    for k in range(6):  # arcs toward the centre
        a = k * math.pi / 3 + 0.2
        x, y = cx + math.cos(a) * R * 0.8, cy + math.sin(a) * R * 0.8
        seg = [(x, y)]
        for j in range(5):
            x += (cx - x) * 0.3 + rng.uniform(-6, 6) * S
            y += (cy - y) * 0.3 + rng.uniform(-6, 6) * S
            seg.append((x, y))
        d.line(seg, fill=hot, width=S * 2)
    # right half: a bolt glyph in a circle
    cx2 = 192 * S
    d.ellipse([cx2 - 40 * S, cy - 40 * S, cx2 + 40 * S, cy + 40 * S], outline=warm, width=3 * S)
    d.polygon([(cx2 + 6 * S, cy - 34 * S), (cx2 - 14 * S, cy + 4 * S), (cx2 - 1 * S, cy + 4 * S), (cx2 - 8 * S, cy + 34 * S),
               (cx2 + 16 * S, cy - 8 * S), (cx2 + 2 * S, cy - 8 * S)], fill=hot)
    img = np.array(im.resize((W, H), Image.LANCZOS)).astype(float)
    img[..., :3] *= img[..., 3:4] / 255.0
    img[..., 3] = np.where(img[..., 3] > 0, 255, 0)
    save_png("textures/entity/volt_marker.png", Image.fromarray(img.astype(np.uint8), "RGBA"))
    bones = [{"name": "root", "pivot": [0, 0, 0]},
             {"name": "ring", "parent": "root", "pivot": [0, 0.2, 0],
              "cubes": [{"origin": [-16, 0.2, -16], "size": [32, 0, 32], "uv": plane_uv(0, 0, 128, 128, ("up", "down"))}]},
             {"name": "glyph", "parent": "root", "pivot": [0, 0.3, 0],
              "cubes": [{"origin": [-9, 0.3, -9], "size": [18, 0, 18], "uv": plane_uv(128, 0, 128, 128, ("up", "down"))}]}]
    save_json("models/entity/volt_marker.geo.json", geometry("geometry.esb.volt_marker", W, H, bones, (12, 2, [0, 0.2, 0])))


# ------------------------------------------------------------------------------ arc bolt (lightning strike)

def bolt():
    W, H = 32, 32
    im = np.zeros((H, W, 4), dtype=np.uint8)
    x = np.arange(16)
    core = np.exp(-((x - 7.5) / 3.0) ** 2)
    for i in range(16):
        im[:, i, :3] = (np.array([235, 248, 255]) * (0.6 + 0.4 * core[i])).astype(np.uint8)
        im[:, 16 + i, :3] = (np.array([120, 190, 255]) * (0.25 + 0.5 * core[i])).astype(np.uint8)
    im[..., 3] = 255
    save_png("textures/entity/arc_bolt.png", Image.fromarray(im, "RGBA"))
    rng = np.random.default_rng(4)
    cubes = []
    x0 = z0 = 0.0
    y = 0.0
    core = {f: {"uv": [0, 0], "uv_size": [16, 32]} for f in ("north", "south", "east", "west")}
    glow = {f: {"uv": [16, 0], "uv_size": [16, 32]} for f in ("north", "south", "east", "west")}
    for i in range(10):
        ln = rng.uniform(20, 30)
        rz, rx = rng.uniform(-24, 24), rng.uniform(-18, 18)
        piv = [round(x0, 2), round(y, 2), round(z0, 2)]
        cubes.append({"origin": [round(x0 - 1, 2), round(y, 2), round(z0 - 1, 2)], "size": [2, round(ln, 2), 2], "pivot": piv,
                      "rotation": [round(rx, 1), 0, round(rz, 1)], "uv": core})
        cubes.append({"origin": [round(x0 - 3, 2), round(y, 2), round(z0 - 3, 2)], "size": [6, round(ln, 2), 6], "pivot": piv,
                      "rotation": [round(rx, 1), 0, round(rz, 1)], "uv": glow})
        x0 -= math.sin(math.radians(-rz)) * ln * 0.9
        z0 += math.sin(math.radians(rx)) * ln * 0.9
        y += ln * 0.95
    bones = [{"name": "root", "pivot": [0, 0, 0]}, {"name": "bolt", "parent": "root", "pivot": [0, 0, 0], "cubes": cubes}]
    save_json("models/entity/arc_bolt.geo.json", geometry("geometry.esb.arc_bolt", W, H, bones, (8, 20, [0, 8, 0])))


if __name__ == "__main__":
    halo()
    aura()
    marker()
    bolt()
    print("ultimate art: halo, aura, volt marker, arc bolt")
