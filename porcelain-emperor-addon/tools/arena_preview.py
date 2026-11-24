"""
Render previews of the Fractured Mandate arena from the compiled blueprint.

    node tools/arena_dump.mjs <compiled-js-dir> arena.json
    python3 tools/arena_preview.py arena.json <out_dir>

Produces a top-down plan (whole court vs. fractured islands) and an
isometric view of every block, so the palace can be checked without the game.
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw

COL = {
    "porcelain:ivory_marble": (236, 227, 207), "porcelain:marble_tile": (246, 239, 224),
    "porcelain:kintsugi_seam": (246, 193, 78), "porcelain:cracked_marble": (220, 207, 178),
    "porcelain:vermilion_lacquer": (199, 50, 42), "porcelain:imperial_roof": (232, 185, 58),
    "porcelain:gilded_floor": (233, 184, 72), "porcelain:seal_tile": (178, 42, 34),
    "minecraft:lantern": (255, 214, 122),
}


def unkey(k):
    return (k // 256 - 128, k % 256 - 128)


def voxels(data, fractured=False):
    vox = {}
    for f in data["fills"]:
        a, b = f["a"], f["b"]
        for x in range(a["x"], b["x"] + 1):
            for y in range(a["y"], b["y"] + 1):
                for z in range(a["z"], b["z"] + 1):
                    vox[(x, y, z)] = f["block"]
    for l in data["lanterns"]:
        vox[(l["x"], l["y"], l["z"])] = "minecraft:lantern"
    if fractured:
        for k in data["gaps"]:
            x, z = unkey(k)
            for y in range(data["bottom"], 1):
                vox.pop((x, y, z), None)
    return vox


def top_down(data, path):
    S = 10
    W = 2 * 56 * S + 30
    img = Image.new("RGB", (W, 56 * S + 40), (24, 22, 30))
    d = ImageDraw.Draw(img)
    for col, fractured in ((0, False), (1, True)):
        vox = voxels(data, fractured)
        top = {}
        for (x, y, z), b in vox.items():
            if (x, z) not in top or y > top[(x, z)][0]:
                top[(x, z)] = (y, b)
        ox = col * (56 * S + 30) + 28 * S
        oz = 28 * S + 30
        for (x, z), (y, b) in top.items():
            c = COL.get(b, (255, 0, 255))
            shade = 1.0 if y <= 1 else min(1.25, 1.0 + y * 0.015)
            c = tuple(min(255, int(v * shade)) for v in c)
            d.rectangle((ox + x * S, oz + z * S, ox + x * S + S - 1, oz + z * S + S - 1), fill=c)
        d.text((ox - 28 * S + 8, 8), "phase 1-2: the whole court (north = up)" if not fractured else
               "phase 3: the Mandate fractures into islands", fill=(240, 230, 200))
        if fractured:
            for isl in data["islands"]:
                sx, sz = isl["safe"]["x"], isl["safe"]["z"]
                d.ellipse((ox + sx * S, oz + sz * S, ox + sx * S + S, oz + sz * S + S), outline=(40, 200, 255), width=2)
    img.save(path)


def iso(data, path, fractured=False, size=1400):
    vox = voxels(data, fractured)
    S = 7.0
    ang = math.radians(35)
    ca, sa = math.cos(ang), math.sin(ang)

    def proj(x, y, z):
        u = (x * ca - z * sa) * S
        w = (x * sa + z * ca)
        v = -y * S * 1.15 + w * S * 0.5
        return u, v, w
    faces = []
    for (x, y, z), b in vox.items():
        c = COL.get(b, (255, 0, 255))
        if (x, y + 1, z) not in vox:
            pts = [proj(x, y + 1, z), proj(x + 1, y + 1, z), proj(x + 1, y + 1, z + 1), proj(x, y + 1, z + 1)]
            faces.append((sum(p[2] for p in pts) / 4 + y * 0.01, pts, c, 1.0))
        if (x, y, z + 1) not in vox:
            pts = [proj(x, y, z + 1), proj(x + 1, y, z + 1), proj(x + 1, y + 1, z + 1), proj(x, y + 1, z + 1)]
            faces.append((sum(p[2] for p in pts) / 4 + 0.5, pts, c, 0.78))
        if (x - 1, y, z) not in vox:
            pts = [proj(x, y, z), proj(x, y, z + 1), proj(x, y + 1, z + 1), proj(x, y + 1, z)]
            faces.append((sum(p[2] for p in pts) / 4 + 0.5, pts, c, 0.62))
    faces.sort(key=lambda f: f[0])
    us = [p[0] for f in faces for p in f[1]]
    vs = [p[1] for f in faces for p in f[1]]
    W = int(max(us) - min(us)) + 40
    H = int(max(vs) - min(vs)) + 40
    img = Image.new("RGB", (W, H), (26, 24, 34))
    d = ImageDraw.Draw(img)
    ou, ov = -min(us) + 20, -min(vs) + 20
    for _, pts, c, l in faces:
        d.polygon([(p[0] + ou, p[1] + ov) for p in pts], fill=tuple(int(v * l) for v in c))
    img.thumbnail((size, size))
    img.save(path)


if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    top_down(data, os.path.join(out, "arena_plan.png"))
    iso(data, os.path.join(out, "arena_iso.png"))
    iso(data, os.path.join(out, "arena_iso_fractured.png"), fractured=True)
    print("arena previews in", out)
