"""
Material tiers and texture painters.

Every painter is deterministic: noise comes from a hash of the texel's
quantised model-space position, so the 21 textures rebuild bit-identically.

Historical finishes (from the research dossier) drive the Iron tier, which is
the "museum" variant: bright steel blades, blued rapier hilt with silver-wire
grip, blackened Zweihänder hilt with black leather grip and ricasso, katana with
hamon, iron tsuba, shakudō fittings and dark-blue ito.  Other tiers adapt those
same parts to Minecraft's materials.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np

RGBA = Tuple[int, int, int, int]


def hx(s: str, a: int = 255) -> RGBA:
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


def mix(a: RGBA, b: RGBA, t: float) -> RGBA:
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(4))  # type: ignore


def shade(c: RGBA, f: float) -> RGBA:
    return mix(c, (255, 255, 255, c[3]), f) if f >= 0 else mix(c, (0, 0, 0, c[3]), -f)


def hash01(*vals) -> float:
    h = 2166136261
    for v in vals:
        h ^= (int(v) & 0xFFFFFFFF)
        h = (h * 16777619) & 0xFFFFFFFF
        h ^= h >> 13
        h = (h * 1274126177) & 0xFFFFFFFF
    return (h & 0xFFFFFF) / float(0x1000000)


def tnoise(t, salt=0, density=8.0) -> float:
    """Per-texel stable noise from the texel's model position."""
    q = np.floor(t.p * density + 1e-4).astype(int)
    return hash01(q[0], q[1], q[2], salt, ord(t.face[0]))


def ramp(cols, t) -> RGBA:
    """Piecewise-linear colour ramp over [0,1]."""
    t = max(0.0, min(1.0, t))
    n = len(cols) - 1
    i = min(n - 1, int(t * n))
    return mix(cols[i], cols[i + 1], t * n - i)


# ----------------------------------------------------------------------------- tiers

@dataclass
class Tier:
    key: str
    name: str
    blade: Tuple[RGBA, RGBA, RGBA, RGBA]   # dark, mid, light, highlight
    kind: str                               # wood | stone | metal | gem


TIERS: Dict[str, Tier] = {
    "wooden": Tier("wooden", "Wooden", (hx("5c4127"), hx("8a6a3f"), hx("a9875a"), hx("c4a574")), "wood"),
    "stone": Tier("stone", "Stone", (hx("4e4e52"), hx("77777b"), hx("97979b"), hx("b3b3b6")), "stone"),
    "copper": Tier("copper", "Copper", (hx("7b3c22"), hx("b4613b"), hx("d98a5c"), hx("f3b98f")), "metal"),
    "iron": Tier("iron", "Iron", (hx("6e7680"), hx("a8b0b9"), hx("d2d8de"), hx("f4f7fa")), "metal"),
    "golden": Tier("golden", "Golden", (hx("9c6a12"), hx("d9a520"), hx("f2d054"), hx("fff4a8")), "metal"),
    "diamond": Tier("diamond", "Diamond", (hx("1a7c79"), hx("2fbfb6"), hx("6ee8df"), hx("d4fffb")), "gem"),
    "netherite": Tier("netherite", "Netherite", (hx("241f22"), hx("3d3539"), hx("594e53"), hx("7d7276")), "metal"),
}
TIER_ORDER = ["wooden", "stone", "copper", "iron", "golden", "diamond", "netherite"]

# fittings palettes (dark, mid, light, highlight)
METALS = {
    "blued": (hx("141b2c"), hx("26334f"), hx("3d5277"), hx("8ea3c7")),
    "blackened": (hx("161616"), hx("2a2a2b"), hx("444446"), hx("7a7a7e")),
    "steel": (hx("5d646c"), hx("8d959e"), hx("bcc3ca"), hx("e8ecf0")),
    "silver": (hx("7c8188"), hx("b9bec4"), hx("dfe3e7"), hx("ffffff")),
    "gilt": (hx("8a5e10"), hx("c79422"), hx("efc94e"), hx("fff0a0")),
    "bronze": (hx("5a3a1c"), hx("8d5e2c"), hx("b88446"), hx("e2b675")),
    "copper": (hx("6e3a20"), hx("a35a36"), hx("cc8257"), hx("eab089")),
    "shakudo": (hx("0f0f12"), hx("202027"), hx("33333d"), hx("5c5c6a")),
    "shibuichi": (hx("4a4e52"), hx("6d7276"), hx("92979b"), hx("c2c6c9")),
    "iron_russet": (hx("231a15"), hx("3a2c22"), hx("54402f"), hx("7a5f46")),
    "netherite": (hx("1c181a"), hx("2e282b"), hx("463d41"), hx("6c6166")),
    "wood_dark": (hx("2e1f12"), hx("4a3320"), hx("644730"), hx("82603f")),
    "wood_light": (hx("6d5232"), hx("9b7a4b"), hx("b8966a"), hx("d2b48a")),
    "stone_dark": (hx("2c2b2e"), hx("444347"), hx("5d5c61"), hx("7d7c82")),
    "stone": (hx("525256"), hx("737377"), hx("929296"), hx("b0b0b4")),
}
LEATHER = {
    "black": (hx("100d0c"), hx("1f1916"), hx("2f2622"), hx("473a33")),
    "brown": (hx("2f1d10"), hx("4f321b"), hx("6c4626"), hx("8a5c34")),
    "red": (hx("3d0d0f"), hx("641a1c"), hx("852a2a"), hx("a8403b")),
    "tan": (hx("5a3d21"), hx("7f5a33"), hx("a07746"), hx("bf955c")),
}
ITO = {  # tsuka-ito colours
    "kon": (hx("0c1226"), hx("18234a"), hx("2a3a6e"), hx("44588f")),
    "black": (hx("0b0b0d"), hx("19191d"), hx("2a2a30"), hx("404049")),
    "brown": (hx("2a170c"), hx("472813"), hx("643a1e"), hx("82502c")),
    "green": (hx("0f2418"), hx("1b3d28"), hx("2b573b"), hx("3f7553")),
    "white": (hx("9a978e"), hx("c9c5ba"), hx("e4e0d5"), hx("f7f4ec")),
    "purple": (hx("1e0d26"), hx("341946"), hx("4c2a63"), hx("6a4185")),
}


def metal_paint(pal, t, salt=0, bands=True, worn=0.12):
    """Hilt metal: vertical light falloff, bright rims, small pits."""
    n = tnoise(t, salt)
    base = ramp([pal[0], pal[1], pal[2]], 0.55 + 0.35 * (0.5 - abs(t.fu - 0.5)) - 0.15 * t.fv)
    if t.face == "up":
        base = mix(base, pal[3], 0.35)
    if t.face == "down":
        base = shade(base, -0.25)
    if (t.x == 0 or t.x == t.w - 1) and t.w > 2:
        base = shade(base, -0.18)
    if n < worn * 0.4:
        base = mix(base, pal[3], 0.6)
    elif n > 1 - worn:
        base = shade(base, -0.12)
    return base


def wood_paint(pal, t, salt=0, along="y"):
    axis = {"x": 0, "y": 1, "z": 2}[along]
    q = np.floor(t.p * 8 + 1e-4).astype(int)
    other = [i for i in range(3) if i != axis]
    ring = math.sin(q[other[0]] * 1.7 + q[other[1]] * 2.3 + hash01(q[other[0]], q[other[1]], salt) * 6.0)
    grain = 0.5 + 0.5 * ring
    n = tnoise(t, salt)
    c = ramp([pal[0], pal[1], pal[2], pal[3]], 0.25 + grain * 0.45 + (n - 0.5) * 0.18)
    if n > 0.97:
        c = shade(pal[0], -0.2)
    return c


def stone_paint(pal, t, salt=0):
    n = tnoise(t, salt)
    n2 = tnoise(t, salt + 7)
    c = ramp([pal[0], pal[1], pal[2], pal[3]], 0.3 + n * 0.55)
    if n2 > 0.86:
        c = shade(pal[0], -0.15)
    return c


def leather_paint(pal, t, salt=0, stitch=False):
    n = tnoise(t, salt)
    c = ramp([pal[0], pal[1], pal[2]], 0.35 + n * 0.35 + 0.15 * (0.5 - abs(t.fu - 0.5)))
    q = int(math.floor(t.p[1] * 8 + 1e-4))
    if q % 6 == 0:
        c = shade(c, -0.25)          # wrap seams
    if stitch and t.x == t.w // 2 and q % 2 == 0:
        c = mix(c, (190, 170, 130, 255), 0.6)
    return c
