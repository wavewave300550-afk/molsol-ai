"""
vesper_model.py - VESPER-0, The Ship That Learned to Pray.

Full-scale skeletal model: ~25.5 blocks long (snout to fluke), ~16.5 blocks tall
(ring A + spires).  Front = -Z.  Model -X is the boss's right side ("r" bones),
+X its left side ("l" bones).

Silhouette: an extraterrestrial whale skeleton turned cathedral-ship.  A long tapered
armoured skull with bone jaws; an elliptical ribcage of external white ribs with
armour panels (stained-glass scripture windows) between them and an open belly
showing the artificial sun inside; a tapering vertebral tail with wide flukes;
solar-sail flippers; three eyed gyroscopic rings (Ophanim).  Six mechanical limbs
are folded away inside the hull until Phase II.
"""
from __future__ import annotations

import math

import geo
import tex
from geo import Model, AtlasLayout, S, U

# ----------------------------------------------------------------------------- materials

ARMOR = S("armor", 0.5)
GLYPH = S("glyph", 0.5)
GOLD = S("gold", 0.5)
FLESH = S("flesh", 0.5)
BONE = S("bone", 0.5)
MACH = S("machine", 0.5)
RING = S("ring", 0.5)
SUN = S("sun", 0.75)
LIGHT = S("light", 0.5)
MAW = S("maw", 0.5)
LIMB = S("limb", 0.5)
SAIL = S("sail", 0.5)
CENSER = S("censer", 0.75)
DARK = S("dark", 0.5)
EYE = U(tex.eye(1), "eye", 1.0)

GLOW_SOFT = S("glow_soft", 1.0)      # sun corona: gold (P1) / violet (P2)
GLOW_HOLY = S("glow_holy", 1.0)      # holy light: cyan (P1) / magenta-violet (P2)
GLOW_STRIP = S("glow_strip", 1.0)
GLOW_GLYPH = S("glow_glyph", 1.0)
SHIELD = S("shield_hex", 0.2)

SIDE = {"r": -1.0, "l": 1.0}          # r = model -X (entity right), l = model +X
OUT_FACE = {"r": "east", "l": "west"}  # outward-facing side face (Bedrock east = model -X)

HULL_C = 66.0           # hull ellipse centre (y)
HULL_A = 72.0           # half width
HULL_B = 60.0           # half height
RIBS = [(-62, 0.80), (-38, 0.95), (-14, 1.0), (10, 1.0), (34, 0.92), (56, 0.78)]
SUN_C = (0.0, 62.0, -2.0)


def build_atlases():
    main = AtlasLayout(512, 256)
    main.add_swatch("armor", 256, 128, tex.armor(11))
    main.add_swatch("flesh", 128, 128, tex.flesh(7))
    main.add_swatch("bone", 128, 64, tex.bone_tex(5))
    main.add_swatch("machine", 128, 64, tex.machine(9))
    main.add_swatch("limb", 128, 64, tex.limb(23))
    main.add_swatch("sail", 128, 64, tex.sail(29))
    main.add_swatch("sun", 64, 64, tex.sun(17))
    main.add_swatch("maw", 64, 64, tex.maw(19))
    main.add_swatch("censer", 64, 64, tex.censer_tex(31))
    main.add_swatch("gold", 128, 32, tex.gold_trim(3))
    main.add_swatch("ring", 128, 32, tex.ring_band(13))
    main.add_swatch("glyph", 128, 16, tex.glyph_strip(43))
    main.add_swatch("dark", 32, 32, tex.dark(37))
    main.add_swatch("light", 32, 16, tex.light())
    glow = AtlasLayout(128, 128)
    glow.add_swatch("glow_soft", 64, 64, tex.tinted(tex.glow_soft, "fff0c0", "c27bff"))
    glow.add_swatch("glow_holy", 64, 64, tex.tinted(tex.glow_soft, "7de9ff", "e06bff"))
    glow.add_swatch("glow_strip", 64, 16, tex.tinted(tex.glow_strip, "8cefff", "c47dff"))
    glow.add_swatch("glow_glyph", 64, 16, tex.tinted(tex.glow_glyph, "b8f6ff", "d79bff"))
    shield = AtlasLayout(64, 64)
    shield.add_swatch("shield_hex", 64, 64, tex.shield_hex)
    return main, glow, shield


def ell(phi_deg, scale, inset=0.0, side=1.0):
    """Point on the hull ellipse (XY) at angle phi (90 = top, -90 = bottom)."""
    p = math.radians(phi_deg)
    return (side * (HULL_A * scale - inset) * math.cos(p), HULL_C + (HULL_B * scale - inset) * math.sin(p))


def arc_panel(m: Model, bone, side, z, scale, phi0, phi1, n, thick, length_z, mat, inset=0.0, layer="main",
              face_mats=None):
    """Curved panel following the hull ellipse between phi0 > phi1 at depth z."""
    cubes = []
    for k in range(n):
        a = phi0 + (phi1 - phi0) * k / n
        b = phi0 + (phi1 - phi0) * (k + 1) / n
        xa, ya = ell(a, scale, inset, side)
        xb, yb = ell(b, scale, inset, side)
        mid = ((xa + xb) / 2, (ya + yb) / 2, z)
        tangent = geo.v_norm((xb - xa, yb - ya, 0.0))
        normal = (tangent[1], -tangent[0], 0.0)
        if geo.v_dot(normal, (mid[0], mid[1] - HULL_C, 0.0)) < 0:
            normal = geo.v_mul(normal, -1)
        seg = math.hypot(xb - xa, yb - ya) + thick * 0.6
        ez = (0.0, 0.0, 1.0)
        ex = tangent
        ey = geo.v_cross(ez, ex)
        cubes.append(m.obox(bone, mid, (ex, ey, ez), (seg, thick, length_z), mat, layer=layer, face_mats=face_mats))
    return cubes


# ----------------------------------------------------------------------------- body parts

def skull(m: Model):
    m.bone("neck_2", (0, 72, -66), "body")
    m.bone("neck_1", (0, 72, -76), "neck_2")
    m.bone("skull", (0, 72, -82), "neck_1")
    # neck: vertebra + gold collar
    m.box("neck_2", (0, 72, -71), (44, 44, 12), BONE)
    m.ring("neck_2", (0, 72, -72), 30, "z", 10, 7, 6, GOLD)
    m.box("neck_1", (0, 70, -79), (36, 36, 8), FLESH)
    # cranium (rear -> snout)
    m.box("skull", (0, 76, -100), (64, 58, 36), ARMOR, face_mats={"south": DARK})
    m.box("skull", (0, 73, -134), (56, 50, 34), ARMOR)
    m.box("skull", (0, 69, -165), (44, 40, 30), ARMOR)
    m.box("skull", (0, 65, -188), (30, 30, 18), ARMOR)
    m.box("skull", (0, 63, -199), (18, 18, 6), GOLD)
    # sloped forehead plates
    m.beam("skull", (0, 106, -84), (0, 99, -120), 58, 8, ARMOR, extend=2)
    m.beam("skull", (0, 99, -120), (0, 90, -152), 50, 8, ARMOR, extend=2)
    m.beam("skull", (0, 90, -152), (0, 80, -194), 32, 8, ARMOR, extend=2)
    # crest blade with scripture
    m.beam("skull", (0, 112, -88), (0, 99, -156), 5, 18, ARMOR, extend=1)
    m.beam("skull", (0, 121.5, -88), (0, 108.5, -156), 7, 3, GOLD, extend=1)
    m.beam("skull", (0, 112, -88), (0, 99, -156), 5.6, 4, GLYPH, extend=-4)
    # frontal visor band with eyes
    m.box("skull", (0, 91.5, -151.6), (50, 7, 1.5), LIGHT)
    for k, x in enumerate((-14, 0, 14)):
        m.box("skull", (x, 91.5, -152.2), (9, 9, 2), DARK, face_mats={"north": EYE})
    for s in ("r", "l"):
        x = SIDE[s]
        # brow ridge
        m.beam("skull", (x * 30, 104, -86), (x * 25, 97, -134), 6, 6, GOLD, extend=2)
        m.beam("skull", (x * 25, 97, -134), (x * 19, 86, -172), 5, 5, GOLD, extend=2)
        # slanted cheek walls: wedge the stacked cranium into a tapering whale skull
        m.beam("skull", (x * 31, 70, -84), (x * 22, 64, -184), 5, 44, ARMOR, up=(0, 1, 0), extend=2)
        m.beam("skull", (x * 33.5, 92, -86), (x * 23, 84, -172), 4, 6, GOLD, extend=1)
        # Ophanim eye cluster on the cheek (outside the slanted wall)
        for (y, z, sz) in ((80, -112, 14), (80, -132, 12), (66, -122, 10), (72, -150, 9)):
            t = (z + 84) / -100.0
            m.box("skull", (x * (31.5 - 9 * t + 2.2), y, z), (2.6, sz, sz + 2), DARK, face_mats={OUT_FACE[s]: EYE})
        m.box("skull", (x * 26.2, 58, -150), (1.2, 3, 50), LIGHT)
        # cheek armour over the jaw hinge
        m.box("skull", (x * 33, 62, -100), (6, 26, 30), ARMOR)
        m.box("skull", (x * 33.4, 48.5, -100), (6, 3, 30), GOLD)
        # swept antenna horns
        m.beam("skull", (x * 22, 104, -94), (x * 38, 146, -56), 7, 7, GOLD)
        m.beam("skull", (x * 38, 146, -56), (x * 42, 158, -44), 4, 4, LIGHT)
        m.locator("skull", f"horn_{s}", (x * 42, 160, -42))
    m.locator("skull", "prow", (0, 64, -206))
    m.locator("skull", "eyes", (0, 92, -156))
    # mandibles: long whale jaw bones (split wide in phase II)
    for s in ("r", "l"):
        x = SIDE[s]
        b = f"mandible_{s}"
        m.bone(b, (x * 24, 50, -88), "skull")
        m.beam(b, (x * 24, 50, -88), (x * 14, 42, -210), 12, 14, BONE, extend=3)
        m.beam(b, (x * 19, 54, -110), (x * 11, 47, -206), 4, 5, GOLD)
        m.box(b, (x * 13, 42, -214), (10, 12, 8), GOLD)
        for k in range(5):
            zt = -124 - k * 18
            m.box(b, (x * (15.5 - k * 0.8), 54, zt), (3, 5, 4), S("bone", 1.0))
        m.box(b, (x * 27, 50, -96), (8, 16, 16), MACH)
    m.bone("maw", (0, 56, -100), "skull")
    m.box("maw", (0, 52, -142), (30, 10, 96), MAW)
    m.locator("maw", "jaw", (0, 50, -196))


def thorax(m: Model):
    m.bone("spine", (0, 128, -66), "body")
    m.beam("spine", (0, 128, -74), (0, 127, 70), 10, 8, BONE)
    m.beam("spine", (0, 132.5, -70), (0, 131.5, 66), 6, 1.5, GLYPH)
    for (z, sc) in RIBS:
        m.box("spine", (0, 127 + 4 * sc, z), (18, 14, 12), BONE)
        m.box("spine", (0, 127 + 4 * sc, z), (20, 4, 14), GOLD)
    # gothic spires between the ribs
    for i, (z, hgt) in enumerate(((-50, 52), (-26, 72), (-2, 64), (22, 46)), start=1):
        b = f"spire_{i}"
        m.bone(b, (0, 132, z), "spine", rotation=(-10, 0, 0))
        m.box(b, (0, 137, z), (16, 10, 16), ARMOR)
        m.box(b, (0, 142 + (hgt - 22) / 2, z), (9, hgt - 22, 9), ARMOR)
        m.box(b, (0, 146, z), (12, 3, 12), GOLD)
        m.box(b, (0, 142 + hgt - 22 - 4, z), (11, 3, 11), GOLD)
        m.box(b, (0, 142 + hgt - 22 + 4, z), (5, 12, 5), LIGHT)
        m.box(b, (0, 142 + hgt - 22 + 4, z), (10, 18, 10), GLOW_HOLY, layer="glow")
        m.locator(b, f"spire_tip_{i}", (0, 142 + hgt - 12, z))
    # ribs (external, cathedral buttresses)
    for i, (z, sc) in enumerate(RIBS, start=1):
        for s in ("r", "l"):
            x = SIDE[s]
            b = f"rib_{s}{i}"
            top = ell(86, sc, 0, x)
            m.bone(b, (top[0], top[1], z), "body")
            prev = None
            for phi in (86, 66, 46, 26, 6, -14, -34, -54, -76):
                p = ell(phi, sc, -3, x)
                if prev is not None:
                    m.beam(b, (prev[0], prev[1], z), (p[0], p[1], z), 10, 9, BONE, extend=2.5)
                prev = p
            gx, gy = ell(6, sc, -6, x)
            m.box(b, (gx, gy, z), (8, 10, 11), GOLD)
    # armour panels between ribs (blow off in phase II) + organic lining (stays)
    for g in range(len(RIBS) - 1):
        z0, s0 = RIBS[g]
        z1, s1 = RIBS[g + 1]
        zm, sm = (z0 + z1) / 2, (s0 + s1) / 2
        gap = (z1 - z0) - 6
        for s in ("r", "l"):
            x = SIDE[s]
            b = f"plate_{s}{g + 1}"
            pv = ell(88, sm, 0, x)
            m.bone(b, (pv[0], pv[1], zm), "body")
            arc_panel(m, b, x, zm, sm, 88, -8, 5, 5, gap + 2, ARMOR, inset=1)
            # stained-glass scripture window + gold sill
            wx, wy = ell(42, sm, -1.5, x)
            ex = geo.v_norm((x * math.sin(math.radians(42)) * HULL_A, -math.cos(math.radians(42)) * HULL_B, 0))
            ez = (0.0, 0.0, 1.0)
            ey = geo.v_cross(ez, ex)
            m.obox(b, (wx, wy, zm), (ex, ey, ez), (26, 1.5, gap - 4), GLYPH)
            sx, sy = ell(-7, sm, -1, x)
            m.box(b, (sx, sy, zm), (6, 4, gap + 2), GOLD)
            # organic lining under the panels (dark flesh with veins)
            arc_panel(m, "body", x, zm, sm, 90, -40, 5, 4, gap + 6, FLESH, inset=9)
    # keel (ventral spine) + censers
    m.bone("keel", (0, 6, -2), "body")
    m.beam("keel", (0, 8, -70), (0, 7, 66), 14, 10, BONE)
    m.beam("keel", (0, 2.5, -66), (0, 2, 62), 6, 3, GOLD)
    for i, z in enumerate((-30, -2, 26), start=1):
        b = f"censer_{i}"
        m.bone(b, (0, 2, z), "keel")
        m.box(b, (0, -9, z), (2, 22, 2), GOLD)
        m.box(b, (0, -22, z), (9, 4, 9), GOLD)
        m.box(b, (0, -31, z), (13, 15, 13), CENSER)
        m.box(b, (0, -40.5, z), (5, 4, 5), GOLD)
        m.box(b, (0, -31, z), (22, 22, 22), GLOW_SOFT, layer="glow")
        m.locator(b, f"censer_{i}", (0, -31, z))
    m.locator("keel", "belly", (0, -2, -2))


def reactor(m: Model):
    m.bone("reactor", SUN_C, "body")
    m.bone("sun", SUN_C, "reactor")
    m.box("sun", SUN_C, (34, 34, 34), SUN)
    m.box("sun", SUN_C, (30, 30, 30), SUN, rotation=(45, 45, 0))
    m.box("sun", SUN_C, (30, 30, 30), SUN, rotation=(0, 45, 45))
    m.box("sun", SUN_C, (54, 54, 54), GLOW_SOFT, layer="glow")
    m.box("sun", SUN_C, (72, 72, 72), GLOW_SOFT, rotation=(45, 0, 45), layer="glow")
    m.box("sun", SUN_C, (108, 108, 108), GLOW_SOFT, rotation=(0, 45, 0), layer="glow")
    m.locator("sun", "core", SUN_C)
    # gyroscopic containment rings ("wheels within wheels")
    m.bone("cage_1", SUN_C, "reactor", rotation=(0, 0, 30))
    m.ring("cage_1", SUN_C, 30, "x", 14, 3, 3, GOLD)
    m.bone("cage_2", SUN_C, "reactor", rotation=(30, 0, 0))
    m.ring("cage_2", SUN_C, 34, "y", 16, 3, 3, GOLD)
    # suspension struts from the spine
    for (x, z) in ((-8, -14), (8, -14), (-8, 10), (8, 10)):
        m.beam("reactor", (x, 124, z), (x * 2.2, 84, z * 1.4), 4, 4, GOLD)


def fins_and_engines(m: Model):
    for s in ("r", "l"):
        x = SIDE[s]
        b = f"fin_{s}"
        m.bone(b, (x * 60, 54, -46), "body", rotation=(0, 0, x * 14))
        m.box(b, (x * 60, 54, -46), (18, 20, 20), GOLD)
        segs = [((60, 54, -46), (104, 46, -38), 12, 46), ((104, 46, -38), (146, 38, -28), 10, 34),
                ((146, 38, -28), (184, 31, -16), 7, 20)]
        parent = "body"
        for k, (p0, p1, arm, chord) in enumerate(segs):
            bn = b if k == 0 else f"fin_{s}_{'blade' if k == 1 else 'tip'}"
            P0 = (x * p0[0], p0[1], p0[2])
            P1 = (x * p1[0], p1[1], p1[2])
            if k > 0:
                m.bone(bn, P0, prev)
                m.box(bn, P0, (arm + 3, arm + 3, arm + 3), GOLD)
            m.beam(bn, P0, P1, arm, arm - 2, BONE, extend=2)
            d = geo.v_norm(geo.v_sub(P1, P0))
            mid = geo.v_mul(geo.v_add(P0, P1), 0.5)
            ex, ez = d, (0.0, 0.0, 1.0)
            ey = geo.v_norm(geo.v_cross(ez, ex))
            ez = geo.v_cross(ex, ey)
            cen = geo.v_add(mid, (0, 0, chord / 2 + arm / 2 - 2))
            span = geo.v_len(geo.v_sub(P1, P0))
            m.obox(bn, cen, (ex, ey, ez), (span, 3, chord), SAIL)
            m.obox(bn, geo.v_add(cen, (0, 0, chord / 2)), (ex, ey, ez), (span, 4, 3), GOLD)
            m.obox(bn, cen, (ex, ey, ez), (span + 2, 2, chord + 4), GLOW_STRIP, layer="glow")
            prev = bn
        m.beam(prev, (x * 184, 31, -16), (x * 192, 29, -12), 4, 4, LIGHT)
        m.locator(prev, f"fin_tip_{s}", (x * 192, 29, -12))
        # ion engine nacelle under the tail root
        e = f"engine_{s}"
        m.bone(e, (x * 40, 38, 62), "body")
        m.box(e, (x * 40, 38, 84), (22, 22, 52), MACH)
        m.box(e, (x * 40, 38, 82), (21, 21, 46), ARMOR, rotation=(0, 0, 45))
        m.box(e, (x * 40, 38, 58), (26, 26, 6), GOLD)
        m.box(e, (x * 40, 38, 110.5), (15, 15, 2), LIGHT)
        m.box(e, (x * 40, 38, 116), (26, 26, 12), GLOW_HOLY, layer="glow")
        m.beam(e, (x * 22, 50, 66), (x * 38, 42, 70), 7, 7, BONE)
        m.locator(e, f"exhaust_{s}", (x * 40, 38, 118))


TAIL = [  # pivot z, centre z, w, h, d, y
    (64, 76, 66, 56, 26, 66),
    (89, 99, 54, 46, 24, 66),
    (111, 120, 42, 37, 22, 65),
    (131, 139, 32, 29, 20, 64),
    (148, 156, 24, 22, 18, 63),
    (164, 171, 17, 16, 16, 62),
]


def tail(m: Model):
    parent = "body"
    for i, (pz, cz, w, h, d, y) in enumerate(TAIL, start=1):
        b = f"tail_{i}"
        m.bone(b, (0, y, pz), parent)
        m.box(b, (0, y + h * 0.2, cz), (w, h * 0.6, d), ARMOR)
        m.box(b, (0, y - h * 0.25, cz), (w - 8, h * 0.5, d - 3), BONE)
        m.box(b, (0, y - h * 0.1, cz), (w - 12, h * 0.4, d + 1), FLESH, faces=("east", "west", "down"))
        m.box(b, (0, y, pz + 1.5), (w + 4, h + 3, 3), GOLD)
        m.beam(b, (0, y + h * 0.5, cz - 6), (0, y + h * 0.5 + 14 - i, cz + 7), 4, 3, BONE)
        m.box(b, (0, y + h * 0.5 + 0.6, cz), (4, 1.4, d - 4), LIGHT)
        parent = b
    for s in ("r", "l"):
        x = SIDE[s]
        b = f"fluke_{s}"
        m.bone(b, (x * 8, 62, 172), "tail_6", rotation=(0, -x * 18, 0))
        m.box(b, (x * 42, 62, 182), (68, 6, 30), SAIL)
        m.box(b, (x * 42, 62, 167), (68, 7, 3), GOLD)
        m.box(b, (x * 42, 62, 197.5), (64, 2, 2), LIGHT)
        m.box(b, (x * 42, 62, 200), (68, 3, 6), GLOW_STRIP, layer="glow")
        m.box(b, (x * 78, 62, 190), (12, 5, 30), SAIL, rotation=(0, -x * 25, 0))
        m.box(b, (x * 8, 62, 178), (10, 10, 16), GOLD)
    m.locator("tail_6", "tail_tip", (0, 62, 206))


LIMBS = {
    # id: (side, attach z, splay deg (forward - / back +))
    "fr": ("r", -36, -26), "fl": ("l", -36, -26),
    "mr": ("r", -2, 0), "ml": ("l", -2, 0),
    "rr": ("r", 30, 26), "rl": ("l", 30, 26),
}


def limb_points(side, z, splay):
    x = SIDE[side]
    sp = math.radians(splay)

    def P(out, y, dz=0.0):
        return (x * (34 + out * math.cos(sp)), y, z + out * math.sin(sp) + dz)
    hip = (x * 34, 20, z)
    knee = P(56, 58)
    ankle = P(86, -30)
    tip = P(80, -72, -10)
    return hip, knee, ankle, tip


def limbs(m: Model):
    for lid, (s, z, splay) in LIMBS.items():
        hip, knee, ankle, tip = limb_points(s, z, splay)
        c, f, t, k = (f"limb_{lid}_{p}" for p in ("coxa", "femur", "tibia", "talon"))
        m.bone(c, hip, "body")
        m.bone(f, hip, c)
        m.bone(t, knee, f)
        m.bone(k, ankle, t)
        m.box(c, hip, (18, 18, 18), MACH)
        m.box(c, hip, (21, 6, 21), GOLD)
        m.beam(f, hip, knee, 13, 13, LIMB, extend=3)
        m.beam(f, geo.v_add(hip, (0, 9, 0)), geo.v_add(knee, (0, 9, 0)), 4, 4, FLESH)
        m.box(t, knee, (15, 15, 15), MACH)
        m.box(t, knee, (17, 5, 17), GOLD)
        m.beam(t, knee, ankle, 10, 10, LIMB, extend=2)
        m.box(k, ankle, (11, 11, 11), GOLD)
        m.beam(k, ankle, tip, 6, 12, ARMOR, extend=1)
        m.beam(k, geo.v_add(tip, (0, 9, 4)), tip, 3, 6, GOLD, extend=2)
        m.locator(k, f"talon_{lid}", tip)


RINGS = {
    # name: (centre, radius, segments, radial, depth, rest rotation, eyes)
    "a": ((0, 64, -2), 132, 24, 10, 8, (0, 0, 0), 6),
    "b": ((0, 72, -128), 76, 18, 8, 7, (22, 0, 0), 4),
    "c": ((0, 64, 122), 62, 16, 7, 6, (-18, 0, 0), 3),
}


def rings(m: Model):
    for name, (c, r, n, rad, dep, rot, eyes) in RINGS.items():
        o = f"ring_{name}"
        sp = f"ring_{name}_spin"
        m.bone(o, c, "body", rotation=rot)
        m.bone(sp, c, o)
        m.ring(sp, c, r, "z", n, rad, dep, RING)
        m.ring(sp, c, r - rad / 2 - 1.2, "z", n, 2.5, dep + 0.8, GOLD)
        m.ring(sp, c, r, "z", n, rad + 5, 2.0, GLOW_GLYPH, layer="glow")
        if name == "a":   # solar crown spikes
            for k in range(12):
                th = math.radians(15 + 30 * k)
                radial = (math.cos(th), math.sin(th), 0.0)
                p0 = geo.v_add(c, geo.v_mul(radial, r + rad / 2))
                p1 = geo.v_add(c, geo.v_mul(radial, r + rad / 2 + (16 if k % 2 else 9)))
                m.beam(sp, p0, p1, 4, 3, GOLD, up=(0, 0, 1))
        for e in range(eyes):
            th = math.radians(360.0 / eyes * e + 90)
            p = (c[0] + r * math.cos(th), c[1] + r * math.sin(th), c[2])
            tangent = (-math.sin(th), math.cos(th), 0.0)
            radial = (math.cos(th), math.sin(th), 0.0)
            m.obox(sp, p, (tangent, radial, (0, 0, 1)), (rad + 6, rad + 6, dep + 4), GOLD,
                   face_mats={"north": EYE, "south": EYE})
        m.locator(sp, f"ring_{name}", (c[0], c[1] + r, c[2]))


def shield(m: Model):
    m.bone("shield", SUN_C, "body")
    m.box("shield", SUN_C, (210, 190, 440), SHIELD, layer="shield")
    m.box("shield", SUN_C, (250, 160, 300), SHIELD, rotation=(0, 45, 0), layer="shield")
    m.box("shield", SUN_C, (180, 230, 330), SHIELD, rotation=(30, 0, 0), layer="shield")


def build() -> tuple:
    m = Model("geometry.sab.vesper_0", tex_size=(512, 256), glow_tex_size=(128, 128), shield_tex_size=(64, 64))
    m.bone("root", (0, 0, 0))
    m.bone("body", SUN_C, "root")
    skull(m)
    thorax(m)
    reactor(m)
    fins_and_engines(m)
    tail(m)
    limbs(m)
    rings(m)
    shield(m)
    m.bounds = (34.0, 24.0, (0.0, 4.0, 0.0))
    main, glow, shield_atlas = build_atlases()
    m.map_uvs(main, "main")
    m.map_uvs(glow, "glow")
    m.map_uvs(shield_atlas, "shield")
    return m, main, glow, shield_atlas


LIMB_BONES = [f"limb_{lid}_{part}" for lid in LIMBS for part in ("coxa", "femur", "tibia", "talon")]
PLATE_BONES = [f"plate_{s}{i}" for s in "rl" for i in range(1, len(RIBS))]
RING_BONES = [f"ring_{n}{suffix}" for n in "abc" for suffix in ("", "_spin")]
CENSER_BONES = [f"censer_{i}" for i in range(1, 4)]
