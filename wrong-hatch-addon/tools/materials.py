"""
Procedural materials (numpy painters) for The Wrong Hatch.

Every material is a factory returning ``paint(face) -> (h, w, 4) float array``.
Alpha 0 = emissive texel (entity_emissive_alpha), 255 = normal opaque texel,
values in between give partial glow.

Texture variants:
    0  "intact"   - phase I: thin glowing seams, few cracks
    1  "cracked"  - phase II: many cracks, half of them glowing
    2  "awakened" - phase III: glowing veins everywhere, core blazing, eyes lit
"""
from __future__ import annotations

import numpy as np

from voxkit import Face, hx, seeded

GLOW = 0.0          # alpha of a fully emissive texel
HALO = 150.0        # alpha of a softly glowing texel

# palette sampled from the approved reference sheet
SHELL = hx("f4ede1")
SHELL_SHADOW = hx("d6c8ad")
SHELL_DEEP = hx("a8987c")
FEATHER = hx("efdfba")
FEATHER_DARK = hx("d5bd8b")
FEATHER_TIP = hx("faf3e2")
CRACK = hx("8a6f4e")
GOLD = hx("ffc22e")
GOLD_HOT = hx("fff1a6")
GOLD_DEEP = hx("f08c12")
RED = hx("c9232b")
RED_DARK = hx("8c1219")
RED_LIGHT = hx("e8473f")
BEAK_UP = hx("f6be3c")
BEAK_LO = hx("e48a1a")
LEG = hx("eb951f")
LEG_DARK = hx("b9650f")
CLAW = hx("f1e7d2")
CLAW_DARK = hx("bfae8c")
GREY = hx("9d9aa6")
GREY_DARK = hx("74717e")
EYE = hx("3b0708")
EYE_RED = hx("b3161c")


def _noise(f: Face, scale: float = 1.0) -> np.ndarray:
    return (f.rng.random((f.h, f.w)) - 0.5) * scale


def _blotch(f: Face, cells: int = 3) -> np.ndarray:
    """Low frequency value noise in [-0.5, 0.5]."""
    gh, gw = max(2, f.h // cells + 2), max(2, f.w // cells + 2)
    g = f.rng.random((gh, gw)) - 0.5
    ys = np.linspace(0, gh - 1.001, f.h)
    xs = np.linspace(0, gw - 1.001, f.w)
    y0, x0 = ys.astype(int), xs.astype(int)
    fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
    a = g[y0][:, x0]
    b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]
    d = g[y0 + 1][:, x0 + 1]
    return a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy


def _bevel(f: Face, rgb: np.ndarray, light: float = 0.10, dark: float = 0.16) -> np.ndarray:
    """Chunky voxel bevel: top/left rows lighter, bottom/right rows darker."""
    if min(f.w, f.h) < 3:
        return rgb
    out = rgb.copy()
    out[0, :] = out[0, :] + (255 - out[0, :]) * light
    out[:, 0] = out[:, 0] + (255 - out[:, 0]) * light * 0.6
    out[-1, :] = out[-1, :] * (1 - dark)
    out[:, -1] = out[:, -1] * (1 - dark * 0.7)
    return out


def _crack_paths(f: Face, count: int, rng: np.random.Generator):
    """Random-walk crack polylines across the face; yields lists of (y, x) texels."""
    paths = []
    for _ in range(count):
        side = rng.integers(4)
        if side == 0:
            y, x, d = 0.0, rng.uniform(0, f.w), np.array([1.0, rng.uniform(-0.8, 0.8)])
        elif side == 1:
            y, x, d = f.h - 1.0, rng.uniform(0, f.w), np.array([-1.0, rng.uniform(-0.8, 0.8)])
        elif side == 2:
            y, x, d = rng.uniform(0, f.h), 0.0, np.array([rng.uniform(-0.8, 0.8), 1.0])
        else:
            y, x, d = rng.uniform(0, f.h), f.w - 1.0, np.array([rng.uniform(-0.8, 0.8), -1.0])
        d = d / np.linalg.norm(d)
        length = rng.uniform(0.45, 1.1) * max(f.w, f.h)
        pts = []
        for _s in range(int(length)):
            iy, ix = int(round(y)), int(round(x))
            if not (0 <= iy < f.h and 0 <= ix < f.w):
                break
            pts.append((iy, ix))
            if rng.random() < 0.12 and len(pts) > 3:
                # branch
                paths.append(_branch(f, iy, ix, rng))
            d = d + rng.normal(0, 0.45, 2)
            d = d / np.linalg.norm(d)
            y, x = y + d[0], x + d[1]
        paths.append(pts)
    return paths


def _branch(f, y, x, rng):
    d = rng.normal(0, 1, 2)
    d /= np.linalg.norm(d)
    pts = []
    for _ in range(int(rng.uniform(2, 6))):
        y, x = y + d[0], x + d[1]
        iy, ix = int(round(y)), int(round(x))
        if not (0 <= iy < f.h and 0 <= ix < f.w):
            break
        pts.append((iy, ix))
        d = d + rng.normal(0, 0.6, 2)
        d /= np.linalg.norm(d)
    return pts


# --------------------------------------------------------------------------- materials

def shell(base=SHELL, crack_rate: float = 1.0, glow_bias: float = 0.0, grey: float = 0.0):
    """Living eggshell plate: speckled cream, bevelled edges, cracks (glowing per variant)."""
    def paint(f: Face) -> np.ndarray:
        bl = _blotch(f, 4)
        # every plate gets its own tone (white, pinkish, warm beige) like the reference sheet
        tone = seeded(f.cube_key, "tone").random()
        tint = (np.array([6, 4, 0.0]) if tone < 0.33 else np.array([4, -4, -6.0]) if tone < 0.66
                else np.array([-6, -10, -18.0]))
        rgb = np.broadcast_to(base + tint, (f.h, f.w, 3)).astype(np.float32).copy()
        rgb += (bl * 26)[..., None]
        rgb += (_noise(f, 10))[..., None]
        # faint shadow towards the lower part of side faces
        if f.name in ("north", "south", "east", "west"):
            u, v = f.grid()
            rgb = rgb * (1 - 0.10 * v[..., None])
        if f.name == "down":
            rgb *= 0.82
        if grey > 0:
            u, v = f.grid()
            t = np.clip((bl + 0.25) * 2.2 * grey, 0, 1)[..., None]
            rgb = rgb * (1 - t) + GREY * t
        # speckles like a real egg
        sp = f.rng.random((f.h, f.w)) < 0.025
        rgb[sp] = rgb[sp] * 0.84
        rgb = _bevel(f, rgb)
        a = np.full((f.h, f.w), 255.0)
        area = f.w * f.h
        base_count = area / 110.0 * crack_rate
        count = int(base_count * (0.6, 1.6, 2.2)[f.variant] + f.rng.random())
        glow_p = min(1.0, (0.25, 0.55, 1.0)[f.variant] + glow_bias)
        crng = seeded(f.key, "crack")
        for path in _crack_paths(f, count, crng):
            glowing = crng.random() < glow_p and len(path) > 2
            for (y, x) in path:
                if glowing:
                    rgb[y, x] = GOLD_HOT if f.variant == 2 else GOLD
                    a[y, x] = GLOW
                    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < f.h and 0 <= xx < f.w and a[yy, xx] > HALO:
                            rgb[yy, xx] = rgb[yy, xx] * 0.55 + GOLD_DEEP * 0.45
                            a[yy, xx] = HALO if f.variant else 255.0
                else:
                    rgb[y, x] = CRACK
        return np.dstack([rgb, a])
    return paint


def feather(base=FEATHER, dark=FEATHER_DARK, tip=FEATHER_TIP, along: str = "v", tip_end: float = 1.0):
    """Feather blade: shaft + barbs striations, lighter tip. ``along`` = axis of the feather length."""
    def paint(f: Face) -> np.ndarray:
        u, v = f.grid()
        k = v if along == "v" else u
        across = u if along == "v" else v
        if tip_end < 0.5:
            k = 1 - k
        rgb = np.broadcast_to(base, (f.h, f.w, 3)).astype(np.float32).copy()
        t = np.clip((k - 0.55) / 0.45, 0, 1)[..., None]
        rgb = rgb * (1 - t) + tip * t
        rgb = rgb * (1 - 0.18 * (1 - k)[..., None]) + dark * 0.18 * (1 - k)[..., None]
        # barbs: diagonal striations
        n = across * (f.w if along == "v" else f.h)
        m = k * (f.h if along == "v" else f.w)
        stripes = ((n * 0.9 + m * 0.6).astype(int) % 4 == 0)
        rgb[stripes] = rgb[stripes] * 0.95
        # shaft
        shaft = np.abs(across - 0.5) < (0.5 / max(2, (f.w if along == "v" else f.h)))
        if f.name in ("north", "south", "east", "west"):
            rgb[shaft] = rgb[shaft] * 0.84
        rgb += _noise(f, 8)[..., None]
        if f.variant == 2:
            rgb = rgb * 0.94 + GOLD * 0.06
        rgb = _bevel(f, rgb, 0.08, 0.2)
        return np.dstack([rgb, np.full((f.h, f.w), 255.0)])
    return paint


def gradient_feather(base=FEATHER, to=GREY, start=0.55, along="v", reverse=False):
    """Feather whose far end fades into another colour (sickle tips)."""
    inner = feather(base, along=along)

    def paint(f: Face) -> np.ndarray:
        out = inner(f)
        u, v = f.grid()
        k = v if along == "v" else u
        if reverse:
            k = 1 - k
        t = np.clip((k - start) / max(0.01, 1 - start), 0, 1)[..., None]
        bl = _blotch(f, 3)[..., None]
        t = np.clip(t + bl * 0.4 * (t > 0), 0, 1)
        out[..., :3] = out[..., :3] * (1 - t) + (to + bl[..., 0:1] * 20) * t
        return out
    return paint


def glow_seam(level: float = 1.0):
    """Molten gold light seen through the gaps between shell plates."""
    def paint(f: Face) -> np.ndarray:
        bl = _blotch(f, 3)
        hot = (bl + 0.5) * (0.7 + 0.15 * f.variant)
        rgb = GOLD_DEEP * (1 - hot[..., None]) + GOLD_HOT * hot[..., None]
        rgb += _noise(f, 18)[..., None]
        if f.variant == 0:
            rgb = rgb * 0.92
        a = np.full((f.h, f.w), GLOW)
        if level < 1.0:
            a[:] = 255 * (1 - level)
        return np.dstack([rgb, a])
    return paint


def core_orb():
    def paint(f: Face) -> np.ndarray:
        u, v = f.grid()
        r = np.sqrt((u - 0.5) ** 2 + (v - 0.5) ** 2) * 2
        t = np.clip(r, 0, 1)[..., None]
        rgb = GOLD_HOT * (1 - t) + GOLD * t
        rgb = np.where((r < 0.35)[..., None], np.array([255, 252, 228.0]), rgb)
        rgb += _noise(f, 10)[..., None]
        return np.dstack([rgb, np.full((f.h, f.w), GLOW)])
    return paint


def gold_star():
    def paint(f: Face) -> np.ndarray:
        bl = _blotch(f, 2)
        rgb = GOLD * (0.85 + 0.3 * (bl[..., None] + 0.5) * 0.5) + GOLD_HOT * 0.15
        u, v = f.grid()
        edge = (np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) < 0.12)
        rgb[edge] = rgb[edge] * 0.75 + GOLD_DEEP * 0.25
        return np.dstack([rgb, np.full((f.h, f.w), GLOW)])
    return paint


def comb():
    def paint(f: Face) -> np.ndarray:
        u, v = f.grid()
        rgb = RED * (1 - 0.25 * v[..., None]) + RED_LIGHT * 0.25 * (1 - v[..., None])
        bl = _blotch(f, 2)
        rgb += (bl * 30)[..., None]
        blocks = f.rng.random((f.h, f.w)) < 0.1
        rgb[blocks] = rgb[blocks] * 0.82
        if f.name == "up":
            rgb = rgb * 0.7 + RED_LIGHT * 0.3
        rgb = _bevel(f, rgb, 0.18, 0.28)
        return np.dstack([rgb, np.full((f.h, f.w), 255.0)])
    return paint


def wattle():
    inner = comb()

    def paint(f: Face) -> np.ndarray:
        out = inner(f)
        u, v = f.grid()
        out[..., :3] = out[..., :3] * (1 - 0.2 * v[..., None]) + RED_DARK * 0.2 * v[..., None]
        return out
    return paint


def beak(upper=True):
    def paint(f: Face) -> np.ndarray:
        u, v = f.grid()
        base = BEAK_UP if upper else BEAK_LO
        rgb = np.broadcast_to(base, (f.h, f.w, 3)).astype(np.float32).copy()
        if f.name in ("north", "south", "east", "west"):
            rgb = rgb * (1 - 0.18 * v[..., None]) + BEAK_LO * 0.18 * v[..., None]
        if f.name == "up":
            rgb = rgb * 0.85 + np.array([255, 226, 120.0]) * 0.15
        rgb += _noise(f, 8)[..., None]
        rgb = _bevel(f, rgb, 0.16, 0.25)
        return np.dstack([rgb, np.full((f.h, f.w), 255.0)])
    return paint


def leg():
    def paint(f: Face) -> np.ndarray:
        u, v = f.grid()
        rgb = np.broadcast_to(LEG, (f.h, f.w, 3)).astype(np.float32).copy()
        if f.name in ("north", "south", "east", "west"):
            band = (np.arange(f.h) % 4 == 3)
            rgb[band, :] = rgb[band, :] * 0.78 + LEG_DARK * 0.22
            rgb = rgb * (1 - 0.12 * u[..., None])
        rgb += _noise(f, 12)[..., None]
        rgb = _bevel(f, rgb, 0.12, 0.22)
        return np.dstack([rgb, np.full((f.h, f.w), 255.0)])
    return paint


def claw():
    def paint(f: Face) -> np.ndarray:
        u, v = f.grid()
        rgb = CLAW * (1 - 0.35 * v[..., None]) + CLAW_DARK * 0.35 * v[..., None]
        rgb += _noise(f, 8)[..., None]
        rgb = _bevel(f, rgb, 0.15, 0.25)
        return np.dstack([rgb, np.full((f.h, f.w), 255.0)])
    return paint


def eye():
    def paint(f: Face) -> np.ndarray:
        u, v = f.grid()
        rgb = np.broadcast_to(EYE, (f.h, f.w, 3)).astype(np.float32).copy()
        a = np.full((f.h, f.w), 255.0)
        if f.name == "north":
            iris = (np.abs(u - 0.62) < 0.22) & (v > 0.35)
            rgb[iris] = EYE_RED
            pupil = (np.abs(u - 0.62) < 0.09) & (v > 0.45) & (v < 0.85)
            rgb[pupil] = np.array([255, 120, 60.0]) if f.variant else np.array([70, 6, 6.0])
            if f.variant >= 1:
                a[iris] = HALO if f.variant == 1 else GLOW
                if f.variant == 2:
                    rgb[iris] = rgb[iris] * 0.3 + GOLD * 0.7
        return np.dstack([rgb, a])
    return paint


def solid(rgbhex: str, noise: float = 8, bevel: bool = True, alpha: float = 255.0):
    c = hx(rgbhex)

    def paint(f: Face) -> np.ndarray:
        rgb = np.broadcast_to(c, (f.h, f.w, 3)).astype(np.float32).copy()
        rgb += _noise(f, noise)[..., None]
        if bevel:
            rgb = _bevel(f, rgb)
        return np.dstack([rgb, np.full((f.h, f.w), alpha)])
    return paint


def egg(base="f2ead9", speckle="b9a88a", crack_rate=1.0, glow=False, tint=None):
    """Egg shell for minion eggs: speckled, cracked; optional tint (rotten / gilded)."""
    b = hx(base)
    s = hx(speckle)
    t = hx(tint) if tint else None
    inner = shell(b, crack_rate=crack_rate, glow_bias=0.5 if glow else -1.0)

    def paint(f: Face) -> np.ndarray:
        out = inner(f)
        sp = f.rng.random((f.h, f.w)) < 0.06
        out[sp, :3] = out[sp, :3] * 0.6 + s * 0.4
        if t is not None:
            bl = _blotch(f, 3)[..., None]
            k = np.clip(0.45 + bl, 0, 1)
            out[..., :3] = out[..., :3] * (1 - k * 0.55) + t * k * 0.55
        return out
    return paint
