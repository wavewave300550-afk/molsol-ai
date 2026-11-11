"""
Supporting models for The Wrong Hatch encounter.

    chick        - Wrong Chick minion (variant 1 texture = golden Yolkling bomber)
    egg          - landed hatch egg (texture variants: 0 brood/mortar, 1 rotten, 2 gilded)
    brood_shell  - giant tethered egg used by the Final Hatch mechanic
    feather_dart - feather shard projectile
"""
from __future__ import annotations

import math

import numpy as np

import materials as M
from voxkit import Face, Model, hx


def _variant_mat(*mats):
    """Pick a different material per texture variant."""
    def paint(f: Face):
        return mats[min(f.variant, len(mats) - 1)](f)
    return paint


def chick() -> Model:
    m = Model("geometry.wrong_hatch.chick", scale=1.0, td=1.0, seed="chick")
    body_mat = _variant_mat(M.feather(), M.glow_seam(), M.feather())
    shell_mat = _variant_mat(M.shell(crack_rate=2.0, glow_bias=0.3), M.shell(M.hx("ffe39a"), crack_rate=2.5, glow_bias=1.0))
    eye_mat = _variant_mat(M.solid("ffc22e", alpha=0, bevel=False), M.solid("fff6c8", alpha=0, bevel=False))
    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 4, 0), "root")
    body.span((-3, 2.5, -3), (3, 8, 3.5), body_mat)
    body.span((-2.4, 2.0, -2.4), (2.4, 8.4, 3.0), body_mat)
    head = m.bone("head", (0, 8, -1), "body")
    head.span((-2.5, 7.5, -4), (2.5, 12, 0.5), body_mat)
    # cracked eggshell helmet still stuck on its head
    head.span((-3.0, 10.5, -4.5), (3.0, 13.2, 1.0), shell_mat)
    head.span((-2.0, 13.0, -3.5), (1.5, 14.2, 0.0), shell_mat)
    head.span((1.0, 13.0, -2.0), (2.5, 14.8, -0.8), shell_mat)
    head.span((-1.6, 9.0, -4.2), (-0.4, 10.2, -3.9), eye_mat)
    head.span((0.4, 9.0, -4.2), (1.6, 10.2, -3.9), eye_mat)
    beak = m.bone("beak", (0, 8.8, -4), "head")
    beak.span((-1, 8.0, -5.6), (1, 9.2, -4), M.beak(True))
    head.span((-0.5, 11.5, -2), (0.5, 12.0, 0), M.comb())
    for side in (-1, 1):
        w = m.bone(f"wing_{'l' if side > 0 else 'r'}", (side * 3, 7, -0.5), "body")
        w.span((side * 3.0, 3.5, -1.5), (side * 3.9, 7.2, 2.8), body_mat)
        leg = m.bone(f"leg_{'l' if side > 0 else 'r'}", (side * 1.3, 2.5, 0), "root")
        leg.span((side * 0.8, 0.6, -0.5), (side * 1.8, 2.6, 0.5), M.leg())
        leg.span((side * 0.4, 0, -2.0), (side * 2.2, 0.6, 1.0), M.leg())
    return m


def egg() -> Model:
    m = Model("geometry.wrong_hatch.egg", scale=1.0, td=1.0, seed="egg")
    mat = _variant_mat(M.egg(crack_rate=1.4, glow=True),
                       M.egg("c9cf9c", "6f7a3a", crack_rate=2.0, tint="7d8f3a"),
                       M.egg("ffd75e", "c98a12", crack_rate=1.2, glow=True, tint="ffc22e"))
    m.bone("root", (0, 0, 0))
    e = m.bone("egg", (0, 0, 0), "root")
    # voxel ovoid, wider at the bottom
    for (y0, y1, r) in ((0, 1, 2.5), (1, 3, 3.6), (3, 7, 4.0), (7, 9, 3.6), (9, 10.5, 2.9), (10.5, 11.5, 1.8)):
        e.span((-r, y0, -r), (r, y1, r), mat)
    return m


def brood_shell() -> Model:
    m = Model("geometry.wrong_hatch.brood_shell", scale=1.0, td=1.0, seed="brood_shell")
    shell_mat = M.shell(crack_rate=2.2, glow_bias=0.4)
    m.bone("root", (0, 0, 0))
    base = m.bone("base", (0, 0, 0), "root")
    for k in range(7):
        a = k / 7 * 2 * math.pi
        x, z = math.sin(a) * 7, math.cos(a) * 7
        base.box((x - 2, 0, z - 1.5), (4, 3 + (k % 3), 3), M.shell(), rotation=(0, math.degrees(a), 12 * (k % 2) - 6),
                 pivot=(x, 0, z))
    e = m.bone("egg", (0, 2, 0), "root")
    for (y0, y1, r) in ((1, 3, 5.0), (3, 7, 6.6), (7, 15, 7.2), (15, 19, 6.6), (19, 22, 5.4), (22, 24, 3.6),
                        (24, 25, 2.0)):
        e.span((-r, y0, -r), (r, y1, r), shell_mat)
    yolk = m.bone("yolk", (0, 12, 0), "egg")
    yolk.span((-4, 9, -7.6), (4, 15, -7.1), M.core_orb())
    yolk.span((-2.5, 16, 7.1), (2.5, 19, 7.6), M.core_orb())
    yolk.span((7.1, 6, -3), (7.6, 12, 3), M.gold_star())
    yolk.span((-7.6, 11, -2), (-7.1, 16, 2), M.gold_star())
    return m


def feather_dart() -> Model:
    m = Model("geometry.wrong_hatch.feather_dart", scale=1.0, td=1.0, seed="dart")
    m.bone("root", (0, 0, 0))
    b = m.bone("body", (0, 1, 0), "root")
    fm = M.feather(along="u")
    b.span((-0.6, 0.0, -6), (0.6, 3.0, 4), fm)
    b.span((-0.5, 0.4, -9), (0.5, 2.6, -6), fm)
    b.span((-0.4, 0.9, -11), (0.4, 2.1, -9), M.solid("fff1a6", alpha=0, bevel=False))
    b.span((-0.5, 0.6, 4), (0.5, 2.4, 7), fm)
    return m


ALL = {"chick": chick, "egg": egg, "brood_shell": brood_shell, "feather_dart": feather_dart}

if __name__ == "__main__":
    import sys
    from preview import turnaround
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    for name, fn in ALL.items():
        mm = fn()
        for v in range(3):
            turnaround(mm, mm.paint(v), f"{out}/{name}_{v}.png", size=200)
        print(name, mm.stats())
    _ = (np, hx)
