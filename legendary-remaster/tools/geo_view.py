"""Render any Bedrock geometry JSON (per-face or box UV) with its texture - used to audit the original models.
    python3 -I tools/geo_view.py <geo.json> <texture.png> <out_prefix> [scale]"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

from modelkit import apply, rot_matrix  # noqa: E402


def load(path):
    d = json.load(open(path))
    g = d["minecraft:geometry"][0]
    return g


def box_uv(c):
    u, v = c["uv"]
    sx, sy, sz = (math.floor(x) if x >= 1 else x for x in c["size"])
    m = c.get("mirror", False)
    faces = {
        "east": (u, v + sz, sz, sy), "north": (u + sz, v + sz, sx, sy), "west": (u + sz + sx, v + sz, sz, sy),
        "south": (u + 2 * sz + sx, v + sz, sx, sy), "up": (u + sz, v, sx, sz), "down": (u + sz + sx, v, sx, sz),
    }
    if m:
        faces["east"], faces["west"] = faces["west"], faces["east"]
    return faces


def corners(c, face):
    (ox, oy, oz), (sx, sy, sz), i = c["origin"], c["size"], c.get("inflate", 0)
    x0, y0, z0, x1, y1, z1 = ox - i, oy - i, oz - i, ox + sx + i, oy + sy + i, oz + sz + i
    return {
        "north": ((x1, y1, z0), (x0, y1, z0), (x1, y0, z0)),
        "south": ((x0, y1, z1), (x1, y1, z1), (x0, y0, z1)),
        "east": ((x1, y1, z1), (x1, y1, z0), (x1, y0, z1)),
        "west": ((x0, y1, z0), (x0, y1, z1), (x0, y0, z0)),
        "up": ((x1, y1, z1), (x0, y1, z1), (x1, y1, z0)),
        "down": ((x1, y0, z0), (x0, y0, z0), (x1, y0, z1)),
    }[face]


def quads(g, tex, hidden=(), pose=None):
    W, H = g["description"]["texture_width"], g["description"]["texture_height"]
    sxp, syp = tex.size[0] / W, tex.size[1] / H
    px = tex.load()
    bones = {b["name"]: b for b in g["bones"]}
    out = []
    pose = pose or {}

    def chain(b):
        r = []
        while b is not None:
            r.append(b)
            b = bones.get(b.get("parent"))
        return r
    for b in g["bones"]:
        ch = chain(b)
        if any(x["name"] in hidden for x in ch):
            continue
        glow = any(x["name"].startswith("glow") for x in ch)
        for c in b.get("cubes", []):
            cm = rot_matrix(c.get("rotation"))
            cpiv = c.get("pivot", c["origin"])

            def tf(p):
                p = apply(cm, p, cpiv)
                for bb in ch:
                    r = bb.get("rotation") or [0, 0, 0]
                    if bb["name"] in pose:
                        r = [r[k] + pose[bb["name"]][k] for k in range(3)]
                    p = apply(rot_matrix(r), p, bb["pivot"])
                return p
            uvs = c["uv"] if isinstance(c.get("uv"), dict) else box_uv(c) if "uv" in c else {}
            for face, uvd in uvs.items():
                if isinstance(uvd, dict):
                    (u, v), (w, h) = uvd["uv"], uvd.get("uv_size", [0, 0])
                else:
                    u, v, w, h = uvd
                if w == 0 or h == 0:
                    continue
                tl, tr, bl = (tf(p) for p in corners(c, face))
                nu = max(1, int(round(abs(w) * sxp)))
                nv = max(1, int(round(abs(h) * syp)))
                step = max(1, int(max(nu, nv) / 24))
                for yy in range(0, nv, step):
                    for xx in range(0, nu, step):
                        tx = int((u + (xx + 0.5) / nu * w) * sxp)
                        ty = int((v + (yy + 0.5) / nv * h) * syp)
                        if not (0 <= tx < tex.size[0] and 0 <= ty < tex.size[1]):
                            continue
                        col = px[tx, ty]
                        if col[3] < 100:
                            continue
                        a0, a1 = xx / nu, min(1, (xx + step) / nu)
                        b0, b1 = yy / nv, min(1, (yy + step) / nv)
                        P = lambda a, bq: tuple(tl[k] + (tr[k] - tl[k]) * a + (bl[k] - tl[k]) * bq for k in range(3))
                        out.append(((P(a0, b0), P(a1, b0), P(a1, b1), P(a0, b1)), col, face, glow))
    return out


def render(qs, path, yaw, pitch, size=520, title=""):
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))

    def view(p):
        x, y, z = p
        x2, z2 = x * cy - z * sy, x * sy + z * cy
        return (-x2, y * cp + z2 * sp, -y * sp + z2 * cp)
    light = {"up": 1.0, "north": 0.88, "south": 0.72, "east": 0.8, "west": 0.8, "down": 0.55}
    proj = []
    for pts, col, face, glow in qs:
        vp = [view(p) for p in pts]
        proj.append((sum(p[2] for p in vp) / 4, vp, col, 1.15 if glow else light[face]))
    if not proj:
        return
    xs = [p[0] for _, vp, _, _ in proj for p in vp]
    ys = [p[1] for _, vp, _, _ in proj for p in vp]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.08
    sc = size / span
    cx, cy2 = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    img = Image.new("RGBA", (size, size), (20, 18, 28, 255))
    d = ImageDraw.Draw(img)
    proj.sort(key=lambda q: -q[0])
    for _, vp, col, l in proj:
        pts = [((p[0] - cx) * sc + size / 2, size / 2 - (p[1] - cy2) * sc) for p in vp]
        d.polygon(pts, fill=tuple(min(255, int(col[i] * l)) for i in range(3)) + (255,))
    if title:
        d.text((6, 6), title, fill=(230, 230, 240, 255))
    img.save(path)


def sheet(geo, texture, prefix, hidden=(), pose=None, label=""):
    g = load(geo)
    tex = Image.open(texture).convert("RGBA")
    qs = quads(g, tex, hidden, pose)
    tiles = []
    for tag, yaw, pitch in (("front", 0, 8), ("front34", 35, 18), ("side", 90, 5), ("back34", 215, 20), ("top", 20, 65)):
        p = f"{prefix}_{tag}.png"
        render(qs, p, yaw, pitch, title=f"{label} {tag}")
        tiles.append(p)
    W = Image.new("RGBA", (3 * 420, 2 * 420), (10, 10, 14, 255))
    for i, p in enumerate(tiles):
        W.paste(Image.open(p).resize((420, 420)), ((i % 3) * 420, (i // 3) * 420))
    W.save(f"{prefix}_sheet.png")
    return len(qs)


if __name__ == "__main__":
    print(sheet(sys.argv[1], sys.argv[2], sys.argv[3], label=os.path.basename(sys.argv[3])))
