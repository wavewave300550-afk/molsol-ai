"""
The Wrong Hatch - voxel boss model, reproduced from the approved four-view sheet.

Built at half scale (1 u = 1/8 block) and exported x2, so the finished model is
~5.2 blocks tall, ~6.3 blocks long and spreads its wings to ~9.6 blocks.

Bedrock geometry space: the boss faces -Z, its right side is -X. Right-side
parts are modelled once and mirrored to the left (with independent textures,
so the two halves are not pixel-identical).

Bone map (animated bones in CAPS-free names used by tools/anims.py):
    root
     ├─ body ─┬─ core            (chest star + golden orb, glow)
     │        ├─ neck ── head ─┬─ beak_upper, jaw, wattle, comb, brow
     │        ├─ wing_r ─┬─ pauldron_r, wing_r_coverts, wing_r_secondaries, wing_r_primaries
     │        ├─ wing_l  (mirror)
     │        ├─ tail ─┬─ sickle_r1..5 (chain), curl_r1..3, sickle_l*, curl_l*, fan
     │        └─ skirt
     ├─ leg_r ── foot_r ── toes
     └─ leg_l ── foot_l
"""
from __future__ import annotations

import math

import materials as M
from voxkit import Bone, Model

S_SHELL = M.shell()
S_SHELL_CRACKY = M.shell(crack_rate=1.6, glow_bias=0.15)
S_SHELL_GREY = M.shell(grey=0.6)
S_SEAM = M.glow_seam()
S_FAN = M.feather(M.hx("f3e5c0"), M.hx("d9bf86"), M.hx("fbf4df"))
S_SHELL_GLOWY = M.shell(crack_rate=1.8, glow_bias=0.45)
S_FEATHER = M.feather()
S_FEATHER_SIDE = M.feather(along="v")
S_FEATHER_DOWN = M.feather(M.FEATHER_DARK, M.hx("b8a37d"), M.FEATHER)
S_INNER = M.solid("c9b48f", noise=10)
S_COMB = M.comb()
S_WATTLE = M.wattle()
S_BEAK_UP = M.beak(True)
S_BEAK_LO = M.beak(False)
S_LEG = M.leg()
S_CLAW = M.claw()
S_EYE = M.eye()
S_ORB = M.core_orb()
S_STAR = M.gold_star()
S_SOCKET = M.solid("2a1410", noise=6, bevel=False)


def blade(b: Bone, base, length, width, thick, rot, mat=S_FEATHER, steps=4, taper=0.3, flat="z", tag="feather"):
    """Broad pointed blade hanging along local -Y from ``base``; ``flat`` = thickness axis.

    The first ~60 % of the blade keeps its full width, the tip steps in like a voxel arrowhead."""
    bx, by, bz = base
    profile = {2: [1.0, 0.55], 3: [1.0, 0.78, 0.42], 4: [1.0, 0.95, 0.72, 0.4], 5: [1.0, 1.0, 0.85, 0.62, 0.34]}[steps]
    fracs = {2: [0.62, 0.38], 3: [0.55, 0.27, 0.18], 4: [0.42, 0.26, 0.18, 0.14], 5: [0.3, 0.25, 0.18, 0.15, 0.12]}[steps]
    y = by
    for w_k, f_k in zip(profile, fracs):
        w = max(0.8, width * (w_k if taper < 0.9 else 1.0))
        seg = length * f_k
        y0 = y - seg
        th = thick * (1.0 if w_k > 0.5 else 0.8)
        if flat == "z":
            origin, size = (bx - w / 2, y0, bz - th / 2), (w, seg + 0.02, th)
        else:
            origin, size = (bx - th / 2, y0, bz - w / 2), (th, seg + 0.02, w)
        b.box(origin, size, mat, rotation=rot, pivot=base, tag=tag)
        y = y0


def plate(b: Bone, center, size, rot=None, mat=S_SHELL, chip=True):
    """Angular eggshell plate centred on ``center`` with an optional raised facet."""
    cx, cy, cz = center
    sx, sy, sz = size
    b.box((cx - sx / 2, cy - sy / 2, cz - sz / 2), size, mat, rotation=rot, pivot=center, tag="shell")
    if chip and min(sx, sy, sz) > 1.5:
        # raised facet towards the outer face (largest outward dimension = smallest size axis)
        axis = min(range(3), key=lambda i: size[i])
        s2 = [v * 0.62 for v in size]
        s2[axis] = size[axis] * 0.45
        c2 = list(center)
        c2[1] += sy * 0.08
        sign = 1
        if axis == 0:
            sign = -1 if cx < 0 else 1
        elif axis == 2:
            sign = -1 if cz < 0 else 1
        c2[axis] += sign * (size[axis] / 2 + s2[axis] / 2 - 0.05)
        b.box((c2[0] - s2[0] / 2, c2[1] - s2[1] / 2, c2[2] - s2[2] / 2), s2, mat, rotation=rot, pivot=center,
              tag="shell")


def build() -> Model:
    m = Model("geometry.wrong_hatch.boss", scale=2.0, td=2.0, seed="wrong_hatch")

    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 13, 0), "root")

    # ------------------------------------------------------------------ torso volume (rounded voxel ovoid)
    for (y0, y1, hx_, z0, z1) in ((8.5, 11, 8.5, -11, 10), (11, 14, 10.0, -13, 12.5), (14, 25, 10.5, -14, 13.5),
                                  (25, 28, 9.5, -12, 10.5), (28, 30, 7.5, -8, 6)):
        body.span((-hx_, y0, z0), (hx_, y1, z1), S_INNER)
    # molten gold under the shell plates (only seen through the seams)
    body.span((-8.8, 21, -8), (8.8, 30.0, 6.5), S_SEAM, tag="glow")
    body.span((-8.8, 21, 6.0), (8.8, 27.0, 12.2), S_SEAM, tag="glow")

    # chest: feathered front, slightly protruding
    body.span((-9, 9.5, -14.8), (9, 23.5, -12), S_FEATHER_DOWN)

    # chest feather plates: overlapping rows of broad blades, leaving the star core free
    rows = ((25.0, 6, 17.0, -15.6), (21.5, 7, 18.0, -16.0), (17.5, 7, 18.5, -16.2),
            (13.8, 7, 17.5, -16.0), (10.8, 6, 15.0, -15.4))
    for row, (y, n, spread, zf) in enumerate(rows):
        for i in range(n):
            x = -spread / 2 + spread * (i + 0.5) / n + (0.6 if row % 2 else 0)
            if 1 <= row <= 3 and abs(x) < 7.2 and abs(y - 16.5) < 8:
                continue        # star core
            blade(body, (x, y, zf + abs(x) * 0.06), 5.4, 4.4, 1.2, (10, 0, x * 1.1), S_FEATHER, steps=3, taper=0.3)

    # ------------------------------------------------------------------ skirt: ring of broad blades around the belly
    skirt = m.bone("skirt", (0, 12, 0), "body")
    for i in range(20):
        ang = (i / 20.0) * 2 * math.pi
        x = math.sin(ang) * 10.6
        z = -math.cos(ang) * 13.0 + 0.5
        rot = (-16 * math.cos(ang), 0, -16 * math.sin(ang))      # tips flare outwards
        length = (6.0 if z < 4 else 4.5) if abs(math.cos(ang)) > 0.6 else (4.5 if z < 4 else 3.5)
        frontish = abs(math.cos(ang)) > 0.6
        base_y = 13.0 + max(0.0, -math.cos(ang)) * 0.8 + max(0.0, math.cos(ang) * -1) * 0 + max(0.0, -z / 13.0) * 0.6 \
            + max(0.0, z / 13.0) * 1.6
        blade(skirt, (x, base_y, z), length, 5.0, 1.3, rot, S_FEATHER, steps=3, taper=0.25,
              flat="z" if frontish else "x")

    # ------------------------------------------------------------------ back: shell plates + chevron
    plates = [
        ((0, 30.4, -3.5), (10, 2.2, 8), (6, 0, 0)),
        ((0, 30.2, 4.5), (11, 2.2, 8), (-4, 0, 0)),
        ((0, 27.4, 10.6), (12, 2.2, 6), (-30, 0, 0)),
        ((-6.4, 29.2, 0.5), (5.5, 2.2, 10), (0, 0, 24)),
        ((6.4, 29.2, 0.5), (5.5, 2.2, 10), (0, 0, -24)),
        ((-7.2, 27.0, 8.4), (5.5, 2.2, 7), (-20, 0, 30)),
        ((7.2, 27.0, 8.4), (5.5, 2.2, 7), (-20, 0, -30)),
        # chevron (V) on the back, seen from behind
        ((-5.0, 22.8, 14.7), (10.0, 6.0, 2.0), (4, 0, -26)),
        ((5.0, 22.8, 14.7), (10.0, 6.0, 2.0), (4, 0, 26)),
        ((0, 18.4, 15.0), (7.5, 4.6, 2.0), (2, 0, 0)),
        ((-9.4, 19.0, 13.2), (4.0, 6.0, 2.0), (0, -24, -6)),
        ((9.4, 19.0, 13.2), (4.0, 6.0, 2.0), (0, 24, 6)),
        ((-8.6, 26.2, 12.4), (4.5, 5.0, 2.0), (-10, -20, 10)),
        ((8.6, 26.2, 12.4), (4.5, 5.0, 2.0), (-10, 20, -10)),
    ]
    for c, sz, r in plates:
        plate(body, c, sz, r, S_SHELL_CRACKY)
    # low rump feathers (hide the torso block in the back view)
    for i in range(5):
        x = -6.0 + i * 3
        blade(body, (x, 14.0, 13.9), 5.0, 4.0, 1.2, (-10, 0, x * 1.2), S_FEATHER, steps=3)
    # rump feathers under the chevron (back view)
    for i in range(6):
        x = -7.5 + i * 3
        blade(body, (x, 17.5, 14.6), 6.5, 4.4, 1.2, (-14, 0, x * 1.4), S_FEATHER, steps=3, taper=0.3)

    # ------------------------------------------------------------------ core (chest star + orb)
    core = m.bone("core", (0, 16.5, -16), "body")
    for k in range(3):
        core.box((-2.0, 16.5 - 6.6, -16.9), (4.0, 13.2, 1.0), S_STAR, rotation=(0, 0, k * 60), pivot=(0, 16.5, -16.4),
                 tag="glow")
    for k in range(6):                       # rim shards between the points
        ang = k * 60 + 30
        cx, cy = math.sin(math.radians(ang)) * 6.0, 16.5 + math.cos(math.radians(ang)) * 6.0
        core.box((cx - 1.7, cy - 1.7, -17.6), (3.4, 3.4, 2.2), S_SHELL, rotation=(0, 0, 45 - ang),
                 pivot=(cx, cy, -16.5), tag="shell")
    for k in range(6):                       # outer shard tips around each point
        ang = k * 60
        cx, cy = math.sin(math.radians(ang)) * 7.9, 16.5 + math.cos(math.radians(ang)) * 7.9
        core.box((cx - 1.0, cy - 2.0, -17.0), (2.0, 4.0, 1.6), S_SHELL, rotation=(0, 0, -ang),
                 pivot=(cx, cy, -16.2), tag="shell")
    core.span((-2.5, 14.0, -18.6), (2.5, 19.0, -16.0), S_ORB, tag="glow")
    core.span((-1.7, 13.2, -19.0), (1.7, 19.8, -16.0), S_ORB, tag="glow")
    core.span((-3.3, 14.8, -18.2), (3.3, 18.2, -16.0), S_ORB, tag="glow")
    core.span((-1.5, 15.0, -19.5), (1.5, 18.0, -18.5), S_ORB, tag="glow")

    # ------------------------------------------------------------------ neck + hackles
    neck = m.bone("neck", (0, 23, -8), "body")
    neck.span((-5.8, 20.5, -15.5), (5.8, 28, -5), S_FEATHER)
    for i in range(6):
        x = -5.5 + i * 2.2
        blade(neck, (x, 26.5, -15.6 + abs(x) * 0.15), 5.5, 3.4, 1.1, (14, 0, x * 2.6), S_FEATHER, steps=3, taper=0.3)
    for side in (-1, 1):
        for j in range(3):
            blade(neck, (side * 6.0, 27.5 - j * 0.6, -13 + j * 3.2), 7.0, 3.6, 1.1, (12, 0, -side * 24),
                  S_FEATHER, steps=3, taper=0.3, flat="x")

    # ------------------------------------------------------------------ head
    head = m.bone("head", (0, 27, -11), "neck")
    head.span((-5.6, 25, -18), (5.6, 35.8, -7), S_SHELL)
    plate(head, (0, 34.0, -18.2), (9.8, 3.4, 1.6), None, S_SHELL, chip=False)
    plate(head, (-4.1, 28.6, -18.1), (3.6, 6.2, 1.6), (0, -12, 0), S_SHELL_CRACKY, chip=False)
    plate(head, (4.1, 28.6, -18.1), (3.6, 6.2, 1.6), (0, 12, 0), S_SHELL_CRACKY, chip=False)
    for side in (-1, 1):
        plate(head, (side * 5.8, 33.0, -12.0), (1.6, 4.6, 9.0), (0, 0, side * 4), S_SHELL_CRACKY)
        plate(head, (side * 5.9, 28.2, -9.6), (1.4, 5.0, 4.6), (0, 0, side * 6), S_SHELL_CRACKY, chip=False)
        head.span((side * 5.55, 30.2, -18.3), (side * 6.05, 32.4, -16.0), S_EYE, tag="eye")
    plate(head, (0, 36.1, -12.5), (10.4, 1.4, 10.6), None, S_SHELL, chip=False)
    plate(head, (0, 31.0, -6.8), (10.4, 9, 1.6), None, S_SHELL, chip=False)
    for side in (-1, 1):
        head.span((side * 0.9, 29.9, -18.95), (side * 4.6, 32.7, -18.3), S_SOCKET)
        head.span((side * 1.3, 30.2, -19.1), (side * 4.2, 32.4, -18.6), S_EYE, tag="eye")
    brow = m.bone("brow", (0, 33, -18.5), "head")
    for side in (-1, 1):
        brow.box((min(0, side * 6.0), 32.3, -20.2), (6.0, 2.0, 2.4), S_SHELL,
                 rotation=(0, 0, -side * 17), pivot=(0, 32.5, -19), tag="shell")
    for side in (-1, 1):                     # cheek feather tufts
        for j, (y, ln, rz) in enumerate(((29.0, 5.0, 58), (26.8, 4.6, 42), (31.2, 4.2, 74))):
            blade(head, (side * 5.4, y, -11.5 - j * 1.8), ln, 3.0, 1.1, (6, 0, -side * rz), S_FEATHER, steps=3,
                  taper=0.25)

    beak = m.bone("beak_upper", (0, 29, -17.5), "head")
    beak.span((-2.8, 28.3, -20.2), (2.8, 31.2, -17.4), S_BEAK_UP)
    beak.span((-2.2, 28.0, -21.8), (2.2, 30.6, -20.1), S_BEAK_UP)
    beak.span((-1.4, 27.4, -23.4), (1.4, 29.8, -21.7), S_BEAK_UP)
    jaw = m.bone("jaw", (0, 28.3, -17.5), "head")
    jaw.span((-2.4, 26.5, -20.3), (2.4, 28.4, -17.4), S_BEAK_LO)
    jaw.span((-1.6, 26.8, -21.4), (1.6, 28.2, -20.2), S_BEAK_LO)

    wat = m.bone("wattle", (0, 26.8, -18), "head")
    wat.span((-1.7, 25.0, -18.9), (1.7, 26.9, -17.4), S_WATTLE)
    for side in (-1, 1):
        wat.span((side * 0.7, 22.8, -19.3), (side * 4.3, 26.7, -17.2), S_WATTLE)
        wat.span((side * 1.2, 21.3, -19.1), (side * 3.9, 22.9, -17.4), S_WATTLE)
        wat.span((side * 1.9, 20.4, -18.9), (side * 3.3, 21.4, -17.6), S_WATTLE)

    comb = m.bone("comb", (0, 36.5, -12.5), "head")
    comb.span((-4.0, 35.9, -17.0), (4.0, 37.0, -8.0), S_COMB)
    # stepped pillars: (x, width, height, z front, z back, tilt) - two sub-pillars along z give side notches
    spikes = ((0.0, 2.6, 5.0, -16.4, -8.6, 0), (-3.4, 2.2, 4.4, -15.8, -9.4, 10), (3.4, 2.2, 4.4, -15.8, -9.4, -10),
              (-6.0, 2.0, 3.2, -14.8, -10.6, 24), (6.0, 2.0, 3.2, -14.8, -10.6, -24))
    for (x, w, h, zf, zb, rz) in spikes:
        piv = (x, 36.6, (zf + zb) / 2)
        zm = (zf + zb) / 2
        for (z0, z1, hh) in ((zf, zm + 0.4, h), (zm - 0.4, zb, h * 0.8)):
            comb.box((x - w / 2, 36.6, z0), (w, hh * 0.68, z1 - z0), S_COMB, rotation=(0, 0, rz), pivot=piv)
            comb.box((x - w * 0.34, 36.6 + hh * 0.68 - 0.02, z0 + 0.5), (w * 0.68, hh * 0.32, max(0.8, z1 - z0 - 1.6)),
                     S_COMB, rotation=(0, 0, rz), pivot=piv)

    # mane: hackle feathers sweeping from the back of the head over the shoulders
    for i, x in enumerate((-4.8, -2.4, 0.0, 2.4, 4.8)):
        blade(head, (x, 35.0, -7.6), 9.0, 3.6, 1.2, (52, 0, -x * 2.2), S_FEATHER, steps=4)
    for side in (-1, 1):
        for j, (z, ln) in enumerate(((-9.5, 8.0), (-7.0, 9.0))):
            blade(head, (side * 6.0, 33.0, z), ln, 4.2, 1.2, (40, 0, -side * 16), S_FEATHER_SIDE, steps=4, flat="x")

    # ------------------------------------------------------------------ right wing (mirrored to the left)
    m.bone("wing_r", (-9.5, 27, -7), "body")
    pauld = m.bone("pauldron_r", (-11, 27, -6), "wing_r")
    pauld.span((-15.6, 20.6, -11.4), (-7.6, 28.8, -0.6), S_SEAM, tag="glow", inflate=-0.4)
    plate(pauld, (-11.4, 26.6, -7.8), (8.0, 6.6, 6.4), (6, 0, 14), S_SHELL_GLOWY)
    plate(pauld, (-11.8, 26.0, -1.6), (7.4, 6.0, 5.6), (-6, 0, 16), S_SHELL_GLOWY)
    plate(pauld, (-15.4, 22.8, -7.2), (2.4, 6.4, 6.2), (4, 0, 8), S_SHELL_GLOWY, chip=False)
    plate(pauld, (-15.2, 22.6, -1.2), (2.4, 6.0, 5.4), (-4, 0, 8), S_SHELL_GLOWY, chip=False)
    plate(pauld, (-10.4, 29.6, -5.0), (6.0, 2.2, 7.6), (0, 0, 20), S_SHELL, chip=False)
    plate(pauld, (-11.4, 23.0, -11.4), (7.0, 5.6, 2.0), (0, 0, 10), S_SHELL_GLOWY, chip=False)

    cov = m.bone("wing_r_coverts", (-13.5, 24.5, 2), "wing_r", (-8, 0, 0))
    cov.span((-15.8, 17.5, 0.0), (-11.0, 25.0, 11.0), S_SEAM, tag="glow", inflate=-0.4)
    for (c, sz, r) in (((-15.2, 22.6, 3.2), (2.2, 5.6, 5.6), (-6, 0, 6)),
                       ((-15.0, 22.2, 8.6), (2.2, 5.4, 5.0), (-14, 0, 8)),
                       ((-14.4, 25.0, 6.0), (4.6, 2.0, 9.0), (-10, 0, 18)),
                       ((-13.6, 24.2, 11.6), (4.0, 4.0, 2.0), (-20, 0, 12))):
        plate(cov, c, sz, r, S_SHELL_GLOWY)

    sec = m.bone("wing_r_secondaries", (-14.5, 21, 0), "wing_r")
    # side layer: broad overlapping blades facing outwards, pointing down-back
    for (z, ln, rx, rz, x) in ((-7.6, 14.5, 14, 6, -16.0), (-3.6, 14.5, 22, 6, -16.4), (0.4, 13.5, 30, 5, -16.7),
                               (4.4, 12.5, 38, 5, -16.9)):
        blade(sec, (x, 21.5, z), ln, 7.2, 1.5, (rx, 0, rz), S_FEATHER_SIDE, steps=4, flat="x")
    # front edge: blades facing forwards, flaring out to the A-shaped silhouette of the front view
    for (x, ln, rz, rx, z) in ((-11.8, 15.0, 4, 5, -11.4), (-14.2, 16.5, 9, 7, -10.6), (-16.4, 15.5, 15, 9, -9.8)):
        blade(sec, (x, 22.0, z), ln, 5.6, 1.5, (rx, 0, rz), S_FEATHER, steps=4)

    pri = m.bone("wing_r_primaries", (-14.5, 20, 6), "wing_r")
    for (z, ln, rx, rz, x) in ((6.4, 13.0, 46, 4, -17.1), (8.8, 12.5, 54, 4, -16.7), (11.0, 11.5, 62, 3, -16.2)):
        blade(pri, (x, 21.5, z), ln, 6.8, 1.5, (rx, 0, rz), S_FEATHER_SIDE, steps=4, flat="x")
    # rear edge blades (back view)
    for (x, ln, rz) in ((-12.6, 12.5, 6), (-15.2, 13.5, 15)):
        blade(pri, (x, 21.0, 12.0), ln, 5.4, 1.4, (-36, 0, rz), S_FEATHER, steps=4)
    # inner layer between wing and torso
    for (z, ln, rx) in ((-6.0, 10.0, 8), (-0.5, 10.5, 16), (5.0, 10.0, 28)):
        blade(pri, (-12.6, 18.5, z), ln, 6.0, 1.2, (rx, 0, 9), S_FEATHER_DOWN, steps=3, flat="x")

    m.mirror("wing_r", "wing_l", lambda n: n.replace("_r", "_l"))

    # ------------------------------------------------------------------ tail: fan, sickles, inner curls
    tail = m.bone("tail", (0, 20, 12.5), "body")
    fan = m.bone("fan", (0, 22, 13.5), "tail")
    for i in range(5):
        x = (i - 2) * 3.3
        h = 18.5 - abs(i - 2) * 2.2
        rz = -(i - 2) * 13
        for k in range(4):
            w = 4.8 * (1 - k * 0.1)
            fan.box((x - w / 2, 21.5 + h * k / 4, 15.4 + i % 2 * 0.5), (w, h / 4 + 0.03, 1.4), S_FAN,
                    rotation=(-12, 0, rz), pivot=(x, 21.5, 16.1), tag="feather")

    def sickle(prefix, side, base, segs, width, thick, grey_from, yaw):
        parent = "tail"
        px, py, pz = base
        anchor = m.bone(f"{prefix}0", (px, py, pz), parent, (0, yaw, 0))
        parent = anchor.name
        for i, (length, rx) in enumerate(segs):
            name = f"{prefix}{i + 1}"
            bn = m.bone(name, (px, py, pz), parent, (rx, 0, 0))
            if i >= grey_from:
                mat = M.gradient_feather(M.FEATHER, M.GREY, start=0.0)
            elif i == grey_from - 1:
                mat = M.gradient_feather(M.FEATHER, M.GREY, start=0.55)
            else:
                mat = S_FEATHER
            w0 = width * (1 - 0.08 * i)
            bn.box((px - thick / 2, py, pz - w0 / 2), (thick, length + 0.5, w0), mat, tag="feather")
            bn.box((px - thick * 0.4, py + length * 0.2, pz + w0 / 2 - 0.2), (thick * 0.8, length * 0.55, 1.0), mat,
                   tag="feather")
            parent = name
            py += length
        return parent

    for side, s in ((-1, "r"), (1, "l")):
        sickle(f"sickle_{s}", side, (side * 7.0, 21.0, 15.0),
               [(6.2, -42), (5.4, 20), (5.0, 36), (4.6, 44), (4.2, 46), (3.6, 42)],
               4.4, 2.6, 4, -side * 42)
        sickle(f"curl_{s}", side, (side * 5.6, 20.5, 12.6),
               [(4.0, -18), (3.6, 42), (3.2, 56), (2.8, 60)],
               3.0, 2.0, 3, -side * 38)

    # ------------------------------------------------------------------ legs + feet (right, mirrored)
    leg = m.bone("leg_r", (-5.8, 9.5, -2.5), "root")
    leg.span((-8.7, 7.0, -5.4), (-2.9, 10.2, 0.4), S_FEATHER_DOWN)
    leg.span((-8.0, 2.6, -4.7), (-3.6, 7.2, -0.3), S_LEG)
    leg.span((-8.3, 5.4, -5.0), (-3.3, 6.4, 0.0), S_LEG)
    foot = m.bone("foot_r", (-5.8, 2.6, -2.5), "leg_r")
    foot.span((-8.4, 0.0, -5.6), (-3.2, 2.7, 0.4), S_LEG)
    for (x, rot) in ((-5.8, 0), (-8.2, 24), (-3.4, -24)):
        foot.box((x - 1.15, 0.0, -10.2), (2.3, 2.1, 5.0), S_LEG, rotation=(0, rot, 0), pivot=(x, 1.0, -5.2))
        foot.box((x - 1.35, 0.0, -13.0), (2.7, 2.6, 3.0), S_CLAW, rotation=(0, rot, 0), pivot=(x, 1.0, -5.2),
                 tag="claw")
        foot.box((x - 0.9, 0.0, -13.9), (1.8, 1.4, 1.0), S_CLAW, rotation=(0, rot, 0), pivot=(x, 1.0, -5.2),
                 tag="claw")
    foot.box((-6.9, 0.0, 0.2), (2.2, 1.8, 2.8), S_LEG)
    foot.box((-7.1, 0.0, 2.9), (2.6, 2.2, 2.4), S_CLAW, tag="claw")
    m.mirror("leg_r", "leg_l", lambda n: n.replace("_r", "_l"))
    return m


GLOW_TAGS = {"glow"}


if __name__ == "__main__":
    mm = build()
    print(mm.stats())
