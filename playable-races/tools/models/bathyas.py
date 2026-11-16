"""Race 008 - Bathyas, the Sun-Impaled.  UNIQUE race.

An abyssal humanoid chimera - deep-sea anglerfish, goblin shark and giant isopod - drawn
as an exhausted, irritable old man who has carried a sun through his heart for longer
than he can remember.  Design rules (docs/CREATIVE.md, v1.2 redesign):

  * a clearly HUNCHED, elongated silhouette: the upper torso pitches forward from the
    waist (bone "chest"), the head hangs low and forward of the heavy, uneven shoulders,
    a thick dorsal hump of seven broad, curved giant-isopod tergites runs down the back
    with raised spines and two torn fins; long arms hang to the knees and end in webbed,
    hard-tipped fingers; humanoid thighs over armoured aquatic shins and WIDE clawed feet;
  * a long, aged goblin-shark head: a bald wrinkled skull, a heavy brow over small deep
    eyes behind heavy lids, a recessed nose above a flat projecting snout, and under it a
    protrusible jaw apparatus (bone "jaws") with irregular needle teeth, an underbite and
    two scraggly barbels; gill flaps along the neck;
  * near light-absorbing blue-black skin that still reads in Minecraft: wet rims along
    upper edges, sparse green-grey sheen, small pits and bumps, a few cold photophores;
  * ONE light source - the white-gold sword through his chest: hilt and sun-guard just
    below the sternum, ~11 px of blade out of the back, charred tissue at entry and exit,
    white-gold fractures along the ribs, the skin facing it lit warm, and light shells at
    both wounds (core_f / core_b) that beat like a heart.

Variants: base (Impaled) | lure (blazing) | maw (Goblin Maw Rush) | bastion (Isopod
Bastion) | unshackled (sword drawn: open wound, predatory crouch) | daybreak (lit gold
from within).  The held sword is its own small model: build_sword() / sword_materials().
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

from kit.geo import Model, rot_matrix
from kit import pixel as px
from models.common import accents, fp_sleeves, humanoid, mat_accent, side_rot

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
DRAWN = {"unshackled", "daybreak"}          # the sword is out of his body (held in the hand)
NO_SWORD = DRAWN | {"bastion"}              # bastion: plates and forearms close over it
CROUCH = {"unshackled", "daybreak"}         # bent knees, hips 1 px lower

# --------------------------------------------------------------------------- the hunch
CHEST_PIVOT = (0.0, 16.5, 0.25)             # the upper torso pitches forward from the waist
CHEST_PITCH = 18.0
CHEST_POSE = {"unshackled": 26.0, "daybreak": 8.0, "bastion": 24.0}
ARM_DZ = -1.25                              # arm geometry sits a little forward, under the pitched shoulders


def chest_world(p, pitch: float = CHEST_PITCH):
    """Rest-pose position of a point given in the (upright) chest frame."""
    piv = np.array(CHEST_PIVOT)
    return piv + rot_matrix((pitch, 0.0, 0.0)) @ (np.asarray(p, float) - piv)


# --------------------------------------------------------------------------- the impalement (chest frame)
ENTRY = (0.0, 18.0, -2.75)                  # front wound, just below the sternum
SWORD_PITCH = 12.0                          # + the chest's 18: the blade climbs 30 deg on its way out of the back
SWORD_YAW = 10.0                            # and leaves a little left of the spine (it reads from behind)
SWORD_ROT = (-(90.0 - SWORD_PITCH), SWORD_YAW, 0.0)
GUARD_Y = 3.5                               # sword-local height that sits at the entry wound
_D = rot_matrix(SWORD_ROT) @ np.array([0.0, 1.0, 0.0])


def along(t: float):
    """Point on the sword axis (chest frame), t units from the entry wound toward the back."""
    return tuple(np.array(ENTRY) + _D * t)


EXIT_T = 8.7                                # where the blade leaves the back (through tergite 3)
EXIT = along(EXIT_T)
TIP_T = 19.75                               # ~11 px of blade out of the back
HILT_T = -3.5                               # the hilt's middle, in front of the chest

# --------------------------------------------------------------------------- palettes (dark -> light)
SKIN = px.pal("#020303", "#060808", "#0b0f10", "#111718", "#182021", "#202b2b", "#2e3c3a", "#4a5c56")
CHITIN = px.pal("#030303", "#080909", "#0e1011", "#151819", "#1d2122", "#272d2d", "#3a4241", "#5c6762")
DAYSKIN = px.pal("#050302", "#0c0705", "#140c07", "#1d120a", "#28190e", "#362314", "#4b331c", "#6c4c29")
WISP = px.pal("#4c5452", "#6f7874", "#959d97", "#bcc2ba")                     # an old man's pale wisps
LIT = px.pal("#22160a", "#43290f", "#6e4718", "#a0712b", "#cf9d48", "#efcb82", "#fff0c6")
SUN = px.pal("#b07a2c", "#dcaa4a", "#f2d17e", "#fdeab4", "#fff8e2", "#ffffff")
STEEL = px.pal("#8d6a35", "#c39a55", "#e6c98c", "#f7e8c0", "#fffbea")       # the blade's metal (white gold)
GOLD = px.pal("#3c240b", "#6a4416", "#a06c24", "#cf9c3c", "#efc867", "#fbe7a2")
EMBER = px.pal("#010000", "#0a0403", "#1a0805", "#331007", "#5a1d0a")
GILL = px.pal("#100508", "#250b10", "#421218", "#691d20", "#8c302a")
BONE = px.pal("#3f3a2c", "#6e6648", "#9c9068", "#c8bb8c", "#e8dfba")
CLAW = px.pal("#030303", "#0c0b0a", "#1b1916", "#35302a", "#5f574a", "#958a74")
LEATHER = px.pal("#0d0805", "#1d120a", "#311f12", "#4a301b")
PHOTO = px.col("#7ee8cf")                   # cold photophores
PHOTO_DIM = px.col("#3c9c8f")
DAYGOLD = px.col("#ffd36e")
REFLECT = px.col("#2b413a")                 # sparse green-grey reflections
WET = px.col("#5b736c")                     # the rare wet specular texel
SPEC = px.col("#718c86")                    # specular on chitin


# ============================================================================= build

def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=256)
    humanoid(m)
    for g in ("torso_g", "head_g", "tail_g"):
        m.bones[g].variant.update({v: ((0.0, -1.0, 0.0), None) for v in CROUCH})
    _legs(m)
    _trunk(m)
    _plates(m)
    _fins(m)
    _sword(m)
    _core(m)
    _arms(m)
    _head(m)
    fp_sleeves(m, "skin", width=4.7)
    accents(m, [
        ("c", "breast", "chest", (0.0, 22.25, -3.25), (6.5, 1.5, 0.5)),
        ("c", "rsh", "r_pauldron", (-6.0, 25.25, 0.25 + ARM_DZ), (3.5, 0.5, 4.5)),
        ("c", "lsh", "l_pauldron", (6.0, 24.75, 0.25 + ARM_DZ), (3.5, 0.5, 4.5)),
        ("l", "r", "r_leg_g", (-4.5, 10.0, 0.0), (0.5, 3.5, 3.0)),
        ("l", "l", "l_leg_g", (4.5, 10.0, 0.0), (0.5, 3.5, 3.0)),
        ("f", "r", "r_foot", (-2.75, 2.25, -1.25), (3.5, 0.5, 2.5)),
        ("f", "l", "l_foot", (2.75, 2.25, -1.25), (3.5, 0.5, 2.5)),
    ])
    m.pack()
    return m


# ----------------------------------------------------------------------------- legs: thighs, armoured aquatic shins, wide feet

def _legs(m: Model) -> None:
    for s, g, p in ((-1, "r_leg_g", "r"), (1, "l_leg_g", "l")):
        m.bones[g].rot = (-6.0, 0.0, 0.0)                                                # knees a little bent
        m.bones[g].variant.update({v: ((0.0, -1.0, 0.0), (-24.0, 0.0, 0.0)) for v in CROUCH})
        m.box(g, (s * 2.5, 10.25, 0.0), (3.0, 4.5, 4.0), "skin")                       # thigh
        m.box(g, (s * 2.5, 7.5, -0.25), (2.5, 2.0, 3.5), "skin")                       # above the knee
        m.box(g, (s * 2.5, 6.75, -2.0), (2.5, 2.0, 1.0), "knee")                       # knee plate
        sh = m.bone(f"{p}_shin", g, (s * 2.5, 6.75, -0.25), (14.0, 0.0, 0.0))
        sh.variant.update({v: ((0, 0, 0), (50.0, 0.0, 0.0)) for v in CROUCH})
        m.box(sh.name, (s * 2.5, 4.25, 0.0), (3.0, 4.5, 3.5), "shin")                  # armoured aquatic shin
        m.box(sh.name, (s * 2.5, 4.5, 3.0), (0.0, 3.5, 2.5), "fin", cutout=True)       # calf fin
        ft = m.bone(f"{p}_foot", sh.name, (s * 2.5, 2.0, 0.0), (-8.0, 0.0, 0.0))
        ft.variant.update({v: ((0, 0, 0), (-26.0, 0.0, 0.0)) for v in CROUCH})
        m.box(ft.name, (s * 2.75, 1.0, -0.5), (4.5, 2.0, 5.0), "foot")                 # wide flat foot
        for dx in (-1.5, 0.0, 1.5):                                                     # three thick digits
            x = s * 2.75 + dx
            m.box(ft.name, (x, 0.5, -3.75), (1.5, 1.0, 1.5), "foot")
            m.box(ft.name, (x, 0.5, -4.75), (1.0, 1.0, 0.5), "claw")                   # short claws
        m.box(ft.name, (s * 2.75, 0.75, 2.5), (2.0, 1.5, 1.0), "claw")                 # heel spur
        ft.locators[f"{p}_step"] = (s * 2.75, 0.2, -1.5)


# ----------------------------------------------------------------------------- trunk: a gaunt old body, pitched forward

def _trunk(m: Model) -> None:
    t = m.bone("trunk", "torso_g", (0.0, 12.0, 0.0))
    m.box(t.name, (0.0, 12.75, 0.25), (6.0, 3.5, 4.5), "skin")                       # pelvis
    m.box(t.name, (0.0, 15.5, 0.0), (5.0, 2.5, 4.0), "belly")                        # narrow old waist
    c = m.bone("chest", t.name, CHEST_PIVOT, (CHEST_PITCH, 0.0, 0.0))
    c.variant.update({v: ((0, 0, 0), (a, 0.0, 0.0)) for v, a in CHEST_POSE.items()})
    m.box(c.name, (0.0, 18.75, -0.25), (6.5, 4.5, 5.0), "ribs")                      # ribcage (the wound)
    m.box(c.name, (0.0, 22.25, -0.25), (7.5, 2.5, 5.5), "chest")                     # chest under heavy shoulders
    m.box(c.name, (0.0, 23.25, 3.0), (7.0, 4.5, 4.0), "skin")                        # the dorsal hump
    m.box(c.name, (0.0, 19.75, 2.5), (7.0, 3.5, 3.0), "skin")                        # upper back under the tergites
    m.box(c.name, (0.0, 24.25, 0.0), (4.0, 1.5, 3.0), "skin")                        # the base of the neck
    for s in (-1, 1):                                                                 # trapezius sloping to the shoulders
        cx = s * 3.25
        m.cube(c.name, (cx - 1.75, 22.75, -1.5), (3.5, 1.5, 4.0), "skin", pivot=(cx, 23.5, 0.5), rot=(0.0, 0.0, s * 24.0))
    c.locators["lure_c"] = (0.0, 18.0, -9.0)
    c.locators["back"] = (0.0, 23.0, 7.5)


# ----------------------------------------------------------------------------- seven broad, curved giant-isopod tergites

PLATES = [  # (bone, centre y, centre z, width, height, thickness, tilt rx, flange angle)
    ("chest", 26.25, 2.75, 6.5, 2.5, 1.5, 66.0, 0.0),
    ("chest", 24.75, 4.75, 9.5, 3.0, 1.5, 40.0, 40.0),
    ("chest", 22.5, 5.5, 11.5, 3.0, 1.5, 16.0, 48.0),
    ("chest", 20.0, 5.0, 11.5, 3.0, 1.5, 0.0, 52.0),       # the blade exits through this one
    ("chest", 17.5, 4.0, 10.0, 3.0, 1.5, -8.0, 52.0),
    ("trunk", 15.0, 2.5, 8.0, 3.0, 1.0, -10.0, 48.0),
    ("trunk", 12.75, 2.75, 7.0, 2.5, 1.0, -18.0, 0.0),
]
# bastion: the tergites slide together and over the nape (offset, extra tilt)
PLATE_BASTION = [((0, 1.0, -1.25), 14.0), ((0, 0.75, -0.5), 9.0), ((0, 0.25, 0.25), 4.0), ((0, 0, 0.5), 0.0),
                 ((0, 0.5, 0.75), -5.0), ((0, 1.0, 0.75), -9.0), ((0, 1.5, 0.75), -12.0)]


def _plates(m: Model) -> None:
    for k, (par, y, z, w, h, th, rx, fl) in enumerate(PLATES):
        b = m.bone(f"plate{k}", par, (0.0, y, z), (rx, 0.0, 0.0))
        off, extra = PLATE_BASTION[k]
        b.variant["bastion"] = (off, (rx + extra, 0.0, 0.0))
        b.variant["daybreak"] = ((0, 0.15 * k, 0.35), (rx - 10.0 + k * 1.5, 0.0, 0.0))
        m.box(b.name, (0.0, y, z), (w, h, th), "plate")
        m.box(b.name, (0.0, y + 0.25, z + th / 2 + 0.25), (1.5, h - 0.5, 0.5), "keel")          # raised spinal keel
        if fl:                                                                                    # curved flanks
            for s in (-1, 1):
                m.cube(b.name, (s * w / 2 - (1.5 if s < 0 else 0.0), y - h / 2 + 0.25, z - th / 2),
                       (1.5, h - 0.5, th), "plate", pivot=(s * w / 2, y, z), rot=(0.0, -s * fl, 0.0))
        if 1 <= k <= 3:                                                                           # a stepped dorsal ridge
            sz = {1: (1.0, 2.5, 1.5), 2: (1.0, 2.0, 1.5), 3: (1.0, 1.5, 1.0)}[k]
            m.cube(b.name, (-0.5, y + h / 2 - 0.75, z + th / 2), sz, "spine",
                   pivot=(0.0, y + h / 2 - 0.75, z + th / 2), rot=(-38.0, 0.0, 0.0))
        # bastion: thin seams of white-gold light leak between the closing tergites
        m.box(b.name, (0.0, y - h / 2 + 0.25, z - 0.25), (w - 1.5, 0.5, th), "seam", only={"bastion"})


# ----------------------------------------------------------------------------- torn fins

def _fins(m: Model) -> None:
    for s, p in ((-1, "r"), (1, "l")):
        f = m.bone(f"{p}_fin", "chest", (s * 4.25, 22.75, 3.75), (-4.0, s * 26.0, 0.0))
        f.variant.update({"daybreak": ((0, 0, 0), (-16.0, s * 52.0, 0.0)), "bastion": ((0, 0, 0), (8.0, s * 10.0, 0.0)),
                          "maw": ((0, 0, 0), (-18.0, s * 20.0, 0.0))})
        m.box(f.name, (s * 4.25, 18.25, 6.25), (0.0, 9.0, 5.0), "fin", cutout=True)


# ----------------------------------------------------------------------------- the sun through his heart

def sword_parts(m: Model, bone: str, base, flat: str = "z", tip: float = 25.75, blade_from: float = 3.75,
                ricasso: bool = True, **kw) -> None:
    """The sword's design, shared by the embedded and the held sword.  Local frame: grip centre
    at `base`, blade along +Y; `flat` names the axis the broad faces point along (the blade's
    width runs along the other horizontal axis)."""
    bx, by, bz = base

    def box(cy, w, h, t, mat, rot=None):
        size = (w, h, t) if flat == "z" else (t, h, w)
        c = (bx, by + cy, bz)
        o = tuple(c[i] - size[i] / 2 for i in range(3))
        if rot is None:
            return m.cube(bone, o, size, mat, **kw)
        r = (0.0, 0.0, rot) if flat == "z" else (rot, 0.0, 0.0)
        return m.cube(bone, o, size, mat, pivot=c, rot=r, **kw)

    box(-2.75, 1.5, 1.5, 1.5, "s_pommel")                # pommel: a small sun
    box(-2.0, 2.0, 0.5, 1.0, "s_hilt")                   # collar
    box(0.0, 1.0, 3.5, 1.0, "s_grip")                    # wrapped grip
    box(2.5, 7.0, 1.0, 0.5, "s_hilt")                    # the guard's horizontal rays
    box(2.5, 4.5, 0.5, 0.5, "s_hilt", rot=45.0)          # diagonal rays
    box(2.5, 4.5, 0.5, 0.5, "s_hilt", rot=-45.0)
    box(2.5, 2.5, 2.5, 1.0, "s_sun")                     # the sun disc at the heart of the guard
    if ricasso:
        box(blade_from + 0.75, 2.5, 1.5, 0.75, "s_ricasso")
    main = tip - 1.5 - blade_from
    box(blade_from + main / 2, 2.5, main, 0.5, "s_blade")
    box(tip - 1.0, 1.5, 1.0, 0.5, "s_blade")
    box(tip - 0.25, 0.5, 0.5, 0.5, "s_blade")


def _sword(m: Model) -> None:
    sw = m.bone("sword", "chest", ENTRY, SWORD_ROT)
    ex, ey, ez = ENTRY
    sword_parts(m, sw.name, (ex, ey - GUARD_Y, ez), flat="x", tip=GUARD_Y + TIP_T, blade_from=GUARD_Y + EXIT_T - 0.75,
                ricasso=False, skip=NO_SWORD)


def _core(m: Model) -> None:
    """The light shells at both wounds: scaled on a heart-rate rhythm by the animations."""
    cf = m.bone("core_f", "chest", ENTRY)
    x, y, z = ENTRY
    m.box(cf.name, (x, y, z - 0.25), (3.5, 1.5, 0.5), "core")                      # a cross of light: it reads round
    m.box(cf.name, (x, y, z - 0.375), (1.5, 3.5, 0.75), "core")                    # when it swells with each beat
    m.box(cf.name, (x, y, z - 0.5), (1.0, 1.0, 1.0), "core_hot")
    cf.locators["wound"] = (x, y, z - 0.5)
    cb = m.bone("core_b", "chest", EXIT, (PLATES[3][6], 0.0, 0.0))
    ex, ey, ez = EXIT
    m.box(cb.name, (ex, ey, ez + 0.125), (3.0, 1.0, 0.25), "core")
    m.box(cb.name, (ex, ey, ez + 0.25), (1.0, 3.0, 0.5), "core")
    cb.locators["wound_back"] = (ex, ey, ez + 0.5)


# ----------------------------------------------------------------------------- long arms: uneven segmented shoulders, webbed hard-tipped hands

FINGER_Z = (-1.25, -0.25, 0.75)
FINGER_FAN = (-12.0, 0.0, 12.0)


def _arms(m: Model) -> None:
    dz = ARM_DZ
    for s, g, p in ((-1, "r_arm_g", "r"), (1, "l_arm_g", "l")):
        lift = 0.75 if s < 0 else -0.5                       # heavy, uneven shoulders: the right rides higher
        pa = m.bone(f"{p}_pauldron", g, (s * 5.0, 23.0 + lift, dz))
        pa.variant.update({"bastion": ((-s * 0.75, 0.75, 0.0), side_rot((0, 0, 8), s)),
                           "unshackled": ((0, 0.5, -0.25), None), "daybreak": ((0, 0.75, 0), side_rot((0, 0, -12), s))})
        plates = [(5.5, 23.5, 3.5, 1.0, 4.0, 20.0), (7.0, 22.25, 2.5, 1.0, 3.5, 56.0)]
        if s < 0:
            plates.insert(0, (4.75, 24.25, 2.5, 1.0, 3.5, 10.0))          # the heavier right shoulder
        for (cx, cy, w, h, d, a) in plates:
            c = (s * cx, cy + lift, dz)
            m.cube(pa.name, (c[0] - w / 2, c[1] - h / 2, c[2] - d / 2), (w, h, d), "shoulder", pivot=c, rot=(0.0, 0.0, s * a))
        m.box(g, (s * 5.75, 21.25 + lift * 0.5, dz), (3.0, 3.0, 3.5), "skin")           # rounded deltoid
        up = m.bone(f"{p}_upper", g, (s * 5.5, 22.0, dz), side_rot((0.0, 0.0, 7.0), s))
        m.box(up.name, (s * 6.25, 18.75, dz), (2.5, 6.0, 2.5), "skin")
        fo = m.bone(f"{p}_fore", up.name, (s * 6.25, 16.0, 0.25 + dz), side_rot((-8.0, 0.0, -11.0), s))
        m.box(fo.name, (s * 6.25, 13.75, dz), (3.0, 4.5, 3.5), "forearm")                # powerful forearm, shelled outside
        m.box(fo.name, (s * 6.25, 16.0, 1.25 + dz), (2.5, 1.5, 1.5), "knee")             # elbow plate
        m.box(fo.name, (s * 6.25, 13.75, 2.75 + dz), (0.0, 4.0, 2.5), "fin", cutout=True)  # forearm fin
        hz = -0.25 + dz
        hd = m.bone(f"{p}_hand", fo.name, (s * 6.25, 11.5, hz))
        m.box(hd.name, (s * 6.25, 10.25, hz), (2.5, 2.5, 3.0), "skin")                   # palm
        m.box(hd.name, (s * 6.5, 7.75, hz), (0.0, 2.5, 3.0), "web", cutout=True)         # webbing between the fingers
        for k, (fz, fan) in enumerate(zip(FINGER_Z, FINGER_FAN)):
            f = m.bone(f"{p}_finger{k}", hd.name, (s * 6.5, 9.0, fz + dz), (fan, 0.0, 0.0))
            m.box(f.name, (s * 6.5, 7.25, fz + dz), (1.0, 3.5, 1.0), "skin")
            m.box(f.name, (s * 6.5, 5.0, fz + dz), (1.0, 1.0, 1.0), "claw")              # hardened tip
        th = m.bone(f"{p}_thumb", hd.name, (s * 5.5, 10.75, -1.5 + dz), side_rot((-10.0, 0.0, -18.0), s))
        m.box(th.name, (s * 5.5, 9.5, -1.5 + dz), (1.0, 2.5, 1.0), "skin")
        hd.locators[f"{p}_claws"] = (s * 6.5, 5.0, hz)


# ----------------------------------------------------------------------------- the head: long, old, predatory

def _head(m: Model) -> None:
    sk = m.bone("skull", "head_g", (0.0, 22.0, -2.5))
    sk.variant.update({"unshackled": ((0, -1.0, -0.75), (6.0, 0, 0)), "daybreak": ((0, 0.5, 0.75), (-18.0, 0, 0)),
                       "bastion": ((0, -1.0, 1.0), (12.0, 0, 0)), "maw": ((0, -0.25, -0.75), (-4.0, 0, 0)),
                       "lure": ((0, 0.25, 0.5), (-6.0, 0, 4.0))})
    m.box(sk.name, (0.0, 21.5, -2.0), (3.5, 2.5, 3.5), "neck")                       # sinewy neck out of the hump
    m.box(sk.name, (0.0, 21.75, -5.25), (4.0, 2.0, 3.0), "jowl")                     # sagging jowls, jaw muscles
    m.box(sk.name, (0.0, 24.75, -5.25), (4.5, 3.5, 4.5), "head")                     # the bald old skull
    m.box(sk.name, (0.0, 26.75, -4.75), (3.5, 0.5, 3.5), "head")                     # crown
    m.box(sk.name, (0.0, 25.0, -2.25), (3.5, 2.5, 1.5), "head")                    # occiput
    m.box(sk.name, (0.0, 23.5, -9.0), (3.0, 1.0, 3.0), "snout")                      # flat goblin-shark snout
    m.box(sk.name, (0.0, 23.25, -11.0), (2.0, 0.5, 1.0), "snout")                    # its tip
    for s, p in ((-1, "r"), (1, "l")):
        br = m.bone(f"brow_{p}", sk.name, (s * 1.25, 26.0, -7.5), side_rot((0.0, 0.0, 10.0), s))
        br.variant.update({"unshackled": ((0, -0.25, 0), side_rot((0.0, 0.0, 18.0), s)),
                           "lure": ((0, -0.25, 0), side_rot((0.0, 0.0, 20.0), s)),
                           "daybreak": ((0, 0.25, 0), side_rot((0.0, 0.0, -6.0), s))})
        m.box(br.name, (s * 1.25, 26.0, -7.5), (2.5, 1.0, 1.0), "brow")
        lid = m.bone(f"lid_{p}", sk.name, (s * 1.0, 25.5, -7.625))
        m.cube(lid.name, (s * 1.0 - 0.875, 25.0, -7.75), (1.75, 0.5, 0.25), "lid")
        for k in range(3):                                                            # gill flaps along the neck
            z0 = -3.25 + k * 0.875
            gl = m.bone(f"gill_{p}{k}", sk.name, (s * 1.875, 21.75, z0))
            m.cube(gl.name, (s * 1.875 - 0.125, 20.5, z0), (0.25, 2.25, 0.75), "gill")
    mw = m.bone("jaws", sk.name, (0.0, 22.25, -6.5))
    mw.variant["maw"] = ((0.0, -0.75, -5.5), None)
    m.box(mw.name, (0.0, 22.75, -9.0), (3.0, 0.5, 2.5), "lip")                       # upper jaw under the snout
    m.box(mw.name, (0.0, 21.75, -9.0), (2.5, 1.5, 2.0), "teeth_u", cutout=True)      # needle teeth (upper row)
    m.box(mw.name, (0.0, 21.75, -6.25), (2.5, 1.5, 6.5), "gum")                      # the protrusible sling
    jw = m.bone("jaw", mw.name, (0.0, 21.75, -6.75))
    jw.variant.update({"maw": ((0, 0, 0), (38.0, 0.0, 0.0)), "daybreak": ((0, 0, 0), (12.0, 0.0, 0.0))})
    m.box(jw.name, (0.0, 20.5, -8.75), (3.5, 1.0, 4.0), "jaw")                       # underbite
    m.box(jw.name, (0.0, 21.75, -9.25), (3.0, 1.5, 2.5), "teeth_l", cutout=True)     # needle teeth (lower row)
    for s in (-1, 1):
        m.box(jw.name, (s * 0.75, 19.25, -9.75), (0.5, 1.5, 0.5), "barbel")          # a scraggly pair of barbels
    jw.locators["maw"] = (0.0, 21.25, -11.0)
    sk.locators["eyes"] = (0.0, 25.0, -8.25)
    sk.locators["gills"] = (0.0, 21.0, -2.25)


# ============================================================================= materials

def materials():
    mats = {
        "skin": mat_skin, "belly": mat_belly, "ribs": mat_ribs, "chest": mat_chest, "neck": mat_neck,
        "jowl": mat_jowl, "head": mat_head, "snout": mat_snout, "brow": mat_brow, "lid": mat_lid, "lip": mat_lip,
        "gum": mat_gum, "jaw": mat_jaw, "teeth_u": mat_teeth_u, "teeth_l": mat_teeth_l, "barbel": mat_barbel,
        "gill": mat_gill, "plate": mat_plate, "keel": mat_keel, "spine": mat_spine, "seam": mat_seam,
        "shoulder": mat_shoulder, "forearm": mat_forearm, "shin": mat_shin, "knee": mat_knee, "foot": mat_foot,
        "claw": mat_claw, "fin": mat_fin, "web": mat_web, "core": mat_core, "core_hot": mat_core_hot,
        "accent": mat_accent,
    }
    mats.update(sword_materials())
    return mats


def _P(ctx):
    p = ctx.params
    return p.get("blaze", 0.0), p.get("open", 0.0), p.get("day", 0.0)


def _wp(ctx):
    return ctx.wp if ctx.wp is not None else ctx.p


def _wn(ctx):
    return ctx.wn if ctx.wn is not None else ctx.n


def _h2(ix, iy, seed):
    v = np.sin(ix * 12.9898 + iy * 78.233 + seed * 37.719) * 43758.5453
    return v - np.floor(v)


def _qpos(ctx):
    """World positions snapped to the texel grid (consistent between the two faces of a plane)."""
    return np.floor(_wp(ctx) * 2.0 + 0.01)


# ----------------------------------------------------------------------------- light from the sword

@lru_cache(maxsize=None)
def _sources(open_: bool):
    if open_:
        src = [(along(-0.6), 7.0, 1.25), (along(EXIT_T + 0.5), 5.0, 0.9)]
    else:
        src = [(along(HILT_T), 6.0, 1.0), (along(-0.4), 5.0, 0.9), (along(EXIT_T + 0.5), 5.0, 0.8)]
        src += [(along(t), 4.0, 0.5) for t in (11.5, 15.0, 18.5)]
    return tuple((tuple(chest_world(c)), R, s) for c, R, s in src)


def sun_light(ctx, reach: float = 1.0) -> np.ndarray:
    """0..1: how much of the sword's (or the open wound's) warm light falls on each texel."""
    blaze, open_, day = _P(ctx)
    p = _wp(ctx)
    n = _wn(ctx)
    out = np.zeros(ctx.N)
    for c, R, s in _sources(bool(open_)):
        R = R * (1.0 + 0.45 * blaze) * reach
        d = np.array(c)[None, :] - p
        dist = np.maximum(np.linalg.norm(d, axis=1), 1e-6)
        facing = np.clip((d @ n) / dist + 0.3, 0, 1)
        out += s * (1.0 + 0.7 * blaze) * np.clip(1 - dist / R, 0, 1) ** 2 * facing
    return np.clip(out, 0, 1)


def warm(ctx, rgb, lv, amount=1.0, reach=1.0, cap=1.0):
    """The sword's light on dark skin: warm palette steps with an ordered-dither edge."""
    blaze, open_, day = _P(ctx)
    I = np.minimum(sun_light(ctx, reach) * amount, cap)
    ix, iy, W, H = px.texel(ctx)
    th = px.BAYER4[iy % 4, ix % 4]
    lit = I * 1.35 > 0.2 + th * 0.4
    c_lit = px.quant(ctx, LIT, np.clip(lv * 0.5 + I * 0.95 - 0.08, 0, 1))
    out = np.where(lit[:, None], c_lit, rgb)
    glow = np.where(lit & (I > 0.55), 0.18 * blaze + 0.12 * day, 0.0)
    return out, glow


# ----------------------------------------------------------------------------- fractures and veins

def _seg_dist(p2, a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((p2 - a) @ ab) / max(float(ab @ ab), 1e-9), 0, 1)
    return np.linalg.norm(p2 - (a + t[:, None] * ab), axis=1)


# chest cracks in the chest frame's front plane (u, y): u = x on the front, unwrapped around the flanks
CRACKS_F = [
    [(0.0, 18.0), (-0.75, 18.75), (-1.0, 19.75), (-0.5, 20.5), (-0.75, 21.25)],               # up the sternum
    [(0.0, 18.0), (-1.25, 18.25), (-2.25, 18.0), (-3.25, 17.5), (-4.5, 17.0), (-5.75, 16.75)],    # along a rib (right)
    [(0.0, 18.0), (1.25, 18.5), (2.25, 18.25), (3.25, 17.75), (4.5, 17.25), (6.0, 17.0)],    # along a rib (left)
    [(-1.0, 19.75), (-2.0, 20.0), (-3.0, 19.75), (-4.25, 19.25), (-5.25, 19.0)],             # the rib above (right)
    [(0.5, 18.75), (1.5, 19.5), (2.5, 20.0), (3.5, 19.75), (4.75, 19.5)],                    # the rib above (left)
    [(0.0, 18.0), (-0.75, 17.0), (-1.5, 16.5)],                                               # down toward the belly
    [(0.0, 18.0), (0.5, 17.0), (1.25, 16.5)],
]
CRACKS_F_MORE = [
    [(-0.75, 21.25), (-1.75, 22.0), (-3.0, 22.5)],
    [(-0.5, 20.5), (0.75, 21.5), (2.25, 22.25)],
    [(-5.75, 16.75), (-7.0, 16.25)],
    [(6.0, 17.0), (7.25, 16.5)],
]
CRACKS_F_DAY = [
    [(-3.0, 22.5), (-4.0, 23.5), (-5.25, 24.0)],
    [(2.25, 22.25), (3.5, 23.0), (4.5, 24.0)],
    [(-1.5, 16.5), (-2.5, 15.25), (-2.25, 14.0), (-3.0, 12.75)],
    [(1.25, 16.5), (2.0, 15.0), (1.5, 13.75), (2.25, 12.5)],
    [(-5.25, 19.0), (-6.5, 19.75), (-7.75, 20.0)],
    [(4.75, 19.5), (6.0, 20.25), (7.25, 20.25)],
]
# cracks around the exit on the back: offsets from the exit in the chest frame's (x, y), seen from behind
CRACKS_B = [
    [(0.0, 0.0), (-1.0, 0.75), (-2.0, 1.25), (-3.25, 1.5), (-4.5, 2.25), (-5.5, 2.5)],
    [(0.0, 0.0), (1.25, 0.5), (2.25, 0.25), (3.5, 0.75), (4.25, 1.5)],
    [(0.0, 0.0), (-0.75, -1.0), (-1.75, -1.75), (-2.5, -2.75), (-3.0, -3.75)],
    [(0.0, 0.0), (0.75, -1.0), (1.5, -2.25), (1.25, -3.25)],
    [(0.0, 0.0), (0.25, 1.25), (-0.25, 2.5), (0.5, 3.5), (0.25, 4.5)],
]
CRACKS_B = [[(EXIT[0] + a, EXIT[1] + b) for a, b in pl] for pl in CRACKS_B]


def _to_chest(p):
    """World rest positions back into the upright chest frame."""
    piv = np.array(CHEST_PIVOT)
    R = rot_matrix((CHEST_PITCH, 0.0, 0.0))
    return (p - piv) @ R + piv


def _unwrap(ctx):
    """(u, y) on the trunk surface for the chest cracks (chest frame): front faces use x; side
    faces continue around the flank (|u| grows as you go back)."""
    p = _to_chest(_wp(ctx))
    n = rot_matrix((CHEST_PITCH, 0, 0)).T @ _wn(ctx)
    if abs(n[0]) > 0.5:
        u = np.sign(n[0]) * (np.abs(p[:, 0]) + (p[:, 2] - ENTRY[2]))
    else:
        u = p[:, 0]
    return np.stack([u, p[:, 1]], axis=1), n


def _polyline_dist(q, sets):
    best = np.full(len(q), 9.0)
    for pl in sets:
        for a, b in zip(pl[:-1], pl[1:]):
            best = np.minimum(best, _seg_dist(q, a, b))
    return best


def kintsugi(ctx):
    """Daybreak: light-filled fracture lines running along about half of the larger faces (a
    jagged line down the face's long axis), fading out far from the heart."""
    ix, iy, W, H = px.texel(ctx)
    pick = _h2(np.array([ctx.seed]), np.array([len(ctx.face) * 7]), 23)[0]
    if min(W, H) < 4 or W * H < 30 or pick > 0.5 or not px.side(ctx):
        return np.zeros(ctx.N, bool)
    a, b, La, Lb = (ix, iy, W, H) if H >= W else (iy, ix, H, W)
    c0 = int(_h2(np.array([ctx.seed]), np.array([len(ctx.face)]), 21)[0] * (La - 2)) + 1
    wob = ((b // 3) % 2) * (1 if c0 < La - 2 else -1)
    line = a == c0 + wob
    heart = np.linalg.norm(_wp(ctx) - np.array(chest_world(ENTRY)), axis=1)
    keep = heart < 26.0 - 6.0 * _h2(np.array([ctx.seed]), np.array([9]), 4)[0]
    return line & keep & (b > 0) & (b < Lb - 1)


# ----------------------------------------------------------------------------- the skin

def skin_level(ctx, offset=0.0, grad=0.16, rim_up=0.26, rim_down=0.05, rough=0.035, proxy=None):
    ix, iy, W, H = px.texel(ctx)
    if proxy is not None:
        lv = px.proxy(ctx, proxy[0], proxy[1], proxy[2] if len(proxy) > 2 else 0.8)
        if px.side(ctx) and H > 1:
            lv = lv + grad * (0.5 - iy / (H - 1))
    else:
        lv = px.light(ctx, grad=grad)
    lv = lv - 0.2 + offset
    if px.side(ctx) and H >= 3:
        lv = lv + rim_up * (iy == 0) - rim_down * (iy == H - 1)
        if rough:
            s = ctx.seed
            pit = _h2(ix, iy, s) < rough
            bump = (_h2(ix, iy + 1, s) < rough) & ~pit & (iy > 0)
            lv = lv - 0.12 * pit + 0.09 * bump
    elif ctx.face == "up" and min(W, H) >= 3:
        lv = lv - 0.08 + rim_up * 0.5 * px.border(ctx, 1)
    elif ctx.face == "up":
        lv = lv - 0.08
    return lv


def skin_paint(ctx, lv, pal=SKIN, sheen=True, light=1.0, reach=1.0, cap=1.0):
    """Quantise onto the skin ramp, then wet runs, rare reflections, the sword's light and the
    daybreak veins.  Returns (rgb, glow)."""
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    if day > 0.5 and pal is SKIN:
        pal = DAYSKIN
    c = px.quant(ctx, pal, lv)
    if sheen and px.side(ctx) and H >= 5 and W >= 4:
        # controlled wet highlights: a short run of sheen down from the rim, and one green-grey
        # reflection streak on larger faces
        col_h = _h2(ix, 0, ctx.seed + 5)
        run = (col_h < 0.12) & (iy >= 1) & (iy <= 2)
        c = np.where(run[:, None], px.quant(ctx, pal, lv + 0.12), c)
        if W >= 6 and H >= 6:
            sx = int(_h2(np.array([ctx.seed]), np.array([1]), 11)[0] * (W - 3)) + 1
            sy = int(_h2(np.array([ctx.seed]), np.array([2]), 13)[0] * (H - 4)) + 2
            streak = (iy == sy) & (ix >= sx) & (ix < sx + 2)
            c = np.where(streak[:, None], REFLECT, c)
        spec = (iy == 0) & (_h2(ix, 1, ctx.seed + 3) < 0.05)
        c = np.where(spec[:, None], WET, c)
    glow = np.zeros(ctx.N)
    if light:
        c, glow = warm(ctx, c, lv, light, reach, cap)
    if day > 0.5:
        v = kintsugi(ctx)
        c = np.where(v[:, None], px.quant(ctx, SUN, 0.5 + 0.3 * (iy % 4 == 0)), c)
        glow = np.where(v, 0.8, glow)
    return c, glow


def mat_skin(ctx):
    c, g = skin_paint(ctx, skin_level(ctx))
    return c, ctx.ones(), g


def mat_belly(ctx):
    """The gaunt waist: ribbed shadow lines below the ribcage."""
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, offset=-0.02)
    if ctx.face == "north":
        lv = lv - 0.1 * ((iy % 2) == 1) * (np.abs(ix - (W - 1) / 2) < W / 2 - 1)
    c, g = skin_paint(ctx, lv)
    return _cracked(ctx, c, g)


def _cracked(ctx, c, g):
    """White-gold fractures on the trunk's front and flanks; charred tissue round the entry wound."""
    blaze, open_, day = _P(ctx)
    q, n = _unwrap(ctx)
    if n[2] > 0.5 or n[1] < -0.5:
        return c, ctx.ones(), g
    sets = CRACKS_F + (CRACKS_F_MORE if (blaze or open_ or day) else []) + (CRACKS_F_DAY if day else [])
    on = _polyline_dist(q, sets) < 0.3
    r = np.hypot(q[:, 0] - ENTRY[0], q[:, 1] - ENTRY[1])
    if n[2] < -0.5:
        ix, iy, W, H = px.texel(ctx)
        char = r < 1.75 + 0.3 * px.BAYER4[iy % 4, ix % 4]
        c = np.where(char[:, None], px.quant(ctx, EMBER, 0.25 + 0.35 * (r < 1.75)), c)
        g = np.where(char, 0.0, g)
    hot = np.clip(1.0 - r / 7.0, 0, 1)
    c = np.where(on[:, None], px.quant(ctx, SUN, np.clip(0.25 + 0.75 * hot + 0.2 * blaze, 0, 1)), c)
    g = np.where(on, np.clip(0.5 + 0.45 * hot + 0.2 * blaze, 0, 1), g)
    return c, ctx.ones(), g


def mat_ribs(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, proxy=(tuple(chest_world((0, 18.75, 0.5))), (4.0, 4.0, 3.5), 0.7))
    if ctx.face in ("north", "east", "west"):
        lv = lv - 0.11 * ((iy % 3) == 2)                                          # ribs under the skin
    c, g = skin_paint(ctx, lv)
    if ctx.face in ("east", "west") and H >= 6:                                     # a lateral line of photophores
        blaze, open_, day = _P(ctx)
        dots = (iy == 3) & ((ix % 3) == 1)
        c = np.where(dots[:, None], DAYGOLD if day else PHOTO_DIM, c)
        g = np.where(dots, 0.4, g)
    return _cracked(ctx, c, g)


def mat_chest(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, proxy=(tuple(chest_world((0, 22.0, 0.5))), (5.0, 3.0, 3.5), 0.7))
    if ctx.face == "north":
        lv = lv - 0.12 * (np.abs(ix - (W - 1) / 2) < 0.6)                        # sternum furrow
    c, g = skin_paint(ctx, lv)
    return _cracked(ctx, c, g)


def mat_neck(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, offset=-0.03, rough=0.04)
    if px.side(ctx):
        lv = lv - 0.1 * ((ix % 3) == 1)                                            # sinews
    c, g = skin_paint(ctx, lv, light=0.5, reach=1.8, cap=0.4)
    return c, ctx.ones(), g


def mat_jowl(ctx):
    """Sagging jowls; the gill slits behind them show as dark red lines."""
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, offset=-0.02, rough=0.05, proxy=((0, 25.0, -5.25), (2.5, 2.5, 2.5), 0.7))
    if px.side(ctx):
        lv = lv - 0.12 * (iy == H - 2)                                             # the fold of a jowl
    c, g = skin_paint(ctx, lv, light=0.55, reach=2.4, cap=0.42)
    return c, ctx.ones(), g


# the face, painted on the skull's front (9 x 7 texels)
FACE = [
    "w.hh.hh.w",
    ".........",
    "sWEEsEEWs",
    "seEPsPEes",
    ".bbnhnbb.",
    ".........",
    ".........",
]


def mat_head(ctx):
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, rough=0.05, proxy=((0, 27.25, -5.0), (2.6, 2.4, 3.4), 0.85))
    if ctx.face in ("east", "west") and H >= 6:
        lv = lv - 0.11 * ((iy % 3 == 1) & ((ix + iy) % 5 < 3))                   # deep old wrinkles
    c, g = skin_paint(ctx, lv, light=0.55, reach=2.4, cap=0.42)
    if ctx.face == "north" and W == 9 and H == 7:
        eye = "#fff0a8" if day else ("#efe39a" if open_ else "#ddd08a")
        colors = {"w": "#020304", "h": "#1c2a2c", "s": "#000000", "E": eye, "e": "#a39558", "P": "#050302",
                  "b": "#010203", "n": "#000000", "W": "#fffbe0"}
        gl = 0.75 if day else (0.4 if open_ else 0.25)
        c, g = px.decal(ctx, c, FACE, colors, 0, 0, glow=g, glow_chars="EeW", glow_level=gl)
    if ctx.face == "up" and W >= 7 and H >= 7:
        # the atrophied light organ of an anglerfish: three cold dots along the crown
        dots = (ix == W // 2) & ((iy % 3) == 1)
        c = np.where(dots[:, None], DAYGOLD if day else PHOTO, c)
        g = np.where(dots, 0.5, g)
    return c, ctx.ones(), g


def mat_snout(ctx):
    """The goblin-shark rostrum: flat, slick on top, dotted with electro-sensing pores."""
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, offset=0.05, rough=0.0, rim_up=0.3)
    c, g = skin_paint(ctx, lv, sheen=False, light=0.55, reach=2.4, cap=0.42)
    if ctx.face == "up":
        pores = ((ix + 2 * iy) % 4 == 1) & (ix > 0) & (ix < W - 1)
        c = np.where(pores[:, None], SKIN[1], c)
        c = np.where(((iy == H - 1) | (ix == 0) | (ix == W - 1))[:, None] & (_h2(ix, iy, 4) < 0.5)[:, None], WET, c)
    if ctx.face == "down":
        c = np.full_like(c, SKIN[1])
    return c, ctx.ones(), g


def mat_brow(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, rim_up=0.34, rough=0.0)
    if ctx.face == "north":
        lv = lv - 0.1 * (iy == H - 1)
        c, g = skin_paint(ctx, lv, light=0.55, reach=2.4, cap=0.42)
        hair = (iy == H - 1) & (((ix + iy) % 2 == 0) | (_h2(ix, 0, 31) < 0.4))
        c = np.where(hair[:, None], WISP[1], c)
        c = np.where(((iy == H - 1) & (ix % 3 == 1))[:, None], WISP[2], c)
        return c, ctx.ones(), g
    if ctx.face in ("east", "west") and H >= 2:
        c, g = skin_paint(ctx, lv, light=0.55, reach=2.4, cap=0.42)
        c = np.where(((iy == H - 1) & (ix % 2 == 0))[:, None], WISP[1], c)
        return c, ctx.ones(), g
    c, g = skin_paint(ctx, lv, light=0.55, reach=2.4, cap=0.42)
    return c, ctx.ones(), g


LIDSKIN = px.pal("#0b0f0f", "#1f2725", "#2f3a36", "#43514b")


def mat_lid(ctx):
    """Heavy, puffy lids: lighter, older skin than the dark sockets, a dark lash line below."""
    ix, iy, W, H = px.texel(ctx)
    c = np.broadcast_to(LIDSKIN[2], (ctx.N, 3)).copy()
    if ctx.face == "up":
        c = np.broadcast_to(LIDSKIN[3], (ctx.N, 3)).copy()
    elif ctx.face == "down":
        c = np.broadcast_to(LIDSKIN[0], (ctx.N, 3)).copy()
    return c, ctx.ones(), ctx.zeros()


def mat_lip(ctx):
    if ctx.face == "down":                                                              # the roof of the mouth
        return px.quant(ctx, GILL, px.light(ctx) - 0.15), ctx.ones(), ctx.zeros()
    lv = skin_level(ctx, rim_up=0.15, rough=0.0, offset=-0.04)
    c, g = skin_paint(ctx, lv, sheen=False, light=0.55, reach=2.4, cap=0.42)
    return c, ctx.ones(), g


def mat_gum(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = px.shade(ctx, GILL, offset=-0.3)
    ridge = (ix % 2 == 0) & px.side(ctx)
    c = np.where(ridge[:, None], GILL[0], c)
    return c, ctx.ones(), ctx.zeros()


def mat_jaw(ctx):
    ix, iy, W, H = px.texel(ctx)
    if ctx.face == "up":
        return px.quant(ctx, GILL, px.light(ctx) - 0.3), ctx.ones(), ctx.zeros()
    lv = skin_level(ctx, rough=0.04, rim_up=0.18)
    c, g = skin_paint(ctx, lv, light=0.55, reach=2.4, cap=0.42)
    return c, ctx.ones(), g


def _teeth(ctx, hang: bool):
    """Irregular rows of needle teeth (cutout): needles of 1-2 texels with gaps between."""
    ix, iy, W, H = px.texel(ctx)
    if not px.side(ctx):
        return np.broadcast_to(BONE[2], (ctx.N, 3)).copy(), ctx.zeros(), ctx.zeros()
    q = _qpos(ctx)
    col = (q[:, 0] + q[:, 2]).astype(int)
    hv = _h2(col, 0, 3 if hang else 7)
    tooth = ((col % 2) == 0) & (hv < 0.72)
    long_ = hv < 0.45
    root_row = iy if hang else (H - 1 - iy)
    a = tooth & ((root_row == 0) | long_)
    c = np.where((root_row == 0)[:, None], BONE[2], BONE[3])
    c = np.where(((root_row == H - 1) & long_)[:, None], BONE[4], c)
    return c, a.astype(float), ctx.zeros()


def mat_teeth_u(ctx):
    return _teeth(ctx, True)


def mat_teeth_l(ctx):
    return _teeth(ctx, False)


def mat_barbel(ctx):
    ix, iy, W, H = px.texel(ctx)
    blaze, open_, day = _P(ctx)
    c = px.shade(ctx, WISP, offset=-0.1)
    tip = iy >= H - 1
    c = np.where(tip[:, None], DAYGOLD if day else PHOTO, c)
    return c, ctx.ones(), np.where(tip, 0.6, 0.0)


def mat_gill(ctx):
    """Outside: skin with a pale trailing rim; inside (toward the neck): red filaments."""
    ix, iy, W, H = px.texel(ctx)
    p = _wp(ctx)
    n = _wn(ctx)
    inner = abs(n[0]) > 0.5 and np.sign(n[0]) != np.sign(p[:, 0].mean())
    if inner:
        c = px.quant(ctx, GILL, px.light(ctx) + 0.12 * ((iy % 2) == 0))
        return c, ctx.ones(), ctx.zeros()
    c = px.shade(ctx, SKIN, offset=-0.05)
    if px.side(ctx) and W >= 2:
        c = np.where(((ix == W - 1) if ctx.face == "west" else (ix == 0))[:, None], SKIN[6], c)
    return c, ctx.ones(), ctx.zeros()


# ----------------------------------------------------------------------------- isopod chitin

def chitin(ctx, rim=0.55, bands=True, photo=0, offset=0.0):
    """Glossy black chitin: a bright wet rim along the upper edge with a few specular texels,
    a darker trailing edge, faint growth lines; optional photophores along the trailing edge."""
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx, grad=0.12) - 0.16 + offset
    if px.side(ctx) and H >= 3:
        crest = np.abs(ix - (W - 1) / 2) <= (W - 1) / 2 * 0.8
        lv = lv + rim * (iy == 0) * crest + 0.1 * (iy == 0) * ~crest + 0.18 * (iy == 1) + 0.05 * (iy == 2) - 0.1 * (iy == H - 1)
        if bands and H >= 5:
            lv = lv - 0.06 * ((iy % 2) == 0) * (iy > 1) * (iy < H - 1)
    elif ctx.face == "up":
        lv = lv - 0.12 + 0.3 * px.border(ctx, 1, ("b",))
    c = px.quant(ctx, CHITIN, lv)
    g = ctx.zeros()
    if px.side(ctx) and H >= 3 and W >= 8:                          # one short glint along the crest of big plates
        sx = int(_h2(np.array([ctx.seed]), np.array([0]), 5)[0] * (W - 4)) + 2
        spec = (iy == 0) & ((ix == sx) | (ix == sx + 1))
        c = np.where(spec[:, None], SPEC, c)
    if day > 0.5 and px.side(ctx) and H >= 3:
        crest_ = (iy == 0) & (np.abs(ix - (W - 1) / 2) <= (W - 1) / 2 * 0.8)
        c = np.where(crest_[:, None], SUN[2], c)
        g = np.where(crest_, 0.5, g)
    if day > 0.5 and ctx.face == "south" and H >= 4:
        leak = iy == H - 1
        c = np.where(leak[:, None], SUN[3], c)
        g = np.where(leak, 0.85, g)
    if photo and px.side(ctx) and H >= 4 and W >= 6:
        dots = (iy == H - 2) & (((ix + ctx.seed) % photo) == 0) & (ix > 0) & (ix < W - 1)
        c = np.where(dots[:, None], DAYGOLD if day else PHOTO, c)
        g = np.where(dots, 0.7 if day else 0.45, g)
    return lv, c, g


def mat_plate(ctx):
    """A tergite; white-gold cracks and charred chitin around the exit wound."""
    ix, iy, W, H = px.texel(ctx)
    lv, c, g = chitin(ctx, photo=9 if (ctx.face == "south" and W >= 18) else 0)
    c, gl = warm(ctx, c, lv, 0.8)
    g = np.maximum(g, gl)
    n = rot_matrix((CHEST_PITCH, 0, 0)).T @ _wn(ctx)
    if n[2] > 0.3:
        p = _to_chest(_wp(ctx))
        q2 = p[:, :2]
        r = np.hypot(p[:, 0] - EXIT[0], p[:, 1] - EXIT[1])
        char = (r < 1.6) & (p[:, 1] > 15.5)
        c = np.where(char[:, None], px.quant(ctx, EMBER, 0.25 + 0.35 * (r < 1.1)), c)
        on = (_polyline_dist(q2, CRACKS_B) < 0.28) & (r < 5.0) & (p[:, 1] > 15.5)
        hot = np.clip(1 - r / 5.0, 0, 1)
        c = np.where(on[:, None], px.quant(ctx, SUN, 0.25 + 0.75 * hot), c)
        g = np.where(on, 0.5 + 0.45 * hot, np.where(char, 0.0, g))
    return c, ctx.ones(), g


def mat_keel(ctx):
    lv, c, g = chitin(ctx, rim=0.45, bands=False, offset=0.04)
    return c, ctx.ones(), g


def mat_shoulder(ctx):
    lv, c, g = chitin(ctx, rim=0.38, photo=0)
    c, gl = warm(ctx, c, lv, 0.6)
    return c, ctx.ones(), np.maximum(g, gl)


def mat_spine(ctx):
    ix, iy, W, H = px.texel(ctx)
    blaze, open_, day = _P(ctx)
    c = px.shade(ctx, CHITIN, offset=0.0, up=0.3)
    tip = (iy == 0) if px.side(ctx) else np.zeros(ctx.N, bool)
    c = np.where(tip[:, None], DAYGOLD if day else PHOTO_DIM, c)
    return c, ctx.ones(), np.where(tip, 0.35, 0.0)


def mat_seam(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = px.quant(ctx, SUN, 0.6 + 0.3 * ((ix % 3) == 1))
    return c, ctx.ones(), np.full(ctx.N, 0.95)


def _limb_shell(ctx, outer_faces, bands=3):
    """Skin on the inside of a limb, overlapping shell segments on its outer side."""
    ix, iy, W, H = px.texel(ctx)
    if ctx.face in outer_faces and H >= 4:
        lv = px.light(ctx, grad=0.05) - 0.16
        seg = max(H // bands, 1)
        r = iy % seg
        crest = np.abs(ix - (W - 1) / 2) <= (W - 1) / 2 * 0.6
        lv = lv + 0.24 * (r == 0) * crest + 0.06 * (r == 1) - 0.1 * (r == seg - 1)
        lv = lv - 0.1 * ((ix == 0) | (ix == W - 1))
        c = px.quant(ctx, CHITIN, lv)
        c, gl = warm(ctx, c, lv, 0.6)
        return c, ctx.ones(), gl
    c, g = skin_paint(ctx, skin_level(ctx, rim_up=0.12))
    return c, ctx.ones(), g


def mat_forearm(ctx):
    p = _wp(ctx)
    outer = ("west",) if p[:, 0].mean() > 0 else ("east",)
    return _limb_shell(ctx, outer + ("south",), bands=2)


def mat_shin(ctx):
    return _limb_shell(ctx, ("north", "east", "west"), bands=2)


def mat_knee(ctx):
    lv, c, g = chitin(ctx, rim=0.35, bands=False)
    return c, ctx.ones(), g


def mat_foot(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, offset=0.0, rim_up=0.26, rough=0.05)
    c, g = skin_paint(ctx, lv, light=0.0)
    if ctx.face == "up" and W >= 6:
        c = np.where(((iy % 3) == 0)[:, None], SKIN[5], c)                       # scutes
    return c, ctx.ones(), g


def mat_claw(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = px.shade(ctx, CLAW, offset=0.0, up=0.25)
    if px.side(ctx) and H >= 2:
        c = np.where((iy == H - 1)[:, None], CLAW[5], c)
    return c, ctx.ones(), ctx.zeros()


def mat_fin(ctx):
    """Soft torn fin membrane (cutout): rays fanning from the root, a ragged trailing edge with
    a dithered (half-transparent) margin, a few holes.  Painted from snapped world positions,
    so both faces of the plane agree."""
    blaze, open_, day = _P(ctx)
    q = _qpos(ctx)
    qy, qz = q[:, 1], q[:, 2]
    u = (qz - qz.min()) / max(np.ptp(qz), 1.0)                      # 0 at the root edge -> 1 trailing
    v = (qy.max() - qy) / max(np.ptp(qy), 1.0)                      # 0 top -> 1 bottom
    tear = 0.7 + 0.18 * np.abs(np.sin(qy * 0.9 + 0.5)) + 0.1 * np.sin(qy * 0.37)
    keep = u <= tear
    margin = keep & (u > tear - 0.1)
    checker = ((qy + qz) % 2) == 0
    notch = (np.mod(qy, 7) == 3) & (u > tear - 0.4)
    holes = _h2(qz, qy, 2.0) < 0.025
    a = keep & ~notch & ~holes & (~margin | checker)
    ray = np.mod(qy + np.floor(u * 2.5), 3) == 0
    c = np.where(ray[:, None], px.col("#2a3a3b"), px.col("#101819"))
    c = np.where(margin[:, None], px.col("#34474a"), c)
    if day > 0.5:
        c = np.where(ray[:, None], px.col("#8a6a2c"), c)
    return c, a.astype(float), ctx.zeros()


def mat_web(ctx):
    """Webbing between the fingers: a scalloped lower edge, half-transparent margin."""
    q = _qpos(ctx)
    qy, qz = q[:, 1], q[:, 2]
    rel = qy - qy.min()
    scallop = rel >= (np.mod(qz, 2) + 1)
    margin = rel < 3
    a = scallop & (~margin | (((qy + qz) % 2) == 0) | (rel >= 2))
    c = np.where(margin[:, None], px.col("#18272a"), px.col("#0b1416"))
    return c, a.astype(float), ctx.zeros()


def mat_core(ctx):
    """The light shell at a wound: white-hot centre, gold ring, ember corners."""
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    cx, cy = (W - 1) / 2, (H - 1) / 2
    rr = np.hypot((ix - cx) / max(cx, 0.5), (iy - cy) / max(cy, 0.5))
    c = px.quant(ctx, SUN, np.clip(1.05 - rr * 0.45, 0, 1))
    g = np.clip(0.7 + 0.25 * (1 - rr) + 0.1 * blaze, 0, 1)
    if ctx.face not in ("north", "south"):
        g = np.full(ctx.N, 0.8)
    return c, ctx.ones(), g


def mat_core_hot(ctx):
    return np.broadcast_to(SUN[5], (ctx.N, 3)).copy(), ctx.ones(), np.full(ctx.N, 1.0)


# ============================================================================= the sword (embedded and held)

def sword_materials():
    return {"s_blade": mat_s_blade, "s_ricasso": mat_s_ricasso, "s_hilt": mat_s_hilt, "s_sun": mat_s_sun,
            "s_grip": mat_s_grip, "s_pommel": mat_s_pommel}


def _sblaze(ctx):
    return max(ctx.params.get("blaze", 0.0), ctx.params.get("day", 0.0))


def mat_s_blade(ctx):
    """White-gold metal blade: bright bevelled edges, a white-hot fuller line, soft heat bands;
    the flat glows a little, the fuller a lot (so the blade's shape stays readable)."""
    ix, iy, W, H = px.texel(ctx)
    b = _sblaze(ctx)
    if W >= 3 and H >= W:
        edge = (ix == 0) | (ix == W - 1)
        fuller = (ix == W // 2) & (H > W)
        heat = ((iy // 4) % 3) == 1                                   # slow heat bands along the flat
        c = np.where(edge[:, None], STEEL[4], np.where(heat[:, None], STEEL[3], STEEL[2]))
        c = np.where(fuller[:, None], SUN[5], c)
        g = np.where(fuller, 0.9, np.where(edge, 0.3, 0.12))
    else:
        c = np.broadcast_to(STEEL[3], (ctx.N, 3)).copy()
        c = np.where(((iy % 4) == 0)[:, None], STEEL[1], c)
        g = np.full(ctx.N, 0.3)
    return c, ctx.ones(), np.clip(g + 0.2 * b, 0, 1)


SUN_GLYPH = ["..r..",
             ".oOo.",
             "rOWOr",
             ".oOo.",
             "..r.."]


def mat_s_ricasso(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = px.shade(ctx, STEEL, offset=-0.1)
    g = np.full(ctx.N, 0.45)
    if W >= 5 and H >= 3:
        c, g = px.decal(ctx, c, ["r.r", ".O.", "r.r"], {"r": GOLD[3], "O": "#ffffff"}, "c", "c", glow=g,
                        glow_chars="O", glow_level=0.95)
    return c, ctx.ones(), g


def mat_s_hilt(ctx):
    """Gold rays of the guard and the collar: bright upper edges, darker undersides."""
    c = px.shade(ctx, GOLD, offset=0.08, up=0.2, down=0.12)
    return c, ctx.ones(), np.full(ctx.N, 0.3 + 0.2 * _sblaze(ctx))


def mat_s_sun(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = px.shade(ctx, GOLD, offset=0.12, up=0.2)
    g = np.full(ctx.N, 0.4)
    if W >= 5 and H >= 5:
        c, g = px.decal(ctx, c, SUN_GLYPH, {"r": GOLD[4], "o": "#f0b14a", "O": "#ffe28c", "W": "#ffffff"}, "c", "c",
                        glow=g, glow_chars="oOWr", glow_level=0.9)
    return c, ctx.ones(), g


def mat_s_grip(ctx):
    """Dark leather wrapped with gold wire (diagonal turns)."""
    ix, iy, W, H = px.texel(ctx)
    c = px.shade(ctx, LEATHER, offset=0.1)
    if px.side(ctx):
        wire = ((iy + ix) % 3) == 0
        c = np.where(wire[:, None], GOLD[3], c)
        g = np.where(wire, 0.25, 0.0)
    else:
        g = ctx.zeros()
    return c, ctx.ones(), g


def mat_s_pommel(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = px.shade(ctx, GOLD, offset=0.1, up=0.25)
    centre = (np.abs(ix - (W - 1) / 2) < 0.6) & (np.abs(iy - (H - 1) / 2) < 0.6)
    c = np.where(centre[:, None], SUN[4], c)
    return c, ctx.ones(), np.where(centre, 0.9, 0.3)


def build_sword() -> Model:
    """The held sword (the same design as the one through his chest): root -> sword, grip
    centre at the origin, blade along +Y (broad faces front/back), 29.25 px long."""
    m = Model("bathyas_sword", ppu=2.0, atlas_width=64)
    m.bone("root", None, (0, 0, 0))
    sw = m.bone("sword", "root", (0, 0, 0))
    sword_parts(m, sw.name, (0.0, 0.0, 0.0), flat="z", tip=25.75)
    sw.locators["blade_tip"] = (0.0, 25.75, 0.0)
    sw.locators["blade_mid"] = (0.0, 14.0, 0.0)
    sw.locators["guard"] = (0.0, 2.5, 0.0)
    m.pack()
    return m
