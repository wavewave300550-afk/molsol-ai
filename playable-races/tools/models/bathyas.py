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
DRAWN = {"unshackled", "daybreak"}          # the sword is out of his body (the real item is in his hand)
SEAMED = {"bastion", "daybreak"}            # light leaks between the armour plates
CROUCH = {"unshackled"}                     # the predator's crouch (used by the animation set)

# --------------------------------------------------------------------------- the hunch
CHEST_PIVOT = (0.0, 17.0, 2.0)              # the upper body pitches forward from the waist
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
ENTRY = (0.0, 22.75, -3.25)                 # the front wound: the heart, just under the pectorals
SWORD_CLIMB = 28.0                          # + the hunch: the blade climbs ~50 deg in the world on its way out
SWORD_YAW = 8.0                             # and leaves a little left of the spine (it reads from behind)
_D = np.array([math.sin(math.radians(SWORD_YAW)) * math.cos(math.radians(SWORD_CLIMB)),
               math.sin(math.radians(SWORD_CLIMB)),
               math.cos(math.radians(SWORD_YAW)) * math.cos(math.radians(SWORD_CLIMB))])


def along(t: float):
    """Point on the sword axis (chest frame), t units from the entry wound toward the back."""
    return tuple(np.array(ENTRY) + _D * t)


EXIT_T = 10.0                               # where the blade leaves the back (between tergites 2 and 3)
EXIT = along(EXIT_T)
TIP_T = 21.25                               # 11 px of blade out of the back
GUARD_T = -0.75                             # the sunburst guard just in front of the wound
SWORD_LEN = 30.0                            # pommel to tip (the held sword is the same length)
GUARD_Y = 3.0                               # sword-local height of the guard above the grip centre
BLADE_Y = 3.75                              # sword-local height where the blade starts
TIP_Y = 26.25                               # sword-local tip (the held model: 30 px from pommel to tip)


def _sword_basis():
    """Columns: the embedded sword's local X (blade width), Y (blade) and Z (flat normal) in the chest frame."""
    y = _D / np.linalg.norm(_D)
    z = np.array([0.0, -y[2], y[1]])         # in the sagittal plane, perpendicular to the blade: the flats face
    z = z - y * float(z @ y)                 # down-back (the 3rd-person camera) and up-front (the head)
    z = -z / np.linalg.norm(z)
    x = np.cross(y, z)
    return np.column_stack([x, y, z])


SWORD_ROT = euler_for(_sword_basis())

# --------------------------------------------------------------------------- the back: overlapping tergites (chest frame)
# (centre y, centre z, outward normal angle from +Z toward +Y in degrees, width, length) from the nape down
TERGITES = [
    (31.0, 1.5, 78.0, 9.0, 3.5),
    (30.0, 3.75, 52.0, 13.0, 3.75),
    (28.25, 5.4, 26.0, 15.0, 3.75),
    (25.75, 6.1, 8.0, 15.5, 3.75),
    (23.0, 6.15, -2.0, 15.0, 3.75),
    (20.25, 5.9, -8.0, 13.5, 3.75),
    (17.75, 5.45, -14.0, 12.0, 3.5),
]
WAIST_PLATES = [(15.25, 4.55, -12.0, 10.5, 3.25), (12.75, 4.2, -18.0, 9.5, 3.0)]   # on the trunk (world frame)
PLATES = TERGITES + WAIST_PLATES             # (the animation set lifts and jostles them in this order)
PLATE_T = 1.25                              # armour thickness

# bastion: the tergites slide together and down over the nape; daybreak: they lift apart (offset along normal, extra tilt)
PLATE_CLOSE = [(-0.35, 10.0), (-0.3, 7.0), (-0.25, 5.0), (-0.2, 3.0), (-0.2, 2.0), (-0.15, 0.0), (-0.1, -2.0),
               (-0.1, -3.0), (0.0, -4.0)]
PLATE_OPEN = [(0.5, -10.0), (0.6, -9.0), (0.7, -8.0), (0.7, -7.0), (0.65, -6.0), (0.6, -5.0), (0.5, -4.0),
              (0.45, -4.0), (0.4, -4.0)]

# --------------------------------------------------------------------------- shoulders, arms, neck
SHOULDER_C = (7.25, 27.25, 1.0)             # shoulder joint (chest frame, right side mirrored with x < 0)
ELBOW = (8.0, 19.25, -2.0)                  # world rest pose (|x|)
WRIST = (7.5, 12.75, -2.0)                  # the hand stays here in every form: held items sit in the claws
NECK_C = (0.0, 29.75, -1.5)                 # where the neck leaves the chest (chest frame)


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
        ("c", "breast", "chest", (0.0, 26.25, -4.25), (8.5, 2.5, 0.5)),
        ("c", "rsh", "r_pauldron", (-7.25, 30.5, 1.0), (4.5, 0.5, 6.0)),
        ("c", "lsh", "l_pauldron", (7.25, 30.5, 1.0), (4.5, 0.5, 6.0)),
        ("l", "r", "r_leg_g", (-5.5, 11.5, 0.0), (0.5, 3.0, 3.5)),
        ("l", "l", "l_leg_g", (5.5, 11.5, 0.0), (0.5, 3.0, 3.5)),
        ("f", "r", "r_foot", (-3.25, 2.25, -0.25), (3.0, 0.5, 2.5)),
        ("f", "l", "l_foot", (3.25, 2.25, -0.25), (3.0, 0.5, 2.5)),
    ])
    m.pack()
    return m


# ----------------------------------------------------------------------------- legs: powerful, digitigrade-ish

HIP = (3.0, 14.25, 0.75)
KNEE = (3.5, 8.25, -2.0)
ANKLE = (3.5, 3.5, 1.25)
BALL = (3.5, 1.0, -1.75)


def _legs(m: Model) -> None:
    for s, g, p in ((-1, "r_leg_g", "r"), (1, "l_leg_g", "l")):
        th, sh, ft = LEG_POSE["base"]
        hip, knee, ankle, ball = (np.array([s * v[0], v[1], v[2]]) for v in (HIP, KNEE, ANKLE, BALL))
        lg = m.bones[g]
        lg.variant.update({v: ((0, 0, 0), (LEG_POSE[v][0], 0.0, 0.0)) for v in VARIANTS if LEG_POSE[v][0]})
        # the thigh: a great muscle mass tapering to the knee
        limb(m, g, hip + (0, 1.25, 0.25), knee + (0, 2.25, 0.5), 5.0, 5.75, "skin", extend=0.5)
        limb(m, g, (hip + knee) / 2 + (0, -0.75, -0.25), knee + (0, -0.5, 0.25), 4.25, 4.75, "skin")
        sn = m.bone(f"{p}_shin", g, tuple(knee))
        sn.variant.update({v: ((0, 0, 0), (LEG_POSE[v][1], 0.0, 0.0)) for v in VARIANTS if LEG_POSE[v][1]})
        slab(m, sn.name, knee + (0, 0.25, -2.25), (0, 0.25, -1), (0, 1, 0.3), 3.5, 3.0, 1.0, "plate")      # knee cop
        limb(m, sn.name, knee + (0, 0.5, 0.25), ankle + (0, -0.25, 0), 3.5, 3.75, "skin")                   # the shin
        mid = (knee + ankle) / 2
        dn = (ankle - knee) / np.linalg.norm(ankle - knee)
        fw = np.array([0.0, dn[2], -dn[1]])                       # the shin's front normal
        fw = -fw if fw[2] > 0 else fw
        for k, f in enumerate((-0.28, 0.12)):                     # two overlapping greave plates down the front
            slab(m, sn.name, mid + dn * f * 5.0 + fw * (1.9 + 0.1 * k), fw, dn, 3.5, 2.75, 0.75, "plate")
        m.cube(sn.name, (s * 3.5, 4.0, 2.0), (0.0, 3.5, 2.5), "fin", cutout=True)                          # calf fin
        fb = m.bone(f"{p}_foot", sn.name, tuple(ankle))
        fb.variant.update({v: ((0, 0, 0), (LEG_POSE[v][2], 0.0, 0.0)) for v in VARIANTS if LEG_POSE[v][2]})
        limb(m, fb.name, ankle + (0, 0.25, 0.25), ball + (0, 0, -0.25), 3.0, 2.75, "skin", fwd=(0, 1, -0.6))  # raised heel
        m.box(fb.name, (s * 3.5, 0.75, -1.75), (3.75, 1.5, 2.5), "skin")                                      # ball of the foot
        for k, (dx, ang) in enumerate(((-1.25, -12.0), (0.0, 0.0), (1.25, 12.0))):                          # three webbed toes
            x = s * 3.5 + s * dx
            a = math.radians(ang * s)
            d = np.array([math.sin(a) * 0.35, 0.0, -math.cos(a)])
            base = np.array([x, 0.6, -2.5])
            tip = base + d * 2.5
            m.cube(fb.name, (x - 0.625, 0.0, -5.0), (1.25, 1.25, 2.75), "skin", pivot=(x, 0.6, -2.25),
                   rot=(0.0, -ang * s, 0.0))
            cl = tip + d * 0.5
            m.cube(fb.name, (cl[0] - 0.375, 0.0, cl[2] - 1.0), (0.75, 1.0, 1.25), "claw", pivot=(cl[0], 0.5, cl[2]),
                   rot=(-10.0, -ang * s, 0.0))
        m.cube(fb.name, (s * 3.5 - 1.25, 0.25, -5.0), (2.5, 0.75, 2.5), "web", cutout=True, faces={"up", "down"})
        m.cube(fb.name, (s * 3.5 - 0.375, 1.25, 1.5), (0.75, 1.0, 1.75), "claw", pivot=(s * 3.5, 1.75, 1.5),
               rot=(30.0, 0.0, 0.0))                                                                          # heel spur
        fb.locators[f"{p}_step"] = (s * 3.5, 0.2, -2.0)


def _settle(m: Model):
    """Hip drop per form: how far the body sinks so that the bent legs stand on the ground."""
    from kit.render import collect_quads
    drop = {}
    legs = set(m.subtree("r_leg_g")) | set(m.subtree("l_leg_g"))
    others = [b for b in m.order if b not in legs and b not in ("root", "rightLeg", "leftLeg")]
    for v in VARIANTS:
        quads = collect_quads(m, v, None, hide=[b for b in others if m.bones[b].parent in (None, "root")] + ["waist"])
        lo = min(float(qd[0][:, 1].min()) for qd in quads)
        drop[v] = round(lo * 4) / 4                                   # snapped to quarter pixels
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
    m.box(t.name, (0.0, 13.75, 0.75), (10.0, 3.5, 6.5), "skin")                      # pelvis
    m.box(t.name, (0.0, 16.5, 1.25), (9.0, 3.0, 6.25), "belly")                      # the waist
    c = m.bone("chest", t.name, CHEST_PIVOT, (POSE["base"], 0.0, 0.0))
    c.variant.update({v: ((0, 0, 0), (POSE[v], 0.0, 0.0)) for v in VARIANTS if v != "base"})
    m.box(c.name, (0.0, 21.75, 1.0), (11.0, 7.5, 8.0), "belly", faces={"north", "east", "west", "down"})  # ribcage
    m.box(c.name, (0.0, 27.0, 1.0), (13.0, 4.0, 8.5), "skin", faces={"north", "east", "west", "down", "up"})  # upper chest
    m.box(c.name, (0.0, 29.75, 1.25), (9.0, 2.0, 6.5), "skin", faces={"north", "up"})                       # trapezius
    for s in (-1, 1):                                                                     # pectorals over the heart
        m.cube(c.name, (s * 3.1 - 2.75, 23.25, -4.0), (5.5, 4.0, 1.25), "skin", pivot=(s * 3.1, 25.25, -3.5),
               rot=(0.0, s * 8.0, s * 6.0))
        m.box(c.name, (s * 5.75, 21.25, 1.25), (1.0, 6.0, 6.5), "ribs")                 # flank: the lateral line
    c.locators["lure_c"] = (0.0, 22.75, -12.0)
    c.locators["back"] = (0.0, 26.0, 8.5)


# ----------------------------------------------------------------------------- isopod tergites over the back

def _plate(m: Model, bone: str, y: float, z: float, ang: float, w: float, ln: float, k: int) -> None:
    n = _ang(ang)                                       # outward normal (YZ plane)
    tng = np.array([0.0, -n[2], n[1]])                  # along the back, pointing down toward the tail
    if tng[1] > 0:
        tng = -tng
    tng = tng * math.cos(math.radians(8.0)) + n * math.sin(math.radians(8.0))   # the trailing edge lifts over the next plate
    c = np.array([0.0, y, z])
    flange = 2.75
    core = w - 2 * 1.75
    slab(m, bone, c, n, tng, core, ln, PLATE_T, "plate")
    for s in (-1, 1):                                   # the sides bend forward round the flanks
        bend = 48.0 if k < 7 else 40.0
        side = np.array([s * 1.0, 0.0, 0.0])
        nn = n * math.cos(math.radians(bend)) + side * math.sin(math.radians(bend))
        edge = c + side * (core / 2 - 0.25)
        across = np.cross(tng, nn)
        across = across if across[0] * s > 0 else -across
        slab(m, bone, edge + across * (flange / 2) - nn * 0.2, nn, tng, flange, ln - 0.25, PLATE_T, "plate")
    slab(m, bone, c + n * (PLATE_T / 2 + 0.3), n, tng, 1.5, ln - 0.75, 0.75, "keel")   # the raised spinal keel
    # light in the seams (bastion, daybreak): a glowing band just under the trailing edge
    slab(m, bone, c - n * 0.45 + tng * (ln / 2 - 0.5), n, tng, w - 1.0, 1.25, 0.5, "seam", only=SEAMED)


def _plates(m: Model) -> None:
    for k, (y, z, ang, w, ln) in enumerate(PLATES):
        par = "chest" if k < len(TERGITES) else "trunk"
        n = _ang(ang)
        b = m.bone(f"plate{k}", par, (0.0, y, z))
        dc, tc = PLATE_CLOSE[k]
        do, to = PLATE_OPEN[k]
        b.variant["bastion"] = (tuple(n * dc + np.array([0.0, -0.15 * k, 0.0])), (tc, 0.0, 0.0))
        b.variant["daybreak"] = (tuple(n * do), (to, 0.0, 0.0))
        _plate(m, b.name, y, z, ang, w, ln, k)


# ----------------------------------------------------------------------------- pauldrons: three lames over each shoulder

LAMES = [  # (x across, y, outward tilt, width along the slope, depth front-back)
    (5.75, 30.4, 16.0, 4.5, 8.5),
    (8.0, 29.35, 40.0, 4.0, 8.0),
    (9.35, 27.4, 66.0, 3.5, 7.25),
]


def _pauldrons(m: Model) -> None:
    for s, p in ((-1, "r"), (1, "l")):
        sx, sy, sz = SHOULDER_C
        pa = m.bone(f"{p}_pauldron", "chest", (s * sx, sy, sz))
        pa.variant.update({"bastion": ((-s * 0.75, -0.5, -1.25), side_rot((-14.0, 0.0, 16.0), s)),
                           "daybreak": ((s * 0.5, 0.75, 0.25), side_rot((0.0, 0.0, -10.0), s)),
                           "unshackled": ((0.0, 0.25, -0.25), side_rot((-6.0, 0.0, 4.0), s))})
        for k, (x, y, tilt, w, d) in enumerate(LAMES):
            a = math.radians(tilt)
            n = np.array([s * math.sin(a), math.cos(a), 0.0])
            c = np.array([s * x, y, sz + 0.25 - 0.25 * k])
            slab(m, pa.name, c, n, (0, 0, 1), w, d, PLATE_T, "plate")
            # the lame curls down over the front of the shoulder
            fz = c[2] - d / 2
            fn = np.array([s * math.sin(a) * 0.4, math.cos(a) * 0.4, -1.0])
            slab(m, pa.name, (c[0], c[1] - 0.6, fz + 0.1), fn, (0, -1, 0.2), w - 0.5, 1.75, 1.0, "plate")
            slab(m, pa.name, c - n * 0.45 + np.array([0, 0, 0]), n, (0, 0, 1), w - 0.5, d - 1.0, 0.5, "seam", only=SEAMED)


# ----------------------------------------------------------------------------- torn dorsal fins

def _fins(m: Model) -> None:
    for s, p in ((-1, "r"), (1, "l")):
        root = (s * 4.75, 26.0, 6.75)
        f0 = m.bone(f"{p}_fin0", "chest", root, side_rot((-30.0, 0.0, -34.0), s))
        f0.variant.update({"daybreak": ((0, 0, 0), side_rot((-36.0, 0.0, -52.0), s)),
                           "bastion": ((0, -0.5, -0.5), side_rot((-8.0, 0.0, -14.0), s)),
                           "unshackled": ((0, 0, 0), side_rot((-36.0, 0.0, -44.0), s)),
                           "maw": ((0, 0, 0), side_rot((-14.0, 0.0, -26.0), s))})
        x, y, z = root
        # three rays fanning up and back from the root (fin plane: x = root x), leading ray tallest
        for k, (ang, ln) in enumerate(((8.0, 8.5), (30.0, 8.0), (52.0, 6.0))):
            d = np.array([0.0, math.cos(math.radians(ang)), math.sin(math.radians(ang))])
            a0 = np.array(root) + d * 0.25
            limb(m, f0.name, a0 + d * ln, a0, 0.5, 0.5, "ray", fwd=(0, -d[2], d[1]))
        m.cube(f0.name, (x, y, z - 0.5), (0.0, 8.5, 5.5), "fin", cutout=True)                 # the membrane
        f1 = m.bone(f"{p}_fin1", f0.name, (x, y + 0.5, z + 4.5))
        d = np.array([0.0, math.cos(math.radians(74.0)), math.sin(math.radians(74.0))])
        limb(m, f1.name, np.array([x, y + 0.5, z + 4.5]) + d * 4.5, (x, y + 0.5, z + 4.5), 0.5, 0.5, "ray",
             fwd=(0, -d[2], d[1]))
        m.cube(f1.name, (x, y - 0.75, z + 4.25), (0.0, 5.5, 4.25), "fin", cutout=True)        # the torn trailing flap


# ----------------------------------------------------------------------------- the sun through his heart

def sword_parts(m: Model, bone: str, base, blade_from: float = BLADE_Y, tip: float = TIP_Y, hilt: bool = True,
                **kw) -> None:
    """The sword, shared by the embedded and the held sword.  Local frame: grip centre at
    `base`, blade along +Y, broad faces along +-Z (the width runs along X)."""
    bx, by, bz = base

    def box(cy, w, h, t, mat, rot=None, **k2):
        size = (w, h, t)
        c = (bx, by + cy, bz)
        o = tuple(c[i] - size[i] / 2 for i in range(3))
        if rot is None:
            return m.cube(bone, o, size, mat, **kw, **k2)
        return m.cube(bone, o, size, mat, pivot=c, rot=rot, **kw, **k2)

    if hilt:
        box(-3.0, 1.75, 1.75, 1.75, "s_pommel")                         # pommel: a small sun
        box(-3.0, 1.25, 1.25, 1.25, "s_pommel", rot=(0.0, 45.0, 0.0))  # (an octagon from every side)
        box(-1.85, 1.75, 0.5, 1.25, "s_hilt")                          # collar
        box(0.25, 1.0, 3.75, 1.0, "s_grip")                            # wrapped grip
        box(GUARD_Y, 2.75, 1.0, 2.75, "s_sun")                         # the sun disc at the heart of the guard
        box(GUARD_Y, 2.0, 1.25, 2.0, "s_sun", rot=(0.0, 45.0, 0.0))
        g = (bx, by + GUARD_Y, bz)
        rays(m, bone, g, 8, 1.25, 3.75, 0.5, "s_hilt", plane="flat", thick=0.5, phase=0.0, **kw)             # sunburst
        rays(m, bone, g, 8, 1.25, 2.75, 0.5, "s_hilt", plane="flat", thick=0.5, phase=22.5, **kw)
    main = tip - 1.75 - blade_from
    box(blade_from + main / 2, 2.5, main, 0.5, "s_blade")
    box(blade_from + main / 2 - 0.25, 0.75, main - 0.5, 1.0, "s_fuller")      # the raised spine: the blade reads edge-on too
    box(tip - 1.25, 1.5, 1.0, 0.5, "s_blade")
    box(tip - 0.375, 0.75, 0.75, 0.5, "s_blade")


def _sword(m: Model) -> None:
    sw = m.bone("sword", "chest", ENTRY, SWORD_ROT)
    ex, ey, ez = ENTRY
    base = (ex, ey - GUARD_Y - GUARD_T, ez)                          # grip centre so that the guard sits at GUARD_T
    sword_parts(m, sw.name, base, blade_from=GUARD_Y + GUARD_T + EXIT_T - 0.75, tip=GUARD_Y + GUARD_T + TIP_T,
                skip=DRAWN)
    m.cube(sw.name, (ex - 1.0, ey - 0.75 - 1.0, ez - 0.25), (2.0, 2.0, 0.5), "s_blade", skip=DRAWN)   # the blade at the wound
    sw.locators["hilt"] = (ex, ey - GUARD_Y - GUARD_T, ez)


def _corona(m: Model) -> None:
    """The light at both wounds: thin glowing rays radiating in a circle, fading outward."""
    x, y, z = ENTRY
    cz = -4.5                                                         # in front of the pectorals
    cf = m.bone("corona_f", "chest", (x, y, cz))
    hide = {"bastion"}                                                # bastion: the light is shut inside the plates
    rays(m, cf.name, (x, y, cz), 8, 2.0, 8.5, 0.75, "corona", plane="front", phase=0.0, skip=hide)
    rays(m, cf.name, (x, y, cz - 0.05), 8, 2.0, 5.75, 0.5, "corona", plane="front", phase=22.5, skip=hide)
    rays(m, cf.name, (x, y, cz - 0.1), 8, 3.0, 13.5, 0.75, "corona", plane="front", phase=11.25, only={"lure"})
    rays(m, cf.name, (x, y, cz - 0.1), 8, 3.0, 11.5, 0.75, "corona", plane="front", phase=33.75,
         only={"lure", "unshackled", "daybreak"})
    m.box(cf.name, (x, y, cz + 0.25), (3.0, 3.0, 0.5), "core", skip=hide)                     # the glare at the wound
    m.box(cf.name, (x, y, cz + 0.05), (2.0, 4.0, 0.5), "core", only=DRAWN)                    # the open sun
    m.box(cf.name, (x, y, cz + 0.05), (4.0, 2.0, 0.5), "core", only=DRAWN)
    m.box(cf.name, (x, y, cz - 0.15), (2.0, 2.0, 0.5), "core_hot", only=DRAWN)
    cf.locators["wound"] = (x, y, cz - 0.5)
    # the exit wound: a smaller corona in the plane of the back plates
    ex, ey, ez = EXIT
    pz = ez + 1.5
    cb = m.bone("corona_b", "chest", (ex, ey, pz), (-14.0, 0.0, 0.0))
    rays(m, cb.name, (ex, ey, pz), 6, 1.5, 5.0, 0.5, "corona", plane="back", phase=0.0)
    rays(m, cb.name, (ex, ey, pz + 0.05), 6, 1.5, 3.25, 0.5, "corona", plane="back", phase=30.0)
    m.box(cb.name, (ex, ey, pz - 0.2), (2.5, 2.5, 0.5), "core")
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
    return round(a, 2), round(b, 2), e


FINGER_Z = (-3.25, -2.0, -0.75)
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
            hd.variant[v] = ((0.0, 0.0, 0.0), (-(a + b), 0.0, 0.0))
        dl = m.bone(f"{p}_delt", up.name, tuple(S0))                   # (hidden in first person: it sits above the eye line)
        m.box(dl.name, tuple(S0 + (s * 0.25, -0.5, 0.25)), (4.5, 4.5, 4.75), "skin")       # the deltoid under the pauldron
        limb(m, dl.name, S0 + (0, -1.5, 0), E0 + (0, 0.25, 0), 3.75, 3.75, "skin")       # upper arm
        # the forearm: massive, shelled on the outside, a torn fin trailing behind
        limb(m, fo.name, E0 + (0, 0.5, 0.25), W0 + (0, -0.25, 0), 4.5, 4.75, "skin")
        ax = (E0 - W0) / np.linalg.norm(E0 - W0)
        mid = (E0 + W0) / 2
        out = np.array([s * 1.0, 0.0, 0.0])
        for k, f in enumerate((0.22, -0.18)):                                              # vambrace lames
            slab(m, fo.name, mid + ax * f * 6.5 + out * (2.45 + 0.1 * k), out, -ax, 4.0, 3.25, 0.75, "plate")
        slab(m, fo.name, E0 + (0, -0.25, 2.25), (0, -0.2, 1), (0, -1, 0), 3.0, 2.5, 0.75, "plate")      # elbow cop
        m.cube(fo.name, (s * 7.75, 13.75, 0.25), (0.0, 4.75, 3.25), "fin", cutout=True)                 # forearm fin
        # the hand: palm, three long webbed fingers with hard white claws, a thumb
        hz = W0[2]
        m.box(hd.name, (s * 7.5, 11.25, hz), (3.0, 3.0, 3.75), "skin")
        m.cube(hd.name, (s * 7.5, 6.75, hz - 1.75), (0.0, 3.5, 3.5), "web", cutout=True)
        for k, (fz, fan) in enumerate(zip(FINGER_Z, FINGER_FAN)):
            f = m.bone(f"{p}_finger{k}", hd.name, (s * 7.5, 9.75, fz), (fan, 0.0, 0.0))
            m.box(f.name, (s * 7.5, 8.25, fz), (1.25, 3.25, 1.25), "skin")
            m.cube(f.name, (s * 7.5 - 0.5, 5.25, fz - 0.6), (1.0, 2.0, 1.0), "claw", pivot=(s * 7.5, 6.75, fz),
                   rot=(-16.0, 0.0, 0.0))
        th = m.bone(f"{p}_thumb", hd.name, (s * 6.5, 11.0, hz - 1.75), side_rot((-24.0, 0.0, -14.0), s))
        m.box(th.name, (s * 6.5, 9.5, hz - 1.75), (1.25, 2.75, 1.25), "skin")
        m.cube(th.name, (s * 6.5 - 0.375, 7.5, hz - 2.25), (0.75, 1.25, 0.75), "claw")
        hd.locators[f"{p}_claws"] = (s * 7.5, 5.5, hz)


# ----------------------------------------------------------------------------- the head: goblin shark, hung low and forward

def _head(m: Model, drop) -> None:
    N0 = _neck("base")
    for v in DRAWN | {"bastion"}:                              # (the groups follow the hips; the skull follows the neck)
        pass
    for g in ("head_g",):
        m.bones[g].variant.update({v: ((0.0, -d, 0.0), None) for v, d in drop.items() if d})
    sk = m.bone("skull", "head_g", tuple(N0))
    head_pose = {   # extra (offset, rotation) of the head per form, on top of following the neck
        "lure": ((0.0, 0.5, 1.25), (-10.0, 14.0, 6.0)),      # recoils from his own light, turned aside
        "maw": ((0.0, -0.75, -1.75), (6.0, 0.0, 0.0)),       # thrust forward and down
        "bastion": ((0.0, -0.5, 2.25), (16.0, 0.0, 0.0)),    # tucked under the shell
        "unshackled": ((0.0, -0.25, -1.0), (2.0, 0.0, 0.0)),  # low and forward, level gaze
        "daybreak": ((0.0, 0.75, 1.25), (-26.0, 0.0, 0.0)),  # thrown back as the light floods out
    }
    for v in VARIANTS:
        if v == "base":
            continue
        dn = _neck(v, drop.get(v, 0.0)) - N0 + np.array([0.0, drop.get(v, 0.0), 0.0])   # head_g already dropped
        off, rot = head_pose.get(v, ((0, 0, 0), (0, 0, 0)))
        sk.variant[v] = (tuple(np.round(dn + np.array(off), 3)), rot)
    x0, y0, z0 = N0
    # neck and skull
    limb(m, sk.name, (0, 28.25, -5.25), (0, 26.25, -9.5), 5.0, 4.25, "skin", fwd=(0, -1, -0.2))
    m.box(sk.name, (0, 27.5, -10.25), (6.0, 4.5, 5.0), "head")                                  # the old bald skull
    m.box(sk.name, (0, 29.875, -10.0), (4.75, 0.75, 4.0), "head")                               # its dome
    m.box(sk.name, (0, 25.25, -9.75), (6.25, 2.25, 4.0), "jowl")                               # sagging jowls
    m.box(sk.name, (0, 28.75, -12.875), (6.0, 1.25, 1.75), "brow")                             # the heavy brow ridge
    m.box(sk.name, (0, 26.75, -13.0), (4.5, 2.75, 1.0), "face", ppu=4.0)                       # the face under it
    # the rostrum: a long flat blade of a snout, slightly upturned
    sweep(m, sk.name, "ros", [(0, 28.5, -13.25), (0, 28.6, -16.5), (0, 29.1, -19.75)], 4.0, 1.5, "snout", h0=1.25, h1=0.75,
          n=2, bones=False, normal=(0, 1, 0))
    for s, p in ((-1, "r"), (1, "l")):
        m.box(sk.name, (s * 2.6, 27.6, -12.25), (0.75, 0.75, 1.0), "eye", ppu=4.0)              # small ice-blue eyes
        lid = m.bone(f"lid_{p}", sk.name, (s * 2.6, 28.05, -12.25))
        m.cube(lid.name, (s * 2.6 - 0.45, 27.95, -12.85), (0.9, 0.25, 1.2), "lid")
        br = m.bone(f"brow_{p}", sk.name, (s * 1.75, 28.75, -13.5), side_rot((0.0, 0.0, 8.0), s))
        m.box(br.name, (s * 1.75, 29.0, -13.25), (2.75, 0.75, 1.25), "hair")                   # the white tuft
        m.cube(br.name, (s * 2.5 - (2.5 if s < 0 else 0.0), 26.25, -13.75), (2.5, 3.0, 0.0), "brow_hair", cutout=True,
               pivot=(s * 2.5, 29.0, -13.75), rot=(0.0, -s * 34.0, 0.0))                        # long brows drooping out
        for k in range(3):                                                                       # gill flaps
            gz = -7.25 - k * 1.0
            gl = m.bone(f"gill_{p}{k}", sk.name, (s * 2.9, 26.75, gz - 0.5))
            m.cube(gl.name, (s * 2.9 - 0.125, 25.0, gz - 0.5), (0.25, 3.0, 1.25), "gill")
    # the protrusible jaw apparatus
    jw = m.bone("jaws", sk.name, (0, 26.0, -11.0))
    jw.variant["maw"] = ((0.0, -0.5, -4.5), (4.0, 0.0, 0.0))
    m.box(jw.name, (0, 25.75, -15.0), (4.0, 1.0, 4.5), "lip")                                  # upper jaw under the snout
    m.box(jw.name, (0, 24.875, -15.0), (3.5, 1.25, 4.0), "teeth", cutout=True)                 # needle teeth (upper row)
    m.box(jw.name, (0, 25.0, -12.0), (3.5, 2.0, 3.0), "gum")                                   # the protrusible sling
    lo = m.bone("jaw", jw.name, (0, 25.0, -11.75))
    lo.variant.update({"maw": ((0, 0, 0), (40.0, 0.0, 0.0)), "daybreak": ((0, 0, 0), (14.0, 0.0, 0.0)),
                       "unshackled": ((0, 0, 0), (6.0, 0.0, 0.0))})
    m.box(lo.name, (0, 23.75, -14.75), (4.5, 1.25, 6.0), "jaw")                                # the underbite
    m.box(lo.name, (0, 24.875, -15.25), (3.5, 1.25, 4.5), "teeth", cutout=True)                # needle teeth (lower row)
    for s, p in ((-1, "r"), (1, "l")):                                                          # barbels with glowing tips
        names = sweep(m, lo.name, f"barbel_{p}", [(s * 1.25, 23.25, -16.0), (s * 1.5, 21.0, -15.25), (s * 1.75, 18.75, -14.25)],
                      0.75, 0.5, "barbel", n=1)
        m.box(names[-1], (s * 1.75, 18.6, -14.2), (0.75, 0.75, 0.75), "lamp")
    lo.locators["maw"] = (0.0, 24.5, -17.5)
    sk.locators["eyes"] = (0.0, 27.75, -13.25)
    sk.locators["gills"] = (0.0, 26.0, -8.0)


# ============================================================================= materials (Gate A: flat placeholders)

def _flat(base, glow=0.0, up=0.12, down=0.12):
    c = px.col(base)
    pal = px.pal(c * 0.55, c * 0.78, c, np.clip(c * 1.18 + 0.03, 0, 1))

    def mat(ctx):
        return px.shade(ctx, pal, offset=0.12, up=up, down=down), ctx.ones(), np.full(ctx.N, glow)
    return mat


def _rayglow(base):
    c = px.col(base)

    def mat(ctx):
        v = np.clip(ctx.local[:, 2], 0, 1)                    # 0 at the root -> 1 at the tip of the ray
        rgb = c[None, :] * (1 - 0.35 * v[:, None]) + np.array([1.0, 0.75, 0.35])[None, :] * 0.35 * v[:, None]
        g = np.clip(0.95 * (1 - v) ** 1.2 + 0.08, 0, 1)
        return rgb, ctx.ones(), g
    return mat


def _cut(base, kind):
    c = px.col(base)

    def mat(ctx):
        ix, iy, W, H = px.texel(ctx)
        if not px.side(ctx) and kind != "web":
            return np.broadcast_to(c, (ctx.N, 3)).copy(), ctx.zeros(), ctx.zeros()
        if kind == "fin":
            u = ix / max(W - 1, 1)
            v = iy / max(H - 1, 1)
            if ctx.face == "west":
                u = 1 - u
            a = (v < 0.55 + 0.4 * u) & ~((iy % 5 == 4) & (u > 0.55)) & (v > 0.12 * (1 - u))
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
        "corona": _rayglow("#fff2c4"), "core": _flat("#ffe9a8", 0.95), "core_hot": _flat("#ffffff", 1.0),
        "fin": _cut("#4f8796", "fin"), "web": _cut("#4f8796", "web"), "teeth": _cut("#f4f6fa", "teeth"),
        "brow_hair": _cut("#eef1f6", "hair"), "accent": mat_accent,
    }
    mats.update(sword_materials())
    return mats


# ============================================================================= the sword (embedded and held)

def sword_materials():
    return {"s_blade": _flat("#f7ecc8", 0.35), "s_fuller": _flat("#fffbea", 0.6), "s_hilt": _flat("#d8a446", 0.3),
            "s_sun": _flat("#ffe08a", 0.7), "s_grip": _flat("#3a2a1c"), "s_pommel": _flat("#e8b85a", 0.5)}


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
