"""DN03 House of Shifting Sleep -- the impossible dollhouse and everything that falls out of it.

Actors
  dn_house_doll        the dollhouse (hinged facade, lifting gable roof, six contradictory rooms,
                       attic music box, wind-up key, chimney that puffs music notes)
  dn_house_wall        pop-up wall segment, 4 x 5 blocks; dream wallpaper on the front, nightmare
                       wallpaper on the back; kinds 0 plain / 1 door / 2 window / 3 stairs fragment
  dn_house_bed         a four-poster bed that breathes (something peeks from underneath)
  dn_house_clock       a thirteen-hour grandfather clock whose hands disagree
  dn_house_chandelier  a chandelier hanging from a chain that fades into nothing
  dn_house_table       an upside-down floating tea table, tablecloth falling upward
  dn_house_door        a door that hops from wall to wall
"""
import math

import numpy as np

from kit import glyphs, synth as sy, tex
from kit.anim import LIFE, Anim, M, S
from kit.geo import Mat, Model, ring
from kit.parts import sym

from .a_fx_common import particles

IVORY, PEACH, PINK, GOLD, BLUE = "#f6efe0", "#ffd9b8", "#e8b4c8", "#e9cf8a", "#bcd6f0"
INDIGO, MAUVE, BURG, AIVORY, GRAY = "#2a2d52", "#6a4a6e", "#6e2f3a", "#cfc6b0", "#8b8f9a"

# ---- animation lengths (seconds) mirrored in src/spells/dn03_shifting_house.ts
L_LAND, L_OPEN, L_UNFOLD, L_SHIFT, L_FOLD, L_CLOSE, L_VANISH = 1.0, 1.6, 1.0, 0.8, 1.0, 1.0, 0.8
L_WRISE, L_WSETTLE, L_WFOLD = 0.8, 0.5, 0.5
L_FAPPEAR, L_FACT, L_FVANISH = 0.6, 0.8, 0.5

HOUSE_STATES = {0: ["hidden"], 1: ["land"], 2: ["closed"], 3: ["open"], 4: ["opened"], 5: ["unfold"], 6: ["spread"],
                7: ["shiftA"], 8: ["shiftB"], 9: ["fold"], 10: ["close"], 11: ["vanish"]}
WALL_STATES = {0: ["hidden"], 1: ["rise"], 2: ["idle"], 3: ["idle", "slide"], 4: ["idle", "settle"], 5: ["fold"], 6: ["fly"]}
FURN_STATES = {0: ["hidden"], 1: ["appear"], 2: ["idle"], 3: ["idle", "move"], 4: ["act"], 5: ["vanish"]}
DOOR_STATES = {0: ["hidden"], 1: ["hop"], 2: ["pop"]}


# =============================================================================================== painters
def _bm(rows):
    return np.array([[c == "#" for c in r] for r in rows], dtype=bool)


MOTIFS = {k: _bm(v) for k, v in glyphs.DREAM.items()}


def wallpaper(base, ink, motif="damask", cell=10, stripe=None, glow=0.0, ink_glow=0.0, key=None):
    """Repeating wallpaper: damask lattice, pinstripes or half-drop rows of DREAM pictograms."""
    kb, ki = tex.rgb(base), tex.rgb(ink)
    ks = tex.rgb(stripe) if stripe else None

    def fn(ctx):
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, base, 1, glow)
        if ks is not None:
            t[..., :3] = np.where(((ix % cell) < 2)[..., None], ks, t[..., :3])
        if motif == "damask":
            lx, ly = ix % cell, iy % cell
            h = cell // 2
            on = (np.abs(lx - h) + np.abs(ly - h) == h) | ((np.abs(lx - h) + np.abs(ly - h)) <= 1)
        elif motif == "stripe":
            on = (ix % cell) == cell // 2
        elif motif in MOTIFS:
            bm = MOTIFS[motif]
            bh, bw = bm.shape
            row = iy // cell
            ox = (ix + (row % 2) * (cell // 2)) % cell
            oy = iy % cell
            x0, y0 = (cell - bw) // 2, (cell - bh) // 2
            inb = (ox >= x0) & (ox < x0 + bw) & (oy >= y0) & (oy < y0 + bh)
            on = inb & bm[np.clip(oy - y0, 0, bh - 1), np.clip(ox - x0, 0, bw - 1)]
        else:
            on = np.zeros(ix.shape, bool)
        t[..., :3] = np.where(on[..., None], ki, t[..., :3])
        t[..., 4] = np.where(on, ink_glow, t[..., 4])
        seam = (ix % (cell * 3)) == 0
        t[..., :3] = np.where(seam[..., None], t[..., :3] * 0.93, t[..., :3])
        return tex.edge(ctx, tex.grain(ctx, t, 0.03), 0.12)
    return Mat(fn, key or f"dnwp{base}{ink}{motif}{cell}{stripe}{glow}{ink_glow}")


def siding(base, line, board=4, key=None):
    """Painted clapboard of a toy house."""
    kb, kl = tex.rgb(base), tex.rgb(line)

    def fn(ctx):
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, base)
        ly = iy % board
        t[..., :3] = np.where((ly == board - 1)[..., None], kl, t[..., :3])
        t[..., :3] = np.where((ly == 0)[..., None], np.clip(kb * 1.06, 0, 1), t[..., :3])
        return tex.edge(ctx, tex.grain(ctx, t, 0.035), 0.12)
    return Mat(fn, key or f"dnsid{base}{line}{board}")


def door_mat(color, trim=IVORY, knob=GOLD, glow=0.0, key=None):
    """Panelled door with a lit brass knob and keyhole."""
    kc, kt, kk = tex.rgb(color), tex.rgb(trim), tex.rgb(knob)

    def fn(ctx):
        u, v = ctx.U, ctx.V
        t = tex.tile(ctx, color, 1, glow)
        p1 = (np.abs(u - 0.5) < 0.33) & (v > 0.07) & (v < 0.43)
        p2 = (np.abs(u - 0.5) < 0.33) & (v > 0.52) & (v < 0.93)
        i1 = (np.abs(u - 0.5) < 0.24) & (v > 0.12) & (v < 0.38)
        i2 = (np.abs(u - 0.5) < 0.24) & (v > 0.57) & (v < 0.88)
        t[..., :3] = np.where(((p1 & ~i1) | (p2 & ~i2))[..., None], kt, t[..., :3])
        t[..., :3] = np.where((i1 | i2)[..., None], kc * 0.86, t[..., :3])
        kn = (np.abs(u - 0.8) < 0.08) & (np.abs(v - 0.48) < 0.04)
        t[..., :3] = np.where(kn[..., None], kk, t[..., :3])
        t[..., 4] = np.where(kn, 0.8, t[..., 4])
        return tex.edge(ctx, tex.grain(ctx, t, 0.03), 0.18)
    return Mat(fn, key or f"dndoor{color}{trim}{knob}{glow}", directional=True)


def night(top="#2a2d52", bottom="#6a4a6e", moon=True, glow=0.55, key=None):
    """A night sky in a window / painting: gradient, stars, a crescent moon."""
    kt, kb = tex.rgb(top), tex.rgb(bottom)

    def fn(ctx):
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, top, 1, glow * 0.4)
        t[..., :3] = tex.mix(kt, kb, ctx.V[..., None])
        st = tex._hash(ix, iy, 77 + ctx.variant) > 0.93
        t[..., :3] = np.where(st[..., None], tex.rgb("#fff3c4"), t[..., :3])
        t[..., 4] = np.where(st, 1.0, t[..., 4])
        if moon:
            u, v = ctx.U * 2 - 1, ctx.V * 2 - 1
            m = (np.hypot(u - 0.3, v + 0.35) < 0.32) & (np.hypot(u - 0.45, v + 0.42) > 0.26)
            t[..., :3] = np.where(m[..., None], tex.rgb("#fff6dc"), t[..., :3])
            t[..., 4] = np.where(m, 1.0, t[..., 4])
        return t
    return Mat(fn, key or f"dnnight{top}{bottom}{moon}{glow}")


def quilt(colors=(PEACH, PINK, GOLD, IVORY), stitch="#b98a6a", glow=0.12, cell=6, key=None):
    ks = [tex.rgb(c) for c in colors]

    def fn(ctx):
        ix, iy = tex.px(ctx)
        h = tex._hash(ix // cell, iy // cell, 5 + ctx.variant)
        t = tex.tile(ctx, colors[0], 1, glow)
        for k, c in enumerate(ks):
            sel = (h * len(ks)).astype(int) == k
            t[..., :3] = np.where(sel[..., None], c, t[..., :3])
        stc = (((ix % cell) == 0) | ((iy % cell) == 0)) & (((ix + iy) % 2) == 0)
        t[..., :3] = np.where(stc[..., None], tex.rgb(stitch), t[..., :3])
        return tex.grain(ctx, t, 0.03)
    return Mat(fn, key or f"dnquilt{colors}{stitch}{glow}{cell}")


def layers(colors=(PEACH, IVORY, PINK, GOLD, INDIGO), key=None):
    """Cut cross-section of a dollhouse wall (seen on its top edge)."""
    ks = [tex.rgb(c) for c in colors]

    def fn(ctx):
        t = tex.tile(ctx, colors[0])
        band = np.clip((ctx.V * len(ks)).astype(int), 0, len(ks) - 1)
        for k, c in enumerate(ks):
            t[..., :3] = np.where((band == k)[..., None], c, t[..., :3])
        return tex.grain(ctx, t, 0.04)
    return Mat(fn, key or f"dnlayers{colors}")


def clock_face():
    """Thirteen hours (the clock is wrong on purpose) with gilt spandrels."""
    def fn(ctx):
        u, v = ctx.U * 2 - 1, 1 - ctx.V * 2
        r = np.hypot(u, v)
        a = (np.arctan2(u, v) / (2 * math.pi)) % 1.0
        t = tex.tile(ctx, "#f4ecd8", 1, 0.35)
        t[..., :3] = np.where((r > 1.0)[..., None], tex.rgb(GOLD), t[..., :3])
        tick = (r > 0.68) & (r < 0.86) & (np.abs((a * 13) % 1.0 - 0.5) > 0.4)
        t[..., :3] = np.where(tick[..., None], tex.rgb(INDIGO), t[..., :3])
        rim = np.abs(r - 0.93) < 0.06
        t[..., :3] = np.where(rim[..., None], tex.rgb(MAUVE), t[..., :3])
        moon = (np.hypot(u, v + 0.38) < 0.2) & (np.hypot(u + 0.08, v + 0.42) > 0.15)
        t[..., :3] = np.where(moon[..., None], tex.rgb(GOLD), t[..., :3])
        return t
    return Mat(fn, "dnclockface", directional=True)


def mats():
    D = {}
    D["sid"] = siding("#f6e3d3", "#cfae9f")
    D["sid_b"] = siding("#ecc9d3", "#b58d9e")
    D["trim"] = tex.speck(IVORY, 0.03, edge_dark=0.16)
    D["gold"] = tex.metal(GOLD, "#fff3c4", "#9c7a3a", bands=2.0, glow=0.15)
    D["hinge"] = tex.metal("#5a5560", "#b2a9b8", "#2c2a33", bands=1.5)
    D["shingle"] = tex.scales("#b98aa0", MAUVE, "#dcafc2", size=4)
    D["plinth"] = tex.marble("#ece3d3", "#c7b8a2", scale=6)
    D["floor"] = tex.wood("#b88a5e", "#7a5434", vertical=False, plank=4)
    D["plaster"] = tex.speck("#f2e9dc", 0.03, edge_dark=0.08)
    D["wood"] = tex.wood("#8a5a3c", "#5a3622")
    D["wood_l"] = tex.wood("#c79a6c", "#8a6040")
    D["glass"] = tex.glow_flat("#ffe2b0", 0.9, core="#fff8e8")
    D["shutter"] = tex.banded(tex.wood("#9ab8dc", "#7593bd"), "#5d7aa5", every=3)
    D["wp1"] = wallpaper(GOLD, "#fff6d6", "damask", cell=8, glow=0.28, ink_glow=0.7)
    D["wp2"] = wallpaper(BLUE, IVORY, "stripe", cell=6, stripe="#a9c4e2")
    D["wp3"] = wallpaper(PINK, "#fff1f5", "moon", cell=11, ink_glow=0.35)
    D["wp4"] = wallpaper("#3a3d66", "#8b6a90", "door", cell=11, ink_glow=0.25)
    D["wp5"] = wallpaper(INDIGO, AIVORY, "eye", cell=11, ink_glow=0.45)
    D["wp6"] = wallpaper(PEACH, "#d9a85a", "star", cell=12, ink_glow=0.3)
    D["wpf"] = wallpaper("#fbe9dc", PINK, "key", cell=12)
    D["rug"] = wallpaper("#c98a9a", GOLD, "damask", cell=6, ink_glow=0.2)
    D["rug_n"] = wallpaper(BURG, AIVORY, "damask", cell=6)
    D["carpet"] = tex.banded(tex.fabric("#a8485a", None, 0.06), GOLD, every=5)
    D["porc"] = tex.porcelain(IVORY, "#ddd0bb", crack=0.2, gilt=GOLD)
    D["porc_p"] = tex.porcelain("#f3c9d6", "#d6a3b4", crack=0.2, gilt=GOLD)
    D["quilt"] = quilt()
    D["quilt_n"] = quilt((MAUVE, INDIGO, BURG, AIVORY), stitch="#cfc6b0", glow=0.05)
    D["fabric"] = tex.fabric("#fff4ec", PINK, 0.05, stripe_w=3)
    D["lace"] = tex.fabric("#fbf6ee", None, 0.1, fringe=True)
    D["flame"] = tex.shaped(tex.m_leaf(), "#fffbe0", "#ffb860", glow=1.0, var=0, key="dnflame")
    D["flame_n"] = tex.shaped(tex.m_leaf(), "#e6dcff", "#8a6ad6", glow=1.0, var=0, key="dnflamen")
    D["night"] = night()
    D["layers"] = layers()
    D["dark"] = tex.speck("#1c1d33", 0.05, edge_dark=0.0)
    D["lampshade"] = tex.glow_flat("#ffd59a", 0.9, core="#fff4dc")
    D["silver"] = tex.metal("#c9cdd6", "#ffffff", "#7a7f8c", bands=3.0)
    return D


# =============================================================================================== the dollhouse
def house_model(D):
    m = Model("dn_house_doll", density=1.0, bounds=(20, 22, (0, 7, 0)))
    root = m.bone("root")
    body = m.bone("body", root)
    body.locator("core", (0, 34, 0))
    # plinth with a gold band and a front step
    body.cube((-31, 0, -21), (62, 3, 42), D["plinth"])
    body.cube((-31.5, 2.3, -21.5), (63, 0.9, 43), D["gold"])
    body.cube((8, 3, -22.5), (12, 1.2, 3), D["plinth"], variant=1)
    # shell: back, sides, floors, centre divider
    body.cube((-28, 3, 16), (56, 62, 2), D["sid_b"], mats={"north": D["plaster"]})
    for sx in (-1, 1):
        x0 = 26 if sx > 0 else -28
        body.cube((x0, 3, -16), (2, 62, 32), D["sid_b"], variant=1,
                  mats={("west" if sx > 0 else "east"): D["plaster"]})
        body.cube((sx * 28.6 - 1.25, 3, -18.9), (2.5, 62, 3), D["trim"], variant=2)     # corner pilaster
        for y in (12, 34, 56):                                                          # hinge pins
            body.box((sx * 29.2, y, -18.9), (1.3, 7, 1.3), D["hinge"])
        # painted side windows with sills
        for f in range(3):
            cy = 14 + 20 * f
            body.box((sx * 28.25, cy, 0), (0.5, 11, 9), D["trim"])
            body.plane("x", (sx * 28.55, cy, 0), 7, 8, D["glass"], variant=f)
            body.box((sx * 28.8, cy - 6, 0), (1.2, 1, 10), D["trim"], variant=1)
    for y in (3, 23, 43, 63):
        body.cube((-26, y, -16), (52, 2, 32), D["plaster"], mats={"up": D["floor"], "north": D["gold"]})
    body.cube((-1, 5, -16), (2, 58, 32), D["plaster"], variant=2)
    body.cube((-28.5, 65, -17), (57, 1.2, 35), D["trim"])
    # attic: a music box keeps the house's tune
    body.box((0, 66.6, 3), (24, 2.4, 14), D["wood"])
    body.box((0, 68.2, -2.5), (18, 0.8, 3), D["silver"])
    cyl = m.bone("attic_cyl", body, pivot=(0, 71, 4))
    cyl.box((0, 71, 4), (17, 4.4, 4.4), D["gold"])
    for k in range(7):
        cyl.box((-7 + k * 2.3, 73.4, 4 + (k % 3 - 1) * 1.1), (0.6, 0.6, 0.6), D["silver"])
    body.box((-10, 71, 4), (1.2, 6, 6), D["gold"], variant=1)
    body.box((10, 71, 4), (1.2, 6, 6), D["gold"], variant=1)
    body.locator("attic", (0, 74, 0))
    # the wind-up key in the back
    key = m.bone("key", body, pivot=(0, 40, 18))
    key.box((0, 40, 21.5), (2.6, 2.6, 7), D["gold"])
    key.box((0, 40, 25.2), (4.5, 4.5, 1.4), D["gold"], variant=1)
    ring(key, (0, 47, 25.2), 4.2, 10, (3.0, 1.5, 1.4), D["gold"], axis="z")
    ring(key, (0, 33, 25.2), 4.2, 10, (3.0, 1.5, 1.4), D["gold"], axis="z")

    _rooms(m, body, D)

    # facade halves: hinged on the outer edges, meeting in the middle with a gold latch
    shutters = []
    for s, sx in (("r", 1), ("l", -1)):
        fac = m.bone(f"facade_{s}", body, pivot=(sx * 28, 0, -18))
        x0 = 0 if sx > 0 else -28
        fac.cube((x0, 3, -18), (28, 62, 2), D["sid"], mats={"south": D["wpf"]})
        fac.cube((x0 - 0.2, 22.3, -18.8), (28.4, 1.6, 0.8), D["trim"])
        fac.cube((x0 - 0.2, 42.3, -18.8), (28.4, 1.6, 0.8), D["trim"], variant=1)
        fac.cube((x0 - 0.4, 62.6, -19.4), (28.8, 2.6, 1.4), D["gold"])
        fac.cube((x0 - 0.4, 3, -19.0), (28.8, 1.6, 1.0), D["trim"], variant=2)
        for y in (12, 34, 56):
            fac.box((sx * 27.4, y, -18.6), (2.6, 5.5, 1.4), D["hinge"])
            fac.box((sx * 25.5, y, -19.4), (3.2, 1.6, 0.4), D["hinge"], variant=1)
        fac.box((sx * 0.3, 34, -18.9), (0.6, 62, 0.4), D["gold"], variant=1)      # seam
        if sx > 0:
            fac.box((1.2, 34, -19.4), (2.4, 3, 1), D["gold"])                      # latch
        for f in range(3):
            cx, cy = sx * 14, 14 + 20 * f
            if f == 0 and sx > 0:     # front door with fanlight and porch lamp
                fac.box((cx, 11.5, -18.5), (11, 15, 1.2), door_mat(PINK, IVORY, GOLD))
                fac.box((cx, 19.8, -18.6), (13, 2, 1.6), D["trim"])
                fac.plane("z", (cx, 21.8, -19.0), 8, 3, tex.shaped(lambda u, v: ((np.hypot(u, v + 1) < 1.8)).astype(float),
                                                                   "#fff4d0", GOLD, glow=0.9, var=0, key="dnfan"))
                fac.box((cx + 8, 16, -19.4), (1.6, 2.4, 1.6), D["lampshade"])
                continue
            fac.box((cx, cy, -18.6), (12.5, 12.5, 1.2), D["trim"])
            fac.plane("z", (cx, cy, -19.25), 9.5, 9.5, D["glass"], variant=f)
            fac.box((cx, cy, -19.4), (0.8, 9.5, 0.4), D["trim"], variant=1)
            fac.box((cx, cy, -19.4), (9.5, 0.8, 0.4), D["trim"], variant=1)
            fac.box((cx, cy - 7, -19.6), (14, 1.4, 2.2), D["trim"], variant=2)
            fac.box((cx, cy - 8.4, -20.0), (11, 2, 2.4), D["wood_l"])
            fac.plane("z", (cx, cy - 6.8, -20.6), 11, 2.6, tex.foliage("#7aa36a", "#a8cc8a", holes=0.2, flowers=PINK),
                      variant=f)
            for side, hx, ang in (("a", cx - 6.2, 1), ("b", cx + 6.2, -1)):
                sh = m.bone(f"shut_{s}{f}{side}", fac.name, pivot=(hx, cy, -19.5))
                sh.cube((hx if ang > 0 else hx - 6.2, cy - 6.2, -19.9), (6.2, 12.4, 0.6), D["shutter"],
                        variant=(f + (1 if ang > 0 else 0)) % 3)
                shutters.append((sh.name, ang))
    # gable roof halves
    L = math.hypot(31, 24)
    ang = math.degrees(math.atan2(24, 31))
    for s, sx in (("r", 1), ("l", -1)):
        rf = m.bone(f"roof_{s}", body, pivot=(sx * 31, 65, 0))
        rf.box((sx * 15.5, 77.4, 0), (L + 3, 3, 43), D["shingle"], rot=(0, 0, -sx * ang), pivot=(sx * 15.5, 77.4, 0),
               mats={"down": D["plaster"], "north": D["trim"], "south": D["trim"]})
        rf.box((sx * 15.5, 77.0, -21.9), (L + 3, 1.6, 1.0), D["trim"], rot=(0, 0, -sx * ang), pivot=(sx * 15.5, 77.0, -21.9))
        for k in range(6):
            yb = 65 + 4 * k
            xm = 31 * (1 - (yb + 2 - 65) / 24) - 1.5
            if xm <= 0.5:
                continue
            x0 = 0 if sx > 0 else -xm
            for zz in (-18, 16.6):
                rf.cube((x0, yb, zz), (xm, 4, 1.4), D["sid_b"], variant=k % 2)
        mask = tex.m_star(5, 0.45) if sx > 0 else tex.m_crescent(0.35)
        rf.plane("z", (sx * 8.5, 71.5, -18.4), 6.5, 6.5, tex.shaped(mask, "#fff3c4", GOLD, glow=1.0, var=0,
                                                                     key=f"dngable{s}"))
        if sx > 0:
            rf.box((0, 89.4, 0), (3.2, 2.2, 44), D["gold"])
            rf.box((17, 82, 7), (5, 12, 5), tex.plates("#c08a90", "#6e2f3a", cell=(4, 3)))
            rf.box((17, 88.5, 7), (6.4, 1.6, 6.4), D["trim"])
            rf.locator("chimney", (17, 90, 7))
        else:
            rf.plane("z", (0, 94, -20.5), 6, 6, tex.shaped(tex.m_crescent(0.4), "#fff3c4", GOLD, glow=1.0, var=0,
                                                         key="dnfinial"))
            rf.box((0, 90.5, -20.5), (0.8, 2.5, 0.8), D["gold"])
    return m, shutters


def _room_paper(b, x0, x1, y0, wp):
    cx, w = (x0 + x1) / 2, x1 - x0
    b.plane("z", (cx, y0 + 9, 15.9), w, 18, wp)
    b.plane("x", (x0 + 0.1, y0 + 9, 0), 32, 18, wp, variant=1)
    b.plane("x", (x1 - 0.1, y0 + 9, 0), 32, 18, wp, variant=1)


def _rooms(m, body, D):
    # --- 1: the peaceful golden bedroom (ground floor, left)
    r1 = m.bone("room1", body)
    _room_paper(r1, -26, -1, 5, D["wp1"])
    r1.plane("y", (-13, 5.1, 2), 18, 20, D["rug"])
    r1.cube((-21, 6.5, 1), (14, 3, 14), D["wood_l"])
    for x in (-20.5, -7.5):
        for z in (1.5, 14.5):
            r1.box((x, 5.8, z), (1.5, 1.6, 1.5), D["gold"])
    r1.cube((-20.5, 9.5, 1.5), (13, 1.6, 12.8), D["trim"])
    r1.cube((-21.5, 5, 14.2), (15, 13, 1.4), D["gold"], variant=1)
    r1.box((-14, 18.6, 14.9), (9, 1.4, 1.4), D["gold"])
    r1.plane("z", (-14, 15, 14.1), 5, 5, tex.shaped(tex.m_crescent(0.4), "#fffbe8", GOLD, glow=1.0, var=0, key="dnbedmoon"))
    r1.cube((-21.5, 5, 0.2), (15, 7.5, 1.2), D["gold"], variant=2)
    r1.box((-17, 11.9, 12.3), (5, 1.8, 3), D["porc_p"])
    r1.box((-11, 11.9, 12.3), (5, 1.8, 3), D["porc"])
    q = m.bone("r1_quilt", r1, pivot=(-14, 10.6, 6))
    q.cube((-21.2, 10.6, 0.5), (14.4, 1.6, 10.5), D["quilt"])
    q.cube((-21.2, 7.5, 0.2), (14.4, 4, 0.5), D["quilt"], variant=1)
    r1.box((-24, 7.5, 12), (3.4, 5, 4), D["wood_l"], variant=1)
    lamp = m.bone("r1_lamp", r1, pivot=(-24, 10, 12))
    lamp.box((-24, 11, 12), (0.8, 2, 0.8), D["gold"])
    lamp.box((-24, 13.4, 12), (3.2, 2.6, 3.2), D["lampshade"])
    r1.box((-14, 20.2, 15.6), (7, 4.4, 0.4), D["gold"], variant=2)
    r1.plane("z", (-14, 20.2, 15.3), 5.6, 3.2, night("#f2c38a", "#ffe9c2", moon=True, glow=0.6, key="dnsunpic"))

    # --- 2: the room with a door on every wall (ground floor, right) -- the whole room turns
    r2 = m.bone("room2", body)
    _room_paper(r2, 1, 26, 5, D["wp2"])
    rd = m.bone("r2_doors", r2, pivot=(13.5, 14, 0))
    doors = [("r2_d1", (4.5, 5, 15.2), (7, 13, 0.6), (4.5, 5, 15.5), PINK),
             ("r2_d2", (15.5, 5, 15.2), (7, 13, 0.6), (22.5, 5, 15.5), GOLD),
             ("r2_d3", (1.1, 5, -6), (0.6, 13, 7), (1.4, 5, -6), "#7da3cf"),
             ("r2_d4", (25.3, 5, 3), (0.6, 13, 7), (25.6, 5, 10), BURG),
             ("r2_d5", (9, 22.3, -2), (7, 0.6, 7), (9, 22.6, 1.5), IVORY),
             ("r2_d6", (14, 5, -12), (7, 0.6, 7), (14, 5.3, -8.5), "#b88a5e")]
    for name, o, size, piv, col in doors:
        db = m.bone(name, rd, pivot=piv)
        db.cube(o, size, door_mat(col, IVORY, GOLD))
        fo = tuple(o[i] - (0.8 if size[i] > 1 else 0.0) for i in range(3))
        fs = tuple(size[i] + 1.6 if size[i] > 1 else 0.3 for i in range(3))
        if name in ("r2_d1", "r2_d2"):
            fo = (fo[0], fo[1], 15.75)
        elif name == "r2_d3":
            fo = (0.95, fo[1], fo[2])
        elif name == "r2_d4":
            fo = (25.75, fo[1], fo[2])
        elif name == "r2_d5":
            fo = (fo[0], 22.8, fo[2])
        else:
            fo = (fo[0], 4.95, fo[2])
        rd.cube(fo, fs, D["trim"], variant=len(name) % 3)
    rd.box((13.5, 21.8, 1.5), (1, 1, 1), D["gold"])
    rd.box((13.5, 20.6, 1.5), (2.6, 1.4, 2.6), D["lampshade"])

    # --- 3: the staircase climbing into the ceiling (middle floor, left)
    r3 = m.bone("room3", body)
    _room_paper(r3, -26, -1, 25, D["wp3"])
    st = m.bone("r3_stairs", r3, pivot=(-13, 25, 7))
    for k in range(8):
        h = min((k + 1) * 2.6, 18)
        sb = m.bone(f"r3_s{k + 1}", st, pivot=(-24 + k * 2.8, 25, 7))
        sb.cube((-25 + k * 2.8, 25, 2), (2.8, h, 10), D["wood_l"], variant=k % 3,
                mats={"up": D["carpet"], "north": D["trim"] if k % 2 else D["wood"]})
    r3.box((-13, 37, 1.6), (25, 0.9, 0.9), D["gold"], rot=(0, 0, 42.9), pivot=(-13, 37, 1.6))
    for k in (0, 3, 6):
        r3.box((-23.6 + k * 2.8, 25 + (k + 1) * 2.6 + 3, 1.6), (0.7, 6, 0.7), D["gold"], variant=1)
    r3.plane("y", (-4, 42.9, 7), 6, 10, D["dark"])        # the hole the stairs disappear into
    r3.box((-3.3, 46, 7), (4.2, 2, 10), D["wood_l"], mats={"up": D["carpet"]})  # ...and come out upstairs
    r3.box((-20, 38, 15.6), (1.2, 2, 1.2), D["gold"])
    r3.plane("z", (-20, 40.2, 15.5), 1.6, 2.4, D["flame"])

    # --- 4: the corridor that loops (middle floor, right)
    r4 = m.bone("room4", body)
    _room_paper(r4, 1, 26, 25, D["wp4"])
    for k in range(5):
        z = -13 + k * 6.6
        w, h = 22 - k * 3.6, 17 - k * 2.6
        fb = m.bone(f"r4_f{k + 1}", r4, pivot=(13.5, 25 + h / 2, z))
        mat = D["gold"] if k % 2 == 0 else D["trim"]
        fb.box((13.5 - w / 2, 25 + h / 2, z), (1.4, h, 1.2), mat)
        fb.box((13.5 + w / 2, 25 + h / 2, z), (1.4, h, 1.2), mat, variant=1)
        fb.box((13.5, 25 + h, z), (w + 1.4, 1.4, 1.2), mat, variant=2)
        r4.plane("y", (13.5, 25.12 + k * 0.01, z + 3.3), max(2.0, w * 0.45), 6.6, D["carpet"], variant=k % 3)
    r4.plane("z", (13.5, 28.5, 15.7), 4, 7, door_mat("#fff3c4", GOLD, "#ffffff", glow=0.9, key="dnglowdoor"))

    # --- 5: the upside-down bedroom (top floor, left) in nightmare colours
    r5 = m.bone("room5", body)
    _room_paper(r5, -26, -1, 45, D["wp5"])
    r5.plane("y", (-13, 62.9, 2), 18, 20, D["rug_n"])
    rr = m.bone("r5_room", r5, pivot=(-13.5, 54, 2))
    rr.cube((-21, 59.5, 1), (14, 2.6, 14), D["wood"])
    for x in (-20.5, -7.5):
        for z in (1.5, 14.5):
            rr.box((x, 62.2, z), (1.4, 1.6, 1.4), D["gold"])
    rr.cube((-20.5, 58, 1.5), (13, 1.6, 12.8), D["trim"], variant=1)
    rr.cube((-21.2, 56.6, 0.5), (14.4, 1.5, 10.5), D["quilt_n"])
    rr.cube((-21.2, 56.6, 0.2), (14.4, 4, 0.5), D["quilt_n"], variant=1)
    rr.cube((-21.5, 50, 14.2), (15, 13, 1.4), D["wood"], variant=1)
    rr.box((-17, 56.9, 12.3), (5, 1.8, 3), D["porc"])
    rr.box((-8, 56.2, -8), (7, 0.8, 6), D["wood"], variant=2)       # table on the ceiling
    for x in (-11, -5):
        for z in (-10.5, -5.5):
            rr.box((x, 59.8, z), (0.8, 6, 0.8), D["wood"])
    rr.box((-8, 55.2, -8), (1.8, 1.4, 1.8), D["porc_p"])
    rr.box((-18, 57.4, -10), (4, 0.6, 4), D["wood"], variant=1)       # chair on the ceiling
    for x in (-19.6, -16.4):
        for z in (-11.6, -8.4):
            rr.box((x, 60.2, z), (0.6, 5, 0.6), D["wood"])
    rr.box((-18, 54.4, -11.8), (4, 5.6, 0.6), D["wood"], variant=2)
    rr.box((-13, 46.4, -6), (3, 2.8, 3), D["gold"])                  # a chandelier standing on the floor
    ring(rr, (-13, 48.2, -6), 3.6, 6, (1.0, 3.6, 0.8), D["gold"])
    fl = m.bone("r5_flames", rr, pivot=(-13, 48, -6))
    for k in range(6):
        a = math.radians(k * 60 + 30)
        px, pz = -13 + math.cos(a) * 5.4, -6 + math.sin(a) * 5.4
        fl.box((px, 49.3, pz), (0.9, 2.2, 0.9), D["trim"])
        fl.plane("z", (px, 47.2, pz), 1.4, 2.4, D["flame_n"], rot=(0, 0, 180), pivot=(px, 47.2, pz))

    # --- 6: the room with an impossible internal scale (top floor, right)
    r6 = m.bone("room6", body)
    _room_paper(r6, 1, 26, 45, D["wp6"])
    r6.box((16, 46.0, 4), (24, 1.4, 22), D["porc"], variant=1)         # saucer pushing through the walls
    cup = m.bone("r6_cup", r6, pivot=(17, 47, 4), rot=(0, 0, 8))
    cup.box((17, 48.2, 4), (9, 2.4, 9), D["porc"])
    ring(cup, (17, 53.5, 4), 6.4, 12, (3.6, 1.4, 11), D["porc_p"])
    ring(cup, (17, 59.3, 4), 6.8, 12, (3.9, 1.6, 1.2), D["gold"], variant=1)
    cup.plane("y", (17, 57.5, 4), 12, 12, tex.shaped(tex.m_disc(), "#c98a4a", "#e9cf8a", glow=0.5, var=0, key="dntea"))
    ring(cup, (24.6, 53.5, 4), 3.4, 6, (2.4, 1.4, 1.4), D["porc"], axis="z", start=-90, sweep=180)
    cup.locator("steam", (18, 61, 4))
    r6.box((4.5, 54, 13.5), (2, 18, 2), D["gold"], rot=(0, 0, -12), pivot=(4.5, 54, 13.5))   # a giant key leaning
    ring(r6, (6.4, 63.5, 13.5), 2.6, 8, (2.0, 1.2, 1.4), D["gold"], axis="z")
    mini = m.bone("r6_mini", r6, pivot=(6.5, 45, -10))                   # the whole house, in miniature
    mini.box((6.5, 45.5, -10), (7, 1, 6), D["plinth"])
    mini.box((6.5, 48.5, -10), (5.6, 5, 4.4), D["sid"])
    mini.box((4.9, 52.2, -10), (4.2, 0.8, 5.6), D["shingle"], rot=(0, 0, 38), pivot=(4.9, 52.2, -10))
    mini.box((8.1, 52.2, -10), (4.2, 0.8, 5.6), D["shingle"], rot=(0, 0, -38), pivot=(8.1, 52.2, -10))
    mini.plane("z", (5.3, 48.9, -12.25), 1.2, 1.2, D["glass"])
    mini.plane("z", (7.7, 48.9, -12.25), 1.2, 1.2, D["glass"])
    mini.plane("z", (6.5, 47, -12.25), 1.2, 2, door_mat(PINK, IVORY, GOLD))


# pose presets: facade yaw (right side; mirrored), roof rotation / position, shutter swing
CLOSED = dict(fac=0.0, rz=0.0, rp=(0.0, 0.0, 0.0), sh=0.0)
OPENED = dict(fac=-112.0, rz=-100.0, rp=(2.0, 3.0, 0.0), sh=165.0)
SPREAD = dict(fac=-172.0, rz=-150.0, rp=(5.0, 0.0, 0.0), sh=170.0)


def _house_pose(a, shutters, keys):
    """keys: {t: preset}.  Writes facade, roof and shutter channels."""
    ts = sorted(keys)
    sym(a, "facade_{s}", rot={t: (0, keys[t]["fac"], 0) for t in ts})
    sym(a, "roof_{s}", rot={t: (0, 0, keys[t]["rz"]) for t in ts}, pos={t: keys[t]["rp"] for t in ts})
    for name, sg in shutters:
        a.rot(name, {t: (0, sg * keys[t]["sh"], 0) for t in ts})


def _mixp(p, q, f):
    return dict(fac=p["fac"] + (q["fac"] - p["fac"]) * f, rz=p["rz"] + (q["rz"] - p["rz"]) * f,
                rp=tuple(p["rp"][i] + (q["rp"][i] - p["rp"][i]) * f for i in range(3)), sh=p["sh"] + (q["sh"] - p["sh"]) * f)


def spin(rate):
    return M(f"q.life_time*{rate}", lambda t: t * rate)


def house_anims(shutters):
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    life = Anim("life", loop=True)                     # always: the rooms are alive
    life.scl("body", (LIFE(0.01, 3.4, base=1.0), LIFE(0.012, 3.4, 0.25, base=1.0), LIFE(0.01, 3.4, base=1.0)))
    life.scl("r1_quilt", (1, LIFE(0.35, 3.0, base=1.0), 1))
    life.scl("r1_lamp", LIFE(0.06, 0.37, base=1.0))
    for k, (ax, amp) in enumerate([(1, 14), (1, -14), (1, 12), (1, -12), (2, -16), (2, 16)]):
        v = [0, 0, 0]
        v[ax] = LIFE(amp, 2.3 + k * 0.17, k * 0.21, base=amp * 0.6)
        life.rot(f"r2_d{k + 1}", tuple(v))
    for k in range(8):
        life.pos(f"r3_s{k + 1}", (0, LIFE(0.7, 1.8, -k * 0.11), 0))
    for k in range(5):
        life.rot(f"r4_f{k + 1}", (0, 0, LIFE(6 + k * 4, 4.0, k * 0.12)))
    life.rot("r5_room", (0, 0, LIFE(3, 6.0)))
    life.scl("r5_flames", LIFE(0.1, 0.31, base=1.0))
    life.pos("r6_mini", (0, LIFE(1.4, 2.6, base=1.4), 0))
    life.rot("r6_mini", (0, spin(25), LIFE(6, 2.6, 0.25)))
    life.rot("r6_cup", (0, 0, LIFE(2, 5.0)))
    life.rot("attic_cyl", (spin(140), 0, 0))
    life.rot("key", (0, 0, spin(-30)))
    A.append(life)

    land = Anim("land", length=L_LAND, loop="hold")
    land.pos("root", {0: (0, 150, 0), 0.25: (0, 100, 0), 0.45: (0, 0, 0), 0.6: (0, 7, 0), 0.75: (0, 0, 0),
                      0.87: (0, 1.5, 0), 1.0: (0, 0, 0)})
    land.scl("root", {0: 0.25, 0.42: (1.0, 1.0, 1.0), 0.5: (1.14, 0.82, 1.14), 0.64: (0.95, 1.07, 0.95),
                      0.8: (1.02, 0.98, 1.02), 1.0: (1, 1, 1)})
    land.rot("root", {0: (0, -200, 0), 0.45: (0, 0, 0), 1.0: (0, 0, 0)})
    sym(land, "facade_{s}", rot={0: (0, 0, 0), 0.5: (0, -6, 0), 0.62: (0, 3, 0), 0.8: (0, 0, 0)})
    A.append(land)

    closed = Anim("closed", loop=True)
    for k, (name, sg) in enumerate(shutters):
        closed.rot(name, (0, sg * LIFE(3, 1.3, k * 0.37, base=3), 0))
    A.append(closed)

    op = Anim("open", length=L_OPEN, loop="hold")
    over = dict(OPENED, fac=-121.0, rz=-108.0, rp=(2.0, 5.0, 0.0), sh=175.0)
    _house_pose(op, shutters, {0: CLOSED, 0.12: dict(CLOSED, sh=40.0), 0.3: dict(CLOSED, sh=175.0),
                               0.5: dict(CLOSED, fac=4.0, sh=165.0), 1.1: dict(over, rz=-40.0, rp=(1.0, 6.0, 0.0)),
                               1.35: over, 1.6: OPENED})
    op.rot("key", {0: (0, 0, 0), 0.5: (0, 0, -300), 0.8: (0, 0, -380), 1.6: (0, 0, -400)})
    op.scl("r6_mini", {0: 0.0, 0.9: 0.0, 1.2: 1.4, 1.6: 1.0})
    op.scl("r3_stairs", {0: (1, 0.2, 1), 0.8: (1, 0.2, 1), 1.3: (1, 1.1, 1), 1.6: (1, 1, 1)})
    op.rot("body", {0: (0, 0, 0), 0.5: (3, 0, 0), 0.9: (-2, 0, 0), 1.3: (0, 0, 0)})
    A.append(op)

    opened = Anim("opened", loop=True, length=1.5)
    sym(opened, "facade_{s}", rot=(0, LIFE(3, 3.1, base=OPENED["fac"]), 0))
    sym(opened, "roof_{s}", rot=(0, 0, LIFE(2.5, 2.7, base=OPENED["rz"])), pos=(2, LIFE(0.8, 2.7, 0.2, base=3), 0))
    for name, sg in shutters:
        opened.rot(name, (0, sg * OPENED["sh"], 0))
    opened.particle(0.3, "note", "chimney")
    A.append(opened)

    unfold = Anim("unfold", length=L_UNFOLD, loop="hold")
    _house_pose(unfold, shutters, {0: OPENED, 0.4: _mixp(OPENED, SPREAD, 0.4), 0.8: dict(SPREAD, fac=-180.0, rz=-158.0),
                                   1.0: SPREAD})
    unfold.rot("body", {0: (0, 0, 0), 0.3: (-6, 0, 0), 0.7: (4, 0, 0), 1.0: (0, 0, 0)})
    unfold.scl("body", {0: 1.0, 0.3: (1.08, 0.9, 1.08), 0.7: (0.96, 1.05, 0.96), 1.0: 1.0})
    unfold.particle(0.4, "scrap", "core")
    A.append(unfold)

    spread = Anim("spread", loop=True, length=1.5)
    sym(spread, "facade_{s}", rot=(0, LIFE(4, 3.3, base=SPREAD["fac"]), 0))
    sym(spread, "roof_{s}", rot=(0, 0, LIFE(4, 2.9, base=SPREAD["rz"])), pos=(5, LIFE(1.0, 2.9, 0.2, base=0), 0))
    for name, sg in shutters:
        spread.rot(name, (0, sg * SPREAD["sh"], 0))
    spread.rot("root", (LIFE(3, 5.0), 0, LIFE(4, 6.2, 0.3)))
    spread.particle(0.3, "note", "chimney")
    A.append(spread)

    # two alternating shifts: rooms change their orientation and change back
    for nm, a0, a1 in (("shiftA", 0, 180), ("shiftB", 180, 0)):
        sh = Anim(nm, length=L_SHIFT, loop="hold")
        jolt = dict(SPREAD, fac=-150.0, rz=-125.0)
        _house_pose(sh, shutters, {0: SPREAD, 0.18: jolt, 0.5: dict(SPREAD, fac=-180.0), 0.8: SPREAD})
        sh.rot("body", {0: (0, 0, 0), 0.15: (0, 0, 7), 0.4: (0, 0, -5), 0.6: (0, 0, 2), 0.8: (0, 0, 0)})
        sh.rot("room5", {0: (a0, 0, 0), 0.65: (a1, 0, 0), 0.8: (a1, 0, 0)})
        sh.rot("r2_doors", {0: (0, a0, 0), 0.65: (0, a1, 0), 0.8: (0, a1, 0)})
        sh.rot("room6", {0: (0, 0, a0 / 2), 0.65: (0, 0, a1 / 2), 0.8: (0, 0, a1 / 2)})
        sh.scl("room4", {0: 1.0, 0.3: (1.0, 1.0, 0.4), 0.6: (1.0, 1.0, 1.15), 0.8: 1.0})
        sh.particle(0.1, "scrap", "core")
        A.append(sh)

    fold = Anim("fold", length=L_FOLD, loop="hold")
    _house_pose(fold, shutters, {0: SPREAD, 0.6: _mixp(SPREAD, OPENED, 0.8), 1.0: OPENED})
    fold.rot("body", {0: (0, 0, 0), 0.4: (5, 0, 0), 1.0: (0, 0, 0)})
    A.append(fold)

    close = Anim("close", length=L_CLOSE, loop="hold")
    _house_pose(close, shutters, {0: OPENED, 0.35: dict(OPENED, rz=-30.0, rp=(1.0, 5.0, 0.0)),
                                  0.62: dict(CLOSED, fac=5.0, sh=120.0), 0.72: dict(CLOSED, fac=-2.0, sh=30.0),
                                  0.85: CLOSED, 1.0: CLOSED})
    close.scl("root", {0: 1.0, 0.6: 1.0, 0.68: (1.06, 0.92, 1.06), 0.85: (0.98, 1.02, 0.98), 1.0: 1.0})
    close.rot("key", {0: (0, 0, 0), 1.0: (0, 0, 240)})
    A.append(close)

    vanish = Anim("vanish", length=L_VANISH, loop="hold")
    vanish.scl("root", {0: 1.0, 0.18: (1.08, 0.9, 1.08), 0.5: 0.16, 0.66: 0.12, 0.8: 0.0})
    vanish.pos("root", {0: (0, 0, 0), 0.25: (0, 6, 0), 0.5: (0, 40, 0), 0.8: (0, 10, 0)})
    vanish.rot("root", {0: (0, 0, 0), 0.8: (0, 540, 0)})
    A.append(vanish)
    return A


# =============================================================================================== wall segments
WALL_PAPERS = [  # (dream front, nightmare back)
    (wallpaper(PEACH, "#f3b897", "damask", cell=10), wallpaper(INDIGO, AIVORY, "eye", cell=12, ink_glow=0.4)),
    (wallpaper(PINK, "#fff1f5", "stripe", cell=7, stripe="#dca2b8"), wallpaper(BURG, "#b0707a", "stripe", cell=7, stripe="#5a2530")),
    (wallpaper(BLUE, IVORY, "moon", cell=12, ink_glow=0.3), wallpaper(MAUVE, AIVORY, "door", cell=12, ink_glow=0.25)),
    (wallpaper(GOLD, "#fff6d6", "star", cell=12, glow=0.1, ink_glow=0.5), wallpaper("#3c3f5c", GRAY, "damask", cell=10)),
]


def wall_model(kind, D):
    names = ["plain", "door", "window", "stairs"]
    m = Model(f"dn_house_wall_{names[kind]}", density=1.0, bounds=(6, 7, (0, 2.5, 0)))
    front, back = WALL_PAPERS[kind]
    pm = dict(mats={"north": front, "south": back, "up": D["layers"]})
    root = m.bone("root")
    panel = m.bone("panel", root)
    panel.locator("mid", (0, 40, 0))
    for sx in (-1, 1):                         # posts with gilt finials
        w = 6.0 if sx < 0 else 5.6
        panel.box((sx * 32, 40, 0), (w, 80, w + 1), D["trim"])
        panel.box((sx * 32, 81, 0), (w + 1, 2, w + 2), D["gold"])
        panel.box((sx * 32, 83.6, 0), (3.4, 3.4, 3.4), D["gold"], variant=1)
    if kind == 1:
        pieces = [((-29, 0), (19, 76)), ((10, 0), (19, 76)), ((-10, 42), (20, 34))]
    elif kind == 2:
        pieces = [((-29, 0), (58, 30)), ((-29, 62), (58, 14)), ((-29, 30), (15, 32)), ((14, 30), (15, 32))]
    else:
        pieces = [((-29, 0), (58, 76))]
    for k, ((x0, y0), (w, h)) in enumerate(pieces):
        panel.cube((x0, y0, -2), (w, h, 4), D["trim"], variant=k % 3, **pm)
    # skirting, dado rail on both faces
    for zf, zz in ((-2.6, -1), (2.0, 1)):
        for k, ((x0, y0), (w, h)) in enumerate(pieces):
            if y0 == 0:
                panel.cube((x0, 0, zf), (w, 5, 0.6), D["wood"], variant=k % 3)
            if y0 <= 29 and y0 + h >= 31:
                panel.cube((x0, 29.4, zf), (w, 1.2, 0.6), D["gold"], variant=k % 2)
    crown = m.bone("crown", root, pivot=(0, 76, 0))
    crown.cube((-30, 76, -3), (60, 3, 6), D["trim"], mats={"up": D["layers"]})
    crown.cube((-30.4, 78.2, -3.4), (60.8, 1.0, 6.8), D["gold"])

    a = m.bone("deco_a", root, pivot=(0, 62, -2.6))
    b = m.bone("deco_b", root, pivot=(-20, 44, -3))
    if kind == 0:
        a.box((0, 50, -2.9), (17, 13, 1), D["gold"])
        a.plane("z", (0, 50, -3.45), 14, 10, night(key="dnwallpic"))
        a.box((-4, 58, -2.8), (8.6, 0.5, 0.5), D["gold"], rot=(0, 0, -26), pivot=(-4, 58, -2.8), variant=1)
        a.box((4, 58, -2.8), (8.6, 0.5, 0.5), D["gold"], rot=(0, 0, 26), pivot=(4, 58, -2.8), variant=1)
        panel.plane("z", (0, 48, 2.7), 13, 15, tex.eye_mat(MAUVE, AIVORY, INDIGO, "#4a3a58", glow=0.8, open_amt=0.55))
        panel.box((0, 48, 2.3), (16, 18, 0.6), D["silver"])
        b.box((-20, 44, -3.2), (1.6, 3, 2.2), D["gold"])
        b.box((-20, 47, -3.8), (1.2, 3.4, 1.2), D["trim"])
        b.plane("z", (-20, 50.4, -3.8), 2.2, 3.4, D["flame"])
        b.plane("x", (-20, 50.4, -3.8), 2.2, 3.4, D["flame"])
    elif kind == 1:
        for sx in (-1, 1):
            panel.box((sx * 11, 21, 0), (2.2, 42, 5.2), D["trim"], variant=2)
        panel.box((0, 43.2, 0), (24.4, 2.4, 5.6), D["gold"])
        a.pivot = (-10, 0, -2.4)
        a.rot = (0, 108, 0)
        a.cube((-10, 0.4, -3.1), (20, 41, 1.4), door_mat(PINK, IVORY, GOLD))
        b.pivot = (0, 47, -2.6)
        b.plane("z", (0, 49.5, -2.6), 16, 7, tex.shaped(lambda u, v: (np.hypot(u, v + 1) < 1.9).astype(float),
                                                         "#fff4d0", GOLD, glow=0.95, var=0, key="dnwfan"))
        b.plane("z", (0, 49.5, 2.6), 16, 7, tex.shaped(lambda u, v: (np.hypot(u, v + 1) < 1.9).astype(float),
                                                        "#d8ccff", MAUVE, glow=0.8, var=0, key="dnwfan2"))
    elif kind == 2:
        for (cx, cy, w, h) in ((-13, 46, 2, 32), (13, 46, 2, 32), (0, 63, 28, 2), (0, 29, 28, 2)):
            panel.box((cx, cy, 0), (w, h, 5), D["trim"], variant=1)
        panel.plane("z", (0, 46, 0), 24, 32, night("#30335e", "#8a6ad6", key="dnwallwin"))
        panel.box((0, 46, 0), (1, 32, 1.2), D["trim"], variant=2)
        panel.box((0, 46, 0), (24, 1, 1.2), D["trim"], variant=2)
        panel.box((0, 28.6, -3.6), (30, 1.4, 3), D["trim"])
        panel.box((0, 65, -3.4), (34, 1, 1), D["gold"])
        a.pivot = (-11, 65, -3.6)
        a.plane("z", (-11, 50, -3.6), 9, 30, D["fabric"])
        b.pivot = (11, 65, -3.6)
        b.plane("z", (11, 50, -3.6), 9, 30, D["fabric"], variant=1)
    else:
        a.pivot = (0, 0, -2)
        for k in range(6):
            sb = (-28 + k * 8, 0, -11)
            a.cube(sb, (8, (k + 1) * 9, 9), D["wood_l"], variant=k % 3, mats={"up": D["carpet"]})
        a.box((-6, 34, -11.4), (46, 1, 1), D["gold"], rot=(0, 0, 48.4), pivot=(-6, 34, -11.4))
        b.pivot = (14, 54, -2.4)
        b.cube((14, 54, -2.6), (8, 15, 0.6), door_mat(GOLD, IVORY, "#ffffff", glow=0.15))
        b.box((18, 55, -2.2), (10, 0.8, 0.5), D["trim"])
    return m


def wall_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    fly = Anim("fly", loop=True)                      # a flat card tumbling through the air
    fly.rot("root", (-88, LIFE(14, 1.1), LIFE(9, 0.8)))
    fly.scl("root", 0.6)
    A.append(fly)
    rise = Anim("rise", length=L_WRISE, loop="hold")   # pops up like a page of a pop-up book
    rise.rot("root", {0: (-88, 0, 0), 0.4: (10, 0, 0), 0.55: (-5, 0, 0), 0.7: (2, 0, 0), 0.8: (0, 0, 0)})
    rise.scl("root", {0: 0.6, 0.35: (1.0, 1.06, 1.0), 0.6: (1.02, 0.97, 1.02), 0.8: 1.0})
    rise.rot("deco_a", {0: (0, 0, 0), 0.45: (0, 0, -18), 0.6: (0, 0, 12), 0.8: (0, 0, 0)})
    rise.pos("crown", {0: (0, 0, 0), 0.42: (0, 3, 0), 0.6: (0, -0.5, 0), 0.8: (0, 0, 0)})
    A.append(rise)
    idle = Anim("idle", loop=True)
    idle.scl("panel", (1, 1, LIFE(0.08, 3.1, base=1.0)))
    idle.rot("deco_a", (LIFE(2.5, 2.9), LIFE(4, 3.7, 0.3), LIFE(3, 2.3)))
    idle.scl("deco_b", LIFE(0.06, 0.41, base=1.0))
    idle.pos("crown", (0, LIFE(0.3, 2.2), 0))
    A.append(idle)
    slide = Anim("slide", loop=True, length=0.6)
    slide.rot("root", (S(2.5, 0.3), 0, S(3, 0.6)))
    slide.pos("panel", (0, S(0.6, 0.3, base=0.6), 0))
    slide.rot("deco_a", (S(8, 0.6), S(16, 0.6, 0.1), S(10, 0.6, 0.25)))
    slide.pos("crown", (S(1.2, 0.6, 0.2), 0, 0))
    A.append(slide)
    settle = Anim("settle", length=L_WSETTLE, loop="hold")
    settle.scl("root", {0: (1.05, 0.9, 1.05), 0.15: (0.98, 1.04, 0.98), 0.32: (1.01, 0.99, 1.01), 0.5: (1, 1, 1)})
    settle.rot("deco_a", {0: (0, 0, -20), 0.2: (0, 0, 12), 0.35: (0, 0, -4), 0.5: (0, 0, 0)})
    settle.pos("crown", {0: (0, -2, 0), 0.2: (0, 1.5, 0), 0.5: (0, 0, 0)})
    A.append(settle)
    fold = Anim("fold", length=L_WFOLD, loop="hold")
    fold.rot("root", {0: (0, 0, 0), 0.12: (6, 0, 0), 0.5: (-88, 0, 0)})
    fold.scl("root", {0: 1.0, 0.5: 0.6})
    fold.rot("deco_a", {0: (0, 0, 0), 0.3: (0, 0, 25), 0.5: (0, 0, 0)})
    A.append(fold)
    return A


# =============================================================================================== furniture
def _common_anims(A, root_rest=None):
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    appear = Anim("appear", length=L_FAPPEAR, loop="hold")
    appear.scl("root", {0: 0.0, 0.32: (1.18, 0.82, 1.18), 0.48: (0.95, 1.06, 0.95), 0.6: 1.0})
    appear.rot("root", {0: (0, -120, 0), 0.4: (0, 0, 0)})
    vanish = Anim("vanish", length=L_FVANISH, loop="hold")
    vanish.scl("root", {0: 1.0, 0.15: (1.12, 0.88, 1.12), 0.5: 0.0})
    vanish.rot("root", {0: (0, 0, 0), 0.5: (0, 200, 0)})
    A += [hidden, appear, vanish]
    return A


def bed_model(D):
    m = Model("dn_house_bed", density=1.0, bounds=(4, 4, (0, 1.5, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 10, 0))
    for s, sx in (("r", 1), ("l", -1)):
        for e, sz in (("f", -1), ("b", 1)):
            lg = m.bone(f"leg_{e}{s}", body, pivot=(sx * 11, 10, sz * 17))
            lg.box((sx * 11, 5.5, sz * 17), (3, 9, 3), D["wood"], variant=1)
            lg.box((sx * 11, 1.2, sz * 17), (4, 2.4, 4), D["gold"])
    body.box((0, 11.5, 0), (26, 4, 38), D["wood"])
    body.box((0, 14.8, 0.5), (24, 3, 36), D["trim"])
    q = m.bone("quilt", body, pivot=(0, 16, 4))
    q.box((0, 17, -3), (25.6, 2.6, 28), D["quilt"])
    q.box((0, 13.4, -17.3), (25.6, 7.4, 0.8), D["quilt"], variant=1)
    for sx in (-1, 1):
        q.box((sx * 12.95, 13.4, -3), (0.8, 7.4, 28), D["quilt"], variant=2)
    pil = m.bone("pillows", body, pivot=(0, 18, 14))
    pil.box((-6, 18.4, 13.5), (10, 3.6, 7), D["porc_p"])
    pil.box((6, 18.4, 13.5), (10, 3.6, 7), D["porc"])
    hb = m.bone("headboard", body, pivot=(0, 10, 19))
    hb.box((0, 24, 19), (28, 28, 2), D["wood"], mats={"north": tex.trimmed(D["wp3"], GOLD, 1, 1)})
    hb.box((0, 39, 19), (20, 3, 2), D["wood"], variant=1)
    hb.box((0, 41.5, 19), (11, 2, 2), D["wood"], variant=2)
    hb.plane("z", (0, 33, 17.8), 9, 9, tex.shaped(tex.m_crescent(0.38), "#fff6d6", GOLD, glow=1.0, var=0, key="dnhbmoon"))
    body.box((0, 17, -19.2), (28, 11, 2), D["wood"], variant=2)
    body.plane("z", (0, 18, -20.3), 7, 7, tex.shaped(tex.m_star(5, 0.45), "#fff6d6", GOLD, glow=0.9, var=0, key="dnfbstar"))
    for sx in (-1, 1):
        for sz in (-1, 1):
            body.box((sx * 13.6, 29, sz * 19.2), (2.4, 38, 2.4), D["wood"], variant=2)
            body.box((sx * 13.6, 48.6, sz * 19.2), (3.2, 3.2, 3.2), D["gold"])
    can = m.bone("canopy", body, pivot=(0, 47, 0))
    can.box((0, 47, 0), (29.6, 1.4, 40), D["wood"], mats={"up": D["fabric"], "down": D["fabric"]})
    for s, sx in (("r", 1), ("l", -1)):
        c = m.bone(f"curtain_{s}", can, pivot=(sx * 14.6, 46.5, 13))
        c.plane("x", (sx * 14.6, 32, 13), 11, 29, D["lace"], variant=1 if sx > 0 else 0)
        c2 = m.bone(f"valance_{s}", can, pivot=(sx * 15, 46.5, 0))
        c2.plane("x", (sx * 15, 43.5, 0), 40, 6, D["lace"], variant=2)
    ey = m.bone("eyes", body, pivot=(0, 6, -16))
    for sx in (-1, 1):
        ey.plane("z", (sx * 4.5, 6, -16.6), 4.5, 3, tex.eye_mat("#d8ccff", "#fff4e8", INDIGO, "#1c1d33", glow=1.0,
                                                               open_amt=0.7, slit=True))
    ey.plane("z", (0, 6, -16.4), 20, 7, D["dark"])
    return m


def bed_anims():
    A = _common_anims([])
    idle = Anim("idle", loop=True)
    idle.scl("quilt", (1, LIFE(0.22, 3.2, base=1.0), 1))
    idle.pos("quilt", (0, LIFE(0.8, 3.2), 0))
    idle.pos("pillows", (0, LIFE(0.5, 3.2, 0.12), 0))
    idle.rot("canopy", (LIFE(1.5, 4.1), 0, LIFE(1.2, 3.3)))
    sym(idle, "curtain_{s}", rot=(LIFE(5, 2.7), 0, LIFE(3, 3.1, 0.2)))
    sym(idle, "valance_{s}", rot=(0, 0, LIFE(2, 2.2)))
    idle.scl("eyes", (1, M("(math.mod(q.life_time, 3.7) < 0.18) ? 0.1 : 1.0",
                           lambda t: 0.1 if (t % 3.7) < 0.18 else 1.0), 1))
    A.append(idle)
    move = Anim("move", loop=True, length=0.6)
    for nm, ph in (("leg_fr", 0), ("leg_bl", 0), ("leg_fl", 0.5), ("leg_br", 0.5)):
        move.rot(nm, (S(26, 0.6, ph), 0, 0))
    move.rot("body", (S(2, 0.3), 0, S(3, 0.6)))
    move.pos("body", (0, S(1.0, 0.3, base=1.0), 0))
    A.append(move)
    act = Anim("act", length=L_FACT, loop="hold")      # a great sleepy breath
    act.scl("quilt", {0: (1, 1, 1), 0.4: (1.05, 1.9, 1.05), 0.8: (1, 1, 1)})
    act.pos("quilt", {0: (0, 0, 0), 0.4: (0, 3, 0), 0.8: (0, 0, 0)})
    act.rot("headboard", {0: (0, 0, 0), 0.4: (-14, 0, 0), 0.8: (0, 0, 0)})
    act.scl("eyes", {0: (1, 1, 1), 0.3: (1.4, 1.6, 1), 0.8: (1, 1, 1)})
    A.append(act)
    return A


def clock_model(D):
    m = Model("dn_house_clock", density=1.0, bounds=(3, 5, (0, 2, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 0, 0))
    for sx in (-1, 1):
        for sz in (-1, 1):
            body.box((sx * 6, 1, sz * 4), (2.4, 2, 2.4), D["gold"])
    body.box((0, 4.5, 0), (15, 5, 10), D["wood"])
    body.box((0, 21, 0), (11, 28, 8), D["wood"], variant=1)
    body.plane("z", (0, 20, -4.05), 8, 21, D["dark"])
    for sx in (-1, 1):
        body.box((sx * 5.8, 21, -4.1), (1.4, 28, 1.4), D["gold"], variant=1)
    pen = m.bone("pendulum", body, pivot=(0, 30, -4.2))
    pen.box((0, 22, -4.2), (0.8, 15, 0.4), D["gold"])
    pen.plane("z", (0, 13.5, -4.45), 5, 5, tex.shaped(tex.m_disc(), "#fff3c4", GOLD, glow=0.6, var=0, key="dnbob"))
    glass = m.bone("glass", body)
    glass.plane("z", (0, 20, -4.9), 8, 21, tex.crystal("#d9e6ff", "#8a9ad0", a=0.25, glow=0.2))
    hood = m.bone("hood", body, pivot=(0, 35, 0))
    hood.box((0, 41.5, 0), (15, 14, 10), D["wood"], variant=2)
    hood.plane("z", (0, 41.5, -5.05), 11.5, 11.5, clock_face())
    ring(hood, (0, 41.5, -5.3), 6.2, 14, (3.0, 1.0, 0.8), D["gold"], axis="z")
    hood.plane("z", (0, 41.5, -5.25), 2.6, 1.8, tex.eye_mat(MAUVE, IVORY, INDIGO, GOLD, glow=0.9, open_amt=0.8))
    hood.box((0, 49.2, 0), (16.4, 2, 11), D["trim"])
    hood.box((0, 51.6, 0), (10, 3, 8), D["wood"], variant=1)
    for sx in (-1, 1):
        hood.box((sx * 6.4, 52.4, 0), (2.6, 2.6, 2.6), D["gold"])
    hood.plane("z", (0, 56.4, 0), 6, 6, tex.shaped(tex.m_crescent(0.36), "#fff3c4", GOLD, glow=1.0, var=0, key="dnclkmoon"))
    hh = m.bone("hand_h", hood, pivot=(0, 41.5, -5.5))
    hh.box((0, 43.2, -5.5), (1.3, 3.6, 0.3), D["dark"])
    hm = m.bone("hand_m", hood, pivot=(0, 41.5, -5.7))
    hm.box((0, 44.0, -5.7), (0.8, 5.2, 0.3), tex.flat(BURG, glow=0.2))
    body.locator("face", (0, 42, -6))
    return m


def clock_anims():
    A = _common_anims([])
    idle = Anim("idle", loop=True)
    idle.rot("pendulum", (0, 0, LIFE(16, 1.1)))
    idle.rot("hand_m", (0, 0, spin(140)))
    idle.rot("hand_h", (0, 0, spin(-35)))
    idle.rot("body", (0, 0, LIFE(1.5, 4.0)))
    idle.rot("hood", (LIFE(1.2, 2.2), 0, 0))
    A.append(idle)
    move = Anim("move", loop=True, length=0.5)
    move.pos("root", (0, M("math.abs(math.sin(q.anim_time*360))*7", lambda t: abs(math.sin(t * 2 * math.pi)) * 7), 0))
    move.rot("body", (S(5, 0.5, 0.25), 0, S(7, 0.5)))
    A.append(move)
    act = Anim("act", length=L_FACT, loop="hold")      # the chime: it shudders, its hands whirl
    act.scl("hood", {0: 1.0, 0.1: 1.16, 0.3: 0.94, 0.5: 1.05, 0.8: 1.0})
    act.rot("body", {0: (0, 0, 0), 0.1: (0, 0, 6), 0.25: (0, 0, -6), 0.4: (0, 0, 3), 0.6: (0, 0, 0)})
    act.rot("hand_m", {0: (0, 0, 0), 0.8: (0, 0, 720)})
    act.rot("hand_h", {0: (0, 0, 0), 0.8: (0, 0, -360)})
    act.rot("pendulum", {0: (0, 0, 0), 0.2: (0, 0, 40), 0.5: (0, 0, -30), 0.8: (0, 0, 0)})
    A.append(act)
    return A


def chandelier_model(D):
    m = Model("dn_house_chandelier", density=1.0, bounds=(4, 8, (0, 4, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 60, 0))
    chain = m.bone("chain", body)
    for k in range(13):                         # the chain fades into nothing
        a = max(0.05, 1.0 - k / 12.0)
        cm = tex.flat("#e9cf8a", glow=0.35, a=round(a, 2), mode="blend", key=f"dnchain{k}")
        size = (1.8, 3.4, 0.6) if k % 2 == 0 else (0.6, 3.4, 1.8)
        chain.box((0, 57 + k * 3, 0), size, cm)
    body.box((0, 52, 0), (5, 7, 5), D["gold"])
    body.box((0, 47.4, 0), (3, 3, 3), D["gold"], variant=1)
    ring(body, (0, 56.5, 0), 4.6, 8, (2.0, 1.0, 1.2), D["gold"], cycle=2)
    ring(body, (0, 50.5, 0), 6.2, 6, (1.3, 9.0, 1.3), D["gold"], start=0)
    ring(body, (0, 51.0, 0), 11, 6, (2.8, 2.8, 1.2), D["gold"], start=0, variant=1)
    fl = m.bone("flames", body, pivot=(0, 52, 0))
    for k in range(6):
        a = math.radians(k * 60 + 30)
        px, pz = math.cos(a) * 11, math.sin(a) * 11
        fl.box((px, 53.6, pz), (1.2, 3.6, 1.2), D["trim"])
        fl.plane("z", (px, 57, pz), 2, 3.2, D["flame"])
        fl.plane("x", (px, 57, pz), 2, 3.2, D["flame"])
    for k in range(6):
        a = math.radians(k * 60)
        px, pz = math.cos(a) * 8, math.sin(a) * 8
        cb = m.bone(f"crys_{k + 1}", body, pivot=(px, 49.5, pz))
        cb.box((px, 47.5, pz), (1.4, 3.6, 1.4), tex.crystal(BLUE, "#8a6ad6", a=0.85, glow=0.5), rot=(0, 45, 0),
               pivot=(px, 47.5, pz))
        cb.box((px, 45.2, pz), (0.8, 1.6, 0.8), tex.crystal("#ffffff", BLUE, a=0.9, glow=0.6), rot=(0, 45, 0),
               pivot=(px, 45.2, pz))
    cc = m.bone("crys_c", body, pivot=(0, 46, 0))
    cc.box((0, 43, 0), (2, 5, 2), tex.crystal(BLUE, "#8a6ad6", a=0.85, glow=0.5), rot=(0, 45, 0), pivot=(0, 43, 0))
    body.locator("hub", (0, 46, 0))
    return m


def chandelier_anims():
    A = _common_anims([])
    idle = Anim("idle", loop=True)
    idle.rot("body", (LIFE(3, 4.4, 0.2), spin(18), LIFE(4, 3.6)))
    idle.scl("flames", LIFE(0.12, 0.27, base=1.0))
    for k in range(6):
        idle.rot(f"crys_{k + 1}", (LIFE(6, 1.6, k * 0.15), 0, LIFE(6, 1.9, k * 0.21)))
    A.append(idle)
    move = Anim("move", loop=True, length=0.8)
    move.rot("root", (S(8, 0.8), 0, S(6, 0.8, 0.25)))
    A.append(move)
    act = Anim("act", length=L_FACT, loop="hold")      # it shudders and lets its crystals fall
    for k in list(range(6)) + ["c"]:
        nm = f"crys_{k + 1}" if k != "c" else "crys_c"
        d = 0 if k == "c" else k * 0.02
        act.pos(nm, {0: (0, 0, 0), 0.12 + d: (0, 2, 0), 0.55 + d: (0, -44, 0), 0.8: (0, -44, 0)})
        act.scl(nm, {0: 1.0, 0.5 + d: 1.0, 0.62 + d: 0.0, 0.8: 0.0})
    act.rot("body", {0: (0, 0, 0), 0.08: (0, 0, 9), 0.18: (0, 0, -9), 0.3: (0, 0, 5), 0.5: (0, 0, 0)})
    act.scl("flames", {0: 1.0, 0.1: 1.6, 0.4: 1.0})
    A.append(act)
    return A


def table_model(D):
    m = Model("dn_house_table", density=1.0, bounds=(3, 4, (0, 2, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 24, 0))
    body.box((0, 24, 0), (28, 2.6, 20), D["wood"], mats={"down": D["wood_l"]})
    body.box((0, 22.6, 0), (26, 0.6, 18), D["lace"])
    for k, (sx, sz) in enumerate(((1, 1), (-1, 1), (1, -1), (-1, -1))):
        lg = m.bone(f"tleg_{k + 1}", body, pivot=(sx * 12, 25.3, sz * 8))
        lg.box((sx * 12, 31.5, sz * 8), (2.2, 12, 2.2), D["wood"], variant=k % 3)
        lg.box((sx * 12, 29, sz * 8), (3, 2, 3), D["wood_l"])
        lg.box((sx * 12, 38.2, sz * 8), (3, 1.6, 3), D["gold"])
    for nm, piv, axis, center, w in (("cloth_f", (0, 25.3, -10.4), "z", (0, 29, -10.4), 29),
                                     ("cloth_b", (0, 25.3, 10.4), "z", (0, 29, 10.4), 29),
                                     ("cloth_r", (14.4, 25.3, 0), "x", (14.4, 29, 0), 21),
                                     ("cloth_l", (-14.4, 25.3, 0), "x", (-14.4, 29, 0), 21)):
        cb = m.bone(nm, body, pivot=piv)
        cb.plane(axis, center, w, 7, D["lace"], rot=(0, 0, 180) if axis == "z" else (180, 0, 0), pivot=center,
                 variant=len(nm) % 2)
    body.box((-5, 20.2, 2), (6, 5, 5), D["porc_p"])
    body.box((-1.2, 19.6, 2), (3, 1.2, 1.2), D["porc_p"], rot=(0, 0, 30), pivot=(-1.2, 19.6, 2))
    body.box((-5, 17.4, 2), (2, 0.8, 2), D["gold"])
    for k, (x, z) in enumerate(((6, -4), (-7, -5), (8, 4))):
        body.box((x, 22.4, z), (5, 0.6, 5), D["porc"], variant=k % 2)
        body.box((x, 20.8, z), (3, 2.6, 3), D["porc"] if k != 1 else D["porc_p"])
    body.box((2, 19.4, 5.5), (1.4, 5, 1.4), D["trim"])
    body.plane("z", (2, 15.6, 5.5), 2, 3, D["flame_n"], rot=(0, 0, 180), pivot=(2, 15.6, 5.5))
    body.plane("x", (2, 15.6, 5.5), 2, 3, D["flame_n"], rot=(180, 0, 0), pivot=(2, 15.6, 5.5))
    return m


def table_anims():
    A = _common_anims([])
    idle = Anim("idle", loop=True)
    idle.pos("body", (0, LIFE(1.4, 2.8), 0))
    idle.rot("body", (LIFE(3, 3.9, 0.3), LIFE(12, 7.0), LIFE(3, 3.3)))
    for k in range(4):
        idle.rot(f"tleg_{k + 1}", (LIFE(6, 1.7, k * 0.25), 0, LIFE(4, 2.1, k * 0.2)))
    for k, nm in enumerate(("cloth_f", "cloth_b", "cloth_r", "cloth_l")):
        idle.rot(nm, (LIFE(9, 2.2, k * 0.2) if k < 2 else 0, 0, LIFE(9, 2.2, k * 0.2) if k >= 2 else 0))
    A.append(idle)
    move = Anim("move", loop=True, length=0.4)
    for k in range(4):
        move.rot(f"tleg_{k + 1}", (S(32, 0.4, k * 0.25), 0, 0))
    move.rot("root", (S(5, 0.4), 0, 0))
    A.append(move)
    act = Anim("act", length=L_FACT, loop="hold")      # lunges and slams
    act.rot("body", {0: (0, 0, 0), 0.15: (-24, 0, 0), 0.35: (18, 0, 0), 0.55: (-4, 0, 0), 0.8: (0, 0, 0)})
    act.pos("body", {0: (0, 0, 0), 0.15: (0, 4, 4), 0.35: (0, -6, -6), 0.8: (0, 0, 0)})
    A.append(act)
    return A


def door_model(D):
    m = Model("dn_house_door", density=1.0, bounds=(3, 4, (0, 1.5, 0)))
    root = m.bone("root", pivot=(0, 22, 0))
    fr = m.bone("frame", root, pivot=(0, 22, 0))
    for sx in (-1, 1):
        fr.box((sx * 11.5, 22, 0), (3, 44, 4), D["trim"], variant=1)
        fr.box((sx * 11.5, 1.5, 0), (4.4, 3, 5), D["gold"])
    fr.box((0, 45.5, 0), (26, 3, 5), D["gold"])
    fr.plane("z", (0, 50, 0), 10, 6, tex.shaped(tex.m_crescent(0.35), "#fff3c4", GOLD, glow=1.0, var=0, key="dndoormoon"))
    lf = m.bone("leaf", root, pivot=(-10, 1, 0))
    lf.cube((-10, 1, -0.8), (20, 43, 1.6), door_mat(GOLD, IVORY, "#ffffff", glow=0.2))
    lf.plane("z", (6, 21, -0.9), 1.4, 2.4, tex.glow_flat("#ffffff", 1.0), )
    return m


def door_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    hop = Anim("hop", loop=True, length=0.8)
    hop.rot("root", {0: (0, 0, 0), 0.8: (-360, 0, 0)}, smooth=False)
    hop.rot("leaf", (0, S(55, 0.4, base=-55), 0))
    hop.scl("root", {0: (1.2, 0.8, 1.2), 0.15: (0.9, 1.1, 0.9), 0.65: (1, 1, 1), 0.8: (1.2, 0.8, 1.2)})
    pop = Anim("pop", length=0.4, loop="hold")
    pop.scl("root", {0: 1.0, 0.1: 1.3, 0.4: 0.0})
    pop.rot("leaf", {0: (0, 0, 0), 0.2: (0, -120, 0)})
    A += [hidden, hop, pop]
    return A


# =============================================================================================== sounds
SEMI = 2 ** (1 / 12)
MOTIF = [0, 7, 4, 11, 9, 2, 5, 0]          # the house's own lullaby (interval pattern, music box)
MBASE = 659.25


def mbox(f, dur=0.9, bright=0.9):
    return sy.mixdown([sy.pluck(f, dur, bright), sy.bell(f * 2, dur * 0.8, inharm=0.25) * 0.3])


def lullaby(step=0.3, warp=0.0, notes=MOTIF, base=MBASE, choir=True):
    parts = []
    for k, n in enumerate(notes):
        f = base * SEMI ** n
        drift = 1 - warp * 0.04 * k                       # pitch sags like a tired spring
        parts.append((k * step * (1 + warp * 0.08 * k), mbox(f * drift, 1.0), 0.8))
        if warp:
            parts.append((k * step + 0.012, mbox(f * drift * 0.97, 0.9), 0.45 * warp))      # detuned double
            parts.append((k * step + 0.05, mbox(f * drift * SEMI ** 6 / 2, 0.8, 0.5), 0.25 * warp))  # tritone shadow
    sig = sy.at(len(notes) * step + 1.0, *parts)
    if choir:
        pad = sy.choir(base / 4 * (1 - warp * 0.06), len(sig) / sy.SR, "oo", voices=4, attack=0.5, release=0.8)
        sig = sy.mixdown([sig, pad * (0.25 + 0.2 * warp)])
    if warp:
        tail = sy.pitch(sig[-int(sy.SR * 0.8):][::-1], 0.92) * 0.35
        sig = sy.at(len(sig) / sy.SR + 0.6, (0.0, sig), (len(sig) / sy.SR - 0.3, tail))
    return sig


def build_sounds(pack):
    rv = sy.reverb
    # music-box wind-up: ratchet clicks speeding up, then the first notes of the motif
    clicks = [(0.07 * k * (1 - k * 0.02), sy.crack(0.05, 3400 + 200 * (k % 3), 2), 0.6) for k in range(14)]
    wind = sy.at(2.4, *clicks, (0.95, lullaby(0.24, 0.0, MOTIF[:4], choir=False), 0.9),
                 (0.9, sy.creak(0.6, 260, 340, 0.1) * 0.25))
    sy.save(pack, "dn_house_windup", rv(wind, 1.4, 0.3), max_distance=48)
    land = sy.at(1.4, (0.0, sy.thump(0.7, 140, 42, 0.5)), (0.0, sy.crack(0.25, 2400, 6) * 0.4),
                 (0.06, mbox(MBASE * SEMI ** 7, 1.2) * 0.5), (0.1, sy.creak(0.4, 160, 120, 0.2) * 0.3))
    sy.save(pack, "dn_house_land", rv(land, 1.2, 0.3), max_distance=48)
    op = sy.at(2.2, (0.0, sy.creak(1.1, 130, 230, 0.3) * 0.7), (0.15, sy.creak(1.0, 170, 260, 0.3) * 0.6),
               (0.4, sy.whoosh(0.9, 300, 1800) * 0.4), (0.3, sy.choir(MBASE / 2, 1.8, "oo", voices=4) * 0.45),
               (0.8, sy.shimmer(1.2, 2000, 16) * 0.35))
    sy.save(pack, "dn_house_open", rv(op, 1.8, 0.35), max_distance=56)
    flaps = [(0.08 + k * 0.09, sy.thump(0.25, 220 - k * 8, 90, 0.7) * 0.5) for k in range(8)]
    unf = sy.at(1.8, *flaps, (0.0, sy.whoosh(1.2, 400, 2600) * 0.5), (0.1, sy.scribble(1.0, 9) * 0.35),
                (0.6, sy.shimmer(1.0, 1600, 12) * 0.3))
    sy.save(pack, "dn_house_unfold", rv(unf, 1.4, 0.3), max_distance=56)

    def slide(f0, f1, cr):
        n = sy.bandpass(sy.noise(0.75), (f0 + f1) / 2, 1.3) * sy.env(0.75, 0.06, 0.1, 0.8, 0.25)
        return sy.mixdown([n, sy.creak(0.7, cr, cr * 1.4, 0.35) * 0.35, sy.rumble(0.75, 60, 5) * 0.4])
    sy.save(pack, "dn_house_slide", rv(slide(500, 900, 120), 0.9, 0.25),
            variants=[rv(slide(350, 700, 95), 0.9, 0.25), rv(slide(650, 1200, 150), 0.9, 0.25)], volume=0.8, max_distance=40)

    def knock(f):
        return sy.at(0.6, (0.0, sy.thump(0.35, f, f * 0.4, 0.8)), (0.0, sy.crack(0.2, 1800, 5) * 0.35),
                     (0.03, sy.lowpass(sy.noise(0.4), 900) * sy.decay(0.4, 0.08) * 0.3))
    sy.save(pack, "dn_house_settle", rv(knock(190), 0.8, 0.25), variants=[rv(knock(160), 0.8, 0.25), rv(knock(230), 0.8, 0.25)],
            volume=0.9, max_distance=40)
    t = sy.t_axis(0.7)
    boing = sy.osc(420 * (1 + 0.25 * np.sin(2 * np.pi * 9 * t) * np.exp(-t / 0.25)), wave_="tri") * np.exp(-t / 0.2)
    popf = sy.osc(sy.sweep(260, 1100, 0.07, 0.5)) * np.exp(-sy.t_axis(0.07) / 0.03)
    pop = sy.at(0.8, (0.0, popf), (0.0, sy.highpass(sy.noise(0.05), 1500) * 0.4), (0.04, boing * 0.6),
                (0.05, mbox(MBASE * SEMI ** 12, 0.6) * 0.3))
    sy.save(pack, "dn_house_pop", rv(pop, 0.8, 0.25), max_distance=40)

    def tick(f, f2):
        return sy.at(0.25, (0.0, sy.pluck(f, 0.12, 1.0) * 0.6), (0.0, sy.highpass(sy.noise(0.012), 3000) * 0.5),
                     (0.004, sy.thump(0.08, f2, f2 * 0.6, 0.6) * 0.4))
    sy.save(pack, "dn_house_tick", rv(tick(2300, 700), 0.5, 0.2),
            variants=[rv(tick(1900, 560), 0.5, 0.2), rv(tick(2600, 820), 0.5, 0.2)], volume=0.6, max_distance=24)
    sy.save(pack, "dn_house_lullaby", rv(lullaby(0.3, 0.0), 2.0, 0.4), volume=0.8, max_distance=56)
    sy.save(pack, "dn_house_lullaby_warp", rv(lullaby(0.28, 1.0, [MOTIF[i] for i in (4, 5, 6, 7, 0, 3)]), 2.2, 0.45),
            variants=[rv(lullaby(0.3, 0.7, [MOTIF[i] for i in (0, 1, 2, 3, 6, 7)], base=MBASE * SEMI ** -3), 2.2, 0.45)],
            volume=0.8, max_distance=56)
    loop = sy.at(1.6, (0.0, sy.whoosh(0.8, 2400, 300)[::-1] * 0.6), (0.55, sy.thump(0.4, 120, 50, 0.9) * 0.7),
                 (0.55, sy.creak(0.35, 300, 200, 0.2) * 0.3), (0.75, sy.thump(0.4, 120, 50, 0.9) * 0.35),
                 (0.95, sy.thump(0.4, 120, 50, 0.9) * 0.15), (0.2, mbox(MBASE * SEMI ** 6, 0.9, 0.5) * 0.35))
    sy.save(pack, "dn_house_loop", rv(loop, 1.6, 0.45), max_distance=40)
    chime = sy.at(2.4, *[(k * 0.42, sy.bell(MBASE / 2 * SEMI ** [0, 6, 1][k] * (1 - 0.01 * k), 1.8, inharm=1.15) * (0.8 - k * 0.15))
                        for k in range(3)], (0.0, sy.pad(MBASE / 8, 2.2, cutoff=600) * 0.2))
    sy.save(pack, "dn_house_chime", rv(chime, 2.0, 0.4), max_distance=48)
    crys = sy.at(1.4, (0.0, sy.crack(0.6, 7000, 22) * 0.7), (0.0, sy.shimmer(1.2, 2600, 26) * 0.6),
                 (0.02, sy.bell(2200, 0.9, inharm=1.3) * 0.3))
    sy.save(pack, "dn_house_crystal", rv(crys, 1.0, 0.3), max_distance=40)
    snore = sy.formants(sy.noise(1.8) * sy.env(1.8, 0.7, 0.2, 0.8, 0.8), sy.VOWELS["oh"])
    snore = sy.mixdown([snore, sy.roar(1.8, 70, 55, growl=18, rough=0.3, formant=(400, 900), breath=0.6, bend=0.1) * 0.25])
    sy.save(pack, "dn_house_bed", rv(snore, 1.0, 0.3), volume=0.7, max_distance=24)
    pat = sy.at(0.7, *[(k * 0.06 + (k % 2) * 0.015, sy.thump(0.08, 420 + (k % 3) * 70, 240, 0.9) * 0.6) for k in range(10)])
    sy.save(pack, "dn_house_scuttle", rv(pat, 0.6, 0.2), max_distance=32)
    fold = sy.at(1.6, (0.0, sy.whoosh(1.2, 2600, 400) * 0.5), *[(0.5 + k * 0.1, sy.thump(0.2, 260, 110, 0.9) * 0.4) for k in range(6)],
                 (0.1, lullaby(0.22, 0.4, [0, 4, 7, 0][::-1], choir=False) * 0.4))
    sy.save(pack, "dn_house_fold", rv(fold, 1.4, 0.35), max_distance=56)
    clack = sy.at(2.4, (0.0, sy.thump(0.4, 240, 80, 1.0)), (0.0, sy.crack(0.15, 2600, 8) * 0.7),
                  (0.06, sy.thump(0.3, 180, 70, 0.8) * 0.4), (0.25, sy.pitch(mbox(MBASE, 2.0), 0.97) * 0.45))
    sy.save(pack, "dn_house_clack", rv(clack, 1.6, 0.35), max_distance=56)


# =============================================================================================== build
def build(pack):
    D = mats()
    fx = particles(pack)
    fx.effect("dn_house_dust", "puff", count=7, life=(0.6, 1.1), size=(0.3, 0.7), shape=("box", (1.4, 0.1, 0.3)),
              speed=(0.3, 1.0), accel=(0, 0.35, 0), drag=1.8, colors=["#efe3d2cc", "#cfc6b000"], blend="blend", spin=(360, 40))
    fx.effect("dn_house_chalk", "dot", count=2, life=(0.5, 0.9), size=(0.13, 0.0), shape=("sphere", 0.25), speed=(0.0, 0.2),
              accel=(0, 0.7, 0), colors=["#eef6ffff", "#bcd6f0cc", "#8a6ad600"])
    fx.effect("dn_house_note", None, sprites=["note", "star"], count=2, life=(1.2, 2.0), size=(0.2, 0.1), shape=("sphere", 0.3),
              direction=(0, 1, 0), speed=(0.4, 0.8), accel=(0.25, 0.35, 0), drag=0.7, colors=["#fff3c4ff", "#ffd9b8ff", "#e8b4c800"])
    fx.effect("dn_house_scrap", None, sprites=["petal", "diamond", "star"], count=10, life=(1.0, 1.8), size=(0.13, 0.08),
              shape=("sphere", 1.2), speed=(1.0, 2.6), accel=(0, -2, 0), drag=1.2, colors=["#ffd9b8ff", "#e8b4c8ff", "#bcd6f000"],
              blend="blend", spin=(360, 180))
    fx.effect("dn_house_loop", None, sprites=["door", "ringthin"], count=7, life=(0.6, 1.0), size=(0.28, 0.0), shape=("disc", 1.0),
              direction="inwards", speed=(0.6, 1.4), colors=["#e8b4c8ff", "#8a6ad6dd", "#2a2d5200"])
    fx.effect("dn_house_sleep", None, sprites=["moon", "star"], count=3, life=(1.0, 1.6), size=(0.17, 0.05), shape=("sphere", 0.7),
              speed=(0.1, 0.3), accel=(0, 0.6, 0), colors=["#bcd6f0ff", "#e9cf8aff", "#e8b4c800"])
    fx.effect("dn_house_crystal", "shard", count=10, life=(0.4, 0.8), size=(0.13, 0.05), shape=("sphere", 0.7), speed=(1.5, 4.0),
              accel=(0, -12, 0), colors=["#ffffffff", "#bcd6f0ff", "#8a6ad600"], spin=(360, 360))
    fx.effect("dn_house_tick", "ringthin", count=1, life=(0.5, 0.6), size=(0.3, 3.5), facing="emitter_transform_xz",
              colors=["#e8b4c8ff", "#6a4a6e00"])
    fx.effect("dn_house_glow", "glow", count=1, life=(0.3, 0.4), size=(0.9, 2.2), colors=["#fff3c4ff", "#ffd9b800"])
    fx.effect("dn_house_key", None, sprites=["key", "door", "window", "moon"], count=5, life=(0.9, 1.5), size=(0.22, 0.08),
              shape=("sphere", 0.8), speed=(0.5, 1.4), accel=(0, 0.8, 0), drag=0.9, colors=["#fff3c4ff", "#e8b4c8ff", "#8a6ad600"])
    pfx = {"note": "grimoire:dn_house_note", "scrap": "grimoire:dn_house_scrap"}

    house, shutters = house_model(D)
    ha = house_anims(shutters)
    pack.actor("dn_house_doll", house, ha, HOUSE_STATES, always=["life"], scale=1.6, lifetime=60,
               particles=pfx, display="House of Shifting Sleep")
    walls = [wall_model(k, D) for k in range(4)]
    wa = wall_anims()
    pack.actor("dn_house_wall", walls[0], wa, WALL_STATES, kinds=walls[1:], lifetime=60, display="Shifting Wall", blend=0.12)
    furn = [("dn_house_bed", bed_model(D), bed_anims(), "Breathing Bed"),
            ("dn_house_clock", clock_model(D), clock_anims(), "Thirteen-Hour Clock"),
            ("dn_house_chandelier", chandelier_model(D), chandelier_anims(), "Chandelier on Nothing"),
            ("dn_house_table", table_model(D), table_anims(), "Upside-Down Table")]
    for ident, mdl, an, disp in furn:
        pack.actor(ident, mdl, an, FURN_STATES, lifetime=60, display=disp, blend=0.15)
    dm = door_model(D)
    da = door_anims()
    pack.actor("dn_house_door", dm, da, DOOR_STATES, lifetime=60, display="Hopping Door", blend=0.0)
    build_sounds(pack)

    by = {a.name: a for a in ha}
    lf = (by["life"], 1.0)
    pack.preview("dn_house_a", house, [[(by["closed"], 0.5), lf], [(by["opened"], 0.5), lf], [(by["spread"], 0.5), lf]],
                 views=((25, 15), (-35, 25), (180, 15)))
    pack.preview("dn_house_b", house, [[(by["opened"], 0.5), lf]], views=((0, 5),), cell=(900, 900))
    wb = {a.name: a for a in wa}
    for k, mdl in enumerate(walls):
        pack.preview(f"dn_house_wall{k}", mdl, [(wb["idle"], 0.5)], views=((20, 12), (200, 12)), cell=(300, 300))
    for ident, mdl, an, _ in furn:
        ab = {a.name: a for a in an}
        pack.preview(ident, mdl, [(ab["idle"], 0.6), (ab["act"], 0.4)], views=((30, 15), (-60, 20)), cell=(300, 300))
    pack.preview("dn_house_door", dm, [None], views=((30, 15),), cell=(300, 300))
    print(f"    house: {house.cube_count()} cubes, {len(house.order)} bones, tex {house.tex_size}; "
          f"walls {[w.cube_count() for w in walls]}")
