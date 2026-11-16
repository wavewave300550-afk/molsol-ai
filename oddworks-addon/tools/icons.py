"""Hand-designed 16x16 item icons, procedural particle sprites and the pack icon."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PAL = {
    ".": (0, 0, 0, 0),
    # antler goggles
    "b": (247, 239, 220, 255), "A": (226, 211, 176, 255), "a": (185, 164, 124, 255), "d": (128, 108, 78, 255),
    "e": (58, 46, 36, 255), "G": (255, 196, 72, 255), "g": (255, 241, 176, 255), "s": (107, 74, 46, 255),
    "S": (88, 83, 76, 255), "k": (36, 30, 26, 255),
    # wood / line / metal
    "W": (150, 88, 44, 255), "w": (110, 60, 28, 255), "x": (78, 42, 18, 255), "L": (240, 232, 210, 255),
    "l": (196, 186, 158, 255), "t": (127, 224, 208, 255), "h": (166, 104, 56, 255), "H": (122, 72, 36, 255),
    "B": (214, 176, 80, 255), "P": (96, 54, 26, 255), "o": (122, 130, 146, 255), "O": (84, 90, 104, 255),
    "i": (176, 182, 190, 255), "n": (226, 220, 200, 255),
    # bamboo / steel / cord
    "Y": (226, 205, 116, 255), "y": (184, 160, 74, 255), "N": (94, 75, 28, 255), "M": (120, 96, 52, 255),
    "m": (88, 66, 34, 255), "K": (24, 20, 18, 255), "F": (90, 94, 102, 255), "R": (150, 34, 48, 255),
    "r": (215, 180, 90, 255), "E": (255, 255, 255, 255), "T": (204, 212, 222, 255), "U": (140, 148, 160, 255),
}

GOGGLES = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "..bbbbbbbbbbbb..",
    ".bAAAAAAAAAAAAb.",
    "sAeAAeAAAAeAAeAs",
    "SAgGGGGaaGGGGgAS",
    "SAAAAAAk.kAAAAAS",
    ".aAAAAa...aAAAa.",
    "..dddd.....dddd.",
    "................",
    "................",
    "................",
    "................",
]

HANDLINE = [
    "................",
    "......xWWWx.....",
    ".....xWwwwWx....",
    ".....LLLLLLLn...",
    ".....LlLtLlL.n..",
    ".....LLLLLLL..n.",
    ".....xWwwwWx...n",
    "......xWWWx....n",
    "........hB.....o",
    ".......hB.....oO",
    "......hH......O.",
    ".....hH.......i.",
    "....PH.......ii.",
    "...PP........i..",
    "................",
    "................",
]

HANDLINE_CAST = [
    "...............n",
    "......xWWWx...n.",
    ".....xWwwwWx.n..",
    ".....wlLLLlwn...",
    ".....wLtLtLw....",
    ".....wlLLLlw....",
    ".....xWwwwWx....",
    "......xWWWx.....",
    "........hB......",
    ".......hB.......",
    "......hH........",
    ".....hH.........",
    "....PH..........",
    "...PP...........",
    "................",
    "................",
]


def _diag(colors, start=(1, 14), extra=None):
    """Draw a 2-px thick 45-degree object from bottom-left to top-right; colors[i] = (light, dark)."""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    x0, y0 = start
    for i, (c1, c2) in enumerate(colors):
        x, y = x0 + i, y0 - i
        if 0 <= x < 16 and 0 <= y < 16 and c1:
            px[x, y] = PAL[c1]
        if 0 <= x + 1 < 16 and 0 <= y < 16 and c2:
            px[x + 1, y] = PAL[c2]
    for (x, y), c in (extra or {}).items():
        px[x, y] = PAL[c]
    return img


def cane_icon():
    seq = [("F", "K")]                                   # butt cap of the handle
    seq += [("M", "m"), ("M", "m"), ("N", "N"), ("M", "m"), ("M", "m")]   # smoked handle w/ node
    seq += [("K", "K")]                                  # hairline seam
    seq += [("Y", "y"), ("Y", "y"), ("N", "N"), ("Y", "y"), ("Y", "y"), ("N", "N"), ("Y", "y"), ("Y", "y")]
    seq += [("U", "F")]                                  # iron ferrule
    extra = {(3, 14): "R", (3, 15): "r", (2, 13): "R"}   # silk cord hanging from the handle
    return _diag(seq, start=(0, 15), extra=extra)


def cane_drawn_icon():
    seq = [("F", "K")]
    seq += [("M", "m"), ("M", "m"), ("N", "N"), ("M", "m"), ("M", "m")]
    seq += [("B", "r")]                                  # brass habaki
    seq += [("T", "U")] * 7 + [("T", "E"), ("E", None)]   # blade with bright edge, tip
    extra = {(3, 14): "R", (3, 15): "r", (2, 13): "R"}
    img = _diag(seq, start=(0, 15), extra=extra)
    px = img.load()
    for i in range(7, 14):                               # hamon highlight on the upper edge
        x, y = i, 15 - i
        if (i % 3) == 0:
            px[x, y] = PAL["E"]
    return img


def from_map(rows):
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    assert len(rows) == 16, len(rows)
    for y, row in enumerate(rows):
        assert len(row) == 16, (y, row, len(row))
        for x, ch in enumerate(row):
            px[x, y] = PAL[ch]
    return img


ICONS = {
    "solar_frost_goggles": lambda: from_map(GOGGLES),
    "endless_handline": lambda: from_map(HANDLINE),
    "endless_handline_cast": lambda: from_map(HANDLINE_CAST),
    "bamboo_sword_cane": cane_icon,
    "bamboo_sword_cane_drawn": cane_drawn_icon,
}


# =========================================================================== particle sprites (white, tinted in JSON)

def _canvas(n):
    yy, xx = np.mgrid[0:n, 0:n]
    c = (n - 1) / 2
    return (xx - c) / (n / 2), (yy - c) / (n / 2)


def _img(alpha, n):
    a = np.clip(alpha, 0, 1)
    rgba = np.zeros((n, n, 4), np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def sprite(kind: str) -> Image.Image:
    n = 32
    x, y = _canvas(n)
    r = np.sqrt(x * x + y * y)
    if kind == "dot":
        return _img(np.exp(-(r / 0.45) ** 2), n)
    if kind == "spark":
        star = np.exp(-(np.abs(x) / 0.07) ** 2) * np.exp(-(np.abs(y) / 0.9) ** 2) + \
            np.exp(-(np.abs(y) / 0.07) ** 2) * np.exp(-(np.abs(x) / 0.9) ** 2)
        return _img(star + np.exp(-(r / 0.18) ** 2), n)
    if kind == "ring":
        return _img(np.exp(-((r - 0.78) / 0.07) ** 2), n)
    if kind == "halo":
        n2 = 64
        x2, y2 = _canvas(n2)
        r2 = np.sqrt(x2 * x2 + y2 * y2)
        a = np.exp(-((r2 - 0.86) / 0.045) ** 2) + 0.35 * np.exp(-((r2 - 0.8) / 0.12) ** 2)
        return _img(a, n2)
    if kind == "crescent":
        n2 = 64
        x2, y2 = _canvas(n2)
        r2 = np.sqrt(x2 * x2 + (y2 + 0.15) ** 2)
        band = np.exp(-((r2 - 0.78) / 0.09) ** 2)
        ang = np.arctan2(-(y2 + 0.15), x2)                 # upper arc only
        mask = np.clip(np.sin(ang), 0, 1) ** 0.6
        taper = np.clip(1 - np.abs(x2) ** 3, 0, 1)
        return _img(band * mask * taper * 1.25, n2)
    if kind == "shard":
        a = np.clip(1 - np.abs(x) / (0.28 * (1 - np.abs(y)) + 0.02), 0, 1) * (np.abs(y) < 0.95)
        return _img(a, n)
    if kind == "flake":
        a = np.zeros_like(x)
        for k in range(3):
            th = k * math.pi / 3
            xr = x * math.cos(th) + y * math.sin(th)
            yr = -x * math.sin(th) + y * math.cos(th)
            a = np.maximum(a, np.exp(-(yr / 0.07) ** 2) * (np.abs(xr) < 0.85))
            a = np.maximum(a, np.exp(-((np.abs(yr) - 0.25 * np.abs(xr)) / 0.06) ** 2) * (np.abs(xr) > 0.45) * (np.abs(xr) < 0.7))
        return _img(a, n)
    if kind == "drop":
        a = np.exp(-((x / 0.38) ** 2 + ((y - 0.15) / 0.45) ** 2) ** 2)
        a = np.maximum(a, np.exp(-((x / (0.12 + 0.2 * (y + 0.9))) ** 2)) * (y < 0.1) * (y > -0.85))
        return _img(a, n)
    if kind == "splat":
        rng = np.random.default_rng(5)
        a = np.exp(-(r / 0.5) ** 4)
        for _ in range(7):
            cx, cy, s = rng.uniform(-0.7, 0.7), rng.uniform(-0.7, 0.7), rng.uniform(0.08, 0.2)
            a = np.maximum(a, np.exp(-(((x - cx) ** 2 + (y - cy) ** 2) / s ** 2) ** 2))
        return _img(a, n)
    if kind == "streak":
        return _img(np.exp(-(y / 0.3) ** 2) * np.clip(1 - np.abs(x) ** 4, 0, 1), n)
    if kind == "line":
        return _img(np.exp(-(y / 0.55) ** 2) * (np.abs(x) < 0.98), n)
    if kind == "flare":
        a = np.exp(-(y / 0.06) ** 2) * np.exp(-(x / 0.95) ** 2) + np.exp(-(r / 0.22) ** 2)
        return _img(a, n)
    if kind == "mist":
        rng = np.random.default_rng(9)
        a = np.zeros_like(x)
        for _ in range(9):
            cx, cy, s = rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), rng.uniform(0.3, 0.5)
            a += 0.35 * np.exp(-(((x - cx) ** 2 + (y - cy) ** 2) / s ** 2))
        return _img(a * np.exp(-(r / 0.8) ** 4), n)
    raise KeyError(kind)


SPRITES = ("dot", "spark", "ring", "halo", "shard", "flake", "drop", "splat", "streak", "line", "flare", "mist")


# =========================================================================== pack icon

def pack_icon(renders: list) -> Image.Image:
    """256x256: three item renders on an aurora-tinted night gradient."""
    W = 256
    yy, xx = np.mgrid[0:W, 0:W] / W
    top = np.array([16, 26, 44])
    bottom = np.array([44, 34, 30])
    aurora = np.array([70, 170, 150])
    g = top[None, None] * (1 - yy[..., None]) + bottom[None, None] * yy[..., None]
    band = np.exp(-((yy - 0.25 - 0.08 * np.sin(xx * 6.0)) / 0.08) ** 2)[..., None]
    g = g + aurora[None, None] * band * 0.35
    bg = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert("RGBA")
    # cane laid diagonally behind, goggles up top, reel bottom-right
    goggles, reel, cane = (r.convert("RGBA") for r in renders)
    c = cane.resize((250, 250), Image.LANCZOS).rotate(-38, resample=Image.BICUBIC, expand=False)
    bg.alpha_composite(c, (6, 12))
    bg.alpha_composite(goggles.resize((170, 170), Image.LANCZOS), (8, 2))
    bg.alpha_composite(reel.resize((150, 150), Image.LANCZOS), (104, 100))
    d = ImageDraw.Draw(bg)
    d.rectangle([0, 0, W - 1, W - 1], outline=(214, 186, 120, 255), width=4)
    return bg
