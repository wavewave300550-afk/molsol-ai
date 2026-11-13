"""DN06 set pieces: the floating antique bed, its dropped pillow, the opened Codex with its
page-structures, the miniature bedroom of the Forgotten Morning, the target mark and the domain."""
import math

import numpy as np

from kit import glyphs, tex
from kit.anim import LIFE, Anim, M, S
from kit.geo import Mat, Model

from .dn_dreamer import (AGED, BURG, INDIGO, IVORY, MAUVE, PBLUE, PEACH, PINK, SGOLD, P, door_mat, gilt, keyed,
                         lamp_mat, quilt, spin, wallpaper, window_mat)

DREAMG = list(glyphs.DREAM.values())

# ---------------------------------------------------------------- bed
BED_SCALE = 2.0
SWING_T = 2.4      # seconds of the pendulum swing (dn06 config mirrors this)
SWING_A = 58.0     # amplitude in degrees


def painted_wood(base="#f4ead8", dark="#d9c6a4"):
    return tex.wood(base, dark, var=0.03)


def headboard_mat():
    kb, kg = tex.rgb(PINK), tex.rgb(SGOLD)

    def fn(ctx):
        u, v = ctx.U * 2 - 1, 1 - ctx.V * 2
        t = tex.tile(ctx, PINK, 1, 0.15)
        t[..., :3] = tex.mix(tex.rgb("#f2cfdc"), tex.rgb("#c995b0"), np.clip(ctx.V, 0, 1)[..., None])
        moon = (np.hypot(u, v - 0.1) < 0.42) & (np.hypot(u - 0.17, v - 0.16) > 0.36)
        t[..., :3] = np.where(moon[..., None], kg, t[..., :3])
        t[..., 4] = np.where(moon, 0.8, 0.15)
        ix, iy = tex.px(ctx)
        st = tex._hash(ix // 2, iy // 2, 41) > 0.95
        t[..., :3] = np.where(st[..., None], tex.rgb("#fff4d8"), t[..., :3])
        t[..., 4] = np.where(st, 0.9, t[..., 4])
        border = (np.abs(u) > 0.9) | (np.abs(v) > 0.88)
        t[..., :3] = np.where(border[..., None], kg, t[..., :3])
        return tex.grain(ctx, t, 0.02)
    return Mat(fn, "dnb_headboard", directional=True)


def scallop(color, color2, key):
    return tex.shaped(lambda u, v: (v > -0.55 + 0.35 * np.abs(np.sin(u * math.pi * 3))).astype(float), color, color2,
                      glow=0.1, outline=SGOLD, key=key, var=0.02)


def pillow_geo(b, cx, cz, y0=0.0, k=1.0):
    pm = tex.alt(quilt("#fff8ee", "#f3e6d6", SGOLD, moon=False, key="pillowq", glow=0.12),
                 nightmare=quilt(AGED, "#bdb39b", BURG, moon=False, key="pillowqn"))
    b.box((cx, y0 + 6 * k, cz), (38 * k, 10 * k, 24 * k), pm)
    b.box((cx, y0 + 6 * k, cz), (34 * k, 12 * k, 20 * k), pm, variant=1)
    for sx in (-1, 1):
        for sz in (-1, 1):
            b.box((cx + sx * 19 * k, y0 + 6 * k, cz + sz * 12 * k), (3 * k, 3 * k, 3 * k), gilt(0.3))


def bed_model():
    m = Model("dn_dreamer_bed", density=0.75, bounds=(40, 30, (0, 0, 0)), alts=("nightmare",))
    W = tex.alt(painted_wood(), nightmare=tex.wood("#8f8478", "#4c4250"))
    G = gilt(0.2)
    root = m.bone("root")
    bed = m.bone("bed", root)
    # mattress, sheet, blanket
    mat_q = tex.alt(quilt("#fbf3e6", "#efe2cf", PEACH, moon=False, key="mattress"),
                    nightmare=quilt("#a99fb0", "#8b8f9a", MAUVE, moon=False, key="mattressn"))
    bed.box((0, -7, 0), (88, 14, 136), mat_q)
    blank = tex.alt(quilt(PBLUE, "#e9f2fb", SGOLD, key="bedq"), nightmare=quilt(INDIGO, "#4a3e6a", BURG, key="bedqn"))
    bed.box((0, 1.5, -24), (90, 3, 90), blank)
    bed.box((0, 3.4, 18), (90, 1.2, 8), tex.flat("#fffaf0", glow=0.1))
    # frame
    for sx in (-1, 1):
        bed.box((sx * 46, -18, 0), (4, 10, 140), W)
        bed.box((sx * 46, -13, 0), (4.6, 1.4, 140.6), G)
    bed.box((0, -18, -70), (92, 10, 4), W)
    bed.box((0, -18, 70), (92, 10, 4), W)
    # headboard with a gilded moon, footboard
    bed.box((0, 26, 72), (92, 52, 4), W)
    bed.plane("z", (0, 26, 69.8), 76, 42, headboard_mat())
    for k, (w, h) in enumerate(((70, 6), (48, 5), (24, 5))):
        bed.box((0, 52 + 3 + k * 5.5, 72), (w, h + 0.5, 4), W, variant=k)
    bed.box((0, 69, 72), (8, 3, 5), G)
    bed.box((0, 8, -72), (92, 26, 4), W, variant=1)
    bed.plane("z", (0, 8, -74.2), 70, 18, door_mat(PINK, SGOLD, key="footpanel", knob=False))
    bed.box((0, 21.5, -72), (94, 2, 5), G)
    # four carved posts
    prof = [(-46, -40, 3), (-40, -32, 6), (-32, -12, 8), (-12, 0, 6.5), (0, 4, 8.5), (4, 30, 4.5), (30, 37, 7.5),
            (37, 68, 4.2), (68, 72, 6.5), (72, 90, 4.0), (90, 95, 7.5)]
    for sx in (-1, 1):
        for sz in (-1, 1):
            for i, (y0, y1, w) in enumerate(prof):
                bed.box((sx * 48, (y0 + y1) / 2, sz * 72), (w, y1 - y0, w), G if i in (0, 4, 8) else W, variant=i % 3)
    # canopy
    can = m.bone("canopy", bed, pivot=(0, 95, 0))
    for sx in (-1, 1):
        can.box((sx * 48, 96.5, 0), (4, 3, 148), W)
    for sz in (-1, 1):
        can.box((0, 96.5, sz * 72), (100, 3, 4), W)
    roof = tex.alt(tex.fabric(PINK, "#f3d2df", stripe_w=6, glow=0.08), nightmare=tex.fabric(MAUVE, BURG, stripe_w=6))
    can.box((0, 99, 0), (96, 1, 144), roof)
    can.box((0, 101, 0), (60, 3, 100), roof, variant=1)
    can.box((0, 104, 0), (28, 3, 50), roof, variant=2)
    can.box((0, 107.5, 0), (5, 4, 5), G)
    val = tex.alt(scallop(PINK, "#f6dbe6", "valance"), nightmare=scallop(MAUVE, BURG, "valancen"))
    for sx in (-1, 1):
        can.plane("x", (sx * 50.5, 90, 0), 148, 10, val)
    for sz in (-1, 1):
        can.plane("z", (0, 90, sz * 74.5), 100, 10, val)
    # curtains: eight ribbon chains streaming in an unfelt wind
    cur = tex.alt(tex.fabric("#fff4f6", "#f8e2ea", stripe_w=3, glow=0.12, a=0.8, mode="blend"),
                  nightmare=tex.fabric("#6a4a6e", "#4a3456", stripe_w=3, a=0.8, mode="blend"))
    cur_e = tex.alt(tex.fabric("#fff4f6", "#f8e2ea", stripe_w=3, glow=0.12, a=0.8, mode="blend", fringe=True),
                    nightmare=tex.fabric("#6a4a6e", "#4a3456", stripe_w=3, a=0.8, mode="blend", fringe=True))
    curtains = []
    for i, (x, z, ax, sgn) in enumerate([(-51, -60, "x", 1), (51, -60, "x", 1), (-51, 60, "x", -1), (51, 60, "x", -1),
                                         (-38, -76, "z", 1), (38, -76, "z", -1), (-38, 76, "z", 1), (38, 76, "z", -1)]):
        par = can
        chain = []
        for s in range(4):
            y1 = 95 - s * 24
            b = m.bone(f"curtain{i + 1}_{s + 1}", par, pivot=(x, y1, z))
            b.plane(ax, (x, y1 - 12, z), 24, 24.5, cur_e if s == 3 else cur, variant=(i + s) % 3)
            par = b
            chain.append(b.name)
        curtains.append((chain, ax, x, z))
    # blanket edges spilling over the sides
    bed_e = tex.alt(quilt(PBLUE, "#e9f2fb", SGOLD, fringe=True, key="bedqe"),
                    nightmare=quilt(INDIGO, "#4a3e6a", BURG, fringe=True, key="bedqen"))
    spills = []
    for i, (x, z, ax) in enumerate([(-45.5, -52, "x"), (-45.5, -18, "x"), (-45.5, 14, "x"), (45.5, -52, "x"),
                                    (45.5, -18, "x"), (45.5, 14, "x"), (-22, -69.5, "z"), (22, -69.5, "z")]):
        par = bed
        chain = []
        for s in range(3):
            y1 = 2 - s * 18
            b = m.bone(f"spill{i + 1}_{s + 1}", par, pivot=(x, y1, z))
            b.plane(ax, (x, y1 - 9, z), 34 if ax == "x" else 44, 18.5, bed_e if s == 2 else blank, variant=(i + s) % 3)
            par = b
            chain.append(b.name)
        spills.append((chain, ax, x))
    # pillows, the sleeper's lump, a floating nightstand
    pl = m.bone("pillow_l", bed, pivot=(-22, 0, 52))
    pillow_geo(pl, -22, 52)
    pr = m.bone("pillow_r", bed, pivot=(22, 0, 52))
    pillow_geo(pr, 22, 52)
    lump = m.bone("lump", bed, pivot=(0, 0, -24))
    lump.box((0, 5, -26), (40, 8, 84), blank, variant=1)
    lump.box((0, 10, -26), (30, 3, 78), blank, variant=2)
    ns = m.bone("nightstand", root, pivot=(66, 10, 58))
    ns.box((66, 10, 58), (14, 16, 12), W)
    ns.box((66, 18.6, 58), (16, 1.2, 14), G)
    ns.box((66, 22, 58), (2, 6, 2), G)
    ns.box((66, 27, 58), (7, 5, 7), lamp_mat())
    ns.plane("z", (66, 9, 51.9), 10, 12, door_mat(PEACH, SGOLD, key="nsdoor"))
    return m, curtains, spills


def bed_anims(curtains, spills):
    A = []
    idle = Anim("drift", loop=True)          # always: the unfelt wind
    for i, (chain, ax, x, z) in enumerate(curtains):
        a = 2 if ax == "x" else 0
        out = (1 if x > 0 else -1) if ax == "x" else (-1 if z < 0 else 1)
        for j, b in enumerate(chain):
            v = [0, 0, 0]
            # billow outward and stream sideways
            v[a] = LIFE(6 + j * 5, 3.1 + i * 0.13, -j * 0.15 + i * 0.07, base=(8 + j * 9) * out * (1 if a == 2 else -1))
            v[1] = LIFE(5 + j * 3, 4.3 + i * 0.2, -j * 0.1)
            idle.rot(b, tuple(v))
    for i, (chain, ax, x) in enumerate(spills):
        a = 2 if ax == "x" else 0
        for j, b in enumerate(chain):
            v = [0, 0, 0]
            v[a] = LIFE(4 + j * 4, 3.4 + i * 0.11, -j * 0.17 + i * 0.09)
            idle.rot(b, tuple(v))
    idle.pos("nightstand", (0, LIFE(3, 4.7), 0))
    idle.rot("nightstand", (LIFE(4, 6.1), spin(12), LIFE(3, 5.3)))
    A.append(idle)
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    flat = {"lump": (1, 0.0, 1)}
    arrive = Anim("arrive", length=2.5, loop="hold")
    arrive.scl("root", {0: 0.05, 1.4: 0.9, 2.0: 1.04, 2.5: 1.0})
    arrive.rot("bed", {0: (0, -60, 14), 1.6: (0, 6, -3), 2.5: (0, 0, 0)})
    arrive.scl("canopy", {0: (0.3, 0.1, 0.3), 1.0: (0.3, 0.1, 0.3), 1.9: (1.06, 1.1, 1.06), 2.5: 1.0})
    arrive.scl("lump", (1, 0.0, 1))
    A.append(arrive)
    bob = Anim("float", loop=True)
    bob.pos("bed", (0, LIFE(2.5, 6.0), 0))
    bob.rot("bed", (LIFE(1.2, 7.3), 0, LIFE(1.5, 8.1, 0.3)))
    bob.scl("lump", (1, 0.0, 1))
    A.append(bob)
    occ = Anim("occupied", length=4.0, loop="hold")     # the blanket rises over the manifesting sleeper
    occ.pos("bed", {0: (0, 0, 0), 1.0: (0, -3, 0), 4.0: (0, -2, 0)})
    occ.scl("lump", {0: (1, 0.0, 1), 0.4: (1, 0.0, 1), 1.4: (1, 1.1, 1), 2.0: (1, 1.0, 1)}, smooth=False)
    A.append(occ)
    dip = Anim("dip", length=2.0, loop="hold")       # the sleeper sits up: the bed takes its weight
    dip.pos("bed", {0: (0, 0, 0), 0.5: (0, -14, 0), 1.0: (0, -8, 0), 1.5: (0, -11, 0), 2.0: (0, -10, 0)})
    dip.rot("bed", {0: (0, 0, 0), 0.5: (9, 0, 2), 1.1: (4, 0, -1), 2.0: (5, 0, 0)})
    dip.scl("pillow_r", {0: 1.0, 0.35: 1.0, 0.45: 0.0}, smooth=False)
    dip.pos("pillow_r", {0: (0, 0, 0), 0.4: (6, 4, -10)})
    A.append(dip)
    empty = Anim("empty", loop=True)
    empty.pos("bed", (0, LIFE(2.5, 6.0, base=-4), 0))
    empty.rot("bed", (LIFE(2, 7.3, base=3), 0, LIFE(1.5, 8.1)))
    empty.scl("lump", (1, 0.0, 1))
    empty.scl("pillow_r", 0.0)
    A.append(empty)
    fold = Anim("fold", length=1.5, loop="hold")     # it folds into a cradle, ready to swing
    fold.scl("lump", (1, 0.0, 1))
    fold.scl("pillow_r", 0.0)
    fold.rot("canopy", {0: (0, 0, 0), 0.8: (0, 90, 0), 1.5: (0, 90, 0)})
    fold.scl("canopy", {0: 1.0, 0.8: (0.9, 1.4, 0.9), 1.5: (0.8, 1.3, 0.8)})
    fold.rot("bed", {0: (0, 0, 0), 0.6: (0, 0, 20), 1.5: (0, 0, SWING_A)})
    fold.rot("nightstand", {0: (0, 0, 0), 1.5: (0, 360, 0)})
    A.append(fold)
    sw = Anim("swing", length=SWING_T, loop="hold")
    keys = {}
    for k in range(25):
        t = SWING_T * k / 24
        keys[round(t, 3)] = (0, 0, SWING_A * math.cos(math.pi * t / SWING_T))
    sw.rot("bed", keys, smooth=False)
    sw.scl("lump", (1, 0.0, 1))
    sw.scl("pillow_r", 0.0)
    sw.rot("canopy", (0, 90, 0))
    sw.scl("canopy", (0.8, 1.3, 0.8))
    A.append(sw)
    van = Anim("vanish", length=2.5, loop="hold")    # folds up into nothing on its way to the book
    van.rot("bed", {0: (0, 0, -SWING_A), 1.0: (0, 180, -10), 2.5: (0, 540, 0)})
    van.scl("root", {0: 1.0, 0.6: 0.8, 2.5: 0.0}, smooth=False)
    van.scl("lump", (1, 0.0, 1))
    van.scl("pillow_r", 0.0)
    van.scl("canopy", {0: (0.8, 1.3, 0.8), 1.0: (0.2, 0.2, 0.2), 1.6: 0.0}, smooth=False)
    A.append(van)
    return A


BED_STATES = {0: ["hidden"], 1: ["arrive"], 2: ["float"], 3: ["occupied"], 4: ["dip"], 5: ["empty"], 6: ["fold"],
              7: ["swing"], 8: ["vanish"]}


# ---------------------------------------------------------------- pillow (Phase II slam)
def pillow_model():
    m = Model("dn_dreamer_pillow", density=1.0, bounds=(10, 6, (0, 1, 0)))
    root = m.bone("root")
    b = m.bone("pillow", root, pivot=(0, 6, 0))
    pillow_geo(b, 0, 0, 0.0, 1.0)
    return m


def pillow_anims():
    tumble = Anim("tumble", loop=True, length=1.2)
    tumble.rot("pillow", (S(30, 1.2), spin(140), S(20, 1.2, 0.25)))
    slam = Anim("slam", length=0.6, loop="hold")
    slam.scl("pillow", {0: 1.0, 0.08: (1.35, 0.45, 1.35), 0.3: (0.95, 1.1, 0.95), 0.6: 1.0})
    fade = Anim("fade", length=0.8, loop="hold")
    fade.scl("root", {0: 1.0, 0.2: 1.08, 0.8: 0.0}, smooth=False)
    fade.pos("root", {0: (0, 0, 0), 0.8: (0, 18, 0)})
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    return [tumble, slam, fade, hidden]


# ---------------------------------------------------------------- codex + page structures
BOOK = (-15.0, 24.0, -13.0)    # where the open book floats, relative to the caster (units)


def paper(c="#fbf4e6", line="#d9cbb0", glow=0.25):
    kc, kl = tex.rgb(c), tex.rgb(line)

    def fn(ctx):
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, c, 1, glow)
        t[..., :3] = np.where(((iy % 3) == 2)[..., None], kl, kc)
        return tex.grain(ctx, t, 0.02)
    return Mat(fn, f"dnb_paper{c}{line}{glow}")


def codex_model():
    m = Model("dn_dreamer_codex", density=2.0, bounds=(8, 5, (0, 1, 0)))
    root = m.bone("root")
    bx, by, bz = BOOK
    book = m.bone("book", root, pivot=BOOK, rot=(-28, 0, 0))
    cov = tex.trimmed(tex.speck("#5d4a86", 0.05, glow=0.05), SGOLD, 1, 1, glow=0.5)
    pg = paper()
    book.box((bx, by, bz - 0.4), (2.2, 19, 2.2), gilt(0.3))         # spine
    for s, sx in (("r", 1), ("l", -1)):
        c = m.bone(f"cover_{s}", book, pivot=(bx, by, bz))
        c.cube((bx if sx > 0 else bx - 14, by - 9.5, bz - 1.2), (14, 19, 0.8), cov)
        c.cube((bx + (0.6 if sx > 0 else -13.4), by - 8.5, bz - 0.4), (12.8, 17, 1.6), pg, variant=1 if sx > 0 else 0)
        c.box((bx + sx * 7, by, bz - 1.4), (4, 4, 0.4), tex.shaped(tex.m_crescent(0.4), SGOLD, "#fff3c8", glow=0.9,
                                                                   key="covermoon"), faces=("north",))
    inl = m.bone("inlay", "cover_r", pivot=(bx + 7, by, bz - 1.6))
    inl.box((bx + 7, by - 3, bz - 2.2), (8, 0.6, 1.4), tex.flat("#c98aa4", glow=0.4))
    inl.plane("z", (bx + 7, by + 0.5, bz - 1.65), 8, 8, wallpaper(PINK, "#f4cfdc", glow=0.6), faces=("north",))
    inl.box((bx + 5.5, by - 2, bz - 2.3), (3.6, 1.4, 1.2), tex.flat("#fff6ea", glow=0.6))
    inl.box((bx + 9.5, by - 1.4, bz - 2.3), (1.2, 1.2, 1.2), lamp_mat())
    inl.plane("z", (bx + 8.5, by + 2.2, bz - 1.7), 2.4, 2.8, window_mat(), faces=("north",))
    for k in range(4):     # loose pages that flip and separate
        p = m.bone(f"page{k + 1}", book, pivot=(bx, by, bz))
        p.plane("z", (bx + 6.5, by, bz - 0.3 - k * 0.1), 12.5, 16.5, pg, variant=k % 2)
    orb = m.bone("orbit", root)
    kinds = ["door", "window", "stair", "arch", "house", "moon"]
    for k, kind in enumerate(kinds):
        a = math.radians(k * 60 + 15)
        r = 34 + (k % 2) * 6
        x, y, z = math.cos(a) * r, 14 + (k % 3) * 9, math.sin(a) * r
        b = m.bone(f"ps{k + 1}", orb, pivot=(x, y, z))
        ink = tex.trimmed(paper(glow=0.35), "#8a6ad6", 1, 0, glow=0.6)
        if kind == "door":
            b.box((x, y, z), (6, 10, 0.6), ink)
            b.plane("z", (x, y, z - 0.35), 4.4, 8.4, door_mat("#fff8ec", "#8a6ad6", glass="#ffe7b0", key="pdoor"),
                    faces=("north",))
        elif kind == "window":
            b.box((x, y, z), (7, 7, 0.6), window_mat("#ffe7b0", "#8a6ad6", "#fbf4e6"))
        elif kind == "stair":
            for j in range(5):
                b.box((x - 4 + j * 2, y - 4 + j * 1.6, z), (2.2, 1.6 + j * 1.6 * 0, 3), ink, variant=j % 2)
        elif kind == "arch":
            from .dn_dreamer import arch_mat
            b.plane("z", (x, y, z), 8, 9, arch_mat("#fbf4e6", "#efe4d0", "#8a6ad6", key="parch", glow=0.3))
        elif kind == "house":
            b.box((x, y, z), (6, 5, 5), window_mat("#ffe7b0", "#8a6ad6", "#fbf4e6", arch=False))
            b.box((x, y + 3.4, z), (4.6, 1.8, 5.4), ink, rot=(0, 0, 45))
        else:
            b.plane("z", (x, y, z), 6, 6, tex.shaped(tex.m_crescent(0.4), "#fff3c8", PEACH, glow=1.0, key="pmoon"))
    return m


def codex_anims():
    bx, by, bz = BOOK
    A = []
    turn = Anim("turn", loop=True)
    turn.rot("orbit", (0, spin(22), 0))
    for k in range(6):
        turn.pos(f"ps{k + 1}", (0, LIFE(2.0, 3.0 + k * 0.4, k * 0.17), 0))
        turn.rot(f"ps{k + 1}", (LIFE(8, 4.1, k * 0.2), spin(-40 - k * 5), 0))
    turn.pos("book", (0, LIFE(0.8, 3.3), 0))
    A.append(turn)
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    closed = {"cover_r": (0, 90, 0), "cover_l": (0, -90, 0)}
    flat = {"cover_r": (0, 0, 0), "cover_l": (0, 0, 0)}
    op = Anim("open", length=3.0, loop="hold")      # opens completely, pages separate into structures
    op.scl("book", {0: 0.0, 0.4: 1.15, 0.6: 1.0})
    for b in ("cover_r", "cover_l"):
        op.rot(b, {0: closed[b], 0.5: closed[b], 1.2: tuple(c * -0.08 for c in closed[b]), 1.4: flat[b]})
    for k in range(4):
        t0 = 1.2 + k * 0.22
        op.rot(f"page{k + 1}", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.35: (0, 120, 0)})
        op.pos(f"page{k + 1}", {0: (0, 0, 0), t0 + 0.2: (0, 0, 0), t0 + 0.7: (0, 16, 8)})
        op.scl(f"page{k + 1}", {0: 1.0, t0 + 0.4: 1.0, t0 + 0.75: 0.0}, smooth=False)
    for k in range(6):
        t0 = 1.5 + k * 0.18
        op.scl(f"ps{k + 1}", {0: 0.0, t0: 0.0, t0 + 0.45: 1.2, t0 + 0.6: 1.0}, smooth=False)
    op.scl("inlay", 0.0)
    A.append(op)
    orb = Anim("hold", loop=True)
    orb.rot("cover_r", flat["cover_r"])
    orb.scl("inlay", 0.0)
    for k in range(4):
        orb.scl(f"page{k + 1}", 0.0)
    A.append(orb)
    ga = Anim("gather", length=2.0, loop="hold")    # the structures fold back into pages
    for k in range(6):
        t0 = k * 0.15
        ga.scl(f"ps{k + 1}", {0: 1.0, t0 + 0.6: 1.0, t0 + 1.0: 0.0}, smooth=False)
    ga.rot("orbit", {0: (0, 0, 0), 1.6: (0, 300, 0)})
    for k in range(4):
        t0 = 0.8 + k * 0.2
        ga.scl(f"page{k + 1}", {0: 0.0, t0: 0.0, t0 + 0.2: 1.0}, smooth=False)
    ga.scl("inlay", 0.0)
    A.append(ga)
    cl = Anim("close", length=2.6, loop="hold")     # the bedroom is embedded in the cover; the book closes
    for b in ("cover_r", "cover_l"):
        cl.rot(b, {0: flat[b], 0.6: flat[b], 1.0: tuple(c * 0.85 for c in closed[b]), 1.15: closed[b]})
    cl.scl("inlay", {0: 0.0, 0.2: 0.0, 0.5: 1.3, 0.7: 1.0})
    cl.scl("orbit", 0.0)
    cl.rot("book", {0: (0, 0, 0), 1.2: (0, 0, 0), 1.6: (0, -90, 0), 2.6: (0, -90, 0)})
    cl.scl("book", {0: 1.0, 1.9: 1.0, 2.1: 1.12, 2.6: 0.0}, smooth=False)
    A.append(cl)
    return A


CODEX_STATES = {0: ["hidden"], 1: ["open"], 2: ["hold"], 3: ["gather"], 4: ["close"]}


# ---------------------------------------------------------------- miniature bedroom
def bedroom_model():
    m = Model("dn_dreamer_bedroom", density=4.0, bounds=(6, 6, (0, 1, 0)))
    root = m.bone("root")
    r = m.bone("room", root, pivot=(0, 0, 0))
    W = tex.wood("#e9d6b8", "#b8946a", plank=2)
    r.box((0, 0.4, 0), (16, 0.8, 16), W)
    r.plane("y", (0, 0.85, 0), 10, 10, tex.fabric("#c98aa4", SGOLD, stripe_w=1, glow=0.2), faces=("up",))
    r.box((0, 8.8, 7.6), (16, 16, 0.8), wallpaper(PINK, "#f4cfdc", glow=0.35))
    r.box((-7.6, 8.8, 0), (0.8, 16, 15.2), wallpaper(PBLUE, "#d9e8f7", glow=0.35))
    r.plane("z", (3, 10, 7.1), 4, 5, window_mat(), faces=("north",))
    r.plane("x", (-7.1, 6, -3), 4, 7, door_mat(PEACH, SGOLD, glass="#fff0c8", key="mbdoor"), faces=("east",))
    r.box((-1, 2.4, 3.5), (9, 2.4, 6), tex.flat("#fff6ea", glow=0.25))
    r.box((-1.5, 3.8, 3.3), (7, 0.6, 6.2), tex.fabric(PINK, "#f6d9e4", stripe_w=1, glow=0.25))
    r.box((-1, 4.4, 6.5), (9, 4, 0.8), W)
    r.box((5.5, 2.5, 5.5), (2.4, 3.4, 2.4), W)
    r.box((5.5, 5.5, 5.5), (2.6, 2, 2.6), lamp_mat())
    for k, (x, z) in enumerate(((-7.6, 7.6), (7.6, 7.6), (-7.6, -7.6))):
        r.box((x, 8.8, z), (1, 16.4, 1), gilt(0.3))
    r.box((0, 17, 0.5), (17, 1, 16), tex.fabric(PINK, "#f3d2df", stripe_w=2, glow=0.15))
    return m


def bedroom_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    appear = Anim("appear", length=0.8, loop="hold")
    appear.scl("room", {0: 0.0, 0.5: 1.15, 0.8: 1.0})
    appear.rot("room", {0: (0, -180, 0), 0.8: (0, 0, 0)})
    flt = Anim("float", loop=True)
    flt.rot("room", (LIFE(6, 3.2), spin(30), LIFE(4, 2.7)))
    flt.pos("room", (0, LIFE(1.0, 2.0), 0))
    settle = Anim("settle", length=0.9, loop="hold")
    settle.scl("room", {0: 1.0, 0.25: 1.2, 0.9: 0.0}, smooth=False)
    settle.rot("room", {0: (0, 0, 0), 0.9: (0, 270, 0)})
    return [hidden, appear, flt, settle]


# ---------------------------------------------------------------- mark (sleeping moon tag)
def mark_model():
    m = Model("dn_dreamer_mark", density=4.0, bounds=(3, 3, (0, 1, 0)), alts=("awake",))
    root = m.bone("root")
    tag = m.bone("tag", root, pivot=(0, 6, 0))

    def moon(awake):
        def fn(ctx):
            u, v = ctx.U * 2 - 1, 1 - ctx.V * 2
            r = np.hypot(u, v)
            disc = (r < 0.92) & (np.hypot(u - 0.42, v - 0.1) > 0.7)
            t = tex.tile(ctx, "#fff3c8", 1, 0.9)
            c = tex.rgb("#2a2d52") if awake else tex.rgb(SGOLD)
            t[..., :3] = tex.mix(tex.rgb("#fff3c8"), tex.rgb(PEACH), np.clip(r, 0, 1)[..., None])
            if awake:
                t[..., :3] = tex.mix(tex.rgb("#b8a6d6"), tex.rgb("#6a4a6e"), np.clip(r, 0, 1)[..., None])
            lid = (np.abs(v + 0.05 - 0.18 * (u + 0.35) ** 2) < 0.07) & (u > -0.75) & (u < 0.05)
            lash = (np.abs(u + 0.35 - 0.0) < 0.5) & (v < -0.05) & (v > -0.3) & (np.abs(((u + 0.75) * 6) % 1 - 0.5) < 0.12)
            if awake:
                eye = np.hypot((u + 0.33) / 0.32, (v + 0.02) / 0.2) < 1
                t[..., :3] = np.where(eye[..., None], tex.rgb("#f3e3b0"), t[..., :3])
                pup = np.hypot(u + 0.33, v + 0.02) < 0.09
                t[..., :3] = np.where(pup[..., None], tex.rgb("#6e2f3a"), t[..., :3])
            else:
                t[..., :3] = np.where((lid | lash)[..., None], c, t[..., :3])
            t[..., 3] = np.where(disc, 1.0, 0.0)
            return t
        return Mat(fn, f"dnb_markmoon{awake}", directional=True)
    mm = tex.alt(moon(False), awake=moon(True))
    tag.plane("z", (0, 6, 0), 6, 6, mm)
    tag.plane("x", (0, 6, 0), 6, 6, mm)
    st = tex.alt(tex.bitmap_cut(glyphs.DREAM["star"], "#fff3c8", glow=1.0, color2=PEACH),
                 awake=tex.bitmap_cut(glyphs.DREAM["eye"], "#f3e3b0", glow=1.0, color2="#8e3446"))
    tag.box((0, 2, 0), (0.3, 2, 0.3), gilt(0.5))
    tag.box((0, 0.6, 0), (2, 2, 0), st, faces=("north", "south"))
    return m


def mark_anims():
    turn = Anim("turn", loop=True)
    turn.rot("tag", (LIFE(8, 2.6), spin(70), 0))
    turn.pos("tag", (0, LIFE(0.8, 1.9), 0))
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    appear = Anim("appear", length=0.5, loop="hold")
    appear.scl("root", {0: 0.0, 0.3: 1.35, 0.5: 1.0})
    hold = Anim("hold", loop=True)
    pop = Anim("pop", length=0.4, loop="hold")
    pop.scl("root", {0: 1.0, 0.15: 1.8, 0.4: 0.0}, smooth=False)
    return [turn, hidden, appear, hold, pop]


# ---------------------------------------------------------------- domain
def domain_model():
    m = Model("dn_dreamer_domain", density=2.0, bounds=(48, 14, (0, 3, 0)), alts=("nightmare",))
    root = m.bone("root")

    def circ(c0, c1, **kw):
        return tex.magic_circle(DREAMG, c0, c1, **kw)
    outer = m.bone("outer", root)
    outer.plane("y", (0, 0.3, 0), 66, 66, tex.alt(circ("#ffe9f2", "#bcd6f0", bands=((0.86, 0.97, 22),), lines=(0.84, 0.99)),
                                                 nightmare=circ("#b8a6d6", "#8e3446", bands=((0.86, 0.97, 22),), lines=(0.84, 0.99))),
                faces=("up", "down"))
    mid = m.bone("mid", root)
    mid.plane("y", (0, 0.45, 0), 40, 40, tex.alt(circ("#fff3c8", PEACH, bands=((0.72, 0.9, 12),), lines=(0.7, 0.94), star=8,
                                                     star_r=(0.3, 0.68)),
                                                nightmare=circ("#8b8f9a", "#6a4a6e", bands=((0.72, 0.9, 12),), lines=(0.7, 0.94),
                                                               star=8, star_r=(0.3, 0.68))), faces=("up", "down"))
    posts = m.bone("posts", root)
    pm = tex.alt(gilt(0.3), nightmare=tex.flat("#4a3e6a"))
    lm = tex.alt(tex.shaped(tex.m_crescent(0.4), "#fff3c8", PEACH, glow=1.0, key="dlamp"),
                 nightmare=tex.shaped(tex.m_disc(0.8), "#f3e3b0", "#8e3446", glow=1.0, key="dlampn"))
    for k in range(8):
        a = math.radians(k * 45)
        x, z = math.cos(a) * 31, math.sin(a) * 31
        b = m.bone(f"post{k + 1}", posts, pivot=(x, 0, z))
        b.box((x, 4, z), (0.5, 8, 0.5), pm)
        b.box((x, 8.2, z), (1.4, 0.4, 1.4), pm)
        b.plane("z", (x, 9.6, z), 2.2, 2.2, lm, rot=(0, -k * 45 + 90, 0), pivot=(x, 9.6, z))
    return m


def domain_anims():
    spin_ = Anim("spin", loop=True)
    spin_.rot("outer", (0, spin(4), 0))
    spin_.rot("mid", (0, spin(-7), 0))
    for k in range(8):
        spin_.pos(f"post{k + 1}", (0, LIFE(0.25, 3.0 + k * 0.2, k * 0.13), 0))
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    form = Anim("form", length=1.6, loop="hold")
    form.scl("outer", {0: 0.0, 0.9: 1.04, 1.2: 1.0})
    form.scl("mid", {0: 0.0, 0.4: 0.0, 1.2: 1.06, 1.6: 1.0})
    for k in range(8):
        form.scl(f"post{k + 1}", {0: (1, 0, 1), 0.6 + k * 0.1: (1, 0, 1), 0.9 + k * 0.1: (1, 1.1, 1), 1.0 + k * 0.1: 1.0},
                 smooth=False)
    hold = Anim("hold", loop=True)
    shrink = Anim("shrink", length=1.6, loop="hold")
    shrink.scl("root", {0: 1.0, 0.3: 1.04, 1.6: 0.0}, smooth=False)
    shrink.rot("root", {0: (0, 0, 0), 1.6: (0, 120, 0)})
    return [spin_, hidden, form, hold, shrink]


def build(pack):
    m, curtains, spills = bed_model()
    ba = bed_anims(curtains, spills)
    pack.actor("dn_dreamer_bed", m, ba, BED_STATES, always=["drift"], scale=BED_SCALE, lifetime=120,
               display="The Bed Above the Sky", blend=0.3)
    by = {a.name: a for a in ba}
    pack.preview("dn_dreamer_bed", m, [[(by["float"], 0.0), (by["drift"], 1.3)], [(by["swing"], 0.3), (by["drift"], 2.0)]],
                 views=((30, 20), (-60, 15), (0, 70)), cell=(420, 420))
    print(f"    bed: {m.cube_count()} cubes, {len(m.order)} bones, tex {m.tex_size}")
    pm = pillow_model()
    pack.actor("dn_dreamer_pillow", pm, pillow_anims(), {0: ["hidden"], 1: ["tumble"], 2: ["slam"], 3: ["fade"]},
               scale=BED_SCALE, lifetime=60, display="Dropped Pillow")
    cm = codex_model()
    ca = codex_anims()
    pack.actor("dn_dreamer_codex", cm, ca, CODEX_STATES, always=["turn"], lifetime=120, display="The Unawakened Codex")
    cb = {a.name: a for a in ca}
    pack.preview("dn_dreamer_codex", cm, [[(cb["hold"], 0), (cb["turn"], 1.0)], [(cb["close"], 0.8)]],
                 views=((160, 25), (30, 30)), cell=(380, 380))
    rm = bedroom_model()
    pack.actor("dn_dreamer_bedroom", rm, bedroom_anims(), {0: ["hidden"], 1: ["appear"], 2: ["float"], 3: ["settle"]},
               size_prop=True, lifetime=60, display="The Forgotten Morning")
    mk = mark_model()
    pack.actor("dn_dreamer_mark", mk, mark_anims(), {0: ["hidden"], 1: ["appear"], 2: ["hold"], 3: ["pop"]},
               always=["turn"], lifetime=120, display="Sleeping Moon", blend=0.0)
    dm = domain_model()
    da = domain_anims()
    pack.actor("dn_dreamer_domain", dm, da, {0: ["hidden"], 1: ["form"], 2: ["hold"], 3: ["shrink"]}, always=["spin"],
               size_prop=True, lifetime=120, display="Dream Domain", blend=0.0)
    pack.preview("dn_dreamer_small", rm, [None], views=((150, 30), (210, 25)), cell=(300, 300))
    pack.preview("dn_dreamer_mark", mk, [None], views=((20, 10), (20, 10)), cell=(200, 200), skin="awake")
