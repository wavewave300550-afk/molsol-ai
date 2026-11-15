"""Race 002 - Runic Titan Golem.

Living architecture: separate basalt fragments held in formation by runes.
Every large stone is its own bone so the body can reconfigure:
  base | siege (hammer) | bastion (shield wall) | arcane (rune formation)
  | scattered (reassembly) | disrupted (runes failing)
"""
from __future__ import annotations

import math

import numpy as np

from kit.geo import Model
from kit.tex import Ctx, hx
from kit import noise as nz
from models.common import humanoid, fp_sleeves, ramp, bevel, face_light, mix3, desat, clamp01, ring_cubes, accents, mat_accent

ID = "golem"
VARIANTS = ["base", "siege", "bastion", "arcane", "scattered", "disrupted"]
TEXTURES = {
    "base": {"glow": 1.0, "hue": 0.0},
    "charged": {"glow": 1.35, "hue": 0.0},
    "disrupted": {"glow": 0.55, "hue": 1.0},
}
VARIANT_TEXTURE = {"base": "base", "siege": "charged", "bastion": "charged", "arcane": "charged",
                   "scattered": "charged", "disrupted": "disrupted"}

# bones that take part in the reassembly scatter animation
MOVABLE: list = []


def _stone(m: Model, name: str, parent: str, center, size, mat="basalt", rot=(0, 0, 0), variant=None, **kw):
    b = m.bone(name, parent, center, rot, **kw)
    if variant:
        b.variant.update(variant)
    m.box(name, center, size, mat)
    MOVABLE.append(name)
    return b


def build() -> Model:
    MOVABLE.clear()
    m = Model(ID, ppu=2.0, atlas_width=512)
    humanoid(m)
    # the stone trunk leans / rolls about the hips, not the neck (torso_g holds no cubes itself)
    m.bones["torso_g"].pivot = (0.0, 13.0, 0.0)
    _legs(m)
    _torso(m)
    _core(m)
    _head(m)
    _arms(m)
    _arcane(m)
    fp_sleeves(m, "basalt", width=5.2)
    accents(m, [
        ("c", "arch", "arch", (0, 33.0, -0.6), (12.8, 0.8, 8.4)),
        ("c", "pr", "pillar_r", (-8.0, 27.4, -0.2), (7.2, 0.8, 9.6)),
        ("c", "pl", "pillar_l", (7.4, 27.0, 0.0), (6.0, 0.8, 9.0)),
        ("c", "rarm", "r_fore", (-9.2, 15.2, 0.0), (7.2, 0.8, 7.0)),
        ("c", "larm", "l_fore", (8.5, 15.4, 0.0), (6.2, 0.8, 6.2)),
        ("l", "r", "r_thigh", (-4.5, 9.4, 0.3), (6.0, 0.8, 6.2)),
        ("l", "l", "l_thigh", (4.5, 9.4, 0.3), (6.0, 0.8, 6.2)),
        ("f", "r", "r_shin", (-4.5, 4.6, 0.2), (5.6, 0.8, 5.8)),
        ("f", "l", "l_shin", (4.5, 4.6, 0.2), (5.6, 0.8, 5.8)),
    ])
    m.pack()
    return m


# ----------------------------------------------------------------------------- legs

def _legs(m: Model) -> None:
    for side, g, p in ((-1, "r_leg_g", "r"), (1, "l_leg_g", "l")):
        x = 4.5 * side
        _stone(m, f"{p}_hip", g, (x, 13.8, 0.4), (6.2, 4.2, 6.4))
        m.box(g, (x, 11.3, 0.4), (4.8, 0.6, 5.0), "seam")
        _stone(m, f"{p}_thigh", g, (x, 8.9, 0.3), (5.6, 4.0, 5.8))
        _stone(m, f"{p}_knee", g, (x, 7.4, -3.0), (3.8, 2.8, 1.4), mat="basalt_carved")
        m.box(g, (x, 6.4, 0.2), (4.4, 0.6, 4.6), "seam")
        _stone(m, f"{p}_shin", g, (x, 3.7, 0.2), (5.2, 4.2, 5.4), mat="basalt_carved")
        _stone(m, f"{p}_foot", g, (x, 0.7, -0.7), (7.0, 1.4, 8.6))
        for k, dx in enumerate((-2.0, 0.0, 2.0)):
            m.box(f"{p}_foot", (x + dx, 1.0, -5.6), (1.8, 2.0, 1.8), "basalt")
        m.bones[f"{p}_foot"].locators[f"{p}_step"] = (x, 0.2, -1.5)
        fr = m.bone(f"{p}_foot_rune", g, (x, 0.0, -0.7))
        m.box(fr.name, (x, -0.25, -0.7), (6.4, 0.3, 7.8), "seam")


# ----------------------------------------------------------------------------- torso

def _torso(m: Model) -> None:
    t = "torso_g"
    _stone(m, "pelvis", t, (0, 14.8, 1.0), (10.0, 3.0, 7.0))
    _stone(m, "midriff", t, (0, 18.6, 1.6), (8.6, 4.8, 6.4), mat="basalt_carved")
    m.box("midriff", (0, 16.6, 1.6), (7.0, 0.5, 5.2), "seam")
    # chest pillars framing the rune core cavity (asymmetric: right side heavier)
    _stone(m, "pillar_r", t, (-8.0, 27.2, -0.2), (6.8, 10.6, 9.2), mat="basalt_carved")
    _stone(m, "pillar_l", t, (7.4, 26.8, 0.0), (5.6, 9.6, 8.6), mat="basalt_carved")
    _stone(m, "arch", t, (0, 33.0, -0.6), (12.4, 3.0, 8.0))
    _stone(m, "lintel", t, (0, 21.6, -0.4), (9.4, 2.2, 7.4))
    _stone(m, "backwall", t, (0, 27.0, 3.4), (9.2, 9.6, 2.4), mat="runewall")
    _stone(m, "backmass", t, (0, 29.6, 6.4), (15.0, 8.4, 3.6))
    # shoulder boulders (the right one is a monumental block)
    _stone(m, "r_shoulder", t, (-14.4, 33.6, 0.6), (8.8, 8.2, 9.4),
           variant={"bastion": ((4.6, -4.8, -9.2), (0, 0, -6)), "arcane": ((-2.0, 3.0, 0.0), (0, 0, -18))})
    _stone(m, "l_shoulder", t, (12.4, 33.0, 0.6), (7.2, 6.8, 7.8),
           variant={"bastion": ((-3.6, -5.6, -9.0), (0, 0, 6)), "arcane": ((2.0, 3.2, 0.0), (0, 0, 16))})
    m.box("r_shoulder", (-14.4, 28.8, 0.6), (5.6, 0.5, 6.0), "seam")
    m.box("l_shoulder", (12.4, 29.2, 0.6), (4.6, 0.5, 5.0), "seam")
    # floating back slabs: swing to the front as a bastion, rise as arcane tablets
    _stone(m, "slab_a", t, (-3.6, 30.6, 9.2), (7.0, 9.4, 1.6), mat="tablet", rot=(-10, 0, -6),
           variant={"bastion": ((-0.2, -6.4, -19.6), (0, 0, -3)), "arcane": ((-12.0, 4.0, -6.0), (0, 70, 0))})
    _stone(m, "slab_b", t, (4.2, 28.6, 9.0), (6.0, 8.0, 1.4), mat="tablet", rot=(-8, 0, 8),
           variant={"bastion": ((0.2, -5.0, -19.2), (0, 0, 4)), "arcane": ((12.0, 5.0, -6.0), (0, -70, 0))})
    # satellites: pebbles hovering around the shoulders
    for k, (c, s) in enumerate((((-17.6, 39.4, -1.0), 2.0), ((-11.2, 39.8, 3.0), 1.6),
                                 ((15.6, 37.8, 1.0), 1.8), ((9.0, 38.6, -2.4), 1.4))):
        arc = (0.0 + 8.0 * math.cos(k * 1.57), 13.0 - 2 * (k % 2), 8.0 * math.sin(k * 1.57))
        _stone(m, f"sat{k}", t, c, (s, s, s), mat="basalt_carved",
               variant={"arcane": ((arc[0] - c[0], 33 + arc[1] - c[1], arc[2] - c[2]), (45, 45, 0))})
    m.bones["torso_g"].locators["core"] = (0, 26.6, -1.6)
    m.bones["torso_g"].locators["back"] = (0, 30, 8)


def _core(m: Model) -> None:
    c = (0.0, 26.6, -1.4)
    m.bone("core", "torso_g", c)
    m.bone("ring_a", "core", c)
    ring_cubes(m, "ring_a", c, 4.0, 0.7, "z", "ring", segments=10)
    m.bone("ring_b", "core", c, (0, 0, 20))
    ring_cubes(m, "ring_b", c, 3.1, 0.6, "y", "ring", segments=8)
    m.bone("ring_c", "core", c, (20, 0, 0))
    ring_cubes(m, "ring_c", c, 2.2, 0.5, "x", "ring", segments=8)
    m.bone("crystal", "core", c)
    m.cube("crystal", (c[0] - 0.9, c[1] - 1.5, c[2] - 0.9), (1.8, 3.0, 1.8), "crystal", pivot=c, rot=(0, 45, 0))
    m.cube("crystal", (c[0] - 0.6, c[1] - 2.1, c[2] - 0.6), (1.2, 4.2, 1.2), "crystal", pivot=c, rot=(0, 45, 0))


def _head(m: Model) -> None:
    """Sculpted monolith head; follows the player's look direction via animation."""
    h = m.bone("crown", "torso_g", (0, 35.2, 0.4))
    MOVABLE.append("crown")
    m.box("crown", (0, 38.4, -0.2), (8.2, 6.4, 7.6), "face", faces={"north"})
    m.box("crown", (0, 38.4, -0.2), (8.2, 6.4, 7.6), "basalt_carved", faces={"south", "east", "west", "up", "down"})
    m.box("crown", (0, 40.2, -4.3), (9.0, 1.6, 1.6), "basalt")         # brow ridge
    m.box("crown", (0, 35.6, -3.0), (6.4, 1.8, 3.4), "basalt")         # chin slab
    for side in (-1, 1):
        m.box("crown", (4.6 * side, 38.0, 0.4), (1.2, 4.6, 5.4), "basalt_carved")   # cheek plates
    m.box("crown", (0, 42.2, 0.6), (4.2, 1.4, 5.2), "basalt")          # crest stones
    m.box("crown", (0, 43.3, 1.2), (2.2, 0.9, 3.2), "seam")
    h.locators["eyes"] = (0, 38.6, -4.4)
    # stone eye shutters hidden under the brow ridge; scale y ~7.8 slides them over the glowing slits
    for side, p in ((-1, "r"), (1, "l")):
        lid = m.bone(f"{p}_eyelid", "crown", (1.9 * side, 39.75, -4.2))
        m.cube(lid.name, (1.9 * side - 1.4, 39.45, -4.45), (2.8, 0.3, 0.4), "basalt")


# ----------------------------------------------------------------------------- arms

def _arms(m: Model) -> None:
    specs = (
        (-1, "r", (-9.8, 19.6, 0.2), (5.4, 5.0, 5.6), (-9.2, 13.0, 0.0), (6.8, 6.2, 6.6), (-9.0, 8.1, -0.4), (7.2, 3.4, 7.0)),
        (1, "l", (8.9, 19.8, 0.2), (4.6, 4.4, 5.0), (8.5, 13.4, 0.0), (5.8, 5.6, 5.8), (8.4, 8.9, -0.3), (6.2, 3.0, 6.0)),
    )
    for side, p, uc, us, fc, fs, kc, ks in specs:
        g = f"{p}_arm_g"
        _stone(m, f"{p}_upper", g, uc, us, mat="basalt_carved")
        m.box(g, (uc[0], uc[1] - us[1] / 2 - 0.4, uc[2]), (us[0] - 1.2, 0.5, us[2] - 1.2), "seam")
        skip = {"siege"} if side > 0 else None
        fb = _stone(m, f"{p}_fore", g, fc, fs)
        if skip:
            fb.only = {"base", "bastion", "arcane", "scattered", "disrupted"}
        kb = _stone(m, f"{p}_fist", g, kc, ks)
        if skip:
            kb.only = {"base", "bastion", "arcane", "scattered", "disrupted"}
        for k in range(3):
            m.box(f"{p}_fist", (kc[0] + (k - 1) * 2.2, kc[1] + 0.2, kc[2] - ks[2] / 2 - 0.5), (1.8, 2.0, 1.2), "basalt_carved")
        # orbiting pebbles around the forearm
        ob = m.bone(f"{p}_orbit", g, fc)
        for k, (dx, dy, dz, s) in enumerate(((4.6, 1.0, 0.0, 1.4), (-1.0, -1.6, 4.4, 1.2), (0.6, 2.4, -4.2, 1.0))):
            m.box(ob.name, (fc[0] + dx * -side, fc[1] + dy, fc[2] + dz), (s, s, s), "basalt_carved")
    # siege hammer (formed from the right arm's fragments plus the left forearm)
    hb = m.bone("hammer", "r_arm_g", (-9.0, 6.4, -0.4), only={"siege"})
    m.box(hb.name, (-9.0, 3.6, -0.4), (3.0, 5.4, 3.0), "seam")
    m.box(hb.name, (-9.0, -2.4, -0.4), (13.0, 7.0, 7.4), "basalt_carved")
    m.box(hb.name, (-9.0, -2.4, -0.4), (13.6, 1.0, 8.0), "ring")
    for dx in (-6.9, 6.9):
        m.box(hb.name, (-9.0 + dx, -2.4, -0.4), (1.2, 7.6, 7.8), "basalt")
    hb.locators["head"] = (-9.0, -2.4, -0.4)


def _arcane(m: Model) -> None:
    """Glyph stones that only exist in the arcane configuration (orbiting rune ring)."""
    ab = m.bone("arcane_ring", "torso_g", (0, 20, 0), only={"arcane"})
    for k in range(8):
        a = k * math.pi / 4
        c = (14.0 * math.cos(a), 20 + (2.0 if k % 2 else -1.0), 14.0 * math.sin(a))
        m.cube(ab.name, (c[0] - 1.4, c[1] - 2.0, c[2] - 0.5), (2.8, 4.0, 1.0), "tablet",
               pivot=c, rot=(0, -math.degrees(a) + 90, 0))


# ============================================================================= materials

def materials():
    return {"basalt": mat_basalt, "basalt_carved": mat_carved, "runewall": mat_runewall, "tablet": mat_tablet,
            "seam": mat_seam, "ring": mat_ring, "crystal": mat_crystal, "face": mat_face, "accent": mat_accent}


def _glowcol(ctx):
    hue = ctx.params.get("hue", 0.0)
    return mix3(hx("#ffc23d"), hx("#ff4a26"), hue), mix3(hx("#fff3c4"), hx("#ffb08a"), hue)


def _stone_base(ctx: Ctx):
    p = ctx.p
    # columnar jointing (hexagonal-ish cells stretched vertically) + weathering
    f1, f2, cid = nz.worley(p * np.array([1.0, 0.35, 1.0]), 0.5, seed=7)
    n = nz.fbm(p, 0.6, 4, seed=3)
    base = ramp([(0, "#16161a"), (0.45, "#28282e"), (0.75, "#3a3a42"), (1, "#4e4d55")], n * 0.8 + cid * 0.25)
    joint = (f2 - f1) < 0.06
    base = np.where(joint[:, None], base * 0.55, base)
    pits = nz.hash_points(p, 0.5, 4) < 0.03
    base = np.where(pits[:, None], base * 0.6, base)
    # weathered upper edges, faint moss in the crevices
    top = (ctx.face == "up") * 1.0
    base = base * (1 + 0.18 * top)
    moss = (nz.fbm(p, 0.9, 2, seed=9) > 0.72) & (ctx.face in ("up", "north", "west", "east"))
    base = np.where(moss[:, None], mix3(base, hx("#3c4a2c"), 0.45), base)
    # aged gold fractures (kintsugi) along selected joints
    gold_line = joint & (cid < 0.07) & (nz.fbm(p, 0.7, 2, seed=12) > 0.45)
    g1, g2 = _glowcol(ctx)
    base = np.where(gold_line[:, None], mix3(hx("#c99a2e"), g1, 0.4), base)
    glow = np.where(gold_line, 0.32 * ctx.params.get("glow", 1.0), 0.0)
    return bevel(ctx, face_light(ctx, base, 0.12, 0.3), 0.25, 0.9), glow


def mat_basalt(ctx):
    c, g = _stone_base(ctx)
    return c, ctx.ones(), g


def _glyph_mask(ctx, cell=(2.4, 3.2), density=0.55, seed=0):
    """Procedural rune glyphs: each cell holds 2-3 strokes (vertical stem + branches)."""
    s, t = ctx.s, ctx.t
    cx = np.floor(s / cell[0])
    cy = np.floor(t / cell[1])
    u = (s - cx * cell[0]) / cell[0]
    v = (t - cy * cell[1]) / cell[1]
    key = np.stack([cx, cy, np.full_like(cx, seed + ctx.seed)], axis=1)
    r1 = nz.hash_points(key, 1.0, 1)
    r2 = nz.hash_points(key, 1.0, 2)
    r3 = nz.hash_points(key, 1.0, 3)
    on = r1 < density
    stem = (np.abs(u - 0.5) < 0.09) & (v > 0.12) & (v < 0.88)
    k1 = np.where(r2 < 0.5, 1, -1)
    diag = (np.abs((u - 0.5) - k1 * (v - 0.25) * 0.8) < 0.08) & (v > 0.18) & (v < 0.55)
    bar = (np.abs(v - (0.35 + 0.3 * r3)) < 0.07) & (np.abs(u - 0.5) < 0.32)
    hook = (np.abs((u - 0.5) + k1 * (v - 0.65) * 0.9) < 0.08) & (v > 0.6) & (v < 0.85)
    shape = stem | np.where(r3 < 0.5, diag, bar) | (hook & (r2 > 0.3))
    margin = (ctx.edge > 0.7)
    return on & shape & margin


def mat_carved(ctx):
    c, g = _stone_base(ctx)
    if ctx.face in ("north", "east", "west", "south"):
        mask = _glyph_mask(ctx, density=0.16)
        g1, g2 = _glowcol(ctx)
        c = np.where(mask[:, None], mix3(g1, g2, 0.35), c)
        g = np.where(mask, 0.85 * ctx.params.get("glow", 1.0), g)
    return c, ctx.ones(), np.clip(g, 0, 1)


def mat_runewall(ctx):
    c, g = _stone_base(ctx)
    c = c * 0.7
    if ctx.face == "north":
        mask = _glyph_mask(ctx, cell=(1.8, 2.4), density=0.75, seed=5)
        g1, g2 = _glowcol(ctx)
        c = np.where(mask[:, None], mix3(g1, g2, 0.5), c)
        g = np.where(mask, 0.95 * ctx.params.get("glow", 1.0), g)
    return c, ctx.ones(), np.clip(g, 0, 1)


def mat_tablet(ctx):
    c, g = _stone_base(ctx)
    if ctx.face in ("north", "south", "east", "west"):
        u = ctx.s / ctx.fw - 0.5
        v = ctx.t / ctx.fh - 0.5
        ring = np.abs(np.sqrt(u * u * 1.0 + v * v * 0.6) - 0.33) < 0.035
        mask = _glyph_mask(ctx, cell=(1.6, 2.2), density=0.6, seed=11) & (np.sqrt(u * u + v * v * 0.6) < 0.3)
        g1, g2 = _glowcol(ctx)
        sel = ring | mask
        c = np.where(sel[:, None], mix3(g1, g2, 0.4), c)
        g = np.where(sel, 0.9 * ctx.params.get("glow", 1.0), g)
    return c, ctx.ones(), np.clip(g, 0, 1)


def mat_seam(ctx):
    g1, g2 = _glowcol(ctx)
    n = nz.fbm(ctx.p, 1.4, 2, seed=2)
    c = mix3(g1, g2, n)
    return c, ctx.ones(), np.clip(0.75 + 0.25 * n, 0, 1) * min(1.0, ctx.params.get("glow", 1.0))


def mat_ring(ctx):
    n = nz.fbm(ctx.p, 1.2, 3, seed=8)
    c = ramp([(0, "#5a3e12"), (0.5, "#a77a28"), (0.8, "#d8ad4a"), (1, "#f1d58a")], n)
    pat = nz.hash_points(ctx.p, 0.5, 6) < 0.15
    c = np.where(pat[:, None], mix3(c, hx("#3f6b52"), 0.5), c)       # verdigris
    g1, g2 = _glowcol(ctx)
    inlay = (np.mod(ctx.s * 1.5, 1.0) < 0.3) & (ctx.face in ("north", "south", "up"))
    c = np.where(inlay[:, None], g2, c)
    return bevel(ctx, c, 0.2, 0.3), ctx.ones(), np.where(inlay, 0.8 * ctx.params.get("glow", 1.0), 0.0)


def mat_crystal(ctx):
    u = ctx.s / ctx.fw - 0.5
    facet = np.abs(u) + np.abs(ctx.t / ctx.fh - 0.5) * 0.5
    hue = ctx.params.get("hue", 0.0)
    c = ramp([(0, "#fffbe8"), (0.3, "#ffe08a"), (0.7, "#ffb02e"), (1, "#c96a10")], facet * 1.4)
    c = mix3(c, mix3(c, hx("#ff3b2a"), 0.8), hue)
    return c, ctx.ones(), ctx.zeros() + 0.95 * min(1.0, 0.5 + 0.5 * ctx.params.get("glow", 1.0))


def mat_face(ctx):
    c, g = _stone_base(ctx)
    c = c * 0.9
    u = ctx.s / ctx.fw
    v = ctx.t / ctx.fh
    g1, g2 = _glowcol(ctx)
    eyes = np.zeros(ctx.N, dtype=bool)
    for cxu in (0.27, 0.73):
        du = np.abs(u - cxu)
        slit = (du < 0.15) & (np.abs(v - 0.42) < 0.055)               # horizontal slit
        stem = (du < 0.035) & (v > 0.30) & (v < 0.62)                # rune stem crossing it
        tick = (np.abs((u - cxu) - (v - 0.36) * 0.6 * (1 if cxu < 0.5 else -1)) < 0.03) & (v > 0.28) & (v < 0.42)
        eyes |= slit | stem | tick
    mouth = (np.abs(v - 0.78) < 0.025) & (np.abs(u - 0.5) < 0.22)
    sel = eyes | mouth
    c = np.where(eyes[:, None], mix3(g2, hx("#ffffff"), 0.3), c)
    c = np.where(mouth[:, None], g1 * 0.8, c)
    g = np.where(eyes, 1.0, np.where(mouth, 0.5, g))
    return c, ctx.ones(), np.clip(g * min(1.2, ctx.params.get("glow", 1.0)), 0, 1)
