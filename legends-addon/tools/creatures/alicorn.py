"""
ALICORN — "Dawnstar Sovereign".

A pearl-white winged unicorn: aurora mane and tail that flow in long ribbons,
layered feathered wings (coverts, secondaries, primaries), gilded hooves and a
spiral crystal horn.  The horn's light changes colour to announce the kind of
spell being woven (no text needed): white = idle, red = ground strike,
blue = projectiles, gold = charge.  Phase III crowns her with orbiting stars
and lights her wingtips.
"""
from __future__ import annotations

from .common import COMMON_PRE, Creature, chain, ellipsoid, kf, mrot, obox, ring_cubes, scale_subtree, tuft, wave
from mk.geo import Model
from mk.paint import (C, bake, crystal, d_pixels, fbm, feathers, fur, glowball, gold, hx, mix, ramp, shade,
                      solid)


def aurora(stops=("ffd1f0", "c9a2ff", "8fd8ff", "b8ffe6"), axis=2, scale=0.05):
    cols = [hx(c) for c in stops]

    def p(f):
        x, y, z = f.p
        k = (f.p[axis] * scale + fbm(x * 0.2, y * 0.2, z * 0.2) * 0.6) % 1.0
        col = ramp(cols + [cols[0]], k)
        strand = (int(x * 2 + z * 2) % 3 == 0)
        col = shade(col, -0.10 if strand else 0.04)
        return bake(col, f, edge=-0.05, top=0.08, bottom=-0.08)
    return p


def sheen(base_painter):
    """Pearl coat with a faint pastel iridescence drifting across the body."""
    cols = [hx("ffe3f6"), hx("e3dcff"), hx("dcf4ff"), hx("fff6dc")]

    def p(f):
        col = base_painter(f)
        x, y, z = f.p
        k = (x * 0.02 + y * 0.035 + z * 0.025 + fbm(x * 0.08, y * 0.08, z * 0.08)) % 1.0
        return mix(col, ramp(cols + [cols[0]], k), 0.35)
    return p


def build() -> Creature:
    m = Model("geometry.legends.alicorn", seed=404, density=2.0)
    m.bounds = (8.0, 7.0, 2.4)

    COAT = sheen(fur("f8f4ff", "d8cdea", "ffffff", streak=0.5, var=0.04))
    COAT_SH = sheen(fur("ece5f8", "c6badf", "f8f6ff", streak=0.5, var=0.04))
    MANE = aurora()
    MANE2 = aurora(("c9a2ff", "8fd8ff", "ffd1f0", "fff1b8"), axis=1)
    HOOF = gold("f0c64a", "8a5d10", "fff6c8")
    GOLD = gold("f5d470", "8f6413", "fffae0", sparkle=0.08)
    FEATH = feathers("fdfbff", "dcccff", "ece4ff", row=3, tip_from=0.5)
    FEATH_P = feathers("fbf8ff", "b49cff", "e2d8ff", row=3, tip_from=0.35)
    FEATH_C = feathers("ffffff", "f1eaff", "f6f2ff", row=3, tip_from=0.75, ragged=False)
    NOSE = solid("e9dcf0", 0.03)
    EYE = glowball("ffffff", "a46bff")
    HORN_W = crystal("eef6ff", "ffffff", "a9c6f0", facet=2)
    HORN_R = crystal("ff8a8a", "ffe6e6", "c02a3a", facet=2)
    HORN_B = crystal("8ad0ff", "e6f8ff", "2a6ac0", facet=2)
    HORN_G = crystal("ffd877", "fff8dc", "c0861a", facet=2)
    STAR = glowball("ffffff", "ffd86a")
    TIP = glowball("ffffff", "c7a6ff")
    GEM = d_pixels([".PP.", "PWWP", "PWWP", ".PP."], {"P": "b07cff", "W": "f3e8ff"}, center=True)

    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 30, 0), "root")
    body.loc("horn_root", (0, 46, -26))
    ellipsoid(body, (0, 30, 0), (7.4, 7.2, 15.5), COAT, layers=5, axis="z")         # barrel
    ellipsoid(body, (0, 29.5, -11.5), (7.8, 8.4, 6.5), COAT, layers=3)               # deep chest
    ellipsoid(body, (0, 31, 11.5), (7.6, 7.6, 7.2), COAT_SH, layers=3)               # haunches
    obox(body, (-5.6, 22.4, -9), (11.2, 2, 18), COAT_SH, axis="z")                   # belly line
    # golden barding: peytral with a gem, girth band and crupper ornament
    body.add((-6.2, 24.6, -18.4), (12.4, 6.5, 1.4), GOLD, decals={"north": GEM})
    for s_ in (-1, 1):
        tuft(body, (s_ * 7, 29, -15.5), (1.2, 8, 6), GOLD, yaw=-25 * s_)
        tuft(body, (s_ * 7.6, 33, 15), (1, 4, 6), GOLD, yaw=20 * s_)
    obox(body, (-7.7, 25.5, -3.2), (15.4, 13, 2.2), GOLD, axis="x")

    # ------------------------------------------------------------------ neck, head, horn
    neck = m.bone("neck", (0, 34, -13), "body", (-38, 0, 0))
    obox(neck, (-4.6, 29, -28), (9.2, 12.5, 17), COAT, axis="z")
    obox(neck, (-3.6, 27.5, -26), (7.2, 3, 13), COAT_SH, axis="z")
    head = m.bone("head", (0, 36, -26), "neck", (38, 0, 0))
    head.loc("horn", (0, 48, -34))
    ellipsoid(head, (0, 35.6, -30.5), (4.3, 4.4, 4.8), COAT, layers=3)              # skull
    obox(head, (-3.1, 30.8, -44), (6.2, 6.4, 13), COAT, axis="z")                   # long face
    obox(head, (-3.5, 30, -38), (7, 3.6, 7), COAT_SH, axis="z")                     # jowls
    head.add((-2.8, 29.6, -46), (5.6, 3.8, 4.4), NOSE,
             decals={"north": d_pixels(["K....K", "......", ".MMMM."], {"K": "6b5a7a", "M": "c9b0d6"}, center=True)})
    for s_ in (-1, 1):
        tuft(head, (s_ * 2.6, 41, -29.5), (1.6, 4.6, 2.2), COAT_SH, roll=-14 * s_, pitch=-8)   # ears
        tuft(head, (s_ * 2.6, 41.4, -29.8), (0.9, 3.2, 0.4), NOSE, roll=-14 * s_, pitch=-8)
        head.add((s_ * 4.25 - 0.3, 36.6, -34.6), (0.6, 0.5, 3), solid("3a2a48"))            # lashes
    ge = m.bone("glow_eyes", (0, 35.5, -33), "head")
    ge.add((-4.35, 34.6, -34.5), (0.5, 1.8, 2.6), EYE)
    ge.add((3.85, 34.6, -34.5), (0.5, 1.8, 2.6), EYE)
    obox(head, (-4.6, 38.4, -34.2), (9.2, 1.2, 6.6), GOLD, axis="y")                 # circlet
    head.add((-1.1, 38.2, -35), (2.2, 2.4, 1), GOLD, decals={"north": d_pixels(["P"], {"P": "b07cff"}, center=True)})
    for name, mat in (("glow_horn_w", HORN_W), ("glow_horn_r", HORN_R), ("glow_horn_b", HORN_B), ("glow_horn_g", HORN_G)):
        hb = m.bone(name, (0, 39.5, -34), "head", (-30, 0, 0))
        for k in range(8):
            sz = 3.0 - k * 0.32
            hb.add((-sz / 2, 39.5 + k * 2.3, -34 - sz / 2), (sz, 2.6, sz), mat, pivot=(0, 39.5 + k * 2.3, -34),
                   rotation=(0, k * 30, 0))
    # forelock
    tuft(head, (0, 38.6, -36.4), (3.4, 5, 1.4), MANE, pitch=28)
    # flowing mane: a crest along the neck with locks cascading down both sides
    def mane_lock(bone, i, p):
        for s_ in (-1, 1):
            tuft(bone, (s_ * 3.4, p[1] - 3.5, p[2] + 2), (1.4, 8 - i * 0.6, 4.6), MANE2 if (i + (s_ > 0)) % 2 else MANE,
                 roll=-12 * s_, pitch=-10)
    chain(m, "mane_a", "neck", (0, 42.5, -27.5), "+z", [5, 5, 5, 4], [(3.2, 6.5), (3.2, 7), (3, 6.5), (2.8, 5.5)],
          [(-6, 0, 0), (4, 0, 0), (8, 0, 0), (14, 0, 0)], MANE, extra=mane_lock)
    chain(m, "mane_b", "neck", (-3.4, 40, -24), "+z", [5, 5, 5], [(1.6, 8), (1.6, 8), (1.4, 7)],
          [(0, 0, 25), (10, 0, 5), (12, 0, 5)], MANE2)

    # ------------------------------------------------------------------ legs: muscular above, slender below, feathered fetlocks
    for name, x, z, hind in (("leg_fr", -4.4, -11.5, False), ("leg_fl", 4.4, -11.5, False),
                             ("leg_br", -4.4, 11, True), ("leg_bl", 4.4, 11, True)):
        s = -1 if x < 0 else 1
        up = m.bone(name, (x, 25, z), "body")
        if hind:
            ellipsoid(up, (x, 21, z + 0.5), (3.4, 6, 3.8), COAT, layers=3, mirror=s > 0)
        else:
            obox(up, (x - 2.7, 13.5, z - 2.9), (5.4, 12, 5.8), COAT, mirror=s > 0)
        lo = m.bone(name + "1", (x, 13.5, z), name)
        obox(lo, (x - 1.8, 3.2, z - 1.8), (3.6, 10.6, 3.6), COAT_SH, mirror=s > 0)
        obox(lo, (x - 2.3, 11.4, z - 2.3), (4.6, 2.6, 4.6), COAT_SH)                       # knee
        tuft(lo, (x, 4.5, z + 2.2), (4.4, 5, 2.4), MANE, pitch=25)                       # feathering
        obox(lo, (x - 2.4, 0, z - 2.5), (4.8, 3, 5), HOOF)
        obox(lo, (x - 2.6, 2.6, z - 2.7), (5.2, 0.8, 5.4), GOLD)

    # ------------------------------------------------------------------ tail: three flowing strands
    def tail_strands(bone, i, p):
        for s_ in (-1, 1):
            tuft(bone, (p[0] + s_ * 2.6, p[1] - 0.5, p[2] + 2.8), (1.6, 3.4 + i * 0.4, 6.5), MANE2, yaw=10 * s_, roll=-10 * s_)
    chain(m, "tail", "body", (0, 35, 16), "+z", [5, 6, 7, 7, 6],
          [(4, 4), (5.6, 4.6), (6.6, 4.6), (6.6, 4.2), (5.6, 3.6)],
          [(-55, 0, 0), (-18, 0, 0), (-10, 0, 0), (-4, 0, 0), (12, 0, 0)], MANE, extra=tail_strands)

    # ------------------------------------------------------------------ grand wings: coverts, secondaries, primaries
    def wing(side):
        s = -1 if side == "r" else 1
        sh = m.bone(f"wing_{side}", (s * 6, 36, -9), "body")
        x0 = s * 6 + (-13 if s < 0 else 0)
        obox(sh, (x0, 34.6, -10.8), (13, 2.8, 4.2), COAT, axis="x", mirror=s > 0)
        sh.add((x0, 35.6, -11.2), (13, 1.4, 1.4), GOLD, mirror=s > 0)                      # gilded leading edge
        for k in range(4):                                                                  # inner coverts + secondaries
            fx = s * (7.5 + k * 3.2)
            sh.add((fx - 1.7, 35.2, -9), (3.4, 0.5, 8), FEATH_C, pivot=(fx, 35.5, -9), rotation=(0, s * 4, 0), mirror=s > 0)
            sh.add((fx - 1.6, 34.7, -6), (3.2, 0.5, 15 + k), FEATH, pivot=(fx, 35, -6), rotation=(0, s * (2 + k), 0), mirror=s > 0)
        fa = m.bone(f"wing_{side}1", (s * 19, 36, -9), sh.name)
        x1 = s * 19 + (-14 if s < 0 else 0)
        obox(fa, (x1, 34.9, -10.5), (14, 2.3, 3.6), COAT, axis="x", mirror=s > 0)
        fa.add((x1, 35.7, -11), (14, 1.2, 1.2), GOLD, mirror=s > 0)
        for k in range(5):
            fx = s * (20 + k * 2.8)
            fa.add((fx - 1.6, 35.4, -9), (3.2, 0.5, 7.5), FEATH_C, pivot=(fx, 35.6, -9), rotation=(0, s * 6, 0), mirror=s > 0)
            fa.add((fx - 1.6, 34.9, -6.5), (3.2, 0.5, 19 - k * 0.6), FEATH, pivot=(fx, 35.2, -6.5),
                   rotation=(0, s * (6 + k * 2.5), 0), mirror=s > 0)
        hd = m.bone(f"wing_{side}2", (s * 33, 36, -9), fa.name)
        x2 = s * 33 + (-8 if s < 0 else 0)
        obox(hd, (x2, 35.1, -10.3), (8, 1.9, 2.8), COAT_SH, axis="x", mirror=s > 0)
        tuft(hd, (s * 41, 36, -10), (2.2, 1.6, 2.2), GOLD, yaw=45)
        for k in range(9):                                                                  # primaries fanning back
            ang = 4 + k * 10
            ln = 26 - k * 1.2
            hd.add((s * 37 - 1.6, 35.2, -9), (3.2, 0.5, ln), FEATH_P, pivot=(s * 37, 35.5, -9),
                   rotation=(0, s * ang, 0), mirror=s > 0)
        tipb = m.bone(f"glow_tip_{side}", (s * 37, 35.5, -9), hd.name)
        for k in range(9):
            ang = 4 + k * 10
            ln = 26 - k * 1.2
            tipb.add((s * 37 - 1.7, 35.15, -9 + ln - 4), (3.4, 0.6, 4), TIP, pivot=(s * 37, 35.5, -9), rotation=(0, s * ang, 0))
    wing("r")
    wing("l")

    # ------------------------------------------------------------------ phase III star crown
    crown = m.bone("glow_crown", (0, 50, -31), "head")
    import math as _m
    for k in range(9):
        a = _m.radians(k * 40)
        px, pz = _m.cos(a) * 6.5, _m.sin(a) * 6.5 - 31
        crown.add((px - 1, 49, pz - 1), (2, 2, 2), STAR, pivot=(px, 50, pz), rotation=(45, 0, 45))

    c = Creature("alicorn", m, scale=1.6, description="Alicorn, Dawnstar Sovereign")
    c.preview_props = {"legends:fly": 0}
    c.pre = COMMON_PRE + [
        "variable.fly = math.lerp(variable.fly ?? 0.0, query.property('legends:fly') == 1 ? 1.0 : 0.0, 0.08)",
        "variable.hue = query.property('legends:var')",
        "variable.gait = variable.mv * (1.0 - variable.fly) * variable.calm",
    ]
    c.visibility += [("glow_horn_w", "variable.hue == 0"), ("glow_horn_r", "variable.hue == 1"),
                     ("glow_horn_b", "variable.hue == 2"), ("glow_horn_g", "variable.hue >= 3"),
                     ("glow_crown", "variable.ph >= 3"), ("glow_tip_r", "variable.ph >= 3"),
                     ("glow_tip_l", "variable.ph >= 3")]

    t = "q.life_time"
    idle = c.loop("idle", "variable.calm")
    idle.rot("neck", [wave(2.5, 70), wave(3, 40), 0])
    idle.rot("head", ["query.target_x_rotation * 0.4", "query.target_y_rotation * 0.5", 0])
    for i in range(4):
        idle.rot(f"mane_a{i}", [wave(4, 90, -i * 40), wave(6, 70, -i * 30), 0])
    for i in range(3):
        idle.rot(f"mane_b{i}", [wave(4, 90, -i * 40 - 30), wave(6, 70, -i * 30 - 20), 0])
    for i in range(5):
        idle.rot(f"tail{i}", [wave(4, 80, -i * 35), wave(10, 60, -i * 30), 0])
    idle.rot("glow_crown", [0, f"{t} * 60", 0])

    fold = c.loop("fold", "1.0 - variable.fly")
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        fold.rot(f"wing_{side}", [-70, 82 * -s, 0])
        fold.rot(f"wing_{side}1", [0, -12 * -s, 0])
        fold.rot(f"wing_{side}2", [0, 25 * -s, 0])

    fly = c.loop("fly", "variable.fly")
    fl = f"{t} * 220"
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        fly.rot(f"wing_{side}", [0, 0, f"(math.sin({fl}) * 42 + 10) * {-s}"])
        fly.rot(f"wing_{side}1", [0, 0, f"(math.sin({fl} - 45) * 16) * {-s}"])
        fly.rot(f"wing_{side}2", [0, f"(math.sin({fl} - 70) * 8) * {-s}", f"(math.sin({fl} - 80) * 14) * {-s}"])
    fly.pos("body", [0, f"math.sin({fl} + 180) * 1.4", 0])
    for leg, a1, a2 in (("leg_fr", -60, 70), ("leg_fl", -45, 60), ("leg_br", 40, 30), ("leg_bl", 50, 25)):
        fly.rot(leg, [a1, 0, 0])
        fly.rot(leg + "1", [a2, 0, 0])

    gait = c.loop("gait", "variable.gait")
    g = "variable.dist * 34.0"
    for leg, ph in (("leg_fr", 0), ("leg_bl", 0), ("leg_fl", 180), ("leg_br", 180)):
        gait.rot(leg, [f"math.sin({g} + {ph}) * 32", 0, 0])
        gait.rot(leg + "1", [f"math.max(0.0, math.cos({g} + {ph})) * 45", 0, 0])
    gait.pos("body", [0, f"math.abs(math.sin({g})) * 1.2", 0])
    gait.rot("neck", [f"math.sin({g} * 2.0) * 4", 0, 0])

    # ---------------------------------------------------------------- acts
    def P(a, bone, frames, ch="rot"):
        (a.rot if ch == "rot" else a.pos if ch == "pos" else a.scl)(bone, kf(frames))

    a = c.act("descend", 3.0, [2.2])
    P(a, "body", {0: [0, 30, 0], 2.2: [0, 0, 0], 2.5: [0, -2, 0], 3.0: [0, 0, 0]}, "pos")
    P(a, "body", {0: [-20, 0, 0], 2.0: [-15, 0, 0], 2.2: [5, 0, 0], 3.0: [0, 0, 0]})
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        P(a, f"wing_{side}", {0: [0, 0, 30 * -s], 0.8: [0, 0, -10 * -s], 1.6: [0, 0, 35 * -s], 2.2: [0, 0, 20 * -s], 3.0: [0, 0, 0]})
    P(a, "head", {0: [0, 0, 0], 2.4: [-30, 0, 0], 3.0: [0, 0, 0]})

    a = c.act("rear", 2.0, [1.3])
    P(a, "body", {0: [0, 0, 0], 0.6: [-45, 0, 0], 1.1: [-45, 0, 0], 1.3: [5, 0, 0], 2.0: [0, 0, 0]})
    P(a, "body", {0: [0, 0, 0], 0.6: [0, 6, 8], 1.1: [0, 6, 8], 1.3: [0, 0, 0], 2.0: [0, 0, 0]}, "pos")
    for leg in ("leg_fr", "leg_fl"):
        P(a, leg, {0: [0, 0, 0], 0.6: [-70, 0, 0], 0.8: [-30, 0, 0], 1.0: [-80, 0, 0], 1.3: [0, 0, 0], 2.0: [0, 0, 0]})
        P(a, leg + "1", {0: [0, 0, 0], 0.6: [80, 0, 0], 1.0: [80, 0, 0], 1.3: [0, 0, 0]})
    for leg in ("leg_br", "leg_bl"):
        P(a, leg, {0: [0, 0, 0], 0.6: [45, 0, 0], 1.1: [45, 0, 0], 1.3: [0, 0, 0]})
    P(a, "neck", {0: [0, 0, 0], 0.6: [-20, 0, 0], 1.3: [10, 0, 0], 2.0: [0, 0, 0]})

    a = c.act("stomp", 1.4, [0.9])
    P(a, "body", {0: [0, 0, 0], 0.55: [-35, 0, 0], 0.9: [6, 0, 0], 1.4: [0, 0, 0]})
    P(a, "body", {0: [0, 0, 0], 0.55: [0, 4, 6], 0.9: [0, -1, 0], 1.4: [0, 0, 0]}, "pos")
    for leg in ("leg_fr", "leg_fl"):
        P(a, leg, {0: [0, 0, 0], 0.55: [-70, 0, 0], 0.9: [10, 0, 0], 1.4: [0, 0, 0]})
        P(a, leg + "1", {0: [0, 0, 0], 0.55: [70, 0, 0], 0.9: [0, 0, 0]})
    for leg in ("leg_br", "leg_bl"):
        P(a, leg, {0: [0, 0, 0], 0.55: [35, 0, 0], 0.9: [0, 0, 0]})

    a = c.act("charge", 1.0, [], loop=True)
    g2 = "q.anim_time * 1300"
    for leg, ph in (("leg_fr", 0), ("leg_fl", 40), ("leg_br", 180), ("leg_bl", 220)):
        a.rot(leg, [f"math.sin({g2} + {ph}) * 50", 0, 0])
        a.rot(leg + "1", [f"math.max(0.0, math.cos({g2} + {ph})) * 60", 0, 0])
    a.rot("neck", [30, 0, 0])
    a.rot("head", [25, 0, 0])
    a.pos("body", [0, f"math.abs(math.sin({g2})) * 2.5", 0])
    a.rot("body", [f"math.sin({g2}) * 5", 0, 0])

    a = c.act("lance", 1.4, [0.7])
    P(a, "neck", {0: [0, 0, 0], 0.45: [-25, 0, 0], 0.7: [15, 0, 0], 1.4: [0, 0, 0]})
    P(a, "head", {0: [0, 0, 0], 0.45: [-20, 0, 0], 0.7: [20, 0, 0], 1.4: [0, 0, 0]})
    P(a, "body", {0: [0, 0, 0], 0.45: [-8, 0, 0], 0.7: [3, 0, 0], 1.4: [0, 0, 0]})

    a = c.act("wing_gust", 1.4, [0.7])
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        P(a, f"wing_{side}", {0: [0, 0, 0], 0.4: [0, 30 * s, 50 * -s], 0.7: [0, -50 * s, -10 * -s], 1.4: [0, 0, 0]})
    P(a, "body", {0: [0, 0, 0], 0.4: [-15, 0, 0], 0.7: [5, 0, 0], 1.4: [0, 0, 0]})

    a = c.act("takeoff", 1.5, [0.7])
    P(a, "body", {0: [0, 0, 0], 0.5: [0, -3, 0], 0.7: [0, 4, 0], 1.5: [0, 0, 0]}, "pos")
    P(a, "body", {0: [0, 0, 0], 0.5: [-20, 0, 0], 1.5: [0, 0, 0]})
    a = c.act("land", 1.2, [0.5])
    P(a, "body", {0: [0, 4, 0], 0.5: [0, -3, 0], 1.2: [0, 0, 0]}, "pos")
    P(a, "body", {0: [-10, 0, 0], 0.5: [6, 0, 0], 1.2: [0, 0, 0]})

    a = c.act("curtain", 2.4, [1.0])
    P(a, "body", {0: [0, 0, 0], 0.7: [-30, 0, 0], 2.0: [-28, 0, 0], 2.4: [0, 0, 0]})
    P(a, "neck", {0: [0, 0, 0], 0.7: [-25, 0, 0], 2.4: [0, 0, 0]})
    P(a, "head", {0: [0, 0, 0], 1.0: [-30, 0, 0], 2.4: [0, 0, 0]})

    a = c.act("comet", 1.6, [1.1])
    P(a, "body", {0: [0, 0, 0], 0.6: [-25, 0, 0], 1.0: [45, 0, 0], 1.1: [50, 0, 0], 1.6: [0, 0, 0]})
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        P(a, f"wing_{side}", {0: [0, 0, 0], 0.6: [0, 0, 45 * -s], 1.0: [0, 55 * -s, 0], 1.6: [0, 0, 0]})

    a = c.act("barrier", 2.0, [1.0])
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        P(a, f"wing_{side}", {0: [0, 0, 0], 0.8: [-30, -60 * s, 40 * -s], 1.6: [-30, -60 * s, 40 * -s], 2.0: [0, 0, 0]})
        P(a, f"wing_{side}1", {0: [0, 0, 0], 0.8: [0, -50 * s, 0], 1.6: [0, -50 * s, 0], 2.0: [0, 0, 0]})
    P(a, "head", {0: [0, 0, 0], 0.8: [20, 0, 0], 2.0: [0, 0, 0]})

    a = c.act("heal", 4.0, [], loop="hold_on_last_frame")
    P(a, "neck", {0: [0, 0, 0], 0.6: [25, 0, 0], 3.5: [25, 0, 0], 4.0: [0, 0, 0]})
    P(a, "head", {0: [0, 0, 0], 0.6: [20, 0, 0], 3.5: [20, 0, 0], 4.0: [0, 0, 0]})
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        P(a, f"wing_{side}", {0: [0, 0, 0], 0.6: [0, -30 * s, 30 * -s], 3.5: [0, -30 * s, 30 * -s], 4.0: [0, 0, 0]})

    a = c.act("nova", 12.0, [2.0, 9.6])
    P(a, "body", {0: [0, 0, 0], 2.0: [-35, 0, 0], 9.2: [-35, 0, 0], 9.6: [10, 0, 0], 12.0: [0, 0, 0]})
    P(a, "head", {0: [0, 0, 0], 2.0: [-35, 0, 0], 9.2: [-35, 0, 0], 9.6: [10, 0, 0], 12.0: [0, 0, 0]})
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        P(a, f"wing_{side}", {0: [0, 0, 0], 2.0: [-20, 0, 35 * -s], 9.2: [-20, 0, 38 * -s], 9.6: [10, 0, -20 * -s], 12.0: [0, 0, 0]})
        P(a, f"wing_{side}2", {0: [0, 0, 0], 2.0: [0, -20 * s, 0], 9.2: [0, -20 * s, 0], 12.0: [0, 0, 0]})
    P(a, "glow_crown", {0: [1, 1, 1], 2.0: [2.2, 2.2, 2.2], 9.2: [2.6, 2.6, 2.6], 9.8: [1, 1, 1]}, "scl")

    a = c.act("hyper", 1.0, [], loop=True)
    a.rot("body", [10, 0, 0])
    a.rot("neck", [35, 0, 0])
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        a.rot(f"wing_{side}", [0, 45 * -s, 5 * -s])
    for leg, v in (("leg_fr", -70), ("leg_fl", -70), ("leg_br", 60), ("leg_bl", 60)):
        a.rot(leg, [v, 0, 0])

    a = c.act("spiral", 3.0, [0.6])
    P(a, "body", {0: [0, 0, 0], 0.6: [-20, 0, 0], 2.6: [-20, 0, 0], 3.0: [0, 0, 0]})
    a.rot("root", [0, "q.anim_time < 2.8 ? q.anim_time * 300 : 0", 0])

    a = c.act("death", 4.0, [3.4])
    P(a, "body", {0: [0, 0, 0], 1.0: [-30, 0, 0], 2.4: [10, 0, 40], 4.0: [5, 0, 85]})
    P(a, "body", {0: [0, 0, 0], 1.0: [0, 3, 0], 2.4: [0, -4, 0], 4.0: [0, -12, 0]}, "pos")
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        P(a, f"wing_{side}", {0: [0, 0, 0], 1.0: [0, 0, 45 * -s], 4.0: [0, 0, -15 * -s]})
    P(a, "neck", {0: [0, 0, 0], 1.0: [-30, 0, 0], 4.0: [30, 0, 0]})
    return c
