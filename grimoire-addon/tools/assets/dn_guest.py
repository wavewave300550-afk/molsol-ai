"""DN02 Nightmare Intrusion: The Guest Behind the Door.

Two original actors:

  dn_guest_door  A free-standing antique bedroom door in a carved, faded-burgundy frame (door 5 blocks,
                 crest ~6.3 blocks) with brass lever handle on its own bone, hinges, a frieze of dream
                 pictograms, a sleeping-eye crest and a cold-glowing keyhole.  Behind the opening lies a
                 forced-perspective corridor built from real geometry: nine nested, geometrically
                 shrinking segments (damask wallpaper over burgundy wainscot, a runner carpet on
                 floorboards, plaster ceiling, wall sconces, picture frames, a moulded frame at every
                 mouth) that is only ~1.3 blocks deep but converges on a vanishing point at eye height,
                 so it reads as tens of metres.  The far end holds a tiny second door that breathes.
                 Skin 1 ("cracked"): the slam splits the paint with glowing fractures and kills the lamps.

  dn_guest       The Guest: a 6.7-block faceless figure in a yellowed nightgown and a moth-eaten indigo
                 coat; narrow sloped shoulders, a too-long neck, a smooth elongated porcelain head with a
                 hairline seam and a door-knob dimple where a face should be, vertebrae through the coat,
                 and arms that hang to its ankles (shoulder, 2 upper, elbow, 2 fore, wrist, 4 two-joint
                 fingers + thumb).  It approaches up the corridor in perspective (tiny, then suddenly
                 close), grips the frame, leans its head out sideways, stoops through, reaches with arms
                 that really lengthen (segment scale), grabs, drags and withdraws.

Arm poses are solved with a small two-bone IK (plus stretch) so the hands meet exactly the grip and drag
points used by src/spells/dn02_nightmare_intrusion.ts (GRAB_Z / PULL_Z / HAND_Y below, in 1/16 block
units in front of the door plane).
"""
import math

import numpy as np

from kit import glyphs, synth as sy, tex
from kit.anim import LIFE, Anim, Expr, M, S
from kit.geo import Mat, Model

from .a_fx_common import particles

# ---------------------------------------------------------------- palette (nightmare side of the book)
INDIGO, MAUVE, BURG, AIV, CGRAY = "#2a2d52", "#6a4a6e", "#6e2f3a", "#cfc6b0", "#8b8f9a"
FRAME_P, FRAME_DK, WOOD_UNDER = "#5b2f37", "#3a2128", "#2a1a1b"
LAMP, COLD, FOG, GILT = "#efdca6", "#e6defc", "#121226", "#8a7448"

# ---------------------------------------------------------------- shared geometry constants (keep in sync with TS)
OPEN_W, OPEN_H = 18.0, 78.0        # half width / height of the doorway
VP = 30.0                          # vanishing point height (viewer eye level)
N_SEG, RATIO, D0, Z0 = 9, 0.78, 5.0, 3.0
KEY_P = (-14.0, 32.6, -1.8)        # keyhole: the door folds into it when it vanishes
GRAB_Z, PULL_Z, HAND_Y, HAND_X = -42.0, -18.0, 17.0, 4.2   # TS: standoff 42/16, pullStop 18/16
GUEST_Z = 5.0                      # the Guest stands just behind the threshold
G_FRAME = (-20.0, 50.0, -4.4)      # where its left hand grips the door frame

# animation lengths (seconds) -- mirrored as tick constants in the spell
DOOR_LEN = dict(manifest=1.2, handle=1.4, open=1.2, slam=0.6, vanish=1.0)
GUEST_LEN = dict(emerge=2.6, reach=1.2, grab=0.5, pull=1.6, withdraw=1.1, miss=0.9)

DOOR_STATES = {0: ["hidden"], 1: ["manifest"], 2: ["closed"], 3: ["handle"], 4: ["open"], 5: ["held"],
               6: ["slam"], 7: ["vanish"]}
GUEST_STATES = {0: ["hidden"], 1: ["emerge"], 2: ["reach"], 3: ["grab"], 4: ["pull"], 5: ["withdraw"],
                6: ["miss"]}

rgb = tex.rgb


def seg_table():
    """Mouth i of the corridor: scale s, depth z, half width w, floor yf, ceiling yc."""
    out, z = [], Z0
    for i in range(N_SEG + 1):
        s = RATIO ** i
        out.append(dict(s=s, z=z, w=OPEN_W * s, yf=VP * (1 - s), yc=VP + (OPEN_H - VP) * s))
        z += D0 * s
    return out


def zs(s):
    """Corridor depth at which the perspective scale is s (continuous version of seg_table)."""
    return Z0 + D0 * (1 - s) / (1 - RATIO)


def spin(rate):
    return M(f"q.life_time*{rate}", lambda t: t * rate)


# ================================================================ materials
def _coords(ctx):
    if ctx.face in ("north", "south"):
        return ctx.X, ctx.Y
    if ctx.face in ("east", "west"):
        return ctx.Z, ctx.Y
    return ctx.X, ctx.Z


def _cracks(ctx, t, a, b, seed):
    """'cracked' skin: glowing fractures and a scorched, darkened surface."""
    if ctx.alt != "cracked":
        return t
    r1 = np.abs(tex.fbm(a / 7.0 + seed, b / 7.0, 61) - 0.5) < 0.03
    r2 = np.abs(tex.vnoise(a / 3.0, b / 3.0 + seed, 67) - 0.5) < 0.03
    c = r1 | (r2 & (tex.fbm(a / 10.0, b / 10.0, 71) > 0.52))
    t[..., :3] = np.where(c[..., None], rgb("#f1e9ff"), t[..., :3] * 0.72)
    t[..., 4] = np.where(c, 1.0, t[..., 4] * 0.3)
    return t


def painted(paint, under, key, peel=0.2, grime=0.3, seed=0, post=None):
    """Old painted wood: paint flaking off the grain, grime toward the floor, cracks in the alt skin."""
    kp, ku = rgb(paint), rgb(under)

    def fn(ctx):
        a, b = _coords(ctx)
        n = tex.fbm(a / 4.0 + seed, b / 4.0, 41 + seed)
        col = kp * (0.84 + 0.26 * n)[..., None]
        gr = tex.fbm(a / 0.9, b / 7.0 + seed, 43)
        wood = tex.mix(ku * 0.75, ku * 1.25, gr[..., None])
        pm = tex.fbm(a / 2.2 + 13 + seed, b / 2.2, 47) > 1 - peel
        col = np.where(pm[..., None], wood, col)
        g = np.clip((26 - ctx.Y) / 26, 0, 1) * grime
        col = col * (1 - 0.5 * g)[..., None]
        t = tex.tile(ctx, paint)
        t[..., :3] = np.clip(col, 0, 1)
        if post:
            t = post(ctx, t)
        t = tex.edge(ctx, t, 0.16)
        t = _cracks(ctx, t, a, b, seed)
        return tex.grain(ctx, t, 0.03)
    return Mat(fn, key, spatial=True)


PANELS = [(0.12, 0.05, 0.44, 0.22), (0.56, 0.05, 0.88, 0.22), (0.12, 0.28, 0.44, 0.48),
          (0.56, 0.28, 0.88, 0.48), (0.12, 0.58, 0.44, 0.94), (0.56, 0.58, 0.88, 0.94)]
LEAF_W, LEAF_Y0, LEAF_H = 36.0, 0.6, 77.4


def _panel_grooves(ctx, t):
    U, V = ctx.U, ctx.V
    for u0, v0, u1, v1 in PANELS:
        inside = (U > u0) & (U < u1) & (V > v0) & (V < v1)
        d = np.minimum(np.minimum(U - u0, u1 - U) * LEAF_W, np.minimum(V - v0, v1 - V) * LEAF_H)
        groove = inside & (d < 0.9)
        recess = inside & (d >= 0.9) & (d < 2.0)
        t[..., :3] = np.where(groove[..., None], t[..., :3] * 0.5, t[..., :3])
        t[..., :3] = np.where(recess[..., None], t[..., :3] * 0.8, t[..., :3])
    return t


def wallpaper(i, fog):
    """Bruised-mauve damask over burgundy wainscot; picture frames on even segments; lamp pools."""
    def fn(ctx):
        U, V = ctx.U, ctx.V
        ix, iy = tex.px(ctx)
        a, b = U * 14.0, V * 78.0
        stripe = (np.floor(a / 3.5) % 2 == 0)
        col = np.where(stripe[..., None], rgb("#62435f"), rgb("#53375a"))
        med = np.cos(((a % 7.0) - 3.5) * 0.9) * np.cos(((b % 10.0) - 5.0) * 0.63)
        col = np.where((med > 0.55)[..., None], rgb("#7d5a7d"), col)
        wain = V > 0.66
        col = np.where(wain[..., None], rgb("#4a2630") * (0.9 + 0.12 * np.cos(a * 1.7))[..., None], col)
        col = np.where(((V > 0.64) & (V < 0.675))[..., None], rgb("#2e1b1c"), col)
        col = np.where((V < 0.035)[..., None], rgb("#2e1b1c"), col)
        n = tex.fbm(ix / 3.0 + i * 3.1, iy / 3.0, 31)
        col = col * (0.8 + 0.32 * n)[..., None]
        glow = np.full(U.shape, 0.04)
        if i % 2 == 0:
            fr = (np.abs(U - 0.5) < 0.2) & (V > 0.08) & (V < 0.27)
            bw, bh = 1.2 / max(ctx.w, 1), 1.2 / max(ctx.h, 1)
            inner = (np.abs(U - 0.5) < 0.2 - bw) & (V > 0.08 + bh) & (V < 0.27 - bh)
            col = np.where((fr & ~inner)[..., None], rgb(GILT), col)
            col = np.where(inner[..., None], rgb("#17152b"), col)
        if ctx.alt != "cracked":
            d = np.hypot((U - 0.5) * 1.3, (V - 0.38) * 1.0)
            pool = np.clip(1 - d / 0.42, 0, 1) ** 2
            col = col + pool[..., None] * rgb(LAMP) * 0.5
            glow = glow + pool * 0.45
        else:
            col = col * 0.55
        col = tex.mix(col, rgb(FOG), fog)
        t = tex.tile(ctx, "#000000")
        t[..., :3] = np.clip(col, 0, 1)
        t[..., 4] = glow
        return t
    return Mat(fn, f"dngd_wp{i}")


def floor_mat(i, fog):
    """Dark floorboards running away from the viewer with a faded burgundy runner carpet."""
    def fn(ctx):
        U, V = ctx.U, ctx.V
        ix, iy = tex.px(ctx)
        n = tex.fbm(ix / 1.2 + i * 5, iy / 6.0, 33)
        col = tex.mix(rgb("#2e1f1d"), rgb("#4c3328"), n[..., None])
        bw = max(2, int(round(ctx.w / 9)))
        col = np.where(((ix % bw) == 0)[..., None], rgb("#1a1112"), col)
        c = np.abs(U - 0.5)
        run = c < 0.24
        dia = (np.abs((V * 5 + 0.5 * i) % 1 - 0.5) + np.abs(((U - 0.5) / 0.4 * 3) % 1 - 0.5)) < 0.22
        rc = np.where(dia[..., None], rgb("#7a4a62"), rgb("#5e2632"))
        col = np.where(run[..., None], rc * (0.85 + 0.2 * n)[..., None], col)
        col = np.where(((c > 0.195) & (c < 0.225))[..., None], rgb("#a89c80"), col)
        if ctx.alt == "cracked":
            col = col * 0.6
        col = tex.mix(col, rgb(FOG), fog)
        t = tex.tile(ctx, "#000000", 1, 0.03)
        t[..., :3] = np.clip(col, 0, 1)
        return t
    return Mat(fn, f"dngd_floor{i}")


def ceil_mat(i, fog):
    def fn(ctx):
        ix, iy = tex.px(ctx)
        n = tex.fbm(ix / 2.5 + i, iy / 2.5, 35)
        col = tex.mix(rgb("#262439"), rgb("#3b3852"), n[..., None])
        cr = np.abs(tex.vnoise(ix / 3.0 + i * 7, iy / 3.0, 37) - 0.5) < 0.03
        col = np.where(cr[..., None], rgb("#15131f"), col)
        col = tex.mix(col, rgb(FOG), fog)
        t = tex.tile(ctx, "#000000", 1, 0.02)
        t[..., :3] = np.clip(col, 0, 1)
        return t
    return Mat(fn, f"dngd_ceil{i}")


def ring_mat(i, hole, W, H, s, fog):
    """The moulded frame at the mouth of the next corridor segment (a plane with a rectangular hole)."""
    u0, u1, v0, v1 = hole

    def fn(ctx):
        U, V = ctx.U, ctx.V
        inside = (U > u0) & (U < u1) & (V > v0) & (V < v1)
        dx = np.maximum(np.maximum(u0 - U, U - u1), 0) * W
        dy = np.maximum(np.maximum(v0 - V, V - v1), 0) * H
        dd = np.hypot(dx, dy)
        col = np.full(U.shape + (3,), rgb("#2b191b"))
        col = np.where((dd < 3.4 * s)[..., None], rgb("#5b3138"), col)
        col = np.where((dd < 1.9 * s)[..., None], rgb("#43242a"), col)
        col = np.where((dd < 0.9 * s + 0.4)[..., None], rgb(GILT), col)
        if ctx.alt == "cracked":
            col = col * 0.6
        col = tex.mix(col, rgb(FOG), fog)
        t = tex.tile(ctx, "#000000", 1, 0.05)
        t[..., :3] = col
        t[..., 3] = np.where(inside, 0.0, 1.0)
        return t
    return Mat(fn, f"dngd_ring{i}")


def lamp_mat(fog):
    def fn(ctx):
        if ctx.alt == "cracked":
            return tex.tile(ctx, "#29252f", 1, 0.0)
        t = tex.tile(ctx, LAMP, 1, 1.0)
        t[..., :3] = tex.mix(rgb("#fff4d6"), rgb(LAMP), fog * 0.6)
        return t
    return Mat(fn, f"dngd_lamp{fog:.2f}")


def far_mat():
    """The far end: darkness, and a tiny door whose keyhole is lit."""
    def fn(ctx):
        U, V = ctx.U, ctx.V
        t = tex.tile(ctx, "#0c0b18", 1, 0.02)
        door = (np.abs(U - 0.5) < 0.17) & (V > 0.32) & (V < 0.97)
        edge = door & ~((np.abs(U - 0.5) < 0.17 - 1.0 / ctx.w) & (V > 0.32 + 1.0 / ctx.h))
        t[..., :3] = np.where(door[..., None], rgb("#2c2836"), t[..., :3])
        t[..., :3] = np.where(edge[..., None], rgb("#4a4258"), t[..., :3])
        if ctx.alt != "cracked":
            kh = (np.abs(U - 0.6) < 1.0 / ctx.w) & (np.abs(V - 0.64) < 1.2 / ctx.h)
            t[..., :3] = np.where(kh[..., None], rgb(COLD), t[..., :3])
            t[..., 4] = np.where(kh, 1.0, np.where(edge, 0.25, t[..., 4]))
        return t
    return Mat(fn, "dngd_far", directional=True)


def void_mat():
    """The outside of the corridor: the dark back of reality, faintly smoking."""
    def fn(ctx):
        ix, iy = tex.px(ctx)
        n = tex.fbm(ix / 2.0 + ctx.variant * 3, iy / 2.0, 77)
        t = tex.tile(ctx, INDIGO, 1, 0.12)
        t[..., :3] = tex.mix(rgb("#0e0d1c"), rgb("#2c2442"), (n ** 2)[..., None])
        st = tex._hash(ix, iy, 79) > 0.985
        t[..., :3] = np.where(st[..., None], rgb("#a990c8"), t[..., :3])
        t[..., 4] = np.where(st, 0.9, 0.1)
        return t
    return Mat(fn, "dngd_void")


def spill_mat():
    """Cold light spilling out of the open doorway across the ground (blend)."""
    def fn(ctx):
        U, V = ctx.U, ctx.V
        x = np.abs(U * 2 - 1)
        halfw = 0.6 + 0.4 * (1 - V)
        m = np.clip((halfw - x) / 0.14, 0, 1)
        t = tex.tile(ctx, "#d9d2ec", 1, 0.9)
        t[..., 3] = 0.0 if ctx.alt == "cracked" else m * (V ** 1.6) * 0.42
        return t
    return Mat(fn, "dngd_spill", mode="blend", directional=True)


KEYHOLE = [" ## ", "####", "####", " ## ", " ## ", "####", "####"]


# ---- Guest materials
def linen(base, key, ragged=False, stain=BURG):
    """Yellowed nightgown linen: weave, grime toward the hem, old burgundy stains, torn edges."""
    kb = rgb(base)

    def fn(ctx):
        ix, iy = tex.px(ctx)
        n = tex.fbm(ix / 3.0 + ctx.variant * 5, iy / 3.0, 7)
        col = kb * (0.84 + 0.22 * n)[..., None]
        col = col * (1 - 0.3 * ctx.V ** 1.5)[..., None]
        st = tex.fbm(ix / 4.0 + 11 + ctx.variant * 3, iy / 4.0, 13) > 0.66
        col = np.where(st[..., None], tex.mix(col, rgb(stain), 0.45), col)
        col = col * (1 - ((ix + iy) % 2) * 0.05)[..., None]
        t = tex.tile(ctx, base, 1, 0.05)
        t[..., :3] = np.clip(col, 0, 1)
        if ragged:
            jag = 0.62 + 0.3 * tex.vnoise(ix / 1.7 + ctx.variant * 9, ix * 0 + 3.3, 17) + 0.08 * tex._hash(ix, ix * 0, 19)
            holes = tex._hash(ix, iy, 5 + ctx.variant) < 0.03
            t[..., 3] = np.where((ctx.V > jag) | (holes & (ctx.V > 0.3)), 0.0, 1.0)
        return tex.grain(ctx, t, 0.04)
    return Mat(fn, f"dng_linen{base}{key}{ragged}")


def coat_mat(key, ragged=False, front=False):
    """Moth-eaten midnight coat: mauve pinstripe, threadbare patches; front=open over the nightgown."""
    def fn(ctx):
        ix, iy = tex.px(ctx)
        U, V = ctx.U, ctx.V
        n = tex.fbm(ix / 3.0 + ctx.variant * 7, iy / 3.0, 23)
        col = tex.mix(rgb("#212446"), rgb("#383b64"), n[..., None])
        col = np.where(((ix % 4) == 0)[..., None], tex.mix(col, rgb(MAUVE), 0.35), col)
        bare = tex.fbm(ix / 4.0 + 5, iy / 4.0 + ctx.variant, 29) > 0.67
        col = np.where(bare[..., None], tex.mix(col, rgb(MAUVE), 0.5), col)
        t = tex.tile(ctx, INDIGO, 1, 0.03)
        if front:
            c = np.abs(U - 0.5)
            col = np.where((c < 0.17)[..., None], rgb("#c8bea3") * (0.85 + 0.15 * n)[..., None], col)
            col = np.where(((c >= 0.17) & (c < 0.23))[..., None], rgb("#4b3557"), col)
            btn = (np.abs(U - 0.27) < 0.05) & ((iy % 5) == 2)
            col = np.where(btn[..., None], rgb(GILT), col)
        t[..., :3] = np.clip(col, 0, 1)
        if ragged:
            jag = 0.6 + 0.32 * tex.vnoise(ix / 1.5 + ctx.variant * 9, ix * 0 + 1.7, 27) + 0.08 * tex._hash(ix, ix * 0, 31)
            holes = tex._hash(ix, iy, 9 + ctx.variant) < 0.04
            t[..., 3] = np.where((V > jag) | (holes & (V > 0.25)), 0.0, 1.0)
        return tex.grain(ctx, t, 0.04)
    return Mat(fn, f"dng_coat{key}{ragged}{front}")


def head_mat(face=False):
    """Smooth aged-ivory skull-shell; the face side carries only a hairline seam and a dimple."""
    def fn(ctx):
        U, V = ctx.U, ctx.V
        ix, iy = tex.px(ctx)
        d = np.hypot((U - 0.5) * 2, (V - 0.42) * 1.5)
        col = tex.mix(rgb("#e0d9c7"), rgb("#9c9ba8"), (np.clip(d * 0.75, 0, 1) ** 1.7)[..., None])
        col = col * (1 - 0.12 * V)[..., None]
        glow = np.full(U.shape, 0.18)
        if face:
            cx = ctx.w // 2
            seam = (ix == cx) & (V > 0.5) & (V < 0.84)
            col = np.where(seam[..., None], col * 0.72, col)
            r = np.hypot((ix + 0.5 - ctx.w / 2) / 1.0, (iy + 0.5 - ctx.h * 0.42) / 1.0)
            ringm = (r > 1.0) & (r < 2.2)
            col = np.where(ringm[..., None], col * 0.7, col)
            core = r <= 1.0
            col = np.where(core[..., None], rgb("#b9b0a0"), col)
            glint = (ix == cx - 1) & (iy == int(ctx.h * 0.42) - 1)
            col = np.where(glint[..., None], rgb("#fffaf0"), col)
            glow = np.where(glint, 0.6, glow)
        t = tex.tile(ctx, "#000000")
        t[..., :3] = np.clip(col, 0, 1)
        t[..., 4] = glow
        return tex.grain(ctx, t, 0.015)
    return Mat(fn, f"dng_head{face}")


# ================================================================ door model
def build_door(m, P=""):
    def n(s):
        return P + s
    frame_p = painted(FRAME_P, WOOD_UNDER, "dngd_frame", peel=0.22, grime=0.3, seed=1)
    frame_dk = painted(FRAME_DK, "#1d1213", "dngd_frame2", peel=0.08, grime=0.2, seed=2)
    leaf_p = painted("#cbc1a9", "#6a4a3e", "dngd_leaf", peel=0.16, grime=0.4, seed=3)
    leaf_face = painted("#cbc1a9", "#6a4a3e", "dngd_leafface", peel=0.16, grime=0.4, seed=3, post=_panel_grooves)
    brass = tex.metal("#8f7744", "#d9c48c", "#4a3b1e", bands=2.0)
    bead = tex.metal(GILT, "#c9b37a", "#4a3b1e", bands=3.0, glow=0.1)
    keyglow = tex.bitmap_cut(KEYHOLE, COLD, glow=1.0, color2="#a99ad0", key="dngd_kh")
    frieze = tex.glyph_rows(list(glyphs.DREAM.values()), "#a08a52", glow=0.4, bg=FRAME_DK, fill=0.9, key="dngd_frieze")
    eye = tex.stamped(tex.speck("#3a2128", 0.06), glyphs.DREAM["eye"], "#d4c2f6", glow=0.85, key="dngd_eye")

    root = m.bone(n("root"), pivot=KEY_P)
    base = m.bone(n("frame_base"), root, pivot=(0, 0, 0))
    base.cube((-18, 0, -3), (36, 1.2, 6), frame_dk)                       # threshold
    for sx in (1, -1):
        base.box((sx * 20.8, 5, 0), (7.4, 10, 7.4), frame_p, variant=1)    # plinth blocks
        base.box((sx * 20.8, 10.4, 0), (7.8, 0.8, 7.8), frame_dk)
    for s, sx in (("r", 1), ("l", -1)):
        j = m.bone(n(f"jamb_{s}"), root, pivot=(sx * 20.5, 0, 0))
        j.box((sx * 20.5, 44.5, 0), (5, 68, 6), frame_p)
        j.box((sx * 18.4, 44.5, -3.1), (0.8, 68, 0.8), bead)               # gilt bead around the opening
        j.box((sx * 20.9, 44.5, -3.15), (1.6, 58, 0.5), frame_dk)          # fluting
        j.box((sx * 20.5, 74, 0), (6, 5, 6.6), frame_dk)                  # capital block
        j.box((sx * 20.5, 74, -3.35), (3.2, 3.2, 0.4), bead)              # rosette
        if sx > 0:
            for y in (10, 40, 70):                                          # hinge knuckles
                j.box((18.3, y, -1.3), (1.5, 5.6, 1.5), brass)
                j.box((18.3, y + 3.2, -1.3), (0.8, 0.8, 0.8), brass)
    lintel = m.bone(n("lintel"), root, pivot=(0, 80, 0))
    lintel.cube((-24.5, 78, -3.6), (49, 7, 7.2), frame_p, variant=2)
    lintel.plane("z", (0, 81.5, -3.7), 34, 5, frieze)
    lintel.cube((-26.5, 85, -4.6), (53, 2.4, 9.2), frame_dk)               # cornice
    lintel.cube((-25.5, 87.4, -4.0), (51, 1.4, 8), frame_p)
    lintel.locator("lintel_dust", (0, 79, -4))
    crest = m.bone(n("crest"), lintel, pivot=(0, 88.8, 0))
    for sx in (1, -1):                                                     # broken pediment
        crest.box((sx * 15.5, 91.2, 0), (17, 2.6, 6), frame_dk, rot=(0, 0, -sx * 15), pivot=(sx * 15.5, 91.2, 0))
        crest.box((sx * 25.5, 90.3, 0), (2.4, 3.0, 2.4), brass)
    crest.box((0, 93.5, -0.4), (6.4, 9, 3.2), frame_p, mats={"north": eye})   # sleeping-eye plaque
    crest.box((0, 98.6, -0.4), (3.2, 1.6, 2.4), frame_dk)
    crest.box((0, 100.2, -0.4), (1.6, 1.8, 1.6), brass)

    leaf = m.bone(n("leaf"), root, pivot=(18, 39, -1))
    leaf.cube((-18, LEAF_Y0, -1), (LEAF_W, LEAF_H, 2), leaf_p, mats={"north": leaf_face, "south": leaf_face})
    for u0, v0, u1, v1 in PANELS:                                          # raised panel fields
        x0, x1 = 18 - u1 * LEAF_W + 2.0, 18 - u0 * LEAF_W - 2.0
        y1, y0 = 78 - v0 * LEAF_H - 2.0, 78 - v1 * LEAF_H + 2.0
        leaf.cube((x0, y0, -1.7), (x1 - x0, y1 - y0, 0.7), leaf_p)
        leaf.cube((x0, y0, 1.0), (x1 - x0, y1 - y0, 0.5), leaf_p)
    leaf.box((-14, 38.6, -1.4), (2.6, 4.4, 0.8), brass)                    # handle rose
    leaf.box((-14, 32.6, -1.35), (2.4, 4.2, 0.7), brass)                   # keyhole escutcheon
    leaf.box((-14, 38.6, 1.4), (2.6, 4.4, 0.8), brass)
    kh = m.bone(n("keyhole"), leaf, pivot=(-14, 32.6, -1.8))
    kh.plane("z", (-14, 32.6, -1.76), 1.4, 2.6, keyglow)
    hd = m.bone(n("handle"), leaf, pivot=(-14, 38.6, -2.0))
    hd.box((-14, 38.6, -2.3), (1.4, 1.4, 1.6), brass)
    hd.box((-11.4, 38.6, -3.1), (5.6, 1.1, 1.1), brass)                    # lever
    hd.box((-8.7, 38.3, -3.1), (1.4, 1.7, 1.5), brass)
    hd.box((-11.4, 38.6, 2.4), (5.6, 1.1, 1.1), brass)                     # back lever

    # ---- the corridor (visible only while the door stands open)
    corr = m.bone(n("corr"), root, pivot=(0, VP, Z0))
    seg = seg_table()
    void = void_mat()
    brass_dk = tex.flat("#3d3326", key="dngd_chain")
    th = 0.6
    for i in range(N_SEG):
        a, b = seg[i], seg[i + 1]
        s = a["s"]
        fog = min(0.82, (1 - s) * 0.95)
        fog_n = min(0.82, (1 - b["s"]) * 0.95)
        sb = m.bone(n(f"corr_s{i}"), corr, pivot=(0, VP, a["z"]))
        z0, z1 = a["z"], b["z"]
        d, w, yf, yc = z1 - z0, a["w"], a["yf"], a["yc"]
        h = yc - yf
        wp = wallpaper(i, fog)
        sb.cube((-w - th, yf, z0), (th, h, d), void, mats={"east": wp})
        sb.cube((w, yf, z0), (th, h, d), void, mats={"west": wp})
        sb.cube((-w - th, yf - th, z0), (2 * w + 2 * th, th, d), void, mats={"up": floor_mat(i, fog)})
        sb.cube((-w - th, yc, z0), (2 * w + 2 * th, th, d), void, mats={"down": ceil_mat(i, fog)})
        # nested moulded frame at the mouth of the next segment
        wo = w + th + 0.8 * s + 0.4
        yo0, yo1 = yf - th - 0.8 * s - 0.4, yc + th + 0.8 * s + 0.4
        W, H = 2 * wo, yo1 - yo0
        hole = ((wo - b["w"]) / W, (wo + b["w"]) / W, (yo1 - b["yc"]) / H, (yo1 - b["yf"]) / H)
        sb.plane("z", (0, (yo0 + yo1) / 2, z1 - 0.03), W, H, ring_mat(i, hole, W, H, b["s"], fog_n))
        # sconces and pendants
        lamp = lamp_mat(round(fog, 2))
        ls = max(0.3, s)
        ly, lz = yf + h * 0.62, z0 + d * 0.5
        for sx in (1, -1):
            sb.box((sx * (w - 0.45 * ls), ly, lz), (0.9 * ls, 1.6 * ls, 0.9 * ls), lamp)
            sb.box((sx * (w - 0.3 * ls), ly - 1.1 * ls, lz), (0.6 * ls, 0.5 * ls, 0.6 * ls), brass_dk)
        if i % 2 == 1:
            sb.box((0, yc - 1.4 * s, lz), (1.8 * s, 1.6 * s, 1.8 * s), lamp)
            sb.box((0, yc - 0.3 * s, lz), (0.3 * s, 0.6 * s, 0.3 * s), brass_dk)
    end = seg[N_SEG]
    far = m.bone(n("corr_far"), corr, pivot=(0, VP, end["z"]))
    far.plane("z", (0, (end["yf"] + end["yc"]) / 2, end["z"] - 0.05), 2 * end["w"] + 1.2,
              end["yc"] - end["yf"] + 1.2, far_mat())
    spill = m.bone(n("corr_spill"), root, pivot=(0, 0.15, -1))
    spill.plane("y", (0, 0.15, -22.5), 60, 43, spill_mat(), faces=("up",))
    return m


# ================================================================ guest model
ARM_X, ARM_Y, ELBOW_Y, WRIST_Y = 8.0, 77.0, 52.0, 28.0
A_UP, B_LO, PALM = ARM_Y - ELBOW_Y, ELBOW_Y - WRIST_Y + 3.5, 3.5
L_WRIST = ARM_Y - WRIST_Y
SKIRT = [k * 45 + 22.5 for k in range(8)]
TAILS = [150, 180, 210]


def build_guest(m, P=""):
    def n(s):
        return P + s
    skin = tex.mottled("#bfb8a8", "#8f8c88", scale=2.5, glow=0.07, edge_dark=0.08)
    skin_dk = tex.mottled("#8d8994", "#5f5b68", scale=2.0, glow=0.05, edge_dark=0.1)
    nail = tex.flat("#2c2632", key="dng_nail")
    gown = linen("#cdc3a8", "gown")
    gown_rag = linen("#c4b89b", "gownrag", ragged=True)
    coat = coat_mat("c")
    coat_front = coat_mat("cf", front=True)
    coat_rag = coat_mat("cr", ragged=True)
    head = head_mat()
    face = head_mat(face=True)

    root = m.bone(n("root"))
    body = m.bone(n("body"), root, pivot=(0, 44, 0))
    body.box((0, 44.5, 0), (10, 6, 6.2), gown)
    for s, sx in (("r", 1), ("l", -1)):
        thb = m.bone(n(f"thigh_{s}"), body, pivot=(sx * 3, 43, 0))
        thb.box((sx * 3, 33, 0), (2.6, 21, 2.6), skin)
        thb.box((sx * 3, 22.6, -0.2), (3.2, 2.8, 3.0), skin_dk)
        shb = m.bone(n(f"shin_{s}"), thb, pivot=(sx * 3, 22.5, 0))
        shb.box((sx * 3, 12.5, 0), (2.1, 19, 2.1), skin, variant=1)
        shb.box((sx * 3, 3.6, 0.2), (2.6, 2.4, 2.6), skin_dk)
        ft = m.bone(n(f"foot_{s}"), shb, pivot=(sx * 3, 2.4, 0))
        ft.cube((sx * 3 - 1.3, 0, -6.4), (2.6, 1.6, 7.9), skin, variant=2)
        for k in range(3):
            ft.box((sx * 3 + (k - 1) * 0.85, 0.5, -7.6), (0.7, 1.0, 2.6), skin_dk)

    s1 = m.bone(n("spine1"), body, pivot=(0, 47, 0))
    s1.box((0, 52, 0), (8.4, 10, 5.4), gown, variant=1)
    s2 = m.bone(n("spine2"), s1, pivot=(0, 57, 0))
    s2.box((0, 62.5, 0.1), (9.4, 11, 6.0), coat, mats={"north": coat_front})
    s3 = m.bone(n("spine3"), s2, pivot=(0, 68, 0))
    s3.box((0, 73.3, 0.3), (11.4, 11, 6.6), coat, mats={"north": coat_front}, variant=1)
    for sx in (1, -1):                                                     # sloped, too-narrow shoulders
        s3.box((sx * 4.6, 78.6, 0.3), (6.4, 2.6, 6.4), coat, rot=(0, 0, -sx * 14), pivot=(sx * 4.6, 78.6, 0.3))
    for bn, ys in ((s1, (50.5, 54.5)), (s2, (59.5, 63.5, 67)), (s3, (71, 75))):   # vertebrae through the cloth
        for y in ys:
            bn.box((0, y, 3.9 if bn is s3 else 3.2), (1.8, 2.0, 1.6), skin_dk)
    for sx in (1, -1):                                                     # torn standing collar
        s3.plane("z", (sx * 3.2, 81.5, 1.4), 4.4, 6, coat_rag, rot=(-14, sx * 28, 0), pivot=(sx * 3.2, 79, 1.4))

    n1 = m.bone(n("neck1"), s3, pivot=(0, 79.5, 0.4))
    n1.box((0, 83, 0.5), (2.8, 7, 2.8), skin)
    n2 = m.bone(n("neck2"), n1, pivot=(0, 86.5, 0.4))
    n2.box((0, 89.6, 0.4), (2.4, 6.6, 2.4), skin, variant=1)
    hb = m.bone(n("head"), n2, pivot=(0, 92.5, 0.4))
    hb.box((0, 100, 0), (7, 15, 8), head, mats={"north": face})
    hb.box((0, 99.5, 0.4), (8.4, 10, 6.6), head, variant=1)
    hb.box((0, 100.2, 0.4), (5.2, 17.4, 6.0), head, variant=2)
    hb.box((0, 101.2, 0.8), (6.2, 12, 9.0), head, variant=3)
    hb.locator("mouth", (0, 97, -5))

    for s, sx in (("r", 1), ("l", -1)):
        cl = m.bone(n(f"clav_{s}"), s3, pivot=(sx * 4, 78.5, 0))
        cl.box((sx * 7.4, 77.6, 0.3), (4.4, 3.6, 4.8), coat, variant=2)
        a1 = m.bone(n(f"arm_{s}_1"), cl, pivot=(sx * ARM_X, ARM_Y, 0))
        a1.box((sx * ARM_X, 70.8, 0), (3.8, 12.6, 3.8), coat, variant=1)
        a2 = m.bone(n(f"arm_{s}_2"), a1, pivot=(sx * ARM_X, 64.5, 0))
        a2.box((sx * ARM_X, 59, 0), (3.3, 11, 3.3), coat, variant=2)
        a2.box((sx * ARM_X, 55, 0), (2.4, 5, 2.4), skin)
        a2.plane("z", (sx * ARM_X, 51.8, -1.7), 3.3, 4.6, coat_rag)
        a2.plane("x", (sx * (ARM_X + 1.7), 51.6, 0), 3.3, 5.0, coat_rag, variant=1)
        a3 = m.bone(n(f"arm_{s}_3"), a2, pivot=(sx * ARM_X, ELBOW_Y, 0))
        a3.box((sx * ARM_X, ELBOW_Y, 0.3), (3.0, 3.0, 3.0), skin_dk)
        a3.box((sx * ARM_X, 46, 0), (2.2, 12, 2.2), skin)
        a4 = m.bone(n(f"arm_{s}_4"), a3, pivot=(sx * ARM_X, 40, 0))
        a4.box((sx * ARM_X, 34, 0), (2.0, 12, 2.0), skin, variant=1)
        a4.box((sx * ARM_X, 28.6, 0), (2.6, 2.0, 2.4), skin_dk)
        hd = m.bone(n(f"hand_{s}"), a4, pivot=(sx * ARM_X, WRIST_Y, 0))
        hd.box((sx * ARM_X, 24.5, 0), (1.4, 7, 4.4), skin, variant=2)
        for k in range(4):
            zk = -1.65 + k * 1.1
            f1 = m.bone(n(f"fing_{s}{k}_1"), hd, pivot=(sx * ARM_X, 21, zk))
            f1.box((sx * ARM_X, 21, zk), (1.3, 1.2, 1.0), skin_dk)
            f1.box((sx * ARM_X, 17.3, zk), (1.0, 7.4, 0.9), skin)
            f2 = m.bone(n(f"fing_{s}{k}_2"), f1, pivot=(sx * ARM_X, 13.6, zk))
            f2.box((sx * ARM_X, 10.2, zk), (0.85, 6.8, 0.8), skin, variant=1)
            f2.box((sx * ARM_X, 6.5, zk), (0.9, 1.2, 0.85), nail)
        th1 = m.bone(n(f"fing_{s}4_1"), hd, pivot=(sx * ARM_X, 25, -2.3), rot=(28, 0, 0))
        th1.box((sx * ARM_X, 21.5, -2.3), (1.0, 7, 1.0), skin)
        th1.box((sx * ARM_X, 17.6, -2.3), (1.0, 1.0, 0.9), nail)

    # nightgown skirt: eight overlapping torn panels in two-bone chains (they lag and sway)
    for k, a in enumerate(SKIRT):
        ra = math.radians(a)
        px, pz = math.sin(ra) * 4.6, -math.cos(ra) * 4.6
        u = m.bone(n(f"skirt{k}_1"), body, pivot=(px, 45, pz), rot=(5, -a, 0))
        u.plane("z", (px, 34.5, pz), 7.4, 21, gown, variant=k % 3)
        lo = m.bone(n(f"skirt{k}_2"), u, pivot=(px, 24, pz), rot=(4, 0, 0))
        lo.plane("z", (px, 13.5, pz), 7.2, 21, gown_rag, variant=k % 3)
    # coat tails at the back
    for k, a in enumerate(TAILS):
        ra = math.radians(a)
        px, pz = math.sin(ra) * 3.6, -math.cos(ra) * 3.6
        par = body
        for j, (y0, L) in enumerate(((57, 15), (42, 15), (27, 14))):
            tb = m.bone(n(f"tail{k}_{j + 1}"), par, pivot=(px, y0, pz), rot=((7, -a, 0) if j == 0 else (3, 0, 0)))
            tb.plane("z", (px, y0 - L / 2, pz), 6.2 - j * 0.6, L, coat_rag if j == 2 else coat, variant=(k + j) % 3)
            par = tb
    return m


# ================================================================ pose helpers + IK
def _v(key, val):
    if isinstance(val, (int, float)):
        return (val, val, val)
    return tuple(val)


def _num(x):
    return x.fn(0.0) if isinstance(x, Expr) else float(x)


def bm_pose(pd, prefix=""):
    """pose dict {'bone': rot, 'bone@p': pos, 'bone@s': scale} -> kit bone_matrices pose."""
    out = {}
    for k, v in pd.items():
        bone, _, ch = k.partition("@")
        r, p, s = out.get(prefix + bone, ((0, 0, 0), (0, 0, 0), (1, 1, 1)))
        v = tuple(_num(x) for x in _v(k, v))
        if ch == "p":
            p = v
        elif ch == "s":
            s = v
        else:
            r = v
        out[prefix + bone] = (r, p, s)
    return out


def keyed(anim, frames, smooth=True):
    """Write keyframes for every channel that appears in any frame (absent = neutral)."""
    keys = set()
    for f in frames.values():
        keys |= set(f)
    for k in sorted(keys):
        bone, _, ch = k.partition("@")
        dflt = (1, 1, 1) if ch == "s" else (0, 0, 0)
        kd = {t: _v(k, f.get(k, dflt)) for t, f in sorted(frames.items())}
        {"": anim.rot, "p": anim.pos, "s": anim.scl}[ch](bone, kd, smooth)
    return anim


def lerp_pose(a, b, f):
    out = {}
    for k in set(a) | set(b):
        dflt = (1, 1, 1) if k.endswith("@s") else (0, 0, 0)
        va, vb = _v(k, a.get(k, dflt)), _v(k, b.get(k, dflt))
        out[k] = tuple(va[i] + (vb[i] - va[i]) * f for i in range(3))
    return out


def smooth(p):
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


def grounded(m, pd, floor_y):
    """Set root@p.y so the lowest foot point rests on floor_y (root scale included)."""
    q = dict(pd)
    rp = _v("root@p", q.get("root@p", (0, 0, 0)))
    q["root@p"] = (rp[0], 0.0, rp[2])
    mats = m.bone_matrices(bm_pose(q))
    lo = min((mats[f"foot_{s}"] @ np.array([sx * 3, 0.0, z, 1.0]))[1]
             for s, sx in (("r", 1), ("l", -1)) for z in (-7.6, 1.5))
    q["root@p"] = (rp[0], floor_y - lo, rp[2])
    return q


def solve_arm(m, pd, side, goal, stretch=True):
    """Aim one arm so the palm centre lands on goal (bb space).  Bends the elbow when the goal is
    close; when it is out of reach the arm really lengthens (arm_1 y-scale, hand counter-scaled)."""
    sx = 1 if side == "r" else -1
    mats = m.bone_matrices(bm_pose(pd))
    Mp = mats[f"clav_{side}"]
    sh = (Mp @ np.array([sx * ARM_X, ARM_Y, 0.0, 1.0]))[:3]
    D = np.array(goal, dtype=float) - sh
    dist = float(np.linalg.norm(D))
    dl = np.linalg.solve(Mp[:3, :3], D)
    dl /= np.linalg.norm(dl)
    a_dir = math.degrees(math.acos(max(-1.0, min(1.0, -dl[1]))))
    b = math.degrees(math.atan2(-dl[0], -dl[2]))
    out = {f"arm_{side}_2": (0, 0, 0), f"arm_{side}_4": (0, 0, 0), f"hand_{side}": (0, 0, 0)}
    if dist >= (A_UP + B_LO) * 0.995:
        F = max(1.0, (dist - PALM) / L_WRIST) if stretch else 1.0
        out.update({f"arm_{side}_1": (a_dir, b, 0), f"arm_{side}_1@s": (1, F, 1), f"arm_{side}_3": (0, 0, 0),
                    f"hand_{side}@s": (1, 1 / F, 1)})
        return out
    ce = (dist ** 2 - A_UP ** 2 - B_LO ** 2) / (2 * A_UP * B_LO)
    e = math.acos(max(-1.0, min(1.0, ce)))
    phi = math.degrees(math.atan2(B_LO * math.sin(e), A_UP + B_LO * math.cos(e)))
    out.update({f"arm_{side}_1": (a_dir - phi, b, 0), f"arm_{side}_1@s": (1, 1, 1),
                f"arm_{side}_3": (math.degrees(e), 0, 0), f"hand_{side}@s": (1, 1, 1)})
    return out


def palm_pos(m, pd, side):
    sx = 1 if side == "r" else -1
    return (m.bone_matrices(bm_pose(pd))[f"hand_{side}"] @ np.array([sx * ARM_X, 24.5, 0, 1.0]))[:3]


def fing(side, c1, c2, spread=0.0, thumb=20.0):
    sg = 1 if side == "r" else -1
    d = {}
    for k in range(4):
        d[f"fing_{side}{k}_1"] = (-(k - 1.5) * spread, 0, -sg * c1)
        d[f"fing_{side}{k}_2"] = (0, 0, -sg * c2)
    d[f"fing_{side}4_1"] = (-thumb * 0.3, 0, -sg * thumb)
    return d


def hands(c1, c2, spread=0.0, thumb=20.0, left=None):
    d = fing("r", c1, c2, spread, thumb)
    d.update(fing("l", *(left or (c1, c2, spread, thumb))))
    return d


REL, SPLAY, CLOSED, GRIP = (14, 16, 0, 15), (-24, -8, 8, -20), (74, 70, 0, 55), (58, 64, 0, 45)
ARMS_HANG = {"arm_r_1": (4, 0, 6), "arm_l_1": (4, 0, -6), "arm_r_3": (10, 0, 0), "arm_l_3": (10, 0, 0),
             "arm_r_1@s": 1, "arm_l_1@s": 1, "hand_r@s": 1, "hand_l@s": 1, "arm_r_2": (0, 0, 0), "arm_l_2": (0, 0, 0),
             "arm_r_4": (0, 0, 0), "arm_l_4": (0, 0, 0), "hand_r": (0, 0, 0), "hand_l": (0, 0, 0)}
ARMS_BACK = {**ARMS_HANG, "arm_r_1": (-28, 0, 10), "arm_l_1": (-28, 0, -10), "arm_r_3": (70, 0, 0), "arm_l_3": (70, 0, 0)}


def legs(th_r, sh_r, th_l=None, sh_l=None):
    th_l = th_r if th_l is None else th_l
    sh_l = sh_r if sh_l is None else sh_l
    return {"thigh_r": (th_r, 0, 0), "shin_r": (sh_r, 0, 0), "foot_r": (-(th_r + sh_r), 0, 0),
            "thigh_l": (th_l, 0, 0), "shin_l": (sh_l, 0, 0), "foot_l": (-(th_l + sh_l), 0, 0)}


def skirt_flare(front, side=0.0):
    """Front skirt panels ride out over bent knees."""
    d = {}
    for k, a in enumerate(SKIRT):
        c = math.cos(math.radians(a))
        if c > 0.3:
            d[f"skirt{k}_1"] = (front * c, 0, 0)
            d[f"skirt{k}_2"] = (-front * 0.4 * c, 0, 0)
    return d


def spine(body, s1, s2, s3, n1, n2, head, roll=0.0):
    return {"body": (body, 0, roll * 0.5), "spine1": (s1, 0, roll), "spine2": (s2, 0, roll), "spine3": (s3, 0, roll * 0.8),
            "neck1": (n1, 0, roll * 0.6), "neck2": (n2, 0, roll * 0.6), "head": head}


LURK = {**spine(-6, -12, -14, -10, 10, 8, (6, 0, -10)), **legs(34, -58), **skirt_flare(26)}
WALK_A = {**spine(-7, -13, -14, -10, 12, 8, (6, 0, -16), roll=-3), **legs(46, -50, 14, -52), **skirt_flare(32)}
WALK_B = {**spine(-7, -13, -14, -10, 12, 8, (4, 0, -4), roll=3), **legs(14, -52, 46, -50), **skirt_flare(32)}
CROUCH = {**spine(-8, -16, -18, -12, 14, 10, (8, 0, -14)), **legs(40, -66), **skirt_flare(30)}
PEEK = {**spine(-8, -16, -18, -14, 12, 12, (6, 18, 44), roll=9), **legs(30, -48), **skirt_flare(24)}
STOOP = {**spine(-10, -19, -21, -15, 20, 14, (8, 0, 18)), **legs(16, -26), **skirt_flare(12)}
REACH = {**spine(-12, -21, -23, -17, 24, 16, (12, 0, 28)), **legs(12, -22), **skirt_flare(10)}
LEANB = {**spine(4, -4, -5, -3, 10, 8, (-2, 0, -16)), **legs(30, -48), **skirt_flare(26)}


def gpose(body, root=(0, 0, GUEST_Z), s=1.0, arms=None, fingers=None, floor=0.0, m=None):
    pd = {"root@p": root, "root@s": s, "clav_r": (0, 0, 0), "clav_l": (0, 0, 0)}
    pd.update(body)
    pd.update(arms or ARMS_HANG)
    pd.update(fingers or hands(*REL))
    return grounded(m, pd, floor)


def with_arms(m, pd, goals, stretch=True, fingers=None):
    q = dict(pd)
    for side, g in goals.items():
        if g is not None:
            q.update(solve_arm(m, q, side, g, stretch))
    if fingers:
        q.update(fingers)
    return q


def aim_only(m, pd, goals):
    """Point both arms at their goals at natural length (the moment before they lengthen)."""
    q = dict(pd)
    for side, g in goals.items():
        sol = solve_arm(m, q, side, g, stretch=True)
        sol[f"arm_{side}_1@s"] = (1, 1, 1)
        sol[f"hand_{side}@s"] = (1, 1, 1)
        q.update(sol)
    return q


def tremble(pd, amp=1.4):
    q = dict(pd)
    for i, side in enumerate(("r", "l")):
        r = _v("x", q[f"arm_{side}_1"])
        q[f"arm_{side}_1"] = (r[0], r[1], S(amp, 0.13, i * 0.37, base=r[2]))
    return q


# ================================================================ animations
def door_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    idle = Anim("door_idle", loop=True)
    idle.scl("keyhole", LIFE(0.14, 1.3, base=1.0))
    idle.scl("corr_far", (LIFE(0.09, 3.6, base=1.0), LIFE(0.09, 3.6, base=1.0), 1.0))
    idle.pos("corr_far", (0, 0, LIFE(1.4, 5.3)))
    idle.scl(f"corr_s{N_SEG - 1}", (1.0, 1.0, LIFE(0.25, 5.3, base=1.0)))
    idle.scl(f"corr_s{N_SEG - 2}", (1.0, 1.0, LIFE(0.12, 5.3, -0.1, base=1.0)))
    A.append(idle)

    man = Anim("manifest", length=DOOR_LEN["manifest"], loop="hold")   # frame assembles, then the door unfolds
    man.scl("frame_base", {0: (1, 0, 1), 0.2: (1, 1.2, 1), 0.3: (1, 1, 1)})
    man.scl("jamb_r", {0: (1, 0, 1), 0.1: (1, 0, 1), 0.45: (1, 1.08, 1), 0.55: (1, 1, 1)})
    man.scl("jamb_l", {0: (1, 0, 1), 0.16: (1, 0, 1), 0.5: (1, 1.08, 1), 0.6: (1, 1, 1)})
    man.pos("jamb_r", {0: (5, 0, 0), 0.45: (0, 0, 0)})
    man.pos("jamb_l", {0: (-5, 0, 0), 0.5: (0, 0, 0)})
    man.pos("lintel", {0: (0, 34, 0), 0.4: (0, 30, 0), 0.62: (0, -1.6, 0), 0.72: (0, 0, 0)})
    man.scl("lintel", {0: 0.0, 0.38: 0.2, 0.6: 1.0})
    man.rot("crest", {0: (0, 0, 0), 0.62: (0, 0, -7), 0.78: (0, 0, 4), 0.92: (0, 0, 0)})
    man.scl("leaf", {0: (0, 1, 1), 0.62: (0, 1, 1), 1.0: (1.04, 1, 1), 1.2: (1, 1, 1)})
    man.rot("root", {0: (0, -10, 0), 0.6: (0, 3, 0), 1.0: (0, 0, 0)})
    A.append(man)

    closed = Anim("closed", loop=True)
    closed.rot("leaf", (0, LIFE(0.5, 2.3, base=-0.5), 0))
    A.append(closed)

    hdl = Anim("handle", length=DOOR_LEN["handle"], loop="hold")     # the dread beat: slow turn, rattle, latch
    hdl.rot("handle", {0: (0, 0, 0), 0.15: (0, 0, -4), 0.22: (0, 0, 2), 0.32: (0, 0, -7), 0.38: (0, 0, -3),
                       0.62: (0, 0, -18), 0.76: (0, 0, -15), 1.02: (0, 0, -38), 1.1: (0, 0, -43), 1.4: (0, 0, -43)})
    hdl.rot("leaf", {0: (0, 0, 0), 0.18: (0, -1.3, 0), 0.24: (0, 0, 0), 0.34: (0, -1.6, 0), 0.42: (0, 0, 0),
                     1.1: (0, 0, 0), 1.16: (0, -2.8, 0), 1.4: (0, -1.6, 0)})
    hdl.scl("keyhole", {0: 1.0, 1.0: 1.0, 1.12: 1.8, 1.4: 1.3})
    hdl.particle(0.22, "dust", "lintel_dust")
    hdl.particle(1.12, "dust", "lintel_dust")
    A.append(hdl)

    op = Anim("open", length=DOOR_LEN["open"], loop="hold")          # a crack ... a hesitation ... it swings wide
    op.rot("leaf", {0: (0, -1.6, 0), 0.25: (0, -11, 0), 0.45: (0, -13, 0), 0.9: (0, -82, 0), 1.2: (0, -105, 0)})
    op.rot("handle", {0: (0, 0, -43), 0.25: (0, 0, -43), 0.38: (0, 0, 5), 0.5: (0, 0, 0)})
    op.scl("corr", {0: (1, 1, 0.25), 0.3: (1, 1, 0.35), 1.2: (1, 1, 1)})
    op.scl("corr_spill", {0: (0.3, 1, 0.15), 0.3: (0.4, 1, 0.3), 1.2: (1, 1, 1)})
    A.append(op)

    held = Anim("held", loop=True)
    held.rot("leaf", (0, LIFE(1.4, 3.3, base=-105), 0))
    held.scl("corr_spill", (1.0, 1.0, LIFE(0.05, 0.9, base=1.0)))
    A.append(held)

    sl = Anim("slam", length=DOOR_LEN["slam"], loop="hold")           # violent: linear keys, bounce, shake
    sl.rot("leaf", {0: (0, -105, 0), 0.15: (0, 0, 0), 0.21: (0, -6, 0), 0.28: (0, 0, 0), 0.35: (0, -1.5, 0),
                    0.42: (0, 0, 0)}, smooth=False)
    sl.pos("root", {0: (0, 0, 0), 0.15: (0, 0, 0), 0.18: (1.3, 0, -1.1), 0.22: (-1.1, 0.5, 0.7), 0.27: (0.7, 0, -0.4),
                    0.33: (-0.3, 0, 0.2), 0.42: (0, 0, 0)}, smooth=False)
    sl.pos("lintel", {0: (0, 0, 0), 0.15: (0, 0, 0), 0.19: (0, 1.8, 0), 0.26: (0, 0, 0)})
    sl.rot("crest", {0: (0, 0, 0), 0.15: (0, 0, 0), 0.2: (0, 0, 10), 0.3: (0, 0, -6), 0.4: (0, 0, 2), 0.5: (0, 0, 0)})
    sl.rot("handle", {0: (0, 0, 0), 0.15: (0, 0, 0), 0.2: (0, 0, -28), 0.32: (0, 0, 9), 0.45: (0, 0, 0)})
    sl.scl("corr", {0: (1, 1, 1), 0.14: (1, 1, 1), 0.2: (1, 1, 0.02), 0.6: (1, 1, 0.02)})
    sl.scl("corr_spill", {0: (1, 1, 1), 0.15: (0.4, 1, 0.02), 0.6: (0, 1, 0)})
    sl.scl("keyhole", {0: 1.0, 0.15: 1.0, 0.2: 2.6, 0.6: 1.2})
    sl.particle(0.16, "dust", "lintel_dust")
    A.append(sl)

    van = Anim("vanish", length=DOOR_LEN["vanish"], loop="hold")      # everything folds flat into the keyhole
    van.scl("root", {0: (1, 1, 1), 0.12: (1.04, 1.04, 1.04), 0.32: (1.02, 1.0, 0.04), 0.6: (0.03, 1.0, 0.04),
                     0.85: (0.03, 0.03, 0.03), 1.0: (0, 0, 0)})
    van.rot("root", {0: (0, 0, 0), 0.6: (0, 0, 0), 1.0: (0, 0, 160)})
    van.scl("keyhole", {0: 1.0, 0.6: 1.6, 0.85: 4.0, 1.0: 4.0})
    A.append(van)
    return A


def guest_anims(m):
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    # ---- always: breathing, a wrong little twitch, cloth that lags, fingers that never stop moving
    idle = Anim("guest_idle", loop=True)
    twitch = M("7*math.pow(math.max(0,math.sin(q.life_time*97)),24)",
               lambda t: 7 * max(0.0, math.sin(math.radians(t * 97))) ** 24)
    idle.rot("spine2", (LIFE(1.4, 4.1), 0, 0))
    idle.rot("spine3", (LIFE(1.1, 4.1, 0.08), 0, LIFE(0.8, 6.3)))
    idle.rot("neck2", (0, LIFE(3.0, 7.7), 0))
    idle.rot("head", (LIFE(1.5, 5.3), 0, twitch))
    idle.rot("clav_r", (0, 0, LIFE(1.6, 4.1, 0.1)))
    idle.rot("clav_l", (0, 0, LIFE(-1.6, 4.1, 0.1)))
    for k in range(len(SKIRT)):
        idle.rot(f"skirt{k}_1", (LIFE(2.5, 2.6, k * 0.13), 0, LIFE(1.4, 3.1, k * 0.21)))
        idle.rot(f"skirt{k}_2", (LIFE(4.5, 2.6, k * 0.13 - 0.2), 0, LIFE(2.0, 3.1, k * 0.21 - 0.15)))
    for k in range(len(TAILS)):
        for j in range(3):
            idle.rot(f"tail{k}_{j + 1}", (LIFE(3 + j * 2.5, 3.4, k * 0.17 - j * 0.16), 0, LIFE(2 + j, 4.3, k * 0.29 - j * 0.1)))
    for s, sg in (("r", 1), ("l", -1)):
        for k in range(4):
            idle.rot(f"fing_{s}{k}_2", (0, 0, LIFE(-sg * 4.5, 1.7 + k * 0.23, k * 0.3 + (0.5 if s == "l" else 0))))
    A.append(idle)

    # ---- emerge: tiny at the far end of the corridor, suddenly close; hand on the frame; head leans out
    em = Anim("emerge", length=GUEST_LEN["emerge"], loop="hold")
    frames = {}
    for t, s, body in ((0.0, 0.12, WALK_A), (0.3, 0.16, WALK_B), (0.56, 0.24, WALK_A), (0.76, 0.38, WALK_B),
                       (0.93, 0.62, WALK_A), (1.1, 1.0, CROUCH)):
        z = max(zs(s), GUEST_Z + 1.0)
        frames[t] = gpose(body, root=(0, 0, z), s=s, floor=VP * (1 - s) if s < 1 else 0.0, m=m)
    crouch = frames[1.1]
    lift = with_arms(m, crouch, {"l": (G_FRAME[0] + 4, G_FRAME[1] - 10, G_FRAME[2] + 6)}, stretch=False,
                     fingers=hands(*REL, left=SPLAY))
    frames[1.28] = lift
    grip_body = gpose({**CROUCH, "head": (8, 0, -6)}, root=(0, 0, GUEST_Z + 1.0), m=m)
    frames[1.45] = with_arms(m, grip_body, {"l": G_FRAME}, stretch=False, fingers=hands(*REL, left=GRIP))
    frames[1.62] = with_arms(m, gpose({**CROUCH, "head": (8, 0, -10)}, root=(0, 0, GUEST_Z + 1.0), m=m),
                             {"l": G_FRAME}, stretch=False, fingers=hands(*REL, left=GRIP))
    peek = gpose(PEEK, root=(0, 0, GUEST_Z), m=m)
    frames[1.95] = with_arms(m, peek, {"l": G_FRAME}, stretch=False, fingers=hands(*REL, left=GRIP))
    frames[2.15] = with_arms(m, gpose({**PEEK, "head": (6, 10, 40)}, root=(0, 0, GUEST_Z), m=m), {"l": G_FRAME},
                             stretch=False, fingers=hands(*REL, left=GRIP))
    stoop = gpose(STOOP, root=(0, 0, GUEST_Z), m=m)
    sh_r = (m.bone_matrices(bm_pose(stoop))["clav_r"] @ np.array([ARM_X, ARM_Y, 0, 1.0]))[:3]
    emerged = with_arms(m, stoop, {"l": G_FRAME, "r": (sh_r[0] + 1, 9.0, sh_r[2] - 10)}, stretch=False,
                        fingers=hands(*REL, left=GRIP))
    frames[2.6] = emerged
    keyed(em, frames)
    em.particle(2.1, "breath", "mouth")
    A.append(em)

    # ---- reach: lets go of the frame, raises both arms, then the arms keep growing
    rc = Anim("reach", length=GUEST_LEN["reach"], loop="hold")
    goals_open = {"r": (HAND_X + 2.6, HAND_Y + 1, GRAB_Z), "l": (-HAND_X - 2.6, HAND_Y + 1, GRAB_Z)}
    st_b = gpose({**STOOP, "head": (10, 0, 24)}, root=(0, 0, GUEST_Z), m=m)
    reach_body = gpose(REACH, root=(0, 0, GUEST_Z), m=m)
    reach_end = with_arms(m, reach_body, goals_open, fingers=hands(*SPLAY))
    keyed(rc, {0: emerged,
               0.25: with_arms(m, st_b, {"l": (-12, 44, -16), "r": (11, 24, -24)}, stretch=False,
                               fingers=hands(*REL, left=SPLAY)),
               0.6: aim_only(m, lerp_pose(st_b, reach_body, 0.6), goals_open) | hands(-8, 0, 4, 0),
               1.05: reach_end,
               1.2: with_arms(m, gpose({**REACH, "head": (12, 0, 32)}, root=(0, 0, GUEST_Z), m=m), goals_open,
                              fingers=hands(-26, -10, 9, -22))})
    rc.particle(0.7, "breath", "mouth")
    A.append(rc)

    # ---- grab: fingers snap shut, a jolt, the grip tightens
    gb = Anim("grab", length=GUEST_LEN["grab"], loop="hold")
    goals = {"r": (HAND_X, HAND_Y, GRAB_Z), "l": (-HAND_X, HAND_Y, GRAB_Z)}
    jolt = gpose({**REACH, "spine3": (-21, 0, 0), "head": (14, 0, 38)}, root=(0, 0, GUEST_Z), m=m)
    grabbed = with_arms(m, reach_body, goals, fingers=hands(*CLOSED))
    keyed(gb, {0: reach_end, 0.1: with_arms(m, jolt, goals, fingers=hands(*CLOSED)), 0.5: grabbed})
    A.append(gb)

    # ---- miss: closes on nothing, tilts its head, opens again
    ms = Anim("miss", length=GUEST_LEN["miss"], loop="hold")
    keyed(ms, {0: reach_end,
               0.3: with_arms(m, reach_body, {"r": (1.0, HAND_Y, GRAB_Z - 1), "l": (-1.0, HAND_Y, GRAB_Z - 1)},
                              fingers=hands(*CLOSED)),
               0.62: with_arms(m, gpose({**REACH, "head": (6, 12, -22)}, root=(0, 0, GUEST_Z), m=m),
                               {"r": (1.5, HAND_Y, GRAB_Z), "l": (-1.5, HAND_Y, GRAB_Z)}, fingers=hands(*CLOSED)),
               0.9: with_arms(m, gpose({**REACH, "head": (8, 0, -12)}, root=(0, 0, GUEST_Z), m=m), goals,
                              fingers=hands(*CLOSED))})
    ms.particle(0.45, "breath", "mouth")
    A.append(ms)

    # ---- pull: retracts while leaning back, knees bent, arms trembling with the strain
    pl = Anim("pull", length=GUEST_LEN["pull"], loop="hold")
    frames = {}
    for p in (0.0, 0.25, 0.5, 0.75, 1.0):
        f = smooth(p)
        body = gpose(lerp_pose(REACH, LEANB, f), root=(0, 0, GUEST_Z + 2.5 * p), m=m)
        z = GRAB_Z + (PULL_Z - GRAB_Z) * f
        frames[p * GUEST_LEN["pull"]] = tremble(with_arms(m, body, {"r": (HAND_X, HAND_Y, z), "l": (-HAND_X, HAND_Y, z)},
                                                          fingers=hands(*CLOSED)))
    pull_end = frames[GUEST_LEN["pull"]]
    keyed(pl, frames)
    A.append(pl)

    # ---- withdraw: lets go, arms whip back, and it recedes down the corridor until it is gone
    wd = Anim("withdraw", length=GUEST_LEN["withdraw"], loop="hold")
    frames = {0: pull_end, 0.06: {**pull_end, **hands(*SPLAY)}}
    for t, s, body in ((0.22, 1.0, LURK), (0.5, 0.45, WALK_A), (0.8, 0.2, WALK_B), (1.0, 0.12, WALK_A), (1.1, 0.0, WALK_A)):
        ss = max(s, 0.12)
        frames[t] = gpose(body, root=(0, 0, max(zs(ss), GUEST_Z + 2)), s=s, arms=ARMS_BACK, fingers=hands(*SPLAY),
                          floor=VP * (1 - ss) if s < 1 else 0.0, m=m)
    keyed(wd, frames)
    A.append(wd)

    # report the hand positions the gameplay relies on
    for nm, pd in (("grab", grabbed), ("pull_end", pull_end)):
        pr, pl_ = palm_pos(m, pd, "r"), palm_pos(m, pd, "l")
        print(f"    dn_guest {nm}: palms r={np.round(pr, 1)} l={np.round(pl_, 1)} "
              f"armF={_v('s', pd['arm_r_1@s'])[1]:.2f}")
    return A, dict(emerged=emerged, reach_end=reach_end, grabbed=grabbed, pull_end=pull_end, crouch=crouch,
                   peek=frames and None)


# ================================================================ particles + sounds
def build_fx(pack):
    fx = particles(pack)
    fx.effect("dn_guest_mote", "dot", count=6, life=(1.5, 2.6), size=(0.07, 0.0), shape=("sphere", 1.6),
              speed=(0.05, 0.25), accel=(0, 0.15, 0), colors=["#cfc6b0cc", "#a98cc8aa", "#6a4a6e00"])
    fx.effect("dn_guest_dust", "puff", count=8, life=(1.0, 2.0), size=(0.25, 0.75), shape=("disc", 1.0),
              speed=(0.2, 0.6), accel=(0, -0.08, 0), drag=1.2, colors=["#8b8f9a99", "#2a2d5200"], blend="blend",
              spin=(360, 30))
    fx.effect("dn_guest_scrap", None, sprites=["petal", "shard"], count=6, life=(1.2, 2.2), size=(0.13, 0.09),
              shape=("sphere", 1.2), speed=(0.4, 1.2), accel=(0, -1.2, 0), drag=1.4,
              colors=["#7d5a7dff", "#cfc6b0ff", "#6a4a6e00"], blend="blend", spin=(360, 220))
    fx.effect("dn_guest_breath", "smoke", count=3, life=(0.8, 1.4), size=(0.15, 0.6), shape=("sphere", 0.2),
              speed=(0.3, 0.6), accel=(0, 0.3, 0), drag=0.8, colors=["#bcc0d0aa", "#8b8f9a00"], blend="blend",
              spin=(360, 40))
    fx.effect("dn_guest_lamp", "dot", count=6, life=(1.4, 2.4), size=(0.06, 0.0), shape=("box", (1.0, 2.2, 0.2)),
              speed=(0.1, 0.4), accel=(0, 0.1, 0), drag=0.6, colors=["#fff4d6ee", "#efdca6aa", "#efdca600"])
    fx.effect("dn_guest_grip", "ringthin", count=1, life=(0.35, 0.4), size=(0.3, 1.8),
              colors=["#efe6ffff", "#e8b4c8aa", "#6a4a6e00"])
    fx.effect("dn_guest_squeeze", "shard", count=5, life=(0.2, 0.45), size=(0.1, 0.0), shape=("sphere", 0.3),
              speed=(1.0, 2.6), drag=1.0, colors=["#ffffffff", "#e8b4c8cc", "#6e2f3a00"], spin=(360, 300))
    fx.effect("dn_guest_drag", "puff", count=4, life=(0.5, 0.9), size=(0.2, 0.5), shape=("disc", 0.4),
              speed=(0.3, 0.8), accel=(0, 0.3, 0), drag=1.5, colors=["#8a826fcc", "#5a4a4a00"], blend="blend")
    fx.effect("dn_guest_splinter", None, sprites=["shard", "rock"], count=16, life=(0.6, 1.2), size=(0.13, 0.07),
              shape=("sphere", 0.5), speed=(3.0, 7.0), accel=(0, -9, 0), drag=0.5,
              colors=["#7a4d3eff", "#3a2626ff", "#3a262600"], blend="blend", spin=(360, 500), collide=True)
    fx.effect("dn_guest_shock", "ringthin", count=1, life=(0.5, 0.6), size=(0.4, 7.0), facing="emitter_transform_xz",
              colors=["#ffffffff", "#e8b4c8cc", "#6e2f3a00"])
    fx.effect("dn_guest_shock_v", "ring", count=1, life=(0.3, 0.35), size=(0.5, 4.0),
              colors=["#efe6ffff", "#6a4a6e00"])
    fx.effect("dn_guest_doors", "door", count=10, life=(0.6, 1.1), size=(0.26, 0.05), shape=("sphere", 0.6),
              speed=(3.0, 6.0), drag=1.5, colors=["#ffffffff", "#cfc6b0ff", "#6a4a6e00"], spin=(360, 300))
    fx.effect("dn_guest_keyhole", "key", count=8, life=(0.5, 0.8), size=(0.16, 0.02), shape=("sphere", 1.6, "surface"),
              direction="inwards", speed=(2.0, 3.0), colors=["#efe6ffff", "#a99ad0cc", "#6a4a6e00"], spin=(360, 180))
    fx.effect("dn_guest_cracklight", "spark", count=12, life=(0.3, 0.6), size=(0.13, 0.0),
              shape=("box", (1.1, 2.4, 0.1)), speed=(0.2, 0.8), colors=["#ffffffff", "#e6defcff", "#6a4a6e00"])


def _click(f, dur=0.05, tau=0.006, ring=0.4):
    t = sy.t_axis(dur)
    return (sy.bandpass(sy.noise(dur), f, 5) * np.exp(-t / tau)
            + ring * np.sin(2 * np.pi * f * 1.27 * t) * np.exp(-t / (tau * 3)))


def _whisper(dur, vowels, hp=300):
    """Breathy formant noise; each syllable swells in and stops dead (reads as reversed speech)."""
    seg = dur / len(vowels)
    parts = []
    for i, v in enumerate(vowels):
        L = seg * 1.35
        w = sy.formants(sy.highpass(sy.noise(L), hp), sy.VOWELS[v])
        parts.append((i * seg, sy.norm(w) * sy.env(L, L * 0.78, 0.02, 0.9, 0.035) * (0.6 + 0.4 * ((i * 7) % 3) / 2)))
    return sy.norm(sy.at(dur, *parts))


def _clicks(dur, n, rng, lo=1400, hi=3600):
    parts = []
    for _ in range(n):
        f = rng.uniform(lo, hi) if rng.random() > 0.25 else rng.uniform(380, 700)
        parts.append((rng.uniform(0, dur * 0.92), _click(f, 0.05, rng.uniform(0.003, 0.009)), rng.uniform(0.3, 1.0)))
    return sy.at(dur, *parts)


def build_sounds(pack):
    rng = np.random.default_rng(2402)
    # door manifest: a wood creak played backwards out of its own echo, settling into place
    cr = sy.creak(1.3, 140, 250, 0.3)
    swell = sy.reverb(cr, 1.6, 0.6)[::-1]
    man = sy.at(2.0, (0.0, swell * 0.8), (0.0, sy.rumble(1.8, 45, 1.5) * 0.35),
                (len(swell) / sy.SR - 0.05, sy.thump(0.4, 90, 40, 0.4) * 0.7),
                (len(swell) / sy.SR - 0.05, _click(900, 0.08, 0.02) * 0.5))
    sy.save(pack, "dn_guest_manifest", sy.reverb(man, 1.0, 0.25), max_distance=48)

    # handle: metal rattles, a slow dry squeak, then the latch gives
    sq = sy.highpass(sy.creak(1.0, 1150, 880, 0.12), 600) * 0.22
    rat = [(t, _click(f, 0.06, 0.007) * g) for t, f, g in ((0.12, 2600, 0.6), (0.17, 2900, 0.45), (0.3, 2500, 0.7),
                                                            (0.35, 3100, 0.5), (0.4, 2700, 0.35), (0.72, 2400, 0.3))]
    latch = sy.at(0.3, (0.0, _click(1700, 0.1, 0.012, 0.8)), (0.01, sy.thump(0.2, 220, 120, 0.2) * 0.5))
    hd = sy.at(1.5, (0.45, sq), *rat, (1.08, latch * 1.2))
    sy.save(pack, "dn_guest_handle", sy.reverb(hd, 0.7, 0.2), max_distance=40)

    # the long creak of the door opening, air rushing out of the corridor
    op = sy.at(2.6, (0.0, sy.creak(2.4, 100, 170, 0.4)), (0.1, sy.creak(2.3, 205, 320, 0.3) * 0.35),
               (0.3, sy.wind(2.2, 180, 520, 2.5, 0.3) * 0.3))
    sy.save(pack, "dn_guest_creak", sy.reverb(op, 1.4, 0.35), max_distance=48)

    # corridor drone: very low, slowly rising, beating; a thin tinnitus line on top
    dur = 4.0
    t = sy.t_axis(dur)
    f = 34 + 16 * (t / dur) ** 1.5
    d = sy.osc(f, wave_="saw") * 0.6 + sy.osc(f * 1.5 * 1.004, wave_="saw") * 0.3 + sy.osc(f * 2.01) * 0.3
    d = sy.lowpass(d, 240) + sy.bandpass(sy.noise(dur), 140, 2) * 0.35
    d = sy.norm(d) * sy.env(dur, 1.2, 0.1, 0.95, 0.8)
    d = d + sy.osc(sy.sweep(2300, 2460, dur)) * 0.02 * sy.env(dur, 2.0, 0.1, 1.0, 0.6)
    sy.save(pack, "dn_guest_drone", sy.reverb(d, 2.0, 0.3), max_distance=40)

    # its voice: breathy reversed whispers, no words
    def voice(vs, p, tone):
        w = _whisper(1.7, vs)
        tn = sy.osc(sy.sweep(tone, tone * 0.93, 1.7)) * sy.env(1.7, 0.9, 0.1, 0.7, 0.3) * 0.06
        sig = sy.reverb(w + tn, 1.3, 0.45)[::-1]
        return sy.pitch(sig, p)
    sy.save(pack, "dn_guest_voice", voice(["oo", "eh", "ah", "oo", "ee"], 1.0, 310),
            variants=[voice(["ah", "oo", "eh", "ee"], 0.88, 280), voice(["ee", "oh", "oo", "eh", "ah", "oo"], 1.08, 340)],
            volume=0.9, max_distance=32)

    # dry joint clicks and fabric rustle
    def clicks(seed_dur):
        c = _clicks(seed_dur, 16, rng)
        rs = sy.highpass(sy.noise(seed_dur), 2500) * sy.lowpass(np.abs(sy.noise(seed_dur)), 6) * 6
        return sy.norm(c + sy.norm(rs) * 0.25)
    sy.save(pack, "dn_guest_clicks", clicks(1.3), variants=[clicks(1.2)], volume=0.8, max_distance=28)

    # it comes up the corridor: bare feet on boards, closer and faster
    steps = []
    for i, (tt, g) in enumerate(((0.0, 0.15), (0.3, 0.22), (0.56, 0.32), (0.76, 0.5), (0.93, 0.72), (1.08, 1.0))):
        steps.append((tt, sy.thump(0.25, 85, 48, 0.15) * g))
        steps.append((tt + 0.01, sy.creak(0.22, 300 + i * 25, 380, 0.2) * 0.12 * g))
    sy.save(pack, "dn_guest_approach", sy.reverb(sy.at(1.6, *steps), 1.2, 0.35), max_distance=36)

    # grab: the thud of the grip, a cloth snap, knuckles
    snap = sy.highpass(sy.noise(0.07), 1800) * np.exp(-sy.t_axis(0.07) / 0.015)
    gr = sy.at(0.9, (0.0, sy.thump(0.45, 130, 50, 0.7)), (0.0, snap * 0.7), (0.03, _clicks(0.12, 7, rng, 900, 2400) * 0.6),
               (0.15, _whisper(0.6, ["ah", "oo"])[::-1] * 0.25))
    sy.save(pack, "dn_guest_grab", sy.reverb(gr, 0.6, 0.2), max_distance=32)

    # strained dragging: sinew creak, scraping, a breathy wordless strain
    dd = 1.7
    scrape = sy.bandpass(sy.noise(dd), 900, 2) * (0.4 + 3 * np.abs(sy.lowpass(sy.noise(dd), 9)))
    strain = sy.roar(1.6, 70, 58, growl=16, rough=0.3, formant=(380, 900), breath=0.7, bend=0.1)
    dr = sy.at(dd, (0.0, sy.creak(dd, 62, 86, 0.45) * 0.7), (0.0, sy.norm(scrape) * 0.45), (0.05, strain * 0.3))
    sy.save(pack, "dn_guest_drag", sy.reverb(dr, 0.8, 0.25), max_distance=36)

    # the SLAM: air pushed ahead of the door, then a huge wooden impact with a short hard room
    knock = sy.bandpass(sy.noise(0.14), 260, 3) * np.exp(-sy.t_axis(0.14) / 0.03)
    sl = sy.at(1.6, (0.0, sy.whoosh(0.16, 600, 2400) * 0.45), (0.15, sy.thump(1.3, 95, 26, 0.9)),
               (0.15, sy.norm(knock)), (0.15, sy.crack(0.5, 3600, 18) * 0.55), (0.16, sy.rumble(1.2, 40) * 0.5),
               (0.32, _clicks(0.35, 8, rng, 1600, 3200) * 0.3))
    sy.save(pack, "dn_guest_slam", sy.reverb(sl, 0.8, 0.32, tone=3500), max_distance=72)

    # aftermath hush: a cold breath drawn back in, a fading high tone, the keyhole clicks shut
    hush = sy.at(2.0, (0.0, sy.reverb(sy.shimmer(0.9, 1500, 10, 1.6), 1.2, 0.6)[::-1] * 0.4),
                 (0.0, sy.osc(sy.sweep(1620, 1500, 1.6)) * sy.env(1.6, 0.4, 0.1, 0.8, 1.0) * 0.18),
                 (0.0, sy.highpass(sy.noise(1.4), 3000) * sy.env(1.4, 1.0, 0.1, 0.5, 0.3) * 0.12),
                 (1.05, _click(2200, 0.08, 0.01, 0.6) * 0.8))
    sy.save(pack, "dn_guest_hush", sy.reverb(hush, 1.2, 0.3), volume=0.8, max_distance=40)


# ================================================================ build + previews
def _combo_pose(door_pose, guest_pose, dummy_z=None):
    out = {}
    for k, v in (door_pose or {}).items():
        out["d_" + k] = v
    for k, v in (guest_pose or {}).items():
        out["g_" + k] = v
    out["dummy"] = ((0, 0, 0), (0, 0, dummy_z if dummy_z is not None else 0), (1, 1, 1) if dummy_z is not None else (0, 0, 0))
    return out


def _apose(anim, t, extra=None):
    p = anim.pose(t)
    for a2, t2 in (extra or []):
        for b, (r, pp, s) in a2.pose(t2).items():
            if b in p:
                r0, p0, s0 = p[b]
                p[b] = (tuple(r0[i] + r[i] for i in range(3)), tuple(p0[i] + pp[i] for i in range(3)),
                        tuple(s0[i] * s[i] for i in range(3)))
            else:
                p[b] = (r, pp, s)
    return p


def build(pack):
    build_fx(pack)
    door = build_door(Model("dn_guest_door", density=1.5, bounds=(9, 8, (0, 3, 0)), alts=("cracked",)))
    da = door_anims()
    pack.actor("dn_guest_door", door, da, DOOR_STATES, always=["door_idle"], lifetime=40, blend=0.1,
               visibility=[{"corr*": "q.property('grimoire:state') >= 4 && q.property('grimoire:state') <= 6"}],
               particles={"dust": "grimoire:dn_guest_dust"}, display="The Door Behind You")
    guest = build_guest(Model("dn_guest", density=2.0, bounds=(10, 9, (0, 3.5, -1))))
    ga, keyp = guest_anims(guest)
    pack.actor("dn_guest", guest, ga, GUEST_STATES, always=["guest_idle"], lifetime=40, blend=0.15,
               particles={"breath": "grimoire:dn_guest_breath"}, display="The Guest")
    build_sounds(pack)
    print(f"    dn_guest_door: {door.cube_count()} cubes, {len(door.order)} bones, tex {door.tex_size}")
    print(f"    dn_guest: {guest.cube_count()} cubes, {len(guest.order)} bones, tex {guest.tex_size}")

    if not getattr(pack.preview, "enabled", False):
        return
    D = {a.name: a for a in da}
    G = {a.name: a for a in ga}
    gi = (G["guest_idle"], 1.0)
    pack.preview("dn_guest_door", door, [(D["closed"], 0.5), (D["handle"], 1.0), (D["held"], 0.3)],
                 views=((0, 6), (30, 14), (-120, 14)), cell=(360, 360))
    pack.preview("dn_guest_door_cracked", door, [(D["slam"], 0.6), (D["vanish"], 0.45)],
                 views=((0, 6), (35, 14)), cell=(320, 320), skin="cracked")
    pack.preview("dn_guest_body", guest, [None, [(G["emerge"], 2.6), gi], [(G["reach"], 1.2), gi]],
                 views=((0, 6), (60, 10), (150, 10), (-90, 4)), cell=(320, 360))
    # composite: door + Guest + a zombie-sized dummy to check that the hands meet the gameplay points
    combo = Model("dn_guest_combo", density=1.0)
    build_door(combo, "d_")
    build_guest(combo, "g_")
    dm = combo.bone("dummy", pivot=(0, 0, 0))
    dm.box((0, 15.6, GRAB_Z), (9.6, 31.2, 5), tex.flat("#4f7a4a", key="dng_dummy"))
    held = D["held"].pose(0.3)
    rows = [
        _combo_pose(held, _apose(G["emerge"], 0.6, [gi]), GRAB_Z * 0),
        _combo_pose(held, _apose(G["emerge"], 1.62, [gi]), 0),
        _combo_pose(held, _apose(G["emerge"], 2.15, [gi]), 0),
        _combo_pose(held, _apose(G["reach"], 1.2, [gi]), 0),
        _combo_pose(held, _apose(G["grab"], 0.5, [gi]), 0),
        _combo_pose(held, _apose(G["pull"], 1.6, [gi]), PULL_Z - GRAB_Z),
    ]
    pack.preview("dn_guest_combo", combo, rows, views=((0, 8), (40, 12), (90, 6)), cell=(330, 330))
