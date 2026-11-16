"""Race 008 - Bathyas, the Sun-Impaled.  UNIQUE race.  (v1.5 premium redesign)

"A towering abyssal titan with a sun through his heart": an exhausted, irritable old
deep-sea chimera (anglerfish + goblin shark + giant isopod) about 37 px tall even though
he is hunched, carrying a white-gold sword through his chest that is his life support,
his light, his lure, his torment and his weapon.

Design rules (v1.5):
  * grand and legible: a 22 deg hunch from the waist, an 18 px span of layered isopod
    pauldrons, a great arched back of overlapping tergites, two torn dorsal fins, long
    arms with webbed claws, powerful digitigrade legs;
  * a goblin-shark head hung low and forward: a long flat blade of a rostrum over a
    protrusible jaw apparatus with white needle teeth, small ice-blue eyes under long
    white old-man brows, barbels with glowing tips, gill flaps along the neck;
  * midtones, never near-black: navy-teal skin with a lighter belly, pearl-grey armour
    with a lavender sheen;
  * the spectacle reads from every side, above all from the 3rd-person camera behind
    him: the sunburst hilt and a CORONA of thin glowing rays at the chest wound, the blade
    rising out of the hump with a smaller corona at the exit wound, golden light-cracks
    and rows of ice-blue photophores.

Variants: base (Impaled) | lure (the corona blazes) | maw (Goblin Maw Rush: the jaw shoots
forward) | bastion (the plates close, light in the seams) | unshackled (sword drawn: the
wound an open sun, a predator's crouch) | daybreak (arched back, light from every seam).
The held sword is its own small model: build_sword() / sword_materials().

Frames: the upper body is authored UPRIGHT in the "chest" bone's frame and pitched
forward by the bone (chest_world() maps a chest-frame point into the rest pose).  The
arms and head hang from the player's own arm / head bones, so per form the shoulders
follow the chest with a 2-bone IK that keeps the hands (and any held item) where the
player's hands are, and the head is carried by the neck base.
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

from kit.geo import Model, rot_matrix
from kit import pixel as px
from models.common import (accents, ellipsoid, euler_for, fp_sleeves, frame_rot, humanoid, mat_accent, q, rays, side_rot,
                           sweep)

ID = "bathyas"
VARIANTS = ["base", "lure", "maw", "bastion", "unshackled", "daybreak"]
TEXTURES = {
    "base": {"blaze": 0.0, "open": 0.0, "day": 0.0},
    "blaze": {"blaze": 1.0, "open": 0.0, "day": 0.0},
    "unshackled": {"blaze": 0.0, "open": 1.0, "day": 0.0},
    "daybreak": {"blaze": 0.0, "open": 1.0, "day": 1.0},
}
VARIANT_TEXTURE = {"base": "base", "lure": "blaze", "maw": "base", "bastion": "base",
                   "unshackled": "unshackled", "daybreak": "daybreak"}
DRAWN = {"unshackled", "daybreak"}          # the sword is out of his body (unshackled: the real item; daybreak: his own fist)
SEAMED = {"bastion", "daybreak"}            # light leaks between the armour plates
CROUCH = {"unshackled"}                     # the predator's crouch (used by the animation set)

# --------------------------------------------------------------------------- the hunch
CHEST_PIVOT = (0.0, 20.0, 2.0)              # the upper body pitches forward from the waist
HUNCH = 22.0
POSE = {  # chest pitch per form
    "base": HUNCH, "lure": 18.0, "maw": 30.0, "bastion": 36.0, "unshackled": 32.0, "daybreak": 4.0,
}
# legs per form: (thigh, shin, foot) pitch on top of the bent rest geometry
LEG_POSE = {
    "base": (0.0, 0.0, 0.0), "lure": (0.0, 0.0, 0.0), "maw": (-8.0, 12.0, -4.0), "bastion": (-12.0, 18.0, -6.0),
    "unshackled": (-24.0, 38.0, -14.0), "daybreak": (4.0, -4.0, 0.0),
}


def chest_world(p, variant: str = "base", drop: float = 0.0):
    """Rest-pose (world) position of a point given in the upright chest frame."""
    piv = np.array(CHEST_PIVOT)
    return piv + rot_matrix((POSE[variant], 0.0, 0.0)) @ (np.asarray(p, float) - piv) + np.array([0.0, -drop, 0.0])


def chest_local(p, variant: str = "base"):
    """The chest-frame point that lands on world point p (inverse of chest_world, no drop)."""
    piv = np.array(CHEST_PIVOT)
    return piv + rot_matrix((POSE[variant], 0.0, 0.0)).T @ (np.asarray(p, float) - piv)


# --------------------------------------------------------------------------- the impalement (chest frame)
ENTRY = (0.0, 23.0, -3.25)                  # the front wound, under the hanging head: his lure
SWORD_CLIMB = 24.0                          # + the hunch: the blade climbs ~46 deg in the world on its way out
SWORD_YAW = 8.0                             # and leaves a little left of the spine (it reads from behind)
_D = np.array([math.sin(math.radians(SWORD_YAW)) * math.cos(math.radians(SWORD_CLIMB)),
               math.sin(math.radians(SWORD_CLIMB)),
               math.cos(math.radians(SWORD_YAW)) * math.cos(math.radians(SWORD_CLIMB))])


def along(t: float):
    """Point on the sword axis (chest frame), t units from the entry wound toward the back."""
    return tuple(np.array(ENTRY) + _D * t)


EXIT_T = 11.25                              # where the blade leaves the back (through tergite 3)
EXIT = along(EXIT_T)
GUARD_T = -0.75                             # the sunburst guard just in front of the wound
GUARD_Y = 3.0                               # sword-local height of the guard above the grip centre
BLADE_Y = 3.75                              # sword-local height where the blade starts
TIP_Y = 26.25                               # sword-local tip: 30 px from the pommel to the tip
TIP_T = TIP_Y - GUARD_Y + GUARD_T           # the embedded blade is the same sword: 11 px of it out of the back


def _sword_basis():
    """Columns: the embedded sword's local X (blade width), Y (blade) and Z (flat normal) in the chest frame."""
    y = _D / np.linalg.norm(_D)
    z = np.array([0.0, -y[2], y[1]])         # in the sagittal plane, perpendicular to the blade: the flats face
    z = z - y * float(z @ y)                 # down-back (the 3rd-person camera) and up-front (the head)
    z = -z / np.linalg.norm(z)
    x = np.cross(y, z)
    return np.column_stack([x, y, z])


SWORD_ROT = euler_for(_sword_basis())

# --------------------------------------------------------------------------- the back: overlapping tergites
# (centre y, centre z, outward normal angle from +Z toward +Y in degrees, width, length), from the nape down;
# the first seven ride on the chest (upright chest frame), the last two on the waist (world frame)
TERGITES = [  # (y, z, normal angle, centre width, flange width, length)
    (34.1, 1.6, 82.0, 8.0, 2.5, 3.75),
    (33.5, 4.6, 56.0, 9.0, 3.25, 3.75),
    (31.75, 6.35, 30.0, 10.0, 3.5, 3.75),
    (29.25, 6.6, 9.0, 10.0, 3.75, 3.75),
    (26.5, 6.35, -2.0, 9.5, 3.75, 3.75),
    (23.75, 6.25, -8.0, 9.0, 3.5, 3.75),
    (21.25, 6.1, -14.0, 8.5, 3.25, 3.5),
]
WAIST_PLATES = [(17.5, 5.6, -14.0, 8.0, 3.0, 4.0)]
PLATES = TERGITES + WAIST_PLATES             # (the animation set lifts and jostles them in this order)
PLATE_T = 1.25                              # armour thickness
PLATE_LIFT = 17.0                           # the trailing edge of each plate lifts over the next one
PLATE_BEND = 55.0                           # the flanges wrap forward round the flanks

# bastion: the tergites slide together and down over the nape; daybreak: they lift apart (offset along normal, extra tilt)
PLATE_CLOSE = [(-0.35, 10.0), (-0.3, 7.0), (-0.25, 5.0), (-0.2, 3.0), (-0.2, 2.0), (-0.15, 0.0), (-0.1, -2.0),
               (-0.05, -3.0)]
PLATE_OPEN = [(0.5, -10.0), (0.6, -9.0), (0.7, -8.0), (0.7, -7.0), (0.65, -6.0), (0.6, -5.0), (0.5, -4.0),
              (0.45, -4.0)]

# --------------------------------------------------------------------------- shoulders, arms, neck
SHOULDER_C = (7.5, 28.75, 1.25)             # shoulder joint (chest frame, right side mirrored with x < 0)
ELBOW = (8.25, 20.5, 0.0)                   # world rest pose (|x|): a slight bend leaves the arm slack for every form
WRIST = (7.5, 13.5, -1.75)                  # the hand stays here in every form: held items sit in the claws
NECK_C = (0.0, 32.5, -1.0)                  # where the neck leaves the chest (chest frame)
FIN_ROOT = (4.5, 28.75, 7.25)               # the dorsal fins rise from tergite 3 (chest frame, |x|)
FIN_RAYS = ((5.0, 8.75), (28.0, 8.5), (50.0, 7.0))   # (angle from up toward the tail, length) in the fin plane
FLAP_RAY = (68.0, 5.5)                      # the torn trailing flap
FIN_DIRS = {  # per form: world direction of the leading ray (x mirrored) and of the fin's trailing edge
    "base": ((0.42, 1.0, 0.42), (0.62, -0.1, 1.0)),
    "lure": ((0.42, 1.0, 0.45), (0.62, -0.05, 1.0)),
    "maw": ((0.3, 1.0, 0.45), (0.45, -0.2, 1.0)),
    "bastion": ((0.22, 0.55, 1.0), (0.28, -0.75, 1.0)),       # folded flat along the closed shell
    "unshackled": ((0.6, 1.0, 0.1), (0.8, 0.15, 1.0)),
    "daybreak": ((0.62, 1.0, 0.0), (0.75, 0.4, 1.0)),
}


def _shoulder(variant: str, s: int, drop: float = 0.0):
    x, y, z = SHOULDER_C
    return chest_world((s * x, y, z), variant, drop)


def _neck(variant: str, drop: float = 0.0):
    return chest_world(NECK_C, variant, drop)


# --------------------------------------------------------------------------- geometry helpers

def orient(y_axis, z_hint):
    """Euler rotation whose local +Y runs along y_axis exactly and local +Z as close to z_hint as possible."""
    y = np.asarray(y_axis, float)
    y = y / np.linalg.norm(y)
    z = np.asarray(z_hint, float)
    z = z - y * float(z @ y)
    if np.linalg.norm(z) < 1e-6:
        z = np.array([0.0, 0.0, 1.0]) - y * y[2]
    z = z / np.linalg.norm(z)
    x = np.cross(y, z)
    return euler_for(np.column_stack([x, y, z]))


def limb(m: Model, bone: str, top, bottom, w: float, d: float, mat: str, fwd=(0.0, 0.0, -1.0), extend: float = 0.0,
         **kw):
    """A box from `top` down to `bottom`: local Y along the limb, its north face toward `fwd`."""
    a, b = np.asarray(top, float), np.asarray(bottom, float)
    axis = a - b
    L = q(float(np.linalg.norm(axis)) + extend)
    c = (a + b) / 2
    rot = orient(axis, -np.asarray(fwd, float))
    size = (q(w), L, q(d))
    return m.cube(bone, tuple(c - np.array(size) / 2), size, mat, pivot=tuple(c), rot=rot, **kw)


def slab(m: Model, bone: str, center, normal, tangent, w: float, length: float, t: float, mat: str, **kw):
    """A plate: width w across, `length` along `tangent`, thickness t along `normal` (local Y)."""
    rot = frame_rot(tangent, normal)
    size = (q(w), q(t, 0.25), q(length))
    c = np.asarray(center, float)
    return m.cube(bone, tuple(c - np.array(size) / 2), size, mat, pivot=tuple(c), rot=rot, **kw)


def _ang(deg):
    a = math.radians(deg)
    return np.array([0.0, math.sin(a), math.cos(a)])


# ============================================================================= build

def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=256)
    humanoid(m, head_pivot=tuple(_neck("base")))
    _legs(m)
    drop = _settle(m)
    _trunk(m, drop)
    _plates(m)
    _pauldrons(m)
    _fins(m)
    _sword(m)
    _corona(m)
    _arms(m, drop)
    _head(m, drop)
    fp_sleeves(m, "fp_arm", width=4.7)
    accents(m, [
        ("c", "breast", "trunk", (0.0, 19.25, -1.9), (8.5, 2.0, 0.5)),       # a belt plate under the corona
        ("c", "rsh", "r_pauldron", (-6.0, 34.25, 1.5), (4.5, 0.5, 6.5)),
        ("c", "lsh", "l_pauldron", (6.0, 34.25, 1.5), (4.5, 0.5, 6.5)),
        ("l", "r", "r_leg_g", (-6.5, 14.0, 0.25), (0.5, 3.5, 4.0)),
        ("l", "l", "l_leg_g", (6.5, 14.0, 0.25), (0.5, 3.5, 4.0)),
        ("f", "r", "r_foot", (-3.75, 1.5, -3.75), (3.5, 0.5, 2.5)),
        ("f", "l", "l_foot", (3.75, 1.5, -3.75), (3.5, 0.5, 2.5)),
    ])
    m.pack()
    return m


# ----------------------------------------------------------------------------- legs: powerful, digitigrade-ish

HIP = (3.25, 16.0, 0.75)
KNEE = (3.75, 9.75, -2.25)
ANKLE = (3.75, 4.25, 1.5)
BALL = (3.75, 1.25, -1.75)


def _legs(m: Model) -> None:
    for s, g, p in ((-1, "r_leg_g", "r"), (1, "l_leg_g", "l")):
        hip, knee, ankle, ball = (np.array([s * v[0], v[1], v[2]]) for v in (HIP, KNEE, ANKLE, BALL))
        lg = m.bones[g]
        lg.variant.update({v: ((0, 0, 0), (LEG_POSE[v][0], 0.0, 0.0)) for v in VARIANTS if LEG_POSE[v][0]})
        # the thigh: a great muscle mass tapering to the knee
        limb(m, g, (s * 3.25, 17.75, 1.0), (s * 3.5, 12.0, -0.75), 5.5, 6.5, "leg")
        limb(m, g, (s * 3.5, 13.0, -0.5), knee + (0, -0.25, 0.25), 4.75, 5.25, "leg")
        sn = m.bone(f"{p}_shin", g, tuple(knee))
        sn.variant.update({v: ((0, 0, 0), (LEG_POSE[v][1], 0.0, 0.0)) for v in VARIANTS if LEG_POSE[v][1]})
        slab(m, sn.name, knee + (0, 0.25, -2.6), (0, 0.3, -1), (0, 1, 0.3), 4.25, 3.5, 1.0, "plate_limb")  # knee cop
        limb(m, sn.name, knee + (0, 0.75, 0.25), ankle + (0, -0.25, 0), 4.0, 4.25, "leg")                   # the shin
        limb(m, sn.name, knee + (0, -0.75, 2.0), ankle + (0, 1.5, 0.75), 3.25, 2.25, "leg")                 # the calf
        mid = (knee + ankle) / 2
        dn = (ankle - knee) / np.linalg.norm(ankle - knee)
        fw = np.array([0.0, dn[2], -dn[1]])                       # the shin's front normal
        fw = -fw if fw[2] > 0 else fw
        slab(m, sn.name, mid + dn * -0.08 * 5.5 + fw * 2.1, fw, dn, 4.0, 4.25, 0.75, "plate_limb")    # the greave
        m.cube(sn.name, (s * 3.75, 4.75, 1.25), (0.0, 4.0, 3.0), "calf_fin", cutout=True)                       # calf fin
        fb = m.bone(f"{p}_foot", sn.name, tuple(ankle))
        fb.variant.update({v: ((0, 0, 0), (LEG_POSE[v][2], 0.0, 0.0)) for v in VARIANTS if LEG_POSE[v][2]})
        limb(m, fb.name, ankle + (0, 0.25, 0.25), ball + (0, 0.25, -0.25), 3.25, 3.0, "foot", fwd=(0, 0.6, -1))  # raised heel
        m.box(fb.name, (s * 3.75, 0.875, -1.75), (4.25, 1.75, 2.75), "foot")                                    # ball of the foot
        for k, (dx, ang) in enumerate(((-1.5, -12.0), (0.0, 0.0), (1.5, 12.0))):                              # three webbed toes
            x = s * 3.75 + s * dx
            a = math.radians(ang * s)
            d = np.array([math.sin(a) * 0.35, 0.0, -math.cos(a)])
            tip = np.array([x, 0.6, -2.75]) + d * 3.0
            m.cube(fb.name, (x - 0.75, 0.0, -5.75), (1.5, 1.25, 3.25), "foot", pivot=(x, 0.6, -2.5),
                   rot=(0.0, -ang * s, 0.0))
            cl = tip + d * 0.5
            m.cube(fb.name, (cl[0] - 0.375, 0.0, cl[2] - 1.0), (0.75, 1.0, 1.25), "claw", pivot=(cl[0], 0.5, cl[2]),
                   rot=(-10.0, -ang * s, 0.0))
        fb.locators[f"{p}_step"] = (s * 3.75, 0.2, -2.0)


def lowest(m: Model, variant: str, roots=("r_leg_g", "l_leg_g")) -> float:
    """Lowest point (rest pose of `variant`) of every solid cube under `roots` (forward kinematics)."""
    from kit.render import bone_matrices
    M = bone_matrices(m, variant)
    lo = math.inf
    for r in roots:
        for bn in m.subtree(r):
            off = m.variant_offset(bn, variant)
            for c in m.bones[bn].cubes:
                if c.cutout or c.accent or not c.in_variant(variant):
                    continue
                o, s = np.array(c.origin) + off, np.array(c.size)
                pts = np.array([[o[0] + s[0] * i, o[1] + s[1] * j, o[2] + s[2] * k]
                                for i in (0, 1) for j in (0, 1) for k in (0, 1)])
                if c.rot is not None:
                    cp = np.array(c.pivot if c.pivot else c.origin) + off
                    pts = (pts - cp) @ rot_matrix(c.rot).T + cp
                w = np.c_[pts, np.ones(8)] @ M[bn].T
                lo = min(lo, float(w[:, 1].min()))
    return lo


def _settle(m: Model):
    """Hip drop per form: how far the body sinks so that the bent legs stand exactly on the ground."""
    drop = {v: round(lowest(m, v), 3) for v in VARIANTS}
    for v, d in drop.items():
        if abs(d) > 1e-6:
            for g in ("r_leg_g", "l_leg_g"):
                m.bones[g].variant[v] = ((0.0, -d, 0.0), m.bones[g].variant.get(v, ((0, 0, 0), None))[1])
    return drop


# ----------------------------------------------------------------------------- trunk and chest (upright chest frame)

def _trunk(m: Model, drop) -> None:
    for g in ("torso_g", "tail_g"):
        m.bones[g].variant.update({v: ((0.0, -d, 0.0), None) for v, d in drop.items() if d})
    t = m.bone("trunk", "torso_g", (0.0, 12.0, 0.0))
    m.box(t.name, (0.0, 16.25, 1.0), (10.5, 4.0, 7.0), "pelvis")                     # pelvis
    m.box(t.name, (0.0, 19.25, 1.5), (9.5, 3.0, 6.5), "belly")                       # the waist
    c = m.bone("chest", t.name, CHEST_PIVOT, (POSE["base"], 0.0, 0.0))
    c.variant.update({v: ((0, 0, 0), (POSE[v], 0.0, 0.0)) for v in VARIANTS if v != "base"})
    m.box(c.name, (0.0, 24.5, -0.25), (11.5, 7.5, 5.5), "belly", faces={"north", "east", "west", "down"})    # ribcage
    m.box(c.name, (0.0, 24.5, 3.75), (8.5, 7.5, 3.5), "skin", faces={"east", "west", "down"})                # (narrower
    m.box(c.name, (0.0, 29.75, -0.25), (14.0, 4.0, 6.0), "skin", faces={"north", "east", "west", "down", "up"})  # behind,
    m.box(c.name, (0.0, 29.75, 4.0), (10.0, 4.0, 3.5), "skin", faces={"east", "west", "up"})                 # so the plates arch)
    m.box(c.name, (0.0, 32.5, 1.5), (9.5, 2.0, 6.5), "skin", faces={"north", "up", "east", "west"})          # trapezius
    for s in (-1, 1):                                                                     # pectorals over the heart
        m.cube(c.name, (s * 3.25 - 2.875, 24.75, -4.125), (5.75, 4.0, 1.25), "skin", pivot=(s * 3.25, 26.75, -3.5),
               rot=(0.0, s * 8.0, s * 6.0))
        m.box(c.name, (s * 6.0, 24.25, 1.5), (1.0, 6.5, 7.0), "ribs")                   # flank: the lateral line
    c.locators["lure_c"] = (0.0, 25.0, -14.0)
    c.locators["back"] = (0.0, 29.0, 9.5)


# ----------------------------------------------------------------------------- isopod tergites over the back

def _plate(m: Model, bone: str, y: float, z: float, ang: float, core: float, flange: float, ln: float, k: int) -> None:
    n = _ang(ang)                                       # outward normal (YZ plane)
    tng = np.array([0.0, -n[2], n[1]])                  # along the back, pointing down toward the tail
    if tng[1] > 0:
        tng = -tng
    lift = math.radians(PLATE_LIFT)
    tng = tng * math.cos(lift) + n * math.sin(lift)      # the trailing edge lifts over the next plate
    nn0 = np.cross(np.array([1.0, 0.0, 0.0]), tng)
    n = nn0 if nn0 @ n > 0 else -nn0
    c = np.array([0.0, y, z])
    w = core + 2 * flange
    slab(m, bone, c, n, tng, core, ln, PLATE_T, "plate")
    for s in (-1, 1):                                   # the sides bend forward round the flanks: a real arch
        bend = math.radians(PLATE_BEND)
        side = np.array([s * 1.0, 0.0, 0.0])
        nn = n * math.cos(bend) + side * math.sin(bend)
        across = np.cross(tng, nn)
        across = across if across[0] * s > 0 else -across
        edge = c + side * (core / 2 - 0.35)
        slab(m, bone, edge + across * (flange / 2) - nn * 0.2, nn, tng, flange, ln - 0.25, PLATE_T, "plate")
    if k < len(TERGITES):
        slab(m, bone, c + n * (PLATE_T / 2 + 0.3), n, tng, 1.5, ln - 0.75, 0.75, "keel")    # the raised spinal keel
    # light in the seams (bastion, daybreak): a glowing band just under the trailing edge
    slab(m, bone, c - n * 0.45 + tng * (ln / 2 - 0.25), n, tng, w - 1.25, 1.5, 0.5, "seam", only=SEAMED)


def _plates(m: Model) -> None:
    for k, (y, z, ang, core, flange, ln) in enumerate(PLATES):
        par = "chest" if k < len(TERGITES) else "trunk"
        n = _ang(ang)
        b = m.bone(f"plate{k}", par, (0.0, y, z))
        dc, tc = PLATE_CLOSE[k]
        do, to = PLATE_OPEN[k]
        b.variant["bastion"] = (tuple(np.round(n * dc + np.array([0.0, -0.15 * k, 0.0]), 3)), (tc, 0.0, 0.0))
        b.variant["daybreak"] = (tuple(np.round(n * do, 3)), (to, 0.0, 0.0))
        _plate(m, b.name, y, z, ang, core, flange, ln, k)


# ----------------------------------------------------------------------------- pauldrons: four lames over each shoulder

LAMES = [  # (x across, y, outward tilt, width along the slope, depth front-back) in the chest frame
    (5.5, 33.3, 14.0, 4.75, 9.25),
    (7.4, 32.4, 36.0, 4.25, 8.75),
    (8.6, 30.6, 60.0, 3.75, 8.0),
    (9.0, 28.35, 82.0, 3.0, 7.0),
]


def _pauldrons(m: Model) -> None:
    for s, p in ((-1, "r"), (1, "l")):
        sx, sy, sz = SHOULDER_C
        pa = m.bone(f"{p}_pauldron", "chest", (s * sx, sy, sz))
        pa.variant.update({"bastion": ((-s * 0.5, -0.75, -1.25), side_rot((-16.0, 0.0, 14.0), s)),
                           "daybreak": ((s * 0.5, 0.75, 0.25), side_rot((0.0, 0.0, -10.0), s)),
                           "unshackled": ((0.0, 0.25, -0.25), side_rot((-6.0, 0.0, 4.0), s))})
        for k, (x, y, tilt, w, d) in enumerate(LAMES):
            a = math.radians(tilt)
            n = np.array([s * math.sin(a), math.cos(a), 0.0])
            c = np.array([s * x, y, sz + 0.25 - 0.25 * k])
            slab(m, pa.name, c, n, (0, 0, 1), w, d, PLATE_T, "plate")
            if k < 3:                                    # the lame curls down over the front of the shoulder
                fz = c[2] - d / 2
                fn = np.array([s * math.sin(a) * 0.4, math.cos(a) * 0.4, -1.0])
                slab(m, pa.name, (c[0], c[1] - 0.65, fz + 0.15), fn, (0, -1, 0.2), w - 0.5, 1.75, 1.0, "plate")
            if k < 3:
                slab(m, pa.name, c - n * 0.5, n, (0, 0, 1), w - 0.5, d - 1.0, 0.5, "seam", only=SEAMED)


# ----------------------------------------------------------------------------- torn dorsal fins

def fin_rot(variant: str, s: int):
    """Chest-relative rotation of a fin bone whose leading ray / trailing edge point along FIN_DIRS in the world."""
    u, b = (np.array([s * v[0], v[1], v[2]], float) for v in FIN_DIRS[variant])
    y = u / np.linalg.norm(u)
    z = b - y * float(b @ y)
    z = z / np.linalg.norm(z)
    x = np.cross(y, z)
    R = rot_matrix((POSE[variant], 0.0, 0.0)).T @ np.column_stack([x, y, z])
    return tuple(round(a, 2) for a in euler_for(R))


def _fins(m: Model) -> None:
    for s, p in ((-1, "r"), (1, "l")):
        x, y, z = s * FIN_ROOT[0], FIN_ROOT[1], FIN_ROOT[2]
        f0 = m.bone(f"{p}_fin0", "chest", (x, y, z), fin_rot("base", s))
        f0.variant.update({v: ((0, 0, 0), fin_rot(v, s)) for v in VARIANTS if v != "base"})
        for ang, ln in FIN_RAYS:                                     # the rays fan up and back in the fin plane (x = root)
            d = np.array([0.0, math.cos(math.radians(ang)), math.sin(math.radians(ang))])
            a0 = np.array([x, y, z]) + d * 0.25
            limb(m, f0.name, a0 + d * ln, a0, 0.5, 0.5, "ray", fwd=(0, -d[2], d[1]))
        m.cube(f0.name, (x, y, z - 0.5), (0.0, 9.0, 7.5), "fin", cutout=True)                  # the membrane
        f1 = m.bone(f"{p}_fin1", f0.name, (x, y, z))
        ang, ln = FLAP_RAY
        d = np.array([0.0, math.cos(math.radians(ang)), math.sin(math.radians(ang))])
        a0 = np.array([x, y, z]) + d * 0.25
        limb(m, f1.name, a0 + d * ln, a0, 0.5, 0.5, "ray", fwd=(0, -d[2], d[1]))
        m.cube(f1.name, (x, y - 0.75, z + 2.0), (0.0, 6.0, 6.25), "fin_flap", cutout=True)    # the torn trailing flap


# ----------------------------------------------------------------------------- the sun through his heart

def sword_parts(m: Model, bone: str, base, blade_from: float = BLADE_Y, tip: float = TIP_Y, hilt: bool = True,
                **kw) -> None:
    """The sword, shared by the embedded and the held sword.  Local frame: grip centre at
    `base`, blade along +Y, broad faces along +-Z (the width runs along X)."""
    bx, by, bz = base

    def box(cy, w, h, t, mat, rot=None):
        size = (w, h, t)
        c = (bx, by + cy, bz)
        o = tuple(c[i] - size[i] / 2 for i in range(3))
        if rot is None:
            return m.cube(bone, o, size, mat, **kw)
        return m.cube(bone, o, size, mat, pivot=c, rot=rot, **kw)

    if hilt:
        box(-3.0, 1.75, 1.75, 1.75, "s_pommel")                         # pommel: a small sun
        box(-3.0, 1.25, 1.25, 1.25, "s_pommel", rot=(0.0, 45.0, 0.0))  # (an octagon from every side)
        box(-1.85, 1.75, 0.5, 1.25, "s_hilt")                          # collar
        box(0.25, 1.0, 3.75, 1.0, "s_grip")                            # wrapped grip
        box(GUARD_Y, 2.75, 1.0, 2.75, "s_sun")                         # the sun disc at the heart of the guard
        box(GUARD_Y, 2.0, 1.25, 2.0, "s_sun", rot=(0.0, 45.0, 0.0))
        g = (bx, by + GUARD_Y, bz)
        rays(m, bone, g, 8, 1.25, 4.0, 0.5, "s_ray", plane="flat", thick=0.5, phase=0.0, **kw)             # sunburst
    main = tip - 1.75 - blade_from
    box(blade_from + main / 2, 2.5, main, 0.5, "s_blade")
    box(blade_from + main / 2 - 0.25, 0.75, main - 0.5, 1.0, "s_fuller")      # the raised spine: the blade reads edge-on too
    box(tip - 1.25, 1.5, 1.0, 0.5, "s_blade")
    box(tip - 0.375, 0.75, 0.75, 0.5, "s_blade")


def _sword(m: Model) -> None:
    sw = m.bone("sword", "chest", ENTRY, SWORD_ROT)
    ex, ey, ez = ENTRY
    base = (ex, ey - GUARD_Y + GUARD_T, ez)                          # grip centre: the guard sits at GUARD_T
    sword_parts(m, sw.name, base, blade_from=GUARD_Y + EXIT_T - GUARD_T - 0.75, tip=TIP_Y, skip=DRAWN)
    m.cube(sw.name, (ex - 1.25, base[1] + BLADE_Y - 0.25, ez - 0.25), (2.5, 1.75, 0.5), "s_blade", skip=DRAWN)   # into the wound
    sw.locators["hilt"] = (ex, base[1], ez)


def sunburst(m: Model, bone: str, center, plane: str, rays_, depth: float = 0.03, **kw):
    """Tapered rays radiating from `center` in `plane` ("front": XY facing -Z, "back": XY facing +Z).
    rays_: [(angle from up toward +X, r0, r_tip, widths)]: each ray is split into len(widths) segments of
    falling width (a broad root to a thin tip); narrower segments sit a hair closer to the viewer."""
    c = np.asarray(center, float)
    nrm = np.array([0.0, 0.0, -1.0 if plane == "front" else 1.0])
    out = []
    for ang, r0, r1, widths in rays_:
        a = math.radians(ang)
        d = np.array([math.sin(a), math.cos(a), 0.0])
        n_seg = len(widths)
        L = (r1 - r0) / n_seg
        for j, w in enumerate(widths):
            ra = r0 + L * j
            rb = r1 if j == n_seg - 1 else ra + L + 0.25
            p0 = c + d * ra + nrm * (depth * j)
            ln = q(rb - ra)
            out.append(m.cube(bone, (p0[0] - q(w) / 2, p0[1] - 0.125, p0[2]), (q(w), 0.25, ln), "corona" if plane == "front"
                              else "corona_b", pivot=tuple(p0), rot=frame_rot(d, nrm), **kw))
    return out


# the sunbursts: (angle, root radius, tip radius, segment widths) - long / short alternating, a little irregular
CORONA_F = ([(a + j, 2.0, L, (1.5, 1.0, 0.5)) for a, j, L in ((0, 2, 9.5), (60, -3, 8.75), (120, 2, 9.25), (180, -2, 8.25),
                                                            (240, 3, 9.75), (300, -2, 8.5))]
            + [(a + j, 2.0, L, (1.0, 0.5)) for a, j, L in ((30, -2, 6.0), (90, 3, 6.75), (150, -3, 5.5), (210, 2, 6.25),
                                                         (270, -2, 6.5), (330, 3, 5.75))])
CORONA_BLAZE = [(a, 3.5, L, (0.75, 0.5)) for a, L in ((15, 14.0), (75, 12.75), (135, 13.5), (195, 12.5), (255, 14.5),
                                                     (315, 13.0))]      # lure / the open sun: long spikes between
CORONA_B = ([(a + j, 1.5, L, (1.0, 0.75, 0.5)) for a, j, L in ((0, 0, 6.25), (90, 4, 5.5), (180, -3, 5.75), (270, 2, 6.0))]
            + [(a + j, 1.5, L, (0.75, 0.5)) for a, j, L in ((45, 3, 4.0), (135, -2, 4.5), (225, 2, 3.75), (315, -3, 4.25))])


def _corona(m: Model) -> None:
    """The light at both wounds: thin glowing rays radiating in a circle, tapering and fading outward."""
    x, y, _ = ENTRY
    cz = -4.6                                                         # in front of the pectorals
    c = (x, y, cz)
    cf = m.bone("corona_f", "chest", c)
    hide = {"bastion"}                                                # bastion: the light is shut inside the plates
    sunburst(m, cf.name, c, "front", CORONA_F, skip=hide)
    sunburst(m, cf.name, (x, y, cz - 0.1), "front", CORONA_BLAZE, only={"lure"})
    sunburst(m, cf.name, (x, y, cz - 0.1), "front", [(a + 30, 3.5, L - 2.0, (0.5,)) for a, _, L, _ in CORONA_BLAZE],
             only=DRAWN)                                             # the open sun: thin glints between the rays
    m.box(cf.name, (x, y, cz + 0.25), (3.0, 3.0, 0.5), "core", skip=hide | DRAWN)               # the glare at the wound
    m.box(cf.name, (x, y, cz + 0.05), (2.5, 4.5, 0.5), "core", only=DRAWN)                      # the open sun
    m.box(cf.name, (x, y, cz + 0.1), (4.5, 2.5, 0.5), "core", only=DRAWN)
    m.box(cf.name, (x, y, cz - 0.2), (2.5, 2.5, 0.5), "core_hot", only=DRAWN)
    cf.locators["wound"] = (x, y, cz - 0.5)
    # the exit wound: a smaller sunburst in the plane of the back plates, above the keel
    ex, ey, ez = EXIT
    pz = 8.0
    cb = m.bone("corona_b", "chest", (ex, ey, pz), (12.0, 0.0, 0.0))
    sunburst(m, cb.name, (ex, ey, pz), "back", CORONA_B)
    m.box(cb.name, (ex, ey, pz - 0.2), (2.75, 2.75, 0.5), "core")
    cb.locators["wound_back"] = (ex, ey, pz + 0.5)


# ----------------------------------------------------------------------------- long arms, webbed claws

def _ik(S0, E0, W0, S1):
    """Pitch (about X) of the upper arm and forearm that keep the wrist at W0 when the shoulder moves to S1."""
    S0, E0, W0, S1 = (np.asarray(v, float) for v in (S0, E0, W0, S1))
    u0, f0 = E0 - S0, W0 - E0

    def wrist(a, b):
        return S1 + rot_matrix((a, 0, 0)) @ u0 + rot_matrix((a + b, 0, 0)) @ f0

    best = (1e9, 0.0, 0.0)
    for a in np.arange(-60, 60.1, 1.0):
        for b in np.arange(-60, 60.1, 1.0):
            e = float(np.linalg.norm(wrist(a, b) - W0))
            if e < best[0]:
                best = (e, a, b)
    e, a, b = best
    step = 0.5
    while step > 0.01:
        for da, db in ((step, 0), (-step, 0), (0, step), (0, -step)):
            e2 = float(np.linalg.norm(wrist(a + da, b + db) - W0))
            if e2 < e:
                e, a, b = e2, a + da, b + db
                break
        else:
            step /= 2
    return round(float(a), 2), round(float(b), 2), e


FINGER_Z = (-3.0, -1.75, -0.5)
FINGER_FAN = (-12.0, 0.0, 12.0)


def _arms(m: Model, drop) -> None:
    for s, g, p in ((-1, "r_arm_g", "r"), (1, "l_arm_g", "l")):
        S0 = _shoulder("base", s)
        E0 = np.array([s * ELBOW[0], ELBOW[1], ELBOW[2]])
        W0 = np.array([s * WRIST[0], WRIST[1], WRIST[2]])
        up = m.bone(f"{p}_upper", g, tuple(S0))
        fo = m.bone(f"{p}_fore", up.name, tuple(E0))
        hd = m.bone(f"{p}_hand", fo.name, tuple(W0))
        for v in VARIANTS:
            if v == "base":
                continue
            S1 = _shoulder(v, s, drop.get(v, 0.0))
            a, b, err = _ik(S0, E0, W0, S1)
            up.variant[v] = (tuple(np.round(S1 - S0, 3)), (a, 0.0, 0.0))
            fo.variant[v] = ((0.0, 0.0, 0.0), (b, 0.0, 0.0))
            hd.variant[v] = ((0.0, 0.0, 0.0), (round(-(a + b), 2), 0.0, 0.0))
        dl = m.bone(f"{p}_delt", up.name, tuple(S0))                   # (hidden in first person: it sits above the eye line)
        m.box(dl.name, tuple(S0 + (s * 0.25, -0.75, 0.25)), (4.75, 4.75, 5.0), "arm")      # the deltoid under the pauldron
        limb(m, dl.name, S0 + (0, -1.75, 0), E0 + (0, 0.25, 0), 4.0, 4.0, "arm")         # upper arm
        # the forearm: massive, shelled on the outside, a torn fin trailing behind
        limb(m, fo.name, E0 + (0, 0.75, 0.25), W0 + (0, -0.25, 0), 5.0, 5.25, "fore")
        ax = (E0 - W0) / np.linalg.norm(E0 - W0)
        mid = (E0 + W0) / 2
        out = np.array([s * 1.0, 0.0, 0.0])
        for k, f in enumerate((0.22, -0.16)):                                              # vambrace lames
            slab(m, fo.name, mid + ax * f * 7.0 + out * (2.7 + 0.1 * k), out, -ax, 4.0, 3.25, 0.75, "plate_limb")
        slab(m, fo.name, E0 + (0, -0.5, 2.5), (0, -0.2, 1), (0, -1, 0), 3.25, 2.75, 0.75, "plate_limb")  # elbow cop
        m.cube(fo.name, (s * 8.0, 14.25, 1.0), (0.0, 5.0, 3.5), "calf_fin", cutout=True)                    # forearm fin
        # the hand: palm, three long webbed fingers with hard white claws, a thumb
        hz = W0[2]
        m.box(hd.name, (s * 7.5, 12.0, hz), (3.0, 3.0, 3.75), "hand")
        m.cube(hd.name, (s * 7.5, 7.0, hz - 1.75), (0.0, 3.75, 3.5), "web", cutout=True)
        for k, (fz, fan) in enumerate(zip(FINGER_Z, FINGER_FAN)):
            f = m.bone(f"{p}_finger{k}", hd.name, (s * 7.5, 10.5, fz), (fan, 0.0, 0.0))
            m.box(f.name, (s * 7.5, 8.875, fz), (1.25, 3.25, 1.25), "hand")
            m.cube(f.name, (s * 7.5 - 0.5, 5.75, fz - 0.6), (1.0, 2.0, 1.0), "claw", pivot=(s * 7.5, 7.25, fz),
                   rot=(-16.0, 0.0, 0.0))
        th = m.bone(f"{p}_thumb", hd.name, (s * 6.5, 11.75, hz - 1.75), side_rot((-24.0, 0.0, -14.0), s))
        m.box(th.name, (s * 6.5, 10.0, hz - 1.75), (1.25, 3.25, 1.25), "hand")
        hd.locators[f"{p}_claws"] = (s * 7.5, 6.0, hz)
        if s > 0:                                # daybreak (the ultimate's Solar Execution): the sun torn out, in his LEFT fist
            palm = (s * 7.5, 11.75, hz)
            sun = m.bone("l_sun", hd.name, palm, orient((0.0, 0.42, -0.91), (0.0, 0.91, 0.42)), only={"daybreak"})
            sword_parts(m, sun.name, palm)
            sun.locators["sun_tip"] = (palm[0], palm[1] + TIP_Y, palm[2])


# ----------------------------------------------------------------------------- the head: goblin shark, hung low and forward

HEAD_PITCH = 15.0                           # the head hangs nose-down from the neck
HEAD_DY = 1.75
HEAD_POSE = {   # extra (offset, rotation) of the head per form, on top of following the neck
    "base": ((0.0, 0.0, 0.0), (HEAD_PITCH, 0.0, 0.0)),
    "lure": ((0.0, 0.5, 1.25), (0.0, 14.0, 6.0)),        # recoils from his own light, turned aside
    "maw": ((0.0, -0.75, -1.75), (14.0, 0.0, 0.0)),      # thrust forward and down
    "bastion": ((0.0, -0.75, 2.5), (30.0, 0.0, 0.0)),    # tucked under the shell
    "unshackled": ((0.0, -0.75, -1.0), (10.0, 0.0, 0.0)),  # low and forward, a level stare
    "daybreak": ((0.0, 0.75, 1.25), (-16.0, 0.0, 0.0)),  # thrown back as the light floods out
}


def _head(m: Model, drop) -> None:
    N0 = _neck("base")
    m.bones["head_g"].variant.update({v: ((0.0, -d, 0.0), None) for v, d in drop.items() if d})
    sk = m.bone("skull", "head_g", tuple(N0), HEAD_POSE["base"][1])
    for v in VARIANTS:
        if v == "base":
            continue
        dn = _neck(v, drop.get(v, 0.0)) - N0 + np.array([0.0, drop.get(v, 0.0), 0.0])   # head_g already dropped
        off, rot = HEAD_POSE[v]
        sk.variant[v] = (tuple(np.round(dn + np.array(off), 3)), rot)
    # neck and skull (authored HEAD_DY higher than the original sketch; the neck bridges down from the chest)
    def P(x, y, z):
        return (x, y + HEAD_DY, z)

    limb(m, sk.name, (0, 31.25, -4.5), P(0, 27.5, -9.25), 5.5, 5.5, "neck", fwd=(0, -1, -0.3))
    ellipsoid(m, sk.name, P(0, 28.75, -10.5), (6.5, 5.5, 6.0), "head", a=0.7, b=0.88)          # the old bald dome
    m.box(sk.name, P(0, 25.75, -10.25), (6.75, 2.5, 4.5), "jowl")                              # sagging jowls
    m.box(sk.name, P(0, 30.0, -13.25), (6.75, 1.5, 2.0), "brow")                               # the heavy brow ridge
    # the rostrum: a long flattened blade tapering to a point, thick where it leaves the face
    sweep(m, sk.name, "ros", [P(0, 28.75, -13.0), P(0, 29.0, -16.75), P(0, 29.75, -21.0)], 4.5, 0.5, "snout", h0=2.0,
          h1=0.5, n=4, bones=False, normal=(0, 1, 0))
    for s, p in ((-1, "r"), (1, "l")):
        m.box(sk.name, P(s * 2.4, 28.75, -13.9), (1.0, 0.75, 0.75), "eye", ppu=4.0)            # small ice-blue eyes
        m.cube(sk.name, P(s * 3.3, 25.0, -9.0), (0.0, 4.0, 4.5), "wisp", cutout=True)            # an old man's last wisps
        lid = m.bone(f"lid_{p}", sk.name, P(s * 2.4, 29.2, -14.05))                              # (scale y to squint / blink)
        m.cube(lid.name, P(s * 2.4 - 0.55, 28.95, -14.4), (1.1, 0.25, 0.6), "lid")
        br = m.bone(f"brow_{p}", sk.name, P(s * 2.0, 30.25, -14.0), side_rot((0.0, 0.0, 8.0), s))
        m.box(br.name, P(s * 2.1, 30.6, -13.9), (2.5, 0.75, 1.0), "hair")                      # the white tuft on the brow
        for k, (dy, dz) in enumerate(((0.0, 0.0), (-0.6, 0.9))):                                # long brows drooping out and
            pts = [P(s * 3.0, 30.5 + dy, -14.0 + dz), P(s * 4.5, 29.6 + dy, -13.6 + dz),        # down past the cheeks
                   P(s * 5.4, 27.75 + dy, -12.75 + dz)]
            sweep(m, br.name, f"brow_{p}{k}", pts, 0.75, 0.5, "hair", h0=0.5, h1=0.5, n=1, bones=False)
        for k in range(2):                                                                       # gill flaps
            gz = -7.0 - k * 1.25
            gl = m.bone(f"gill_{p}{k}", sk.name, P(s * 2.75, 28.0, gz - 0.5))
            m.cube(gl.name, P(s * 2.75 - 0.125, 25.0, gz - 0.5), (0.25, 3.0, 1.5), "gill")
    # the protrusible jaw apparatus
    jw = m.bone("jaws", sk.name, P(0, 26.5, -11.5))
    jw.variant["maw"] = ((0.0, -0.5, -4.5), (4.0, 0.0, 0.0))
    m.box(jw.name, P(0, 26.25, -15.25), (4.25, 1.0, 5.0), "lip")                               # upper jaw under the snout
    m.box(jw.name, P(0, 25.375, -15.25), (3.75, 1.25, 4.5), "teeth", cutout=True)              # needle teeth (upper row)
    m.box(jw.name, P(0, 25.5, -11.625), (3.5, 2.0, 6.75), "gum")                               # the sling: it stretches out
    lo = m.bone("jaw", jw.name, P(0, 25.5, -12.0))
    lo.variant.update({"maw": ((0, 0, 0), (40.0, 0.0, 0.0)), "daybreak": ((0, 0, 0), (14.0, 0.0, 0.0)),
                       "unshackled": ((0, 0, 0), (6.0, 0.0, 0.0))})
    m.box(lo.name, P(0, 24.25, -15.0), (4.75, 1.25, 6.25), "jaw")                              # the underbite
    m.box(lo.name, P(0, 25.375, -15.5), (3.75, 1.25, 4.75), "teeth", cutout=True)              # needle teeth (lower row)
    for s, p in ((-1, "r"), (1, "l")):                                                          # barbels with glowing tips
        sweep(m, lo.name, f"barbel_{p}", [P(s * 2.0, 23.75, -15.25), P(s * 2.75, 21.5, -14.5), P(s * 3.25, 19.0, -13.5)],
              0.75, 0.75, "barbel", n=1)
    lo.locators["maw"] = P(0.0, 25.0, -18.0)
    sk.locators["eyes"] = P(0.0, 28.75, -14.25)
    sk.locators["gills"] = P(0.0, 26.5, -7.75)


# ============================================================================= materials
#
# Premium painting (kit/pixel.py v1.5): continuous ramps, light from the smooth form, soft rims and
# occlusion, and light as DESIGNED patterns - golden cracks radiating from both wounds, rows of
# ice-blue photophores, the white-gold sword and its coronas.  Midtones everywhere: the renderer
# (and Bedrock) darken back faces to about half, so the ramps sit high.

SKIN = px.pal("#0e1f2e", "#173444", "#1d3a4a", "#2a5262", "#3f6a78", "#5a8c99", "#86bcc4")
BELLY = px.pal("#22404c", "#33596a", "#4a7482", "#66919b", "#8bb3b8", "#b4d4d4")
DAYSKIN = px.pal("#1e0f06", "#36200e", "#553318", "#764822", "#98622f", "#bc8448", "#e2b06c")      # burnt bronze
DAYBELLY = px.pal("#3a200e", "#5a3517", "#7c4c22", "#a0682f", "#c48a46", "#e6b46c")
WET = px.col("#a6e6ea")                     # wet cyan highlight
WARM = px.pal("#5e2f12", "#a65a1e", "#e09238", "#ffc867", "#ffe7a8")     # the sun's light on skin
ARMOR = px.pal("#3a3e54", "#5b6178", "#7a8099", "#9aa0bb", "#b8bdd4", "#d2d6ea", "#eef0fa")
LAVENDER = px.col("#c4b9ec")
PEARL_CYAN = px.col("#cfeef2")
SEAMLINE = px.col("#262a3e")
SUN = px.pal("#8a3a0c", "#c8621a", "#f3982c", "#ffc75a", "#ffe8a4", "#fff8e2", "#ffffff")
GOLD = px.pal("#4a2a0c", "#7a4e18", "#b07c2c", "#dcaa48", "#f6d47a", "#fff0bc")
STEEL = px.pal("#a87f42", "#d3ae6e", "#eed69e", "#faedc9", "#fffbec")
PHOTO_RIM, PHOTO_MID, PHOTO_CORE = px.col("#3aa6d6"), px.col("#8fe2fb"), px.col("#effcff")
BONE = px.pal("#6c717d", "#a2a8b4", "#d0d4dc", "#eef0f4", "#ffffff")
GILL = px.pal("#2c0a12", "#521624", "#7a2636", "#a2445a")
HAIR = px.pal("#8f98a3", "#b9c1c9", "#dee3e8", "#f6f8fa", "#ffffff")
LEATHER = px.pal("#1b110a", "#2e1d10", "#463019", "#664627")
FIN = px.pal("#183442", "#24495a", "#346a7a", "#4f8a98", "#78b0ba", "#a6d2d6")

_RC = rot_matrix((HUNCH, 0.0, 0.0))
_RH = rot_matrix((HEAD_PITCH, 0.0, 0.0))
_N0 = None


def _P(ctx):
    p = ctx.params
    return p.get("blaze", 0.0), p.get("open", 0.0), p.get("day", 0.0)


def _wp(ctx):
    return ctx.wp if ctx.wp is not None else ctx.p


def _wn(ctx):
    return ctx.wn if ctx.wn is not None else ctx.n


def _cf(ctx):
    """Texel positions in the upright chest frame (for everything that rides on the chest)."""
    piv = np.array(CHEST_PIVOT)
    return (_wp(ctx) - piv) @ _RC + piv


def _cfn(ctx):
    return _RC.T @ _wn(ctx)


def _head_w(p):
    """World rest position of a head point authored like the head geometry (before HEAD_DY)."""
    n0 = _neck("base")
    a = np.array([p[0], p[1] + HEAD_DY, p[2]])
    return n0 + _RH @ (a - n0)


def _mix(a, b, t):
    t = np.clip(np.asarray(t, float), 0, 1)
    if t.ndim == 1:
        t = t[:, None]
    return a * (1 - t) + b * t


def _h(ix, iy, seed):
    v = np.sin(ix * 12.9898 + iy * 78.233 + seed * 37.719) * 43758.5453
    return v - np.floor(v)


def _spots(P, centers, radius, core=0.35):
    g = np.zeros(len(P))
    for c in centers:
        d = np.linalg.norm(P - np.asarray(c, float), axis=1) / radius
        t = np.clip((1 - d) / (1 - core), 0, 1)
        g = np.maximum(g, t * t * (3 - 2 * t))
    return g


def _seg2(q, a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((q - a) @ ab) / max(float(ab @ ab), 1e-9), 0, 1)
    return np.linalg.norm(q - (a + t[:, None] * ab), axis=1)


def _pdist(q, lines):
    d = np.full(len(q), 99.0)
    for pl in lines:
        for a, b in zip(pl[:-1], pl[1:]):
            d = np.minimum(d, _seg2(q, a, b))
    return d


# ----------------------------------------------------------------------------- light: photophores and cracks

def photophores(rgb, glow, g, gold=False):
    """Paint ice-blue photophores (gold in daybreak) where g (0..1) is non-zero."""
    rim, mid, core = ((px.col("#c8781e"), px.col("#ffc867"), px.col("#fff6d6")) if gold else
                      (PHOTO_RIM, PHOTO_MID, PHOTO_CORE))
    c = np.where((g > 0.85)[:, None], core, np.where((g > 0.45)[:, None], mid, rim))
    on = g > 0.12
    rgb = np.where(on[:, None], _mix(rgb, c, np.clip(g * 1.4, 0, 1)), rgb)
    glow = np.where(on, np.maximum(glow, 0.35 + 0.6 * g), glow)
    return rgb, glow


# the designed crack pattern on the chest, in the chest frame unwrapped round the flanks (u, y): it radiates
# from the heart wound up over the pectorals to both shoulders, along the ribs round the flanks, and down
CRACKS_F = [
    [(0.0, 23.0), (-1.25, 24.5), (-2.0, 26.0), (-3.5, 27.25), (-5.0, 28.0), (-6.5, 29.5), (-7.5, 31.0)],
    [(-3.5, 27.25), (-4.0, 28.75), (-3.75, 30.5)],
    [(0.0, 23.0), (1.0, 24.75), (2.25, 25.75), (3.25, 27.5), (4.75, 28.25), (6.25, 29.75), (7.25, 31.25)],
    [(2.25, 25.75), (3.75, 25.5), (5.25, 26.25), (6.25, 25.75)],
    [(0.0, 23.0), (-1.75, 22.5), (-3.25, 22.75), (-4.5, 22.0), (-5.75, 21.5), (-7.5, 21.25), (-9.0, 22.0), (-10.5, 21.5)],
    [(-4.5, 22.0), (-5.25, 23.75), (-6.75, 24.5), (-8.25, 24.0)],
    [(0.0, 23.0), (1.5, 22.25), (3.0, 22.5), (4.5, 21.75), (5.75, 22.25), (7.25, 21.75), (8.75, 22.5), (10.25, 22.0)],
    [(0.0, 23.0), (-0.75, 21.5), (-1.5, 20.75), (-1.25, 19.5), (-2.25, 18.5)],
    [(0.0, 23.0), (0.5, 21.25), (1.75, 20.5), (2.0, 19.25), (3.25, 18.75)],
    [(0.0, 23.0), (-0.5, 24.25), (0.25, 25.25), (-0.25, 26.5)],
]
# ... and on the back round the exit wound, in the chest frame (x, y), seen from behind
CRACKS_B = [
    [(1.4, 27.6), (2.5, 29.0), (3.5, 30.75), (5.0, 31.75), (6.75, 33.0)],
    [(1.4, 27.6), (0.25, 29.25), (-1.25, 30.5), (-2.75, 31.25), (-4.5, 32.5), (-6.25, 33.25)],
    [(1.4, 27.6), (-0.5, 27.0), (-2.0, 27.5), (-3.75, 26.75), (-5.5, 27.25), (-7.0, 26.5)],
    [(1.4, 27.6), (3.25, 27.0), (5.0, 27.5), (6.5, 26.75), (7.75, 27.25)],
    [(1.4, 27.6), (1.0, 26.0), (1.75, 24.5), (0.75, 23.0), (1.5, 21.5), (0.5, 20.0)],
    [(1.4, 27.6), (2.75, 26.0), (4.0, 24.75), (5.5, 23.75), (6.5, 22.25)],
    [(1.4, 27.6), (0.0, 26.25), (-1.5, 25.0), (-3.0, 23.5), (-4.25, 22.75)],
]
# ... and over the tops of the shoulders (chest frame, seen from above: x, z)
CRACKS_S = [
    [(-4.0, 0.25), (-5.0, -0.75), (-6.25, 0.25), (-7.25, -0.5), (-8.5, 0.5), (-9.75, 0.0)],
    [(-6.25, 0.25), (-6.75, 2.0), (-7.75, 3.0)],
    [(4.0, 0.5), (5.25, -0.5), (6.25, 0.5), (7.5, -0.25), (8.75, 0.75), (9.75, 0.25)],
    [(7.5, -0.25), (8.0, -2.0), (9.0, -2.75)],
]


def _reach(ctx):
    """How far (px) the cracks reach from the wounds, and how hot they burn, per texture set."""
    blaze, open_, day = _P(ctx)
    if open_ or day:
        return 40.0, 1.0
    return (13.0, 0.95) if blaze else (11.5, 0.8)


def crack(rgb, glow, d, r, reach, heat, width=0.3):
    """Two-tone light-cracks: a white-gold core, an amber rim; they cool with distance r from the wound."""
    fade = np.clip(1 - r / reach, 0, 1)
    core = (d < width) & (fade > 0.02)
    rim = (d < width + 0.34) & ~core & (fade > 0.1)
    rgb = np.where(core[:, None], px.smooth_ramp(SUN, 0.48 + 0.24 * fade + 0.14 * (heat > 0.9)), rgb)   # gold, white-hot only near
    rgb = np.where(rim[:, None], _mix(rgb, SUN[2], 0.35 + 0.35 * fade), rgb)
    glow = np.where(core, np.maximum(glow, (0.42 + 0.53 * fade) * heat), glow)
    glow = np.where(rim, np.maximum(glow, 0.22 * fade * heat), glow)
    return rgb, glow


def chest_cracks(ctx, rgb, glow):
    """The designed cracks on everything that rides on the chest (front, flanks, shoulders, back)."""
    reach, heat = _reach(ctx)
    P = _cf(ctx)
    n = _cfn(ctx)
    if n[1] > 0.6 and abs(n[2]) < 0.6:                        # facing up: the shoulder tops
        d = _pdist(P[:, [0, 2]], CRACKS_S)
        r = np.linalg.norm(P - np.array(ENTRY), axis=1)
        return crack(rgb, glow, d, r, reach + 1.0, heat)
    if n[2] < 0.35:                                           # front and flanks
        u = np.where(abs(n[0]) > 0.5, np.sign(n[0]) * (np.abs(P[:, 0]) + (P[:, 2] + 3.0)), P[:, 0])
        q = np.stack([u, P[:, 1]], axis=1)
        d = _pdist(q, CRACKS_F)
        r = np.hypot(q[:, 0] - ENTRY[0], q[:, 1] - ENTRY[1])
        return crack(rgb, glow, d, r, reach, heat)
    d = _pdist(P[:, :2], CRACKS_B)                          # the back, round the exit wound
    r = np.hypot(P[:, 0] - EXIT[0], P[:, 1] - EXIT[1])
    return crack(rgb, glow, d, r, reach * 0.8, heat)


ZIG = (0, 0, 1, 1, 1, 0, 0, -1, -1, -1)       # a crack's walk down a face, one texel at a time


def limb_cracks(ctx, rgb, glow, seed=0):
    """Unshackled / daybreak: the cracks blaze across the whole body - a continuous zigzag split down
    most limb faces with a branch, cooling with distance from the heart (designed, never speckle)."""
    blaze, open_, day = _P(ctx)
    if not (open_ or day) or not px.side(ctx):
        return rgb, glow
    ix, iy, W, H = px.texel(ctx)
    if H < 5 or W < 3:
        return rgb, glow
    k = ctx.seed * 3 + len(ctx.face) * 7 + seed
    if _h(np.array([k]), np.array([1]), 5)[0] > 0.5:                  # about half the faces
        return rgb, glow
    x0 = 1 + int(_h(np.array([k]), np.array([2]), 9)[0] * max(W - 2, 1))
    zz = np.array(ZIG)[(iy + k) % len(ZIG)]
    x_line = np.clip(x0 + zz, 0, W - 1)
    on = ix == x_line
    b = H // 2 + (k % 3) - 1                                             # one branch splits off sideways
    sgn = 1 if x0 < W / 2 else -1
    on |= (iy > b) & (iy <= b + 3) & (ix == np.clip(x_line + sgn * (iy - b), 0, W - 1))
    r = np.linalg.norm(_wp(ctx) - np.array(chest_world(ENTRY)), axis=1)
    return crack(rgb, glow, np.where(on, 0.0, 9.0), r, 36.0, 0.85)


def sun_spill(ctx, reach: float = 9.0):
    """0..1: the warm light of the wound falling on nearby skin that faces it."""
    blaze, open_, day = _P(ctx)
    c = np.array(chest_world(ENTRY)) + np.array([0.0, 0.0, -1.0])
    d = c[None, :] - _wp(ctx)
    dist = np.maximum(np.linalg.norm(d, axis=1), 1e-6)
    facing = np.clip((d @ _wn(ctx)) / dist + 0.25, 0, 1)
    R = reach * (1.35 if blaze else 1.0) * (1.25 if open_ else 1.0)
    return np.clip((1 - dist / R), 0, 1) ** 1.6 * facing * (1.2 if (blaze or open_) else 0.85)


# ----------------------------------------------------------------------------- skin

def pillow(ctx, edge=0.16, grad=0.12, rim=0.08):
    """Light level of a limb box painted as a rounded form: real face direction, darker toward the
    face's side edges, lighter toward the top, a soft rim along the top edge."""
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx, grad=0.0)
    if px.side(ctx):
        u = (ix + 0.5) / W * 2 - 1
        lv = lv - edge * u ** 2 + grad * (0.5 - (iy + 0.5) / H)
        if H >= 4:
            lv = lv + rim * (iy == 0)
    else:
        u = (ix + 0.5) / W * 2 - 1
        v = (iy + 0.5) / H * 2 - 1
        lv = lv - edge * 0.5 * (u ** 2 + v ** 2)
    return lv


def skin_pal(ctx, belly=False):
    blaze, open_, day = _P(ctx)
    if day > 0.5:
        return DAYBELLY if belly else DAYSKIN
    return BELLY if belly else SKIN


def skin(ctx, lv, belly=False, spill=1.0, wet=True, seed=0):
    """Skin colour for light level lv: the navy-teal ramp (lighter belly), wet cyan highlights on the
    brightest texels, sparse wet glints along upper edges, the warm light of the wound."""
    ix, iy, W, H = px.texel(ctx)
    pal = skin_pal(ctx, belly)
    wn = _wn(ctx)
    lv = lv - 0.12 * max(wn[1], 0.0) + 0.1 * max(-wn[1], 0.0)   # countershaded like a shark: dark above, pale below
    lv = 0.2 + 0.7 * lv                                       # faces land in the midtones; the top is for wet light
    rgb = px.smooth_ramp(pal, lv)
    blaze, open_, day = _P(ctx)
    if wet and day < 0.5:
        hi = np.clip((lv - 0.8) / 0.14, 0, 1)
        rgb = _mix(rgb, WET, hi * 0.55)
        if px.side(ctx) and H >= 4:
            glint = (iy <= 1) & (_h(ix, iy, ctx.seed + seed) < 0.10)
            rgb = np.where(glint[:, None], _mix(rgb, WET, 0.6), rgb)
    glow = np.zeros(ctx.N)
    if spill:
        s = sun_spill(ctx) * spill
        warm = px.smooth_ramp(WARM, np.clip(0.35 + 0.65 * s, 0, 1))
        rgb = _mix(rgb, warm, np.clip(s * 1.1, 0, 0.85))
        glow = np.where(s > 0.55, 0.12 + 0.2 * blaze, 0.0)
    return rgb, glow


def _torso_level(ctx, offset=0.08):
    c = chest_world((0.0, 26.0, 1.0))
    lv = px.proxy(ctx, tuple(c), (7.5, 9.0, 6.0), 0.75) + offset
    if px.side(ctx):
        ix, iy, W, H = px.texel(ctx)
        lv = lv + 0.06 * (0.5 - (iy + 0.5) / H)
    return lv


def mat_skin(ctx):
    """The upper body: pectorals, the upper chest and trapezius under the plates."""
    lv = _torso_level(ctx) + px.ao_near(ctx, [chest_world((s * 7.5, 28.75, 1.25)) for s in (-1, 1)], 3.5, 0.12)
    rgb, glow = skin(ctx, lv)
    rgb, glow = chest_cracks(ctx, rgb, glow)
    return rgb, ctx.ones(), glow


def mat_belly(ctx):
    """The pale underside: the ribcage front and the waist, with soft ventral grooves."""
    ix, iy, W, H = px.texel(ctx)
    lv = _torso_level(ctx, 0.12)
    if ctx.face == "north" and H >= 6:
        lv = lv - 0.06 * ((iy % 3) == 2) * (np.abs(ix + 0.5 - W / 2) < W / 2 - 1)
    rgb, glow = skin(ctx, lv, belly=True)
    rgb, glow = chest_cracks(ctx, rgb, glow)
    return rgb, ctx.ones(), glow


PHOTO_FLANK = [(s * 6.55, y, z) for s in (-1, 1) for y, z in ((21.6, 1.75), (22.9, 1.25), (24.2, 1.75), (25.5, 1.25),
                                                              (26.8, 1.75))]


def mat_ribs(ctx):
    """The flanks: ribs under the skin and the lateral line of photophores."""
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    lv = _torso_level(ctx, 0.05)
    if px.side(ctx) and H >= 6:
        lv = lv - 0.07 * ((iy % 3) == 1)
    rgb, glow = skin(ctx, lv)
    rgb, glow = chest_cracks(ctx, rgb, glow)
    if px.side(ctx) and abs(_cfn(ctx)[0]) > 0.5:
        rgb, glow = photophores(rgb, glow, _spots(_cf(ctx), PHOTO_FLANK, 0.85), gold=day > 0.5)
    return rgb, ctx.ones(), glow


def mat_pelvis(ctx):
    lv = px.proxy(ctx, (0.0, 17.0, 1.0), (6.0, 3.5, 4.5), 0.7) + 0.06
    rgb, glow = skin(ctx, lv, spill=0.6)
    rgb, glow = limb_cracks(ctx, rgb, glow, 3)
    return rgb, ctx.ones(), glow


PHOTO_LIMB = []


def _photo_limbs():
    if PHOTO_LIMB:
        return PHOTO_LIMB
    for s in (-1, 1):
        S0 = _shoulder("base", s)
        E0 = np.array([s * ELBOW[0], ELBOW[1], ELBOW[2]])
        W0 = np.array([s * WRIST[0], WRIST[1], WRIST[2]])
        for t in (0.22, 0.46, 0.7):                                    # down the back of the forearm
            PHOTO_LIMB.append(tuple(E0 + (W0 - E0) * t + np.array([0.0, 0.0, 2.6])))
        for t in (0.5, 0.75):                                          # the outside of the upper arm
            PHOTO_LIMB.append(tuple(S0 + (E0 - S0) * t + np.array([s * 2.05, 0.0, 0.0])))
        PHOTO_LIMB.extend([(s * 6.15, 15.25, 0.5), (s * 6.0, 13.5, -0.25)])     # the outer thigh (lateral line)
    return PHOTO_LIMB


def mat_arm(ctx):
    lv = pillow(ctx) + 0.06
    rgb, glow = skin(ctx, lv, spill=0.5)
    rgb, glow = limb_cracks(ctx, rgb, glow, 5)
    rgb, glow = photophores(rgb, glow, px.glow_spot(ctx, _photo_limbs(), 0.62), gold=_P(ctx)[2] > 0.5)
    return rgb, ctx.ones(), glow


def mat_fore(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = pillow(ctx, edge=0.14) + 0.06
    if px.side(ctx) and H >= 8:                                        # tendons along the forearm
        lv = lv - 0.05 * ((ix % 3) == 1) * (iy > 1)
    rgb, glow = skin(ctx, lv, spill=0.4)
    rgb, glow = limb_cracks(ctx, rgb, glow, 7)
    rgb, glow = photophores(rgb, glow, px.glow_spot(ctx, _photo_limbs(), 0.62), gold=_P(ctx)[2] > 0.5)
    return rgb, ctx.ones(), glow


def mat_hand(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = pillow(ctx, edge=0.12) + 0.05
    if px.side(ctx) and H >= 5:                                        # knuckle creases
        lv = lv - 0.08 * ((iy % 4) == 3)
    rgb, glow = skin(ctx, lv, spill=0.3)
    rgb, glow = limb_cracks(ctx, rgb, glow, 9)
    return rgb, ctx.ones(), glow


def mat_leg(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = pillow(ctx) + 0.05
    rgb, glow = skin(ctx, lv, spill=0.25)
    rgb, glow = limb_cracks(ctx, rgb, glow, 13)
    rgb, glow = photophores(rgb, glow, px.glow_spot(ctx, _photo_limbs(), 0.62), gold=_P(ctx)[2] > 0.5)
    return rgb, ctx.ones(), glow


def mat_foot(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = pillow(ctx, edge=0.1) + 0.02
    if ctx.face == "up" and W >= 4:                                    # scutes over the toes
        lv = lv + 0.08 * ((iy % 3) == 0) - 0.04 * ((iy % 3) == 2)
    rgb, glow = skin(ctx, lv, spill=0.0)
    rgb, glow = limb_cracks(ctx, rgb, glow, 15)
    return rgb, ctx.ones(), glow


def mat_fp_arm(ctx):
    lv = pillow(ctx) + 0.12
    rgb, glow = skin(ctx, lv, spill=0.0)
    ix, iy, W, H = px.texel(ctx)
    if px.side(ctx) and H >= 12:                                        # a short row of photophores
        g = np.zeros(ctx.N)
        for k in (0.3, 0.5, 0.7):
            g = np.maximum(g, np.clip(1 - np.hypot(ix + 0.5 - W / 2, iy + 0.5 - H * k) / 1.4, 0, 1))
        rgb, glow = photophores(rgb, glow, g, gold=_P(ctx)[2] > 0.5)
    return rgb, ctx.ones(), glow


# ----------------------------------------------------------------------------- the head

def _head_level(ctx, offset=0.0):
    c = _head_w((0.0, 28.5, -10.75))
    return px.proxy(ctx, tuple(c), (3.6, 3.2, 4.2), 0.75) + offset


PHOTO_HEAD = None


def _photo_head():
    global PHOTO_HEAD
    if PHOTO_HEAD is None:
        PHOTO_HEAD = [_head_w((s * 3.45, y, z)) for s in (-1, 1) for y, z in ((27.25, -12.0), (26.5, -11.0), (25.9, -9.9))]
    return PHOTO_HEAD


def mat_head(ctx):
    """The old bald dome: wrinkled sides, a few age spots, a row of cheek photophores."""
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    lv = _head_level(ctx)
    if px.side(ctx) and H >= 6:
        lv = lv - 0.07 * (((iy + (ix // 4)) % 4) == 1) * (ix > 0) * (ix < W - 1)
    if ctx.face == "up" and W >= 6:
        spots = _h(ix, iy, ctx.seed + 4) < 0.06
        lv = lv - 0.08 * spots
    rgb, glow = skin(ctx, lv, spill=0.7)
    rgb, glow = photophores(rgb, glow, px.glow_spot(ctx, _photo_head(), 0.7), gold=day > 0.5)
    rgb, glow = limb_cracks(ctx, rgb, glow, 17)
    return rgb, ctx.ones(), glow


def mat_neck(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = pillow(ctx, edge=0.12) + 0.08
    if px.side(ctx) and W >= 5:
        lv = lv - 0.06 * ((ix % 3) == 1)                                  # sinews
    rgb, glow = skin(ctx, lv, spill=0.9)
    rgb, glow = limb_cracks(ctx, rgb, glow, 19)
    return rgb, ctx.ones(), glow


def mat_jowl(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = _head_level(ctx, 0.04)
    if px.side(ctx) and H >= 4:
        lv = lv - 0.08 * (iy == H - 2) - 0.04 * (iy == 1)                 # the folds of old jowls
    rgb, glow = skin(ctx, lv, spill=1.0)
    rgb, glow = photophores(rgb, glow, px.glow_spot(ctx, _photo_head(), 0.7), gold=_P(ctx)[2] > 0.5)
    return rgb, ctx.ones(), glow


def mat_brow(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = _head_level(ctx, 0.12)
    if px.side(ctx) and H >= 3:
        lv = lv + 0.1 * (iy == 0) - 0.12 * (iy == H - 1)
    rgb, glow = skin(ctx, lv, spill=0.6)
    return rgb, ctx.ones(), glow


def mat_snout(ctx):
    """The rostrum: a flat blade, slick on top and dotted with electro-sensing pores."""
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx, grad=0.0) + 0.14
    if ctx.face == "up":
        lv = lv + 0.06 * (1 - np.abs((ix + 0.5) / W * 2 - 1))
        pores = (((ix + 2 * iy) % 4) == 1) & (ix > 0) & (ix < W - 1)
        lv = lv - 0.1 * pores
    elif ctx.face == "down":
        lv = lv - 0.06
    rgb, glow = skin(ctx, lv, spill=0.5)
    if ctx.face == "up":
        rim = (ix == 0) | (ix == W - 1)
        rgb = np.where(rim[:, None], _mix(rgb, WET, 0.45), rgb)
    return rgb, ctx.ones(), glow


EYE = [".oo.", "oOWo", ".oo."]


def mat_eye(ctx):
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    socket = np.broadcast_to(SKIN[0], (ctx.N, 3)).copy()
    if day > 0.5:
        cols = {"o": "#e0902c", "O": "#ffd36e", "W": "#fff8e0"}
    else:
        cols = {"o": "#3aa6d6", "O": "#8fe2fb", "W": "#f2fdff"}
    if ctx.face == "north":
        rgb, g = px.decal(ctx, socket, EYE, cols, "c", "c", glow=ctx.zeros(), glow_chars="oOW", glow_level=0.9)
        return rgb, ctx.ones(), g
    return px.smooth_ramp(SKIN, px.light(ctx) - 0.1), ctx.ones(), ctx.zeros()


def mat_lid(ctx):
    lv = px.light(ctx) - 0.02
    rgb, _ = skin(ctx, lv, spill=0.0, wet=False)
    return rgb, ctx.ones(), ctx.zeros()


def mat_hair(ctx):
    """An old man's white brows: pale strands, greyer underneath."""
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx, grad=0.1) + 0.12
    if px.side(ctx):
        lv = lv - 0.08 * ((ix % 2) == 1)
    return px.smooth_ramp(HAIR, lv), ctx.ones(), ctx.zeros()


def mat_wisp(ctx):
    """The last long wisps behind the jowls (cutout): thin strands with gaps, ragged ends."""
    q = np.floor(_wp(ctx) * 2.0 + 0.01)
    col = (q[:, 2]).astype(int)
    row = (q[:, 1] - q[:, 1].min()).astype(int)
    length = 4 + (_h(col, 0, 7) * 5).astype(int)
    strand = (col % 2 == 0) & (row >= (q[:, 1].max() - q[:, 1].min()) - length)
    c = px.smooth_ramp(HAIR, 0.55 + 0.35 * (row % 3 == 0))
    return c, strand.astype(float), ctx.zeros()


def mat_gill(ctx):
    """Outside: a skin flap with a pale trailing rim; inside (toward the neck): red filaments."""
    ix, iy, W, H = px.texel(ctx)
    n = _wn(ctx)
    inner = abs(n[0]) > 0.5 and np.sign(n[0]) != np.sign(_wp(ctx)[:, 0].mean())
    if inner:
        return px.smooth_ramp(GILL, px.light(ctx) + 0.12 * ((iy % 2) == 0)), ctx.ones(), ctx.zeros()
    rgb, glow = skin(ctx, px.light(ctx) + 0.04, spill=0.2)
    edge = (ix == 0) | (ix == W - 1)
    rgb = np.where(edge[:, None], GILL[2], rgb)
    return rgb, ctx.ones(), glow


def mat_lip(ctx):
    if ctx.face == "down":                                                  # the roof of the mouth
        return px.smooth_ramp(GILL, px.light(ctx) + 0.05), ctx.ones(), ctx.zeros()
    rgb, glow = skin(ctx, px.light(ctx) + 0.1, spill=0.8)
    return rgb, ctx.ones(), glow


def mat_jaw(ctx):
    ix, iy, W, H = px.texel(ctx)
    if ctx.face == "up":                                                    # the tongue bed
        return px.smooth_ramp(GILL, px.light(ctx) - 0.2), ctx.ones(), ctx.zeros()
    lv = px.light(ctx) + 0.1
    if px.side(ctx) and H >= 2:
        lv = lv - 0.06 * (iy == H - 1)
    rgb, glow = skin(ctx, lv, spill=1.0)
    return rgb, ctx.ones(), glow


def mat_gum(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx) - 0.05 - 0.12 * ((ix % 2) == 0) * px.side(ctx)
    return px.smooth_ramp(GILL, lv), ctx.ones(), ctx.zeros()


def mat_teeth(ctx):
    """Irregular rows of white needle teeth (cutout): the upper row hangs, the lower row stands."""
    ix, iy, W, H = px.texel(ctx)
    if not px.side(ctx):
        return np.broadcast_to(BONE[2], (ctx.N, 3)).copy(), ctx.zeros(), ctx.zeros()
    hang = ctx.size[2] < 4.6                                  # the upper row is the shorter box
    q = np.floor(_wp(ctx) * 2.0 + 0.01)
    col = (q[:, 0] + q[:, 2]).astype(int)
    hv = _h(col, 0, 3 if hang else 7)
    tooth = ((col % 2) == 0) & (hv < 0.8)
    root = iy if hang else (H - 1 - iy)                       # 0 at the gum
    a = tooth & ((root <= H - 2) | (hv < 0.45))
    c = np.where((root == 0)[:, None], BONE[2], np.where((root >= H - 1)[:, None], BONE[4], BONE[3]))
    return c, a.astype(float), ctx.zeros()


def mat_barbel(ctx):
    """Barbels: pale skin, lighter toward the tip; the very tip is a glowing ice-blue lure."""
    blaze, open_, day = _P(ctx)
    lv = px.light(ctx) + 0.16
    rgb = px.smooth_ramp(BELLY if day < 0.5 else DAYBELLY, lv)
    lower = ctx.origin[1] + ctx.size[1] / 2 < 24.5 + HEAD_DY      # the second (hanging) segment ...
    tip = (ctx.local[:, 2] > 0.8) & lower                          # ... and its last texels
    c = px.col("#ffd36e") if day > 0.5 else PHOTO_MID
    rgb = np.where(tip[:, None], c, rgb)
    return rgb, ctx.ones(), np.where(tip, 0.9, 0.0)


# ----------------------------------------------------------------------------- pearl armour

def plate_paint(ctx, crack_fn=chest_cracks, photo=True, rim_glow=0.0):
    """Pearl-grey isopod armour with a lavender sheen: light from the plate's real direction, a soft
    swell across it, a bright bevel round the outer face, dark seams on the thin edges, growth lines,
    photophores on the flanges, cracks near the wounds; daybreak: light pours from every edge."""
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    lv = 0.2 + 0.66 * px.light(ctx, grad=0.0)
    glow = np.zeros(ctx.N)
    if ctx.face == "up":                                                  # the outer face of a slab
        u = (ix + 0.5) / W * 2 - 1
        v = (iy + 0.5) / H * 2 - 1
        lv = lv + 0.08 * (1 - u ** 2) - 0.05 * v ** 2
        lv = lv - 0.035 * ((iy % 3) == 1) * (W >= 6)                      # growth lines
        rgb = px.smooth_ramp(ARMOR, lv)
        sheen = np.clip(np.sin((u * 0.9 + v * 0.35 + 0.3) * np.pi) * 0.5 + 0.2, 0, 1)
        rgb = _mix(rgb, LAVENDER, 0.4 * sheen)
        rgb = _mix(rgb, PEARL_CYAN, 0.16 * np.clip(-np.sin((u * 0.9 + v * 0.35) * np.pi), 0, 1))
        bevel = (ix == 0) | (iy == 0) | (ix == W - 1) | (iy == H - 1)
        inner = ((ix == 1) | (iy == 1) | (ix == W - 2) | (iy == H - 2)) & ~bevel & (min(W, H) >= 5)
        rgb = np.where(bevel[:, None], _mix(rgb, ARMOR[5], 0.5), rgb)
        rgb = np.where(inner[:, None], _mix(rgb, ARMOR[1], 0.22), rgb)
        if day > 0.5:                                                     # light pours from the trailing edge
            lip = iy == 0
            glow = np.where(lip, 0.8, glow)
            rgb = np.where(lip[:, None], SUN[4], rgb)
    elif ctx.face == "down":                                              # the underside
        rgb = px.smooth_ramp(ARMOR, lv - 0.25)
    else:                                                                 # the thin edges: dark seams
        rgb = px.smooth_ramp(ARMOR, lv - 0.18)
        rgb = np.where((iy == 0)[:, None], _mix(rgb, ARMOR[5], 0.6), rgb)
        rgb = np.where((iy == H - 1)[:, None] if H >= 2 else np.zeros((ctx.N, 1), bool), SEAMLINE, rgb)
        if day > 0.5 and ctx.face == "south":                             # ... and from every seam (trailing edges)
            rgb = _mix(rgb, SUN[3], 0.8)
            glow = np.full(ctx.N, 0.75)
    if crack_fn is not None:
        rgb, glow = crack_fn(ctx, rgb, glow)
    if photo and ctx.face == "up" and W >= 4 and H >= 4:
        n = _wn(ctx)
        g = np.zeros(ctx.N)
        if abs(n[0]) > 0.45:                                              # two photophores on every flange and lame:
            for fy in (0.3, 0.72):                                        # rows down the back
                g = np.maximum(g, np.clip(1 - np.hypot(ix - (W - 1) / 2, iy - (H - 1) * fy) / 1.45, 0, 1))
        rgb, glow = photophores(rgb, glow, g, gold=day > 0.5)
    return rgb, glow


def mat_plate(ctx):
    rgb, glow = plate_paint(ctx)
    return rgb, ctx.ones(), glow


def mat_plate_limb(ctx):
    rgb, glow = plate_paint(ctx, crack_fn=None, photo=False)
    rgb, glow = limb_cracks(ctx, rgb, glow, 21)
    return rgb, ctx.ones(), glow


def mat_keel(ctx):
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    lv = 0.26 + 0.66 * px.light(ctx, grad=0.0)
    rgb = px.smooth_ramp(ARMOR, lv)
    glow = np.zeros(ctx.N)
    if ctx.face == "up":
        ridge = np.abs(ix + 0.5 - W / 2) < 0.75
        rgb = np.where(ridge[:, None], ARMOR[6], _mix(rgb, LAVENDER, 0.25))
    else:
        rgb = np.where((iy == H - 1)[:, None] if H >= 2 else np.zeros((ctx.N, 1), bool), SEAMLINE, rgb)
    rgb, glow = chest_cracks(ctx, rgb, glow)
    if day > 0.5:
        rgb = np.where((iy == 0)[:, None], SUN[4], rgb)
        glow = np.where(iy == 0, 0.7, glow)
    return rgb, ctx.ones(), glow


def mat_seam(ctx):
    """Bastion / daybreak: light leaking between the plates."""
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    lv = 0.6 + 0.2 * ((ix % 4) == 1) + 0.15 * day
    seen = ctx.face in ("up", "south", "east", "west")                   # the hidden underside stays dark gold
    return px.smooth_ramp(SUN, lv if seen else lv - 0.3), ctx.ones(), np.full(ctx.N, 0.85 if seen else 0.0)


def mat_claw(ctx):
    """Hard white claws and teeth-like nails: darker at the root."""
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx) + 0.1
    if px.side(ctx) and H >= 2:
        lv = lv + 0.18 * (iy / max(H - 1, 1)) - 0.08
    return px.smooth_ramp(BONE, lv), ctx.ones(), ctx.zeros()


def mat_ray(ctx):
    """Fin rays: bony spines, lighter toward the tip, the tip a tiny glowing photophore."""
    blaze, open_, day = _P(ctx)
    lv = px.light(ctx) + 0.12 + 0.12 * ctx.local[:, 1]
    rgb = px.smooth_ramp(FIN, lv)
    tip = ctx.local[:, 1] > 0.88
    c = px.col("#ffd36e") if day > 0.5 else PHOTO_MID
    rgb = np.where(tip[:, None], c, rgb)
    return rgb, ctx.ones(), np.where(tip, 0.75, 0.0)


def fin_alpha(ctx, rays_, a0: float, a1: float):
    """Torn fin membrane between rays (cutout): polar coordinates about the fin root in the fin plane."""
    p = ctx.p
    s = np.sign(p[:, 0].mean()) or 1.0
    root = np.array([s * FIN_ROOT[0], FIN_ROOT[1], FIN_ROOT[2]])
    dy, dz = p[:, 1] - root[1], p[:, 2] - root[2]
    r = np.hypot(dy, dz)
    ang = np.degrees(np.arctan2(dz, dy))
    angs = np.array([a for a, _ in rays_])
    lens = np.array([l for _, l in rays_])
    edge = np.interp(ang, angs, lens)
    k = np.clip(np.searchsorted(angs, ang) - 1, 0, len(angs) - 2)
    f = np.clip((ang - angs[k]) / np.maximum(angs[k + 1] - angs[k], 1e-6), 0, 1)
    edge = edge - 1.6 * np.sin(np.pi * f) - 0.6 * (np.mod(np.floor(r * 2 + ang * 0.3), 5) == 0) * (r > edge - 2.5)
    keep = (ang >= a0) & (ang <= a1) & (r <= edge) & (r > 0.4)
    return keep


def _membrane(ctx, keep):
    """Torn fin membrane colours: darker near the root, rays as darker lines, a pale ragged margin."""
    ix, iy, W, H = px.texel(ctx)
    p = ctx.p
    s = np.sign(p[:, 0].mean()) or 1.0
    root = np.array([s * FIN_ROOT[0], FIN_ROOT[1], FIN_ROOT[2]])
    dy, dz = p[:, 1] - root[1], p[:, 2] - root[2]
    r = np.hypot(dy, dz)
    ang = np.degrees(np.arctan2(dz, dy))
    angs = np.array([a for a, _ in FIN_RAYS + (FLAP_RAY,)])
    on_ray = np.min(np.abs(ang[:, None] - angs[None, :]), axis=1) * np.pi / 180 * r < 0.45
    lv = 0.38 + 0.05 * r - 0.12 * on_ray
    rgb = px.smooth_ramp(FIN, lv)
    a = keep.copy()
    # the margin: a pale dithered rim makes the membrane read thin and translucent
    edge = keep & ~(np.roll(keep, 1) & np.roll(keep, -1))
    rgb = np.where(edge[:, None], FIN[5], rgb)
    return rgb, a.astype(float), ctx.zeros()


def mat_fin(ctx):
    return _membrane(ctx, fin_alpha(ctx, FIN_RAYS + (FLAP_RAY,), 0.0, 50.0))


def mat_fin_flap(ctx):
    return _membrane(ctx, fin_alpha(ctx, FIN_RAYS[-1:] + (FLAP_RAY, (78.0, 3.0)), 46.0, 74.0))


def mat_small_fin(ctx):
    """Calf and forearm fins (cutout): a swept-back sail with rays and a ragged trailing edge."""
    ix, iy, W, H = px.texel(ctx)
    u = (ix + 0.5) / W
    if ctx.face == "west":
        u = 1 - u
    v = (iy + 0.5) / H
    edge = 0.3 + 0.62 * u - 0.12 * (np.mod(iy, 4) == 3) * (u > 0.4)
    keep = (v < edge) & px.side(ctx) & (ctx.face in ("east", "west"))
    ray = (np.mod(ix + iy // 2, 3) == 0)
    rgb = px.smooth_ramp(FIN, 0.45 + 0.25 * u - 0.12 * ray)
    return rgb, keep.astype(float), ctx.zeros()


def mat_web(ctx):
    """Webbing between the fingers: a scalloped lower edge."""
    q = np.floor(_wp(ctx) * 2.0 + 0.01)
    qy, qz = q[:, 1], q[:, 2]
    rel = qy - qy.min()
    a = rel >= (np.mod(qz, 3) == 1) * 2 + 1
    c = np.where((rel < 3)[:, None], FIN[4], FIN[2])
    return c, a.astype(float), ctx.zeros()


# ----------------------------------------------------------------------------- the light: coronas and wound cores

def _corona_paint(ctx, center, r_max, plane_n):
    blaze, open_, day = _P(ctx)
    r = np.linalg.norm(_wp(ctx) - np.array(chest_world(center)), axis=1)
    v = np.clip((r - 1.8) / (r_max - 1.8), 0, 1)
    hot = 1.0 + 0.15 * blaze + 0.1 * open_
    rgb = px.smooth_ramp(SUN[::-1], np.clip(v * 0.72, 0, 1))      # white -> gold -> amber at the tip
    if day > 0.5:
        rgb = _mix(rgb, SUN[6], 0.25)
    g = np.clip((0.8 * (1 - v) ** 1.2 + 0.24) * hot, 0, 1)
    return rgb, ctx.ones(), g


def mat_corona(ctx):
    return _corona_paint(ctx, (ENTRY[0], ENTRY[1], -4.6), 14.5, -1)


def mat_corona_b(ctx):
    return _corona_paint(ctx, (EXIT[0], EXIT[1], 8.0), 6.5, 1)


def mat_core(ctx):
    ix, iy, W, H = px.texel(ctx)
    cx, cy = (W - 1) / 2, (H - 1) / 2
    rr = np.hypot((ix - cx) / max(cx, 0.5), (iy - cy) / max(cy, 0.5))
    return px.smooth_ramp(SUN, np.clip(1.0 - rr * 0.35, 0, 1)), ctx.ones(), np.clip(0.95 - 0.15 * rr, 0, 1)


def mat_core_hot(ctx):
    return np.broadcast_to(SUN[6], (ctx.N, 3)).copy(), ctx.ones(), np.full(ctx.N, 1.0)


def materials():
    mats = {
        "skin": mat_skin, "belly": mat_belly, "ribs": mat_ribs, "pelvis": mat_pelvis, "arm": mat_arm, "fore": mat_fore,
        "hand": mat_hand, "leg": mat_leg, "foot": mat_foot, "fp_arm": mat_fp_arm, "neck": mat_neck, "head": mat_head,
        "jowl": mat_jowl, "brow": mat_brow, "snout": mat_snout, "eye": mat_eye, "lid": mat_lid, "hair": mat_hair,
        "wisp": mat_wisp, "gill": mat_gill, "lip": mat_lip, "jaw": mat_jaw, "gum": mat_gum, "teeth": mat_teeth,
        "barbel": mat_barbel, "plate": mat_plate, "plate_limb": mat_plate_limb, "keel": mat_keel, "seam": mat_seam,
        "claw": mat_claw, "ray": mat_ray, "fin": mat_fin, "fin_flap": mat_fin_flap, "calf_fin": mat_small_fin,
        "web": mat_web, "corona": mat_corona, "corona_b": mat_corona_b, "core": mat_core, "core_hot": mat_core_hot,
        "accent": mat_accent,
    }
    mats.update(sword_materials())
    return mats


# ============================================================================= the sword (embedded and held)

def sword_materials():
    return {"s_blade": mat_s_blade, "s_fuller": mat_s_fuller, "s_hilt": mat_s_hilt, "s_ray": mat_s_ray,
            "s_sun": mat_s_sun, "s_grip": mat_s_grip, "s_pommel": mat_s_pommel}


def _sblaze(ctx):
    return max(ctx.params.get("blaze", 0.0), ctx.params.get("day", 0.0))


def mat_s_blade(ctx):
    """White-gold metal: bright bevelled edges, soft heat bands down the flat; the flat glows a little."""
    ix, iy, W, H = px.texel(ctx)
    b = _sblaze(ctx)
    if px.side(ctx) and W >= 3 and H >= W:
        edge = (ix == 0) | (ix == W - 1)
        heat = ((iy // 3) % 4) == 1
        lv = 0.6 + 0.26 * (1 - np.abs((ix + 0.5) / W * 2 - 1)) + 0.08 * heat
        rgb = px.smooth_ramp(STEEL, lv)
        rgb = np.where(edge[:, None], STEEL[4], rgb)
        g = np.where(edge, 0.34, 0.06 + 0.08 * heat)
    else:
        rgb = px.smooth_ramp(STEEL, px.light(ctx) + 0.25)
        g = np.full(ctx.N, 0.2)
    return rgb, ctx.ones(), np.clip(g + 0.2 * b, 0, 1)


def mat_s_fuller(ctx):
    """The raised spine: a white-hot line of light down the blade."""
    ix, iy, W, H = px.texel(ctx)
    rgb = px.smooth_ramp(SUN, 0.8 + 0.15 * ((iy % 4) == 0))
    return rgb, ctx.ones(), np.full(ctx.N, 0.62)


def mat_s_hilt(ctx):
    """Gold fittings: bright upper edges, darker undersides."""
    rgb = px.smooth_ramp(GOLD, px.rim(ctx, px.light(ctx) + 0.12, 0.2, 0.15))
    return rgb, ctx.ones(), np.full(ctx.N, 0.25 + 0.2 * _sblaze(ctx))


def mat_s_ray(ctx):
    """The sunburst guard: polished gold rays (metal in front of the light), a bright upper edge."""
    ix, iy, W, H = px.texel(ctx)
    v = np.clip(ctx.local[:, 2], 0, 1)
    lv = 0.78 - 0.3 * v + (0.15 if ctx.face == "up" else 0.0) - (0.15 if ctx.face == "down" else 0.0)
    rgb = px.smooth_ramp(GOLD, lv)
    return rgb, ctx.ones(), np.clip(0.3 - 0.2 * v + 0.15 * _sblaze(ctx), 0, 1)


def mat_s_sun(ctx):
    """The sun disc at the heart of the guard: white core, gold rim."""
    ix, iy, W, H = px.texel(ctx)
    cx, cy = (W - 1) / 2, (H - 1) / 2
    rr = np.hypot((ix - cx) / max(cx, 0.5), (iy - cy) / max(cy, 0.5))
    rgb = px.smooth_ramp(SUN, np.clip(1.02 - 0.45 * rr, 0, 1))
    return rgb, ctx.ones(), np.clip(0.95 - 0.3 * rr, 0, 1)


def mat_s_grip(ctx):
    """Dark leather wrapped with gold wire (diagonal turns)."""
    ix, iy, W, H = px.texel(ctx)
    rgb = px.smooth_ramp(LEATHER, px.light(ctx) + 0.1)
    if px.side(ctx):
        wire = ((iy + ix) % 3) == 0
        rgb = np.where(wire[:, None], GOLD[3], rgb)
        return rgb, ctx.ones(), np.where(wire, 0.3, 0.0)
    return rgb, ctx.ones(), ctx.zeros()


def mat_s_pommel(ctx):
    """The pommel: a small sun, gold round a glowing core."""
    ix, iy, W, H = px.texel(ctx)
    rr = np.hypot(ix + 0.5 - W / 2, iy + 0.5 - H / 2) / max(W / 2, 0.5)
    rgb = px.smooth_ramp(GOLD, np.clip(1.0 - 0.5 * rr + 0.05 * (ctx.face == "up"), 0, 1))
    rgb = np.where((rr < 0.45)[:, None], SUN[5], rgb)
    return rgb, ctx.ones(), np.where(rr < 0.45, 0.9, 0.35)


def build_sword() -> Model:
    """The held sword (the same design as the one through his chest): root -> sword, grip
    centre at the origin, blade along +Y (broad faces front/back), 30 px from pommel to tip."""
    m = Model("bathyas_sword", ppu=2.0, atlas_width=64)
    m.bone("root", None, (0, 0, 0))
    sw = m.bone("sword", "root", (0, 0, 0))
    sword_parts(m, sw.name, (0.0, 0.0, 0.0))
    sw.locators["blade_tip"] = (0.0, TIP_Y, 0.0)
    sw.locators["blade_mid"] = (0.0, 15.0, 0.0)
    sw.locators["guard"] = (0.0, GUARD_Y, 0.0)
    m.pack()
    return m
