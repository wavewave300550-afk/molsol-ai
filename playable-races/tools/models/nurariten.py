"""Race 006 - Nurariten (นูราริเทน), the Uninvited Sovereign.  UNIQUE race.

A celestial sovereign built from the yokai Nurarihyon's later popular image (the
gourd-headed elder who walks into a house and is taken for its master) turned into
heavenly aristocracy: a throne that walks.

  * elongated cranium curving back (the gourd silhouette), an ivory mask-like face
    with narrow golden eyes and vertical pupils, a gold diadem
  * a fragmented golden halo - arcs and glyph tablets floating around the head
  * an elongated neck in layered ceremonial collars
  * tall slender robes in ivory, aged gold and deep vermilion; stiff shoulder wings
  * long sleeves that hide the hands; slender long-fingered hands appear to hold
    items and to issue decrees
  * architectural halos and a heavenly gate on the back that unfold into a court
    (Uninvited Temple) or a throne-palace (the ultimate)

Variants: base | nocturne (night radiance) | edict | court | throne.
Helper models: the celestial gate, the heralds and the procession columns.
"""
from __future__ import annotations

import math

import numpy as np

from kit.geo import Model
from kit.tex import Ctx, hx
from kit import noise as nz
from models.common import humanoid, side_rot, fp_sleeves, ramp, bevel, face_light, mix3, clamp01, accents, mat_accent, ring_cubes

ID = "nurariten"
VARIANTS = ["base", "nocturne", "edict", "court", "throne"]
TEXTURES = {
    "base": {"radiant": 0.0, "night": 0.0},
    "nocturne": {"radiant": 0.35, "night": 1.0},
    "radiant": {"radiant": 1.0, "night": 0.0},
}
VARIANT_TEXTURE = {"base": "base", "nocturne": "nocturne", "edict": "radiant", "court": "radiant", "throne": "radiant"}
GRAND = {"court", "throne"}
HALO = 8


def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=512)
    humanoid(m)
    _legs(m)
    _robe(m)
    _arms(m)
    _head(m)
    _halo(m)
    _back(m)
    fp_sleeves(m, "silk", width=5.2)
    accents(m, [
        ("c", "breast", "robe", (0, 20.4, -2.45), (4.6, 3.0, 0.5)),
        ("c", "rsh", "r_arm_g", (-6.4, 23.0, 0.2), (3.8, 0.8, 5.0)),
        ("c", "lsh", "l_arm_g", (6.4, 23.0, 0.2), (3.8, 0.8, 5.0)),
        ("l", "r", "r_leg_g", (-2.1, 8.0, -2.6), (3.6, 3.0, 0.5)),
        ("l", "l", "l_leg_g", (2.1, 8.0, -2.6), (3.6, 3.0, 0.5)),
        ("f", "r", "r_leg_g", (-2.1, 1.2, -2.7), (3.4, 1.0, 0.5)),
        ("f", "l", "l_leg_g", (2.1, 1.2, -2.7), (3.4, 1.0, 0.5)),
    ])
    m.pack()
    return m


# ----------------------------------------------------------------------------- legs: wide hakama, lacquered clogs

def _legs(m: Model) -> None:
    for side, g, p in ((-1, "r_leg_g", "r"), (1, "l_leg_g", "l")):
        x = 2.1 * side
        m.box(g, (x, 6.6, 0.0), (4.6, 11.0, 5.0), "silk_red")                     # hakama leg
        m.box(g, (x, 1.3, 0.0), (4.9, 0.8, 5.3), "gold")                          # hem band
        m.box(g, (x, 0.45, -0.6), (3.0, 0.9, 4.4), "lacquer")                     # geta clog
        m.box(g, (x, 0.25, -0.6), (2.6, 0.5, 0.6), "lacquer")
        m.bones[g].locators[f"{p}_step"] = (x, 0.2, -0.6)


# ----------------------------------------------------------------------------- robes

def _robe(m: Model) -> None:
    t = m.bone("robe", "torso_g", (0, 12, 0))
    m.box(t.name, (0, 18.2, 0.2), (6.4, 12.4, 4.2), "silk_red")                  # inner robe
    for side in (-1, 1):
        # outer ivory panels crossing at the chest (kimono overlap), gold-edged
        m.box(t.name, (1.6 * side, 18.4, -2.15), (3.4, 12.0, 0.5), "silk")
        m.box(t.name, (3.3 * side, 18.4, 0.2), (0.5, 12.0, 4.4), "silk")
    m.box(t.name, (0, 18.4, 2.45), (6.8, 12.0, 0.5), "silk")
    m.box(t.name, (0, 15.4, 0.2), (7.0, 2.0, 4.8), "gold")                       # obi sash
    m.box(t.name, (0, 15.4, 2.9), (2.6, 2.6, 1.2), "silk_red")                  # sash knot
    m.box(t.name, (0, 21.4, -2.45), (1.2, 5.8, 0.3), "gold")                     # collar seam
    # stiff ceremonial shoulder wings
    for side, p in ((-1, "r"), (1, "l")):
        w = m.bone(f"{p}_wing", t.name, (3.4 * side, 23.6, 0.2), side_rot((0, 0, 10), side))
        w.variant.update({"court": ((0, 0, 0), side_rot((0, 0, 22), side)), "throne": ((0, 0, 0), side_rot((0, 0, 18), side))})
        m.box(w.name, (5.6 * side, 23.6, 0.2), (4.6, 0.7, 5.0), "silk")
        m.box(w.name, (7.9 * side, 23.5, 0.2), (0.4, 0.9, 5.2), "gold")
    # front and back over-skirts that sway from the waist
    for name, z, rot in (("skirt_f", -2.4, (-4, 0, 0)), ("skirt_b", 2.6, (4, 0, 0))):
        sk = m.bone(name, t.name, (0, 14.4, z), rot)
        sk.variant.update({"court": ((0, 0, 0), (rot[0] * 3, 0, 0))})
        m.box(sk.name, (0, 9.4, z), (7.2, 10.0, 0.5), "silk")
        m.box(sk.name, (0, 4.6, z), (7.4, 0.6, 0.6), "gold")
    # layered collars around the long neck
    for k, (sz, mat) in enumerate(((4.8, "gold"), (4.0, "silk_red"), (3.4, "silk"))):
        m.box(t.name, (0, 24.3 + k * 0.6, 0.2), (sz, 0.6, sz), mat)
    t.locators["chest"] = (0, 20.0, -2.6)
    t.locators["feet"] = (0, 0.2, 0)


# ----------------------------------------------------------------------------- sleeves and hands

def _arms(m: Model) -> None:
    for side, g, p in ((-1, "r_arm_g", "r"), (1, "l_arm_g", "l")):
        ax = 6.2 * side
        sl = m.bone(f"{p}_sleeve", g, (5.0 * side, 22.4, 0.2))
        sl.variant.update({"court": ((0, 0, 0), side_rot((0, 0, 18), side)), "edict": ((0, 0, 0), side_rot((-14, 0, 6), side))})
        m.box(sl.name, (ax, 20.6, 0.2), (3.4, 3.4, 3.8), "silk")                     # shoulder
        m.box(sl.name, (ax - 0.2 * side, 14.6, 0.2), (4.6, 9.6, 5.2), "silk")        # the long wide sleeve
        m.box(sl.name, (ax - 0.2 * side, 9.6, 0.2), (4.4, 0.6, 5.0), "silk_red")     # vermilion lining at the cuff
        m.box(sl.name, (ax - 0.2 * side, 10.0, 0.2), (4.9, 0.5, 5.5), "gold")
        # the hand rests concealed high inside the sleeve; it is drawn out (4.6 units down)
        # to hold an item or to issue a decree
        H = 4.6
        hand = m.bone(f"{p}_hand", g, (ax - 0.1 * side, 11.2 + H, -0.2))
        hand.variant.update({v: ((0, -H, 0), None) for v in ("edict", "court", "throne")})
        m.box(hand.name, (ax - 0.1 * side, 9.6 + H, -0.2), (1.8, 2.0, 1.2), "skin")
        for k in range(4):
            fz = -0.65 + k * 0.42
            f = m.bone(f"{p}_finger{k}", hand.name, (ax - 0.1 * side, 8.7 + H, fz))
            ln = (3.0, 3.4, 3.2, 2.6)[k]
            m.cube(f.name, (ax - 0.1 * side - 0.17, 8.7 + H - ln, fz - 0.17), (0.34, ln, 0.34), "skin")
            m.cube(f.name, (ax - 0.1 * side - 0.19, 8.7 + H - ln - 0.5, fz - 0.19), (0.38, 0.5, 0.38), "gold")   # nail guard
        th = m.bone(f"{p}_thumb", hand.name, (ax - 0.9 * side, 9.4 + H, -0.6), side_rot((0, 0, -25), side))
        m.cube(th.name, (ax - 0.9 * side - 0.18, 7.6 + H, -0.78), (0.36, 1.8, 0.36), "skin")
        hand.locators[f"{p}_fingertip"] = (ax - 0.1 * side, 5.2 + H, -0.2)


# ----------------------------------------------------------------------------- head

def _head(m: Model) -> None:
    sk = m.bone("skull", "head_g", (0, 24.0, 0.0))
    sk.variant.update({"throne": ((0, 0.6, 0), (-6, 0, 0))})
    m.box(sk.name, (0, 25.1, 0.2), (2.4, 2.4, 2.4), "skin")                       # long neck
    m.box(sk.name, (0, 28.2, -0.2), (4.6, 4.4, 4.2), "skin")                       # jaw and temples
    m.box(sk.name, (0, 28.4, -2.35), (4.2, 4.6, 0.5), "mask")                      # the mask-like face
    # the elongated cranium curving back (the gourd of Nurarihyon)
    for (y, z, w, h, d) in ((31.2, 0.6, 4.6, 2.2, 4.6), (32.5, 1.9, 4.0, 1.6, 4.2), (33.0, 3.4, 3.2, 1.4, 3.4), (32.8, 4.9, 2.2, 1.2, 2.4)):
        m.box(sk.name, (0, y, z), (w, h, d), "skin")
    m.box(sk.name, (0, 30.6, 0.2), (5.0, 0.6, 4.8), "gold")                        # diadem
    m.box(sk.name, (0, 31.0, -2.3), (1.2, 1.2, 0.4), "gold")                       # diadem jewel
    eyes = m.bone("eyes", sk.name, (0, 29.2, -2.6))
    m.box(eyes.name, (0, 29.2, -2.62), (3.6, 0.7, 0.05), "eye", faces={"north"})
    lid = m.bone("lid", sk.name, (0, 29.65, -2.65))
    m.cube(lid.name, (-1.9, 29.55, -2.72), (3.8, 0.1, 0.1), "mask")                # scale y ~8 closes both eyes
    sk.locators["eyes"] = (0, 29.2, -3.0)
    sk.locators["crown"] = (0, 33.0, 1.0)


def _halo(m: Model) -> None:
    """A fragmented golden halo: arcs and glyph tablets floating behind the head."""
    c = (0.0, 30.6, 4.8)
    for k in range(HALO):
        ang = k * 360 / HALO + 22
        b = m.bone(f"halo{k}", "head_g", c)
        # rearranged formations: a decree ring above the head (edict); a wide crown (court/throne)
        b.variant.update({
            "edict": ((math.cos(math.radians(ang)) * 1.5, 3.0 + math.sin(math.radians(ang)) * 1.5, -3.0), None),
            "court": ((math.cos(math.radians(ang)) * 2.5, math.sin(math.radians(ang)) * 2.5 + 1.0, 0.6), None),
            "throne": ((math.cos(math.radians(ang)) * 4.0, math.sin(math.radians(ang)) * 4.0 + 2.0, 1.0), None),
        })
        r = 5.6
        x, y = c[0] + math.cos(math.radians(ang)) * r, c[1] + math.sin(math.radians(ang)) * r
        if k % 3 == 2:      # glyph tablet
            m.box(b.name, (x, y, c[2]), (1.6, 2.2, 0.3), "glyph")
        else:               # arc fragment, tangent to the ring
            m.cube(b.name, (x - 1.6, y - 0.35, c[2] - 0.25), (3.2, 0.7, 0.5), "gold_glow", pivot=(x, y, c[2]), rot=(0, 0, ang + 90))
    m.bones["head_g"].locators["halo"] = c


# ----------------------------------------------------------------------------- the architecture on the back

def _back(m: Model) -> None:
    t = "robe"
    # folded state: a compact gate and two halos close to the back
    gate = m.bone("gate", t, (0, 20.0, 4.6))
    gate.variant.update({"court": ((0, 1.0, 2.6), None), "throne": ((0, 2.0, 4.0), None)})
    for side in (-1, 1):
        m.box(gate.name, (3.6 * side, 21.0, 5.2), (0.9, 11.0, 0.9), "lacquer_red")   # pillars
    m.box(gate.name, (0, 26.8, 5.2), (10.2, 0.9, 1.2), "lacquer")                    # kasagi (top lintel)
    m.box(gate.name, (0, 27.3, 5.2), (11.4, 0.5, 1.3), "gold")
    m.box(gate.name, (0, 25.0, 5.2), (8.0, 0.7, 0.8), "lacquer_red")                 # nuki
    m.box(gate.name, (0, 25.9, 5.2), (1.6, 1.4, 0.6), "glyph")                       # gakuzuka plaque
    for k, (r, y) in enumerate(((5.4, 22.0), (7.2, 22.0))):
        ring = m.bone(f"ring{k}", gate.name, (0, y, 5.8 + k * 0.8), (0, 0, 0))
        ring.variant.update({"court": ((0, 1.0 + k, 0.6 + k * 0.6), None), "throne": ((0, 3.0 + k * 2, 1.0 + k), None)})
        ring_cubes(m, ring.name, (0, y, 5.8 + k * 0.8), r, 0.6, "z", "gold_glow", segments=12)
    # grand court: the gate opens into a heavenly palace gateway (court and throne only)
    grand = m.bone("grand", t, (0, 20.0, 7.0), only=GRAND)
    for side in (-1, 1):
        m.box(grand.name, (7.4 * side, 22.0, 8.0), (1.4, 18.0, 1.4), "lacquer_red", only=GRAND)
        m.box(grand.name, (11.2 * side, 19.0, 8.6), (1.0, 12.0, 1.0), "lacquer_red", only=GRAND)
    m.box(grand.name, (0, 31.4, 8.0), (20.0, 1.2, 1.8), "lacquer", only=GRAND)
    m.box(grand.name, (0, 32.2, 8.0), (22.0, 0.6, 2.0), "gold", only=GRAND)
    m.box(grand.name, (0, 28.8, 8.0), (15.6, 0.9, 1.2), "lacquer_red", only=GRAND)
    ring_cubes(m, grand.name, (0, 22.0, 9.4), 11.0, 0.7, "z", "gold_glow", segments=16, only=GRAND)
    # the throne without permission (ultimate only): a tall seat-back of light and lacquer
    th = m.bone("throne", t, (0, 12.0, 6.0), only={"throne"})
    m.box(th.name, (0, 22.0, 6.8), (9.0, 22.0, 1.2), "lacquer", only={"throne"})
    m.box(th.name, (0, 22.0, 6.15), (7.4, 20.0, 0.2), "glyph_panel", only={"throne"})
    for side in (-1, 1):
        m.box(th.name, (5.2 * side, 26.0, 6.8), (1.4, 30.0, 1.4), "gold", only={"throne"})
        m.box(th.name, (5.2 * side, 41.6, 6.8), (2.2, 1.6, 2.2), "gold_glow", only={"throne"})
    ring_cubes(m, th.name, (0, 36.0, 7.6), 6.0, 0.6, "z", "gold_glow", segments=12, only={"throne"})
    ring_cubes(m, th.name, (0, 36.0, 8.4), 15.5, 0.8, "z", "gold_glow", segments=20, only={"throne"})


# ============================================================================= materials

def materials():
    return {"silk": mat_silk, "silk_red": mat_silk_red, "gold": mat_gold, "gold_glow": mat_gold_glow, "skin": mat_skin,
            "mask": mat_mask, "eye": mat_eye, "lacquer": mat_lacquer, "lacquer_red": mat_lacquer_red, "glyph": mat_glyph,
            "glyph_panel": mat_glyph_panel, "accent": mat_accent, "figure": mat_figure, "figure_red": mat_figure_red,
            "banner": mat_banner, "scroll": mat_scroll}


def _P(ctx):
    return ctx.params.get("radiant", 0.0), ctx.params.get("night", 0.0)


def mat_silk(ctx):
    rad, night = _P(ctx)
    n = nz.fbm(ctx.p * np.array([1.0, 0.4, 1.0]), 1.0, 3, seed=2)
    c = ramp([(0, "#cfc6b2"), (0.5, "#e9e2d0"), (1, "#faf6ea")], n * 0.7 + 0.25)
    # woven cloud-scroll pattern (damask) in faint gold
    u, v = ctx.s, ctx.t
    pat = np.abs(np.sin(u * 2.2 + np.sin(v * 1.4) * 1.5) * np.cos(v * 1.1)) > 0.92
    c = np.where(pat[:, None], mix3(c, hx("#d8b25a"), 0.45), c)
    edge = ctx.edge < 0.35
    c = np.where(edge[:, None], mix3(c, hx("#b98a2e"), 0.55), c)
    g = np.where(pat, 0.12 * rad + 0.1 * night, 0.0)
    return face_light(ctx, c, 0.08, 0.2), ctx.ones(), g


def mat_silk_red(ctx):
    rad, night = _P(ctx)
    n = nz.fbm(ctx.p * np.array([1.0, 0.35, 1.0]), 1.2, 3, seed=5)
    c = ramp([(0, "#5c0f0c"), (0.5, "#8f1d14"), (1, "#b8321e")], n)
    fold = np.abs(np.mod(ctx.s * 0.8 + nz.value(ctx.p, 0.5, seed=1) * 0.6, 1.0) - 0.5) < 0.08
    c = np.where(fold[:, None], c * 0.8, c)
    return face_light(ctx, c, 0.08, 0.22), ctx.ones(), ctx.zeros()


def mat_gold(ctx):
    rad, night = _P(ctx)
    n = nz.fbm(ctx.p, 1.6, 3, seed=9)
    c = ramp([(0, "#6e4a12"), (0.4, "#a6772a"), (0.8, "#d9ac4c"), (1, "#f6dc8c")], n)
    worn = nz.hash_points(ctx.p, 0.5, 4) < 0.08
    c = np.where(worn[:, None], c * 0.75, c)
    return bevel(ctx, c, 0.25, 0.3), ctx.ones(), ctx.zeros() + 0.1 * rad + 0.25 * night


def mat_gold_glow(ctx):
    rad, night = _P(ctx)
    c, a, g = mat_gold(ctx)
    c = mix3(c, hx("#fff2b8"), 0.35 + 0.3 * rad)
    return c, a, ctx.zeros() + 0.45 + 0.4 * rad + 0.3 * night


def mat_skin(ctx):
    rad, night = _P(ctx)
    n = nz.fbm(ctx.p, 0.8, 2, seed=7)
    c = ramp([(0, "#d9d2c4"), (1, "#f6f2ea")], n * 0.6 + 0.35)
    return face_light(ctx, c, 0.08, 0.18), ctx.ones(), ctx.zeros() + 0.05 * night


def mat_mask(ctx):
    rad, night = _P(ctx)
    c = np.broadcast_to(hx("#f4f0e6"), (ctx.N, 3)).copy()
    if ctx.face == "north":
        u = ctx.s / ctx.fw - 0.5
        v = ctx.t / ctx.fh
        mouth = (np.abs(v - 0.82) < 0.025) & (np.abs(u) < 0.12)
        brow = (np.abs(v - 0.2 - np.abs(u) * 0.15) < 0.02) & (np.abs(u) > 0.08) & (np.abs(u) < 0.4)
        c = np.where(mouth[:, None], hx("#7c2a22"), c)
        c = np.where(brow[:, None], hx("#a39a88"), c)
        # vermilion cheek marks of a court face
        mark = ((np.abs(u) - 0.3) ** 2 + (v - 0.55) ** 2 * 0.4) < 0.002
        c = np.where(mark[:, None], hx("#c23a24"), c)
    return face_light(ctx, c, 0.05, 0.12), ctx.ones(), ctx.zeros()


def mat_eye(ctx):
    rad, night = _P(ctx)
    c = np.broadcast_to(hx("#f4f0e6"), (ctx.N, 3)).copy()
    g = ctx.zeros()
    u = ctx.s / ctx.fw
    v = ctx.t / ctx.fh - 0.5
    for cu in (0.22, 0.78):
        du = (u - cu) / 0.17
        eye = (du ** 2 + (v / 0.45) ** 2) < 1.0
        c = np.where(eye[:, None], hx("#f2c23c"), c)
        g = np.where(eye, 0.75 + 0.25 * rad, g)
        pupil = eye & (np.abs(u - cu) < 0.025)                                # vertical slit
        c = np.where(pupil[:, None], hx("#1a0d04"), c)
        g = np.where(pupil, 0.0, g)
    return c, ctx.ones(), g


def mat_lacquer(ctx):
    n = nz.fbm(ctx.p, 1.0, 2, seed=11)
    c = ramp([(0, "#120d0c"), (1, "#2a1d18")], n)
    shine = nz.hash_points(ctx.p, 0.5, 6) < 0.05
    c = np.where(shine[:, None], hx("#5a463a"), c)
    return face_light(ctx, c, 0.12, 0.2), ctx.ones(), ctx.zeros()


def mat_lacquer_red(ctx):
    n = nz.fbm(ctx.p, 1.0, 2, seed=13)
    c = ramp([(0, "#6a0f08"), (1, "#c22c16")], n)
    return face_light(ctx, c, 0.12, 0.2), ctx.ones(), ctx.zeros()


def _glyphs(u, v, density=3.0):
    """Abstract ideogram-like strokes (not real characters)."""
    cu, cv = np.floor(u * density), np.floor(v * density * 1.6)
    fu, fv = np.mod(u * density, 1.0), np.mod(v * density * 1.6, 1.0)
    h = np.mod(np.sin(cu * 12.9 + cv * 78.2) * 43758.5, 1.0)
    stroke = ((np.abs(fv - 0.25) < 0.08) & (h > 0.3)) | ((np.abs(fu - 0.5) < 0.07) & (h > 0.5)) | \
             ((np.abs(fv - 0.7) < 0.08) & (fu > 0.2) & (fu < 0.8)) | ((np.abs(fu - fv) < 0.07) & (h > 0.75))
    return stroke & (fu > 0.12) & (fu < 0.88) & (fv > 0.1) & (fv < 0.9)


def mat_glyph(ctx):
    rad, night = _P(ctx)
    c = np.broadcast_to(hx("#2b1a10"), (ctx.N, 3)).copy()
    st = _glyphs(ctx.s / max(ctx.fw, 1e-6), ctx.t / max(ctx.fh, 1e-6), 2.0)
    c = np.where(st[:, None], hx("#ffe08a"), c)
    return c, ctx.ones(), np.where(st, 0.7 + 0.3 * rad, 0.0)


def mat_glyph_panel(ctx):
    rad, night = _P(ctx)
    c = mix3(hx("#3a1410"), hx("#5a1c14"), nz.fbm(ctx.p, 0.6, 2))
    st = _glyphs(ctx.s / max(ctx.fw, 1e-6), ctx.t / max(ctx.fh, 1e-6), 5.0)
    c = np.where(st[:, None], hx("#ffe8a8"), c)
    return c, ctx.ones(), np.where(st, 0.8, 0.0)


def mat_figure(ctx):
    """Celestial attendants: luminous ivory-gold beings (they glow softly, but keep their form)."""
    n = nz.fbm(ctx.p, 0.8, 2, seed=3)
    c = ramp([(0, "#d9c79a"), (0.6, "#efe2be"), (1, "#fff6dc")], n)
    edge = ctx.edge < 0.5
    c = np.where(edge[:, None], mix3(c, hx("#c39a48"), 0.5), c)
    return face_light(ctx, c, 0.12, 0.25), ctx.ones(), ctx.zeros() + 0.3


def mat_figure_red(ctx):
    n = nz.fbm(ctx.p, 0.8, 2, seed=4)
    c = ramp([(0, "#b8402c"), (1, "#e86a48")], n)
    return face_light(ctx, c, 0.1, 0.2), ctx.ones(), ctx.zeros() + 0.3


def mat_banner(ctx):
    c = mix3(hx("#f4e7c2"), hx("#fffaf0"), ctx.t / max(ctx.fh, 1e-6))
    st = _glyphs(ctx.s / max(ctx.fw, 1e-6), ctx.t / max(ctx.fh, 1e-6), 2.5)
    c = np.where(st[:, None], hx("#b02a1c"), c)
    return c, ctx.ones(), ctx.zeros() + 0.4


def mat_scroll(ctx):
    """A decree: columns of brushed characters and a vermilion seal."""
    c = mix3(hx("#efe2bc"), hx("#fbf3dc"), nz.fbm(ctx.p, 1.2, 2))
    u = ctx.s / max(ctx.fw, 1e-6)
    v = ctx.t / max(ctx.fh, 1e-6)
    col = np.floor(ctx.s).astype(int)
    text = (col % 2 == 0) & (v > 0.14) & (v < 0.86) & (u > 0.1) & (u < 0.78) & (nz.hash_points(ctx.p, 1.0, 7) < 0.62)
    c = np.where(text[:, None], hx("#4a2a18"), c)
    seal = (u > 0.83) & (u < 0.95) & (v > 0.58) & (v < 0.86)
    c = np.where(seal[:, None], hx("#c23a24"), c)
    return c, ctx.ones(), ctx.zeros() + 0.35


# ============================================================================= helper entities

def build_gate() -> Model:
    """The Uninvited Temple's gate (and, scaled up, the sky gate of the ultimate)."""
    m = Model("celestial_gate", ppu=1.0, atlas_width=128)
    m.bone("root", None, (0, 0, 0))
    g = m.bone("gate", "root", (0, 0, 0))
    for side in (-1, 1):
        m.box(g.name, (14 * side, 22, 0), (3.0, 44, 3.0), "lacquer_red")
        m.box(g.name, (14 * side, 1.0, 0), (4.2, 2.0, 4.2), "lacquer")
    m.box(g.name, (0, 45.5, 0), (40, 3.0, 4.0), "lacquer")
    m.box(g.name, (0, 47.6, 0), (44, 1.4, 4.4), "gold")
    m.box(g.name, (0, 39.0, 0), (32, 2.4, 2.4), "lacquer_red")
    m.box(g.name, (0, 42.2, 0), (5.0, 4.4, 1.2), "glyph")
    ring = m.bone("ring", g.name, (0, 24, 1.8))
    ring_cubes(m, ring.name, (0, 24, 1.8), 12.0, 1.2, "z", "gold_glow", segments=16)
    inner = m.bone("ring_inner", g.name, (0, 24, 2.4))
    ring_cubes(m, inner.name, (0, 24, 2.4), 7.0, 1.0, "z", "gold_glow", segments=12)
    m.bones["gate"].locators["center"] = (0, 24, 0)
    m.pack()
    return m


def _figure(m: Model, parent: str, name: str, x: float, z: float, rank: str) -> None:
    """One celestial attendant (2.2 x 7 units) with the attribute of its rank."""
    b = m.bone(name, parent, (x, 0, z))
    m.box(b.name, (x, 1.7, z), (3.0, 3.4, 2.4), "figure")                         # flared hem of the robe
    m.box(b.name, (x, 5.0, z), (2.1, 3.4, 1.7), "figure")                         # upper robe
    m.box(b.name, (x, 3.6, z), (2.6, 0.5, 2.0), "figure_red")                     # sash
    m.box(b.name, (x, 6.75, z), (2.3, 0.45, 1.9), "gold")                        # collar
    for sd in (-1, 1):                                                            # long hanging sleeves
        m.box(b.name, (x + 1.5 * sd, 4.6, z - 0.1), (0.9, 3.0, 1.3), "figure")
    m.box(b.name, (x, 7.75, z), (1.5, 1.6, 1.5), "mask")                          # ivory mask face
    m.box(b.name, (x, 8.75, z + 0.1), (1.2, 0.5, 1.2), "lacquer")                 # cap
    if rank == "standard":           # tall pole with a nobori banner
        m.box(b.name, (x + 1.4, 8.0, z), (0.3, 16.0, 0.3), "figure_red")
        fl = m.bone(f"{name}_banner", b.name, (x + 1.55, 15.6, z))
        m.box(fl.name, (x + 2.6, 12.6, z), (2.2, 6.0, 0.15), "banner")
    elif rank == "guard":            # spear and a crested helmet
        m.box(b.name, (x - 1.4, 7.0, z), (0.3, 13.0, 0.3), "figure_red")
        m.box(b.name, (x - 1.4, 13.8, z), (0.6, 1.4, 0.6), "gold_glow")
        m.box(b.name, (x, 8.3, z), (1.8, 0.6, 1.8), "gold")
    elif rank == "herald":           # a long horn raised
        m.cube(b.name, (x - 0.3, 6.8, z - 3.4), (0.6, 0.6, 3.4), "gold", pivot=(x, 7.1, z), rot=(-25, 0, 0))
    elif rank == "judge":            # a tall court hat and a scroll
        m.box(b.name, (x, 8.9, z + 0.3), (1.1, 2.2, 1.1), "lacquer")
        m.box(b.name, (x + 1.2, 4.6, z - 0.4), (0.6, 2.4, 0.6), "scroll")
    elif rank == "parasol":          # a great parasol (kasa) on a pole
        m.box(b.name, (x, 9.0, z), (0.3, 6.0, 0.3), "lacquer")
        m.box(b.name, (x, 12.2, z), (5.4, 0.5, 5.4), "figure_red")
        m.box(b.name, (x, 12.6, z), (3.6, 0.4, 3.6), "gold_glow")
    elif rank == "bearer":           # palanquin bearers carry the pole on the shoulder
        m.box(b.name, (x, 8.4, z), (1.2, 0.5, 1.2), "figure_red")


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
            _figure(m, col.name, f"fig_{row}_{'r' if side < 0 else 'l'}", 3.2 * side, z, rank)
    # the palanquin carried by the bearers (row 4)
    pal = m.bone("palanquin", col.name, (0, 9.0, 7.5))
    m.box(pal.name, (0, 8.9, 7.5), (0.5, 0.5, 13.0), "lacquer")                    # poles
    m.box(pal.name, (0, 11.0, 7.5), (4.4, 3.8, 4.4), "lacquer_red")
    m.box(pal.name, (0, 13.3, 7.5), (5.6, 0.8, 5.6), "gold")
    m.box(pal.name, (0, 14.3, 7.5), (1.2, 1.4, 1.2), "gold_glow")
    m.pack()
    return m


def build_heralds() -> Model:
    """Two heralds of the proclamation carrying an immense decree between them."""
    m = Model("herald", ppu=1.0, atlas_width=128)
    m.bone("root", None, (0, 0, 0))
    g = m.bone("pair", "root", (0, 0, 0))
    for side in (-1, 1):
        _figure(m, g.name, f"herald_{'r' if side < 0 else 'l'}", 8.0 * side, 0.0, "herald")
    sc = m.bone("decree", g.name, (0, 8.0, -0.8))
    m.box(sc.name, (0, 6.0, -0.8), (13.0, 5.0, 0.2), "scroll")
    for side in (-1, 1):
        m.box(sc.name, (6.8 * side, 6.0, -0.8), (0.8, 5.8, 0.8), "lacquer_red")
    m.pack()
    return m
