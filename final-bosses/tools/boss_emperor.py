"""Boss 01 - The Void Emperor: a living throne whose emperor is absent.

Silhouette: tall gothic throne on four clawed cabriole legs, crown of spires and void orbs,
a vast ring of black shards behind it, two giant gauntlets floating free at its sides and a
crowned porcelain mask hovering over the empty seat. The seat is a hole of nothingness that
still remembers the outline of the one who sat there.
"""
import math

import materials as M
from modelkit import Model
from shapes import bevel, chain_links, mx, orb, ring, spike, strut


def build() -> Model:
    m = Model("geometry.fb.void_emperor", seed=101, density=2)
    obs, gold, velv, cape, iron = M.obsidian(), M.royal_gold(), M.velvet(), M.royal_cape(), M.dark_iron()
    vglow = M.glowgrad("f1dcff", "8a2be2")
    vcore = M.radial_glow("ffffff", "7a1fd1")

    m.bone("root", (0, 0, 0))
    t = m.bone("throne", (0, 20, 0), "root")

    # ---- seat and pedestal
    bevel(t, (-16, 16, -14), (32, 8, 28), obs, b=1.0)
    bevel(t, (-14, 9, -12), (28, 7.2, 24), obs, b=0.8)
    t.add((-14.4, 14.2, -12.4), (28.8, 1.6, 24.8), gold)
    for o, s in (((-16.4, 22.4, -14.4), (32.8, 1.8, 1.4)), ((-16.4, 22.4, 13.0), (32.8, 1.8, 1.4)),
                 ((-16.4, 22.4, -13.0), (1.4, 1.8, 26.0)), ((15.0, 22.4, -13.0), (1.4, 1.8, 26.0))):
        t.add(o, s, gold)
    t.add((-14.5, 24, -12.5), (29, 2.2, 21), velv, face_mats={"up": M.void_surface()})
    t.add((-15, 12, -14.8), (30, 4.2, 1.0), gold)
    for x in (-10, 0, 10):
        orb(t, (x, 13.2, -15.2), 1.1, gold)

    # ---- backrest
    bevel(t, (-15, 24, 8), (30, 42, 6), obs, b=1.0)
    t.add((-11, 29, 7.4), (22, 33, 0.8), velv)
    t.add((-8, 31, 7.15), (16, 28, 0.15), M.solid("000000", 0), glow=True, faces=("north",),
          decals={"north": M.silhouette_outline()})
    for sx in (-1, 1):
        x0 = -17.5 if sx < 0 else 14.0
        t.add((x0, 24, 6.8), (3.5, 42, 8.4), gold)
        t.add((x0 - 0.7, 66, 6.2), (4.9, 2.5, 9.6), gold)
        t.add((x0 - 0.7, 24.3, 6.2), (4.9, 2.0, 9.6), gold)
    ring(t, (0, 66, 11), 12.6, 9, gold, thickness=2.0, width=3.0, plane="xy", arc=(0, 180))

    # ---- crown of spires
    strut(t, (0, 66, 11), (0, 86, 11), 3.5, obs)
    spike(t, (0, 86, 11), (0, 93, 11), 2.6, gold)
    for sx in (-1, 1):
        strut(t, (8 * sx, 66, 11), (9 * sx, 80, 11), 2.8, obs)
        spike(t, (9 * sx, 80, 11), (9.6 * sx, 86, 11), 2.0, gold)
        strut(t, (15.75 * sx, 68.5, 11), (16.5 * sx, 76, 11), 2.2, obs)
        spike(t, (16.5 * sx, 76, 11), (17 * sx, 80.5, 11), 1.6, gold)
    orbs = m.bone("crown_orbs", (0, 90, 11), "throne", floating=True)
    for (x, y) in ((0, 96.5), (-9.8, 89), (9.8, 89)):
        orb(orbs, (x, y, 11), 1.9, obs)
        orb(orbs, (x, y, 11), 1.15, vcore, glow=True)

    # ---- armrests
    for sx in (-1, 1):
        def P(x, y, z):
            return (x * sx, y, z)
        x0 = -17 if sx < 0 else 13
        bevel(t, (x0, 24, -12), (4, 8, 20.5), obs, b=0.6)
        t.add((x0 - 0.3, 32, -12.3), (4.6, 1.2, 21.1), gold)
        orb(t, P(15, 30, -13.2), 2.8, gold)
        orb(t, P(15, 30, -15.4), 1.2, vcore, glow=True)
        strut(t, P(15, 17.5, -13.5), P(15, 24.5, -12.5), 2.0, gold)
        chain_links(t, P(15, 27.6, -13.2), 6, 2.0, iron)

    # ---- four clawed cabriole legs
    for name, sx, sz in (("leg_fr", -1, -1), ("leg_fl", 1, -1), ("leg_br", -1, 1), ("leg_bl", 1, 1)):
        leg = m.bone(name, (12 * sx, 13, 10 * sz), "throne")
        strut(leg, (12 * sx, 14, 10 * sz), (17 * sx, 5, 14.5 * sz), 4.0, obs)
        orb(leg, (14.6 * sx, 9.4, 12.4 * sz), 2.3, gold)
        strut(leg, (17 * sx, 5.4, 14.5 * sz), (17.5 * sx, 1.6, 15.5 * sz), 3.2, gold)
        out = math.atan2(sz, sx)
        for da in (-0.75, 0.0, 0.75):
            a = out + da
            spike(leg, (17.5 * sx, 2.2, 15.5 * sz), (17.5 * sx + math.cos(a) * 3.6, 0.05, 15.5 * sz + math.sin(a) * 3.6), 1.3, iron, steps=2)

    # ---- royal cape
    prev, top = "throne", 64
    for i in range(4):
        c = m.bone(f"cape{i}", (0, top, 14.2 + i * 0.1), prev)
        w = 26 + i
        c.add((-w / 2, top - 14, 14.1 + i * 0.1), (w, 14, 0.8), cape)
        prev, top = f"cape{i}", top - 14
    for sx in (-1, 1):
        orb(m.get("cape0"), (12 * sx, 63, 14.6), 1.2, gold)

    # ---- the floating gauntlets (the emperor's hands without an emperor)
    for side in ("r", "l"):
        sx = -1 if side == "r" else 1
        h = m.bone(f"hand_{side}", (34 * sx, 36, -4), "root", floating=True)

        def X(x):
            return x * sx

        ring(h, (X(34), 36, 2.2), 4.4, 12, gold, thickness=1.6, width=3.0, plane="xy")
        orb(h, (X(34), 36, 3.4), 3.0, vcore, glow=True)
        for k in range(3):
            strut(h, (X(34 + (k - 1) * 1.6), 36 + (k - 1) * 1.2, 4), (X(34 + (k - 1) * 2.4), 36 + (k - 1) * 2.0, 10 + k * 1.5), 0.9, vglow, glow=True)
        o = (-39, 32, -10) if sx < 0 else (29, 32, -10)
        bevel(h, o, (10, 7, 12.4), obs, b=0.8)
        h.add((o[0] + 0.5, 38.9, -9.4), (9, 0.8, 10.6), gold)
        h.add((o[0] + 2, 39.75, -7.6), (6, 0.05, 6), M.radial_glow("e9c8ff", "000000"), glow=True, faces=("up",))
        for k in range(4):
            fx = (-38.6 + k * 2.4) if sx < 0 else (28.4 + (3 - k) * 2.4)
            fa = m.bone(f"finger_{side}{k}_a", (fx + 1.1, 35, -10), f"hand_{side}", rotation=(12, 0, 0))
            fa.add((fx, 33.5, -16.2), (2.2, 3.0, 6.4), obs)
            fa.add((fx - 0.15, 33.3, -12.2), (2.5, 3.4, 1.0), gold)
            fb = m.bone(f"finger_{side}{k}_b", (fx + 1.1, 35, -16), f"finger_{side}{k}_a", rotation=(18, 0, 0))
            fb.add((fx + 0.15, 33.8, -21.4), (1.9, 2.6, 5.6), obs)
            spike(fb, (fx + 1.1, 35, -21.2), (fx + 1.1, 33.2, -25.5), 1.7, gold, steps=2)
        th = m.bone(f"thumb_{side}", (X(29.5), 34, -4), f"hand_{side}")
        strut(th, (X(29.5), 34.5, -3), (X(26.6), 33.4, -9.5), 2.5, obs)
        spike(th, (X(26.6), 33.4, -9.5), (X(25.4), 32.4, -12.4), 1.6, gold, steps=2)

    # ---- the mask where a face should be
    mk = m.bone("mask", (0, 50, -2), "root", floating=True)
    bevel(mk, (-6.5, 41, -3), (13, 17, 3), M.porcelain(gold_crack=True), b=0.8)
    mk.add((-5.5, 42, -3.3), (11, 15, 0.4), M.porcelain(gold_crack=True), decals={"north": M.emperor_mask()})
    for sx in (-1, 1):
        mk.add((2.2 * sx - 1.3, 50.4, -3.38), (2.6, 0.55, 0.05), M.solid("f3e1ff", 0), glow=True, faces=("north",),
               pivot=(2.2 * sx, 50.7, -3.36), rotation=(0, 0, 12 * sx))
    mk.add((-7, 57.6, -3.7), (14, 2.2, 4.6), gold)
    for x in (-6, -4, -2, 0, 2, 4, 6):
        spike(mk, (x, 59.6, -1.5), (x * 1.15, 67 - abs(x) * 0.8, -1.5 + abs(x) * 0.2), 1.6, gold, steps=2)
    orb(mk, (0, 58.7, -3.9), 1.0, vcore, glow=True)
    for sx in (-1, 1):
        for k in range(4):
            spike(mk, (6.0 * sx, 54 - k * 3.4, -1.0), ((10.5 + k * 0.6) * sx, 56 - k * 5.2, -0.4), 1.4, gold, steps=2)
    ring(mk, (0, 41.2, -1.5), 3.6, 12, vglow, thickness=0.4, width=0.4, plane="xz", glow=True)
    halo = m.bone("mask_halo", (0, 50, 1.6), "mask", floating=True)
    ring(halo, (0, 50, 1.6), 10, 14, obs, thickness=1.2, width=0.8, plane="xy", jag=[1, 2.6, 1.6, 3.2])
    ring(halo, (0, 50, 1.4), 8.4, 18, vglow, thickness=0.35, width=0.35, plane="xy", glow=True)

    # ---- the rift halo behind the throne
    rift = m.bone("rift", (0, 50, 24), "root", floating=True)
    ring(rift, (0, 50, 24), 30, 28, obs, thickness=1.5, width=1.0, plane="xy", jag=[1, 3, 1.5, 4.2, 2])
    ring(rift, (0, 50, 23.6), 28.2, 32, vglow, thickness=0.5, width=0.5, plane="xy", glow=True)
    return m
