"""
Second HD particle atlas: textures/particle/legends_fx2.png (512x512, 128 px per cell, the particle
JSON addresses it in 128x128 UV units, 32 per cell). White/grey sprites that the particles tint.

  row 0: sigil taotie (leiwen key band), sigil nidhogg (runes + roots), sigil hanuman (lotus +
         chakra), sigil alicorn (eight-point star)
  row 1: sigil tenko (nine tomoe + mitsudomoe), sigil logos (heptagram + seven seals + eye),
         ground crack, sun rays
  row 2: lightning bolt A, lightning bolt B, energy rim, anamorphic flare
  row 3: comet (head at the bottom), sakura blossom, wind swirl, energy dome (fresnel sphere)
"""
import math
import sys

import numpy as np
from PIL import Image

C = 128
N = 4
TAU = 2 * math.pi


def grid():
    y, x = np.mgrid[0:C, 0:C].astype(np.float32)
    return (x + 0.5) / C - 0.5, (y + 0.5) / C - 0.5      # -0.5..0.5, y down


def polar():
    x, y = grid()
    return np.hypot(x, y) * 2.0, np.arctan2(y, x)       # r 0..1 at the cell edge


def ring(r, r0, w):
    return np.exp(-((r - r0) / w) ** 2)


def seg_dist(x, y, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy + 1e-9
    t = np.clip(((x - ax) * dx + (y - ay) * dy) / L2, 0.0, 1.0)
    return np.hypot(x - (ax + t * dx), y - (ay + t * dy)), t


def lines(x, y, segs, w, glow=0.0):
    """segs: [(a, b, w0, w1)] in cell coords (-0.5..0.5). Returns alpha."""
    acc = np.zeros_like(x)
    for a, b, w0, w1 in segs:
        d, t = seg_dist(x, y, a, b)
        ww = (w0 + (w1 - w0) * t) * w
        acc = np.maximum(acc, np.exp(-(d / np.maximum(1e-4, ww)) ** 2))
        if glow:
            acc = np.maximum(acc, glow * np.exp(-(d / np.maximum(1e-4, ww * 5)) ** 2))
    return acc


def poly(pts, closed=True, w0=1.0, w1=1.0):
    seq = list(pts) + ([pts[0]] if closed else [])
    return [(seq[i], seq[i + 1], w0, w1) for i in range(len(seq) - 1)]


def pol(r, a):
    return (0.5 * r * math.cos(a), 0.5 * r * math.sin(a))


def frame(r, ang, ticks=36):
    """Shared sigil frame: double outer ring with ticks, inner ring."""
    a = ring(r, 0.95, 0.012) + ring(r, 0.885, 0.008) * 0.9 + ring(r, 0.56, 0.008) * 0.8
    tick = (np.abs(np.mod(ang / TAU * ticks + 0.5, 1.0) - 0.5) < 0.06) * (r > 0.89) * (r < 0.945)
    return a + tick * 0.8


def finish(a, lum=None):
    a = np.clip(np.nan_to_num(a), 0, 1)
    if lum is None:
        lum = np.clip(0.82 + a * 0.18, 0, 1)
    return a, lum


# ----------------------------------------------------------------------------- sigils
def sig_taotie():
    x, y = grid()
    r, ang = polar()
    a = frame(r, ang, 32)
    # leiwen (thunder / key) band: concentric squares in 16 polar cells
    seg = 16
    fu = np.mod(ang / TAU * seg, 1.0) - 0.5
    fv = (r - 0.6) / 0.27 - 0.5
    band = (r > 0.6) * (r < 0.87)
    ch = np.maximum(np.abs(fu), np.abs(fv))
    key = np.exp(-((np.mod(ch * 3.2, 1.0) - 0.5) / 0.12) ** 2) * (ch < 0.46)
    # break each square on one side so it reads as a spiral key
    key *= ~((fu > 0.0) & (np.abs(fv) < 0.12))
    a = a + key * band * 0.85
    # two crossed squares (eight-point bronze star) and the taotie's eyes
    sq1 = [pol(0.5, k * TAU / 4 + TAU / 8) for k in range(4)]
    sq2 = [pol(0.5, k * TAU / 4) for k in range(4)]
    a = np.maximum(a, lines(x, y, poly(sq1) + poly(sq2), 0.008))
    for s in (-1, 1):
        ex, ey = s * 0.085, -0.02
        d = np.hypot(x - ex, y - ey) * 2
        a = np.maximum(a, ring(d, 0.07, 0.012) + np.exp(-(d / 0.03) ** 2))
    a = np.maximum(a, ring(r, 0.3, 0.008))
    return finish(a)


def sig_nidhogg():
    x, y = grid()
    r, ang = polar()
    rng = np.random.default_rng(7)
    a = ring(r, 0.96, 0.01) + ring(r, 0.58, 0.008)
    # jagged fang ring
    tri = np.abs(np.mod(ang / TAU * 28, 1.0) - 0.5) * 2
    a = a + ring(r, 0.84 + 0.07 * tri, 0.01)
    # rune glyphs between 0.62 and 0.8
    segs = []
    n = 20
    for i in range(n):
        th = i * TAU / n
        r0, r1 = 0.63, 0.79
        ca, sa = math.cos(th), math.sin(th)
        tx, ty = -sa, ca                       # tangential

        def P(rr, tt):
            return (0.5 * (rr * ca) + tt * tx * 0.5, 0.5 * (rr * sa) + tt * ty * 0.5)
        segs.append((P(r0, 0), P(r1, 0), 1, 1))
        kind = rng.integers(0, 4)
        if kind == 0:
            segs.append((P(0.7, 0), P(0.77, 0.06), 1, 1))
        elif kind == 1:
            segs.append((P(0.66, -0.05), P(0.75, 0.05), 1, 1))
            segs.append((P(0.66, 0.05), P(0.75, -0.05), 1, 1))
        elif kind == 2:
            segs.append((P(0.72, 0), P(0.66, 0.06), 1, 1))
            segs.append((P(0.72, 0), P(0.78, 0.06), 1, 1))
        else:
            segs.append((P(0.76, 0), P(0.7, -0.06), 1, 1))
            segs.append((P(0.7, -0.06), P(0.65, 0), 1, 1))
    a = np.maximum(a, lines(x, y, segs, 0.007))
    # roots of the world tree gnawed at the centre
    roots = []
    for i in range(7):
        th = i * TAU / 7 + rng.uniform(-0.15, 0.15)
        p = (0.0, 0.0)
        rr = 0.05
        while rr < 0.52:
            rr2 = rr + rng.uniform(0.07, 0.11)
            th += rng.uniform(-0.3, 0.3)
            q = pol(rr2, th)
            roots.append((p, q, 1.6 - rr * 2, 1.6 - rr2 * 2))
            if rng.random() < 0.45 and rr2 < 0.45:
                bq = pol(rr2 + 0.1, th + rng.choice([-0.5, 0.5]))
                roots.append((q, bq, 1.0 - rr2, 0.4))
            p, rr = q, rr2
    a = np.maximum(a, lines(x, y, roots, 0.009, glow=0.25))
    a = np.maximum(a, np.exp(-(r / 0.08) ** 2))
    return finish(a)


def sig_hanuman():
    x, y = grid()
    r, ang = polar()
    a = frame(r, ang, 24)
    # twelve lotus petals (outline + midrib) between 0.58 and 0.86
    seg = 12
    fu = np.mod(ang / TAU * seg, 1.0) - 0.5
    t = np.clip((r - 0.58) / 0.28, 0, 1)
    half = 0.46 * np.clip(np.sin(np.pi * t), 0, 1) ** 0.8 * (1 - t * 0.35)
    inside = (r > 0.58) * (r < 0.87)
    edge = np.exp(-((np.abs(fu) - half) / 0.035) ** 2) * inside
    rib = np.exp(-(fu / 0.02) ** 2) * inside * (t < 0.85)
    a = a + edge * 0.95 + rib * 0.5
    # flame tips outside the frame
    fl = np.mod(ang / TAU * 24, 1.0) - 0.5
    tip = np.clip(1 - np.abs(fl) * 6 - (r - 0.95) * 18, 0, 1) * (r > 0.95) * (r < 1.0)
    a = a + tip * 0.6
    # Sudarshana wheel: two rings and twelve spokes
    a = np.maximum(a, ring(r, 0.36, 0.01) + ring(r, 0.17, 0.01))
    spokes = (np.abs(np.mod(ang / TAU * 12, 1.0) - 0.5) > 0.47) * (r > 0.17) * (r < 0.36)
    a = np.maximum(a, spokes * 0.9)
    a = np.maximum(a, np.exp(-(r / 0.07) ** 2))
    return finish(a)


def sig_alicorn():
    x, y = grid()
    r, ang = polar()
    a = frame(r, ang, 48)
    pts = []
    for k in range(16):
        th = k * TAU / 16 - TAU / 4
        if k % 4 == 0:
            rr = 0.86
        elif k % 2 == 0:
            rr = 0.58
        else:
            rr = 0.2
        pts.append(pol(rr, th))
    star = lines(x, y, poly(pts), 0.009)
    spokes = [((0.0, 0.0), pts[k], 0.8, 0.6) for k in range(0, 16, 2)]
    a = np.maximum(a, star + lines(x, y, spokes, 0.006) * 0.6)
    # ring of small stars
    for k in range(12):
        sx, sy = pol(0.72, k * TAU / 12 + TAU / 24)
        d = np.hypot(x - sx, y - sy) * 2
        a = np.maximum(a, np.exp(-(d / 0.025) ** 2))
    a = np.maximum(a, ring(r, 0.12, 0.01))
    return finish(a)


def tomoe(x, y, cx, cy, size, rot):
    """A comma: round head with a tail curling around its centre."""
    acc = np.exp(-(np.hypot(x - cx, y - cy) / (size * 0.42)) ** 4)
    segs = []
    prev = None
    for i in range(10):
        t = i / 9
        th = rot + t * 2.2
        rr = size * (0.35 + 0.65 * t)
        p = (cx + math.cos(th) * rr * 0.9 - math.cos(rot) * size * 0.3,
             cy + math.sin(th) * rr * 0.9 - math.sin(rot) * size * 0.3)
        if prev is not None:
            segs.append((prev, p, 1.0 - t * 0.85 + 0.1, 1.0 - t * 0.85))
        prev = p
    return np.maximum(acc, lines(x, y, segs, size * 0.28))


def sig_tenko():
    x, y = grid()
    r, ang = polar()
    a = frame(r, ang, 30)
    for k in range(9):
        th = k * TAU / 9 - TAU / 4
        cx, cy = pol(0.72, th)
        a = np.maximum(a, tomoe(x, y, cx, cy, 0.075, th + math.pi / 2) * 0.95)
    for k in range(3):
        th = k * TAU / 3
        cx, cy = pol(0.16, th)
        a = np.maximum(a, tomoe(x, y, cx, cy, 0.1, th + math.pi * 0.6))
    a = np.maximum(a, ring(r, 0.42, 0.01))
    return finish(a)


def sig_logos():
    x, y = grid()
    r, ang = polar()
    a = frame(r, ang, 42)
    vs = [pol(0.8, k * TAU / 7 - TAU / 4) for k in range(7)]
    hept = [(vs[k], vs[(k * 3) % 7], 1, 1) for k in range(7)]
    hept = [(vs[(k * 3) % 7], vs[((k + 1) * 3) % 7], 1, 1) for k in range(7)]
    a = np.maximum(a, lines(x, y, hept, 0.007))
    for v in vs:
        d = np.hypot(x - v[0], y - v[1]) * 2
        a = np.maximum(a, ring(d, 0.075, 0.01) + np.exp(-(d / 0.025) ** 2))
    # the eye: vesica of two arcs, iris ring and pupil
    ey = np.abs(y) * 2
    ex = np.abs(x) * 2
    lid = 0.16 * np.clip(1 - (ex / 0.34) ** 2, 0, 1)
    eye_edge = np.exp(-((ey - lid) / 0.012) ** 2) * (ex < 0.34)
    iris = ring(r, 0.1, 0.01) + np.exp(-(r / 0.04) ** 2)
    a = np.maximum(a, eye_edge + iris)
    a = np.maximum(a, ring(r, 0.45, 0.008) * 0.7)
    return finish(a)


# ----------------------------------------------------------------------------- impacts
def crack():
    x, y = grid()
    r, ang = polar()
    rng = np.random.default_rng(11)
    segs = []

    def branch(p, th, rr, w, depth):
        while rr < 0.95:
            rr2 = rr + rng.uniform(0.06, 0.12)
            th2 = th + rng.uniform(-0.22, 0.22)
            q = pol(rr2, th2)
            segs.append((p, q, w, w * 0.85))
            w *= 0.85
            if depth < 1 and rng.random() < 0.22:
                branch(q, th2 + rng.choice([-0.6, 0.6]), rr2, w * 0.7, depth + 1)
            p, rr, th = q, rr2, th2
    for i in range(7):
        th = i * TAU / 7 + rng.uniform(-0.2, 0.2)
        branch(pol(0.1, th), th, 0.1, 1.6, 0)
    a = lines(x, y, segs, 0.011, glow=0.18)
    a = np.maximum(a, np.exp(-(r / 0.14) ** 2) * 0.9)
    a *= np.clip((1.0 - r) * 3, 0, 1)
    return finish(a, np.clip(0.75 + a * 0.25, 0, 1))


def rays():
    r, ang = polar()
    k1 = (0.5 + 0.5 * np.cos(ang * 14)) ** 8
    k2 = (0.5 + 0.5 * np.cos(ang * 9 + 1.3)) ** 14 * 0.7
    fall = np.clip(1 - r, 0, 1) ** 1.4
    a = (np.maximum(k1, k2) * fall) + np.exp(-(r / 0.16) ** 2)
    return finish(a)


def bolt(seed):
    x, y = grid()
    rng = np.random.default_rng(seed)

    def path(p0, p1, rough, depth):
        pts = [p0, p1]
        for _ in range(depth):
            out = [pts[0]]
            for a, b in zip(pts, pts[1:]):
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                mx += rng.uniform(-rough, rough) * L
                out += [(mx, my), b]
            pts = out
        return pts
    main = path((rng.uniform(-0.05, 0.05), -0.49), (rng.uniform(-0.08, 0.08), 0.49), 0.32, 5)
    main = [(max(-0.36, min(0.36, px)), py) for px, py in main]
    segs = [(a, b, 1.0, 1.0) for a, b in zip(main, main[1:])]
    for _ in range(4):
        i = rng.integers(4, len(main) - 8)
        p = main[i]
        q = (max(-0.4, min(0.4, p[0] + rng.choice([-1, 1]) * rng.uniform(0.1, 0.2))), min(0.46, p[1] + rng.uniform(0.1, 0.2)))
        br = [(max(-0.42, min(0.42, bx)), by) for bx, by in path(p, q, 0.4, 3)]
        segs += [(a, b, 0.6, 0.6) for a, b in zip(br, br[1:])]
    a = lines(x, y, segs, 0.012, glow=0.45)
    return finish(a, np.clip(0.85 + a * 0.15, 0, 1))


def rim():
    r, _ = polar()
    a = ring(r, 0.86, 0.06) + ring(r, 0.86, 0.015) * 0.6 + np.clip(r / 0.86, 0, 1) ** 6 * 0.25 * (r < 0.86)
    return finish(a)


def flare():
    x, y = grid()
    a = np.exp(-(y / 0.018) ** 2) * np.exp(-(x / 0.3) ** 2)
    a += np.exp(-(y / 0.05) ** 2) * np.exp(-(x / 0.12) ** 2) * 0.5
    a += np.exp(-(x / 0.012) ** 2) * np.exp(-(y / 0.12) ** 2) * 0.45
    a += np.exp(-(np.hypot(x, y) / 0.05) ** 2)
    return finish(a)


def comet():
    x, y = grid()
    head = np.exp(-(np.hypot(x, y - 0.32) / 0.1) ** 2) + np.exp(-(np.hypot(x, y - 0.32) / 0.04) ** 2)
    t = np.clip((0.32 - y) / 0.8, 0, 1)
    tail = np.exp(-(x / (0.03 + 0.08 * t)) ** 2) * (1 - t) ** 1.3 * (y < 0.32)
    core = np.exp(-(x / (0.006 + 0.02 * t)) ** 2) * (1 - t) ** 2 * (y < 0.32)
    a = head + tail * 0.8 + core * 0.6
    return finish(a)


def sakura():
    x, y = grid()
    acc = np.zeros_like(x)
    for k in range(5):
        th = k * TAU / 5 - TAU / 4
        ca, sa = math.cos(th), math.sin(th)
        u = x * ca + y * sa            # along the petal
        v = -x * sa + y * ca
        e = ((u - 0.2) / 0.19) ** 2 + (v / (0.12 + 0.05 * np.clip(u / 0.35, 0, 1))) ** 2
        petal = np.clip((1 - e) * 4, 0, 1)
        notch = np.clip(1 - (np.abs(v) / 0.035 + (0.39 - u) / 0.06), 0, 1)
        acc = np.maximum(acc, petal * (1 - notch))
    r = np.hypot(x, y) * 2
    lum = np.clip(0.72 + 0.28 * np.exp(-(r / 0.25) ** 2), 0, 1)
    acc = np.maximum(acc, np.exp(-(r / 0.06) ** 2))
    return finish(acc, lum)


def wind():
    r, ang = polar()
    acc = np.zeros_like(r)
    for k in range(3):
        a0 = k * TAU / 3
        rel = np.mod(ang - a0, TAU) / TAU          # 0..1 around the circle
        span = rel < 0.55
        t = rel / 0.55
        rr = 0.25 + 0.6 * t
        w = 0.015 + 0.05 * np.clip(np.sin(np.pi * np.clip(t, 0, 1)), 0, 1)
        acc = np.maximum(acc, np.exp(-((r - rr) / w) ** 2) * span * np.clip(np.sin(np.pi * np.clip(t, 0, 1)), 0, 1) ** 0.6)
    return finish(acc)


def dome():
    x, y = grid()
    r, ang = polar()
    inside = r < 0.92
    fres = (0.12 + 0.88 * np.clip(r / 0.92, 0, 1) ** 5) * inside
    edge = ring(r, 0.92, 0.025)
    # faint hexagonal lattice
    s = 9.0
    q = x * s * 2 / math.sqrt(3)
    rr = y * s - x * s / math.sqrt(3)
    fx = np.abs(np.mod(q, 1.0) - 0.5)
    fy = np.abs(np.mod(rr, 1.0) - 0.5)
    fz = np.abs(np.mod(q + rr, 1.0) - 0.5)
    hexl = (np.minimum(np.minimum(fx, fy), fz) < 0.05) * inside * 0.22
    a = fres + edge + hexl
    return finish(a)


CELLS = [[sig_taotie, sig_nidhogg, sig_hanuman, sig_alicorn],
         [sig_tenko, sig_logos, crack, rays],
         [lambda: bolt(3), lambda: bolt(19), rim, flare],
         [comet, sakura, wind, dome]]


def paint(path):
    out = np.zeros((C * N, C * N, 4), np.float32)
    for row in range(N):
        for col in range(N):
            a, lum = CELLS[row][col]()
            pad = np.ones_like(a)
            pad[:2, :] = pad[-2:, :] = 0
            pad[:, :2] = pad[:, -2:] = 0
            a = a * pad
            for ch in range(3):
                out[row * C:(row + 1) * C, col * C:(col + 1) * C, ch] = lum
            out[row * C:(row + 1) * C, col * C:(col + 1) * C, 3] = a
    img = Image.fromarray((np.clip(np.nan_to_num(out), 0, 1) * 255).astype(np.uint8), "RGBA")
    img.save(path)
    return path


if __name__ == "__main__":
    print(paint(sys.argv[1]))
