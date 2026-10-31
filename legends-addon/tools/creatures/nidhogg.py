"""
NIDHOGG (Níðhöggr) — "Malice-Striker, Gnawer of the World-Root".

A colossal serpent-wyrm: a horned skull crowned with backward spines and a
splinter of Yggdrasil's root still clenched in its jaws; two great clawed
forelimbs; a long legless serpent body that ripples as it moves; a tail that
frays into living roots; and vast tattered wings that fold along its back on
the ground and spread for the sky.  Venom-green light leaks from its eyes and
mouth — and in Ragnarök (phase III) from every vein and spine.

Modelled at half size and rendered with entity scale 2.
"""
from __future__ import annotations

import math

from .common import COMMON_PRE, Creature, chain, ellipsoid, kf, mrot, obox, tuft, wave
from mk.geo import Model
from mk.paint import (bone_mat, by_face, d_pixels, d_teeth, fbm, glowball, hx, membrane, mix, scales, shade,
                      solid, horn, fur)


def venom_veins(base_painter, vein="7dff6a", core="d9ffb8"):
    v, c = hx(vein), hx(core)

    def p(f):
        col = base_painter(f)
        if f.variant >= 1 and col[3]:
            x, y, z = f.p
            r = abs(fbm(x * 0.21 + 9, y * 0.21, z * 0.21, 3) - 0.5)
            if r < 0.018:
                return c
            if r < 0.04:
                return mix(col, v, 0.7)
        return col
    return p


def build() -> Creature:
    m = Model("geometry.legends.nidhogg", seed=202, density=2.0)
    m.bounds = (11.0, 7.0, 2.0)

    SC = venom_veins(scales("2a3852", "0c1220", "5f93a8", size=6.0, belly="9a9378", glint="9ff0e0", var=0.04))
    SC_B = venom_veins(scales("2a3852", "0c1220", "5f93a8", size=4.0, belly="9a9378", glint="9ff0e0", var=0.04))
    SC_DARK = venom_veins(scales("1d273a", "080c16", "45708a", size=3.5, var=0.04))
    BELLY = solid("a39d82", 0.06)
    BELLY_D = solid("7f7a63", 0.06)
    HORN = horn("e2dac2", "7d725e")
    HORN_D = horn("b3a98f", "4a4538")
    TOOTH = bone_mat("efe9d6", "a39a80")
    CLAW = bone_mat("3a342e", "0d0b0a")
    MEMB = membrane("4a2238", "16080f", holes=0.07, dark="2a1220", scallop=0.32, glowvein="8dff6a")
    MEMB_IN = membrane("4a2238", "16080f", holes=0.03, dark="2a1220", glowvein="8dff6a")
    WINGBONE = venom_veins(scales("252b3a", "0b0e16", "485868", size=2.0))
    ROOT = solid("5f4127", 0.12)
    ROOT_D = solid("3b2716", 0.12)
    MOSS = solid("3d5a2a", 0.15)
    MOUTH = solid("2a0f14", 0.05, edge=0)
    GLOW_EYE = glowball("f4ffe0", "58e83a")
    GLOW_VEN = glowball("d8ffb8", "3fbf2a")

    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 15, 0), "root")
    body.loc("chest", (0, 15, -4))
    # ------------------------------------------------------------------ chest: rounded mass, plated belly, spined back
    ellipsoid(body, (0, 16.5, -1), (11, 9, 13.5), SC, layers=5, axis="z")
    obox(body, (-6.5, 7.6, -11), (13, 2.2, 22), BELLY, axis="z")
    for z in range(-10, 11, 3):
        body.add((-6.8, 7.4, z), (13.6, 0.6, 1.2), BELLY_D)
    for s_ in (-1, 1):                                                  # shoulder plates
        tuft(body, (s_ * 8.5, 18, -8), (5, 7, 9), SC_DARK, yaw=0, pitch=0, roll=-25 * s_)
    for i, z in enumerate((-11, -6, -1, 4, 9)):                        # great dorsal spines
        h = (6, 9, 11, 9, 7)[i]
        body.add((-1.1, 23, z - 1.4), (2.2, h, 2.8), HORN, pivot=(0, 23, z), rotation=(38, 0, 0))
        for s_ in (-1, 1):
            body.add((s_ * 3 - 0.6, 22, z - 0.8), (1.2, h * 0.45, 1.6), HORN_D, pivot=(s_ * 3, 22, z), rotation=(40, 0, -20 * s_))
    gs = m.bone("glow_spine", (0, 23, 0), "body")
    for i, z in enumerate((-11, -6, -1, 4, 9)):
        h = (6, 9, 11, 9, 7)[i]
        gs.add((-0.5, 23 + h * 0.3, z - 0.6), (1.0, h * 0.5, 1.2), GLOW_VEN, pivot=(0, 23, z), rotation=(38, 0, 0))

    # ------------------------------------------------------------------ neck & head
    def neck_extra(bone, i, p):
        bone.add((-1, p[1] + 3.8, p[2] - 3.5), (2, 5 - i * 0.4, 2.4), HORN, pivot=(0, p[1] + 4, p[2] - 2), rotation=(35, 0, 0))
        bone.add((-(4.6 - i * 0.4), p[1] - 5.2 + i * 0.3, p[2] - 6.5), (9.2 - i * 0.8, 1.6, 6.2), BELLY)
        for s_ in (-1, 1):
            bone.add((s_ * (5 - i * 0.3) - 0.5, p[1] + 1, p[2] - 4), (1, 2.6, 3), HORN_D, pivot=(s_ * 5, p[1] + 1.5, p[2] - 3),
                     rotation=(30, 0, -35 * s_))
    necks = chain(m, "neck", "body", (0, 18, -12), "-z", [7, 7, 6.5, 6, 6],
                  [(13, 12), (12.2, 11.2), (11.4, 10.5), (10.6, 9.8), (10, 9.4)],
                  [(-24, 0, 0), (-12, 0, 0), (0, 0, 0), (12, 0, 0), (16, 0, 0)], SC_B, extra=neck_extra, rounded=True)
    head = m.bone("head", (0, 18, -44.5), necks[-1])
    head.loc("mouth", (0, 13, -66))
    ellipsoid(head, (0, 19.5, -51), (7, 5.6, 7.5), SC_B, layers=4, axis="z")      # cranium
    obox(head, (-4.4, 14.4, -66.5), (8.8, 7.4, 16), SC_B, axis="z")             # long snout
    obox(head, (-3.4, 20.8, -64), (6.8, 1.8, 12), SC_DARK, axis="z")            # nasal ridge
    nost = d_pixels(["##....##", "##....##"], {"#": "0a0a0a"}, center=True)
    head.add((-3.8, 18.2, -66.8), (7.6, 2.6, 0.6), SC_DARK, decals={"north": nost})
    for s_ in (-1, 1):
        tuft(head, (s_ * 5.8, 23, -55.5), (5, 2.6, 9), HORN_D, yaw=-12 * s_, pitch=-10, roll=18 * s_)   # brow ridge
        for k in range(5):                                                               # upper teeth
            z = -64.5 + k * 3
            head.add((s_ * 3.9 - 0.5, 12.2, z), (1, 2.6 - (k % 2) * 0.8, 1), TOOTH)
        tuft(head, (s_ * 3.6, 23.5, -62), (1.2, 2.6, 1.2), HORN, pitch=-30)                 # nose horns
    head.add((-4.2, 13.6, -66.2), (8.4, 1.2, 16), MOUTH, faces=("down",))
    ge = m.bone("glow_eyes", (0, 20, -55), "head")
    for s_ in (-1, 1):
        ge.add((s_ * 6.9 - 0.45, 19.2, -57.5), (0.9, 1.8, 4), GLOW_EYE)
    # crown of horns: two great horns + brow horns + a crest of spikes
    hl = [7, 7, 6, 5, 4]
    hs = [(4.2, 4.2), (3.6, 3.6), (2.9, 2.9), (2.1, 2.1), (1.4, 1.4)]
    hr = [(-34, -16, 0), (-12, -8, 0), (-8, -6, 0), (6, -4, 0), (14, 0, 0)]
    HM = [HORN, HORN, HORN, HORN_D, HORN_D]
    chain(m, "horn_r", "head", (-4.6, 23, -47), "+z", hl, hs, hr, HM, rounded=True)
    chain(m, "horn_l", "head", (4.6, 23, -47), "+z", hl, hs, [mrot(r) for r in hr], HM, rounded=True)
    for s_ in (-1, 1):
        for k, (y, z, ln, rx, ry) in enumerate(((21, -50, 6, -28, -35), (18.5, -48, 5, -12, -45), (16, -47, 4.5, 4, -50))):
            head.add((s_ * 6.2 - 0.7, y - 0.7, z), (1.4, 1.4, ln), HORN_D, pivot=(s_ * 6.2, y, z), rotation=(rx, ry * s_, 0))
    for k in range(4):
        head.add((-0.6, 24.2, -58 + k * 3.2), (1.2, 2.4 - k * 0.3, 1.6), HORN_D, pivot=(0, 24.2, -57 + k * 3.2), rotation=(30, 0, 0))
    # frills behind the jaw: membrane fans on spines
    for s_ in (-1, 1):
        fr = m.bone("frill_" + ("r" if s_ < 0 else "l"), (s_ * 6, 16, -46), "head", (0, -40 * s_, 0))
        for k in range(3):
            tuft(fr, (s_ * (8 + k * 0.4), 16 + (k - 1) * 3.2, -44.5), (1, 1, 7), HORN_D, yaw=0, pitch=(k - 1) * 22)
        fr.add((s_ * 6 + (-0.1 if s_ < 0 else 0), 11.5, -46), (0.2, 9, 7), MEMB_IN, density=1.5)
    # lower jaw
    jaw = m.bone("jaw", (0, 15, -47), "head")
    obox(jaw, (-4, 10.4, -66), (8, 4.2, 19.5), SC_B, axis="z")
    jaw.add((-3.6, 14.4, -65.5), (7.2, 0.4, 17), MOUTH, faces=("up",))
    for s_ in (-1, 1):
        for k in range(5):
            jaw.add((s_ * 3.5 - 0.5, 14.4, -64.8 + k * 3.1), (1, 2.2 - (k % 2) * 0.7, 1), TOOTH)
        jaw.add((s_ * 4.6 - 0.7, 8.8, -54), (1.4, 2.6, 6), HORN_D, pivot=(s_ * 4.6, 10, -51), rotation=(25, -15 * s_, 0))
    gm = m.bone("glow_maw", (0, 13, -55), "jaw")
    gm.add((-2.8, 14.5, -62), (5.6, 0.6, 14), GLOW_VEN)
    # the splinter of Yggdrasil's root clenched in its jaws
    rt = m.bone("jaw_root", (0, 14.5, -58), "jaw")
    rt.add((-15, 13.4, -59.5), (30, 2.8, 2.8), ROOT, pivot=(0, 14.5, -58), rotation=(0, 12, -6))
    rt.add((-17, 12, -60.5), (5, 2.2, 2.2), ROOT_D, pivot=(-15, 13.5, -59), rotation=(0, 25, -30))
    rt.add((12, 11.5, -58), (6, 1.8, 1.8), ROOT_D, pivot=(13, 13.5, -58), rotation=(0, -30, 35))
    rt.add((-8, 10, -60.2), (1.4, 5, 1.4), ROOT_D, pivot=(-8, 13.5, -59.5), rotation=(0, 0, 12))
    rt.add((-13.5, 15.4, -60), (3.4, 1.2, 2.4), MOSS)

    # ------------------------------------------------------------------ serpent coils & root tail
    def seg_extra(bone, i, p):
        h = max(2.5, 8.5 - i * 1.0)
        bone.add((-1, p[1] + 5.8 - i * 0.6, p[2] + 1.5), (2, h, 2.6), HORN, pivot=(0, p[1] + 6 - i * 0.5, p[2] + 2.5), rotation=(38, 0, 0))
        for s_ in (-1, 1):
            bone.add((s_ * (5.6 - i * 0.55) - 0.5, p[1] + 3.5 - i * 0.4, p[2] + 2), (1, h * 0.35, 1.4), HORN_D,
                     pivot=(s_ * 5.6, p[1] + 4, p[2] + 2.5), rotation=(40, 0, -30 * s_))
        bone.add((-(6.6 - i * 0.65), p[1] - 6.2 + i * 0.5, p[2]), (13.2 - i * 1.3, 1.4, 7), BELLY)
    segs = chain(m, "seg", "body", (0, 15, 11), "+z", [8, 8, 7.5, 7, 6.5, 6],
                 [(19.5, 15.5), (18, 14.5), (16, 13), (14, 11.6), (12, 10.2), (10, 8.8)],
                 [(0, -8, 0), (0, 12, 0), (0, 14, 0), (0, -10, 0), (0, -14, 0), (0, 10, 0)],
                 SC, extra=seg_extra, rounded=True)
    gse = m.bone("glow_segs", (0, 21, 15), segs[1])
    for z, hgt in ((21.5, 3.2), (14.5, 3.6)):
        gse.add((-0.5, 20.5, z), (1.0, hgt, 1.0), GLOW_VEN, pivot=(0, 20.5, z + 0.5), rotation=(38, 0, 0))
    tails = chain(m, "tail", segs[-1], (0, 15, 54), "+z", [6, 6, 5, 5, 4.5],
                  [(8.4, 7.6), (7, 6.3), (5.6, 5), (4.2, 4), (3, 3)],
                  [(0, -10, 0), (0, -14, 0), (-6, 10, 0), (-6, 14, 0), (-8, 10, 0)],
                  [SC, SC_DARK, ROOT, ROOT, ROOT_D], rounded=True)
    tip = m.get(tails[-1])
    tz = 54 + 6 + 6 + 5 + 5
    for k, (ry, rx, ln) in enumerate(((-38, -10, 8), (0, -28, 9), (38, -5, 8), (16, 22, 7), (-22, 26, 7), (55, 10, 6))):
        tip.add((-0.7, 14.3, tz + 3), (1.4, 1.4, ln), ROOT if k % 2 else ROOT_D, pivot=(0, 15, tz + 3), rotation=(rx, ry, 0))
    tip.add((-2, 13, tz), (4, 4, 4), MOSS)
    gt = m.bone("glow_tailroots", (0, 15, tz + 3), tails[-1])
    for k, (ry, rx, ln) in enumerate(((-38, -10, 8), (0, -28, 9), (38, -5, 8))):
        gt.add((-0.5, 14.5, tz + 3 + ln - 1.2), (1, 1, 1.6), GLOW_VEN, pivot=(0, 15, tz + 3), rotation=(rx, ry, 0))

    # ------------------------------------------------------------------ forelimbs
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        up = m.bone(f"arm_{side}", (s * 8.5, 12, -7), "body", (-20, 0, -12 * s))
        obox(up, (s * 9 - 3.6, 2.5, -10.6), (7.2, 11, 7.2), SC_B, mirror=(s > 0))
        tuft(up, (s * 11.5, 6, -6), (1.4, 1.4, 5), HORN_D, pitch=-40, yaw=-20 * s)          # elbow spike
        lo = m.bone(f"arm_{side}1", (s * 9, 3.5, -7), up.name, (35, 0, 0))
        obox(lo, (s * 9 - 2.8, -5, -9.8), (5.6, 9, 5.6), SC_B, mirror=(s > 0))
        hd = m.bone(f"hand_{side}", (s * 9, -4.5, -7), lo.name, (-15, 0, 0))
        obox(hd, (s * 9 - 3.6, -7, -12), (7.2, 3, 7.5), SC_DARK, axis="z")
        for k, dx in enumerate((-2.6, -0.9, 0.9, 2.6)):
            hd.add((s * 9 + dx - 0.7, -7.6, -17.5), (1.4, 1.8, 6), CLAW, pivot=(s * 9 + dx, -6.5, -12), rotation=(20, dx * 6, 0))
        hd.add((s * 9 - s * 3.8 - 0.7, -7.2, -11), (1.4, 1.6, 4.5), CLAW, pivot=(s * 9 - s * 3.8, -6.5, -10), rotation=(10, -40 * s, 0))

    # ------------------------------------------------------------------ vast tattered wings (4 fingers)
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        sh = m.bone(f"wing_{side}", (s * 7, 22, -6), "body")
        x0 = s * 7 + (-17 if s < 0 else 0)
        obox(sh, (x0, 20.2, -7.9), (17, 3.8, 3.8), WINGBONE, axis="x", mirror=(s > 0))
        for k in range(3):
            tuft(sh, (s * (11 + k * 5), 23.6, -7), (1.2, 3, 1.2), HORN_D, roll=-30 * s, pitch=-20)
        sh.add((x0, 21.9, -5.5), (17, 0, 20), MEMB_IN, density=1.2, mirror=(s > 0))
        fa = m.bone(f"wing_{side}1", (s * 24, 22, -6), sh.name)
        x1 = s * 24 + (-21 if s < 0 else 0)
        obox(fa, (x1, 20.6, -7.5), (21, 2.9, 2.9), WINGBONE, axis="x", mirror=(s > 0))
        fa.add((x1, 22, -5.5), (21, 0, 22), MEMB_IN, density=1.2, mirror=(s > 0))
        tuft(fa, (s * 45, 22.6, -9), (2.2, 2.2, 6), CLAW, pitch=0, yaw=20 * s)              # wrist claw
        for k, (ln, ry, w) in enumerate(((32, 6, 14), (29, 24, 13), (25, 42, 12), (20, 62, 10))):
            fg = m.bone(f"wing_{side}f{k}", (s * 45, 22, -6), fa.name, (0, -ry * s, 0))
            xf = s * 45 + (-ln if s < 0 else 0)
            obox(fg, (xf, 21.1, -6.9), (ln, 1.8, 1.8), WINGBONE, axis="x", mirror=(s > 0))
            fg.add((xf, 22, -6), (ln, 0, w), MEMB, density=1.2, mirror=(s > 0))

    c = Creature("nidhogg", m, scale=2.3, variants=2, variant_expr="variable.ph >= 3 ? 1 : 0",
                 description="Nidhogg, Gnawer of the World-Root")
    c.preview_props = {"legends:var": 0}
    c.pre = COMMON_PRE + [
        "variable.fly = math.lerp(variable.fly ?? 0.0, query.property('legends:var') == 1 ? 1.0 : 0.0, 0.07)",
        "variable.slither = variable.mv * (1.0 - variable.fly) * variable.calm",
    ]
    for b in ("glow_spine", "glow_segs", "glow_tailroots"):
        c.visibility.append((b, "variable.ph >= 3"))

    t = "q.life_time"
    idle = c.loop("idle", "variable.calm")
    idle.pos("body", [0, wave(0.4, 80), 0])
    for i, nb in enumerate(necks):
        idle.rot(nb, [wave(2, 70, -i * 25), wave(3, 45, -i * 30), 0])
    idle.rot("head", ["query.target_x_rotation * 0.4", "query.target_y_rotation * 0.4", 0])
    idle.rot("jaw", [f"math.max(0.0, {wave(6, 60)}) + 3.0", 0, 0])
    for i, sb in enumerate(segs + tails):
        idle.rot(sb, [0, wave(3 + i * 0.4, 70, -i * 35), 0])

    fold = c.loop("fold", "1.0 - variable.fly")
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        fold.rot(f"wing_{side}", [-15, 78 * -s, 28 * -s])
        fold.rot(f"wing_{side}1", [0, -150 * -s, 0])
        for k in range(4):
            fold.rot(f"wing_{side}f{k}", [0, (150 - k * 10) * -s, 0])

    fly = c.loop("fly", "variable.fly")
    fl = f"{t} * 160"
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        fly.rot(f"wing_{side}", [f"math.sin({fl}) * 4", 8 * -s, f"(math.sin({fl}) * 38 + 8) * {-s}"])
        fly.rot(f"wing_{side}1", [0, f"(math.sin({fl} - 40) * 10 - 4) * {-s}", f"(math.sin({fl} - 50) * 18) * {-s}"])
        for k in range(4):
            fly.rot(f"wing_{side}f{k}", [0, 0, f"(math.sin({fl} - 80 - {k * 10}) * 12) * {-s}"])
    fly.pos("body", [0, f"math.sin({fl} + 180) * 1.6", 0])
    for i, sb in enumerate(segs + tails):
        fly.rot(sb, [wave(4, 120, -i * 40), wave(5, 90, -i * 30), 0])
    for i, nb in enumerate(necks):
        fly.rot(nb, [wave(2.5, 160, -i * 30 - 60), 0, 0])
    for side in ("r", "l"):
        fly.rot(f"arm_{side}", [55, 0, 0])
        fly.rot(f"arm_{side}1", [-40, 0, 0])

    sl = c.loop("slither", "variable.slither")
    dm = "variable.dist * 30.0"
    for i, sb in enumerate(segs + tails):
        sl.rot(sb, [0, f"math.sin({dm} - {i * 45}) * {10 + i}", 0])
    for side, ph in (("r", 0), ("l", 180)):
        sl.rot(f"arm_{side}", [f"math.sin({dm} + {ph}) * 30", 0, 0])
        sl.rot(f"arm_{side}1", [f"math.max(0.0, math.cos({dm} + {ph})) * 25", 0, 0])
    sl.pos("body", [0, f"math.abs(math.sin({dm})) * 0.6", 0])

    # ---------------------------------------------------------------- acts
    a = c.act("emerge", 3.6, [2.4])
    a.pos("root", kf({0: [0, -34, 0], 1.6: [0, -20, 0], 2.4: [0, 2, 0], 3.0: [0, -1, 0], 3.6: [0, 0, 0]}))
    a.rot("body", kf({0: [-50, 0, 0], 1.6: [-45, 0, 0], 2.4: [-25, 0, 0], 3.6: [0, 0, 0]}))
    a.rot("neck0", kf({0: [-10, 0, 0], 2.4: [-30, 0, 0], 2.8: [-35, 15, 0], 3.2: [-30, -15, 0], 3.6: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 2.4: [10, 0, 0], 2.7: [45, 0, 0], 3.3: [40, 0, 0], 3.6: [0, 0, 0]}))

    a = c.act("roar", 2.2, [0.6])
    for i, nb in enumerate(necks):
        a.rot(nb, kf({0: [0, 0, 0], 0.5: [-10 - i * 3, 0, 0], 1.5: [-8 - i * 3, 0, 0], 2.2: [0, 0, 0]}))
    a.rot("head", kf({0: [0, 0, 0], 0.5: [-25, 0, 0], 1.0: [-25, 0, 10], 1.4: [-25, 0, -10], 2.2: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.5: [50, 0, 0], 1.7: [45, 0, 0], 2.2: [0, 0, 0]}))
    a.rot("body", kf({0: [0, 0, 0], 0.5: [-12, 0, 0], 1.7: [-10, 0, 0], 2.2: [0, 0, 0]}))

    a = c.act("bite", 1.3, [0.6])
    for i, nb in enumerate(necks):
        a.rot(nb, kf({0: [0, 0, 0], 0.4: [-12, 0, 0], 0.6: [10 + i * 2, 0, 0], 0.9: [4, 0, 0], 1.3: [0, 0, 0]}))
    a.pos("body", kf({0: [0, 0, 0], 0.4: [0, 0, 4], 0.6: [0, 0, -8], 0.9: [0, 0, -4], 1.3: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.45: [55, 0, 0], 0.6: [0, 0, 0], 1.3: [0, 0, 0]}))

    a = c.act("tail_sweep", 1.5, [0.75])
    for i, sb in enumerate(segs + tails):
        a.rot(sb, kf({0: [0, 0, 0], 0.45: [0, -(8 + i * 2), 0], 0.75: [0, 14 + i * 3, 0], 1.1: [0, 6, 0], 1.5: [0, 0, 0]}))
    a.rot("body", kf({0: [0, 0, 0], 0.45: [0, 15, 0], 0.75: [0, -25, 0], 1.5: [0, 0, 0]}))

    a = c.act("burrow", 1.6, [1.2])
    a.rot("body", kf({0: [0, 0, 0], 0.5: [-25, 0, 0], 1.2: [55, 0, 0], 1.6: [70, 0, 0]}))
    a.pos("root", kf({0: [0, 0, 0], 0.5: [0, 4, 0], 1.2: [0, -20, 0], 1.6: [0, -40, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.5: [40, 0, 0], 1.2: [10, 0, 0]}))

    a = c.act("underground", 1.0, [], loop=True)
    a.pos("root", [0, -60, 0])
    a.scl("root", 0.01)

    a = c.act("erupt", 1.6, [0.25])
    a.pos("root", kf({0: [0, -40, 0], 0.25: [0, 2, 0], 0.7: [0, 8, 0], 1.2: [0, 0, 0], 1.6: [0, 0, 0]}))
    a.rot("body", kf({0: [-70, 0, 0], 0.25: [-55, 0, 0], 0.7: [-35, 0, 0], 1.6: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.2: [55, 0, 0], 0.9: [40, 0, 0], 1.6: [0, 0, 0]}))

    a = c.act("root_snare", 1.5, [0.8])
    a.rot("body", kf({0: [0, 0, 0], 0.55: [-22, 0, 0], 0.8: [8, 0, 0], 1.5: [0, 0, 0]}))
    for side in ("r", "l"):
        a.rot(f"arm_{side}", kf({0: [0, 0, 0], 0.55: [-70, 0, 0], 0.8: [20, 0, 0], 1.5: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.55: [30, 0, 0], 0.85: [45, 0, 0], 1.5: [0, 0, 0]}))

    a = c.act("takeoff", 1.8, [1.0])
    a.pos("body", kf({0: [0, 0, 0], 0.6: [0, -3, 0], 1.0: [0, 6, 0], 1.8: [0, 0, 0]}))
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        a.rot(f"wing_{side}", kf({0: [0, 0, 0], 0.6: [0, 0, 40 * -s], 1.0: [0, 0, -30 * -s], 1.4: [0, 0, 35 * -s], 1.8: [0, 0, 0]}))

    a = c.act("land", 1.4, [0.6])
    a.pos("body", kf({0: [0, 6, 0], 0.6: [0, -3, 0], 1.0: [0, 0.5, 0], 1.4: [0, 0, 0]}))
    a.rot("body", kf({0: [-15, 0, 0], 0.6: [6, 0, 0], 1.4: [0, 0, 0]}))
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        a.rot(f"wing_{side}", kf({0: [0, 0, 30 * -s], 0.6: [0, 0, -20 * -s], 1.4: [0, 0, 0]}))

    a = c.act("strafe", 1.0, [], loop=True)
    a.rot("neck0", [10, 0, 0])
    a.rot("neck3", [15, 0, 0])
    a.rot("head", [20, 0, 0])
    a.rot("jaw", [f"40 + {wave(6, 1100)}", 0, 0])

    a = c.act("breath", 3.0, [0.8])
    a.rot("neck0", kf({0: [0, 0, 0], 0.6: [-10, 0, 0], 2.6: [-10, 0, 0], 3.0: [0, 0, 0]}))
    a.rot("neck2", kf({0: [0, 0, 0], 0.6: [0, -25, 0], 1.7: [8, 0, 0], 2.6: [0, 25, 0], 3.0: [0, 0, 0]}, smooth=True))
    a.rot("neck4", kf({0: [0, 0, 0], 0.6: [0, -20, 0], 1.7: [8, 0, 0], 2.6: [0, 20, 0], 3.0: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.6: [45, 0, 0], 2.6: [45, 0, 0], 3.0: [0, 0, 0]}))

    a = c.act("gale", 1.8, [0.7, 1.4])
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        a.rot(f"wing_{side}", kf({0: [0, 0, 0], 0.45: [-20, -10 * s, 45 * -s], 0.7: [25, 25 * s, -35 * -s],
                                  1.15: [-20, -10 * s, 45 * -s], 1.4: [25, 25 * s, -35 * -s], 1.8: [0, 0, 0]}))
    a.rot("body", kf({0: [0, 0, 0], 0.45: [-15, 0, 0], 0.7: [5, 0, 0], 1.15: [-15, 0, 0], 1.4: [5, 0, 0], 1.8: [0, 0, 0]}))

    a = c.act("dive", 1.7, [1.15])
    a.rot("body", kf({0: [0, 0, 0], 0.6: [-20, 0, 0], 1.0: [40, 0, 0], 1.15: [45, 0, 0], 1.7: [0, 0, 0]}))
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        a.rot(f"wing_{side}", kf({0: [0, 0, 0], 0.6: [0, 0, 45 * -s], 1.0: [0, 50 * -s, -10 * -s], 1.4: [0, 30 * -s, 0], 1.7: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.9: [50, 0, 0], 1.2: [10, 0, 0], 1.7: [0, 0, 0]}))

    a = c.act("ascend", 2.4, [1.2])
    a.rot("body", kf({0: [0, 0, 0], 0.8: [-40, 0, 0], 2.0: [-30, 0, 0], 2.4: [0, 0, 0]}))
    a.rot("head", kf({0: [0, 0, 0], 0.8: [-30, 0, 0], 2.0: [-30, 0, 0], 2.4: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 1.0: [55, 0, 0], 2.0: [50, 0, 0], 2.4: [0, 0, 0]}))

    a = c.act("ragnarok", 7.0, [])
    a.rot("body", kf({0: [0, 0, 0], 0.8: [15, 0, 0], 6.4: [15, 0, 0], 7.0: [0, 0, 0]}))
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        a.rot(f"wing_{side}", kf({0: [0, 0, 0], 0.8: [-10, -15 * s, 20 * -s], 6.4: [-10, -15 * s, 20 * -s], 7.0: [0, 0, 0]}))
    a.rot("head", kf({0: [0, 0, 0], 0.8: [30, 0, 0], 6.4: [30, 0, 0], 7.0: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.8: [50, 0, 0], 6.4: [52, 0, 0], 7.0: [0, 0, 0]}))

    a = c.act("rupture", 2.2, [1.3])
    a.rot("body", kf({0: [0, 0, 0], 0.6: [-30, 0, 0], 1.1: [60, 0, 0], 1.3: [70, 0, 0], 2.2: [0, 0, 0]}))
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        a.rot(f"wing_{side}", kf({0: [0, 0, 0], 0.6: [0, 0, 50 * -s], 1.1: [0, 60 * -s, 0], 2.2: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.8: [55, 0, 0], 1.3: [10, 0, 0], 2.2: [0, 0, 0]}))

    a = c.act("exhausted", 4.0, [], loop="hold_on_last_frame")
    a.pos("body", kf({0: [0, 0, 0], 0.6: [0, -5, 0], 4.0: [0, -5, 0]}))
    a.rot("body", kf({0: [0, 0, 0], 0.6: [8, 0, -10], 4.0: [8, 0, -10]}))
    for i, nb in enumerate(necks):
        a.rot(nb, [f"q.anim_time > 0.5 ? 12 + math.sin(q.anim_time * 200) * 3 : q.anim_time * 24", 0, 0])
    a.rot("jaw", [f"20 + math.sin(q.anim_time * 400) * 8", 0, 0])
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        a.rot(f"wing_{side}", kf({0: [0, 0, 0], 0.6: [0, 0, -25 * -s], 4.0: [0, 0, -25 * -s]}))

    a = c.act("coil", 2.4, [1.8])
    for i, sb in enumerate(segs + tails):
        a.rot(sb, kf({0: [0, 0, 0], 1.2: [0, 28, 0], 1.8: [0, 36, 0], 2.4: [0, 0, 0]}))
    a.rot("body", kf({0: [0, 0, 0], 1.2: [0, -40, 0], 1.8: [0, -60, 0], 2.4: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 1.5: [40, 0, 0], 1.8: [10, 0, 0], 2.4: [0, 0, 0]}))

    a = c.act("death", 5.0, [4.2])
    a.rot("body", kf({0: [0, 0, 0], 1.0: [-30, 0, 0], 2.5: [-20, 0, 30], 4.0: [5, 0, 85], 5.0: [5, 0, 90]}))
    a.pos("body", kf({0: [0, 0, 0], 2.5: [0, 2, 0], 4.0: [0, -6, 0], 5.0: [0, -7, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 1.0: [55, 0, 0], 4.0: [35, 0, 0], 5.0: [30, 0, 0]}))
    for i, nb in enumerate(necks):
        a.rot(nb, kf({0: [0, 0, 0], 1.0: [-12, 0, 0], 4.0: [10, 8, 0], 5.0: [12, 10, 0]}))
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        a.rot(f"wing_{side}", kf({0: [0, 0, 0], 1.0: [0, 0, 40 * -s], 4.0: [0, 0, -20 * -s], 5.0: [0, 0, -25 * -s]}))
    return c
