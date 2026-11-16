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
CRANIUM_A = ((0.0, 28.5, -6.5), [(0.0, 2.3), (1.75, 2.95), (3.5, 2.75), (4.75, 1.5)])   # dome (authored)
CRANIUM_SQUASH = (0.9, 1.15)
EYE_A = (2.05, 30.4, -8.25)
BEAK_A = [(0.0, 30.2, -10.25), (0.0, 30.0, -12.5), (0.0, 29.0, -13.9), (0.0, 27.5, -14.2)]
EYE_RY = 16.0
CREST_A = [(0.0, 31.0, -10.75), (0.0, 32.9, -8.75), (0.0, 33.9, -6.0), (0.0, 34.6, -2.75), (0.0, 34.8, 0.5),
           (0.0, 34.4, 3.0)]
SHOULDER = (3.75, 19.5, -2.5)
ELBOW = (5.0, 16.25, -0.25)
WRIST = (5.75, 13.0, -2.25)
SPUR = (7.5, 17.75, 4.5)              # tip of the styliform digit (the folded wing's upper spar)
HIP = (3.0, 13.0, 1.5)
THIGH_PROFILE = [(0.0, 1.9), (1.0, 2.55), (4.5, 2.85), (7.75, 2.4), (8.75, 1.5)]   # along the femur, knee -> hip
KNEE = (3.25, 7.75, -2.0)
ANKLE = (3.25, 3.75, 3.0)
BALL = (3.25, 0.75, 0.5)
TAIL_PTS = [(0.0, 14.5, 4.25), (0.0, 15.5, 8.0), (0.0, 16.75, 11.5), (0.0, 18.25, 14.75), (0.0, 19.75, 17.5),
            (0.0, 21.0, 19.75)]
FAN_LEN = [9.5, 9.75, 10.0, 10.25, 10.5, 10.25, 10.0, 9.75, 9.5]
FAN_W = 2.75
FAN_REST = ((0.0, -0.57, 0.82), (0.0, 0.82, 0.57))   # rest fan: centre line 35 deg down, upper face toward the camera
FAN_CUP = 22.0                        # the outer feathers droop this much (a shallow dome)
FAN_FOLD = 66.0                       # rest fan: total spread (degrees) - partly open
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
    lathe(m, t.name, TRUNK_PIVOT, TRUNK_PROFILE, "body", sides=12, squash=TRUNK_SQUASH, skew=TRUNK_SKEW)
    # ankylosaur osteoderms down the spine (upright trunk frame: +Z is the back)
    px_, py, pz = TRUNK_PIVOT
    plate_row(m, t.name, (0, py + 9.0, pz + 3.5), (0, py + 3.0, pz + 4.5), 3, 1.75, 2.25, 2.25, 0.5, "osteo",
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
    sweep(m, sk.name, "beak", [H(p_) for p_ in BEAK_A], 2.75 * HS, 0.75, "beak", h0=3.25 * HS, h1=0.75, n=1, bones=False,
          power=0.75)
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
    sweep(m, jw.name, "jawb", [H(p_) for p_ in ((0, 28.25, -6.75), (0, 27.9, -10.25), (0, 27.85, -13.1))], 3.25 * HS, 0.75,
          "jaw", h0=1.5 * HS, h1=0.75, n=1, bones=False)
    # eyes: big, amber, turned a little forward; slit pupils; a nictitating membrane
    ew, eh, ed = 0.5, 2.5, 2.5                                                    # round iris painted at ppu 4
    for s, p in SIDES:
        ex, ey, ez = s * EYE[0], EYE[1], EYE[2]
        m.cube(sk.name, (ex - ew / 2, ey - eh / 2, ez - ed / 2), (ew, eh, ed), "eye", ppu=4.0,
               pivot=(ex, ey, ez), rot=side_rot((0, -EYE_RY, 0), s))
    pu = m.bone("pupils", sk.name, (0, EYE[1], EYE[2]))
    nc = m.bone("nict", sk.name, (0, EYE[1], EYE[2] - ed / 2 + 0.1))
    for s, p in SIDES:
        ex, ey, ez = s * EYE[0], EYE[1], EYE[2]
        m.cube(pu.name, (ex + s * 0.27 - 0.05, ey - 0.875, ez - 0.25), (0.1, 1.75, 0.5), "pupil", ppu=4.0,
               pivot=(ex, ey, ez), rot=side_rot((0, -EYE_RY, 0), s))                # the slit (narrows by scale)
        m.cube(nc.name, (ex + s * 0.31 - 0.025, ey - eh / 2, ez - ed / 2 + 0.1), (0.05, eh, 0.1), "nict",
               pivot=(ex, ey, ez), rot=side_rot((0, -EYE_RY, 0), s))
    sk.locators["eyes"] = (0, EYE[1], EYE[2] - 1.5)
    # throat pouch: tucked under the jaw at rest, a balloon in the display
    gu = m.bone("gular", sk.name, GULAR_PIVOT)
    oell(m, gu.name, H((0, 27.25, -8.0)), HZ((3.0, 2.0, 3.75)), None, None, "gular", a=0.66, b=0.86, skip=OPEN)
    lathe(m, gu.name, H((0, 22.5, -8.25)), [(0.0, 1.0), (1.0, 2.5), (2.75, 3.1), (4.5, 2.5), (5.5, 1.0)],
          "gular_big", sides=8, squash=(0.92, 1.1), only=OPEN)
    gu.locators["throat"] = H((0, 25.5, -8.25))
    # the hollow tubular crest: from the snout over the skull roof, sweeping far behind
    sweep(m, sk.name, "crest", CREST[:4], 3.0, 1.75, "crest", h0=3.0, h1=1.75, n=2, per_bone=6, power=0.7)
    c1 = m.bone("crest1", "crest0", CREST[3])
    sweep(m, c1.name, "crestb", CREST[3:], 1.75, 2.5, "crest", h0=1.75, h1=2.5, n=1, bones=False, power=2.0)
    m.bones["crest0"].variant.update({"display": ((0, 0, 0), (16.0, 0, 0)), "overflow": ((0, 0, 0), (11.0, 0, 0))})
    c1.variant.update({"display": ((0, 0, 0), (10.0, 0, 0)), "overflow": ((0, 0, 0), (7.0, 0, 0))})
    tip = _v(CREST[-1])
    d = _dir(CREST[-2], CREST[-1])
    vane_cube(m, c1.name, tip - d * 0.25, d, (0, 1, 0), 1.0, 3.0, "crest_end", thick=3.0)          # the flared bell lip
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
        oell(m, up.name, (sh + el) / 2 + (0, 0.25, 0), (2.75, 2.75, 5.0), el - sh, (1, 0, 0), "arm", a=0.7, b=0.88)
        fo = m.bone(f"{p}_fore", up.name, tuple(el))
        sweep(m, fo.name, f"{p}_fa", [el, wr], 2.0, 1.5, "coverts", n=1, bones=False)
        ha = m.bone(f"{p}_hand", fo.name, tuple(wr))
        m.box(ha.name, tuple(wr + (0.1 * s, -1.0, -0.4)), (1.5, 2.0, 2.0), "scale")
        for dx, dz, ln in ((-0.4, -0.5, 2.25), (0.45, -0.25, 2.0)):
            a = wr + (dx * s, -1.75, dz - 0.4)
            sweep(m, ha.name, f"{p}_cl", [a, a + (0, -ln, -ln * 0.45)], 0.6, 0.4, "claw", n=1, bones=False)
        # the styliform digit: a long ivory spar from the wrist up and back over the hip; the primaries
        # hang from it (as the membrane of Yi qi hung from its styliform element)
        st = m.bone(f"{p}_stylus", ha.name, tuple(wr))
        spur = _v(_x(SPUR, s))
        sweep(m, st.name, f"{p}_st", [wr + (0.55 * s, 0.25, 0.25), (wr + spur) / 2 + (0.2 * s, 0.25, 0), spur], 0.9, 0.4,
              "spike", n=1, bones=False)
        n_w = _unit((s * 0.72, 0.69, 0.0))                       # folded feathers face up-out (seen from behind too)
        # folded wing: three secondaries fanned along the forearm, three long primaries along the spar
        sec = m.bone(f"{p}_sec", fo.name, tuple(el))
        sec_ref = _unit((0.16 * s, 0.0, 1.0))
        for k, (t, ln) in enumerate(((0.12, 6.75), (0.42, 7.25), (0.72, 7.75))):
            o = el + (wr - el) * t + (0.45 * s + 0.12 * k * s, 0, 0)
            vane_cube(m, sec.name, o, _unit((0.16 * s, 0.25 * (1 - k), 1.0)), n_w, ln, 2.75, "flight", cutout=True)
        pri_dir = []
        for k, (t, ln, drop) in enumerate(((0.35, 8.25, -0.2), (0.65, 9.25, -0.3), (0.95, 9.75, -0.38))):
            o = wr + (spur - wr) * t + (0.15 * s, -0.25, 0)
            pr = m.bone(f"{p}_pri{k}", st.name, tuple(o))
            d = _unit((0.3 + 0.08 * k) * s * _v((1, 0, 0)) + _v((0, drop, 1.0)))
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
        top = hip + (0.15 * s, 2.5, 1.5)
        olathe(m, th.name, knee + (0.1 * s, 0.25, 0.0), top - knee, THIGH_PROFILE, "thigh", sides=8, squash=(0.9, 1.12),
               front=(0, 0, -1))
        # feathered trousers: plumes hanging from the thigh over the knee
        for k, (off, ln) in enumerate((((0.6, 1.25, 0.9), 4.5), ((1.6, 1.0, -0.2), 4.0))):
            o = knee + _v((off[0] * s, off[1], off[2]))
            out = _unit((s * (0.35 + 0.5 * k), 0.0, 1.0 - 0.6 * k))
            vane_cube(m, th.name, o, _unit(_v((0, -0.8, 0.45)) + out * 0.25), out, ln, 2.75, "trouser", cutout=True)
        sh = m.bone(f"{p}_shin", th.name, tuple(knee))
        sweep(m, sh.name, f"{p}_sn", [knee + (0, 0.5, -0.25), ankle], 2.0, 1.25, "shin", h0=2.25, h1=1.5, n=1, bones=False)
        mt = m.bone(f"{p}_meta", sh.name, tuple(ankle))
        sweep(m, mt.name, f"{p}_mt", [ankle + (0, 0.25, 0.1), ball], 1.5, 1.25, "scale", n=1, bones=False)
        ft = m.bone(f"{p}_foot", mt.name, tuple(ball))
        bx, by, bz = ball
        sweep(m, ft.name, f"{p}_d3", [(bx, 0.55, bz), (bx, 0.45, bz - 3.75)], 1.25, 1.0, "toe", h0=1.0, h1=0.9, n=1,
              bones=False)
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
    for k, a in enumerate((3.0, 6.0, 8.0, 9.0, 8.0)):              # display: the tail lifts its fan high
        m.bones[names[k]].variant["display"] = ((0, 0, 0), (a, 0, 0))
        m.bones[names[k]].variant["overflow"] = ((0, 0, 0), (a * 0.7, 0, 0))
    for k, a in enumerate((-14.0, -4.0, -5.0, -4.0, 0.0)):          # veer: straight out behind, a rudder
        if a:
            m.bones[names[k]].variant["veer"] = ((0, 0, 0), (a, 0, 0))
    # ankylosaur osteoderms along the top of the tail base
    plate_row(m, "tail0", (0, 17.25, 5.0), (0, 17.0, 9.75), 3, 2.0, 1.5, 1.75, 0.5, "osteo", tilt=12, arch=0.25)
    # Psittacosaurus bristles standing along the top
    for k, (bn, y, z) in enumerate((("tail1", 16.75, 10.25), ("tail2", 17.0, 13.25))):
        m.cube(bn, (0, y - 0.25, z - 1.0), (0.0, 3.0 - 0.5 * k, 3.5), "bristle", cutout=True,
               faces={"east", "west"}, pivot=(0, y, z), rot=(-22, 0, 0))
    # the fan: nine eyed feathers, each its own bone (it opens and closes)
    tip = _v(TAIL_PTS[-1])
    fan = m.bone("fan", names[-1], tuple(tip))
    ez, ey = _v((0, 0, 1)), _v((0, 1, 0))
    aim(m, fan.name, None, ez, ey, FAN_REST[0], FAN_REST[1])
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


# ============================================================================= materials (Gate B: premium surface)
#
# Every solid part is lit from the smooth form its boxes approximate (a pitched ellipsoid for the
# trunk, tubes along the neck / tail / thighs / crest / beak / horns, ellipsoids for the skull and
# pouch), painted with continuous hue-shifted ramps (no dither, no noise), patterned in world space
# so patterns run on across the lathe strips, and lit (glow) by designed lines and spots that fade.

# palettes, dark -> light (shadows cool / saturated, highlights warm)
PLUME = px.pal("#26150f", "#53301b", "#87552a", "#b3833f", "#d6ac63", "#ecd092", "#f8ebcc")    # cream-gold plumage
CREAM = px.pal("#6a4a2c", "#a9824f", "#d6b680", "#eedbb0", "#fcf3dc")                          # breast / belly
BAND = px.pal("#1c100c", "#3a2216", "#5e3a20", "#84582d")                                     # soft dark banding
TEAL = px.pal("#04191d", "#08343a", "#0d5754", "#14806f", "#2fae8f", "#7fdcb6")                # flight feathers: base
VIOLET = px.pal("#0b0a22", "#181843", "#272a6c", "#3b3f94", "#5d63bb", "#9aa0e0")              # .. middle (indigo-violet)
GOLD = px.pal("#3a2205", "#73460c", "#ab7218", "#d9a537", "#f4d070", "#fff1bd")                # .. tips
OLIVE = px.pal("#0f1408", "#1e270f", "#334019", "#4c5b27", "#6c7c3d", "#94a35d")               # leg scales
KERAT = px.pal("#050407", "#0d0b12", "#1a1722", "#2f2b3a", "#4e4a5e", "#8f8aa3")               # glossy black keratin
IVORY = px.pal("#58452c", "#8e7a55", "#bba680", "#dbc9a0", "#eee0bd", "#f8efd6")
BRASS = px.pal("#2e1a05", "#5e3a0c", "#94611a", "#c4902f", "#e8bd58", "#fbe39a")
WINE = px.pal("#14020a", "#2e0617", "#510c27", "#781739", "#a3294f", "#cf4f75", "#f08aa8")
SKIN = px.pal("#17110f", "#2c221d", "#463630", "#634d43", "#86695a")                          # bare face skin
TURQ = px.pal("#022422", "#05433f", "#0a6a62", "#139489", "#2fc2b0", "#7debd9", "#d2fff6")      # display skin
LUMEN = px.col("#08282a")
AMBER = px.pal("#3d1702", "#7a3304", "#bd610b", "#ec951c", "#ffc84a", "#fff0b0")
RIMC = px.pal("#7a1c48", "#c73a7a", "#ff6fa8", "#ffc2dc")
L_SPEC = _v((-0.35, 0.8, -0.5)) / np.linalg.norm((-0.35, 0.8, -0.5))


def materials():
    return {
        "body": mat_body, "arm": mat_arm, "coverts": mat_coverts, "thigh": mat_thigh, "neck": mat_neck, "tailp": mat_tail,
        "skull": mat_skull, "face": mat_face, "brow": mat_brow, "beak": mat_beak, "jaw": mat_jaw, "teeth": mat_teeth,
        "eye": mat_eye, "pupil": mat_pupil, "nict": mat_nict, "horn": mat_horn, "crest": mat_crest,
        "crest_end": mat_crest_end, "gular": mat_gular, "gular_big": mat_gular_big, "shin": mat_scale,
        "scale": mat_scale, "toe": mat_scale, "claw": mat_claw, "sickle": mat_sickle, "spike": mat_spike,
        "osteo": mat_osteo, "bristle": mat_bristle, "flight": mat_flight, "fanf": mat_fanf, "ocellus": mat_ocellus,
        "tuft": mat_tuft, "ruff": mat_ruff, "trouser": mat_trouser, "membrane": mat_membrane, "rod": mat_rod,
        "rim": mat_rim, "sleeve": mat_sleeve, "accent": mat_accent,
    }


# ----------------------------------------------------------------------------- helpers

def _ramp(pal, lv):
    """px.smooth_ramp for an array of levels, or one colour for a scalar level."""
    if np.ndim(lv) == 0:
        return px.smooth_ramp(pal, np.array([float(lv)]))[0]
    return px.smooth_ramp(pal, lv)


def _night(ctx):
    return float(ctx.params.get("night", 0.0))


def _over(ctx):
    return float(ctx.params.get("overflow", 0.0)) > 0.5


def G(ctx, base, night, over):
    """A glow level for this texture set: base / night / overflow."""
    return over if _over(ctx) else base + (night - base) * _night(ctx)


def _P(ctx):
    return ctx.wp if ctx.wp is not None else ctx.p


def _WN(ctx):
    return _v(ctx.wn if ctx.wn is not None else ctx.n)


def _ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def _mixc(a, b, t):
    t = np.clip(np.asarray(t, float), 0, 1)
    if t.ndim == 1:
        t = t[:, None]
    return np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t


def _lvn(ctx, nn, k=0.85):
    """Light level from smooth-form normals nn (N, 3), blended with the face's own level."""
    face = float(px.level_of(_WN(ctx))[0])
    return face + (px.level_of(nn) - face) * k


def _ell(ctx, c, r, R=None, pivot=None):
    """Ellipsoid normals (world) and local positions; R / pivot: an ellipsoid authored in a rotated frame."""
    p = _P(ctx)
    if R is not None:
        p = (p - _v(pivot)) @ R + _v(pivot)
    d = (p - _v(c)) / (_v(r) ** 2)
    nl = d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
    nw = nl @ R.T if R is not None else nl
    return nw, nl, p


_TUBES = {}


def _poly(key, pts, n=4):
    if key not in _TUBES:
        from models.common import spline
        P = np.array(spline(pts, n) if len(pts) > 2 else [_v(a) for a in pts])
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
        _TUBES[key] = (P, np.concatenate([[0.0], np.cumsum(seg)]))
    return _TUBES[key]


def _tube(ctx, key, pts, n=4):
    """Nearest point on a polyline: (normals, parameter 0..1 along it, distance)."""
    P, cum = _poly(key, pts, n)
    p = _P(ctx)
    best = np.full(len(p), np.inf)
    foot = np.zeros_like(p)
    tpar = np.zeros(len(p))
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        ab = b - a
        L2 = max(float(ab @ ab), 1e-9)
        t = np.clip(((p - a) @ ab) / L2, 0, 1)
        f = a + t[:, None] * ab
        d = np.linalg.norm(p - f, axis=1)
        m = d < best
        best[m], foot[m] = d[m], f[m]
        tpar[m] = (cum[i] + t[m] * np.sqrt(L2)) / max(cum[-1], 1e-9)
    off = p - foot
    nn = off / np.maximum(np.linalg.norm(off, axis=1, keepdims=True), 1e-9)
    _TUBES["_last_off"] = off
    return nn, tpar, best


def _scallop(s, t, w, h, depth=0.09):
    """Rows of overlapping rounded feather tips in a (around, along) parameter space: a level offset
    (each feather lighter toward its rounded tip, a soft shadow just past the tip)."""
    row = np.floor(t / h)
    fx = np.mod(s / w + 0.5 * row, 1.0) - 0.5
    fy = np.mod(t / h, 1.0)
    edge = 0.55 + 0.45 * np.sqrt(np.clip(1 - (2 * fx) ** 2, 0, 1))
    inside = fy <= edge
    body = np.where(inside, fy / np.maximum(edge, 1e-3), 0.0)          # 0 at the feather root .. 1 at its tip
    shadow = np.where(inside, 0.0, np.clip(1 - (fy - edge) / 0.3, 0, 1))
    return depth * (0.9 * body - 0.35 - 1.1 * shadow)


def _spec(nn, power=10.0, amt=1.0):
    return amt * np.clip(nn @ L_SPEC, 0, 1) ** power


def _side_x(ctx):
    return np.sign(np.mean(_P(ctx)[:, 0])) or 1.0


# ----------------------------------------------------------------------------- body plumage

TRUNK_ELL = ((0.0, 16.75, 1.65), (4.25, 6.4, 4.9))       # the trunk lathe as one ellipsoid (upright frame, absolute)


def _plumage(lv, dorsal, ventral, band, scal):
    """Countershaded cream-gold plumage: a warm banded back, a pale cream breast."""
    lv = lv + scal - 0.2 * dorsal + 0.06 * ventral
    rgb = _ramp(PLUME, lv)
    rgb = _mixc(rgb, _ramp(CREAM, lv + 0.1), _ss(0.0, 0.7, ventral) * 0.9)
    rgb = _mixc(rgb, _ramp(BAND, lv * 0.95 + 0.08), band * _ss(0.05, 0.6, dorsal) * 0.85)
    return rgb


def mat_body(ctx):
    R = rot_matrix((PITCH, 0, 0))
    c, r = TRUNK_ELL
    nw, nl, u = _ell(ctx, c, r, R, TRUNK_PIVOT)
    lv = _lvn(ctx, nw, 0.85) + 0.02
    dorsal = np.clip(nl[:, 2] * 1.5 + 0.2, 0, 1)
    ventral = np.clip(-nl[:, 2] * 1.6 - 0.15, 0, 1)
    band = _ss(0.45, 0.9, 0.5 + 0.5 * np.cos((u[:, 1] - 0.5) * 2 * np.pi / 3.0))
    ang = np.arctan2(u[:, 0], u[:, 2] - c[2]) * 4.3
    scal = _scallop(ang, -u[:, 1], 3.0, 2.0, 0.12)
    lv = lv + px.ao_near(ctx, [(s * 2.9, 13.4, 1.5) for s in (-1, 1)], 3.5, 0.14)
    rgb = _plumage(lv, dorsal, ventral, band, scal)
    g = ctx.zeros()
    wid = 0.1 + 0.05 * _night(ctx) + (0.04 if _over(ctx) else 0.0)
    flank = np.clip(1 - np.abs(np.abs(nl[:, 0]) - 0.8) / wid, 0, 1)
    flank = flank * _ss(12.5, 15.0, u[:, 1]) * _ss(23.0, 20.5, u[:, 1])
    if not _over(ctx):                               # a row of display spots on each flank (a continuous line in the overflow)
        flank = flank * _ss(0.35, 0.75, 0.5 + 0.5 * np.cos(u[:, 1] * 2 * np.pi / 1.6))
    rgb = _mixc(rgb, _ramp(TURQ, 0.72 + 0.2 * flank), flank)
    g = flank * G(ctx, 0.25, 0.95, 0.95)
    return rgb, ctx.ones(), g


def mat_arm(ctx):
    sx = _side_x(ctx)
    sh, el = _v(_x(SHOULDER, sx)), _v(_x(ELBOW, sx))
    nn, t, _ = _tube(ctx, f"arm{sx}", [sh, el])
    lv = _lvn(ctx, nn, 0.85)
    p = _P(ctx)
    scal = _scallop(np.arctan2(nn[:, 0], nn[:, 2]) * 1.6, -p[:, 1], 2.5, 1.75, 0.11)
    band = _ss(0.6, 0.95, 0.5 + 0.5 * np.cos(p[:, 1] * 2 * np.pi / 2.5))
    dorsal = np.clip(nn[:, 2] * 1.2 + 0.4, 0, 1)
    return _plumage(lv, dorsal, np.clip(-nn[:, 2], 0, 1) * 0.6, band, scal), ctx.ones(), ctx.zeros()


def mat_coverts(ctx):
    """The forearm: small iridescent covert feathers (the wing starts here)."""
    sx = _side_x(ctx)
    el, wr = _v(_x(ELBOW, sx)), _v(_x(WRIST, sx))
    nn, t, _ = _tube(ctx, f"fore{sx}", [el, wr])
    lv = _lvn(ctx, nn, 0.8)
    sa, sb = np.arctan2(nn[:, 0], nn[:, 2]) * 1.4, t * 4.0
    scal = _scallop(sa, sb, 1.5, 1.0, 0.1)
    rgb = _mixc(_ramp(TEAL, lv + scal + 0.05), _ramp(VIOLET, lv + scal + 0.12), _ss(0.2, 0.9, t))
    tip = np.clip(scal / 0.1 * 1.6 - 0.55, 0, 1)                            # the bright edge of each covert
    rgb = _mixc(rgb, _ramp(TURQ, 0.8), tip * 0.7)
    return rgb, ctx.ones(), tip * G(ctx, 0.2, 0.8, 1.0)


def mat_sleeve(ctx):
    lv = px.light(ctx, grad=0.1)
    return _ramp(TEAL, lv + 0.05), ctx.ones(), ctx.zeros()


def _thigh_axis(sx):
    hip, knee = _v(_x(HIP, sx)), _v(_x(KNEE, sx))
    return [knee + _v((0.1 * sx, 0.25, 0.0)), hip + _v((0.15 * sx, 2.5, 1.5))]


def mat_thigh(ctx):
    """Feathered trousers: banded drumstick, the scalloped fringe deepest toward the knee."""
    sx = _side_x(ctx)
    pts = _thigh_axis(sx)
    nn, t, _ = _tube(ctx, f"thigh{sx}", pts)
    lv = _lvn(ctx, nn, 0.85)
    ang = np.arctan2(nn[:, 0] * sx, -nn[:, 2]) * 2.6
    along = t * 8.75
    scal = _scallop(ang, -along, 2.75, 1.75, 0.11 + 0.05 * (1 - t))
    band = _ss(0.6, 0.95, 0.5 + 0.5 * np.cos(along * 2 * np.pi / 2.25))
    dorsal = np.clip(0.55 + 0.45 * nn[:, 2], 0, 1)
    lv = lv - 0.08 * _ss(0.3, 0.0, t)                                      # shade toward the knee
    rgb = _plumage(lv, dorsal, np.clip(-nn[:, 2] - 0.2, 0, 1) * 0.5, band, scal)
    return rgb, ctx.ones(), ctx.zeros()


def mat_neck(ctx):
    """Plumage behind, bare turquoise display skin down the throat with a glowing line."""
    nn, t, _ = _tube(ctx, "neck", NECK)
    lv = _lvn(ctx, nn, 0.85)
    front = nn @ _unit((0, -0.3, -1.0))
    p = _P(ctx)
    skin = _ss(1.25, 0.8, np.abs(p[:, 0])) * _ss(0.15, 0.45, front)        # a strip of bare skin down the throat
    scal = _scallop(np.arctan2(nn[:, 0], nn[:, 2]) * 2.2, -p[:, 1], 2.5, 1.6, 0.11)
    band = _ss(0.6, 0.95, 0.5 + 0.5 * np.cos(p[:, 1] * 2 * np.pi / 2.6))
    rgb = _plumage(lv, np.clip(nn[:, 2] + 0.3, 0, 1), 0.0, band, scal)
    w = 0.35 + 0.25 * _night(ctx) + (0.3 if _over(ctx) else 0.0)          # half-width of the line, units
    line = _ss(w, w * 0.35, np.abs(p[:, 0])) * _ss(0.2, 0.6, front) * _ss(0.0, 0.12, t)
    off = _TUBES["_last_off"]
    ang = np.degrees(np.arctan2(np.abs(off[:, 0]), -off[:, 2]))            # 0 = the throat, 90 = the side
    sw = 9.0 + 6.0 * _night(ctx) + (4.0 if _over(ctx) else 0.0)
    stripe = _ss(sw, sw * 0.3, np.abs(ang - 72.0)) * _ss(0.02, 0.15, t) * _ss(1.0, 0.85, t)
    nape = _ss(0.45, 0.15, np.abs(p[:, 0])) * _ss(0.2, 0.6, -front) * _ss(0.3, 0.45, t)
    stripe = np.maximum(stripe, nape)
    rgb = _mixc(rgb, _ramp(TURQ, lv - 0.18), skin)
    rgb = _mixc(rgb, _ramp(TURQ, 0.62 + 0.3 * stripe), stripe * 0.9)
    rgb = _mixc(rgb, _ramp(TURQ, 0.8 + 0.2 * line), line * 0.85)
    g = np.maximum.reduce([line * G(ctx, 0.4, 1.0, 1.0), stripe * G(ctx, 0.28, 0.95, 1.0), skin * G(ctx, 0.12, 0.55, 0.7)])
    return rgb, ctx.ones(), g


def mat_tail(ctx):
    nn, t, _ = _tube(ctx, "tail", TAIL_PTS)
    lv = _lvn(ctx, nn, 0.85)
    up = nn[:, 1]
    dorsal = np.clip(up * 1.3 + 0.35, 0, 1)
    ventral = np.clip(-up * 1.5 - 0.2, 0, 1)
    along = t * 17.0
    band = _ss(0.55, 0.95, 0.5 + 0.5 * np.cos((along - 1.0) * 2 * np.pi / 2.6))
    scal = _scallop(np.arctan2(nn[:, 0], nn[:, 1]) * 2.0, -along, 2.75, 1.75, 0.11)
    rgb = _plumage(lv, dorsal, ventral, band, scal)
    p = _P(ctx)
    top = _ss(0.7, 0.92, up) * _ss(0.2, 0.32, t) * _ss(1.0, 0.88, t) * _ss(0.75, 0.3, np.abs(p[:, 0]))
    if not _over(ctx):                               # a dotted display line along the top (continuous in the overflow)
        top = top * _ss(0.35, 0.8, 0.5 + 0.5 * np.cos(along * 2 * np.pi / 1.75))
    rgb = _mixc(rgb, _ramp(TURQ, 0.75 + 0.15 * top), top)
    return rgb, ctx.ones(), top * G(ctx, 0.3, 0.95, 1.0)


# ----------------------------------------------------------------------------- head

def _cranium_ell():
    base, prof = CRANIUM
    hmax = prof[-1][0]
    rmax = max(r for _, r in prof)
    return (_v(base) + _v((0, hmax * 0.42, 0)), _v((rmax * CRANIUM_SQUASH[0], hmax * 0.62, rmax * CRANIUM_SQUASH[1])))


def _eye_ring(ctx, rgb):
    """A ring of bare turquoise display skin round each amber eye (glows)."""
    p = _P(ctx)
    d = np.minimum(*[np.linalg.norm(p - _v((s * EYE[0], EYE[1], EYE[2])), axis=1) for s in (-1, 1)])
    w = 0.32 + 0.18 * _night(ctx) + (0.12 if _over(ctx) else 0.0)
    ring = np.clip(1 - np.abs(d - 1.75) / w, 0, 1) ** 1.5
    rgb = _mixc(rgb, _ramp(TURQ, 0.7 + 0.25 * ring), ring)
    return rgb, ring * G(ctx, 0.3, 0.95, 1.0)


def mat_skull(ctx):
    c, r = _cranium_ell()
    nw, nl, p = _ell(ctx, c, r)
    lv = _lvn(ctx, nw, 0.9) + 0.03
    scal = _scallop(np.arctan2(nl[:, 0], nl[:, 2]) * 3.2, -p[:, 1], 2.0, 1.4, 0.09)
    crown = np.clip(nl[:, 1] * 1.4 - 0.1, 0, 1)
    band = _ss(0.6, 0.95, 0.5 + 0.5 * np.cos((p[:, 2] + 6.0) * 2 * np.pi / 2.2)) * crown
    rgb = _plumage(lv, crown, np.clip(-nl[:, 1], 0, 1) * 0.5, band, scal)
    # a dark mask round each eye (makes the amber read) fading into the plumage
    mask = px.glow_spot(ctx, [(s * EYE[0], EYE[1], EYE[2]) for s in (-1, 1)], 2.4, 0.35)
    rgb = _mixc(rgb, _ramp(SKIN, lv - 0.1), mask * 0.9)
    rgb, g = _eye_ring(ctx, rgb)
    return rgb, ctx.ones(), g


def mat_face(ctx):
    c, r = _cranium_ell()
    nw, nl, p = _ell(ctx, (c[0], c[1] - 0.5, c[2] - 2.5), (r[0], r[1], r[2] * 1.2))
    lv = _lvn(ctx, nw, 0.8)
    mask = px.glow_spot(ctx, [(s * EYE[0], EYE[1], EYE[2]) for s in (-1, 1)], 2.6, 0.3)
    wr = 0.04 * np.sin(p[:, 1] * 9.0 + p[:, 2] * 2.0)                     # fine soft wrinkles (smooth)
    rgb = _ramp(SKIN, lv + wr - 0.08 * mask)
    rgb, g = _eye_ring(ctx, rgb)
    return rgb, ctx.ones(), g


def mat_brow(ctx):
    lv = px.light(ctx, grad=0.12)
    rgb = _mixc(_ramp(IVORY, lv - 0.08), _ramp(BRASS, lv), 0.35)
    return rgb, ctx.ones(), ctx.zeros()


BEAK = [H(p_) for p_ in BEAK_A]


def mat_beak(ctx):
    """Glossy black keratin with a long specular streak; an ivory hook."""
    nn, t, _ = _tube(ctx, "beak", BEAK)
    lv = _lvn(ctx, nn, 0.85) - 0.12
    rgb = _ramp(KERAT, lv)
    rgb = rgb + _spec(nn, 14, 0.55)[:, None] * px.col("#cfd8ff")
    tip = _ss(0.62, 0.9, t)
    rgb = _mixc(rgb, _ramp(IVORY, lv + 0.25) + _spec(nn, 10, 0.25)[:, None], tip)
    return np.clip(rgb, 0, 1), ctx.ones(), ctx.zeros()


JAW_PTS = [H(p_) for p_ in ((0, 28.25, -6.75), (0, 27.9, -10.25), (0, 27.85, -13.1))]


def mat_jaw(ctx):
    nn, t, _ = _tube(ctx, "jaw", JAW_PTS, 1)
    lv = _lvn(ctx, nn, 0.8) - 0.1
    rgb = _mixc(_ramp(SKIN, lv), _ramp(KERAT, lv) + _spec(nn, 12, 0.35)[:, None], _ss(0.25, 0.45, t))
    rgb = _mixc(rgb, _ramp(IVORY, lv + 0.2), _ss(0.78, 0.97, t))
    return np.clip(rgb, 0, 1), ctx.ones(), ctx.zeros()


def mat_teeth(ctx):
    """A row of small conical ivory teeth (cutout)."""
    ix, iy, W, Hh = px.texel(ctx)
    k = np.mod(ix, 3)
    depth = 1 - iy / max(Hh - 1, 1)                                     # 1 at the gum, 0 at the tip row
    tooth = (np.abs(k - 1) <= depth * 1.2) & (np.mod(ix // 3, 4) != 3)
    rgb = _mixc(_ramp(IVORY, 0.85 - 0.3 * (1 - depth)), px.col("#c88f86"), _ss(0.8, 1.0, depth))
    return rgb, tooth.astype(float), ctx.zeros()


def mat_eye(ctx):
    """A round amber iris in a dark lid ring; the corners are face skin, so the eye reads round."""
    lvf = px.light(ctx, grad=0.0)
    sx = np.sign(EYE[0]) * _side_x(ctx)
    out_face = abs(_WN(ctx)[0]) > 0.7 and np.sign(_WN(ctx)[0]) == np.sign(np.mean(_P(ctx)[:, 0]))
    if not out_face:
        return _ramp(SKIN, lvf), ctx.ones(), ctx.zeros()
    ix, iy, W, Hh = px.texel(ctx)
    cx, cy = (W - 1) / 2, (Hh - 1) / 2
    r = np.hypot(ix - cx, iy - cy) / (min(W, Hh) / 2)
    iris = np.clip(1 - r / 0.82, 0, 1)
    over = _over(ctx)
    pal = AMBER if not over else px.pal("#7a3304", "#ec951c", "#ffd36a", "#fff3c4", "#ffffff", "#ffffff")
    rgb = _ramp(pal, 0.25 + 0.75 * iris ** 0.6)
    rgb = _mixc(rgb, px.col("#1a0b05"), _ss(0.70, 0.86, r))                     # the dark limbal ring
    rgb = _mixc(rgb, _ramp(SKIN, lvf - 0.05), _ss(0.9, 1.0, r))        # lid skin in the corners
    front = (ix >= W - 3) if ctx.face == "east" else (ix <= 2)
    hi = front & (iy == 2) | (front & (iy == 3) & ((ix == W - 3) | (ix == 2)))
    rgb = np.where(hi[:, None], px.col("#fffdf0"), rgb)
    g = np.clip(1 - r / 0.8, 0, 1) ** 0.7 * G(ctx, 0.55, 0.85, 1.0)
    return rgb, ctx.ones(), g


def mat_pupil(ctx):
    rgb = np.broadcast_to(px.col("#050304"), (ctx.N, 3)).copy()
    return rgb, ctx.ones(), ctx.zeros()


def mat_nict(ctx):
    return np.broadcast_to(px.col("#cdd8e0"), (ctx.N, 3)).copy(), ctx.ones(), ctx.zeros()


RHORN = [H(p_) for p_ in ((-1.9, 31.9, -8.4), (-2.3, 33.25, -9.0), (-2.5, 34.5, -10.25), (-2.25, 35.0, -11.75))]
LHORN = [H(p_) for p_ in ((1.9, 31.9, -8.4), (2.1, 32.9, -8.9))]


def mat_horn(ctx):
    """Ivory horns on burnished brass bases, fine growth rings."""
    right = _side_x(ctx) < 0
    nn, t, _ = _tube(ctx, "rhorn" if right else "lhorn", RHORN if right else LHORN)
    lv = _lvn(ctx, nn, 0.85)
    rings = 0.05 * np.cos(t * (28 if right else 10))
    rgb = _mixc(_ramp(BRASS, lv + rings), _ramp(IVORY, lv + rings + 0.1), _ss(0.12, 0.45, t))
    rgb = rgb + _spec(nn, 12, 0.25)[:, None]
    return np.clip(rgb, 0, 1), ctx.ones(), ctx.zeros()


def mat_crest(ctx):
    """The hollow crest: ivory with burnished brass rings, a turquoise display line along each side."""
    nn, t, _ = _tube(ctx, "crest", CREST)
    lv = _lvn(ctx, nn, 0.85)
    ring = _ss(0.55, 0.85, 0.5 + 0.5 * np.cos(t * 2 * np.pi * 4.5))
    rgb = _mixc(_ramp(IVORY, lv + 0.05), _ramp(BRASS, lv + 0.05), ring * _ss(0.1, 0.3, t) * 0.85)
    rgb = rgb + _spec(nn, 12, 0.1)[:, None]
    off = _TUBES["_last_off"]
    w = 0.3 + 0.2 * _night(ctx) + (0.2 if _over(ctx) else 0.0)           # half-height of the line, units
    line = _ss(w, w * 0.3, np.abs(off[:, 1])) * _ss(0.4, 0.8, np.abs(nn[:, 0])) * _ss(0.05, 0.18, t)
    ridge = _ss(0.3, 0.1, np.abs(off[:, 0])) * _ss(0.3, 0.7, nn[:, 1]) * _ss(0.12, 0.25, t) * min(1.0, _night(ctx) + _over(ctx))
    rgb = _mixc(rgb, _ramp(TURQ, 0.75 + 0.25 * line), line * 0.9)
    rgb = _mixc(rgb, _ramp(TURQ, 0.85), ridge * 0.9)
    g = np.maximum(line * G(ctx, 0.32, 1.0, 1.0), ridge * G(ctx, 0.0, 0.85, 1.0))
    return np.clip(rgb, 0, 1), ctx.ones(), g


def mat_crest_end(ctx):
    """The bell lip: brass outside; the open end shows the dark lumen with a glowing inner ring."""
    d = _dir(CREST[-2], CREST[-1])
    lv = px.light(ctx, grad=0.1)
    rgb = _ramp(BRASS, lv + 0.05)
    g = ctx.zeros()
    if float(_WN(ctx) @ d) > 0.7:
        ix, iy, W, Hh = px.texel(ctx)
        r = np.hypot(ix - (W - 1) / 2, iy - (Hh - 1) / 2) / (min(W, Hh) / 2)
        ring = np.clip(1 - np.abs(r - 0.62) / 0.16, 0, 1)
        rgb = np.where((r < 0.8)[:, None], LUMEN, rgb)
        rgb = _mixc(rgb, _ramp(TURQ, 0.9), ring)
        g = ring * G(ctx, 0.5, 0.9, 1.0)
    return rgb, ctx.ones(), g


def mat_gular(ctx):
    """The folded throat pouch: turquoise display skin, glowing along its folds."""
    p = _P(ctx)
    c = _v(H((0, 27.25, -8.0)))
    nw, nl, _ = _ell(ctx, c, _v(HZ((3.0, 2.0, 3.75))) / 2)
    lv = _lvn(ctx, nw, 0.85)
    fold = 0.5 + 0.5 * np.cos((p[:, 1] - c[1]) * 2 * np.pi / 0.9)
    rgb = _ramp(TURQ, lv - 0.08 + 0.14 * fold)
    g = np.maximum(_ss(0.7, 1.0, fold) * G(ctx, 0.55, 0.95, 1.0), np.full(ctx.N, G(ctx, 0.22, 0.6, 0.7)))
    return rgb, ctx.ones(), g


def mat_gular_big(ctx):
    """The inflated pouch: concentric glowing rings round a golden heart on the front."""
    base = _v(H((0, 22.5, -8.25)))                     # the lathe is not head-scaled: its profile is in model units
    c = base + _v((0, 2.75, 0))
    r = _v((3.1 * 0.92 * 0.92, 2.9, 3.1 * 1.1 * 0.92))
    nw, nl, p = _ell(ctx, c, r)
    lv = _lvn(ctx, nw, 0.9)
    heart = c + _v((0, 0.3, -r[2]))
    dd = np.linalg.norm(p - heart, axis=1)
    rings = np.maximum(np.clip(1 - np.abs(dd - 2.25) / 0.5, 0, 1), np.clip(1 - np.abs(dd - 3.9) / 0.5, 0, 1))
    hearts = _ss(1.5, 0.8, dd)
    rgb = _ramp(TURQ, lv + 0.08 + 0.25 * rings)
    rgb = _mixc(rgb, _ramp(GOLD, 0.7 + 0.3 * hearts), hearts)
    g = np.maximum(rings * G(ctx, 0.55, 0.85, 1.0), hearts * G(ctx, 0.5, 0.8, 1.0))
    return rgb, ctx.ones(), g


# ----------------------------------------------------------------------------- legs, hands, claws

def mat_scale(ctx):
    """Deep olive scales: big scutes down the front, small scales elsewhere; lit as limbs."""
    lv = px.light(ctx, grad=0.12) + 0.02
    front = float(_WN(ctx) @ _v((0, 0.2, -1.0))) > 0.45
    sc = px.scales(ctx, size=3 if front else 2, depth=0.12 if front else 0.08)
    lv = lv + sc + px.ao_near(ctx, [_x(KNEE, s) for s in (-1, 1)] + [_x(ANKLE, s) for s in (-1, 1)], 1.6, 0.12)
    return _ramp(OLIVE, lv), ctx.ones(), ctx.zeros()


def mat_claw(ctx):
    lv = px.light(ctx, grad=0.2) - 0.05
    rgb = _ramp(KERAT, lv)
    ix, iy, W, Hh = px.texel(ctx)
    rgb = _mixc(rgb, _ramp(IVORY, lv + 0.1), _ss(0.6, 1.0, iy / max(Hh - 1, 1)) * 0.6)
    return rgb, ctx.ones(), ctx.zeros()


def mat_sickle(ctx):
    """The sickle talon: glossy black with a pale cutting edge; the edge glows in the overflow."""
    lv = px.light(ctx, grad=0.2) - 0.08
    rgb = _ramp(KERAT, lv) + _spec(np.broadcast_to(_WN(ctx), (ctx.N, 3)), 6, 0.2)[:, None]
    ix, iy, W, Hh = px.texel(ctx)
    edge = (iy == Hh - 1) if px.side(ctx) else np.zeros(ctx.N, bool)
    rgb = np.where(edge[:, None], _ramp(IVORY, 0.85), rgb)
    g = edge * (0.7 if _over(ctx) else 0.0)
    return np.clip(rgb, 0, 1), ctx.ones(), g.astype(float)


def mat_spike(ctx):
    """The styliform digit: ivory with dark joint bands, a brass point."""
    lv = px.light(ctx, grad=0.1) + 0.05
    loc = ctx.local[:, 2]
    rgb = _mixc(_ramp(IVORY, lv), _ramp(BRASS, lv), _ss(0.55, 1.0, loc))
    joint = np.clip(1 - np.abs(np.mod(loc * 3.0, 1.0) - 0.5) / 0.08, 0, 1) * 0.5
    rgb = _mixc(rgb, _ramp(IVORY, lv - 0.35), joint)
    return rgb, ctx.ones(), ctx.zeros()


def mat_osteo(ctx):
    """Osteoderm: an ivory plate inlaid with a burnished brass rim; its keel seam glows at night."""
    ix, iy, W, Hh = px.texel(ctx)
    lv = px.light(ctx, grad=0.1) + 0.08
    rgb = _ramp(IVORY, lv)
    rim = px.border(ctx, 1)
    rgb = np.where(rim[:, None], _ramp(BRASS, lv - 0.05), rgb)
    g = ctx.zeros()
    if W >= 3 and Hh >= 3 and not px.side(ctx):
        keel = np.clip(1 - np.abs(ix - (W - 1) / 2) / 0.9, 0, 1) * (~rim)
        rgb = _mixc(rgb, _ramp(TURQ, 0.8), keel)
        g = keel * G(ctx, 0.28, 0.95, 1.0)
    return rgb, ctx.ones(), g


def mat_bristle(ctx):
    """Stiff pale Psittacosaurus bristles (cutout): strands of uneven length."""
    ix, iy, W, Hh = px.texel(ctx)
    up = 1 - ctx.local[:, 1]
    ln = 0.15 + 0.3 * (0.5 + 0.5 * np.sin(ix * 2.1 + 0.7))
    strand = (np.mod(ix, 2) == 0) & (up >= ln)
    rgb = _ramp(IVORY, 0.95 - 0.55 * up)
    return rgb, strand.astype(float), ctx.zeros()


# ----------------------------------------------------------------------------- feathers (cutout)

def _iridescent(ctx, v, lv):
    """Teal at the root -> violet -> gold tips; the hue slides with the feather's angle."""
    wn = _WN(ctx)
    sheen = 0.5 + 0.5 * float(wn @ _unit((0.25, 0.9, 0.35)))
    a = _ramp(TEAL, lv + 0.04 + 0.08 * sheen)
    b = _ramp(VIOLET, lv + 0.10 - 0.06 * sheen)
    rgb = _mixc(a, b, _ss(0.42, 0.72, v + 0.08 * (sheen - 0.5)))
    return _mixc(rgb, _ramp(GOLD, lv + 0.18), _ss(0.82, 0.95, v))


def mat_flight(ctx):
    alpha, lvl = px.vane(ctx, width_at=0.42, tip=0.97, base=0.18, rachis=0.09, barb=2.5)
    v = ctx.local[:, 2]
    lv = px.light(ctx, grad=0.0) + lvl + 0.10 * v
    rgb = _iridescent(ctx, v, lv)
    rach = np.abs(ctx.local[:, 0] * 2 - 1) < 0.09
    rgb = np.where((rach & (v < 0.85))[:, None], _mixc(rgb, px.col("#e9e3c8"), 0.45), rgb)
    return rgb, alpha, ctx.zeros()


def mat_fanf(ctx):
    """Tail-fan feather: the same iridescence, darkened in a halo round the eye-spot inset."""
    alpha, lvl = px.vane(ctx, width_at=0.5, tip=0.98, base=0.22, rachis=0.07, barb=2.0)
    v = ctx.local[:, 2]
    lv = px.light(ctx, grad=0.0) + lvl + 0.08 * v
    rgb = _iridescent(ctx, v, lv)
    halo = np.clip(1 - np.abs(v - 0.63) / 0.16, 0, 1)
    rgb = _mixc(rgb, _ramp(VIOLET, lv - 0.15), halo * 0.7)
    return rgb, alpha, ctx.zeros()


def mat_ocellus(ctx):
    """The eye-spot inset: gold rim, bronze, a glowing turquoise ring round a deep blue heart."""
    lv = px.light(ctx, grad=0.0) + 0.05
    if px.side(ctx) and min(ctx.fw, ctx.fh) < 0.6:
        return _ramp(VIOLET, lv - 0.1), ctx.ones(), ctx.zeros()
    ix, iy, W, Hh = px.texel(ctx)
    r = np.hypot(ix - (W - 1) / 2, iy - (Hh - 1) / 2) / (min(W, Hh) / 2)
    rgb = _ramp(VIOLET, lv - 0.15)                                     # the feather round it
    rgb = _mixc(rgb, _ramp(GOLD, 0.75), _ss(1.0, 0.9, r))
    rgb = _mixc(rgb, px.col("#6b3d14"), _ss(0.82, 0.7, r))
    ring = np.clip(1 - np.abs(r - 0.52) / 0.22, 0, 1)
    rgb = _mixc(rgb, _ramp(TURQ, 0.85 + 0.15 * ring), _ss(0.68, 0.56, r))
    rgb = _mixc(rgb, px.col("#0b1c5a"), _ss(0.38, 0.26, r))
    g = np.maximum(ring, 0.75 * _ss(0.45, 0.0, r)) * G(ctx, 0.65, 0.95, 1.0)
    return rgb, ctx.ones(), g


def _plume(ctx, dark=0.0, banded=True):
    alpha, lvl = px.vane(ctx, width_at=0.5, tip=0.95, base=0.3, rachis=0.06, barb=2.0)
    v = ctx.local[:, 2]
    lv = px.light(ctx, grad=0.0) + lvl + 0.04 - dark - 0.12 * v
    rgb = _ramp(PLUME, lv)
    if banded:
        band = _ss(0.6, 0.95, 0.5 + 0.5 * np.cos(v * 2 * np.pi * 2.5)) * _ss(0.35, 0.6, v)
        rgb = _mixc(rgb, _ramp(BAND, lv), band * 0.55)
    rgb = _mixc(rgb, _ramp(CREAM, lv + 0.15), _ss(0.85, 0.98, v) * 0.6)
    return rgb, alpha


def mat_ruff(ctx):
    rgb, a = _plume(ctx, 0.0)
    return rgb, a, ctx.zeros()


def mat_trouser(ctx):
    rgb, a = _plume(ctx, 0.08)
    return rgb, a, ctx.zeros()


def mat_tuft(ctx):
    """Long ivory plume with an iridescent tip and a gold edge."""
    alpha, lvl = px.vane(ctx, width_at=0.55, tip=0.97, base=0.25, rachis=0.06, barb=2.0)
    v = ctx.local[:, 2]
    lv = px.light(ctx, grad=0.0) + lvl + 0.2
    rgb = _ramp(IVORY, lv)
    rgb = _mixc(rgb, _iridescent(ctx, (v - 0.55) * 2.2, lv - 0.12), _ss(0.55, 0.8, v))
    return rgb, alpha, ctx.zeros()


# ----------------------------------------------------------------------------- membranes, rods, the luminous rim

def mat_membrane(ctx):
    """Wine membrane: dark at the hinge, thin and bright toward the rim, veins fanning out."""
    u = ctx.local[:, 0] * 2 - 1
    v = ctx.local[:, 2]
    a = ctx.ones()
    if ctx.face in ("up", "down"):                                    # an open wedge, apex at the hinge
        a = (np.abs(u) <= v * 1.02 + 0.04).astype(float)
        ang = np.where(v > 1e-3, u / np.maximum(v, 1e-3), 0.0)
        vein = np.clip(1 - np.abs(np.mod(ang * 2.5 + 0.5, 1.0) - 0.5) / 0.12, 0, 1) * _ss(0.1, 0.3, v)
        thin = v
    else:                                                             # the folded strip
        ix, iy, W, Hh = px.texel(ctx)
        thin = iy / max(Hh - 1, 1)
        vein = np.clip(1 - np.abs(np.mod(ctx.local[:, 2] * 6, 1.0) - 0.5) / 0.15, 0, 1) * 0.6
    lv = 0.18 + 0.62 * thin ** 0.8 + 0.06 * px.light(ctx, grad=0.0)
    rgb = _ramp(WINE, lv - 0.22 * vein)
    rgb = _mixc(rgb, _ramp(RIMC, 0.6), _ss(0.9, 1.0, thin) * 0.6)
    return rgb, a, ctx.zeros()


def mat_rod(ctx):
    """Jointed bony rods: ivory with burnished brass knuckles."""
    lv = px.light(ctx, grad=0.08) + 0.05
    loc = ctx.local[:, 2]
    knuck = np.clip(1 - np.abs(np.mod(loc * 3.0, 1.0) - 0.5) / 0.1, 0, 1)
    rgb = _mixc(_ramp(IVORY, lv), _ramp(BRASS, lv), knuck)
    return rgb, ctx.ones(), knuck * (0.5 if _over(ctx) else 0.0)


def mat_rim(ctx):
    lv = px.light(ctx, grad=0.0)
    return _ramp(RIMC, 0.55 + 0.4 * lv), ctx.ones(), np.full(ctx.N, G(ctx, 0.55, 0.85, 1.0))
