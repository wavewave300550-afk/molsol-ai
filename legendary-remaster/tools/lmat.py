"""
Legend materials - procedural painters for the Legendary & Divine Beings remaster.

Painters are closures over FaceCtx (pixel coords at the model's density). Several materials have
palette variants (phase textures): set VARIANT["name"] before Model.paint(); the UV layout is
identical between paints, so variant PNGs can be swapped by the render controller.
"""
import math

from modelkit import TRANSPARENT, FaceCtx, hx, mix, shade

VARIANT = {"name": "default"}


def var(name):
    return VARIANT["name"] == name


def noise(f: FaceCtx, amt: float):
    return (f.rng.random() - 0.5) * 2 * amt


def H(*vals) -> float:
    """Deterministic hash in [0,1)."""
    x = 0
    for v in vals:
        x = (x * 1103515245 + int(v) * 2654435761 + 12345) & 0x7FFFFFFF
    x ^= x >> 13
    x = (x * 1274126177) & 0x7FFFFFFF
    return (x % 10007) / 10007.0


def U(f):
    """face coords in model units (float)"""
    return f.x / f.density, f.y / f.density


def solid(base, var_=0.05):
    c = hx(base)
    return lambda f: shade(c, noise(f, var_))


def glow(core, edge, mode="v"):
    """Additive-layer gradient. mode: v (vertical), u, r (radial), vb (bright at bottom)."""
    c, e = hx(core), hx(edge)

    def p(f):
        if mode == "r":
            t = min(1.0, math.hypot(f.u - 0.5, f.v - 0.5) * 1.5)
        elif mode == "u":
            t = abs(f.u - 0.5) * 2
        elif mode == "vb":
            t = 1 - f.v
        elif mode == "vt":
            t = f.v
        else:
            t = abs(f.v - 0.5) * 2
        return mix(c, e, t)
    return p


def flat_glow(col):
    c = hx(col)
    return lambda f: c


# =========================================================================== TAOTIE (bronze)

def _leiwen(ux, uy, cell=8.0):
    """Square-spiral (thunder pattern) groove mask in model units."""
    cx = (ux % cell) - cell / 2 + 0.5
    cy = (uy % cell) - cell / 2 + 0.5
    m = max(abs(cx), abs(cy))
    groove = abs(m - 1.0) < 0.42 or abs(m - 3.0) < 0.42
    if abs(m - 3.0) < 0.42 and cx > 0.6 and cy < -0.4:
        groove = False                      # opening of the outer square
    if abs(cy + 0.5) < 0.42 and 0.6 < cx < 3.2:
        groove = True                       # bridge -> spiral
    return groove


def bronze(kind="cast", lei=False, cell=8.0, patina=0.1):
    """Ritual bronze: dark field, raised gold-bronze leiwen relief, teal patina, polished edges.
    kind: cast (body), plate (warmer, smoother), dark (recesses). Variant 'heated': ember relief."""
    pal = {"cast": ("3b2613", "8c5c2c"), "plate": ("57341a", "b47c3c"), "dark": ("24170b", "4a3016")}
    hot = {"cast": ("3f170a", "9c3f18"), "plate": ("5e240e", "c2561f"), "dark": ("220b05", "52200c")}

    def p(f):
        b, h = (hot if var("heated") else pal)[kind]
        b, h = hx(b), hx(h)
        col = mix(h, b, 0.18 + f.v * 0.72)
        col = shade(col, noise(f, 0.04))
        ux, uy = U(f)
        if lei and f.w > 3 * f.density and f.h > 3 * f.density and _leiwen(ux, uy, cell):
            col = hx("ff8f3a") if var("heated") else shade(hx("c79546"), noise(f, 0.06) + 0.08 * (1 - f.v))
        elif patina and H(int(ux // 2.5), int(uy // 2.5), f.cube_index) < patina * (0.3 + 1.2 * f.v) * (0.25 if f.face == "up" else 1.0):
            col = mix(col, hx("2a0c06") if var("heated") else hx("2f7e6b"), 0.6)
        if f.y == 0 and f.h > 2:
            col = shade(col, 0.25)          # polished top edge
        return col
    return p


def gold(engrave=False):
    g, d = hx("e9bf4f"), hx("8a5a12")

    def p(f):
        col = mix(g, d, f.v * 0.7)
        col = shade(col, noise(f, 0.05))
        if engrave and (f.x + f.y) % (3 * f.density) == 0:
            col = shade(col, -0.25)
        if f.y == 0:
            col = shade(col, 0.3)
        return col
    return p


def ivory():
    a, b = hx("f3ead2"), hx("b9a77c")
    return lambda f: shade(mix(a, b, f.v * 0.8), noise(f, 0.04))


def gullet():
    a, b = hx("5a0d14"), hx("1f0306")

    def p(f):
        col = mix(a, b, f.v)
        if (f.y // f.density) % 3 == 0:
            col = shade(col, 0.12)          # throat ridges
        return shade(col, noise(f, 0.06))
    return p


def hoof():
    a = hx("2a1c12")
    return lambda f: shade(a, noise(f, 0.06) + (0.15 if f.y == 0 else 0))


def taotie_mask_decal(gold_col="ffd36a", dark="1b0f05"):
    """Relief taotie face for flanks/plates: two eyes, nose ridge, brow and jaw curls."""
    g, dk = hx(gold_col), hx(dark)

    def d(setp, w, h):
        for y in range(h):
            for x in range(w):
                nx, ny = x / w, y / h
                dx = abs(nx - 0.5)
                on = False
                # eyes
                e = ((dx - 0.2) / 0.09) ** 2 + ((ny - 0.45) / 0.12) ** 2
                if 0.62 < e < 1.45:
                    on = True
                if ((dx - 0.2) / 0.035) ** 2 + ((ny - 0.45) / 0.05) ** 2 < 1:
                    setp(x, y, dk)
                    continue
                # nose ridge
                if dx < 0.035 and 0.2 < ny < 0.8:
                    on = True
                # brow curls (C shapes)
                r = math.hypot(dx - 0.33, ny - 0.22)
                if abs(r - 0.12) < 0.03 and not (dx < 0.33 and ny > 0.22):
                    on = True
                # jaw curls
                r2 = math.hypot(dx - 0.3, ny - 0.75)
                if abs(r2 - 0.1) < 0.03 and ny > 0.7:
                    on = True
                # horn sweep
                if abs(ny - (0.12 + (dx - 0.1) ** 2 * 2.2)) < 0.03 and 0.08 < dx < 0.45:
                    on = True
                if on:
                    setp(x, y, g)
    return d


def bulging_eye(iris="ffcf4a", pupil="1a0c04"):
    """Decal for the taotie head's eyes: gold iris ring with a slit pupil (front face)."""
    ir, pu = hx(iris), hx(pupil)

    def d(setp, w, h):
        for y in range(h):
            for x in range(w):
                nx, ny = (x + 0.5) / w - 0.5, (y + 0.5) / h - 0.5
                r = math.hypot(nx, ny)
                if r < 0.42:
                    setp(x, y, ir if r > 0.12 else pu)
                if abs(nx) < 0.05 and abs(ny) < 0.36:
                    setp(x, y, pu)
    return d


# =========================================================================== shared bits

def iron():
    a, b = hx("5b5d66"), hx("2b2c33")
    return lambda f: shade(mix(a, b, f.v), noise(f, 0.05) + (0.18 if f.y == 0 else 0))


def stone(base="8d8a84", dark="5e5b56"):
    a, b = hx(base), hx(dark)

    def p(f):
        ux, uy = U(f)
        col = mix(a, b, H(int(ux // 2), int(uy // 2), f.cube_index) * 0.6 + f.v * 0.3)
        return shade(col, noise(f, 0.06))
    return p


def horn_bronze():
    """Uniform bronze for tube-built horns: fine annular ridges, no per-segment gradient."""
    def p(f):
        b = hx("6a3e1a") if var("heated") else hx("7a5128")
        col = shade(b, noise(f, 0.035))
        if (f.y // f.density) % 2 == 0 and f.face in ("north", "south", "east", "west"):
            col = shade(col, -0.07)
        return col
    return p


# =========================================================================== NIDHOGG

def wyrm_scale(base="1d2619", hi="47552f", belly=False):
    """Dark overlapping scales (arc rows) with a sickly sheen; variant 'ragnarok' adds burning veins."""
    def p(f):
        b, h = hx(base), hx(hi)
        ux, uy = U(f)
        row = int(uy // 2.2)
        off = 1.6 if row % 2 else 0
        cx = (ux + off) % 3.2 - 1.6
        cy = uy % 2.2
        arc = math.hypot(cx, cy - 2.4)
        col = mix(h, b, min(1.0, 0.35 + f.v * 0.55))
        if arc > 2.1:
            col = shade(col, -0.25)               # scale rim shadow
        elif arc < 1.2:
            col = shade(col, 0.08)
        col = shade(col, noise(f, 0.05))
        vein = abs(math.sin(ux * 0.55 + math.sin(uy * 0.35 + f.cube_index) * 1.8)) < 0.05
        if vein:
            col = hx("b8ff4a") if var("ragnarok") else mix(col, hx("3d6b1c"), 0.6)
        return col
    return p


def bone_plate():
    a, b = hx("ddd6bc"), hx("8f876d")

    def p(f):
        col = mix(a, b, f.v * 0.8)
        ux, uy = U(f)
        if H(int(ux), int(uy * 2), f.cube_index) < 0.05:
            col = shade(col, -0.3)
        if f.y == 0:
            col = shade(col, 0.15)
        return shade(col, noise(f, 0.04))
    return p


def membrane():
    """Leathery wing membrane: dark, one radiating vein per strip, tattered (alpha-cut) trailing edge."""
    def p(f):
        b = hx("2c2026")
        ux, uy = U(f)
        col = mix(hx("43302f"), b, f.v * 0.8)
        col = shade(col, noise(f, 0.04))
        if f.face in ("up", "down"):
            if abs(f.u - 0.5) < 0.07:
                col = hx("a6ff3a") if var("ragnarok") else mix(col, hx("587f2c"), 0.7)
            if f.v > 0.86 and H(int(ux * 1.5), int(uy * 1.5), f.cube_index) < (f.v - 0.86) * 3.0:
                return TRANSPARENT
        return col
    return p


def root_horn():
    a, b, tip = hx("4a3522"), hx("231710"), hx("cfc6a4")

    def p(f):
        col = mix(a, b, f.v * 0.6)
        if (f.x // max(1, f.density)) % 3 == 0:
            col = shade(col, -0.12)               # bark grain
        return shade(col, noise(f, 0.06))
    return p


def claw_dark():
    a, b = hx("2a2620"), hx("d9d2b5")
    return lambda f: shade(mix(a, b, f.v * 0.5), noise(f, 0.05))


# =========================================================================== HANUMAN (Thai khon)

def white_fur(sparkle=True):
    """Hanuman's white fur with diamond glints (ขนเพชร)."""
    a, b = hx("f7f5ee"), hx("c9c6bd")

    def p(f):
        col = mix(a, b, f.v * 0.55)
        ux, uy = U(f)
        if (f.x + 2 * f.y) % 5 == 0:
            col = shade(col, -0.06)               # fur strands
        if sparkle and H(f.x, f.y, f.cube_index) < 0.012:
            col = hx("e6fbff")
        return shade(col, noise(f, 0.03))
    return p


def thai_gold(gems=True):
    """Gold with kranok (flame) relief rows and red/green gem dots."""
    g, d, red, grn = hx("f2c84b"), hx("9a6512"), hx("d1172c"), hx("19a35a")

    def p(f):
        ux, uy = U(f)
        col = mix(g, d, f.v * 0.45)
        cx = ux % 3.0
        cy = uy % 3.0
        # kranok: teardrop flames pointing up
        k = (cx - 1.5) ** 2 * 1.6 + (cy - 1.8) ** 2 * (0.9 if cy > 1.8 else 2.2)
        if 0.55 < k < 0.95:
            col = shade(col, -0.32)
        elif k < 0.3:
            col = shade(col, 0.12)
        if gems and f.w >= 4 * f.density and (int(ux // 3) + int(uy // 3)) % 4 == 0 and math.hypot(cx - 1.5, cy - 1.5) < 0.45:
            col = red if (int(ux // 3) % 2 == 0) else grn
        if f.y == 0:
            col = shade(col, 0.25)
        return shade(col, noise(f, 0.03))
    return p


def thai_cloth(base="b0122a", border="f2c84b"):
    """Silk with a gold brocade border and a small diamond motif."""
    b, br = hx(base), hx(border)

    def p(f):
        ux, uy = U(f)
        col = shade(b, noise(f, 0.03) - f.v * 0.12)
        if f.v > 0.86 or f.u < 0.06 or f.u > 0.94:
            col = br
        elif (int(ux * 1.2) + int(uy * 1.2)) % 3 == 0 and abs((ux * 1.2) % 1 - 0.5) + abs((uy * 1.2) % 1 - 0.5) < 0.3:
            col = mix(col, br, 0.6)
        return col
    return p


def khon_face():
    """Decal for Hanuman's khon face front: gold-rimmed round eyes, mother-of-pearl dots, red mouth line."""
    gold, pearl, red, blk, grn = hx("e9b83a"), hx("dff2ff"), hx("c8102e"), hx("161012"), hx("2bbf6a")

    def d(setp, w, h):
        for y in range(h):
            for x in range(w):
                nx, ny = x / w, y / h
                dx = abs(nx - 0.5)
                # brow arcs
                if abs(ny - (0.3 - (dx - 0.25) ** 2 * 1.4)) < 0.035 and 0.05 < dx < 0.45:
                    setp(x, y, gold)
                # eye rims (the irises are separate glow cubes)
                e = ((dx - 0.24) / 0.15) ** 2 + ((ny - 0.47) / 0.12) ** 2
                if 1.0 < e < 1.6:
                    setp(x, y, grn)
                # nose
                if dx < 0.06 and 0.55 < ny < 0.66:
                    setp(x, y, blk)
                # cheek pearls
                if ((dx - 0.36) ** 2 + (ny - 0.68) ** 2) < 0.0018:
                    setp(x, y, pearl)
                # forehead jewel line
                if dx < 0.025 and 0.08 < ny < 0.26:
                    setp(x, y, red)
                if abs(ny - 0.86) < 0.025 and dx < 0.3:
                    setp(x, y, red)
    return d


def crystal(tint="d9fbff"):
    t = hx(tint)
    return lambda f: shade(t, noise(f, 0.04) + (0.12 if (f.x + f.y) % 4 == 0 else 0))


def steel():
    a, b = hx("d7dde6"), hx("7d8794")
    return lambda f: shade(mix(a, b, f.v * 0.6), noise(f, 0.04) + (0.2 if f.y == 0 else 0))


# =========================================================================== ALICORN

def pearl_coat():
    """Pearlescent white coat: lavender in the shadows, faint cyan sheen on top."""
    w, lav, cy = hx("fbf8ff"), hx("d8cdf0"), hx("e6fbff")

    def p(f):
        col = mix(w, lav, f.v * 0.55)
        if f.face == "up":
            col = mix(col, cy, 0.25)
        ux, uy = U(f)
        if (f.x + f.y * 3) % 7 == 0:
            col = shade(col, -0.04)
        return shade(col, noise(f, 0.02))
    return p


def aurora(alpha_tips=False):
    """Glow gradient through pink, violet and cyan along the strand (v)."""
    stops = [hx("ffd6f4"), hx("ff8ad8"), hx("b48cff"), hx("7fe0ff"), hx("d8fff6")]

    def p(f):
        t = f.v * (len(stops) - 1)
        i = min(len(stops) - 2, int(t))
        col = mix(stops[i], stops[i + 1], t - i)
        if abs(f.u - 0.5) > 0.42:
            col = shade(col, -0.25)
        return col
    return p


def feather_mat(tip="e9c35a"):
    w, g, t = hx("fdfcff"), hx("cfc8e8"), hx(tip)

    def p(f):
        col = mix(w, g, abs(f.u - 0.5) * 1.4)
        if abs(f.u - 0.5) < 0.06:
            col = shade(col, -0.12)               # rachis
        if f.v > 0.88 and f.face in ("up", "down"):
            col = mix(col, t, 0.8)
        return shade(col, noise(f, 0.02))
    return p


def star_gold():
    g, d = hx("ffe08a"), hx("c08a1a")
    return lambda f: shade(mix(g, d, f.v * 0.6), noise(f, 0.04) + (0.25 if f.y == 0 else 0))


# =========================================================================== TENKO

def fox_fur(base="fffaf0", shade_col="e9d9b8", sock=None):
    """Celestial fox fur: warm white with a gold sheen, soft strands; optional vermilion socks (low v)."""
    a, b = hx(base), hx(shade_col)

    def p(f):
        if var("illusion"):
            col = mix(hx("cfe6ff"), hx("6a8cff"), f.v * 0.7)
            return shade(col, noise(f, 0.03))
        col = mix(a, b, f.v * 0.6)
        if (f.x * 2 + f.y) % 6 == 0:
            col = shade(col, -0.05)
        if sock and f.v > 0.55 and f.face in ("north", "south", "east", "west"):
            col = mix(col, hx(sock), min(1.0, (f.v - 0.55) * 4))
        return shade(col, noise(f, 0.025))
    return p


def vermilion():
    return lambda f: (shade(hx("9ab8ff"), noise(f, 0.03)) if var("illusion") else shade(mix(hx("e8381f"), hx("a3170c"), f.v * 0.6), noise(f, 0.03)))


def shimenawa():
    r, w = hx("d11f1f"), hx("f6f1e4")

    def p(f):
        k = int((f.x + f.y) / max(1, f.density))
        return shade(r if k % 4 < 2 else w, noise(f, 0.03) - (0.15 if (f.x + f.y) % (2 * f.density) == 0 else 0))
    return p


def ofuda():
    paper, ink, red = hx("f4eedc"), hx("1a1410"), hx("c41818")

    def p(f):
        col = shade(paper, noise(f, 0.02))
        if abs(f.u - 0.5) < 0.08 and 0.15 < f.v < 0.85 and (f.y // max(1, f.density)) % 2 == 0:
            col = ink
        if abs(f.u - 0.5) < 0.18 and abs(f.v - 0.2) < 0.06:
            col = red
        return col
    return p


def kitsune_face():
    """Decal: vermilion kitsune make-up lines (front of the skull)."""
    red, gold = hx("e3261a"), hx("f2c14a")

    def d(setp, w, h):
        for y in range(h):
            for x in range(w):
                nx, ny = x / w, y / h
                dx = abs(nx - 0.5)
                if abs(ny - (0.25 + dx * 0.6)) < 0.04 and 0.08 < dx < 0.45:
                    setp(x, y, red)              # upswept brow strokes
                if dx < 0.035 and 0.05 < ny < 0.3:
                    setp(x, y, gold)             # forehead jewel line
                if ((dx) ** 2 + (ny - 0.12) ** 2) < 0.004:
                    setp(x, y, red)
    return d


# =========================================================================== THE WORD (Logos) & Choir

def divine_gold(glyphs=True):
    """Bright gold with engraved glyph rows (letters of the Word)."""
    g, d, ink = hx("ffe28a"), hx("c8901e"), hx("7a4a08")

    def p(f):
        col = mix(g, d, f.v * 0.5)
        ux, uy = U(f)
        if glyphs and f.w > 3 * f.density:
            cx, cy = int(ux // 2), int(uy // 3)
            lx, ly = ux % 2, uy % 3
            hsh = H(cx, cy, f.cube_index)
            if 0.3 < lx < 1.6 and 0.5 < ly < 2.4:
                if (hsh < 0.33 and abs(lx - 0.95) < 0.22) or (0.33 <= hsh < 0.66 and abs(ly - 1.45) < 0.22) or (hsh >= 0.66 and abs(lx - ly + 0.5) < 0.25):
                    col = ink
        if f.y == 0:
            col = shade(col, 0.25)
        return shade(col, noise(f, 0.03))
    return p


def parchment():
    a, b, ink, gold = hx("f6ecd2"), hx("d9c79c"), hx("5a3a1a"), hx("e8b84a")

    def p(f):
        col = mix(a, b, f.v * 0.5)
        if f.face in ("up", "down", "north", "south") and f.w > 4 * f.density:
            ux, uy = U(f)
            if 0.12 < f.u < 0.88 and 0.1 < f.v < 0.9 and (uy % 1.5) < 0.35 and H(int(ux * 2), int(uy / 1.5), f.cube_index) > 0.18:
                col = ink
        if f.u < 0.05 or f.u > 0.95 or f.v < 0.04 or f.v > 0.96:
            col = gold
        return shade(col, noise(f, 0.02))
    return p


def wax_seal():
    a, b, gold = hx("b3122a"), hx("6a0814"), hx("f2c84b")

    def p(f):
        col = mix(a, b, math.hypot(f.u - 0.5, f.v - 0.5) * 1.4)
        if f.face in ("north", "south"):
            r = math.hypot(f.u - 0.5, f.v - 0.5)
            if abs(r - 0.3) < 0.04 or (abs(f.u - 0.5) < 0.04 and r < 0.3) or (abs(f.v - 0.45) < 0.04 and r < 0.22):
                col = gold
        return shade(col, noise(f, 0.03))
    return p


def eye_decal(iris="ffd040", pupil="140a02"):
    ir, pu, ring_ = hx(iris), hx(pupil), hx("fff6d0")

    def d(setp, w, h):
        for y in range(h):
            for x in range(w):
                nx, ny = (x + 0.5) / w - 0.5, (y + 0.5) / h - 0.5
                r = math.hypot(nx, ny * 1.15)
                if r < 0.34:
                    setp(x, y, pu if r < 0.12 else (ring_ if r > 0.3 else ir))
    return d


def burnished_bronze():
    a, b = hx("d9a24a"), hx("7a4a14")

    def p(f):
        col = mix(a, b, f.v * 0.7)
        if (f.x + f.y) % 9 == 0:
            col = shade(col, 0.15)                # burnished glints
        if f.y == 0:
            col = shade(col, 0.3)
        return shade(col, noise(f, 0.04))
    return p


def beryl():
    a, b = hx("7fe6c8"), hx("2a8a78")
    return lambda f: shade(mix(a, b, f.v * 0.7), noise(f, 0.04) + (0.2 if f.y == 0 else 0))
