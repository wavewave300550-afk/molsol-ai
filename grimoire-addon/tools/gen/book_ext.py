"""Expansion 02 grimoires: Plasma (Celestial Ion Furnace), Darkness (The Hollow Codex),
Prism Light (The Chromatic Codex). Plugged into book.py through small hooks so the original three
books are generated exactly as before.

Every new book adds an always-running "extras" animation driven by two variables the attachable keeps:
  v.ck   - smoothed 0..1 "is preparing" (opens mechanisms while Use is held)
  v.flip_t / v.rel_t - start times of the page-flip and release states (already used by book.py)
"""
import math
import numpy as np
from .art import Art

DIMS = {
    "plasma": (35, 26, 7),
    "darkness": (37, 26, 8),
    "prism_light": (34, 25, 6),
}

STYLE = {
    "edge": {"plasma": "pg_plasma", "darkness": "pg_dark", "prism_light": "pg_prism"},
    "cover_side": {"plasma": "pl_ceramic", "darkness": "d_glass", "prism_light": "pr_pearl"},
    "metal": {"plasma": "pl_titanium", "darkness": "d_emerald", "prism_light": "pr_gold"},
    "metal_hi": {"plasma": "pl_titanium", "darkness": "d_plate", "prism_light": "pr_gold"},
    "glow": {"plasma": "pl_glow_band", "darkness": "d_jade_line", "prism_light": "pr_beam"},
    "core": {"plasma": "pl_core", "darkness": "d_void", "prism_light": "pr_core"},
    "gem": {"plasma": "pl_channel", "darkness": "d_jade_tile", "prism_light": "pr_glass_thick"},
}
SIGIL_COL = {"plasma": ((214, 80, 255), (255, 230, 255)), "darkness": ((70, 140, 100), (150, 210, 175)),
             "prism_light": ((240, 214, 150), (255, 255, 255))}
SPECTRUM = [(255, 52, 52), (255, 140, 34), (255, 232, 52), (64, 255, 100), (52, 132, 255), (92, 68, 255), (180, 68, 255)]


def _bar(bone, a, b, y, thick, height, style):
    """Box from 2D point a to b (emblem-local x/z plane) standing `height` above the cover."""
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz)
    ang = math.degrees(math.atan2(-dz, dx))
    bone.cbox(((a[0] + b[0]) / 2, y, (a[1] + b[1]) / 2), (L + thick * 0.6, height, thick), style, rotation=(0, ang, 0))


def _diamond(bone, cx, cz, w, h, y, thick, height, style):
    pts = [(cx, cz + h), (cx + w, cz), (cx, cz - h), (cx - w, cz)]
    for i in range(4):
        _bar(bone, pts[i], pts[(i + 1) % 4], y, thick, height, style)


# ============================================================================== cover painting
def _iridescence(img, strength=0.18):
    """Subtle pearlescent shimmer: hue drifts with position (viewed as angle-dependent on the cover)."""
    h, w = img.shape[:2]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    t = (x / w * 0.7 + y / h * 0.5) * math.tau
    tint = np.stack([0.5 + 0.5 * np.sin(t), 0.5 + 0.5 * np.sin(t + 2.1), 0.5 + 0.5 * np.sin(t + 4.2)], -1) * 255
    img[..., :3] = img[..., :3] * (1 - strength) + tint * strength
    return img


def paint(school):
    from . import book as B
    W, H, SW = B.ART_W, B.ART_H, B.SPINE_W
    rs = np.random.RandomState({"plasma": 61, "darkness": 62, "prism_light": 63}[school])
    cx, cy = W / 2, H / 2
    if school == "plasma":
        ti, ti_hi, vio, mag, white = (150, 156, 178), (226, 230, 246), (180, 60, 255), (255, 70, 210), (255, 238, 255)
        a = Art(W, H)
        a.grain((42, 22, 86), 0.3, 1.4, seed=21)
        # transparent channels revealing moving filaments (the flow overlay animates them in game)
        for x0 in (14, W - 22):
            a.rect(x0, 16, x0 + 8, H - 16, fill=(18, 8, 40), outline=(90, 70, 140), width=0.6)
            for k in range(3):
                pts = [(x0 + 4 + math.sin(t * 0.35 + k * 2.1) * 2.6, 16 + t) for t in range(0, int(H - 32), 2)]
                a.line(pts, (vio, mag, (140, 110, 255))[k], 0.55, glow=0.8)
        # angular titanium reinforcements
        for (x, y, sx, sy) in ((0, 0, 1, 1), (W, 0, -1, 1), (0, H, 1, -1), (W, H, -1, -1)):
            a.poly([(x, y), (x + 18 * sx, y), (x + 10 * sx, y + 6 * sy), (x + 6 * sx, y + 10 * sy), (x, y + 18 * sy)], fill=ti)
            a.poly([(x + 3 * sx, y + 3 * sy), (x + 11 * sx, y + 3 * sy), (x + 3 * sx, y + 11 * sy)], fill=ti_hi)
        a.rect(2, 2, W - 2, H - 2, outline=ti, width=1.6)
        a.line([(26, 6), (W - 26, 6)], ti_hi, 1.2)
        a.line([(26, H - 6), (W - 26, H - 6)], ti_hi, 1.2)
        # Triune Plasma Core: rhombus containment, three intertwined filaments, floating plates
        a.poly([(cx, cy - 34), (cx + 24, cy), (cx, cy + 34), (cx - 24, cy)], outline=ti_hi, width=1.6)
        a.poly([(cx, cy - 28), (cx + 19, cy), (cx, cy + 28), (cx - 19, cy)], outline=(90, 70, 150), width=0.8)
        for f in range(3):
            pts = []
            for t in range(90):
                rr = 18 - t * 0.17
                ang = f * math.tau / 3 + t * 0.14
                pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr * 1.25))
            a.line(pts, (vio, mag, (150, 120, 255))[f], 0.8, glow=0.85)
        for k in range(4):
            ang = math.pi / 4 + k * math.pi / 2
            px, py = cx + math.cos(ang) * 29, cy + math.sin(ang) * 36
            a.poly([(px - 3, py - 2), (px + 3, py - 3), (px + 3, py + 2), (px - 3, py + 3)], fill=ti)
        a.radial_glow(cx, cy, 14, mag, 0.8, glow=0.6)
        a.circle(cx, cy, 3.4, fill=white, glow=1.0)
        front = a.finish()
        b = Art(W, H)
        b.grain((38, 20, 80), 0.3, 1.4, seed=22)
        b.rect(2, 2, W - 2, H - 2, outline=ti, width=1.6)
        b.poly([(cx, cy - 16), (cx + 11, cy), (cx, cy + 16), (cx - 11, cy)], outline=ti_hi, width=1.0)
        b.circle(cx, cy, 2, fill=white, glow=0.8)
        back = b.finish()
        s = Art(SW, H)
        s.grain((34, 18, 70), 0.3, 1.0, seed=23)
        for y0 in range(4, H - 8, 24):          # segmented metal sections (they separate when the book opens)
            s.rect(1, y0, SW - 1, y0 + 19, fill=ti, outline=ti_hi, width=0.5)
        s.rect(SW / 2 - 1.6, 4, SW / 2 + 1.6, H - 4, fill=(20, 8, 44))
        s.line([(SW / 2 + math.sin(t * 0.4) * 1.0, t) for t in range(4, H - 4)], mag, 0.6, glow=0.9)
        spine = s.finish()
        p = Art(64, 80, bg=(238, 232, 255))
        p.grain((238, 232, 255), 0.1, 2, seed=24)
        for row in range(8, 78, 5):
            x = 6
            while x < 58:
                ln = rs.randint(3, 8)
                p.line([(x, row + math.sin(x) * 0.6), (min(58, x + ln), row)], (190, 40, 240), 0.7, glow=0.85)
                x += ln + rs.randint(2, 4)
        p.poly([(32, 14), (40, 26), (32, 38), (24, 26)], outline=(160, 40, 230), width=0.8, glow=0.9)
        page = p.finish()
        return front, back, spine, page

    if school == "darkness":
        g0, plate_cols = (14, 40, 26), [(20, 58, 38), (16, 50, 32), (24, 64, 42), (12, 44, 28), (18, 54, 36), (22, 60, 40), (14, 46, 30)]
        emer, jade, void = (34, 84, 58), (92, 150, 116), (3, 9, 6)
        a = Art(W, H)
        a.grain(g0, 0.25, 1.2, seed=31)
        # seven asymmetrical overlapping armour plates of light-absorbing green glass
        plates = [(4, 4, 52, 40, 3), (40, 6, 92, 50, -4), (2, 36, 44, 90, -2), (46, 44, 94, 86, 5), (6, 82, 50, 120, 4),
                  (44, 80, 92, 120, -3), (22, 30, 74, 96, 0)]
        for k, (x0, y0, x1, y1, sk) in enumerate(plates):
            pts = [(x0 + sk, y0), (x1, y0 + sk), (x1 - sk, y1), (x0, y1 - sk)]
            a.poly(pts, fill=plate_cols[k], outline=emer, width=0.9)
            a.line([pts[0], pts[1]], (60, 110, 84), 0.4)            # faint top bevel
        a.rect(1.5, 1.5, W - 1.5, H - 1.5, outline=emer, width=1.8)
        # The Hollow Eye: layered shutters around a darker vertical diamond absence
        for i, (w, h) in enumerate(((20, 34), (15, 26), (10, 18))):
            a.poly([(cx, cy - h), (cx + w, cy), (cx, cy + h), (cx - w, cy)], fill=(18 + i * 6, 52 + i * 10, 36 + i * 6), outline=jade if i < 2 else emer, width=1.0)
        a.poly([(cx, cy - 12), (cx + 4.2, cy), (cx, cy + 12), (cx - 4.2, cy)], fill=void)
        for k in range(8):                                             # shutter blades
            ang = k * math.pi / 4
            a.line([(cx + math.cos(ang) * 21, cy + math.sin(ang) * 30), (cx + math.cos(ang) * 26, cy + math.sin(ang) * 37)], jade, 0.7)
        front = a.finish(emissive=False)
        b = Art(W, H)
        b.grain(g0, 0.25, 1.2, seed=32)
        for k, (x0, y0, x1, y1, sk) in enumerate(plates[:5]):
            b.poly([(x0 + sk, y0), (x1, y0 + sk), (x1 - sk, y1), (x0, y1 - sk)], fill=plate_cols[k], outline=emer, width=0.8)
        b.rect(1.5, 1.5, W - 1.5, H - 1.5, outline=emer, width=1.8)
        b.poly([(cx, cy - 8), (cx + 3, cy), (cx, cy + 8), (cx - 3, cy)], fill=void)
        back = b.finish(emissive=False)
        s = Art(SW, H)
        s.grain((12, 34, 22), 0.25, 1.0, seed=33)
        for y0 in (6, 30, H - 36, H - 12):
            s.rect(2, y0, SW - 2, y0 + 5, fill=emer)
        s.rect(SW / 2 - 1.4, 10, SW / 2 + 1.4, H - 10, fill=void)          # the vertical slit
        s.line([(SW / 2 - 1.8, 10), (SW / 2 - 1.8, H - 10)], jade, 0.4)
        s.line([(SW / 2 + 1.8, 10), (SW / 2 + 1.8, H - 10)], jade, 0.4)
        spine = s.finish(emissive=False)
        p = Art(64, 80, bg=(74, 100, 86))
        p.grain((74, 100, 86), 0.12, 2, seed=34)
        for row in range(8, 78, 6):                                    # letters made of absence (dark blocks)
            x = 6
            while x < 58:
                ln = rs.randint(2, 6)
                p.rect(x, row - 1.5, min(58, x + ln), row + 1.5, fill=(8, 22, 14))
                if rs.rand() < 0.3:
                    p.rect(x + 1, row - 3, x + 2, row - 1.5, fill=(8, 22, 14))
                x += ln + rs.randint(2, 4)
        page = p.finish(emissive=False)
        return front, back, spine, page

    # ------------------------------------------------------------------ prism light
    pearl, gold, gold_hi, glass = (246, 242, 236), (214, 182, 118), (255, 240, 200), (210, 226, 250)
    a = Art(W, H, bg=pearl)
    a.grain(pearl, 0.06, 1.6, seed=41)
    a.rect(2, 2, W - 2, H - 2, outline=gold, width=1.4)
    a.rect(5, 5, W - 5, H - 5, outline=gold_hi, width=0.5)
    for (x, y, sx, sy) in ((0, 0, 1, 1), (W, 0, -1, 1), (0, H, 1, -1), (W, H, -1, -1)):   # faceted corners
        a.poly([(x, y), (x + 13 * sx, y), (x, y + 13 * sy)], fill=gold)
        a.poly([(x + 3 * sx, y + 3 * sy), (x + 9 * sx, y + 3 * sy), (x + 3 * sx, y + 9 * sy)], fill=glass)
    for (gx, gy, r) in ((18, 22, 7), (W - 18, H - 22, 7), (W - 16, 24, 5)):          # optical mechanisms (gear-rings)
        a.circle(gx, gy, r, outline=gold, width=0.8)
        a.ring_ticks(gx, gy, r, r + 1.6, 16, gold, 0.4)
        a.circle(gx, gy, r * 0.45, fill=glass)
    # Sevenfold Aperture: prism, one white beam in, seven spectral beams out, seven mirrors around
    tri = [(cx, cy - 13), (cx + 12, cy + 8), (cx - 12, cy + 8)]
    a.poly(tri, fill=(232, 240, 252), outline=gold, width=0.9)
    a.line([(6, cy - 10), (cx - 6, cy - 2)], (255, 255, 255), 1.2, glow=0.9)
    for k, col in enumerate(SPECTRUM):
        ang = -0.38 + k * 0.125
        a.line([(cx + 6, cy - 1), (cx + 6 + math.cos(ang) * 30, cy - 1 + math.sin(ang) * 30)], col, 0.8, glow=0.85)
    for k in range(7):
        ang = math.tau * k / 7 - math.pi / 2
        mx, my = cx + math.cos(ang) * 30, cy + math.sin(ang) * 38
        a.line([(mx - 3, my - 2), (mx + 3, my + 2)], gold, 1.2)
    front = _iridescence(a.finish(), 0.12)
    b = Art(W, H, bg=pearl)
    b.grain(pearl, 0.06, 1.6, seed=42)
    b.rect(2, 2, W - 2, H - 2, outline=gold, width=1.4)
    b.circle(cx, cy, 16, outline=gold, width=0.9)
    b.circle(cx, cy, 11, fill=glass)
    back = _iridescence(b.finish(), 0.12)
    s = Art(SW, H, bg=pearl)
    for y0 in range(6, H - 6, 12):                                     # layered translucent components
        s.rect(2, y0, SW - 2, y0 + 7, fill=glass, outline=gold, width=0.5)
    spine = _iridescence(s.finish(), 0.15)
    p = Art(64, 80, bg=(252, 250, 244))
    p.grain((252, 250, 244), 0.05, 2, seed=43)
    for row in range(8, 78, 5):                                        # letters drawn by moving light paths
        x = 6
        while x < 58:
            ln = rs.randint(3, 8)
            p.line([(x, row), (min(58, x + ln), row)], (190, 170, 120), 0.6)
            if rs.rand() < 0.15:
                p.circle(min(58, x + ln), row, 0.7, fill=SPECTRUM[rs.randint(0, 7)], glow=0.9)
            x += ln + rs.randint(2, 4)
    page = p.finish()
    return front, back, spine, page


def paint_sigil(school, a, c, size, col, hi):
    if school == "plasma":
        a.poly([(c, c - size * 0.34), (c + size * 0.24, c), (c, c + size * 0.34), (c - size * 0.24, c)], outline=hi, width=0.8)
        for f in range(3):
            pts = [(c + math.cos(f * 2.094 + t * 0.2) * (size * 0.3 - t * 0.5), c + math.sin(f * 2.094 + t * 0.2) * (size * 0.3 - t * 0.5)) for t in range(30)]
            a.line(pts, col, 0.7)
    elif school == "darkness":
        for k in range(3):
            w, h = size * (0.2 - k * 0.05), size * (0.32 - k * 0.07)
            a.poly([(c, c - h), (c + w, c), (c, c + h), (c - w, c)], outline=hi if k == 0 else col, width=0.7)
    else:
        a.poly([(c, c - size * 0.18), (c + size * 0.16, c + size * 0.1), (c - size * 0.16, c + size * 0.1)], outline=hi, width=0.8)
        for k, colk in enumerate(SPECTRUM):
            ang = -0.4 + k * 0.13
            a.line([(c + size * 0.06, c), (c + size * 0.06 + math.cos(ang) * size * 0.3, c + math.sin(ang) * size * 0.3)], colk, 0.6)


def paint_flow(school, img, x, y, rs, w, h):
    if school == "plasma":
        for k in range(4):                     # filaments drifting through the transparent channels
            px = rs.rand() * w
            xx = px + np.sin(y / h * math.tau * 3 + k) * 3
            d = np.abs(x - xx)
            img += np.exp(-d * d / 0.5)[..., None] * np.array([210, 70, 255], np.float32) * 0.5
    elif school == "darkness":
        for k in range(3):                     # barely-visible jade seams sliding between plates
            yy = (rs.rand() * h + x * 0.5) % h
            d = np.minimum(np.abs(y - yy), h - np.abs(y - yy))
            img += np.exp(-d * d / 0.4)[..., None] * np.array([60, 120, 90], np.float32) * 0.35
    else:
        for k in range(7):                     # faint spectral glints travelling along the optical mechanisms
            px, py = rs.rand() * w, rs.rand() * h
            d2 = (x - px) ** 2 + ((y - py + h / 2) % h - h / 2) ** 2
            img += np.exp(-d2 / 2.0)[..., None] * np.array(SPECTRUM[k], np.float32) * 0.6


# ============================================================================== geometry
def corner(orn, school, xx, yy, c):
    if school == "plasma":
        orn.cbox((xx + 0.6, yy + 0.6, -c - 0.3), (0.5, 0.5, 0.2), "pl_channel", rotation=(0, 0, 45))
    elif school == "darkness":
        orn.cbox((xx + 0.6, yy + 0.6, -c - 0.26), (0.8, 0.8, 0.1), "d_plate", rotation=(0, 0, 20))
    elif school == "prism_light":
        orn.cbox((xx + 0.6, yy + 0.6, -c - 0.3), (0.42, 0.42, 0.42), "pr_glass_thick", rotation=(45, 0, 45))


def emblem(m, school, ex, ey, ez, glow, metal, core):
    m.bone("emblem", "half_l", pivot=(ex, ey, ez), rotation=(90, 0, 0))
    if school == "plasma":
        frame = m.bone("frame", "emblem", pivot=(ex, ey, ez))
        _diamond(frame, ex, ez, 1.75, 2.45, ey + 0.1, 0.16, 0.14, "pl_titanium")
        _diamond(frame, ex, ez, 1.4, 1.95, ey + 0.06, 0.08, 0.08, "pl_dark_metal")
        for f, st in enumerate(("pl_filament", "pl_magenta", "pl_indigo")):
            fb = m.bone(f"g_fil{f}", "emblem", pivot=(ex, ey, ez))
            for t in range(9):
                rr = 1.55 - t * 0.15
                ang = f * math.tau / 3 + t * 0.62
                fb.cbox((ex + math.cos(ang) * rr, ey + 0.16 + 0.03 * math.sin(t + f), ez + math.sin(ang) * rr * 1.25), (0.16, 0.1, 0.16), st)
        m.bone("g_core", "emblem", pivot=(ex, ey, ez)).cbox((ex, ey + 0.2, ez), (0.32, 0.18, 0.32), core)
        pl = m.bone("plates", "emblem", pivot=(ex, ey, ez))
        for k in range(4):
            ang = math.pi / 4 + k * math.pi / 2
            pl.cbox((ex + math.cos(ang) * 1.9, ey + 0.18, ez + math.sin(ang) * 2.4), (0.36, 0.06, 0.26), "pl_titanium", rotation=(0, k * 20, 0))
    elif school == "darkness":
        for i, (w, h, st) in enumerate(((1.95, 3.0, "d_jade_tile"), (1.5, 2.3, "d_emerald"), (1.05, 1.6, "d_jade_tile"))):
            sh = m.bone(f"shutter{i}", "emblem", pivot=(ex, ey, ez))
            _diamond(sh, ex, ez, w, h, ey + 0.08 + i * 0.05, 0.14, 0.1, st)
        eye = m.bone("g_eyeline", "emblem", pivot=(ex, ey, ez))
        _diamond(eye, ex, ez, 0.85, 1.3, ey + 0.2, 0.04, 0.04, "d_jade_line")
        hollow = m.bone("hollow", "emblem", pivot=(ex, ey, ez))
        hollow.cbox((ex, ey + 0.22, ez), (0.42, 0.06, 0.42), "d_void", rotation=(0, 45, 0))
        hollow.cbox((ex, ey + 0.23, ez), (0.24, 0.06, 1.3), "d_void")
    else:
        pr = m.bone("prism", "emblem", pivot=(ex, ey, ez))
        tp = m.bone("t_prism", "prism", pivot=(ex, ey, ez))
        pts = [(ex + math.cos(math.radians(a)) * 1.05, ez + math.sin(math.radians(a)) * 1.05) for a in (90, 210, 330)]
        for i in range(3):
            _bar(tp, pts[i], pts[(i + 1) % 3], ey + 0.45, 0.06, 0.7, "pr_glass_thick")
            _bar(pr, pts[i], pts[(i + 1) % 3], ey + 0.1, 0.1, 0.08, "pr_gold")
        m.bone("g_beam_in", "emblem", pivot=(ex, ey, ez)).cbox((ex - 2.2, ey + 0.4, ez + 0.2), (2.4, 0.1, 0.1), "pr_beam", rotation=(0, -8, 0))
        for i in range(7):
            sb = m.bone(f"g_spec{i}", "emblem", pivot=(ex + 0.5, ey, ez), rotation=(0, -24 + i * 8, 0))
            sb.cbox((ex + 0.5 + 1.25, ey + 0.4, ez), (2.5, 0.08, 0.08), f"pr_s{i}")
        mir = m.bone("mirrors", "emblem", pivot=(ex, ey, ez))
        for i in range(7):
            ang = math.tau * i / 7
            mx, mz = ex + math.cos(ang) * 2.3, ez + math.sin(ang) * 3.0
            mb = m.bone(f"mir{i}", "mirrors", pivot=(mx, ey, mz))
            mb.cbox((mx, ey + 0.2, mz), (0.5, 0.3, 0.06), "pr_mirror", rotation=(0, math.degrees(ang) + 90, 0))
            mb.cbox((mx, ey + 0.06, mz), (0.56, 0.06, 0.1), "pr_gold", rotation=(0, math.degrees(ang) + 90, 0))


def extra_geometry(m, school, d):
    H, W, s, p, c = d["H"], d["W"], d["s"], d["p"], d["c"]
    if school == "plasma":
        # segmented spine sections that separate slightly when the book opens
        for k in range(4):
            seg = m.bone(f"seg{k}", "spine", pivot=(0, -H / 2 + H * (k + 0.5) / 4, -c))
            seg.box((-s - c - 0.08, -H / 2 + H * k / 4 + 0.08, -c - 0.1), (2 * (s + c) + 0.16, H / 4 - 0.16, 0.1), "pl_titanium")
        sf = m.bone("g_spinefil", "bookc", pivot=(0, 0, -c / 2))
        for k in range(3):
            ang = k * math.tau / 3
            for t in range(6):
                y = -H / 2 + 0.6 + (H - 1.2) * ((k / 3 + t / 6) % 1)
                sf.cbox((math.cos(ang + t * 1.1) * (s + c + 0.35), y, -c / 2 + math.sin(ang + t * 1.1) * (s + c + 0.35)), (0.14, 0.4, 0.14),
                        ("pl_filament", "pl_magenta", "pl_indigo")[k])
        st = m.bone("g_streams", "lift", pivot=(0, 0, p))
        for k in range(3):
            st.cbox((-1.2 + k * 1.2, H * 0.3, p + 0.3), (0.12, H * 0.6, 0.12), ("pl_filament", "pl_magenta", "pl_indigo")[k], rotation=(0, 0, (k - 1) * 12))
    elif school == "darkness":
        plates = [(-0.55, 0.32, 0.42, 0.34, 6), (-0.2, 0.36, 0.5, 0.3, -5), (-0.75, -0.05, 0.36, 0.4, -3),
                  (-0.3, -0.08, 0.46, 0.38, 4), (-0.62, -0.4, 0.4, 0.3, 3), (-0.22, -0.38, 0.48, 0.32, -4), (-0.45, 0.12, 0.5, 0.5, 0)]
        for k, (fx, fy, fw, fh, rot) in enumerate(plates):
            cxp, cyp = -s - W / 2 + (fx + 0.45) * W, fy * H
            pb = m.bone(f"plate{k}", "half_l", pivot=(cxp, cyp, -c))
            pb.cbox((cxp, cyp, -c - 0.06 - 0.02 * k), (fw * W, fh * H, 0.06), "d_plate" if k % 2 else "d_glass", rotation=(0, 0, rot))
        sl = m.bone("slit", "spine", pivot=(0, 0, -c))
        sl.box((-0.14, -H / 2 + 0.8, -c - 0.06), (0.28, H - 1.6, 0.05), "d_void")
        m.bone("g_slitedge", "slit", pivot=(0, 0, -c)).box((-0.2, -H / 2 + 0.8, -c - 0.08), (0.4, H - 1.6, 0.02), "d_jade_vline")
        fold = m.bone("folds", "lift", pivot=(0, 0, -1.6))
        for k in range(4):
            fb = m.bone(f"fold{k}", "folds", pivot=(0, 0, -1.6), rotation=(0, 0, k * 90))
            fb.box((0, 0, -1.6), (2.2, 0.04, 2.2), "d_shadow" if k % 2 else "d_glass", faces=None)
    else:
        sp = m.bone("t_spineglass", "spine", pivot=(0, 0, -c))
        for k in range(5):
            sp.box((-s - c + 0.1, -H / 2 + 0.7 + k * (H - 1.4) / 5, -c - 0.16), (2 * (s + c) - 0.2, (H - 1.4) / 5 - 0.25, 0.08), "pr_glass_thick")
        rib = m.bone("ribbons", "bookc", pivot=(0, 0, p))
        for i in range(7):
            rb = m.bone(f"g_rib{i}", "ribbons", pivot=(0, 0, p), rotation=(0, -45 + i * 15, 0))
            rb.box((0.2, -H * 0.42 + i * 0.25, p + 0.05), (W * 1.3, 0.22, 0.03), f"pr_s{i}")
        lens = m.bone("lenses", "lift", pivot=(0, 0, -1.5))
        for k, (z, r) in enumerate(((-1.6, 1.6), (-3.2, 2.3), (-5.0, 3.0))):
            lb = m.bone(f"t_lens{k}", "lenses", pivot=(0, 0, z))
            lb.cbox((0, 0, z), (r * 2, r * 2, 0.08), "pr_glass")
            lb.cbox((0, 0, z), (r * 1.42, r * 1.42, 0.09), "pr_glass", rotation=(0, 0, 45))
            m.bone(f"lensrim{k}", f"t_lens{k}", pivot=(0, 0, z)).cbox((0, r, z), (r * 0.8, 0.12, 0.12), "pr_gold")


# ============================================================================== animation
def emblem_life(life, school):
    if school == "plasma":
        for f in range(3):
            life.rot(f"g_fil{f}", [0, f"q.life_time * {70 + f * 25} * {1 if f % 2 else -1}", 0])
        life.scale("g_core", ["1 + math.sin(q.life_time * 420) * 0.14"] * 3)
        life.rot("plates", [0, "q.life_time * 18", 0])
        life.pos("plates", [0, "math.sin(q.life_time * 90) * 0.05", 0])
        life.rot("g_spinefil", [0, "q.life_time * 140", 0])
    elif school == "darkness":
        life.rot("shutter0", [0, "math.sin(q.life_time * 30) * 4", 0])
        life.rot("shutter1", [0, "-math.sin(q.life_time * 30) * 6", 0])
        life.scale("hollow", ["1 + math.sin(q.life_time * 60) * 0.06"] * 3)
    else:
        for i in range(7):
            life.rot(f"mir{i}", [0, f"math.sin(q.life_time * 50 + {i * 51}) * 25", 0])
        life.scale("t_prism", ["1 + math.sin(q.life_time * 120) * 0.03"] * 3)
        life.rot("lensrim0", [0, 0, "q.life_time * 40"])


def extras(n, school):
    """Always-on animation: mechanisms respond to v.ck (preparing), v.flip_t (selection) and v.rel_t (release)."""
    from .anim import Anim
    a = Anim(f"{n}.extras", loop=True)
    flip = "((q.life_time - v.flip_t) < 0.55 && v.flip_t > 0 ? math.sin((q.life_time - v.flip_t) / 0.55 * 180) : 0)"
    rel = "((q.life_time - v.rel_t) < 0.35 && v.rel_t > 0 ? 1 - (q.life_time - v.rel_t) / 0.35 : 0)"
    openk = f"math.max(v.ck, {flip})"
    if school == "plasma":
        for k in range(4):
            a.pos(f"seg{k}", [0, f"{openk} * {(k - 1.5) * 0.35}", f"-{openk} * 0.15"])
        a.scale("g_streams", [f"v.ck", f"v.ck", f"v.ck"])
        a.scale("frame", [f"1 + {rel} * 0.6", 1, f"1 + {rel} * 0.6"])
    elif school == "darkness":
        dirs = [(-1, 1), (1, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (0, 0.3)]
        for k, (dx, dy) in enumerate(dirs):
            a.pos(f"plate{k}", [f"{openk} * {dx * 0.45}", f"{openk} * {dy * 0.45}", f"-{openk} * {0.05 + k * 0.03}"])
        a.scale("slit", [f"1 + v.ck * 2.4 + math.sin(q.life_time * 80) * 0.2", 1, 1])
        a.scale("emblem", [f"1 - {rel} * 0.45", 1, f"1 - {rel} * 0.45"])
        for k in range(4):
            a.rot(f"fold{k}", [f"(1 - v.ck) * 80 + math.sin(q.life_time * 90 + {k * 90}) * 12 * v.ck", 0, 0])
        a.scale("folds", ["v.ck", "v.ck", "v.ck"])
    else:
        a.scale("ribbons", [flip, flip, flip])
        for k in range(3):
            a.scale(f"t_lens{k}", [f"math.clamp(v.ck * 3 - {k}, 0, 1)"] * 3)
        a.rot("lenses", [0, 0, "q.life_time * 12"])
        a.rot("mirrors", [0, f"{rel} * 90", 0])
    return a
