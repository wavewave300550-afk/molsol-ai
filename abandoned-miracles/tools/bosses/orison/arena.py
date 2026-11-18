"""
The Court of Unlived Hours - Orison's demonstration arena.

A ruined tribunal laid out as a clock: the floor is a polar grid (rings every
four blocks, spokes every 45 degrees, two-tone cells, gold hour marks at the
rim) - the same grid Orison's ultimate uses, so the floor itself helps a player
read and remember the patterns. Around it stand a judge's bench under a broken
dial, public galleries, stopped clock faces and hanging pendulums. Everything
taller than the floor stands OUTSIDE the 18-block fighting circle.
"""
from __future__ import annotations

import math

from kit.arena import AIR, Arena, blk, froglight, lantern, pillar, slab, stairs

SIZE = 47          # 23 blocks from the centre to each edge
HEIGHT = 14
NAME = "court_of_unlived_hours"


def _dial(a: Arena, cx: int, y0: int, cz: int, axis: str, r: int, broken: float, hour: float, minute: float) -> None:
    """A standing clock face in the plane perpendicular to `axis` ('x' -> faces east/west, 'z' -> north/south)."""
    for du in range(-r, r + 1):
        for dv in range(-r, r + 1):
            d = math.hypot(du, dv)
            if d > r + 0.4:
                continue
            x, z = (cx, cz + du) if axis == "x" else (cx + du, cz)
            y = y0 + r + dv
            if a.rng.random() < broken and d > r * 0.45:
                continue                                          # a missing piece of the dial
            if d > r - 0.6:
                b = blk("polished_blackstone") if (round(math.degrees(math.atan2(dv, du))) % 30) else blk("gold_block")
            elif d < 0.6:
                b = blk("gold_block")
            else:
                b = blk("calcite") if a.rng.random() < 0.8 else blk("smooth_quartz", pillar_axis="y")
            a.put(x, y, z, b)
    for ang, ln in ((hour, r * 0.5), (minute, r * 0.8)):
        for k in range(1, int(ln) + 1):
            du, dv = round(math.cos(math.radians(ang)) * k), round(math.sin(math.radians(ang)) * k)
            x, z = (cx, cz + du) if axis == "x" else (cx + du, cz)
            a.put(x, y0 + r + dv, z, blk("iron_block"))


def build() -> Arena:
    a = Arena(SIZE, HEIGHT, floor=0, seed=4004)
    dark, pale = blk("polished_deepslate"), blk("polished_tuff")
    line, rim, outer = blk("iron_block"), blk("polished_blackstone_bricks"), blk("deepslate_bricks")

    def floor(r: float, th: float):
        if r < 1.5:
            return froglight("pearlescent")
        if 17.5 <= r < 18.5:
            return rim                                             # the edge of the fighting circle
        if r >= 18.5:
            return outer if a.rng.random() < 0.85 else blk("deepslate_tiles")
        if 16.3 <= r < 17.5 and min(th % 30, 30 - th % 30) * r * math.pi / 180 < 0.55:
            return blk("gold_block")                               # twelve hour marks
        for ring in (4, 8, 12, 16):
            if abs(r - ring) < 0.5:
                return line
        spoke = min((th - 22.5) % 45, 45 - (th - 22.5) % 45)
        if r > 4.5 and spoke * r * math.pi / 180 < 0.5:
            return blk("polished_blackstone")
        if abs(r - 10) < 0.5 and min(th % 45, 45 - th % 45) * r * math.pi / 180 < 0.5:
            return froglight("pearlescent")                        # floor lights in the middle of each wedge
        band = int(r // 4)
        wedge = int(((th + 22.5) % 360) // 45)
        return dark if (band + wedge) % 2 == 0 else pale

    a.disc(0, 23.4, 0, floor)
    a.clear_above_floor(22.6, HEIGHT - 1)
    c = a.c

    # the bench: a dais on the north side with a tall back and the court's own dial, cracked
    for dx in range(-5, 6):
        for dz, h in ((-20, 1), (-21, 2), (-22, 3)):
            for y in range(1, 1 + h):
                a.put(c + dx, y, c + dz, outer if abs(dx) < 5 else blk("polished_blackstone"))
        a.put(c + dx, 2, c - 20, stairs("polished_blackstone_brick_stairs", "north")) if abs(dx) < 5 else None
    for dx in (-5, 5):
        a.column(c + dx, c - 22, 4, 7, pillar("quartz_pillar"), blk("chiseled_quartz_block", pillar_axis="y"))
        a.put(c + dx, 11, c - 22, lantern("soul_lantern", False))
    for dx in range(-1, 2):
        a.put(c + dx, 4, c - 22, blk("polished_blackstone"))        # the seat no one sits in
    a.put(c, 5, c - 22, blk("chiseled_polished_blackstone"))
    _dial(a, c, 6, c - 23, "z", 3, 0.22, 200, -70)

    # public galleries east and west: two rows of benches facing the floor
    for side in (-1, 1):
        for row, dx in enumerate((20, 21)):
            for dz in range(-7, 8):
                if abs(dz) == 3:
                    continue
                x = c + side * dx
                if row:
                    a.put(x, 1, c + dz, outer)
                a.put(x, 1 + row, c + dz, stairs("polished_blackstone_brick_stairs", "east" if side > 0 else "west"))
    # stopped clocks standing around the rim, each wrong in its own way
    for th, r, hr, mn, br in ((52, 2, 30, 150, 0.15), (128, 3, 100, 10, 0.3), (232, 2, 250, 300, 0.1), (308, 3, 170, 80, 0.35)):
        x, z = a.polar(21.2, th)
        axis = "x" if abs(math.cos(math.radians(th))) > 0.7 else "z"
        a.box(x - (0 if axis == "x" else r), 1, z - (r if axis == "x" else 0), x + (0 if axis == "x" else r), 1, z + (r if axis == "x" else 0), blk("polished_blackstone"))
        _dial(a, x, 2, z, axis, r, br, hr, mn)
    # pendulums that no longer swing: a frame, a rod, a bob hanging at the wrong angle of rest
    for th in (20, 160, 200, 340):
        x, z = a.polar(20.6, th)
        tx, tz = -math.sin(math.radians(th)), math.cos(math.radians(th))
        p0 = (int(round(x - tx * 2)), int(round(z - tz * 2)))
        p1 = (int(round(x + tx * 2)), int(round(z + tz * 2)))
        for (px, pz) in (p0, p1):
            a.column(px, pz, 1, 9, pillar("quartz_pillar"), blk("chiseled_quartz_block", pillar_axis="y"), blk("quartz_bricks"))
        for k in range(5):
            bx, bz = int(round(p0[0] + (p1[0] - p0[0]) * k / 4)), int(round(p0[1] + (p1[1] - p0[1]) * k / 4))
            a.put(bx, 10, bz, slab("smooth_quartz_slab", False))
        for y in range(5, 10):
            a.put(int(round(x)), y, int(round(z)), blk("end_rod", facing_direction=1))
        a.put(int(round(x)), 4, int(round(z)), blk("gold_block"))
        a.put(int(round(x)), 3, int(round(z)), slab("smooth_quartz_slab", True))
    # the public door, south
    for dx in (-3, 3):
        a.column(c + dx, c + 22, 1, 6, pillar("quartz_pillar"), blk("chiseled_quartz_block", pillar_axis="y"))
        a.put(c + dx, 7, c + 22, lantern("soul_lantern", False))
    # fallen pieces of dial lying outside the circle
    for th in (95, 180, 275):
        x, z = a.polar(20.2, th)
        for _ in range(4):
            a.put(x + a.rng.randint(-1, 1), 1, z + a.rng.randint(-1, 1), a.rng.choice((blk("calcite"), slab("smooth_quartz_slab"), blk("iron_block"))))
    return a
