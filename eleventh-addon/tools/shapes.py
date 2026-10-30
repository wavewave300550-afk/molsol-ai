"""Geometric primitives (rings, wire-frame cubes, orbs, chains) and extra painters for modelkit."""
import math
import random

from modelkit import TRANSPARENT, FaceCtx, hx, mix, shade


def _norm(deg: float) -> float:
    deg = (deg + 180) % 360 - 180
    return round(deg, 3)


def ring(bone, center, radius, segments, mat, *, thickness=1.0, width=1.0, plane="xz", glow=False,
         phase=0.0, fill=1.08, decals=None):
    """Circle of tangent-aligned cubes. plane: 'xz' (horizontal), 'xy' (facing z), 'yz' (facing x)."""
    cx, cy, cz = center
    L = 2 * math.pi * radius / segments * fill
    for i in range(segments):
        a = 2 * math.pi * i / segments + phase
        ad = math.degrees(a)
        if plane == "xz":
            p = (cx + radius * math.cos(a), cy, cz + radius * math.sin(a))
            size = (L, width, thickness)
            rot = (0, _norm(ad + 90), 0)
        elif plane == "xy":
            p = (cx + radius * math.cos(a), cy + radius * math.sin(a), cz)
            size = (L, thickness, width)
            rot = (0, 0, _norm(ad + 90))
        else:
            p = (cx, cy + radius * math.cos(a), cz + radius * math.sin(a))
            size = (width, L, thickness)
            rot = (_norm(-(ad + 90)), 0, 0)
        origin = tuple(round(p[k] - size[k] / 2, 3) for k in range(3))
        bone.add(origin, size, mat, pivot=tuple(round(x, 3) for x in p), rotation=rot, glow=glow,
                 decals=dict(decals or {}))


def frame_cube(bone, center, side, thickness, mat, glow=False):
    """Wire-frame cube: 12 edges."""
    cx, cy, cz = center
    h = side / 2
    t = thickness
    L = side + t
    for a in (-h, h):
        for b in (-h, h):
            bone.add((cx - L / 2, cy + a - t / 2, cz + b - t / 2), (L, t, t), mat, glow=glow)
            bone.add((cx + a - t / 2, cy - L / 2 + t, cz + b - t / 2), (t, L - 2 * t, t), mat, glow=glow)
            bone.add((cx + a - t / 2, cy + b - t / 2, cz - L / 2 + t), (t, t, L - 2 * t), mat, glow=glow)


def orb(bone, center, r, mat, glow=False, decals=None, face_mats=None):
    """Rounded ball from three overlapping boxes plus a core."""
    cx, cy, cz = center
    k = 0.72
    for sx, sy, sz in ((2 * r, 2 * r * k, 2 * r * k), (2 * r * k, 2 * r, 2 * r * k), (2 * r * k, 2 * r * k, 2 * r)):
        bone.add((cx - sx / 2, cy - sy / 2, cz - sz / 2), (sx, sy, sz), mat, glow=glow,
                 decals=dict(decals or {}), face_mats=dict(face_mats or {}))


def segment_between(bone, a, b, thickness, mat, glow=False):
    """Cube from point a to point b (rotation solved for the preview/Bedrock convention)."""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    L = math.sqrt(dx * dx + dy * dy + dz * dz)
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)
    # Cube built along +y, then pitched (x) and yawed (y): direction = (sin p * -sin yaw?, ...)
    # Solve: right-handed angles (alpha about x, then phi about y) mapping (0,1,0) -> d.
    d = (dx / L, dy / L, dz / L)
    alpha = math.atan2(math.hypot(d[0], d[2]), d[1])          # tilt away from +y
    phi = math.atan2(d[0], d[2]) if (d[0] or d[2]) else 0.0     # heading in xz
    # (0,1,0) rotated about x by alpha -> (0, cos a, sin a); then about y by phi -> (sin a sin phi, cos a, sin a cos phi)
    rot = (_norm(-math.degrees(alpha)), _norm(-math.degrees(phi)), 0)
    origin = (mid[0] - thickness / 2, mid[1] - L / 2, mid[2] - thickness / 2)
    bone.add(tuple(round(x, 3) for x in origin), (thickness, round(L, 3), thickness), mat,
             pivot=tuple(round(x, 3) for x in mid), rotation=rot, glow=glow)


# --------------------------------------------------------------------------- painters

def m_void(base="120a26", deep="05030d", stars=("ffffff", "b9a6ff", "8fe9ff"), density=0.06):
    """Starfield cloth: a body that contains its own night sky."""
    b, d = hx(base), hx(deep)
    st = [hx(s) for s in stars]

    def p(f: FaceCtx):
        col = mix(b, d, f.v * 0.8 + (f.rng.random() - 0.5) * 0.2)
        r = f.rng.random()
        if r < density:
            col = st[int(f.rng.random() * len(st))]
        elif r < density * 2.2:
            col = mix(col, st[1], 0.35)
        return col
    return p


def m_crystal(c1="b78cff", c2="5fd7ff", c3="ffffff", dark="3a2366"):
    a, b, c, dk = hx(c1), hx(c2), hx(c3), hx(dark)

    def p(f: FaceCtx):
        t = (f.u + f.v) / 2
        col = mix(a, b, t)
        facet = ((f.x // 2) + (f.y // 3)) % 3
        col = shade(col, (facet - 1) * 0.12)
        if (f.x + f.y) % 7 == 0:
            col = mix(col, c, 0.6)
        if f.edge and min(f.w, f.h) > 2:
            col = mix(col, dk, 0.45)
        return col
    return p


def m_energy(core="ffffff", edge="a46bff", bands=True):
    c, e = hx(core), hx(edge)

    def p(f: FaceCtx):
        d = abs(f.v - 0.5) * 2 if f.h > 1 else abs(f.u - 0.5) * 2
        col = mix(c, e, min(1.0, d * 1.2))
        if bands and (f.x + f.y) % 4 == 0:
            col = shade(col, 0.15)
        return col
    return p


def m_membrane(vein="7ff6ff", web="0e4a5a", deep="051c24"):
    v, w, dp = hx(vein), hx(web), hx(deep)

    def p(f: FaceCtx):
        if f.face in ("north", "south", "east", "west") and (f.w <= 1 or f.h <= 1):
            return v
        col = mix(w, dp, f.rng.random() * 0.6)
        if f.x % 5 == 0 or (f.y + f.x // 3) % 6 == 0:
            col = mix(col, v, 0.75)
        if f.rng.random() < 0.02:
            col = hx("ffffff")
        return col
    return p


def m_runes(base="d4a63a", rune="3b0f6b", seed=3):
    """Metal with engraved glyph strips."""
    b, r = hx(base), hx(rune)
    glyphs = [
        (0b111, 0b101, 0b111), (0b010, 0b111, 0b010), (0b101, 0b010, 0b101), (0b110, 0b011, 0b110),
        (0b111, 0b010, 0b010), (0b100, 0b111, 0b001), (0b011, 0b100, 0b011), (0b101, 0b111, 0b100),
    ]
    rnd = random.Random(seed)
    order = [rnd.randrange(len(glyphs)) for _ in range(64)]

    def p(f: FaceCtx):
        col = shade(b, 0.22 * (1 - f.v) - 0.1 + (f.rng.random() - 0.5) * 0.06)
        if f.h >= 4 and f.w >= 4:
            gx, gy = f.x % 4, (f.y - 1) % 4
            if gx < 3 and gy < 3 and 1 <= f.y < f.h - 1:
                g = glyphs[order[(f.x // 4 + f.cube_index) % 64]]
                if (g[gy] >> (2 - gx)) & 1:
                    col = r
        if f.edge:
            col = shade(col, -0.25)
        return col
    return p


def m_glyph_glow(base="ffd27a", dim="40250a", seed=5):
    """Glow strip with bright glyphs on a dim channel (for additive layers)."""
    b, d = hx(base), hx(dim)
    rnd = random.Random(seed)
    pattern = [rnd.random() < 0.55 for _ in range(97)]

    def p(f: FaceCtx):
        on = pattern[(f.x * 7 + f.y * 13 + f.cube_index * 5) % 97]
        return b if on else d
    return p


def m_porcelain(base="efe9f5", shadow="b8acc9"):
    b, s = hx(base), hx(shadow)

    def p(f: FaceCtx):
        col = mix(b, s, f.v * 0.55)
        return shade(col, (f.rng.random() - 0.5) * 0.04)
    return p


def m_feather_eye(base="f7f1e1", tip="d9a441", iris="c4122f"):
    """White-gold feathers; some feathers carry an eye."""
    b, t, ir = hx(base), hx(tip), hx(iris)

    def p(f: FaceCtx):
        col = mix(b, t, max(0.0, f.v - 0.4) / 0.6)
        if f.x % 2 == 1:
            col = shade(col, -0.08)
        if f.v > 0.92 and f.x % 2:
            return TRANSPARENT
        return col
    return p


def eye_decal(iris="c4122f", ring_col="ffcc66", pupil="0b0306", sclera=None):
    i, rc, pp = hx(iris), hx(ring_col), hx(pupil)
    sc = hx(sclera) if sclera else None

    def d(setp, w, h):
        cx, cy = (w - 1) / 2, (h - 1) / 2
        r = min(w, h) / 2
        for y in range(h):
            for x in range(w):
                dd = math.hypot(x - cx, y - cy)
                if sc is not None and dd <= r:
                    setp(x, y, sc)
                if dd <= r * 0.62:
                    setp(x, y, rc if dd > r * 0.45 else i)
                if dd <= r * 0.2 + 0.3:
                    setp(x, y, pp)
    return d


def slit_eyes(col="ffffff"):
    c = hx(col)

    def d(setp, w, h):
        for x in range(w):
            setp(x, h // 2, c)
    return d
