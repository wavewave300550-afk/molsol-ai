"""
The Observatory of Unwritten Borders - Nomos's demonstration arena.

A square surveying floor, 40 x 40, ruled into the same 8 x 8 grid of five-block
cells that the fight's logic uses: dark ruled lines on every cell boundary,
a heavier meridian and parallel through the centre, a lodestone at the origin,
an emerald benchmark at the middle of each quadrant, and a graduated border
like the frame of a chart. Everything taller than the floor (corner survey
pillars, a broken armillary, chart tables) stands outside the fighting square.
"""
from __future__ import annotations

import math

from kit.arena import AIR, Arena, blk, froglight, lantern, pillar, slab, stairs

SIZE = 47          # 23 blocks from the centre to each edge; the fighting square is the inner 41 x 41
HEIGHT = 15
NAME = "observatory_of_unwritten_borders"
HALF = 20
CELL = 5


def build() -> Arena:
    a = Arena(SIZE, HEIGHT, floor=0, seed=3003)
    vellum, vellum2, chis = blk("smooth_sandstone"), blk("cut_sandstone"), blk("chiseled_sandstone")
    ink, ink2 = blk("polished_blackstone"), blk("deepslate_tiles")
    brass, brass2 = blk("waxed_cut_copper"), blk("waxed_exposed_cut_copper")
    frame = blk("polished_deepslate")

    def floor(dx: int, dz: int):
        ax, az = abs(dx), abs(dz)
        if ax > HALF + 3 or az > HALF + 3:
            return None
        if ax > HALF or az > HALF:                               # outside the fighting square
            return frame if (ax + az) % 7 else blk("deepslate_bricks")
        if dx == 0 and dz == 0:
            return blk("lodestone")                             # the origin of every measurement
        if ax == HALF or az == HALF:                             # graduated chart border
            k = dx if az == HALF else dz
            if ax == HALF and az == HALF:
                return brass
            return blk("smooth_quartz", pillar_axis="y") if k % 2 else ink
        if dx == 0 or dz == 0:                                   # prime meridian and parallel
            return brass if (ax + az) % 5 else brass2
        if ax == 10 and az == 10:                                # quadrant benchmarks
            return blk("emerald_block")
        if ax % CELL == 0 and az % CELL == 0:                    # every grid intersection is lit
            return blk("sea_lantern")
        if ax % CELL == 0 or az % CELL == 0:                     # ruled cell boundaries
            return ink if (ax % 10 == 0 and az % CELL != 0) or (az % 10 == 0 and ax % CELL != 0) else ink2
        if max(abs(ax - 10), abs(az - 10)) == 1:                 # a small frame round each benchmark
            return chis
        return vellum2 if a.rng.random() < 0.18 else vellum

    a.square(HALF + 3, 0, floor)
    for dx in range(-HALF - 3, HALF + 4):
        for dz in range(-HALF - 3, HALF + 4):
            for y in range(1, HEIGHT):
                a.put(a.c + dx, y, a.c + dz, AIR)

    # corner survey pillars: copper columns carrying a lightning-rod "station pole"
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = a.c + sx * (HALF + 2), a.c + sz * (HALF + 2)
            a.column(x, z, 1, 8, blk("waxed_exposed_cut_copper"), blk("waxed_chiseled_copper"), blk("deepslate_bricks"))
            a.put(x, 9, z, blk("lightning_rod", facing_direction=1))
            a.put(x - sx, 1, z, slab("deepslate_brick_slab"))
            a.put(x, 1, z - sz, slab("deepslate_brick_slab"))
            a.put(x - sx, 6, z, lantern("soul_lantern", True) if False else blk("sea_lantern"))

    # low parapet with gaps: the edge of the known world, readable from inside
    for k in range(-HALF - 2, HALF + 3):
        for (x, z) in ((a.c + k, a.c - HALF - 3), (a.c + k, a.c + HALF + 3), (a.c - HALF - 3, a.c + k), (a.c + HALF + 3, a.c + k)):
            if abs(k) <= 2 or abs(abs(k) - 12) <= 1:
                continue                                         # entrances on every side
            h = 2 if k % 4 else 3
            for y in range(1, 1 + h):
                a.put(x, y, z, blk("deepslate_bricks") if y < h else blk("deepslate_tiles"))

    # north: a broken armillary ring of copper, taller than the parapet
    cx, cz = a.c, a.c - HALF - 2
    for ang in range(0, 360, 15):
        if 200 < ang < 250:
            continue                                             # the gap where it failed
        x = round(cx + 6 * math.cos(math.radians(ang)))
        y = round(7 + 6 * math.sin(math.radians(ang)))
        if y >= 1:
            a.put(x, y, cz, blk("waxed_weathered_cut_copper") if ang % 30 else blk("waxed_exposed_cut_copper"))
    for y in range(1, 8):
        a.put(cx, y, cz, pillar("quartz_pillar") if y < 7 else blk("emerald_block"))
    # south: chart tables and shelves of unfinished maps
    for dx in (-9, -8, -7, 7, 8, 9):
        a.put(a.c + dx, 1, a.c + HALF + 2, blk("cartography_table") if abs(dx) != 8 else blk("bookshelf"))
        if abs(dx) == 8:
            a.put(a.c + dx, 2, a.c + HALF + 2, blk("bookshelf"))
    # east / west: sighting posts aligned with the parallel
    for sx in (-1, 1):
        x = a.c + sx * (HALF + 2)
        for y in range(1, 5):
            a.put(x, y, a.c + 6, blk("waxed_cut_copper") if y < 4 else froglight("verdant"))
            a.put(x, y, a.c - 6, blk("waxed_cut_copper") if y < 4 else froglight("verdant"))
    return a
