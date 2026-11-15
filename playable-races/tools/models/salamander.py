"""Race 001 - Aberrant Flora Salamander.

An amphibian whose tissues are fused with carnivorous / photosynthetic plant
organs.  Variants (one geometry each, shared atlas):
  base (stable) | bloom | dormant | predatory | rooted
"""
from __future__ import annotations

import math

import numpy as np

from kit.geo import Model
from kit.tex import Ctx, hx
from kit import noise as nz
from models.common import (humanoid, side_rot, fp_sleeves, ramp, bevel, face_light, mix3, desat,
                           clamp01, accents, mat_accent)

ID = "salamander"
VARIANTS = ["base", "bloom", "dormant", "predatory", "rooted"]
TEXTURES = {  # texture variant -> painter params
    "base": {"vivid": 0.35, "dry": 0.0, "pred": 0.0},
    "bloom": {"vivid": 1.0, "dry": 0.0, "pred": 0.0},
    "dormant": {"vivid": 0.0, "dry": 1.0, "pred": 0.0},
    "predatory": {"vivid": 0.45, "dry": 0.0, "pred": 1.0},
}
VARIANT_TEXTURE = {"base": "base", "bloom": "bloom", "dormant": "dormant", "predatory": "predatory", "rooted": "bloom"}

# plate hinge roll per variant (degrees outward); flower petal opening
PLATE_ROLL = {"base": 34, "bloom": 62, "dormant": 8, "predatory": 46, "rooted": 70}
PETAL_OPEN = {"base": 40, "bloom": 72, "dormant": 8, "predatory": 55, "rooted": 72}
GILL_FLARE = {"base": 0, "bloom": 10, "dormant": -14, "predatory": 22, "rooted": 8}
LOBE_OPEN = {"base": 12, "bloom": 16, "dormant": 4, "predatory": 58, "rooted": 10}


def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=512)
    humanoid(m)
    _legs(m)
    _torso(m)
    _plates(m)
    _arms(m)
    _head(m)
    _tail(m)
    fp_sleeves(m, "skin", width=4.8)
    accents(m, [
        ("c", "sternum", "torso", (0, 21.4, -2.45), (6.2, 3.0, 0.5)),
        ("c", "rsh", "r_arm_g", (-5.6, 23.6, 0.2), (5.0, 1.2, 5.2)),
        ("c", "lsh", "l_arm_g", (5.6, 23.6, 0.2), (5.0, 1.2, 5.2)),
        ("l", "r", "r_thigh", (-2.4, 9.4, -2.15), (3.8, 4.0, 0.5)),
        ("l", "l", "l_thigh", (2.4, 9.4, -2.15), (3.8, 4.0, 0.5)),
        ("f", "r", "r_shin", (-2.5, 4.3, -1.75), (3.0, 3.6, 0.5)),
        ("f", "l", "l_shin", (2.5, 4.3, -1.75), (3.0, 3.6, 0.5)),
    ])
    m.pack()
    return m


# ----------------------------------------------------------------------------- legs

def _legs(m: Model) -> None:
    for side, g, prefix in ((-1, "r_leg_g", "r"), (1, "l_leg_g", "l")):
        hx_ = 1.9 * side
        thigh = m.bone(f"{prefix}_thigh", g, (hx_, 12, 0), side_rot((0, 0, 7), side))
        m.box(thigh.name, (hx_ + 0.5 * side, 9.4, 0.4), (4.4, 6.0, 4.6), "skin")
        m.box(thigh.name, (hx_ + 0.6 * side, 11.6, 0.4), (4.9, 2.2, 5.0), "skin")       # hip mass
        knee = m.bone(f"{prefix}_shin", thigh.name, (hx_ + 0.5 * side, 6.6, 0.4), side_rot((-6, 0, -9), side))
        m.box(knee.name, (hx_ + 0.6 * side, 4.1, 0.1), (3.5, 5.2, 3.6), "skin")
        m.box(knee.name, (hx_ + 0.6 * side, 5.6, 1.6), (2.4, 1.6, 1.0), "gland")       # calf gland
        foot = m.bone(f"{prefix}_foot", knee.name, (hx_ + 0.6 * side, 1.6, 0.2), side_rot((4, 0, 2), side))
        m.box(foot.name, (hx_ + 0.7 * side, 0.75, -0.9), (5.0, 1.5, 5.6), "skin")
        # broad splayed toes with adhesive pads
        for k, (dx, ang, ln) in enumerate(((-1.8, 26, 2.7), (-0.6, 9, 3.2), (0.6, -9, 3.2), (1.8, -26, 2.6))):
            tx = hx_ + 0.7 * side + dx
            toe = m.bone(f"{prefix}_toe{k}", foot.name, (tx, 0.6, -3.5), (0, ang, 0))
            m.cube(toe.name, (tx - 0.55, 0.0, -3.6 - ln), (1.1, 0.9, ln), "skin")
            m.cube(toe.name, (tx - 0.75, 0.0, -4.55 - ln), (1.5, 0.95, 1.1), "pad")
        # retractable roots (only in the rooted form)
        roots = m.bone(f"{prefix}_roots", foot.name, (hx_ + 0.7 * side, 0.2, -0.8), only={"rooted"})
        for k, (dx, dz, rx, rz, ln) in enumerate(((-1.6, -2.2, 18, -14, 6.0), (1.4, -1.8, 12, 16, 5.0),
                                                   (0.0, 0.8, -16, 4, 6.5), (-1.0, 1.6, -22, -20, 4.5),
                                                   (1.6, 1.0, -10, 26, 4.0))):
            rb = m.bone(f"{prefix}_root{k}", roots.name, (hx_ + 0.7 * side + dx, 0.2, -0.8 + dz),
                        side_rot((rx, 0, rz), side), only={"rooted"})
            m.cube(rb.name, (hx_ + 0.7 * side + dx - 0.45, 0.2 - ln, -0.8 + dz - 0.45), (0.9, ln, 0.9), "root",
                   only={"rooted"})
            m.cube(rb.name, (hx_ + 0.7 * side + dx - 0.3, 0.2 - ln - 2.0, -0.8 + dz - 0.3), (0.6, 2.0, 0.6),
                   "root", only={"rooted"})


# ----------------------------------------------------------------------------- torso

def _torso(m: Model) -> None:
    t = m.bone("torso", "torso_g", (0, 12, 0), (4, 0, 0))
    # main trunk without its front face (a translucent membrane sits there)
    m.cube(t.name, (-4.6, 11.6, -2.2), (9.2, 12.9, 5.8), "skin", faces={"south", "east", "west", "up", "down"})
    m.cube(t.name, (-4.6, 11.6, -2.2), (9.2, 3.0, 0.01), "skin", faces={"north"})            # lower rim
    m.cube(t.name, (-4.6, 21.0, -2.2), (9.2, 3.5, 0.01), "skin", faces={"north"})            # chest rim
    m.cube(t.name, (-4.6, 14.6, -2.2), (1.4, 6.4, 0.01), "skin", faces={"north"})            # flank rims
    m.cube(t.name, (3.2, 14.6, -2.2), (1.4, 6.4, 0.01), "skin", faces={"north"})
    # abdominal cavity: dark wall, fluid sacs and vascular channels behind a membrane
    m.cube(t.name, (-3.2, 14.6, -0.6), (6.4, 6.4, 0.5), "inner", faces={"north"})
    for (cx, cy, w, h) in ((-1.5, 18.6, 2.6, 2.4), (1.5, 18.8, 2.4, 2.2), (0.0, 16.2, 3.0, 2.0),
                           (-1.9, 15.6, 1.4, 1.4), (1.9, 15.8, 1.3, 1.6)):
        m.box(t.name, (cx, cy, -1.25), (w, h, 1.1), "sac")
    for (cx, cy, w, h) in ((0, 17.7, 0.5, 5.4), (-0.9, 17.6, 2.4, 0.45), (0.9, 17.0, 2.4, 0.45)):
        m.box(t.name, (cx, cy, -0.95), (w, h, 0.5), "channel")
    m.cube(t.name, (-3.2, 14.6, -2.05), (6.4, 6.4, 0.0), "membrane", faces={"north"}, cutout=True)
    # shoulders / hunch, throat, spine ridge
    m.box(t.name, (0, 23.6, 0.9), (10.2, 2.4, 5.0), "skin")
    m.box(t.name, (0, 24.6, 1.9), (6.0, 1.6, 3.0), "skin")
    m.box(t.name, (0, 22.8, -2.0), (5.2, 1.6, 1.0), "belly")
    for k in range(5):
        m.box(t.name, (0, 23.4 - k * 2.4, 3.9), (1.2, 1.4, 1.0), "gland")
    m.box(t.name, (0, 12.2, 0.6), (8.6, 1.8, 5.2), "skin")    # pelvis
    t.locators["spores"] = (0, 24.5, 3.5)
    t.locators["belly"] = (0, 17.5, -2.5)


def _plates(m: Model) -> None:
    """Dorsal photosynthetic plates: hinged at the spine, roll outward to bloom."""
    rows = ((23.0, 8.2, 5.4), (19.8, 7.6, 5.0), (16.6, 6.4, 4.4), (13.8, 5.0, 3.6))
    for k, (y, ln, wd) in enumerate(rows):
        for side in (-1, 1):
            name = f"plate_{'r' if side < 0 else 'l'}{k}"
            px = 0.7 * side
            var = {v: ((0, 0, 0), side_rot((-8 - k * 4, 0, PLATE_ROLL[v]), side)) for v in VARIANTS}
            b = m.bone(name, "torso", (px, y, 3.6), side_rot((-8 - k * 4, 0, PLATE_ROLL["base"]), side))
            b.variant.update(var)
            x0 = px if side > 0 else px - ln
            m.cube(name, (x0, y - 0.45, 3.6 - wd / 2 + 0.6), (ln, 0.9, wd), "leaf")
            # leading glandular rim (sundew tentacles) as a cutout fringe
            xf = x0 + (ln if side > 0 else 0)
            m.cube(name, (xf - 0.0, y - 0.45, 3.6 - wd / 2 + 0.6), (0.0, 1.6, wd), "fringe", cutout=True,
                   faces={"east", "west"})


# ----------------------------------------------------------------------------- arms

def _arms(m: Model) -> None:
    for side, g, prefix in ((-1, "r_arm_g", "r"), (1, "l_arm_g", "l")):
        ax = 5.6 * side
        m.box(g, (ax, 21.2, 0.2), (4.4, 4.4, 4.6), "skin")                      # shoulder
        m.box(g, (ax, 17.6, 0.1), (3.6, 4.2, 3.7), "skin")                      # upper arm
        fore = m.bone(f"{prefix}_fore", g, (ax, 15.6, 0.1), side_rot((-6, 0, 0), side))
        m.box(fore.name, (ax, 13.6, 0.0), (3.3, 4.6, 3.4), "skin")
        # adhesive glands along the forearm
        for k, gy in enumerate((15.0, 13.6, 12.4)):
            m.box(fore.name, (ax + 1.7 * side, gy, -0.6 + k * 0.5), (0.7, 0.8, 0.8), "gland")
        # venus-trap lobes on the outer forearm (hinged, open in the predatory form)
        for lk, lz in ((0, -1), (1, 1)):
            lname = f"{prefix}_lobe{lk}"
            open_ = {v: ((0, 0, 0), (LOBE_OPEN[v] * lz * -1, 0, 0)) for v in VARIANTS}
            lb = m.bone(lname, fore.name, (ax + 1.75 * side, 14.0, 0.0 + 0.25 * lz),
                        (LOBE_OPEN["base"] * -lz, 0, 0))
            lb.variant.update(open_)
            m.cube(lname, (ax + 1.75 * side - 0.0, 11.9, 0.25 * lz if lz > 0 else -2.45),
                   (0.0, 4.4, 2.2), "lobe", cutout=True, faces={"east", "west"})
        # sticky tendrils hanging from the wrist
        for tk, (dx, dz, ln) in enumerate(((0.9, -1.2, 3.2), (-0.6, 1.1, 2.6))):
            tb = m.bone(f"{prefix}_tendril{tk}", fore.name, (ax + dx * side, 11.6, dz), (8 * (1 if tk else -1), 0, 6 * side))
            m.cube(tb.name, (ax + dx * side - 0.3, 11.6 - ln, dz - 0.3), (0.6, ln, 0.6), "tendril")
            m.cube(tb.name, (ax + dx * side - 0.45, 11.6 - ln - 0.9, dz - 0.45), (0.9, 0.9, 0.9), "dew",
                   only={"predatory", "bloom"})
            ext = m.bone(f"{prefix}_tendril{tk}x", tb.name, (ax + dx * side, 11.6 - ln, dz), (10, 0, 0),
                         only={"predatory"})
            m.cube(ext.name, (ax + dx * side - 0.25, 11.6 - ln - 3.0, dz - 0.25), (0.5, 3.0, 0.5), "tendril",
                   only={"predatory"})
        # broad hand with digit pads (holds items at the vanilla grip point)
        hand = m.bone(f"{prefix}_hand", fore.name, (ax, 11.4, 0.0))
        m.box(hand.name, (ax, 10.6, -0.2), (3.4, 2.0, 3.6), "skin")
        for k, (dz, ln) in enumerate(((-1.3, 2.2), (0.0, 2.6), (1.3, 2.1))):
            m.cube(hand.name, (ax - 0.45, 9.6 - ln + 1.0, -0.2 + dz - 0.45), (0.9, ln, 0.9), "skin")
            m.cube(hand.name, (ax - 0.6, 8.9 - ln + 1.0, -0.2 + dz - 0.6), (1.2, 0.9, 1.2), "pad")
        m.cube(hand.name, (ax + 1.2 * side - 0.4, 9.4, -2.3), (0.8, 1.6, 0.8), "skin")    # thumb


# ----------------------------------------------------------------------------- head

def _head(m: Model) -> None:
    h = m.bone("skull", "head_g", (0, 24.5, 1.0))
    h.variant.update({"dormant": ((0, 0, 0), (9, 0, 0)), "predatory": ((0, 0, 0), (-5, 0, 0))})
    # broad, flattened amphibian skull with a rounded, overhanging snout
    m.cube(h.name, (-5.6, 25.9, -6.0), (11.2, 3.3, 8.0), "skin")
    m.cube(h.name, (-4.9, 25.8, -8.2), (9.8, 3.0, 2.2), "skin")
    m.cube(h.name, (-3.8, 25.9, -9.3), (7.6, 2.5, 1.1), "skin")
    m.cube(h.name, (-3.6, 29.1, -5.2), (7.2, 0.6, 6.6), "skin")                  # flat crown
    m.cube(h.name, (-5.2, 26.3, 1.6), (10.4, 2.6, 1.6), "skin")                   # occiput
    m.cube(h.name, (-6.0, 25.3, -6.4), (12.0, 0.9, 7.6), "lip")                  # mouth reaching the cheeks
    m.cube(h.name, (-4.6, 25.3, -8.6), (9.2, 0.9, 2.2), "lip")
    for side in (-1, 1):
        # bulging dorsolateral eyes, set wide like a salamander's
        m.box(h.name, (4.7 * side, 29.3, -5.0), (3.2, 3.0, 3.2), "eye")
        m.box(h.name, (4.7 * side, 27.9, -5.0), (3.6, 0.8, 3.6), "skin")           # lower lid
        m.box(h.name, (1.3 * side, 28.0, -9.35), (0.9, 0.6, 0.5), "nostril")
        m.box(h.name, (5.4 * side, 27.2, -1.0), (0.7, 1.4, 3.0), "gland")           # parotoid ridge
    # lower jaw: hinged at the back, gapes in the predatory form
    j = m.bone("jaw", "skull", (0, 25.6, 1.4), (0, 0, 0))
    j.variant.update({"predatory": ((0, 0, 0), (16, 0, 0))})
    m.cube(j.name, (-5.6, 23.7, -8.3), (11.2, 1.7, 9.8), "skin")
    m.cube(j.name, (-4.6, 23.2, -7.6), (9.2, 0.6, 8.2), "belly")                 # gular pouch
    m.cube(j.name, (-5.0, 25.35, -8.0), (10.0, 0.1, 9.0), "mouth", faces={"up"})
    m.cube(h.name, (-5.0, 25.25, -8.2), (10.0, 0.1, 9.2), "mouth", faces={"down"})
    for side in (-1, 1):
        for k in range(4):
            m.box(j.name, (side * (1.2 + k * 1.1), 25.6, -8.2 + k * 0.5), (0.35, 0.5, 0.35), "tooth")
    h.locators["mouth"] = (0, 25.6, -9.8)
    # external gills: three feathery stalks per side with carnivorous fronds
    for side in (-1, 1):
        for k, (gy, rx, ry) in enumerate(((29.2, -38, 30), (27.6, -10, 42), (26.0, 16, 54))):
            name = f"gill_{'r' if side < 0 else 'l'}{k}"
            gb = m.bone(name, "skull", (5.2 * side, gy, 1.2), side_rot((rx, -ry, 0), side))
            gb.variant.update({v: ((0, 0, 0), side_rot((rx - GILL_FLARE[v] * 0.6, -ry - GILL_FLARE[v], 0), side))
                               for v in VARIANTS})
            m.cube(name, (5.2 * side - 0.5, gy - 0.5, 1.2), (1.0, 1.0, 6.4), "gill")
            m.cube(name, (5.2 * side, gy - 2.2, 2.2), (0.0, 4.4, 6.0), "frond", cutout=True, faces={"east", "west"})
            m.cube(name, (5.2 * side - 2.2, gy, 2.2), (4.4, 0.0, 6.0), "frond", cutout=True, faces={"up", "down"})


# ----------------------------------------------------------------------------- tail

def _tail(m: Model) -> None:
    segs = ((5.4, 4.4, 4.6), (4.2, 3.4, 4.4), (3.0, 2.5, 4.2), (2.0, 1.7, 4.0))
    parent, y, z = "tail_g", 12.8, 2.6
    for k, (w, h, ln) in enumerate(segs):
        b = m.bone(f"tail{k}", parent, (0, y, z), (12 if k == 0 else 5, 0, 0))
        m.cube(b.name, (-w / 2, y - h / 2, z), (w, h, ln), "skin")
        m.cube(b.name, (0, y + h / 2 - 0.2, z), (0.0, 1.8 + (3 - k) * 0.35, ln), "fin", cutout=True,
               faces={"east", "west"})
        m.cube(b.name, (0, y - h / 2 - 1.3, z + 0.4), (0.0, 1.4, ln - 0.6), "fin", cutout=True,
               faces={"east", "west"})
        parent, y, z = b.name, y - 0.2, z + ln
    fl = m.bone("tail_flower", parent, (0, y, z))
    m.box(fl.name, (0, y, z + 0.6), (1.8, 1.8, 1.4), "calyx")
    for k in range(5):
        ang = 72 * k
        pb = m.bone(f"petal{k}", fl.name, (0, y, z + 1.2), (0, 0, ang))
        pb.variant.update({v: ((0, 0, 0), None) for v in VARIANTS})
        # each petal leans outward from the tail axis by PETAL_OPEN (child bone)
        lean = m.bone(f"petal{k}_l", pb.name, (0, y + 0.6, z + 1.2), (-PETAL_OPEN["base"], 0, 0))
        lean.variant.update({v: ((0, 0, 0), (-PETAL_OPEN[v], 0, 0)) for v in VARIANTS})
        m.cube(lean.name, (-1.4, y + 0.6, z + 1.2), (2.8, 0.0, 4.2), "petal", cutout=True, faces={"up", "down"})
    m.box(fl.name, (0, y, z + 2.0), (0.8, 0.8, 1.6), "stamen")
    fl.locators["pollen"] = (0, y, z + 3.0)


# ============================================================================= materials

def materials():
    return {
        "skin": mat_skin, "belly": mat_belly, "lip": mat_lip, "mouth": mat_mouth, "nostril": mat_mouth,
        "eye": mat_eye, "gland": mat_gland, "pad": mat_pad, "inner": mat_inner, "sac": mat_sac,
        "channel": mat_channel, "membrane": mat_membrane, "leaf": mat_leaf, "fringe": mat_fringe,
        "gill": mat_gill, "frond": mat_frond, "lobe": mat_lobe, "tendril": mat_tendril, "dew": mat_dew,
        "fin": mat_fin, "calyx": mat_calyx, "tooth": mat_tooth, "accent": mat_accent, "petal": mat_petal, "stamen": mat_stamen, "root": mat_root,
    }


def _P(ctx):
    return ctx.params.get("vivid", 0.3), ctx.params.get("dry", 0.0), ctx.params.get("pred", 0.0)


def mat_skin(ctx: Ctx):
    vivid, dry, pred = _P(ctx)
    p = ctx.p
    mott = nz.fbm(p, 0.22, 3, seed=3)
    base = ramp([(0.0, "#142416"), (0.40, "#213a21"), (0.70, "#315232"), (1.0, "#4a7038")], mott)
    fine = nz.fbm(p, 1.1, 2, seed=4)
    base = base * (0.93 + 0.12 * fine)[:, None]
    base = mix3(base, base * np.array([0.85, 1.25, 0.8]), vivid * 0.6)
    # symbiotic algae spots (spotted-salamander nod)
    f1, f2, cid = nz.worley(p, 0.30, seed=11)
    spot = (f1 < 0.20) & (cid < 0.30)
    spotc = mix3(hx("#7f9c2c"), hx("#b9d84a"), vivid)
    base = np.where(spot[:, None], mix3(base, spotc, 0.85), base)
    # purple-red vascular network under the skin
    r = nz.ridged(nz.warp(p, 1.4, 0.18, seed=5), 0.36, 3, seed=8)
    vein = nz.smoothstep(0.86, 0.95, r)
    veinc = mix3(hx("#5d1f43"), hx("#b5122e"), pred)
    base = mix3(base, veinc, vein * (0.75 + 0.25 * pred))
    # wet specular glints
    glint = (nz.hash_points(p, 0.5, 21) < 0.012 * (1 - dry)) & (ctx.n[1] > 0.5)
    base = np.where(glint[:, None], mix3(base, hx("#d6f5cf"), 0.7), base)
    # dry: dull, chalky, cracked
    if dry > 0:
        base = desat(base, 0.55 * dry) * (1 + 0.25 * dry) + hx("#2a2416") * 0.15 * dry
        cr = (f2 - f1) < 0.05
        base = np.where(cr[:, None], base * (1 - 0.45 * dry), base)
    # pale ventral side
    if ctx.face == "down":
        base = mix3(base, hx("#9c9070"), 0.55)
    base = bevel(ctx, face_light(ctx, base), 0.18, 0.7)
    glow = vein * 0.30 * pred
    return base, ctx.ones(), glow


def mat_belly(ctx):
    vivid, dry, pred = _P(ctx)
    n = nz.fbm(ctx.p, 0.8, 3, seed=2)
    c = ramp([(0, "#8d7d62"), (0.5, "#c6b38f"), (1, "#e2d0ad")], n)
    c = mix3(c, hx("#d79a92"), 0.18 + 0.2 * pred)
    wr = (np.sin(ctx.p[:, 1] * 5.0 + n * 3) > 0.85)
    c = np.where(wr[:, None], c * 0.86, c)
    c = desat(c, 0.4 * dry)
    return bevel(ctx, c, 0.12), ctx.ones(), ctx.zeros()


def mat_lip(ctx):
    vivid, dry, pred = _P(ctx)
    c = mix3(hx("#2d1d22"), hx("#5a2032"), 0.5 + 0.5 * pred)
    n = nz.fbm(ctx.p, 1.2, 2, seed=4)
    c = c * (0.85 + 0.3 * n)[:, None]
    return c, ctx.ones(), ctx.zeros()


def mat_mouth(ctx):
    vivid, dry, pred = _P(ctx)
    n = nz.fbm(ctx.p, 1.5, 2, seed=6)
    c = mix3(hx("#2a070d"), hx("#7a1424"), n * (0.6 + 0.4 * pred))
    return c, ctx.ones(), ctx.zeros() + 0.12 * pred


def mat_eye(ctx):
    vivid, dry, pred = _P(ctx)
    socket = mix3(hx("#1a2316"), hx("#26341f"), nz.fbm(ctx.p, 1, 2))
    out = socket.copy()
    glow = ctx.zeros()
    if ctx.face in ("north", "east", "west", "up"):
        u = ctx.s / ctx.fw - 0.5
        v = ctx.t / ctx.fh - 0.5
        rr = np.sqrt(u * u + v * v)
        iris = rr < 0.42
        irc = ramp([(0, "#ffd34a"), (0.6, "#e59a14"), (1.0, "#8f4f06")], rr / 0.42)
        if dry > 0:
            irc = desat(irc, 0.45 * dry)
        out = np.where(iris[:, None], irc, out)
        pupil = (np.abs(v) < 0.09) & (np.abs(u) < 0.30)
        out = np.where(pupil[:, None], hx("#0b0606"), out)
        hl = ((u + 0.17) ** 2 + (v + 0.17) ** 2) < 0.012
        out = np.where(hl[:, None], hx("#fff6dc"), out)
        glow = np.where(iris & ~pupil, 0.35 + 0.15 * vivid, 0.0)
    return out, ctx.ones(), glow


def mat_gland(ctx):
    vivid, dry, pred = _P(ctx)
    c = mix3(hx("#6e2a35"), hx("#c4334a"), 0.4 + 0.6 * pred)
    hl = nz.hash_points(ctx.p, 0.5, 9) < 0.18
    c = np.where(hl[:, None], mix3(c, hx("#ffd7de"), 0.6), c)
    c = desat(c, 0.5 * dry)
    return bevel(ctx, c, 0.25, 0.4), ctx.ones(), ctx.zeros() + 0.18 * (0.5 * vivid + pred) * (1 - dry)


def mat_pad(ctx):
    vivid, dry, pred = _P(ctx)
    n = nz.fbm(ctx.p, 2.0, 2, seed=12)
    c = mix3(hx("#6f7a45"), hx("#a7ad6c"), n)
    return bevel(ctx, desat(c, 0.4 * dry), 0.2, 0.4), ctx.ones(), ctx.zeros()


def mat_inner(ctx):
    n = nz.fbm(ctx.p, 0.9, 3, seed=14)
    c = mix3(hx("#1d0609"), hx("#4a121b"), n)
    return c, ctx.ones(), ctx.zeros()


def mat_sac(ctx):
    vivid, dry, pred = _P(ctx)
    u = ctx.local
    d = np.sqrt(((u[:, 0] - 0.5) ** 2) + ((u[:, 1] - 0.5) ** 2))
    c = ramp([(0, "#ffd0d8"), (0.35, "#ff6a86"), (0.7, "#b71f45"), (1, "#5c0d22")], d * 1.6)
    c = mix3(c, desat(c, 0.7) * 0.7, dry)
    glow = clamp01(0.55 - d) * (0.6 + 0.4 * vivid) * (1 - 0.7 * dry)
    return c, ctx.ones(), glow


def mat_channel(ctx):
    vivid, dry, pred = _P(ctx)
    c = mix3(hx("#c2324d"), hx("#ff7a3d"), vivid * 0.4)
    return c, ctx.ones(), ctx.zeros() + 0.45 * (1 - dry)


def mat_membrane(ctx):
    vivid, dry, pred = _P(ctx)
    p = ctx.p
    f1, f2, cid = nz.worley(p * np.array([1, 1.4, 1]), 0.75, seed=31)
    window = (f2 - f1) > 0.17
    c = mix3(hx("#b9a98f"), hx("#e8d4b9"), nz.fbm(p, 1.2, 2, 4))
    rim = (f2 - f1) < 0.09
    c = np.where(rim[:, None], mix3(c, hx("#8e2442"), 0.75), c)
    alpha = np.where(window, 0.0, 1.0)
    return desat(c, 0.4 * dry), alpha, ctx.zeros()


def _leaf_colors(vivid, dry):
    top = mix3(hx("#3f8a2a"), hx("#6fd844"), vivid)
    top = mix3(top, hx("#6b6430"), dry)
    edge = mix3(hx("#5d8c2a"), hx("#a8e05a"), vivid)
    edge = mix3(edge, hx("#7a5a2a"), dry)
    return top, edge


def mat_leaf(ctx):
    vivid, dry, pred = _P(ctx)
    top, edge = _leaf_colors(vivid, dry)
    lx, lz = ctx.local[:, 0], ctx.local[:, 2]
    ax = np.abs(ctx.p[:, 0])
    along = np.clip((ax - 0.6) / 6.0, 0, 1)                      # 0 at spine, 1 at tip
    across = np.abs(lz - 0.5) * 2
    c = mix3(top, edge, along * 0.7 + across * 0.3)
    mid = across < 0.10
    veins = (np.abs(np.sin((along * 9.0 - across * 3.2) * math.pi)) < 0.12) & (across > 0.1)
    vcol = mix3(hx("#9c2b3e"), hx("#c8f070"), 0.35 + 0.3 * vivid)
    c = np.where((mid | veins)[:, None], mix3(c, vcol, 0.65), c)
    # sundew glands along the rim with dew drops
    rim = across > 0.80
    gl = rim & (nz.hash_points(ctx.p, 0.5, 33) < 0.45)
    c = np.where(gl[:, None], mix3(hx("#c41d33"), hx("#ff8fa0"), 0.2), c)
    dew = gl & (nz.hash_points(ctx.p, 0.5, 34) < 0.35)
    c = np.where(dew[:, None], hx("#f4fff4"), c)
    if ctx.face == "down":
        c = mix3(c, hx("#93ad6a"), 0.35)
    if ctx.face in ("east", "west", "north", "south"):
        c = c * 0.75
    if dry > 0:
        burn = (along > 0.75) & (nz.fbm(ctx.p, 1.3, 2, 5) > 0.45)
        c = np.where(burn[:, None], mix3(c, hx("#4a3218"), 0.7 * dry), c)
    glow = np.where(dew, 0.55 * (1 - dry), 0.0) + np.where(mid & (ctx.face == "up"), 0.12 * vivid, 0.0)
    return bevel(ctx, c, 0.12, 0.5), ctx.ones(), glow


def mat_fringe(ctx):
    vivid, dry, pred = _P(ctx)
    # glandular tentacles: thin vertical hairs with red knobs at the tips
    s = ctx.s
    hair = (np.mod(s * 2.0, 1.0) < 0.38)
    tip = ctx.t < 0.45
    alpha = np.where(hair, 1.0, 0.0)
    c = np.where(tip[:, None], mix3(hx("#d01f3b"), hx("#ff9db0"), 0.25), mix3(hx("#7d2f3a"), hx("#5f8a2b"), 0.4))
    c = desat(c, 0.5 * dry)
    return c, alpha, ctx.zeros()


def mat_gill(ctx):
    vivid, dry, pred = _P(ctx)
    n = nz.fbm(ctx.p, 1.0, 2, seed=40)
    c = mix3(hx("#5a1f37"), hx("#a1355a"), n)
    c = mix3(c, hx("#c11e3c"), 0.5 * pred)
    c = desat(c, 0.5 * dry)
    return bevel(ctx, c, 0.2, 0.4), ctx.ones(), ctx.zeros()


def mat_frond(ctx):
    vivid, dry, pred = _P(ctx)
    u = ctx.s / ctx.fw
    v = ctx.t / ctx.fh
    # lobed leaf silhouette (pinnate) with glandular filaments
    lob = 0.36 + 0.12 * np.sin(u * math.pi * 5) ** 2
    inside = np.abs(v - 0.5) < lob * np.sin(np.clip(u, 0, 1) * math.pi) ** 0.6
    hairs = (np.abs(v - 0.5) < lob + 0.12) & (np.mod(u * 9, 1) < 0.22) & ~inside
    alpha = np.where(inside | hairs, 1.0, 0.0)
    c = mix3(hx("#3c7f2a"), hx("#7cd04a"), vivid * 0.8)
    c = mix3(c, hx("#7d2a3e"), 0.3 + 0.4 * pred)
    c = np.where(hairs[:, None], hx("#d0233d"), c)
    c = mix3(c, hx("#6a5a30"), dry * 0.7)
    return c, alpha, ctx.zeros()


def mat_lobe(ctx):
    vivid, dry, pred = _P(ctx)
    u = ctx.s / ctx.fw
    v = ctx.t / ctx.fh
    # kidney-shaped trap lobe with interlocking cilia along the rim
    d = ((u - 0.5) / 0.48) ** 2 + ((v - 0.5) / 0.5) ** 2
    body = d < 0.78
    cilia = (d >= 0.78) & (d < 1.25) & (np.mod((np.arctan2(v - 0.5, u - 0.5) + 4) * 6.0, 1.0) < 0.33)
    alpha = np.where(body | cilia, 1.0, 0.0)
    inner = ramp([(0, "#ff4a5c"), (0.6, "#b0122c"), (1, "#3f7f2a")], d)
    outer = mix3(hx("#2f6324"), hx("#5aa53a"), vivid)
    c = inner if ctx.face == ("west" if ctx.p[0, 0] < 0 else "east") else outer
    c = np.where(cilia[:, None], hx("#6fa83a"), c)
    c = desat(c, 0.5 * dry)
    return c, alpha, ctx.zeros()


def mat_tendril(ctx):
    vivid, dry, pred = _P(ctx)
    c = mix3(hx("#476d26"), hx("#8a2a3d"), ctx.local[:, 1] * 0.8 + 0.2 * pred)
    return desat(c, 0.5 * dry), ctx.ones(), ctx.zeros()


def mat_tooth(ctx):
    return mix3(hx("#e8e2c8"), hx("#fffbe8"), ctx.local[:, 1]), ctx.ones(), ctx.zeros()


def mat_dew(ctx):
    c = mix3(hx("#e9fff2"), hx("#9be8c9"), nz.fbm(ctx.p, 2, 2))
    return c, ctx.ones(), ctx.zeros() + 0.6


def mat_fin(ctx):
    vivid, dry, pred = _P(ctx)
    u = ctx.s / ctx.fw
    v = ctx.t / ctx.fh
    edge = 0.25 + 0.75 * np.abs(np.sin(u * math.pi * 3.0))
    inside = v < edge * 0.92 + 0.08 if ctx.face else v
    alpha = np.where(inside, 1.0, 0.0)
    c = mix3(hx("#2f6a28"), hx("#73c548"), vivid * 0.8 + (1 - v) * 0.2)
    rib = np.mod(u * 7, 1) < 0.14
    c = np.where(rib[:, None], mix3(c, hx("#8c2a40"), 0.5), c)
    c = mix3(c, hx("#6a5a30"), dry * 0.7)
    return c, alpha, ctx.zeros()


def mat_calyx(ctx):
    vivid, dry, pred = _P(ctx)
    c = mix3(hx("#2e5a20"), hx("#4f8a2e"), nz.fbm(ctx.p, 1.5, 2))
    return bevel(ctx, desat(c, 0.5 * dry), 0.2, 0.4), ctx.ones(), ctx.zeros()


def mat_petal(ctx):
    vivid, dry, pred = _P(ctx)
    u = ctx.s / ctx.fw
    v = ctx.t / ctx.fh
    d = ((u - 0.5) / 0.5) ** 2 + ((v - 0.55) / 0.55) ** 2
    alpha = np.where(d < 1.0, 1.0, 0.0)
    c = ramp([(0, "#fff1f6"), (0.5, "#ff7fc0"), (1, "#a3125e")], np.clip(v * 1.1, 0, 1))
    c = mix3(c, hx("#7a5a50"), dry * 0.75)
    vein = np.abs(u - 0.5) < 0.05
    c = np.where(vein[:, None], c * 0.8, c)
    return c, alpha, ctx.zeros()


def mat_stamen(ctx):
    vivid, dry, pred = _P(ctx)
    c = mix3(hx("#ffe36b"), hx("#fff7c4"), nz.fbm(ctx.p, 2, 2))
    return c, ctx.ones(), ctx.zeros() + 0.7 * (1 - 0.8 * dry)


def mat_root(ctx):
    n = nz.fbm(ctx.p * np.array([3, 0.6, 3]), 1.2, 3, seed=50)
    c = ramp([(0, "#2a1c10"), (0.5, "#5a3d22"), (1, "#7d6a3a")], n)
    c = mix3(c, hx("#4b6b2a"), clamp01(ctx.p[:, 1] + 1.5) * 0.4)
    return bevel(ctx, c, 0.2, 0.3), ctx.ones(), ctx.zeros()
