"""ED05 The Chronicle of Buried Kingdoms -- the fossil monument and its projections.

ed5_tablet_<species>  colossal rough-hewn fossil slab (12 x 9 x 1.4 blocks): strata edges, mineral veins,
                      carved draconic frame, bronze museum clamps and label plaque, painted micro-fossils
                      (ammonites, fern prints, tracks), a moulded cavity, and a deep bas-relief of the species'
                      skeleton in its death pose (the skeleton geometry itself, squashed on one axis).
                      Skins: 0 dormant, 1 awake (relief glows in the lineage colour), 2 blaze (luminous, seams lit).
ed5_memorial          bronze armature that holds the four tablets as a turning four-sided monument.
ed5_inscription_*     draconic inscription rings that descend into the ground where a tablet will rise.
ed5_imprint_*         the fossil image projected onto the ground (outline + bone structure), 4 kinds.
ed5_spike             strata-stone spike with an embedded bone and roots (Nature attacks).
ed5_trail             glowing theropod trackway / heat-haze lane (Heat charges), float property len.
ed5_icefan            sail-shaped fan of ice crystals (Tide attacks).
ed5_gust              wind shockwave ring with spectral feathers (Air wingbeats).

Also writes src/spells/_ed05_assets.ts: state tables, timings and the fossil outlines for the spell.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw

from kit import glyphs, tex
from kit.anim import LIFE, Anim, M, S
from kit.geo import Mat, Model, ring
from kit.pack import ROOT

from . import ed_air, ed_heat, ed_nature, ed_tide
from .ed5_bones import (DEATH, EMERGE_LEN, FLAT, GLOW, GLOW2, KC, LIVING, PANEL, REL_ROT, RETURN_LEN, SPECIES, YAW_OFF, Mats,
                        Sk, bone_tex, flat_vec, posed_quads, relief)
from .ed5_skeletons import STATES as SKEL_STATES

DR = glyphs.DRACONIC
TILT = 60.0                       # formation tilt (face down) in degrees
IMPRINT_SCALE = 1.3               # rendered scale of ed5_imprint (panel 192 x 144 units -> 15.6 x 11.7 blocks)
RX0, RX1, RY0, RY1 = -96.0, 96.0, 0.0, 144.0
RES = 1.0

FRAG_ROWS = [(0, 30, [-96, -22, 38, 96]), (30, 66, [-96, 12, 96]), (66, 104, [-96, -44, 26, 96]), (104, 144, [-96, -6, 96])]
FRAGS = [(x0, x1, y0, y1) for (y0, y1, xs) in FRAG_ROWS for x0, x1 in zip(xs, xs[1:])]
BANDS = {"top": (-96, 96, 127, 144), "bottom": (-96, 96, 0, 17), "left": (-96, -82, 17, 127), "right": (82, 96, 17, 127)}
STRATA = [("#b39a6c", 9), ("#8e7350", 5), ("#c8b994", 8), ("#6b625a", 4), ("#a2865e", 7), ("#d2c4a0", 5), ("#7d6a52", 6),
          ("#b8a07a", 8), ("#5e5850", 3)]
EMBLEM = {"nature": 9, "heat": 5, "tide": 2, "air": 4}

TABLET_STATES = ["hidden", "rise", "stand", "memorial", "awaken", "empty", "receive", "formation", "aim", "project",
                 "project_all", "fracture"]
LEN = {"rise": 2.2, "memorial": 0.6, "awaken": 1.2, "empty": 0.6, "receive": 0.9, "formation": 2.0, "fracture": 1.8}


def spin(rate):
    return M(f"q.life_time*{rate}", lambda t: t * rate)


# ================================================================ seams / stone
def _seams():
    segs = []
    for (y0, y1, xs) in FRAG_ROWS:
        if y0 > 0:
            segs.append(("h", y0, -96, 96))
        for x in xs[1:-1]:
            segs.append(("v", x, y0, y1))
    return segs


SEAMS = _seams()


def seam_dist(X, Y):
    d = np.full(X.shape, 1e9)
    jag = np.sin(X * 0.37) * 1.2 + np.sin(Y * 0.29 + 1.0) * 1.0
    for kind, c, a, b in SEAMS:
        if kind == "h":
            dd = np.where((X >= a) & (X <= b), np.abs(Y - c + jag * 0.6), 1e9)
        else:
            dd = np.where((Y >= a) & (Y <= b), np.abs(X - c + jag * 0.6), 1e9)
        d = np.minimum(d, dd)
    return d


def strata_mat(sp):
    g, g2 = tex.rgb(GLOW[sp]), tex.rgb(GLOW2[sp])
    cols = np.array([tex.rgb(c) for c, _ in STRATA])
    cum = np.cumsum([h for _, h in STRATA])
    tot = float(cum[-1])

    def fn(ctx):
        X, Y, Z = ctx.X, ctx.Y, ctx.Z
        hz = X + Z * 0.7
        n = tex.fbm(hz / 9.0 + 3.0, Y / 9.0, 501)
        yy = Y + (n - 0.5) * 7.0 + np.sin(hz * 0.05) * 2.5
        idx = np.clip(np.searchsorted(cum, np.mod(yy, tot), side="right"), 0, len(cols) - 1)
        col = cols[idx] * (0.86 + 0.24 * tex.fbm(hz / 2.2, Y / 2.2, 503))[..., None]
        col = np.where((np.floor(yy * 1.4) % 3 == 0)[..., None], col * 0.93, col)
        vein = np.abs(np.sin(hz * 0.071 + Y * 0.113 + n * 6.0)) < 0.035
        glow = np.zeros(X.shape)
        vcol = {None: tex.rgb("#ece4d0"), "awake": g, "blaze": g2}[ctx.alt]
        col = np.where(vein[..., None], vcol, col)
        if ctx.alt is not None:
            glow = np.where(vein, 0.85 if ctx.alt == "awake" else 1.0, glow)
        if ctx.alt == "blaze":
            sm = seam_dist(X, Y) < 1.4
            col = np.where(sm[..., None], g2, col)
            glow = np.where(sm, 1.0, glow)
        t = tex.tile(ctx, "#000000", 1.0, 0.0)
        t[..., :3] = np.clip(col, 0, 1)
        t[..., 4] = glow
        return tex.grain(ctx, t, 0.05)
    return Mat(fn, f"ed5strata{sp}", spatial=True, directional=True)


def micro(X, Y, fossils):
    dark = np.zeros(X.shape, dtype=bool)
    light = np.zeros(X.shape, dtype=bool)
    for kind, cx, cy, r, ang in fossils:
        dx, dy = X - cx, Y - cy
        d = np.hypot(dx, dy)
        if kind == "ammonite":
            a = np.arctan2(dy, dx)
            inside = d < r
            spiral = np.abs(np.sin(np.log(d + 0.6) * 5.5 - a)) < 0.33
            ribs = np.abs(np.sin(a * 11 + d * 0.4)) < 0.2
            light |= inside & ~spiral & (d > r * 0.12)
            dark |= inside & (spiral | (ribs & (d > r * 0.55)))
            dark |= np.abs(d - r) < 0.55
        elif kind == "fern":
            ca, sa = math.cos(ang), math.sin(ang)
            u, v = dx * ca + dy * sa, -dx * sa + dy * ca
            stem = (np.abs(v) < 0.55) & (u > 0) & (u < r)
            pin = (u > 1) & (u < r) & (np.abs(v) < (r - u) * 0.36 + 0.6) & (np.abs(np.sin(u * 0.95 + np.abs(v) * 0.75)) < 0.34)
            dark |= stem | pin
        else:   # three-toed track
            for ta in (-0.5, 0.0, 0.5):
                ex, ey = math.cos(ang + ta) * r, math.sin(ang + ta) * r
                tt = np.clip((dx * ex + dy * ey) / (ex * ex + ey * ey), 0, 1)
                dark |= np.hypot(dx - ex * tt, dy - ey * tt) < 1.1 - 0.4 * tt
            dark |= d < r * 0.32
    return dark, light


def panel_mat(sp, H):
    g, g2 = tex.rgb(GLOW[sp]), tex.rgb(GLOW2[sp])

    def fn(ctx):
        X, Y = ctx.X, ctx.Y
        n = tex.fbm(X / 6.0 + 7.0, Y / 6.0, 521)
        col = tex.mix(tex.rgb("#51483d"), tex.rgb("#7c6f5b"), n[..., None])
        col = np.where((np.floor(Y * 1.1 + n * 3) % 4 == 0)[..., None], col * 0.92, col)
        mask, rim, lines = H["mask"], H["rim"], H["lines"]
        hh, ww = mask.shape
        ix = np.clip(((X - RX0) * RES).astype(int), 0, ww - 1)
        iy = np.clip(((RY1 - Y) * RES).astype(int), 0, hh - 1)
        m, rm, ln = mask[iy, ix], rim[iy, ix], lines[iy, ix]
        alt = ctx.alt
        glow = np.zeros(X.shape)
        col = np.where(m[..., None], tex.mix(col, tex.rgb("#2a2119"), 0.72), col)
        col = np.where((m & ln)[..., None], tex.rgb("#4e3d29") if alt is None else tex.mix(tex.rgb("#4e3d29"), g, 0.6), col)
        if alt is not None:
            glow = np.where(m & ln, 0.35 if alt == "awake" else 0.7, glow)
        col = np.where(rm[..., None], {None: tex.rgb("#b49a6c"), "awake": g, "blaze": g2}[alt], col)
        glow = np.where(rm, {None: 0.0, "awake": 0.95, "blaze": 1.0}[alt], glow)
        dk, lt = micro(X, Y, H["fossils"])
        col = np.where(lt[..., None], tex.rgb("#a8916a"), col)
        col = np.where(dk[..., None], tex.rgb("#33291f") if alt is None else tex.mix(tex.rgb("#33291f"), g, 0.55), col)
        if alt is not None:
            glow = np.where(dk, 0.45 if alt == "awake" else 0.8, glow)
        if alt == "blaze":
            sm = seam_dist(X, Y) < 1.4
            col = np.where(sm[..., None], g2, col)
            glow = np.where(sm, 1.0, glow)
        t = tex.tile(ctx, "#000000", 1.0, 0.0)
        t[..., :3] = np.clip(col, 0, 1)
        t[..., 4] = glow
        return tex.grain(ctx, t, 0.04)
    return Mat(fn, f"ed5panel{sp}", spatial=True, directional=True)


def frame_mat(sp, vertical):
    base = tex.glyph_rows(DR, "#4a3c2a", glow=0.0, bg="#b3a383", vertical=vertical, fill=0.8, key=f"ed5fr{vertical}")
    aw = tex.glyph_rows(DR, GLOW[sp], glow=1.0, color2=GLOW2[sp], bg="#b3a383", vertical=vertical, fill=0.8,
                        key=f"ed5frA{sp}{vertical}")
    bz = tex.glyph_rows(DR, "#ffffff", glow=1.0, color2=GLOW2[sp], bg="#d8caa8", bg_glow=0.25, vertical=vertical, fill=0.8,
                        key=f"ed5frB{sp}{vertical}")
    return tex.alt(base, awake=aw, blaze=bz)


def bronze(bright=False):
    base = tex.metal("#a07d45" if bright else "#8a6a3a", "#f0d08a" if bright else "#d8b878", "#4a3418", bands=2.0)

    def post(ctx, t):
        ix, iy = tex.px(ctx)
        n = tex.fbm(ix / 2.5 + ctx.variant * 3.0, iy / 2.5, 611)
        v = n > 0.64
        t[..., :3] = np.where(v[..., None], tex.mix(t[..., :3], tex.rgb("#4f9a82"), 0.7), t[..., :3])
        return t
    return tex.overlay(base, post, f"verd{bright}")


def crack_mat(sp):
    g, g2 = tex.rgb(GLOW[sp]), tex.rgb(GLOW2[sp])

    def fn(ctx):
        u, v = ctx.U * 2 - 1, ctx.V * 2 - 1
        ix, iy = tex.px(ctx)
        trench = (np.abs(v) < 0.16 * (1 - np.abs(u) * 0.7)) & (np.abs(u) < 0.74)
        c = np.abs(tex.vnoise(ix / 3.0, iy / 3.0, 5) - tex.vnoise(ix / 3.0 + 40, iy / 3.0, 9))
        reach = np.hypot(u * 0.9, v * 1.5) < 0.98 - 0.3 * tex.fbm(ix / 5.0, iy / 5.0, 7)
        cr = (c < 0.06) & reach & ~trench
        t = tex.tile(ctx, "#000000", 1.0, 0.0)
        t[..., :3] = np.where(trench[..., None], tex.rgb("#1d150d"), tex.mix(g, g2, 0.3))
        edge = trench & ((np.abs(v) > 0.11 * (1 - np.abs(u) * 0.7)))
        t[..., :3] = np.where(edge[..., None], g, t[..., :3])
        t[..., 3] = (trench | cr).astype(float)
        t[..., 4] = np.where(cr | edge, 0.95, 0.0)
        return t
    return Mat(fn, f"ed5crack{sp}", directional=True)


# ================================================================ silhouette of the relief
def _dilate(m, k):
    out = m.copy()
    for _ in range(k):
        o = out.copy()
        o[1:, :] |= out[:-1, :]
        o[:-1, :] |= out[1:, :]
        o[:, 1:] |= out[:, :-1]
        o[:, :-1] |= out[:, 1:]
        out = o
    return out


def raster(quads):
    W, Hh = int((RX1 - RX0) * RES), int((RY1 - RY0) * RES)
    fill = Image.new("L", (W, Hh), 0)
    edge = Image.new("L", (W, Hh), 0)
    df, de = ImageDraw.Draw(fill), ImageDraw.Draw(edge)
    for q in quads:
        pts = [((p[0] - RX0) * RES, (RY1 - p[1]) * RES) for p in q]
        df.polygon(pts, fill=255)
        de.polygon(pts, outline=255)
    mask = np.array(fill) > 0
    lines = np.array(edge) > 0
    inner = mask & ~(~_dilate(~mask, 1))
    rim = (_dilate(mask, 1) & ~mask) | (mask & _dilate(~mask, 1))
    return {"mask": mask, "lines": lines & mask & ~inner, "rim": rim}


def place_fossils(mask, seed):
    rng = np.random.default_rng(seed)
    free = ~_dilate(mask, 7)
    picks = []
    plan = [("ammonite", 6.5), ("fern", 16), ("ammonite", 5.0), ("track", 5.5), ("fern", 12), ("ammonite", 4.0), ("track", 5.0),
            ("ammonite", 3.5)]
    hh, ww = mask.shape
    for kind, r in plan:
        for _ in range(400):
            cx = rng.uniform(PANEL[0] + r + 2, PANEL[1] - r - 2)
            cy = rng.uniform(PANEL[2] + r + 2, PANEL[3] - r - 2)
            ok = True
            for a in np.linspace(0, 2 * math.pi, 10):
                for rr in (0.0, r * 0.6, r):
                    x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
                    ix, iy = int((x - RX0) * RES), int((RY1 - y) * RES)
                    if not (0 <= ix < ww and 0 <= iy < hh) or not free[iy, ix]:
                        ok = False
            if ok and all(math.hypot(cx - p[1], cy - p[2]) > r + p[3] + 5 for p in picks):
                picks.append((kind, cx, cy, r, rng.uniform(0, 2 * math.pi) if kind != "track" else rng.uniform(1.2, 1.9)))
                break
    return picks


def _fps(pts, n, start=None):
    """Farthest point sampling of an (N, 2) array."""
    if len(pts) == 0:
        return np.zeros((0, 2))
    c = pts.mean(axis=0)
    i0 = int(np.argmax(np.hypot(*(pts - c).T))) if start is None else start
    chosen = [i0]
    d = np.hypot(*(pts - pts[i0]).T)
    for _ in range(min(n, len(pts)) - 1):
        i = int(np.argmax(d))
        chosen.append(i)
        d = np.minimum(d, np.hypot(*(pts - pts[i]).T))
    return pts[chosen]


def outline_points(H):
    """Rim and interior samples in imprint-decal block coordinates [bx, bz] (bb space, z forward = -)."""
    mask = H["mask"]
    rimpix = np.argwhere(mask & _dilate(~mask, 1))
    fillpix = np.argwhere(mask & ~_dilate(~mask, 3))

    def conv(p):
        X = RX0 + (p[:, 1] + 0.5) / RES
        Y = RY1 - (p[:, 0] + 0.5) / RES
        return np.stack([X / 16 * IMPRINT_SCALE, -(Y - 72) / 16 * IMPRINT_SCALE], axis=1)
    rim = _fps(conv(rimpix.astype(float)), 16)
    fill = _fps(conv(fillpix.astype(float)), 18)
    return [[round(float(a), 2), round(float(b), 2)] for a, b in rim], [[round(float(a), 2), round(float(b), 2)] for a, b in fill]


# ================================================================ tablets
def tablet_model(sp):
    r = relief(sp)
    m = Model(f"ed5_tablet_{sp}", density=1.0, bounds=(26, 26, (0, 4.5, 0)), alts=("awake", "blaze"))
    H = {}
    strata, panel = strata_mat(sp), panel_mat(sp, H)
    fr_h, fr_v = frame_mat(sp, False), frame_mat(sp, True)
    root = m.bone("root")
    crack = m.bone("crack", root)
    crack.plane("y", (0, 0.35, -2), 300, 112, crack_mat(sp), density=0.35, faces=("up",))
    tilt = m.bone("tilt", root, pivot=(0, 72, 0))
    slab = m.bone("slab", tilt, pivot=(0, 72, 0))
    rng = np.random.default_rng(len(sp) * 31 + 7)
    for k, (x0, x1, y0, y1) in enumerate(FRAGS):
        fb = m.bone(f"frag{k + 1}", slab, pivot=((x0 + x1) / 2, (y0 + y1) / 2, 0))
        fb.cube((x0, y0, -10), (x1 - x0, y1 - y0, 22), strata, mats={"north": panel})
        for band, (bx0, bx1, by0, by1) in BANDS.items():
            ix0, ix1, iy0, iy1 = max(x0, bx0), min(x1, bx1), max(y0, by0), min(y1, by1)
            if ix1 - ix0 > 0.5 and iy1 - iy0 > 0.5:
                fb.cube((ix0, iy0, -13), (ix1 - ix0, iy1 - iy0, 3), strata,
                        mats={"north": fr_v if band in ("left", "right") else fr_h})
        # rough-hewn outer edges
        if y1 == 144:
            for j in range(2):
                w = rng.uniform(12, 26)
                cx = rng.uniform(x0 + w / 2 + 2, x1 - w / 2 - 2)
                h = rng.uniform(3, 9)
                fb.cube((cx - w / 2, 144, -9 + rng.uniform(0, 4)), (w, h, rng.uniform(10, 16)), strata, variant=j)
        if y0 == 0:
            w = rng.uniform(16, 30)
            cx = rng.uniform(x0 + w / 2 + 2, x1 - w / 2 - 2)
            fb.cube((cx - w / 2, -rng.uniform(3, 6), -8), (w, 6, rng.uniform(14, 18)), strata)
        for xe, sgn in ((-96, -1), (96, 1)):
            if (sgn < 0 and x0 == xe) or (sgn > 0 and x1 == xe):
                hgt = rng.uniform(10, min(24, y1 - y0 - 4))
                cy = rng.uniform(y0 + hgt / 2 + 1, y1 - hgt / 2 - 1)
                dep = rng.uniform(2.5, 5)
                fb.cube((xe if sgn > 0 else xe - dep, cy - hgt / 2, -8 + rng.uniform(0, 5)), (dep, hgt, rng.uniform(10, 15)), strata)
        if x0 <= 0 < x1 and y0 <= 8 < y1:     # museum label plaque
            lbl = tex.stamped(bronze(True), glyphs.line(DR, [EMBLEM[sp], 3, 7, 1, 10, 6], gap=1), "#3a2a14", key=f"ed5lbl{sp}")
            lbl = tex.alt(lbl, awake=tex.stamped(bronze(True), glyphs.line(DR, [EMBLEM[sp], 3, 7, 1, 10, 6], gap=1), GLOW2[sp],
                                                 glow=1.0, key=f"ed5lblA{sp}"))
            fb.cube((-21, 3.5, -14.2), (42, 10, 1.4), bronze(), mats={"north": lbl}, density=1.5)
        for ex in (-48, 48):
            if x0 <= ex - 8 and ex + 8 <= x1 and y0 <= 128 and y1 >= 144:
                rune = DR[EMBLEM[sp]] if ex < 0 else DR[(EMBLEM[sp] + 6) % len(DR)]
                em = tex.alt(tex.bitmap_cut(rune, "#5a4630"), awake=tex.bitmap_cut(rune, GLOW2[sp], glow=1.0, color2=GLOW[sp]),
                             blaze=tex.bitmap_cut(rune, "#ffffff", glow=1.0, color2=GLOW2[sp]))
                fb.box((ex, 135.5, -13.5), (15, 15, 1.0), bronze(), variant=1)
                fb.plane("z", (ex, 135.5, -14.1), 9, 12.6, em, density=1.0)
    # bronze museum clamps
    cl = m.bone("clamps", tilt, pivot=(0, 72, 0))
    bz, bz2 = bronze(), bronze(True)
    for sx in (1, -1):
        for y in (36, 108):
            cl.box((sx * 98.5, y, 0), (4, 15, 30), bz)
            cl.box((sx * 91.5, y, -14.0), (14, 10, 2.4), bz)
            cl.box((sx * 91.5, y, 13.2), (14, 10, 2.4), bz, variant=1)
            cl.box((sx * 89.5, y, -15.6), (3, 3, 1.0), bz2)
    # the bas-relief: the species' skeleton in its death pose, squashed into the slab
    rs = m.bone("relief_show", tilt, pivot=KC)
    m.bone("relief_flat", rs, pivot=KC, rot=REL_ROT[sp])
    s, C = r["s"], r["C"]
    Sk(sp, m, Mats(sp, relief=True), prefix="r_", parent="relief_flat", s=s, t=np.array(KC) - s * C, pose=DEATH[sp], detail=0,
       locators=False)
    names = [n for n in m.order if n.startswith("r_")]
    quads = posed_quads(m, names, pose={"relief_flat": ((0, 0, 0), (0, 0, 0), flat_vec(sp))})
    H.update(raster([q for q in quads]))
    H["fossils"] = place_fossils(H["mask"], 1000 + len(sp) * 17 + ord(sp[0]))
    return m, H


def tablet_anims():
    fr = [f"frag{k + 1}" for k in range(len(FRAGS))]
    A = []

    def a_(name, length=None, loop="hold", crack=False):
        a = Anim(name, length=length, loop=loop)
        if not crack:
            a.scl("crack", 0.0)
        A.append(a)
        return a
    h = a_("hidden", loop=True)
    h.scl("root", 0.0)
    fl = Anim("flat", loop=True)
    A.append(fl)                                   # filled per species (flatten axis) in build()
    L = LEN["rise"]
    rise = a_("rise", L, crack=True)
    rise.pos("tilt", {0: (0, -150, 0), 0.3: (0, -128, 0), 1.5: (0, -10, 0), 1.85: (0, 5, 0), 2.05: (0, -1.2, 0), L: (0, 0, 0)})
    rise.rot("tilt", {0: (9, 0, 5), 1.5: (-3, 0, -1.5), 1.9: (1, 0, 0.6), L: (0, 0, 0)})
    rise.scl("crack", {0: 0.0, 0.25: (1.12, 1, 1.12), 0.5: 1.0, L: 1.0})
    for k, f in enumerate(fr):
        rise.pos(f, {0: (0, 0, 0), 1.6 + 0.02 * k: (0, 0, 0), 1.72 + 0.02 * k: (0, -1.5 + (k % 3), 0), L: (0, 0, 0)})
    stand = a_("stand", loop=True, crack=True)
    stand.rot("tilt", (LIFE(0.25, 3.1), 0, LIFE(0.2, 4.3)))
    mem = a_("memorial", LEN["memorial"], crack=True)
    mem.scl("crack", {0: 1.0, 0.45: (0.4, 1, 0.1), LEN["memorial"]: 0.0})
    aw = a_("awaken", LEN["awaken"])
    aw.scl("relief_show", {0: 1.0, 0.3: 1.07, 0.7: 0.98, LEN["awaken"]: 1.0})
    for k, f in enumerate(fr):
        aw.pos(f, {0: (0, 0, 0), 0.1: (0.6 * ((k % 2) * 2 - 1), 0.4, 0), 0.25: (-0.4 * ((k % 2) * 2 - 1), 0, 0), 0.45: (0, 0, 0)})
    em = a_("empty", LEN["empty"])
    em.scl("relief_show", {0: 1.0, 0.12: 1.06, 0.5: 0.0, LEN["empty"]: 0.0})
    em.pos("relief_show", {0: (0, 0, 0), 0.4: (0, 0, -6), LEN["empty"]: (0, 0, -6)})
    rc = a_("receive", LEN["receive"])
    rc.scl("relief_show", {0: 0.0, 0.28: 1.2, 0.6: 0.96, LEN["receive"]: 1.0})
    for k, f in enumerate(fr):
        rc.pos(f, {0: (0, 0, 0), 0.28: (0, 0, 2.5 + (k % 3)), 0.6: (0, 0, -0.5), LEN["receive"]: (0, 0, 0)})
    L = LEN["formation"]
    fm = a_("formation", L)
    fm.rot("tilt", {0: (0, 0, 0), 0.4: (6, 0, 0), 1.4: (-TILT - 7, 0, 0), L: (-TILT, 0, 0)})
    fm.scl("clamps", {0: 1.0, 0.2: 1.08, 0.8: 0.0, L: 0.0})
    fm.rot("clamps", {0: (0, 0, 0), 0.8: (0, 0, 40), L: (0, 0, 40)})
    aim = a_("aim", loop=True)
    aim.rot("tilt", (LIFE(1.2, 3.3, 0, -TILT), 0, LIFE(0.8, 4.1)))
    aim.scl("clamps", 0.0)
    for name, per, amp, pulse in (("project", 1.0, 1.6, 0.06), ("project_all", 0.5, 2.4, 0.1)):
        pj = a_(name, per, loop=True)
        pj.rot("tilt", (S(amp, per, 0, -TILT), 0, S(amp * 0.4, per, 0.25)))
        pj.scl("relief_show", (S(pulse, per, 0, 1.0), S(pulse, per, 0, 1.0), S(pulse * 2.0, per, 0, 1.0)))
        pj.pos("slab", (S(0.5, per / 4), S(0.4, per / 3, 0.2), 0))
        pj.scl("clamps", 0.0)
    L = LEN["fracture"]
    fc = a_("fracture", L)
    fc.rot("tilt", (-TILT, 0, 0))
    fc.scl("clamps", 0.0)
    fc.scl("relief_show", {0: 1.0, 0.1: 1.22, 0.4: 0.0, L: 0.0})
    rng = np.random.default_rng(55)
    for k, (x0, x1, y0, y1) in enumerate(FRAGS):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 - 72
        dl = math.hypot(cx, cy) + 1e-6
        dx, dy = cx / dl, cy / dl
        out = (dx * 70, dy * 70 - 20, -30 - rng.uniform(0, 30))
        fc.pos(fr[k], {0: (0, 0, 0), 0.12: (dx * 2, dy * 2, -1), 0.25: (dx * 6, dy * 6, -4), L: out})
        fc.rot(fr[k], {0: (0, 0, 0), 0.12: (0, 0, rng.uniform(-4, 4)), L: tuple(rng.uniform(-90, 90, 3))})
        fc.scl(fr[k], {0: 1.0, 0.25: 1.0, 1.1: 0.7, L: 0.0})
    return A


# ================================================================ memorial
def memorial_model():
    m = Model("ed5_memorial", density=1.0, bounds=(22, 22, (0, 2, 0)))
    bz, bz2 = bronze(), bronze(True)
    stone = tex.stone("#9c8a6a", "#6b5d48", "#bfae8a", scale=4, cracks=0.2, strata=0.6)
    band = tex.glyph_rows(DR, "#ffe2a0", glow=1.0, color2="#e0a050", bg="#6a5028", fill=0.85, key="ed5memband")
    root = m.bone("root")
    for k, (x, z) in enumerate(((54, -54), (54, 54), (-54, 54), (-54, -54))):
        p = m.bone(f"post{k + 1}", root, pivot=(x, 36, z))
        p.box((x, 36, z), (8, 84, 8), bz, variant=k % 2)
        p.box((x, 79.5, z), (11, 4, 11), bz2)
        p.box((x, -6, z), (10, 5, 10), bz2, variant=1)
        p.box((x, 36, z), (9.6, 3, 9.6), bz2, variant=1)
        p.box((x, -12, z), (4, 8, 4), bz, rot=(0, 45, 0))
    bm = m.bone("beams", root, pivot=(0, 80, 0))
    for sz in (54, -54):
        bm.box((0, 80, sz), (100, 5, 5), bz, mats={"north": band, "south": band})
        bm.box((sz, 80, 0), (5, 5, 100), bz, mats={"east": band, "west": band})
    cr = m.bone("crown", root, pivot=(0, 80, 0))
    cr.box((0, 84, 0), (72, 4, 72), stone)
    cr.box((0, 89, 0), (52, 6, 52), stone, variant=1)
    cr.box((0, 95, 0), (32, 6, 32), stone, variant=2)
    cr.box((0, 104.5, 0), (5, 14, 5), bz, rot=(0, 45, 0))
    cr.box((0, 113.5, 0), (6, 6, 6), tex.glow_flat("#ffe2a0", 1.0, core="#ffffff"), rot=(45, 45, 0))
    gm = m.bone("gems", cr, pivot=(0, 89, 0))
    for sp, (x, z) in zip(("nature", "heat", "air", "tide"), ((0, -27), (27, 0), (0, 27), (-27, 0))):   # memorial slots 0..3
        gm.box((x, 89, z), (6.5, 6.5, 6.5), tex.glow_flat(GLOW[sp], 1.0, core=GLOW2[sp]), rot=(45, 0, 45))
    pd = m.bone("pendant", root, pivot=(0, -6, 0))
    pd.box((0, -8, 0), (72, 4, 72), stone, variant=1)
    pd.box((0, -13, 0), (48, 6, 48), stone, variant=2)
    pd.box((0, -20, 0), (28, 8, 28), stone)
    pd.box((0, -32, 0), (6, 16, 6), bz, rot=(0, 45, 0))
    pd.box((0, -42, 0), (3.5, 4.5, 3.5), tex.glow_flat("#ffe2a0", 1.0, core="#ffffff"), rot=(0, 45, 0))
    rn = m.bone("runes", root, pivot=(0, -26, 0))
    for i in range(8):
        g = tex.bitmap_cut(DR[(i * 5 + 1) % len(DR)], "#fff0c8", glow=1.0, color2="#e0a050")
        rn.box((0, -24, -40), (6, 8.4, 0), g, rot=(0, i * 45, 0), pivot=(0, -24, 0), faces=("north", "south"))
    return m


def memorial_anims():
    A = []
    sp_ = Anim("spin", loop=True)
    sp_.rot("runes", (0, spin(36), 0))
    sp_.scl("gems", LIFE(0.08, 1.7, 0, 1.0))
    A.append(sp_)
    h = Anim("hidden", loop=True)
    h.scl("root", 0.0)
    A.append(h)
    L = 3.0
    a = Anim("assemble", length=L, loop="hold")
    for k, (x, z) in enumerate(((54, -54), (54, 54), (-54, 54), (-54, -54))):
        t0 = 0.3 + 0.18 * k
        a.pos(f"post{k + 1}", {0: (x * 1.2, -50, z * 1.2), t0: (x * 1.2, -50, z * 1.2), t0 + 1.2: (0, 3, 0), t0 + 1.45: (0, 0, 0)})
        a.scl(f"post{k + 1}", {0: 0.0, t0: 0.0, t0 + 0.3: 0.9, t0 + 1.2: 1.0})
    a.scl("beams", {0: 0.0, 1.6: 0.0, 2.05: 1.06, 2.3: 1.0, L: 1.0})
    a.pos("crown", {0: (0, 90, 0), 1.9: (0, 90, 0), 2.55: (0, -3, 0), 2.8: (0, 0, 0), L: (0, 0, 0)})
    a.scl("crown", {0: 0.0, 1.85: 0.0, 1.95: 1.0, L: 1.0})
    a.pos("pendant", {0: (0, -80, 0), 2.0: (0, -80, 0), 2.7: (0, 2, 0), L: (0, 0, 0)})
    a.scl("pendant", {0: 0.0, 1.95: 0.0, 2.05: 1.0, L: 1.0})
    a.scl("runes", {0: 0.0, 2.4: 0.0, 2.85: 1.15, L: 1.0})
    A.append(a)
    hold = Anim("hold", loop=True)
    hold.pos("pendant", (0, LIFE(1.2, 3.6), 0))
    hold.pos("crown", (0, LIFE(0.6, 3.6, 0.5), 0))
    A.append(hold)
    L = 1.6
    d = Anim("dissolve", length=L, loop="hold")
    for k, (x, z) in enumerate(((54, -54), (54, 54), (-54, 54), (-54, -54))):
        d.pos(f"post{k + 1}", {0: (0, 0, 0), 0.2: (0, 2, 0), L: (x * 0.5, -60, z * 0.5)})
        d.rot(f"post{k + 1}", {0: (0, 0, 0), L: (x * 0.5, 0, -z * 0.5)})
        d.scl(f"post{k + 1}", {0: 1.0, 0.8: 0.8, L: 0.0})
    d.scl("beams", {0: 1.0, 0.15: 1.08, 0.5: 0.0, L: 0.0})
    d.pos("crown", {0: (0, 0, 0), L: (0, 50, 0)})
    d.scl("crown", {0: 1.0, 0.9: 0.7, L: 0.0})
    d.pos("pendant", {0: (0, 0, 0), L: (0, -60, 0)})
    d.scl("pendant", {0: 1.0, 1.0: 0.6, L: 0.0})
    d.scl("runes", {0: 1.0, 0.4: 1.5, 1.0: 0.0, L: 0.0})
    A.append(d)
    return A


# ================================================================ inscriptions
def inscription_model(sp):
    m = Model(f"ed5_inscription_{sp}", density=2.0, bounds=(8, 30, (0, 8, 0)))
    root = m.bone("root")
    for k, (r, n) in enumerate(((22, 10), (16, 8), (10, 6))):
        rb = m.bone(f"ring{k + 1}", root)
        for i in range(n):
            g = tex.bitmap_cut(DR[(i * 5 + k * 3) % len(DR)], GLOW2[sp], glow=1.0, color2="#e0b060")
            rb.box((0, 5, -r), (5, 7, 0), g, rot=(0, i * 360 / n, 0), pivot=(0, 5, 0), faces=("north", "south"))
    gr = m.bone("ground", root)
    gr.plane("y", (0, 0.3, 0), 60, 60, tex.magic_circle(DR, GLOW2[sp], GLOW[sp], bands=((0.72, 0.92, 14),), lines=(0.68, 0.96),
                                                        star=4, star_r=(0.2, 0.62)), faces=("up",))
    return m


def inscription_anims():
    sp_ = Anim("spin", loop=True)
    for k, r in enumerate((40, -60, 90)):
        sp_.rot(f"ring{k + 1}", (0, spin(r), 0))
    sp_.rot("ground", (0, spin(-20), 0))
    h = Anim("hidden", loop=True)
    h.scl("root", 0.0)
    L = 2.2
    d = Anim("descend", length=L, loop="hold")
    for k in range(3):
        t0 = 0.1 + 0.15 * k
        d.pos(f"ring{k + 1}", {0: (0, 200 + 40 * k, 0), t0: (0, 200 + 40 * k, 0), 1.45 + 0.1 * k: (0, 6, 0), 1.75 + 0.1 * k: (0, -16, 0),
                               L: (0, -16, 0)}, smooth=False)
        d.scl(f"ring{k + 1}", {0: 0.6, t0: 0.6, 1.0: 1.0, 1.5 + 0.1 * k: 1.0, 1.8 + 0.1 * k: 0.0, L: 0.0})
    d.scl("ground", {0: 0.0, 1.3: 0.0, 1.6: 1.18, 1.8: 1.0, L: 0.0})
    return [sp_, h, d]


# ================================================================ imprint
def imprint_mats(sp, H):
    g, g2 = tex.rgb(GLOW[sp]), tex.rgb(GLOW2[sp])

    def look(ctx):
        X, Yp = ctx.X, 72.0 - ctx.Z
        mask = H["mask"]
        hh, ww = mask.shape
        ix = np.clip(((X - RX0) * RES).astype(int), 0, ww - 1)
        iy = np.clip(((RY1 - Yp) * RES).astype(int), 0, hh - 1)
        return mask[iy, ix], H["rim"][iy, ix], H["lines"][iy, ix], ix, iy

    def rim_fn(ctx):
        m, rm, ln, ix, iy = look(ctx)
        t = tex.tile(ctx, "#000000", 0.0, 1.0)
        on = rm | (m & ln)
        t[..., :3] = np.where(rm[..., None], g2, g)
        t[..., 3] = on.astype(float)
        t[..., 4] = np.where(rm, 1.0, 0.85)
        return t

    def fill_fn(ctx):
        m, rm, ln, ix, iy = look(ctx)
        t = tex.tile(ctx, "#000000", 0.0, 0.6)
        dith = ((ix + iy) % 2) == 0
        t[..., :3] = tex.mix(g, g2, 0.25)
        t[..., 3] = (m & dith).astype(float)
        return t
    return Mat(rim_fn, f"ed5imprim{sp}", spatial=True, directional=True), Mat(fill_fn, f"ed5impfill{sp}", spatial=True,
                                                                               directional=True)


def imprint_model(sp, H):
    m = Model(f"ed5_imprint_{sp}", density=1.0, bounds=(22, 4, (0, 0, 0)))
    rim_m, fill_m = imprint_mats(sp, H)
    root = m.bone("root")
    rb = m.bone("rim", root)
    rb.plane("y", (0, 0.45, 0), 192, 144, rim_m, faces=("up",))
    fb = m.bone("fill", root)
    fb.plane("y", (0, 0.3, 0), 192, 144, fill_m, faces=("up",), density=0.5)
    return m


def imprint_anims():
    h = Anim("hidden", loop=True)
    h.scl("root", 0.0)
    w = Anim("warn", length=1.2, loop="hold")
    w.scl("rim", {0: 0.0, 0.25: 1.08, 0.4: 1.0})
    w.scl("fill", {0: 0.04, 1.2: 1.0}, smooth=False)
    b = Anim("brand", length=0.5, loop="hold")
    b.scl("root", {0: 1.0, 0.1: 1.16, 0.5: 1.0})
    hold = Anim("pulse", loop=True)
    hold.scl("fill", LIFE(0.05, 0.45, 0, 1.0))
    f = Anim("fade", length=0.6, loop="hold")
    f.scl("root", {0: 1.0, 0.15: 1.1, 0.6: 0.0})
    return [h, w, b, hold, f]


# ================================================================ spike (nature)
def spike_model():
    m = Model("ed5_spike", density=1.5, bounds=(6, 8, (0, 2, 0)))
    st = tex.stone("#8c7a5c", "#5d4f3c", "#b8a27e", scale=3, cracks=0.3, strata=0.9)
    st2 = tex.stone("#6b625a", "#45403a", "#8a8076", scale=3, cracks=0.3, strata=0.9)
    bone = bone_tex()
    root_m = tex.wood("#4a3420", "#2a1c10")
    moss = tex.foliage("#3a5a22", "#8fd055", holes=0.25, glow=0.25)
    root = m.bone("root")
    sb = m.bone("spike", root)
    sb.box((0, 17, 0), (11, 36, 10), st, rot=(6, 18, 4))
    sb.box((1.2, 41, 0.5), (7, 18, 6.5), st2, rot=(-4, 40, 8))
    sb.box((2.0, 52.5, 1.0), (3.4, 9, 3.4), st, rot=(10, 20, 14))
    sb.box((-0.5, 26, -5.6), (2.6, 24, 2.6), bone, rot=(0, 0, 26))
    sb.box((-5.6, 36.6, -5.6), (3.8, 3.6, 3.8), bone)
    for k in range(3):
        a = k * 120 + 20
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        sb.box((ca * 6.5, 6, sa * 6.5), (2.2, 14, 2.2), root_m, rot=(sa * 30, 0, -ca * 30), variant=k)
    sb.box((0, 2.5, 0), (14, 4, 13), moss)
    cr = m.bone("crack", root)
    cr.plane("y", (0, 0.3, 0), 40, 40, tex.shaped(lambda u, v: ((np.abs(np.sin(np.arctan2(v, u) * 3.5 + np.hypot(u, v) * 3)) < 0.22) &
                                                                (np.hypot(u, v) < 0.95)).astype(float), "#d8ffb0", "#8fe85a",
                                                    glow=0.95, key="ed5spikecrack"), faces=("up",))
    return m


def spike_anims():
    h = Anim("hidden", loop=True)
    h.scl("root", 0.0)
    r = Anim("rise", length=0.6, loop="hold")
    r.pos("spike", {0: (0, -66, 0), 0.22: (0, 5, 0), 0.36: (0, -1.5, 0), 0.6: (0, 0, 0)})
    r.rot("spike", {0: (9, 0, -7), 0.3: (-3, 0, 2), 0.6: (0, 0, 0)})
    r.scl("crack", {0: 0.0, 0.15: 1.25, 0.6: 1.0})
    hold = Anim("hold", loop=True)
    s = Anim("sink", length=0.7, loop="hold")
    s.pos("spike", {0: (0, 0, 0), 0.15: (0, 3, 0), 0.7: (0, -72, 0)})
    s.scl("crack", {0: 1.0, 0.7: 0.0})
    return [h, r, hold, s]


# ================================================================ trail (heat): fossil trackway + heat haze
TRACK = ["#   #   #", "#   #   #", " #  #  # ", " #  #  # ", "  # # #  ", "  #####  ", "   ###   ", "   ###   ", "    #    "]
TRAIL_SEGS = 12


def haze_mat():
    def fn(ctx):
        t = tex.tile(ctx, "#ff8a3a", 0.0, 0.0)
        ix, iy = tex.px(ctx)
        n = tex.fbm(ix / 3.0, iy / 2.0, 701)
        rip = 0.5 + 0.5 * np.sin(ix * 0.7 + iy * 0.3 + n * 5)
        a = (ctx.V ** 1.5) * (0.25 + 0.3 * rip) * np.sin(np.pi * ctx.U) ** 0.6
        t[..., :3] = tex.mix(tex.rgb("#fff0c0"), tex.rgb("#ff6a1a"), ctx.V[..., None])
        t[..., 3] = np.clip(a, 0, 1)
        return t
    return Mat(fn, "ed5haze", mode="blend")


def trail_model():
    m = Model("ed5_trail", density=1.0, bounds=(30, 6, (0, 0, -12)))
    pr = tex.bitmap_cut(TRACK, "#ffe2a0", glow=1.0, color2="#ff6a1a", key="ed5track")
    hz = haze_mat()
    scorch = tex.shaped(lambda u, v: (np.abs(u) < 0.85 - 0.15 * np.sin(v * 9)).astype(float), "#3a1a0a", "#ff6a1a", glow=0.55,
                        key="ed5scorch")
    root = m.bone("root")
    for k in range(TRAIL_SEGS):
        z = -32 * k - 16
        sb = m.bone(f"seg{k + 1:02d}", root, pivot=(0, 0, z))
        sx = 6 if k % 2 == 0 else -6
        sb.plane("y", (sx, 0.45, z + 4), 12, 14, pr, faces=("up",), density=1.5)
        sb.plane("y", (0, 0.3, z), 14, 32, scorch, faces=("up",), density=0.5)
        hb = m.bone(f"seg{k + 1:02d}h", root, pivot=(0, 0, z))
        hb.plane("x", (0, 12, z), 32, 24, hz, density=0.5)
    return m


def trail_anims():
    h = Anim("hidden", loop=True)
    h.scl("root", 0.0)
    w = Anim("warn", length=0.8, loop=True)
    for k in range(TRAIL_SEGS):
        w.scl(f"seg{k + 1:02d}", S(0.12, 0.8, -k * 0.06, 1.0))
        w.scl(f"seg{k + 1:02d}h", 0.0)
    b = Anim("burn", length=1.2, loop=True)
    for k in range(TRAIL_SEGS):
        b.scl(f"seg{k + 1:02d}h", (1.0, S(0.25, 1.2, -k * 0.09, 1.0), 1.0))
        b.rot(f"seg{k + 1:02d}h", (0, S(6, 1.2, k * 0.13), 0))
    f = Anim("fade", length=0.8, loop="hold")
    f.scl("root", {0: 1.0, 0.8: (1.0, 0.0, 1.0)})
    for k in range(TRAIL_SEGS):
        f.scl(f"seg{k + 1:02d}", {0: 1.0, 0.1 + k * 0.04: 1.0, 0.4 + k * 0.03: 0.0})
    return [h, w, b, f]


# ================================================================ icefan (tide)
FAN_ROWS = [(14, 5, 18), (30, 7, 28), (46, 9, 36)]


def icefan_model():
    m = Model("ed5_icefan", density=1.5, bounds=(12, 8, (0, 1, -3)))
    cry = tex.crystal("#eafbff", "#6fbfe8", "#ffffff", a=0.78, mode="blend")
    cry2 = tex.crystal("#d6f4ff", "#3f8fcf", "#ffffff", a=0.7, mode="blend", facets=3.0)
    root = m.bone("root")
    names = []
    for ri, (r, n, h0) in enumerate(FAN_ROWS):
        for j in range(n):
            a = -50 + 100 * j / (n - 1)
            prof = math.cos(math.radians(a) * 1.1) ** 2
            h = h0 * (0.45 + 0.55 * prof)
            ra = math.radians(a)
            p = (-math.sin(ra) * r, 0, -math.cos(ra) * r)
            nm = f"c{ri}_{j}"
            b = m.bone(nm, root, pivot=p, rot=(-24, a, 0))
            b.box((p[0], h / 2, p[2]), (4.6, h, 4.6), cry, rot=(0, 45, 0), pivot=(p[0], 0, p[2]), variant=j % 3)
            b.box((p[0] + 2.4, h * 0.3, p[2] + 1), (2.6, h * 0.5, 2.6), cry2, rot=(0, 20, 25), pivot=(p[0], 0, p[2]))
            names.append((nm, ri, abs(a)))
    fr = m.bone("frost", root)
    fr.plane("y", (0, 0.3, -26), 110, 60, tex.shaped(lambda u, v: ((np.abs(np.sin(np.arctan2(u, v + 1.2) * 18)) < 0.3) &
                                                                  (np.hypot(u, (v + 1) * 0.6) < 1.0) & (v > -0.95)).astype(float),
                                                       "#ffffff", "#9fdcff", glow=0.9, key="ed5frostfan"), faces=("up",), density=0.5)
    return m, names


def icefan_anims(names):
    h = Anim("hidden", loop=True)
    h.scl("root", 0.0)
    bu = Anim("burst", length=0.7, loop="hold")
    for nm, ri, aa in names:
        t0 = 0.06 * ri + aa * 0.0016
        bu.scl(nm, {0: 0.0, t0: 0.0, t0 + 0.12: 1.22, t0 + 0.26: 1.0, 0.7: 1.0})
    bu.scl("frost", {0: 0.0, 0.25: 1.05, 0.7: 1.0})
    hold = Anim("hold", loop=True)
    sh = Anim("shatter", length=0.5, loop="hold")
    for nm, ri, aa in names:
        sh.scl(nm, {0: 1.0, 0.1: 1.18, 0.5: 0.0})
        sh.pos(nm, {0: (0, 0, 0), 0.5: (0, 6 + ri * 3, 0)})
    sh.scl("frost", {0: 1.0, 0.5: 0.0})
    return [h, bu, hold, sh]


# ================================================================ gust (air)
def streak_mat():
    def fn(ctx):
        t = tex.tile(ctx, "#ffffff", 0.0, 0.0)
        band = np.exp(-((ctx.V - 0.5) / 0.24) ** 2)
        streak = 0.55 + 0.45 * np.sin(ctx.U * 19 + ctx.V * 3)
        t[..., :3] = tex.mix(tex.rgb("#bcd6ff"), tex.rgb("#ffffff"), band[..., None])
        t[..., 3] = np.clip(band * streak * np.sin(np.pi * ctx.U) ** 0.8 * 0.8, 0, 1)
        return t
    return Mat(fn, "ed5streak", mode="blend")


def gust_model():
    m = Model("ed5_gust", density=1.0, bounds=(14, 6, (0, 1, 0)))
    st = streak_mat()
    vane = Mats("air").vane
    root = m.bone("root")
    rg = m.bone("ring", root, pivot=(0, 6, 0))
    ring(rg, (0, 6, 0), 24, 12, (14, 0, 6), st, axis="y", tilt=12)
    rg2 = m.bone("ring2", root, pivot=(0, 3, 0))
    ring(rg2, (0, 3, 0), 16, 10, (11, 0, 4), st, axis="y", tilt=-18)
    fb = m.bone("feathers", root, pivot=(0, 5, 0))
    for i in range(8):
        a = i * 45 + 10
        fb.box((0, 5, -14), (4, 0, 12), vane, rot=(0, a, 0), pivot=(0, 5, 0), faces=("up", "down"), variant=i % 3)
    return m


def gust_anims():
    h = Anim("hidden", loop=True)
    h.scl("root", 0.0)
    b = Anim("burst", length=0.8, loop="hold")
    b.scl("ring", {0: (0.2, 1.0, 0.2), 0.65: (2.5, 0.5, 2.5), 0.8: (2.8, 0.0, 2.8)})
    b.rot("ring", {0: (0, 0, 0), 0.8: (0, 140, 0)})
    b.scl("ring2", {0: (0.1, 1.0, 0.1), 0.1: (0.1, 1.0, 0.1), 0.7: (2.0, 0.6, 2.0), 0.8: (2.2, 0.0, 2.2)})
    b.rot("ring2", {0: (0, 0, 0), 0.8: (0, -200, 0)})
    b.scl("feathers", {0: 0.3, 0.6: 2.2, 0.8: 0.0})
    b.rot("feathers", {0: (0, 0, 0), 0.8: (0, 90, 0)})
    b.pos("root", {0: (0, 0, 0), 0.8: (0, 6, 0)})
    return [h, b]


# ================================================================ TS mirror
def write_ts(outlines):
    def ids(lst):
        return {n: i for i, n in enumerate(lst)}
    living = {
        "nature": dict(walkSpeed=ed_nature.WALK_SPEED, turnRate=ed_nature.TURN_RATE, attackA=ed_nature.LEN["attack_a"],
                       hitA=ed_nature.HIT["attack_a"], attackB=ed_nature.LEN["attack_b"], hitB=ed_nature.HIT["attack_b"],
                       power=ed_nature.LEN["power"]),
        "heat": dict(runSpeed=round(ed_heat.RUN_SPEED, 3), walkSpeed=round(ed_heat.WALK_SPEED, 3), turnRate=ed_heat.TURN_RATE,
                     turn=ed_heat.TURN_T, skid=ed_heat.SKID_LEN, roar=ed_heat.ROAR_LEN, attackA=ed_heat.ATTACK_A_LEN,
                     hitA=ed_heat.ATTACK_A_HIT, attackB=ed_heat.ATTACK_B_LEN, hitB=ed_heat.ATTACK_B_HIT),
        "tide": dict(walkSpeed=ed_tide.WALK_SPEED, attackA=ed_tide.LENGTHS["attack_a"], hitsA=list(ed_tide.HITS["attack_a"]),
                     attackB=ed_tide.LENGTHS["attack_b"], hitB=ed_tide.HITS["attack_b"][0], attackC=ed_tide.LENGTHS["attack_c"],
                     hitC=ed_tide.HITS["attack_c"][0], roar=ed_tide.LENGTHS["roar"], turn=ed_tide.LENGTHS["turn_l"]),
        "air": dict(flyDy=ed_air.FLY_DY, flap=0.8, attackA=0.7, hitA=0.3, roll=1.0, flare=0.5),
    }
    skel = {sp: dict(actor=f"ed5_skel_{sp}", scale=LIVING[sp].SCALE, states=ids(SKEL_STATES[sp]), emerge=EMERGE_LEN[sp],
                     ret=RETURN_LEN[sp], yawOff=YAW_OFF[sp], living=living[sp]) for sp in SPECIES}
    data = {
        "ED5_SKEL": skel,
        "ED5_TABLET": dict(actors={sp: f"ed5_tablet_{sp}" for sp in SPECIES}, states=ids(TABLET_STATES),
                           len={k: v for k, v in LEN.items()}, tilt=TILT,
                           relief=[KC[0] / 16, KC[1] / 16, KC[2] / 16], width=12, height=9, front=10 / 16, back=12 / 16),
        "ED5_IMPRINT": dict(actors={sp: f"ed5_imprint_{sp}" for sp in SPECIES}, scale=IMPRINT_SCALE,
                            states=ids(["hidden", "warn", "brand", "pulse", "fade"]), outline=outlines),
        "ED5_PROPS": dict(
            memorial=dict(actor="ed5_memorial", scale=2.0, states=ids(["hidden", "assemble", "hold", "dissolve"]), assemble=3.0,
                          dissolve=1.6, half=54 / 16 * 2.0),
            inscription=dict(actors={sp: f"ed5_inscription_{sp}" for sp in SPECIES}, states=ids(["hidden", "descend"]), descend=2.2),
            spike=dict(actor="ed5_spike", states=ids(["hidden", "rise", "hold", "sink"]), rise=0.6, sink=0.7),
            trail=dict(actor="ed5_trail", states=ids(["hidden", "warn", "burn", "fade"]), segment=2.0, fade=0.8),
            icefan=dict(actor="ed5_icefan", states=ids(["hidden", "burst", "hold", "shatter"]), burst=0.7, shatter=0.5,
                        reach=FAN_ROWS[-1][0] / 16, halfAngle=50),
            gust=dict(actor="ed5_gust", states=ids(["hidden", "burst"]), burst=0.8),
        ),
    }
    lines = ["// GENERATED by tools/assets/ed5_monument.py (python3 tools/build.py --only ed5_bones,ed5_fx,ed5_monument,ed5_skeletons).",
             "// Mirrors the ED05 asset state tables, animation timings and fossil outlines.  Do not edit by hand.", ""]
    for k, v in data.items():
        lines.append(f"export const {k} = {json.dumps(v, separators=(', ', ': '))} as const;")
        lines.append("")
    p = os.path.join(ROOT, "src", "spells", "_ed05_assets.ts")
    with open(p, "w") as fh:
        fh.write("\n".join(lines))


# ================================================================ build
def build(pack):
    ta = tablet_anims()
    by_t = {a.name: a for a in ta}
    outlines = {}
    tstates = {i: [n] for i, n in enumerate(TABLET_STATES)}
    tstates = {k: {"animations": v, "blend": 0.0 if v[0] in ("hidden", "empty", "receive") else 0.25} for k, v in tstates.items()}
    for sp in SPECIES:
        m, H = tablet_model(sp)
        fl = by_t["flat"]
        fl.tracks.clear()
        fl.scl("relief_flat", flat_vec(sp))
        import copy
        anims = [copy.deepcopy(a) for a in ta]
        pack.actor(f"ed5_tablet_{sp}", m, anims, tstates, always=["flat"], lifetime=60, display=f"Fossil Tablet ({sp.title()})",
                   blend=0.25)
        rim, fill = outline_points(H)
        outlines[sp] = {"rim": rim, "fill": fill}
        im = imprint_model(sp, H)
        pack.actor(f"ed5_imprint_{sp}", im, imprint_anims(), {0: ["hidden"], 1: ["warn"], 2: ["brand"], 3: ["pulse"], 4: ["fade"]},
                   scale=IMPRINT_SCALE, size_prop=True, lifetime=60, display="Fossil Imprint", blend=0.0)
        ins = inscription_model(sp)
        pack.actor(f"ed5_inscription_{sp}", ins, inscription_anims(), {0: ["hidden"], 1: ["descend"]}, always=["spin"],
                   size_prop=True, lifetime=60, display="Draconic Inscription", blend=0.0)
        print(f"    ed5_tablet_{sp}: {m.cube_count()} cubes, {len(m.order)} bones, tex {m.tex_size}; fossils {len(H['fossils'])}")
        anm = {a.name: a for a in anims}
        pose_f = (anm["flat"], 0.0)
        pack.preview(f"ed5_tablet_{sp}", m, [[pose_f], [(anm["formation"], 2.0), pose_f], [(anm["fracture"], 0.7), pose_f]],
                     views=((0, 4), (-35, 18), (0, -55)), cell=(440, 360), skin="awake")
        if sp == "nature":
            pack.preview("ed5_tablet_nature_dormant", m, [[pose_f], [(anm["empty"], 0.6), pose_f]], views=((0, 2), (60, 10)), cell=(560, 440))
            pack.preview("ed5_tablet_nature_blaze", m, [[pose_f]], views=((0, 2),), cell=(560, 440), skin="blaze")
            pack.preview("ed5_imprint_nature", im, [None], views=((0, 89),), cell=(500, 400))
    mm = memorial_model()
    ma = memorial_anims()
    pack.actor("ed5_memorial", mm, ma, {0: ["hidden"], 1: ["assemble"], 2: ["hold"], 3: ["dissolve"]}, always=["spin"], scale=2.0,
               lifetime=60, display="Suspended Memorial", blend=0.2)
    sm = spike_model()
    pack.actor("ed5_spike", sm, spike_anims(), {0: ["hidden"], 1: ["rise"], 2: ["hold"], 3: ["sink"]}, size_prop=True,
               lifetime=60, display="Fossil Spike", blend=0.0)
    tm = trail_model()
    vis = [{f"seg{k + 1:02d}*": f"q.property('grimoire:len') > {2 * k + 0.5}"} for k in range(TRAIL_SEGS)]
    pack.actor("ed5_trail", tm, trail_anims(), {0: ["hidden"], 1: ["warn"], 2: ["burn"], 3: ["fade"]}, lifetime=60,
               display="Burning Trackway", blend=0.0, visibility=vis,
               props={"len": {"type": "float", "range": [0.0, 64.0], "default": 16.0, "client_sync": True}})
    fm, names = icefan_model()
    pack.actor("ed5_icefan", fm, icefan_anims(names), {0: ["hidden"], 1: ["burst"], 2: ["hold"], 3: ["shatter"]}, size_prop=True,
               lifetime=60, display="Crystal Fan", blend=0.0)
    gm = gust_model()
    pack.actor("ed5_gust", gm, gust_anims(), {0: ["hidden"], 1: ["burst"]}, size_prop=True, lifetime=60, display="Wind Shockwave",
               blend=0.0)
    write_ts(outlines)
    print(f"    memorial {mm.cube_count()} / spike {sm.cube_count()} / trail {tm.cube_count()} / icefan {fm.cube_count()} / "
          f"gust {gm.cube_count()} cubes")
    ma_ = {a.name: a for a in ma}
    pack.preview("ed5_props", mm, [(ma_["hold"], 0.0), (ma_["assemble"], 1.6)], views=((30, 20),), cell=(400, 400))
    pack.preview("ed5_spike", sm, [None], views=((30, 15),), cell=(260, 300))
    fa = {a.name: a for a in icefan_anims(names)}
    pack.preview("ed5_icefan", fm, [(fa["burst"], 0.7)], views=((160, 25),), cell=(360, 300))
    pack.preview("ed5_gust", gm, [(gust_anims()[1], 0.35)], views=((20, 30),), cell=(300, 300))
    pack.preview("ed5_trail", tm, [None], views=((60, 45),), cell=(400, 300))
