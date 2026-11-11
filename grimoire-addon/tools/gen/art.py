"""Supersampled vector painting helpers (Pillow) producing RGBA float arrays with emissive masks.

Art layers:
  base  - RGB surface colour
  glow  - 0..1 emissive mask; for entity_emissive_alpha final alpha = 255 * (1 - glow)
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from .texkit import noise2


class Art:
    def __init__(self, w, h, ss=4, bg=(0, 0, 0)):
        self.w, self.h, self.ss = w, h, ss
        self.W, self.H = w * ss, h * ss
        self.base = Image.new('RGB', (self.W, self.H), bg)
        self.glow = Image.new('L', (self.W, self.H), 0)
        self.alpha = Image.new('L', (self.W, self.H), 255)
        self.d = ImageDraw.Draw(self.base)
        self.g = ImageDraw.Draw(self.glow)
        self.a = ImageDraw.Draw(self.alpha)

    # coordinates are given in final-texture pixels (floats); converted to supersampled space
    def S(self, *v):
        return [x * self.ss for x in v]

    def grain(self, color, amount=0.25, scale=1.5, seed=1):
        n = noise2(self.W, self.H, seed, scale * self.ss, 4)
        c = np.array(color, np.float32)
        arr = c[None, None, :] * (1 - amount / 2 + n[..., None] * amount)
        self.base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')
        self.d = ImageDraw.Draw(self.base)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=1.0, glow=None):
        box = self.S(x0, y0, x1, y1)
        self.d.rectangle(box, fill=fill, outline=outline, width=max(1, int(width * self.ss)) if outline else 0)
        if glow is not None:
            self.g.rectangle(box, fill=int(glow * 255) if fill else None,
                             outline=int(glow * 255) if outline else None,
                             width=max(1, int(width * self.ss)) if outline else 0)

    def circle(self, cx, cy, r, fill=None, outline=None, width=1.0, glow=None):
        box = self.S(cx - r, cy - r, cx + r, cy + r)
        self.d.ellipse(box, fill=fill, outline=outline, width=max(1, int(width * self.ss)) if outline else 0)
        if glow is not None:
            self.g.ellipse(box, fill=int(glow * 255) if fill else None, outline=int(glow * 255) if outline else None,
                           width=max(1, int(width * self.ss)) if outline else 0)

    def poly(self, pts, fill=None, outline=None, width=1.0, glow=None):
        P = [tuple(self.S(x, y)) for x, y in pts]
        self.d.polygon(P, fill=fill, outline=outline)
        if outline and width > 1:
            self.d.line(P + [P[0]], fill=outline, width=int(width * self.ss), joint='curve')
        if glow is not None:
            self.g.polygon(P, fill=int(glow * 255) if fill else None, outline=int(glow * 255) if outline else None)
            if outline and width > 1:
                self.g.line(P + [P[0]], fill=int(glow * 255), width=int(width * self.ss))

    def line(self, pts, color, width=1.0, glow=None):
        P = [tuple(self.S(x, y)) for x, y in pts]
        self.d.line(P, fill=color, width=max(1, int(width * self.ss)), joint='curve')
        if glow is not None:
            self.g.line(P, fill=int(glow * 255), width=max(1, int(width * self.ss)))

    def ring_ticks(self, cx, cy, r0, r1, n, color, width=0.6, glow=None, start=0.0):
        for i in range(n):
            a = math.radians(start + 360 * i / n)
            self.line([(cx + math.cos(a) * r0, cy + math.sin(a) * r0), (cx + math.cos(a) * r1, cy + math.sin(a) * r1)],
                      color, width, glow)

    def radial_glow(self, cx, cy, r, color, strength=1.0, glow=0.0):
        """Additive soft halo into base (and optional glow mask)."""
        arr = np.asarray(self.base, np.float32)
        y, x = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
        d = np.sqrt((x - cx * self.ss) ** 2 + (y - cy * self.ss) ** 2) / (r * self.ss)
        k = np.clip(1 - d, 0, 1) ** 2 * strength
        arr = arr + np.array(color, np.float32)[None, None, :] * k[..., None]
        self.base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')
        self.d = ImageDraw.Draw(self.base)
        if glow:
            g = np.asarray(self.glow, np.float32) + k * 255 * glow
            self.glow = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8), 'L')
            self.g = ImageDraw.Draw(self.glow)

    def hexagon(self, cx, cy, r, color, width=1.0, glow=None, rot=30.0, fill=None):
        pts = [(cx + r * math.cos(math.radians(rot + 60 * i)), cy + r * math.sin(math.radians(rot + 60 * i))) for i in range(6)]
        if fill:
            self.poly(pts, fill=fill, glow=glow if fill else None)
        self.line(pts + [pts[0]], color, width, glow)
        return pts

    def star6(self, cx, cy, r, color, width=1.2, glow=None, branches=True):
        """Six-pointed ice crystal (snowflake-like arms with side branches)."""
        for i in range(6):
            a = math.radians(-90 + 60 * i)
            ex, ey = cx + math.cos(a) * r, cy + math.sin(a) * r
            self.line([(cx, cy), (ex, ey)], color, width, glow)
            if branches:
                for k in (0.45, 0.7):
                    bx, by = cx + math.cos(a) * r * k, cy + math.sin(a) * r * k
                    for s in (-1, 1):
                        b = a + s * math.radians(45)
                        self.line([(bx, by), (bx + math.cos(b) * r * 0.25, by + math.sin(b) * r * 0.25)], color, width * 0.7, glow)

    def blur_glow(self, radius=1.0):
        self.glow = self.glow.filter(ImageFilter.GaussianBlur(radius * self.ss))
        self.g = ImageDraw.Draw(self.glow)

    def finish(self, emissive=True, alpha_from_glow=True):
        base = self.base.resize((self.w, self.h), Image.LANCZOS)
        glow = self.glow.resize((self.w, self.h), Image.LANCZOS)
        alpha = self.alpha.resize((self.w, self.h), Image.LANCZOS)
        out = np.zeros((self.h, self.w, 4), np.float32)
        out[..., :3] = np.asarray(base, np.float32)
        g = np.asarray(glow, np.float32) / 255.0
        if emissive and alpha_from_glow:
            out[..., 3] = np.clip(255 * (1 - g * 1.0), 0, 255)
        else:
            out[..., 3] = np.asarray(alpha, np.float32)
        return out


def vein_paths(rs, w, h, starts, life=60, branch=0.06, wobble=0.5):
    """Random branching paths (list of polylines) used for veins and frost cracks."""
    paths = []

    def grow(x, y, ang, life, depth):
        pts = [(x, y)]
        for _ in range(life):
            x += math.cos(ang) * 1.2
            y += math.sin(ang) * 1.2
            ang += (rs.rand() - 0.5) * wobble
            pts.append((x, y))
            if x < 0 or y < 0 or x > w or y > h:
                break
            if depth < 3 and rs.rand() < branch:
                grow(x, y, ang + (rs.rand() - 0.5) * 2.0, life // 2, depth + 1)
        paths.append((pts, depth))

    for (x, y, ang) in starts:
        grow(x, y, ang, life, 0)
    return paths


def voronoi_facets(w, h, n, seed, c1, c2):
    """Faceted crystal surface: Voronoi cells shaded by a per-cell gradient."""
    rs = np.random.RandomState(seed)
    pts = rs.rand(n, 2) * [w, h]
    shade = rs.rand(n)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.full((h, w), 1e9, np.float32)
    idx = np.zeros((h, w), np.int32)
    d2 = np.full((h, w), 1e9, np.float32)
    for i, (px, py) in enumerate(pts):
        dd = (x - px) ** 2 + (y - py) ** 2
        m = dd < d
        d2 = np.where(m, d, np.minimum(d2, dd))
        d = np.where(m, dd, d)
        idx = np.where(m, i, idx)
    edge = np.sqrt(d2) - np.sqrt(d)
    t = shade[idx] * 0.7 + (y / h) * 0.3
    c1, c2 = np.array(c1, np.float32), np.array(c2, np.float32)
    rgb = c2[None, None, :] + (c1 - c2)[None, None, :] * t[..., None]
    rgb = np.where((edge < 1.2)[..., None], rgb * 1.35 + 20, rgb)
    return np.clip(rgb, 0, 255), edge
