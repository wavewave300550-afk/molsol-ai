"""Cherubim -- the Four Living Witnesses (DW02, reused by DW05).

Original design: a colossal armoured witness with no legs.  Its lower body is a hovering,
swaying column of bronze inscription tiers wrapped by three counter-rotating letter rings and
hanging testament banners.  A cuirass of bronze-gold plates carries a censer of burning coals
between the wing roots.  The head is a four-faced drum (human front, lion right, ox left, eagle
back), each face modelled in relief, that turns on the neck so the active witness looks forward
while the body keeps its heading.  Four great wings re-configure per aspect.  Each face "wakes"
(glowing eyes and sigils, render-controller visibility) while its aspect is active.

Helpers: dw_cherub_blade (luminous feather-blade that dives from above) and dw_cherub_roar
(a travelling ring of sacred letters carried by the lion's roar).
"""
import math

import numpy as np

from kit import glyphs, synth as sy, tex
from kit.anim import LIFE, Anim, M
from kit.geo import Mat, Model, ring
from kit.parts import feather_wing, flutter, sym, wave

from .a_fx_common import particles

IVORY, GOLD, WGOLD, SILVER, BLUE = "#f5f0e1", "#c9a24a", "#fff3c4", "#d8dde3", "#2b3f8f"
FW = glyphs.FIRST_WORD

# ---------------------------------------------------------------------------------------------
# state ids shared by every spell that uses the Cherubim (mirrored in src/spells/dw02_*.ts)
STATES_NAMES = ["hidden", "arrive", "idle", "human", "ox", "ox_retaliate", "lion", "eagle", "verdict", "depart"]
# animation lengths / key moments in seconds (the spell timeline mirrors these)
T_ARRIVE = 1.6
T_HUMAN = 1.6        # writing strokes 0.35-1.0, casting throw at HUMAN_CAST
HUMAN_CAST = 1.05
T_OX = 1.0           # wings locked into the shield wall at OX_LOCK
OX_LOCK = 0.75
T_RETALIATE = 1.0    # wings blast open at RET_BLAST
RET_BLAST = 0.3
T_LION = 1.8         # jaw fully open at LION_ROAR
LION_ROAR = 0.95
T_EAGLE = 2.8        # summon at 0.6, dive commands at EAGLE_THRUST
EAGLE_THRUST = (1.6, 2.5)
T_VERDICT = 1.6      # the four faces whirl, wings slam down at VERDICT_HIT
VERDICT_HIT = 0.8
T_DEPART = 1.8

BLADE_FORM, BLADE_DIVE, BLADE_SHATTER = 0.6, 0.25, 0.5
ROAR_LIFE = 1.0


def spin(rate):
    return M(f"q.life_time*{rate}", lambda t: t * rate)


# ---------------------------------------------------------------------------------------------
# materials
def _mats():
    k = {}
    k["gold"] = tex.metal(GOLD, "#ffe9a3", "#7a5a1e", bands=2.0)
    k["gold_t"] = tex.metal("#d9b45a", "#fff3c4", "#8a6a26", bands=3.0, glow=0.18)
    k["bronze"] = tex.metal("#a8783a", "#e8c27a", "#4e3416", bands=3.0)
    k["bronze_d"] = tex.metal("#7d5527", "#c99a55", "#3a2410", bands=2.5)
    k["plates"] = tex.plates("#b98c40", "#4e3416", hi="#ffe2a0", cell=(8, 6), rivet="#fff3c4", glow_line=0.12)
    k["plates2"] = tex.plates("#c99a48", "#5a3c18", hi="#fff0c0", cell=(6, 5), rivet="#fff3c4", glow_line=0.08)
    k["cuirass"] = tex.trimmed(tex.metal("#c79a45", "#fff0b8", "#6e4c1c", bands=4.0), WGOLD, 1, 0, glow=0.35)
    k["blue"] = tex.trimmed(tex.speck(BLUE, 0.05, edge_dark=0.2), GOLD, 1, 0, glow=0.25)
    k["ivory"] = tex.porcelain(IVORY, "#e2d6bd", crack=0.0, gilt=GOLD)
    k["ivory_p"] = tex.porcelain("#efe6d0", "#d4c5a3", crack=0.0)
    k["glyphs"] = tex.glyph_rows(FW, WGOLD, glow=1.0, color2="#ffd76a", fill=0.85, key="cherub_glyphs")
    k["glyphs_b"] = tex.glyph_rows(FW, "#dfe8ff", glow=1.0, color2=WGOLD, fill=0.75, seed=5, key="cherub_glyphs_b")
    k["lion"] = tex.metal("#d6a443", "#ffe7a0", "#7d561c", bands=4.0, glow=0.05)
    k["mane"] = tex.metal("#c98f32", "#ffdc86", "#6e4512", bands=5.0, glow=0.12, vertical=True)
    k["mane2"] = tex.metal("#e2b450", "#fff1c0", "#8a6020", bands=6.0, glow=0.22, vertical=True)
    k["horn"] = tex.bone_mat("#efe4c8", "#b8a57c", pores=0.05)
    k["eagle"] = tex.scales("#f5f0e1", "#b9b2a2", light="#ffffff", size=3)
    k["beak"] = tex.metal("#f0c24a", "#fff3c4", "#9a6a18", bands=2.0, glow=0.15)
    k["dark"] = tex.flat("#24160a")
    k["coal"] = tex.mottled("#ff8a2a", "#fff1b0", scale=2.0, glow=1.0, edge_dark=0.0)
    k["flame"] = tex.shaped(tex.m_leaf(), "#fffbe6", "#ffb84a", glow=1.0, var=0, key="cherubflame")
    k["mouthglow"] = tex.glow_flat("#fff3c4", 1.0, core="#ffffff")
    k["gem"] = tex.shaped(tex.m_diamond(), "#ffffff", "#7f9cff", glow=1.0, var=0, key="cherubgem")
    k["seal"] = tex.magic_circle(FW, WGOLD, GOLD, bands=((0.62, 0.92, 10),), lines=(0.58, 0.97), star=4,
                                 star_r=(0.1, 0.5), core=0.12, key="cherubseal")
    k["fabric"] = tex.trimmed(tex.fabric("#f7f1e0", None, 0.05, glow=0.12, fringe=True), BLUE, 1, 0, glow=0.1)

    def fz(base, tip, rachis, **kw):   # feathers that become luminous blades in the 'blaze' skin
        return tex.alt(tex.feather(base, tip, rachis, **kw),
                       blaze=tex.feather("#fffdf2", "#fff3c4", "#ffd76a", glyph_color="#ffffff", glyph_glow=1.0,
                                         **{**kw, "glow": 0.45, "glow_tip": 1.0}))
    k["f_up"] = [fz("#fbf8ee", "#f0d98e", GOLD, glow=0.05, glow_tip=0.35),
                 fz("#f4efe0", "#e6c870", "#b8923a", glow=0.05, glow_tip=0.3, notch=0.1)]
    k["f_low"] = [fz("#e9d3a0", "#b8863a", "#7a5a1e", glow=0.04, glow_tip=0.3),
                  fz("#e2c98e", "#a87a30", "#6e4e18", glow=0.04, glow_tip=0.28, notch=0.12)]
    k["covert"] = tex.alt(tex.feather("#fffaf0", "#efdcae", "#c9a24a", glow=0.05, taper=0.9, notch=0.0),
                          blaze=tex.feather("#ffffff", "#fff3c4", "#ffd76a", glow=0.6, taper=0.9, notch=0.0))
    k["covert_b"] = tex.alt(tex.feather("#d9b46a", "#a87a30", "#6e4e18", glow=0.04, taper=0.9, notch=0.0),
                            blaze=tex.feather("#fff3c4", "#ffd76a", "#c9a24a", glow=0.6, taper=0.9, notch=0.0))
    return k


def _glyph(i, color=WGOLD, color2="#ffd76a"):
    return tex.bitmap_cut(FW[i % len(FW)], color, glow=1.0, color2=color2)


def _letter_ring(m, name, parent, y, r, n_seg, n_glyph, mat, seed):
    """Horizontal ring of gold segments carrying standing letters."""
    b = m.bone(name, parent, pivot=(0, y, 0))
    ring(b, (0, y, 0), r, n_seg, (2 * math.pi * r / n_seg * 0.72, 1.6, 1.4), mat, axis="y", cycle=2)
    for k in range(n_glyph):
        b.box((0, y + 3.4, -r), (3.2, 4.4, 0), _glyph(seed + k * 3), rot=(0, k * 360 / n_glyph, 0), pivot=(0, y, 0),
              faces=("north", "south"), density=2.5)
    return b


# ---------------------------------------------------------------------------------------------
def build_model():
    K = _mats()
    m = Model("cherub", density=1.5, bounds=(44, 34, (0, 7, 0)), alts=("blaze",))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 40, 0))

    # ---- hovering column of inscription tiers (no legs)
    col3 = m.bone("col3", body, pivot=(0, 40, 0))
    col3.box((0, 35, 0), (15, 10, 13), K["plates"])
    col3.box((0, 31, 0), (15.6, 1.6, 13.6), K["gold_t"])
    for ax, c, w in (("z", (0, 35, -6.62), 15), ("z", (0, 35, 6.62), 15), ("x", (7.62, 35, 0), 13), ("x", (-7.62, 35, 0), 13)):
        col3.plane(ax, c, w - 1, 6, K["glyphs"], variant=len(c) % 2)
    col2 = m.bone("col2", col3, pivot=(0, 30, 0))
    col2.box((0, 25, 0), (12, 10, 10.5), K["plates2"])
    col2.box((0, 21, 0), (12.6, 1.4, 11.1), K["blue"])
    for ax, c, w in (("z", (0, 25.5, -5.37), 12), ("z", (0, 25.5, 5.37), 12), ("x", (6.12, 25.5, 0), 10.5), ("x", (-6.12, 25.5, 0), 10.5)):
        col2.plane(ax, c, w - 1, 5, K["glyphs_b"], variant=1)
    col1 = m.bone("col1", col2, pivot=(0, 20, 0))
    col1.box((0, 15.5, 0), (9, 9, 8), K["plates"], variant=1)
    col1.box((0, 11, 0), (9.6, 1.4, 8.6), K["gold_t"], variant=1)
    col1.box((0, 7.5, 0), (5.2, 6, 5.2), K["gold"], rot=(0, 45, 0))           # inverted point
    col1.box((0, 3.6, 0), (2.4, 3, 2.4), K["gold_t"], rot=(0, 45, 0))
    col1.plane("y", (0, 2.2, 0), 14, 14, K["seal"], faces=("up", "down"), density=3)
    col1.locator("tip", (0, 3, 0))
    _letter_ring(m, "ring_a", col1, 14, 9.5, 10, 5, K["gold_t"], 2)
    _letter_ring(m, "ring_b", col2, 26, 12.5, 12, 6, K["gold_t"], 9)
    _letter_ring(m, "ring_c", col3, 37.5, 15.5, 12, 8, K["gold_t"], 17)

    # testament banners hanging from the girdle (front, back, both sides)
    for i, (ax, x, z) in enumerate((("z", 0, -8.1), ("z", 0, 8.1), ("x", 9.3, 0), ("x", -9.3, 0))):
        par = body.name
        for s in range(3):
            y1 = 40 - s * 8.5
            b = m.bone(f"banner{i + 1}_{s + 1}", par, pivot=(x, y1, z))
            b.plane(ax, (x, y1 - 4.25, z), 6 - s * 0.6, 8.5, K["fabric"], variant=(i + s) % 3)
            off = -0.15 if (z < 0 or x < 0) else 0.15
            gc = (x + (off if ax == "x" else 0), y1 - 4.25, z + (off if ax == "z" else 0))
            b.plane(ax, gc, 4.4 - s * 0.6, 7, K["glyphs"], variant=(i * 3 + s) % 4, density=2)
            par = b.name

    # ---- armoured torso
    body.box((0, 42, 0), (18, 4, 14), K["gold_t"])                       # girdle
    for k in range(12):                                                   # pteruges: hanging lames of the girdle
        a = math.radians(k * 30 + 15)
        x, z = math.sin(a) * 9.6, -math.cos(a) * 8.4
        body.box((x, 37.5, z), (3.4, 7, 0.8), K["blue"] if k % 2 else K["gold"], rot=(0, -k * 30 - 15, 0),
                 variant=k % 2)
    body.box((0, 52, 0), (20, 16, 13), K["cuirass"])                     # cuirass
    body.box((0, 49, 0), (21, 1.4, 13.8), K["gold"])                      # lames
    body.box((0, 45.5, 0), (19.4, 1.4, 13.4), K["gold"], variant=1)
    body.box((0, 62, 0), (24, 6, 14.4), K["gold"])                        # yoke
    body.box((0, 54.5, -6.7), (8, 11, 0.8), K["blue"])                   # blue stole panel
    body.plane("z", (0, 55, -7.2), 6.5, 6.5, K["seal"], density=3)        # breast seal
    body.plane("z", (0, 51, -7.25), 3.5, 3.5, K["gem"], density=3)
    for sx in (1, -1):                                                    # pauldrons in three lames
        body.box((sx * 13.5, 62.5, 0), (8, 5, 12), K["gold"], variant=1)
        body.box((sx * 14.5, 59, 0), (7, 3, 11), K["plates2"], rot=(0, 0, sx * -14))
        body.box((sx * 15.2, 56.4, 0), (6, 2.6, 10), K["gold_t"], rot=(0, 0, sx * -22))
    body.box((0, 67, 0), (11, 4, 11), K["gold_t"], variant=1)             # gorget
    body.locator("chest", (0, 55, -9))

    # censer of burning coals between the wing roots
    cen = m.bone("censer", body, pivot=(0, 55, 11))
    cen.box((0, 53.5, 11), (9, 3, 7), K["gold"])
    cen.box((0, 55.4, 11), (10.4, 1, 8.4), K["gold_t"])
    cen.box((0, 51.2, 11), (4, 2, 4), K["gold"], variant=1)
    for i, (dx, dz) in enumerate(((-2.4, -1.4), (1.8, -1.6), (-0.4, 1.2), (2.6, 1.6), (-2.6, 1.8))):
        cen.box((dx, 56.3, 11 + dz), (2.2, 1.6, 2.2), K["coal"], variant=i % 2, rot=(0, i * 37, 0))
    fl = m.bone("censer_flame", cen, pivot=(0, 56, 11))
    fl.plane("z", (0, 61, 11), 7, 10, K["flame"])
    fl.plane("x", (0, 60, 11), 6, 8, K["flame"])
    fl.locator("censer", (0, 60, 11))

    neck = m.bone("neck_ring", body, pivot=(0, 69, 0))
    ring(neck, (0, 69, 0), 8.2, 10, (3.4, 1.2, 1.2), K["gold_t"], axis="y")
    for k in range(6):
        neck.box((0, 71, -8.2), (2.6, 3.4, 0), _glyph(k * 5 + 1, "#dfe8ff", WGOLD), rot=(0, k * 60, 0), pivot=(0, 69, 0),
                 faces=("north", "south"), density=2.5)

    # ---- the four-faced head: 'head' tilts, 'drum' turns the chosen face to the front
    head = m.bone("head", body, pivot=(0, 70, 0))
    drum = m.bone("drum", head, pivot=(0, 70, 0))
    drum.box((0, 79, 0), (14, 18, 14), K["bronze_d"])
    drum.box((0, 70.8, 0), (16, 2, 16), K["gold"])
    drum.box((0, 88.6, 0), (16, 1.6, 16), K["gold"], variant=1)
    for sx in (1, -1):
        for sz in (1, -1):
            drum.box((sx * 7.2, 79, sz * 7.2), (2.2, 17, 2.2), K["gold_t"])  # corner pilasters
    # HUMAN (front, -Z): serene porcelain face with braided beard
    drum.box((0, 79.5, -7.6), (10, 14, 1.2), K["ivory"])
    drum.box((0, 82.8, -8.5), (9, 1.4, 1.0), K["ivory_p"])                # brow
    drum.box((0, 79.4, -8.8), (1.6, 4.6, 1.6), K["ivory_p"])              # nose
    drum.box((0, 77.4, -9.3), (2.2, 1.0, 1.2), K["ivory_p"])
    for sx in (1, -1):
        drum.box((sx * 2.9, 77.6, -8.4), (2.4, 2.2, 0.8), K["ivory_p"])   # cheeks
        drum.box((sx * 2.4, 80.7, -8.32), (2.6, 0.6, 0.3), K["gold"])     # closed lids
        drum.box((sx * 5.6, 78, -7.9), (1.4, 10, 1.6), K["gold_t"])       # side locks
    drum.box((0, 75.4, -8.45), (3.4, 0.8, 0.6), K["gold"])                # lips
    beard = tex.banded(K["gold"], "#7a5a1e", every=2, width=1, horizontal=True)
    drum.box((0, 72.9, -8.5), (6, 3.6, 1.6), beard)
    drum.box((0, 71.2, -8.7), (4, 1.6, 1.4), beard, variant=1)
    # LION (right, +X): golden muzzle, opening jaw, two-layer mane
    drum.box((7.6, 79.5, 0), (1.2, 13, 10), K["lion"])
    drum.box((9.6, 77.2, 0), (4, 4.4, 5.6), K["lion"], variant=1)          # muzzle
    drum.box((11.9, 78.6, 0), (1, 1.6, 3), K["dark"])                     # nose
    drum.box((9, 82.2, 0), (2.4, 1.6, 9), K["lion"], variant=2)            # brow ridge
    for sz in (1, -1):
        drum.box((10.7, 76.4, sz * 1.9), (2.4, 2.2, 2.2), K["lion"], variant=1)   # whisker pads
        drum.box((11.6, 74.6, sz * 1.6), (0.8, 1.6, 0.8), K["ivory_p"])          # upper fangs
        drum.box((8.36, 80.7, sz * 2.5), (0.3, 0.6, 2.4), K["gold"])              # closed lids
    drum.box((8.4, 74.6, 0), (0.4, 2.4, 4.4), K["mouthglow"])
    jaw = m.bone("jaw_lion", drum, pivot=(8.4, 74.6, 0))
    jaw.box((10.2, 73.7, 0), (4, 1.6, 5), K["lion"], variant=2)
    for sz in (1, -1):
        jaw.box((11.7, 74.9, sz * 1.4), (0.7, 1.2, 0.7), K["ivory_p"])
    jaw.locator("mouth_lion", (12, 75, 0))
    mane = m.bone("mane", drum, pivot=(7.4, 79, 0))
    ring(mane, (10.2, 79, 0), 6.6, 10, (4.0, 4.2, 2.6), K["mane2"], axis="x", cycle=2)
    ring(mane, (8.4, 79, 0), 8.8, 12, (4.4, 5.0, 2.8), K["mane"], axis="x", start=15.0, cycle=2)
    # OX (left, -X): broad bronze face, long muzzle, ivory horns, nose ring
    drum.box((-7.6, 79.5, 0), (1.2, 14, 10), K["bronze"])
    drum.box((-8.9, 77.5, 0), (2.4, 9, 4.2), K["bronze"], variant=1)       # long face
    drum.box((-10.4, 73.6, 0), (3.6, 4, 6.4), K["bronze"], variant=2)      # muzzle
    for sz in (1, -1):
        drum.box((-12.25, 73.9, sz * 1.6), (0.2, 1.4, 1.2), K["dark"])     # nostrils
        drum.box((-8.36, 80.9, sz * 3.3), (0.3, 0.6, 2.4), K["gold"])     # closed lids
        drum.box((-8.2, 82.6, sz * 6.4), (1.2, 2.2, 3.4), K["bronze"], rot=(sz * 20, 0, 0))   # ears
    drum.box((-8.9, 83.4, 0), (2.2, 2, 9.6), K["bronze"], variant=2)       # brow
    nr = m.bone("nose_ring", drum, pivot=(-12.4, 73.2, 0))
    ring(nr, (-12.4, 71.6, 0), 1.7, 8, (1.4, 0.6, 0.6), K["gold_t"], axis="x")
    for sz, tag in ((-1, "f"), (1, "b")):
        p0 = (-8.4, 85, sz * 4.6)
        h1 = m.bone(f"horn_{tag}1", drum, pivot=p0)
        h1.box((p0[0], p0[1], p0[2] + sz * 2.6), (3.2, 3.2, 5.2), K["horn"])
        p1 = (p0[0], p0[1], p0[2] + sz * 5.2)
        h2 = m.bone(f"horn_{tag}2", h1, pivot=p1, rot=(-sz * 38, 0, 0))
        h2.box((p1[0], p1[1], p1[2] + sz * 2.4), (2.5, 2.5, 4.8), K["horn"], variant=1)
        p2 = (p1[0], p1[1], p1[2] + sz * 4.8)
        h3 = m.bone(f"horn_{tag}3", h2, pivot=p2, rot=(-sz * 40, sz * 20, 0))
        h3.box((p2[0], p2[1], p2[2] + sz * 2.0), (1.8, 1.8, 4.0), K["horn"], variant=2)
        h3.box((p2[0], p2[1], p2[2] + sz * 4.5), (1.0, 1.0, 1.4), K["gold_t"])
    # EAGLE (back, +Z): white feathered face, hooked golden beak, ruff of feathers
    drum.box((0, 79.5, 7.6), (10, 13, 1.2), K["eagle"])
    for sx in (1, -1):
        drum.box((sx * 2.6, 82.2, 8.7), (4.2, 1.4, 1.6), K["gold"], rot=(0, 0, -sx * 14))   # stern brows
        drum.box((sx * 2.6, 80.6, 8.32), (2.6, 0.6, 0.3), K["gold"])                           # closed lids
    drum.box((0, 79.5, 8.8), (4, 1.4, 1.4), K["beak"])                    # cere
    drum.box((0, 78.2, 10.1), (3.6, 2.8, 3.2), K["beak"], variant=1)
    drum.box((0, 77.6, 12.4), (2.8, 2.4, 2.0), K["beak"])
    drum.box((0, 76.3, 13.4), (2.0, 2.6, 1.4), K["beak"], rot=(28, 0, 0))   # hook
    blo = m.bone("beak_lo", drum, pivot=(0, 76.6, 9))
    blo.box((0, 76.1, 10.8), (2.6, 1.0, 3.2), K["beak"], variant=1)
    ruff = m.bone("ruff", drum, pivot=(0, 79, 8.4))
    rf = tex.feather("#ffffff", "#d8dde3", "#c9a24a", glow=0.05, taper=0.8, notch=0.1)
    for k in range(9):
        a = -100 + k * 25                                                   # around the upper half
        rr = math.radians(a)
        cx, cy = math.sin(rr) * 7.6, 79 + math.cos(rr) * 7.6
        ruff.box((cx, cy + 3.5, 8.6), (3.2, 8, 0), rf, rot=(-24, 0, -a), pivot=(cx, cy, 8.6), variant=k % 3,
                 faces=("north", "south"))
    # crown on top of the drum
    crown = m.bone("crown", drum, pivot=(0, 90, 0))
    ring(crown, (0, 90.4, 0), 8.6, 12, (4.2, 1.4, 1.6), K["gold_t"], axis="y", cycle=2)
    for k in range(8):
        a = math.radians(k * 45)
        x, z = math.sin(a) * 8.6, -math.cos(a) * 8.6
        crown.box((x, 93, z), (1.6, 5 if k % 2 == 0 else 3, 1.6), K["gold"], rot=(0, k * 45, 0))
        if k % 2 == 0:
            crown.box((x * 1.02, 95.5, z * 1.02), (2.2, 2.6, 0), K["gem"], rot=(0, -k * 45, 0), density=3,
                      faces=("north", "south"))
    # wake overlays: glowing open eyes and brow sigils, shown only while that witness acts
    eh = tex.eye_mat(iris=BLUE, sclera="#fffdf4", pupil="#0b1030", lid="#efe6d0", glow=1.0, ring=WGOLD)
    el = tex.eye_mat(iris="#ffb020", sclera="#fff3c4", pupil="#2a1400", lid="#d6a443", glow=1.0, ring="#fff7d0")
    eo = tex.eye_mat(iris="#4a64c8", sclera="#f6ecd8", pupil="#0b0f20", lid="#a8783a", glow=1.0, ring="#dfe8ff")
    ee = tex.eye_mat(iris="#ffd040", sclera="#fffbe8", pupil="#000000", lid="#f5f0e1", glow=1.0, ring="#ffffff", slit=True)
    wh = m.bone("wake_h", drum, pivot=(0, 80.7, -8.5))
    for sx in (1, -1):
        wh.plane("z", (sx * 2.4, 80.7, -8.55), 2.8, 1.6, eh, density=6)
    wh.box((0, 85.4, -8.45), (2.6, 3.6, 0), _glyph(3), density=4, faces=("north", "south"))
    wl_ = m.bone("wake_l", drum, pivot=(8.6, 80.7, 0))
    for sz in (1, -1):
        wl_.plane("x", (8.6, 80.7, sz * 2.5), 2.6, 1.5, el, density=6)
    wl_.box((8.5, 85.6, 0), (0, 3.2, 2.4), _glyph(6), density=4, faces=("east", "west"))
    wo = m.bone("wake_o", drum, pivot=(-8.6, 80.9, 0))
    for sz in (1, -1):
        wo.plane("x", (-8.6, 80.9, sz * 3.3), 2.6, 1.6, eo, density=6)
    wo.box((-10.1, 81.4, 0), (0, 3.0, 2.2), _glyph(10, "#dfe8ff", WGOLD), density=4, faces=("east", "west"))
    we = m.bone("wake_e", drum, pivot=(0, 80.6, 8.6))
    for sx in (1, -1):
        we.plane("z", (sx * 2.6, 80.6, 8.55), 2.8, 1.6, ee, density=6)
    we.box((0, 85.3, 8.5), (2.6, 3.4, 0), _glyph(14), density=4, faces=("north", "south"))

    # halos of moving inscription above the head (attached to the neck, they do not turn with the faces)
    halo = m.bone("halo", head, pivot=(0, 99, 0))
    ring(halo, (0, 99, 0), 14, 16, (4.2, 1.6, 1.0), K["gold"], axis="y", cycle=2)
    for k in range(8):
        halo.box((0, 101.6, -14), (3.4, 4.6, 0), _glyph(k * 7 + 2), rot=(0, k * 45, 0), pivot=(0, 99, 0),
                 faces=("north", "south"), density=2.5)
    halo2 = m.bone("halo2", head, pivot=(0, 97, 0), rot=(16, 0, 10))
    ring(halo2, (0, 97, 0), 10.5, 12, (3.0, 1.0, 0.8), K["gold_t"], axis="y")

    # ---- the hands of a man under the wings
    for s, sx in (("r", 1), ("l", -1)):
        a1 = m.bone(f"arm_{s}_1", body, pivot=(sx * 12.5, 60, -0.5))
        a1.box((sx * 12.5, 54.5, -0.5), (4.6, 11, 4.6), K["plates2"])
        a1.box((sx * 12.5, 49.6, -0.5), (5, 1.4, 5), K["gold"])
        a2 = m.bone(f"arm_{s}_2", a1, pivot=(sx * 12.5, 49, -0.5))
        a2.box((sx * 12.5, 44, -0.5), (4.2, 10, 4.2), K["gold"], variant=1)
        a2.box((sx * 12.5, 40.4, -0.5), (4.8, 2.2, 4.8), K["gold_t"])
        a2.plane("x", (sx * 14.75, 44.5, -0.5), 3.6, 6, K["glyphs"], density=2)
        hd = m.bone(f"hand_{s}", a2, pivot=(sx * 12.5, 39.2, -0.5))
        hd.box((sx * 12.5, 36.8, -0.6), (2.4, 4.6, 3.6), K["ivory_p"])
        hd.box((sx * 12.5 - sx * 0.2, 37.4, -2.9), (1.6, 2.8, 1.2), K["ivory_p"], rot=(20, 0, 0))   # thumb
        hd.locator(f"palm_{s}", (sx * 12.5, 35, -1))

    # ---- four wings (upper pair from the shoulders, lower pair from the waist)
    wings = {}
    for s, sx in (("r", 1), ("l", -1)):
        wings[f"wu_{s}"] = feather_wing(
            m, f"wu_{s}", body, (sx * 8, 63, 7.5), sx, [20, 22, 16],
            [dict(n=3, l0=20, l1=26, w=9, a0=3, a1=10, covert=(11, 7), bones=False),
             dict(n=4, l0=28, l1=36, w=9, a0=12, a1=27, covert=(12, 7)),
             dict(n=3, l0=38, l1=43, w=9, a0=31, a1=55, covert=(12, 7))],
            K["gold"], K["f_up"], K["covert"], arm_thick=3.2, tip_feathers=dict(n=4, l=44, w=9, a0=60, a1=88))
        wings[f"wl_{s}"] = feather_wing(
            m, f"wl_{s}", body, (sx * 7, 50, 7), sx, [16, 18, 13],
            [dict(n=3, l0=17, l1=23, w=8, a0=3, a1=10, covert=(9, 6), bones=False),
             dict(n=4, l0=25, l1=31, w=8, a0=12, a1=28, covert=(10, 6)),
             dict(n=3, l0=32, l1=36, w=8, a0=32, a1=56, covert=(10, 6))],
            K["bronze"], K["f_low"], K["covert_b"], arm_thick=2.8, tip_feathers=dict(n=3, l=36, w=8, a0=62, a1=88))
    return m, wings


# ---------------------------------------------------------------------------------------------
def _euler(R):
    """Decompose R = Rz(c) Ry(e) Rx(f) (the kit's X-then-Y-then-Z order) into (rx, ry, rz) degrees."""
    e = -math.asin(max(-1.0, min(1.0, R[2, 0])))
    f = math.atan2(R[2, 1], R[2, 2])
    c = math.atan2(R[1, 0], R[0, 0])
    return tuple(round(math.degrees(v), 2) for v in (f, e, c))


def _frame(d, h):
    x = np.array(d, float)
    x /= np.linalg.norm(x)
    hh = np.array(h, float)
    hp = hh - hh.dot(x) * x
    y = -hp / np.linalg.norm(hp)        # feathers hang along local -Y
    return np.stack([x, y, np.cross(x, y)], axis=1)


def aim_wing(*segs):
    """Wing pose from body-space intent: segs = (direction, hang) per arm segment (right wing; the
    left one is mirrored by sym).  Avoids the roll that Euler angles give a forward-swung wing."""
    out, prev = [], np.eye(3)
    for d, h in segs:
        R = _frame(d, h)
        out.append(_euler(prev.T @ R))
        prev = R
    return tuple(out)


DN = (0, -1, 0)
# wing pose presets (right side; mirrored by sym): wu / wl -> (a1, a2, a3) rotations
VEIL_L = aim_wing(((0.55, -0.55, -0.62), DN), ((-0.85, -0.35, -0.4), DN), ((-0.9, -0.1, 0.2), DN))
IDLE = dict(wu=((0, -12, 40), (0, -4, 12), (0, 0, 8)), wl=VEIL_L)
HUMAN = dict(wu=((0, -6, 54), (0, -2, 16), (0, 0, 12)),
             wl=aim_wing(((0.5, -0.6, -0.62), DN), ((-0.8, -0.4, -0.45), DN), ((-0.92, -0.15, 0.1), DN)))
OX = dict(wu=aim_wing(((0.45, 0.35, -0.82), DN), ((-0.7, 0.2, -0.68), DN), ((-0.9, 0.3, -0.3), DN)),
          wl=aim_wing(((0.5, -0.2, -0.84), DN), ((-0.7, -0.15, -0.7), DN), ((-0.92, -0.05, -0.38), DN)))
OX_PRE = dict(wu=aim_wing(((0.35, 0.3, -0.88), DN), ((-0.8, 0.2, -0.56), DN), ((-0.95, 0.25, -0.1), DN)),
              wl=aim_wing(((0.4, -0.2, -0.9), DN), ((-0.8, -0.15, -0.58), DN), ((-0.95, -0.05, -0.2), DN)))
BLAST = dict(wu=((0, -30, 28), (0, -12, 8), (0, -6, 4)), wl=((0, -30, -26), (0, -12, -8), (0, -6, -4)))
W_LION_IN = dict(wu=((0, -26, 58), (0, -8, 18), (0, 0, 12)), wl=((0, -22, -10), (0, -6, -4), (0, 0, 0)))
W_LION_ROAR = dict(wu=((0, 18, 30), (0, 10, 6), (0, 4, 2)), wl=((0, 14, -34), (0, 8, -8), (0, 4, 0)))
EAGLE = dict(wu=((0, -42, 58), (0, -14, 16), (0, -4, 10)), wl=((0, -48, 26), (0, -16, 12), (0, -4, 8)))
EAGLE_DIVE = dict(wu=((0, -30, 40), (0, -10, 6), (0, -4, 0)), wl=((0, -36, 12), (0, -12, 4), (0, -4, 2)))
V_UP = dict(wu=((0, 0, 62), (0, 0, 16), (0, 0, 10)), wl=((0, 0, -52), (0, 0, -12), (0, 0, -8)))
V_DOWN = dict(wu=((0, 30, -14), (0, 10, -10), (0, 0, -6)), wl=((0, 26, -62), (0, 10, -8), (0, 0, -6)))
COCOON = dict(wu=aim_wing(((0.45, 0.45, -0.77), DN), ((-0.55, 0.35, -0.76), DN), ((-0.95, 0.1, 0.1), DN)),
              wl=aim_wing(((0.45, -0.45, -0.77), DN), ((-0.6, -0.35, -0.72), DN), ((-0.95, -0.1, 0.1), DN)))

ARISE = dict(wu=aim_wing(((0.7, 0.45, -0.55), DN), ((0.62, 0.7, -0.3), DN), ((0.42, 0.9, -0.1), DN)),
             wl=aim_wing(((0.6, -0.5, -0.62), DN), ((-0.5, -0.5, -0.7), DN), ((-0.9, -0.2, -0.1), DN)))
SHIELD_IN = dict(wu=aim_wing(((0.75, 0.4, -0.5), DN), ((0.2, 0.5, -0.85), DN), ((-0.5, 0.5, -0.7), DN)),
                 wl=aim_wing(((0.7, -0.3, -0.6), DN), ((0.1, -0.3, -0.95), DN), ((-0.6, -0.2, -0.75), DN)))

# arm presets (right side): (arm_1, arm_2, hand)
A_REST = ((-8, 0, 6), (-20, 0, 0), (0, 0, 0))
A_PRAY = ((-46, 0, -10), (-72, 0, -24), (0, 0, 10))
A_WRITE = ((-128, 0, 12), (-26, 0, 0), (-14, 0, 0))
A_OPEN = ((-58, 0, 34), (-36, 0, 0), (0, 0, 20))
A_BRACE = ((-82, 0, -6), (-34, 0, 0), (-30, 0, 0))
A_FLING = ((14, 0, 52), (-12, 0, 0), (0, 0, 12))
A_RAISE = ((-158, 0, 16), (-10, 0, 0), (0, 0, 0))
A_THRUST = ((-62, 0, 6), (-4, 0, 0), (-20, 0, 0))


def _wings(a, keys):
    for w in ("wu", "wl"):
        for j in range(3):
            k = {t: p[w][j] for t, p in keys.items()}
            sym(a, f"{w}_{{s}}_a{j + 1}", rot=k if len(k) > 1 else next(iter(k.values())))


def _arms(a, keys, left=None):
    """keys: {t: preset}; left: optional {t: preset} for the left arm (in right-side terms)."""
    for j, b in enumerate(("arm_{s}_1", "arm_{s}_2", "hand_{s}")):
        kr = {t: p[j] for t, p in keys.items()}
        kl = {t: p[j] for t, p in (left or keys).items()}
        sym(a, b, rot=kr if len(kr) > 1 else next(iter(kr.values())),
            phase_l=(kl if len(kl) > 1 else next(iter(kl.values()))) if left else None)


def _mixp(p, q, f):
    return {w: tuple(tuple(p[w][j][k] + (q[w][j][k] - p[w][j][k]) * f for k in range(3)) for j in range(3)) for w in p}


def _wake(a, bone):
    a.scl(bone, {0: 0.2, 0.25: 1.35, 0.45: 1.0})


def build_anims(wings):
    A = []
    tips = [f for w in wings.values() for f in w["feathers"] if "_t" in f]

    breathe = Anim("breathe", loop=True)
    breathe.pos("body", (0, LIFE(1.4, 4.2), 0))
    breathe.scl("head", 1.22)                     # the crown of faces is deliberately over-scaled
    breathe.rot("body", (LIFE(1.2, 6.0), 0, 0))
    breathe.rot("col3", (LIFE(1.8, 5.1, 0.1), 0, LIFE(1.4, 6.3)))
    breathe.rot("col2", (LIFE(2.6, 5.1, 0.25), 0, LIFE(2.0, 6.3, 0.2)))
    breathe.rot("col1", (LIFE(3.6, 5.1, 0.4), 0, LIFE(2.8, 6.3, 0.4)))
    breathe.rot("ring_a", (0, spin(48), 0))
    breathe.rot("ring_b", (0, spin(-34), 0))
    breathe.rot("ring_c", (0, spin(22), 0))
    breathe.rot("neck_ring", (0, spin(-40), 0))
    breathe.rot("halo", (0, spin(18), 0))
    breathe.rot("halo2", (0, spin(-46), 0))
    breathe.rot("nose_ring", (LIFE(10, 2.2), 0, 0))
    breathe.scl("censer_flame", (LIFE(0.12, 0.43, base=1.0), LIFE(0.22, 0.31, base=1.05), LIFE(0.12, 0.37, base=1.0)))
    for i in range(4):
        wave(breathe, [f"banner{i + 1}_{s + 1}" for s in range(3)], 0 if i < 2 else 2, 7 if i < 2 else -7, 3.4,
             lag=0.17, grow=1.25, clock="q.life_time")
    flutter(breathe, tips, amp=2.2, period=2.9)
    A.append(breathe)

    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    # arrive: the letter rings condense out of the air, the column tiers stack from below, the
    # cocooned wings open and the head whirls through all four faces before the human one settles
    arrive = Anim("arrive", length=T_ARRIVE, loop="hold")
    arrive.scl("root", {0: 0.45, 0.5: 0.92, 1.0: 1.03, 1.3: 1.0})
    arrive.pos("root", {0: (0, -26, 0), 0.7: (0, 3, 0), 1.1: (0, -1, 0), 1.4: (0, 0, 0)})
    for i, (b, t0) in enumerate((("ring_c", 0.0), ("ring_b", 0.08), ("ring_a", 0.16))):
        arrive.scl(b, {0: 3.2, t0 + 0.45: 0.9, t0 + 0.6: 1.0})
        arrive.pos(b, {0: (0, 30 + i * 8, 0), t0 + 0.5: (0, 0, 0)})
    arrive.pos("col1", {0: (0, -16, 0), 0.35: (0, -16, 0), 0.75: (0, 1, 0), 0.9: (0, 0, 0)})
    arrive.pos("col2", {0: (0, -10, 0), 0.25: (0, -10, 0), 0.6: (0, 1, 0), 0.75: (0, 0, 0)})
    arrive.scl("col1", {0: 0.2, 0.35: 0.2, 0.75: 1.0})
    arrive.scl("col2", {0: 0.3, 0.25: 0.3, 0.6: 1.0})
    _wings(arrive, {0: COCOON, 0.6: COCOON, 0.95: ARISE, 1.25: _mixp(IDLE, V_UP, 0.25), 1.6: IDLE})
    _arms(arrive, {0: A_PRAY, 1.0: A_PRAY, 1.6: A_REST})
    arrive.rot("drum", {0: (0, 720, 0), 1.1: (0, -12, 0), 1.35: (0, 5, 0), 1.6: (0, 0, 0)})
    arrive.rot("head", {0: (18, 0, 0), 1.1: (-8, 0, 0), 1.6: (0, 0, 0)})
    arrive.scl("halo", {0: 0.0, 0.9: 0.0, 1.3: 1.15, 1.6: 1.0})
    arrive.scl("halo2", {0: 0.0, 1.0: 0.0, 1.4: 1.1, 1.6: 1.0})
    arrive.scl("censer_flame", {0: 0.0, 0.8: 0.0, 1.1: 1.6, 1.4: 1.0})
    A.append(arrive)

    idle = Anim("idle", loop=True)
    _wings(idle, {0: IDLE})
    _arms(idle, {0: A_REST})
    A.append(idle)

    # HUMAN WITNESS: the face wakes, the right hand raised high writes in the air, then casts
    human = Anim("human", length=T_HUMAN, loop="hold")
    _wings(human, {0: IDLE, 0.5: HUMAN, 1.0: _mixp(HUMAN, V_UP, 0.25), T_HUMAN: HUMAN})
    wr = A_WRITE
    stroke = lambda dz, dy: ((wr[0][0], wr[0][1] + dy, wr[0][2] + dz), wr[1], wr[2])
    _arms(human, {0: A_REST, 0.35: wr, 0.5: stroke(10, 6), 0.62: stroke(-6, -4), 0.74: stroke(8, -8), 0.86: stroke(-4, 8),
                  0.98: wr, HUMAN_CAST: ((-96, 0, 8), (-6, 0, 0), (-30, 0, 0)), T_HUMAN: ((-92, 0, 8), (-8, 0, 0), (-26, 0, 0))},
          left={0: A_REST, 0.4: A_OPEN, T_HUMAN: A_OPEN})
    human.rot("drum", {0: (0, 0, 0), 0.15: (0, 8, 0), 0.4: (0, -4, 0), 0.6: (0, 0, 0)})
    human.rot("head", {0: (0, 0, 0), 0.3: (-10, 0, 0), 0.9: (-6, 0, 0), HUMAN_CAST: (6, 0, 0), T_HUMAN: (2, 0, 0)})
    human.rot("body", {0: (0, 0, 0), 0.9: (4, 0, 0), HUMAN_CAST: (-6, 0, 0), T_HUMAN: (-3, 0, 0)})
    _wake(human, "wake_h")
    A.append(human)

    # OX WITNESS: the head turns the ox to the front, all four wings fold forward into a crossed wall
    ox = Anim("ox", length=T_OX, loop="hold")
    ox.rot("drum", {0: (0, 0, 0), 0.1: (0, 10, 0), 0.45: (0, -98, 0), 0.6: (0, -90, 0)})
    ox.rot("head", {0: (0, 0, 0), 0.45: (-6, 0, 0), OX_LOCK: (8, 0, 0), T_OX: (6, 0, 0)})
    _wings(ox, {0: IDLE, 0.2: _mixp(IDLE, BLAST, 0.3), 0.45: SHIELD_IN, 0.62: OX_PRE, OX_LOCK: OX, T_OX: OX})
    _arms(ox, {0: A_REST, 0.5: A_BRACE, T_OX: A_BRACE})
    ox.pos("root", {0: (0, 0, 0), 0.6: (0, 1, 0), OX_LOCK: (0, -3, 0), T_OX: (0, -2, 0)})
    ox.rot("body", {0: (0, 0, 0), OX_LOCK: (-6, 0, 0), T_OX: (-4, 0, 0)})
    _wake(ox, "wake_o")
    A.append(ox)
    brace = Anim("ox_brace", loop=True, length=1.0)   # the wall trembles under the load
    for w in ("wu", "wl"):
        sym(brace, f"{w}_{{s}}_a3", rot=(0, LIFE(2.0, 0.37), LIFE(1.2, 0.29)))
    brace.scl("mane", 1.0)
    A.append(brace)

    ret = Anim("ox_retaliate", length=T_RETALIATE, loop="hold")
    ret.rot("drum", (0, -90, 0))
    ret.rot("head", {0: (6, 0, 0), 0.15: (14, 0, 0), RET_BLAST: (-16, 0, 0), T_RETALIATE: (0, 0, 0)})
    _wings(ret, {0: OX, 0.15: OX_PRE, RET_BLAST: BLAST, 0.6: _mixp(BLAST, IDLE, 0.5), T_RETALIATE: IDLE})
    _arms(ret, {0: A_BRACE, 0.15: A_PRAY, RET_BLAST: A_FLING, T_RETALIATE: A_REST})
    ret.pos("root", {0: (0, -2, 0), 0.15: (0, -5, 0), RET_BLAST: (0, 4, 0), T_RETALIATE: (0, 0, 0)})
    ret.rot("body", {0: (-4, 0, 0), 0.15: (6, 0, 0), RET_BLAST: (-8, 0, 0), T_RETALIATE: (0, 0, 0)})
    ret.scl("censer_flame", {0: 1.0, RET_BLAST: 2.2, T_RETALIATE: 1.0})
    _wake(ret, "wake_o")
    A.append(ret)

    # LION WITNESS: turn (passing the eagle), inhale with the head thrown back, then the roar
    R = LION_ROAR
    lion = Anim("lion", length=T_LION, loop="hold")
    lion.rot("drum", {0: (0, -90, 0), 0.08: (0, -80, 0), 0.5: (0, -282, 0), 0.65: (0, -270, 0)})
    lion.rot("head", {0: (0, 0, 0), 0.4: (0, 0, 0), R - 0.1: (16, 0, 0), R: (-14, 0, 0), 1.5: (-10, 0, 0), T_LION: (-2, 0, 0)})
    lion.rot("jaw_lion", {0: (0, 0, 0), R - 0.25: (0, 0, 6), R - 0.05: (0, 0, -40), 1.45: (0, 0, -36), T_LION: (0, 0, -6)})
    lion.scl("mane", {0: 1.0, R - 0.15: 0.9, R + 0.05: 1.32, 1.4: 1.22, T_LION: 1.05})
    lion.rot("mane", {0: (0, 0, 0), R: (0, 0, 0), 1.5: (0, 0, 0)})
    lion.rot("body", {0: (0, 0, 0), R - 0.1: (8, 0, 0), R: (-12, 0, 0), 1.5: (-8, 0, 0), T_LION: (0, 0, 0)})
    lion.pos("root", {0: (0, 0, 0), R - 0.1: (0, 3, 3), R: (0, -1, -4), T_LION: (0, 0, 0)})
    _wings(lion, {0: IDLE, R - 0.1: W_LION_IN, R + 0.05: W_LION_ROAR, 1.5: W_LION_ROAR, T_LION: _mixp(W_LION_ROAR, IDLE, 0.4)})
    _arms(lion, {0: A_REST, R - 0.1: ((-40, 0, 10), (-50, 0, 0), (0, 0, 0)), R + 0.05: A_FLING, T_LION: A_FLING})
    _wake(lion, "wake_l")
    lion.scl("wake_l", {0: 0.2, 0.3: 1.3, 0.45: 1.0, R: 1.5, 1.2: 1.0})
    A.append(lion)

    # EAGLE WITNESS: the eagle comes forward, wings sweep up and back with feathers splayed like
    # knives, the arms summon the blades and twice command the dive
    T1, T2 = EAGLE_THRUST
    eagle = Anim("eagle", length=T_EAGLE, loop="hold")
    eagle.rot("drum", {0: (0, -270, 0), 0.08: (0, -278, 0), 0.45: (0, -174, 0), 0.6: (0, -180, 0)})
    eagle.rot("beak_lo", {0: (0, 0, 0), 0.4: (0, 0, 0), 0.55: (26, 0, 0), 0.9: (4, 0, 0), T1 - 0.1: (0, 0, 0), T1: (24, 0, 0),
                          T1 + 0.3: (0, 0, 0), T2: (24, 0, 0), T2 + 0.3: (2, 0, 0)})
    eagle.rot("head", {0: (0, 0, 0), 0.5: (-14, 0, 0), T1 - 0.15: (-10, 0, 0), T1: (10, 0, 0), T2 - 0.2: (-8, 0, 0),
                       T2: (12, 0, 0), T_EAGLE: (4, 0, 0)})
    _wings(eagle, {0: IDLE, 0.8: EAGLE, T1 - 0.15: EAGLE, T1: EAGLE_DIVE, T1 + 0.4: EAGLE, T2 - 0.15: EAGLE, T2: EAGLE_DIVE,
                   T_EAGLE: _mixp(EAGLE_DIVE, EAGLE, 0.5)})
    _arms(eagle, {0: A_REST, 0.9: A_RAISE, T1 - 0.15: A_RAISE, T1: A_THRUST, T1 + 0.45: A_RAISE, T2 - 0.15: A_RAISE,
                  T2: A_THRUST, T_EAGLE: A_THRUST})
    eagle.pos("root", {0: (0, 0, 0), 0.9: (0, 7, 0), T1: (0, 4, -2), T1 + 0.4: (0, 7, 0), T2: (0, 4, -2), T_EAGLE: (0, 5, 0)})
    eagle.rot("body", {0: (0, 0, 0), 0.9: (-4, 0, 0), T1: (10, 0, 0), T1 + 0.4: (-2, 0, 0), T2: (10, 0, 0), T_EAGLE: (4, 0, 0)})
    for wname in ("wu", "wl"):
        fr = wings[f"{wname}_r"]["feathers"]
        for k, f in enumerate(fr):
            sp = 4 + 3.0 * k                      # splay the flight feathers like blades
            pat = f.replace(f"{wname}_r", f"{wname}_{{s}}", 1)
            sym(eagle, pat, rot={0: (0, 0, 0), 0.5: (0, 0, 0), 0.9: (8, 0, sp), T_EAGLE: (8, 0, sp)})
    _wake(eagle, "wake_e")
    A.append(eagle)

    # VERDICT (ultimate finisher): the drum whirls through all four faces, wings rise then slam down
    H = VERDICT_HIT
    verdict = Anim("verdict", length=T_VERDICT, loop="hold")
    verdict.rot("drum", {0: (0, 0, 0), 0.15: (0, 14, 0), H - 0.05: (0, -360, 0), H + 0.15: (0, -366, 0), T_VERDICT: (0, -360, 0)})
    verdict.rot("head", {0: (0, 0, 0), H - 0.2: (-18, 0, 0), H: (14, 0, 0), T_VERDICT: (8, 0, 0)})
    _wings(verdict, {0: IDLE, 0.45: V_UP, H - 0.1: _mixp(V_UP, V_DOWN, -0.15), H: V_DOWN, T_VERDICT: V_DOWN})
    _arms(verdict, {0: A_REST, 0.45: A_RAISE, H - 0.1: A_RAISE, H: A_THRUST, T_VERDICT: A_THRUST})
    verdict.pos("root", {0: (0, 0, 0), H - 0.1: (0, 12, 2), H: (0, -2, -3), T_VERDICT: (0, 0, -2)})
    verdict.rot("body", {0: (0, 0, 0), H - 0.1: (-10, 0, 0), H: (12, 0, 0), T_VERDICT: (8, 0, 0)})
    verdict.rot("jaw_lion", {0: (0, 0, 0), H: (0, 0, -34), T_VERDICT: (0, 0, -20)})
    verdict.rot("beak_lo", {0: (0, 0, 0), H: (24, 0, 0), T_VERDICT: (10, 0, 0)})
    verdict.scl("mane", {0: 1.0, H: 1.3, T_VERDICT: 1.15})
    verdict.scl("halo", {0: 1.0, H - 0.1: 0.85, H: 1.5, T_VERDICT: 1.3})
    for b in ("wake_h", "wake_l", "wake_o", "wake_e"):
        _wake(verdict, b)
    A.append(verdict)

    # DEPART: wings cocoon, the column tiers fall away into letters, the rings flare outward and
    # the sealed figure is drawn up into a single line of light
    depart = Anim("depart", length=T_DEPART, loop="hold")
    depart.rot("drum", {0: (0, 0, 0), 0.5: (0, 90, 0), T_DEPART: (0, 540, 0)})
    _wings(depart, {0: IDLE, 0.35: ARISE, 0.6: COCOON, T_DEPART: COCOON})
    _arms(depart, {0: A_REST, 0.5: A_PRAY, T_DEPART: A_PRAY})
    depart.pos("col1", {0: (0, 0, 0), 0.6: (0, 0, 0), 1.0: (0, -14, 0)})
    depart.scl("col1", {0: 1.0, 0.6: 1.0, 1.0: 0.0})
    depart.pos("col2", {0: (0, 0, 0), 0.75: (0, 0, 0), 1.15: (0, -12, 0)})
    depart.scl("col2", {0: 1.0, 0.75: 1.0, 1.15: 0.0})
    for i, b in enumerate(("ring_a", "ring_b", "ring_c")):
        depart.scl(b, {0: 1.0, 0.5 + i * 0.1: 1.0, 1.1 + i * 0.1: 3.2, 1.3 + i * 0.1: 0.0})
        depart.pos(b, {0: (0, 0, 0), 0.5: (0, 0, 0), 1.2 + i * 0.1: (0, 20 + i * 6, 0)})
    depart.scl("halo", {0: 1.0, 1.0: 1.6, 1.5: 0.0})
    depart.scl("halo2", {0: 1.0, 1.0: 1.8, 1.45: 0.0})
    depart.pos("root", {0: (0, 0, 0), 0.7: (0, -2, 0), 1.2: (0, 10, 0), T_DEPART: (0, 64, 0)})
    depart.scl("root", {0: 1.0, 1.1: 1.0, 1.55: (0.3, 1.5, 0.3), T_DEPART: (0.0, 2.0, 0.0)})
    depart.scl("censer_flame", {0: 1.0, 0.5: 2.0, 1.0: 0.0})
    A.append(depart)
    return A


STATES = {0: ["hidden"], 1: ["arrive"], 2: ["idle"], 3: ["human"], 4: ["ox", "ox_brace"], 5: ["ox_retaliate"],
          6: ["lion"], 7: ["eagle"], 8: ["verdict"], 9: ["depart"]}


def _vis(states):
    return " || ".join(f"q.property('grimoire:state') == {s}" for s in states)


VISIBILITY = [{"wake_h": _vis((3, 8))}, {"wake_o": _vis((4, 5, 8))}, {"wake_l": _vis((6, 8))}, {"wake_e": _vis((7, 8))}]


# ---------------------------------------------------------------------------------------------
# feather-blade helper
def _blade_mat(edge, core, key, glow=0.75):
    ke, kc = tex.rgb(edge), tex.rgb(core)

    def fn(ctx):
        ix, iy = tex.px(ctx)
        u = ctx.U * 2 - 1
        v = ctx.V
        width = np.where(v < 0.32, 0.3 + 0.7 * (v / 0.32), np.clip(1 - (v - 0.32) / 0.68, 0, 1) ** 0.85)
        inside = np.abs(u) <= width * 0.96
        t = tex.tile(ctx, core, 1.0, glow)
        d = np.abs(u) / np.maximum(width, 1e-3)
        t[..., :3] = tex.mix(kc, ke, np.clip(d, 0, 1)[..., None] ** 2)
        barb = ((iy + (np.abs(ix - (ctx.w - 1) / 2)).astype(int)) % 4 == 0) & (d > 0.15)
        t[..., :3] = np.where(barb[..., None], t[..., :3] * 0.82, t[..., :3])
        rim = d > 0.82
        t[..., 4] = np.where(rim, 1.0, glow * (0.6 + 0.4 * v))
        mid = np.abs(ix - (ctx.w - 1) / 2) < 0.75
        t[..., :3] = np.where(mid[..., None], tex.rgb("#ffd76a"), t[..., :3])
        gl = (tex._hash(ix // 2, iy // 3, 51) > 0.78) & ~mid & (d < 0.75) & ((iy % 3) != 0)
        t[..., :3] = np.where(gl[..., None], tex.rgb("#ffffff"), t[..., :3])
        t[..., 3] = np.where(inside, 1.0, 0.0)
        return t
    return Mat(fn, key, directional=True)


def _streak_mat(color, key):
    kc = tex.rgb(color)

    def fn(ctx):
        u = ctx.U * 2 - 1
        t = tex.tile(ctx, color, 0.0, 1.0)
        t[..., :3] = kc
        t[..., 3] = np.clip(ctx.V ** 1.4 * (1 - np.abs(u) ** 1.5) * 0.85, 0, 1)
        return t
    return Mat(fn, key, mode="blend", directional=True)


def blade_model():
    K = _mats()
    m = Model("dw_cherub_blade", density=2.0, bounds=(8, 10, (0, 3, 0)))
    root = m.bone("root")
    bl = m.bone("blade", root)
    bm = _blade_mat("#ffffff", "#fff1c2", "cherubblade")
    bl.plane("z", (0, 28, 0), 12, 54, bm)
    bl.plane("x", (0, 28, 0), 12, 54, bm)
    bl.box((0, 30, 0), (1.4, 46, 1.4), K["gold_t"])
    bl.box((0, 56.5, 0), (11, 1.8, 1.8), K["gold"])
    bl.box((0, 56.5, 0), (1.8, 1.8, 11), K["gold"], variant=1)
    ring(bl, (0, 59.5, 0), 2.4, 8, (2.0, 0.8, 1.4), K["gold_t"], axis="y")
    bl.box((0, 63.5, 0), (2.6, 3.2, 2.6), K["gem"].but(key="cherubpommel"), rot=(0, 45, 0))
    bl.box((0, 63.5, 0), (2.2, 3.6, 2.2), tex.glow_flat("#ffffff", 1.0, core="#dfe8ff"))
    bl.locator("tip", (0, 1, 0))
    barb = _blade_mat("#ffffff", "#ffe39a", "cherubbarb", glow=0.6)
    for k, (s, ry) in enumerate(((1, 0), (-1, 0), (1, 90), (-1, 90))):
        b = m.bone(f"barb{k + 1}", bl, pivot=(0, 50, 0), rot=(0, ry, s * 30))
        b.plane("z", (s * 3.2, 38, 0), 5, 22, barb, variant=k % 2)
    tr = m.bone("trail", root)
    st = _streak_mat("#fff3c4", "cherubstreak")
    tr.plane("z", (0, 96, 0), 9, 64, st)
    tr.plane("x", (0, 96, 0), 9, 64, st)
    return m


def blade_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    form = Anim("form", length=BLADE_FORM, loop="hold")
    form.scl("root", {0: 0.0, 0.35: 1.15, BLADE_FORM: 1.0})
    form.rot("root", {0: (0, -540, 0), BLADE_FORM: (0, 0, 0)})
    form.scl("trail", 0.0)
    aim = Anim("aim", loop=True, length=1.0)
    aim.pos("root", (0, LIFE(1.2, 0.9), 0))
    aim.rot("blade", (LIFE(1.6, 0.23), spin(120), LIFE(1.6, 0.29, 0.3)))
    aim.scl("trail", 0.0)
    dive = Anim("dive", length=BLADE_DIVE, loop="hold")
    dive.scl("root", {0: (1, 1, 1), 0.1: (0.8, 1.4, 0.8)})
    dive.scl("trail", {0: 0.0, 0.08: 1.0})
    shatter = Anim("shatter", length=BLADE_SHATTER, loop="hold")
    shatter.scl("blade", {0: 1.0, 0.08: (1.3, 0.55, 1.3), BLADE_SHATTER: (0.0, 0.0, 0.0)})
    shatter.scl("trail", {0: 1.0, 0.12: 0.0})
    for k, (s, ry) in enumerate(((1, 0), (-1, 0), (1, 90), (-1, 90))):
        dx = s * 18 if ry == 0 else 0
        dz = s * 18 if ry == 90 else 0
        shatter.pos(f"barb{k + 1}", {0: (0, 0, 0), BLADE_SHATTER: (dx, 8, dz)})
        shatter.rot(f"barb{k + 1}", {0: (0, 0, 0), BLADE_SHATTER: (0, 0, s * 140)})
    return [hidden, form, aim, dive, shatter]


BLADE_STATES = {0: ["hidden"], 1: ["form"], 2: ["aim"], 3: ["dive"], 4: ["shatter"]}


# roar ring helper: a vertical ring of letters carried forward by the lion's roar
def roar_model():
    K = _mats()
    m = Model("dw_cherub_roar", density=2.0, bounds=(30, 30, (0, 0, 0)))
    root = m.bone("root")
    band = m.bone("band", root)
    ring(band, (0, 0, 0), 22, 18, (6.4, 2.6, 1.6), K["gold_t"], axis="z", cycle=2)
    for k in range(12):
        a = k * 30
        band.box((0, 27.5, 0), (4, 5.4, 0), _glyph(k * 3 + 4), rot=(0, 0, a), pivot=(0, 0, 0),
                 faces=("north", "south"), density=2)
    wv = m.bone("wave", root)
    wv.plane("z", (0, 0, 0), 52, 52, tex.shaped(tex.m_ring(0.62, 0.86), "#fff3c4", "#ffd76a", glow=1.0, var=0, a=0.45,
                                                 mode="blend", key="cherubroarwave"))
    return m


def roar_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    blast = Anim("blast", length=ROAR_LIFE, loop="hold")
    blast.scl("root", {0: 0.25, 0.25: 1.4, 0.85: 3.4, ROAR_LIFE: 4.2})
    blast.rot("band", {0: (0, 0, 0), ROAR_LIFE: (0, 0, 220)}, smooth=False)
    blast.scl("wave", {0: 1.2, ROAR_LIFE: 0.9})
    return [hidden, blast]


# ---------------------------------------------------------------------------------------------
def build_fx(pack):
    fx = particles(pack)
    fx.effect("dw_cherub_ember", "ember", count=6, life=(0.8, 1.6), size=(0.1, 0.02), shape=("sphere", 0.5),
              speed=(0.3, 1.0), accel=(0, 1.4, 0), drag=0.8, colors=["#fff6d0ff", "#ffb040ff", "#c9602000"], spin=(360, 60))
    fx.effect("dw_cherub_glyph", None, sprites=[f"glyph{i}" for i in range(1, 9)], count=2, life=(0.45, 0.8),
              size=(0.24, 0.08), shape=("sphere", 0.25), speed=(0.1, 0.4), drag=1.0,
              colors=["#ffffffff", "#fff3c4ff", "#c9a24a00"])
    fx.effect("dw_cherub_quake", "ringthin", count=1, life=(0.6, 0.7), size=(0.6, 10.0), facing="emitter_transform_xz",
              colors=["#ffffffff", "#ffd76acc", "#a8783a00"])
    fx.effect("dw_cherub_dust", "puff", count=14, life=(0.7, 1.3), size=(0.4, 1.1), shape=("disc", 2.5), speed=(3.0, 6.5),
              accel=(0, 0.6, 0), drag=2.2, colors=["#d9c9a0cc", "#a8957000"], blend="blend", spin=(360, 50))
    fx.effect("dw_cherub_shield", "diamond", count=10, life=(0.6, 1.1), size=(0.18, 0.04), shape=("sphere", 2.2, "surface"),
              speed=(0.1, 0.5), accel=(0, 0.6, 0), colors=["#ffffffff", "#fff3c4ff", "#2b3f8f00"], spin=(360, 90))
    fx.effect("dw_cherub_absorb", "star", count=8, life=(0.35, 0.5), size=(0.2, 0.05), shape=("sphere", 1.4, "surface"),
              direction="inwards", speed=(2.5, 3.5), colors=["#ffffffff", "#ffd76aff", "#c9a24a00"], spin=(360, 180))
    fx.effect("dw_cherub_roar", "wave", count=1, life=(0.35, 0.45), size=(0.8, 3.6), colors=["#fff3c4ff", "#ffd76a00"])
    fx.effect("dw_cherub_breath", "spark", count=16, life=(0.3, 0.7), size=(0.2, 0.0), shape=("sphere", 0.6),
              speed=(4, 9), drag=1.6, colors=["#ffffffff", "#ffe08aff", "#c9a24a00"], spin=(360, 300))
    fx.effect("dw_cherub_trail", "beam", count=3, life=(0.2, 0.35), size=(0.16, 0.02), size_y=(1.6, 0.4),
              shape=("sphere", 0.3), facing="lookat_y", colors=["#ffffffff", "#fff3c400"])
    fx.effect("dw_cherub_shatter", "shard", count=16, life=(0.5, 1.0), size=(0.18, 0.04), shape=("sphere", 0.5),
              speed=(4, 9), accel=(0, -9, 0), drag=0.9, colors=["#ffffffff", "#fff3c4ff", "#c9a24a00"], spin=(360, 400))
    fx.effect("dw_cherub_feather", "feather", count=5, life=(1.4, 2.4), size=(0.26, 0.18), shape=("sphere", 2.4),
              speed=(0.4, 1.4), accel=(0, -1.0, 0), drag=1.6, colors=["#fffdf4ff", "#e8c468cc", "#c9a24a00"],
              blend="blend", spin=(360, 140))


def build_sounds(pack):
    def chord(f, vowel, dur, ratios=(1.0, 1.26, 1.5), bright=1.0, voices=4):
        return sy.mixdown([sy.choir(f * r, dur, vowel, voices=voices, bright=bright) for r in ratios])

    # arrival: bronze ground-swell, rising choir, scribbling letters, a heavy bronze strike
    arr = sy.at(2.4, (0.0, sy.rumble(2.0, 46) * 0.55), (0.0, sy.scribble(1.2, 9) * 0.35),
                (0.3, chord(110.0, "oh", 1.8, (1.0, 1.5, 2.0)) * 0.6), (0.9, sy.choir(330, 1.2, "ah", voices=4) * 0.35),
                (1.3, sy.bell(98.0, 1.1, bright=0.7, inharm=1.25) * 0.7), (1.3, sy.thump(0.8, 120, 34, 0.5) * 0.6))
    sy.save(pack, "dw_cherub_arrive", sy.reverb(arr, 1.2, 0.4), max_distance=72)
    # the drum of faces turning: grinding bronze and a soft toll
    turn = sy.at(1.0, (0.0, sy.creak(0.6, 70, 110, 0.15) * 0.45), (0.0, sy.lowpass(sy.noise(0.6), 400) * 0.3),
                 (0.45, sy.bell(196.0, 0.6, bright=0.6, inharm=1.3) * 0.45))
    sy.save(pack, "dw_cherub_turn", sy.reverb(sy.lowpass(turn, 3000), 1.0, 0.3), volume=0.9,
            variants=[sy.reverb(sy.lowpass(sy.pitch(turn, 0.88), 3000), 1.0, 0.3)])
    # HUMAN voice: a short wordless choir phrase (three overlapping tones over a fifth drone)
    ph = sy.at(1.8, (0.0, sy.choir(196.0, 1.7, "oo", voices=4) * 0.35), (0.0, sy.choir(293.7, 1.7, "oo", voices=3) * 0.25),
               (0.05, sy.choir(370.0, 0.55, "ah", attack=0.08, release=0.25) * 0.6),
               (0.45, sy.choir(440.0, 0.55, "ah", attack=0.08, release=0.25) * 0.55),
               (0.85, sy.choir(415.3, 0.9, "eh", attack=0.1, release=0.5) * 0.6), (0.3, sy.scribble(1.0, 8) * 0.25))
    sy.save(pack, "dw_cherub_human", sy.reverb(ph, 1.2, 0.42), max_distance=64)
    gl = sy.at(0.6, (0.0, sy.scribble(0.25, 3) * 0.6), (0.08, sy.pluck(1567.98, 0.4, 0.8) * 0.6),
               (0.12, sy.pluck(2349.3, 0.35, 0.8) * 0.4))
    sy.save(pack, "dw_cherub_glyph", sy.reverb(gl, 0.9, 0.3), volume=0.7, max_distance=32,
            variants=[sy.reverb(sy.pitch(gl, 1.12), 0.9, 0.3)])
    # OX voice: a low horn-like drone (formant-shaped saw with a slow swell)
    src = sy.osc(sy.sweep(58.0, 62.0, 2.2), wave_="saw") + 0.4 * sy.osc(sy.sweep(116.0, 124.0, 2.2), wave_="saw")
    horn = sy.formants(src, [(380, 120, 1.0), (760, 160, 0.55), (1500, 260, 0.2)])
    horn = sy.norm(horn * sy.env(2.2, 0.5, 0.2, 0.85, 0.7))
    ox = sy.at(2.2, (0.0, horn * 0.8), (0.0, sy.choir(123.5, 2.2, "oo", voices=4) * 0.3), (0.2, sy.rumble(1.8, 40) * 0.4))
    sy.save(pack, "dw_cherub_ox", sy.reverb(ox, 1.0, 0.33), max_distance=72)
    sh = sy.at(1.3, (0.0, sy.whoosh(0.5, 300, 1800) * 0.5), (0.4, sy.bell(146.8, 0.9, bright=0.8, inharm=1.4) * 0.6),
               (0.4, sy.thump(0.6, 90, 40, 0.6) * 0.6), (0.45, sy.shimmer(0.8, 1600, 14) * 0.3))
    sy.save(pack, "dw_cherub_shield", sy.reverb(sh, 1.4, 0.35), max_distance=56)
    ab = sy.at(0.6, (0.0, sy.thump(0.3, 160, 70, 0.4) * 0.5), (0.02, sy.bell(587.3, 0.45, bright=0.7) * 0.4),
               (0.0, sy.shimmer(0.4, 2400, 8) * 0.3))
    sy.save(pack, "dw_cherub_absorb", sy.reverb(ab, 0.8, 0.3), volume=0.8, max_distance=32)
    rt = sy.at(1.8, (0.0, sy.thump(1.1, 140, 28, 0.8)), (0.0, sy.crack(0.5, 4500, 12) * 0.35),
               (0.02, horn[:int(sy.SR * 1.2)] * np.linspace(1, 0, int(sy.SR * 1.2)) * 0.7),
               (0.05, sy.whoosh(0.7, 2400, 300) * 0.4))
    sy.save(pack, "dw_cherub_retaliate", sy.reverb(rt, 1.2, 0.33), max_distance=72)
    # LION voice: a roar blended with a bright choir
    li = sy.at(2.0, (0.0, sy.roar(1.9, 125, 62, growl=30, rough=0.7, formant=(520, 1250), breath=0.45, bend=0.3) * 0.9),
               (0.08, chord(146.8, "ah", 1.7, (1.0, 1.5, 2.0), bright=1.3) * 0.45), (0.0, sy.thump(0.7, 80, 30, 0.5) * 0.5),
               (0.15, sy.wind(1.4, 600, 2600, 1.5, 0.3) * 0.25))
    sy.save(pack, "dw_cherub_lion", sy.reverb(li, 1.2, 0.36), max_distance=80)
    # EAGLE voice: a piercing descending cry with a high choir halo
    cry_f = np.concatenate([sy.sweep(1350, 2500, 0.18, 0.6), sy.sweep(2500, 1250, 0.75, 1.4)])
    cry = sy.osc(cry_f * (1 + 0.02 * np.sin(2 * np.pi * 23 * np.arange(len(cry_f)) / sy.SR)), wave_="saw")
    cry = sy.formants(cry, [(2300, 500, 1.0), (3600, 700, 0.5), (1300, 300, 0.3)])
    cry = sy.norm(cry * sy.env(len(cry_f) / sy.SR, 0.03, 0.1, 0.8, 0.35))
    ea = sy.at(1.8, (0.0, cry * 0.7), (0.05, sy.bandpass(sy.noise(0.8), 3200, 2.0) * sy.env(0.8, 0.02, 0.1, 0.5, 0.4) * 0.25),
               (0.1, sy.choir(880.0, 1.2, "ee", voices=3) * 0.3), (0.0, sy.whoosh(0.6, 800, 4000) * 0.3))
    sy.save(pack, "dw_cherub_eagle", sy.reverb(ea, 1.2, 0.33), max_distance=80)
    bl = sy.at(1.0, (0.0, sy.shimmer(0.7, 2600, 14) * 0.5), (0.0, sy.whoosh(0.5, 900, 5000) * 0.35),
               (0.25, sy.bell(1318.5, 0.6, bright=1.3) * 0.35))
    sy.save(pack, "dw_cherub_blade", sy.reverb(bl, 1.0, 0.3), volume=0.8, max_distance=48)
    dv = sy.at(0.5, (0.0, sy.whoosh(0.4, 5000, 600) * 0.8))
    sy.save(pack, "dw_cherub_dive", dv, volume=0.9, max_distance=48)
    im = sy.at(1.4, (0.0, sy.crack(0.5, 7000, 16) * 0.5), (0.0, sy.thump(0.7, 150, 40, 0.6) * 0.7),
               (0.01, sy.bell(783.99, 1.1, bright=1.2) * 0.45), (0.01, sy.bell(1174.7, 0.9) * 0.25))
    sy.save(pack, "dw_cherub_impact", sy.reverb(im, 1.4, 0.32), max_distance=56,
            variants=[sy.reverb(sy.pitch(im, 1.1), 1.4, 0.32), sy.reverb(sy.pitch(im, 0.92), 1.4, 0.32)])
    rr = sy.at(1.2, (0.0, sy.whoosh(1.0, 300, 2400) * 0.6), (0.0, sy.scribble(0.6, 6) * 0.3))
    sy.save(pack, "dw_cherub_ring", sy.reverb(rr, 1.0, 0.3), volume=0.8, max_distance=48)
    # departure: the four voices fold into one sustained chord that rises and thins away
    dp = sy.at(2.2, (0.0, chord(146.8, "oo", 2.0, (1.0, 1.5, 2.0, 3.0), voices=3) * 0.55),
               (0.0, sy.whoosh(1.6, 200, 3600) * 0.3), (0.6, sy.shimmer(1.5, 2800, 18)[::-1] * 0.35),
               (0.0, sy.lowpass(horn, 400)[:int(sy.SR * 1.2)] * 0.25))
    sy.save(pack, "dw_cherub_depart", sy.reverb(dp, 1.2, 0.42), max_distance=72)


def build(pack):
    build_fx(pack)
    build_sounds(pack)
    m, wings = build_model()
    anims = build_anims(wings)
    pack.actor("cherub", m, anims, STATES, always=["breathe"], scale=2.0, lifetime=120, display="Cherubim",
               visibility=VISIBILITY, blend=0.15)
    bm = blade_model()
    ba = blade_anims()
    pack.actor("dw_cherub_blade", bm, ba, BLADE_STATES, lifetime=40, display="Feather Blade", blend=0.05)
    rm = roar_model()
    ra = roar_anims()
    pack.actor("dw_cherub_roar", rm, ra, {0: ["hidden"], 1: ["blast"]}, lifetime=20, display="Roar of Letters", blend=0.0)

    by = {a.name: a for a in anims}
    br = (by["breathe"], 1.0)
    pack.preview("cherub_a", m, [[(by["idle"], 0), br]], views=((25, 12), (115, 12), (-115, 12), (200, 15)),
                 hide=("wake_",))
    pack.preview("cherub_b", m, [[(by["human"], 0.7), br], [(by["ox"], T_OX), br], [(by["lion"], LION_ROAR + 0.1), br],
                                 [(by["eagle"], 1.2), br]], views=((25, 12), (-70, 10), (0, 55)))
    pack.preview("cherub_head", m, [[(by["idle"], 0), br]], views=((0, 5), (90, 5), (180, 5), (-90, 5)),
                 hide=("wing", "wu_", "wl_", "halo", "arm_", "banner", "ring_"), fit=None, cell=(360, 360))
    pack.preview("cherub_c", m, [[(by["arrive"], 0.85), br], [(by["arrive"], 1.1), br], [(by["ox"], 0.4), br],
                                 [(by["ox"], 0.6), br], [(by["depart"], 0.45), br]], views=((35, 12), (-60, 10)))
    pack.preview("dw_cherub_helpers", bm, [(ba[2], 0.2), (ba[3], 0.2), (ba[4], 0.25)], views=((20, 10), (0, 60)))
    pack.preview("dw_cherub_roar", rm, [(ra[1], 0.3)], views=((0, 0), (40, 20)))
    print(f"    cherub: {m.cube_count()} cubes, {len(m.order)} bones, tex {m.tex_size}; "
          f"blade {bm.cube_count()}/{len(bm.order)} {bm.tex_size}; roar {rm.cube_count()} {rm.tex_size}")
