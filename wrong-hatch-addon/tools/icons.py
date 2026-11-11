"""Pixel-art item icons (16x16), the particle sprite atlas and the pack icon."""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

C = {
    "o": (60, 40, 25, 255),      # outline
    "w": (246, 240, 228, 255),   # shell white
    "c": (232, 214, 176, 255),   # cream feather
    "d": (196, 172, 128, 255),   # dark cream
    "g": (255, 196, 46, 255),    # gold
    "h": (255, 246, 190, 255),   # hot gold
    "G": (214, 130, 18, 255),    # deep gold
    "r": (201, 35, 43, 255),     # red
    "y": (246, 190, 60, 255),    # yolk
    "s": (150, 150, 162, 255),   # steel grey
    "k": (40, 30, 26, 255),      # dark handle
    "n": (120, 140, 60, 255),    # rotten green
    ".": (0, 0, 0, 0),
}

ICONS = {
    "guillotine_pinion": [
        "............ow..",
        "...........owwo.",
        "..........owcwo.",
        ".........owcwo..",
        "........owcwo...",
        ".......owcdo....",
        "......owcdo.....",
        ".....owcdo......",
        "..o.owcdo.......",
        "..ogocdo........",
        "...oggo.........",
        "...okgo.........",
        "..oko.oo........",
        ".oko............",
        ".oo.............",
        "................",
    ],
    "golden_yolk": [
        "................",
        "......oooo......",
        "....oowwwwoo....",
        "...owwwwwwwwo...",
        "..owwwoooowwwo..",
        "..owwoyyyyowwo..",
        ".owwoyhhyyyowwo.",
        ".owwoyhyyyyowwo.",
        ".owwoyyyyyGowwo.",
        ".owwoyyyyGGowwo.",
        "..owwoyyGGowwo..",
        "..owwwoooowwwo..",
        "...owwwwwwwwo...",
        "....oowwwwoo....",
        "......oooo......",
        "................",
    ],
    "eggshell_plate": [
        "................",
        "....ooooo.......",
        "...owwwwwoo.....",
        "..owwwwwwwwoo...",
        "..owwgwwwwwwwo..",
        ".owwwwgwwwwwwo..",
        ".owwwwwgwwwwwwo.",
        ".owwwwwwggwwwwo.",
        "..owwwwwwwgwwwo.",
        "..owwwwwwwwgwo..",
        "...owwwwwwwwwo..",
        "...oowwwwwwwo...",
        ".....oowwwwo....",
        ".......oooo.....",
        "................",
        "................",
    ],
    "hatch_core": [
        "................",
        ".......oo.......",
        "......owwo......",
        "..oo.owggwo.oo..",
        "..owoogggggowo..",
        "...owghhhhgwo...",
        "...oghhhhhhgo...",
        ".oowghhhhhhgwoo.",
        ".owgghhhhhhggwo.",
        "..oowghhhhgwoo..",
        "....oghhhhgo....",
        "...owggggggwo...",
        "..owoowggwoowo..",
        "..oo..owwo..oo..",
        ".......oo.......",
        "................",
    ],
    "suspicious_egg": [
        "................",
        "......oooo......",
        ".....owwwwo.....",
        "....owwwwwwo....",
        "...owwwgwwwwo...",
        "...owwwwgwwwo...",
        "..owwwwwggwwwo..",
        "..owwwwgwwgwwo..",
        "..owwwgwwwwgwo..",
        "..owwwwwwwwwwo..",
        "..owwdwwwwdwwo..",
        "...owwwwwwwwo...",
        "...owdwwwdwwo...",
        "....owwwwwwo....",
        ".....oooooo.....",
        "................",
    ],
    "spawn_egg": [
        "................",
        "......oooo......",
        ".....owwwwo.....",
        "....owrrrrwo....",
        "...owwrrrrwwo...",
        "...owwwwwwwwo...",
        "..owwgggwwwwwo..",
        "..owghhhgwwwwo..",
        "..owghhhgwwwwo..",
        "..owwgggwwwgwo..",
        "..owwwwwwwgwwo..",
        "...owwwwwgwwo...",
        "...owwwwwwwwo...",
        "....owyywwwo....",
        ".....oooooo.....",
        "................",
    ],
}


def icon(name: str) -> Image.Image:
    rows = ICONS[name]
    img = Image.new("RGBA", (16, 16))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            img.putpixel((x, y), C[ch])
    return img


# particle atlas: 64x64, 16x16 cells
PARTICLE_UV = {
    "spark": (0, 0), "feather": (16, 0), "shard": (32, 0), "puff": (48, 0),
    "star": (0, 16), "ring": (16, 16), "drop": (32, 16), "flare": (48, 16),
}


def particle_atlas() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # spark: soft round dot (white, tinted by particle colour)
    for r in range(7, 0, -1):
        a = int(255 * (1 - r / 8) ** 0.6)
        d.ellipse((8 - r, 8 - r, 8 + r - 1, 8 + r - 1), fill=(255, 255, 255, a))
    # feather: diagonal vane
    for i in range(12):
        x, y = 18 + i, 13 - i
        d.line((x - 2, y + 1, x + 1, y - 2), fill=(255, 255, 255, 255))
    d.line((17, 15, 30, 2), fill=(200, 200, 200, 255))
    # shard: angular eggshell chip
    d.polygon([(34, 3), (45, 2), (47, 9), (40, 14), (35, 11)], fill=(255, 255, 255, 255), outline=(170, 160, 140, 255))
    # puff: blobby cloud
    for (cx, cy, r) in ((54, 9, 5), (58, 7, 4), (52, 6, 3), (59, 11, 3)):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 200))
    # star: 4 point star
    d.polygon([(8, 17), (10, 23), (16, 24), (10, 25), (8, 31), (6, 25), (0, 24), (6, 23)], fill=(255, 255, 255, 255))
    # ring
    d.ellipse((17, 17, 30, 30), outline=(255, 255, 255, 255), width=2)
    # drop
    d.ellipse((36, 22, 44, 30), fill=(255, 255, 255, 255))
    d.polygon([(40, 17), (44, 25), (36, 25)], fill=(255, 255, 255, 255))
    # flare: big glow
    for r in range(8, 0, -1):
        a = int(255 * (1 - r / 9) ** 1.4)
        d.ellipse((56 - r, 24 - r, 56 + r - 1, 24 + r - 1), fill=(255, 255, 255, a))
    return img


def pack_icon(render_img: Image.Image) -> Image.Image:
    bg = Image.new("RGB", (256, 256), (32, 26, 22))
    d = ImageDraw.Draw(bg)
    for r in range(128, 0, -4):
        c = int(40 + 90 * (1 - r / 128) ** 2)
        d.ellipse((128 - r, 120 - r, 128 + r, 120 + r), fill=(c + 30, int(c * 0.75), int(c * 0.2)))
    im = render_img.convert("RGBA").resize((236, 236))
    # white background -> transparent
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if r > 248 and g > 248 and b > 248:
                px[x, y] = (0, 0, 0, 0)
    bg.paste(im, (10, 14), im)
    _ = math
    return bg
