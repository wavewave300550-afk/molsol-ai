"""
Prop / projectile / hazard models used by the bosses' skills.  Their idle
animations are driven by query.life_time so they animate without scripts
(rise from the ground, spin, flicker).
"""
from __future__ import annotations

import math

from .common import Creature, chain, kf, ring_cubes, wave
from mk.geo import Model
from mk.paint import (bone_mat, bronze, crystal, d_pixels, flame, fur, glowball, glyphs, gold, horn, marble, solid)

T = "q.life_time"


def rise(c: Creature, bone="root", dur=0.25):
    c.loops[0][1].scl(bone, [1, f"math.min(1.0, {T} / {dur})", 1])


def build_ding() -> Creature:
    m = Model("geometry.legends.ding", seed=1101)
    m.bounds = (3.0, 3.0, 1.0)
    BR = bronze("4c6c54", "86c4a7", "c8a456", "1f2b24", band=(0.2, 0.8), cell=6)
    BRP = bronze("435f4b", "79b49a", "c39a48", "1c2620", motif=False)
    DARK = solid("140f0c", 0.04, edge=0)
    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 10, 0), "root")
    mask = d_pixels(["G......G", ".GG..GG.", ".OO..OO.", "...GG...", "..G..G.."], {"G": "c8a456", "O": "e0602a"}, center=True)
    body.add((-10, 8, -10), (20, 15, 20), BR, decals={f: mask for f in ("north", "south", "east", "west")})
    body.add((-11, 22, -11), (22, 2.5, 22), BRP)                                   # rim
    body.add((-9, 24.4, -9), (18, 0.2, 18), DARK, faces=("up",))
    for s in (-1, 1):                                                              # upright handles (ears)
        body.add((s * 7 - 1.5, 24, -1.5), (3, 8, 3), BRP)
        body.add((s * 7 - 1.5, 30, -5), (3, 2.5, 10), BRP)
        body.add((s * 7 - 1.5, 24, 3.5), (3, 8, 3), BRP)
        body.add((s * 7 - 1.5, 24, -6.5), (3, 8, 3), BRP)
    for x, z in ((-8, -8), (5, -8), (-8, 5), (5, 5)):                             # pillar legs
        body.add((x, 0, z), (3, 9, 3), BRP)
    for k, (x, z) in enumerate(((-10.6, -1.5), (9.6, -1.5))):                       # corner flanges
        body.add((x, 10, z), (1, 11, 3), gold("c8a456", "6e4a14", "f0d48a"))
    c = Creature("ding", m, scale=1.4)
    idle = c.loop("idle")
    idle.scl("root", [f"math.min(1.0, {T} * 4)", f"math.min(1.0, {T} * 4)", f"math.min(1.0, {T} * 4)"])
    idle.rot("body", [0, 0, f"query.property('legends:act') == 1 ? math.sin({T} * 1600) * 6 : 0"])
    c.pre = ["variable.act = query.property('legends:act')"]
    return c


def build_root_spike() -> Creature:
    m = Model("geometry.legends.root_spike", seed=1102)
    m.bounds = (3.0, 4.0, 1.5)
    ROOT = solid("5a3d24", 0.12)
    ROOT_D = solid("3b2716", 0.12)
    VEN = glowball("d9ffb8", "58e83a")
    m.bone("root", (0, 0, 0))
    for k, (x, z, rz, rx) in enumerate(((0, 0, 0, 0), (-5, 3, 25, -10), (4, -4, -20, 15), (3, 5, -10, -25))):
        names = chain(m, f"r{k}_", "root", (x, 0, z), "+y", [10, 9, 8, 6] if k == 0 else [7, 6, 5],
                      [(5, 5), (4, 4), (3, 3), (2, 2)] if k == 0 else [(3.5, 3.5), (2.6, 2.6), (1.8, 1.8)],
                      [(rx, 0, rz), (-15, 0, 10), (20, 0, -15), (10, 0, 10)], [ROOT, ROOT_D, ROOT, ROOT_D])
    g = m.bone("glow_sap", (0, 20, 0), "r0_2")
    g.add((-1, 19, -1.6), (2, 4, 0.5), VEN)
    c = Creature("root_spike", m, scale=1.6)
    idle = c.loop("idle")
    idle.scl("root", [1, f"math.min(1.0, {T} * 5)", 1])
    idle.rot("r0_1", [wave(4, 200), 0, wave(4, 160)])
    idle.rot("r0_2", [wave(6, 200, -60), 0, wave(6, 160, -60)])
    return c


def build_meteor() -> Creature:
    m = Model("geometry.legends.nid_meteor", seed=1103)
    m.bounds = (2.0, 2.0, 0.5)
    BONE = bone_mat("e1d9bf", "8f8466")
    HORN = horn("8f8670", "4a4538")
    root = m.bone("root", (0, 0, 0))
    sk = m.bone("skull", (0, 4, 0), "root")
    sk.add((-3.5, 1, -3.5), (7, 6, 7), BONE, decals={"north": d_pixels(["KK.KK", "KK.KK", ".....", "..K..", "TTTTT"],
                                                                         {"K": "0b1a08", "T": "f0ead2"}, center=True)})
    for s in (-1, 1):
        sk.add((s * 4 - 1, 5, 0), (2, 2, 6), HORN, pivot=(s * 4, 6, 1), rotation=(-30, 0, 20 * s))
    g = m.bone("glow_fire", (0, 4, 3), "skull")
    g.add((-3, 1, 3), (6, 6, 4), glowball("eaffd0", "3fbf2a"))
    g.add((-2, 2, 7), (4, 4, 4), glowball("d0ffb8", "2a8f1a"))
    g.add((-1, 3, 11), (2, 2, 3), glowball("b0ff90", "1f6a12"))
    ge = m.bone("glow_eyes", (0, 5, -3.6), "skull")
    ge.add((-2.5, 4.5, -3.7), (1.5, 1.2, 0.3), glowball("ffffff", "7dff6a"))
    ge.add((1.0, 4.5, -3.7), (1.5, 1.2, 0.3), glowball("ffffff", "7dff6a"))
    c = Creature("nid_meteor", m, scale=1.6)
    idle = c.loop("idle")
    idle.scl("glow_fire", [f"1 + {wave(0.15, 900)}", f"1 + {wave(0.15, 700)}", f"1 + {wave(0.2, 800)}"])
    return c


def build_discus() -> Creature:
    m = Model("geometry.legends.discus", seed=1104)
    m.bounds = (2.0, 1.0, 0.25)
    GOLD = gold("f2c14e", "8c5a12", "fff2c0")
    CRY = crystal("bfefff", "ffffff", "7fb7d6", facet=2)
    root = m.bone("root", (0, 0, 0))
    d = m.bone("disc", (0, 3, 0), "root")
    ring_cubes(d, (0, 3, 0), 7, 14, 2.2, 1.6, GOLD, plane="xz")
    for k in range(8):
        a = math.radians(k * 45)
        px, pz = math.cos(a) * 9.5, math.sin(a) * 9.5
        d.add((px - 1, 2.5, pz - 2.2), (2, 1, 4.4), CRY, pivot=(px, 3, pz), rotation=(0, -k * 45 - 30, 0))
    g = m.bone("glow_hub", (0, 3, 0), "disc")
    g.add((-2, 2, -2), (4, 2, 4), glowball("ffffff", "ffd36a"))
    c = Creature("discus", m, scale=1.6)
    c.loop("idle").rot("disc", [0, f"{T} * 1440", 0])
    return c


def build_boulder() -> Creature:
    m = Model("geometry.legends.boulder", seed=1105)
    m.bounds = (5.0, 5.0, 1.5)
    ROCK = solid("7b7468", 0.14)
    ROCK_D = solid("5b554b", 0.14)
    GRASS = solid("5e9c3a", 0.12)
    WOOD = solid("6a4a2a", 0.08)
    LEAF = solid("3f7a2a", 0.14)
    root = m.bone("root", (0, 0, 0))
    b = m.bone("rock", (0, 14, 0), "root")
    for k, (w, y, h) in enumerate(((30, 0, 6), (26, 6, 6), (20, 12, 6), (13, 18, 6), (7, 24, 5))):
        b.add((-w / 2 + (k % 2), y, -w / 2 - (k % 2)), (w, h, w), ROCK if k % 2 else ROCK_D)
    b.add((-13, 5.9, -13), (26, 0.4, 26), GRASS, faces=("up",))
    b.add((-6.5, 23.9, -6.5), (13, 0.3, 13), GRASS, faces=("up",))
    b.add((-12, -6, -12), (24, 6, 24), ROCK_D)
    b.add((-7, -10, -7), (14, 4, 14), ROCK)
    for x, z in ((-9, -8), (8, 6)):
        b.add((x - 0.6, 6, z - 0.6), (1.2, 5, 1.2), WOOD)
        b.add((x - 2.5, 10, z - 2.5), (5, 4, 5), LEAF)
    c = Creature("boulder", m, scale=1.5)
    c.loop("idle").rot("rock", [f"{T} * 40", f"{T} * 25", 0])
    return c


def build_wisp() -> Creature:
    m = Model("geometry.legends.wind_wisp", seed=1106)
    m.bounds = (2.0, 2.0, 0.8)
    WIND = solid("d8f4ee", 0.06)
    root = m.bone("root", (0, 0, 0))
    a = m.bone("ring_a", (0, 10, 0), "root")
    ring_cubes(a, (0, 10, 0), 6, 10, 1.4, 1.4, WIND, plane="xz", arc=270)
    b = m.bone("ring_b", (0, 10, 0), "root")
    ring_cubes(b, (0, 10, 0), 4, 8, 1.2, 1.2, WIND, plane="xy", arc=270)
    g = m.bone("glow_core", (0, 10, 0), "root")
    g.add((-1.8, 8.2, -1.8), (3.6, 3.6, 3.6), glowball("ffffff", "7dffe0"), pivot=(0, 10, 0), rotation=(45, 45, 0))
    c = Creature("wind_wisp", m, scale=1.2)
    idle = c.loop("idle")
    idle.rot("ring_a", [0, f"{T} * 400", 0])
    idle.rot("ring_b", [0, 0, f"-{T} * 500"])
    idle.pos("root", [0, wave(1.2, 180), 0])
    return c


def build_crescent() -> Creature:
    m = Model("geometry.legends.crescent", seed=1107)
    m.bounds = (6.0, 2.0, 0.5)
    MOON = glowball("ffffff", "e6ecff")
    root = m.bone("root", (0, 0, 0))
    g = m.bone("glow_moon", (0, 4, 0), "root")
    for k, (r, th) in enumerate(((22, 3.2), (19.5, 2.4), (24, 1.4))):
        ring_cubes(g, (0, 4, 0), r, 18, th, 1.4, MOON, plane="xz", arc=150, phase=105)
    c = Creature("crescent", m, scale=1.4)
    c.loop("idle").scl("glow_moon", [f"1 + {wave(0.04, 600)}", 1, f"1 + {wave(0.04, 600)}"])
    return c


def build_prism() -> Creature:
    m = Model("geometry.legends.prism", seed=1108)
    m.bounds = (2.0, 3.0, 1.0)
    CRY = crystal("e7dcff", "ffffff", "9a7ad6", facet=2)
    root = m.bone("root", (0, 0, 0))
    p = m.bone("crystal", (0, 16, 0), "root")
    for k, (w, y) in enumerate(((2, 26), (5, 23), (8, 20), (10, 17), (10, 15), (8, 12), (5, 9), (2, 6))):
        p.add((-w / 2, y - 1.5, -w / 2), (w, 3, w), CRY, pivot=(0, y, 0), rotation=(0, 45, 0))
    g = m.bone("glow_core", (0, 16, 0), "crystal")
    g.add((-2, 14, -2), (4, 4, 4), glowball("ffffff", "c7a6ff"), pivot=(0, 16, 0), rotation=(45, 45, 0))
    c = Creature("prism", m, scale=1.3)
    idle = c.loop("idle")
    idle.rot("crystal", [0, f"{T} * 60", 0])
    idle.pos("crystal", [0, wave(1.2, 90), 0])
    return c


def build_lance() -> Creature:
    m = Model("geometry.legends.star_lance", seed=1109)
    m.bounds = (3.0, 1.0, 0.25)
    root = m.bone("root", (0, 0, 0))
    g = m.bone("glow_lance", (0, 4, 0), "root")
    g.add((-0.8, 3.2, -14), (1.6, 1.6, 26), glowball("ffffff", "a6c8ff"))
    g.add((-2.2, 1.8, -17), (4.4, 4.4, 4.4), glowball("ffffff", "ffe28a"), pivot=(0, 4, -15), rotation=(45, 0, 45))
    c = Creature("star_lance", m, scale=1.2)
    c.loop("idle").rot("glow_lance", [0, 0, f"{T} * 720"])
    return c


def build_foxfire() -> Creature:
    m = Model("geometry.legends.foxfire", seed=1110)
    m.bounds = (1.5, 1.5, 0.5)
    root = m.bone("root", (0, 0, 0))
    g = m.bone("glow_fire", (0, 5, 0), "root")
    g.add((-3, 2, -3), (6, 6, 6), glowball("ffffff", "38a8ff"))
    for k, (x, z, h) in enumerate(((-1.5, -1.5, 5), (1.5, 0.5, 4), (0, 1.8, 3.5))):
        g.add((x - 1, 7, z - 1), (2, h, 2), glowball("e8fbff", "1f6fff"))
    c = Creature("foxfire", m, scale=1.3)
    idle = c.loop("idle")
    idle.scl("glow_fire", [f"1 + {wave(0.12, 900)}", f"1 + {wave(0.18, 700)}", f"1 + {wave(0.12, 800)}"])
    idle.rot("glow_fire", [0, f"{T} * 200", 0])
    return c


def build_torii() -> Creature:
    m = Model("geometry.legends.torii", seed=1111)
    m.bounds = (5.0, 5.0, 2.0)
    RED = solid("c8251e", 0.08)
    BLACK = solid("1e1a1a", 0.05)
    GOLD = gold("f2c14e", "8c5a12", "fff2c0")
    STONE = solid("8d8a84", 0.1)
    root = m.bone("root", (0, 0, 0))
    g = m.bone("gate", (0, 0, 0), "root")
    for s in (-1, 1):
        g.add((s * 14 - 2, 0, -2), (4, 44, 4), RED)
        g.add((s * 14 - 3, 0, -3), (6, 3, 6), BLACK)
        g.add((s * 14 - 2.5, 40, -2.5), (5, 2, 5), BLACK)
    g.add((-20, 34, -1.6), (40, 3, 3.2), RED)                                         # nuki
    g.add((-21, 44, -2.5), (42, 3, 5), RED)                                           # shimaki
    g.add((-23, 47, -3), (46, 2.5, 6), BLACK)                                         # kasagi
    for s in (-1, 1):
        g.add((s * 23 - 2.5 + s * 1.5, 47.5, -3), (5, 2.5, 6), BLACK, pivot=(s * 23, 48, 0), rotation=(0, 0, -12 * s))
    g.add((-3, 37, -2), (6, 7, 4), GOLD, decals={"north": d_pixels(["K..K", ".KK.", "K..K"], {"K": "3a2a12"}, center=True)})
    gl = m.bone("glow_lanterns", (0, 30, 0), "gate")
    for s in (-1, 1):
        gl.add((s * 14 - 1.5, 30, -4.5), (3, 4, 1), glowball("e8fbff", "38a8ff"))
    c = Creature("torii", m, scale=1.25)
    c.loop("idle").scl("gate", [1, f"math.min(1.0, {T} * 3)", 1])
    return c


def build_tail_spike() -> Creature:
    m = Model("geometry.legends.tail_spike", seed=1112)
    m.bounds = (2.0, 4.0, 1.5)
    TAIL = fur("f8e3ad", "d9a24f", "fff5d8", streak=1.0)
    TW = fur("fffaf0", "e9dfcf", "ffffff", streak=1.0)
    m.bone("root", (0, 0, 0))
    names = chain(m, "t", "root", (0, 0, 0), "+y", [8, 9, 9, 7], [(5, 5), (7, 7), (7.5, 7.5), (5.5, 5.5)],
                  [(0, 0, 0), (8, 0, 0), (10, 0, 6), (12, 0, 8)], [TAIL, TAIL, TAIL, TW])
    g = m.bone("glow_tip", (0, 33, 0), names[-1])
    g.add((-2, 33, -2), (4, 4, 4), glowball("e8fbff", "38a8ff"))
    c = Creature("tail_spike", m, scale=1.4)
    idle = c.loop("idle")
    idle.scl("root", [1, f"math.min(1.0, {T} * 6)", 1])
    for i, nb in enumerate(names):
        idle.rot(nb, [wave(6 + i * 3, 260, -i * 50), 0, wave(5 + i * 2, 220, -i * 40)])
    return c


def build_tablet() -> Creature:
    m = Model("geometry.legends.tablet", seed=1113)
    m.bounds = (3.0, 3.0, 1.0)
    STONE = glyphs("d9d2c3", "c49a2c", rows=3, seed=31)
    root = m.bone("root", (0, 0, 0))
    t = m.bone("slab", (0, 14, 0), "root")
    for s in (-1, 1):
        x0 = 0.4 if s > 0 else -12.4
        t.add((x0, 0, -1.5), (12, 22, 3), STONE)
        t.add((x0 + 2, 22, -1.5), (8, 3, 3), STONE)
    c = Creature("tablet", m, scale=1.4)
    c.loop("idle").rot("slab", [f"{T} * 90", f"{T} * 40", 0])
    return c


def build_spear() -> Creature:
    m = Model("geometry.legends.light_spear", seed=1114)
    m.bounds = (3.0, 1.0, 0.25)
    root = m.bone("root", (0, 0, 0))
    g = m.bone("glow_spear", (0, 4, 0), "root")
    g.add((-0.7, 3.3, -10), (1.4, 1.4, 24), glowball("ffffff", "ffe9a0"))
    g.add((-1.6, 2.4, -16), (3.2, 3.2, 6), glowball("ffffff", "fff3c4"), pivot=(0, 4, -13), rotation=(0, 45, 0))
    c = Creature("light_spear", m, scale=1.2)
    c.loop("idle").rot("glow_spear", [0, 0, f"{T} * 540"])
    return c


def build_eden() -> Creature:
    m = Model("geometry.legends.eden_sword", seed=1115)
    m.bounds = (3.0, 4.0, 1.5)
    GOLD = gold("f2c14e", "8c5a12", "fff2c0")
    STEEL = solid("e8edf3", 0.03)
    root = m.bone("root", (0, 0, 0))
    s = m.bone("sword", (0, 0, 0), "root")
    s.add((-0.7, 0, -0.7), (1.4, 26, 1.4), STEEL)
    s.add((-3.2, 26, -1), (6.4, 1.4, 2), GOLD)
    s.add((-0.9, 27.4, -0.9), (1.8, 6, 1.8), GOLD)
    g = m.bone("glow_blade", (0, 0, 0), "sword")
    g.add((-1.5, 2, -1.2), (3, 24, 2.4), glowball("fffbe0", "ff7a1a"))
    ring = m.bone("glow_ring", (0, 1, 0), "root")
    ring_cubes(ring, (0, 1, 0), 10, 20, 1.2, 0.6, glowball("fffbe0", "ffd36a"), plane="xz")
    c = Creature("eden_sword", m, scale=1.4)
    idle = c.loop("idle")
    idle.rot("glow_ring", [0, f"{T} * 45", 0])
    idle.scl("glow_blade", [f"1 + {wave(0.12, 800)}", 1, f"1 + {wave(0.12, 700)}"])
    return c


def build_coal() -> Creature:
    m = Model("geometry.legends.coal", seed=1116)
    m.bounds = (1.0, 1.0, 0.3)
    root = m.bone("root", (0, 0, 0))
    g = m.bone("glow_coal", (0, 3, 0), "root")
    g.add((-2.5, 0.5, -2.5), (5, 5, 5), glowball("fff1c0", "ff4a14"), pivot=(0, 3, 0), rotation=(30, 45, 15))
    c = Creature("coal", m, scale=1.3)
    c.loop("idle").rot("glow_coal", [f"{T} * 300", f"{T} * 200", 0])
    return c


ALL = {
    "ding": build_ding, "root_spike": build_root_spike, "nid_meteor": build_meteor, "discus": build_discus,
    "boulder": build_boulder, "wind_wisp": build_wisp, "crescent": build_crescent, "prism": build_prism,
    "star_lance": build_lance, "foxfire": build_foxfire, "torii": build_torii, "tail_spike": build_tail_spike,
    "tablet": build_tablet, "light_spear": build_spear, "eden_sword": build_eden, "coal": build_coal,
}
