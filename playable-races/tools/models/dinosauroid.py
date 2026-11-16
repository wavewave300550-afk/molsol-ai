"""Race 007 - The Unknown Dinosauroid.  (v1.5 premium redesign: "the misbred feathered sovereign")

A magnificent feathered impossibility: a powerful theropod leaning forward over strong
thighs, a deep keeled chest under a regal ruff, an S-neck carrying a long skull with a
hollow hadrosaur crest sweeping far back over the head, forearms folded as iridescent wings,
and a long tapering tail that ends in a broad fan of individual eyed feathers.

Big shapes first - beveled ellipsoid masses (trunk, skull, thighs), swept forms (neck, tail,
crest, horns, beak, claws), feather fans with one bone per feather where they must open -
and the fine detail (barbs, scales, teeth, plate bevels, banding) lives in the textures.

  * skull   - an enlarged braincase; a deep hooked oviraptorosaur beak (glossy black, ivory
              tip) with a row of teeth behind it; ASYMMETRIC supraorbital horns (the right long
              and curving forward, the left a blunt stump); the hollow tubular crest with a
              flared open end; plume tufts behind the eyes; a throat pouch; big amber eyes with
              slit pupils and a nictitating membrane
  * arms    - a folded wing: secondaries along the forearm, three long primaries from the hand
              reaching the hips; two clawed fingers and the elongated styliform digit (a long
              ivory spike from the wrist along the wing's leading edge)
  * legs    - digitigrade runners: a raised sickle claw on digit II; Microraptor feathers on
              the shank and the metatarsus; hip-to-ankle membranes on two jointed rods
              (folded against the leg at rest, wide sails in the Veer and the Overflow)
  * tail    - five bones; osteoderm plates, Psittacosaurus bristles and a frond of side
              feathers; a fan of nine eyed feathers (each its own bone: it opens and closes)

Rig: the head sits far ahead of the player's head pivot, so the animations cancel the player's
look on head_g (pitch) and hfix (yaw) and re-apply it on the neck (see anims/dinosauroid.py).

Variants: base | night (display skin luminous) | display (Crest of Misclassification) |
veer (Hindwing Veer) | overflow (Taxonomic Error: everything open, everything lit).
"""
from __future__ import annotations

import math

import numpy as np

from kit.geo import Model, rot_matrix
from kit import pixel as px
from models.common import (accents, fp_sleeves, frame_rot, humanoid, lathe, mat_accent, plate_row, q,
                           side_rot, sweep)

ID = "dinosauroid"
VARIANTS = ["base", "night", "display", "veer", "overflow"]
TEXTURES = {
    "base": {"night": 0.0, "overflow": 0.0},
    "night": {"night": 1.0, "overflow": 0.0},
    "overflow": {"night": 0.6, "overflow": 1.0},
}
VARIANT_TEXTURE = {"base": "base", "night": "night", "display": "base", "veer": "base", "overflow": "overflow"}
OPEN = {"display", "overflow"}        # crest raised, pouch inflated, arm fans and tail fan spread
WINGS = {"veer", "overflow"}          # hindlimb sails and leg feathers deployed
SIDES = ((-1, "r"), (1, "l"))
TAIL = 5                              # tail bones tail0..tail4
FAN = 9                               # tail-fan feathers fan0..fan8

# ----------------------------------------------------------------------------- anatomy (JSON model units, rest pose)
TRUNK_PIVOT = (0.0, 12.75, 2.25)      # the hips: the trunk pitches forward about them
PITCH = 36.0                          # theropod posture (trunk axis from vertical)
VEER_LEAN = 20.0                      # extra lean of the Hindwing Veer
# the trunk: one rounded lathe mass in the upright trunk frame - (height above the pivot, radius)
TRUNK_PROFILE = [(-2.25, 2.75), (0.25, 3.9), (3.0, 4.5), (6.0, 4.6), (8.5, 3.9), (10.25, 2.75)]
TRUNK_SQUASH = (0.92, 1.06)           # x (width) and z (depth: the deep keeled chest)
TRUNK_SKEW = (0.0, -1.25)             # the chest bulges forward
NECK = [(0.0, 19.25, -2.0), (0.0, 22.5, -4.5), (0.0, 25.5, -5.25), (0.0, 28.0, -4.5)]
NECK_BASE = NECK[0]
RUFF_C = (0.0, 23.75, -4.25)          # the ruff ring round the neck, just above the shoulders
SKULL_PIVOT = NECK[-1]
HS = 1.15                             # the head is authored at a base size and scaled about the skull pivot
CRANIUM_A = ((0.0, 28.5, -6.5), [(0.0, 2.25), (1.25, 2.9), (2.75, 3.0), (3.75, 2.6), (4.75, 1.6)])   # dome (authored)
CRANIUM_SQUASH = (0.9, 1.15)
EYE_A = (2.2, 30.4, -8.25)
BEAK_A = [(0.0, 30.25, -10.5), (0.0, 30.1, -12.25), (0.0, 29.1, -13.65), (0.0, 27.6, -14.1)]
EYE_RY = 16.0
CREST_A = [(0.0, 31.0, -10.75), (0.0, 32.9, -8.75), (0.0, 33.9, -6.0), (0.0, 34.6, -2.75), (0.0, 34.8, 0.5),
           (0.0, 34.4, 3.0)]
SHOULDER = (3.75, 19.5, -2.5)
ELBOW = (5.0, 16.25, -0.25)
WRIST = (5.75, 13.0, -2.25)
SPUR = (6.5, 17.75, 4.75)             # tip of the styliform digit (the folded wing's upper spar)
HIP = (3.0, 13.0, 1.5)
KNEE = (3.25, 7.75, -2.0)
ANKLE = (3.25, 3.75, 3.0)
BALL = (3.25, 0.75, 0.5)
TAIL_PTS = [(0.0, 14.5, 4.25), (0.0, 15.0, 7.75), (0.0, 15.75, 11.25), (0.0, 16.25, 14.5), (0.0, 16.5, 17.5),
            (0.0, 16.25, 20.25)]
FAN_LEN = [9.5, 9.75, 10.0, 10.25, 10.5, 10.25, 10.0, 9.75, 9.5]
FAN_W = 2.75
FAN_DROOP = -14.0                     # the folded fan trails a little below the tail line
FAN_CUP = 22.0                        # the outer feathers droop this much (a shallow dome)
FAN_FOLD = 56.0                       # folded fan: total spread (degrees)
FAN_OPEN = 176.0                      # display: total spread (a full half-wheel)


def _v(p):
    return np.asarray(p, float)


def _x(p, s):
    """A right-side-authored point (x given as a positive distance) placed on side s (-1 right, +1 left)."""
    return (s * abs(p[0]), p[1], p[2])


def trunk_to_world(p, pitch=PITCH):
    """Where a point given in the upright trunk frame sits once the trunk pitches forward."""
    piv = _v(TRUNK_PIVOT)
    return tuple(piv + rot_matrix((pitch, 0, 0)) @ (_v(p) - piv))


def world_to_trunk(p, pitch=PITCH):
    piv = _v(TRUNK_PIVOT)
    return tuple(piv + rot_matrix((pitch, 0, 0)).T @ (_v(p) - piv))


def lean_offset(p, deg, pivot=TRUNK_PIVOT):
    """Displacement of world point p when the trunk leans `deg` further forward about the hips."""
    piv = _v(pivot)
    v = _v(p) - piv
    return tuple(np.round(rot_matrix((deg, 0, 0)) @ v - v, 3))


def _dir(a, b):
    d = _v(b) - _v(a)
    return d / max(np.linalg.norm(d), 1e-9)


def _unit(v):
    v = _v(v)
    return v / max(np.linalg.norm(v), 1e-9)


def oell(m, bone, center, dims, along, normal, mat, a=0.7, b=0.88, **kw):
    """A beveled ellipsoid (cross of three boxes + a core) whose local Z runs along `along` and
    local Y along `normal`: dims = (x, y, z) in that frame.  No two faces coplanar."""
    c = _v(center)
    rot = frame_rot(along, normal) if along is not None else None
    dx, dy, dz = dims
    out, seen = [], set()
    for sz in ((dx, dy * a, dz * a), (dx * a, dy, dz * a), (dx * a, dy * a, dz), (dx * b, dy * b, dz * b)):
        s = tuple(q(v) for v in sz)
        while s in seen:
            s = (s[0] - 0.5, s[1], s[2])
        seen.add(s)
        out.append(m.cube(bone, tuple(c - _v(s) / 2), s, mat, pivot=tuple(c) if rot else None, rot=rot, **kw))
    return out


def olathe(m, bone, base, axis, profile, mat, sides=8, squash=(1.0, 1.0), front=(0, 0, -1), step=0.5, **kw):
    """common.lathe() along an arbitrary `axis` from `base` (profile = [(distance along the axis,
    radius), ...]); squash scales the cross-section along `front` (z) and across it (x).  Each
    strip keeps the lathe's stagger (no coplanar faces).  Returns the cubes."""
    from models.common import euler_for
    yax = _unit(axis)
    zax = _unit(_v(front) - yax * float(_v(front) @ yax))
    xax = np.cross(yax, zax)
    F = np.column_stack([xax, yax, zax])
    out = []
    for i in range(len(profile) - 1):
        (y0, r0), (y1, r1) = profile[i], profile[i + 1]
        r = (r0 + r1) / 2
        h = q(y1 - y0, step / 2)
        apo = r * math.cos(math.pi / sides)
        edge = 2 * r * math.sin(math.pi / sides)
        for k in range(sides // 2):
            ang = 360.0 / sides * k
            a_r = math.radians(ang)
            sq = math.hypot(squash[0] * math.sin(a_r), squash[1] * math.cos(a_r))
            sx, sz = q(edge * sq + 0.25, step / 2), q(2 * apo * sq, step / 2)
            e = 0.02 * k
            piv = _v(base) + yax * (y0 - e)
            R = F @ rot_matrix((0.0, ang, 0.0))
            out.append(m.cube(bone, tuple(piv - _v((sx / 2, 0.0, sz / 2))), (sx, h + 2 * e, sz), mat, pivot=tuple(piv),
                              rot=tuple(_wrap(a) for a in euler_for(R)), **kw))
    return out


def vane_cube(m, bone, origin, direction, normal, length, width, mat, thick=0.25, **kw):
    """One feather / blade box: `width` across, `thick` through its plane (normal), `length`
    along `direction` from `origin` (local +Z along the feather: paint with px.vane)."""
    o = _v(origin)
    return m.cube(bone, (o[0] - q(width) / 2, o[1] - thick / 2, o[2]), (q(width), thick, q(length)), mat,
                  pivot=tuple(o), rot=frame_rot(direction, normal), **kw)


def panel(m, bone, top, length, width, mat, **kw):
    """A vertical zero-thickness panel in the YZ plane: hanging `length` down from `top` and
    `width` back (+Z) from it (membranes: solid, so their luminous rims can glow)."""
    x, y, z = top
    return m.cube(bone, (x, y - length, z), (0.0, length, width), mat, faces={"east", "west"}, **kw)


def _wrap(a):
    a = (a + 180.0) % 360.0 - 180.0
    return 180.0 if a <= -180.0 + 1e-9 else round(a, 2) + 0.0


def _tidy_angles(m: Model) -> None:
    """Bedrock wants angles in (-180, 180]: frame_rot / euler_for may return exactly -180."""
    for bn in m.order:
        b = m.bones[bn]
        b.rot = tuple(_wrap(a) for a in b.rot)
        for v, (off, r) in list(b.variant.items()):
            if r is not None:
                b.variant[v] = (off, tuple(_wrap(a) for a in r))
        for c in b.cubes:
            if c.rot is not None:
                c.rot = tuple(_wrap(a) for a in c.rot)


def _frame(d, n):
    """Orthonormal frame (columns x, y, z) with z along d and y along n (made orthogonal)."""
    z = _unit(d)
    y = _v(n) - z * float(_v(n) @ z)
    if np.linalg.norm(y) < 1e-6:
        y = _v((0, 1, 0)) - z * z[1]
    y = _unit(y)
    return np.column_stack([np.cross(y, z), y, z])


def aim(m: Model, bone: str, variant, ref_dir, ref_nrm, tgt_dir, tgt_nrm, offset=(0.0, 0.0, 0.0)) -> None:
    """Pose `bone` in `variant` (None: its rest rotation) so that a feature authored along
    ref_dir with plane normal ref_nrm (rest model space) points along tgt_dir / tgt_nrm in the
    world, given its parents' pose in that variant.  Set parents before children."""
    from kit.render import bone_matrices
    from models.common import euler_for
    par = m.bones[bone].parent
    P = bone_matrices(m, variant)[par][:3, :3] if par else np.eye(3)
    R = P.T @ _frame(tgt_dir, tgt_nrm) @ _frame(ref_dir, ref_nrm).T
    e = tuple(_wrap(a) for a in euler_for(R))
    if variant is None:
        m.bones[bone].rot = e
    else:
        m.bones[bone].variant[variant] = (tuple(offset), e)


def in_plane(theta, s, n):
    """Direction at `theta` degrees in the plane facing n: 0 = straight down, 90 = outward (side s)."""
    t = math.radians(theta)
    d = _v((s * math.sin(t), -math.cos(t), 0.0))
    n = _unit(n)
    return _unit(d - n * float(d @ n))


# ============================================================================= build

def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=256)
    humanoid(m)
    # the player's look is cancelled here (pitch on head_g, yaw on hfix, both about the player's
    # head pivot) and re-applied on the neck, which pivots where the neck leaves the chest
    m.bone("hfix", "head_g", (0, 24, 0))
    m.bones["hfix"].variant["veer"] = (lean_offset(NECK_BASE, VEER_LEAN), None)
    for s, g in ((-1, "r_arm_g"), (1, "l_arm_g")):
        m.bones[g].variant["veer"] = (lean_offset(_x(SHOULDER, s), VEER_LEAN), None)
    _trunk(m)
    _neck_head(m)
    _arms(m)
    _legs(m)
    _tail(m)
    fp_sleeves(m, "sleeve", width=4.4)
    accents(m, [
        ("c", "breast", "trunk", (0, 18.5, -3.6), (4.5, 4.0, 0.5)),
        ("l", "r", "r_thigh", (-5.25, 10.5, -0.25), (0.5, 3.5, 3.5)),
        ("l", "l", "l_thigh", (5.25, 10.5, -0.25), (0.5, 3.5, 3.5)),
        ("f", "r", "r_meta", (-3.25, 2.25, 1.75), (2.0, 1.0, 2.0)),
        ("f", "l", "l_meta", (3.25, 2.25, 1.75), (2.0, 1.0, 2.0)),
    ])
    _tidy_angles(m)
    m.pack()
    return m


# ----------------------------------------------------------------------------- trunk: a deep keeled chest, pitched forward

def _trunk(m: Model) -> None:
    t = m.bone("trunk", "torso_g", TRUNK_PIVOT, (PITCH, 0, 0))
    t.variant["veer"] = ((0, 0, 0), (PITCH + VEER_LEAN, 0, 0))
    # one rounded mass from the pelvis to the shoulders (upright trunk frame), its deep chest
    # bulging forward (skew): lit as one form in the texture (trunk_proxy)
    lathe(m, t.name, TRUNK_PIVOT, TRUNK_PROFILE, "plume", sides=12, squash=TRUNK_SQUASH, skew=TRUNK_SKEW)
    # ankylosaur osteoderms down the spine (upright trunk frame: +Z is the back)
    px_, py, pz = TRUNK_PIVOT
    plate_row(m, t.name, (0, py + 9.5, pz + 3.25), (0, py + 2.5, pz + 4.5), 4, 1.5, 2.25, 1.75, 0.5, "osteo",
              normal=(0, 0, 1), tilt=14, arch=0.4)
    t.locators["chest"] = (0, py + 4.5, pz - 5.0)


# ----------------------------------------------------------------------------- neck and head

def H(p):
    """Head geometry is authored at a base size and scaled HS about the skull pivot."""
    piv = _v(SKULL_PIVOT)
    return tuple(piv + HS * (_v(p) - piv))


def HZ(size, step=0.5):
    return tuple(q(v * HS, step) if v > 0 else 0.0 for v in size)


CRANIUM = (H(CRANIUM_A[0]), [(h * HS, r * HS) for h, r in CRANIUM_A[1]])
EYE = tuple(np.round(H(EYE_A), 3))
JAW_PIVOT = H((0.0, 28.5, -6.0))
GULAR_PIVOT = H((0.0, 28.0, -7.0))
CREST = [H(p_) for p_ in CREST_A]


def _neck_head(m: Model) -> None:
    sweep(m, "hfix", "neck", NECK, 4.5, 3.25, "neck", h0=5.0, h1=3.5, n=3, per_bone=5)
    # n=3 over 3 spans -> 9 cubes; per_bone=5 -> neck0 (lower S), neck1 (upper S)
    # the regal ruff: a mantle of plumes round the base of the neck, over the shoulders
    rc = _v(RUFF_C)
    na = m.bone("nape", "neck0", tuple(rc))
    na.variant.update({v: ((0, 0, 0), (22.0, 0, 0)) for v in OPEN})
    for k, (ang, ln, w) in enumerate(((0.0, 7.5, 3.75), (-42.0, 7.5, 3.75), (42.0, 7.5, 3.75), (-84.0, 7.0, 3.5),
                                      (84.0, 7.0, 3.5), (-124.0, 5.5, 3.0), (124.0, 5.5, 3.0))):
        a = math.radians(ang)
        out = _v((math.sin(a), 0.0, math.cos(a)))                  # 0 = straight back, + = toward +X
        o = rc + out * (2.0 + 0.04 * k) + _v((0, 0.3 * (k % 3), 0))
        d = _unit(out * 0.9 + _v((0, -0.44, 0)))
        vane_cube(m, na.name, o, d, out + _v((0, 0.45, 0)), ln, w, "ruff", cutout=True)
    sk = m.bone("skull", "neck1", SKULL_PIVOT)
    sk.variant.update({"display": ((0, 0, 0), (-14.0, 0, 0)), "overflow": ((0, 0, 0), (-8.0, 0, 6.0))})
    # the braincase: a rounded dome (lathe), a tapering snout, cheeks; brow ridges overhang the eyes
    cb, prof = CRANIUM_A
    lathe(m, sk.name, H(cb), [(h * HS, r * HS) for h, r in prof], "skull", sides=12, squash=CRANIUM_SQUASH)
    sweep(m, sk.name, "snout", [H((0, 30.25, -8.25)), H((0, 30.25, -10.75))], 3.25 * HS, 2.75 * HS, "face",
          h0=3.25 * HS, h1=3.0 * HS, n=1, bones=False)
    m.box(sk.name, H((0, 29.0, -8.0)), HZ((4.0, 2.0, 3.0)), "face")                    # cheeks under the eyes
    for s in (-1, 1):
        c_ = H((s * 2.1, 31.6, -8.1))
        m.cube(sk.name, tuple(_v(c_) - _v(HZ((1.25, 0.75, 3.0))) / 2), HZ((1.25, 0.75, 3.0)), "brow", pivot=c_,
               rot=side_rot((0, -EYE_RY, 8), s))
    # the beak: deep at the base, tapering to a clearly hooked point (oviraptorosaur)
    sweep(m, sk.name, "beak", [H(p_) for p_ in BEAK_A], 2.75 * HS, 0.5, "beak", h0=3.0 * HS, h1=0.5, n=2, bones=False,
          power=0.85)
    # a row of teeth behind the beak (cutout planes hanging from the upper jaw line)
    for s in (-1, 1):
        o = H((s * 1.45, 28.5, -11.25))
        m.cube(sk.name, (o[0], o[1] - 1.0, o[2]), (0.0, 1.0, q(3.75 * HS)), "teeth", cutout=True, faces={"east", "west"})
    # ASYMMETRIC supraorbital horns from the brow ridges: the right long and curving forward, the left a blunt stump
    sweep(m, sk.name, "rhorn", [H(p_) for p_ in ((-1.9, 31.9, -8.4), (-2.3, 33.25, -9.0), (-2.5, 34.5, -10.25),
                                                  (-2.25, 35.0, -11.75))], 1.75, 0.5, "horn", n=1, bones=False)
    sweep(m, sk.name, "lhorn", [H(p_) for p_ in ((1.9, 31.9, -8.4), (2.1, 32.9, -8.9))], 1.75, 1.25, "horn", n=1,
          bones=False)
    # jaw
    jw = m.bone("jaw", sk.name, JAW_PIVOT)
    jw.variant.update({"display": ((0, 0, 0), (10.0, 0, 0)), "overflow": ((0, 0, 0), (14.0, 0, 0))})
    sweep(m, jw.name, "jawb", [H(p_) for p_ in ((0, 28.25, -6.75), (0, 28.0, -10.0), (0, 27.55, -13.0))], 3.25 * HS, 0.75,
          "jaw", h0=1.5 * HS, h1=0.6, n=1, bones=False)
    # eyes: big, amber, turned a little forward; slit pupils; a nictitating membrane
    ew, eh, ed = 0.5, q(2.0 * HS, 0.25), q(2.25 * HS, 0.25)
    for s, p in SIDES:
        ex, ey, ez = s * EYE[0], EYE[1], EYE[2]
        m.cube(sk.name, (ex - ew / 2, ey - eh / 2, ez - ed / 2), (ew, eh, ed), "eye", ppu=4.0,
               pivot=(ex, ey, ez), rot=side_rot((0, -EYE_RY, 0), s))
    pu = m.bone("pupils", sk.name, (0, EYE[1], EYE[2]))
    nc = m.bone("nict", sk.name, (0, EYE[1], EYE[2] - ed / 2 + 0.1))
    for s, p in SIDES:
        ex, ey, ez = s * EYE[0], EYE[1], EYE[2]
        m.cube(pu.name, (ex + s * 0.27 - 0.05, ey - 0.875, ez - 0.25), (0.1, 1.75, 0.5), "pupil", ppu=4.0,
               pivot=(ex, ey, ez), rot=side_rot((0, -EYE_RY, 0), s))
        m.cube(nc.name, (ex + s * 0.31 - 0.025, ey - eh / 2, ez - ed / 2 + 0.1), (0.05, eh, 0.1), "nict",
               pivot=(ex, ey, ez), rot=side_rot((0, -EYE_RY, 0), s))
    sk.locators["eyes"] = (0, EYE[1], EYE[2] - 1.5)
    # throat pouch: tucked under the jaw at rest, a balloon in the display
    gu = m.bone("gular", sk.name, GULAR_PIVOT)
    oell(m, gu.name, H((0, 27.25, -8.0)), HZ((3.0, 2.0, 3.75)), None, None, "gular", a=0.66, b=0.86, skip=OPEN)
    lathe(m, gu.name, H((0, 22.5, -8.25)), [(0.0, 0.9), (0.75, 2.25), (2.0, 3.0), (3.5, 3.0), (4.75, 2.25), (5.5, 1.0)],
          "gular_big", sides=8, squash=(0.92, 1.1), only=OPEN)
    gu.locators["throat"] = H((0, 25.5, -8.25))
    # the hollow tubular crest: from the snout over the skull roof, sweeping far behind
    sweep(m, sk.name, "crest", CREST[:4], 3.0, 1.75, "crest", h0=3.0, h1=1.75, n=2, per_bone=6, power=0.7)
    c1 = m.bone("crest1", "crest0", CREST[3])
    sweep(m, c1.name, "crestb", CREST[3:], 1.75, 2.0, "crest", h0=1.75, h1=2.0, n=2, bones=False, power=2.0)
    m.bones["crest0"].variant.update({"display": ((0, 0, 0), (16.0, 0, 0)), "overflow": ((0, 0, 0), (11.0, 0, 0))})
    c1.variant.update({"display": ((0, 0, 0), (10.0, 0, 0)), "overflow": ((0, 0, 0), (7.0, 0, 0))})
    tip = _v(CREST[-1])
    d = _dir(CREST[-2], CREST[-1])
    vane_cube(m, c1.name, tip - d * 1.25, d, (0, 1, 0), 0.75, 2.5, "crest_end", thick=2.5)         # the flared open end:
    vane_cube(m, c1.name, tip - d * 0.5, d, (0, 1, 0), 0.75, 3.25, "crest_end", thick=3.25)        # a two-step bell
    c1.locators["crest_tip"] = tuple(np.round(tip + d * 0.9, 3))
    # plume tufts behind the eyes: one long plume per side sweeping back
    for s, p in SIDES:
        o = _v(H((s * 2.25, 31.5, -5.25)))
        tf = m.bone(f"{p}_tuft", sk.name, tuple(o))
        tf.variant.update({v: ((0, 0, 0), side_rot((30, -24, 0), s)) for v in OPEN})
        vane_cube(m, tf.name, o, _unit((0.16 * s, 0.3, 1.0)), (1, 0, 0), 8.0, 1.75, "tuft", cutout=True)


# ----------------------------------------------------------------------------- arms: folded wings with three digits

def _arms(m: Model) -> None:
    for s, p in SIDES:
        g = f"{p}_arm_g"
        sh, el, wr = (_v(_x(c, s)) for c in (SHOULDER, ELBOW, WRIST))
        # the arm itself never leaves the player's arm (held items stay in the hand): only the
        # wing feathers and the styliform digit open in the display forms
        up = m.bone(f"{p}_upper", g, tuple(sh))
        oell(m, up.name, (sh + el) / 2 + (0, 0.25, 0), (2.75, 2.75, 5.0), el - sh, (1, 0, 0), "plume", a=0.7, b=0.88)
        fo = m.bone(f"{p}_fore", up.name, tuple(el))
        sweep(m, fo.name, f"{p}_fa", [el, wr], 2.0, 1.5, "plume", n=1, bones=False)
        ha = m.bone(f"{p}_hand", fo.name, tuple(wr))
        m.box(ha.name, tuple(wr + (0.1 * s, -1.0, -0.4)), (1.5, 2.0, 2.0), "scale")
        for dx, dz, ln in ((-0.4, -0.5, 2.25), (0.45, -0.25, 2.0)):
            a = wr + (dx * s, -1.75, dz - 0.4)
            sweep(m, ha.name, f"{p}_cl", [a, a + (0, -ln * 0.7, -ln * 0.45), a + (0, -ln, -ln * 0.3)], 0.6, 0.35, "claw",
                  n=1, bones=False)
        # the styliform digit: a long ivory spar from the wrist up and back over the hip; the primaries
        # hang from it (as the membrane of Yi qi hung from its styliform element)
        st = m.bone(f"{p}_stylus", ha.name, tuple(wr))
        spur = _v(_x(SPUR, s))
        sweep(m, st.name, f"{p}_st", [wr + (0.55 * s, 0.25, 0.25), (wr + spur) / 2 + (0.2 * s, 0.25, 0), spur], 0.9, 0.4,
              "spike", n=1, bones=False)
        n_w = _unit((s * 0.86, 0.5, 0.0))                        # folded feathers face up-out (seen from behind too)
        # folded wing: three secondaries fanned along the forearm, three long primaries along the spar
        sec = m.bone(f"{p}_sec", fo.name, tuple(el))
        sec_ref = _unit((0.05 * s, 0.0, 1.0))
        for k, (t, ln) in enumerate(((0.12, 6.75), (0.42, 7.25), (0.72, 7.75))):
            o = el + (wr - el) * t + (0.45 * s + 0.12 * k * s, 0, 0)
            vane_cube(m, sec.name, o, _unit((0.05 * s, 0.25 * (1 - k), 1.0)), n_w, ln, 2.75, "flight", cutout=True)
        pri_dir = []
        for k, (t, ln, drop) in enumerate(((0.35, 8.25, -0.2), (0.65, 9.25, -0.3), (0.95, 9.75, -0.38))):
            o = wr + (spur - wr) * t + (0.15 * s, -0.25, 0)
            pr = m.bone(f"{p}_pri{k}", st.name, tuple(o))
            d = _unit((0.2 + 0.06 * k) * s * _v((1, 0, 0)) + _v((0, drop, 1.0)))
            pri_dir.append(d)
            vane_cube(m, pr.name, o + (0.1 * k * s, 0, 0), d, n_w, ln, 2.75, "flight", cutout=True)
        # display: each wing opens as a fan facing forward that rises from the wrist up the flank, so the
        # two wings frame the body (bird-of-paradise); overflow: half-open and drooping
        ex = _v((1, 0, 0))
        n_d = _unit((s * 0.25, 0.0, -1.0))
        sp_ref = spur - wr
        aim(m, sec.name, "display", sec_ref, n_w, in_plane(70, s, n_d), n_d)
        aim(m, st.name, "display", sp_ref, ex, in_plane(160, s, n_d), n_d)
        for k in range(3):
            aim(m, f"{p}_pri{k}", "display", pri_dir[k], n_w, in_plane(98 + 18 * k, s, n_d), n_d)
        n_o = _unit((s * 1.0, 0.2, 0.25))

        def droop(t):
            a = math.radians(t)
            return _unit(_v((s * 0.42, 0.0, 0.0)) + _v((0, 0, 1)) * math.cos(a) + _v((0, -1, 0)) * math.sin(a))
        aim(m, sec.name, "overflow", sec_ref, n_w, droop(30), n_o)
        aim(m, st.name, "overflow", sp_ref, ex, _unit((s * 0.55, 0.75, 0.75)), n_o)
        for k in range(3):
            aim(m, f"{p}_pri{k}", "overflow", pri_dir[k], n_w, droop(12 + 16 * k), n_o)


# ----------------------------------------------------------------------------- legs: digitigrade runners with hindwings

def _legs(m: Model) -> None:
    for s, p in SIDES:
        g = f"{p}_leg_g"
        hip, knee, ankle, ball = (_v(_x(c, s)) for c in (HIP, KNEE, ANKLE, BALL))
        th = m.bone(f"{p}_thigh", g, tuple(hip))
        top = hip + (0.1 * s, 2.25, 1.25)
        oell(m, th.name, (top + knee) / 2 + (0.15 * s, 0, 0.25), (4.5, 5.5, 8.5), knee - top, (0, 0, -1), "thigh",
             a=0.7, b=0.88)
        sh = m.bone(f"{p}_shin", th.name, tuple(knee))
        sweep(m, sh.name, f"{p}_sn", [knee + (0, 0.75, -0.25), ankle], 2.75, 1.75, "shin", h0=3.0, h1=1.75, n=1, bones=False)
        mt = m.bone(f"{p}_meta", sh.name, tuple(ankle))
        sweep(m, mt.name, f"{p}_mt", [ankle + (0, 0.25, 0.1), ball], 1.75, 1.5, "scale", n=1, bones=False)
        ft = m.bone(f"{p}_foot", mt.name, tuple(ball))
        bx, by, bz = ball
        sweep(m, ft.name, f"{p}_d3", [(bx, 0.6, bz), (bx, 0.5, bz - 2.0), (bx, 0.4, bz - 3.75)], 1.25, 0.75, "toe",
              h0=1.0, h1=0.75, n=1, bones=False)
        sweep(m, ft.name, f"{p}_d4", [(bx + 0.4 * s, 0.6, bz), (bx + 1.3 * s, 0.45, bz - 2.5)], 1.0, 0.75, "toe",
              h0=0.9, h1=0.7, n=1, bones=False)
        m.box(ft.name, (bx - 0.4 * s, 0.5, bz + 1.0), (1.0, 1.0, 1.5), "toe")                    # hallux
        # digit II: raised, carrying the enlarged sickle claw
        tx = bx - 0.8 * s
        tl = m.bone(f"{p}_talon", ft.name, (tx, 0.75, bz))
        sweep(m, tl.name, f"{p}_d2", [(tx, 0.75, bz), (tx, 1.5, bz - 1.25)], 0.9, 0.75, "toe", n=1, bones=False)
        sweep(m, tl.name, f"{p}_sk", [(tx, 1.4, bz - 1.25), (tx, 2.85, bz - 1.75), (tx, 3.1, bz - 2.85), (tx, 2.25, bz - 3.75)],
              0.85, 0.35, "sickle", h0=1.0, h1=0.4, n=1, bones=False)
        tl.locators[f"{p}_sickle"] = (tx, 2.5, bz - 3.0)
        # Microraptor feathers: long feathers down the back of the shank ...
        sf = m.bone(f"{p}_sfan", sh.name, tuple(knee + (0.75 * s, -0.5, 1.0)))
        for k, (t, ln) in enumerate(((0.1, 7.0), (0.4, 7.5), (0.7, 6.5))):
            o = knee + (ankle - knee) * t + (0.8 * s + 0.1 * k * s, 0, 0.5)
            vane_cube(m, sf.name, o, _unit((0.0, -0.36 + 0.06 * k, 1.0)), (1, 0, 0), ln, 2.25, "flight", cutout=True)
        # ... and a metatarsal fan behind the ankle
        lf = m.bone(f"{p}_lfan", mt.name, tuple(ankle + (0.5 * s, 0, 0.5)))
        for k, ln in enumerate((6.0, 5.5, 4.75)):
            o = ankle + (0.5 * s + 0.1 * k * s, -0.5 * k, 0.5)
            vane_cube(m, lf.name, o, _unit((0.0, -0.08 - 0.12 * k, 1.0)), (1, 0, 0), ln, 2.0, "flight", cutout=True)
        # the hindwing: a folding fan of membrane hinged at the hip - jointed rods, the first running down
        # the leg to the ankle, wedges of membrane between them, a luminous rim along the outer edge.
        # Folded at rest (one rod and a strip of membrane behind the thigh), opened in the WINGS forms.
        hinge = hip + (1.5 * s, 1.0, 1.25)
        sl = m.bone(f"{p}_sail", th.name, tuple(hinge))
        _hindwing(m, sl.name, hinge, ankle + (0.9 * s, 0.0, 0.0), s)
        ex, ey, ez = _v((1, 0, 0)), _v((0, 1, 0)), _v((0, 0, 1))
        # the leg feathers open as horizontal hindwings
        for v in WINGS:
            aim(m, sf.name, v, (0, -0.3, 1.0), ex, (s * 0.8, -0.12, 0.62), ey)
            aim(m, lf.name, v, (0, -0.2, 1.0), ex, (s * 0.88, -0.06, 0.48), ey)


RODS = 4                              # hindwing fan: rods (3 membrane wedges between them)
HW_SPREAD = (8.0, 112.0)              # open: angle of the first and last rod from straight down toward outward


def hindwing_plane(s):
    """Open hindwing fan plane: faces mostly backward (seen from the third-person camera)."""
    return _unit((s * 0.32, 0.18, 1.0))


def _hindwing(m, bone, hinge, ankle, s):
    hinge, ankle = _v(hinge), _v(ankle)
    leg = ankle - hinge
    R = float(np.linalg.norm(leg)) + 0.5
    # folded: the first rod down the back of the leg with a narrow strip of membrane behind it
    d0 = _unit(leg)
    back = _unit(_v((0, 0, 1)) - d0 * d0[2])
    m.cube(bone, tuple(hinge - _v((0.25, 0.25, 0.0))), (0.5, 0.5, q(R)), "rod", pivot=tuple(hinge),
           rot=frame_rot(d0, back), skip=WINGS)
    m.cube(bone, (hinge[0], hinge[1], hinge[2]), (0.0, 1.5, q(R - 0.5)), "membrane", cutout=True, faces={"east", "west"},
           pivot=tuple(hinge), rot=frame_rot(d0, back), skip=WINGS)
    # open: the fan
    n = hindwing_plane(s)
    a0, a1 = HW_SPREAD
    angs = [a0 + (a1 - a0) * k / (RODS - 1) for k in range(RODS)]
    dirs = [in_plane(a, s, n) for a in angs]
    lens = [R, R * 0.97, R * 0.9, R * 0.78]
    tips = [hinge + d * L for d, L in zip(dirs, lens)]
    for k in range(RODS):
        nrm = _unit(np.cross(n, dirs[k])) * s
        m.cube(bone, tuple(hinge - _v((0.25, 0.25, 0.0))), (0.5, 0.5, q(lens[k])), "rod", pivot=tuple(hinge),
               rot=frame_rot(dirs[k], nrm), only=WINGS)
    for k in range(RODS - 1):
        mid = _unit(dirs[k] + dirs[k + 1])
        half = math.acos(max(-1.0, min(1.0, float(dirs[k] @ dirs[k + 1])))) / 2
        L = max(lens[k], lens[k + 1]) * math.cos(half)
        W = 2 * max(lens[k], lens[k + 1]) * math.sin(half) + 0.5
        side = _unit(np.cross(n, mid))
        o = hinge + n * (0.02 * k)
        m.cube(bone, tuple(o - _v((q(W) / 2, 0.0, 0.0))), (q(W), 0.0, q(L)), "membrane", cutout=True, faces={"up", "down"},
               pivot=tuple(o), rot=frame_rot(mid, n), only=WINGS)
        # the luminous rim along the trailing edge between two rod tips
        a, b = tips[k], tips[k + 1]
        m.cube(bone, tuple(a - _v((0.15, 0.15, 0.0))), (0.3, 0.3, q(float(np.linalg.norm(b - a)))), "rim",
               pivot=tuple(a), rot=frame_rot(b - a, n), only=WINGS)


# ----------------------------------------------------------------------------- tail: plates, bristles, side feathers, the fan

def _tail(m: Model) -> None:
    names = sweep(m, "tail_g", "tail", TAIL_PTS, 5.75, 1.75, "tailp", h0=5.25, h1=1.75, n=2, per_bone=2, power=0.7)
    for k, a in enumerate((4.0, 9.0, 12.0, 12.0, 10.0)):            # display: the tail lifts its fan high
        m.bones[names[k]].variant["display"] = ((0, 0, 0), (a, 0, 0))
        m.bones[names[k]].variant["overflow"] = ((0, 0, 0), (a * 0.7, 0, 0))
    m.bones[names[0]].variant["veer"] = ((0, 0, 0), (4.0, 0, 0))
    # ankylosaur osteoderms along the top of the tail base
    plate_row(m, "tail0", (0, 17.25, 5.0), (0, 17.0, 9.75), 3, 2.0, 1.5, 1.75, 0.5, "osteo", tilt=12, arch=0.25)
    # Psittacosaurus bristles standing along the top
    for k, (bn, y, z) in enumerate((("tail1", 16.75, 10.25), ("tail2", 17.0, 13.25))):
        m.cube(bn, (0, y - 0.25, z - 1.0), (0.0, 3.0 - 0.5 * k, 3.5), "bristle", cutout=True,
               faces={"east", "west"}, pivot=(0, y, z), rot=(-22, 0, 0))
    # the fan: nine eyed feathers, each its own bone (it opens and closes)
    tip = _v(TAIL_PTS[-1])
    fan = m.bone("fan", names[-1], tuple(tip), (FAN_DROOP, 0, 0))
    ez, ey = _v((0, 0, 1)), _v((0, 1, 0))
    aim(m, fan.name, "display", ez, ey, (0, 1.0, 0.22), (0, 0.22, -1.0))          # raised: a vertical fan facing forward
    aim(m, fan.name, "overflow", ez, ey, (0, 0.72, 0.7), (0, 0.7, -0.72))
    aim(m, fan.name, "veer", ez, ey, (0, -0.05, 1.0), (1, 0, 0))                   # a rudder
    for k in range(FAN):
        f = k / (FAN - 1)
        c = 2 * f - 1                                          # -1 (right edge) .. 1 (left edge)
        a0 = -FAN_FOLD / 2 + FAN_FOLD * f
        a1 = -FAN_OPEN / 2 + FAN_OPEN * f
        # cupped: the outer feathers droop and roll outward, the middle pair lies on top
        phi, roll = math.radians(FAN_CUP * abs(c)), math.radians(FAN_CUP * 0.8 * c)
        a = math.radians(a0)
        d = _v((math.sin(a) * math.cos(phi), -math.sin(phi), math.cos(a) * math.cos(phi)))
        nrm = _v((math.sin(roll), math.cos(roll), 0.0))
        o = tip + (0, -0.12 * abs(k - (FAN - 1) / 2), 0)
        bn = m.bone(f"fan{k}", "fan", tuple(tip)).name
        m.bones[bn].variant.update({v: ((0, 0, 0), (0, a1 - a0, 0)) for v in OPEN})
        m.bones[bn].variant["veer"] = ((0, 0, 0), (0, (a1 - a0) * 0.45, 0))
        L = FAN_LEN[k]
        vane_cube(m, bn, o, d, nrm, L, FAN_W, "fanf", cutout=True)
        # the eye-spot near the tip: a solid inset (cutout feathers cannot glow)
        vane_cube(m, bn, o + d * (L * 0.58), d, nrm, 2.0, 2.0, "ocellus", thick=0.5, ppu=4.0)
    fan.locators["tail_fan"] = tuple(tip + (0, 0.5, 5.0))


# ============================================================================= materials (Gate A: flat placeholders)

def materials():
    names = ["plume", "neck", "skull", "face", "brow", "beak", "jaw", "eye", "pupil", "nict", "horn", "crest",
             "crest_end", "gular", "gular_big", "thigh", "shin", "scale", "toe", "claw", "sickle", "spike", "osteo",
             "tailp", "rod", "rim", "ocellus", "sleeve"]
    mats = {nm: _flat(nm) for nm in names}
    for nm in ("flight", "fanf", "tuft", "ruff"):
        mats[nm] = _flat_vane(nm)
    mats["membrane"] = _flat_membrane
    mats["teeth"] = _flat_teeth
    mats["bristle"] = _flat_bristle
    mats["accent"] = mat_accent
    return mats


FLAT = {
    "plume": "#c9a46a", "neck": "#c9a46a", "skull": "#b8935e", "face": "#a5845a", "brow": "#9c7c52", "beak": "#1d1b22",
    "jaw": "#2a2630", "eye": "#e0a020", "pupil": "#120a06", "nict": "#d6dcd6", "horn": "#e8dcc0", "crest": "#e4d6b2",
    "crest_end": "#c8a050", "gular": "#2bb3a6", "gular_big": "#2bb3a6", "thigh": "#c39a62", "shin": "#4f5a2a",
    "scale": "#4f5a2a", "toe": "#46512a", "claw": "#16141a", "sickle": "#1a171e", "spike": "#efe3c6", "osteo": "#d9c48f",
    "tailp": "#c39a62", "membrane": "#7a1f3d", "rod": "#e8d8a8", "rim": "#ff7ab0", "ocellus": "#3ad6c8", "sleeve": "#c9a46a",
    "flight": "#1f6f74", "fanf": "#2a5f86", "tuft": "#efe0bb", "ruff": "#dcc28c",
}


def _flat(name):
    base = px.col(FLAT[name])

    def mat(ctx):
        lv = px.light(ctx, grad=0.1)
        rgb = base * (0.55 + 0.75 * lv)[:, None]
        g = ctx.zeros()
        if name in ("eye", "ocellus", "gular_big"):
            g = np.full(ctx.N, 0.5)
        return rgb, ctx.ones(), g
    return mat


def _flat_vane(name):
    base = px.col(FLAT[name])

    def mat(ctx):
        a, lvl = px.vane(ctx)
        lv = px.light(ctx, grad=0.0) + lvl
        return base * (0.6 + 0.6 * lv)[:, None], a, ctx.zeros()
    return mat


def _flat_membrane(ctx):
    base = px.col(FLAT["membrane"])
    a = ctx.ones()
    if ctx.face in ("up", "down"):                       # an open wedge: apex at the hinge (local z = 0)
        u = np.abs(ctx.local[:, 0] - 0.5) * 2
        a = (u <= ctx.local[:, 2] * 1.02 + 0.04).astype(float)
    lv = px.light(ctx, grad=0.0)
    return base * (0.6 + 0.6 * lv)[:, None], a, ctx.zeros()


def _flat_teeth(ctx):
    ix, iy, W, H = px.texel(ctx)
    tooth = (iy < H - 1 - (ix % 2)) | (iy == 0)
    return np.broadcast_to(px.col("#efe6cf"), (ctx.N, 3)).copy(), tooth.astype(float), ctx.zeros()


def _flat_bristle(ctx):
    ix, iy, W, H = px.texel(ctx)
    strand = (ix % 2 == 0)
    return np.broadcast_to(px.col("#efe6cf"), (ctx.N, 3)).copy(), strand.astype(float), ctx.zeros()
