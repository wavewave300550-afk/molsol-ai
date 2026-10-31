"""
TEN-TAILED FOX (十尾の天狐) — "Tenko of the Tenfold Moon".

A celestial fox beyond the nine-tailed kitsune: ivory-gold fur with crimson
kumadori markings, a sacred shimenawa rope with shide paper at its throat, and
TEN great tails fanned like a peacock's train, each tipped with blue foxfire.
Nine are golden; the tenth, at the centre, is sealed with rope until phase
III, when it unfurls as the silver "moon tail" and the tails form a radiant
wheel for the eclipse.
"""
from __future__ import annotations

import math

from .common import COMMON_PRE, Creature, chain, kf, mrot, scale_subtree, wave
from mk.geo import Model
from mk.paint import (C, bake, cloth, d_pixels, fbm, fur, glowball, gold, h2, hx, mix, shade, solid)

TAILS = 10


def marked_fur(base, dark, light, mark="c8102e", stripes=None):
    fb = fur(base, dark, light, streak=0.9, var=0.06)
    mk = hx(mark)

    def p(f):
        col = fb(f)
        if stripes and stripes(f):
            return bake(mk, f, edge=-0.04)
        return col
    return p


def moon_fur():
    """Tenth tail: silver fur that turns star-flecked midnight in phase III."""
    sil = fur("e8ecf6", "aab3c8", "ffffff", streak=0.9, var=0.05)
    night = fur("232a52", "11152e", "3d4a8a", streak=0.9, var=0.06)
    star = hx("fff6c8")

    def p(f):
        if f.variant >= 1:
            if h2(f.x * 3 + int(f.p[2]), f.y, f.cube_index) > 0.94:
                return star
            return night(f)
        return sil(f)
    return p


def build() -> Creature:
    m = Model("geometry.legends.tenko", seed=505)
    m.bounds = (8.0, 7.0, 2.4)

    FUR = marked_fur("f6dfa6", "d4a65a", "fff3d2")
    FUR_LEG = marked_fur("f6dfa6", "d4a65a", "fff3d2", stripes=lambda f: f.side and int(f.p[1]) % 6 == 0)
    WHITE = fur("fffaf0", "e6dccb", "ffffff", streak=1.2, var=0.04)
    TAILF = fur("f8e3ad", "d9a24f", "fff5d8", streak=1.0, var=0.07)
    TAIL_WHITE = fur("fffaf0", "e9dfcf", "ffffff", streak=1.0, var=0.05)
    MOON = moon_fur()
    RED = solid("c8102e", 0.06)
    BLACK = solid("1b1414", 0.05)
    NOSE = solid("2a1a1a", 0.04)
    ROPE = cloth("e9d6a8", None, fold=0.12)
    PAPER = solid("fbfbf6", 0.02)
    GOLD = gold("f2c14e", "8c5a12", "fff2c0")
    EYE = glowball("fffbe0", "ffb11f")
    FOXFIRE = glowball("e8fbff", "38a8ff")
    JEWEL = glowball("ffffff", "8fd6ff")

    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 26, 0), "root")
    body.add((-6, 19, -14), (12, 12, 28), FUR, inflate=0.3, face_mats={"down": WHITE})
    body.add((-6.5, 18, -16), (13, 13, 7), WHITE, inflate=0.3)                     # chest ruff
    body.add((-5, 17, -17.5), (10, 8, 3), WHITE)
    # shimenawa rope collar + shide paper
    body.add((-7, 27, -16.6), (14, 2.4, 9), ROPE)
    for s in (-1, 1):
        body.add((s * 3 - 1, 22, -17.4), (2, 5, 0.4), PAPER, decals={"north": d_pixels(["#.", ".#", "#.", ".#", "#."], {"#": "d8d8d0"})})
    body.add((-1, 21.5, -17.6), (2, 5.5, 0.4), PAPER)
    body.add((-2.5, 25.5, -17.8), (5, 3, 1), GOLD)                                  # bell-knot

    # ------------------------------------------------------------------ head
    neck = m.bone("neck", (0, 29, -14), "body", (-25, 0, 0))
    neck.add((-4.5, 26, -20), (9, 9, 9), FUR)
    head = m.bone("head", (0, 33, -19), "neck", (25, 0, 0))
    head.loc("mouth", (0, 30, -32))
    head.add((-4.5, 29, -25), (9, 8, 8), FUR, inflate=0.2)
    head.add((-2.6, 28.5, -32), (5.2, 4, 7.5), FUR)                                  # snout
    head.add((-2.4, 28, -31.5), (4.8, 1.4, 7), WHITE)                                # jaw
    head.add((-1, 31.6, -32.3), (2, 1.2, 1), NOSE)
    for s in (-1, 1):
        head.add((s * 5 - 1.5, 28.5, -24), (3, 4.5, 4), WHITE, pivot=(s * 5, 31, -22), rotation=(0, 0, -25 * s))  # cheek fluff
        # tall ears (3 tiers) with crimson insides
        e = m.bone("ear_r" if s < 0 else "ear_l", (s * 3, 37, -21), "head", (0, 0, -12 * s))
        e.add((s * 3 - 2, 36.5, -22), (4, 3, 2), FUR)
        e.add((s * 3 - 1.5, 39.5, -22), (3, 3, 1.8), FUR)
        e.add((s * 3 - 0.9, 42.5, -21.8), (1.8, 2.5, 1.4), BLACK)
        e.add((s * 3 - 1.2, 37, -22.3), (2.4, 4.5, 0.4), RED)
    # kumadori markings: brows, eye lines, muzzle stripes
    face = d_pixels(["RR....RR", ".RR..RR.", "........", "........"], {"R": "c8102e"}, center=True)
    head.add((-4.6, 33.5, -25.4), (9.2, 3.5, 0.4), FUR, decals={"north": face})
    for s in (-1, 1):
        head.add((s * 2.8 - 0.5, 30.5, -30), (1, 0.6, 4), RED)
    ge = m.bone("glow_eyes", (0, 33, -25.5), "head")
    for s in (-1, 1):
        ge.add((s * 2.4 - 0.9, 32.6, -25.6), (1.8, 1.0, 0.4), EYE)
    gj = m.bone("glow_jewel", (0, 39.5, -24), "head")                                    # hoshi-no-tama
    gj.add((-1.2, 38.5, -25.2), (2.4, 2.4, 2.4), JEWEL, pivot=(0, 39.7, -24), rotation=(45, 0, 45))

    # ------------------------------------------------------------------ legs
    for name, x, z in (("leg_fr", -3.6, -11), ("leg_fl", 3.6, -11), ("leg_br", -3.6, 10), ("leg_bl", 3.6, 10)):
        s = -1 if x < 0 else 1
        up = m.bone(name, (x, 21, z), "body")
        up.add((x - 2.2, 11, z - 2.4), (4.4, 10.5, 4.8), FUR, mirror=s > 0)
        lo = m.bone(name + "1", (x, 11.5, z), name)
        lo.add((x - 1.6, 2, z - 1.6), (3.2, 10, 3.2), FUR_LEG, mirror=s > 0)
        lo.add((x - 2, 0, z - 3), (4, 2.4, 5), WHITE)
        lo.add((x - 1.7, 6, z - 1.9), (3.4, 1, 3.8), RED)

    # ------------------------------------------------------------------ ten tails
    tails = []
    for i in range(TAILS):
        if i == TAILS - 1:
            ry, rx = 0.0, 52.0                                 # the tenth tail stands tall at the centre
        else:
            k = i - 4
            ry = k * 24.0
            rx = 40 - abs(k) * 5
        base = (0, 28, 13)
        mat = MOON if i == TAILS - 1 else [TAILF, TAILF, TAILF, TAIL_WHITE]
        names = chain(m, f"tail{i}_", "body", base, "+z", [6, 7, 7, 6],
                      [(3.6, 3.6), (6.2, 6.2), (7, 7), (5.2, 5.2)],
                      [(rx, ry, 0), (14, 0, 0), (16, 0, 0), (18, 0, 0)], mat, share="tail" if i < TAILS - 1 else None)
        tails.append(names)
        tip = m.get(names[-1])
        x, y, z = tip.pivot
        g = m.bone(f"glow_fire{i}", tip.pivot, names[-1])
        g.add((x - 2, y - 2, z + 5.4), (4, 4, 3.5), FOXFIRE)
        g.add((x - 1.1, y - 1.1, z + 8.6), (2.2, 2.2, 2.2), FOXFIRE)
    scale_subtree(m, "neck", 1.3)
    # rope seal on the tenth tail (removed in phase III)
    seal = m.bone("tail_seal", m.get(tails[-1][1]).pivot, tails[-1][1])
    sx, sy, sz = seal.pivot
    seal.add((sx - 3.6, sy - 3.6, sz + 2), (7.2, 7.2, 2.2), ROPE)
    seal.add((sx - 0.6, sy - 6, sz + 2.4), (1.2, 3, 0.4), PAPER)

    c = Creature("tenko", m, scale=1.35, variants=2, variant_expr="variable.ph >= 3 ? 1 : 0",
                 description="Tenko, the Ten-Tailed Fox")
    c.pre = COMMON_PRE + [
        "variable.flare = math.lerp(variable.flare ?? 0.0, variable.act == 0 ? 0.0 : 1.0, 0.08)",
        "variable.runw = variable.mv * variable.calm",
    ]
    c.visibility += [("tail_seal", "variable.ph < 3"), (f"glow_fire{TAILS - 1}", "variable.ph >= 3")]

    t = "q.life_time"
    idle = c.loop("idle")
    idle.pos("body", [0, wave(0.3, 90), 0])
    idle.rot("neck", [wave(2, 70), wave(3, 45), 0])
    idle.rot("head", ["query.target_x_rotation * 0.5", "query.target_y_rotation * 0.6", wave(3, 35)])
    idle.rot("ear_r", [0, 0, wave(4, 50)])
    idle.rot("ear_l", [0, 0, wave(-4, 50, 60)])
    idle.pos("glow_jewel", [0, wave(0.6, 120), 0])
    idle.rot("glow_jewel", [0, f"{t} * 90", 0])
    for i, names in enumerate(tails):
        ph = i * 37
        spd = 70 + (i % 3) * 12
        for j, nb in enumerate(names):
            amp_y = 5 + j * 3
            amp_x = 3 + j * 2.5
            spread = f" + variable.flare * {(i - 4) * 4 if i < TAILS - 1 else 0} * {1 if j == 0 else 0}"
            idle.rot(nb, [wave(amp_x, spd, -ph - j * 40), f"{wave(amp_y, spd * 0.8, -ph - j * 45)}{spread}", 0])

    run = c.loop("run", "variable.runw")
    g = "variable.dist * 30.0"
    for leg, ph in (("leg_fr", 0), ("leg_fl", 30), ("leg_br", 180), ("leg_bl", 210)):
        run.rot(leg, [f"math.sin({g} + {ph}) * 40", 0, 0])
        run.rot(leg + "1", [f"math.max(0.0, math.cos({g} + {ph})) * 50", 0, 0])
    run.pos("body", [0, f"math.abs(math.sin({g})) * 1.5", 0])
    run.rot("body", [f"math.sin({g}) * 4", 0, 0])

    def P(a, bone, frames, ch="rot"):
        (a.rot if ch == "rot" else a.pos if ch == "pos" else a.scl)(bone, kf(frames))

    def tails_to(a, frames_fn):
        for i, names in enumerate(tails):
            P(a, names[0], frames_fn(i))

    a = c.act("manifest", 3.0, [2.0])
    P(a, "root", {0: [0.05, 0.05, 0.05], 1.2: [0.6, 0.6, 0.6], 2.0: [1.05, 1.05, 1.05], 2.4: [1, 1, 1]}, "scl")
    P(a, "root", {0: [0, 0, 0], 2.0: [0, 720, 0]})
    tails_to(a, lambda i: {0: [-40, 0, 0], 2.0: [-30, 0, 0], 2.6: [10, 0, 0], 3.0: [0, 0, 0]})

    a = c.act("howl", 2.2, [0.8])
    P(a, "body", {0: [0, 0, 0], 0.5: [-25, 0, 0], 1.8: [-25, 0, 0], 2.2: [0, 0, 0]})
    P(a, "body", {0: [0, 0, 0], 0.5: [0, -2, 4], 1.8: [0, -2, 4], 2.2: [0, 0, 0]}, "pos")
    P(a, "neck", {0: [0, 0, 0], 0.6: [-35, 0, 0], 1.8: [-35, 0, 0], 2.2: [0, 0, 0]})
    P(a, "head", {0: [0, 0, 0], 0.6: [-25, 0, 0], 1.8: [-25, 0, 0], 2.2: [0, 0, 0]})
    for leg in ("leg_br", "leg_bl"):
        P(a, leg, {0: [0, 0, 0], 0.5: [-60, 0, 0], 1.8: [-60, 0, 0], 2.2: [0, 0, 0]})
        P(a, leg + "1", {0: [0, 0, 0], 0.5: [70, 0, 0], 1.8: [70, 0, 0], 2.2: [0, 0, 0]})
    tails_to(a, lambda i: {0: [0, 0, 0], 0.6: [-15, (i - 4) * 5 if i < 9 else 0, 0], 1.8: [-15, (i - 4) * 5 if i < 9 else 0, 0], 2.2: [0, 0, 0]})

    a = c.act("pounce", 1.2, [0.45])
    P(a, "body", {0: [0, 0, 0], 0.3: [0, -4, 3], 0.45: [0, 4, -3], 0.9: [0, 0, 0]}, "pos")
    P(a, "body", {0: [0, 0, 0], 0.3: [10, 0, 0], 0.45: [-20, 0, 0], 0.9: [10, 0, 0], 1.2: [0, 0, 0]})
    for leg in ("leg_fr", "leg_fl"):
        P(a, leg, {0: [0, 0, 0], 0.3: [30, 0, 0], 0.45: [-80, 0, 0], 0.9: [0, 0, 0]})
    for leg in ("leg_br", "leg_bl"):
        P(a, leg, {0: [0, 0, 0], 0.3: [-30, 0, 0], 0.45: [50, 0, 0], 0.9: [0, 0, 0]})

    a = c.act("swipe", 1.0, [0.45])
    P(a, "leg_fr", {0: [0, 0, 0], 0.3: [-90, 0, -30], 0.45: [10, 0, 20], 1.0: [0, 0, 0]})
    P(a, "body", {0: [0, 0, 0], 0.3: [-10, 10, 0], 0.45: [5, -10, 0], 1.0: [0, 0, 0]})

    a = c.act("tail_lash", 1.6, [0.8])
    P(a, "root", {0: [0, 0, 0], 0.35: [0, 30, 0], 1.1: [0, -330, 0], 1.6: [0, -360, 0]})
    tails_to(a, lambda i: {0: [0, 0, 0], 0.35: [-30, 0, 0], 0.8: [-40, (i - 4) * 4 if i < 9 else 0, 0], 1.6: [0, 0, 0]})

    a = c.act("foxfire", 1.6, [0.7])
    tails_to(a, lambda i: {0: [0, 0, 0], 0.5: [25, (i - 4) * 6 if i < 9 else 0, 0], 0.7: [-10, (i - 4) * 4 if i < 9 else 0, 0], 1.6: [0, 0, 0]})
    P(a, "head", {0: [0, 0, 0], 0.5: [-15, 0, 0], 0.7: [10, 0, 0], 1.6: [0, 0, 0]})

    a = c.act("lanterns", 2.0, [1.0])
    P(a, "body", {0: [0, 0, 0], 0.6: [-20, 0, 0], 1.6: [-20, 0, 0], 2.0: [0, 0, 0]})
    for leg in ("leg_br", "leg_bl"):
        P(a, leg, {0: [0, 0, 0], 0.6: [-55, 0, 0], 1.6: [-55, 0, 0], 2.0: [0, 0, 0]})
    tails_to(a, lambda i: {0: [0, 0, 0], 0.6: [30, (i - 4) * 8 if i < 9 else 0, 0], 1.6: [30, (i - 4) * 8 if i < 9 else 0, 0], 2.0: [0, 0, 0]})

    a = c.act("illusion", 2.0, [1.2])
    P(a, "root", {0: [0, 0, 0], 1.2: [0, 540, 0], 2.0: [0, 720, 0]})
    P(a, "root", {0: [1, 1, 1], 1.0: [0.7, 1.2, 0.7], 1.2: [1.2, 0.8, 1.2], 1.5: [1, 1, 1]}, "scl")

    a = c.act("torii", 2.2, [1.2])
    P(a, "body", {0: [0, 0, 0], 0.8: [-35, 0, 0], 1.2: [5, 0, 0], 2.2: [0, 0, 0]})
    P(a, "body", {0: [0, 0, 0], 0.8: [0, 4, 6], 1.2: [0, -1, 0], 2.2: [0, 0, 0]}, "pos")
    for leg in ("leg_fr", "leg_fl"):
        P(a, leg, {0: [0, 0, 0], 0.8: [-80, 0, 0], 1.2: [15, 0, 0], 2.2: [0, 0, 0]})

    a = c.act("tail_spikes", 2.4, [1.0])
    tails_to(a, lambda i: {0: [0, 0, 0], 0.6: [30, 0, 0], 1.0: [-95, (i - 4) * 10 if i < 9 else 0, 0], 2.0: [-90, (i - 4) * 10 if i < 9 else 0, 0], 2.4: [0, 0, 0]})
    P(a, "body", {0: [0, 0, 0], 1.0: [8, 0, 0], 2.0: [8, 0, 0], 2.4: [0, 0, 0]})

    a = c.act("kagura", 4.0, [0.6, 1.4, 2.2, 3.0])
    P(a, "root", {0: [0, 0, 0], 0.6: [0, 90, 0], 1.4: [0, 180, 0], 2.2: [0, 270, 0], 3.0: [0, 360, 0], 4.0: [0, 360, 0]})
    P(a, "body", {0: [0, 0, 0], 0.4: [-30, 0, 0], 0.6: [5, 0, 0], 1.2: [-30, 0, 0], 1.4: [5, 0, 0], 2.0: [-30, 0, 0],
                  2.2: [5, 0, 0], 2.8: [-30, 0, 0], 3.0: [5, 0, 0], 4.0: [0, 0, 0]})
    tails_to(a, lambda i: {0: [0, 0, 0], 0.6: [20, 0, 0], 1.4: [-10, 0, 0], 2.2: [20, 0, 0], 3.0: [-10, 0, 0], 4.0: [0, 0, 0]})

    # eclipse: tails become a radiant wheel behind the fox
    a = c.act("eclipse", 11.0, [2.0, 9.6])
    P(a, "body", {0: [0, 0, 0], 2.0: [0, 14, 0], 9.6: [0, 14, 0], 11.0: [0, 0, 0]}, "pos")
    P(a, "body", {0: [0, 0, 0], 2.0: [-12, 0, 0], 9.6: [-12, 0, 0], 11.0: [0, 0, 0]})
    for i, names in enumerate(tails):
        if i == TAILS - 1:
            ry0, rx0 = 0.0, 52.0
        else:
            ry0, rx0 = (i - 4) * 24.0, 40 - abs(i - 4) * 5
        theta = -90 + i * 36
        target = [90 - rx0, -ry0, theta]
        P(a, names[0], {0: [0, 0, 0], 2.0: target, 9.4: target, 11.0: [0, 0, 0]})
        for nb in names[1:]:
            P(a, nb, {0: [0, 0, 0], 2.0: [-8, 0, 0], 9.4: [-8, 0, 0], 11.0: [0, 0, 0]})

    a = c.act("unseal", 4.0, [2.5])
    P(a, tails[-1][0], {0: [0, 0, 0], 1.0: [-40, 0, 0], 2.5: [15, 0, 0], 4.0: [0, 0, 0]})
    P(a, "neck", {0: [0, 0, 0], 1.5: [-35, 0, 0], 3.6: [-35, 0, 0], 4.0: [0, 0, 0]})
    P(a, "head", {0: [0, 0, 0], 1.5: [-25, 0, 0], 3.6: [-25, 0, 0], 4.0: [0, 0, 0]})
    P(a, "body", {0: [0, 0, 0], 1.5: [-20, 0, 0], 3.6: [-20, 0, 0], 4.0: [0, 0, 0]})

    a = c.act("dash", 1.0, [], loop=True)
    g2 = "q.anim_time * 1500"
    for leg, ph in (("leg_fr", 0), ("leg_fl", 30), ("leg_br", 180), ("leg_bl", 210)):
        a.rot(leg, [f"math.sin({g2} + {ph}) * 55", 0, 0])
    a.rot("body", [f"math.sin({g2}) * 5", 0, 0])
    tails_to(a, lambda i: {0: [-25, 0, 0]})

    a = c.act("death", 4.0, [3.4])
    P(a, "body", {0: [0, 0, 0], 1.0: [-20, 0, 0], 2.5: [10, 0, 40], 4.0: [5, 0, 85]})
    P(a, "body", {0: [0, 0, 0], 2.5: [0, -3, 0], 4.0: [0, -10, 0]}, "pos")
    tails_to(a, lambda i: {0: [0, 0, 0], 1.0: [20, 0, 0], 4.0: [-40, 0, 0]})
    return c
