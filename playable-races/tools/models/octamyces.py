"""Race 009 - Octamyces Undecimus, Witness of the Eleventh Rift.

An extradimensional fungal organism that watches several realities at once - "something is
observing the player from a reality the player cannot observe in return".  Not a monster with
one eye and not malicious: unreadable.  Drawn as elegant pixel art next to vanilla Minecraft:

  * a large ASYMMETRIC mushroom cap: a wide thin brim (an umbrella, lifted on the creature's left)
    under a dome of layered tissue, each layer its own hue (deep blue-violet at the brim ->
    violet -> magenta -> pink at the crown: a coherent iridescent drift), lit filaments in the
    margin, a lattice of geometric spore pits at the crown.  It contradicts itself: two shelves
    on the back pass through each other, the upper layers can slide off the lower ones
  * spiral lamellae under the brim (they glow), radial gill vanes that turn, two pore pads that open
  * THE UNDECIMAL EYE in the front of the dome: eleven concentric polygon frames - a triangle
    inside a square inside a pentagon ... out to a thirteen-gon - each its own bone (ring0 ..
    ring10) turning on the viewing axis, every frame a quarter unit in front of the one inside
    it (a funnel into a starfield void: the pupil).  Pale and saturated frames alternate, so
    every ring reads on its own.  Eight trapezoid plates (lid0 .. lid7) stand open around it
    as a crown of points and fold shut over it to blink.  The iris rides the head group and
    turns toward where the player looks, on its own, inside its socket
  * a twisted, partly hollow stalk: three lattice tiers of pale strips, each turned further,
    wound round a glowing spiral core
  * EIGHT mycelial groups with different jobs (myc0 .. myc7, each a chain myc<N>_0..2):
    0/1 braided manipulators on the arms ending in three fingers at the vanilla hand (they hold
    the item), 2/3 propulsion fans (ribbed fins) at the back, 4 a sensor with three fine
    feelers, 5 a spore emitter (an earthstar puffball), 6 a stabiliser tassel of hanging
    filaments, 7 a resonance antenna with a small floating triangle; a fringe of glowing
    threads hangs from the brim
  * it floats: nothing comes within two and a half pixels of the ground

Variants: base (Witnessing) | sporeveil | record | offset | frame | unstable (on fire).
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

from kit.geo import Model
from kit import pixel as px
from models.common import accents, fp_sleeves, humanoid, mat_accent, q, segment

ID = "octamyces"
VARIANTS = ["base", "sporeveil", "record", "offset", "frame", "unstable"]
TEXTURES = {
    "base": {"record": 0.0, "frame": 0.0, "burn": 0.0},
    "record": {"record": 1.0, "frame": 0.0, "burn": 0.0},
    "frame": {"record": 0.0, "frame": 1.0, "burn": 0.0},
    "unstable": {"record": 0.0, "frame": 0.0, "burn": 1.0},
}
VARIANT_TEXTURE = {"base": "base", "sporeveil": "base", "record": "record", "offset": "base", "frame": "frame",
                   "unstable": "unstable"}

# ----------------------------------------------------------------------------- proportions
HEAD = (0.0, 24.0, 0.0)              # the player's head pivot (head_g and the look counter-rotation)
FLOAT_C = (0.0, 12.0, 0.5)           # the body's centre: hover bob, lean and roll pivot about here
CAP_J = (0.0, 16.0, 0.5)             # cap / stalk joint (the cap turns and tilts about it)
EYE_C = (0.0, 23.0, -7.0)            # centre of the iris (ring0's plane)
EYE_PIV = (0.0, 23.0, -8.0)          # the iris turns about a point inside its funnel
RING_SIDES = tuple(range(3, 14))     # ring0 = triangle (innermost) ... ring10 = thirteen-gon
RINGS = len(RING_SIDES)
RING_A0, RING_DA = 0.55, 0.44        # apothem of ring0 and the step outward
RING_DZ = 0.25                       # every ring sits a quarter unit in front of the one inside it
RING_T = 0.25                        # bar thickness: thin luminous lines with the void between them
LIDS = 8
LID_A = 5.5                          # apothem of the lid octagon (the hinges)
LID_LEN = 5.0                        # trapezoid plates: shut, they leave only the singularity showing
LID_OPEN = -138.0                    # rest fold: the plates stand open as a crown of points round the eye
LID_Z = EYE_C[2] - RING_DZ * (RINGS - 1) - 0.5     # hinge plane, just in front of the outermost ring
SOCKET = 5.75                        # half-opening of the socket in the cap
SOCKET_TOP = EYE_C[1] + SOCKET
SOCKET_BACK = -4.5                   # the socket's back wall
MYC = 8                              # primary mycelial groups
SEGS = 3                             # segments per group
BRIM_Y = (16.25, 17.0)
BRIM_C = (0.0, 16.625, 0.5)
BRIM_LIFT = -6.0                     # the brim is lifted on the creature's left (+X) side
STALK_Y = (7.75, 16.0)

# the dome above the brim: (y0, y1, x0, x1, z0, z1) per band; each band is an X-wide and a Z-deep box
# (a rounded footprint); the eye's socket is cut out of the front of the lower bands.  Lopsided on
# purpose: the left (+X) side swells, the crown sits left of centre.
BANDS = [
    (16.5, 20.0, -10.5, 10.5, -9.25, 9.0),
    (20.0, 23.0, -10.25, 10.75, -9.5, 8.75),
    (23.0, 25.5, -9.5, 10.25, -9.25, 8.0),
    (25.5, 27.5, -8.25, 9.25, -8.5, 7.25),
    (27.5, SOCKET_TOP, -6.75, 8.0, -7.5, 6.25),
    (SOCKET_TOP, 30.25, -5.25, 6.5, -6.25, 5.0),
    (30.25, 31.5, -2.75, 4.5, -4.0, 3.0),
]
UPPER = 3                            # bands from here up ride the cap_upper bone (Hyphal Offset slides them)
DOME_C = (0.5, 15.5, 0.0)            # light proxy for the dome
DOME_R = (11.5, 16.0, 10.0)


def ring_apothem(k: int) -> float:
    return RING_A0 + RING_DA * k


def ring_z(k: int) -> float:
    return EYE_C[2] - RING_DZ * k


def _norm_deg(a: float) -> float:
    a = (a + 180.0) % 360.0 - 180.0
    return 180.0 if abs(a + 180.0) < 1e-9 else round(a, 4) + 0.0


def _rot(a: float):
    a = _norm_deg(a)
    return None if abs(a) < 1e-6 else a


def strand(m: Model, bone: str, a, b, w: float, mat: str, overlap: float = 0.25, **kw):
    """A bar of cross-section w from a to b, turned on ONE axis only (the segment must lie in an
    axis plane: x-y, y-z or x-z).  Downward bars are built from b up to a (small angles)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    if d[1] < 0 and (abs(d[2]) < 1e-6 or abs(d[0]) < 1e-6):
        a, b, d = b, a, -d
    ln = q(float(np.linalg.norm(d)) + overlap)
    n = d / max(np.linalg.norm(d), 1e-9)
    if abs(n[0]) < 1e-6 and abs(n[2]) < 1e-6:           # vertical
        return m.cube(bone, (a[0] - w / 2, a[1], a[2] - w / 2), (w, ln, w), mat, **kw)
    if abs(d[2]) < 1e-6:                                 # x-y plane: a y bar turned about z
        return m.cube(bone, (a[0] - w / 2, a[1], a[2] - w / 2), (w, ln, w), mat, pivot=tuple(a),
                      rot=(0, 0, _norm_deg(math.degrees(math.atan2(n[0], n[1])))), **kw)
    if abs(d[0]) < 1e-6:                                 # y-z plane: a y bar turned about x
        return m.cube(bone, (a[0] - w / 2, a[1], a[2] - w / 2), (w, ln, w), mat, pivot=tuple(a),
                      rot=(_norm_deg(math.degrees(math.atan2(-n[2], n[1]))), 0, 0), **kw)
    if abs(d[1]) < 1e-6:                                 # x-z plane: a z bar turned about y
        return m.cube(bone, (a[0] - w / 2, a[1] - w / 2, a[2]), (w, w, ln), mat, pivot=tuple(a),
                      rot=(0, _norm_deg(math.degrees(math.atan2(n[0], n[2]))), 0), **kw)
    return segment(m, bone, a, b, w, w, mat, overlap=overlap, **kw)


def _perp(a, b):
    """Offset direction for parallel strands of the segment a->b (normal to its plane)."""
    d = np.asarray(b, float) - np.asarray(a, float)
    if abs(d[2]) < 1e-6 and abs(d[0]) > 1e-6:
        return np.array([0.0, 0.0, 1.0])
    if abs(d[0]) < 1e-6 and abs(d[2]) > 1e-6:
        return np.array([1.0, 0.0, 0.0])
    if abs(d[1]) < 1e-6:
        return np.array([0.0, 1.0, 0.0])
    return np.array([1.0, 0.0, 0.0])


# ============================================================================= build

def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=256)
    humanoid(m)
    # head chain: head_g and `steady` cancel the player's look exactly (x on one bone, y on the
    # next); `float_h` mirrors the body's hover; the cap then turns by a fraction of the look about
    # the stalk joint, and the iris by more, inside its socket
    m.bone("steady", "head_g", HEAD)
    m.bone("float_h", "steady", FLOAT_C)
    m.bone("float", "torso_g", FLOAT_C)
    m.bone("cap", "float_h", CAP_J)
    m.bone("cap_upper", "cap", (0.0, BANDS[UPPER][0], 0.5))
    m.bones["cap_upper"].variant["offset"] = ((-2.0, 0.75, 1.25), (0.0, -12.0, 0.0))
    _cap(m)
    _brim(m)
    _eye(m)
    _gills(m)
    _stalk(m)
    _mycelia(m)
    fp_sleeves(m, "tendril_fp", width=4.5)
    accents(m, [
        ("c", "rim", "brim", (-9.0, 17.25, -7.0), (5.0, 0.5, 2.0)),
        ("c", "band", "cap", (8.25, 21.5, -6.75), (3.0, 1.0, 3.5)),
        ("l", "r", "myc2_0", (-3.25, 14.75, 4.75), (1.5, 1.5, 1.5)),
        ("l", "l", "myc3_0", (3.25, 14.75, 4.75), (1.5, 1.5, 1.5)),
        ("f", "r", "myc6_2", (-2.0, 7.5, 7.25), (1.0, 0.5, 1.0)),
        ("f", "l", "myc6_2", (1.9, 7.25, 7.5), (1.0, 0.5, 1.0)),
    ])
    m.pack()
    return m


# ----------------------------------------------------------------------------- the cap

def _box_minus_socket(b, half=SOCKET):
    """Split box (x0,x1,y0,y1,z0,z1) around the eye socket: the part behind the socket's back wall
    and the two cheeks either side of it (and the part above it)."""
    x0, x1, y0, y1, z0, z1 = b
    if y0 >= SOCKET_TOP or z0 >= SOCKET_BACK:
        return [b]
    out = []
    if z1 > SOCKET_BACK:
        out.append((x0, x1, y0, y1, SOCKET_BACK, z1))
    zf = min(z1, SOCKET_BACK)
    if x0 < -half:
        out.append((x0, -half, y0, y1, z0, zf))
    if x1 > half:
        out.append((half, x1, y0, y1, z0, zf))
    if y1 > SOCKET_TOP:
        out.append((max(x0, -half), min(x1, half), SOCKET_TOP, y1, z0, zf))
    return out


@lru_cache(maxsize=None)
def cap_boxes():
    """(x0,x1,y0,y1,z0,z1, band) for every cube of the dome."""
    out = []
    for i, (y0, y1, x0, x1, z0, z1) in enumerate(BANDS):
        c = q(0.3 * min(x1 - x0, z1 - z0) / 2)            # corner chamfer of the footprint
        for bx in _box_minus_socket((x0, x1, y0, y1, z0, z1 - c)):
            out.append((*bx, i))
        if i == 0:
            continue                                    # the lowest band is mostly under the brim
        zf = max(z0, SOCKET_BACK + 0.25) if y0 < SOCKET_TOP else z0
        out.append((x0 + c, x1 - c, y0 + 0.25, y1 + 0.25, zf, z1, i))
    return tuple(out)


def _cap(m: Model) -> None:
    for x0, x1, y0, y1, z0, z1, i in cap_boxes():
        bone = "cap_upper" if i >= UPPER else "cap"
        m.cube(bone, (x0, y0, z0), (x1 - x0, y1 - y0, z1 - z0), f"cap{i}")
    # two shelves stepping out of the dome's back that pass THROUGH each other (an X seen from
    # behind): one tilts up, one tilts down - each its own bone so they can slide apart (offset)
    pa = m.bone("plate_a", "cap", (5.0, 22.5, 4.5))
    m.cube(pa.name, (0.5, 22.25, 0.5), (11.0, 0.5, 10.5), "plate", pivot=(5.0, 22.5, 4.5), rot=(0, 0, -14))
    pb = m.bone("plate_b", "cap_upper", (5.0, 22.5, 4.5))
    m.cube(pb.name, (-2.5, 22.25, 3.5), (11.5, 0.5, 7.5), "plate", pivot=(5.0, 22.5, 4.5), rot=(0, 0, 12))
    pa.variant["offset"] = ((1.0, 0.5, 1.5), None)
    pb.variant["offset"] = ((-1.5, -0.5, 1.0), None)
    m.bones["cap_upper"].locators["cap_top"] = (1.0, 31.75, -0.5)


THREADS = ((-12.25, 2.5, 4.5), (-9.5, 8.5, 3.0), (-3.5, 11.25, 5.0), (5.0, 10.75, 3.5), (10.5, 6.75, 5.0),
           (12.5, -2.5, 3.0))


def _brim(m: Model) -> None:
    """The umbrella: a wide thin brim lifted on one side, a fringe of glowing threads under its edge."""
    br = m.bone("brim", "cap", BRIM_C, (0.0, 0.0, BRIM_LIFT))
    br.variant["sporeveil"] = ((0.0, 0.0, 0.0), (-5.0, 0.0, BRIM_LIFT))        # the brim flares up at the front
    br.variant["unstable"] = ((0.0, -0.25, 0.0), (4.0, 0.0, BRIM_LIFT + 5.0))  # scorched: it sags
    y0, y1 = BRIM_Y
    m.cube(br.name, (-13.5, y0, -9.5), (27.0, y1 - y0, 20.0), "brim")
    m.cube(br.name, (-10.75, y0 - 0.25, -12.0), (21.5, y1 - y0, 24.5), "brim")
    for x, z, ln in THREADS:
        m.cube(br.name, (x - 0.25, y0 - ln, z - 0.25), (0.5, ln, 0.5), "thread")


# ----------------------------------------------------------------------------- the undecimal eye

def _eye(m: Model) -> None:
    cx, cy, cz = EYE_C
    eye = m.bone("eye", "cap", EYE_PIV)
    eye.locators["eye_c"] = (cx, cy, cz + 0.25)
    # the void behind the iris: an octagon of deep space (two squares turned 45 degrees), and the
    # singularity at its centre
    pu = m.bone("pupil", eye.name, (cx, cy, cz + 0.75))
    m.cube(pu.name, (cx - 4.5, cy - 4.5, cz + 0.75), (9.0, 9.0, 0.5), "void")
    m.cube(pu.name, (cx - 4.5, cy - 4.5, cz + 0.5), (9.0, 9.0, 0.5), "void", pivot=(cx, cy, cz + 0.75), rot=(0, 0, 45))
    m.cube(pu.name, (cx - 0.75, cy - 0.75, cz + 0.25), (1.5, 1.5, 0.25), "singularity")
    for k, n in enumerate(RING_SIDES):
        z = ring_z(k)
        r = m.bone(f"ring{k}", eye.name, (cx, cy, z))
        a = ring_apothem(k)
        ln = q(2 * (a + RING_T / 2) * math.tan(math.pi / n) + 0.15)
        off = 180.0 / n                              # at rest every polygon has a vertex at the top (aligned)
        for j in range(n):
            ang = _rot(off + 360.0 * j / n)
            m.cube(r.name, (cx - ln / 2, cy + a - RING_T / 2, z - 0.25), (ln, RING_T, 0.5), "ring",
                   pivot=(cx, cy, z), rot=(0, 0, ang) if ang else None)
    # eight trapezoid plates hinged on an octagon around the iris (on the socket, so they do not
    # turn with the gaze): at rest they stand open, folded forward and out as a crown of points;
    # a blink folds them shut (rx -> 0) into a flat octagon with only the singularity showing
    so = m.bone("socket", "cap", (cx, cy, LID_Z))
    w = q(2 * LID_A * math.tan(math.pi / LIDS))
    for j in range(LIDS):
        th = _norm_deg(45.0 * j)
        hx = cx + LID_A * math.sin(math.radians(th))
        hy = cy + LID_A * math.cos(math.radians(th))
        lid = m.bone(f"lid{j}", so.name, (hx, hy, LID_Z), (LID_OPEN, 0.0, th))
        m.cube(lid.name, (hx - w / 2, hy - LID_LEN, LID_Z - 0.25), (w, LID_LEN, 0.5), "lid", cutout=True,
               faces={"north", "south", "up"})


# ----------------------------------------------------------------------------- gills

def _gills(m: Model) -> None:
    """Under the brim: three vanes crossing at the stalk (six radial fins) that turn slowly, and
    two pads of pores that open."""
    g = m.bone("gill_spin", "cap", (0.0, 15.5, 0.5))
    for a in (0.0, 60.0, 120.0):
        m.cube(g.name, (-10.5, 14.75, 0.25), (21.0, 1.5, 0.5), "gill", pivot=(0.0, 15.5, 0.5), rot=(0, a, 0) if a else None)
    for s, p in ((-1, "r"), (1, "l")):
        fl = m.bone(f"gill_{p}", "cap", (s * 4.25, 16.0, 4.0))
        m.cube(fl.name, (s * 4.25 - 1.75, 15.25, 2.25), (3.5, 0.75, 3.5), "pore")
        fl.variant["sporeveil"] = ((0.0, -0.5, 0.0), (0.0, 0.0, s * 24.0))     # the pads hang open
        # Parallax Sporeveil: clusters of ripe spores swell out of the opened pads
        for k, (dx, dz, sz) in enumerate(((0.75, 1.0, 1.0), (-0.5, -0.25, 0.75))):
            m.box(fl.name, (s * (4.25 + dx), 14.75 - 0.25 * k, 4.0 + dz), (sz, sz, sz), "spore", only={"sporeveil"})
    m.bones["gill_spin"].locators["gills"] = (0.0, 14.5, 0.5)


# ----------------------------------------------------------------------------- the stalk

STALK_TIERS = ((8.25, 11.0, 0.0), (11.0, 13.75, 22.5), (13.75, 16.5, 45.0))


def _stalk(m: Model) -> None:
    st = m.bone("stalk", "float", (0.0, 11.0, 0.5))
    m.box(st.name, (0.0, 12.25, 0.5), (1.5, 8.5, 1.5), "core")
    # translucent strips wound round the glowing core: three lattice tiers, each turned further
    for y0, y1, a in STALK_TIERS:
        m.cube(st.name, (-1.75, y0, -1.25), (3.5, y1 - y0, 3.5), "shell", cutout=True, pivot=(0.0, (y0 + y1) / 2, 0.5),
               rot=(0, a, 0) if a else None)
    m.box(st.name, (0.0, 8.25, 0.5), (3.5, 1.0, 3.5), "volva")            # the bulb at the base
    m.box(st.name, (0.0, 7.75, 0.5), (2.5, 1.0, 2.5), "volva")
    st.locators["base_c"] = (0.0, 7.25, 0.5)


# ----------------------------------------------------------------------------- the eight mycelial groups

# chain points per group (every segment lies in an axis plane: single-axis cubes)
MYC_PTS = {
    # 0/1 manipulators: from under the brim out and down to the vanilla hand (three fingers)
    0: [(-4.75, 15.75, -0.5), (-7.25, 14.0, -0.5), (-8.0, 12.25, -0.5), (-6.5, 10.75, -0.5)],
    # 2/3 propulsion fans: sweep back from under the brim, a ribbed fin at the end
    2: [(-3.25, 15.75, 3.0), (-3.25, 14.0, 6.0), (-5.25, 13.0, 6.0), (-5.25, 12.25, 8.5)],
    # 4 sensor (front-left): reaches forward and down, three fine feelers
    4: [(3.5, 15.75, -3.0), (3.5, 13.0, -5.75), (5.25, 11.0, -5.75), (5.25, 9.75, -8.25)],
    # 5 spore emitter (front-right): hangs and curls up to hold an earthstar puffball
    5: [(-4.5, 15.75, -2.75), (-7.75, 12.75, -2.75), (-9.75, 9.75, -2.75), (-11.0, 11.0, -2.75)],
    # 6 stabiliser: a curtain of filaments trailing from under the back of the brim, a kite's tail
    6: [(0.0, 15.75, 4.25), (0.0, 12.25, 5.75), (0.0, 8.75, 6.25), (0.0, 5.5, 8.75)],
    # 7 resonance antenna: rises from the crown, a small floating triangle at its tip
    7: [(2.0, 31.25, 0.5), (2.0, 33.0, 1.75), (2.75, 34.5, 1.75), (2.75, 35.25, 2.5)],
}
MYC_PTS[1] = [(-x, y, z) for x, y, z in MYC_PTS[0]]
MYC_PTS[3] = [(-x, y, z) for x, y, z in MYC_PTS[2]]
MYC_PARENT = {0: "r_arm_g", 1: "l_arm_g", 2: "float", 3: "float", 4: "float", 5: "float", 6: "float", 7: "cap_upper"}
MYC_W = {0: [1.0, 1.0, 0.75], 2: [1.0, 1.0, 0.75], 4: [1.0, 0.75, 0.5], 5: [1.25, 1.0, 0.75],
         6: [0.5, 0.5, 0.5], 7: [0.75, 0.5, 0.5]}
MYC_W[1], MYC_W[3] = MYC_W[0], MYC_W[2]
MYC_N = {0: 2, 1: 2, 2: 2, 3: 2, 4: 1, 5: 1, 6: 4, 7: 1}           # parallel strands per segment
CURTAIN_X = (-2.0, -0.75, 0.6, 1.9)          # the stabiliser's four filaments, side by side
CURTAIN_END = (0.5, -0.5, 0.0, 1.0)          # each ends a little higher (+) or lower (-)
MYC_JOB = {0: "m", 1: "m", 2: "f", 3: "f", 4: "s", 5: "p", 6: "b", 7: "a"}
FIN_SPREAD = {2: (-20.0, -28.0, 12.0), 3: (-20.0, 28.0, -12.0), 4: (-18.0, 22.0, 0.0), 5: (0.0, 0.0, -24.0),
              6: (18.0, 0.0, 0.0), 7: (-10.0, 0.0, -10.0)}
DROOP = {2: (14.0, 0.0, 0.0), 3: (14.0, 0.0, 0.0), 4: (16.0, 0.0, 0.0), 5: (0.0, 0.0, 10.0), 6: (-6.0, 0.0, 0.0),
         7: (22.0, 0.0, 0.0)}
def _mycelia(m: Model) -> None:
    for g in range(MYC):
        pts = [np.array(p) for p in MYC_PTS[g]]
        job = MYC_JOB[g]
        root = m.bone(f"myc{g}", MYC_PARENT[g], tuple(pts[0]))
        if g in FIN_SPREAD:                  # Hyphal Offset: the mycelia stand out like fins
            root.variant["offset"] = ((0.0, 0.0, 0.0), FIN_SPREAD[g])
        if g in DROOP:                       # on fire: the mycelia hang limp
            root.variant["unstable"] = ((0.0, 0.0, 0.0), DROOP[g])
        par = root.name
        for k in range(SEGS):
            b = m.bone(f"myc{g}_{k}", par, tuple(pts[k])).name
            mat = f"hy_{job}{k}"
            a, e = pts[k], pts[k + 1]
            w = MYC_W[g][k]
            if g == 6:
                for t, dx in enumerate(CURTAIN_X):
                    o = np.array([dx, 0.0, 0.0])
                    end = e + o + (np.array([0.0, CURTAIN_END[t], 0.0]) if k == SEGS - 1 else 0.0)
                    strand(m, b, a + o, end, w, mat)
            elif MYC_N[g] == 2:
                pp = _perp(a, e) * 0.4
                strand(m, b, a - pp, e - pp, w, mat)
                strand(m, b, a + pp, e + pp + np.array([0.0, 0.25, 0.0]), w * 0.75 if k else w, mat)
            else:
                strand(m, b, a, e, w, mat)
            par = b
        tip = f"myc{g}_{SEGS - 1}"
        e = pts[-1]
        s = -1 if g in (0, 2) else 1
        if g in (0, 1):            # three fingers around the held item
            strand(m, tip, e, e + np.array([0.0, -1.75, -1.0]), 0.5, "grip", overlap=0.0)
            strand(m, tip, e, e + np.array([0.0, -1.75, 1.0]), 0.5, "grip", overlap=0.0)
            strand(m, tip, e, e + np.array([-s * 1.25, -1.25, 0.0]), 0.5, "grip", overlap=0.0)
            m.bones[tip].locators[f"{'r' if g == 0 else 'l'}_grip"] = tuple(e + np.array([0.0, -1.0, 0.0]))
        elif g in (2, 3):          # a ribbed fin spreading back from the stem (a half ellipse)
            m.cube(tip, (e[0] - 0.25, e[1] - 3.5, e[2] - 0.25), (0.5, 7.0, 6.5), "fan", cutout=True,
                   pivot=tuple(e), rot=(0, s * 28.0, 0), faces={"east", "west"})
        elif g == 4:               # three fine feelers
            strand(m, tip, e, e + np.array([0.0, 1.25, -1.75]), 0.25, "hy_tip", overlap=0.0)
            strand(m, tip, e, e + np.array([0.0, -1.0, -1.75]), 0.25, "hy_tip", overlap=0.0)
            strand(m, tip, e, e + np.array([1.5, 0.5, 0.0]), 0.25, "hy_tip", overlap=0.0)
            m.bones[tip].locators["sensor"] = tuple(e + np.array([0.0, 0.0, -1.5]))
        elif g == 5:               # the earthstar: a puffball sitting in a star of rays
            c = e + np.array([-0.25, 1.0, 0.0])
            m.box(tip, tuple(c + np.array([0.0, 0.75, 0.0])), (3.0, 2.0, 3.0), "puff")
            m.box(tip, tuple(c + np.array([0.0, 1.0, 0.0])), (2.0, 3.0, 2.0), "puff")
            m.box(tip, tuple(c + np.array([0.0, -0.5, 0.0])), (5.0, 0.5, 1.5), "puff_rays")
            m.box(tip, tuple(c + np.array([0.0, -0.75, 0.0])), (1.5, 0.5, 5.0), "puff_rays")
            m.bones[tip].locators["spores"] = tuple(c + np.array([0.0, 2.75, 0.0]))
        elif g == 7:               # a small floating triangle at the tip, echoing the eye
            tc = e + np.array([0.0, 1.25, 0.0])
            for j in range(3):
                ang = _rot(60.0 + 120.0 * j)
                m.cube(tip, (tc[0] - 0.75, tc[1] + 0.4, tc[2] - 0.25), (1.5, 0.25, 0.5), "crystal",
                       pivot=tuple(tc), rot=(0, 0, ang) if ang else None)
            m.bones[tip].locators["antenna"] = tuple(tc)


# ============================================================================= materials

def _P(ctx, k):
    return ctx.params.get(k, 0.0)


def _wp(ctx):
    return ctx.wp if ctx.wp is not None else ctx.p


def _burn(ctx) -> bool:
    return _P(ctx, "burn") > 0.5


# layered tissue: the hue drifts from deep blue-violet (brim) to pink (crown); every layer is one ramp
LAYER_LO = ("#110b2b", "#1b1447", "#271d63", "#342880", "#45359b", "#5946b1", "#705dc5", "#8d7cd8", "#b0a5ea")
LAYER_HI = ("#290a29", "#410f42", "#5c155a", "#791d73", "#95288a", "#af379c", "#c650ad", "#d973be", "#eda0d2")
LAYER = [px.pal(*LAYER_LO) * (1 - t) + px.pal(*LAYER_HI) * t for t in np.linspace(0.0, 1.0, len(BANDS))]
CYAN = px.pal("#0a2a30", "#0e4a4c", "#13716a", "#1f9a86", "#3fc7a6", "#86ecc9", "#d4fff0")
VOID = px.pal("#030209", "#070512", "#0c0920", "#151033")
LILAC = px.pal("#2e2746", "#463d63", "#615782", "#7f75a0", "#9e95bc", "#beb6d6", "#ddd8ec", "#f4f2fa")
MYCEL = px.pal("#2a1c46", "#432f6c", "#604690", "#8061b0", "#a080cc", "#c0a4e2", "#dccaf2", "#f4ecfc")
PINK = px.pal("#3e0f30", "#66184e", "#93246c", "#bb3a88", "#dc5ea4", "#f38fc2", "#ffc6e2")
GOLD = px.pal("#4a2c0e", "#7a5018", "#ad7c2a", "#d8aa48", "#f3d27c", "#fff0c0")
CREAM = px.pal("#3e2a32", "#6a4f58", "#977b80", "#c1a9a6", "#e2d2c8", "#f8efe6")
EMBER = px.pal("#1a0806", "#3a120a", "#6a220e", "#a63e12", "#e06a1e", "#ffb050")
ASH = px.pal("#0d0a0f", "#18131c", "#241d2a", "#322938", "#433848", "#584c5c", "#6f6474")
SHEEN = px.col("#a8f0ff")
TIP = {"m": PINK, "f": CYAN, "s": CYAN, "p": CREAM, "b": CYAN, "a": CYAN}
# the iris: pale and saturated frames alternate so every ring reads on its own; the hue drifts
# mint -> cyan -> blue -> violet -> magenta -> pink from the centre out
RING_COL = ["#f2fff9", "#2fd9a6", "#cbfff0", "#2aa6d6", "#b4e6ff", "#4c5ee8", "#cbbcff", "#9a3fe0", "#f6c2f6",
            "#e0329f", "#ffc4dc"]


def _socket_face(ctx) -> np.ndarray:
    """Texels on the socket's inner walls (behind / beside the eye)."""
    p = ctx.p
    inside = (np.abs(p[:, 0]) <= SOCKET + 0.3) & (p[:, 1] <= SOCKET_TOP + 0.01) & (p[:, 2] <= SOCKET_BACK + 0.3)
    return inside & (p[:, 1] >= BANDS[0][0] - 0.01) & (p[:, 2] >= BANDS[1][4] + 0.3)


def _layer(ctx, band: int):
    lv = px.proxy(ctx, DOME_C, DOME_R, 0.95) + 0.06
    ix, iy, W, H = px.texel(ctx)
    burn = _burn(ctx)
    ramp = ASH if burn else LAYER[band]
    c = px.quant(ctx, ramp, lv, dither=0.3)
    g = ctx.zeros()
    if px.side(ctx) and band <= 2:
        # striations in the translucent margin: darker grooves, a few filaments lit from inside
        groove = ((ix + band) % 4) == 0
        c = np.where(groove[:, None], c * 0.82, c)
        # every third groove carries a filament lit from the gills below: bright at the brim, fading upward
        lit = groove & (((ix // 4) + band + ctx.seed) % 3 == 0)
        k = np.clip((iy + 0.5) / H, 0, 1) * (1.0 if band == 0 else 0.55)
        fc = EMBER[4] if burn else CYAN[4]
        c = np.where(lit[:, None], c * (1 - 0.65 * k[:, None]) + fc[None, :] * (0.65 * k[:, None]), c)
        g = np.where(lit, 0.3 * k, g)
    elif ctx.face == "up" and band >= len(BANDS) - 3:
        # geometric spore pits at the crown: a sparse staggered lattice of lit points
        lat = ((iy % 3) == 1) & (((ix + (iy // 3) * 2) % 5) == 2) & ~px.border(ctx, 1)
        c = np.where(lat[:, None], EMBER[3] if burn else GOLD[4], c)
        g = np.where(lat, 0.45, g)
    sock = _socket_face(ctx)
    if sock.any():
        dark = px.quant(ctx, ASH if burn else VOID, lv * 0.45 + 0.4)
        c = np.where(sock[:, None], dark, c)
        g = np.where(sock, 0.0, g)
    return c, ctx.ones(), g


def _cap_mat(band: int):
    return lambda ctx: _layer(ctx, band)


def mat_brim(ctx):
    """The umbrella's brim: the cap's own tissue on top with radial grooves, a pale margin, and
    spiral lamellae glowing underneath."""
    ix, iy, W, H = px.texel(ctx)
    burn = _burn(ctx)
    p = ctx.p
    r = np.hypot(p[:, 0], p[:, 2] - 0.5)
    ang = np.degrees(np.arctan2(p[:, 2] - 0.5, p[:, 0]))
    if ctx.face == "up":
        lv = px.proxy(ctx, DOME_C, DOME_R, 0.95) + 0.08 - 0.1 * np.clip((r - 9.0) / 5.0, 0, 1)
        c = px.quant(ctx, ASH if burn else LAYER[0], lv, dither=0.45)
        groove = (np.mod(ang + 360.0, 10.0) < 2.0) & (r > 7.5)
        c = np.where(groove[:, None], c * 0.8, c)
        return c, ctx.ones(), ctx.zeros()
    if ctx.face == "down":
        # spiral lamellae: lines of constant (angle - k * ln r)
        sp = np.mod(ang - 95.0 * np.log(np.maximum(r, 0.5)), 20.0) < 6.5
        c = np.where(sp[:, None], EMBER[3] if burn else CYAN[4], EMBER[0] if burn else CYAN[0])
        return c, ctx.ones(), np.where(sp, 0.4 if not burn else 0.2, 0.06)
    top = iy == 0
    c = np.where(top[:, None], (ASH[5] if burn else LAYER[0][8]), (EMBER[3] if burn else CYAN[3]))
    return c, ctx.ones(), np.where(top, 0.1, 0.4)


def mat_thread(ctx):
    ix, iy, W, H = px.texel(ctx)
    burn = _burn(ctx)
    c = px.quant(ctx, ASH if burn else LILAC, px.light(ctx, grad=0.0) + 0.05)
    tip = iy >= H - 1
    c = np.where(tip[:, None], EMBER[4] if burn else CYAN[5], c)
    return c, ctx.ones(), np.where(tip, 0.7, 0.1)


def mat_plate(ctx):
    """Geometric shelves: magenta tissue with a luminous cyan rim and an inset line."""
    ix, iy, W, H = px.texel(ctx)
    burn = _burn(ctx)
    lv = px.light(ctx) + 0.05
    c = px.quant(ctx, ASH if burn else PINK, lv - 0.15)
    edge = px.border(ctx, 1)
    inset = (px.border(ctx, 3) & ~px.border(ctx, 2)) if min(W, H) >= 7 else np.zeros(ctx.N, bool)
    c = np.where(edge[:, None], EMBER[3] if burn else CYAN[5], c)
    c = np.where(inset[:, None], EMBER[2] if burn else PINK[4], c)
    g = np.where(edge, 0.45, np.where(inset, 0.2, 0.0))
    return c, ctx.ones(), g


def mat_void(ctx):
    """Deep space: near-black with a faint violet nebula and sparse stars in odd colours."""
    p = ctx.p
    d = np.hypot(p[:, 0] - EYE_C[0], p[:, 1] - EYE_C[1])
    neb = 0.5 + 0.5 * np.sin(p[:, 0] * 1.3 + p[:, 1] * 0.7) * np.cos(p[:, 1] * 1.1 - p[:, 0] * 0.4)
    c = np.where((neb > 0.8)[:, None], VOID[3], np.where((neb > 0.55)[:, None], VOID[2], VOID[1]))
    c = np.where((d < 1.6)[:, None], VOID[0], c)
    h = px.hash01(ctx, 3)
    star = (h > 0.95) & (d > 1.2)
    scol = np.where((px.hash01(ctx, 9) > 0.6)[:, None], CYAN[5],
                    np.where((px.hash01(ctx, 11) > 0.5)[:, None], PINK[5], GOLD[5]))
    c = np.where(star[:, None], EMBER[4] if _burn(ctx) else scol, c)
    return c, ctx.ones(), np.where(star, 0.75, 0.04 + 0.1 * _P(ctx, "frame"))


def mat_singularity(ctx):
    c = np.broadcast_to(VOID[0], (ctx.N, 3)).copy()
    if ctx.face == "north":
        rec = _P(ctx, "record")
        ring = px.border(ctx, 1)
        c = np.where(ring[:, None], PINK[4] if rec > 0.5 else VOID[3], c)
        return c, ctx.ones(), np.where(ring, 0.3 + 0.5 * rec, 0.0)
    return c, ctx.ones(), ctx.zeros()


def ring_index(ctx) -> int:
    zc = ctx.origin[2] + ctx.size[2] / 2
    return int(np.clip(round((EYE_C[2] - zc) / RING_DZ), 0, RINGS - 1))


def mat_ring(ctx):
    k = ring_index(ctx)
    base = px.col(RING_COL[k])
    rec, frame, burn = _P(ctx, "record"), _P(ctx, "frame"), _burn(ctx)
    if frame > 0.5:                       # luminous, but every frame keeps its own hue
        base = base * 0.6 + px.col("#ffffff") * 0.4
    elif rec > 0.5:
        base = base * 0.8 + px.col("#fff4fa") * 0.2
    lv = px.light(ctx, grad=0.0)
    c = base[None, :] * (0.8 + 0.25 * lv)[:, None]
    g = 0.4 + 0.25 * rec + 0.3 * frame
    if burn:
        c = c * 0.4 + EMBER[2][None, :] * 0.3
        g = 0.12
    return c, ctx.ones(), np.full(ctx.N, g)


def mat_lid(ctx):
    """A trapezoid plate (alpha-tested), wide at its hinge.  Open, its south face looks out of the
    crown (deep tissue, a pale edge, a pink spine); shut, the north faces make an octagon with
    luminous seams."""
    ix, iy, W, H = px.texel(ctx)
    burn = _burn(ctx)
    lv = px.light(ctx, grad=0.0)
    if ctx.face not in ("north", "south"):
        return px.quant(ctx, ASH if burn else LAYER[1], lv + 0.1), ctx.ones(), ctx.zeros()
    t = (iy + 0.5) / H                                      # 0 at the hinge .. 1 at the inner end
    half = (W / 2.0) * (1.0 - t * 0.88)
    dx = np.abs(ix + 0.5 - W / 2.0)
    inside = dx <= half + 0.3
    edge = inside & (dx > half - 0.9)
    if ctx.face == "north":
        c = px.quant(ctx, ASH if burn else LAYER[2], lv + 0.05)
        c = np.where(edge[:, None], EMBER[4] if burn else CYAN[5], c)
    else:
        c = px.quant(ctx, ASH if burn else LAYER[1], 0.45 + 0.35 * (1 - t))
        c = np.where(edge[:, None], EMBER[4] if burn else SHEEN, c)
        spine = inside & (dx < 0.6) & (iy >= 1) & (iy <= H - 2)
        c = np.where(spine[:, None], EMBER[3] if burn else PINK[5], c)
    return c, inside.astype(float), ctx.zeros()


def mat_gill(ctx):
    ix, iy, W, H = px.texel(ctx)
    burn = _burn(ctx)
    lv = px.light(ctx, grad=0.0) + 0.05
    c = px.quant(ctx, EMBER if burn else CYAN, lv)
    lam = (ix % 2) == 0
    c = np.where(lam[:, None], EMBER[1] if burn else CYAN[1], c)
    return c, ctx.ones(), np.where(lam, 0.0, 0.4 if not burn else 0.2)


def mat_pore(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx) + 0.05
    burn = _burn(ctx)
    c = px.quant(ctx, ASH if burn else LAYER[3], lv)
    pores = ((ix % 3) == 1) & ((iy % 3) == 1)
    c = np.where(pores[:, None], EMBER[4] if burn else GOLD[4], c)
    return c, ctx.ones(), np.where(pores, 0.6, 0.0)


def mat_shell(ctx):
    """The stalk's lattice (alpha-tested): broad diagonal strips of deep translucent tissue wound
    round the glowing core, each strip lit along its upper edge."""
    ix, iy, W, H = px.texel(ctx)
    burn = _burn(ctx)
    lv = px.light(ctx, grad=0.12) + 0.1
    ramp = ASH if burn else LAYER[1]
    c = px.quant(ctx, ramp, lv)
    if px.side(ctx):
        k = (ix + iy) % 6
        a = (k < 3).astype(float)
        c = np.where((k == 0)[:, None], (EMBER[3] if burn else MYCEL[6]), c)
        c = np.where((k == 2)[:, None], ramp[2], c)
        return c, a, ctx.zeros()
    return c, ctx.ones(), ctx.zeros()


def mat_volva(ctx):
    ix, iy, W, H = px.texel(ctx)
    burn = _burn(ctx)
    lv = px.cyl(ctx, (0, 5, 0.5), (0, 9, 0.5), 0.7) + 0.15
    c = px.quant(ctx, ASH if burn else LAYER[0], lv)
    if px.side(ctx):
        c = np.where((iy == 0)[:, None], SHEEN * 0.6 + c * 0.4, c)
    return c, ctx.ones(), ctx.zeros()


def mat_core(ctx):
    ix, iy, W, H = px.texel(ctx)
    burn = _burn(ctx)
    sp = ((ix + iy) % 4) < 2
    c = np.where(sp[:, None], EMBER[4] if burn else PINK[5], EMBER[2] if burn else CYAN[5])
    return c, ctx.ones(), np.full(ctx.N, 0.85 if not burn else 0.4)


def _hypha(job: str, k: int):
    """Mycelial strand k (0 root .. 2 tip): pale lilac fading into the group's luminous colour,
    a lit filament running down its middle."""
    def mat(ctx):
        ix, iy, W, H = px.texel(ctx)
        burn = _burn(ctx)
        lv = px.light(ctx, grad=0.0) + 0.04 + 0.05 * k
        ramp = ASH if burn else (MYCEL if k < 2 else TIP[job])
        c = px.quant(ctx, ramp, lv)
        g = np.full(ctx.N, 0.25 if (k == 2 and not burn) else 0.0)
        if px.side(ctx) and not burn and W >= 2:
            vein = ix == W // 2
            c = np.where(vein[:, None], TIP[job][5] * 0.75 + c * 0.25, c)
            g = np.where(vein, 0.4, g)
        return c, ctx.ones(), g
    return mat


def mat_hy_tip(ctx):
    lv = px.light(ctx, grad=0.0) + 0.25
    burn = _burn(ctx)
    return px.quant(ctx, EMBER if burn else CYAN, lv), ctx.ones(), np.full(ctx.N, 0.65)


def mat_grip(ctx):
    lv = px.light(ctx) + 0.1
    burn = _burn(ctx)
    return px.quant(ctx, ASH if burn else PINK, lv), ctx.ones(), np.full(ctx.N, 0.35 if not burn else 0.0)


def mat_fan(ctx):
    """A propulsion fin (alpha-tested): five rays fanning back from the stem at the middle of its
    front edge, the membrane scalloped between them, pale where it joins the stem."""
    burn = _burn(ctx)
    ramp = EMBER if burn else CYAN
    c = px.quant(ctx, ramp, px.light(ctx, grad=0.0))
    a = ctx.ones()
    if ctx.face in ("east", "west"):
        dz = (ctx.p[:, 2] - ctx.origin[2]) * 2.0 + 0.5                # texels back from the stem
        dy = (ctx.p[:, 1] - (ctx.origin[1] + ctx.size[1] / 2)) * 2.0   # texels above / below it
        rz, ry = ctx.size[2] * 2.0, ctx.size[1]                         # radii (texels)
        r = np.hypot(dz / rz, dy / ry)
        phi = np.degrees(np.arctan2(dy / ry, dz / rz))
        rays = np.array([-72.0, -36.0, 0.0, 36.0, 72.0])
        dphi = np.min(np.abs(phi[:, None] - rays[None, :]), axis=1)
        edge = 0.98 - 0.2 * np.clip(dphi / 18.0, 0, 1) ** 1.5           # concave between the rays
        a = ((r <= edge) & (dz > 0)).astype(float)
        rib = np.zeros(ctx.N, bool)
        for f in np.radians(rays):
            u, v = math.cos(f) * rz, math.sin(f) * ry                     # ray direction in texels
            ln = math.hypot(u, v)
            rib |= (np.abs(dz * v / ln - dy * u / ln) < 0.6) & (dz * u + dy * v > 0)
        mem = np.where((r < 0.5)[:, None], ramp[3], ramp[2])
        c = np.where(rib[:, None], ramp[-1], mem)
        c = np.where(((r > edge - 0.1) & ~rib)[:, None], ramp[4], c)
    return c, a, ctx.zeros()


def mat_puff(ctx):
    ix, iy, W, H = px.texel(ctx)
    burn = _burn(ctx)
    lv = px.proxy(ctx, ctx.origin + ctx.size / 2, ctx.size / 2, 0.8) + 0.1
    c = px.quant(ctx, ASH if burn else CREAM, lv)
    dots = ((ix + iy) % 3 == 0) & ((ix - iy) % 3 == 0)
    c = np.where(dots[:, None], EMBER[3] if burn else LAYER[3][6], c)
    if ctx.face == "up":
        mouth = (np.abs(ix - (W - 1) / 2) < 0.6) & (np.abs(iy - (H - 1) / 2) < 0.6)
        c = np.where(mouth[:, None], VOID[1], c)
    return c, ctx.ones(), np.where(dots, 0.45, 0.0)


def mat_puff_rays(ctx):
    lv = px.light(ctx) + 0.1
    burn = _burn(ctx)
    c = px.quant(ctx, ASH if burn else PINK, lv)
    if ctx.face == "up":
        c = np.where(px.border(ctx, 1)[:, None], EMBER[3] if burn else PINK[6], c)
    return c, ctx.ones(), ctx.zeros()


def mat_spore(ctx):
    """Ripe spores: small glowing pearls with a geometric facet."""
    ix, iy, W, H = px.texel(ctx)
    c = px.quant(ctx, GOLD, px.light(ctx, grad=0.0) + 0.3)
    c = np.where(((ix + iy) % 2 == 0)[:, None], PINK[5], c)
    return c, ctx.ones(), np.full(ctx.N, 0.7)


def mat_crystal(ctx):
    lv = px.light(ctx, grad=0.0) + 0.3
    burn = _burn(ctx)
    return px.quant(ctx, EMBER if burn else CYAN, lv), ctx.ones(), np.full(ctx.N, 0.8)


def materials():
    mats = {f"cap{i}": _cap_mat(i) for i in range(len(BANDS))}
    for job in set(MYC_JOB.values()):
        for k in range(SEGS):
            mats[f"hy_{job}{k}"] = _hypha(job, k)
    mats.update({"brim": mat_brim, "thread": mat_thread, "plate": mat_plate, "void": mat_void,
                 "singularity": mat_singularity, "ring": mat_ring, "lid": mat_lid, "gill": mat_gill, "pore": mat_pore,
                 "shell": mat_shell, "volva": mat_volva, "core": mat_core, "hy_tip": mat_hy_tip, "grip": mat_grip,
                 "fan": mat_fan, "puff": mat_puff, "puff_rays": mat_puff_rays, "crystal": mat_crystal, "spore": mat_spore,
                 "tendril_fp": _hypha("m", 1), "accent": mat_accent})
    return mats
