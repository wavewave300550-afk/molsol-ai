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

from .common import COMMON_PRE, Creature, chain, ellipsoid, kf, mrot, obox, ring_cubes, scale_subtree, tuft, wave
from mk.geo import Model
from mk.paint import (C, bake, cloth, crystal, d_center_gem, d_pixels, eyes_band, feathers, flame, glowball, glyphs,
                      gold, hx, marble, mix, shade, solid, fur, horn, bone_mat, metal, plush)

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
    m = Model("geometry.legends.logos", seed=606, density=1.5)
    m.bounds = (12.0, 12.0, 4.5)
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
    # ---------------------------------------------------------- gyroscope rings around the core + an outer halo
    RUNE = glyphs("f5d470", "7a4a0c", rows=2, seed=41, margin=0)
    ga = m.bone("gyro_a", (0, 44, 0), "body")
    ring_cubes(ga, (0, 44, 0), 13.5, 22, 1.4, 1.6, RUNE, plane="yz")
    gb_ = m.bone("gyro_b", (0, 44, 0), "body")
    ring_cubes(gb_, (0, 44, 0), 15.5, 26, 1.2, 1.4, RUNE, plane="xz")
    ho = m.bone("glow_halo_outer", (0, 44, 9), "halo")
    for k in range(24):
        a = math.radians(k * 15 + 7.5)
        px, py = math.cos(a) * 31, 44 + math.sin(a) * 31
        ho.add((px - 0.6, py - 1.8, 8.6), (1.2, 3.6 + (k % 2) * 2, 0.8), LIGHT, pivot=(px, py, 9), rotation=(0, 0, -(k * 15 + 7.5 - 90)))
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
        for j, nb in enumerate(names):
            b = m.get(nb)
            x, y, z = b.pivot
            L = lens[j]
            b.add((x + (-L if s < 0 else 0), y - 5.6, z - 1.1), (L, 0.8, 2.2), GOLD, mirror=s > 0)
            b.add((x + (-L if s < 0 else 0), y + 4.8, z - 1.1), (L, 0.8, 2.2), GOLD, mirror=s > 0)
            gg = m.bone(f"glow_script_{name}{j}", b.pivot, nb)                       # luminous lines of script
            for row in (-2.6, 0, 2.6):
                gg.add((x + (-L + 1 if s < 0 else 1), y + row - 0.3, z - 0.95), (L - 2, 0.6, 0.25),
                       glyphs("fff3c4", "d79a2a", rows=2, seed=j + 3, margin=0, light=False), density=2)
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

    c = Creature("logos", m, scale=2.0, description="The Word of God")
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
    idle.rot("gyro_a", [f"{t} * 35", 0, f"{t} * 12"])
    idle.rot("gyro_b", [f"{t} * 10", f"-{t} * 28", 0])
    idle.rot("glow_halo_outer", [0, 0, f"-{t} * 20"])
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
    m = Model("geometry.legends.seraph", seed=707, density=2.0)
    m.bounds = (8.0, 7.0, 2.0)
    FIRE = flame("fffbe0", "ffa52e", "e8361b", cut=False)
    FEATH = feathers("fff4d0", "ff3a12", "ffe6a8", row=3, tip_from=0.3, axis="v")
    FEATH_IN = feathers("fffbea", "ff9a2a", "fff4dc", row=3, tip_from=0.4, ragged=False, axis="v")
    GOLD_F = gold("ffd36a", "a8620e", "fff6d0", sparkle=0.08)
    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 22, 0), "root")
    ellipsoid(body, (0, 21, 0), (3.8, 9, 3.8), FIRE, layers=4)
    obox(body, (-2.4, 8, -2.4), (4.8, 5, 4.8), FIRE)
    gb = m.bone("glow_body", (0, 22, 0), "body")
    ellipsoid(gb, (0, 21.5, 0), (2.4, 6.5, 2.4), glowball("ffffff", "ffd36a"), layers=3)
    gb.add((-3, 28, -3), (6, 6, 6), glowball("ffffff", "ffe9a8"))                     # the veiled head-light
    gh = m.bone("glow_halo", (0, 36, 0), "body")
    ring_cubes(gh, (0, 36, 1), 5, 14, 0.9, 0.6, glowball("fffbe0", "ffc84a"), plane="xy")

    def wing(name, pivot, base_rz, length, n, mat, chord, z_off=0.0):
        """A wing in the frontal plane: arm along X, feathers hanging along -Y and fanning toward the tip."""
        s = -1 if name.endswith("_r") else 1
        b = m.bone(name, pivot, "body", (0, 0, base_rz * -s))
        x, y, z = pivot
        z += z_off
        x0 = x + (-length if s < 0 else 0)
        obox(b, (x0, y - 1.2, z - 1.2), (length, 2.4, 2.4), FIRE, axis="x", mirror=s > 0)
        b.add((x0, y + 1.0, z - 0.6), (length, 0.8, 1.2), GOLD_F, mirror=s > 0)
        for k in range(n):
            fx = x + s * (length * (k + 0.5) / n)
            L = chord + k * 2.2
            b.add((fx - 1.8, y - L, z - 0.3 - k * 0.05), (3.6, L, 0.6), mat, pivot=(fx, y, z),
                  rotation=(0, 0, s * (k * 5)), mirror=s > 0)
        return b
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        wing(f"wing_face_{side}", (s * 2, 33, -2.6), 52, 13, 5, FEATH_IN, 7, z_off=-0.6)    # crossing above: veil the face
        wing(f"wing_fly_{side}", (s * 3, 27, 0), 4, 21, 7, FEATH, 9)                       # spread wide: fly
        wing(f"wing_feet_{side}", (s * 2, 15, -2.4), -50, 11, 5, FEATH_IN, 6, z_off=-0.6)   # crossing below: veil the feet
    arm = m.bone("arm", (-3, 20, -2), "body", (-50, 0, 10))
    obox(arm, (-4.2, 11, -3.2), (2.4, 10, 2.4), FIRE)
    arm.add((-3.8, 3.5, -2.8), (0.6, 8, 0.6), GOLD_F)
    arm.add((-2.6, 3.5, -2.8), (0.6, 8, 0.6), GOLD_F)
    coal = m.bone("glow_coal", (-3, 3.5, -2.3), "arm")
    coal.add((-4.4, 1.6, -3.7), (2.8, 2.8, 2.8), glowball("fff1c0", "ff4a14"))
    m.get("body").loc("coal", (-3, 3, -10))

    c = Creature("seraph", m, scale=1.5, description="Seraph of the Burning Choir")
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
    idle.rot("glow_halo", [0, 0, f"{t} * 40"])

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
    m = Model("geometry.legends.cherub", seed=808, density=2.0)
    m.bounds = (8.0, 7.0, 2.2)
    BRONZE = gold("d39a46", "5c3412", "f8d79a", sparkle=0.06)
    BRONZE_D = gold("a8702e", "4a2a0e", "e2ad70", sparkle=0.03)
    GOLDP = gold("f5d470", "8f6413", "fffae0", sparkle=0.08)
    SKIN = solid("ecd2ac", 0.04)
    LION = plush("dda846", "8a5a1c", "f6d27e")
    OX = plush("6f4c33", "3a2416", "93704f")
    EAGLE = feathers("f2eadb", "6b4a2a", "fbf6ec", row=2, tip_from=0.6, ragged=False)
    FEATH = feathers("fffaf0", "e0b450", "fff4dc", row=3, tip_from=0.45)
    STEEL = solid("eef2f7", 0.03)
    HOOF = gold("c98a3c", "6a4214", "e8b880")
    GEM = d_pixels([".RR.", "RWWR", "RWWR", ".RR."], {"R": "c4182c", "W": "ffb0b8"}, center=True)

    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 22, 0), "root")
    ellipsoid(body, (0, 29, 0), (5.6, 6.5, 3.8), BRONZE, layers=3)                    # cuirass
    body.add((-2, 30, -4.4), (4, 4, 1), GOLDP, decals={"north": GEM})
    obox(body, (-6, 34, -3.5), (12, 2, 7), GOLDP)                                    # collar
    for s_ in (-1, 1):
        ellipsoid(body, (s_ * 6.2, 33, 0), (2.6, 2.4, 3.2), GOLDP, layers=2)        # pauldrons
    obox(body, (-4.6, 21, -3), (9.2, 3, 6), BRONZE_D)                               # belt
    for k, (w, y) in enumerate(((10, 18), (11, 15), (12, 12))):                      # layered skirt plates
        obox(body, (-w / 2, y, -3.6 - k * 0.3), (w, 3.4, 7.2 + k * 0.6), BRONZE if k % 2 == 0 else BRONZE_D)
    obox(body, (-3.4, 4, -2.3), (6.8, 8.5, 4.6), BRONZE)                             # straight fused legs
    for s_ in (-1, 1):
        obox(body, (s_ * 1.9 - 1.7, 0, -3.2), (3.4, 4, 5), HOOF, axis="z")            # calf's hooves
        body.add((s_ * 1.9 - 0.3, 0, -3.4), (0.6, 4, 0.6), solid("3b220c"))
        obox(body, (s_ * 6.5 - 1.3, 19, -1.3), (2.6, 9, 2.6), SKIN)                    # hands of a man
        obox(body, (s_ * 6.5 - 1.6, 21, -1.6), (3.2, 2, 3.2), GOLDP)
    # head with four faces: man (front), lion (right = east), ox (left = west), eagle (back)
    head = m.bone("head", (0, 37, 0), "body")
    obox(head, (-4.2, 37, -4.2), (8.4, 8.4, 8.4), SKIN, axis="y",
         face_mats={"east": LION, "west": OX, "south": EAGLE})
    head.add((-3.6, 39, -4.5), (7.2, 5, 0.5), SKIN, decals={"north": d_pixels(
        ["........", ".KK..KK.", "........", "...SS...", "..R..R..", "...RR..."], {"K": "2a2014", "S": "c9a77e", "R": "8a3a2a"}, center=True)})
    for k in range(6):                                                                 # lion's mane (right)
        tuft(head, (-4.8, 37.5 + k * 1.4, -1 + (k % 2)), (1.4, 3, 7), LION, roll=-20 + k * 8, yaw=0)
    head.add((-5.4, 40, -3.2), (1.2, 2.6, 3), plush("c08a2c", "7a4a14", "e0b050"))     # lion snout
    head.add((4.2, 39, -3.4), (2, 3, 3.6), OX)                                        # ox muzzle (left)
    for s_ in (1,):
        tuft(head, (6.5, 44.5, 0), (5, 1.4, 1.4), bone_mat("efe6cf", "a89a7a"), roll=30)
        tuft(head, (5.5, 44, -1.5), (1.4, 1.4, 1.4), OX)
    tuft(head, (0, 40.5, 5.4), (2.6, 2.2, 3.4), GOLDP, pitch=20)                      # eagle beak (back)
    obox(head, (-4.8, 45.2, -4.8), (9.6, 1.4, 9.6), GOLDP)
    for k in range(8):                                                                 # crown points
        a = math.radians(k * 45)
        tuft(head, (math.cos(a) * 4, 47.2, math.sin(a) * 4), (1.2, 2.6, 1.2), GOLDP)
    gh = m.bone("glow_eyes", (0, 40, 0), "head")
    gh.add((-2.6, 40.6, -4.75), (1.6, 0.8, 0.4), LIGHT)
    gh.add((1.0, 40.6, -4.75), (1.6, 0.8, 0.4), LIGHT)
    gh.add((-4.45, 40.4, -2.6), (0.4, 0.8, 1.4), LIGHT)
    gh.add((4.05, 40.4, -2.6), (0.4, 0.8, 1.4), LIGHT)
    # four wings: two spread upward, two folded down covering the body
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        up = m.bone(f"wing_up_{side}", (s * 4.5, 34, 3), "body", (0, 0, -55 * s))
        x0 = s * 4.5 + (-19 if s < 0 else 0)
        obox(up, (x0, 32.9, 1.9), (19, 2.2, 2.4), BRONZE, axis="x", mirror=s > 0)
        up.add((x0, 34.3, 1.6), (19, 0.8, 1), GOLDP, mirror=s > 0)
        for k in range(7):
            fx = s * (4.5 + 19 * (k + 0.5) / 7)
            up.add((fx - 1.7, 33.6, 3), (3.4, 0.5, 9 + k * 1.4), FEATH, pivot=(fx, 34, 3), rotation=(0, s * (4 + k * 5), 0),
                   mirror=s > 0)
        dn = m.bone(f"wing_dn_{side}", (s * 4.5, 31, 2.5), "body", (-75, s * 20, 60 * s))
        x1 = s * 4.5 + (-14 if s < 0 else 0)
        obox(dn, (x1, 30, 1.5), (14, 2, 2), BRONZE, axis="x", mirror=s > 0)
        for k in range(5):
            fx = s * (4.5 + 14 * (k + 0.5) / 5)
            dn.add((fx - 1.7, 30.6, 2.5), (3.4, 0.5, 8 + k * 1.2), FEATH, pivot=(fx, 31, 2.5), rotation=(0, s * (4 + k * 5), 0),
                   mirror=s > 0)
    # the flaming sword that turns every way (orbits the Cherub)
    orbit = m.bone("sword_orbit", (0, 26, 0), "root")
    sw = m.bone("sword", (0, 26, -13), "sword_orbit", (90, 0, 0))
    sw.add((-0.8, 24.5, -14.5), (1.6, 4, 3), GOLD)
    sw.add((-2.6, 28, -14), (5.2, 1, 2), GOLD)
    sw.add((-0.7, 29, -13.7), (1.4, 22, 1.4), STEEL)
    gsw = m.bone("glow_sword", (0, 38, -13), "sword")
    gsw.add((-1.5, 29, -14.3), (3, 22, 2.6), glowball("fffbe0", "ff7a1a"))
    gsw.add((-0.9, 51, -13.7), (1.8, 3, 1.4), glowball("ffffff", "ffb04a"))
    m.get("root").loc("sword_tip", (0, 26, -30))

    c = Creature("cherub", m, scale=1.5, description="Cherub of the Eastern Gate")
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

    c = Creature("ophan", m, scale=1.5, description="Ophan of the Thrones")
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
