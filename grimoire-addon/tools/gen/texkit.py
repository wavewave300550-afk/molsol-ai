"""Procedural texture painters and per-model atlases (numpy + Pillow).

Every model gets its own atlas. A face asks for a style; the atlas paints (or reuses) a tile
whose size is derived from the face size (about 1 texel per 2 model pixels, 4..32 texels).
Alpha meaning depends on the material the bone uses:
  * default bones  -> entity_emissive_alpha: alpha 255 = lit surface, alpha 0 = full glow;
  * "t_" bones     -> entity_alphablend:     alpha = transparency;
  * "g_" bones     -> entity_beam_additive:  colour adds light (black = invisible).
"""
import math
import hashlib
import numpy as np
from PIL import Image


def hexrgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def seed_of(*parts):
    return int(hashlib.md5('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16)


def mix(a, b, t):
    return a + (b - a) * t


def noise2(w, h, seed, scale=4.0, octaves=3):
    """Cheap value noise in [0,1]."""
    rs = np.random.RandomState(seed % (2 ** 31))
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        gw = max(2, int(w / scale * (2 ** o)) + 2)
        gh = max(2, int(h / scale * (2 ** o)) + 2)
        g = rs.rand(gh, gw).astype(np.float32)
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += np.asarray(img, np.float32) / 255.0 * amp
        tot += amp
        amp *= 0.5
    return np.clip(out / tot, 0, 1)


def grid(w, h):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    return (x + 0.5) / w, (y + 0.5) / h


# --------------------------------------------------------------------------------------------
# painters: f(w, h, spec, seed) -> float32 RGBA array (h, w, 4) in 0..255
# --------------------------------------------------------------------------------------------

def p_solid(w, h, s, seed):
    c = hexrgb(s['c'])
    n = noise2(w, h, seed, 3) - 0.5
    rgb = c[None, None, :] * (1 + n[..., None] * s.get('noise', 0.15))
    return rgba(rgb, s.get('a', 255))


def p_grad(w, h, s, seed):
    u, v = grid(w, h)
    t = v if s.get('dir', 'v') == 'v' else u
    if s.get('mirror'):
        t = 1 - np.abs(t * 2 - 1)
    a, b = hexrgb(s['c1']), hexrgb(s['c2'])
    n = noise2(w, h, seed, 3) - 0.5
    rgb = mix(a[None, None, :], b[None, None, :], t[..., None]) * (1 + n[..., None] * s.get('noise', 0.08))
    alpha = s.get('a', 255)
    if 'a2' in s:
        alpha = mix(np.float32(s['a']), np.float32(s['a2']), t)
    return rgba(rgb, alpha)


def p_metal(w, h, s, seed):
    """Brushed metal with bevel highlight and dark border."""
    u, v = grid(w, h)
    c = hexrgb(s['c'])
    hi = hexrgb(s.get('hi', '#ffffff'))
    lo = hexrgb(s.get('lo', '#000000'))
    rs = np.random.RandomState(seed % 2 ** 31)
    streak = np.repeat(rs.rand(h, 1).astype(np.float32), w, 1) * 0.5 + noise2(w, h, seed + 1, 2) * 0.5
    edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    bevel = np.clip(1 - edge * max(w, h) / 2.0, 0, 1)
    rgb = c[None, None, :] * (0.82 + streak[..., None] * 0.3)
    rgb = mix(rgb, hi[None, None, :], (np.clip(0.35 - v, 0, 0.35) * 1.2)[..., None])
    rgb = mix(rgb, lo[None, None, :], (bevel * 0.55)[..., None])
    return rgba(rgb, s.get('a', 255))


def p_glow(w, h, s, seed):
    """Bright core fading out; mode 'radial', 'band' (horizontal band) or 'edge'."""
    u, v = grid(w, h)
    mode = s.get('mode', 'radial')
    if mode == 'radial':
        d = np.sqrt((u - 0.5) ** 2 + (v - 0.5) ** 2) * 2
    elif mode == 'band':
        d = np.abs(v - 0.5) * 2
    elif mode == 'vband':
        d = np.abs(u - 0.5) * 2
    else:  # edge: bright rim
        d = 1 - np.clip(np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) * 2 * s.get('rim', 3.0), 0, 1)
        d = 1 - d
    k = np.clip(1 - d, 0, 1) ** s.get('pow', 1.2)
    core, outer = hexrgb(s['c1']), hexrgb(s['c2'])
    rgb = mix(outer[None, None, :], core[None, None, :], k[..., None])
    floor = s.get('floor', 0.25)
    rgb = rgb * (floor + (1 - floor) * k[..., None])
    alpha = s.get('a', 255)
    if s.get('emissive'):
        return rgba(rgb, np.where(k > 0.15, 0, 255))
    return rgba(rgb, alpha)


def p_runes(w, h, s, seed):
    """Dark band with glowing rune strokes; emissive where strokes are."""
    rs = np.random.RandomState(seed % 2 ** 31)
    base, glow = hexrgb(s['c1']), hexrgb(s['c2'])
    img = np.zeros((h, w), np.float32)
    cell = max(3, min(h, 8))
    x = 0
    while x < w - 2:
        cw = rs.randint(max(2, cell - 2), cell + 2)
        # each glyph: 2-4 strokes inside the cell
        for _ in range(rs.randint(2, 5)):
            if rs.rand() < 0.5:
                yy = rs.randint(1, max(2, h - 1))
                img[yy, x:min(w, x + cw)] = 1
            else:
                xx = min(w - 1, x + rs.randint(0, max(1, cw)))
                y0 = rs.randint(0, max(1, h // 2))
                img[y0:min(h, y0 + rs.randint(2, max(3, h))), xx] = 1
        x += cw + 1
    rgb = mix(base[None, None, :], glow[None, None, :], img[..., None])
    if s.get('transparent'):
        return rgba(rgb, np.where(img > 0, 255, s.get('a', 40)))
    return rgba(rgb, np.where(img > 0, 0, 255))


def p_ice(w, h, s, seed):
    """Translucent crystal ice with cracks and bright facets (for alphablend bones)."""
    u, v = grid(w, h)
    c1, c2 = hexrgb(s.get('c1', '#9fd8ff')), hexrgb(s.get('c2', '#2a5fd0'))
    n = noise2(w, h, seed, 3)
    rgb = mix(c2[None, None, :], c1[None, None, :], (0.35 + 0.65 * (1 - v) * 0.7 + n * 0.3)[..., None])
    rs = np.random.RandomState(seed % 2 ** 31)
    cracks = np.zeros((h, w), np.float32)
    for _ in range(max(1, (w * h) // 90)):
        x, y = rs.randint(0, w), rs.randint(0, h)
        ang = rs.rand() * math.pi
        for t in range(rs.randint(3, max(4, max(w, h)))):
            xi, yi = int(x + math.cos(ang) * t), int(y + math.sin(ang) * t)
            if 0 <= xi < w and 0 <= yi < h:
                cracks[yi, xi] = 1
            ang += (rs.rand() - 0.5) * 0.6
    edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) * min(w, h)
    rim = np.clip(1.5 - edge, 0, 1)
    rgb = mix(rgb, np.array([235, 250, 255], np.float32), np.clip(cracks * 0.8 + rim * 0.6, 0, 1)[..., None])
    a = s.get('a', 150)
    alpha = np.clip(a + rim * 80 + cracks * 70, 0, 255)
    return rgba(rgb, alpha)


def p_frost(w, h, s, seed):
    c1, c2 = hexrgb(s.get('c1', '#e8f6ff')), hexrgb(s.get('c2', '#8cc8f0'))
    n = noise2(w, h, seed, 2, 4)
    rgb = mix(c2[None, None, :], c1[None, None, :], n[..., None])
    return rgba(rgb, s.get('a', 255))


def p_liquid(w, h, s, seed):
    """Glossy magical blood: dark core, bright ripples, specular streaks."""
    u, v = grid(w, h)
    c1, c2 = hexrgb(s.get('c1', '#ff2a33')), hexrgb(s.get('c2', '#4a020c'))
    n = noise2(w, h, seed, 4)
    rip = 0.5 + 0.5 * np.sin((v * 6 + n * 3 + u * 2) * math.pi)
    rgb = mix(c2[None, None, :], c1[None, None, :], (rip * 0.55 + n * 0.25)[..., None])
    spec = np.clip((rip - 0.86) * 7, 0, 1) * s.get('spec', 0.7)
    rgb = mix(rgb, np.array([255, 190, 190], np.float32), spec[..., None])
    a = s.get('a', 230)
    if s.get('emissive'):
        return rgba(rgb, np.where(rip > 0.75, 0, 255))
    return rgba(rgb, a)


def p_veins(w, h, s, seed):
    """Dark base with branching bright vessels (emissive)."""
    rs = np.random.RandomState(seed % 2 ** 31)
    base, glow = hexrgb(s['c1']), hexrgb(s['c2'])
    n = noise2(w, h, seed, 3)
    img = np.zeros((h, w), np.float32)

    def grow(x, y, ang, life, wdt):
        for _ in range(life):
            xi, yi = int(x) % w, int(y) % h
            img[yi, xi] = max(img[yi, xi], wdt)
            x += math.cos(ang)
            y += math.sin(ang)
            ang += (rs.rand() - 0.5) * 0.7
            if rs.rand() < 0.08 and life > 4:
                grow(x, y, ang + (rs.rand() - 0.5) * 1.6, life // 2, wdt * 0.7)

    for _ in range(max(1, (w + h) // 12)):
        grow(rs.randint(0, w), rs.randint(0, h), rs.rand() * math.tau, max(w, h), 1.0)
    rgb = base[None, None, :] * (0.75 + n[..., None] * 0.4)
    rgb = mix(rgb, glow[None, None, :], img[..., None])
    return rgba(rgb, np.where(img > 0.45, 0, 255) if s.get('emissive', True) else s.get('a', 255))


def p_leather(w, h, s, seed):
    """Book cover leather with grain, worn edge and tooled double border."""
    u, v = grid(w, h)
    c = hexrgb(s['c'])
    n = noise2(w, h, seed, 1.5, 4)
    rgb = c[None, None, :] * (0.78 + n[..., None] * 0.4)
    edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    rgb = rgb * (0.7 + 0.3 * np.clip(edge * 12, 0, 1))[..., None]
    if s.get('border'):
        bc = hexrgb(s['border'])
        px = 1.0 / max(w, h)
        for e0 in (0.06, 0.1):
            m = (np.abs(edge - e0) < px * 0.9) & (edge > 0)
            rgb[m] = bc
    return rgba(rgb, 255)


def p_pages(w, h, s, seed):
    """Stacked page edges (horizontal lines), parchment / ice / blood tinted."""
    u, v = grid(w, h)
    c1, c2 = hexrgb(s.get('c1', '#efe2c0')), hexrgb(s.get('c2', '#bfa77a'))
    lines = (np.floor(v * h) % 2).astype(np.float32)
    n = noise2(w, h, seed, 2)
    rgb = mix(c1[None, None, :], c2[None, None, :], (lines * 0.5 + n * 0.3)[..., None])
    return rgba(rgb, s.get('a', 255))


def p_script(w, h, s, seed):
    """Page surface with luminous writing lines (emissive strokes)."""
    rs = np.random.RandomState(seed % 2 ** 31)
    paper, ink = hexrgb(s.get('c1', '#f1e6c8')), hexrgb(s.get('c2', '#ff8a1e'))
    n = noise2(w, h, seed, 2)
    rgb = paper[None, None, :] * (0.9 + n[..., None] * 0.15)
    mask = np.zeros((h, w), bool)
    for row in range(2, h - 1, 3):
        x = rs.randint(1, 3)
        while x < w - 2:
            ln = rs.randint(2, 6)
            mask[row, x:min(w - 1, x + ln)] = True
            x += ln + rs.randint(1, 3)
    rgb[mask] = ink
    if s.get('transparent'):
        return rgba(rgb, np.where(mask, 255, s.get('a', 140)))
    return rgba(rgb, np.where(mask, 0, 255))


def p_scales(w, h, s, seed):
    u, v = grid(w, h)
    c1, c2 = hexrgb(s['c1']), hexrgb(s['c2'])
    k = s.get('k', 3.0)
    uu, vv = u * k * 2, v * k * 2
    row = np.floor(vv)
    uu = uu + (row % 2) * 0.5
    fu, fv = uu % 1 - 0.5, vv % 1
    d = np.sqrt(fu ** 2 + (fv * 0.9) ** 2)
    shade = np.clip(1 - d * 1.4, 0, 1)
    rgb = mix(c2[None, None, :], c1[None, None, :], shade[..., None])
    rim = (np.abs(d - 0.55) < 0.08)
    rgb[rim] = rgb[rim] * 0.55
    return rgba(rgb, s.get('a', 255))


def p_petal(w, h, s, seed):
    """Petal: bright center vein, darker curled edges, soft gradient."""
    u, v = grid(w, h)
    c1, c2 = hexrgb(s['c1']), hexrgb(s['c2'])
    edge = np.abs(u - 0.5) * 2
    rgb = mix(c1[None, None, :], c2[None, None, :], np.clip(edge ** 1.5 + v * 0.3, 0, 1)[..., None])
    vein = np.abs(u - 0.5) < (0.5 / max(4, w))
    rgb[vein] = rgb[vein] * 1.25
    n = noise2(w, h, seed, 2)
    rgb = rgb * (0.9 + n[..., None] * 0.2)
    return rgba(rgb, s.get('a', 255))


def p_air(w, h, s, seed):
    """Transparent compressed air: faint body with wavy isobar contour lines."""
    u, v = grid(w, h)
    c = hexrgb(s.get('c', '#ff9a3a'))
    n = noise2(w, h, seed, 3)
    iso = np.abs(np.sin((v * 5 + n * 1.6) * math.pi))
    line = np.clip((0.12 - iso) * 9, 0, 1)
    rgb = mix(c[None, None, :] * 0.8, np.array([255, 235, 200], np.float32), line[..., None])
    alpha = np.clip(s.get('a', 50) + line * 140, 0, 255)
    return rgba(rgb, alpha)


def p_hex(w, h, s, seed):
    """Hexagonal grid lines (for barriers/mirrors)."""
    u, v = grid(w, h)
    k = s.get('k', 2.0)
    x, y = u * k * 2, v * k * 2 * 1.1547
    q = (math.sqrt(3) / 3 * x - y / 3)
    r = 2 / 3 * y
    # distance to hex cell edge via cube coords
    cx, cz = q, r
    cy = -cx - cz
    rx, ry, rz = np.round(cx), np.round(cy), np.round(cz)
    dx, dy, dz = np.abs(rx - cx), np.abs(ry - cy), np.abs(rz - cz)
    d = np.maximum(np.maximum(dx, dy), dz)
    line = np.clip((d - 0.38) * 12, 0, 1)
    c1, c2 = hexrgb(s['c1']), hexrgb(s['c2'])
    rgb = mix(c1[None, None, :], c2[None, None, :], line[..., None])
    alpha = np.clip(s.get('a', 70) + line * 170, 0, 255)
    if s.get('opaque'):
        alpha = 255
    return rgba(rgb, alpha)


def p_crystal(w, h, s, seed):
    """Faceted crystal (opaque or emissive-tinted) with diagonal facet highlights."""
    u, v = grid(w, h)
    c1, c2 = hexrgb(s['c1']), hexrgb(s['c2'])
    facet = (np.floor((u + v * 0.6) * 3) % 2)
    t = np.clip(0.25 + facet * 0.35 + (1 - v) * 0.4, 0, 1)
    rgb = mix(c2[None, None, :], c1[None, None, :], t[..., None])
    hl = np.clip(1 - np.abs((u - v) * 3 - 0.6) * 4, 0, 1) * 0.6
    rgb = mix(rgb, np.array([255, 255, 255], np.float32), hl[..., None])
    if s.get('emissive'):
        return rgba(rgb, np.where(hl > 0.25, 0, 255))
    return rgba(rgb, s.get('a', 255))


def p_rivets(w, h, s, seed):
    base = p_metal(w, h, s, seed)
    u, v = grid(w, h)
    k = s.get('k', 2)
    fu, fv = (u * k) % 1 - 0.5, (v * k) % 1 - 0.5
    d = np.sqrt(fu ** 2 + fv ** 2)
    m = d < 0.18
    hi = hexrgb(s.get('hi', '#ffffff'))
    base[m, :3] = hi
    return base


STYLE_KINDS = {
    'solid': p_solid, 'grad': p_grad, 'metal': p_metal, 'glow': p_glow, 'runes': p_runes, 'ice': p_ice,
    'frost': p_frost, 'liquid': p_liquid, 'veins': p_veins, 'leather': p_leather, 'pages': p_pages,
    'script': p_script, 'scales': p_scales, 'petal': p_petal, 'air': p_air, 'hex': p_hex,
    'crystal': p_crystal, 'rivets': p_rivets,
}


def rgba(rgb, alpha):
    h, w = rgb.shape[:2]
    out = np.zeros((h, w, 4), np.float32)
    out[..., :3] = np.clip(rgb, 0, 255)
    out[..., 3] = np.broadcast_to(np.asarray(alpha, np.float32), (h, w))
    return out


# --------------------------------------------------------------------------------------------
# style registry (shared by all models)
# --------------------------------------------------------------------------------------------
STYLES = {}


def style(name, kind, **spec):
    STYLES[name] = dict(kind=kind, **spec)


def quant(n, lo=4, hi=32):
    n = max(lo, min(hi, n))
    for q in (4, 6, 8, 12, 16, 24, 32):
        if n <= q:
            return q
    return hi


class Atlas:
    def __init__(self, w=128, h=128, max_h=1024):
        self.w, self.h, self.max_h = w, h, max_h
        self.img = np.zeros((h, w, 4), np.float32)
        self.cache = {}
        self.cx, self.cy, self.row_h = 0, 0, 0

    def _alloc(self, tw, th):
        if self.cx + tw > self.w:
            self.cx, self.cy, self.row_h = 0, self.cy + self.row_h, 0
        while self.cy + th > self.h:
            if self.h * 2 > self.max_h:
                raise RuntimeError('atlas full')
            self.img = np.concatenate([self.img, np.zeros_like(self.img)], 0)
            self.h *= 2
        u, v = self.cx, self.cy
        self.cx += tw
        self.row_h = max(self.row_h, th)
        return u, v

    def tile(self, style_name, fw, fh, force=None):
        """Return (u, v, w, h) of a tile for a face of size fw x fh model pixels."""
        if force:
            tw, th = force
        else:
            tw, th = quant(int(round(fw / 2)) or 1), quant(int(round(fh / 2)) or 1)
        key = (style_name, tw, th)
        if key in self.cache:
            return self.cache[key]
        if style_name not in STYLES:
            raise KeyError(f'unknown style {style_name}')
        spec = STYLES[style_name]
        px = STYLE_KINDS[spec['kind']](tw, th, spec, seed_of(style_name, tw, th))
        u, v = self._alloc(tw, th)
        self.img[v:v + th, u:u + tw] = px
        r = (u, v, tw, th)
        self.cache[key] = r
        return r

    def put_image(self, key, arr):
        """Place an arbitrary RGBA image (h, w, 4) and return its rect."""
        if key in self.cache:
            return self.cache[key]
        th, tw = arr.shape[:2]
        u, v = self._alloc(tw, th)
        self.img[v:v + th, u:u + tw] = arr
        r = (u, v, tw, th)
        self.cache[key] = r
        return r

    def save(self, path):
        Image.fromarray(np.clip(self.img, 0, 255).astype(np.uint8), 'RGBA').save(path, optimize=True)
