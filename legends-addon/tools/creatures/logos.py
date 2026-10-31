"""
THE WORD OF GOD (Logos, พระวัจนะแห่งพระเจ้า) and its Choir.

The Word is not a body but an utterance given form: a radiant octahedral core
holding one sealed eye; a great halo with twelve star points; four page-wings
of scripture (luminous glyphs, never readable words) that unfold as the fight
escalates; seven wax seals orbiting the core that break one by one; seven
lampstand flames crowning it; and a veil of glyph-ribbons trailing beneath.

Choir (followers, not bosses):
  SERAPH  — a body of living flame wrapped in six wings (two veil the face, two
            the feet, two fly), bearing tongs with a live coal.
  CHERUB  — burnished-bronze guardian with four faces (man, lion on the right,
            ox on the left, eagle behind), four wings, calf-hooved legs, and the
            flaming sword that turns every way, orbiting it.
  OPHAN   — a Throne: wheels within wheels of beryl, rims full of eyes, around
            a heart of fire.
"""
from __future__ import annotations

import math

from .common import COMMON_PRE, Creature, chain, kf, mrot, ring_cubes, scale_subtree, wave
from mk.geo import Model
from mk.paint import (C, bake, cloth, crystal, d_center_gem, d_pixels, eyes_band, feathers, flame, glowball, glyphs,
                      gold, hx, marble, mix, shade, solid, fur, horn, bone_mat, metal)

GOLD = gold("f3cf5c", "8e6412", "fff7cf", sparkle=0.05)
GOLD_D = gold("d8ac3c", "70480c", "f8e3a0", sparkle=0.03)
MARBLE = marble("f6f3ec", "c8bfae", gold_vein="e7c25a")
PAGE = glyphs("f1e6c8", "b67d1f", rows=3, seed=7)
PAGE_B = glyphs("f6edd5", "c9952c", rows=3, seed=13)
VEIL = glyphs("fbf6e8", "d9a93c", rows=3, seed=21)
CORE = glowball("ffffff", "ffe9a8")
LIGHT = glowball("ffffff", "fff3c4")
FLAME = glowball("fffbe0", "ffb238")
SEAL = solid("a3122a", 0.08)


def build_logos() -> Creature:
    m = Model("geometry.legends.logos", seed=606)
    m.bounds = (10.0, 10.0, 4.0)
    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 44, 0), "root")
    body.loc("eye", (0, 44, -8))
    # ---------------------------------------------------------- octahedral core (stacked rotated squares)
    core = m.bone("core", (0, 44, 0), "body")
    for k, (w, y) in enumerate(((3, 58), (6, 55), (9, 52), (12, 49), (14, 46), (14, 42), (12, 39), (9, 36), (6, 33), (3, 30))):
        core.add((-w / 2, y - 1.5, -w / 2), (w, 3, w), MARBLE, pivot=(0, y, 0), rotation=(0, 45, 0))
    for k, y in enumerate((46.5, 41.5)):
        core.add((-7.6, y - 0.6, -7.6), (15.2, 1.2, 15.2), GOLD, pivot=(0, y, 0), rotation=(0, 45, 0))
    gc = m.bone("glow_core", (0, 44, 0), "core")
    gc.add((-4, 40, -4), (8, 8, 8), CORE, pivot=(0, 44, 0), rotation=(0, 45, 0))
    # the eye: sealed (phases I-II) and open (phase III)
    ec = m.bone("glow_eye_shut", (0, 44, -9), "core")
    ec.add((-4, 43.4, -10.2), (8, 1.2, 1), LIGHT)
    eo = m.bone("glow_eye_open", (0, 44, -9), "core")
    eo.add((-5, 41, -10.4), (10, 6, 1), glowball("ffffff", "ffe28a"),
           decals={"north": d_pixels(["..##..", ".#oo#.", ".#oo#.", "..##.."], {"#": "e2a516", "o": "2a1606"}, center=True)})
    scale_subtree(m, "core", 1.45)
    # ---------------------------------------------------------- halo with twelve star points
    halo = m.bone("halo", (0, 44, 7), "body")
    ring_cubes(halo, (0, 44, 7), 23, 28, 2.2, 1.6, GOLD, plane="xy")
    ring_cubes(halo, (0, 44, 7.5), 19.5, 24, 1.0, 1.0, GOLD_D, plane="xy")
    gh = m.bone("glow_halo", (0, 44, 7), "halo")
    for k in range(12):
        a = math.radians(k * 30)
        px, py = math.cos(a) * 26.5, 44 + math.sin(a) * 26.5
        gh.add((px - 1.2, py - 3, 6.4), (2.4, 6, 1.2), LIGHT, pivot=(px, py, 7), rotation=(0, 0, -(k * 30 - 90)))
    # ---------------------------------------------------------- four page-wings (unfold in chains)
    for name, base, rz in (("wing_ur", (-6, 50, 2), 35), ("wing_ul", (6, 50, 2), -35),
                           ("wing_dr", (-6, 38, 2), -30), ("wing_dl", (6, 38, 2), 30)):
        s = -1 if name.endswith("r") else 1
        d = "-x" if s < 0 else "+x"
        mats = [PAGE, PAGE_B, PAGE]
        lens = [14, 13, 11] if name.startswith("wing_u") else [12, 11, 9]
        rot0 = (0, 0, rz)
        names = chain(m, name, "body", base, d, lens, [(10, 1.4), (9, 1.3), (7.5, 1.2)],
                      [rot0, (0, 0, 8 * (-s if name.startswith("wing_u") else s)), (0, 0, 10 * (-s if name.startswith("wing_u") else s))],
                      mats, share=f"page{name[-2]}", mirror=s > 0)
        for nb in names:
            b = m.get(nb)
            x, y, z = b.pivot
            L = lens[names.index(nb)]
            b.add((x + (-L if s < 0 else 0), y - 5.6, z - 1.1), (L, 0.8, 2.2), GOLD, mirror=s > 0)
            b.add((x + (-L if s < 0 else 0), y + 4.8, z - 1.1), (L, 0.8, 2.2), GOLD, mirror=s > 0)
    # ---------------------------------------------------------- seven seals orbiting
    seals = m.bone("seals", (0, 44, 0), "body")
    for i in range(7):
        a = math.radians(i * 360 / 7)
        px, pz = math.cos(a) * 17, math.sin(a) * 17
        sb = m.bone(f"seal{i}", (px, 44, pz), "seals")
        sb.add((px - 2.5, 41.5, pz - 0.6), (5, 5, 1.2), SEAL, pivot=(px, 44, pz), rotation=(0, -(i * 360 / 7) - 90, 0),
               decals={"north": d_pixels([".GG.", "G..G", "G..G", ".GG."], {"G": "f3cf5c"}, center=True),
                       "south": d_pixels([".GG.", "G..G", "G..G", ".GG."], {"G": "f3cf5c"}, center=True)})
    # ---------------------------------------------------------- crown of seven lampstands
    crown = m.bone("crown", (0, 66, 0), "body")
    for i in range(7):
        a = math.radians(i * 360 / 7 + 13)
        px, pz = math.cos(a) * 8, math.sin(a) * 8
        crown.add((px - 0.6, 62, pz - 0.6), (1.2, 4, 1.2), GOLD)
        crown.add((px - 1.4, 65.6, pz - 1.4), (2.8, 0.8, 2.8), GOLD_D)
    gl = m.bone("glow_lamps", (0, 66, 0), "crown")
    for i in range(7):
        a = math.radians(i * 360 / 7 + 13)
        px, pz = math.cos(a) * 8, math.sin(a) * 8
        gl.add((px - 0.8, 66.4, pz - 0.8), (1.6, 2.6, 1.6), FLAME)
    # ---------------------------------------------------------- veil of glyph ribbons
    for k, (x, ln) in enumerate(((-5, 6), (0, 7), (5, 6))):
        chain(m, f"veil{k}_", "body", (x, 31, 1), "-y", [ln, ln, ln - 1, ln - 2], [(3.6, 0.8), (3.4, 0.8), (3.0, 0.8), (2.6, 0.8)],
              [(8, 0, 0), (6, 0, 0), (6, 0, 0), (6, 0, 0)], VEIL, share=f"veil{k}")

    c = Creature("logos", m, scale=1.6, description="The Word of God")
    c.preview_props = {"legends:var": 0}
    c.pre = COMMON_PRE + [
        "variable.open = math.lerp(variable.open ?? 0.0, variable.ph >= 3 ? 1.0 : (variable.ph >= 2 ? 0.55 : 0.0), 0.04)",
        "variable.seals = query.property('legends:var')",
    ]
    c.visibility += [("glow_eye_shut", "variable.ph < 3"), ("glow_eye_open", "variable.ph >= 3")]
    for i in range(7):
        c.visibility.append((f"seal{i}", f"variable.seals <= {i}"))

    t = "q.life_time"
    idle = c.loop("idle")
    idle.pos("body", [0, wave(1.6, 60), 0])
    idle.rot("halo", [0, 0, f"{t} * 12"])
    idle.rot("seals", [wave(6, 30), f"{t} * 40", 0])
    idle.rot("crown", [0, f"-{t} * 30", 0])
    idle.rot("core", [0, wave(10, 25), 0])
    idle.scl("glow_core", [f"1.0 + {wave(0.08, 200)}", f"1.0 + {wave(0.08, 200)}", f"1.0 + {wave(0.08, 200)}"])
    for name in ("wing_ur", "wing_ul", "wing_dr", "wing_dl"):
        s = -1 if name.endswith("r") else 1
        up = 1 if name.startswith("wing_u") else -1
        idle.rot(f"{name}0", [0, f"variable.open * {-35 * s} + {wave(4, 70)}", f"{wave(5 * s * up, 70)} + variable.open * {20 * s * up * -1}"])
        idle.rot(f"{name}1", [0, f"variable.open * {-25 * s}", f"{wave(4 * s * up, 70, -40)}"])
        idle.rot(f"{name}2", [0, f"variable.open * {-20 * s}", f"{wave(4 * s * up, 70, -80)}"])
    for k in range(3):
        for j in range(4):
            idle.rot(f"veil{k}_{j}", [wave(6 + j * 2, 80, -k * 50 - j * 40), 0, wave(4 + j, 60, -k * 70 - j * 30)])

    def P(a, bone, frames, ch="rot"):
        (a.rot if ch == "rot" else a.pos if ch == "pos" else a.scl)(bone, kf(frames))

    a = c.act("advent", 4.0, [3.0])
    P(a, "root", {0: [0, 90, 0], 2.8: [0, 4, 0], 3.2: [0, -2, 0], 4.0: [0, 0, 0]}, "pos")
    P(a, "halo", {0: [0.2, 0.2, 0.2], 2.8: [0.9, 0.9, 0.9], 3.2: [1.15, 1.15, 1.15], 4.0: [1, 1, 1]}, "scl")
    P(a, "halo", {0: [0, 0, 0], 4.0: [0, 0, 360]})

    a = c.act("speak", 2.0, [0.8])
    P(a, "glow_core", {0: [1, 1, 1], 0.6: [1.6, 1.6, 1.6], 0.8: [0.8, 0.8, 0.8], 2.0: [1, 1, 1]}, "scl")
    P(a, "halo", {0: [1, 1, 1], 0.6: [1.12, 1.12, 1.12], 2.0: [1, 1, 1]}, "scl")

    a = c.act("fiat", 2.4, [1.2])
    P(a, "glow_core", {0: [1, 1, 1], 1.0: [2.2, 2.2, 2.2], 1.2: [0.7, 0.7, 0.7], 2.4: [1, 1, 1]}, "scl")
    P(a, "halo", {0: [0, 0, 0], 1.2: [0, 0, 180], 2.4: [0, 0, 220]})
    P(a, "body", {0: [0, 0, 0], 1.0: [0, 4, 0], 1.2: [0, -2, 0], 2.4: [0, 0, 0]}, "pos")

    a = c.act("lances", 1.8, [0.6])
    P(a, "glow_halo", {0: [1, 1, 1], 0.4: [1.25, 1.25, 1.25], 0.6: [0.9, 0.9, 0.9], 1.8: [1, 1, 1]}, "scl")
    P(a, "halo", {0: [0, 0, 0], 0.6: [0, 0, 90], 1.8: [0, 0, 120]})

    a = c.act("gaze", 3.0, [0.8])
    P(a, "core", {0: [0, 0, 0], 0.8: [0, -50, 0], 2.6: [0, 50, 0], 3.0: [0, 0, 0]})
    P(a, "glow_core", {0: [1, 1, 1], 0.8: [1.3, 1.3, 1.3], 2.6: [1.3, 1.3, 1.3], 3.0: [1, 1, 1]}, "scl")

    a = c.act("trumpet", 2.2, [0.6, 1.2, 1.8])
    for name in ("wing_ur", "wing_ul", "wing_dr", "wing_dl"):
        s = -1 if name.endswith("r") else 1
        P(a, f"{name}0", {0: [0, 0, 0], 0.45: [0, 40 * s, 0], 0.6: [0, -30 * s, 0], 1.05: [0, 40 * s, 0], 1.2: [0, -30 * s, 0],
                          1.65: [0, 40 * s, 0], 1.8: [0, -30 * s, 0], 2.2: [0, 0, 0]})

    a = c.act("babel", 3.2, [0.5])
    P(a, "body", {0: [0, 0, 0], 0.5: [0, 60, 0], 2.8: [0, 720, 0], 3.2: [0, 720, 0]})

    a = c.act("reforge", 2.5, [1.8])
    for name in ("wing_ur", "wing_ul", "wing_dr", "wing_dl"):
        s = -1 if name.endswith("r") else 1
        P(a, f"{name}0", {0: [0, 0, 0], 1.2: [0, 70 * s, 0], 1.8: [0, -20 * s, 0], 2.5: [0, 0, 0]})
    P(a, "glow_core", {0: [1, 1, 1], 1.2: [1.5, 1.5, 1.5], 1.8: [1, 1, 1]}, "scl")

    a = c.act("unseal", 2.0, [1.0])
    P(a, "seals", {0: [1, 1, 1], 0.8: [1.3, 1.3, 1.3], 1.0: [0.9, 0.9, 0.9], 2.0: [1, 1, 1]}, "scl")
    P(a, "seals", {0: [0, 0, 0], 1.0: [0, 180, 0], 2.0: [0, 200, 0]})

    a = c.act("apocalypse", 14.0, [3.0, 8.0, 12.6])
    P(a, "body", {0: [0, 0, 0], 3.0: [0, 30, 0], 12.6: [0, 30, 0], 14.0: [0, 0, 0]}, "pos")
    P(a, "halo", {0: [1, 1, 1], 3.0: [1.8, 1.8, 1.8], 12.4: [2.1, 2.1, 2.1], 12.6: [2.6, 2.6, 2.6], 14.0: [1, 1, 1]}, "scl")
    P(a, "halo", {0: [0, 0, 0], 14.0: [0, 0, 720]})
    P(a, "glow_core", {0: [1, 1, 1], 3.0: [1.6, 1.6, 1.6], 12.2: [2.4, 2.4, 2.4], 12.6: [3.2, 3.2, 3.2], 14.0: [1, 1, 1]}, "scl")
    for name in ("wing_ur", "wing_ul", "wing_dr", "wing_dl"):
        s = -1 if name.endswith("r") else 1
        up = 1 if name.startswith("wing_u") else -1
        P(a, f"{name}0", {0: [0, 0, 0], 3.0: [0, 35 * s, 12 * s * up], 12.6: [0, 35 * s, 16 * s * up], 14.0: [0, 0, 0]})

    a = c.act("death", 6.0, [5.0])
    P(a, "halo", {0: [1, 1, 1], 2.0: [1.4, 1.4, 1.4], 5.0: [0.05, 0.05, 0.05]}, "scl")
    P(a, "seals", {0: [1, 1, 1], 2.0: [1.8, 1.8, 1.8], 4.0: [0.05, 0.05, 0.05]}, "scl")
    P(a, "glow_core", {0: [1, 1, 1], 4.5: [3.0, 3.0, 3.0], 5.0: [0.1, 0.1, 0.1]}, "scl")
    P(a, "body", {0: [0, 0, 0], 5.0: [0, -20, 0], 6.0: [0, -24, 0]}, "pos")
    for name in ("wing_ur", "wing_ul", "wing_dr", "wing_dl"):
        P(a, f"{name}0", {0: [1, 1, 1], 3.0: [1, 1, 1], 5.0: [0.05, 0.05, 0.05]}, "scl")
    return c


# =========================================================================== SERAPH

def build_seraph() -> Creature:
    m = Model("geometry.legends.seraph", seed=707)
    m.bounds = (6.0, 5.0, 1.6)
    FIRE = flame("fffbe0", "ffa52e", "e8361b", cut=False)
    FEATH = feathers("ffd9a0", "ff5a1f", "ffe9c4", row=2, tip_from=0.45)
    FEATH_IN = feathers("fff2d6", "ffb347", "fff7e6", row=2, tip_from=0.6, ragged=False)
    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 22, 0), "root")
    body.add((-3.5, 12, -3.5), (7, 18, 7), FIRE)
    body.add((-2.5, 9, -2.5), (5, 4, 5), FIRE)
    gb = m.bone("glow_body", (0, 22, 0), "body")
    gb.add((-2, 14, -2.2), (4, 13, 4.4), glowball("ffffff", "ffcf6a"))
    gb.add((-2.8, 28, -2.8), (5.6, 5.6, 5.6), glowball("ffffff", "ffd98a"))                # the veiled head-light

    def wing(name, pivot, base_rot, length, width, mat, n=4):
        s = -1 if name.endswith("_r") else 1
        b = m.bone(name, pivot, "body", base_rot)
        x, y, z = pivot
        b.add((x + (-length if s < 0 else 0), y - 1, z - 1), (length, 2, 2.4), FIRE, mirror=s > 0)
        for k in range(n):
            fx = x + s * (length * (k + 0.6) / n)
            b.add((fx - width / 2, y - 0.25, z), (width, 0.5, 9 + k * 2.2), mat, pivot=(fx, y, z),
                  rotation=(0, s * (6 + k * 7), 0), share=f"{name[:-2]}{k}", mirror=s > 0)
        return b
    # two wings veil the face, two fly, two veil the feet
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        wing(f"wing_face_{side}", (s * 2.5, 31, -2), (-70, s * 60, 0), 9, 3.2, FEATH_IN)
        wing(f"wing_fly_{side}", (s * 3, 26, 2), (0, 0, 0), 15, 3.6, FEATH, n=5)
        wing(f"wing_feet_{side}", (s * 2.5, 13, -1), (70, s * 55, 0), 8, 3.0, FEATH_IN)
    # arm with tongs holding the live coal
    arm = m.bone("arm", (-3, 20, -2), "body", (-50, 0, 10))
    arm.add((-4, 11, -3), (2, 10, 2), FIRE)
    arm.add((-3.6, 4, -2.6), (0.6, 8, 0.6), GOLD_D)
    arm.add((-2.6, 4, -2.6), (0.6, 8, 0.6), GOLD_D)
    coal = m.bone("glow_coal", (-3, 3.5, -2.3), "arm")
    coal.add((-4.2, 2, -3.5), (2.4, 2.4, 2.4), glowball("fff1c0", "ff4a14"))
    m.get("body").loc("coal", (-3, 3, -10))

    c = Creature("seraph", m, scale=1.15, description="Seraph of the Burning Choir")
    c.pre = COMMON_PRE[:]
    t = "q.life_time"
    idle = c.loop("idle")
    idle.pos("body", [0, wave(1.2, 140), 0])
    fl = f"{t} * 300"
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        idle.rot(f"wing_fly_{side}", [0, 0, f"(math.sin({fl}) * 40 + 5) * {-s}"])
        idle.rot(f"wing_face_{side}", [wave(3, 300, -60), 0, 0])
        idle.rot(f"wing_feet_{side}", [wave(3, 300, -120), 0, 0])
    idle.scl("glow_body", [f"1 + {wave(0.06, 500)}", f"1 + {wave(0.08, 430)}", f"1 + {wave(0.06, 500)}"])

    def P(a, bone, frames, ch="rot"):
        (a.rot if ch == "rot" else a.pos if ch == "pos" else a.scl)(bone, kf(frames))
    a = c.act("spawn", 2.0, [1.2])
    P(a, "root", {0: [0.05, 0.05, 0.05], 1.2: [1.1, 1.1, 1.1], 2.0: [1, 1, 1]}, "scl")
    a = c.act("dive", 1.6, [0.8])
    P(a, "body", {0: [0, 0, 0], 0.5: [-30, 0, 0], 0.8: [60, 0, 0], 1.6: [0, 0, 0]})
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        P(a, f"wing_fly_{side}", {0: [0, 0, 0], 0.5: [0, 0, 50 * -s], 0.8: [0, 60 * -s, 0], 1.6: [0, 0, 0]})
    a = c.act("coal", 1.2, [0.6])
    P(a, "arm", {0: [0, 0, 0], 0.4: [-70, 0, 0], 0.6: [60, 0, 0], 1.2: [0, 0, 0]})
    a = c.act("sanctus", 2.4, [0.6, 1.2, 1.8])
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        P(a, f"wing_fly_{side}", {0: [0, 0, 0], 0.5: [0, -30 * s, 30 * -s], 0.6: [0, 30 * s, -30 * -s], 1.1: [0, -30 * s, 30 * -s],
                                  1.2: [0, 30 * s, -30 * -s], 1.7: [0, -30 * s, 30 * -s], 1.8: [0, 30 * s, -30 * -s], 2.4: [0, 0, 0]})
    P(a, "glow_body", {0: [1, 1, 1], 0.6: [1.5, 1.3, 1.5], 1.2: [1.6, 1.4, 1.6], 1.8: [1.8, 1.5, 1.8], 2.4: [1, 1, 1]}, "scl")
    a = c.act("trisagion", 3.6, [0.9, 1.9, 2.9])
    P(a, "body", {0: [0, 0, 0], 0.9: [0, 6, 0], 1.9: [0, 10, 0], 2.9: [0, 14, 0], 3.6: [0, 0, 0]}, "pos")
    P(a, "root", {0: [0, 0, 0], 3.6: [0, 1080, 0]})
    P(a, "glow_body", {0: [1, 1, 1], 0.9: [2, 1.6, 2], 1.9: [2.4, 1.8, 2.4], 2.9: [2.8, 2, 2.8], 3.6: [1, 1, 1]}, "scl")
    a = c.act("death", 2.0, [1.6])
    P(a, "root", {0: [1, 1, 1], 1.0: [1.3, 1.3, 1.3], 1.6: [0.05, 0.05, 0.05]}, "scl")
    return c


# =========================================================================== CHERUB

def build_cherub() -> Creature:
    m = Model("geometry.legends.cherub", seed=808)
    m.bounds = (6.0, 6.0, 2.0)
    BRONZE = gold("c98a3c", "5c3412", "f3c98a", sparkle=0.06)
    BRONZE_D = gold("a26a2a", "4a2a0e", "dca064", sparkle=0.03)
    SKIN = solid("e7c9a0", 0.04)
    LION = fur("d9a441", "8a5a1c", "f3cf7a", streak=1.2)
    OX = fur("6b4a32", "3a2416", "8f6a4a", streak=1.0)
    EAGLE = feathers("efe6d6", "6b4a2a", "f9f3e8", row=2, tip_from=0.6, ragged=False)
    FEATH = feathers("f6efe2", "c9a24f", "fff7e8", row=2, tip_from=0.5)
    STEEL = solid("e8edf3", 0.03)
    FIRE = flame("fffbe0", "ffa52e", "ff4a1a", cut=False)
    HOOF = solid("c98a3c", 0.06)

    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 22, 0), "root")
    body.add((-5, 22, -3), (10, 13, 6), BRONZE, inflate=0.2)
    body.add((-4, 16, -2.5), (8, 6, 5), BRONZE_D)
    body.add((-5.4, 30, -3.4), (10.8, 2, 6.8), GOLD)
    # straight fused legs with calf's hooves
    body.add((-3.2, 4, -2.2), (6.4, 12.5, 4.4), BRONZE)
    body.add((-3.6, 0, -3), (3.2, 4, 5), HOOF)
    body.add((0.4, 0, -3), (3.2, 4, 5), HOOF)
    for s in (-1, 1):
        body.add((s * 1.6 - 0.3, 0, -3.2), (0.6, 4, 0.6), solid("3b220c"))
    # hands of a man under the wings
    for s in (-1, 1):
        body.add((s * 6 - 1.2, 18, -1.2), (2.4, 9, 2.4), SKIN, pivot=(s * 6, 27, 0), rotation=(-25, 0, 8 * s))
    # head with four faces: man (front), lion (right = east), ox (left = west), eagle (back)
    head = m.bone("head", (0, 35, 0), "body")
    head.add((-4, 35, -4), (8, 8, 8), SKIN,
             decals={"north": d_pixels(["........", ".KK..KK.", "........", "...SS...", "..R..R..", "...RR..."],
                                       {"K": "2a2014", "S": "c9a77e", "R": "8a3a2a"}, center=True)},
             face_mats={"east": LION, "west": OX, "south": EAGLE})
    head.add((-4.8, 34, -3), (1, 9, 7), LION)                                       # lion's mane (right)
    head.add((-5.4, 35, -2), (1, 7, 5), shade_mat("b8822a"))
    head.add((-5.2, 38, -1), (0.4, 1.2, 1.2), solid("1a1208"))
    head.add((3.8, 40, -1), (1.4, 1.4, 2), OX)                                       # ox horns (left)
    head.add((5, 41, -0.6), (4, 1.2, 1.2), bone_mat("efe6cf", "a89a7a"), pivot=(5, 41.6, 0), rotation=(0, 0, 25))
    head.add((-1, 41, -0.6), (1, 1, 1), OX)
    head.add((4.0, 36, -2.5), (1.8, 2.4, 3), OX)                                     # ox muzzle
    head.add((-1.2, 37.5, 4), (2.4, 2, 3), GOLD)                                     # eagle beak (back)
    head.add((-0.8, 36.6, 6.6), (1.6, 1.2, 1.2), GOLD_D)
    head.add((-4.4, 43, -4.4), (8.8, 1.2, 8.8), GOLD)
    gh = m.bone("glow_eyes", (0, 39, 0), "head")
    gh.add((-2.6, 39.6, -4.2), (1.6, 0.8, 0.4), LIGHT)
    gh.add((1.0, 39.6, -4.2), (1.6, 0.8, 0.4), LIGHT)
    gh.add((-4.25, 39.4, -2.6), (0.4, 0.8, 1.4), LIGHT)
    gh.add((3.85, 39.4, -2.6), (0.4, 0.8, 1.4), LIGHT)
    # four wings: two spread upward, two folded down covering the body
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        up = m.bone(f"wing_up_{side}", (s * 4, 33, 3), "body", (0, 0, -55 * s))
        up.add((s * 4 + (-16 if s < 0 else 0), 32, 2), (16, 2, 2), BRONZE, mirror=s > 0)
        for k in range(5):
            fx = s * (4 + 16 * (k + 0.6) / 5)
            up.add((fx - 1.6, 32.6, 3), (3.2, 0.5, 8 + k * 1.5), FEATH, pivot=(fx, 33, 3), rotation=(0, s * (4 + k * 6), 0),
                   share=f"cwu{k}", mirror=s > 0)
        dn = m.bone(f"wing_dn_{side}", (s * 4, 30, 2.5), "body", (-75, s * 20, 60 * s))
        dn.add((s * 4 + (-12 if s < 0 else 0), 29, 1.5), (12, 2, 2), BRONZE, mirror=s > 0)
        for k in range(4):
            fx = s * (4 + 12 * (k + 0.6) / 4)
            dn.add((fx - 1.6, 29.6, 2.5), (3.2, 0.5, 7 + k * 1.4), FEATH, pivot=(fx, 30, 2.5), rotation=(0, s * (4 + k * 5), 0),
                   share=f"cwd{k}", mirror=s > 0)
    # the flaming sword that turns every way (orbits the Cherub)
    orbit = m.bone("sword_orbit", (0, 26, 0), "root")
    sw = m.bone("sword", (0, 26, -13), "sword_orbit", (90, 0, 0))
    sw.add((-0.8, 24.5, -14.5), (1.6, 4, 3), GOLD)
    sw.add((-2.6, 28, -14), (5.2, 1, 2), GOLD)
    sw.add((-0.6, 29, -13.6), (1.2, 16, 1.2), STEEL)
    gsw = m.bone("glow_sword", (0, 36, -13), "sword")
    gsw.add((-1.3, 29, -14.1), (2.6, 16, 2.2), glowball("fffbe0", "ff7a1a"))
    m.get("root").loc("sword_tip", (0, 26, -30))

    c = Creature("cherub", m, scale=1.2, description="Cherub of the Eastern Gate")
    c.pre = COMMON_PRE[:]
    t = "q.life_time"
    idle = c.loop("idle")
    idle.pos("body", [0, wave(1.0, 90), 0])
    idle.rot("head", [0, wave(25, 30), 0])
    idle.rot("sword_orbit", [0, f"{t} * 120", 0])
    idle.rot("sword", [wave(10, 120), 0, f"{t} * 360"])
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        idle.rot(f"wing_up_{side}", [0, 0, f"{wave(10, 120)} * {-s}"])
        idle.rot(f"wing_dn_{side}", [wave(3, 120, -60), 0, 0])

    def P(a, bone, frames, ch="rot"):
        (a.rot if ch == "rot" else a.pos if ch == "pos" else a.scl)(bone, kf(frames))
    a = c.act("spawn", 2.0, [1.2])
    P(a, "root", {0: [0.05, 0.05, 0.05], 1.2: [1.1, 1.1, 1.1], 2.0: [1, 1, 1]}, "scl")
    a = c.act("sweep", 1.6, [0.8])
    P(a, "sword_orbit", {0: [0, 0, 0], 0.5: [0, -60, 0], 0.8: [0, 300, 0], 1.6: [0, 360, 0]})
    P(a, "sword_orbit", {0: [1, 1, 1], 0.5: [1.5, 1, 1.5], 1.2: [1.5, 1, 1.5], 1.6: [1, 1, 1]}, "scl")
    a = c.act("ward", 2.0, [0.8], loop="hold_on_last_frame")
    P(a, "head", {0: [0, 0, 0], 0.6: [-15, 0, 0], 2.0: [-15, 0, 0]})
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        P(a, f"wing_up_{side}", {0: [0, 0, 0], 0.6: [0, 0, -30 * s], 2.0: [0, 0, -30 * s]})
    a = c.act("gaze4", 2.4, [0.6, 1.2, 1.8])
    P(a, "head", {0: [0, 0, 0], 0.6: [0, 90, 0], 1.2: [0, 180, 0], 1.8: [0, 270, 0], 2.4: [0, 360, 0]})
    a = c.act("gate", 3.0, [2.0])
    P(a, "sword_orbit", {0: [0, 0, 0], 1.0: [0, 0, 0], 2.0: [0, 0, 0]})
    P(a, "sword", {0: [0, 0, 0], 1.0: [-90, 0, 0], 2.0: [-90, 0, 0], 3.0: [0, 0, 0]})
    P(a, "sword", {0: [0, 0, 0], 1.0: [0, 12, 0], 2.0: [0, -10, 0], 3.0: [0, 0, 0]}, "pos")
    P(a, "body", {0: [0, 0, 0], 1.0: [-20, 0, 0], 2.0: [20, 0, 0], 3.0: [0, 0, 0]})
    a = c.act("death", 2.0, [1.6])
    P(a, "root", {0: [1, 1, 1], 1.0: [1.3, 1.3, 1.3], 1.6: [0.05, 0.05, 0.05]}, "scl")
    return c


def shade_mat(hexcol):
    return solid(hexcol, 0.08)


# =========================================================================== OPHAN (Thrones)

def build_ophan() -> Creature:
    m = Model("geometry.legends.ophan", seed=909)
    m.bounds = (5.0, 5.0, 1.8)
    BERYL = eyes_band("3fb8a0", "fbf6e6", "2a6fd6", "07101c", period=4)
    BERYL2 = eyes_band("5fd0b4", "fbf6e6", "d6a12a", "07101c", period=4)
    RIM = gold("8fe0c9", "2d7a68", "e8fff8", sparkle=0.05)
    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 24, 0), "root")
    gc = m.bone("glow_heart", (0, 24, 0), "body")
    gc.add((-3, 21, -3), (6, 6, 6), glowball("ffffff", "ff9a2a"), pivot=(0, 24, 0), rotation=(45, 45, 0))
    gc.add((-2, 22, -2), (4, 4, 4), glowball("fff9d8", "ffd36a"))
    w1 = m.bone("wheel1", (0, 24, 0), "body")
    ring_cubes(w1, (0, 24, 0), 14, 20, 2.6, 3.0, BERYL, plane="xy")
    ring_cubes(w1, (0, 24, 0), 15.6, 20, 0.8, 3.4, RIM, plane="xy", phase=9)
    w2 = m.bone("wheel2", (0, 24, 0), "body")
    ring_cubes(w2, (0, 24, 0), 11, 16, 2.4, 2.6, BERYL2, plane="yz")
    w3 = m.bone("wheel3", (0, 24, 0), "body")
    ring_cubes(w3, (0, 24, 0), 8, 12, 2.0, 2.2, BERYL, plane="xz")
    # spokes of fire from the heart to the first wheel
    sp = m.bone("glow_spokes", (0, 24, 0), "wheel1")
    for k in range(6):
        sp.add((-0.6, 24, -0.6), (1.2, 12, 1.2), glowball("fff6d0", "ffb03a"), pivot=(0, 24, 0), rotation=(0, 0, k * 60))

    c = Creature("ophan", m, scale=1.15, description="Ophan of the Thrones")
    c.pre = COMMON_PRE[:]
    t = "q.life_time"
    idle = c.loop("idle")
    idle.pos("body", [0, wave(1.4, 70), 0])
    idle.rot("wheel1", [0, f"{t} * 25", f"{t} * 90"])
    idle.rot("wheel2", [f"{t} * 120", 0, 0])
    idle.rot("wheel3", [0, f"-{t} * 160", 0])
    idle.rot("glow_heart", [f"{t} * 60", f"{t} * 80", 0])

    def P(a, bone, frames, ch="rot"):
        (a.rot if ch == "rot" else a.pos if ch == "pos" else a.scl)(bone, kf(frames))
    a = c.act("spawn", 2.0, [1.2])
    P(a, "root", {0: [0.05, 0.05, 0.05], 1.2: [1.1, 1.1, 1.1], 2.0: [1, 1, 1]}, "scl")
    a = c.act("roll", 1.6, [0.6])
    P(a, "body", {0: [0, 0, 0], 1.6: [720, 0, 0]})
    a = c.act("eyes", 2.4, [0.8])
    P(a, "body", {0: [1, 1, 1], 0.6: [1.2, 1.2, 1.2], 2.0: [1.2, 1.2, 1.2], 2.4: [1, 1, 1]}, "scl")
    a = c.act("restore", 4.0, [], loop="hold_on_last_frame")
    P(a, "glow_heart", {0: [1, 1, 1], 0.6: [1.6, 1.6, 1.6], 3.6: [1.6, 1.6, 1.6], 4.0: [1, 1, 1]}, "scl")
    a = c.act("wheels", 4.0, [1.0])
    P(a, "wheel1", {0: [1, 1, 1], 1.0: [1.8, 1.8, 1.8], 3.6: [1.8, 1.8, 1.8], 4.0: [1, 1, 1]}, "scl")
    P(a, "wheel2", {0: [1, 1, 1], 1.0: [1.6, 1.6, 1.6], 3.6: [1.6, 1.6, 1.6], 4.0: [1, 1, 1]}, "scl")
    P(a, "body", {0: [0, 0, 0], 4.0: [0, 1440, 0]})
    a = c.act("death", 2.0, [1.6])
    P(a, "root", {0: [1, 1, 1], 1.0: [1.3, 1.3, 1.3], 1.6: [0.05, 0.05, 0.05]}, "scl")
    return c
