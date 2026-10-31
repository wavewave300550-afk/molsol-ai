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

from .common import COMMON_PRE, Creature, chain, kf, mrot, ring_cubes, scale_subtree, wave
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
    m = Model("geometry.legends.alicorn", seed=404)
    m.bounds = (7.0, 6.0, 2.0)

    COAT = sheen(fur("f7f3ff", "d5cbe8", "ffffff", streak=0.6, var=0.05))
    COAT_SH = sheen(fur("ebe4f7", "c4b8dc", "f8f6ff", streak=0.6, var=0.05))
    MANE = aurora()
    MANE2 = aurora(("c9a2ff", "8fd8ff", "ffd1f0", "fff1b8"), axis=1)
    HOOF = gold("f0c64a", "8a5d10", "fff6c8")
    GOLD = gold("f2cf5b", "8f6413", "fff7cf")
    FEATH = feathers("fbf8ff", "d9c9ff", "e8ddff", row=2, tip_from=0.55)
    FEATH_P = feathers("f6f2ff", "a98bff", "dccfff", row=2, tip_from=0.4)
    FEATH_C = feathers("ffffff", "efe6ff", "f1ebff", row=2, tip_from=0.7, ragged=False)
    NOSE = solid("e8d9ee", 0.04)
    EYE = glowball("ffffff", "a46bff")
    HORN_W = crystal("e8f4ff", "ffffff", "a9c6f0", facet=2)
    HORN_R = crystal("ff7a7a", "ffe0e0", "c02a3a", facet=2)
    HORN_B = crystal("7ac8ff", "e0f6ff", "2a6ac0", facet=2)
    HORN_G = crystal("ffd36a", "fff6d0", "c0861a", facet=2)
    STAR = glowball("ffffff", "ffd86a")
    TIP = glowball("ffffff", "c7a6ff")

    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 30, 0), "root")
    body.add((-7, 22, -15), (14, 14, 30), COAT, inflate=0.3, face_mats={"down": COAT_SH})
    body.add((-7.5, 24, -17), (15, 13, 6), COAT)                                        # chest
    body.add((-6.5, 23, 12), (13, 12, 5), COAT_SH)                                      # rump
    body.add((-7.6, 30.5, -6), (15.2, 1.2, 2.5), GOLD)                                  # thin golden girth
    body.loc("horn_root", (0, 46, -26))

    # ------------------------------------------------------------------ neck, head, horn
    neck = m.bone("neck", (0, 34, -13), "body", (-38, 0, 0))
    neck.add((-4.5, 30, -27), (9, 11, 16), COAT, inflate=0.2)
    neck.add((-3.5, 28.5, -25), (7, 3, 12), COAT_SH)
    head = m.bone("head", (0, 36, -26), "neck", (38, 0, 0))
    head.loc("horn", (0, 46, -34))
    head.add((-3.6, 32, -33), (7.2, 7, 8), COAT)                                         # skull
    head.add((-3.0, 30, -43), (6, 6, 11), COAT)                                          # long face
    head.add((-3.2, 29, -38), (6.4, 3, 6), COAT_SH)                                      # jaw line
    head.add((-3.0, 29.2, -42.5), (6, 2.6, 4.5), NOSE,
             decals={"north": d_pixels(["K....K"], {"K": "6b5a7a"}, center=True)})
    for s in (-1, 1):
        head.add((s * 3.4 - 0.6, 38.5, -29), (1.2, 3.2, 2), COAT_SH, pivot=(s * 3.4, 38.5, -28), rotation=(-10, 0, 12 * s))
    ge = m.bone("glow_eyes", (0, 35.5, -32), "head")
    ge.add((-3.75, 34.6, -32.5), (0.4, 1.4, 2), EYE)
    ge.add((3.35, 34.6, -32.5), (0.4, 1.4, 2), EYE)
    head.add((-2, 38.6, -33.6), (4, 1, 4), GOLD)                                         # circlet
    # spiral horn, one glow bone per colour (visibility picks the colour)
    for name, mat in (("glow_horn_w", HORN_W), ("glow_horn_r", HORN_R), ("glow_horn_b", HORN_B), ("glow_horn_g", HORN_G)):
        hb = m.bone(name, (0, 39, -34), "head", (-28, 0, 0))
        for k in range(6):
            sz = 2.6 - k * 0.38
            hb.add((-sz / 2, 39 + k * 2.2, -34 - sz / 2), (sz, 2.4, sz), mat, pivot=(0, 39 + k * 2.2, -34),
                   rotation=(0, k * 28, 0))
    # flowing mane: two ribbons down the neck + forelock
    mane_l = [5, 5, 5, 4]
    chain(m, "mane_a", "neck", (0, 42.5, -27), "+z", mane_l, [(3, 6), (3, 6.5), (3, 6), (2.6, 5)],
          [(-6, 0, 0), (4, 0, 0), (8, 0, 0), (14, 0, 0)], MANE)
    chain(m, "mane_b", "neck", (-3.2, 40, -24), "+z", [5, 5, 5], [(1.6, 7), (1.6, 7), (1.4, 6)],
          [(0, 0, 25), (10, 0, 5), (12, 0, 5)], MANE2)
    head.add((-1.5, 37, -35.5), (3, 4, 2), MANE, pivot=(0, 39, -34), rotation=(30, 0, 0))

    # ------------------------------------------------------------------ legs
    for name, x, z in (("leg_fr", -4, -11), ("leg_fl", 4, -11), ("leg_br", -4, 10), ("leg_bl", 4, 10)):
        s = -1 if x < 0 else 1
        up = m.bone(name, (x, 24, z), "body")
        up.add((x - 2.4, 13, z - 2.6), (4.8, 12, 5.2), COAT, mirror=s > 0)
        lo = m.bone(name + "1", (x, 13, z), name)
        lo.add((x - 1.8, 3, z - 1.8), (3.6, 10.5, 3.6), COAT_SH, mirror=s > 0)
        lo.add((x - 2.2, 3, z - 2.2), (4.4, 2.4, 4.4), solid("f4eefc", 0.03))            # feathered fetlock
        lo.add((x - 2.1, 0, z - 2.1), (4.2, 3, 4.2), HOOF)

    # ------------------------------------------------------------------ tail
    tails = chain(m, "tail", "body", (0, 34, 16), "+z", [5, 6, 7, 7, 6],
                  [(4, 4), (5.5, 4.5), (6.5, 4.5), (6.5, 4), (5.5, 3.5)],
                  [(-55, 0, 0), (-18, 0, 0), (-10, 0, 0), (-4, 0, 0), (12, 0, 0)], MANE)

    # ------------------------------------------------------------------ wings
    def wing(side):
        s = -1 if side == "r" else 1
        sh = m.bone(f"wing_{side}", (s * 6, 35, -9), "body")
        sh.add((s * 6 + (-11 if s < 0 else 0), 33.8, -10.5), (11, 2.4, 4), COAT, mirror=s > 0)
        sh.add((s * 6 + (-11 if s < 0 else 0), 34.4, -8), (11, 0.6, 8), FEATH_C, density=1, share="awc0", mirror=s > 0)
        fa = m.bone(f"wing_{side}1", (s * 17, 35, -9), sh.name)
        fa.add((s * 17 + (-12 if s < 0 else 0), 34, -10.2), (12, 2, 3.4), COAT, mirror=s > 0)
        fa.add((s * 17 + (-12 if s < 0 else 0), 34.6, -8), (12, 0.6, 7), FEATH_C, share="awc1", mirror=s > 0)
        # secondaries: a fan of long feathers along the forearm
        for k in range(5):
            x0 = s * 8 + s * k * 4.2
            fa_ = sh if k < 2 else fa
            fa_.add((x0 - 1.6, 34.2, -6), (3.2, 0.5, 14 - abs(k - 2) * 0.8), FEATH, pivot=(x0, 34.5, -6),
                    rotation=(0, s * (2 + k * 2), 0), share=f"aws{k}", mirror=s > 0)
        hd = m.bone(f"wing_{side}2", (s * 29, 35, -9), fa.name)
        hd.add((s * 29 + (-7 if s < 0 else 0), 34.2, -10), (7, 1.6, 2.8), COAT_SH, mirror=s > 0)
        # primaries: long feathers fanning backwards from the hand
        for k in range(6):
            ang = 8 + k * 13
            ln = 20 - k * 1.3
            hd.add((s * 33 - 1.4, 34.3, -9), (2.8, 0.5, ln), FEATH_P, pivot=(s * 33, 34.5, -9),
                   rotation=(0, s * ang, 0),
                   share=f"awp{k}", mirror=s > 0)
        tipb = m.bone(f"glow_tip_{side}", (s * 33, 34.5, -9), hd.name)
        for k in range(6):
            ang = 8 + k * 13
            ln = 20 - k * 1.3
            tipb.add((s * 33 - 1.5, 34.25, -9 + ln - 3.5), (3, 0.6, 3.5), TIP, pivot=(s * 33, 34.5, -9),
                     rotation=(0, s * ang, 0))
    wing("r")
    wing("l")

    # ------------------------------------------------------------------ phase III star crown
    crown = m.bone("glow_crown", (0, 48, -30), "head")
    import math as _m
    for k in range(7):
        a = _m.radians(k * 360 / 7)
        px, pz = _m.cos(a) * 5.5, _m.sin(a) * 5.5 - 30
        crown.add((px - 0.9, 47, pz - 0.9), (1.8, 1.8, 1.8), STAR, pivot=(px, 47.9, pz), rotation=(45, 0, 45))

    c = Creature("alicorn", m, scale=1.3, description="Alicorn, Dawnstar Sovereign")
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
