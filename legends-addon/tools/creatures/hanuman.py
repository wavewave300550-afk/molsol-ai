"""
HANUMAN (หนุมาน) — "Son of the Wind".

A towering white monkey warrior in Thai Ramakien regalia: a gold diadem with
ear-flares (กรรเจียก), crystal fangs (เขี้ยวแก้ว), diamond-glinting fur (ขนเพชร),
pointed shoulder ornaments (อินทรธนู), a jewelled breast pendant (ทับทรวง),
crossed chains (สังวาล), red sampot with kanok-flame borders, and the trident
ตรีเพชร.  Phase II sets his tail ablaze (the burning of Lanka).  Phase III
reveals the divine form สี่หน้าแปดกร: four faces and eight arms bearing
discus, conch, sword, mace, bow and arrow.
"""
from __future__ import annotations

from .common import COMMON_PRE, Creature, chain, ellipsoid, kf, mpt, mrot, obox, wave
from mk.geo import Model
from mk.paint import (C, bake, by_face, cloth, crystal, d_band, d_center_gem, d_combine, d_pixels, d_teeth, fbm, flame,
                      fur, glowball, gold, h2, hx, kanok, mix, shade, solid)


def diamond_fur(base="f4f1e8", dark="b9bccb", light="ffffff", spark="bfe9ff"):
    fb = fur(base, dark, light, streak=1.1, var=0.07)
    sp = hx(spark)

    def p(f):
        col = fb(f)
        if h2(f.x + int(f.p[0] * 3), f.y + int(f.p[2] * 3), f.cube_index) > 0.965:
            return mix(col, sp, 0.85)
        return col
    return p


def build() -> Creature:
    m = Model("geometry.legends.hanuman", seed=303, density=2.0)
    m.bounds = (6.0, 6.5, 2.2)

    FUR = diamond_fur()
    FUR_SH = diamond_fur("e6e3dc", "a9acbb")
    FACE = solid("f7f4ee", 0.03)
    MUZZLE = solid("f1d9cf", 0.04)
    GOLD = gold("e8b52c", "8a560d", "fff0a8", sparkle=0.06)
    GOLD_D = gold("c99522", "6b400a", "f5d97a", sparkle=0.03)
    KANOK = kanok("e8b52c", "8e1b1b", "4a0b0b", period=5)
    SAMPOT = cloth("9b1c1c", "e8b52c", trim_rows=2)
    GREEN = solid("1d6b45", 0.06)
    RUBY = solid("c4182c", 0.05)
    CRYSTAL = crystal("bfefff", "ffffff", "7fb7d6", facet=2)
    STEEL = solid("d9dee6", 0.04)
    MOUTH = solid("6b0d12", 0.04, edge=0)
    TASSEL = solid("c41e2a", 0.06)
    EYE = glowball("fffbe0", "58d26a")
    FIRE = flame("fff8d0", "ffb531", "ff4b1a")
    WOOD = solid("6a4524", 0.08)

    root = m.bone("root", (0, 0, 0))
    waist = m.bone("waist", (0, 26, 0), "root")
    # pelvis, sampot, belt
    waist.add((-7.2, 22, -4.2), (14.4, 7, 8.4), SAMPOT)
    waist.add((-7.6, 27, -4.6), (15.2, 2.6, 9.2), GOLD, decals={"north": d_center_gem("c4182c", "ff8a96", 2)})
    waist.add((-2.5, 25.5, -5.4), (5, 4.5, 1), GOLD, decals={"north": d_center_gem("1d6b45", "6fe0a6", 2)})  # ปั้นเหน่ง
    waist.add((-3, 14, -5.2), (6, 12, 1), KANOK)                                          # front sash ชายไหว
    for s in (-1, 1):
        waist.add((s * 5 - 1.5, 15, -4.9), (3, 10, 1), SAMPOT, pivot=(s * 5, 25, -4.5), rotation=(0, 0, 6 * s))  # ชายแครง
    waist.add((-7, 19, 3.6), (14, 8, 1), SAMPOT)

    # flowing sashes (ชายผ้า) from the belt
    for s_ in (-1, 1):
        chain(m, "sash_r" if s_ < 0 else "sash_l", "waist", (s_ * 6, 27, -3), "-y", [5, 5, 5, 4],
              [(3, 0.6), (3, 0.6), (2.8, 0.6), (2.6, 0.6)], [(-8, 0, -10 * s_), (6, 0, 0), (8, 0, 0), (6, 0, 0)],
              [SAMPOT, KANOK, SAMPOT, KANOK])
    chest = m.bone("chest", (0, 29, 0), "waist")
    obox(chest, (-8, 29, -4.5), (16, 15, 9), FUR)
    for s_ in (-1, 1):
        ellipsoid(chest, (s_ * 3.8, 39, -3.8), (3.4, 2.6, 1.4), FUR_SH, layers=2)        # pectorals
    # kanok flame back ornament (กนกเปลว)
    for k, (x, hgt, rz) in enumerate(((0, 14, 0), (-4, 11, 14), (4, 11, -14), (-7.5, 8, 30), (7.5, 8, -30))):
        chest.add((x - 1.8, 38, 4.6), (3.6, hgt, 1), GOLD if k % 2 == 0 else KANOK, pivot=(x, 38, 5), rotation=(-12, 0, rz))
    chest.add((-6, 31, -4.9), (12, 6, 1), FUR_SH)                                         # abs
    # สังวาล crossed chains
    for s in (-1, 1):
        for k in range(6):
            chest.add((s * (5.5 - k * 1.8) - 0.7, 43 - k * 2.4, -5.0), (1.4, 1.4, 0.6), GOLD)
    chest.add((-2.5, 34.5, -5.6), (5, 6, 1.2), GOLD, decals={"north": d_center_gem("c4182c", "ff8a96", 2)})   # ทับทรวง
    chest.add((-1, 33, -5.9), (2, 2, 1), RUBY)
    chest.add((-8.5, 41.5, -5), (17, 3, 10), GOLD_D)                                     # collar กรองศอ
    chest.add((-7.5, 39.5, -5.4), (15, 2, 1), KANOK)
    # back ornament
    chest.add((-5, 34, 4.4), (10, 8, 1), KANOK)

    # ------------------------------------------------------------------ head
    head = m.bone("head", (0, 44, 0), "chest")
    head.loc("mouth", (0, 47, -7))
    head.add((-4.5, 44, -4.5), (9, 9, 9), FUR, inflate=0.3)
    mask_px = ["GGG..GGG",
               "GEKWWKEG",
               "WGGWWGGW",
               "WWWKKWWW",
               "WRRRRRRW",
               "WTRTTRTW",
               "WWRRRRWW"]
    pal = {"G": "e8b52c", "E": "7dff8f", "K": "141414", "W": "f7f4ee", "R": "9e1420", "T": "dff6ff"}
    face_dec = d_pixels(mask_px, pal, center=True)
    head.add((-4.4, 44.6, -5.4), (8.8, 7.6, 1), FACE, decals={"north": d_pixels(
        ["G......G", "........", "........", "R......R", ".R....R."], {"G": "e8b52c", "R": "c0392b"}, center=True)})
    # curling gold brows (คิ้ว) and gold eye rims
    for s in (-1, 1):
        head.add((s * 2.4 - 1.9, 50.6, -6.1), (3.8, 1.1, 1), GOLD, pivot=(s * 2.4, 51, -5.6), rotation=(0, 0, -14 * s))
        head.add((s * 4.3 - 0.6, 51.2, -6.0), (1.2, 1.6, 0.9), GOLD, pivot=(s * 4.3, 51.5, -5.6), rotation=(0, 0, -40 * s))
        head.add((s * 2.3 - 1.6, 47.8, -5.9), (3.2, 2.6, 0.5), GOLD)
    ge = m.bone("glow_eyes", (0, 49, -6.2), "head")
    for s in (-1, 1):
        ge.add((s * 2.3 - 1.1, 48.3, -6.25), (2.2, 1.6, 0.4), EYE)
    # rounded white muzzle with nostrils, open red mouth, teeth and crystal fangs (เขี้ยวแก้ว)
    head.add((-3.3, 45.2, -8.2), (6.6, 2.6, 3.2), FACE, decals={"north": d_pixels(["..K..K..", "........"],
                                                                                    {"K": "151515"}, center=True)})
    head.add((-3.6, 44.2, -8.0), (7.2, 1.2, 3.0), MOUTH, faces=("north", "east", "west", "down"))
    head.add((-3.4, 44.9, -8.25), (6.8, 0.5, 0.4), solid("eef4f8", 0.02), decals={"north": d_teeth("eef4f8", row="top", step=2)})
    jw = m.bone("jaw", (0, 44.5, -4), "head")
    jw.add((-3.2, 42.4, -7.8), (6.4, 1.8, 3.4), FACE, face_mats={"up": MOUTH})
    for s in (-1, 1):
        jw.add((s * 2.6 - 0.45, 43.6, -8.0), (0.9, 2.4, 0.9), CRYSTAL, pivot=(s * 2.6, 44, -7.6), rotation=(0, 0, 10 * s))
    head.add((-1.2, 47.4, -8.0), (2.4, 1.6, 2.6), FACE)                                    # nose bridge
    for s in (-1, 1):
        head.add((s * 5.3 - 0.7, 47, -1.5), (1.4, 3, 2.6), FUR_SH)                          # ears
    # diadem กระบังหน้า + crest + ear flares กรรเจียก
    head.add((-4.9, 52.2, -5), (9.8, 2, 10), GOLD, decals={"north": d_center_gem("1d6b45", "6fe0a6", 2)})
    head.add((-1, 54, -5.4), (2, 3.5, 1.4), GOLD, pivot=(0, 54, -4.8), rotation=(-10, 0, 0))
    head.add((-0.6, 57, -5.2), (1.2, 2, 1), RUBY)
    for s in (-1, 1):
        head.add((s * 5.6 - 0.6, 47, -2.5), (1.2, 7, 4.5), GOLD, pivot=(s * 5.6, 50, -0.5), rotation=(0, 0, 12 * s))
        head.add((s * 6.6 - 0.5, 53, -1.5), (1, 3.5, 2.5), GOLD_D, pivot=(s * 6.6, 53, -0.5), rotation=(0, 0, 30 * s))
    # phase III: three more faces (left, right, back) — painted Khon masks
    for name, rot in (("face_r", (0, -90, 0)), ("face_l", (0, 90, 0)), ("face_b", (0, 180, 0))):
        fb = m.bone(name, (0, 48.5, 0), "head", rot)
        fb.add((-3.6, 44.6, -5.7), (7.2, 7, 1), FACE, decals={"north": face_dec})
        fb.add((-1.6, 44.2, -6.6), (3.2, 2.2, 1.2), FACE, decals={"north": d_pixels(["K..K"], {"K": "151515"}, center=True)})
        fb.add((-3.8, 51.4, -5.9), (7.6, 1, 0.8), GOLD)

    # ------------------------------------------------------------------ main arms + อินทรธนู
    def arm(side, name, pivot, parent, length_up=11, scale=1.0, rot=None):
        s = -1 if side == "r" else 1
        px, py, pz = pivot
        up = m.bone(name, pivot, parent, rot)
        up.add((px - 2.6 + s * 0.6, py - length_up, pz - 2.6), (5.2, length_up + 1, 5.2), FUR, mirror=s > 0)
        up.add((px - 2.9 + s * 0.6, py - 5, pz - 2.9), (5.8, 1.6, 5.8), GOLD)            # พาหุรัด armlet
        lo = m.bone(name + "_lo", (px + s * 0.6, py - length_up, pz), name)
        lo.add((px - 2.4 + s * 0.6, py - length_up - 10, pz - 2.4), (4.8, 10.5, 4.8), FUR_SH, mirror=s > 0)
        lo.add((px - 2.7 + s * 0.6, py - length_up - 8.5, pz - 2.7), (5.4, 2.4, 5.4), GOLD)   # ทองกร bracelet
        hd = m.bone(name + "_hand", (px + s * 0.6, py - length_up - 10, pz), name + "_lo")
        hd.add((px - 2 + s * 0.6, py - length_up - 14, pz - 2), (4, 4.5, 4), MUZZLE)
        return hd

    hand_r = arm("r", "arm_r", (-9.5, 42, 0), "chest")
    hand_l = arm("l", "arm_l", (9.5, 42, 0), "chest")
    for s in (-1, 1):                                                                       # อินทรธนู
        chest.add((s * 10 - 3, 42, -3), (6, 3, 6), GOLD_D)
        chest.add((s * 12.5 - 1, 43, -1.5), (2, 7, 3), GOLD, pivot=(s * 12, 44, 0), rotation=(0, 0, -28 * s))
        chest.add((s * 14.2 - 0.7, 48, -1), (1.4, 4, 2), GOLD, pivot=(s * 14, 49, 0), rotation=(0, 0, -45 * s))

    # trident ตรีเพชร in the right hand (shaft along the forearm direction when the arm hangs)
    tri = m.bone("trident", (-8.9, 20, 0), "arm_r_hand")
    tri.loc("tip", (-8.9, 20, -30))
    tri.add((-9.6, 19.3, -18), (1.4, 1.4, 34), WOOD)
    tri.add((-10.2, 18.7, -20), (2.6, 2.6, 2.4), GOLD)
    tri.add((-10, 18.9, 14), (2.2, 2.2, 3), GOLD)
    tri.add((-9.4, 19.5, 16.5), (1, 1, 3), TASSEL)
    tri.add((-12.6, 19.2, -22.5), (7.4, 1.6, 2), GOLD)                                     # cross guard
    tri.add((-9.9, 19.1, -30), (2, 1.8, 8), CRYSTAL)                                       # centre blade
    gtri = m.bone("glow_trident", (-8.9, 20, -26), "trident")
    gtri.add((-9.5, 19.5, -31), (1.2, 0.8, 6), glowball("ffffff", "8fe8ff"))
    for s in (-1, 1):
        tri.add((-8.9 + s * 3.2 - 0.6, 19.4, -27), (1.2, 1.2, 5), CRYSTAL, pivot=(-8.9 + s * 3.2, 20, -22),
                rotation=(0, 10 * s, 0))
    tri.add((-10.1, 18.6, -21.8), (2.4, 2.8, 1.2), TASSEL)

    # ------------------------------------------------------------------ extra arms (phase III)
    weapons = {}
    for side, idx, py, pz, splay in (("r", 2, 38, 1.5, 32), ("l", 2, 38, 1.5, 32), ("r", 3, 34, 2.5, 52),
                                     ("l", 3, 34, 2.5, 52), ("r", 4, 40, 3.5, 70), ("l", 4, 40, 3.5, 70)):
        s = -1 if side == "r" else 1
        nm = f"xarm_{side}{idx}"
        hd = arm(side, nm, (s * 8.5, py, pz), "chest", length_up=9, rot=(0, 0, -splay * s))
        weapons[(side, idx)] = hd
    # weapons held by the extra hands
    def wbone(side, idx, name):
        s = -1 if side == "r" else 1
        h = weapons[(side, idx)]
        return m.bone(name, (h.pivot[0], h.pivot[1] - 3, h.pivot[2]), h.name)
    w = wbone("r", 2, "w_discus")                                                           # จักร
    wx, wy, wz = w.pivot
    w.add((wx - 0.5, wy - 4, wz - 4), (1, 8, 8), GOLD, decals={"east": d_center_gem("c4182c", "ff8a96", 2)})
    w.add((wx - 0.6, wy - 5, wz - 1), (1.2, 10, 2), CRYSTAL)
    w.add((wx - 0.6, wy - 1, wz - 5), (1.2, 2, 10), CRYSTAL)
    w = wbone("l", 2, "w_conch")                                                            # สังข์
    wx, wy, wz = w.pivot
    w.add((wx - 1.8, wy - 3, wz - 3), (3.6, 4, 5), solid("f6efe2", 0.05))
    w.add((wx - 1.2, wy - 2.4, wz - 5), (2.4, 2.8, 2.5), GOLD)
    w = wbone("r", 3, "w_sword")                                                            # พระขรรค์
    wx, wy, wz = w.pivot
    w.add((wx - 0.8, wy - 1, wz - 1), (1.6, 3, 2), GOLD)
    w.add((wx - 0.5, wy - 1, wz - 14), (1, 1.8, 13), STEEL)
    w.add((wx - 1.8, wy - 0.5, wz - 1.6), (3.6, 1, 1.2), GOLD)
    w = wbone("l", 3, "w_mace")                                                             # คทา
    wx, wy, wz = w.pivot
    w.add((wx - 0.6, wy - 0.6, wz - 10), (1.2, 1.2, 12), GOLD_D)
    w.add((wx - 2, wy - 2, wz - 14), (4, 4, 4.5), GOLD, decals={"north": d_center_gem("1d6b45", "6fe0a6", 2)})
    w = wbone("r", 4, "w_bow")                                                              # ธนู
    wx, wy, wz = w.pivot
    for k, (dy, rx) in enumerate(((7, 20), (3.5, 8), (0, 0), (-3.5, -8), (-7, -20))):
        w.add((wx - 0.5, wy + dy - 2, wz - 1.5 - abs(dy) * 0.25), (1, 4, 1), GOLD_D, pivot=(wx, wy + dy, wz), rotation=(rx, 0, 0))
    w.add((wx - 0.15, wy - 8, wz + 0.4), (0.3, 16, 0.3), solid("f0e6c8", 0.02))
    w = wbone("l", 4, "w_arrow")                                                            # ศร
    wx, wy, wz = w.pivot
    w.add((wx - 0.4, wy - 0.4, wz - 13), (0.8, 0.8, 15), WOOD)
    w.add((wx - 0.9, wy - 0.9, wz - 15), (1.8, 1.8, 2.4), CRYSTAL)
    w.add((wx - 1, wy - 0.2, wz + 1), (2, 0.4, 2.5), TASSEL)

    # ------------------------------------------------------------------ legs
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        th = m.bone(f"leg_{side}", (s * 4, 24, 0), "waist")
        th.add((s * 4 - 3.2, 13, -3.2), (6.4, 11, 6.4), SAMPOT, mirror=s > 0)               # สนับเพลา
        th.add((s * 4 - 3.4, 12.5, -3.4), (6.8, 2, 6.8), KANOK)
        sh = m.bone(f"leg_{side}1", (s * 4, 13, 0), th.name)
        sh.add((s * 4 - 2.6, 2, -2.6), (5.2, 11.5, 5.2), FUR_SH, mirror=s > 0)
        sh.add((s * 4 - 2.9, 2.5, -2.9), (5.8, 1.6, 5.8), GOLD)
        ft = m.bone(f"foot_{side}", (s * 4, 2.5, 0), sh.name)
        ft.add((s * 4 - 2.7, 0, -6.5), (5.4, 2.5, 8.5), MUZZLE)
        for k, dx in enumerate((-1.8, 0, 1.8)):
            ft.add((s * 4 + dx - 0.7, 0, -8.6), (1.4, 1.6, 2.4), MUZZLE)

    # ------------------------------------------------------------------ tail (burns in phase II)
    tl = chain(m, "tail", "waist", (0, 24, 4), "+z", [5, 5, 5, 5, 5, 4, 4, 4],
               [(3.2, 3.2), (3, 3), (2.8, 2.8), (2.6, 2.6), (2.4, 2.4), (2.2, 2.2), (2, 2), (1.8, 1.8)],
               [(30, 0, 0), (-25, 0, 0), (-25, 0, 0), (-20, 0, 0), (-15, 0, 0), (-10, 0, 0), (20, 0, 0), (30, 0, 0)],
               FUR)
    tip = m.get(tl[-1])
    tip.add((-1.6, 22.4, 39), (3.2, 3.2, 4), FUR_SH)
    for i in (3, 5, 7):
        b = m.get(tl[i])
        fb = m.bone(f"glow_fire{i}", b.pivot, b.name)
        x, y, z = b.pivot
        fb.add((x - 2.2, y + 0.4, z + 0.5), (4.4, 4.5, 3.5), FIRE)
        fb.add((x - 1.4, y + 4, z + 1), (2.8, 3, 2.5), FIRE)

    c = Creature("hanuman", m, scale=1.5, description="Hanuman, Son of the Wind")
    c.pre = COMMON_PRE + [
        "variable.divine = math.lerp(variable.divine ?? 0.0, variable.ph >= 3 ? 1.0 : 0.0, 0.05)",
        "variable.size = math.lerp(variable.size ?? 1.0, query.property('legends:var') == 1 ? 0.35 : (variable.ph >= 3 ? 1.45 : 1.0), 0.1)",
        "variable.walkw = variable.mv * variable.calm",
    ]
    for b in ("face_r", "face_l", "face_b") + \
            tuple(b.name for b in m.bones if b.name.startswith(("xarm_", "w_"))):
        c.visibility.append((b, "variable.ph >= 3"))
    for i in (3, 5, 7):
        c.visibility.append((f"glow_fire{i}", "variable.ph >= 2"))

    t = "q.life_time"
    base = c.loop("base")
    base.scl("root", "variable.size")
    for nm in [b.name for b in m.bones if b.name.startswith("xarm_") and b.name.count("_") == 1]:
        base.scl(nm, "variable.divine")

    idle = c.loop("idle", "variable.calm")
    idle.pos("chest", [0, wave(0.35, 110), 0])
    for side in ("r", "l"):
        for j in range(4):
            idle.rot(f"sash_{side}{j}", [wave(6 + j * 3, 90, -j * 40 + (0 if side == "r" else 70)), 0, wave(4 + j * 2, 70, -j * 35)])
    idle.rot("chest", [wave(1.5, 110), 0, 0])
    idle.rot("head", ["query.target_x_rotation * 0.7", "query.target_y_rotation * 0.7", 0])
    idle.rot("jaw", [f"math.max(0.0, {wave(8, 70)})", 0, 0])
    idle.rot("arm_r", [wave(3, 110), 0, f"{wave(2, 110)} + 8"])
    idle.rot("arm_r_lo", [-35, 0, 0])
    idle.rot("arm_l", [wave(-3, 110), 0, f"{wave(-2, 110)} - 8"])
    for i, tb in enumerate(tl):
        idle.rot(tb, [wave(5, 90, -i * 30), wave(9, 60, -i * 35), 0])
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        for idx in (2, 3, 4):
            idle.rot(f"xarm_{side}{idx}", [wave(6, 90, idx * 60 + (0 if s < 0 else 90)), 0, wave(5 * -s, 70, idx * 40)])
            idle.rot(f"xarm_{side}{idx}_lo", [f"{wave(10, 90, idx * 50)} - 40", 0, 0])

    walk = c.loop("walk", "variable.walkw")
    sw = "variable.dist * 32.0"
    walk.rot("leg_r", [f"math.cos({sw}) * 34", 0, 0])
    walk.rot("leg_l", [f"-math.cos({sw}) * 34", 0, 0])
    walk.rot("leg_r1", [f"math.max(0.0, math.sin({sw})) * 40", 0, 0])
    walk.rot("leg_l1", [f"math.max(0.0, -math.sin({sw})) * 40", 0, 0])
    walk.rot("arm_l", [f"math.cos({sw}) * 28", 0, 0])
    walk.rot("arm_r", [f"-math.cos({sw}) * 12", 0, 0])
    walk.pos("waist", [0, f"math.abs(math.sin({sw})) * 1.2", 0])
    walk.rot("chest", [8, f"math.cos({sw}) * 6", 0])

    # ---------------------------------------------------------------- acts
    def pose3(a, bone, frames):
        a.rot(bone, kf(frames))

    a = c.act("descend", 2.4, [0.35])
    a.pos("waist", kf({0: [0, 4, 0], 0.35: [0, -9, 0], 1.6: [0, -8, 0], 2.4: [0, 0, 0]}))
    pose3(a, "leg_r", {0: [-30, 0, 0], 0.35: [-75, 0, 10], 1.6: [-70, 0, 10], 2.4: [0, 0, 0]})
    pose3(a, "leg_r1", {0: [30, 0, 0], 0.35: [100, 0, 0], 1.6: [95, 0, 0], 2.4: [0, 0, 0]})
    pose3(a, "leg_l", {0: [-30, 0, 0], 0.35: [-20, 0, -15], 1.6: [-20, 0, -15], 2.4: [0, 0, 0]})
    pose3(a, "leg_l1", {0: [30, 0, 0], 0.35: [60, 0, 0], 1.6: [55, 0, 0], 2.4: [0, 0, 0]})
    pose3(a, "chest", {0: [-10, 0, 0], 0.35: [30, 0, 0], 1.6: [25, 0, 0], 2.4: [0, 0, 0]})
    pose3(a, "arm_l", {0: [-150, 0, 0], 0.35: [30, 0, -20], 1.6: [20, 0, -30], 2.4: [0, 0, 0]})
    pose3(a, "arm_r", {0: [-150, 0, 0], 0.35: [-80, 0, 30], 1.6: [-90, 0, 40], 2.4: [0, 0, 0]})
    pose3(a, "head", {0: [0, 0, 0], 1.6: [-20, 0, 0], 2.4: [0, 0, 0]})

    a = c.act("taunt", 2.2, [1.1])
    pose3(a, "arm_r", {0: [0, 0, 0], 0.5: [-100, 0, 20], 0.8: [-100, -60, 20], 1.1: [-100, 60, 20], 1.5: [-170, 0, 10], 2.2: [0, 0, 0]})
    pose3(a, "arm_r_lo", {0: [0, 0, 0], 0.5: [-20, 0, 0], 1.5: [0, 0, 0], 2.2: [0, 0, 0]})
    pose3(a, "arm_l", {0: [0, 0, 0], 0.5: [-60, 0, -40], 1.5: [-60, 0, -40], 2.2: [0, 0, 0]})
    pose3(a, "head", {0: [0, 0, 0], 1.3: [-25, 0, 0], 1.8: [-20, 0, 0], 2.2: [0, 0, 0]})
    pose3(a, "chest", {0: [0, 0, 0], 1.3: [-10, 0, 0], 2.2: [0, 0, 0]})

    a = c.act("combo", 2.1, [0.45, 1.0, 1.65])
    pose3(a, "arm_r", {0: [0, 0, 0], 0.3: [-20, 0, 30], 0.45: [-95, 0, 5], 0.7: [-90, 70, 20], 1.0: [-90, -60, 20],
                       1.35: [-175, 0, 0], 1.65: [-40, 0, 0], 2.1: [0, 0, 0]})
    pose3(a, "arm_l", {0: [0, 0, 0], 0.45: [-90, 0, -10], 1.0: [-30, 0, -40], 1.35: [-170, 0, 0], 1.65: [-50, 0, 0], 2.1: [0, 0, 0]})
    pose3(a, "chest", {0: [0, 0, 0], 0.3: [0, 25, 0], 0.45: [10, -20, 0], 0.7: [0, 30, 0], 1.0: [5, -40, 0],
                       1.35: [-20, 0, 0], 1.65: [30, 0, 0], 2.1: [0, 0, 0]})
    pose3(a, "leg_r", {0: [0, 0, 0], 0.45: [-35, 0, 0], 1.0: [-10, 0, 0], 1.65: [-45, 0, 0], 2.1: [0, 0, 0]})
    pose3(a, "leg_l", {0: [0, 0, 0], 0.45: [25, 0, 0], 1.0: [10, 0, 0], 1.65: [30, 0, 0], 2.1: [0, 0, 0]})
    a.pos("waist", kf({0: [0, 0, 0], 0.45: [0, -2, -3], 1.0: [0, -1, 0], 1.65: [0, -5, -4], 2.1: [0, 0, 0]}))

    a = c.act("jump", 0.5, [0.35])
    a.pos("waist", kf({0: [0, 0, 0], 0.3: [0, -6, 0], 0.4: [0, 2, 0], 0.5: [0, 0, 0]}))
    pose3(a, "leg_r", {0: [0, 0, 0], 0.3: [-60, 0, 0], 0.4: [20, 0, 0], 0.5: [-40, 0, 0]})
    pose3(a, "leg_l", {0: [0, 0, 0], 0.3: [-60, 0, 0], 0.4: [20, 0, 0], 0.5: [-40, 0, 0]})
    pose3(a, "leg_r1", {0: [0, 0, 0], 0.3: [90, 0, 0], 0.4: [0, 0, 0], 0.5: [80, 0, 0]})
    pose3(a, "leg_l1", {0: [0, 0, 0], 0.3: [90, 0, 0], 0.4: [0, 0, 0], 0.5: [80, 0, 0]})
    pose3(a, "arm_r", {0: [0, 0, 0], 0.3: [40, 0, 0], 0.4: [-170, 0, 10], 0.5: [-170, 0, 10]})
    pose3(a, "arm_l", {0: [0, 0, 0], 0.3: [40, 0, 0], 0.4: [-150, 0, -20], 0.5: [-150, 0, -20]})

    a = c.act("air", 1.0, [], loop=True)
    a.rot("leg_r", [-50, 0, 0])
    a.rot("leg_r1", [80, 0, 0])
    a.rot("leg_l", [-30, 0, 0])
    a.rot("leg_l1", [70, 0, 0])
    a.rot("arm_r", [-170, 0, 10])
    a.rot("arm_l", [-140, 0, -25])
    a.rot("chest", [-10, 0, 0])
    for i, tb in enumerate(tl):
        a.rot(tb, [wave(10, 300, -i * 40, t="q.anim_time"), 0, 0])

    a = c.act("slam", 1.0, [0.15])
    a.pos("waist", kf({0: [0, 0, 0], 0.15: [0, -10, -2], 0.6: [0, -9, -2], 1.0: [0, 0, 0]}))
    pose3(a, "arm_r", {0: [-170, 0, 10], 0.15: [-30, 0, 0], 0.6: [-25, 0, 0], 1.0: [0, 0, 0]})
    pose3(a, "arm_l", {0: [-140, 0, -25], 0.15: [-30, 0, -20], 0.6: [-25, 0, -20], 1.0: [0, 0, 0]})
    pose3(a, "chest", {0: [-10, 0, 0], 0.15: [40, 0, 0], 0.6: [35, 0, 0], 1.0: [0, 0, 0]})
    pose3(a, "leg_r", {0: [-50, 0, 0], 0.15: [-80, 0, 10], 0.6: [-75, 0, 10], 1.0: [0, 0, 0]})
    pose3(a, "leg_r1", {0: [80, 0, 0], 0.15: [100, 0, 0], 0.6: [95, 0, 0], 1.0: [0, 0, 0]})
    pose3(a, "leg_l", {0: [-30, 0, 0], 0.15: [10, 0, -10], 0.6: [10, 0, -10], 1.0: [0, 0, 0]})
    pose3(a, "leg_l1", {0: [70, 0, 0], 0.15: [80, 0, 0], 0.6: [75, 0, 0], 1.0: [0, 0, 0]})

    a = c.act("tail_whip", 1.6, [0.8])
    a.scl("tail0", kf({0: [1, 1, 1], 0.4: [1.4, 1.4, 1.4], 1.2: [1.4, 1.4, 1.4], 1.6: [1, 1, 1]}))
    a.rot("waist", kf({0: [0, 0, 0], 0.4: [0, 40, 0], 0.8: [0, -200, 0], 1.2: [0, -340, 0], 1.6: [0, -360, 0]}, smooth=False))
    for i, tb in enumerate(tl):
        a.rot(tb, kf({0: [0, 0, 0], 0.4: [-25, 0, 0], 0.8: [-30 if i == 0 else 4, 18, 0], 1.6: [0, 0, 0]}))


    a = c.act("dash", 0.7, [0.3])
    a.pos("waist", kf({0: [0, 0, 0], 0.2: [0, -3, 3], 0.3: [0, -2, -6], 0.7: [0, 0, 0]}))
    pose3(a, "chest", {0: [0, 0, 0], 0.2: [25, 0, 0], 0.3: [30, 0, 0], 0.7: [0, 0, 0]})
    pose3(a, "arm_r", {0: [0, 0, 0], 0.2: [-30, 0, 30], 0.3: [-95, 0, 0], 0.7: [0, 0, 0]})
    pose3(a, "arm_l", {0: [0, 0, 0], 0.3: [40, 0, -20], 0.7: [0, 0, 0]})

    a = c.act("guard", 2.6, [])
    pose3(a, "arm_r", {0: [0, 0, 0], 0.3: [-70, 50, 30], 2.3: [-70, 50, 30], 2.6: [0, 0, 0]})
    pose3(a, "arm_r_lo", {0: [0, 0, 0], 0.3: [-60, 0, 0], 2.3: [-60, 0, 0], 2.6: [0, 0, 0]})
    pose3(a, "arm_l", {0: [0, 0, 0], 0.3: [-80, -40, -20], 2.3: [-80, -40, -20], 2.6: [0, 0, 0]})
    pose3(a, "leg_r", {0: [0, 0, 0], 0.3: [-25, 0, 15], 2.3: [-25, 0, 15], 2.6: [0, 0, 0]})
    pose3(a, "leg_l", {0: [0, 0, 0], 0.3: [20, 0, -10], 2.3: [20, 0, -10], 2.6: [0, 0, 0]})
    a.pos("waist", kf({0: [0, 0, 0], 0.3: [0, -3, 0], 2.3: [0, -3, 0], 2.6: [0, 0, 0]}))

    a = c.act("counter", 0.8, [0.25])
    pose3(a, "arm_r", {0: [-70, 50, 30], 0.15: [-120, 0, 30], 0.25: [-90, -50, 0], 0.8: [0, 0, 0]})
    pose3(a, "chest", {0: [0, 0, 0], 0.15: [0, 40, 0], 0.25: [10, -50, 0], 0.8: [0, 0, 0]})
    a.pos("waist", kf({0: [0, -3, 0], 0.25: [0, -2, -8], 0.8: [0, 0, 0]}))

    a = c.act("ignite", 2.0, [1.2])
    for i, tb in enumerate(tl):
        a.rot(tb, kf({0: [0, 0, 0], 0.6: [-35 if i < 3 else -10, 0, 0], 1.6: [-30 if i < 3 else -8, 0, 0], 2.0: [0, 0, 0]}))
    pose3(a, "arm_l", {0: [0, 0, 0], 0.6: [-170, 0, -10], 1.2: [-110, 0, -10], 2.0: [0, 0, 0]})
    pose3(a, "head", {0: [0, 0, 0], 0.6: [-35, 0, 0], 1.6: [-30, 0, 0], 2.0: [0, 0, 0]})

    a = c.act("fire_spin", 1.6, [0.8])
    a.scl("tail0", kf({0: [1, 1, 1], 0.3: [1.35, 1.35, 1.35], 1.3: [1.35, 1.35, 1.35], 1.6: [1, 1, 1]}))
    a.rot("waist", kf({0: [0, 0, 0], 0.3: [0, 30, 0], 1.3: [0, -360, 0], 1.6: [0, -360, 0]}, smooth=False))
    a.pos("waist", kf({0: [0, 0, 0], 0.3: [0, -3, 0], 0.8: [0, 3, 0], 1.3: [0, -2, 0], 1.6: [0, 0, 0]}))
    for i, tb in enumerate(tl):
        a.rot(tb, kf({0: [0, 0, 0], 0.3: [-28, 0, 0], 1.3: [-28, 0, 0], 1.6: [0, 0, 0]}))


    a = c.act("shrunk", 1.0, [], loop=True)
    a.rot("chest", [30, 0, 0])
    a.rot("leg_r", [f"math.sin(q.anim_time * 1440) * 50", 0, 0])
    a.rot("leg_l", [f"-math.sin(q.anim_time * 1440) * 50", 0, 0])
    a.rot("arm_r", [-40, 0, 20])
    a.rot("arm_l", [f"-math.sin(q.anim_time * 1440) * 40", 0, 0])

    a = c.act("grow", 1.4, [1.05])
    pose3(a, "arm_r", {0: [0, 0, 0], 0.7: [-175, 0, 0], 1.05: [-30, 0, 0], 1.4: [0, 0, 0]})
    pose3(a, "arm_l", {0: [0, 0, 0], 0.7: [-175, 0, 0], 1.05: [-30, 0, 0], 1.4: [0, 0, 0]})
    pose3(a, "chest", {0: [0, 0, 0], 0.7: [-25, 0, 0], 1.05: [35, 0, 0], 1.4: [0, 0, 0]})
    a.scl("root", kf({0: [0.4, 0.4, 0.4], 0.7: [1.9, 1.9, 1.9], 1.05: [2.0, 2.0, 2.0], 1.4: [1, 1, 1]}))

    a = c.act("awaken", 4.2, [2.6])
    a.pos("waist", kf({0: [0, 0, 0], 1.0: [0, -4, 0], 2.6: [0, 10, 0], 3.6: [0, 8, 0], 4.2: [0, 0, 0]}))
    pose3(a, "chest", {0: [0, 0, 0], 1.0: [30, 0, 0], 2.6: [-25, 0, 0], 3.6: [-15, 0, 0], 4.2: [0, 0, 0]})
    pose3(a, "arm_r", {0: [0, 0, 0], 1.0: [10, 0, 10], 2.6: [-20, 0, 80], 3.6: [-20, 0, 70], 4.2: [0, 0, 0]})
    pose3(a, "arm_l", {0: [0, 0, 0], 1.0: [10, 0, -10], 2.6: [-20, 0, -80], 3.6: [-20, 0, -70], 4.2: [0, 0, 0]})
    pose3(a, "head", {0: [0, 0, 0], 1.0: [25, 0, 0], 2.6: [-30, 0, 0], 4.2: [0, 0, 0]})
    pose3(a, "leg_r", {0: [0, 0, 0], 1.0: [-40, 0, 0], 2.6: [0, 0, 8], 4.2: [0, 0, 0]})
    pose3(a, "leg_l", {0: [0, 0, 0], 1.0: [-40, 0, 0], 2.6: [0, 0, -8], 4.2: [0, 0, 0]})

    a = c.act("yawn", 10.0, [1.6, 5.2, 8.6])
    a.pos("waist", kf({0: [0, 0, 0], 1.2: [0, 8, 0], 9.2: [0, 8, 0], 10.0: [0, 0, 0]}))
    pose3(a, "head", {0: [0, 0, 0], 1.2: [-45, 0, 0], 4.8: [-40, 0, 0], 5.2: [-20, 0, 0], 8.2: [-30, 0, 0], 8.6: [10, 0, 0], 10.0: [0, 0, 0]})
    pose3(a, "chest", {0: [0, 0, 0], 1.2: [-20, 0, 0], 8.2: [-20, 0, 0], 8.6: [15, 0, 0], 10.0: [0, 0, 0]})
    pose3(a, "arm_r", {0: [0, 0, 0], 1.2: [-30, 0, 85], 8.2: [-40, 0, 85], 8.6: [-90, 0, 10], 10.0: [0, 0, 0]})
    pose3(a, "arm_l", {0: [0, 0, 0], 1.2: [-30, 0, -85], 8.2: [-40, 0, -85], 8.6: [-90, 0, -10], 10.0: [0, 0, 0]})
    a.scl("head", kf({0: [1, 1, 1], 1.2: [1.15, 1.15, 1.15], 8.2: [1.15, 1.15, 1.15], 10.0: [1, 1, 1]}))
    for side in ("r", "l"):
        s = -1 if side == "r" else 1
        for idx in (2, 3, 4):
            pose3(a, f"xarm_{side}{idx}", {0: [0, 0, 0], 1.2: [-20 - idx * 25, 0, 40 * -s], 8.2: [-20 - idx * 25, 0, 40 * -s], 10.0: [0, 0, 0]})

    a = c.act("barrage", 2.5, [0.5, 0.8, 1.1, 1.4, 1.7, 2.0])
    for k, (side, idx) in enumerate((("r", 2), ("l", 2), ("r", 3), ("l", 3), ("r", 4), ("l", 4))):
        t0 = 0.5 + k * 0.3
        s = -1 if side == "r" else 1
        pose3(a, f"xarm_{side}{idx}", {0: [0, 0, 0], t0 - 0.2: [-150, 0, 30 * -s], t0: [-60, 20 * s, 0], t0 + 0.3: [-20, 0, 0], 2.5: [0, 0, 0]})
    pose3(a, "chest", {0: [0, 0, 0], 0.5: [10, 20, 0], 0.8: [10, -20, 0], 1.1: [10, 20, 0], 1.4: [10, -20, 0], 1.7: [10, 20, 0], 2.0: [10, -20, 0], 2.5: [0, 0, 0]})

    a = c.act("discus", 1.2, [0.6])
    pose3(a, "xarm_r2", {0: [0, 0, 0], 0.4: [-60, 0, 70], 0.6: [-90, -80, 10], 1.2: [0, 0, 0]})
    pose3(a, "chest", {0: [0, 0, 0], 0.4: [0, 35, 0], 0.6: [0, -30, 0], 1.2: [0, 0, 0]})

    a = c.act("mountain", 2.6, [2.0])
    pose3(a, "arm_r", {0: [0, 0, 0], 0.8: [-175, 0, 15], 1.7: [-180, 0, 10], 2.0: [-60, 0, 0], 2.6: [0, 0, 0]})
    pose3(a, "arm_l", {0: [0, 0, 0], 0.8: [-175, 0, -15], 1.7: [-180, 0, -10], 2.0: [-60, 0, 0], 2.6: [0, 0, 0]})
    pose3(a, "chest", {0: [0, 0, 0], 0.8: [-15, 0, 0], 1.7: [-25, 0, 0], 2.0: [30, 0, 0], 2.6: [0, 0, 0]})
    a.pos("waist", kf({0: [0, 0, 0], 0.8: [0, -3, 0], 1.7: [0, -1, 0], 2.0: [0, -4, -3], 2.6: [0, 0, 0]}))

    a = c.act("collapse", 1.5, [])
    a.pos("waist", kf({0: [0, 0, 0], 0.6: [0, -12, 0], 1.5: [0, -20, 0]}))
    a.rot("waist", kf({0: [0, 0, 0], 0.6: [20, 0, 0], 1.5: [85, 0, 0]}))
    pose3(a, "leg_r", {0: [0, 0, 0], 0.6: [-80, 0, 0], 1.5: [-90, 0, 0]})
    pose3(a, "leg_l", {0: [0, 0, 0], 0.6: [-70, 0, 0], 1.5: [-90, 0, 0]})

    a = c.act("revive", 2.6, [2.0])
    a.pos("waist", kf({0: [0, -20, 0], 1.2: [0, -10, 0], 2.0: [0, 6, 0], 2.6: [0, 0, 0]}))
    a.rot("waist", kf({0: [85, 0, 0], 1.2: [20, 0, 0], 2.0: [-10, 0, 0], 2.6: [0, 0, 0]}))
    pose3(a, "arm_r", {0: [0, 0, 0], 2.0: [-30, 0, 70], 2.6: [0, 0, 0]})
    pose3(a, "arm_l", {0: [0, 0, 0], 2.0: [-30, 0, -70], 2.6: [0, 0, 0]})
    pose3(a, "head", {0: [0, 0, 0], 2.0: [-35, 0, 0], 2.6: [0, 0, 0]})

    a = c.act("death", 4.0, [3.4])
    a.pos("waist", kf({0: [0, 0, 0], 1.0: [0, -8, 0], 2.6: [0, -14, 0], 4.0: [0, -20, 0]}))
    a.rot("waist", kf({0: [0, 0, 0], 1.0: [15, 0, 0], 2.6: [40, 0, 0], 4.0: [85, 0, 0]}))
    pose3(a, "leg_r", {0: [0, 0, 0], 1.0: [-80, 0, 0], 4.0: [-90, 0, 0]})
    pose3(a, "leg_l", {0: [0, 0, 0], 1.0: [-75, 0, 0], 4.0: [-90, 0, 0]})
    pose3(a, "head", {0: [0, 0, 0], 1.0: [-30, 0, 0], 4.0: [20, 0, 0]})
    pose3(a, "arm_r", {0: [0, 0, 0], 1.0: [-40, 0, 30], 4.0: [-10, 0, 40]})
    return c
