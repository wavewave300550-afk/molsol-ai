"""
Pixel-art and vector sprites shared by models, icons and particles.

The fleur-de-lis is drawn as a vector shape at high resolution and reduced to
crisp masks of any size, so the emblem looks identical on the breastplate,
the banner, the particle atlas and the item icons.
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFilter

HI = 512


def _fleur_hi() -> Image.Image:
    """White fleur-de-lis on transparent background, HI x HI."""
    im = Image.new("L", (HI, HI), 0)
    d = ImageDraw.Draw(im)
    S = HI

    def P(x, y):
        return (x * S, y * S)

    # central petal: pointed top, swelling, narrowing into the band
    cp = []
    for i in range(41):
        t = i / 40
        y = 0.04 + t * 0.56
        w = 0.112 * math.sin(math.pi * min(1.0, t * 1.08)) ** 0.9 + 0.012
        if t > 0.85:
            w = max(w, 0.06)
        cp.append((0.5 - w, y))
    right = [(1 - x, y) for x, y in reversed(cp)]
    d.polygon([P(*p) for p in cp + right], fill=255)

    # side petals: tapering strokes along a cubic bezier that sweeps out, up and curls down
    def bez(p0, p1, p2, p3, t):
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t * t
        e = t ** 3
        return (a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1])

    for side in (-1, 1):
        sx = lambda x: 0.5 + side * (x - 0.5)  # noqa: E731
        p0, p1, p2, p3 = (sx(0.53), 0.62), (sx(0.60), 0.20), (sx(1.04), 0.16), (sx(0.90), 0.55)
        left, right = [], []
        n = 60
        for i in range(n + 1):
            t = i / n
            x, y = bez(p0, p1, p2, p3, t)
            x2, y2 = bez(p0, p1, p2, p3, min(1, t + 0.01))
            x1, y1 = bez(p0, p1, p2, p3, max(0, t - 0.01))
            tx, ty = x2 - x1, y2 - y1
            ln = math.hypot(tx, ty) or 1
            nx, ny = -ty / ln, tx / ln
            w = 0.075 * (1 - t) ** 0.7 + 0.016
            left.append((x + nx * w, y + ny * w))
            right.append((x - nx * w, y - ny * w))
        d.polygon([P(*p) for p in left + list(reversed(right))], fill=255)
        d.ellipse([P(p3[0] - 0.022, p3[1] - 0.022), P(p3[0] + 0.022, p3[1] + 0.022)], fill=255)

    # band
    d.rounded_rectangle([P(0.25, 0.60), P(0.75, 0.68)], radius=S * 0.02, fill=255)
    # foot: centre lobe + two small curling lobes
    d.polygon([P(0.43, 0.68), P(0.57, 0.68), P(0.55, 0.84), P(0.5, 0.95), P(0.45, 0.84)], fill=255)
    for side in (-1, 1):
        d.polygon([P(0.5 + side * 0.05, 0.68), P(0.5 + side * 0.22, 0.68), P(0.5 + side * 0.30, 0.80),
                   P(0.5 + side * 0.24, 0.86), P(0.5 + side * 0.13, 0.76)], fill=255)
    return im.filter(ImageFilter.GaussianBlur(S * 0.004))


HAND_FLEURS = {
    (7, 8): ["...#...",
             "..###..",
             "#.###.#",
             "##.#.##",
             ".#####.",
             "#######",
             "..###..",
             ".#.#.#."],
    (9, 10): ["....#....",
              "...###...",
              "...###...",
              "##.###.##",
              "#.#####.#",
              "#..###..#",
              "#########",
              "...###...",
              "..#####..",
              ".#..#..#."],
}


@lru_cache(maxsize=None)
def fleur_mask(w: int, h: int) -> Tuple[Tuple[int, ...], ...]:
    """Binary mask (rows) of a fleur-de-lis fitted in w x h pixels."""
    if (w, h) in HAND_FLEURS:
        return tuple(tuple(1 if c == "#" else 0 for c in r) for r in HAND_FLEURS[(w, h)])
    hi = _fleur_hi()
    bbox = hi.point(lambda v: 255 if v > 40 else 0).getbbox()
    hi = hi.crop(bbox)
    small = hi.resize((w, h), Image.BOX)
    px = small.load()
    rows = []
    for y in range(h):
        rows.append(tuple(1 if px[x, y] > 150 else 0 for x in range(w)))
    # force symmetry for crispness
    sym = []
    for r in rows:
        r = list(r)
        for x in range(w // 2):
            v = max(r[x], r[w - 1 - x])
            r[x] = r[w - 1 - x] = v
        sym.append(tuple(r))
    return tuple(sym)


def fleur_image(size: int, color=(255, 255, 255, 255), outline=None, soft: bool = False) -> Image.Image:
    """RGBA fleur-de-lis sprite. soft=True keeps anti-aliased edges (for particles)."""
    hi = _fleur_hi()
    bbox = hi.point(lambda v: 255 if v > 40 else 0).getbbox()
    hi = hi.crop(bbox)
    w = h = size
    if soft:
        a = hi.resize((w, h), Image.LANCZOS)
        im = Image.new("RGBA", (w, h), color[:3] + (0,))
        im.putalpha(a.point(lambda v: int(v * color[3] / 255)))
        return im
    m = fleur_mask(w, h)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()
    for y in range(h):
        for x in range(w):
            if m[y][x]:
                px[x, y] = color
    if outline:
        out = im.copy()
        opx = out.load()
        for y in range(h):
            for x in range(w):
                if m[y][x]:
                    continue
                if any(0 <= x + dx < w and 0 <= y + dy < h and m[y + dy][x + dx]
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    opx[x, y] = outline
        im = out
    return im


# --------------------------------------------------------------------------- face (14 x 16 HD texels)

FACE_ROWS = [
    "HHHHHHHHHHHHHH",
    "HHHHHHHHHHHHHH",
    "HhHHHhHHhHHHhH",
    "hsshssssssshss",
    "sBBBssssssBBBs",
    "sLLLLssssLLLLs",
    "sWIIWssssWIIWs",
    "sdIIdsnnsdIIds",
    "sssssnnnnsssss",
    "sCCsssNNsssCCs",
    "sCCssNNNNssCCs",
    "sssssssssssss s",
    "ssssmMMMMmssss",
    "sssssmmmmsssss",
    "dsssssssssssd",
    "ddssssssssssdd",
]

FACE_PALETTE = {
    "H": "3d2416",   # hair
    "h": "5a3622",   # hair strand highlight / fringe tips
    "s": "f1c9a9",   # skin
    "d": "dcac8c",   # skin shadow
    "B": "3a2416",   # brow
    "L": "2b1a12",   # upper lash line
    "W": "f5f1ea",   # sclera
    "I": "4f7398",   # iris (blue-grey)
    "n": "e9b898",   # nose bridge light shadow
    "N": "d9a385",   # nose shadow
    "C": "efb4a0",   # cheek blush
    "m": "c77a6f",   # lip
    "M": "a65750",   # lip centre
}


def face_rows() -> List[str]:
    rows = []
    for r in FACE_ROWS:
        r = r.replace(" ", "")
        r = (r + "s" * 14)[:14]
        rows.append(r)
    return rows


# --------------------------------------------------------------------------- tiny 3x5 font for the IHS trigram

GLYPHS = {
    "I": ["###", ".#.", ".#.", ".#.", "###"],
    "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "S": ["###", "#..", "###", "..#", "###"],
}


def text_mask(s: str) -> List[List[int]]:
    rows = [[] for _ in range(5)]
    for i, ch in enumerate(s):
        g = GLYPHS[ch]
        for y in range(5):
            rows[y].extend(1 if c == "#" else 0 for c in g[y])
            if i < len(s) - 1:
                rows[y].append(0)
    return rows


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "fleur_preview.png"
    sheet = Image.new("RGBA", (900, 260), (40, 44, 54, 255))
    x = 10
    for s in (7, 9, 11, 13, 15, 21):
        im = fleur_image(s, (232, 185, 35, 255), outline=(120, 80, 10, 255)).resize((s * 10, s * 10), Image.NEAREST)
        sheet.paste(im, (x, 10), im)
        x += s * 10 + 10
    soft = fleur_image(64, (255, 230, 150, 255), soft=True).resize((192, 192), Image.LANCZOS)
    sheet.paste(soft, (x - 200, 60), soft)
    sheet.save(out)
    print(out)
