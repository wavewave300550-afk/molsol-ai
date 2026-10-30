"""Procedural 2D art: item icons, particle sprites (sigil, danger ring, runes...), pack icon."""
import math
import random

from PIL import Image, ImageDraw, ImageFilter

PALETTE = {
    ".": None, "K": "120a1e", "W": "ffffff", "w": "c9c2d8",
    "V": "8a4dff", "v": "c9a6ff", "P": "4b1d8a", "C": "38e8ff", "c": "b9fbff", "T": "136a7a",
    "G": "ffd27a", "g": "c98a1a", "R": "ff2a3d", "r": "7a0b14",
    "1": "ff3b3b", "2": "ff9a2e", "3": "ffe14d", "4": "4dff7a", "5": "3de8ff", "6": "4d6bff", "7": "c45bff",
}

ICONS = {
    "resonator": [
        "................",
        "......K..K......",
        ".....KvK.KvK....",
        ".....KVK.KVK....",
        ".....KVK.KVK....",
        ".....KVKKKVK....",
        "......KVVVK.....",
        ".......KVK......",
        "......K1K2K.....",
        ".....K3KWK4K....",
        "......K5K6K.....",
        ".......K7K......",
        ".......KgK......",
        "......KgGgK.....",
        "......KKKKK.....",
        "................",
    ],
    "folded_petal": [
        "................",
        "..........KK....",
        ".........KvvK...",
        "........KvWvK...",
        ".......KvVvK....",
        "......KvVVvK....",
        ".....KvVPVK.....",
        "....KvVPVvK.....",
        "...KvVPVvK......",
        "...KVPVvK.......",
        "..KVPVVK........",
        "..KPVVK.........",
        "..KVVK..........",
        "...KK...........",
        "................",
        "................",
    ],
    "string_of_creation": [
        "................",
        "...........cc...",
        "..........cWWc..",
        ".........C.cc...",
        "........C.......",
        ".......C...CC...",
        "......C...C..C..",
        ".....C...C....C.",
        "....C...C......C",
        "...C...C.......C",
        "..C...C.......C.",
        ".cc..C......CC..",
        "cWWcC.....CC....",
        ".cc..CCCCC......",
        "................",
        "................",
    ],
    "eye_of_the_axis": [
        "................",
        ".....KKKKKK.....",
        "...KKgGGGGgKK...",
        "..KgG......GgK..",
        ".KgG..WWWW..GgK.",
        ".KG..WWRRWW..GK.",
        "KgG.WWRrrRWW.GgK",
        "KG..WRrKKrRW..GK",
        "KG..WRrKKrRW..GK",
        "KgG.WWRrrRWW.GgK",
        ".KG..WWRRWW..GK.",
        ".KgG..WWWW..GgK.",
        "..KgG......GgK..",
        "...KKgGGGGgKK...",
        ".....KKKKKK.....",
        "................",
    ],
}


def _hex(s, a=255):
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def icon(name):
    rows = ICONS[name]
    assert len(rows) == 16 and all(len(r) == 16 for r in rows), name
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if PALETTE[ch]:
                px[x, y] = _hex(PALETTE[ch])
    return img


def spark():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for y in range(16):
        for x in range(16):
            d = math.hypot(x - 7.5, y - 7.5) / 7.5
            if d <= 1:
                px[x, y] = (255, 255, 255, int(255 * (1 - d) ** 1.5))
    return img


def soft_ring(size=64, width=0.08):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c, y - c) / c
            a = max(0.0, 1 - abs(d - 0.9) / width)
            inner = max(0.0, 0.25 * (1 - abs(d - 0.75) / 0.2))
            a = min(1.0, a + inner * (d < 0.95))
            if a > 0:
                px[x, y] = (255, 255, 255, int(255 * a))
    return img


def sigil(size=128):
    S = size * 4
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = S / 2
    gold, violet, white = (255, 214, 122, 255), (196, 120, 255, 255), (255, 255, 255, 255)
    for r, col, w in ((0.48, gold, 10), (0.44, violet, 5), (0.30, gold, 6), (0.12, white, 6)):
        R = r * S
        d.ellipse((c - R, c - R, c + R, c + R), outline=col, width=w)
    pts = [(c + 0.44 * S * math.cos(-math.pi / 2 + k * 2 * math.pi / 7), c + 0.44 * S * math.sin(-math.pi / 2 + k * 2 * math.pi / 7)) for k in range(7)]
    for k in range(7):
        d.line((pts[k], pts[(k + 3) % 7]), fill=white, width=5)
        R = 0.035 * S
        d.ellipse((pts[k][0] - R, pts[k][1] - R, pts[k][0] + R, pts[k][1] + R), fill=gold)
    rnd = random.Random(11)
    for k in range(36):
        a = k * 2 * math.pi / 36
        r0, r1 = 0.355 * S, 0.395 * S
        x0, y0 = c + r0 * math.cos(a), c + r0 * math.sin(a)
        x1, y1 = c + r1 * math.cos(a + rnd.uniform(-0.05, 0.05)), c + r1 * math.sin(a + rnd.uniform(-0.05, 0.05))
        d.line((x0, y0, x1, y1), fill=gold, width=4)
        if k % 3 == 0:
            d.line((x1, y1, c + r1 * math.cos(a + 0.06), c + r1 * math.sin(a + 0.06)), fill=gold, width=4)
    img = img.filter(ImageFilter.GaussianBlur(1.2)).resize((size, size), Image.LANCZOS)
    return img


def danger(size=64):
    S = size * 4
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = S / 2
    d.ellipse((c - 0.47 * S, c - 0.47 * S, c + 0.47 * S, c + 0.47 * S), fill=(255, 40, 40, 70), outline=(255, 60, 60, 255), width=12)
    d.ellipse((c - 0.32 * S, c - 0.32 * S, c + 0.32 * S, c + 0.32 * S), outline=(255, 120, 90, 200), width=5)
    for k in range(12):
        a = k * math.pi / 6
        d.line((c + 0.36 * S * math.cos(a), c + 0.36 * S * math.sin(a), c + 0.45 * S * math.cos(a), c + 0.45 * S * math.sin(a)), fill=(255, 200, 160, 255), width=6)
    return img.resize((size, size), Image.LANCZOS)


def runes():
    """8 glyphs of 8x8 in a 64x8 strip."""
    glyphs = [
        ["..####..", ".#....#.", ".#.##.#.", ".#.##.#.", ".#....#.", "..####..", "...##...", "..####.."],
        ["...##...", "..#..#..", ".#.##.#.", "#..##..#", "...##...", "..####..", ".#....#.", "#......#"],
        ["#......#", ".#....#.", "..#..#..", "...##...", "...##...", "..#..#..", ".######.", "........"],
        ["..####..", ".##..##.", "##.##.##", "#.####.#", "##.##.##", ".##..##.", "..####..", "........"],
        ["....#...", "...###..", "..#.#.#.", ".#..#..#", "....#...", "..#####.", "....#...", "...###.."],
        ["#.#.#.#.", ".#.#.#.#", "........", ".######.", ".#....#.", ".#.##.#.", ".######.", "........"],
        ["...#....", "..###...", ".#####..", "#######.", ".#####..", "..###...", "...#....", "..###..."],
        ["##....##", "#.#..#.#", "#..##..#", "#..##..#", "#.#..#.#", "##....##", "........", ".######."],
    ]
    img = Image.new("RGBA", (64, 8), (0, 0, 0, 0))
    px = img.load()
    for gi, g in enumerate(glyphs):
        for y, row in enumerate(g):
            for x, ch in enumerate(row):
                if ch == "#":
                    px[gi * 8 + x, y] = (255, 255, 255, 255)
    return img


def flash_sprite(size=32):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c, y - c) / c
            if d <= 1:
                px[x, y] = (255, 255, 255, int(255 * (1 - d) ** 0.8))
    return img


def pack_icon():
    S = 256
    img = Image.new("RGBA", (S, S), (8, 4, 18, 255))
    rnd = random.Random(4)
    px = img.load()
    for _ in range(260):
        x, y = rnd.randrange(S), rnd.randrange(S)
        b = rnd.randrange(110, 255)
        px[x, y] = (b, b, min(255, b + 30), 255)
    sg = sigil(220)
    img.alpha_composite(sg, (18, 18))
    d = ImageDraw.Draw(img)
    cols = ["ff3b3b", "ff9a2e", "ffe14d", "4dff7a", "3de8ff", "4d6bff", "c45bff"]
    for k, col in enumerate(cols):
        a = -math.pi / 2 + k * 2 * math.pi / 7
        x, y = 128 + 96 * math.cos(a), 128 + 96 * math.sin(a)
        d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=_hex(col))
    d.text((112, 116), "11", fill=(255, 255, 255, 255))
    big = Image.new("RGBA", (S, S))
    big.alpha_composite(img)
    ic = icon("eye_of_the_axis").resize((96, 96), Image.NEAREST)
    big.alpha_composite(ic, (80, 80))
    return big
