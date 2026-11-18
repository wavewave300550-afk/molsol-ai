"""
Orison, The Witness of Tomorrow - geometry and textures.

Silhouette: two needle-thin stilt legs with knees that fold the wrong way, an
open, lopsided clock-case torso with one shoulder built up into a tower, an
hourglass caged in the chest with a small coffin hanging beneath it, four
mismatched arms each ending in a different instrument (minute hand, hour hand,
winding key, gavel), and where a head should be an inverted pendulum - the rod
rises and the heavy bob swings above everything like a metronome. Three
segmented metal ribbons float behind it without touching.

The hourglass bulbs are on `*_glass` bones (alpha-blended material) and the
spectral lights on `*_glow` bones (emissive material); nothing here relies on
rendering features Bedrock entities do not have.

Geo units: 16 = 1 block. Front is -Z. +X is the creature's LEFT.
"""
from __future__ import annotations

import math

import numpy as np

from kit import paint as P
from kit.geo import Model

IDENT = "geometry.abm.orison"

SILVER = ["#3a3e47", "#6b717d", "#9ca2ae", "#cdd2d9"]
GOLD = ["#4a4229", "#7a6d42", "#a39462", "#cbbd8a"]
IRON = ["#16181d", "#262a32", "#383c47", "#4f5461"]
BLUE = ["#070a14", "#0e1426", "#17203a", "#243052"]
WOOD = ["#090b15", "#121626", "#1b2035", "#272d49"]
SAND = ["#857852", "#b0a16f", "#d2c593", "#ece3bd"]
PALE = "#dfe9ff"
SPECTRAL = "#8fa6d8"


def _silver(ctx: P.FaceCtx) -> np.ndarray:
    """Tarnished silver: bright metal eaten by dark sulphide blotches, hairline scratches."""
    t = P.fbm(ctx, 0.16, 11, 3)
    blot = P.noise3(ctx.P, 0.085, 29)
    t = np.clip(0.6 + (t - 0.5) * 0.6 - np.clip(blot - 0.52, 0, 1) * 1.9 + (P.white(ctx) - 0.5) * 0.07, 0, 1)
    img = P.ramp(t, SILVER)
    scratch = ((ctx.X * 2 + ctx.Y + (ctx.seed % 7)) % 9 == 0) & (P.white(ctx, 3) < 0.4)
    img = P.shade(img, scratch.astype(np.float32) * 0.22)
    img = P.bevel(ctx, img, 0.2, 0.26)
    return P.face_light(ctx, img)


def _gold(ctx: P.FaceCtx) -> np.ndarray:
    """Desaturated gilt: dull brass with engraved hatch lines and grey wear."""
    t = P.fbm(ctx, 0.2, 17, 2)
    t = np.clip(0.52 + (t - 0.5) * 0.7 - (ctx.V - 0.5) * 0.25, 0, 1)
    img = P.ramp(t, GOLD)
    if min(ctx.w, ctx.h) >= 4:
        img = P.shade(img, -0.18 * P.stripes(ctx, 3.0, 1.0, "v"))
    img = P.over(img, P.rgba(SILVER[1], 0.5), (P.white(ctx, 5) < 0.07).astype(np.float32))
    return P.face_light(ctx, P.bevel(ctx, img, 0.22, 0.28))


def _iron(ctx: P.FaceCtx) -> np.ndarray:
    t = P.fbm(ctx, 0.3, 23, 2)
    img = P.ramp(np.clip(0.42 + (t - 0.5) * 0.8 + (P.white(ctx) - 0.5) * 0.1, 0, 1), IRON)
    return P.face_light(ctx, P.bevel(ctx, img, 0.16, 0.24), 0.04, -0.2)


def _blue(ctx: P.FaceCtx) -> np.ndarray:
    """Near-black blue enamel with a cold sheen and a few pin-prick stars."""
    t = P.fbm(ctx, 0.12, 31, 2)
    sheen = np.clip(1 - np.abs(ctx.U - 0.35) * 3.0, 0, 1) * 0.3
    img = P.ramp(np.clip(0.3 + (t - 0.5) * 0.7 + sheen, 0, 1), BLUE)
    img = P.over(img, P.rgba(SPECTRAL, 0.85), (P.white(ctx, 8) < 0.018).astype(np.float32))
    return P.face_light(ctx, P.bevel(ctx, img, 0.2, 0.25))


def _wood(ctx: P.FaceCtx) -> np.ndarray:
    grain = P.noise3(ctx.P * np.array([1.6, 0.12, 1.6], dtype=np.float32), 0.6, 37)
    img = P.ramp(np.clip(0.35 + (grain - 0.5) * 0.9, 0, 1), WOOD)
    return P.face_light(ctx, P.outline(ctx, img, 0.3))


def _sand(ctx: P.FaceCtx) -> np.ndarray:
    t = np.clip(0.5 + (P.white(ctx) - 0.5) * 0.9 + (P.fbm(ctx, 0.5, 41, 2) - 0.5) * 0.4, 0, 1)
    return P.face_light(ctx, P.ramp(P.steps(t, 4), SAND), 0.08, -0.12)


def _glass(alpha: float = 0.26):
    """Blown glass for the alpha-blended layer: mostly clear, bright streak, firmer rim."""
    def painter(ctx: P.FaceCtx) -> np.ndarray:
        img = ctx.fill(P.rgba("#b9c9e6"))
        streak = np.clip(1 - np.abs((ctx.U * 1.3 - ctx.V * 0.6) - 0.22) * 6, 0, 1)
        a = alpha + 0.42 * streak + 0.26 * (ctx.edge_dist() == 0)
        img = P.over(img, P.rgba("#f4f8ff"), streak)
        img[..., 3] = np.clip(a, 0, 0.85)
        return img
    return painter


def _shards(ctx: P.FaceCtx) -> np.ndarray:
    """What is left after the hourglass breaks: jagged glass teeth with gaps (alpha-blended)."""
    img = _glass(0.34)(ctx)
    jag = (ctx.Y + ((ctx.X * 5 + ctx.seed) % 4)) < ctx.h * 0.45
    img[..., 3] = np.where(jag, 0.0, img[..., 3])
    return img


def _clock_face(ctx: P.FaceCtx, img: np.ndarray) -> np.ndarray:
    """Engraved dial for the back plate: ring, twelve ticks, two hands frozen at a wrong hour."""
    if ctx.face != "south" or min(ctx.w, ctx.h) < 10:
        return img
    cx, cy = (ctx.w - 1) / 2, (ctx.h - 1) * 0.42
    dx, dy = ctx.X - cx, ctx.Y - cy
    r = np.sqrt(dx * dx + dy * dy)
    R = min(ctx.w, ctx.h) * 0.44
    out = P.over(img, P.rgba(IRON[0], 0.9), (np.abs(r - R) < 0.6).astype(np.float32))
    ang = (np.degrees(np.arctan2(dy, dx)) + 360) % 30
    ticks = (np.minimum(ang, 30 - ang) < 4.5) & (r > R - 2.2) & (r < R - 0.6)
    out = P.over(out, P.rgba(GOLD[2]), ticks.astype(np.float32))
    for a, ln, col in ((-70, R * 0.8, BLUE[0]), (165, R * 0.5, BLUE[0])):
        ux, uy = math.cos(math.radians(a)), math.sin(math.radians(a))
        along = dx * ux + dy * uy
        across = np.abs(-dx * uy + dy * ux)
        out = P.over(out, P.rgba(col), ((along > 0) & (along < ln) & (across < 0.6)).astype(np.float32))
    return out


def _bob_eye(ctx: P.FaceCtx, img: np.ndarray) -> np.ndarray:
    """The pendulum bob's face: concentric rings around a blind, vertical slit."""
    if ctx.face not in ("north", "south"):
        return img
    cx, cy = (ctx.w - 1) / 2, (ctx.h - 1) / 2
    r = np.sqrt((ctx.X - cx) ** 2 + (ctx.Y - cy) ** 2)
    out = img
    for rr, col in ((min(ctx.w, ctx.h) * 0.46, IRON[0]), (min(ctx.w, ctx.h) * 0.3, GOLD[0])):
        out = P.over(out, P.rgba(col, 0.9), (np.abs(r - rr) < 0.55).astype(np.float32))
    slit = (np.abs(ctx.X - cx) < 0.7) & (np.abs(ctx.Y - cy) < min(ctx.w, ctx.h) * 0.2)
    return P.over(out, P.rgba(BLUE[0]), slit.astype(np.float32))


def _coffin_inlay(ctx: P.FaceCtx, img: np.ndarray) -> np.ndarray:
    if ctx.face != "north":
        return img
    cx = (ctx.w - 1) / 2
    line = (np.abs(ctx.X - cx) < 0.6) | ((ctx.Y == 1) & (ctx.h >= 4))
    return P.over(img, P.rgba(SILVER[2], 0.9), line.astype(np.float32))


def _numerals(ctx: P.FaceCtx, img: np.ndarray) -> np.ndarray:
    """Ribbon segments carry engraved hour strokes: I, II, III ..."""
    if ctx.face not in ("north", "south") or ctx.w < 3 or ctx.h < 5:
        return img
    n = 1 + (ctx.seed % 3)
    cols = np.zeros((ctx.h, ctx.w), dtype=np.float32)
    start = (ctx.w - (2 * n - 1)) // 2
    for i in range(n):
        x = start + i * 2
        if 0 <= x < ctx.w:
            cols[1:ctx.h - 1, x] = 1
    return P.over(img, P.rgba(BLUE[0], 0.9), cols)


def _mats(m: Model) -> None:
    m.materials.update({
        "silver": _silver, "gold": _gold, "iron": _iron, "blue": _blue, "wood": _wood, "sand": _sand,
        "glass": _glass(), "shards": _shards,
        "spectral": P.glow(PALE, SPECTRAL, 0.1),
        "sandglow": P.glow("#fff6d8", SAND[2], 0.16),
    })


def _m(side: int, origin, size):
    if side > 0:
        return origin, size
    return (-(origin[0] + size[0]), origin[1], origin[2]), size


# Arms: shoulder position, segment lengths, and the bind rotation of each of the three bones.
# For the shoulder: rx < 0 swings the arm forward, rz lifts it sideways (negative = towards +X).
ARMS = {
    "ul": dict(at=(9.5, 109, 0), la=22, lb=26, lc=30, rot=((-6, 0, -126), (-16, 0, 0), (-24, 0, 0))),     # minute hand, flung high and wide
    "ur": dict(at=(-9.5, 95, 0), la=16, lb=20, lc=17, rot=((-20, 0, 82), (-74, 0, 0), (-34, 0, 0))),      # hour hand, levelled from the low shoulder
    "ll": dict(at=(8.5, 82, -2), la=12, lb=14, lc=10, rot=((-50, 22, 0), (-74, 0, 0), (30, 0, 0))),       # winding key, curled in to the hourglass
    "lr": dict(at=(-9.5, 78, -1), la=18, lb=22, lc=15, rot=((-8, 0, 38), (-96, 0, 0), (54, 0, 0))),       # gavel, cocked at the hip
}
# Legs: hip, segment lengths and absolute angles (thigh, shin, metatarsus) - the knee folds forward, the shin back.
LEGS = {
    "l": dict(at=(7, 62.6, 0), ln=(18, 38, 24), ang=(55, -40, 15), roll=-7),
    "r": dict(at=(-7, 62.6, 0), ln=(18, 38, 26), ang=(48, -46, 24), roll=9),
}


def _side(x: float) -> int:
    return 1 if x >= 0 else -1


def build() -> Model:
    m = Model(IDENT, density=1.0, bounds=(9.0, 10.5, 4.0))
    _mats(m)
    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 64, 0), "root")
    body.box((-6, 60, -3), (12, 6, 6), "iron")                                  # pelvis yoke
    body.box((-8.5, 61.5, -1.5), (17, 3, 3), "gold")

    # a plumb weight hangs under the pelvis and always swings a beat behind everything else
    plumb = m.bone("plumb", (0, 60, 0), "body")
    plumb.box((-0.4, 44, -0.4), (0.8, 16, 0.8), "silver")
    plumb.box((-1.6, 40, -1.6), (3.2, 4.4, 3.2), "gold")
    plumb.box((-0.8, 37, -0.8), (1.6, 3, 1.6), "blue")
    plumb.box((-0.3, 34.4, -0.3), (0.6, 2.6, 0.6), "silver")

    # ------------------------------------------------------------------ torso: an open, lopsided clock case
    torso = m.bone("torso", (0, 66, 0), "body", (8, 0, -5))
    torso.box((-1.5, 66, 2.5), (3, 38, 3), "blue")                              # spine column
    torso.box((-7, 69, 5.2), (14, 28, 1.2), "silver", decal={"south": _clock_face})     # back plate (engraved dial)
    torso.box((6, 68, -4), (2, 39, 2), "silver")                                # left posts - taller
    torso.box((6, 68, 3.2), (2, 39, 2), "silver")
    torso.box((-8, 68, -4), (2, 28, 2), "silver")                               # right posts - shorter
    torso.box((-8, 68, 3.2), (2, 28, 2), "silver")
    torso.box((-8.5, 66, -4.5), (17, 2.2, 10), "iron")                          # floor of the case
    torso.box((6, 83, -2), (2, 2, 5.2), "gold")
    torso.box((-8, 83, -2), (2, 2, 5.2), "gold")
    torso.box((-8.6, 100.2, -1), (17.2, 2, 2), "silver", pivot=(0, 101.2, 0), rotation=(0, 0, -34))   # slanted lintel
    torso.box((-8.6, 100.2, 3.2), (17.2, 2, 2), "silver", pivot=(0, 101.2, 4), rotation=(0, 0, -34))
    for y, w in ((74, 4.5), (80, 3), (95, 5.5), (101, 4)):                      # ribs on the left only
        torso.box((8 - w - 2, y, -5.2), (w, 1, 1), "gold")
    torso.box((-7.6, 70, -5), (1, 20, 1), "iron", pivot=(-7, 70, -4.5), rotation=(0, 0, 26))     # one long brace on the right
    torso.box((4.5, 104, -4), (7, 11, 8), "blue")                               # the shoulder tower (left)
    torso.box((3.9, 115, -4.6), (8.2, 1.6, 9.2), "silver")
    torso.box((5.2, 116.6, -3.2), (5.6, 2.4, 6.4), "blue")
    torso.box((7, 119, -1), (2, 8, 2), "silver")
    torso.box((7.5, 127, -0.5), (1, 3.4, 1), "gold")
    torso.box((4.2, 108, -4.3), (7.6, 4, 0.5), "gold")                          # a small dial on the tower
    torso.box((-11, 93, -2.2), (4, 4, 4.4), "gold")                             # the low right shoulder
    torso.box((-10.4, 97, -1.2), (1.4, 5, 1.4), "silver", pivot=(-9.7, 97, -0.5), rotation=(0, 0, 14))
    torso.box((-2.5, 101, 1.6), (5, 4.5, 4), "gold")                            # pendulum pivot housing
    torso.locator("chest", (0, 92, -7))
    torso.locator("top", (0, 105, 0))

    esc = m.bone("escapement", (0, 103, 1.2), "torso")
    esc.box((-3.5, 99.5, 0.6), (7, 7, 0.8), "silver")
    esc.box((-0.8, 98.3, 0.7), (1.6, 9.4, 0.6), "gold")
    esc.box((-4.7, 102.2, 0.7), (9.4, 1.6, 0.6), "gold")

    # ------------------------------------------------------------------ the hourglass in the chest
    hg = m.bone("hourglass", (0, 92.5, -1.5), "torso")
    hg.box((-4.5, 99.5, -6), (9, 1.5, 9), "gold")
    hg.box((-4.5, 84.5, -6), (9, 1.5, 9), "gold")
    for x in (-4.2, 3.4):
        for z in (-5.7, 1.9):
            hg.box((x, 86, z), (0.8, 13.5, 0.8), "silver")
    glass = m.bone("hourglass_glass", (0, 92.5, -1.5), "hourglass")
    glass.box((-3.5, 93.3, -5), (7, 6.2, 7), "glass")
    glass.box((-3.5, 86, -5), (7, 6.2, 7), "glass")
    glass.box((-1, 92, -2.5), (2, 1.5, 2), "glass")
    broken = m.bone("hourglass_broken_glass", (0, 92.5, -1.5), "hourglass")
    broken.box((-3.5, 86, -5), (7, 3.6, 7), "shards")
    broken.box((-3.5, 96.5, -5), (7, 3, 7), "shards", pivot=(0, 98, -1.5), rotation=(180, 0, 0))
    st = m.bone("sand_top", (0, 93.4, -1.5), "hourglass")
    st.box((-2.8, 93.5, -4.3), (5.6, 3.8, 5.6), "sand")
    sb = m.bone("sand_bottom", (0, 86.1, -1.5), "hourglass")
    sb.box((-2.8, 86.2, -4.3), (5.6, 2.8, 5.6), "sand")
    stream = m.bone("sand_glow", (0, 92.5, -1.5), "hourglass")
    stream.box((-0.3, 89, -1.8), (0.6, 4.6, 0.6), "sandglow")
    hg.locator("sand", (0, 88, -5.5))

    # ------------------------------------------------------------------ the coffin hanging under it
    coffin = m.bone("coffin", (0, 84.5, -1.2), "torso")
    for x in (-1.6, 1.0):
        coffin.box((x, 81.4, -1.5), (0.6, 3.2, 0.6), "iron")                     # chains
    coffin.box((-1.75, 78.6, -3), (3.5, 2.8, 3.6), "wood", decal={"north": _coffin_inlay})
    coffin.box((-2.75, 74.4, -3.1), (5.5, 4.2, 3.8), "wood", decal={"north": _coffin_inlay})
    coffin.box((-2.25, 70.8, -3), (4.5, 3.6, 3.6), "wood", decal={"north": _coffin_inlay})
    coffin.box((-1.6, 68.6, -2.9), (3.2, 2.2, 3.4), "wood", decal={"north": _coffin_inlay})
    cg = m.bone("coffin_glow", (0, 76, -3.2), "coffin")
    cg.box((-2.4, 76.2, -3.3), (4.8, 0.6, 0.3), "spectral")                      # a line of light where the lid does not quite close

    # ------------------------------------------------------------------ the inverted pendulum (no head: this)
    pen = m.bone("pendulum", (0, 103.2, 3.5), "torso")
    pen.box((-1, 103, 2.5), (2, 15, 2), "silver")
    pen.box((-2, 107, 2.2), (4, 1.4, 2.6), "gold")
    pen.box((-2, 112.5, 2.2), (4, 1.4, 2.6), "gold")
    pen.box((-7, 118.5, 1.6), (14, 9, 3.8), "gold", decal={"north": _bob_eye, "south": _bob_eye})    # the bob: a heavy disc
    pen.box((-4.5, 116, 1.7), (9, 14, 3.6), "gold")
    pen.box((-8, 121.2, 2.3), (16, 3.6, 2.4), "silver")
    pen.box((-1.2, 130, 2.4), (2.4, 2.2, 2.2), "silver")
    pen.locator("bob", (0, 123, 1))
    eye = m.bone("pendulum_glow", (0, 123, 1.6), "pendulum")
    eye.box((-0.7, 120, 1.42), (1.4, 6, 0.35), "spectral")

    # ------------------------------------------------------------------ four mismatched arms
    for tag, a in ARMS.items():
        x, y, z = a["at"]
        ra, rb, rc = a["rot"]
        ua = m.bone(f"arm_{tag}_a", (x, y, z), "torso", ra)
        ua.box((x - 1.5, y - 1.5, z - 1.5), (3, 3, 3), "gold", uv_key=f"sh_{tag}")
        ua.box((x - 1, y - a["la"], z - 1), (2, a["la"] - 1, 2), "iron", uv_key=f"ua_{tag}")
        fb = m.bone(f"arm_{tag}_b", (x, y - a["la"], z), f"arm_{tag}_a", rb)
        fb.box((x - 1.25, y - a["la"] - 1.25, z - 1.25), (2.5, 2.5, 2.5), "gold", uv_key=f"el_{tag}")
        fb.box((x - 0.8, y - a["la"] - a["lb"], z - 0.8), (1.6, a["lb"] - 1, 1.6), "silver", uv_key=f"fa_{tag}")
        wy = y - a["la"] - a["lb"]
        tc_b = m.bone(f"arm_{tag}_c", (x, wy, z), f"arm_{tag}_b", rc)
        tc_b.box((x - 1, wy - 1, z - 1), (2, 2, 2), "gold", uv_key=f"wr_{tag}")
        L = a["lc"]
        if tag == "ul":            # minute hand: long shaft, a lozenge near the end, a point
            tc_b.box((x - 0.6, wy - 16, z - 0.45), (1.2, 15, 0.9), "blue")
            tc_b.box((x - 1.8, wy - 23, z - 0.4), (3.6, 7, 0.8), "silver")
            tc_b.box((x - 0.5, wy - L, z - 0.35), (1, 7, 0.7), "silver")
        elif tag == "ur":          # hour hand: short shaft, broad spade
            tc_b.box((x - 0.6, wy - 8, z - 0.45), (1.2, 7, 0.9), "blue")
            tc_b.box((x - 2.2, wy - 14, z - 0.4), (4.4, 6, 0.8), "silver")
            tc_b.box((x - 0.6, wy - L, z - 0.35), (1.2, 3, 0.7), "silver")
        elif tag == "ll":          # winding key: shaft, bit, and a cross bow
            tc_b.box((x - 0.45, wy - 8, z - 0.45), (0.9, 7, 0.9), "silver")
            tc_b.box((x - 0.45, wy - L, z - 1.6), (0.9, 2.4, 3.2), "gold")
            tc_b.box((x - 1.8, wy - 2.6, z - 0.4), (3.6, 0.8, 0.8), "gold")
        else:                      # gavel
            tc_b.box((x - 0.6, wy - 10, z - 0.6), (1.2, 9, 1.2), "wood")
            tc_b.box((x - 3.4, wy - L, z - 2.2), (6.8, 5.2, 4.4), "iron")
            tc_b.box((x - 3.7, wy - L + 1.7, z - 2.4), (0.9, 1.8, 4.8), "gold")
            tc_b.box((x + 2.8, wy - L + 1.7, z - 2.4), (0.9, 1.8, 4.8), "gold")
        tc_b.locator({"ul": "minute", "ur": "hour", "ll": "key", "lr": "gavel"}[tag], (x, wy - L, z))

    # ------------------------------------------------------------------ two stilt legs with reversed knees
    for tag, g in LEGS.items():
        x, y, z = g["at"]
        l1, l2, l3 = g["ln"]
        a1, a2, a3 = g["ang"]
        hip = m.bone(f"leg_{tag}", (x, y, z), "body", (0, 0, g["roll"]))
        hip.box((x - 1.6, y - 1.6, z - 1.6), (3.2, 3.2, 3.2), "gold", uv_key="hip")
        th = m.bone(f"leg_{tag}_a", (x, y, z), f"leg_{tag}", (-a1, 0, 0))
        th.box((x - 1, y - l1, z - 1), (2, l1 - 1.2, 2), "iron", uv_key="thigh")
        sh = m.bone(f"leg_{tag}_b", (x, y - l1, z), f"leg_{tag}_a", (-(a2 - a1), 0, 0))
        sh.box((x - 1.4, y - l1 - 1.4, z - 1.4), (2.8, 2.8, 2.8), "gold", uv_key="knee")
        sh.box((x - 0.8, y - l1 - l2, z - 0.8), (1.6, l2 - 1, 1.6), "silver", uv_key="shin")
        sh.box((x - 1.1, y - l1 - 16, z + 0.6), (2.2, 9, 0.7), "blue", uv_key="greave")           # spur plate behind the shin
        sh.box((x - 0.4, y - l1 - 5, z - 4.4), (0.8, 0.8, 3.6), "silver", uv_key="spur")            # a spur at the knee
        mt = m.bone(f"leg_{tag}_c", (x, y - l1 - l2, z), f"leg_{tag}_b", (-(a3 - a2), 0, 0))
        mt.box((x - 1.1, y - l1 - l2 - 1.1, z - 1.1), (2.2, 2.2, 2.2), "gold", uv_key="ankle")
        mt.box((x - 0.7, y - l1 - l2 - l3, z - 0.7), (1.4, l3 - 0.8, 1.4), "blue", uv_key=f"meta_{tag}")
        fy = y - l1 - l2 - l3
        ft = m.bone(f"leg_{tag}_d", (x, fy, z), f"leg_{tag}_c", (a3, 0, 0))
        ft.box((x - 0.8, fy - 0.2, z - 6.5), (1.6, 1.1, 7.5), "silver", uv_key="toe")              # a clock-hand toe
        ft.box((x - 1.8, fy - 0.2, z - 3.2), (3.6, 1.1, 1.6), "silver", uv_key="toe_bar")
        ft.box((x - 0.5, fy - 0.2, z + 0.8), (1, 1.1, 3.4), "iron", uv_key="heel")
        ft.locator(f"foot_{tag}", (x, fy, z))

    # ------------------------------------------------------------------ three floating ribbons (never attached)
    for i, (x, y, z, n, lean, side) in enumerate(((15, 112, 9, 5, -14, -10), (-16, 98, 9, 5, 12, 12), (2, 86, 14, 4, 16, 0)), 1):
        parent = "body"
        py = y
        for k in range(n):
            name = f"ribbon_{i}_{'abcde'[k]}"
            b = m.bone(name, (x, py, z), parent, (lean if k == 0 else 4, 0, side if k == 0 else side * 0.4))
            mat = "silver" if (k + i) % 2 else "gold"
            b.box((x - 2.5, py - 7.4, z - 0.25), (5, 6.8, 0.5), mat, decal={"north": _numerals, "south": _numerals})
            parent = name
            py -= 8.2
    m.get("ribbon_1_a").locator("ribbon", (15, 108, 9))
    return m


# --------------------------------------------------------------------------- helper entities

def build_shadow() -> Model:
    """The shadow manifestation: not a dark Orison but a cut-out - a flat, stretched silhouette
    standing up out of a pool, with only a pale ring where the pendulum bob would be."""
    m = Model("geometry.abm.orison_shadow", density=1.0, bounds=(5.0, 7.0, 2.5))
    dark = lambda a: (lambda ctx: _shade_sheet(ctx, a))             # noqa: E731
    m.materials.update({"shade": dark(0.72), "shade_thin": dark(0.5), "pool": dark(0.6),
                        "ring": P.glow(PALE, SPECTRAL, 0.08), "slit": P.glow("#ffffff", PALE, 0.06)})
    m.bone("root", (0, 0, 0))
    pool = m.bone("pool_glass", (0, 0, 0), "root")
    pool.box((-13, 0.05, -8), (26, 0.2, 16), "pool")
    pool.box((-8, 0.1, -13), (16, 0.2, 26), "pool")
    pool.box((-5, 0.15, -17), (10, 0.2, 9), "pool")
    stem = m.bone("stem_glass", (0, 0, 0), "root")
    for (w, y0, h) in ((12, 0, 10), (7, 10, 14), (3.5, 24, 16), (8, 40, 12), (11, 52, 10), (6, 62, 9)):
        stem.box((-w / 2, y0, -0.3), (w, h, 0.6), "shade")
    stem.box((-0.5, 71, -0.3), (1, 12, 0.6), "shade_thin")
    stem.locator("shadow_core", (0, 48, 0))
    ring = m.bone("ring_glow", (0, 88, 0), "stem_glass")
    ring.box((-5, 83, -0.35), (10, 1.2, 0.7), "ring")
    ring.box((-5, 91.8, -0.35), (10, 1.2, 0.7), "ring")
    ring.box((-5, 84.2, -0.35), (1.2, 7.6, 0.7), "ring")
    ring.box((3.8, 84.2, -0.35), (1.2, 7.6, 0.7), "ring")
    ring.box((-0.4, 85.5, -0.4), (0.8, 5, 0.8), "slit")
    ring.locator("shadow_ring", (0, 88, 0))
    for side, tag in ((1, "l"), (-1, "r")):
        o, s = _m(side, (5, 34, -0.25), (1.6, 26, 0.5))
        a = m.bone(f"sarm_{tag}_glass", (5.8 * side, 60, 0), "stem_glass", (0, 0, -16 * side))
        a.box(o, s, "shade")
        o, s = _m(side, (5.2, 6, -0.2), (1.2, 28, 0.4))
        b = m.bone(f"sarm_{tag}_b_glass", (5.8 * side, 34, 0), f"sarm_{tag}_glass", (-24, 0, 0))
        b.box(o, s, "shade_thin")
        b.locator(f"shadow_hand_{tag}", (5.8 * side, 6, 0))
    return m


def _shade_sheet(ctx: P.FaceCtx, alpha: float) -> np.ndarray:
    """Translucent near-black with a ragged, dissolving lower edge."""
    t = P.fbm(ctx, 0.3, 53, 2)
    img = P.ramp(np.clip(0.2 + (t - 0.5) * 0.5, 0, 1), BLUE)
    a = alpha * (0.75 + 0.5 * t)
    if ctx.face in ("north", "south") and ctx.h >= 6:
        ragged = (ctx.Y > ctx.h - 3) & (P.white(ctx, 4) < 0.5)
        a = np.where(ragged, 0.0, a)
    img[..., 3] = np.clip(a, 0, 0.9)
    return img


def build_hourglass() -> Model:
    """A Drain hourglass: a tall standing glass in a tarnished frame, sand running while it lasts."""
    m = Model("geometry.abm.orison_hourglass", density=1.0, bounds=(3.0, 4.0, 1.5))
    _mats(m)
    m.bone("root", (0, 0, 0))
    fr = m.bone("frame", (0, 0, 0), "root")
    fr.box((-6, 0, -6), (12, 2, 12), "iron")
    fr.box((-5, 2, -5), (10, 1.5, 10), "gold")
    fr.box((-5, 32.5, -5), (10, 1.5, 10), "gold")
    fr.box((-6, 34, -6), (12, 2, 12), "iron")
    for x in (-4.8, 3.8):
        for z in (-4.8, 3.8):
            fr.box((x, 3.5, z), (1, 29, 1), "silver")
    gl = m.bone("bulb_glass", (0, 18, 0), "root")
    gl.box((-4, 19, -4), (8, 13.5, 8), "glass")
    gl.box((-4, 3.5, -4), (8, 13.5, 8), "glass")
    gl.box((-1.2, 17, -1.2), (2.4, 2, 2.4), "glass")
    top = m.bone("sand_top", (0, 19.2, 0), "root")
    top.box((-3.2, 19.3, -3.2), (6.4, 9, 6.4), "sand")
    bot = m.bone("sand_bottom", (0, 3.7, 0), "root")
    bot.box((-3.2, 3.8, -3.2), (6.4, 9, 6.4), "sand")
    st = m.bone("stream_glow", (0, 18, 0), "root")
    st.box((-0.35, 5, -0.35), (0.7, 14, 0.7), "sandglow")
    fr.locator("drain", (0, 18, 0))
    return m
