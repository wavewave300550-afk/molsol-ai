"""
TAOTIE (饕餮) — "The Devouring Maw".

A quadruped of living ritual bronze whose head is the taotie mask of Shang
vessels: bulging eyes, a flanged nose bridge, C-curled kui-dragon horns and
tiger fangs.  Paoxiao's hidden eyes sleep under its forelimbs (they open in
phase II) and its forefeet are unsettling human hands with gilded nails.
In phase III it devours its own body: only the colossal head remains, riding
a vortex of black-gold cloud scrolls.
"""
from __future__ import annotations

from .common import (COMMON_PRE, Creature, chain, kf, mpt, mrot, ring_cubes, sym, wave)
from mk.geo import Model
from mk.paint import (bone_mat, bronze, by_face, d_band, d_combine, d_pixels, d_teeth, fill, flat, gold,
                      glowball, h2, hx, mix, shade, solid, C, bake, fbm, TRANSPARENT)


def molten(base_painter, crack="ff7a1a", hot="ffd36b"):
    """Variant 1 overlay: glowing hunger-cracks running through the bronze."""
    cr, ht = hx(crack), hx(hot)

    def p(f):
        col = base_painter(f)
        if f.variant >= 1 and col[3]:
            x, y, z = f.p
            r = abs(fbm(x * 0.11 + 4, y * 0.11, z * 0.11 - 2, 3) - 0.5)
            if r < 0.014:
                return ht
            if r < 0.03:
                return mix(col, cr, 0.7)
        return col
    return p


def build() -> Creature:
    m = Model("geometry.legends.taotie", seed=101, density=2.0)
    m.bounds = (8.0, 6.5, 2.0)

    BRZ = molten(bronze("4c6c54", "86c4a7", "c8a456", "1f2b24"))
    BRZ_HEAD = molten(bronze("4c6c54", "86c4a7", "d4ad5c", "1f2b24", band=(0.12, 0.88), cell=7))
    BRZ_PLAIN = molten(bronze("435f4b", "79b49a", "c39a48", "1c2620", motif=False))
    BELLY = molten(bronze("3a4c3d", "6e9a85", "b08a40", "151c18", motif=False))
    GOLD = gold("cf9c3a", "6e4510", "f7dc93", sparkle=0.03)
    MOUTH = solid("4a0c10", 0.06, edge=0)
    TONGUE = solid("a3283a", 0.08)
    TOOTH = bone_mat("f2e8cf", "b5a27e")
    NAIL = gold("e6c25a", "8a6418", "fff4c2")
    HOOF = solid("1b1714", 0.05)
    DARK = solid("10140f", 0.04, edge=0)
    CINNABAR = solid("8f1d14", 0.08)
    EYE = glowball("fff3c2", "ff8a1a")
    CLOUD = bronze("2a1e2e", "5b3b52", "f0c35a", "0c080d", cell=6, band=(0.15, 0.85))

    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 34, 0), "root")

    # ------------------------------------------------------------------ torso (hidden in phase III)
    torso = m.bone("torso", (0, 34, 0), "body")
    torso.add((-17, 26, -25), (34, 26, 16), BRZ, inflate=0.4, face_mats={"down": BELLY})    # shoulder hump
    torso.add((-14.5, 24, -12), (29, 23, 26), BRZ, face_mats={"down": BELLY})                # barrel
    torso.add((-13.5, 25, 12), (27, 21, 13), BRZ, face_mats={"down": BELLY})                 # haunch
    torso.add((-11, 47, -21), (22, 3, 39), BRZ_PLAIN)                                         # rounded back
    torso.add((-15, 50, -24), (30, 4, 12), BRZ_PLAIN)
    torso.add((-12, 21.5, -11), (24, 3, 24), BELLY)                                          # belly plate
    torso.add((-14, 23, -26.5), (28, 18, 3), BELLY, decals={"north": d_band("c39a48", 1)})   # chest plate
    for i, z in enumerate(range(-23, 22, 5)):                                                 # spine flanges 扉棱
        h = 7 if i % 2 == 0 else 5
        y0 = 54 if z < -12 else 50
        torso.add((-1.5, y0, z), (3, h, 3.5), GOLD if i % 3 == 0 else BRZ_PLAIN)
        torso.add((-2.2, y0 + h - 2, z + 0.5), (4.4, 1.2, 2.5), GOLD)
    for z in (-6, 3, 10):                                                                     # side flanges
        torso.add((-15.4, 28, z), (1.4, 15, 2.4), GOLD)
        torso.add((14, 28, z), (1.4, 15, 2.4), GOLD, mirror=True)
    for s in (-1, 1):                                                                         # shoulder flame-scrolls
        torso.add((s * 17 - 3, 42, -22), (6, 8, 10), GOLD, pivot=(s * 17, 46, -17), rotation=(0, 0, -30 * s))
        torso.add((s * 19 - 2, 47, -20), (4, 6, 6), BRZ_PLAIN, pivot=(s * 19, 49, -17), rotation=(0, 0, -55 * s))
    # Paoxiao eyelids (closed) under the forelimbs
    eyelid = d_combine(d_band("0b0b0b", 3, 1))
    torso.add((-17.6, 29, -21), (1, 7, 9), BRZ_PLAIN, decals={"east": eyelid})
    torso.add((16.6, 29, -21), (1, 7, 9), BRZ_PLAIN, decals={"west": eyelid}, mirror=True)
    pupil = d_pixels(["..##..", ".####.", ".####.", "..##.."], {"#": "1a0505"}, center=True)
    g_ar = m.bone("glow_armpit_r", (-18, 32, -16), "torso")
    g_ar.add((-18.3, 28.5, -21.5), (1, 8, 10), EYE, decals={"east": pupil})
    g_al = m.bone("glow_armpit_l", (18, 32, -16), "torso")
    g_al.add((17.3, 28.5, -21.5), (1, 8, 10), EYE, decals={"west": pupil})

    # ------------------------------------------------------------------ neck & head
    neck = m.bone("neck", (0, 44, -22), "body")
    neckf = m.bone("neck_flesh", (0, 44, -22), "neck")
    neckf.add((-12, 33, -34), (24, 20, 14), BRZ_PLAIN, inflate=0.4, face_mats={"down": BELLY})
    for k in range(4):                                                                      # neck mane flames
        neckf.add((-1.5 - k * 0.0, 53, -33 + k * 3.2), (3, 5 - k * 0.6, 3), GOLD)

    head = m.bone("head", (0, 46, -30), "neck")
    head.loc("mouth", (0, 30, -56))
    head.add((-19, 32, -49), (38, 28, 20), BRZ_HEAD, inflate=0.3)                # skull block
    def mask(setp, w, h):
        r = hx("8f1d14")
        for x in range(2, w - 2):
            if abs(x - w / 2 + 0.5) > 3:
                setp(x, h - 2, r)
        for y in range(2, h - 2):
            setp(1, y, r)
            setp(w - 2, y, r)
    head.add((-20, 35, -51.5), (40, 23, 3), BRZ_HEAD, decals={"north": mask})       # face plate
    # kui-dragon brows
    for s in (-1, 1):
        o = (-19.5, 52, -54) if s < 0 else (2.5, 52, -54)
        head.add(o, (17, 5, 6), GOLD, pivot=(s * 2.5, 54.5, -51), rotation=(0, 0, 10 * s))
        head.add((s * 15 - 3, 56, -53), (6, 4, 5), BRZ_PLAIN, pivot=(s * 15, 57, -51), rotation=(0, 0, -25 * s))
    # eye sockets + glowing eyes
    for s in (-1, 1):
        head.add((s * 9.5 - 6.5, 40, -54), (13, 11, 3.5), DARK)
        head.add((s * 9.5 - 7.5, 38.6, -53.4), (15, 1.6, 2.5), GOLD)                   # lower lid
        head.add((s * 9.5 - 7.5, 50.4, -53.4), (15, 1.2, 2.5), CINNABAR)               # upper lid line
    eye_dec = d_pixels(["........", "...##...", "...##...", "...##...", "...##...", "........"],
                       {"#": "1a0503"}, center=True)
    g_er = m.bone("glow_eye_r", (-9.5, 45.5, -54), "head")
    g_er.add((-14.5, 41.5, -54.6), (10, 8, 1.2), EYE, decals={"north": eye_dec})
    g_el = m.bone("glow_eye_l", (9.5, 45.5, -54), "head")
    g_el.add((4.5, 41.5, -54.6), (10, 8, 1.2), EYE, decals={"north": eye_dec})
    # nose-bridge flange & broad nostrils
    head.add((-2.5, 39, -55.5), (5, 17, 4.5), GOLD)
    for k in range(4):
        head.add((-3.1, 41 + k * 3.8, -55.8), (6.2, 1, 1), BRZ_PLAIN)
    nost = d_pixels(["###........###", "###........###"], {"#": "120606"}, center=True)
    head.add((-9, 34, -56), (18, 6, 6), BRZ_HEAD, decals={"north": nost})
    # upper jaw, teeth, tiger fangs
    head.add((-17.5, 29.5, -54), (35, 5, 24), BRZ_PLAIN, face_mats={"down": MOUTH})
    head.add((-16.5, 28, -54.2), (33, 1.6, 1), TOOTH, decals={"north": d_teeth(row="top", step=2)})
    for s in (-1, 1):
        head.add((s * 14 - 1.8, 21, -53.5), (3.6, 9, 3.6), TOOTH, pivot=(s * 14, 30, -52), rotation=(-8, 0, 6 * s))
        head.add((s * 7 - 1.2, 25, -53.3), (2.4, 4.5, 2.4), TOOTH)
    # cheek flares (the mask's ears) with gold scroll curls
    for s in (-1, 1):
        x0 = -27 if s < 0 else 19
        head.add((x0, 33, -49), (8, 19, 13), BRZ_HEAD, pivot=(s * 20, 40, -42), rotation=(0, -20 * s, 0))
        head.add((s * 25 - 3.5, 49, -47), (7, 7, 7), GOLD, pivot=(s * 23, 51, -44), rotation=(0, 0, 28 * s))
        head.add((s * 25 - 4, 26, -46), (8, 8, 6), GOLD, pivot=(s * 23, 30, -44), rotation=(0, 0, -25 * s))
        head.add((s * 24 - 5, 53, -38), (10, 8, 3), BRZ_PLAIN, pivot=(s * 22, 54, -37), rotation=(0, 20 * s, 32 * s))
    # crest of flame-flanges on the brow
    for x in (-12, -6, 0, 6, 12):
        hgt = 7 if x == 0 else 4.5
        head.add((x - 1.3, 59.5, -45 + abs(x) * 0.3), (2.6, hgt, 7), GOLD if x == 0 else BRZ_PLAIN)

    # lower jaw
    jaw = m.bone("jaw", (0, 31, -32), "head")
    jaw.add((-16, 23, -53), (32, 7, 22), BRZ_PLAIN, face_mats={"up": TONGUE})
    jaw.add((-15, 29.9, -52.5), (30, 1.8, 1), TOOTH, decals={"north": d_teeth(row="bottom", step=2)})
    for s in (-1, 1):
        jaw.add((s * 12.5 - 1.6, 28.5, -53.5), (3.2, 7.5, 3.2), TOOTH, pivot=(s * 12.5, 30, -52), rotation=(10, 0, -5 * s))
    jaw.add((-4, 17, -54), (8, 7, 6), GOLD)                                  # chin flange (beard)
    jaw.add((-7, 19, -52), (14, 5, 4), BRZ_PLAIN)
    jaw.add((-6, 29.8, -47), (12, 1.5, 13), TONGUE)
    jaw.add((-14, 23.5, -33), (28, 9, 1), MOUTH)

    # a halo of flame-scroll mane behind the mask (the bronze "fire" of ritual vessels)
    mane = m.bone("mane", (0, 44, -26), "head")
    import math as _m
    for k in range(13):
        a = _m.radians(10 + k * 160 / 12)
        r = 27 + (k % 2) * 4
        px, py = _m.cos(a) * r, 42 + _m.sin(a) * r * 0.85
        ln = 11 + (k % 3) * 2.5
        mane.add((px - 3, py - ln / 2, -27.5), (6, ln, 3.4), GOLD if k % 2 else BRZ, pivot=(px, py, -26),
                 rotation=(0, 0, -(_m.degrees(a) - 90)))
        mane.add((px - 1.6, py + ln / 2 - 1, -27), (3.2, 5.5, 2.4), GOLD, pivot=(px, py, -26),
                 rotation=(0, 0, -(_m.degrees(a) - 90) + 28))
    gmk = m.bone("glow_mask", (0, 46, -52), "head")                                # inlaid luminous mask lines
    for s_ in (-1, 1):
        gmk.add((s_ * 9.5 - 7.5, 51.6, -53.9), (15, 0.7, 0.4), glowball("ffd0a0", "ff4a1a"), pivot=(s_ * 9.5, 52, -53.7), rotation=(0, 0, 10 * s_))
        gmk.add((s_ * 17 - 0.4, 36, -51.9), (0.8, 18, 0.4), glowball("ffd0a0", "ff4a1a"))
    gmk.add((-0.4, 39, -56.1), (0.8, 16, 0.4), glowball("fff0c0", "ffb02a"))
    # C-curled ram horns (chains), the left one mirrored
    hl = [10, 10, 9, 8, 7, 6, 5]
    hs = [(11, 10), (10, 9), (9, 8), (7.5, 7), (6, 5.5), (4.5, 4), (3, 3)]
    hr = [(8, 18, 6), (0, 8, 22), (-4, 4, 30), (-6, 0, 34), (-8, -4, 36), (-8, -6, 34), (-4, -6, 30)]
    HORN = [BRZ_PLAIN, BRZ, BRZ_PLAIN, BRZ, BRZ_PLAIN, GOLD, GOLD]
    chain(m, "horn_r", "head", (-16, 57, -40), "-x", hl, hs, hr, HORN, share="horn")
    chain(m, "horn_l", "head", (16, 57, -40), "+x", hl, hs, [mrot(r) for r in hr], HORN, share="horn", mirror=True)

    # ------------------------------------------------------------------ forelimbs with human hands
    def foreleg(side):
        s = -1 if side == "r" else 1
        up = m.bone(f"leg_f{side}", (s * 14, 42, -15), "body")
        up.add((s * 15 - 6.5, 22, -21.5), (13, 22, 13), BRZ, inflate=0.4)
        up.add((s * 15 - 7, 35, -22), (14, 4, 14), GOLD)                       # bronze armlet
        low = m.bone(f"leg_f{side}1", (s * 14, 23, -15), up.name)
        low.add((s * 14 - 5, 5, -20), (10, 19, 10), BRZ_PLAIN)
        low.add((s * 14 - 5.5, 8, -20.5), (11, 2.5, 11), GOLD)
        hand = m.bone(f"hand_f{side}", (s * 14, 6, -16), low.name)
        hand.add((s * 14 - 6, 0, -24), (12, 5, 11), BELLY)
        for k, fx in enumerate((-4.2, -1.4, 1.4, 4.2)):
            ln = 6 if abs(fx) < 2 else 5
            hand.add((s * 14 + fx - 1.2, 0, -24 - ln), (2.4, 3.2, ln + 0.5), BELLY)
            hand.add((s * 14 + fx - 1.2, 0, -25 - ln), (2.4, 2.2, 1.5), NAIL)
        tx = s * 14 - s * 5.5
        hand.add((tx - 1.5, 0, -21), (3, 3, 5), BELLY, pivot=(tx, 1, -19), rotation=(0, -35 * s, 0))
        hand.add((tx - 1.5 - s * 1.5, 0, -24.5), (2.5, 2, 1.4), NAIL, pivot=(tx, 1, -19), rotation=(0, -35 * s, 0))
    foreleg("r")
    foreleg("l")

    # ------------------------------------------------------------------ goat hind legs
    def hindleg(side):
        s = -1 if side == "r" else 1
        th = m.bone(f"leg_b{side}", (s * 11, 36, 16), "body")
        th.add((s * 11.5 - 6.5, 21, 9), (13, 19, 15), BRZ, inflate=0.3)
        sh = m.bone(f"leg_b{side}1", (s * 11.5, 22, 17), th.name, (25, 0, 0))
        sh.add((s * 11.5 - 4, 9, 13.5), (8, 14, 8), BRZ_PLAIN)
        cn = m.bone(f"leg_b{side}2", (s * 11.5, 10, 17), sh.name, (-25, 0, 0))
        cn.add((s * 11.5 - 3, 2, 14.5), (6, 9, 5), BELLY)
        cn.add((s * 11.5 - 3.5, 0, 13), (7, 3, 7), HOOF)
        cn.add((s * 11.5 - 3.6, 2.6, 13.4), (7.2, 1.5, 6.6), GOLD)
    hindleg("r")
    hindleg("l")

    # ------------------------------------------------------------------ curled tail with flame tuft
    tails = chain(m, "tail", "body", (0, 42, 23), "+z", [6, 5, 5], [(6, 6), (5, 5), (4, 4)],
                  [(30, 0, 0), (35, 0, 0), (40, 0, 0)], [BRZ_PLAIN, BRZ_PLAIN, BRZ_PLAIN])
    tip = m.get(tails[-1])
    tip.add((-3, 40, 37), (6, 6, 5), GOLD, pivot=(0, 42, 38), rotation=(20, 0, 0))

    # ------------------------------------------------------------------ phase III vortex body
    vort = m.bone("vortex", (0, 20, 0), "root")
    for name, r, y, n, th in (("vortex_a", 19, 24, 14, 6), ("vortex_b", 13, 15, 12, 5), ("vortex_c", 8, 7, 9, 4)):
        vb = m.bone(name, (0, y, 0), "vortex")
        ring_cubes(vb, (0, y, 0), r, n, th, 5, CLOUD, plane="xz", arc=290, phase=r * 9)
        for k in range(4):                                   # cloud-scroll flame tongues
            import math as _m
            a = _m.radians(r * 9 + k * 90 + 30)
            px, pz = _m.cos(a) * (r + 2), _m.sin(a) * (r + 2)
            vb.add((px - 2.5, y - 1, pz - 2.5), (5, 6, 5), GOLD, pivot=(px, y, pz), rotation=(0, -k * 90 - 30, 25))
    gv = m.bone("glow_vortex", (0, 10, 0), "vortex")
    gv.add((-3, 1, -3), (6, 6, 6), glowball("fff1b8", "ff7d1f"))
    gv.add((-1.5, 8, -1.5), (3, 14, 3), glowball("ffe08a", "ff5a10"))

    # ------------------------------------------------------------------ creature spec
    c = Creature("taotie", m, scale=1.6, variants=2, variant_expr="variable.ph >= 2 ? 1 : 0",
                 description="Taotie, the Devouring Maw")
    c.pre = COMMON_PRE + [
        "variable.p3 = math.lerp(variable.p3 ?? 0.0, variable.ph >= 3 ? 1.0 : 0.0, 0.06)",
        "variable.walkw = variable.mv * (1.0 - variable.p3) * variable.calm",
    ]
    body_hidden = ["torso", "glow_armpit_r", "glow_armpit_l", "neck_flesh"] + \
                  [b.name for b in m.bones if b.name.startswith(("leg_", "hand_", "tail"))]
    for b in body_hidden:
        c.visibility.append((b, "variable.ph < 3"))
    for b in ("glow_armpit_r", "glow_armpit_l"):
        c.visibility.append((b, "variable.ph == 2"))
    for b in ("vortex", "vortex_a", "vortex_b", "vortex_c", "glow_vortex"):
        c.visibility.append((b, "variable.ph >= 3"))

    t = "q.life_time"
    idle = c.loop("idle", "variable.calm")
    idle.rot("body", [wave(1.2, 90), 0, 0])
    idle.pos("body", [0, f"{wave(0.5, 90)} - variable.p3 * 14.0", "variable.p3 * 37.0"])
    idle.rot("neck", [f"{wave(2.5, 90, -40)} - variable.p3 * 10.0", 0, 0])
    idle.rot("head", ["query.target_x_rotation * 0.5", "query.target_y_rotation * 0.6", wave(1.5, 45)])
    idle.rot("jaw", [f"math.max(0.0, {wave(5, 70)}) + 2.0", 0, 0])
    idle.rot("tail0", [wave(6, 110), wave(14, 80), 0])
    idle.rot("tail1", [wave(8, 110, -40), 0, 0])
    idle.rot("horn_r0", [0, 0, wave(1.2, 60)])
    idle.rot("mane", [0, 0, wave(2.5, 50)])
    idle.rot("horn_l0", [0, 0, wave(-1.2, 60)])
    idle.rot("vortex_a", [0, f"{t} * 160", 0])
    idle.rot("vortex_b", [0, f"-{t} * 230", 0])
    idle.rot("vortex_c", [0, f"{t} * 320", 0])
    idle.pos("vortex", [0, wave(1.5, 120), 0])

    walk = c.loop("walk", "variable.walkw")
    sw = "variable.dist * 22.0"
    walk.rot("leg_fr", [f"math.sin({sw}) * 26.0", 0, 0])
    walk.rot("leg_fl", [f"-math.sin({sw}) * 26.0", 0, 0])
    walk.rot("leg_fr1", [f"math.max(0.0, -math.cos({sw})) * 22.0", 0, 0])
    walk.rot("leg_fl1", [f"math.max(0.0, math.cos({sw})) * 22.0", 0, 0])
    walk.rot("leg_br", [f"-math.sin({sw}) * 24.0", 0, 0])
    walk.rot("leg_bl", [f"math.sin({sw}) * 24.0", 0, 0])
    walk.pos("body", [0, f"math.abs(math.cos({sw})) * 1.4", 0])
    walk.rot("body", [0, 0, f"math.sin({sw}) * 2.0"])
    walk.rot("neck", [f"math.cos({sw} * 2.0) * 3.0", 0, 0])

    # ---------------------------------------------------------------- acts
    a = c.act("emerge", 3.2, [2.4])
    a.pos("root", kf({0: [0, -46, 0], 1.4: [0, -24, 0], 2.2: [0, -2, 0], 2.6: [0, 2, 0], 3.2: [0, 0, 0]}))
    a.rot("body", kf({0: [-30, 0, 0], 1.8: [-20, 0, 0], 2.6: [8, 0, 0], 3.2: [0, 0, 0]}))
    a.rot("neck", kf({0: [-20, 0, 0], 2.2: [-30, 0, 0], 2.6: [-35, 0, 0], 3.2: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 2.2: [5, 0, 0], 2.5: [42, 0, 0], 3.0: [38, 0, 0], 3.2: [0, 0, 0]}))
    a.rot("leg_fr", kf({0: [-70, 0, 0], 1.6: [-50, 0, 0], 2.4: [0, 0, 0]}))
    a.rot("leg_fl", kf({0: [-60, 0, 0], 1.9: [-55, 0, 0], 2.6: [0, 0, 0]}))

    a = c.act("roar", 2.2, [0.7])
    a.rot("body", kf({0: [0, 0, 0], 0.5: [-12, 0, 0], 1.6: [-10, 0, 0], 2.2: [0, 0, 0]}))
    a.rot("neck", kf({0: [0, 0, 0], 0.5: [-28, 0, 0], 0.9: [-22, 6, 0], 1.3: [-22, -6, 0], 1.7: [-20, 0, 0], 2.2: [0, 0, 0]}))
    a.rot("head", kf({0: [0, 0, 0], 0.6: [-10, 0, 8], 1.0: [-10, 0, -8], 1.4: [-10, 0, 6], 2.2: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.5: [48, 0, 0], 1.7: [44, 0, 0], 2.2: [0, 0, 0]}))
    a.rot("leg_fr", kf({0: [0, 0, 0], 0.5: [-25, 0, 0], 1.7: [-20, 0, 0], 2.2: [0, 0, 0]}))
    a.rot("leg_fl", kf({0: [0, 0, 0], 0.5: [-25, 0, 0], 1.7: [-20, 0, 0], 2.2: [0, 0, 0]}))

    a = c.act("claw", 1.4, [0.48, 0.9])
    a.rot("leg_fr", kf({0: [0, 0, 0], 0.32: [-75, 0, -20], 0.48: [20, 0, 10], 0.7: [0, 0, 0]}))
    a.rot("leg_fr1", kf({0: [0, 0, 0], 0.32: [-30, 0, 0], 0.48: [0, 0, 0]}))
    a.rot("leg_fl", kf({0: [0, 0, 0], 0.5: [0, 0, 0], 0.75: [-75, 0, 20], 0.9: [20, 0, -10], 1.1: [0, 0, 0]}))
    a.rot("leg_fl1", kf({0: [0, 0, 0], 0.75: [-30, 0, 0], 0.9: [0, 0, 0]}))
    a.rot("body", kf({0: [0, 0, 0], 0.32: [-6, 8, 0], 0.48: [5, -6, 0], 0.75: [-6, -8, 0], 0.9: [5, 6, 0], 1.4: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.4: [22, 0, 0], 1.0: [10, 0, 0], 1.4: [0, 0, 0]}))

    a = c.act("charge", 1.0, [], loop=True)
    a.rot("neck", [18, 0, 0])
    a.rot("head", [10, 0, 0])
    a.rot("jaw", [f"25 + {wave(8, 900)}", 0, 0])
    gal = "q.anim_time * 1080"
    a.rot("leg_fr", [f"math.sin({gal}) * 45", 0, 0])
    a.rot("leg_fl", [f"math.sin({gal} + 40) * 45", 0, 0])
    a.rot("leg_br", [f"-math.sin({gal}) * 40", 0, 0])
    a.rot("leg_bl", [f"-math.sin({gal} + 40) * 40", 0, 0])
    a.pos("body", [0, f"math.abs(math.sin({gal})) * 2.5", 0])
    a.rot("body", [f"math.sin({gal}) * 4", 0, 0])

    a = c.act("windup", 0.9, [])
    a.rot("body", kf({0: [0, 0, 0], 0.5: [8, 0, 0], 0.9: [10, 0, 0]}))
    a.pos("body", kf({0: [0, 0, 0], 0.5: [0, -3, 3], 0.9: [0, -3.5, 4]}))
    a.rot("neck", kf({0: [0, 0, 0], 0.5: [15, 0, 0], 0.9: [18, 0, 0]}))
    a.rot("leg_fr", kf({0: [0, 0, 0], 0.25: [-30, 0, 0], 0.45: [10, 0, 0], 0.65: [-25, 0, 0], 0.9: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.9: [18, 0, 0]}))

    a = c.act("inhale", 3.2, [2.75])
    a.rot("body", kf({0: [0, 0, 0], 0.5: [-6, 0, 0], 2.5: [-8, 0, 0], 2.75: [10, 0, 0], 3.2: [0, 0, 0]}))
    a.pos("body", kf({0: [0, 0, 0], 0.5: [0, 0, 3], 2.5: [0, 0, 4], 2.75: [0, 0, -6], 3.2: [0, 0, 0]}))
    a.rot("neck", kf({0: [0, 0, 0], 0.5: [-8, 0, 0], 2.5: [-6, 0, 0], 2.75: [14, 0, 0], 3.2: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.6: [55, 0, 0], 2.55: [62, 0, 0], 2.75: [0, 0, 0], 3.2: [0, 0, 0]}))
    a.rot("head", [f"q.anim_time < 2.6 ? {wave(2.5, 1400, t='q.anim_time')} : 0", 0, 0])
    a.scl("head", kf({0: [1, 1, 1], 0.6: [1.06, 1.06, 1.06], 2.55: [1.1, 1.1, 1.1], 2.85: [1, 1, 1]}))

    a = c.act("quake", 1.7, [1.0])
    a.rot("body", kf({0: [0, 0, 0], 0.7: [-32, 0, 0], 0.9: [-30, 0, 0], 1.0: [6, 0, 0], 1.3: [0, 0, 0]}))
    a.pos("body", kf({0: [0, 0, 0], 0.7: [0, 6, 8], 1.0: [0, -2, 0], 1.3: [0, 0, 0]}))
    a.rot("leg_fr", kf({0: [0, 0, 0], 0.7: [-80, 0, -10], 1.0: [10, 0, 0], 1.3: [0, 0, 0]}))
    a.rot("leg_fl", kf({0: [0, 0, 0], 0.7: [-80, 0, 10], 1.0: [10, 0, 0], 1.3: [0, 0, 0]}))
    a.rot("leg_br", kf({0: [0, 0, 0], 0.7: [32, 0, 0], 1.0: [-6, 0, 0], 1.3: [0, 0, 0]}))
    a.rot("leg_bl", kf({0: [0, 0, 0], 0.7: [32, 0, 0], 1.0: [-6, 0, 0], 1.3: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.7: [30, 0, 0], 1.05: [10, 0, 0], 1.7: [0, 0, 0]}))

    a = c.act("gaze", 2.6, [0.8])
    a.rot("leg_fr", kf({0: [0, 0, 0], 0.6: [-20, 0, -35], 2.2: [-20, 0, -35], 2.6: [0, 0, 0]}))
    a.rot("leg_fl", kf({0: [0, 0, 0], 0.6: [-20, 0, 35], 2.2: [-20, 0, 35], 2.6: [0, 0, 0]}))
    a.rot("body", kf({0: [0, 0, 0], 0.6: [-10, 0, 0], 2.2: [-10, 0, 0], 2.6: [0, 0, 0]}))
    a.rot("neck", kf({0: [0, 0, 0], 0.6: [-15, 0, 0], 2.6: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.6: [20, 0, 0], 2.6: [0, 0, 0]}))
    a.scl("glow_armpit_r", kf({0: [1, 1, 1], 0.6: [1, 1.4, 1.4], 2.2: [1, 1.4, 1.4], 2.6: [1, 1, 1]}))
    a.scl("glow_armpit_l", kf({0: [1, 1, 1], 0.6: [1, 1.4, 1.4], 2.2: [1, 1.4, 1.4], 2.6: [1, 1, 1]}))

    a = c.act("summon", 1.5, [0.6])
    a.rot("neck", kf({0: [0, 0, 0], 0.45: [-38, 0, 0], 0.9: [-30, 0, 0], 1.5: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.45: [45, 0, 0], 1.0: [40, 0, 0], 1.5: [0, 0, 0]}))
    a.rot("body", kf({0: [0, 0, 0], 0.45: [-10, 0, 0], 1.5: [0, 0, 0]}))

    a = c.act("pounce", 1.1, [0.35])
    a.pos("body", kf({0: [0, 0, 0], 0.3: [0, -5, 4], 0.45: [0, 3, -2], 0.9: [0, 0, 0]}))
    a.rot("body", kf({0: [0, 0, 0], 0.3: [8, 0, 0], 0.45: [-15, 0, 0], 0.9: [6, 0, 0], 1.1: [0, 0, 0]}))
    a.rot("leg_fr", kf({0: [0, 0, 0], 0.3: [20, 0, 0], 0.45: [-70, 0, 0], 0.9: [0, 0, 0]}))
    a.rot("leg_fl", kf({0: [0, 0, 0], 0.3: [20, 0, 0], 0.45: [-70, 0, 0], 0.9: [0, 0, 0]}))
    a.rot("leg_br", kf({0: [0, 0, 0], 0.3: [-20, 0, 0], 0.45: [40, 0, 0], 0.9: [0, 0, 0]}))
    a.rot("leg_bl", kf({0: [0, 0, 0], 0.3: [-20, 0, 0], 0.45: [40, 0, 0], 0.9: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.45: [40, 0, 0], 0.85: [0, 0, 0]}))

    a = c.act("spit", 1.2, [0.6])
    a.rot("neck", kf({0: [0, 0, 0], 0.45: [-18, 0, 0], 0.6: [16, 0, 0], 0.9: [6, 0, 0], 1.2: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.45: [8, 0, 0], 0.6: [40, 0, 0], 0.9: [20, 0, 0], 1.2: [0, 0, 0]}))

    a = c.act("devour", 4.2, [1.0, 1.8, 2.6, 3.3])
    a.rot("neck", kf({0: [0, 0, 0], 0.6: [10, -70, 0], 1.0: [20, -140, 0], 1.4: [10, -120, 0], 1.8: [25, -150, 0],
                      2.2: [10, -110, 0], 2.6: [25, -150, 0], 3.0: [0, -60, 0], 3.3: [-30, 0, 0], 4.2: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.8: [50, 0, 0], 1.0: [0, 0, 0], 1.6: [50, 0, 0], 1.8: [0, 0, 0], 2.4: [50, 0, 0],
                     2.6: [0, 0, 0], 3.3: [55, 0, 0], 4.2: [0, 0, 0]}))
    a.rot("body", kf({0: [0, 0, 0], 1.0: [0, 0, 12], 2.6: [0, 0, -12], 3.3: [-10, 0, 0], 4.2: [0, 0, 0]}))
    a.scl("torso", kf({0: [1, 1, 1], 1.8: [0.9, 0.85, 0.85], 2.6: [0.7, 0.6, 0.6], 3.2: [0.45, 0.35, 0.4]}))

    a = c.act("maw", 9.0, [8.4])
    a.rot("head", kf({0: [0, 0, 0], 1.2: [-28, 0, 0], 7.8: [-24, 0, 0], 8.4: [12, 0, 0], 9.0: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 1.2: [62, 0, 0], 8.2: [68, 0, 0], 8.4: [0, 0, 0], 9.0: [0, 0, 0]}))
    a.scl("head", kf({0: [1, 1, 1], 1.5: [1.25, 1.25, 1.25], 8.2: [1.45, 1.45, 1.45], 8.6: [1.1, 1.1, 1.1], 9.0: [1, 1, 1]}))
    a.rot("vortex", [0, "q.anim_time * 420", 0])
    a.scl("vortex", kf({0: [1, 1, 1], 1.5: [1.4, 1.2, 1.4], 8.2: [1.6, 1.3, 1.6], 9.0: [1, 1, 1]}))

    a = c.act("ram", 1.3, [0.55])
    a.rot("head", kf({0: [0, 0, 0], 0.4: [-20, 0, 0], 0.55: [25, 0, 0], 1.0: [10, 0, 0], 1.3: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.4: [35, 0, 0], 0.55: [0, 0, 0]}))

    a = c.act("bites", 1.6, [0.35, 0.8, 1.25])
    a.rot("jaw", kf({0: [0, 0, 0], 0.22: [50, 0, 0], 0.35: [0, 0, 0], 0.67: [50, 0, 0], 0.8: [0, 0, 0],
                     1.12: [50, 0, 0], 1.25: [0, 0, 0], 1.6: [0, 0, 0]}))
    a.rot("head", kf({0: [0, 0, 0], 0.22: [-12, -12, 0], 0.35: [10, -8, 0], 0.67: [-12, 12, 0], 0.8: [10, 8, 0],
                      1.12: [-14, 0, 0], 1.25: [12, 0, 0], 1.6: [0, 0, 0]}))

    a = c.act("spiral", 3.0, [0.5])
    a.rot("head", kf({0: [0, 0, 0], 0.5: [-10, 0, 0], 2.6: [-10, 0, 0], 3.0: [0, 0, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.5: [35, 0, 0], 2.6: [35, 0, 0], 3.0: [0, 0, 0]}))
    a.rot("body", [0, "q.anim_time < 2.7 ? q.anim_time * 260.0 : 0", 0])

    a = c.act("death", 4.0, [3.6])
    a.rot("body", kf({0: [0, 0, 0], 0.8: [-15, 0, 0], 2.0: [10, 0, 25], 3.0: [20, 0, 80], 4.0: [22, 0, 88]}))
    a.pos("body", kf({0: [0, 0, 0], 2.0: [0, -4, 0], 3.0: [0, -16, 0], 4.0: [0, -18, 0]}))
    a.rot("jaw", kf({0: [0, 0, 0], 0.8: [55, 0, 0], 2.5: [40, 0, 0], 4.0: [30, 0, 0]}))
    a.rot("neck", kf({0: [0, 0, 0], 0.8: [-35, 0, 0], 2.5: [10, 0, 0], 4.0: [25, 0, 0]}))
    a.scl("vortex", kf({0: [1, 1, 1], 3.0: [0.2, 0.2, 0.2], 3.6: [0.01, 0.01, 0.01]}))

    c.overlay = None
    return c
