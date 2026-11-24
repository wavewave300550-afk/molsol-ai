"""
Procedural materials for the Joan of Arc add-on.

Every painter is variant-aware:
    base     - Phase I look (polished silver, royal blue, white banner)
    burning  - Phase II look (soot, scorched cloth, burnt holes)
    ghost    - translucent spectral copy (Martyr's Procession echoes, phantom standards)
    glow1    - emissive overlay for Phase I (halo, gems)   ; transparent elsewhere
    glow2    - emissive overlay for Phase II (embers, burning edges, eyes)
    white    - purified look used by the death scene (banner turns pure white)
Painters return RGBA for a texel described by modelkit.FaceCtx.
"""
from __future__ import annotations

import math
from typing import Callable, Optional

from art import FACE_PALETTE, face_rows, fleur_mask, text_mask
from modelkit import (TRANSPARENT, FaceCtx, fbm, hash01, hx, mix, shade, smoothstep, vnoise, with_alpha)

Painter = Callable[[FaceCtx], "tuple"]

STEEL_HI = hx("eef2f6")
STEEL = hx("c3ccd6")
STEEL_MID = hx("9aa6b3")
STEEL_DK = hx("5f6b79")
GOLD_HI = hx("fff0a8")
GOLD = hx("e9b52f")
GOLD_DK = hx("9b6a10")
BLUE = hx("2d4fb0")
BLUE_DK = hx("1b3279")
BLUE_HI = hx("4a6fd0")
WHITE_CLOTH = hx("f4f0e4")
CLOTH_SHADOW = hx("d6cfbd")
SOOT = hx("2e2a28")
EMBER = hx("ff9a2e")
EMBER_HOT = hx("ffe08a")
GHOST = hx("bfe3ff")


def _noise(f: FaceCtx, scale: float = 1.0, seed: float = 0.0) -> float:
    p = f.pos
    return fbm(p[0] * scale + p[2] * 0.37 * scale, p[1] * scale + p[2] * 0.61 * scale, seed)


def _ghost(col, f: FaceCtx, alpha: int = 150):
    lum = (col[0] * 0.3 + col[1] * 0.59 + col[2] * 0.11) / 255
    c = mix(GHOST, hx("ffffff"), lum * 0.6)
    a = alpha + int((_noise(f, 0.4, 7) - 0.5) * 50)
    return with_alpha(c, a)


def _scorch(col, f: FaceCtx, amount: float):
    """Phase II soot: an overall tarnish, heavier near the ground where the burning
    roads lick at her, with vertical smoke streaks rising from below."""
    y = f.pos[1]
    low = 1.0 - smoothstep(2.0, 22.0, y)                       # feet -> waist
    streak = vnoise(f.pos[0] * 0.9 + f.pos[2] * 0.7, y * 0.12, 13)
    t = 0.18 * amount + low * 0.55 * amount + smoothstep(0.62, 0.85, streak) * 0.35 * amount
    col = mix(col, SOOT, min(0.85, t))
    # heat tint on metal-ish colours
    return mix(col, hx("6a3a22"), low * 0.15 * amount)


# --------------------------------------------------------------------------- armour

def steel(panel: bool = True, spec: float = 0.25, dark: float = 0.0, trim: bool = False) -> Painter:
    """Polished plate: vertical light falloff, sky reflection band, bevelled edges."""

    def p(f: FaceCtx):
        if f.glow:
            if f.variant == "glow2":
                # thin ember cracks through the scorched plate, mostly low on the body
                n = vnoise(f.pos[0] * 1.15 + f.pos[2] * 0.8, f.pos[1] * 0.9, 11)
                if abs(n - 0.5) < 0.011 and f.pos[1] < 24 and vnoise(f.pos[0] * 0.3, f.pos[1] * 0.3, 2) > 0.45:
                    return EMBER if f.pos[1] > 8 else EMBER_HOT
            return TRANSPARENT
        base = mix(STEEL, STEEL_MID, 0.35 + dark)
        if f.face == "up":
            col = mix(STEEL_HI, STEEL, 0.4)
        elif f.face == "down":
            col = mix(STEEL_MID, STEEL_DK, 0.5)
        else:
            t = f.v
            col = mix(STEEL_HI, base, smoothstep(0.0, 0.55, t))
            col = mix(col, STEEL_DK, smoothstep(0.55, 1.0, t) * 0.55)
            # sky reflection band
            band = math.exp(-((f.u - 0.32) ** 2) / 0.006)
            col = mix(col, STEEL_HI, band * spec)
        col = shade(col, (_noise(f, 2.2, 1) - 0.5) * 0.08)
        if f.edge_dist() == 0 and min(f.w, f.h) > 3:
            col = shade(col, 0.22) if f.y == 0 else shade(col, -0.25)
        if trim and f.edge_dist() <= 1 and min(f.w, f.h) > 5:
            col = mix(GOLD, GOLD_HI, 0.3 if f.y < f.h / 2 else 0.0)
        if panel and f.face in ("north", "south", "east", "west"):
            if f.h > 10 and f.y % 7 == 6:
                col = shade(col, -0.18)
        if f.variant == "burning":
            col = _scorch(col, f, 0.55)
        elif f.variant == "ghost":
            return _ghost(col, f)
        elif f.variant == "white":
            col = mix(col, hx("ffffff"), 0.35)
        return col
    return p


def gold(rivets: bool = False) -> Painter:
    def p(f: FaceCtx):
        if f.glow:
            return TRANSPARENT
        t = f.v if f.face not in ("up", "down") else 0.3
        col = mix(GOLD_HI, GOLD, smoothstep(0.0, 0.45, t))
        col = mix(col, GOLD_DK, smoothstep(0.5, 1.0, t) * 0.7)
        col = shade(col, (_noise(f, 3.0, 2) - 0.5) * 0.12)
        if rivets and f.x % 4 == 1 and f.y % 4 == 1:
            col = GOLD_HI
        if f.variant == "burning":
            col = _scorch(col, f, 0.3)
        elif f.variant == "ghost":
            return _ghost(col, f, 170)
        return col
    return p


def chainmail() -> Painter:
    def p(f: FaceCtx):
        if f.glow:
            return TRANSPARENT
        ring = (f.x + (f.y % 2)) % 2 == 0
        col = STEEL_MID if ring else STEEL_DK
        col = shade(col, (hash01(f.x, f.y, f.cube.origin[0]) - 0.5) * 0.15)
        if f.variant == "burning":
            col = _scorch(col, f, 0.6)
        elif f.variant == "ghost":
            return _ghost(col, f, 120)
        return col
    return p


def leather(base="6b4528", dark="452a16", stitch=True) -> Painter:
    b, d = hx(base), hx(dark)

    def p(f: FaceCtx):
        if f.glow:
            return TRANSPARENT
        col = mix(b, d, _noise(f, 2.5, 5) * 0.6)
        if stitch and f.face in ("north", "south", "east", "west") and (f.y == 1 or f.y == f.h - 2) and f.x % 3 == 0:
            col = hx("c8a878")
        if f.variant == "burning":
            col = _scorch(col, f, 0.4)
        elif f.variant == "ghost":
            return _ghost(col, f, 120)
        return col
    return p


def gem(color="3f7fff") -> Painter:
    c = hx(color)

    def p(f: FaceCtx):
        if f.variant == "glow1":
            return mix(c, hx("ffffff"), 0.25)
        if f.variant == "glow2":
            return hx("ff7a1c")
        col = mix(shade(c, 0.45), shade(c, -0.35), f.v)
        if f.x == 0 and f.y == 0:
            col = hx("ffffff")
        if f.variant == "ghost":
            return _ghost(col, f, 200)
        return col
    return p


# --------------------------------------------------------------------------- skin, face, hair

def skin() -> Painter:
    s, d = hx(FACE_PALETTE["s"]), hx(FACE_PALETTE["d"])

    def p(f: FaceCtx):
        if f.glow:
            return TRANSPARENT
        col = mix(s, d, f.v * 0.5)
        if f.variant == "burning":
            col = _scorch(col, f, 0.2)
        elif f.variant == "ghost":
            return _ghost(col, f, 160)
        return col
    return p


def face() -> Painter:
    rows = face_rows()
    sk = skin()

    def p(f: FaceCtx):
        # map the 14x16 design onto whatever the face slot is
        gx = min(13, int(f.u * 14))
        gy = min(15, int(f.v * 16))
        ch = rows[gy][gx]
        if f.variant == "glow2":
            if ch in "I":
                return hx("ffd25a")
            if ch == "W":
                return hx("fff3c4")
            return TRANSPARENT
        if f.glow:
            return TRANSPARENT
        if ch in ("H", "h"):
            col = hair()(f)
        else:
            col = hx(FACE_PALETTE.get(ch, FACE_PALETTE["s"]))
            if ch == "s":
                col = sk(f)
        if f.variant == "burning":
            # soot smudges on the cheeks, a scar of light under the left eye
            if ch in "sdC" and vnoise(gx * 0.6, gy * 0.6, 4) > 0.7:
                col = mix(col, SOOT, 0.45)
        elif f.variant == "ghost":
            return _ghost(col, f, 170)
        return col
    return p


def hair() -> Painter:
    H, Hh, Hd = hx("3d2416"), hx("5e3a23"), hx("24140b")

    def p(f: FaceCtx):
        if f.glow:
            if f.variant == "glow2" and f.face != "up" and f.v > 0.86 and hash01(f.x, f.pos[2], f.pos[0]) > 0.6:
                return EMBER
            return TRANSPARENT
        strand = hash01(round(f.pos[0] * 2) + round(f.pos[2] * 2) * 7.1, 3)
        col = mix(H, Hh, strand * 0.6)
        if f.face == "up":
            col = mix(col, Hh, 0.25)
        else:
            col = mix(col, Hd, smoothstep(0.55, 1.0, f.v) * 0.6)
            if 0.15 < f.v < 0.3:
                col = mix(col, hx("8a5a36"), 0.35 * strand)   # glossy band
        if f.variant == "burning":
            col = mix(col, hx("6a2a10"), smoothstep(0.6, 1.0, f.v) * 0.5)
        elif f.variant == "ghost":
            return _ghost(col, f, 150)
        return col
    return p


# --------------------------------------------------------------------------- cloth

def royal_blue(seme: bool = True, ermine_hem: int = 0, trim_rows: int = 1) -> Painter:
    """Royal French blue sewn with gold fleurs-de-lis; optional ermine hem."""
    fm = fleur_mask(7, 8)

    def p(f: FaceCtx):
        if f.glow:
            if f.variant == "glow2" and f.v > 0.93 and hash01(f.x, f.pos[0], 9) > 0.55:
                return EMBER
            return TRANSPARENT
        fold = math.sin(f.pos[0] * 1.3 + f.pos[2] * 0.9) * 0.5 + 0.5
        col = mix(BLUE_HI, BLUE, 0.4 + 0.6 * fold)
        col = mix(col, BLUE_DK, smoothstep(0.6, 1.0, f.v) * 0.5)
        col = shade(col, (_noise(f, 3.0, 8) - 0.5) * 0.06)
        if seme and f.face in ("north", "south", "east", "west") and f.w >= 10:
            cell_w, cell_h = 10, 12
            ox = (f.y // cell_h) % 2 * 5
            cx, cy = (f.x + ox) % cell_w - 1, f.y % cell_h - 2
            if 0 <= cx < 7 and 0 <= cy < 8 and fm[cy][cx]:
                col = GOLD if cy < 4 else mix(GOLD, GOLD_DK, 0.35)
        if ermine_hem and f.face in ("north", "south", "east", "west") and f.y >= f.h - ermine_hem:
            col = hx("f6f4ee")
            if (f.x % 4 == 1) and (f.y - (f.h - ermine_hem)) % 4 == 1:
                col = hx("1a1a1a")
        elif trim_rows and f.face in ("north", "south", "east", "west") and f.y >= f.h - trim_rows:
            col = GOLD
        if f.variant == "burning":
            col = _scorch(col, f, 0.5)
            if f.v > 0.92 and hash01(f.x, 3) > 0.5:
                return TRANSPARENT
        elif f.variant == "ghost":
            return _ghost(col, f, 140)
        return col
    return p


def wood() -> Painter:
    W, Wd, Wl = hx("5b3a22"), hx("3a2414"), hx("7b5332")

    def p(f: FaceCtx):
        if f.glow:
            if f.variant == "glow2" and hash01(f.pos[1] * 3, f.x) > 0.96:
                return EMBER
            return TRANSPARENT
        g = math.sin(f.pos[1] * 0.9 + hash01(f.x, f.face == "north") * 6) * 0.5 + 0.5
        col = mix(W, Wl if g > 0.6 else Wd, abs(g - 0.5))
        if f.face in ("up", "down"):
            col = Wd
        if f.variant == "burning":
            col = _scorch(col, f, 0.5)
        elif f.variant == "ghost":
            return _ghost(col, f, 160)
        return col
    return p


# --------------------------------------------------------------------------- the war banner

class BannerCloth:
    """
    Joan's white standard. Painted in *cloth coordinates* derived from the
    model-space position, so the design is continuous across the cloth bones:
        s = distance along the fly from the hoist (z), t = height (y)
    Shape: top edge straight, bottom edge tapering towards the fly, swallow-tail
    at the fly end, gold fringe, seme of fleurs-de-lis, large central lily,
    the IHS trigram near the hoist, battle damage (holes, tears, scorches).
    """

    def __init__(self, hoist_z: float, length: float, top_y: float, h_hoist: float, h_fly: float):
        self.z0, self.L, self.top = hoist_z, length, top_y
        self.h0, self.h1 = h_hoist, h_fly
        self.fm_small = fleur_mask(9, 10)
        self.fm_big = fleur_mask(21, 22)
        self.ihs = text_mask("IHS")
        # (s, t_from_top, radius) holes in cloth units; burning adds more
        self.holes = [(9.5, 6.0, 0.9), (18.5, 10.5, 1.2), (24.0, 3.2, 0.7), (13.0, 13.5, 0.6)]
        self.burn_holes = [(5.5, 11.0, 1.4), (21.0, 7.5, 1.6), (27.5, 9.0, 1.3), (15.5, 2.5, 1.0)]

    def height_at(self, s: float) -> float:
        k = max(0.0, min(1.0, s / self.L))
        return self.h0 + (self.h1 - self.h0) * k

    def __call__(self, f: FaceCtx):
        s = f.pos[2] - self.z0
        t = self.top - f.pos[1]          # depth below the top edge
        h = self.height_at(s)
        burning = f.variant in ("burning", "glow2")
        # ---- silhouette: tapered bottom edge with ragged tears
        rag = (hash01(round(s * 2)) - 0.5) * 1.1 + math.sin(s * 1.7) * 0.35
        bottom = h - 0.3 + rag * 0.6
        if t > bottom:
            return TRANSPARENT
        # swallow-tail notch at the fly end
        notch_depth = 5.0
        if s > self.L - notch_depth:
            k = (s - (self.L - notch_depth)) / notch_depth
            mid = bottom / 2
            if abs(t - mid) < k * bottom * 0.42:
                return TRANSPARENT
        # fraying fly edge
        if s > self.L - 0.6 and hash01(round(t * 2), 5) > 0.55:
            return TRANSPARENT
        # holes
        holes = list(self.holes) + (self.burn_holes if burning else [])
        rim = 0.0
        for hs, ht, hr in holes:
            d = math.hypot((s - hs) * 1.0, (t - ht) * 1.15) - hr * (0.85 + 0.3 * vnoise(s * 1.3, t * 1.3, hs))
            if d < 0:
                return TRANSPARENT
            if d < 0.55:
                rim = max(rim, 1 - d / 0.55)
        # burnt fly end in phase II
        burn_front = self.L - 6.5 + vnoise(t * 0.7, 1, 2) * 3.0
        if burning and s > burn_front + 1.6:
            return TRANSPARENT
        # ---- glow layers
        if f.variant == "glow2":
            if burning and burn_front < s <= burn_front + 1.6:
                return EMBER_HOT if hash01(round(s * 2), round(t * 2)) > 0.45 else EMBER
            if rim > 0.35 and hash01(round(s * 3), round(t * 3)) > 0.3:
                return EMBER
            return TRANSPARENT
        if f.variant == "glow1":
            # a few threads of the great lily catch the light
            if self._big_lily(s, t, h) and hash01(round(s * 2), round(t * 2), 1) > 0.93:
                return hx("fff3c0")
            return TRANSPARENT
        # ---- base linen
        weave = 0.035 if (f.x + f.y) % 2 == 0 else -0.02
        fold = math.sin(s * 0.9) * 0.5 + 0.5
        col = mix(WHITE_CLOTH, CLOTH_SHADOW, fold * 0.35 + (t / max(1, h)) * 0.15)
        col = shade(col, weave + (_noise(f, 1.5, 4) - 0.5) * 0.05)
        # gold border + fringe
        if t > bottom - 1.0:
            col = GOLD if (f.x % 2 == 0) else GOLD_DK               # silk fringe
        elif t < 0.5:
            col = mix(GOLD, GOLD_HI, 0.3)                           # hem along the staff top
        elif abs(t - (bottom - 1.55)) < 0.26:
            col = mix(col, GOLD, 0.55)                              # embroidered line above the fringe
        else:
            big = self._big_lily_px(s, t, h)
            if big == 1:
                col = mix(GOLD, GOLD_HI, 0.3 if t < h * 0.42 else 0.0)
            elif big == 2:
                col = GOLD_DK                                       # outline of the great lily
            elif self._clear(s, t, h):
                pass
            elif self._seme(s, t):
                col = mix(GOLD, WHITE_CLOTH, 0.35)
            elif self._ihs(s, t, h):
                col = hx("b9861f")
        # wear: soot stains, blood-brown battle stains, scorched hole rims
        stain = vnoise(s * 0.35, t * 0.35, 21)
        if stain > 0.72:
            col = mix(col, hx("b8a888"), (stain - 0.72) * 2.2)
        if rim > 0:
            col = mix(col, hx("4a3424"), rim * 0.9)
        if f.variant == "burning":
            col = _scorch(col, f, 0.45)
            if s > burn_front - 3.0:
                col = mix(col, SOOT, smoothstep(burn_front - 3.0, burn_front + 1.0, s))
        elif f.variant == "ghost":
            return _ghost(col, f, 135)
        elif f.variant == "white":
            col = mix(col, hx("ffffff"), 0.6)
        return col

    def _seme(self, s: float, t: float) -> bool:
        cw, ch = 8.0, 7.0
        row = int(t // ch)
        off = (row % 2) * cw / 2
        cx = (s + off) % cw
        cy = t % ch
        # 9x10 pixel fleur occupying 4.5 x 5 units (2 px / unit)
        gx, gy = int((cx - 1.0) * 2), int((cy - 0.6) * 2)
        if 0 <= gx < 9 and 0 <= gy < 10:
            # keep the area around the great lily and the trigram clear
            return bool(self.fm_small[gy][gx])
        return False

    def _clear(self, s: float, t: float, h: float) -> bool:
        cs, ct = self.L * 0.42, h * 0.5
        if (s - cs) ** 2 / 49.0 + (t - ct) ** 2 / 36.0 < 1.0:
            return True
        return s < 4.6 and abs(t - h * 0.5) < 3.0                    # around the IHS trigram

    def _big_lily_px(self, s: float, t: float, h: float) -> int:
        """1 = lily body, 2 = outline, 0 = none."""
        cs, ct = self.L * 0.42, h * 0.5
        gx = int((s - (cs - 5.25)) * 2)
        gy = int((t - (ct - 5.5)) * 2)
        m = self.fm_big
        if 0 <= gx < 21 and 0 <= gy < 22 and m[gy][gx]:
            return 1
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x2, y2 = gx + dx, gy + dy
            if 0 <= x2 < 21 and 0 <= y2 < 22 and m[y2][x2]:
                return 2
        return 0

    def _big_lily(self, s: float, t: float, h: float) -> bool:
        cs, ct = self.L * 0.42, h * 0.5
        gx = int((s - (cs - 5.25)) * 2)
        gy = int((t - (ct - 5.5)) * 2)
        if 0 <= gx < 21 and 0 <= gy < 22:
            return bool(self.fm_big[gy][gx])
        return False

    def _ihs(self, s: float, t: float, h: float) -> bool:
        # 11 x 5 glyph block, each glyph pixel = 0.5 unit
        gx = int((s - 1.4) * 2)
        gy = int((t - (h * 0.5 - 1.25)) * 2)
        if 0 <= gy < 5 and 0 <= gx < len(self.ihs[0]):
            return bool(self.ihs[gy][gx])
        return False

    def in_clear_zone(self, s, t, h):
        return False


def flat_color(c: str, glow: Optional[str] = None, glow_variant: str = "glow1", ghost_alpha: int = 160) -> Painter:
    col = hx(c)
    g = hx(glow) if glow else None

    def p(f: FaceCtx):
        if f.glow:
            if g is not None and (f.variant == glow_variant or glow_variant == "both"):
                return g
            return TRANSPARENT
        if f.variant == "ghost":
            return _ghost(col, f, ghost_alpha)
        out = shade(col, (hash01(f.x, f.y, f.pos[1]) - 0.5) * 0.06)
        if f.variant == "burning":
            out = _scorch(out, f, 0.4)
        return out
    return p


def halo(fire: bool = False) -> Painter:
    """Golden halo; in glow1 it shines gold, in glow2 it becomes a ring of fire."""

    def p(f: FaceCtx):
        if f.variant == "glow1":
            return mix(hx("fff6c8"), hx("ffd75e"), f.v)
        if f.variant == "glow2":
            k = hash01(f.x, f.y, f.pos[0])
            return mix(EMBER_HOT, hx("ff6a1a"), k * 0.8 + f.v * 0.2)
        if f.variant == "ghost":
            return with_alpha(hx("e8f6ff"), 190)
        if f.variant == "burning":
            return mix(hx("ff9a2e"), hx("ffcf6a"), f.v)
        return mix(GOLD_HI, GOLD, f.v)
    return p


def ember_flame() -> Painter:
    """Flame planes (stake fire, phase II accents): visible only in glow layers."""

    def p(f: FaceCtx):
        t = f.v
        flick = hash01(f.x, f.y, f.cube.origin[0])
        if t < 0.25 and abs(f.u - 0.5) > 0.12 + t:
            return TRANSPARENT
        if abs(f.u - 0.5) > 0.5 - t * 0.25 + flick * 0.05:
            return TRANSPARENT
        if f.variant in ("glow2", "glow1"):
            col = mix(EMBER_HOT, hx("ff5a14"), smoothstep(0.1, 0.9, t + (flick - 0.5) * 0.2))
            return col
        return TRANSPARENT
    return p


class BannerTatter:
    """A loose strip of the standard hanging under the cloth."""

    def __call__(self, f: FaceCtx):
        burning = f.variant in ("burning", "glow2")
        seed = f.pos[2]
        length = 0.55 + 0.4 * hash01(seed, 7)
        if f.v > length + 0.12 * hash01(f.x, seed) - (0.2 if burning else 0):
            return TRANSPARENT
        if abs(f.u - 0.5) > 0.5 - f.v * 0.3:
            return TRANSPARENT
        if f.variant == "glow2":
            return EMBER if f.v > 0.5 and hash01(f.x, f.y) > 0.4 else TRANSPARENT
        if f.glow:
            return TRANSPARENT
        col = mix(WHITE_CLOTH, CLOTH_SHADOW, f.v * 0.8)
        col = shade(col, -0.05 if f.x % 2 else 0.02)
        if f.variant == "burning":
            col = _scorch(col, f, 0.6)
        elif f.variant == "ghost":
            return _ghost(col, f, 130)
        elif f.variant == "white":
            col = mix(col, hx("ffffff"), 0.6)
        return col


def ribbon(tip: bool = False) -> Painter:
    """Royal-blue streamer with gold edges; the tip is forked with a gold tassel."""

    def p(f: FaceCtx):
        if tip:
            if f.v > 0.7 and abs(f.u - 0.5) < (f.v - 0.7) * 1.4:
                return TRANSPARENT                      # forked tail
        if f.variant == "glow2":
            return EMBER if (tip and f.v > 0.8 and hash01(f.x, f.y) > 0.5) else TRANSPARENT
        if f.glow:
            return TRANSPARENT
        col = mix(BLUE_HI, BLUE_DK, f.v * 0.6)
        if f.x == 0 or f.x == f.w - 1:
            col = GOLD
        if tip and f.v > 0.55:
            col = mix(GOLD, GOLD_DK, (f.v - 0.55) * 2)
        if f.variant == "burning":
            col = _scorch(col, f, 0.5)
        elif f.variant == "ghost":
            return _ghost(col, f, 140)
        return col
    return p


def seraph_wing() -> Painter:
    """Small feathered wing (single plane): white-gold, ragged feather tips."""

    def p(f: FaceCtx):
        x0 = min(abs(c) for c in (f.cube.origin[0], f.cube.origin[0] + f.cube.size[0]))
        span = abs(f.cube.size[0])
        d = max(0.0, min(1.0, (abs(f.pos[0]) - x0) / span))          # 0 at the body, 1 at the tip
        feathers = 5
        k = d * feathers
        scallop = 0.18 * (1 - abs((k % 1.0) - 0.5) * 2)
        limit = 1.0 - 0.6 * d + scallop - 0.12
        top = 0.08 * d * d
        if f.v > limit or f.v < top:
            return TRANSPARENT
        if f.variant == "glow1":
            return mix(hx("ffffff"), hx("ffe7a0"), f.v) if f.y % 3 != 2 else hx("ffd86a")
        if f.variant == "glow2":
            return mix(hx("fff0b0"), hx("ff7a24"), f.v)
        col = mix(hx("fffaf0"), hx("e6d29a"), f.v)
        return col
    return p
