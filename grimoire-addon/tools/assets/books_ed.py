"""Codex of the Four Primordial Dragons -- the Elemental Dragon Grimoire (worker M3, g = ed).

Delivers (see briefs M_books / M_split):
  * attachable for item grimoire:elemental_dragon  (geometry.grimoire.book_ed, its own render
    controller controller.render.grimoire.book_ed, animations + an animation controller)
  * actor book_ed_vision  -- selection vision, kinds 0-5 = spell index, states 0 hidden / 1 show (1.2 s)
  * actor book_ed_charge  -- charge construct, kinds 0-5, states 0 hidden / 1 form (1.5 s, holds) /
                             2 loop / 3 release (0.5 s) / 4 cancel (0.4 s)
  * sounds grimoire.book_ed_select / _charge / _release / _deny (+ six lineage calls used by the actors)
  * particles grimoire:book_ed_mote / grimoire:book_ed_burst (+ leaf / ember / drop / feather / grit)
  * inventory icon textures/items/grimoire_elemental_dragon.png

The book: overlapping antique-bronze scale rows that breathe, aged-gold corners, an articulated
vertebral spine (with a tiny skull cap and tail tip), four different dragon-claw clasps
(Nature: blunt mossy toes; Heat: hooked basalt talons with ember seams; Water & Ice: webbed
sapphire claw; Air: slender raptor foot with a sickle claw and a feather), a central draconic
seal ringed by four distinct skull emblems (sauropod, carnotaur, spinosaur, microraptor) and
bone-ivory pages with sepia anatomical drawings.

Bind pose of every actor is its fully-formed pose; one-shot animations move away from it, so state
changes never snap.  Lineage order everywhere: 0 Nature, 1 Heat, 2 Water & Ice, 3 Air.
"""
import math
import os

import numpy as np

from kit import glyphs, tex
from kit import synth as sy
from kit.anim import LIFE, Anim, M, S, animations_file
from kit.geo import Mat, Model, ring
from kit.pack import _write
from kit.parts import feather_wing, flutter, wave
from kit.render import render
from kit.tex import _hash, fbm, grain, mix, rgb, tile

from .a_fx_common import particles

# =====================================================================================
# ATTACHABLE PLACEMENT -- every hand offset lives here (bb space: +X = the holder's right, +Y up,
# -Z = the holder's forward; units 1/16 block; degrees).  The root bone is bound with
# q.item_slot_to_bone_name(c.item_slot); its space is the player model's space (right hand at about
# (6, 12..15, 1)).  This is deliberately the SAME frame and the same numbers as the Divine Word book
# (tools/assets/books_dw.py, worker M1) so all three Grimoires sit in the same place and are tuned the
# same way after an in-game look.  The book is modelled upright, centred on its own origin, cover
# facing -Z, spine on +X, 20 x 14 x 5 units; the scales make it ~8% larger than the Divine Word book
# (40 x 29 x 9 cm vs 38 x 28 x 8 cm).
#   rot  : ry 180 turns the cover (and, when open, the pages) toward the caster; rx tips it up.
#   turn : extra spin about the book's own vertical axis; lift: hover offset in the book's own frame.
# The open-while-using motion (rise 10 units = ~4 px, tilt 28 deg, spread re-centred) is in build_book_anims.
HAND_PIVOT = (0.0, 0.0, 0.0)
BOOK_CENTER = (0.0, 0.0, 0.0)
FIRST = dict(pos=(-2.0, 27.0, -6.0), rot=(20.0, 196.0, -6.0), turn=0.0, lift=(0.0, 0.0, 0.0), scale=0.31)
THIRD = dict(pos=(9.5, 19.0, -5.5), rot=(18.0, 180.0, -8.0), turn=0.0, lift=(0.0, 0.0, 0.0), scale=0.405)
# Charge construct / vision face: their front (-Z, the readable page side) points along the actor
# yaw.  The presenter should spawn them with the yaw that faces the player (player yaw + 180).
FACE_YAW = 0.0
# =====================================================================================

# v.open: 0 -> 1 while Use is held (fully open after ~8 ticks), back to 0 within ~1/3 s after release.
# The same four lines drive the Divine Word book (books_dw.py), which opened correctly on an iPhone.
OPEN_PRE_ANIMATION = [
    "v.held = q.main_hand_item_use_duration > 0.0 ? math.max(q.main_hand_item_max_duration - q.main_hand_item_use_duration, 0.0) : 0.0;",
    "v.target = q.main_hand_item_use_duration > 0.0 ? math.clamp(v.held / 8.0, 0.15, 1.0) : 0.0;",
    "v.open = math.max(v.target, math.clamp((v.open ?? 0.0) - q.delta_time * 3.0, 0.0, 1.0));",
    "v.open = v.open * v.open * (3.0 - 2.0 * v.open);",
]
# while open the book rises toward the charge construct and tilts its pages to the reader (as books_dw.py)
FP_OPEN_POS = (-1.5, 2.5, -1.0)
FP_OPEN_ROT = (10.0, -8.0, 6.0)
TP_OPEN_POS = (-2.5, 4.0, -2.5)
TP_OPEN_ROT = (18.0, 0.0, 8.0)

BRONZE, BRONZE_HI, BRONZE_LO = "#8a6a3a", "#d0a462", "#3c2a12"
GOLD, GOLD_HI, GOLD_LO = "#b8913e", "#f2d58a", "#5e4418"
IVORY, IVORY_SH = "#e9dfc6", "#b8a985"
INK = "#6b4526"
MOSS, BASALT, EMBER, SAPPHIRE, ICE, SILVER = "#5f7d3a", "#34302d", "#ff7a1e", "#2f6fd6", "#e8f6ff", "#a9c3d9"
LIN = ("n", "h", "w", "a")
EL = {  # glow colour, deep colour, bone tint
    "n": ("#9be35f", "#3f6a2a", "#e4ecd0"),
    "h": ("#ff8a2a", "#7a2a10", "#f2dcc2"),
    "w": ("#7fd6ff", "#1f4f9a", "#d8eaf4"),
    "a": ("#b9dcff", "#7f9fbf", "#eef2f8"),
}

# ------------------------------------------------------------------ skull bitmaps (snout left)
SKULL_ART = {
    "n": ["    ####    ",
          "   ## ####  ",
          "  ##   #####",
          " ######## ##",
          "############",
          "#.#.#.##### ",
          " ########## "],
    "h": ["  ##    ##  ",
          "   ##  ##   ",
          "  ######### ",
          " ### ## ####",
          "############",
          "####...#####",
          "# # ########",
          " ########## "],
    "w": ["        ##  ",
          "       #### ",
          "      ### ##",
          "   #########",
          "############",
          "#.#.#.#.####",
          "  ######### "],
    "a": ["      # #   ",
          "     # # #  ",
          "     #####  ",
          "    ##  ### ",
          "#######  ## ",
          "  ######### ",
          "    ######  "],
}

# ------------------------------------------------------------------ anatomical drawings (u right, v down)
def _ribs(x0, x1, n, y0, y1):
    return [[(x0 + (x1 - x0) * i / max(1, n - 1), y0), (x0 + (x1 - x0) * i / max(1, n - 1) + 0.01, y1)] for i in range(n)]


SCENES = {
    "n": dict(lines=[[(0.30, 0.52), (0.45, 0.45), (0.62, 0.47), (0.78, 0.55), (0.90, 0.64), (0.98, 0.70)],
                     [(0.32, 0.50), (0.26, 0.33), (0.20, 0.18), (0.13, 0.10)],
                     [(0.13, 0.10), (0.05, 0.12), (0.07, 0.17), (0.15, 0.15)],
                     [(0.36, 0.55), (0.35, 0.90)], [(0.41, 0.52), (0.42, 0.90)],
                     [(0.62, 0.52), (0.61, 0.90)], [(0.68, 0.56), (0.69, 0.90)],
                     [(0.36, 0.63), (0.50, 0.68), (0.64, 0.62)], [(0.02, 0.94), (0.98, 0.94)]]
              + _ribs(0.42, 0.60, 5, 0.47, 0.66), circles=[(0.84, 0.22, 0.07), (0.84, 0.22, 0.03)]),
    "h": dict(lines=[[(0.15, 0.55), (0.20, 0.30), (0.45, 0.22), (0.70, 0.25), (0.85, 0.40), (0.85, 0.60),
                      (0.60, 0.66), (0.30, 0.68), (0.15, 0.55)],
                     [(0.62, 0.24), (0.72, 0.06)], [(0.52, 0.23), (0.58, 0.06)],
                     [(0.18, 0.62), (0.40, 0.82), (0.80, 0.74)], [(0.36, 0.40), (0.48, 0.52)],
                     [(0.10, 0.93), (0.90, 0.93)], [(0.10, 0.90), (0.10, 0.96)], [(0.50, 0.90), (0.50, 0.96)],
                     [(0.90, 0.90), (0.90, 0.96)]] + _ribs(0.24, 0.56, 6, 0.66, 0.72),
              circles=[(0.64, 0.38, 0.07), (0.30, 0.46, 0.05)]),
    "w": dict(lines=[[(0.10, 0.60), (0.30, 0.62), (0.60, 0.60), (0.80, 0.56), (0.97, 0.50)],
                     [(0.10, 0.60), (0.01, 0.64)], [(0.30, 0.55), (0.40, 0.22), (0.50, 0.14), (0.60, 0.24), (0.68, 0.52)],
                     [(0.80, 0.56), (0.86, 0.40), (0.94, 0.46), (0.97, 0.50)],
                     [(0.36, 0.62), (0.35, 0.74)], [(0.60, 0.60), (0.62, 0.74)],
                     [(0.02, 0.84), (0.12, 0.81), (0.22, 0.84), (0.32, 0.81), (0.42, 0.84), (0.52, 0.81), (0.62, 0.84),
                      (0.72, 0.81), (0.82, 0.84), (0.92, 0.81)],
                     [(0.05, 0.92), (0.15, 0.89), (0.25, 0.92), (0.35, 0.89), (0.45, 0.92), (0.55, 0.89), (0.65, 0.92)]]
              + _ribs(0.34, 0.64, 8, 0.24, 0.58), circles=[(0.07, 0.58, 0.02)]),
    "a": dict(lines=[[(0.50, 0.50), (0.35, 0.33), (0.15, 0.28)], [(0.50, 0.50), (0.70, 0.50), (0.95, 0.56)],
                     [(0.50, 0.50), (0.42, 0.42), (0.38, 0.40)], [(0.62, 0.52), (0.60, 0.72), (0.66, 0.88)],
                     [(0.38, 0.40), (0.30, 0.36)]]
              + [[(0.35 - 0.04 * i, 0.33 - 0.01 * i), (0.36 - 0.02 * i, 0.58 + 0.02 * i)] for i in range(5)]
              + [[(0.62 + 0.03 * i, 0.70 + 0.03 * i), (0.78 + 0.03 * i, 0.74 + 0.04 * i)] for i in range(4)]
              + [[(0.75 + 0.05 * i, 0.52 + 0.01 * i), (0.80 + 0.05 * i, 0.66)] for i in range(4)],
              circles=[(0.33, 0.37, 0.03)]),
}


def _stroke_dist(ctx, scene):
    pxx = ctx.U * ctx.w
    pyy = ctx.V * ctx.h
    dist = np.full((ctx.h, ctx.w), 99.0)
    for line in scene.get("lines", []):
        for (u0, v0), (u1, v1) in zip(line, line[1:]):
            ax, ay, bx, by = u0 * ctx.w, v0 * ctx.h, u1 * ctx.w, v1 * ctx.h
            dx, dy = bx - ax, by - ay
            L2 = dx * dx + dy * dy + 1e-9
            tt = np.clip(((pxx - ax) * dx + (pyy - ay) * dy) / L2, 0, 1)
            dist = np.minimum(dist, np.hypot(pxx - (ax + tt * dx), pyy - (ay + tt * dy)))
    for (cu, cv, r) in scene.get("circles", []):
        rr = r * min(ctx.w, ctx.h)
        dist = np.minimum(dist, np.abs(np.hypot(pxx - cu * ctx.w, pyy - cv * ctx.h) - rr))
    return dist


def _stroke_mask(ctx, scene, width=0.6):
    pxx = ctx.U * ctx.w
    pyy = ctx.V * ctx.h
    on = np.zeros((ctx.h, ctx.w), dtype=bool)
    for line in scene.get("lines", []):
        for (u0, v0), (u1, v1) in zip(line, line[1:]):
            ax, ay, bx, by = u0 * ctx.w, v0 * ctx.h, u1 * ctx.w, v1 * ctx.h
            dx, dy = bx - ax, by - ay
            L2 = dx * dx + dy * dy + 1e-9
            tt = np.clip(((pxx - ax) * dx + (pyy - ay) * dy) / L2, 0, 1)
            d = np.hypot(pxx - (ax + tt * dx), pyy - (ay + tt * dy))
            on |= d < width
    for (cu, cv, r) in scene.get("circles", []):
        rr = r * min(ctx.w, ctx.h)
        on |= np.abs(np.hypot(pxx - cu * ctx.w, pyy - cv * ctx.h) - rr) < width
    return on


def page_art(lines_of, key, glyph_rows=2):
    """Bone-ivory page: stains, ruled glyph lines and sepia anatomical drawings stacked in bands."""
    ki, ks, kk = rgb(IVORY), rgb("#c9b48a"), rgb(INK)

    def fn(ctx):
        ix, iy = tex.px(ctx)
        n = fbm(ix / 6.0 + ctx.variant * 9, iy / 6.0, 301)
        t = tile(ctx, IVORY)
        vig = np.clip(np.maximum(np.abs(ctx.U - 0.5), np.abs(ctx.V - 0.5)) * 2 - 0.7, 0, 1)
        t[..., :3] = mix(ki, ks, np.clip(n * 0.55 + vig * 0.9, 0, 1)[..., None])
        nb = len(lines_of)
        on = np.zeros((ctx.h, ctx.w), dtype=bool)
        ink = np.zeros((ctx.h, ctx.w))
        for bi, sc in enumerate(lines_of):
            v0, v1 = bi / nb, (bi + 1) / nb
            band = (ctx.V >= v0) & (ctx.V < v1)

            class Sub:
                pass
            sub = Sub()
            sub.w, sub.h = ctx.w, ctx.h
            sub.V = (ctx.V - v0) / (v1 - v0) * 1.15 - 0.05
            sub.U = (ctx.U - 0.08) / 0.84
            d = _stroke_dist(sub, SCENES[sc])
            ink = np.maximum(ink, np.where(band, np.clip(1.25 - d / 0.75, 0, 1), 0))
            on |= band & (d < 0.6)
        # draconic text rows (tiny 1px dashes) under each drawing
        dash = (_hash(ix // 2, iy // 3, 77 + ctx.variant) > 0.45) & (iy % 3 == 1) & (ix % 2 == 0)
        rows = np.zeros_like(on)
        for bi in range(nb):
            y1 = int((bi + 1) / nb * ctx.h)
            for r in range(glyph_rows):
                yy = y1 - 2 - r * 3
                rows |= (iy == yy) & (ix > ctx.w * 0.12) & (ix < ctx.w * 0.88)
        rows &= dash | (_hash(ix, iy, 5) > 0.6)
        t[..., :3] = mix(t[..., :3], kk, (ink * 0.92)[..., None])
        t[..., :3] = np.where((rows & ~on)[..., None], mix(kk, ki, 0.5), t[..., :3])
        return grain(ctx, t, 0.03)
    return Mat(fn, f"edpage{key}", directional=True)


def fossil_slab(sc, glow_col, key):
    """Stone slab face with an embedded glowing fossil skeleton of a lineage."""
    kb, kd, kg, kv = rgb("#9a8a72"), rgb("#5f5446"), rgb(glow_col), rgb("#efe6cf")

    def fn(ctx):
        ix, iy = tex.px(ctx)
        n = fbm(ix / 4.0 + ctx.variant * 3, iy / 4.0, 411)
        t = tile(ctx, "#9a8a72")
        t[..., :3] = mix(kd, kb, np.clip(n * 1.4 - 0.1, 0, 1)[..., None])
        strata = (np.sin(iy * 0.9 + n * 5) > 0.92)
        t[..., :3] = np.where(strata[..., None], kd * 0.85, t[..., :3])

        class Sub:
            pass
        sub = Sub()
        sub.w, sub.h, sub.U, sub.V = ctx.w, ctx.h, (ctx.U - 0.06) / 0.88, (ctx.V - 0.06) / 0.88
        core = _stroke_mask(sub, SCENES[sc], 0.7)
        halo = _stroke_mask(sub, SCENES[sc], 1.5) & ~core
        t[..., :3] = np.where(halo[..., None], mix(kd, kg, 0.55), t[..., :3])
        t[..., 4] = np.where(halo, 0.55, 0.0)
        t[..., :3] = np.where(core[..., None], kv, t[..., :3])
        t[..., 4] = np.where(core, 0.85, t[..., 4])
        return tex.edge(ctx, grain(ctx, t, 0.05), 0.2)
    return Mat(fn, f"edslab{key}{sc}{glow_col}", directional=True)


def scale_row(n=6, key="srow", base=BRONZE, dark=BRONZE_LO, light=BRONZE_HI):
    """One row of overlapping antique-bronze scales, scalloped (cut-out) lower edge."""
    kb, kd, kl = rgb(base), rgb(dark), rgb(light)

    def fn(ctx):
        u = ctx.U * n + (0.5 if ctx.variant % 2 else 0.0)
        cell = np.floor(u)
        lx = (u - cell) * 2 - 1
        v = ctx.V
        bottom = 0.5 + 0.48 * np.sqrt(np.clip(1 - lx ** 2, 0, 1))
        inside = v <= bottom
        hl = np.clip(1 - np.abs(lx) * 1.2, 0, 1) * np.clip(1.05 - v * 1.2, 0, 1)
        t = tile(ctx, base)
        t[..., :3] = mix(kb * 0.82, kl, (hl * 0.85)[..., None])
        ridge = (np.abs(lx) < 0.1) & (v > 0.15)
        t[..., :3] = np.where(ridge[..., None], np.clip(t[..., :3] * 1.12, 0, 1), t[..., :3])
        rim = (bottom - v) < 0.1
        t[..., :3] = np.where(rim[..., None], kd, t[..., :3])
        verd = _hash(cell.astype(int), np.full_like(cell, ctx.variant).astype(int), 71)
        t[..., :3] *= (0.85 + 0.3 * verd)[..., None]
        patina = (_hash((u * 6).astype(int), (v * 8).astype(int), 73 + ctx.variant) > 0.93) & ~rim
        t[..., :3] = np.where(patina[..., None], rgb("#6f8a6a"), t[..., :3])
        t[..., 3] = np.where(inside, 1.0, 0.0)
        return grain(ctx, t, 0.04)
    return Mat(fn, f"edscalerow{key}{n}{base}", directional=False)


def spiral_mat(color, key, glow=0.0):
    def mask(u, v):
        r = np.hypot(u, v)
        a = (np.arctan2(v, u) / (2 * math.pi)) % 1.0
        s = (r * 3.2 - a) % 1.0
        return ((r < 0.98) & ((s < 0.62) | (r < 0.12))).astype(float)
    return tex.shaped(mask, color, "#5a4a36", glow=glow, var=0.05, key=f"edspiral{key}")


def ellipse(rx=1.0, ry=0.4):
    return lambda u, v: (((u / rx) ** 2 + (v / ry) ** 2) <= 1.0).astype(float)


def vane_mat(color, tip, key, glow=0.0, n=5):
    """Feather fan for a horizontal plane: scalloped trailing edge along +V, barbs, rachis lines."""
    k0, k1 = rgb(color), rgb(tip)

    def fn(ctx):
        u = ctx.U * n
        lx = (u % 1.0) * 2 - 1
        v = ctx.V
        edge_v = 0.72 + 0.28 * np.sqrt(np.clip(1 - lx ** 2, 0, 1))
        inside = v <= edge_v
        t = tile(ctx, color, 1, glow)
        t[..., :3] = mix(k0, k1, np.clip(v, 0, 1)[..., None])
        rach = np.abs(lx) < 0.14
        t[..., :3] = np.where(rach[..., None], k0 * 0.7, t[..., :3])
        barb = (((tex.px(ctx)[1] + np.abs(lx * 3).astype(int)) % 3) == 0)
        t[..., :3] = np.where(barb[..., None], t[..., :3] * 0.88, t[..., :3])
        t[..., 4] = glow * np.clip(v, 0, 1)
        t[..., 3] = np.where(inside, 1.0, 0.0)
        return grain(ctx, t, 0.04)
    return Mat(fn, f"edvane{key}{color}{tip}{glow}{n}", directional=False)


def teeth_mat(color, key, n=6, glow=0.0):
    def mask(u, v):
        lx = ((u + 1) / 2 * n) % 1.0
        return (((v + 1) / 2) >= np.abs(lx - 0.5) * 2).astype(float)
    return tex.shaped(mask, color, "#cfc3a0", glow=glow, var=0.03, key=f"edteeth{key}{n}{color}")


# ------------------------------------------------------------------ geometry helpers
def seg(bone, p0, p1, t, mat, t2=None, **kw):
    """Box spanning p0 -> p1 (thickness t, depth t2)."""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    d = p1 - p0
    L = float(np.linalg.norm(d)) or 1e-3
    a = math.degrees(math.asin(max(-1.0, min(1.0, d[2] / L))))
    c = math.degrees(math.atan2(-d[0], d[1]))
    mid = tuple((p0 + p1) / 2)
    return bone.box(mid, (t, L, t2 if t2 is not None else t), mat, rot=(a, 0, c), pivot=mid, **kw)


def chain(m, prefix, parent, pts, thick, mat, extra=None, start=1):
    names, par = [], parent
    for i in range(len(pts) - 1):
        b = m.bone(f"{prefix}{i + start}", par, pivot=tuple(pts[i]))
        seg(b, pts[i], pts[i + 1], thick(i) if callable(thick) else thick, mat, variant=i % 3)
        if extra:
            extra(b, i, pts[i], pts[i + 1])
        names.append(b.name)
        par = b.name
    return names


def _shift(model, delta):
    dx, dy, dz = delta
    for b in model.bones.values():
        b.pivot = (b.pivot[0] + dx, b.pivot[1] + dy, b.pivot[2] + dz)
        for c in b.cubes:
            c.origin = (c.origin[0] + dx, c.origin[1] + dy, c.origin[2] + dz)
            if c.pivot:
                c.pivot = (c.pivot[0] + dx, c.pivot[1] + dy, c.pivot[2] + dz)
        b.locators = {k: (v[0] + dx, v[1] + dy, v[2] + dz) for k, v in b.locators.items()}


def mats_common():
    return dict(
        gold=tex.metal(GOLD, GOLD_HI, GOLD_LO, bands=2.0),
        bronze=tex.metal(BRONZE, BRONZE_HI, BRONZE_LO, bands=1.5),
        board=tex.mottled("#4a3418", "#6e5028", scale=3.0, edge_dark=0.25),
        bone=tex.bone_mat(IVORY, IVORY_SH),
        bone_dk=tex.bone_mat("#cbbd98", "#8e7f5c"),
        basalt=tex.stone(BASALT, "#1d1b1a", "#4a4440", scale=3, cracks=0.35, glow_crack=0.9, crack_color=EMBER),
        basalt_plain=tex.stone(BASALT, "#1d1b1a", "#4f4844", scale=3, cracks=0.1),
        moss=tex.mottled(MOSS, "#93a85a", scale=2.0, edge_dark=0.15),
        dark=tex.flat("#1a120a"),
        sapph=tex.metal("#3d6fae", "#a9d4ff", "#1d3557", bands=2.0),
        silver=tex.metal(SILVER, "#f4fbff", "#5d7086", bands=2.5),
    )


def glow_disc(c):
    return tex.shaped(tex.m_disc(1.0), "#ffffff", c, glow=1.0, var=0, key=f"edgd{c}")


def eye_glow(c):
    return tex.glow_flat(c, 1.0, core="#ffffff")


# ------------------------------------------------------------------ 3D skulls (facing -Z, joint at `at`)
def skull(m, lin, prefix, parent, at, s, face=(0, 0, 0), bone_mat=None, glow=None, jaw_open=0.0):
    """Original lineage skulls.  Returns (skull bone, jaw bone)."""
    x0, y0, z0 = at
    bm = bone_mat or tex.bone_mat(IVORY, IVORY_SH)
    gc = glow or EL[lin][0]
    dark = tex.flat("#20160c")
    eye = eye_glow(gc)
    sk = m.bone(f"{prefix}skull", parent, pivot=at, rot=face)

    def B(c, sz, mat=bm, **kw):
        return sk.box((x0 + c[0] * s, y0 + c[1] * s, z0 + c[2] * s), (sz[0] * s, sz[1] * s, sz[2] * s), mat, **kw)

    jaw = m.bone(f"{prefix}jaw", sk, pivot=(x0, y0 + 0.45 * s, z0 - 0.2 * s), rot=(-jaw_open, 0, 0))

    def J(c, sz, mat=bm, **kw):
        return jaw.box((x0 + c[0] * s, y0 + c[1] * s, z0 + c[2] * s), (sz[0] * s, sz[1] * s, sz[2] * s), mat, **kw)

    def teeth(zc, length, y, n=6):
        for sx in (1, -1):
            sk.plane("x", (x0 + sx * 0.5 * s * tw, y0 + y * s, z0 + zc * s), length * s, 0.35 * s,
                     teeth_mat("#f4ecd6", lin, n))
    if lin == "n":          # sauropod: high nasal arch, blunt broad snout, peg teeth
        tw = 1.3
        B((0, 1.1, -0.9), (1.8, 1.7, 1.9))
        B((0, 1.95, -0.55), (1.5, 0.5, 1.1), variant=1)                     # skull roof
        B((0, 2.2, -1.75), (1.3, 1.1, 1.3), variant=1)                      # high nasal arch
        B((0, 2.85, -1.75), (0.9, 0.35, 0.9), variant=2)
        B((0, 0.85, -2.65), (1.55, 1.1, 1.3), variant=2)                    # broad muzzle
        B((0, 1.45, -2.45), (1.1, 0.5, 0.9))
        B((0, 3.04, -1.75), (0.6, 0.05, 0.6), dark)                         # naris on the dome
        for sx in (1, -1):
            B((sx * 0.93, 0.95, -0.55), (0.06, 0.7, 0.9), dark)             # temporal openings
        for sx in (1, -1):
            B((sx * 0.91, 1.45, -1.05), (0.06, 0.55, 0.6), dark)
            B((sx * 0.88, 1.45, -1.05), (0.06, 0.28, 0.3), eye)
        teeth(-2.6, 1.2, 0.2)
        J((0, 0.15, -1.75), (1.4, 0.4, 2.7))
    elif lin == "h":        # carnotaur: deep short skull, brow horns, ember fenestrae
        tw = 1.5
        B((0, 1.3, -1.0), (1.9, 2.0, 2.0))
        B((0, 1.05, -2.45), (1.5, 1.6, 1.1), variant=1)
        B((0, 2.35, -1.55), (1.95, 0.3, 0.7), variant=2)
        for k in range(3):                                                  # rugose nasal bosses
            B((0, 1.95 - k * 0.12, -2.1 - k * 0.45), (0.7, 0.3, 0.4), variant=k)
        hm = tex.bone_mat("#d7c7a0", "#8f7a52")
        for sx in (1, -1):
            B((sx * 1.0, 0.85, -1.2), (0.25, 0.9, 1.6), variant=2)            # flared jugal
            hp = (x0 + sx * 0.8 * s, y0 + 2.3 * s, z0 - 1.25 * s)
            sk.box((x0 + sx * 0.8 * s, y0 + 2.85 * s, z0 - 1.25 * s), (0.6 * s, 1.2 * s, 0.6 * s), hm,
                   rot=(-10, 0, -sx * 52), pivot=hp)
            sk.box((x0 + sx * 0.8 * s, y0 + 3.7 * s, z0 - 1.25 * s), (0.35 * s, 0.8 * s, 0.35 * s), hm,
                   rot=(-10, 0, -sx * 52), pivot=hp, variant=1)
            B((sx * 0.78, 1.15, -2.45), (0.06, 0.5, 0.6), dark)               # antorbital fenestra
            B((sx * 0.96, 1.55, -1.45), (0.06, 0.55, 0.6), dark)
            B((sx * 0.98, 1.55, -1.45), (0.06, 0.3, 0.3), eye)
            B((sx * 0.96, 0.95, -2.1), (0.06, 0.35, 0.8), tex.glow_flat(EMBER, 0.9, core="#ffd08a"))
        teeth(-2.0, 1.6, 0.18, 7)
        J((0, 0.15, -1.6), (1.6, 0.55, 2.6))
    elif lin == "w":        # spinosaur: long low croc snout, rosette tip, sail crest
        tw = 0.95
        B((0, 1.0, -0.8), (1.4, 1.5, 1.7))
        B((0, 0.65, -2.85), (0.8, 0.65, 2.8), variant=1)
        B((0, 1.05, -2.0), (0.55, 0.35, 1.6), variant=2)                     # nasal ridge
        B((0, 0.62, -4.45), (1.1, 0.8, 0.6), variant=2)
        sk.plane("x", (x0, y0 + 2.05 * s, z0 - 1.5 * s), 1.8 * s, 1.0 * s,
                 tex.shaped(tex.m_crescent(0.0), "#9fd8ff", "#3f7fd0", glow=0.5, key="edcrest"))
        for sx in (1, -1):
            B((sx * 0.71, 1.3, -0.95), (0.06, 0.45, 0.5), dark)
            B((sx * 0.73, 1.3, -0.95), (0.06, 0.25, 0.25), eye)
        teeth(-3.0, 2.8, 0.3, 9)
        J((0, 0.12, -2.4), (0.9, 0.35, 4.2))
    else:                   # microraptor: round cranium, great orbit, slender beak, crest feathers
        tw = 0.7
        B((0, 1.0, -0.7), (1.3, 1.3, 1.4))
        B((0, 1.55, -0.55), (1.0, 0.3, 1.0), variant=2)
        B((0, 0.78, -1.85), (0.7, 0.6, 1.2), variant=1)
        B((0, 0.66, -2.65), (0.42, 0.38, 0.6), variant=2)
        for sx in (1, -1):
            B((sx * 0.66, 1.15, -0.85), (0.06, 0.7, 0.7), dark)
            B((sx * 0.68, 1.15, -0.85), (0.06, 0.38, 0.38), eye)
        fm = tex.feather("#e8eef6", "#9fb8d2", "#7f8fa6", glow=0.2, glow_tip=0.5, notch=0.0)
        for k in range(3):
            sk.cube((x0 - 0.15 * s, y0 + 1.65 * s, z0 - (0.2 - 0.35 * k) * s), (0.3 * s, 1.2 * s, 0), fm,
                    rot=(55 + k * 12, 0, 0), pivot=(x0, y0 + 1.65 * s, z0 - (0.2 - 0.35 * k) * s), variant=k)
        teeth(-1.9, 1.3, 0.48, 5)
        J((0, 0.42, -1.6), (0.6, 0.22, 2.0))
    return sk.name, jaw.name


# =====================================================================================
#                                     THE HELD BOOK
# =====================================================================================
W, H, T = 14.0, 20.0, 5.0       # width (x), height (y), thickness (z)
HX = W / 2                      # spine / hinge at +X


def build_book():
    m = Model("book_ed", density=3.0, bounds=(3, 3, (0, 1.6, 0)), dscale=0.68)   # held-item texture budget: 256x256
    m.plain = True   # held item: also write a plain texture for the vanilla material (books_zfix)
    C = mats_common()
    gold, bone, board = C["gold"], C["bone"], C["board"]
    edge_side = tex.banded(tex.flat("#e6dbbd", jitter=0.03), "#b7a47a", every=2, width=1, horizontal=False)
    edge_ud = tex.banded(tex.flat("#e6dbbd", jitter=0.03), "#b7a47a", every=2, width=1, horizontal=True)
    art_l = page_art(["n", "h"], "L")
    art_r = page_art(["w", "a"], "R")
    art_leaf = page_art(["h", "a"], "leaf")

    root = m.bone("book", None, pivot=(0, 0, 0))
    root.binding = "q.item_slot_to_bone_name(c.item_slot)"
    place = m.bone("place", root, pivot=(0, 0, 0))
    face = m.bone("face", place, pivot=(0, 0, 0))
    hover = m.bone("hover", face, pivot=(0, 0, 0))
    body = m.bone("body", hover, pivot=(0, 0, 0))

    # --- back board + its page stack
    body.cube((-HX - 0.2, -H / 2 - 0.3, 1.8), (W + 0.4, H + 0.6, 0.8), board)
    body.cube((-HX + 0.2, -H / 2 + 0.2, 0.0), (W - 0.6, H - 0.4, 1.8), edge_side, mats={"north": art_l, "up": edge_ud, "down": edge_ud},
              density=5)
    body.plane("z", (0, 0, 2.63), 10.0, 10.0, tex.magic_circle(glyphs.DRACONIC, BRONZE_HI, GOLD, glow=0.15,
                                                                bands=((0.62, 0.9, 12),), lines=(0.58, 0.95), star=4,
                                                                star_r=(0.15, 0.55), core=0.1, key="edback"), density=5)
    body.plane("z", (0, 0, 2.65), 2.6, 2.6, spiral_mat("#d8c7a0", "back"))
    for sx, sy in ((-1, 1), (-1, -1)):          # back corners (fore-edge side)
        body.box((sx * (HX - 0.6), sy * (H / 2 - 0.6), 2.45), (1.6, 1.6, 0.5), gold, variant=1)
    # spine board + vertebrae
    spine = m.bone("spine", body, pivot=(HX, 0, 0))
    spine.cube((HX - 0.2, -H / 2 - 0.3, -2.6), (0.9, H + 0.6, 5.2), board, variant=1)
    pts = [(HX + 0.9, -H / 2 + 1.0 + i * 3.0, 0) for i in range(7)]
    verts = []
    par = spine.name
    for i in range(6):
        b = m.bone(f"vert{i + 1}", par, pivot=pts[i])
        y = pts[i][1] + 1.5
        b.box((HX + 1.05, y, 0), (1.3, 2.3, 2.3), bone, variant=i % 3)                  # centrum
        b.box((HX + 1.05, y - 1.35, 0), (1.15, 0.4, 2.0), C["bone_dk"])                 # disc
        b.box((HX + 2.2, y + 0.2, 0), (1.6, 0.7, 0.8), bone, rot=(0, 0, -22), pivot=(HX + 1.5, y, 0), variant=1)
        for sz in (1, -1):
            b.box((HX + 1.2, y, sz * 1.95), (0.6, 0.55, 1.3), bone, rot=(sz * 18, 0, 0), pivot=(HX + 1.2, y, sz * 1.2))
        verts.append(b.name)
        par = b.name
    cap = m.bone("spine_skull", verts[-1], pivot=(HX + 1.0, H / 2, 0))
    cap.box((HX + 1.1, H / 2 + 0.7, -0.2), (1.5, 1.4, 1.8), bone)
    cap.box((HX + 1.1, H / 2 + 0.55, -1.4), (1.0, 0.8, 1.1), bone, variant=1)
    cap.box((HX + 1.86, H / 2 + 0.9, -0.5), (0.05, 0.35, 0.35), eye_glow(EMBER))
    tail = m.bone("spine_tail", spine, pivot=(HX + 0.9, -H / 2 + 1.0, 0))
    seg(tail, (HX + 1.0, -H / 2 + 1.0, 0), (HX + 1.4, -H / 2 - 0.6, 0.4), 0.9, bone)
    seg(tail, (HX + 1.4, -H / 2 - 0.6, 0.4), (HX + 1.5, -H / 2 - 1.8, 1.1), 0.55, bone, variant=1)

    # --- front cover (hinged on the spine) with its page stack
    front = m.bone("front", body, pivot=(HX, 0, 0))
    front.cube((-HX - 0.2, -H / 2 - 0.3, -2.6), (W + 0.4, H + 0.6, 0.8), board, variant=2,
               mats={"south": tex.mottled("#7a5a2c", "#5a3f1c", scale=2.0)})
    front.cube((-HX + 0.2, -H / 2 + 0.2, -1.8), (W - 0.6, H - 0.4, 1.8), edge_side, mats={"south": art_r, "up": edge_ud, "down": edge_ud},
               density=5)
    # draconic inscription bands, top and bottom
    band = tex.glyph_rows(glyphs.DRACONIC, GOLD_HI, glow=0.75, bg="#2a1c0c", bg_glow=0.0, fill=0.9, key="edband")
    front.plane("z", (0, H / 2 - 0.9, -2.66), W - 1.4, 1.3, band, density=7)
    front.plane("z", (0, -H / 2 + 0.9, -2.66), W - 1.4, 1.3, band, density=7, variant=1)
    # gold L-corners
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        cx, cy = sx * (HX - 0.4), sy * (H / 2 - 0.4)
        front.box((cx - sx * 1.2, cy, -2.85), (3.2, 0.9, 0.7), gold, variant=sx > 0)
        front.box((cx, cy - sy * 1.2, -2.85), (0.9, 3.2, 0.7), gold, variant=2)
        front.box((cx, cy, -3.05), (0.7, 0.7, 0.4), tex.metal("#d9b45a", "#fff3c4", "#8a6a26", bands=3.0, glow=0.2))
    # breathing scale rows (shingled, upper rows in front)
    rows = []
    nrow = 6
    for i in range(nrow):
        y_top = H / 2 - 1.75 - i * 2.75
        z = -2.66 - 0.07 * (nrow - i)
        b = m.bone(f"scales{i + 1}", front, pivot=(0, y_top, z), rot=(9, 0, 0))
        b.plane("z", (0, y_top - 1.85, z), W - 0.6, 3.7, scale_row(6, f"r{i % 2}"), variant=i % 2, density=4)
        rows.append(b.name)
    # fossil inlays near the lower corners
    for sx in (1, -1):
        front.plane("z", (sx * 4.6, -H / 2 + 2.9, -3.2), 1.6, 1.6, spiral_mat("#d8c7a0", f"f{sx}"), variant=sx > 0)
    # central seal + four skull emblems
    emb = m.bone("emblem", front, pivot=(0, 0, -3.3))
    emb.plane("z", (0, 0, -3.35), 5.2, 5.2, tex.shaped(tex.m_disc(1.0), "#2a1c0c", "#140c06", var=0, key="edsealbg"))
    ring(emb, (0, 0, -3.4), 2.75, 10, (1.9, 0.55, 0.55), gold, axis="z", cycle=2)
    seal = m.bone("seal", emb, pivot=(0, 0, -3.5))
    seal.plane("z", (0, 0, -3.5), 4.6, 4.6, tex.magic_circle(glyphs.DRACONIC, GOLD_HI, EMBER, glow=0.9,
                                                             bands=((0.6, 0.92, 9),), lines=(0.55, 0.97), star=4,
                                                             star_r=(0.1, 0.5), core=0.12, key="edseal"), density=8)
    spots = {"n": (0, 5.7), "h": (-4.45, 0), "w": (0, -5.7), "a": (4.45, 0)}
    for lin, (ex, ey) in spots.items():
        pb = m.bone(f"plaque_{lin}", emb, pivot=(ex, ey, -3.3))
        pb.plane("z", (ex, ey, -3.32), 4.2, 3.2, tex.shaped(tex.m_disc(1.0), BASALT, "#140f0c", outline=GOLD, var=0,
                                                         key="edplaque"), density=6)
        gb = m.bone(f"glow_{lin}", pb, pivot=(ex, ey, -3.38))
        gb.plane("z", (ex, ey, -3.38), 3.8, 2.8, glow_disc(EL[lin][0]), density=6)
        art = SKULL_ART[lin]
        pb.plane("z", (ex, ey, -3.46), 3.1, 3.1 * len(art) / len(art[0]),
                 tex.bitmap_cut(art, "#f2ead6", glow=0.3, color2=IVORY_SH, key=f"edskullart{lin}"), density=6)

    # --- loose leaves (turned in flourishes)
    leaves = []
    for k in range(3):
        lb = m.bone(f"leaf{k + 1}", body, pivot=(HX - 0.4, 0, -0.04 - 0.05 * k))
        lb.plane("z", (-0.1, 0, -0.04 - 0.05 * k), W - 1.0, H - 0.8, art_leaf, variant=k, density=4)
        leaves.append(lb.name)

    # --- four distinct dragon-claw clasps (hinged on the back board)
    clasp_specs = build_clasps(m, body, C)

    # --- bookmark ribbons
    for k, (rx, col) in enumerate(((HX - 1.6, "#8a2a1a"), (HX - 2.6, "#3f5f2a"))):
        par = body.name
        for s_ in range(2):
            y1 = -H / 2 + 0.2 - s_ * 2.6
            rb = m.bone(f"ribbon{k + 1}_{s_ + 1}", par, pivot=(rx, y1, 0.2))
            rb.plane("z", (rx, y1 - 1.3, 0.2), 0.8, 2.6, tex.fabric(col, None, 0.1, fringe=s_ == 1), variant=s_)
            par = rb.name

    # --- the draconic halo that rises behind the open book
    halo = m.bone("halo", hover, pivot=(HX, 0, 4.2))
    halo.plane("z", (HX, 0, 4.2), 30, 30, tex.magic_circle(glyphs.DRACONIC, "#ffd27a", EMBER, glow=1.0,
                                                       bands=((0.70, 0.86, 18), (0.40, 0.52, 10)), lines=(0.66, 0.9, 0.37),
                                                       star=4, star_r=(0.2, 0.62), key="edhalo"), density=2.2)
    _shift(m, BOOK_CENTER)
    for n in ("place",):
        m.bones[n].pivot = HAND_PIVOT
    return m, dict(rows=rows, verts=verts, leaves=leaves, clasps=clasp_specs)


def build_clasps(m, body, C):
    """Four clasps: Nature + Heat on the fore-edge, Water on the top edge, Air on the bottom edge."""
    out = {}
    fx = -HX - 0.2            # fore-edge x
    # fore-edge clasps hinge about Y at (fx, *, 2.6)
    for lin, yc in (("n", 4.6), ("h", -4.6)):
        b = m.bone(f"clasp_{lin}", body, pivot=(fx, yc, 2.6))
        if lin == "n":
            strap, toe, nail = C["moss"], C["bronze"], tex.bone_mat("#efe6cc", "#a89670")
            tw, tl, nl = 0.8, 2.0, 0.8
        else:
            strap, toe, nail = C["basalt"], C["basalt"], tex.flat("#141010", jitter=0.08)
            tw, tl, nl = 0.5, 2.5, 1.5
        b.box((fx + 1.0, yc, 2.85), (2.6, 2.2, 0.5), strap)
        b.box((fx - 0.25, yc, 0), (0.55, 2.2, 5.7), strap, variant=1)
        b.box((fx + 0.9, yc, -2.95), (2.4, 2.4, 0.6), toe)
        for k, dy in enumerate((-0.75, 0.0, 0.75)):
            L = tl * (0.85 if k != 1 else 1.0)
            b.box((fx + 2.1 + L / 2, yc + dy, -2.95), (L, tw, tw * 0.9), toe, variant=k)
            tip_x = fx + 2.1 + L
            if lin == "n":
                b.box((tip_x + nl / 2 - 0.1, yc + dy, -2.85), (nl, tw * 1.05, tw * 0.95), nail)
            else:
                b.box((tip_x + nl / 2 - 0.2, yc + dy, -2.75), (nl, 0.4, 0.45), nail, rot=(0, 30, 0),
                      pivot=(tip_x - 0.2, yc + dy, -2.75))
        if lin == "n":
            b.plane("z", (fx + 0.6, yc + 1.25, -3.3), 1.6, 1.0, tex.foliage("#3f7a35", "#8fc060", holes=0.2), faces=("north", "south"))
        else:
            b.box((fx + 0.9, yc, -3.27), (1.2, 0.25, 0.06), tex.glow_flat(EMBER, 1.0, core="#ffe0a0"))
        out[lin] = b.name
    # top clasp (Water & Ice): hinge about X at (*, H/2+0.3, 2.6), toes point down (-Y)
    yt = H / 2 + 0.3
    b = m.bone("clasp_w", body, pivot=(-2.4, yt, 2.6))
    sa = C["sapph"]
    b.box((-2.4, yt - 1.0, 2.85), (2.2, 2.4, 0.5), sa)
    b.box((-2.4, yt + 0.25, 0), (2.2, 0.55, 5.7), sa, variant=1)
    b.box((-2.4, yt - 0.9, -2.95), (2.4, 2.2, 0.6), sa, variant=2)
    for k, dx in enumerate((-0.8, 0.0, 0.8)):
        b.box((-2.4 + dx, yt - 2.9, -2.95), (0.45, 2.0, 0.45), sa, variant=k)
        b.box((-2.4 + dx, yt - 4.2, -2.85), (0.35, 0.8, 0.35), tex.crystal(ICE, "#7fb7e6", mode="solid", glow=0.5))
    web = m.bone("clasp_w_web", b, pivot=(-2.4, yt, 2.6))
    web.plane("z", (-2.4, yt - 3.0, -2.98), 1.7, 2.0, tex.fluid("#3c8fe6", "#bfe8ff", a=0.6, glow=0.4))
    out["w"] = b.name
    # bottom clasp (Air): slender raptor foot with sickle claw and a feather
    yb = -H / 2 - 0.3
    b = m.bone("clasp_a", body, pivot=(-2.4, yb, 2.6))
    sv = C["silver"]
    b.box((-2.4, yb + 1.0, 2.85), (1.6, 2.4, 0.4), sv)
    b.box((-2.4, yb - 0.25, 0), (1.6, 0.5, 5.7), sv, variant=1)
    b.box((-2.4, yb + 0.9, -2.92), (1.6, 2.0, 0.5), sv, variant=2)
    for k, dx in enumerate((-0.5, 0.5)):
        b.box((-2.4 + dx, yb + 2.8, -2.92), (0.35, 2.0, 0.35), sv, variant=k)
    seg(b, (-1.4, yb + 1.6, -2.95), (-0.6, yb + 2.6, -3.0), 0.4, tex.flat("#dfe7ef", jitter=0.05))
    seg(b, (-0.6, yb + 2.6, -3.0), (-0.75, yb + 3.4, -3.0), 0.3, tex.flat("#eef4fa", glow=0.3))
    b.cube((-3.6, yb - 0.6, -3.0), (0.9, 2.4, 0), tex.feather("#eef3fa", "#9fb8d2", "#7f8fa6", glow=0.15, glow_tip=0.45),
           rot=(0, 0, -20), pivot=(-3.15, yb + 1.8, -3.0))
    out["a"] = b.name
    return out


def build_book_anims(info):
    A = []
    rows, verts, leaves, clasps = info["rows"], info["verts"], info["leaves"], info["clasps"]

    def fp(a, b):
        return M(f"c.is_first_person ? {a} : {b}", lambda t: b)

    def fp_open(a, b, oa, ob):
        return M(f"(c.is_first_person ? {a} : {b}) + v.open * (c.is_first_person ? {oa} : {ob})", lambda t: b)

    place = Anim("place", loop=True)
    place.pos("place", tuple(fp_open(FIRST["pos"][i], THIRD["pos"][i], FP_OPEN_POS[i], TP_OPEN_POS[i]) for i in range(3)))
    place.rot("place", tuple(fp_open(FIRST["rot"][i], THIRD["rot"][i], FP_OPEN_ROT[i], TP_OPEN_ROT[i]) for i in range(3)))
    place.rot("face", (0, fp(FIRST["turn"], THIRD["turn"]), 0))
    place.pos("face", tuple(fp(FIRST["lift"][i] * FIRST["scale"], THIRD["lift"][i] * THIRD["scale"]) for i in range(3)))
    place.scl("hover", fp(FIRST["scale"], THIRD["scale"]))
    A.append(place)

    idle = Anim("idle", loop=True)
    idle.pos("hover", (0, LIFE(0.7, 3.6), 0))
    idle.rot("hover", (LIFE(2.2, 5.2), LIFE(3.5, 7.4, 0.2), LIFE(1.6, 4.6, 0.4)))
    idle.rot("front", (0, LIFE(1.1, 3.2, 0.0, -1.2), 0))
    for i, r in enumerate(rows):
        idle.rot(r, (LIFE(3.2, 3.2, -i * 0.07), 0, 0))
    for i, v in enumerate(verts):
        idle.rot(v, (0, LIFE(1.4, 4.0, -i * 0.1), LIFE(1.0, 4.0, -i * 0.1 + 0.25)))
    idle.rot("spine_skull", (LIFE(6, 5.0), LIFE(10, 6.5), 0))
    idle.rot("spine_tail", (LIFE(8, 2.6), LIFE(12, 3.3), 0))
    for k, lf in enumerate(leaves):
        idle.rot(lf, (0, LIFE(0.9, 2.2, k * 0.21, -0.9), 0))
    for k in (1, 2):
        wave(idle, [f"ribbon{k}_1", f"ribbon{k}_2"], 0, 9, 2.8 + k * 0.4, lag=0.2, grow=1.3, clock="q.life_time")
    idle.rot(clasps["n"], (0, LIFE(1.2, 2.9), 0))
    idle.rot(clasps["h"], (0, LIFE(1.2, 2.9, 0.5), 0))
    idle.rot(clasps["w"], (LIFE(1.2, 3.3, 0.2), 0, 0))
    idle.rot(clasps["a"], (LIFE(1.2, 3.3, 0.7), 0, 0))
    for k, lin in enumerate(LIN):   # each skull emblem wakes in turn
        idle.scl(f"glow_{lin}", M(f"0.55 + 0.6 * math.pow(math.max(0, math.sin(q.life_time * 90 - {k * 90})), 4)",
                                  lambda t, k=k: 0.55 + 0.6 * max(0, math.sin(math.radians(t * 90 - k * 90))) ** 4))
    idle.rot("seal", (0, 0, M("q.life_time * 12", lambda t: t * 12)))
    A.append(idle)

    closed = Anim("closed", loop=True)
    closed.scl("halo", 0.0)
    A.append(closed)

    # page-turn flourish on crouch: clasps flick, cover pops, three leaves riffle across, closes
    turn = Anim("turn", length=1.15, loop="hold")
    turn.rot(clasps["n"], {0: (0, 0, 0), 0.12: (0, 80, 0), 0.95: (0, 80, 0), 1.12: (0, 0, 0)})
    turn.rot(clasps["h"], {0: (0, 0, 0), 0.15: (0, 80, 0), 0.95: (0, 80, 0), 1.12: (0, 0, 0)})
    turn.rot(clasps["w"], {0: (0, 0, 0), 0.12: (85, 0, 0), 0.95: (85, 0, 0), 1.1: (0, 0, 0)})
    turn.rot(clasps["a"], {0: (0, 0, 0), 0.14: (-85, 0, 0), 0.95: (-85, 0, 0), 1.1: (0, 0, 0)})
    turn.rot("front", {0: (0, 0, 0), 0.12: (0, 0, 0), 0.32: (0, -168, 0), 0.72: (0, -165, 0), 0.98: (0, 4, 0), 1.08: (0, 0, 0)})
    for k, lf in enumerate(leaves):
        t0 = 0.34 + k * 0.1
        turn.rot(lf, {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.06: (0, -40, 0), t0 + 0.16: (0, -158 + k * 3, 0),
                      0.72: (0, -158 + k * 3, 0), 0.98: (0, 2, 0), 1.08: (0, 0, 0)})
    turn.pos("hover", {0: (0, 0, 0), 0.2: (0, 1.4, 0), 0.7: (0, 1.0, 0), 1.15: (0, 0, 0)})
    turn.rot("hover", {0: (0, 0, 0), 0.2: (-6, 8, 0), 0.7: (-4, -6, 0), 1.15: (0, 0, 0)})
    for lin in LIN:
        turn.scl(f"glow_{lin}", {0: 1.0, 0.3: 1.5, 0.8: 1.3, 1.15: 1.0})
    turn.scl("emblem", {0: 1.0, 0.25: 1.08, 0.6: 1.0})
    turn.sound(0.0, "flip")
    A.append(turn)

    # open and rise while Use is held
    op = Anim("open", length=0.75, loop="hold")
    op.anim_time_update = "v.open * 0.75"     # always applied; its time follows v.open (0 = closed)
    op.rot(clasps["n"], {0: (0, 0, 0), 0.15: (0, 75, 0), 0.3: (0, 64, 0)})
    op.rot(clasps["h"], {0: (0, 0, 0), 0.18: (0, 78, 0), 0.33: (0, 66, 0)})
    op.rot(clasps["w"], {0: (0, 0, 0), 0.15: (72, 0, 0), 0.3: (62, 0, 0)})
    op.rot(clasps["a"], {0: (0, 0, 0), 0.17: (-72, 0, 0), 0.32: (-62, 0, 0)})
    op.rot("front", {0: (0, 0, 0), 0.15: (0, -10, 0), 0.5: (0, -172, 0), 0.62: (0, -166, 0), 0.75: (0, -170, 0)})
    op.rot("spine", {0: (0, 0, 0), 0.15: (0, 0, 0), 0.5: (0, -86, 0), 0.75: (0, -85, 0)})
    op.pos("spine", {0: (0, 0, 0), 0.15: (0, 0, 0), 0.5: (0, 0, 2.4), 0.75: (0, 0, 2.4)})
    op.pos("body", {0: (0, 0, 0), 0.5: (-HX, 10.5, 0), 0.75: (-HX, 10.0, 0)})
    op.rot("body", {0: (0, 0, 0), 0.5: (32, 0, 0), 0.75: (28, 0, 0)})
    op.scl("halo", {0: 0.0, 0.3: 0.0, 0.6: 1.08, 0.75: 1.0})
    op.pos("halo", {0: (0, 0, 0), 0.75: (-HX, 10.0, 0)})
    for lin in LIN:
        op.scl(f"glow_{lin}", {0: 1.0, 0.5: 1.6, 0.75: 1.35})
    A.append(op)

    ol = Anim("open_loop", loop=True, length=2.4)
    for k, lf in enumerate(leaves):
        t0 = 0.15 + k * 0.75
        ol.rot(lf, {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.12: (0, -50, 0), t0 + 0.4: (0, -166, 0), 2.4: (0, -166, 0)})
        ol.scl(lf, {0: 1.0, t0 + 0.42: 1.0, t0 + 0.46: 0.0, 2.36: 0.0, 2.4: 1.0}, smooth=False)
    ol.rot("halo", (0, 0, M("q.life_time * 40", lambda t: t * 40)))
    ol.pos("hover", (0, S(0.6, 1.2), 0))
    for k, lin in enumerate(LIN):
        ol.scl(f"glow_{lin}", S(0.25, 1.2, k * 0.25, 1.0))
    A.append(ol)
    return A


def book_controller():
    # opening is not a state any more: "open" always plays with its time set from v.open (see OPEN_PRE_ANIMATION)
    return {"format_version": "1.10.0", "animation_controllers": {
        "controller.animation.grimoire.book_ed.main": {
            "initial_state": "idle",
            "states": {
                "idle": {"animations": [], "transitions": [{"turn": "q.is_sneaking && v.open < 0.05"}],
                         "blend_transition": 0.3},
                "turn": {"animations": ["turn"], "transitions": [{"wait": "q.all_animations_finished"}],
                         "blend_transition": 0.12},
                "wait": {"animations": [], "transitions": [{"idle": "!q.is_sneaking"}],
                         "blend_transition": 0.1},
            }}}}


def write_attachable(pack, m, anims):
    geo_id, tex_path = pack.model(m)
    for a in anims:
        a.model = "book_ed"
    rp = pack.rp
    _write(os.path.join(rp, "animations", "book_ed.animation.json"), animations_file(anims))
    _write(os.path.join(rp, "animation_controllers", "book_ed.animation_controllers.json"), book_controller())
    rc = {"geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"]}
    for b in m.blend_bones:
        rc["materials"].append({b: "Material.blend"})
    _write(os.path.join(rp, "render_controllers", "book_ed.render_controllers.json"),
           {"format_version": "1.8.0", "render_controllers": {"controller.render.grimoire.book_ed": rc}})
    amap = {a.name: a.full for a in anims}
    amap["ctl"] = "controller.animation.grimoire.book_ed.main"
    _write(os.path.join(rp, "attachables", "elemental_dragon.json"), {
        "format_version": "1.10.0",
        "minecraft:attachable": {"description": {
            "identifier": "grimoire:elemental_dragon",
            "materials": {"default": "entity_emissive_alpha", "blend": "entity_alphablend"},
            "textures": {"default": tex_path},
            "geometry": {"default": geo_id},
            "animations": amap,
            "scripts": {"pre_animation": list(OPEN_PRE_ANIMATION),
                        "animate": ["place", "idle", "open", {"open_loop": "v.open"}, "ctl"]},
            "sound_effects": {"flip": "grimoire.book_ed_flip"},
            "render_controllers": ["controller.render.grimoire.book_ed"],
        }}})


# =====================================================================================
#                                  SELECTION VISION
# =====================================================================================
def _bone_mats(lin):
    g, deep, tint = EL[lin]
    return tex.bone_mat(tint, IVORY_SH, glow=0.45), tex.glow_flat(g, 1.0, core="#ffffff")


def skel_sauropod(m, p, parent, o, s, bm, face=(0, 0, 0)):
    """Quadruped, long neck, column legs.  Facing -X.  Returns dict(order, legs, neck, tail)."""
    ox, oy, oz = o
    P = lambda x, y, z=0.0: (ox + x * s, oy + y * s, oz + z * s)  # noqa: E731
    body = m.bone(f"{p}body", parent, pivot=P(0, 3.6), rot=face)
    seg(body, P(1.6, 3.7), P(-2.2, 4.0), 0.5 * s, bm)
    body.box(P(1.0, 3.45), (1.2 * s, 0.9 * s, 1.2 * s), bm, variant=1)
    body.box(P(-1.7, 3.6), (0.7 * s, 1.4 * s, 1.3 * s), bm, variant=2)
    for i in range(4):
        body.box(P(-1.2 + i * 0.65, 3.05), (0.22 * s, 1.3 * s, 1.5 * s), bm, variant=i % 3)
    neck = chain(m, f"{p}n", body, [P(-2.2, 4.0), P(-3.0, 5.3), P(-3.5, 6.6), P(-3.7, 7.8), P(-3.6, 8.7)],
                 lambda i: (0.55 - i * 0.07) * s, bm)
    skull(m, "n", f"{p}h_", neck[-1], P(-3.6, 8.5), 0.55 * s, face=(0, 90, 0), bone_mat=bm)
    tail = chain(m, f"{p}t", body, [P(1.6, 3.7), P(2.8, 3.4), P(4.0, 2.9), P(5.1, 2.3), P(6.1, 1.6)],
                 lambda i: (0.5 - i * 0.09) * s, bm)
    legs = []
    for nm, lx, lz in (("fr", -1.6, -0.6), ("fl", -1.6, 0.6), ("rr", 1.0, -0.6), ("rl", 1.0, 0.6)):
        u = m.bone(f"{p}{nm}1", body, pivot=P(lx, 3.1, lz))
        seg(u, P(lx, 3.1, lz), P(lx, 1.6, lz), 0.5 * s, bm)
        lo = m.bone(f"{p}{nm}2", u, pivot=P(lx, 1.6, lz))
        seg(lo, P(lx, 1.6, lz), P(lx + 0.05, 0.25, lz), 0.42 * s, bm)
        lo.box(P(lx - 0.15, 0.15, lz), (0.8 * s, 0.3 * s, 0.6 * s), bm)
        legs.append((u.name, lo.name))
    order = [body.name] + [l[0] for l in legs] + [l[1] for l in legs] + tail + neck + [f"{p}h_skull"]
    return dict(order=order, legs=legs, neck=neck, tail=tail, root=body.name)


def skel_carnotaur(m, p, parent, o, s, bm, face=(0, 0, 0)):
    ox, oy, oz = o
    P = lambda x, y, z=0.0: (ox + x * s, oy + y * s, oz + z * s)  # noqa: E731
    body = m.bone(f"{p}body", parent, pivot=P(0, 3.6), rot=face)
    seg(body, P(0.8, 3.7), P(-2.3, 3.95), 0.48 * s, bm)
    body.box(P(0.2, 3.45), (1.3 * s, 0.8 * s, 1.0 * s), bm, variant=1)
    for i in range(3):
        body.box(P(-0.7 - i * 0.55, 3.25), (0.22 * s, 1.1 * s, 1.2 * s), bm, variant=i % 3)
    for sz in (-0.45, 0.45):
        seg(body, P(-2.0, 3.6, sz), P(-2.15, 3.05, sz), 0.18 * s, bm)
    neck = chain(m, f"{p}n", body, [P(-2.3, 3.95), P(-2.9, 4.55), P(-3.3, 4.85)], 0.42 * s, bm)
    skull(m, "h", f"{p}h_", neck[-1], P(-3.2, 4.55), 0.62 * s, face=(0, 90, 0), bone_mat=bm)
    tail = chain(m, f"{p}t", body, [P(0.8, 3.7), P(2.3, 3.8), P(3.7, 3.7), P(5.0, 3.5), P(6.0, 3.3)],
                 lambda i: (0.46 - i * 0.08) * s, bm)
    legs = []
    for nm, lz in (("r", -0.45), ("l", 0.45)):
        a = m.bone(f"{p}leg{nm}1", body, pivot=P(0.1, 3.5, lz))
        seg(a, P(0.1, 3.5, lz), P(-0.3, 2.1, lz), 0.45 * s, bm)
        b = m.bone(f"{p}leg{nm}2", a, pivot=P(-0.3, 2.1, lz))
        seg(b, P(-0.3, 2.1, lz), P(0.4, 0.9, lz), 0.36 * s, bm)
        c = m.bone(f"{p}leg{nm}3", b, pivot=P(0.4, 0.9, lz))
        seg(c, P(0.4, 0.9, lz), P(0.15, 0.2, lz), 0.3 * s, bm)
        c.box(P(-0.2, 0.12, lz), (0.9 * s, 0.22 * s, 0.45 * s), bm)
        legs.append((a.name, b.name, c.name))
    order = [body.name] + [x for l in legs for x in l] + tail + neck + [f"{p}h_skull"]
    return dict(order=order, legs=legs, neck=neck, tail=tail, root=body.name)


def skel_spinosaur(m, p, parent, o, s, bm, face=(0, 0, 0)):
    ox, oy, oz = o
    P = lambda x, y, z=0.0: (ox + x * s, oy + y * s, oz + z * s)  # noqa: E731
    body = m.bone(f"{p}body", parent, pivot=P(0, 2.6), rot=face)
    seg(body, P(1.4, 2.6), P(-2.2, 2.8), 0.5 * s, bm)
    for i in range(4):
        body.box(P(-1.6 + i * 0.7, 2.15), (0.22 * s, 1.0 * s, 1.3 * s), bm, variant=i % 3)
    spines = []
    sail = m.bone(f"{p}sail", body, pivot=P(-0.4, 2.9))
    for i in range(7):
        x = -1.9 + i * 0.5
        h = 1.0 + 2.2 * math.sin(math.pi * (i + 0.5) / 7)
        seg(sail, P(x, 2.9), P(x + 0.15, 2.9 + h), 0.2 * s, bm, variant=i % 3)
        spines.append(h)
    mem = m.bone(f"{p}sailm", sail, pivot=P(-0.4, 2.9))

    def sail_mask(u, v):
        hh = np.clip(np.sin(np.pi * (u + 1) / 2), 0, 1)
        return (((v + 1) / 2) <= hh * 0.95).astype(float)
    mem.plane("z", P(-0.35, 2.9 + 1.6), 3.6 * s, 3.2 * s,
              tex.shaped(sail_mask, "#7fd6ff", "#1f4f9a", glow=0.4, a=0.55, mode="blend", key="edsailm"))
    neck = chain(m, f"{p}n", body, [P(-2.2, 2.8), P(-3.0, 3.25), P(-3.6, 3.45)], 0.4 * s, bm)
    skull(m, "w", f"{p}h_", neck[-1], P(-3.5, 3.15), 0.55 * s, face=(0, 90, 0), bone_mat=bm)
    fin = tex.shaped(ellipse(1.0, 0.95), "#9fd8ff", "#2f6fd6", glow=0.5, key="edfin")

    def tail_fin(b, i, a, c):
        mid = ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2, a[2])
        b.plane("z", mid, abs(c[0] - a[0]) * 1.1, (1.6 - i * 0.15) * s, fin, variant=i % 2)
    tail = chain(m, f"{p}t", body, [P(1.4, 2.6), P(2.5, 2.5), P(3.6, 2.4), P(4.6, 2.3), P(5.5, 2.2), P(6.4, 2.1)],
                 lambda i: (0.42 - i * 0.06) * s, bm, extra=tail_fin)
    legs = []
    for nm, lx, lz, ln in (("fr", -1.6, -0.5, 1.1), ("fl", -1.6, 0.5, 1.1), ("rr", 0.9, -0.5, 1.6), ("rl", 0.9, 0.5, 1.6)):
        u = m.bone(f"{p}{nm}1", body, pivot=P(lx, 2.3, lz))
        seg(u, P(lx, 2.3, lz), P(lx - 0.3, 2.3 - ln, lz), 0.32 * s, bm)
        u.box(P(lx - 0.5, 2.3 - ln - 0.05, lz), (0.6 * s, 0.18 * s, 0.4 * s), bm)
        legs.append((u.name,))
    order = [body.name] + [l[0] for l in legs] + tail + [sail.name, mem.name] + neck + [f"{p}h_skull"]
    return dict(order=order, legs=legs, neck=neck, tail=tail, root=body.name, sail=sail.name)


def skel_microraptor(m, p, parent, o, s, bm, face=(0, 0, 0)):
    ox, oy, oz = o
    P = lambda x, y, z=0.0: (ox + x * s, oy + y * s, oz + z * s)  # noqa: E731
    vf = vane_mat("#eef3fa", "#8fb0d2", "vis", glow=0.35)
    body = m.bone(f"{p}body", parent, pivot=P(0, 3.5), rot=face)
    seg(body, P(0.9, 3.5), P(-1.1, 3.75), 0.55 * s, bm)
    body.box(P(-0.3, 3.3), (1.4 * s, 0.7 * s, 0.9 * s), bm, variant=1)
    neck = chain(m, f"{p}n", body, [P(-1.1, 3.75), P(-1.6, 4.3), P(-1.9, 4.5)], 0.32 * s, bm)
    skull(m, "a", f"{p}h_", neck[-1], P(-1.85, 4.3), 0.5 * s, face=(0, 90, 0), bone_mat=bm)
    wings = {}
    for nm, sz in (("r", -1), ("l", 1)):
        pts = [P(-0.7, 3.8, 0.35 * sz), P(-0.5, 3.95, 1.7 * sz), P(-0.9, 4.0, 3.1 * sz), P(-0.7, 4.0, 4.2 * sz)]
        names = []
        par = body.name
        for i in range(3):
            b = m.bone(f"{p}w{nm}{i + 1}", par, pivot=pts[i])
            seg(b, pts[i], pts[i + 1], 0.22 * s, bm)
            za, zb = pts[i][2], pts[i + 1][2]
            b.plane("y", (pts[i][0] + (1.0 + i * 0.25) * s, pts[i][1] - 0.05, (za + zb) / 2),
                    (2.0 + i * 0.5) * s, abs(zb - za) * 1.1, vf, variant=i)
            names.append(b.name)
            par = b.name
        wings[nm] = names
    hind = {}
    for nm, sz in (("r", -1), ("l", 1)):
        a = m.bone(f"{p}hl{nm}1", body, pivot=P(0.5, 3.3, 0.3 * sz))
        seg(a, P(0.5, 3.3, 0.3 * sz), P(1.3, 3.0, 1.2 * sz), 0.22 * s, bm)
        b = m.bone(f"{p}hl{nm}2", a, pivot=P(1.3, 3.0, 1.2 * sz))
        seg(b, P(1.3, 3.0, 1.2 * sz), P(2.2, 2.9, 1.9 * sz), 0.18 * s, bm)
        b.plane("y", (2.4 * s + ox, 2.85 * s + oy, 1.6 * sz * s + oz), 1.8 * s, 1.2 * s, vf, variant=2)
        hind[nm] = (a.name, b.name)
    tail = chain(m, f"{p}t", body, [P(0.9, 3.5), P(2.0, 3.45), P(3.1, 3.4), P(4.1, 3.35)], 0.22 * s, bm)
    m.bones[tail[-1]].plane("y", P(4.6, 3.3), 1.8 * s, 1.6 * s,
                            tex.shaped(tex.m_diamond(), "#eef3fa", "#8fb0d2", glow=0.35, key="edtailfan"))
    order = [body.name] + tail + [x for w in wings.values() for x in w] + [x for h in hind.values() for x in h] + neck + [f"{p}h_skull"]
    return dict(order=order, wings=wings, hind=hind, neck=neck, tail=tail, root=body.name)


SKEL = {"n": skel_sauropod, "h": skel_carnotaur, "w": skel_spinosaur, "a": skel_microraptor}


def locomotion(a, lin, info, period, clock="q.anim_time", amp=1.0):
    """Lineage gait as Molang sines (walk / run / swim / fly)."""
    def Sx(am, ph=0.0, base=0.0):
        return S(am * amp, period, ph, base, clock=clock)
    if lin == "n":       # heavy diagonal walk, neck bob
        for (u, lo), ph in zip(info["legs"], (0.0, 0.5, 0.5, 0.0)):
            a.rot(u, (0, 0, Sx(18, ph)))
            a.rot(lo, (0, 0, Sx(10, ph - 0.2, 6)))
        wave(a, info["neck"], 2, 4 * amp, period, lag=0.1, clock=clock)
        wave(a, info["tail"], 1, 6 * amp, period * 2, lag=0.12, clock=clock)
        a.pos(info["root"], (0, S(0.15 * amp, period / 2, clock=clock), 0))
    elif lin == "h":     # predatory run
        for legs, ph in zip(info["legs"], (0.0, 0.5)):
            a.rot(legs[0], (0, 0, Sx(32, ph)))
            a.rot(legs[1], (0, 0, Sx(26, ph - 0.25, 10)))
            a.rot(legs[2], (0, 0, Sx(16, ph - 0.4)))
        a.rot(info["root"], (0, 0, Sx(4, 0.25, -6)))
        a.pos(info["root"], (0, S(0.3 * amp, period / 2, clock=clock), 0))
        wave(a, info["tail"], 1, 5 * amp, period, lag=0.08, clock=clock)
        a.rot(info["neck"][-1], (0, 0, Sx(6, 0.1)))
    elif lin == "w":     # swimming: lateral tail sweep, sail ripple, paddling legs
        wave(a, info["tail"], 1, 16 * amp, period, lag=0.14, grow=1.1, clock=clock)
        a.rot(info["root"], (Sx(4), Sx(6, 0.3), 0))
        a.rot(info["sail"], (Sx(5, 0.2), 0, 0))
        for (u,), ph in zip(info["legs"], (0.0, 0.5, 0.5, 0.0)):
            a.rot(u, (0, 0, Sx(25, ph)))
        wave(a, info["neck"], 1, 5 * amp, period, lag=0.1, clock=clock)
    else:                # flapping flight
        for nm, sg in (("r", 1), ("l", -1)):
            w = info["wings"][nm]
            a.rot(w[0], (Sx(38 * sg), 0, 0))
            a.rot(w[1], (Sx(14 * sg, -0.1), 0, 0))
            a.rot(w[2], (Sx(10 * sg, -0.2), 0, 0))
            a.rot(info["hind"][nm][0], (Sx(16 * sg, 0.4), 0, 0))
        a.pos(info["root"], (0, S(0.4 * amp, period, 0.25, clock=clock), 0))
        wave(a, info["tail"], 2, 5 * amp, period, lag=0.1, clock=clock)


def assemble(a, order, t0, t1, out=None):
    """Bones appear one after another (scale 0 -> 1 with a pop); optional disassembly window."""
    n = len(order)
    for i, b in enumerate(order):
        ta = t0 + (t1 - t0) * i / max(1, n - 1)
        keys = {0: 0.0, ta: 0.0, ta + 0.06: 1.18, ta + 0.11: 1.0}
        if out:
            tb = out[0] + (out[1] - out[0]) * (n - 1 - i) / max(1, n - 1)
            keys.update({tb: 1.0, tb + 0.08: 0.0})
        a.scl(b, keys)


def vision_page(m, root, lin_list):
    """The floating codex page the reconstruction stands over + the emblem plaque behind it."""
    C = mats_common()
    page = m.bone("page", root, pivot=(0, -1.2, 0))
    for sx, nm in ((1, "pg_r"), (-1, "pg_l")):
        b = m.bone(nm, page, pivot=(0, -1.2, 0))
        sc = lin_list[0] if sx > 0 else lin_list[-1]
        b.plane("y", (sx * 2.6, -1.15, 0), 5.2, 4.4, page_art([sc], f"v{sc}", glyph_rows=1), density=7)
        b.cube((sx * 2.6 - 2.7, -1.6, -2.3), (5.4, 0.4, 4.6), C["bronze"], faces=("down", "east", "west", "north", "south"))
        b.box((sx * 5.1, -1.45, 2.1), (0.6, 0.5, 0.6), C["gold"])
        b.box((sx * 5.1, -1.45, -2.1), (0.6, 0.5, 0.6), C["gold"])
    sp = m.bone("pg_spine", page, pivot=(0, -1.6, 0))
    for i in range(4):
        sp.box((0, -1.7, -1.8 + i * 1.2), (0.8, 0.7, 1.0), C["bone"], variant=i % 3)
    emb = m.bone("emb", root, pivot=(0, 5.2, 3.2))
    emb.plane("z", (0, 5.2, 3.3), 5.0, 5.0, tex.shaped(tex.m_disc(1.0), BASALT, "#120d0a", outline=GOLD, var=0, key="edvplq"), density=5)
    ring(emb, (0, 5.2, 3.2), 2.5, 10, (1.7, 0.4, 0.4), C["gold"], axis="z", cycle=2)
    eg = m.bone("emb_glow", emb, pivot=(0, 5.2, 3.15))
    if len(lin_list) == 1:
        lin = lin_list[0]
        eg.plane("z", (0, 5.2, 3.15), 4.6, 4.6, glow_disc(EL[lin][0]), density=5)
        art = SKULL_ART[lin]
        emb.plane("z", (0, 5.2, 3.05), 3.6, 3.6 * len(art) / len(art[0]),
                  tex.bitmap_cut(art, "#f6efdc", glow=0.5, color2=IVORY_SH, key=f"edvart{lin}"), density=6)
    else:
        for k, lin in enumerate(LIN):
            dx, dy = (-1.15 if k % 2 == 0 else 1.15), (1.0 if k < 2 else -1.0)
            eg.plane("z", (dx, 5.2 + dy, 3.15 - 0.01 * k), 2.3, 2.0, glow_disc(EL[lin][0]), density=5)
            art = SKULL_ART[lin]
            emb.plane("z", (dx, 5.2 + dy, 3.05), 2.0, 2.0 * len(art) / len(art[0]),
                      tex.bitmap_cut(art, "#f6efdc", glow=0.5, color2=IVORY_SH, key=f"edvart{lin}"), density=6)
    return page.name


VISION_LEN = 1.2
GAIT = {"n": 0.6, "h": 0.4, "w": 0.6, "a": 0.3}


def build_vision():
    models, kinfo = [], []
    for k in range(6):
        m = Model(f"book_ed_vision_k{k}", density=3.0, bounds=(2, 2, (0, 0.3, 0)))
        root = m.bone("root", None, pivot=(0, 0, 0), rot=(0, FACE_YAW, 0))
        root.locator("mote", (0, 2.0, 0))
        if k < 4:
            lin = LIN[k]
            vision_page(m, root, [lin])
            bm, _g = _bone_mats(lin)
            sk = m.bone("sk", root, pivot=(0, -1.0, 0))
            s = {"n": 0.72, "h": 0.8, "w": 0.7, "a": 0.95}[lin]
            face = (-28, -38, 0) if lin == "a" else (0, 0, 0)
            ox = {"n": 0.6, "h": 0.4, "w": -0.4, "a": -0.2}[lin]
            info = SKEL[lin](m, f"{lin}_", sk, (ox, -1.0, 0), s, bm, face=face)
            if lin == "w":
                wb = m.bone("water", root, pivot=(0, 0, 0))
                wb.plane("y", (0, -0.6, 0), 10.5, 5.0, tex.fluid("#2f6fd6", "#9fe0ff", a=0.45, glow=0.3), density=2)
            kinfo.append(dict(lin=lin, info=info))
        elif k == 4:      # the four lineages as fossils: stone skulls rising and waking
            vision_page(m, root, list(LIN))
            sk = m.bone("sk", root, pivot=(0, -1.0, 0))
            slab = m.bone("slab", sk, pivot=(0, -1.0, 0))
            slab.box((0, -0.85, 0), (10.0, 0.5, 4.6), tex.stone("#9a8a72", "#5f5446", "#b8a88c", scale=3, cracks=0.3,
                                                                   glow_crack=0.6, crack_color="#ffd27a"))
            heads = []
            for i, lin in enumerate(LIN):
                hb = m.bone(f"fos{i}", sk, pivot=(-3.6 + i * 2.4, -0.6, 0))
                stone = tex.stone("#a39276", "#6a5d4a", "#c2b296", scale=2, cracks=0.2)
                skull(m, lin, f"f{i}_", hb, (-3.6 + i * 2.4, -0.6, 0.6), 0.62, face=(0, 0, 0), bone_mat=stone)
                heads.append(hb.name)
            kinfo.append(dict(lin=None, heads=heads))
        else:             # the four alive: four tiny reconstructions circling over the page
            vision_page(m, root, list(LIN))
            sk = m.bone("sk", root, pivot=(0, -1.0, 0))
            orbit = m.bone("orbit", sk, pivot=(0, 0, 0))
            infos = []
            for i, lin in enumerate(LIN):
                hold = m.bone(f"hold{i}", orbit, pivot=(0, 0, 0), rot=(0, i * 90, 0))
                bm, _g = _bone_mats(lin)
                s = {"n": 0.36, "h": 0.4, "w": 0.36, "a": 0.5}[lin]
                info = SKEL[lin](m, f"{lin}_", hold, (0, -1.0, -3.0), s, bm, face=(0, 0, 0))
                infos.append((lin, info))
            kinfo.append(dict(lin=None, infos=infos))
        models.append(m)
    return models, kinfo


def build_vision_anims(kinfo):
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    L = VISION_LEN
    show = Anim("show", length=L, loop="hold")
    show.scl("root", {0: 0.0, 0.12: 1.12, 0.22: 1.0, 1.0: 1.0, 1.12: 1.08, L: 0.0})
    show.pos("root", {0: (0, -3, 0), 0.22: (0, 0.4, 0), 0.4: (0, 0, 0), 1.0: (0, 0.5, 0), L: (0, 2.5, 0)})
    show.rot("root", {0: (0, -40, 0), 0.25: (0, 6, 0), 0.4: (0, 0, 0), 1.0: (0, -4, 0), L: (0, 20, 0)})
    show.rot("pg_l", {0: (0, 0, -80), 0.08: (0, 0, -80), 0.26: (0, 0, 6), 0.34: (0, 0, 0), 0.98: (0, 0, 0), L: (0, 0, -70)})
    show.rot("pg_r", {0: (0, 0, 80), 0.08: (0, 0, 80), 0.26: (0, 0, -6), 0.34: (0, 0, 0), 0.98: (0, 0, 0), L: (0, 0, 70)})
    show.rot("page", (-28, 0, 0))
    show.scl("emb", {0: 0.0, 0.1: 0.0, 0.24: 1.15, 0.32: 1.0, 1.05: 1.0, L: 0.2})
    show.scl("emb_glow", {0: 0.3, 0.2: 0.3, 0.3: 1.35, 0.45: 0.95, 0.75: 1.15, 1.0: 1.0, L: 0.0})
    show.rot("emb", {0: (0, 0, -90), 0.3: (0, 0, 8), 0.42: (0, 0, 0)})
    A.append(show)
    for k, ki in enumerate(kinfo):
        a = Anim(f"show_k{k}", length=L, loop="hold")
        if ki.get("info"):
            lin, info = ki["lin"], ki["info"]
            assemble(a, info["order"], 0.16, 0.5, out=(0.92, 1.12))
            locomotion(a, lin, info, GAIT[lin])
            a.pos("sk", {0: (2.6, 0, 0), 0.5: (1.6, 0, 0), 1.1: (-1.8, 0, 0), L: (-2.2, 0, 0)})
            if lin == "a":
                a.pos("sk", {0: (2.6, -1.0, 0), 0.5: (1.6, 0.0, 0), 1.1: (-1.8, 1.4, 0), L: (-2.4, 1.8, 0)})
            if lin == "w":
                a.scl("water", {0: 0.0, 0.2: 0.0, 0.4: 1.0, 1.0: 1.0, L: 0.0})
            a.sound(0.22, f"call_{lin}")
            a.particle(0.3, {"n": "leaf", "h": "ember", "w": "drop", "a": "feather"}[lin], locator="mote")
        elif ki.get("heads"):
            for i, h in enumerate(ki["heads"]):
                t0 = 0.18 + i * 0.1
                a.scl(h, {0: 0.0, t0: 0.0, t0 + 0.08: 1.2, t0 + 0.14: 1.0, 0.95 + i * 0.03: 1.0, 1.1 + i * 0.02: 0.0})
                a.pos(h, {0: (0, -2.5, 0), t0: (0, -2.5, 0), t0 + 0.14: (0, 0.3, 0), 0.7: (0, 0.6, 0), 1.0: (0, 0.2, 0)})
                a.rot(h, {0: (0, 0, 0), t0 + 0.14: (0, 0, 0), t0 + 0.3: (-20, (-1) ** i * 25, 0), 0.9: (0, 0, 0)})
                a.rot(f"f{i}_jaw", {0: (0, 0, 0), t0 + 0.3: (0, 0, 0), t0 + 0.4: (-22, 0, 0), t0 + 0.55: (0, 0, 0)})
            a.scl("slab", {0: 0.0, 0.12: 1.0, 1.0: 1.0, L: 0.0})
            a.sound(0.22, "call_f")
            a.particle(0.25, "grit", locator="mote")
        else:
            for i, (lin, info) in enumerate(ki["infos"]):
                assemble(a, info["order"], 0.16 + i * 0.06, 0.4 + i * 0.06, out=(0.95, 1.12))
                locomotion(a, lin, info, GAIT[lin], amp=0.8)
            a.rot("orbit", {0: (0, 0, 0), L: (0, -150, 0)}, smooth=False)
            a.sound(0.22, "call_all")
            a.particle(0.3, "burst_small", locator="mote")
        A.append(a)
    return A


# =====================================================================================
#                                  CHARGE CONSTRUCT
# =====================================================================================
FORM_LEN, RELEASE_LEN, CANCEL_LEN = 1.5, 0.5, 0.4


def charge_codex(m, root, C):
    """Open codex lying almost flat, tilted toward the reader; `grow` is the structure root."""
    stage = m.bone("stage", root, pivot=(0, 0, 0))
    codex = m.bone("codex", stage, pivot=(0, 0, 0), rot=(-32, 0, 0))
    art = {1: page_art(["n", "w"], "cl"), -1: page_art(["h", "a"], "cr")}
    for sx, nm in ((-1, "half_l"), (1, "half_r")):
        h = m.bone(nm, codex, pivot=(0, 0, 0), rot=(0, 0, 7 * sx))
        h.cube((min(0, sx * 12.2), -1.3, -8.4), (12.2, 0.9, 16.8), C["board"], variant=sx > 0)
        h.cube((min(0, sx * 11.6) + (0.2 if sx > 0 else -0.2) * 0, -0.4, -7.8), (11.6, 1.2, 15.6),
               tex.banded(tex.flat("#e6dbbd", jitter=0.03), "#b7a47a", every=2, width=1, horizontal=True),
               mats={"up": art[sx]}, density=4)
        for i in range(5):     # scale rows on the underside of the cover
            h.plane("y", (sx * 6.1, -1.32, -6.6 + i * 3.3), 12.0, 3.6, scale_row(6, "cc"), variant=i % 2, faces=("down",), density=2)
        for cz in (-8.0, 8.0):
            h.box((sx * 11.6, -0.85, cz), (1.6, 1.3, 1.6), C["gold"], variant=cz > 0)
        lf = m.bone(f"cleaf_{nm[-1]}", h, pivot=(0, 0.85, 0))
        lf.plane("y", (sx * 5.6, 0.86, 0), 11.0, 15.2, page_art(["a" if sx > 0 else "n"], f"cl{sx}"), density=3)
    sp = m.bone("cspine", codex, pivot=(0, -1.4, 0))
    for i in range(6):
        z = -7.0 + i * 2.8
        sp.box((0, -1.8, z), (1.8, 1.6, 2.2), C["bone"], variant=i % 3)
        sp.box((0, -3.0, z), (0.7, 1.4, 0.8), C["bone"], rot=(25, 0, 0), variant=1)
    # the four claw clasps hang open from the corners
    claw = {"n": C["moss"], "h": C["basalt"], "w": C["sapph"], "a": C["silver"]}
    for (lin, sx, sz) in (("n", -1, -1), ("h", 1, -1), ("w", -1, 1), ("a", 1, 1)):
        cb = m.bone(f"cclasp_{lin}", codex, pivot=(sx * 12.2, -0.8, sz * 6.0))
        cb.box((sx * 12.9, -1.8, sz * 6.0), (1.2, 2.4, 2.2), claw[lin])
        for k in range(3):
            seg(cb, (sx * 13.0, -2.8, sz * 6.0 + (k - 1) * 0.7), (sx * 13.6, -4.4, sz * 6.0 + (k - 1) * 0.9), 0.45, claw[lin], variant=k)
    # rune halo under the book and orbiting runes
    circ = m.bone("circle", stage, pivot=(0, -4.5, 0))
    circ.plane("y", (0, -4.5, 0), 34, 34, tex.magic_circle(glyphs.DRACONIC, "#ffd27a", EMBER, glow=1.0,
                                                          bands=((0.74, 0.9, 20),), lines=(0.7, 0.94, 0.4), star=4,
                                                          star_r=(0.25, 0.66), key="edccircle"), density=1.6)
    runes = m.bone("runes", stage, pivot=(0, 2, 0))
    for k in range(8):
        a = k * 45
        g = glyphs.DRACONIC[(k * 5) % len(glyphs.DRACONIC)]
        runes.box((0, 2 + (k % 2) * 3, -15.5), (2.0, 2.8, 0), tex.bitmap_cut(g, "#ffe2a0", glow=1.0, color2=EMBER),
                  rot=(0, a, 0), pivot=(0, 2, 0), faces=("north", "south"))
    grow = m.bone("grow", stage, pivot=(0, 0.5, 0))
    for nm, pos in (("mote", (0, 6, 0)),):
        grow.locator(nm, pos)
    return grow


def build_charge():
    models, kinfo = [], []
    for k in range(6):
        m = Model(f"book_ed_charge_k{k}", density=1.6, bounds=(4, 4, (0, 1.0, 0)))
        C = mats_common()
        root = m.bone("root", None, pivot=(0, 0, 0), rot=(0, FACE_YAW, 0))
        grow = charge_codex(m, root, C)
        info = [build_k_neck, build_k_carno, build_k_spino, build_k_micro, build_k_slabs, build_k_skulls][k](m, grow, C)
        models.append(m)
        kinfo.append(info)
    return models, kinfo


def build_k_neck(m, grow, C):
    """Sauropod neck: an S of mossy vertebrae rising from the page, small skull on top."""
    bm = tex.bone_mat(IVORY, IVORY_SH, glow=0.08)
    mossb = tex.mottled("#b9bf8a", "#5f7d3a", scale=2.0, edge_dark=0.15)
    pts = [(0, 0.5, 2.2), (0.2, 4.0, 3.4), (0.6, 7.6, 3.4), (1.0, 11.0, 2.0), (1.2, 14.0, -0.2), (1.2, 16.6, -2.4),
           (0.9, 19.0, -3.6), (0.5, 21.0, -3.6), (0.2, 22.4, -2.8)]
    leaf = tex.foliage("#3f7a35", "#8fc060", holes=0.22, flowers="#e8e0a0")

    def deco(b, i, p0, p1):
        th = 2.6 - i * 0.17
        mid = tuple((np.array(p0) + np.array(p1)) / 2)
        b.box((mid[0], mid[1], mid[2] + th * 0.55), (th * 0.35, th * 0.55, th * 0.6), bm, variant=1)   # neural spine
        for sx in (1, -1):
            seg(b, (mid[0] + sx * th * 0.45, mid[1] - 0.2, mid[2] - 0.1), (mid[0] + sx * th * 0.5, mid[1] - 2.6, mid[2] + 0.4),
                0.3, bm, variant=2)                                                                      # cervical ribs
        if i % 2 == 1:
            b.box((mid[0] - th * 0.3, mid[1] + 0.2, mid[2] - th * 0.3), (th * 0.7, 0.9, th * 0.6), mossb)
        if i in (1, 4, 6):
            b.plane("x", (mid[0] + th * 0.55, mid[1] + 0.4, mid[2]), 2.4, 2.0, leaf, variant=i % 3)
    neck = chain(m, "nk", grow, pts, lambda i: 2.6 - i * 0.17, bm, extra=deco)
    sk, jaw = skull(m, "n", "nh_", neck[-1], (0.2, 21.6, -2.4), 2.6, face=(-12, -20, 0), bone_mat=bm)
    m.bones[sk].locator("head", (0.2, 23.5, -8.0))
    base = m.bone("nbase", grow, pivot=(0, 0.5, 0))
    for i in range(6):
        a = i * 60 + 20
        r = 4.2 + (i % 2) * 1.2
        x, z = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
        base.box((x, 0.9 + (i % 3) * 0.3, z), (1.6 + (i % 2), 1.4 + (i % 3) * 0.7, 1.5), C["basalt_plain"],
                 rot=(i * 7, a, i * 5), variant=i % 3)
    for i in range(3):
        a = i * 120 + 60
        x, z = 3.0 * math.cos(math.radians(a)), 3.0 * math.sin(math.radians(a))
        base.plane("x", (x, 1.8, z), 3.0, 3.2, leaf, variant=i, rot=(0, a, 0), pivot=(x, 0.5, z))
    return dict(kind="neck", chain=neck, skull=sk, jaw=jaw, extra=[base.name], call="call_n", fx="leaf", loc="head")


def build_k_carno(m, grow, C):
    """Carnotaur horns and jaws: a great horned skull bursting from the page amid ember vents."""
    bm = tex.bone_mat("#ecdcc0", "#9c845c", glow=0.06)
    neck = chain(m, "ck", grow, [(0, 0.3, 1.6), (0, 3.0, 1.4), (0, 5.4, 0.9)], lambda i: 2.4 - i * 0.3, bm)
    sk, jaw = skull(m, "h", "ch_", neck[-1], (0, 4.6, 2.2), 4.2, face=(-14, 34, 0), bone_mat=bm, jaw_open=28)
    throat = m.bone("ch_throat", sk, pivot=(0, 6.6, -2))
    throat.box((0, 6.4, -3.2), (5.2, 1.2, 6.4), tex.glow_flat(EMBER, 1.0, core="#fff0b8"))
    m.bones[sk].locator("maw", (0, 7.0, -12.0))
    vents = m.bone("cvents", grow, pivot=(0, 0.5, 0))
    for i in range(7):
        a = i * (360 / 7) + 10
        r = 6.5 + (i % 2) * 1.5
        x, z = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
        h = 2.4 + (i % 3) * 1.4
        vents.box((x, 0.5 + h / 2, z), (1.6, h, 1.6), C["basalt"], rot=(0, a, (i % 2) * 14 - 7), variant=i % 3)
        vents.box((x, 0.6 + h, z), (0.9, 0.3, 0.9), tex.glow_flat(EMBER, 1.0, core="#fff0c0"), rot=(0, a, 0))
    return dict(kind="carno", chain=neck, skull=sk, jaw=jaw, extra=[vents.name], call="call_h", fx="ember", loc="maw")


def build_k_spino(m, grow, C):
    """Spinosaur sail and tail: a sapphire-membraned sail and a paddle tail sweeping up out of the page."""
    bm = tex.bone_mat("#e2ecf0", "#8aa2b0", glow=0.1)
    sail = m.bone("ss_sail", grow, pivot=(-2, 0.5, 2))
    spines = []
    for i in range(9):
        x = -9.0 + i * 1.6
        h = 4 + 12 * math.sin(math.pi * (i + 0.5) / 9)
        b = m.bone(f"ss_sp{i + 1}", sail, pivot=(x, 0.5, 2))
        seg(b, (x, 0.5, 2), (x + 0.6, 0.5 + h, 2.2), 0.5, bm, variant=i % 3)
        spines.append(b.name)
    sail.box((-2.6, 1.0, 2.0), (16.0, 1.4, 1.8), bm)
    mem = m.bone("ss_mem", sail, pivot=(-2, 0.5, 2))

    def sail_mask(u, v):
        hh = np.clip(np.sin(np.pi * (u + 1) / 2), 0, 1)
        return (((v + 1) / 2) <= hh * 0.96).astype(float)
    mem.plane("z", (-2.2, 8.4, 2.1), 15.4, 15.6, tex.shaped(sail_mask, "#a8e6ff", "#1f5fb0", glow=0.5, a=0.78,
                                                           mode="blend", key="edcsail"), density=1.2)
    fin = tex.shaped(ellipse(1.0, 0.95), "#9fe0ff", "#2f6fd6", glow=0.55, key="edcfin")

    def tail_fin(b, i, a, c):
        mid = tuple((np.array(a) + np.array(c)) / 2)
        L = float(np.linalg.norm(np.array(c) - np.array(a)))
        d = np.array(c) - np.array(a)
        ang = math.degrees(math.atan2(-d[0], d[1]))
        fw = 6.0 - i * 0.55
        b.cube((mid[0] - fw / 2, mid[1] - L * 0.55, mid[2]), (fw, L * 1.1, 0), fin, rot=(0, 0, ang), pivot=mid,
               variant=i % 2)
    pts = [(7.0, 0.8, 1.0), (9.2, 3.0, 0.6), (10.6, 6.0, 0.0), (11.2, 9.4, -0.6), (10.6, 12.8, -1.0), (9.0, 15.6, -1.0),
           (6.8, 17.4, -0.6)]
    tail = chain(m, "st", grow, pts, lambda i: 2.2 - i * 0.24, bm, extra=tail_fin)
    m.bones[tail[-1]].locator("tip", (6.0, 18.0, 0))
    ice = m.bone("sice", grow, pivot=(0, 0.5, 0))
    cr = tex.crystal(ICE, "#6fb7e6", a=0.78, glow=0.35)
    for i in range(6):
        a = i * 60 + 30
        r = 6.0 + (i % 2) * 2.0
        x, z = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
        ice.box((x, 1.8, z), (1.2, 3.0 + (i % 3) * 1.5, 1.2), cr, rot=((i % 2) * 18 - 9, a, (i % 3) * 10 - 10), variant=i % 3)
    water = m.bone("swater", grow, pivot=(0, 0.7, 0))
    water.plane("y", (0, 0.9, 0), 20, 14, tex.fluid("#2f6fd6", "#9fe0ff", a=0.5, glow=0.35), density=1.0)
    return dict(kind="spino", chain=tail, spines=spines, sail=sail.name, extra=[ice.name, water.name, mem.name],
                call="call_w", fx="drop", loc="tip")


def build_k_micro(m, grow, C):
    """Microraptor feathered limbs: four feathered limbs fanning up out of the page around a slim spine."""
    bm = tex.bone_mat("#eef0f2", "#9aa6b2", glow=0.1)
    torso = chain(m, "mt", grow, [(0, 0.4, 1.0), (0, 4.0, 1.0), (0, 7.5, 0.8), (0, 10.5, 0.6)], 1.1, bm)
    skull(m, "a", "mh_", torso[-1], (0, 10.2, 0.4), 1.6, face=(10, 0, 0), bone_mat=bm)
    fA = [tex.feather("#f4f8fc", "#7f9fc6", "#6a7c94", glow=0.08, glow_tip=0.4),
          tex.feather("#e8eef6", "#a4c0dc", "#7f8fa6", glow=0.08, glow_tip=0.35, notch=0.1)]
    cov = tex.feather("#fbfdff", "#dfe8f2", "#b8c4d2", glow=0.05, taper=0.9, notch=0.0)
    wings = {}
    for nm, side, y, segs, rows, droop in (
            ("fw", 1, 8.8, [3.5, 4.0, 3.5], [dict(n=3, l0=5, l1=6.5, w=2.4, a0=4, a1=12, covert=(3, 2)),
                                             dict(n=3, l0=7, l1=8.5, w=2.4, a0=14, a1=26, covert=(3.4, 2)),
                                             dict(n=3, l0=8.5, l1=9.5, w=2.4, a0=30, a1=50, covert=(3.4, 2))], 0),
            ("hw", 1, 3.6, [3.0, 3.4, 2.6], [dict(n=3, l0=4, l1=5, w=2.2, a0=4, a1=12, covert=(2.6, 2)),
                                             dict(n=3, l0=5.5, l1=6.5, w=2.2, a0=14, a1=26, covert=(2.8, 2)),
                                             dict(n=2, l0=6.5, l1=7, w=2.2, a0=30, a1=46)], 0)):
        for sd, sx in (("r", 1), ("l", -1)):
            w = feather_wing(m, f"{nm}_{sd}", torso[1] if nm == "fw" else torso[0], (sx * 1.0, y, 1.0), sx, segs, rows,
                             bm, fA, cov, arm_thick=0.9, tip_feathers=dict(n=3, l=rows[-1]["l1"] + 0.5, w=2.4, a0=56, a1=86))
            wings[f"{nm}_{sd}"] = w
    tl = chain(m, "mtl", grow, [(0, 0.6, 2.0), (0, 1.6, 4.5), (0, 3.4, 6.8)], 0.7, bm)
    fan = m.bone("mfan", tl[-1], pivot=(0, 3.4, 6.8))
    for k in range(5):
        a = -40 + k * 20
        fan.cube((-1.1, 3.4, 6.8), (2.2, 7.0, 0), fA[k % 2], rot=(-30, 0, a + 180), pivot=(0, 3.4, 6.8), variant=k % 3)
    m.bones[torso[-1]].locator("crown", (0, 13.0, 0))
    return dict(kind="micro", chain=torso, wings=wings, tail=tl, extra=[fan.name], call="call_a", fx="feather", loc="crown")


def build_k_slabs(m, grow, C):
    """Four fossil slabs rising out of the page and orbiting, each holding one lineage's skeleton."""
    ring_b = m.bone("fring", grow, pivot=(0, 0, 0))
    slabs = []
    for i, lin in enumerate(LIN):
        hb = m.bone(f"fhold{i}", ring_b, pivot=(0, 0, 0), rot=(0, i * 90 + 45, 0))
        sb = m.bone(f"fslab{i}", hb, pivot=(0, 8.0, -8.5))
        sb.box((0, 8.0, -8.5), (8.0, 9.6, 1.4), tex.stone("#9a8a72", "#5f5446", "#b8a88c", scale=3, cracks=0.25,
                                                          glow_crack=0.7, crack_color=EL[lin][0]),
               mats={"north": fossil_slab(lin, EL[lin][0], f"s{i}")}, density=2.4, variant=i % 3)
        sb.box((0, 3.0, -8.5), (5.0, 0.8, 1.0), tex.stone("#7a6c58", "#4a4136", "#968670", scale=2, cracks=0.2), variant=i % 2)
        slabs.append(sb.name)
    m.bones[ring_b.name].locator("core", (0, 7, 0))
    core = m.bone("fcore", grow, pivot=(0, 6, 0))
    for i, lin in enumerate(LIN):
        core.box((0, 6, 0), (1.2, 4.2, 1.2), tex.crystal(EL[lin][0], EL[lin][1], a=0.8, glow=0.6), rot=(0, i * 45, 22),
                 pivot=(0, 6, 0), variant=i)
    return dict(kind="slabs", chain=[], slabs=slabs, ring=ring_b.name, extra=[core.name], call="call_f", fx="grit", loc="core")


def build_k_skulls(m, grow, C):
    """Four skulls together: the four lineage skulls on vertebral stalks fanned toward the reader."""
    heads = []
    for i, lin in enumerate(LIN):
        yaw = (-84, -28, 28, 84)[i]
        hb = m.bone(f"khold{i}", grow, pivot=(0, 0.5, 0), rot=(0, yaw, 0))
        bm = tex.bone_mat(EL[lin][2], IVORY_SH, glow=0.12)
        h0 = (6.0, 10.5, 10.5, 6.0)[i]
        stalk = chain(m, f"kst{i}_", hb, [(0, 0.5, -2.0), (0, h0 * 0.5, -4.0), (0, h0, -5.6)], 1.2, bm)
        s = {"n": 2.6, "h": 2.5, "w": 2.1, "a": 3.0}[lin]
        sk, jaw = skull(m, lin, f"k{i}_", stalk[-1], (0, h0 - 0.8, -5.0), s, face=(-6, 0, 0), bone_mat=bm)
        heads.append(dict(hold=hb.name, stalk=stalk, skull=sk, jaw=jaw))
    core = m.bone("kcore", grow, pivot=(0, 4, 0))
    for i, lin in enumerate(LIN):
        core.box((0, 4.5, 0), (1.0, 4.4, 1.0), tex.crystal(EL[lin][0], EL[lin][1], a=0.8, glow=0.7), rot=(0, i * 45, 18),
                 pivot=(0, 4.5, 0), variant=i)
    core.locator("core", (0, 7, 0))
    return dict(kind="skulls", chain=[], heads=heads, extra=[core.name], call="call_all", fx="burst_small", loc="core")


def build_charge_anims(kinfo):
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    life = Anim("life", loop=True)
    life.pos("stage", (0, LIFE(0.5, 3.0), 0))
    life.rot("stage", (LIFE(1.5, 4.4), LIFE(2.0, 6.0, 0.3), 0))
    life.rot("circle", (0, M("q.life_time * 30", lambda t: t * 30), 0))
    life.rot("runes", (0, M("q.life_time * -45", lambda t: -t * 45), 0))
    life.rot("cleaf_l", (0, 0, LIFE(4, 1.7, 0, 3)))
    life.rot("cleaf_r", (0, 0, LIFE(4, 1.9, 0.3, -3)))
    A.append(life)

    form = Anim("form", length=FORM_LEN, loop="hold")
    form.scl("root", {0: 0.15, 0.22: 1.06, 0.36: 1.0})
    form.rot("root", {0: (0, -70, 0), 0.3: (0, 4, 0), 0.45: (0, 0, 0)})
    form.rot("half_l", {0: (0, 0, -84), 0.16: (0, 0, -84), 0.42: (0, 0, 4), 0.52: (0, 0, 0)})
    form.rot("half_r", {0: (0, 0, 84), 0.16: (0, 0, 84), 0.42: (0, 0, -4), 0.52: (0, 0, 0)})
    form.scl("circle", {0: 0.0, 0.2: 0.0, 0.6: 1.12, 0.8: 1.0})
    form.scl("runes", {0: 0.0, 0.4: 0.0, 0.8: 1.1, 1.0: 1.0})
    form.pos("grow", {0: (0, -5, 0), 0.38: (0, -5, 0), 1.25: (0, 0.4, 0), 1.5: (0, 0, 0)})
    form.scl("grow", {0: 0.0, 0.36: 0.0, 0.42: 0.3, 1.25: 1.04, 1.5: 1.0})
    for c in ("cclasp_n", "cclasp_h", "cclasp_w", "cclasp_a"):
        form.rot(c, {0: (0, 0, 0), 0.3: (0, 0, 0), 0.5: (25, 0, 0), 0.62: (0, 0, 0)})
    A.append(form)

    rel = Anim("release", length=RELEASE_LEN, loop="hold")
    rel.scl("grow", {0: 1.0, 0.12: 1.25, 0.3: 1.45, 0.5: 0.0})
    rel.pos("grow", {0: (0, 0, 0), 0.3: (0, 3, 0), 0.5: (0, 9, 0)})
    rel.scl("circle", {0: 1.0, 0.15: 1.7, 0.5: 0.0})
    rel.scl("runes", {0: 1.0, 0.2: 1.6, 0.45: 0.0})
    rel.rot("half_l", {0: (0, 0, 0), 0.12: (0, 0, 12), 0.5: (0, 0, -60)})
    rel.rot("half_r", {0: (0, 0, 0), 0.12: (0, 0, -12), 0.5: (0, 0, 60)})
    rel.scl("root", {0: 1.0, 0.3: 1.06, 0.5: 0.0})
    A.append(rel)

    can = Anim("cancel", length=CANCEL_LEN, loop="hold")
    can.pos("grow", {0: (0, 0, 0), 0.3: (0, -7, 0)})
    can.scl("grow", {0: 1.0, 0.28: 0.1, 0.32: 0.0})
    can.rot("half_l", {0: (0, 0, 0), 0.12: (0, 0, 0), 0.34: (0, 0, -84)})
    can.rot("half_r", {0: (0, 0, 0), 0.12: (0, 0, 0), 0.34: (0, 0, 84)})
    can.scl("circle", {0: 1.0, 0.3: 0.0})
    can.scl("runes", {0: 1.0, 0.2: 0.0})
    can.scl("root", {0: 1.0, 0.3: 0.9, 0.4: 0.0})
    A.append(can)

    for k, ki in enumerate(kinfo):
        f = Anim(f"form_k{k}", length=FORM_LEN, loop="hold")
        lp = Anim(f"loop_k{k}", length=4.0, loop=True)
        kind = ki["kind"]
        if ki["chain"]:
            n = len(ki["chain"])
            for i, b in enumerate(ki["chain"]):
                t0 = 0.4 + 0.8 * i / max(1, n - 1)
                f.scl(b, {0: 0.0, t0: 0.0, t0 + 0.1: 1.15, t0 + 0.18: 1.0})
                f.rot(b, {0: (0, 0, 0), t0: (14, 0, -10), t0 + 0.22: (0, 0, 0)})
        for e in ki["extra"]:
            f.scl(e, {0: 0.0, 0.5: 0.0, 0.75: 1.1, 0.9: 1.0})
        f.sound(0.55, ki["call"])
        f.particle(0.6, ki["fx"], locator=ki["loc"])
        if kind == "neck":
            f.scl(ki["skull"], {0: 0.0, 1.15: 0.0, 1.28: 1.2, 1.4: 1.0})
            f.rot(ki["skull"], {0: (0, 0, 0), 1.2: (-30, 0, 0), 1.5: (0, 0, 0)})
            wave(lp, ki["chain"], 2, 3.0, 4.0, lag=0.08)
            wave(lp, ki["chain"], 0, 2.0, 4.0, lag=0.1)
            lp.rot(ki["skull"], {0: (0, 0, 0), 1.0: (12, 25, 0), 2.0: (20, 0, 0), 3.0: (8, -25, 0), 4.0: (0, 0, 0)})
            lp.rot(ki["jaw"], {0: (0, 0, 0), 1.6: (0, 0, 0), 1.8: (-18, 0, 0), 2.2: (0, 0, 0)})
            lp.particle(1.8, "leaf", locator="head")
            lp.particle(3.6, "leaf", locator="head")
        elif kind == "carno":
            f.scl(ki["skull"], {0: 0.0, 0.85: 0.0, 1.05: 1.25, 1.25: 1.0})
            f.rot(ki["jaw"], {0: (0, 0, 0), 1.05: (-26, 0, 0), 1.3: (12, 0, 0), 1.5: (0, 0, 0)})
            for half in (0.0, 2.0):
                lp.rot(ki["jaw"], {half: (0, 0, 0), half + 0.5: (-22, 0, 0), half + 0.8: (-24, 0, 0), half + 0.95: (12, 0, 0),
                                   half + 1.2: (0, 0, 0)} if half == 0 else
                       {0: (0, 0, 0), 0.5: (-22, 0, 0), 0.8: (-24, 0, 0), 0.95: (12, 0, 0), 1.2: (0, 0, 0),
                        2.5: (-22, 0, 0), 2.8: (-24, 0, 0), 2.95: (12, 0, 0), 3.2: (0, 0, 0), 4.0: (0, 0, 0)})
            lp.rot(ki["skull"], {0: (0, 0, 0), 0.8: (-8, 8, 0), 0.95: (4, 0, 0), 2.0: (0, -6, 0), 2.8: (-8, -10, 4),
                                 2.95: (4, 0, 0), 4.0: (0, 0, 0)})
            lp.scl("ch_throat", S(0.25, 1.0, 0, 1.0))
            lp.scl("cvents", S(0.04, 2.0, 0, 1.0))
            for t in (0.95, 2.95):
                lp.particle(t, "ember", locator="maw")
        elif kind == "spino":
            f.scl(ki["sail"], {0: 0.0, 0.5: 0.0, 0.62: 0.3, 1.1: 1.08, 1.3: 1.0})
            f.pos(ki["sail"], {0: (0, -8, 0), 0.5: (0, -8, 0), 1.2: (0, 0, 0)})
            wave(lp, ki["chain"], 2, 7.0, 2.0, lag=0.12, grow=1.1)
            wave(lp, ki["chain"], 1, 9.0, 4.0, lag=0.1)
            for i, sp in enumerate(ki["spines"]):
                lp.rot(sp, (0, 0, S(3.0, 2.0, -i * 0.08)))
            lp.rot(ki["sail"], (S(2.0, 4.0), 0, 0))
            lp.scl("swater", S(0.05, 2.0, 0, 1.0))
            lp.particle(0.5, "drop", locator="tip")
            lp.particle(2.5, "drop", locator="tip")
        elif kind == "micro":
            for wn, w in ki["wings"].items():
                a1 = w["arms"][0]
                fwd = wn.startswith("fw")
                sg = 1 if wn.endswith("_r") else -1
                f.rot(a1, {0: (0, 0, sg * -70), 0.7: (0, 0, sg * -70), 1.2: (0, 0, sg * 8), 1.5: (0, 0, 0)})
                period, ph = 1.0, (0.0 if fwd else 0.5)
                lp.rot(a1, (0, S(6, period, ph + 0.1), S(26 * sg, period, ph, sg * (22 if fwd else -18))))
                lp.rot(w["arms"][1], (0, 0, S(12 * sg, period, ph - 0.12)))
                lp.rot(w["arms"][2], (0, 0, S(10 * sg, period, ph - 0.24)))
                flutter(lp, w["feathers"], amp=3.0, period=1.0, clock="q.anim_time")
            wave(lp, ki["tail"], 0, 6, 2.0, lag=0.15)
            lp.pos(ki["chain"][0], (0, S(0.6, 1.0, 0.25), 0))
            lp.particle(0.4, "feather", locator="crown")
            lp.particle(2.4, "feather", locator="crown")
        elif kind == "slabs":
            for i, sb in enumerate(ki["slabs"]):
                t0 = 0.45 + i * 0.15
                f.scl(sb, {0: 0.0, t0: 0.0, t0 + 0.12: 1.12, t0 + 0.2: 1.0})
                f.pos(sb, {0: (0, -9, 0), t0: (0, -9, 0), t0 + 0.35: (0, 0.5, 0), t0 + 0.5: (0, 0, 0)})
                lp.pos(sb, (0, S(0.8, 2.0, i * 0.25), 0))
                lp.rot(sb, (S(4, 4.0, i * 0.25), S(8, 4.0, i * 0.25 + 0.1), 0))
            f.rot(ki["ring"], {0: (0, -90, 0), 1.5: (0, 0, 0)})
            lp.rot(ki["ring"], {0: (0, 0, 0), 4.0: (0, 90, 0)}, smooth=False)
            lp.rot("fcore", (0, M("q.anim_time * 90", lambda t: t * 90), 0))
            lp.particle(1.0, "grit", locator="core")
            lp.particle(3.0, "grit", locator="core")
        elif kind == "skulls":
            for i, h in enumerate(ki["heads"]):
                t0 = 0.5 + i * 0.16
                f.scl(h["hold"], {0: 0.0, t0: 0.0, t0 + 0.12: 1.15, t0 + 0.2: 1.0})
                f.rot(h["skull"], {0: (0, 0, 0), t0 + 0.1: (-40, 0, 0), t0 + 0.4: (0, 0, 0)})
                f.rot(h["jaw"], {0: (0, 0, 0), t0 + 0.25: (-25, 0, 0), t0 + 0.45: (0, 0, 0)})
                o = i * 1.0
                lp.rot(h["jaw"], {0: (0, 0, 0), o + 0.2: (0, 0, 0), o + 0.45: (-24, 0, 0), o + 0.7: (4, 0, 0), o + 0.85: (0, 0, 0),
                                  4.0: (0, 0, 0)})
                lp.rot(h["skull"], {0: (0, 0, 0), o + 0.2: (0, 0, 0), o + 0.45: (-12, 0, 0), o + 0.85: (0, 0, 0), 4.0: (0, 0, 0)})
                lp.pos(h["hold"], (0, S(0.5, 2.0, i * 0.25), 0))
                lp.rot(h["stalk"][0], (S(3, 4.0, i * 0.2), 0, S(3, 4.0, i * 0.2 + 0.3)))
            lp.rot("kcore", (0, M("q.anim_time * 90", lambda t: t * 90), 0))
            lp.particle(0.5, "burst_small", locator="core")
        A.append(f)
        A.append(lp)
    return A


# =====================================================================================
#                                  PARTICLES / SOUNDS / ICON
# =====================================================================================
def build_particles(pack):
    fx = particles(pack)
    fx.effect("book_ed_mote", "rune1", sprites=["rune1", "rune2", "rune3", "rune4", "rune5", "rune6", "scale", "dot"],
              count=4, life=(0.8, 1.6), size=(0.09, 0.0), shape=("sphere", 0.9), speed=(0.1, 0.45), accel=(0, 0.55, 0),
              drag=1.2, colors=["#ffe7b0ff", "#e0762acc", "#8a6a3a00"], spin=(360, 40))
    fx.effect("book_ed_burst", "bone", sprites=["bone", "scale", "rune2", "rune4", "spark", "ember", "leaf", "flake"],
              count=40, life=(0.5, 1.3), size=(0.17, 0.0), shape=("sphere", 0.5), speed=(3.0, 7.5), drag=3.2,
              accel=(0, -0.6, 0), colors=["#fff6dcff", "#ffb060ee", "#7fd6ffaa", "#8a6a3a00"], spin=(360, 220))
    fx.effect("book_ed_leaf", "leaf", count=6, life=(1.0, 1.8), size=(0.1, 0.06), shape=("sphere", 0.5), speed=(0.3, 0.9),
              accel=(0, -0.6, 0), drag=1.5, colors=["#9be35fff", "#4f8a30ff", "#3f6a2a00"], blend="blend", spin=(360, 160))
    fx.effect("book_ed_ember", "ember", count=10, life=(0.5, 1.1), size=(0.07, 0.0), shape=("sphere", 0.4), speed=(0.6, 1.8),
              accel=(0, 1.4, 0), drag=1.0, colors=["#fff0b0ff", "#ff8a2aff", "#7a2a1000"])
    fx.effect("book_ed_drop", "drop", sprites=["drop", "flake", "dot"], count=8, life=(0.6, 1.2), size=(0.08, 0.03),
              shape=("sphere", 0.4), speed=(0.6, 1.6), accel=(0, -3.0, 0), drag=0.6, colors=["#e8f6ffff", "#7fd6ffdd", "#2f6fd600"])
    fx.effect("book_ed_feather", "feather", count=5, life=(1.0, 1.8), size=(0.12, 0.08), shape=("sphere", 0.5),
              speed=(0.4, 1.1), accel=(0, -0.4, 0), drag=2.0, colors=["#ffffffff", "#cfe6ffee", "#a9c3d900"], blend="blend",
              spin=(360, 120))
    fx.effect("book_ed_grit", "rock", sprites=["rock", "puff", "bone"], count=10, life=(0.6, 1.3), size=(0.09, 0.04),
              shape=("sphere", 0.6), speed=(0.3, 1.2), accel=(0, -1.5, 0), drag=1.4,
              colors=["#d8c7a0ff", "#9a8a72dd", "#5f544600"], blend="blend", spin=(360, 90))
    fx.effect("book_ed_spark", "spark", sprites=["spark", "rune3", "rune5", "scale"], count=12, life=(0.4, 0.9),
              size=(0.1, 0.0), shape=("sphere", 0.3), speed=(1.0, 2.6), drag=2.2,
              colors=["#ffffffff", "#ffe2a0ff", "#9be35fcc", "#7fd6ff00"])


def _env_t(n, a, r):
    e = np.ones(n)
    an, rn = int(a * sy.SR), int(r * sy.SR)
    e[:an] = np.linspace(0, 1, max(an, 1))[:an]
    if rn:
        e[-rn:] *= np.linspace(1, 0, rn)
    return e


def riffle(dur=0.4, flicks=7, lo=1800, hi=5200):
    out = np.zeros(int(sy.SR * dur))
    for k in range(flicks):
        L = 0.03 + 0.02 * (k % 3)
        seg_ = sy.bandpass(sy.noise(L), lo + (hi - lo) * (k / flicks), 1.3) * np.hanning(int(sy.SR * L))
        i = int(sy.SR * dur * k / flicks * 0.9)
        out[i:i + len(seg_)] += seg_[:len(out) - i]
    return sy.norm(out)


def bone_clack(f=420, dur=0.18):
    t = sy.t_axis(dur)
    body = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t)) * np.exp(-t / 0.025)
    click = sy.highpass(sy.noise(dur), 2500) * np.exp(-t / 0.004)
    return sy.norm(body + click * 0.6)


def build_sounds(pack):
    # select: dry page riffle, two bone clacks and a low breath (the Codex stirring)
    sel = sy.at(1.2, (0.0, riffle(0.42), 0.8), (0.18, bone_clack(380), 0.5), (0.3, bone_clack(560), 0.4),
                (0.25, sy.roar(0.75, f0=62, f1=48, growl=14, rough=0.35, formant=(330, 820), breath=0.7, bend=0.1), 0.45))
    sy.save(pack, "book_ed_select", sy.reverb(sel, 0.9, 0.22, tone=3500), volume=0.9, max_distance=24)
    sy.save(pack, "book_ed_flip", riffle(0.3, 5, 1500, 4200) * 0.8, volume=0.35, max_distance=10)
    # charge: ~2 s swell -- rising geological rumble, a slow growling inhale, quickening bone rattle
    n = int(sy.SR * 2.1)
    ramp = np.linspace(0, 1, n) ** 1.6
    rat = np.zeros(n)
    for k in range(22):
        tt = (k / 22) ** 0.6 * 1.9
        c = bone_clack(300 + 40 * (k % 5), 0.12) * (0.2 + 0.8 * tt / 1.9)
        i = int(sy.SR * tt)
        rat[i:i + len(c)] += c[:n - i]
    ch = (sy.rumble(2.1, fc=48, wobble=2.0) * 0.8 + sy.roar(2.1, f0=42, f1=84, growl=12, rough=0.4, formant=(300, 700),
                                                            breath=0.6, bend=0.05) * 0.7) * ramp + rat * 0.35
    ch += sy.at(2.1, (1.4, sy.shimmer(0.7, 900, 10, 2.0) * 0.25))[:n]
    sy.save(pack, "book_ed_charge", sy.reverb(ch, 1.1, 0.25, tone=3000), volume=0.9, max_distance=24)
    # release: the manifestation breaks free -- whoosh, primal bark, impact, splitting bone/stone
    rel = sy.at(1.6, (0.0, sy.whoosh(0.45, 200, 2600), 0.7), (0.08, sy.roar(0.9, f0=118, f1=66, growl=30, rough=0.65,
                                                                            formant=(520, 1250), breath=0.45), 0.9),
                (0.1, sy.thump(0.8, 92, 32, 0.5), 1.0), (0.12, sy.crack(0.6, 3800, 18), 0.5))
    sy.save(pack, "book_ed_release", sy.reverb(rel, 1.3, 0.3, tone=4200), volume=1.0, max_distance=32)
    # deny: the clasps refuse -- dull bony knock and a short descending grumble
    den = sy.at(0.7, (0.0, sy.thump(0.35, 84, 40, 0.7), 0.9), (0.02, bone_clack(240, 0.15), 0.5),
                (0.08, sy.roar(0.5, f0=66, f1=40, growl=18, rough=0.7, formant=(300, 640), breath=0.3, bend=0.0), 0.6))
    sy.save(pack, "book_ed_deny", den, volume=0.7, max_distance=16)
    # lineage calls for the vision / construct
    call_n = sy.at(1.0, (0.0, sy.roar(0.95, f0=46, f1=36, growl=9, rough=0.25, formant=(250, 560), breath=0.3, bend=0.15), 1.0),
                   (0.02, sy.thump(0.5, 70, 28, 0.4), 0.7), (0.3, sy.rumble(0.7, 50) * 0.5))
    call_h = sy.at(0.9, (0.0, sy.roar(0.7, f0=135, f1=86, growl=34, rough=0.8, formant=(620, 1450), breath=0.5), 1.0),
                   (0.35, sy.highpass(sy.noise(0.5), 3000) * sy.env(0.5, 0.05, 0.1, 0.6, 0.3) * 0.5))
    tb = sy.t_axis(0.8)
    hum = sy.bandpass(sy.noise(0.8), 180, 6) * np.exp(-tb / 0.4) * 2
    call_w = sy.at(0.9, (0.0, sy.water(0.8, bubbles=26, base=380), 0.7), (0.05, sy.bell(1250, 0.75, inharm=1.3), 0.35),
                   (0.25, sy.crack(0.4, 7000, 8), 0.3), (0.0, hum, 0.6))
    chirp = sy.osc(sy.sweep(1700, 3300, 0.18, 0.6)) * sy.env(0.18, 0.01, 0.05, 0.6, 0.08)
    chirp2 = sy.osc(sy.sweep(2600, 1900, 0.14)) * sy.env(0.14, 0.01, 0.04, 0.6, 0.06)
    flap = sy.bandpass(sy.noise(0.6), 900, 1.2) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 14 * sy.t_axis(0.6))))
    call_a = sy.at(0.9, (0.0, chirp, 0.6), (0.2, chirp2, 0.5), (0.1, sy.whoosh(0.6, 700, 3600), 0.5), (0.05, flap * 0.35))
    call_f = sy.at(1.0, (0.0, sy.rumble(0.9, 60), 0.6), (0.05, sy.crack(0.9, 1600, 26), 0.6), (0.0, sy.thump(0.5, 80, 34, 0.6), 0.6))
    for nm, sig in (("n", call_n), ("h", call_h), ("w", call_w), ("a", call_a), ("f", call_f)):
        sy.save(pack, f"book_ed_call_{nm}", sy.reverb(sig, 0.8, 0.2), volume=0.7, max_distance=20)
    allc = sy.at(1.2, (0.0, sy.pitch(call_n, 1.3)[:int(sy.SR * 0.5)], 0.7), (0.15, call_h[:int(sy.SR * 0.45)], 0.6),
                 (0.3, call_w[:int(sy.SR * 0.45)], 0.6), (0.42, call_a[:int(sy.SR * 0.5)], 0.6))
    sy.save(pack, "book_ed_call_all", sy.reverb(allc, 0.9, 0.25), volume=0.75, max_distance=20)


ACTOR_SOUNDS = {f"call_{k}": f"grimoire.book_ed_call_{k}" for k in ("n", "h", "w", "a", "f", "all")}
ACTOR_PARTICLES = {"leaf": "grimoire:book_ed_leaf", "ember": "grimoire:book_ed_ember", "drop": "grimoire:book_ed_drop",
                   "feather": "grimoire:book_ed_feather", "grit": "grimoire:book_ed_grit", "burst_small": "grimoire:book_ed_spark"}


def write_icon(pack, m):
    img = render(m, None, yaw=28, pitch=12, size=(32, 32), bg=(0, 0, 0, 0), ss=6, margin=0.02, hide=("halo",))
    p = os.path.join(pack.rp, "textures", "items", "grimoire_elemental_dragon.png")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    img.save(p)
    return img


# =====================================================================================
#                                     PREVIEWS
# =====================================================================================
def _merge(poses):
    out = {}
    for a, t in poses:
        for b, (r, pp, s) in a.pose(t).items():
            if b in out:
                r0, p0, s0 = out[b]
                out[b] = (tuple(r0[i] + r[i] for i in range(3)), tuple(p0[i] + pp[i] for i in range(3)),
                          tuple(s0[i] * s[i] for i in range(3)))
            else:
                out[b] = (r, pp, s)
    return out


def _grid(pack, name, rows, cell=300):
    """rows: [[(model, [(anim, t), ...], (yaw, pitch)), ...], ...] -> one PNG."""
    if not getattr(pack.preview, "enabled", False):
        return
    from PIL import Image
    from kit.pack import PREVIEW
    nr, nc = len(rows), max(len(r) for r in rows)
    out = Image.new("RGBA", (cell * nc, cell * nr), (34, 38, 46, 255))
    for i, row in enumerate(rows):
        for j, (m, poses, (yaw, pitch)) in enumerate(row):
            out.paste(render(m, _merge(poses) if poses else None, yaw=yaw, pitch=pitch, size=(cell, cell)), (j * cell, i * cell))
    os.makedirs(PREVIEW, exist_ok=True)
    out.save(os.path.join(PREVIEW, f"{name}.png"))


# =====================================================================================
def build(pack):
    build_particles(pack)
    build_sounds(pack)

    book, binfo = build_book()
    banims = build_book_anims(binfo)
    write_attachable(pack, book, banims)
    write_icon(pack, book)
    print(f"    book_ed: {book.cube_count()} cubes, {len(book.order)} bones, tex {book.tex_size}")

    vmodels, vinfo = build_vision()
    vanims = build_vision_anims(vinfo)
    vstates = {0: ["hidden"], 1: ["show"] + [{f"show_k{k}": f"q.property('grimoire:kind') == {k}"} for k in range(6)]}
    pack.actor("book_ed_vision", vmodels[0], vanims, vstates, kinds=vmodels[1:], lifetime=30, blend=0.0,
               sounds=ACTOR_SOUNDS, particles=ACTOR_PARTICLES, display="Codex Vision")
    cmodels, cinfo = build_charge()
    canims = build_charge_anims(cinfo)
    gate = lambda pre: [{f"{pre}_k{k}": f"q.property('grimoire:kind') == {k}"} for k in range(6)]  # noqa: E731
    cstates = {0: ["hidden"], 1: ["form"] + gate("form"), 2: gate("loop"), 3: ["release"], 4: ["cancel"]}
    pack.actor("book_ed_charge", cmodels[0], canims, cstates, kinds=cmodels[1:], always=["life"], lifetime=120,
               sounds=ACTOR_SOUNDS, particles=ACTOR_PARTICLES, display="Codex Manifestation")
    for k, (vm, cm) in enumerate(zip(vmodels, cmodels)):
        print(f"    vision k{k}: {vm.cube_count()} cubes {len(vm.order)} bones tex {vm.tex_size} | "
              f"charge k{k}: {cm.cube_count()} cubes {len(cm.order)} bones tex {cm.tex_size}")

    # ---------------- previews
    by = {a.name: a for a in banims}
    idle = (by["idle"], 1.3)
    shut = (by["closed"], 0)
    _grid(pack, "book_ed_held", [
        [(book, [idle, shut], (25, 15)), (book, [idle, shut], (-35, 10)), (book, [idle, shut], (155, 15)),
         (book, [idle, shut], (90, 5))],
        [(book, [(by["turn"], 0.5), idle, shut], (25, 15)), (book, [(by["turn"], 0.75), idle, shut], (-30, 20)),
         (book, [(by["open"], 0.75), (by["open_loop"], 0.5), idle], (5, 10)),
         (book, [(by["open"], 0.75), (by["open_loop"], 1.1), idle], (-40, 30))],
    ], cell=320)
    vb = {a.name: a for a in vanims}
    _grid(pack, "book_ed_vision", [
        [(vmodels[k], [(vb["show"], t), (vb[f"show_k{k}"], t)], (20, 15)) for t in (0.3, 0.55, 0.8)]
        + [(vmodels[k], [(vb["show"], 0.7), (vb[f"show_k{k}"], 0.7)], (-60, 25))] for k in range(6)], cell=260)
    cb = {a.name: a for a in canims}
    _grid(pack, "book_ed_charge", [
        [(cmodels[k], [(cb["form"], 0.8), (cb[f"form_k{k}"], 0.8)], (20, 15)),
         (cmodels[k], [(cb["form"], 1.5), (cb[f"form_k{k}"], 1.5), (cb[f"loop_k{k}"], 0.9)], (20, 15)),
         (cmodels[k], [(cb["form"], 1.5), (cb[f"form_k{k}"], 1.5), (cb[f"loop_k{k}"], 2.6)], (-55, 20)),
         (cmodels[k], [(cb["cancel"], 0.2)], (20, 15))] for k in range(6)], cell=260)
