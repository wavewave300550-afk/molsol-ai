"""Boss 04 - The World Parasite: a hill that is alive.

Built from block-sized cubes at vanilla resolution (16 px per block) so that, dormant, it is a
grassy mound with an oak tree, mossy stone and some odd white bones. Awake, the front of the hill
lifts into a cavernous maw lined with stalactite teeth, boulder eyelids roll open over two
slit-pupilled eyes, root-tentacles writhe out of its base, the tree on its back sways as a lure,
and its torn-open back reveals a pulsing flesh heart studded with glowing pustules.
"""
import math

import materials as M
from modelkit import Model
from shapes import orb, spike, strut

W, D = 7, 6
L0 = [(i, j) for i in range(W) for j in range(D) if (i, j) not in ((0, 0), (6, 0), (0, 5), (6, 5), (6, 4))]
MAW = [(2, 0), (3, 0), (4, 0)]
L1 = [(i, j) for i in range(1, 6) for j in range(1, 5) if (i, j) not in ((5, 4), (1, 4), (3, 4), (2, 4), (4, 4))] + [(1, 0), (5, 0)]
L2 = [(i, j) for i in range(2, 5) for j in range(1, 4)] + [(1, 2), (5, 2)]
L3 = [(3, 2), (3, 1), (2, 2)]
FLESH_SIDES = {(6, 2, 0): "west", (0, 3, 0): "east", (5, 3, 1): "west", (1, 1, 1): "east"}


def cell(i, j, layer):
    return (-56 + 16 * i, 16 * layer, -48 + 16 * j)


def build() -> Model:
    m = Model("geometry.fb.world_parasite", seed=404, density=1)
    gt, gs, dirt, stone, moss = M.grass_top(), M.grass_side(), M.dirt(), M.stone(), M.mossy_stone()
    flesh, bark, leaves, bn = M.flesh(), M.bark(), M.leaves(), M.bone()
    sick = M.pustule()
    occ = {(i, j, 0) for i, j in L0} | {(i, j, 1) for i, j in L1 + MAW} | {(i, j, 2) for i, j in L2} | {(i, j, 3) for i, j in L3}

    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 0, 0), "root")

    def mat_for(i, j, layer):
        if (i, j, layer + 1) not in occ:
            return gs, {"up": gt, "down": dirt}
        if layer == 0:
            return (moss if (i * 7 + j) % 4 == 0 else stone if (i + j) % 3 == 0 else dirt), {}
        return dirt, {}

    tops = []
    for layer, cells in ((0, L0), (1, L1), (2, L2), (3, L3)):
        for i, j in cells:
            mat, fm = mat_for(i, j, layer)
            side = FLESH_SIDES.get((i, j, layer))
            if side:
                fm[side] = flesh
            if layer == 0 and j == 0 and (i, j) in [(2, 0), (3, 0), (4, 0)]:
                fm.update({"up": flesh, "north": moss})
            if layer == 1 and j == 1 and 2 <= i <= 4:
                fm["north"] = flesh
            body.add(cell(i, j, layer), (16, 16, 16), mat, face_mats=fm)
            if (i, j, layer + 1) not in occ:
                tops.append((i, j, layer))

    # ---- mouth interior (only visible while the maw is open)
    body.add((-22, 16, -47), (44, 1.5, 14), flesh)
    orb(body, (0, 23, -33.5), 4.2, sick, glow=True)
    for x in range(-20, 21, 6):
        spike(body, (x, 15.5, -45), (x, 21.5, -45.3), 2.2, bn, steps=2)

    # ---- the upper maw is the front of the hill
    maw = m.bone("maw", (0, 32, -32), "body")
    for i, j in MAW:
        maw.add(cell(i, j, 1), (16, 16, 16), gs, face_mats={"up": gt, "down": flesh, "north": moss})
    for x in range(-21, 22, 6):
        spike(maw, (x, 16.6, -46), (x, 10.5, -46.3), 2.4, stone, steps=2)
    for side, x in (("r", -12), ("l", 12)):
        maw.add((x - 5, 20.5, -49.5), (10, 9, 1.5), M.solid("f2e7b8", 0.03), decals={"north": M.parasite_eye()})
        lid = m.bone(f"eyelid_{side}", (x, 30.8, -50.2), "maw")
        lid.add((x - 6, 19.5, -52), (12, 11.5, 1.9), moss)
    maw.add((-22, 30.2, -50.6), (44, 2.6, 3.1), stone)
    for x in (-19, -7, 5, 17):
        strut(maw, (x, 30, -50), (x + 1, 17 + (x % 5), -50.4), 0.9, M.leaves())

    # ---- fossil ribs breaking out of the flanks, a ridge of bone plates along the back
    for sx in (-1, 1):
        for z in (-26, -8, 10):
            p0, p1, p2, p3 = (55 * sx, 4, z), (63 * sx, 15, z), (60 * sx, 28, z + 1), (40 * sx, 35, z + 2)
            for a, b in ((p0, p1), (p1, p2), (p2, p3)):
                strut(body, a, b, 3.4, bn)
    for k, z in enumerate((-30, -18, -6, 6, 18)):
        h = 9 - abs(k - 2) * 2
        top = 48 if (3, (z + 48) // 16, 3) not in occ else 64
        strut(body, (0, top - 1, z), (0, top + h, z + 3), 2.2, bn, depth=6)

    # ---- the torn-open back: a pulsing heart
    heart = m.bone("heart", (0, 22, 24), "body")
    orb(heart, (0, 24, 26), 11.5, flesh)
    for p in ((6, 28, 32), (-7, 24, 33), (2, 15, 33), (-3, 31, 28), (8, 18, 30)):
        orb(heart, p, 2.0, sick, glow=True)
    for a in range(0, 360, 45):
        r = math.radians(a)
        strut(heart, (0, 22, 25), (math.cos(r) * 14, 22 + math.sin(r) * 10, 31), 1.3, M.solid("6e1b2c", 0.05))

    for p in ((56.6, 10, -20), (-56.6, 22, 6), (40.6, 26, -6), (-24.6, 40, 8), (24.6, 42, -22)):
        orb(body, p, 2.4, sick, glow=True)

    # ---- grass tufts on top of exposed blocks
    for n, (i, j, layer) in enumerate(tops):
        if n % 3:
            continue
        x, y, z = cell(i, j, layer)
        x, y, z = x + 8, y + 16, z + 8
        body.add((x - 4, y, z), (8, 7, 0), gs, faces=("north", "south"), bake=False)
        body.add((x, y, z - 4), (0, 7, 8), gs, faces=("east", "west"), bake=False)

    # ---- the tree is a lure
    tree = m.bone("tree", (0, 64, -8), "body")
    tree.add((-3, 64, -11), (6, 34, 6), bark)
    strut(tree, (2.5, 84, -8), (11, 93, -8), 2.6, bark)
    strut(tree, (-2.5, 80, -8), (-11, 88, -7), 2.4, bark)
    canopy = m.bone("canopy", (0, 96, -8), "tree")
    for o, s in (((-9, 94, -17), (18, 12, 18)), ((-21, 88, -14), (13, 10, 12)), ((8, 88, -14), (13, 10, 12)),
                 ((-8, 88, -27), (16, 10, 12)), ((-8, 88, -1), (16, 10, 12)), ((-6, 105.5, -14), (12, 7, 12))):
        canopy.add(o, s, leaves, bake=False)

    # ---- root tentacles
    for k, (sx, z, ang) in enumerate(((-1, -24, -25), (-1, 20, 30), (1, -24, 25), (1, 8, -30))):
        prev = "body"
        dx, dz = math.cos(math.radians(ang)) * sx, math.sin(math.radians(ang))
        p = (55 * sx, 3.5, z)
        for s in range(5):
            q = (p[0] + dx * 12, 3.0 - s * 0.35, p[2] + dz * 12)
            rb = m.bone(f"root{k}_{s}", p, prev)
            strut(rb, p, q, 5.6 - s * 0.9, bark, depth=5.6 - s * 0.9)
            if s == 4:
                spike(rb, q, (q[0] + dx * 6, 2.0, q[2] + dz * 6), 1.4, flesh, steps=2)
            prev, p = f"root{k}_{s}", q
    return m
