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

from .common import COMMON_PRE, Creature, chain, kf, mrot, scale_subtree, translate_subtree, wave
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
    m = Model("geometry.legends.nidhogg", seed=202, density=1.0)
    m.bounds = (9.0, 6.0, 1.8)

    SC = venom_veins(scales("2a3550", "0d1220", "4d6188", size=4.0, belly="6d6a52", glint="8fb7d6"))
    SC_B = venom_veins(scales("2a3550", "0d1220", "4d6188", size=3.0, belly="6d6a52", glint="8fb7d6"))
    SC_DARK = venom_veins(scales("1b2236", "070a12", "34436a", size=2.5))
    BELLY = solid("6d6a52", 0.08)
    HORN = horn("cfc6ad", "6a6352")
    HORN_D = horn("8f8670", "4a4538")
    TOOTH = bone_mat("e8e1c9", "9c9278")
    CLAW = bone_mat("2b2723", "0d0b0a")
    MEMB = membrane("3d3150", "181024", holes=0.16, dark="21182c")
    MEMB_T = membrane("3d3150", "181024", holes=0.26, dark="21182c")
    WINGBONE = solid("2c2a38", 0.06)
    ROOT = solid("5a3d24", 0.12)
    ROOT_D = solid("3b2716", 0.12)
    MOSS = solid("3d5a2a", 0.15)
    MOUTH = solid("2a0f14", 0.05, edge=0)
    GLOW_EYE = glowball("eaffd0", "58e83a")
    GLOW_VEN = glowball("c8ffa8", "3fbf2a")

    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 14, 0), "root")
    body.loc("chest", (0, 14, -4))
    body.add((-8, 7.5, -11), (16, 13, 22), SC, inflate=0.3, face_mats={"down": BELLY})
    body.add((-6.5, 6.5, -10), (13, 2, 20), BELLY)
    body.add((-7, 19.5, -9), (14, 3, 18), SC_DARK)
    for i, z in enumerate((-9, -4.5, 0, 4.5, 9)):                                  # dorsal spines
        h = 5 if i in (1, 2, 3) else 3.5
        body.add((-1, 22, z - 1.2), (2, h, 2.4), HORN_D, pivot=(0, 22, z), rotation=(25, 0, 0))
    gs = m.bone("glow_spine", (0, 22, 0), "body")
    for z in (-6.8, -2.3, 2.3, 6.8):
        gs.add((-0.75, 22.5, z - 0.75), (1.5, 3, 1.5), GLOW_VEN, pivot=(0, 22, z), rotation=(25, 0, 0))

    # ------------------------------------------------------------------ neck & head
    def neck_spine(bone, i, p):
        bone.add((-0.8, p[1] + 3.6, p[2] - 3.2), (1.6, 3.4 - i * 0.3, 2), HORN_D, pivot=(0, p[1] + 4, p[2] - 2),
                 rotation=(30, 0, 0))
    necks = chain(m, "neck", "body", (0, 17, -10), "-z", [7, 7, 6.5, 6, 6],
                  [(11, 10), (10, 9.4), (9.4, 8.6), (8.8, 8), (8.2, 7.4)],
                  [(-24, 0, 0), (-12, 0, 0), (0, 0, 0), (12, 0, 0), (16, 0, 0)], SC_B, extra=neck_spine)
    head = m.bone("head", (0, 17, -37.5), necks[-1])
    head.loc("mouth", (0, 13, -58))
    head.add((-5.5, 13.5, -50), (11, 9, 13), SC_B, inflate=0.2)                         # skull
    head.add((-4, 12.5, -59), (8, 6.5, 10), SC_B)                                       # snout
    head.add((-6, 19.5, -49), (12, 2.5, 8), SC_DARK)                                    # brow plate
    for s in (-1, 1):
        head.add((s * 4.6 - 1.6, 18.5, -51), (3.2, 2.2, 6), HORN_D, pivot=(s * 4.6, 19.5, -48), rotation=(-12, 0, 10 * s))
        head.add((s * 2.6 - 0.9, 17.8, -58.6), (1.8, 1.2, 3), HORN_D)                  # nostril ridges
    head.add((-3.6, 11, -58.8), (7.2, 1.6, 9.5), TOOTH, decals={"north": d_teeth(row="bottom", step=2, height=1)},
             faces=("north", "east", "west", "down"))
    for s in (-1, 1):
        head.add((s * 3.2 - 0.6, 9, -58), (1.2, 3, 1.2), TOOTH, pivot=(s * 3.2, 11, -57.5), rotation=(-10, 0, 0))
        head.add((s * 4.4 - 0.6, 9.8, -52), (1.2, 2.5, 1.2), TOOTH)
    nost = d_pixels(["#....#"], {"#": "0a0a0a"}, center=True)
    head.add((-3, 17.5, -59.4), (6, 1.5, 0.6), SC_DARK, decals={"north": nost})
    # crown of backward horns
    hl = [6, 6, 5, 4]
    hs = [(3.2, 3.2), (2.7, 2.7), (2.1, 2.1), (1.4, 1.4)]
    hr = [(-38, -18, 0), (-10, -6, 0), (-6, -4, 0), (8, 0, 0)]
    chain(m, "horn_r", "head", (-4, 21, -42), "+z", hl, hs, hr, [HORN, HORN, HORN, HORN_D], share="nhorn")
    chain(m, "horn_l", "head", (4, 21, -42), "+z", hl, hs, [mrot(r) for r in hr], [HORN, HORN, HORN, HORN_D],
          share="nhorn", mirror=True)
    for s in (-1, 1):                                                                    # lesser cheek spikes
        for k, (y, z, ln) in enumerate(((17, -44, 5), (15, -42, 4), (19.5, -45, 4))):
            head.add((s * 5.5 - 0.7, y - 0.7, z), (1.4, 1.4, ln), HORN_D, pivot=(s * 5.5, y, z),
                     rotation=(-15 + k * 12, -25 * s, 0))
    ge = m.bone("glow_eyes", (0, 18, -50), "head")
    for s in (-1, 1):
        ge.add((s * 5.6 - 0.6, 16.5, -49.5), (1.2, 1.6, 3), GLOW_EYE)
    jaw = m.bone("jaw", (0, 13.5, -41), "head")
    jaw.add((-4.8, 10, -57.5), (9.6, 3.5, 17), SC_B, face_mats={"up": MOUTH})
    jaw.add((-3.4, 13.4, -57), (6.8, 1.4, 8.5), TOOTH, decals={"north": d_teeth(row="top", step=2)},
            faces=("north", "east", "west", "up"))
    for s in (-1, 1):
        jaw.add((s * 3 - 0.6, 13, -56.8), (1.2, 2.8, 1.2), TOOTH, pivot=(s * 3, 13.5, -56), rotation=(12, 0, 0))
        jaw.add((s * 5 - 0.7, 8.5, -50), (1.4, 2, 6), HORN_D, pivot=(s * 5, 9.5, -47), rotation=(20, -20 * s, 0))
    gm = m.bone("glow_maw", (0, 12, -50), "jaw")
    gm.add((-3, 12.2, -55), (6, 0.8, 12), GLOW_VEN)
    # splinter of Yggdrasil's root clenched in the jaws
    rt = m.bone("jaw_root", (0, 13, -54), "jaw")
    rt.add((-12, 12.2, -55), (24, 2.2, 2.4), ROOT, pivot=(0, 13, -54), rotation=(0, 12, -6))
    rt.add((-14, 11, -56), (4, 2, 2), ROOT_D, pivot=(-12, 12, -55), rotation=(0, 20, -30))
    rt.add((9, 10, -54), (5, 1.6, 1.6), ROOT_D, pivot=(10, 12, -54), rotation=(0, -30, 35))
    rt.add((-6, 9, -55.6), (1.2, 4, 1.2), ROOT_D, pivot=(-6, 12, -55), rotation=(0, 0, 12))
    rt.add((-11, 13.6, -55.4), (3, 1, 2), MOSS)

    # ------------------------------------------------------------------ serpent body & root tail
    def seg_spines(bone, i, p):
        h = max(1.5, 4.2 - i * 0.35)
        bone.add((-0.8, p[1] + 5.5 - i * 0.55, p[2] + 1.5), (1.6, h, 2), HORN_D, pivot=(0, p[1] + 6 - i * 0.5, p[2] + 2.5),
                 rotation=(28, 0, 0))
        bone.add((-(6.4 - i * 0.6), p[1] - 5.2 + i * 0.45, p[2]), (12.8 - i * 1.2, 1.2, 6), BELLY)
    segs = chain(m, "seg", "body", (0, 14, 10), "+z", [8, 8, 7, 7, 6, 6],
                 [(16, 13), (15, 12.5), (13.5, 11), (12, 10), (10, 8.5), (8.5, 7.5)],
                 [(0, -8, 0), (0, 12, 0), (0, 14, 0), (0, -10, 0), (0, -14, 0), (0, 10, 0)],
                 SC, extra=seg_spines)
    gse = m.bone("glow_segs", (0, 20, 14), segs[1])
    gse.add((-0.6, 19.5, 21), (1.2, 2.6, 1.2), GLOW_VEN, pivot=(0, 19.5, 21.5), rotation=(28, 0, 0))
    tails = chain(m, "tail", segs[-1], (0, 14, 52), "+z", [5, 5, 4, 4, 4],
                  [(6, 5.5), (5, 4.6), (4, 3.8), (3, 3), (2.2, 2.2)],
                  [(0, -10, 0), (0, -14, 0), (-6, 10, 0), (-6, 14, 0), (-8, 10, 0)],
                  [SC, SC_DARK, ROOT, ROOT, ROOT_D])
    tip = m.get(tails[-1])
    for k, (ry, rx, ln) in enumerate(((-35, -10, 7), (0, -25, 8), (35, -5, 7), (15, 20, 6), (-20, 25, 6))):
        tip.add((-0.6, 13.4, 74), (1.2, 1.2, ln), ROOT if k % 2 else ROOT_D, pivot=(0, 14, 74), rotation=(rx, ry, 0))
    tip.add((-1.5, 12.5, 72), (3, 3, 3), MOSS)

    # ------------------------------------------------------------------ forelimbs
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        up = m.bone(f"arm_{side}", (s * 7.5, 12, -6), "body", (-20, 0, -12 * s))
        up.add((s * 8 - 3, 3, -9), (6, 10, 6), SC_B, mirror=(s > 0))
        lo = m.bone(f"arm_{side}1", (s * 8, 4, -6), up.name, (35, 0, 0))
        lo.add((s * 8 - 2.3, -4, -8.3), (4.6, 8.5, 4.6), SC_B, mirror=(s > 0))
        hd = m.bone(f"hand_{side}", (s * 8, -3.5, -6), lo.name, (-15, 0, 0))
        hd.add((s * 8 - 3, -5.5, -10), (6, 2.5, 6), SC_DARK)
        for k, dx in enumerate((-2, 0, 2)):
            hd.add((s * 8 + dx - 0.6, -6, -14), (1.2, 1.6, 4.5), CLAW, pivot=(s * 8 + dx, -5, -10), rotation=(18, dx * 6, 0))
        hd.add((s * 8 - s * 3 - 0.6, -5.8, -9), (1.2, 1.4, 3.5), CLAW, pivot=(s * 8 - s * 3, -5, -8), rotation=(10, -40 * s, 0))

    # ------------------------------------------------------------------ tattered wings
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        d = "-x" if s < 0 else "+x"
        sh = m.bone(f"wing_{side}", (s * 6, 20, -6), "body")
        sh.add((s * 6 + (-13 if s < 0 else 0), 18.6, -7.4), (13, 2.8, 2.8), WINGBONE, mirror=(s > 0))
        sh.add((s * 6 + (-13 if s < 0 else 0), 19.9, -5), (13, 0, 15), MEMB, density=0.75, share="nm0", mirror=(s > 0))
        fa = m.bone(f"wing_{side}1", (s * 19, 20, -6), sh.name)
        fa.add((s * 19 + (-16 if s < 0 else 0), 18.9, -7.1), (16, 2.2, 2.2), WINGBONE, mirror=(s > 0))
        fa.add((s * 19 + (-16 if s < 0 else 0), 20, -5), (16, 0, 17), MEMB, density=0.75, share="nm1", mirror=(s > 0))
        fa.add((s * 34.5 - 1.5, 19, -8.5), (3, 2, 3), HORN_D)                         # wrist claw
        fa.add((s * 35 - 0.6, 19.4, -12.5), (1.2, 1.2, 4.5), CLAW, pivot=(s * 35, 20, -8), rotation=(0, 20 * s, 0))
        for k, (ln, ry, w) in enumerate(((24, 8, 14), (21, 30, 13), (17, 52, 11))):
            fg = m.bone(f"wing_{side}f{k}", (s * 35, 20, -6), fa.name, (0, -ry * s, 0))
            fg.add((s * 35 + (-ln if s < 0 else 0), 19.4, -6.6), (ln, 1.2, 1.2), WINGBONE, mirror=(s > 0))
            fg.add((s * 35 + (-ln if s < 0 else 0), 20, -6), (ln, 0, w), MEMB_T if k == 2 else MEMB, density=0.7,
                   share=f"nmf{k}", mirror=(s > 0))

    translate_subtree(m, "head", (0, 0, -5))
    scale_subtree(m, "head", 1.4)
    scale_subtree(m, "wing_r", 1.5)
    scale_subtree(m, "wing_l", 1.5)
    c = Creature("nidhogg", m, scale=2.0, variants=2, variant_expr="variable.ph >= 3 ? 1 : 0",
                 description="Nidhogg, Gnawer of the World-Root")
    c.preview_props = {"legends:var": 0}
    c.pre = COMMON_PRE + [
        "variable.fly = math.lerp(variable.fly ?? 0.0, query.property('legends:var') == 1 ? 1.0 : 0.0, 0.07)",
        "variable.slither = variable.mv * (1.0 - variable.fly) * variable.calm",
    ]
    for b in ("glow_spine", "glow_segs"):
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
        for k in range(3):
            fold.rot(f"wing_{side}f{k}", [0, (150 - k * 10) * -s, 0])

    fly = c.loop("fly", "variable.fly")
    fl = f"{t} * 160"
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        fly.rot(f"wing_{side}", [f"math.sin({fl}) * 4", 8 * -s, f"(math.sin({fl}) * 38 + 8) * {-s}"])
        fly.rot(f"wing_{side}1", [0, f"(math.sin({fl} - 40) * 10 - 4) * {-s}", f"(math.sin({fl} - 50) * 18) * {-s}"])
        for k in range(3):
            fly.rot(f"wing_{side}f{k}", [0, 0, f"(math.sin({fl} - 80) * 12) * {-s}"])
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
