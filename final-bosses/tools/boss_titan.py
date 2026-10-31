"""Boss 02 - The Titan of Creation: a walking world-forge.

Silhouette: a 6.5-block colossus built like a temple-foundry. Fluted marble column shins on
sandstone plinths, a brick-and-bronze chest with a colonnade and a blazing forge window behind a
turning gear, domed observatory head with an aperture lens and an astrolabe, tower pauldrons,
three smoking chimneys, a gear halo, a forge hammer for one hand and an architect's caliper claw
for the other - plus glowing blueprint solids orbiting it. Nothing about it is a rock golem:
everything is *built*.
"""
import math

import materials as M
from modelkit import Model
from shapes import bevel, frame_cube, gear, orb, ring, spike, strut


def build() -> Model:
    m = Model("geometry.fb.titan", seed=202, density=2)
    brz, brass, sand, marb, iron = M.bronze(), M.brass_gear(), M.sandstone_bricks(), M.marble(), M.iron_plate()
    forge, blue = M.forge_glow(), M.blueprint()
    lens = M.radial_glow("ffffff", "1f8fff")
    bglow = M.glowgrad("cfefff", "1f6fff")

    m.bone("root", (0, 0, 0))
    hips = m.bone("hips", (0, 40, 0), "root")
    bevel(hips, (-12, 36, -7), (24, 10, 14), brz, b=0.8)
    gear(hips, (0, 41, -7.7), 4.4, 10, brass, plane="xy", width=1.2)
    hips.add((-6, 22, -8.2), (12, 14.2, 1.5), marb)
    hips.add((-5, 23, -8.45), (10, 12, 0.2), blue, glow=True, faces=("north",))
    hips.add((-6, 24, 6.0), (12, 13, 1.5), brz)
    for sx in (-1, 1):
        hips.add(((12 if sx > 0 else -13.5), 27, -5), (1.5, 11.2, 10), brz)

    # ---- legs: sandstone thighs, gear knees, fluted marble column shins, plinth feet
    for side, sx in (("r", -1), ("l", 1)):
        def X(o, w):
            return o if sx < 0 else -(o + w)
        leg = m.bone(f"leg_{side}", (8 * sx, 37, 0), "hips")
        bevel(leg, (X(-13, 10), 22, -5), (10, 16, 10), sand, b=0.8)
        leg.add((X(-13.4, 10.8), 30, -5.4), (10.8, 2, 10.8), brz)
        shin = m.bone(f"shin_{side}", (8 * sx, 23, 0), f"leg_{side}")
        gear(shin, (13.6 * sx, 23, 0), 3.2, 8, brass, plane="yz", width=1.0)
        orb(shin, (8 * sx, 23, -5.0), 2.6, brz)
        shin.add((X(-12, 8), 6, -4), (8, 17, 8), marb)
        shin.add((X(-12.8, 9.6), 21, -4.8), (9.6, 2, 9.6), marb)
        shin.add((X(-12.8, 9.6), 4, -4.8), (9.6, 2, 9.6), marb)
        foot = m.bone(f"foot_{side}", (8 * sx, 4, 0), f"shin_{side}")
        bevel(foot, (X(-14, 12), 0, -9), (12, 4.2, 15), sand, b=0.6)
        for k in range(3):
            foot.add((X(-14 + k * 4.2, 3.6), 0, -11.2), (3.6, 3.0, 3.0), brz)

    # ---- torso: foundry-temple
    torso = m.bone("torso", (0, 46, 0), "hips")
    bevel(torso, (-11, 45, -7.5), (22, 6, 15), iron, b=0.6)
    bevel(torso, (-17, 50, -11), (34, 24, 21), sand, b=1.0)
    torso.add((-8, 53, -11.6), (16, 15, 0.8), iron)
    torso.add((-6.5, 54.5, -11.75), (13, 12, 0.1), forge, glow=True, faces=("north",))
    cg = m.bone("core_gear", (0, 60.5, -12.6), "torso")
    gear(cg, (0, 60.5, -12.6), 6.0, 12, brass, plane="xy", width=1.2)
    for x in (-14.5, -10.5, 10.5, 14.5):
        torso.add((x - 1.3, 51, -13.2), (2.6, 20, 2.6), marb)
        torso.add((x - 1.7, 50.4, -13.6), (3.4, 1.2, 3.4), marb)
    torso.add((-17.5, 71, -14), (35, 3, 4.4), marb)
    torso.add((-16, 71.6, -14.25), (32, 1.8, 0.2), blue, glow=True, faces=("north",))
    for sx in (-1, 1):
        o = (17 if sx > 0 else -29)
        bevel(torso, (o, 62, -9), (12, 12, 18), brz, b=0.8)
        torso.add((o + 1, 74, -8), (10, 2.5, 16), brz)
        torso.add((o + 2.5, 76.5, -6), (7, 2, 12), brz)
        spike(torso, (23 * sx, 78.5, 0), (23 * sx, 87, 0), 2.2, brass)
        for k in range(3):
            torso.add(((29.02 if sx > 0 else -29.12), 65, -6 + k * 4), (0.1, 4.5, 1.4), forge, glow=True,
                      faces=("west",) if sx > 0 else ("east",))
    for x in (-9, 0, 9):
        bevel(torso, (x - 2, 66, 10), (4, 22, 4), sand, b=0.4)
        torso.add((x - 2.3, 74, 9.7), (4.6, 1.4, 4.6), brz)
        torso.add((x - 2.6, 88, 9.4), (5.2, 1.5, 5.2), iron)
        torso.add((x - 1.2, 89.55, 10.8), (2.4, 0.05, 2.4), forge, glow=True, faces=("up",))
    strut(torso, (0, 72, 10.5), (0, 79, 13.4), 3.0, brz)
    halo = m.bone("gear_halo", (0, 84, 14), "torso")
    gear(halo, (0, 84, 14), 15, 18, brass, plane="xy", width=1.6, spokes=6)

    # ---- head: domed observatory with an aperture lens and an astrolabe
    head = m.bone("head", (0, 79, -1), "torso")
    head.add((-4, 73, -4), (8, 8.5, 8), iron)
    bevel(head, (-7.5, 81, -7.5), (15, 8, 15), marb, b=0.8)
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        head.add((7.6 * math.cos(a) - 0.8, 81.3, 7.6 * math.sin(a) - 0.8), (1.6, 7.4, 1.6), marb)
    head.add((-6.5, 89, -6.5), (13, 2.5, 13), brz)
    head.add((-5, 91.5, -5), (10, 2.2, 10), brz)
    head.add((-3.2, 93.7, -3.2), (6.4, 1.8, 6.4), brz)
    head.add((-1.2, 95.5, -1.2), (2.4, 3, 2.4), brass)
    spike(head, (0, 98.5, 0), (0, 103, 0), 1.6, brass, steps=2)
    orb(head, (0, 85, -8.2), 3.1, brass)
    orb(head, (0, 85, -9.6), 1.9, lens, glow=True)
    ring(head, (0, 85, -10.9), 2.4, 8, iron, thickness=0.9, width=0.5, plane="xy", jag=[1, 1.6])
    astro = m.bone("astrolabe", (0, 87, 0), "head", floating=True)
    ring(astro, (0, 87, 0), 11.5, 24, brass, thickness=0.8, width=0.8, plane="xz")
    ring(astro, (0, 87, 0), 10.4, 22, brass, thickness=0.7, width=0.7, plane="yz")
    for p in ((11.5, 87, 0), (-8.1, 87, 8.1), (0, 97.4, 0), (0, 79.6, -7.4)):
        orb(astro, p, 1.1, bglow, glow=True)

    # ---- arms
    for side, sx in (("r", -1), ("l", 1)):
        def X(o, w):
            return o if sx < 0 else -(o + w)
        arm = m.bone(f"arm_{side}", (23 * sx, 68, 0), "torso", rotation=(0, 0, -6 * sx))
        orb(arm, (23 * sx, 67, 0), 4.0, iron)
        bevel(arm, (X(-27, 8), 50, -4.5), (8, 17, 9), brz, b=0.7)
        strut(arm, (28.6 * sx, 64, 3.2), (28.6 * sx, 52, 3.2), 1.4, iron)
        arm.add((X(-29.4, 1.6), 52, 2.4), (1.6, 6, 1.6), M.solid("c9ccd6", 0.03))
        fore = m.bone(f"forearm_{side}", (23 * sx, 50, 0), f"arm_{side}", rotation=(-10, 0, 0))
        gear(fore, (27.8 * sx, 50, 0), 3.6, 8, brass, plane="yz", width=1.0)
        bevel(fore, (X(-27.5, 9), 31, -5), (9, 19, 10), brz, b=0.8)
        for k in range(3):
            fore.add(((-27.6 if sx < 0 else 27.5), 34 + k * 4.5, -2.5), (0.1, 2.2, 5),
                     forge, glow=True, faces=("east",) if sx < 0 else ("west",))
        hand = m.bone(f"hand_{side}", (23 * sx, 31, 0), f"forearm_{side}")
        if side == "r":
            bevel(hand, (-27, 24, -4.5), (8, 7.2, 9), iron, b=0.7)
            strut(hand, (-23, 25, -1), (-23, 13, -1), 2.4, M.dark_iron())
            bevel(hand, (-31, 2, -7), (16, 11.2, 12), iron, b=1.0)
            for y in (4.2, 9.6):
                hand.add((-31.4, y, -7.4), (16.8, 1.4, 12.8), brz)
            hand.add((-31.12, 3.6, -5), (0.1, 8, 8), blue, glow=True, faces=("east",))
            hand.add((-15.0, 3.6, -5), (0.1, 8, 8), blue, glow=True, faces=("west",))
            hand.add((-30, 13.2, -6), (14, 1.2, 10), brz)
        else:
            bevel(hand, (19, 25, -4.5), (8, 6.2, 9), iron, b=0.7)
            for k, (fx, fz) in enumerate(((20.5, -3.5), (25.5, -3.5), (23, 3.2))):
                fa = m.bone(f"claw_{k}_a", (fx, 25.5, fz), "hand_l")
                strut(fa, (fx, 25.5, fz), (fx + (fx - 23) * 0.25, 17, fz + fz * 0.25), 1.6, brz)
                orb(fa, (fx + (fx - 23) * 0.25, 17, fz + fz * 0.25), 1.2, brass)
                fb = m.bone(f"claw_{k}_b", (fx + (fx - 23) * 0.25, 17, fz + fz * 0.25), f"claw_{k}_a")
                spike(fb, (fx + (fx - 23) * 0.25, 17, fz + fz * 0.25), (fx + (fx - 23) * 0.1, 9.5, fz + fz * 0.05), 1.3, brass, steps=3)
            holo = m.bone("holo", (23, 12, 0), "hand_l", floating=True)
            ring(holo, (23, 9, 0), 5.5, 18, bglow, thickness=0.3, width=0.3, plane="xz", glow=True)
            frame_cube(holo, (23, 13, 0), 4.2, 0.35, bglow, glow=True)

    # ---- orbiting blueprint solids (what it is creating)
    solids = m.bone("solids", (0, 60, 0), "root", floating=True)
    for k, (r, y) in enumerate(((32, 72), (34, 58), (31, 86))):
        a = 2 * math.pi * k / 3 + 0.4
        c = (r * math.cos(a), y, r * math.sin(a))
        frame_cube(solids, c, 5 + k, 0.4, bglow, glow=True)
        orb(solids, c, 1.2, lens, glow=True)
    return m
