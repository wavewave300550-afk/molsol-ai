"""Procedural magic-circle textures (additive: black = transparent)."""
import math
import numpy as np
from .art import Art


def _rune_band(a, cx, cy, r0, r1, n, color, seed, glow=None, width=0.6):
    """A ring band filled with procedural glyphs."""
    rs = np.random.RandomState(seed)
    a.circle(cx, cy, r0, outline=color, width=width)
    a.circle(cx, cy, r1, outline=color, width=width)
    rm = (r0 + r1) / 2
    hh = (r1 - r0) * 0.38
    for i in range(n):
        ang = math.tau * (i + 0.5) / n
        ca, sa = math.cos(ang), math.sin(ang)
        tx, ty = -sa, ca  # tangent
        px, py = cx + ca * rm, cy + sa * rm
        for _ in range(rs.randint(2, 4)):
            u0, v0, u1, v1 = (rs.rand(4) - 0.5) * 2
            p0 = (px + tx * u0 * hh + ca * v0 * hh, py + ty * u0 * hh + sa * v0 * hh)
            p1 = (px + tx * u1 * hh + ca * v1 * hh, py + ty * u1 * hh + sa * v1 * hh)
            a.line([p0, p1], color, width * 0.9, glow)
        if rs.rand() < 0.35:
            a.circle(px, py, hh * 0.35, outline=color, width=width * 0.7)


def _finish_additive(a):
    out = a.finish(emissive=False, alpha_from_glow=False)
    out[..., 3] = np.clip(out[..., :3].max(-1) * 1.5, 0, 255)
    return out


def circle_pressure(size=256, variant=0):
    a = Art(size, size, ss=2)
    c = size / 2
    S = size / 256
    org, gold, white, copper = (255, 140, 30), (255, 200, 90), (255, 245, 225), (200, 110, 50)
    a.circle(c, c, 124 * S, outline=org, width=2.4 * S)
    a.circle(c, c, 119 * S, outline=gold, width=0.8 * S)
    _rune_band(a, c, c, 104 * S, 117 * S, 36, gold, 3 + variant, width=0.9 * S)
    a.ring_ticks(c, c, 96 * S, 103 * S, 72, org, 0.8 * S)
    # isobar ripples (pressure contour rings, slightly wavy)
    for k, r in enumerate((86, 74, 62)):
        pts = [(c + math.cos(t / 90 * math.tau) * (r + math.sin(t / 90 * math.tau * (6 + k)) * 2.2) * S,
                c + math.sin(t / 90 * math.tau) * (r + math.sin(t / 90 * math.tau * (6 + k)) * 2.2) * S) for t in range(91)]
        a.line(pts, org if k % 2 == 0 else copper, 1.4 * S)
    # gauge sectors / compression arrows
    for i in range(8):
        ang = math.tau * i / 8 + (math.pi / 8 if variant else 0)
        for rr in (50, 40):
            tip = (c + math.cos(ang) * (rr - 8) * S, c + math.sin(ang) * (rr - 8) * S)
            l = (c + math.cos(ang - 0.12) * rr * S, c + math.sin(ang - 0.12) * rr * S)
            rgt = (c + math.cos(ang + 0.12) * rr * S, c + math.sin(ang + 0.12) * rr * S)
            a.line([l, tip, rgt], gold, 1.2 * S)
    for r in (30, 24, 18, 12):
        a.circle(c, c, r * S, outline=org if r % 12 == 0 else gold, width=1.3 * S)
    a.radial_glow(c, c, 22 * S, org, 0.7)
    a.circle(c, c, 6 * S, fill=white)
    if variant == 2:
        for i in range(12):
            ang = math.tau * i / 12
            a.circle(c + math.cos(ang) * 92 * S, c + math.sin(ang) * 92 * S, 5 * S, outline=gold, width=1 * S)
    return _finish_additive(a)


def circle_ice(size=256, variant=0):
    a = Art(size, size, ss=2)
    c = size / 2
    S = size / 256
    cyan, ice, white, sapph = (60, 210, 255), (150, 225, 255), (240, 252, 255), (60, 110, 230)
    a.circle(c, c, 124 * S, outline=cyan, width=2.2 * S)
    _rune_band(a, c, c, 106 * S, 119 * S, 42, ice, 11 + variant, width=0.9 * S)
    a.hexagon(c, c, 102 * S, white, 1.6 * S, rot=0)
    a.hexagon(c, c, 102 * S, cyan, 1.2 * S, rot=30)
    # hexagram
    for rot in (90, -90):
        pts = [(c + math.cos(math.radians(rot + 120 * i)) * 96 * S, c + math.sin(math.radians(rot + 120 * i)) * 96 * S) for i in range(3)]
        a.line(pts + [pts[0]], ice, 1.4 * S)
    for i in range(6):
        ang = math.radians(-90 + 60 * i)
        px, py = c + math.cos(ang) * 70 * S, c + math.sin(ang) * 70 * S
        a.hexagon(px, py, 13 * S, cyan, 1.0 * S)
        a.star6(px, py, 8 * S, white, 0.8 * S)
    a.hexagon(c, c, 48 * S, white, 1.4 * S)
    a.hexagon(c, c, 40 * S, cyan, 1.0 * S, rot=0)
    a.radial_glow(c, c, 30 * S, (80, 200, 255), 0.6)
    a.star6(c, c, 34 * S, white, 2.0 * S)
    a.circle(c, c, 5 * S, fill=white)
    if variant >= 1:
        a.ring_ticks(c, c, 52 * S, 58 * S, 36, ice, 0.8 * S)
    return _finish_additive(a)


def _heart(cx, cy, s):
    pts = []
    for i in range(48):
        t = math.tau * i / 48
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s, cy - y * s))
    return pts


def circle_blood(size=256, variant=0):
    a = Art(size, size, ss=2)
    c = size / 2
    S = size / 256
    red, scarlet, pale, gold = (230, 20, 40), (255, 60, 60), (255, 190, 190), (255, 140, 80)
    a.circle(c, c, 124 * S, outline=red, width=2.4 * S)
    a.circle(c, c, 120 * S, outline=pale, width=0.7 * S)
    _rune_band(a, c, c, 106 * S, 118 * S, 30, scarlet, 21 + variant, width=1.0 * S)
    # gothic rose window: 12 pointed arches around
    for i in range(12):
        ang = math.tau * i / 12
        bx, by = c + math.cos(ang) * 82 * S, c + math.sin(ang) * 82 * S
        tx, ty = -math.sin(ang), math.cos(ang)
        w = 11 * S
        pts = []
        for k in range(13):
            t = k / 12
            # pointed arch in local coords: base at radius 70, apex at radius 100
            r = 70 * S + 30 * S * math.sin(math.pi * t) ** 0.8 * (1.0 if 0.2 < t < 0.8 else 0.85)
            off = (t - 0.5) * 2 * w
            pts.append((c + math.cos(ang) * r + tx * off * (1 - abs(t - 0.5) * 0.4), c + math.sin(ang) * r + ty * off * (1 - abs(t - 0.5) * 0.4)))
        a.line(pts, scarlet, 1.1 * S)
        a.circle(bx, by, 3 * S, outline=pale, width=0.7 * S)
    # vascular branches toward the center
    rs = np.random.RandomState(31 + variant)
    for i in range(10):
        ang = math.tau * i / 10
        x, y = c + math.cos(ang) * 68 * S, c + math.sin(ang) * 68 * S
        pts = [(x, y)]
        for _ in range(9):
            ang2 = math.atan2(c - y, c - x) + (rs.rand() - 0.5) * 0.9
            x += math.cos(ang2) * 4.2 * S
            y += math.sin(ang2) * 4.2 * S
            pts.append((x, y))
        a.line(pts, red, 1.0 * S)
    a.circle(c, c, 40 * S, outline=pale, width=1.2 * S)
    for k in range(8):
        ang = math.tau * k / 8
        a.circle(c + math.cos(ang) * 30 * S, c + math.sin(ang) * 30 * S, 9 * S, outline=scarlet, width=1.0 * S)
    a.radial_glow(c, c, 26 * S, red, 0.7)
    a.poly(_heart(c, c + 1, 1.0 * S), outline=pale, width=1.6 * S)
    if variant == 2:
        a.circle(c, c, 112 * S, outline=gold, width=1.0 * S)
    return _finish_additive(a)


PAINTERS = {"pressure": circle_pressure, "ice": circle_ice, "blood": circle_blood}
