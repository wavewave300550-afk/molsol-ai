"""
Procedural materials ("painters") and decals.

A painter is a function FaceCtx -> RGBA.  Most painters sample 3D value noise at
the texel's model-space position so patterns continue across cube faces, and
bake a gentle top-light / bottom-shadow gradient plus edge definition, which is
what makes low-resolution Minecraft textures read well at a distance.
"""
from __future__ import annotations

import math
import random
from typing import Callable, Optional, Sequence

from .geo import FaceCtx, RGBA, TRANSPARENT

# --------------------------------------------------------------------------- colour helpers


def hx(s: str, a: int = 255) -> RGBA:
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


def mix(c1: RGBA, c2: RGBA, t: float) -> RGBA:
    t = max(0.0, min(1.0, t))
    return tuple(int(round(c1[i] * (1 - t) + c2[i] * t)) for i in range(4))  # type: ignore


def shade(c: RGBA, f: float) -> RGBA:
    """f > 0 lightens towards white, f < 0 darkens towards black (alpha kept)."""
    if f >= 0:
        return mix(c, (255, 255, 255, c[3]), f)
    return mix(c, (0, 0, 0, c[3]), -f)


def ramp(stops: Sequence[RGBA], t: float) -> RGBA:
    t = max(0.0, min(1.0, t)) * (len(stops) - 1)
    i = min(len(stops) - 2, int(t))
    return mix(stops[i], stops[i + 1], t - i)


def C(c) -> RGBA:
    return hx(c) if isinstance(c, str) else c


# --------------------------------------------------------------------------- noise

_R = random.Random(1234)
_PERM = list(range(256))
_R.shuffle(_PERM)
_PERM += _PERM
_VAL = [_R.random() for _ in range(256)]


def _hash(ix, iy, iz):
    return _VAL[_PERM[(_PERM[(_PERM[ix & 255] + iy) & 255] + iz) & 255]]


def vnoise(x: float, y: float, z: float) -> float:
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    fx, fy, fz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)
    c000, c100 = _hash(ix, iy, iz), _hash(ix + 1, iy, iz)
    c010, c110 = _hash(ix, iy + 1, iz), _hash(ix + 1, iy + 1, iz)
    c001, c101 = _hash(ix, iy, iz + 1), _hash(ix + 1, iy, iz + 1)
    c011, c111 = _hash(ix, iy + 1, iz + 1), _hash(ix + 1, iy + 1, iz + 1)
    x00 = c000 + (c100 - c000) * fx
    x10 = c010 + (c110 - c010) * fx
    x01 = c001 + (c101 - c001) * fx
    x11 = c011 + (c111 - c011) * fx
    y0 = x00 + (x10 - x00) * fy
    y1 = x01 + (x11 - x01) * fy
    return y0 + (y1 - y0) * fz


def fbm(x, y, z, octaves=3):
    a, f, s, n = 0.5, 1.0, 0.0, 0.0
    for _ in range(octaves):
        s += a * vnoise(x * f, y * f, z * f)
        n += a
        a *= 0.5
        f *= 2.03
    return s / n


def h2(x: int, y: int, seed: int = 0) -> float:
    """Deterministic per-texel hash in [0,1)."""
    n = (x * 374761393 + y * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65536.0


# --------------------------------------------------------------------------- lighting bake


def bake(col: RGBA, f: FaceCtx, top=0.10, bottom=-0.16, edge=-0.10, up_boost=0.06, down=-0.22) -> RGBA:
    """Soft baked light: lighter near the top of side faces, darker underneath, defined edges."""
    if col[3] == 0:
        return col
    if f.side:
        col = shade(col, top + (bottom - top) * f.v)
    elif f.face == "up":
        col = shade(col, up_boost)
    else:
        col = shade(col, down)
    if edge and f.edge and min(f.w, f.h) > 2:
        col = shade(col, edge)
    return col


# --------------------------------------------------------------------------- basic painters

Painter = Callable[[FaceCtx], RGBA]


def solid(base, var=0.05, edge=-0.10, light=True) -> Painter:
    b = C(base)

    def p(f: FaceCtx) -> RGBA:
        n = fbm(f.p[0] * 0.35, f.p[1] * 0.35, f.p[2] * 0.35)
        col = shade(b, (n - 0.5) * 2 * var)
        return bake(col, f, edge=edge) if light else col
    return p


def flat(base) -> Painter:
    b = C(base)
    return lambda f: b


def grad(top, bottom, var=0.04, edge=-0.08) -> Painter:
    t, b = C(top), C(bottom)

    def p(f: FaceCtx) -> RGBA:
        if f.side:
            col = mix(t, b, f.v)
        elif f.face == "up":
            col = t
        else:
            col = b
        n = fbm(f.p[0] * 0.4, f.p[1] * 0.4, f.p[2] * 0.4)
        return bake(shade(col, (n - 0.5) * 2 * var), f, top=0.04, bottom=-0.06, edge=edge)
    return p


def vgrad_world(top, bottom, y0, y1, var=0.05) -> Painter:
    """Gradient by model-space height (continuous across cubes)."""
    t, b = C(top), C(bottom)

    def p(f: FaceCtx) -> RGBA:
        k = (f.p[1] - y0) / max(1e-6, (y1 - y0))
        col = mix(b, t, k)
        n = fbm(f.p[0] * 0.4, f.p[1] * 0.4, f.p[2] * 0.4)
        return bake(shade(col, (n - 0.5) * 2 * var), f, top=0.03, bottom=-0.05)
    return p


# --------------------------------------------------------------------------- organic


def scales(base, dark, light=None, size=3.0, belly=None, belly_face="down", var=0.08, glint=None) -> Painter:
    """Diamond-lattice reptile scales with dark seams and lit upper rims; optional plated belly."""
    b, d = C(base), C(dark)
    l = C(light) if light else shade(b, 0.22)
    bel = C(belly) if belly else None
    gl = C(glint) if glint else None

    def p(f: FaceCtx) -> RGBA:
        x, y, z = f.p
        if bel is not None and f.face == belly_face:
            k = z if f.face in ("down", "up") else y
            c = shade(bel, -0.16 if (int(k * 1.6) % 3 == 0) else 0.0)
            return bake(shade(c, (fbm(x * 0.3, y * 0.3, z * 0.3) - 0.5) * 0.1), f, edge=-0.04)
        hcoord = x if f.face in ("north", "south", "up", "down") else z
        vcoord = y if f.side else (z if f.face in ("up", "down") else y)
        ga, gb = (hcoord + vcoord) / size, (hcoord - vcoord) / size
        ia, ib = math.floor(ga), math.floor(gb)
        fa, fb = ga - ia, gb - ib
        edge = min(fa, 1 - fa, fb, 1 - fb)
        if edge < 0.14:
            c = mix(d, b, 0.35)
        elif fa > 0.62 and fb < 0.5:
            c = mix(l, b, 0.3)
        else:
            c = b
        n = fbm(x * 0.15, y * 0.15, z * 0.15)
        c = shade(c, (n - 0.5) * 2 * var + (h2(ia, ib, 3) - 0.5) * 0.12)
        if gl and h2(ia, ib, 9) > 0.92 and edge >= 0.14:
            c = mix(c, gl, 0.7)
        return bake(c, f, edge=-0.06)
    return p


def fur(base, dark=None, light=None, streak=1.0, var=0.10, tip=None) -> Painter:
    """Fur: vertical strand streaks with lighter tips and darker roots."""
    b = C(base)
    d = C(dark) if dark else shade(b, -0.25)
    l = C(light) if light else shade(b, 0.25)
    tp = C(tip) if tip else None

    def p(f: FaceCtx) -> RGBA:
        x, y, z = f.p
        hcoord = x if f.face in ("north", "south", "up", "down") else z
        strand = vnoise(hcoord * 1.3 * streak, y * 0.18, (z if f.face in ("north", "south") else x) * 0.6)
        c = mix(d, l, strand)
        c = mix(c, b, 0.45)
        n = fbm(x * 0.12, y * 0.12, z * 0.12)
        c = shade(c, (n - 0.5) * 2 * var)
        if tp is not None and f.side and f.v > 0.7:
            c = mix(c, tp, (f.v - 0.7) / 0.3 * 0.8)
        return bake(c, f, edge=-0.05)
    return p


def feathers(base, tip, shaft=None, row=3, tip_from=0.45, ragged=True, axis="u", flip=False) -> Painter:
    """Rows of overlapping feathers.  The tip colour grows along `axis` of the face."""
    b, t = C(base), C(tip)
    sh = C(shaft) if shaft else shade(b, 0.35)

    def p(f: FaceCtx) -> RGBA:
        k = f.u if axis == "u" else f.v
        if flip:
            k = 1 - k
        lane = f.y if axis == "u" else f.x
        idx = lane // row
        within = lane % row
        jitter = (h2(idx, 0, 5) - 0.5) * 0.12
        c = mix(b, t, max(0.0, (k - tip_from + jitter) / max(0.05, 1 - tip_from)))
        c = shade(c, ((idx % 3) - 1) * 0.06)
        if within == row - 1:
            c = shade(c, -0.18)           # shadow line between feathers
        elif within == row // 2 and row >= 3 and k < 0.85:
            c = mix(c, sh, 0.35)          # rachis
        if ragged and k > 0.9 and within == row - 1:
            return TRANSPARENT
        if ragged and k > 0.97 and (h2(f.x, f.y, 7) > 0.5):
            return TRANSPARENT
        return c
    return p


def membrane(base, vein, holes=0.0, dark=None, scallop=0.0, glowvein=None) -> Painter:
    """Wing membrane with branching veins, tears and an optional scalloped trailing edge (v -> 1)."""
    b, vn = C(base), C(vein)
    dk = C(dark) if dark else shade(b, -0.35)
    gv = C(glowvein) if glowvein else None

    def p(f: FaceCtx) -> RGBA:
        x, y, z = f.p
        if scallop and f.face in ("up", "down"):
            edge = 1 - scallop * (0.35 + 0.65 * abs(math.sin(f.u * math.pi * 3)))
            if f.v > edge:
                return TRANSPARENT
            if f.v > edge - 0.05:
                return shade(dk, -0.3)
        n = fbm(x * 0.25, y * 0.25, z * 0.25, 4)
        c = mix(dk, b, 0.4 + n * 0.8)
        # veins: ridges of a low frequency noise
        r = abs(vnoise(x * 0.09 + 3, y * 0.09, z * 0.09) - 0.5)
        if r < 0.035:
            c = gv if (gv is not None and f.variant >= 1) else vn
        elif r < 0.06:
            c = mix(c, vn, 0.4)
        if holes > 0:
            hn = fbm(x * 0.18 + 11, y * 0.18, z * 0.18 + 5)
            if hn > 1 - holes:
                return TRANSPARENT
            if hn > 1 - holes - 0.04:
                c = shade(dk, -0.3)
        return c
    return p


def plush(base, dark=None, light=None, var=0.07, tip=None, tip_axis=None) -> Painter:
    """Soft, fluffy fur: low-frequency light and shade with only a hint of strands (no wood-grain)."""
    b = C(base)
    d = C(dark) if dark else shade(b, -0.22)
    l = C(light) if light else shade(b, 0.22)
    tp = C(tip) if tip else None

    def p(f: FaceCtx) -> RGBA:
        x, y, z = f.p
        n = fbm(x * 0.09, y * 0.09, z * 0.09, 3)
        c = mix(d, l, 0.25 + n * 0.75)
        c = mix(c, b, 0.4)
        c = shade(c, (vnoise(x * 0.9, y * 0.45, z * 0.9) - 0.5) * var)
        if tp is not None and tip_axis is not None:
            t = f.p[tip_axis[0]]
            k = (t - tip_axis[1]) / max(1e-6, tip_axis[2] - tip_axis[1])
            if k > 0:
                c = mix(c, tp, min(1.0, k))
        return bake(c, f, edge=-0.03, top=0.08, bottom=-0.12)
    return p


def bone_mat(base="efe6cf", dark="a8977a") -> Painter:
    b, d = C(base), C(dark)

    def p(f: FaceCtx) -> RGBA:
        n = fbm(f.p[0] * 0.5, f.p[1] * 0.5, f.p[2] * 0.5)
        c = mix(b, d, n * 0.6 + (0.25 * f.v if f.side else 0))
        return bake(c, f, edge=-0.12)
    return p


def horn(base, tip, rings=True, ring_period=2.0) -> Painter:
    b, t = C(base), C(tip)

    def p(f: FaceCtx) -> RGBA:
        x, y, z = f.p
        n = fbm(x * 0.4, y * 0.4, z * 0.4)
        c = shade(mix(b, t, n * 0.5), (n - 0.5) * 0.18)
        if rings and int((x + y + z) / ring_period) % 2 == 0:
            c = shade(c, -0.10)
        return bake(c, f, edge=-0.12)
    return p


# --------------------------------------------------------------------------- precious & built


def gold(base="e9b52b", dark="8c5a0c", light="fff3b0", var=0.10, sparkle=0.05) -> Painter:
    b, d, l = C(base), C(dark), C(light)

    def p(f: FaceCtx) -> RGBA:
        x, y, z = f.p
        n = fbm(x * 0.5, y * 0.5, z * 0.5)
        if f.side:
            t = f.v
            c = mix(l, b, min(1, t * 2.4)) if t < 0.42 else mix(b, d, (t - 0.42) / 0.58)
        elif f.face == "up":
            c = mix(l, b, 0.35)
        else:
            c = d
        c = shade(c, (n - 0.5) * 2 * var)
        if h2(f.x + int(x * 7), f.y + int(z * 5), 11) < sparkle:
            c = shade(l, 0.5)
        if f.edge and min(f.w, f.h) > 2:
            c = shade(d, -0.1) if (f.y == f.h - 1 and f.side) else shade(c, 0.12)
        return c
    return p


def metal(base="cfd6df", line="7d8794", panel=4, var=0.03) -> Painter:
    b, ln = C(base), C(line)

    def p(f: FaceCtx) -> RGBA:
        c = shade(b, (fbm(f.p[0], f.p[1], f.p[2]) - 0.5) * 2 * var)
        if (f.x % panel == panel - 1 and f.w > panel + 1) or (f.y % panel == panel - 1 and f.h > panel + 1):
            c = mix(c, ln, 0.5)
        return bake(c, f, edge=-0.16)
    return p


def leiwen(x: int, y: int, cell: int = 6) -> bool:
    """Square 'thunder' spiral (雷纹) motif of Shang bronzes; True = raised line."""
    cx, cy = x % cell, y % cell
    flip = ((x // cell) + (y // cell)) % 2
    if flip:
        cx = cell - 1 - cx
    # a squared spiral drawn as nested L-shapes
    ring = min(cx, cy, cell - 1 - cx, cell - 1 - cy)
    if ring % 2 == 0:
        # gap in each ring so the line spirals inward
        if cy == ring and cx == ring + 1 and ring > 0:
            return False
        return not (cy == ring + 1 and cx == ring and ring + 1 < cell // 2)
    return False


def bronze(base="5a7d5e", patina="7fb6a0", raised="c79a4a", dark="2b3a2e", motif=True, cell=8, var=0.10,
           band=(0.28, 0.72), border=True) -> Painter:
    """Ancient ritual bronze: verdigris patina; leiwen spirals cast in a bordered register band."""
    b, pa, r, d = C(base), C(patina), C(raised), C(dark)
    rl = mix(r, b, 0.35)

    def p(f: FaceCtx) -> RGBA:
        x, y, z = f.p
        n = fbm(x * 0.22, y * 0.22, z * 0.22, 4)
        c = mix(d, b, 0.55 + n * 0.6)
        pat = fbm(x * 0.35 + 7, y * 0.35, z * 0.35 - 3)
        if pat > 0.55:
            c = mix(c, pa, min(1, (pat - 0.55) * 3.5))
        if motif and f.side and f.w >= cell + 2 and f.h >= 8:
            lo, hi = int(band[0] * f.h), int(band[1] * f.h)
            if border and (f.y == lo - 1 or f.y == hi + 1):
                c = mix(rl, pa, 0.3 if pat > 0.6 else 0.0)
            elif lo <= f.y <= hi and leiwen(f.x - 1, f.y - lo, cell):
                c = mix(c, rl, 0.85)
                c = mix(c, pa, 0.3 if pat > 0.62 else 0)
            elif lo <= f.y <= hi:
                c = shade(c, -0.12)                          # recessed ground of the band
        c = shade(c, (h2(f.x, f.y, f.cube_index) - 0.5) * var)
        return bake(c, f, edge=-0.16)
    return p


def marble(base="f4f1ea", vein="b9b2a3", gold_vein=None, var=0.05) -> Painter:
    b, vn = C(base), C(vein)
    gv = C(gold_vein) if gold_vein else None

    def p(f: FaceCtx) -> RGBA:
        x, y, z = f.p
        n = fbm(x * 0.12, y * 0.12, z * 0.12, 4)
        r = abs(math.sin((x * 0.2 + y * 0.35 + z * 0.15 + n * 6.0)))
        c = shade(b, (fbm(x * 0.6, y * 0.6, z * 0.6) - 0.5) * 2 * var)
        if r < 0.08:
            c = gv if gv and n > 0.55 else mix(c, vn, 0.75)
        elif r < 0.16:
            c = mix(c, vn, 0.25)
        return bake(c, f, top=0.06, bottom=-0.10, edge=-0.08)
    return p


def crystal(base, light, dark=None, facet=3) -> Painter:
    b, l = C(base), C(light)
    d = C(dark) if dark else shade(b, -0.35)

    def p(f: FaceCtx) -> RGBA:
        k = ((f.x // facet) * 7 + (f.y // facet) * 3 + f.cube_index) % 5
        c = ramp([d, b, l], (k / 4) * 0.8 + (1 - f.v) * 0.2 if f.side else 0.7)
        if (f.x + f.y) % (facet * 2) == 0:
            c = shade(c, 0.35)
        return c
    return p


def cloth(base, trim=None, trim_rows=1, fold=0.07, pattern=None) -> Painter:
    b = C(base)
    tr = C(trim) if trim else None

    def p(f: FaceCtx) -> RGBA:
        if tr is not None and f.side and f.y >= f.h - trim_rows:
            return bake(shade(tr, -0.12 if (f.x % 2) else 0.12), f, edge=0)
        c = shade(b, -fold if (int(f.p[0] + f.p[2]) % 3 == 0) else 0)
        if pattern and pattern(f):
            c = shade(c, 0.18)
        return bake(shade(c, (fbm(f.p[0] * 0.5, f.p[1] * 0.5, f.p[2] * 0.5) - 0.5) * 0.08), f, edge=-0.06)
    return p


def kanok(gold_c="e9b52b", red="9b1c1c", deep="4a0b0b", period=6) -> Painter:
    """Thai kanok-flame band ornament: gold flame tongues on lacquer red."""
    g, r, dk = C(gold_c), C(red), C(deep)

    def p(f: FaceCtx) -> RGBA:
        lx = f.x % period
        ly = f.y % period
        tongue = abs(lx - period / 2 + 0.5) < (period / 2) * (1 - ly / period) + 0.3
        c = shade(g, 0.15 - 0.25 * (ly / period)) if tongue else r
        if ly == period - 1:
            c = dk
        if f.edge:
            c = shade(g, -0.2)
        return c
    return p


def flame(core="fff6c8", mid="ffb43b", outer="ff4f1a", cut=True) -> Painter:
    c0, m, o = C(core), C(mid), C(outer)

    def p(f: FaceCtx) -> RGBA:
        t = f.v if f.side else 0.2
        n = vnoise(f.p[0] * 0.8, f.p[1] * 0.6, f.p[2] * 0.8)
        t = t * 0.8 + n * 0.3
        c = ramp([c0, m, o], t)
        if cut and f.side and t > 0.75 and h2(f.x, f.y, 3) < (t - 0.75) * 3:
            return TRANSPARENT
        return c
    return p


def glowball(core, edge) -> Painter:
    c0, e = C(core), C(edge)

    def p(f: FaceCtx) -> RGBA:
        dx, dy = f.u - 0.5, f.v - 0.5
        return mix(c0, e, min(1.0, math.sqrt(dx * dx + dy * dy) * 2))
    return p


def glyphs(base, ink, rows=4, seed=1, margin=1, light=True) -> Painter:
    """Lines of abstract luminous script (never real words)."""
    b, ik = C(base), C(ink)

    def p(f: FaceCtx) -> RGBA:
        c = shade(b, (fbm(f.p[0] * 0.4, f.p[1] * 0.4, f.p[2] * 0.4) - 0.5) * 0.08)
        if margin <= f.x < f.w - margin and margin <= f.y < f.h - margin:
            ly = (f.y - margin) % rows
            if ly < rows - 1:
                gx = (f.x - margin) // 3
                gy = (f.y - margin) // rows
                cell = int(h2(gx, gy, seed + f.cube_index) * 16)
                lx = (f.x - margin) % 3
                bit = (cell >> ((lx + ly * 2) % 4)) & 1
                if lx < 2 and bit:
                    c = ik
        return bake(c, f, edge=-0.05) if light else c
    return p


def eyes_band(base, white="f6f1e2", iris="2c8fd6", pupil="0d0d12", period=4) -> Painter:
    """A rim covered with eyes (for the Thrones' wheels)."""
    b, w_, ir, pu = C(base), C(white), C(iris), C(pupil)

    def p(f: FaceCtx) -> RGBA:
        c = bake(shade(b, (fbm(f.p[0] * 0.5, f.p[1] * 0.5, f.p[2] * 0.5) - 0.5) * 0.12), f, edge=-0.12)
        if f.h >= 3 and f.side or f.face in ("up", "down"):
            lx = f.x % period
            cy = f.h // 2
            if abs(f.y - cy) <= 0 and 0 < lx < period - 1:
                c = ir if lx == period // 2 else w_
                if lx == period // 2 and (f.x // period) % 2 == 0:
                    c = pu
        return c
    return p


def dither(c1: Painter, c2: Painter, t: float, seed=0) -> Painter:
    def p(f: FaceCtx) -> RGBA:
        return c2(f) if h2(f.x, f.y, seed + f.cube_index) < t else c1(f)
    return p


def by_face(default: Painter, **faces: Painter) -> Painter:
    def p(f: FaceCtx) -> RGBA:
        return faces.get(f.face, default)(f)
    return p


def blend_by(fn, a: Painter, b: Painter) -> Painter:
    """Blend two painters by a scalar function of the FaceCtx (0 -> a, 1 -> b)."""
    def p(f: FaceCtx) -> RGBA:
        t = fn(f)
        if t <= 0:
            return a(f)
        if t >= 1:
            return b(f)
        return mix(a(f), b(f), t)
    return p


# --------------------------------------------------------------------------- decals

def fill(setp, x0, y0, x1, y1, col):
    for y in range(int(y0), int(y1) + 1):
        for x in range(int(x0), int(x1) + 1):
            setp(x, y, col)


def d_eyes(white="f8f3e3", iris="e8b923", pupil="120a06", lid=None, row=None, size=2, gap=None, slit=False,
           brow=None) -> Callable:
    """Two eyes placed symmetrically on a face."""
    w_, ir, pu = C(white), C(iris), C(pupil)
    ld = C(lid) if lid else None
    br = C(brow) if brow else None

    def d(setp, w, h):
        r = h // 3 if row is None else row
        g = (w // 4) if gap is None else gap
        cx = w / 2
        for side in (-1, 1):
            x0 = int(round(cx + side * g - (size if side < 0 else 0)))
            x0 = int(cx - g - size) if side < 0 else int(cx + g)
            fill(setp, x0, r, x0 + size - 1, r + size - 1, ir)
            if size >= 3:
                setp(x0, r, w_)
            if slit:
                for yy in range(r, r + size):
                    setp(x0 + size // 2, yy, pu)
            else:
                setp(x0 + (size - 1 if side < 0 else 0), r + size - 1, pu)
                if size >= 3:
                    setp(x0 + (size - 2 if side < 0 else 1), r + size - 2, pu)
            if ld is not None:
                fill(setp, x0, r - 1, x0 + size - 1, r - 1, ld)
            if br is not None:
                fill(setp, x0 - (1 if side < 0 else 0), r - 2, x0 + size - (0 if side < 0 else 1), r - 2, br)
    return d


def d_teeth(tooth="f3eedb", gum=None, row="bottom", step=2, height=1) -> Callable:
    t = C(tooth)
    g = C(gum) if gum else None

    def d(setp, w, h):
        for x in range(w):
            if g is not None:
                setp(x, 0 if row == "top" else h - 1 - height, g)
            if x % step == 0:
                for k in range(height):
                    setp(x, (k if row == "top" else h - 1 - k), t)
    return d


def d_mouth(inner="3a0a0a", tooth="f3eedb", y0=None, fangs=True) -> Callable:
    i, t = C(inner), C(tooth)

    def d(setp, w, h):
        a = h // 2 if y0 is None else y0
        fill(setp, 1, a, w - 2, h - 2, i)
        if fangs:
            for x in range(1, w - 1, 2):
                setp(x, a, t)
            setp(2, a + 1, t)
            setp(w - 3, a + 1, t)
    return d


def d_dot(x, y, col, r=0) -> Callable:
    c = C(col)

    def d(setp, w, h):
        fill(setp, x - r, y - r, x + r, y + r, c)
    return d


def d_center_gem(col="d42a2a", light="ff9b9b", size=2) -> Callable:
    c, l = C(col), C(light)

    def d(setp, w, h):
        x0, y0 = w // 2 - size // 2, h // 2 - size // 2
        fill(setp, x0, y0, x0 + size - 1, y0 + size - 1, c)
        setp(x0, y0, l)
    return d


def d_band(col, row, thickness=1) -> Callable:
    c = C(col)

    def d(setp, w, h):
        rr = row if row >= 0 else h + row
        fill(setp, 0, rr, w - 1, rr + thickness - 1, c)
    return d


def d_vband(col, colx, thickness=1) -> Callable:
    c = C(col)

    def d(setp, w, h):
        xx = colx if colx >= 0 else w + colx
        fill(setp, xx, 0, xx + thickness - 1, h - 1, c)
    return d


def d_combine(*ds) -> Callable:
    def d(setp, w, h):
        for x in ds:
            x(setp, w, h)
    return d


def d_pixels(art: Sequence[str], palette: dict, ox=0, oy=0, center=False) -> Callable:
    """Stamp a small pixel-art pattern ('.' = keep)."""
    pal = {k: C(v) for k, v in palette.items()}

    def d(setp, w, h):
        x0 = (w - len(art[0])) // 2 if center else ox
        y0 = (h - len(art)) // 2 if center else oy
        for j, line in enumerate(art):
            for i, ch in enumerate(line):
                if ch in pal:
                    setp(x0 + i, y0 + j, pal[ch])
    return d
