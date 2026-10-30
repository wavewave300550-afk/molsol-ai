"""
The three Intelligent Beings of the 11th Dimension (+ minions), described with modelkit.

Every model is exported twice from one atlas:
    geometry.dim11.<name>        solid cubes      (material entity_alphatest)
    geometry.dim11.<name>.glow   energy cubes     (material entity_beam_additive)
Both share the full bone hierarchy, so one animation set drives both layers.

    archon     AEON-7, the Calabi-Yau Archon     - folded-space sovereign of the 7 hidden dimensions
    sovereign  The M5 Sovereign (Brane-Leviathan) - a living membrane that swims between universes
    observer   The Ophanim of the Eleventh Axis   - a hypercube of wheels and eyes that sees all timelines
    wisp       Closed-String Wisp                 - minion of the Sovereign
"""
import math

from modelkit import Model, hx, m_solid, m_gold, m_stripes
from shapes import (eye_decal, frame_cube, m_crystal, m_energy, m_feather_eye, m_glyph_glow, m_membrane,
                    m_porcelain, m_runes, m_void, orb, ring, segment_between)

SEVEN = ["ff3b3b", "ff9a2e", "ffe14d", "4dff7a", "3de8ff", "4d6bff", "c45bff"]


def _mirror_x(origin, size):
    return (-(origin[0] + size[0]), origin[1], origin[2])


# --------------------------------------------------------------------------- AEON-7, the Calabi-Yau Archon

def archon() -> Model:
    m = Model("geometry.dim11.archon", seed=1101)
    void = m_void()
    gold = m_runes("d4a63a", "3b0f6b", seed=11)
    gold_glyph = m_glyph_glow("ffe6a3", "2a1400", seed=12)
    crystal = m_crystal()
    porcelain = m_porcelain()
    core = m_energy("ffffff", "b07cff")
    vglow = m_energy("f3e8ff", "8a4dff", bands=False)

    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 40, 0), "root")
    orb(body, (0, 40, 0), 3.3, core, glow=True)
    for k in range(8):
        a = math.radians(k * 45 + 22.5)
        lo = (4.2 * math.cos(a), 31.5, 4.2 * math.sin(a))
        mid = (6.6 * math.cos(a), 40, 6.6 * math.sin(a))
        hi = (4.2 * math.cos(a), 48.5, 4.2 * math.sin(a))
        segment_between(body, lo, mid, 1.5, crystal)
        segment_between(body, mid, hi, 1.5, crystal)
    ring(body, (0, 48.6, 0), 6.2, 12, gold, thickness=1.4, width=1.8)
    ring(body, (0, 31.4, 0), 5.0, 10, gold, thickness=1.2, width=1.4)
    body.add((-9, 49.4, -3), (18, 3, 6), gold)
    orb(body, (-10.6, 51.5, 0), 2.6, crystal)
    orb(body, (10.6, 51.5, 0), 2.6, crystal)
    body.add((-1.3, 52.4, -1.3), (2.6, 2.2, 2.6), void)

    head = m.bone("head", (0, 54, 0), "body")
    head.add((-3.5, 54.5, -3.2), (7, 8.6, 6.4), porcelain)
    head.add((-2.6, 53.2, -2.9), (5.2, 1.4, 5.6), porcelain)
    head.add((-2.9, 58.4, -3.5), (2.1, 0.6, 0.4), vglow, glow=True)
    head.add((0.8, 58.4, -3.5), (2.1, 0.6, 0.4), vglow, glow=True)
    head.add((-0.5, 60.2, -3.5), (1.0, 1.7, 0.4), m_energy("ffffff", "ff5be3"), glow=True)
    head.add((-1, 62.4, -2.4), (2, 7, 5), gold, pivot=(0, 62.4, 0), rotation=(-22, 0, 0))
    head.add((-4.6, 59, -1.4), (1.1, 5, 3), gold, pivot=(-4, 59, 0), rotation=(0, 0, 16))
    head.add((3.5, 59, -1.4), (1.1, 5, 3), gold, pivot=(4, 59, 0), rotation=(0, 0, -16))
    halo = m.bone("halo", (0, 60, 4.2), "head")
    ring(halo, (0, 60, 4.2), 7.6, 22, vglow, thickness=0.7, width=0.5, plane="xy", glow=True)
    ring(halo, (0, 60, 4.6), 6.1, 16, gold, thickness=0.6, width=0.6, plane="xy")
    for k in range(8):
        a = math.radians(k * 45)
        segment_between(halo, (6.4 * math.cos(a), 60 + 6.4 * math.sin(a), 4.6),
                        (9.4 * math.cos(a), 60 + 9.4 * math.sin(a), 4.6), 0.5, gold_glyph, glow=True)

    for side in (-1, 1):
        nm = "r" if side < 0 else "l"
        arm = m.bone(f"arm_{nm}", (11 * side, 50, 0), "body", rotation=(0, 0, 10 * side))
        def put(bone, origin, size, mat, **kw):
            o = origin if side < 0 else _mirror_x(origin, size)
            bone.add(o, size, mat, **kw)
        put(arm, (-12.5, 41, -1.4), (3, 8, 2.8), void)
        put(arm, (-12.8, 44, -1.7), (3.6, 1.2, 3.4), gold)
        orb(arm, (11 * side, 39.6, 0), 1.0, vglow, glow=True)
        fore = m.bone(f"forearm_{nm}", (11 * side, 39, 0), f"arm_{nm}", rotation=(-12, 0, 0))
        put(fore, (-12.3, 30.4, -1.2), (2.6, 8, 2.4), crystal)
        orb(fore, (11 * side, 29.4, 0), 0.8, vglow, glow=True)
        hand = m.bone(f"hand_{nm}", (11 * side, 28.8, 0), f"forearm_{nm}")
        put(hand, (-12.5, 25.4, -1.5), (3, 3, 3), porcelain)
        for k in range(4):
            put(hand, (-12.6 + k * 0.8, 20.6, -1.1 + (k % 2) * 0.4), (0.6, 5, 0.6), porcelain)
            put(hand, (-12.6 + k * 0.8, 19.6, -1.1 + (k % 2) * 0.4), (0.6, 1.0, 0.6), vglow, glow=True)

    prev, top = "body", 33
    dims = [(11, 8, 9), (9, 8, 7), (6.4, 8, 5.2), (4, 7, 3.2)]
    for i, (w, h, d) in enumerate(dims):
        b = m.bone(f"robe{i}", (0, top, 0), prev)
        b.add((-w / 2, top - h, -d / 2), (w, h, d), void)
        b.add((-w / 2 - 0.15, top - h, -d / 2 - 0.15), (w + 0.3, 0.6, d + 0.3), vglow, glow=True)
        prev, top = f"robe{i}", top - h
    tail = m.get("robe3")
    for k, (x, z) in enumerate(((-1.4, -1), (1.4, -1), (-1.4, 1), (1.4, 1))):
        tail.add((x - 0.2, top - 6, z - 0.2), (0.4, 6, 0.4), vglow, glow=True)

    for name, plane, r, seg, mat in (("ring_a", "xz", 13.0, 24, gold), ("ring_b", "xy", 11.0, 20, gold),
                                     ("ring_c", "yz", 9.0, 18, crystal)):
        b = m.bone(name, (0, 40, 0), "body")
        ring(b, (0, 40, 0), r, seg, mat, thickness=0.9, width=1.5, plane=plane)
        ring(b, (0, 40, 0), r - 0.9, seg, gold_glyph, thickness=0.3, width=0.6, plane=plane, glow=True)

    petals = m.bone("petals", (0, 40, 0), "body")
    for k in range(6):
        p = m.bone(f"petal{k}", (0, 40, 0), "petals", rotation=(0, k * 60, 0))
        p.add((16, 36, -0.4), (6, 8, 0.8), crystal, pivot=(16, 40, 0), rotation=(0, 0, 18))
        p.add((21.2, 37.5, -0.3), (5, 6, 0.6), crystal, pivot=(21.2, 40, 0), rotation=(0, 0, 34))
        p.add((16, 43.9, -0.5), (6, 0.4, 1.0), vglow, pivot=(16, 40, 0), rotation=(0, 0, 18), glow=True)

    crown = m.bone("crown", (0, 68, 0), "body")
    for k in range(7):
        a = 2 * math.pi * k / 7
        x, z = 6.6 * math.cos(a), 6.6 * math.sin(a)
        col = m_energy("ffffff", SEVEN[k])
        crown.add((x - 0.7, 66, z - 0.7), (1.4, 4, 1.4), col, glow=True, pivot=(x, 68, z), rotation=(0, -math.degrees(a), 0))
        crown.add((x - 0.4, 64.6, z - 0.4), (0.8, 1.4, 0.8), col, glow=True)
        crown.add((x - 0.35, 70, z - 0.35), (0.7, 1.4, 0.7), col, glow=True)
    return m


# --------------------------------------------------------------------------- The M5 Sovereign (Brane-Leviathan)

def sovereign() -> Model:
    m = Model("geometry.dim11.sovereign", seed=1102)
    shell = m_crystal("1f6f86", "3fe0ff", "d8ffff", "0a2a36")
    plate = m_runes("173946", "62f4ff", seed=21)
    membrane = m_membrane()
    cyan = m_energy("ffffff", "38e8ff")
    string = m_energy("ffffff", "8ffcff", bands=False)
    belly = m_glyph_glow("9ffcff", "06303a", seed=22)

    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 24, 0), "root")
    body.add((-6, 18.5, -18), (12, 11, 12), shell)
    body.add((-5.5, 19, -6), (11, 10, 10), shell)
    body.add((-6.4, 28.6, -17.5), (12.8, 1.4, 21), plate)
    body.add((-4, 18.2, -17), (8, 0.4, 20), belly, glow=True)
    for z in (-15, -6):
        body.add((-0.5, 29.5, z), (1, 5, 7), shell, pivot=(0, 29.5, z + 3), rotation=(-22, 0, 0))
        body.add((-0.6, 34.2, z + 1.5), (1.2, 0.5, 5), cyan, pivot=(0, 29.5, z + 3), rotation=(-22, 0, 0), glow=True)
    heart = m.bone("heart", (0, 16, -10), "body")
    orb(heart, (0, 15.5, -10), 2.2, cyan, glow=True)
    ring(heart, (0, 15.5, -10), 4.2, 14, string, thickness=0.35, width=0.35, plane="xz", glow=True)
    segment_between(heart, (0, 18.6, -10), (0, 17.5, -10), 0.6, plate)

    head = m.bone("head", (0, 24, -18), "body")
    head.add((-5, 19.5, -29), (10, 8, 11), shell)
    head.add((-5.5, 26.5, -28), (11, 2, 9), plate)
    head.add((-3.5, 20, -33), (7, 5, 4.2), shell)
    for (x, y, w, h) in ((-4.3, 24.4, 2.1, 1.2), (2.2, 24.4, 2.1, 1.2), (-3.4, 22.3, 1.5, 0.9), (1.9, 22.3, 1.5, 0.9)):
        head.add((x, y, -29.35), (w, h, 0.45), m_energy("ffffff", "ff4df2"), glow=True)
    for side in (-1, 1):
        o = (-4.6, 17.4, -31) if side < 0 else (2.6, 17.4, -31)
        head.add(o, (2, 3.2, 6.5), plate, pivot=(3.6 * side, 20, -27), rotation=(12, 0, 0))
    for k in range(9):
        a = math.radians(-64 + k * 16)
        s = m.bone(f"string{k}", (0, 27.5, -22), "head")
        end = (math.sin(a) * 15, 27.5 + math.cos(a) * 11, -8 - abs(math.sin(a)) * 3)
        segment_between(s, (0, 27.5, -22), end, 0.4, string, glow=True)
        orb(s, end, 0.55, cyan, glow=True)

    prev, z = "body", 4
    for i, (w, h, L) in enumerate(((8, 7, 9), (6, 5, 9), (4, 3.6, 9), (2.4, 2, 9))):
        t = m.bone(f"tail{i}", (0, 24, z), prev)
        t.add((-w / 2, 24 - h / 2, z), (w, h, L), shell)
        t.add((-0.4, 24 + h / 2, z + 1), (0.8, 1.6, L - 2), cyan, glow=True)
        prev, z = f"tail{i}", z + L
    fluke = m.get("tail3")
    fluke.add((-6, 23.7, z - 2), (12, 0.6, 6), membrane, glow=True)
    fluke.add((-6, 23.4, z - 2.6), (12, 1.0, 0.9), plate)

    depths = (24, 20, 16, 11.5, 7)
    for side in (-1, 1):
        nm = "r" if side < 0 else "l"
        prev = "body"
        for k, depth in enumerate(depths):
            x_in = 6 + 8 * k
            px = x_in * side
            b = m.bone(f"wing_{nm}{k}", (px, 24, -10), prev, rotation=(0, 0, 4 * side) if k == 0 else None)
            z0 = -21 + 1.5 * k
            x0 = x_in if side > 0 else -x_in - 8
            b.add((x0, 23.75, z0), (8, 0.5, depth), membrane, glow=True)
            b.add((x0, 23.3, z0 - 0.9), (8, 1.3, 1.3), plate)
            rib_x = x0 if side > 0 else x0 + 8 - 0.6
            b.add((rib_x, 23.45, z0), (0.6, 1.0, depth), plate)
            for fx in (2, 6):
                b.add((x0 + fx, 17.2, z0 + depth - 0.4), (0.3, 6.4, 0.3), string, glow=True)
            prev = f"wing_{nm}{k}"
    return m


# --------------------------------------------------------------------------- The Ophanim of the Eleventh Axis

def observer() -> Model:
    m = Model("geometry.dim11.observer", seed=1103)
    gold = m_runes("e2b64a", "5a0b12", seed=31)
    goldg = m_energy("fff6d8", "ffb31a", bands=False)
    sclera = m_porcelain("fbf7ee", "d9cdb5")
    iris_glow = m_energy("ffffff", "ff2a3d", bands=False)
    feather = m_feather_eye()
    eyes = eye_decal(sclera="fbf7ee")

    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 32, 0), "root")
    outer = m.bone("tesseract_outer", (0, 32, 0), "body")
    frame_cube(outer, (0, 32, 0), 22, 1.4, gold)
    inner = m.bone("tesseract_inner", (0, 32, 0), "body")
    frame_cube(inner, (0, 32, 0), 11, 0.9, goldg, glow=True)

    eye = m.bone("eye", (0, 32, 0), "body")
    orb(eye, (0, 32, 0), 4.2, sclera)
    eye.add((-2.3, 29.7, -4.65), (4.6, 4.6, 0.4), iris_glow, glow=True,
            decals={"north": eye_decal("ff2a3d", "ffd27a", "200005")})
    eye.add((-0.8, 31.2, -4.95), (1.6, 1.6, 0.3), m_solid("0b0306", 0.02, 0))
    lid = m.bone("eyelid", (0, 36.2, -2), "eye")
    lid.add((-3.2, 35.6, -4.4), (6.4, 1.0, 4), gold)

    wa = m.bone("wheel_a", (0, 32, 0), "body")
    ring(wa, (0, 32, 0), 17, 20, gold, thickness=2.4, width=3.4, plane="xy", decals={"up": eyes})
    ring(wa, (0, 32, 0), 15.6, 20, goldg, thickness=0.4, width=1.0, plane="xy", glow=True)
    wb = m.bone("wheel_b", (0, 32, 0), "body")
    ring(wb, (0, 32, 0), 15, 18, gold, thickness=2.4, width=3.4, plane="yz", decals={"north": eyes, "south": eyes})
    ring(wb, (0, 32, 0), 13.6, 18, goldg, thickness=0.4, width=1.0, plane="yz", glow=True)

    for side in (-1, 1):
        nm = "r" if side < 0 else "l"
        for tier, (dy, rz) in enumerate(((7, 38), (0, 6), (-7, -30))):
            b = m.bone(f"wing_{nm}{tier}", (4 * side, 32 + dy, 9), "body", rotation=(0, -24 * side, rz * side))
            y = 32 + dy
            for (x0, w, hh) in ((4, 6, 10), (10, 6, 8), (16, 6, 6)):
                o = (x0, y - hh / 2, 9)
                if side < 0:
                    o = (-x0 - w, y - hh / 2, 9)
                b.add(o, (w, hh, 0.6), feather, decals={"north": eye_decal(sclera="fbf7ee")} if x0 != 10 else {})

    halo = m.bone("halo", (0, 50, 0), "body")
    ring(halo, (0, 50, 0), 8, 18, goldg, thickness=0.6, width=0.6, plane="xz", glow=True)
    for k in range(12):
        a = 2 * math.pi * k / 12
        halo.add((8 * math.cos(a) - 0.3, 50.3, 8 * math.sin(a) - 0.3), (0.6, 2.2, 0.6), gold)
    for k, x in enumerate((-6, 0, 6)):
        s = m.bone(f"trail{k}", (x, 20.3, 0), "body")
        s.add((x - 0.3, 8, -0.3), (0.6, 12.3, 0.6), goldg, glow=True)
    return m


# --------------------------------------------------------------------------- Closed-String Wisp

def wisp() -> Model:
    m = Model("geometry.dim11.wisp", seed=1104)
    cyan = m_energy("ffffff", "38e8ff")
    white = m_energy("ffffff", "c9fbff", bands=False)
    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 8, 0), "root")
    orb(body, (0, 8, 0), 1.3, m_crystal("1f6f86", "3fe0ff", "d8ffff", "0a2a36"))
    la = m.bone("loop_a", (0, 8, 0), "body")
    ring(la, (0, 8, 0), 4.2, 14, cyan, thickness=0.5, width=0.5, plane="xy", glow=True)
    lb = m.bone("loop_b", (0, 8, 0), "body")
    ring(lb, (0, 8, 0), 3.2, 12, white, thickness=0.4, width=0.4, plane="yz", glow=True)
    orb(body, (0, 8, 0), 0.8, white, glow=True)
    return m


ALL = {"archon": archon, "sovereign": sovereign, "observer": observer, "wisp": wisp}
