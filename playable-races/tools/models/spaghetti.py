"""Race 005 - Flying Spaghetti Monster.  (v1.2 redesign: "the appetising deity")

The deity of Pastafarianism (Bobby Henderson's 2005 open letter to the Kansas State
Board of Education): a floating mass of spaghetti with two meatballs and two eyes on
stalks.  Drawn as absurd-but-premium food art - a plate of spaghetti and meatballs
without the plate:

  * a round nest of glossy golden pasta floating over a clear gap; the nest is built from
    twelve staggered slices and painted with strands wound around it (continuous across
    every face), a few real loops lift off the surface and break the outline
  * two seared meatballs sitting on its shoulders, glazed with marinara
  * a ladle of sauce poured over the top that runs down the sides - one drip runs UP
  * two big round eyes on noodle stalks, each with a sliding pupil and its own lid
  * His Noodly Appendages: two curling noodles at the sides, a fringe of short curls below
  * a golden perforated halo with two handles - the Holy Colander's rim
  * noodle braids that form arms only while a hand holds something
  * Al Dente: dry spaghetti rods lock into a lattice; the Revelation: three spiral
    layers of pasta unfold around the body

Variants: base | rigid | detached | revelation | brittle (singed by fire).
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

from kit.geo import Model
from kit import pixel as px
from models.common import accents, chain, ellipsoid, fp_sleeves, humanoid, mat_accent, q, segment

ID = "spaghetti"
VARIANTS = ["base", "rigid", "detached", "revelation", "brittle"]
TEXTURES = {
    "base": {"dente": 0.0, "burnt": 0.0, "holy": 0.0},
    "dente": {"dente": 1.0, "burnt": 0.0, "holy": 0.0},
    "burnt": {"dente": 0.0, "burnt": 1.0, "holy": 0.0},
    "holy": {"dente": 0.0, "burnt": 0.0, "holy": 1.0},
}
VARIANT_TEXTURE = {"base": "base", "rigid": "dente", "detached": "base", "revelation": "holy", "brittle": "burnt"}
CENTER = (0.0, 13.5, 0.5)            # centre of the pasta nest
SEMI = (8.0, 6.0, 7.0)               # its semi-axes (16 x 12 x 14)
GROUPS = 3                           # twist groups of loose loops
HANG = 2                             # short hooked danglers below
DRAPES = 3                           # U-loops drooping below
APP = 4                              # segments of each noodly appendage
EYES = {-1: (-4.25, 27.0, -1.0), 1: (4.25, 27.25, -0.75)}
EYE_D = 5.0
MEATBALLS = {-1: (-5.0, 19.25, -2.75), 1: (5.0, 19.25, -2.75)}
MB_D = 5.5
HALO_C = (0.0, 31.25, 0.25)
HALO_R = 4.5
STRAND_PITCH = 1.5                   # painted strand spacing on the nest (3 texels)

PASTA = px.pal("#74440f", "#b47c26", "#dea843", "#f2ca68", "#fde296", "#fff3c9")
DRY = px.pal("#7e6128", "#b08f47", "#d8bc75", "#ecd9a0", "#faf0cc")
BURNT = px.pal("#24140a", "#4c2c13", "#7a4c1f", "#a8783c", "#cfa56a")
HOLY = px.pal("#8a5a14", "#c08a2c", "#e6b74c", "#f8d978", "#fff0b0", "#fffbe6")
SAUCE = px.pal("#3e0806", "#6e120e", "#a5221a", "#cf3a28", "#ec6248")
GLOSS = px.col("#ffd6c2")
MEAT = px.pal("#47220f", "#683319", "#8a4825", "#a65d31", "#c07745", "#d89662")
MEAT_BURNT = px.pal("#140a06", "#2a160c", "#432414", "#5e3520", "#7a4a2e")
GOLD = px.pal("#5b3b10", "#8c6420", "#c0902f", "#e6bb55", "#fbe39a")
EYE = px.pal("#a29c92", "#d2cdc3", "#ebe7de", "#f7f5ef", "#ffffff")
HERB = px.col("#4f7a3a")


# ============================================================================= the nest's shape

@lru_cache(maxsize=None)
def core_boxes():
    """Twelve staggered slices: per 2-unit band one wide-in-x and one deep-in-z box (a plus-
    shaped, nearly round cross-section), the z-boxes offset by half a unit so that no two
    boxes ever share a face plane (no z-fighting).  Returns ((centre), (size)) pairs."""
    cx, cy, cz = CENTER
    sx, sy, sz = SEMI
    out = []
    for i in range(6):
        for kind, y0 in (("x", 7.5 + 2 * i), ("z", 8.0 + 2 * i)):
            y1 = y0 + 2.0
            d = 0.0 if y0 <= cy <= y1 else min(abs(y0 - cy), abs(y1 - cy))
            r = math.sqrt(max(0.0, 1.0 - (d / sy) ** 2))
            if kind == "x":
                size = (q(2 * sx * r, 1.0), 2.0, q(2 * sz * r * 0.72, 1.0))
            else:
                size = (q(2 * sx * r * 0.72, 1.0), 2.0, q(2 * sz * r, 1.0))
            out.append(((cx, (y0 + y1) / 2, cz), size))
    return tuple(out)


def _inside(p) -> bool:
    for c, s in core_boxes():
        if all(abs(p[i] - c[i]) <= s[i] / 2 for i in range(3)):
            return True
    return False


def surf(d, grow: float = 0.0) -> np.ndarray:
    """Point on the voxel nest's surface along direction d from the centre (+ grow)."""
    d = np.asarray(d, float)
    d = d / np.linalg.norm(d)
    c = np.array(CENTER)
    t = 0.0
    while _inside(c + d * (t + 0.05)) and t < 20:
        t += 0.05
    return c + d * (t + grow)


def sphere_dir(phi: float, theta: float) -> np.ndarray:
    """Direction for ellipsoidal polar angle phi (0 = top) and azimuth theta (atan2(z, x))."""
    p, t = math.radians(phi), math.radians(theta)
    v = np.array([math.sin(p) * math.cos(t) * SEMI[0], math.cos(p) * SEMI[1], math.sin(p) * math.sin(t) * SEMI[2]])
    return v / np.linalg.norm(v)


def strand(m: Model, bone: str, pts, thick: float, mat: str, **kw) -> None:
    for a, b in zip(pts[:-1], pts[1:]):
        if np.linalg.norm(np.asarray(b) - np.asarray(a)) < 0.3:
            continue
        segment(m, bone, a, b, thick, thick, mat, overlap=0.3, **kw)


# ============================================================================= build

def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=256)
    humanoid(m)
    mass = m.bone("mass", "torso_g", CENTER)
    for g in range(GROUPS):
        m.bone(f"twist{g}", mass.name, CENTER)
    _nest(m)
    _loops(m)
    _curls(m)
    _appendages(m)
    _meatballs(m)
    _eyes(m)
    _sauce(m)
    _halo(m)
    _arms(m)
    _lattice(m)
    _spirals(m)
    fp_sleeves(m, "braid", width=4.5)
    accents(m, [
        ("c", "band", "mass", (0, 13.5, -6.75), (8.0, 1.0, 0.5)),
        ("c", "rsh", "r_arm_g", (-6.0, 19.0, 0.0), (2.5, 1.0, 2.5)),
        ("c", "lsh", "l_arm_g", (6.0, 19.0, 0.0), (2.5, 1.0, 2.5)),
        ("l", "skirt", "mass", (0, 8.25, -4.75), (7.0, 0.5, 0.5)),
        ("f", "tip", "hang0_0", (0.0, 5.0, -1.25), (1.5, 0.5, 1.5)),
    ])
    m.pack()
    return m


def _nest(m: Model) -> None:
    for c, s in core_boxes():
        m.box("mass", c, s, "noodle_core")
    m.bones["mass"].locators["core"] = CENTER
    m.bones["mass"].locators["top"] = (0.0, 21.5, CENTER[2])


LOOPS = [  # (polar deg, azimuth from, azimuth to, lift, tilt) - azimuth: 0 = left side, -90 = front, 180 = right
    (84.0, -172.0, -118.0, 1.0, 14.0),
    (70.0, -58.0, 6.0, 1.0, -16.0),
    (98.0, 24.0, 92.0, 1.0, 12.0),
    (66.0, 112.0, 176.0, 1.0, -12.0),
]


def _loops(m: Model) -> None:
    """Loose strands wound the same way as the painted ones, lifting off the surface in the
    middle: they break the outline into something soft and noodly."""
    for k, (phi, t0, t1, lift, tilt) in enumerate(LOOPS):
        pts = []
        n = 6
        for j in range(n + 1):
            f = j / n
            d = sphere_dir(phi + tilt * (f - 0.5), t0 + (t1 - t0) * f)
            pts.append(surf(d, 0.3 + lift * math.sin(math.pi * f)))
        strand(m, f"twist{k % GROUPS}", pts, 1.0, "noodle")


def _curls(m: Model) -> None:
    """Under the floating nest: three noodles drooping in U-loops (both ends attached, so they
    can only swing - never read as legs) and two short hooked danglers."""
    for k, (a, b, sag) in enumerate((((-4.5, 7.75, -1.25), (-1.25, 7.75, -2.25), 2.25),
                                     ((1.0, 7.75, -2.25), (4.5, 7.75, -0.75), 2.0),
                                     ((-2.25, 7.75, 2.75), (2.5, 7.75, 3.25), 2.5))):
        a, b = np.array(a), np.array(b)
        mid = (a + b) / 2
        dr = m.bone(f"drape{k}", "mass", tuple(mid))
        pts = [a, a + (b - a) * 0.22 + (0, -sag * 0.85, 0), b + (a - b) * 0.22 + (0, -sag * 0.85, 0), b]
        pts[1] = pts[1] + (0, -0.0, 0)
        strand(m, dr.name, [tuple(p) for p in pts], 0.75, "noodle")
    for k, (x, z, L) in enumerate(((0.0, -1.25, 1.0), (3.0, 2.25, 0.8))):
        s = 1 if k == 0 else -1
        y = 7.75
        pts = [(x, y, z), (x + 0.5 * s, y - 1.75 * L, z - 0.25), (x - 0.25 * s, y - 3.0 * L, z),
               (x - 1.25 * s, y - 3.25 * L, z + 0.25)]
        chain(m, "mass", f"hang{k}_", pts, [0.75, 0.75, 0.5], "noodle")
        m.bones[f"hang{k}_{2}"].locators[f"tip{k}"] = pts[-1]


def _appendages(m: Model) -> None:
    """His Noodly Appendages: a curling noodle at each side."""
    for s, p in ((-1, "r"), (1, "l")):
        pts = [(s * 7.5, 13.5, 0.0), (s * 9.5, 13.0, 1.25), (s * 10.75, 12.5, 3.0), (s * 11.25, 12.75, 5.0),
               (s * 11.0, 13.5, 6.75)]
        chain(m, "mass", f"{p}_app", pts, [1.0, 1.0, 0.75, 0.75], "noodle")


def _meatballs(m: Model) -> None:
    for s, p in ((-1, "r"), (1, "l")):
        c = MEATBALLS[s]
        orb = m.bone(f"{p}_orbit", "mass", (0.0, c[1], CENTER[2]))
        mb = m.bone(f"{p}_meatball", orb.name, c)
        mb.variant["revelation"] = ((s * 4.0, 3.5, 1.5), None)
        ellipsoid(m, mb.name, c, (MB_D, MB_D, MB_D), "meatball", a=0.667, b=0.75, skip={"detached"})
        # the sauce-filled socket left behind while the meatballs ricochet (detached form)
        m.box("mass", (c[0], 19.75, -2.25), (4.0, 0.5, 3.5), "socket", only={"detached"})
        mb.locators[f"{p}_meatball_c"] = c          # locator names never repeat a bone name


def _eyes(m: Model) -> None:
    for s, p in ((-1, "r"), (1, "l")):
        ex, ey, ez = EYES[s]
        pts = [(s * 2.0, 19.75, 0.75), (s * 2.75, 22.25, 0.25), (s * 3.5, 24.25, -0.5), (ex, ey - 1.5, ez)]
        names = chain(m, "mass", f"{p}_stalk", pts, [1.0, 1.0, 0.75], "noodle")
        m.bones[names[0]].variant["revelation"] = ((0, 1.0, 0), (-8.0, 0, -s * 14.0))
        eye = m.bone(f"{p}_eye", names[-1], (ex, ey, ez))
        ellipsoid(m, eye.name, (ex, ey, ez), (EYE_D, EYE_D, EYE_D), "eyeball", a=0.6, b=0.7)
        pupil = m.bone(f"{p}_pupil", eye.name, (ex, ey, ez - EYE_D / 2))
        m.box(pupil.name, (ex, ey, ez - EYE_D / 2 - 0.25), (3.0, 3.0, 0.5), "pupil", ppu=4.0)
        # the lid hangs in front of the eye when closed; at rest it is folded back over the top
        lid = m.bone(f"{p}_lid", eye.name, (ex, ey + 2.5, ez - 3.0), (90.0, 0.0, 0.0))
        m.box(lid.name, (ex, ey + 0.5, ez - 3.25), (3.5, 4.0, 0.5), "lid")
        eye.locators[f"{p}_eye_c"] = (ex, ey, ez - 3.0)


def _sauce(m: Model) -> None:
    sb = m.bone("sauce", "mass", (0.0, 20.5, 0.5))
    m.box(sb.name, (0.0, 20.25, 0.5), (7.0, 0.75, 9.5), "sauce")                 # the ladleful
    m.box(sb.name, (0.0, 20.875, 0.75), (4.5, 0.5, 5.5), "sauce")                # its rounded top
    m.box(sb.name, (1.75, 21.375, -1.25), (2.5, 0.25, 1.5), "basil", rot=(0, 25, 0), pivot=(1.75, 21.375, -1.25))
    drips = [  # (x, z, top, length, face normal) running down the outside of the nest
        (0.25, -4.75, 20.25, 2.25, (0, 0, -1)),
        (6.25, 1.75, 19.75, 2.0, (1, 0, 0)),
        (-6.25, 0.75, 19.75, 2.5, (-1, 0, 0)),
        (-1.5, 5.75, 20.0, 2.0, (0, 0, 1)),
    ]
    for k, (x, z, top, ln, nrm) in enumerate(drips):
        d = m.bone(f"drip{k}", sb.name, (x, top, z))
        thin = (0.5 if nrm[0] else 1.0, ln, 1.0 if nrm[0] else 0.5)
        m.box(d.name, (x, top - ln / 2, z), thin, "sauce")
        m.box(d.name, (x + nrm[0] * 0.25, top - ln - 0.25, z + nrm[2] * 0.25), (1.5, 1.0, 1.5), "sauce")   # the drop
        if k == 0:
            d.locators["drip"] = (x, top - ln - 0.75, z - 0.25)
        if nrm[0]:   # a film of sauce over the rim and across the terrace to the drip
            m.box(d.name, (x - nrm[0] * 1.25, 19.625, z), (2.5, 0.25, 1.0), "sauce")
            m.box(d.name, (x - nrm[0] * 2.375, 20.0, z), (0.75, 0.75, 1.0), "sauce")
    up = m.bone("drip_up", sb.name, (-1.5, 21.0, -1.75))                         # a bead that will run UP
    m.box(up.name, (-1.5, 21.5, -1.75), (1.25, 1.0, 1.25), "sauce")
    sb.locators["sauce_top"] = (-1.5, 22.5, -1.75)


def _halo(m: Model) -> None:
    """The Holy Colander's rim: a perforated golden band with two handles, worn as a halo."""
    cx, cy, cz = HALO_C
    # v1.3.1: the halo rides the head group (it follows a fifth of the player's look) - the
    # Spaghetti Monster was the only race with nothing under its head bone
    h = m.bone("halo", "head_g", HALO_C, (78.0, 0.0, 8.0))
    n = 12
    seg = q(2 * HALO_R * math.tan(math.pi / n) + 0.3)
    for k in range(n):
        ang = 360.0 / n * (k + 0.5)
        ang = ang - 360.0 if ang > 180.0 else ang          # cube angles kept within (-180, 180]
        m.cube(h.name, (cx - seg / 2, cy + HALO_R - 0.375, cz - 0.625), (seg, 0.75, 1.25), "halo",
               pivot=(cx, cy, cz), rot=(0, 0, ang))
    for s in (-1, 1):
        m.box(h.name, (cx + s * (HALO_R + 0.75), cy, cz), (1.25, 1.5, 0.5), "halo")   # handles
    h.locators["halo_c"] = (cx, cy, cz)


def _arms(m: Model) -> None:
    """Noodle braids that become arms only while that hand holds something (scaled in by the animation)."""
    for s, g, p in ((-1, "r_arm_g", "r"), (1, "l_arm_g", "l")):
        br = m.bone(f"{p}_braid", g, (s * 5.0, 21.0, 0.0))
        for k, dz in enumerate((-0.5, 0.5)):
            pts = [(s * 5.0, 21.0, dz), (s * (6.0 + 0.25 * k), 17.0, dz * 1.5), (s * 6.0, 13.0, dz), (s * 6.0, 10.5, -0.5)]
            strand(m, br.name, pts, 0.75, "noodle")
        m.box(br.name, (s * 6.0, 11.0, -0.75), (2.0, 1.5, 2.0), "noodle")                    # the "hand": a knot of noodles


def _lattice(m: Model) -> None:
    """Al Dente: straight dry rods lock into a crosshatched lattice around the body."""
    lat = m.bone("lattice", "mass", CENTER, only={"rigid"})
    for k in range(6):
        phi = math.radians(k * 60.0 + 15.0)
        d = np.array([math.sin(phi), 0.12, -math.cos(phi)])
        c = surf(d, 0.9)
        t = np.array([math.cos(phi), 0.0, math.sin(phi)])            # horizontal tangent
        for tilt in (-38.0, 38.0):
            v = t * math.cos(math.radians(tilt)) + np.array([0.0, 1.0, 0.0]) * math.sin(math.radians(tilt))
            segment(m, lat.name, c - v * 6.5, c + v * 6.5, 0.75, 0.75, "dry_noodle", only={"rigid"}, overlap=0.0)


def _spirals(m: Model) -> None:
    """The Great Pasta Revelation: three spiral layers of pasta unfold around the body."""
    for layer in range(3):
        sp = m.bone(f"spiral{layer}", "mass", CENTER, only={"revelation"})
        y = CENTER[1] - 2.0 + layer * 2.5
        pts = []
        for k in range(13):
            t = k / 12.0
            ang = math.radians(layer * 120 + t * 420)
            r = 9.5 + 6.5 * t
            pts.append((math.cos(ang) * r, y + math.sin(t * math.pi) * 1.5, CENTER[2] + math.sin(ang) * r))
        strand(m, sp.name, pts, 1.0, "noodle_holy", only={"revelation"})


# ============================================================================= materials

def materials():
    return {"noodle": mat_noodle, "noodle_core": mat_core, "noodle_holy": mat_noodle_holy, "dry_noodle": mat_dry,
            "braid": mat_noodle, "meatball": mat_meatball, "meatball_solo": mat_meatball_solo, "sauce": mat_sauce,
            "socket": mat_socket, "eyeball": mat_eyeball, "pupil": mat_pupil, "lid": mat_lid, "halo": mat_halo,
            "basil": mat_basil, "accent": mat_accent}


def _pasta(ctx):
    if ctx.params.get("burnt", 0) > 0.5:
        return BURNT
    if ctx.params.get("dente", 0) > 0.5:
        return DRY
    if ctx.params.get("holy", 0) > 0.5:
        return HOLY
    return PASTA


def _holy(ctx):
    return ctx.params.get("holy", 0.0)


def _wp(ctx):
    return ctx.wp if ctx.wp is not None else ctx.p


def pillow(ctx, amount: float = 0.1):
    """Level offset darkening a face toward its edges: small boxes read as domed, round."""
    a = np.abs(ctx.s / max(ctx.fw, 1e-6) - 0.5) * 2
    b = np.abs(ctx.t / max(ctx.fh, 1e-6) - 0.5) * 2
    return -amount * np.maximum(a, b) ** 2


def mat_noodle(ctx):
    """A noodle lit as it actually lies, with a glossy streak along its upper side."""
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx, grad=0.0) + 0.08
    pal = _pasta(ctx)
    c = px.quant(ctx, pal, lv)
    if ctx.wn is not None and ctx.wn[1] > 0.5 and ctx.params.get("burnt", 0) < 0.5:
        streak = ((ix + 2 * iy) % 6) < 3 if W >= H else ((iy + 2 * ix) % 6) < 3
        c = np.where(streak[:, None], pal[-1], c)
    return c, ctx.ones(), np.full(ctx.N, 0.25 * _holy(ctx))


def mat_noodle_holy(ctx):
    c, a, g = mat_noodle(ctx)
    return c, a, np.full(ctx.N, 0.55)


def strand_field(p):
    """The strands wound around the nest, as (phase, family): two families of waved helices
    around the vertical axis (integer turns, so every strand is continuous) - one wound
    shallow, one steep - and patches where the steep family lies on top: woven, tangled.
    p: positions relative to CENTER.  Returns (fractional phase, on_top_of_other, edge)."""
    u = p / np.array(SEMI)
    rr = np.maximum(np.linalg.norm(u, axis=1), 1e-6)
    phi = np.arccos(np.clip(u[:, 1] / rr, -1, 1))
    th = np.arctan2(u[:, 2], u[:, 0])
    k = 6.6 / STRAND_PITCH
    a = phi * k - 4 * th / (2 * np.pi) + 0.42 * np.sin(3 * th + 2.0 * phi) + 0.16 * np.sin(7 * th - phi)
    b = phi * k + 15 * th / (2 * np.pi) + 0.3 * np.sin(4 * th - 1.5 * phi + 1.0)
    mask = np.sin(2 * th + 2.5 * phi + 0.6) + 0.6 * np.sin(5 * th - 3.0 * phi + 1.3)
    top = mask > 1.05
    edge = (mask > 0.9) & ~top
    ph = np.where(top, b, a)
    return ph - np.floor(ph), top, edge


def mat_core(ctx):
    """The nest: strands wound around it (dark groove under each, a glossy crest on top), lit
    as one rounded mass."""
    p = _wp(ctx) - np.array(CENTER)
    f, top, edge = strand_field(p)
    lv = px.proxy(ctx, CENTER, SEMI, 1.0) + 0.07
    groove = (f > 0.7) | edge
    crest = (f < 0.28) & ~edge
    lv = lv + np.where(groove, -0.19, 0.0) + np.where(crest, 0.1, 0.0) + np.where(top & ~groove, 0.04, 0.0)
    c = px.quant(ctx, _pasta(ctx), lv)
    return c, ctx.ones(), np.full(ctx.N, 0.2 * _holy(ctx))


def mat_dry(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = px.shade(ctx, DRY, up=0.15, down=0.1)
    crack = px.hash01(ctx, 9) < 0.06
    c = np.where(crack[:, None], DRY[1], c)
    return c, ctx.ones(), ctx.zeros()


@lru_cache(maxsize=None)
def _cells():
    rng = np.random.default_rng(11)
    v = rng.normal(size=(24, 3))
    return v / np.linalg.norm(v, axis=1, keepdims=True)


LIGHT = np.array([-0.45, 0.78, -0.45]) / np.linalg.norm([-0.45, 0.78, -0.45])


def _meat(ctx, c, r):
    """Seared meatball: a sphere of lumps (crevices between them), glazed with marinara on
    top (running down in drips), glossy where it faces the light, a few herb flecks."""
    p = _wp(ctx) - np.asarray(c, float)
    dn = p / np.maximum(np.linalg.norm(p, axis=1, keepdims=True), 1e-6)
    sims = np.sort(dn @ _cells().T, axis=1)
    d1, d2 = 1 - sims[:, -1], 1 - sims[:, -2]
    crevice = (d2 - d1) < 0.045
    lump = np.clip(1.0 - d1 / 0.35, 0, 1)
    sphere = px.proxy(ctx, c, (r, r, r), 1.0) + pillow(ctx, 0.12)
    lv = sphere + 0.08 + 0.07 * lump - np.where(crevice, 0.2, 0.0)
    burnt = ctx.params.get("burnt", 0) > 0.5
    col = px.quant(ctx, MEAT_BURNT if burnt else MEAT, lv)
    gl = (dn @ LIGHT) > 0.9
    az = np.arctan2(dn[:, 2], dn[:, 0])
    glaze = dn[:, 1] > 0.66 + 0.16 * np.sin(5 * az + 1.0) + 0.08 * np.sin(9 * az)
    if not burnt:
        col = np.where((gl & ~crevice)[:, None], px.col("#ecb084"), col)
        herb = (px.hash01(ctx, 11) < 0.035) & ~crevice & ~gl
        col = np.where(herb[:, None], HERB, col)
        sc = px.quant(ctx, SAUCE, sphere + 0.1 - np.where(crevice, 0.1, 0.0))
        sc = np.where((gl | (px.hash01(ctx, 3) < 0.05))[:, None], GLOSS, sc)
        col = np.where(glaze[:, None], sc, col)
    return col, ctx.ones(), ctx.zeros()


def mat_meatball(ctx):
    s = 1 if _wp(ctx)[:, 0].mean() > 0 else -1
    return _meat(ctx, MEATBALLS[s], MB_D / 2)


def mat_meatball_solo(ctx):
    return _meat(ctx, (0.0, 4.0, 0.0), 1.9)


def mat_sauce(ctx):
    """Thick glossy marinara: shaded by its real normals, bright glints along upper edges,
    a few parmesan flakes on top."""
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx, grad=0.1) + 0.06
    c = px.quant(ctx, SAUCE, lv)
    if ctx.face == "up":
        gl = (px.hash01(ctx, 2) < 0.06)
        c = np.where(gl[:, None], GLOSS, c)
        if W >= 8:
            cheese = (px.hash01(ctx, 5) > 0.955)
            c = np.where(cheese[:, None], px.col("#fff2cf"), c)
    elif px.side(ctx) and H > 1:
        c = np.where(((iy == 0) & ((ix % 3) == 1))[:, None], GLOSS, c)
    if ctx.params.get("burnt", 0) > 0.5:
        c = c * 0.62
    return c, ctx.ones(), np.full(ctx.N, 0.1 * _holy(ctx))


def mat_socket(ctx):
    return px.shade(ctx, px.pal("#2a0806", "#4a0c08", "#6a140e", "#8a1c12")), ctx.ones(), ctx.zeros()


def mat_eyeball(ctx):
    """Glossy eyeball shaded as a sphere (the pupil is its own sliding piece)."""
    p = _wp(ctx)
    s = 1 if p[:, 0].mean() > 0 else -1
    ex, ey, ez = EYES[s]
    lv = px.proxy(ctx, (ex, ey, ez), (EYE_D / 2,) * 3, 1.0) + 0.16 + pillow(ctx, 0.1)
    c = px.quant(ctx, EYE, lv)
    if ctx.params.get("burnt", 0) > 0.5:
        c = c * np.array([0.92, 0.86, 0.8])
    return c, ctx.ones(), ctx.zeros()


PUPIL = ["....oooo....",
         "..ooOOOOoo..",
         ".oOOaaaaOOo.",
         ".oOaPPPPaOo.",
         "oOaPPWWPPaOo",
         "oOaPPWPPPaOo",
         "oOaPPPPPPaOo",
         "oOaPPPPPPaOo",
         ".oOaPPPwaOo.",
         ".oOOaaaaOOo.",
         "..ooOOOOoo..",
         "....oooo...."]


def mat_pupil(ctx):
    lv = px.light(ctx, grad=0.0) + 0.2
    c = px.quant(ctx, EYE, lv)
    if ctx.face == "north":
        c, _ = px.decal(ctx, c, PUPIL, {"o": "#3a2412", "O": "#b8742a", "a": "#e7a64a", "P": "#140d0a",
                                         "W": "#ffffff", "w": "#d8d2c8"}, "c", "c")
    return c, ctx.ones(), ctx.zeros()


def mat_lid(ctx):
    """The lid is eyeball-white (folded back it disappears into the eye); a dark lash line
    along its free edge shows when it closes."""
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx, grad=0.0) + 0.12
    c = px.quant(ctx, EYE, lv)
    if ctx.face == "north":
        c = np.where((iy >= H - 1)[:, None], px.col("#5a4430"), c)
    elif ctx.face == "down":
        c = np.full_like(c, px.col("#5a4430"))
    return c, ctx.ones(), ctx.zeros()


def mat_halo(ctx):
    """Gilded perforated band: a row of dark holes along its outer face, bright upper edge."""
    ix, iy, W, H = px.texel(ctx)
    c = px.shade(ctx, GOLD, up=0.2, down=0.12)
    if W >= 4 and H >= 2 and px.side(ctx):
        holes = ((ix % 2) == 1) & (iy == H // 2)
        c = np.where(holes[:, None], px.col("#4a300c"), c)
    return c, ctx.ones(), np.full(ctx.N, 0.45 + 0.3 * _holy(ctx))


def mat_basil(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = px.shade(ctx, px.pal("#1f3d14", "#2f5a1e", "#467a2c", "#6a9e42"))
    if ctx.face == "up":
        c = np.where(((iy == H // 2) & (ix > 0))[:, None], px.col("#8ab85a"), c)
    return c, ctx.ones(), ctx.zeros()


# ============================================================================= the detached meatball entity

def build_meatball() -> Model:
    """The detached meatball (Meatball Ricochet): its own small entity model."""
    m = Model("meatball", ppu=2.0, atlas_width=128)
    m.bone("root", None, (0, 0, 0))
    ball = m.bone("ball", "root", (0, 4.0, 0))
    ellipsoid(m, ball.name, (0, 4.0, 0), (4.0, 4.0, 4.0), "meatball_solo", a=0.625, b=0.75)
    # two noodle tethers trailing behind it (they lead back to the body)
    for k, (dx, dy) in enumerate(((-1.0, 0.5), (0.75, -0.5))):
        tb = m.bone(f"tether{k}", ball.name, (dx, 4.0 + dy, 1.5))
        strand(m, tb.name, [(dx, 4.0 + dy, 1.5), (dx * 1.5, 4.0 + dy * 2, 4.5), (dx, 4.0 + dy, 7.5)], 0.75, "noodle")
    ball.locators["trail"] = (0, 4.0, 2.0)
    m.pack()
    return m
