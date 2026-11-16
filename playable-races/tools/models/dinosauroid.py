"""Race 007 - The Unknown Dinosauroid.  (v1.5 premium redesign: "the misbred feathered sovereign")

A magnificent feathered impossibility: a powerful theropod leaning forward over strong
thighs, a deep keeled chest, an S-neck carrying a long skull with a hollow hadrosaur crest
sweeping far back over the head, forearms folded as iridescent wings, and a long tapering
tail that ends in a broad fan of individual eyed feathers.

Big shapes first (lathe trunk, swept neck / tail / crest / horns, feather fans with one bone
per feather where they must open); fine detail lives in the textures.

  * skull   - an enlarged braincase; a deep hooked oviraptorosaur beak (glossy black, ivory
              tip) with a row of teeth behind it; ASYMMETRIC supraorbital horns (the right long
              and curving forward, the left a blunt stump); the hollow tubular crest; plume
              tufts behind the eyes; a throat pouch; big amber eyes with slit pupils and a
              nictitating membrane
  * arms    - a folded wing: coverts and secondaries on the forearm, three long primaries
              from the hand reaching the hips; two clawed fingers and the elongated styliform
              digit (a long ivory spike from the wrist along the wing's leading edge)
  * legs    - digitigrade runners: a raised sickle claw on digit II; Microraptor feathers on
              the shank and the metatarsus; hip-to-ankle membranes on two jointed rods
              (folded against the leg at rest, wide sails in the Veer and the Overflow)
  * tail    - five bones; osteoderm plates, Psittacosaurus bristles and side feathers; a
              fan of nine feathers with eye-spots (each its own bone: it opens and closes)

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
from models.common import (accents, ellipsoid, feather_fan, fp_sleeves, frame_rot, humanoid, lathe, lathe_proxy,
                           mat_accent, plate_row, q, side_rot, sweep)

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
PITCH = 34.0                          # theropod posture (trunk axis from vertical)
VEER_LEAN = 20.0                      # extra lean of the Hindwing Veer
# trunk profile in the upright trunk frame: (height above the pivot, radius)
TRUNK_PROFILE = [(-2.25, 2.4), (0.0, 3.35), (2.75, 4.0), (5.5, 4.2), (7.75, 3.75), (9.5, 2.85), (10.75, 2.0)]
TRUNK_SQUASH = (0.84, 1.0)
TRUNK_SKEW = (0.0, -1.0)
NECK = [(0.0, 19.5, -2.25), (0.0, 22.5, -4.25), (0.0, 25.25, -5.0), (0.0, 27.75, -4.5)]
NECK_BASE = NECK[0]
SKULL_PIVOT = NECK[-1]
CRANIUM = ((0.0, 30.0, -6.5), (4.75, 4.5, 5.5))                 # centre, dims of the braincase
EYE = (2.3, 30.0, -8.0)
EYE_RY = 16.0
JAW_PIVOT = (0.0, 28.0, -5.75)
GULAR_PIVOT = (0.0, 27.5, -6.75)
CREST = [(0.0, 30.5, -10.25), (0.0, 32.25, -8.5), (0.0, 33.25, -5.75), (0.0, 34.25, -2.5), (0.0, 35.25, 1.0)]
SHOULDER = (3.5, 19.25, -2.75)
ELBOW = (4.75, 16.0, -0.5)
WRIST = (5.5, 13.0, -2.5)
HIP = (2.75, 13.0, 1.75)
KNEE = (3.0, 8.0, -1.75)
ANKLE = (3.0, 3.75, 2.75)
BALL = (3.0, 0.75, 0.25)
TAIL_PTS = [(0.0, 13.5, 4.0), (0.0, 13.5, 8.5), (0.0, 14.0, 13.0), (0.0, 15.0, 17.5), (0.0, 16.25, 21.5),
            (0.0, 17.25, 24.75)]
FAN_LEN = [8.0, 8.75, 9.25, 9.5, 9.75, 9.5, 9.25, 8.75, 8.0]
FAN_FOLD = 64.0                       # folded fan: total spread (degrees)
FAN_OPEN = 160.0                      # display: total spread


def _v(p):
    return np.asarray(p, float)


def _x(p, s):
    """Mirror a right-side-authored point for side s (-1 right, +1 left): x -> s * |x|."""
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


def vane_cube(m, bone, origin, direction, normal, length, width, mat, thick=0.25, **kw):
    """One feather / blade box: `width` across, `thick` through its plane (normal), `length`
    along `direction` from `origin` (local +Z along the feather: paint with px.vane)."""
    o = _v(origin)
    return m.cube(bone, (o[0] - q(width) / 2, o[1] - thick / 2, o[2]), (q(width), thick, q(length)), mat,
                  pivot=tuple(o), rot=frame_rot(direction, normal), **kw)


def panel(m, bone, top, length, width, mat, **kw):
    """A vertical zero-thickness panel in the YZ plane: hanging `length` down from `top` and
    `width` back (+Z) from it (membranes; solid so that their rims can glow)."""
    x, y, z = top
    return m.cube(bone, (x, y - length, z), (0.0, length, width), mat, faces={"east", "west"}, **kw)


# ============================================================================= build

def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=256)
    humanoid(m)
    # the player's look is cancelled here (pitch on head_g, yaw on hfix, both about the player's
    # head pivot) and re-applied on the neck, which pivots where the neck leaves the chest
    m.bone("hfix", "head_g", (0, 24, 0))
    for g in ("hfix", "r_arm_g", "l_arm_g"):
        piv = NECK_BASE if g == "hfix" else _x(SHOULDER, -1 if g[0] == "r" else 1)
        m.bones[g].variant["veer"] = (lean_offset(piv, VEER_LEAN), None)
    _trunk(m)
    _neck_head(m)
    _arms(m)
    _legs(m)
    _tail(m)
    fp_sleeves(m, "sleeve", width=4.4)
    accents(m, [
        ("c", "breast", "trunk", trunk_to_world((0, 18.25, -2.15)), (4.0, 3.5, 0.5)),
        ("l", "r", "r_thigh", (-4.6, 10.75, 0.25), (0.5, 3.0, 3.0)),
        ("l", "l", "l_thigh", (4.6, 10.75, 0.25), (0.5, 3.0, 3.0)),
        ("f", "r", "r_meta", (-3.0, 2.0, 1.75), (1.75, 1.0, 1.75)),
        ("f", "l", "l_meta", (3.0, 2.0, 1.75), (1.75, 1.0, 1.75)),
    ])
    m.pack()
    return m


# ----------------------------------------------------------------------------- trunk: a deep keeled chest, pitched forward

def _trunk(m: Model) -> None:
    t = m.bone("trunk", "torso_g", TRUNK_PIVOT, (PITCH, 0, 0))
    t.variant["veer"] = ((0, 0, 0), (PITCH + VEER_LEAN, 0, 0))
    lathe(m, t.name, TRUNK_PIVOT, TRUNK_PROFILE, "plume", sides=12, squash=TRUNK_SQUASH, skew=TRUNK_SKEW)
    # osteoderms down the spine (upright trunk frame: +Z is the back)
    px_, py, pz = TRUNK_PIVOT
    plate_row(m, t.name, (0, py + 9.0, pz + 2.6), (0, py + 1.0, pz + 3.6), 4, 1.5, 2.0, 1.75, 0.5, "osteo",
              normal=(0, 0, 1), tilt=14, arch=0.35)
    t.locators["chest"] = trunk_to_world((0, py + 5.0, pz - 4.2))


# ----------------------------------------------------------------------------- neck and head

def _neck_head(m: Model) -> None:
    sweep(m, "hfix", "neck", NECK, 3.75, 2.75, "neck", h0=4.0, h1=3.0, n=2, per_bone=3)
    # n=2 over 3 spans -> 6 cubes; per_bone=3 -> neck0 (lower S), neck1 (upper S)
    na = m.bone("nape", "neck1", (0.0, 28.0, -3.25), (-30.0, 0, 0))
    na.variant.update({v: ((0, 0, 0), (-62.0, 0, 0)) for v in OPEN})
    feather_fan(m, na.name, "nape", (0.0, 28.0, -3.25), 3, [4.0, 5.0, 4.5], [1.5, 1.75, 1.5], "mane",
                spread=30, center=150, plane="side", thick=0.25, bones=False, cutout=True)
    sk = m.bone("skull", "neck1", SKULL_PIVOT)
    sk.variant.update({"display": ((0, 0, 0), (-14.0, 0, 0)), "overflow": ((0, 0, 0), (-8.0, 0, 6.0))})
    c, d = CRANIUM
    ellipsoid(m, sk.name, c, d, "skull", a=0.66, b=0.88)
    m.box(sk.name, (0, 29.75, -9.5), (3.5, 3.0, 2.5), "face")                       # snout between the eyes and the beak
    m.box(sk.name, (0, 28.5, -7.75), (4.25, 2.0, 3.0), "face")                      # cheeks
    m.box(sk.name, (0, 31.5, -8.0), (5.25, 0.75, 2.0), "brow")                      # heavy supraorbital ridge
    # the beak: deep, hooked, oviraptorosaur
    sweep(m, sk.name, "beak", [(0, 30.0, -10.5), (0, 29.75, -11.75), (0, 29.0, -13.0), (0, 27.75, -13.75)],
          3.0, 1.0, "beak", h0=2.75, h1=1.0, n=1, bones=False)
    # a row of teeth behind the beak (cutout planes hanging from the upper jaw line)
    for s in (-1, 1):
        m.cube(sk.name, (s * 1.45, 27.0, -10.75), (0.0, 1.0, 3.5), "teeth", cutout=True, faces={"east", "west"})
    # ASYMMETRIC supraorbital horns: the right long and curving forward, the left a blunt stump
    sweep(m, sk.name, "rhorn", [(-1.75, 31.5, -8.25), (-2.25, 32.75, -8.75), (-2.5, 34.0, -10.0), (-2.25, 34.5, -11.5)],
          1.5, 0.5, "horn", n=1, bones=False)
    sweep(m, sk.name, "lhorn", [(1.75, 31.5, -8.25), (2.0, 32.5, -8.75)], 1.5, 1.25, "horn", n=1, bones=False)
    # jaw
    jw = m.bone("jaw", sk.name, JAW_PIVOT)
    jw.variant.update({"display": ((0, 0, 0), (10.0, 0, 0)), "overflow": ((0, 0, 0), (14.0, 0, 0))})
    sweep(m, jw.name, "jawb", [(0, 27.75, -6.25), (0, 27.5, -9.75), (0, 27.25, -12.75)], 3.25, 1.5, "jaw",
          h0=1.25, h1=0.75, n=1, bones=False)
    # eyes: big, amber, turned a little forward; slit pupils; a nictitating membrane
    for s, p in SIDES:
        ex, ey, ez = s * EYE[0], EYE[1], EYE[2]
        m.cube(sk.name, (ex - 0.25, ey - 1.0, ez - 1.125), (0.5, 2.0, 2.25), "eye", ppu=4.0,
               pivot=(ex, ey, ez), rot=side_rot((0, -EYE_RY, 0), s))
    pu = m.bone("pupils", sk.name, (0, EYE[1], EYE[2]))
    nc = m.bone("nict", sk.name, (0, EYE[1], EYE[2] - 1.0))
    for s, p in SIDES:
        ex, ey, ez = s * EYE[0], EYE[1], EYE[2]
        m.cube(pu.name, (ex + s * 0.27 - 0.05, ey - 0.75, ez - 0.25), (0.1, 1.5, 0.5), "pupil", ppu=4.0,
               pivot=(ex, ey, ez), rot=side_rot((0, -EYE_RY, 0), s))
        m.cube(nc.name, (ex + s * 0.31 - 0.025, ey - 1.0, ez - 1.0), (0.05, 2.0, 0.1), "nict",
               pivot=(ex, ey, ez), rot=side_rot((0, -EYE_RY, 0), s))
    sk.locators["eyes"] = (0, EYE[1], EYE[2] - 1.5)
    # throat pouch: tucked under the jaw at rest, a balloon in the display
    gu = m.bone("gular", sk.name, GULAR_PIVOT)
    ellipsoid(m, gu.name, (0, 26.75, -7.75), (2.75, 2.0, 3.5), "gular", a=0.66, b=0.86, skip=OPEN)
    lathe(m, gu.name, (0, 22.75, -8.0), [(0.0, 1.5), (1.25, 2.5), (2.75, 2.9), (4.0, 2.5), (5.0, 1.5)], "gular_big",
          sides=12, squash=(0.92, 1.08), only=OPEN)
    gu.locators["throat"] = (0, 25.5, -8.0)
    # the hollow tubular crest: from the snout over the skull roof, sweeping far behind
    sweep(m, sk.name, "crest", CREST, 1.75, 2.25, "crest", h0=1.75, h1=2.0, n=2, per_bone=4)
    m.bones["crest0"].variant.update({"display": ((0, 0, 0), (-14.0, 0, 0)), "overflow": ((0, 0, 0), (-10.0, 0, 0))})
    m.bones["crest1"].variant.update({"display": ((0, 0, 0), (-12.0, 0, 0)), "overflow": ((0, 0, 0), (-8.0, 0, 0))})
    tip = _v(CREST[-1])
    d = _dir(CREST[-2], CREST[-1])
    vane_cube(m, "crest1", tip - d * 0.5, d, (0, 1, 0), 1.0, 2.75, "crest_end", thick=2.75)
    m.bones["crest1"].locators["crest_tip"] = tuple(np.round(tip + d * 0.6, 3))
    # plume tufts behind the eyes
    for s, p in SIDES:
        o = (s * 2.25, 30.75, -4.75)
        tf = m.bone(f"{p}_tuft", sk.name, o, side_rot((0, -8, 0), s))
        tf.variant.update({v: ((0, 0, 0), side_rot((-26, -32, 0), s)) for v in OPEN})
        feather_fan(m, tf.name, f"{p}_tf", o, 3, [5.0, 6.0, 4.5], [1.5, 1.75, 1.5], "tuft", spread=34, center=112,
                    plane="side", thick=0.25, bones=False, cutout=True)


# ----------------------------------------------------------------------------- arms: folded wings with three digits

def _arms(m: Model) -> None:
    for s, p in SIDES:
        g = f"{p}_arm_g"
        sh, el, wr = (_v(_x(c, s)) for c in (SHOULDER, ELBOW, WRIST))
        up = m.bone(f"{p}_upper", g, tuple(sh))
        up.variant.update({"display": ((0, 0, 0), side_rot((-24, 0, 38), s)),
                           "overflow": ((0, 0, 0), side_rot((-20, 0, 30), s))})
        sweep(m, up.name, f"{p}_ua", [sh + (0, 0.5, 0), el], 2.5, 2.0, "plume", h0=2.75, h1=2.0, n=1, bones=False)
        fo = m.bone(f"{p}_fore", up.name, tuple(el))
        fo.variant.update({"display": ((0, 0, 0), side_rot((-30, 0, 20), s)),
                           "overflow": ((0, 0, 0), side_rot((-26, 0, 16), s))})
        sweep(m, fo.name, f"{p}_fa", [el, wr], 2.0, 1.5, "plume", n=1, bones=False)
        ha = m.bone(f"{p}_hand", fo.name, tuple(wr))
        m.box(ha.name, tuple(wr + (0.1 * s, -1.0, -0.4)), (1.5, 2.0, 1.75), "scale")
        for dx, dz, ln in ((-0.4, -0.5, 2.25), (0.45, -0.25, 2.0)):
            a = wr + (dx * s, -1.75, dz - 0.4)
            sweep(m, ha.name, f"{p}_cl", [a, a + (0, -ln * 0.7, -ln * 0.45), a + (0, -ln, -ln * 0.3)], 0.6, 0.35, "claw",
                  n=1, bones=False)
        # the styliform digit: a long ivory spike from the wrist back along the wing's leading edge
        st = m.bone(f"{p}_stylus", ha.name, tuple(wr))
        st.variant.update({v: ((0, 0, 0), side_rot((-20, 0, -26), s)) for v in OPEN})
        sweep(m, st.name, f"{p}_st", [wr + (0.55 * s, 0.25, 0.25), wr + (0.7 * s, 2.0, 3.5), wr + (0.75 * s, 3.25, 7.25)],
              0.75, 0.35, "spike", n=1, bones=False)
        # folded wing: secondaries along the forearm, three long primaries from the hand to the hips
        fold = _v((0.0, -0.5, 1.0))
        sec = m.bone(f"{p}_sec", fo.name, tuple(el))
        sec.variant.update({v: ((0, 0, 0), side_rot((-48, 0, 0), s)) for v in OPEN})
        for k, (t, ln) in enumerate(((0.15, 6.0), (0.45, 6.75), (0.75, 7.25))):
            o = el + (wr - el) * t + (0.35 * s, 0, 0)
            dk = fold + _v((0.06 * s, -0.12 * k, 0))
            vane_cube(m, sec.name, o + (0.12 * k * s, 0, 0), dk, (1, 0, 0), ln, 2.5, "flight", cutout=True)
        for k, (ln, ang) in enumerate(((9.0, 0.0), (10.0, 8.0), (10.5, 16.0))):
            pr = m.bone(f"{p}_pri{k}", ha.name, tuple(wr))
            pr.variant.update({v: ((0, 0, 0), side_rot((-40 - 22 * k, 0, 0), s)) for v in OPEN})
            a = math.radians(ang)
            dk = _v((0.04 * s, -0.42 - 0.3 * math.sin(a), 0.9))
            vane_cube(m, pr.name, wr + ((0.0 - 0.12 * k) * s, -0.5, 0.0), dk, (1, 0, 0), ln, 2.5, "flight", cutout=True)


# ----------------------------------------------------------------------------- legs: digitigrade runners with hindwings

def _legs(m: Model) -> None:
    for s, p in SIDES:
        g = f"{p}_leg_g"
        hip, knee, ankle, ball = (_v(_x(c, s)) for c in (HIP, KNEE, ANKLE, BALL))
        th = m.bone(f"{p}_thigh", g, tuple(hip))
        sweep(m, th.name, f"{p}_tg", [hip + (0, 1.25, 0.75), hip + (0.1 * s, -2.0, -1.0), knee + (0, 0, 0.25)],
              4.0, 2.25, "thigh", h0=5.25, h1=2.5, n=1, bones=False)
        sh = m.bone(f"{p}_shin", th.name, tuple(knee))
        sweep(m, sh.name, f"{p}_sn", [knee + (0, 0.5, -0.25), ankle], 2.25, 1.5, "shin", h0=2.5, h1=1.5, n=1, bones=False)
        mt = m.bone(f"{p}_meta", sh.name, tuple(ankle))
        sweep(m, mt.name, f"{p}_mt", [ankle + (0, 0.25, 0.1), ball], 1.5, 1.25, "scale", n=1, bones=False)
        ft = m.bone(f"{p}_foot", mt.name, tuple(ball))
        bx, by, bz = ball
        sweep(m, ft.name, f"{p}_d3", [(bx, 0.6, bz), (bx, 0.5, bz - 2.0), (bx, 0.4, bz - 3.75)], 1.25, 0.75, "toe",
              h0=1.0, h1=0.75, n=1, bones=False)
        sweep(m, ft.name, f"{p}_d4", [(bx + 0.4 * s, 0.6, bz), (bx + 1.3 * s, 0.45, bz - 2.5)], 1.0, 0.75, "toe",
              h0=0.9, h1=0.7, n=1, bones=False)
        m.box(ft.name, (bx - 0.4 * s, 0.5, bz + 1.0), (0.75, 0.75, 1.25), "toe")                 # hallux
        # digit II: raised, carrying the enlarged sickle claw
        tx = bx - 0.8 * s
        tl = m.bone(f"{p}_talon", ft.name, (tx, 0.75, bz))
        sweep(m, tl.name, f"{p}_d2", [(tx, 0.75, bz), (tx, 1.5, bz - 1.25)], 0.9, 0.75, "toe", n=1, bones=False)
        sweep(m, tl.name, f"{p}_sk", [(tx, 1.4, bz - 1.25), (tx, 2.75, bz - 1.75), (tx, 3.0, bz - 2.75), (tx, 2.25, bz - 3.6)],
              0.75, 0.35, "sickle", h0=1.0, h1=0.4, n=1, bones=False)
        tl.locators[f"{p}_sickle"] = (tx, 2.5, bz - 3.0)
        # Microraptor feathers: long feathers down the back of the shank ...
        sf = m.bone(f"{p}_sfan", sh.name, tuple(knee + (0.6 * s, -0.5, 1.0)))
        sf.variant.update({v: ((0, 0, 0), side_rot((0, -20, 72), s)) for v in WINGS})
        for k, (t, ln) in enumerate(((0.1, 7.0), (0.4, 7.5), (0.7, 6.5))):
            o = knee + (ankle - knee) * t + (0.7 * s + 0.1 * k * s, 0, 0.5)
            vane_cube(m, sf.name, o, _v((0.0, -0.55 + 0.1 * k, 0.83)), (1, 0, 0), ln, 2.25, "flight", cutout=True)
        # ... and a metatarsal fan behind the ankle
        lf = m.bone(f"{p}_lfan", mt.name, tuple(ankle + (0.5 * s, 0, 0.5)))
        lf.variant.update({v: ((0, 0, 0), side_rot((0, -26, 80), s)) for v in WINGS})
        for k, ln in enumerate((6.5, 6.0, 5.25)):
            o = ankle + (0.5 * s + 0.1 * k * s, -0.5 * k, 0.5)
            vane_cube(m, lf.name, o, _v((0.0, -0.25 - 0.22 * k, 0.95)), (1, 0, 0), ln, 2.0, "flight", cutout=True)
        # hindwing membranes on two jointed rods: hip -> knee and knee -> ankle
        s0 = m.bone(f"{p}_sail0", th.name, tuple(hip + (1.75 * s, 0.75, 1.0)))
        s0.variant.update({v: ((0, 0, 0), side_rot((0, -8, 76), s)) for v in WINGS})
        _sail(m, s0.name, hip + (1.75 * s, 0.75, 1.0), 6.0, 1.25, 6.5, s)
        s1 = m.bone(f"{p}_sail1", sh.name, tuple(knee + (1.25 * s, 0.25, 0.75)))
        s1.variant.update({v: ((0, 0, 0), side_rot((0, -14, 70), s)) for v in WINGS})
        _sail(m, s1.name, knee + (1.25 * s, 0.25, 0.75), 5.25, 1.25, 6.0, s)


def _sail(m, bone, top, length, folded, wide, s):
    """A membrane panel hanging from `top`, its rod along the free (back) edge: a narrow strip
    folded against the leg, a wide sail in the WINGS variants."""
    top = _v(top)
    for w, cond in ((folded, {"skip": WINGS}), (wide, {"only": WINGS})):
        panel(m, bone, tuple(top), length, w, "membrane", **cond)
        m.cube(bone, (top[0] - 0.3, top[1] - length - 0.25, top[2] + w - 0.3), (0.6, length + 0.5, 0.6), "rod", **cond)


# ----------------------------------------------------------------------------- tail: plates, bristles, side feathers, the fan

def _tail(m: Model) -> None:
    names = sweep(m, "tail_g", "tail", TAIL_PTS, 4.75, 1.25, "tailp", h0=4.25, h1=1.25, n=2, per_bone=2, power=0.85)
    for k, a in enumerate((-6.0, 4.0, 10.0, 14.0, 16.0)):          # display: the tail lifts its fan high
        m.bones[names[k]].variant["display"] = ((0, 0, 0), (-a * 0.5 if k == 0 else -a, 0, 0))
        m.bones[names[k]].variant["overflow"] = ((0, 0, 0), (-a * 0.35 if k == 0 else -a * 0.7, 0, 0))
    m.bones[names[0]].variant["veer"] = ((0, 0, 0), (4.0, 0, 0))
    # ankylosaur osteoderms along the top of the tail base
    plate_row(m, "tail0", (0, 15.75, 4.5), (0, 15.25, 10.5), 3, 1.75, 1.25, 2.0, 0.5, "osteo", tilt=12, arch=0.25)
    # Psittacosaurus bristles standing along the top
    for k, (y, z) in enumerate(((15.25, 10.5), (15.5, 13.5))):
        m.cube(names[1 + k], (0, y - 0.25, z - 1.0), (0.0, 2.75 - 0.5 * k, 3.25), "bristle", cutout=True,
               faces={"east", "west"}, pivot=(0, y, z), rot=(-22, 0, 0))
    # side feathers on the distal tail (a frond)
    for k, (seg, z, ln) in enumerate(((2, 14.5, 4.0), (3, 18.0, 4.5))):
        for s in (-1, 1):
            o = (s * (1.75 - 0.4 * k), TAIL_PTS[seg][1] + 0.6, z)
            vane_cube(m, names[seg], o, _v((0.55 * s, 0.05, 0.84)), (0, 1, 0), ln, 1.75, "flight", cutout=True)
    # the fan: nine eyed feathers, each its own bone (it opens and closes)
    tip = _v(TAIL_PTS[-1])
    fan = m.bone("fan", names[-1], tuple(tip))
    fan.variant.update({"display": ((0, 0, 0), (78.0, 0, 0)), "veer": ((0, 0, 0), (0, 0, 88.0)),
                        "overflow": ((0, 0, 0), (52.0, 0, 0))})
    feathers = feather_fan(m, "fan", "fan", tuple(tip), FAN, FAN_LEN, 2.5, "fanf", spread=FAN_FOLD, center=0.0,
                           plane="flat", thick=0.25, bones=True, cutout=True)
    for k, bn in enumerate(feathers):
        f = 0.5 if FAN == 1 else k / (FAN - 1)
        a0 = -FAN_FOLD / 2 + FAN_FOLD * f
        a1 = -FAN_OPEN / 2 + FAN_OPEN * f
        m.bones[bn].variant.update({v: ((0, 0, 0), (0, a1 - a0, 0)) for v in OPEN})
        m.bones[bn].variant["veer"] = ((0, 0, 0), (0, (a1 - a0) * 0.45, 0))
        # the eye-spot near the tip: a solid inset (cutout feathers cannot glow)
        a = math.radians(a0)
        d = _v((math.sin(a), 0.0, math.cos(a)))
        L = FAN_LEN[k]
        vane_cube(m, bn, tip + d * (L * 0.62), d, (0, 1, 0), 1.75, 1.75, "ocellus", thick=0.5, ppu=4.0)
    fan.locators["tail_fan"] = tuple(tip + (0, 0.5, 5.0))


# ============================================================================= materials (Gate A: flat placeholders)

def materials():
    names = ["plume", "neck", "skull", "face", "brow", "beak", "jaw", "eye", "pupil", "nict", "horn", "crest",
             "crest_end", "gular", "gular_big", "thigh", "shin", "scale", "toe", "claw", "sickle", "spike", "osteo",
             "tailp", "membrane", "rod", "ocellus", "sleeve"]
    mats = {nm: _flat(nm) for nm in names}
    for nm in ("flight", "fanf", "tuft", "mane"):
        mats[nm] = _flat_vane(nm)
    mats["teeth"] = _flat_teeth
    mats["bristle"] = _flat_bristle
    mats["accent"] = mat_accent
    return mats


FLAT = {
    "plume": "#c9a46a", "neck": "#c9a46a", "skull": "#b8935e", "face": "#a5845a", "brow": "#9c7c52", "beak": "#1d1b22",
    "jaw": "#2a2630", "eye": "#e0a020", "pupil": "#120a06", "nict": "#d6dcd6", "horn": "#e8dcc0", "crest": "#e4d6b2",
    "crest_end": "#c8a050", "gular": "#2bb3a6", "gular_big": "#2bb3a6", "thigh": "#c39a62", "shin": "#4f5a2a",
    "scale": "#4f5a2a", "toe": "#46512a", "claw": "#16141a", "sickle": "#1a171e", "spike": "#efe3c6", "osteo": "#d9c48f",
    "tailp": "#c39a62", "membrane": "#7a1f3d", "rod": "#e8d8a8", "ocellus": "#3ad6c8", "sleeve": "#c9a46a",
    "flight": "#1f6f74", "fanf": "#2a5f86", "tuft": "#efe0bb", "mane": "#e2cf9e",
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


def _flat_teeth(ctx):
    ix, iy, W, H = px.texel(ctx)
    tooth = (iy < H - 1 - (ix % 2)) | (iy == 0)
    return np.broadcast_to(px.col("#efe6cf"), (ctx.N, 3)).copy(), tooth.astype(float), ctx.zeros()


def _flat_bristle(ctx):
    ix, iy, W, H = px.texel(ctx)
    strand = (ix % 2 == 0)
    return np.broadcast_to(px.col("#efe6cf"), (ctx.N, 3)).copy(), strand.astype(float), ctx.zeros()
