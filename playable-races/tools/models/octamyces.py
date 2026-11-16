"""Race 009 - Octamyces Undecimus, Witness of the Eleventh Rift (v1.5 premium redesign).

"ผู้เฝ้ามองแห่งรอยแยกที่ 11" - a majestic floating witness.  An extradimensional fungus that
watches several realities at once: not a monster with one eye and not malicious, unreadable.

  * a smooth lopsided DOME cap (lathe(), 24 px across, 10.5 px tall, thin bands toward the crown)
    leaning forward over its eye like a hood, its crown pushed to the left; a long luminous
    skirt of lappets hangs from the rim and radiating gill fins glow underneath
  * THE UNDECIMAL EYE seated in a socket of cap tissue on the front of the cap: eleven thin
    polygon rings (3- to 13-sided, ring0 .. ring10) over a deep void with a star pupil, each ring
    a little in front of the one inside it; eight eyelid petals (lid0 .. lid7) grow from the
    socket's lip, stand open as a flower crown and fold shut to blink
  * a thick twisted lattice stalk with a glowing core, on a bulb
  * EIGHT mycelial groups, each shaped for its job (myc<g>_0..2), thick at the root and tapering
    to fine glowing tips in S-curves that trail outward and back like a jellyfish's:
    0/1 manipulators that hold your items at the vanilla hand points, 2/3 propulsion fins,
    4 a sensor, 5 a spore emitter (a lantern pod), 6 a stabiliser curtain (a trailing ribbon),
    7 a resonance antenna on the crown
  * it floats: nothing comes within 4 px of the ground

Variants: base (Witnessing) | sporeveil | record | offset | frame | unstable (on fire).
"""
from __future__ import annotations

import math

import numpy as np

from kit.geo import Model, rot_matrix
from kit import pixel as px
from models.common import (accents, feather_fan, fp_sleeves, frame_rot, humanoid, lathe, mat_accent, q, rays, segment,
                           spline, sweep)

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
FLOAT_C = (0.0, 19.0, 0.5)           # the body's centre: hover bob, lean and roll pivot about here
CAP_J = (0.0, 25.75, 0.5)            # cap / stalk joint (the cap turns and tilts about it)
RIM_Y = 26.25
CAP_C = (0.0, RIM_Y, 0.5)            # lathe centre of the dome (rim level)
CAP_H = 10.75
# bell-dome profile (height above the rim, radius): thinner bands toward the crown so the steps
# shrink where the camera looks down on them; heights on 0.25 steps so the bands meet exactly
CAP_PROFILE = [(0.0, 12.0), (3.0, 11.5), (4.75, 10.6), (6.0, 9.5), (7.0, 8.4), (7.75, 7.4), (8.5, 6.2), (9.25, 4.9),
               (9.75, 3.8), (10.25, 2.5), (10.75, 1.0)]
CAP_SKEW = (1.5, -4.0)               # the crown leans forward over the eye like a hood, swelling to the left (+X)
CAP_SQUASH = (1.0, 0.95)
BAND_BONE = ["cap"] * 4 + ["cap_mid"] * 3 + ["cap_upper"] * 3

EYE_C = (0.0, 28.0, -11.75)          # centre of the void (the eye bone's pivot, before its tilt): under the hood
EYE_TILT = 20.0                      # the eye looks forward and a little up
RING_SIDES = tuple(range(3, 14))     # ring0 = triangle (innermost) ... ring10 = thirteen-gon
RINGS = len(RING_SIDES)
RING_A0, RING_DA = 0.8, 0.45         # apothem of ring0 and the even step outward
RING_T = 0.25                        # bar thickness: thin luminous lines
RING_D = 0.25                        # bar depth
RING_DZ = 0.14                       # each ring sits a little in front of the one inside it (a shallow funnel)
LIP_IN = 5.65                        # the socket: an octagonal lip of cap tissue round the outermost ring
LIP_T = (1.0, 1.75, 2.0, 2.25)       # its thickness, top .. bottom: a fine rim above, a full cheek below
LIP_DEPTH = (2.5, 8.0)               # each lip segment reaches back until it is sunk in the cap (min, max)
LIDS = 8
LID_W, LID_LEN = 3.75, 4.5           # eyelid petals: widest across, length from the hinge
LID_OPEN = -124.0                    # rest fold: open, cupped forward round the eye like a flower
LID_PHASE = 22.5                     # petals centred on the lip's eight segments
STALK_TOP, STALK_BOT = 25.75, 13.25
MYC = 8

# ---------------------------------------------------------------------------- derived


def ring_apothem(k: int) -> float:
    return RING_A0 + RING_DA * k


def ring_z(k: int) -> float:
    return EYE_C[2] - 0.35 - RING_DZ * k


def ring_circum(k: int) -> float:
    return ring_apothem(k) / math.cos(math.pi / RING_SIDES[k])


LID_A = LIP_IN + 0.15                                  # hinge circle of the petals (the lip's inner front edge)
LID_Z = ring_z(RINGS - 1) - 0.2                        # hinge plane, just in front of the outermost ring
VOID_H = 5.6                                           # half-side of the void square (its corners hide in the lip)


def _norm_deg(a: float) -> float:
    a = (a + 180.0) % 360.0 - 180.0
    return 180.0 if abs(a + 180.0) < 1e-9 else round(a, 4) + 0.0


def _rot(a: float):
    a = _norm_deg(a)
    return None if abs(a) < 1e-6 else a


def _cube_rot(r):
    """Cube rotation with every angle inside (-180, 180] (rounded, no -0.0)."""
    return tuple(_norm_deg(v) for v in r)


def plate(m: Model, bone: str, top, down, normal, w: float, ln: float, thick: float, mat: str, **kw):
    """A thin plate hanging from `top` (centre of its top edge) along `down`, facing `normal`:
    w across (local X), thick through (local Y), ln along (local Z)."""
    o = np.asarray(top, float)
    return m.cube(bone, (o[0] - w / 2, o[1] - thick / 2, o[2]), (w, thick, ln), mat, pivot=tuple(o),
                  rot=_cube_rot(frame_rot(down, normal)), **kw)


def cap_band(i: int):
    """(y0, y1, centre, radius, sides) of dome band i (absolute heights)."""
    (y0, r0), (y1, r1) = CAP_PROFILE[i], CAP_PROFILE[i + 1]
    g = ((y0 + y1) / 2) / CAP_H
    c = (CAP_C[0] + CAP_SKEW[0] * g, CAP_C[1], CAP_C[2] + CAP_SKEW[1] * g)
    r = (r0 + r1) / 2
    return RIM_Y + y0, RIM_Y + y1, c, r, (12 if r > 5.6 else 8)


def in_dome(p, margin: float = 0.0) -> bool:
    """Is the rest-pose point p inside the dome's bands (by at least `margin`)?"""
    x, y, z = p
    for i in range(len(CAP_PROFILE) - 1):
        y0, y1, c, r, sides = cap_band(i)
        if y0 + margin <= y <= y1 - margin + (0.0 if i < len(CAP_PROFILE) - 2 else 0.0):
            apo = r * math.cos(math.pi / sides) - margin
            if apo > 0 and ((x - c[0]) / (apo * CAP_SQUASH[0])) ** 2 + ((z - c[2]) / (apo * CAP_SQUASH[1])) ** 2 <= 1.0:
                return True
    return False


def rim_dist(theta: float) -> float:
    """Distance from the rim band's centre to its side facing direction theta (degrees from the
    front toward the creature's right), as lathe() builds it."""
    _, _, _, r, sides = cap_band(0)
    apo = r * math.cos(math.pi / sides)
    a = math.radians(theta)
    sq = math.hypot(CAP_SQUASH[0] * math.sin(a), CAP_SQUASH[1] * math.cos(a))
    return q(2 * apo * sq, 0.25) / 2


def heading(theta: float) -> np.ndarray:
    """Horizontal unit vector theta degrees from the front (-Z) toward the creature's right (-X)."""
    a = math.radians(theta)
    return np.array([-math.sin(a), 0.0, -math.cos(a)])


def eye_to_world(p) -> np.ndarray:
    """A point given in the eye's untilted frame, as it sits in the rest pose."""
    c = np.asarray(EYE_C, float)
    return rot_matrix((-EYE_TILT, 0.0, 0.0)) @ (np.asarray(p, float) - c) + c


# ============================================================================= build

def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=256)
    humanoid(m)
    # head chain: head_g and `steady` cancel the player's look exactly (x on one bone, y on the
    # next); `float_h` mirrors the body's hover so the cap stays on its stalk; the cap then turns
    # by a fraction of the look about the stalk joint, the iris by more, inside its socket
    m.bone("steady", "head_g", HEAD)
    m.bone("float_h", "steady", FLOAT_C)
    m.bone("float", "torso_g", FLOAT_C)
    m.bone("cap", "float_h", CAP_J)
    _dome(m)
    _frill(m)
    _gills(m)
    _eye(m)
    _stalk(m)
    _mycelia(m)
    fp_sleeves(m, "tendril_fp", width=4.5)
    accents(m, [
        ("c", "collar", "stalk", (0.0, 24.75, 0.5), (8.0, 0.75, 8.0)),
        ("l", "fins", "float", (0.0, 22.5, 3.0), (5.0, 1.5, 0.75)),
        ("f", "tips", "myc6_2", (0.0, 4.75, 10.5), (3.0, 0.5, 1.5)),
    ])
    for b in m.bones.values():               # every cube angle inside (-180, 180] (the same rotations)
        for c in b.cubes:
            if c.rot is not None:
                c.rot = _cube_rot(c.rot)
    m.pack()
    return m


# ----------------------------------------------------------------------------- the dome cap

def _dome(m: Model) -> None:
    """The cap: a lathe() dome, one band per call so each band carries its own faces and bone.
    The upper bands ride cap_mid / cap_upper (Hyphal Offset slides them off the lower ones)."""
    lo, mid = cap_band(BAND_BONE.index("cap_mid")), cap_band(BAND_BONE.index("cap_upper"))
    m.bone("cap_mid", "cap", (lo[2][0], lo[0], lo[2][2]))
    m.bone("cap_upper", "cap_mid", (mid[2][0], mid[0], mid[2][2]))
    m.bones["cap_mid"].variant["offset"] = ((1.75, 0.5, 1.5), (0.0, 14.0, -3.0))
    m.bones["cap_upper"].variant["offset"] = ((-2.5, 1.0, 1.0), (0.0, -26.0, 4.0))
    for i in range(len(CAP_PROFILE) - 1):
        y0, y1, c, r, sides = cap_band(i)
        faces = {"north", "south", "up"} | ({"down"} if i == 0 else set())
        lathe(m, BAND_BONE[i], c, [(y0 - RIM_Y, r), (y1 - RIM_Y, r)], "cap", sides=sides, squash=CAP_SQUASH,
              faces=faces)
    top = cap_band(len(CAP_PROFILE) - 2)
    m.bones["cap_upper"].locators["cap_top"] = (top[2][0], RIM_Y + CAP_H + 0.5, top[2][2])
    m.bones["cap"].locators["gills"] = (0.0, 23.5, 0.5)


FRILL_Q = {"frill_f": (11, 1), "frill_r": (2, 3, 4), "frill_b": (5, 6, 7), "frill_l": (8, 9, 10)}
FRILL_LEN = (4.25, 5.0)              # alternating lappets: a long luminous skirt with a wavy hem
FRILL_FLARE = (10.0, 21.0)


def _frill(m: Model) -> None:
    """A luminous skirt hanging from the rim: lappets on the sides of the rim band (the front one
    gives way to the eye's socket), flared outward at alternating angles, in four quadrants
    that ripple."""
    _, _, c, r, sides = cap_band(0)
    c = np.asarray(c, float)
    edge = 2 * r * math.sin(math.pi / sides)
    for name, ks in FRILL_Q.items():
        th0 = 30.0 * {"frill_f": 0, "frill_r": 3, "frill_b": 6, "frill_l": 9}[name]
        piv = c + heading(th0) * rim_dist(th0) + np.array([0.0, 0.25, 0.0])
        b = m.bone(name, "cap", tuple(piv))
        for k in ks:
            th = 30.0 * k
            n = heading(th)
            f = math.radians(FRILL_FLARE[k % 2])
            down = np.array([0.0, -1.0, 0.0]) * math.cos(f) + n * math.sin(f)
            nrm = n * math.cos(f) + np.array([0.0, 1.0, 0.0]) * math.sin(f)
            a = math.radians(th)
            sq = math.hypot(CAP_SQUASH[0] * math.sin(a), CAP_SQUASH[1] * math.cos(a))
            top = c + n * (rim_dist(th) + 0.15) + np.array([0.0, 0.75, 0.0])
            plate(m, b.name, top, down, nrm, q(edge * sq + 0.5), FRILL_LEN[k % 2] + 0.75, 0.25, "frill")
    # (+rx swings a hanging part back, +rz swings a part on the creature's right outward)
    for name, rot in (("frill_f", (16.0, 0, 0)), ("frill_b", (-16.0, 0, 0)), ("frill_r", (0, 0, -16.0)),
                      ("frill_l", (0, 0, 16.0))):
        m.bones[name].variant["unstable"] = ((0.0, -0.25, 0.0), rot)                 # scorched: the skirt sags limp
    for name, rot in (("frill_f", (-22.0, 0, 0)), ("frill_b", (22.0, 0, 0)), ("frill_r", (0, 0, 22.0)),
                      ("frill_l", (0, 0, -22.0))):
        m.bones[name].variant["sporeveil"] = ((0.0, 0.0, 0.0), rot)                  # the skirt flares open


def _gills(m: Model) -> None:
    """Radiating glowing gill fins under the cap, and (Parallax Sporeveil) ripe spore pearls."""
    g = m.bone("gill_ring", "cap", (0.0, 25.5, 0.5))
    rays(m, g.name, (0.25, 25.25, 0.25), 8, 3.75, 11.0, 0.5, "gill", plane="flat", thick=2.0, phase=22.5)
    for k in range(6):
        a = math.radians(30.0 + 60.0 * k)
        rr = 6.0 + 1.75 * (k % 2)
        m.box(g.name, (0.25 + rr * math.sin(a), 23.25 - 0.75 * (k % 2), 0.25 + rr * math.cos(a)), (1.0, 1.0, 1.0),
              "spore", only={"sporeveil"})


# ----------------------------------------------------------------------------- the undecimal eye

def _lip_t(th: float) -> float:
    return LIP_T[min(range(4), key=lambda i: abs(abs(_norm_deg(th)) - (22.5 + 45.0 * i)))]


def _lip_depth(th: float) -> float:
    """Mirrored segments share a depth (the deeper of the two), so the socket is symmetric."""
    return max(_lip_depth1(th), _lip_depth1(-th))


def _lip_depth1(th: float) -> float:
    """How deep the lip segment at angle th (0 = top) reaches back: until its outer back corners
    are sunk in the cap (segments that cannot reach it keep the minimum)."""
    cx, cy, cz = EYE_C
    lo = LIP_IN + _lip_t(th)
    a = math.radians(th)
    d = LIP_DEPTH[0]
    while d < LIP_DEPTH[1]:
        corners = []
        for t in (-0.45, 0.45):                     # the two outer back corners of the segment
            u = lo * math.tan(math.pi / 8) * t * 2
            x, y = u * math.cos(a) + lo * math.sin(a), -u * math.sin(a) + lo * math.cos(a)
            corners.append(eye_to_world((cx + x, cy + y, LID_Z + d)))
        if all(in_dome(c, 0.4) for c in corners):
            return q(d + 0.5, 0.25)
        d += 0.25
    return LIP_DEPTH[0]


def _eye(m: Model) -> None:
    cx, cy, cz = EYE_C
    eye = m.bone("eye", "cap", EYE_C, (-EYE_TILT, 0.0, 0.0))
    eye.locators["eye_c"] = (cx, cy, ring_z(RINGS - 1) - 0.5)
    # the socket: eight thick segments of cap tissue round the outermost ring, sunk into the cap;
    # the eyelid petals grow from its inner front edge
    for j in range(8):
        th = _norm_deg(LID_PHASE + 45.0 * j)
        t = _lip_t(th)
        seg = q(2 * (LIP_IN + t) * math.tan(math.pi / 8) + 0.25, 0.25)
        m.cube(eye.name, (cx - seg / 2, cy + LIP_IN, LID_Z), (seg, t, _lip_depth(th)), "lip", pivot=(cx, cy, cz),
               rot=(0, 0, th) if _rot(th) else None)
    # the iris tilts about the middle of its ring funnel (so a glance never pushes a ring into the lip)
    iris = m.bone("iris", eye.name, (cx, cy, ring_z(RINGS // 2)))
    # the void at the back of the socket (never turned or scaled: its corners hide in the lip) and
    # the star pupil on its own bone, free to drift toward the look, turn and pulse
    pu = m.bone("pupil", iris.name, (cx, cy, cz))
    m.cube(pu.name, (cx - VOID_H, cy - VOID_H, cz), (2 * VOID_H, 2 * VOID_H, 0.25), "void", faces={"north"})
    star = m.bone("star", pu.name, (cx, cy, cz - 0.07))
    m.cube(star.name, (cx - 1.25, cy - 1.25, cz - 0.12), (2.5, 2.5, 0.1), "star", ppu=4.0, faces={"north"})
    # eleven rings, evenly spaced, the inner ones deeper
    for k, n in enumerate(RING_SIDES):
        z = ring_z(k)
        r = m.bone(f"ring{k}", iris.name, (cx, cy, z))
        a = ring_apothem(k)
        ln = q(2 * (a + RING_T / 2) * math.tan(math.pi / n) + 0.1, 0.25)
        off = 180.0 / n                              # at rest every polygon has a vertex at the top (aligned)
        for j in range(n):
            ang = _rot(off + 360.0 * j / n)
            m.cube(r.name, (cx - ln / 2, cy + a - RING_T / 2, z - RING_D / 2), (ln, RING_T, RING_D), f"ring{k}",
                   pivot=(cx, cy, z), rot=(0, 0, ang) if ang else None, ppu=4.0)
    # eight eyelid petals: open they stand as a crown cupped forward; a blink folds them shut
    # (rx -> 0) into a flat octagon with only the star showing
    for j in range(LIDS):
        th = _norm_deg(LID_PHASE + 45.0 * j)
        hx = cx + LID_A * math.sin(math.radians(th))
        hy = cy + LID_A * math.cos(math.radians(th))
        lid = m.bone(f"lid{j}", eye.name, (hx, hy, LID_Z), (LID_OPEN, 0.0, th))
        lid.variant["record"] = ((0.0, 0.0, 0.0), (LID_OPEN + 22.0, 0.0, th))      # the crown narrows to focus
        lid.variant["frame"] = ((0.0, 0.0, 0.0), (LID_OPEN - 30.0, 0.0, th))       # wide open for the telescope
        lid.variant["sporeveil"] = ((0.0, 0.0, 0.0), (LID_OPEN - 18.0, 0.0, th))
        lid.variant["unstable"] = ((0.0, 0.0, 0.0), (LID_OPEN + 30.0, 0.0, th))    # wilting
        m.cube(lid.name, (hx - LID_W / 2, hy - LID_LEN, LID_Z - 0.125), (LID_W, LID_LEN, 0.25), "lid", cutout=True,
               faces={"north", "south"}, ppu=4.0)


# ----------------------------------------------------------------------------- the stalk

def _twisted(m: Model, bone: str, y0: float, y1: float, r: float, twist: float, mat: str, **kw):
    """One band of an eight-sided prism (four crossing strips) turned by `twist` degrees."""
    apo = r * math.cos(math.pi / 8)
    edge = q(2 * r * math.sin(math.pi / 8) + 0.25, 0.25)
    for k in range(4):
        ang = _rot(45.0 * k + twist)
        e = 0.02 * k
        m.cube(bone, (-edge / 2, y0 - e, 0.5 - q(2 * apo, 0.25) / 2), (edge, y1 - y0 + 2 * e, q(2 * apo, 0.25)), mat,
               pivot=(0.0, y0, 0.5), rot=(0, ang, 0) if ang else None, **kw)


STALK_BANDS = ((21.0, STALK_TOP, 3.5, 0.0), (17.0, 21.0, 3.1, 15.0), (STALK_BOT, 17.0, 3.4, 30.0))
BULB = (10.0, [(0.0, 2.9), (1.5, 4.9), (3.25, 4.1)])     # base height and lathe profile of the bulb


def _stalk(m: Model) -> None:
    st = m.bone("stalk", "float", (0.0, STALK_TOP, 0.5))
    core = m.bone("core", st.name, (0.0, 19.5, 0.5))
    m.cube(core.name, (-1.375, STALK_BOT, -0.875), (2.75, STALK_TOP - STALK_BOT - 0.25, 2.75), "core",
           pivot=(0.0, 19.5, 0.5), rot=(0, 45.0, 0), faces={"north", "south", "east", "west"})
    for y0, y1, r, tw in STALK_BANDS:
        _twisted(m, st.name, y0, y1, r, tw, "lattice", cutout=True, faces={"north", "south"})
    y, prof = BULB
    lathe(m, st.name, (0.0, y, 0.5), prof, "volva", sides=8, faces={"north", "south", "up", "down"})
    st.locators["base_c"] = (0.0, y - 0.5, 0.5)


# ----------------------------------------------------------------------------- the eight mycelial groups

# control points (Catmull-Rom through them); every group a chain of three bones myc<g>_0..2,
# thick at the root, tapering to a fine glowing tip, curving outward and back
MYC_PTS = {
    # 0/1 manipulators: out from under the cap, back and down in an S, then in to the vanilla hand point
    0: [(-4.25, 25.0, 0.75), (-7.25, 22.25, 2.25), (-8.75, 18.0, 1.75), (-7.75, 14.0, 0.25), (-6.0, 11.25, -0.75)],
    # 2/3 propulsion fins: from the back of the stalk, sweeping far back and out
    2: [(-2.75, 22.5, 2.5), (-5.5, 21.0, 5.5), (-8.5, 18.25, 7.75), (-9.75, 14.5, 10.25)],
    # 4 sensor (front-left): reaches forward and down, its tip curling up
    4: [(2.5, 23.0, -2.25), (5.0, 20.25, -5.25), (5.75, 16.75, -8.0), (4.5, 14.75, -10.75)],
    # 5 spore emitter (front-right): carries a lantern pod
    5: [(-2.5, 21.25, -2.25), (-4.75, 18.75, -4.5), (-5.25, 16.0, -6.25), (-4.5, 14.5, -7.25)],
    # 6 stabiliser curtain: a wide ribbon trailing from the bulb, down and far back in an S
    6: [(0.0, 10.25, 2.25), (0.5, 7.5, 4.0), (-0.5, 5.75, 6.75), (0.5, 5.0, 9.5), (-0.25, 4.75, 12.0)],
    # 7 resonance antenna: rises from the crown and leans back
    7: [(2.75, 36.25, 0.25), (3.75, 38.25, 1.5), (3.5, 39.75, 3.25), (4.25, 40.5, 5.0)],
}
MYC_PTS[1] = [(-x, y, z) for x, y, z in MYC_PTS[0]]
MYC_PTS[3] = [(-x, y, z) for x, y, z in MYC_PTS[2]]
MYC_PARENT = {0: "r_arm_g", 1: "l_arm_g", 2: "stalk", 3: "stalk", 4: "stalk", 5: "stalk", 6: "stalk", 7: "cap_upper"}
MYC_W = {0: (2.0, 0.5), 1: (2.0, 0.5), 2: (2.0, 0.5), 3: (2.0, 0.5), 4: (1.5, 0.5), 5: (1.5, 1.0), 7: (1.0, 0.5)}
MYC_JOB = {0: "m", 1: "m", 2: "f", 3: "f", 4: "s", 5: "p", 6: "b", 7: "a"}
RIBBON_W = (4.0, 1.25)                   # the curtain narrows toward its tip
SPREAD = {2: (-12.0, -22.0, 18.0), 3: (-12.0, 22.0, -18.0), 4: (-20.0, 18.0, -8.0), 5: (-14.0, -14.0, 14.0),
          6: (24.0, 0.0, 0.0), 7: (-14.0, 0.0, -12.0)}            # Hyphal Offset: the mycelia stand out like fins
DROOP = {2: (18.0, 0.0, -8.0), 3: (18.0, 0.0, 8.0), 4: (22.0, 0.0, 0.0), 5: (10.0, 0.0, 8.0), 6: (-6.0, 0.0, 0.0),
         7: (-30.0, 0.0, 8.0)}                                        # on fire: they hang limp


def myc_chain(g: int):
    return [f"myc{g}_{k}" for k in range(3)]


def _mycelia(m: Model) -> None:
    for g in range(MYC):
        if g == 6:
            _curtain(m)
        else:
            pts = MYC_PTS[g]
            spans = (len(pts) - 1) * 2
            per = 3 if spans == 8 else 2
            w0, w1 = MYC_W[g]
            sweep(m, MYC_PARENT[g], f"myc{g}_", pts, w0, w1, f"hy_{MYC_JOB[g]}", n=2, per_bone=per, power=0.8)
        root = m.bones[f"myc{g}_0"]
        if g in SPREAD:
            root.variant["offset"] = ((0.0, 0.0, 0.0), SPREAD[g])
        if g in DROOP:
            root.variant["unstable"] = ((0.0, 0.0, 0.0), DROOP[g])
    _tips(m)


def _curtain(m: Model) -> None:
    """The stabiliser: a wide ribbon of four plates following an S down and back from the bulb."""
    pts = [np.asarray(p, float) for p in MYC_PTS[6]]
    par = MYC_PARENT[6]
    bones = []
    for k in range(3):
        b = m.bone(f"myc6_{k}", par, tuple(pts[k]))
        bones.append(b.name)
        par = b.name
    sp = spline(pts, 2)                                       # eight plates along the smooth curve
    for k in range(len(sp) - 1):
        a, e = sp[k], sp[k + 1]
        d = e - a
        nrm = np.cross(d, np.array([1.0, 0.0, 0.0]))         # the ribbon's face looks up and back
        if nrm[1] < 0:
            nrm = -nrm
        w = q(RIBBON_W[0] + (RIBBON_W[1] - RIBBON_W[0]) * k / (len(sp) - 2), 0.25)
        plate(m, bones[min(k // 3, 2)], a, d, nrm, w, q(float(np.linalg.norm(d)) + 0.35, 0.25), 0.25, "ribbon")


def _tips(m: Model) -> None:
    for g, side, p in ((0, -1, "r"), (1, 1, "l")):            # a curled grip round the held item
        e = np.asarray(MYC_PTS[g][-1], float)
        tip = f"myc{g}_2"
        segment(m, tip, e, e + np.array([side * 0.75, -1.0, -1.0]), 0.5, 0.5, "grip", overlap=0.0)
        m.bones[tip].locators[f"{p}_grip"] = tuple(e + np.array([0.0, -1.0, -0.25]))
    for g, side in ((2, -1), (3, 1)):                        # fin membranes trailing from the fin's middle joint
        o = MYC_PTS[g][1]
        feather_fan(m, f"myc{g}_1", f"fin{g}_", o, 3, [6.0, 7.5, 6.5], [3.0, 3.0, 2.5], "fan", spread=62.0,
                    center=side * 118.0, plane="back", lift=34.0, bones=False, cutout=True, faces={"up", "down"})
    e = np.asarray(MYC_PTS[4][-1], float)                     # the sensor's glowing bulb and a feeler
    m.box("myc4_2", tuple(e + np.array([0.0, 0.25, -0.5])), (1.25, 1.25, 1.25), "bulb", rot=(45.0, 0.0, 45.0),
          pivot=tuple(e + np.array([0.0, 0.25, -0.5])))
    segment(m, "myc4_2", e, e + np.array([0.5, 1.75, -1.5]), 0.25, 0.25, "feeler", overlap=0.0)
    m.bones["myc4_2"].locators["sensor"] = tuple(e + np.array([0.0, 0.5, -1.25]))
    pod = np.asarray(MYC_PTS[5][-1], float) + np.array([0.0, -1.75, 0.0])    # the lantern pod
    for s in ((3.0, 2.5, 3.0), (2.5, 3.75, 2.5), (3.5, 1.75, 3.5)):
        m.box("myc5_2", tuple(pod), s, "pod")
    m.bones["myc5_2"].locators["spores"] = tuple(pod + np.array([0.0, -2.25, 0.0]))
    e = np.asarray(MYC_PTS[7][-1], float) + np.array([0.0, 0.9, 0.25])      # a floating triangle at the antenna's tip
    for j in range(3):
        ang = _rot(60.0 + 120.0 * j)
        m.cube("myc7_2", (e[0] - 0.75, e[1] + 0.35, e[2] - 0.125), (1.5, 0.25, 0.25), "crystal", pivot=tuple(e),
               rot=(0, 0, ang) if ang else None)
    m.bones["myc7_2"].locators["antenna"] = tuple(e)


# ============================================================================= materials
#
# Marketplace-premium surface: every colour is a smooth, hue-shifted ramp computed from the texel's
# rest-pose world position (so gradients run continuously across the dome's bands and across the
# strips of every lathe), light comes from the smooth form each part approximates, and glow is a
# designed pattern (spore spots, ring lines, the skirt's rim and hem, veins and tips), never noise.

def _P(ctx, k):
    return ctx.params.get(k, 0.0)


def _burn(ctx) -> bool:
    return _P(ctx, "burn") > 0.5


def _wp(ctx):
    return ctx.wp if ctx.wp is not None else ctx.p


def _wn(ctx):
    return ctx.wn if ctx.wn is not None else ctx.n


def _mix(a, b, t):
    """Blend colour arrays/rows a -> b by t (scalar or (N,))."""
    t = np.asarray(t, float)
    if t.ndim == 1:
        t = t[:, None]
    return np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t


def _ss(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# palettes, dark -> light, hue-shifted (shadows cool, lights warm)
CAP_RAMP = px.pal("#0d0830", "#170f4a", "#22156a", "#2f1d8a", "#4227aa", "#5733c4", "#6d42d6", "#8457e3", "#9b6eea",
                  "#ae86ef")
PEARL = px.col("#f6efff")
IRIS_MAGENTA = px.col("#d04fd6")
IRIS_BLUE = px.col("#3a6cf0")
GOLD = px.pal("#6a3a12", "#b8701e", "#eaa83c", "#ffd97e", "#fff3c8")
MINT = px.pal("#06302f", "#0c4f4b", "#14756c", "#22a08c", "#3fcaa9", "#7deac6", "#c2fbe6", "#f0fff9")
CYAN_TIP = px.col("#8ff3ff")
PINK_TIP = px.col("#ff8fd6")
VOID = px.pal("#030208", "#07051a", "#100a30", "#1d1250", "#2c1a6c")
PALE = px.pal("#3b2f6e", "#5b4a96", "#8270bd", "#a999db", "#cdc2f0", "#e9e3fb", "#f8f5ff")
CREAM = px.pal("#4c3242", "#7a5664", "#a8848a", "#d1b6b0", "#efe0d6", "#fff8ef")
ASH = px.pal("#09070a", "#140f13", "#211a1f", "#30262c", "#41363b", "#55494d", "#6b5f60", "#857876")
EMBER = px.pal("#2a0904", "#5e1606", "#a22e0a", "#e05a14", "#ff9a3c", "#ffd58a")
# the iris: ONE iridescent gradient, mint at the centre through cyan and violet to magenta outside
RING_HEX = ["#8cffcf", "#6ff9e0", "#5aeaf2", "#55cdfd", "#5ea9ff", "#6f88ff", "#8470ff", "#9a5ff6", "#b355eb",
            "#d050d7", "#ec56c2"]
RING_EMBER = ["#ffe0a0", "#ffd088", "#ffbf70", "#ffaa58", "#ff9446", "#f87e38", "#ec682e", "#dc5426", "#c8421f",
              "#b2341a", "#9a2814"]
KEY = np.array([-0.35, 0.8, -0.45]) / np.linalg.norm([-0.35, 0.8, -0.45])     # the key light (front-left-top)


def _dome_proxy():
    """(centre, radii) of the ellipsoid the dome's bands approximate (its crown leans with the skew)."""
    return ((CAP_C[0] + CAP_SKEW[0] * 0.4, RIM_Y - 0.75, CAP_C[2] + CAP_SKEW[1] * 0.4), (12.0, 11.5, 11.6))


def engine_level(n) -> np.ndarray:
    """The vertical part of Minecraft entity lighting (top 1.0, sides ~0.72, bottom ~0.45) for normals n."""
    ny = np.atleast_2d(n)[:, 1]
    return np.where(ny >= 0, 0.72 + 0.28 * ny, 0.72 + 0.27 * ny)


def smooth_normals(ctx, center, radii) -> np.ndarray:
    d = (_wp(ctx) - np.asarray(center, float)) / np.asarray(radii, float) ** 2
    return d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)


def face_comp(ctx, center, radii, gain: float = 1.0) -> np.ndarray:
    """Level offset that cancels the engine's per-face light on a stacked smooth form: risers
    near a crown are lifted, the tops of low terraces lowered, so the bands read as one surface."""
    return gain * (engine_level(smooth_normals(ctx, center, radii)) - engine_level(_wn(ctx))[0])


_L = np.array([-0.45, 0.75, -0.55]) / np.linalg.norm([-0.45, 0.75, -0.55])


def engine_light(n) -> np.ndarray:
    """Entity light for normals n: the mean of Bedrock's entity shading (0.45 ambient + 0.55 from
    above, -0.1 on X faces, +0.1 on Z faces) and the preview renderer's key light, so the
    correction holds in the game and in every preview."""
    n = np.atleast_2d(n)
    bed = 0.45 + 0.55 * (1 + n[:, 1]) / 2 - 0.1 * n[:, 0] ** 2 + 0.1 * n[:, 2] ** 2
    ren = 0.52 + 0.55 * np.clip(n @ _L, 0, None) + 0.08 * np.clip(n[:, 1], 0, None)
    return 0.5 * (bed + ren)


def light_ratio(ctx, center, radii, lo: float = 0.7, hi: float = 1.6) -> np.ndarray:
    """Multiply a stacked form's colour by this so each band face shows the light its smooth
    surface would get (hue kept, unlike a level shift)."""
    n = smooth_normals(ctx, center, radii)
    return np.clip(engine_light(n) / engine_light(_wn(ctx))[0], lo, hi)


def _band_point(i: int, theta: float, up: float = 0.5) -> np.ndarray:
    """A point on the side of dome band i facing direction theta, `up` of the way up the band."""
    y0, y1, c, r, sides = cap_band(i)
    a = math.radians(theta)
    sq = math.hypot(CAP_SQUASH[0] * math.sin(a), CAP_SQUASH[1] * math.cos(a))
    d = r * math.cos(math.pi / sides) * sq
    return np.array([c[0] - math.sin(a) * d, y0 + (y1 - y0) * up, c[2] - math.cos(a) * d])


SPORE = px.pal("#6e3c2a", "#b97a4c", "#e7b47c", "#f8d9a8", "#fff3e0")      # warm pearl-gold, not lemon


def _crown_c():
    i = len(CAP_PROFILE) - 2
    return np.array(cap_band(i)[2], float)


def _exposed_ledge(x: float, z: float):
    """Height of the dome's band ledge exposed at plan position (x, z), or None outside the rim."""
    top = None
    for i in range(len(CAP_PROFILE) - 1):
        y0, y1, c, r, sides = cap_band(i)
        apo = r * math.cos(math.pi / sides) - 0.1
        if ((x - c[0]) / (apo * CAP_SQUASH[0])) ** 2 + ((z - c[2]) / (apo * CAP_SQUASH[1])) ** 2 <= 1.0:
            top = y1
    return top


def _spore_spots():
    """Spore spots in a golden-angle (Vogel) spiral seen from above the crown: they lie in drifting
    spiral arms that follow the dome, dense at the crown and thinning toward the rim (where the
    ledges grow steep and narrow); mostly 1-2 texels, a few 3, brightness drifting along the arms.
    A sparse second scatter sits on the taller lower bands so the sides are not bare.
    Returns (centres, radii, brightness)."""
    cc = _crown_c()
    out, rad, bri = [], [], []
    for i in range(1, 190):
        rho = 0.78 * math.sqrt(i)
        th = math.radians(i * 137.508)
        x, z = cc[0] + rho * math.sin(th), cc[2] + rho * math.cos(th)
        if z < cc[2] - 4.5 and abs(x - cc[0]) < 7.5:      # the eye's socket fills the front
            continue
        y = _exposed_ledge(x, z)
        if y is None:
            continue
        arm = (0.5 + 0.5 * math.cos(2 * math.pi * (i % 13) / 13 + rho * 0.55)) * (0.5 + 0.5 * math.cos(2 * math.pi * (i % 8) / 8))
        if arm < 0.18 and i % 3:                          # gaps between the drifts
            continue
        thin = 1.0 - 0.55 * min(1.0, rho / 11.0)
        big = (i % 17 == 0)
        rad.append((0.62 if big else 0.28 + 0.17 * arm) * (0.85 + 0.3 * thin))
        bri.append(0.45 + 0.55 * arm * thin + (0.25 if big else 0.0))
        out.append((x, y + 0.02, z))
    k = 0
    for i, per in ((1, 6), (2, 5), (3, 4)):               # the sparse scatter on the side bands
        for j in range(per):
            th = (k * 137.508 + 101.0) % 360.0 - 180.0
            jit = (k * 0.7548776662) % 1.0
            k += 1
            if abs(th) < 70.0:
                continue
            out.append(tuple(_band_point(i, th, 0.2 + 0.6 * jit)))
            rad.append(0.3 + 0.12 * ((k * 0.618034) % 1.0))
            bri.append(0.5 + 0.3 * jit)
    return np.array(out), np.array(rad), np.array(bri)


SPOTS = _spore_spots()


def _spots(ctx):
    """(glow 0..1, colour weight 0..1) of the spore spots at this texel: a soft core and falloff."""
    p = _wp(ctx)
    g = np.zeros(ctx.N)
    for c, r, b in zip(*SPOTS):
        d = np.linalg.norm(p - c, axis=1) / r
        g = np.maximum(g, b * (1 - _ss(0.35, 1.45, d)))
    return g


def _cap_colour(ctx, extra_lv=0.0):
    """The dome's tissue at each texel: (rgb, level, h, smooth normal)."""
    p = _wp(ctx)
    c0, r0 = _dome_proxy()
    n = smooth_normals(ctx, c0, r0)
    h = np.clip((p[:, 1] - RIM_Y) / CAP_H, 0, 1)
    lv = px.proxy(ctx, c0, r0, 1.0) + 0.14 * h - 0.06 + extra_lv
    # faint radial striations near the margin cross the bands (a striate cap margin)
    az = np.degrees(np.arctan2(p[:, 0] - c0[0], p[:, 2] - c0[2]))
    stria = (np.abs(((az + 7.5) % 15.0) - 7.5) < 1.1) & (h < 0.55)
    lv = lv - 0.05 * stria * (1 - h / 0.55)
    ratio = light_ratio(ctx, c0, r0)[:, None]
    if _burn(ctx):
        return np.clip(px.smooth_ramp(ASH, lv * 0.95) * ratio, 0, 1), lv, h, n
    rgb = px.smooth_ramp(CAP_RAMP, lv)
    # iridescence: the hue drifts round the cap - magenta on its swollen left, blue on its right
    side = 0.5 + 0.5 * np.clip(n[:, 0] * 1.4, -1, 1)
    rgb = _mix(rgb, rgb * 0.55 + IRIS_MAGENTA * 0.45, 0.30 * side * (0.4 + 0.6 * h))
    rgb = _mix(rgb, rgb * 0.55 + IRIS_BLUE * 0.45, 0.24 * (1 - side) * (1 - 0.5 * h))
    # pearl: a soft sheen and a tight highlight where the smooth form faces the key light
    nk = np.clip(n @ KEY, 0, 1)
    rgb = _mix(rgb, px.col("#c9b3ff"), 0.16 * nk ** 3)
    rgb = _mix(rgb, PEARL, 0.55 * nk ** 22)
    return np.clip(rgb * ratio, 0, 1), lv, h, n


def mat_cap(ctx):
    p = _wp(ctx)
    if ctx.face == "down":                              # the underside: dark gill shadow with radial lines of light
        r = np.hypot(p[:, 0], p[:, 2] - 0.5)
        az = np.arctan2(p[:, 0], p[:, 2] - 0.5)
        ray = (0.5 + 0.5 * np.cos(8 * (az - np.pi / 8))) ** 3          # broad soft rays between the gills
        fade = 1 - _ss(3.5, 11.5, r)
        if _burn(ctx):
            c = _mix(np.broadcast_to(ASH[1], (ctx.N, 3)), EMBER[2], 0.5 * ray * fade)
            return c, ctx.ones(), 0.3 * ray * fade
        c = _mix(np.broadcast_to(MINT[1], (ctx.N, 3)), MINT[4], 0.35 * fade + 0.3 * ray * fade)
        return c, ctx.ones(), 0.45 * ray ** 2 * fade
    rgb, lv, h, n = _cap_colour(ctx)
    core = _spots(ctx)
    if _burn(ctx):
        # scorched: the spore spots are embers, a few hairline cracks glow
        rgb = _mix(rgb, px.smooth_ramp(EMBER, 0.55 + 0.45 * core), np.clip(core * 1.4, 0, 1))
        crack = _ember_cracks(ctx)
        rgb = _mix(rgb, EMBER[3], crack)
        return rgb, ctx.ones(), np.maximum(0.6 * core, 0.55 * crack)
    rgb = _mix(rgb, px.smooth_ramp(SPORE, 0.3 + 0.7 * core), np.clip(core * 1.5, 0, 1))
    g = 0.85 * core ** 1.3
    return rgb, ctx.ones(), g


def _ember_cracks(ctx):
    """Hairline ember cracks over the scorched cap (world-position based, deterministic)."""
    p = _wp(ctx)
    a = np.sin(p[:, 0] * 0.9 + 1.3 * np.sin(p[:, 2] * 0.7)) + np.sin(p[:, 2] * 1.1 - 0.8 * np.sin(p[:, 1] * 0.9))
    return (1 - _ss(0.0, 0.07, np.abs(a))) * _ss(0.45, 0.85, np.sin(p[:, 1] * 0.8 + p[:, 0] * 0.3) * 0.5 + 0.5)


def mat_lip(ctx):
    """The socket: the dome's own tissue bulging round the eye - a pearl rim on its front edge, its
    inner wall lit violet by the eye."""
    rgb, lv, h, n = _cap_colour(ctx, extra_lv=0.04)
    g = np.zeros(ctx.N)
    burn = _burn(ctx)
    if ctx.face == "down":                              # the inner wall facing the eye
        v = np.clip(ctx.local[:, 2] / np.maximum(1e-6, 1.0), 0, 1)          # 0 front .. 1 deep
        t = 1 - _ss(0.0, 0.85, v * ctx.size[2] / 2.5)
        if burn:
            return _mix(np.broadcast_to(ASH[1], (ctx.N, 3)), EMBER[3], 0.7 * t), ctx.ones(), 0.35 * t
        c = _mix(np.broadcast_to(VOID[2], (ctx.N, 3)), px.col("#b76cff"), 0.8 * t)
        c = _mix(c, px.col("#ffb6f0"), 0.5 * t ** 3)
        return c, ctx.ones(), 0.7 * _ss(0.6, 1.0, t)
    if ctx.face == "north":                             # the rim facing out of the socket
        u = ctx.local[:, 1]                             # 0 inner edge .. 1 outer edge
        inner = u < 0.22 if ctx.size[1] > 1.2 else u < 0.3
        outer = u > 0.72
        if burn:
            rgb = _mix(rgb, EMBER[4], inner * 0.9)
            return rgb, ctx.ones(), np.where(inner, 0.6, 0.0)
        rgb = _mix(rgb, PEARL, 0.55 * outer)
        rgb = _mix(rgb, px.col("#e7a6ff"), 0.85 * inner)
        g = np.where(inner, 0.55, 0.0)
    return rgb, ctx.ones(), g


def petal_alpha(ctx, width_at: float = 0.45, base: float = 0.3):
    """Almond petal on a lid plate: v = 0 at the hinge .. 1 at the free end; widest at width_at."""
    u = ctx.local[:, 0] * 2 - 1
    v = 1 - ctx.local[:, 1]
    prof = np.where(v < width_at, base + (1 - base) * np.sin(np.clip(v / width_at, 0, 1) * np.pi / 2),
                    np.cos(np.clip((v - width_at) / (1 - width_at), 0, 1) * np.pi / 2) ** 0.8)
    return (np.abs(u) <= prof * 0.97).astype(float), u, v, prof


def mat_lid(ctx):
    """Eyelid petals: outside, the cap's own skin with a pearl edge; inside, pearl-lilac flushing
    to orchid at the tip with fine veins (alpha-tested: no glow, so the colours are bright)."""
    a, u, v, prof = petal_alpha(ctx)
    edge = np.abs(u) > prof * 0.97 - 0.2
    mid = np.abs(u) < 0.09
    lv = px.light(ctx, grad=0.0)
    burn = _burn(ctx)
    if ctx.face == "north":                             # the outside (faces the viewer when shut)
        if burn:
            c = px.smooth_ramp(ASH, 0.35 + 0.3 * lv + 0.2 * v)
            c = _mix(c, EMBER[3], edge * 0.8)
            return c, a, ctx.zeros()
        c = px.smooth_ramp(CAP_RAMP, 0.32 + 0.3 * lv + 0.28 * v)
        c = _mix(c, c * 0.55 + IRIS_MAGENTA * 0.45, 0.25 * v)
        c = _mix(c, PEARL, 0.6 * edge)
        c = _mix(c, px.col("#b58cf0"), 0.5 * mid * (v < 0.85))
        return c, a, ctx.zeros()
    if burn:
        c = _mix(np.broadcast_to(ASH[4], (ctx.N, 3)), EMBER[4], 0.25 + 0.5 * v)
        return c, a, ctx.zeros()
    base = _mix(px.col("#f6dcff"), px.col("#dc9dff"), _ss(0.05, 0.6, v))      # saturated: the cup's inside is shaded
    c = _mix(base, px.col("#ff58bd"), _ss(0.45, 1.0, v) * 0.95)
    c = _mix(c, px.col("#c27cff"), 0.45 * (mid & (v > 0.08) & (v < 0.85)))
    c = _mix(c, px.col("#ffffff"), 0.6 * edge * (v < 0.6))
    c = np.clip(c * (1.0 + 0.1 * lv)[:, None], 0, 1)
    return c, a, ctx.zeros()


def mat_void(ctx):
    """Deep space at the back of the socket: near-black indigo, a faint violet bloom toward the rim."""
    p = ctx.p
    d = np.hypot(p[:, 0] - EYE_C[0], p[:, 1] - EYE_C[1]) / VOID_H
    lv = 0.12 + 0.55 * _ss(0.15, 1.05, d) + 0.1 * _P(ctx, "frame")
    if _burn(ctx):
        return px.smooth_ramp(ASH[:4], lv), ctx.ones(), ctx.zeros()
    return px.smooth_ramp(VOID, lv), ctx.ones(), np.full(ctx.N, 0.1 * _P(ctx, "record"))


STAR = ["....w....",
        "....W....",
        ".w..W..w.",
        "..wWWWw..",
        "wWWWSWWWw",
        "..wWWWw..",
        ".w..W..w.",
        "....W....",
        "....w...."]


def mat_star(ctx):
    """The star pupil (4 texels per unit): a fine four-point sparkle with short diagonal glints,
    its rays fading from a white core into mint, on the void."""
    ix, iy, W, H = px.texel(ctx)
    rec, frame = _P(ctx, "record"), _P(ctx, "frame")
    bg = px.smooth_ramp(VOID, np.full(ctx.N, 0.15))
    if ctx.face != "north":
        return bg, ctx.ones(), ctx.zeros()
    x = ix + 0.5 - W / 2.0
    y = iy + 0.5 - H / 2.0
    r = np.hypot(x, y)
    long_ = np.maximum(np.clip(1 - np.abs(x) / 0.75, 0, 1) * np.clip(1 - np.abs(y) / 5.0, 0, 1),
                       np.clip(1 - np.abs(y) / 0.75, 0, 1) * np.clip(1 - np.abs(x) / 5.0, 0, 1))
    diag = np.clip(1 - np.abs(np.abs(x) - np.abs(y)) / 0.75, 0, 1) * np.clip(1 - r / 2.6, 0, 1)
    core = np.clip(1 - r / 1.6, 0, 1)
    k = np.clip(np.maximum.reduce([long_, 0.75 * diag, core * 1.4]), 0, 1)
    if _burn(ctx):
        lo, hi = px.col("#c2481a"), px.col("#fff0c0")
    elif rec > 0.5 or frame > 0.5:
        lo, hi = px.col("#c8fff0"), px.col("#ffffff")
    else:
        lo, hi = px.col("#5fe0c4"), px.col("#ffffff")
    c = _mix(bg, _mix(lo, hi, np.clip(core * 1.6 + 0.3 * long_, 0, 1)), np.clip(k * 1.3, 0, 1))
    g = np.where(k > 0.12, 0.35 + 0.65 * k, 0.0) * (0.75 if _burn(ctx) else 1.0)
    return c, ctx.ones(), g


def _ring_mat(k: int):
    def mat(ctx):
        rec, frame = _P(ctx, "record"), _P(ctx, "frame")
        if _burn(ctx):
            base = px.col(RING_EMBER[k])
            c = np.broadcast_to(base * (0.75 + 0.25 * (ctx.face == "north")), (ctx.N, 3))
            return c, ctx.ones(), np.full(ctx.N, 0.45)
        base = px.col(RING_HEX[k])
        if frame > 0.5:
            base = base * 0.62 + px.col("#ffffff") * 0.38
        elif rec > 0.5:
            base = base * 0.75 + px.col("#ffffff") * 0.25
        shade = 1.0 if ctx.face == "north" else 0.78
        c = np.broadcast_to(base * shade, (ctx.N, 3))
        return c, ctx.ones(), np.full(ctx.N, 0.82 + 0.13 * max(rec, frame))
    return mat


def mat_frill(ctx):
    """The luminous skirt: each lappet glows brightest where it leaves the rim, softens to a
    translucent teal, and its hem glows again in two scallops; fine veins run down it."""
    u = ctx.local[:, 0]                                 # across the lappet
    v = ctx.local[:, 2]                                 # 0 at the rim .. 1 at the hem
    if ctx.face not in ("up", "down"):
        c = px.smooth_ramp(ASH if _burn(ctx) else MINT, np.full(ctx.N, 0.55))
        return c, ctx.ones(), np.full(ctx.N, 0.0 if _burn(ctx) else 0.3)
    inner = ctx.face == "down"
    sc = 1 - (np.abs(((u * 2.0) % 1.0) - 0.5) * 2) ** 2                   # two scallops across the hem
    vs = 0.8 + 0.15 * sc                                                   # the scallop curve: lobes hang lower
    hem_line = np.abs(v - vs) < 0.05
    hem = v > vs + 0.05                                                    # beyond the lobes: dim, as if open
    vein = (np.abs(((u * 6.0) % 1.0) - 0.5) < 0.09) & (v > 0.12) & (v < vs - 0.08)
    if _burn(ctx):
        lv = 0.38 - 0.18 * v
        c = px.smooth_ramp(ASH, lv)
        c = _mix(c, EMBER[3], hem_line * 0.9)
        return c, ctx.ones(), np.where(hem_line, 0.55, 0.0)
    top = 1 - _ss(0.0, 0.5, v)
    lv = 0.5 + 0.32 * top + (0.06 if inner else 0.0) - 0.08 * _ss(0.5, 0.86, v)
    c = px.smooth_ramp(MINT, lv)
    c = _mix(c, MINT[7], 0.55 * hem_line)
    c = _mix(c, MINT[6], 0.35 * vein)
    c = _mix(c, MINT[1], 0.75 * hem)
    band = 1 - _ss(0.0, 0.16, v)                       # the luminous band where the skirt leaves the rim
    g = 0.42 * band ** 1.6 + (0.06 * top if inner else 0.0)
    g = np.where(hem_line, 0.62, g) + 0.1 * vein * (v < 0.45)
    g = np.where(hem, 0.0, g)
    return c, ctx.ones(), np.clip(g, 0, 1)


def mat_gill(ctx):
    """Radiating gill fins: mint light, brightest at the free edge, fine lamellae along them."""
    ix, iy, W, H = px.texel(ctx)
    t = (iy + 0.5) / H if px.side(ctx) else np.full(ctx.N, 0.5)          # 0 top (under the cap) .. 1 free edge
    lam = (ix % 3) == 0
    if _burn(ctx):
        c = px.smooth_ramp(ASH, 0.3 + 0.2 * t)
        c = _mix(c, EMBER[3], 0.7 * (t > 0.75))
        return c, ctx.ones(), np.where(t > 0.75, 0.4, 0.0)
    c = px.smooth_ramp(MINT, 0.45 + 0.4 * t - 0.08 * lam)
    return c, ctx.ones(), 0.7 * _ss(0.55, 1.0, t)


def mat_spore(ctx):
    lv = px.light(ctx, grad=0.0) + 0.2
    return px.smooth_ramp(GOLD, lv), ctx.ones(), np.full(ctx.N, 0.75)


def _helix(ctx, turns: float = 0.55, phase: float = 0.0):
    """Phase (0..1) of a helix wound round the stalk axis: continuous over every face."""
    p = _wp(ctx)
    th = np.degrees(np.arctan2(p[:, 0], p[:, 2] - 0.5)) / 360.0
    return (th + p[:, 1] * turns / 2.0 + phase) % 1.0


def mat_lattice(ctx):
    """The stalk's twisted lattice (alpha-tested): two helices of pale tissue crossing."""
    a1 = _helix(ctx, 0.5)
    a2 = _helix(ctx, -0.5, 0.125)
    s1 = np.abs(((a1 * 4) % 1.0) - 0.5) < 0.13
    s2 = np.abs(((a2 * 4) % 1.0) - 0.5) < 0.1
    alpha = (s1 | s2).astype(float)
    lv = px.cyl(ctx, (0, STALK_BOT, 0.5), (0, STALK_TOP, 0.5), 0.9) + 0.06
    if _burn(ctx):
        return px.smooth_ramp(ASH, lv * 0.8 + 0.1), alpha, ctx.zeros()
    c = px.smooth_ramp(PALE, lv + 0.08)
    edge = np.abs(((a1 * 4) % 1.0) - 0.5) > 0.08
    c = _mix(c, PALE[6], 0.5 * (s1 & edge))
    return c, alpha, ctx.zeros()


def mat_core(ctx):
    """The glowing core: cyan light with a pink spiral wound through it."""
    h = _helix(ctx, 0.4)
    band = np.abs(((h * 3) % 1.0) - 0.5) < 0.2
    if _burn(ctx):
        c = _mix(np.broadcast_to(EMBER[3], (ctx.N, 3)), EMBER[5], band * 0.7)
        return c, ctx.ones(), np.full(ctx.N, 0.5)
    c = _mix(np.broadcast_to(px.col("#7ff6ea"), (ctx.N, 3)), px.col("#ff9fe0"), band * 0.85)
    return c, ctx.ones(), np.where(band, 0.85, 0.09)


def mat_volva(ctx):
    """The bulb: deep cap tissue with a pearl sheen and a ring of glowing pores round its waist."""
    y, prof = BULB
    c0 = (0.0, y + 1.6, 0.5)
    lv = px.proxy(ctx, c0, (4.8, 2.6, 4.8), 0.9) + 0.02
    p = _wp(ctx)
    pc = [np.array([4.35 * math.sin(math.radians(a)), y + 2.1, 0.5 + 4.35 * math.cos(math.radians(a))])
          for a in range(0, 360, 45)]
    pore = px.glow_spot(ctx, pc, 0.8, 0.2)
    if _burn(ctx):
        c = px.smooth_ramp(ASH, lv)
        return _mix(c, EMBER[4], pore), ctx.ones(), 0.6 * pore
    c = px.smooth_ramp(CAP_RAMP, lv * 0.85 + 0.05)
    n = smooth_normals(ctx, c0, (4.8, 2.6, 4.8))
    c = _mix(c, PEARL, 0.5 * np.clip(n @ KEY, 0, 1) ** 6)
    c = _mix(c, px.smooth_ramp(GOLD, 0.4 + 0.6 * pore), np.clip(pore * 1.5, 0, 1))
    if ctx.face == "down":
        r = np.hypot(p[:, 0], p[:, 2] - 0.5)
        mouth = 1 - _ss(0.8, 1.9, r)
        c = _mix(c, MINT[6], mouth)
        return c, ctx.ones(), 0.7 * mouth
    return c, ctx.ones(), 0.75 * pore ** 1.5


# ---------------------------------------------------------------------------- the mycelia

def _polylines():
    out = {}
    for g in range(MYC):
        P = np.array(spline(MYC_PTS[g], 6))
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
        out[g] = (P, np.concatenate([[0.0], np.cumsum(seg)]))
    return out


POLY = _polylines()
JOB_GROUPS = {"m": (0, 1), "f": (2, 3), "s": (4,), "p": (5,), "b": (6,), "a": (7,)}
JOB_TIP = {"m": PINK_TIP, "f": CYAN_TIP, "s": CYAN_TIP, "p": PINK_TIP, "b": CYAN_TIP, "a": CYAN_TIP}


def _along(ctx, groups):
    """0 (root) .. 1 (tip) along the nearest of the groups' centre curves, for every texel."""
    p = _wp(ctx)
    best_d = np.full(ctx.N, np.inf)
    best_t = np.zeros(ctx.N)
    for g in groups:
        P, cum = POLY[g]
        for i in range(len(P) - 1):
            a, b = P[i], P[i + 1]
            ab = b - a
            L2 = max(float(ab @ ab), 1e-9)
            t = np.clip(((p - a) @ ab) / L2, 0, 1)
            d = np.linalg.norm(p - (a + t[:, None] * ab), axis=1)
            m = d < best_d
            best_d = np.where(m, d, best_d)
            best_t = np.where(m, (cum[i] + t * math.sqrt(L2)) / cum[-1], best_t)
    return best_t


def _hypha(job: str):
    """A pale translucent tendril: lighter at its edges than its middle (light passing through), an
    inner vein that brightens toward the tip, and the last quarter flushing into a glowing tip."""
    tipc = JOB_TIP[job]

    def mat(ctx):
        t = _along(ctx, JOB_GROUPS[job])
        lv = px.light(ctx, grad=0.0)
        lx, ly = np.abs(ctx.local[:, 0] * 2 - 1), np.abs(ctx.local[:, 1] * 2 - 1)
        across = ly if ctx.face in ("east", "west") else (lx if ctx.face in ("up", "down") else np.maximum(lx, ly))
        burn = _burn(ctx)
        if burn:
            c = px.smooth_ramp(ASH, 0.3 + 0.35 * lv + 0.1 * across)
            tipm = _ss(0.8, 0.98, t)
            c = _mix(c, EMBER[3], tipm)
            return c, ctx.ones(), 0.55 * tipm
        c = px.smooth_ramp(PALE, 0.48 + 0.3 * lv + 0.16 * across ** 2 + 0.06 * t)
        vein = across < 0.3
        c = _mix(c, _mix(px.col("#c9b6ff"), tipc, t), 0.55 * vein)
        tipm = _ss(0.7, 0.97, t)
        c = _mix(c, tipc, 0.85 * tipm)
        g = np.where(vein, 0.4 * _ss(0.45, 0.9, t), 0.0)
        g = np.maximum(g, 0.75 * tipm)
        return c, ctx.ones(), g
    return mat


def mat_grip(ctx):
    if _burn(ctx):
        return np.broadcast_to(EMBER[3], (ctx.N, 3)), ctx.ones(), np.full(ctx.N, 0.5)
    c = _mix(np.broadcast_to(PINK_TIP, (ctx.N, 3)), px.col("#ffe0f4"), 0.3 * (ctx.face == "up"))
    return c, ctx.ones(), np.full(ctx.N, 0.8)


def mat_fan(ctx):
    """Propulsion fin vanes (alpha-tested): a translucent membrane, lilac at the root, pale cyan
    toward a bright edge, with darker rays."""
    a, lvl = px.vane(ctx, width_at=0.38, tip=0.98, base=0.35, rachis=0.1, barb=3.0)
    v = ctx.local[:, 2]
    u = np.abs(ctx.local[:, 0] * 2 - 1)
    if _burn(ctx):
        c = px.smooth_ramp(ASH, 0.35 + lvl + 0.2 * v)
        return _mix(c, EMBER[3], 0.6 * (u > 0.8)), a, ctx.zeros()
    c = _mix(px.col("#c8adff"), px.col("#8ff0ff"), _ss(0.1, 0.85, v))
    c = c * (0.95 + lvl * 1.2)[:, None]
    c = _mix(c, px.col("#f4feff"), 0.7 * (u > 0.8))
    return np.clip(c, 0, 1), a, ctx.zeros()


def mat_ribbon(ctx):
    """The stabiliser curtain: a translucent ribbon with glowing edges and cross veins, its tip cyan."""
    u = np.abs(ctx.local[:, 0] * 2 - 1)
    t = _along(ctx, (6,))
    if ctx.face not in ("up", "down"):
        return px.smooth_ramp(PALE, np.full(ctx.N, 0.7)), ctx.ones(), np.full(ctx.N, 0.3)
    edge = u > 0.78
    ix, iy, W, H = px.texel(ctx)
    cross = (np.abs(((t * 14.0) % 1.0) - 0.5) < 0.08) & ~edge
    if _burn(ctx):
        c = px.smooth_ramp(ASH, np.full(ctx.N, 0.35) + 0.1 * u)
        return _mix(c, EMBER[3], edge * _ss(0.5, 1.0, t)), ctx.ones(), np.where(edge, 0.4 * t, 0.0)
    c = px.smooth_ramp(PALE, 0.55 + 0.2 * u ** 2 + 0.1 * (ctx.face == "up"))
    c = _mix(c, _mix(px.col("#b9fff1"), CYAN_TIP, t), 0.75 * edge)
    c = _mix(c, px.col("#d8cdfb"), 0.5 * cross)
    tipm = _ss(0.82, 1.0, t)
    c = _mix(c, CYAN_TIP, 0.8 * tipm)
    g = np.where(edge, 0.5 * _ss(0.35, 0.8, t), 0.0)
    return c, ctx.ones(), np.maximum(g, 0.7 * tipm)


def mat_bulb(ctx):
    if _burn(ctx):
        return np.broadcast_to(EMBER[4], (ctx.N, 3)), ctx.ones(), np.full(ctx.N, 0.7)
    c = np.broadcast_to(px.col("#9ff8ff"), (ctx.N, 3)) * (0.9 + 0.12 * (ctx.face == "up"))
    return c, ctx.ones(), np.full(ctx.N, 0.95)


def mat_feeler(ctx):
    return np.broadcast_to(EMBER[3] if _burn(ctx) else px.col("#c9fbff"), (ctx.N, 3)), ctx.ones(), np.full(ctx.N, 0.6)


def mat_pod(ctx):
    """The lantern pod: pearl-cream skin over a glowing heart - gold pores, a lit mouth below."""
    pod = np.asarray(MYC_PTS[5][-1], float) + np.array([0.0, -1.75, 0.0])
    lv = px.proxy(ctx, pod, (1.75, 1.9, 1.75), 0.85) + 0.06
    p = _wp(ctx)
    d = p - pod
    az = np.degrees(np.arctan2(d[:, 0], d[:, 2]))
    pore = (np.abs(((az + 30) % 60.0) - 30) < 9.0) & (np.abs(d[:, 1] + 0.1) < 0.45) & px.side(ctx)
    mouth = (ctx.face == "down") & (np.hypot(d[:, 0], d[:, 2]) < 0.9)
    if _burn(ctx):
        c = px.smooth_ramp(ASH, lv)
        m = pore | mouth
        return _mix(c, EMBER[4], m), ctx.ones(), np.where(m, 0.65, 0.0)
    c = px.smooth_ramp(CREAM, lv)
    seam = (np.abs(((az + 30) % 60.0) - 30) > 27) & px.side(ctx)
    c = _mix(c, CREAM[2], 0.5 * seam)
    c = _mix(c, px.smooth_ramp(GOLD, np.full(ctx.N, 0.85)), pore | mouth)
    return c, ctx.ones(), np.where(pore | mouth, 0.75, 0.0)


def mat_crystal(ctx):
    if _burn(ctx):
        return np.broadcast_to(EMBER[4], (ctx.N, 3)), ctx.ones(), np.full(ctx.N, 0.7)
    return np.broadcast_to(px.col("#a8fbff"), (ctx.N, 3)), ctx.ones(), np.full(ctx.N, 0.9)


def mat_tendril_fp(ctx):
    """First person: the arm drawn as a pale translucent tendril, a pink glowing tip at the hand
    (only the last texels glow, so nothing bright sits in the middle of the screen)."""
    p = ctx.p
    t = np.clip((24.0 - p[:, 1]) / 12.8, 0, 1)
    lv = px.light(ctx, grad=0.0)
    across = np.abs(ctx.local[:, 0] * 2 - 1) if ctx.face in ("north", "south") else np.abs(ctx.local[:, 2] * 2 - 1)
    if _burn(ctx):
        c = px.smooth_ramp(ASH, 0.35 + 0.3 * lv)
        return _mix(c, EMBER[3], _ss(0.85, 1.0, t)), ctx.ones(), 0.4 * _ss(0.85, 1.0, t)
    c = px.smooth_ramp(PALE, 0.5 + 0.25 * lv + 0.15 * across ** 2)
    vein = across < 0.2
    c = _mix(c, px.col("#cdb8ff"), 0.4 * vein)
    tipm = _ss(0.86, 1.0, t)
    c = _mix(c, PINK_TIP, 0.8 * tipm)
    return c, ctx.ones(), np.maximum(0.12 * vein * t, 0.5 * tipm)


def materials():
    mats = {
        "cap": mat_cap, "lip": mat_lip, "lid": mat_lid, "void": mat_void, "star": mat_star, "frill": mat_frill,
        "gill": mat_gill, "spore": mat_spore, "lattice": mat_lattice, "core": mat_core, "volva": mat_volva,
        "grip": mat_grip, "fan": mat_fan, "ribbon": mat_ribbon, "bulb": mat_bulb, "feeler": mat_feeler, "pod": mat_pod,
        "crystal": mat_crystal, "tendril_fp": mat_tendril_fp, "accent": mat_accent,
    }
    for job in JOB_GROUPS:
        mats[f"hy_{job}"] = _hypha(job)
    for k in range(RINGS):
        mats[f"ring{k}"] = _ring_mat(k)
    return mats
