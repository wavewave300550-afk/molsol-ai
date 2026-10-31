"""
16x16 pixel-art item icons, the particle sprite atlas and the pack icon,
all drawn procedurally.
"""
import math

from PIL import Image, ImageDraw


def _img():
    return Image.new("RGBA", (16, 16), (0, 0, 0, 0))


def _px(img, pts, col):
    for x, y in pts:
        if 0 <= x < 16 and 0 <= y < 16:
            img.putpixel((x, y), col)


def H(s, a=255):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


def art(rows, pal):
    img = _img()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in pal:
                img.putpixel((x, y), H(pal[ch]))
    return img


def outline(img, col="1a1410"):
    out = img.copy()
    c = H(col)
    for y in range(16):
        for x in range(16):
            if img.getpixel((x, y))[3] == 0:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < 16 and 0 <= yy < 16 and img.getpixel((xx, yy))[3] > 0:
                        out.putpixel((x, y), c)
                        break
    return out


ICONS = {}


def icon(fn):
    ICONS[fn.__name__] = fn
    return fn


# ------------------------------------------------------------------ summoning sigils

@icon
def sigil_taotie():
    return outline(art([
        "................",
        "...GG......GG...",
        "...BB......BB...",
        "..BBBBBBBBBBBB..",
        "..bYYbbbbbbYYb..",
        "..BBBBBBBBBBBB..",
        "..BgGBBBBBBGgB..",
        "..BBRRBBBBRRBB..",
        "..BBRRBGGBRRBB..",
        "..BBBBGBBGBBBB..",
        "..BbBBBBBBBBbB..",
        "..BBBBBBBBBBBB..",
        "...bB......Bb...",
        "...BB......BB...",
        "...bb......bb...",
        "................"], {"G": "e0b04a", "g": "8a6a20", "B": "4c6c54", "b": "2b3a2e", "Y": "86c4a7", "R": "e0602a"}))


@icon
def sigil_nidhogg():
    return outline(art([
        "................",
        "..........MG....",
        ".........RRM....",
        "........RRr.....",
        ".......RRr......",
        "......RRr.......",
        ".....RRrG.......",
        "....RRr.........",
        "...RRr..........",
        "..RRrRR.........",
        "..RrR.RR........",
        ".RR....R........",
        ".R......R.......",
        "R...............",
        "................",
        "................"], {"R": "6a4524", "r": "3b2716", "M": "3d5a2a", "G": "7dff6a"}))


@icon
def sigil_hanuman():
    return outline(art([
        "....C..C..C.....",
        "....C..C..C.....",
        "....C..C..C.....",
        "....CCCCCCC.....",
        ".....GGGGG......",
        ".......W........",
        ".......WR.......",
        ".......WR.......",
        ".......W........",
        ".......W........",
        ".......W........",
        ".......W........",
        ".......W........",
        "......GGG.......",
        ".......R........",
        "......R.R......."], {"C": "bfefff", "G": "e8b52c", "W": "6a4524", "R": "c41e2a"}))


@icon
def sigil_alicorn():
    return outline(art([
        "..............W.",
        ".............WC.",
        "............WC..",
        "...........WC...",
        "..........WC....",
        ".........WC.....",
        "........WC......",
        ".......WC.......",
        "......WC........",
        ".....WC.........",
        "....GG..........",
        "...GYG..........",
        "..PGG...........",
        ".PP.............",
        "PP..............",
        "................"], {"W": "ffffff", "C": "a9c6f0", "G": "f2cf5b", "Y": "fff7cf", "P": "c9a2ff"}))


@icon
def sigil_tenko():
    img = _img()
    d = ImageDraw.Draw(img)
    d.ellipse((3, 3, 12, 12), fill=H("bfe9ff"), outline=H("38a8ff"))
    _px(img, [(6, 5), (7, 5), (5, 6), (5, 7)], H("ffffff"))
    _px(img, [(8, 1), (9, 2), (7, 2), (8, 2)], H("38a8ff"))
    _px(img, [(10, 9), (9, 10), (11, 8)], H("1f6fff"))
    return outline(img)


@icon
def sigil_logos():
    return outline(art([
        "................",
        "..GGGGGGGGGGGG..",
        "..GPPPPPPPPPPG..",
        "..GPgpgPgpgPPG..",
        "..GPPPPPPPPPPG..",
        "..GPgPgpgPgPPG..",
        "..GPPPPPPPPPPG..",
        "..GPpgPgPpgPPG..",
        "..GPPPPPPPPPPG..",
        "..GPgpgPpgPPPG..",
        "..GPPPPPPPPPPG..",
        "..GGGGGRRGGGGG..",
        "......RRRR......",
        ".......RR.......",
        "................",
        "................"], {"G": "f3cf5c", "P": "f1e6c8", "g": "b67d1f", "p": "d9a93c", "R": "a3122a"}))


# ------------------------------------------------------------------ trophies (boss cores)

def _gem(c1, c2, c3, glint="ffffff"):
    img = _img()
    pts = [(8, 2), (12, 6), (12, 10), (8, 14), (4, 10), (4, 6)]
    d = ImageDraw.Draw(img)
    d.polygon(pts, fill=H(c2))
    d.polygon([(8, 2), (12, 6), (8, 8), (4, 6)], fill=H(c1))
    d.polygon([(8, 8), (12, 10), (8, 14), (4, 10)], fill=H(c3))
    _px(img, [(7, 4), (6, 5)], H(glint))
    return outline(img)


@icon
def core_taotie():
    return _gem("e0b04a", "4c6c54", "1f2b24", "fff1b8")


@icon
def core_nidhogg():
    return outline(art([
        "................",
        "......WW........",
        ".....WWW........",
        ".....WWW........",
        "....WWWW........",
        "....WWWG........",
        "....WWWG........",
        "...WWWGG........",
        "...WWWGG........",
        "...WWGGG........",
        "..WWWGG.........",
        "..WWGG..........",
        "..WGG...........",
        "..GG............",
        "................",
        "................"], {"W": "e8e1c9", "G": "58e83a"}))


@icon
def core_hanuman():
    return _gem("ffffff", "bfefff", "7fb7d6", "ffffff")


@icon
def core_alicorn():
    return outline(art([
        "...........PP...",
        "..........PWP...",
        ".........PWWP...",
        "........PWWWP...",
        ".......PWWWP....",
        "......PWWWWP....",
        ".....PWWWWP.....",
        "....PWWWWP......",
        "....PWWWP.......",
        "...PWWWP........",
        "...PWWP.........",
        "..PWWP..........",
        "..GGP...........",
        ".GG.............",
        "G...............",
        "................"], {"W": "fbf8ff", "P": "c9a2ff", "G": "f2cf5b"}))


@icon
def core_tenko():
    img = _img()
    d = ImageDraw.Draw(img)
    d.ellipse((4, 6, 11, 14), fill=H("38a8ff"))
    d.polygon([(5, 8), (8, 1), (11, 8)], fill=H("8fd6ff"))
    d.polygon([(7, 9), (8, 5), (9, 9)], fill=H("ffffff"))
    return outline(img)


@icon
def core_logos():
    img = _img()
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 13, 13), fill=H("a3122a"), outline=H("f3cf5c"))
    d.ellipse((5, 5, 10, 10), outline=H("f3cf5c"))
    _px(img, [(7, 7), (8, 7), (7, 8), (8, 8)], H("fff3c4"))
    return outline(img)


@icon
def codex():
    return outline(art([
        "................",
        "..PPPPPPPPPPPP..",
        "..PGGGGGGGGGGP..",
        "..PG.WWWWWW.GP..",
        "..PG.WRRRRW.GP..",
        "..PG.WRWWRW.GP..",
        "..PG.WRRRRW.GP..",
        "..PG.WWWWWW.GP..",
        "..PG..GGGG..GP..",
        "..PG.G.GG.G.GP..",
        "..PG..G..G..GP..",
        "..PG........GP..",
        "..PGGGGGGGGGGP..",
        "..PPPPPPPPPPPP..",
        "...pppppppppp...",
        "................"], {"P": "3a1f5c", "p": "1e0f30", "G": "f3cf5c", "W": "fff3c4", "R": "c8102e"}))


def icon_image(name):
    return ICONS[name]()


# ------------------------------------------------------------------ particle atlas (128x128, 32px cells)

PARTICLE_CELLS = ["dot", "star", "ring", "disc", "rect", "cone", "flame", "feather",
                  "petal", "rune", "cloud", "shard", "glint", "crescent", "drop", "spiral"]


def particle_atlas():
    S = 32
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    for idx, name in enumerate(PARTICLE_CELLS):
        cell = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        px = cell.load()
        for y in range(S):
            for x in range(S):
                u, v = (x + 0.5) / S * 2 - 1, (y + 0.5) / S * 2 - 1
                r = math.hypot(u, v)
                a = 0.0
                if name == "dot":
                    a = max(0.0, 1 - r) ** 1.6
                elif name == "star":
                    a = max(0.0, 1 - r) ** 2 + max(0.0, 1 - abs(u) * 8) * max(0.0, 1 - abs(v)) * 0.8 + \
                        max(0.0, 1 - abs(v) * 8) * max(0.0, 1 - abs(u)) * 0.8
                elif name == "ring":
                    a = max(0.0, 1 - abs(r - 0.9) * 14)
                elif name == "disc":
                    a = 0.0 if r > 1 else (0.42 + (0.58 if r > 0.9 else 0.0))
                elif name == "rect":
                    edge = max(abs(u), abs(v))
                    a = 0.0 if edge > 1 else (1.0 if (abs(u) > 0.9 or abs(v) > 0.96) else 0.38)
                elif name == "cone":
                    # 90-degree sector pointing up (-v), apex at the bottom centre
                    vv = (y + 0.5) / S
                    ang = math.degrees(math.atan2(u, 1 - vv * 1.0 + 1e-6))
                    rr = math.hypot(u, (1 - vv) * 2 - 0) / 2
                    dist = 1 - vv
                    if abs(ang) <= 45 and dist <= 1:
                        edge = abs(abs(ang) - 45) < 3 or dist > 0.95
                        a = 1.0 if edge else 0.38
                elif name == "flame":
                    a = max(0.0, 1 - math.hypot(u * 1.6, (v - 0.3) * 0.9)) ** 1.2
                elif name == "feather":
                    a = 1.0 if abs(u) < 0.32 * (1 - abs(v)) + 0.04 and abs(v) < 0.95 else 0.0
                elif name == "petal":
                    a = 1.0 if (u * u) / 0.35 + (v * v) / 0.9 < 1 and not (v < -0.7 and abs(u) < 0.15) else 0.0
                elif name == "rune":
                    a = 1.0 if (abs(u) < 0.12 or (abs(v + 0.5) < 0.1 and abs(u) < 0.6) or
                                (abs(v - 0.4) < 0.1 and abs(u) < 0.45) or abs(r - 0.85) < 0.06) and r < 0.95 else 0.0
                elif name == "cloud":
                    a = max(0.0, 1 - r) ** 0.8 * 0.85
                elif name == "shard":
                    a = 1.0 if abs(u) < (1 - (v + 1) / 2) * 0.6 and abs(v) < 1 else 0.0
                elif name == "glint":
                    a = max(0.0, 1 - abs(u) * abs(v) * 30 - r * 0.6)
                elif name == "crescent":
                    a = 1.0 if (r < 0.95 and math.hypot(u - 0.35, v) > 0.75) else 0.0
                elif name == "drop":
                    a = 1.0 if math.hypot(u, (v - 0.25) * 1.2) < 0.6 or (abs(u) < (v + 1) * 0.3 and v < 0.3) else 0.0
                elif name == "spiral":
                    ang = math.atan2(v, u)
                    a = max(0.0, 1 - abs(((r * 6 - ang / math.pi) % 2) - 1) * 3) * (1 if r < 1 else 0)
                a = max(0.0, min(1.0, a))
                px[x, y] = (255, 255, 255, int(a * 255))
        img.paste(cell, ((idx % 4) * S, (idx // 4) * S))
    return img


def particle_uv(name):
    i = PARTICLE_CELLS.index(name)
    return [(i % 4) * 32, (i // 4) * 32]


def pack_icon():
    img = Image.new("RGBA", (128, 128), (14, 12, 28, 255))
    d = ImageDraw.Draw(img)
    for r, col in ((60, (40, 26, 70, 255)), (48, (70, 40, 110, 255)), (36, (230, 190, 90, 255)), (30, (20, 16, 36, 255))):
        d.ellipse((64 - r, 64 - r, 64 + r, 64 + r), fill=col)
    for k in range(12):
        a = math.radians(k * 30)
        d.line((64 + math.cos(a) * 38, 64 + math.sin(a) * 38, 64 + math.cos(a) * 58, 64 + math.sin(a) * 58),
               fill=(255, 230, 150, 255), width=3)
    d.ellipse((50, 54, 78, 74), fill=(255, 245, 210, 255))
    d.ellipse((59, 58, 69, 70), fill=(40, 20, 10, 255))
    for k in range(6):
        a = math.radians(k * 60 + 30)
        x, y = 64 + math.cos(a) * 44, 64 + math.sin(a) * 44
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(163, 18, 42, 255))
    return img
