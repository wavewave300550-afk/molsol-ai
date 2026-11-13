"""Grimoire 01 -- Codex of the First Word (Divine Word book, worker M1).

Builds
  * the held attachable for grimoire:divine_word (geometry book_dw, idle / page-turn / open-and-rise)
  * actor book_dw_vision  -- selection vision (6 kinds): a page turns, a fresh sentence is written by an
                             invisible author and the selected spell's emblem rises and lights
  * actor book_dw_charge  -- charge construct (6 kinds): lines of writing rise and assemble into large
                             3D words while the spell's celestial emblem unfolds
  * particles book_dw_mote / book_dw_burst, sounds book_dw_select / _charge / _release / _deny
  * inventory icon, textures/item_texture.json (all three books) and both pack_icon.png files

Text-to-reality is the animation language: everything here is written, rises, assembles, ignites.
All lettering uses the invented script glyphs.FIRST_WORD.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from kit import glyphs, synth as sy, tex
from kit.anim import LIFE, Anim, M, animations_file
from kit.geo import Mat, Model, ring
from kit.pack import _write
from kit.render import render

from .a_fx_common import particles

# =====================================================================================================
# HELD-BOOK PLACEMENT -- the only numbers to tune after an in-game look (bb space: +X = the holder's
# right, +Y up, -Z = the holder's forward; units 1/16 block; degrees).  The attachable root bone is bound
# to the hand item bone, whose space is the player model's space (right hand ~ (6, 12..15, 1)).
# The book is modelled upright, centred on its own origin, cover facing -Z, spine on +X.
#   ROT (rx, ry, rz): ry 180 turns the cover/pages toward the caster; rx tips the page face upward.
#   OPEN_*: added while Use is held (book opens, rises and tilts up to be read).
# =====================================================================================================
TP_POS = (9.5, 19.0, -5.5)        # third person: beside and above the right hand, a little forward
TP_ROT = (18.0, 180.0, -8.0)
TP_SCALE = 0.55                   # 14-unit tall model -> ~0.48 block book (38 x 28 x 8 cm)
TP_OPEN_POS = (-2.5, 4.0, -2.5)   # rises toward the chest line when charging
TP_OPEN_ROT = (34.0, 0.0, 8.0)

FP_POS = (5.0, 21.0, -9.0)        # first person: up and right of the hand, clear of the crosshair
FP_ROT = (20.0, 196.0, -6.0)
FP_SCALE = 0.42
FP_OPEN_POS = (-1.5, 2.5, -1.0)
FP_OPEN_ROT = (26.0, -8.0, 6.0)

OPEN_RATE = 3.0                   # how fast the book closes again after Use is released (1/s)
OPEN_TICKS = 8.0                  # held ticks until fully open
# =====================================================================================================

IVORY, GOLD, WGOLD, SILVER, BLUE = "#f5f0e1", "#c9a24a", "#fff3c4", "#d8dde3", "#2b3f8f"
FW = glyphs.FIRST_WORD
G = "dw"
ITEM = "divine_word"

# actor state tables (mirrored in src/config/books.ts)
VISION_STATES = {0: ["hidden"], 1: ["show"]}
CHARGE_STATES = {0: ["hidden"], 1: ["form"], 2: ["loop"], 3: ["release"], 4: ["cancel"]}
VISION_LEN, FORM_LEN, RELEASE_LEN, CANCEL_LEN = 1.2, 1.5, 0.5, 0.4

PV = {"open": 0.0}  # preview twin for Molang v.open


# ----------------------------------------------------------------------------------------- materials
def pearl(base=IVORY, vein="#e0d8c4", key="pearl"):
    """Polished ancient marble with a faint pearlescent sheen."""
    marb = tex.marble(base, vein, vein2="#d3dcea", scale=6.0, edge_dark=0.05)

    def fn(ctx):
        t = np.array(marb.fn(ctx), dtype=float)
        ph = (ctx.U * 1.6 + ctx.V * 1.1 + ctx.variant * 0.37) * 2 * math.pi
        t[..., 0] += 0.025 * np.sin(ph)
        t[..., 1] += 0.012 * np.sin(ph + 2.1)
        t[..., 2] += 0.035 * np.sin(ph + 4.2)
        t[..., :3] = np.clip(t[..., :3], 0, 1)
        return t
    return Mat(fn, f"{key}{base}{vein}")


def cover_face():
    """Front cover: pearl marble with a band of engraved gold inscription inside the frame."""
    base = pearl(key="pearlcov")

    def fn(ctx):
        t = np.array(base.fn(ctx), dtype=float)
        ix, iy = tex.px(ctx)
        d = np.minimum(np.minimum(ix, ctx.w - 1 - ix), np.minimum(iy, ctx.h - 1 - iy))
        band = (d >= 4) & (d <= 6)
        cx, cy = ix // 2, iy // 3
        mark = (tex._hash(cx, cy, 5) < 0.62) & (((ix + iy * 3) % 5) != 0) & ((iy % 3) != 2)
        on = band & mark
        t[..., :3] = np.where(on[..., None], tex.rgb("#b88c34"), t[..., :3])
        t[..., 4] = np.where(on, 0.35, t[..., 4])
        rule = (d == 3) | (d == 7)
        t[..., :3] = np.where(rule[..., None], tex.rgb("#d9b45a"), t[..., :3])
        t[..., 4] = np.where(rule, 0.2, t[..., 4])
        return t
    return Mat(fn, "dwcoverface", directional=True)


def page_edge():
    """Gilded page block edge: fine leaves running parallel to the covers."""
    def fn(ctx):
        t = tex.tile(ctx, "#d6b05a", 1, 0.15)
        leaf = (np.floor(ctx.Z * 6.0) % 2 == 0)
        t[..., :3] = np.where(leaf[..., None], tex.rgb("#e8c873"), tex.rgb("#b8913f"))
        return tex.grain(ctx, t, 0.04)
    return Mat(fn, "dwpageedge", spatial=True)


def page_text(ink="#7a5a24", glow=0.0, bg="#f3e8cb", key="dwpage"):
    """Warm ivory page with lines of First Word text, margins and a fine gilt rule."""
    rows = tex.glyph_rows(FW, ink, glow=glow, bg=bg, fill=0.78, key=key + "rows")

    def fn(ctx):
        t = np.array(rows.fn(ctx), dtype=float)
        ix, iy = tex.px(ctx)
        d = np.minimum(np.minimum(ix, ctx.w - 1 - ix), np.minimum(iy, ctx.h - 1 - iy))
        margin = d < 3
        t[..., :3] = np.where(margin[..., None], tex.rgb(bg), t[..., :3])
        t[..., 4] = np.where(margin, 0.0, t[..., 4])
        gilt = d == 1
        t[..., :3] = np.where(gilt[..., None], tex.rgb("#c9a24a"), t[..., :3])
        t[..., 3] = 1.0
        sh = 1 - 0.08 * np.abs(ctx.U - 0.5) * 2
        t[..., :3] *= sh[..., None]
        return t
    return Mat(fn, key, directional=True)


def parchment(key="dwparch"):
    def fn(ctx):
        t = tex.tile(ctx, "#f6edd3", 1, 0.12)
        n = tex.fbm(ctx.U * 5 + ctx.variant, ctx.V * 5, 7)
        t[..., :3] *= (0.94 + 0.08 * n)[..., None]
        ix, iy = tex.px(ctx)
        d = np.minimum(np.minimum(ix, ctx.w - 1 - ix), np.minimum(iy, ctx.h - 1 - iy))
        t[..., :3] = np.where((d == 1)[..., None], tex.rgb(GOLD), t[..., :3])
        t[..., 4] = np.where(d == 1, 0.5, t[..., 4])
        return tex.grain(ctx, t, 0.03)
    return Mat(fn, key, directional=True)


def M_():
    """Shared material set (created once per build)."""
    gold = tex.metal(GOLD, "#ffe9a3", "#7a5a1e", bands=2.0)
    return dict(
        pearl=pearl(), pearl2=pearl(IVORY, "#d9cfb8", key="pearl2"), cover=cover_face(),
        back=tex.trimmed(pearl(key="pearlback"), "#c9a24a", 1, 2, glow=0.15),
        gold=gold, goldb=tex.metal("#d9b45a", "#fff3c4", "#8a6a26", bands=3.0, glow=0.18),
        goldg=tex.metal("#e9c66a", "#fffbe6", "#a8842e", bands=2.0, glow=0.45),
        silver=tex.metal(SILVER, "#ffffff", "#8a93a3", bands=2.0, glow=0.15),
        wgold=tex.glow_flat(WGOLD, 1.0, core="#ffffff"),
        white=tex.glow_flat("#ffffff", 1.0, core="#ffffff"),
        blue=tex.trimmed(tex.speck(BLUE, 0.06, edge_dark=0.15), GOLD, 1, 0, glow=0.2),
        bluedisc=tex.shaped(tex.m_disc(0.98), "#3a52a8", BLUE, glow=0.25, outline=GOLD, glow_edge=0.6, key="dwbluedisc"),
        edge=page_edge(), page=page_text(), page_lit=page_text("#c9962e", 0.5, "#fbf3dc", key="dwpagelit"),
        fgold=tex.feather("#e6c46a", "#fff3c4", "#a8842e", glow=0.12, glow_tip=0.45, notch=0.0, barbs=True),
        fivory=tex.feather("#fbf8ee", "#f3e3a8", GOLD, glow=0.15, glow_tip=0.6, notch=0.1),
        fwhite=tex.feather("#fffdf4", "#dfe6ff", SILVER, glow=0.3, glow_tip=0.85, notch=0.0),
        flame=tex.shaped(tex.m_leaf(), "#fffbe6", "#ffd060", glow=1.0, var=0, key="dwbflame"),
        diamond=tex.shaped(tex.m_diamond(), "#ffffff", WGOLD, glow=1.0, var=0, key="dwbdiam"),
        ribbon=tex.fabric(BLUE, "#3a52a8", 0.06, 2, fringe=True, glow=0.05),
        eye=tex.eye_mat(iris=BLUE, lid=GOLD, glow=0.9, ring="#9fb4ff"),
        eye_s=tex.eye_mat(iris="#4a64c8", lid=SILVER, glow=0.9, ring="#ffffff"),
        line=tex.glyph_rows(FW, WGOLD, glow=1.0, color2="#ffd76a", fill=0.9, key="dwbline"),
        line_old=tex.glyph_rows(FW, "#8a6a2a", glow=0.15, fill=0.85, key="dwbold"),
        line_new=tex.glyph_rows(FW, "#ffffff", glow=1.0, color2=WGOLD, fill=0.92, key="dwbnew"),
        chevron=tex.bitmap_cut(["#        #", "##      ##", "###    ###", " ###  ### ", "  ######  ", "   ####   ",
                                "    ##    "], "#e9c66a", glow=0.3, color2="#fff3c4", key="dwchev"),
        parch=parchment(),
        glow_disc=tex.shaped(tex.m_disc(1.0), "#ffffff", WGOLD, glow=1.0, var=0, key="dwglowdisc"),
        windows=tex.windowed("#efe8d6", GOLD, "#fff3c4", glow=0.95, cols=2, rows=2, arch=True),
        windows1=tex.windowed("#efe8d6", GOLD, "#fff3c4", glow=0.95, cols=1, rows=2, arch=True),
        rose=tex.magic_circle(FW, WGOLD, GOLD, bands=((0.55, 0.9, 10),), lines=(0.5, 0.95), star=8,
                              star_r=(0.1, 0.5), core=0.12, fill="#2b3f8f", fill_glow=0.35, key="dwrose"),
        letter_front=tex.glow_flat("#ffe596", 0.85, core="#fffaf0"),
        letter_side=tex.metal("#b88c34", "#e9c66a", "#6a4a16", bands=1.0, glow=0.08),
        seal_thin=tex.magic_circle(FW, "#e9c66a", "#a8842e", glow=0.5, bands=((0.86, 0.95, 40),), lines=(0.83, 0.975, 0.6),
                                   key="dwbsealthin"),
    )


# ---------------------------------------------------------------- tiny faces of the four living creatures
FACES = {
    "human": ("#f3ead6", ["     ", " # # ", "     ", " ### ", "     "], "#6a5530"),
    "lion": ("#e0b04a", ["# # #", "     ", " # # ", "  #  ", "# # #"], "#6a4a18"),
    "ox": ("#d8cbb0", ["#   #", "#   #", " # # ", "     ", " ### "], "#5a4a30"),
    "eagle": ("#f7f3ea", [" # # ", "     ", " ### ", " ### ", "  #  "], "#b8862a"),
}


def face_mats():
    out = []
    for name, (base, art, ink) in FACES.items():
        out.append(tex.stamped(tex.porcelain(base, "#c9b88f", crack=0.0, gilt=GOLD), art, ink, glow=0.2,
                               key=f"dwface{name}"))
    return out


# ----------------------------------------------------------------------------------- geometry helpers
def dir_rz(dx, dy):
    """rz that turns the local -Y axis toward direction (dx, dy)."""
    return math.degrees(math.atan2(dx, -dy))


def feathers(b, c, L, W, mats, arm=None, n=3, spread=13.0, r0=None):
    """A small wing pointing along the bone's local -Y from point c (quills at c)."""
    cx, cy, cz = c
    r0 = L * 0.1 if r0 is None else r0
    for k in range(n):
        off = k - (n - 1) / 2
        lk = L * (1.0 - 0.13 * abs(off))
        b.cube((cx - W / 2, cy - r0 - lk, cz + 0.04 * k), (W, lk, 0), mats[k % len(mats)], rot=(0, 0, off * spread),
               pivot=(cx, cy - r0, cz), variant=k % 3)
    if arm is not None:
        b.box((cx, cy - r0 - L * 0.3, cz - 0.15), (W * 0.2, L * 0.6, W * 0.2), arm)


def glyph_plate(b, center, w, h, gi, color=WGOLD, glow=1.0, rot=None, pivot=None, color2="#ffd76a"):
    g = tex.bitmap_cut(FW[gi % len(FW)], color, glow=glow, color2=color2)
    return b.cube((center[0] - w / 2, center[1] - h / 2, center[2]), (w, h, 0), g, rot=rot, pivot=pivot)


# =========================================================================================== emblems
def emblem(kind, m, parent, c, R, mt):
    """The six celestial emblems.  Generic bones so one animation set drives every kind:
    em_core (pulses), em_ring1 (spins in plane), em_ring2 (spins about Y), em_a1..em_a6 (unfold)."""
    cx, cy, cz = c
    core = m.bone("em_core", parent, pivot=c)
    r1 = m.bone("em_ring1", parent, pivot=c)
    r2 = m.bone("em_ring2", parent, pivot=c)
    seg = max(R * 0.07, 0.25)
    if kind == 0:   # SERAPHIM: six symmetrically arranged wings around a flame
        core.plane("z", (cx, cy, cz - seg), R * 0.34, R * 0.55, mt["flame"])
        core.plane("z", (cx, cy - R * 0.05, cz - seg * 1.6), R * 0.18, R * 0.24, mt["diamond"])
        dirs = [(-34, 0.95), (34, 0.95), (-92, 1.0), (92, 1.0), (-146, 0.82), (146, 0.82)]
        for i, (phi, lf) in enumerate(dirs):
            dx, dy = math.sin(math.radians(phi)), math.cos(math.radians(phi))
            b = m.bone(f"em_a{i + 1}", parent, pivot=c, rot=(0, 0, dir_rz(dx, dy)))
            feathers(b, (cx, cy, cz + 0.05 * i), R * lf, R * 0.3,
                     [mt["fwhite"], mt["fivory"], mt["fwhite"]] if i < 2 else [mt["fivory"], mt["fgold"], mt["fivory"]],
                     arm=mt["goldg"], r0=R * 0.16, n=4, spread=11)
        ring(r1, (cx, cy, cz + seg * 2), R * 0.42, 12, (R * 0.22, seg, seg), mt["goldg"], axis="z")
        ring(r2, (cx, cy, cz + seg * 3), R * 1.08, 20, (R * 0.3, seg * 0.6, seg * 0.6), mt["wgold"], axis="z")
    elif kind == 1:   # CHERUBIM: four faces (human, lion, ox, eagle) on a winged wheel
        core.plane("z", (cx, cy, cz - seg * 0.5), R * 0.62, R * 0.62, mt["bluedisc"])
        core.box((cx, cy, cz - seg), (R * 0.16, R * 0.16, seg * 1.5), mt["goldg"])
        fm = face_mats()
        for i, ang in enumerate((0, 90, 180, 270)):
            b = m.bone(f"em_a{i + 1}", parent, pivot=c, rot=(0, 0, ang))
            fc = (cx, cy + R * 0.58, cz - seg)
            b.box(fc, (R * 0.36, R * 0.36, R * 0.16), mt["goldb"], mats={"north": fm[i]}, rot=(0, 0, -ang), pivot=fc)
            for s in (1, -1):
                b.cube((cx - R * 0.09, cy + R * 0.58, cz), (R * 0.18, R * 0.42, 0), mt["fivory"],
                       rot=(0, 0, s * 70), pivot=(cx, cy + R * 0.58, cz))
        ring(r1, (cx, cy, cz + seg), R * 0.86, 16, (R * 0.36, seg * 1.2, seg * 1.2), mt["gold"], axis="z")
        for k in range(4):
            r1.box((cx, cy, cz + seg), (seg, R * 1.6, seg), mt["goldb"], rot=(0, 0, 45 + k * 90), pivot=(cx, cy, cz + seg))
        ring(r2, (cx, cy, cz), R * 0.36, 10, (R * 0.24, seg * 0.7, seg * 0.7), mt["silver"], axis="z")
    elif kind == 2:   # OPHANIM: interlocking eye-covered wheels
        core.plane("z", (cx, cy, cz - seg), R * 0.42, R * 0.42, mt["eye"])
        ring(core, (cx, cy, cz - seg * 0.5), R * 0.27, 10, (R * 0.17, seg, seg), mt["goldg"], axis="z")
        ring(r1, (cx, cy, cz), R * 0.86, 16, (R * 0.36, seg * 1.3, seg * 1.3), mt["gold"], axis="z")
        for k in range(4):
            a = math.radians(45 + k * 90)
            r1.plane("z", (cx + R * 0.86 * math.cos(a), cy + R * 0.86 * math.sin(a), cz - seg * 0.9), R * 0.24, R * 0.24, mt["eye"])
        ring(r2, (cx, cy, cz), R * 0.74, 14, (R * 0.34, seg * 1.1, seg * 1.1), mt["silver"], axis="x")
        for k in range(4):
            a = math.radians(k * 90)
            r2.plane("x", (cx + seg * 0.9, cy + R * 0.74 * math.sin(a), cz + R * 0.74 * math.cos(a)), R * 0.22, R * 0.22,
                     mt["eye_s"])
        for i in range(6):
            ang = i * 60 + 30
            b = m.bone(f"em_a{i + 1}", parent, pivot=c, rot=(0, 0, ang))
            ec = (cx, cy + R * 0.5, cz - seg * 1.5)
            b.plane("z", ec, R * 0.16, R * 0.16, mt["eye"], rot=(0, 0, -ang), pivot=ec)
            b.cube((cx - R * 0.05, cy + R * 0.5, cz - seg), (R * 0.1, R * 0.3, 0), mt["fwhite"], rot=(0, 0, 180), pivot=(cx, cy + R * 0.5, cz))
    elif kind == 3:   # SANCTUARY: a cathedral of the Word
        base = cy - R * 0.75
        core.box((cx, base + R * 0.45, cz), (R * 0.8, R * 0.9, R * 0.4), mt["pearl"], mats={"north": mt["windows1"]})
        core.box((cx, base + R * 0.92, cz), (R * 0.58, R * 0.58, R * 0.38), mt["goldb"], rot=(0, 0, 45),
                 pivot=(cx, base + R * 0.92, cz))
        core.plane("z", (cx, base + R * 0.98, cz - R * 0.22), R * 0.34, R * 0.34, mt["rose"])
        core.plane("z", (cx, base + R * 0.18, cz - R * 0.21), R * 0.22, R * 0.36, mt["wgold"])
        for i, s in enumerate((1, -1)):
            b = m.bone(f"em_a{i + 1}", parent, pivot=(cx + s * R * 0.55, base, cz))
            tx = cx + s * R * 0.55
            b.box((tx, base + R * 0.62, cz), (R * 0.3, R * 1.24, R * 0.34), mt["pearl2"], mats={"north": mt["windows1"]})
            b.box((tx, base + R * 1.3, cz), (R * 0.34, R * 0.1, R * 0.38), mt["gold"])
            b.box((tx, base + R * 1.45, cz), (R * 0.2, R * 0.22, R * 0.2), mt["goldb"], rot=(0, 45, 0), pivot=(tx, base + R * 1.45, cz))
            b.box((tx, base + R * 1.72, cz), (R * 0.07, R * 0.42, R * 0.07), mt["wgold"])
        for i, s in enumerate((1, -1)):
            b = m.bone(f"em_a{i + 3}", parent, pivot=(cx + s * R * 0.92, base, cz + R * 0.05))
            b.box((cx + s * R * 0.92, base + R * 0.32, cz + R * 0.05), (R * 0.26, R * 0.64, R * 0.3), mt["pearl"],
                  mats={"north": mt["windows1"]})
            b.box((cx + s * R * 0.92, base + R * 0.7, cz + R * 0.05), (R * 0.2, R * 0.2, R * 0.26), mt["gold"],
                  rot=(0, 0, 45), pivot=(cx + s * R * 0.92, base + R * 0.7, cz + R * 0.05))
        for i, s in enumerate((1, -1)):
            b = m.bone(f"em_a{i + 5}", parent, pivot=(cx + s * R * 0.3, base + R * 0.9, cz))
            b.box((cx + s * R * 0.3, base + R * 1.12, cz), (R * 0.08, R * 0.44, R * 0.08), mt["goldg"])
            b.plane("z", (cx + s * R * 0.3, base + R * 1.38, cz - R * 0.05), R * 0.14, R * 0.14, mt["diamond"])
        for k in range(8):
            a = k * 45
            gp = (cx, base + R * 0.98 + R * 0.24, cz - R * 0.26)
            glyph_plate(r1, gp, R * 0.09, R * 0.12, k * 3 + 1, rot=(0, 0, a), pivot=(cx, base + R * 0.98, cz - R * 0.26))
        r1.pivot = (cx, base + R * 0.98, cz - R * 0.26)
        ring(r2, (cx, base + R * 2.05, cz), R * 0.22, 10, (R * 0.14, seg, seg), mt["wgold"], axis="y")
        r2.pivot = (cx, base + R * 2.05, cz)
    elif kind == 4:   # THREEFOLD HEAVENLY THRONE
        base = cy - R * 0.55

        def throne(b, x, y, z, s, mt):
            b.box((x, y + s * 0.3, z), (s * 0.56, s * 0.14, s * 0.46), mt["goldb"])
            b.box((x, y + s * 0.39, z - s * 0.02), (s * 0.48, s * 0.05, s * 0.4), mt["blue"])
            b.box((x, y + s * 0.12, z), (s * 0.5, s * 0.24, s * 0.4), mt["pearl"])
            b.box((x, y + s * 0.82, z + s * 0.2), (s * 0.54, s * 0.9, s * 0.1), mt["pearl2"], mats={"north": mt["page_lit"]})
            b.box((x, y + s * 1.27, z + s * 0.2), (s * 0.38, s * 0.38, s * 0.12), mt["gold"], rot=(0, 0, 45),
                  pivot=(x, y + s * 1.27, z + s * 0.2))
            for sx in (1, -1):
                b.box((x + sx * s * 0.3, y + s * 0.5, z), (s * 0.08, s * 0.2, s * 0.44), mt["goldg"])
                b.box((x + sx * s * 0.3, y + s * 0.82, z + s * 0.2), (s * 0.08, s * 0.95, s * 0.12), mt["gold"])
        throne(core, cx, base, cz, R, mt)
        core.plane("z", (cx, base + R * 1.0, cz + R * 0.27), R * 0.95, R * 0.95, mt["glow_disc"])
        for i, s in enumerate((1, -1)):
            b = m.bone(f"em_a{i + 1}", parent, pivot=(cx + s * R * 0.78, base - R * 0.12, cz + R * 0.1))
            throne(b, cx + s * R * 0.78, base - R * 0.12, cz + R * 0.1, R * 0.62, mt)
        for i in range(3):
            b = m.bone(f"em_a{i + 3}", parent, pivot=(cx, base - R * 0.12 * (i + 1), cz - R * 0.3 - i * R * 0.1))
            w = R * (1.0 + 0.5 * i)
            b.box((cx, base - R * 0.12 * i - R * 0.06, cz + R * 0.02 - i * R * 0.08), (w, R * 0.12, R * 0.6 + i * R * 0.2),
                  mt["pearl"] if i % 2 == 0 else mt["pearl2"], mats={"north": mt["goldb"]})
        b = m.bone("em_a6", parent, pivot=(cx, base + R * 1.0, cz + R * 0.3))
        for k in range(7):
            a = -54 + k * 18
            b.box((cx, base + R * 1.0 + R * 0.75, cz + R * 0.3), (R * 0.05, R * 0.75, R * 0.05), mt["wgold"],
                  rot=(0, 0, a), pivot=(cx, base + R * 1.0, cz + R * 0.3))
        ring(r1, (cx, base + R * 1.0, cz + R * 0.22), R * 0.42, 14, (R * 0.2, seg, seg), mt["goldg"], axis="z")
        r1.pivot = (cx, base + R * 1.0, cz + R * 0.22)
        for k in range(8):
            a = k * 45
            glyph_plate(r2, (cx, cy + R * 0.95, cz - seg), R * 0.16, R * 0.22, k * 2 + 5, rot=(0, 0, a), pivot=(cx, cy, cz - seg))
    else:   # THE FIRST UTTERANCE: an enormous glyph recombined from moving letterforms
        gl = FW[6]
        p = R * 0.24
        rects = glyphs.rects(gl)
        ox, oy, oz = cx + 2.5 * p, cy + 3.5 * p, cz - p * 0.5
        bones = [m.bone(f"em_a{i + 1}", parent, pivot=c) for i in range(6)]
        for j, (x, y, w, h) in enumerate(rects):
            bones[j % 6].cube((ox - (x + w) * p, oy - (y + h) * p, oz), (w * p, h * p, p), mt["letter_side"],
                              mats={"north": mt["letter_front"]})
        core.box((cx, cy, cz + p * 1.5), (R * 0.16, R * 0.16, R * 0.16), mt["white"], rot=(45, 45, 0), pivot=(cx, cy, cz + p * 1.5))
        core.plane("z", (cx, cy, cz + p * 3.0), R * 0.5, R * 0.5, mt["glow_disc"])
        for k in range(12):
            glyph_plate(r1, (cx, cy + R * 1.08, cz), R * 0.18, R * 0.25, k * 5 + 2, rot=(0, 0, k * 30), pivot=c)
        for k in range(10):
            glyph_plate(r2, (cx, cy + R * 0.88, cz), R * 0.16, R * 0.22, k * 7 + 3, color="#ffffff", rot=(k * 36, 90, 0), pivot=c)


# ===================================================================================== held book model
W0, W1 = -5.3, 5.2          # cover x extent (fore-edge .. spine edge); spine at +X
H = 7.2                     # half height of covers
HX = (5.2, 0.0, 0.0)        # hinge (spine axis)


def book_model(mt):
    m = Model("book_dw", density=4.0, bounds=(3, 3, (0, 1, 0)))
    root = m.bone("root")
    root.binding = "q.item_slot_to_bone_name(c.item_slot)"
    place = m.bone("place", root)
    lift = m.bone("lift", place)
    hover = m.bone("hover", lift)
    book = m.bone("book", hover)

    # ---- spine: wing-feather segments interlocking along a pearl spine
    spine = m.bone("spine", book, pivot=HX)
    spine.cube((5.2, -7.3, -1.75), (0.7, 14.6, 3.5), mt["pearl"])
    spine.cube((5.0, 7.0, -1.8), (1.0, 0.55, 3.6), mt["goldg"])
    spine.cube((5.0, -7.55, -1.8), (1.0, 0.55, 3.6), mt["goldg"])
    for i in range(6):
        y = 5.6 - i * 2.25
        b = m.bone(f"spseg{i + 1}", spine, pivot=(5.95, y, 0))
        b.plane("x", (5.98, y, 0), 3.0, 2.3, mt["chevron"], variant=i % 2)
        if i < 5:
            b.cube((5.85, y - 1.25, -1.5), (0.22, 0.24, 3.0), mt["gold"])

    # ---- back half: back cover + back page block
    back = m.bone("back", book, pivot=HX)
    back.cube((W0, -H, 1.2), (W1 - W0, 2 * H, 0.4), mt["back"])
    back.cube((-4.9, -6.8, 0.0), (9.9, 13.6, 1.2), mt["edge"], mats={"north": mt["page"]})
    for (x0, y0, w, h) in ((W0, H - 0.55, W1 - W0, 0.55), (W0, -H, W1 - W0, 0.55), (W0, -H, 0.55, 2 * H)):
        back.cube((x0, y0, 1.6), (w, h, 0.3), mt["gold"])
    ring(back, (0, 0, 1.75), 1.6, 8, (1.2, 0.35, 0.3), mt["goldb"], axis="z")
    back.plane("z", (0, 0, 1.92), 2.5, 2.5, mt["bluedisc"])

    # ---- front half: front cover + front page block + frame + emblems
    front = m.bone("front", book, pivot=HX)
    front.cube((W0, -H, -1.6), (W1 - W0, 2 * H, 0.4), mt["pearl"], mats={"north": mt["cover"]})
    front.cube((-4.9, -6.8, -1.2), (9.9, 13.6, 1.2), mt["edge"], mats={"south": mt["page"]})
    fz = -1.6
    for (x0, y0, w, h) in ((W0, H - 0.6, W1 - W0, 0.6), (W0, -H, W1 - W0, 0.6), (W0, -H + 0.6, 0.6, 2 * H - 1.2),
                           (W1 - 0.6, -H + 0.6, 0.6, 2 * H - 1.2)):
        front.cube((x0, y0, fz - 0.35), (w, h, 0.35), mt["gold"])
    for (x0, y0, w, h) in ((-3.9, 5.7, 7.8, 0.22), (-3.9, -5.92, 7.8, 0.22), (-3.92, -5.9, 0.22, 11.8), (3.7, -5.9, 0.22, 11.8)):
        front.cube((x0, y0, fz - 0.14), (w, h, 0.14), mt["goldb"])
    # inlaid royal blue cartouche behind the First Utterance
    front.plane("z", (-0.05, 0.8, fz - 0.03), 5.6, 5.6, mt["bluedisc"], faces=("north",))

    # corner wing ornaments (articulated)
    for name, (x, y) in (("tl", (W1, H)), ("tr", (W0, H)), ("bl", (W1, -H)), ("br", (W0, -H))):
        sx, sy = (1 if x > 0 else -1), (1 if y > 0 else -1)
        cx, cy = x - sx * 0.25, y - sy * 0.25
        b = m.bone(f"cw_{name}", front, pivot=(cx, cy, fz))
        b.cube((cx - (2.4 if sx > 0 else 0), cy - (0.5 if sy > 0 else 0), fz - 0.42), (2.4, 0.5, 0.42), mt["goldg"])
        b.cube((cx - (0.5 if sx > 0 else 0), cy - (2.4 if sy > 0 else 0), fz - 0.42), (0.5, 2.4, 0.42), mt["goldg"])
        rz = dir_rz(sx, sy)
        L = 2.1 if sx > 0 else 2.7     # shorter over the spine
        for k, d in enumerate((-30, 0, 30)):
            b.cube((cx - 0.45, cy - L * (1 - 0.15 * abs(k - 1)), fz - 0.5 - 0.04 * k), (0.9, L * (1 - 0.15 * abs(k - 1)), 0),
                   mt["fgold"], rot=(0, 0, rz + d), pivot=(cx, cy, fz - 0.5), variant=k)
        b.box((cx - sx * 0.9, cy - sy * 0.9, fz - 0.5), (0.7, 0.7, 0.3), mt["diamond"], faces=("north",))

    ez = fz - 0.45
    # First Utterance: rotating ring of letters around three morphing letterforms
    uc = (-0.05, 0.8, ez)
    ur = m.bone("utter_ring", front, pivot=uc)
    ring(ur, uc, 2.55, 14, (1.2, 0.3, 0.3), mt["gold"], axis="z")
    for k in range(8):
        glyph_plate(ur, (uc[0], uc[1] + 1.85, ez - 0.2), 0.75, 1.0, k * 2 + 1, rot=(0, 0, k * 45), pivot=(uc[0], uc[1], ez - 0.2))
    for k, gi in enumerate((6, 13, 1)):
        b = m.bone(f"utter_g{k + 1}", front, pivot=(uc[0], uc[1], ez - 0.3))
        glyph_plate(b, (uc[0], uc[1], ez - 0.3 - 0.05 * k), 2.1, 2.9, gi, color="#ffffff", color2=WGOLD)

    # Seraph emblem: six wings
    sc = (-0.05, 5.0, ez)
    sb = m.bone("seraph", front, pivot=sc)
    sb.plane("z", (sc[0], sc[1], ez - 0.25), 0.8, 1.2, mt["flame"])
    for i, (phi, lf) in enumerate([(-38, 1.0), (38, 1.0), (-90, 1.15), (90, 1.15), (-142, 0.85), (142, 0.85)]):
        dx, dy = math.sin(math.radians(phi)), math.cos(math.radians(phi))
        b = m.bone(f"sw{i + 1}", sb, pivot=sc, rot=(0, 0, dir_rz(dx, dy)))
        feathers(b, (sc[0], sc[1], ez - 0.1), 1.7 * lf, 0.6, [mt["fivory"], mt["fwhite"]], n=2, spread=16, r0=0.3)

    # Cherub emblem: four faces turning on a little wheel
    cc = (2.45, -4.45, ez)
    cb = m.bone("cherub", front, pivot=cc)
    ring(cb, cc, 1.35, 10, (0.85, 0.22, 0.22), mt["goldb"], axis="z")
    fm = face_mats()
    for i, ang in enumerate((0, 90, 180, 270)):
        a = math.radians(ang + 90)
        p = (cc[0] + 0.72 * math.cos(a), cc[1] + 0.72 * math.sin(a), ez - 0.2)
        cb.box(p, (0.95, 0.95, 0.35), mt["goldb"], mats={"north": fm[i]})

    # Ophanim emblem: two interlocking eye-covered wheels
    oc = (-2.55, -4.45, ez - 0.6)
    oa = m.bone("ophan_a", front, pivot=oc)
    ring(oa, oc, 1.3, 10, (0.82, 0.24, 0.24), mt["gold"], axis="z")
    for k in range(3):
        a = math.radians(90 + k * 120)
        oa.plane("z", (oc[0] + 1.3 * math.cos(a), oc[1] + 1.3 * math.sin(a), oc[2] - 0.2), 0.62, 0.62, mt["eye"])
    ob = m.bone("ophan_b", oa, pivot=oc)
    ring(ob, oc, 1.05, 8, (0.82, 0.2, 0.2), mt["silver"], axis="x")
    oa.plane("z", (oc[0], oc[1], oc[2] - 0.1), 0.75, 0.75, mt["eye_s"])

    # pages that riffle / turn (hinged at the spine, resting on the back block)
    for i in range(3):
        b = m.bone(f"pg{i + 1}", book, pivot=HX)
        b.cube((-4.75, -6.6, -0.02 - 0.01 * i), (9.9, 13.2, 0), mt["page"], variant=i)

    # rising lines of writing (charging) and drifting letters (idle)
    for i in range(3):
        b = m.bone(f"ln{i + 1}", book, pivot=(5.2, 1.0, -2.2))
        b.plane("z", (5.2, 1.0, -2.2 - 0.1 * i), 11.0, 1.5, mt["line"], variant=i)
    glow = m.bone("spread_glow", book, pivot=(5.2, 7.6, -0.8))   # radiance above the spine while open
    glow.plane("z", (5.2, 8.6, -0.8), 3.2, 3.2, mt["glow_disc"])
    glow.plane("z", (5.2, 8.6, -1.0), 1.4, 1.4, mt["diamond"])
    for i in range(5):
        b = m.bone(f"dr{i + 1}", book, pivot=(-3.2 + i * 1.7, 7.3, -0.5 + 0.25 * i))
        glyph_plate(b, (-3.2 + i * 1.7, 7.3, -0.5 + 0.25 * i), 0.9, 1.25, i * 3 + 2)

    # royal blue silk bookmark with a gilt tip
    par = book
    for i in range(3):
        b = m.bone(f"rb{i + 1}", par, pivot=(1.6, -6.8 - i * 1.9, 0.1))
        b.plane("z", (1.6, -6.8 - i * 1.9 - 0.95, 0.1), 0.8, 1.9, mt["ribbon"], variant=i)
        par = b
    par.box((1.6, -12.7, 0.1), (0.5, 0.5, 0.5), mt["goldg"], rot=(0, 0, 45), pivot=(1.6, -12.7, 0.1))
    return m


# ------------------------------------------------------------------------------------- Molang helpers
def spin(rate):
    return M(f"q.life_time*{rate}", lambda t: t * rate)


def frac(rate, phase):
    return f"math.mod(q.life_time*{rate}+{phase},1.0)", (lambda t: (t * rate + phase) % 1.0)


OPEN = M("v.open", lambda t: PV["open"])


def oexpr(k, base=0.0):
    """base + k * v.open"""
    return M(f"{base}+({k})*v.open", lambda t: base + k * PV["open"])


def book_anims():
    A = []
    idle = Anim("idle", loop=True)
    idle.pos("hover", (LIFE(0.18, 1.7, 0.3), LIFE(0.7, 3.2), 0))
    idle.rot("hover", (LIFE(3.0, 4.4), LIFE(5.0, 6.3, 0.2), LIFE(2.5, 5.1, 0.6)))
    idle.rot("front", (0, LIFE(1.4, 3.2, 0.0, -1.4), 0))           # the cover breathes slightly ajar
    idle.rot("utter_ring", (0, 0, spin(28)))
    for k in range(3):   # three letterforms recombining into one another
        ph = k * 120
        s = M(f"math.clamp(math.sin(q.life_time*80+{ph})*1.6,0,1)",
              lambda t, ph=ph: max(0.0, min(1.0, math.sin(math.radians(t * 80 + ph)) * 1.6)))
        idle.scl(f"utter_g{k + 1}", (s, s, 1))
        idle.rot(f"utter_g{k + 1}", (0, 0, M(f"math.sin(q.life_time*80+{ph})*-18",
                                             lambda t, ph=ph: -18 * math.sin(math.radians(t * 80 + ph)))))
    for i in range(6):
        idle.rot(f"sw{i + 1}", (0, 0, LIFE(7 if i % 2 == 0 else -7, 2.2, 0.08 * (i // 2))))
    idle.rot("cherub", (0, 0, spin(-14)))
    idle.rot("ophan_a", (0, 0, spin(46)))
    idle.rot("ophan_b", (0, spin(-70), 0))
    for i, n in enumerate(("tl", "tr", "bl", "br")):
        idle.rot(f"cw_{n}", (0, 0, LIFE(4.0 if i % 2 == 0 else -4.0, 2.7, i * 0.21)))
    for i in range(6):
        idle.rot(f"spseg{i + 1}", (0, 0, LIFE(5.0, 2.4, -i * 0.1)))
    for i in range(3):
        idle.rot(f"rb{i + 1}", (LIFE(10 + 4 * i, 2.9, -i * 0.14), 0, LIFE(5 + 3 * i, 3.7, -i * 0.2)))
    for i in range(5):   # small golden letters drift from the pages and dissolve
        m_, f = frac(0.38 + 0.05 * i, i * 0.2)
        idle.pos(f"dr{i + 1}", (M(f"math.sin(({m_})*360+{i * 70})*1.2", lambda t, f=f, i=i: 1.2 * math.sin(math.radians(f(t) * 360 + i * 70))),
                                M(f"({m_})*7.0", lambda t, f=f: f(t) * 7.0), M(f"({m_})*-1.5", lambda t, f=f: -1.5 * f(t))))
        sc = M(f"math.sin(({m_})*180)*0.9", lambda t, f=f: 0.9 * math.sin(math.radians(f(t) * 180)))
        idle.scl(f"dr{i + 1}", (sc, sc, sc))
    A.append(idle)

    op = Anim("open", loop=True)   # weight comes from v.open (0 closed .. 1 open)
    op.rot("front", (0, oexpr(-166), 0))
    op.rot("back", (0, oexpr(-10), 0))
    op.pos("book", (oexpr(-5.2), 0, 0))
    op.scl("spread_glow", (M("v.open*(0.85+0.15*math.sin(q.life_time*400))", lambda t: PV["open"] * (0.85 + 0.15 * math.sin(math.radians(t * 400)))),) * 3)
    for i in range(3):   # pages riffle over continuously while the Word gathers
        m_, f = frac(1.1, i / 3.0)
        op.rot(f"pg{i + 1}", (0, M(f"v.open*(-10-156*math.clamp(({m_})*1.7-0.2,0,1))",
                                   lambda t, f=f: PV["open"] * (-10 - 156 * min(1, max(0, f(t) * 1.7 - 0.2)))), 0))
    for i in range(3):   # lines of writing rise above the open book and dissolve
        m_, f = frac(0.55, i / 3.0)
        op.pos(f"ln{i + 1}", (M(f"math.sin(({m_})*360+{i * 90})*0.8", lambda t, f=f, i=i: 0.8 * math.sin(math.radians(f(t) * 360 + i * 90))),
                              M(f"({m_})*10.0", lambda t, f=f: f(t) * 10.0), 0))
        s = M(f"v.open*math.sin(({m_})*180)", lambda t, f=f: PV["open"] * math.sin(math.radians(f(t) * 180)))
        op.scl(f"ln{i + 1}", (s, s, s))
    A.append(op)

    turn = Anim("turn", length=0.95, loop=False)   # selection flourish: open, riffle three pages, close
    turn.rot("front", {0: (0, 0, 0), 0.16: (0, -150, 0), 0.72: (0, -150, 0), 0.95: (0, 0, 0)})
    turn.rot("back", {0: (0, 0, 0), 0.16: (0, -8, 0), 0.72: (0, -8, 0), 0.95: (0, 0, 0)})
    turn.pos("book", {0: (0, 0, 0), 0.16: (-4.6, 0, 0), 0.72: (-4.6, 0, 0), 0.95: (0, 0, 0)})
    turn.pos("hover", {0: (0, 0, 0), 0.2: (0, 1.4, 0), 0.6: (0, 1.0, 0), 0.95: (0, 0, 0)})
    turn.rot("lift", {0: (0, 0, 0), 0.2: (-8, 0, 3), 0.95: (0, 0, 0)})
    for i in range(3):
        t0 = 0.16 + 0.11 * i
        turn.rot(f"pg{i + 1}", {0: (0, 0, 0), t0: (0, -8, 0), t0 + 0.08: (0, -70, 6), t0 + 0.2: (0, -150, 0),
                                0.72: (0, -150, 0), 0.95: (0, 0, 0)})
    turn.scl("spread_glow", {0: 0.0, 0.2: 0.9, 0.6: 0.6, 0.9: 0.0})
    for k in range(3):
        turn.scl(f"utter_g{k + 1}", {0: (1, 1, 1), 0.3: (1.5, 1.5, 1), 0.95: (1, 1, 1)})
    A.append(turn)

    def placement(name, pos, rot, scale, opos, orot):
        a = Anim(name, loop=True)
        a.pos("place", tuple(oexpr(opos[i], pos[i]) for i in range(3)))
        a.rot("place", tuple(oexpr(orot[i], rot[i]) for i in range(3)))
        a.scl("place", scale)
        return a
    A.append(placement("place_fp", FP_POS, FP_ROT, FP_SCALE, FP_OPEN_POS, FP_OPEN_ROT))
    A.append(placement("place_tp", TP_POS, TP_ROT, TP_SCALE, TP_OPEN_POS, TP_OPEN_ROT))
    for a in A:
        a.model = "book_dw"
    return A


def write_attachable(pack, m, anims):
    geo, texp = pack.model(m)
    rp = pack.rp
    by = {a.name: a for a in anims}
    _write(os.path.join(rp, "animations", "book_dw.animation.json"), animations_file(list(by.values())))
    ctl = "controller.animation.grimoire.book_dw.turn"
    _write(os.path.join(rp, "animation_controllers", "book_dw.animation_controllers.json"), {
        "format_version": "1.10.0",
        "animation_controllers": {ctl: {
            "initial_state": "default",
            "states": {
                "default": {"transitions": [{"turn": "q.is_sneaking"}], "blend_transition": 0.1},
                "turn": {"animations": ["turn"], "transitions": [{"rest": "q.all_animations_finished"}],
                         "blend_transition": 0.1},
                "rest": {"transitions": [{"default": "!q.is_sneaking"}], "blend_transition": 0.1},
            }}}})
    _write(os.path.join(rp, "render_controllers", "book_dw.render_controllers.json"), {
        "format_version": "1.8.0",
        "render_controllers": {"controller.render.grimoire.book_dw": {
            "geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"]}}})
    amap = {n: a.full for n, a in by.items()}
    amap["ctl_turn"] = ctl
    _write(os.path.join(rp, "attachables", f"{ITEM}.json"), {
        "format_version": "1.10.0",
        "minecraft:attachable": {"description": {
            "identifier": f"grimoire:{ITEM}",
            "materials": {"default": "entity_emissive_alpha"},
            "textures": {"default": texp},
            "geometry": {"default": geo},
            "animations": amap,
            "scripts": {
                "pre_animation": [
                    # ticks the item has been in use (the engine counts use_duration down from the max)
                    "v.held = q.main_hand_item_use_duration > 0.0 ? "
                    "math.max(q.main_hand_item_max_duration - q.main_hand_item_use_duration, 0.0) : 0.0;",
                    f"v.target = q.main_hand_item_use_duration > 0.0 ? math.clamp(v.held / {OPEN_TICKS}, 0.15, 1.0) : 0.0;",
                    # opens with the hold, closes smoothly afterwards
                    f"v.open = math.max(v.target, math.clamp((v.open ?? 0.0) - q.delta_time * {OPEN_RATE}, 0.0, 1.0));",
                    "v.open = v.open * v.open * (3.0 - 2.0 * v.open);",
                ],
                "animate": ["idle", "open", {"place_fp": "c.is_first_person"}, {"place_tp": "!c.is_first_person"},
                            "ctl_turn"],
            },
            "render_controllers": ["controller.render.grimoire.book_dw"],
        }}})


# =================================================================================== selection vision
LINES_V = (1.2, -1.2, -3.6)    # vision text line heights (each line is one full glyph row tall)


def vision_model(kind, mt):
    m = Model(f"book_dw_vision_k{kind}", density=4.0, bounds=(2, 2, (0, 0.2, 0)))
    root = m.bone("root")
    spread = m.bone("spread", root, pivot=(0, -1.5, 0), rot=(32, 0, 0))
    pl = m.bone("pl", spread, pivot=(0, -1.5, 0), rot=(0, 14, 0))
    pl.plane("z", (3.0, -1.5, 0), 6.0, 8.0, mt["parch"])
    pl.cube((0, -5.6, 0.0), (6.1, 8.2, 0.5), mt["pearl"], faces=("south", "east", "west", "up", "down"))
    pr = m.bone("pr", spread, pivot=(0, -1.5, 0), rot=(0, -14, 0))
    pr.plane("z", (-3.0, -1.5, 0), 6.0, 8.0, mt["parch"], variant=1)
    pr.cube((-6.1, -5.6, 0.0), (6.1, 8.2, 0.5), mt["pearl"], faces=("south", "east", "west", "up", "down"))
    spread.box((0, -1.5, 0.2), (0.6, 8.4, 0.6), mt["goldg"])
    for i in range(3):   # the previous sentence (on the left page) dissolves
        y = LINES_V[i]
        b = m.bone(f"o{i + 1}", pl, pivot=(3.0, y, -0.08))
        b.plane("z", (3.0, y, -0.08), 4.6, 2.25, mt["line_old"], variant=i)
    t = m.bone("turn", spread, pivot=(0, -1.5, 0), rot=(0, -14, 0))
    t.plane("z", (-3.0, -1.5, -0.05), 5.8, 7.8, mt["page"])
    for i in range(3):   # the new sentence is written on the right page, left to right
        y = LINES_V[i]
        b = m.bone(f"n{i + 1}", pr, pivot=(-0.6, y, -0.1))
        b.plane("z", (-2.9, y, -0.1), 4.6, 2.25, mt["line_new"], variant=i)
    nib = m.bone("nib", pr, pivot=(-0.6, LINES_V[0], -0.4))
    nib.plane("z", (-0.6, LINES_V[0], -0.4), 0.9, 0.9, mt["diamond"])
    nib.plane("z", (-0.6, LINES_V[0], -0.35), 1.6, 1.6, mt["glow_disc"])
    em = m.bone("emblem", root, pivot=(0, 5.0, -0.5))
    emblem(kind, m, em, (0, 5.0, -0.5), 3.3, mt)
    gl = m.bone("gleam", em, pivot=(0, 5.0, 0.6))
    gl.plane("z", (0, 5.0, 0.6), 5.0, 5.0, mt["glow_disc"])
    return m


def vision_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    s = Anim("show", length=VISION_LEN, loop="hold")
    s.scl("root", {0: 0.0, 0.1: 1.12, 0.2: 1.0, 1.02: 1.0, 1.2: 0.0})
    s.pos("root", {0: (0, -3, 0), 0.2: (0, 0, 0), 1.0: (0, 1.0, 0), 1.2: (0, 2.5, 0)})
    s.rot("spread", {0: (8, 0, 0), 0.25: (0, 0, 0), 1.2: (-4, 0, 0)})
    for i in range(3):
        t0 = 0.06 + 0.05 * i
        s.scl(f"o{i + 1}", {0: (1, 1, 1), t0: (1, 1, 1), t0 + 0.2: (1.25, 0, 1)})
        s.pos(f"o{i + 1}", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.2: (0, 1.2, -1.2)})
    s.rot("turn", {0: (0, 0, 0), 0.12: (0, 0, 0), 0.26: (0, -70, 0), 0.42: (0, -152, 0), 1.2: (0, -152, 0)})
    s.scl("turn", {0: 1.0, 0.42: 1.0, 0.46: 0.0})          # the turned page settles onto the left page
    for i in range(3):
        t0 = 0.44 + 0.15 * i
        s.scl(f"n{i + 1}", {0: (0, 1, 1), t0: (0, 1, 1), t0 + 0.15: (1, 1, 1)}, smooth=False)
    nib_keys = {0: (0, 0, 0), 0.44: (0, 0, 0)}
    for i in range(3):
        t0 = 0.44 + 0.15 * i
        dy = LINES_V[i] - LINES_V[0]
        nib_keys[t0 + 0.001] = (0, dy, 0)
        nib_keys[t0 + 0.15] = (-4.6, dy, 0)
    s.pos("nib", nib_keys, smooth=False)
    s.scl("nib", {0: 0.0, 0.43: 0.0, 0.46: 1.0, 0.9: 1.0, 0.94: 0.0})
    s.scl("emblem", {0: 0.0, 0.5: 0.0, 0.78: 1.2, 0.92: 1.0, 1.2: 1.1})
    s.pos("emblem", {0: (0, -4, 0), 0.5: (0, -4, 0), 0.9: (0, 0, 0)})
    s.rot("emblem", {0: (0, -60, 0), 0.5: (0, -60, 0), 0.95: (0, 0, 0), 1.2: (0, 10, 0)})
    s.scl("gleam", {0: 0.0, 0.7: 0.0, 0.86: 1.3, 1.2: 0.4})
    for i in range(6):
        t0 = 0.55 + 0.04 * i
        s.rot(f"em_a{i + 1}", {0: (-70, 0, -25), t0: (-70, 0, -25), t0 + 0.3: (0, 0, 0)})
        s.scl(f"em_a{i + 1}", {0: 0.25, t0: 0.25, t0 + 0.3: 1.0})
    s.rot("em_ring1", (0, 0, spin(90)))
    s.rot("em_ring2", (0, spin(-120), 0))
    s.scl("em_core", {0: 1.0, 0.8: 1.0, 0.88: 1.4, 1.0: 1.0})
    A.append(s)
    return A


# ===================================================================================== charge construct
P = 0.72          # letter pixel (units)
DEPTH = 1.1


def layout(kind):
    """Letters per kind: list of (center, rot, glyph index, parent) and the emblem (center, R)."""
    seq = glyphs.seq(41 + kind * 7, 16)
    L = []
    if kind == 0:     # Seraphic Litany: two ascending wing-rows and a base line, a V of praise
        for s in (1, -1):
            for i in range(4):
                L.append(((s * (8.2 + 2.8 * i), -6.5 + 4.2 * i, 1.0 + 0.6 * i), (0, s * 14, -s * 18), None, "words"))
        for i in range(4):
            L.append((((1.5 - i) * 4.4, -11.5, 0.0), (0, 0, 0), None, "words"))
        em = ((0, 1.5, 3.0), 7.4)
    elif kind == 1:   # Cherubic Testament: four witnesses' words, one at each point of the cross
        for i in range(3):
            L.append((((1 - i) * 4.4, 12.0, 0.0), (0, 0, 0), None, "words"))
            L.append((((1 - i) * 4.4, -12.0, 0.0), (0, 0, 0), None, "words"))
            L.append(((12.8, 5.2 - i * 5.2, 0.5), (0, 16, 0), None, "words"))
            L.append(((-12.8, 5.2 - i * 5.2, 0.5), (0, -16, 0), None, "words"))
        em = ((0, 0, 3.0), 6.8)
    elif kind == 2:   # Ophanim: a turning wheel of letters around the wheels within wheels
        for i in range(12):
            a = i * 30
            r = 12.6
            L.append(((r * math.sin(math.radians(a)), r * math.cos(math.radians(a)), 0.5), (0, 0, -a), None, "wring"))
        em = ((0, 0, 3.0), 7.4)
    elif kind == 3:   # Let There Be Sanctuary: words stacked into pillars and an arch
        for s in (1, -1):
            for i in range(4):
                L.append(((s * 9.6, -12.5 + i * 5.3, 0.0), (0, 0, 0), None, "words"))
        for i in range(5):
            a = -64 + i * 32
            L.append(((9.6 * math.sin(math.radians(a)), 7.5 + 7.0 * math.cos(math.radians(a)), 0.0), (0, 0, -a), None, "words"))
        em = ((0, -4.0, 3.5), 6.6)
    elif kind == 4:   # Threefold Heavenly Throne: a three-tiered dais of words beneath the throne
        for i in range(6):
            L.append((((2.5 - i) * 4.3, -11.0, -1.0), (-8, 0, 0), None, "words"))
        for i in range(4):
            L.append((((1.5 - i) * 4.3, -5.4, 1.4), (-8, 0, 0), None, "words"))
        for i in range(2):
            L.append((((0.5 - i) * 4.3, 0.2, 3.8), (-8, 0, 0), None, "words"))
        em = ((0, 8.5, 4.5), 6.2)
    else:             # The Word Before Creation: letters orbit the First Utterance
        for i in range(10):
            a = i * 36
            r = 13.0
            L.append(((r * math.sin(math.radians(a)), 0.0, -r * math.cos(math.radians(a))), (0, -a, 0), None, "worbit"))
        em = ((0, 0, 2.0), 8.0)
    out = []
    for i, (c, r, _g, par) in enumerate(L):
        out.append((c, r, seq[i] % len(FW), par))
    return out, em


LINE_Y = (-8.0, -2.5, 3.0)


def charge_model(kind, mt):
    m = Model(f"book_dw_charge_k{kind}", density=2.5, bounds=(5, 5, (0, 0, 0)))
    root = m.bone("root")
    body = m.bone("body", root)
    seal = m.bone("seal", body, pivot=(0, 0, 9.0))
    seal.plane("z", (0, 0, 9.0), 27, 27, mt["seal_thin"])
    words = m.bone("words", body)
    wr = m.bone("wring", body)                                  # letters turning in the picture plane
    wo = m.bone("worbit", body, rot=(14, 0, 0))                  # letters orbiting around the emblem
    letters, (ec, R) = layout(kind)
    for i, (c, r, gi, par) in enumerate(letters):
        b = m.bone(f"w{i + 1}", {"wring": wr, "worbit": wo}.get(par, words), pivot=c, rot=r)
        glyphs.extrude(b, FW[gi], (c[0] + 2.5 * P, c[1] + 3.5 * P, c[2] - DEPTH / 2), P, DEPTH, mt["letter_side"],
                       mats={"north": mt["letter_front"]})
    for i, y in enumerate(LINE_Y):
        b = m.bone(f"ln{i + 1}", body, pivot=(0, y, -2.0))
        b.plane("z", (0, y, -2.0 - 0.1 * i), 14, 1.2, mt["line"], variant=i)
    em = m.bone("emblem", body, pivot=ec)
    emblem(kind, m, em, ec, R, mt)
    fl = m.bone("flash", body, pivot=(0, 0, -3))
    fl.plane("z", (0, 0, -3), 30, 30, mt["glow_disc"])
    return m


def charge_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    NW = max(len(layout(k)[0]) for k in range(6))   # letter bones w1..wNW

    form = Anim("form", length=FORM_LEN, loop="hold")
    form.scl("root", {0: 0.6, 0.25: 1.0})
    form.scl("flash", 0.0)
    form.scl("seal", {0: 0.0, 0.15: 0.0, 0.7: 1.08, 0.9: 1.0})
    form.rot("seal", (0, 0, spin(-20)))
    for i in range(3):   # flat lines of sacred writing rise from the book ...
        t0 = 0.0 + 0.12 * i
        form.pos(f"ln{i + 1}", {0: (0, -16, 2), t0: (0, -16, 2), t0 + 0.55: (0, 0, 0)})
        form.scl(f"ln{i + 1}", {0: (0.2, 1, 1), t0 + 0.2: (1, 1, 1), 0.8 + 0.12 * i: (1, 1, 1), 1.15 + 0.1 * i: (1.5, 0, 1)})
    for i in range(NW):  # ... and their letters lift out of them as solid, three-dimensional words
        t0 = 0.3 + 0.055 * i
        t1 = t0 + 0.5
        form.pos(f"w{i + 1}", {0: (0, -14, -3), t0: (0, -14, -3), t1 - 0.12: (0, 0.8, 0), t1: (0, 0, 0)})
        form.scl(f"w{i + 1}", {0: (0, 0, 0), t0: (1.0, 0.2, 0.05), t1 - 0.12: (1.18, 1.18, 1.18), t1: (1, 1, 1)})
        form.rot(f"w{i + 1}", {0: (70, 0, 0), t0: (70, 0, 0), t1: (0, 0, 0)})
    form.scl("emblem", {0: 0.0, 0.55: 0.0, 1.05: 1.1, 1.3: 1.0})
    for i in range(6):   # the celestial emblem unfolds
        t0 = 0.7 + 0.06 * i
        form.rot(f"em_a{i + 1}", {0: (-80, 0, -30), t0: (-80, 0, -30), t0 + 0.45: (4, 0, 2), t0 + 0.6: (0, 0, 0)})
        form.scl(f"em_a{i + 1}", {0: 0.2, t0: 0.2, t0 + 0.45: 1.05, t0 + 0.6: 1.0})
    form.scl("em_core", {0: 0.0, 0.8: 0.0, 1.2: 1.3, 1.5: 1.0})
    form.rot("em_ring1", (0, 0, spin(60)))
    form.rot("em_ring2", (0, spin(-80), 0))
    A.append(form)

    loop = Anim("loop", loop=True)
    loop.pos("body", (0, LIFE(0.8, 3.0), 0))
    loop.rot("body", (LIFE(1.5, 4.1), LIFE(2.5, 5.3, 0.3), 0))
    loop.scl("flash", 0.0)
    loop.rot("seal", (0, 0, spin(-20)))
    loop.rot("em_ring1", (0, 0, spin(60)))
    loop.rot("em_ring2", (0, spin(-80), 0))
    loop.scl("em_core", LIFE(0.1, 0.9, 0, 1.0))
    loop.rot("wring", (0, 0, spin(-12)))
    loop.rot("worbit", (0, spin(16), 0))
    for i in range(6):
        loop.rot(f"em_a{i + 1}", (LIFE(4, 2.6, i * 0.11), 0, LIFE(3, 3.1, i * 0.17)))
    for i in range(NW):
        loop.pos(f"w{i + 1}", (0, LIFE(0.6, 2.2, i * 0.09), 0))
        loop.scl(f"w{i + 1}", LIFE(0.04, 1.1, i * 0.13, 1.0))
    for i in range(3):   # the writing keeps rising through the construct
        m_, f = frac(0.5, i / 3.0)
        loop.pos(f"ln{i + 1}", (0, M(f"({m_})*22.0-11.0-{LINE_Y[i]}", lambda t, f=f, i=i: f(t) * 22 - 11 - LINE_Y[i]), 0))
        s = M(f"math.sin(({m_})*180)", lambda t, f=f: math.sin(math.radians(f(t) * 180)))
        loop.scl(f"ln{i + 1}", (s, s, s))
    A.append(loop)

    rel = Anim("release", length=RELEASE_LEN, loop="hold")   # the sentence ignites, then becomes the spell
    rel.scl("flash", {0: 0.0, 0.1: 0.9, 0.28: 1.5, 0.5: 0.0})
    rel.scl("words", {0: 1.0, 0.14: 1.14, 0.42: 0.0})
    rel.scl("emblem", {0: 1.0, 0.14: 1.35, 0.45: 0.0})
    rel.scl("seal", {0: 1.0, 0.2: 1.5, 0.5: 0.0})
    rel.scl("root", {0: 1.0, 0.44: 1.0, 0.5: 0.0})
    for i in range(3):
        rel.scl(f"ln{i + 1}", 0.0)
    rel.rot("seal", (0, 0, spin(-160)))
    rel.rot("wring", (0, 0, spin(-12)))
    rel.rot("worbit", (0, spin(16), 0))
    A.append(rel)

    can = Anim("cancel", length=CANCEL_LEN, loop="hold")     # the words lose their meaning and sink away
    can.scl("flash", 0.0)
    for i in range(NW):
        t0 = 0.012 * i
        can.pos(f"w{i + 1}", {0: (0, 0, 0), t0: (0, 0, 0), 0.4: (0, -9, -2)})
        can.scl(f"w{i + 1}", {0: (1, 1, 1), t0: (1, 1, 1), 0.4: (1.0, 0.0, 0.05)})
    for i in range(6):
        can.rot(f"em_a{i + 1}", {0: (0, 0, 0), 0.3: (-80, 0, -30)})
    can.scl("emblem", {0: 1.0, 0.36: 0.0})
    can.scl("seal", {0: 1.0, 0.38: 0.0})
    can.scl("root", {0: 1.0, 0.36: 1.0, 0.4: 0.0})
    for i in range(3):
        can.scl(f"ln{i + 1}", 0.0)
    A.append(can)
    return A


# ======================================================================================== particles
def build_particles(pack):
    fx = particles(pack)
    gl = [f"glyph{i}" for i in range(1, 9)]
    fx.effect("book_dw_mote", None, sprites=gl + ["dot"], count=3, life=(0.9, 1.6), size=(0.11, 0.02),
              shape=("disc", 0.9), speed=(0.15, 0.45), direction=(0, 1, 0), accel=(0, 0.7, 0), drag=0.8,
              colors=["#fff3c400", "#fff3c4ff", "#ffd76acc", "#c9a24a00"])
    fx.effect("book_dw_burst", None, sprites=gl + ["star", "spark"], count=26, life=(0.45, 1.0), size=(0.2, 0.0),
              shape=("sphere", 0.4), speed=(3.0, 7.0), drag=2.2, accel=(0, 0.6, 0),
              colors=["#ffffffff", "#fff3c4ff", "#ffd76acc", "#c9a24a00"], spin=(360, 160))


# =========================================================================================== sounds
def build_sounds(pack):
    def page_flip(dur=0.16, f=3400):
        n = sy.noise(dur)
        x = np.linspace(0, 1, len(n))
        return sy.norm(sy.bandpass(n, f, 1.2) * np.sin(np.pi * x) ** 0.7 * (0.6 + 0.4 * np.sin(x * 40)))

    # select: three quick page turns, then a tiny ascending three-note motif of glass and choir
    sel = sy.at(1.2, (0.0, page_flip(0.17, 3000) * 0.55), (0.08, page_flip(0.15, 3800) * 0.45),
                (0.16, page_flip(0.16, 3300) * 0.4),
                (0.24, sy.pluck(1174.7, 0.5, 0.8) * 0.45), (0.33, sy.pluck(1568.0, 0.5, 0.8) * 0.4),
                (0.42, sy.bell(1975.5, 0.7) * 0.35), (0.38, sy.choir(587.3, 0.7, "oo", voices=3, attack=0.08, release=0.4) * 0.25))
    sy.save(pack, "book_dw_select", sy.reverb(sel, 1.3, 0.35), volume=0.8, max_distance=24)

    # charge: a two-second swell -- quill-scratch writing under a rising choir and gathering shimmer
    d = 2.1
    t = sy.t_axis(d)
    swell = np.clip(t / d, 0, 1) ** 1.3
    choirs = sy.mixdown([sy.choir(293.7, d, "oo", voices=4, attack=1.2, release=0.3),
                         sy.choir(440.0, d, "ah", voices=3, attack=1.5, release=0.3),
                         sy.choir(587.3, d, "ah", voices=3, attack=1.7, release=0.25, bright=1.2)])
    write = sy.scribble(d, 9) * (0.3 + 0.4 * swell)
    shim = sy.shimmer(d, 2100, 26) * swell
    ch = sy.mixdown([choirs * swell, write * 0.45, shim * 0.35, sy.pad(146.8, d, cutoff=900, attack=1.0) * 0.25])
    sy.save(pack, "book_dw_charge", sy.reverb(ch, 0.9, 0.3), volume=0.75, max_distance=24)

    # release: the sentence ignites -- impact, struck bells, a bright held chord, rising air
    rel = sy.at(1.6, (0.0, sy.thump(0.6, 160, 48, 0.4) * 0.6), (0.0, sy.whoosh(0.5, 600, 5200) * 0.45),
                (0.02, sy.bell(587.3, 1.4) * 0.5), (0.04, sy.bell(1174.7, 1.2) * 0.35),
                (0.03, sy.mixdown([sy.choir(293.7, 1.2, "ah", attack=0.02, release=0.8, bright=1.4),
                                   sy.choir(370.0, 1.2, "ah", voices=4, attack=0.02, release=0.8),
                                   sy.choir(440.0, 1.2, "ee", voices=3, attack=0.02, release=0.8)]) * 0.6),
                (0.05, sy.shimmer(1.0, 2600, 20) * 0.3))
    sy.save(pack, "book_dw_release", sy.reverb(rel, 1.3, 0.4), volume=0.9, max_distance=40)

    # deny: a muted descending pair on a dull bell and the cover softly shutting
    den = sy.at(0.7, (0.0, sy.pluck(392.0, 0.35, 0.2) * 0.5), (0.13, sy.pluck(369.9, 0.45, 0.15) * 0.45),
                (0.18, sy.thump(0.25, 140, 70, 0.6) * 0.35), (0.16, page_flip(0.1, 1800) * 0.25))
    sy.save(pack, "book_dw_deny", sy.reverb(sy.lowpass(den, 2600), 0.8, 0.25), volume=0.6, max_distance=16)


# ========================================================================================== icons
def icon(m, anims):
    by = {a.name: a for a in anims}
    PV["open"] = 0.0
    pose = by["idle"].pose(0.0)
    hide = ("dr", "ln", "spread_glow", "rb", "pg")
    img = render(m, pose, yaw=32, pitch=14, size=(32, 32), bg=(0, 0, 0, 0), ss=8, margin=0.04, hide=hide)
    a = np.asarray(img).astype(float)
    alpha = a[..., 3]
    a[..., 3] = np.where(alpha > 110, 255, 0)
    # dark 1px outline so the book reads on any inventory background
    on = a[..., 3] > 0
    pad = np.pad(on, 1)
    nb = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
    ring_ = nb & ~on
    a[ring_] = [46, 34, 18, 230]
    a[..., :3] = np.clip(a[..., :3] * 1.06, 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA"), render(m, pose, yaw=32, pitch=14, size=(160, 160),
                                                               bg=(0, 0, 0, 0), ss=2, margin=0.04, hide=hide)


def pack_icon(book_img):
    """256x256 emblem: the three Grimoires as medallions on a First Word seal."""
    S = 256
    y, x = np.mgrid[0:S, 0:S]
    u, v = (x + 0.5) / S * 2 - 1, (y + 0.5) / S * 2 - 1
    r = np.hypot(u, v)
    bg = np.zeros((S, S, 4))
    c0, c1 = tex.rgb("#1b2350"), tex.rgb("#070914")
    bg[..., :3] = c0 + (c1 - c0) * np.clip(r, 0, 1)[..., None]
    bg[..., 3] = 1
    img = Image.fromarray((bg * 255).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(img)
    gold, wg = (201, 162, 74, 255), (255, 243, 196, 255)
    d.ellipse((10, 10, S - 10, S - 10), outline=gold, width=3)
    d.ellipse((24, 24, S - 24, S - 24), outline=(201, 162, 74, 160), width=1)
    # a ring of First Word letters between the two circles
    for k in range(22):
        g = glyphs.bitmap(FW[(k * 5) % len(FW)])
        a = 2 * math.pi * k / 22
        cx, cy = S / 2 + 106 * math.sin(a), S / 2 - 106 * math.cos(a)
        for gy in range(g.shape[0]):
            for gx in range(g.shape[1]):
                if g[gy, gx]:
                    d.rectangle((cx - 4 + gx * 1.6, cy - 5 + gy * 1.6, cx - 4 + gx * 1.6 + 1.2, cy - 5 + gy * 1.6 + 1.2), fill=wg)

    def medal(cx, cy, rr, fill, rim, draw_fn):
        glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse((cx - rr - 8, cy - rr - 8, cx + rr + 8, cy + rr + 8), fill=rim[:3] + (110,))
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(7)))
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=fill, outline=rim, width=3)
        draw_fn(cx, cy, rr)

    def stamp(rows, cx, cy, px, col):
        g = glyphs.bitmap(rows)
        h, w = g.shape
        for gy in range(h):
            for gx in range(w):
                if g[gy, gx]:
                    x0, y0 = cx - w * px / 2 + gx * px, cy - h * px / 2 + gy * px
                    d.rectangle((x0, y0, x0 + px - 1, y0 + px - 1), fill=col)

    def dream(cx, cy, rr):
        stamp(glyphs.DREAM["moon"], cx - 10, cy - 4, 5, (255, 236, 214, 255))
        stamp(glyphs.DREAM["door"], cx + 12, cy + 6, 3, (106, 74, 110, 255))

    def dragon(cx, cy, rr):
        stamp(glyphs.DRACONIC[2], cx, cy, 6, (255, 226, 160, 255))
        for k in range(3):
            d.line((cx - 26 + k * 9, cy + 26, cx - 12 + k * 9, cy - 24), fill=(224, 118, 42, 200), width=2)

    medal(70, 172, 40, (232, 180, 200, 255), (255, 217, 184, 255), dream)
    medal(186, 172, 40, (138, 106, 58, 255), (233, 223, 198, 255), dragon)

    def divine(cx, cy, rr):
        b = book_img.resize((int(rr * 1.9), int(rr * 1.9)), Image.LANCZOS)
        img.alpha_composite(b, (int(cx - b.width / 2), int(cy - b.height / 2)))
    medal(128, 96, 58, (43, 63, 143, 255), (255, 243, 196, 255), divine)
    return img


# ============================================================================================ build
def build(pack):
    mt = M_()
    build_particles(pack)
    build_sounds(pack)

    # ---- held book (attachable)
    bm = book_model(mt)
    ba = book_anims()
    write_attachable(pack, bm, ba)
    by = {a.name: a for a in ba}
    print(f"    book_dw: {bm.cube_count()} cubes, {len(bm.order)} bones, tex {bm.tex_size}")

    # ---- selection vision
    vms = [vision_model(k, mt) for k in range(6)]
    va = vision_anims()
    pack.actor("book_dw_vision", vms[0], va, VISION_STATES, kinds=vms[1:], lifetime=30, display="Codex Vision", blend=0.0)
    # ---- charge construct
    cms = [charge_model(k, mt) for k in range(6)]
    ca = charge_anims()
    pack.actor("book_dw_charge", cms[0], ca, CHARGE_STATES, kinds=cms[1:], lifetime=120, display="Rising Word", blend=0.1)
    print("    vision cubes", [v.cube_count() for v in vms], "charge cubes", [c.cube_count() for c in cms],
          "bones", [len(c.order) for c in cms], "tex", [c.tex_size for c in cms])

    # ---- icons + item texture atlas (all three books) + pack icons
    ic, big = icon(bm, ba)
    ip = os.path.join(pack.rp, "textures", "items", f"grimoire_{ITEM}.png")
    os.makedirs(os.path.dirname(ip), exist_ok=True)
    ic.save(ip)
    _write(os.path.join(pack.rp, "textures", "item_texture.json"), {
        "resource_pack_name": "grimoire", "texture_name": "atlas.items",
        "texture_data": {f"grimoire_{n}": {"textures": f"textures/items/grimoire_{n}"}
                         for n in ("divine_word", "dream_nightmare", "elemental_dragon")}})
    pi = pack_icon(big)
    pi.save(os.path.join(pack.rp, "pack_icon.png"))
    pi.save(os.path.join(pack.bp, "pack_icon.png"))

    # ---- previews (contact sheets)
    if getattr(pack.preview, "enabled", False):
        from kit.pack import PREVIEW
        os.makedirs(PREVIEW, exist_ok=True)
        ic.resize((128, 128), Image.NEAREST).save(os.path.join(PREVIEW, "book_dw_icon.png"))
        pi.save(os.path.join(PREVIEW, "book_dw_packicon.png"))
    PV["open"] = 0.0
    pack.preview("book_dw_closed", bm, [[(by["idle"], 0.6), (by["open"], 0.6)],
                                        [(by["idle"], 1.4), (by["open"], 1.4), (by["turn"], 0.4)]],
                 views=((25, 12), (155, 12), (-60, 8), (0, 0)), cell=(360, 360))
    PV["open"] = 1.0
    pack.preview("book_dw_open", bm, [[(by["idle"], 0.6), (by["open"], 0.6)], [(by["idle"], 1.3), (by["open"], 1.3)]],
                 views=((15, 25), (-40, 35), (0, 70)), cell=(360, 360))
    PV["open"] = 0.0
    vb = {a.name: a for a in va}
    for k in (0, 3):
        pack.preview(f"book_dw_vision_k{k}", vms[k], [(vb["show"], 0.3), (vb["show"], 0.7), (vb["show"], 0.95)],
                     views=((15, 20), (0, 50)), cell=(300, 300))
    cb = {a.name: a for a in ca}
    for k in range(6):
        pack.preview(f"book_dw_charge_k{k}", cms[k], [(cb["form"], 0.6), (cb["loop"], 0.3)],
                     views=((0, 0), (35, 15)), cell=(440, 440))
