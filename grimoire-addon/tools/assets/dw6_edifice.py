"""DW06 -- written architecture.

dw6_glyph     : a giant golden letter drawn stroke by stroke on the page, falling out as 3D (kinds 0-5)
dw6_edifice   : the six marble structures the letters become (kinds 0-5):
                0 column, 1 arch, 2 floating bridge, 3 monumental gate, 4 elevated platform,
                5 celestial geometric formation (armillary of text)
dw6_wall      : written walls of Law I (kind 0 marble) and the text waves of Law III (kind 1)
dw6_dome      : the refuge of Law V, a dome of written rings
dw6_boundary  : the boundary inscription ring that marks the domain
"""
import math

from kit import tex
from kit.anim import LIFE, Anim
from kit.geo import Model, ring

from .dw6_codex import PAGE_SCALE, PAGE_TILT
from .dw6_common import FW, GOLD, LETTER, WGOLD, engraved, extrude, extrude_strokes, gold_metal, spin, text_band

GLYPH_STATES = {0: ["hidden"], 1: ["draw"], 2: ["fall"], 3: ["land"]}
EDIFICE_STATES = {0: ["hidden"], 1: ["assemble"], 2: ["hold"], 3: ["swing"], 4: ["strike"], 5: ["unwrite"]}
WALL_STATES = {0: ["hidden"], 1: ["rise"], 2: ["hold"], 3: ["sink"]}
DOME_STATES = {0: ["hidden"], 1: ["form"], 2: ["hold"], 3: ["fade"]}
BOUND_STATES = {0: ["hidden"], 1: ["inscribe"], 2: ["hold"], 3: ["unwrite"]}

MARBLE = tex.marble("#f6f1e4", "#cbbf9f", vein2="#d9b45a", scale=6)
MARBLE2 = tex.marble("#ece4d0", "#bfb293", vein2="#c9a24a", scale=5)
GOLD_M = gold_metal(0.3)
GOLD_HOT = tex.metal("#ffe08a", "#ffffff", "#c9a24a", bands=2.0, glow=0.85)
FLASH = tex.glow_flat("#fff3c4", glow=1.0, a=0.42, core="#ffffff", mode="blend")


# ============================================================================== letters
def glyph_model(kind):
    g = FW[LETTER[kind]]
    m = Model(f"dw6_glyph{kind}", density=2.0, bounds=(12, 14, (0, 0, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 0, 0))
    aura = m.bone("aura", body, pivot=(0, 0, 4))
    aura.plane("z", (0, 0, 4), 44, 44, tex.shaped(tex.m_disc(1.0), "#fff3c4", "#e9c15a", glow=1.0, var=0, a=0.3, mode="blend",
                                                  key="dw6aura"))
    face = tex.glow_flat("#fffbe8", 1.0, core="#ffffff")
    extrude_strokes(m, body, g, (0, 0, -2.5), 4.0, 5.0, tex.metal("#e9c15a", "#fff3c4", "#9a7428", bands=1.5, glow=0.55),
                    prefix="s", n=5, edge=face)
    return m


def glyph_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    draw = Anim("draw", length=1.0, loop="hold")          # five strokes written one after another
    draw.rot("body", (PAGE_TILT, 0, 0))
    for k in range(5):
        t = 0.04 + 0.17 * k
        draw.scl(f"s{k + 1}", {0: 0.0, t: 0.0, t + 0.13: 1.18, t + 0.2: 1.0})
    draw.scl("aura", {0: 0.0, 0.72: 0.4, 0.88: 1.3, 1.0: 1.0})
    fall = Anim("fall", length=0.9, loop="hold")          # it tips out of the page, turns once and shrinks as it falls
    fall.rot("body", {0: (PAGE_TILT, 0, 0), 0.25: (PAGE_TILT + 18, 40, -8), 0.9: (0, 360, 0)})
    fall.pos("body", {0: (0, 0, 0), 0.2: (0, 2, -10), 0.9: (0, 0, 0)})
    fall.scl("body", {0: 1.0, 0.15: 1.06, 0.9: 0.55})
    fall.scl("aura", {0: 1.0, 0.9: 0.45})
    land = Anim("land", length=0.5, loop="hold")          # squashes into the ground as the marble rises
    land.scl("body", {0: 0.55, 0.12: (0.7, 0.4, 0.7), 0.5: (0.1, 0.0, 0.1)})
    land.pos("body", {0: (0, 0, 0), 0.5: (0, -16, 0)})
    land.scl("aura", {0: 0.45, 0.15: 2.2, 0.5: 0.0})
    return [hidden, draw, fall, land]


# ============================================================================== edifices
def _octo(b, center, w, h, mat, **kw):
    b.box(center, (w, h, w), mat, **kw)
    b.box(center, (w * 0.98, h, w * 0.98), mat, rot=(0, 45, 0), pivot=center, variant=1)


def _course(m, root, i, pivot):
    return m.bone(f"c{i}", root, pivot=pivot)


def _text_and_flash(m, root, W, H, D, y0=0.0):
    t = m.bone("text", root, pivot=(0, y0 + H * 0.5, 0))
    for j, f in enumerate((0.25, 0.5, 0.75)):
        y = y0 + H * f
        t.plane("z", (0, y, 0), W, 7, text_band(seed=j), variant=j)
        t.plane("x", (0, y, 0), max(D, 14), 7, text_band(seed=j + 3), variant=j)
    fl = m.bone("flash", root, pivot=(0, y0 + H * 0.5, 0))
    fl.plane("z", (0, y0 + H * 0.5, 0), W * 0.9, H, FLASH)
    fl.plane("x", (0, y0 + H * 0.5, 0), max(D, W * 0.5), H, FLASH)


def _sigil(m, root, kind, center, pixel):
    s = m.bone("sigil", root, pivot=center)
    extrude(s, FW[LETTER[kind]], (center[0], center[1], center[2] - pixel * 0.6), pixel, pixel * 1.2, GOLD_HOT)
    return s


def column():
    m = Model("dw6_edifice0", density=1.0, bounds=(14, 26, (0, 11, 0)))
    root = m.bone("root")
    c1 = _course(m, root, 1, (0, 0, 0))
    c1.box((0, 1.5, 0), (22, 3, 22), MARBLE2)
    c1.box((0, 4.5, 0), (18, 3, 18), MARBLE)
    c1.box((0, 6.2, 0), (18.6, 0.6, 18.6), GOLD_M)
    c2 = _course(m, root, 2, (0, 6.5, 0))
    c2.box((0, 8.5, 0), (14, 4, 14), MARBLE2)
    ring(c2, (0, 11.5, 0), 6.6, 12, (3.8, 2.6, 2.6), MARBLE, axis="y")
    ring(c2, (0, 13.2, 0), 5.9, 12, (3.4, 1.4, 1.2), GOLD_M, axis="y")
    c3 = _course(m, root, 3, (0, 13, 0))
    eng = engraved(seed=1)
    _octo(c3, (0, 26, 0), 10.4, 26, MARBLE)
    c3.box((0, 26, 0), (10.6, 26, 0.2), eng, faces=("north", "south"))
    c3.box((0, 26, 0), (0.2, 26, 10.6), eng, faces=("east", "west"))
    for y in (20, 33):
        ring(c3, (0, y, 0), 5.6, 8, (4.8, 1.0, 1.4), GOLD_HOT, axis="y")
    c4 = _course(m, root, 4, (0, 39, 0))
    _octo(c4, (0, 51.5, 0), 9.4, 25, MARBLE)
    c4.box((0, 51.5, 0), (9.6, 25, 0.2), engraved(seed=2), faces=("north", "south"))
    ring(c4, (0, 62.5, 0), 5.2, 8, (4.4, 1.0, 1.4), GOLD_M, axis="y")
    c5 = _course(m, root, 5, (0, 64, 0))
    _octo(c5, (0, 65.5, 0), 12.5, 3, MARBLE)
    c5.box((0, 68.5, 0), (17, 3, 17), MARBLE2)
    for sx in (-1, 1):
        for sz in (-1, 1):
            c5.box((sx * 7.6, 66.5, sz * 7.6), (3, 3, 3), GOLD_M, rot=(0, 45, 0))
    c6 = _course(m, root, 6, (0, 70, 0))
    c6.box((0, 71, 0), (8, 2, 8), GOLD_M)
    ring(c6, (0, 75, 0), 9.5, 14, (4.4, 1.0, 1.2), GOLD_HOT, axis="y")
    _sigil(m, root, 0, (0, 82, 0), 1.6)
    _text_and_flash(m, root, 22, 72, 22)
    return m


def arch():
    m = Model("dw6_edifice1", density=1.0, bounds=(14, 24, (0, 10, 0)))
    root = m.bone("root")
    c1 = _course(m, root, 1, (0, 0, 0))
    c2 = _course(m, root, 2, (0, 4, 0))
    c3 = _course(m, root, 3, (0, 24, 0))
    for sx in (-1, 1):
        c1.box((sx * 22, 2, 0), (15, 4, 16), MARBLE2)
        c1.box((sx * 22, 4.3, 0), (15.4, 0.6, 16.4), GOLD_M)
        c2.box((sx * 22, 14, 0), (10, 20, 12), MARBLE, mats={"north": engraved(seed=3), "south": engraved(seed=4)})
        c3.box((sx * 22, 32, 0), (10, 16, 12), MARBLE, variant=1)
        c3.box((sx * 22, 41.5, 0), (14, 3, 15), MARBLE2)
        c3.box((sx * 22, 43.3, 0), (14.4, 0.6, 15.4), GOLD_M)
    c4 = _course(m, root, 4, (0, 43, 0))
    ring(c4, (0, 43, 0), 22, 9, (8.2, 10, 12), MARBLE, axis="z", start=0, sweep=180)
    c5 = _course(m, root, 5, (0, 43, 0))
    ring(c5, (0, 43, -0.5), 27.6, 11, (8.4, 1.4, 13), GOLD_M, axis="z", start=0, sweep=180)
    for k in range(7):                                         # glyph plates on the archivolt face
        a = math.radians(15 + k * 25)
        p = (24 * math.cos(a), 43 + 24 * math.sin(a), -6.4)
        c5.box(p, (4.2, 5.6, 0), tex.bitmap_cut(FW[(k * 5 + 1) % len(FW)], WGOLD, glow=1.0, color2="#ffffff"),
               rot=(0, 0, math.degrees(a) - 90), faces=("north", "south"))
    c5.box((0, 66.5, 0), (8, 11, 14), GOLD_HOT)                # keystone
    c6 = _course(m, root, 6, (0, 66, 0))
    c6.box((0, 72, 0), (62, 5, 14), MARBLE, mats={"north": engraved(seed=5), "south": engraved(seed=6)})
    c6.box((0, 75.2, 0), (64, 1.5, 15), GOLD_M)
    _sigil(m, root, 1, (0, 85, 0), 1.8)
    _text_and_flash(m, root, 60, 76, 14)
    return m


def bridge():
    m = Model("dw6_edifice2", density=1.0, bounds=(20, 14, (0, 4, 0)))
    root = m.bone("root")
    deck = tex.trimmed(MARBLE, GOLD, 1, 0, glow=0.5)
    c1 = _course(m, root, 1, (0, 30, 0))
    c1.box((0, 30, 0), (40, 4, 22), deck)
    c2 = _course(m, root, 2, (0, 30, 0))
    for sx in (-1, 1):
        c2.box((sx * 38, 30, 0), (36, 4, 22), deck, variant=1)
    c3 = _course(m, root, 3, (0, 32, 0))
    for sz in (-1, 1):
        c3.box((0, 39.5, sz * 10), (108, 1.6, 2.2), GOLD_M)
        for k in range(11):
            c3.box((-50 + k * 10, 35.2, sz * 10), (2, 5.6, 2), MARBLE2, variant=k % 2)
    c4 = _course(m, root, 4, (0, 30, 0))
    for sx in (-1, 1):
        c4.box((sx * 58, 33, 0), (10, 16, 26), MARBLE, mats={"east": engraved(seed=7), "west": engraved(seed=8)})
        c4.box((sx * 58, 41.8, 0), (12, 1.6, 28), GOLD_M)
        c4.box((sx * 58, 45, 0), (6, 6, 6), GOLD_HOT, rot=(45, 0, 45))
    c5 = _course(m, root, 5, (0, 28, 0))
    arcm = tex.glyph_rows(FW, "#ffffff", glow=1.0, color2=WGOLD, bg="#d9b45a", bg_glow=0.6, fill=0.6, key="dw6arc")
    for sx in (-1, 1):
        ring(c5, (sx * 28, 30, 0), 17, 7, (8.0, 3, 6), arcm, axis="z", start=180, sweep=180)
    c6 = _course(m, root, 6, (0, 27.9, 0))
    c6.plane("y", (0, 27.8, 0), 108, 20, text_band(seed=9), faces=("down",))
    for x in (-40, 0, 40):
        c6.box((x, 22, 0), (3, 3, 3), GOLD_HOT, rot=(45, 0, 45))
    _sigil(m, root, 2, (0, 50, 0), 1.8)
    _text_and_flash(m, root, 108, 30, 22, y0=20)
    return m


def gate():
    m = Model("dw6_edifice3", density=1.0, bounds=(16, 28, (0, 12, 0)))
    root = m.bone("root")
    c1 = _course(m, root, 1, (0, 0, 0))
    c2 = _course(m, root, 2, (0, 6, 0))
    c3 = _course(m, root, 3, (0, 36, 0))
    for sx in (-1, 1):
        c1.box((sx * 27, 3, 0), (20, 6, 22), MARBLE2)
        c1.box((sx * 27, 6.3, 0), (20.4, 0.6, 22.4), GOLD_M)
        c2.box((sx * 27, 21, 0), (16, 30, 18), MARBLE, mats={"north": engraved(seed=10), "south": engraved(seed=11)})
        c3.box((sx * 27, 48, 0), (14, 24, 16), MARBLE, variant=1)
        c3.box((sx * 27, 61, 0), (16, 2, 18), GOLD_M)
        c3.box((sx * 27, 65, 0), (8, 6, 8), GOLD_HOT, rot=(0, 45, 0))
    c4 = _course(m, root, 4, (0, 62, 0))
    c4.box((0, 67, 0), (72, 10, 16), MARBLE, mats={"north": engraved(seed=12), "south": engraved(seed=13)})
    c4.box((0, 73, 0), (76, 2, 18), GOLD_M)
    for j, (w, y, d) in enumerate(((52, 76, 14), (36, 80, 12), (20, 84, 10))):
        c4.box((0, y, 0), (w, 4, d), MARBLE2 if j % 2 == 0 else MARBLE)
    c5 = _course(m, root, 5, (0, 6, 0))
    lattice = tex.glyph_rows(FW, "#ffe9a3", glow=0.9, color2="#ffffff", scale=2, fill=0.95, key="dw6lattice")
    for sx in (-1, 1):
        door = m.bone(f"door_{'r' if sx > 0 else 'l'}", c5, pivot=(sx * 19, 6, -2), rot=(0, sx * 62, 0))
        cx = sx * 10
        door.plane("z", (cx, 34, -2), 18, 56, lattice, variant=(sx + 1) // 2)
        for (x, y, w, h) in ((cx, 6.8, 18, 1.6), (cx, 61.2, 18, 1.6), (cx, 34, 18, 1.2)):
            door.box((x, y, -2), (w, h, 1.4), GOLD_M)
        for x in (cx - 9, cx + 9):
            door.box((x, 34, -2), (1.6, 56, 1.4), GOLD_M)
    c6 = _course(m, root, 6, (0, 86, 0))
    c6.plane("z", (0, 98, -1), 26, 26, tex.magic_circle(FW, WGOLD, GOLD, bands=((0.7, 0.92, 14),), lines=(0.66, 0.97),
                                                         star=6, star_r=(0.2, 0.6)))
    _sigil(m, root, 3, (0, 98, -3), 2.0)
    _text_and_flash(m, root, 72, 90, 18)
    return m


def platform():
    m = Model("dw6_edifice4", density=1.0, bounds=(14, 10, (0, 3, 0)))
    root = m.bone("root")
    c1 = _course(m, root, 1, (0, 19, 0))
    _octo(c1, (0, 14, 0), 24, 4, MARBLE2)
    _octo(c1, (0, 17.5, 0), 38, 3, MARBLE)
    c1.box((0, 8, 0), (6, 8, 6), GOLD_HOT, rot=(0, 45, 0))
    c2 = _course(m, root, 2, (0, 19, 0))
    _octo(c2, (0, 21, 0), 62, 4, tex.trimmed(MARBLE, GOLD, 1, 0, glow=0.4))
    c3 = _course(m, root, 3, (0, 23, 0))
    ring(c3, (0, 23.6, 0), 30.5, 16, (12.4, 2.4, 2.2), GOLD_M, axis="y")
    c4 = _course(m, root, 4, (0, 23, 0))
    c4.plane("y", (0, 23.25, 0), 56, 56, tex.magic_circle(FW, WGOLD, GOLD, bands=((0.62, 0.86, 20),), lines=(0.58, 0.9, 0.97),
                                                          star=8, star_r=(0.15, 0.52), core=0.08), faces=("up", "down"))
    c5 = _course(m, root, 5, (0, 4, -40))
    for k in range(3):
        c5.box((0, 5 + 6 * k, -46 + 4 * k), (16, 2, 6), MARBLE2, variant=k % 2)
        c5.box((0, 6.2 + 6 * k, -48.6 + 4 * k), (16.4, 0.5, 0.8), GOLD_M)
    c6 = _course(m, root, 6, (0, 23, 0))
    for k in range(8):
        a = math.radians(k * 45 + 22.5)
        x, z = 28 * math.cos(a), 28 * math.sin(a)
        c6.box((x, 26, z), (2, 6, 2), GOLD_M)
        c6.box((x, 33, z), (6, 8.4, 0), tex.bitmap_cut(FW[(k * 3 + 4) % len(FW)], WGOLD, glow=1.0, color2="#ffffff"),
               rot=(0, -math.degrees(a) - 90, 0), faces=("north", "south"))
    _sigil(m, root, 4, (0, 42, 0), 1.6)
    _text_and_flash(m, root, 62, 30, 62, y0=10)
    return m


def celestial():
    Y = 46                                                    # armillary centre (kept low so it stays in view)
    m = Model("dw6_edifice5", density=1.0, bounds=(14, 20, (0, 8, 0)))
    root = m.bone("root")
    gtext = tex.glyph_rows(FW, "#ffffff", glow=1.0, color2=WGOLD, bg="#c9a24a", bg_glow=0.55, fill=0.75, key="dw6armil")
    for i, (bn, rot, r, n) in enumerate((("spa", (0, 0, 0), 28, 18), ("spb", (0, 0, 62), 24, 16), ("spc", (64, 0, 0), 20, 14))):
        sp = m.bone(bn, root, pivot=(0, Y, 0), rot=rot)
        c = _course(m, sp, i + 1, (0, Y, 0))
        ring(c, (0, Y, 0), r, n, (2 * math.pi * r / n * 1.02, 1.4, 4.2), gtext, axis="y", cycle=3)
        ring(c, (0, Y + 2.6, 0), r + 0.3, n, (2 * math.pi * r / n * 1.02, 1.8, 0.8), GOLD_M, axis="y")
    spd = m.bone("spd", root, pivot=(0, Y, 0))
    c4 = _course(m, spd, 4, (0, Y, 0))
    R, L = 15.0, 15.0 * math.sqrt(2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            c4.box((sx * R / 2, Y + sy * R / 2, 0), (1.5, L, 1.5), GOLD_HOT, rot=(0, 0, 45 * sx * sy))
            c4.box((0, Y + sy * R / 2, sx * R / 2), (1.5, L, 1.5), GOLD_HOT, rot=(-45 * sy * sx, 0, 0))
            c4.box((sx * R / 2, Y, sy * R / 2), (L, 1.5, 1.5), GOLD_HOT, rot=(0, 45 * sx * sy, 0))
    for (x, y, z) in ((R, 0, 0), (-R, 0, 0), (0, R, 0), (0, -R, 0), (0, 0, R), (0, 0, -R)):
        c4.box((x, Y + y, z), (3.4, 3.4, 3.4), GOLD_M, rot=(45, 45, 0))
    c5 = _course(m, spd, 5, (0, Y, 0))
    core = tex.glow_flat("#fff3c4", 1.0, core="#ffffff")
    c5.box((0, Y, 0), (8, 8, 8), core, rot=(45, 0, 45))
    c5.box((0, Y, 0), (6.5, 6.5, 6.5), core, rot=(0, 45, 45))
    for k in range(6):
        a = k * 60
        c5.box((0, Y, -10.5), (4, 5.6, 0), tex.bitmap_cut(FW[(k * 7 + 2) % len(FW)], WGOLD, glow=1.0, color2="#ffffff"),
               rot=(0, a, 0), pivot=(0, Y, 0), faces=("north", "south"))
    c6 = _course(m, root, 6, (0, 0, 0))
    c6.plane("y", (0, 0.4, 0), 44, 44, tex.magic_circle(FW, WGOLD, GOLD, bands=((0.7, 0.92, 16),), lines=(0.66, 0.96),
                                                         star=5, star_r=(0.2, 0.6), core=0.1), faces=("up",))
    beam = m.bone("beam", c6, pivot=(0, 0, 0))
    beam.plane("z", (0, Y / 2, 0), 3.5, Y, FLASH)
    beam.plane("x", (0, Y / 2, 0), 3.5, Y, FLASH)
    _sigil(m, root, 5, (0, Y + 36, 0), 1.6)
    _text_and_flash(m, root, 56, 50, 56, y0=Y - 24)
    return m


EDIFICES = [column, arch, bridge, gate, platform, celestial]


def edifice_anims():
    A = []
    turn = Anim("turn", loop=True)
    turn.rot("sigil", (0, spin(55), 0))
    turn.pos("sigil", (0, LIFE(1.2, 3.0), 0))
    turn.rot("spa", (0, spin(32), 0))
    turn.rot("spb", (0, spin(-46), 0))
    turn.rot("spc", (0, spin(58), 0))
    turn.rot("spd", (spin(20), spin(27), 0))
    turn.scl("beam", (LIFE(0.25, 0.6, base=1.0), 1, LIFE(0.25, 0.6, base=1.0)))
    A.append(turn)
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    def assemble_tracks(a, t0=0.0, step=0.18):
        for i in range(1, 7):
            t = t0 + step * (i - 1)
            a.scl(f"c{i}", {0: (0.0, 0.0, 0.0), t: (0.55, 0.0, 0.55), t + 0.22: (1.08, 1.1, 1.08), t + 0.34: (1.0, 1.0, 1.0)})
        a.scl("sigil", {0: 2.4, t0 + step * 5: 2.4, t0 + step * 5 + 0.3: 0.9, t0 + step * 5 + 0.45: 1.0})
        a.pos("sigil", {0: (0, -40, 0), t0 + step * 5: (0, -10, 0), t0 + step * 5 + 0.3: (0, 3, 0), t0 + step * 5 + 0.45: (0, 0, 0)})
        a.scl("text", 0.0)
        a.scl("flash", {0: (1.0, 0.0, 1.0), t0 + 0.05: (1.2, 1.0, 1.2), t0 + 0.5: (0.2, 1.0, 0.2), t0 + 0.7: 0.0})

    assemble = Anim("assemble", length=1.6, loop="hold")
    assemble_tracks(assemble)
    assemble.pos("root", {0: (0, 6, 0), 0.12: (0, -1.5, 0), 0.3: (0, 0, 0)})
    A.append(assemble)
    hold = Anim("hold", loop=True)
    hold.scl("text", 0.0)
    hold.scl("flash", 0.0)
    A.append(hold)
    swing = Anim("swing", length=1.4, loop="hold")             # bridge: written folded, then swings into place
    assemble_tracks(swing, 0.0, 0.07)
    swing.rot("root", {0: (0, -96, 0), 0.45: (0, -96, 0), 1.05: (0, 7, 0), 1.25: (0, -2, 0), 1.4: (0, 0, 0)})
    A.append(swing)
    strike = Anim("strike", length=0.8, loop="hold")
    strike.scl("root", {0: 1.0, 0.12: (1.05, 1.08, 1.05), 0.4: 0.98, 0.8: 1.0})
    strike.scl("flash", {0: 0.0, 0.08: (1.3, 1.0, 1.3), 0.45: (0.3, 1.0, 0.3), 0.7: 0.0})
    strike.scl("sigil", {0: 1.0, 0.12: 2.0, 0.5: 1.0})
    strike.scl("text", 0.0)
    A.append(strike)
    unwrite = Anim("unwrite", length=2.0, loop="hold")        # marble becomes lines of floating text again
    for i in range(1, 7):
        t = 0.1 * (6 - i)
        unwrite.scl(f"c{i}", {0: 1.0, t: 1.0, t + 0.5: (1.2, 0.04, 1.2), t + 0.8: (0.0, 0.0, 0.0)})
    unwrite.scl("sigil", {0: 1.0, 0.2: 1.6, 0.9: 0.0})
    unwrite.scl("text", {0: 0.0, 0.3: (0.6, 0.0, 0.6), 0.8: (1.1, 1.0, 1.1), 1.5: (1.5, 1.2, 1.5), 2.0: (2.0, 0.0, 2.0)})
    unwrite.pos("text", {0: (0, 0, 0), 0.8: (0, 4, 0), 2.0: (0, 50, 0)})
    unwrite.rot("text", {0: (0, 0, 0), 2.0: (0, 70, 0)})
    unwrite.scl("flash", 0.0)
    A.append(unwrite)
    return A


# ============================================================================== walls
def wall_marble():
    m = Model("dw6_wall0", density=1.0, bounds=(8, 8, (0, 2, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 0, 0))
    body.box((0, 2, 0), (68, 4, 12), MARBLE2)
    body.box((0, 22, 0), (64, 36, 8), MARBLE, mats={"north": engraved(seed=20), "south": engraved(seed=21)})
    for x in (-30, 30):
        body.box((x, 22, 0), (5, 36, 10), MARBLE2, variant=1)
    body.box((0, 41, 0), (68, 2, 11), GOLD_M)
    crest = m.bone("crest", body, pivot=(0, 42, 0))
    for k in range(5):
        crest.box((-24 + k * 12, 47, 0), (6, 8.4, 0), tex.bitmap_cut(FW[(k * 4 + 3) % len(FW)], WGOLD, glow=1.0, color2="#ffffff"),
                  faces=("north", "south"))
    return m


def wall_text():
    m = Model("dw6_wall1", density=1.0, bounds=(10, 6, (0, 2, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 0, 0))
    for j, z in enumerate((-3, 0, 3)):
        lb = m.bone(f"l{j + 1}", body, pivot=(0, 20, z))
        lb.plane("z", (0, 22, z), 80, 34, tex.glyph_rows(FW, "#fff3c4" if j != 1 else "#ffffff", glow=1.0, color2="#e9c15a",
                                                         scale=2, fill=0.8, seed=j * 7, key=f"dw6wave{j}"))
    body.box((0, 3, 0), (84, 2, 4), GOLD_HOT)
    body.box((0, 40.5, 0), (84, 1, 2), GOLD_HOT, variant=1)
    for x in (-42, 42):
        body.box((x, 21.5, 0), (2, 39, 4), GOLD_M)
    return m


def wall_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    rise = Anim("rise", length=1.0, loop="hold")
    rise.pos("body", {0: (0, -46, 0), 0.65: (0, 2.5, 0), 0.85: (0, -0.8, 0), 1.0: (0, 0, 0)})
    rise.scl("body", {0: (0.6, 1.0, 0.6), 0.6: (1.04, 1.0, 1.04), 1.0: 1.0})
    rise.scl("crest", {0: 0.0, 0.6: 0.0, 0.85: 1.3, 1.0: 1.0})
    hold = Anim("hold", loop=True)
    hold.pos("crest", (0, LIFE(1.0, 2.4), 0))
    for j in range(3):
        hold.pos(f"l{j + 1}", (LIFE(3, 0.9, j * 0.33), LIFE(1.5, 1.3, j * 0.2), 0))
    sink = Anim("sink", length=1.0, loop="hold")
    sink.pos("body", {0: (0, 0, 0), 0.2: (0, 2, 0), 1.0: (0, -48, 0)})
    sink.scl("crest", {0: 1.0, 0.3: 1.4, 0.6: 0.0})
    return [hidden, rise, hold, sink]


# ============================================================================== refuge dome
DOME_R = 106          # 6.6 blocks: the refuge is drawn AROUND the caster, never across their eyes


def dome():
    """Refuge of Law V, seen from inside: a seal on the ground, a low fence of standing letters at
    6.6 blocks, and two rings of text that turn above eye level (nothing crosses the view)."""
    R = DOME_R
    m = Model("dw6_dome", density=1.0, bounds=(16, 8, (0, 3, 0)))
    root = m.bone("root")
    seal = m.bone("seal", root, pivot=(0, 0, 0))
    seal.plane("y", (0, 0.5, 0), 2 * R + 16, 2 * R + 16,
               tex.magic_circle(FW, WGOLD, GOLD, glow=0.8, bands=((0.88, 0.96, 34),), lines=(0.865, 0.975, 0.62)),
               faces=("up",), density=0.75)
    fence = m.bone("fence", root, pivot=(0, 0, 0))
    ring(fence, (0, 1.2, 0), R, 30, (2 * math.pi * R / 30 * 1.02, 1.6, 1.4), GOLD_HOT, axis="y")
    for k in range(20):                                   # standing letters, knee high
        a = k * 18
        fence.box((0, 8.5, -R), (5.2, 7.3, 0), tex.bitmap_cut(FW[(k * 5 + 2) % len(FW)], WGOLD, glow=1.0, color2="#ffffff"),
                  rot=(0, a, 0), pivot=(0, 8.5, 0), faces=("north", "south"))
    band = tex.glyph_rows(FW, "#fff3c4", glow=1.0, color2="#ffffff", fill=0.9, key="dw6domeband")
    for i, (y, r) in enumerate(((82, R * 1.02), (104, R * 0.74))):     # above eye level: out of the caster's view
        b = m.bone(f"r{i + 1}", root, pivot=(0, y, 0))
        n = max(10, int(r / 4.2))
        ring(b, (0, y, 0), r, n, (2 * math.pi * r / n * 1.02, 1.0, 7.0), band, axis="y", cycle=3)
        ring(b, (0, y - 4.4, 0), r, n, (2 * math.pi * r / n * 1.02, 1.0, 0.8), GOLD_HOT, axis="y")
    crown = m.bone("crown", root, pivot=(0, 118, 0))
    crown.box((0, 120, 0), (8, 8, 8), tex.glow_flat("#fff3c4", 1.0, core="#ffffff"), rot=(45, 0, 45))
    return m


def dome_anims():
    always = Anim("drift", loop=True)
    always.rot("r1", (0, spin(-16), 0))
    always.rot("r2", (0, spin(22), 0))
    always.rot("fence", (0, spin(5), 0))
    always.rot("seal", (0, spin(-10), 0))
    always.rot("crown", (0, spin(80), 0))
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    form = Anim("form", length=1.2, loop="hold")
    form.scl("seal", {0: 0.0, 0.4: 1.1, 0.55: 1.0})
    form.scl("fence", {0: (0.0, 0.0, 0.0), 0.2: (1.0, 0.0, 1.0), 0.6: (1.0, 1.25, 1.0), 0.8: 1.0})
    for i in range(2):
        t = 0.45 + i * 0.2
        form.scl(f"r{i + 1}", {0: 0.0, t: 0.0, t + 0.3: 1.1, t + 0.45: 1.0})
    form.scl("crown", {0: 0.0, 1.0: 0.0, 1.2: 1.0})
    hold = Anim("hold", loop=True)
    hold.scl("crown", LIFE(0.15, 1.2, base=1.0))
    hold.pos("r1", (0, LIFE(1.5, 3.1), 0))
    hold.pos("r2", (0, LIFE(1.5, 3.7, 0.3), 0))
    fade = Anim("fade", length=1.0, loop="hold")
    fade.scl("fence", {0: 1.0, 0.25: (1.0, 1.2, 1.0), 0.8: (1.0, 0.0, 1.0)})
    fade.scl("r1", {0: 1.0, 0.3: 1.1, 0.9: 0.0})
    fade.scl("r2", {0: 1.0, 0.2: 1.1, 0.8: 0.0})
    fade.scl("seal", {0: 1.0, 0.4: 1.05, 1.0: 0.0})
    fade.scl("crown", {0: 1.0, 0.5: 0.0})
    return [always, hidden, form, hold, fade]


# ============================================================================== domain boundary
BR = 300


def boundary():
    m = Model("dw6_boundary", density=1.0, bounds=(44, 6, (0, 1, 0)))
    root = m.bone("root")
    text = tex.glyph_rows(FW, "#fff3c4", glow=1.0, color2="#e9c15a", fill=0.9, key="dw6bound")
    n_arc, per = 8, 6
    seg = 2 * math.pi * BR / (n_arc * per) * 1.01
    for k in range(n_arc):
        a0 = k * 360 / n_arc
        am = math.radians(a0 + 180 / n_arc)
        b = m.bone(f"a{k + 1}", root, pivot=(BR * math.cos(am), 0, BR * math.sin(am)))
        ring(b, (0, 0.6, 0), BR, per, (seg, 14, 0.4), text, axis="y", start=a0, sweep=360 / n_arc, cycle=3)
        ring(b, (0, 0.5, 0), BR - 10, per, (seg * 0.97, 1.4, 0.3), GOLD_HOT, axis="y", start=a0, sweep=360 / n_arc)
        ring(b, (0, 0.5, 0), BR + 10, per, (seg * 1.03, 1.4, 0.3), GOLD_HOT, axis="y", start=a0, sweep=360 / n_arc)
    plates = m.bone("plates", root, pivot=(0, 0, 0))
    for k in range(16):
        a = k * 22.5
        pb = m.bone(f"pl{k + 1}", plates, pivot=(0, 0, 0), rot=(0, a, 0))
        pb.box((0, 16, -(BR + 14)), (12, 17, 0), tex.bitmap_cut(FW[(k * 5 + 3) % len(FW)], WGOLD, glow=1.0, color2="#ffffff"),
               faces=("north", "south"))
        pb.box((0, 5, -(BR + 14)), (4, 4, 4), GOLD_HOT, rot=(45, 0, 45))
    return m


def boundary_anims():
    always = Anim("drift", loop=True)
    always.rot("root", (0, spin(3), 0))
    always.rot("plates", (0, spin(-7), 0))
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    # written from the far point of the ring (the actor faces the caster: bb +Z is the far side) around both
    # sides toward the caster, so the inscription is seen being written
    ins = Anim("inscribe", length=2.0, loop="hold")
    for k in range(8):
        mid = k * 45 + 22.5
        rank = round((abs((mid - 90 + 180) % 360 - 180) - 22.5) / 45)
        t = 0.1 + rank * 0.36
        ins.scl(f"a{k + 1}", {0: 0.0, t: 0.0, t + 0.36: 1.0})
    for k in range(16):
        t = 0.45 + min(abs(k - 8), 16 - abs(k - 8)) * 0.15
        ins.pos(f"pl{k + 1}", {0: (0, -30, 0), t: (0, -30, 0), t + 0.4: (0, 3, 0), t + 0.55: (0, 0, 0)})
        ins.scl(f"pl{k + 1}", {0: 0.0, t: 0.0, t + 0.3: 1.0})
    hold = Anim("hold", loop=True)
    for k in range(16):
        hold.pos(f"pl{k + 1}", (0, LIFE(2.0, 3.2, k * 0.11), 0))
    unw = Anim("unwrite", length=1.5, loop="hold")
    for k in range(8):
        t = 0.1 + (7 - k) * 0.12
        unw.scl(f"a{k + 1}", {0: 1.0, t: 1.0, t + 0.35: 0.0})
    for k in range(16):
        unw.pos(f"pl{k + 1}", {0: (0, 0, 0), 1.2: (0, 50, 0)})
        unw.scl(f"pl{k + 1}", {0: 1.0, 0.8: 1.0, 1.3: 0.0})
    return [always, hidden, ins, hold, unw]


def build(pack):
    gms = [glyph_model(k) for k in range(6)]
    ga = glyph_anims()
    pack.actor("dw6_glyph", gms[0], ga, GLYPH_STATES, kinds=gms[1:], scale=PAGE_SCALE, lifetime=90, display="Golden Letter",
               blend=0.05)
    ems = [f() for f in EDIFICES]
    ea = edifice_anims()
    pack.actor("dw6_edifice", ems[0], ea, EDIFICE_STATES, always=["turn"], kinds=ems[1:], scale=2.0, size_prop=True,
               lifetime=90, display="Written Edifice", blend=0.1)
    wms = [wall_marble(), wall_text()]
    wa = wall_anims()
    pack.actor("dw6_wall", wms[0], wa, WALL_STATES, kinds=wms[1:], size_prop=True, lifetime=90, display="Written Wall")
    dm = dome()
    da = dome_anims()
    pack.actor("dw6_dome", dm, da, DOME_STATES, always=["drift"], lifetime=90, display="Refuge of the Word")
    bm = boundary()
    ba = boundary_anims()
    pack.actor("dw6_boundary", bm, ba, BOUND_STATES, always=["drift"], lifetime=90, display="Boundary Inscription")

    gb = {a.name: a for a in ga}
    for k in (0, 3):
        pack.preview(f"dw6_glyph{k}", gms[k], [(gb["draw"], 0.4), (gb["draw"], 1.0), (gb["fall"], 0.3)], views=((15, 10),))
    eb = {a.name: a for a in ea}
    tn = (eb["turn"], 0.6)
    for k, em in enumerate(ems):
        pack.preview(f"dw6_edifice{k}", em, [[(eb["hold"], 0.0), tn], [(eb["assemble"], 0.7), tn], [(eb["unwrite"], 0.9), tn]],
                     views=((25, 15), (100, 35)))
    wb = {a.name: a for a in wa}
    pack.preview("dw6_walls", wms[0], [(wb["hold"], 0.0)], views=((25, 15),))
    pack.preview("dw6_wall1", wms[1], [(wb["hold"], 0.0)], views=((25, 15),))
    db = {a.name: a for a in da}
    pack.preview("dw6_dome", dm, [(db["hold"], 0.0)], views=((25, 25),))
    bb = {a.name: a for a in ba}
    pack.preview("dw6_boundary", bm, [(bb["hold"], 0.0)], views=((25, 35),))
    for name, mm in [("glyph", gms[0]), ("edifice", ems[3]), ("dome", dm), ("boundary", bm)]:
        print(f"    dw6_{name}: {mm.cube_count()} cubes, {len(mm.order)} bones, tex {mm.tex_size}")
    print("    edifice cubes:", [e.cube_count() for e in ems])
