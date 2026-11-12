"""The three Grimoire attachables: painted covers, hinged geometry, flow overlays, animations."""
import math
import numpy as np
from PIL import Image, ImageDraw
from .art import Art, vein_paths, voronoi_facets
from .modelkit import Model, geometry_file
from .anim import Anim, anim_file, controller_file
from .fxdefs import dump
from . import book_ext as EXT

K = 0.28  # model pixels per centimetre (books rendered ~1.75x real size; proportions exact)

BOOKS = {
    # name: (height cm, width cm, thickness cm)
    "pressure": (35, 27, 7),
    "ice": (36, 28, 7),
    "blood": (36, 27, 7),
    **EXT.DIMS,
}

ART_W, ART_H = 96, 124      # front/back cover art resolution
SPINE_W = 24


# ============================================================================== painting

def paint_pressure():
    rs = np.random.RandomState(11)
    # ---- front: charcoal leather, copper frame, reinforced corners, 5 compression rings + orange core
    a = Art(ART_W, ART_H)
    a.grain((34, 30, 28), 0.35, 1.2, seed=3)
    cx, cy = ART_W / 2, ART_H / 2
    # faint isobar contour lines (pressure differential motif)
    for k in range(9):
        pts = []
        for i in range(60):
            x = i / 59 * ART_W
            y = 8 + k * 13 + math.sin(x / 13 + k) * 3 + math.sin(x / 5.0 + k * 2) * 0.8
            pts.append((x, y))
        a.line(pts, (58, 44, 34), 0.5)
    copper, copper_hi, copper_lo = (184, 104, 47), (255, 210, 150), (90, 44, 16)
    a.rect(3, 3, ART_W - 3, ART_H - 3, outline=copper, width=2.2)
    a.rect(6.5, 6.5, ART_W - 6.5, ART_H - 6.5, outline=copper_lo, width=0.8)
    for i in range(0, 13):
        y = 10 + i * (ART_H - 20) / 12
        a.circle(4.1, y, 0.7, fill=copper_hi)
        a.circle(ART_W - 4.1, y, 0.7, fill=copper_hi)
    for (x, y, sx, sy) in ((0, 0, 1, 1), (ART_W, 0, -1, 1), (0, ART_H, 1, -1), (ART_W, ART_H, -1, -1)):
        a.poly([(x, y), (x + 16 * sx, y), (x, y + 16 * sy)], fill=copper)
        a.line([(x + 13 * sx, y + 1.5 * sy), (x + 1.5 * sx, y + 13 * sy)], copper_hi, 0.7)
        a.circle(x + 4.5 * sx, y + 4.5 * sy, 1.2, fill=copper_hi)
    # emblem: five concentric compression rings around a bright orange core
    radii = [8.5, 13.5, 18.5, 23.5, 28.5]
    for i, r in enumerate(radii):
        if i % 2 == 0:
            a.circle(cx, cy, r, outline=(255, 150, 40), width=1.8, glow=0.9)
        else:
            a.circle(cx, cy, r, outline=copper, width=2.0)
            a.circle(cx, cy, r - 1.1, outline=copper_hi, width=0.4)
    a.ring_ticks(cx, cy, 25.2, 27.0, 36, (255, 170, 60), 0.5, glow=0.6)
    a.ring_ticks(cx, cy, 15.4, 16.8, 18, (255, 170, 60), 0.5, glow=0.6, start=5)
    for i in range(4):
        ang = math.radians(45 + 90 * i)
        a.line([(cx + math.cos(ang) * 29, cy + math.sin(ang) * 29), (cx + math.cos(ang) * 40, cy + math.sin(ang) * 40)], copper, 1.4)
    a.radial_glow(cx, cy, 13, (255, 140, 30), 0.9, glow=0.6)
    a.circle(cx, cy, 5.2, fill=(255, 150, 40), glow=1.0)
    a.circle(cx, cy, 3.0, fill=(255, 236, 190), glow=1.0)
    a.circle(cx - 1.0, cy - 1.0, 1.0, fill=(255, 255, 255), glow=1.0)
    front = a.finish()

    # ---- back: frame + single gauge ring
    b = Art(ART_W, ART_H)
    b.grain((32, 28, 26), 0.35, 1.2, seed=4)
    b.rect(3, 3, ART_W - 3, ART_H - 3, outline=copper, width=2.2)
    b.rect(6.5, 6.5, ART_W - 6.5, ART_H - 6.5, outline=copper_lo, width=0.8)
    for (x, y, sx, sy) in ((0, 0, 1, 1), (ART_W, 0, -1, 1), (0, ART_H, 1, -1), (ART_W, ART_H, -1, -1)):
        b.poly([(x, y), (x + 14 * sx, y), (x, y + 14 * sy)], fill=copper)
    b.circle(cx, cy, 14, outline=copper, width=1.6)
    b.ring_ticks(cx, cy, 10, 12.5, 24, copper_hi, 0.5)
    b.circle(cx, cy, 3, fill=(255, 150, 40), glow=0.8)
    back = b.finish()

    # ---- spine: raised copper bands and glowing orange channels
    s = Art(SPINE_W, ART_H)
    s.grain((30, 27, 25), 0.3, 1.0, seed=5)
    for x in (7, SPINE_W - 7):
        s.line([(x, 4), (x, ART_H - 4)], (255, 150, 40), 1.4, glow=1.0)
    for y in (12, 40, ART_H - 40, ART_H - 12):
        s.rect(1, y - 3, SPINE_W - 1, y + 3, fill=copper)
        s.line([(1, y - 2.2), (SPINE_W - 1, y - 2.2)], copper_hi, 0.5)
    s.circle(SPINE_W / 2, ART_H / 2, 4, outline=(255, 160, 50), width=1.2, glow=0.9)
    spine = s.finish()

    # ---- page script (luminous orange diagrams)
    p = Art(64, 80, bg=(240, 226, 190))
    p.grain((240, 226, 190), 0.12, 2, seed=6)
    for row in range(8, 78, 5):
        x = 6
        while x < 58:
            ln = rs.randint(3, 9)
            p.line([(x, row), (min(58, x + ln), row)], (255, 130, 30), 0.7, glow=0.9)
            x += ln + rs.randint(2, 4)
    p.circle(32, 26, 10, outline=(255, 130, 30), width=0.8, glow=0.9)
    p.circle(32, 26, 6, outline=(255, 130, 30), width=0.6, glow=0.9)
    p.circle(32, 26, 2, fill=(255, 170, 60), glow=1.0)
    page = p.finish()
    return front, back, spine, page


def paint_ice():
    rs = np.random.RandomState(21)
    cx, cy = ART_W / 2, ART_H / 2
    silver, silver_hi, cyan = (200, 212, 232), (250, 252, 255), (90, 230, 255)

    def facets(seed):
        rgb, edge = voronoi_facets(ART_W * 4, ART_H * 4, 34, seed, (70, 120, 235), (12, 32, 110))
        img = Image.fromarray(rgb.astype(np.uint8), 'RGB')
        return img

    a = Art(ART_W, ART_H)
    a.base = facets(7)
    a.d = ImageDraw.Draw(a.base)
    # glowing cracks
    for pts, depth in vein_paths(rs, ART_W, ART_H, [(rs.rand() * ART_W, rs.rand() * ART_H, rs.rand() * 6.28) for _ in range(9)], life=40, branch=0.07, wobble=0.35):
        a.line(pts, (150, 240, 255), 0.55 if depth else 0.8, glow=0.85)
    # intricate silver framework
    a.rect(2.5, 2.5, ART_W - 2.5, ART_H - 2.5, outline=silver, width=2.0)
    a.rect(5.5, 5.5, ART_W - 5.5, ART_H - 5.5, outline=silver_hi, width=0.6)
    for (x, y, sx, sy) in ((0, 0, 1, 1), (ART_W, 0, -1, 1), (0, ART_H, 1, -1), (ART_W, ART_H, -1, -1)):
        a.line([(x + 3 * sx, y + 3 * sy), (x + (cx - x) * 0.62, y + (cy - y) * 0.62)], silver, 0.9)
        a.poly([(x, y), (x + 13 * sx, y), (x + 4 * sx, y + 4 * sy), (x, y + 13 * sy)], fill=silver)
        a.poly([(x + 2 * sx, y + 2 * sy), (x + 8 * sx, y + 2.5 * sy), (x + 2.5 * sx, y + 8 * sy)], fill=(230, 248, 255), glow=0.5)
    # filigree arcs
    for r in (36, 40):
        a.circle(cx, cy, r, outline=silver, width=0.5)
    # hexagonal magical rings + six-pointed ice crystal
    a.hexagon(cx, cy, 30, silver, 1.6)
    a.hexagon(cx, cy, 26, cyan, 0.9, glow=0.9)
    a.hexagon(cx, cy, 19, silver_hi, 1.0, rot=0)
    a.radial_glow(cx, cy, 16, (90, 200, 255), 0.8, glow=0.5)
    a.star6(cx, cy, 15, (240, 252, 255), 1.6, glow=1.0)
    a.circle(cx, cy, 3.2, fill=(255, 255, 255), glow=1.0)
    for i in range(6):
        ang = math.radians(-90 + 60 * i)
        a.circle(cx + math.cos(ang) * 30, cy + math.sin(ang) * 30, 1.5, fill=(200, 245, 255), glow=0.9)
    front = a.finish()

    b = Art(ART_W, ART_H)
    b.base = facets(9)
    b.d = ImageDraw.Draw(b.base)
    b.rect(2.5, 2.5, ART_W - 2.5, ART_H - 2.5, outline=silver, width=2.0)
    b.hexagon(cx, cy, 14, silver, 1.2)
    b.hexagon(cx, cy, 10, cyan, 0.7, glow=0.8)
    for pts, depth in vein_paths(rs, ART_W, ART_H, [(rs.rand() * ART_W, rs.rand() * ART_H, rs.rand() * 6.28) for _ in range(6)], life=30):
        b.line(pts, (150, 240, 255), 0.5, glow=0.8)
    back = b.finish()

    s = Art(SPINE_W, ART_H)
    s.grain((20, 46, 140), 0.3, 1.0, seed=8)
    for y in (10, 36, ART_H - 36, ART_H - 10):
        s.rect(1, y - 2.5, SPINE_W - 1, y + 2.5, fill=silver)
        s.poly([(SPINE_W / 2, y - 5), (SPINE_W / 2 + 3, y), (SPINE_W / 2, y + 5), (SPINE_W / 2 - 3, y)], fill=(230, 248, 255), glow=0.6)
    for pts, depth in vein_paths(rs, SPINE_W, ART_H, [(SPINE_W / 2, 50, 1.57), (SPINE_W / 2, 74, -1.57)], life=24, wobble=0.6):
        s.line(pts, cyan, 0.7, glow=1.0)
    spine = s.finish()

    p = Art(64, 80, bg=(220, 240, 255))
    p.grain((220, 240, 255), 0.1, 2, seed=9)
    for row in range(8, 78, 5):
        x = 6
        while x < 58:
            ln = rs.randint(3, 9)
            p.line([(x, row), (min(58, x + ln), row)], (40, 190, 255), 0.7, glow=0.9)
            x += ln + rs.randint(2, 4)
    p.star6(32, 28, 9, (40, 190, 255), 0.7, glow=0.9)
    page = p.finish()
    return front, back, spine, page


def gothic_arch(a, x0, x1, ytop, ybot, color, width=1.4, glow=None):
    """Pointed gothic arch outline."""
    cx = (x0 + x1) / 2
    w = x1 - x0
    # pointed arch: two circular arcs (radius = span) meeting at the apex
    left, right = [], []
    for i in range(21):
        t = math.radians(60 * i / 20)
        left.append((x0 + w * (1 - math.cos(t)), ytop + w * 0.9 - w * math.sin(t) * 0.9))
        right.append((x1 - w * (1 - math.cos(t)), ytop + w * 0.9 - w * math.sin(t) * 0.9))
    a.line([(x0, ybot)] + left, color, width, glow)
    a.line([(x1, ybot)] + right, color, width, glow)
    return (cx, ytop + w * 0.9 - w * 0.9 * math.sin(math.radians(60)))


def heart_pts(cx, cy, s):
    pts = []
    for i in range(48):
        t = math.tau * i / 48
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s, cy - y * s))
    return pts


def paint_blood():
    rs = np.random.RandomState(31)
    cx, cy = ART_W / 2, ART_H / 2 + 4
    silver, silver_hi = (60, 60, 70), (160, 160, 176)
    a = Art(ART_W, ART_H)
    a.grain((76, 12, 24), 0.38, 1.2, seed=12)
    for pts, depth in vein_paths(rs, ART_W, ART_H, [(cx, cy, rs.rand() * 6.28) for _ in range(10)], life=45, branch=0.09, wobble=0.45):
        a.line(pts, (200, 24, 40) if depth else (235, 40, 50), 0.5 if depth else 0.85, glow=0.55 if depth else 0.75)
    a.rect(2.5, 2.5, ART_W - 2.5, ART_H - 2.5, outline=silver, width=2.2)
    a.rect(5.5, 5.5, ART_W - 5.5, ART_H - 5.5, outline=silver_hi, width=0.5)
    apex = gothic_arch(a, 12, ART_W - 12, 14, ART_H - 12, silver, 1.8)
    gothic_arch(a, 16, ART_W - 16, 18, ART_H - 16, silver_hi, 0.5)
    for (x, y, sx, sy) in ((0, 0, 1, 1), (ART_W, 0, -1, 1), (0, ART_H, 1, -1), (ART_W, ART_H, -1, -1)):
        a.poly([(x, y), (x + 12 * sx, y), (x + 12 * sx, y + 3 * sy), (x + 3 * sx, y + 3 * sy), (x + 3 * sx, y + 12 * sy), (x, y + 12 * sy)], fill=silver)
        a.poly([(x + 6 * sx, y + 3 * sy), (x + 9 * sx, y + 6 * sy), (x + 6 * sx, y + 9 * sy), (x + 3 * sx, y + 6 * sy)], fill=(220, 30, 50), glow=0.8)
    # quatrefoil rosettes
    for qx, qy in ((cx, 30), (22, ART_H - 26), (ART_W - 22, ART_H - 26)):
        for k in range(4):
            ang = math.radians(90 * k)
            a.circle(qx + math.cos(ang) * 3, qy + math.sin(ang) * 3, 2.6, outline=silver_hi, width=0.6)
        a.circle(qx, qy, 1.3, fill=(230, 30, 50), glow=0.9)
    # pulsating ruby heart emblem
    a.radial_glow(cx, cy, 20, (255, 30, 50), 0.85, glow=0.45)
    a.poly(heart_pts(cx, cy, 1.15), fill=(160, 10, 26), outline=silver_hi, width=1.0)
    a.poly(heart_pts(cx, cy, 0.85), fill=(235, 28, 44), glow=0.85)
    a.poly(heart_pts(cx - 2.5, cy - 3, 0.3), fill=(255, 190, 200), glow=1.0)
    front = a.finish()

    b = Art(ART_W, ART_H)
    b.grain((72, 12, 22), 0.38, 1.2, seed=13)
    for pts, depth in vein_paths(rs, ART_W, ART_H, [(rs.rand() * ART_W, rs.rand() * ART_H, rs.rand() * 6.28) for _ in range(6)], life=40):
        b.line(pts, (200, 24, 40), 0.6, glow=0.6)
    b.rect(2.5, 2.5, ART_W - 2.5, ART_H - 2.5, outline=silver, width=2.2)
    gothic_arch(b, 20, ART_W - 20, 26, ART_H - 22, silver, 1.2)
    b.poly(heart_pts(cx, cy, 0.5), fill=(200, 20, 36), glow=0.6)
    back = b.finish()

    s = Art(SPINE_W, ART_H)
    s.grain((70, 10, 22), 0.3, 1.0, seed=14)
    for y in (10, 34, ART_H - 34, ART_H - 10):
        s.rect(1, y - 2.5, SPINE_W - 1, y + 2.5, fill=silver)
        s.poly([(SPINE_W / 2, y - 3.5), (SPINE_W / 2 + 2.5, y), (SPINE_W / 2, y + 3.5), (SPINE_W / 2 - 2.5, y)], fill=(230, 30, 50), glow=0.9)
    for pts, depth in vein_paths(rs, SPINE_W, ART_H, [(SPINE_W / 2, 50, 1.57), (SPINE_W / 2, 74, -1.57)], life=26, wobble=0.6):
        s.line(pts, (240, 40, 50), 0.7, glow=0.8)
    spine = s.finish()

    p = Art(64, 80, bg=(236, 212, 204))
    p.grain((236, 212, 204), 0.12, 2, seed=15)
    for row in range(8, 78, 5):
        x = 6
        while x < 58:
            ln = rs.randint(3, 9)
            p.line([(x, row), (min(58, x + ln), row)], (220, 20, 36), 0.7, glow=0.9)
            x += ln + rs.randint(2, 4)
    p.poly(heart_pts(32, 26, 0.45), outline=(220, 20, 36), width=0.8, glow=0.9)
    page = p.finish()
    return front, back, spine, page


def paint_sigil(school, size=64):
    """Small magic circle shown behind the open book while charging (additive)."""
    a = Art(size, size)
    c = size / 2
    col = {"pressure": (255, 150, 40), "ice": (110, 220, 255), "blood": (255, 40, 60), **{k: v[0] for k, v in EXT.SIGIL_COL.items()}}[school]
    hi = {"pressure": (255, 236, 190), "ice": (230, 250, 255), "blood": (255, 200, 200), **{k: v[1] for k, v in EXT.SIGIL_COL.items()}}[school]
    a.circle(c, c, size * 0.46, outline=col, width=1.4)
    a.circle(c, c, size * 0.40, outline=hi, width=0.6)
    a.ring_ticks(c, c, size * 0.40, size * 0.46, 48, col, 0.4)
    if school == "pressure":
        for r in (0.12, 0.2, 0.28, 0.34):
            a.circle(c, c, size * r, outline=col, width=0.8)
    elif school == "ice":
        a.hexagon(c, c, size * 0.34, hi, 0.9)
        a.hexagon(c, c, size * 0.28, col, 0.7, rot=0)
        a.star6(c, c, size * 0.22, hi, 0.9)
    elif school in EXT.DIMS:
        EXT.paint_sigil(school, a, c, size, col, hi)
    else:
        for k in range(8):
            ang = math.radians(45 * k)
            a.circle(c + math.cos(ang) * size * 0.26, c + math.sin(ang) * size * 0.26, size * 0.08, outline=col, width=0.6)
        a.poly(heart_pts(c, c + 1, size * 0.008), outline=hi, width=0.8)
    a.radial_glow(c, c, size * 0.2, col, 0.6)
    out = a.finish(emissive=False, alpha_from_glow=False)
    out[..., 3] = np.clip(out[..., :3].max(-1) * 1.4, 0, 255)  # additive: alpha follows brightness
    return out


def paint_flow(school, w=128, h=128):
    """Seamlessly tiling (vertical) flow texture for the uv_anim overlay (additive, sparse & subtle)."""
    rs = np.random.RandomState({"pressure": 41, "ice": 42, "blood": 43, "plasma": 44, "darkness": 45, "prism_light": 46}[school])
    img = np.zeros((h, w, 3), np.float32)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    if school == "pressure":
        # a few thin isobar pulses travelling along the spine/cover
        for k in range(3):
            yy = (rs.rand() * h + x * 0.15) % h
            d = np.minimum(np.abs(y - yy), h - np.abs(y - yy))
            img += np.exp(-d * d / 1.2)[..., None] * np.array([255, 150, 40], np.float32) * 0.55
    elif school == "ice":
        for _ in range(26):
            px, py = rs.rand() * w, rs.rand() * h
            d2 = (x - px) ** 2 + ((y - py + h / 2) % h - h / 2) ** 2
            img += np.exp(-d2 / 1.5)[..., None] * np.array([170, 235, 255], np.float32) * 0.8
    elif school in EXT.DIMS:
        EXT.paint_flow(school, img, x, y, rs, w, h)
    else:
        # blood flowing down a few branching vessels, brighter in pulses
        for _ in range(5):
            px = rs.rand() * w
            amp = rs.rand() * 5 + 2
            xx = px + np.sin(y / h * math.tau * 2 + rs.rand() * 6) * amp
            d = np.abs(x - xx)
            pulse = np.clip(np.sin(y / h * math.tau * 3) * 2 - 1, 0, 1)
            img += np.exp(-d * d / 0.6)[..., None] * np.array([255, 40, 50], np.float32) * (0.15 + 0.6 * pulse[..., None])
    img = np.clip(img, 0, 255)
    out = np.zeros((h, w, 4), np.float32)
    out[..., :3] = img
    out[..., 3] = np.clip(img.max(-1) * 1.2, 0, 255)
    return out


# ============================================================================== geometry

def build_book(school):
    Hc, Wc, Tc = BOOKS[school]
    H, W, T = Hc * K, Wc * K, Tc * K
    c = 0.3                      # cover board thickness
    p = (T - 2 * c) / 2          # pages per half
    s = p                        # spine half width (closed book thickness = 2(p+c) = T)
    m = Model(f"geometry.grimoire.book_{school}", 256, 256, bounds=(2.5, 2.5, (0, 0, 0)))
    at = m.atlas
    front, back, spine, page = EXT.paint(school) if school in EXT.DIMS else {"pressure": paint_pressure, "ice": paint_ice, "blood": paint_blood}[school]()
    R_front = ('rect',) + at.put_image('front', front)
    R_back = ('rect',) + at.put_image('back', back)
    R_spine = ('rect',) + at.put_image('spine', spine)
    R_page = ('rect',) + at.put_image('page', page)
    R_sigil = ('rect',) + at.put_image('sigil', paint_sigil(school))
    edge_style = {"pressure": "pg_parch", "ice": "pg_ice", "blood": "pg_blood", **EXT.STYLE["edge"]}[school]
    cover_side = {"pressure": "p_charcoal", "ice": "i_sapphire", "blood": "b_burgundy", **EXT.STYLE["cover_side"]}[school]
    metal = {"pressure": "p_copper", "ice": "i_silver", "blood": "b_silver", **EXT.STYLE["metal"]}[school]
    metal_hi = {"pressure": "p_gold", "ice": "i_silver", "blood": "b_silver_light", **EXT.STYLE["metal_hi"]}[school]
    glow = {"pressure": "p_glow_band", "ice": "i_glow_band", "blood": "b_glow_band", **EXT.STYLE["glow"]}[school]
    core = {"pressure": "p_core", "ice": "i_core", "blood": "b_core", **EXT.STYLE["core"]}[school]
    gem = {"pressure": "p_channel", "ice": "i_crystal_glow", "blood": "b_ruby", **EXT.STYLE["gem"]}[school]

    # binding: hand in both views (dynamic Molang like the vanilla spyglass)
    m.bone("book", pivot=(0, 0, 0), binding="q.item_slot_to_bone_name(c.item_slot)")
    m.bone("anchor", "book", pivot=(0, 0, 0))
    m.bone("lift", "anchor", pivot=(0, 0, 0))
    m.bone("bookc", "lift", pivot=(0, 0, 0))
    sp = m.bone("spine", "bookc", pivot=(0, 0, 0))
    sp.box((-s - c, -H / 2, -c), (2 * (s + c), H, c), cover_side, faces={"north": R_spine})
    # raised spine bands
    for yy in (-H * 0.36, -H * 0.12, H * 0.12, H * 0.36):
        sp.box((-s - c - 0.05, yy - 0.18, -c - 0.12), (2 * (s + c) + 0.1, 0.36, 0.14), metal)

    for side in ("r", "l"):
        sign = 1 if side == "r" else -1
        hinge = sign * s
        hb = m.bone(f"half_{side}", "bookc", pivot=(hinge, 0, 0))
        x0 = hinge if sign > 0 else hinge - W
        art = R_back if side == "r" else R_front
        hb.box((x0, -H / 2, -c), (W, H, c), cover_side, faces={"north": art})
        px0 = x0 + (0.12 if sign > 0 else 0.15)
        pg = m.bone(f"pages_{side}", f"half_{side}", pivot=(hinge, 0, 0))
        pg.box((px0, -H / 2 + 0.16, 0), (W - 0.27, H - 0.32, p), edge_style, faces={"south": R_page})
        # corner reinforcements / frozen corners / gothic corners (raised, outward = -Z)
        orn = m.bone(f"orn_{side}", f"half_{side}", pivot=(hinge, 0, 0))
        for cxs in (0, 1):
            for cys in (0, 1):
                xx = x0 + (0.05 if cxs == 0 else W - 1.25)
                yy = -H / 2 + (0.05 if cys == 0 else H - 1.25)
                orn.box((xx, yy, -c - 0.16), (1.2, 1.2, 0.18), metal_hi)
                if school == "ice":
                    # sharp frozen corner spikes
                    orn.cbox((xx + 0.6, yy + 0.6, -c - 0.34), (0.42, 0.42, 0.42), "i_crystal_glow", rotation=(45, 45, 0))
                if school == "blood":
                    orn.cbox((xx + 0.6, yy + 0.6, -c - 0.3), (0.34, 0.34, 0.34), "b_ruby", rotation=(0, 0, 45))
                if school in EXT.DIMS:
                    EXT.corner(orn, school, xx, yy, c)
        # frame strips along the outer edges
        orn.box((x0 + 0.05, -H / 2 + 1.25, -c - 0.08), (0.28, H - 2.5, 0.09), metal)
        orn.box((x0 + W - 0.33, -H / 2 + 1.25, -c - 0.08), (0.28, H - 2.5, 0.09), metal)
        orn.box((x0 + 1.25, -H / 2 + 0.05, -c - 0.08), (W - 2.5, 0.28, 0.09), metal)
        orn.box((x0 + 1.25, H / 2 - 0.33, -c - 0.08), (W - 2.5, 0.28, 0.09), metal)

    # --------------------------------------------------------------- front emblem (on half_l outer face)
    ex, ey, ez = -s - W / 2, 0.0, -c
    if school == "pressure":
        m.bone("emblem", "half_l", pivot=(ex, ey, ez), rotation=(90, 0, 0))
        for i, r in enumerate([0.6, 0.95, 1.3, 1.65, 2.0]):
            rb = m.bone(f"g_ring{i}" if i % 2 == 0 else f"ring{i}", "emblem", pivot=(ex, ey, ez))
            rb.ring((ex, ey + 0.12 + 0.03 * i, ez), r, 0.16, 0.1 + 0.02 * i, 12 + 2 * i,
                    glow if i % 2 == 0 else metal)
        m.bone("g_core", "emblem", pivot=(ex, ey, ez)).solid_cylinder((ex, ey, ez), 0.36, 0.34, core, layers=3)
    elif school == "ice":
        m.bone("emblem", "half_l", pivot=(ex, ey, ez), rotation=(90, 0, 0))
        hx = m.bone("hexrings", "emblem", pivot=(ex, ey, ez))
        hx.hexagon((ex, ey + 0.06, ez), 2.05, 0.16, 0.1, metal, start=0)
        hx.hexagon((ex, ey + 0.06, ez), 1.55, 0.12, 0.08, metal, start=30)
        m.bone("g_hexglow", "emblem", pivot=(ex, ey, ez)).hexagon((ex, ey + 0.08, ez), 1.8, 0.08, 0.06, glow, start=0)
        cr = m.bone("crystal", "emblem", pivot=(ex, ey, ez))
        for i in range(6):
            arm = m.bone(f"arm{i}", "crystal", pivot=(ex, ey, ez), rotation=(0, 60 * i, 0))
            arm.cbox((ex + 0.62, ey + 0.16, ez), (1.24, 0.16, 0.22), "i_crystal_glow")
            arm.cbox((ex + 1.3, ey + 0.16, ez), (0.3, 0.14, 0.3), "i_crystal_glow", rotation=(0, 45, 0))
        cr.cbox((ex, ey + 0.2, ez), (0.42, 0.3, 0.42), "i_crystal_glow", rotation=(0, 45, 0))
        m.bone("g_core", "emblem", pivot=(ex, ey, ez)).cbox((ex, ey + 0.32, ez), (0.26, 0.1, 0.26), core)
    elif school in EXT.DIMS:
        EXT.emblem(m, school, ex, ey, ez, glow, metal, core)
    else:
        m.bone("emblem", "half_l", pivot=(ex, ey - 0.3, ez), rotation=(90, 0, 0))
        hb = m.bone("heart", "emblem", pivot=(ex, ey - 0.3, ez))
        # heart from stacked boxes (two lobes + tapering point)
        hy = ey - 0.3
        for (dx, dz, w, d) in ((-0.42, -0.35, 0.8, 0.8), (0.42, -0.35, 0.8, 0.8), (0, 0.05, 1.3, 0.75), (0, 0.45, 0.8, 0.5), (0, 0.72, 0.36, 0.3)):
            hb.cbox((ex + dx, hy + 0.2, ez + dz), (w, 0.32, d), "b_ruby", rotation=(0, 0, 0))
        m.bone("g_heartglow", "emblem", pivot=(ex, ey - 0.3, ez)).cbox((ex, hy + 0.38, ez - 0.05), (0.7, 0.05, 0.6), core)
        # gothic arch in blackened silver around the heart (raised strips)
        arch = m.bone("arch", "emblem", pivot=(ex, ey - 0.3, ez))
        for sgn in (-1, 1):
            arch.cbox((ex + sgn * 1.9, hy + 0.08, ez + 0.5), (0.2, 0.14, 3.2), metal)
            arch.cbox((ex + sgn * 1.25, hy + 0.08, ez - 1.75), (0.2, 0.14, 1.6), metal, rotation=(0, -sgn * 35, 0))
        arch.cbox((ex, hy + 0.12, ez - 2.35), (0.32, 0.2, 0.32), "b_ruby", rotation=(0, 45, 0))

    # --------------------------------------------------------------- flipping pages (pivot at spine center)
    for i in range(3):
        fb = m.bone(f"flip{i}", "bookc", pivot=(0, 0, p + 0.03 + 0.012 * i))
        fb.box((0.06, -H / 2 + 0.22, p + 0.02 + 0.012 * i), (s + W - 0.5, H - 0.44, 0.02), edge_style,
               faces={"south": R_page, "north": R_page})

    # --------------------------------------------------------------- flow overlays (2nd render controller, uv_anim)
    full = ('rect', 0, 0, 256, 256)
    fo = m.bone("flow_spine", "spine", pivot=(0, 0, 0))
    fo.box((-s - c + 0.1, -H / 2 + 0.2, -c - 0.02), (2 * (s + c) - 0.2, H - 0.4, 0.0), None, faces={"north": full, "south": None})
    fl = m.bone("flow_front", "half_l", pivot=(-s, 0, 0))
    fl.box((-s - W + 0.3, -H / 2 + 0.3, -c - 0.03), (W - 0.6, H - 0.6, 0.0), None, faces={"north": full, "south": None})
    fp = m.bone("flow_pages", "pages_r", pivot=(s, 0, 0))
    fp.box((s + 0.3, -H / 2 + 0.4, p + 0.01), (W - 0.8, H - 0.8, 0.0), None, faces={"south": full, "north": None})

    # --------------------------------------------------------------- casting sigil (behind the open book)
    sg = m.bone("g_sigil", "lift", pivot=(0, 0, -0.8))
    sgr = m.bone("g_sigil_spin", "g_sigil", pivot=(0, 0, -0.8), rotation=(90, 0, 0))
    sgr.box((-5.2, 0, -0.8 - 5.2), (10.4, 0.0, 10.4), None, faces={"up": R_sigil, "down": R_sigil})
    dims = dict(H=H, W=W, T=T, s=s, p=p, c=c)
    if school in EXT.DIMS:
        EXT.extra_geometry(m, school, dims)
    return m, dims


# ============================================================================== animations

def book_animations(school, dims):
    n = f"animation.grimoire.book_{school}"
    A = []
    # pose by view (spyglass-style offsets; geometry authored at origin)
    pose = Anim(f"{n}.pose", loop=True)
    pose.pos("anchor", ["c.is_first_person ? 3.5 : 2.0", "c.is_first_person ? 21.5 : 21.0", "c.is_first_person ? -5.0 : -1.5"])
    pose.rot("anchor", ["c.is_first_person ? 18.0 : 5.0", "c.is_first_person ? -40.0 : 70.0", "c.is_first_person ? -6.0 : 8.0"])
    A.append(pose)
    # closed + floating idle (gentle bob and sway)
    closed = Anim(f"{n}.closed", loop=True)
    closed.rot("half_r", [0, -90, 0]).rot("half_l", [0, 90, 0])
    for i in range(3):
        closed.rot(f"flip{i}", [0, -90, 0])
    closed.pos("lift", [0, "math.sin(q.life_time * 120) * 0.35 + 1.2", 0])
    closed.rot("lift", ["math.sin(q.life_time * 70) * 3", "math.sin(q.life_time * 45) * 6", "math.cos(q.life_time * 60) * 3"])
    closed.scale("g_sigil", [0, 0, 0])
    A.append(closed)
    # opening transition then open idle with charge pulse
    opening = Anim(f"{n}.open", loop="hold_on_last_frame", length=0.35)
    opening.rot("half_r", {0: [0, -90, 0], 0.35: [0, -14, 0]}).rot("half_l", {0: [0, 90, 0], 0.35: [0, 14, 0]})
    opening.pos("lift", {0: [0, 1.2, 0], 0.35: [0, 3.4, -1.5]})
    opening.scale("g_sigil", {0: [0, 0, 0], 0.35: [1, 1, 1]})
    A.append(opening)
    charge = Anim(f"{n}.charge", loop=True)
    charge.rot("lift", ["math.sin(q.life_time * 200) * 1.2", 0, "math.sin(q.life_time * 160) * 1.2"])
    charge.rot("g_sigil_spin", [0, "q.life_time * 120", 0])
    charge.scale("g_sigil", ["1 + math.sin(q.life_time * 300) * 0.05"] * 3)
    for i in range(3):
        # pages flutter continuously while preparing
        charge.rot(f"flip{i}", [0, f"-14 - math.mod(q.life_time * 220 + {i * 60}, 152)", 0])
    A.append(charge)
    # release burst
    rel = Anim(f"{n}.release", length=0.5)
    rel.pos("lift", {0: [0, 3.4, -1.5], 0.1: [0, 3.8, -4.0], 0.5: [0, 1.2, 0]})
    rel.scale("g_sigil", {0: [1, 1, 1], 0.12: [1.8, 1.8, 1.8], 0.3: [0, 0, 0]})
    rel.rot("half_r", {0: [0, -14, 0], 0.5: [0, -90, 0]}).rot("half_l", {0: [0, 14, 0], 0.5: [0, 90, 0]})
    for i in range(3):
        rel.rot(f"flip{i}", {0: [0, -60, 0], 0.5: [0, -90, 0]})
    A.append(rel)
    # spell selection: one page flip per crouch press (book briefly opens)
    flip = Anim(f"{n}.flip", length=0.55)
    flip.rot("half_r", {0: [0, -90, 0], 0.12: [0, -20, 0], 0.42: [0, -20, 0], 0.55: [0, -90, 0]})
    flip.rot("half_l", {0: [0, 90, 0], 0.12: [0, 20, 0], 0.42: [0, 20, 0], 0.55: [0, 90, 0]})
    flip.rot("flip0", {0: [0, -90, 0], 0.12: [0, -22, 0], 0.4: [0, -158, 0], 0.55: [0, -90, 0]})
    flip.rot("flip1", {0: [0, -90, 0], 0.12: [0, -22, 0], 0.55: [0, -90, 0]})
    flip.rot("flip2", {0: [0, -90, 0], 0.12: [0, -22, 0], 0.55: [0, -90, 0]})
    flip.pos("lift", {0: [0, 1.2, 0], 0.15: [0, 2.0, -0.5], 0.55: [0, 1.2, 0]})
    flip.scale("g_sigil", [0, 0, 0])
    A.append(flip)
    # emblem life (always): rings counter-rotate / crystal turns / heart beats
    life = Anim(f"{n}.emblem", loop=True)
    if school == "pressure":
        for i in range(5):
            bone = f"g_ring{i}" if i % 2 == 0 else f"ring{i}"
            life.rot(bone, [0, f"q.life_time * {(40 + i * 18) * (1 if i % 2 else -1)}", 0])
        life.scale("g_core", ["1 + math.sin(q.life_time * 400) * 0.12"] * 3)
    elif school == "ice":
        life.rot("crystal", [0, "q.life_time * 30", 0])
        life.rot("hexrings", [0, "-q.life_time * 12", 0])
        life.scale("g_core", ["1 + math.sin(q.life_time * 260) * 0.15"] * 3)
    elif school in EXT.DIMS:
        EXT.emblem_life(life, school)
    else:
        beat = "1 + math.pow(math.max(0, math.sin(q.life_time * 216)), 12) * 0.22"
        life.scale("heart", [beat, beat, beat])
        life.scale("g_heartglow", [f"({beat}) * 1.15"] * 3)
    A.append(life)
    if school in EXT.DIMS:
        A.append(EXT.extras(n, school))
    return A


def book_controller(school):
    n = f"animation.grimoire.book_{school}"
    ctrl = {
        "initial_state": "closed",
        "states": {
            "closed": {
                "animations": ["closed"],
                "transitions": [{"opening": "q.is_using_item"}, {"flip": "q.is_sneaking"}],
                "blend_transition": 0.15,
            },
            "flip": {
                "animations": ["flip"],
                "on_entry": ["v.flip_t = q.life_time;"],
                "transitions": [{"opening": "q.is_using_item && !q.is_sneaking"}, {"flip_hold": "q.life_time - v.flip_t > 0.55"}],
                "blend_transition": 0.08,
            },
            "flip_hold": {
                "animations": ["closed"],
                "transitions": [{"closed": "!q.is_sneaking"}, {"opening": "q.is_using_item && !q.is_sneaking"}],
                "blend_transition": 0.1,
            },
            "opening": {
                "animations": ["open", "charge"],
                "transitions": [{"release": "!q.is_using_item"}, {"flip": "q.is_sneaking"}],
                "blend_transition": 0.1,
            },
            "release": {
                "animations": ["release"],
                "on_entry": ["v.rel_t = q.life_time;"],
                "transitions": [{"closed": "q.life_time - v.rel_t > 0.5"}, {"opening": "q.is_using_item && q.life_time - v.rel_t > 0.2"}],
                "blend_transition": 0.05,
            },
        },
    }
    return {f"controller.animation.grimoire.book_{school}": ctrl}


def attachable(school):
    n = f"book_{school}"
    out = _attachable(school, n)
    if school in EXT.DIMS:
        d = out["minecraft:attachable"]["description"]
        d["animations"]["extras"] = f"animation.grimoire.{n}.extras"
        d["scripts"]["initialize"] = ["v.flip_t = 0; v.rel_t = 0; v.ck = 0;"]
        d["scripts"]["pre_animation"] = ["v.ck = math.lerp(v.ck, q.is_using_item ? 1.0 : 0.0, 0.18);"]
        d["scripts"]["animate"].append("extras")
    return out


def _attachable(school, n):
    return {
        "format_version": "1.10.0",
        "minecraft:attachable": {
            "description": {
                "identifier": f"grimoire:{school}",
                "materials": {"default": "entity_emissive_alpha", "trans": "entity_alphablend", "glow": "entity_beam_additive"},
                "textures": {
                    "default": f"textures/entity/grimoire/{n}",
                    "flow": f"textures/entity/grimoire/{n}_flow",
                },
                "geometry": {"default": f"geometry.grimoire.{n}"},
                "animations": {
                    "pose": f"animation.grimoire.{n}.pose",
                    "closed": f"animation.grimoire.{n}.closed",
                    "open": f"animation.grimoire.{n}.open",
                    "charge": f"animation.grimoire.{n}.charge",
                    "release": f"animation.grimoire.{n}.release",
                    "flip": f"animation.grimoire.{n}.flip",
                    "emblem": f"animation.grimoire.{n}.emblem",
                    "ctrl": f"controller.animation.grimoire.{n}",
                },
                "scripts": {
                    "initialize": ["v.flip_t = 0; v.rel_t = 0;"],
                    "animate": ["pose", "emblem", "ctrl"],
                },
                "render_controllers": [
                    "controller.render.grimoire.book",
                    "controller.render.grimoire.book_flow",
                ],
            }
        },
    }


BOOK_RENDER_CONTROLLERS = {
    "format_version": "1.10.0",
    "render_controllers": {
        "controller.render.grimoire.book": {
            "geometry": "Geometry.default",
            "textures": ["Texture.default"],
            "materials": [{"*": "Material.default"}, {"t_*": "Material.trans"}, {"g_*": "Material.glow"}],
            "part_visibility": [{"*": True}, {"flow_*": False}],
        },
        "controller.render.grimoire.book_flow": {
            "geometry": "Geometry.default",
            "textures": ["Texture.flow"],
            "materials": [{"*": "Material.glow"}],
            "part_visibility": [{"*": False}, {"flow_*": True}],
            "uv_anim": {"offset": [0.0, "math.mod(q.life_time * 0.35, 1.0)"], "scale": [1.0, 1.0]},
        },
    },
}


def write_books(rp):
    for school in BOOKS:
        m, dims = build_book(school)
        dump(f"{rp}/models/entity/grimoire/book_{school}.geo.json", geometry_file([m]))
        m.atlas.save(f"{rp}/textures/entity/grimoire/book_{school}.png")
        flow = paint_flow(school, 256, 256)
        Image.fromarray(flow.astype(np.uint8), 'RGBA').save(f"{rp}/textures/entity/grimoire/book_{school}_flow.png")
        dump(f"{rp}/animations/grimoire/book_{school}.animation.json", anim_file(book_animations(school, dims)))
        dump(f"{rp}/animation_controllers/grimoire/book_{school}.ac.json", controller_file(book_controller(school)))
        dump(f"{rp}/attachables/grimoire_{school}.json", attachable(school))
    dump(f"{rp}/render_controllers/grimoire_book.render_controllers.json", BOOK_RENDER_CONTROLLERS)
