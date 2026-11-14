"""DW06 -- the seven law tablets (Phase III) and the descending lines of sacred text (Phase IV).

dw6_tablet : kinds 0-6, one per law.  Each has its own silhouette, border, emblem and motion:
             I Containment (castellated square, turning ring of inward arrows)
             II Station (ziggurat stele between colonnettes, three sliding columns)
             III Direction (lancet, chevron border, scrolling lines + arrowhead)
             IV Stillness (lapis disc, silver pinned star, a ring that barely moves)
             V Refuge (round-topped shield framed by sheltering feathers, breathing heart)
             VI Sequence (polyptych of four panels that light one after another)
             VII Judgment (pedimented slab, sunburst, gliding sword of text)
dw6_line   : kinds 0-4 lines of extruded glyphs: 0 straight line (sweep), 1 ring (expanding),
             2 lattice (checkerboard of columns), 3 spiral (converging), 4 the white-gold formation
"""
import math

from kit import tex
from kit.anim import LIFE, Anim
from kit.geo import Model, ring

from .dw6_common import BLUE, FW, GOLD, SILVER, WGOLD, extrude, gold_metal, spin, text_band

TABLET_STATES = {0: ["hidden"], 1: ["form"], 2: ["idle"], 3: ["declare"], 4: ["shed"], 5: ["return"]}
TABLET_SCALE = 1.9         # the tablets hang ~33 m away, above the written temple (tops ~15 degrees up)
LINE_STATES = {0: ["hidden"], 1: ["assemble"], 2: ["hold"], 3: ["strike"], 4: ["unwrite"]}

MARBLE = tex.marble("#f6f1e4", "#cbbf9f", vein2="#d9b45a", scale=6)
LAPIS = tex.marble("#2b3f8f", "#1b275c", vein2="#d8dde3", scale=5)
GOLD_M = gold_metal(0.35)
GOLD_HOT = tex.metal("#ffe08a", "#ffffff", "#c9a24a", bands=2.0, glow=0.85)
SILV = tex.metal("#d8dde3", "#ffffff", "#8a93a6", bands=2.0, glow=0.5)
HALO = tex.shaped(tex.m_ring(0.55, 1.0), "#fff3c4", "#e9c15a", glow=1.0, var=0, a=0.32, mode="blend", key="dw6tabhalo")


def _glyph_plate(code, color=WGOLD):
    return tex.bitmap_cut(FW[code % len(FW)], color, glow=1.0, color2="#ffffff")


def _tablet_base(kind, w, h, y0=4, mat=None, header=None):
    m = Model(f"dw6_tablet{kind}", density=1.0, bounds=(10, 12, (0, 3, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, y0 + h / 2, 0))
    halo = m.bone("halo", body, pivot=(0, y0 + h / 2, 4))
    halo.plane("z", (0, y0 + h / 2, 4), max(w, h) * 1.25, max(w, h) * 1.25, HALO)
    insc = m.bone("insc", body, pivot=(0, y0 + 6, -2.6))
    insc.plane("z", (0, y0 + 6, -2.6), w - 6, 7, text_band(seed=30 + kind))
    hb = m.bone("head", body, pivot=(0, y0 + h, 0))
    if header is not None:
        hb.box((0, y0 + h + 6, -0.5), (6, 8.4, 0), _glyph_plate(header), faces=("north", "south"))
    return m, root, body


def tablet(kind):
    T = [_t_containment, _t_station, _t_direction, _t_stillness, _t_refuge, _t_sequence, _t_judgment][kind]
    return T()


def _t_containment():
    m, root, body = _tablet_base(0, 32, 32, header=1)
    body.box((0, 20, 0), (32, 32, 4), MARBLE)
    for k in range(8):                                                # crenellated border
        for (x, y) in ((-14 + k * 4, 37.5), (-14 + k * 4, 2.5)):
            if k % 2 == 0:
                body.box((x, y, 0), (3.6, 3, 4.6), GOLD_M, variant=k % 2)
        body.box((-17.5, 6 + k * 4, 0), (3, 2.4 if k % 2 else 3.6, 4.6), GOLD_M)
        body.box((17.5, 6 + k * 4, 0), (3, 2.4 if k % 2 else 3.6, 4.6), GOLD_M)
    emb = m.bone("emb", body, pivot=(0, 22, -2.2))
    sp = m.bone("m_spin", emb, pivot=(0, 22, -2.2))
    sp.plane("z", (0, 22, -2.3), 22, 22, tex.magic_circle(FW, WGOLD, GOLD, bands=((0.72, 0.93, 12),), lines=(0.68, 0.97)))
    for k in range(4):
        a = k * 90
        sp.box((0, 22 + 6.5, -3), (3.2, 3.2, 1.2), GOLD_HOT, rot=(0, 0, 45), pivot=(0, 22, -3))
        sp.cubes[-1].rot = (0, 0, a + 45)
    emb.box((0, 22, -3.2), (5, 5, 1), tex.glow_flat("#ffffff", 1.0), rot=(0, 0, 45))
    return m


def _t_station():
    m, root, body = _tablet_base(1, 22, 40, header=3)
    body.box((0, 24, 0), (22, 40, 4), MARBLE)
    for j, (w, y) in enumerate(((18, 45), (13, 48), (8, 51))):       # ziggurat steps
        body.box((0, y, 0), (w, 3, 4), GOLD_M if j % 2 else MARBLE)
    for sx in (-1, 1):                                                # colonnettes
        body.box((sx * 13, 24, -0.5), (2.6, 38, 2.6), MARBLE, variant=1)
        body.box((sx * 13, 44, -0.5), (4, 2, 4), GOLD_M)
        body.box((sx * 13, 4, -0.5), (4, 2, 4), GOLD_M)
    emb = m.bone("emb", body, pivot=(0, 26, -2.2))
    emb.box((0, 19, -2.6), (18, 1.4, 1.2), GOLD_M)
    for k in range(3):
        b = m.bone(f"m_slide{k + 1}", emb, pivot=(-6 + k * 6, 20, -3))
        b.box((-6 + k * 6, 26, -3.2), (2.6, 12, 2.6), tex.glow_flat("#fffbe8", 0.9, core="#ffffff"))
        b.box((-6 + k * 6, 32.6, -3.2), (4, 1.4, 4), GOLD_HOT)
        b.box((-6 + k * 6, 19.8, -3.2), (4, 1.4, 4), GOLD_HOT)
    return m


def _t_direction():
    m, root, body = _tablet_base(2, 26, 32, header=5)
    body.box((0, 20, 0), (26, 32, 4), MARBLE)
    for sx in (-1, 1):                                                # lancet point
        body.box((sx * 6.2, 39, 0), (14, 4, 4), MARBLE, rot=(0, 0, -sx * 34), variant=1)
        body.box((sx * 6.6, 41.6, 0), (14.4, 1.2, 4.6), GOLD_M, rot=(0, 0, -sx * 34))
    for k in range(6):                                                # chevron border
        for sx in (-1, 1):
            body.box((sx * 14, 6 + k * 5.5, -0.3), (3, 1.2, 4.6), GOLD_M, rot=(0, 0, sx * 35))
    emb = m.bone("emb", body, pivot=(0, 24, -2.2))
    sc = m.bone("m_scroll", emb, pivot=(0, 24, -2.6))
    for j in range(3):
        sc.plane("z", (-1, 18 + j * 5.5, -2.6), 18, 3.6, text_band(seed=40 + j), variant=j)
    ar = m.bone("m_arrow", emb, pivot=(9, 23.5, -3))
    for sy_ in (-1, 1):
        ar.box((8, 23.5 + sy_ * 2.4, -3), (6, 1.8, 1.4), GOLD_HOT, rot=(0, 0, -sy_ * 40))
    return m


def _t_stillness():
    m, root, body = _tablet_base(3, 32, 32, header=7)
    body.box((0, 20, 0), (28, 28, 4), LAPIS)
    body.box((0, 20, 0), (28, 28, 4), LAPIS, rot=(0, 0, 45), pivot=(0, 20, 0))
    st = m.bone("m_still", body, pivot=(0, 20, 0))
    ring(st, (0, 20, -0.4), 18.5, 20, (6.2, 2.2, 4.4), SILV, axis="z", cycle=2)
    for k in range(10):
        a = math.radians(k * 36)
        st.box((15.5 * math.cos(a), 20 + 15.5 * math.sin(a), -2.4), (3, 4.2, 0), _glyph_plate(k * 3 + 2, "#e8eeff"),
               rot=(0, 0, k * 36 - 90), faces=("north", "south"))
    emb = m.bone("emb", body, pivot=(0, 20, -2.2))
    emb.plane("z", (0, 20, -2.5), 18, 18, tex.shaped(tex.m_star(4, 0.32), "#ffffff", SILVER, glow=0.9, outline="#8a93a6",
                                                       key="dw6star4"))
    emb.box((0, 20, -3.2), (1.6, 14, 1.2), tex.metal(BLUE, "#6f86d6", "#141c40", glow=0.4))
    emb.box((0, 20, -3.2), (8, 1.6, 1.2), tex.metal(BLUE, "#6f86d6", "#141c40", glow=0.4))
    emb.box((0, 20, -3.8), (3, 3, 1), GOLD_HOT, rot=(0, 0, 45))
    return m


def _t_refuge():
    m, root, body = _tablet_base(4, 28, 34, header=9)
    body.box((0, 17, 0), (28, 26, 4), MARBLE)
    body.plane("z", (0, 30, -2.01), 28, 28, tex.shaped(lambda u, v: (((u * u + v * v) <= 1.0) & (v >= 0)).astype(float), "#f6f1e4", "#e2d6b8",
                                                          outline=GOLD, glow=0.1, key="dw6arch"))
    body.plane("z", (0, 30, 2.01), 28, 28, tex.shaped(lambda u, v: (((u * u + v * v) <= 1.0) & (v >= 0)).astype(float), "#f6f1e4", "#e2d6b8",
                                                         outline=GOLD, glow=0.1, key="dw6arch"))
    fm = tex.feather("#fffdf6", "#f3e3a8", GOLD, glow=0.2, glow_tip=0.6)
    for k in range(9):                                                # sheltering feathers around the arch
        a = -80 + k * 20
        body.box((0, 30 + 16, 1.5), (5, 12, 0), fm, rot=(0, 0, a), pivot=(0, 30, 1.5), variant=k % 3)
    emb = m.bone("emb", body, pivot=(0, 22, -2.2))
    emb.plane("z", (0, 24, -2.4), 18, 18, tex.shaped(tex.m_ring(0.82, 1.0), WGOLD, GOLD, glow=0.9, key="dw6domering"))
    emb.box((0, 18.2, -2.6), (20, 1.4, 1.2), GOLD_M)
    br = m.bone("m_breath", emb, pivot=(0, 23, -3))
    br.plane("z", (0, 23, -3), 8, 8, tex.shaped(tex.m_leaf(), "#ffffff", "#ffd060", glow=1.0, var=0, key="dw6heart"))
    return m


def _t_sequence():
    m, root, body = _tablet_base(5, 24, 44, header=11)
    body.box((0, 26, 0), (24, 44, 4), MARBLE)
    body.box((0, 48.6, 0), (26, 1.4, 5), GOLD_M)
    body.box((0, 3.4, 0), (26, 1.4, 5), GOLD_M)
    for sx in (-1, 1):
        body.box((sx * 12.6, 26, 0), (1.4, 44, 5), GOLD_M)
    emb = m.bone("emb", body, pivot=(0, 28, -2.2))
    for k in range(4):
        y = 41 - k * 10
        b = m.bone(f"m_seq{k + 1}", emb, pivot=(0, y, -2.6))
        b.box((0, y, -2.4), (18, 8.4, 0.6), tex.trimmed(tex.flat("#e9dfc3", glow=0.2), GOLD, 1, 0, glow=0.8))
        b.box((0, y, -2.9), (5, 7, 0), _glyph_plate(2 + k * 4), faces=("north", "south"))
    return m


def _t_judgment():
    m, root, body = _tablet_base(6, 34, 40, header=13)
    rays = m.bone("m_rays", body, pivot=(0, 26, 1.5))
    for k in range(12):
        rays.box((0, 26 + 17, 2.4), (1.6, 20, 0.8), GOLD_HOT, rot=(0, 0, k * 30), pivot=(0, 26, 2.4))
    body.box((0, 24, 0), (34, 40, 4), MARBLE)
    body.box((0, 24, -2.05), (14, 34, 0), tex.flat(BLUE, glow=0.25), faces=("north",))
    for j, (w, y) in enumerate(((38, 45.5), (28, 49), (18, 52.5), (8, 56))):   # pediment
        body.box((0, y, 0), (w, 3.5, 4.4), GOLD_M if j % 2 == 0 else MARBLE)
    emb = m.bone("emb", body, pivot=(0, 24, -2.2))
    sw = m.bone("m_sword", emb, pivot=(0, 24, -2.6))
    sw.plane("z", (0, 22, -2.6), 4.5, 26, tex.glyph_rows(FW, "#ffffff", glow=1.0, color2=WGOLD, fill=0.95, key="dw6sword"))
    sw.box((0, 35.5, -2.8), (11, 1.6, 1.2), GOLD_HOT)
    sw.box((0, 38, -2.8), (2.4, 3.6, 1.2), GOLD_HOT)
    sw.box((0, 7.5, -2.8), (2.8, 2.8, 1.2), GOLD_HOT, rot=(0, 0, 45))
    return m


def tablet_anims():
    A = []
    idle = Anim("idle", loop=True)
    idle.pos("body", (0, LIFE(1.4, 4.2), 0))
    idle.rot("m_spin", (0, 0, spin(28)))
    for k in range(3):
        idle.pos(f"m_slide{k + 1}", (LIFE(2.4, 2.6, k * 0.33), 0, 0))
    idle.pos("m_scroll", (LIFE(2.0, 1.4), 0, 0))
    idle.scl("m_arrow", LIFE(0.18, 0.7, base=1.05))
    idle.rot("m_still", (0, 0, spin(3)))
    idle.scl("m_breath", LIFE(0.14, 2.4, base=1.0))
    for k in range(4):
        idle.scl(f"m_seq{k + 1}", (1, 1, 1))
        idle.pos(f"m_seq{k + 1}", (0, 0, LIFE(0.7, 2.0, -k * 0.25, -0.3)))
    idle.rot("m_rays", (0, 0, spin(-12)))
    idle.pos("m_sword", (0, LIFE(1.6, 3.0), 0))
    idle.scl("halo", 0.0)
    A.append(idle)
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    form = Anim("form", length=1.0, loop="hold")
    form.scl("body", {0: (1.0, 0.04, 0.3), 0.45: (1.05, 1.1, 1.0), 0.7: (1.0, 1.0, 1.0)})
    form.scl("emb", {0: 0.0, 0.45: 0.0, 0.8: 1.15, 1.0: 1.0})
    form.scl("halo", {0: 0.0, 0.2: 1.4, 0.7: 0.0})
    A.append(form)
    declare = Anim("declare", length=1.6, loop="hold")
    declare.pos("body", {0: (0, 0, 0), 0.3: (0, -2.5, 0), 0.7: (0, 9, 0), 1.6: (0, 7, 0)})
    declare.scl("emb", {0: 1.0, 0.3: 0.9, 0.7: 1.65, 1.0: 1.2, 1.6: 1.25})
    declare.scl("halo", {0: 0.0, 0.6: 0.0, 0.8: 1.5, 1.6: 1.1})
    declare.rot("halo", {0: (0, 0, 0), 1.6: (0, 0, 90)})
    declare.scl("head", {0: 1.0, 0.7: 1.8, 1.6: 1.4})
    declare.rot("m_spin", (0, 0, spin(140)))
    declare.rot("m_rays", (0, 0, spin(-60)))
    for k in range(4):
        t = 0.3 + 0.25 * k
        declare.scl(f"m_seq{k + 1}", {0: 1.0, t: 1.0, t + 0.1: 1.25, t + 0.3: 1.05})
    A.append(declare)
    shed = Anim("shed", length=1.4, loop="hold")             # the letters detach from the stone
    shed.pos("insc", {0: (0, 0, 0), 0.4: (0, 2, -6), 1.4: (0, -10, -40)})
    shed.scl("insc", {0: 1.0, 0.4: 1.3, 1.2: 2.2, 1.4: 0.0})
    shed.pos("body", (0, LIFE(1.4, 4.2), 0))
    shed.scl("halo", {0: 0.0, 0.3: 1.2, 1.4: 0.0})
    shed.scl("head", {0: 1.0, 0.5: 1.5, 1.4: 1.0})
    A.append(shed)
    ret = Anim("return", length=1.0, loop="hold")            # flatten back into a strip of the page
    ret.scl("body", {0: 1.0, 0.25: (1.05, 1.05, 1.05), 1.0: (1.0, 0.04, 0.2)})
    ret.scl("emb", {0: 1.0, 0.5: 0.0})
    ret.scl("insc", 0.0)
    ret.scl("halo", 0.0)
    A.append(ret)
    return A


# ============================================================================== lines of sacred text
P, D = 2.0, 2.5                       # glyph pixel and depth (units)
LETTERS = tex.metal("#fff3c4", "#ffffff", "#d9b45a", bands=1.6, glow=0.9)
LETTERS_HOT = tex.metal("#ffffff", "#ffffff", "#ffe08a", bands=1.2, glow=1.0)
RULE = tex.metal("#ffe08a", "#ffffff", "#c9a24a", bands=2.0, glow=1.0)


def _glyph_bone(m, parent, i, center, code, yaw=0.0, mat=LETTERS, pixel=P):
    b = m.bone(f"g{i}", parent, pivot=center, rot=(0, yaw, 0))
    extrude(b, FW[code % len(FW)], (center[0], center[1], center[2] - D / 2), pixel, D, mat)
    b.box((center[0], center[1] - 8 * pixel / 2 - 1.2, center[2]), (pixel * 3, 0.8, 0.8), RULE)
    return b


def line_straight():
    m = Model("dw6_line0", density=2.0, bounds=(28, 8, (0, 0, 0)))
    root = m.bone("root")
    for i in range(9):
        _glyph_bone(m, root, i + 1, (-56 + i * 14, 0, 0), (i * 7 + 3))
    rule = m.bone("rule", root, pivot=(0, 0, 0))
    rule.box((0, -9.5, 0), (130, 1.0, 1.6), RULE)
    rule.box((0, 9.5, 0), (130, 0.6, 1.0), RULE, variant=1)
    for x in (-66, 66):
        rule.box((x, 0, 0), (3, 3, 3), LETTERS_HOT, rot=(45, 0, 45))
    return m


def line_ring():
    m = Model("dw6_line1", density=2.0, bounds=(40, 8, (0, 0, 0)))
    root = m.bone("root")
    sp = m.bone("spin", root, pivot=(0, 0, 0))
    for i in range(12):
        a = i * 30
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        _glyph_bone(m, sp, i + 1, (40 * ca, 0, 40 * sa), i * 5 + 2, yaw=-a - 90)
    rule = m.bone("rule", sp, pivot=(0, 0, 0))
    ring(rule, (0, -9.5, 0), 40, 24, (10.6, 1.4, 1.0), RULE, axis="y")
    return m


def line_lattice():
    m = Model("dw6_line2", density=2.0, bounds=(30, 8, (0, 0, 0)))
    root = m.bone("root")
    k = 0
    for gz in (-1, 0, 1):
        for gx in (-1, 0, 1):
            k += 1
            _glyph_bone(m, root, k, (gx * 32, 0, gz * 32), k * 11 + 1)
    rule = m.bone("rule", root, pivot=(0, 0, 0))
    for t in (-32, 0, 32):
        rule.box((0, -9.5, t), (70, 1.0, 1.0), RULE)
        rule.box((t, -9.5, 0), (1.0, 1.0, 70), RULE, variant=1)
    return m


def line_spiral():
    m = Model("dw6_line3", density=2.0, bounds=(30, 8, (0, 0, 0)))
    root = m.bone("root")
    sp = m.bone("spin", root, pivot=(0, 0, 0))
    for i in range(12):
        a = i * 42
        r = 46 - i * 3.2
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        _glyph_bone(m, sp, i + 1, (r * ca, 0, r * sa), i * 3 + 5, yaw=-a - 90)
    rule = m.bone("rule", sp, pivot=(0, 0, 0))
    for j in range(36):
        a = j * 14
        r = 46 - j * 1.07
        rule.box((r * math.cos(math.radians(a)), -9.5, r * math.sin(math.radians(a))), (2.0, 2.0, 2.0), RULE,
                 rot=(45, -a, 45))
    return m


def line_formation():
    m = Model("dw6_line4", density=1.0, bounds=(48, 20, (0, 4, 0)))
    root = m.bone("root")
    seal = m.bone("seal", root, pivot=(0, -14, 0))
    seal.plane("y", (0, -14, 0), 132, 132, tex.magic_circle(FW, "#ffffff", WGOLD, bands=((0.8, 0.95, 40), (0.46, 0.58, 20)),
                                                            lines=(0.77, 0.98, 0.43, 0.61), star=7, star_r=(0.12, 0.42),
                                                            core=0.05), faces=("up", "down"), density=2.0)
    rin = m.bone("ring_in", root, pivot=(0, 0, 0))
    rout = m.bone("ring_out", root, pivot=(0, 0, 0))
    i = 0
    for parent, n, r, px in ((rin, 10, 26, 2.0), (rout, 16, 48, 2.4)):
        for k in range(n):
            i += 1
            a = k * 360 / n
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            _glyph_bone(m, parent, i, (r * ca, 0, r * sa), i * 13 + 4, yaw=-a - 90, mat=LETTERS_HOT if k % 2 else LETTERS,
                        pixel=px)
    ring(rin, (0, -10, 0), 26, 20, (8.4, 1.2, 1.0), RULE, axis="y")
    ring(rout, (0, -12, 0), 48, 32, (9.6, 1.4, 1.0), RULE, axis="y")
    spk = m.bone("spokes", root, pivot=(0, 0, 0))
    for k in range(8):
        spk.box((0, -12, -37), (1.6, 1.6, 22), RULE, rot=(0, k * 45, 0), pivot=(0, -12, 0))
    spire = m.bone("spire", root, pivot=(0, 0, 0))            # one crowning letter (kept low: it must stay in view)
    extrude(spire, FW[13], (0, 5, -2), 2.6, 4.0, LETTERS_HOT)
    spire.box((0, -5.5, 0), (12, 1.4, 1.4), RULE, rot=(0, 45, 0))
    spire.box((0, 3, 0), (1.2, 26, 1.2), RULE)
    return m


LINES = [line_straight, line_ring, line_lattice, line_spiral, line_formation]


def line_anims():
    A = []
    always = Anim("turn", loop=True)
    always.rot("spin", (0, spin(24), 0))
    always.rot("ring_in", (0, spin(30), 0))
    always.rot("ring_out", (0, spin(-18), 0))
    always.rot("spire", (0, spin(40), 0))
    always.rot("seal", (0, spin(12), 0))
    A.append(always)
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    asm = Anim("assemble", length=1.5, loop="hold")          # letters fly in from the tablets and lock in
    for i in range(1, 27):
        t = 0.03 * i
        off = (math.sin(i * 2.3) * 40, 30 + math.cos(i * 1.7) * 20, math.cos(i * 3.1) * 40)
        asm.pos(f"g{i}", {0: off, t: off, t + 0.55: (0, -2, 0), t + 0.7: (0, 0, 0)})
        asm.scl(f"g{i}", {0: 0.0, t: 0.2, t + 0.5: 1.2, t + 0.7: 1.0})
        asm.rot(f"g{i}", {0: (0, 0, 0), t: (90, 180, 0), t + 0.6: (0, 0, 0)})
    asm.scl("rule", {0: (0, 1, 0), 0.9: (0, 1, 0), 1.3: (1.05, 1, 1.05), 1.5: 1.0})
    asm.scl("seal", {0: 0.0, 0.6: 0.0, 1.3: 1.08, 1.5: 1.0})
    asm.scl("spokes", {0: 0.0, 1.0: 0.0, 1.4: 1.0})
    asm.scl("spire", {0: (1, 0, 1), 0.5: (1, 0, 1), 1.3: (1, 1.1, 1), 1.5: 1.0})
    A.append(asm)
    hold = Anim("hold", loop=True)
    for i in range(1, 27):
        hold.pos(f"g{i}", (0, LIFE(1.8, 2.2, i * 0.083), 0))
    A.append(hold)
    strike = Anim("strike", length=0.6, loop="hold")
    for i in range(1, 27):
        strike.scl(f"g{i}", {0: 1.0, 0.08: (1.35, 0.55, 1.35), 0.3: 1.12, 0.6: 1.0})
    strike.scl("rule", {0: 1.0, 0.1: (1.25, 3.0, 1.25), 0.6: 1.0})
    strike.scl("seal", {0: 1.0, 0.1: 1.2, 0.6: 1.05})
    strike.scl("spire", {0: 1.0, 0.06: (1.4, 0.4, 1.4), 0.4: (1.0, 1.1, 1.0), 0.6: 1.0})
    A.append(strike)
    unw = Anim("unwrite", length=1.0, loop="hold")
    for i in range(1, 27):
        t = 0.02 * i
        unw.pos(f"g{i}", {0: (0, 0, 0), t: (0, 0, 0), 1.0: (0, 26, 0)})
        unw.scl(f"g{i}", {0: 1.0, t + 0.3: 1.2, 1.0: 0.0})
    for b in ("rule", "seal", "spokes", "spire"):
        unw.scl(b, {0: 1.0, 0.5: 0.0})
    A.append(unw)
    return A


def build(pack):
    tms = [tablet(k) for k in range(7)]
    ta = tablet_anims()
    pack.actor("dw6_tablet", tms[0], ta, TABLET_STATES, kinds=tms[1:], scale=TABLET_SCALE, lifetime=90, display="Tablet of Law")
    lms = [f() for f in LINES]
    la = line_anims()
    pack.actor("dw6_line", lms[0], la, LINE_STATES, always=["turn"], kinds=lms[1:], scale=3.0, size_prop=True, lifetime=90,
               display="Line of Sacred Text", blend=0.05)
    tb = {a.name: a for a in ta}
    for k, tm in enumerate(tms):
        pack.preview(f"dw6_tablet{k}", tm, [(tb["idle"], 0.5), (tb["declare"], 1.0)], views=((15, 8),), cell=(300, 300))
    lb = {a.name: a for a in la}
    for k, lm in enumerate(lms):
        pack.preview(f"dw6_line{k}", lm, [[(lb["hold"], 0.3), (lb["turn"], 0.2)], [(lb["assemble"], 0.6), (lb["turn"], 0.2)]],
                     views=((20, 30),), cell=(300, 300))
    print("    tablets cubes:", [t.cube_count() for t in tms], "bones:", [len(t.order) for t in tms])
    print("    lines cubes:", [t.cube_count() for t in lms], "bones:", [len(t.order) for t in lms], "tex", lms[4].tex_size)
