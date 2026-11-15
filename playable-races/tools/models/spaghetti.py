"""Race 005 - Flying Spaghetti Monster.

The deity of Pastafarianism (Bobby Henderson's 2005 open letter to the Kansas State
Board of Education): a floating tangle of living spaghetti with two meatballs and
two eyes on stalks.  Here it is a playable body:

  * a dense, asymmetrical mass of curved noodle strands (generated as chains of thin
    rotated segments) split into twist groups that slowly circulate
  * dangling strands underneath and trailing strands behind (they stream back like
    a comet when it moves)
  * exactly two meatballs on orbit pivots (they leave and return for Meatball Ricochet
    and circle the vortex in the Great Pasta Revelation)
  * two eyes on long noodle stalks, each with its own lid (independent looks/blinks)
  * tomato sauce on the strands, a sauce crown and drips that can flow upward
  * improvised noodle arms bound to the player's arms - they only form while that
    hand holds something (or strikes), so tools sit in a "hand" of braided strands
  * Al Dente: straight, dry spaghetti rods lock into a rigid lattice
  * the Revelation: three spiral layers of noodles unfold around the body

Variants: base | rigid | detached | revelation | brittle (singed by fire).
"""
from __future__ import annotations

import math

import numpy as np

from kit.geo import Model
from kit.tex import Ctx, hx
from kit import noise as nz
from models.common import humanoid, fp_sleeves, ramp, bevel, face_light, mix3, clamp01, accents, mat_accent

ID = "spaghetti"
VARIANTS = ["base", "rigid", "detached", "revelation", "brittle"]
TEXTURES = {
    "base": {"dente": 0.0, "burnt": 0.0, "glow": 0.0},
    "dente": {"dente": 1.0, "burnt": 0.0, "glow": 0.0},
    "burnt": {"dente": 0.3, "burnt": 1.0, "glow": 0.0},
    "holy": {"dente": 0.0, "burnt": 0.0, "glow": 1.0},
}
VARIANT_TEXTURE = {"base": "base", "rigid": "dente", "detached": "base", "revelation": "holy", "brittle": "burnt"}
CENTER = (0.0, 13.0, 0.4)
GROUPS = 6
HANG = 6


def _dir_rot(d):
    """Bedrock cube rotation that points a cube's +Z axis along d."""
    d = np.asarray(d, float)
    d = d / max(np.linalg.norm(d), 1e-9)
    rx = math.degrees(math.asin(max(-1.0, min(1.0, d[1]))))
    ry = math.degrees(math.atan2(d[0], d[2]))
    return (rx, ry, 0.0)


def strand(m: Model, bone: str, pts, thick: float, mat: str, ppu: float = 1.0, **kw) -> None:
    """A noodle along a polyline: one rotated segment per span (1 texel per unit: noodles
    are plain, and hundreds of segments must fit one 256x256 atlas)."""
    for a, b in zip(pts[:-1], pts[1:]):
        a, b = np.asarray(a, float), np.asarray(b, float)
        ln = float(np.linalg.norm(b - a))
        if ln < 0.2:
            continue
        m.cube(bone, (a[0] - thick / 2, a[1] - thick / 2, a[2]), (thick, thick, ln + thick * 0.35), mat,
               pivot=tuple(a), rot=_dir_rot(b - a), ppu=ppu, **kw)


def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=512)
    humanoid(m)
    rng = np.random.default_rng(5)
    mass = m.bone("mass", "torso_g", CENTER)
    for g in range(GROUPS):
        m.bone(f"twist{g}", mass.name, CENTER)
    _mass(m, rng)
    _hanging(m, rng)
    _meatballs(m)
    _eyes(m)
    _sauce(m)
    _arms(m)
    _lattice(m)
    _spirals(m)
    fp_sleeves(m, "braid", width=4.4)
    accents(m, [
        ("c", "band", "mass", (0, 14.5, -6.2), (8.0, 1.2, 0.5)),
        ("c", "rsh", "r_arm_g", (-6.0, 19.0, 0.0), (2.6, 1.0, 2.6)),
        ("c", "lsh", "l_arm_g", (6.0, 19.0, 0.0), (2.6, 1.0, 2.6)),
        ("l", "skirt", "mass", (0, 7.6, -4.6), (7.0, 0.8, 0.5)),
        ("f", "tip", "hang0", (0, 3.4, -1.0), (1.4, 0.8, 1.4)),
    ])
    m.pack()
    return m


# ----------------------------------------------------------------------------- the noodle mass

def _loop(c, r, normal, start, span, n, wobble, rng):
    normal = np.asarray(normal, float)
    normal /= np.linalg.norm(normal)
    a = np.cross(normal, [0.0, 1.0, 0.0])
    if np.linalg.norm(a) < 1e-3:
        a = np.cross(normal, [1.0, 0.0, 0.0])
    a /= np.linalg.norm(a)
    b = np.cross(normal, a)
    pts = []
    for k in range(n + 1):
        t = math.radians(start + span * k / n)
        rr = r * (1 + wobble * math.sin(3 * t + rng.uniform(0, 6)))
        pts.append(np.asarray(c) + a * math.cos(t) * rr + b * math.sin(t) * rr)
    return pts


def _mass(m: Model, rng) -> None:
    cx, cy, cz = CENTER
    # an ellipsoidal tangle: wide (1.1 blocks), a little flattened, lumpy
    for k in range(40):
        g = k % GROUPS
        back = 2.4 if k >= 34 else 0.0          # extra strands over the back
        c = (cx + rng.uniform(-3.6, 3.6), cy + rng.uniform(-2.6, 3.0), cz + rng.uniform(-1.8, 1.8) + back)
        r = rng.uniform(3.6, 6.4)
        normal = rng.normal(size=3)
        span = rng.uniform(150, 300)
        pts = _loop(c, r, normal, rng.uniform(0, 360), span, max(6, int(span / 20)), 0.1, rng)
        # pull every strand onto an ellipsoidal shell (1.1 blocks wide) so the tangle reads as one mass
        out = []
        for q in pts:
            d = (q - np.array(CENTER)) / np.array([8.6, 6.6, 6.0])
            n = np.linalg.norm(d)
            f = (0.78 + 0.22 * rng.uniform()) / max(n, 0.35) if n > 1.0 or n < 0.7 else 1.0
            out.append(np.array(CENTER) + (q - np.array(CENTER)) * f)
        strand(m, f"twist{g}", out, 0.95 if k % 5 else 1.2, "noodle")
    # a dense core so the tangle never looks hollow
    m.box("mass", (cx, cy, cz), (11.4, 8.8, 7.4), "noodle_core")
    m.box("mass", (cx, cy + 4.4, cz), (9.4, 2.4, 6.4), "noodle_core")
    m.box("mass", (cx, cy - 4.8, cz), (9.0, 2.2, 6.0), "noodle_core")
    m.bones["mass"].locators["core"] = CENTER
    m.bones["mass"].locators["top"] = (cx, cy + 6.5, cz)


def _hanging(m: Model, rng) -> None:
    """Strands dangling below and streaming behind (3-joint chains so they can sway)."""
    cx, cy, cz = CENTER
    spots = [(-3.4, 7.2, -2.4), (2.8, 7.0, -2.6), (-0.6, 6.6, 0.8), (4.6, 7.8, 1.6), (-5.0, 8.0, 1.2), (1.0, 7.0, 3.6)]
    for k, (x, y, z) in enumerate(spots[:HANG]):
        parent = "mass"
        px, py, pz = x, y, z
        for j in range(3):
            name = f"hang{k}" if j == 0 else f"hang{k}_{j}"
            b = m.bone(name, parent, (px, py, pz))
            ln = 2.2 - j * 0.3
            dx, dz = rng.uniform(-0.6, 0.6), rng.uniform(-0.3, 0.9)
            end = (px + dx, py - ln, pz + dz)
            strand(m, name, [(px, py, pz), end], 0.85, "noodle")
            parent, (px, py, pz) = name, end
        if k == 0:
            m.bones[parent].locators["drip"] = (px, py - 0.4, pz)
    # trailing strands behind: they stretch out in motion (scale z)
    for k, (x, y) in enumerate(((-2.4, 14.6), (1.8, 11.4), (0.2, 16.8), (-0.8, 9.6))):
        name = f"trail{k}"
        b = m.bone(name, "mass", (x, y, cz + 3.2))
        strand(m, name, [(x, y, cz + 3.2), (x + 0.6, y - 0.8, cz + 6.2), (x - 0.3, y - 1.8, cz + 8.6)], 0.8, "noodle")


def _ball(m: Model, bone: str, c, r: float, mat: str, round_more: bool = True, **kw) -> None:
    x, y, z = c
    m.box(bone, c, (2 * r, 2 * r * 0.74, 2 * r * 0.74), mat, **kw)
    m.box(bone, c, (2 * r * 0.74, 2 * r, 2 * r * 0.74), mat, **kw)
    m.box(bone, c, (2 * r * 0.74, 2 * r * 0.74, 2 * r), mat, **kw)
    if round_more:
        k = 2 * r * 0.86
        for rot in ((0, 45, 0), (45, 0, 0), (0, 0, 45)):
            m.cube(bone, (x - k / 2, y - k / 2, z - k / 2), (k, k, k), mat, pivot=c, rot=rot, **kw)


def _meatballs(m: Model) -> None:
    keep = set(VARIANTS) - {"detached"}
    for side, p, c in ((-1, "r", (-5.8, 12.0, -2.2)), (1, "l", (5.4, 14.6, -1.6))):
        orb = m.bone(f"orbit_{p}", "torso_g", CENTER)
        mb = m.bone(f"meatball_{p}", orb.name, c, only=keep)
        # the Revelation flings them out to orbit around the vortex
        mb.variant.update({"revelation": ((side * 5.0, 1.0, -1.0), None)})
        _ball(m, mb.name, c, 3.3, "meatball", only=keep)
        m.box(mb.name, (c[0], c[1] + 2.9, c[2]), (3.6, 0.6, 3.4), "sauce", only=keep)      # sauce cap
        mb.locators[f"{p}_meatball"] = c


def _eyes(m: Model) -> None:
    for side, p, base in ((-1, "r", (-3.0, 18.6, 0.6)), (1, "l", (3.2, 19.0, 0.2))):
        parent = "mass"
        x, y, z = base
        for j in range(3):
            name = f"stalk_{p}{j}"
            b = m.bone(name, parent, (x, y, z), (6 * (j - 1), 0, side * 7 * (j + 1) * 0.6))
            if j == 0:
                b.variant.update({"revelation": ((side * 1.5, 4.5, 0.0), None)})
            ln = 2.6
            strand(m, name, [(x, y, z), (x, y + ln, z)], 1.0, "noodle")
            parent, y = name, y + ln
        eye = m.bone(f"eye_{p}", parent, (x, y + 1.6, z))
        _ball(m, eye.name, (x, y + 1.6, z), 1.75, "eyeball", round_more=False)
        lid = m.bone(f"lid_{p}", eye.name, (x, y + 3.45, z))
        m.cube(lid.name, (x - 1.9, y + 3.15, z - 1.9), (3.8, 0.3, 3.8), "eyelid")              # scale y ~11 closes
        eye.locators[f"{p}_eye"] = (x, y + 1.6, z - 1.8)


def _sauce(m: Model) -> None:
    cx, cy, cz = CENTER
    crown = m.bone("sauce", "mass", (cx, cy + 4.6, cz))
    m.box(crown.name, (cx + 0.6, cy + 5.8, cz - 0.2), (6.6, 1.0, 5.0), "sauce")
    m.box(crown.name, (cx + 0.2, cy + 6.5, cz + 0.2), (3.8, 0.8, 3.0), "sauce")
    m.box(crown.name, (cx - 3.4, cy + 5.2, cz - 2.6), (2.6, 1.0, 2.2), "sauce")
    m.box(crown.name, (cx + 4.0, cy + 4.9, cz + 1.8), (2.2, 1.0, 2.6), "sauce")
    for k, (x, z, ln) in enumerate(((-3.8, -4.6, 2.8), (1.4, -4.9, 3.6), (4.6, -3.4, 2.2), (-1.6, -5.0, 1.6))):
        d = m.bone(f"drip{k}", crown.name, (x, cy + 5.2, z))
        m.box(d.name, (x, cy + 5.2 - ln / 2, z), (0.9, ln, 0.9), "sauce")
        m.box(d.name, (x, cy + 5.2 - ln - 0.4, z), (1.3, 1.1, 1.3), "sauce")


def _arms(m: Model) -> None:
    """Improvised arms: braided strands from the mass to the player's hand position."""
    for side, g, p in ((-1, "r_arm_g", "r"), (1, "l_arm_g", "l")):
        ax = 5.8 * side
        app = m.bone(f"{p}_appendage", g, (5.0 * side, 22.0, 0.0))
        for k in range(3):
            ph = k * 2.1
            pts = [(ax + 0.7 * math.cos(ph + t * 1.6), 21.0 - t * 1.25, 0.7 * math.sin(ph + t * 1.6)) for t in range(9)]
            strand(m, app.name, pts, 0.75, "braid")
        hand = m.bone(f"{p}_grip", app.name, (ax, 10.4, 0.0))
        for k in range(5):
            a = k * 72
            dx, dz = math.cos(math.radians(a)) * 1.0, math.sin(math.radians(a)) * 1.0
            strand(m, hand.name, [(ax + dx * 0.6, 10.6, dz * 0.6), (ax + dx * 1.3, 9.0, dz * 1.3), (ax + dx * 0.6, 7.8, dz * 0.6)], 0.6, "braid")


def _lattice(m: Model) -> None:
    """Al Dente: dry spaghetti rods snap into a rigid lattice around the body."""
    cx, cy, cz = CENTER
    lat = m.bone("lattice", "torso_g", CENTER, only={"rigid"})
    rng = np.random.default_rng(11)
    for k in range(16):
        ang = math.radians(k * 360 / 16)
        r = 8.6
        a = (cx + math.cos(ang) * r, cy - 6.5, cz + math.sin(ang) * r * 0.8)
        ang2 = ang + math.radians(rng.choice([-50, 50]))
        b = (cx + math.cos(ang2) * r, cy + 7.0, cz + math.sin(ang2) * r * 0.8)
        strand(m, lat.name, [a, b], 0.55, "rod", only={"rigid"})
    for y in (cy - 3.0, cy + 3.5):
        pts = [(cx + math.cos(math.radians(t)) * 8.9, y, cz + math.sin(math.radians(t)) * 7.1) for t in range(0, 361, 30)]
        strand(m, lat.name, pts, 0.5, "rod", only={"rigid"})


def _spirals(m: Model) -> None:
    """The Great Pasta Revelation: three spiral layers of living noodles."""
    cx, cy, cz = CENTER
    for k, (r0, r1, y, turns) in enumerate(((9.0, 15.0, cy - 1.0, 1.3), (14.0, 22.0, cy + 3.0, 1.1), (20.0, 28.0, cy - 4.0, 0.9))):
        sp = m.bone(f"spiral{k}", "torso_g", CENTER, only={"revelation"})
        pts = []
        n = int(28 * turns)
        for i in range(n + 1):
            t = i / n
            ang = t * 360 * turns + k * 120
            r = r0 + (r1 - r0) * t
            pts.append((cx + math.cos(math.radians(ang)) * r, y + math.sin(math.radians(ang * 2)) * 1.2, cz + math.sin(math.radians(ang)) * r))
        strand(m, sp.name, pts, 1.1 - k * 0.15, "noodle", only={"revelation"})
        strand(m, sp.name, [(p[0] * 0.97, p[1] + 1.2, p[2] * 0.97) for p in pts[::2]], 0.7, "sauce_strand", only={"revelation"})


# ============================================================================= materials

def materials():
    return {"noodle": mat_noodle, "noodle_core": mat_core, "braid": mat_braid, "meatball": mat_meatball, "eyelid": mat_eyelid,
            "eyeball": mat_eyeball, "sauce": mat_sauce, "sauce_strand": mat_sauce_strand, "rod": mat_rod,
            "accent": mat_accent}


def _P(ctx):
    return ctx.params.get("dente", 0.0), ctx.params.get("burnt", 0.0), ctx.params.get("glow", 0.0)


def _pasta(ctx: Ctx, light=0.0):
    dente, burnt, glow = _P(ctx)
    p = ctx.p
    n = nz.fbm(p, 0.9, 2, seed=3)
    c = ramp([(0, "#dcb866"), (0.45, "#efd894"), (0.8, "#f8e9b8"), (1, "#fff5d6")], n * 0.6 + 0.35 + light)
    c = mix3(c, hx("#f2cf52"), 0.35 * dente)              # al dente: deeper, drier yellow
    # sauce coating in patches (coherent across neighbouring strands)
    sauce = nz.smoothstep(0.7, 0.78, nz.fbm(p * 0.7 + 11.0, 0.45, 2, seed=9))
    red = ramp([(0, "#8e1a14"), (0.6, "#c4301f"), (1, "#e35a36")], nz.fbm(p, 1.6, 2, seed=4))
    c = mix3(c, red, sauce * (1 - 0.6 * dente))
    if burnt > 0:
        scorch = nz.smoothstep(0.45, 0.8, nz.fbm(p * 1.4, 0.8, 2, seed=21))
        c = mix3(c, hx("#7a4a1c"), scorch * 0.8 * burnt)
        c = mix3(c, hx("#2c1a0c"), nz.smoothstep(0.82, 0.9, nz.fbm(p, 1.5, 2, seed=2)) * burnt)
    g = ctx.zeros() + 0.0
    if glow > 0:
        g = g + 0.18 * glow
        c = mix3(c, hx("#fff4c2"), 0.25 * glow)
    return c, sauce, g


def mat_noodle(ctx):
    c, sauce, g = _pasta(ctx)
    if ctx.face == "up":
        c = c * 1.12
    elif ctx.face == "down":
        c = c * 0.78
    # glossy highlight along the strand (wet pasta)
    v = ctx.t / max(ctx.fh, 1e-6)
    gloss = (np.abs(v - 0.3) < 0.12) & (ctx.face in ("east", "west", "up"))
    c = np.where(gloss[:, None], mix3(c, hx("#ffffff"), 0.35), c)
    return c, ctx.ones(), g


def mat_core(ctx):
    """The tangle's interior: many tiny crossing strands and pooled sauce."""
    c, sauce, g = _pasta(ctx, light=-0.12)
    u = ctx.s
    v = ctx.t
    w = nz.value(ctx.p, 0.8, seed=31) * 6.28
    lines = np.abs(np.mod(u * np.cos(w) + v * np.sin(w), 1.0) - 0.5) < 0.18
    c = np.where(lines[:, None], c * 1.1, c * 0.82)
    return c, ctx.ones(), g


def mat_braid(ctx):
    c, sauce, g = _pasta(ctx, light=0.05)
    twist = np.mod(ctx.t * 1.2 + ctx.s * 0.8, 1.0) < 0.5
    return np.where(twist[:, None], c * 1.06, c * 0.88), ctx.ones(), g


def mat_meatball(ctx):
    dente, burnt, glow = _P(ctx)
    p = ctx.p
    n = nz.fbm(p, 1.1, 3, seed=14)
    c = ramp([(0, "#4a2214"), (0.4, "#7a3a20"), (0.75, "#9c5530"), (1, "#bb7244")], n)
    crust = nz.hash_points(p, 0.5, 7) < 0.18
    c = np.where(crust[:, None], c * 0.62, c)
    fat = nz.hash_points(p, 0.5, 23) < 0.05
    c = np.where(fat[:, None], mix3(c, hx("#d9a27a"), 0.6), c)
    herb = nz.hash_points(p, 0.5, 19) < 0.012
    c = np.where(herb[:, None], hx("#4e7a2c"), c)
    if ctx.face == "up":
        c = np.where((nz.fbm(p, 0.8, 2, seed=8) > 0.5)[:, None], hx("#b02a1a"), c)
    c = mix3(c, hx("#1e0f06"), 0.5 * burnt)
    return bevel(ctx, face_light(ctx, c, 0.12, 0.25), 0.25, 0.9), ctx.ones(), ctx.zeros() + 0.12 * glow


def mat_eyeball(ctx):
    dente, burnt, glow = _P(ctx)
    c = np.broadcast_to(hx("#f7f5ee"), (ctx.N, 3)).copy()
    vein = nz.smoothstep(0.86, 0.93, nz.ridged(ctx.p, 1.2, 2, seed=3))
    c = mix3(c, hx("#d76b6b"), vein * 0.5)
    g = ctx.zeros()
    if ctx.face == "north":
        u = ctx.s / ctx.fw - 0.5
        v = ctx.t / ctx.fh - 0.5
        r = np.sqrt(u * u + v * v)
        iris = r < 0.36
        c = np.where(iris[:, None], ramp([(0, "#2e2010"), (1, "#6b4a22")], r / 0.36), c)
        pupil = r < 0.2
        c = np.where(pupil[:, None], hx("#050403"), c)
        hl = ((u + 0.1) ** 2 + (v + 0.12) ** 2) < 0.006
        c = np.where(hl[:, None], hx("#ffffff"), c)
        g = np.where(iris & ~pupil, 0.15 * glow, 0.0)
    return face_light(ctx, c, 0.06, 0.12), ctx.ones(), g


def mat_eyelid(ctx):
    dente, burnt, glow = _P(ctx)
    c = mix3(hx("#f1dca0"), hx("#fff1c8"), nz.fbm(ctx.p, 1.2, 2, seed=5))
    return face_light(ctx, c, 0.1, 0.2), ctx.ones(), ctx.zeros()


def mat_sauce(ctx):
    dente, burnt, glow = _P(ctx)
    n = nz.fbm(ctx.p, 1.4, 3, seed=6)
    c = ramp([(0, "#7a120c"), (0.5, "#b8261a"), (0.85, "#e04a2c"), (1, "#ff8a5c")], n)
    chunk = nz.hash_points(ctx.p, 0.5, 12) < 0.08
    c = np.where(chunk[:, None], hx("#9e2a18"), c)
    shine = (nz.hash_points(ctx.p, 0.5, 2) < 0.05) & (ctx.face == "up")
    c = np.where(shine[:, None], hx("#ffd0b8"), c)
    c = mix3(c, hx("#3a0c06"), 0.5 * burnt)
    return c, ctx.ones(), ctx.zeros() + 0.2 * glow


def mat_sauce_strand(ctx):
    c, a, g = mat_sauce(ctx)
    return c, a, g + 0.35


def mat_rod(ctx):
    n = nz.value(ctx.p * np.array([4, 0.4, 4]), 1.0, seed=2)
    c = ramp([(0, "#d9b04a"), (1, "#f3d983")], n)
    crack = nz.hash_points(ctx.p, 0.5, 4) < 0.06
    c = np.where(crack[:, None], c * 0.7, c)
    return face_light(ctx, c, 0.1, 0.2), ctx.ones(), ctx.zeros()


# ============================================================================= the meatball entity

def build_meatball() -> Model:
    """The detached meatball (Meatball Ricochet): its own small entity model."""
    m = Model("meatball", ppu=2.0, atlas_width=128)
    m.bone("root", None, (0, 0, 0))
    ball = m.bone("ball", "root", (0, 4.0, 0))
    _ball(m, ball.name, (0, 4.0, 0), 3.4, "meatball")
    m.box(ball.name, (0, 6.9, 0), (3.6, 0.6, 3.4), "sauce")
    # two noodle tethers trailing behind it (they lead back to the body)
    for k, (dx, dy) in enumerate(((-1.2, 0.6), (1.0, -0.4))):
        tb = m.bone(f"tether{k}", ball.name, (dx, 4.0 + dy, 3.0))
        strand(m, tb.name, [(dx, 4.0 + dy, 3.0), (dx * 1.6, 4.0 + dy * 2, 6.4), (dx, 4.0 + dy, 9.6)], 0.7, "noodle")
    ball.locators["trail"] = (0, 4.0, 2.5)
    m.pack()
    return m
