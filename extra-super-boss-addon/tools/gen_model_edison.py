#!/usr/bin/env python3
"""
Boss 2: Thomas Edison, "the Wizard of Menlo Park" - an assassin with a broken light bulb.

  RP models/entity/edison.geo.json      + textures/entity/edison.png, edison_charged.png (phase 2, AC)
  RP models/entity/dynamo.geo.json      + textures/entity/dynamo.png, dynamo_charged.png
  RP models/entity/electric_chair.geo.json + textures/entity/electric_chair.png
  RP models/entity/volt_bulb.geo.json   + textures/entity/volt_bulb.png (thrown bulb)

From the reference art: messy black wavy hair with a white streak over his right brow, amber eyes and a
smirk, white shirt open at the collar with the sleeves rolled up, an olive-green work apron with black
leather straps and brass buckles, brown belt with brass tool tubes, long black gloves, dark trousers with a
green knee patch, black lace-up boots.  His RIGHT hand holds the broken-bulb shiv; his LEFT hand holds a
glowing bulb.  The generator cabinet (wood, brass, gauges, bulbs, levers, coils, cables) is the Dynamo.

Same conventions as gen_model.py (+X = his left, faces -Z, 4 px per unit, alpha < 255 glows).
The *_charged textures are the same atlases repainted with blue-white AC arcs for phase 2.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_model as G  # noqa: E402  (shared painters and helpers)
from gen_model import FACE_LIGHT, hexrgb, mix, outline, par, smooth_noise, tile_of, vgrad  # noqa: E402
from modelkit import FaceCtx, Model  # noqa: E402

RP = G.RP

HAIR_E = hexrgb("#211D22")
HAIR_E_HI = hexrgb("#4C4553")
HAIR_E_SH = hexrgb("#0E0B10")
STREAK = hexrgb("#ECEAE6")
STREAK_SH = hexrgb("#A9A5A1")
APRON = hexrgb("#5D6A44")
APRON_HI = hexrgb("#7A8858")
APRON_SH = hexrgb("#3D472C")
BLACK = hexrgb("#1D1A1C")
BLACK_HI = hexrgb("#4A4446")
TROUSER_E = hexrgb("#38302D")
TROUSER_E_HI = hexrgb("#52463F")
OAK = hexrgb("#7B5A3A")
OAK_SH = hexrgb("#4E3822")
DARKWOOD = hexrgb("#4A3022")
DARKWOOD_SH = hexrgb("#2C1C14")
BRONZE = hexrgb("#4A3A26")
DIAL = hexrgb("#E9DEC2")
RED_HANDLE = hexrgb("#7E2E22")
GLASS = hexrgb("#F2EEDC")
BULB_GLOW = hexrgb("#FFD27A")
BULB_CORE = hexrgb("#FFF6D8")
AC_BLUE = hexrgb("#9FE3FF")
AC_WHITE = hexrgb("#F2FBFF")

CHARGED = False  # repaint pass for the phase 2 (AC) textures


def arcs(t, ctx, density=1.0, color=None):
    """Blue-white lightning on a tile (emissive) for the charged textures."""
    if not CHARGED or min(ctx.w, ctx.h) < 6:
        return t
    rng = np.random.default_rng(int(ctx.rng.integers(0, 1 << 30)))
    h, w = ctx.h, ctx.w
    n = max(1, int(density * (w * h) / 260))
    col = color if color is not None else AC_BLUE
    for _ in range(n):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        ang = rng.uniform(0, 2 * math.pi)
        for _ in range(int(rng.integers(6, 14))):
            xi, yi = int(x), int(y)
            if 0 <= xi < w and 0 <= yi < h:
                t[yi, xi, :3] = np.clip(mix(col, AC_WHITE, rng.uniform(0, 0.6)), 0, 255)
                t[yi, xi, 3] = 30
            ang += rng.uniform(-0.9, 0.9)
            x += math.cos(ang) * 1.2
            y += math.sin(ang) * 1.2
    return t


# ------------------------------------------------------------------------------ face (male, sly smirk)

def face_grid():
    return G.handsome_face("sly")


FACE_ART = face_grid()
FACE_COL = dict(G.FACE_COL)
FACE_COL.update({"H": HAIR_E, "h": HAIR_E_SH, "X": STREAK, "x": STREAK_SH, "B": hexrgb("#17101A"),
                 "A": hexrgb("#E8902C"), "a": hexrgb("#9A4E14"), "G": hexrgb("#FFF0C8")})


def paint_face(rgb):
    h, w = rgb.shape[:2]
    out = tile_of(rgb)
    for y, row in enumerate(FACE_ART[:h]):
        for x, ch in enumerate(row[:w]):
            if ch in FACE_COL:
                col = FACE_COL[ch]
                if CHARGED and ch in "AaG":
                    col = {"A": AC_BLUE, "a": hexrgb("#4AA8E0"), "G": AC_WHITE}[ch]
                if CHARGED and ch in "Xx":
                    col = mix(col, AC_BLUE, 0.35)
                out[y, x, :3] = np.clip(col, 0, 255)
                if ch in "Aa":
                    out[y, x, 3] = 60 if CHARGED else 150
                if CHARGED and ch in "Xx":
                    out[y, x, 3] = 120
    return out


def p_skin(ctx: FaceCtx):
    rgb = np.broadcast_to(G.SKIN, (ctx.h, ctx.w, 3)).copy() * vgrad(ctx, 1.03, 0.93)[..., None]
    if ctx.p.get("face") and ctx.face == "north":
        return paint_face(rgb)
    if ctx.p.get("chin"):
        return tile_of(G.paint_chin(rgb, ctx.face) * FACE_LIGHT[ctx.face])
    if ctx.face == "down":
        rgb = mix(rgb, G.SKIN_SH, 0.5)
    return tile_of(outline(rgb, 0.88) * FACE_LIGHT[ctx.face])


def p_hair(ctx: FaceCtx):
    U, V = ctx.grid()
    w, h = ctx.w, ctx.h
    white = ctx.p.get("streak")
    base_hi, base, sh = (STREAK, mix(STREAK, STREAK_SH, 0.4), STREAK_SH) if white else (HAIR_E_HI, HAIR_E, HAIR_E_SH)
    ph = ctx.rng.random() * 10
    strands = np.sin(U * w * 0.9 + np.sin(V * 3.0 + ph) * 1.8 + ph)
    rgb = mix(base_hi, base, np.clip(V * 1.4, 0, 1)) if ctx.face != "up" else np.broadcast_to(mix(base_hi, base, 0.5), (h, w, 3))
    rgb = np.broadcast_to(rgb, (h, w, 3)).copy() * (1 + 0.13 * strands)[..., None]
    gaps = np.sin(U * w * 0.55 + ph * 2 + np.sin(V * 2.4) * 2.2) > 0.82
    rgb[gaps] = mix(rgb[gaps], sh, 0.7)
    if ctx.face in ("north", "south", "east", "west") and not white:
        band = np.exp(-((V - 0.25) / 0.07) ** 2) * (0.5 + 0.5 * np.sin(U * w * 1.3 + ph))
        rgb = mix(rgb, hexrgb("#6A6474"), np.clip(band * 0.5, 0, 1))
    if ctx.face == "down":
        rgb = mix(rgb, sh, 0.6)
    t = tile_of(outline(rgb, 0.8) * FACE_LIGHT[ctx.face])
    if white and CHARGED:
        t[..., :3] = np.clip(mix(t[..., :3].astype(float), AC_BLUE, 0.3), 0, 255)
        t[..., 3] = 140
    return t


def p_apron(ctx: FaceCtx):
    h, w = ctx.h, ctx.w
    n = smooth_noise(w, h, ctx.rng, 3.0)
    rgb = np.broadcast_to(APRON, (h, w, 3)) * (0.92 + 0.16 * n)[..., None]
    rgb = rgb * G.folds(ctx, n=ctx.p.get("fold_n", 1.6), amp=0.07, along="u")[..., None] * vgrad(ctx, 1.05, 0.88)[..., None]
    if ctx.p.get("dark"):
        rgb = mix(rgb, APRON_SH, 0.35)
    if ctx.face in ("north", "south") and min(w, h) >= 8:
        for x in range(2, w - 2, 3):  # stitched hem
            rgb[1, x] = APRON_HI
            rgb[h - 2, x] = APRON_HI
        for y in range(2, h - 2, 3):
            rgb[y, 1] = APRON_HI
            rgb[y, w - 2] = APRON_HI
    if ctx.p.get("pocket") == ctx.face and w >= 16 and h >= 16:
        x0, x1, y0, y1 = int(w * 0.2), int(w * 0.62), int(h * 0.12), int(h * 0.42)
        rgb[y0:y1, x0:x1] = mix(rgb[y0:y1, x0:x1], APRON_SH, 0.35)
        rgb[y0, x0:x1] = APRON_HI
        rgb[y0:y1, x0] = APRON_SH
        rgb[y0:y1, x1 - 1] = APRON_SH
        rgb[y0 + 2:y1 - 1, x0 + int((x1 - x0) * 0.7)] = hexrgb("#8B6A3A")  # a pencil in the pocket
    t = tile_of(outline(rgb, 0.8) * FACE_LIGHT[ctx.face])
    return arcs(t, ctx, 1.2)


def p_black(ctx: FaceCtx):
    """Black leather: gloves, straps, boots."""
    h, w = ctx.h, ctx.w
    U, V = ctx.grid()
    rgb = np.broadcast_to(BLACK, (h, w, 3)).copy()
    streak = np.exp(-((U - 0.35) / 0.12) ** 2) * (ctx.face in ("north", "south", "east", "west"))
    rgb = mix(rgb, BLACK_HI, np.clip(streak * 0.55, 0, 1)) * vgrad(ctx, 1.08, 0.9)[..., None]
    if ctx.p.get("laces") == ctx.face and w >= 6:
        lace = hexrgb("#7A6C60")
        for y in range(2, h - 1, 3):
            rgb[y, 2:w - 2] = lace  # lace bars
            rgb[y, 1] = G.BRASS_HI  # eyelets
            rgb[y, w - 2] = G.BRASS_HI
        rgb[1:h - 1, w // 2] = mix(rgb[1:h - 1, w // 2], BLACK, 0.6)  # tongue seam
    if ctx.p.get("sole") and ctx.face != "up":
        rgb[-2:, :] = hexrgb("#3A2A20")
    if ctx.p.get("stitch") and min(w, h) >= 4:
        if w >= h:
            rgb[1, 1:w - 1:3] = BLACK_HI * 1.3
            rgb[h - 2, 1:w - 1:3] = BLACK_HI * 1.3
        else:
            rgb[1:h - 1:3, 1] = BLACK_HI * 1.3
            rgb[1:h - 1:3, w - 2] = BLACK_HI * 1.3
    t = tile_of(outline(rgb, 0.7) * FACE_LIGHT[ctx.face])
    if ctx.p.get("glove"):
        t = arcs(t, ctx, 2.0)
    return t


def p_trouser(ctx: FaceCtx):
    rgb = np.broadcast_to(TROUSER_E, (ctx.h, ctx.w, 3)).copy() * G.folds(ctx, n=1.6, amp=0.12)[..., None]
    if ctx.p.get("patch") == ctx.face and ctx.w >= 8 and ctx.h >= 8:
        y0, y1 = int(ctx.h * 0.55), int(ctx.h * 0.95)
        rgb[y0:y1, 1:-1] = mix(rgb[y0:y1, 1:-1], APRON, 0.85)
        rgb[y0, 1:-1:2] = APRON_HI
    return tile_of(outline(rgb, 0.8) * FACE_LIGHT[ctx.face])


def p_glass(ctx: FaceCtx):
    """Light bulb glass: pale and glowing; the shiv is cracked and jagged."""
    h, w = ctx.h, ctx.w
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((yy - (h - 1) / 2) / max(h / 2, 1), (xx - (w - 1) / 2) / max(w / 2, 1))
    hot = AC_BLUE if CHARGED else BULB_GLOW
    rgb = mix(BULB_CORE, mix(GLASS, hot, 0.5), np.clip(r, 0, 1))
    t = tile_of(rgb, 200 if ctx.p.get("broken") else 110)
    t[..., 3] = np.where(r < 0.55, 60 if not ctx.p.get("broken") else 150, t[..., 3]).astype(np.uint8)
    if ctx.p.get("broken") and ctx.face in ("north", "south", "east", "west"):
        rng = ctx.rng
        for _ in range(3):  # crack lines
            x, y = rng.uniform(0, w), rng.uniform(0, h)
            for _ in range(6):
                xi, yi = int(x), int(y)
                if 0 <= xi < w and 0 <= yi < h:
                    t[yi, xi, :3] = hexrgb("#8C8A80")
                    t[yi, xi, 3] = 255
                x += rng.uniform(-1, 1)
                y += rng.uniform(0.5, 1.2)
        # jagged top edge
        for x in range(w):
            for y in range(int(abs(math.sin(x * 2.1)) * 2)):
                t[y, x, 3] = 255
                t[y, x, :3] = hexrgb("#BDB8A8")
    return t


def p_filament(ctx: FaceCtx):
    t = tile_of(np.broadcast_to(AC_WHITE if CHARGED else hexrgb("#FFE6A0"), (ctx.h, ctx.w, 3)), 10)
    return t


def p_wood_dark(ctx: FaceCtx):
    h, w = ctx.h, ctx.w
    U, V = ctx.grid()
    oak = ctx.p.get("oak")
    a, b = (OAK, OAK_SH) if oak else (DARKWOOD, DARKWOOD_SH)
    along_u = w >= h
    grain = np.sin((V if along_u else U) * 30 + np.sin((U if along_u else V) * 6 + ctx.rng.random() * 6) * 2.5)
    rgb = mix(a, b, np.clip(0.35 + 0.3 * grain, 0, 1))
    if ctx.p.get("brass_edge") and min(w, h) >= 6:
        rgb[:2, :] = G.BRASS
        rgb[-2:, :] = G.BRASS_SH
    return tile_of(outline(rgb, 0.75) * FACE_LIGHT[ctx.face])


def p_panel(ctx: FaceCtx):
    """Bronze machine plate with rivets; optional gauge dial or switch plate art on the front."""
    h, w = ctx.h, ctx.w
    n = smooth_noise(w, h, ctx.rng, 4.0)
    rgb = np.broadcast_to(BRONZE, (h, w, 3)) * (0.85 + 0.3 * n)[..., None]
    rgb = rgb * vgrad(ctx, 1.08, 0.9)[..., None]
    if min(w, h) >= 8:
        for (x, y) in ((1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)):
            rgb[y, x] = G.BRASS_HI
    t = tile_of(outline(rgb, 0.7) * FACE_LIGHT[ctx.face])
    if ctx.p.get("dial") and ctx.face == "north":
        t = paint_dial(t)
    if CHARGED and ctx.p.get("charge"):
        t = arcs(t, ctx, 0.8)
    return t


def paint_dial(t):
    h, w = t.shape[:2]
    cy, cx = (h - 1) / 2, (w - 1) / 2
    yy, xx = np.mgrid[0:h, 0:w]
    rr = np.hypot(yy - cy, xx - cx)
    R = min(h, w) / 2 - 0.5
    face = rr < R - 1
    t[rr < R, :3] = G.BRASS
    t[face, :3] = DIAL
    ang = np.degrees(np.arctan2(yy - cy, xx - cx))
    ticks = face & (rr > R - 3) & (np.abs(((ang + 360) % 30) - 15) > 13) & (ang < 0)
    t[ticks, :3] = hexrgb("#3A2A1A")
    # needle
    a = math.radians(-60)
    for k in range(int(R - 1)):
        x, y = int(round(cx + math.cos(a) * k)), int(round(cy + math.sin(a) * k))
        if 0 <= x < w and 0 <= y < h:
            t[y, x, :3] = hexrgb("#1A1210")
    t[int(cy), int(cx), :3] = hexrgb("#7E2E22")
    return t


def p_rubber(ctx: FaceCtx):
    U, V = ctx.grid()
    rgb = mix(hexrgb("#3C3A3C"), hexrgb("#121112"), np.clip(np.abs(U - 0.35) * 2, 0, 1))
    rgb = np.broadcast_to(rgb, (ctx.h, ctx.w, 3)).copy()
    if ctx.p.get("rings") and ctx.face in ("north", "south", "east", "west"):
        for f in (0.15, 0.5, 0.85):
            y = int(ctx.h * f)
            rgb[max(0, y - 1):y + 1, :] = G.BRASS
    t = tile_of(outline(rgb, 0.8) * FACE_LIGHT[ctx.face])
    return arcs(t, ctx, 1.0) if ctx.p.get("charge") else t


def p_handle(ctx: FaceCtx):
    rgb = np.broadcast_to(RED_HANDLE, (ctx.h, ctx.w, 3)) * vgrad(ctx, 1.15, 0.85)[..., None]
    return tile_of(outline(rgb, 0.75) * FACE_LIGHT[ctx.face])


PAINTERS = dict(G.PAINTERS)
PAINTERS.update({
    "skin": p_skin, "hair": p_hair, "apron": p_apron, "black": p_black, "trouser": p_trouser, "glass": p_glass,
    "filament": p_filament, "wood": p_wood_dark, "panel": p_panel, "rubber": p_rubber, "handle": p_handle,
})


# ------------------------------------------------------------------------------ Edison

def build_edison() -> Model:
    m = Model("geometry.esb.edison")
    m.bone("root", None, (0, 0, 0))
    m.bone("body", "root", (0, 17, 0))
    m.cube("body", (-4.2, 16.5, -2.4), (8.4, 2.0, 4.8), "leather", stitch=True)  # belt
    m.cube("body", (-0.9, 16.4, -2.7), (1.8, 2.2, 0.4), "brass", rivets=True)  # buckle
    m.cube("body", (-4.6, 12.5, -1.75), (1.25, 4.5, 1.25), "brass", seams=2)  # tool tubes (right hip)
    m.cube("body", (-4.5, 13.75, -0.25), (1.0, 3.25, 1.0), "brass", seams=1)
    m.cube("body", (-4.7, 15.75, -1.95), (1.6, 1.0, 1.6), "leather")
    # apron skirt: two panels so the legs can move
    m.bone("apron_l", "body", (2.0, 17, -2.6))
    m.cube("apron_l", (0.05, 6.5, -2.95), (3.9, 10.5, 0.45), "apron", pocket="north", fold_n=1.0)
    m.bone("apron_r", "body", (-2.0, 17, -2.6))
    m.cube("apron_r", (-3.95, 6.5, -2.95), (3.9, 10.5, 0.45), "apron", fold_n=1.0)
    m.cube("body", (-4.4, 9.5, -2.0), (0.4, 7.5, 4.0), "apron", dark=True)  # apron sides wrap the hips
    m.cube("body", (4.0, 9.5, -2.0), (0.4, 7.5, 4.0), "apron", dark=True)

    m.bone("torso", "body", (0, 18, 0))
    m.cube("torso", (-4, 18.25, -2.2), (8, 10.5, 4.4), "shirt", fold_n=2.0, inner_shadow=True)
    m.cube("torso", (-2.0, 26.25, -2.45), (4.0, 2.5, 0.3), "black")  # dark undershirt in the open collar
    m.cube("torso", (0.6, 27.75, -2.75), (2.4, 2.0, 0.45), "shirt", rotation=(-14, -30, -12), pivot=(0.8, 28.2, -2.5))
    m.cube("torso", (-3.0, 27.75, -2.75), (2.4, 2.0, 0.45), "shirt", rotation=(-14, 30, 12), pivot=(-0.8, 28.2, -2.5))
    m.cube("torso", (-2.6, 27.9, -1.4), (5.2, 1.3, 3.4), "shirt")
    # apron bib, straps over the shoulders crossing on the back, brass buckles, a chain
    m.cube("torso", (-3.0, 18.25, -2.65), (6.0, 7.25, 0.45), "apron")
    m.cube("torso", (-3.0, 25.0, -2.75), (1.0, 4.0, 0.35), "black", stitch=True)
    m.cube("torso", (2.0, 25.0, -2.75), (1.0, 4.0, 0.35), "black", stitch=True)
    m.cube("torso", (-3.1, 24.6, -2.95), (1.2, 1.1, 0.3), "brass")
    m.cube("torso", (1.9, 24.6, -2.95), (1.2, 1.1, 0.3), "brass")
    m.cube("torso", (-3.0, 28.4, -2.3), (1.0, 0.45, 4.6), "black")  # over the shoulders
    m.cube("torso", (2.0, 28.4, -2.3), (1.0, 0.45, 4.6), "black")
    m.cube("torso", (-0.5, 17.5, 2.2), (1.0, 12.5, 0.35), "black", rotation=(0, 0, 32), pivot=(0, 23.5, 2.35))
    m.cube("torso", (-0.5, 17.5, 2.25), (1.0, 12.5, 0.35), "black", rotation=(0, 0, -32), pivot=(0, 23.5, 2.4))
    for i in range(5):
        m.cube("torso", (2.3 - i * 0.05, 23.9 - i * 0.65, -2.98), (0.45, 0.55, 0.2), "gold")
    m.locator("torso", "loc_chest_e", (0, 22, -2.8))

    # head & hair (messy black, white streak over his right brow)
    m.bone("head", "torso", (0, 29, 0))
    m.cube("head", (-1.5, 27.75, -1.5), (3.0, 2.25, 3.0), "skin")
    m.cube("head", (-3.5, 29.5, -3.5), (7, 7, 7), "skin", face=True)
    m.cube("head", (3.45, 31.25, -1.5), (0.45, 1.75, 1.0), "skin")
    m.cube("head", (-3.9, 31.25, -1.5), (0.45, 1.75, 1.0), "skin")
    m.cube("head", (-3.8, 34.5, -3.8), (7.6, 2.75, 7.6), "hair")
    m.cube("head", (-3.95, 28.5, 0.5), (7.9, 6.5, 3.5), "hair")  # back
    m.cube("head", (3.2, 29.75, -1.0), (1.1, 5.0, 3.5), "hair")  # sides
    m.cube("head", (-4.3, 29.75, -1.0), (1.1, 5.0, 3.5), "hair")
    m.cube("head", (-3.5, 27.0, 1.5), (7.0, 2.0, 2.25), "hair", rotation=(-20, 0, 0), pivot=(0, 28.75, 2.5))  # nape flick
    # messy tufts on top
    for (x, z, rz, rx) in ((-3.2, -3.0, 18, -10), (-0.6, -3.4, -12, -16), (1.6, -2.4, -24, -6), (-2.4, 0.5, 12, 18),
                           (0.8, 0.8, -16, 22)):
        m.cube("head", (x, 36.75, z), (2.4, 1.1, 3.4), "hair", rotation=(rx, 0, rz), pivot=(x + 1.2, 37, z + 1.7))
    # fringe strands (one white)
    for (x, ln, rz) in ((-1.0, 3.0, 10), (0.5, 3.4, -6), (1.9, 2.8, -16), (2.8, 3.6, -8)):
        m.cube("head", (x, 36.5 - ln, -3.95), (1.2, ln, 0.6), "hair", rotation=(0, 0, rz), pivot=(x + 0.6, 36.5, -3.65))
    m.cube("head", (-3.3, 33.6, -3.98), (1.0, 2.9, 0.65), "hair", streak=True, rotation=(0, 0, -14), pivot=(-2.8, 36.5, -3.65))
    m.cube("head", (-3.9, 33.0, -2.5), (0.6, 3.5, 1.6), "hair", streak=True)
    m.locator("head", "loc_head_e", (0, 33, -3.6))

    # right arm: rolled sleeve, black glove, broken-bulb shiv
    m.bone("arm_r", "torso", (-5.0, 28.0, 0))
    m.cube("arm_r", (-6.75, 22.25, -1.75), (3.4, 6.75, 3.5), "shirt", folds_v=True, fold_n=1.4)
    m.cube("arm_r", (-6.95, 22.0, -1.95), (3.8, 1.5, 3.9), "shirt", band=True)  # rolled cuff
    m.bone("forearm_r", "arm_r", (-5.0, 22.25, 0))
    m.cube("forearm_r", (-6.5, 16.25, -1.5), (3.0, 6.0, 3.0), "black", glove=True)
    m.bone("hand_r", "forearm_r", (-5.0, 16.25, 0))
    m.cube("hand_r", (-6.3, 13.5, -1.3), (2.6, 2.9, 2.6), "black", glove=True)
    m.bone("shiv", "hand_r", (-5.0, 14.25, -1.0))
    m.cube("shiv", (-5.55, 13.2, -2.6), (1.1, 1.1, 1.6), "brass", seams=1)  # screw base held in the fist
    m.cube("shiv", (-5.9, 13.0, -5.4), (1.8, 1.6, 2.8), "glass", broken=True)  # broken glass blade (points forward)
    m.cube("shiv", (-5.4, 13.4, -6.9), (0.8, 0.8, 1.6), "glass", broken=True, rotation=(10, 18, 0), pivot=(-5, 13.8, -5.4))
    m.cube("shiv", (-5.25, 13.6, -5.2), (0.5, 0.4, 2.0), "filament")
    m.locator("shiv", "loc_shiv", (-5.0, 13.8, -6.8))

    # left arm: rolled sleeve with a green armband, black glove, a glowing bulb
    m.bone("arm_l", "torso", (5.0, 28.0, 0))
    m.cube("arm_l", (3.35, 22.25, -1.75), (3.4, 6.75, 3.5), "shirt", folds_v=True, fold_n=1.4)
    m.cube("arm_l", (3.2, 25.0, -1.9), (3.7, 1.5, 3.8), "apron")  # armband
    m.cube("arm_l", (3.15, 22.0, -1.95), (3.8, 1.5, 3.9), "shirt", band=True)
    m.bone("forearm_l", "arm_l", (5.0, 22.25, 0))
    m.cube("forearm_l", (3.5, 16.25, -1.5), (3.0, 6.0, 3.0), "black", glove=True)
    m.bone("hand_l", "forearm_l", (5.0, 16.25, 0))
    m.cube("hand_l", (3.7, 13.5, -1.3), (2.6, 2.9, 2.6), "black", glove=True)
    m.bone("bulb_l", "hand_l", (5.0, 13.5, 0))
    m.cube("bulb_l", (4.4, 12.0, -0.6), (1.2, 1.4, 1.2), "brass", seams=1)
    m.cube("bulb_l", (3.9, 9.4, -1.1), (2.2, 2.6, 2.2), "glass")
    m.cube("bulb_l", (4.2, 9.1, -0.8), (1.6, 0.6, 1.6), "glass")
    m.cube("bulb_l", (4.75, 10.2, -0.25), (0.5, 1.4, 0.5), "filament")
    m.locator("bulb_l", "loc_bulb", (5.0, 10.6, 0))

    # legs: dark trousers, green knee patch on the right, black lace-up boots
    m.bone("leg_l", "root", (2.0, 17, 0))
    m.cube("leg_l", (0.3, 8.75, -1.7), (3.4, 8.75, 3.4), "trouser")
    m.bone("shin_l", "leg_l", (2.0, 8.75, 0))
    m.cube("shin_l", (0.3, 2.25, -1.7), (3.4, 6.75, 3.4), "trouser")
    m.cube("shin_l", (0.15, 2.25, -1.85), (3.7, 5.0, 3.7), "black", laces="north")
    m.bone("foot_l", "shin_l", (2.0, 2.25, -0.25))
    m.cube("foot_l", (0.15, 0, -4.0), (3.7, 2.5, 5.75), "black", sole=True, laces="up")
    m.cube("foot_l", (0.5, 0, -4.6), (3.0, 1.75, 0.75), "black", sole=True)
    m.mirror(names={"leg_l", "shin_l", "foot_l"})
    for c in m.bones["shin_r"].cubes[:1]:
        c.params = dict(c.params, patch="north")

    m.locator("root", "loc_ground_e", (0, 0.25, 0))
    return m


# ------------------------------------------------------------------------------ Dynamo (generator cabinet)

def build_dynamo() -> Model:
    m = Model("geometry.esb.dynamo")
    m.bone("root", None, (0, 0, 0))
    m.bone("cabinet", "root", (0, 0, 0))
    m.cube("cabinet", (-11, 0, -8), (22, 3, 16), "wood", brass_edge=True)  # plinth
    for x in (-11.5, 8.5):
        for z in (-8.5, 5.5):
            m.cube("cabinet", (x, 0, z), (3, 3.5, 3), "brass", rivets=True)  # brass feet
    m.cube("cabinet", (-10, 3, -7), (20, 28, 14), "wood")
    m.cube("cabinet", (-11, 31, -8), (22, 2.5, 16), "wood", brass_edge=True)  # top
    for x in (-10.5, 9.5):
        m.cube("cabinet", (x, 3, -7.5), (1, 28, 1), "brass")  # brass corner rails
    m.cube("cabinet", (-8, 4.5, -7.5), (16, 25, 0.5), "panel", charge=True)  # front plate
    m.cube("cabinet", (-8.5, 16.5, -7.8), (17, 0.6, 0.6), "brass")  # dividers
    m.cube("cabinet", (-8.5, 11.0, -7.8), (17, 0.6, 0.6), "brass")
    for i, x in enumerate((-6.75, -1.75, 3.25)):
        m.cube("cabinet", (x, 17.75, -8.1), (3.5, 3.5, 0.6), "panel", dial=True)  # gauges
    # levers
    for i, x in enumerate((-5.5, -0.75, 4.0)):
        b = f"lever_{i + 1}"
        m.cube("cabinet", (x - 0.6, 12.0, -8.1), (2.2, 3.6, 0.6), "brass", rivets=True)
        m.bone(b, "cabinet", (x + 0.5, 15.0, -8.3))
        m.cube(b, (x + 0.1, 11.5, -8.9), (0.8, 3.75, 0.8), "handle")
        m.cube(b, (x + 0.25, 14.5, -8.7), (0.5, 0.75, 0.5), "brass")
    # bulbs on top section and in the lower window
    for i, (x, y) in enumerate(((-6.5, 23.5), (-2.5, 23.5), (1.5, 23.5), (5.5, 23.5), (2.5, 6.0))):
        b = f"bulb_{i + 1}"
        m.bone(b, "cabinet", (x, y, -8.4))
        m.cube(b, (x - 0.75, y, -9.1), (1.5, 1.2, 1.5), "brass")
        m.cube(b, (x - 1.0, y + 1.2, -9.35), (2.0, 2.8, 2.0), "glass")
        m.cube(b, (x - 0.25, y + 1.8, -8.6), (0.5, 1.4, 0.5), "filament")
    m.cube("cabinet", (-6.5, 5.5, -8.0), (6.0, 4.5, 0.6), "panel")  # lower window coil
    m.cube("cabinet", (-5.5, 6.0, -9.0), (2.5, 3.5, 1.2), "rubber", rings=True, charge=True)
    # side coils and cables
    m.cube("cabinet", (-14.0, 12.0, -2.0), (4.0, 13.0, 4.0), "rubber", rings=True, charge=True)
    m.cube("cabinet", (-13.5, 11.0, -1.5), (3.0, 1.0, 3.0), "brass")
    m.cube("cabinet", (-13.5, 25.0, -1.5), (3.0, 1.0, 3.0), "brass")
    for (x, z, y0, h) in ((10.0, -4.0, 3.0, 22.0), (10.5, -1.5, 0.0, 26.0), (10.0, 1.5, 3.0, 18.0)):
        m.cube("cabinet", (x, y0, z), (1.2, h, 1.2), "rubber", charge=True)
    m.cube("cabinet", (-12.5, 0.0, -6.0), (1.2, 12.0, 1.2), "rubber")
    m.cube("cabinet", (-12.5, 0.0, -6.0), (8.0, 1.2, 1.2), "rubber")
    m.locator("cabinet", "loc_top", (0, 33.5, 0))
    m.locator("cabinet", "loc_coil", (-12, 22, 0))
    m.locator("cabinet", "loc_panel", (0, 22, -9))
    return m


# ------------------------------------------------------------------------------ Electric chair

def build_chair() -> Model:
    m = Model("geometry.esb.electric_chair")
    m.bone("root", None, (0, 0, 0))
    m.bone("frame", "root", (0, 0, 0))
    for x in (-6, 4):
        for z in (-6, 4):
            m.cube("frame", (x, 0, z), (2, 8, 2), "wood", oak=True)
    m.cube("frame", (-6.5, 8, -6.5), (13, 2, 13), "wood", oak=True)  # seat
    m.cube("frame", (-6.5, 10, 4.5), (13, 20, 2), "wood", oak=True)  # back
    m.cube("frame", (-7.5, 14, -6.5), (2, 2, 12), "wood", oak=True)  # arms
    m.cube("frame", (5.5, 14, -6.5), (2, 2, 12), "wood", oak=True)
    m.cube("frame", (-7.5, 10, -6.5), (2, 4, 2), "wood", oak=True)
    m.cube("frame", (5.5, 10, -6.5), (2, 4, 2), "wood", oak=True)
    m.cube("frame", (-1.0, 30, 4.5), (2, 6, 2), "brass", rivets=True)  # helmet mast
    m.cube("frame", (-1.0, 34, -1.5), (2, 2, 7.5), "brass")
    m.cube("frame", (-4.0, 26.0, 5.5), (1.2, 10.0, 1.2), "rubber", rotation=(0, 0, 12), pivot=(-3.4, 36, 6))
    m.cube("frame", (-7.0, 0.0, 6.5), (1.2, 26.0, 1.2), "rubber")
    m.bone("helmet", "frame", (0, 33, 0))
    m.cube("helmet", (-3.5, 29.5, -3.5), (7, 3.5, 7), "steel", gear=True)
    m.cube("helmet", (-0.75, 33.0, -0.75), (1.5, 1.0, 1.5), "brass")
    m.bone("straps", "frame", (0, 15, 0))
    for x in (-7.6, 5.4):
        m.cube("straps", (x, 15.9, -4.0), (2.2, 0.4, 1.6), "black", stitch=True)
        m.cube("straps", (x, 15.9, -0.5), (2.2, 0.4, 1.6), "black", stitch=True)
    for x in (-5.5, 3.5):
        m.cube("straps", (x, 3.5, -6.6), (2.0, 1.2, 2.2), "black")
    m.cube("straps", (-6.6, 20.0, 4.3), (13.2, 1.5, 0.4), "black", stitch=True)  # chest strap
    m.locator("helmet", "loc_helmet", (0, 29.5, 0))
    m.locator("frame", "loc_seat", (0, 10, 0))
    return m


# ------------------------------------------------------------------------------ thrown bulb

def build_bulb() -> Model:
    m = Model("geometry.esb.volt_bulb")
    m.bone("root", None, (0, 0, 0))
    m.bone("spin", "root", (0, 3, 0))
    m.cube("spin", (-0.75, 4.2, -0.75), (1.5, 1.3, 1.5), "brass", seams=1)
    m.cube("spin", (-1.4, 1.2, -1.4), (2.8, 3.0, 2.8), "glass")
    m.cube("spin", (-1.0, 0.8, -1.0), (2.0, 0.6, 2.0), "glass")
    m.cube("spin", (-0.3, 2.0, -0.3), (0.6, 1.6, 0.6), "filament")
    m.locator("spin", "loc_bulb_p", (0, 3, 0))
    return m


def export(model, name, tex_w, ppu, bounds, charged=False):
    global CHARGED
    used = model.pack(tex_w, pad=1, ppu=ppu)
    h = 1
    while h < used:
        h *= 2
    CHARGED = False
    img = model.paint(tex_w, h, PAINTERS, seed=11)
    os.makedirs(os.path.join(RP, "models", "entity"), exist_ok=True)
    with open(os.path.join(RP, "models", "entity", f"{name}.geo.json"), "w") as f:
        json.dump(model.to_json(tex_w, h, *bounds), f, indent=1)
    Image.fromarray(img, "RGBA").save(os.path.join(RP, "textures", "entity", f"{name}.png"))
    if charged:
        CHARGED = True
        img2 = model.paint(tex_w, h, PAINTERS, seed=11)
        Image.fromarray(img2, "RGBA").save(os.path.join(RP, "textures", "entity", f"{name}_charged.png"))
        CHARGED = False
    nb, nc = model.stats()
    print(f"{name}: {nb} bones, {nc} cubes, texture {tex_w}x{h}")


def main():
    export(build_edison(), "edison", 512, 4, (3.5, 3.5, [0, 1.5, 0]), charged=True)
    export(build_dynamo(), "dynamo", 512, 4, (3, 3, [0, 1.2, 0]), charged=True)
    export(build_chair(), "electric_chair", 256, 2, (2, 3, [0, 1.2, 0]))
    export(build_bulb(), "volt_bulb", 64, 4, (1, 1, [0, 0.3, 0]))


if __name__ == "__main__":
    main()
