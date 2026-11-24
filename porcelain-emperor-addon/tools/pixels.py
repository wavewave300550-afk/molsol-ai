"""
Pixel art for the add-on: arena block textures, item icons, the particle
atlas and the pack icon. Everything is generated procedurally and
deterministically so the build is reproducible.
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw, ImageFilter

from modelkit import PAL, fbm, hash01, mix, shade

BLOCK_TEXTURES = (
    "ivory_marble", "marble_tile", "kintsugi_seam", "cracked_marble",
    "vermilion_lacquer", "imperial_roof", "gilded_floor", "seal_tile",
)


def _rgb(c):
    return (c[0], c[1], c[2], 255)


def _marble_px(x, y, seed, base="ivory"):
    n = fbm(x * 0.25 + seed, y * 0.25, seed)
    col = mix(PAL["ivory_hi"], PAL[base], n * 1.2)
    vein = abs(math.sin(x * 0.55 + y * 0.21 + fbm(x * 0.2, y * 0.2, seed + 3) * 5.0))
    if vein < 0.09:
        col = mix(col, PAL["vein"], 0.6)
    return col


def block_texture(name: str) -> Image.Image:
    img = Image.new("RGBA", (16, 16))
    px = img.load()
    seed = sum(ord(c) for c in name)
    for y in range(16):
        for x in range(16):
            if name == "ivory_marble":
                col = _marble_px(x, y, seed)
                # a single fine gold vein crossing the block (gold mineral vein)
                if abs((x * 0.8 + 3) - y - math.sin(x * 0.7) * 1.4) < 0.5 and 2 < x < 14:
                    col = PAL["gold_mid"]
            elif name == "marble_tile":
                col = _marble_px(x, y, seed, "ivory_hi")
                if x == 0 or y == 0:
                    col = shade(PAL["ivory_mid"], -0.05)
                elif x == 15 or y == 15:
                    col = PAL["ivory_lo"]
                elif 5 <= x <= 10 and 5 <= y <= 10 and (x + y) % 5 == 0:
                    col = shade(col, 0.15)
            elif name == "kintsugi_seam":
                t = (math.sin((x + y) * 0.7) + 1) / 2
                col = mix(PAL["gold"], PAL["gold_hi"], t)
                if hash01(x, y, seed) < 0.12:
                    col = PAL["core_hot"]
                if (x + 2 * y) % 9 == 0:
                    col = PAL["gold_mid"]
            elif name == "cracked_marble":
                col = _marble_px(x, y, seed, "ivory_mid")
                if x == 0 or y == 0:
                    col = shade(PAL["ivory_mid"], -0.05)
                elif x == 15 or y == 15:
                    col = PAL["ivory_lo"]
            elif name == "vermilion_lacquer":
                n = fbm(x * 0.3, y * 0.3, seed)
                col = mix(PAL["red_hi"], PAL["red_lo"], n * 1.1)
                # auspicious cloud scroll in gold
                cx, cy = x - 7.5, y - 7.5
                r = math.hypot(cx, cy)
                if abs(r - 4.5) < 0.55 and math.atan2(cy, cx) > -0.4:
                    col = PAL["gold"]
                if abs(math.hypot(cx - 3, cy + 3) - 2) < 0.5:
                    col = PAL["gold_mid"]
            elif name == "imperial_roof":
                row = y // 4
                off = 0 if row % 2 == 0 else 2
                lx = (x + off) % 4
                ly = y % 4
                col = mix(hx_("ffd45a"), hx_("e0a020"), ly / 3)
                if lx == 0:
                    col = hx_("a86c10")
                if ly == 3:
                    col = shade(col, -0.25)
                if ly == 0 and lx in (1, 2):
                    col = hx_("fff0a8")
            elif name == "gilded_floor":
                base = _marble_px(x, y, seed, "ivory_hi")
                n = fbm(x * 0.35, y * 0.35, seed + 9)
                col = mix(base, PAL["gold"], 0.55 + n * 0.45)
                if hash01(x, y, seed) < 0.08:
                    col = PAL["gold_hi"]
            elif name == "seal_tile":
                col = PAL["red"]
                if x in (0, 15) or y in (0, 15):
                    col = PAL["gold"]
                elif x in (1, 14) or y in (1, 14):
                    col = PAL["red_lo"]
                else:
                    # stylised seal-script glyph (symmetric)
                    gx, gy = min(x, 15 - x), y
                    if (gx in (3, 4) and 3 <= gy <= 12) or (gy in (3, 7, 12) and 3 <= gx <= 7) or (gx == 7 and 7 <= gy <= 10):
                        col = PAL["ivory_hi"]
            else:
                raise KeyError(name)
            px[x, y] = _rgb(col)
    if name == "cracked_marble":
        rng = random.Random(seed)
        d = ImageDraw.Draw(img)
        for _ in range(3):
            x0, y0 = rng.randint(2, 13), rng.randint(2, 13)
            pts = [(x0, y0)]
            for _ in range(5):
                x0 = max(0, min(15, x0 + rng.choice((-2, -1, 1, 2))))
                y0 = max(0, min(15, y0 + rng.choice((-2, -1, 1, 2))))
                pts.append((x0, y0))
            d.line(pts, fill=_rgb(PAL["gold_mid"]), width=1)
    return img


def hx_(s):
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)


# --------------------------------------------------------------------------- item icons

def icon(name: str) -> Image.Image:
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    if name == "imperial_seal":
        # square porcelain seal stamp with a coiled dragon knob and a red seal face
        for y in range(16):
            for x in range(16):
                if 3 <= x <= 12 and 9 <= y <= 14:            # seal body
                    col = PAL["ivory"] if x not in (3, 12) else PAL["ivory_lo"]
                    if y == 14:
                        col = PAL["red"]
                    if y == 9:
                        col = PAL["gold"]
                    if (x + y) % 7 == 0 and 4 <= x <= 11 and 10 <= y <= 13:
                        col = PAL["gold_mid"]
                    px[x, y] = _rgb(col)
        knob = ["......xx......",
                "....xxxxx.....",
                "...xx...xx....",
                "...x..o..x....",
                "....xx..xx....",
                ".....xxxx.....",
                "....xxxxxx....",
                "...xxxxxxxx..."]
        for j, row in enumerate(knob):
            for i, ch in enumerate(row):
                if ch == "x":
                    px[i + 1, j + 1] = _rgb(PAL["ivory_hi"] if (i + j) % 3 else PAL["gold"])
                elif ch == "o":
                    px[i + 1, j + 1] = _rgb(PAL["red_hi"])
        for x in (5, 8, 11):
            px[x, 12] = _rgb(PAL["red_lo"])
    elif name == "kintsugi_heart":
        cx, cy = 7.5, 7.0
        for y in range(16):
            for x in range(16):
                dx, dy = (x - cx) / 6.5, (y - cy) / 6.5
                # classic heart implicit curve
                v = (dx * dx + dy * dy - 0.55) ** 3 - dx * dx * (-dy) ** 3 * 1.2
                if v <= 0 and 1 <= y <= 14:
                    col = mix(PAL["ivory_hi"], PAL["ivory_mid"], (y - 2) / 12)
                    if x < cx - 2 and y < 6:
                        col = PAL["ivory_hi"]
                    px[x, y] = _rgb(col)
        crack = [(7, 3), (7, 4), (8, 5), (7, 6), (6, 7), (7, 8), (8, 9), (8, 10), (7, 11), (7, 12)]
        for (x, y) in crack:
            if px[x, y][3]:
                px[x, y] = _rgb(PAL["gold_hi"] if y % 3 else PAL["gold"])
        for (x, y) in ((5, 5), (4, 6), (10, 7), (11, 6)):
            if px[x, y][3]:
                px[x, y] = _rgb(PAL["gold"])
        # outline
        base = img.copy()
        bp = base.load()
        for y in range(16):
            for x in range(16):
                if bp[x, y][3] == 0 and any(0 <= x + a < 16 and 0 <= y + b < 16 and bp[x + a, y + b][3]
                                            for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    px[x, y] = _rgb(PAL["ink"])
    elif name == "mandate_shard":
        pts = [(8, 1), (12, 6), (10, 14), (5, 12), (4, 5)]
        d = ImageDraw.Draw(img)
        d.polygon(pts, fill=_rgb(PAL["ivory_hi"]), outline=_rgb(PAL["gold"]))
        d.line([(8, 3), (7, 7), (9, 11)], fill=_rgb(PAL["gold_hi"]))
    else:
        raise KeyError(name)
    return img


ICONS = ("imperial_seal", "kintsugi_heart", "mandate_shard")


# --------------------------------------------------------------------------- particle atlas

PARTICLE_UV = {
    # name: (u, v, w, h) in a 128x128 atlas
    "dot": (0, 0, 16, 16),
    "spark": (16, 0, 16, 16),
    "chip": (32, 0, 16, 16),
    "flake": (48, 0, 16, 16),
    "ring": (64, 0, 16, 16),
    "petal": (80, 0, 16, 16),
    "seal": (0, 32, 64, 64),
    "crack": (64, 32, 64, 64),
}


def particle_atlas() -> Image.Image:
    S = 128
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    px = img.load()

    def put(x, y, c):
        if 0 <= x < S and 0 <= y < S:
            px[x, y] = c
    # soft dot (white, tinted in game)
    u, v, w, h = PARTICLE_UV["dot"]
    for y in range(h):
        for x in range(w):
            r = math.hypot(x - 7.5, y - 7.5) / 7.5
            a = max(0.0, 1 - r) ** 1.6
            put(u + x, v + y, (255, 255, 255, int(255 * a)))
    # four-point spark
    u, v, w, h = PARTICLE_UV["spark"]
    for y in range(h):
        for x in range(w):
            dx, dy = abs(x - 7.5), abs(y - 7.5)
            a = max(0.0, 1 - (min(dx, dy) * 0.9 + max(dx, dy) * 0.14))
            put(u + x, v + y, (255, 255, 255, int(255 * min(1, a * 1.3))))
    # porcelain chip: white triangle with gold edge (not tinted)
    u, v, w, h = PARTICLE_UV["chip"]
    chip = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(chip)
    d.polygon([(2, 13), (8, 2), (14, 11)], fill=(250, 244, 230, 255), outline=(246, 198, 79, 255))
    d.line([(8, 4), (7, 9), (9, 12)], fill=(217, 154, 38, 255))
    img.paste(chip, (u, v))
    # gold flake
    u, v, w, h = PARTICLE_UV["flake"]
    flake = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(flake)
    d.polygon([(3, 8), (8, 3), (13, 7), (9, 13)], fill=(255, 223, 110, 255), outline=(217, 154, 38, 255))
    d.point([(7, 6), (8, 7)], fill=(255, 250, 220, 255))
    img.paste(flake, (u, v))
    # thin ring
    u, v, w, h = PARTICLE_UV["ring"]
    for y in range(h):
        for x in range(w):
            r = math.hypot(x - 7.5, y - 7.5)
            a = max(0.0, 1 - abs(r - 6.2) / 1.3)
            put(u + x, v + y, (255, 255, 255, int(255 * a)))
    # plum petal (victory)
    u, v, w, h = PARTICLE_UV["petal"]
    petal = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(petal)
    d.ellipse((3, 5, 13, 12), fill=(255, 236, 214, 255), outline=(240, 190, 120, 255))
    d.point([(8, 8)], fill=(246, 198, 79, 255))
    img.paste(petal, (u, v))
    # imperial seal decal: concentric ring, radial ticks and a square seal glyph
    u, v, w, h = PARTICLE_UV["seal"]
    seal = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sp = seal.load()
    for y in range(h):
        for x in range(w):
            dx, dy = x - 31.5, y - 31.5
            r = math.hypot(dx, dy)
            ang = math.atan2(dy, dx)
            a = 0.0
            if 29 <= r <= 31.5:
                a = 1.0
            elif 25.5 <= r <= 26.8:
                a = 0.8
            elif 26.8 < r < 29 and int((ang + math.pi) / (2 * math.pi) * 32) % 2 == 0:
                a = 0.55
            elif r < 25.5:
                a = 0.12 + 0.1 * (1 - r / 25.5)
            sx, sy = abs(dx), abs(dy)
            if max(sx, sy) <= 12 and (max(sx, sy) >= 10.5 or (sx < 1.2 and sy < 8) or (sy < 1.2 and sx < 8)
                                       or (abs(sx - 5) < 1 and abs(sy - 5) < 1)):
                a = 0.95
            if a > 0:
                sp[x, y] = (255, 255, 255, int(255 * a))
    img.paste(seal, (u, v))
    # kintsugi crack decal: jagged gold cracks radiating from the centre
    u, v, w, h = PARTICLE_UV["crack"]
    crack = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(crack)
    rng = random.Random(7)
    for k in range(9):
        ang = k / 9 * math.tau + rng.uniform(-0.2, 0.2)
        x, y = 32.0, 32.0
        pts = [(x, y)]
        for s in range(8):
            ang += rng.uniform(-0.45, 0.45)
            step = rng.uniform(2.5, 4.2)
            x += math.cos(ang) * step
            y += math.sin(ang) * step
            pts.append((x, y))
            if rng.random() < 0.3:
                b = ang + rng.choice((-0.9, 0.9))
                d.line([(x, y), (x + math.cos(b) * 5, y + math.sin(b) * 5)], fill=(255, 230, 140, 220), width=1)
        d.line(pts, fill=(255, 214, 90, 255), width=2)
    crack = crack.filter(ImageFilter.SMOOTH)
    img.paste(crack, (u, v))
    return img


# --------------------------------------------------------------------------- pack icon

def pack_icon(head_render: Image.Image) -> Image.Image:
    S = 256
    bg = Image.new("RGBA", (S, S))
    d = ImageDraw.Draw(bg)
    for y in range(S):
        t = y / S
        c = mix((44, 30, 28, 255), (122, 26, 22, 255), t)
        d.line([(0, y), (S, y)], fill=c)
    # gold kintsugi crack across the background
    rng = random.Random(3)
    x, y = 0.0, 40.0
    pts = [(x, y)]
    while x < S:
        x += rng.uniform(10, 22)
        y += rng.uniform(-14, 14) + 3
        pts.append((x, y))
    d.line(pts, fill=(246, 198, 79, 255), width=4)
    d.ellipse((24, 24, 232, 232), outline=(246, 198, 79, 255), width=5)
    head = head_render.convert("RGBA").resize((236, 236), Image.LANCZOS)
    # drop the preview background colour
    hp = head.load()
    bgc = hp[0, 0]
    for yy in range(head.size[1]):
        for xx in range(head.size[0]):
            c = hp[xx, yy]
            if abs(c[0] - bgc[0]) + abs(c[1] - bgc[1]) + abs(c[2] - bgc[2]) < 12:
                hp[xx, yy] = (0, 0, 0, 0)
    bg.alpha_composite(head, (10, 14))
    return bg
