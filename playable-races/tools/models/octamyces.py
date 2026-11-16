"""Race 009 - Octamyces Undecimus, Witness of the Eleventh Rift (v1.5 premium redesign).

"ผู้เฝ้ามองแห่งรอยแยกที่ 11" - a majestic floating witness.  An extradimensional fungus that
watches several realities at once: not a monster with one eye and not malicious, unreadable.

  * a smooth lopsided DOME cap (lathe(), 20 px across, 9 px tall) leaning forward over its eye like
    a hood, its crown pushed to the left; a scalloped luminous frill hangs from the rim and
    radiating gill fins glow underneath
  * THE UNDECIMAL EYE on the front of the cap: eleven thin polygon rings (3- to 13-sided, ring0 ..
    ring10) over a deep void with a star pupil, each ring a little in front of the one inside it,
    framed by eight eyelid petals (lid0 .. lid7) that fold shut like a flower to blink and by a
    corona of eight glowing rays that frame the cap's edge from behind
  * a twisted lattice stalk with a glowing core and a bulb
  * EIGHT mycelial groups, each shaped for its job (myc<g>_0..2): 0/1 manipulators that hold your
    items at the vanilla hand points, 2/3 propulsion fins, 4 a sensor, 5 a spore emitter (a
    lantern pod), 6 a stabiliser curtain, 7 a resonance antenna on the crown
  * it floats: the lowest filament ends 4 px above the ground

Variants: base (Witnessing) | sporeveil | record | offset | frame | unstable (on fire).
"""
from __future__ import annotations

import math

import numpy as np

from kit.geo import Model
from kit import pixel as px
from models.common import (accents, feather_fan, fp_sleeves, frame_rot, humanoid, lathe, mat_accent, q, rays, segment,
                           sweep)

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
CAP_J = (0.0, 26.5, 0.5)             # cap / stalk joint (the cap turns and tilts about it)
RIM_Y = 27.0
CAP_C = (0.0, RIM_Y, 0.5)            # lathe centre of the dome (rim level)
CAP_H = 9.0
# bell-dome profile (height above the rim, radius): heights on 0.25 steps so the bands meet exactly
CAP_PROFILE = [(0.0, 10.0), (3.0, 9.5), (4.5, 8.5), (5.5, 7.45), (6.25, 6.35), (7.0, 5.05), (7.75, 3.65), (8.5, 2.15),
               (9.0, 0.75)]
CAP_SKEW = (1.25, -2.0)              # the crown leans forward over the eye and swells to the left (+X)
CAP_SQUASH = (1.0, 0.95)
BAND_BONE = ["cap", "cap", "cap", "cap_mid", "cap_mid", "cap_mid", "cap_upper", "cap_upper"]

EYE_C = (0.0, 29.25, -9.75)          # centre of the void (the eye bone's pivot, before its tilt)
EYE_TILT = 24.0                      # the eye looks forward and a little up
RING_SIDES = tuple(range(3, 14))     # ring0 = triangle (innermost) ... ring10 = thirteen-gon
RINGS = len(RING_SIDES)
RING_A0, RING_DA = 0.8, 0.45         # apothem of ring0 and the even step outward
RING_T = 0.25                        # bar thickness: thin luminous lines
RING_D = 0.25                        # bar depth
RING_DZ = 0.14                       # each ring sits a little in front of the one inside it (a shallow funnel)
VOID_A = 5.0                         # apothem of the void disc (an octagon hidden behind the outermost ring)
LIDS = 8
LID_W, LID_LEN = 3.5, 4.0            # eyelid petals: widest across, length from the hinge
LID_OPEN = -120.0                    # rest fold: open, cupped forward round the eye like a flower
LID_PHASE = 22.5                     # two petals either side of the top, a ray of the corona between them
RAYS = 8
RAY_R = (5.9, 9.75)                  # the corona between the petals (longest at the top, shortest below)
RAY_LEN = (1.0, 0.85, 0.75, 0.6, 0.45, 0.6, 0.75, 0.85)
STALK_TOP, STALK_BOT = 26.25, 13.0
MYC = 8

# ---------------------------------------------------------------------------- derived


def ring_apothem(k: int) -> float:
    return RING_A0 + RING_DA * k


def ring_z(k: int) -> float:
    return EYE_C[2] - 0.35 - RING_DZ * k


def ring_circum(k: int) -> float:
    return ring_apothem(k) / math.cos(math.pi / RING_SIDES[k])


LID_A = ring_circum(RINGS - 1) + 0.3                   # hinge circle of the petals
LID_Z = ring_z(RINGS - 1) - 0.2                        # hinge plane, just in front of the outermost ring


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
    return RIM_Y + y0, RIM_Y + y1, c, r, (12 if r > 3.0 else 8)


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
    from kit.geo import rot_matrix
    c = np.asarray(EYE_C, float)
    return rot_matrix((-EYE_TILT, 0.0, 0.0)) @ (np.asarray(p, float) - c) + c


# ============================================================================= build

def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=256)
    humanoid(m)
    # head chain: head_g and `steady` cancel the player's look exactly (x on one bone, y on the
    # next); `float_h` mirrors the body's hover so the cap stays on its stalk; the cap then turns
    # by a fraction of the look about the stalk joint, the iris by more, inside its crown
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
        ("c", "collar", "stalk", (0.0, 24.75, 0.5), (4.5, 0.75, 4.5)),
        ("l", "fins", "float", (0.0, 22.0, 2.0), (3.5, 1.5, 0.75)),
        ("f", "tips", "myc6_2", (0.0, 5.0, 4.25), (3.5, 0.5, 1.0)),
    ])
    for b in m.bones.values():               # every cube angle inside (-180, 180] (the same rotations)
        for c in b.cubes:
            if c.rot is not None:
                c.rot = _cube_rot(c.rot)
    m.pack()
    return m


# ----------------------------------------------------------------------------- the dome cap

def _dome(m: Model) -> None:
    """The cap: a lathe() dome, one band per call so each band can carry its own faces and bone.
    The upper bands ride cap_mid / cap_upper (Hyphal Offset slides them off the lower ones)."""
    m.bone("cap_mid", "cap", (CAP_C[0] + 0.8, RIM_Y + 4.5, CAP_C[2] - 1.0))
    m.bone("cap_upper", "cap_mid", (CAP_C[0] + 1.1, RIM_Y + 6.75, CAP_C[2] - 1.5))
    m.bones["cap_mid"].variant["offset"] = ((1.5, 0.5, 1.25), (0.0, 14.0, -3.0))
    m.bones["cap_upper"].variant["offset"] = ((-2.25, 1.0, 0.75), (0.0, -26.0, 4.0))
    for i in range(len(CAP_PROFILE) - 1):
        y0, y1, c, r, sides = cap_band(i)
        faces = {"north", "south", "up"} | ({"down"} if i == 0 else set())
        lathe(m, BAND_BONE[i], c, [(y0 - RIM_Y, r), (y1 - RIM_Y, r)], "cap", sides=sides, squash=CAP_SQUASH,
              faces=faces)
    top = cap_band(len(CAP_PROFILE) - 2)
    m.bones["cap_upper"].locators["cap_top"] = (top[2][0], RIM_Y + CAP_H + 0.5, top[2][2])
    m.bones["cap"].locators["gills"] = (0.0, 25.0, 0.5)


FRILL_Q = {"frill_f": (11, 0, 1), "frill_r": (2, 3, 4), "frill_b": (5, 6, 7), "frill_l": (8, 9, 10)}
FRILL_LEN = (2.75, 2.25)             # alternating lappets: a gently wavy rim
FRILL_FLARE = (14.0, 27.0)


def _frill(m: Model) -> None:
    """A luminous frill hanging from the rim: twelve lappets on the twelve sides of the rim band,
    flared outward at alternating angles (a gentle wave), in four quadrants that ripple."""
    _, _, c, r, sides = cap_band(0)
    c = np.asarray(c, float)
    edge = 2 * r * math.sin(math.pi / sides)
    for name, ks in FRILL_Q.items():
        th0 = 30.0 * ks[1]
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
            top = c + n * (rim_dist(th) + 0.15) + np.array([0.0, 0.6, 0.0])
            plate(m, b.name, top, down, nrm, q(edge * sq + 0.5), FRILL_LEN[k % 2] + 0.6, 0.25, "frill")
    # (+rx swings a hanging part back, +rz swings a part on the creature's right outward)
    m.bones["frill_f"].variant["unstable"] = ((0.0, -0.25, 0.0), (16.0, 0.0, 0.0))      # scorched: the rim sags limp
    m.bones["frill_b"].variant["unstable"] = ((0.0, -0.25, 0.0), (-16.0, 0.0, 0.0))
    m.bones["frill_r"].variant["unstable"] = ((0.0, -0.25, 0.0), (0.0, 0.0, -16.0))
    m.bones["frill_l"].variant["unstable"] = ((0.0, -0.25, 0.0), (0.0, 0.0, 16.0))
    for name, rot in (("frill_f", (-22.0, 0, 0)), ("frill_b", (22.0, 0, 0)), ("frill_r", (0, 0, 22.0)),
                      ("frill_l", (0, 0, -22.0))):
        m.bones[name].variant["sporeveil"] = ((0.0, 0.0, 0.0), rot)       # the frill flares open


def _gills(m: Model) -> None:
    """Radiating glowing gill fins under the cap, and (Parallax Sporeveil) ripe spore pearls."""
    g = m.bone("gill_ring", "cap", (0.0, 26.5, 0.5))
    rays(m, g.name, (0.15, 26.0, 0.4), 12, 1.75, 8.75, 0.5, "gill", plane="flat", thick=2.0, phase=15.0)
    for k in range(6):
        a = math.radians(30.0 + 60.0 * k)
        rr = 4.5 + 1.5 * (k % 2)
        m.box(g.name, (0.15 + rr * math.sin(a), 24.0 - 0.75 * (k % 2), 0.4 + rr * math.cos(a)), (1.0, 1.0, 1.0),
              "spore", only={"sporeveil"})


# ----------------------------------------------------------------------------- the undecimal eye

def _eye(m: Model) -> None:
    cx, cy, cz = EYE_C
    eye = m.bone("eye", "cap", EYE_C, (-EYE_TILT, 0.0, 0.0))
    eye.locators["eye_c"] = (cx, cy, ring_z(RINGS - 1) - 0.5)
    iris = m.bone("iris", eye.name, (cx, cy, cz + 1.5))
    # the void: a deep twelve-gon (three squares a hair apart), the star pupil just in front
    pu = m.bone("pupil", iris.name, (cx, cy, cz))
    ve = q(2 * VOID_A * math.tan(math.pi / 8) + 0.25, 0.25)        # an octagon from four crossing strips (lathe's trick)
    for k in range(4):
        m.cube(pu.name, (cx - ve / 2, cy - VOID_A, cz + 0.02 * k), (ve, 2 * VOID_A, 0.25), "void",
               pivot=(cx, cy, cz), rot=(0, 0, 45.0 * k) if k else None, faces={"north"} if k else {"north", "south"})
    m.cube(pu.name, (cx - 1.25, cy - 1.25, cz - 0.12), (2.5, 2.5, 0.1), "star", ppu=4.0, faces={"north"})
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
    # eight eyelid petals hinged round the outermost ring: open they stand as a crown, cupped
    # forward; a blink folds them shut (rx -> 0) into a flat octagon with only the star showing
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
    # the corona: eight glowing rays between the petals, leaning back over the cap
    lean = math.radians(16.0)
    for j in range(RAYS):
        th = math.radians(LID_PHASE + 22.5 + 45.0 * j)
        d = np.array([math.sin(th) * math.cos(lean), math.cos(th) * math.cos(lean), math.sin(lean)])
        o = np.array([cx, cy, LID_Z + 0.6]) + d * RAY_R[0]
        ln = (RAY_R[1] - RAY_R[0]) * RAY_LEN[j]
        m.cube(eye.name, (o[0] - 0.375, o[1] - 0.125, o[2]), (0.75, 0.25, q(ln)), "ray", pivot=tuple(o),
               rot=_cube_rot(frame_rot(d, (0.0, 0.0, -1.0))))


# ----------------------------------------------------------------------------- the stalk

def _twisted(m: Model, bone: str, y0: float, y1: float, r: float, twist: float, mat: str, **kw):
    """One band of an eight-sided prism (four crossing strips) turned by `twist` degrees."""
    apo = r * math.cos(math.pi / 8)
    edge = 2 * r * math.sin(math.pi / 8)
    for k in range(4):
        ang = _rot(45.0 * k + twist)
        e = 0.02 * k
        m.cube(bone, (-q(edge + 0.25, 0.25) / 2, y0 - e, 0.5 - q(2 * apo, 0.25) / 2), (q(edge + 0.25, 0.25), y1 - y0 + 2 * e,
               q(2 * apo, 0.25)), mat, pivot=(0.0, y0, 0.5), rot=(0, ang, 0) if ang else None, **kw)


STALK_BANDS = ((21.5, 26.25, 2.0, 0.0), (17.0, 21.5, 1.75, 15.0), (13.0, 17.0, 2.0, 30.0))


def _stalk(m: Model) -> None:
    st = m.bone("stalk", "float", (0.0, STALK_TOP, 0.5))
    core = m.bone("core", st.name, (0.0, 20.0, 0.5))
    for k in range(2):
        m.cube(core.name, (-0.75, STALK_BOT + 0.5 + 0.02 * k, -0.25), (1.5, STALK_TOP - STALK_BOT - 0.5 - 0.04 * k, 1.5),
               "core", pivot=(0.0, 20.0, 0.5), rot=(0, 45.0, 0) if k else None, faces={"north", "south", "east", "west"})
    for y0, y1, r, tw in STALK_BANDS:
        _twisted(m, st.name, y0, y1, r, tw, "lattice", cutout=True, faces={"north", "south"})
    # the bulb (volva) the stalk grows from
    lathe(m, st.name, (0.0, 11.25, 0.5), [(0.0, 2.75), (2.0, 2.75)], "volva", sides=8,
          faces={"north", "south", "up", "down"})
    st.locators["base_c"] = (0.0, 10.75, 0.5)


# ----------------------------------------------------------------------------- the eight mycelial groups

# control points (Catmull-Rom through them); every group a chain of three bones myc<g>_0..2
MYC_PTS = {
    # 0/1 manipulators: out from under the cap, down in an S to the vanilla hand point
    0: [(-2.75, 25.0, 0.25), (-5.25, 22.75, 0.5), (-6.75, 18.25, 0.25), (-6.75, 14.25, -0.25), (-6.0, 11.5, -0.75)],
    # 2/3 propulsion fins: from the back of the stalk, sweeping back and out
    2: [(-1.25, 22.0, 1.75), (-4.0, 20.75, 4.0), (-6.25, 18.25, 6.0), (-7.0, 14.75, 7.25)],
    # 4 sensor (front-left): reaches forward and down, its tip curling up
    4: [(1.25, 23.75, -0.75), (4.5, 20.5, -4.5), (5.25, 16.25, -8.25), (4.25, 16.5, -10.75)],
    # 5 spore emitter (front-right): carries a lantern pod
    5: [(-1.25, 22.5, -0.75), (-3.25, 20.25, -3.75), (-4.25, 17.75, -6.0), (-4.25, 16.5, -6.75)],
    # 6 stabiliser curtain: a train of filaments trailing from the bulb
    6: [(0.0, 11.25, 1.0), (0.0, 8.5, 2.0), (0.0, 6.25, 3.25), (0.0, 4.25, 4.75)],
    # 7 resonance antenna: rises from the crown and leans back
    7: [(2.0, 35.5, -0.5), (2.75, 37.25, 1.0), (3.25, 38.5, 2.75), (3.5, 39.0, 4.25)],
}
MYC_PTS[1] = [(-x, y, z) for x, y, z in MYC_PTS[0]]
MYC_PTS[3] = [(-x, y, z) for x, y, z in MYC_PTS[2]]
MYC_PARENT = {0: "r_arm_g", 1: "l_arm_g", 2: "stalk", 3: "stalk", 4: "stalk", 5: "stalk", 6: "stalk", 7: "cap_upper"}
MYC_W = {0: (1.0, 0.5), 1: (1.0, 0.5), 2: (1.0, 0.5), 3: (1.0, 0.5), 4: (0.75, 0.5), 5: (1.0, 0.75), 7: (0.5, 0.5)}
MYC_JOB = {0: "m", 1: "m", 2: "f", 3: "f", 4: "s", 5: "p", 6: "b", 7: "a"}
CURTAIN_X = (-1.0, 0.0, 1.0)             # the stabiliser's three filaments, side by side
CURTAIN_SPREAD = 1.9                     # ... fanning out toward their tips
CURTAIN_END = (0.75, -0.25, 1.0)         # each ends a little higher (+) or lower (-)
SPREAD = {2: (-12.0, -22.0, 18.0), 3: (-12.0, 22.0, -18.0), 4: (-20.0, 18.0, -8.0), 5: (-14.0, -14.0, 14.0),
          6: (34.0, 0.0, 0.0), 7: (-14.0, 0.0, -12.0)}             # Hyphal Offset: the mycelia stand out like fins
DROOP = {2: (18.0, 0.0, -8.0), 3: (18.0, 0.0, 8.0), 4: (22.0, 0.0, 0.0), 5: (10.0, 0.0, 8.0), 6: (-4.0, 0.0, 0.0),
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
            sweep(m, MYC_PARENT[g], f"myc{g}_", pts, w0, w1, f"hy_{MYC_JOB[g]}", n=2, per_bone=per)
        root = m.bones[f"myc{g}_0"]
        if g in SPREAD:
            root.variant["offset"] = ((0.0, 0.0, 0.0), SPREAD[g])
        if g in DROOP:
            root.variant["unstable"] = ((0.0, 0.0, 0.0), DROOP[g])
    _tips(m)


def _curtain(m: Model) -> None:
    pts = [np.asarray(p, float) for p in MYC_PTS[6]]
    par = MYC_PARENT[6]
    for k in range(3):
        b = m.bone(f"myc6_{k}", par, tuple(pts[k]))
        par = b.name
        for t, dx in enumerate(CURTAIN_X):
            f0 = 1.0 + (CURTAIN_SPREAD - 1.0) * k / 3
            f1 = 1.0 + (CURTAIN_SPREAD - 1.0) * (k + 1) / 3
            a = pts[k] + np.array([dx * f0, 0.0, 0.0])
            e = pts[k + 1] + np.array([dx * f1, CURTAIN_END[t] if k == 2 else 0.0, 0.0])
            segment(m, b.name, a, e, 0.5, 0.5, "hy_b", overlap=0.3)


def _tips(m: Model) -> None:
    for g, side, p in ((0, -1, "r"), (1, 1, "l")):            # a curled grip round the held item
        e = np.asarray(MYC_PTS[g][-1], float)
        tip = f"myc{g}_2"
        segment(m, tip, e, e + np.array([side * 0.75, -1.0, -1.0]), 0.5, 0.5, "grip", overlap=0.0)
        m.bones[tip].locators[f"{p}_grip"] = tuple(e + np.array([0.0, -1.0, -0.25]))
    for g, side in ((2, -1), (3, 1)):                        # fin membranes trailing from the fin's middle joint
        o = MYC_PTS[g][1]
        feather_fan(m, f"myc{g}_1", f"fin{g}_", o, 3, [5.0, 6.5, 5.5], [2.5, 2.5, 2.0], "fan", spread=62.0,
                    center=side * 118.0, plane="back", lift=34.0, bones=False, cutout=True, faces={"up", "down"})
    e = np.asarray(MYC_PTS[4][-1], float)                     # the sensor's glowing bulb and two feelers
    m.box("myc4_2", tuple(e + np.array([0.0, 0.25, -0.25])), (1.0, 1.0, 1.0), "bulb", rot=(45.0, 0.0, 0.0),
          pivot=tuple(e + np.array([0.0, 0.25, -0.25])))
    segment(m, "myc4_2", e, e + np.array([0.75, 1.5, -1.25]), 0.25, 0.25, "feeler", overlap=0.0)
    segment(m, "myc4_2", e, e + np.array([-0.75, 1.25, -1.5]), 0.25, 0.25, "feeler", overlap=0.0)
    m.bones["myc4_2"].locators["sensor"] = tuple(e + np.array([0.0, 0.5, -1.0]))
    pod = np.asarray(MYC_PTS[5][-1], float) + np.array([0.0, -1.5, 0.0])     # the lantern pod
    for s in ((2.75, 2.25, 2.75), (2.25, 3.25, 2.25), (3.25, 1.5, 3.25)):
        m.box("myc5_2", tuple(pod), s, "pod")
    m.bones["myc5_2"].locators["spores"] = tuple(pod + np.array([0.0, -2.5, 0.0]))
    e = np.asarray(MYC_PTS[7][-1], float) + np.array([0.0, 0.9, 0.25])      # a floating triangle at the antenna's tip
    for j in range(3):
        ang = _rot(60.0 + 120.0 * j)
        m.cube("myc7_2", (e[0] - 0.75, e[1] + 0.35, e[2] - 0.125), (1.5, 0.25, 0.25), "crystal", pivot=tuple(e),
               rot=(0, 0, ang) if ang else None)
    m.bones["myc7_2"].locators["antenna"] = tuple(e)


# ============================================================================= materials (gate A: flat placeholders)

def _P(ctx, k):
    return ctx.params.get(k, 0.0)


def _flat(hexc, glow=0.0, k=0.6):
    col = px.col(hexc)

    def mat(ctx):
        lv = px.light(ctx, grad=0.0)
        c = col[None, :] * (0.55 + k * lv)[:, None]
        if _P(ctx, "burn") > 0.5:
            g = c.mean(axis=1, keepdims=True)
            c = g * np.array([0.9, 0.7, 0.6])[None, :]
        return c, ctx.ones(), np.full(ctx.N, glow)
    return mat


RING_HEX = ["#9effd8", "#86f7e0", "#6eeaf0", "#62d2fa", "#6cb4ff", "#8a96ff", "#a67cff", "#c066f5", "#d95ae6",
            "#ee58d2", "#ff5fbf"]


def _dome_proxy():
    """(centre, radii) of the ellipsoid the dome's bands approximate (its crown leans with the skew)."""
    return ((CAP_C[0] + CAP_SKEW[0] * 0.45, RIM_Y - 0.5, CAP_C[2] + CAP_SKEW[1] * 0.45), (10.0, 9.5, 9.6))


def engine_level(n) -> np.ndarray:
    """The vertical part of Minecraft entity lighting (top 1.0, sides ~0.72, bottom ~0.45) for normals n."""
    ny = np.atleast_2d(n)[:, 1]
    return np.where(ny >= 0, 0.72 + 0.28 * ny, 0.72 + 0.27 * ny)


def smooth_normals(ctx, center, radii) -> np.ndarray:
    p = ctx.wp if ctx.wp is not None else ctx.p
    d = (p - np.asarray(center, float)) / np.asarray(radii, float) ** 2
    return d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)


def face_comp(ctx, center, radii, gain: float = 1.0) -> np.ndarray:
    """Level offset that cancels the engine's per-face light on a stacked smooth form: risers
    near a crown are lifted, the tops of low terraces lowered, so the bands read as one surface."""
    wn = ctx.wn if ctx.wn is not None else ctx.n
    return gain * (engine_level(smooth_normals(ctx, center, radii)) - engine_level(wn)[0])


def _cap(ctx):
    c0, r0 = _dome_proxy()
    pal = px.pal("#2a1d6e", "#4b31a8", "#7552d6", "#a88cf0")
    if _P(ctx, "burn") > 0.5:
        pal = px.pal("#1c1518", "#3a2c2e", "#5c4642", "#86685c")
    return (px.soft_shade(ctx, pal, 0.0, ellipsoid=(c0, r0), k=0.9, up=0.0, down=0.0, extra=face_comp(ctx, c0, r0, 1.7)),
            ctx.ones(), ctx.zeros())


def petal_alpha(ctx, width_at: float = 0.45, base: float = 0.28):
    """Almond petal on a lid plate: v = 0 at the hinge .. 1 at the free end; widest at width_at."""
    u = ctx.local[:, 0] * 2 - 1
    v = 1 - ctx.local[:, 1]
    prof = np.where(v < width_at, base + (1 - base) * np.sin(np.clip(v / width_at, 0, 1) * np.pi / 2),
                    np.cos(np.clip((v - width_at) / (1 - width_at), 0, 1) * np.pi / 2) ** 0.85)
    return (np.abs(u) <= prof * 0.97).astype(float)


def _lid(ctx):
    lv = px.light(ctx, grad=0.0)
    c = px.col("#e6d6ff")[None, :] * (0.65 + 0.45 * lv)[:, None]
    return c, petal_alpha(ctx), ctx.zeros()


def _fan(ctx):
    a, lvl = px.vane(ctx, width_at=0.38, tip=0.98, base=0.35, rachis=0.1, barb=3.0)
    c = px.col("#bfe9ff")[None, :] * (0.8 + lvl)[:, None]
    return c, a, ctx.zeros()


def _lattice(ctx):
    ix, iy, W, H = px.texel(ctx)
    a = (((ix + iy) % 4) < 2).astype(float)
    c = px.col("#e3d9f7")[None, :] * (0.6 + 0.4 * px.light(ctx, grad=0.0))[:, None]
    return c, a, ctx.zeros()


def materials():
    mats = {
        "cap": _cap, "frill": _flat("#86f5d2", 0.5), "gill": _flat("#7cf2cf", 0.6),
        "spore": _flat("#ffd27a", 0.7), "void": _flat("#0d0a24", 0.0), "star": _flat("#ffffff", 0.95),
        "lid": _lid, "ray": _flat("#b9a2ff", 0.7), "core": _flat("#7ff2ff", 0.8), "lattice": _lattice,
        "volva": _flat("#4a2f8e", 0.0), "hy_m": _flat("#e8def8"), "hy_f": _flat("#e0ecfa"), "hy_s": _flat("#e6e0fa"),
        "hy_p": _flat("#efe2f2"), "hy_b": _flat("#dfeaf7"), "hy_a": _flat("#e2e6fa"), "grip": _flat("#ff8fd0", 0.6),
        "fan": _fan, "bulb": _flat("#8ff6ff", 0.8), "feeler": _flat("#bff8ff", 0.5), "pod": _flat("#f1e2d0"),
        "pod_mouth": _flat("#ffd27a", 0.7), "crystal": _flat("#9ffcff", 0.85), "tendril_fp": _flat("#e8def8"),
        "accent": mat_accent,
    }
    for k in range(RINGS):
        mats[f"ring{k}"] = _flat(RING_HEX[k], 0.8)
    return mats
