"""
Procedural surface materials (painters) for the final bosses.
Painters work in pixel space (FaceCtx.x/y, w/h) at the model's density; `ux/uy` give model units.
"""
import math

from modelkit import TRANSPARENT, FaceCtx, hx, mix, shade


def noise(f: FaceCtx, amt: float):
    return (f.rng.random() - 0.5) * 2 * amt


def _h(*vals) -> float:
    """Deterministic hash in [0,1) - stable patterns independent of the RNG stream."""
    x = 0
    for v in vals:
        x = (x * 1103515245 + int(v) * 2654435761 + 12345) & 0x7FFFFFFF
    x ^= x >> 13
    x = (x * 1274126177) & 0x7FFFFFFF
    return (x % 10007) / 10007.0


# --------------------------------------------------------------------------- shared

def solid(base, var=0.05):
    c = hx(base)
    return lambda f: shade(c, noise(f, var))


def glowgrad(core, edge, axis="v", pulse_bands=False):
    """Additive-layer gradient: bright core fading to the edge colour."""
    c, e = hx(core), hx(edge)

    def p(f):
        t = abs((f.v if axis == "v" else f.u) - 0.5) * 2 if axis in ("v", "u") else math.hypot(f.u - 0.5, f.v - 0.5) * 1.4
        col = mix(c, e, min(1, t))
        if pulse_bands and (f.x + f.y) % 6 == 0:
            col = shade(col, 0.2)
        return col
    return p


def radial_glow(core, edge):
    c, e = hx(core), hx(edge)
    return lambda f: mix(c, e, min(1.0, math.hypot(f.u - 0.5, f.v - 0.5) * 1.6))


def flame(core="fff4c2", mid="ffab2e", outer="ff3d12", up=True):
    c, m, o = hx(core), hx(mid), hx(outer)

    def p(f):
        t = f.v if up else 1 - f.v          # 0 at the base
        t = 1 - t
        side = abs(f.u - 0.5) * 2
        k = min(1.0, t * 0.8 + side * 0.6 + noise(f, 0.08))
        if k < 0.35:
            return mix(c, m, k / 0.35)
        if k < 0.85:
            return mix(m, o, (k - 0.35) / 0.5)
        return mix(o, (0, 0, 0, 255), (k - 0.85) / 0.15 * 0.8)
    return p


# --------------------------------------------------------------------------- Void Emperor

def obsidian():
    base, vein, hi = hx("1a1024"), hx("5a2a8f"), hx("3a2a52")

    def p(f):
        col = shade(base, noise(f, 0.06))
        u, v = f.x / max(1, f.density), f.y / max(1, f.density)
        w = math.sin(u * 0.9 + v * 0.45 + f.cube_index) + math.sin(u * 0.33 - v * 1.1)
        if abs(w) < 0.08:
            col = mix(col, vein, 0.7)
        if (f.x + f.y * 2) % 23 == 0:
            col = mix(col, hi, 0.6)
        return col
    return p


def royal_gold(engrave="6b3e09"):
    g1, g2, g3, en = hx("ffe08a"), hx("d9a531"), hx("8a5a12"), hx(engrave)

    def p(f):
        t = f.v
        col = mix(g1, g2, t * 1.6) if t < 0.6 else mix(g2, g3, (t - 0.6) / 0.4)
        # filigree: interlocking arcs every 3 units
        u, v = f.x / f.density, f.y / f.density
        cu, cv = (u % 3) - 1.5, (v % 3) - 1.5
        r = math.hypot(cu, cv)
        if f.w > 4 * f.density and f.h > 3 * f.density and 0.95 < r < 1.25:
            col = mix(col, en, 0.55)
        if _h(f.x, f.y, f.cube_index) < 0.03:
            col = shade(g1, 0.5)
        return col
    return p


def velvet(base="3b1260", quilt="23093d", button="e8b923"):
    b, q, bt = hx(base), hx(quilt), hx(button)

    def p(f):
        u, v = f.x / f.density, f.y / f.density
        d = (u + v) % 4.0
        e = (u - v) % 4.0
        col = shade(b, noise(f, 0.04) + 0.08 * math.sin(u * 1.3))
        if d < 0.35 or e < 0.35:
            col = mix(col, q, 0.8)
        if (d < 0.6 and e < 0.6):
            col = bt
        return col
    return p


def void_surface(rim="b26bff"):
    deep, rimc = hx("030106"), hx(rim)

    def p(f):
        edge = min(f.u, f.v, 1 - f.u, 1 - f.v)
        col = mix(rimc, deep, min(1.0, edge * 9))
        if _h(f.x, f.y, f.cube_index, 7) < 0.012:
            col = hx("d8c8ff")
        return col
    return p


def porcelain(crack="9b8fb0", gold_crack=False):
    b, s, c = hx("f4f0f7"), hx("c9c0d6"), hx("d8a331" if gold_crack else crack)

    def p(f):
        col = mix(b, s, f.v * 0.5 + noise(f, 0.03))
        u, v = f.x / f.density, f.y / f.density
        line = math.sin(u * 1.7 + math.sin(v * 0.9 + f.cube_index) * 1.6)
        if abs(line) < 0.05 and _h(int(v * 2), f.cube_index) < 0.7:
            col = c
        return col
    return p


def dark_iron():
    b, r = hx("2c2a33"), hx("6d6a78")

    def p(f):
        col = shade(b, noise(f, 0.05) + 0.12 * (1 - f.v))
        if f.x % (3 * f.density) == 1 and f.y % (3 * f.density) == 1 and f.w > 3 * f.density:
            col = r      # rivets
        return col
    return p


def royal_cape():
    b, d, g = hx("4a1078"), hx("2a073f"), hx("e8b923")

    def p(f):
        u = f.x / f.density
        col = mix(b, d, 0.5 + 0.5 * math.sin(u * 0.8))     # folds
        col = shade(col, noise(f, 0.03))
        if f.v > 0.9:
            col = g if (f.x // f.density) % 2 == 0 else shade(g, -0.3)
        return col
    return p


def silhouette_outline(color="b26bff"):
    """Glow decal of a seated figure that is not there: an outline on black (black adds nothing)."""
    c = hx(color)

    def d(setp, w, h):
        cx = w / 2
        for y in range(h):
            for x in range(w):
                nx, ny = (x - cx) / w, y / h
                head = math.hypot(nx * 1.0, (ny - 0.17) * 1.25) - 0.12
                torso = max(abs(nx) - (0.18 + ny * 0.32), 0.33 - ny)
                body = min(head, torso if ny < 1.0 else 9)
                if abs(head) < 0.018 or (ny > 0.33 and abs(abs(nx) - (0.18 + ny * 0.32)) < 0.02) or (abs(ny - 0.33) < 0.012 and abs(nx) < 0.29):
                    setp(x, y, c)
                elif body < 0:
                    setp(x, y, (24, 6, 40, 255))
                else:
                    setp(x, y, (0, 0, 0, 255))
    return d


# --------------------------------------------------------------------------- Titan of Creation

def bronze():
    b, l, pat = hx("b0713a"), hx("e8b36a"), hx("3f9c86")

    def p(f):
        col = mix(l, b, f.v * 0.8 + 0.1)
        col = shade(col, noise(f, 0.05))
        if _h(f.x // 2, f.y // 2, f.cube_index) < 0.08 + 0.12 * f.v:
            col = mix(col, pat, 0.65)   # verdigris
        return col
    return p


def brass_gear():
    b, d = hx("d9a441"), hx("7a5212")
    return lambda f: shade(mix(b, d, f.v * 0.6), noise(f, 0.05) + (0.15 if f.edge else 0))


def sandstone_bricks():
    b, m, d = hx("d8c59a"), hx("a8925f"), hx("c2ab7a")

    def p(f):
        u, v = f.x / f.density, f.y / f.density
        row = int(v // 2.5)
        off = 2.5 if row % 2 else 0
        mortar = (v % 2.5) < 0.3 or ((u + off) % 5) < 0.3
        col = m if mortar else shade(mix(b, d, _h(row, int((u + off) // 5), f.cube_index)), noise(f, 0.04))
        return col
    return p


def marble():
    b, vein = hx("efeae2"), hx("8f8a86")

    def p(f):
        u, v = f.x / f.density, f.y / f.density
        w = math.sin(u * 0.6 + math.sin(v * 0.5 + f.cube_index) * 2.0 + v * 0.3)
        col = shade(b, noise(f, 0.03))
        if abs(w) < 0.06:
            col = mix(col, vein, 0.7)
        # fluting for columns
        if f.face in ("north", "south", "east", "west") and f.w >= 4 * f.density and (f.x // f.density) % 2 == 0:
            col = shade(col, -0.06)
        return col
    return p


def iron_plate():
    b, r = hx("5b5d66"), hx("a7aab5")

    def p(f):
        col = shade(b, noise(f, 0.05) + 0.15 * (1 - f.v))
        g = 4 * f.density
        if (f.x % g in (1, g - 2)) and (f.y % g in (1, g - 2)):
            col = r
        return col
    return p


def blueprint():
    """Glow layer: blue grid lines on black (black is invisible under additive blending)."""
    line, dim = hx("63c7ff"), hx("06121e")

    def p(f):
        g = 2 * f.density
        if f.x % g == 0 or f.y % g == 0:
            return line
        if (f.x + f.y) % (5 * f.density) == 0:
            return shade(line, -0.4)
        return dim
    return p


def forge_glow():
    return radial_glow("fff6cf", "ff6a00")


# --------------------------------------------------------------------------- Devouring Star

def bone():
    b, d, pore, crack = hx("ddd0b2"), hx("a8977a"), hx("7d6c53"), hx("4a3b2c")

    def p(f):
        col = mix(b, d, f.v * 0.7 + noise(f, 0.06))
        if _h(f.x, f.y, f.cube_index, 3) < 0.05:
            col = pore
        u, v = f.x / f.density, f.y / f.density
        if abs(math.sin(u * 0.8 + math.sin(v * 1.2 + f.cube_index) * 1.4)) < 0.035:
            col = crack
        return col
    return p


def charred_bone():
    b, d, ember = hx("3a2f2a"), hx("17110e"), hx("ff7a1a")

    def p(f):
        col = mix(b, d, f.v * 0.7 + noise(f, 0.06))
        u, v = f.x / f.density, f.y / f.density
        if abs(math.sin(u * 1.1 + v * 0.7 + f.cube_index)) < 0.05:
            col = mix(col, ember, 0.8)
        return col
    return p


def abyss_flesh():
    b, v_ = hx("3b0d2a"), hx("a02a52")

    def p(f):
        col = shade(b, noise(f, 0.06))
        u, v = f.x / f.density, f.y / f.density
        if abs(math.sin(u * 0.9 + math.sin(v * 1.3) * 1.5)) < 0.07:
            col = v_
        return col
    return p


def tooth():
    b, d = hx("fbf6ea"), hx("c9bfa5")
    return lambda f: mix(b, d, f.v)


def star_core():
    return radial_glow("ffffff", "ffb21f")


def corona():
    return glowgrad("fff1b0", "ff5a10")


# --------------------------------------------------------------------------- World Parasite (16 px per block - matches vanilla)

def grass_top():
    a, b, c = hx("5fa03a"), hx("4b8a2e"), hx("78b64a")

    def p(f):
        r = _h(f.x, f.y, f.cube_index)
        return a if r < 0.45 else b if r < 0.8 else c
    return p


def grass_side():
    g, d1, d2 = hx("5fa03a"), hx("866043"), hx("6b4a33")

    def p(f):
        drip = 2 + int(_h(f.x, f.cube_index) * 3)
        if f.y < drip:
            return shade(g, noise(f, 0.06))
        return d1 if _h(f.x, f.y, f.cube_index) < 0.6 else d2
    return p


def dirt():
    d1, d2, d3 = hx("866043"), hx("6b4a33"), hx("9a7255")
    return lambda f: (d1, d2, d3)[int(_h(f.x, f.y, f.cube_index, 2) * 3)]


def stone():
    s1, s2, s3 = hx("7d7d7d"), hx("6a6a6a"), hx("8f8f8f")
    return lambda f: (s1, s2, s3)[int(_h(f.x // 2, f.y // 2, f.cube_index, 5) * 3)]


def mossy_stone():
    st, m = stone(), hx("4f7a2e")

    def p(f):
        col = st(f)
        if _h(f.x // 2, f.y // 3, f.cube_index, 9) < 0.35 + 0.3 * (1 - f.v):
            col = shade(m, noise(f, 0.08))
        return col
    return p


def flesh():
    b, v_, d = hx("b5485b"), hx("6e1b2c"), hx("e07a8a")

    def p(f):
        col = shade(b, noise(f, 0.06))
        if abs(math.sin(f.x * 0.45 + math.sin(f.y * 0.31) * 2.2)) < 0.12:
            col = v_
        elif _h(f.x, f.y, 1) < 0.05:
            col = d
        return col
    return p


def bark():
    a, b = hx("6b4f2e"), hx("4f3920")
    return lambda f: a if (f.x + int(_h(f.y // 3, f.cube_index) * 3)) % 4 < 2 else b


def leaves():
    a, b, c = hx("3f7a24"), hx("2f6219"), hx("5a9636")

    def p(f):
        r = _h(f.x, f.y, f.cube_index, 4)
        if r < 0.18:
            return TRANSPARENT
        return a if r < 0.6 else b if r < 0.85 else c
    return p


def parasite_eye():
    def d(setp, w, h):
        cx, cy = (w - 1) / 2, (h - 1) / 2
        for y in range(h):
            for x in range(w):
                dd = math.hypot((x - cx) / (w / 2), (y - cy) / (h / 2))
                if dd > 1:
                    continue
                col = hx("f2e7b8")
                if dd < 0.62:
                    col = hx("c8d42a")
                if dd < 0.5 and abs(x - cx) < w * 0.07:
                    col = hx("120806")       # slit pupil
                if 0.62 <= dd < 1 and _h(x, y) < 0.08:
                    col = hx("c0283a")       # veins
                setp(x, y, col)
    return d


def pustule():
    return radial_glow("e9ff8a", "3aa82a")


# --------------------------------------------------------------------------- Choir of Mirrors

def mirror(tint="bfe6ff", seed=0):
    """Reflective pane: sky gradient, horizon line, diagonal highlight streaks."""
    sky, low, hi, horizon, deep = hx("eef8ff"), hx(tint), hx("ffffff"), hx("4f6f96"), hx("5d7ea6")

    def p(f):
        t = f.v
        col = mix(sky, low, t * 1.4) if t < 0.58 else mix(deep, low, (t - 0.58) * 1.6)
        if 0.55 < t < 0.6:
            col = mix(col, horizon, 0.5)
        s = (f.u * 1.0 + f.v * 0.8 + seed * 0.37) % 1.0
        if s < 0.06 or 0.18 < s < 0.21:
            col = mix(col, hi, 0.85)
        return col
    return p


def silver():
    b, d = hx("e3e7ee"), hx("8d95a3")
    return lambda f: shade(mix(b, d, f.v * 0.7), noise(f, 0.04) + (0.12 if f.edge else 0))


def veil():
    b, g = hx("f3f1fa"), hx("d9b44a")

    def p(f):
        col = shade(b, -0.06 * math.sin(f.x / f.density * 1.5))
        if f.v > 0.92 or f.u < 0.06 or f.u > 0.94:
            col = g
        if (f.x // 2 + f.y // 2) % 5 == 0 and (f.x // 2 - f.y // 2) % 5 == 0:
            return TRANSPARENT            # lace pattern
        return col
    return p


def mask_face(mouth="O", gold=True):
    """Decal: hollow eyes and an expression on a porcelain mask face."""
    blk, g = hx("08060c"), hx("d8a331")

    def d(setp, w, h):
        for y in range(h):
            for x in range(w):
                nx, ny = x / w, y / h
                # eyes
                for ex in (0.3, 0.7):
                    if ((nx - ex) / 0.11) ** 2 + ((ny - 0.38) / 0.07) ** 2 < 1:
                        setp(x, y, blk)
                # mouth
                if mouth == "O" and ((nx - 0.5) / 0.09) ** 2 + ((ny - 0.74) / 0.11) ** 2 < 1:
                    setp(x, y, blk)
                if mouth == "smile" and abs(ny - (0.7 + ((nx - 0.5) ** 2) * -1.6)) < 0.03 and abs(nx - 0.5) < 0.22:
                    setp(x, y, blk)
                if mouth == "frown" and abs(ny - (0.78 - ((nx - 0.5) ** 2) * -1.6)) < 0.03 and abs(nx - 0.5) < 0.22:
                    setp(x, y, blk)
                if mouth == "wail" and abs(nx - 0.5) < 0.08 and 0.62 < ny < 0.92:
                    setp(x, y, blk)
                # tear lines / kintsugi
                if gold and abs(nx - (0.3 + (ny - 0.45) * 0.15)) < 0.012 and 0.46 < ny < 0.9:
                    setp(x, y, g)
                if gold and abs(ny - (0.12 + nx * 0.5)) < 0.012 and nx > 0.55:
                    setp(x, y, g)
    return d


def rune_eyes(color="ffffff"):
    c = hx(color)

    def d(setp, w, h):
        for y in range(h):
            for x in range(w):
                if math.hypot((x - w / 2) / (w / 2), (y - h / 2) / (h / 2)) < 0.8:
                    setp(x, y, c)
    return d


def emperor_mask():
    """Decal: stern imperial mask - slanted hollow eyes, brow ridge, forehead jewel, gold tear-cracks."""
    blk, g, br = hx("06030b"), hx("d8a331"), hx("b9a9cf")

    def d(setp, w, h):
        for y in range(h):
            for x in range(w):
                nx, ny = x / w, y / h
                for side in (-1, 1):
                    ex = 0.5 + side * 0.21
                    # slanted almond: inner corner lower than the outer corner
                    yy = ny - (0.42 + (nx - ex) * side * -0.35)
                    if ((nx - ex) / 0.13) ** 2 + (yy / 0.045) ** 2 < 1:
                        setp(x, y, blk)
                    if abs(yy + 0.07) < 0.012 and abs(nx - ex) < 0.15:
                        setp(x, y, br)          # brow ridge
                    if abs(nx - (ex + side * 0.02)) < 0.012 and 0.48 < ny < 0.78:
                        setp(x, y, g)           # golden tear
                if abs(nx - 0.5) < 0.012 and 0.08 < ny < 0.3:
                    setp(x, y, g)
                if abs(nx - 0.5) + abs(ny - 0.3) < 0.05:
                    setp(x, y, hx("8a2be2"))   # forehead jewel
                if abs(ny - 0.86) < 0.01 and abs(nx - 0.5) < 0.12:
                    setp(x, y, br)          # closed lips
    return d
