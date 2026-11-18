"""
Nomos, The Unmapped Sovereign - geometry and textures.

Silhouette: a surveying instrument that learned to walk. A long boxwood
"ruler" spine carried high on four divider-legs (the hinged legs of drafting
compasses, knees above the body, steel points on the floor). Where a head
would be, an armillary of four nested compass rings turns on a gimbal. Folded
map sheets hang in pleats along both flanks; two ruling-pen arms reach down in
front and scribe the ground; a plumb line trails behind. Brass instruments are
bolted into the back: a telescope turret, a protractor plate, a spirit level.

Phase II stands the creature up, opens the four map sheets into a flat canopy
and sends the four compass rings out over the four sheets, one per quadrant.

Geo units: 16 = 1 block. Front is -Z. +X is the creature's LEFT.
"""
from __future__ import annotations

import math

import numpy as np

from kit import paint as P
from kit.geo import Model

IDENT = "geometry.abm.nomos"

PARCH = ["#8a7350", "#b89f73", "#d8c69b", "#ece0bd"]
BOXWOOD = ["#7a5a2c", "#a8843e", "#c9a65a", "#e0c684"]
BRASS = ["#4a3a18", "#7c6426", "#a98a34", "#d3b659"]
VERDIGRIS = "#3f8a78"
GRAPHITE = ["#16181c", "#26292f", "#3a3e46", "#565b66"]
INK = "#11131f"
EMERALD = "#2fae74"

SIDES = (("l", 1), ("r", -1))
QUADS = (("fl", 1, -1), ("fr", -1, -1), ("bl", 1, 1), ("br", -1, 1))     # tag, x sign, z sign
FOLD = (68.0, -136.0, 136.0)      # bind rotation of the three panels of a sheet: a hanging concertina


def _parchment(mapped: bool = True, seed: int = 5):
    """Aged vellum. With `mapped`, ink contour lines, a survey grid and a few emerald route marks."""
    def painter(ctx: P.FaceCtx) -> np.ndarray:
        n = P.fbm(ctx, 0.09, seed, 3)
        t = np.clip(0.62 + (n - 0.5) * 0.9 + (P.white(ctx) - 0.5) * 0.07, 0, 1)
        img = P.ramp(t, PARCH)
        stain = np.clip((P.fbm(ctx, 0.05, seed + 40, 2) - 0.62) * 5, 0, 1)
        img = P.shade(img, -0.22 * stain)
        if mapped and min(ctx.w, ctx.h) >= 6:
            h = P.fbm(ctx, 0.07, seed + 9, 3)
            contour = (np.abs(np.mod(h * 7.0, 1.0) - 0.5) < 0.07).astype(np.float32)
            img = P.over(img, P.rgba(INK, 0.55), contour)
            gx = (np.mod(np.round(ctx.P[..., 0]), 8) == 0) | (np.mod(np.round(ctx.P[..., 2]), 8) == 0)
            img = P.over(img, P.rgba("#4a4032", 0.45), gx.astype(np.float32))
            sea = (h < 0.36).astype(np.float32) * ((ctx.X + ctx.Y) % 3 == 0)
            img = P.over(img, P.rgba("#5d6e7a", 0.5), sea)
            route = (np.abs(P.fbm(ctx, 0.11, seed + 77, 2) - 0.5) < 0.012) & ((ctx.X + ctx.Y) % 4 < 2)
            img = P.over(img, P.rgba(EMERALD, 0.95), route.astype(np.float32))
        edge = (ctx.edge_dist() == 0).astype(np.float32)
        img = P.shade(img, -0.28 * edge)
        return P.face_light(ctx, img, 0.04, -0.2)
    return painter


def _ruler(ctx: P.FaceCtx) -> np.ndarray:
    """Boxwood rule: engraved graduations along the long axis, darker every eighth."""
    n = P.fbm(ctx, 0.18, 21, 2)
    grain = P.noise3(ctx.P * np.array([0.25, 1.2, 0.08], dtype=np.float32), 1.0, 23)
    t = np.clip(0.55 + (n - 0.5) * 0.5 + (grain - 0.5) * 0.3, 0, 1)
    img = P.ramp(t, BOXWOOD)
    long_u = ctx.w >= ctx.h
    along = ctx.X if long_u else ctx.Y
    across = ctx.Y if long_u else ctx.X
    span = ctx.h if long_u else ctx.w
    if span >= 2:
        tick = (along % 2 == 0) & (across < max(1, span // 3))
        major = (along % 8 == 0) & (across < max(2, (span * 2) // 3))
        img = P.over(img, P.rgba(INK, 0.9), (tick | major).astype(np.float32))
    return P.face_light(ctx, P.bevel(ctx, img, 0.14, 0.24))


def _brass(patina: float = 0.55, rivet: bool = False):
    def painter(ctx: P.FaceCtx) -> np.ndarray:
        n = P.fbm(ctx, 0.2, 31, 3)
        sheen = np.clip(1 - np.abs(ctx.V - 0.3) * 2.6, 0, 1) * 0.3
        img = P.ramp(np.clip(0.42 + (n - 0.5) * 0.7 + sheen, 0, 1), BRASS)
        green = np.clip((P.fbm(ctx, 0.16, 37, 3) - patina) * 6, 0, 1)
        img = P.over(img, P.rgba(VERDIGRIS, 0.85), green)
        img = P.over(img, P.rgba("#74c7b0", 0.8), ((green > 0.6) & (P.white(ctx, 3) < 0.25)).astype(np.float32))
        if rivet:
            img = P.over(img, P.rgba(BRASS[3]), P.rivets(ctx, 4, 1))
        return P.face_light(ctx, P.bevel(ctx, img, 0.2, 0.28))
    return painter


def _graphite(ctx: P.FaceCtx) -> np.ndarray:
    n = P.fbm(ctx, 0.25, 41, 2)
    streak = (np.mod(ctx.X + ctx.Y * 2, 7) == 0).astype(np.float32) * 0.18
    img = P.ramp(np.clip(0.38 + (n - 0.5) * 0.6 + streak, 0, 1), GRAPHITE)
    return P.face_light(ctx, P.bevel(ctx, img, 0.22, 0.3), 0.06, -0.22)


def _steel(ctx: P.FaceCtx) -> np.ndarray:
    n = P.fbm(ctx, 0.3, 47, 2)
    img = P.ramp(np.clip(0.5 + (n - 0.5) * 0.5, 0, 1), ["#3b4048", "#6a717d", "#9aa2ae", "#c9cfd8"])
    return P.face_light(ctx, P.bevel(ctx, img, 0.25, 0.3))


def _ink(ctx: P.FaceCtx) -> np.ndarray:
    n = P.fbm(ctx, 0.3, 53, 2)
    img = P.ramp(np.clip(0.3 + (n - 0.5) * 0.8, 0, 1), ["#07080f", INK, "#1d2238", "#33406a"])
    return P.over(img, P.rgba("#6f86c9", 0.8), (P.white(ctx, 2) < 0.05).astype(np.float32))


def _glass(ctx: P.FaceCtx) -> np.ndarray:
    img = P.mix("#9fe0c2", "#e8fff4", np.clip(1 - np.abs(ctx.V - 0.3) * 3, 0, 1))
    img[..., 3] = 0.42
    return img


def _dial(ctx: P.FaceCtx, img: np.ndarray) -> np.ndarray:
    """Engraved degree marks for the protractor plate."""
    if ctx.face not in ("north", "south"):
        return img
    out = img.copy()
    marks = ((ctx.X % 2 == 0) & (ctx.Y < 1)) | ((ctx.X % 4 == 0) & (ctx.Y < 2))
    return P.over(out, P.rgba(INK, 0.9), marks.astype(np.float32))


def _mx(side: int, origin, size):
    if side > 0:
        return origin, size
    return (-(origin[0] + size[0]), origin[1], origin[2]), size


def _mr(side: int, rot):
    return rot if side > 0 else (rot[0], -rot[1], -rot[2])


def _mp(side: int, p):
    return (p[0] * side, p[1], p[2])


def _ring(bone, centre, radius: float, thick: float, mat, depth: float = None, uv_key=None):
    """Octagonal ring in the XY plane around `centre` (eight bars)."""
    cx, cy, cz = centre
    depth = thick if depth is None else depth
    length = 2 * radius * math.tan(math.radians(22.5)) + thick * 0.45
    for k in range(8):
        bone.box((cx - length / 2, cy + radius - thick / 2, cz - depth / 2), (length, thick, depth), mat,
                 pivot=(cx, cy, cz), rotation=(0, 0, k * 45), uv_key=(uv_key, k % 2) if uv_key else None)


HEAD = (0.0, 86.0, -46.0)
RING_R = (17.0, 13.4, 9.8, 6.2)


def _board(ctx: P.FaceCtx) -> np.ndarray:
    """The plane-table: a boxwood drawing board, scored with a survey grid and old pin holes."""
    n = P.fbm(ctx, 0.12, 61, 2)
    grain = P.noise3(ctx.P * np.array([0.9, 1.0, 0.07], dtype=np.float32), 1.0, 63)
    img = P.ramp(np.clip(0.48 + (n - 0.5) * 0.4 + (grain - 0.5) * 0.36, 0, 1), BOXWOOD)
    if ctx.face in ("up", "down"):
        grid = (np.mod(np.round(ctx.P[..., 0]), 6) == 0) | (np.mod(np.round(ctx.P[..., 2]), 6) == 0)
        img = P.over(img, P.rgba(INK, 0.5), grid.astype(np.float32))
        img = P.over(img, P.rgba("#3a2a12", 0.8), (P.white(ctx, 8) < 0.02).astype(np.float32))
    return P.face_light(ctx, P.bevel(ctx, img, 0.14, 0.26))


def build() -> Model:
    m = Model(IDENT, density=1.0, bounds=(11.0, 10.0, 4.0))
    m.materials.update({
        "parchment": _parchment(True, 5), "parchment_b": _parchment(True, 19), "vellum": _parchment(False, 7),
        "ruler": _ruler, "board": _board, "brass": _brass(0.56), "brass_riv": _brass(0.6, True),
        "brass_old": _brass(0.42), "graphite": _graphite, "steel": _steel, "ink": _ink, "glass": _glass,
        "emerald": P.glow("#d8ffe9", "#1f9a62", 0.12), "lamp": P.glow("#fff6d0", "#c9a23a", 0.2),
    })

    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 64, 0), "root")

    # ------------------------------------------------------------------ the plane table: a drawing board on legs
    table = m.bone("table", (0, 64, 0), "body")
    table.box((-12, 63, -23), (24, 2, 46), "board")
    table.box((-9, 65, -20), (18, 0.4, 40), "parchment")                          # the chart pinned to it
    for x in (-12.6, 9.6):
        for z in (-23.6, 20.6):
            table.box((x, 62.6, z), (3, 2.8, 3), "brass_riv", uv_key="corner")
    table.box((-5, 56.5, -18), (10, 6.5, 36), "graphite")                         # works housing under the board
    table.box((-6, 58, -8), (12, 2, 3), "brass_old")
    table.box((-6, 58, 6), (12, 2, 3), "brass_old")
    case = m.bone("map_case", (0, 53, 0), "table")
    case.box((-3, 50, -15), (6, 6, 30), "vellum")                                 # slung chart rolls
    case.box((-3.5, 49.5, -16.5), (7, 7, 2), "brass_old")
    case.box((-3.5, 49.5, 14.5), (7, 7, 2), "brass_old")

    # ------------------------------------------------------------------ the ruler spine (five hinged links) along its top
    parent = "body"
    for i in range(5):
        z0 = -30 + i * 12
        sp = m.bone(f"spine_{i + 1}", (0, 66, z0), parent)
        sp.box((-3, 65.4, z0), (6, 2.8, 12), "ruler")
        sp.box((-3.6, 65, z0 + 10.6), (7.2, 3.6, 1.4), "brass_riv")                # hinge strap
        sp.box((-0.8, 68.2, z0 + 10.8), (1.6, 1.2, 1), "steel")                   # hinge pin
        parent = sp.name

    # ------------------------------------------------------------------ instruments bolted along the spine
    prot = m.bone("protractor", (0, 68, -12), "spine_2")
    for w, y in ((20, 68), (16, 71), (10, 74)):
        prot.box((-w / 2, y, -12.6), (w, 3, 1.2), "brass", decal={"*": _dial})
    prot.box((-10, 68, -13.2), (20, 1, 2.4), "brass_riv")
    pg = m.bone("protractor_glow", (0, 68, -12), "protractor")
    pg.box((-0.6, 69, -13.4), (1.2, 9, 0.6), "emerald")

    sb = m.bone("scope_base", (0, 68, 0), "spine_3")
    sb.box((-3.5, 68, -3.5), (7, 2, 7), "brass_riv")
    sb.box((-4.5, 70, -1), (1.5, 7, 2), "brass")
    sb.box((3, 70, -1), (1.5, 7, 2), "brass")
    sc = m.bone("scope", (0, 75, 0), "scope_base", (-14, 0, 0))
    sc.box((-2, 73, -11), (4, 4, 18), "graphite")
    sc.box((-2.6, 72.4, -12.5), (5.2, 5.2, 2.5), "brass")
    sc.box((-1.5, 73.5, 7), (3, 3, 4), "brass_old")
    sl = m.bone("scope_lens_glass", (0, 75, -12), "scope")
    sl.box((-1.8, 73.2, -12.9), (3.6, 3.6, 0.6), "glass")

    lv = m.bone("level", (0, 68, 12), "spine_4")
    lv.box((-5, 68, 9.5), (10, 1.2, 5), "brass_riv")
    lv.box((-5, 69.2, 9.5), (1.4, 2.4, 5), "brass")
    lv.box((3.6, 69.2, 9.5), (1.4, 2.4, 5), "brass")
    lg = m.bone("level_glass", (0, 70, 12), "level")
    lg.box((-3.6, 69.3, 10.6), (7.2, 2.2, 2.8), "glass")
    lb = m.bone("level_bubble_glow", (0, 70.4, 12), "level")
    lb.box((-1, 69.9, 11.3), (2, 1.2, 1.4), "emerald")

    # ------------------------------------------------------------------ tail boom and plumb line
    tail = m.bone("tail", (0, 66.8, 30), "spine_5")
    tail.box((-1.2, 65.6, 30), (2.4, 2.4, 20), "graphite", pivot=(0, 66.8, 30), rotation=(32, 0, 0))
    tail.box((-1.8, 76, 44.6), (3.6, 3.6, 3), "brass")
    line = m.bone("plumb_line", (0, 77.6, 46), "tail")
    line.box((-0.4, 34, 45.6), (0.8, 43, 0.8), "steel")
    bob = m.bone("plumb_bob", (0, 34, 46), "plumb_line")
    bob.box((-2, 28, 44), (4, 6, 4), "brass")
    bob.box((-1.2, 24.5, 44.8), (2.4, 3.5, 2.4), "brass_old")
    bob.box((-0.5, 21, 45.5), (1, 3.5, 1), "steel")
    bob.locator("plumb", (0, 21, 46))

    # ------------------------------------------------------------------ neck crane and the compass armillary
    neck = m.bone("neck", (0, 66, -28), "spine_1")
    neck.box((-2, 66, -30), (4, 27, 4), "brass_riv", pivot=(0, 66, -28), rotation=(40, 0, 0))
    neck.box((-3, 74, -31), (6, 2, 6), "graphite", pivot=(0, 66, -28), rotation=(40, 0, 0))
    neck.box((-2.6, 64.6, -30.6), (5.2, 3, 5.2), "brass_old")
    head = m.bone("head", HEAD, "neck")
    hx, hy, hz = HEAD
    head.box((hx - 1.5, hy - 1.5, hz - 1.5), (3, 3, 4), "graphite")               # axle back to the crane
    head.box((hx - 2.5, hy - 2.5, hz - 2.5), (5, 5, 5), "brass_riv")              # hub
    head.locator("compass", HEAD)
    head.locator("compass_front", (hx, hy, hz - 4))
    mats = ("brass", "graphite", "brass_old", "steel")
    for k, r in enumerate(RING_R):
        ring = m.bone(f"ind_{k + 1}", HEAD, "head")
        thick = (2.6, 2.2, 1.8, 1.5)[k]
        _ring(ring, (hx, hy, hz - 3.4 - k * 0.2), r, thick, mats[k], depth=thick + 0.6, uv_key=f"ring{k}")
        for a in (0, 90, 180, 270):                                              # cardinal bosses on the rim
            ring.box((hx - 1, hy + r - thick / 2 - 0.4, hz - 4.6 - k * 0.2), (2, thick + 0.8, thick + 2.4),
                     "brass_riv" if k % 2 else "graphite", pivot=(hx, hy, hz), rotation=(0, 0, a), uv_key=f"stud{k}")
        needle = m.bone(f"ind_{k + 1}_needle", HEAD, f"ind_{k + 1}")
        needle.box((hx - 0.7, hy - r + 1.2, hz - 3.8 - k * 0.2), (1.4, r - 2.2, 1.0), "graphite", uv_key=f"needle_s{k}")
        needle.box((hx - 0.7, hy + 1.0, hz - 3.8 - k * 0.2), (1.4, r - 3.4, 1.0), "steel", uv_key=f"needle_n{k}")
        tip = m.bone(f"ind_{k + 1}_tip_glow", HEAD, f"ind_{k + 1}_needle")
        tip.box((hx - 1.1, hy + r - 3.0, hz - 4.1 - k * 0.2), (2.2, 2.2, 1.6), "emerald", uv_key="tip")
        needle.locator(f"needle_{k + 1}", (hx, hy + r - 2, hz - 4))

    # ------------------------------------------------------------------ four pleated map sheets (one per quadrant)
    for tag, sx, sz in QUADS:
        z0 = -22 if sz < 0 else 1
        zc = z0 + 10.5
        chain = "table"
        fold = FOLD
        for i in range(3):
            x0 = 12 + i * 14
            bone = m.bone(f"map_{tag}_{i + 1}", _mp(sx, (x0, 64.5, zc)), chain, _mr(sx, (0, 0, fold[i])))
            o, s = _mx(sx, (x0, 64, z0), (14, 1, 21))
            bone.box(o, s, "parchment" if (i + (sx > 0) + (sz > 0)) % 2 else "parchment_b")
            o, s = _mx(sx, (x0 - 0.5, 63.7, z0 - 0.5), (1, 1.6, 22))
            bone.box(o, s, "brass_old", uv_key="map_hinge")                      # brass fold rail
            chain = bone.name
        m.get(f"map_{tag}_3").locator(f"sheet_{tag}", _mp(sx, (47, 65, zc)))

    # ------------------------------------------------------------------ four divider legs: hip yaw -> thigh -> long shank
    for tag, sx, sz in QUADS:
        hz_ = -25 if sz < 0 else 25
        yaw = 26 if sz < 0 else -26
        hip = m.bone(f"leg_{tag}", _mp(sx, (7, 62, hz_)), "body", _mr(sx, (0, yaw, 0)))
        o, s = _mx(sx, (4, 59.5, hz_ - 3), (6, 5, 6))
        hip.box(o, s, "brass_riv", uv_key="hip")
        up = m.bone(f"leg_{tag}_a", _mp(sx, (7, 62, hz_)), f"leg_{tag}", _mr(sx, (0, 0, -50)))
        o, s = _mx(sx, (7, 60, hz_ - 2), (30, 4, 4))
        up.box(o, s, "graphite", uv_key="thigh")
        o, s = _mx(sx, (12, 62.6, hz_ - 2.6), (14, 2, 5.2))
        up.box(o, s, "ruler", uv_key="thigh_rule")
        lo = m.bone(f"leg_{tag}_b", _mp(sx, (37, 62, hz_)), f"leg_{tag}_a", _mr(sx, (0, 0, 134)))
        o, s = _mx(sx, (34.5, 59.5, hz_ - 3.2), (5, 5, 6.4))
        lo.box(o, s, "brass", uv_key="knee")                                      # knee hinge
        o, s = _mx(sx, (36.2, 61.2, hz_ - 4.4), (1.6, 1.6, 8.8))
        lo.box(o, s, "steel", uv_key="knee_pin")
        o, s = _mx(sx, (39, 60.3, hz_ - 1.7), (32, 3.4, 3.4))
        lo.box(o, s, "ruler", uv_key="shank_a")
        o, s = _mx(sx, (71, 60.7, hz_ - 1.3), (32, 2.6, 2.6))
        lo.box(o, s, "graphite", uv_key="shank_b")
        o, s = _mx(sx, (68, 60, hz_ - 2), (4, 4, 4))
        lo.box(o, s, "brass_old", uv_key="shank_collar")
        o, s = _mx(sx, (103, 61.1, hz_ - 0.9), (16, 1.8, 1.8))
        lo.box(o, s, "steel", uv_key="shank_c")
        o, s = _mx(sx, (119, 61.5, hz_ - 0.5), (3.5, 1, 1))
        lo.box(o, s, "ink", uv_key="point")
        lo.locator(f"foot_{tag}", _mp(sx, (122.5, 62, hz_)))

    # ------------------------------------------------------------------ two ruling-pen arms that scribe the floor
    for tag, sx in SIDES:
        a = m.bone(f"scribe_{tag}_a", _mp(sx, (5, 60, -28)), "spine_1", _mr(sx, (-48, 0, -7)))
        o, s = _mx(sx, (4.1, 34, -28.9), (1.8, 26, 1.8))
        a.box(o, s, "graphite", uv_key="scribe_a")
        o, s = _mx(sx, (3.4, 57.6, -29.6), (3.2, 3.2, 3.2))
        a.box(o, s, "brass", uv_key="scribe_j")
        b = m.bone(f"scribe_{tag}_b", _mp(sx, (5, 34, -28)), f"scribe_{tag}_a", _mr(sx, (58, 0, 0)))
        o, s = _mx(sx, (4.2, 8, -28.8), (1.6, 26, 1.6))
        b.box(o, s, "steel", uv_key="scribe_b")
        o, s = _mx(sx, (3.5, 32.5, -29.5), (3, 3, 3))
        b.box(o, s, "brass_old", uv_key="scribe_j2")
        c = m.bone(f"scribe_{tag}_c", _mp(sx, (5, 8, -28)), f"scribe_{tag}_b", _mr(sx, (-25, 0, 0)))
        o, s = _mx(sx, (3.8, 0, -29.2), (2.4, 8, 2.4))
        c.box(o, s, "brass", uv_key="pen_body")                                   # ink reservoir
        o, s = _mx(sx, (4.1, -8, -29.1), (0.5, 8, 2.2))
        c.box(o, s, "steel", uv_key="pen_blade")
        o, s = _mx(sx, (5.4, -8, -29.1), (0.5, 8, 2.2))
        c.box(o, s, "steel", uv_key="pen_blade")
        o, s = _mx(sx, (4.5, -9.6, -28.6), (1, 2.4, 1.2))
        c.box(o, s, "ink", uv_key="pen_ink")
        c.locator(f"nib_{tag}", _mp(sx, (5, -10, -28)))
    body.locator("core", (0, 66, 0))
    return m
