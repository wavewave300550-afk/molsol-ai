"""Particle atlas 2 (v1.2): full-colour, anti-aliased sprites for races 004-006, and their
particle effects.  Races 001-003 keep using the original atlas (fx.py) untouched.

Sprites are drawn 8x supersampled and painted in each race's palette (the tint then only
fades them): Xenentoma's ivory and violet, the Flying Spaghetti Monster's marinara and
gold, Nurariten's vermilion, gold and petal pink.  Effects follow one rule - few
particles, clear shapes, a rise-hold-fade rhythm.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

NS = "plrace"
TEX = "textures/plrace/races/particles/particles_ex"
W = H = 256
S = 8                                     # supersampling

CELLS: Dict[str, Tuple[int, int, int, int]] = {}
_ROW0 = ["x_mote", "x_ripple", "x_ring2", "x_drop", "x_shard", "x_star", "x_arc", "f_sparkle"]
_ROW1 = ["f_drop", "f_blob", "f_steam", "f_noodle", "f_crack", "f_ring", "f_loop", "n_spark"]
_ROW2 = ["n_mote", "n_glyph", "n_seal", "n_petal", "n_ring", "n_pillar", "f_crumb", "x_dust"]
for _r, _row in enumerate((_ROW0, _ROW1, _ROW2)):
    for _c, _nm in enumerate(_row):
        CELLS[_nm] = (_c * 32, _r * 32, 32, 32)
CELLS.update({"n_court": (0, 96, 64, 64), "n_gate": (64, 96, 64, 64), "n_fracture": (128, 96, 64, 64),
              "f_spiral": (192, 96, 64, 64), "n_procession": (0, 160, 128, 64), "x_burst": (128, 160, 64, 64)})


# ============================================================================= drawing helpers

def _canvas(w, h):
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def _radial(w, h, stops, cx=0.5, cy=0.5, sx=1.0, sy=1.0):
    """Radial gradient image; stops: [(r (0..1 of the half-size), (r, g, b, a))]."""
    yy, xx = np.mgrid[0:h * S, 0:w * S] + 0.5
    r = np.hypot((xx / (w * S) - cx) / (0.5 * sx), (yy / (h * S) - cy) / (0.5 * sy))
    rs = np.array([s[0] for s in stops])
    cols = np.array([s[1] for s in stops], float)
    out = np.zeros((h * S, w * S, 4))
    for ch in range(4):
        out[..., ch] = np.interp(r, rs, cols[:, ch])
    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA")


def _glow(im, radius):
    return im.filter(ImageFilter.GaussianBlur(radius * S))


def _over(*layers):
    out = layers[0]
    for la in layers[1:]:
        out = Image.alpha_composite(out, la)
    return out


def _tint(im, rgb, alpha=1.0):
    """Recolour a drawn shape (keeps its alpha)."""
    a = np.array(im)[..., 3].astype(float) * alpha
    out = np.zeros(a.shape + (4,), np.uint8)
    out[..., :3] = rgb
    out[..., 3] = a.clip(0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def _P(w, h, pts):
    return [(x * w * S, y * h * S) for x, y in pts]


def _line(d, w, h, pts, col, width):
    d.line(_P(w, h, pts), fill=col, width=max(1, int(width * w * S)), joint="curve")
    r = width * w * S / 2
    for x, y in _P(w, h, [pts[0], pts[-1]]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)


def _circle(d, w, h, cx, cy, r, fill=None, outline=None, width=0.0):
    R = r * w * S
    x, y = cx * w * S, cy * h * S
    d.ellipse([x - R, y - R, x + R, y + R], fill=fill, outline=outline, width=int(width * w * S) if width else 0)


def _star(w, h, col, ray=0.48, waist=0.07, cx=0.5, cy=0.5, rot=0.0, n=4):
    im, d = _canvas(w, h)
    pts = []
    for k in range(n * 2):
        ang = math.radians(rot) + k * math.pi / n
        rr = ray if k % 2 == 0 else waist
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    d.polygon(_P(w, h, pts), fill=col)
    return im


def _teardrop(w, h, body, rim, inner, hi, cy=0.62, r=0.24, tip=0.14):
    im, d = _canvas(w, h)
    for col, grow in ((rim, 0.035), (body, 0.0)):
        rr = r + grow
        d.polygon(_P(w, h, [(0.5, tip - grow), (0.5 - rr * 0.92, cy - rr * 0.3), (0.5 + rr * 0.92, cy - rr * 0.3)]), fill=col)
        _circle(d, w, h, 0.5, cy, rr, fill=col)
    _circle(d, w, h, 0.47, cy - 0.03, r * 0.62, fill=inner)
    _circle(d, w, h, 0.41, cy - 0.06, r * 0.22, fill=hi)
    _circle(d, w, h, 0.6, cy + 0.1, r * 0.09, fill=hi[:3] + (150,))
    return im


def _noodle(d, w, h, pts, scale=1.0):
    _line(d, w, h, pts, (150, 98, 26, 255), 0.17 * scale)
    _line(d, w, h, pts, (236, 190, 84, 255), 0.12 * scale)
    _line(d, w, h, [(x - 0.012, y - 0.02) for x, y in pts], (255, 238, 176, 255), 0.045 * scale)


# ============================================================================= sprites

def _sprite(name: str, w: int, h: int) -> Image.Image:
    if name == "x_mote":
        core = _radial(w, h, [(0, (255, 255, 255, 255)), (0.14, (246, 236, 255, 255)), (0.32, (196, 166, 255, 190)),
                              (0.62, (140, 100, 230, 60)), (1.0, (120, 80, 220, 0))])
        cross = _tint(_star(w, h, (255, 255, 255, 255), ray=0.46, waist=0.03), (226, 210, 255), 0.55)
        return _over(core, cross)
    if name in ("x_ripple", "x_ring2", "n_ring"):
        im, d = _canvas(w, h)
        col = (232, 218, 255, 255) if name != "n_ring" else (255, 228, 150, 255)
        _circle(d, w, h, 0.5, 0.5, 0.42, outline=col, width=0.055)
        if name == "x_ring2":
            _circle(d, w, h, 0.5, 0.5, 0.25, outline=col[:3] + (170,), width=0.04)
        glow = _tint(_glow(im, 1.2), (176, 140, 255) if name != "n_ring" else (255, 190, 80), 0.9)
        return _over(glow, im)
    if name == "x_drop":
        return _teardrop(w, h, (214, 228, 198, 236), (140, 160, 126, 255), (232, 242, 222, 236), (255, 255, 255, 240))
    if name == "x_shard":
        im, d = _canvas(w, h)
        poly = [(0.5, 0.08), (0.86, 0.42), (0.62, 0.92), (0.18, 0.6)]
        d.polygon(_P(w, h, poly), fill=(236, 228, 214, 224))
        _line(d, w, h, [poly[3], poly[0], poly[1]], (255, 255, 255, 255), 0.05)
        _line(d, w, h, [poly[1], poly[2], poly[3]], (168, 156, 140, 230), 0.04)
        _line(d, w, h, [(0.5, 0.22), (0.47, 0.5), (0.52, 0.78)], (150, 118, 214, 220), 0.045)
        return im
    if name == "x_star":
        glow = _tint(_glow(_star(w, h, (255, 255, 255, 255), ray=0.42, waist=0.12), 1.6), (180, 140, 255), 1.0)
        core = _star(w, h, (255, 255, 255, 255), ray=0.47, waist=0.06)
        dot = _radial(w, h, [(0, (255, 255, 255, 255)), (0.18, (255, 255, 255, 255)), (0.3, (220, 200, 255, 0)), (1, (0, 0, 0, 0))])
        return _over(glow, core, dot)
    if name == "x_arc":
        im, d = _canvas(w, h)
        for k in range(40):
            t = k / 39
            ang = math.radians(200 + 140 * t)
            r = 0.36
            x, y = 0.5 + math.cos(ang) * r, 0.62 + math.sin(ang) * r
            th = 0.02 + 0.07 * math.sin(math.pi * t)
            a = int(255 * math.sin(math.pi * t) ** 0.6)
            _circle(d, w, h, x, y, th, fill=(236, 224, 255, a))
        glow = _tint(_glow(im, 1.0), (170, 130, 255), 0.9)
        return _over(glow, im)
    if name in ("f_sparkle", "n_spark"):
        gold = (255, 206, 96) if name == "f_sparkle" else (255, 226, 140)
        glow = _tint(_glow(_star(w, h, (255, 255, 255, 255), ray=0.4, waist=0.1), 1.4), gold, 1.0)
        core = _star(w, h, (255, 248, 222, 255), ray=0.46 if name == "f_sparkle" else 0.4, waist=0.05)
        diag = _tint(_star(w, h, (255, 255, 255, 255), ray=0.24, waist=0.04, rot=45), (255, 240, 200), 0.8)
        return _over(glow, diag, core)
    if name == "f_drop":
        return _teardrop(w, h, (196, 38, 24, 255), (112, 18, 14, 255), (226, 70, 44, 255), (255, 236, 226, 255))
    if name == "f_blob":
        im, d = _canvas(w, h)
        for (cx, cy, r) in ((0.5, 0.55, 0.27), (0.18, 0.3, 0.07), (0.82, 0.36, 0.09), (0.74, 0.86, 0.06), (0.22, 0.82, 0.05)):
            _circle(d, w, h, cx, cy, r + 0.03, fill=(112, 18, 14, 255))
            _circle(d, w, h, cx, cy, r, fill=(196, 38, 24, 255))
            _circle(d, w, h, cx - r * 0.15, cy - r * 0.15, r * 0.6, fill=(226, 70, 44, 255))
            _circle(d, w, h, cx - r * 0.38, cy - r * 0.38, r * 0.24, fill=(255, 236, 226, 255))
        return im
    if name == "f_steam":
        im, d = _canvas(w, h)
        for k in range(16):
            t = k / 15
            x = 0.5 + 0.18 * math.sin(t * math.pi * 2.0)
            y = 0.86 - 0.7 * t
            _circle(d, w, h, x, y, 0.07 + 0.1 * t, fill=(255, 255, 255, 120))
        return _tint(_glow(im, 1.6), (252, 248, 240), 0.95)
    if name == "f_noodle":
        im, d = _canvas(w, h)
        pts = [(0.12 + 0.76 * k / 20, 0.5 + 0.2 * math.sin(k / 20 * math.pi * 2.2)) for k in range(21)]
        _noodle(d, w, h, pts)
        return im
    if name == "f_loop":
        im, d = _canvas(w, h)
        pts = [(0.5 + 0.3 * math.cos(a), 0.52 + 0.24 * math.sin(a) + 0.04 * math.sin(3 * a))
               for a in np.linspace(0, 2 * math.pi * 1.04, 40)]
        _noodle(d, w, h, pts, 0.9)
        return im
    if name == "f_crack":
        im, d = _canvas(w, h)
        d.polygon(_P(w, h, [(0.2, 0.8), (0.5, 0.44), (0.82, 0.16), (0.56, 0.54)]), fill=(255, 214, 110, 255))
        _line(d, w, h, [(0.3, 0.7), (0.74, 0.24)], (255, 252, 230, 255), 0.04)
        glow = _tint(_glow(im, 1.4), (255, 190, 70), 0.9)
        return _over(glow, im)
    if name == "f_crumb":
        im, d = _canvas(w, h)
        d.polygon(_P(w, h, [(0.25, 0.35), (0.6, 0.2), (0.82, 0.55), (0.55, 0.82), (0.2, 0.66)]), fill=(150, 98, 40, 255))
        d.polygon(_P(w, h, [(0.3, 0.38), (0.58, 0.26), (0.7, 0.45), (0.4, 0.5)]), fill=(214, 168, 92, 255))
        return im
    if name == "f_ring":
        im, d = _canvas(w, h)
        _circle(d, w, h, 0.5, 0.5, 0.38, outline=(112, 18, 14, 255), width=0.1)
        _circle(d, w, h, 0.5, 0.5, 0.38, outline=(204, 44, 28, 255), width=0.06)
        for k in range(7):
            a = k * 2 * math.pi / 7 + 0.4
            _circle(d, w, h, 0.5 + math.cos(a) * 0.46, 0.5 + math.sin(a) * 0.46, 0.035 + 0.015 * (k % 2),
                    fill=(204, 44, 28, 255))
        return im
    if name == "n_mote":
        return _radial(w, h, [(0, (255, 255, 255, 255)), (0.16, (255, 248, 222, 255)), (0.36, (255, 214, 120, 180)),
                              (0.7, (240, 170, 60, 40)), (1.0, (240, 160, 40, 0))])
    if name == "n_glyph":
        im, d = _canvas(w, h)
        col = (255, 236, 168, 255)
        _circle(d, w, h, 0.5, 0.5, 0.44, outline=col, width=0.04)
        for stroke in ([(0.5, 0.16), (0.24, 0.42)], [(0.5, 0.16), (0.78, 0.42)], [(0.38, 0.46), (0.62, 0.46)],
                       [(0.3, 0.56), (0.68, 0.56), (0.68, 0.7), (0.62, 0.72)], [(0.47, 0.56), (0.47, 0.86)]):
            _line(d, w, h, stroke, col, 0.075)
        glow = _tint(_glow(im, 1.3), (255, 180, 60), 1.0)
        return _over(glow, im)
    if name == "n_seal":
        im, d = _canvas(w, h)
        d.rounded_rectangle(_P(w, h, [(0.12, 0.12), (0.88, 0.88)]), radius=0.08 * w * S, fill=(196, 40, 30, 255))
        d.rounded_rectangle(_P(w, h, [(0.2, 0.2), (0.8, 0.8)]), radius=0.04 * w * S, outline=(255, 240, 226, 255),
                            width=int(0.035 * w * S))
        white = (255, 244, 232, 255)
        for y, x0, x1 in ((0.33, 0.32, 0.68), (0.5, 0.36, 0.64), (0.67, 0.3, 0.7)):
            _line(d, w, h, [(x0, y), (x1, y)], white, 0.065)
        _line(d, w, h, [(0.5, 0.33), (0.5, 0.67)], white, 0.065)
        return im
    if name == "n_petal":
        im, d = _canvas(w, h)
        d.ellipse(_P(w, h, [(0.28, 0.1), (0.72, 0.9)]), fill=(255, 214, 226, 255))
        d.ellipse(_P(w, h, [(0.36, 0.52), (0.64, 0.9)]), fill=(244, 160, 188, 255))
        d.polygon(_P(w, h, [(0.44, 0.08), (0.5, 0.2), (0.56, 0.08)]), fill=(0, 0, 0, 0))
        im = im.rotate(-24, resample=Image.BICUBIC)
        return im
    if name == "n_pillar":
        yy, xx = np.mgrid[0:h * S, 0:w * S] + 0.5
        u = xx / (w * S) - 0.5
        v = yy / (h * S)
        a = np.exp(-(u / 0.16) ** 2) * np.clip(np.minimum(v / 0.2, (1 - v) / 0.35), 0, 1)
        core = np.exp(-(u / 0.05) ** 2) * np.clip(np.minimum(v / 0.2, (1 - v) / 0.35), 0, 1)
        out = np.zeros(a.shape + (4,))
        out[..., 0] = 255
        out[..., 1] = 226 + 29 * core
        out[..., 2] = 150 + 105 * core
        out[..., 3] = 255 * np.clip(a * 0.85 + core * 0.3, 0, 1)
        return Image.fromarray(out.astype(np.uint8), "RGBA")
    if name == "x_dust":
        return _radial(w, h, [(0, (238, 228, 214, 200)), (0.4, (228, 216, 200, 140)), (1.0, (220, 206, 190, 0))])
    if name == "n_court":
        im, d = _canvas(w, h)
        col = (255, 230, 160, 255)
        _circle(d, w, h, 0.5, 0.5, 0.46, outline=col, width=0.022)
        _circle(d, w, h, 0.5, 0.5, 0.38, outline=col, width=0.014)
        _circle(d, w, h, 0.5, 0.5, 0.2, outline=col, width=0.014)
        for k in range(24):
            a = k * math.pi / 12
            r0 = 0.38 if k % 6 == 0 else 0.4
            _line(d, w, h, [(0.5 + math.cos(a) * r0, 0.5 + math.sin(a) * r0), (0.5 + math.cos(a) * 0.46, 0.5 + math.sin(a) * 0.46)],
                  col, 0.012 if k % 6 else 0.02)
        for k in range(8):
            a = k * math.pi / 4
            rr = 0.36 if k % 2 == 0 else 0.27
            _line(d, w, h, [(0.5 + math.cos(a) * 0.2, 0.5 + math.sin(a) * 0.2), (0.5 + math.cos(a) * rr, 0.5 + math.sin(a) * rr)],
                  col, 0.012)
        for k in range(4):
            a = k * math.pi / 2 + math.pi / 4
            cx, cy = 0.5 + math.cos(a) * 0.42, 0.5 + math.sin(a) * 0.42
            d.polygon(_P(w, h, [(cx, cy - 0.04), (cx + 0.03, cy), (cx, cy + 0.04), (cx - 0.03, cy)]), fill=col)
        glow = _tint(_glow(im, 1.6), (255, 186, 70), 1.0)
        return _over(glow, im)
    if name == "n_gate":
        im, d = _canvas(w, h)
        col = (255, 244, 214, 255)
        for x in (0.27, 0.73):
            d.polygon(_P(w, h, [(x - 0.035, 0.3), (x + 0.035, 0.3), (x + 0.045, 0.95), (x - 0.045, 0.95)]), fill=col)
        d.polygon(_P(w, h, [(0.04, 0.1), (0.2, 0.15), (0.8, 0.15), (0.96, 0.1), (0.94, 0.16), (0.8, 0.21), (0.2, 0.21),
                            (0.06, 0.16)]), fill=col)
        d.rectangle(_P(w, h, [(0.14, 0.32), (0.86, 0.37)]), fill=col)
        d.rectangle(_P(w, h, [(0.47, 0.2), (0.53, 0.33)]), fill=col)
        inner = _radial(w, h, [(0, (255, 236, 170, 120)), (0.5, (255, 214, 120, 50)), (1.0, (255, 200, 90, 0))],
                        cy=0.62, sx=0.5, sy=0.62)
        glow = _tint(_glow(im, 1.8), (255, 190, 80), 1.0)
        return _over(inner, glow, im)
    if name == "n_fracture":
        im, d = _canvas(w, h)
        rng = np.random.default_rng(6)
        col = (255, 252, 236, 255)

        def branch(x, y, ang, length, width, depth):
            for _ in range(3):
                nx = x + math.cos(ang) * length / 3
                ny = y + math.sin(ang) * length / 3
                _line(d, w, h, [(x, y), (nx, ny)], col, width)
                x, y = nx, ny
                ang += rng.uniform(-0.5, 0.5)
                width *= 0.8
            if depth > 0:
                branch(x, y, ang + 0.6, length * 0.55, width, depth - 1)
                branch(x, y, ang - 0.5, length * 0.5, width, depth - 1)
        for k in range(6):
            branch(0.5, 0.5, k * math.pi / 3 + rng.uniform(-0.3, 0.3), 0.26, 0.03, 1)
        glow = _tint(_glow(im, 1.5), (255, 200, 90), 1.0)
        return _over(glow, im)
    if name == "f_spiral":
        im, d = _canvas(w, h)
        pts = []
        for k in range(120):
            t = k / 119
            a = t * 2.2 * 2 * math.pi
            r = 0.05 + 0.38 * t
            pts.append((0.5 + math.cos(a) * r, 0.5 + math.sin(a) * r))
        _noodle(d, w, h, pts, 0.42)
        glow = _tint(_glow(im, 1.2), (255, 200, 90), 0.6)
        return _over(glow, im)
    if name == "n_procession":
        im, d = _canvas(w, h)
        white = (255, 255, 255, 255)

        def person(x, tall=1.0, hat=False):
            _circle(d, w, h, x, (0.42 - 0.1 * tall) , 0.016, fill=white)
            d.polygon(_P(w, h, [(x - 0.018, 0.46 - 0.1 * tall), (x + 0.018, 0.46 - 0.1 * tall), (x + 0.03, 0.86), (x - 0.03, 0.86)]),
                      fill=white)
            _line(d, w, h, [(x - 0.012, 0.85), (x - 0.02, 0.97)], white, 0.008)
            _line(d, w, h, [(x + 0.012, 0.85), (x + 0.02, 0.97)], white, 0.008)
            if hat:
                d.rectangle(_P(w, h, [(x - 0.006, 0.2 - 0.1 * tall), (x + 0.006, 0.31 - 0.1 * tall)]), fill=white)
        for k, x in enumerate((0.06, 0.16, 0.3, 0.42, 0.56, 0.7, 0.84, 0.95)):
            person(x, 1.0 if k % 3 else 0.9, hat=k % 2 == 0)
            if k in (1, 6):               # nobori banners
                _line(d, w, h, [(x + 0.03, 0.05), (x + 0.03, 0.9)], white, 0.007)
                d.rectangle(_P(w, h, [(x + 0.033, 0.07), (x + 0.07, 0.42)]), fill=white)
            if k == 4:                    # a parasol
                _line(d, w, h, [(x + 0.03, 0.12), (x + 0.03, 0.6)], white, 0.007)
                d.polygon(_P(w, h, [(x - 0.04, 0.2), (x + 0.03, 0.06), (x + 0.1, 0.2)]), fill=white)
        d.rectangle(_P(w, h, [(0.27, 0.38), (0.46, 0.66)]), fill=white)          # the palanquin
        d.polygon(_P(w, h, [(0.25, 0.4), (0.365, 0.26), (0.48, 0.4)]), fill=white)
        _line(d, w, h, [(0.22, 0.56), (0.51, 0.56)], white, 0.012)
        return im
    if name == "x_burst":
        im, d = _canvas(w, h)
        for k in range(12):
            a = k * math.pi / 6 + (0.12 if k % 2 else 0)
            r0, r1 = (0.16, 0.46) if k % 2 == 0 else (0.22, 0.36)
            _line(d, w, h, [(0.5 + math.cos(a) * r0, 0.5 + math.sin(a) * r0), (0.5 + math.cos(a) * r1, 0.5 + math.sin(a) * r1)],
                  (240, 230, 255, 255), 0.02)
        glow = _tint(_glow(im, 1.2), (170, 130, 255), 1.0)
        return _over(glow, im)
    raise KeyError(name)


def atlas() -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for name, (x, y, w, h) in CELLS.items():
        sp = _sprite(name, w, h).resize((w, h), Image.LANCZOS)
        img.alpha_composite(sp, (x, y))
    return img


# ============================================================================= effects

def _uv(name):
    x, y, w, h = CELLS[name]
    return {"texture_width": W, "texture_height": H, "uv": [x, y], "uv_size": [w, h]}


def _uv_pick(names):
    """One of several same-row sprites per particle (by random)."""
    x0, y0, w, h = CELLS[names[0]]
    return {"texture_width": W, "texture_height": H,
            "uv": [f"{x0} + math.floor(variable.particle_random_3 * {len(names)}) * {w}", y0], "uv_size": [w, h]}


def grad(stops, interp="v.particle_age / v.particle_lifetime"):
    return {"gradient": {str(k): v for k, v in stops}, "interpolant": interp}


def effect(ident: str, material: str, comps: dict) -> dict:
    return {"format_version": "1.10.0", "particle_effect": {
        "description": {"identifier": f"{NS}:{ident}",
                        "basic_render_parameters": {"material": material, "texture": TEX}},
        "components": comps}}


def burst(n, life="0.1"):
    return {"minecraft:emitter_rate_instant": {"num_particles": n},
            "minecraft:emitter_lifetime_once": {"active_time": life}}


def bb(size, uv, mode="lookat_xyz"):
    return {"minecraft:particle_appearance_billboard": {"size": size, "facing_camera_mode": mode, "uv": uv}}


AGE = "(v.particle_age / v.particle_lifetime)"
FADE = f"math.clamp((1 - {AGE}) * 3, 0, 1)"                         # hold, then fade over the last third
IN_OUT = f"math.clamp(math.min({AGE} * 6, (1 - {AGE}) * 2.5), 0, 1)"  # quick rise, hold, soft fade
POP = f"(1 + 0.35 * math.max(0, 1 - {AGE} * 5))"                     # a little pop on arrival


def particles() -> Dict[str, dict]:
    P: Dict[str, dict] = {}

    def add(name, material, comps):
        P[name] = effect(name, material, comps)

    alpha = lambda e: {"color": ["1", "1", "1", e]}    # noqa: E731 - sprites carry their own colour

    # ------------------------------------------------------------------ 004 Xenentoma: ivory, violet, silence
    add("sensilla_mote", "particles_add", {**burst(2), "minecraft:emitter_shape_sphere": {"radius": 0.12, "direction": "outwards"},
        "minecraft:particle_initial_speed": 0.12, "minecraft:particle_lifetime_expression": {"max_lifetime": "1.0 + variable.particle_random_1 * 0.6"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.2, 0], "linear_drag_coefficient": 1.6},
        **bb([f"0.07 * {IN_OUT}", f"0.07 * {IN_OUT}"], _uv("x_mote")),
        "minecraft:particle_appearance_tinting": alpha("0.9")})
    add("sensilla_ripple", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.55},
        **bb([f"0.1 + {AGE} * 0.7", f"0.1 + {AGE} * 0.7"], _uv("x_ripple")),
        "minecraft:particle_appearance_tinting": alpha(f"(1 - {AGE}) * 0.9")})
    add("vibration_ping", "particles_add", {"minecraft:emitter_rate_instant": {"num_particles": 2},
        "minecraft:emitter_lifetime_once": {"active_time": 0.1}, "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "0.9 + v.particle_random_1 * 0.25"},
        **bb([f"0.3 + {AGE} * (1.5 + v.particle_random_2)", f"0.3 + {AGE} * (1.5 + v.particle_random_2)"], _uv("x_ring2"),
             "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": alpha(f"(1 - {AGE}) * (1 - {AGE})")})
    add("vibration_trace", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.7},
        **bb([f"0.15 + {AGE} * 0.9", f"0.15 + {AGE} * 0.9"], _uv("x_ripple"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": alpha(f"(1 - {AGE}) * 0.55")})
    add("molt_fluid", "particles_blend", {**burst(4), "minecraft:emitter_shape_sphere": {"radius": 0.35},
        "minecraft:particle_initial_speed": 0.25, "minecraft:particle_lifetime_expression": {"max_lifetime": 0.9},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -5.0, 0]},
        **bb(["0.06", f"0.06 + math.min({AGE} * 0.08, 0.04)"], _uv("x_drop")),
        "minecraft:particle_appearance_tinting": alpha(FADE), "minecraft:particle_appearance_lighting": {}})
    add("chitin_shards", "particles_blend", {**burst(14), "minecraft:emitter_shape_box": {"half_dimensions": [0.3, 0.8, 0.3], "direction": "outwards"},
        "minecraft:particle_initial_speed": "1.6 + variable.particle_random_1 * 1.4", "minecraft:particle_lifetime_expression": {"max_lifetime": 1.2},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -9, 0], "linear_drag_coefficient": 0.6},
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_1 * 360", "rotation_rate": "200 + variable.particle_random_2 * 300"},
        **bb(["0.13", "0.13"], _uv("x_shard")),
        "minecraft:particle_appearance_tinting": alpha(FADE), "minecraft:particle_appearance_lighting": {}})
    add("surge_strike", "particles_add", {"minecraft:emitter_rate_instant": {"num_particles": 7},
        "minecraft:emitter_lifetime_once": {"active_time": 0.1}, "minecraft:emitter_shape_sphere": {"radius": 0.15, "direction": "outwards"},
        "minecraft:particle_initial_speed": "1.8 + v.particle_random_1 * 1.2", "minecraft:particle_lifetime_expression": {"max_lifetime": 0.4},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 5},
        "minecraft:particle_initial_spin": {"rotation": "v.particle_random_2 * 90", "rotation_rate": 0},
        **bb([f"0.16 * {FADE} * {POP}", f"0.16 * {FADE} * {POP}"], _uv("x_star")),
        "minecraft:particle_appearance_tinting": alpha("1")})

    # ------------------------------------------------------------------ 005 Flying Spaghetti Monster: marinara and gold
    add("sauce_drip", "particles_blend", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_initial_speed": 0.0, "minecraft:particle_lifetime_expression": {"max_lifetime": 1.0},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, f"-7 * math.clamp({AGE} * 4 - 0.6, 0, 1)", 0]},
        **bb([f"0.07", f"0.07 + math.clamp({AGE} * 4 - 0.4, 0, 1) * 0.03"], _uv("f_drop")),
        "minecraft:particle_appearance_tinting": alpha(FADE), "minecraft:particle_appearance_lighting": {}})
    add("sauce_splash", "particles_blend", {**burst(12), "minecraft:emitter_shape_sphere": {"radius": 0.45, "direction": "outwards"},
        "minecraft:particle_initial_speed": "1.6 + variable.particle_random_1 * 1.4", "minecraft:particle_lifetime_expression": {"max_lifetime": 0.8},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -9, 0], "linear_drag_coefficient": 0.8},
        "minecraft:particle_initial_spin": {"rotation": "v.particle_random_2 * 360", "rotation_rate": 0},
        **bb(["0.075 + v.particle_random_3 * 0.04", "0.075 + v.particle_random_3 * 0.04"], _uv_pick(["f_drop", "f_blob"])),
        "minecraft:particle_appearance_tinting": alpha(FADE), "minecraft:particle_appearance_lighting": {}})
    add("sauce_spiral", "particles_blend", {"minecraft:emitter_rate_steady": {"spawn_rate": 26, "max_particles": 26},
        "minecraft:emitter_lifetime_once": {"active_time": 0.6}, "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.1},
        "minecraft:particle_initial_speed": 0.0,
        "minecraft:particle_motion_parametric": {"relative_position": [
            "math.cos(v.particle_age * 480 + v.particle_random_1 * 360) * (0.35 + v.particle_age * 0.45)",
            "v.particle_age * 1.5",
            "math.sin(v.particle_age * 480 + v.particle_random_1 * 360) * (0.35 + v.particle_age * 0.45)"]},
        **bb([f"0.07 * {IN_OUT}", f"0.07 * {IN_OUT}"], _uv("f_drop")),
        "minecraft:particle_appearance_tinting": alpha("1"), "minecraft:particle_appearance_lighting": {}})
    add("dente_crack", "particles_blend", {**burst(9), "minecraft:emitter_shape_sphere": {"radius": 0.6, "direction": "outwards"},
        "minecraft:particle_initial_speed": 1.3, "minecraft:particle_lifetime_expression": {"max_lifetime": 0.75},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -8, 0]},
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_1 * 360", "rotation_rate": 280},
        **bb(["0.1", "0.1"], _uv("f_crack")),
        "minecraft:particle_appearance_tinting": alpha(FADE)})
    add("pasta_steam", "particles_blend", {**burst(2), "minecraft:emitter_shape_sphere": {"radius": 0.35},
        "minecraft:particle_initial_speed": 0.15, "minecraft:particle_lifetime_expression": {"max_lifetime": "1.6 + v.particle_random_1 * 0.6"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.5, 0], "linear_drag_coefficient": 1.4},
        "minecraft:particle_initial_spin": {"rotation": "v.particle_random_2 * 40 - 20", "rotation_rate": "v.particle_random_3 * 30 - 15"},
        **bb([f"(0.16 + {AGE} * 0.22)", f"(0.2 + {AGE} * 0.3)"], _uv("f_steam")),
        "minecraft:particle_appearance_tinting": alpha(f"{IN_OUT} * 0.55")})
    add("pasta_vortex", "particles_blend", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.7},
        "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 420},
        **bb([f"0.8 + {AGE} * 3.2", f"0.8 + {AGE} * 3.2"], _uv("f_spiral"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": alpha(f"(1 - {AGE}) * 0.95")})
    add("sauce_wave", "particles_blend", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.7},
        **bb([f"0.6 + {AGE} * 10", f"0.6 + {AGE} * 10"], _uv("f_ring"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": alpha(f"(1 - {AGE})")})
    add("meatball_trail", "particles_blend", {"minecraft:emitter_rate_steady": {"spawn_rate": 14, "max_particles": 16},
        "minecraft:emitter_lifetime_looping": {"active_time": 1}, "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.55},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -5, 0]},
        **bb(["0.06", "0.07"], _uv("f_drop")),
        "minecraft:particle_appearance_tinting": alpha(FADE), "minecraft:particle_appearance_lighting": {}})
    add("noodle_strand", "particles_blend", {
        "minecraft:emitter_rate_instant": {"num_particles": 18}, "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.7},
        "minecraft:particle_initial_speed": 0,
        "minecraft:particle_initial_spin": {"rotation": "v.particle_random_2 * 360", "rotation_rate": 0},
        "minecraft:particle_motion_parametric": {"relative_position": [
            "v.dx * (v.particle_random_1) * math.sin(math.min(v.particle_age / 0.35, 1) * 90) * (v.particle_age < 0.35 ? 1 : (1 - (v.particle_age - 0.35) / 0.35))",
            "v.dy * (v.particle_random_1) * (v.particle_age < 0.35 ? 1 : (1 - (v.particle_age - 0.35) / 0.35)) + math.sin(v.particle_random_1 * 900) * 0.12",
            "v.dz * (v.particle_random_1) * math.sin(math.min(v.particle_age / 0.35, 1) * 90) * (v.particle_age < 0.35 ? 1 : (1 - (v.particle_age - 0.35) / 0.35))"]},
        **bb(["0.16", "0.16"], _uv("f_noodle")),
        "minecraft:particle_appearance_tinting": alpha("1"), "minecraft:particle_appearance_lighting": {}})

    # ------------------------------------------------------------------ 006 Nurariten: gold, vermilion, petals
    add("royal_mote", "particles_add", {**burst(2), "minecraft:emitter_shape_sphere": {"radius": 0.5},
        "minecraft:particle_initial_speed": 0.04, "minecraft:particle_lifetime_expression": {"max_lifetime": "1.8 + variable.particle_random_1"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.12, 0], "linear_drag_coefficient": 1.0},
        **bb([f"0.07 * {IN_OUT}", f"0.07 * {IN_OUT}"], _uv("n_mote")), "minecraft:particle_appearance_tinting": alpha("0.85")})
    add("decree_burst", "particles_add", {**burst(8), "minecraft:emitter_shape_sphere": {"radius": 0.3, "direction": "outwards"},
        "minecraft:particle_initial_speed": 1.1, "minecraft:particle_lifetime_expression": {"max_lifetime": 1.0},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 2.6},
        "minecraft:particle_initial_spin": {"rotation": "v.particle_random_2 * 30 - 15", "rotation_rate": 0},
        **bb([f"0.2 * {IN_OUT} * {POP}", f"0.2 * {IN_OUT} * {POP}"], _uv("n_glyph")), "minecraft:particle_appearance_tinting": alpha("1")})
    add("procession_shadow", "particles_alpha", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 3.2},
        "minecraft:particle_motion_parametric": {"relative_position": ["v.particle_age * 0.45 - 0.7", 0, 0]},
        **bb(["1.6", "0.8"], _uv("n_procession"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#00140c10"), (0.2, "#78140c10"), (0.8, "#78140c10"), (1.0, "#00140c10")])}})
    add("court_pillar", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.1},
        "minecraft:particle_motion_parametric": {"relative_position": [0, "v.particle_age * 0.5", 0]},
        **bb(["0.3", f"1.6 * {IN_OUT}"], _uv("n_pillar"), "lookat_y"),
        "minecraft:particle_appearance_tinting": alpha("0.9")})
    add("court_ring", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.3},
        "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 12},
        **bb(["v.size * 0.5", "v.size * 0.5"], _uv("n_court"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": alpha(f"{IN_OUT} * 0.9")})
    add("judgment_seal", "particles_blend", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.6},
        **bb([f"(0.25 + v.stacks * 0.12) * {POP}", f"(0.25 + v.stacks * 0.12) * {POP}"], _uv("n_seal")),
        "minecraft:particle_appearance_tinting": alpha(FADE)})
    add("arrival_gate", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.0},
        **bb([f"2.4 * (0.85 + 0.15 * math.min({AGE} * 4, 1))", f"2.4 * (0.85 + 0.15 * math.min({AGE} * 4, 1))"], _uv("n_gate")),
        "minecraft:particle_appearance_tinting": alpha(IN_OUT)})
    add("gate_shadow", "particles_alpha", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 2.4},
        **bb(["3.2", "3.2"], _uv("n_gate"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#00a07818"), (0.3, "#80a07818"), (1.0, "#00a07818")])}})
    add("sky_fracture", "particles_add", {**burst(10), "minecraft:emitter_shape_disc": {"radius": 7.0, "plane_normal": "y"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "1.2 + variable.particle_random_1"},
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_2 * 360", "rotation_rate": 6},
        **bb(["1.2 + v.particle_random_3 * 1.4", "1.2 + v.particle_random_3 * 1.4"], _uv("n_fracture")),
        "minecraft:particle_appearance_tinting": alpha(IN_OUT)})
    add("heaven_ring", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.8},
        "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 20},
        **bb([f"2 + {AGE} * 16", f"2 + {AGE} * 16"], _uv("n_court"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": alpha(f"(1 - {AGE})")})
    add("seal_converge", "particles_blend", {
        "minecraft:emitter_rate_instant": {"num_particles": 12}, "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.8},
        "minecraft:particle_initial_speed": 0,
        "minecraft:particle_motion_parametric": {"relative_position": [
            "v.dx * math.clamp(v.particle_age / 0.6 - v.particle_random_1 * 0.4, 0, 1)",
            "v.dy * math.clamp(v.particle_age / 0.6 - v.particle_random_1 * 0.4, 0, 1)",
            "v.dz * math.clamp(v.particle_age / 0.6 - v.particle_random_1 * 0.4, 0, 1)"]},
        **bb(["0.2", "0.2"], _uv("n_seal")), "minecraft:particle_appearance_tinting": alpha(FADE)})
    add("dissolve_light", "particles_blend", {**burst(18), "minecraft:emitter_shape_box": {"half_dimensions": [1.4, 1.0, 1.4]},
        "minecraft:particle_initial_speed": 0.2, "minecraft:particle_lifetime_expression": {"max_lifetime": "1.4 + variable.particle_random_1"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.1, 0], "linear_drag_coefficient": 1.0},
        "minecraft:particle_initial_spin": {"rotation": "v.particle_random_2 * 360", "rotation_rate": "v.particle_random_3 * 160 - 80"},
        **bb([f"0.11 * {IN_OUT}", f"0.11 * {IN_OUT}"], _uv("n_petal")), "minecraft:particle_appearance_tinting": alpha("1")})
    return P


RACE_PARTICLES = ("sensilla_mote", "sensilla_ripple", "vibration_ping", "vibration_trace", "molt_fluid", "chitin_shards",
                  "surge_strike", "sauce_drip", "sauce_splash", "sauce_spiral", "dente_crack", "pasta_steam", "pasta_vortex",
                  "sauce_wave", "meatball_trail", "noodle_strand", "royal_mote", "decree_burst", "procession_shadow",
                  "court_pillar", "court_ring", "judgment_seal", "arrival_gate", "gate_shadow", "sky_fracture",
                  "heaven_ring", "seal_converge", "dissolve_light")
