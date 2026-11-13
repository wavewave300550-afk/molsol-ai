"""Grimoire 02 - The Unawakened Codex (Dream & Nightmare), worker M2.

Produces
  * the held 3D book (attachable for grimoire:dream_nightmare): ceramic cover with miniature
    architecture, a forced-perspective miniature bedroom embedded in the cover, a spine that is a
    little open tower with a turning spiral staircase, idle dreaming / page-turn flourish on sneak /
    open-and-rise while Use is held, plus a recurring "bad dream" in which nightmare geometry grows
    out of the cover (spires, cracks, hands under the bed, an eye in the window).
  * actor book_dn_vision  (selection: a page folds into a little door that opens on the spell's
    miniature scene; kinds 0-5 = spell index)
  * actor book_dn_charge  (charge construct: the spell's miniature centrepiece plus orbiting rooms,
    doors, stairs and dream objects; nightmare-tinted for nightmare spells; kinds 0-5)
  * sounds grimoire.book_dn_select / _charge / _release / _deny (+ _door used by the vision)
  * particles grimoire:book_dn_mote / _burst (+ _spill used by the vision)
  * inventory icon textures/items/grimoire_dream_nightmare.png
"""
import math
import os

import numpy as np
from PIL import Image

from kit import glyphs, synth as sy, tex
from kit.anim import LIFE, Anim, M, animations_file
from kit.geo import Mat, Model
from kit.pack import PREVIEW, _write
from kit.render import render, sheet

from .a_fx_common import particles

# =====================================================================================
# HELD-BOOK PLACEMENT - every offset that positions the attachable lives here.
# Units: 1/16 block, bb space of the bound hand bone (rightItem / leftItem):
#   +X = holder's right, +Y = up along the arm, -Z = forward.  Rotations in degrees, X then Y then Z.
# The book is authored upright, front cover facing -Z, spine on the left as the reader sees it,
# centred on the origin, about 32 x 38 x 9 units; PLACE_SCALE brings it to ~0.6 x 0.7 block.
#
# Third person: the arm hangs (almost) straight, so the hand frame ~ the body frame.  The book
#   floats a hand's width outward and slightly forward of the fist at hip height, turned so its
#   cover faces back-and-outward (readable from the usual over-the-shoulder camera).
# First person: the arm is raised forward, so in the hand frame -Y points into the screen and
#   -Z points up.  (90, 180, 0) maps the book's up to screen-up and its cover toward the camera;
#   the extra few degrees turn it toward the screen centre.  The offset lifts it above the fist and
#   slides it toward the middle of the screen so it never covers the crosshair.
FP_POS = (-2.5, -4.0, -6.0)
FP_ROT = (82.0, 168.0, 0.0)
FP_SCALE = 0.26
TP_POS = (4.5, 2.0, -3.0)
TP_ROT = (-8.0, -140.0, 0.0)
TP_SCALE = 0.32
RISE = 9.0          # how far (book units) the book rises while Use is held
OPEN_TILT = 16.0    # tilt back (deg) while open so the pages face the reader
# =====================================================================================

ITEM_ID = "grimoire:dream_nightmare"
ITEM_SUFFIX = "dream_nightmare"
GEO = "book_dn"

# palette (DEVELOPING.md section 2)
IVORY, PEACH, PINK, SGOLD, PBLUE = "#f4ecdc", "#ffd9b8", "#e8b4c8", "#e9cf8a", "#bcd6f0"
FGOLD = "#c9ad6a"
INDIGO, MAUVE, BURG, AIVORY, CGRAY = "#2a2d52", "#6a4a6e", "#6e2f3a", "#cfc6b0", "#8b8f9a"
SICK = "#9aa58a"   # muted unnatural accent

VISION_STATES = {"hidden": 0, "show": 1}
CHARGE_STATES = {"hidden": 0, "form": 1, "loop": 2, "release": 3, "cancel": 4}
VISION_LEN, FORM_LEN, RELEASE_LEN, CANCEL_LEN = 1.2, 1.5, 0.5, 0.4
VS, CS, FS = 0.55, 1.3, 1.2      # centrepiece scale in the vision / in the charge construct; fragment scale

DREAM_SCRIPT = list(glyphs.DREAM.values())


# ------------------------------------------------------------------------------- helpers
def spin(rate):
    return M(f"q.life_time*{rate}", lambda t: t * rate)


def _nm_fn(t):
    return min(1.0, max(0.0, (math.sin(math.radians(t * 15.0)) - 0.7) * 3.4))


# "bad dream" amount for the held book: 0 most of the time, ramps to 1 for ~4 s every 24 s
NM = M("math.clamp((math.sin(q.life_time*15)-0.7)*3.4,0,1)", _nm_fn)


class K:
    """Placement wrapper: scale + offset (+ optional X mirror) for building parts in a model.

    mirror=True converts 'reader space' (x grows to the reader's right when facing the front) into
    bb space (+X is the model's right = the reader's left): x -> -x, ry -> -ry, rz -> -rz."""

    def __init__(self, m, s=1.0, off=(0, 0, 0), pre="", mirror=False):
        self.m, self.s, self.off, self.pre, self.mx = m, s, off, pre, mirror

    def T(self, p):
        x = -p[0] if self.mx else p[0]
        return (self.off[0] + x * self.s, self.off[1] + p[1] * self.s, self.off[2] + p[2] * self.s)

    def R(self, r):
        if r is None:
            return None
        return (r[0], -r[1], -r[2]) if self.mx else tuple(r)

    def n(self, name):
        return self.pre + name

    def bone(self, name, parent=None, pivot=(0, 0, 0), rot=(0, 0, 0)):
        return self.m.bone(self.pre + name, parent, pivot=self.T(pivot), rot=self.R(rot))

    def box(self, b, c, size, mat, rot=None, pivot=None, **kw):
        return b.box(self.T(c), tuple(abs(v) * self.s for v in size), mat, rot=self.R(rot),
                     pivot=self.T(pivot) if pivot else None, **kw)

    def plane(self, b, axis, c, w, h, mat, rot=None, pivot=None, **kw):
        return b.plane(axis, self.T(c), w * self.s, h * self.s, mat, rot=self.R(rot),
                       pivot=self.T(pivot) if pivot else None, **kw)


def MR(v):
    """Mirror an animation rotation channel written in reader space."""
    if isinstance(v, dict):
        return {t: MR(x) for t, x in v.items()}
    return (v[0], -v[1], -v[2])


def MP(v):
    if isinstance(v, dict):
        return {t: MP(x) for t, x in v.items()}
    return (-v[0], v[1], v[2])


def _P(key, fn, mode="solid", directional=True, spatial=False):
    return Mat(fn, "bdn_" + key, mode=mode, directional=directional, spatial=spatial)


rgb, mix = tex.rgb, tex.mix


def _dist_edge(ctx):
    ix, iy = tex.px(ctx)
    return np.minimum(np.minimum(ix, ctx.w - 1 - ix), np.minimum(iy, ctx.h - 1 - iy))


def bm(rows):
    return [r.replace(".", " ") for r in rows]


CRESCENT = bm(["...####..", "..###....", ".###.....", "###......", "###......", "###......", ".###.....",
               "..###....", "...####.."])
STAR = bm(["...#...", "...#...", ".#####.", "#######", ".#####.", "..#.#..", ".#...#."])
NOTE = bm(["..####", "..#..#", "..#..#", "..#..#", "###.##", "###.##", "###..."])
NOTE_BROKEN = bm(["...##.", "..#..#", "..#...", ".##..#", "###.##", "##..##", "#....."])
HOUSE = bm(["....##....", "...####...", "..######..", ".########.", "##########", "#.##..##.#", "#.##..##.#",
            "##########", "####..####", "####..####", "####..####"])
ARCH_DOOR = bm(["..####..", ".######.", "########", "###..###", "##....##", "##....##", "##....##", "##....##",
                "##....##", "########"])
STAIR_SIL = bm(["......##", "......##", "....####", "....####", "..######", "..######", "########", "########"])
HORSE = bm([".......##.", "......###.", ".....####.", "#########.", "#########.", ".########.", ".#.#..#.#.",
            ".#.#..#.#."])
KEY = glyphs.DREAM["key"]
HAND = bm(["..#.#.#..", "..#.#.#.#", "#.#.#.#.#", "#.#.#.#.#", "#########", ".#######.", "..#####..", "..#####..",
           "...###..."])


# ------------------------------------------------------------------------------- painters
def pearl(base=IVORY, shade="#e2d4bf", gilt=None, crack=0.5, glow=0.0, sheen=0.35, engrave=None, eng_col=FGOLD,
          eng_glow=0.18, key="pearl"):
    """Pearlescent ceramic: soft shading, iridescent pink/blue sheen bands, hairline crackle, engraving."""
    kb, ks, kp, kq, ke = rgb(base), rgb(shade), rgb("#ffdcea"), rgb("#d6e6ff"), rgb(eng_col)

    def fn(ctx):
        U, V = ctx.U, ctx.V
        t = tex.tile(ctx, base, 1, glow)
        col = mix(kb, ks, np.clip((V - 0.2) * 0.6, 0, 1)[..., None])
        s = np.sin((U * 1.4 + V * 0.8) * math.pi * 2 + ctx.variant * 1.9)
        col = mix(col, kp, (np.clip(s, 0, 1) * sheen * 0.35)[..., None])
        col = mix(col, kq, (np.clip(-s, 0, 1) * sheen * 0.35)[..., None])
        ix, iy = tex.px(ctx)
        if crack:
            sv = ctx.variant * 11.0
            c = np.abs(tex.vnoise(ix / 5.0 + sv, iy / 5.0, 81) - tex.vnoise(ix / 5.0 + 9.0, iy / 5.0 + sv, 82))
            col = np.where((c < 0.018 * crack)[..., None], col * 0.86, col)
        t[..., :3] = col
        if engrave is not None:
            m = engrave(ctx)
            t[..., :3] = np.where(m[..., None], ke, t[..., :3])
            t[..., 4] = np.where(m, eng_glow, t[..., 4])
        if gilt is not None and min(ctx.w, ctx.h) >= 6:
            d = _dist_edge(ctx)
            t[..., :3] = np.where((d == 0)[..., None], rgb(gilt), t[..., :3])
        return tex.grain(ctx, t, 0.02)
    return _P(key + base + shade + str(gilt) + str(crack) + str(glow) + str(sheen), fn, directional=engrave is not None)


def eng_cover(ctx):
    """Fine engraved architecture around the cover edge: double border, stair-step band, tiny arches."""
    ix, iy = tex.px(ctx)
    d = _dist_edge(ctx)
    m = (d == 3) | (d == 9)
    band = (d >= 5) & (d <= 7)
    step = ((ix + iy) // 2) % 4
    m |= band & (((d == 5) & (step < 2)) | ((d == 7) & (step >= 2)) | ((d == 6) & ((ix + iy) % 4 == 2)))
    stars = (tex._hash(ix, iy, 7) > 0.992) & (d > 11)
    return m | stars


def eng_back(ctx):
    """Back cover: an engraved facade - rows of arched windows, a great door and a crescent."""
    U, V = ctx.U, ctx.V
    pxu, pxv = 1.0 / ctx.w, 1.0 / ctx.h
    cu = (U * 5) % 1.0
    row = V * 7
    cv = row % 1.0
    win = (np.abs(cu - 0.5) < 0.22) & (cv > 0.25) & (cv < 0.85) & (V > 0.08) & (V < 0.72)
    win |= (np.hypot((cu - 0.5) / 0.22, (cv - 0.25) / 0.16) < 1) & (V > 0.08) & (V < 0.72)
    inner = (np.abs(cu - 0.5) < 0.22 - pxu * 5 * 1.1) & (cv > 0.25 + pxv * 7 * 1.1) & (cv < 0.85 - pxv * 7)
    inner |= (np.hypot((cu - 0.5) / (0.22 - pxu * 6), (cv - 0.25) / (0.16 - pxv * 7)) < 1) & (cv <= 0.25)
    m = win & ~inner
    door = (np.abs(U - 0.5) < 0.13) & (V > 0.76) & (V < 0.97)
    door |= (np.hypot((U - 0.5) / 0.13, (V - 0.76) / 0.06) < 1)
    dinner = (np.abs(U - 0.5) < 0.13 - pxu * 1.2) & (V > 0.76) & (V < 0.97 - pxv)
    dinner |= (np.hypot((U - 0.5) / (0.13 - pxu * 1.2), (V - 0.76) / (0.06 - pxv)) < 1)
    m |= door & ~dinner
    d = _dist_edge(ctx)
    m |= (d == 2)
    m |= (np.abs(V - 0.74) < pxv * 0.6)
    return m


def page_edge():
    kc, kg = rgb("#f3e6cc"), rgb("#e2c88e")

    def fn(ctx):
        t = tex.tile(ctx, "#f3e6cc", 1, 0.05)
        ix, iy = tex.px(ctx)
        c = ix if ctx.face in ("east", "west", "north", "south") else iy
        col = mix(kc, kg, 0.55)
        t[..., :3] = np.where(((c % 2) == 0)[..., None], col, col * 0.9)
        return tex.grain(ctx, t, 0.03)
    return _P("pageedge", fn)


def leaf_mat(seed=0):
    """A page: warm paper, ruled lines in faded ink, dream pictograms sketched in pink and gold."""
    pics = DREAM_SCRIPT
    kp, ki, kg = rgb("#f7ecd6"), rgb("#b89a8a"), rgb(SGOLD)

    def fn(ctx):
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, "#f7ecd6", 1, 0.12)
        t[..., :3] = mix(kp, rgb("#efdcc0"), np.clip(np.abs(ctx.U - 0.5) * 1.2, 0, 1)[..., None])
        lines = ((iy % 4) == 3) & (ix > 4) & (ix < ctx.w - 4) & (tex._hash(ix // 6, iy // 4, seed + 3) > 0.25)
        t[..., :3] = np.where(lines[..., None], mix(kp, ki, 0.45), t[..., :3])
        # two pictograms, inked
        for k, (cu, cv) in enumerate(((0.3, 0.3), (0.68, 0.66))):
            g = glyphs.bitmap(pics[(seed * 3 + k * 5) % len(pics)])
            gh, gw = g.shape
            sc = max(1, ctx.w // 30)
            ox, oy = int(cu * ctx.w - gw * sc / 2), int(cv * ctx.h - gh * sc / 2)
            gx, gy = (ix - ox) // sc, (iy - oy) // sc
            ok = (gx >= 0) & (gx < gw) & (gy >= 0) & (gy < gh)
            on = ok & g[np.clip(gy, 0, gh - 1), np.clip(gx, 0, gw - 1)]
            t[..., :3] = np.where(on[..., None], kg if k == 0 else rgb(PINK) * 0.85, t[..., :3])
            t[..., 4] = np.where(on, 0.5, t[..., 4])
        d = _dist_edge(ctx)
        t[..., :3] = np.where((d == 0)[..., None], kg, t[..., :3])
        return tex.grain(ctx, t, 0.02)
    return _P(f"leaf{seed}", fn, directional=False)


def endpaper():
    """Inside of the cover: marbled dusty-pink endpaper with a printed staircase-and-moon frieze."""
    def fn(ctx):
        U, V = ctx.U, ctx.V
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, PINK, 1, 0.15)
        n = tex.fbm(ix / 7.0, iy / 5.0, 61)
        sw = np.sin(ix * 0.25 + n * 9.0)
        col = mix(rgb("#e8b4c8"), rgb("#f6dbe2"), (sw * 0.5 + 0.5)[..., None])
        col = mix(col, rgb("#bcd6f0"), np.clip((n - 0.62) * 3, 0, 1)[..., None])
        d = _dist_edge(ctx)
        fr = (d >= 3) & (d <= 4)
        col = np.where(fr[..., None], rgb(SGOLD), col)
        stp = (d >= 5) & (d <= 8) & (((ix + iy) // 2) % 4 < 2)
        col = np.where(stp[..., None], rgb("#fff1dc"), col)
        t[..., :3] = col
        t[..., 4] = np.where(fr, 0.4, 0.15)
        return tex.grain(ctx, t, 0.02)
    return _P("endpaper", fn)


def page_open():
    """The first page (visible when the book opens): an architect's dream floor-plan in glowing ink."""
    def fn(ctx):
        U, V = ctx.U, ctx.V
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, "#f7ecd6", 1, 0.2)
        cx, cy = U * 2 - 1, V * 2 - 1
        r = np.hypot(cx * 0.8, cy * 0.6)
        t[..., :3] = mix(rgb("#fff4dc"), rgb("#efd8bc"), np.clip(r, 0, 1)[..., None])
        t[..., 4] = np.clip(0.55 - r * 0.45, 0.12, 1)
        gx, gy = (U * 6) % 1.0, (V * 8) % 1.0
        wall = ((gx < 0.06) | (gy < 0.05)) & (r < 0.95)
        gap = (np.abs(gy - 0.5) < 0.16) & (gx < 0.06) | (np.abs(gx - 0.5) < 0.14) & (gy < 0.05)
        wall &= ~gap
        arc = (np.abs(np.hypot(gx - 0.06, gy - 0.34) - 0.3) < 0.035) & (gx > 0.06) & (gy > 0.34) & (r < 0.95)
        stairs = (((ix // 2) + (iy // 2)) % 3 == 0) & (np.abs(cx - 0.5) < 0.12) & (np.abs(cy + 0.4) < 0.2)
        m = wall | arc | stairs
        t[..., :3] = np.where(m[..., None], rgb("#c98aa0"), t[..., :3])
        t[..., 4] = np.where(m, 0.75, t[..., 4])
        moon = (np.hypot(cx, cy + 0.05) < 0.17) & (np.hypot(cx - 0.07, cy + 0.08) > 0.14)
        t[..., :3] = np.where(moon[..., None], rgb("#fff0b0"), t[..., :3])
        t[..., 4] = np.where(moon, 1.0, t[..., 4])
        return tex.grain(ctx, t, 0.02)
    return _P("pageopen", fn)


def floor_mat():
    """Perspective checker floor (front -> back narrows and compresses) with a rug and far glow."""
    def fn(ctx):
        U, V = ctx.U, ctx.V   # up face: V=0 front edge, V=1 back edge
        t = tex.tile(ctx, PEACH, 1, 0.15)
        wv = 1 - 0.36 * V
        x = (U - 0.5) / wv
        d = -np.log(1 - 0.72 * V)
        chk = (np.floor(x * 7 + 0.5) + np.floor(d * 7)) % 2
        col = np.where(chk[..., None] > 0, rgb("#f6e3cf"), rgb("#f2c9b4"))
        rug = ((x / 0.34) ** 2 + ((V - 0.42) / 0.26) ** 2) < 1
        rim = rug & (((x / 0.29) ** 2 + ((V - 0.42) / 0.21) ** 2) >= 1)
        col = np.where(rug[..., None], rgb(PINK), col)
        col = np.where(rim[..., None], rgb(SGOLD), col)
        col = mix(col, rgb("#fff1d6"), (V ** 2 * 0.55)[..., None])
        t[..., :3] = col
        t[..., 4] = 0.18 + 0.5 * V ** 2
        return t
    return _P("floor", fn)


def ceiling_mat():
    def fn(ctx):
        U, V = ctx.U, ctx.V   # down face: V=0 back, V=1 front
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, PBLUE, 1, 0.25)
        t[..., :3] = mix(rgb("#fbe7d8"), rgb("#9fbde2"), np.clip(V, 0, 1)[..., None])
        st = tex._hash(ix, iy, 31) > 0.93
        t[..., :3] = np.where(st[..., None], rgb("#fff6c8"), t[..., :3])
        t[..., 4] = np.where(st, 1.0, 0.25 + 0.4 * (1 - V))
        return t
    return _P("ceiling", fn)


def wall_mat(nm=False):
    """Wallpaper whose stripes crowd together toward the back (forced perspective) and hazes out."""
    c0, c1 = (PINK, PEACH) if not nm else (MAUVE, AIVORY)

    def fn(ctx):
        U, V = ctx.U, ctx.V
        b = U if ctx.face == "west" else 1 - U       # 0 front .. 1 back
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, c0, 1, 0.1)
        f = -np.log(1 - 0.75 * b) * 6
        stripe = (f % 1.0) < 0.35
        col = np.where(stripe[..., None], rgb(c1), rgb(c0))
        dots = (tex._hash(ix // 3, iy // 3, 11) > 0.9) & (ix % 3 == 1) & (iy % 3 == 1) & ~stripe
        col = np.where(dots[..., None], rgb(SGOLD), col)
        wains = V > 0.78
        col = np.where(wains[..., None], rgb("#f1d2b8") if not nm else rgb(CGRAY), col)
        col = np.where((np.abs(V - 0.78) < 0.012)[..., None], rgb(SGOLD), col)
        col = mix(col, rgb("#fff1d6"), (b ** 1.5 * 0.55)[..., None])
        t[..., :3] = col
        t[..., 4] = 0.1 + 0.45 * b ** 2
        return tex.grain(ctx, t, 0.02)
    return _P(f"wall{nm}", fn)


def backwall_mat():
    """Back wall: wallpaper with a doorway onto an endless corridor of receding door frames whose far
    end glows - the room appears much deeper than the book is thick."""
    cu, cv, hw, hh = 0.612, 0.667, 0.17, 0.33

    def fn(ctx):
        U, V = ctx.U, ctx.V
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, PINK, 1, 0.35)
        col = mix(rgb(PINK), rgb("#f7d6c8"), (V * 0.6)[..., None])
        dots = (tex._hash(ix // 3, iy // 3, 12) > 0.93) & (ix % 3 == 1) & (iy % 3 == 1)
        col = np.where(dots[..., None], rgb(SGOLD), col)
        glow = np.full(U.shape, 0.42)
        # corridor: nested arched frames toward a vanishing point slightly above centre
        layer = np.full(U.shape, -1)
        for k in range(8):
            s = 0.74 ** k
            vx, vy = cu, cv - hh * 0.25 * (1 - s)
            inside = (np.abs(U - vx) < hw * s) & (V < vy + hh * s) & (V > vy - hh * s * 0.55)
            inside |= (np.hypot((U - vx) / (hw * s), (V - (vy - hh * s * 0.55)) / (hh * s * 0.45)) < 1)
            layer = np.where(inside, k, layer)
        palette = [rgb("#b97b8e"), rgb("#f3d2c0"), rgb("#9a6f8f"), rgb("#f7e0cc"), rgb("#b88aa6"),
                   rgb("#fbe9d4"), rgb("#ffe7b0"), rgb("#fffbe8")]
        for k in range(8):
            col = np.where((layer == k)[..., None], palette[k], col)
            glow = np.where(layer == k, 0.45 + 0.08 * k, glow)
        # frame lines between layers
        pad = np.pad(layer, 1, mode="edge")
        edge = (pad[1:-1, 1:-1] != pad[:-2, 1:-1]) | (pad[1:-1, 1:-1] != pad[1:-1, :-2])
        col = np.where((edge & (layer >= 0))[..., None], rgb("#e9c77a"), col)
        col = np.where((layer == 7)[..., None], rgb("#fffdf0"), col)
        glow = np.where(layer == 7, 1.0, glow)
        t[..., :3] = col
        t[..., 4] = glow
        return t
    return _P("backwall", fn)


def sky_pane(nm=False):
    """Window glass with a sky: dream = pale blue to peach with a crescent; nightmare = indigo with an eye."""
    def fn(ctx):
        U, V = ctx.U, ctx.V
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, PBLUE, 1, 0.85)
        d = _dist_edge(ctx)
        if not nm:
            t[..., :3] = mix(rgb("#a9c9ee"), rgb("#ffd9b8"), V[..., None])
            cx, cy = U * 2 - 1.3, V * 2 - 0.6
            moon = (np.hypot(cx, cy) < 0.32) & (np.hypot(cx - 0.14, cy - 0.06) > 0.26)
            t[..., :3] = np.where(moon[..., None], rgb("#fff6c8"), t[..., :3])
            st = tex._hash(ix, iy, 5) > 0.93
            t[..., :3] = np.where(st[..., None], rgb("#ffffff"), t[..., :3])
        else:
            t[..., :3] = mix(rgb("#1d1f3c"), rgb("#4a2a40"), V[..., None])
            u, v = U * 2 - 1, 1 - V * 2
            almond = np.abs(v) <= (1 - u ** 2) * 0.5
            r = np.hypot(u, v)
            t[..., :3] = np.where(almond[..., None], rgb(AIVORY), t[..., :3])
            t[..., :3] = np.where((almond & (r < 0.36))[..., None], rgb("#9a2f45"), t[..., :3])
            t[..., :3] = np.where((almond & (np.abs(u) < 0.07) & (r < 0.33))[..., None], rgb("#0c0c18"), t[..., :3])
            t[..., 4] = np.where(almond, 0.95, 0.5)
        mull = ((np.abs(U - 0.5) < 0.6 / ctx.w) | (np.abs(V - 0.5) < 0.6 / ctx.h))
        t[..., :3] = np.where((mull | (d == 0))[..., None], rgb(SGOLD) if not nm else rgb(CGRAY), t[..., :3])
        t[..., 4] = np.where(mull | (d == 0), 0.2, t[..., 4])
        return t
    return _P(f"sky{nm}", fn)


def framed_window(pal):
    """A cube face that is a little lit window in a coloured frame (fragments, towers)."""
    def fn(ctx):
        U, V = ctx.U, ctx.V
        t = tex.tile(ctx, pal["frame"], 1, 0.0)
        inner = (np.abs(U - 0.5) < 0.34) & (V > 0.18) & (V < 0.88)
        inner |= (np.hypot((U - 0.5) / 0.34, (V - 0.2) / 0.14) < 1)
        t[..., :3] = np.where(inner[..., None], mix(rgb(pal["glass"]), rgb(pal["glow"]), V[..., None]), t[..., :3])
        t[..., 4] = np.where(inner, 0.9, 0.0)
        mull = inner & ((np.abs(U - 0.5) < 0.05) | (np.abs(V - 0.55) < 0.04))
        t[..., :3] = np.where(mull[..., None], rgb(pal["frame"]), t[..., :3])
        t[..., 4] = np.where(mull, 0.0, t[..., 4])
        return tex.grain(ctx, t, 0.03)
    return _P("fwin" + pal["name"], fn)


def door_panel(pal, stretched=False):
    """Painted door leaf: four sunk panels, a gilt knob; nightmare doors get stretched panels."""
    def fn(ctx):
        U, V = ctx.U, ctx.V
        t = tex.tile(ctx, pal["wood"], 1, 0.0)
        ix, iy = tex.px(ctx)
        cu, cv = (U * 2) % 1.0, (V * (2 if not stretched else 3)) % 1.0
        sunk = (np.abs(cu - 0.5) < 0.3) & (np.abs(cv - 0.5) < 0.36)
        col = np.where(sunk[..., None], rgb(pal["wood"]) * 0.82, rgb(pal["wood"]))
        rim = sunk & ~((np.abs(cu - 0.5) < 0.24) & (np.abs(cv - 0.5) < 0.3))
        col = np.where(rim[..., None], rgb(pal["trim"]), col)
        knob = np.hypot((U - 0.82) * ctx.w, (V - 0.55) * ctx.h) < max(0.8, ctx.w * 0.07)
        col = np.where(knob[..., None], rgb(pal["trim"]), col)
        t[..., :3] = col
        t[..., 4] = np.where(knob, 0.6, 0.0)
        return tex.grain(ctx, t, 0.03)
    return _P("door" + pal["name"] + str(stretched), fn)


def ink_door():
    """The vision page's centre panel: paper with a door drawn in pink ink, writing around it."""
    def fn(ctx):
        U, V = ctx.U, ctx.V
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, "#f7ecd6", 1, 0.25)
        u, v = U * 2 - 1, V * 2 - 1
        out = (np.abs(u) < 0.72) & (v > -0.62) & (v < 0.86)
        out |= (np.hypot(u / 0.72, (v + 0.62) / 0.3) < 1)
        inn = (np.abs(u) < 0.6) & (v > -0.55) & (v < 0.8)
        inn |= (np.hypot(u / 0.6, (v + 0.55) / 0.24) < 1)
        line = out & ~inn
        pan = inn & ((np.abs(np.abs(u) - 0.3) > 0.2) | (np.abs(np.abs(v - 0.15) - 0.35) > 0.25)) & \
            ((np.abs(np.abs(u) - 0.3) < 0.23) & (np.abs(np.abs(v - 0.15) - 0.35) < 0.28))
        knob = np.hypot(u - 0.42, v - 0.15) < 0.07
        col = np.where(line[..., None], rgb("#c77b95"), t[..., :3])
        col = np.where(pan[..., None], rgb("#d9a0b4"), col)
        col = np.where(knob[..., None], rgb(SGOLD), col)
        lines = ((iy % 3) == 2) & ~out & (tex._hash(ix // 3, iy // 3, 77) > 0.35)
        col = np.where(lines[..., None], rgb("#b7a08e"), col)
        t[..., :3] = col
        t[..., 4] = np.where(line | knob, 0.7, 0.25)
        return t
    return _P("inkdoor", fn)


def crack_overlay():
    """Cut-out web of nightmare cracks laid just over the cover (shows during the bad dream)."""
    def fn(ctx):
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, BURG, 0.0, 0.45)
        c = np.abs(tex.vnoise(ix / 6.0, iy / 6.0, 91) - tex.vnoise(ix / 6.0 + 17.0, iy / 6.0 + 3.0, 92))
        c2 = np.abs(tex.vnoise(ix / 3.0 + 5, iy / 3.0, 93) - tex.vnoise(ix / 3.0 + 31.0, iy / 3.0, 94))
        on = (c < 0.03) | ((c2 < 0.02) & (tex.vnoise(ix / 9.0, iy / 9.0, 95) > 0.55))
        t[..., :3] = np.where((c < 0.012)[..., None], rgb("#c0485e"), rgb(BURG))
        t[..., 3] = np.where(on, 1.0, 0.0)
        return t
    return _P("cracks", fn)


def tapestry(nm=False):
    """Woven tapestry panel: dream half (peach/pink, moons, stars) or nightmare half (indigo, eyes, mouths)."""
    def fn(ctx):
        U, V = ctx.U, ctx.V
        ix, iy = tex.px(ctx)
        base, band = ((PEACH, PINK) if not nm else (INDIGO, BURG))
        t = tex.tile(ctx, base, 1, 0.25)
        col = np.where((((iy // 2) % 6) == 0)[..., None], rgb(band), rgb(base))
        w = ((ix + iy) % 2) * 0.06
        col = col * (1 - w)[..., None]
        u, v = U * 2 - 1, V * 2 - 1
        if not nm:
            moon = (np.hypot(u, v + 0.15) < 0.42) & (np.hypot(u - 0.2, v + 0.2) > 0.34)
            col = np.where(moon[..., None], rgb("#fff3c0"), col)
            st = (tex._hash(ix // 2, iy // 2, 41 + ctx.variant) > 0.9)
            col = np.where(st[..., None], rgb(SGOLD), col)
            g = moon | st
        else:
            almond = (np.abs(v + 0.2) <= (1 - (u / 0.7) ** 2) * 0.28) & (np.abs(u) < 0.7)
            pupil = np.hypot(u, v + 0.2) < 0.12
            mouth = (((u / 0.32) ** 2 + ((v - 0.45) / 0.22) ** 2) < 1)
            col = np.where(almond[..., None], rgb(AIVORY), col)
            col = np.where((almond & pupil)[..., None], rgb("#a33a4a"), col)
            col = np.where(mouth[..., None], rgb("#120e1c"), col)
            g = almond
        fr = (iy >= ctx.h - 2) & (ix % 2 == 0)
        t[..., :3] = col
        t[..., 3] = np.where(fr, 0.0, 1.0)
        t[..., 4] = np.where(g, 0.85, 0.2)
        return t
    return _P(f"tap{nm}", fn)


def backdrop(kind):
    """The painted environment seen through the vision's little door (one per spell)."""
    def fn(ctx):
        U, V = ctx.U, ctx.V
        ix, iy = tex.px(ctx)
        u, v = U * 2 - 1, V * 2 - 1
        t = tex.tile(ctx, PEACH, 1, 0.9)
        if kind == 0:   # twilight road with lanterns
            col = mix(rgb("#9fbde2"), rgb("#ffd2b0"), V[..., None])
            road = (np.abs(u - 0.25 * np.sin(v * 3)) < 0.12 + 0.35 * np.clip(v, 0, 1)) & (v > -0.2)
            col = np.where(road[..., None], rgb("#fff4e0"), col)
            lam = (tex._hash(ix // 2, iy // 2, 3) > 0.94) & (v < 0.3)
            col = np.where(lam[..., None], rgb("#ffb27a"), col)
        elif kind == 1:   # dark corridor, burgundy light at the end
            col = mix(rgb("#14152a"), rgb("#3a1a2a"), np.clip(1 - np.abs(u), 0, 1)[..., None])
            for k in range(5):
                s = 0.8 ** k
                fr = (np.abs(np.abs(u) - 0.8 * s) < 0.04) & (np.abs(v) < 0.9 * s) | \
                     (np.abs(np.abs(v) - 0.9 * s) < 0.03) & (np.abs(u) < 0.8 * s)
                col = np.where(fr[..., None], rgb(CGRAY) * (0.9 - k * 0.12), col)
            end = (np.abs(u) < 0.22) & (np.abs(v) < 0.3)
            col = np.where(end[..., None], rgb("#c0485e"), col)
        elif kind == 2:   # one-point-perspective room with doors on every wall, slightly askew
            col = mix(rgb("#ffe0c4"), rgb("#d9b0d0"), V[..., None])
            bx = (np.abs(u - 0.05) < 0.38) & (np.abs(v + 0.05) < 0.4)
            col = np.where(bx[..., None], rgb("#f7d2b8"), col)
            diag = (np.abs(np.abs(u - 0.05) - np.abs(v + 0.05) * 0.95) < 0.04) & ~bx
            col = np.where(diag[..., None], rgb(SGOLD), col)
            for dx in (-0.62, 0.05, 0.7):
                dr = (np.abs(u - dx) < 0.1) & (v > 0.0) & (v < 0.32 if dx == 0.05 else v < 0.55)
                col = np.where(dr[..., None], rgb(MAUVE) if dx > 0.5 else rgb("#c77b95"), col)
            fl = (v > 0.35) & ((((u * 6).astype(int) + (v * 8).astype(int)) % 2) == 0)
            col = np.where(fl[..., None], col * 0.9, col)
        elif kind == 3:   # split: lullaby half / scream half
            col = np.where((u < 0)[..., None], mix(rgb("#ffd9b8"), rgb(PINK), V[..., None]),
                           mix(rgb(INDIGO), rgb(BURG), V[..., None]))
            notes = tex._hash(ix // 3, iy // 3, 9) > 0.9
            col = np.where(notes[..., None], np.where((u < 0)[..., None], rgb(SGOLD), rgb("#c0485e")), col)
        elif kind == 4:   # skyline at dusk
            col = mix(rgb("#bcd6f0"), rgb("#ffd2c0"), V[..., None])
            hgt = 0.2 + 0.5 * tex._hash(np.floor(U * 9), np.zeros_like(U), 17)
            bld = (1 - V) < hgt
            col = np.where(bld[..., None], np.where((u > 0.2)[..., None], rgb(MAUVE), rgb("#f4ecdc")), col)
            win = bld & (tex._hash(ix, iy, 19) > 0.8)
            col = np.where(win[..., None], rgb("#ffd36a"), col)
        else:             # night sky over a bed
            col = mix(rgb("#232a55"), rgb("#8a6aa0"), V[..., None])
            st = tex._hash(ix, iy, 23) > 0.92
            col = np.where(st[..., None], rgb("#fff6c8"), col)
            moon = (np.hypot(u - 0.3, v + 0.5) < 0.25) & (np.hypot(u - 0.4, v + 0.55) > 0.2)
            col = np.where(moon[..., None], rgb("#fff3c0"), col)
        t[..., :3] = col
        return t
    return _P(f"bd{kind}", fn)


# ------------------------------------------------------------------------------- palettes / materials
def palette(name):
    if name == "dream":
        return dict(name=name, wall=IVORY, shade="#e9d6c4", trim=SGOLD, accent=PINK, glass=PBLUE, glow="#ffe6b0",
                    wood="#e7c3a0", dark="#c79a7a", frame="#f1dcc0", spark="#ffe9c6")
    if name == "night":
        return dict(name=name, wall=AIVORY, shade="#8f8a9c", trim=CGRAY, accent=BURG, glass=INDIGO, glow="#b8405a",
                    wood=MAUVE, dark=INDIGO, frame="#4b4566", spark="#c0485e")
    return dict(name=name, wall=PEACH, shade="#c7a3c4", trim=SGOLD, accent=MAUVE, glass="#b9c7a8", glow="#f0d0ff",
                wood="#d9a7b6", dark="#7a5a7e", frame="#e3c0c8", spark="#f0d0ff")


_MAT_CACHE = {}


def mats(pal):
    if pal["name"] in _MAT_CACHE:
        return _MAT_CACHE[pal["name"]]
    nm = pal["name"] == "night"
    d = dict(
        wall=pearl(pal["wall"], pal["shade"], crack=0.9 if nm else 0.4, sheen=0.1 if nm else 0.35),
        trim=tex.metal(pal["trim"], "#fff1c8" if not nm else "#c4c8d4", "#8f7440" if not nm else "#3b3d50", bands=2.0),
        wood=tex.wood(pal["wood"], pal["dark"]),
        win=framed_window(pal),
        door=door_panel(pal, stretched=nm),
        glow=tex.glow_flat(pal["glow"], 1.0, core="#ffffff" if not nm else "#e07080"),
        fabric=tex.fabric(pal["accent"], pal["wall"], stripe_w=2, glow=0.05),
        stone=tex.stone(pal["wall"], pal["shade"], pal["frame"], scale=3, cracks=0.4 if nm else 0.1, edge_dark=0.1,
                        glow_crack=0.4 if nm else 0.0, crack_color=BURG if nm else None),
        dark=tex.speck(pal["dark"], 0.06, edge_dark=0.15),
        moon=tex.bitmap_cut(CRESCENT, "#fff3c0" if not nm else "#d8c8d0", glow=1.0, color2=SGOLD if not nm else MAUVE),
        star=tex.bitmap_cut(STAR, "#fffbe0" if not nm else "#e0a0b0", glow=1.0),
        key=tex.bitmap_cut(KEY, SGOLD if not nm else CGRAY, glow=0.8 if not nm else 0.3, color2="#fff3c4"),
        note=tex.bitmap_cut(NOTE if not nm else NOTE_BROKEN, SGOLD if not nm else "#c0485e", glow=1.0),
        cloud=tex.glow_flat("#fff3ea" if not nm else "#8f8a9c", 0.55 if not nm else 0.2, core="#ffffff" if not nm else "#a39cb0"),
    )
    _MAT_CACHE[pal["name"]] = d
    return d


# ------------------------------------------------------------------------------- small architecture parts
def part_door(k, b, c, P, h=5.0, w=2.6, ajar=40.0, stretch=1.0):
    mt = mats(P)
    h = h * stretch
    x, y, z = c
    k.box(b, (x - w / 2 - 0.25, y, z), (0.5, h, 0.8), mt["trim"])
    k.box(b, (x + w / 2 + 0.25, y, z), (0.5, h, 0.8), mt["trim"], variant=1)
    k.box(b, (x, y + h / 2 + 0.3, z), (w + 1.2, 0.6, 0.9), mt["trim"], variant=2)
    k.plane(b, "z", (x, y, z + 0.2), w, h, mt["glow"])
    k.box(b, (x, y, z - 0.1), (w, h - 0.1, 0.25), mt["door"], rot=(0, ajar, 0), pivot=(x - w / 2, y, z - 0.1))


def part_window(k, b, c, P, w=3.0, h=3.4):
    mt = mats(P)
    x, y, z = c
    k.box(b, (x, y, z), (w, h, 0.5), mt["trim"], mats={"north": mt["win"], "south": mt["win"]})
    k.box(b, (x, y - h / 2 - 0.2, z - 0.1), (w + 0.6, 0.4, 0.9), mt["trim"], variant=1)
    k.plane(b, "z", (x - w / 2 - 0.6, y, z - 0.6), 1.3, h, mt["wood"], rot=(0, -50, 0), pivot=(x - w / 2, y, z - 0.3))
    k.plane(b, "z", (x + w / 2 + 0.6, y, z - 0.6), 1.3, h, mt["wood"], rot=(0, 50, 0), pivot=(x + w / 2, y, z - 0.3))


def part_stairs(k, b, c, P, n=5, invert=False):
    mt = mats(P)
    x, y, z = c
    for i in range(n):
        hgt = 0.7 * (i + 1)
        yy = y - 1.8 + hgt / 2 if not invert else y + 1.8 - hgt / 2
        k.box(b, (x - 1.8 + i * 0.9, yy, z), (0.9, hgt, 2.0), mt["stone"], variant=i % 3)


def part_room(k, b, c, P, inner="bed"):
    mt = mats(P)
    x, y, z = c
    k.box(b, (x, y - 1.8, z), (4.2, 0.4, 3.2), mt["wood"])
    k.box(b, (x, y, z + 1.6), (4.2, 4.0, 0.4), mt["wall"])
    k.box(b, (x + 2.1, y, z), (0.4, 4.0, 3.2), mt["wall"], variant=1)
    k.plane(b, "z", (x - 0.4, y + 0.5, z + 1.38), 1.6, 1.8, mats(P)["glow"])
    if inner == "bed":
        k.box(b, (x - 0.5, y - 1.2, z + 0.3), (2.4, 0.8, 1.6), mt["fabric"])
        k.box(b, (x - 1.5, y - 0.9, z + 0.3), (0.6, 0.5, 1.4), tex.porcelain(IVORY, "#e3d3bd", crack=0.0))
    else:
        k.box(b, (x + 0.8, y - 1.0, z), (0.9, 1.2, 0.9), mt["trim"])
        k.box(b, (x + 0.8, y - 0.1, z), (1.3, 0.6, 1.3), mt["glow"])


def part_moon(k, b, c, P, size=3.4):
    mt = mats(P)
    x, y, z = c
    k.plane(b, "z", (x, y, z), size, size, mt["moon"])
    k.plane(b, "z", (x + size * 0.55, y + size * 0.45, z + 0.2), size * 0.38, size * 0.38, mt["star"])


def part_lantern(k, b, c, P):
    mt = mats(P)
    x, y, z = c
    k.box(b, (x, y - 2.35, z), (0.25, 3.2, 0.25), mt["trim"])
    k.box(b, (x, y, z), (1.2, 1.5, 1.2), mt["glow"])
    k.box(b, (x, y + 0.95, z), (1.6, 0.4, 1.6), mt["trim"], variant=1)
    k.box(b, (x, y + 1.3, z), (0.5, 0.5, 0.5), mt["trim"], variant=2, rot=(45, 0, 45))
    k.box(b, (x, y - 0.85, z), (0.8, 0.25, 0.8), mt["trim"], variant=2)


def part_frame(k, b, c, P, h=7.0):
    """Empty, too-tall door frame leaning at a wrong angle, an eye floating inside."""
    mt = mats(P)
    x, y, z = c
    k.box(b, (x - 1.5, y, z), (0.5, h, 0.7), mt["trim"], rot=(0, 0, 8), pivot=(x, y, z))
    k.box(b, (x + 1.5, y, z), (0.5, h, 0.7), mt["trim"], rot=(0, 0, 8), pivot=(x, y, z), variant=1)
    k.box(b, (x, y + h / 2, z), (3.6, 0.6, 0.8), mt["trim"], rot=(0, 0, 8), pivot=(x, y, z), variant=2)
    k.plane(b, "z", (x, y + 0.6, z), 2.0, 1.2, tex.eye_mat("#9a2f45", AIVORY, "#0c0c18", INDIGO, 0.9, slit=True,
                                                             ring="#c0485e"))


def part_chair(k, b, c, P, flip=False):
    mt = mats(P)
    x, y, z = c
    s = -1 if flip else 1
    k.box(b, (x, y, z), (2.0, 0.35, 2.0), mt["wood"])
    k.box(b, (x, y + s * 1.3, z + 0.85), (2.0, 2.4, 0.3), mt["wood"], variant=1)
    for dx in (-0.8, 0.8):
        k.box(b, (x + dx, y - s * 0.9, z - 0.8), (0.25, 1.8, 0.25), mt["dark"])
        k.box(b, (x + dx, y - s * 0.9, z + 0.8), (0.25, 1.8, 0.25), mt["dark"])


def part_key(k, b, c, P):
    k.plane(b, "z", c, 2.2, 3.2, mats(P)["key"])


def part_notes(k, b, c, P):
    mt = mats(P)
    x, y, z = c
    k.plane(b, "z", (x, y, z), 2.2, 2.6, mt["note"])
    k.plane(b, "z", (x + 1.6, y + 1.1, z + 0.3), 1.6, 1.9, mt["note"], variant=1)


def part_tower(k, b, c, P, w=2.0, h=6.0):
    mt = mats(P)
    x, y, z = c
    k.box(b, (x, y, z), (w, h, w), mt["wall"], mats={f: mt["win"] for f in ("north", "south", "east", "west")})
    k.box(b, (x, y + h / 2 + w * 0.35, z), (w * 0.72, w * 0.72, w * 0.72), mt["trim"], rot=(45, 0, 45),
          pivot=(x, y + h / 2 + w * 0.35, z))
    k.box(b, (x, y + h / 2 + 0.1, z), (w + 0.4, 0.3, w + 0.4), mt["trim"], variant=1)


def part_cloud(k, b, c, P):
    mt = mats(P)
    x, y, z = c
    k.box(b, (x, y, z), (4.0, 1.2, 2.6), mt["cloud"])
    k.box(b, (x - 1.0, y + 0.7, z), (2.0, 1.2, 2.0), mt["cloud"])
    k.box(b, (x + 1.1, y + 0.5, z + 0.2), (1.6, 1.0, 1.8), mt["cloud"])


PARTS = dict(door=part_door, window=part_window, stairs=part_stairs, room=part_room, moon=part_moon,
             lantern=part_lantern, frame=part_frame, chair=part_chair, key=part_key, notes=part_notes,
             tower=part_tower, cloud=part_cloud)


# ------------------------------------------------------------------------------- per-spell centrepieces
# Each builder makes the spell's miniature in bones prefixed k<kind>_ under `parent`, sized for the
# charge construct at s = 1 (about 16 units across); the vision reuses them at a smaller s.
def core_k0(k, parent):
    """DN01 Reverie Procession: an ivory dream-road spiralling upward, paper lanterns, a gateway,
    a tiny porcelain horse trotting along it, a crescent moon above."""
    D = palette("dream")
    mt = mats(D)
    road_mat = tex.trimmed(tex.plates(IVORY, "#d9c7a6", cell=(4, 3)), SGOLD, 1, 0, glow=0.5)
    road = k.bone("road", parent)
    for i in range(8):
        a = math.radians(-150 + i * 36)
        p = (5.5 * math.cos(a), -6 + i * 1.2, 5.5 * math.sin(a))
        k.box(road, p, (2.6, 0.35, 3.6), road_mat, rot=(-14, -(-150 + i * 36), 0), variant=i % 2)
    a = math.radians(-150 + 8 * 36)
    gx, gy, gz = 5.5 * math.cos(a), -6 + 8 * 1.2, 5.5 * math.sin(a)
    gate = k.bone("gate", parent, pivot=(gx, gy, gz), rot=(0, -(-150 + 8 * 36), 0))
    k.box(gate, (gx - 1.6, gy + 1.6, gz), (0.5, 3.4, 0.5), mt["trim"])
    k.box(gate, (gx + 1.6, gy + 1.6, gz), (0.5, 3.4, 0.5), mt["trim"], variant=1)
    k.box(gate, (gx, gy + 3.5, gz), (4.0, 0.6, 0.7), mt["trim"], variant=2)
    k.plane(gate, "z", (gx, gy + 1.5, gz), 2.8, 3.0, tex.shaped(tex.m_disc(1.0), "#fff3e0", "#ffd9b8", glow=0.9,
                                                                 a=1.0, key="gateglow"))
    for j in range(4):
        a = math.radians(-150 + (j * 2 + 1) * 36 + 18)
        p = (7.0 * math.cos(a), -6 + (j * 2 + 1.5) * 1.2 + 3.6, 7.0 * math.sin(a))
        lb = k.bone(f"lant{j + 1}", parent, pivot=(p[0], p[1] - 3.9, p[2]))
        pal = D if j % 2 == 0 else dict(D, glow="#ffc0d0", name="dreampink")
        part_lantern(k, lb, p, pal)
    # porcelain horse (faces +Z = direction of travel when it sits at angle 0 of the road)
    hx, hy = 5.5, -6 + 0.35 + 1.0
    horse = k.bone("horse", parent, pivot=(0, 0, 0))
    por = tex.porcelain("#fbf6ee", "#e6d8c6", crack=0.3, gilt=SGOLD)
    k.box(horse, (hx, hy + 1.2, 0), (0.9, 0.9, 2.0), por)
    neck = k.bone("horse_neck", horse, pivot=(hx, hy + 1.5, 0.9))
    k.box(neck, (hx, hy + 2.1, 1.1), (0.6, 1.3, 0.6), por, rot=(-30, 0, 0))
    k.box(neck, (hx, hy + 2.7, 1.6), (0.55, 0.55, 1.0), por, variant=1)
    k.box(neck, (hx, hy + 2.6, 0.9), (0.15, 1.2, 0.9), tex.flat(PINK, 0.3), variant=0)
    for li, (lx, lz) in enumerate(((-0.3, 0.7), (0.3, 0.7), (-0.3, -0.7), (0.3, -0.7))):
        lg = k.bone(f"horse_leg{li + 1}", horse, pivot=(hx + lx, hy + 0.8, lz))
        k.box(lg, (hx + lx, hy + 0.35, lz), (0.28, 1.0, 0.28), por, variant=li % 2)
    moon = k.bone("moon", parent, pivot=(0, 8.5, 0))
    part_moon(k, moon, (0, 8.5, 0), D, 4.2)


def core_k1(k, parent):
    """DN02 Nightmare Intrusion: a too-tall door left ajar on burgundy light, an eye in the gap, long
    fingers curling round its edge, a stair that sinks away beneath it, a swinging bare bulb."""
    N = palette("night")
    mt = mats(N)
    fr = k.bone("frame", parent, pivot=(0, -6, 0), rot=(0, 0, 5))
    k.box(fr, (-2.7, 0, 0), (0.8, 13, 1.2), mt["trim"])
    k.box(fr, (2.7, 0, 0), (0.8, 13, 1.2), mt["trim"], variant=1)
    k.box(fr, (0, 6.9, 0), (6.4, 0.9, 1.4), mt["trim"], variant=2)
    k.box(fr, (0, -6.7, -0.2), (6.6, 0.6, 1.8), mt["stone"])
    k.plane(fr, "z", (0, 0, 0.35), 4.6, 12.8, tex.vgrad("#d0506a", "#2a1020", var=0, glow_top=1.0, glow_bottom=0.6,
                                                          edge_dark=0))
    leaf = k.bone("leaf", fr, pivot=(-2.25, 0, 0), rot=(0, 36, 0))
    k.box(leaf, (0, 0, 0), (4.5, 12.6, 0.35), mt["door"])
    eye = k.bone("eye", fr, pivot=(1.4, 2.4, 0.25))
    k.plane(eye, "z", (1.2, 2.4, 0.25), 2.6, 1.6, tex.eye_mat("#b8405a", AIVORY, "#0c0c18", "#1d1f3c", 1.0,
                                                                slit=True, ring="#ff7088"))
    hand = k.bone("hand", fr, pivot=(2.3, 1.0, 0))
    bone_m = tex.porcelain(AIVORY, "#9d968a", "#6e2f3a", crack=1.0)
    for i in range(4):
        k.box(hand, (1.6, -0.4 + i * 0.75, -0.55), (1.9, 0.26, 0.26), bone_m, rot=(0, 0, -6 + i * 4),
              pivot=(2.4, -0.4 + i * 0.75, -0.55))
    for i in range(5):
        s = 0.86 ** i
        k.box(fr, (0, -7.4 - i * 0.75, -1.4 - i * 1.0), (5.6 * s, 0.45, 1.0 * s), mt["stone"], variant=i % 3)
    k.plane(fr, "y", (0, -7.05, -5.5), 3.2, 9.5, tex.shaped(lambda u, v: (np.abs(u) < 0.55 * (0.4 + 0.6 * (v + 1) / 2))
                                                             .astype(float), "#2a1020", "#4a2a40", glow=0.15,
                                                             key="nmshadow"), faces=("up", "down"))
    bulb = k.bone("bulb", parent, pivot=(-1.0, 13.5, -2.0))
    k.box(bulb, (-1.0, 11.6, -2.0), (0.12, 3.8, 0.12), mt["dark"])
    k.box(bulb, (-1.0, 9.4, -2.0), (0.9, 1.1, 0.9), tex.glow_flat("#e8e0a0", 1.0, core="#ffffff"))


def core_k2(k, parent):
    """DN03 House of Shifting Sleep: a cut-away dollhouse whose four rooms disagree - a golden bedroom,
    a stair that climbs into the ceiling, an upside-down bedroom, a room with doors on every wall."""
    D, S = palette("dream"), palette("strange")
    md, ms = mats(D), mats(S)
    house = k.bone("house", parent, pivot=(0, -6, 0))
    k.box(house, (0, -6.3, 0), (10.8, 0.6, 6.6), md["trim"])
    k.box(house, (0, -2.0, 0.2), (10.0, 0.4, 6.0), md["wood"])
    k.box(house, (0, -2.0, 3.0), (10.0, 8.6, 0.4), md["wall"], mats={"south": ms["win"]})
    k.box(house, (-5.0, -2.0, 0.2), (0.4, 8.6, 6.0), md["wall"], variant=1, mats={"west": ms["win"]})
    k.box(house, (5.0, -2.0, 0.2), (0.4, 8.6, 6.0), md["wall"], variant=2, mats={"east": ms["win"]})
    k.box(house, (0, -2.0, 0.2), (0.3, 8.6, 6.0), ms["wall"])
    for sgn in (-1, 1):
        k.box(house, (sgn * 2.75, 4.3, 0.2), (6.6, 0.6, 7.0), ms["trim"], rot=(0, 0, -sgn * 35),
              pivot=(sgn * 2.75, 4.3, 0.2))
    k.box(house, (3.0, 5.6, 1.5), (1.0, 2.4, 1.0), md["stone"])
    wp = [tex.glow_flat("#ffd98a", 0.7, core="#fff3c4"), tex.glow_flat("#cfd8f0", 0.5), tex.glow_flat("#e8c0d8", 0.5),
          tex.glow_flat("#d9c8f0", 0.6)]
    for i, (cx, cy) in enumerate(((-2.5, -4.0), (2.5, -4.0), (-2.5, 0.2), (2.5, 0.2))):
        k.plane(house, "z", (cx, cy, 2.75), 4.4, 3.8, wp[i])
    k.box(house, (-3.0, -5.5, 1.2), (2.6, 0.7, 1.8), md["fabric"])
    k.box(house, (-4.1, -5.0, 1.2), (0.4, 1.6, 1.8), md["wood"])
    k.box(house, (-1.0, -5.3, 2.2), (0.6, 1.4, 0.6), md["glow"])
    for i in range(4):
        k.box(house, (1.2 + i * 1.0, -5.6 + i * 0.95, 1.0), (1.0, 0.35, 1.8), ms["stone"], variant=i % 3)
    flip = k.bone("flip", house, pivot=(-2.5, 0.2, 1.0))
    k.box(flip, (-3.0, 1.7, 1.2), (2.6, 0.7, 1.8), ms["fabric"])
    k.box(flip, (-4.1, 1.2, 1.2), (0.4, 1.6, 1.8), ms["wood"])
    k.box(flip, (-1.4, 1.0, 1.4), (0.5, 1.6, 0.5), ms["glow"])
    doors = k.bone("doors", house, pivot=(2.5, 0.2, 1.0))
    dmat = tex.bitmap_cut(ARCH_DOOR, "#e8b4c8", glow=0.6, color2=MAUVE)
    k.plane(doors, "z", (2.5, -0.2, 2.6), 1.6, 2.4, dmat)
    k.plane(doors, "x", (0.4, -0.2, 1.0), 1.6, 2.4, dmat, variant=1)
    k.plane(doors, "x", (4.6, -0.2, 1.0), 1.6, 2.4, dmat, variant=2)
    k.plane(doors, "y", (2.5, -1.6, 0.6), 1.6, 2.4, dmat, variant=3)
    for sgn, nm in ((-1, "front_l"), (1, "front_r")):
        fb = k.bone(nm, house, pivot=(sgn * 5.2, -2.0, -2.9), rot=(0, -sgn * 118, 0))
        k.box(fb, (sgn * 2.7, -2.0, -2.95), (5.0, 8.6, 0.3), md["wall"], mats={"north": md["win"]}, variant=sgn + 1)


def core_k3(k, parent):
    """DN04 Lullaby and Scream: an open porcelain music box at the centre of a turning tapestry carousel,
    half lullaby (peach, moons) and half scream (indigo, eyes, mouths), with notes drifting round."""
    D, N = palette("dream"), palette("night")
    md = mats(D)
    box = k.bone("mbox", parent, pivot=(0, -5, 0))
    por = pearl(IVORY, "#e3d3bd", gilt=SGOLD, crack=0.3)
    k.box(box, (0, -3.7, 0), (5.0, 2.6, 3.4), por)
    k.box(box, (0, -5.1, 0), (5.4, 0.4, 3.8), md["trim"])
    cyl = k.bone("cyl", box, pivot=(0, -2.8, 0))
    k.box(cyl, (0, -2.8, 0), (3.6, 0.8, 0.8), md["trim"], variant=1)
    lid = k.bone("lid", box, pivot=(0, -2.4, 1.7), rot=(70, 0, 0))
    k.box(lid, (0, -2.25, 0), (5.0, 0.3, 3.4), por, variant=1, mats={"down": tex.glow_flat("#cfe2ff", 0.8, core="#ffffff")})
    crank = k.bone("crank", box, pivot=(2.6, -3.7, 0))
    k.box(crank, (2.8, -3.7, 0), (0.4, 0.3, 0.3), md["trim"])
    k.box(crank, (3.0, -3.2, 0), (0.25, 1.1, 0.25), md["trim"], variant=1)
    dancer = k.bone("dancer", box, pivot=(0, -2.4, 0))
    k.box(dancer, (0, -1.6, 0), (0.2, 1.6, 0.2), md["trim"])
    k.plane(dancer, "z", (0, -0.2, 0), 1.6, 1.6, md["moon"])
    ring_b = k.bone("tring", parent)
    tapD, tapN = tapestry(False), tapestry(True)
    for i in range(10):
        ab = k.bone(f"tapa{i + 1}", ring_b, rot=(0, i * 36 + 18, 0))
        tb = k.bone(f"tap{i + 1}", ab, pivot=(0, 4.0, -7.6))
        k.plane(tb, "z", (0, 1.4, -7.6), 4.4, 5.2, tapD if i < 5 else tapN, variant=i % 3)
        k.box(tb, (0, 4.1, -7.6), (4.8, 0.3, 0.3), md["trim"] if i < 5 else mats(N)["trim"], variant=i % 2)
    notes = k.bone("notes", parent)
    for i in range(6):
        a = math.radians(i * 60 + 10)
        r = 4.2 + (i % 2) * 6.0
        p = (r * math.cos(a), -1.5 + (i % 3) * 3.5, r * math.sin(a))
        nb = k.bone(f"note{i + 1}", notes, pivot=p, rot=(0, -i * 60 + 80, 0))
        k.plane(nb, "z", p, 2.0, 2.4, mats(D if i % 2 == 0 else N)["note"], variant=i % 2)


TOWERS = [(0, 0, 2.6, 12.0, 0), (-3.4, 1.6, 2.0, 8.0, 0), (3.2, 1.2, 2.2, 9.5, 1), (-1.6, -3.2, 1.8, 6.5, 0),
          (2.2, -3.2, 1.6, 7.2, 1), (-4.8, -2.0, 1.6, 5.5, 0), (4.8, -1.4, 1.8, 6.2, 1)]


def core_k4(k, parent):
    """DN05 The City That Sleeps: a floating skyline on a cloud - ivory towers with golden windows,
    bridges, an aerial stair; the eastern third already stretched, tilted and nightmare-coloured."""
    D, N = palette("dream"), palette("night")
    md = mats(D)
    city = k.bone("city", parent)
    for (cx, cz, w, d) in ((0, 0, 11, 7), (-3.5, 1.5, 6, 5), (3.6, -1.5, 6, 5), (0.5, -3.0, 6, 3.5)):
        k.box(city, (cx, -6.3, cz), (w, 1.4, d), md["cloud"], variant=int(cx) % 2)
    for i, (x, z, w, h, nm) in enumerate(TOWERS):
        tb = k.bone(f"tw{i + 1}", city, pivot=(x, -5.6, z), rot=((0, 14, -9) if nm else (0, 0, 0)))
        part_tower(k, tb, (x, -5.6 + h / 2, z), N if nm else D, w, h)
    k.box(city, (-1.7, 1.5, 0.8), (4.0, 0.4, 1.0), md["trim"], rot=(0, -20, 8))
    k.box(city, (0.2, -1.5, -1.6), (0.9, 0.35, 4.2), md["trim"], rot=(10, 0, 0), variant=1)
    st = k.bone("astair", city)
    for i in range(7):
        a = math.radians(i * 40)
        k.box(st, (2.4 * math.cos(a), -2.0 + i * 1.05, 2.4 * math.sin(a)), (1.6, 0.3, 0.9), md["stone"],
              rot=(0, -i * 40, 0), variant=i % 3)


def core_k5(k, parent):
    """DN06 The Dreamer Who Never Wakes: an antique four-poster bed with a faceless porcelain sleeper
    (a tiny door set in its face) breathing under the blanket; a moon and stars turn above the canopy
    while long nightmare fingers creep out from beneath the bed."""
    D, N = palette("dream"), palette("night")
    md, mn = mats(D), mats(N)
    bed = k.bone("bed", parent, pivot=(0, -5, 0))
    wood = tex.wood("#d9b48a", "#9a6e4a")
    k.box(bed, (0, -4.6, 0), (8.4, 1.2, 5.0), wood)
    for sx in (-4.0, 4.0):
        for sz in (-2.3, 2.3):
            k.box(bed, (sx, -0.6, sz), (0.5, 9.2, 0.5), md["trim"], variant=int(sx > 0))
    k.box(bed, (0, 3.9, 0), (8.8, 0.5, 5.4), md["trim"], variant=2)
    k.box(bed, (4.1, -2.2, 0), (0.5, 4.0, 4.6), wood, variant=1)
    k.box(bed, (-4.1, -3.0, 0), (0.5, 2.4, 4.6), wood, variant=2)
    k.box(bed, (0, -3.6, 0), (7.6, 0.8, 4.6), pearl(IVORY, "#e3d3bd", crack=0.0))
    k.box(bed, (3.0, -2.9, 0), (1.5, 0.7, 2.8), tex.fabric(IVORY, PEACH, stripe_w=1))
    breath = k.bone("breath", bed, pivot=(-0.6, -3.2, 0))
    k.box(breath, (-0.6, -2.85, 0), (5.4, 0.8, 4.8), tex.fabric(PINK, PEACH, stripe_w=2, glow=0.05))
    k.box(breath, (-0.4, -2.3, 0), (3.6, 0.6, 1.8), tex.fabric(PINK, PEACH, stripe_w=2, glow=0.05), variant=1)
    head = k.bone("head", bed, pivot=(2.9, -2.0, 0))
    por = tex.porcelain("#fbf6ee", "#e6d8c6", crack=0.3)
    k.box(head, (2.9, -2.0, 0), (1.5, 1.4, 1.5), por, mats={"up": tex.stamped(por, ARCH_DOOR, SGOLD, glow=0.8,
                                                                                 key="sleepdoor")})
    for i, (x, z, w, h) in enumerate(((0, 2.6, 8.0, 3.0), (-3.2, -2.6, 2.0, 7.4))):
        cb = k.bone(f"curt{i + 1}", bed, pivot=(x, 3.6, z))
        k.plane(cb, "z", (x, 3.6 - h / 2, z), w, h, tex.fabric(PINK if i == 0 else MAUVE, None, glow=0.1, fringe=True),
                variant=i)
    dream = k.bone("dream", parent, pivot=(0, 8.0, 0))
    part_moon(k, dream, (0, 8.0, 0), D, 3.4)
    for j in range(3):
        a = math.radians(j * 120)
        k.plane(dream, "z", (3.4 * math.cos(a), 7.0 + j * 0.8, 3.4 * math.sin(a)), 1.3, 1.3, md["star"], variant=j)
    hands = k.bone("hands", bed, pivot=(0, -5.4, -2.2))
    k.plane(hands, "y", (0, -5.35, -3.4), 7.0, 3.0, tex.shaped(lambda u, v: (np.abs(u) < 1 - (1 - (v + 1) / 2) ** 2)
                                                               .astype(float), "#1d1f3c", MAUVE, glow=0.1,
                                                               key="bedshadow"), faces=("up", "down"))
    fing = tex.porcelain(AIVORY, "#9d968a", "#6e2f3a", crack=1.0)
    for i in range(4):
        k.box(hands, (-2.0 + i * 1.3, -5.2, -3.4), (0.28, 0.28, 2.6), fing, rot=(8, -10 + i * 7, 0),
              pivot=(-2.0 + i * 1.3, -5.2, -2.2))


CORES = [core_k0, core_k1, core_k2, core_k3, core_k4, core_k5]
MOODS = ["dream", "night", "strange", "both", "dream_to_night", "both"]


def core_motion(a, kind, s=1.0):
    """Living motion of each centrepiece (q.life_time based, so it runs in any state)."""
    p = f"k{kind}_"
    if kind == 0:
        for j in range(4):
            a.rot(p + f"lant{j + 1}", (LIFE(5, 2.1, j * 0.23), 0, LIFE(9, 1.7, j * 0.17)))
        prog = M("math.mod(q.life_time,4)/4", lambda t: (t % 4) / 4)
        a.rot(p + "horse", (0, M("150-288*math.mod(q.life_time,4)/4", lambda t: 150 - 288 * ((t % 4) / 4)), 0))
        a.pos(p + "horse", (0, prog * (9.6 * s), 0))
        a.scl(p + "horse", M("math.clamp(math.min(math.mod(q.life_time,4)*4,(4-math.mod(q.life_time,4))*4),0,1)",
                             lambda t: max(0, min(1, min((t % 4) * 4, (4 - t % 4) * 4)))))
        a.rot(p + "horse_neck", (LIFE(10, 0.5), 0, 0))
        for li in range(4):
            a.rot(p + f"horse_leg{li + 1}", (LIFE(35, 0.5, 0.5 * (li % 2) + 0.25 * (li // 2)), 0, 0))
        a.rot(p + "moon", (0, spin(25), LIFE(6, 4.0)))
    elif kind == 1:
        a.rot(p + "leaf", (0, LIFE(12, 3.4, 0, 2), 0))
        a.scl(p + "eye", (1, M("math.mod(q.life_time,2.7)<0.16?0.1:1",
                               lambda t: 0.1 if (t % 2.7) < 0.16 else 1.0), 1))
        a.pos(p + "eye", (LIFE(0.25 * s, 1.3), 0, 0))
        a.rot(p + "hand", (0, 0, LIFE(5, 2.2)))
        a.rot(p + "bulb", (LIFE(4, 2.3), 0, LIFE(14, 1.7)))
        a.rot(p + "frame", (0, LIFE(4, 5.0), LIFE(2, 3.1)))
    elif kind == 2:
        a.rot(p + "flip", (0, 0, LIFE(18, 4.4)))
        a.rot(p + "doors", (0, LIFE(25, 3.3), 0))
        a.pos(p + "doors", (LIFE(0.5 * s, 2.2), 0, 0))
        a.rot(p + "house", (0, LIFE(10, 6.0), LIFE(3, 4.1)))
        a.rot(p + "front_l", (0, LIFE(6, 2.9), 0))
        a.rot(p + "front_r", (0, LIFE(6, 3.3, 0.4), 0))
    elif kind == 3:
        a.rot(p + "tring", (0, spin(28), 0))
        for i in range(10):
            a.rot(p + f"tap{i + 1}", (LIFE(12, 2.2, i / 10.0, -4), 0, 0))
        a.rot(p + "cyl", (spin(220), 0, 0))
        a.rot(p + "crank", (spin(-160), 0, 0))
        a.rot(p + "dancer", (0, spin(90), 0))
        a.rot(p + "lid", (LIFE(4, 1.1), 0, 0))
        a.rot(p + "notes", (0, spin(-40), 0))
        for i in range(6):
            a.pos(p + f"note{i + 1}", (0, LIFE(0.9 * s, 1.8, i / 6.0), 0))
    elif kind == 4:
        a.rot(p + "city", (0, spin(14), LIFE(2, 5.0)))
        for i, t_ in enumerate(TOWERS):
            if t_[4]:
                a.scl(p + f"tw{i + 1}", (1, LIFE(0.16, 2.6, i * 0.2, 1.1), 1))
                a.rot(p + f"tw{i + 1}", (0, LIFE(10, 3.7, i * 0.3), LIFE(4, 2.9, i * 0.1)))
            else:
                a.scl(p + f"tw{i + 1}", (1, LIFE(0.03, 3.3, i * 0.15, 1.0), 1))
        a.rot(p + "astair", (0, spin(-30), 0))
    elif kind == 5:
        a.scl(p + "breath", (1, LIFE(0.14, 3.6, 0, 1.0), 1))
        a.rot(p + "head", (LIFE(3, 3.6), 0, LIFE(2, 7.0)))
        a.rot(p + "curt1", (LIFE(7, 2.6), 0, 0))
        a.rot(p + "curt2", (LIFE(-7, 2.9, 0.3), 0, 0))
        a.rot(p + "dream", (0, spin(20), 0))
        a.pos(p + "hands", (0, 0, LIFE(-0.9 * s, 4.5, 0, -0.5 * s)))
        a.rot(p + "hands", (LIFE(4, 1.3), LIFE(6, 3.1), 0))
        a.rot(p + "bed", (0, 0, LIFE(1.5, 5.0)))


# fragments that orbit each charge construct: (part, palette, height)
FRAGS = [
    [("lantern", "dream", 1.0), ("door", "dream", -2.0), ("moon", "dream", 3.0), ("stairs", "dream", -1.0),
     ("lantern", "strange", 2.0), ("window", "dream", 0.0)],
    [("frame", "night", 1.0), ("window", "night", -1.5), ("chair", "night", 3.0), ("door", "night", -1.0),
     ("stairs", "night", 2.0), ("key", "night", 0.0)],
    [("room", "strange", 1.0), ("stairs", "strange", -1.5), ("door", "dream", 2.5), ("room", "dream", -1.0),
     ("window", "strange", 2.0), ("chair", "dream", -0.5)],
    [("notes", "dream", 1.5), ("moon", "dream", -1.0), ("door", "dream", 2.5), ("notes", "night", -0.5),
     ("frame", "night", 1.0), ("key", "night", 2.0)],
    [("tower", "dream", 0.0), ("cloud", "dream", 2.5), ("window", "dream", -1.0), ("stairs", "night", 2.0),
     ("tower", "night", -0.5), ("cloud", "night", 1.0)],
    [("door", "dream", 0.5), ("moon", "dream", 3.0), ("window", "night", -1.0), ("stairs", "dream", 1.5),
     ("frame", "night", -0.5), ("cloud", "dream", 2.5)],
]
ORBIT_R = 15.0


def frag_centers(kind):
    out = []
    for i, (_p, _pal, h) in enumerate(FRAGS[kind]):
        a = math.radians(i * 60 + 30)
        out.append((ORBIT_R * math.cos(a), h, ORBIT_R * math.sin(a), i * 60 + 30))
    return out


# ------------------------------------------------------------------------------- the held book
def book_model():
    m = Model(GEO, density=2.0, bounds=(4, 4, (0, 1, 0)))
    k = K(m, 1.0, (-2.75, 0, 0), mirror=True)   # reader space, centred on the whole book incl. spine tower
    cer = pearl(IVORY, "#e2d4bf", gilt=FGOLD, crack=0.5)
    cer_cover = pearl("#f6efe2", "#e6d6c0", gilt=FGOLD, crack=0.45, engrave=eng_cover, key="pcov")
    cer_back = pearl("#f3ebdc", "#e0d0ba", gilt=FGOLD, crack=0.5, engrave=eng_back, key="pback")
    gilt = tex.metal("#d4b874", "#f6e6b4", "#8f7440", bands=2.0)
    gilt2 = tex.metal("#cdb070", "#efe0b0", "#8a6f3e", bands=3.0, glow=0.1)
    relief = pearl("#fbf5ea", "#eadcc6", crack=0.2, sheen=0.5, key="relief")
    D = palette("dream")
    md = mats(D)

    root = m.bone("root")
    root.binding = "q.item_slot_to_bone_name(c.item_slot)"
    place = m.bone("place", root)
    flt = m.bone("float", place)
    book = m.bone("book", flt)

    back = k.bone("back", book)
    k.box(back, (0, 0, 3.55), (27, 38, 1.1), cer, mats={"south": cer_back})
    pages = k.bone("pages", book)
    k.box(pages, (0.1, 0, 0.1), (25.4, 36.4, 5.6), page_edge(), mats={"north": page_open()})

    # ---- spine: an open little tower with a turning spiral staircase
    spine = k.bone("spine", book)
    k.box(spine, (-14.2, 0, 0), (1.6, 38.8, 8.4), cer, variant=1)
    k.box(spine, (-16.5, -18.8, 0), (5.2, 1.6, 5.4), gilt)
    k.box(spine, (-16.5, 18.7, 0), (5.2, 1.8, 5.4), gilt, variant=1)
    k.box(spine, (-16.5, 20.2, 0), (3.0, 3.0, 3.0), relief, rot=(45, 0, 45), pivot=(-16.5, 20.2, 0))
    for sx in (-18.6, -14.6):
        for sz in (-2.2, 2.2):
            k.box(spine, (sx, 0, sz), (0.8, 36, 0.8), relief, variant=int(sz > 0))
    for y in (-6.5, 6.5):
        k.box(spine, (-16.5, y, 0), (5.0, 0.6, 5.2), gilt2)
    spiral = k.bone("spiral", spine, pivot=(-16.6, 0, 0))
    k.box(spiral, (-16.6, 0, 0), (0.8, 36, 0.8), gilt2, variant=1)
    for i in range(16):
        a = i * 50
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        k.box(spiral, (-16.6 + 1.25 * ca, -16.8 + i * 2.25, 1.25 * sa), (2.1, 0.45, 1.2),
              relief if i % 2 else gilt, rot=(0, -a, 0), variant=i % 2)

    # ---- leaves (riffle on the page-turn flourish, fan out when opened)
    for i in range(3):
        lb = k.bone(f"leaf{i + 1}", book, pivot=(-12.6, 0, -2.8 - 0.06 * i))
        k.plane(lb, "z", (0.0, 0, -2.8 - 0.06 * i), 25.2, 36.0, leaf_mat(i))

    # ---- pop-up paper architecture that stands up from the first page when the book opens
    pop_mats = [tex.bitmap_cut(HOUSE, "#fff6ea", glow=0.45, color2="#f2c9b4"),
                tex.bitmap_cut(ARCH_DOOR, "#f7d6c8", glow=0.6, color2=PINK),
                tex.bitmap_cut(STAIR_SIL, "#fff1dc", glow=0.45, color2=SGOLD),
                tex.bitmap_cut(CRESCENT, "#fff3c0", glow=1.0, color2=SGOLD)]
    for i, (cx, by, w, h) in enumerate(((0, -12, 9, 7), (-5, -2, 4, 6), (4.5, -2, 5, 4.5), (1, 5, 4, 5))):
        pb = k.bone(f"pop{i + 1}", pages, pivot=(cx, by, -2.72))
        k.plane(pb, "z", (cx, by + h / 2, -2.72), w, h, pop_mats[i])

    # ---- front cover: hinge at the spine
    cover = k.bone("cover", book, pivot=(-13.5, 0, -3.45))
    k.box(cover, (0, 0, -3.45), (27, 38, 1.1), cer, mats={"north": cer_cover, "south": endpaper()})
    for (c, s) in (((0, 18.3, -4.15), (27, 1.4, 0.5)), ((0, -18.3, -4.15), (27, 1.4, 0.5)),
                   ((-12.8, 0, -4.15), (1.4, 38, 0.5)), ((12.8, 0, -4.15), (1.4, 38, 0.5))):
        k.box(cover, c, s, gilt, variant=int(s[0] > 2))

    # corners on contradictory planes
    corners = [("c_tl", (-12.0, 17.3), (0, 0, 45), (35.3, 45, 0)), ("c_tr", (12.0, 17.3), (0, 38, 0), (0, 0, 90)),
               ("c_bl", (-12.0, -17.3), (38, 0, 0), (0, 0, 22)), ("c_br", (12.0, -17.3), (-30, -30, 0), (180, 0, 0))]
    for name, (cx, cy), r1, r2 in corners:
        cb = k.bone(name, cover, pivot=(cx, cy, -4.4))
        k.box(cb, (cx, cy, -4.5), (3.4, 3.4, 0.5), gilt2, rot=r1, pivot=(cx, cy, -4.5))
        if name in ("c_tl", "c_bl"):
            k.box(cb, (cx, cy, -5.4), (1.5, 1.5, 1.5), relief, rot=r2, pivot=(cx, cy, -5.4))
        else:
            for j in range(2):
                k.box(cb, (cx - 0.5 + j * 0.9, cy + (0.4 if name == "c_tr" else -0.4) * (j + 1), -5.0),
                      (0.9, 0.8 * (j + 1), 1.0), relief, rot=r2, pivot=(cx, cy, -5.0), variant=j)

    # reliefs: stairs, doors, windows engraved into the ceramic
    for i in range(5):     # flight climbing to the little house's sill (left)
        k.box(cover, (-11.6 + i * 0.85, -15.4 + i * 1.6, -4.25), (1.5, 0.75, 0.7), relief, variant=i % 2)
    for i in range(4):     # upside-down flight hanging from the top right
        k.box(cover, (11.3 - i * 0.85, 13.0 - i * 1.5, -4.25), (1.5, 0.75, 0.7), relief, variant=i % 2)
    for (dx, dy) in ((-10.4, 4.2), (10.2, -12.6), (-5.4, -13.6), (6.4, -13.6)):
        k.box(cover, (dx, dy, -4.2), (2.8, 4.4, 0.5), gilt2)
        k.box(cover, (dx, dy - 0.1, -4.35), (2.0, 3.8, 0.6), md["door"], variant=int(dx > 0))
    for (wx, wy) in ((-10.4, 9.6), (10.2, -1.0), (-8.0, 15.4), (9.0, 15.4)):
        k.box(cover, (wx, wy, -4.25), (2.4, 2.8, 0.55), relief, mats={"north": md["win"]}, variant=1)
    for i, w in enumerate((6.0, 7.2, 8.4)):  # front stoop
        k.box(cover, (-0.5, -7.9 - i * 1.0, -4.3 - 0.2 * (2 - i)), (w, 1.0, 0.6 + 0.4 * (2 - i)), relief, variant=i)
    k.plane(cover, "z", (-0.5, 16.4, -4.1), 3.4, 3.4, tex.bitmap_cut(CRESCENT, "#f6e6b4", glow=0.9, color2=FGOLD))

    # ---- the miniature bedroom (a shadow box with forced perspective)
    shell = k.bone("shell", cover)
    k.box(shell, (-7.05, 1.5, -5.8), (1.1, 16.2, 3.2), relief)
    k.box(shell, (6.05, 1.5, -5.8), (1.1, 16.2, 3.2), relief, variant=1)
    k.box(shell, (-0.5, -6.5, -5.9), (15.2, 1.0, 3.4), gilt)
    k.box(shell, (-0.5, 9.55, -5.8), (15.2, 1.1, 3.2), gilt, variant=1)
    for sgn in (-1, 1):
        k.box(shell, (-0.5 + sgn * 4.2, 12.2, -5.8), (9.9, 1.0, 3.6), gilt2, rot=(0, 0, -sgn * 27.5),
              pivot=(-0.5 + sgn * 4.2, 12.2, -5.8), variant=sgn + 1)
    k.box(shell, (-0.5, 14.5, -5.8), (1.2, 1.2, 1.2), gilt, rot=(0, 45, 45), pivot=(-0.5, 14.5, -5.8))
    k.box(shell, (3.6, 13.2, -6.2), (1.2, 2.8, 1.2), relief, variant=2)
    k.plane(shell, "z", (-0.5, 11.6, -4.35), 2.6, 2.6, tex.shaped(tex.m_disc(1.0), PBLUE, "#fff3e0", glow=0.9,
                                                                    outline=FGOLD, key="oculus"))
    for nm, cx in (("curt_l", -5.9), ("curt_r", 4.9)):
        cb = k.bone(nm, shell, pivot=(cx, 9.0, -7.1))
        k.plane(cb, "z", (cx + (-0.3 if cx < 0 else 0.3), 2.0, -7.1), 1.1, 14.0,
                tex.fabric(PINK, None, glow=0.1, fringe=True), variant=int(cx > 0))

    room = k.bone("room", cover)
    k.plane(room, "y", (-0.5, -4.2, -5.775), 14.0, 4.6, floor_mat(), rot=(-51.6, 0, 0), faces=("up",), density=5)
    k.plane(room, "y", (-0.5, 7.8, -5.775), 14.0, 3.75, ceiling_mat(), rot=(40.1, 0, 0), faces=("down",), density=4)
    k.plane(room, "x", (-5.3, 1.5, -5.775), 3.75, 15.0, wall_mat(), rot=(0, 40.1, 0), density=4)
    k.plane(room, "x", (4.3, 1.5, -5.775), 3.75, 15.0, wall_mat(), rot=(0, -40.1, 0), density=4)
    k.plane(room, "z", (-0.5, 2.1, -4.35), 9.8, 9.6, backwall_mat(), faces=("north",), density=8)

    bed = k.bone("bed", room, pivot=(-2.7, -3.0, -5.3))
    bwood = tex.wood("#e2b98f", "#a7764e")
    k.box(bed, (-2.75, -2.6, -5.25), (3.7, 0.8, 1.5), bwood)
    for lx in (-4.3, -1.2):
        k.box(bed, (lx, -3.65, -5.85), (0.4, 1.3, 0.3), bwood, variant=1)
    k.box(bed, (-2.75, -1.9, -5.25), (3.5, 0.6, 1.4), pearl(IVORY, "#e3d3bd", crack=0.0))
    k.box(bed, (-4.7, -1.4, -5.25), (0.4, 3.2, 1.5), bwood, variant=2)
    k.box(bed, (-1.0, -2.0, -5.25), (0.35, 1.8, 1.5), bwood, variant=3)
    k.box(bed, (-3.9, -1.35, -5.3), (1.0, 0.5, 1.1), tex.fabric(IVORY, PEACH, stripe_w=1))
    blanket = k.bone("blanket", bed, pivot=(-2.3, -1.6, -5.25))
    k.box(blanket, (-2.3, -1.45, -5.25), (2.2, 0.45, 1.6), tex.fabric(PINK, PEACH, stripe_w=2, glow=0.05))
    k.box(blanket, (-2.3, -2.25, -6.06), (2.2, 1.3, 0.05), tex.fabric(PINK, PEACH, stripe_w=2, glow=0.05), variant=1)
    nmb = k.bone("nm_blanket", blanket, pivot=(-2.3, -1.45, -5.25))
    k.box(nmb, (-2.3, -1.45, -5.25), (2.2, 0.45, 1.6), tex.fabric(BURG, MAUVE, stripe_w=1), inflate=0.06)
    nmh = k.bone("nm_hands", bed, pivot=(-2.6, -3.4, -5.6))
    fing = tex.porcelain(AIVORY, "#9d968a", BURG, crack=1.0)
    for i in range(3):
        k.box(nmh, (-3.3 + i * 0.7, -3.4, -6.4), (0.22, 0.22, 1.7), fing, rot=(6, -8 + i * 8, 0),
              pivot=(-3.3 + i * 0.7, -3.4, -5.6))

    win = k.bone("window", room, pivot=(-2.5, 2.8, -4.45))
    k.box(win, (-2.5, 2.8, -4.5), (2.6, 3.0, 0.2), gilt2, mats={"north": sky_pane(False)}, density=6)
    k.box(win, (-2.5, 1.2, -4.65), (3.0, 0.3, 0.5), relief)
    for nm, sx, sg in (("shut_l", -3.8, -1), ("shut_r", -1.2, 1)):
        sb = k.bone(nm, win, pivot=(sx, 2.8, -4.62))
        k.plane(sb, "z", (sx + sg * 0.65, 2.8, -4.62), 1.3, 3.0, tex.wood("#bcd6f0", "#8aa6c8", vertical=True))
    nmw = k.bone("nm_window", win, pivot=(-2.5, 2.8, -4.62))
    k.plane(nmw, "z", (-2.5, 2.8, -4.62), 2.5, 2.9, sky_pane(True), density=7)

    rwall = k.bone("rwall", room, pivot=(4.3, 1.5, -5.775), rot=(0, -40.1, 0))
    k.box(rwall, (4.15, -1.75, -5.775), (0.25, 5.2, 2.3), gilt2)
    k.plane(rwall, "x", (4.0, -1.8, -5.775), 1.9, 4.7, tex.glow_flat("#ffe2c0", 1.0, core="#fffaf0"))
    nmd = k.bone("nm_doorglow", rwall, pivot=(3.98, -1.8, -5.775))
    k.plane(nmd, "x", (3.98, -1.8, -5.775), 1.9, 4.7, tex.glow_flat("#b8405a", 1.0, core="#ff8090"))
    dl = k.bone("door_leaf", rwall, pivot=(3.95, -1.8, -4.8))
    k.box(dl, (3.9, -1.8, -5.775), (0.15, 4.6, 1.95), md["door"])

    # impossible staircase: climbs the right wall from the door's lintel, then walks on along the ceiling
    for i, (sx, sy, sz, w) in enumerate(((3.6, 1.6, -6.75, 1.2), (3.6, 2.6, -6.3, 1.2), (3.6, 3.6, -5.85, 1.2),
                                         (3.6, 4.6, -5.4, 1.2), (3.6, 5.6, -4.95, 1.2), (3.3, 6.5, -4.6, 1.6),
                                         (2.4, 7.05, -4.9, 1.6), (1.4, 7.3, -5.4, 1.6))):
        sb = k.bone(f"st{i + 1}", rwall, pivot=(sx, sy, sz))
        k.box(sb, (sx, sy, sz), (w, 0.5, 0.8), relief, variant=i % 2, mats={"north": gilt2, "south": gilt2})

    mob = k.bone("mobile", room, pivot=(-0.5, 7.4, -5.9))
    k.box(mob, (-0.5, 6.5, -5.9), (0.1, 1.8, 0.1), gilt)
    k.plane(mob, "z", (-0.5, 5.0, -5.9), 1.6, 1.6, tex.bitmap_cut(CRESCENT, "#fff3c0", glow=1.0, color2=SGOLD))
    k.plane(mob, "z", (0.6, 5.6, -5.9), 0.8, 0.8, tex.bitmap_cut(STAR, "#fffbe0", glow=1.0))

    veil = k.bone("nm_veil", room, pivot=(-0.5, 1.5, -7.0))
    k.plane(veil, "z", (-0.5, 1.5, -7.05), 13.6, 15.0, tex.vgrad("#2a2d52", "#6e2f3a", var=0, glow_top=0.1,
                                                                 glow_bottom=0.3, edge_dark=0, a=0.45, mode="blend"))
    # nightmare geometry that grows out of the cover during the bad dream
    spires = k.bone("nm_spires", cover, pivot=(-0.5, 13.5, -5.8))
    sp = pearl(CGRAY, "#5a5d6a", crack=1.0, sheen=0.0, key="spire")
    tip = tex.glow_flat("#c0485e", 0.9, core="#ff9aa8")
    for i, (sx, h, r) in enumerate(((-6.0, 6, 24), (-3.4, 9, 12), (-0.5, 12, -3), (2.6, 8, -15), (5.2, 5.5, -28))):
        k.box(spires, (sx, 13.0 + h * 0.3, -5.8), (1.2, h * 0.6, 1.2), sp, rot=(6 * (i - 2), 30 * i, r),
              pivot=(sx, 12.6, -5.8), variant=i % 3)
        k.box(spires, (sx, 13.0 + h * 0.75, -5.8), (0.6, h * 0.5, 0.6), sp, rot=(6 * (i - 2) + 10, 30 * i + 45, r * 1.5),
              pivot=(sx, 12.6, -5.8), variant=(i + 1) % 3)
        k.box(spires, (sx, 13.0 + h * 1.02, -5.8), (0.35, 0.9, 0.35), tip, rot=(6 * (i - 2) + 10, 30 * i + 45, r * 1.5),
              pivot=(sx, 12.6, -5.8))
    cr = k.bone("nm_cracks", cover, pivot=(0, 0, -4.02))
    k.plane(cr, "z", (0, 0, -4.03), 26.0, 37.0, crack_overlay(), density=1.5)
    return m


def book_anims():
    """Reader-space values pass through MR/MP (the model is mirrored into bb space)."""
    def fp_tp(fp, tp):
        return M(f"c.is_first_person ? {fp} : {tp}", lambda t: tp)

    place = Anim("place", loop=True)
    place.pos("place", tuple(fp_tp(FP_POS[i], TP_POS[i]) for i in range(3)))
    place.rot("place", tuple(fp_tp(FP_ROT[i], TP_ROT[i]) for i in range(3)))
    place.scl("place", fp_tp(FP_SCALE, TP_SCALE))

    trem = LIFE(0.6, 0.13) * NM
    idle = Anim("idle", loop=True)
    idle.pos("float", MP((0, LIFE(0.9, 3.6) + trem, 0)))
    idle.rot("float", MR((LIFE(3, 5.1), LIFE(5, 7.3), LIFE(2.5, 6.1, 0.3) + NM * 7)))
    idle.rot("cover", MR((0, LIFE(2.2, 4.4, 0, 2.4) + NM * 9, 0)))
    for i in range(3):
        idle.rot(f"leaf{i + 1}", MR((0, LIFE(1.0, 3.1, i * 0.2, 1.2 - i * 0.3), 0)))
    idle.rot("spiral", MR((0, spin(45) + NM * LIFE(12, 0.4), 0)))
    idle.rot("bed", MR((0, 0, LIFE(1.4, 5.3) + NM * LIFE(5, 0.3))))
    idle.scl("blanket", (1, LIFE(0.2, 3.4, 0, 1.0), 1))
    idle.pos("window", MP((LIFE(0.7, 9.1) + NM * 2.2, LIFE(0.45, 6.7) + NM * -1.2, 0)))
    idle.rot("shut_l", MR((0, -(LIFE(20, 4.8, 0, 26) + NM * 50), 0)))
    idle.rot("shut_r", MR((0, LIFE(20, 5.3, 0.3, 26) + NM * 50, 0)))
    idle.rot("door_leaf", MR((0, -(LIFE(16, 6.7, 0, 18) + NM * 60), 0)))
    idle.rot("mobile", MR((LIFE(4, 3.1), spin(30), LIFE(9, 2.6) + NM * LIFE(20, 0.9))))
    for i in range(8):
        idle.pos(f"st{i + 1}", (0, LIFE(0.22, 1.8, i * 0.11) + NM * (0.5 * (i % 2) - 0.25), 0))
    idle.rot("curt_l", MR((LIFE(3, 3.3), 0, LIFE(4, 2.9))))
    idle.rot("curt_r", MR((LIFE(3, 3.6, 0.4), 0, -LIFE(4, 3.1, 0.2))))
    for name, axis in (("c_tl", 2), ("c_tr", 1), ("c_bl", 0), ("c_br", 1)):
        v = [0, 0, 0]
        v[axis] = LIFE(3, 6.0 + axis) + NM * (25 if axis != 1 else -25)
        idle.rot(name, MR(tuple(v)))
    for nmb in ("nm_window", "nm_blanket", "nm_doorglow", "nm_veil", "nm_cracks"):
        idle.scl(nmb, NM)
    idle.scl("nm_spires", (NM, NM * 1.1, NM))
    idle.scl("nm_hands", NM)
    idle.pos("nm_hands", (0, 0, NM * -0.6 + LIFE(0.2, 0.7) * NM))

    flip = Anim("flip", length=0.9, loop="hold")
    flip.rot("cover", MR({0: (0, 0, 0), 0.15: (0, 122, 0), 0.62: (0, 126, 0), 0.9: (0, 0, 0)}))
    for i in range(3):
        t0 = 0.12 + 0.1 * i
        flip.rot(f"leaf{i + 1}", MR({0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.24: (0, 116 - 6 * i, 0), 0.72: (0, 112 - 6 * i, 0),
                                     0.88: (0, 0, 0)}))
    flip.pos("float", {0: (0, 0, 0), 0.15: (0, 1.6, 0), 0.9: (0, 0, 0)})
    flip.rot("float", MR({0: (0, 0, 0), 0.15: (0, 0, -6), 0.5: (0, 0, 3), 0.9: (0, 0, 0)}))

    opn = Anim("open", length=0.6, loop="hold")
    opn.rot("cover", MR({0: (0, 0, 0), 0.35: (0, 156, 0), 0.5: (0, 148, 0), 0.6: (0, 150, 0)}))
    for i, (t0, ang) in enumerate(((0.06, 143), (0.12, 133), (0.18, 116))):
        opn.rot(f"leaf{i + 1}", MR({0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.34: (0, ang + 4, 0), 0.6: (0, ang, 0)}))
    opn.pos("float", {0: (0, 0, 0), 0.4: (0, RISE * 1.08, 0), 0.6: (0, RISE, 0)})
    opn.rot("float", {0: (0, 0, 0), 0.6: (OPEN_TILT, 0, 0)})
    for i in range(4):
        t0 = 0.22 + 0.06 * i
        opn.scl(f"pop{i + 1}", {0: 0.0, t0: 0.0, t0 + 0.12: 1.0, 0.6: 1.0})
        opn.rot(f"pop{i + 1}", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.26: (-60, 0, 0), 0.6: (-52, 0, 0)})
    opn.scl("nm_veil", 0.0)
    shut = Anim("shut", loop=True)     # pop-ups stay folded away while the book is closed
    for i in range(4):
        shut.scl(f"pop{i + 1}", 0.0)
    opn_loop = Anim("open_loop", loop=True)
    opn_loop.rot("leaf3", MR((0, LIFE(11, 1.3), 0)))
    opn_loop.rot("leaf2", MR((0, LIFE(3, 1.7, 0.3), 0)))
    opn_loop.rot("spiral", MR((0, spin(140), 0)))
    for i in range(4):
        opn_loop.rot(f"pop{i + 1}", (LIFE(4, 1.9, i * 0.2), 0, LIFE(2, 2.3, i * 0.3)))
    opn_loop.pos("float", (0, LIFE(0.8, 1.6), 0))
    return [place, idle, flip, opn, opn_loop, shut]


def build_attachable(pack, model, anims):
    geo, tpath = pack.model(model)
    for a in anims:
        a.model = GEO
    _write(os.path.join(pack.rp, "animations", f"{GEO}.animation.json"), animations_file(anims))
    ctl = f"controller.animation.grimoire.{GEO}.pose"
    use = "q.main_hand_item_use_duration > 0.0"
    _write(os.path.join(pack.rp, "animation_controllers", f"{GEO}.animation_controllers.json"), {
        "format_version": "1.10.0",
        "animation_controllers": {ctl: {
            "initial_state": "rest",
            "states": {
                "rest": {"animations": ["shut"], "transitions": [{"use": use}, {"flip": "q.is_sneaking"}],
                         "blend_transition": 0.25},
                "flip": {"animations": ["flip", "shut"], "blend_transition": 0.15,
                         "transitions": [{"use": use}, {"rest": "!q.is_sneaking && q.all_animations_finished"}]},
                "use": {"animations": ["open", "open_loop"], "blend_transition": 0.3,
                        "transitions": [{"rest": "q.main_hand_item_use_duration <= 0.0"}]},
            }}},
    })
    rc = f"controller.render.grimoire.{GEO}"
    mats_ = [{"*": "Material.default"}] + [{b: "Material.blend"} for b in model.blend_bones]
    _write(os.path.join(pack.rp, "render_controllers", f"{GEO}.render_controllers.json"),
           {"format_version": "1.8.0", "render_controllers": {rc: {"geometry": "Geometry.default", "materials": mats_,
                                                                    "textures": ["Texture.default"]}}})
    amap = {a.name: a.full for a in anims}
    amap["pose"] = ctl
    _write(os.path.join(pack.rp, "attachables", f"{ITEM_SUFFIX}.json"), {
        "format_version": "1.10.0",
        "minecraft:attachable": {"description": {
            "identifier": ITEM_ID,
            "materials": {"default": "entity_emissive_alpha", "blend": "entity_alphablend"},
            "textures": {"default": tpath},
            "geometry": {"default": geo},
            "animations": amap,
            "scripts": {"animate": ["place", "idle", "pose"]},
            "render_controllers": [rc],
        }},
    })


def write_icon(pack, model, idle):
    """32x32 inventory icon: supersampled render, contrast/saturation lift, crisp alpha, dark outline."""
    img = render(model, idle.pose(0.0), yaw=16, pitch=8, size=(32, 32), bg=(58, 40, 62, 0), ss=8, margin=0.02,
                 hide=("nm_",))
    a = np.asarray(img).astype(float)
    rgb_ = a[..., :3] / 255.0
    lum = rgb_.mean(axis=2, keepdims=True)
    rgb_ = np.clip(lum + (rgb_ - lum) * 1.3, 0, 1)
    rgb_ = np.clip((rgb_ - 0.5) * 1.18 + 0.52, 0, 1)
    on = a[..., 3] >= 110
    pad = np.pad(on, 1)
    near = (pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]) & ~on
    out = np.zeros((32, 32, 4), dtype=np.uint8)
    out[..., :3] = np.round(rgb_ * 255)
    out[..., 3] = np.where(on, 255, 0)
    out[near] = (52, 34, 58, 255)
    p = os.path.join(pack.rp, "textures", "items", f"grimoire_{ITEM_SUFFIX}.png")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    Image.fromarray(out, "RGBA").save(p, optimize=True)
    if getattr(pack.preview, "enabled", False):
        Image.fromarray(out, "RGBA").resize((256, 256), Image.NEAREST).save(os.path.join(PREVIEW, "book_dn_icon.png"))


# ------------------------------------------------------------------------------- selection vision
def vision_model(kind):
    m = Model(f"book_dn_vision_k{kind}", density=3.0, bounds=(2, 2, (0, 0.4, 0)))
    root = m.bone("root")
    page = m.bone("page", root)
    paper = tex.porcelain("#f7ecd6", "#ead6b8", crack=0.0)
    ink = ink_door()
    side = leaf_mat(kind + 3)
    fl = m.bone("flap_l", page, pivot=(-3, 0, 0))
    fl.box((-4.5, 0, 0), (3, 10, 0.2), paper, mats={"north": side, "south": side})
    fr = m.bone("flap_r", page, pivot=(3, 0, 0))
    fr.box((4.5, 0, 0), (3, 10, 0.2), paper, mats={"north": side, "south": side})
    ft = m.bone("flap_t", page, pivot=(0, 5, 0))
    ft.box((0, 6.5, 0), (12, 3, 0.2), paper, mats={"north": side, "south": side})
    lf = m.bone("leaf", page, pivot=(-3, 0, 0))
    lf.box((0, 0, 0.05), (6, 10, 0.2), paper, mats={"north": ink, "south": side})
    bd = m.bone("backdrop", page, pivot=(0, 0, 0.6))
    bd.plane("z", (0, 0, 0.6), 6, 10, backdrop(kind), faces=("north",))
    page.locator("door", (0, 0, -1.0))
    scene = m.bone("scene", root, pivot=(0, 0, 0))
    k = K(m, VS, (0, 0, 0), pre=f"k{kind}_")
    CORES[kind](k, scene)
    return m


def vision_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    show = Anim("show", length=VISION_LEN, loop="hold")
    show.scl("root", {0: 0.0, 0.1: 1.08, 0.18: 1.0, 1.02: 1.0, 1.1: 1.08, 1.2: 0.0})
    show.rot("root", {0: (0, -30, 10), 0.2: (0, 0, 0), 1.0: (0, 0, 0), 1.2: (0, 25, -8)})
    show.pos("root", {0: (0, -3, 0), 0.2: (0, 0, 0), 1.2: (0, 1.5, 0)})
    show.rot("flap_l", {0: (0, 0, 0), 0.16: (0, 0, 0), 0.36: (0, -98, 0), 0.44: (0, -88, 0)})
    show.rot("flap_r", {0: (0, 0, 0), 0.2: (0, 0, 0), 0.4: (0, 98, 0), 0.48: (0, 88, 0)})
    show.rot("flap_t", {0: (0, 0, 0), 0.24: (0, 0, 0), 0.44: (-98, 0, 0), 0.52: (-88, 0, 0)})
    show.rot("leaf", {0: (0, 0, 0), 0.46: (0, 0, 0), 0.52: (0, 8, 0), 0.7: (0, -116, 0), 0.8: (0, -104, 0)})
    show.scl("backdrop", {0: 0.0, 0.44: 0.0, 0.47: 1.0})
    show.pos("scene", {0: (0, -1, 3), 0.56: (0, -1, 3), 0.84: (0, 8.8, -2.5), 1.0: (0, 9.4, -2.5), 1.2: (0, 10, -2)})
    show.scl("scene", {0: 0.0, 0.54: 0.0, 0.62: 0.35, 0.84: 1.15, 0.95: 1.0, 1.08: 1.0, 1.2: 0.4})
    show.rot("scene", {0: (0, -40, 0), 0.56: (0, -40, 0), 1.2: (0, 35, 0)})
    show.sound(0.44, "door")
    show.particle(0.6, "spill", locator="door")
    life = Anim("life", loop=True)
    for kd in range(6):
        core_motion(life, kd, VS)
    return [hidden, show, life]


# ------------------------------------------------------------------------------- charge construct
def charge_model(kind):
    m = Model(f"book_dn_charge_k{kind}", density=2.0, bounds=(4, 3.5, (0, 0.2, 0)))
    root = m.bone("root")
    rig = m.bone("rig", root)
    rig.locator("core", (0, 0, 0))
    mood = MOODS[kind]
    night = mood in ("night",)
    c0, c1 = ((SGOLD, PINK) if not night else ("#c0485e", MAUVE))
    if mood in ("both", "dream_to_night"):
        c0, c1 = (PEACH, MAUVE)
    if mood == "strange":
        c0, c1 = ("#f0d0ff", SGOLD)
    plate = m.bone("plate", rig, pivot=(0, -9, 0))
    plate.plane("y", (0, -9, 0), 30, 30, tex.magic_circle(DREAM_SCRIPT, c0, c1, glow=1.0, bands=((0.8, 0.94, 14),),
                                                           lines=(0.76, 0.97, 0.5), star=0, core=0.0,
                                                           key=f"bdnplate{kind}"), faces=("up", "down"))
    core = m.bone("core", rig, pivot=(0, -7, 0))
    CORES[kind](K(m, CS, (0, 0, 0), pre=f"k{kind}_"), core)
    orbit = m.bone("orbit", rig)
    for i, ((part, pal, _h), (x, y, z, ang)) in enumerate(zip(FRAGS[kind], frag_centers(kind))):
        fb = m.bone(f"frag{i + 1}", orbit, pivot=(x, y, z), rot=(0, -(90 + ang), 0))
        kk = K(m, FS, (x, y, z))
        PARTS[part](kk, fb, (0, 0, 0), palette(pal))
    return m


def charge_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    life = Anim("life", loop=True)
    life.rot("orbit", (0, spin(32), 0))
    life.pos("rig", (0, LIFE(0.7, 3.2), 0))
    life.rot("rig", (LIFE(2, 5.3), 0, LIFE(2, 6.7, 0.25)))
    life.rot("plate", (0, spin(-14), 0))
    for i in range(6):
        life.rot(f"frag{i + 1}", (LIFE(6, 3.1 + i * 0.37, i / 6), LIFE(12, 4.3 + i * 0.29, i / 5), LIFE(5, 2.7 + i * 0.4)))
        life.pos(f"frag{i + 1}", (0, LIFE(0.8, 2.4 + i * 0.21, i / 6), 0))
    for kd in range(6):
        core_motion(life, kd, CS)

    form = Anim("form", length=FORM_LEN, loop="hold")
    form.scl("plate", {0: 0.0, 0.45: 1.12, 0.65: 1.0})
    form.rot("plate", {0: (0, -120, 0), 0.65: (0, 0, 0)})
    form.scl("core", {0: 0.0, 0.2: 0.0, 0.85: 1.1, 1.05: 1.0})
    form.pos("core", {0: (0, -5, 0), 0.2: (0, -5, 0), 0.85: (0, 0.6, 0), 1.05: (0, 0, 0)})
    form.rot("core", {0: (0, 160, 0), 0.2: (0, 160, 0), 1.05: (0, 0, 0)})
    for sgn, nm in ((-1, "k2_front_l"), (1, "k2_front_r")):
        form.rot(nm, {0: (0, sgn * 118, 0), 0.8: (0, sgn * 118, 0), 1.25: (0, -sgn * 8, 0), 1.4: (0, 0, 0)})
    form.rot("k1_leaf", {0: (0, -36, 0), 0.85: (0, -36, 0), 1.2: (0, 12, 0), 1.4: (0, 0, 0)})
    form.scl("k5_hands", {0: 0.0, 1.0: 0.0, 1.4: 1.0})
    form.scl("k4_astair", {0: 0.0, 0.9: 0.0, 1.35: 1.0})
    form.scl("k3_tring", {0: (1, 0, 1), 0.7: (1, 0, 1), 1.2: (1, 1.1, 1), 1.4: (1, 1, 1)})
    form.scl("k0_road", {0: (0, 1, 0), 0.4: (0, 1, 0), 1.0: (1.05, 1, 1.05), 1.15: (1, 1, 1)})
    for i, (x, y, z, _a) in enumerate(frag_centers(0)):
        t0 = 0.3 + i * 0.13
        form.pos(f"frag{i + 1}", {0: (-x * 0.92, -y - 4, -z * 0.92), t0: (-x * 0.92, -y - 4, -z * 0.92),
                                  t0 + 0.55: (0, 0, 0)})
        form.scl(f"frag{i + 1}", {0: 0.0, t0: 0.0, t0 + 0.4: 1.15, t0 + 0.55: 1.0})
        form.rot(f"frag{i + 1}", {0: (0, 200, 0), t0: (0, 200, 0), t0 + 0.55: (0, 0, 0)})

    loop = Anim("loop", loop=True, length=2.0)
    loop.scl("plate", LIFE(0.03, 1.0, 0, 1.0))
    loop.particle(0.0, "mote", locator="core")
    loop.particle(1.0, "mote", locator="core")

    rel = Anim("release", length=RELEASE_LEN, loop="hold")
    rel.scl("root", {0: 1.0, 0.12: 1.25, 0.32: 1.1, 0.5: 0.0})
    rel.scl("plate", {0: 1.0, 0.2: 1.6, 0.5: 2.4})
    rel.rot("core", {0: (0, 0, 0), 0.5: (0, 200, 0)})
    rel.scl("core", {0: 1.0, 0.15: 1.3, 0.5: 0.4})
    for i, (x, y, z, _a) in enumerate(frag_centers(0)):
        rel.pos(f"frag{i + 1}", {0: (0, 0, 0), 0.5: (x * 0.9, y * 0.5 + 5, z * 0.9)})
        rel.rot(f"frag{i + 1}", {0: (0, 0, 0), 0.5: (0, 0, 120 if i % 2 else -120)})
    rel.particle(0.0, "burst", locator="core")

    can = Anim("cancel", length=CANCEL_LEN, loop="hold")
    can.scl("root", {0: 1.0, 0.3: 0.9, 0.4: 0.0})
    can.scl("core", {0: 1.0, 0.35: 0.0})
    can.pos("core", {0: (0, 0, 0), 0.35: (0, -4, 0)})
    can.scl("plate", {0: 1.0, 0.4: 0.0})
    for i, (x, y, z, _a) in enumerate(frag_centers(0)):
        can.pos(f"frag{i + 1}", {0: (0, 0, 0), 0.4: (-x * 0.9, -y - 3, -z * 0.9)})
        can.scl(f"frag{i + 1}", {0: 1.0, 0.4: 0.0})
    return [hidden, life, form, loop, rel, can]


# ------------------------------------------------------------------------------- particles / sounds
def build_fx(pack):
    fx = particles(pack)
    fx.effect("book_dn_mote", None, sprites=["star", "moon", "dot", "key", "door", "window"], count=4, life=(1.0, 1.8),
              size=(0.08, 0.02), shape=("sphere", 1.1), speed=(0.05, 0.35), accel=(0, 0.25, 0), drag=0.8,
              colors=["#fff3e0ff", "#ffd9b8ff", "#e8b4c8cc", "#bcd6f000"], spin=(360, 40))
    fx.effect("book_dn_burst", None, sprites=["door", "window", "key", "star", "moon", "petal", "ring"], count=22,
              life=(0.6, 1.4), size=(0.2, 0.04), shape=("sphere", 0.4), speed=(2.0, 5.5), accel=(0, -0.6, 0), drag=2.2,
              colors=["#ffffffff", "#ffd9b8ff", "#e8b4c8ff", "#8a6ad6cc", "#2a2d5200"], spin=(360, 160))
    fx.effect("book_dn_spill", "glow", count=6, life=(0.4, 0.8), size=(0.18, 0.0), shape=("sphere", 0.2),
              speed=(0.4, 1.4), direction=(0, 0.2, -1), drag=1.5, colors=["#fff6e0ff", "#ffd9b8aa", "#e8b4c800"])


def build_sounds(pack):
    def mbox(f, dur=0.7, warp=0.0):
        """Music-box tine: bright pluck + faint bell, with an optional slow detune (dream warp)."""
        s = sy.mixdown([sy.pluck(f, dur, 0.85), sy.bell(f * 2, dur, 0.6) * 0.35])
        if warp:
            s = sy.pitch(s, 1.0 - warp)
        return s

    def rustle(dur=0.35):
        n = sy.bandpass(sy.noise(dur), 3200, 0.9) * sy.env(dur, 0.02, 0.08, 0.5, dur * 0.5)
        flick = sy.highpass(sy.noise(0.04), 5000) * sy.decay(0.04, 0.008)
        return sy.at(dur, (0.0, n * 0.7), (dur * 0.55, flick * 0.8))

    # select: two quick page flicks, a little latch-and-door click, then an invented four-tine motif
    # (a rising minor sixth that falls back a tritone - deliberately not any known tune)
    motif = [(0.36, 1244.5), (0.48, 1975.5), (0.62, 1396.9), (0.80, 987.8)]
    sel = sy.at(1.4, (0.0, rustle(0.3) * 0.6), (0.14, rustle(0.28) * 0.5),
                (0.3, sy.crack(0.08, 3200, 3) * 0.25), (0.31, sy.thump(0.15, 420, 180, 0.2) * 0.25),
                *[(t, mbox(f, 0.7, 0.012 * i) * (0.55 - 0.06 * i)) for i, (t, f) in enumerate(motif)],
                (0.36, sy.pad(311.1, 1.0, 3, "tri", 1200, 0.2, 0.6) * 0.18))
    sy.save(pack, "book_dn_select", sy.reverb(sel, 1.6, 0.4), volume=0.75, max_distance=24)

    # charge: a 2 s swell - warm pad drifting out of tune, reversed shimmer rising, faint clockwork and a
    # door hinge somewhere far off; ends on a held breath so it can retrigger.
    dur = 2.1
    t = sy.t_axis(dur)
    warble = 1 + 0.008 * np.sin(2 * np.pi * 0.9 * t) * np.linspace(0.2, 1, len(t))
    pad1 = sy.osc(233.1 * warble, wave_="tri") + 0.6 * sy.osc(349.2 * warble * 1.004, wave_="tri") \
        + 0.4 * sy.osc(466.2 * warble * 0.996, wave_="sine")
    pad1 = sy.lowpass(pad1, 1500) * np.linspace(0.05, 1.0, len(t)) ** 1.6
    shim = sy.shimmer(1.6, 2200, 24)[::-1]
    ticks = np.zeros(int(sy.SR * dur))
    for i in range(14):
        c = sy.crack(0.03, 5200, 1) * (0.15 + 0.2 * i / 14)
        p = int(sy.SR * (0.15 + i * 0.13))
        ticks[p:p + len(c)] += c[:len(ticks) - p]
    hinge = sy.creak(0.6, 260, 380, 0.3) * 0.12
    ch = sy.at(dur, (0.0, sy.norm(pad1) * 0.7), (0.5, shim * 0.4), (0.0, ticks), (1.1, hinge),
               (1.4, sy.whoosh(0.7, 400, 2600) * 0.25))
    sy.save(pack, "book_dn_charge", sy.reverb(ch, 1.8, 0.4), volume=0.7, max_distance=24)

    # release: the little door flung open - hinge snap, a gust out of it, a glittering bell cluster that
    # bends half a step flat (dream tipping toward nightmare), a soft low thud underneath
    cl = sy.mixdown([sy.bell(f, 1.4, 0.8) for f in (622.3, 932.3, 1244.5, 1661.2)])
    bend = sy.pitch(cl, 1.03)[: int(sy.SR * 1.3)]
    rel = sy.at(1.8, (0.0, sy.creak(0.18, 420, 620, 0.2) * 0.35), (0.06, sy.whoosh(0.6, 3200, 500) * 0.6),
                (0.08, bend * 0.6), (0.08, sy.thump(0.6, 120, 45, 0.3) * 0.55), (0.2, sy.shimmer(1.2, 2600, 18) * 0.3))
    sy.save(pack, "book_dn_release", sy.reverb(rel, 2.0, 0.42), volume=0.9, max_distance=40)

    # deny: a music box winding down - three tines, each slower and flatter - then the door shuts softly
    den = sy.at(1.0, (0.0, mbox(880.0, 0.4) * 0.5), (0.16, mbox(830.6, 0.4, 0.02) * 0.42),
                (0.36, mbox(739.99, 0.5, 0.05) * 0.36), (0.6, sy.thump(0.25, 220, 90, 0.4) * 0.45),
                (0.6, sy.crack(0.06, 2400, 2) * 0.15))
    sy.save(pack, "book_dn_deny", sy.reverb(den, 1.0, 0.3), volume=0.6, max_distance=16)

    # vision door: short creak opening onto a breath of warm air and one high tine
    door = sy.at(0.9, (0.0, sy.creak(0.4, 300, 520, 0.25) * 0.45), (0.25, sy.whoosh(0.5, 600, 2400) * 0.35),
                 (0.3, mbox(1568.0, 0.6, 0.01) * 0.4))
    sy.save(pack, "book_dn_door", sy.reverb(door, 1.2, 0.35), volume=0.55, max_distance=16)


# ------------------------------------------------------------------------------- previews
def _grid(rows, path):
    w = max(sum(im.width for im in r) for r in rows)
    h = sum(max(im.height for im in r) for r in rows)
    out = Image.new("RGBA", (w, h), (34, 38, 46, 255))
    y = 0
    for r in rows:
        x = 0
        for im in r:
            out.paste(im, (x, y))
            x += im.width
        y += max(im.height for im in r)
    out.save(path)


def _merge(*pairs):
    merged = {}
    for a, t in pairs:
        for b, (r, pp, s) in a.pose(t).items():
            if b in merged:
                r0, p0, s0 = merged[b]
                merged[b] = (tuple(r0[i] + r[i] for i in range(3)), tuple(p0[i] + pp[i] for i in range(3)),
                             tuple(s0[i] * s[i] for i in range(3)))
            else:
                merged[b] = (r, pp, s)
    return merged


def previews(pack, book, banims, visions, vanims, charges, canims):
    if not getattr(pack.preview, "enabled", False):
        return
    os.makedirs(PREVIEW, exist_ok=True)
    by = {a.name: a for a in banims}
    idle, flip, opn, opl = by["idle"], by["flip"], by["open"], by["open_loop"]
    poses = [_merge((idle, 0.0)), _merge((idle, 6.0)), _merge((idle, 1.0), (flip, 0.42)),
             _merge((idle, 1.0), (opn, 0.6), (opl, 0.5))]
    views = ((0, 6), (35, 18), (90, 6), (180, 12))
    rows = [[render(book, p, yaw=y, pitch=pt, size=(340, 340)) for (y, pt) in views] for p in poses]
    _grid(rows, os.path.join(PREVIEW, "book_dn.png"))
    rows = [[render(book, poses[0], yaw=8, pitch=4, size=(700, 700), fit=((-2.5, 2, -5), 10.5)),
             render(book, poses[1], yaw=-14, pitch=8, size=(700, 700), fit=((-2.5, 2, -5), 10.5))]]
    _grid(rows, os.path.join(PREVIEW, "book_dn_room.png"))
    vb = {a.name: a for a in vanims}
    rows = []
    for kd, vm in enumerate(visions):
        rows.append([render(vm, _merge((vb["show"], t), (vb["life"], t)), yaw=y, pitch=12, size=(230, 230),
                            fit=((0, 4, 0), 10)) for t, y in ((0.3, 20), (0.6, 20), (0.9, 20), (0.95, 160))])
    _grid(rows, os.path.join(PREVIEW, "book_dn_vision.png"))
    cb = {a.name: a for a in canims}
    rows = []
    for kd, cm in enumerate(charges):
        rows.append([render(cm, _merge((cb["form"], 0.75), (cb["life"], 0.75)), yaw=25, pitch=18, size=(260, 260),
                            fit=((0, 0, 0), 23)),
                     render(cm, _merge((cb["form"], 1.5), (cb["life"], 2.0)), yaw=25, pitch=18, size=(260, 260),
                            fit=((0, 0, 0), 23)),
                     render(cm, _merge((cb["form"], 1.5), (cb["life"], 3.0)), yaw=-150, pitch=10, size=(260, 260),
                            fit=((0, 0, 0), 23)),
                     render(cm, _merge((cb["form"], 1.5), (cb["life"], 2.0)), yaw=10, pitch=12, size=(260, 260),
                            fit=((0, 0, 0), 9), hide=("frag", "plate"))])
    _grid(rows, os.path.join(PREVIEW, "book_dn_charge.png"))


# ------------------------------------------------------------------------------- build
def build(pack):
    build_fx(pack)
    build_sounds(pack)
    book = book_model()
    banims = book_anims()
    build_attachable(pack, book, banims)
    write_icon(pack, book, banims[1])

    visions = [vision_model(i) for i in range(6)]
    vanims = vision_anims()
    pack.actor("book_dn_vision", visions[0], vanims, {0: ["hidden"], 1: ["show"]}, always=["life"],
               kinds=visions[1:], lifetime=30, sounds={"door": "grimoire.book_dn_door"},
               particles={"spill": "grimoire:book_dn_spill"}, display="Unawakened Codex Vision", blend=0.0)

    charges = [charge_model(i) for i in range(6)]
    canims = charge_anims()
    pack.actor("book_dn_charge", charges[0], canims,
               {0: ["hidden"], 1: ["form"], 2: ["loop"], 3: ["release"], 4: ["cancel"]}, always=["life"],
               kinds=charges[1:], lifetime=120,
               particles={"mote": "grimoire:book_dn_mote", "burst": "grimoire:book_dn_burst"},
               display="Unawakened Codex Construct", blend=0.15)
    previews(pack, book, banims, visions, vanims, charges, canims)
