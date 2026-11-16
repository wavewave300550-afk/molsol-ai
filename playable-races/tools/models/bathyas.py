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
from models.common import accents, euler_for, fp_sleeves, frame_rot, humanoid, mat_accent, q, rays, side_rot, sweep

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
TERGITES = [
    (34.1, 1.6, 82.0, 9.5, 3.75),
    (33.5, 4.6, 56.0, 13.5, 3.75),
    (31.75, 6.3, 30.0, 15.5, 3.75),
    (29.25, 6.55, 9.0, 16.0, 3.75),
    (26.5, 6.3, -2.0, 15.5, 3.75),
    (23.75, 6.2, -8.0, 14.25, 3.75),
    (21.25, 6.05, -14.0, 12.75, 3.5),
]
WAIST_PLATES = [(18.5, 5.4, -12.0, 11.0, 3.25), (16.0, 5.15, -18.0, 10.25, 3.0)]
PLATES = TERGITES + WAIST_PLATES             # (the animation set lifts and jostles them in this order)
PLATE_T = 1.25                              # armour thickness
PLATE_LIFT = 15.0                           # the trailing edge of each plate lifts over the next one

# bastion: the tergites slide together and down over the nape; daybreak: they lift apart (offset along normal, extra tilt)
PLATE_CLOSE = [(-0.35, 10.0), (-0.3, 7.0), (-0.25, 5.0), (-0.2, 3.0), (-0.2, 2.0), (-0.15, 0.0), (-0.1, -2.0),
               (-0.1, -3.0), (0.0, -4.0)]
PLATE_OPEN = [(0.5, -10.0), (0.6, -9.0), (0.7, -8.0), (0.7, -7.0), (0.65, -6.0), (0.6, -5.0), (0.5, -4.0),
              (0.45, -4.0), (0.4, -4.0)]

# --------------------------------------------------------------------------- shoulders, arms, neck
SHOULDER_C = (7.5, 28.75, 1.25)             # shoulder joint (chest frame, right side mirrored with x < 0)
ELBOW = (8.25, 20.5, 0.0)                   # world rest pose (|x|): a slight bend leaves the arm slack for every form
WRIST = (7.5, 13.5, -1.75)                  # the hand stays here in every form: held items sit in the claws
NECK_C = (0.0, 32.5, -1.0)                  # where the neck leaves the chest (chest frame)
FIN_ROOT = (4.5, 28.75, 7.25)               # the dorsal fins rise from tergite 3 (chest frame, |x|)
FIN_RAYS = ((5.0, 9.75), (28.0, 9.25), (50.0, 7.5))   # (angle from up toward the tail, length) in the fin plane
FLAP_RAY = (68.0, 5.75)                     # the torn trailing flap
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
        limb(m, g, (s * 3.25, 17.75, 1.0), (s * 3.5, 12.0, -0.75), 5.5, 6.5, "skin")
        limb(m, g, (s * 3.5, 13.0, -0.5), knee + (0, -0.25, 0.25), 4.75, 5.25, "skin")
        sn = m.bone(f"{p}_shin", g, tuple(knee))
        sn.variant.update({v: ((0, 0, 0), (LEG_POSE[v][1], 0.0, 0.0)) for v in VARIANTS if LEG_POSE[v][1]})
        slab(m, sn.name, knee + (0, 0.25, -2.6), (0, 0.3, -1), (0, 1, 0.3), 4.25, 3.5, 1.0, "plate")       # knee cop
        limb(m, sn.name, knee + (0, 0.75, 0.25), ankle + (0, -0.25, 0), 4.0, 4.25, "skin")                  # the shin
        limb(m, sn.name, knee + (0, -0.75, 2.0), ankle + (0, 1.5, 0.75), 3.25, 2.25, "skin")                # the calf
        mid = (knee + ankle) / 2
        dn = (ankle - knee) / np.linalg.norm(ankle - knee)
        fw = np.array([0.0, dn[2], -dn[1]])                       # the shin's front normal
        fw = -fw if fw[2] > 0 else fw
        for k, f in enumerate((-0.26, 0.14)):                     # two overlapping greave plates down the front
            slab(m, sn.name, mid + dn * f * 5.5 + fw * (2.1 + 0.1 * k), fw, dn, 4.0, 3.0, 0.75, "plate")
        m.cube(sn.name, (s * 3.75, 4.75, 1.25), (0.0, 4.0, 3.0), "calf_fin", cutout=True)                       # calf fin
        fb = m.bone(f"{p}_foot", sn.name, tuple(ankle))
        fb.variant.update({v: ((0, 0, 0), (LEG_POSE[v][2], 0.0, 0.0)) for v in VARIANTS if LEG_POSE[v][2]})
        limb(m, fb.name, ankle + (0, 0.25, 0.25), ball + (0, 0.25, -0.25), 3.25, 3.0, "skin", fwd=(0, 0.6, -1))  # raised heel
        m.box(fb.name, (s * 3.75, 0.875, -1.75), (4.25, 1.75, 2.75), "skin")                                    # ball of the foot
        for k, (dx, ang) in enumerate(((-1.5, -12.0), (0.0, 0.0), (1.5, 12.0))):                              # three webbed toes
            x = s * 3.75 + s * dx
            a = math.radians(ang * s)
            d = np.array([math.sin(a) * 0.35, 0.0, -math.cos(a)])
            tip = np.array([x, 0.6, -2.75]) + d * 3.0
            m.cube(fb.name, (x - 0.75, 0.0, -5.75), (1.5, 1.25, 3.25), "skin", pivot=(x, 0.6, -2.5),
                   rot=(0.0, -ang * s, 0.0))
            cl = tip + d * 0.5
            m.cube(fb.name, (cl[0] - 0.375, 0.0, cl[2] - 1.0), (0.75, 1.0, 1.25), "claw", pivot=(cl[0], 0.5, cl[2]),
                   rot=(-10.0, -ang * s, 0.0))
        m.cube(fb.name, (s * 3.75 - 1.5, 0.5, -5.5), (3.0, 0.0, 2.75), "web", cutout=True)
        m.cube(fb.name, (s * 3.75 - 0.375, 1.5, 1.75), (0.75, 1.0, 1.75), "claw", pivot=(s * 3.75, 2.0, 1.75),
               rot=(30.0, 0.0, 0.0))                                                                            # heel spur
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
    m.box(t.name, (0.0, 16.25, 1.0), (10.5, 4.0, 7.0), "skin")                       # pelvis
    m.box(t.name, (0.0, 19.25, 1.5), (9.5, 3.0, 6.5), "belly")                       # the waist
    c = m.bone("chest", t.name, CHEST_PIVOT, (POSE["base"], 0.0, 0.0))
    c.variant.update({v: ((0, 0, 0), (POSE[v], 0.0, 0.0)) for v in VARIANTS if v != "base"})
    m.box(c.name, (0.0, 24.5, 1.25), (11.5, 7.5, 8.5), "belly", faces={"north", "east", "west", "down"})     # ribcage
    m.box(c.name, (0.0, 29.75, 1.25), (14.0, 4.0, 9.0), "skin", faces={"north", "east", "west", "down", "up"})  # upper chest
    m.box(c.name, (0.0, 32.5, 1.5), (9.5, 2.0, 6.5), "skin", faces={"north", "up", "east", "west"})          # trapezius
    for s in (-1, 1):                                                                     # pectorals over the heart
        m.cube(c.name, (s * 3.25 - 2.875, 24.75, -4.125), (5.75, 4.0, 1.25), "skin", pivot=(s * 3.25, 26.75, -3.5),
               rot=(0.0, s * 8.0, s * 6.0))
        m.box(c.name, (s * 6.0, 24.25, 1.5), (1.0, 6.5, 7.0), "ribs")                   # flank: the lateral line
    c.locators["lure_c"] = (0.0, 25.0, -14.0)
    c.locators["back"] = (0.0, 29.0, 9.5)


# ----------------------------------------------------------------------------- isopod tergites over the back

def _plate(m: Model, bone: str, y: float, z: float, ang: float, w: float, ln: float, k: int) -> None:
    n = _ang(ang)                                       # outward normal (YZ plane)
    tng = np.array([0.0, -n[2], n[1]])                  # along the back, pointing down toward the tail
    if tng[1] > 0:
        tng = -tng
    lift = math.radians(PLATE_LIFT)
    tng = tng * math.cos(lift) + n * math.sin(lift)      # the trailing edge lifts over the next plate
    nn0 = np.cross(np.array([1.0, 0.0, 0.0]), tng)
    n = nn0 if nn0 @ n > 0 else -nn0
    c = np.array([0.0, y, z])
    flange = 3.0
    core = w - 2 * 2.0
    slab(m, bone, c, n, tng, core, ln, PLATE_T, "plate")
    for s in (-1, 1):                                   # the sides bend forward round the flanks
        bend = math.radians(54.0)
        side = np.array([s * 1.0, 0.0, 0.0])
        nn = n * math.cos(bend) + side * math.sin(bend)
        across = np.cross(tng, nn)
        across = across if across[0] * s > 0 else -across
        edge = c + side * (core / 2 - 0.3)
        slab(m, bone, edge + across * (flange / 2) - nn * 0.15, nn, tng, flange, ln - 0.25, PLATE_T, "plate")
    slab(m, bone, c + n * (PLATE_T / 2 + 0.3), n, tng, 1.5, ln - 0.75, 0.75, "keel")    # the raised spinal keel
    # light in the seams (bastion, daybreak): a glowing band just under the trailing edge
    slab(m, bone, c - n * 0.45 + tng * (ln / 2 - 0.25), n, tng, w - 1.25, 1.5, 0.5, "seam", only=SEAMED)


def _plates(m: Model) -> None:
    for k, (y, z, ang, w, ln) in enumerate(PLATES):
        par = "chest" if k < len(TERGITES) else "trunk"
        n = _ang(ang)
        b = m.bone(f"plate{k}", par, (0.0, y, z))
        dc, tc = PLATE_CLOSE[k]
        do, to = PLATE_OPEN[k]
        b.variant["bastion"] = (tuple(np.round(n * dc + np.array([0.0, -0.15 * k, 0.0]), 3)), (tc, 0.0, 0.0))
        b.variant["daybreak"] = (tuple(np.round(n * do, 3)), (to, 0.0, 0.0))
        _plate(m, b.name, y, z, ang, w, ln, k)


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
        m.cube(f0.name, (x, y, z - 0.5), (0.0, 10.0, 8.0), "fin", cutout=True)                 # the membrane
        f1 = m.bone(f"{p}_fin1", f0.name, (x, y, z))
        ang, ln = FLAP_RAY
        d = np.array([0.0, math.cos(math.radians(ang)), math.sin(math.radians(ang))])
        a0 = np.array([x, y, z]) + d * 0.25
        limb(m, f1.name, a0 + d * ln, a0, 0.5, 0.5, "ray", fwd=(0, -d[2], d[1]))
        m.cube(f1.name, (x, y - 0.75, z + 2.0), (0.0, 6.0, 6.25), "fin_flap", cutout=True)    # the torn trailing flap


# ----------------------------------------------------------------------------- the sun through his heart

def sword_parts(m: Model, bone: str, base, blade_from: float = BLADE_Y, tip: float = TIP_Y, hilt: bool = True,
                short_rays: bool = True, **kw) -> None:
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
        if short_rays:
            rays(m, bone, g, 8, 1.25, 2.75, 0.5, "s_ray", plane="flat", thick=0.5, phase=22.5, **kw)
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


def _corona(m: Model) -> None:
    """The light at both wounds: thin glowing rays radiating in a circle, fading outward."""
    x, y, _ = ENTRY
    cz = -4.6                                                         # in front of the pectorals
    c = (x, y, cz)
    cf = m.bone("corona_f", "chest", c)
    hide = {"bastion"}                                                # bastion: the light is shut inside the plates
    rays(m, cf.name, c, 8, 2.25, 5.5, 1.0, "corona", plane="front", phase=0.0, skip=hide)     # long rays: a broad root
    rays(m, cf.name, (x, y, cz - 0.05), 8, 5.5, 9.25, 0.5, "corona", plane="front", phase=0.0, skip=hide)  # ... a thin tip
    rays(m, cf.name, (x, y, cz - 0.1), 8, 2.25, 6.25, 0.5, "corona", plane="front", phase=22.5, skip=hide)
    rays(m, cf.name, (x, y, cz - 0.15), 8, 3.0, 14.0, 0.75, "corona", plane="front", phase=11.25, only={"lure"})
    rays(m, cf.name, (x, y, cz - 0.15), 8, 3.0, 12.0, 0.75, "corona", plane="front", phase=33.75,
         only={"lure", "unshackled", "daybreak"})
    m.box(cf.name, (x, y, cz + 0.25), (3.0, 3.0, 0.5), "core", skip=hide | DRAWN)               # the glare at the wound
    m.box(cf.name, (x, y, cz + 0.05), (2.5, 4.5, 0.5), "core", only=DRAWN)                      # the open sun
    m.box(cf.name, (x, y, cz + 0.1), (4.5, 2.5, 0.5), "core", only=DRAWN)
    m.box(cf.name, (x, y, cz - 0.2), (2.5, 2.5, 0.5), "core_hot", only=DRAWN)
    cf.locators["wound"] = (x, y, cz - 0.5)
    # the exit wound: a smaller corona in the plane of the back plates, above the keel
    ex, ey, ez = EXIT
    pz = 8.0
    cb = m.bone("corona_b", "chest", (ex, ey, pz), (12.0, 0.0, 0.0))
    rays(m, cb.name, (ex, ey, pz), 6, 1.5, 6.25, 0.75, "corona_b", plane="back", phase=0.0)
    rays(m, cb.name, (ex, ey, pz + 0.05), 6, 1.5, 4.0, 0.5, "corona_b", plane="back", phase=30.0)
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
        m.box(dl.name, tuple(S0 + (s * 0.25, -0.75, 0.25)), (4.75, 4.75, 5.0), "skin")     # the deltoid under the pauldron
        limb(m, dl.name, S0 + (0, -1.75, 0), E0 + (0, 0.25, 0), 4.0, 4.0, "skin")        # upper arm
        # the forearm: massive, shelled on the outside, a torn fin trailing behind
        limb(m, fo.name, E0 + (0, 0.75, 0.25), W0 + (0, -0.25, 0), 5.0, 5.25, "skin")
        ax = (E0 - W0) / np.linalg.norm(E0 - W0)
        mid = (E0 + W0) / 2
        out = np.array([s * 1.0, 0.0, 0.0])
        for k, f in enumerate((0.22, -0.16)):                                              # vambrace lames
            slab(m, fo.name, mid + ax * f * 7.0 + out * (2.7 + 0.1 * k), out, -ax, 4.0, 3.25, 0.75, "plate")
        slab(m, fo.name, E0 + (0, -0.5, 2.5), (0, -0.2, 1), (0, -1, 0), 3.25, 2.75, 0.75, "plate")      # elbow cop
        m.cube(fo.name, (s * 8.0, 14.25, 1.0), (0.0, 5.0, 3.5), "calf_fin", cutout=True)                    # forearm fin
        # the hand: palm, three long webbed fingers with hard white claws, a thumb
        hz = W0[2]
        m.box(hd.name, (s * 7.5, 12.0, hz), (3.0, 3.0, 3.75), "skin")
        m.cube(hd.name, (s * 7.5, 7.0, hz - 1.75), (0.0, 3.75, 3.5), "web", cutout=True)
        for k, (fz, fan) in enumerate(zip(FINGER_Z, FINGER_FAN)):
            f = m.bone(f"{p}_finger{k}", hd.name, (s * 7.5, 10.5, fz), (fan, 0.0, 0.0))
            m.box(f.name, (s * 7.5, 8.875, fz), (1.25, 3.25, 1.25), "skin")
            m.cube(f.name, (s * 7.5 - 0.5, 5.75, fz - 0.6), (1.0, 2.0, 1.0), "claw", pivot=(s * 7.5, 7.25, fz),
                   rot=(-16.0, 0.0, 0.0))
        th = m.bone(f"{p}_thumb", hd.name, (s * 6.5, 11.75, hz - 1.75), side_rot((-24.0, 0.0, -14.0), s))
        m.box(th.name, (s * 6.5, 10.25, hz - 1.75), (1.25, 2.75, 1.25), "skin")
        m.cube(th.name, (s * 6.5 - 0.375, 8.25, hz - 2.25), (0.75, 1.25, 0.75), "claw")
        hd.locators[f"{p}_claws"] = (s * 7.5, 6.0, hz)
        if s < 0:                                # daybreak (the ultimate's Solar Execution): the sun torn out, in his fist
            palm = (s * 7.5, 11.75, hz)
            sun = m.bone("r_sun", hd.name, palm, orient((0.0, 0.42, -0.91), (0.0, 0.91, 0.42)), only={"daybreak"})
            sword_parts(m, sun.name, palm, short_rays=False)
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

    limb(m, sk.name, (0, 31.25, -4.5), P(0, 27.5, -9.25), 5.5, 5.5, "skin", fwd=(0, -1, -0.3))
    m.box(sk.name, P(0, 28.25, -10.5), (6.5, 5.0, 5.5), "head")                                 # the old bald skull
    m.box(sk.name, P(0, 31.125, -10.25), (5.25, 0.75, 4.25), "head")                            # its dome
    m.box(sk.name, P(0, 25.75, -10.25), (6.75, 2.5, 4.5), "jowl")                              # sagging jowls
    m.box(sk.name, P(0, 30.0, -13.25), (6.5, 1.5, 1.75), "brow")                               # the heavy brow ridge
    m.box(sk.name, P(0, 27.75, -13.5), (5.0, 2.75, 1.0), "face", ppu=4.0)                      # the face under it
    m.box(sk.name, P(0, 28.375, -15.0), (4.75, 2.75, 2.25), "snout")                            # the muzzle tapers into ...
    # ... the rostrum: a long flat blade of a snout, slightly upturned
    sweep(m, sk.name, "ros", [P(0, 29.75, -13.75), P(0, 29.9, -17.0), P(0, 30.4, -20.25)], 4.25, 1.5, "snout", h0=1.5,
          h1=0.75, n=2, bones=False, normal=(0, 1, 0))
    for s, p in ((-1, "r"), (1, "l")):
        m.box(sk.name, P(s * 2.4, 28.75, -13.9), (1.0, 0.75, 0.75), "eye", ppu=4.0)            # small ice-blue eyes
        m.cube(sk.name, P(s * 3.3, 25.0, -9.0), (0.0, 4.0, 4.5), "wisp", cutout=True)            # an old man's last wisps
        lid = m.bone(f"lid_{p}", sk.name, P(s * 2.4, 29.2, -14.05))                              # (scale y to squint / blink)
        m.cube(lid.name, P(s * 2.4 - 0.55, 28.95, -14.4), (1.1, 0.25, 0.6), "lid")
        br = m.bone(f"brow_{p}", sk.name, P(s * 2.0, 30.25, -14.0), side_rot((0.0, 0.0, 8.0), s))
        m.box(br.name, P(s * 2.0, 30.5, -13.75), (2.75, 0.75, 1.25), "hair")                   # the white tuft
        m.cube(br.name, P(s * 3.0 - (2.25 if s < 0 else 0.0), 28.0, -14.25), (2.25, 2.75, 0.0), "brow_hair",
               cutout=True, pivot=P(s * 3.0, 30.5, -14.25), rot=(0.0, -s * 42.0, s * 10.0))      # long brows drooping out
        for k in range(3):                                                                       # gill flaps
            gz = -6.75 - k * 1.0
            gl = m.bone(f"gill_{p}{k}", sk.name, P(s * 2.75, 28.0, gz - 0.5))
            m.cube(gl.name, P(s * 2.75 - 0.125, 25.0, gz - 0.5), (0.25, 3.0, 1.25), "gill")
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
        names = sweep(m, lo.name, f"barbel_{p}", [P(s * 2.0, 23.75, -15.25), P(s * 2.75, 21.5, -14.5),
                                                  P(s * 3.25, 19.25, -13.5)], 0.75, 0.5, "barbel", n=1)
        m.box(names[-1], P(s * 3.25, 19.1, -13.45), (0.75, 0.75, 0.75), "lamp")
    lo.locators["maw"] = P(0.0, 25.0, -18.0)
    sk.locators["eyes"] = P(0.0, 28.75, -14.25)
    sk.locators["gills"] = P(0.0, 26.5, -7.75)


# ============================================================================= materials (Gate A: flat placeholders)

def _flat(base, glow=0.0, up=0.12, down=0.12):
    c = px.col(base)
    pal = px.pal(c * 0.55, c * 0.78, c, np.clip(c * 1.18 + 0.03, 0, 1))

    def mat(ctx):
        return px.shade(ctx, pal, offset=0.12, up=up, down=down), ctx.ones(), np.full(ctx.N, glow)
    return mat


def _rayglow(base, center, r_max):
    """Corona rays: white-gold at the root fading to amber and to a faint glow at the tip (by radius)."""
    c = px.col(base)

    def mat(ctx):
        r = np.linalg.norm(ctx.p[:, :2] - np.array(center[:2]), axis=1)
        v = np.clip((r - 2.0) / (r_max - 2.0), 0, 1)
        rgb = c[None, :] * (1 - 0.45 * v[:, None]) + np.array([1.0, 0.62, 0.22])[None, :] * 0.45 * v[:, None]
        g = np.clip(0.95 * (1 - v) ** 1.3 + 0.06, 0, 1)
        return rgb, ctx.ones(), g
    return mat


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


def _cut(base, kind):
    c = px.col(base)

    def mat(ctx):
        ix, iy, W, H = px.texel(ctx)
        if kind == "fin":
            a = fin_alpha(ctx, FIN_RAYS + (FLAP_RAY,), 0.0, 50.0)
        elif kind == "fin_flap":
            a = fin_alpha(ctx, FIN_RAYS[-1:] + (FLAP_RAY, (78.0, 3.0)), 46.0, 74.0)
        elif kind == "plain_fin":
            u = ix / max(W - 1, 1)
            v = iy / max(H - 1, 1)
            a = (v < 0.35 + 0.55 * u) if ctx.face == "east" else (v < 0.35 + 0.55 * (1 - u))
        elif not px.side(ctx) and kind != "web":
            return np.broadcast_to(c, (ctx.N, 3)).copy(), ctx.zeros(), ctx.zeros()
        elif kind == "teeth":
            a = (ix % 2 == 0) & (iy < H - (ix % 4 == 0))
        elif kind == "hair":
            a = (ix % 2 == 0) | (iy < 2)
        else:
            a = np.ones(ctx.N, bool)
        return np.broadcast_to(c, (ctx.N, 3)).copy(), a.astype(float), ctx.zeros()
    return mat


def materials():
    mats = {
        "skin": _flat("#2f5868"), "belly": _flat("#557f8a"), "ribs": _flat("#3a6573"), "head": _flat("#356070"),
        "jowl": _flat("#2f5868"), "face": _flat("#3f6a78"), "brow": _flat("#356070"), "snout": _flat("#4a7684"),
        "lip": _flat("#2f5868"), "jaw": _flat("#2f5868"), "gum": _flat("#7a2a3a"), "gill": _flat("#9a4250"),
        "lid": _flat("#3f6a78"), "eye": _flat("#9fe8ff", 0.9), "hair": _flat("#e8ecf2"), "barbel": _flat("#3f6a78"),
        "lamp": _flat("#9fe8ff", 0.9), "plate": _flat("#9aa0bb"), "keel": _flat("#b9bdd4"),
        "seam": _flat("#ffd98a", 0.95), "claw": _flat("#e4e7ee"), "ray": _flat("#6d98a6"), "fp_arm": _flat("#2f5868"),
        "corona": _rayglow("#fff2c4", ENTRY, 14.0), "corona_b": _rayglow("#fff2c4", EXIT, 6.25),
        "core": _flat("#ffe9a8", 0.95), "core_hot": _flat("#ffffff", 1.0),
        "fin": _cut("#4f8796", "fin"), "fin_flap": _cut("#4f8796", "fin_flap"), "web": _cut("#4f8796", "web"),
        "calf_fin": _cut("#4f8796", "plain_fin"), "teeth": _cut("#f4f6fa", "teeth"),
        "brow_hair": _cut("#eef1f6", "hair"), "wisp": _cut("#e6eaf0", "hair"), "accent": mat_accent,
    }
    mats.update(sword_materials())
    return mats


# ============================================================================= the sword (embedded and held)

def sword_materials():
    return {"s_blade": _flat("#f7ecc8", 0.35), "s_fuller": _flat("#fffbea", 0.6), "s_hilt": _flat("#d8a446", 0.3),
            "s_ray": _flat("#e6b450", 0.45), "s_sun": _flat("#ffe08a", 0.7), "s_grip": _flat("#3a2a1c"),
            "s_pommel": _flat("#e8b85a", 0.5)}


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
