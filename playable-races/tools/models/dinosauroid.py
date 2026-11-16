"""Race 007 - The Unknown Dinosauroid.  (Expansion 02)

An intelligent, calm, quietly unsettling biped that should not exist: a taxonomic
impossibility assembled from prehistoric lineages that never met, grown into one organism.

Design rules (see docs/CREATIVE.md): a clean theropod silhouette - S-necked, big-skulled,
digitigrade, counterweighted by a long tail - with every region its OWN material, painted
as a pixel artist would: dense soft plumage (dark umber, spangled with buff feather tips,
a warm grey-buff underside), long barred flight feathers, stiff keratin bristles, coarse
olive scales, ivory osteoderms, bare leathery skin, thin dusky-crimson membranes on bony
rods and one family of colour-changing display skin (teal by day, luminous at night).

  * skull  - an enlarged dome of a braincase, an oviraptorosaur beak with a row of small
             teeth behind it and an irregular second row, ASYMMETRICAL supraorbital horns
             (the right long and curving forward, the left a blunt stump), a hollow tubular
             hadrosaur crest swept back, plume tufts behind the head, an inflatable gular
             sac, big amber eyes with slit pupils and a nictitating membrane, teal wattles
  * arms   - three digits: two clawed fingers and an elongated styliform digit that
             carries a crimson display membrane; long feather panels from shoulder to
             wrist; the hand ends where the player's hand is, so it holds items
  * legs   - powerful digitigrade running legs (thigh, shank, metatarsus, toes) with a
             raised sickle talon on digit II; Microraptor-style metatarsal feather fans;
             jointed membranes from hip to ankle on bony rods (folded at rest)
  * tail   - five segments: stiff Psittacosaurus bristles on the base, embedded bony
             plates, feather vanes, and a distal feather fan that opens

Variants: base | night (display skin luminous) | display (Crest of Misclassification) |
veer (Hindwing Veer) | overflow (Taxonomic Error: everything at once, luminous eyes).
"""
from __future__ import annotations

import math

import numpy as np

from kit.geo import Model, rot_matrix
from kit import pixel as px
from models.common import accents, ellipsoid, fp_sleeves, humanoid, mat_accent, q, side_rot

ID = "dinosauroid"
VARIANTS = ["base", "night", "display", "veer", "overflow"]
TEXTURES = {
    "base": {"night": 0.0, "overflow": 0.0},
    "night": {"night": 1.0, "overflow": 0.0},
    "overflow": {"night": 0.5, "overflow": 1.0},
}
VARIANT_TEXTURE = {"base": "base", "night": "night", "display": "base", "veer": "base", "overflow": "overflow"}
OPEN = {"display", "overflow"}        # crest raised, pouch inflated, arm fans and tail fan spread, quills up
WINGS = {"veer", "overflow"}          # hindlimb membranes and leg fans deployed
FANNED = {"display", "veer", "overflow"}
SIDES = ((-1, "r"), (1, "l"))
TAIL = 5                              # tail segments

# palettes (dark -> light; shadows cool, highlights warm)
PLUME = px.pal("#1c1613", "#2f2520", "#46372d", "#5e4a3c", "#78604d", "#94795f")
DOWN = px.pal("#4f4337", "#6f604e", "#8f7e66", "#ad9b7f", "#c8b797")
SPANGLE = px.col("#c9b48e")
QUILL = px.pal("#14100d", "#271f19", "#3f3229", "#5f4d3e", "#86715b", "#b3a083", "#d6c8ab")
SCALE = px.pal("#22211d", "#383630", "#524f43", "#6d6a59", "#8b8771")
BONE = px.pal("#574c3c", "#81765c", "#a99c7c", "#ccc09f", "#e8dfc3")
SKIN = px.pal("#3a3330", "#544a45", "#70645c", "#8d8075", "#aa9c8f")
MEMB = px.pal("#220c16", "#3d1525", "#5e2035", "#823249", "#a54f62", "#c47684")
TEAL = px.pal("#0a2a36", "#114857", "#196b77", "#2a9396", "#58bfb4")
LUMI = px.pal("#17606e", "#25a2ad", "#4fd8d8", "#9ef9f0")
IRID = px.pal("#2a1a5c", "#4b2c94", "#2f7fbf", "#3fd0d0", "#b8fff2")
GULAR = px.pal("#3a0a0c", "#661414", "#9a231e", "#c9402a", "#ea7350")
BEAK = px.pal("#1a1817", "#312e2b", "#514c46", "#7f776c", "#b0a693", "#d8ceb8")
CLAW = px.pal("#110f0f", "#272120", "#463c37", "#857a6d", "#cdc3b0")
IRIS = ("#4a2706", "#9a5810", "#d99222", "#ffd24d")

# ----------------------------------------------------------------------------- anatomy (model units, JSON space)
TRUNK_PIVOT = (0.0, 12.0, 0.75)
VEER_LEAN = 24.0                      # the Hindwing Veer throws the body forward
SKULL_PIVOT = (0.0, 26.5, -2.0)
DOME_C = (0.0, 29.0, -1.75)
EYE = (2.0, 28.2, -4.35)              # eye centre (x mirrored per side)
EYE_RY = 30.0                         # eyes turned forward (binocular)
GULAR_PIVOT = (0.0, 26.0, -4.25)
CREST0 = ((0.0, 30.9, -3.1), (0.0, 32.35, -0.4))   # rises steeply from the brow
CREST1 = ((0.0, 32.35, -0.4), (0.0, 33.1, 5.0))    # the tube sweeps back
HIP = (2.4, 12.25, 0.75)
KNEE = (2.65, 7.75, -1.75)
ANKLE = (2.65, 3.75, 1.75)
BALL = (2.65, 0.75, -0.25)
SHOULDER = (4.1, 21.75, -0.75)
ELBOW = (5.4, 17.25, 1.25)
WRIST = (5.95, 13.0, -0.75)
TAIL_PTS = [(0.0, 12.75, 2.5), (0.0, 12.25, 6.25), (0.0, 12.0, 9.5), (0.0, 12.25, 12.5), (0.0, 12.75, 15.0),
            (0.0, 13.25, 17.25)]
TAIL_W = [4.0, 3.25, 2.5, 1.75, 1.25]
TAIL_H = [3.75, 3.0, 2.25, 1.5, 1.0]


def _v(p):
    return np.asarray(p, float)


def _rot(ang, axis):
    """A single-axis cube rotation (None when negligible)."""
    if abs(ang) < 0.05:
        return None
    r = [0.0, 0.0, 0.0]
    r["xyz".index(axis)] = round(ang, 2)
    return tuple(r)


def yseg(m, bone, top, bot, w, d, mat, pad=0.0, **kw):
    """A box whose long axis runs from `top` down to `bot` (same x): rotated about X only."""
    top, bot = _v(top), _v(bot)
    v = bot - top
    L = q(float(math.hypot(v[1], v[2])) + pad)
    r = _rot(math.degrees(math.atan2(v[2], -v[1])), "x")
    c = (top + bot) / 2
    return m.cube(bone, (c[0] - w / 2, c[1] - L / 2, c[2] - d / 2), (w, L, d), mat,
                  pivot=tuple(c) if r else None, rot=r, **kw)


def seg2(m, bone, top, bot, w, d, mat, pad=0.0, **kw):
    """Like yseg, but the segment may also lean sideways (rotation X then Z: two axes)."""
    top, bot = _v(top), _v(bot)
    v = bot - top
    L = float(np.linalg.norm(v))
    dv = v / L
    rx = math.degrees(math.asin(dv[2]))
    rz = math.degrees(math.atan2(-dv[0], -dv[1]))
    c = (top + bot) / 2
    Lq = q(L + pad)
    return m.cube(bone, (c[0] - w / 2, c[1] - Lq / 2, c[2] - d / 2), (w, Lq, d), mat, pivot=tuple(c),
                  rot=(round(rx, 2), 0.0, round(rz, 2)), **kw)


def zseg(m, bone, a, b, w, h, mat, pad=0.0, **kw):
    """A box whose long axis runs along Z from a to b (same x): rotated about X only."""
    a, b = _v(a), _v(b)
    v = b - a
    if v[2] < 0:
        v = -v
    L = q(float(math.hypot(v[1], v[2])) + pad)
    r = _rot(math.degrees(math.atan2(v[1], v[2])), "x")
    c = (a + b) / 2
    return m.cube(bone, (c[0] - w / 2, c[1] - h / 2, c[2] - L / 2), (w, h, L), mat,
                  pivot=tuple(c) if r else None, rot=r, **kw)


def vane(m, bone, root, length, width, mat, rx=0.0, ry=0.0, flat=False, **kw):
    """A cutout feather / membrane plane growing from `root` toward +Z, tilted by rx (a vertical
    plane spanning `width` in Y below the root; +rx lifts the tip) or ry (a horizontal plane
    spanning `width` in X centred on the root; +ry swings the tip toward +X)."""
    x, y, z = root
    if flat:
        o, s, faces, r = (x - width / 2, y, z), (width, 0.0, length), {"up", "down"}, _rot(ry, "y")
    else:
        o, s, faces, r = (x, y - width, z), (0.0, width, length), {"east", "west"}, _rot(rx, "x")
    return m.cube(bone, o, s, mat, pivot=tuple(root) if r else None, rot=r, cutout=True, faces=faces, **kw)


def lean_offset(p, deg, pivot=TRUNK_PIVOT):
    """Displacement of point p when the trunk leans `deg` forward about the hips."""
    piv = _v(pivot)
    v = _v(p) - piv
    return tuple(np.round(rot_matrix((deg, 0, 0)) @ v - v, 3))


# ============================================================================= build

def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=256)
    humanoid(m)
    # the Hindwing Veer throws the trunk forward; head and arm groups follow it exactly
    for g, piv in (("head_g", (0, 24, 0)), ("r_arm_g", (-5, 22, 0)), ("l_arm_g", (5, 22, 0))):
        m.bones[g].variant["veer"] = (lean_offset(piv, VEER_LEAN), None)
    _trunk(m)
    _head(m)
    _arms(m)
    _legs(m)
    _tail(m)
    fp_sleeves(m, "sleeve", width=4.4)
    accents(m, [
        ("c", "breast", "trunk", (0, 19.25, -3.45), (3.5, 3.5, 0.5)),
        ("c", "rsh", "r_upper", (-4.35, 22.0, -0.75), (2.75, 0.5, 2.75)),
        ("c", "lsh", "l_upper", (4.35, 22.0, -0.75), (2.75, 0.5, 2.75)),
        ("l", "r", "r_thigh", (-4.25, 10.75, 0.0), (0.5, 2.5, 2.5)),
        ("l", "l", "l_thigh", (4.25, 10.75, 0.0), (0.5, 2.5, 2.5)),
        ("f", "r", "r_meta", (-2.65, 2.25, 0.4), (1.75, 1.0, 1.75)),
        ("f", "l", "l_meta", (2.65, 2.25, 0.4), (1.75, 1.0, 1.75)),
    ])
    m.pack()
    return m


# ----------------------------------------------------------------------------- trunk: plumage, osteoderms, dorsal quills

def _trunk(m: Model) -> None:
    t = m.bone("trunk", "torso_g", TRUNK_PIVOT)
    t.variant["veer"] = ((0, 0, 0), (VEER_LEAN, 0, 0))
    m.box(t.name, (0, 13.0, 1.25), (5.0, 3.5, 5.0), "body")                            # pelvis
    m.box(t.name, (0, 15.75, 0.5), (4.5, 3.0, 4.5), "body")                            # narrow waist
    ellipsoid(m, t.name, (0, 19.25, -0.5), (6.5, 6.0, 6.0), "body", a=0.68, b=0.88)    # deep chest
    m.cube(t.name, (-2.0, 21.25, -2.5), (4.0, 2.5, 3.5), "plume", pivot=(0, 22.5, -0.75), rot=(-12, 0, 0))   # neck base
    # ankylosaur osteoderms: two rows of small bony plates down the back
    for s in (-1, 1):
        for k, (y, z) in enumerate(((21.0, 2.4), (18.75, 2.75), (16.25, 2.6))):
            m.box(t.name, (s * 1.3, y, z), (1.0, 1.5, 0.5), "osteo")
    # stiff dorsal quills along the spine: they lie back at rest and rise in the display
    for k, (y, z, h, ln) in enumerate(((22.0, 1.6, 3.5, 3.0), (18.75, 2.9, 3.0, 3.0))):
        b = m.bone(f"quill{k}", t.name, (0, y, z), (-72.0, 0, 0))
        b.variant.update({v: ((0, 0, 0), (-8.0 + 8 * k, 0, 0)) for v in OPEN})
        m.cube(b.name, (0, y, z - ln / 2), (0.0, h, ln), "bristle", cutout=True, faces={"east", "west"})
    t.locators["chest"] = (0, 19.5, -3.6)


# ----------------------------------------------------------------------------- head

def _head(m: Model) -> None:
    hg = "head_g"
    yseg(m, hg, (0, 27.25, -2.6), (0, 22.75, -1.25), 3.0, 3.0, "neck")                 # S-neck, upper part
    sk = m.bone("skull", hg, SKULL_PIVOT)
    sk.variant.update({"display": ((0, 0, 0), (-10.0, 0, 0)), "overflow": ((0, 0, 0), (-6.0, 0, 10.0))})
    ellipsoid(m, sk.name, DOME_C, (5.5, 5.0, 5.5), "dome", a=0.62, b=0.86)             # enlarged braincase
    m.box(sk.name, (0, 27.6, -5.0), (3.75, 2.75, 2.25), "face")                        # orbits and cheeks
    m.box(sk.name, (0, 29.4, -4.6), (4.25, 0.75, 1.25), "brow")                        # heavy brow ridge
    # oviraptorosaur beak: deep, parrot-like, hooked
    m.box(sk.name, (0, 27.4, -7.0), (2.5, 2.0, 2.0), "beak")
    m.box(sk.name, (0, 26.75, -8.25), (1.75, 1.75, 1.0), "beak")
    m.box(sk.name, (0, 26.6, -6.25), (2.0, 0.5, 2.5), "mouth")                        # gape (dark)
    for s in (-1, 1):                                                                 # wattles of display skin
        m.box(sk.name, (s * 1.9, 26.6, -4.0), (0.5, 1.5, 1.75), "display")
    # ASYMMETRICAL ceratopsian horns: the right long and curving forward, the left a blunt stump
    seg2(m, sk.name, (-1.6, 32.1, -5.2), (-1.4, 29.6, -4.3), 0.75, 0.75, "horn")
    seg2(m, sk.name, (-1.65, 33.0, -6.6), (-1.6, 31.75, -5.0), 0.5, 0.5, "horn")
    seg2(m, sk.name, (2.05, 31.0, -4.5), (1.45, 29.6, -4.3), 0.75, 0.75, "horn")
    # teeth: a row behind the beak and an irregular second row (exposed as the jaw drops)
    th = m.bone("teeth", sk.name, (0, 26.6, -5.5))
    for s in (-1, 1):
        for z in (-6.0, -5.35, -4.7):
            m.box(th.name, (s * 1.1, 26.15, z), (0.5, 0.5, 0.5), "tooth")
        for z, h, dx in ((-6.55, 0.75, 0.45), (-5.3, 0.5, 0.55)):
            m.box(th.name, (s * dx, 26.45 - h / 2, z), (0.5, h, 0.5), "tooth")
    # lower jaw
    jw = m.bone("jaw", sk.name, (0, 26.35, -3.75))
    jw.variant.update({"display": ((0, 0, 0), (8.0, 0, 0)), "overflow": ((0, 0, 0), (12.0, 0, 0))})
    m.box(jw.name, (0, 25.9, -5.75), (2.5, 1.0, 3.5), "jaw")
    m.box(jw.name, (0, 25.85, -7.75), (1.5, 0.75, 1.0), "beak")
    # eyes: big amber eyes turned forward; slit pupils that contract; a nictitating membrane
    for s, p in SIDES:
        ex, ey, ez = s * EYE[0], EYE[1], EYE[2]
        eb = m.bone(f"{p}_eye", sk.name, (ex, ey, ez), side_rot((0, -EYE_RY, 0), s))
        m.box(eb.name, (ex, ey, ez), (0.5, 2.0, 2.0), "eye", ppu=4.0)
        pu = m.bone(f"{p}_pupil", eb.name, (ex, ey, ez))
        m.box(pu.name, (ex + s * 0.3, ey, ez), (0.1, 1.5, 0.5), "pupil", ppu=4.0)
        nm = m.bone(f"{p}_nict", eb.name, (ex + s * 0.33, ey, ez - 1.0))
        m.cube(nm.name, (ex + s * 0.33 - 0.025, ey - 1.0, ez - 1.0), (0.05, 2.0, 0.1), "nict")
    sk.locators["eyes"] = (0, EYE[1], EYE[2] - 1.2)
    # throat pouch (gular sac): tucked under the jaw at rest, a swollen balloon in the display
    gu = m.bone("gular", sk.name, GULAR_PIVOT)
    ellipsoid(m, gu.name, (0, 25.2, -4.4), (2.25, 1.75, 3.0), "gular", a=0.65, b=0.85, skip=OPEN)
    ellipsoid(m, gu.name, (0, 23.6, -4.75), (4.5, 4.0, 5.0), "gular", a=0.66, b=0.86, only=OPEN)
    gu.locators["throat"] = (0, 24.5, -4.75)
    # the hollow tubular crest: rises from the brow and sweeps back; it lifts and fans a frill in the display
    c0 = m.bone("crest0", sk.name, CREST0[0])
    c0.variant.update({"display": ((0, 0, 0), (26.0, 0, 0)), "overflow": ((0, 0, 0), (20.0, 0, 0))})
    zseg(m, c0.name, CREST0[0], CREST0[1], 1.75, 1.5, "crest", pad=0.75)
    c1 = m.bone("crest1", c0.name, CREST1[0])
    c1.variant.update({"display": ((0, 0, 0), (10.0, 0, 0)), "overflow": ((0, 0, 0), (14.0, 0, 0))})
    zseg(m, c1.name, CREST1[0], CREST1[1], 1.5, 1.5, "crest", pad=0.25)
    zseg(m, c1.name, (0, 32.3, -0.2), (0, 33.0, 4.8), 1.0, 2.0, "crest")
    m.cube(c1.name, (0, 28.5, -0.25), (0.0, 4.0, 5.25), "frill", cutout=True, faces={"east", "west"}, only=OPEN)
    c1.locators["crest_tip"] = (0, CREST1[1][1] + 0.1, CREST1[1][2] + 0.4)
    # plume tufts behind the head
    for s, p in SIDES:
        tf = m.bone(f"{p}_tuft", sk.name, (s * 1.8, 29.5, -0.5), side_rot((0, -18, 0), s))
        tf.variant.update({v: ((0, 0, 0), side_rot((-26, -34, 0), s)) for v in OPEN})
        vane(m, tf.name, (s * 1.8, 30.0, -0.5), 5.0, 1.25, "plumelong", rx=-10)
        vane(m, tf.name, (s * 1.85, 29.0, -0.5), 3.75, 1.0, "plumelong", rx=-30)


# ----------------------------------------------------------------------------- arms: two clawed fingers + a styliform digit

def _arms(m: Model) -> None:
    for s, p in SIDES:
        g = f"{p}_arm_g"
        sh, el, wr = (_v((s * c[0], c[1], c[2])) for c in (SHOULDER, ELBOW, WRIST))
        up = m.bone(f"{p}_upper", g, tuple(sh))
        seg2(m, up.name, sh + (0, 0.5, 0), el, 2.25, 2.5, "plume")
        fo = m.bone(f"{p}_fore", up.name, tuple(el))
        seg2(m, fo.name, el + (0, 0.5, 0.1), wr, 1.75, 1.75, "fore")
        ha = m.bone(f"{p}_hand", fo.name, tuple(wr))
        m.box(ha.name, (wr[0], 12.1, -0.85), (1.5, 1.75, 1.75), "scale")
        yseg(m, ha.name, (wr[0] - s * 0.4, 11.5, -1.5), (wr[0] - s * 0.4, 9.75, -2.0), 0.5, 0.5, "finger")
        yseg(m, ha.name, (wr[0] + s * 0.35, 11.5, -1.25), (wr[0] + s * 0.35, 9.5, -1.75), 0.5, 0.5, "finger")
        # feather panels from shoulder to wrist: a folded wing at rest, two wide fans in the display
        p0 = m.bone(f"{p}_plume0", up.name, (s * 4.7, 21.25, 0.25))
        p0.variant.update({v: ((0, 0, 0), side_rot((0, -72, 0), s)) for v in OPEN})
        m.cube(p0.name, (s * 4.7, 16.75, 0.25), (0.0, 4.5, 3.75), "armfan", cutout=True, faces={"east", "west"},
               pivot=(s * 4.7, 21.25, 0.25), rot=(-22, 0, 0))
        p1 = m.bone(f"{p}_plume1", fo.name, (s * 5.65, 17.25, 1.0))
        p1.variant.update({v: ((0, 0, 0), side_rot((0, -80, 0), s)) for v in OPEN})
        m.cube(p1.name, (s * 5.65, 12.25, 0.5), (0.0, 5.0, 5.0), "armfan", cutout=True, faces={"east", "west"},
               pivot=(s * 5.65, 17.25, 1.0), rot=(-18, 0, 0))
        # the styliform digit: a bony rod from the wrist folded back along the forearm, carrying a membrane
        st = m.bone(f"{p}_stylus", ha.name, (s * 5.4, 12.6, 0.0))
        st.variant.update({v: ((0, 0, 0), side_rot((-30, 0, -78), s)) for v in OPEN})
        yseg(m, st.name, (s * 5.4, 18.0, 2.25), (s * 5.4, 12.35, 0.0), 0.5, 0.5, "rod")
        m.cube(st.name, (s * 5.35, 12.75, -0.25), (0.0, 4.75, 1.75), "memb", cutout=True, faces={"east", "west"},
               skip=OPEN)
        m.cube(st.name, (s * 5.35, 12.25, -2.25), (0.0, 6.0, 4.5), "membw", cutout=True, faces={"east", "west"},
               only=OPEN)


# ----------------------------------------------------------------------------- legs: digitigrade runners with hindwings

def _legs(m: Model) -> None:
    for s, p in SIDES:
        g = f"{p}_leg_g"
        hip, knee, ankle, ball = (_v((s * c[0], c[1], c[2])) for c in (HIP, KNEE, ANKLE, BALL))
        th = m.bone(f"{p}_thigh", g, tuple(hip))
        yseg(m, th.name, hip + (s * 0.1, 0.75, 0.5), hip + (s * 0.15, -3.0, -1.0), 3.25, 4.0, "thigh")   # the drumstick
        yseg(m, th.name, hip + (s * 0.15, -2.0, -0.75), knee + (0, 0, 0.25), 2.25, 2.75, "thigh")
        sh = m.bone(f"{p}_shin", th.name, tuple(knee))
        yseg(m, sh.name, knee + (0, 0.5, 0), ankle, 1.75, 2.0, "shin")
        mt = m.bone(f"{p}_meta", sh.name, tuple(ankle))
        yseg(m, mt.name, ankle + (0, 0.25, 0), ball, 1.25, 1.25, "scale")
        ft = m.bone(f"{p}_foot", mt.name, tuple(ball))
        bx, by, bz = ball
        m.box(ft.name, (bx, 0.375, bz - 1.5), (0.75, 0.75, 3.0), "toe")                    # digit III
        m.cube(ft.name, (bx - 0.375, 0.0, bz - 2.75), (0.75, 0.75, 2.5), "toe", pivot=(bx, 0.4, bz),
               rot=side_rot((0, 24, 0), s))                                                # digit IV
        m.box(ft.name, (bx - s * 0.45, 0.6, bz + 0.85), (0.5, 0.5, 1.0), "toe")            # hallux
        m.box(ft.name, (bx, 0.25, bz - 3.25), (0.5, 0.5, 0.5), "claw")
        # digit II: raised, carrying the enlarged sickle talon
        tx = bx - s * 0.75
        tl = m.bone(f"{p}_talon", ft.name, (tx, 0.75, bz - 0.5))
        zseg(m, tl.name, (tx, 0.75, bz - 0.25), (tx, 1.5, bz - 1.75), 0.6, 0.6, "toe")
        yseg(m, tl.name, (tx, 2.75, bz - 2.25), (tx, 1.25, bz - 1.75), 0.5, 0.6, "claw")
        zseg(m, tl.name, (tx, 2.6, bz - 2.4), (tx, 1.9, bz - 3.4), 0.5, 0.5, "claw")
        tl.locators[f"{p}_sickle"] = (tx, 2.0, bz - 3.3)
        # hindwing membranes on jointed bony rods: hip -> knee and knee -> ankle (folded strips at rest)
        s0 = m.bone(f"{p}_sail0", th.name, (s * 3.1, 12.0, 1.75))
        s0.variant.update({v: ((0, 0, 0), side_rot((8, -12, 70), s)) for v in WINGS})
        yseg(m, s0.name, (s * 3.1, 12.0, 1.75), (s * 3.1, 7.0, -0.25), 0.5, 0.5, "rod")
        m.cube(s0.name, (s * 3.05, 7.25, -0.25), (0.0, 4.75, 1.75), "memb", cutout=True, faces={"east", "west"},
               skip=WINGS)
        m.cube(s0.name, (s * 3.05, 6.0, -0.5), (0.0, 6.0, 6.0), "membw", cutout=True, faces={"east", "west"},
               only=WINGS)
        s1 = m.bone(f"{p}_sail1", sh.name, (s * 2.9, 7.25, -0.5))
        s1.variant.update({v: ((0, 0, 0), side_rot((-6, -16, 62), s)) for v in WINGS})
        yseg(m, s1.name, (s * 2.9, 7.25, -0.5), (s * 2.9, 3.5, 2.75), 0.5, 0.5, "rod")
        m.cube(s1.name, (s * 2.85, 3.75, -0.25), (0.0, 3.75, 2.0), "memb", cutout=True, faces={"east", "west"},
               skip=WINGS)
        m.cube(s1.name, (s * 2.85, 2.5, -0.5), (0.0, 5.25, 6.5), "membw", cutout=True, faces={"east", "west"},
               only=WINGS)
        # Microraptor-style metatarsal feather fans
        lf = m.bone(f"{p}_lfan", mt.name, (s * 2.65, 3.75, 2.25))
        lf.variant.update({v: ((0, 0, 0), side_rot((14, -24, 74), s)) for v in WINGS})
        for k, (ln, rx) in enumerate(((5.25, -22.0), (4.75, -34.0), (4.25, -46.0), (3.5, -58.0))):
            vane(m, lf.name, (s * (2.65 + 0.03 * k), 3.75 + 0.6, 2.25), ln, 1.25, "quill", rx=rx)


# ----------------------------------------------------------------------------- tail: bristles, plates, vanes, the fan

def _tail(m: Model) -> None:
    par = "tail_g"
    names = []
    for k in range(TAIL):
        a, b = TAIL_PTS[k], TAIL_PTS[k + 1]
        tb = m.bone(f"tail{k}", par, a)
        zseg(m, tb.name, a, b, TAIL_W[k], TAIL_H[k], "tail", pad=0.75 if k < TAIL - 1 else 0.25)
        names.append(tb.name)
        par = tb.name
    # display curl: the tail lifts its fan high behind the body
    for k, a in enumerate((0.0, 8.0, 16.0, 18.0, 16.0)):
        if a:
            m.bones[names[k]].variant["display"] = ((0, 0, 0), (a, 0, 0))
            m.bones[names[k]].variant["overflow"] = ((0, 0, 0), (a * 0.6, 0, 0))
    # Psittacosaurus bristles on the tail base
    for k, (y, z, h, ln) in enumerate(((14.6, 3.25, 3.25, 3.5), (13.75, 6.75, 2.75, 3.0))):
        bb = m.bone(f"bristle{k}", names[k], (0, y, z), (-50.0, 0, 0))
        bb.variant.update({v: ((0, 0, 0), (-8.0, 0, 0)) for v in OPEN})
        m.cube(bb.name, (0, y, z - 0.25), (0.0, h, ln), "bristle", cutout=True, faces={"east", "west"})
    # small bony plates embedded along the tail
    for seg, x, y, z in ((1, 1.45, 13.4, 7.75), (2, 1.1, 12.95, 10.5), (2, 1.0, 13.0, 11.75)):
        for s in (-1, 1):
            m.box(names[seg], (s * x, y, z), (0.75, 0.5, 1.0), "osteo")
    # feather vanes along the sides of the distal tail
    for seg, w in ((2, 2.0), (3, 2.0)):
        a = TAIL_PTS[seg]
        for s in (-1, 1):
            hw = TAIL_W[seg] / 2
            m.cube(names[seg], (s * (hw + w / 2) - w / 2, a[1], a[2] + 0.25), (w, 0.0, 3.25), "vane", cutout=True,
                   faces={"up", "down"})
    # the distal fan: closed (narrow) at rest, spread in the display, the veer and the overflow
    tip = TAIL_PTS[-1]
    fc = m.bone("fan", names[-1], tip)
    fc.variant.update({"display": ((0, 0, 0), (50.0, 0, 0)), "veer": ((0, 0, 0), (0, 0, 84.0)),
                       "overflow": ((0, 0, 0), (34.0, 0, 26.0))})
    vane(m, fc.name, tip, 6.5, 1.75, "fanq", flat=True)
    fc.locators["tail_fan"] = (tip[0], tip[1], tip[2] + 3.5)
    for s, p in SIDES:
        fb = m.bone(f"{p}_fan", fc.name, tip, (0, s * 6.0, 0))
        fb.variant.update({v: ((0, 0, 0), (0, s * 46.0, 0)) for v in FANNED})
        vane(m, fb.name, tip, 6.0, 1.75, "fanq", flat=True, ry=s * 14.0)
        vane(m, fb.name, tip, 5.5, 1.75, "fanq", flat=True, ry=s * 30.0)


# ============================================================================= materials

def materials():
    return {
        "body": mat_body, "plume": mat_plume, "neck": mat_neck, "dome": mat_dome, "face": mat_face,
        "brow": mat_brow, "beak": mat_beak, "mouth": mat_mouth, "jaw": mat_jaw, "tooth": mat_tooth,
        "horn": mat_horn, "eye": mat_eye, "pupil": mat_pupil, "nict": mat_nict, "gular": mat_gular,
        "display": mat_display, "crest": mat_crest, "frill": mat_memb, "plumelong": mat_quill, "quill": mat_quill,
        "fanq": mat_quill, "vane": mat_quill, "armfan": mat_quill, "bristle": mat_bristle, "osteo": mat_osteo,
        "fore": mat_fore, "scale": mat_scale, "finger": mat_finger, "rod": mat_rod, "memb": mat_memb,
        "membw": mat_memb, "thigh": mat_thigh, "shin": mat_shin, "toe": mat_scale, "claw": mat_claw,
        "tail": mat_tail, "sleeve": mat_fore, "accent": mat_accent,
    }


def _night(ctx):
    return ctx.params.get("night", 0.0)


def _over(ctx):
    return ctx.params.get("overflow", 0.0)


def _spangles(ctx, c, lv, pal, w=4, h=3, light=SPANGLE, every=1):
    """Spangled plumage: a pale buff tip on each feather of a staggered grid, with a darker
    texel tucked under it - the starling look, kept sparse and low in contrast."""
    ix, iy, W, H = px.texel(ctx)
    row = iy // h
    cx = (ix + (row % 2) * (w // 2) + ctx.seed % w) % w
    cy = iy % h
    tip = (cy == h - 1) & (cx == w // 2) & ((row + (ix // w)) % every == 0)
    shadow = (cy == 0) & (cx == w // 2) & (iy > 0)
    c = np.where(tip[:, None], light * 0.55 + pal[int(len(pal) * 0.6)] * 0.45, c)
    c = np.where(shadow[:, None], pal[max(0, int(len(pal) * 0.2))], c)
    return c


def _plumage(ctx, pal, lv, w=4, h=3, every=1, dither=0.3):
    c = px.quant(ctx, pal, lv, dither=dither)
    return _spangles(ctx, c, lv, pal, w, h, every=every)


def mat_body(ctx):
    """Trunk plumage, countershaded: umber above and behind, warm grey-buff breast and belly."""
    n = ctx.wn if ctx.wn is not None else ctx.n
    lv = px.rim(ctx, px.light(ctx, grad=0.14), 0.07, 0.1)
    if n[1] < -0.5 or n[2] < -0.6:
        c = px.quant(ctx, DOWN, lv + 0.04, dither=0.35)
        ix, iy, W, H = px.texel(ctx)
        fine = ((ix + 2 * (iy // 2)) % 4 == 0) & (iy % 2 == 1)          # soft down: fine dark flecks
        return np.where(fine[:, None], DOWN[1], c), ctx.ones(), ctx.zeros()
    return _plumage(ctx, PLUME, lv), ctx.ones(), ctx.zeros()


def mat_plume(ctx):
    lv = px.rim(ctx, px.light(ctx, grad=0.14), 0.07, 0.1)
    return _plumage(ctx, PLUME, lv), ctx.ones(), ctx.zeros()


def mat_thigh(ctx):
    lv = px.rim(ctx, px.light(ctx, grad=0.16) + 0.02, 0.07, 0.12)
    return _plumage(ctx, PLUME, lv, w=4, h=2, every=2), ctx.ones(), ctx.zeros()


def mat_tail(ctx):
    n = ctx.wn if ctx.wn is not None else ctx.n
    lv = px.rim(ctx, px.light(ctx, grad=0.1), 0.07, 0.1)
    if n[1] < -0.5:
        return px.quant(ctx, DOWN, lv, dither=0.3), ctx.ones(), ctx.zeros()
    return _plumage(ctx, PLUME, lv, w=4, h=2), ctx.ones(), ctx.zeros()


def mat_neck(ctx):
    """The upper neck: plumage behind, bare display skin down the throat (cassowary)."""
    ix, iy, W, H = px.texel(ctx)
    n = ctx.wn if ctx.wn is not None else ctx.n
    if n[2] < -0.5:                                   # throat: bare, colour-changing display skin
        return _display_skin(ctx)
    lv = px.rim(ctx, px.light(ctx, grad=0.12), 0.06, 0.08)
    c = _plumage(ctx, PLUME, lv, w=3, h=2)
    if ctx.face in ("east", "west"):                  # the bare skin wraps a texel around the sides
        front = (ix == (W - 1 if ctx.face == "east" else 0))
        dc, _, dg = _display_skin(ctx)
        return np.where(front[:, None], dc, c), ctx.ones(), np.where(front, dg, 0.0)
    return c, ctx.ones(), ctx.zeros()


def mat_dome(ctx):
    """The braincase: a smooth, finely feathered dome lit as one round form."""
    lv = px.proxy(ctx, DOME_C, (2.8, 2.5, 2.8), 0.85) + 0.03
    return _plumage(ctx, PLUME, lv, w=3, h=2, every=2, dither=0.25), ctx.ones(), ctx.zeros()


def mat_face(ctx):
    lv = px.proxy(ctx, (0, 27.7, -4.6), (2.0, 1.6, 2.0), 0.7)
    c = px.quant(ctx, SKIN, lv + 0.08, dither=0.25)
    return c, ctx.ones(), ctx.zeros()


def mat_brow(ctx):
    return px.shade(ctx, PLUME, offset=-0.02, up=0.14, down=0.2), ctx.ones(), ctx.zeros()


def mat_beak(ctx):
    """Keratin: slate at the base, pale horn at the hooked tip, a pale cutting edge."""
    p = ctx.wp if ctx.wp is not None else ctx.p
    fwd = np.clip((-p[:, 2] - 5.5) / 3.0, 0, 1)
    lv = px.rim(ctx, px.light(ctx, grad=0.12), 0.1, 0.12) + fwd * 0.4 - 0.1
    return px.quant(ctx, BEAK, lv, dither=0.3), ctx.ones(), ctx.zeros()


def mat_jaw(ctx):
    p = ctx.wp if ctx.wp is not None else ctx.p
    fwd = np.clip((-p[:, 2] - 5.5) / 2.5, 0, 1)
    c = px.quant(ctx, SKIN, px.light(ctx, grad=0.1) - 0.02)
    b = px.quant(ctx, BEAK, px.light(ctx) + fwd * 0.35 - 0.1)
    return np.where((fwd > 0.2)[:, None], b, c), ctx.ones(), ctx.zeros()


def mat_mouth(ctx):
    return px.quant(ctx, px.pal("#1a0d0e", "#341518", "#4f2023"), px.light(ctx)), ctx.ones(), ctx.zeros()


def mat_tooth(ctx):
    return px.quant(ctx, BONE, px.light(ctx) + 0.2), ctx.ones(), ctx.zeros()


def mat_horn(ctx):
    p = ctx.wp if ctx.wp is not None else ctx.p
    up = np.clip((p[:, 1] - 29.8) / 2.8, 0, 1)
    lv = px.light(ctx, grad=0.1) - 0.15 + up * 0.5
    return px.quant(ctx, BEAK, lv, dither=0.3), ctx.ones(), ctx.zeros()


EYE_PIX = [".oooooo.",
           "oOOOOOOo",
           "oOYYYYOo",
           "oOYyyYOo",
           "oOYyyYOo",
           "oOYYYYOo",
           "oOOOOOOo",
           ".oooooo."]


def mat_eye(ctx):
    """Big amber eye (painted at 4 texels per unit); the slit pupil is its own sliding piece."""
    night, over = _night(ctx), _over(ctx)
    outer = ctx.wn is not None and abs(ctx.wn[0]) > 0.4 and np.sign(ctx.wn[0]) == np.sign(ctx.p[0, 0])
    if not outer:
        return px.quant(ctx, SKIN, px.light(ctx) - 0.05), ctx.ones(), ctx.zeros()
    c = np.broadcast_to(px.col(SKIN[1]), (ctx.N, 3)).copy()
    cols = {"o": SKIN[0], "O": IRIS[1], "Y": IRIS[2], "y": IRIS[3]}
    if over > 0.5:
        cols = {"o": "#3a1a04", "O": "#e0a020", "Y": "#ffd860", "y": "#fff6c0"}
    gl = 0.0 if night < 0.5 and over < 0.5 else (0.45 if over < 0.5 else 0.9)
    c, g = px.decal(ctx, c, EYE_PIX, cols, 0, 0, glow=ctx.zeros(), glow_chars="OYy" if gl else "", glow_level=gl)
    ix, iy, W, H = px.texel(ctx)
    hi = (iy == 2) & (ix == (2 if ctx.face == "west" else W - 3))          # catch-light toward the front
    c = np.where(hi[:, None], px.col("#fffbea"), c)
    return c, ctx.ones(), g


def mat_pupil(ctx):
    c = np.broadcast_to(px.col("#0b0606"), (ctx.N, 3)).copy()
    ix, iy, W, H = px.texel(ctx)
    if px.side(ctx):
        rim_ = (iy == 0) | (iy == H - 1)
        c = np.where(rim_[:, None], px.col("#2a1306"), c)
    return c, ctx.ones(), ctx.zeros()


def mat_nict(ctx):
    return np.broadcast_to(px.col("#cfd8d4"), (ctx.N, 3)).copy(), ctx.ones(), ctx.zeros()


def _display_skin(ctx, base=0.0):
    """Colour-changing display skin: teal by day, luminous at night, iridescent in the overflow."""
    ix, iy, W, H = px.texel(ctx)
    night, over = _night(ctx), _over(ctx)
    lv = px.rim(ctx, px.light(ctx, grad=0.12), 0.1, 0.08) + base
    bump = ((ix + 2 * (iy // 2)) % 4 == 0) & (iy % 2 == 0)                  # pebbled skin
    lv = lv + np.where(bump, 0.1, 0.0)
    if over > 0.5:
        band = ((ix + iy) // 2) % 5
        c = IRID[np.clip(band, 0, 4)]
        c = np.where(bump[:, None], IRID[4], c)
        return c, ctx.ones(), np.full(ctx.N, 0.8)
    if night > 0.5:
        return px.quant(ctx, LUMI, lv + 0.1), ctx.ones(), np.where(bump, 0.85, 0.65)
    return px.quant(ctx, TEAL, lv, dither=0.2), ctx.ones(), ctx.zeros()


def mat_display(ctx):
    return _display_skin(ctx, 0.05)


def mat_gular(ctx):
    """The throat pouch: crimson skin with folds (it swells smooth in the display)."""
    night, over = _night(ctx), _over(ctx)
    ix, iy, W, H = px.texel(ctx)
    lv = px.proxy(ctx, (0, 24.5, -4.6), (2.2, 2.0, 2.4), 0.8) + 0.08
    fold = (iy % 3 == 2) & (ctx.fw < 3.5)
    lv = lv - np.where(fold, 0.12, 0.0)
    c = px.quant(ctx, GULAR, lv, dither=0.25)
    g = ctx.zeros() if night < 0.5 else np.full(ctx.N, 0.35 + 0.4 * over)
    return c, ctx.ones(), g


def mat_crest(ctx):
    """The hollow tubular crest: bone-pale tube with a stripe of display skin along each side;
    its open end shows the dark lumen."""
    ix, iy, W, H = px.texel(ctx)
    night, over = _night(ctx), _over(ctx)
    c = px.quant(ctx, BONE, px.rim(ctx, px.light(ctx, grad=0.1), 0.12, 0.1) - 0.1, dither=0.2)
    g = ctx.zeros()
    if ctx.face in ("east", "west") and H >= 2:
        stripe = iy == H // 2
        dc, _, dg = _display_skin(ctx, 0.1)
        c = np.where(stripe[:, None], dc, c)
        g = np.where(stripe, dg, 0.0)
    if ctx.face in ("north", "south") and ctx.fw < 1.6 and ctx.fh < 1.6:
        lumen = (ix >= 1) & (ix <= W - 2) & (iy >= 1) & (iy <= H - 2)
        c = np.where(lumen[:, None], px.col("#120a0a"), c)
        g = np.where(lumen, 0.7 * over, g)
        if over > 0.5:
            c = np.where(lumen[:, None], px.col("#7ffff0"), c)
    return c, ctx.ones(), g


def mat_quill(ctx):
    """Long flight feathers (cutout planes growing toward +Z): a pale shaft, barred vanes and a
    dark notched tip; a panel holds several feathers side by side with gaps between the tips."""
    ix, iy, W, H = px.texel(ctx)
    along = ctx.local[:, 2]                                   # 0 at the root .. 1 at the tip
    vertical = ctx.size[0] < 1e-6
    across = ctx.local[:, 1] if vertical else ctx.local[:, 0]
    n_across = H if vertical else W
    k = max(1, int(round(n_across / 3.0)))                   # feathers side by side, ~3 texels each
    pos = across * k
    cell = np.floor(np.minimum(pos, k - 1e-6))
    fr = pos - cell
    half = 1 - np.abs(fr - 0.5) * 2                          # 1 on the shaft .. 0 at the edges
    taper = np.clip((1 - along) / 0.22, 0, 1)                # the last fifth narrows to a point
    stagger = 0.06 * (cell % 2)
    alpha = (half >= (1 - taper) * 0.9 + stagger * 2) | (along < 0.5)
    shaft = half > 0.66
    bar = (np.floor(along * 10 + cell * 1.5) % 3 == 0) & (along > 0.3)
    lv = 0.5 + 0.22 * half - 0.18 * along
    lv = lv - np.where(bar, 0.14, 0.0) + np.where(shaft & (along < 0.85), 0.2, 0.0)
    lv = lv - np.where(along > 0.78, 0.16, 0.0)
    c = px.quant(ctx, QUILL, lv)
    return c, alpha.astype(float), ctx.zeros()


def mat_bristle(ctx):
    """Stiff keratin bristles (cutout): strands every other texel, uneven lengths, pale tips."""
    ix, iy, W, H = px.texel(ctx)
    up = 1 - ctx.local[:, 1]                                  # 0 at the top
    h = (np.sin(ix * 2.3 + ctx.seed) * 0.5 + 0.5) * 0.35
    strand = (ix % 2 == 0) & (up >= h)
    c = px.quant(ctx, QUILL, 0.3 + 0.45 * (up < h + 0.22))
    return c, strand.astype(float), ctx.zeros()


def mat_osteo(ctx):
    """Bony osteoderm: ivory plate, a darker rim and a pale keel."""
    ix, iy, W, H = px.texel(ctx)
    c = px.quant(ctx, BONE, px.light(ctx, grad=0.1) + 0.05)
    c = np.where(px.border(ctx, 1)[:, None], BONE[1], c)
    if W >= 2:
        keel = ix == W // 2
        c = np.where((keel & ~px.border(ctx, 1, ("t", "b")))[:, None], BONE[4], c)
    return c, ctx.ones(), ctx.zeros()


def _scales(ctx, lv):
    """Coarse scales: rows of rounded 2x2 scales offset like brickwork, dark grout."""
    ix, iy, W, H = px.texel(ctx)
    row = iy // 2
    cx = (ix + row) % 3
    grout = (cx == 2) | (iy % 2 == 1) & (cx == 1)
    return lv - np.where(grout, 0.14, 0.0) + np.where((iy % 2 == 0) & (cx == 0), 0.06, 0.0)


def mat_scale(ctx):
    lv = _scales(ctx, px.rim(ctx, px.light(ctx, grad=0.1), 0.08, 0.1))
    return px.quant(ctx, SCALE, lv), ctx.ones(), ctx.zeros()


def mat_shin(ctx):
    """Shank: plumage on the upper half, coarse scales below."""
    p = ctx.wp if ctx.wp is not None else ctx.p
    lv = px.rim(ctx, px.light(ctx, grad=0.1), 0.08, 0.1)
    sc = px.quant(ctx, SCALE, _scales(ctx, lv))
    fe = _plumage(ctx, PLUME, lv, w=4, h=2, every=2)
    return np.where((p[:, 1] > 5.75)[:, None], fe, sc), ctx.ones(), ctx.zeros()


def mat_fore(ctx):
    lv = px.rim(ctx, px.light(ctx, grad=0.1), 0.08, 0.1)
    return px.quant(ctx, SCALE, _scales(ctx, lv)), ctx.ones(), ctx.zeros()


def mat_finger(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = px.quant(ctx, SCALE, px.light(ctx))
    if px.side(ctx):
        c = np.where((iy >= H - 1)[:, None], CLAW[1], c)
    return c, ctx.ones(), ctx.zeros()


def mat_claw(ctx):
    return px.shade(ctx, CLAW, offset=0.05, up=0.2), ctx.ones(), ctx.zeros()


def mat_rod(ctx):
    """The bony support rods of the membranes: ivory with dark joints."""
    ix, iy, W, H = px.texel(ctx)
    c = px.quant(ctx, BONE, px.light(ctx, grad=0.05) - 0.05)
    if px.side(ctx) and H > 4:
        c = np.where(((iy % 5) == 4)[:, None], BONE[0], c)
    return c, ctx.ones(), ctx.zeros()


def mat_memb(ctx):
    """Thin membrane (cutout): dusky crimson, lighter where it is thin, darker veins running
    out from the rod, a scalloped free edge."""
    ix, iy, W, H = px.texel(ctx)
    u = ctx.local[:, 2]
    v = ctx.local[:, 1]
    vein = (np.abs(((v * H + u * 3) % 4) - 0) < 0.6) & (u > 0.15)
    lv = 0.55 + 0.25 * u - np.where(vein, 0.22, 0.0)
    c = px.quant(ctx, MEMB, lv)
    scallop = (u > 0.9) & ((iy % 4) < 2)
    alpha = (~scallop).astype(float)
    return c, alpha, ctx.zeros()
