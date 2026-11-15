"""16x16 item icons + pack icons."""
from __future__ import annotations

import os
import sys

from PIL import Image

PAL = {
    ".": None,
    "k": (24, 18, 30), "s": (98, 98, 102), "S": (140, 140, 138), "L": (186, 186, 180), "d": (64, 64, 70),
    "m": (88, 112, 52), "M": (120, 150, 70),
    "r": (110, 34, 38), "R": (160, 52, 48), "o": (255, 110, 40), "y": (255, 200, 110),
    "p": (110, 70, 190), "P": (160, 112, 235), "w": (236, 214, 255), "q": (70, 40, 130),
    "b": (92, 60, 38), "B": (126, 86, 54), "c": (226, 214, 190), "C": (196, 182, 156),
}

ATLAS = [
    "................",
    "..kkkkkkkkkkkk..",
    ".kBBBBBBBBBBBBk.",
    ".kBdddddddddcBk.",
    ".kBdSSSSSSSdcBk.",
    ".kBdSqPPPqSdcBk.",
    ".kBdSPwwPPSdcBk.",
    ".kBdSqPPPqSdcBk.",
    ".kBdSSoRoSSdcBk.",
    ".kBdSrRoRrSdcBk.",
    ".kBdSSSSSSSdcBk.",
    ".kBdddddddddcBk.",
    ".kBBBBBBBBBBBCk.",
    ".kbbbbbbbbbbbCk.",
    "..kkkkkkkkkkkk..",
    "................",
]
LODESTONE = [
    "................",
    "......MMMm......",
    "....mMMmMMMm....",
    "...kmMmMMmMmk...",
    "..kSSLSSSLSSSk..",
    "..kddsddsddsdk..",
    ".kSSSSpPPSSLSSk.",
    ".ksssspwPpssssk.",
    ".kLSSqPwwPqSSSk.",
    ".kdddsqPPqdddsk.",
    ".kSSSSoRoSSSSSk.",
    "..ksssRoRsssskk.",
    "..kddddrddddk...",
    "...krrRrrRrk....",
    "....kkkkkkk.....",
    "................",
]
SHARD = [
    "................",
    ".........k......",
    "........kwk.....",
    ".......kPwPk....",
    "......kPPwPk....",
    "......kPpPwPk...",
    ".....kpPPpPPk...",
    ".....kqpPPpPk...",
    "....kqqpPPpk....",
    "....kqpqpPPk....",
    "...kqqqppPk.....",
    "...kqqqpPk......",
    "...kkqqpk.......",
    "....kkqk........",
    "......k.........",
    "................",
]


# Strata Breaker: a strata-banded stone hammer head with a glowing vein and moss, on a sinew-wrapped haft
STRATA_BREAKER = [
    "................",
    "..kkkkkkkk......",
    ".kMMmMMmMMk.....",
    ".kLSSLSSLSSk....",
    ".kddsddsddsk....",
    ".kSSoyoSSSSk....",
    ".kssRoRsssskk...",
    "..kkkkkkkkrBk...",
    "........krBk....",
    ".......krBk.....",
    "......krRk......",
    ".....krBk.......",
    "....krBk........",
    "...kdsk.........",
    "...kSk..........",
    "....k...........",
]
# Anchorage Greaves: rock-plated boots bound by root fibres, an ember vein down the shin
GREAVES = [
    "................",
    "....kkkk..kkkk..",
    "...kSLSk.kSLSk..",
    "...kdsdk.kdsdk..",
    "...kSoSk.kSoSk..",
    "...kryrk.kryrk..",
    "...kSoSk.kSoSk..",
    "...kbBbk.kbBbk..",
    "...kSSSkkkSSSk..",
    "..kdSLSSkSLSSdk.",
    "..kMmMmmkMmMmmk.",
    "..kkkkkkkkkkkkk.",
    "................",
    "................",
    "................",
    "................",
]


def armor_layer(seed: int = 7) -> Image.Image:
    """64x32 armor texture (layer 1) for the Anchorage Greaves: banded rock plates, moss, root fibres, ember veins.

    Fully opaque so the armor material never cuts holes; the boots geometry samples its leg region.
    """
    import random
    rnd = random.Random(seed)
    img = Image.new("RGBA", (64, 32))
    px = img.load()
    for y in range(32):
        for x in range(64):
            band = (y // 3) % 3
            base = [(140, 140, 138), (98, 98, 102), (120, 120, 118)][band]
            j = rnd.randint(-10, 10)
            c = (base[0] + j, base[1] + j, base[2] + j)
            if (x * 7 + y * 3) % 11 == 0:
                c = (92, 60, 38)  # root fibre
            if y % 8 == 7 and rnd.random() < 0.6:
                c = (88, 112, 52) if rnd.random() < 0.7 else (120, 150, 70)  # moss on the ledges
            if x % 16 in (5, 6) and 18 <= y <= 30 and y % 4 != 0:
                c = (255, 110, 40) if y % 2 else (255, 200, 110)  # ember vein down the shin
            px[x, y] = (max(0, min(255, c[0])), max(0, min(255, c[1])), max(0, min(255, c[2])), 255)
    return img


def icon(rows) -> Image.Image:
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            c = PAL.get(ch)
            if c:
                img.putpixel((x, y), c + (255,))
    return img


def main(rp: str, bp: str, hero: str | None) -> None:
    d = os.path.join(rp, "textures", "items", "anatomy")
    os.makedirs(d, exist_ok=True)
    icon(ATLAS).save(os.path.join(d, "anatomical_atlas.png"))
    icon(LODESTONE).save(os.path.join(d, "restless_lodestone.png"))
    icon(SHARD).save(os.path.join(d, "lithic_heart_shard.png"))
    icon(STRATA_BREAKER).save(os.path.join(d, "strata_breaker.png"))
    icon(GREAVES).save(os.path.join(d, "anchorage_greaves.png"))
    armor_dir = os.path.join(rp, "textures", "models", "armor")
    os.makedirs(armor_dir, exist_ok=True)
    armor_layer().save(os.path.join(armor_dir, "anatomy_anchorage_1.png"))
    # pack icon: crop of the assembled-creature render if available, else the lodestone icon scaled up
    if hero and os.path.exists(hero):
        im = Image.open(hero).convert("RGB")
        w, h = im.size
        s = min(w, h)
        box = ((w - s) // 2 + int(s * 0.06), int(h * 0.12), (w - s) // 2 + s - int(s * 0.06), int(h * 0.12) + s - int(s * 0.12))
        pic = im.crop(box).resize((256, 256), Image.LANCZOS)
    else:
        pic = icon(LODESTONE).resize((256, 256), Image.NEAREST)
    for p in (rp, bp):
        pic.save(os.path.join(p, "pack_icon.png"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
