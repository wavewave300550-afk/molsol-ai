"""Pixel-art material kit (Marketplace-style textures for the race forms).

The older materials evaluated continuous noise per texel, which reads as dirt at
Minecraft resolution.  Here every material is built the way a pixel artist paints
a mob texture:

  * a small hand-picked palette per material (dark -> light, hue-shifted),
  * a light level per texel from the face direction and height (top lit, sides
    medium, bottom dark - like Bedrock entity lighting), with crisp 1-texel rims,
  * quantisation onto the palette with a 4x4 ordered dither (no random noise),
  * motifs and decals placed on exact texels (faces, eyes, seals, glyphs, weaves).

All helpers work on a `Ctx` from kit.tex (one sample per texel; `ctx.pw/ph` give
the face size in texels) and return arrays shaped like the context.
"""
from __future__ import annotations

from typing import Dict, Iterable, Optional, Sequence, Union

import numpy as np

from kit.tex import Ctx, hx

Color = Union[str, Sequence[float], np.ndarray]

BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16.0

# Bedrock-like directional light levels per face (0..1)
FACE_LEVEL = {"up": 0.86, "north": 0.62, "west": 0.56, "east": 0.56, "south": 0.56, "down": 0.24}


def col(c: Color) -> np.ndarray:
    return hx(c) if isinstance(c, str) else np.asarray(c, dtype=float)


def pal(*hexes: Color) -> np.ndarray:
    """Palette (K, 3), ordered dark -> light."""
    return np.array([col(h) for h in hexes])


# ----------------------------------------------------------------------------- texel coordinates

def texel(ctx: Ctx):
    """(ix, iy, W, H): integer texel column/row of every sample (0 = face's left/top) and the face size."""
    W = ctx.pw or max(1, int(np.ceil(ctx.fw * 2 - 1e-6)))
    H = ctx.ph or max(1, int(np.ceil(ctx.fh * 2 - 1e-6)))
    ix = np.clip(np.floor(ctx.s / max(ctx.fw, 1e-9) * W), 0, W - 1).astype(int)
    iy = np.clip(np.floor(ctx.t / max(ctx.fh, 1e-9) * H), 0, H - 1).astype(int)
    return ix, iy, W, H


def side(ctx: Ctx) -> bool:
    return ctx.face in ("north", "south", "east", "west")


# ----------------------------------------------------------------------------- light and quantisation

def level_of(nrm: np.ndarray) -> np.ndarray:
    """Light level for a normal (or (N,3) normals): top bright, bottom dark, front a touch
    brighter than the back - matches FACE_LEVEL on axis-aligned faces."""
    nrm = np.atleast_2d(nrm)
    y, z, x = nrm[:, 1], nrm[:, 2], nrm[:, 0]
    up = np.where(y > 0, 0.86 - 0.56, 0.56 - 0.24) * y          # +0.30 up / -0.32 down
    fb = np.where(z < 0, 0.06, 0.0) * np.abs(z)                   # front +0.06 (the back is what the 3rd-person camera sees)
    return 0.56 + up + fb + 0.0 * x


def light(ctx: Ctx, grad: float = 0.16, base: Optional[Dict[str, float]] = None, ao: float = 0.0,
          real: bool = True) -> np.ndarray:
    """Light level per texel: the face's real direction in the rest pose (rotated cubes are
    lit as they actually sit) + a top-to-bottom gradient on side faces.
    `ao` darkens the texels next to the face's bottom edge (contact shadow)."""
    if real and ctx.wn is not None and base is None:
        lv = float(level_of(ctx.wn)[0])
    else:
        lv = (base or FACE_LEVEL)[ctx.face]
    ix, iy, W, H = texel(ctx)
    out = np.full(ctx.N, lv, dtype=float)
    if side(ctx) and H > 1:
        out += grad * (0.5 - iy / (H - 1))
        if ao:
            out -= ao * (iy >= H - 1)
    return out


def rim(ctx: Ctx, level: np.ndarray, up: float = 0.14, down: float = 0.12, edges: float = 0.0,
        min_size: int = 3) -> np.ndarray:
    """Crisp 1-texel rims: a highlight along the top edge of side faces (and around top
    faces), a darker line along the bottom edge.  `edges` darkens left/right edges."""
    ix, iy, W, H = texel(ctx)
    out = level.copy()
    if side(ctx):
        if H >= min_size:
            out = out + up * (iy == 0) - down * (iy == H - 1)
        if edges and W >= min_size:
            out = out - edges * ((ix == 0) | (ix == W - 1))
    elif ctx.face == "up" and min(W, H) >= min_size:
        border = (ix == 0) | (iy == 0) | (ix == W - 1) | (iy == H - 1)
        out = out + up * 0.6 * border
    return out


def quant(ctx: Ctx, palette: np.ndarray, level: np.ndarray, dither: float = 0.0) -> np.ndarray:
    """Map light levels (0..1) onto the palette with a 4x4 ordered dither between steps."""
    K = len(palette)
    ix, iy, _, _ = texel(ctx)
    d = (BAYER4[iy % 4, ix % 4] - 0.5) * dither
    idx = np.clip(np.round(np.clip(level, 0, 1) * (K - 1) + d), 0, K - 1).astype(int)
    return palette[idx]


def proxy(ctx: Ctx, center, radii, k: float = 1.0) -> np.ndarray:
    """Light level as if the texel lay on an ellipsoid (centre, radii) - stacked boxes then
    read as one rounded form.  Uses the rest-pose position of each texel."""
    p = ctx.wp if ctx.wp is not None else ctx.p
    r = np.asarray(radii, float)
    d = (p - np.asarray(center, float)) / (r * r)
    nn = d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
    base = level_of(nn)
    face = level_of(ctx.wn if ctx.wn is not None else ctx.n)[0]
    return face + (base - face) * k


def cyl(ctx: Ctx, axis_from, axis_to, k: float = 1.0) -> np.ndarray:
    """Light level as if the texel lay on a cylinder around the segment from->to."""
    p = ctx.wp if ctx.wp is not None else ctx.p
    a = np.asarray(axis_from, float)
    b = np.asarray(axis_to, float)
    ab = b - a
    L2 = max(float(ab @ ab), 1e-9)
    t = np.clip(((p - a) @ ab) / L2, 0, 1)
    foot = a + t[:, None] * ab
    nn = p - foot
    nn = nn / np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-9)
    base = level_of(nn)
    face = level_of(ctx.wn if ctx.wn is not None else ctx.n)[0]
    return face + (base - face) * k


def shade(ctx: Ctx, palette: np.ndarray, offset: float = 0.0, grad: float = 0.16, up: float = 0.14,
          down: float = 0.12, edges: float = 0.0, dither: float = 0.0, ao: float = 0.0) -> np.ndarray:
    """The default look: directional light + rims, quantised onto `palette`."""
    lv = rim(ctx, light(ctx, grad, ao=ao) + offset, up, down, edges)
    return quant(ctx, palette, lv, dither)


# ----------------------------------------------------------------------------- masks and stamps

def border(ctx: Ctx, width: int = 1, which: Iterable[str] = ("l", "r", "t", "b")) -> np.ndarray:
    ix, iy, W, H = texel(ctx)
    m = np.zeros(ctx.N, dtype=bool)
    w = set(which)
    if "l" in w:
        m |= ix < width
    if "r" in w:
        m |= ix >= W - width
    if "t" in w:
        m |= iy < width
    if "b" in w:
        m |= iy >= H - width
    return m


def stripes(ctx: Ctx, period: int, width: int = 1, axis: str = "x", phase: int = 0) -> np.ndarray:
    ix, iy, _, _ = texel(ctx)
    a = ix if axis == "x" else iy
    return ((a + phase) % period) < width


def circle(ctx: Ctx, cx: float, cy: float, r: float, ring: Optional[float] = None) -> np.ndarray:
    """Disc (or ring of thickness `ring`) in texel space, centre in texels."""
    ix, iy, _, _ = texel(ctx)
    d = np.hypot(ix + 0.5 - cx, iy + 0.5 - cy)
    return (d <= r) if ring is None else ((d <= r) & (d > r - ring))


def decal(ctx: Ctx, rgb: np.ndarray, pixmap: Sequence[str], colors: Dict[str, Color],
          x0: Union[int, str] = "c", y0: Union[int, str] = "c", glow: Optional[np.ndarray] = None,
          glow_chars: str = "", glow_level: float = 0.8, mirror: bool = False):
    """Stamp an ASCII pixel map onto the face.  '.' or ' ' = transparent.
    x0/y0: top-left texel, or "c" to centre.  Returns (rgb, glow)."""
    ix, iy, W, H = texel(ctx)
    h = len(pixmap)
    w = max(len(r) for r in pixmap)
    ox = (W - w) // 2 if x0 == "c" else int(x0)
    oy = (H - h) // 2 if y0 == "c" else int(y0)
    out = rgb.copy()
    g = np.zeros(ctx.N) if glow is None else glow.copy()
    lx = ix - ox
    ly = iy - oy
    inside = (lx >= 0) & (lx < w) & (ly >= 0) & (ly < h)
    if not inside.any():
        return out, g
    cmap = {k: col(v) for k, v in colors.items()}
    for k in np.nonzero(inside)[0]:
        row = pixmap[ly[k]]
        cx = (w - 1 - lx[k]) if mirror else lx[k]
        ch = row[cx] if cx < len(row) else "."
        if ch in (".", " "):
            continue
        out[k] = cmap[ch]
        if ch in glow_chars:
            g[k] = glow_level
    return out, g


def tile(ctx: Ctx, pixmap: Sequence[str], ox: int = 0, oy: int = 0) -> np.ndarray:
    """Repeat an ASCII tile over the face; returns the character per texel (object array)."""
    ix, iy, _, _ = texel(ctx)
    h = len(pixmap)
    w = len(pixmap[0])
    rows = np.array([list(r.ljust(w, ".")) for r in pixmap])
    return rows[(iy + oy) % h, (ix + ox) % w]


def hash01(ctx: Ctx, seed: int = 0) -> np.ndarray:
    """Deterministic per-texel value in [0,1) (for sparse sprinkles only - never as noise)."""
    ix, iy, _, _ = texel(ctx)
    v = np.sin((ix * 12.9898 + iy * 78.233 + (ctx.seed + seed) * 37.719)) * 43758.5453
    return v - np.floor(v)


def mix(a: Color, b: Color, t: float) -> np.ndarray:
    return col(a) * (1 - t) + col(b) * t


# ----------------------------------------------------------------------------- premium painting (v1.5)
#
# The Marketplace look of races 007-009: continuous gradients (no quantisation noise), light
# taken from the smooth form the boxes approximate (proxy / cyl), soft ambient occlusion where
# parts meet, crisp rims, and glow designed as patterns (lines, spots, veins) that fade out.

def smooth_ramp(palette: np.ndarray, level) -> np.ndarray:
    """Continuous colour along a dark -> light palette for light levels 0..1 (no dither)."""
    P = np.asarray(palette, float)
    K = len(P)
    x = np.clip(np.asarray(level, float), 0, 1) * (K - 1)
    i0 = np.minimum(np.floor(x).astype(int), K - 1)
    i1 = np.minimum(i0 + 1, K - 1)
    t = (x - i0)[:, None]
    return P[i0] * (1 - t) + P[i1] * t


def _pos(ctx: Ctx) -> np.ndarray:
    return ctx.wp if ctx.wp is not None else ctx.p


def ao_near(ctx: Ctx, points, radius: float, strength: float = 0.25) -> np.ndarray:
    """Soft ambient occlusion around rest-pose points (joints, where parts meet): a level
    offset (<= 0) that fades quadratically to 0 at `radius` model units."""
    p = _pos(ctx)
    out = np.zeros(ctx.N)
    for c in points:
        d = np.linalg.norm(p - np.asarray(c, float), axis=1)
        out -= strength * np.clip(1 - d / radius, 0, 1) ** 2
    return out


def ao_below(ctx: Ctx, y: float, depth: float, strength: float = 0.22) -> np.ndarray:
    """Darken texels just below height y (the shadow under a cap, a crest, a plate edge)."""
    p = _pos(ctx)
    d = y - p[:, 1]
    return -strength * np.clip(1 - d / depth, 0, 1) * (d >= 0)


def soft_shade(ctx: Ctx, palette: np.ndarray, offset: float = 0.0, ellipsoid=None, cylinder=None, k: float = 0.85,
               grad: float = 0.10, up: float = 0.08, down: float = 0.07, extra=None) -> np.ndarray:
    """The premium default: light from the smooth form (ellipsoid=(center, radii) or
    cylinder=(from, to)), a gentle top-to-bottom gradient, soft rims, optional extra level
    offsets (ao_near / ao_below / patterns), mapped continuously onto `palette`.
    For stacked forms that must read as ONE surface (lathe domes, sweeps) pass up=0, down=0:
    per-box rims would stripe them."""
    if ellipsoid is not None:
        lv = proxy(ctx, ellipsoid[0], ellipsoid[1], k)
    elif cylinder is not None:
        lv = cyl(ctx, cylinder[0], cylinder[1], k)
    else:
        lv = light(ctx, grad)
    lv = rim(ctx, lv + offset, up, down)
    if extra is not None:
        lv = lv + extra
    return smooth_ramp(palette, lv)


def glow_spot(ctx: Ctx, centers, radius: float, core: float = 0.35) -> np.ndarray:
    """Emissive strength 0..1 of round glowing spots at rest-pose positions (photophores,
    ocelli, spore pits): 1 inside core*radius, easing to 0 at `radius`."""
    p = _pos(ctx)
    g = np.zeros(ctx.N)
    for c in centers:
        d = np.linalg.norm(p - np.asarray(c, float), axis=1) / max(radius, 1e-6)
        t = np.clip((1 - d) / max(1 - core, 1e-6), 0, 1)
        g = np.maximum(g, t * t * (3 - 2 * t))
    return g


def _seg_dist(p: np.ndarray, a, b) -> np.ndarray:
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-9), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def glow_line(ctx: Ctx, pts, width: float, core: float = 0.3) -> np.ndarray:
    """Emissive strength along a rest-pose polyline (veins of light, display lines, cracks):
    1 within core*width of the line, easing to 0 at `width`."""
    p = _pos(ctx)
    d = np.full(ctx.N, np.inf)
    for a, b in zip(pts[:-1], pts[1:]):
        d = np.minimum(d, _seg_dist(p, a, b))
    t = np.clip((1 - d / max(width, 1e-6)) / max(1 - core, 1e-6), 0, 1)
    return t * t * (3 - 2 * t)


def vane(ctx: Ctx, width_at=0.45, tip: float = 0.97, base: float = 0.12, rachis: float = 0.10, barb: float = 2.5,
         notch: float = 0.0):
    """A feather on a box that runs along its local +Z (feather_fan / sweep vanes): returns
    (alpha, level_offset).  The silhouette is widest at `width_at` of the length and comes to a
    point at `tip`; a light rachis runs down the middle; barbs are soft diagonal grooves every
    `barb` texels; notch > 0 cuts a few gaps in the trailing edge (worn primaries)."""
    u = ctx.local[:, 0] * 2 - 1           # -1..1 across
    v = ctx.local[:, 2]                   # 0 base .. 1 tip
    prof = np.where(v < width_at, base + (1 - base) * np.sin(np.clip(v / width_at, 0, 1) * np.pi / 2),
                    np.cos(np.clip((v - width_at) / max(tip - width_at, 1e-6), 0, 1) * np.pi / 2))
    alpha = (np.abs(u) <= prof * 0.98) & (v <= tip)
    if notch > 0:
        ix, iy, _, _ = texel(ctx)
        alpha &= ~((u > 0.55) & (((iy + 3 * ix) % 9) < 9 * notch))
    ix, iy, _, _ = texel(ctx)
    groove = ((ix + iy * np.sign(u + 1e-6)) % max(barb, 1.0)) < 1.0
    lvl = 0.10 * (np.abs(u) < rachis) - 0.05 * groove - 0.10 * np.clip(np.abs(u) / np.maximum(prof, 1e-3), 0, 1) ** 4
    return alpha.astype(float), lvl


def scales(ctx: Ctx, size: int = 3, depth: float = 0.10) -> np.ndarray:
    """Overlapping rounded scales in texel space (rows offset by half a scale): a level
    offset with a light upper edge and a shadowed lower rim on each scale."""
    ix, iy, _, _ = texel(ctx)
    row = iy // size
    x = (ix + (row % 2) * (size // 2)) % size
    y = iy % size
    r = np.hypot(x - (size - 1) / 2, y) / max(size * 0.62, 1e-6)
    return depth * (0.6 - np.clip(r, 0, 1) * 1.4) * (y < size)


def veins(ctx: Ctx, seed: int = 0, n: int = 4, width: float = 0.7, branch: int = 2) -> np.ndarray:
    """Branching hairline veins / cracks in face texel space (deterministic per seed):
    returns 0..1 strength (use as glow for light-cracks, or as a darkening mask)."""
    ix, iy, W, H = texel(ctx)
    rng = np.random.default_rng((ctx.seed * 7919 + seed) & 0xFFFFFFFF)
    P = np.column_stack([ix + 0.5, iy + 0.5]).astype(float)
    d = np.full(ctx.N, np.inf)

    def walk(x, y, ang, steps, depth):
        nonlocal d
        for _ in range(steps):
            nx, ny = x + np.cos(ang) * 2.2, y + np.sin(ang) * 2.2
            a, b = np.array([x, y]), np.array([nx, ny])
            ab = b - a
            t = np.clip(((P - a) @ ab) / max(float(ab @ ab), 1e-9), 0, 1)
            d = np.minimum(d, np.linalg.norm(P - (a + t[:, None] * ab), axis=1))
            x, y = nx, ny
            ang += rng.uniform(-0.6, 0.6)
            if depth < branch and rng.random() < 0.18:
                walk(x, y, ang + rng.choice([-1.0, 1.0]) * rng.uniform(0.6, 1.1), max(2, steps // 2), depth + 1)
    for _ in range(n):
        walk(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0, 2 * np.pi), int(max(W, H) / 2.2) + 2, 0)
    return np.clip(1 - d / max(width, 1e-6), 0, 1)
