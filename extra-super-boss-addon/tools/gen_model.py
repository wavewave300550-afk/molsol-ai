#!/usr/bin/env python3
"""
Leonardo da Vinci boss model  ->  RP models/entity/da_vinci.geo.json
                                  RP textures/entity/da_vinci.png

Built from the reference art: long wavy brown hair tied half-up, amber eyes, cream shirt with
an open collar and full sleeves, dark brown brocade vest, two leather straps crossing the chest
with brass medallions, crimson mantle with gold trim falling into long back tails (gold hem and
a compass-rose emblem), crimson sash and leather belts, brass scroll tube at the left hip, dark
trousers, tall brown boots with folded cuffs and gold fleur ornaments.  The LEFT arm is a brass
clockwork gauntlet (steel gear ring at the elbow, glowing amber core, jointed fingers); the
RIGHT hand holds a brass drafting compass, his weapon.

Phase 2 adds ornithopter wings (wood spars + parchment canvas covered in sepia sketches) that
are scaled to 0 by the animations until he transforms.

Coordinates: Bedrock model units (16 = 1 block), +Y up, the boss faces -Z, +X is HIS LEFT.
Texture: 4 pixels per unit (UVs are written in pixels; texture size = PNG size).
Pixels with alpha < 255 glow under the entity_emissive material.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modelkit import FaceCtx, Model  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "extra_super_boss")
PPU = 4
TEX_W = 512


def hexrgb(s):
    s = s.lstrip("#")
    return np.array([int(s[i:i + 2], 16) for i in (0, 2, 4)], dtype=float)


# ------------------------------------------------------------------------------ palette (from the art)
SKIN = hexrgb("#F2CDB0")
SKIN_SH = hexrgb("#D9A486")
HAIR = hexrgb("#6A3F22")
HAIR_HI = hexrgb("#9A6438")
HAIR_SH = hexrgb("#3F2414")
SHIRT = hexrgb("#EFE6D4")
SHIRT_SH = hexrgb("#C9B99F")
VEST = hexrgb("#3A251E")
VEST_HI = hexrgb("#57392C")
CRIMSON = hexrgb("#7E1F2A")
CRIMSON_HI = hexrgb("#A0313A")
CRIMSON_SH = hexrgb("#561520")
GOLD = hexrgb("#CFA556")
GOLD_HI = hexrgb("#F1D489")
GOLD_SH = hexrgb("#8A6430")
BRASS = hexrgb("#B98A3C")
BRASS_HI = hexrgb("#EBC570")
BRASS_SH = hexrgb("#6A4A20")
STEEL = hexrgb("#5E5B5A")
STEEL_HI = hexrgb("#9C9893")
STEEL_SH = hexrgb("#2E2C2C")
LEATHER = hexrgb("#5C3A25")
LEATHER_SH = hexrgb("#3A2417")
BOOT = hexrgb("#4B2F23")
BOOT_HI = hexrgb("#7A5240")
TROUSER = hexrgb("#2D2427")
TROUSER_HI = hexrgb("#43363A")
WOOD = hexrgb("#6E4A2A")
WOOD_SH = hexrgb("#47301B")
PARCH = hexrgb("#DCC69A")
PARCH_SH = hexrgb("#B89D6B")
INK = hexrgb("#5A3B1E")
AMBER = hexrgb("#FFB13B")
AMBER_HI = hexrgb("#FFF0B5")

GLOW_ALPHA = 10


def mix(a, b, t):
    t = np.asarray(t, dtype=float)
    if t.ndim:
        t = t[..., None]
    return a * (1 - t) + b * t


def tile_of(rgb, alpha=255):
    h, w = rgb.shape[:2]
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = alpha
    return out


def smooth_noise(w, h, rng, cell=4.0):
    gw, gh = int(w / cell) + 3, int(h / cell) + 3
    g = rng.random((gh, gw))
    xs, ys = np.arange(w) / cell, np.arange(h) / cell
    x0, y0 = np.floor(xs).astype(int), np.floor(ys).astype(int)
    fx, fy = xs - x0, ys - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = g[y0][:, x0]
    b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]
    d = g[y0 + 1][:, x0 + 1]
    top = a * (1 - fx) + b * fx
    bot = c * (1 - fx) + d * fx
    return top * (1 - fy[:, None]) + bot * fy[:, None]


SWAP = {"east": "west", "west": "east", "left": "right", "right": "left"}


def par(ctx, key, default=None):
    """Cube parameter, with east/west and left/right swapped on mirrored (right side) cubes."""
    v = ctx.p.get(key, default)
    if not ctx.p.get("mirrored") or v is None:
        return v
    if isinstance(v, str):
        return SWAP.get(v, v)
    if isinstance(v, dict):
        return {SWAP.get(k, k): tuple(SWAP.get(e, e) for e in vv) if isinstance(vv, tuple) else vv for k, vv in v.items()}
    return v


FACE_LIGHT = {"up": 1.10, "north": 1.0, "south": 0.97, "east": 0.95, "west": 0.95, "down": 0.80}


def vgrad(ctx, top=1.06, bot=0.90):
    """Vertical light falloff on side faces (v = 0 at the top)."""
    if ctx.face in ("up", "down"):
        return np.ones((ctx.h, ctx.w))
    v = (np.arange(ctx.h) + 0.5) / ctx.h
    return np.broadcast_to((top * (1 - v) + bot * v)[:, None], (ctx.h, ctx.w))


def outline(rgb, k=0.78, px=1):
    """Darken the outer ring of a face: gives the cel-shaded edge of the art."""
    h, w = rgb.shape[:2]
    if h < 5 or w < 5:
        return rgb
    out = rgb.copy()
    out[:px] *= k
    out[-px:] *= k
    out[:, :px] *= k
    out[:, -px:] *= k
    return out


def folds(ctx, n=3.0, amp=0.09, along="u"):
    """Soft cloth folds: shading that varies across the face."""
    U, V = ctx.grid()
    ph = ctx.rng.random() * 6.28
    x = U if along == "u" else V
    f = np.sin(x * n * 6.283 + ph) * 0.6 + np.sin(x * n * 2.1 * 6.283 + ph * 1.7) * 0.4
    return 1 + amp * f


# ------------------------------------------------------------------------------ painters

def p_skin(ctx: FaceCtx):
    rgb = np.broadcast_to(SKIN, (ctx.h, ctx.w, 3)).copy()
    rgb = rgb * vgrad(ctx, 1.03, 0.93)[..., None]
    if ctx.p.get("face") and ctx.face == "north":
        return paint_face(rgb)
    if ctx.p.get("chin"):
        return tile_of(paint_chin(rgb, ctx.face) * FACE_LIGHT[ctx.face])
    if ctx.face == "down":
        rgb = mix(rgb, SKIN_SH, 0.5)
    return tile_of(outline(rgb, 0.88) * FACE_LIGHT[ctx.face])


# Face, 28 x 28 px (7 x 7 units at 4 px/unit) - the head's north face, drawn as a handsome anime man:
# large almond eyes close to the centre with a heavy upper lash line and a sharp outer corner, clean angled
# brows, a minimal nose (only the shadow under the tip), a short firm mouth and a soft V-shaped jaw shadow.
# Rows 0-8 sit under the hair cap.  style: "stern" (Da Vinci) or "sly" (Edison: one brow raised, smirk).
#  H hair  h hair shadow  B brow  K lash line  k soft lid  W eye white  A iris  a iris dark  P pupil  G glint
#  s skin shadow  j jaw shade  n nose shadow  m mouth  l lower lip  c chin light
def handsome_face(style="stern"):
    W = H = 28
    g = [["." for _ in range(W)] for _ in range(H)]

    def put(x, y, ch):
        if 0 <= x < W and 0 <= y < H and ch != " ":
            g[y][x] = ch

    def stamp(x0, y0, rows):
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                put(x0 + dx, y0 + dy, ch)

    for y in range(0, 9):
        for x in range(W):
            put(x, y, "H")
    for x, d in ((0, 3), (1, 3), (2, 2), (3, 1), (7, 1), (12, 1), (17, 1), (22, 1), (24, 1), (25, 2), (26, 3), (27, 3)):
        for k in range(d):
            put(x, 9 + k, "h" if k == d - 1 else "H")
    for y in range(9, 19):  # sideburns
        put(0, y, "h")
        put(27, y, "h")
    # brows: two pixels thick, the inner ends lower (stern) - Edison arches his left one (sly)
    stamp(4, 10, ["BBBBBB  ", "   BBBBB"])
    if style == "sly":
        stamp(16, 9, ["  BBBBBB", "BBBB   B"])
    else:
        stamp(16, 10, ["  BBBBBB", "BBBBB   "])
    # eyes: 7 x 5 almond with a heavy upper lash, a 4-px iris, pupil, glint on the upper left
    stamp(5, 13, [" KKKKKK",
                  "KKGaaaK",
                  "KWAPPAW",
                  " sAAAA ",
                  "   ss  "])
    stamp(16, 13, ["KKKKKK ",
                   "KGaaaKK",
                   "WAPPAWK",
                   " AAAAs ",
                   "  ss   "])
    # nose: only the shadow under the tip
    put(14, 19, "s")
    put(13, 20, "n")
    put(14, 20, "n")
    # mouth
    if style == "sly":
        stamp(11, 22, ["     mm", "mmmmmm ", " llll  "])
    else:
        stamp(11, 23, ["mmmmmm", " llll "])
    # a soft jaw: small shaded triangles in the lower corners, light on the chin
    for y in range(23, 28):
        for x in range(y - 22):
            put(x, y, "s")
            put(W - 1 - x, y, "s")
    for x in range(11, 17):
        put(x, 27, "c")
    return ["".join(r) for r in g]


def face_grid():
    return handsome_face("stern")


FACE_ART = face_grid()
FACE_COL = {
    "H": HAIR, "h": HAIR_SH, "B": hexrgb("#3E2314"), "K": hexrgb("#1E120A"), "k": hexrgb("#6E5040"),
    "W": hexrgb("#F2EBE2"), "A": hexrgb("#D3A23E"), "a": hexrgb("#8E5F1B"), "P": hexrgb("#2E1A0A"), "G": hexrgb("#FFF6DA"),
    "s": hexrgb("#E2B69A"), "j": hexrgb("#D7A587"), "n": hexrgb("#CF9C82"), "m": hexrgb("#A8665C"),
    "l": hexrgb("#E4B09A"), "c": hexrgb("#F6D6BE"),
}
EYE_GLOW = {"A": 190, "a": 190}


def paint_face(rgb):
    h, w = rgb.shape[:2]
    out = tile_of(rgb)
    for y, row in enumerate(FACE_ART[:h]):
        row = row.ljust(w, ".")
        for x, ch in enumerate(row[:w]):
            if ch in FACE_COL:
                col = FACE_COL[ch]
                if ch in "Hh":
                    col = col * (1.0 + 0.05 * math.sin(x * 1.7 + y))
                out[y, x, :3] = np.clip(col, 0, 255)
                if ch in EYE_GLOW:
                    out[y, x, 3] = EYE_GLOW[ch]
    return out  # RGBA: the eye glow lives in alpha


def paint_chin(rgb, face):
    """The chin cube under the head: jaw contour on the sides, shadow underneath."""
    h, w = rgb.shape[:2]
    out = rgb.copy()
    if face == "north":
        out[:, :2] = hexrgb("#C38F72")
        out[:, -2:] = hexrgb("#C38F72")
        out[-1, :] = SKIN_SH
        out[0, w // 2 - 2:w // 2 + 2] = SKIN_SH
    elif face in ("east", "west"):
        out[:] = mix(out, SKIN_SH, 0.45)
    elif face == "down":
        out[:] = SKIN_SH * 0.85
    return out


def p_hair(ctx: FaceCtx):
    U, V = ctx.grid()
    w, h = ctx.w, ctx.h
    # strands run along the hair's length (v on side faces, along z on the top face)
    across = U if ctx.face != "up" else U
    ph = ctx.rng.random() * 10
    strands = np.sin(across * w * 0.9 + np.sin(V * 3.0 + ph) * 1.6 + ph)
    base = mix(HAIR_HI, HAIR, np.clip(V * 1.3, 0, 1)) if ctx.face != "up" else mix(HAIR_HI, HAIR, 0.35)
    if ctx.face == "down":
        base = np.broadcast_to(HAIR_SH, (h, w, 3))
    rgb = np.broadcast_to(base, (h, w, 3)).copy()
    rgb = rgb * (1 + 0.10 * strands)[..., None]
    # dark strand gaps
    gaps = (np.sin(across * w * 0.55 + ph * 2 + np.sin(V * 2.4) * 2.2) > 0.86)
    rgb[gaps] = mix(rgb[gaps], HAIR_SH, 0.6)
    # the "angel ring" shine of anime hair on the upper part of side faces
    if ctx.p.get("shine") and ctx.face in ("north", "south", "east", "west"):
        band = np.exp(-((V - 0.28) / 0.07) ** 2) * (0.5 + 0.5 * np.sin(across * w * 1.3 + ph))
        rgb = mix(rgb, hexrgb("#C08A55"), np.clip(band * 0.55, 0, 1))
    if ctx.p.get("tips"):
        rgb = mix(rgb, HAIR_SH, np.clip((V - 0.75) * 2.2, 0, 1) * (ctx.face != "up"))
    return tile_of(outline(rgb, 0.85) * FACE_LIGHT[ctx.face])


def p_shirt(ctx: FaceCtx):
    rgb = np.broadcast_to(SHIRT, (ctx.h, ctx.w, 3)).copy()
    along = "v" if ctx.p.get("folds_v") else "u"
    rgb = rgb * folds(ctx, n=ctx.p.get("fold_n", 2.2), amp=0.07, along=along)[..., None]
    rgb = rgb * vgrad(ctx, 1.03, 0.90)[..., None]
    if ctx.p.get("inner_shadow") and ctx.face in ("north", "south"):
        U, V = ctx.grid()
        rgb = mix(rgb, SHIRT_SH, np.clip(1 - np.abs(U - 0.5) * 2.6, 0, 1) * 0.35)
    if ctx.p.get("band"):
        rgb = mix(rgb, SHIRT_SH, 0.35)
    if ctx.face == "down":
        rgb = mix(rgb, SHIRT_SH, 0.6)
    return tile_of(outline(rgb, 0.84) * FACE_LIGHT[ctx.face])


def p_vest(ctx: FaceCtx):
    h, w = ctx.h, ctx.w
    yy, xx = np.mgrid[0:h, 0:w]
    rgb = np.broadcast_to(VEST, (h, w, 3)).copy()
    # damask pattern: diamonds with a dot in the middle
    d = ((xx + yy) % 8 == 0) | ((xx - yy) % 8 == 0)
    rgb[d] = VEST_HI
    dots = ((xx % 8) == 4) & ((yy % 8) == 0)
    rgb[dots] = VEST_HI * 1.15
    rgb = rgb * vgrad(ctx, 1.05, 0.88)[..., None]
    if ctx.p.get("chest") and ctx.face == "north":
        rgb = paint_chest_front(rgb, ctx)
    return tile_of(outline(rgb, 0.80) * FACE_LIGHT[ctx.face])


def paint_chest_front(rgb, ctx):
    """Torso front: deep V-neck of the shirt with skin at the collarbone, buttons of the vest."""
    h, w = rgb.shape[:2]
    out = rgb.copy()
    cx = (w - 1) / 2
    for y in range(h):
        # shirt opening: wide at the top, closing at ~62% of the height
        t = y / (h * 0.62)
        if t >= 1:
            continue
        half = (1 - t) * w * 0.30 + 1.5
        for x in range(w):
            dx = abs(x - cx)
            if dx < half:
                out[y, x] = SHIRT * (0.95 + 0.05 * math.sin(y * 0.9 + x))
                if dx < half - 2.5 and t < 0.55:
                    # skin shows inside the open collar
                    k = 1 - t / 0.55
                    out[y, x] = mix(SHIRT, SKIN, min(1.0, k * 1.6))
                    if abs(dx - (half - 3)) < 0.7:
                        out[y, x] = SHIRT_SH  # shirt edge shadow
            elif dx < half + 1.2:
                out[y, x] = SHIRT_SH * 0.9  # shadow where the vest overlaps
    # collarbone hint
    yb = int(h * 0.12)
    for x in range(int(cx - 5), int(cx + 6)):
        if 0 <= x < w and abs(x - cx) > 1:
            out[yb + (abs(x - int(cx)) // 3), x] = SKIN_SH
    # vest buttons (brass) below the V
    for i in range(3):
        y = int(h * 0.66) + i * 5
        if y + 1 < h:
            out[y:y + 2, int(cx) - 1:int(cx) + 1] = BRASS_HI
    return out


def p_crimson(ctx: FaceCtx):
    h, w = ctx.h, ctx.w
    rgb = np.broadcast_to(CRIMSON, (h, w, 3)).copy()
    along = "v" if ctx.p.get("folds_v") else "u"
    rgb = rgb * folds(ctx, n=ctx.p.get("fold_n", 2.5), amp=0.10, along=along)[..., None]
    rgb = rgb * vgrad(ctx, 1.06, 0.86)[..., None]
    if ctx.face in ("north",) and ctx.p.get("lining"):
        rgb = mix(rgb, CRIMSON_SH, 0.35)
    trims = par(ctx, "trim", {})
    edges = trims.get(ctx.face, trims.get("*", ()))
    for e in edges:
        bw = ctx.p.get("trim_w", 3) if e in ("bottom", "top") else ctx.p.get("trim_side", 2)
        rgb = gold_border(rgb, e, bw, ctx.p.get("vine", False))
    if par(ctx, "emblem") == ctx.face:
        rgb = draw_emblem(rgb)
    if par(ctx, "crest") == ctx.face:
        rgb = draw_crest(rgb)
    return tile_of(outline(rgb, 0.82) * FACE_LIGHT[ctx.face])


def gold_border(rgb, edge, bw, vine):
    h, w = rgb.shape[:2]
    out = rgb.copy()
    bw = min(bw, h // 2 if edge in ("top", "bottom") else w // 2)
    if bw <= 0:
        return out
    if edge == "bottom":
        sl = (slice(h - bw, h), slice(0, w))
    elif edge == "top":
        sl = (slice(0, bw), slice(0, w))
    elif edge == "left":
        sl = (slice(0, h), slice(0, bw))
    else:
        sl = (slice(0, h), slice(w - bw, w))
    out[sl] = GOLD
    # bevel: bright line on the outer side, dark line on the inner side
    if edge == "bottom":
        out[h - bw, :] = GOLD_SH
        out[h - 1, :] = GOLD_HI * 0.95
    elif edge == "top":
        out[bw - 1, :] = GOLD_SH
        out[0, :] = GOLD_HI * 0.95
    elif edge == "left":
        out[:, bw - 1] = GOLD_SH
    else:
        out[:, w - bw] = GOLD_SH
    if vine and edge in ("bottom", "top") and bw >= 5:
        # leaf motif inside the hem
        y0 = h - bw + 1 if edge == "bottom" else 1
        for x in range(0, w, 6):
            for dx, dy in ((0, 1), (1, 0), (1, 2), (2, 1), (3, 1)):
                xx, yy = x + dx, y0 + dy
                if 0 <= xx < w and 0 <= yy < h and yy < y0 + bw - 2:
                    out[yy, xx] = CRIMSON_SH
    if edge in ("bottom", "top") and bw >= 4:
        # a thin second gold line inside the hem, like the art
        yl = h - bw - 2 if edge == "bottom" else bw + 1
        if 0 <= yl < h:
            out[yl, :] = mix(out[yl, :], GOLD_SH, 0.8)
    return out


def _pil_draw(rgb, fn):
    h, w = rgb.shape[:2]
    S = 4
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fn(d, w * S, h * S, S)
    im = im.resize((w, h), Image.LANCZOS)
    a = np.array(im).astype(float)
    al = a[..., 3:4] / 255.0
    return rgb * (1 - al) + a[..., :3] * al


def draw_emblem(rgb):
    """Compass rose with laurel sprigs, gold on crimson (the emblem on the robe's tail)."""
    def fn(d, W, H, S):
        cx, cy = W * 0.5, H * 0.66
        r = min(W, H) * 0.30
        g = tuple(int(v) for v in GOLD) + (255,)
        gd = tuple(int(v) for v in GOLD_SH) + (255,)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=g, width=max(2, S))
        d.ellipse([cx - r * 0.35, cy - r * 0.35, cx + r * 0.35, cy + r * 0.35], outline=g, width=max(2, S // 2))
        for k in range(8):
            a = k * math.pi / 4
            L = r * (1.25 if k % 2 == 0 else 0.8)
            d.line([cx, cy, cx + math.sin(a) * L, cy - math.cos(a) * L], fill=g, width=max(2, S // 2 + 1))
        for k in range(4):
            a = k * math.pi / 2 + math.pi / 4
            px, py = cx + math.sin(a) * r * 0.62, cy - math.cos(a) * r * 0.62
            d.ellipse([px - S, py - S, px + S, py + S], fill=gd)
        # laurel sprig rising above the rose
        for side in (-1, 1):
            for i in range(5):
                y = cy - r * 1.35 - i * r * 0.32
                x = cx + side * (r * 0.12 + i * r * 0.05)
                d.ellipse([x - S * 1.6 + side * S * 1.2, y - S * 0.8, x + S * 1.6 + side * S * 1.2, y + S * 0.8], fill=g)
        d.line([cx, cy - r * 1.2, cx, cy - r * 2.9], fill=g, width=max(2, S // 2))
    return _pil_draw(rgb, fn)


def draw_crest(rgb):
    """Small laurel crown motif (front of the robe tails, like the art)."""
    def fn(d, W, H, S):
        g = tuple(int(v) for v in GOLD) + (235,)
        cx, cy = W * 0.5, H * 0.55
        for side in (-1, 1):
            for i in range(6):
                y = cy - i * S * 2.2
                x = cx + side * (S * 3 + math.sin(i * 0.6) * S * 1.5)
                d.ellipse([x - S * 1.5, y - S * 0.9, x + S * 1.5, y + S * 0.9], fill=g)
        d.line([cx, cy + S * 4, cx, cy - S * 12], fill=g, width=S)
    return _pil_draw(rgb, fn)


def p_gold(ctx: FaceCtx):
    U, V = ctx.grid()
    rgb = mix(GOLD_HI, GOLD_SH, np.clip(V * 0.9 + 0.05, 0, 1))
    rgb = np.broadcast_to(rgb, (ctx.h, ctx.w, 3)).copy()
    if ctx.p.get("disc") and ctx.face in ("north", "south", "east", "west") and min(ctx.w, ctx.h) >= 6:
        rgb = draw_medallion(rgb)
    return tile_of(outline(rgb, 0.72) * FACE_LIGHT[ctx.face])


def draw_medallion(rgb):
    def fn(d, W, H, S):
        g = tuple(int(v) for v in GOLD_SH) + (255,)
        hi = tuple(int(v) for v in GOLD_HI) + (255,)
        r = min(W, H) * 0.42
        cx, cy = W / 2, H / 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=g, width=S)
        for k in range(6):
            a = k * math.pi / 3
            d.line([cx, cy, cx + math.cos(a) * r * 0.8, cy + math.sin(a) * r * 0.8], fill=g, width=max(1, S // 2))
        d.ellipse([cx - S, cy - S, cx + S, cy + S], fill=hi)
    return _pil_draw(rgb, fn)


def p_brass(ctx: FaceCtx):
    U, V = ctx.grid()
    h, w = ctx.h, ctx.w
    rgb = mix(BRASS_HI, BRASS_SH, np.clip(V * 0.85 + 0.08, 0, 1))
    rgb = np.broadcast_to(rgb, (h, w, 3)).copy()
    # polished streak
    streak = np.exp(-((U - 0.32) / 0.08) ** 2)
    rgb = mix(rgb, BRASS_HI * 1.08, np.clip(streak * 0.55, 0, 1))
    seams = ctx.p.get("seams", 0)
    if seams and ctx.face in ("north", "south", "east", "west"):
        for k in range(1, seams + 1):
            y = int(h * k / (seams + 1))
            rgb[y, :] = BRASS_SH * 0.8
            if y + 1 < h:
                rgb[y + 1, :] = BRASS_HI
    if ctx.p.get("rivets") and min(w, h) >= 8:
        for (x, y) in ((2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)):
            rgb[y, x] = BRASS_SH * 0.7
            rgb[y - 1, x - 1] = BRASS_HI * 1.1
    if ctx.p.get("joint"):
        rgb = rgb * 0.62
    return tile_of(outline(rgb, 0.70) * FACE_LIGHT[ctx.face])


def p_steel(ctx: FaceCtx):
    h, w = ctx.h, ctx.w
    U, V = ctx.grid()
    rgb = mix(STEEL_HI, STEEL_SH, np.clip(V * 0.8 + 0.1, 0, 1))
    rgb = np.broadcast_to(rgb, (h, w, 3)).copy()
    if ctx.p.get("gear") and ctx.face in ("north", "south", "east", "west"):
        xx = np.arange(w)
        teeth = (xx // 3) % 2 == 0
        rgb[: max(1, h // 4), teeth] = STEEL_HI
        rgb[: max(1, h // 4), ~teeth] = STEEL_SH * 0.7
        rgb[h - max(1, h // 4):, teeth] = STEEL_HI * 0.9
        rgb[h - max(1, h // 4):, ~teeth] = STEEL_SH * 0.7
    if ctx.face in ("up", "down") and ctx.p.get("gear"):
        cy, cx = (h - 1) / 2, (w - 1) / 2
        yy, xx = np.mgrid[0:h, 0:w]
        rr = np.hypot(yy - cy, xx - cx)
        ang = np.arctan2(yy - cy, xx - cx)
        tooth = (np.sin(ang * 10) > 0) & (rr > min(h, w) * 0.40)
        rgb[tooth] = STEEL_SH * 0.6
    return tile_of(outline(rgb, 0.7) * FACE_LIGHT[ctx.face])


def p_leather(ctx: FaceCtx):
    h, w = ctx.h, ctx.w
    n = smooth_noise(w, h, ctx.rng, 3.0)
    rgb = np.broadcast_to(LEATHER, (h, w, 3)) * (0.9 + 0.2 * n)[..., None]
    rgb = rgb * vgrad(ctx, 1.05, 0.9)[..., None]
    if ctx.p.get("stitch") and min(h, w) >= 4:
        long_u = w >= h
        if long_u:
            for x in range(1, w, 3):
                rgb[1, x] = LEATHER * 1.45
                rgb[h - 2, x] = LEATHER * 1.45
        else:
            for y in range(1, h, 3):
                rgb[y, 1] = LEATHER * 1.45
                rgb[y, w - 2] = LEATHER * 1.45
    if ctx.p.get("bands") and ctx.face in ("north", "south", "east", "west"):
        for f in (0.12, 0.5, 0.88):
            y = int(h * f)
            rgb[max(0, y - 1):y + 2, :] = BRASS
            rgb[max(0, y - 1), :] = BRASS_HI
    return tile_of(outline(rgb, 0.78) * FACE_LIGHT[ctx.face])


def p_boot(ctx: FaceCtx):
    h, w = ctx.h, ctx.w
    U, V = ctx.grid()
    rgb = np.broadcast_to(BOOT, (h, w, 3)).copy()
    # glossy leather: highlight streak on the front
    streak = np.exp(-((U - 0.38) / 0.10) ** 2) * (ctx.face in ("north", "south"))
    rgb = mix(rgb, BOOT_HI, np.clip(streak * 0.6, 0, 1))
    rgb = rgb * vgrad(ctx, 1.06, 0.85)[..., None]
    if par(ctx, "fleur") == ctx.face:
        rgb = draw_fleur(rgb)
    if ctx.p.get("sole") and ctx.face != "up":
        rgb[-2:, :] = LEATHER_SH * 0.6
    return tile_of(outline(rgb, 0.76) * FACE_LIGHT[ctx.face])


def draw_fleur(rgb):
    def fn(d, W, H, S):
        g = tuple(int(v) for v in GOLD) + (255,)
        cx, cy = W / 2, H * 0.45
        d.polygon([(cx, cy - H * 0.32), (cx - W * 0.13, cy), (cx, cy + H * 0.12), (cx + W * 0.13, cy)], fill=g)
        d.ellipse([cx - W * 0.36, cy - H * 0.12, cx - W * 0.10, cy + H * 0.06], fill=g)
        d.ellipse([cx + W * 0.10, cy - H * 0.12, cx + W * 0.36, cy + H * 0.06], fill=g)
        d.rectangle([cx - W * 0.25, cy + H * 0.14, cx + W * 0.25, cy + H * 0.20], fill=g)
        d.polygon([(cx - W * 0.08, cy + H * 0.2), (cx + W * 0.08, cy + H * 0.2), (cx, cy + H * 0.42)], fill=g)
    return _pil_draw(rgb, fn)


def p_trouser(ctx: FaceCtx):
    rgb = np.broadcast_to(TROUSER, (ctx.h, ctx.w, 3)).copy()
    rgb = rgb * folds(ctx, n=1.6, amp=0.12, along="u")[..., None]
    U, V = ctx.grid()
    crease = np.exp(-((U - 0.5) / 0.05) ** 2) * (ctx.face in ("north", "south"))
    rgb = mix(rgb, TROUSER_HI, np.clip(crease * 0.6, 0, 1))
    return tile_of(outline(rgb, 0.8) * FACE_LIGHT[ctx.face])


def p_wood(ctx: FaceCtx):
    h, w = ctx.h, ctx.w
    U, V = ctx.grid()
    grain = np.sin((U if w >= h else V) * 40 + np.sin((V if w >= h else U) * 7) * 2)
    rgb = mix(WOOD, WOOD_SH, np.clip(0.3 + 0.3 * grain, 0, 1))
    return tile_of(outline(rgb, 0.8) * FACE_LIGHT[ctx.face])


def p_canvas(ctx: FaceCtx):
    """Parchment wing canvas covered with Leonardo-style sepia sketches and mirror writing."""
    h, w = ctx.h, ctx.w
    n = smooth_noise(w, h, ctx.rng, 6.0)
    rgb = mix(PARCH, PARCH_SH, np.clip(n * 0.6, 0, 1))
    rgb = np.broadcast_to(rgb, (h, w, 3)).copy()
    rng = ctx.rng
    ink = tuple(int(v) for v in INK)

    def fn(d, W, H, S):
        col = ink + (170,)
        faint = ink + (110,)
        # ribs of the wing (radiating from the spar at the top)
        for i in range(1, 5):
            x = W * i / 5
            d.line([x, 0, x + (i - 2.5) * S * 2, H], fill=col, width=S)
        # little sketches: gears, circles, arcs
        for _ in range(max(1, (W * H) // (S * S * 260))):
            x, y = rng.uniform(0.1, 0.9) * W, rng.uniform(0.15, 0.85) * H
            r = rng.uniform(3, 7) * S
            kind = rng.integers(0, 3)
            if kind == 0:
                d.ellipse([x - r, y - r, x + r, y + r], outline=faint, width=max(1, S // 2))
                for k in range(8):
                    a = k * math.pi / 4
                    d.line([x + math.cos(a) * r, y + math.sin(a) * r, x + math.cos(a) * r * 1.3,
                            y + math.sin(a) * r * 1.3], fill=faint, width=max(1, S // 2))
            elif kind == 1:
                d.arc([x - r * 2, y - r, x + r * 2, y + r], 200, 340, fill=faint, width=max(1, S // 2))
            else:
                d.line([x - r, y, x + r, y - r * 0.6], fill=faint, width=max(1, S // 2))
        # mirror-writing scribble lines
        y = H * 0.12
        while y < H * 0.95:
            x = W * rng.uniform(0.05, 0.2)
            end = W * rng.uniform(0.6, 0.95)
            while x < end:
                L = rng.uniform(2, 6) * S
                d.line([x, y + rng.uniform(-1, 1) * S * 0.4, x + L, y + rng.uniform(-1, 1) * S * 0.4],
                       fill=faint, width=max(1, S // 2))
                x += L + S * 1.5
            y += H * rng.uniform(0.10, 0.16)
    if ctx.face in ("north", "south"):
        rgb = _pil_draw(rgb, fn)
    return tile_of(outline(rgb, 0.85) * FACE_LIGHT[ctx.face])


def p_glow(ctx: FaceCtx):
    h, w = ctx.h, ctx.w
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((yy - (h - 1) / 2) / max(h / 2, 1), (xx - (w - 1) / 2) / max(w / 2, 1))
    rgb = mix(AMBER_HI, AMBER, np.clip(r, 0, 1))
    t = tile_of(rgb, GLOW_ALPHA)
    if min(h, w) >= 4:
        # brass bezel around the core
        t[0, :, :3] = BRASS_SH
        t[-1, :, :3] = BRASS_SH
        t[:, 0, :3] = BRASS_SH
        t[:, -1, :3] = BRASS_SH
        t[0, :, 3] = t[-1, :, 3] = t[:, 0, 3] = t[:, -1, 3] = 255
    return t


PAINTERS = {
    "skin": p_skin, "hair": p_hair, "shirt": p_shirt, "vest": p_vest, "crimson": p_crimson, "gold": p_gold,
    "brass": p_brass, "steel": p_steel, "leather": p_leather, "boot": p_boot, "trouser": p_trouser,
    "wood": p_wood, "canvas": p_canvas, "glow": p_glow,
}


# ------------------------------------------------------------------------------ geometry

def build() -> Model:
    m = Model("geometry.esb.da_vinci")
    m.bone("root", None, (0, 0, 0))

    # ---------------------------------------------------------------- lower body (hips & skirts)
    m.bone("body", "root", (0, 17, 0))
    m.cube("body", (-4.3, 16.25, -2.6), (8.6, 3.0, 5.2), "crimson", fold_n=4, folds_v=False)  # sash
    m.cube("body", (-4.45, 17.25, -2.75), (8.9, 1.25, 5.5), "leather", stitch=True)  # main belt
    m.cube("body", (-4.6, 15.5, -2.85), (9.2, 0.75, 5.7), "leather", rotation=(0, 0, 7), pivot=(0, 16, 0))  # low belt
    m.cube("body", (0.75, 16.95, -3.0), (2.0, 1.75, 0.5), "gold", rivets=True)  # buckle
    m.cube("body", (-3.25, 12.0, -3.0), (2.0, 4.5, 0.5), "crimson", rotation=(0, 0, 8), pivot=(-2.25, 16.5, -2.75),
           trim={"north": ("bottom",)}, trim_w=2)  # sash tail hanging in front
    m.cube("body", (-1.75, 12.75, -3.05), (1.5, 3.75, 0.5), "crimson", rotation=(0, 0, -6), pivot=(-1, 16.5, -2.8))

    # white shirt tails (long coat under the robe): front panels and back panel
    m.bone("coat_front_l", "body", (3.3, 17, -2.6))
    m.cube("coat_front_l", (3.0, 6.0, -2.95), (1.75, 11.25, 0.5), "shirt", fold_n=1.0, rotation=(0, 0, 5), pivot=(3.9, 17, -2.7))
    m.bone("coat_back", "body", (0, 17, 2.5))
    m.cube("coat_back", (-4.4, 5.0, 2.25), (8.8, 12.25, 0.5), "shirt", fold_n=2.5)
    # crimson robe sides (long coat silhouette)
    m.bone("robe_side_l", "body", (4.6, 17, 0))
    m.cube("robe_side_l", (4.25, 5.0, -1.5), (0.5, 12.25, 4.25), "crimson", fold_n=2,
           trim={"east": ("bottom",), "west": ("bottom",)}, trim_w=3)
    # scroll tube at the left hip
    m.bone("tube", "body", (3.6, 16.75, -2.6))
    m.cube("tube", (2.9, 9.25, -3.6), (1.5, 7.0, 1.5), "leather", bands=True, rotation=(0, 0, -16), pivot=(3.65, 16.5, -2.85))
    m.cube("tube", (2.8, 15.5, -3.7), (1.75, 1.0, 1.75), "brass", rotation=(0, 0, -16), pivot=(3.65, 16.5, -2.85))
    m.cube("tube", (2.8, 8.75, -3.7), (1.75, 0.75, 1.75), "brass", rotation=(0, 0, -16), pivot=(3.65, 16.5, -2.85))

    # ---------------------------------------------------------------- torso
    m.bone("torso", "body", (0, 18, 0))
    m.cube("torso", (-4, 18.25, -2.25), (8, 10.75, 4.5), "vest", chest=True)
    # open collar of the shirt
    m.cube("torso", (0.5, 28.25, -2.75), (2.5, 2.25, 0.5), "shirt", rotation=(-12, -28, -10), pivot=(0.75, 28.5, -2.5))
    m.cube("torso", (-3.0, 28.25, -2.75), (2.5, 2.25, 0.5), "shirt", rotation=(-12, 28, 10), pivot=(-0.75, 28.5, -2.5))
    m.cube("torso", (-2.5, 28.0, -1.5), (5.0, 1.5, 3.5), "shirt")  # shirt yoke around the neck
    # crossing leather straps with medallions
    m.cube("torso", (-0.5, 17.5, -2.6), (1.0, 13.5, 0.35), "leather", stitch=True, rotation=(0, 0, -33), pivot=(0, 23.5, -2.45))
    m.cube("torso", (-0.5, 18.5, -2.7), (1.0, 12.5, 0.35), "leather", stitch=True, rotation=(0, 0, 30), pivot=(0, 23.5, -2.55))
    m.cube("torso", (2.0, 25.75, -3.05), (2.0, 2.0, 0.4), "gold", disc=True)
    m.cube("torso", (-4.0, 25.75, -3.05), (2.0, 2.0, 0.4), "gold", disc=True)
    # crimson mantle front panels (lapels) with gold trim on the inner edge
    m.cube("torso", (2.6, 18.25, -2.85), (1.75, 10.5, 0.5), "crimson", folds_v=False, fold_n=1,
           trim={"north": ("left",)}, trim_w=2)
    m.cube("torso", (-4.35, 18.25, -2.85), (1.75, 10.5, 0.5), "crimson", folds_v=False, fold_n=1,
           trim={"north": ("right",)}, trim_w=2)
    # shoulder mantle (left / right)
    m.bone("mantle_l", "torso", (4.25, 28.5, 0))
    m.cube("mantle_l", (2.25, 27.5, -2.85), (5.25, 2.0, 5.7), "crimson", rotation=(0, 0, -14), pivot=(3, 28.5, 0),
           trim={"north": ("bottom",), "south": ("bottom",), "west": ("bottom",)}, trim_w=2)
    m.cube("mantle_l", (6.6, 23.25, -2.8), (0.6, 4.5, 5.6), "crimson", rotation=(0, 0, -8), pivot=(6.9, 27.5, 0),
           trim={"west": ("bottom",), "east": ("bottom",)}, trim_w=3, vine=True)
    m.mirror(names={"mantle_l"})

    # back robe: upper cape and two long tails
    m.bone("cape", "torso", (0, 29, 2.4))
    m.cube("cape", (-4.75, 17.5, 2.25), (9.5, 11.75, 0.6), "crimson", fold_n=3)
    m.bone("cape_tail_l", "body", (2.4, 17.25, 2.9))
    m.cube("cape_tail_l", (0.0, 1.5, 2.85), (4.9, 15.75, 0.6), "crimson", fold_n=1.6,
           trim={"south": ("bottom", "right"), "north": ("bottom",), "west": ("bottom",)}, trim_w=6, vine=True,
           emblem="south", crest="north", lining=True)
    m.mirror(names={"cape_tail_l"})
    # the right tail has no emblem: overwrite its params
    for c in m.bones["cape_tail_r"].cubes:
        c.params = dict(c.params, emblem=None, crest=None)
    m.mirror(names={"coat_front_l", "robe_side_l"})

    # ---------------------------------------------------------------- head & hair
    m.bone("head", "torso", (0, 29, 0))
    m.cube("head", (-1.5, 27.75, -1.5), (3.0, 2.25, 3.0), "skin")  # neck
    m.cube("head", (-3.5, 29.5, -3.5), (7, 7, 7), "skin", face=True)
    m.cube("head", (3.45, 31.25, -1.5), (0.45, 1.75, 1.0), "skin")  # ears
    m.cube("head", (-3.9, 31.25, -1.5), (0.45, 1.75, 1.0), "skin")
    m.cube("head", (-3.75, 34.25, -3.75), (7.5, 3.0, 7.5), "hair", shine=True)  # cap (above the brows)
    m.cube("head", (-3.9, 26.75, 1.5), (7.8, 7.5, 2.5), "hair", shine=True, tips=True)  # back mass
    m.cube("head", (3.15, 27.5, -0.5), (1.25, 7.0, 3.0), "hair", tips=True)  # side hair behind the ears
    m.cube("head", (-4.4, 27.5, -0.5), (1.25, 7.0, 3.0), "hair", tips=True)
    m.cube("head", (3.0, 32.75, -3.0), (0.9, 1.75, 2.75), "hair")  # temples
    m.cube("head", (-3.9, 32.75, -3.0), (0.9, 1.75, 2.75), "hair")
    # swept-back fringe: a parting toward his left, one loose strand falls over his right brow
    m.cube("head", (-3.6, 32.75, -3.95), (1.0, 3.75, 0.6), "hair", tips=True, rotation=(0, 0, 10), pivot=(-3.1, 36.5, -3.65))
    m.cube("head", (-2.4, 34.0, -3.95), (2.25, 2.25, 0.6), "hair", rotation=(0, 0, -24), pivot=(-1.3, 36.25, -3.65))
    m.cube("head", (0.4, 34.25, -3.95), (2.0, 2.0, 0.6), "hair", rotation=(0, 0, 18), pivot=(1.4, 36.25, -3.65))
    m.cube("head", (2.4, 33.75, -3.95), (1.25, 2.5, 0.6), "hair", rotation=(0, 0, -8), pivot=(3.0, 36.25, -3.65))
    # volume swept back over the top and waves at the ends of the side hair
    m.cube("head", (-3.5, 36.75, -3.25), (3.25, 0.75, 6.75), "hair", rotation=(8, 0, 9), pivot=(-1.75, 37, 0))
    m.cube("head", (0.25, 36.75, -3.25), (3.25, 0.75, 6.75), "hair", rotation=(8, 0, -7), pivot=(1.75, 37, 0))
    m.cube("head", (3.4, 25.25, -0.25), (1.25, 2.5, 3.0), "hair", tips=True, rotation=(0, 0, -10), pivot=(3.9, 27.5, 1))
    m.cube("head", (-4.65, 25.25, -0.25), (1.25, 2.5, 3.0), "hair", tips=True, rotation=(0, 0, 10), pivot=(-3.9, 27.5, 1))
    m.cube("head", (-4.0, 25.25, 1.75), (8.0, 2.0, 2.0), "hair", tips=True, rotation=(-8, 0, 0), pivot=(0, 27, 2.75))
    # half-up ponytail
    m.bone("hair_tail", "head", (0, 32.5, 3.75))
    m.cube("hair_tail", (-0.75, 31.75, 3.75), (1.5, 1.25, 1.25), "leather")  # tie
    m.cube("hair_tail", (-1.25, 24.0, 3.75), (2.5, 8.25, 1.5), "hair", tips=True)
    m.cube("hair_tail", (-1.0, 21.75, 3.5), (2.0, 2.75, 1.25), "hair", tips=True, rotation=(10, 0, 0), pivot=(0, 24, 4))

    # ---------------------------------------------------------------- right arm (holds the compass)
    m.bone("arm_r", "torso", (-5.25, 28.25, 0))
    m.cube("arm_r", (-7.0, 22.5, -1.9), (3.5, 6.75, 3.8), "shirt", folds_v=True, fold_n=1.5)
    m.bone("forearm_r", "arm_r", (-5.25, 22.75, 0))
    m.cube("forearm_r", (-7.4, 18.75, -2.15), (4.25, 4.75, 4.3), "shirt", folds_v=True, fold_n=1.2)  # full sleeve
    m.cube("forearm_r", (-7.0, 17.75, -1.85), (3.5, 1.25, 3.7), "shirt", band=True)  # cuff
    m.bone("hand_r", "forearm_r", (-5.25, 17.75, 0))
    m.cube("hand_r", (-6.4, 15.0, -1.25), (2.35, 3.0, 2.5), "skin")
    m.bone("compass", "hand_r", (-5.25, 15.75, -0.25))
    m.cube("compass", (-6.05, 15.25, -1.0), (1.6, 1.75, 1.5), "gold", rivets=True)  # hinge head
    m.cube("compass", (-5.6, 7.0, -0.55), (0.6, 8.5, 0.6), "gold", rotation=(0, 0, 7), pivot=(-5.3, 15.5, -0.25))
    m.cube("compass", (-5.0, 7.0, -0.55), (0.6, 8.5, 0.6), "gold", rotation=(0, 0, -7), pivot=(-4.7, 15.5, -0.25))
    m.cube("compass", (-5.9, 13.0, -0.4), (1.9, 0.5, 0.3), "gold")  # arc brace
    m.locator("compass", "loc_compass_tip", (-5.25, 7.0, -0.25))

    # ---------------------------------------------------------------- left arm: clockwork gauntlet
    m.bone("arm_l", "torso", (5.25, 28.25, 0))
    m.cube("arm_l", (3.5, 22.5, -1.9), (3.5, 6.75, 3.8), "shirt", folds_v=True, fold_n=1.5)
    m.bone("gauntlet_l", "arm_l", (5.25, 22.75, 0))
    m.cube("gauntlet_l", (2.85, 21.0, -2.4), (4.8, 1.75, 4.8), "steel", gear=True)  # elbow gear ring
    m.cube("gauntlet_l", (3.15, 17.25, -2.1), (4.2, 4.0, 4.2), "brass", seams=2, rivets=True)  # vambrace
    m.cube("gauntlet_l", (2.9, 18.0, -1.6), (0.75, 2.75, 3.2), "brass", rivets=True)  # inner plate
    m.cube("gauntlet_l", (6.85, 17.75, -1.4), (0.75, 3.0, 2.8), "brass", rivets=True)  # outer plate
    m.cube("gauntlet_l", (4.4, 18.25, -2.6), (1.75, 1.75, 0.5), "glow")  # amber core
    m.cube("gauntlet_l", (3.0, 16.25, -2.2), (4.5, 1.0, 4.4), "crimson")  # wrist strap
    m.cube("gauntlet_l", (7.35, 15.9, -1.0), (0.5, 2.0, 2.0), "gold", disc=True)  # wrist medallion
    m.locator("gauntlet_l", "loc_core", (5.25, 19.1, -2.65))
    m.bone("ghand_l", "gauntlet_l", (5.25, 16.25, 0))
    m.cube("ghand_l", (3.75, 13.0, -1.75), (3.0, 3.25, 3.5), "brass", rivets=True)  # palm
    m.cube("ghand_l", (3.6, 14.25, -1.85), (3.3, 0.6, 3.7), "steel")  # knuckle bar
    for i, z in enumerate((-1.7, -0.825, 0.05, 0.925)):
        b = f"finger_l_{i + 1}"
        m.bone(b, "ghand_l", (5.25, 13.0, z + 0.4))
        ln = (2.9, 3.3, 3.1, 2.6)[i]
        m.cube(b, (4.8, 13.0 - ln * 0.5, z), (0.9, ln * 0.5, 0.8), "brass")
        m.cube(b, (4.85, 13.0 - ln * 0.5 - 0.3, z + 0.05), (0.8, 0.3, 0.7), "brass", joint=True)
        m.cube(b, (4.8, 13.0 - ln - 0.3, z), (0.9, ln * 0.5, 0.8), "brass")
    m.bone("thumb_l", "ghand_l", (5.0, 15.25, -1.75))
    m.cube("thumb_l", (4.55, 12.75, -2.65), (0.9, 2.75, 0.9), "brass", rotation=(28, 0, 0), pivot=(5.0, 15.25, -1.75))
    m.locator("ghand_l", "loc_palm", (5.25, 11.5, -0.4))

    # ---------------------------------------------------------------- legs & boots
    m.bone("leg_l", "root", (2.0, 17, 0))
    m.cube("leg_l", (0.3, 9.0, -1.7), (3.4, 8.5, 3.4), "trouser")
    m.bone("shin_l", "leg_l", (2.0, 9.0, 0))
    m.cube("shin_l", (0.15, 2.5, -1.85), (3.7, 6.75, 3.7), "boot", fleur="north")
    m.cube("shin_l", (-0.15, 8.0, -2.15), (4.3, 2.5, 4.3), "boot", fleur="west")  # folded cuff
    m.cube("shin_l", (1.25, 8.75, -2.5), (1.5, 1.5, 0.5), "gold", rotation=(0, 0, 45), pivot=(2.0, 9.5, -2.25))
    m.bone("foot_l", "shin_l", (2.0, 2.5, -0.25))
    m.cube("foot_l", (0.15, 0.0, -4.25), (3.7, 2.75, 6.0), "boot", sole=True)
    m.cube("foot_l", (0.55, 0.0, -4.9), (2.9, 1.75, 0.75), "boot", sole=True)  # toe cap
    m.cube("foot_l", (0.65, 1.75, -3.6), (2.7, 1.0, 0.5), "gold")  # instep ornament
    m.mirror(names={"leg_l", "shin_l", "foot_l"})

    # ---------------------------------------------------------------- ornithopter wings (phase 2)
    m.bone("wing_l", "torso", (2.0, 26.5, 3.2))
    m.cube("wing_l", (0.75, 25.25, 2.75), (2.5, 2.5, 1.5), "brass", rivets=True)  # back mount
    m.cube("wing_l", (2.0, 26.0, 3.0), (9.0, 1.0, 1.0), "wood")
    m.cube("wing_l", (2.25, 18.0, 3.3), (8.75, 8.0, 0.25), "canvas")
    m.bone("wing_l_mid", "wing_l", (11.0, 26.5, 3.5))
    m.cube("wing_l_mid", (11.0, 26.05, 3.05), (8.0, 0.9, 0.9), "wood")
    m.cube("wing_l_mid", (11.0, 20.0, 3.3), (8.0, 6.0, 0.25), "canvas")
    m.bone("wing_l_tip", "wing_l_mid", (19.0, 26.5, 3.5))
    m.cube("wing_l_tip", (19.0, 26.1, 3.1), (6.5, 0.8, 0.8), "wood")
    m.cube("wing_l_tip", (19.0, 22.75, 3.3), (6.0, 3.25, 0.25), "canvas")
    m.cube("wing_l_tip", (24.9, 21.0, 3.15), (0.6, 5.5, 0.6), "wood", rotation=(0, 0, 20), pivot=(25.2, 26.5, 3.45))
    m.mirror(names={"wing_l", "wing_l_mid", "wing_l_tip"})

    # locators used by the scripts / particles
    m.locator("head", "loc_head", (0, 33, -3.6))
    m.locator("body", "loc_chest", (0, 22, -2.6))
    m.locator("root", "loc_ground", (0, 0.25, 0))
    return m


def main():
    m = build()
    used = m.pack(TEX_W, pad=1, ppu=PPU)
    h = 1
    while h < used:
        h *= 2
    img = m.paint(TEX_W, h, PAINTERS, seed=7)
    os.makedirs(os.path.join(RP, "models", "entity"), exist_ok=True)
    os.makedirs(os.path.join(RP, "textures", "entity"), exist_ok=True)
    geo = m.to_json(TEX_W, h, 4, 3.5, [0, 1.6, 0])
    with open(os.path.join(RP, "models", "entity", "da_vinci.geo.json"), "w") as f:
        json.dump(geo, f, indent=1)
    Image.fromarray(img, "RGBA").save(os.path.join(RP, "textures", "entity", "da_vinci.png"))
    nb, nc = m.stats()
    print(f"da_vinci: {nb} bones, {nc} cubes, texture {TEX_W}x{h} (used {used} rows)")


if __name__ == "__main__":
    main()
