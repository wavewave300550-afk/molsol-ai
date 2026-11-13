"""Procedural texture painters ("materials") for the geometry kit.

Every factory returns a geo.Mat.  Painters receive a FaceCtx (w, h, U, V in 0..1,
X/Y/Z model coords, rng) and return a float tile (h, w, 5): r, g, b, alpha, glow.
Colours are '#rrggbb' strings or (r, g, b) floats.
"""
from __future__ import annotations

import math

import numpy as np

from .geo import Mat


def rgb(c):
    if isinstance(c, str):
        c = c.lstrip("#")
        return np.array([int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
    return np.array(c, dtype=float)


def mix(a, b, t):
    return a + (b - a) * t


def tile(ctx, color, a=1.0, e=0.0):
    t = np.zeros((ctx.h, ctx.w, 5))
    t[..., :3] = rgb(color)
    t[..., 3] = a
    t[..., 4] = e
    return t


def _hash(ix, iy, seed=0):
    n = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def vnoise(x, y, seed=0):
    """Smooth value noise over float coordinate arrays, 0..1."""
    x0, y0 = np.floor(x), np.floor(y)
    fx, fy = x - x0, y - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = _hash(x0, y0, seed), _hash(x0 + 1, y0, seed)
    c, d = _hash(x0, y0 + 1, seed), _hash(x0 + 1, y0 + 1, seed)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(x, y, seed=0, octaves=3):
    out, amp, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        out = out + vnoise(x * (2 ** o), y * (2 ** o), seed + o * 17) * amp
        tot += amp
        amp *= 0.5
    return out / tot


def px(ctx):
    """Integer pixel coordinate grids (ix, iy)."""
    return np.meshgrid(np.arange(ctx.w), np.arange(ctx.h))


def grain(ctx, t, amount=0.06):
    """Minecraft-style per-pixel brightness jitter."""
    j = (ctx.rng.random((ctx.h, ctx.w)) - 0.5) * 2 * amount
    t[..., :3] = np.clip(t[..., :3] * (1 + j[..., None]), 0, 1)
    return t


def edge(ctx, t, amount=0.16, width=1):
    """Darken the border pixels of a tile (cheap ambient occlusion / panel line)."""
    ix, iy = px(ctx)
    d = np.minimum(np.minimum(ix, ctx.w - 1 - ix), np.minimum(iy, ctx.h - 1 - iy))
    m = (d < width) & (min(ctx.w, ctx.h) > 2 * width + 1)
    t[..., :3] = np.where(m[..., None], t[..., :3] * (1 - amount), t[..., :3])
    return t


def bevel(ctx, t, amount=0.14):
    """Lighten top/left border, darken bottom/right border."""
    if min(ctx.w, ctx.h) < 4:
        return t
    ix, iy = px(ctx)
    hi = (iy == 0) | (ix == 0)
    lo = (iy == ctx.h - 1) | (ix == ctx.w - 1)
    t[..., :3] = np.where(hi[..., None], np.clip(t[..., :3] * (1 + amount) + amount * 0.3, 0, 1), t[..., :3])
    t[..., :3] = np.where(lo[..., None] & ~hi[..., None], t[..., :3] * (1 - amount * 1.3), t[..., :3])
    return t


# ---------------------------------------------------------------- basic materials
def flat(color, glow=0.0, a=1.0, mode="solid", jitter=0.0, key=None):
    def fn(ctx):
        t = tile(ctx, color, a, glow)
        return grain(ctx, t, jitter) if jitter else t
    return Mat(fn, key or f"flat{color}{glow}{a}{jitter}", mode=mode)


def speck(color, var=0.07, glow=0.0, edge_dark=0.12, a=1.0, mode="solid"):
    def fn(ctx):
        t = grain(ctx, tile(ctx, color, a, glow), var)
        return edge(ctx, t, edge_dark) if edge_dark else t
    return Mat(fn, f"speck{color}{var}{glow}{edge_dark}{a}", mode=mode)


def vgrad(top, bottom, var=0.05, glow_top=0.0, glow_bottom=0.0, edge_dark=0.1, a=1.0, mode="solid"):
    """Gradient down the tile (top row -> bottom row)."""
    ct, cb = rgb(top), rgb(bottom)

    def fn(ctx):
        t = tile(ctx, top, a)
        v = ctx.V[..., None]
        t[..., :3] = mix(ct, cb, v)
        t[..., 4] = mix(glow_top, glow_bottom, ctx.V)
        t = grain(ctx, t, var)
        return edge(ctx, t, edge_dark) if edge_dark else t
    return Mat(fn, f"vgrad{top}{bottom}{var}{glow_top}{glow_bottom}{a}", mode=mode)


def sgrad(c0, c1, axis="y", lo=0.0, hi=16.0, var=0.05, glow0=0.0, glow1=0.0, edge_dark=0.0, a=1.0, mode="solid",
          steps=0):
    """Spatial gradient along a model axis between coordinate lo..hi (seamless across cubes)."""
    k0, k1 = rgb(c0), rgb(c1)

    def fn(ctx):
        co = {"x": ctx.X, "y": ctx.Y, "z": ctx.Z}[axis]
        f = np.clip((co - lo) / (hi - lo), 0, 1)
        if steps:
            f = np.round(f * steps) / steps
        t = tile(ctx, c0, a)
        t[..., :3] = mix(k0, k1, f[..., None])
        t[..., 4] = mix(glow0, glow1, f)
        t = grain(ctx, t, var)
        return edge(ctx, t, edge_dark) if edge_dark else t
    return Mat(fn, f"sgrad{c0}{c1}{axis}{lo}{hi}{glow0}{glow1}{a}{steps}", mode=mode, spatial=True)


def mottled(c0, c1, scale=4.0, var=0.05, glow=0.0, edge_dark=0.1, a=1.0, mode="solid", thresh=None, seed=0):
    """Two-colour blotchy noise (skin, stone, moss...). thresh makes hard patches."""
    k0, k1 = rgb(c0), rgb(c1)

    def fn(ctx):
        ix, iy = px(ctx)
        n = fbm(ix / scale + ctx.variant * 31.7, iy / scale, seed + ctx.variant * 7)
        if thresh is not None:
            n = (n > thresh).astype(float)
        t = tile(ctx, c0, a, glow)
        t[..., :3] = mix(k0, k1, n[..., None])
        t = grain(ctx, t, var)
        return edge(ctx, t, edge_dark) if edge_dark else t
    return Mat(fn, f"mott{c0}{c1}{scale}{var}{glow}{a}{thresh}{seed}", mode=mode)


def scales(base, dark, light=None, size=4, var=0.05, glow_gap=0.0, gap=None, edge_dark=0.0):
    """Overlapping reptile scales. glow_gap lights the gaps (thermal fissures)."""
    kb, kd = rgb(base), rgb(dark)
    kl = rgb(light) if light is not None else np.clip(kb * 1.25 + 0.05, 0, 1)
    kg = rgb(gap) if gap is not None else kd

    def fn(ctx):
        ix, iy = px(ctx)
        row = iy // size
        ox = ix + (row % 2) * (size // 2)
        lx, ly = ox % size, iy % size
        t = tile(ctx, base)
        top = (ly == 0)
        side = (lx == 0) & (ly < size - 1)
        hi = (ly == 1) & (lx > 0) & (lx < size - 1)
        t[..., :3] = np.where(hi[..., None], kl, t[..., :3])
        g = top | side
        t[..., :3] = np.where(g[..., None], kg, t[..., :3])
        t[..., 4] = np.where(g, glow_gap, 0.0)
        cell = _hash(ox // size, row, 5)
        t[..., :3] *= (0.9 + 0.2 * cell)[..., None] * np.where(g[..., None], 1.0, 1.0)
        t = grain(ctx, t, var)
        return edge(ctx, t, edge_dark) if edge_dark else t
    return Mat(fn, f"scales{base}{dark}{light}{size}{glow_gap}{gap}")


def plates(base, line, hi=None, cell=(8, 6), rivet=None, var=0.04, glow_line=0.0):
    """Armour / stone block plating with offset rows."""
    kb, kl = rgb(base), rgb(line)
    kh = rgb(hi) if hi is not None else np.clip(kb * 1.18 + 0.04, 0, 1)

    def fn(ctx):
        ix, iy = px(ctx)
        cw, ch = cell
        row = iy // ch
        ox = ix + (row % 2) * (cw // 2)
        lx, ly = ox % cw, iy % ch
        t = tile(ctx, base)
        t[..., :3] = np.where(((ly == 1) | (lx == 1))[..., None], kh, t[..., :3])
        ln = (ly == 0) | (lx == 0)
        t[..., :3] = np.where(ln[..., None], kl, t[..., :3])
        t[..., 4] = np.where(ln, glow_line, 0)
        if rivet is not None:
            rv = (lx == 2) & (ly == 2)
            t[..., :3] = np.where(rv[..., None], rgb(rivet), t[..., :3])
        t[..., :3] *= (0.92 + 0.16 * _hash(ox // cw, row, 3))[..., None]
        return grain(ctx, t, var)
    return Mat(fn, f"plates{base}{line}{hi}{cell}{rivet}{glow_line}")


def marble(base="#f3efe6", vein="#b9b2a6", vein2=None, scale=7.0, var=0.025, edge_dark=0.08, glow=0.0):
    kb, kv = rgb(base), rgb(vein)
    k2 = rgb(vein2) if vein2 else kv

    def fn(ctx):
        ix, iy = px(ctx)
        s = ctx.variant * 13.3
        n = fbm(ix / scale + s, iy / scale - s, 11)
        v = np.abs(np.sin((ix * 0.35 + iy * 0.22 + n * 9.0 + s)))
        t = tile(ctx, base, 1, glow)
        m = np.clip((0.16 - v) / 0.16, 0, 1)
        t[..., :3] = mix(kb, kv, (m * 0.85)[..., None])
        v2 = np.abs(np.sin((ix * -0.21 + iy * 0.31 + n * 7.0 + 2.0 + s)))
        m2 = np.clip((0.07 - v2) / 0.07, 0, 1)
        t[..., :3] = mix(t[..., :3], k2, (m2 * 0.55)[..., None])
        t[..., :3] *= (0.95 + 0.08 * n)[..., None]
        t = grain(ctx, t, var)
        return edge(ctx, t, edge_dark) if edge_dark else t
    return Mat(fn, f"marble{base}{vein}{vein2}{scale}{glow}")


def metal(base="#c9a24a", hi="#ffe9a3", lo="#7a5a1e", bands=3.0, var=0.03, glow=0.0, trim=None, vertical=False):
    """Brushed metal with soft highlight bands and bevel."""
    kb, kh, kl = rgb(base), rgb(hi), rgb(lo)

    def fn(ctx):
        c = ctx.U if vertical else ctx.V
        s = np.sin((c * bands + 0.15 + ctx.variant * 0.37) * math.pi * 2) * 0.5 + 0.5
        t = tile(ctx, base, 1, glow)
        t[..., :3] = np.where(s[..., None] > 0.5, mix(kb, kh, ((s - 0.5) * 2)[..., None] ** 2),
                              mix(kl, kb, (s * 2)[..., None]))
        t = bevel(ctx, grain(ctx, t, var), 0.2)
        if trim is not None and min(ctx.w, ctx.h) >= 6:
            ix, iy = px(ctx)
            d = np.minimum(np.minimum(ix, ctx.w - 1 - ix), np.minimum(iy, ctx.h - 1 - iy))
            t[..., :3] = np.where((d == 1)[..., None], rgb(trim), t[..., :3])
        return t
    return Mat(fn, f"metal{base}{hi}{lo}{bands}{glow}{trim}{vertical}")


def stone(base="#8a8378", dark="#5d574e", light="#a8a094", scale=5.0, cracks=0.25, var=0.06, edge_dark=0.14,
          glow_crack=0.0, crack_color=None, strata=0.0):
    kb, kd, kl = rgb(base), rgb(dark), rgb(light)
    kc = rgb(crack_color) if crack_color else kd * 0.7

    def fn(ctx):
        ix, iy = px(ctx)
        s = ctx.variant * 9.1
        n = fbm(ix / scale + s, iy / scale + s * 0.3, 21)
        t = tile(ctx, base)
        t[..., :3] = np.where(n[..., None] > 0.5, mix(kb, kl, ((n - 0.5) * 2)[..., None]),
                              mix(kd, kb, (n * 2)[..., None]))
        if strata:
            band = np.sin((ctx.Y * strata + n * 2.0)) * 0.5 + 0.5
            t[..., :3] *= (0.86 + 0.2 * band)[..., None]
        if cracks:
            c = np.abs(vnoise(ix / 3.0 + s, iy / 3.0, 5) - vnoise(ix / 3.0 + 40.0, iy / 3.0 + s, 9))
            m = c < 0.035 * (cracks / 0.25)
            t[..., :3] = np.where(m[..., None], kc, t[..., :3])
            t[..., 4] = np.where(m, glow_crack, 0)
        t = grain(ctx, t, var)
        return edge(ctx, t, edge_dark) if edge_dark else t
    return Mat(fn, f"stone{base}{dark}{light}{scale}{cracks}{glow_crack}{crack_color}{strata}", spatial=bool(strata))


def bone_mat(base="#e9dfc6", shade="#b8a985", pores=0.1, var=0.04, glow=0.0):
    kb, ks = rgb(base), rgb(shade)

    def fn(ctx):
        ix, iy = px(ctx)
        n = fbm(ix / 3.0 + ctx.variant * 5, iy / 5.0, 33)
        t = tile(ctx, base, 1, glow)
        t[..., :3] = mix(kb, ks, (n * 0.6)[..., None])
        p = ctx.rng.random((ctx.h, ctx.w)) < pores * 0.25
        t[..., :3] = np.where(p[..., None], ks * 0.8, t[..., :3])
        return bevel(ctx, grain(ctx, t, var), 0.16)
    return Mat(fn, f"bone{base}{shade}{pores}{glow}")


def wood(base="#8a6238", dark="#5e3f20", var=0.04, vertical=True, plank=0):
    kb, kd = rgb(base), rgb(dark)

    def fn(ctx):
        ix, iy = px(ctx)
        a, b = (ix, iy) if vertical else (iy, ix)
        n = fbm(a / 1.6 + ctx.variant * 7, b / 9.0, 41)
        t = tile(ctx, base)
        t[..., :3] = mix(kd, kb, np.clip(n * 1.3, 0, 1)[..., None])
        if plank:
            t[..., :3] = np.where(((a % plank) == 0)[..., None], kd * 0.7, t[..., :3])
        return edge(ctx, grain(ctx, t, var), 0.14)
    return Mat(fn, f"wood{base}{dark}{vertical}{plank}")


def porcelain(base="#f4efe4", shade="#d9cfbd", crackle="#b9ad98", crack=0.5, glow=0.0, var=0.015, gilt=None):
    """Glazed ceramic: smooth shading, hairline crackle, optional gilt border."""
    kb, ks, kc = rgb(base), rgb(shade), rgb(crackle)

    def fn(ctx):
        ix, iy = px(ctx)
        t = tile(ctx, base, 1, glow)
        sh = np.clip((ctx.V - 0.35) * 0.9, 0, 1)
        t[..., :3] = mix(kb, ks, sh[..., None])
        if min(ctx.w, ctx.h) >= 4:
            hl = (np.abs(ctx.U - 0.3) < 0.08) & (ctx.V > 0.12) & (ctx.V < 0.45)
            t[..., :3] = np.where(hl[..., None], np.clip(t[..., :3] + 0.06, 0, 1), t[..., :3])
        if crack:
            s = ctx.variant * 17.0
            c = np.abs(vnoise(ix / 4.0 + s, iy / 4.0, 51) - vnoise(ix / 4.0 + 13.0, iy / 4.0 + s, 52))
            t[..., :3] = np.where((c < 0.02 * crack)[..., None], kc, t[..., :3])
        if gilt is not None and min(ctx.w, ctx.h) >= 6:
            d = np.minimum(np.minimum(ix, ctx.w - 1 - ix), np.minimum(iy, ctx.h - 1 - iy))
            t[..., :3] = np.where((d == 0)[..., None], rgb(gilt), t[..., :3])
        return grain(ctx, t, var)
    return Mat(fn, f"porc{base}{shade}{crackle}{crack}{glow}{gilt}")


def fabric(base, stripe=None, weave=0.08, stripe_w=4, var=0.03, a=1.0, mode="solid", fringe=False, glow=0.0,
           vertical=True):
    kb = rgb(base)
    ks = rgb(stripe) if stripe is not None else kb

    def fn(ctx):
        ix, iy = px(ctx)
        t = tile(ctx, base, a, glow)
        if stripe is not None:
            c = ix if vertical else iy
            t[..., :3] = np.where(((c // stripe_w) % 2 == 1)[..., None], ks, kb)
        w = ((ix + iy) % 2) * weave
        t[..., :3] *= (1 - w)[..., None]
        fold = np.sin(ctx.U * math.pi * 3 + ctx.variant) * 0.06
        t[..., :3] = np.clip(t[..., :3] * (1 + fold[..., None]), 0, 1)
        if fringe:
            cut = (iy >= ctx.h - 2) & (ix % 2 == 0)
            t[..., 3] = np.where(cut, 0.0, t[..., 3])
        return grain(ctx, t, var)
    return Mat(fn, f"fabric{base}{stripe}{weave}{stripe_w}{a}{mode}{fringe}{glow}{vertical}", mode=mode)


def foliage(c0="#3f7a35", c1="#6fae4b", holes=0.28, glow=0.0, scale=2.0, flowers=None):
    """Cut-out leafy canopy texture."""
    k0, k1 = rgb(c0), rgb(c1)

    def fn(ctx):
        ix, iy = px(ctx)
        n = fbm(ix / scale + ctx.variant * 3, iy / scale, 61, 2)
        t = tile(ctx, c0, 1, glow)
        t[..., :3] = mix(k0, k1, np.clip(n * 1.4 - 0.2, 0, 1)[..., None])
        h = _hash(ix, iy, 63 + ctx.variant)
        t[..., 3] = np.where(h < holes, 0.0, 1.0)
        if flowers is not None:
            fl = _hash(ix // 2, iy // 2, 64 + ctx.variant) > 0.93
            t[..., :3] = np.where(fl[..., None], rgb(flowers), t[..., :3])
            t[..., 3] = np.where(fl, 1.0, t[..., 3])
        return grain(ctx, t, 0.06)
    return Mat(fn, f"foliage{c0}{c1}{holes}{glow}{scale}{flowers}")


def crystal(base="#9fd8ff", deep="#3f7fd0", hi="#ffffff", a=0.82, mode="blend", glow=0.0, facets=5.0):
    """Faceted ice / crystal. blend mode -> translucent."""
    kb, kd, kh = rgb(base), rgb(deep), rgb(hi)

    def fn(ctx):
        ix, iy = px(ctx)
        s = ctx.variant * 3.3
        f = np.abs(((ix + iy * 0.6 + s) / facets) % 2 - 1)
        g = np.abs(((ix * 0.5 - iy + s) / facets) % 2 - 1)
        t = tile(ctx, base, a, glow)
        t[..., :3] = mix(kd, kb, np.clip(f * 0.7 + g * 0.5, 0, 1)[..., None])
        ridge = (f < 0.12) | (g < 0.1)
        t[..., :3] = np.where(ridge[..., None], kh, t[..., :3])
        if mode == "blend":
            t[..., 3] = np.where(ridge, min(1.0, a + 0.15), a)
        return t
    return Mat(fn, f"crystal{base}{deep}{hi}{a}{mode}{glow}{facets}", mode=mode)


def fluid(base="#3c7fd6", light="#8fd0ff", a=0.55, flow=6.0, glow=0.0):
    """Translucent flowing water (blend)."""
    kb, kl = rgb(base), rgb(light)

    def fn(ctx):
        ix, iy = px(ctx)
        n = fbm(ix / flow + ctx.variant * 5, iy / (flow * 0.4), 71)
        t = tile(ctx, base, a, glow)
        t[..., :3] = mix(kb, kl, np.clip((n - 0.45) * 3, 0, 1)[..., None])
        t[..., 3] = np.clip(a + (n - 0.5) * 0.35, 0.1, 1.0)
        return t
    return Mat(fn, f"fluid{base}{light}{a}{flow}{glow}", mode="blend")


def glow_flat(color, glow=1.0, a=1.0, core=None, mode="solid"):
    """Self-lit surface; optional brighter core toward the tile centre."""
    kc = rgb(color)
    kk = rgb(core) if core is not None else kc

    def fn(ctx):
        t = tile(ctx, color, a, glow)
        d = np.maximum(np.abs(ctx.U - 0.5), np.abs(ctx.V - 0.5)) * 2
        t[..., :3] = mix(kk, kc, np.clip(d, 0, 1)[..., None] ** 1.5)
        return t
    return Mat(fn, f"glowflat{color}{glow}{a}{core}{mode}", mode=mode)


# ---------------------------------------------------------------- shaped cut-outs (for planes)
def shaped(mask_fn, color, color2=None, glow=0.0, var=0.04, outline=None, key=None, a=1.0, mode="solid",
           glow_edge=None, directional=True):
    """Generic cut-out: mask_fn(u, v) -> 0..1 coverage where u, v in -1..1 (v up)."""
    k0 = rgb(color)
    k1 = rgb(color2) if color2 is not None else k0

    def fn(ctx):
        u, v = ctx.U * 2 - 1, 1 - ctx.V * 2
        m = np.clip(mask_fn(u, v), 0, 1)
        t = tile(ctx, color, 1, glow)
        t[..., :3] = mix(k0, k1, np.clip(np.hypot(u, v), 0, 1)[..., None])
        inside = m > 0.5
        t[..., 3] = np.where(inside, a if mode == "blend" else 1.0, 0.0)
        if outline is not None or glow_edge is not None:
            pad = np.pad(inside, 1, mode="constant")
            nb = pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:]
            rim = inside & ~nb
            if outline is not None:
                t[..., :3] = np.where(rim[..., None], rgb(outline), t[..., :3])
            if glow_edge is not None:
                t[..., 4] = np.where(rim, glow_edge, t[..., 4])
        return grain(ctx, t, var) if var else t
    return Mat(fn, key or f"shaped{id(mask_fn)}{color}{color2}{glow}{outline}{a}{mode}{glow_edge}", mode=mode,
               directional=directional)


def m_disc(r=1.0):
    return lambda u, v: (np.hypot(u, v) <= r).astype(float)


def m_ring(r0=0.7, r1=1.0):
    return lambda u, v: ((np.hypot(u, v) <= r1) & (np.hypot(u, v) >= r0)).astype(float)


def m_diamond():
    return lambda u, v: ((np.abs(u) + np.abs(v)) <= 1.0).astype(float)


def m_star(points=5, inner=0.45):
    def fn(u, v):
        a = np.arctan2(u, v)
        r = np.hypot(u, v)
        seg = (a / (2 * math.pi) * points) % 1.0
        edge_r = inner + (1 - inner) * np.abs(seg - 0.5) * 2
        return (r <= edge_r).astype(float)
    return fn


def m_crescent(offset=0.35):
    return lambda u, v: ((np.hypot(u, v) <= 1.0) & (np.hypot(u - offset, v) > 0.82)).astype(float)


def m_leaf():
    """Pointed leaf / flame, tip at top."""
    return lambda u, v: (np.abs(u) <= (1 - ((v + 1) / 2) ** 1.6) * np.sqrt(np.clip((v + 1) / 2, 0, 1)) * 1.6).astype(float)


def feather(base, tip=None, rachis=None, glow=0.0, glow_tip=None, barbs=True, taper=0.75, notch=0.18, var=0.04,
            glyph_color=None, glyph_glow=0.9, round_tip=True):
    """Feather on a plane: quill at the tile TOP, vane widening then rounding at the BOTTOM tip.

    glyph_color sprinkles luminous inscription marks along the vane.
    """
    kb = rgb(base)
    kt = rgb(tip) if tip is not None else kb
    kr = rgb(rachis) if rachis is not None else np.clip(kb * 0.7, 0, 1)

    def fn(ctx):
        ix, iy = px(ctx)
        u = ctx.U * 2 - 1
        v = ctx.V
        width = np.clip(0.28 + v * (1 - 0.28) / max(taper, 1e-3), 0, 1)
        if round_tip:
            width = np.where(v > 0.78, width * np.sqrt(np.clip(1 - ((v - 0.78) / 0.22) ** 2, 0, 1)), width)
        inside = np.abs(u) <= width
        t = tile(ctx, base, 1, glow)
        t[..., :3] = mix(kb, kt, np.clip((v - 0.35) / 0.65, 0, 1)[..., None])
        if barbs and ctx.w >= 4:
            diag = ((iy + np.abs(ix - (ctx.w - 1) / 2).astype(int)) % 3 == 0)
            t[..., :3] = np.where(diag[..., None], t[..., :3] * 0.86, t[..., :3])
            if notch:
                nt = (_hash(iy // 3, (ix > ctx.w / 2).astype(int), 7 + ctx.variant) < notch) & (np.abs(u) > width - 0.3)
                inside = inside & ~(nt & ((iy % 3) == 1))
        mid = np.abs(ix - (ctx.w - 1) / 2) < 0.75
        t[..., :3] = np.where(mid[..., None], kr, t[..., :3])
        gt = glow if glow_tip is None else glow_tip
        t[..., 4] = mix(glow, gt, np.clip((v - 0.4) / 0.6, 0, 1))
        if glyph_color is not None and ctx.w >= 5:
            g = (_hash(ix // 2, iy // 3, 91 + ctx.variant) > 0.8) & ~mid & ((iy % 3) != 0) & (ix % 2 == 0)
            t[..., :3] = np.where(g[..., None], rgb(glyph_color), t[..., :3])
            t[..., 4] = np.where(g, glyph_glow, t[..., 4])
        t[..., 3] = np.where(inside, 1.0, 0.0)
        return grain(ctx, t, var)
    return Mat(fn, f"feather{base}{tip}{rachis}{glow}{glow_tip}{barbs}{taper}{notch}{glyph_color}{round_tip}")


def eye_mat(iris="#3f6fd0", sclera="#f6f1e2", pupil="#10131c", lid="#c9a24a", glow=0.85, open_amt=1.0,
            slit=False, ring="#ffe9a3"):
    """An eye on a plane/face: almond opening, iris, pupil. open_amt 0..1 (0 = closed lid)."""
    def fn(ctx):
        u, v = ctx.U * 2 - 1, 1 - ctx.V * 2
        t = tile(ctx, lid)
        almond = (np.abs(v) <= (1 - u ** 2) * 0.62 * open_amt) & (np.abs(u) <= 0.96)
        r = np.hypot(u, v)
        t[..., :3] = np.where(almond[..., None], rgb(sclera), t[..., :3])
        ir = almond & (r < 0.5)
        t[..., :3] = np.where(ir[..., None], mix(rgb(iris), rgb(ring), np.clip(r / 0.5, 0, 1)[..., None] ** 3), t[..., :3])
        pu = almond & ((np.abs(u) < 0.1) & (np.abs(v) < 0.42) if slit else (r < 0.22))
        t[..., :3] = np.where(pu[..., None], rgb(pupil), t[..., :3])
        t[..., 4] = np.where(ir & ~pu, glow, np.where(almond, glow * 0.25, 0))
        rim = (np.abs(v) <= (1 - u ** 2) * 0.62 * max(open_amt, 0.12) + 0.14) & ~almond & (np.abs(u) <= 1)
        t[..., :3] = np.where(rim[..., None], rgb(lid) * 0.62, t[..., :3])
        return t
    return Mat(fn, f"eye{iris}{sclera}{pupil}{lid}{glow}{open_amt}{slit}{ring}", directional=True)


def windowed(wall, frame, glass, glow=0.8, cols=2, rows=2, arch=False, var=0.03, mullion=True):
    """Wall tile with lit windows."""
    def fn(ctx):
        t = grain(ctx, tile(ctx, wall), var)
        cu = (ctx.U * cols) % 1.0
        cv = (ctx.V * rows) % 1.0
        win = (np.abs(cu - 0.5) < 0.26) & (cv > 0.2) & (cv < 0.8)
        if arch:
            win = win | ((np.hypot((cu - 0.5) / 0.26, (cv - 0.2) / 0.14) < 1) & (cv <= 0.2))
        fr = (np.abs(cu - 0.5) < 0.34) & (cv > 0.13) & (cv < 0.87) & ~win
        t[..., :3] = np.where(fr[..., None], rgb(frame), t[..., :3])
        t[..., :3] = np.where(win[..., None], rgb(glass), t[..., :3])
        t[..., 4] = np.where(win, glow, 0)
        if mullion:
            mu = win & ((np.abs(cu - 0.5) < 0.035) | (np.abs(cv - 0.5) < 0.035))
            t[..., :3] = np.where(mu[..., None], rgb(frame), t[..., :3])
            t[..., 4] = np.where(mu, 0, t[..., 4])
        return edge(ctx, t, 0.1)
    return Mat(fn, f"windowed{wall}{frame}{glass}{glow}{cols}{rows}{arch}{mullion}")


def overlay(base: Mat, fn2, key):
    """Post-process a material: fn2(ctx, tile) -> tile."""
    def fn(ctx):
        return fn2(ctx, np.array(base.fn(ctx), dtype=float))
    return Mat(fn, base.key + "|" + key, mode=base.mode, spatial=base.spatial, directional=base.directional,
               density=base.density)


def trimmed(base: Mat, color, width=1, inset=0, glow=0.0):
    """Add a border line (gold filigree etc.) to any material."""
    kc = rgb(color)

    def post(ctx, t):
        if min(ctx.w, ctx.h) < 2 * (inset + width) + 2:
            return t
        ix, iy = px(ctx)
        d = np.minimum(np.minimum(ix, ctx.w - 1 - ix), np.minimum(iy, ctx.h - 1 - iy))
        m = (d >= inset) & (d < inset + width)
        t[..., :3] = np.where(m[..., None], kc, t[..., :3])
        t[..., 4] = np.where(m, glow, t[..., 4])
        return t
    return overlay(base, post, f"trim{color}{width}{inset}{glow}")


def banded(base: Mat, color, every=6, width=1, glow=0.0, horizontal=True):
    kc = rgb(color)

    def post(ctx, t):
        ix, iy = px(ctx)
        c = iy if horizontal else ix
        m = (c % every) < width
        t[..., :3] = np.where(m[..., None], kc, t[..., :3])
        t[..., 4] = np.where(m, glow, t[..., 4])
        return t
    return overlay(base, post, f"band{color}{every}{width}{glow}{horizontal}")


def stamped(base: Mat, bitmap, color, glow=0.0, scale=1, center=True, repeat=False, key=None, offset=(0, 0)):
    """Stamp a boolean bitmap (rows of 0/1 or '#'/' ' strings) onto a material."""
    bm = np.array([[ch not in (" ", ".", 0, "0") for ch in row] for row in bitmap], dtype=bool)
    bm = np.kron(bm, np.ones((scale, scale), dtype=bool))
    kc = rgb(color)

    def post(ctx, t):
        bh, bw = bm.shape
        if repeat:
            ix, iy = px(ctx)
            m = bm[(iy + offset[1]) % bh, (ix + offset[0]) % bw]
        else:
            m = np.zeros((ctx.h, ctx.w), dtype=bool)
            ox = (ctx.w - bw) // 2 + offset[0] if center else offset[0]
            oy = (ctx.h - bh) // 2 + offset[1] if center else offset[1]
            x0, y0 = max(ox, 0), max(oy, 0)
            x1, y1 = min(ox + bw, ctx.w), min(oy + bh, ctx.h)
            if x1 > x0 and y1 > y0:
                m[y0:y1, x0:x1] = bm[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        t[..., :3] = np.where(m[..., None], kc, t[..., :3])
        t[..., 4] = np.where(m, glow, t[..., 4])
        t[..., 3] = np.where(m, 1.0, t[..., 3])
        return t
    return overlay(base, post, key or f"stamp{hash(bm.tobytes())}{color}{glow}{scale}{repeat}{offset}")


def bitmap_cut(bitmap, color, glow=0.0, color2=None, key=None, mode="solid", a=1.0):
    """A plane whose silhouette is a bitmap stretched over the tile (nearest)."""
    bm = np.array([[ch not in (" ", ".", 0, "0") for ch in row] for row in bitmap], dtype=bool)
    k0 = rgb(color)
    k1 = rgb(color2) if color2 is not None else k0

    def fn(ctx):
        bh, bw = bm.shape
        iy = np.clip((ctx.V * bh).astype(int), 0, bh - 1)
        ix = np.clip((ctx.U * bw).astype(int), 0, bw - 1)
        m = bm[iy, ix]
        t = tile(ctx, color, 1, glow)
        t[..., :3] = mix(k0, k1, ctx.V[..., None])
        t[..., 3] = np.where(m, a if mode == "blend" else 1.0, 0.0)
        return t
    return Mat(fn, key or f"bmcut{hash(bm.tobytes())}{color}{glow}{color2}{mode}{a}", directional=True, mode=mode)


def alt(base: Mat, **alts):
    """Material that paints differently per texture skin: alt(base, inscribed=other_mat)."""
    def fn(ctx):
        return (alts.get(ctx.alt) or base).fn(ctx)
    return Mat(fn, base.key + "|alt" + "".join(f"{k}:{v.key}" for k, v in sorted(alts.items())), mode=base.mode,
               spatial=base.spatial or any(a.spatial for a in alts.values()),
               directional=base.directional or any(a.directional for a in alts.values()), density=base.density)
