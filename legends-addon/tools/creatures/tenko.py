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

from .common import COMMON_PRE, Creature, chain, ellipsoid, kf, mrot, obox, scale_subtree, tuft, wave
from mk.geo import Model
from mk.paint import (C, bake, cloth, d_pixels, fbm, fur, glowball, gold, h2, hx, mix, plush, shade, solid)

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
    m = Model("geometry.legends.tenko", seed=505, density=2.0)
    m.bounds = (9.0, 8.0, 2.6)

    FUR = plush("f6dca0", "d6a556", "fff3d0")
    FUR_LEG = plush("f6dca0", "d6a556", "fff3d0")
    WHITE = plush("fffaf0", "e6dac6", "ffffff", var=0.04)
    TAILF = plush("f8e2a8", "d8a04c", "fff4d4")
    TAIL_WHITE = plush("fffaf0", "e9dfcd", "ffffff", var=0.04)
    MOON = moon_fur()
    RED = solid("c8102e", 0.06)
    BLACK = solid("1b1414", 0.05)
    NOSE = solid("2a1a1a", 0.04)
    ROPE = cloth("eedcac", None, fold=0.14)
    PAPER = solid("fbfbf6", 0.02)
    GOLD = gold("f5c851", "8c5a12", "fff4c8", sparkle=0.07)
    EYE = glowball("fffbe0", "ffb11f")
    MARK = glowball("ffd0a0", "ff2a3a")
    FOXFIRE = glowball("e8fbff", "38a8ff")
    JEWEL = glowball("ffffff", "8fd6ff")
    shide = d_pixels(["##..", ".##.", "..##", ".##.", "##..", ".##.", "..##"], {"#": "e9e9df"}, center=True)

    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 26, 0), "root")
    ellipsoid(body, (0, 25, 0), (6.4, 6.6, 14.5), FUR, layers=5, axis="z")
    ellipsoid(body, (0, 23.5, -12.5), (6.8, 7.5, 5), WHITE, layers=3)                   # chest
    ellipsoid(body, (0, 24.5, -15.5), (6.2, 6.4, 3.6), WHITE, layers=3)                 # soft chest ruff
    ellipsoid(body, (0, 20.5, -14.8), (4.4, 3.4, 3.2), WHITE, layers=2)
    for z in (-6, 0, 6, 11):                                                              # back fur crest
        tuft(body, (0, 31.4, z), (2.4, 2.4, 5), FUR, pitch=30)
    # shimenawa rope (twisted), shide papers and a golden bell
    for k in range(9):
        a = -80 + k * 20
        tuft(body, (math.sin(math.radians(a)) * 7.4, 28.5 - abs(math.sin(math.radians(a))) * 1.5, -15.5 + abs(math.sin(math.radians(a))) * 4.8),
             (3.2, 2.6, 2.6), ROPE, yaw=a, roll=25 * (1 if k % 2 else -1))
    for x in (-4, 0, 4):
        body.add((x - 1.1, 19.5, -18.3), (2.2, 7, 0.4), PAPER, decals={"north": shide})
    obox(body, (-2, 24.5, -19.4), (4, 4, 3), GOLD, axis="z")
    gm = m.bone("glow_marks", (0, 26, 0), "body")
    for s_ in (-1, 1):                                                                    # kumadori flank markings
        for k, (z, y, ln) in enumerate(((-6, 27, 8), (2, 25.5, 7), (9, 27, 5))):
            gm.add((s_ * 6.55 - 0.15, y, z), (0.3, 0.8, ln), MARK, pivot=(s_ * 6.5, y, z), rotation=(18 - k * 12, 0, 0))

    # ------------------------------------------------------------------ head
    neck = m.bone("neck", (0, 29, -14), "body", (-25, 0, 0))
    obox(neck, (-4.6, 25.5, -21), (9.2, 9.5, 10), FUR, axis="z")
    ellipsoid(neck, (0, 28.5, -17.5), (5.8, 5.6, 5), WHITE, layers=3)                   # mane collar
    head = m.bone("head", (0, 33, -19), "neck", (25, 0, 0))
    head.loc("mouth", (0, 30, -34))
    ellipsoid(head, (0, 33, -22), (4.8, 4.4, 4.8), FUR, layers=3)
    obox(head, (-3, 29.3, -32), (6, 4.8, 8.5), FUR, axis="z")                           # snout
    obox(head, (-1.9, 29, -36), (3.8, 3.4, 5), FUR, axis="z")                           # muzzle tip
    obox(head, (-2.8, 28.2, -35), (5.6, 1.6, 10), WHITE, axis="z")                       # jaw
    head.add((-1.1, 31.6, -36.6), (2.2, 1.6, 1.2), NOSE)
    for s_ in (-1, 1):
        for k in range(3):                                                                 # sweeping cheek fluff
            tuft(head, (s_ * (5 + k * 0.6), 30.5 - k * 0.9, -21 + k * 1.2), (1.6, 3, 6), WHITE, yaw=-40 * s_, roll=-25 * s_ - k * 10 * s_)
        e = m.bone("ear_r" if s_ < 0 else "ear_l", (s_ * 3, 37, -21), "head", (0, 0, -12 * s_))
        for k, (w, h, d) in enumerate(((4.4, 3.2, 2.4), (3.4, 3.2, 2.2), (2.4, 3, 1.8), (1.4, 2.4, 1.2))):
            e.add((s_ * 3 - w / 2, 36.5 + k * 3, -22.5 + k * 0.2), (w, h, d), FUR if k < 3 else BLACK)
        e.add((s_ * 3 - 1.5, 37, -22.8), (3, 8, 0.4), RED)
        e.add((s_ * 3 - 0.9, 39, -23), (1.8, 4, 0.4), WHITE)
    ge = m.bone("glow_eyes", (0, 33, -26), "head")
    for s_ in (-1, 1):
        ge.add((s_ * 2.5 - 1.0, 32.8, -26.9), (2.0, 1.0, 0.4), EYE)
        ge.add((s_ * 2.5 - 1.4, 34.2, -26.6), (2.8, 0.6, 0.4), MARK, pivot=(s_ * 2.5, 34.5, -26.4), rotation=(0, 0, 18 * s_))
        ge.add((s_ * 2.1 - 0.3, 30.4, -33.2), (0.6, 0.5, 5), MARK)
    ge.add((-0.6, 35.5, -26.8), (1.2, 2.6, 0.4), MARK)
    gj = m.bone("glow_jewel", (0, 41, -24), "head")                                      # hoshi-no-tama
    gj.add((-1.6, 39.4, -25.6), (3.2, 3.2, 3.2), JEWEL, pivot=(0, 41, -24), rotation=(45, 0, 45))
    go = m.bone("glow_orbs", (0, 34, 0), "body")                                          # orbiting foxfire
    for k in range(3):
        a = math.radians(k * 120)
        go.add((math.cos(a) * 13 - 1.3, 33, math.sin(a) * 13 - 1.3), (2.6, 2.6, 2.6), FOXFIRE,
               pivot=(math.cos(a) * 13, 34.3, math.sin(a) * 13), rotation=(45, 45, 0))

    # ------------------------------------------------------------------ legs
    for name, x, z in (("leg_fr", -3.6, -11), ("leg_fl", 3.6, -11), ("leg_br", -3.6, 10.5), ("leg_bl", 3.6, 10.5)):
        s = -1 if x < 0 else 1
        hind = z > 0
        up = m.bone(name, (x, 21, z), "body")
        if hind:
            ellipsoid(up, (x, 17.5, z + 0.5), (2.8, 5, 3.4), FUR, layers=3, mirror=s > 0)
        else:
            obox(up, (x - 2.1, 11, z - 2.3), (4.2, 10.5, 4.6), FUR, mirror=s > 0)
        tuft(up, (x, 13, z + 2.2), (2.6, 3.5, 2), WHITE, pitch=30)
        lo = m.bone(name + "1", (x, 11.5, z), name)
        obox(lo, (x - 1.5, 2, z - 1.5), (3, 10, 3), FUR_LEG, mirror=s > 0)
        obox(lo, (x - 1.9, 0, z - 3), (3.8, 2.4, 5), WHITE, axis="z")
        obox(lo, (x - 1.8, 5.5, z - 1.8), (3.6, 1, 3.6), RED)
        obox(lo, (x - 1.8, 3.2, z - 1.8), (3.6, 0.8, 3.6), GOLD)

    # ------------------------------------------------------------------ ten tails
    tails = []
    for i in range(TAILS):
        if i == TAILS - 1:
            ry, rx = 0.0, 52.0
        else:
            k = i - 4
            ry = k * 24.0
            rx = 40 - abs(k) * 5
        base = (0, 28, 13)
        mat = MOON if i == TAILS - 1 else [TAILF, TAILF, TAILF, TAILF, TAIL_WHITE]

        def fluff(bone, j, p, mat_=mat):
            if j in (1, 2, 3):
                mt = mat_ if not isinstance(mat_, list) else mat_[j]
                for s_ in (-1, 1):
                    tuft(bone, (p[0] + s_ * 3, p[1] + 1, p[2] + 3.5), (2.4, 4.5, 6), mt, yaw=15 * s_, roll=-20 * s_)
        names = chain(m, f"tail{i}_", "body", base, "+z", [6, 7, 7.5, 7, 6],
                      [(4.2, 4.2), (6.8, 6.8), (8.4, 8.4), (7.8, 7.8), (5.8, 5.8)],
                      [(rx, ry, 0), (12, 0, 0), (14, 0, 0), (14, 0, 0), (16, 0, 0)], mat, extra=fluff, rounded=True)
        tails.append(names)
        tip = m.get(names[-1])
        x, y, z = tip.pivot
        g = m.bone(f"glow_fire{i}", tip.pivot, names[-1])
        g.add((x - 2.4, y - 2.4, z + 5.6), (4.8, 4.8, 4.2), FOXFIRE)
        g.add((x - 1.5, y - 1.5, z + 9.4), (3, 3, 3.2), FOXFIRE)
        g.add((x - 0.8, y - 0.8, z + 12.2), (1.6, 1.6, 2.4), FOXFIRE)
    scale_subtree(m, "neck", 1.25)
    seal = m.bone("tail_seal", m.get(tails[-1][1]).pivot, tails[-1][1])
    sx, sy, sz = seal.pivot
    obox(seal, (sx - 4.4, sy - 4.4, sz + 2), (8.8, 8.8, 2.4), ROPE, axis="z")
    seal.add((sx - 0.6, sy - 7.5, sz + 2.6), (1.2, 3.5, 0.4), PAPER)

    c = Creature("tenko", m, scale=1.7, variants=2, variant_expr="variable.ph >= 3 ? 1 : 0",
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
    idle.rot("glow_orbs", [0, f"{t} * 50", 0])
    idle.pos("glow_orbs", [0, wave(1.2, 80), 0])
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
