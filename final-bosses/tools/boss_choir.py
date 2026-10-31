"""Boss 05 - The Choir of Mirrors: a cathedral of reflections that sings.

Silhouette: a great porcelain mask, cracked with gold and missing a shard that floats beside it,
singing with light pouring from its open mouth; a halo of mirror fragments and a crown of glass
spikes; three tiers of framed mirror panes fanning out like wings on silver rods; lace ribbons
trailing beneath; a column of floating glass rings carrying its voice downward; and six smaller
choir masks - each with a different expression - orbiting it.
"""
import math

import materials as M
from modelkit import Model, hx
from shapes import bevel, orb, ring, spike, strut


def eye_hole(side):
    """Decal for one mask piece: a single hollow eye with a gold tear."""
    blk, g = hx("08060c"), hx("d8a331")

    def d(setp, w, h):
        cx = w * (0.62 if side == "l" else 0.42)
        for y in range(h):
            for x in range(w):
                if ((x - cx) / (w * 0.2)) ** 2 + ((y - h * 0.62) / (h * 0.12)) ** 2 < 1:
                    setp(x, y, blk)
                if abs(x - cx) < 0.6 and h * 0.72 < y < h * 0.98:
                    setp(x, y, g)
    return d


def singing_mouth():
    blk, g = hx("08060c"), hx("d8a331")

    def d(setp, w, h):
        for y in range(h):
            for x in range(w):
                if ((x - w / 2) / (w * 0.13)) ** 2 + ((y - h * 0.45) / (h * 0.24)) ** 2 < 1:
                    setp(x, y, blk)
                if abs(y - (h * 0.2 + abs(x - w / 2) * 0.35)) < 0.6 and abs(x - w / 2) > w * 0.2 and abs(x - w / 2) < w * 0.36:
                    setp(x, y, g)       # cheek cracks
    return d


def build() -> Model:
    m = Model("geometry.fb.choir", seed=505, density=2)
    por, sil, veil, gold = M.porcelain(gold_crack=True), M.silver(), M.veil(), M.royal_gold()
    light = M.radial_glow("ffffff", "8fd8ff")
    beam = M.glowgrad("ffffff", "6fbfff")
    glass = M.glowgrad("e8fbff", "4aa8ff")

    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 52, 0), "root")

    # ---- the broken mask
    mask = m.bone("mask", (0, 58, 0), "body")
    bevel(mask, (-10, 44, -3.5), (20, 15, 5), por, b=0.9)
    bevel(mask, (-10, 59, -3.5), (11.5, 13, 5), por, b=0.9)
    mask.add((-9, 45, -3.8), (18, 13.5, 0.4), por, decals={"north": singing_mouth()})
    mask.add((-9, 59.4, -3.8), (10, 11.5, 0.4), por, decals={"north": eye_hole("r")})
    mask.add((-5.6, 63.3, -3.86), (1.6, 1.0, 0.05), light, glow=True, faces=("north",))
    mask.add((-1.3, 50.6, -3.86), (2.6, 3.6, 0.05), light, glow=True, faces=("north",))
    for a in (-38, -14, 14, 38):
        r = math.radians(a - 90)
        strut(mask, (0, 51, -4.2), (math.cos(r) * 15, 51 + math.sin(r) * 15, -7), 0.7, beam, glow=True)
    mask.add((1.5, 59.2, -3.4), (0.3, 12.6, 4.6), M.solid("ffd27a", 0), glow=True)
    shard = m.bone("mask_shard", (6.5, 66, -1), "mask", rotation=(0, -8, -14), floating=True)
    bevel(shard, (3.5, 60.5, -4.5), (8, 12, 5), por, b=0.8)
    shard.add((4.2, 61.3, -4.8), (6.6, 10.4, 0.4), por, decals={"north": eye_hole("l")})
    shard.add((7.5, 64.75, -4.86), (1.6, 1.0, 0.05), light, glow=True, faces=("north",))
    mask.add((-11, 48, 1.5), (22, 23, 1.2), veil)
    for sx in (-1, 1):
        mask.add(((10.4 if sx > 0 else -11.6), 42, -2.5), (1.2, 26, 4), veil)
    mask.add((-10.6, 72, -3.9), (21.2, 1.6, 5.8), gold)
    for k in range(7):
        a = math.radians(30 + k * 20)
        spike(mask, (math.cos(a) * 7, 73.4, -0.5), (math.cos(a) * 15, 73.4 + math.sin(a) * 13, 0.5), 1.8, M.mirror(seed=k), steps=3)

    # ---- halo of mirror fragments
    halo = m.bone("halo", (0, 58, 5), "body", floating=True)
    ring(halo, (0, 58, 5), 17, 22, M.mirror(seed=3), thickness=1.6, width=0.6, plane="xy", jag=[1, 1.9, 1.2, 2.5])
    ring(halo, (0, 58, 4.6), 14, 26, gold, thickness=0.7, width=0.7, plane="xy")
    ring(halo, (0, 58, 4.3), 12.6, 30, glass, thickness=0.3, width=0.3, plane="xy", glow=True)

    # ---- three tiers of mirror wings on silver rods
    for side, sx in (("r", -1), ("l", 1)):
        for tier, (dy, base_rot) in enumerate(((10, 28), (0, 5), (-11, -22))):
            pv = (9.5 * sx, 58 + dy * 0.3, 2.5)
            wb = m.bone(f"wing_{side}{tier}", pv, "mask", rotation=(0, -18 * sx, base_rot * sx))
            for k in range(4):
                cx = (15 + k * 7.5) * sx
                cy = 58 + dy * 0.3 + (k - 1.5) * 1.5 * (1 if tier == 0 else -1 if tier == 2 else 0)
                w, h = 6.5, 15 - k * 1.8 - tier * 1.5
                rot = (0, 0, (k * 7 - 6) * sx)
                strut(wb, pv, (cx, cy, 3.2), 0.8, sil)
                wb.add((cx - w / 2 - 0.5, cy - h / 2 - 0.5, 3.0), (w + 1.0, h + 1.0, 0.5), sil, pivot=(cx, cy, 3.2), rotation=rot)
                wb.add((cx - w / 2, cy - h / 2, 2.5), (w, h, 0.5), M.mirror(seed=k + tier * 4 + (0 if sx > 0 else 13)),
                       pivot=(cx, cy, 3.2), rotation=rot)

    # ---- lace ribbons
    for k, x in enumerate((-12, -6, 6, 12)):
        prev, top = "mask", 44.6
        for s in range(3):
            rb = m.bone(f"ribbon{k}_{s}", (x, top, 1.0), prev, rotation=(0, 0, (4 if x > 0 else -4) if s == 0 else 0))
            rb.add((x - 1.1, top - 9, 0.8 + s * 0.05), (2.2, 9.2, 0.3), veil)
            prev, top = f"ribbon{k}_{s}", top - 9

    # ---- the voice: a column of glass rings
    voice = m.bone("voice", (0, 40, 0), "body", floating=True)
    for r, y in ((5.5, 41), (4.5, 35), (3.6, 29.5), (2.6, 24.5), (1.7, 20)):
        ring(voice, (0, y, 0), r, max(8, int(r * 3)), glass, thickness=0.45, width=0.45, plane="xz", glow=True)
    orb(voice, (0, 16.5, 0), 1.3, light, glow=True)

    # ---- six orbiting choir masks
    chorus = m.bone("chorus", (0, 52, 0), "body", floating=True)
    for k, face in enumerate(("O", "smile", "wail", "frown", "O", "wail")):
        a = 2 * math.pi * k / 6
        cx, cz = 23 * math.cos(a), 23 * math.sin(a)
        cy = 52 + (8 if k % 2 else -6)
        cm = m.bone(f"chorister{k}", (cx, cy, cz), "chorus", rotation=(0, -math.degrees(a) - 90, 0), floating=True)
        bevel(cm, (cx - 3.2, cy - 4.2, cz - 1), (6.4, 8.4, 2), por, b=0.5)
        cm.add((cx - 2.8, cy - 3.8, cz - 1.25), (5.6, 7.6, 0.3), por, decals={"north": M.mask_face(face, gold=True)})
        cm.add((cx - 3.6, cy - 6.2, cz - 0.6), (7.2, 1.6, 1.4), M.mirror(seed=k))
        orb(cm, (cx, cy - 7.6, cz), 0.8, light, glow=True)
    return m
