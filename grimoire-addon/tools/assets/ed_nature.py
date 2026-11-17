"""Nature Dragon -- "The Walking Continent" (ED01 Genesis Colossus; reused by ED05 / ED06).

Original Argentinosaurus-inspired titanosaur dragon: a tiny head on a very long neck, a deep
barrel torso on four columnar, elephantine legs (wide gauge, shoulders level with the hips), a
long whip tail, and a back that is a living landscape: layered strata ridges like a mountain
range, a miniature forest of four tree species, mossy boulders, standing stones and a little
waterfall pouring down the right flank.  No wings.

RIG (bb space: front = -Z, +X = the dragon's right, units 1/16 block, rendered at SCALE = 2.0,
so 8 model units = 1 block.  Nose to tail ~ 37 blocks, back ~ 9.5 blocks, head ~ 13 blocks at
rest and ~ 18-19 blocks when raised.)
  root            (0, 0, 0)            ground contact, whole-creature offsets (arrive / depart)
  body            (0, 50, 30)          torso core; pivots at the hip line (rearing / mass shift)
    chest         (0, 52, -10)         front half: shoulder hump, pectorals, waterfall, ridges 1-3
      neck1..neck9  start (0, 64, -46)   chain rising forward; joint pivots along a curve
        head      end of neck9 (~(0, 102, -128));  jaw (hinge ~6 units below/behind the eye)
      fleg_{r,l}_1 (+-24, 50, -30) -> fleg_{s}_2 (+-24, 25, -30) -> ffoot_{s} (+-24, 6, -30)
      falls       blend bone: waterfall on the right flank
    hips          (0, 52, 26)          back half, ridges 5-7
      tail1..tail10 start (0, 62, 44)    chain going back (+Z), sloping down, 100 units long
      hleg_{r,l}_1 (+-24, 52, 30) -> hleg_{s}_2 (+-24, 26, 30) -> hfoot_{s} (+-24, 6, 29)
    ridge1..ridge7  strata crest bones along the spine (power pushes them up)
    tree1..tree9    tree bones, pivot at the trunk base (grown by the forest latch, see below)
    antler{1..3}_{s} on neck3/5/7, antlerh_{s} on the head (branching root-antlers)
    moss_{s}        hanging moss skirts along the flanks
Locators: foot_fl, foot_fr, foot_hl, foot_hr (soles), mouth, back, tail_tip, falls_base.

Chains: positive rx RAISES a neck bone (it points forward) and LOWERS a tail bone; positive ry
swings the neck toward the dragon's left (-X) and the tail toward its right (+X); positive rx on
a leg swings the foot forward.

LOCOMOTION: `move` is a 4-beat lateral-sequence walk, cycle 3.2 s, authored for
WALK_SPEED = 1.5 blocks/s (feet planted during stance).  Footfalls inside the cycle:
LH 0.0 s, LF 0.8 s, RH 1.6 s, RF 2.4 s.  At strike a front foot is ~5.5 blocks ahead of the
origin and 3 blocks to the side; a hind foot ~1.9 blocks behind and 3 to the side.
`turn_l` / `turn_r` are in-place shuffles (cycle 2.4 s) for a yaw rate of TURN_RATE = 20 deg/s.

FOREST LATCH: the client keeps v.fg (0 = saplings, 1 = full canopy).  It eases toward 1 once the
`power` state (8) has played and back to 0 only in `hidden` (0); trees, antlers and moss skirts
scale with it in the `forest` always-animation.  Skins: 0 default, 1 "bloom" (flowers, glowing
sap veins), 2 "stone" (petrified - used by `depart`).

Timed animations (seconds): arrive 3.2 (body lands 2.5), power 2.6, attack_a 3.2 (forelimb slam
lands 2.2, right forefoot ~3 blocks right / 5 blocks ahead of the origin), attack_b 2.4 (neck lash
low sweep right->left, hit 1.35), react 1.4, depart 2.8 (sinking from 1.0).
"""
import math

import numpy as np

from kit import glyphs, synth as sy, tex
from kit.anim import LIFE, Anim, M, S
from kit.geo import Mat, Model
from kit.parts import sym, wave

from .a_fx_common import particles

ACTOR = "dragon_nature"
SCALE = 2.0
WALK_SPEED = 1.5          # blocks per second for the `move` loop
WALK_CYCLE = 3.2          # seconds
TURN_RATE = 20.0          # degrees per second for turn_l / turn_r
STEP_TIMES = {"hl": 0.0, "fl": 0.8, "hr": 1.6, "fr": 2.4}
LEN = {"arrive": 3.2, "power": 2.6, "attack_a": 3.2, "attack_b": 2.4, "react": 1.4, "depart": 2.8}
HIT = {"attack_a": 2.2, "attack_b": 1.35, "arrive_land": 2.5}

STATES = {0: ["hidden"], 1: ["arrive"], 2: ["idle"], 3: ["move"], 4: ["turn_l"], 5: ["turn_r"], 6: ["attack_a"],
          7: ["attack_b"], 8: ["power"], 9: ["react"], 10: ["rest"], 11: ["depart"]}
STATE_IDS = {v[0]: k for k, v in STATES.items()}
# blend time when LEAVING each state (seconds)
_BLEND = {0: 0.0, 1: 0.4, 2: 0.6, 3: 0.5, 4: 0.5, 5: 0.5, 6: 0.5, 7: 0.4, 8: 0.5, 9: 0.4, 10: 1.0, 11: 0.2}

NECK = [f"neck{i + 1}" for i in range(9)]
TAIL = [f"tail{i + 1}" for i in range(10)]
TREES = [f"tree{i + 1}" for i in range(9)]
RIDGES = [f"ridge{i + 1}" for i in range(7)]

# ---------------------------------------------------------------- palette
BASALT, SLATE, SAND, OCHRE, LIME, BRONZE, IVORY = "#3b3a3c", "#6a6460", "#b89a68", "#8f6a42", "#cbbf9e", "#8a6a3a", "#e9dfc6"
MOSS0, MOSS1, SAP = "#3e5a26", "#7a9a44", "#9cff7a"
FLOWERS = [tex.rgb(c) for c in ("#f6c8e0", "#fff4c8", "#f2e06a", "#ffffff", "#e7a6d8")]


# ================================================================ materials
def _fc(ctx):
    if ctx.face in ("north", "south"):
        return ctx.X, ctx.Y
    if ctx.face in ("east", "west"):
        return ctx.Z, ctx.Y
    return ctx.X, ctx.Z


def _vor(a, b, cell, seed):
    """Voronoi distances (nearest, second) and a per-cell random value."""
    ga, gb = np.floor(a / cell), np.floor(b / cell)
    d1 = np.full(a.shape, 9e9)
    d2 = np.full(a.shape, 9e9)
    cid = np.zeros(a.shape)
    for oa in (-1, 0, 1):
        for ob in (-1, 0, 1):
            ca, cb = ga + oa, gb + ob
            pa = (ca + 0.15 + 0.7 * tex._hash(ca, cb, seed)) * cell
            pb = (cb + 0.15 + 0.7 * tex._hash(ca, cb, seed + 7)) * cell
            d = np.hypot(a - pa, b - pb)
            closer = d < d1
            d2 = np.where(closer, d1, np.minimum(d2, d))
            cid = np.where(closer, tex._hash(ca, cb, seed + 13), cid)
            d1 = np.where(closer, d, d1)
    return d1, d2, cid


def _stone_of(ctx, t):
    """Petrify a tile: grey weathered stone with hairline cracks, no glow."""
    t = np.array(t, dtype=float)
    lum = t[..., 0] * 0.3 + t[..., 1] * 0.59 + t[..., 2] * 0.11
    k0, k1 = tex.rgb("#5f5d58"), tex.rgb("#b3aea3")
    t[..., :3] = tex.mix(k0, k1, np.clip(lum * 1.5, 0, 1)[..., None])
    ix, iy = tex.px(ctx)
    c = np.abs(tex.vnoise(ix / 3.0 + ctx.variant * 5, iy / 3.0, 91) - tex.vnoise(ix / 3.0 + 30, iy / 3.0, 92))
    t[..., :3] = np.where((c < 0.03)[..., None], t[..., :3] * 0.55, t[..., :3])
    t[..., 4] = 0.0
    return tex.grain(ctx, t, 0.05)


def petrify(mat):
    return Mat(lambda ctx: _stone_of(ctx, mat.fn(ctx)), mat.key + "|pet", mode=mat.mode, spatial=mat.spatial,
               directional=mat.directional, density=mat.density)


def nat(mat, bloom=None):
    """Three-skin wrapper for kit materials: default / bloom / petrified stone."""
    return tex.alt(mat, bloom=bloom or mat, stone=petrify(mat))


def hide(lo=26.0, hi=82.0, cell=5.0, moss=0.55, belly="#8f846e", flank="#5a4a38", top="#5c6a40", key="hide"):
    """Bark-stone scutes grading from a pale stony belly through bark-brown flanks to a mossy back."""
    kb, kf, kt = tex.rgb(belly), tex.rgb(flank), tex.rgb(top)
    m0, m1, sap = tex.rgb(MOSS0), tex.rgb(MOSS1), tex.rgb(SAP)

    def fn(ctx):
        a, b = _fc(ctx)
        f = np.clip((ctx.Y - lo) / (hi - lo), 0, 1)
        if ctx.face == "down":
            f = f * 0.0
        if ctx.face == "up":
            f = np.maximum(f, 0.8)
        lowc = tex.mix(kb, kf, np.clip(f / 0.35, 0, 1)[..., None])
        highc = tex.mix(kf, kt, np.clip((f - 0.35) / 0.65, 0, 1)[..., None] ** 1.4)
        col = np.where((f < 0.35)[..., None], lowc, highc)
        d1, d2, cid = _vor(a, b, cell, 3)
        border = (d2 - d1) < 0.6
        col = col * (0.84 + 0.26 * cid)[..., None]
        st = tex.vnoise(a * 0.8, b * 0.12, 5)
        col = np.where((st < 0.2)[..., None], col * 0.8, col)
        col = np.where(border[..., None], col * 0.58, col)
        mn = tex.fbm(a / 7.0, b / 7.0, 9)
        mm = (mn > 0.92 - moss * f * f) & (f > 0.55)
        mcol = tex.mix(m0, m1, tex.fbm(a / 2.0, b / 2.0, 4)[..., None])
        col = np.where(mm[..., None], mcol, col)
        t = np.zeros((ctx.h, ctx.w, 5))
        t[..., :3] = col
        t[..., 3] = 1.0
        if ctx.alt == "bloom":
            h = tex._hash(np.floor(a), np.floor(b), 77)
            fl = mm & (h > 0.965)
            pick = (tex._hash(np.floor(a), np.floor(b), 78) * len(FLOWERS)).astype(int) % len(FLOWERS)
            t[..., :3] = np.where(fl[..., None], np.array(FLOWERS)[pick], t[..., :3])
            vein = border & (f > 0.6) & (cid > 0.88)
            t[..., :3] = np.where(vein[..., None], sap, t[..., :3])
            t[..., 4] = np.where(fl, 0.5, np.where(vein, 0.75, 0.0))
        elif ctx.alt == "stone":
            return _stone_of(ctx, t)
        return tex.grain(ctx, t, 0.05)
    return Mat(fn, f"{key}{lo}{hi}{cell}{moss}{belly}{flank}{top}", spatial=True)


STRATA_BANDS = [BASALT, SLATE, SAND, OCHRE, LIME, "#5a5852", "#a07a4a", "#7b6f5e"]


def strata(seed=0, moss_top=True, vein=0.0, band=3.4, key="strata"):
    """Layered sedimentary rock: warped horizontal bands, cracks, mossy upper faces.
    vein > 0: glowing green magic veins along some band boundaries (always lit)."""
    pal = np.array([tex.rgb(c) for c in STRATA_BANDS])
    m0, m1, sap = tex.rgb(MOSS0), tex.rgb(MOSS1), tex.rgb(SAP)

    def fn(ctx):
        a, b = _fc(ctx)
        warp = tex.fbm(a / 9.0 + seed, b / 9.0, 31) * 4.0
        y = ctx.Y + warp + seed * 7.3
        idx = np.floor(y / band).astype(int)
        frac = y / band - np.floor(y / band)
        col = pal[(idx * 3 + seed) % len(pal)]
        n = tex.fbm(a / 3.0, b / 3.0 + seed, 33)
        col = col * (0.82 + 0.3 * n)[..., None]
        col = np.where((frac < 0.12)[..., None], col * 0.7, col)
        cr = np.abs(tex.vnoise(a / 4.0 + seed, b / 2.0, 35) - tex.vnoise(a / 4.0 + 17, b / 2.0, 36)) < 0.03
        col = np.where(cr[..., None], col * 0.5, col)
        t = np.zeros((ctx.h, ctx.w, 5))
        t[..., :3] = col
        t[..., 3] = 1.0
        if moss_top and ctx.face == "up":
            mm = tex.fbm(a / 3.0, b / 3.0, 37) > 0.35
            t[..., :3] = np.where(mm[..., None], tex.mix(m0, m1, n[..., None]), t[..., :3])
        vv = vein
        if ctx.alt == "bloom":
            vv = max(vein, 0.7)
        if vv > 0 and ctx.face != "up":
            v = (frac < 0.09) & ((idx % 4) == (seed % 4)) & (tex.vnoise(a / 3.0, idx * 1.0, 39) > 0.55)
            t[..., :3] = np.where(v[..., None], sap, t[..., :3])
            t[..., 4] = np.where(v, vv, 0.0)
        if ctx.alt == "stone":
            return _stone_of(ctx, t)
        return tex.grain(ctx, t, 0.04)
    return Mat(fn, f"{key}{seed}{moss_top}{vein}{band}", spatial=True)


def moss_hang(c0=MOSS0, c1=MOSS1, key="mosshang"):
    """Cut-out hanging moss strands (rows grow downward from the tile top)."""
    k0, k1 = tex.rgb(c0), tex.rgb(c1)

    def fn(ctx):
        ix, iy = tex.px(ctx)
        ln = (0.35 + 0.65 * tex._hash(ix, ix * 0 + 3, 31 + ctx.variant)) * ctx.h
        t = tex.tile(ctx, c0)
        t[..., :3] = tex.mix(k1, k0, (iy / max(1, ctx.h - 1))[..., None])
        hole = tex._hash(ix, iy, 33 + ctx.variant) < 0.18
        t[..., 3] = np.where((iy < ln) & ~hole, 1.0, 0.0)
        if ctx.alt == "bloom":
            fl = (tex._hash(ix, iy, 34) > 0.94) & (iy < ln)
            t[..., :3] = np.where(fl[..., None], tex.rgb("#f6c8e0"), t[..., :3])
            t[..., 4] = np.where(fl, 0.5, 0.0)
        elif ctx.alt == "stone":
            return _stone_of(ctx, t)
        return tex.grain(ctx, t, 0.06)
    return Mat(fn, f"{key}{c0}{c1}")


def crack_disc(key="ednqcrack"):
    """Top-down radial ground fracture: dark soil lips around glowing green fissures."""
    def fn(ctx):
        u, v = ctx.U * 2 - 1, ctx.V * 2 - 1
        r = np.hypot(u, v)
        a = np.arctan2(v, u)
        on = np.zeros(r.shape, dtype=bool)
        rng = np.random.default_rng(7)
        for k in range(9):
            a0 = k * 2 * math.pi / 9 + rng.uniform(-0.2, 0.2)
            wig = a0 + 0.12 * np.sin(r * 9 + k)
            d = np.abs(np.angle(np.exp(1j * (a - wig)))) * r
            on |= (d < 0.035 + 0.02 * (1 - r)) & (r < 0.55 + 0.4 * rng.random())
        on |= (np.abs(r - 0.42 - 0.04 * np.sin(a * 5)) < 0.022) & (np.sin(a * 7) > -0.3)
        core = r < 0.12
        t = tex.tile(ctx, "#3a2e22")
        t[..., :3] = tex.mix(tex.rgb(SAP), tex.rgb("#e8ffd0"), np.clip(1 - r * 3, 0, 1)[..., None])
        lip = ~on & ~core
        t[..., :3] = np.where(lip[..., None], tex.rgb("#3a2e22"), t[..., :3])
        rim = np.zeros(r.shape, dtype=bool)
        pad = np.pad(on | core, 1)
        nb = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
        rim = nb & lip & (r < 0.95)
        t[..., 3] = np.where(on | core | rim, 1.0, 0.0)
        t[..., 4] = np.where(on | core, 0.95, 0.0)
        return t
    return Mat(fn, key, directional=True)


# ================================================================ geometry helpers
def _stick(bone, p0, p1, w, mat, d=None, **kw):
    """Box spanning p0 -> p1 (its long axis), square cross-section w (or (w, d))."""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    v = p1 - p0
    L = float(np.linalg.norm(v))
    u = v / L
    rx = math.degrees(math.asin(max(-1.0, min(1.0, u[2]))))
    rz = math.degrees(math.atan2(-u[0], u[1]))
    mid = tuple((p0 + p1) / 2)
    return bone.box(mid, (w, L, d if d is not None else w), mat, rot=(rx, 0, rz), pivot=mid, **kw)


def _chain(start, angles, lengths, back=False):
    pts = [np.array(start, float)]
    for a, L in zip(angles, lengths):
        r = math.radians(a)
        pts.append(pts[-1] + np.array([0.0, math.sin(r), (1 if back else -1) * math.cos(r)]) * L)
    return pts


def _tree(m, name, parent, kind, base, h, mats):
    """Tree bone with its pivot at the trunk base (scale grows it from the ground)."""
    x, y, z = base
    b = m.bone(name, parent, pivot=(x, y, z))
    wood, birch, fol_dark, fol_light, fol_old, fol_birch = mats
    if kind == "conifer":
        b.box((x, y + h * 0.3, z), (2.4, h * 0.62, 2.4), wood)
        for i, (fy, fw) in enumerate(((0.32, 0.6), (0.55, 0.46), (0.76, 0.32))):
            b.box((x, y + h * fy + h * 0.1, z), (h * fw, h * 0.26, h * fw), fol_dark, variant=i)
        b.box((x, y + h * 0.96, z), (h * 0.12, h * 0.14, h * 0.12), fol_dark, variant=2)
    elif kind == "broad":
        b.box((x, y + h * 0.27, z), (2.8, h * 0.56, 2.8), wood, variant=1)
        _stick(b, (x, y + h * 0.42, z), (x + h * 0.22, y + h * 0.62, z - 1), 1.6, wood)
        b.box((x, y + h * 0.72, z), (h * 0.74, h * 0.4, h * 0.7), fol_light)
        b.box((x + h * 0.24, y + h * 0.62, z + 1), (h * 0.42, h * 0.3, h * 0.44), fol_light, variant=1)
        b.box((x - h * 0.2, y + h * 0.86, z - 1), (h * 0.36, h * 0.24, h * 0.4), fol_light, variant=2)
    elif kind == "ancient":   # ancient branching tree: twisted bole, spreading limbs, blossom clouds
        b.box((x, y + h * 0.22, z), (4.2, h * 0.46, 4.2), wood, variant=2)
        b.box((x, y + 1.2, z), (6.5, 2.4, 6.5), wood, variant=1)              # root flare
        tips = []
        for k, (dx, dz, hy) in enumerate(((0.42, 0.1, 0.62), (-0.38, 0.22, 0.7), (0.05, -0.4, 0.78), (-0.1, 0.36, 0.9))):
            p0 = (x, y + h * 0.42, z)
            p1 = (x + h * dx, y + h * hy, z + h * dz)
            _stick(b, p0, p1, 2.0 - 0.2 * k, wood)
            tips.append(p1)
        for k, p in enumerate(tips):
            b.box(p, (h * 0.36, h * 0.2, h * 0.34), fol_old, variant=k % 3)
    else:   # birch
        b.box((x, y + h * 0.35, z), (2.0, h * 0.7, 2.0), birch)
        b.box((x, y + h * 0.78, z), (h * 0.46, h * 0.44, h * 0.46), fol_birch)
        b.box((x + 1, y + h * 0.56, z + 1), (h * 0.3, h * 0.24, h * 0.3), fol_birch, variant=1)
    return b


# ================================================================ the dragon
NECK_START = (0.0, 64.0, -46.0)
NECK_ANG = [40, 37, 33, 29, 25, 21, 17, 13, 9]
NECK_LEN = [11, 11, 10.5, 10.5, 10, 10, 10, 9.5, 9.5]
TAIL_START = (0.0, 62.0, 44.0)
TAIL_ANG = [-18, -15, -12, -10, -8, -6, -5, -4, -3, -2]
TAIL_LEN = [12, 12, 11, 11, 10, 10, 9, 9, 8, 8]


def build_model():
    """Return (model, info).  No side effects."""
    m = Model(ACTOR, density=1.0, bounds=(44, 30, (0, 6, 0)), alts=("bloom", "stone"))
    skin = hide()
    skin_leg = hide(lo=0, hi=90, cell=4.5, moss=0.45, key="hideleg")
    skin_neck = hide(lo=40, hi=118, cell=3.6, moss=0.6, key="hideneck")
    skin_tail = hide(lo=30, hi=80, cell=4.0, moss=0.5, key="hidetail")
    sole = nat(tex.stone("#4d443a", "#2f2a24", "#6a5f50", scale=3, cracks=0.3))
    claw = nat(tex.bone_mat(IVORY, "#a8946a", pores=0.15))
    wood = nat(tex.wood("#5b4128", "#3a2816"))
    birch = nat(tex.overlay(tex.wood("#d8d2c0", "#a9a291", vertical=False), _birch_marks, "birchm"))
    fol_dark = nat(tex.foliage("#24472a", "#3f7a35", holes=0.3), tex.foliage("#24472a", "#3f7a35", holes=0.3, flowers="#f2f0ff"))
    fol_light = nat(tex.foliage("#3f7a2f", "#86b84f", holes=0.26), tex.foliage("#3f7a2f", "#86b84f", holes=0.26, flowers="#f6c8e0"))
    fol_old = nat(tex.foliage("#4f7a3a", "#9cc46a", holes=0.3),
                  tex.foliage("#c9a0c0", "#fff0f6", holes=0.2, glow=0.35, flowers="#ffffff"))
    fol_birch = nat(tex.foliage("#7a9a2e", "#d8d070", holes=0.3), tex.foliage("#7a9a2e", "#d8d070", holes=0.25, flowers="#fff4c8"))
    tmats = (wood, birch, fol_dark, fol_light, fol_old, fol_birch)
    mhang = moss_hang()
    boulder = nat(tex.mottled("#6a6a5e", "#4f6a31", scale=2.5, thresh=0.55))
    standing = nat(tex.stone("#8d877c", "#5d574e", "#b0a898", scale=3, cracks=0.35))
    eye = tex.alt(tex.eye_mat("#c8f070", "#2b2a1a", "#10130c", "#4a3b2c", glow=0.95, ring="#f6ffb0"),
                  stone=tex.flat("#6e6b64", key="ednstoneeye"))
    teeth = nat(tex.bone_mat("#efe6cf", "#c2b48e", pores=0.05))
    water = tex.alt(tex.fluid("#3f86b0", "#c4ecff", a=0.62, flow=3.0, glow=0.2),
                    stone=tex.flat("#8a8780", a=0.0, mode="blend", key="ednstonewater"))
    info = {"neck": NECK, "tail": TAIL, "trees": TREES, "ridges": RIDGES, "antlers": []}

    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 50, 30))
    chest = m.bone("chest", body, pivot=(0, 52, -10))
    hips = m.bone("hips", body, pivot=(0, 52, 26))
    # ---- torso: a deep barrel, wide gauge
    body.box((0, 51, -1), (46, 38, 72), skin)
    body.box((0, 31, -4), (34, 6, 54), skin, variant=1)
    for sx in (1, -1):
        body.box((sx * 22.5, 49, -2), (8, 28, 54), skin, variant=2)
    chest.box((0, 51, -34), (44, 38, 26), skin)
    chest.box((0, 70, -26), (36, 10, 38), skin, variant=1)
    chest.box((0, 53, -49), (34, 30, 8), skin, variant=2)
    for sx in (1, -1):
        chest.box((sx * 21.5, 50, -31), (8, 28, 28), skin, variant=3)
    hips.box((0, 52, 30), (42, 34, 24), skin)
    hips.box((0, 68, 24), (34, 8, 30), skin, variant=1)
    hips.box((0, 54, 44), (30, 26, 8), skin, variant=2)
    # osteoderm plates on the upper flanks: foothills below the ridge
    for i, z in enumerate((-36, -22, -6, 10, 26, 38)):
        par = chest if z < -12 else (hips if z > 18 else body)
        for sx in (1, -1):
            yb = 66 if -40 < z < -10 else 64
            par.box((sx * 19.5, yb, z), (7, 6, 11), strata(seed=i + 10, band=2.6), rot=(0, 0, sx * -28),
                    pivot=(sx * 19.5, yb, z))
    # ---- strata ridge: a mountain range along the spine
    prof = [(-40, 75, 16), (-28, 75, 27), (-15, 74, 34), (-2, 70, 22), (11, 71, 30), (24, 72, 20), (36, 70, 12)]
    for k, (z, yb, h) in enumerate(prof):
        par = chest if k < 3 else (body if k == 3 else hips)
        rb = m.bone(RIDGES[k], par, pivot=(0, yb, z))
        sm = strata(seed=k, band=3.0)
        rb.box((0.5, yb + h / 2 - 3, z), (8, h, 12), sm, rot=(-8 + 4 * (k % 3), 0, 6 - 5 * (k % 2)), pivot=(0, yb, z))
        rb.box((-5, yb + h * 0.32 - 3, z + 3), (7, h * 0.64, 9), strata(seed=k + 20, band=2.4), rot=(10, 0, 18),
               pivot=(-4, yb, z + 3))
        rb.box((5.5, yb + h * 0.26 - 3, z - 3), (6, h * 0.5, 8), strata(seed=k + 30, band=2.2), rot=(-6, 0, -22),
               pivot=(4.5, yb, z - 3))
    # ---- the miniature forest
    forest = [("conifer", (-13, 74, -36), 24), ("broad", (12, 74, -33), 20), ("ancient", (-12, 70, -16), 27),
              ("conifer", (14, 70, -10), 18), ("birch", (-15, 70, 3), 17), ("broad", (12, 71, 14), 19),
              ("conifer", (-12, 71, 24), 21), ("ancient", (13, 71, 31), 18), ("birch", (-5, 69, 41), 12)]
    for i, (kind, base, h) in enumerate(forest):
        par = chest if base[2] < -12 else (hips if base[2] > 18 else body)
        _tree(m, TREES[i], par, kind, base, h * 1.45, tmats)
    # boulders, ferns and a tiny ring of standing stones on the rump
    for i, (x, y, z, s) in enumerate(((-7, 75, -28, 5), (8, 70, 2, 6), (-8, 72, 34, 4), (16, 74, -22, 3.5))):
        par = chest if z < -12 else (hips if z > 18 else body)
        par.box((x, y + s * 0.35, z), (s, s * 0.8, s * 1.1), boulder, variant=i % 3, rot=(0, 25 * i, 0))
    fern = nat(tex.foliage("#2f6a2a", "#6fae4b", holes=0.4, scale=1.2))
    for i, (x, y, z) in enumerate(((-17, 70, -6), (17, 71, 4), (-17, 72, 14), (8, 75, -42))):
        par = chest if z < -12 else (hips if z > 18 else body)
        par.plane("z", (x, y + 3, z), 8, 6, fern, rot=(0, 40, 0), pivot=(x, y, z), variant=i % 2)
        par.plane("z", (x, y + 3, z), 8, 6, fern, rot=(0, -50, 0), pivot=(x, y, z), variant=(i + 1) % 2)
    for k in range(4):
        a = math.radians(k * 90 + 20)
        x, z = 4 + 5 * math.cos(a), 18 + 5 * math.sin(a)
        hips.box((x, 72 + 3, z), (2.2, 7 + (k % 2) * 2, 1.6), standing, rot=(0, k * 90 + 20, 4 * (k % 2) - 2))
    hips.box((4, 72.6, 18), (5, 1.2, 2.4), standing, variant=1)
    # ---- moss skirts along the flanks (grow with the forest)
    for s, sx in (("r", 1), ("l", -1)):
        mb = m.bone(f"moss_{s}", body, pivot=(sx * 26.8, 50, 0))
        for k, z in enumerate(range(-44, 44, 9)):
            mb.plane("x", (sx * 26.7, 44, z + 4.5), 9.5, 12, mhang, variant=k % 3)
        info.setdefault("moss", []).append(mb.name)
    # ---- waterfall (blend bone) from a pool on the shoulder hump down the right flank
    falls = m.bone("falls", chest, pivot=(20, 72, -24))
    falls.box((15, 75.3, -24), (8, 0.6, 9), water)
    falls.plane("y", (22.6, 72.4, -24), 6, 5.4, water, variant=1)
    falls.plane("x", (26.1, 52, -24), 5, 40, water, variant=2)
    falls.plane("x", (26.4, 47, -24), 3, 50, water, variant=3)
    falls.locator("falls_base", (26.4, 30, -24))
    chest.locator("back", (0, 80, -20))

    # ---- neck: nine bones, rising forward
    pts = _chain(NECK_START, NECK_ANG, NECK_LEN)
    par = chest
    beard = moss_hang("#4f6a31", "#8aa850", key="beard")
    for i, nm in enumerate(NECK):
        p0, p1 = pts[i], pts[i + 1]
        nb = m.bone(nm, par, pivot=tuple(p0))
        f = i / 8
        w, h = 25 - 13 * f, 27 - 14 * f
        mid = tuple((p0 + p1) / 2)
        nb.box(mid, (w, h, NECK_LEN[i] + 4), skin_neck, rot=(NECK_ANG[i], 0, 0), pivot=mid, variant=i % 3)
        top = (mid[0], mid[1] + h / 2 * math.cos(math.radians(NECK_ANG[i])) + 1.0,
               mid[2] + h / 2 * math.sin(math.radians(NECK_ANG[i])))
        nb.box(top, (3.2 - 1.2 * f, 4.5 - 1.5 * f, NECK_LEN[i] * 0.7), strata(seed=40 + i, band=1.8),
               rot=(NECK_ANG[i] - 10, 0, 0), pivot=top)
        if i in (1, 3, 5):   # moss beards under the throat
            low = (mid[0], mid[1] - h / 2 * math.cos(math.radians(NECK_ANG[i])), mid[2] - 2)
            nb.plane("z", (low[0], low[1] - 4, low[2]), w * 0.6, 8, beard, variant=i % 3)
        if i in (2, 4, 6):   # branching root-antlers along the neck
            for s, sx in (("r", 1), ("l", -1)):
                an = f"antler{i // 2}_{s}"
                bp = (sx * w * 0.38, mid[1] + h * 0.36, mid[2] + 1)
                ab = m.bone(an, nb, pivot=bp)
                L = 15 - i
                tip = (bp[0] + sx * L * 0.45, bp[1] + L * 0.8, bp[2] + L * 0.45)
                _stick(ab, bp, tip, 2.2, wood)
                mid2 = tuple(np.array(bp) * 0.45 + np.array(tip) * 0.55)
                _stick(ab, mid2, (mid2[0] + sx * L * 0.35, mid2[1] + L * 0.35, mid2[2] - L * 0.25), 1.4, wood)
                _stick(ab, tip, (tip[0] - sx * 2, tip[1] + 4, tip[2] + 3), 1.0, claw)
                ab.box(tip, (5, 3.5, 5), fol_light, variant=i % 3)
                info["antlers"].append(an)
        par = nb

    # ---- head: small titanosaur skull with raised nasal arch, glowing eyes, root-antlers
    j = pts[-1]
    jx, jy, jz = j
    head = m.bone("head", par, pivot=(jx, jy, jz))
    hd = hide(lo=jy - 8, hi=jy + 10, cell=2.6, moss=0.4, key="hidehead")
    hd.density = 2.0
    head.box((0, jy + 1, jz - 5), (12, 12, 12), hd)
    head.box((0, jy - 0.5, jz - 17), (9, 8, 14), hd, variant=1)
    head.box((0, jy + 5.5, jz - 11), (7, 5, 9), hd, variant=2)                   # raised nasal arch
    head.box((0, jy + 6.5, jz - 14.5), (5, 2.5, 3), hd, variant=3)
    for s, sx in (("r", 1), ("l", -1)):
        head.box((sx * 5, jy + 6, jz - 6), (3, 3, 8), strata(seed=60, band=1.2), rot=(0, sx * -8, sx * -10))
        head.plane("x", (sx * 6.06, jy + 3, jz - 7.5), 4, 3.2, eye, density=4.0)
        head.box((sx * 4.2, jy + 0.8, jz - 3), (1, 3, 4), sole)                   # cheek scute
        an = f"antlerh_{s}"
        bp = (sx * 4.5, jy + 6.5, jz - 1)
        ab = m.bone(an, head, pivot=bp)
        tip = (sx * 9, jy + 16, jz + 7)
        _stick(ab, bp, tip, 1.8, wood)
        _stick(ab, (sx * 6.6, jy + 11, jz + 2.6), (sx * 11, jy + 13, jz - 2), 1.2, wood)
        _stick(ab, tip, (sx * 8, jy + 20, jz + 9), 1.0, claw)
        ab.box((sx * 11, jy + 13.5, jz - 2.5), (3.5, 2.5, 3.5), fol_light, variant=1)
        info["antlers"].append(an)
    head.box((0, jy - 4.8, jz - 17), (8.2, 1.6, 11), teeth)                     # peg-tooth row
    head.locator("mouth", (0, jy - 3, jz - 25))
    jaw = m.bone("jaw", head, pivot=(0, jy - 4, jz - 3))
    jaw.box((0, jy - 6.2, jz - 13), (8.6, 3.4, 20), hd, variant=4)
    jaw.box((0, jy - 4.4, jz - 17), (7.6, 1.2, 10), teeth, variant=1)
    jaw.plane("z", (0, jy - 10, jz - 8), 6, 6, beard, variant=1)

    # ---- tail: ten bones, sloping down then held out as a whip
    tp = _chain(TAIL_START, TAIL_ANG, TAIL_LEN, back=True)
    par = hips
    for i, nm in enumerate(TAIL):
        p0, p1 = tp[i], tp[i + 1]
        tb = m.bone(nm, par, pivot=tuple(p0))
        f = i / 9
        w, h = 24 - 20.5 * f ** 0.85, 24 - 20.5 * f ** 0.85
        mid = tuple((p0 + p1) / 2)
        tb.box(mid, (w, h, TAIL_LEN[i] + 3), skin_tail, rot=(-TAIL_ANG[i], 0, 0), pivot=mid, variant=i % 3)
        if i < 6:
            top = (0, mid[1] + h / 2 + 1.2, mid[2])
            tb.box(top, (3.2 - 0.4 * i, 5 - 0.6 * i, TAIL_LEN[i] * 0.65), strata(seed=50 + i, band=1.8),
                   rot=(-TAIL_ANG[i] + 12, 0, 0), pivot=top)
        par = tb
    m.bones[TAIL[-1]].locator("tail_tip", tuple(tp[-1]))
    m.bones[TAIL[-1]].box(tuple(tp[-1] + np.array([0, 0, 1.5])), (1.6, 1.6, 5), claw)

    # ---- legs: columnar pillars on elephantine feet
    legs = {}
    for s, sx in (("r", 1), ("l", -1)):
        x = sx * 24
        u = m.bone(f"fleg_{s}_1", chest, pivot=(x, 50, -30))
        u.box((x, 37.5, -30), (15, 27, 15), skin_leg)
        u.box((x, 48, -30), (17, 8, 17), skin, variant=4)
        u.box((x + sx * 1, 31, -37.6), (9, 9, 2), strata(seed=70, band=1.6))          # elbow plate
        lo = m.bone(f"fleg_{s}_2", u, pivot=(x, 25, -30))
        lo.box((x, 15, -30), (13, 22, 13), skin_leg, variant=1)
        ft = m.bone(f"ffoot_{s}", lo, pivot=(x, 6, -30))
        ft.box((x, 3.5, -31), (17, 7, 17), sole)
        ft.box((x, 8.2, -30), (15, 3, 15), skin_leg, variant=2)
        for dx in (-5.4, -1.8, 1.8, 5.4):
            ft.box((x + dx, 1.5, -40), (2.8, 3.0, 2.8), claw, variant=int(dx > 0))
        ft.locator(f"foot_f{s}", (x, 0.5, -31))
        legs[f"f{s}"] = (u.name, lo.name, ft.name)
        u = m.bone(f"hleg_{s}_1", hips, pivot=(x, 52, 30))
        u.box((x, 39, 30), (18, 28, 19), skin_leg, variant=3)
        u.box((x, 50, 30), (20, 8, 21), skin, variant=5)
        lo = m.bone(f"hleg_{s}_2", u, pivot=(x, 26, 30))
        lo.box((x, 15.5, 29), (14, 22, 14), skin_leg, variant=4)
        ft = m.bone(f"hfoot_{s}", lo, pivot=(x, 6, 29))
        ft.box((x, 3.5, 28), (18, 7, 19), sole, variant=1)
        ft.box((x, 8.2, 29), (16, 3, 16), skin_leg, variant=5)
        for dx in (-5, 0, 5):
            ft.box((x + dx, 1.5, 18), (3.0, 3.0, 3.0), claw, variant=2)
        ft.locator(f"foot_h{s}", (x, 0.5, 28))
        legs[f"h{s}"] = (u.name, lo.name, ft.name)
    info["legs"] = legs
    return m, info


def _birch_marks(ctx, t):
    ix, iy = tex.px(ctx)
    mk = (tex._hash(ix // 2, iy, 81) > 0.82) & (iy % 3 == 0)
    t[..., :3] = np.where(mk[..., None], tex.rgb("#2c2a26"), t[..., :3])
    return t


# ================================================================ animation helpers
NECK_W = [1.35, 1.25, 1.15, 1.05, 1.0, 0.9, 0.82, 0.76, 0.72]
TAIL_W = [1.3, 1.2, 1.1, 1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7]


def _dist(a, bones, weights, keys, smooth=True):
    """Distribute total rotation keyframes {t: (rx, ry, rz)} over a chain by weights."""
    tot = sum(weights)
    for b, w in zip(bones, weights):
        f = w / tot
        if isinstance(keys, dict):
            a.rot(b, {t: tuple(c * f for c in v) for t, v in keys.items()}, smooth)
        else:
            a.rot(b, tuple(c * f for c in keys), smooth)


def neck(a, keys, smooth=True):
    _dist(a, NECK, NECK_W, keys, smooth)


def tail(a, keys, smooth=True):
    _dist(a, TAIL, TAIL_W, keys, smooth)


def _leg_keys(T, phase, amp, knee, stance=0.75, n=32, lift=0.45, compress=3.0):
    up, lo, ft = {}, {}, {}
    for i in range(n + 1):
        t = round(T * i / n, 4)
        p = (t / T - phase) % 1.0
        if p < stance:
            s = p / stance
            u = amp * (1 - 2 * s)
            l = -compress * math.sin(math.pi * min(1.0, s / 0.2)) if s < 0.2 else 0.0
        else:
            s = (p - stance) / (1 - stance)
            e = s * s * (3 - 2 * s)
            u = -amp + 2 * amp * e + knee * lift * math.sin(math.pi * s)
            l = -knee * math.sin(math.pi * s)
        up[t] = (u, 0, 0)
        lo[t] = (l, 0, 0)
        ft[t] = (-(u + l) * 0.85, 0, 0)
    return up, lo, ft


def _gait(a, info, T, amp_f, amp_h, knee_f, knee_h, phases=None, **kw):
    phases = phases or {k: v / WALK_CYCLE for k, v in STEP_TIMES.items()}
    for leg, (b1, b2, b3) in info["legs"].items():
        front = leg[0] == "f"
        up, lo, ft = _leg_keys(T, phases[leg], amp_f if front else amp_h, knee_f if front else knee_h, **kw)
        a.rot(b1, up, smooth=False)
        a.rot(b2, lo, smooth=False)
        a.rot(b3, ft, smooth=False)


def _forest_expr(k, lo=0.3, rate=1.6, lag=0.07):
    return M(f"{lo} + {1 - lo} * math.clamp(v.fg * {rate} - {k * lag:.3f}, 0, 1)", lambda t, lo=lo: lo)


# ================================================================ animations
def build_anims(info):
    """All dragon animations (list of Anim).  No side effects."""
    A = []
    T = WALK_CYCLE

    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    # ---- always: breathing + small life
    breathe = Anim("breathe", loop=True)
    breathe.scl("chest", (LIFE(0.018, 4.6, 0, 1.0), LIFE(0.024, 4.6, 0, 1.0), 1.0))
    breathe.scl("body", (LIFE(0.012, 4.6, 0.08, 1.0), LIFE(0.016, 4.6, 0.08, 1.0), 1.0))
    breathe.rot(NECK[0], (LIFE(0.7, 4.6, 0.12), 0, 0))
    breathe.rot("head", (LIFE(-0.9, 4.6, 0.2), 0, 0))
    breathe.rot("jaw", (LIFE(-0.8, 4.6, 0.3, -0.6), 0, 0))
    A.append(breathe)
    life = Anim("life", loop=True)
    for k, tr in enumerate(TREES):
        life.rot(tr, (LIFE(0.9, 3.3 + 0.3 * (k % 3), k * 0.13), 0, LIFE(1.4, 2.9 + 0.2 * (k % 4), k * 0.21)))
    for k, an in enumerate(info["antlers"]):
        life.rot(an, (0, 0, LIFE(1.6, 2.5, k * 0.17)))
    for k, mb in enumerate(info.get("moss", [])):
        life.rot(mb, (0, 0, LIFE(1.5, 3.7, k * 0.5)))
    for i, tb in enumerate(TAIL[5:]):
        life.rot(tb, (0, LIFE(1.2 + 0.4 * i, 6.1, -0.08 * i), 0))
    life.scl("falls", (1.0, LIFE(0.02, 0.37, 0, 1.0), 1.0))
    A.append(life)
    forest = Anim("forest", loop=True)            # driven by the client-side forest latch v.fg
    for k, tr in enumerate(TREES):
        forest.scl(tr, _forest_expr(k))
    for k, an in enumerate(info["antlers"]):
        forest.scl(an, _forest_expr(k, lo=0.4, rate=1.3, lag=0.05))
    for mb in info.get("moss", []):
        forest.scl(mb, (1.0, _forest_expr(0, lo=0.45, rate=1.2, lag=0), 1.0))
    A.append(forest)

    # ---- idle: weight shifts, slow look-around, tail sway (8 s loop)
    idle = Anim("idle", loop=True, length=8.0)
    idle.rot("body", (S(0.4, 8.0, 0.1), S(0.8, 8.0, 0.3), S(1.0, 8.0)))
    idle.pos("body", (S(0.8, 8.0), S(0.3, 4.0, 0.2), 0))
    for i, b in enumerate(NECK):
        idle.rot(b, (S(0.9, 8.0, 0.05 * i, 0.2), S(1.6, 8.0, 0.25 + 0.04 * i), S(0.3, 4.0, 0.03 * i)))
    idle.rot("head", (S(4.0, 8.0 / 3, 0.1), S(7.0, 8.0, 0.4), S(3.0, 4.0, 0.3)))
    idle.rot("jaw", (S(-2.0, 2.0, 0, -2.0), 0, 0))          # slow chewing of browse
    wave(idle, TAIL, 1, 1.4, 8.0, lag=0.05, grow=1.06)
    for leg, (b1, b2, b3) in info["legs"].items():
        ph = {"fl": 0.0, "fr": 0.5, "hl": 0.25, "hr": 0.75}[leg]
        idle.rot(b1, (S(0.8, 8.0, ph), 0, 0))
        idle.rot(b3, (S(-0.8, 8.0, ph), 0, 0))
    A.append(idle)

    # ---- move: 4-beat heavy walk, cycle T, for WALK_SPEED blocks/s
    move = Anim("move", loop=True, length=T)
    _gait(move, info, T, amp_f=16.0, amp_h=15.5, knee_f=30.0, knee_h=26.0)
    move.pos("body", (0, S(-0.7, T / 4, 0.0, -0.6), 0))
    move.rot("body", (S(0.6, T / 2, 0.15), S(1.0, T, 0.35), S(1.8, T, 0.1)))
    move.rot("chest", (0, S(2.6, T, 0.0), S(1.2, T, 0.25)))
    move.rot("hips", (0, S(-2.6, T, 0.0), S(-1.2, T, 0.25)))
    for i, b in enumerate(NECK):
        move.rot(b, (S(0.5, T / 2, 0.08 * i + 0.2, -0.1), S(-1.1, T, 0.05 * i), 0))
    move.rot("head", (S(-1.8, T / 2, 0.55), S(2.5, T, 0.4), 0))
    for i, b in enumerate(TAIL):
        move.rot(b, (S(0.5, T / 2, 0.1 + 0.06 * i), S(1.6 * 1.08 ** i, T, -0.07 * i - 0.1), 0))
    for k, tr in enumerate(TREES):
        move.rot(tr, (S(1.2, T / 4, 0.15 + k * 0.02), 0, S(2.2, T / 2, k * 0.05)))
    for leg, t0 in STEP_TIMES.items():
        move.sound(t0 + 0.02, "step")
        move.particle(t0 + 0.02, "dust", locator=f"foot_{leg}")
    A.append(move)

    # ---- turning in place (shuffle), neck leads, tail swings out
    for name, sgn in (("turn_l", 1), ("turn_r", -1)):
        tn = Anim(name, loop=True, length=2.4)
        _gait(tn, info, 2.4, amp_f=7.0, amp_h=6.0, knee_f=22.0, knee_h=18.0,
              phases={"hl": 0.0, "fl": 0.25, "hr": 0.5, "fr": 0.75})
        tn.rot("body", (0, sgn * 3.0 + S(0.6, 1.2), S(1.2, 2.4, 0.1)))
        tn.rot("chest", (0, sgn * 3.5, 0))
        tn.rot("hips", (0, sgn * -2.0, 0))
        tn.pos("body", (0, S(-0.5, 0.6, 0, -0.4), 0))
        for i, b in enumerate(NECK):
            tn.rot(b, (S(0.4, 1.2, 0.07 * i), sgn * (2.8 + 0.4 * math.sin(i)) + S(0.4, 2.4, 0.05 * i), 0))
        tn.rot("head", (0, sgn * 9.0, sgn * -4.0))
        for i, b in enumerate(TAIL):
            tn.rot(b, (0, sgn * 1.8 * 1.05 ** i + S(0.6, 2.4, -0.06 * i), 0))
        for leg, t0 in (("hl", 0.0), ("fl", 0.6), ("hr", 1.2), ("fr", 1.8)):
            tn.sound(t0 + 0.02, "step")
        A.append(tn)

    # ---- arrive: rises out of the strata, neck first; lands at 2.5 s
    L = LEN["arrive"]
    arr = Anim("arrive", length=L, loop="hold")
    arr.pos("root", {0: (0, -152, 26), 0.6: (0, -122, 20), 1.3: (0, -70, 10), 2.0: (0, -22, 2), 2.35: (0, 4, 0),
                     2.5: (0, -2.5, 0), 2.75: (0, 1, 0), L: (0, 0, 0)})
    arr.rot("root", {0: (32, 0, -4), 1.3: (22, 0, 3), 2.0: (9, 0, -1), 2.35: (-2, 0, 0), 2.6: (1, 0, 0), L: (0, 0, 0)})
    neck(arr, {0: (54, 0, 0), 0.8: (50, -8, 0), 1.6: (36, 10, 0), 2.3: (12, 0, 0), 2.6: (-6, 0, 0), 2.9: (3, 0, 0),
               L: (0, 0, 0)})
    arr.rot("head", {0: (-24, 0, 0), 0.9: (-10, 0, 0), 1.7: (6, 0, 0), 2.0: (22, 0, 0), 2.6: (12, 0, 0), L: (0, 0, 0)})
    arr.rot("jaw", {0: (0, 0, 0), 1.75: (0, 0, 0), 2.0: (-24, 0, 0), 2.8: (-18, 0, 0), L: (0, 0, 0)})
    for s in ("r", "l"):
        arr.rot(f"fleg_{s}_1", {0: (-30, 0, 0), 1.2: (48, 0, 0), 2.0: (34, 0, 0), 2.4: (-4, 0, 0), 2.7: (2, 0, 0), L: (0, 0, 0)})
        arr.rot(f"fleg_{s}_2", {0: (-60, 0, 0), 1.2: (-30, 0, 0), 2.0: (-24, 0, 0), 2.4: (0, 0, 0), L: (0, 0, 0)})
        arr.rot(f"ffoot_{s}", {0: (40, 0, 0), 2.0: (-10, 0, 0), 2.4: (4, 0, 0), L: (0, 0, 0)})
        arr.rot(f"hleg_{s}_1", {0: (40, 0, 0), 1.4: (30, 0, 0), 2.0: (-18, 0, 0), 2.4: (-4, 0, 0), L: (0, 0, 0)})
        arr.rot(f"hleg_{s}_2", {0: (-50, 0, 0), 1.6: (-40, 0, 0), 2.1: (8, 0, 0), L: (0, 0, 0)})
        arr.rot(f"hfoot_{s}", {0: (10, 0, 0), 2.1: (10, 0, 0), 2.4: (2, 0, 0), L: (0, 0, 0)})
    tail(arr, {0: (-40, 10, 0), 1.4: (-20, -16, 0), 2.2: (6, 10, 0), 2.6: (10, -6, 0), L: (0, 0, 0)})
    for k, tr in enumerate(TREES):
        arr.rot(tr, {0: (0, 0, 0), 2.3: (0, 0, 0), 2.45: (-6 + k % 3 * 4, 0, 7 - k % 4 * 4), 2.8: (2, 0, -2),
                     L: (0, 0, 0)})
    arr.sound(1.75, "call")
    arr.particle(0.4, "rock", locator="mouth")
    arr.particle(1.2, "dust", locator="back")
    arr.particle(2.0, "leaf", locator="back")
    for leg in ("fl", "fr"):
        arr.particle(2.45, "dust", locator=f"foot_{leg}")
    arr.sound(2.45, "step")
    A.append(arr)

    # ---- power: ground-bracing, neck raised to the sky, bellow; ridges heave (forest grows via latch)
    L = LEN["power"]
    pw = Anim("power", length=L, loop="hold")
    pw.pos("body", {0: (0, 0, 0), 0.4: (0, -2.5, 0), 1.2: (0, -1, 0), L: (0, -1.2, 0)})
    pw.rot("body", {0: (0, 0, 0), 0.4: (-1.5, 0, 0), 1.3: (3.5, 0, 0), L: (3, 0, 0)})
    neck(pw, {0: (0, 0, 0), 0.45: (-6, 0, 0), 1.3: (50, 0, 0), 1.6: (52, 0, 0), 2.2: (47, 0, 0), L: (46, 0, 0)})
    pw.rot("head", {0: (0, 0, 0), 0.45: (-6, 0, 0), 1.3: (24, 0, 0), 2.0: (26, 0, 0), L: (6, 0, 0)})
    pw.rot("jaw", {0: (0, 0, 0), 1.0: (0, 0, 0), 1.3: (-28, 0, 0), 2.1: (-24, 0, 0), L: (-2, 0, 0)})
    for s in ("r", "l"):
        sym_s = 1 if s == "r" else -1
        pw.rot(f"fleg_{s}_1", {0: (0, 0, 0), 0.4: (-3, 0, sym_s * 6), L: (-3, 0, sym_s * 5)})
        pw.rot(f"ffoot_{s}", {0: (0, 0, 0), 0.4: (3, 0, sym_s * -6), L: (3, 0, sym_s * -5)})
        pw.rot(f"hleg_{s}_1", {0: (0, 0, 0), 0.4: (-4, 0, sym_s * 5), 1.3: (-6, 0, sym_s * 5), L: (-5, 0, sym_s * 4)})
        pw.rot(f"hfoot_{s}", {0: (0, 0, 0), 0.4: (4, 0, sym_s * -5), 1.3: (6, 0, sym_s * -5), L: (5, 0, sym_s * -4)})
    for k, rb in enumerate(RIDGES):
        t0 = 0.5 + 0.08 * k
        pw.pos(rb, {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.25: (0, 4.5, 0), t0 + 0.6: (0, 1.5, 0), L: (0, 1.5, 0)})
        pw.rot(rb, {0: (0, 0, 0), t0 + 0.25: ((-1) ** k * 4, 0, (-1) ** k * 3), L: (0, 0, 0)})
    for k, tr in enumerate(TREES):
        pw.rot(tr, {0: (0, 0, 0), 0.6: (0, 0, 0), 0.9 + k * 0.05: (5, 0, -6 + (k % 3) * 6), 1.6: (-2, 0, 2), L: (0, 0, 0)})
    tail(pw, {0: (0, 0, 0), 0.4: (6, 0, 0), 1.3: (-10, 0, 0), L: (-6, 0, 0)})
    pw.sound(0.95, "bellow")
    pw.particle(1.0, "leaf", locator="back")
    pw.particle(1.4, "pollen", locator="back")
    pw.particle(1.9, "pollen", locator="back")
    pw.particle(0.4, "dust", locator="foot_fl")
    pw.particle(0.4, "dust", locator="foot_fr")
    A.append(pw)

    # ---- attack_a: Continental Descent - rear back on the hips, raise the right forelimb, slam
    L, H = LEN["attack_a"], HIT["attack_a"]
    at = Anim("attack_a", length=L, loop="hold")
    rear = {0: 0, 0.5: -2.5, 1.2: 14, 1.7: 21, 1.9: 22, H: -5, H + 0.25: -2.5, L: 0}
    at.rot("body", {t: (v, 0, (2.5 if 0.6 < t < H else 0)) for t, v in rear.items()})
    at.pos("root", {0: (0, 0, 0), 0.5: (0, -1.5, 3), 1.7: (0, 0, 4), H: (0, -4, 0), H + 0.15: (0, -6, 0),
                    H + 0.45: (0, -1.5, 0), L: (0, 0, 0)})
    for s in ("r", "l"):
        at.rot(f"hleg_{s}_1", {t: (-v, 0, 0) for t, v in rear.items()})
        at.rot(f"hleg_{s}_2", {0: (0, 0, 0), 0.5: (-6, 0, 0), 1.7: (4, 0, 0), H: (0, 0, 0), L: (0, 0, 0)})
        at.rot(f"hfoot_{s}", {0: (0, 0, 0), 0.5: (6, 0, 0), 1.7: (-4, 0, 0), H: (0, 0, 0), L: (0, 0, 0)})
    at.rot("fleg_r_1", {0: (0, 0, 0), 0.5: (-6, 0, 0), 1.2: (40, 0, 4), 1.8: (62, 0, 6), 1.95: (64, 0, 6),
                        H: (6, 0, 0), H + 0.2: (4, 0, 0), L: (0, 0, 0)})
    at.rot("fleg_r_2", {0: (0, 0, 0), 1.2: (-40, 0, 0), 1.9: (-34, 0, 0), H - 0.05: (-4, 0, 0), H: (0, 0, 0), L: (0, 0, 0)})
    at.rot("ffoot_r", {0: (0, 0, 0), 1.2: (-10, 0, 0), 1.9: (-20, 0, 0), H: (-1, 0, 0), L: (0, 0, 0)})
    at.rot("fleg_l_1", {0: (0, 0, 0), 0.5: (-4, 0, 0), 1.2: (-4, 0, -3), 1.9: (6, 0, -4), H: (3, 0, 0), L: (0, 0, 0)})
    at.rot("fleg_l_2", {0: (0, 0, 0), 1.2: (-12, 0, 0), 1.9: (-18, 0, 0), H: (0, 0, 0), L: (0, 0, 0)})
    at.rot("ffoot_l", {0: (0, 0, 0), 1.9: (12, 0, 0), H: (0, 0, 0), L: (0, 0, 0)})
    neck(at, {0: (0, 0, 0), 0.5: (-8, 6, 0), 1.3: (18, -4, 0), 1.9: (22, -6, 0), H: (-20, 4, 0), H + 0.3: (-14, 2, 0),
              L: (0, 0, 0)})
    at.rot("head", {0: (0, 0, 0), 1.3: (18, 0, 0), 1.9: (24, 0, 0), H: (-14, 0, 0), L: (0, 0, 0)})
    at.rot("jaw", {0: (0, 0, 0), 1.25: (0, 0, 0), 1.5: (-26, 0, 0), 1.95: (-22, 0, 0), H: (-6, 0, 0), L: (0, 0, 0)})
    tail(at, {0: (0, 0, 0), 1.2: (-26, 8, 0), 1.9: (-34, 10, 0), H: (12, -6, 0), H + 0.4: (4, 4, 0), L: (0, 0, 0)})
    for k, tr in enumerate(TREES):
        at.rot(tr, {0: (0, 0, 0), H: (0, 0, 0), H + 0.12: (-8 + k % 3 * 3, 0, 6 - k % 4 * 4), H + 0.5: (3, 0, -2),
                    L: (0, 0, 0)})
    for k, rb in enumerate(RIDGES):
        at.pos(rb, {0: (0, 0, 0), H: (0, 0, 0), H + 0.1: (0, -2.5, 0), H + 0.4: (0, 0.6, 0), L: (0, 0, 0)})
    at.sound(1.3, "strain")
    at.particle(H, "dust", locator="foot_fr")
    at.particle(H, "rock", locator="foot_fr")
    at.particle(H + 0.05, "leaf", locator="back")
    A.append(at)

    # ---- attack_b: neck lash - wind up right, sweep low to the left (hit 1.35 s)
    L, H = LEN["attack_b"], HIT["attack_b"]
    ab = Anim("attack_b", length=L, loop="hold")
    neck(ab, {0: (0, 0, 0), 0.8: (12, -30, 0), 1.1: (14, -34, 0), H: (-22, 22, 0), 1.6: (-24, 34, 0), 2.0: (-8, 12, 0),
              L: (0, 0, 0)})
    ab.rot("head", {0: (0, 0, 0), 0.8: (8, -8, 0), H: (-10, 14, 0), 1.6: (-8, 16, 0), L: (0, 0, 0)})
    ab.rot("jaw", {0: (0, 0, 0), 1.1: (0, 0, 0), 1.3: (-22, 0, 0), 1.8: (-8, 0, 0), L: (0, 0, 0)})
    ab.rot("body", {0: (0, 0, 0), 0.8: (0, -3, 2), H: (0, 4, -2), L: (0, 0, 0)})
    ab.rot("chest", {0: (0, 0, 0), 0.8: (0, -4, 0), H: (0, 6, 0), L: (0, 0, 0)})
    tail(ab, {0: (0, 0, 0), 0.8: (0, 18, 0), H: (0, -24, 0), 1.8: (0, -10, 0), L: (0, 0, 0)})
    for s in ("r", "l"):
        sgn = 1 if s == "r" else -1
        ab.rot(f"fleg_{s}_1", {0: (0, 0, 0), 0.8: (0, 0, sgn * 4), H: (0, 0, sgn * 7), L: (0, 0, 0)})
        ab.rot(f"ffoot_{s}", {0: (0, 0, 0), 0.8: (0, 0, sgn * -4), H: (0, 0, sgn * -7), L: (0, 0, 0)})
    ab.sound(1.05, "lash")
    ab.particle(H, "dust", locator="mouth")
    A.append(ab)

    # ---- react: recoil and groan
    L = LEN["react"]
    rc = Anim("react", length=L, loop="hold")
    rc.rot("body", {0: (0, 0, 0), 0.15: (-2, 3, -5), 0.5: (1, -1, 2.5), 0.9: (0, 0, -0.8), L: (0, 0, 0)})
    rc.pos("root", {0: (0, 0, 0), 0.15: (-3, -1, 2), 0.5: (1, 0, -0.5), L: (0, 0, 0)})
    neck(rc, {0: (0, 0, 0), 0.12: (18, 14, 0), 0.45: (-6, -8, 0), 0.9: (3, 2, 0), L: (0, 0, 0)})
    rc.rot("head", {0: (0, 0, 0), 0.12: (12, 0, 12), 0.3: (0, 0, -10), 0.5: (4, 0, 6), 0.8: (0, 0, -2), L: (0, 0, 0)})
    rc.rot("jaw", {0: (0, 0, 0), 0.1: (-16, 0, 0), 0.6: (-6, 0, 0), L: (0, 0, 0)})
    tail(rc, {0: (0, 0, 0), 0.2: (-8, 26, 0), 0.55: (4, -14, 0), 1.0: (0, 4, 0), L: (0, 0, 0)})
    for k, tr in enumerate(TREES):
        rc.rot(tr, {0: (0, 0, 0), 0.15: (0, 0, 6 + k % 3), 0.45: (0, 0, -4), 0.8: (0, 0, 1.5), L: (0, 0, 0)})
    rc.sound(0.05, "groan")
    rc.particle(0.1, "leaf", locator="back")
    A.append(rc)

    # ---- rest: settled on folded legs, head lowered to the ground (loop)
    rs = Anim("rest", loop=True, length=8.0)
    rs.pos("root", (0, -19, 0))
    for s in ("r", "l"):
        rs.rot(f"fleg_{s}_1", (-55, 0, 0))
        rs.rot(f"fleg_{s}_2", (108, 0, 0))
        rs.rot(f"ffoot_{s}", (-53, 0, 0))
        rs.rot(f"hleg_{s}_1", (52, 0, 0))
        rs.rot(f"hleg_{s}_2", (-104, 0, 0))
        rs.rot(f"hfoot_{s}", (52, 0, 0))
    for i, b in enumerate(NECK):
        rs.rot(b, (-3.0 * NECK_W[i] + S(0.4, 8.0, 0.05 * i), S(1.2, 8.0, 0.3 + 0.04 * i), 0))
    rs.rot("head", (18 + S(2.0, 8.0, 0.4), S(4.0, 8.0, 0.5), 0))
    for i, b in enumerate(TAIL):
        rs.rot(b, (2.0 * TAIL_W[i] if i < 4 else -0.6, S(1.5, 8.0, -0.06 * i, 2.0), 0))
    rs.rot("body", (S(0.3, 8.0), 0, S(0.6, 8.0, 0.2)))
    A.append(rs)

    # ---- depart: last moan, petrify (skin 2 set by script at 0.7 s), stiffen, sink into the earth
    L = LEN["depart"]
    dp = Anim("depart", length=L, loop="hold")
    neck(dp, {0: (0, 0, 0), 0.7: (-18, 6, 0), 1.0: (-17, 6, 0), 2.0: (-34, 8, 0), L: (-40, 8, 0)})
    dp.rot("head", {0: (0, 0, 0), 0.4: (10, 0, 0), 0.7: (-6, 0, 0), L: (-12, 0, 0)})
    dp.rot("jaw", {0: (0, 0, 0), 0.1: (-14, 0, 0), 0.65: (-10, 0, 0), 0.75: (0, 0, 0)})
    dp.pos("root", {0: (0, 0, 0), 0.7: (0, -1, 0), 1.0: (0, -1.5, 0), 1.25: (0, -3, 0), 1.9: (0, -34, 0), 2.5: (0, -88, 0),
                    L: (0, -128, 0)})
    dp.rot("root", {0: (0, 0, 0), 1.0: (0, 0, 0), 1.3: (-1.5, 0, 2), 2.0: (-6, 0, -3), L: (-9, 0, 4)})
    dp.scl("root", {0: 1.0, 2.6: (1.02, 0.92, 1.02), 2.75: (1.0, 0.9, 1.0), L: 0.0})
    tail(dp, {0: (0, 0, 0), 0.7: (6, -4, 0), 1.2: (8, -4, 0), L: (14, 8, 0)})
    for k, tr in enumerate(TREES):
        side = 1 if k % 2 else -1
        dp.rot(tr, {0: (0, 0, 0), 1.1 + 0.07 * k: (0, 0, 0), 1.6 + 0.07 * k: (8 * (k % 3 - 1), 0, side * 26),
                    L: (8 * (k % 3 - 1), 0, side * 34)})
    for k, rb in enumerate(RIDGES):
        dp.pos(rb, {0: (0, 0, 0), 1.1: (0, 0, 0), 1.5 + 0.06 * k: (0, -3, 0), L: (0, -6, 0)})
        dp.rot(rb, {0: (0, 0, 0), 1.1: (0, 0, 0), 1.6 + 0.06 * k: ((-1) ** k * 10, 0, (-1) ** k * 8), L: ((-1) ** k * 12, 0, (-1) ** k * 9)})
    dp.sound(0.0, "moan")
    dp.sound(0.75, "petrify")
    dp.particle(1.0, "rock", locator="back")
    dp.particle(1.3, "dust", locator="foot_fl")
    dp.particle(1.3, "dust", locator="foot_hr")
    dp.particle(1.8, "dust", locator="back")
    A.append(dp)
    return A


# ================================================================ supporting constructs
def strata_model():
    """Strata upheaval: five tilted layered slabs with glowing magic veins.  ~5 blocks across at size 1."""
    m = Model("ed_nature_strata", density=1.0, bounds=(14, 9, (0, 2, 0)))
    root = m.bone("root")
    slabs = [((-14, -6), (26, 56, 16), (-14, 8, 18)), ((16, -4), (24, 46, 15), (-10, -12, -22)),
             ((-4, 14), (30, 38, 14), (20, 4, 6)), ((6, -18), (18, 30, 12), (-24, 20, -8)),
             ((20, 16), (14, 24, 10), (18, -30, -16))]
    for i, ((px, pz), (w, h, d), r) in enumerate(slabs):
        b = m.bone(f"slab{i + 1}", root, pivot=(px, 0, pz), rot=r)
        b.box((px, h / 2 - 6, pz), (w, h, d), strata(seed=i, vein=0.85, band=4.2, key="sts"))
        b.box((px + 1.5, h - 5, pz - 1), (w - 5, 2.5, d - 3), strata(seed=i + 5, vein=0.0, band=2.0, key="stc"))
        b.box((px - w * 0.3, h * 0.55 - 6, pz + d * 0.5 + 1.5), (w * 0.35, h * 0.55, 3), strata(seed=i + 9, vein=0.6, band=3.0, key="sts"))
    rub = m.bone("rubble", root)
    st = tex.stone("#6a6158", "#433c34", "#8d8275", scale=2, cracks=0.3)
    for k in range(7):
        a = k * 2 * math.pi / 7 + 0.4
        r = 24 + 6 * (k % 3)
        s = 4 + (k % 3) * 2
        rub.box((r * math.cos(a), s * 0.35, r * math.sin(a)), (s, s * 0.8, s * 1.1), st, rot=(10 * k, 30 * k, 8 * k), variant=k % 3)
    return m, slabs


def strata_anims(slabs):
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    tremble = Anim("tremble", loop=True)
    tremble.pos("root", (LIFE(0.25, 0.23), 0, LIFE(0.2, 0.31, 0.2)))
    A.append(tremble)
    rise = Anim("rise", length=1.3, loop="hold")
    for i in range(len(slabs)):
        t0 = 0.05 + i * 0.09
        rise.pos(f"slab{i + 1}", {0: (0, -64, 0), t0: (0, -64, 0), t0 + 0.5: (0, 5, 0), t0 + 0.72: (0, -1, 0), 1.3: (0, 0, 0)})
        rise.rot(f"slab{i + 1}", {0: (0, 0, 0), t0 + 0.5: ((-1) ** i * 6, 0, (-1) ** i * -5), 1.3: (0, 0, 0)})
    rise.scl("rubble", {0: 0.0, 0.3: 1.25, 0.6: 1.0})
    A.append(rise)
    A.append(Anim("hold", loop=True))
    part_off = {}
    for i, ((px, pz), _s, _r) in enumerate(slabs):
        n = math.hypot(px, pz) or 1
        ox, oz = px / n, pz / n
        part_off[i] = ((ox * 18, -6, oz * 18), (oz * 16, 0, -ox * 16))
    part = Anim("part", length=1.0, loop="hold")
    for i, (p, r) in part_off.items():
        part.pos(f"slab{i + 1}", {0: (0, 0, 0), 0.15: (0, 2, 0), 1.0: p})
        part.rot(f"slab{i + 1}", {0: (0, 0, 0), 0.15: (0, 0, 0), 1.0: r})
    part.scl("rubble", {0: 1.0, 1.0: 1.3})
    A.append(part)
    erupt = Anim("erupt", length=0.7, loop="hold")
    for i, (p, r) in part_off.items():
        up = (p[0] * 0.6, p[1] + 30, p[2] * 0.6)
        erupt.pos(f"slab{i + 1}", {0: p, 0.1 + 0.02 * i: up, 0.7: (p[0], p[1] + 12, p[2])})
        erupt.rot(f"slab{i + 1}", {0: r, 0.12: (r[0] * 0.3, 0, r[2] * 0.3), 0.7: (r[0] * 1.3, 0, r[2] * 1.3)})
    erupt.scl("rubble", {0: 1.3, 0.1: 1.7, 0.7: 1.4})
    A.append(erupt)
    crumble = Anim("crumble", length=1.2, loop="hold")
    for i, (p, r) in part_off.items():
        crumble.pos(f"slab{i + 1}", {0: (p[0], p[1] + 12, p[2]), 1.2: (p[0] * 1.2, -60, p[2] * 1.2)})
        crumble.rot(f"slab{i + 1}", {0: (r[0] * 1.3, 0, r[2] * 1.3), 1.2: (r[0] * 2, 0, r[2] * 2)})
        crumble.scl(f"slab{i + 1}", {0: 1.0, 0.8: (0.9, 0.7, 0.9), 1.2: 0.0})
    crumble.scl("rubble", {0: 1.4, 1.2: 0.0})
    A.append(crumble)
    return A


STRATA_STATES = {0: ["hidden"], 1: ["rise"], 2: ["hold"], 3: ["part"], 4: ["erupt"], 5: ["crumble"]}


def pillar_model():
    """Basalt-and-strata column cluster bound by roots, with one glowing draconic rune.
    ~5.5 blocks tall, ~2 blocks wide at size 1.  Front (-Z) faces the circle it guards."""
    m = Model("ed_nature_pillar", density=1.0, bounds=(10, 10, (0, 3, 0)))
    root = m.bone("root")
    col = m.bone("col", root, pivot=(0, 0, 0))
    cols = [((0, 0), 12, 88, 0), ((-9, 5), 9, 66, 1), ((8, 6), 10, 58, 2), ((2, -9), 8, 46, 3)]
    for (x, z), w, h, k in cols:
        sm = strata(seed=80 + k, vein=0.0, band=3.6, key="pils")
        col.box((x, h / 2 - 8, z), (w, h, w), sm, variant=k)
        col.box((x, h / 2 - 8, z), (w * 0.82, h - 0.5, w * 0.82), sm, rot=(0, 45, 0), variant=k + 4)
        col.box((x, h - 7.2, z), (w + 0.6, 1.6, w + 0.6), nat(tex.foliage("#3e5a26", "#7a9a44", holes=0.2)))
    rootm = tex.overlay(tex.wood("#5b4128", "#33240f", vertical=False), _sap_lines, "pilroot")
    for k in range(3):
        a0 = k * 2.1
        pts = [(8.6 * math.cos(a0 + t * 1.3), 4 + t * 20 + k * 8, 8.6 * math.sin(a0 + t * 1.3)) for t in range(4)]
        for p0, p1 in zip(pts, pts[1:]):
            _stick(col, p0, p1, 2.2, rootm)
    rune = tex.bitmap_cut(glyphs.DRACONIC[4], "#d8ffb0", glow=1.0, color2="#6fd04a")
    col.plane("z", (0, 46, -9.2), 7, 9.8, rune)
    cap = m.bone("cap", col, pivot=(0, 80, 0))
    fern = tex.foliage("#2f6a2a", "#86b84f", holes=0.35, scale=1.3)
    cap.plane("z", (0, 84, 0), 10, 8, fern, rot=(0, 30, 0), pivot=(0, 80, 0))
    cap.plane("z", (0, 84, 0), 10, 8, fern, rot=(0, -60, 0), pivot=(0, 80, 0), variant=1)
    rub = m.bone("rubble", root)
    st = tex.stone("#5d574e", "#3d3832", "#837a6c", scale=2, cracks=0.3)
    for k in range(6):
        a = k * 60 + 15
        r = 12 + 3 * (k % 2)
        s = 3.5 + (k % 3)
        rub.box((r * math.cos(math.radians(a)), s * 0.3, r * math.sin(math.radians(a))), (s, s * 0.7, s), st,
                rot=(12 * k, 40 * k, 0), variant=k % 3)
    return m


def _sap_lines(ctx, t):
    ix, iy = tex.px(ctx)
    ln = (iy % 5 == 2) & (tex._hash(ix // 3, iy, 99) > 0.4)
    t[..., :3] = np.where(ln[..., None], tex.rgb(SAP), t[..., :3])
    t[..., 4] = np.where(ln, 0.7, t[..., 4])
    return t


PILLAR_IMPACT = 0.6   # seconds into `erupt` where the toppling pillar hits the ground


def pillar_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    rise = Anim("rise", length=0.8, loop="hold")
    rise.pos("col", {0: (0, -96, 0), 0.38: (0, 8, 0), 0.52: (0, -2.5, 0), 0.8: (0, 0, 0)})
    rise.rot("col", {0: (6, 0, -4), 0.38: (-3, 8, 3), 0.6: (1, 0, -1), 0.8: (0, 0, 0)})
    rise.scl("rubble", {0: 0.0, 0.3: 1.3, 0.8: 1.0})
    rise.scl("cap", {0: 0.3, 0.45: 0.3, 0.8: 1.0})
    A.append(rise)
    hold = Anim("hold", loop=True)
    hold.rot("cap", (0, 0, LIFE(2.5, 2.7)))
    A.append(hold)
    erupt = Anim("erupt", length=1.1, loop="hold")      # thrust up, topple toward the front (centre), shatter
    I = PILLAR_IMPACT
    erupt.pos("col", {0: (0, 0, 0), 0.14: (0, 16, 0), 0.24: (0, 13, 0), I: (0, 2, -4), I + 0.1: (0, -1, -5), 1.1: (0, -2, -5)})
    erupt.rot("col", {0: (0, 0, 0), 0.14: (7, 0, 2), 0.24: (4, 0, 1), I: (-86, 0, -3), I + 0.08: (-80, 0, -2), 1.1: (-84, 0, -3)})
    erupt.scl("col", {0: 1.0, I: 1.0, I + 0.1: (1.25, 0.75, 1.25), 0.85: (1.2, 0.6, 1.2), 1.1: 0.0})
    erupt.scl("rubble", {0: 1.0, 0.14: 1.6, 1.1: 0.0})
    A.append(erupt)
    crumble = Anim("crumble", length=0.9, loop="hold")
    crumble.pos("col", {0: (0, 0, 0), 0.9: (0, -50, 0)})
    crumble.rot("col", {0: (0, 0, 0), 0.9: (8, 0, -6)})
    crumble.scl("col", {0: 1.0, 0.6: (0.85, 0.8, 0.85), 0.9: 0.0})
    crumble.scl("rubble", {0: 1.0, 0.9: 0.0})
    A.append(crumble)
    return A


PILLAR_STATES = {0: ["hidden"], 1: ["rise"], 2: ["hold"], 3: ["erupt"], 4: ["crumble"]}

ROOT_LEN_BLOCKS = 6.0     # root reach at size 1
ROOT_SEGS = 8


def root_model():
    """Snaking root that grows forward (-Z) 6 blocks (x size) and closes a 4-claw cage at its tip.
    The `grip` bone is counter-scaled by 1/size so the cage always fits a mob."""
    m = Model("ed_nature_root", density=1.0, bounds=(18, 6, (0, 1, -3)))
    root = m.bone("root")
    rootm = tex.overlay(tex.wood("#5b4128", "#2e2010", vertical=False), _sap_lines, "rootm")
    mossy = tex.mottled("#5b4128", "#55702e", scale=2.0, thresh=0.6)
    seg_len = 96.0 / ROOT_SEGS
    xs = [3.5 * math.sin(i * 0.95) for i in range(ROOT_SEGS + 1)]
    for i in range(ROOT_SEGS):
        f = i / (ROOT_SEGS - 1)
        w = 8.5 - 4.5 * f
        h = 7.0 - 3.2 * f
        z0, z1 = -seg_len * i, -seg_len * (i + 1)
        b = m.bone(f"seg{i + 1}", root, pivot=(xs[i], 0, z0))
        mid = ((xs[i] + xs[i + 1]) / 2, h * 0.28, (z0 + z1) / 2)
        ry = math.degrees(math.atan2(-(xs[i + 1] - xs[i]), seg_len))
        b.box(mid, (w, h, seg_len + 3), rootm, rot=(0, ry, 0), pivot=mid, variant=i % 3)
        b.box((mid[0], mid[1] + h * 0.45, mid[2]), (w * 0.6, 1.2, seg_len * 0.7), mossy, rot=(0, ry, 0), pivot=mid)
        sd = 1 if i % 2 else -1
        _stick(b, (mid[0] + sd * w * 0.4, h * 0.3, mid[2]), (mid[0] + sd * (w * 0.4 + 7), -1, mid[2] + 4), 1.6 - 0.1 * i, rootm)
    tip = (xs[-1], 0, -96)
    grip = m.bone("grip", root, pivot=tip)
    claw = tex.overlay(tex.wood("#4a3420", "#2a1c0c", vertical=True), _sap_lines, "clawm")
    thorn = tex.bone_mat(IVORY, "#a8946a", pores=0.1)
    for k in range(4):
        cb = m.bone(f"claw{k + 1}", grip, pivot=tip, rot=(0, 45 + 90 * k, 0))
        ca = m.bone(f"claw{k + 1}a", cb, pivot=(tip[0], 0, tip[2] - 8))
        x, z = tip[0], tip[2] - 8
        _stick(ca, (x, -1, z), (x, 15, z - 0.5), 3.4, claw)
        _stick(ca, (x, 15, z - 0.5), (x, 27, z + 4.5), 2.6, claw)
        _stick(ca, (x, 27, z + 4.5), (x, 33, z + 7.5), 1.4, thorn)
        ca.box((x, 8, z - 1.6), (3.6, 4, 1.2), nat(tex.foliage("#3e5a26", "#7a9a44", holes=0.3)))
    return m


def root_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    always = Anim("fit", loop=True)
    always.scl("grip", M("1.0 / math.max(0.3, q.property('grimoire:size'))", lambda t: 1.0))
    A.append(always)
    grow = Anim("grow", length=1.25, loop="hold")
    for i in range(ROOT_SEGS):
        t0 = 0.05 + i * 0.08
        b = f"seg{i + 1}"
        grow.scl(b, {0: (0.2, 0.2, 0.0), t0: (0.2, 0.2, 0.0), t0 + 0.14: (1.15, 1.2, 1.0), t0 + 0.3: (1.0, 1.0, 1.0)})
        grow.pos(b, {0: (0, -5, 0), t0: (0, -5, 0), t0 + 0.12: (0, 1.5, 0), t0 + 0.3: (0, 0, 0)})
    for k in range(4):
        ca = f"claw{k + 1}a"
        grow.scl(ca, {0: 0.0, 0.7: 0.0, 0.82: 1.0})
        grow.rot(ca, {0: (-85, 0, 0), 0.7: (-85, 0, 0), 0.9: (-55, 0, 0), 1.05: (10, 0, 0), 1.15: (-3, 0, 0), 1.25: (0, 0, 0)})
    A.append(grow)
    hold = Anim("hold", loop=True, length=2.0)
    for i in range(ROOT_SEGS):
        hold.rot(f"seg{i + 1}", (0, S(2.5, 2.0, -0.09 * i), 0))
        hold.pos(f"seg{i + 1}", (0, S(0.4, 1.0, -0.1 * i, 0.2), 0))
    for k in range(4):
        hold.rot(f"claw{k + 1}a", (S(3.0, 1.0, 0.1 * k, 3.0), 0, 0))
    A.append(hold)
    erupt = Anim("erupt", length=0.8, loop="hold")
    for i in range(ROOT_SEGS):
        t0 = 0.02 + 0.025 * i
        b = f"seg{i + 1}"
        erupt.pos(b, {0: (0, 0, 0), t0 + 0.08: (0, 12 + i, 0), t0 + 0.3: (0, 6, 0), 0.8: (0, -4, 0)})
        erupt.rot(b, {0: (0, 0, 0), t0 + 0.08: ((-1) ** i * 18, (-1) ** i * 12, 0), 0.8: ((-1) ** i * 30, 0, 0)})
        erupt.scl(b, {0: 1.0, t0 + 0.08: 1.35, 0.5: 1.0, 0.8: 0.0})
    for k in range(4):
        ca = f"claw{k + 1}a"
        erupt.rot(ca, {0: (0, 0, 0), 0.08: (14, 0, 0), 0.25: (-110, 0, 0), 0.8: (-120, 0, 0)})
        erupt.scl(ca, {0: 1.0, 0.25: 1.5, 0.8: 0.0})
    A.append(erupt)
    wither = Anim("wither", length=1.0, loop="hold")
    for i in range(ROOT_SEGS):
        wither.scl(f"seg{i + 1}", {0: 1.0, 1.0: (0.6, 0.0, 1.0)})
        wither.pos(f"seg{i + 1}", {0: (0, 0, 0), 1.0: (0, -4, 0)})
    for k in range(4):
        wither.rot(f"claw{k + 1}a", {0: (0, 0, 0), 0.6: (-60, 0, 0)})
        wither.scl(f"claw{k + 1}a", {0: 1.0, 1.0: 0.0})
    A.append(wither)
    return A


ROOT_STATES = {0: ["hidden"], 1: ["grow"], 2: ["hold"], 3: ["erupt"], 4: ["wither"]}
ROOT_BIND = 1.05   # seconds into `grow` when the cage closes


def quake_model():
    """Footfall shock decal: radial glowing fissure + jumping rock chunks.  Radius 2 blocks at size 1."""
    m = Model("ed_nature_quake", density=1.0, bounds=(8, 3, (0, 0, 0)))
    root = m.bone("root")
    crack = m.bone("crack", root)
    crack.plane("y", (0, 0.5, 0), 64, 64, crack_disc(), faces=("up",))
    st = tex.stone("#6e655a", "#463f36", "#8f8678", scale=2, cracks=0.3, strata=0.0)
    moss = tex.mottled("#6e655a", "#557a2c", scale=1.5, thresh=0.5)
    for k in range(9):
        a = k * 40 + 10
        r = 9 + 11 * ((k * 7) % 3) / 2
        s = 3 + (k % 3) * 1.5
        c = (r * math.cos(math.radians(a)), s * 0.4, r * math.sin(math.radians(a)))
        b = m.bone(f"chunk{k + 1}", root, pivot=c)
        b.box(c, (s, s * 0.8, s * 1.1), moss if k % 3 == 0 else st, variant=k % 3)
    return m


def quake_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    burst = Anim("burst", length=1.3, loop="hold")
    burst.scl("crack", {0: 0.15, 0.1: 1.05, 0.3: 1.0, 0.95: 1.0, 1.3: 0.0})
    for k in range(9):
        h = 10 + (k % 4) * 5
        t1 = 0.22 + (k % 3) * 0.05
        burst.pos(f"chunk{k + 1}", {0: (0, -4, 0), 0.04: (0, 0, 0), t1: (0, h, 0), t1 * 2: (0, 0, 0), 1.3: (0, -3, 0)})
        burst.rot(f"chunk{k + 1}", {0: (0, 0, 0), t1 * 2: (140 + 30 * k, 60 * k, 90), 1.3: (150 + 30 * k, 60 * k, 90)})
        burst.scl(f"chunk{k + 1}", {0: 0.0, 0.05: 1.2, 0.9: 1.0, 1.3: 0.0})
    A.append(burst)
    return A


# ================================================================ sounds
def _call(dur, contour, horn=1.0, rough=0.25, whale=0.35, sub=0.6, bright=3000, growl=17.0):
    """Deep titanosaur call: low saw voice through horn-like formants, an infrasonic sub, and a
    gliding whale-like overtone moan."""
    t = sy.t_axis(dur)
    xs, ys = zip(*contour)
    f = np.interp(t / dur, xs, ys)
    f = f * (1 + 0.012 * np.sin(2 * np.pi * 4.1 * t) + 0.05 * sy.lowpass(sy.noise(dur), 5) * 3)
    src = sy.osc(f, wave_="saw") + 0.4 * sy.osc(f * 1.003, wave_="saw", phase=1.1)
    src *= 1 - rough * 0.5 * (1 + np.sign(np.sin(2 * np.pi * growl * t + 1.5 * np.sin(2 * np.pi * 1.7 * t))))
    voiced = sy.formants(src, [(240, 110, 1.0), (520, 150, 0.75 * horn), (1180, 240, 0.32 * horn), (2350, 380, 0.08 * horn)])
    wf = f * np.interp(t / dur, [0, 0.3, 0.65, 1.0], [3.0, 4.3, 3.7, 2.7])
    moan = sy.osc(wf) * sy.env(dur, 0.4 * dur, 0.1, 0.8, 0.4 * dur) * whale
    low = sy.osc(f * 0.5) * sub
    breath = sy.lowpass(sy.noise(dur), 500) * 0.22
    e = sy.env(dur, 0.22 * dur, 0.1, 0.85, 0.35 * dur)
    return sy.norm(sy.lowpass((sy.norm(voiced) + low + moan + breath) * e, bright))


def _rustle(dur, density=0.6):
    t = sy.t_axis(dur)
    n = sy.bandpass(sy.noise(dur), 3200, 1.1)
    flutter = 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 7.3 * t + 3 * np.sin(2 * np.pi * 0.8 * t)))
    return sy.norm(n * flutter * density * sy.env(dur, 0.3 * dur, 0.1, 0.9, 0.3 * dur))


def build_sounds(pack):
    rv = sy.reverb
    call = _call(3.2, [(0, 58), (0.28, 76), (0.6, 64), (1.0, 46)], horn=1.0, whale=0.4)
    sy.save(pack, "ed_nature_call", rv(sy.at(3.2, (0.0, call), (0.0, sy.rumble(3.0, 40, 1.2) * 0.35)), 2.6, 0.42),
            max_distance=96, volume=1.0)
    bell = _call(3.0, [(0, 66), (0.35, 104), (0.7, 96), (1.0, 80)], horn=1.4, whale=0.5, rough=0.15, bright=4200)
    sy.save(pack, "ed_nature_bellow", rv(sy.at(3.0, (0.0, bell), (0.5, _rustle(2.3) * 0.35)), 2.6, 0.42), max_distance=96)
    sy.save(pack, "ed_nature_groan", rv(_call(1.3, [(0, 62), (0.3, 70), (1.0, 44)], horn=0.7, rough=0.55, whale=0.15), 1.4, 0.3),
            max_distance=64)
    moan = _call(2.6, [(0, 60), (0.25, 64), (1.0, 34)], horn=0.8, whale=0.45, rough=0.3)
    sy.save(pack, "ed_nature_moan", rv(moan, 2.4, 0.45), max_distance=80)
    strain = _call(1.6, [(0, 52), (0.6, 82), (1.0, 92)], horn=1.2, rough=0.5, whale=0.2)
    sy.save(pack, "ed_nature_strain", rv(strain, 1.8, 0.35), max_distance=80)
    lash = sy.at(1.2, (0.0, sy.whoosh(0.8, 160, 1400) * 0.8), (0.1, _call(0.9, [(0, 70), (1, 58)], rough=0.6, whale=0.0) * 0.6))
    sy.save(pack, "ed_nature_lash", rv(lash, 1.0, 0.25), max_distance=64)

    def step(p=1.0):
        s = sy.at(1.4, (0.0, sy.thump(1.2, 70 * p, 24, 0.5)), (0.0, sy.rumble(1.3, 42, 2.0) * 0.45),
                  (0.03, sy.lowpass(sy.crack(0.9, 1400, 26), 2400) * 0.3))
        return rv(s, 1.1, 0.25)
    sy.save(pack, "ed_nature_step", step(), variants=[step(0.9), step(1.12)], max_distance=72)
    qk = sy.at(1.1, (0.0, sy.crack(0.7, 2600, 22) * 0.6), (0.0, sy.thump(0.8, 90, 40, 0.6) * 0.6),
               (0.1, sy.lowpass(sy.crack(1.0, 900, 40), 1500) * 0.5))
    sy.save(pack, "ed_nature_quake", rv(qk, 0.9, 0.25), variants=[rv(sy.pitch(qk, 0.88), 0.9, 0.25)], max_distance=56)
    rum = sy.at(3.0, (0.0, sy.rumble(3.0, 38, 1.6)), (0.4, sy.lowpass(sy.creak(2.2, 40, 70, 0.4), 600) * 0.5),
                (0.8, sy.lowpass(sy.crack(2.0, 700, 50), 1200) * 0.35))
    sy.save(pack, "ed_nature_rumble", rv(rum, 2.0, 0.35), max_distance=96)
    grind = sy.at(1.6, (0.0, sy.lowpass(sy.creak(1.4, 55, 90, 0.5), 900) * 0.8), (0.0, sy.rumble(1.5, 50, 4) * 0.6),
                  (0.2, sy.crack(1.2, 1800, 30) * 0.35), (1.0, sy.thump(0.6, 80, 34, 0.4) * 0.6))
    sy.save(pack, "ed_nature_strata", rv(grind, 1.4, 0.3), max_distance=80)
    grow = sy.at(2.4, (0.0, _rustle(2.4, 0.8) * 0.6), (0.1, sy.creak(1.0, 140, 300, 0.3) * 0.35),
                 (0.7, sy.creak(1.1, 110, 240, 0.3) * 0.3), (1.2, sy.creak(0.9, 180, 380, 0.3) * 0.25),
                 (0.5, sy.shimmer(1.6, 1500, 14) * 0.18))
    sy.save(pack, "ed_nature_grow", rv(grow, 1.6, 0.35), max_distance=72)
    rootc = sy.at(1.3, (0.0, sy.lowpass(sy.crack(1.2, 900, 60), 1600) * 0.7), (0.0, sy.creak(1.1, 90, 160, 0.4) * 0.5),
                  (0.0, sy.lowpass(sy.noise(1.2), 300) * sy.env(1.2, 0.2, 0.2, 0.7, 0.4) * 0.5))
    sy.save(pack, "ed_nature_root", rv(rootc, 1.0, 0.25), variants=[rv(sy.pitch(rootc, 1.15), 1.0, 0.25)], max_distance=48)
    bind = sy.at(0.8, (0.0, sy.creak(0.5, 220, 120, 0.2) * 0.6), (0.3, sy.crack(0.4, 2400, 8) * 0.6))
    sy.save(pack, "ed_nature_bind", rv(bind, 0.7, 0.2), max_distance=40)
    pil = sy.at(1.3, (0.0, sy.whoosh(0.5, 120, 700) * 0.5), (0.3, sy.thump(0.8, 90, 32, 0.6)), (0.32, sy.crack(0.8, 1600, 24) * 0.45),
                (0.0, sy.rumble(1.2, 55, 3) * 0.4))
    sy.save(pack, "ed_nature_pillar", rv(pil, 1.2, 0.3), variants=[rv(sy.pitch(pil, 0.9), 1.2, 0.3)], max_distance=64)
    slam = sy.at(2.8, (0.0, sy.thump(1.8, 62, 18, 0.8)), (0.0, sy.crack(0.9, 3000, 30) * 0.5), (0.05, sy.rumble(2.6, 34, 1.2) * 0.8),
                 (0.15, sy.lowpass(sy.crack(2.2, 800, 90), 1400) * 0.45), (0.0, sy.whoosh(0.4, 2000, 200) * 0.3))
    sy.save(pack, "ed_nature_slam", rv(slam, 2.2, 0.38), max_distance=128)
    er = sy.at(1.3, (0.0, sy.crack(0.8, 2200, 26) * 0.7), (0.02, sy.thump(0.9, 100, 36, 0.6) * 0.7),
               (0.05, sy.creak(0.6, 260, 120, 0.3) * 0.35), (0.15, sy.lowpass(sy.crack(1.0, 900, 40), 1400) * 0.4))
    sy.save(pack, "ed_nature_erupt", rv(er, 1.1, 0.3), variants=[rv(sy.pitch(er, 1.1), 1.1, 0.3), rv(sy.pitch(er, 0.9), 1.1, 0.3)],
            max_distance=72)
    top = sy.at(1.5, (0.0, sy.whoosh(0.6, 700, 120) * 0.6), (0.55, sy.thump(0.9, 75, 26, 0.7)), (0.56, sy.crack(0.9, 2000, 40) * 0.55))
    sy.save(pack, "ed_nature_topple", rv(top, 1.3, 0.3), variants=[rv(sy.pitch(top, 0.92), 1.3, 0.3)], max_distance=72)
    pet = sy.at(2.0, (0.0, sy.crack(1.9, 3400, 90) * 0.5), (0.0, sy.lowpass(sy.creak(1.8, 50, 80, 0.5), 800) * 0.6),
                (0.3, sy.rumble(1.6, 40, 1.5) * 0.5))
    sy.save(pack, "ed_nature_petrify", rv(pet, 1.6, 0.35), max_distance=80)


# ================================================================ build
def build(pack):
    fx = particles(pack)
    fx.effect("ed_nature_dust", "puff", count=12, life=(0.9, 1.8), size=(0.6, 1.7), shape=("disc", 1.8), speed=(1.0, 3.0),
              accel=(0, 0.5, 0), drag=1.6, colors=["#8a7558cc", "#6b5a4466", "#6b5a4400"], blend="blend", spin=(360, 30))
    fx.effect("ed_nature_rock", "rock", count=10, life=(0.8, 1.4), size=(0.2, 0.14), shape=("disc", 1.2), direction=(0, 1, 0),
              speed=(4, 8), accel=(0, -18, 0), colors=["#6e655aff", "#4a443cff"], blend="alpha", spin=(360, 220), collide=True)
    fx.effect("ed_nature_leaf", "leaf", count=8, life=(1.8, 3.0), size=(0.16, 0.12), shape=("sphere", 2.5), speed=(0.4, 1.2),
              accel=(0, -0.9, 0), drag=1.4, colors=["#86b84fff", "#4f8a3aff", "#3f6a2a00"], blend="alpha", spin=(360, 160))
    fx.effect("ed_nature_pollen", "dot", count=10, life=(1.4, 2.6), size=(0.09, 0.0), shape=("sphere", 3.0), speed=(0.1, 0.5),
              accel=(0, 0.5, 0), colors=["#f0ffc0ff", "#9cff7aaa", "#9cff7a00"])
    fx.effect("ed_nature_petal", "petal", count=10, life=(1.6, 2.8), size=(0.14, 0.1), shape=("sphere", 2.0), speed=(0.5, 1.6),
              accel=(0, -0.6, 0), drag=1.2, colors=["#f6c8e0ff", "#fff4c8ff", "#e7a6d800"], blend="alpha", spin=(360, 140))
    fx.effect("ed_nature_shock", "ringthin", count=1, life=(0.55, 0.65), size=(0.5, 4.8), facing="emitter_transform_xz",
              colors=["#e8ffc0ff", "#9cff7acc", "#8a6a3a00"])
    fx.effect("ed_nature_shock_big", "ring", count=1, life=(0.8, 0.9), size=(1.0, 11.0), facing="emitter_transform_xz",
              colors=["#ffffffff", "#c8ff9acc", "#8a6a3a00"])
    fx.effect("ed_nature_spore", "spark", count=12, life=(0.4, 0.9), size=(0.14, 0.0), shape=("sphere", 0.6), speed=(2.0, 5.0),
              accel=(0, -2, 0), drag=1.0, colors=["#f0ffd0ff", "#9cff7aff", "#3f8a2a00"], spin=(360, 200))
    fx.effect("ed_nature_splinter", "shard", count=10, life=(0.6, 1.2), size=(0.16, 0.08), shape=("sphere", 0.8), speed=(3, 7),
              accel=(0, -12, 0), colors=["#7a5a36ff", "#4a3420ff"], blend="alpha", spin=(360, 300), collide=True)
    fx.effect("ed_nature_rise", "beam", count=6, life=(0.4, 0.7), size=(0.12, 0.02), size_y=(1.2, 2.6), shape=("disc", 1.0),
              direction=(0, 1, 0), speed=(4, 9), colors=["#e8ffd0ff", "#9cff7aff", "#3f8a2a00"], facing="lookat_y")
    fx.effect("ed_nature_mote", "dot", count=6, life=(1.0, 2.0), size=(0.07, 0.0), shape=("disc", 3.0), speed=(0.05, 0.3),
              accel=(0, 0.6, 0), colors=["#d8ffb0ff", "#9cff7a00"])

    build_sounds(pack)

    # ---- the dragon
    m, info = build_model()
    anims = build_anims(info)
    spec = {k: {"animations": v, "blend": _BLEND[k]} for k, v in STATES.items()}
    pack.actor(ACTOR, m, anims, spec, always=["breathe", "life", "forest"], scale=SCALE, lifetime=150,
               init=["v.ft = 0.0; v.fg = 0.0;"],
               pre_anim=["v.ft = q.property('grimoire:state') == 8 ? 1.0 : (q.property('grimoire:state') == 0 ? 0.0 : v.ft);",
                         "v.fg = v.fg + (v.ft - v.fg) * math.min(1.0, q.delta_time * 1.1);"],
               sounds={"step": "grimoire.ed_nature_step", "call": "grimoire.ed_nature_call", "bellow": "grimoire.ed_nature_bellow",
                       "groan": "grimoire.ed_nature_groan", "moan": "grimoire.ed_nature_moan", "strain": "grimoire.ed_nature_strain",
                       "lash": "grimoire.ed_nature_lash", "petrify": "grimoire.ed_nature_petrify"},
               particles={"dust": "grimoire:ed_nature_dust", "rock": "grimoire:ed_nature_rock", "leaf": "grimoire:ed_nature_leaf",
                          "pollen": "grimoire:ed_nature_pollen"},
               display="Nature Dragon", collision=(2.0, 4.0))

    # ---- constructs
    sm, slabs = strata_model()
    pack.actor("ed_nature_strata", sm, strata_anims(slabs), STRATA_STATES, always=["tremble"], size_prop=True, lifetime=60,
               display="Living Strata", blend=0.1)
    pm = pillar_model()
    pack.actor("ed_nature_pillar", pm, pillar_anims(), PILLAR_STATES, size_prop=True, lifetime=60, display="Root-Bound Pillar",
               blend=0.05)
    rm = root_model()
    pack.actor("ed_nature_root", rm, root_anims(), ROOT_STATES, always=["fit"], size_prop=True, lifetime=60,
               display="Snaking Root", blend=0.05)
    qm = quake_model()
    pack.actor("ed_nature_quake", qm, quake_anims(), {0: ["hidden"], 1: ["burst"]}, size_prop=True, lifetime=20,
               display="Geological Shock", blend=0.0)

    # ---- previews
    by = {a.name: a for a in anims}
    full = Anim("forest_full", loop=True)
    for tr in TREES + info["antlers"]:
        full.scl(tr, 1.0)
    br = (by["breathe"], 1.0)
    side, q34, back, top = (90, 4), (35, 14), (150, 16), (0, 82)
    pack.preview("ed_nature_a", m, [[(by["idle"], 0.5), br], [(by["idle"], 0.5), br, (full, 0)]],
                 views=(side, q34, back, top), cell=(420, 300))
    pack.preview("ed_nature_walk", m, [[(by["move"], t), br] for t in (0.0, 0.8, 1.6, 2.4)], views=(side, (20, 10)),
                 cell=(480, 300))
    pack.preview("ed_nature_poses", m, [[(by["arrive"], 1.3), br, (by["forest"], 0)], [(by["move"], 1.2), br, (by["forest"], 0)],
                                        [(by["power"], 2.6), br, (full, 0)], [(by["attack_a"], 1.9), br, (full, 0)],
                                        [(by["attack_a"], 2.3), br, (full, 0)], [(by["attack_b"], 1.35), br, (full, 0)],
                                        [(by["rest"], 1.0), br], [(by["depart"], 2.0), br]],
                 views=(side, q34), cell=(420, 280), skin="bloom")
    pack.preview("ed_nature_skins", m, [[(by["idle"], 0.5), br, (full, 0)], [(by["turn_l"], 0.6), br]],
                 views=((60, 20), (120, 25)), cell=(420, 300), skin="stone")
    pack.preview("ed_nature_head", m, [[(by["idle"], 0.5), br, (full, 0)]], views=((60, 10), (0, 5)), cell=(420, 300),
                 fit=((0, 106, -141), 24))
    sa = {a.name: a for a in strata_anims(slabs)}
    pa = {a.name: a for a in pillar_anims()}
    ra = {a.name: a for a in root_anims()}
    qa = {a.name: a for a in quake_anims()}
    pack.preview("ed_nature_strata", sm, [(sa["hold"], 0), (sa["part"], 1.0), (sa["erupt"], 0.12)], views=((25, 20), (0, 70)),
                 cell=(320, 320))
    pack.preview("ed_nature_pillar", pm, [(pa["hold"], 0), (pa["erupt"], 0.2), (pa["erupt"], 0.65)], views=((25, 12), (100, 10)),
                 cell=(320, 320))
    pack.preview("ed_nature_root", rm, [(ra["grow"], 0.5), (ra["hold"], 0.3), (ra["erupt"], 0.15)], views=((35, 30), (110, 20)),
                 cell=(360, 300))
    pack.preview("ed_nature_quake", qm, [(qa["burst"], 0.3)], views=((0, 80), (25, 30)), cell=(320, 320))
    print(f"    dragon_nature: {m.cube_count()} cubes, {len(m.order)} bones, tex {m.tex_size}")
    print(f"    strata {sm.cube_count()}c, pillar {pm.cube_count()}c, root {rm.cube_count()}c, quake {qm.cube_count()}c")
