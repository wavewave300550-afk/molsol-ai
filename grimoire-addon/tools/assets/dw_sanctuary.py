"""DW04 Divine Edict: Let There Be Sanctuary -- a celestial cathedral written into existence.

Modular piece actors (all share one life cycle, see PIECE_STATES):
  dw_sanct_pillar  (2 kinds)  marble pillar, octagonal shaft, gilt capital, orbiting letter-finial
  dw_sanct_wall               engraved wall panel with two stained-glass lancets and a rose medallion
  dw_sanct_gate               monumental open archway: voussoir arch, gable, tympanum, golden gate leaves
  dw_sanct_bridge             flying gallery / arcade bridge that floats over each wall panel
  dw_sanct_rib                vault rib: 8 segments that are written one after another up to the crown
  dw_sanct_crown              keystone crown: open ring, lantern, spire and an orbit of letters
  dw_sanct_script             a ruled line of sacred writing that circles the caster and is peeled away

Every piece exists first as one giant extruded FIRST_WORD glyph (letter), the glyph stretches and is
redrawn into stone by a travelling quill of light (form), stands with drifting inscriptions (stand),
shatters back into tumbling letters (break), or thins into a line of writing that streams away
(unwrite).  Model units: pieces are modelled at half size and rendered at scale 2 (1 block = 8 units).
"""
import math

import numpy as np

from kit import glyphs, synth as sy, tex
from kit.anim import LIFE, Anim, M
from kit.geo import Cube, Mat, Model, ring

from .a_fx_common import particles

IVORY, GOLD, WGOLD, SILVER, BLUE = "#f5f0e1", "#c9a24a", "#fff3c4", "#d8dde3", "#2b3f8f"
FW = glyphs.FIRST_WORD
SCALE = 2.0

# ---- timing shared with src/spells/dw04_sanctuary.ts (seconds)
LETTER_T = 0.7     # letter grows while it flies (14 ticks)
FORM_T = 1.0       # letter -> architecture (20 ticks)
BREAK_T = 1.3      # shatter into letters (26 ticks)
UNWRITE_T = 1.5    # thin into writing and stream away (30 ticks)
FLARE_T = 0.5      # inscription flash (10 ticks)
WRITE_T = 1.2      # script line is written (24 ticks)
PEEL_T = 3.5       # script line letters peel away (70 ticks)
FADE_T = 0.7

PIECE_STATES = {0: ["hidden"], 1: ["letter"], 2: ["form"], 3: ["stand"], 4: ["break"], 5: ["unwrite"],
                6: ["stand", "flare"]}
SCRIPT_STATES = {0: ["hidden"], 1: ["write"], 2: ["hold"], 3: ["peel"], 4: ["fade"]}


def _spin(rate):
    return M(f"q.life_time*{rate}", lambda t: t * rate)


def _vis(expr):
    return f"q.property('grimoire:state') {expr}"


VISIBILITY = [{"letter*": "q.property('grimoire:state') == 1 || q.property('grimoire:state') == 2"},
              {"shard*": _vis("== 4")}, {"quill*": _vis("== 2")}, {"ribbon*": _vis("== 5")}, {"flare*": _vis("== 6")}]


# ================================================================ materials
def over(base, top, key):
    """Composite `top` (where opaque) over `base`."""
    def fn(ctx):
        b = np.array(base.fn(ctx), dtype=float)
        t = np.array(top.fn(ctx), dtype=float)
        m = (t[..., 3:4] > 0.5)
        out = np.where(m, t, b)
        out[..., 3] = np.maximum(b[..., 3], t[..., 3])
        return out
    return Mat(fn, f"over|{base.key}|{top.key}|{key}", spatial=base.spatial or top.spatial,
               directional=base.directional or top.directional)


def lancet(key="lancet"):
    """Stained-glass lancet: pointed arch, diamond leading, blue/gold/ivory panes, gilt frame."""
    pal = [tex.rgb(c) for c in (BLUE, "#3d5bb8", "#5f7fd6", WGOLD, "#e8c66a", "#f5f0e1", "#8fa8e8", BLUE)]

    def fn(ctx):
        u = ctx.U * 2 - 1
        v = ctx.V
        top = 0.32
        w = np.where(v < top, 0.92 * np.clip(np.sin(np.pi / 2 * np.clip(v / top, 0, 1)), 0, 1) ** 0.6, 0.92)
        inside = (np.abs(u) <= w) & (v < 0.985)
        ix, iy = tex.px(ctx)
        t = np.zeros((ctx.h, ctx.w, 5))
        a = (ix + iy) // 3
        b = (ix - iy + 300) // 3
        cell = tex._hash(a, b, 41 + ctx.variant)
        col = np.zeros((ctx.h, ctx.w, 3))
        for i, c in enumerate(pal):
            col = np.where(((cell * len(pal)).astype(int) == i)[..., None], c, col)
        t[..., :3] = col
        t[..., 4] = 0.75 + 0.25 * tex._hash(a, b, 7)
        lead = (((ix + iy) % 3) == 0) | (((ix - iy) % 3) == 0)
        t[..., :3] = np.where(lead[..., None], tex.rgb("#5a4418"), t[..., :3])
        t[..., 4] = np.where(lead, 0.08, t[..., 4])
        # central mullion + trefoil ring in the arch head
        mull = np.abs(u) < 1.6 / ctx.w
        r = np.hypot(u * 1.0, (v - top * 0.62) * (ctx.h / ctx.w) * 2)
        tre = np.abs(r - 0.42) < 2.0 / ctx.w
        gold = (mull & (v > top * 0.95)) | tre
        t[..., :3] = np.where(gold[..., None], tex.rgb(GOLD), t[..., :3])
        t[..., 4] = np.where(gold, 0.45, t[..., 4])
        pad = np.pad(inside, 1, mode="constant")
        nb = pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:]
        rim = inside & ~nb
        t[..., :3] = np.where(rim[..., None], tex.rgb("#ffe9a3"), t[..., :3])
        t[..., 4] = np.where(rim, 0.6, t[..., 4])
        t[..., 3] = inside * 1.0
        return t
    return Mat(fn, key, directional=False)


def rose(key="rose", petals=12):
    """Rose window: radial petals of blue and gold glass in a gilt ring, glyph core."""
    def fn(ctx):
        u, v = ctx.U * 2 - 1, ctx.V * 2 - 1
        r = np.hypot(u, v)
        a = (np.arctan2(v, u) / (2 * math.pi)) % 1.0
        t = np.zeros((ctx.h, ctx.w, 5))
        k = (a * petals) % 1.0
        petal = np.abs(k - 0.5) * 2 < (1 - np.clip((r - 0.25) / 0.7, 0, 1)) * 0.9 + 0.1
        odd = (np.floor(a * petals).astype(int) % 2) == 0
        col = np.where(odd[..., None], tex.rgb(BLUE), tex.rgb("#5f7fd6"))
        col = np.where((petal & (r > 0.3))[..., None], col, tex.rgb(WGOLD))
        t[..., :3] = col
        t[..., 4] = np.where(petal, 0.9, 0.7)
        pxl = 2.0 / ctx.w
        lines = (np.abs(r - 0.96) < pxl * 1.2) | (np.abs(r - 0.3) < pxl) | ((np.abs(k - 0.5) > 0.44) & (r > 0.3))
        t[..., :3] = np.where(lines[..., None], tex.rgb(GOLD), t[..., :3])
        t[..., 4] = np.where(lines, 0.4, t[..., 4])
        core = r < 0.18
        t[..., :3] = np.where(core[..., None], tex.rgb("#ffffff"), t[..., :3])
        t[..., 4] = np.where(core, 1.0, t[..., 4])
        t[..., 3] = (r <= 1.0) * 1.0
        return t
    return Mat(fn, key, directional=False)


def lattice_gold(key="gatelattice"):
    """Golden grille for the gate leaves: bars, frame and a glowing glyph medallion."""
    base = tex.metal(GOLD, "#ffe9a3", "#7a5a1e", bands=2.0, glow=0.15)
    g = np.array([[c == "#" for c in row] for row in FW[6]], dtype=bool)

    def fn(ctx):
        t = np.array(base.fn(ctx), dtype=float)
        ix, iy = tex.px(ctx)
        bars = ((ix % 4) == 0) | ((iy % 5) == 0) | (ix <= 0) | (ix >= ctx.w - 1) | (iy <= 0) | (iy >= ctx.h - 1)
        diag = ((ix + iy) % 8 == 0) | ((ix - iy + 400) % 8 == 0)
        keep = bars | diag
        cy, cx = ctx.h // 3, ctx.w // 2
        gy, gx = iy - (cy - 3), ix - (cx - 2)
        ing = (gy >= 0) & (gy < 7) & (gx >= 0) & (gx < 5)
        gm = np.zeros_like(keep)
        gm[ing] = g[gy[ing], gx[ing]]
        t[..., :3] = np.where(gm[..., None], tex.rgb("#ffffff"), t[..., :3])
        t[..., 4] = np.where(gm, 1.0, t[..., 4])
        t[..., 3] = (keep | gm) * 1.0
        return t
    return Mat(fn, key, directional=True)


class Mats:
    def __init__(self):
        self.marble = tex.marble(IVORY, "#d9cfb8", vein2="#c9a24a", scale=6)
        self.marble_t = tex.trimmed(self.marble, GOLD, 1, 0, glow=0.25)
        self.ashlar = tex.banded(tex.marble("#f1ead8", "#d5c9ae", scale=7), "#d8cbb0", every=6, width=1)
        self.gold = tex.metal(GOLD, "#ffe9a3", "#7a5a1e", bands=2.0)
        self.gold_g = tex.metal("#e2bf62", "#fff3c4", "#8a6a26", bands=3.0, glow=0.4)
        self.blue = tex.trimmed(tex.speck(BLUE, 0.05, edge_dark=0.2, glow=0.1), GOLD, 1, 0, glow=0.3)
        self.light = tex.glow_flat(WGOLD, 1.0, core="#ffffff")
        self.letter = tex.trimmed(tex.glow_flat("#fff8dc", 1.0, core="#ffffff"), "#ffd76a", 1, 0, glow=0.9)
        self.insc = tex.glyph_rows(FW, WGOLD, glow=1.0, color2="#ffd76a", fill=0.9, key="sanct_insc")
        self.insc_v = tex.glyph_rows(FW, WGOLD, glow=1.0, color2="#ffd76a", fill=0.85, vertical=True, key="sanct_inscv")
        self.insc_w = tex.glyph_rows(FW, "#ffffff", glow=1.0, color2=WGOLD, fill=1.0, key="sanct_inscw")
        self.insc_eng = over(tex.marble("#efe7d2", "#d3c6a8", scale=5),
                             tex.glyph_rows(FW, "#b8902f", glow=0.55, color2=GOLD, fill=0.8, key="sanct_eng"), "eng")
        self.lancet = lancet()
        self.rose = rose()
        self.lattice = lattice_gold()
        self.seal = tex.magic_circle(FW, "#ffffff", WGOLD, bands=((0.62, 0.92, 12),), lines=(0.58, 0.97), star=6,
                                     star_r=(0.2, 0.55), core=0.1)
        self.seal_w = tex.magic_circle(FW, "#ffffff", "#ffffff", bands=((0.62, 0.92, 12),), lines=(0.58, 0.97), star=4,
                                       star_r=(0.2, 0.55))

    def glyph(self, i, color=WGOLD, glow=1.0):
        return tex.bitmap_cut(FW[i % len(FW)], color, glow=glow, color2="#ffd76a")


# ================================================================ common piece parts
def add_letter(m, mt, gi, rest, pixel, depth=4.0):
    """The giant glowing glyph a piece is born as (centered on `rest`, reads from the front)."""
    g = FW[gi % len(FW)]
    gw, gh = len(g[0]) * pixel, len(g) * pixel
    b = m.bone("letter", "root", pivot=rest)
    glyphs.extrude(b, g, (rest[0] + gw / 2, rest[1] + gh / 2, rest[2] - depth / 2), pixel, depth, mt.letter)
    h = m.bone("letter_halo", "letter", pivot=rest)
    h.plane("z", (rest[0], rest[1], rest[2] + depth / 2 + 0.6), gh * 1.35, gh * 1.35, mt.seal)
    return gh


def add_shards(m, mt, spots, seed):
    """Small letters the piece breaks into: [(pos, delta, tumble)]."""
    seqi = glyphs.seq(seed, len(spots))
    names = []
    for i, (p, _d, _r) in enumerate(spots):
        b = m.bone(f"shard{i + 1}", "root", pivot=p)
        px_ = 2.2 if i % 2 == 0 else 1.8
        g = FW[seqi[i] % len(FW)]
        glyphs.extrude(b, g, (p[0] + 2.5 * px_, p[1] + 3.5 * px_, p[2] - 1), px_, 2.0, mt.letter)
        names.append(b.name)
    return names


def shard_spots(points, rng, out=1.0, H=60):
    """Tumbling trajectories for break shards: rise a little, fly outward (both faces), fall."""
    spots = []
    for i, p in enumerate(points):
        side = 1 if i % 2 == 0 else -1
        d = (rng.uniform(-16, 16), -H * rng.uniform(0.25, 0.5), side * out * rng.uniform(14, 26))
        r = (rng.uniform(-260, 260), rng.uniform(-300, 300), rng.uniform(-200, 200))
        spots.append((p, d, r))
    return spots


def piece_anims(spec):
    """Generic life cycle.  spec keys: H, rest, stretch, shards, quill (keys), insc, halo, thin, ribbons,
    rise, flare, form_extra(anim), struct_form (bool)."""
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    idle = Anim("idle", loop=True)
    for i, (bn, rate) in enumerate(spec.get("halo", [])):
        idle.rot(bn, (0, _spin(rate), 0))
    A.append(idle)

    letter = Anim("letter", length=LETTER_T, loop="hold")
    letter.scl("struct", 0.0)
    letter.scl("letter", {0: 0.12, 0.45: 1.12, 0.7: 1.0})
    letter.rot("letter", {0: (0, -200, 0), 0.55: (0, 12, 0), 0.7: (0, 0, 0)})
    letter.rot("letter_halo", (0, 0, _spin(90)))
    A.append(letter)

    form = Anim("form", length=FORM_T, loop="hold")
    sx, sy_, sz = spec["stretch"]
    if spec.get("letter_form"):
        spec["letter_form"](form)
    else:
        form.scl("letter", {0: 1.0, 0.3: (sx, sy_, sz), 0.62: (sx * 0.45, sy_ * 1.04, sz * 0.45), 0.78: 0.0})
        form.rot("letter_halo", {0: (0, 0, 0), 0.4: (0, 0, 180)})
        form.scl("letter_halo", {0: 1.0, 0.35: 0.0})
    if spec.get("struct_form", True):
        form.scl("struct", {0: (0.75, 0.0, 0.75), 0.2: (0.78, 0.03, 0.78), 0.7: (1.02, 1.04, 1.02), 0.85: (1, 0.99, 1),
                            1.0: (1, 1, 1)})
    if "quill" in spec:
        qp, qs = spec["quill"]
        form.pos("quill", qp)
        form.scl("quill", qs)
    for bn in spec.get("insc", []):
        form.scl(bn, {0: 0.0, 0.75: 0.0, 0.92: 1.15, 1.0: 1.0})
    if spec.get("form_extra"):
        spec["form_extra"](form)
    A.append(form)

    stand = Anim("stand", loop=True)
    for i, bn in enumerate(spec.get("insc", [])):
        stand.pos(bn, (0, LIFE(0.7, 3.2, i * 0.17), 0))
    if spec.get("stand_extra"):
        spec["stand_extra"](stand)
    A.append(stand)

    brk = Anim("break", length=BREAK_T, loop="hold")
    brk.scl("struct", {0: 1.0, 0.06: (1.03, 0.98, 1.03), 0.14: (0.97, 1.01, 0.97), 0.22: (1, 1, 1),
                       0.5: (0.35, 0.55, 0.35), 0.62: 0.0})
    brk.rot("struct", {0: (0, 0, 0), 0.05: (0, 0, 1.5), 0.1: (0, 0, -1.5), 0.15: (0, 0, 1), 0.5: (3, 0, -4)})
    for i, (p, d, r) in enumerate(spec["shards"]):
        bn = f"shard{i + 1}"
        t0 = 0.12 + 0.03 * i
        brk.scl(bn, {0: 0.0, t0: 0.0, t0 + 0.13: 1.25, 0.9: 1.0, BREAK_T: 0.0})
        brk.pos(bn, {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.3: (d[0] * 0.35, 9, d[2] * 0.4),
                     BREAK_T: d})
        brk.rot(bn, {0: (0, 0, 0), t0: (0, 0, 0), BREAK_T: r})
    A.append(brk)

    unw = Anim("unwrite", length=UNWRITE_T, loop="hold")
    for bn, thin in spec["thin"]:
        unw.scl(bn, {0: 1.0, 0.12: (1.03, 1.02, 1.03), 0.55: thin, 0.75: tuple(0.0 if abs(c - 1) > 1e-6 else 1.0 for c in thin)})
    if spec.get("unw_struct_fade"):
        unw.scl("struct", {0: 1.0, 0.7: 1.0, 0.95: 0.0})
    for bn in spec["ribbons"]:
        ax = spec.get("ribbon_axis", "y")
        z0, z1 = ((1, 0, 1), (1, 0.05, 1)) if ax == "y" else ((0, 1, 1), (0.05, 1, 1))
        unw.scl(bn, {0: z0, 0.2: z1, 0.5: 1.0, 0.85: 1.0, UNWRITE_T: (0.2, 0.5, 0.2)})
        unw.pos(bn, {0: (0, 0, 0), 0.6: (0, 0, 0), UNWRITE_T: spec["rise"]})
    A.append(unw)

    flare = Anim("flare", length=FLARE_T, loop="hold")
    for bn in spec.get("flare", []):
        flare.scl(bn, {0: 0.85, 0.12: 1.12, 0.3: 1.0, FLARE_T: 0.0})
    flare.scl("struct", {0: 1.0, 0.1: (1.015, 1.0, 1.015), 0.3: 1.0})
    A.append(flare)
    return A


def flare_planes(m, mt, parent, quads):
    b = m.bone("flare", parent)
    for axis, c, w, h in quads:
        b.plane(axis, c, w, h, mt.insc_w)
    return b


# ================================================================ pillar
P_H = 104
P_TOP = 94          # top of the abacus: vault ribs spring from here (11.75 blocks)


def pillar_model(mt, name, gi, variant):
    m = Model(name, density=1.0, bounds=(10, 18, (0, 7, 0)))
    m.bone("root")
    st = m.bone("struct", "root")
    st.box((0, 3, 0), (19, 6, 19), mt.marble_t)
    st.box((0, 7, 0), (15.5, 2, 15.5), mt.gold)
    ring(st, (0, 9.2, 0), 7.2, 12, (4.2, 2.2, 2.2), mt.gold, axis="y")
    st.box((0, 45, 0), (8.6, 72, 8.6), mt.marble)                      # octagonal shaft: core + 8 faces
    ring(st, (0, 45, 0), 4.6, 8, (4.7, 2.0, 72), mt.marble, axis="y", start=-22.5, variant=variant)
    for k in range(4):   # engaged colonnettes on the four axis faces
        a = math.radians(k * 90)
        cx, cz = 6.3 * math.cos(a), 6.3 * math.sin(a)
        st.box((cx, 45, cz), (2.4, 72, 2.4), mt.marble, variant=2)
        for y in (12, 45, 78):
            st.box((cx, y, cz), (3.2, 1.4, 3.2), mt.gold)
    for k in range(4):   # fluted inscription strips on the four diagonal faces
        a = math.radians(k * 90 + 45)
        c = (5.68 * math.cos(a), 45, 5.68 * math.sin(a))
        st.box(c, (0, 62, 3.4), mt.insc_v, rot=(0, -(k * 90 + 45), 0), faces=("east", "west"))
    for y in (24, 64):
        ring(st, (0, y, 0), 6.1, 8, (5.4, 1.6, 2.4), mt.blue, axis="y", start=22.5)
        ring(st, (0, y + 2.2, 0), 6.0, 8, (5.2, 1.4, 1.0), mt.gold_g, axis="y", start=22.5)
    st.box((0, 82.5, 0), (13, 3, 13), mt.gold)
    st.box((0, 86.5, 0), (12, 5, 12), mt.marble_t)
    ring(st, (0, 86.5, 0), 6.6, 8, (6.4, 2.4, 5), mt.marble_t, axis="y", start=-22.5)
    st.box((0, 92, 0), (20, 4, 20), mt.marble_t)
    for k in range(4):   # gilt volutes
        a = math.radians(k * 90 + 45)
        st.box((9.2 * math.cos(a), 88, 9.2 * math.sin(a)), (3.2, 3.2, 3.2), mt.gold_g, rot=(45, -(k * 90 + 45), 0))
    for k in range(4):   # capital glyph medallions
        a = k * 90
        st.box((0, 86.5, -8.0), (5, 5, 0), mt.glyph(gi + k + 3), rot=(0, a, 0), pivot=(0, 86.5, 0), faces=("north",))
    # finial: orb and orbiting letters above the capital
    fin = m.bone("finial", "struct", pivot=(0, 100, 0))
    fin.box((0, 100, 0), (4, 4, 4), mt.light, rot=(45, 45, 0))
    halo = m.bone("phalo", "struct", pivot=(0, 99, 0))
    for k in range(6):
        halo.box((0, 99, -9), (3.4, 4.8, 0), mt.glyph(gi * 3 + k), rot=(0, k * 60, 0), pivot=(0, 99, 0),
                 faces=("north", "south"))
    insc = m.bone("pinsc", "struct", pivot=(0, 50, 0))
    for k in range(2):
        insc.box((0, 30 + k * 34, -8.6), (4, 5.6, 0), mt.glyph(gi + 7 + k), rot=(0, 30 + k * 180, 0),
                 pivot=(0, 30 + k * 34, 0), faces=("north", "south"))

    rest = (0, 48, 0)
    add_letter(m, mt, gi, rest, 6.0)
    q = m.bone("quill", "root")
    ring(q, (0, 0, 0), 9.5, 12, (5.2, 1.6, 1.6), mt.light, axis="y")
    q.plane("y", (0, 0, 0), 22, 22, mt.seal)
    rng = np.random.default_rng(11 + variant)
    spots = shard_spots([(0, y, 0) for y in (14, 32, 50, 68, 86)], rng, H=P_H)
    add_shards(m, mt, spots, 40 + variant)
    rb = m.bone("ribbon", "root", pivot=(0, 0, 0))
    rb.plane("z", (0, 50, 0), 12, 96, mt.insc_v)
    rb.plane("x", (0, 50, 0), 12, 96, mt.insc_v, variant=1)
    fl = flare_planes(m, mt, "root", [("z", (0, 46, -6.2), 9, 70), ("z", (0, 46, 6.2), 9, 70),
                                       ("x", (6.2, 46, 0), 9, 70), ("x", (-6.2, 46, 0), 9, 70)])
    fl.plane("y", (0, 0.6, 0), 34, 34, mt.seal_w)
    spec = dict(H=P_H, rest=rest, stretch=(0.45, 2.15, 0.45), shards=spots,
                quill=({0: (0, 0, 0), 0.2: (0, 2, 0), 0.72: (0, P_TOP, 0)}, {0: 0.0, 0.12: 1.0, 0.72: 0.85, 0.86: 0.0}),
                insc=["pinsc", "finial"], halo=[("phalo", 40)], thin=[("struct", (0.12, 1.0, 0.12))],
                ribbons=["ribbon"], rise=(0, 60, 0), flare=["flare"])
    return m, spec


# ================================================================ wall panel
W_W = 50
W_H = 74


def wall_model(mt):
    m = Model("dw_sanct_wall", density=1.0, bounds=(10, 14, (0, 5, 0)))
    m.bone("root")
    st = m.bone("struct", "root")
    st.box((0, 3, 0), (52, 6, 9), mt.marble_t)
    st.box((0, 34, 0), (48, 56, 5), mt.ashlar)
    for sx in (-1, 1):
        st.box((sx * 22, 34, 0), (4.5, 56, 7.5), mt.marble, variant=1)
        st.box((sx * 22, 34, 0), (1.6, 44, 7.9), mt.blue)
    st.box((0, 28, 0), (3.6, 36, 6.4), mt.marble, variant=2)
    for z in (-2.65, 2.65):      # two stained-glass lancets on both faces
        for xc in (-11, 11):
            st.plane("z", (xc, 30, z), 13, 34, mt.lancet)
    for zs in (-1, 1):            # hood mouldings
        z = zs * 2.9
        for xc in (-11, 11):
            for sx in (-1, 1):
                st.box((xc + sx * 7.0, 26, z), (1.4, 26, 1.2), mt.gold)
                st.box((xc + sx * 3.6, 46.2, z), (8.4, 1.4, 1.2), mt.gold, rot=(0, 0, -sx * 38), pivot=(xc + sx * 3.6, 46.2, z))
            st.box((xc, 12.6, z), (15, 1.4, 1.6), mt.gold)
        st.plane("z", (0, 54.5, zs * 2.7), 12, 12, mt.rose)
        ring(st, (0, 54.5, zs * 3.0), 6.6, 12, (3.7, 1.3, 1.2), mt.gold_g, axis="z")
        st.plane("z", (0, 8.8, zs * 2.7), 40, 4.4, mt.insc_eng)
    st.box((0, 63, 0), (52, 2, 8), mt.gold)
    st.box((0, 66, 0), (54, 4, 9), mt.marble_t)
    for x in (-22, 22):           # pinnacles
        st.box((x, 70, 0), (3.4, 4, 3.4), mt.marble)
        st.box((x, 74, 0), (2.4, 4, 2.4), mt.gold_g, rot=(0, 45, 0))
    crest = m.bone("wcrest", "struct", pivot=(0, 72, 0))
    for i, x in enumerate((-15, -7.5, 7.5, 15)):
        crest.box((x, 72, 0), (4.6, 6.4, 0), mt.glyph(5 + i * 3), faces=("north", "south"))
    insc = m.bone("winsc", "struct", pivot=(0, 30, 0))
    for zs in (-1, 1):
        insc.plane("z", (0, 60.4, zs * 3.0), 40, 3.6, mt.insc, variant=(zs + 1) // 2)

    rest = (0, 34, 0)
    add_letter(m, mt, 13, rest, 6.0)
    q = m.bone("quill", "root")
    q.box((0, 0, 0), (56, 1.6, 9), mt.light)
    q.plane("y", (0, 0, 0), 60, 14, mt.insc_w)
    rng = np.random.default_rng(23)
    pts = [(-16, 16, 0), (12, 22, 0), (-6, 38, 0), (17, 46, 0), (-18, 58, 0), (4, 66, 0)]
    spots = shard_spots(pts, rng, H=W_H)
    add_shards(m, mt, spots, 51)
    rb = m.bone("ribbon", "root")
    for y in (14, 32, 50):
        rb.plane("z", (0, y, 0), 50, 7, mt.insc_w)
    fl = flare_planes(m, mt, "root", [("z", (0, 32, -3.3), 44, 50), ("z", (0, 32, 3.3), 44, 50)])
    spec = dict(H=W_H, rest=rest, stretch=(1.6, 1.25, 0.6), shards=spots,
                quill=({0: (0, 0, 0), 0.2: (0, 2, 0), 0.72: (0, W_H - 4, 0)}, {0: 0.0, 0.12: 1.0, 0.72: 0.9, 0.86: 0.0}),
                insc=["winsc", "wcrest"], thin=[("struct", (1.0, 0.1, 0.25))], ribbons=["ribbon"], rise=(0, 70, 0), ribbon_axis="x",
                flare=["flare"])
    return m, spec


# ================================================================ gate
G_H = 98


def gate_model(mt):
    m = Model("dw_sanct_gate", density=1.0, bounds=(12, 18, (0, 7, 0)))
    m.bone("root")
    st = m.bone("struct", "root")
    for sx in (-1, 1):
        st.box((sx * 18.5, 3, 0), (13, 6, 11), mt.marble_t)
        st.box((sx * 18.5, 40, 0), (12, 68, 7.5), mt.ashlar)
        st.box((sx * 24.2, 40, 0), (2.6, 68, 9), mt.marble, variant=1)
        st.box((sx * 12.9, 26, 0), (2.0, 40, 9), mt.gold_g)          # jamb shafts
        for zs in (-1, 1):
            st.plane("z", (sx * 18.5, 38, zs * 3.8), 6.5, 50, mt.insc_v, variant=(sx + 1) // 2)
        st.box((sx * 18.5, 80, 0), (6.5, 8, 6.5), mt.marble)          # pinnacles
        st.box((sx * 18.5, 87, 0), (3.6, 6, 3.6), mt.gold_g, rot=(0, 45, 0))
        st.box((sx * 18.5, 92, 0), (2.4, 2.4, 2.4), mt.light, rot=(45, 45, 0))
        st.box((sx * 10.6, 55.5, 0), (3.2, 5, 7.5), mt.marble, variant=2)  # spandrel fill
    ring(st, (0, 46, 0), 13.2, 11, (4.4, 4.2, 8.2), mt.marble_t, axis="z", start=0, sweep=180)
    ring(st, (0, 46, 0), 10.7, 11, (3.4, 1.0, 8.6), mt.gold_g, axis="z", start=0, sweep=180)
    st.box((0, 61.6, 0), (6, 6, 8.8), mt.blue, rot=(0, 0, 45))            # keystone
    st.box((0, 67, 0), (24, 14, 7.5), mt.ashlar)
    for zs in (-1, 1):
        st.plane("z", (0, 67, zs * 3.85), 12, 12, mt.seal)                 # tympanum seal
        st.plane("z", (0, 84, zs * 3.1), 10, 10, mt.rose)
    st.box((0, 75.5, 0), (54, 3, 9.5), mt.marble_t)
    for i, (w, y) in enumerate(((40, 80), (29, 85.5), (18, 91), (8, 95.5))):    # stepped gable
        st.box((0, y, 0), (w, 5.5, 6), mt.marble, variant=i % 2)
    for sx in (-1, 1):
        st.box((sx * 11.0, 87.5, 0), (25, 2.2, 7.2), mt.gold, rot=(0, 0, -sx * 38), pivot=(sx * 11.0, 87.5, 0))
    st.box((0, 99, 0), (3, 3, 3), mt.light, rot=(45, 45, 0))
    # threshold seal (the law) on the floor of the doorway
    st.plane("y", (0, 0.4, 0), 22, 22, mt.seal)
    # golden gate leaves, hinged at the jambs, standing open outward (+Z = outside)
    for s, sx in (("r", 1), ("l", -1)):
        lf = m.bone(f"leaf_{s}", "struct", pivot=(sx * 11.5, 6, 4.2), rot=(0, sx * 100, 0))
        lf.box((sx * 5.75, 28, 4.2), (11.5, 44, 0.8), mt.lattice)
        lf.box((sx * 0.6, 28, 4.2), (1.2, 44, 1.6), mt.gold)
    insc = m.bone("ginsc", "struct", pivot=(0, 50, 0))
    for i, x in enumerate((-18.5, 18.5)):
        insc.box((x, 70, -4.4), (5, 7, 0), mt.glyph(9 + i * 5), faces=("north", "south"))
        insc.box((x, 70, 4.4), (5, 7, 0), mt.glyph(9 + i * 5 + 1), faces=("north", "south"))

    rest = (0, 50, 0)
    add_letter(m, mt, 1, rest, 7.0)
    q = m.bone("quill", "root")
    q.box((0, 0, 0), (56, 1.6, 10), mt.light)
    q.plane("y", (0, 0, 0), 60, 16, mt.insc_w)
    rng = np.random.default_rng(31)
    pts = [(-18, 14, 0), (18, 26, 0), (-18, 44, 0), (0, 62, 0), (18, 70, 0), (0, 88, 0)]
    spots = shard_spots(pts, rng, H=G_H)
    add_shards(m, mt, spots, 61)
    rb = m.bone("ribbon", "root")
    for x in (-18.5, 18.5):
        rb.plane("z", (x, 44, 0), 9, 76, mt.insc_v)
    rb.plane("z", (0, 72, 0), 40, 8, mt.insc_w)
    fl = flare_planes(m, mt, "root", [("z", (-18.5, 40, -4.0), 11, 62), ("z", (18.5, 40, -4.0), 11, 62),
                                       ("z", (-18.5, 40, 4.0), 11, 62), ("z", (18.5, 40, 4.0), 11, 62)])
    fl.plane("y", (0, 0.9, 0), 30, 30, mt.seal_w)
    fl.plane("z", (0, 67, -4.1), 15, 15, mt.seal_w)
    fl.plane("z", (0, 67, 4.1), 15, 15, mt.seal_w)

    def gate_form(a):
        for s, sx in (("r", 1), ("l", -1)):          # leaves swing open at the end of the writing
            a.rot(f"leaf_{s}", {0: (0, -sx * 100, 0), 0.7: (0, -sx * 100, 0), 0.92: (0, sx * 6, 0), 1.0: (0, 0, 0)})

    def gate_unw(a):
        pass
    spec = dict(H=G_H, rest=rest, stretch=(1.5, 1.7, 0.6), shards=spots,
                quill=({0: (0, 0, 0), 0.2: (0, 2, 0), 0.72: (0, G_H - 6, 0)}, {0: 0.0, 0.12: 1.0, 0.72: 0.9, 0.86: 0.0}),
                insc=["ginsc"], thin=[("struct", (0.25, 1.0, 0.25))], ribbons=["ribbon"], rise=(0, 66, 0),
                flare=["flare"], form_extra=gate_form)
    return m, spec


# ================================================================ bridge (flying gallery)
def bridge_model(mt):
    m = Model("dw_sanct_bridge", density=1.0, bounds=(10, 6, (0, 1, 0)))
    m.bone("root")
    st = m.bone("struct", "root")
    st.box((0, 2, 0), (56, 4, 12), mt.marble_t)
    ring(st, (0, -18, 0), 21.5, 9, (5.2, 4.2, 10), mt.marble, axis="z", start=32, sweep=116)
    ring(st, (0, -18, 0), 18.8, 9, (5.0, 1.2, 10.6), mt.gold_g, axis="z", start=32, sweep=116)
    for x in (-24, -12, 0, 12, 24):       # arcade columns on the inner edge
        st.box((x, 10, -4.2), (2.2, 12, 2.2), mt.marble, variant=1)
        st.box((x, 4.8, -4.2), (3.2, 1.6, 3.2), mt.gold)
    for x in (-18, -6, 6, 18):            # little round arches
        ring(st, (x, 16, -4.2), 5.4, 5, (3.6, 2.0, 2.6), mt.gold_g, axis="z", start=0, sweep=180)
    st.box((0, 23.2, -4.2), (54, 2.2, 4.2), mt.marble_t)
    st.box((0, 9, 4.6), (54, 10, 2.8), mt.marble, variant=2)    # back parapet
    st.plane("z", (0, 9, 6.05), 50, 6, mt.insc_eng)
    for x in (-14, 14):                   # hanging lanterns
        st.box((x, -3.5, 0), (0.8, 5, 0.8), mt.gold)
        st.box((x, -8, 0), (3.2, 4.4, 3.2), mt.light, rot=(0, 45, 0))
    insc = m.bone("binsc", "struct", pivot=(0, 9, 0))
    insc.plane("z", (0, 9, 3.0), 50, 4, mt.insc)
    for i, x in enumerate((-20, 0, 20)):
        insc.box((x, 29, 0), (4, 5.6, 0), mt.glyph(2 + i * 4), faces=("north", "south"))

    rest = (0, 12, 0)
    add_letter(m, mt, 7, rest, 5.0)
    q = m.bone("quill", "root")
    q.box((0, 0, 0), (2, 30, 14), mt.light)
    rng = np.random.default_rng(37)
    pts = [(-22, 8, 0), (-8, 2, 0), (8, 12, 0), (22, 4, 0), (0, 22, 0)]
    spots = shard_spots(pts, rng, H=30)
    add_shards(m, mt, spots, 71)
    rb = m.bone("ribbon", "root")
    rb.plane("z", (0, 6, 0), 56, 7, mt.insc_w)
    rb.plane("y", (0, 6, 0), 56, 7, mt.insc_w, variant=1)
    fl = flare_planes(m, mt, "root", [("z", (0, 9, 6.3), 50, 10), ("z", (0, 9, -6.3), 50, 10)])

    def bridge_form(a):     # the gallery is written from left to right
        a.scl("struct", {0: (0.0, 0.8, 0.8), 0.15: (0.04, 0.9, 0.9), 0.7: (1.03, 1.03, 1.03), 0.85: 1.0})
        a.pos("quill", {0: (-28, 0, 0), 0.15: (-26, 0, 0), 0.7: (28, 0, 0)})
        a.scl("quill", {0: 0.0, 0.1: 1.0, 0.7: 1.0, 0.8: 0.0})
    spec = dict(H=30, rest=rest, stretch=(2.0, 0.5, 0.8), shards=spots, struct_form=False, form_extra=bridge_form,
                insc=["binsc"], thin=[("struct", (1.0, 0.1, 0.1))], ribbons=["ribbon"], rise=(0, 40, 0), flare=["flare"],
                ribbon_axis="x")
    return m, spec


# ================================================================ vault rib
R_L, R_RISE, R_N = 62.0, 38.0, 8


def rib_points():
    pts = []
    for i in range(R_N + 1):
        ph = math.pi / 2 * i / R_N
        pts.append((0.0, R_RISE * math.sin(ph), -R_L * (1 - math.cos(ph))))
    return pts


def rib_model(mt):
    m = Model("dw_sanct_rib", density=1.0, bounds=(18, 14, (0, 2, 0)))
    m.bone("root")
    st = m.bone("struct", "root")
    st.box((0, 1.5, 0), (8, 3, 8), mt.gold)
    st.box((0, 4.5, 0), (6, 3, 6), mt.marble_t)
    pts = rib_points()
    segs = []
    for i in range(R_N):
        p, q = pts[i], pts[i + 1]
        dy, dz = q[1] - p[1], q[2] - p[2]
        L = math.hypot(dy, dz)
        rx = -math.degrees(math.atan2(-dz, dy))
        b = m.bone(f"seg{i + 1}", "struct", pivot=p, rot=(rx, 0, 0))
        b.box((0, p[1] + L / 2, p[2]), (4.4, L + 0.8, 5.2), mt.marble, variant=i % 3)
        b.box((0, p[1] + L / 2, p[2] + 3.0), (2.2, L + 0.4, 1.2), mt.gold_g)
        b.box((0, p[1] + L / 2, p[2] - 3.0), (1.4, L + 0.4, 0.9), mt.gold)
        for sx in (-1, 1):
            b.plane("x", (sx * 2.25, p[1] + L / 2, p[2]), 3.6, L, mt.insc, variant=(i + (sx + 1) // 2) % 3)
        if i % 2 == 1:   # crockets
            b.box((0, p[1] + L * 0.5, p[2] + 4.4), (2.4, 2.4, 2.4), mt.gold_g, rot=(45, 0, 45))
        else:            # hanging pendant letters on the underside
            b.box((0, p[1] + L * 0.5, p[2] - 6.2), (0, 4.6, 3.4), mt.glyph(i * 2 + 3), faces=("east", "west"))
        segs.append(b.name)
    end = pts[-1]
    boss = m.bone("rboss", "struct", pivot=end)
    boss.box(end, (5.5, 5.5, 5.5), mt.gold_g, rot=(45, 0, 45))

    rest = (0, 16, -6)
    add_letter(m, mt, 10, rest, 5.0)
    q = m.bone("quill", "root")
    q.box((0, 0, 0), (7, 7, 7), mt.light, rot=(45, 45, 0))
    q.plane("x", (0, 0, 0), 14, 14, mt.seal)
    rng = np.random.default_rng(43)
    spots = shard_spots([pts[k] for k in (1, 3, 4, 6, 8)], rng, out=0.4, H=40)
    spots = [(p, (d[2], d[1], d[0] * 0.5), r) for p, d, r in spots]     # rib shards scatter sideways
    add_shards(m, mt, spots, 81)
    ribbons = []
    for i in range(R_N):
        p, q2 = pts[i], pts[i + 1]
        dy, dz = q2[1] - p[1], q2[2] - p[2]
        L = math.hypot(dy, dz)
        rx = -math.degrees(math.atan2(-dz, dy))
        rb = m.bone(f"ribbon{i + 1}", "root", pivot=p, rot=(rx, 0, 0))
        rb.plane("x", (0, p[1] + L / 2, p[2]), 6, L + 0.5, mt.insc_w, variant=i % 2)
        ribbons.append(rb.name)

    T0, T1 = 0.12, 0.82

    def rib_form(a):
        a.scl("struct", 1.0)
        a.scl("rboss", {0: 0.0, T1: 0.0, T1 + 0.1: 1.3, 1.0: 1.0})
        lk, qk = {0: (0, 0, 0)}, {}
        for i, sn in enumerate(segs):
            t0 = T0 + (T1 - T0) * i / R_N
            t1 = T0 + (T1 - T0) * (i + 1) / R_N
            a.scl(sn, {0: 0.0, t0: (0.0, 0.0, 0.0), t0 + 0.01: (0.6, 0.0, 0.6), t1: (1.0, 1.0, 1.0)}, smooth=False)
            tip = pts[i + 1]
            lk[t1] = (tip[0] - rest[0], tip[1] + 7 - rest[1], tip[2] - rest[2])
            qk[t1] = tip
        a.pos("letter", lk)
        a.scl("letter", {0: 1.0, 0.3: 0.65, T1: 0.45, T1 + 0.08: 0.0})
        a.rot("letter", {0: (0, 0, 0), T1: (-80, 0, 0)})
        a.scl("letter_halo", {0: 1.0, 0.3: 0.0})
        qk[0] = pts[0]
        a.pos("quill", qk)
        a.scl("quill", {0: 0.0, T0: 1.0, T1: 1.0, T1 + 0.1: 0.0})

    spec = dict(H=40, rest=rest, stretch=(1, 1, 1), shards=spots, struct_form=False, letter_form=lambda a: None,
                form_extra=rib_form, insc=[], thin=[(s, (0.1, 1.0, 0.1)) for s in segs], ribbons=ribbons, unw_struct_fade=True,
                rise=(0, 34, 0))
    return m, spec


# ================================================================ crown / keystone
def crown_model(mt):
    m = Model("dw_sanct_crown", density=1.0, bounds=(10, 8, (0, 0, 0)))
    m.bone("root")
    st = m.bone("struct", "root")
    ring(st, (0, 0, 0), 14, 16, (5.8, 4.2, 4.6), mt.marble_t, axis="y")
    ring(st, (0, 2.9, 0), 14, 16, (5.8, 2.6, 1.6), mt.gold_g, axis="y")
    ring(st, (0, -2.6, 0), 12.4, 16, (5.0, 1.2, 1.2), mt.blue, axis="y")
    st.box((0, 0, 0), (8, 6, 8), mt.gold)
    st.box((0, 0, 0), (8, 6, 8), mt.gold, rot=(0, 45, 0))
    for k in range(8):           # open lattice spokes
        a = k * 45 + 22.5
        st.box((0, 0.5, -8.0), (1.4, 1.4, 8.4), mt.gold_g, rot=(0, a, 0), pivot=(0, 0.5, 0))
    st.plane("y", (0, -3.3, 0), 22, 22, mt.seal)
    st.box((0, -7, 0), (0.9, 8, 0.9), mt.gold)                       # lantern chain + lantern
    st.box((0, -14, 0), (5.5, 7.5, 5.5), mt.light)
    st.box((0, -14, 0), (6.5, 1.2, 6.5), mt.gold, rot=(0, 45, 0))
    st.box((0, -10, 0), (6.5, 1.2, 6.5), mt.gold, rot=(0, 45, 0))
    st.box((0, -18.5, 0), (2, 2, 2), mt.gold_g, rot=(45, 0, 45))
    st.box((0, 7.5, 0), (4.2, 9, 4.2), mt.marble)                    # spire
    st.box((0, 15, 0), (2.8, 7, 2.8), mt.gold_g, rot=(0, 45, 0))
    st.box((0, 21, 0), (3.6, 3.6, 3.6), mt.light, rot=(45, 45, 0))
    halo = m.bone("chalo", "struct", pivot=(0, 6, 0))
    for k in range(12):
        halo.box((0, 6, -22), (4.2, 5.8, 0), mt.glyph(k * 5 + 2), rot=(0, k * 30, 0), pivot=(0, 6, 0),
                 faces=("north", "south"))
    halo2 = m.bone("chalo2", "struct", pivot=(0, 0, 0), rot=(12, 0, 8))
    ring(halo2, (0, 0, 0), 27, 24, (4.2, 0.8, 0.8), mt.gold_g, axis="y")

    rest = (0, 2, 0)
    add_letter(m, mt, 11, rest, 6.0)
    q = m.bone("quill", "root")
    ring(q, (0, 0, 0), 18, 12, (6, 1.4, 1.4), mt.light, axis="y")
    rng = np.random.default_rng(53)
    spots = shard_spots([(10, 0, 0), (-10, 0, 0), (0, 0, 10), (0, 0, -10), (0, -14, 0)], rng, H=30)
    add_shards(m, mt, spots, 91)
    rb = m.bone("ribbon", "root")
    rb.plane("z", (0, 0, 0), 8, 44, mt.insc_v)
    rb.plane("x", (0, 0, 0), 8, 44, mt.insc_v, variant=1)

    def crown_form(a):
        a.scl("struct", {0: 0.0, 0.25: 0.05, 0.7: 1.08, 0.85: 1.0})
        a.rot("struct", {0: (0, -160, 0), 0.85: (0, 0, 0)})
        a.scl("quill", {0: 0.0, 0.2: 0.3, 0.6: 1.5, 0.8: 0.0})
        a.rot("quill", {0: (0, 0, 0), 0.8: (0, 200, 0)})
    spec = dict(H=30, rest=rest, stretch=(1.6, 1.6, 1.6), shards=spots, struct_form=False, form_extra=crown_form,
                halo=[("chalo", 26), ("chalo2", -14)], insc=[], thin=[("struct", (0.08, 1.2, 0.08))],
                ribbons=["ribbon"], rise=(0, 50, 0))
    return m, spec


# ================================================================ script line (ruled line of writing)
SC_N, SC_R = 24, 56


def script_model(mt):
    m = Model("dw_sanct_script", density=2.0, bounds=(10, 4, (0, 0, 0)))
    m.bone("root")
    sp = m.bone("spin", "root")
    seqi = glyphs.seq(5, SC_N)
    for i in range(SC_N):
        b = m.bone(f"p{i + 1}", "spin", pivot=(0, 0, 0), rot=(0, i * 360 / SC_N, 0))
        b.box((0, 0, -SC_R), (9.5, 13.3, 0), mt.glyph(seqi[i]), faces=("north", "south"))
    for y in (-8.5, 8.5):
        rl = m.bone(f"rule{'t' if y > 0 else 'b'}", "spin", pivot=(0, y, 0))
        ring(rl, (0, y, 0), SC_R + 0.4, SC_N, (14.8, 0.5, 0.5), mt.gold_g, axis="y")
    nib = m.bone("nib", "spin", pivot=(0, 0, 0))
    nib.box((0, 0, -SC_R - 1), (3, 3, 3), mt.light, rot=(45, 45, 0), pivot=(0, 0, -SC_R - 1))
    return m


def script_anims():
    A = []
    h = Anim("hidden", loop=True)
    h.scl("root", 0.0)
    A.append(h)
    turn = Anim("turn", loop=True)
    turn.rot("spin", (0, _spin(-24), 0))
    for i in range(SC_N):
        turn.pos(f"p{i + 1}", (0, LIFE(0.6, 2.4, i / SC_N), 0))
    A.append(turn)
    write = Anim("write", length=WRITE_T, loop="hold")
    step = (WRITE_T - 0.2) / SC_N
    for i in range(SC_N):
        t0 = 0.05 + i * step
        write.scl(f"p{i + 1}", {0: 0.0, t0: 0.0, t0 + 0.06: 1.35, t0 + 0.14: 1.0}, smooth=False)
    write.rot("nib", {0: (0, 0, 0), 0.05 + SC_N * step: (0, 360, 0)}, smooth=False)
    write.scl("nib", {0: 1.0, WRITE_T - 0.1: 1.0, WRITE_T: 0.0})
    for r in ("rulet", "ruleb"):
        write.scl(r, {0: (0.0, 1, 0.0), 0.35: (1.0, 1, 1.0)})
    A.append(write)
    hold = Anim("hold", loop=True)
    hold.scl("nib", 0.0)
    A.append(hold)
    peel = Anim("peel", length=PEEL_T, loop="hold")
    peel.scl("nib", 0.0)
    order = glyphs.seq(9, SC_N)
    rank = sorted(range(SC_N), key=lambda k: order[k])
    for j, i in enumerate(rank):
        t0 = 0.1 + j * (PEEL_T - 0.5) / SC_N
        peel.scl(f"p{i + 1}", {0: 1.0, t0: 1.0, t0 + 0.08: 1.5, t0 + 0.22: 0.0}, smooth=False)
        peel.pos(f"p{i + 1}", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.22: (0, 10, 0)}, smooth=False)
    A.append(peel)
    fade = Anim("fade", length=FADE_T, loop="hold")
    fade.scl("nib", 0.0)
    for i in range(SC_N):
        fade.scl(f"p{i + 1}", 0.0)
    for r in ("rulet", "ruleb"):
        fade.scl(r, {0: 1.0, FADE_T: (1.6, 1, 1.6)})
    fade.scl("spin", {0: 1.0, 0.45: (1.2, 1.0, 1.2), FADE_T: 0.0})
    A.append(fade)
    return A


# ================================================================ assembly preview (art direction only)
BRIDGE_Y = 10.0        # blocks above the floor (mirrors DW04 config)
R_CORNER = 9.5 * 8     # model units at half scale (1 block = 8 units)


def placements():
    """(model key, (x, y, z) units, angle_deg of the outward direction) for the assembled cathedral."""
    out = []
    apo = R_CORNER * math.cos(math.radians(22.5))
    for k in range(8):
        a = k * 45 + 22.5
        out.append(("pillar" if k % 2 == 0 else "pillar2", (R_CORNER * math.cos(math.radians(a)), 0, R_CORNER * math.sin(math.radians(a))), a))
    for k in range(8):
        a = k * 45
        p = (apo * math.cos(math.radians(a)), 0, apo * math.sin(math.radians(a)))
        out.append(("gate" if k % 2 == 0 else "wall", p, a))
        if k % 2 == 1:
            out.append(("bridge", (p[0], BRIDGE_Y * 8, p[2]), a))
    for k in range(8):
        a = k * 45 + 22.5
        out.append(("rib", (R_CORNER * math.cos(math.radians(a)), P_TOP, R_CORNER * math.sin(math.radians(a))), a))
    out.append(("crown", (0, P_TOP + R_RISE, 0), 0))
    return out


HIDE = ("letter", "shard", "quill", "ribbon", "flare")


def assembly(models, name="dw_sanct_assembly", include=None):
    big = Model(name, density=0.5, bounds=(40, 40, (0, 8, 0)))
    big.bone("root")
    n = 0
    for key, p, a in placements():
        if include and key not in include:
            continue
        src = models[key]
        yaw = 90 - a                  # front (-Z) faces the centre
        r = math.radians(yaw)
        # translation expressed in the rotated frame: rotate p by -yaw about Y
        c, s = math.cos(r), math.sin(r)
        lx, lz = c * p[0] - s * p[2], s * p[0] + c * p[2]
        off = (lx, p[1], lz)
        holder = big.bone(f"h{n}", "root", pivot=(0, 0, 0), rot=(0, yaw, 0))
        n += 1
        for bn in src.order:
            if bn == "root" or any(bn.startswith(h) for h in HIDE):
                continue
            b = src.bones[bn]
            par = holder.name if b.parent in (None, "root") else f"{holder.name}_{b.parent}"
            nb = big.bone(f"{holder.name}_{bn}", par, pivot=tuple(b.pivot[i] + off[i] for i in range(3)), rot=b.rot)
            for cu in b.cubes:
                nc = Cube(nb, tuple(cu.origin[i] + off[i] for i in range(3)), cu.size, cu.mat, rot=cu.rot,
                          pivot=tuple(cu.pivot[i] + off[i] for i in range(3)) if cu.pivot else None, inflate=cu.inflate,
                          density=cu.density, faces=cu.faces, variant=cu.variant, mats=cu.mats)
                nb.cubes.append(nc)
    return big


def _merge_pose(items):
    merged = {}
    for a, t in items:
        for b, (r, pp, sc) in a.pose(t).items():
            if b in merged:
                r0, p0, s0 = merged[b]
                merged[b] = (tuple(r0[i] + r[i] for i in range(3)), tuple(p0[i] + pp[i] for i in range(3)),
                             tuple(s0[i] * sc[i] for i in range(3)))
            else:
                merged[b] = (r, pp, sc)
    return merged


def lifecycle_sheet(name, model, by, views=((25, 14), (155, 22)), cell=(260, 300)):
    """One contact sheet: columns = life-cycle poses (with the in-game part visibility), rows = views."""
    import os
    from PIL import Image
    from kit.pack import PREVIEW
    from kit.render import render
    idle = (by["idle"], 1.0)
    poses = [([(by["letter"], LETTER_T), idle], ("shard", "quill", "ribbon", "flare")),
             ([(by["form"], 0.3), idle], ("shard", "ribbon", "flare")),
             ([(by["form"], 0.6), idle], ("shard", "ribbon", "flare")),
             ([(by["stand"], 0.5), idle], HIDE),
             ([(by["break"], 0.45), idle], ("letter", "quill", "ribbon", "flare")),
             ([(by["unwrite"], 0.45), idle], ("letter", "shard", "quill", "flare")),
             ([(by["unwrite"], 1.1), idle], ("letter", "shard", "quill", "flare"))]
    model.finalize()
    lo, hi = model.bbox(_merge_pose(poses[3][0]))
    c = (lo + hi) / 2
    half = float(max(hi - lo)) * 0.62
    out = Image.new("RGBA", (cell[0] * len(poses), cell[1] * len(views)))
    for i, (items, hide) in enumerate(poses):
        pz = _merge_pose(items)
        for j, (yw, pt) in enumerate(views):
            im = render(model, pz, yaw=yw, pitch=pt, size=cell, hide=hide, fit=(c, half))
            out.paste(im, (i * cell[0], j * cell[1]))
    os.makedirs(PREVIEW, exist_ok=True)
    out.save(os.path.join(PREVIEW, f"{name}.png"))


# ================================================================ build
def build(pack):
    fx = particles(pack)
    G = [f"glyph{i}" for i in range(1, 9)]
    fx.effect("dw_sanct_ink", None, sprites=G, count=3, life=(0.5, 0.9), size=(0.22, 0.04), shape=("sphere", 0.6),
              speed=(0.1, 0.5), accel=(0, 0.4, 0), drag=1.0, colors=["#ffffffff", "#fff3c4ff", "#c9a24a00"])
    fx.effect("dw_sanct_quill", "spark", count=10, life=(0.25, 0.6), size=(0.12, 0.0), shape=("sphere", 0.4),
              speed=(1.5, 4.0), accel=(0, -2, 0), drag=1.5, colors=["#ffffffff", "#ffe9a3ff", "#c9a24a00"], spin=(360, 300))
    fx.effect("dw_sanct_peel", None, sprites=G, count=6, life=(0.6, 1.0), size=(0.3, 0.08), shape=("sphere", 0.5),
              speed=(0.6, 1.8), drag=1.4, colors=["#ffffffff", "#fff3c4ff", "#ffd76a00"])
    fx.effect("dw_sanct_settle", "puff", count=10, life=(0.7, 1.3), size=(0.4, 1.1), shape=("disc", 1.6), speed=(0.8, 2.0),
              direction="outwards", accel=(0, 0.3, 0), drag=1.6, colors=["#f3ead6cc", "#d9cfb800"], blend="blend", spin=(360, 40))
    fx.effect("dw_sanct_gild", "dot", count=12, life=(0.8, 1.6), size=(0.09, 0.0), shape=("disc", 1.4), speed=(0.2, 0.8),
              direction=(0, 1, 0), accel=(0, 0.8, 0), colors=["#fff3c4ff", "#ffd76aff", "#c9a24a00"])
    fx.effect("dw_sanct_edict", "ringthin", count=1, life=(0.45, 0.55), size=(0.4, 3.2), facing="emitter_transform_xz",
              colors=["#ffffffff", "#fff3c4cc", "#2b3f8f00"])
    fx.effect("dw_sanct_law", None, sprites=["rune1", "rune2", "rune3", "glyph4", "glyph6"], count=7, life=(0.4, 0.7),
              size=(0.35, 0.1), shape=("disc", 1.2), direction=(0, 1, 0), speed=(1.0, 2.5), drag=2.0,
              colors=["#ffffffff", "#8fa8e8ff", "#2b3f8f00"])
    fx.effect("dw_sanct_ward", "ring", count=1, life=(0.4, 0.5), size=(0.4, 1.4), colors=["#fff3c4ff", "#c9a24a00"])
    fx.effect("dw_sanct_dissolve", None, sprites=G, count=8, life=(0.4, 0.8), size=(0.18, 0.02), shape=("sphere", 0.3),
              speed=(1.0, 2.4), drag=1.8, colors=["#ffffffff", "#fff3c4ff", "#c9a24a00"])
    fx.effect("dw_sanct_shard", None, sprites=G, count=8, life=(1.0, 1.6), size=(0.38, 0.14), shape=("box", (1.6, 2.5, 0.6)),
              speed=(1.0, 2.6), accel=(0, -5, 0), drag=0.4, colors=["#ffffffff", "#fff3c4ff", "#c9a24a00"], spin=(360, 220))
    fx.effect("dw_sanct_stream", None, sprites=G, count=6, life=(1.0, 1.8), size=(0.24, 0.06), shape=("box", (0.8, 2.5, 0.8)),
              direction=(0, 1, 0), speed=(1.5, 3.0), accel=(0, 1.2, 0), drag=0.6, colors=["#ffffffff", "#fff3c4ff", "#c9a24a00"])
    fx.effect("dw_sanct_mote", "dot", count=6, life=(1.5, 2.5), size=(0.06, 0.0), shape=("disc", 7.0), speed=(0.05, 0.25),
              direction=(0, 1, 0), accel=(0, 0.25, 0), colors=["#fff3c4ff", "#fff3c400"])
    fx.effect("dw_sanct_beam", "beam", count=8, life=(0.4, 0.7), size=(0.16, 0.02), size_y=(2.0, 4.0), shape=("disc", 1.0),
              direction=(0, 1, 0), speed=(5, 10), colors=["#ffffffff", "#fff3c4ff", "#ffd76a00"], facing="lookat_y")

    mt = Mats()
    p1, ps1 = pillar_model(mt, "dw_sanct_pillar", 0, 0)
    p2, ps2 = pillar_model(mt, "dw_sanct_pillar_b", 16, 1)
    w, ws = wall_model(mt)
    g, gs = gate_model(mt)
    b, bs = bridge_model(mt)
    r, rs = rib_model(mt)
    c, cs = crown_model(mt)
    common = dict(scale=SCALE, lifetime=60, visibility=VISIBILITY, blend=0.1)
    builds = [("dw_sanct_pillar", p1, ps1, dict(kinds=[p2], display="Sanctuary Pillar")),
              ("dw_sanct_wall", w, ws, dict(display="Sanctuary Wall")),
              ("dw_sanct_gate", g, gs, dict(display="Sanctuary Gate")),
              ("dw_sanct_bridge", b, bs, dict(display="Sanctuary Gallery")),
              ("dw_sanct_rib", r, rs, dict(display="Sanctuary Vault Rib")),
              ("dw_sanct_crown", c, cs, dict(display="Sanctuary Crown"))]
    anims_by = {}
    for ident, model, spec, extra in builds:
        anims = piece_anims(spec)
        anims_by[ident] = anims
        pack.actor(ident, model, anims, PIECE_STATES, always=["idle"], **common, **extra)
        print(f"    {ident}: {model.cube_count()} cubes, {len(model.order)} bones, tex {model.tex_size}")
    sm = script_model(mt)
    sa = script_anims()
    pack.actor("dw_sanct_script", sm, sa, SCRIPT_STATES, always=["turn"], size_prop=True, lifetime=60,
               display="Line of Sacred Writing", blend=0.0)

    # ---- previews: life cycle sheets per piece + the assembled cathedral
    if pack.preview.enabled:
        for ident, model, spec, _x in builds:
            by = {a.name: a for a in anims_by[ident]}
            lifecycle_sheet(ident, model, by)
    by = {a.name: a for a in sa}
    pack.preview("dw_sanct_script", sm, [(by["write"], 0.6), [(by["hold"], 0), (by["turn"], 1)], (by["peel"], 1.8)],
                 views=((20, 25),), cell=(360, 300))
    if pack.preview.enabled:
        import os
        big = assembly({"pillar": p1, "pillar2": p2, "wall": w, "gate": g, "bridge": b, "rib": r, "crown": c})
        if os.environ.get("SANCT_ASM", "1") == "1":
            pack.preview("dw_sanct_assembly", big, [None], views=((20, 12), (65, 30), (0, 88)), cell=(560, 480), hide=HIDE)

    import os as _os
    if _os.environ.get("SANCT_NOSND") != "1":
        build_sounds(pack)


def build_sounds(pack):
    def chord(root, vowel, dur, ratios, bright=1.0, attack=0.25, release=0.5):
        return sy.mixdown([sy.choir(root * k, dur, vowel, voices=4 if i else 5, bright=bright, attack=attack, release=release)
                           for i, k in enumerate(ratios)])

    # quill scribble + choir swell while the lines are written
    write = sy.at(2.6, (0.0, sy.scribble(1.4, 9) * 0.55), (0.2, sy.scribble(1.2, 7) * 0.35),
                  (0.1, chord(174.6, "oo", 2.3, (1.0, 1.5, 2.0, 2.52), attack=1.2, release=0.8) * 0.5),
                  (1.2, sy.shimmer(1.3, 2400, 14) * 0.25))
    sy.save(pack, "dw_sanct_write", sy.reverb(write, 2.2, 0.4), max_distance=64)
    # a letter peeling off the line
    pe = sy.at(0.5, (0.0, sy.whoosh(0.35, 900, 4200) * 0.5), (0.02, sy.pluck(1567.98, 0.35, 0.8) * 0.4))
    sy.save(pack, "dw_sanct_letter", sy.reverb(pe, 0.8, 0.3), volume=0.6, max_distance=40,
            variants=[sy.reverb(sy.pitch(pe, 1.12), 0.8, 0.3), sy.reverb(sy.pitch(pe, 0.89), 0.8, 0.3)])

    # stone settling: weight, grind of marble, a gilded ring  (three variants)
    def settle(f, bellf):
        grind = sy.lowpass(sy.bandpass(sy.noise(0.7), 420, 1.2), 1200) * np.exp(-np.linspace(0, 5, int(0.7 * sy.SR)))
        return sy.at(1.2, (0.0, sy.thump(0.6, f, f * 0.35, 0.45)), (0.03, grind * 0.6), (0.0, sy.rumble(0.8, 60, 4.0) * 0.3),
                     (0.08, sy.bell(bellf, 0.9, bright=0.7) * 0.22))
    s0, s1, s2 = settle(120, 523.3), settle(96, 659.3), settle(140, 440.0)
    sy.save(pack, "dw_sanct_settle", sy.reverb(s0, 1.4, 0.35), max_distance=48,
            variants=[sy.reverb(s1, 1.4, 0.35), sy.reverb(s2, 1.4, 0.35)])
    # the crown sets: the sanctuary is complete
    comp = sy.at(3.0, (0.0, sy.thump(1.0, 110, 30, 0.6)), (0.02, sy.bell(293.7, 2.4, bright=1.2) * 0.6),
                 (0.05, chord(146.8, "ah", 2.6, (1.0, 1.5, 2.0, 2.5, 3.0), bright=1.2, attack=0.15, release=1.0) * 0.7),
                 (0.3, sy.shimmer(1.8, 2600, 22) * 0.3))
    sy.save(pack, "dw_sanct_complete", sy.reverb(comp, 3.0, 0.45), max_distance=80)
    # quiet sustained bed (replayed by the script every 3 s)
    bed = sy.mixdown([sy.pad(110.0, 3.2, cutoff=900, attack=0.8, release=0.8) * 0.6,
                      sy.choir(220.0, 3.2, "oo", voices=4, attack=0.9, release=0.9, bright=0.6) * 0.5,
                      sy.choir(330.0, 3.2, "oo", voices=3, attack=1.1, release=0.9, bright=0.5) * 0.35])
    sy.save(pack, "dw_sanct_bed", sy.reverb(bed, 2.0, 0.5), volume=0.45, max_distance=32)
    # ward absorbs a blow
    ab = sy.at(0.9, (0.0, sy.bell(1046.5, 0.8, bright=1.1) * 0.6), (0.0, sy.bell(1396.9, 0.6) * 0.3),
               (0.02, sy.shimmer(0.6, 3000, 8) * 0.3))
    sy.save(pack, "dw_sanct_absorb", sy.reverb(ab, 1.2, 0.35), volume=0.8, max_distance=32,
            variants=[sy.reverb(sy.pitch(ab, 1.06), 1.2, 0.35)])
    # threshold law: a hostile is repelled at the gate
    rp = sy.at(1.0, (0.0, sy.thump(0.5, 160, 50, 0.6) * 0.8), (0.0, sy.whoosh(0.45, 2400, 500) * 0.5),
               (0.03, chord(392.0, "eh", 0.6, (1.0, 1.335), bright=1.4, attack=0.01, release=0.35) * 0.5))
    sy.save(pack, "dw_sanct_repel", sy.reverb(rp, 1.2, 0.35), max_distance=40)
    # projectile turned to letters
    ds = sy.at(0.6, (0.0, sy.shimmer(0.45, 3200, 10) * 0.5), (0.0, sy.whoosh(0.3, 3000, 900) * 0.3))
    sy.save(pack, "dw_sanct_dissolve", sy.reverb(ds, 0.8, 0.3), volume=0.6, max_distance=32)
    # wall breaks: crack, grinding, falling letters
    fall = sy.at(1.6, *[(0.15 + 0.11 * k, sy.pluck(1800 - k * 140, 0.4, 0.8) * (0.5 - k * 0.04)) for k in range(9)])
    br = sy.at(2.0, (0.0, sy.crack(0.6, 5200, 18) * 0.8), (0.0, sy.thump(0.8, 90, 30, 0.6) * 0.7),
               (0.05, sy.rumble(1.2, 70, 6.0) * 0.4), (0.1, fall * 0.5))
    sy.save(pack, "dw_sanct_break", sy.reverb(br, 1.6, 0.4), max_distance=56,
            variants=[sy.reverb(sy.pitch(br, 0.9), 1.6, 0.4)])
    # unwrite: reverse shimmer + an original two-chord "amen" cadence (suspended -> open fifth)
    rev = sy.shimmer(1.4, 2200, 20)[::-1]
    cad = sy.at(3.2, (0.0, chord(196.0, "ah", 1.5, (1.0, 1.335, 1.5, 2.0), attack=0.3, release=0.5) * 0.6),
                (1.25, chord(196.0, "eh", 1.9, (1.0, 1.26, 1.5, 2.0), attack=0.3, release=1.2) * 0.4),
                (1.35, chord(130.8, "ah", 1.9, (1.0, 1.5, 2.0, 3.0), attack=0.25, release=1.2) * 0.6))
    unw = sy.at(4.0, (0.0, rev * 0.45), (0.0, sy.whoosh(1.2, 400, 3200) * 0.25), (0.6, cad))
    sy.save(pack, "dw_sanct_unwrite", sy.reverb(unw, 2.8, 0.45), max_distance=72)
