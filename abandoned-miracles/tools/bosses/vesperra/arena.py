"""
The Hall of Endless Succession - Vesperra's demonstration arena.

A circular throne hall: a pale inlaid floor, a ring of ivory columns (several
snapped), the wool-and-web cocoons of abandoned moltings between them, and the
statues of earlier empresses - each one a little more broken than the last.
Everything taller than the floor stands OUTSIDE the 17-block fighting circle.
"""
from __future__ import annotations

import math

from kit.arena import AIR, Arena, blk, bone, candle, froglight, lantern, pillar, slab, stairs

SIZE = 45          # 22 blocks from the centre to each edge
HEIGHT = 14
NAME = "hall_of_endless_succession"


def build() -> Arena:
    a = Arena(SIZE, HEIGHT, floor=0, seed=1001)
    quartz, bricks, calcite = blk("smooth_quartz", pillar_axis="y"), blk("quartz_bricks"), blk("calcite")
    dark, darkb, gilt = blk("polished_blackstone"), blk("polished_blackstone_bricks"), blk("gilded_blackstone")

    def floor(r: float, th: float):
        if r < 1.5:
            return froglight("pearlescent")
        if r < 3.5:
            return blk("chiseled_quartz_block", pillar_axis="y")
        if 5.5 <= r < 6.5 or 11.5 <= r < 12.5:
            return gilt if int(th // 15) % 4 == 0 else dark
        if 16.5 <= r < 17.5:                                    # the edge of the fighting circle, readable underfoot
            return darkb
        spoke = min((th % 60), 60 - (th % 60))                  # six radial inlays
        if spoke * r * math.pi / 180 < 0.55 and r >= 3.5:
            return bone("x" if abs(math.cos(math.radians(th))) > 0.7 else "z")
        if (9.5 <= r < 10.5 or 14.5 <= r < 15.5) and abs((th % 30) - 15) * r * math.pi / 180 < 0.5:
            return froglight("pearlescent")                     # floor lights: no shadows, nothing to trip on
        if r >= 17.5:
            return darkb if a.rng.random() < 0.8 else blk("blackstone")
        return calcite if a.rng.random() < 0.16 else (bricks if a.rng.random() < 0.3 else quartz)

    a.disc(0, 22.4, 0, floor)
    a.clear_above_floor(21.5, HEIGHT - 1)

    # the colonnade: twelve ivory columns, some snapped by an earlier reign
    for i in range(12):
        th = i * 30 + 15
        x, z = a.polar(19.5, th)
        broken = i in (2, 7, 10)
        h = a.rng.choice((3, 4, 5)) if broken else 10
        a.column(x, z, 1, h, pillar("quartz_pillar"), None if broken else blk("chiseled_quartz_block", pillar_axis="y"),
                 blk("quartz_bricks"), wide=2)
        if not broken:
            a.put(x, 1 + h, z, lantern("soul_lantern", False))
        else:                                                    # rubble where the drum fell
            for _ in range(5):
                rx, rz = x + a.rng.randint(-2, 3), z + a.rng.randint(-2, 3)
                if math.hypot(rx - a.c, rz - a.c) > 18:
                    a.put(rx, 1, rz, a.rng.choice((bricks, calcite, slab("smooth_quartz_slab"))))
        # a low broken wall behind every second column
        if i % 2 == 0:
            for d in (-2, -1, 0, 1, 2, 3):
                wx, wz = a.polar(21.4, th + d * 3.2)
                for y in range(1, 1 + a.rng.choice((1, 2, 2, 3))):
                    a.put(wx, y, wz, blk("deepslate_tiles") if a.rng.random() < 0.7 else blk("polished_deepslate"))

    # abandoned cocoons: each molting left one behind
    for th in (0, 60, 95, 150, 200, 240, 300, 335):
        x, z = a.polar(19.2 + a.rng.random(), th)
        tall = a.rng.choice((2, 3, 3, 4))
        for y in range(1, 1 + tall):
            for dx in (0, 1):
                for dz in (0, 1):
                    if y == tall and (dx + dz) % 2:
                        continue
                    a.put(x + dx, y, z + dz, blk("white_wool") if a.rng.random() < 0.6 else
                          blk("mushroom_stem", huge_mushroom_bits=15))
        a.put(x, 1 + tall, z, blk("web"))
        a.put(x + 1, tall, z - 1, blk("web"))

    # statues of the empresses that came before: body, flared skirt, bone arms, a candle crown
    for k, th in enumerate((45, 135, 225, 315)):
        x, z = a.polar(18.8, th)
        a.box(x - 1, 1, z - 1, x + 1, 1, z + 1, dark)
        for d, f in (((1, 0), "west"), ((-1, 0), "east"), ((0, 1), "north"), ((0, -1), "south")):
            a.put(x + d[0], 2, z + d[1], stairs("smooth_quartz_stairs", f))
        a.put(x, 2, z, quartz)
        a.put(x, 3, z, quartz)
        if k != 1:
            a.put(x, 4, z, quartz)
            ax = "x" if abs(math.cos(math.radians(th))) < 0.71 else "z"
            if k != 3:
                a.put(x + (1 if ax == "x" else 0), 4, z + (1 if ax == "z" else 0), bone(ax))
            a.put(x - (1 if ax == "x" else 0), 4, z - (1 if ax == "z" else 0), bone(ax))
        if k == 0:                                               # the only one that kept her head
            a.put(x, 5, z, blk("chiseled_quartz_block", pillar_axis="y"))
            a.put(x, 6, z, candle("white_candle", 3, True))
        elif k == 2:
            a.put(x, 5, z, candle("white_candle", 1, False))
            hx, hz = a.polar(17.9, th + 9)
            a.put(hx, 1, hz, blk("chiseled_quartz_block", pillar_axis="x"))   # her head, on the floor
    # a throne dais on the north side, outside the circle
    for dx in range(-3, 4):
        a.put(a.c + dx, 1, a.c - 20, darkb)
        a.put(a.c + dx, 1, a.c - 21, darkb)
        a.put(a.c + dx, 2, a.c - 21, quartz if abs(dx) < 3 else gilt)
    for y in range(3, 8):
        a.put(a.c, y, a.c - 21, pillar("quartz_pillar") if y < 7 else candle("white_candle", 3, True))
    a.put(a.c - 1, 3, a.c - 21, stairs("smooth_quartz_stairs", "west"))
    a.put(a.c + 1, 3, a.c - 21, stairs("smooth_quartz_stairs", "east"))
    return a
