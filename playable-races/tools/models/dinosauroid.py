"""Race 007 - The Unknown Dinosauroid.  (Expansion 02)

An intelligent, calm, quietly unsettling biped that should not exist: a taxonomic
impossibility assembled from prehistoric lineages that never met, grown into one organism.

Silhouette: a theropod - torso pitched forward from the hips, an S-neck carrying a big
skull well ahead of the chest, digitigrade running legs, a long counterweight tail with a
distal fan.  Every region is its own material with its own small lit palette:
  soft downy plumage (warm grey-umber)        long flight feathers (iridescent black-teal,
  stiff bristles (pale bone)                    pale tips - Microraptor)
  coarse scales (olive-grey, shins and feet)  osteoderms (bone with dark rims, along the back)
  bare leathery skin (dusky rose: face, throat) membranes (wine-red with veins, bony rods)
  colour-changing display skin (teal / amber / violet: crest, pouch, forearm fans, tail fan)

  * skull  - an enlarged braincase, an oviraptorosaur beak with a row of small teeth behind
             it and an irregular second row, ASYMMETRICAL supraorbital horns (the right long
             and curving forward, the left a blunt stump), a hollow tubular hadrosaur crest
             sweeping back well past the head, plume tufts, an inflatable gular sac, big
             amber eyes with slit pupils and a nictitating membrane
  * arms   - two clawed fingers and an elongated styliform digit (a pale bony spike behind
             the elbow) carrying a wine membrane; flight-feather panels with display eyes from
             upper arm to wrist; the hand ends where the player's hand is, so it holds items
  * legs   - digitigrade (thigh, shank, metatarsus, toes) with a raised sickle talon on digit
             II; long Microraptor feathers on the shank and a metatarsal fan; membranes from
             hip to ankle on jointed bony rods - folded at rest, wide wings in the veer
  * tail   - five segments, pale Psittacosaurus bristles, embedded bony plates, feather vanes
             and a distal fan that opens

Rig note: the head sits far ahead of the player's head pivot, so the add-on cancels the
player's look on head_g (pitch) and hfix (yaw) and re-applies it on its own neck bone,
pivoting at the real base of the neck (see anims/dinosauroid.py).

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
    "overflow": {"night": 0.6, "overflow": 1.0},
}
VARIANT_TEXTURE = {"base": "base", "night": "night", "display": "base", "veer": "base", "overflow": "overflow"}
OPEN = {"display", "overflow"}        # crest raised, pouch inflated, arm fans spread, quills and bristles up
WINGS = {"veer", "overflow"}          # hindlimb membranes and leg feathers deployed
FANNED = {"display", "veer", "overflow"}
SIDES = ((-1, "r"), (1, "l"))
TAIL = 5

# ----------------------------------------------------------------------------- palettes (dark -> light)
DOWNY = px.pal("#211a16", "#372b24", "#514035", "#6d5948", "#8b745e", "#aa9278", "#c8b296")   # soft plumage
FLIGHT = px.pal("#06090b", "#0c161a", "#122429", "#19363a", "#21504f", "#2d6a63")     # iridescent black-teal
SHEEN = px.pal("#0a0810", "#161126", "#22193a", "#30234e", "#423063")                  # its violet sheen
TIP = px.col("#e6dec8")                                                                # pale feather tips
BRISTLE = px.pal("#6d624e", "#988c72", "#c1b595", "#e0d6b9", "#f5efdb")                # stiff bristles
SCALE = px.pal("#252618", "#3a3c28", "#52553a", "#6c704f", "#8a8e69")                  # coarse scales
BONE = px.pal("#463c30", "#776b55", "#a6997b", "#ccc0a0", "#e9e1c6")                   # osteoderms, rods, crest
ROSE = px.pal("#382226", "#543238", "#71474b", "#905d5d", "#ad7873", "#c8988f")        # bare leathery skin
WINE = px.pal("#22070f", "#3e0d1c", "#5e152b", "#82213d", "#a43752", "#c4566b")        # membranes
KERATIN = px.pal("#161518", "#2b292d", "#474247", "#736c69", "#a59b90", "#d4cab8")     # beak, horns, claws
TEAL = px.pal("#082a33", "#0f4954", "#176d74", "#25948f", "#4cbcab", "#8fe0c8")
AMBER = px.pal("#4a2604", "#7d4508", "#b36b0f", "#e0981e", "#ffc548", "#ffe79a")
VIOLET = px.pal("#1d0f33", "#331a57", "#4e2a7d", "#6c3ea0", "#8f59c2", "#b585e0")
LTEAL = px.pal("#1a6b72", "#2aa5a8", "#4fdcd2", "#a2fff0")                            # luminous (night)
LAMBER = px.pal("#b5720f", "#f0a92a", "#ffd76a", "#fff3c2")
LVIOLET = px.pal("#6a3cb0", "#9a62e6", "#c99bff", "#efdcff")
IRIS = ("#4a2706", "#9a5810", "#d99222", "#ffd24d")

# ----------------------------------------------------------------------------- anatomy (JSON model units, rest pose)
TRUNK_PIVOT = (0.0, 12.5, 2.0)        # the hips: the trunk pitches forward about them
PITCH = 30.0                          # theropod posture
VEER_LEAN = 22.0                      # extra lean of the Hindwing Veer
NECK_BASE = (0.0, 20.75, -4.25)       # where the neck leaves the chest: the neck bone's pivot
SKULL_PIVOT = (0.0, 25.25, -5.0)      # top of the neck
DOME_C = (0.0, 27.75, -4.25)          # the enlarged braincase
EYE = (2.15, 27.5, -7.15)             # eye centre (x mirrored per side)
EYE_RY = 28.0                         # eyes turned forward (binocular)
GULAR_PIVOT = (0.0, 25.4, -7.25)
CREST = [(0.0, 30.0, -6.5), (0.0, 31.75, -3.5), (0.0, 32.75, 3.0)]    # brow -> over the dome -> far behind
HIP = (2.3, 12.5, 2.0)
KNEE = (2.6, 8.0, -0.5)
ANKLE = (2.6, 4.25, 3.0)
BALL = (2.6, 0.75, 0.75)
SHOULDER = (3.75, 19.75, -2.75)
ELBOW = (5.3, 16.0, 0.25)
WRIST = (5.9, 12.5, -2.0)
TAIL_PTS = [(0.0, 13.25, 4.0), (0.0, 13.0, 7.5), (0.0, 13.0, 10.75), (0.0, 13.5, 13.75), (0.0, 14.25, 16.5),
            (0.0, 15.0, 18.75)]
TAIL_W = [3.75, 3.0, 2.5, 1.75, 1.25]
TAIL_H = [3.5, 2.75, 2.25, 1.5, 1.0]


def _v(p):
    return np.asarray(p, float)


def _rot(ang, axis):
    """A single-axis cube rotation (None when negligible)."""
    if abs(ang) < 0.05:
        return None
    r = [0.0, 0.0, 0.0]
    r["xyz".index(axis)] = round(ang, 2)
    return tuple(r)


def trunk_to_world(p):
    """Where a point given in the upright trunk frame sits once the trunk pitches forward."""
    piv = _v(TRUNK_PIVOT)
    return tuple(piv + rot_matrix((PITCH, 0, 0)) @ (_v(p) - piv))


def lean_offset(p, deg, pivot=TRUNK_PIVOT):
    """Displacement of world point p when the trunk leans `deg` further forward about the hips."""
    piv = _v(pivot)
    v = _v(p) - piv
    return tuple(np.round(rot_matrix((deg, 0, 0)) @ v - v, 3))


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
    """A cutout feather plane growing from `root` toward +Z, tilted by rx (a vertical plane
    hanging `width` below the root line; +rx lifts the tip) or ry (a horizontal plane `width`
    wide centred on the root; +ry swings the tip toward +X)."""
    x, y, z = root
    if flat:
        o, s, faces, r = (x - width / 2, y, z), (width, 0.0, length), {"up", "down"}, _rot(ry, "y")
    else:
        o, s, faces, r = (x, y - width, z), (0.0, width, length), {"east", "west"}, _rot(rx, "x")
    return m.cube(bone, o, s, mat, pivot=tuple(root) if r else None, rot=r, cutout=True, faces=faces, **kw)


# six nested boxes per rounded mass, all extents distinct per axis (no coplanar faces -> no z-fighting)
BALL6 = ((1.0, 0.6, 0.6), (0.6, 1.0, 0.5), (0.5, 0.55, 1.0), (0.85, 0.82, 0.76), (0.76, 0.91, 0.84), (0.92, 0.73, 0.92))


def ball6(m, bone, center, dims, mat, **kw):
    """A rounder voxel mass than common.ellipsoid: six nested boxes."""
    sizes = set()
    out = []
    for fx, fy, fz in BALL6:
        sz = (q(dims[0] * fx), q(dims[1] * fy), q(dims[2] * fz))
        if sz in sizes:
            continue
        sizes.add(sz)
        out.append(m.box(bone, center, sz, mat, **kw))
    return out


def panel(m, bone, pivot, x, length, width, mat, rx, **kw):
    """A cutout plane in the YZ plane hanging `length` down from `pivot` and `width` back
    (+Z) from it, then tilted by rx about the pivot (+rx swings its lower edge back)."""
    _, py, pz = pivot
    return m.cube(bone, (x, py - length, pz), (0.0, length, width), mat, pivot=tuple(pivot), rot=_rot(rx, "x"),
                  cutout=True, faces={"east", "west"}, **kw)


# ============================================================================= build

def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=256)
    humanoid(m)
    # the player's look is cancelled here (pitch on head_g, yaw on hfix, both about the player's
    # head pivot) and re-applied on the neck, which pivots where the neck really leaves the chest
    m.bone("hfix", "head_g", (0, 24, 0))
    nk = m.bone("neck", "hfix", NECK_BASE)
    nk.variant["veer"] = (lean_offset(NECK_BASE, VEER_LEAN), None)
    for g, piv in (("r_arm_g", (-5, 22, 0)), ("l_arm_g", (5, 22, 0))):
        m.bones[g].variant["veer"] = (lean_offset(trunk_to_world((0, 21.0, 1.25)), VEER_LEAN), None)
    _trunk(m)
    _head(m)
    _arms(m)
    _legs(m)
    _tail(m)
    fp_sleeves(m, "sleeve", width=4.4)
    accents(m, [
        ("c", "breast", "trunk", (0, 19.5, -1.85), (3.5, 3.5, 0.5)),
        ("c", "rsh", "r_upper", (-3.9, 20.1, -2.75), (2.5, 0.5, 2.5)),
        ("c", "lsh", "l_upper", (3.9, 20.1, -2.75), (2.5, 0.5, 2.5)),
        ("l", "r", "r_thigh", (-4.05, 10.5, 1.0), (0.5, 2.5, 2.5)),
        ("l", "l", "l_thigh", (4.05, 10.5, 1.0), (0.5, 2.5, 2.5)),
        ("f", "r", "r_meta", (-2.6, 2.25, 1.75), (1.75, 1.0, 1.75)),
        ("f", "l", "l_meta", (2.6, 2.25, 1.75), (1.75, 1.0, 1.75)),
    ])
    m.pack()
    return m


# ----------------------------------------------------------------------------- trunk (authored upright, pitched forward)

def _trunk(m: Model) -> None:
    t = m.bone("trunk", "torso_g", TRUNK_PIVOT, (PITCH, 0, 0))
    t.variant["veer"] = ((0, 0, 0), (PITCH + VEER_LEAN, 0, 0))
    m.box(t.name, (0, 13.75, 2.5), (4.25, 3.5, 4.5), "downy")                         # narrow pelvis
    m.box(t.name, (0, 16.5, 2.0), (3.75, 3.0, 4.75), "downy")                         # narrow waist
    ball6(m, t.name, (0, 19.5, 1.5), (6.0, 5.5, 6.5), "downy")                        # deep keeled chest
    m.box(t.name, (0, 22.75, 0.25), (3.25, 3.25, 3.25), "downy")                      # lower neck
    # ankylosaur osteoderms: two rows of small bony plates down the back
    for s in (-1, 1):
        for y, z in ((21.25, 4.0), (19.0, 4.65), (16.75, 4.35), (14.5, 4.75)):
            m.box(t.name, (s * 1.25, y, z), (1.0, 1.5, 0.5), "osteo")
    # stiff dorsal bristles along the spine: they lie back at rest and rise in the display
    for k, (y, z, h, ln) in enumerate(((22.0, 3.5, 3.5, 3.0), (18.25, 4.65, 3.0, 3.0))):
        b = m.bone(f"quill{k}", t.name, (0, y, z), (-74.0, 0, 0))
        b.variant.update({v: ((0, 0, 0), (-16.0 + 8 * k, 0, 0)) for v in OPEN})
        m.cube(b.name, (0, y, z - ln / 2), (0.0, h, ln), "bristle", cutout=True, faces={"east", "west"})
    t.locators["chest"] = (0, 19.5, -2.0)


# ----------------------------------------------------------------------------- head

def _head(m: Model) -> None:
    nk = "neck"
    yseg(m, nk, (0, 23.25, -4.6), (0, 19.75, -4.0), 3.25, 3.5, "throat")               # the S-neck: thick base ...
    yseg(m, nk, (0, 26.0, -5.6), (0, 22.5, -4.5), 2.75, 3.0, "throat")                 # ... curving into the skull
    na = m.bone("nape", nk, (0, 25.25, -3.9), (-62.0, 0, 0))                          # pale bristles down the nape
    na.variant.update({v: ((0, 0, 0), (-14.0, 0, 0)) for v in OPEN})
    m.cube(na.name, (0, 25.25, -5.25), (0.0, 2.5, 3.0), "bristle", cutout=True, faces={"east", "west"})
    sk = m.bone("skull", nk, SKULL_PIVOT)
    sk.variant.update({"display": ((0, 0, 0), (-12.0, 0, 0)), "overflow": ((0, 0, 0), (-6.0, 0, 11.0))})
    ball6(m, sk.name, DOME_C, (6.0, 5.5, 6.0), "dome")                                 # the enlarged braincase
    m.box(sk.name, (0, 27.1, -7.6), (4.25, 3.0, 2.75), "face")                         # orbits and cheeks, bare skin
    m.box(sk.name, (0, 29.0, -7.25), (5.0, 0.75, 1.5), "brow")                         # heavy brow ridge
    # oviraptorosaur beak: deep, parrot-like, hooked
    m.box(sk.name, (0, 27.25, -9.5), (3.0, 2.5, 1.5), "beak")
    m.box(sk.name, (0, 26.875, -10.875), (2.5, 2.25, 1.25), "beak")
    m.box(sk.name, (0, 26.25, -12.0), (1.75, 2.0, 1.0), "beak")                       # the hooked tip
    m.box(sk.name, (0, 25.95, -9.25), (2.25, 0.5, 3.0), "mouth")                      # gape (dark)
    # ASYMMETRICAL ceratopsian horns: the right long and curving forward, the left a blunt stump
    seg2(m, sk.name, (-1.75, 31.75, -8.25), (-1.5, 28.75, -7.0), 1.0, 1.0, "horn")
    seg2(m, sk.name, (-1.8, 32.75, -10.0), (-1.75, 31.25, -7.75), 0.75, 0.75, "horn")
    seg2(m, sk.name, (2.35, 30.25, -7.25), (1.5, 28.75, -7.0), 1.0, 1.0, "horn")
    # teeth: a row behind the beak and an irregular second row (bared as the jaw drops)
    th = m.bone("teeth", sk.name, (0, 25.9, -8.5))
    for s in (-1, 1):
        for z in (-9.6, -8.95, -8.3, -7.65):
            m.box(th.name, (s * 1.25, 25.5, z), (0.5, 0.5, 0.5), "tooth")
        for z, h, dx in ((-10.2, 0.75, 0.5), (-8.6, 0.5, 0.65)):
            m.box(th.name, (s * dx, 25.85 - h / 2, z), (0.5, h, 0.5), "tooth")
    # lower jaw
    jw = m.bone("jaw", sk.name, (0, 25.9, -6.5))
    jw.variant.update({"display": ((0, 0, 0), (9.0, 0, 0)), "overflow": ((0, 0, 0), (13.0, 0, 0))})
    m.box(jw.name, (0, 25.3, -8.75), (2.75, 1.0, 4.0), "jaw")
    m.box(jw.name, (0, 25.3, -11.0), (1.75, 0.75, 1.0), "beak")
    # eyes: big amber eyes turned forward; slit pupils that contract; a nictitating membrane
    for s, p in SIDES:
        ex, ey, ez = s * EYE[0], EYE[1], EYE[2]
        eb = m.bone(f"{p}_eye", sk.name, (ex, ey, ez), side_rot((0, -EYE_RY, 0), s))
        m.box(eb.name, (ex, ey, ez), (0.5, 2.0, 2.0), "eye", ppu=4.0)
        pu = m.bone(f"{p}_pupil", eb.name, (ex, ey, ez))
        m.box(pu.name, (ex + s * 0.3, ey, ez), (0.1, 1.5, 0.5), "pupil", ppu=4.0)
        nm = m.bone(f"{p}_nict", eb.name, (ex + s * 0.33, ey, ez - 1.0))
        m.cube(nm.name, (ex + s * 0.33 - 0.025, ey - 1.0, ez - 1.0), (0.05, 2.0, 0.1), "nict")
    sk.locators["eyes"] = (0, EYE[1], EYE[2] - 1.5)
    # throat pouch (gular sac) of display skin: tucked under the jaw at rest, a balloon in the display
    gu = m.bone("gular", sk.name, GULAR_PIVOT)
    ellipsoid(m, gu.name, (0, 24.75, -7.75), (2.5, 2.0, 3.25), "gular", a=0.65, b=0.85, skip=OPEN)
    ellipsoid(m, gu.name, (0, 22.75, -8.0), (5.0, 5.0, 5.5), "gular", a=0.6, b=0.86, only=OPEN)
    gu.locators["throat"] = (0, 23.75, -8.0)
    # the hollow tubular crest: rises from the brow, runs over the dome and sweeps far behind
    c0 = m.bone("crest0", sk.name, CREST[0])
    c0.variant.update({"display": ((0, 0, 0), (17.0, 0, 0)), "overflow": ((0, 0, 0), (13.0, 0, 0))})
    zseg(m, c0.name, CREST[0], CREST[1], 1.75, 1.75, "crest", pad=0.75)
    c1 = m.bone("crest1", c0.name, CREST[1])
    c1.variant.update({"display": ((0, 0, 0), (6.0, 0, 0)), "overflow": ((0, 0, 0), (10.0, 0, 0))})
    zseg(m, c1.name, CREST[1], CREST[2], 1.5, 1.75, "crest", pad=0.25)
    cx_, cy_, cz_ = CREST[2]
    zseg(m, c1.name, (cx_, cy_ - 0.05, cz_ - 0.5), (cx_, cy_ + 0.05, cz_ + 0.5), 2.25, 2.25, "crestend")   # flared hollow end
    m.cube(c1.name, (0, 27.25, -3.0), (0.0, 4.75, 6.0), "frill", cutout=True, faces={"east", "west"}, only=OPEN)
    c1.locators["crest_tip"] = (0, CREST[2][1] + 0.1, CREST[2][2] + 0.3)
    # plume tufts behind the eyes
    for s, p in SIDES:
        tf = m.bone(f"{p}_tuft", sk.name, (s * 2.3, 29.0, -3.5), side_rot((0, -12, 0), s))
        tf.variant.update({v: ((0, 0, 0), side_rot((-34, -36, 0), s)) for v in OPEN})
        vane(m, tf.name, (s * 2.3, 29.75, -3.5), 5.0, 1.25, "tuft", rx=-10)
        vane(m, tf.name, (s * 2.35, 28.75, -3.5), 3.75, 1.0, "tuft", rx=-30)


# ----------------------------------------------------------------------------- arms: two clawed fingers + a styliform digit

def _arms(m: Model) -> None:
    for s, p in SIDES:
        g = f"{p}_arm_g"
        sh, el, wr = (_v((s * c[0], c[1], c[2])) for c in (SHOULDER, ELBOW, WRIST))
        up = m.bone(f"{p}_upper", g, tuple(sh))
        seg2(m, up.name, sh + (0, 0.5, 0), el, 2.0, 2.25, "downy")
        fo = m.bone(f"{p}_fore", up.name, tuple(el))
        seg2(m, fo.name, el + (0, 0.5, 0.25), wr, 1.5, 1.75, "fore")
        ha = m.bone(f"{p}_hand", fo.name, tuple(wr))
        m.box(ha.name, (wr[0], 11.75, -2.1), (1.5, 1.75, 1.5), "scale")
        yseg(m, ha.name, (wr[0] - s * 0.4, 11.25, -2.6), (wr[0] - s * 0.4, 9.5, -3.1), 0.5, 0.5, "finger")
        yseg(m, ha.name, (wr[0] + s * 0.35, 11.25, -2.35), (wr[0] + s * 0.35, 9.25, -2.85), 0.5, 0.5, "finger")
        # flight-feather panels: a folded wing at rest, two wide fans in the display
        p0 = m.bone(f"{p}_plume0", up.name, (s * 4.6, 18.75, -1.0), side_rot((0, -10, 0), s))
        p0.variant.update({v: ((0, 0, 0), side_rot((-10, -70, 0), s)) for v in OPEN})
        for k, (ln, rx) in enumerate(((4.25, -24.0), (3.75, -44.0))):
            vane(m, p0.name, (s * (4.6 + 0.02 * k), 19.25 - 0.75 * k, -1.0), ln, 1.5, "coverts", rx=rx)
        p1 = m.bone(f"{p}_plume1", fo.name, (s * 5.75, 15.0, -0.75), side_rot((0, -12, 0), s))
        p1.variant.update({v: ((0, 0, 0), side_rot((-14, -82, 0), s)) for v in OPEN})
        for k, (ln, rx) in enumerate(((6.5, -6.0), (6.25, -24.0), (5.75, -42.0), (5.0, -60.0))):
            vane(m, p1.name, (s * (5.75 + 0.02 * k), 16.0 - 0.9 * k, -0.25 - 0.45 * k), ln, 2.0, "armfan", rx=rx)
        # the styliform digit: a long pale bony spike from the wrist past the elbow, carrying a membrane
        st = m.bone(f"{p}_stylus", ha.name, (s * 6.3, 12.5, -1.25))
        st.variant.update({v: ((0, 0, 0), side_rot((-24, 0, -72), s)) for v in OPEN})
        yseg(m, st.name, (s * 6.3, 19.75, 4.6), (s * 6.3, 12.25, -1.25), 0.75, 0.75, "spike")
        m.cube(st.name, (s * 6.25, 12.5, -1.75), (0.0, 5.75, 5.25), "membtri", cutout=True, faces={"east", "west"})


# ----------------------------------------------------------------------------- legs: digitigrade runners with hindwings

def _legs(m: Model) -> None:
    for s, p in SIDES:
        g = f"{p}_leg_g"
        hip, knee, ankle, ball = (_v((s * c[0], c[1], c[2])) for c in (HIP, KNEE, ANKLE, BALL))
        th = m.bone(f"{p}_thigh", g, tuple(hip))
        yseg(m, th.name, hip + (s * 0.1, 0.75, 0.75), hip + (s * 0.15, -2.75, -0.25), 3.0, 3.75, "thigh")   # drumstick
        yseg(m, th.name, hip + (s * 0.15, -2.0, -0.25), knee + (0, 0, 0.25), 2.0, 2.5, "thigh")
        sh = m.bone(f"{p}_shin", th.name, tuple(knee))
        yseg(m, sh.name, knee + (0, 0.5, -0.1), ankle, 1.75, 2.0, "shin")
        mt = m.bone(f"{p}_meta", sh.name, tuple(ankle))
        yseg(m, mt.name, ankle + (0, 0.25, 0.1), ball, 1.25, 1.25, "scale")
        ft = m.bone(f"{p}_foot", mt.name, tuple(ball))
        bx, by, bz = ball
        m.box(ft.name, (bx, 0.375, bz - 1.5), (0.75, 0.75, 3.0), "toe")                    # digit III
        m.cube(ft.name, (bx - 0.375, 0.0, bz - 2.75), (0.75, 0.75, 2.5), "toe", pivot=(bx, 0.4, bz),
               rot=side_rot((0, 24, 0), s))                                                # digit IV
        m.box(ft.name, (bx - s * 0.45, 0.5, bz + 0.85), (0.5, 0.5, 1.0), "toe")            # hallux
        m.box(ft.name, (bx, 0.25, bz - 3.25), (0.5, 0.5, 0.5), "claw")
        # digit II: raised, carrying the enlarged sickle talon
        tx = bx - s * 0.75
        tl = m.bone(f"{p}_talon", ft.name, (tx, 0.75, bz - 0.5))
        zseg(m, tl.name, (tx, 0.75, bz - 0.25), (tx, 1.5, bz - 1.75), 0.6, 0.6, "toe")
        yseg(m, tl.name, (tx, 2.75, bz - 2.25), (tx, 1.25, bz - 1.75), 0.5, 0.75, "claw")
        zseg(m, tl.name, (tx, 2.6, bz - 2.4), (tx, 1.85, bz - 3.5), 0.5, 0.5, "claw")
        tl.locators[f"{p}_sickle"] = (tx, 2.0, bz - 3.4)
        # hindwing membranes on jointed bony rods: hip -> knee and knee -> ankle; a folded edge at rest
        x0 = s * 4.1
        s0 = m.bone(f"{p}_sail0", th.name, (x0, 12.75, 2.75))
        s0.variant.update({v: ((0, 0, 0), side_rot((0, -6, 74), s)) for v in WINGS})
        _sail(m, s0.name, (x0, 12.75, 2.75), 5.25, -29.0, 1.5, 8.5)
        x1 = s * 3.65
        s1 = m.bone(f"{p}_sail1", sh.name, (x1, 8.0, 0.75))
        s1.variant.update({v: ((0, 0, 0), side_rot((0, -10, 66), s)) for v in WINGS})
        _sail(m, s1.name, (x1, 8.0, 0.75), 4.75, 43.0, 1.5, 8.0, up=True)
        # Microraptor feathers: long "trousers" down the back of the shank ...
        sf = m.bone(f"{p}_sfan", sh.name, (s * 3.5, 7.5, 0.5))
        sf.variant.update({v: ((0, 0, 0), side_rot((0, -18, 70), s)) for v in WINGS})
        for k, (ln, rx) in enumerate(((5.5, -40.0), (5.0, -52.0), (4.25, -64.0))):
            vane(m, sf.name, (s * (3.5 + 0.03 * k), 7.75 - 0.5 * k, 0.5), ln, 1.5, "flight", rx=rx)
        vane(m, sf.name, (s * 3.6, 7.75, 0.5), 8.5, 2.0, "flight", rx=-28, only=WINGS)
        vane(m, sf.name, (s * 3.62, 7.25, 0.5), 8.0, 2.0, "flight", rx=-46, only=WINGS)
        # ... and the metatarsal fan behind the ankle (two bones: it spreads wide in the veer)
        for j, (rz, ry) in enumerate(((72, -26), (82, -8))):
            lf = m.bone(f"{p}_lfan{j}", mt.name, (s * 2.7, 4.25, 3.25))
            lf.variant.update({v: ((0, 0, 0), side_rot((0, ry, rz), s)) for v in WINGS})
            for k, (ln, rx) in enumerate(((6.0, -6.0), (5.5, -18.0)) if j == 0 else ((5.0, -30.0), (4.5, -42.0))):
                vane(m, lf.name, (s * (2.7 + 0.03 * (2 * j + k)), 4.75, 3.25), ln, 1.5, "flight", rx=rx)
            vane(m, lf.name, (s * 2.75, 4.75, 3.25), 9.0 - j, 2.0, "flight", rx=-12.0 - 20 * j, only=WINGS)


def _sail(m, bone, pivot, length, rx, folded, wide, up=False):
    """A membrane panel with a bony rod along its free edge.  Folded: a narrow strip; in the
    WINGS variants a wide sail.  `up`: the panel extends to the other side of the rod line."""
    x, py, pz = pivot
    for w, cond in ((folded, {"skip": WINGS}), (wide, {"only": WINGS})):
        mat = "membsail"
        if not up:
            panel(m, bone, pivot, x, length, w, mat, rx, **cond)
            rod_z = pz + w
        else:
            m.cube(bone, (x, py - length, pz - w), (0.0, length, w), mat, pivot=tuple(pivot), rot=_rot(rx, "x"),
                   cutout=True, faces={"east", "west"}, **cond)
            rod_z = pz - w
        m.cube(bone, (x - 0.25, py - length, rod_z - 0.25), (0.5, length, 0.5), "rod", pivot=tuple(pivot),
               rot=_rot(rx, "x"), **cond)


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
    for k, a in enumerate((0.0, 8.0, 14.0, 16.0, 14.0)):          # display: the tail lifts its fan high
        if a:
            m.bones[names[k]].variant["display"] = ((0, 0, 0), (a, 0, 0))
            m.bones[names[k]].variant["overflow"] = ((0, 0, 0), (a * 0.6, 0, 0))
    # pale Psittacosaurus bristles on the tail base
    for k, (y, z, h, ln) in enumerate(((15.0, 4.5, 3.5, 3.5), (14.4, 7.75, 3.0, 3.25))):
        bb = m.bone(f"bristle{k}", names[k], (0, y, z), (-46.0, 0, 0))
        bb.variant.update({v: ((0, 0, 0), (-6.0, 0, 0)) for v in OPEN})
        m.cube(bb.name, (0, y, z - 0.25), (0.0, h, ln), "bristle", cutout=True, faces={"east", "west"})
    # small bony plates embedded along the tail
    for seg, x, y, z in ((1, 1.3, 14.4, 9.0), (2, 1.05, 14.1, 11.75), (2, 0.95, 14.15, 13.0)):
        for s in (-1, 1):
            m.box(names[seg], (s * x, y, z), (0.75, 0.5, 1.0), "osteo")
    # flight-feather vanes along the sides of the distal tail
    for seg, w in ((2, 2.0), (3, 2.25)):
        a = TAIL_PTS[seg]
        for s in (-1, 1):
            hw = TAIL_W[seg] / 2
            m.cube(names[seg], (s * (hw + w / 2) - w / 2, a[1], a[2] + 0.25), (w, 0.0, 3.25), "flight",
                   cutout=True, faces={"up", "down"})
    # the distal fan: closed at rest, a raised display fan, a vertical rudder in the veer
    tip = TAIL_PTS[-1]
    fc = m.bone("fan", names[-1], tip)
    fc.variant.update({"display": ((0, 0, 0), (55.0, 0, 0)), "veer": ((0, 0, 0), (0, 0, 86.0)),
                       "overflow": ((0, 0, 0), (36.0, 0, 28.0))})
    vane(m, fc.name, tip, 7.0, 2.0, "fanq", flat=True)
    for s in (-1, 1):
        vane(m, fc.name, tip, 6.75, 2.0, "fanq", flat=True, ry=s * 18.0)
    fc.locators["tail_fan"] = (tip[0], tip[1], tip[2] + 4.0)
    for s, p in SIDES:
        fb = m.bone(f"{p}_fan", fc.name, tip, (0, -s * 10.0, 0))
        fb.variant.update({v: ((0, 0, 0), (0, s * 42.0, 0)) for v in FANNED})
        vane(m, fb.name, tip, 6.5, 2.0, "fanq", flat=True)
        vane(m, fb.name, tip, 6.0, 2.0, "fanq", flat=True, ry=s * 18.0)


# ============================================================================= materials

def materials():
    return {
        "downy": mat_downy, "throat": mat_throat, "dome": mat_dome, "face": mat_face, "brow": mat_brow,
        "beak": mat_beak, "mouth": mat_mouth, "jaw": mat_jaw, "tooth": mat_tooth, "horn": mat_horn,
        "eye": mat_eye, "pupil": mat_pupil, "nict": mat_nict, "gular": mat_gular, "crest": mat_crest,
        "frill": mat_frill, "tuft": mat_tuft, "flight": mat_flight, "armfan": mat_armfan, "fanq": mat_fanq,
        "coverts": mat_coverts, "crestend": mat_crestend,
        "bristle": mat_bristle, "osteo": mat_osteo, "fore": mat_fore, "scale": mat_scale, "finger": mat_finger,
        "rod": mat_rod, "spike": mat_spike, "membsail": mat_sail, "membtri": mat_membtri, "thigh": mat_thigh, "shin": mat_shin,
        "toe": mat_scale, "claw": mat_claw, "tail": mat_tail, "sleeve": mat_sleeve, "accent": mat_accent,
    }


def _night(ctx):
    return ctx.params.get("night", 0.0)


def _over(ctx):
    return ctx.params.get("overflow", 0.0)


def _wn(ctx):
    return ctx.wn if ctx.wn is not None else ctx.n


def qidx(ctx, K, level, dither=0.0):
    """Palette index per texel (light level 0..1 -> 0..K-1, ordered dither), so a pattern can
    shift texels by exact palette steps."""
    ix, iy, _, _ = px.texel(ctx)
    d = (px.BAYER4[iy % 4, ix % 4] - 0.5) * dither
    return np.clip(np.round(np.clip(level, 0, 1) * (K - 1) + d), 0, K - 1).astype(int)


def chevrons(ctx, w=6, h=4):
    """Small down-pointing V marks on a staggered grid: overlapping feather tips."""
    ix, iy, W, H = px.texel(ctx)
    row = iy // h
    cx = (ix + (row % 2) * (w // 2) + ctx.seed % w) % w
    cy = iy % h
    return ((cx == 1) & (cy == h - 2)) | ((cx == 2) & (cy == h - 1)) | ((cx == 3) & (cy == h - 2))


def _downy(ctx, lv, w=8, h=4, dither=0.2):
    K = len(DOWNY)
    i = qidx(ctx, K, lv, dither)
    i = np.where(chevrons(ctx, w, h), np.maximum(i - 1, 0), i)
    return DOWNY[i]


def _bars(ctx, coord, period=3.0, width=1.0):
    """Bold dark transverse bars (a model-space coordinate along the body axis, units)."""
    return np.mod(coord, period) < width


def mat_downy(ctx):
    """Soft downy plumage: warm grey-umber, countershaded (barred dark back, pale buff breast)."""
    n = _wn(ctx)
    lv = px.rim(ctx, px.light(ctx, grad=0.14), 0.06, 0.08)
    belly = n[1] < -0.4 or n[2] < -0.55
    lv = lv + (0.32 if belly else -0.1)
    c = _downy(ctx, lv)
    if not belly and ctx.face in ("south", "up", "east", "west"):
        back = ctx.p[:, 2] > 1.0 if ctx.face in ("east", "west") else np.ones(ctx.N, bool)
        bar = _bars(ctx, ctx.p[:, 1] + 0.3, 2.75, 1.0) & back
        i = np.clip(qidx(ctx, len(DOWNY), lv, 0.2) - 2, 0, None)
        c = np.where(bar[:, None], DOWNY[i], c)
    return c, ctx.ones(), ctx.zeros()


def mat_thigh(ctx):
    lv = px.rim(ctx, px.light(ctx, grad=0.18) - 0.06, 0.06, 0.12)
    return _downy(ctx, lv, 4, 3), ctx.ones(), ctx.zeros()


def mat_tail(ctx):
    """Tail plumage: barred above (the bars continue the back's), pale buff beneath."""
    n = _wn(ctx)
    lv = px.rim(ctx, px.light(ctx, grad=0.1), 0.06, 0.1)
    below = n[1] < -0.5
    lv = lv + (0.3 if below else -0.1)
    c = _downy(ctx, lv, 6, 3)
    if not below:
        bar = _bars(ctx, ctx.p[:, 2] - 4.5, 2.75, 1.0)
        i = np.clip(qidx(ctx, len(DOWNY), lv, 0.2) - 2, 0, None)
        c = np.where(bar[:, None], DOWNY[i], c)
    return c, ctx.ones(), ctx.zeros()


def mat_throat(ctx):
    """The upper neck: downy behind, bare dusky-rose skin down the throat."""
    n = _wn(ctx)
    lv = px.rim(ctx, px.light(ctx, grad=0.12), 0.05, 0.08)
    if n[2] < -0.5:
        ix, iy, W, H = px.texel(ctx)
        wr = (iy % 3 == 1) & ((ix + iy) % 4 != 0)                          # wrinkled, leathery
        return px.quant(ctx, ROSE, lv + 0.05 - 0.08 * wr, dither=0.25), ctx.ones(), ctx.zeros()
    return _downy(ctx, lv - 0.08, 4, 3), ctx.ones(), ctx.zeros()


def mat_dome(ctx):
    """The enlarged braincase: close velvety down, lit as one round form, a paler brow."""
    lv = px.proxy(ctx, DOME_C, (3.0, 2.75, 3.0), 0.9) - 0.02
    return px.quant(ctx, DOWNY, lv, dither=0.3), ctx.ones(), ctx.zeros()


def mat_face(ctx):
    """Bare leathery skin around the eyes: dusky rose, finely wrinkled."""
    ix, iy, W, H = px.texel(ctx)
    lv = px.proxy(ctx, (0, 27.2, -7.0), (2.2, 1.7, 2.0), 0.7) + 0.08
    wr = (iy % 3 == 2) & ((ix + 2 * iy) % 5 != 0)
    return px.quant(ctx, ROSE, lv - 0.06 * wr, dither=0.25), ctx.ones(), ctx.zeros()


def mat_brow(ctx):
    return px.shade(ctx, DOWNY, offset=-0.04, up=0.16, down=0.24), ctx.ones(), ctx.zeros()


def _fwd(ctx, z0, span):
    p = ctx.wp if ctx.wp is not None else ctx.p
    return np.clip((-p[:, 2] - z0) / span, 0, 1)


def mat_beak(ctx):
    """Keratin: slate at the base, pale horn at the hooked tip, a pale ridge along the top."""
    lv = px.rim(ctx, px.light(ctx, grad=0.12), 0.1, 0.12) + _fwd(ctx, 9.6, 2.6) * 0.5 - 0.22
    c = px.quant(ctx, KERATIN, lv, dither=0.3)
    if ctx.face in ("up", "north"):
        ix, iy, W, H = px.texel(ctx)
        ridge = np.abs(ix - (W - 1) / 2.0) < 0.6
        c = np.where(ridge[:, None], px.quant(ctx, KERATIN, lv + 0.25), c)
    return c, ctx.ones(), ctx.zeros()


def mat_jaw(ctx):
    f = _fwd(ctx, 8.75, 2.5)
    c = px.quant(ctx, ROSE, px.light(ctx, grad=0.1) + 0.02)
    b = px.quant(ctx, KERATIN, px.light(ctx) + f * 0.38 - 0.06)
    return np.where((f > 0.2)[:, None], b, c), ctx.ones(), ctx.zeros()


def mat_mouth(ctx):
    return px.quant(ctx, px.pal("#1a0b0e", "#36141a", "#552027"), px.light(ctx)), ctx.ones(), ctx.zeros()


def mat_tooth(ctx):
    return px.quant(ctx, BONE, px.light(ctx) + 0.22), ctx.ones(), ctx.zeros()


def mat_horn(ctx):
    p = ctx.wp if ctx.wp is not None else ctx.p
    up = np.clip((p[:, 1] - 29.0) / 3.5, 0, 1)
    lv = px.light(ctx, grad=0.1) - 0.18 + up * 0.58
    return px.quant(ctx, KERATIN, lv, dither=0.3), ctx.ones(), ctx.zeros()


EYE_PIX = [".oooooo.",
           "oOOOOOOo",
           "oOYYYYOo",
           "oOYyyYOo",
           "oOYyyYOo",
           "oOYYYYOo",
           "oOOOOOOo",
           ".oooooo."]


def mat_eye(ctx):
    """Big amber eye (painted at 4 texels per unit); the slit pupil is its own piece."""
    night, over = _night(ctx), _over(ctx)
    n = _wn(ctx)
    outer = abs(n[0]) > 0.4 and np.sign(n[0]) == np.sign(ctx.p[0, 0])
    if not outer:
        return px.quant(ctx, ROSE, px.light(ctx) - 0.05), ctx.ones(), ctx.zeros()
    c = np.broadcast_to(px.col(ROSE[1]), (ctx.N, 3)).copy()
    cols = {"o": ROSE[0], "O": IRIS[1], "Y": IRIS[2], "y": IRIS[3]}
    if over > 0.5:
        cols = {"o": "#3a1a04", "O": "#ffb428", "Y": "#ffe070", "y": "#fffbd8"}
    gl = 0.0 if night < 0.5 and over < 0.5 else (0.5 if over < 0.5 else 0.95)
    c, g = px.decal(ctx, c, EYE_PIX, cols, 0, 0, glow=ctx.zeros(), glow_chars="OYy" if gl else "", glow_level=gl)
    ix, iy, W, H = px.texel(ctx)
    hi = (iy == 2) & (ix == (2 if ctx.face == "west" else W - 3))          # catch-light toward the front
    c = np.where(hi[:, None], px.col("#fffbea"), c)
    return c, ctx.ones(), g


def mat_pupil(ctx):
    c = np.broadcast_to(px.col("#0b0606"), (ctx.N, 3)).copy()
    ix, iy, W, H = px.texel(ctx)
    if px.side(ctx):
        c = np.where(((iy == 0) | (iy == H - 1))[:, None], px.col("#2a1306"), c)
    return c, ctx.ones(), ctx.zeros()


def mat_nict(ctx):
    return np.broadcast_to(px.col("#d6dcd6"), (ctx.N, 3)).copy(), ctx.ones(), ctx.zeros()


# ----------------------------------------------------------------------------- display skin (teal / amber / violet)

def _disp_pals(ctx):
    """(teal, amber, violet) palettes and a glow level for this texture set."""
    night, over = _night(ctx), _over(ctx)
    if over > 0.5:
        return LTEAL[:3], LAMBER[:3], LVIOLET[:3], 0.7
    if night > 0.5:
        return LTEAL[:3], LAMBER[:3], LVIOLET[:3], 0.55
    return TEAL, AMBER, VIOLET, 0.0


def _pk(pal, i):
    """Palette entry i, clamped to the palette's length (the luminous palettes are shorter)."""
    return pal[min(i, len(pal) - 1)]


def _display(ctx, lv, field):
    """Display skin: `field` 0..1 picks the colour zone - violet rim, teal body, amber heart -
    with pebbled scales.  Returns (rgb, glow)."""
    T, Am, V, gl = _disp_pals(ctx)
    ix, iy, W, H = px.texel(ctx)
    peb = ((ix + 2 * (iy // 2)) % 4 == 0) & (iy % 2 == 0)
    lvp = lv + np.where(peb, 0.12, 0.0)
    over = _over(ctx) > 0.5
    cv = px.quant(ctx, V, lvp + (0.15 if over else 0.0), dither=0.3)
    ct = px.quant(ctx, T, lvp, dither=0.3)
    ca = px.quant(ctx, Am, lvp + 0.12, dither=0.3)
    c = np.where((field < 0.33)[:, None], cv, np.where((field < 0.72)[:, None], ct, ca))
    g = np.where(field < 0.33, gl * 0.85, np.where(field < 0.72, gl, gl * 1.1)) if gl else ctx.zeros()
    return c, np.clip(g, 0, 1)


def mat_gular(ctx):
    """The throat pouch: display skin in rings - an amber heart, teal, a violet rim."""
    p = ctx.wp if ctx.wp is not None else ctx.p
    big = ctx.size[1] > 2.6 or ctx.size[0] > 2.6
    c0, r = ((0, 22.75, -8.0), (2.6, 2.6, 2.9)) if big else ((0, 24.75, -7.75), (1.3, 1.1, 1.7))
    d = np.sqrt((((p - np.asarray(c0)) / np.asarray(r)) ** 2).sum(axis=1))
    lv = px.proxy(ctx, c0, r, 0.85) + 0.1
    field = np.clip(1.15 - d * 0.75, 0, 1)
    if not big:
        ix, iy, W, H = px.texel(ctx)
        lv = lv - 0.12 * (iy % 2 == 1)                                     # folded when deflated
    c, g = _display(ctx, lv, field)
    return c, ctx.ones(), g * 0.75                                          # luminous skin, not a lamp


def mat_crest(ctx):
    """The hollow tubular crest: pale bone with darker growth rings and a thin line of
    display skin along each side."""
    ix, iy, W, H = px.texel(ctx)
    lv = px.rim(ctx, px.light(ctx, grad=0.1), 0.12, 0.12)
    i = qidx(ctx, len(BONE), lv - 0.02, 0.2)
    if ctx.face in ("east", "west", "up", "down"):
        L = W if ctx.face in ("east", "west") else H
        al = np.clip(np.floor(ctx.local[:, 2] * L), 0, L - 1).astype(int)
        i = np.where(al % 4 == 0, np.maximum(i - 1, 0), i)
    c = BONE[i]
    g = ctx.zeros()
    if ctx.face in ("east", "west") and H >= 3:
        line = iy == H // 2
        L = W
        al = np.clip(np.floor(ctx.local[:, 2] * L), 0, L - 1).astype(int)
        field = np.where(al % 6 == 3, 0.9, 0.5)
        dc, dg = _display(ctx, px.light(ctx) + 0.1, field)
        c = np.where(line[:, None], dc, c)
        g = np.where(line, dg, 0.0)
    return c, ctx.ones(), g


def mat_crestend(ctx):
    """The flared open end of the crest: a bone rim around the dark lumen (luminous in the overflow)."""
    ix, iy, W, H = px.texel(ctx)
    c = px.quant(ctx, BONE, px.light(ctx) + 0.05)
    g = ctx.zeros()
    if ctx.face in ("north", "south"):
        lumen = (ix >= 1) & (ix <= W - 2) & (iy >= 1) & (iy <= H - 2)
        over = _over(ctx) > 0.5
        inner = lumen & (ix >= 2) & (ix <= W - 3) & (iy >= 2) & (iy <= H - 3)
        c = np.where(lumen[:, None], px.col("#3a2a24" if not over else "#4fd8d0"), c)
        c = np.where(inner[:, None], px.col("#0d0707" if not over else "#c8fff6"), c)
        g = np.where(lumen, 0.9 if over else 0.0, g)
    else:
        c = np.where(px.border(ctx, 1, ("l", "r"))[:, None], BONE[1], c)
    return c, ctx.ones(), g


# ----------------------------------------------------------------------------- feathers (cutout planes)

def _fgrid(ctx):
    """Texel coordinates on a feather / membrane plane: `al` along it (0 at the root .. L-1 at
    the tip; planes grow toward +Z) and `ac` across it (0 at the bottom / -X edge)."""
    ix, iy, W, H = px.texel(ctx)
    vertical = ctx.face in ("east", "west")
    L, A = (W, H) if vertical else (H, W)
    al = np.clip(np.floor(ctx.local[:, 2] * L), 0, L - 1).astype(int)
    ac = np.clip(np.floor(ctx.local[:, 1 if vertical else 0] * A), 0, A - 1).astype(int)
    return al, ac, L, A


def _feathers(ctx, cw=3, ocelli=False, pal=FLIGHT, tips=True, bars=True, light=0.0, speculum=False):
    """Long feathers side by side (cutout): each `cw` texels wide with a shaft, a pointed tip
    (alternate feathers a texel shorter), an iridescent black-teal vane with a violet sheen,
    a pale tip; `ocelli`: an amber-teal-violet display eye near each tip."""
    al, ac, L, A = _fgrid(ctx)
    nf = max(1, int(round(A / cw)))
    cwf = A / nf
    f = np.floor((ac + 0.5) / cwf).astype(int)
    c = (ac + 0.5) - f * cwf
    mid = cwf / 2.0
    shaft = np.abs(c - mid) < 0.5
    edge = (c < 0.75) & (nf > 1)
    rem = (L - 1 - al) - (f % 2)                               # texels left to this feather's tip
    alpha = (rem >= 1) | ((rem == 0) & shaft)
    t = al / max(L - 1, 1)
    lv = 0.42 + light + 0.28 * t - np.where(edge, 0.14, 0.0) + np.where(shaft, 0.12, 0.0)
    if bars:
        lv = lv - np.where(((al + f) % 3 == 0) & (t > 0.3) & ~shaft, 0.12, 0.0)
    col = px.quant(ctx, pal, lv, dither=0.2)
    if pal is FLIGHT:                                           # iridescence: a violet sheen in diagonal bands
        sheen = ((al + 2 * ac) // 2) % 6 == 0
        col = np.where((sheen & ~shaft)[:, None], px.quant(ctx, SHEEN, lv + 0.1), col)
    if tips:
        col = np.where(((rem <= 1) & alpha)[:, None], TIP, col)
    if speculum and L >= 8:                                     # a bright display band across the panel
        T, Am, V, gl = _disp_pals(ctx)
        b0 = int(L * 0.45)
        band = (al >= b0) & (al <= b0 + 1) & alpha
        col = np.where(band[:, None], np.where((al == b0)[:, None], _pk(T, 3), _pk(T, 2)), col)
        col = np.where(((al == b0 - 1) & alpha)[:, None], TIP * 0.8 + 0.2 * _pk(T, 3), col)
        col = np.where((band & (al == b0) & shaft & (f % 2 == 0))[:, None], Am[-2], col)
    if ocelli and L >= 7:
        T, Am, V, gl = _disp_pals(ctx)
        ring = (rem >= 2) & (rem <= 4)
        heart = (rem == 3) & (np.abs(c - mid) < 0.75)
        col = np.where(ring[:, None], _pk(V, 2), col)
        col = np.where((ring & (np.abs(c - mid) < cwf / 2 - 0.4))[:, None], _pk(T, 3), col)
        col = np.where(heart[:, None], Am[-2], col)
    return col, alpha.astype(float)


def mat_flight(ctx):
    c, a = _feathers(ctx)
    return c, a, ctx.zeros()


def mat_armfan(ctx):
    c, a = _feathers(ctx, speculum=True)
    return c, a, ctx.zeros()


def mat_coverts(ctx):
    c, a = _feathers(ctx, cw=3, light=0.06)
    return c, a, ctx.zeros()


def mat_fanq(ctx):
    c, a = _feathers(ctx, cw=4, ocelli=True)
    return c, a, ctx.zeros()


def mat_tuft(ctx):
    """Soft plume tufts: downy, pale at the base darkening to umber tips, no barring."""
    c, a = _feathers(ctx, cw=3, pal=DOWNY, tips=False, bars=False, light=0.02)
    return c, a, ctx.zeros()


def mat_bristle(ctx):
    """Stiff pale-bone bristles (cutout): strands every other texel, uneven lengths."""
    ix, iy, W, H = px.texel(ctx)
    up = 1 - ctx.local[:, 1]                                  # 0 at the top
    h = (np.sin(ix * 2.3 + ctx.seed) * 0.5 + 0.5) * 0.35
    strand = (ix % 2 == 0) & (up >= h)
    c = px.quant(ctx, BRISTLE, 0.85 - 0.6 * up)
    return c, strand.astype(float), ctx.zeros()


def mat_osteo(ctx):
    """Bony osteoderm: ivory plate, a dark rim and a pale keel."""
    ix, iy, W, H = px.texel(ctx)
    c = px.quant(ctx, BONE, px.light(ctx, grad=0.1) + 0.08)
    c = np.where(px.border(ctx, 1)[:, None], BONE[0], c)
    if W >= 3:
        keel = (ix == W // 2) & ~px.border(ctx, 1, ("t", "b"))
        c = np.where(keel[:, None], BONE[4], c)
    return c, ctx.ones(), ctx.zeros()


def _scales(ctx, lv):
    """Coarse scales: rows of rounded scales offset like brickwork, dark grout."""
    ix, iy, W, H = px.texel(ctx)
    row = iy // 2
    cx = (ix + row) % 3
    grout = (cx == 2) | (iy % 2 == 1) & (cx == 1)
    return lv - np.where(grout, 0.15, 0.0) + np.where((iy % 2 == 0) & (cx == 0), 0.07, 0.0)


def mat_scale(ctx):
    lv = _scales(ctx, px.rim(ctx, px.light(ctx, grad=0.1), 0.08, 0.1))
    return px.quant(ctx, SCALE, lv), ctx.ones(), ctx.zeros()


def mat_shin(ctx):
    """Shank: downy above, coarse scales below."""
    p = ctx.wp if ctx.wp is not None else ctx.p
    lv = px.rim(ctx, px.light(ctx, grad=0.1), 0.08, 0.1)
    sc = px.quant(ctx, SCALE, _scales(ctx, lv))
    fe = _downy(ctx, lv - 0.1, 4, 3)
    return np.where((p[:, 1] > 6.5)[:, None], fe, sc), ctx.ones(), ctx.zeros()


def mat_fore(ctx):
    """Forearm: downy, with a band of display skin on the outer face."""
    lv = px.rim(ctx, px.light(ctx, grad=0.1), 0.08, 0.1)
    c = _downy(ctx, lv - 0.08, 4, 3)
    n = _wn(ctx)
    if abs(n[0]) > 0.6 and np.sign(n[0]) == np.sign(ctx.p[0, 0]):
        ix, iy, W, H = px.texel(ctx)
        band = (ix >= 1) & (ix <= W - 2) & (iy >= 2) & (iy <= H - 3)
        field = np.where((iy == 2) | (iy == H - 3), 0.2, np.where(iy % 3 == 0, 0.9, 0.5))
        dc, dg = _display(ctx, lv, field)
        return np.where(band[:, None], dc, c), ctx.ones(), np.where(band, dg, 0.0)
    return c, ctx.ones(), ctx.zeros()


def mat_sleeve(ctx):
    """First-person sleeve: the downy forearm."""
    lv = px.rim(ctx, px.light(ctx, grad=0.1), 0.08, 0.1)
    return _downy(ctx, lv - 0.05, 4, 3), ctx.ones(), ctx.zeros()


def mat_finger(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = px.quant(ctx, SCALE, px.light(ctx))
    if px.side(ctx):
        c = np.where((iy >= H - 1)[:, None], KERATIN[1], c)
    return c, ctx.ones(), ctx.zeros()


def mat_claw(ctx):
    return px.shade(ctx, KERATIN, offset=0.05, up=0.2), ctx.ones(), ctx.zeros()


def mat_spike(ctx):
    """The styliform digit: a long pale bone spike, darkening to a keratin point."""
    p = ctx.wp if ctx.wp is not None else ctx.p
    tip = np.clip((p[:, 1] - 16.5) / 3.0, 0, 1)
    lv = px.light(ctx, grad=0.05) + 0.12 - 0.45 * tip ** 2
    return px.quant(ctx, BONE, lv), ctx.ones(), ctx.zeros()


def mat_rod(ctx):
    """The bony support rods: ivory with dark joints."""
    ix, iy, W, H = px.texel(ctx)
    c = px.quant(ctx, BONE, px.light(ctx, grad=0.05) + 0.05)
    if px.side(ctx) and H > 4:
        c = np.where(((iy % 5) == 4)[:, None], BONE[0], c)
    return c, ctx.ones(), ctx.zeros()


# ----------------------------------------------------------------------------- membranes (cutout planes)

def _veins(ctx, al, ac, L, A):
    """Wine-red membrane: lighter where thin (toward the free edge), dark veins."""
    t = al / max(L - 1, 1)
    vein = ((ac + (al // 3)) % 4 == 0) & (al >= 1)
    lv = 0.5 + 0.28 * t - np.where(vein, 0.24, 0.0)
    return px.quant(ctx, WINE, lv, dither=0.2)


def mat_sail(ctx):
    """Hindwing sail: the rod runs along the far edge (local z = 1); the top and bottom edges
    are scalloped inward between the leg and the rod."""
    al, ac, L, A = _fgrid(ctx)
    u = (al + 0.5) / L
    v = (ac + 0.5) / A
    sag = 0.16 * np.sin(np.pi * np.clip(u, 0, 1)) * (L > 4)
    alpha = (v >= sag) & (v <= 1 - sag * 0.6)
    return _veins(ctx, al, ac, L, A), alpha.astype(float), ctx.zeros()


def mat_membtri(ctx):
    """The styliform membrane: fills the triangle between the forearm (front edge) and the
    bony spike running from the bottom-front to the top-back corner, scalloped on top."""
    al, ac, L, A = _fgrid(ctx)
    u = (al + 0.5) / L
    v = (ac + 0.5) / A
    scal = 0.1 * np.abs(np.sin(u * np.pi * 3))
    alpha = (v >= u - 0.08) & (v <= 1 - scal)
    return _veins(ctx, al, ac, L, A), alpha.astype(float), ctx.zeros()


def mat_frill(ctx):
    """The crest frill (display only): wine membrane between the raised crest and the skull,
    with display-skin veins."""
    al, ac, L, A = _fgrid(ctx)
    u = (al + 0.5) / L
    v = (ac + 0.5) / A
    alpha = v >= 0.15 + 0.7 * u * u
    c = _veins(ctx, al, ac, L, A)
    T, Am, V, gl = _disp_pals(ctx)
    spot = ((al + ac) % 5 == 0) & (v > 0.5)
    return np.where(spot[:, None], _pk(T, 3), c), alpha.astype(float), ctx.zeros()
