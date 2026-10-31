"""Boss 03 - The Devouring Star: a skeletal abyssal leviathan with a sun for a heart.

Silhouette: an 8-block flying predator. Charred skull crowned by a corona of spikes, rows of
amber eyes, three nested mouths (outer fangs, side mandibles, an inner jaw with a tiny burning
throat-star), an angler lure carrying a miniature sun, an open ribcage caging a living star,
solar-flare wings and dorsal flames, and a vertebral tail that ends in a comet tail.
"""
import math

import materials as M
from modelkit import Model
from shapes import bevel, orb, ring, spike, strut


def build() -> Model:
    m = Model("geometry.fb.devouring_star", seed=303, density=2)
    bn, ch, fl, th = M.bone(), M.charred_bone(), M.abyss_flesh(), M.tooth()
    core, cor = M.star_core(), M.corona()
    flame = M.glowgrad("fff1b0", "ff3d12")
    amber = M.radial_glow("fff6b0", "ff8a00")

    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 32, 0), "root")

    # ---- spine, dorsal spines and dorsal flames
    for k in range(8):
        z = -12 + k * 5
        bevel(body, (-2.5, 36.5, z), (5, 5, 4), bn, b=0.5)
        body.add((-1.8, 37.3, z + 3.8), (3.6, 3.4, 1.4), ch)
        spike(body, (0, 41.4, z + 2), (0, 48 - abs(k - 3.5) * 0.8, z + 4.5), 1.8, bn, steps=3, tip_mat=ch)
        body.add((-0.3, 41.6, z + 0.6), (0.6, 5.5 - abs(k - 3.5) * 0.5, 3.6), flame, glow=True)

    # ---- ribcage around the living star
    for k, z in enumerate((-8, -2, 4, 10, 16)):
        s = 1 - abs(k - 2) * 0.12
        for sx in (-1, 1):
            p0, p1 = (2.5 * sx, 37, z), (11 * s * sx, 33, z + 1)
            p2, p3 = (12.5 * s * sx, 24, z + 2), (7 * s * sx, 17, z + 2.5)
            strut(body, p0, p1, 1.8, bn)
            strut(body, p1, p2, 1.8, bn)
            strut(body, p2, p3, 1.7, bn)
            strut(body, p3, (0, 16.6, z + 2.5), 1.6, bn)
            orb(body, p1, 1.2, ch)
            orb(body, p2, 1.2, ch)
    strut(body, (0, 16.4, -6), (0, 16.4, 19), 2.2, bn)
    orb(body, (0, 27.5, 4), 6.2, core, glow=True)
    orb(body, (0, 27.5, 4), 8.0, cor, glow=True, k=0.62)
    for x, z in ((-5, -2), (5, 6), (-3, 12), (4, -6)):
        strut(body, (x, 16.4, z), (x * 1.3, 3, z + 6), 0.5, flame, glow=True)

    # ---- solar-flare wings (bone fingers + flame membranes)
    for side, sx in (("r", -1), ("l", 1)):
        prev = "body"
        for k, depth in enumerate((17, 13, 9)):
            x0 = 12 + 10 * k
            b = m.bone(f"fin_{side}{k}", (x0 * sx, 31, -4), prev, rotation=(0, 0, 6 * sx) if k == 0 else None)
            xa, xb = x0 * sx, (x0 + 10) * sx
            strut(b, (xa, 31, -5.5), (xb, 31 + (2 if k < 2 else 4), -5.5 + 2 * k), 1.5, bn)
            ox = x0 if sx > 0 else -(x0 + 10)
            b.add((ox, 30.6, -5 + 2 * k), (10, 0.4, depth), flame, glow=True)
            strut(b, (xa, 30.8, -5), ((x0 + 9) * sx, 30.8, -5 + depth + 2 * k), 0.8, ch)
            prev = f"fin_{side}{k}"

    # ---- head: tapered skull, burning corona, eyes, three mouths, lure
    head = m.bone("head", (0, 34, -12), "body")
    bevel(head, (-9, 30, -22.5), (18, 13, 11), ch, b=1.2)
    bevel(head, (-7.5, 29, -29.5), (15, 11.5, 8), bn, b=1.0)
    bevel(head, (-5.5, 28.5, -35.5), (11, 7.5, 6.8), bn, b=0.9)
    bevel(head, (-6, 42.4, -24), (12, 2.6, 12), ch, b=0.5)
    for sx in (-1, 1):
        head.add((4.5 * sx - 1.9, 33.4, -29.75), (3.8, 2.8, 0.4), ch)
        orb(head, (4.5 * sx, 34.8, -30.0), 1.05, amber, glow=True)
        strut(head, (7.6 * sx, 38.4, -28.5), (1.6 * sx, 37.0, -30.4), 1.4, ch)
        strut(head, (7.8 * sx, 30.2, -23.5), (5.8 * sx, 29.0, -32.5), 1.6, bn)
        for k in range(3):
            orb(head, (9.3 * sx, 37.6 - k * 1.4, -20.5 + k * 2.6), 0.7, amber, glow=True)
            head.add(((9.0 if sx > 0 else -9.4), 36.5 - k * 1.4, -21.6 + k * 2.6), (0.4, 2.2, 2.2), ch)
    head.add((-1.6, 31.4, -35.75), (3.2, 2.4, 0.4), ch)
    for k in range(17):
        a = math.radians(-35 + k * 250 / 16)
        r0 = 9.2
        L = 17 + (k % 2) * 5
        base = (r0 * math.cos(a), 36 + r0 * math.sin(a), -13)
        tip = ((r0 + L) * math.cos(a), 36 + (r0 + L) * math.sin(a), -7 + (k % 3))
        spike(head, base, tip, 1.8, ch, steps=3)
        strut(head, tuple(base[i] + (tip[i] - base[i]) * 0.35 for i in range(3)), tip, 0.9, flame, glow=True)
    for z in range(-33, -22, 3):
        for sx in (-1, 1):
            w = 5.0 if z < -28 else 7.0
            spike(head, (w * sx, 28.9, z), (w * 0.95 * sx, 24.6, z - 0.4), 1.2, th, steps=2)
    for x in (-3.6, -1.2, 1.2, 3.6):
        spike(head, (x, 28.9, -35.2), (x, 24.2 + abs(x) * 0.3, -35.6), 1.3, th, steps=2)

    jaw = m.bone("jaw", (0, 29, -16), "head", rotation=(20, 0, 0))
    bevel(jaw, (-7, 22.5, -30), (14, 4.6, 14.5), bn, b=0.8)
    bevel(jaw, (-5, 22.8, -36), (10, 4.0, 6.5), bn, b=0.7)
    for z in range(-33, -18, 3):
        for sx in (-1, 1):
            w = 4.2 if z < -29 else 6.2
            spike(jaw, (w * sx, 27, z), (w * 0.95 * sx, 30.6, z + 0.4), 1.1, th, steps=2)
    jaw.add((-5.6, 26.95, -29), (11.2, 0.2, 12), fl)

    for side, sx in (("r", -1), ("l", 1)):
        md = m.bone(f"mandible_{side}", (8.5 * sx, 27, -17), "head", rotation=(0, 12 * sx, 0))
        strut(md, (8.5 * sx, 27, -17), (11.5 * sx, 25.5, -27), 2.0, ch)
        spike(md, (11.5 * sx, 25.5, -27), (6.5 * sx, 24.5, -37), 1.8, ch, steps=3, tip_mat=th)
        for k in range(3):
            spike(md, (10.6 * sx - k * sx, 25.2, -25 - k * 2.6), (8.8 * sx - k * sx, 25, -25.5 - k * 2.6), 0.7, th, steps=1)
    inner = m.bone("inner_jaw", (0, 27, -16), "head")
    inner.add((-5, 24.6, -27), (10, 2, 10.5), fl)
    for x in (-3.5, -1.2, 1.2, 3.5):
        spike(inner, (x, 26.5, -26), (x, 29, -26.4), 0.7, th, steps=1)
    orb(inner, (0, 28, -20), 2.6, core, glow=True)

    prev, a = "head", (0, 42.5, -24)
    for k, b in enumerate(((0, 50, -30), (0, 52.5, -38), (0, 48.5, -44))):
        lb = m.bone(f"lure{k}", a, prev)
        strut(lb, a, b, 1.3 - k * 0.25, bn if k < 2 else ch)
        prev, a = f"lure{k}", b
    bulb = m.get("lure2")
    orb(bulb, (0, 46.6, -45), 1.6, M.radial_glow("ffffff", "ffd84a"), glow=True)
    ring(bulb, (0, 46.6, -45), 2.8, 12, flame, thickness=0.25, width=0.25, plane="xy", glow=True)

    # ---- vertebral tail ending in a comet
    prev, z = "body", 22
    for k, (w, h, L) in enumerate(((6, 5, 8), (5, 4.4, 8), (4.2, 3.8, 8), (3.4, 3.2, 8), (2.6, 2.6, 8), (2, 2, 8))):
        tb = m.bone(f"tail{k}", (0, 36, z), prev)
        bevel(tb, (-w / 2, 36 - h / 2, z), (w, h, L + 0.4), ch if k % 2 else bn, b=0.4)
        for sx in (-1, 1):
            spike(tb, (w / 2 * sx, 36, z + 3), ((w / 2 + 3 - k * 0.3) * sx, 37, z + 6), 0.9, bn, steps=2)
        prev, z = f"tail{k}", z + L
    comet = m.get("tail5")
    orb(comet, (0, 36, z + 0.5), 1.8, core, glow=True)
    for dx, dy in ((0, 0), (-3.5, 1), (3.5, 1), (-2, -2.5), (2, -2.5), (0, 3)):
        strut(comet, (0, 36, z), (dx * 1.8, 36 + dy * 1.6, z + 26 - abs(dx) * 2), 1.3 - abs(dx) * 0.12, flame, glow=True)
    return m
