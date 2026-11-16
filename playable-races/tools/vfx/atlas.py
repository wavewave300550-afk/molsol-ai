"""Particle atlas 3 (v1.3): white, soft, animated sprites for the ability effects of every race.

The sprites are drawn white / grey so one sprite serves every race: the particle tint gives
it the race's colour (additive glows) or its material colour (blended smoke, liquid).
Rows 0-6 are 8-frame flipbooks of 64 px cells (flash, shockwave ring, magic circle that
draws itself, sword-arc slash, smoke puff, liquid splash, branching crack); row 7 holds
32 px static sprites.  Drawn from distance fields at 4x supersampling.
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

TEX = "textures/plrace/races/particles/particles_vfx"
W = H = 512
CELL = 64
FRAMES = 8
SS = 4

FLIPBOOKS = ["flash", "ring", "circle", "slash", "smoke", "splash", "crack"]
FLIP: Dict[str, Tuple[int, int]] = {name: (0, row * CELL) for row, name in enumerate(FLIPBOOKS)}   # base UV of frame 0
SPRITES = ["streak", "dot", "star4", "star8", "petal", "leaf", "droplet", "shard",
           "rune1", "rune2", "rune3", "rune4", "ember", "crescent", "hexagon", "chunk",
           "glyphring", "spiral", "heart", "feather",
           # v1.4 (Expansion 02)
           "clade", "eye", "polyspore", "tooth", "sunsigil", "fan"]
SPR: Dict[str, Tuple[int, int, int, int]] = {}
for _i, _n in enumerate(SPRITES):
    SPR[_n] = ((_i % 16) * 32, 7 * CELL + (_i // 16) * 32, 32, 32)
SPR["leviathan"] = (13 * 32, 7 * CELL + 32, 96, 32)    # a wide silhouette in the last three cells


# ============================================================================= fields

def _grid(n=CELL * SS):
    c = (np.arange(n) + 0.5) / n * 2 - 1
    X, Y = np.meshgrid(c, c)
    return X, Y, np.hypot(X, Y), np.arctan2(Y, X)


def _img(alpha, shade=None):
    """White (or grey-shaded) RGBA from an alpha field in 0..1."""
    a = np.clip(alpha, 0, 1)
    rgb = np.ones(a.shape + (3,)) if shade is None else np.repeat(np.clip(shade, 0, 1)[..., None], 3, axis=2)
    out = np.dstack([rgb * 255, a * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def _down(im, size=CELL):
    return im.resize((size, size), Image.LANCZOS)


def _angdiff(a, b):
    return (a - b + np.pi) % (2 * np.pi) - np.pi


# ============================================================================= flipbooks

def flash(t):
    X, Y, R, A = _grid()
    core = np.exp(-(R / (0.13 + 0.2 * t)) ** 2) * (1 - t) ** 1.1
    rays = np.zeros_like(R)
    for k in range(16):
        a = k * np.pi / 8 + 0.2
        major = k % 2 == 0
        L = (0.38 + 0.55 * t) * (1.0 if major else 0.6)
        w = (0.045 if major else 0.03) * (1 - 0.5 * t)
        d = _angdiff(A, a)
        perp, along = np.abs(R * np.sin(d)), R * np.cos(d)
        rays = np.maximum(rays, np.exp(-(perp / w) ** 2) * np.clip(1 - along / L, 0, 1) * (along > 0))
    halo = 0.45 * np.exp(-(R / (0.35 + 0.45 * t)) ** 2) * (1 - t) ** 2
    return _img(core + rays * (1 - t) ** 1.3 + halo)


def ring(t):
    X, Y, R, A = _grid()
    r = 0.14 + 0.78 * t
    w = 0.085 * (1 - 0.6 * t) + 0.018
    band = np.exp(-((R - r) / w) ** 2)
    inner = 0.3 * np.exp(-((R - r * 0.82) / (w * 3)) ** 2)
    breakup = 1 - 0.35 * t * (0.5 + 0.5 * np.sin(A * 9 + 3 * t))
    return _img((band + inner) * breakup * (1 - t) ** 0.9)


def circle(t):
    """Magic circle drawing itself: frame 7 is the complete circle."""
    p = min(1.0, (t * 7 + 1) / 6)
    X, Y, R, A = _grid()
    ang = (A + np.pi / 2) % (2 * np.pi)                 # 0 at the top, increasing clockwise in image space
    out = np.zeros_like(R)

    def arc(radius, width, frac, glow=1.0):
        on = ang <= frac * 2 * np.pi
        return np.exp(-((R - radius) / width) ** 2) * on * glow
    out = np.maximum(out, arc(0.9, 0.022, p))
    out = np.maximum(out, arc(0.7, 0.014, max(0.0, p * 1.15 - 0.15)))
    out = np.maximum(out, arc(0.26, 0.016, max(0.0, p * 1.3 - 0.3)))
    for k in range(24):                                  # tick marks between the rings
        a = k * 2 * np.pi / 24
        if a / (2 * np.pi) > p:
            continue
        d = _angdiff(ang, a)
        long_tick = k % 6 == 0
        r0 = 0.7 if long_tick else 0.78
        tick = np.exp(-((R * np.sin(d)) / 0.012) ** 2) * (R > r0) * (R < 0.9) * (np.cos(d) > 0)
        out = np.maximum(out, tick * (1.0 if long_tick else 0.7))
    if p > 0.45:                                          # an eight-point star appears inside
        q = min(1.0, (p - 0.45) / 0.4)
        pts = [(math.cos(k * math.pi / 4 - math.pi / 2) * 0.68, math.sin(k * math.pi / 4 - math.pi / 2) * 0.68) for k in range(8)]
        for k in range(8):
            ax, ay = pts[k]
            bx, by = pts[(k + 3) % 8]
            dx, dy = bx - ax, by - ay
            L = math.hypot(dx, dy)
            u = ((X - ax) * dx + (Y - ay) * dy) / L
            v = np.abs((X - ax) * dy - (Y - ay) * dx) / L
            seg = np.exp(-(v / 0.01) ** 2) * (u > 0) * (u < L * q)
            out = np.maximum(out, seg * 0.8)
    if p > 0.7:                                           # four diamonds on the cardinal points
        for k in range(4):
            a = k * np.pi / 2
            cx, cy = math.cos(a) * 0.8, math.sin(a) * 0.8
            dia = (np.abs(X - cx) + np.abs(Y - cy)) < 0.06
            out = np.maximum(out, dia * 1.0)
    im = _img(out)
    glow = im.filter(ImageFilter.GaussianBlur(2.2 * SS))
    a = np.maximum(np.asarray(im)[..., 3], (np.asarray(glow)[..., 3] * (0.55 + 0.3 * (t > 0.95)))).astype(np.uint8)
    return Image.fromarray(np.dstack([np.full(a.shape + (3,), 255, np.uint8), a]), "RGBA")


def slash(t):
    X, Y, R, A = _grid()
    head = -2.1 + 3.3 * min(1.0, t * 1.7)                 # radians, sweeping across the top
    tail = head - 2.5 * min(1.0, t * 2.4 + 0.1)
    a = A
    inside = (a <= head) & (a >= tail)
    f = np.clip((a - tail) / max(head - tail, 1e-3), 0, 1)
    thick = 0.16 * f ** 1.2 + 0.01
    band = np.exp(-((R - 0.62) / thick) ** 2) * inside
    edge = np.exp(-((R - 0.62 - thick * 0.6) / 0.02) ** 2) * inside * f
    fade = 1.0 if t < 0.55 else max(0.0, 1 - (t - 0.55) / 0.45)
    return _img((band * f ** 0.7 + edge) * fade)


def smoke(t):
    X, Y, R, A = _grid()
    rng = np.random.default_rng(4)
    out = np.zeros_like(R)
    for k in range(6):
        cx, cy = rng.uniform(-0.25, 0.25, 2) * (0.5 + t)
        rr = (0.25 + 0.45 * t) * rng.uniform(0.6, 1.0)
        out = np.maximum(out, np.exp(-((np.hypot(X - cx, Y - cy - 0.15 * t)) / rr) ** 2.4))
    shade = 0.75 + 0.25 * np.clip(-Y, 0, 1)
    return _img(out * 0.85 * (1 - t) ** 1.3, shade)


def splash(t):
    X, Y, R, A = _grid()
    out = np.exp(-(R / (0.28 * (1 - t) + 0.05)) ** 2) * (1 - t)
    rng = np.random.default_rng(9)
    for k in range(12):
        a = k * 2 * np.pi / 12 + rng.uniform(-0.2, 0.2)
        sp = rng.uniform(0.6, 1.0)
        cx = math.cos(a) * (0.15 + 0.7 * t * sp)
        cy = math.sin(a) * (0.15 + 0.7 * t * sp) - 0.25 * t + 0.45 * t * t   # flung up, then falling
        rr = 0.07 * (1 - 0.5 * t) * rng.uniform(0.7, 1.2)
        out = np.maximum(out, np.exp(-(np.hypot(X - cx, Y - cy) / rr) ** 2.5) * (1 - t) ** 0.6)
    ring_ = 0.6 * np.exp(-((R - (0.22 + 0.6 * t)) / 0.03) ** 2) * (1 - t)
    shade = 0.8 + 0.2 * np.clip(-(X + Y), 0, 1)
    return _img(out + ring_, shade)


_CRACK = None


def _crack_paths():
    global _CRACK
    if _CRACK is None:
        rng = np.random.default_rng(12)
        paths = []

        def grow(x, y, a, L, depth, start):
            pts = [(x, y, start)]
            s = start
            for _ in range(5):
                a += rng.uniform(-0.45, 0.45)
                nx, ny = x + math.cos(a) * L / 5, y + math.sin(a) * L / 5
                s += L / 5
                pts.append((nx, ny, s))
                x, y = nx, ny
                if depth > 0 and rng.random() < 0.35:
                    grow(x, y, a + rng.choice([-0.8, 0.8]), L * 0.5, depth - 1, s)
            paths.append(pts)
        for k in range(6):
            grow(0.0, 0.0, k * math.pi / 3 + rng.uniform(-0.3, 0.3), 0.85, 1, 0.0)
        _CRACK = paths
    return _CRACK


def crack(t):
    X, Y, R, A = _grid()
    reveal = min(1.2, t * 2.4)
    out = np.zeros_like(R)
    for pts in _crack_paths():
        for (ax, ay, sa), (bx, by, sb) in zip(pts, pts[1:]):
            if sa > reveal:
                continue
            frac = min(1.0, (reveal - sa) / max(sb - sa, 1e-6))
            ex, ey = ax + (bx - ax) * frac, ay + (by - ay) * frac
            dx, dy = ex - ax, ey - ay
            L = math.hypot(dx, dy)
            if L < 1e-3:
                continue
            u = ((X - ax) * dx + (Y - ay) * dy) / L
            v = np.abs((X - ax) * dy - (Y - ay) * dx) / L
            w = 0.022 * (1 - sa / 1.3) + 0.006
            seg = np.exp(-(v / w) ** 2) * (u > -w) * (u < L + w)
            out = np.maximum(out, seg)
    fade = 1.0 if t < 0.6 else max(0.0, 1 - (t - 0.6) / 0.4)
    im = _img(out * fade)
    glow = np.asarray(im.filter(ImageFilter.GaussianBlur(2.5 * SS)))[..., 3]
    a = np.maximum(np.asarray(im)[..., 3], glow * 0.6).astype(np.uint8)
    return Image.fromarray(np.dstack([np.full(a.shape + (3,), 255, np.uint8), a]), "RGBA")


DRAW = {"flash": flash, "ring": ring, "circle": circle, "slash": slash, "smoke": smoke, "splash": splash, "crack": crack}


# ============================================================================= static sprites (32 px)

def _sprite(name):
    n = 32 * 8
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def P(pts):
        return [(x * n, y * n) for x, y in pts]
    white, grey = (255, 255, 255, 255), (200, 200, 200, 255)
    X, Y, R, A = _grid(n)
    if name == "streak":
        u = np.abs(X) / 0.16
        v = np.abs(Y) / 0.95
        return _img(np.exp(-u ** 2) * np.clip(1 - v ** 2, 0, 1) + 0.6 * np.exp(-(np.abs(X) / 0.05) ** 2) * np.clip(1 - v ** 1.5, 0, 1))
    if name == "dot":
        return _img(np.exp(-(R / 0.42) ** 2) + 0.5 * np.exp(-(R / 0.15) ** 2))
    if name in ("star4", "star8"):
        k = 4 if name == "star4" else 8
        out = np.exp(-(R / 0.12) ** 2)
        for i in range(k):
            a = i * 2 * np.pi / k
            dd = _angdiff(A, a)
            L = 0.95 if i % 2 == 0 or k == 4 else 0.55
            out = np.maximum(out, np.exp(-((R * np.sin(dd)) / 0.05) ** 2) * np.clip(1 - R * np.cos(dd) / L, 0, 1) * (np.cos(dd) > 0))
        return _img(out + 0.35 * np.exp(-(R / 0.4) ** 2))
    if name == "petal":
        shape = ((X / 0.42) ** 2 + ((Y - 0.05) / 0.85) ** 2) < 1
        notch = (np.abs(X) < 0.12 - (Y + 0.85) * 0.4) & (Y < -0.65)
        shade = 0.75 + 0.25 * (1 - np.abs(X) / 0.42) - 0.15 * (Y > 0.4)
        return _img(shape & ~notch, shade)
    if name == "leaf":
        shape = ((X / 0.38) ** 2 + (Y / 0.9) ** 2) < 1
        vein = np.abs(X) < 0.035
        side = (np.abs(np.abs(X) - (0.9 - Y) * 0.25) < 0.025) & (np.abs(X) < 0.3)
        shade = 0.7 + 0.25 * (1 - np.abs(X) / 0.38) + 0.25 * vein + 0.12 * side
        return _img(shape * 1.0, shade)
    if name == "droplet":
        d.polygon(P([(0.5, 0.08), (0.28, 0.58), (0.72, 0.58)]), fill=white)
        d.ellipse(P([(0.27, 0.42), (0.73, 0.88)]), fill=white)
        d.ellipse(P([(0.38, 0.52), (0.48, 0.64)]), fill=(255, 255, 255, 255))
        a = np.asarray(im)[..., 3] / 255.0
        shade = 0.72 + 0.28 * np.clip(-(X + Y) * 0.8, 0, 1)
        return _img(a, shade)
    if name == "shard":
        d.polygon(P([(0.5, 0.06), (0.82, 0.42), (0.6, 0.94), (0.22, 0.6)]), fill=white)
        a = np.asarray(im)[..., 3] / 255.0
        shade = 0.6 + 0.4 * (X < 0) * 1.0 + 0.0
        return _img(a, np.where(X + Y * 0.3 < 0, 1.0, 0.68))
    if name.startswith("rune"):
        k = int(name[-1])
        strokes = {1: [[(0.5, 0.12), (0.5, 0.88)], [(0.5, 0.3), (0.78, 0.12)], [(0.5, 0.52), (0.78, 0.34)]],
                   2: [[(0.3, 0.12), (0.3, 0.88)], [(0.3, 0.12), (0.72, 0.4)], [(0.72, 0.4), (0.3, 0.62)], [(0.3, 0.62), (0.72, 0.88)]],
                   3: [[(0.2, 0.2), (0.8, 0.8)], [(0.8, 0.2), (0.2, 0.8)], [(0.5, 0.1), (0.5, 0.9)]],
                   4: [[(0.25, 0.85), (0.5, 0.12)], [(0.5, 0.12), (0.75, 0.85)], [(0.32, 0.6), (0.68, 0.6)]]}[k]
        for s in strokes:
            d.line(P(s), fill=white, width=int(0.11 * n), joint="curve")
            for x, y in P([s[0], s[-1]]):
                r = 0.055 * n
                d.ellipse([x - r, y - r, x + r, y + r], fill=white)
        g = im.filter(ImageFilter.GaussianBlur(0.06 * n))
        a = np.maximum(np.asarray(im)[..., 3], np.asarray(g)[..., 3] * 0.6) / 255.0
        return _img(a)
    if name == "ember":
        return _img(((np.abs(X) / 0.32 + np.abs(Y) / 0.62) < 1) * 1.0 + 0.4 * np.exp(-(R / 0.5) ** 2))
    if name == "crescent":
        outer = R < 0.8
        inner = np.hypot(X - 0.32, Y + 0.12) < 0.66
        shape = outer & ~inner
        return _img(shape * 1.0 + 0.25 * np.exp(-(R / 0.9) ** 2) * ~inner, 0.85 + 0.15 * (X < -0.3))
    if name == "hexagon":
        hexd = np.maximum(np.abs(X) * 0.866 + np.abs(Y) * 0.5, np.abs(Y))
        return _img(np.exp(-((hexd - 0.78) / 0.05) ** 2) + 0.18 * (hexd < 0.78))
    if name == "chunk":
        d.polygon(P([(0.22, 0.32), (0.55, 0.14), (0.84, 0.38), (0.76, 0.8), (0.36, 0.86), (0.14, 0.6)]), fill=white)
        a = np.asarray(im)[..., 3] / 255.0
        shade = np.where(Y < -0.1, 1.0, np.where(X < 0, 0.72, 0.55))
        return _img(a, shade)
    if name == "glyphring":
        out = np.exp(-((R - 0.82) / 0.05) ** 2) + np.exp(-((R - 0.6) / 0.035) ** 2) * 0.8
        for k in range(8):
            a = k * np.pi / 4
            dd = _angdiff(A, a)
            out = np.maximum(out, np.exp(-((R * np.sin(dd)) / 0.03) ** 2) * (R > 0.6) * (R < 0.82) * (np.cos(dd) > 0))
        return _img(out)
    if name == "spiral":
        th = (A + 2 * np.pi) % (2 * np.pi)
        out = np.zeros_like(R)
        for turn in range(3):
            rr = 0.1 + (th + turn * 2 * np.pi) / (6 * np.pi) * 0.8
            out = np.maximum(out, np.exp(-((R - rr) / 0.04) ** 2))
        return _img(out * (R < 0.95))
    if name == "heart":
        x, y = X / 0.8, -Y / 0.8 + 0.15
        f = (x * x + y * y - 0.55) ** 3 - x * x * y ** 3
        return _img((f < 0) * 1.0, 0.8 + 0.2 * (Y < -0.2))
    if name == "feather":
        shape = ((X / 0.25) ** 2 + (Y / 0.92) ** 2) < 1
        barbs = 0.75 + 0.25 * np.sin((Y - np.abs(X) * 0.8) * 40)
        return _img(shape * 1.0, barbs)
    # ---- v1.4 (Expansion 02)
    if name == "clade":
        # a cladogram whose middle branch is broken and re-joined somewhere it should not be
        for seg in ([(0.5, 0.92), (0.5, 0.62)], [(0.5, 0.62), (0.24, 0.36)], [(0.5, 0.62), (0.76, 0.36)],
                    [(0.24, 0.36), (0.12, 0.1)], [(0.24, 0.36), (0.36, 0.1)], [(0.76, 0.36), (0.88, 0.1)],
                    [(0.64, 0.1), (0.52, 0.3)], [(0.52, 0.3), (0.36, 0.1)]):
            d.line(P(seg), fill=white, width=int(0.075 * n))
        for x, y in P([(0.12, 0.1), (0.36, 0.1), (0.64, 0.1), (0.88, 0.1)]):
            r = 0.06 * n
            d.ellipse([x - r, y - r, x + r, y + r], fill=white)
        g = im.filter(ImageFilter.GaussianBlur(0.05 * n))
        return _img(np.maximum(np.asarray(im)[..., 3], np.asarray(g)[..., 3] * 0.7) / 255.0)
    if name == "eye":
        out = np.zeros_like(R)
        for k, rr in enumerate((0.86, 0.66, 0.47)):
            sides = (11, 7, 5)[k]
            poly = R * np.cos(_angdiff(A, np.round(A / (2 * np.pi / sides)) * (2 * np.pi / sides))) / np.cos(np.pi / sides)
            out = np.maximum(out, np.exp(-((poly - rr) / 0.035) ** 2) * (0.6 + 0.4 * (k == 0)))
        out = np.maximum(out, (R < 0.22) * 1.0)
        return _img(out, np.where(R < 0.22, 0.25, 1.0))
    if name == "polyspore":
        sides = 5
        poly = R * np.cos(_angdiff(A, np.round(A / (2 * np.pi / sides)) * (2 * np.pi / sides))) / np.cos(np.pi / sides)
        return _img(np.exp(-((poly - 0.62) / 0.07) ** 2) + 0.35 * (poly < 0.62) + 0.6 * np.exp(-(R / 0.14) ** 2))
    if name == "tooth":
        d.polygon(P([(0.5, 0.04), (0.64, 0.7), (0.5, 0.96), (0.36, 0.7)]), fill=white)
        a = np.asarray(im)[..., 3] / 255.0
        return _img(a, np.where(X < 0, 1.0, 0.75))
    if name == "sunsigil":
        out = np.exp(-((R - 0.52) / 0.05) ** 2)
        for k in range(12):
            dd = _angdiff(A, k * np.pi / 6)
            out = np.maximum(out, np.exp(-((R * np.sin(dd)) / 0.03) ** 2) * (R > 0.62) * (R < (0.95 if k % 3 == 0 else 0.8)) * (np.cos(dd) > 0))
        blade = (np.abs(X) < 0.06 - np.abs(Y) * 0.03) & (np.abs(Y) < 0.9)
        return _img(np.maximum(out, blade * 1.0))
    if name == "fan":
        out = np.zeros_like(R)
        for k in range(7):
            a = -np.pi / 2 + (k - 3) * 0.32
            dd = _angdiff(A, a)
            out = np.maximum(out, np.exp(-((R * np.sin(dd)) / (0.05 + R * 0.05)) ** 2) * (R < 0.92) * (np.cos(dd) > 0))
        return _img(out, 0.8 + 0.2 * (R > 0.6))
    raise KeyError(name)


def _leviathan() -> Image.Image:
    """A vast deep-sea silhouette (anglerfish-whale) with a lure, 3:1, soft-edged."""
    w, h = 96 * 8, 32 * 8
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    body = [(0.06, 0.55), (0.18, 0.3), (0.42, 0.18), (0.7, 0.22), (0.86, 0.36), (0.97, 0.3), (0.95, 0.5), (0.97, 0.72),
            (0.86, 0.62), (0.7, 0.78), (0.42, 0.84), (0.2, 0.76), (0.1, 0.66)]
    d.polygon([(x * w, y * h) for x, y in body], fill=(255, 255, 255, 255))
    d.line([(0.16 * w, 0.32 * h), (0.1 * w, 0.06 * h), (0.03 * w, 0.12 * h)], fill=(255, 255, 255, 255), width=int(0.025 * h * 3))
    for k in range(9):   # needle teeth along the jaw
        x = 0.07 + k * 0.012
        d.polygon([(x * w, 0.58 * h), ((x + 0.006) * w, 0.7 * h), ((x + 0.012) * w, 0.58 * h)], fill=(0, 0, 0, 0))
    im = im.filter(ImageFilter.GaussianBlur(4))
    lure = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(lure).ellipse([0.015 * w, 0.05 * h, 0.05 * w, 0.17 * h], fill=(255, 255, 255, 255))
    a = np.maximum(np.asarray(im)[..., 3] / 255.0 * 0.95, np.asarray(lure)[..., 3] / 255.0)
    shade = np.where(np.asarray(lure)[..., 3] > 0, 1.0, 0.35)
    out = np.dstack([np.repeat(shade[..., None], 3, axis=2) * 255, a * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def atlas() -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for row, name in enumerate(FLIPBOOKS):
        for f in range(FRAMES):
            img.alpha_composite(_down(DRAW[name](f / (FRAMES - 1))), (f * CELL, row * CELL))
    for name, (x, y, w, h) in SPR.items():
        src = _leviathan() if name == "leviathan" else _sprite(name)
        img.alpha_composite(src.resize((w, h), Image.LANCZOS), (x, y))
    return img
