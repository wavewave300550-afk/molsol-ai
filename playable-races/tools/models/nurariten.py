"""Race 006 - Nurariten (นูราริเทน), the Uninvited Sovereign.  UNIQUE race.  (v1.2 redesign)

The yokai Nurarihyon - the gourd-headed elder who walks into a house at its busiest
hour and is taken for its master - as a sovereign of the Heian celestial court.

Design rules (see docs/CREATIVE.md): a tall, narrow, ordered silhouette; ivory, aged
gold and vermilion with black lacquer for weight; gold only on real edges; long
court sleeves whose pockets swing a beat late; a two-lobed gourd head under a still
ivory mask; and ONE halo - six gilt lintel beams and four vermilion seals - that
reassembles itself into the torii of the Uninvited Temple (court) and the gate of
the throne-palace (throne).

Variants: base | nocturne (night radiance) | edict | court | throne.
Helper models: the celestial gate, the heralds and the procession columns.
"""
from __future__ import annotations

import math

import numpy as np

from kit.geo import Model, rot_matrix
from kit.tex import hx
from kit import pixel as px
from models.common import accents, ellipsoid, fp_sleeves, humanoid, mat_accent

ID = "nurariten"
VARIANTS = ["base", "nocturne", "edict", "court", "throne"]
TEXTURES = {
    "base": {"radiant": 0.0, "night": 0.0},
    "nocturne": {"radiant": 0.35, "night": 1.0},
    "radiant": {"radiant": 1.0, "night": 0.0},
}
VARIANT_TEXTURE = {"base": "base", "nocturne": "nocturne", "edict": "radiant", "court": "radiant", "throne": "radiant"}
GRAND = {"court", "throne"}
HALO = 6                      # gilt lintel beams in the halo
SEALS = 4
HALO_C = (0.0, 31.0, 8.5)     # halo centre (behind the head)
APOTHEM = 6.0                 # beam distance from the halo centre
BEAM = 5.0                    # beam length
H = 4.6                       # how far the hands hide inside the sleeves

# palettes (dark -> light, shadows cool, highlights warm)
IVORY = px.pal("#7d7482", "#a69c95", "#cdc2ad", "#e8dfca", "#f7f1e4")
MOON = px.pal("#5a6384", "#8a95b4", "#b7c1d8", "#dbe2ef", "#f2f6fc")
GOLD = px.pal("#56380f", "#87601f", "#b8893a", "#dcb35d", "#f5de9c")
VERM = px.pal("#3d0d0a", "#6b1712", "#9b2716", "#c2391f", "#dc5a34")
LACQ = px.pal("#0a0707", "#191210", "#2a201c", "#43352e")
INDIGO = px.pal("#141a33", "#25305a", "#3b4b85")
MASK = px.pal("#a29a90", "#d2cbbf", "#eee9df", "#fbf8f1", "#ffffff")
SKIN = px.pal("#8d837d", "#bbb0a3", "#ded5c6", "#f0eade", "#faf6ee")


def _rz(deg):
    return rot_matrix((0, 0, deg))


def _beam_center(rz_deg):
    """Where a halo beam's centre lands for a bone rotation rz about the halo centre."""
    return np.array(HALO_C) + _rz(rz_deg) @ np.array([0.0, APOTHEM, 0.0])


SEAL_R = 8.75


def _seal_center(rz_deg):
    return np.array(HALO_C) + _rz(rz_deg) @ np.array([0.0, SEAL_R, -0.2])


# court / throne: where each beam goes (centre, rotation) - the halo becomes a torii
GATE_Z = 9.5
PILLAR_X = 9.0
BEAM_GATE = {
    0: ((0.0, 37.0, GATE_Z), 0.0),                 # kasagi, centre
    1: ((PILLAR_X, 37.6, GATE_Z), -10.0),          # kasagi, end swept up (+X)
    5: ((-PILLAR_X, 37.6, GATE_Z), 10.0),          # kasagi, end swept up (-X)
    3: ((0.0, 32.5, GATE_Z), 0.0),                 # nuki (tie beam)
    2: ((PILLAR_X, 34.0, GATE_Z), 90.0),           # pillar head (+X)
    4: ((-PILLAR_X, 34.0, GATE_Z), -90.0),         # pillar head (-X)
}
SEAL_GATE = {
    0: ((0.0, 34.75, GATE_Z - 0.75), 0.0),         # the plaque between kasagi and nuki
    1: ((PILLAR_X, 21.0, GATE_Z - 1.0), 0.0),
    2: ((-PILLAR_X, 21.0, GATE_Z - 1.0), 0.0),
    3: ((0.0, 32.5, GATE_Z - 0.75), 0.0),
}


def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=512)
    humanoid(m)
    _legs(m)
    _robe(m)
    _arms(m)
    _head(m)
    _halo(m)
    _gate(m)
    _throne(m)
    fp_sleeves(m, "sleeve", width=5.0)
    accents(m, [
        ("c", "breast", "robe", (0, 20.0, -2.5), (5.0, 4.0, 0.5)),
        ("c", "rsh", "r_wing", (-6.0, 24.0, 0.25), (3.5, 0.5, 4.0)),
        ("c", "lsh", "l_wing", (6.0, 24.0, 0.25), (3.5, 0.5, 4.0)),
        ("l", "r", "r_leg_g", (-4.6, 8.0, 0.0), (0.5, 5.0, 3.5)),
        ("l", "l", "l_leg_g", (4.6, 8.0, 0.0), (0.5, 5.0, 3.5)),
        ("f", "r", "r_leg_g", (-2.1, 1.25, -3.0), (2.5, 0.5, 1.0)),
        ("f", "l", "l_leg_g", (2.1, 1.25, -3.0), (2.5, 0.5, 1.0)),
    ])
    m.pack()
    return m


# ----------------------------------------------------------------------------- legs: hakama, clogs, the parting robe hem

def _legs(m: Model) -> None:
    for s, g, p in ((-1, "r_leg_g", "r"), (1, "l_leg_g", "l")):
        m.box(g, (s * 2.25, 8.0, 0.0), (4.5, 9.0, 5.0), "hakama")                       # wide pleated trouser
        m.box(g, (s * 2.4, 2.25, 0.0), (5.0, 3.5, 5.5), "hakama")                       # flared hem
        m.box(g, (s * 2.1, 0.5, -1.25), (3.0, 1.0, 4.5), "geta")                        # lacquered clog
        m.bones[g].locators[f"{p}_step"] = (s * 2.1, 0.2, -1.0)
        # outer robe: front, back and side hem panels ride on the legs and part as they step
        f = m.bone(f"{p}_hem_f", g, (s * 2.5, 14.5, -3.0), (-8.0, 0.0, -s * 5.0))
        m.box(f.name, (s * 2.5, 7.75, -3.0), (5.0, 13.5, 0.5), "robe_hem")
        b = m.bone(f"{p}_hem_b", g, (s * 2.5, 14.5, 3.0), (11.0, 0.0, -s * 5.0))
        m.box(b.name, (s * 2.5, 7.625, 3.0), (5.0, 13.75, 0.5), "robe_hem")
        sd = m.bone(f"{p}_hem_s", g, (s * 4.75, 14.5, 0.0), (0.0, 0.0, -s * 10.0))
        m.box(sd.name, (s * 4.75, 8.25, 0.0), (0.5, 12.5, 5.0), "robe_hem")


# ----------------------------------------------------------------------------- the court robe

def _robe(m: Model) -> None:
    t = m.bone("robe", "torso_g", (0, 12, 0))
    m.box(t.name, (0, 13.25, 0.0), (7.0, 2.5, 5.0), "hakama")                        # under-robe at the waist
    m.box(t.name, (0, 15.25, 0.0), (7.5, 1.5, 5.5), "belt")                          # black lacquer court belt
    m.box(t.name, (0, 19.75, 0.0), (7.0, 7.5, 4.5), "chest")                         # outer robe, crossed collar
    # layered collars around the long neck
    m.box(t.name, (0, 23.875, 0.25), (4.5, 0.75, 4.0), "gold")
    m.box(t.name, (0, 24.625, 0.25), (4.0, 0.75, 3.5), "vermilion")
    m.box(t.name, (0, 25.375, 0.25), (3.5, 0.75, 3.0), "robe")
    # two vermilion cords with gold beads hanging from the belt
    for x in (-1.25, 1.25):
        m.box(t.name, (x, 12.25, -2.9), (0.5, 4.0, 0.5), "vermilion")
        m.box(t.name, (x, 10.0, -2.9), (1.0, 1.0, 1.0), "gold")
    # stiff upswept shoulder wings
    for s, p in ((-1, "r"), (1, "l")):
        w = m.bone(f"{p}_wing", t.name, (s * 3.5, 23.25, 0.0), (0.0, 0.0, -s * 12.0))
        w.variant.update({"court": ((0, 0, 0), (0.0, 0.0, -s * 20.0)), "throne": ((0, 0, 0), (0.0, 0.0, -s * 20.0))})
        m.box(w.name, (s * 6.0, 23.25, 0.25), (5.0, 1.0, 5.5), "wing")
    t.locators["chest"] = (0, 20.0, -2.6)
    t.locators["feet"] = (0, 0.2, 0)


# ----------------------------------------------------------------------------- sleeves and hands

def _arms(m: Model) -> None:
    for s, g, p in ((-1, "r_arm_g", "r"), (1, "l_arm_g", "l")):
        sl = m.bone(f"{p}_sleeve", g, (s * 5.0, 22.5, 0.0))
        sl.variant.update({"court": ((0, 0, 0), (0.0, 0.0, -s * 8.0)), "edict": ((0, 0, 0), (-10.0, 0.0, -s * 4.0))})
        m.box(sl.name, (s * 6.0, 19.0, 0.0), (4.5, 7.0, 5.0), "sleeve")              # upper sleeve
        m.box(sl.name, (s * 6.25, 13.5, 0.0), (5.0, 4.0, 6.0), "cuff")               # bell with the layered cuff
        tm = m.bone(f"{p}_tamoto", sl.name, (s * 6.25, 12.0, 1.0))
        m.box(tm.name, (s * 6.25, 8.25, 1.25), (4.5, 7.5, 3.5), "tamoto")             # the hanging sleeve pocket
        # the hand rests concealed inside the sleeve; it is drawn out to hold an item or issue a decree
        ax = s * 6.0
        hand = m.bone(f"{p}_hand", g, (ax, 11.2 + H, -1.5))
        hand.variant.update({v: ((0, -H, 0), None) for v in ("edict", "court", "throne")})
        m.box(hand.name, (ax, 10.0 + H, -1.5), (1.5, 2.0, 1.5), "skin")
        for k in range(4):
            fz = -2.05 + k * 0.38
            f = m.bone(f"{p}_finger{k}", hand.name, (ax, 9.0 + H, fz))
            ln = (2.5, 3.0, 2.75, 2.25)[k]
            m.cube(f.name, (ax - 0.15, 9.0 + H - ln, fz - 0.15), (0.3, ln, 0.3), "skin")
            m.cube(f.name, (ax - 0.175, 9.0 + H - ln - 0.5, fz - 0.175), (0.35, 0.5, 0.35), "gold")   # nail guard
        th = m.bone(f"{p}_thumb", hand.name, (ax - s * 0.7, 9.6 + H, -1.9), (0.0, 0.0, -s * 25.0))
        m.cube(th.name, (ax - s * 0.7 - 0.15, 8.1 + H, -2.05), (0.3, 1.5, 0.3), "skin")
        hand.locators[f"{p}_fingertip"] = (ax, 5.5 + H, -1.5)


# ----------------------------------------------------------------------------- the gourd head and the mask

CRANIUM_PIVOT = (0.0, 29.5, 0.5)
# (centre x, y, z, width, height, depth): a stepped dome that sweeps up and back
CRANIUM_BOXES = [
    (0.0, 32.0, 0.25, 5.5, 3.5, 5.0),     # the great bald dome above the brow
    (0.0, 31.75, 3.5, 5.0, 3.0, 2.0),     # back of the skull
    (0.0, 31.75, 5.25, 4.0, 2.0, 1.5),    # the gourd tapering behind
    (0.0, 31.5, 6.5, 2.5, 1.0, 1.0),      # tip
]
FACE_C = (0.0, 28.0, -0.25)


def _cranium_center():
    return np.array([0.0, 31.5, 3.0])


def _head(m: Model) -> None:
    sk = m.bone("skull", "head_g", (0, 25.0, 0.0))
    sk.variant.update({"throne": ((0, 0.4, 0), (-4, 0, 0))})
    m.box(sk.name, (0, 25.5, 0.25), (2.5, 2.0, 2.5), "skin_lo")                       # long neck
    m.box(sk.name, FACE_C, (4.5, 4.5, 4.0), "mask", ppu=4.0)                           # the mask-like face
    m.box(sk.name, (0, 27.75, 1.0), (4.0, 4.0, 3.0), "skin_lo")                        # cheeks and jaw, back
    # the gourd's upper lobe: a stepped dome sweeping up and back
    cr = m.bone("cranium", sk.name, CRANIUM_PIVOT)
    for k, (x, y, z, w, h, d) in enumerate(CRANIUM_BOXES):
        if k < 2:   # dome and back of the skull: rounded (cross + core) so they read round from every side
            ellipsoid(m, cr.name, (x, y, z), (w, h, d), "skin_hi", a=0.7, b=0.9)
        else:
            m.box(cr.name, (x, y, z), (w, h, d), "skin_hi")
    # a fine gold diadem across the brow with a vermilion jewel
    m.box(sk.name, (0, 30.5, -2.5), (5.5, 0.5, 0.5), "gold")
    m.box(sk.name, (0, 31.0, -2.6), (1.0, 1.0, 0.5), "jewel")
    # eyelids: a thin mask-coloured strip above the eyes, scaled down over them to blink
    lid = m.bone("lid", sk.name, (0, 28.1, -2.32))
    m.cube(lid.name, (-2.0, 28.0, -2.4), (4.0, 0.1, 0.1), "lidmat")      # scale y x8.5 covers both eyes
    sk.locators["eyes"] = (0, 28.4, -2.6)
    sk.locators["crown"] = (0, 33.5, 2.0)


# ----------------------------------------------------------------------------- the halo (six gilt beams + four seals)

def _halo(m: Model) -> None:
    halo = m.bone("halo", "robe", HALO_C)
    halo.locators["halo_c"] = HALO_C                 # locator names never repeat a bone name
    cx, cy, cz = HALO_C
    y = cy + APOTHEM
    for k in range(HALO):
        rz = 60.0 * k
        b = m.bone(f"beam{k}", halo.name, HALO_C, (0.0, 0.0, rz))
        ang = math.radians(rz)
        b.variant["edict"] = ((1.2 * math.sin(ang), 1.2 * math.cos(ang), 0.0), None)
        tgt, grz = BEAM_GATE[k]
        off = tuple(np.array(tgt) - _beam_center(grz))
        b.variant["court"] = (off, (0.0, 0.0, grz))
        b.variant["throne"] = (off, (0.0, 0.0, grz))
        m.cube(b.name, (cx - BEAM / 2, y - 0.5, cz - 0.5), (BEAM, 1.0, 1.0), "gilt")
        # upturned ends: like the swept ends of a torii lintel (only the outer ends stay on the gate)
        keep_r = k == 1
        keep_l = k == 5
        m.cube(b.name, (cx + BEAM / 2 - 0.25, y - 0.375, cz - 0.5), (1.5, 0.75, 1.0), "gilt",
               pivot=(cx + BEAM / 2 - 0.25, y, cz), rot=(0, 0, -28), skip=None if keep_r else GRAND)
        m.cube(b.name, (cx - BEAM / 2 - 1.25, y - 0.375, cz - 0.5), (1.5, 0.75, 1.0), "gilt",
               pivot=(cx - BEAM / 2 + 0.25, y, cz), rot=(0, 0, 28), skip=None if keep_l else GRAND)
    seals = m.bone("seals", halo.name, HALO_C)
    for k in range(SEALS):
        rz = 45.0 + 90.0 * k
        sb = m.bone(f"seal{k}", seals.name, HALO_C, (0.0, 0.0, rz))
        tgt, grz = SEAL_GATE[k]
        off = tuple(np.array(tgt) - _seal_center(grz))
        sb.variant["court"] = (off, (0.0, 0.0, grz))
        sb.variant["throne"] = (off, (0.0, 0.0, grz))
        m.box(sb.name, (cx, cy + SEAL_R, cz - 0.2), (2.0, 2.0, 0.5), "seal", ppu=4.0)


def _gate(m: Model) -> None:
    """Court / throne only: the parts of the torii that are not halo beams.  Each grows in
    (scale 0 -> 1 from its own pivot) while the beams fly into place."""
    z = GATE_Z
    for s, p in ((1, "r"), (-1, "l")):
        pl = m.bone(f"pillar_{p}", "halo", (s * PILLAR_X, 31.5, z), only=GRAND)
        m.box(pl.name, (s * PILLAR_X, 15.75, z), (1.5, 31.5, 1.5), "pillar", only=GRAND)
        m.box(pl.name, (s * PILLAR_X, 0.5, z), (2.5, 1.0, 2.5), "lacquer", only=GRAND)     # kamaki (pillar foot)
    nk = m.bone("nuki", "halo", (0.0, 32.5, z), only=GRAND)
    for s in (-1, 1):
        m.box(nk.name, (s * 5.75, 32.5, z), (6.5, 1.0, 1.0), "gilt", only=GRAND)
    ks = m.bone("kasagi", "halo", (0.0, 37.0, z), only=GRAND)
    for s in (-1, 1):
        m.box(ks.name, (s * 4.75, 37.0, z), (4.5, 1.0, 1.0), "gilt", only=GRAND)
    m.box(ks.name, (0.0, 37.75, z), (14.0, 0.5, 1.5), "lacquer", only=GRAND)        # black cap of the lintel


def _throne(m: Model) -> None:
    th = m.bone("throne", "robe", (0.0, 8.0, 5.0), only={"throne"})
    o = {"throne"}
    m.box(th.name, (0.0, 18.5, 5.0), (9.0, 21.0, 1.0), "lacquer", only=o)           # tall seat back
    m.box(th.name, (0.0, 18.5, 4.375), (7.0, 17.0, 0.25), "throne_silk", only=o)    # vermilion silk inset
    for s in (-1, 1):
        m.box(th.name, (s * 5.0, 17.0, 5.0), (1.0, 18.0, 1.0), "gold", only=o)      # posts
        m.box(th.name, (s * 5.0, 26.75, 5.0), (1.5, 1.5, 1.5), "gilt", only=o)       # finials
    m.box(th.name, (0.0, 29.25, 5.0), (11.0, 1.0, 1.5), "gold", only=o)             # crest rail
    for s, p in ((-1, "r"), (1, "l")):
        bn = m.bone(f"banner_{p}", th.name, (s * 4.0, 35.75, GATE_Z - 0.75), only=o)
        m.box(bn.name, (s * 4.0, 30.75, GATE_Z - 0.75), (2.5, 10.0, 0.25), "banner_silk", only=o)


# ============================================================================= materials

def materials():
    mats = {
        "robe": mat_robe, "robe_hem": mat_robe_hem, "chest": mat_chest, "hakama": mat_hakama, "belt": mat_belt,
        "wing": mat_wing, "sleeve": mat_sleeve, "cuff": mat_cuff, "tamoto": mat_tamoto,
        "gold": mat_gold, "vermilion": mat_vermilion, "lacquer": mat_lacquer, "geta": mat_geta,
        "skin": mat_skin, "skin_lo": mat_skin_lo, "skin_hi": mat_skin_hi, "mask": mat_mask, "lidmat": mat_lid,
        "jewel": mat_jewel, "gilt": mat_gilt, "seal": mat_seal, "pillar": mat_pillar, "veil": mat_veil,
        "throne_silk": mat_throne_silk, "banner_silk": mat_banner_silk, "accent": mat_accent,
    }
    mats.update(helper_materials())
    return mats


def _P(ctx):
    return ctx.params.get("radiant", 0.0), ctx.params.get("night", 0.0)


def _ivory(ctx):
    return MOON if _P(ctx)[1] > 0.5 else IVORY


def _folds(ctx, lv, period=6):
    """Soft vertical fold bands (cloth hanging in folds)."""
    if not px.side(ctx):
        return lv
    ix, iy, W, Hh = px.texel(ctx)
    ph = (ix + ctx.seed % 3) % period
    return lv + np.where(ph == 0, -0.07, np.where(ph == 1, 0.04, 0.0))


def _gold_glow(ctx, mask, base=0.0):
    rad, night = _P(ctx)
    return np.where(mask, base + 0.25 * rad + 0.35 * night, 0.0)


def mat_robe(ctx):
    lv = _folds(ctx, px.rim(ctx, px.light(ctx), 0.1, 0.1))
    return px.quant(ctx, _ivory(ctx), lv), ctx.ones(), ctx.zeros()


def mat_robe_hem(ctx):
    """Outer robe panel: folds, a gold hem with a crimson piping row above it."""
    ix, iy, W, Hh = px.texel(ctx)
    lv = _folds(ctx, px.light(ctx, grad=0.12))
    c = px.quant(ctx, _ivory(ctx), lv)
    g = ctx.zeros()
    if px.side(ctx):
        hem = iy >= Hh - 2
        pipe = iy == Hh - 3
        c = np.where(hem[:, None], px.quant(ctx, GOLD, px.light(ctx) + 0.05), c)
        c = np.where(pipe[:, None], VERM[2], c)
        g = _gold_glow(ctx, hem)
    return c, ctx.ones(), g


def mat_chest(ctx):
    ix, iy, W, Hh = px.texel(ctx)
    lv = _folds(ctx, px.rim(ctx, px.light(ctx), 0.1, 0.0), period=7)
    c = px.quant(ctx, _ivory(ctx), lv)
    g = ctx.zeros()
    if ctx.face == "south":
        # the house crest on the back of the robe (what everyone behind the sovereign sees)
        c2, _ = px.decal(ctx, c, MON, {"G": GOLD[3]}, "c", 3)
        mon = np.any(c2 != c, axis=1)
        return c2, ctx.ones(), _gold_glow(ctx, mon)
    if ctx.face == "north":
        # the crossed collar: the wearer's left panel over the right, a "y" with layered edges
        cxp = (W - 1) / 2.0
        u = ix - cxp
        top = 1.5 - iy * 0.55            # top layer edge: from the viewer's upper right down to lower left
        inner = -1.5 + iy * 0.55          # under layer edge, hidden past the crossing
        d_top = u - top
        d_in = inner - u
        opening = (d_top < 0) & (d_in < 0)
        c = np.where(opening[:, None], hx("#f7f2e8"), c)                     # white under-kimono in the V
        for k, colr in enumerate((GOLD[3], VERM[3], INDIGO[1])):
            band_t = (d_top >= k) & (d_top < k + 1)
            band_i = (d_in >= k) & (d_in < k + 1) & (iy < 9)
            c = np.where((band_t | band_i)[:, None], colr, c)
            if k == 0:
                g = np.where(band_t | band_i, _gold_glow(ctx, np.ones(ctx.N, bool)), g)
    return c, ctx.ones(), g


def mat_hakama(ctx):
    ix, iy, W, Hh = px.texel(ctx)
    lv = px.light(ctx, grad=0.2, ao=0.1)
    if px.side(ctx):
        lv = lv - 0.13 * ((ix % 3) == 0)                  # pleats
    return px.quant(ctx, VERM, lv), ctx.ones(), ctx.zeros()


def mat_belt(ctx):
    ix, iy, W, Hh = px.texel(ctx)
    c = px.shade(ctx, LACQ, up=0.25, down=0.05)
    g = ctx.zeros()
    if ctx.face == "north":
        plaque = ((ix % 4) == 1) & (iy >= 1) & (iy <= Hh - 2) & (ix > 1) & (ix < W - 2)
        c = np.where(plaque[:, None], GOLD[3], c)
        g = _gold_glow(ctx, plaque)
    return c, ctx.ones(), g


def mat_wing(ctx):
    if ctx.face == "down":
        return px.shade(ctx, VERM), ctx.ones(), ctx.zeros()
    if ctx.face != "up":
        return px.quant(ctx, GOLD, px.light(ctx)), ctx.ones(), _gold_glow(ctx, np.ones(ctx.N, bool))
    c = px.quant(ctx, _ivory(ctx), px.rim(ctx, px.light(ctx), 0.12, 0.1))
    edge = px.border(ctx, 1)
    c = np.where(edge[:, None], GOLD[3], c)
    return c, ctx.ones(), _gold_glow(ctx, edge)


def mat_sleeve(ctx):
    lv = _folds(ctx, px.rim(ctx, px.light(ctx), 0.1, 0.0), period=5)
    return px.quant(ctx, _ivory(ctx), lv), ctx.ones(), ctx.zeros()


MON = ["..GGG..",
       ".G...G.",
       "G.GGG.G",
       "G.G.G.G",
       "G.GGG.G",
       ".G...G.",
       "..GGG.."]


def mat_cuff(ctx):
    """The sleeve's bell: a gold sun-crest (mon) on the outer face, three layered lining
    colours at the opening, and the dark inside of the sleeve."""
    ix, iy, W, Hh = px.texel(ctx)
    if ctx.face == "down":
        c = np.broadcast_to(LACQ[1], (ctx.N, 3)).copy()
        c = np.where(px.border(ctx, 1)[:, None], VERM[3], c)
        return c, ctx.ones(), ctx.zeros()
    lv = _folds(ctx, px.light(ctx), period=5)
    c = px.quant(ctx, _ivory(ctx), lv)
    g = ctx.zeros()
    if px.side(ctx):
        for k, colr in enumerate((INDIGO[2], VERM[3], GOLD[3])):          # from the opening up: indigo, vermilion, gold
            c = np.where((iy == Hh - 1 - k)[:, None], colr, c)
        outer = ctx.wn is not None and abs(ctx.wn[0]) > 0.7 and np.sign(ctx.wn[0]) == np.sign(ctx.p[0, 0])
        if outer:
            mon = np.zeros(ctx.N, bool)
            c2, _ = px.decal(ctx, c, MON, {"G": GOLD[3]}, "c", 0)
            mon = np.any(c2 != c, axis=1)
            c = c2
            g = _gold_glow(ctx, mon)
    return c, ctx.ones(), g


def mat_tamoto(ctx):
    ix, iy, W, Hh = px.texel(ctx)
    lv = _folds(ctx, px.light(ctx, grad=0.1), period=5)
    c = px.quant(ctx, _ivory(ctx), lv)
    if px.side(ctx):
        c = np.where((iy >= Hh - 1)[:, None], GOLD[3], c)
        c = np.where((iy == Hh - 2)[:, None], VERM[2], c)
    return c, ctx.ones(), ctx.zeros()


def mat_gold(ctx):
    return px.shade(ctx, GOLD, up=0.18, down=0.12), ctx.ones(), _gold_glow(ctx, np.ones(ctx.N, bool))


def mat_vermilion(ctx):
    return px.shade(ctx, VERM), ctx.ones(), ctx.zeros()


def mat_lacquer(ctx):
    return px.shade(ctx, LACQ, up=0.3, down=0.05), ctx.ones(), ctx.zeros()


def mat_geta(ctx):
    ix, iy, W, Hh = px.texel(ctx)
    c = px.shade(ctx, LACQ, up=0.2)
    if ctx.face == "up":
        thong = (np.abs(ix - (W - 1) / 2) < 1) & (iy < Hh // 2)
        c = np.where(thong[:, None], VERM[3], c)
    return c, ctx.ones(), ctx.zeros()


def mat_skin(ctx):
    return px.shade(ctx, SKIN), ctx.ones(), ctx.zeros()


def mat_skin_lo(ctx):
    lv = px.proxy(ctx, (0.0, 27.75, 0.25), (2.6, 2.6, 2.6), 0.8)
    return px.quant(ctx, SKIN, lv), ctx.ones(), ctx.zeros()


def mat_skin_hi(ctx):
    lv = px.proxy(ctx, tuple(_cranium_center()), (3.0, 3.2, 5.2), 0.95)
    return px.quant(ctx, SKIN, lv + 0.04), ctx.ones(), ctx.zeros()


# the mask, painted at 4 texels per unit (18 x 18): Heian court make-up
FACE = [
    "..................",
    "..................",
    "..................",
    "...bbb......bbb...",
    "..................",
    "..................",
    "..................",
    "..................",
    "..L............L..",
    "...LLLL....LLLL...",
    ".jYYYPY....YPYYYj.",
    "...yyy......yyy...",
    "..................",
    "..................",
    "..................",
    ".......rrrr.......",
    "........rr........",
    "..................",
]


def mat_mask(ctx):
    rad, night = _P(ctx)
    if ctx.face != "north":
        lv = px.proxy(ctx, FACE_C, (2.5, 2.6, 2.4), 0.7)
        return px.quant(ctx, SKIN, lv), ctx.ones(), ctx.zeros()
    lv = px.proxy(ctx, (FACE_C[0], FACE_C[1], FACE_C[2] + 2.0), (3.2, 3.2, 3.6), 0.6) + 0.06
    c = px.quant(ctx, MASK, lv, dither=0.3)
    colors = {"b": "#a59c92", "j": "#c2391f", "L": "#6e6458", "Y": "#ffd24a", "y": "#c98a1e", "P": "#1a0d04", "r": "#b8261a"}
    c, g = px.decal(ctx, c, FACE, colors, 0, 0, glow=ctx.zeros(), glow_chars="Yy", glow_level=0.55 + 0.3 * rad)
    return c, ctx.ones(), g


def mat_lid(ctx):
    return np.broadcast_to(MASK[3], (ctx.N, 3)).copy(), ctx.ones(), ctx.zeros()


def mat_jewel(ctx):
    return px.shade(ctx, VERM, offset=0.15), ctx.ones(), np.full(ctx.N, 0.35)


def mat_gilt(ctx):
    """Halo / gate beams: gilt with a glowing core line along the beam."""
    rad, night = _P(ctx)
    ix, iy, W, Hh = px.texel(ctx)
    c = px.shade(ctx, GOLD, up=0.2, down=0.15)
    core = np.zeros(ctx.N, bool)
    if px.side(ctx) and Hh >= 2 and W >= 3:
        core = (iy == Hh // 2) & (ix > 0) & (ix < W - 1)
        c = np.where(core[:, None], GOLD[4], c)
    g = np.where(core, 0.55 + 0.35 * rad, 0.0) + _gold_glow(ctx, ~core) * 0.5
    return c, ctx.ones(), g


SEAL = ["WWWWWW",            # 王 - "sovereign"
        "..WW..",
        ".WWWW.",
        "..WW..",
        "..WW..",
        "WWWWWW"]


def mat_seal(ctx):
    rad, night = _P(ctx)
    c = px.shade(ctx, VERM, up=0.1)
    g = ctx.zeros()
    if ctx.face in ("north", "south"):
        c = np.where(px.border(ctx, 1)[:, None], GOLD[3], c)
        c, g = px.decal(ctx, c, SEAL, {"W": "#fff4dc"}, "c", "c", glow=g, glow_chars="W", glow_level=0.5 + 0.3 * rad)
    return c, ctx.ones(), g


def mat_pillar(ctx):
    """Gate pillars: vermilion lacquer with two gold bands near the top."""
    ix, iy, W, Hh = px.texel(ctx)
    c = px.quant(ctx, VERM, px.rim(ctx, px.light(ctx, grad=0.05), 0.0, 0.0, edges=0.08))
    if px.side(ctx):
        c = np.where(((iy == 3) | (iy == 5))[:, None], GOLD[3], c)
    return c, ctx.ones(), ctx.zeros()


def mat_veil(ctx):
    """The light hanging inside the gate: thin golden bands of mist (cutout)."""
    ix, iy, W, Hh = px.texel(ctx)
    band = ((iy // 3) % 3 == 0) & (px.hash01(ctx, 5) < 0.55)
    c = np.broadcast_to(px.col("#ffe6a0"), (ctx.N, 3)).copy()
    return c, band.astype(float), ctx.zeros()


def mat_throne_silk(ctx):
    c = px.quant(ctx, VERM, px.light(ctx, grad=0.1))
    if ctx.face == "north":
        c, g = px.decal(ctx, c, MON, {"G": GOLD[3]}, "c", 4, glow=ctx.zeros(), glow_chars="G", glow_level=0.5)
        return c, ctx.ones(), g
    return c, ctx.ones(), ctx.zeros()


def mat_banner_silk(ctx):
    c = px.quant(ctx, VERM, px.light(ctx, grad=0.12))
    if px.side(ctx):
        c = np.where(px.border(ctx, 1, ("l", "r"))[:, None], GOLD[3], c)
    return c, ctx.ones(), ctx.zeros()


# ============================================================================= helper entities
# (celestial gate, heralds, procession) - the same visual language as the sovereign

def helper_materials():
    return {"h_robe": mat_h_robe, "h_robe_red": mat_h_robe_red, "h_cap": mat_lacquer, "h_face": mat_h_face,
            "h_gold": mat_gold, "h_scroll": mat_h_scroll, "h_banner": mat_h_banner, "h_parasol": mat_h_parasol,
            "h_pillar": mat_pillar, "h_gilt": mat_gilt, "h_lacquer": mat_lacquer, "h_glow": mat_h_glow}


def mat_h_robe(ctx):
    lv = _folds(ctx, px.rim(ctx, px.light(ctx), 0.1, 0.1), period=4)
    return px.quant(ctx, IVORY, lv), ctx.ones(), np.full(ctx.N, 0.15)


def mat_h_robe_red(ctx):
    lv = _folds(ctx, px.light(ctx), period=4)
    return px.quant(ctx, VERM, lv), ctx.ones(), np.full(ctx.N, 0.12)


def mat_h_face(ctx):
    c = px.shade(ctx, MASK, offset=0.05)
    if ctx.face == "north":
        ix, iy, W, Hh = px.texel(ctx)
        eyes = (iy == Hh // 2) & ((ix == 0) | (ix == W - 1))
        c = np.where(eyes[:, None], GOLD[3], c)
    return c, ctx.ones(), np.full(ctx.N, 0.1)


def mat_h_scroll(ctx):
    ix, iy, W, Hh = px.texel(ctx)
    c = px.quant(ctx, px.pal("#b9ab8a", "#ded2b4", "#f1e8d1", "#fbf6e8"), px.light(ctx, grad=0.05) + 0.1)
    if ctx.face in ("north", "south"):
        text = ((ix % 2) == 0) & (iy > 1) & (iy < Hh - 2) & (ix > 1) & (ix < W - 4) & (px.hash01(ctx, 7) < 0.7)
        c = np.where(text[:, None], px.col("#3a2416"), c)
        seal = (ix >= W - 3) & (ix <= W - 2) & (iy >= Hh - 4) & (iy <= Hh - 3)
        c = np.where(seal[:, None], VERM[3], c)
    return c, ctx.ones(), np.full(ctx.N, 0.2)


def mat_h_banner(ctx):
    c = px.quant(ctx, IVORY, px.light(ctx, grad=0.06) + 0.08)
    if ctx.face in ("north", "south"):
        c, _ = px.decal(ctx, c, MON, {"G": VERM[3]}, "c", 2)
        c = np.where(px.border(ctx, 1, ("l", "r"))[:, None], VERM[3], c)
    return c, ctx.ones(), np.full(ctx.N, 0.2)


def mat_h_parasol(ctx):
    ix, iy, W, Hh = px.texel(ctx)
    c = px.quant(ctx, VERM, px.light(ctx))
    if ctx.face == "up":
        ribs = (ix == W // 2) | (iy == Hh // 2) | px.border(ctx, 1)
        c = np.where(ribs[:, None], GOLD[3], c)
    return c, ctx.ones(), np.full(ctx.N, 0.12)


def mat_h_glow(ctx):
    return px.shade(ctx, GOLD, offset=0.15), ctx.ones(), np.full(ctx.N, 0.8)


def build_gate() -> Model:
    """The celestial gate: a torii in the sovereign's language - vermilion pillars, gilt
    tie beam, a black-capped lintel swept up at both ends, a seal plaque and bands of
    golden mist (scaled x3.6 for the sky gate of the ultimate)."""
    m = Model("celestial_gate", ppu=1.0, atlas_width=128)
    m.bone("root", None, (0, 0, 0))
    g = m.bone("gate", "root", (0, 0, 0))
    for s in (-1, 1):
        m.box(g.name, (s * 13.0, 21.0, 0), (3.0, 42.0, 3.0), "h_pillar")
        m.box(g.name, (s * 13.0, 1.0, 0), (5.0, 2.0, 5.0), "h_lacquer")
        m.box(g.name, (s * 13.0, 30.0, 0), (4.0, 1.0, 4.0), "h_gold")
    m.box(g.name, (0, 37.0, 0), (34.0, 2.0, 2.0), "h_gilt")                                   # nuki
    m.box(g.name, (0, 43.5, 0), (34.0, 2.5, 3.0), "h_lacquer")                                # kasagi
    m.box(g.name, (0, 41.75, 0), (30.0, 1.5, 2.5), "h_pillar")                                # shimaki
    for s in (-1, 1):                                                                          # swept-up ends
        x0 = 17.0 if s > 0 else -22.0
        m.cube(g.name, (x0, 42.25, -1.5), (5.0, 2.5, 3.0), "h_lacquer", pivot=(s * 17.0, 43.5, 0), rot=(0, 0, -14 * s))
    m.box(g.name, (0, 39.75, -0.75), (4.0, 4.0, 1.0), "h_scroll")                              # gakuzuka plaque
    ring = m.bone("ring", g.name, (0, 22, 0.5))
    for (x, y, w) in ((-3.0, 9.0, 13.0), (4.0, 16.5, 11.0), (-2.5, 24.0, 15.0), (3.5, 31.0, 9.0)):   # suyari-gasumi:
        m.box(ring.name, (x, y, 0.5), (w, 2.0, 0.5), "h_glow")                                    # staggered bands of
        for e in (-1, 1):                                                                          # golden mist with
            m.box(ring.name, (x + e * (w / 2 + 0.75), y + 0.25 * e, 0.5), (1.5, 1.0, 0.5), "h_glow")  # rounded ends
    inner = m.bone("ring_inner", g.name, (0, 22, 1.0))
    m.box(inner.name, (0, 22, 1.0), (1.0, 1.0, 1.0), "h_glow")
    m.bones["gate"].locators["center"] = (0, 24, 0)
    m.pack()
    return m


def _attendant(m: Model, parent: str, name: str, x: float, z: float, rank: str) -> None:
    """One attendant of the Hundred Heavens: slim flared robe, sleeves, mask, tall cap."""
    b = m.bone(name, parent, (x, 0, z))
    robe = "h_robe_red" if rank in ("guard", "bearer") else "h_robe"
    m.box(b.name, (x, 2.0, z), (3.0, 4.0, 2.5), robe)                     # flared hem
    m.box(b.name, (x, 5.5, z), (2.0, 3.0, 1.5), robe)                     # upper robe
    m.box(b.name, (x, 4.5, z - 1.0), (2.5, 3.0, 0.5), "h_robe")           # sleeves held together in front
    m.box(b.name, (x, 7.75, z), (1.5, 1.5, 1.5), "h_face")                # mask
    m.box(b.name, (x, 9.5, z + 0.25), (1.0, 2.0, 1.0), "h_cap")           # tall cap (eboshi)
    if rank == "standard":
        m.box(b.name, (x + 1.5, 8.0, z), (0.5, 16.0, 0.5), "h_lacquer")
        fl = m.bone(f"{name}_banner", b.name, (x + 1.75, 15.5, z))
        m.box(fl.name, (x + 3.0, 12.5, z), (2.5, 6.0, 0.25), "h_banner")
    elif rank == "guard":
        m.box(b.name, (x - 1.5, 7.0, z), (0.5, 13.0, 0.5), "h_lacquer")
        m.box(b.name, (x - 1.5, 13.75, z), (0.75, 1.5, 0.75), "h_gold")
    elif rank == "herald":
        m.cube(b.name, (x - 0.25, 6.75, z - 3.5), (0.5, 0.5, 3.5), "h_gold", pivot=(x, 7.0, z), rot=(-25, 0, 0))
    elif rank == "judge":
        m.box(b.name, (x + 1.25, 4.5, z - 0.5), (0.5, 2.5, 0.5), "h_scroll")
    elif rank == "parasol":
        m.box(b.name, (x, 9.0, z), (0.5, 6.0, 0.5), "h_lacquer")
        m.box(b.name, (x, 12.25, z), (6.0, 0.5, 6.0), "h_parasol")
        m.box(b.name, (x, 12.75, z), (1.0, 0.5, 1.0), "h_gold")
    elif rank == "bearer":
        m.box(b.name, (x, 8.5, z), (1.0, 0.5, 1.0), "h_gold")


def build_procession() -> Model:
    """One column of the Hundred Heavens: twelve attendants of six ranks in two files,
    with an empty palanquin (koshi) borne in the middle."""
    m = Model("procession", ppu=1.0, atlas_width=256)
    m.bone("root", None, (0, 0, 0))
    col = m.bone("column", "root", (0, 0, 0))
    ranks = ["standard", "guard", "herald", "judge", "bearer", "parasol"]
    for row, rank in enumerate(ranks):
        z = -12.5 + row * 5.0
        for side in (-1, 1):
            _attendant(m, col.name, f"fig_{row}_{'r' if side < 0 else 'l'}", 3.5 * side, z, rank)
    pal = m.bone("palanquin", col.name, (0, 9.0, 7.5))
    m.box(pal.name, (0, 9.0, 7.5), (0.5, 0.5, 13.0), "h_lacquer")
    m.box(pal.name, (0, 11.0, 7.5), (4.0, 3.5, 4.0), "h_robe_red")
    m.box(pal.name, (0, 13.25, 7.5), (5.5, 1.0, 5.5), "h_gold")
    m.box(pal.name, (0, 14.25, 7.5), (1.0, 1.0, 1.0), "h_glow")
    m.pack()
    return m


def build_heralds() -> Model:
    """Two heralds of the proclamation carrying an immense decree between them."""
    m = Model("herald", ppu=1.0, atlas_width=128)
    m.bone("root", None, (0, 0, 0))
    g = m.bone("pair", "root", (0, 0, 0))
    for side in (-1, 1):
        _attendant(m, g.name, f"herald_{'r' if side < 0 else 'l'}", 8.0 * side, 0.0, "herald")
    sc = m.bone("decree", g.name, (0, 8.0, -0.8))
    m.box(sc.name, (0, 6.0, -0.8), (13.0, 5.0, 0.5), "h_scroll")
    for side in (-1, 1):
        m.box(sc.name, (6.75 * side, 6.0, -0.8), (1.0, 6.0, 1.0), "h_lacquer")
    m.pack()
    return m
