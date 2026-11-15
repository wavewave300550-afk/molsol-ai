"""Atlas painter: evaluates procedural materials for every texel of every face.

A material is a callable  mat(ctx) -> (rgb (N,3) floats 0..1, alpha (N,), glow (N,))
  * rgb    - albedo colour
  * alpha  - coverage (only meaningful for cutout cubes; 0 = hole)
  * glow   - emissive strength 0..1 (only meaningful for solid cubes; encoded
             in the texture alpha channel for the `entity_emissive_alpha`
             material: alpha = 1 - glow)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

import numpy as np
from PIL import Image

from .geo import Model, face_frame, NORMALS

Result = Tuple[np.ndarray, np.ndarray, np.ndarray]


def hx(s: str) -> np.ndarray:
    s = s.lstrip("#")
    return np.array([int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def lerp(a, b, t):
    t = np.asarray(t)
    if t.ndim == 1:
        t = t[:, None]
    return a * (1 - t) + b * t


@dataclass
class Ctx:
    p: np.ndarray          # (N,3) texel centre, JSON model space (rest pose)
    n: np.ndarray          # (3,) face normal
    face: str
    s: np.ndarray          # (N,) distance along u in model units (0..fw)
    t: np.ndarray          # (N,) distance along v in model units (0..fh)
    fw: float
    fh: float
    local: np.ndarray      # (N,3) position inside the cube, 0..1 per axis
    origin: np.ndarray
    size: np.ndarray
    seed: int
    params: dict
    pw: int = 0            # face width / height in texels (for pixel-exact painting, kit/pixel.py)
    ph: int = 0
    wp: Optional[np.ndarray] = None   # (N,3) texel positions in the rest pose (cube + bone rotations applied)
    wn: Optional[np.ndarray] = None   # (3,) the face's real normal in the rest pose

    @property
    def N(self) -> int:
        return len(self.s)

    def ones(self) -> np.ndarray:
        return np.ones(self.N)

    def zeros(self) -> np.ndarray:
        return np.zeros(self.N)

    @property
    def edge(self) -> np.ndarray:
        """Distance (units) to the nearest face edge."""
        return np.minimum(np.minimum(self.s, self.fw - self.s), np.minimum(self.t, self.fh - self.t))


Material = Callable[[Ctx], Result]


def solid(rgb: np.ndarray, ctx: Ctx, glow=None, alpha=None) -> Result:
    rgb = np.broadcast_to(rgb, (ctx.N, 3)).astype(float)
    return rgb, (ctx.ones() if alpha is None else alpha), (ctx.zeros() if glow is None else glow)


def paint(model: Model, materials: Dict[str, Material], params: Optional[dict] = None,
          supersample: int = 1) -> Image.Image:
    """Paint the full atlas for `model` (after model.pack())."""
    params = params or {}
    W, H = model.tex_w, model.tex_h
    from .render import bone_matrices          # local import: render does not depend on tex
    from .geo import rot_matrix
    rest = bone_matrices(model, None)
    img = np.zeros((H, W, 4), dtype=np.float64)
    filled = np.zeros((H, W), dtype=bool)
    for bn in model.order:
        for c in model.bones[bn].cubes:
            mat = materials.get(c.mat)
            if mat is None:
                raise KeyError(f"material {c.mat!r} (bone {bn}) not defined")
            for f in c.emitted_faces():
                u0, v0, pw, ph = c.uv[f]
                corner, du, dv, fw, fh = face_frame(f, c.origin, c.size)
                ss = supersample
                ix, iy = np.meshgrid(np.arange(pw * ss), np.arange(ph * ss))
                a = (ix.ravel() + 0.5) / (pw * ss)
                b = (iy.ravel() + 0.5) / (ph * ss)
                p = corner[None, :] + a[:, None] * du[None, :] + b[:, None] * dv[None, :]
                size = np.maximum(np.array(c.size, dtype=float), 1e-6)
                local = (p - np.array(c.origin)) / size
                # where this texel really is once the cube's and its bones' rest rotations apply
                Rc = rot_matrix(c.rot) if c.rot is not None else np.eye(3)
                pc = np.array(c.pivot if c.pivot is not None else c.origin, dtype=float)
                pr = (p - pc) @ Rc.T + pc
                M = rest[bn]
                wp = pr @ M[:3, :3].T + M[:3, 3]
                wn = M[:3, :3] @ (Rc @ np.array(NORMALS[f]))
                wn = wn / max(np.linalg.norm(wn), 1e-9)
                ctx = Ctx(p=p, n=np.array(NORMALS[f]), face=f, s=a * fw, t=b * fh, fw=fw, fh=fh,
                          local=np.clip(local, 0, 1), origin=np.array(c.origin), size=np.array(c.size),
                          seed=c.seed, params=params, pw=pw * ss, ph=ph * ss, wp=wp, wn=wn)
                rgb, alpha, glow = mat(ctx)
                rgb = np.clip(np.broadcast_to(np.asarray(rgb, dtype=float), (ctx.N, 3)), 0, 1).reshape(ph * ss, pw * ss, 3)
                alpha = np.clip(np.broadcast_to(alpha, (ctx.N,)), 0, 1).reshape(ph * ss, pw * ss)
                glow = np.clip(np.broadcast_to(glow, (ctx.N,)), 0, 1).reshape(ph * ss, pw * ss)
                if ss > 1:
                    rgb = rgb.reshape(ph, ss, pw, ss, 3).mean(axis=(1, 3))
                    alpha = alpha.reshape(ph, ss, pw, ss).mean(axis=(1, 3))
                    glow = glow.reshape(ph, ss, pw, ss).max(axis=(1, 3))
                if c.cutout:
                    out_a = (alpha >= 0.5).astype(float)
                else:
                    # emissive-alpha encoding: 1 = unlit-normal, lower = glowing.
                    out_a = 1.0 - glow * 0.92
                    out_a = np.where(glow > 0.02, np.minimum(out_a, 0.985), 1.0)
                tile = np.concatenate([rgb, out_a[..., None]], axis=2)
                img[v0:v0 + ph, u0:u0 + pw] = tile
                filled[v0:v0 + ph, u0:u0 + pw] = True
    # bleed colours into the 1px padding (prevents seams); keep padding alpha 0
    out = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
    bleed = out.copy()
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        src = np.roll(np.roll(out, dy, axis=0), dx, axis=1)
        srcf = np.roll(np.roll(filled, dy, axis=0), dx, axis=1)
        m = (~filled) & srcf
        bleed[m, :3] = src[m, :3]
        bleed[m, 3] = src[m, 3]
    return Image.fromarray(bleed, "RGBA")


# ----------------------------------------------------------------------------- helpers

def shade_ao(ctx: Ctx, rgb: np.ndarray, amount: float = 0.18, width: float = 0.9) -> np.ndarray:
    """Darken near face edges (fake ambient occlusion / bevel)."""
    e = np.clip(ctx.edge / width, 0, 1)
    k = 1 - amount * (1 - e) ** 2
    return rgb * k[:, None]


def top_light(ctx: Ctx, rgb: np.ndarray, amount: float = 0.12) -> np.ndarray:
    """Slight vertical gradient: lighter towards the top of side faces."""
    if ctx.face in ("up",):
        return rgb * (1 + amount)
    if ctx.face == "down":
        return rgb * (1 - amount * 1.5)
    k = 1 + amount * (0.5 - ctx.t / max(ctx.fh, 1e-6))
    return rgb * k[:, None]
