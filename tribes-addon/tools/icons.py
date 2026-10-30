"""Hand-made 16x16 pixel-art item icons, the particle sprite and the pack icon."""
import math

from PIL import Image

PALETTE = {
    ".": None,
    "K": "1d1622",  # outline
    "P": "5b2a86", "p": "8a52c4",              # codex purple
    "Y": "e8b923", "y": "a8740c",              # gold
    "W": "f3eee0", "w": "cfc6b0",              # parchment / bone
    "G": "5bd16a", "g": "2e8a3a",              # green gem
    "A": "2f6bd8",                              # lapis
    "N": "f2cf63",                              # noodle
    "M": "7a3e1d", "m": "4c230e",              # meatball
    "C": "38e8ff", "c": "c9fbff",              # cyan glow
    "T": "d9a441", "t": "a47a2c", "k": "5e3f12", "S": "fff1a0",  # clay tablet
    "R": "eef2f6", "s": "3a3f47", "H": "c9ced6",  # colander metal
    "D": "3b4552", "O": "ff8a2a", "E": "9aa5b1",   # gauntlet
    "r": "c0281b",                              # sauce
    "B": "254a3e",                              # dark scales
}

ICONS = {
    "tribal_codex": [
        "................",
        ".KKKKKKKKKKKK...",
        ".KYPPPPPPPPYKW..",
        ".KPPPPPPPPPPKWw.",
        ".KPPPYYYYPPPKWw.",
        ".KPPYpGApYPPKWw.",
        ".KPPYpNCpYPPKWw.",
        ".KPPPYYYYPPPKWw.",
        ".KPPPPpPPPPPKWw.",
        ".KPPPpYpPPPPKWw.",
        ".KPPPPpPPPPPKWw.",
        ".KPPPPPPPPPPKWw.",
        ".KYPPPPPPPPYKWw.",
        ".KKKKKKKKKKKKWw.",
        "..KwwwwwwwwwwwK.",
        "...KKKKKKKKKKK..",
    ],
    "primal_fang": [
        "................",
        "...........kk...",
        "..........k..k..",
        ".........k....k.",
        "........KK....k.",
        ".......KWWK...k.",
        "......KWWwK..k..",
        ".....KWWwK..k...",
        "....KWWwwK.GG...",
        "...KWWwwK.GggG..",
        "...KWwwK..GgGG..",
        "..KWwwK....GG...",
        "..KWwK..........",
        ".KwwK...........",
        ".KKK............",
        "................",
    ],
    "tablet_of_destinies": [
        "................",
        "...KKKKKKKKKK...",
        "..KAAAAAAAAAAK..",
        "..KATTTSTTTTAK..",
        "..KATTSSSTTTAK..",
        "..KATTTSTTTTAK..",
        "..KATkTkkTkTAK..",
        "..KATTTTTTTTAK..",
        "..KATkkTkTkkAK..",
        "..KATTTTTTTTAK..",
        "..KATkTkkkTTAK..",
        "..KATTTTTTTTAK..",
        "..KATkkTTkkTAK..",
        "..KAttttttttAK..",
        "..KAAAAAAAAAAK..",
        "...KKKKKKKKKK...",
    ],
    "holy_colander": [
        "................",
        ".....N.NN..N....",
        "....N.N..NN.N...",
        "...NMMN.NN..N...",
        "...NMmMN.rNN....",
        ".KKKKKKKKKKKKKK.",
        "KHRRRRRRRRRRRRHK",
        ".KHsHsHsHsHsHHK.",
        "..KHHHHHHHHHHK..",
        "..KHsHsHsHsHHK..",
        "...KHHHHHHHHK...",
        "...KHsHsHsHHK...",
        "....KHHHHHHK....",
        ".....KKKKKK.....",
        "......KDDK......",
        "................",
    ],
    "omni_gauntlet": [
        "................",
        "......KKKK......",
        ".....KRRRRK.....",
        "....KRDDDDRK....",
        "...KRDCccCDRK...",
        "...KRDCccCDRK...",
        "...KRRDDDDRRK...",
        "...KRERRRRERK...",
        "..KRRERRRRERRK..",
        "..KROOOOOOOORK..",
        "..KDDDDDDDDDDK..",
        "..KRRCRRCRRCRK..",
        "..KRRRRRRRRRRK..",
        "...KDKDKDKDKK...",
        "...KDKDKDKDK....",
        "................",
    ],
}


def _hex(s):
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def icon(name: str) -> Image.Image:
    rows = ICONS[name]
    assert len(rows) == 16 and all(len(r) == 16 for r in rows), name
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            col = PALETTE[ch]
            if col:
                px[x, y] = _hex(col)
    return img


def particle_sprite() -> Image.Image:
    """Soft round white sprite; tinted per particle."""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for y in range(16):
        for x in range(16):
            d = math.hypot(x - 7.5, y - 7.5) / 7.5
            if d <= 1:
                a = int(255 * (1 - d) ** 1.4)
                px[x, y] = (255, 255, 255, a)
    return img


def pack_icon(colors=("4f8a3c", "e8b923", "f2cf63", "38e8ff")) -> Image.Image:
    size = 256
    img = Image.new("RGBA", (size, size), (20, 16, 34, 255))
    px = img.load()
    # starfield
    import random
    rnd = random.Random(7)
    for _ in range(140):
        x, y = rnd.randrange(size), rnd.randrange(size)
        b = rnd.randrange(120, 255)
        px[x, y] = (b, b, min(255, b + 20), 255)
    names = ["primal_fang", "tablet_of_destinies", "holy_colander", "omni_gauntlet"]
    for i, n in enumerate(names):
        cx, cy = (i % 2) * 128, (i // 2) * 128
        c = _hex(colors[i])
        for y in range(8, 120):
            for x in range(8, 120):
                d = math.hypot(x - 64, y - 64)
                if 52 <= d <= 58:
                    px[cx + x, cy + y] = c
                elif d < 52:
                    r, g, b, _ = px[cx + x, cy + y]
                    px[cx + x, cy + y] = (int(r * 0.6 + c[0] * 0.15), int(g * 0.6 + c[1] * 0.15), int(b * 0.6 + c[2] * 0.15), 255)
        ic = icon(n).resize((80, 80), Image.NEAREST)
        img.alpha_composite(ic, (cx + 24, cy + 24))
    return img
