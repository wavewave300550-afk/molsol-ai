"""Race 008 - Bathyas, the Sun-Impaled.  UNIQUE race.

An abyssal humanoid chimera - deep-sea anglerfish, goblin shark and giant isopod - drawn
as an exhausted, irritable old man who has carried a sun through his heart for longer
than he can remember.  The design rules (see docs/CREATIVE.md, v1.2 redesign):

  * a tall, elongated, slightly hunched silhouette: a narrow aged head pushed forward
    and down between heavy segmented shoulders, a thick dorsal hump of seven
    giant-isopod plates, long arms whose webbed, hard-tipped fingers hang to the knee,
    humanoid thighs over armoured aquatic shins and WIDE clawed feet;
  * near light-absorbing blue-black skin that still reads in Minecraft: wet rims along
    every upper edge, plate edges, a few green-grey reflections, small pits and bumps;
  * ONE light source - the white-gold sword through his chest: hilt and sun-guard just
    below the sternum, ~11 px of blade out of the back, charred tissue at entry and
    exit, white-gold fractures running along the ribs, and the skin it faces lit warm;
    the glow at both wounds beats like a heart (core_f / core_b);
  * cold cyan photophores along plate edges as the only other light (gold at daybreak).

Variants: base (Impaled) | lure (blazing) | maw (Goblin Maw Rush) | bastion (Isopod
Bastion) | unshackled (sword drawn: open wound, predatory stance) | daybreak (lit gold
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

# --------------------------------------------------------------------------- the impalement
ENTRY = (0.0, 18.0, -2.75)                  # front wound, just below the sternum
SWORD_PITCH = 22.0                          # the blade rises this much (deg) on its way out of the back
GUARD_Y = 4.0                               # sword-local height that sits at the entry wound
_D = np.array([0.0, math.sin(math.radians(SWORD_PITCH)), math.cos(math.radians(SWORD_PITCH))])


def along(t: float):
    """Point on the sword axis, t units from the entry wound toward the back."""
    return tuple(np.array(ENTRY) + _D * t)


EXIT_T = 8.1
EXIT = along(EXIT_T)                        # where the blade leaves the back (on plate 3)
TIP_T = 19.25                               # ~11 px of blade out of the back
HILT_T = -3.0                               # the hilt's middle, in front of the chest

# --------------------------------------------------------------------------- palettes (dark -> light)
SKIN = px.pal("#030405", "#06090b", "#0b1114", "#11191d", "#182429", "#223338", "#324a4c", "#517069")
CHITIN = px.pal("#020304", "#05080b", "#0a1015", "#10191f", "#172530", "#21343e", "#304b55", "#4f727a")
LIT = px.pal("#2a1a0b", "#4d3214", "#7c5420", "#ad7d32", "#d8aa52", "#f3d48a", "#fff2c8")
SUN = px.pal("#b07a2c", "#dcaa4a", "#f2d17e", "#fdeab4", "#fff8e2", "#ffffff")
GOLD = px.pal("#3c240b", "#6a4416", "#a06c24", "#cf9c3c", "#efc867", "#fbe7a2")
EMBER = px.pal("#020101", "#0d0504", "#1e0a06", "#3a1309", "#62210c")
GILL = px.pal("#12060a", "#2a0c12", "#48131a", "#701f22", "#94332c")
BONE = px.pal("#4a4436", "#7c745a", "#ada382", "#d6cca6", "#f1e9cc")
CLAW = px.pal("#050505", "#0f0e0d", "#211e1a", "#3d372f", "#6b6152", "#9b8e78")
LEATHER = px.pal("#0d0805", "#1d120a", "#311f12", "#4a301b")
PHOTO = px.col("#7ee8cf")                   # cold photophores
PHOTO_DIM = px.col("#2f7f78")
DAYGOLD = px.col("#ffd36e")
REFLECT = px.col("#2e463f")                 # sparse green-grey reflections
WET = px.col("#6f8f86")                     # the rare wet specular texel


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
        ("c", "breast", "trunk", (0.0, 22.25, -3.25), (6.5, 1.5, 0.5)),
        ("c", "rsh", "r_pauldron", (-6.0, 25.0, 0.25), (3.5, 0.5, 4.5)),
        ("c", "lsh", "l_pauldron", (6.0, 25.0, 0.25), (3.5, 0.5, 4.5)),
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
        lg = m.bones[g]
        lg.variant.update({v: ((0.0, -1.0, 0.0), (-24.0, 0.0, 0.0)) for v in CROUCH})
        m.box(g, (s * 2.4, 10.25, 0.0), (3.75, 4.5, 4.0), "skin")                      # thigh
        m.box(g, (s * 2.5, 7.5, -0.25), (3.25, 2.0, 3.5), "skin")                      # above the knee
        m.box(g, (s * 2.5, 6.75, -2.0), (2.5, 2.0, 1.0), "plate")                      # knee cap
        sh = m.bone(f"{p}_shin", g, (s * 2.5, 6.75, -0.25))
        sh.variant.update({v: ((0, 0, 0), (50.0, 0.0, 0.0)) for v in CROUCH})
        m.box(sh.name, (s * 2.5, 4.25, 0.25), (3.0, 4.5, 3.5), "skin")                 # shin
        m.box(sh.name, (s * 2.5, 4.5, -1.75), (3.5, 4.0, 1.0), "greave")               # segmented shin armour
        m.box(sh.name, (s * 2.5, 4.5, 3.25), (0.0, 3.5, 2.5), "fin", cutout=True)      # calf fin
        ft = m.bone(f"{p}_foot", sh.name, (s * 2.5, 2.0, 0.0))
        ft.variant.update({v: ((0, 0, 0), (-26.0, 0.0, 0.0)) for v in CROUCH})
        m.box(ft.name, (s * 2.75, 1.0, -0.5), (4.5, 2.0, 5.0), "foot")                 # wide flat foot
        for k, dx in enumerate((-1.5, 0.0, 1.5)):                                       # three thick digits
            x = s * 2.75 + dx
            m.box(ft.name, (x, 0.75, -3.75), (1.5, 1.5, 1.5), "foot")
            m.box(ft.name, (x, 0.5, -4.75), (1.0, 1.0, 0.5), "claw")                   # short claws
        m.box(ft.name, (s * 2.75, 0.75, 2.5), (2.0, 1.5, 1.0), "claw")                 # heel spur
        ft.locators[f"{p}_step"] = (s * 2.75, 0.2, -1.5)


# ----------------------------------------------------------------------------- trunk: a gaunt old body under a dorsal hump

def _trunk(m: Model) -> None:
    t = m.bone("trunk", "torso_g", (0.0, 12.0, 0.0))
    t.variant.update({"unshackled": ((0, 0, 0), (9.0, 0, 0)), "daybreak": ((0, 0, 0), (-6.0, 0, 0)),
                      "bastion": ((0, 0, 0), (6.0, 0, 0))})
    m.box(t.name, (0.0, 12.75, 0.25), (7.0, 3.5, 4.5), "skin")                       # pelvis
    m.box(t.name, (0.0, 15.5, 0.0), (6.0, 2.5, 4.0), "belly")                        # narrow old waist
    m.box(t.name, (0.0, 18.75, -0.25), (7.5, 4.5, 5.0), "ribs")                      # ribcage (the wound)
    m.box(t.name, (0.0, 22.25, -0.25), (9.0, 2.5, 5.5), "chest")                     # heavy shoulders / chest shelf
    m.box(t.name, (0.0, 24.0, 2.0), (7.0, 3.5, 4.0), "skin")                         # the hump behind the neck
    m.box(t.name, (0.0, 20.75, 2.0), (8.0, 3.5, 3.5), "skin")                        # upper back under the plates
    t.locators["lure_c"] = (0.0, 18.0, -9.0)
    t.locators["back"] = (0.0, 22.0, 6.5)


# ----------------------------------------------------------------------------- seven giant-isopod plates

PLATES = [  # (centre y, centre z, width, height, thickness, tilt rx) - the hunch, top to bottom
    (26.25, 1.25, 6.0, 2.5, 1.5, 70.0),
    (24.75, 3.5, 8.0, 3.0, 1.5, 42.0),
    (22.75, 4.25, 9.0, 3.0, 1.5, 18.0),
    (20.5, 4.0, 9.0, 3.0, 1.5, 6.0),        # the blade exits through this one
    (18.0, 2.75, 8.5, 3.0, 1.0, -2.0),
    (15.5, 2.5, 7.5, 3.0, 1.0, -8.0),
    (13.0, 2.75, 7.0, 2.5, 1.0, -16.0),
]
# bastion: the plates slide together and over the nape (offset, extra tilt)
PLATE_BASTION = [((0, 0.75, -0.75), 12.0), ((0, 0.5, -0.25), 8.0), ((0, 0.25, 0.25), 4.0), ((0, 0, 0.25), 0.0),
                 ((0, 0.5, 0.5), -4.0), ((0, 1.0, 0.75), -8.0), ((0, 1.5, 1.0), -12.0)]


def _plates(m: Model) -> None:
    for k, (y, z, w, h, th, rx) in enumerate(PLATES):
        b = m.bone(f"plate{k}", "trunk", (0.0, y, z), (rx, 0.0, 0.0))
        off, extra = PLATE_BASTION[k]
        b.variant["bastion"] = (off, (rx + extra, 0.0, 0.0))
        b.variant["daybreak"] = ((0, 0, 0.25 * k / 6), (rx - 6.0 + k * 1.5, 0.0, 0.0))
        m.box(b.name, (0.0, y, z), (w, h, th), "plate")
        m.box(b.name, (0.0, y + 0.25, z + th / 2 + 0.25), (1.5, h - 0.5, 0.5), "plate")        # raised spinal keel
        if 1 <= k <= 5:                                                                           # flanges wrap the flanks
            for s in (-1, 1):
                fx = s * (w / 2 + 0.6)
                m.cube(b.name, (fx - 0.75, y - h / 2 + 0.25, z - th / 2 - 0.25), (1.5, h - 0.5, th),
                       "plate", pivot=(s * w / 2, y, z), rot=(0.0, -s * 38.0, 0.0))
        if k <= 2:                                                                                # dorsal spines
            m.cube(b.name, (-0.5, y + h / 2 - 0.5, z + th / 2), (1.0, 1.0, 1.5), "spine",
                   pivot=(0.0, y + h / 2 - 0.5, z + th / 2), rot=(-35.0, 0.0, 0.0))
        # bastion: thin seams of white-gold light leak between the closing plates
        m.box(b.name, (0.0, y - h / 2 + 0.25, z - 0.25), (w - 1.5, 0.5, th), "seam", only={"bastion"})


# ----------------------------------------------------------------------------- torn fins

def _fins(m: Model) -> None:
    for s, p in ((-1, "r"), (1, "l")):
        f = m.bone(f"{p}_fin", "trunk", (s * 4.25, 22.0, 2.5), (6.0, s * 24.0, 0.0))
        f.variant.update({"daybreak": ((0, 0, 0), (-10.0, s * 46.0, 0.0)), "bastion": ((0, 0, 0), (12.0, s * 8.0, 0.0))})
        m.box(f.name, (s * 4.25, 18.5, 4.75), (0.0, 7.0, 4.5), "fin", cutout=True)


# ----------------------------------------------------------------------------- the sun through his heart

def sword_parts(m: Model, bone: str, base, flat: str = "z", tip: float = 25.75, blade_from: float = 4.25,
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

    box(-3.0, 1.5, 1.5, 1.5, "s_pommel")                 # pommel: a small sun
    box(-2.0, 2.0, 0.5, 1.0, "s_hilt")                   # collar
    box(0.0, 1.0, 4.0, 1.0, "s_grip")                    # wrapped grip
    box(3.0, 7.0, 1.0, 0.5, "s_hilt")                    # the guard's horizontal rays
    box(3.0, 4.5, 0.5, 0.5, "s_hilt", rot=45.0)          # diagonal rays
    box(3.0, 4.5, 0.5, 0.5, "s_hilt", rot=-45.0)
    box(3.0, 2.5, 2.5, 1.0, "s_sun")                     # the sun disc at the heart of the guard
    if ricasso:
        box(blade_from + 0.75, 2.5, 1.5, 0.75, "s_ricasso")
    main = tip - 1.5 - blade_from
    box(blade_from + main / 2, 2.0, main, 0.5, "s_blade")
    box(tip - 1.0, 1.0, 1.0, 0.5, "s_blade")
    box(tip - 0.25, 0.5, 0.5, 0.5, "s_blade")


def _sword(m: Model) -> None:
    sw = m.bone("sword", "trunk", ENTRY, (-(90.0 - SWORD_PITCH), 0.0, 0.0))
    ex, ey, ez = ENTRY
    sword_parts(m, sw.name, (ex, ey - GUARD_Y, ez), flat="x", tip=GUARD_Y + TIP_T, blade_from=GUARD_Y + EXIT_T - 0.75,
                ricasso=False, skip=NO_SWORD)
    sw.locators["wound"] = ENTRY


def _core(m: Model) -> None:
    """The light shells at both wounds: scaled on a heart-rate rhythm by the animations."""
    cf = m.bone("core_f", "trunk", ENTRY)
    x, y, z = ENTRY
    m.box(cf.name, (x, y, z - 0.25), (3.0, 3.0, 0.5), "core")
    m.box(cf.name, (x, y, z - 0.375), (1.5, 1.5, 0.75), "core_hot")
    cb = m.bone("core_b", "trunk", EXIT, (PLATES[3][5], 0.0, 0.0))
    ex, ey, ez = EXIT
    m.box(cb.name, (ex, ey, ez + 0.125), (2.5, 2.5, 0.25), "core")
    cb.locators["wound_back"] = (ex, ey, ez + 0.5)


# ----------------------------------------------------------------------------- long arms: segmented shoulders, webbed hard-tipped hands

FINGER_Z = (-1.25, -0.25, 0.75)
FINGER_FAN = (-12.0, 0.0, 12.0)


def _arms(m: Model) -> None:
    for s, g, p in ((-1, "r_arm_g", "r"), (1, "l_arm_g", "l")):
        pa = m.bone(f"{p}_pauldron", g, (s * 5.0, 23.5, 0.25))
        pa.variant.update({"bastion": ((-s * 0.5, 0.5, 0.0), side_rot((0, 0, 6), s)),
                           "unshackled": ((0, 0.25, -0.25), None), "daybreak": ((0, 0.75, 0), side_rot((0, 0, -10), s))})
        for (cx, cy, w, h, d, a) in ((6.0, 24.25, 4.5, 1.5, 5.5, 12.0), (7.25, 22.75, 3.5, 1.5, 5.0, 36.0),
                                     (7.9, 21.25, 2.5, 1.5, 4.5, 60.0)):
            c = (s * cx, cy, 0.25)
            m.cube(pa.name, (c[0] - w / 2, cy - h / 2, 0.25 - d / 2), (w, h, d), "plate", pivot=c, rot=(0.0, 0.0, s * a))
        up = m.bone(f"{p}_upper", g, (s * 5.5, 22.0, 0.0))
        m.box(up.name, (s * 6.25, 18.75, 0.0), (3.0, 6.0, 3.0), "skin")
        fo = m.bone(f"{p}_fore", up.name, (s * 6.25, 16.0, 0.25), (-8.0, 0.0, 0.0))
        m.box(fo.name, (s * 6.25, 13.75, 0.0), (3.5, 4.5, 3.5), "skin")                  # powerful forearm
        m.box(fo.name, (s * 6.75, 14.0, 0.0), (2.75, 3.0, 4.0), "bracer")               # segmented forearm armour
        m.box(fo.name, (s * 6.25, 16.0, 1.5), (3.0, 1.5, 1.5), "plate")                 # elbow cap
        m.box(fo.name, (s * 6.25, 13.75, 3.0), (0.0, 4.0, 2.5), "fin", cutout=True)     # forearm fin
        hd = m.bone(f"{p}_hand", fo.name, (s * 6.25, 11.5, -0.25))
        m.box(hd.name, (s * 6.25, 10.5, -0.25), (2.5, 2.0, 3.0), "skin")                # palm
        m.box(hd.name, (s * 6.5, 8.5, -0.25), (0.0, 2.0, 3.0), "web", cutout=True)      # webbing
        for k, (fz, fan) in enumerate(zip(FINGER_Z, FINGER_FAN)):
            f = m.bone(f"{p}_finger{k}", hd.name, (s * 6.5, 9.5, fz), (fan, 0.0, 0.0))
            m.box(f.name, (s * 6.5, 8.0, fz), (1.0, 3.0, 1.0), "skin")
            m.box(f.name, (s * 6.5, 6.0, fz), (1.0, 1.0, 1.0), "claw")                 # hardened tip
        th = m.bone(f"{p}_thumb", hd.name, (s * 5.5, 10.75, -1.5), side_rot((-10.0, 0.0, -18.0), s))
        m.box(th.name, (s * 5.5, 9.5, -1.5), (1.0, 2.5, 1.0), "skin")
        hd.locators[f"{p}_claws"] = (s * 6.5, 6.0, -0.25)


# ----------------------------------------------------------------------------- the head: an old, tired, predatory face

def _head(m: Model) -> None:
    sk = m.bone("skull", "head_g", (0.0, 24.5, -1.0))
    sk.variant.update({"unshackled": ((0, -0.75, -0.75), (8.0, 0, 0)), "daybreak": ((0, 0.25, 0.25), (-16.0, 0, 0)),
                       "bastion": ((0, -1.0, 0.75), (14.0, 0, 0)), "maw": ((0, -0.25, -1.0), (-6.0, 0, 0))})
    m.box(sk.name, (0.0, 24.5, -0.75), (3.5, 3.0, 3.0), "neck")                      # sinewy neck
    m.box(sk.name, (0.0, 25.0, -3.25), (4.5, 2.0, 2.5), "jowl")                      # cheeks, jaw muscles, gill slits
    m.box(sk.name, (0.0, 28.25, -3.0), (5.0, 4.5, 5.0), "head")                      # the old skull
    m.box(sk.name, (0.0, 28.75, 0.5), (3.5, 3.0, 1.5), "head")                       # occiput
    for s, p in ((-1, "r"), (1, "l")):
        br = m.bone(f"brow_{p}", sk.name, (s * 1.25, 29.0, -5.75), side_rot((0.0, 0.0, 10.0), s))
        br.variant.update({"unshackled": ((0, 0, 0), side_rot((0.0, 0.0, 16.0), s)),
                           "lure": ((0, -0.25, 0), side_rot((0.0, 0.0, 18.0), s))})
        m.box(br.name, (s * 1.375, 29.0, -5.75), (2.75, 1.0, 1.0), "brow")
        lid = m.bone(f"lid_{p}", sk.name, (s * 1.0, 28.5, -5.625))
        m.cube(lid.name, (s * 1.0 - 0.75, 28.0, -5.75), (1.5, 0.5, 0.25), "lid")
        for k in range(3):                                                            # gill flaps along the neck
            z0 = -2.0 + k * 0.875
            gl = m.bone(f"gill_{p}{k}", sk.name, (s * 1.875, 25.0, z0))
            m.cube(gl.name, (s * 1.875 - 0.125, 23.75, z0), (0.25, 2.5, 0.75), "gill")
    mw = m.bone("maw", sk.name, (0.0, 25.5, -4.0))
    mw.variant["maw"] = ((0.0, -0.5, -4.5), None)
    m.box(mw.name, (0.0, 26.25, -6.0), (3.5, 1.0, 2.0), "lip")                       # projecting upper jaw
    m.box(mw.name, (0.0, 26.0, -3.5), (3.0, 1.5, 3.5), "gum")                        # palate: fills the gap when it shoots out
    m.box(mw.name, (0.0, 25.25, -6.0), (3.0, 1.0, 1.5), "teeth_u", cutout=True)      # needle teeth (upper row)
    jw = m.bone("jaw", mw.name, (0.0, 25.0, -3.5))
    jw.variant.update({"maw": ((0, 0, 0), (34.0, 0.0, 0.0)), "daybreak": ((0, 0, 0), (10.0, 0.0, 0.0))})
    m.box(jw.name, (0.0, 24.25, -5.25), (3.5, 1.0, 3.5), "jaw")                      # underbite
    m.box(jw.name, (0.0, 25.25, -6.0), (3.5, 1.0, 2.0), "teeth_l", cutout=True)      # needle teeth (lower row)
    for s in (-1, 1):
        m.box(jw.name, (s * 0.75, 23.0, -6.25), (0.5, 1.5, 0.5), "barbel")           # a scraggly pair of barbels
    jw.locators["maw"] = (0.0, 24.75, -7.25)
    sk.locators["eyes"] = (0.0, 28.0, -6.25)
    sk.locators["gills"] = (0.0, 24.5, -1.0)


# ============================================================================= materials

def materials():
    mats = {
        "skin": mat_skin, "belly": mat_belly, "ribs": mat_ribs, "chest": mat_chest, "neck": mat_neck,
        "jowl": mat_jowl, "head": mat_head, "brow": mat_brow, "lid": mat_lid, "lip": mat_lip, "gum": mat_gum,
        "jaw": mat_jaw, "teeth_u": mat_teeth_u, "teeth_l": mat_teeth_l, "barbel": mat_barbel, "gill": mat_gill,
        "plate": mat_plate, "spine": mat_spine, "seam": mat_seam, "greave": mat_greave, "bracer": mat_bracer,
        "foot": mat_foot, "claw": mat_claw, "fin": mat_fin, "web": mat_web, "core": mat_core, "core_hot": mat_core_hot,
        "accent": mat_accent,
    }
    mats.update(sword_materials())
    return mats


def _P(ctx):
    p = ctx.params
    return p.get("blaze", 0.0), p.get("open", 0.0), p.get("day", 0.0)


def _wp(ctx):
    return ctx.wp if ctx.wp is not None else ctx.p


def _h2(ix, iy, seed):
    v = np.sin(ix * 12.9898 + iy * 78.233 + seed * 37.719) * 43758.5453
    return v - np.floor(v)


def _hp(p, seed=0.0):
    """Deterministic value in [0,1) per world-space texel position (consistent across faces)."""
    v = np.sin(p[:, 0] * 41.13 + p[:, 1] * 17.71 + p[:, 2] * 29.97 + seed * 7.31) * 43758.5453
    return v - np.floor(v)


# ----------------------------------------------------------------------------- light from the sword

def _light_sources(ctx):
    blaze, open_, day = _P(ctx)
    if open_:
        src = [(np.array(ENTRY) + np.array([0, 0, -0.75]), 7.0, 1.25), (np.array(EXIT) + np.array([0, 0, 0.6]), 5.0, 0.9)]
    else:
        src = [(np.array(along(HILT_T)), 6.5, 1.0), (np.array(ENTRY) + np.array([0, 0, -0.5]), 5.5, 0.9),
               (np.array(EXIT) + np.array([0, 0, 0.5]), 5.0, 0.8)]
        for t in (11.0, 14.5, 18.0):
            src.append((np.array(along(t)), 4.0, 0.55))
    k = 1.0 + 0.7 * blaze
    return [(c, R * (1.0 + 0.45 * blaze), s * k) for c, R, s in src]


def sun_light(ctx) -> np.ndarray:
    """0..1: how much of the sword's / wound's warm light falls on each texel (rest pose)."""
    p = _wp(ctx)
    n = ctx.wn if ctx.wn is not None else ctx.n
    out = np.zeros(ctx.N)
    for c, R, s in _light_sources(ctx):
        d = c[None, :] - p
        dist = np.maximum(np.linalg.norm(d, axis=1), 1e-6)
        facing = np.clip((d @ n) / dist + 0.3, 0, 1)
        out += s * np.clip(1 - dist / R, 0, 1) ** 2 * facing
    return np.clip(out, 0, 1)


def warm(ctx, rgb, lv, amount=1.0):
    """Paint the sword's light onto dark skin: warm palette steps with an ordered-dither edge."""
    blaze, open_, day = _P(ctx)
    I = sun_light(ctx) * amount
    ix, iy, W, H = px.texel(ctx)
    th = px.BAYER4[iy % 4, ix % 4]
    lit = I * 1.35 > 0.18 + th * 0.4
    c_lit = px.quant(ctx, LIT, np.clip(lv * 0.55 + I * 0.95 - 0.05, 0, 1))
    out = np.where(lit[:, None], c_lit, rgb)
    glow = np.where(lit & (I > 0.55), 0.18 * blaze + 0.12 * day, 0.0)
    return out, glow


# ----------------------------------------------------------------------------- fractures and veins

def _seg_dist(p2, a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((p2 - a) @ ab) / max(float(ab @ ab), 1e-9), 0, 1)
    return np.linalg.norm(p2 - (a + t[:, None] * ab), axis=1)


# cracks in the plane of the chest, (u, y): u = x on the front, unwrapped around the flanks
CRACKS_F = [
    [(0.0, 18.0), (-0.75, 18.75), (-1.0, 19.75), (-0.5, 20.5), (-0.75, 21.25)],               # up the sternum
    [(0.0, 18.0), (-1.25, 18.25), (-2.25, 18.0), (-3.25, 17.5), (-4.25, 17.0), (-5.75, 16.75)],   # along a rib (right)
    [(0.0, 18.0), (1.25, 18.5), (2.25, 18.25), (3.5, 17.75), (4.5, 17.25), (6.0, 17.0)],     # along a rib (left)
    [(-1.0, 19.75), (-2.0, 20.0), (-3.0, 19.75), (-4.0, 19.25), (-5.0, 19.0)],               # the rib above (right)
    [(0.5, 18.75), (1.5, 19.5), (2.75, 20.0), (3.75, 19.75), (4.75, 19.5)],                  # the rib above (left)
    [(0.0, 18.0), (-0.75, 17.0), (-1.75, 16.5)],                                              # down into the belly
    [(0.0, 18.0), (0.5, 17.0), (1.5, 16.25), (2.0, 15.5)],
]
CRACKS_F_BLAZE = [
    [(-0.75, 21.25), (-1.75, 22.0), (-3.0, 22.5)],
    [(-0.5, 20.5), (0.75, 21.5), (2.25, 22.25)],
    [(2.0, 15.5), (2.75, 14.5)],
    [(-5.75, 16.75), (-7.0, 16.25)],
    [(6.0, 17.0), (7.25, 16.5)],
]
# cracks around the exit on the back, (x, y) seen from behind
CRACKS_B = [
    [(0.0, 21.0), (-1.0, 21.75), (-2.0, 22.25), (-3.25, 22.5), (-4.25, 23.25)],
    [(0.0, 21.0), (1.25, 21.5), (2.25, 21.25), (3.5, 21.75)],
    [(0.0, 21.0), (-0.75, 20.0), (-1.75, 19.25), (-2.5, 18.25)],
    [(0.0, 21.0), (0.75, 20.0), (1.5, 18.75), (1.25, 17.5)],
    [(0.0, 21.0), (0.25, 22.25), (-0.25, 23.5), (0.5, 24.5)],
]


def _unwrap(ctx):
    """2D coordinates on the trunk surface for the chest cracks: front faces use x; side faces
    continue around the flank (x grows as you go back)."""
    p = _wp(ctx)
    n = ctx.wn if ctx.wn is not None else ctx.n
    if n[2] < -0.5:
        u = p[:, 0]
    elif abs(n[0]) > 0.5:
        sgn = np.sign(n[0])
        u = sgn * (np.abs(p[:, 0]) + (p[:, 2] - ENTRY[2]))
    else:
        u = p[:, 0]
    return np.stack([u, p[:, 1]], axis=1)


def crack_field(ctx, sets, width=0.3):
    """Returns (on_crack mask, distance-to-wound) for texels near the given crack polylines."""
    q = _unwrap(ctx)
    best = np.full(ctx.N, 9.0)
    for pl in sets:
        for a, b in zip(pl[:-1], pl[1:]):
            best = np.minimum(best, _seg_dist(q, a, b))
    return best < width


@lru_cache(maxsize=None)
def _vein_points():
    rng = np.random.default_rng(8)
    return rng.uniform([-10, -1, -9], [10, 33, 16], size=(260, 3))


def veins(ctx, thick=0.11):
    """A network of fine fractures over the whole body (daybreak: lit from within)."""
    p = _wp(ctx)
    pts = _vein_points()
    d = np.linalg.norm(p[:, None, :] - pts[None, :, :], axis=2)
    d.sort(axis=1)
    return (d[:, 1] - d[:, 0]) < thick * 2.0


# ----------------------------------------------------------------------------- the skin

def skin_level(ctx, offset=0.0, grad=0.10, rim_up=0.24, rim_down=0.05, rough=0.07, proxy=None):
    ix, iy, W, H = px.texel(ctx)
    if proxy is not None:
        lv = px.proxy(ctx, proxy[0], proxy[1], proxy[2] if len(proxy) > 2 else 0.8)
        if px.side(ctx) and H > 1:
            lv = lv + grad * (0.5 - iy / (H - 1))
    else:
        lv = px.light(ctx, grad=grad)
    lv = lv - 0.17 + offset
    if px.side(ctx) and H >= 3:
        lv = lv + rim_up * (iy == 0) - rim_down * (iy == H - 1)
        if rough:
            s = ctx.seed
            pit = _h2(ix, iy, s) < rough
            bump = (_h2(ix, iy + 1, s) < rough) & ~pit & (iy > 0)
            lv = lv - 0.12 * pit + 0.09 * bump
    elif ctx.face == "up" and min(W, H) >= 3:
        lv = lv + rim_up * 0.45 * px.border(ctx, 1)
    return lv


def skin_paint(ctx, lv, pal=SKIN, sheen=True, light=1.0):
    """Quantise onto the skin ramp, then wet runs, rare reflections, the sword's light, and
    the daybreak veins.  Returns (rgb, glow)."""
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    c = px.quant(ctx, pal, lv)
    if sheen and px.side(ctx) and H >= 4:
        col_h = _h2(ix, 0, ctx.seed + 5)
        run = (col_h < 0.2) & (iy >= 1) & (iy <= 1 + (col_h * 10).astype(int) % 3)
        c = np.where(run[:, None], px.quant(ctx, pal, lv + 0.13), c)
        refl = (_h2(ix, iy, ctx.seed + 9) < 0.03) & (iy > 0) & (iy < H - 1)
        c = np.where(refl[:, None], REFLECT, c)
        spec = (iy == 0) & (_h2(ix, 1, ctx.seed + 3) < 0.12)
        c = np.where(spec[:, None], WET, c)
    glow = np.zeros(ctx.N)
    if light:
        c, glow = warm(ctx, c, lv, light)
    if day > 0.5:
        v = veins(ctx)
        c = np.where(v[:, None], px.quant(ctx, SUN, 0.45 + 0.3 * (px.hash01(ctx, 4) > 0.5)), c)
        glow = np.where(v, 0.7, glow)
        if px.side(ctx) and H >= 3:
            rim_ = iy == 0
            c = np.where(rim_[:, None], LIT[4], c)
            glow = np.where(rim_, np.maximum(glow, 0.25), glow)
    return c, glow


def mat_skin(ctx):
    lv = skin_level(ctx)
    c, g = skin_paint(ctx, lv)
    return c, ctx.ones(), g


def mat_belly(ctx):
    """The gaunt waist: ribbed shadow lines under the ribcage."""
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, offset=-0.02)
    if ctx.face == "north":
        lv = lv - 0.1 * ((iy % 2) == 1) * (np.abs(ix - (W - 1) / 2) < W / 2 - 1)
    c, g = skin_paint(ctx, lv)
    return _cracked(ctx, c, g)


def _cracked(ctx, c, g):
    """White-gold fractures on the trunk's front and flanks; charred tissue at the entry wound."""
    blaze, open_, day = _P(ctx)
    n = ctx.wn if ctx.wn is not None else ctx.n
    if n[2] > 0.5 or n[1] < -0.5:
        return c, ctx.ones(), g
    sets = CRACKS_F + (CRACKS_F_BLAZE if (blaze or open_ or day) else [])
    on = crack_field(ctx, sets)
    q = _unwrap(ctx)
    r = np.hypot(q[:, 0] - ENTRY[0], q[:, 1] - ENTRY[1])
    if n[2] < -0.5:
        # darkened, charred tissue around the entry; it never closes
        char = r < 2.1 + 0.25 * px.BAYER4[px.texel(ctx)[1] % 4, px.texel(ctx)[0] % 4]
        c = np.where(char[:, None], px.quant(ctx, EMBER, 0.35 + 0.25 * (r < 1.6)), c)
        g = np.where(char, 0.0, g)
    hot = np.clip(1.0 - r / 7.0, 0, 1)
    col = px.quant(ctx, SUN, np.clip(0.3 + 0.7 * hot + 0.2 * blaze, 0, 1))
    c = np.where(on[:, None], col, c)
    g = np.where(on, np.clip(0.55 + 0.4 * hot + 0.2 * blaze, 0, 1), g)
    return c, ctx.ones(), g


def mat_ribs(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, proxy=((0, 18.75, 0.5), (4.5, 4.0, 3.5), 0.7))
    if ctx.face in ("north", "east", "west"):
        lv = lv - 0.11 * ((iy % 3) == 2)                                          # ribs under the skin
    c, g = skin_paint(ctx, lv)
    return _cracked(ctx, c, g)


def mat_chest(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, proxy=((0, 22.0, 0.5), (5.5, 3.0, 3.5), 0.7))
    if ctx.face == "north":
        lv = lv - 0.12 * (np.abs(ix - (W - 1) / 2) < 0.6)                        # sternum furrow
        lv = lv + 0.08 * (iy == H - 2)                                             # pectoral shelf
    c, g = skin_paint(ctx, lv)
    return _cracked(ctx, c, g)


def mat_neck(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, offset=-0.03, rough=0.04)
    if px.side(ctx):
        lv = lv - 0.1 * ((ix % 3) == 1)                                            # sinews
    c, g = skin_paint(ctx, lv)
    return c, ctx.ones(), g


def mat_jowl(ctx):
    """Cheeks and jaw muscles; the gill slits show as dark red lines on the flanks."""
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, offset=-0.02, rough=0.05, proxy=((0, 26.5, -3.0), (2.8, 3.0, 3.0), 0.7))
    c, g = skin_paint(ctx, lv)
    if ctx.face in ("east", "west"):
        slit = ((ix % 2) == 1) & (iy >= 1) & (iy <= H - 2)
        c = np.where(slit[:, None], GILL[2], c)
    return c, ctx.ones(), g


# the face, painted on the skull's front (10 x 9 texels)
FACE = [
    "w..ww..w.w",
    ".hh..hh.h.",
    "..........",
    "..........",
    ".sEEssEEs.",
    ".seP..Pes.",
    "c.bb..bb.c",
    "...nh.n...",
    "..........",
]


def mat_head(ctx):
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, rough=0.05, proxy=((0, 28.5, -2.75), (3.0, 3.0, 3.6), 0.85))
    if ctx.face in ("east", "west"):
        lv = lv - 0.1 * ((iy % 3 == 1) & ((ix + iy) % 4 < 2))                    # deep old wrinkles
    c, g = skin_paint(ctx, lv)
    if ctx.face == "north" and W == 10:
        eye = "#fff0a8" if day else ("#e7dc92" if open_ else "#cdc27c")
        colors = {"w": "#020304", "h": "#22313a", "s": "#000000", "E": eye, "e": "#97894c", "P": "#060403",
                  "b": "#020304", "c": "#05080a", "n": "#000000"}
        gl = 0.65 if day else (0.28 if open_ else 0.12)
        c, g = px.decal(ctx, c, FACE, colors, 0, 0, glow=g, glow_chars="Ee", glow_level=gl)
    if ctx.face == "up" and W >= 8:
        # the atrophied light organ of an anglerfish: three cold photophores along the crown
        dots = (ix == W // 2) & ((iy % 3) == 1)
        c = np.where(dots[:, None], DAYGOLD if day else PHOTO, c)
        g = np.where(dots, 0.5, g)
    return c, ctx.ones(), g


def mat_brow(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, rim_up=0.3, rough=0.0)
    c, g = skin_paint(ctx, lv, light=0.6)
    if ctx.face == "down":
        c = np.full_like(c, SKIN[0])
    return c, ctx.ones(), g


def mat_lid(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = np.broadcast_to(SKIN[3], (ctx.N, 3)).copy()
    if ctx.face == "north":
        c = np.where((iy == H - 1)[:, None], SKIN[1], c)
    return c, ctx.ones(), ctx.zeros()


def mat_lip(ctx):
    ix, iy, W, H = px.texel(ctx)
    if ctx.face == "down":                                                              # the roof of the mouth
        return px.quant(ctx, GILL, px.light(ctx) + 0.1), ctx.ones(), ctx.zeros()
    lv = skin_level(ctx, rim_up=0.2, rough=0.0)
    c, g = skin_paint(ctx, lv)
    return c, ctx.ones(), g


def mat_gum(ctx):
    return px.shade(ctx, GILL, offset=-0.05), ctx.ones(), ctx.zeros()


def mat_jaw(ctx):
    ix, iy, W, H = px.texel(ctx)
    if ctx.face == "up":
        return px.quant(ctx, GILL, px.light(ctx) - 0.1), ctx.ones(), ctx.zeros()
    lv = skin_level(ctx, rough=0.04, rim_up=0.18)
    c, g = skin_paint(ctx, lv)
    return c, ctx.ones(), g


def _teeth(ctx, hang: bool):
    """Irregular rows of needle teeth (cutout): every other texel column a needle of 1-2 texels."""
    ix, iy, W, H = px.texel(ctx)
    if not px.side(ctx):
        return np.broadcast_to(BONE[2], (ctx.N, 3)).copy(), ctx.zeros(), ctx.zeros()
    p = _wp(ctx)
    col = np.floor((p[:, 0] + p[:, 2]) * 2.0 + 0.01).astype(int)
    hv = _h2(col, 0, 3 if hang else 7)
    tooth = (col % 2 == 0) | (hv < 0.25)
    long_ = hv < 0.55
    row_from_root = iy if hang else (H - 1 - iy)
    a = tooth & ((row_from_root == 0) | long_)
    c = np.where((row_from_root == 0)[:, None], BONE[1], BONE[3])
    c = np.where(((row_from_root == H - 1) & long_)[:, None], BONE[4], c)
    return c, a.astype(float), ctx.zeros()


def mat_teeth_u(ctx):
    return _teeth(ctx, True)


def mat_teeth_l(ctx):
    return _teeth(ctx, False)


def mat_barbel(ctx):
    ix, iy, W, H = px.texel(ctx)
    blaze, open_, day = _P(ctx)
    c = px.shade(ctx, SKIN, offset=0.05)
    tip = iy >= H - 1
    c = np.where(tip[:, None], DAYGOLD if day else PHOTO, c)
    return c, ctx.ones(), np.where(tip, 0.6, 0.0)


def mat_gill(ctx):
    """Outside: skin with a pale trailing rim; inside (toward the neck): red filaments."""
    ix, iy, W, H = px.texel(ctx)
    p = _wp(ctx)
    n = ctx.wn if ctx.wn is not None else ctx.n
    inner = abs(n[0]) > 0.5 and np.sign(n[0]) != np.sign(p[:, 0].mean())
    if inner:
        c = px.quant(ctx, GILL, px.light(ctx) + 0.1 * ((iy % 2) == 0))
        return c, ctx.ones(), ctx.zeros()
    c = px.shade(ctx, SKIN, offset=-0.08)
    if px.side(ctx):
        c = np.where((ix == W - 1)[:, None] if ctx.face == "west" else (ix == 0)[:, None], SKIN[5], c)
    return c, ctx.ones(), ctx.zeros()


# ----------------------------------------------------------------------------- isopod chitin

def _photophores(ctx, c, g, row, every=3, offset=0):
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    dots = (iy == row) & (((ix + offset + ctx.seed) % every) == 0) & (ix > 0) & (ix < W - 1)
    c = np.where(dots[:, None], DAYGOLD if day else PHOTO, c)
    g = np.where(dots, 0.7 if day else 0.45, g)
    return c, g


def mat_plate(ctx):
    """Glossy black chitin: a bright wet rim along each upper edge, a gloss band, transverse
    growth lines, cold photophores along the trailing edge; white-gold cracks around the exit."""
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx, grad=0.14) - 0.12
    if px.side(ctx) and H >= 3:
        lv = lv + 0.42 * (iy == 0) + 0.12 * (iy == 1) - 0.08 * (iy == H - 1)
        lv = lv - 0.07 * ((iy % 2) == 0) * (iy > 1)
    elif ctx.face == "up":
        lv = lv + 0.2
    c = px.quant(ctx, CHITIN, lv)
    g = ctx.zeros()
    if px.side(ctx) and H >= 3:
        spec = (iy == 0) & (_h2(ix, 0, ctx.seed + 1) < 0.18)
        c = np.where(spec[:, None], px.col("#9fc2bd"), c)
    if day > 0.5:
        rim_ = (iy == 0) if px.side(ctx) else px.border(ctx, 1)
        c = np.where(rim_[:, None], SUN[2], c)
        g = np.where(rim_, 0.55, g)
    if ctx.face == "south" and H >= 5 and W >= 6:
        c, g = _photophores(ctx, c, g, H - 2, every=3)
    c, gl = warm(ctx, c, lv, 0.8)
    g = np.maximum(g, gl)
    # fractures and char around the exit wound (back faces only)
    n = ctx.wn if ctx.wn is not None else ctx.n
    if n[2] > 0.3:
        p = _wp(ctx)
        q2 = np.stack([p[:, 0], p[:, 1]], axis=1)
        best = np.full(ctx.N, 9.0)
        for pl in CRACKS_B:
            for a, b in zip(pl[:-1], pl[1:]):
                best = np.minimum(best, _seg_dist(q2, a, b))
        r = np.hypot(p[:, 0] - EXIT[0], p[:, 1] - EXIT[1])
        char = r < 1.9
        c = np.where(char[:, None], px.quant(ctx, EMBER, 0.3 + 0.3 * (r < 1.3)), c)
        on = (best < 0.28) & (r < 5.5)
        hot = np.clip(1 - r / 5.5, 0, 1)
        c = np.where(on[:, None], px.quant(ctx, SUN, 0.3 + 0.7 * hot), c)
        g = np.where(on, 0.5 + 0.45 * hot, np.where(char, 0.0, g))
    return c, ctx.ones(), g


def mat_spine(ctx):
    ix, iy, W, H = px.texel(ctx)
    blaze, open_, day = _P(ctx)
    c = px.shade(ctx, CHITIN, offset=0.08, up=0.3)
    tip = (iy == 0) if px.side(ctx) else np.zeros(ctx.N, bool)
    c = np.where(tip[:, None], DAYGOLD if day else PHOTO_DIM, c)
    return c, ctx.ones(), np.where(tip, 0.35, 0.0)


def mat_seam(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = px.quant(ctx, SUN, 0.6 + 0.3 * ((ix % 3) == 1))
    return c, ctx.ones(), np.full(ctx.N, 0.95)


def mat_greave(ctx):
    """Segmented shin armour: three overlapping bands, each with a wet upper rim."""
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx, grad=0.06) - 0.1
    if px.side(ctx):
        band = iy % 3
        lv = lv + 0.36 * (band == 0) - 0.1 * (band == 2)
    c = px.quant(ctx, CHITIN, lv)
    g = ctx.zeros()
    if day > 0.5 and px.side(ctx):
        rim_ = (iy % 3) == 0
        c = np.where(rim_[:, None], SUN[2], c)
        g = np.where(rim_, 0.45, g)
    return c, ctx.ones(), g


def mat_bracer(ctx):
    return mat_greave(ctx)


def mat_foot(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = skin_level(ctx, offset=0.0, rim_up=0.26, rough=0.05)
    c, g = skin_paint(ctx, lv, light=0.0)
    if ctx.face == "up" and W >= 6:
        scutes = ((iy % 3) == 0)
        c = np.where(scutes[:, None], SKIN[5], c)
    return c, ctx.ones(), g


def mat_claw(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = px.shade(ctx, CLAW, offset=0.05, up=0.25)
    if px.side(ctx) and H >= 2:
        c = np.where((iy == H - 1)[:, None], CLAW[5], c)
    return c, ctx.ones(), ctx.zeros()


def mat_fin(ctx):
    """Soft, torn fin membrane (cutout): dark rays fanning from the root, ragged trailing edge,
    a few holes.  Painted from world positions so both faces of the plane agree."""
    blaze, open_, day = _P(ctx)
    p = _wp(ctx)
    ix, iy, W, H = px.texel(ctx)
    u = (p[:, 2] - p[:, 2].min()) / max(np.ptp(p[:, 2]), 1e-6)            # 0 at the root edge -> 1 trailing
    v = (p[:, 1].max() - p[:, 1]) / max(np.ptp(p[:, 1]), 1e-6)             # 0 top -> 1 bottom
    qz = np.floor(p[:, 2] * 2 + 0.01)
    qy = np.floor(p[:, 1] * 2 + 0.01)
    tear = 0.58 + 0.25 * np.abs(np.sin(qy * 1.7)) + 0.12 * np.sin(qy * 0.6 + 1.0)
    keep = u < tear
    notch = (np.mod(qy, 5) == 2) & (u > tear - 0.3)
    holes = _hp(np.stack([qz, qy, qz * 0], axis=1), 2.0) < 0.05
    a = keep & ~notch & ~holes
    ray = np.mod(qy + np.floor(u * 3.0), 3) == 0
    c = np.where(ray[:, None], px.col("#1d2f33"), px.col("#091114"))
    c = np.where((u > tear - 0.12)[:, None] & keep[:, None], px.col("#22383a"), c)
    if day > 0.5:
        c = np.where(ray[:, None], px.col("#8a6a2c"), c)
    return c, a.astype(float), ctx.zeros()


def mat_web(ctx):
    p = _wp(ctx)
    qy = np.floor(p[:, 1] * 2 + 0.01)
    qz = np.floor(p[:, 2] * 2 + 0.01)
    scallop = (qy - qy.min()) < (1 + (np.mod(qz, 2) == 0))
    c = np.where(scallop[:, None], px.col("#162327"), px.col("#0c1517"))
    return c, (~scallop | (qy - qy.min() >= 1)).astype(float) * 0 + (qy - qy.min() >= (np.mod(qz, 2))).astype(float), ctx.zeros()


def mat_core(ctx):
    """The light shell at a wound: white-hot centre, gold ring, ember corners."""
    blaze, open_, day = _P(ctx)
    ix, iy, W, H = px.texel(ctx)
    cx, cy = (W - 1) / 2, (H - 1) / 2
    r = np.maximum(np.abs(ix - cx), np.abs(iy - cy)) / max(cx, 1e-6)
    rr = np.hypot(ix - cx, iy - cy) / max(cx, 1e-6)
    lvl = np.clip(1.05 - rr * 0.55, 0, 1)
    c = px.quant(ctx, SUN, lvl)
    corner = rr > 1.15
    c = np.where(corner[:, None], EMBER[3], c)
    g = np.where(corner, 0.2, np.clip(0.75 + 0.2 * (1 - rr) + 0.1 * blaze, 0, 1))
    if not px.side(ctx) and ctx.face != "north" and ctx.face != "south":
        g = np.full(ctx.N, 0.8)
    return c, ctx.ones(), g


def mat_core_hot(ctx):
    c = np.broadcast_to(SUN[5], (ctx.N, 3)).copy()
    return c, ctx.ones(), np.full(ctx.N, 1.0)


# ============================================================================= the sword (embedded and held)

def sword_materials():
    return {"s_blade": mat_s_blade, "s_ricasso": mat_s_ricasso, "s_hilt": mat_s_hilt, "s_sun": mat_s_sun,
            "s_grip": mat_s_grip, "s_pommel": mat_s_pommel}


def _sblaze(ctx):
    return max(ctx.params.get("blaze", 0.0), ctx.params.get("day", 0.0))


def mat_s_blade(ctx):
    """White-gold blade: pale edges, a white-hot fuller, slow heat bands along its length."""
    ix, iy, W, H = px.texel(ctx)
    b = _sblaze(ctx)
    wide = W >= 3 and H > W
    if wide:
        edge = (ix == 0) | (ix == W - 1)
        band = ((iy // 3) % 4) == 1
        c = np.where(edge[:, None], SUN[3], np.where(band[:, None], SUN[4], SUN[5]))
        g = np.where(edge, 0.72, 0.92)
    else:
        c = np.broadcast_to(SUN[3], (ctx.N, 3)).copy()
        c = np.where(((iy % 4) == 0)[:, None], SUN[2], c)
        g = np.full(ctx.N, 0.7)
    return c, ctx.ones(), np.clip(g + 0.1 * b, 0, 1)


SUN_GLYPH = ["..r..",
             ".oOo.",
             "rOWOr",
             ".oOo.",
             "..r.."]


def mat_s_ricasso(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = px.shade(ctx, SUN, offset=-0.15)
    g = np.full(ctx.N, 0.55)
    if W >= 5 and H >= 3:
        c, g = px.decal(ctx, c, ["r.r", ".O.", "r.r"], {"r": GOLD[3], "O": "#ffffff"}, "c", "c", glow=g,
                        glow_chars="O", glow_level=0.95)
    return c, ctx.ones(), g


def mat_s_hilt(ctx):
    """Gold rays of the guard and the collar: bright upper edges, darker undersides."""
    c = px.shade(ctx, GOLD, offset=0.08, up=0.2, down=0.12)
    return c, ctx.ones(), np.full(ctx.N, 0.35 + 0.2 * _sblaze(ctx))


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
        g = np.where(wire, 0.3, 0.0)
    else:
        g = ctx.zeros()
    return c, ctx.ones(), g


def mat_s_pommel(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = px.shade(ctx, GOLD, offset=0.1, up=0.25)
    centre = (np.abs(ix - (W - 1) / 2) < 0.6) & (np.abs(iy - (H - 1) / 2) < 0.6)
    c = np.where(centre[:, None], SUN[4], c)
    return c, ctx.ones(), np.where(centre, 0.9, 0.35)


def build_sword() -> Model:
    """The held sword (the same design as the one through his chest): root -> sword, grip
    centre at the origin, blade along +Y (broad faces front/back), ~30 px long."""
    m = Model("bathyas_sword", ppu=2.0, atlas_width=64)
    m.bone("root", None, (0, 0, 0))
    sw = m.bone("sword", "root", (0, 0, 0))
    sword_parts(m, sw.name, (0.0, 0.0, 0.0), flat="z", tip=25.75)
    sw.locators["blade_tip"] = (0.0, 25.75, 0.0)
    sw.locators["blade_mid"] = (0.0, 14.0, 0.0)
    sw.locators["guard"] = (0.0, 3.0, 0.0)
    m.pack()
    return m
