"""
The Basilica of the Last Note - Cantor XIII's demonstration arena.

A round performance sanctuary. The floor is the score: six copper spokes cut it
into sectors and two copper rings into bands (an inner disc, a middle band, an
outer band), which are exactly the regions The Final Requiem calls out, so a
player can read "which sixth, which ring" straight off the stone. A ruined organ
stands at the north end, four stained-glass arches at the diagonals, and
everything taller than the floor is outside the 19-block fighting circle.
"""
from __future__ import annotations

import math

from kit.arena import Arena, blk, froglight, lantern, slab, stairs

SIZE = 51          # 25 blocks from the centre to each edge
HEIGHT = 16
NAME = "basilica_of_the_last_note"
INNER, MIDDLE = 6.0, 12.0            # ring radii used by the script's region patterns


def build() -> Arena:
    a = Arena(SIZE, HEIGHT, floor=0, seed=2002)
    tiles, polished, bricks = blk("deepslate_tiles"), blk("polished_deepslate"), blk("deepslate_bricks")
    copper, gilt, dark = blk("waxed_oxidized_cut_copper"), blk("gilded_blackstone"), blk("polished_blackstone")

    def floor(r: float, th: float):
        if r < 1.5:
            return froglight("ochre")
        if abs(r - INNER) < 0.5 or abs(r - MIDDLE) < 0.5:
            return copper                                         # the two rings
        if 18.5 <= r < 19.5:
            return gilt                                           # the edge of the fighting circle
        spoke = min(th % 60, 60 - th % 60)
        if r >= 1.5 and spoke * r * math.pi / 180 < 0.55 and r < 18.5:
            return copper                                         # six spokes
        if (abs(r - 9) < 0.5 or abs(r - 15.5) < 0.5) and abs((th % 60) - 30) * r * math.pi / 180 < 0.5:
            return froglight("ochre")                             # flush floor lights
        if r >= 19.5:
            return bricks if a.rng.random() < 0.75 else blk("cracked_deepslate_bricks")
        if r < INNER:
            return polished
        return polished if a.rng.random() < 0.22 else tiles

    a.disc(0, 25.4, 0, floor)
    a.clear_above_floor(24.5, HEIGHT - 1)

    # the ruined great organ at the north end: ranks of copper pipes, the tallest in the middle
    for i in range(-7, 8):
        x = a.c + i
        z = a.c - 22 - (1 if abs(i) % 2 else 0)
        h = max(3, 13 - abs(i) - (a.rng.randint(2, 6) if i in (-5, 2, 6) else 0))
        mat = blk("waxed_weathered_copper") if abs(i) % 3 else blk("waxed_oxidized_copper")
        a.column(x, z, 1, h, mat, blk("waxed_oxidized_cut_copper"))
    for dx in range(-8, 9):                                       # organ case
        a.put(a.c + dx, 1, a.c - 24, dark)
        a.put(a.c + dx, 2, a.c - 24, bricks)
    for dx in (-3, -2, -1, 0, 1, 2, 3):                           # the keyboard nobody plays
        a.put(a.c + dx, 1, a.c - 20, stairs("dark_oak_stairs", "north"))
    a.put(a.c - 4, 1, a.c - 20, lantern("lantern", False))
    a.put(a.c + 4, 1, a.c - 20, lantern("lantern", False))
    for (dx, dz) in ((6, -19), (7, -18), (-8, -17)):              # fallen pipes
        for k in range(4):
            a.put(a.c + dx + k * (1 if dx > 0 else -1), 1, a.c + dz, blk("waxed_weathered_copper"))

    # four stained-glass arches at the diagonals, some panes long gone
    glass = [blk("blue_stained_glass"), blk("purple_stained_glass"), blk("red_stained_glass")]
    for k, th in enumerate((45, 135, 225, 315)):
        tx, tz = -math.sin(math.radians(th)), math.cos(math.radians(th))
        for j in range(-3, 4):
            x, z = a.polar(22.6, th)
            x, z = int(round(x + tx * j)), int(round(z + tz * j))
            edge = abs(j) == 3
            top = 9 - abs(j)
            for y in range(1, top + 1):
                if edge or y == 1 or y == top:
                    a.put(x, y, z, bricks)
                elif not (k in (1, 2) and a.rng.random() < 0.3):
                    a.put(x, y, z, glass[(j + y) % 3])
        x, z = a.polar(21.2, th)
        a.put(x, 1, z, lantern("soul_lantern", False))

    # short pew arcs on the south side, outside the circle
    for th in range(60, 121, 6):
        for r in (21.0, 23.0):
            x, z = a.polar(r, th)
            a.put(x, 1, z, stairs("dark_oak_stairs", "south"))
    # bell stands either side of the south door
    for sx in (-1, 1):
        x, z = a.c + sx * 9, a.c + 22
        a.column(x, z, 1, 4, blk("polished_blackstone_bricks"), blk("gold_block"))
        a.put(x, 5, z, slab("polished_blackstone_slab"))
        a.put(x, 6, z, lantern("lantern", False))
    return a
