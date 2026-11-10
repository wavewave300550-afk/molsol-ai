#!/usr/bin/env python3
"""Software preview renderer for real .geo.json + texture files (library; used by tools/preview.py).

Adapted from the Grizzly's Oath add-on in this repository.

* Bedrock per-face UVs, bone pivots / parents / rotations (Blockbench convention:
  Rz(z) * Ry(-y) * Rx(-x)), cube inflate.
* Pixels the packs mark as emissive (low alpha with the entity_emissive material) are drawn
  full-bright with a red bloom, like in game.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def bedrock_rot(r):
    x, y, z = (math.radians(v) for v in r)
    return rz(z) @ ry(-y) @ rx(-x)


def load_geo(path):
    return json.load(open(path))["minecraft:geometry"][0]


def sample(keys, t):
    """keys: {"time": value} with numbers or [x,y,z]; linear interpolation."""
    if not isinstance(keys, dict):
        return keys
    pts = sorted((float(k), v) for k, v in keys.items())
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0
            if isinstance(v0, list):
                return [a + (b - a) * f for a, b in zip(v0, v1)]
            return v0 + (v1 - v0) * f
    return pts[-1][1]


def bone_matrices(geo, pose):
    bones = {b["name"]: b for b in geo["bones"]}
    cache = {}

    def world(name):
        if name in cache:
            return cache[name]
        b = bones[name]
        piv = np.array(b.get("pivot", [0, 0, 0]), float)
        p = pose.get(name, {})
        rot = np.array(b.get("rotation", [0, 0, 0]), float) + np.array(p.get("rotation", [0, 0, 0]), float)
        R = bedrock_rot(rot)
        sc = p.get("scale", 1)
        sc = np.array(sc if isinstance(sc, list) else [sc] * 3, float)
        pos = p.get("position", [0, 0, 0])
        off = np.array([-pos[0], pos[1], pos[2]], float)  # animation x is mirrored

        def local(v, R=R, piv=piv, sc=sc, off=off):
            return (R @ ((v - piv) * sc)) + piv + off

        parent = b.get("parent")
        if parent:
            pw = world(parent)
            fn = lambda v, local=local, pw=pw: pw(local(v))
        else:
            fn = local
        cache[name] = fn
        return fn

    return {n: world(n) for n in bones}


FACES = {
    # face: (top-left corner selector, u axis, v axis, normal)
    "north": ((1, 1, 0), (-1, 0, 0), (0, -1, 0), (0, 0, -1)),
    "south": ((0, 1, 1), (1, 0, 0), (0, -1, 0), (0, 0, 1)),
    "east": ((1, 1, 1), (0, 0, -1), (0, -1, 0), (1, 0, 0)),
    "west": ((0, 1, 0), (0, 0, 1), (0, -1, 0), (-1, 0, 0)),
    "up": ((0, 1, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0)),
    "down": ((0, 0, 1), (1, 0, 0), (0, 0, -1), (0, -1, 0)),
}


def collect_quads(geo, pose):
    mats = bone_matrices(geo, pose)
    quads = []
    for b in geo["bones"]:
        W = mats[b["name"]]
        for c in b.get("cubes", []):
            inf = c.get("inflate", 0)
            o = np.array(c["origin"], float) - inf
            s = np.array(c["size"], float) + 2 * inf
            lo, hi = o, o + s
            for face, f in c.get("uv", {}).items():
                sel, ua, va, n = FACES[face]
                tl = np.where(np.array(sel) == 1, hi, lo)
                du = np.array(ua, float) * s
                dv = np.array(va, float) * s
                p0, p1, p2 = W(tl), W(tl + du), W(tl + dv)
                pn = W(tl + np.array(n, float)) - p0
                quads.append((p0, p1 - p0, p2 - p0, pn, f["uv"], f["uv_size"]))
    return quads


def render(geo, tex, pose, yaw, pitch, size, scale, center, light=(0.45, 0.8, -0.4)):
    tex = np.asarray(tex.convert("RGBA"), float) / 255.0
    TH, TW = tex.shape[:2]
    # camera basis (orthographic): rotate world so the camera looks along +z after yaw/pitch
    M = rx(math.radians(pitch)) @ ry(math.radians(yaw))
    color = np.zeros((size, size, 3))
    alpha = np.zeros((size, size))
    glow = np.zeros((size, size, 3))
    depth = np.full((size, size), np.inf)
    L = np.array(light, float)
    L /= np.linalg.norm(L)
    c = np.array(center, float)
    for p0, e1, e2, nrm, uv, uvs in collect_quads(geo, pose):
        q0 = M @ (p0 - c)
        a = M @ e1
        b = M @ e2
        n = M @ nrm
        if n[2] > -1e-6:  # back face (camera looks along +z)
            continue
        to_px = lambda q: np.array([size / 2 + q[0] * scale, size / 2 - q[1] * scale])
        s0 = to_px(q0)
        sa = np.array([a[0] * scale, -a[1] * scale])
        sb = np.array([b[0] * scale, -b[1] * scale])
        corners = np.array([s0, s0 + sa, s0 + sb, s0 + sa + sb])
        x0, y0 = np.floor(corners.min(0)).astype(int)
        x1, y1 = np.ceil(corners.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        det = sa[0] * sb[1] - sa[1] * sb[0]
        if abs(det) < 1e-9:
            continue
        ys, xs = np.mgrid[y0 : y1 + 1, x0 : x1 + 1]
        dx = xs + 0.5 - s0[0]
        dy = ys + 0.5 - s0[1]
        s = (dx * sb[1] - dy * sb[0]) / det
        t = (sa[0] * dy - sa[1] * dx) / det
        inside = (s >= 0) & (s <= 1) & (t >= 0) & (t <= 1)
        if not inside.any():
            continue
        z = q0[2] + s * a[2] + t * b[2]
        u = np.clip(np.floor(uv[0] + s * uvs[0]), 0, TW - 1).astype(int)
        v = np.clip(np.floor(uv[1] + t * uvs[1]), 0, TH - 1).astype(int)
        texel = tex[v, u]
        nn = n / (np.linalg.norm(n) + 1e-9)
        world_n = M.T @ nn
        shade = 0.55 + 0.45 * max(0.0, float(world_n @ L)) + 0.08 * world_n[1]
        visible = inside & (texel[..., 3] > 0.0) & (z < depth[ys, xs])
        if not visible.any():
            continue
        yy, xx = ys[visible], xs[visible]
        tv = texel[visible]
        emissive = tv[:, 3] < 0.5
        rgb = tv[:, :3] * np.where(emissive[:, None], 1.0, shade)
        depth[yy, xx] = z[visible]
        color[yy, xx] = rgb
        alpha[yy, xx] = 1.0
        glow[yy, xx] = np.where(emissive[:, None], tv[:, :3], 0.0)
    return color, alpha, glow


def compose(color, alpha, glow, bg):
    size = color.shape[0]
    base = np.asarray(bg.convert("RGB").resize((size, size)), float) / 255.0
    out = base * (1 - alpha[..., None]) + color * alpha[..., None]
    g = Image.fromarray((np.clip(glow, 0, 1) * 255).astype(np.uint8))
    bloom = sum(np.asarray(g.filter(ImageFilter.GaussianBlur(r)), float) / 255.0 * w for r, w in ((3, 0.9), (10, 0.7), (24, 0.5)))
    out = 1 - (1 - out) * (1 - np.clip(bloom, 0, 1))  # screen blend
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


def backdrop(size, hue=(120, 14, 18)):
    yy, xx = np.mgrid[0:size, 0:size] / size
    d = np.sqrt((xx - 0.5) ** 2 + (yy - 0.45) ** 2)
    t = np.clip(1 - d * 1.7, 0, 1) ** 2
    img = np.zeros((size, size, 3))
    for i, (lo, hi) in enumerate(zip((10, 6, 8), hue)):
        img[..., i] = lo + (hi - lo) * t
    return Image.fromarray(img.astype(np.uint8))


def label(img, text, sub=None):
    d = ImageDraw.Draw(img)
    d.text((18, img.size[1] - 46), text, fill=(255, 214, 200))
    if sub:
        d.text((18, img.size[1] - 28), sub, fill=(190, 120, 110))
    return img
