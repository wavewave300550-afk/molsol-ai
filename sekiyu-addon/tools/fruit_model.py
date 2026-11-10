"""
The Sekiyu Sekiyu no Mi as a real 3D model, built from the approved reference art
(art/sekiyu_fruit_reference.png).

* Body: the banana's curved centerline (traced from the art) is swept with overlapping rotated
  boxes in three widths, giving a rounded, octagon-like cross-section that keeps the crescent
  silhouette. Every texel of every face is painted by projecting it onto the art (side view), so
  the spirals, amber highlights and fissures are the drawing's own; faces off the picture plane pick
  up the colours at the silhouette edge. Glowing fissure texels get low alpha (emissive material).
* Drips: found automatically along the underside (where the art hangs below the smoothed body
  outline), each a hanging strand with a bulb.
* Stem: a tapered curl following the drawing, with its own drip. Leaf: horizontal strips filling the
  leaf shape (no cut-out transparency, so it works with the emissive material).
* Locators on top of the fruit emit the heated vapour particles.

Units: image pixels * K -> model units (1 unit = 1/16 block). Image left is model -x, so the north
face (the entity's front) shows the drawing unmirrored, +x on the viewer's right.
"""
import math
import os

import numpy as np
from PIL import Image

import oilkit

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "art", "sekiyu_fruit_reference.png")

CELL = 1254 / 40  # the hand-traced control points below are in 40x40 grid cells of the art
K = 0.026          # model units per art pixel (the fruit is ~31 units = ~2 blocks wide at scale 1)
CX, CY = 560.0, 790.0  # art pixel that becomes the model origin: the grip, mid-underside of the body

# centerline of the body, tip (left) -> stem end (top right), in grid cells
BODY = [(1.6, 22.4), (4.0, 24.2), (7.0, 25.6), (10.0, 26.4), (13.0, 26.9), (16.0, 26.9), (19.0, 26.3),
        (22.0, 25.2), (24.8, 23.4), (27.3, 21.0), (29.4, 18.1), (30.9, 15.0), (31.9, 12.0), (32.4, 9.8), (32.6, 8.6)]
STEM = [(32.6, 8.9), (32.6, 7.0), (32.8, 5.2), (33.2, 3.4), (33.9, 2.0), (35.0, 1.0), (36.4, 0.6), (37.7, 1.1),
        (38.4, 2.4), (38.2, 3.8), (37.2, 4.6), (36.1, 4.3), (35.7, 3.3), (36.2, 2.5), (37.0, 2.6)]
LEAF = [(14.6, 11.6), (15.8, 9.0), (17.4, 6.4), (19.6, 4.0), (22.4, 2.4), (25.4, 2.0), (27.8, 3.0), (28.8, 4.6),
        (27.4, 6.0), (24.6, 7.0), (21.4, 7.6), (18.6, 8.6), (16.4, 10.0)]


def catmull(points, n):
    pts = np.array(points, float)
    pts = np.vstack([pts[0] * 2 - pts[1], pts, pts[-1] * 2 - pts[-2]])
    out = []
    segs = len(pts) - 3
    for i in range(n + 1):
        t = i / n * segs
        k = min(int(t), segs - 1)
        u = t - k
        p0, p1, p2, p3 = pts[k:k + 4]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    return np.array(out)


def to_model(ix, iy):
    return (ix - CX) * K, (CY - iy) * K


def to_art(mx, my):
    return CX + mx / K, CY - my / K


class Art:
    """The reference art, with colours bled outward so samples just off the silhouette stay on-model."""

    def __init__(self, scale=4):
        im = Image.open(SRC).convert("RGBA")
        self.full = np.asarray(im, np.float32) / 255.0
        self.scale = scale
        small = im.resize((im.width // scale, im.height // scale), Image.LANCZOS)
        a = np.asarray(small, np.float32) / 255.0
        solid = a[..., 3] > 0.8
        rgb = np.where(solid[..., None], a[..., :3], 0)
        have = solid.copy()
        for _ in range(60):  # bleed nearest colours into the background
            if have.all():
                break
            acc = np.zeros_like(rgb)
            cnt = np.zeros(have.shape, np.float32)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                hs = np.roll(have, (dy, dx), (0, 1))
                acc += np.roll(rgb, (dy, dx), (0, 1)) * hs[..., None]
                cnt += hs
            grow = (~have) & (cnt > 0)
            rgb[grow] = acc[grow] / cnt[grow][:, None]
            have |= grow
        self.rgb = rgb
        self.solid = solid
        self.mask_full = self.full[..., 3] > 0.8

    def sample(self, ix, iy):
        s = self.scale
        x = np.clip((ix / s).astype(int), 0, self.rgb.shape[1] - 1)
        y = np.clip((iy / s).astype(int), 0, self.rgb.shape[0] - 1)
        return self.rgb[y, x]


ART = None


def art():
    global ART
    if ART is None:
        ART = Art()
    return ART


def projected(darken=0.0, glow=True) -> oilkit.Painter:
    """Paint by projecting each texel onto the art along the view axis (z)."""
    def p(pts, face, u, v):
        ix, iy = to_art(pts[:, 0], pts[:, 1])
        col = art().sample(ix, iy)
        if face not in ("north", "south"):
            # off the picture plane the projection smears into stripes: blend in glossy crude oil
            n = oilkit.fbm(pts * np.array([1.0, 1.0, 2.2]), 2.2, seed=7)
            oil = np.stack([0.10 + 0.55 * n ** 3, 0.05 + 0.30 * n ** 3, 0.03 + 0.05 * n ** 3], -1)
            col = (col * 0.55 + oil * 0.45) * (1 - darken)
        out = np.ones((len(pts), 4), np.float32)
        out[:, :3] = col
        if glow:
            r, g, b = col[:, 0], col[:, 1], col[:, 2]
            fissure = (r > 0.82) & (g > 0.18) & (g < 0.62) & (b < 0.3)
            hot = (r > 0.95) & (g > 0.62) & (b < 0.45)
            out[fissure, 3] = 0.3
            out[hot, 3] = 0.6
        return out
    return p


def thickness(center, normal, max_px=260):
    """Distance (art px) to the silhouette edge from `center` along +normal and -normal."""
    m = art().mask_full
    out = []
    for sgn in (1, -1):
        d = 0
        gap = 0
        for step in range(0, max_px, 3):
            x, y = (center + normal * step * sgn).astype(int)
            if not (0 <= x < m.shape[1] and 0 <= y < m.shape[0]) or not m[y, x]:
                gap += 3
                if gap > 9:
                    break
            else:
                gap = 0
                d = step
        out.append(d)
    return out


def build(binding=True, identifier="geometry.sekiyu.fruit"):
    m = oilkit.Model(identifier, tpu=2.4, max_tex=256)
    root = m.bone("fruit", (0, 0, 0), binding="q.item_slot_to_bone_name(c.item_slot)" if binding else None)
    body = m.bone("body", (0, 0, 0), parent="fruit")
    paint = projected()
    paint_side = projected(darken=0.12)

    # ---- body sweep
    cl = catmull([(x * CELL, y * CELL) for x, y in BODY], 40)
    profile = []
    for i in range(len(cl) - 1):
        a, b = cl[i], cl[i + 1]
        c = (a + b) / 2
        t = b - a
        L = np.linalg.norm(t)
        t /= L
        n = np.array([-t[1], t[0]])
        up, dn = thickness(c, n)
        # the underside measurement must not run down the drips: cap by the neighbouring width
        half = max(0.5 * (up + dn), 18)
        off = (up - dn) / 2
        cc = c + n * off
        profile.append((cc, t, L, half))
    # smooth the radii so drips / steam do not create bumps
    radii = np.array([p[3] for p in profile])
    radii = np.convolve(np.pad(radii, 4, mode="edge"), np.ones(9) / 9, mode="valid")
    taper = np.minimum(1.0, np.linspace(0.0, 1.0, len(radii)) * 9 + 0.3)  # rounded tip
    last = len(profile) - 1
    for k, ((cc, t, L, _), r, tp) in enumerate(zip(profile, radii, taper)):
        mx, my = to_model(*cc)
        h = 2 * r * K * tp
        length = L * K + 0.6
        ang = math.degrees(math.atan2(-t[1], t[0]))  # art y points down
        for hw, dw in ((1.0, 0.56), (0.82, 0.86), (0.56, 1.0)):
            hh, dd = h * hw, h * dw
            # the joint faces (local +-x) of inner segments sit inside their neighbours: not textured
            faces = None if k in (0, last) else ("north", "south", "up", "down")
            body.add((mx - length / 2, my - hh / 2, -dd / 2), (length, hh, dd), paint_side if hw < 1 else paint,
                     rotation=(0, 0, round(ang, 2)), pivot=(mx, my, 0), faces=faces)
    # end caps: slightly smaller boxes so the tip and the stem end are rounded
    for idx, scale_ in ((0, 0.55), (len(profile) - 1, 0.8)):
        cc, t, L, _ = profile[idx]
        mx, my = to_model(*cc)
        h = 2 * radii[idx] * K * scale_
        body.add((mx - h / 2, my - h / 2, -h / 2), (h, h, h), paint_side)

    # ---- drips along the underside (where the art hangs below the smoothed outline)
    drips = find_drips(cl, profile, radii)
    dr = m.bone("drips", (0, 0, 0), parent="body")
    for (ix, iy_top, iy_tip, w) in drips:
        x0, y_top = to_model(ix, iy_top)
        _, y_tip = to_model(ix, iy_tip)
        wid = max(0.9, w * K)
        length = max(0.8, y_top - y_tip)
        dr.add((x0 - wid / 2, y_tip + wid * 0.6, -wid / 2), (wid, length - wid * 0.6, wid), paint)
        bulb = wid * 1.45
        dr.add((x0 - bulb / 2, y_tip, -bulb / 2), (bulb, bulb * 0.9, bulb), paint)

    # ---- stem curl (tapered), with a drip from the curl end
    st = m.bone("stem", tuple(to_model(*np.array(STEM[0]) * CELL)) + (0,), parent="fruit")
    sc = catmull([(x * CELL, y * CELL) for x, y in STEM], 26)
    for i in range(len(sc) - 1):
        a, b = sc[i], sc[i + 1]
        c = (a + b) / 2
        t = (b - a) / np.linalg.norm(b - a)
        mx, my = to_model(*c)
        w = (1.9 - 1.05 * i / (len(sc) - 1)) * 1.0
        length = np.linalg.norm(b - a) * K + 0.6
        ang = math.degrees(math.atan2(-t[1], t[0]))
        st.add((mx - length / 2, my - w / 2, -w / 2), (length, w, w), paint, rotation=(0, 0, round(ang, 2)), pivot=(mx, my, 0))
    ex, ey = to_model(*sc[-1])
    st.add((ex - 0.45, ey - 2.6, -0.45), (0.9, 2.2, 0.9), paint)
    st.add((ex - 0.7, ey - 3.6, -0.7), (1.4, 1.2, 1.4), paint)

    # ---- leaf: horizontal strips filling the outline, 0.6 units thick, tilted slightly toward the viewer
    lf = m.bone("leaf", tuple(to_model(28.6 * CELL, 4.4 * CELL)) + (0,), parent="stem", rotation=(0, 14, 0))
    poly = np.array(LEAF) * CELL
    ys = np.arange(poly[:, 1].min(), poly[:, 1].max(), 0.55 / K)
    for y in ys:
        xs = scanline(poly, y + 0.275 / K)
        for x0, x1 in zip(xs[0::2], xs[1::2]):
            mx0, my = to_model(x0, y)
            mx1, _ = to_model(x1, y)
            lf.add((mx0, my - 0.55, -0.3), (mx1 - mx0, 0.55, 0.6), paint)
    # petiole joining the leaf base to the stem
    pet = catmull([(28.4 * CELL, 4.5 * CELL), (30.2 * CELL, 4.9 * CELL), (32.0 * CELL, 5.8 * CELL), (32.8 * CELL, 6.6 * CELL)], 6)
    for i in range(len(pet) - 1):
        a, b = pet[i], pet[i + 1]
        c = (a + b) / 2
        t = (b - a) / np.linalg.norm(b - a)
        mx, my = to_model(*c)
        length = np.linalg.norm(b - a) * K + 0.4
        ang = math.degrees(math.atan2(-t[1], t[0]))
        st.add((mx - length / 2, my - 0.45, -0.45), (length, 0.9, 0.9), paint, rotation=(0, 0, round(ang, 2)), pivot=(mx, my, 0))
    # leaf drip at its lower tip
    tx, ty = to_model(15.0 * CELL, 11.6 * CELL)
    lf.add((tx - 0.4, ty - 2.2, -0.4), (0.8, 2.2, 0.8), paint)
    lf.add((tx - 0.65, ty - 3.1, -0.65), (1.3, 1.1, 1.3), paint)

    # vapour locators on top of the body
    for name, cell in (("vapor_a", (16.0, 21.6)), ("vapor_b", (24.0, 17.5)), ("vapor_c", (29.5, 12.5))):
        x, y = to_model(*np.array(cell) * CELL)
        body.locators[name] = (round(x, 2), round(y, 2), 0.0)
    root.locators["fruit_center"] = (0.0, 0.0, 0.0)
    return m


def scanline(poly, y):
    xs = []
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        if (y0 <= y < y1) or (y1 <= y < y0):
            xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
    return sorted(xs)


def find_drips(cl, profile, radii):
    """Hanging drips: art columns whose lowest solid pixel sits well below the body's underside."""
    m = art().mask_full
    # underside of the body (art px): centre + normal(down side) * radius
    under = {}
    for (cc, t, L, _), r in zip(profile, radii):
        n = np.array([-t[1], t[0]])
        down = n if n[1] > 0 else -n
        p = cc + down * r
        under[int(p[0])] = p[1]
    xs = np.array(sorted(under))
    ys = np.array([under[x] for x in xs])
    drips = []
    col_bottom = []
    for x in range(int(xs.min()) + 30, int(29 * CELL), 2):  # horizontal underside only
        col = np.where(m[:, x])[0]
        if len(col) == 0:
            continue
        uy = np.interp(x, xs, ys)
        below = col[col > uy + 6]
        bottom = below.max() if len(below) else uy
        col_bottom.append((x, uy, bottom))
    run = []
    for x, uy, bottom in col_bottom + [(None, 0, 0)]:
        if x is not None and bottom - uy > 28:
            run.append((x, uy, bottom))
            continue
        if len(run) >= 3:
            xs_ = [r[0] for r in run]
            tip = max(run, key=lambda r: r[2])
            drips.append((float(np.mean(xs_)), float(tip[1]) - 8, float(tip[2]), float(min(70, xs_[-1] - xs_[0] + 2))))
        run = []
    # keep the strongest, well separated drips
    drips.sort(key=lambda d: -(d[2] - d[1]))
    kept = []
    for d in drips:
        if all(abs(d[0] - k[0]) > 45 for k in kept):
            kept.append(d)
    return kept[:12]


if __name__ == "__main__":
    mdl = build()
    mdl.paint()
    print(mdl.stats())
