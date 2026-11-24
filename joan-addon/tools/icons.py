"""Item icons (32x32 HD pixel art), the spawn egg and the pack icon."""
from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFilter

from art import fleur_image, fleur_mask

GOLD = (233, 181, 47, 255)
GOLD_DK = (155, 106, 16, 255)
GOLD_HI = (255, 240, 168, 255)
BLUE = (45, 79, 176, 255)
BLUE_DK = (27, 50, 121, 255)
WHITE = (244, 240, 228, 255)
SHADOW = (214, 207, 189, 255)
WOOD = (91, 58, 34, 255)
WOOD_DK = (58, 36, 20, 255)
OUTLINE = (34, 24, 18, 255)


def _outline(im: Image.Image, color=OUTLINE) -> Image.Image:
    px = im.load()
    w, h = im.size
    out = im.copy()
    opx = out.load()
    for y in range(h):
        for x in range(w):
            if px[x, y][3] > 0:
                continue
            if any(0 <= x + dx < w and 0 <= y + dy < h and px[x + dx, y + dy][3] > 0 and px[x + dx, y + dy] != color
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                opx[x, y] = color
    return out


def _paste_fleur(im, x, y, w, h, color, dark=None):
    m = fleur_mask(w, h)
    px = im.load()
    for yy in range(h):
        for xx in range(w):
            if m[yy][xx]:
                px[x + xx, y + yy] = color if (dark is None or yy < h * 0.55) else dark


def banner_icon() -> Image.Image:
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # diagonal pole from bottom-left to top-right
    for i in range(27):
        x, y = 3 + i, 29 - i
        d.point((x, y), WOOD if i % 3 else WOOD_DK)
        d.point((x + 1, y), WOOD_DK)
    for x, y in ((29, 2), (30, 1), (28, 2), (29, 1), (30, 2)):
        d.point((x, y), GOLD)
    d.point((30, 0), GOLD_HI)
    # flag hanging from the upper pole, swallow-tailed, flying left
    flag = [(26, 4), (12, 4), (8, 7), (12, 10), (8, 14), (13, 17), (24, 9)]
    d.polygon(flag, fill=WHITE)
    d.line([(26, 4), (12, 4)], fill=GOLD)
    d.line([(24, 9), (13, 17)], fill=GOLD_DK)
    _paste_fleur(im, 14, 6, 7, 8, GOLD, GOLD_DK)
    for x, y in ((18, 13), (11, 12)):
        d.point((x, y), SHADOW)
    return _outline(im)


def heart_icon() -> Image.Image:
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # flames behind
    for k, (x, h) in enumerate(((10, 10), (16, 14), (22, 10), (13, 8), (19, 8))):
        d.polygon([(x - 3, 24), (x, 24 - h - 6), (x + 3, 24)], fill=(255, 150 - k * 10, 40, 255))
    # heart
    heart = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    hd = ImageDraw.Draw(heart)
    hd.ellipse([7, 9, 17, 19], fill=(196, 32, 44, 255))
    hd.ellipse([15, 9, 25, 19], fill=(196, 32, 44, 255))
    hd.polygon([(7, 15), (25, 15), (16, 27)], fill=(196, 32, 44, 255))
    hd.ellipse([10, 11, 13, 14], fill=(255, 140, 140, 255))
    im.alpha_composite(heart)
    # gold cross of light
    d.line([(16, 13), (16, 22)], fill=GOLD_HI)
    d.line([(13, 16), (19, 16)], fill=GOLD_HI)
    return _outline(im)


def standard_icon() -> Image.Image:
    """Pilgrim's Standard: blue pennant with a gold lily on a short staff (summoning item)."""
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([7, 3, 8, 30], fill=WOOD)
    d.rectangle([6, 1, 9, 3], fill=GOLD)
    d.polygon([(9, 4), (28, 7), (23, 11), (28, 15), (9, 18)], fill=BLUE)
    d.line([(9, 4), (28, 7)], fill=GOLD)
    d.line([(9, 18), (28, 15)], fill=BLUE_DK)
    _paste_fleur(im, 12, 6, 9, 10, GOLD, GOLD_DK)
    return _outline(im)


def spawn_egg() -> Image.Image:
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([7, 3, 25, 29], fill=WHITE)
    d.pieslice([7, 3, 25, 29], 0, 180, fill=BLUE)
    d.ellipse([10, 6, 14, 12], fill=(255, 255, 255, 255))
    _paste_fleur(im, 12, 11, 9, 10, GOLD, GOLD_DK)
    return _outline(im)


def pack_icon() -> Image.Image:
    S = 256
    im = Image.new("RGBA", (S, S), (24, 30, 62, 255))
    d = ImageDraw.Draw(im)
    # radiant road of light
    for i in range(40):
        a = math.radians(-90 + (i - 20) * 4.5)
        d.line([(S / 2, S * 0.95), (S / 2 + math.cos(a) * S, S * 0.95 + math.sin(a) * S)],
               fill=(60 + i % 3 * 10, 80, 150, 255), width=3)
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([S * 0.18, S * 0.1, S * 0.82, S * 0.74], fill=(255, 210, 110, 160))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(28)))
    # winding road (S-curve) of white-blue-gold
    pts = []
    for i in range(60):
        t = i / 59
        x = S * (0.5 + 0.28 * math.sin(t * math.pi * 2.0) * (1 - t))
        y = S * (0.98 - 0.75 * t)
        pts.append((x, y))
    for w, col in ((26, (255, 214, 120, 255)), (16, (190, 225, 255, 255)), (7, (255, 255, 255, 255))):
        d.line(pts, fill=col, width=w, joint="curve")
    fl = fleur_image(120, (255, 222, 120, 255), soft=True)
    im.alpha_composite(fl, (68, 38))
    d.rectangle([4, 4, S - 5, S - 5], outline=(233, 181, 47, 255), width=6)
    return im


ICONS = {
    "banner_of_divine_paths": banner_icon,
    "unburnt_heart": heart_icon,
    "pilgrims_standard": standard_icon,
}
