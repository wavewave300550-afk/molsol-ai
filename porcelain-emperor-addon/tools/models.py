"""
Models of "The Porcelain Emperor" add-on, described with modelkit.

Design language of the Emperor:
  * a serpentine imperial dragon whose body is a chain of hollow porcelain
    rings floating around a spine of golden light (the gaps are part of the
    silhouette, the body is literally "already broken"),
  * a serene human porcelain mask set in the dragon's brow, veiled by the bead
    curtain of a floating imperial crown board (mianliu), above a muzzle whose
    lower jaw is split into two mandibles that open sideways,
  * dorsal "Edict Tablets" standing along the spine - the shards it fires,
  * five-clawed limbs that float detached from the body, tethered by gold,
  * a tail that ends in a ruyi sceptre head,
  * a lidded vessel-heart of molten gold in the chest.
"""
from __future__ import annotations

import math

from modelkit import (PAL, Model, glow, hx, m_claw, m_core, m_gold, m_jade, m_lacquer, m_marble, m_pearl,
                      m_ribbon, m_solid, m_tablet, mix, opaque, shade, hash01)

CHEST_Y = 30          # height of the spine above the entity origin (px)
SEGMENTS = 7           # body rings behind the chest
PLATES = 6             # dorsal edict tablets (segments 1..6)
HEAD_SCALE = 1.3       # the head (with crown, mask and whiskers) is built at 1.3x


# --------------------------------------------------------------------------- decals

def mask_decal(setp, w, h, variant):
    """Serene imperial face on the brow mask (left-right symmetric)."""
    cx = (w - 1) / 2.0
    ink = PAL["ink"]
    gold = PAL["gold"]
    for x in range(w):
        dx = abs(x - cx)
        # brows: thin cobalt arcs
        if 1.5 <= dx <= 3.6:
            setp(x, 2 if dx < 2.6 else 3, opaque(PAL["cobalt"]))
        # eyes: closed serene lines (variant 0/1), open golden slits (variant 2)
        if 1.0 <= dx <= 3.2:
            if variant < 2:
                setp(x, 4, opaque(ink))
            else:
                setp(x, 4, glow(PAL["core_hot"], 1.0))
                setp(x, 5, glow(PAL["core"], 0.8))
        # lips: small vermilion
        if dx <= 1.2:
            setp(x, h - 3, opaque(PAL["red"]))
    # forehead seal (urna)
    setp(int(cx), 1, opaque(PAL["red_hi"]))
    if w % 2 == 0:
        setp(int(cx) + 1, 1, opaque(PAL["red_hi"]))
    # kintsugi seam through the face, growing per variant
    if variant >= 1:
        x = int(cx) + 1
        for y in range(h):
            setp(x, y, glow(gold, 0.6))
            if y % 3 == 2:
                x += 1 if (y // 3) % 2 == 0 else -1
    if variant >= 2:
        x = int(cx) - 2
        for y in range(h // 2, h):
            setp(x, y, glow(PAL["gold_hi"], 0.7))
            if y % 2 == 0:
                x -= 1


def seal_decal(setp, w, h, variant):
    """Red imperial seal stamp (square with gold border)."""
    for y in range(h):
        for x in range(w):
            if x in (0, w - 1) or y in (0, h - 1):
                setp(x, y, glow(PAL["gold"], 0.35))
            elif (x + y) % 3 == 0:
                setp(x, y, opaque(PAL["red_hi"]))
            else:
                setp(x, y, opaque(PAL["red"]))


def belly_band_decal(setp, w, h, variant):
    for y in range(h):
        if y % 4 == 3:
            for x in range(w):
                setp(x, y, glow(PAL["gold_mid"], 0.2))


def m_belly() -> callable:
    base = m_marble("ivory_mid", 0.6)

    def p(f):
        col = base(f)
        if col[3] == 255 and f.face == "down" and f.y % 4 == 3:
            return glow(PAL["gold_mid"], 0.2)
        return col
    return p


def m_bead(kind: str):
    if kind == "jade":
        return m_jade()
    if kind == "pearl":
        return m_pearl()
    return m_gold(0.3)


def m_thread():
    return m_solid(PAL["gold"], 0.05, glow_amt=0.4)


def m_teeth():
    def p(f):
        return glow(mix(PAL["gold_hi"], PAL["gold"], f.v), 0.35)
    return p


# --------------------------------------------------------------------------- helpers

def m_seal():
    def p(f):
        if f.x in (0, f.w - 1) or f.y in (0, f.h - 1):
            return glow(PAL["gold"], 0.35)
        return opaque(PAL["red_hi"] if (f.x * 3 + f.y) % 4 == 0 else PAL["red"])
    return p


def ring(m: Model, name: str, parent: str, z0: float, z1: float, width: float, height: float,
         y: float = CHEST_Y, rotation=None, hide_top: bool = False, plate: int = 0, studs: bool = False,
         seal: bool = False):
    """A porcelain ring (octagonal cross-section) around a glowing spine, spanning z0 -> z1.
    The shell is 3px shorter than the ring, so neighbouring rings show the golden core."""
    d = 1 if z1 >= z0 else -1
    length = abs(z1 - z0)
    seg = m.bone(name, (0, y, z0), parent, rotation=rotation)
    zc = (z0 + z1) / 2
    seg.box((0, y, zc), (max(5, width * 0.45), max(5, height * 0.45), length + 0.6), m_core(),
            faces=("east", "west", "up", "down"))
    sl = length - 3
    zs = z0 + d * (1.5 + sl / 2)
    marble = m_marble("ivory")
    W, H = width, height
    sh = min(4, W / 5)
    top_bone = m.bone(f"{name}_top", (0, y + H / 2, zs), name) if hide_top else seg
    top_bone.box((0, y + H / 2 - 1.5, zs), (W - 2 * sh, 3, sl), marble, faces=("up", "north", "south"))
    for sx in (-1, 1):
        outer = "east" if sx < 0 else "west"
        top_bone.box((sx * (W / 2 - sh / 2), y + H / 2 - sh / 2 - 1, zs), (sh, sh, sl), marble,
                     faces=("up", "north", "south", outer))
        seg.box((sx * (W / 2 - 1.5), y, zs), (3, max(2, H - 2 * sh - 4), sl), marble, faces=("north", "south", outer))
        seg.box((sx * (W / 2 - sh / 2), y - H / 2 + sh / 2 + 1, zs), (sh, sh, sl), m_belly(),
                faces=("down", "north", "south", outer))
        if seal:
            seg.box((sx * (W / 2 + 0.25), y + 1, zs), (0.5, 5, 5), m_seal(), faces=(outer,))
    seg.box((0, y - H / 2 + 1.5, zs), (W - 2 * sh, 3, sl), m_belly(), faces=("down", "north", "south"))
    # gold rim at the leading edge
    seg.box((0, y + H / 2 - 0.4, z0 + d * 1.0), (W - 2 * sh + 1, 1.2, 1.2), m_gold(0.35), faces=("up", "north", "south"))
    if plate:
        th = 10 + plate * 0.0 + max(0, 15 - plate)
        pl = m.bone(f"plate{plate}", (0, y + H / 2, zs), name, rotation=(-14, 0, 0))
        pl.box((0, y + H / 2 + th / 2 + 0.6, zs), (2, th, min(9, sl - 2)), m_tablet(),
               faces=("east", "west", "up", "north", "south"))
        pl.box((0, y + H / 2 + 0.3, zs), (3.2, 1.6, min(10, sl - 1)), m_gold(0.3), faces=("east", "west", "up", "north", "south"))
        pl.box((0, y + H / 2 + th + 1.1, zs), (2.6, 1.0, min(9.6, sl - 1.4)), m_gold(0.45), faces=("east", "west", "up", "north", "south"))
    if studs:
        seg.box((0, y + H / 2 + 1, zs), (2, 2, 3), m_gold(0.4), faces=("east", "west", "up", "north", "south"))
    return seg


def limb(m: Model, side: int, name: str, parent: str, shoulder, scale: float = 1.0, rest=(-18, 0, 0)):
    """Floating five-clawed limb. side -1 = right (-X), +1 = left (+X)."""
    sx, sy, sz = shoulder
    s = scale
    up = m.bone(f"{name}", (sx, sy, sz), parent, rotation=(rest[0], rest[1], rest[2] * side))
    # golden tether from the body flank to the floating limb
    up.box((sx - side * 3.5 * s, sy + 1, sz), (4 * s, 1.5, 1.5), m_thread())
    up.box((sx, sy - 4.5 * s, sz), (6.5 * s, 9 * s, 6.5 * s), m_marble("ivory"))
    up.box((sx, sy - 0.2 * s, sz), (7.2 * s, 1.5, 7.2 * s), m_gold(0.3), faces=("up", "north", "south", "east", "west"))
    up.box((sx + side * 3.4 * s, sy - 4 * s, sz), (0.5, 3.5 * s, 3.5 * s), m_seal(), faces=("east" if side < 0 else "west",))
    fore = m.bone(f"{name}_fore", (sx, sy - 10 * s, sz), name, rotation=(-28, 0, 0))
    fore.box((sx, sy - 14.5 * s, sz - 0.5), (5.2 * s, 9 * s, 5.2 * s), m_marble("ivory"))
    fore.box((sx, sy - 11.5 * s, sz - 0.5), (6.0 * s, 1.6, 6.0 * s), m_gold(0.35), faces=("north", "south", "east", "west", "up"))
    hand = m.bone(f"{name}_hand", (sx, sy - 19.5 * s, sz - 0.5), f"{name}_fore", rotation=(32, 0, 0))
    hand.box((sx, sy - 20.6 * s, sz - 1.5), (6.4 * s, 2.4 * s, 6.4 * s), m_marble("ivory_mid"))
    talons = m.bone(f"{name}_talons", (sx, sy - 21 * s, sz - 4 * s), f"{name}_hand")
    for i in range(5):
        tx = sx + (i - 2) * 1.4 * s
        tz = sz - 4.4 * s if i not in (0, 4) else sz - 3.2 * s
        talons.add((tx - 0.6, sy - 26 * s, tz - 0.6), (1.2, 5 * s, 1.2), m_claw(),
                   pivot=(tx, sy - 21 * s, tz), rotation=(-30 if i not in (0, 4) else -12, 0, (i - 2) * 7))
    return up


def scale_subtree(m: Model, root: str, f: float):
    """Uniformly scale a bone and all its descendants about the root bone's pivot."""
    names = {root}
    changed = True
    while changed:
        changed = False
        for b in m.bones:
            if b.parent in names and b.name not in names:
                names.add(b.name)
                changed = True
    px, py, pz = m.get(root).pivot

    def sp(p):
        return (px + (p[0] - px) * f, py + (p[1] - py) * f, pz + (p[2] - pz) * f)
    for b in m.bones:
        if b.name not in names:
            continue
        b.pivot = sp(b.pivot)
        for c in b.cubes:
            c.origin = sp(c.origin)
            c.size = tuple(v * f for v in c.size)
            if c.pivot:
                c.pivot = sp(c.pivot)


# --------------------------------------------------------------------------- the Emperor

def emperor() -> Model:
    m = Model("geometry.porcelain.emperor", seed=1101)
    y = CHEST_Y
    m.bone("root", (0, y, 0))
    body = m.bone("body", (0, y, 0), "root")
    marble = m_marble("ivory")
    # thorax: octagonal shell W 26 x H 24, z -16 .. +10
    W, H, zc, L = 26, 24, -3, 26
    sh = 5
    body.box((0, y, zc), (14, 14, L - 2), m_core(), faces=("up", "down", "east", "west", "south"))
    body.box((0, y + H / 2 - 1.5, zc), (W - 2 * sh, 3, L), marble, faces=("up", "north", "south"))
    for sx in (-1, 1):
        outer = "east" if sx < 0 else "west"
        body.box((sx * (W / 2 - sh / 2), y + H / 2 - sh / 2 - 1, zc), (sh, sh, L), marble, faces=("up", "north", "south", outer))
        body.box((sx * (W / 2 - 1.5), y, zc), (3, H - 2 * sh - 4, L), marble, faces=("north", "south", outer))
        body.box((sx * (W / 2 - sh / 2), y - H / 2 + sh / 2 + 1, zc + 4), (sh, sh, L - 8), m_belly(), faces=("down", "south", outer))
        body.box((sx * (W / 2 + 0.25), y + 1.5, zc - 2), (0.5, 7, 7), m_seal(), faces=(outer,))
    body.box((0, y - H / 2 + 1.5, zc + 4), (W - 2 * sh, 3, L - 8), m_belly(), faces=("down", "south"))
    # gold collar framing the neck joint
    body.box((0, y + H / 2 + 0.25, -16.5), (W - 2 * sh + 2, 1.5, 2), m_gold(0.4))
    for sx in (-1, 1):
        body.box((sx * (W / 2 + 0.25), y + 1, -16.5), (1.5, H - 6, 2), m_gold(0.4))
    # breast plates over the vessel-heart (a slit shows the molten core)
    chest_r = m.bone("chest_r", (-11, y - 3, -17), "body")
    chest_r.add((-11.5, y - 11, -18), (10, 16, 3), m_marble("ivory_hi"))
    chest_r.add((-2.0, y - 11, -18.3), (0.5, 16, 0.5), m_gold(0.5), faces=("north", "west"))
    chest_l = m.bone("chest_l", (11, y - 3, -17), "body")
    chest_l.add((1.5, y - 11, -18), (10, 16, 3), m_marble("ivory_hi"))
    chest_l.add((1.5, y - 11, -18.3), (0.5, 16, 0.5), m_gold(0.5), faces=("north", "east"))
    heart = m.bone("heart", (0, y - 4, -12), "body")
    heart.box((0, y - 4, -12), (9, 11, 9), m_core())
    heart.box((0, y + 2.25, -12), (11, 1.5, 11), m_gold(0.4))
    heart.box((0, y + 3.6, -12), (4, 1.4, 4), m_lacquer("red"))

    # ---- neck (held high: the imperial posture)
    ring(m, "neck1", "body", -16, -29, 18, 16, y=y + 3, rotation=(-32, 0, 0))
    ring(m, "neck2", "neck1", -29, -41, 16, 14, y=y + 3, rotation=(-12, 0, 0))

    # ---- head
    hy = y + 4
    head = m.bone("head", (0, hy, -41), "neck2", rotation=(40, 0, 0))
    head.box((0, hy + 4, -49), (18, 14, 16), m_marble("ivory"))                  # cranium
    head.box((0, hy - 0.5, -65), (14, 8, 17), m_marble("ivory"))                 # muzzle
    head.box((0, hy + 4.25, -65.5), (11, 1.5, 15), m_marble("ivory_hi"), faces=("up", "north", "east", "west"))
    head.box((0, hy + 1.2, -74.2), (9, 5, 1.6), m_marble("ivory_hi"))           # nose
    head.box((0, hy + 4.2, -74.6), (5, 1, 1.0), m_gold(0.5))
    for sx in (-1, 1):
        head.box((sx * 2.4, hy + 1.2, -75.1), (1, 1, 0.4), m_core(), faces=("north",))   # nostrils glow
        outer = "east" if sx < 0 else "west"
        head.box((sx * 9.25, hy + 5, -51), (0.5, 5, 8), m_gold(0.45), faces=(outer,))     # cheek inlay
        head.box((sx * 7.25, hy - 0.5, -66), (0.5, 3, 12), m_gold(0.4), faces=(outer,))
    head.box((0, hy + 11.5, -57.2), (16, 2, 3), m_gold(0.5))                   # brow ridge
    throat = m.bone("throat", (0, hy - 4, -56), "head")
    throat.box((0, hy - 4.5, -62), (8, 2, 18), m_core(), faces=("up", "north", "east", "west"))
    mask = m.bone("mask", (0, hy + 5, -57), "head")
    mask.add((-6.5, hy - 0.5, -59.7), (13, 11, 2), m_marble("ivory_hi", 0.35), decals={"north": mask_decal},
             faces=("north", "east", "west", "up", "down"))
    mask.add((-7.5, hy - 1.5, -58.2), (15, 13, 1), m_gold(0.45), faces=("north", "east", "west", "up", "down"))
    for side, name in ((-1, "jaw_r"), (1, "jaw_l")):
        jaw = m.bone(name, (side * 4.5, hy - 4, -55), "head")
        jx0 = 0.5 if side > 0 else -7.0
        jaw.add((jx0, hy - 8.5, -73), (6.5, 4, 18), m_marble("ivory_mid"))
        tx = 0.6 if side > 0 else -1.6
        for k in range(7):
            jaw.add((tx, hy - 4.6, -72 + k * 2.4), (1, 1.8, 1), m_teeth(), faces=("north", "south", "east", "west", "up"))
        jaw.add((jx0 + (6.4 if side > 0 else -0.4), hy - 7.5, -71), (0.5, 2, 13), m_gold(0.4),
                faces=("west" if side > 0 else "east", "up", "north"))
    # horns: brush-stroke horns sweeping back
    for side, nm in ((-1, "r"), (1, "l")):
        hx0 = side * 6.5
        h1 = m.bone(f"horn_{nm}1", (hx0, hy + 10, -47), "head", rotation=(-50, 0, 20 * side))
        h1.box((hx0, hy + 14.5, -47), (3.5, 9, 3.5), m_marble("ivory"))
        h2 = m.bone(f"horn_{nm}2", (hx0, hy + 19, -47), f"horn_{nm}1", rotation=(-24, 0, 8 * side))
        h2.box((hx0, hy + 23, -47), (2.8, 8, 2.8), m_marble("ivory"))
        h2.box((hx0, hy + 19.6, -47), (3.2, 1.2, 3.2), m_gold(0.4))
        h3 = m.bone(f"horn_{nm}3", (hx0, hy + 27, -47), f"horn_{nm}2", rotation=(-20, 0, 0))
        h3.box((hx0, hy + 30.5, -47), (1.8, 7, 1.8), m_gold(0.5))
    # whiskers: long gold-leaf ribbons flowing from the muzzle
    for side, nm in ((-1, "r"), (1, "l")):
        wx = side * 7.4
        w1 = m.bone(f"wh_{nm}1", (wx, hy + 0.5, -71), "head", rotation=(-8, side * 38, 0))
        w1.add((wx - 0.25, hy - 0.75, -71), (0.5, 2.5, 13), m_ribbon())
        w2 = m.bone(f"wh_{nm}2", (wx, hy + 0.5, -58), f"wh_{nm}1", rotation=(22, side * 14, 0))
        w2.add((wx - 0.25, hy - 0.5, -58), (0.5, 2.0, 13), m_ribbon())
        w3 = m.bone(f"wh_{nm}3", (wx, hy + 0.5, -45), f"wh_{nm}2", rotation=(26, -side * 10, 0))
        w3.add((wx - 0.25, hy - 0.25, -45), (0.5, 1.5, 12), m_ribbon())
    beard = m.bone("beard", (0, hy - 8.5, -66), "head")
    for sx in (-1, 0, 1):
        beard.add((sx * 2.2 - 0.5, hy - 15, -67), (1, 7, 1), m_ribbon(), pivot=(sx * 2.2, hy - 8.5, -66.5),
                  rotation=(22, 0, -12 * sx))
    # mane: gold flame plates fanning behind the head
    mane = m.bone("mane", (0, hy + 9, -42), "head")
    for ang in (-64, -40, -16, 16, 40, 64):
        mane.add((-0.5, hy + 9, -42), (1, 12 - abs(ang) / 10, 6), m_ribbon(), pivot=(0, hy + 9, -40),
                 rotation=(-62, 0, ang))
    # crown: floating mianliu board with bead curtains (veils the mask)
    crown = m.bone("crown", (0, hy + 16, -52), "head", rotation=(6, 0, 0))
    cy = hy + 19.5
    crown.box((0, cy, -52), (24, 1.5, 17), m_lacquer("red"))
    for fz in (-60.25, -43.75):
        crown.box((0, cy + 1.0, fz), (24.5, 0.8, 1.0), m_gold(0.45), faces=("up", "north", "south"))
    for fx in (-12.0, 12.0):
        crown.box((fx, cy + 1.0, -52), (1.0, 0.8, 17.5), m_gold(0.45), faces=("up", "east", "west"))
    crown.box((0, cy - 3.75, -52), (7, 3.5, 7), m_gold(0.3))                    # crown cap (floats)
    crown.box((0, cy + 1.6, -52), (3, 1.6, 3), m_jade())                           # finial
    beads = [("jade", "pearl", "gold"), ("pearl", "jade", "pearl"), ("gold", "jade", "jade")]
    for i, bx in enumerate((-10, -5, 0, 5, 10)):
        s = m.bone(f"bead_f{i}", (bx, cy - 0.75, -60.2), "crown")
        s.add((bx - 0.25, cy - 12, -60.45), (0.5, 11.25, 0.5), m_thread(), faces=("north", "south", "east", "west"))
        for k, kind in enumerate(beads[i % 3]):
            s.box((bx, cy - 3.5 - k * 3.6, -60.2), (1.8, 1.8, 1.8), m_bead(kind))
    for i, bx in enumerate((-8, 0, 8)):
        s = m.bone(f"bead_b{i}", (bx, cy - 0.75, -43.8), "crown")
        s.add((bx - 0.25, cy - 9, -44.05), (0.5, 8.25, 0.5), m_thread(), faces=("north", "south", "east", "west"))
        for k, kind in enumerate(("pearl", "jade")):
            s.box((bx, cy - 3.5 - k * 3.4, -43.8), (1.8, 1.8, 1.8), m_bead(kind))

    scale_subtree(m, "head", HEAD_SCALE)

    # ---- front limbs float beside the thorax
    limb(m, -1, "arm_r", "body", (-19, y - 2, -8), 1.35)
    limb(m, 1, "arm_l", "body", (19, y - 2, -8), 1.35)

    # ---- body rings
    z = 10.0
    parent = "body"
    dims = [(22, 25, 22), (21, 23.5, 20.5), (20, 22, 19), (19, 20, 17.5), (18, 18, 16), (17, 16, 14.5), (16, 14, 13)]
    for i, (length, width, height) in enumerate(dims, start=1):
        ring(m, f"seg{i}", parent, z, z + length, width, height, hide_top=i in (2, 4, 6),
             plate=i if i <= PLATES else 0, studs=i > PLATES, seal=i in (3, 5))
        if i == 4:
            limb(m, -1, "leg_r", "seg4", (-(width / 2 + 4), y - 2, z + length / 2), 1.0, rest=(-34, 0, 0))
            limb(m, 1, "leg_l", "seg4", ((width / 2 + 4), y - 2, z + length / 2), 1.0, rest=(-34, 0, 0))
        parent = f"seg{i}"
        z += length
    for i, (length, width, height) in enumerate(((14, 12, 11), (12, 10, 9), (10, 8, 7)), start=1):
        ring(m, f"tail{i}", parent, z, z + length, width, height, studs=True)
        parent = f"tail{i}"
        z += length
    # ruyi sceptre head (the tail's hammer)
    ruyi = m.bone("ruyi", (0, y, z), parent)
    rz = z + 10
    ruyi.box((0, y, z + 2), (3.5, 3.5, 4), m_gold(0.4))
    ruyi.box((0, y, rz), (3, 14, 14), m_marble("ivory_hi"))
    ruyi.box((0, y + 8, rz - 1.5), (3, 4, 9), m_marble("ivory_hi"))
    ruyi.box((0, y - 8, rz - 1.5), (3, 4, 9), m_marble("ivory_hi"))
    ruyi.box((0, y, rz + 8.5), (3, 8, 4), m_marble("ivory_hi"))
    ruyi.box((0, y, rz), (3.6, 5, 5), m_lacquer("red"))
    ruyi.box((0, y, rz), (3.4, 15.5, 1.2), m_gold(0.45), faces=("east", "west", "up", "down"))
    ruyi.box((0, y, rz), (3.4, 1.2, 15.5), m_gold(0.45), faces=("east", "west", "north", "south"))
    m.tail_end = rz + 10.5  # type: ignore[attr-defined]
    return m


# idle pose used for previews (mirrors the base of the idle animation)
IDLE_POSE = {
    "seg1": (2, 10, 0), "seg2": (-2, 12, 0), "seg3": (2, -14, 0), "seg4": (-1, -16, 0), "seg5": (2, 12, 0),
    "seg6": (0, 16, 0), "seg7": (2, -10, 0), "tail1": (0, -14, 0), "tail2": (4, -12, 0), "tail3": (4, 10, 0),
    "arm_r": (-10, 0, 0), "arm_l": (18, 0, 0),
}


# --------------------------------------------------------------------------- projectiles / fragments

def edict_tablet() -> Model:
    """Large edict tablet: flies like a thrown slab, then stands embedded as a monolith."""
    m = Model("geometry.porcelain.edict_tablet", seed=2203)
    t = m.bone("tablet", (0, 0, 0))
    t.box((0, 13, 0), (3, 24, 12), m_tablet(), faces=("north", "south", "east", "west", "up", "down"))
    t.box((0, 1, 0), (4, 2, 13), m_gold(0.35))
    t.box((0, 25.5, 0), (4, 1.5, 13), m_gold(0.4))
    t.box((0, 19, 0), (3.6, 5, 5), m_lacquer("red"), faces=("east", "west"))
    glowb = m.bone("halo", (0, 13, 0), "tablet")
    glowb.box((0, 13, 0), (1, 26, 14), m_core(), faces=("north", "south"))
    return m


def shard() -> Model:
    """Small porcelain shard with a glowing kintsugi edge."""
    m = Model("geometry.porcelain.shard", seed=2207)
    b = m.bone("shard", (0, 4, 0))
    b.add((-3, 1, -0.75), (6, 6, 1.5), m_marble("ivory_hi", 1.5), pivot=(0, 4, 0), rotation=(0, 0, 45))
    b.add((-1.5, 4, -1), (3, 5, 2), m_marble("ivory", 1.5), pivot=(0, 4, 0), rotation=(12, 20, -18))
    b.add((-3.5, 3.5, -0.4), (7, 0.8, 0.8), m_gold(0.6), pivot=(0, 4, 0), rotation=(0, 0, 45))
    return m


def rubble() -> Model:
    """A broken chunk of the palace floor: marble tile with a gold seam."""
    m = Model("geometry.porcelain.rubble", seed=2211)
    b = m.bone("chunk", (0, 8, 0))
    b.box((0, 8, 0), (14, 12, 14), m_marble("ivory", 1.4))
    b.box((0, 14.4, 0), (14.6, 1, 2), m_gold(0.55), faces=("up", "east", "west"))
    b.box((-5, 2, 3), (6, 5, 6), m_marble("ivory_mid", 1.2), faces=("north", "south", "east", "west", "down"))
    b.box((4, 3, -4), (5, 4, 4), m_marble("ivory_mid", 1.2), faces=("north", "south", "east", "west", "down"))
    peb = m.bone("pebbles", (0, 8, 0), "chunk")
    for i in range(3):
        a = i * 2.1
        peb.box((math.cos(a) * 11, 8 + i * 2 - 2, math.sin(a) * 11), (2, 2, 2), m_marble("ivory_hi", 1.0))
    return m


def severed_claw() -> Model:
    """The Emperor's detached claw: forearm, five gold talons and a golden wrist-light."""
    m = Model("geometry.porcelain.severed_claw", seed=2213)
    s = 1.0
    root = m.bone("claw", (0, 16, 0))
    root.box((0, 22, 0), (8, 12, 8), m_marble("ivory"))
    root.box((0, 16.5, 0), (9, 2, 9), m_gold(0.4))
    root.box((0, 15, 0), (6, 2, 6), m_core())
    palm = m.bone("palm", (0, 14, 0), "claw")
    palm.box((0, 12, -1), (9, 3, 9), m_marble("ivory_mid"))
    tal = m.bone("talons", (0, 11, -3), "palm")
    for i in range(5):
        tx = (i - 2) * 2.0
        tz = -5.2 if i not in (0, 4) else -3.6
        tal.add((tx - 0.75, 3, tz - 0.75), (1.5, 8 * s, 1.5), m_claw(), pivot=(tx, 11, tz),
                rotation=(-35 if i not in (0, 4) else -15, 0, (i - 2) * 8))
    return m


def courtier() -> Model:
    """Porcelain courtier: a kneeling servant doll of blue-and-white porcelain that
    rises from un-shattered shards in the final phase."""
    m = Model("geometry.porcelain.courtier", seed=2221)

    def m_robe():
        base = m_marble("ivory_hi", 0.8)

        def p(f):
            col = base(f)
            if col[3] != 255:
                return col
            if f.face in ("north", "south", "east", "west"):
                wave = math.sin(f.x * 0.9 + f.y * 0.3) * 1.5
                if abs((f.y % 6) - 3 - wave) < 0.7:
                    return opaque(PAL["cobalt"])
                if f.y >= f.h - 2:
                    return opaque(PAL["cobalt_lo"])
            return col
        return p

    def face_decal(setp, w, h, variant):
        cx = (w - 1) / 2
        for x in range(w):
            dx = abs(x - cx)
            if 1 <= dx <= 2.5:
                setp(x, h // 2 - 1, opaque(PAL["ink"]))
            if dx < 1:
                setp(x, h - 2, opaque(PAL["red"]))
        setp(int(cx), 1, opaque(PAL["red_hi"]))
    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 12, 0), "root")
    body.box((0, 7, 0), (10, 10, 7), m_robe())
    body.box((0, 15, 0), (8, 6, 5), m_robe())
    body.box((0, 12.5, -2.6), (3, 3, 0.4), m_core(), faces=("north",))
    head = m.bone("head", (0, 18, 0), "body")
    head.add((-3.5, 18, -3.5), (7, 7, 7), m_marble("ivory_hi", 0.6), decals={"north": face_decal})
    head.box((0, 26, 0.5), (4, 2.5, 4), m_solid(PAL["ink"]))
    head.box((0, 25.2, 0), (7.6, 0.8, 7.6), m_gold(0.3), faces=("up", "north", "south", "east", "west"))
    for side, nm in ((-1, "arm_r"), (1, "arm_l")):
        a = m.bone(nm, (side * 5, 17, 0), "body")
        a.box((side * 6, 12, 0), (3, 10, 3.5), m_robe())
        a.box((side * 6, 6.5, -0.5), (3.6, 2, 4.4), m_robe())
        a.box((side * 6, 5, -1), (1.5, 1.5, 1.5), m_claw())
    for side, nm in ((-1, "leg_r"), (1, "leg_l")):
        lg = m.bone(nm, (side * 2.5, 4, 0), "body")
        lg.box((side * 2.5, 2, 0), (3.5, 4, 4), m_robe())
    return m


ALL = {
    "emperor": emperor,
    "edict_tablet": edict_tablet,
    "shard": shard,
    "rubble": rubble,
    "severed_claw": severed_claw,
    "courtier": courtier,
}

# texture variants per model (the Emperor swaps three damage states)
VARIANTS = {"emperor": 3}

# visible bounds (width, height, y offset) in blocks
BOUNDS = {
    "emperor": (34, 18, 1.5),
    "edict_tablet": (2.5, 2.5, 0.8),
    "shard": (1, 1, 0.25),
    "rubble": (2, 2, 0.5),
    "severed_claw": (2.5, 2.5, 1.0),
    "courtier": (1.6, 2.2, 0.8),
}
