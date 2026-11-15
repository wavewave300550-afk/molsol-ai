"""Vectorised 3-D procedural noise (numpy).

Every function takes an (N, 3) float array of points and returns an (N,)
array.  Textures are painted from the *3-D rest-pose position* of each texel,
so patterns flow continuously across faces and cubes ("solid texturing").
"""
from __future__ import annotations

import numpy as np

_U32 = np.uint32


def _hash3(ix: np.ndarray, iy: np.ndarray, iz: np.ndarray, seed: int) -> np.ndarray:
    """Integer lattice hash -> float in [0, 1)."""
    h = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263
         + iz.astype(np.int64) * 2147483647 + seed * 974634713) & 0xFFFFFFFF
    h = h.astype(np.uint64)
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF).astype(np.float64) / float(0x1000000)


def _fade(t: np.ndarray) -> np.ndarray:
    return t * t * t * (t * (t * 6 - 15) + 10)


def value(p: np.ndarray, freq: float = 1.0, seed: int = 0) -> np.ndarray:
    """Smooth value noise in [0, 1]."""
    q = p * freq
    i = np.floor(q)
    f = q - i
    ix, iy, iz = i[:, 0].astype(np.int64), i[:, 1].astype(np.int64), i[:, 2].astype(np.int64)
    u = _fade(f)
    acc = np.zeros(len(p))
    for dx in (0, 1):
        wx = u[:, 0] if dx else 1 - u[:, 0]
        for dy in (0, 1):
            wy = u[:, 1] if dy else 1 - u[:, 1]
            for dz in (0, 1):
                wz = u[:, 2] if dz else 1 - u[:, 2]
                acc += wx * wy * wz * _hash3(ix + dx, iy + dy, iz + dz, seed)
    return acc


def fbm(p: np.ndarray, freq: float = 1.0, octaves: int = 4, seed: int = 0,
        lac: float = 2.03, gain: float = 0.5) -> np.ndarray:
    """Fractal sum of value noise, normalised to roughly [0, 1]."""
    total = np.zeros(len(p))
    amp, norm, f = 1.0, 0.0, freq
    for o in range(octaves):
        total += amp * value(p, f, seed + o * 31)
        norm += amp
        amp *= gain
        f *= lac
    return total / norm


def ridged(p: np.ndarray, freq: float = 1.0, octaves: int = 3, seed: int = 0) -> np.ndarray:
    """Ridged noise: thin bright ridges (veins, cracks) in [0, 1]."""
    total = np.zeros(len(p))
    amp, norm, f = 1.0, 0.0, freq
    for o in range(octaves):
        n = value(p, f, seed + o * 17) * 2 - 1
        total += amp * (1 - np.abs(n)) ** 2
        norm += amp
        amp *= 0.5
        f *= 2.1
    return total / norm


def worley(p: np.ndarray, freq: float = 1.0, seed: int = 0, jitter: float = 0.9):
    """Cellular noise.  Returns (F1, F2, cell_id) where cell_id in [0,1)."""
    q = p * freq
    i = np.floor(q).astype(np.int64)
    f = q - i
    n = len(p)
    f1 = np.full(n, 9.0)
    f2 = np.full(n, 9.0)
    cid = np.zeros(n)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                cx, cy, cz = i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz
                ox = _hash3(cx, cy, cz, seed) * jitter + (1 - jitter) / 2
                oy = _hash3(cx, cy, cz, seed + 7) * jitter + (1 - jitter) / 2
                oz = _hash3(cx, cy, cz, seed + 13) * jitter + (1 - jitter) / 2
                d = np.sqrt((dx + ox - f[:, 0]) ** 2 + (dy + oy - f[:, 1]) ** 2 + (dz + oz - f[:, 2]) ** 2)
                closer = d < f1
                f2 = np.where(closer, f1, np.minimum(f2, d))
                cid = np.where(closer, _hash3(cx, cy, cz, seed + 99), cid)
                f1 = np.where(closer, d, f1)
    return f1, f2, cid


def warp(p: np.ndarray, amount: float, freq: float, seed: int = 0) -> np.ndarray:
    """Domain warp: displace points by low-frequency noise."""
    d = np.stack([fbm(p, freq, 2, seed + k * 5) - 0.5 for k in range(3)], axis=1)
    return p + d * 2 * amount


def hash_points(p: np.ndarray, cell: float, seed: int = 0) -> np.ndarray:
    """Per-cell random value (blocky speckle) in [0,1)."""
    i = np.floor(p / cell).astype(np.int64)
    return _hash3(i[:, 0], i[:, 1], i[:, 2], seed)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)
