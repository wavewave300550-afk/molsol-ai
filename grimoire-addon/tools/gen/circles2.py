"""Expansion 02 magic circles (additive: black = transparent): Plasma, Darkness, Prism Light.

Each has its own geometry language:
  plasma      - magnetic field lines / confinement rhombus / three braided filaments, white-hot core
  darkness    - nested squares and folding shutters around a hollow (dark) centre, muted jade only
  prism_light - optical bench: a prism, one entering ray, seven dispersed rays, mirrors and lens arcs
"""
import math
import numpy as np
from .art import Art
from .circles import PAINTERS, _finish_additive, _rune_band


def circle_plasma(size=256, variant=0):
    a = Art(size, size, ss=2)
    c = size / 2
    S = size / 256
    vio, mag, uv, white, ind = (176, 60, 255), (255, 70, 210), (120, 80, 255), (255, 236, 255), (80, 60, 240)
    a.circle(c, c, 124 * S, outline=vio, width=2.2 * S)
    _rune_band(a, c, c, 106 * S, 118 * S, 30, mag, 51 + variant, width=0.9 * S)
    # dipole field lines: nested lobes left and right of the core (magnetic confinement)
    for k in range(5):
        r = (16 + k * 11) * S
        for sgn in (-1, 1):
            pts = [(c + sgn * (r + math.cos(t / 60 * math.tau) * r), c + math.sin(t / 60 * math.tau) * r * 0.62) for t in range(61)]
            a.line(pts, uv if k % 2 else vio, 1.0 * S)
    # angular rhombus containment frame
    for r, col in ((92, (200, 200, 220)), (84, vio)):
        a.poly([(c, c - r * S), (c + r * 0.72 * S, c), (c, c + r * S), (c - r * 0.72 * S, c)], outline=col, width=1.4 * S)
    # three braided filaments spiralling into the core
    for f in range(3):
        pts = []
        for t in range(120):
            rr = (78 - t * 0.6) * S
            ang = f * math.tau / 3 + t * 0.09 + (0.5 if variant == 1 else 0)
            pts.append((c + math.cos(ang) * rr, c + math.sin(ang) * rr))
        a.line(pts, mag if f == 1 else vio, 1.3 * S)
    if variant == 2:
        for i in range(6):
            ang = math.tau * i / 6
            x, y = c + math.cos(ang) * 100 * S, c + math.sin(ang) * 100 * S
            a.poly([(x, y - 6 * S), (x + 4 * S, y), (x, y + 6 * S), (x - 4 * S, y)], outline=ind, width=1 * S)
    a.radial_glow(c, c, 26 * S, mag, 0.75)
    a.circle(c, c, 7 * S, fill=white)
    return _finish_additive(a)


def circle_darkness(size=256, variant=0):
    """Dim jade geometry; the centre is a dark hollow (additive black = nothing)."""
    a = Art(size, size, ss=2)
    c = size / 2
    S = size / 256
    jade, deep, faint = (104, 176, 134), (52, 122, 86), (30, 76, 52)
    a.circle(c, c, 124 * S, outline=deep, width=1.6 * S)
    a.circle(c, c, 118 * S, outline=faint, width=0.7 * S)
    # seven overlapping rotated squares (shadow plates)
    for k in range(7):
        ang = k * math.pi / 14 + (0.2 if variant == 1 else 0)
        r = (108 - k * 6) * S
        pts = [(c + math.cos(ang + q * math.pi / 2) * r, c + math.sin(ang + q * math.pi / 2) * r) for q in range(4)]
        a.poly(pts, outline=jade if k % 3 == 0 else deep, width=1.0 * S)
    # erased glyph fragments: broken strokes on a band
    rs = np.random.RandomState(70 + variant)
    for i in range(28):
        ang = math.tau * i / 28
        if rs.rand() < 0.3:
            continue
        r0, r1 = 64 * S, (64 + rs.randint(6, 14)) * S
        a.line([(c + math.cos(ang) * r0, c + math.sin(ang) * r0), (c + math.cos(ang + 0.05) * r1, c + math.sin(ang + 0.05) * r1)], jade, 1.1 * S)
    # hollow eye: layered vertical diamonds; the innermost is left black (absence)
    for i, (w, h) in enumerate(((34, 52), (26, 40), (18, 30))):
        a.poly([(c, c - h * S), (c + w * S, c), (c, c + h * S), (c - w * S, c)], outline=jade if i == 0 else deep, width=1.2 * S)
    if variant == 2:
        for i in range(7):
            ang = math.tau * i / 7
            a.rect(c + math.cos(ang) * 92 * S - 5 * S, c + math.sin(ang) * 92 * S - 5 * S,
                   c + math.cos(ang) * 92 * S + 5 * S, c + math.sin(ang) * 92 * S + 5 * S, outline=jade, width=0.8 * S)
    out = _finish_additive(a)
    return out


def circle_prism_light(size=256, variant=0):
    a = Art(size, size, ss=2)
    c = size / 2
    S = size / 256
    white, champ, glass = (255, 255, 255), (240, 214, 150), (200, 220, 255)
    spectrum = [(255, 52, 52), (255, 140, 34), (255, 232, 52), (64, 255, 100), (52, 132, 255), (92, 68, 255), (180, 68, 255)]
    a.circle(c, c, 124 * S, outline=champ, width=1.8 * S)
    a.ring_ticks(c, c, 112 * S, 120 * S, 84, champ, 0.6 * S)
    a.circle(c, c, 108 * S, outline=glass, width=0.7 * S)
    # seven small mirrors on the rim
    for i in range(7):
        ang = math.tau * i / 7 + (0.22 if variant == 1 else 0)
        x, y = c + math.cos(ang) * 96 * S, c + math.sin(ang) * 96 * S
        tx, ty = -math.sin(ang + 0.6), math.cos(ang + 0.6)
        a.line([(x - tx * 7 * S, y - ty * 7 * S), (x + tx * 7 * S, y + ty * 7 * S)], champ, 1.6 * S)
    # lens arcs
    for sgn in (-1, 1):
        pts = [(c + sgn * (40 + 18 * math.cos(t / 30 * math.pi - math.pi / 2)) * S, c + (t / 30 - 0.5) * 90 * S) for t in range(31)]
        a.line(pts, glass, 1.0 * S)
    # the prism with one white ray in and seven rays out (dispersion)
    tri = [(c, c - 26 * S), (c + 23 * S, c + 14 * S), (c - 23 * S, c + 14 * S)]
    a.poly(tri, outline=white, width=1.4 * S)
    a.line([(c - 104 * S, c - 12 * S), (c - 11 * S, c - 4 * S)], white, 1.6 * S)
    for k, col in enumerate(spectrum):
        ang = -0.42 + k * 0.14
        a.line([(c + 11 * S, c - 2 * S), (c + 11 * S + math.cos(ang) * 92 * S, c - 2 * S + math.sin(ang) * 92 * S)], col, 1.3 * S)
    if variant == 2:
        for r in (54, 70, 86):
            a.circle(c, c, r * S, outline=champ, width=0.5 * S)
    a.radial_glow(c, c, 18 * S, white, 0.5)
    return _finish_additive(a)


PAINTERS.update({"plasma": circle_plasma, "darkness": circle_darkness, "prism_light": circle_prism_light})
