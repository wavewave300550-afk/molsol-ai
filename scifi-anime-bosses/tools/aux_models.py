"""
aux_models.py - helper entities of the VESPER-0 encounter.

All of them map onto the boss's own atlases (main / glow), so the game loads no extra
textures for them.  Sizes are in model units (1/16 block); front = -Z.
"""
from __future__ import annotations

import math

import geo
from geo import Model
from vesper_model import (ARMOR, BONE, CENSER, DARK, EYE, FLESH, GLOW_GLYPH, GLOW_SOFT, GLOW_STRIP, GLYPH,
                          GOLD, LIGHT, MACH, RING, SAIL, SUN)


def _finish(m: Model, main, glow, bounds):
    m.bounds = bounds
    m.map_uvs(main, "main")
    if m.layers() and "glow" in m.layers():
        m.map_uvs(glow, "glow")
    return m


def cherub(main, glow) -> Model:
    """Autonomous drone: an eye inside a gold octahedron, four blade wings and a halo."""
    m = Model("geometry.sab.cherub", tex_size=(512, 256), glow_tex_size=(128, 64))
    m.bone("root", (0, 0, 0))
    m.bone("body", (0, 12, 0), "root")
    m.box("body", (0, 12, 0), (9, 9, 9), ARMOR)
    m.box("body", (0, 12, 0), (8, 8, 8), GOLD, rotation=(45, 0, 45))
    m.box("body", (0, 12, -4.4), (6, 6, 1.4), DARK, face_mats={"north": EYE})
    m.box("body", (0, 12, -5), (12, 12, 6), GLOW_SOFT, layer="glow")
    m.box("body", (0, 5, 0), (3, 5, 3), GOLD)
    m.box("body", (0, 2, 0), (2, 3, 2), LIGHT)
    # two pairs of swept angelic blade-wings (upper long, lower short)
    for i, (side, up, length, rise) in enumerate((("r", 1, 18, 9), ("l", 1, 18, 9), ("r", -1, 11, -6), ("l", -1, 11, -6))):
        x = -1 if side == "r" else 1
        b = f"wing_{i + 1}"
        root = (x * 4, 12 + up * 2, 2)
        m.bone(b, root, "body")
        tip = (x * (4 + length), 12 + up * 2 + rise, 9)
        m.beam(b, root, tip, 2, 6 if up > 0 else 4, SAIL, up=(0, 0, 1))
        m.beam(b, geo.v_add(root, (0, 0, 2)), geo.v_add(tip, (0, 0, 2)), 2.4, 1.2, GOLD, up=(0, 0, 1))
        m.beam(b, geo.v_add(root, (0, 0, -1)), geo.v_add(tip, (0, 0, -1)), 1, 1, LIGHT, up=(0, 0, 1))
    m.bone("halo", (0, 24, 0), "body")
    m.ring("halo", (0, 24, 0), 7, "y", 10, 1.6, 1.4, GOLD)
    m.ring("halo", (0, 24, 0), 7, "y", 10, 3.0, 0.6, GLOW_STRIP, layer="glow")
    m.locator("body", "muzzle", (0, 12, -7))
    return _finish(m, main, glow, (2.0, 2.5, (0, 0.8, 0)))


def plasma_orb(main, glow) -> Model:
    m = Model("geometry.sab.plasma_orb", tex_size=(512, 256), glow_tex_size=(128, 64))
    m.bone("root", (0, 0, 0))
    m.bone("core", (0, 4, 0), "root")
    m.box("core", (0, 4, 0), (6, 6, 6), SUN)
    m.box("core", (0, 4, 0), (5, 5, 5), SUN, rotation=(45, 45, 0))
    m.box("core", (0, 4, 0), (11, 11, 11), GLOW_SOFT, layer="glow")
    m.box("core", (0, 4, 0), (12, 12, 12), GLOW_SOFT, rotation=(45, 45, 0), layer="glow")
    m.box("core", (0, 4, 0), (12, 12, 12), GLOW_SOFT, rotation=(0, 45, 45), layer="glow")
    return _finish(m, main, glow, (1.5, 1.5, (0, 0.25, 0)))


def censer(main, glow) -> Model:
    """Prayer node: a floating thurible with a spinning ring and incense core."""
    m = Model("geometry.sab.censer", tex_size=(512, 256), glow_tex_size=(128, 64))
    m.bone("root", (0, 0, 0))
    m.bone("body", (0, 16, 0), "root")
    m.box("body", (0, 40, 0), (2, 26, 2), GOLD)
    m.box("body", (0, 27, 0), (12, 4, 12), GOLD)
    m.box("body", (0, 24, 0), (8, 3, 8), GOLD, rotation=(0, 45, 0))
    m.box("body", (0, 15, 0), (16, 18, 16), CENSER)
    m.box("body", (0, 15, 0), (14, 16, 14), CENSER, rotation=(0, 45, 0))
    m.box("body", (0, 4.5, 0), (6, 4, 6), GOLD)
    m.box("body", (0, 1.5, 0), (3, 3, 3), LIGHT)
    m.box("body", (0, 15, 0), (28, 28, 28), GLOW_SOFT, layer="glow")
    m.bone("ring", (0, 15, 0), "body", rotation=(20, 0, 0))
    m.ring("ring", (0, 15, 0), 15, "y", 12, 2.5, 2, RING)
    m.ring("ring", (0, 15, 0), 15, "y", 12, 4, 0.8, GLOW_GLYPH, layer="glow")
    for e in range(3):
        th = math.radians(120 * e)
        p = (15 * math.cos(th), 15, 15 * math.sin(th))
        tangent = (-math.sin(th), 0.0, math.cos(th))
        radial = (math.cos(th), 0.0, math.sin(th))
        m.obox("ring", p, (tangent, (0, 1, 0), radial), (5, 5, 4), GOLD, face_mats={"south": EYE, "north": EYE})
    m.locator("body", "incense", (0, 28, 0))
    return _finish(m, main, glow, (2.5, 3.5, (0, 1.5, 0)))


SERAPH = {"a": (64, 18, 9, 7), "b": (48, 16, 8, 6), "c": (34, 12, 7, 5)}   # radius, segments, radial, depth


def seraph(main, glow) -> Model:
    """Detached Ophanim ring: rim + light spokes + central eye hub. Variant chosen by bone visibility."""
    m = Model("geometry.sab.seraph", tex_size=(512, 256), glow_tex_size=(128, 64))
    m.bone("root", (0, 0, 0))
    m.bone("tilt", (0, 16, 0), "root")
    m.bone("spin", (0, 16, 0), "tilt")
    c = (0, 16, 0)
    m.box("spin", c, (12, 12, 12), ARMOR)
    m.box("spin", c, (11, 11, 11), GOLD, rotation=(45, 45, 0))
    m.box("spin", (0, 16, -6.4), (8, 8, 1.4), DARK, face_mats={"north": EYE})
    m.box("spin", (0, 16, 6.4), (8, 8, 1.4), DARK, face_mats={"south": EYE})
    m.box("spin", c, (22, 22, 22), GLOW_SOFT, layer="glow")
    for name, (r, n, rad, dep) in SERAPH.items():
        b = f"rim_{name}"
        m.bone(b, c, "spin")
        m.ring(b, c, r, "z", n, rad, dep, RING)
        m.ring(b, c, r - rad / 2 - 1, "z", n, 2, dep + 0.6, GOLD)
        m.ring(b, c, r, "z", n, rad + 4, 1.6, GLOW_GLYPH, layer="glow")
        for k in range(6):
            th = math.radians(60 * k + 30)
            p1 = (r * math.cos(th), 16 + r * math.sin(th), 0)
            m.beam(b, c, p1, 2.5, 2.5, GLOW_STRIP, up=(0, 0, 1), layer="glow")
            m.beam(b, geo.v_add(c, geo.v_mul((math.cos(th), math.sin(th), 0), 8)),
                   geo.v_add(c, geo.v_mul((math.cos(th), math.sin(th), 0), r - rad / 2)), 1.5, 1.5, GOLD,
                   up=(0, 0, 1))
        for e in range(4):
            th = math.radians(90 * e)
            p = (r * math.cos(th), 16 + r * math.sin(th), 0)
            tangent = (-math.sin(th), math.cos(th), 0.0)
            radial = (math.cos(th), math.sin(th), 0.0)
            m.obox(b, p, (tangent, radial, (0, 0, 1)), (rad + 5, rad + 5, dep + 3), GOLD,
                   face_mats={"north": EYE, "south": EYE})
    m.locator("spin", "hub", c)
    return _finish(m, main, glow, (9.0, 9.0, (0, 1.0, 0)))


def hull_plate(main, glow) -> Model:
    """Fallen armour plate embedded in the ground (Phase II cover)."""
    m = Model("geometry.sab.hull_plate", tex_size=(512, 256), glow_tex_size=(128, 64))
    m.bone("root", (0, 0, 0))
    m.bone("slab", (0, 0, 0), "root", rotation=(14, 0, 4))
    m.box("slab", (0, 30, 0), (46, 66, 9), ARMOR)
    m.box("slab", (0, 30, 5), (38, 58, 2), FLESH, faces=("south",))
    m.box("slab", (0, 63.5, 0), (48, 3, 10), GOLD)
    m.box("slab", (-23.5, 30, 0), (3, 66, 10), GOLD)
    m.box("slab", (23.5, 30, 0), (3, 66, 10), GOLD)
    m.box("slab", (0, 40, -4.8), (30, 3, 1), GLYPH)
    m.box("slab", (8, 18, -5), (10, 12, 1.5), DARK)
    m.bone("rubble", (0, 0, 0), "root")
    for (x, z, s, r) in ((-20, -10, 12, 20), (18, -12, 10, -35), (-8, 14, 14, 50), (22, 10, 9, 10), (2, -18, 8, 70)):
        m.box("rubble", (x, s / 2 - 3, z), (s, s, s), ARMOR if s > 10 else BONE, rotation=(r * 0.4, r, r * 0.2))
    m.box("rubble", (0, -1, 0), (52, 4, 40), DARK)
    m.bone("cracks", (0, 0, 0), "slab")
    m.box("cracks", (0, 30, 0), (47, 67, 10), GLOW_STRIP, layer="glow")
    m.locator("slab", "top", (0, 66, 0))
    return _finish(m, main, glow, (4.0, 5.0, (0, 2.0, 0)))


def singularity(main, glow) -> Model:
    """Event Horizon: a black sphere with a violet accretion disk and a lensing ring."""
    m = Model("geometry.sab.singularity", tex_size=(512, 256), glow_tex_size=(128, 64))
    m.bone("root", (0, 0, 0))
    m.bone("core", (0, 24, 0), "root")
    m.box("core", (0, 24, 0), (18, 18, 18), DARK)
    m.box("core", (0, 24, 0), (16, 16, 16), DARK, rotation=(45, 45, 0))
    m.box("core", (0, 24, 0), (16, 16, 16), DARK, rotation=(0, 45, 45))
    m.bone("disk", (0, 24, 0), "core", rotation=(14, 0, 8))
    m.ring("disk", (0, 24, 0), 22, "y", 16, 10, 1.5, SUN)
    m.ring("disk", (0, 24, 0), 30, "y", 18, 8, 1.0, GLOW_STRIP, layer="glow")
    m.bone("lens", (0, 24, 0), "core")
    m.ring("lens", (0, 24, 0), 14, "z", 14, 3, 2, GLOW_GLYPH, layer="glow")
    m.box("lens", (0, 24, 0), (40, 40, 40), GLOW_SOFT, layer="glow")
    return _finish(m, main, glow, (5.0, 5.0, (0, 1.5, 0)))


LANCE_LEN = 512.0


def lance(main, glow) -> Model:
    """Litany Lance beam. Built along -Z for LANCE_LEN units; scaled on Z by the client."""
    m = Model("geometry.sab.lance", tex_size=(512, 256), glow_tex_size=(128, 64))
    m.bone("root", (0, 0, 0))
    m.bone("aim", (0, 0, 0), "root")
    m.bone("beam", (0, 0, 0), "aim")
    m.box("beam", (0, 0, -LANCE_LEN / 2), (5, 5, LANCE_LEN), LIGHT)
    m.box("beam", (0, 0, -LANCE_LEN / 2), (16, 16, LANCE_LEN), GLOW_STRIP, layer="glow")
    m.box("beam", (0, 0, -LANCE_LEN / 2), (16, 16, LANCE_LEN), GLOW_STRIP, rotation=(0, 0, 45), layer="glow")
    m.bone("rings", (0, 0, 0), "beam")
    for k in range(8):
        z = -24 - k * 64
        m.ring("rings", (0, 0, z), 12 - k * 0.6, "z", 10, 3, 2, GLOW_GLYPH, layer="glow")
    m.bone("muzzle", (0, 0, 0), "aim")
    m.box("muzzle", (0, 0, 0), (36, 36, 36), GLOW_SOFT, layer="glow")
    m.box("muzzle", (0, 0, 0), (12, 12, 12), SUN)
    return _finish(m, main, glow, (64.0, 64.0, (0, 0, 0)))


def orison_halo(main, glow) -> Model:
    """The thrown Orison Halo (player reward weapon)."""
    m = Model("geometry.sab.orison_halo", tex_size=(512, 256), glow_tex_size=(128, 64))
    m.bone("root", (0, 0, 0))
    m.bone("spin", (0, 6, 0), "root")
    m.ring("spin", (0, 6, 0), 9, "y", 12, 3, 2, RING)
    m.ring("spin", (0, 6, 0), 7, "y", 12, 1.2, 2.4, GOLD)
    m.ring("spin", (0, 6, 0), 9, "y", 12, 5, 0.8, GLOW_GLYPH, layer="glow")
    for e in range(3):
        th = math.radians(120 * e)
        p = (9 * math.cos(th), 6, 9 * math.sin(th))
        m.box("spin", p, (4, 4, 4), GOLD, rotation=(0, -math.degrees(th), 0), face_mats={"up": EYE})
    return _finish(m, main, glow, (1.5, 1.0, (0, 0.4, 0)))


def empty() -> Model:
    m = Model("geometry.sab.empty", tex_size=(16, 16))
    m.bone("root", (0, 0, 0))
    m.bounds = (1.0, 1.0, (0, 0.5, 0))
    return m


def build_all(main, glow):
    return {
        "cherub": cherub(main, glow),
        "plasma_orb": plasma_orb(main, glow),
        "censer": censer(main, glow),
        "seraph": seraph(main, glow),
        "hull_plate": hull_plate(main, glow),
        "singularity": singularity(main, glow),
        "lance": lance(main, glow),
        "orison_halo": orison_halo(main, glow),
        "empty": empty(),
    }
