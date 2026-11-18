"""
paint.py - procedural texture painting for model faces.

A painter is `fn(ctx: FaceCtx) -> float32 array (h, w, 4)` with values 0..1.
Painters get per-texel face coordinates *and* the 3D layout-space position of
every texel, so noise, grime and wear stay continuous across neighbouring
faces and cubes instead of restarting on every rectangle.

Everything is deterministic: seeds derive from model / bone / face names.
"""
from __future__ import annotations

import math
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

import numpy as np

Color = Tuple[float, float, float, float]


def rgba(h: str, a: float = 1.0) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a], dtype=np.float32)


def as_col(c) -> np.ndarray:
    return rgba(c) if isinstance(c, str) else np.asarray(c, dtype=np.float32)


class FaceCtx:
    """Everything a painter may want to know about one face rectangle."""

    def __init__(self, model, bone, cube, face: str, w: int, h: int, seed: int):
        self.model, self.bone, self.cube, self.face = model, bone, cube, face
        self.w, self.h, self.seed = w, h, seed
        self.rng = np.random.default_rng(seed)
        ys, xs = np.mgrid[0:h, 0:w]
        self.X, self.Y = xs, ys
        self.U = (xs + 0.5) / w
        self.V = (ys + 0.5) / h
        tl, tr, bl = (np.array(p, dtype=np.float32) for p in cube.corners(face))
        self.P = tl + (tr - tl) * self.U[..., None] + (bl - tl) * self.V[..., None]
        self.size_u, self.size_v = cube.face_dims(face)

    @property
    def height(self) -> np.ndarray:
        """Layout-space Y of each texel (model units)."""
        return self.P[..., 1]

    def fill(self, c) -> np.ndarray:
        out = np.empty((self.h, self.w, 4), dtype=np.float32)
        out[:] = as_col(c)
        return out

    def edge_dist(self) -> np.ndarray:
        """Distance in texels to the nearest rectangle edge (0 on the border)."""
        return np.minimum(np.minimum(self.X, self.w - 1 - self.X), np.minimum(self.Y, self.h - 1 - self.Y))


# --------------------------------------------------------------------------- noise

def _hash(ix, iy, iz, seed: int) -> np.ndarray:
    """Integer lattice -> [0,1) (vectorised)."""
    n = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263 +
         iz.astype(np.int64) * 2147483647 + int(seed) * 1274126177) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 1103515245 & 0xFFFFFFFF
    n = n ^ (n >> 16)
    return (n & 0xFFFFFF).astype(np.float32) / float(0x1000000)


def white(ctx: FaceCtx, salt: int = 0) -> np.ndarray:
    """Per-texel white noise in [0,1)."""
    return _hash(ctx.X, ctx.Y, np.zeros_like(ctx.X), ctx.seed + salt * 7919)


def noise3(P: np.ndarray, freq: float, seed: int) -> np.ndarray:
    """Trilinear value noise in [0,1] over 3D positions P (..., 3)."""
    p = P * freq
    i = np.floor(p).astype(np.int64)
    f = p - i
    f = f * f * (3 - 2 * f)
    out = np.zeros(P.shape[:-1], dtype=np.float32)
    for dx in (0, 1):
        wx = f[..., 0] if dx else 1 - f[..., 0]
        for dy in (0, 1):
            wy = f[..., 1] if dy else 1 - f[..., 1]
            for dz in (0, 1):
                wz = f[..., 2] if dz else 1 - f[..., 2]
                out += wx * wy * wz * _hash(i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz, seed)
    return out


def fbm(ctx_or_P, freq: float = 0.25, seed: int = 0, octaves: int = 3, gain: float = 0.5) -> np.ndarray:
    """Fractal value noise in [0,1], continuous in model space."""
    P = ctx_or_P.P if isinstance(ctx_or_P, FaceCtx) else ctx_or_P
    total = np.zeros(P.shape[:-1], dtype=np.float32)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        total += amp * noise3(P, freq * (2 ** o), seed + o * 101)
        norm += amp
        amp *= gain
    return total / norm


# --------------------------------------------------------------------------- colour ops

def mix(a, b, t) -> np.ndarray:
    a, b = as_col(a), as_col(b)
    t = np.clip(np.asarray(t, dtype=np.float32), 0, 1)
    if t.ndim:
        t = t[..., None]
    return a * (1 - t) + b * t


def ramp(t: np.ndarray, stops: Sequence) -> np.ndarray:
    """Piecewise-linear colour ramp; stops are colours spread evenly over t in [0,1]."""
    cols = np.stack([as_col(c) for c in stops])
    t = np.clip(t, 0, 1) * (len(cols) - 1)
    i = np.clip(np.floor(t).astype(int), 0, len(cols) - 2)
    f = (t - i)[..., None]
    return cols[i] * (1 - f) + cols[i + 1] * f


def steps(t: np.ndarray, n: int) -> np.ndarray:
    """Quantise to n flat steps - keeps a hand-pixelled look."""
    return np.floor(np.clip(t, 0, 0.9999) * n) / max(1, n - 1)


def shade(img: np.ndarray, k) -> np.ndarray:
    """k>0 lightens towards white, k<0 darkens towards black (per texel or scalar)."""
    k = np.asarray(k, dtype=np.float32)
    if k.ndim:
        k = k[..., None]
    out = img.copy()
    rgb = out[..., :3]
    out[..., :3] = np.where(k >= 0, rgb + (1 - rgb) * k, rgb * (1 + k))
    return out


def over(base: np.ndarray, col, mask) -> np.ndarray:
    """Blend a flat colour over `base` through `mask` (0..1)."""
    c = as_col(col)
    m = np.clip(np.asarray(mask, dtype=np.float32), 0, 1)[..., None] * c[3]
    out = base.copy()
    out[..., :3] = base[..., :3] * (1 - m) + c[:3] * m
    out[..., 3] = np.maximum(base[..., 3], m[..., 0])
    return out


def set_alpha(img: np.ndarray, a) -> np.ndarray:
    out = img.copy()
    out[..., 3] = a
    return out


# --------------------------------------------------------------------------- structure

def bevel(ctx: FaceCtx, img: np.ndarray, light: float = 0.16, dark: float = 0.22, width: int = 1) -> np.ndarray:
    """Raised-panel shading: lit top/left rim, shadowed bottom/right rim."""
    if min(ctx.w, ctx.h) < 3:
        return img
    k = np.zeros((ctx.h, ctx.w), dtype=np.float32)
    k[(ctx.Y < width) | (ctx.X < width)] = light
    k[(ctx.Y >= ctx.h - width) | (ctx.X >= ctx.w - width)] = -dark
    return shade(img, k)


def outline(ctx: FaceCtx, img: np.ndarray, dark: float = 0.3) -> np.ndarray:
    if min(ctx.w, ctx.h) < 3:
        return img
    return shade(img, np.where(ctx.edge_dist() == 0, -dark, 0.0))


def crack_mask(ctx: FaceCtx, count: float = 1.0, salt: int = 0, branch: float = 0.25) -> np.ndarray:
    """Hairline fractures: random walks seeded on the face. Returns a 0/1 mask."""
    rng = np.random.default_rng(ctx.seed + 9001 + salt)
    m = np.zeros((ctx.h, ctx.w), dtype=np.float32)
    n = int(count) + (1 if rng.random() < (count - int(count)) else 0)
    for _ in range(n):
        x, y = rng.uniform(0, ctx.w), rng.uniform(0, ctx.h)
        ang = rng.uniform(0, 2 * math.pi)
        for _ in range(int(rng.uniform(0.5, 1.4) * max(ctx.w, ctx.h))):
            xi, yi = int(x), int(y)
            if not (0 <= xi < ctx.w and 0 <= yi < ctx.h):
                break
            m[yi, xi] = 1
            ang += rng.normal(0, 0.45)
            if rng.random() < branch * 0.1:
                ang += rng.choice([-1.0, 1.0]) * 1.1
            x += math.cos(ang)
            y += math.sin(ang)
    return m


def rivets(ctx: FaceCtx, spacing: int = 4, inset: int = 1) -> np.ndarray:
    """Mask of evenly spaced rivet heads along the face border."""
    m = np.zeros((ctx.h, ctx.w), dtype=np.float32)
    if ctx.w < 2 * inset + 2 or ctx.h < 2 * inset + 2:
        return m
    on_x = ((ctx.X - inset) % spacing == 0) & (ctx.X >= inset) & (ctx.X < ctx.w - inset)
    on_y = ((ctx.Y - inset) % spacing == 0) & (ctx.Y >= inset) & (ctx.Y < ctx.h - inset)
    m[(on_x & ((ctx.Y == inset) | (ctx.Y == ctx.h - 1 - inset))) |
      (on_y & ((ctx.X == inset) | (ctx.X == ctx.w - 1 - inset)))] = 1
    return m


def stripes(ctx: FaceCtx, period: float, width: float, axis: str = "v", offset: float = 0.0) -> np.ndarray:
    """Band mask; axis 'u'/'v' in texels, or 'x'/'y'/'z' in model units (continuous across faces)."""
    k = {"u": ctx.X, "v": ctx.Y, "x": ctx.P[..., 0], "y": ctx.P[..., 1], "z": ctx.P[..., 2]}[axis]
    return (np.mod(k + offset, period) < width).astype(np.float32)


def grime(ctx: FaceCtx, img: np.ndarray, low: float = 0.0, high: float = 48.0, amount: float = 0.25,
          seed: int = 77) -> np.ndarray:
    """Dirt gathering towards the ground (model-space height) broken up with noise."""
    t = 1 - np.clip((ctx.height - low) / max(1e-6, high - low), 0, 1)
    n = fbm(ctx, 0.3, seed, 2)
    return shade(img, -amount * t * (0.6 + 0.8 * n))


def face_light(ctx: FaceCtx, img: np.ndarray, up: float = 0.06, down: float = -0.18, side: float = 0.0) -> np.ndarray:
    """Subtle baked directional tint so undersides read darker than tops."""
    k = up if ctx.face == "up" else down if ctx.face == "down" else side
    return shade(img, k) if k else img


# --------------------------------------------------------------------------- generic materials

def surface(palette: Sequence, *, freq: float = 0.22, seed: int = 1, octaves: int = 3, quant: int = 0,
            speckle: float = 0.0, speckle_col=None, bevel_k: Tuple[float, float] = (0.14, 0.2),
            grime_k: float = 0.0, grime_range: Tuple[float, float] = (0.0, 48.0),
            cracks: float = 0.0, crack_col="#2a1a18", contrast: float = 1.0,
            edge_dark: float = 0.0) -> Callable[[FaceCtx], np.ndarray]:
    """General weathered solid: noise-driven palette ramp + optional speckle, cracks, bevel, grime."""
    def painter(ctx: FaceCtx) -> np.ndarray:
        t = fbm(ctx, freq, seed, octaves)
        t = np.clip((t - 0.5) * contrast + 0.5 + (white(ctx) - 0.5) * 0.08, 0, 1)
        if quant:
            t = steps(t, quant)
        img = ramp(t, palette)
        if speckle:
            img = over(img, speckle_col or palette[-1], (white(ctx, 3) < speckle).astype(np.float32))
        if cracks:
            img = over(img, crack_col, crack_mask(ctx, cracks * ctx.w * ctx.h / 256.0))
        if grime_k:
            img = grime(ctx, img, grime_range[0], grime_range[1], grime_k)
        if bevel_k:
            img = bevel(ctx, img, bevel_k[0], bevel_k[1])
        if edge_dark:
            img = outline(ctx, img, edge_dark)
        return face_light(ctx, img)
    return painter


def flat(col, alpha: float = 1.0) -> Callable[[FaceCtx], np.ndarray]:
    c = as_col(col).copy()
    c[3] = alpha
    return lambda ctx: ctx.fill(c)


def glow(core, rim, alpha: float = 0.16, pulse_axis: Optional[str] = None) -> Callable[[FaceCtx], np.ndarray]:
    """Emissive panel for `entity_emissive_alpha`: low alpha = strongly self-lit."""
    def painter(ctx: FaceCtx) -> np.ndarray:
        d = np.sqrt((ctx.U - 0.5) ** 2 + (ctx.V - 0.5) ** 2) * 2
        img = mix(core, rim, np.clip(d, 0, 1))
        img[..., 3] = alpha + (1 - alpha) * 0.35 * np.clip(d, 0, 1)
        return img
    return painter
