"""DN05 The City That Sleeps Above the World -- the floating dream city.

Districts (each its own actor so they animate independently and cull well):
  dn_city_spire      central ivory spire district on a cloud island (hero, nightmare skin)
  dn_city_quarter_a  tower quarter on a cloud island (x4 around the spire, two layouts)
  dn_city_quarter_b
  dn_city_ring       four folding bridges + the floating ring road linking the quarters
  dn_city_mini       the miniature city the metropolis folds into above the Grimoire
  dn_city_wave       the final dream-wave (ring + aurora wall, sized by script)
Shared materials / palette live here (dn_city_constructs imports them), plus every DN05
particle and sound.

All districts share one state table (DISTRICT_STATES); the spell mirrors it.
Every district model is authored at 1/16 block and rendered at SCALE = 2.
"""
from __future__ import annotations

import math

import numpy as np

from kit import glyphs, synth as sy, tex
from kit.anim import LIFE, Anim, M, S
from kit.geo import Mat, Model, ring

from .a_fx_common import particles

# ---- palette (Dream & Nightmare)
IVORY, PEACH, PINK, GOLD, BLUE = "#f6efe0", "#ffd9b8", "#e8b4c8", "#e9cf8a", "#bcd6f0"
INDIGO, MAUVE, BURG, AGED, GRAY = "#2a2d52", "#6a4a6e", "#6e2f3a", "#cfc6b0", "#8b8f9a"

SCALE = 2.0
# timing (seconds) -- mirrored in src/spells/dn05_sleeping_city.ts
T_ASM, T_LIV, T_WARP, T_NIGHT, T_COL = 5.0, 6.0, 2.0, 4.0, 3.0
DISTRICT_STATES = {0: ["hidden"], 1: ["assemble"], 2: ["dream"], 3: ["living"], 4: ["warp"], 5: ["nightmare"],
                   6: ["collapse"]}
# geometry shared with the ring: quarter centre distance and radii (model units)
R_QUARTER, R_SPIRE_EDGE, R_ISLAND = 120.0, 44.0, 34.0


def spin(rate, clock="q.life_time"):
    return M(f"{clock}*{rate}", lambda t: t * rate)


# ====================================================================== materials
def cloud_mat(c0, c1, key, a=0.72, glow=0.3, soft=1.0):
    """Soft cloud: noisy disc with translucent edges (blend)."""
    k0, k1 = tex.rgb(c0), tex.rgb(c1)

    def fn(ctx):
        u, v = ctx.U * 2 - 1, ctx.V * 2 - 1
        r = np.hypot(u, v) if soft else np.maximum(np.abs(u), np.abs(v)) * 0.9
        ix, iy = tex.px(ctx)
        n = tex.fbm(ix / max(ctx.w / 5.0, 1) + ctx.variant * 7.3, iy / max(ctx.h / 5.0, 1), 301, 3)
        cover = np.clip((1.0 - r * 1.08) * 1.7 + (n - 0.5) * 1.4, 0, 1)
        t = tex.tile(ctx, c0, 1, glow)
        t[..., :3] = tex.mix(k1, k0, np.clip(n * 1.25 + (1 - r) * 0.35 - 0.2, 0, 1)[..., None])
        t[..., 3] = cover * a
        return t
    return Mat(fn, key, mode="blend")


def eye_wall(wall, frame, iris, key, cols=2, rows=2):
    """Nightmare facade: stained aged stone whose windows have become almond eyes, jittered
    out of their grid and clustered."""
    kw, kf, ki = tex.rgb(wall), tex.rgb(frame), tex.rgb(iris)

    def fn(ctx):
        t = tex.grain(ctx, tex.tile(ctx, wall), 0.05)
        ix, iy = tex.px(ctx)
        streak = tex.vnoise(ix / 1.5 + ctx.variant * 3, iy / 7.0, 401)
        t[..., :3] = kw * (0.78 + 0.3 * streak)[..., None]
        ci, cj = np.floor(ctx.U * cols), np.floor(ctx.V * rows)
        jx = (tex._hash(ci, cj, 411 + ctx.variant) - 0.5) * 0.36
        jy = (tex._hash(ci, cj, 412 + ctx.variant) - 0.5) * 0.4
        sz = 0.7 + 0.5 * tex._hash(ci, cj, 413 + ctx.variant)
        cu = ((ctx.U * cols) % 1.0 - 0.5 - jx) / (0.42 * sz)
        cv = ((ctx.V * rows) % 1.0 - 0.5 - jy) / (0.3 * sz)
        almond = np.abs(cv) <= (1 - cu ** 2) * 0.9
        rim = (np.abs(cv) <= (1 - cu ** 2) * 0.9 + 0.35) & (np.abs(cu) <= 1.12) & ~almond
        r = np.hypot(cu, cv * 1.1)
        t[..., :3] = np.where(rim[..., None], kf, t[..., :3])
        t[..., :3] = np.where(almond[..., None], tex.mix(ki, np.array([1.0, 0.9, 0.95]), np.clip(r, 0, 1)[..., None] ** 2), t[..., :3])
        pupil = almond & (np.abs(cu) < 0.13) & (np.abs(cv) < 0.75)
        t[..., :3] = np.where(pupil[..., None], np.array([0.05, 0.03, 0.08]), t[..., :3])
        t[..., 4] = np.where(almond & ~pupil, 0.85, 0.0)
        return tex.edge(ctx, t, 0.15)
    return Mat(fn, f"eyewall{key}{wall}{frame}{iris}{cols}{rows}")


def arch_window_mat(glass, frame, key, glow=1.0):
    """Tall arched window plane (cut-out): glowing glass, mullion cross, frame."""
    kg, kf = tex.rgb(glass), tex.rgb(frame)

    def fn(ctx):
        u, v = ctx.U * 2 - 1, 1 - ctx.V * 2
        outer = (np.abs(u) <= 0.95) & ((v < 0.35) | (np.hypot(u / 0.95, (v - 0.35) / 0.62) <= 1)) & (v > -0.97)
        inner = (np.abs(u) <= 0.7) & ((v < 0.35) | (np.hypot(u / 0.7, (v - 0.35) / 0.45) <= 1)) & (v > -0.85)
        t = tex.tile(ctx, frame, 1, 0.0)
        t[..., :3] = np.where(inner[..., None], tex.mix(kg, np.array([1.0, 1.0, 0.95]), np.clip(1 - np.abs(u), 0, 1)[..., None] * 0.5), kf)
        mull = inner & ((np.abs(u) < 0.09) | (np.abs(v + 0.15) < 0.05))
        t[..., :3] = np.where(mull[..., None], kf, t[..., :3])
        t[..., 4] = np.where(inner & ~mull, glow, 0.0)
        t[..., 3] = np.where(outer, 1.0, 0.0)
        return t
    return Mat(fn, f"archwin{key}{glass}{frame}{glow}", directional=True)


def door_mat(door, frame, knob, key, eye=False):
    """Arched door with panels and a glowing knob (nightmare: an eye for a keyhole)."""
    kd, kf, kk = tex.rgb(door), tex.rgb(frame), tex.rgb(knob)

    def fn(ctx):
        u, v = ctx.U * 2 - 1, 1 - ctx.V * 2
        outer = (np.abs(u) <= 0.98) & ((v < 0.5) | (np.hypot(u / 0.98, (v - 0.5) / 0.5) <= 1))
        inner = (np.abs(u) <= 0.78) & ((v < 0.5) | (np.hypot(u / 0.78, (v - 0.5) / 0.4) <= 1)) & (v > -0.95)
        t = tex.tile(ctx, frame, 1, 0.0)
        t[..., :3] = np.where(inner[..., None], kd, kf)
        ix, iy = tex.px(ctx)
        panel = inner & (((np.abs(u) > 0.12) & (np.abs(u) < 0.62)) & (((v > -0.8) & (v < -0.2)) | ((v > 0.0) & (v < 0.55))))
        t[..., :3] = np.where(panel[..., None], kd * 0.82, t[..., :3])
        kn = np.hypot((u - 0.5) * 1.0, (v + 0.08) * 0.5) < 0.12
        t[..., :3] = np.where(kn[..., None], kk, t[..., :3])
        t[..., 4] = np.where(kn, 1.0, 0.0)
        if eye:
            e = (np.abs(v - 0.2) <= (1 - (u / 0.4) ** 2) * 0.08) & (np.abs(u) < 0.4)
            t[..., :3] = np.where(e[..., None], kk, t[..., :3])
            t[..., 4] = np.where(e, 1.0, t[..., 4])
        t[..., 3] = np.where(outer, 1.0, 0.0)
        return tex.grain(ctx, t, 0.03)
    return Mat(fn, f"door{key}{door}{frame}{knob}{eye}", directional=True)


_M = None


def mats():
    """Dream materials, each with its 'nightmare' skin twin."""
    global _M
    if _M:
        return _M
    a = tex.alt
    d = {}
    d["wall"] = a(tex.windowed("#f7f0e2", "#d8b86a", "#ffe3a0", glow=0.95, cols=2, rows=2, arch=True),
                  nightmare=eye_wall("#bdb39e", "#4a2f45", "#d77fae", "nw1"))
    d["wall2"] = a(tex.windowed("#ffe6d2", "#c9a24a", "#fff0b8", glow=0.9, cols=2, rows=1, arch=False),
                   nightmare=eye_wall("#9a97a2", "#3a2440", "#c9a0e0", "nw2", cols=2, rows=1))
    d["wall3"] = a(tex.windowed("#e9f0f8", "#c9a24a", "#ffe8b0", glow=0.9, cols=1, rows=2, arch=True),
                   nightmare=eye_wall("#a99fb0", BURG, "#e0b0c0", "nw3", cols=1, rows=2))
    d["marble"] = a(tex.marble("#f8f2e6", "#e6cdb4", PINK, scale=6),
                    nightmare=tex.marble("#c4baa2", MAUVE, BURG, scale=5))
    d["floor"] = a(tex.plates("#f6ecdc", "#e2c08a", "#fffaf0", cell=(6, 6), glow_line=0.25),
                   nightmare=tex.plates("#4a4468", BURG, "#5e5880", cell=(6, 6), glow_line=0.45))
    d["gold"] = a(tex.metal(GOLD, "#fff4cc", "#a8843e", bands=2.0, glow=0.1),
                  nightmare=tex.metal("#8e8068", "#c9bfa8", "#3e3230", bands=2.0))
    d["gold_glow"] = a(tex.metal("#f3d98f", "#fff8e0", "#c09a4c", bands=2.0, glow=0.55),
                       nightmare=tex.metal("#a06a86", "#e0a8c8", "#3a2440", bands=2.0, glow=0.45))
    d["roof"] = a(tex.porcelain(PINK, "#cf98b0", "#b07a90", crack=0.2, gilt=GOLD),
                  nightmare=tex.porcelain(MAUVE, "#3e2a44", INDIGO, crack=1.2, gilt=BURG))
    d["roof_b"] = a(tex.porcelain(BLUE, "#94b4d8", "#7f9cc0", crack=0.2, gilt=GOLD),
                    nightmare=tex.porcelain(INDIGO, "#181a34", MAUVE, crack=1.2, gilt=GRAY))
    d["roof_p"] = a(tex.porcelain(PEACH, "#e8b48e", "#c99a78", crack=0.2, gilt=GOLD),
                    nightmare=tex.porcelain(BURG, "#401820", "#8b8f9a", crack=1.2, gilt=AGED))
    d["street"] = a(tex.banded(tex.plates(PEACH, "#e0a982", "#fff0e2", cell=(5, 4)), "#ffe9a8", every=9, width=1, glow=0.7,
                               horizontal=False),
                    nightmare=tex.banded(tex.plates("#3a3c62", "#1c1d38", "#50527a", cell=(5, 4)), "#c0507a", every=9, width=1,
                                         glow=0.8, horizontal=False))
    d["under"] = a(tex.stone("#f1e6d6", "#d2bfa6", "#fff6e8", scale=4, cracks=0.12, edge_dark=0.1),
                   nightmare=tex.stone("#55506c", INDIGO, "#76708a", scale=4, cracks=0.5, glow_crack=0.7, crack_color="#d070a8"))
    d["lamp"] = a(tex.glow_flat("#ffd59a", 1.0, core="#fffbe8"), nightmare=tex.glow_flat("#a85a9a", 0.95, core="#ffd0f0"))
    d["cloud"] = a(cloud_mat("#fff4ee", "#f2c6d8", "dncl1"), nightmare=cloud_mat("#5a4a78", "#2a2d52", "dncl1n", glow=0.15))
    d["puff"] = a(cloud_mat("#fffaf4", "#ffd9c0", "dncl2", a=0.85), nightmare=cloud_mat("#6a4a6e", "#24264a", "dncl2n", a=0.85, glow=0.1))
    d["window"] = a(arch_window_mat("#ffd77a", "#c9a24a", "w1"),
                    nightmare=tex.eye_mat(iris="#c45a90", sclera="#efe3cf", pupil="#120c18", lid=BURG, glow=0.95, slit=True,
                                          ring="#ffd0e0"))
    d["door"] = a(door_mat("#bcd6f0", "#c9a24a", "#fff0b0", "d1"), nightmare=door_mat(BURG, "#3a2440", "#ff9ad0", "d1n", eye=True))
    d["moon"] = a(tex.shaped(tex.m_crescent(0.38), "#fff6d0", "#e9cf8a", glow=1.0, key="dncmoon"),
                  nightmare=tex.eye_mat(iris="#ff8ac0", sclera="#efe3cf", pupil="#120c18", lid=MAUVE, glow=1.0, slit=True))
    d["fabric"] = a(tex.fabric(PINK, "#f6efe0", stripe_w=2, fringe=True, glow=0.15),
                    nightmare=tex.fabric(BURG, "#3a2440", stripe_w=2, fringe=True))
    _M = d
    return d


# ====================================================================== district geometry
class District:
    def __init__(self, phase=0.0):
        self.phase = phase
        self.clouds, self.towers, self.roofs, self.windows, self.doors = [], [], [], [], []
        self.streets, self.hangs, self.spiral, self.extras = [], [], [], []
        self.lamps = []
        self.top = (0, 60, 0)   # where folded windows gather


def build_roof(b, kind, x, y, z, w, mat, finial=True):
    M_ = mats()
    if kind == "dome":
        h = y
        b.box((x, h + 1.0, z), (w + 1.0, 2.0, w + 1.0), M_["gold"])           # drum
        h += 2.0
        for f, dh in ((0.96, 2.6), (0.88, 2.6), (0.74, 2.4), (0.55, 2.2), (0.3, 1.8)):
            b.box((x, h + dh / 2, z), (w * f, dh, w * f), mat)
            h += dh
        top = h
    elif kind == "onion":
        h = y
        for f, dh in ((0.9, 1.6), (1.08, 2.4), (1.0, 2.6), (0.72, 2.6), (0.42, 2.4), (0.18, 3.0)):
            b.box((x, h + dh / 2, z), (w * f, dh, w * f), mat, rot=(0, 45, 0))
            h += dh
        top = h
    elif kind == "cone":
        n = 6
        h = y
        for i in range(n):
            ww = (w + 1.6) * (1 - i / n) + 0.8
            b.box((x, h + 1.4, z), (ww, 2.8, ww), mat, rot=(0, 45 * (i % 2), 0), variant=i % 2)
            h += 2.8
        top = h
    else:  # flat crown with merlons
        b.box((x, y + 1.0, z), (w + 1.5, 2.0, w + 1.5), M_["marble"])
        for k in range(4):
            a = math.radians(k * 90 + 45)
            b.box((x + math.cos(a) * w * 0.45, y + 3.0, z + math.sin(a) * w * 0.45), (2.4, 2.0, 2.4), M_["gold"])
        top = y + 2.0
    if finial:
        b.box((x, top + 3.0, z), (1.2, 6.0, 1.2), M_["gold_glow"])
        b.box((x, top + 6.6, z), (2.2, 2.2, 2.2), M_["lamp"], rot=(45, 45, 0))
        top += 8
    return top


def tower(m, d, name, parent, x, z, y0, floors, roof="dome", wall=None, roof_mat=None, balcony=None, ry=0.0,
          pennant=False):
    M_ = mats()
    wall = wall or M_["wall"]
    roof_mat = roof_mat or M_["roof"]
    par, y, chain = parent, y0, []
    rot = (0, ry, 0) if ry else None
    for i, (w, h) in enumerate(floors):
        b = m.bone(f"{name}_{i + 1}", par, pivot=(x, y, z))
        b.box((x, y + h / 2, z), (w, h, w), wall, variant=i % 3, rot=rot)
        b.box((x, y + h - 0.6, z), (w + 1.6, 1.2, w + 1.6), M_["gold"], rot=rot)
        if i == 0:
            b.box((x, y + 0.8, z), (w + 2.4, 1.6, w + 2.4), M_["marble"], rot=rot)
        if balcony == i:
            for k in range(4):
                a = math.radians(k * 90 + ry)
                ox, oz = math.cos(a), math.sin(a)
                ext = w / 2 + 1.3
                long_ = (2.6, 1.0, w + 5) if abs(ox) > 0.5 else (w + 5, 1.0, 2.6)
                b.box((x + ox * ext, y + 1.0, z + oz * ext), long_, M_["marble"])
                rl = (0.6, 1.8, w + 5) if abs(ox) > 0.5 else (w + 5, 1.8, 0.6)
                b.box((x + ox * (ext + 1.0), y + 2.4, z + oz * (ext + 1.0)), rl, M_["gold"])
        chain.append(b.name)
        par = b
        y += h
    rb = m.bone(f"{name}_roof", par, pivot=(x, y, z))
    top = build_roof(rb, roof, x, y, z, floors[-1][0], roof_mat)
    if pennant:
        rb.plane("z", (x + 3.5, top - 1.0, z), 6, 3, M_["fabric"])
    d.towers.append(chain)
    d.roofs.append(rb.name)
    return top


def face_of(x, z, w, face, off=0.35):
    """Point on a tower face. face: 'n' (-Z) 's' 'e' (+X) 'w'. Returns (px, pz, axis, normal)."""
    h = w / 2 + off
    return {"n": (x, z - h, "z", (0, 0, -1)), "s": (x, z + h, "z", (0, 0, 1)),
            "e": (x + h, z, "x", (1, 0, 0)), "w": (x - h, z, "x", (-1, 0, 0))}[face]


def window(m, d, name, parent, center, axis, normal, w=5.0, h=8.0):
    b = m.bone(name, parent, pivot=center)
    b.plane(axis, center, w, h, mats()["window"], variant=len(d.windows) % 2)
    d.windows.append((name, center, axis, normal))
    return b


def door(m, d, name, parent, px, y, pz, axis, w=6.0, h=10.0):
    hinge = (px - w / 2, y, pz) if axis == "z" else (px, y, pz - w / 2)
    b = m.bone(name, parent, pivot=hinge)
    b.plane(axis, (px, y + h / 2, pz), w, h, mats()["door"])
    d.doors.append(name)
    return b


def street(m, d, name, parent, start, yaw, segs, width=9.0, y=4.3):
    """Ribbon street from start along local -Z (rotated by yaw).  Chain of segment bones."""
    M_ = mats()
    sx, sz = start
    base = m.bone(name, parent, pivot=(0, y, 0), rot=(0, yaw, 0))
    par, z, names = base, sz, []
    for i, L in enumerate(segs):
        b = m.bone(f"{name}_{i + 1}", par, pivot=(sx, y, z))
        b.cube((sx - width / 2, y - 0.5, z - L), (width, 1.0, L), M_["street"], variant=i % 2)
        for s in (-1, 1):
            b.cube((sx + s * (width / 2 + 0.3) - 0.5, y - 0.6, z - L), (1.0, 1.5, L), M_["gold"])
        names.append(b.name)
        par = b
        z -= L
    d.streets.append((name, names))
    return names


def hang_stair(m, d, name, parent, start, yaw, n_segs=3, steps=4):
    """Impossible staircase hanging under an island and leading nowhere."""
    M_ = mats()
    sx, sy_, sz = start
    base = m.bone(name, parent, pivot=(0, sy_, 0), rot=(0, yaw, 0))
    par, y, z, names = base, sy_, sz, []
    for s in range(n_segs):
        b = m.bone(f"{name}_{s + 1}", par, pivot=(sx, y, z))
        for i in range(steps):
            b.box((sx, y - 3.2 * i - 0.6, z - 2.6 * i - 1.3), (8.0, 1.2, 3.0), M_["marble"], variant=i % 2)
            b.box((sx + 4.4, y - 3.2 * i + 1.0, z - 2.6 * i - 1.3), (0.6, 3.0, 0.6), M_["gold"])
        b.box((sx - 4.4, y - 3.2 * steps / 2 + 0.4, z - 2.6 * steps / 2), (0.8, 0.8, 13.0), M_["gold"],
              rot=(-51, 0, 0))
        names.append(b.name)
        par = b
        y -= 3.2 * steps
        z -= 2.6 * steps
    # a little door to nowhere at the end of the flight
    b.box((sx, y - 1.0, z - 1.0), (9.0, 1.2, 4.0), M_["marble"])
    b.plane("z", (sx, y + 4.6, z - 1.6), 5.0, 9.0, M_["door"])
    d.hangs.append((name, names))
    return names


def clouds(m, d, parent, radius, n_puffs, y=-1.5, lower=True, seed=0):
    M_ = mats()
    c1 = m.bone("cloud_1", parent)
    c1.plane("y", (0, y, 0), radius * 2.4, radius * 2.4, M_["cloud"])
    for k in range(n_puffs):
        a = math.radians(k * 360 / n_puffs + seed * 17)
        r = radius * (0.92 + 0.12 * ((k * 7 + seed) % 3))
        c1.box((r * math.cos(a), y - 1.5 + (k % 2) * 1.5, r * math.sin(a)), (radius * 0.6, 8 + (k % 3) * 2, radius * 0.45),
               M_["puff"], rot=(0, -math.degrees(a), 0), variant=k % 3)
    d.clouds.append("cloud_1")
    if lower:
        c2 = m.bone("cloud_2", parent)
        c2.plane("y", (0, y - 16, 0), radius * 3.0, radius * 3.0, M_["cloud"], variant=1)
        for k in range(n_puffs - 2):
            a = math.radians(k * 360 / (n_puffs - 2) + 30 + seed * 11)
            r = radius * 1.25
            c2.box((r * math.cos(a), y - 15, r * math.sin(a)), (radius * 0.5, 7, radius * 0.4), M_["puff"],
                   rot=(0, -math.degrees(a), 0), variant=(k + 1) % 3)
        d.clouds.append("cloud_2")


def lamps(m, d, parent, pts):
    M_ = mats()
    b = m.bone("lamps", parent)
    for (x, y, z) in pts:
        b.box((x, y + 3.5, z), (1.0, 7.0, 1.0), M_["gold"])
        b.box((x, y + 7.8, z), (2.6, 2.6, 2.6), M_["lamp"], rot=(0, 45, 0))
    d.lamps.append("lamps")


def build_spire():
    M_ = mats()
    m = Model("dn_city_spire", density=1.0, bounds=(34, 36, (0, 2, 0)), alts=("nightmare",))
    d = District(0.0)
    root = m.bone("root")
    fl = m.bone("float", root)
    clouds(m, d, fl, 44, 9)
    # plaza: octagram of two squares with gilt rims and a marble floor
    pl = m.bone("plaza", fl)
    for rot_ in (0, 45):
        pl.box((0, 2, 0), (68, 4, 68), M_["under"], rot=(0, rot_, 0) if rot_ else None, mats={"up": M_["floor"]})
        for s in (-1, 1):
            pl.box((0, 4.2, s * 34), (68, 1.0, 1.0), M_["gold_glow"], rot=(0, rot_, 0), pivot=(0, 4.2, 0))
            pl.box((s * 34, 4.2, 0), (1.0, 1.0, 68), M_["gold_glow"], rot=(0, rot_, 0), pivot=(0, 4.2, 0))
    pl.plane("y", (0, 4.15, 0), 30, 30, tex.alt(tex.magic_circle(list(glyphs.DREAM.values()),
                                                                  "#fff3d8", "#e9cf8a", bands=((0.78, 0.95, 14),), lines=(0.74, 0.98), star=8,
                                                                  star_r=(0.2, 0.7), key="dncplazac"),
                                                 nightmare=tex.magic_circle(list(glyphs.DREAM.values()),
                                                                            "#ff9ad0", MAUVE, bands=((0.78, 0.95, 14),), lines=(0.74, 0.98),
                                                                            star=7, star_r=(0.2, 0.7), key="dncplazacn")),
             faces=("up",))
    # keel: the inverted city hanging beneath the island
    kl = m.bone("keel", fl, pivot=(0, 0, 0))
    h = 0
    for i, (w, dh) in enumerate(((58, 7), (46, 8), (34, 9), (22, 11), (12, 12), (5, 10))):
        kl.box((0, h - dh / 2, 0), (w, dh, w), M_["under"] if i < 5 else M_["gold"], rot=(0, 45 * (i % 2), 0), variant=i % 3)
        h -= dh
    kl.box((0, h - 2.5, 0), (5, 5, 5), M_["lamp"], rot=(45, 45, 0))
    for k in range(4):
        a = math.radians(k * 90 + 45)
        x, z = 21 * math.cos(a), 21 * math.sin(a)
        kl.box((x, -8, z), (7, 14, 7), M_["wall3"], variant=k % 2)
        hh = -15
        for j, ww in enumerate((8.5, 6.5, 4.5, 2.5)):
            kl.box((x, hh - 1.4, z), (ww, 2.8, ww), M_["roof_b"], rot=(0, 45 * (j % 2), 0))
            hh -= 2.8
        kl.box((x, hh - 1.5, z), (2.2, 2.2, 2.2), M_["lamp"], rot=(45, 45, 0))
    # central spire
    top = tower(m, d, "tw1", fl, 0, 0, 4, [(22, 14), (20, 12), (18, 12), (18, 12), (15, 11), (13, 10)], roof="dome",
                roof_mat=M_["gold"], balcony=2)
    mb = m.bone("moon", "tw1_roof", pivot=(0, top + 4, 0))
    mb.plane("z", (0, top + 4, 0), 10, 10, M_["moon"])
    # four turrets at the cardinal points
    for k, (x, z, roof, floors, rm) in enumerate((
            (30, 0, "cone", [(10, 12), (9, 11), (8, 10)], M_["roof"]),
            (0, 30, "onion", [(11, 11), (10, 10)], M_["roof_b"]),
            (-30, 0, "cone", [(10, 13), (9, 12), (8, 10), (7, 8)], M_["roof_p"]),
            (0, -30, "dome", [(11, 12), (10, 10)], M_["roof"]))):
        tower(m, d, f"tw{k + 2}", fl, x, z, 4, floors, roof=roof, roof_mat=rm, wall=M_["wall3"] if k % 2 else M_["wall"],
              ry=0, pennant=(k % 2 == 0))
    # hero windows on the central tower (they slide, wander and become eyes)
    for k, (face, y, w) in enumerate((("n", 36, 18), ("e", 36, 18), ("s", 36, 18), ("w", 36, 18),
                                      ("n", 59, 15), ("e", 59, 15), ("s", 59, 15), ("w", 59, 15))):
        px, pz, ax, nrm = face_of(0, 0, w, face, 0.5)
        window(m, d, f"win_{k + 1}", fl, (px, y, pz), ax, nrm, 5.0, 8.0)
    for k, face in enumerate("nesw"):
        px, pz, ax, _ = face_of(0, 0, 22, face, 1.35)
        door(m, d, f"door_{k + 1}", fl, px, 5.6, pz, ax, 6.0, 10.0)
    # dream streets along the diagonals
    for k in range(4):
        street(m, d, f"st{k + 1}", fl, (0, -13), 45 + 90 * k, [12, 12, 14])
    # impossible spiral stair climbing past the dome into nothing, ending in a door
    for g in range(4):
        sb = m.bone(f"spiral_{g + 1}", fl, pivot=(0, 4, 0))
        d.spiral.append(sb.name)
        for i in range(5):
            n = g * 5 + i
            a = math.radians(n * 27 + 10)
            r = 17.0
            y = 7 + n * 3.9
            p = (r * math.cos(a), y, r * math.sin(a))
            sb.box(p, (7.0, 1.3, 4.6), M_["marble"], rot=(0, -math.degrees(a), 0),
                   pivot=p, variant=n % 3)
            if i % 2 == 0:
                q = ((r + 3.4) * math.cos(a), y + 2.2, (r + 3.4) * math.sin(a))
                sb.box(q, (0.6, 3.2, 0.6), M_["gold"])
        if g == 3:
            a = math.radians(19 * 27 + 10)
            p = (17 * math.cos(a), 7 + 19 * 3.9 + 1, 17 * math.sin(a))
            sb.box((p[0], p[1] + 5.5, p[2]), (1.0, 11, 1.0), M_["gold_glow"], rot=(0, -math.degrees(a), 0),
                   pivot=p)
            sb.plane("x", (p[0], p[1] + 5.0, p[2]), 5, 9, M_["door"], rot=(0, -math.degrees(a), 0), pivot=p)
    for k in range(2):
        hang_stair(m, d, f"hang{k + 1}", fl, (0, 0, -30), 110 + 180 * k, 3, 4)
    lamps(m, d, fl, [(40 * math.cos(math.radians(a)), 4, 40 * math.sin(math.radians(a))) for a in range(0, 360, 45)])
    d.top = (0, 50, 0)
    return m, d


def house(b, x, y, z, w, dp, h, wall, roof_mat, face_x=1):
    M_ = mats()
    b.box((x, y + h / 2, z), (w, h, dp), wall)
    b.box((x, y + h - 0.5, z), (w + 1.0, 1.0, dp + 1.0), M_["gold"])
    s = w / 2 + 1.0
    pitch = 38
    L = s / math.cos(math.radians(pitch)) + 0.8
    hg = s * math.tan(math.radians(pitch))
    for sx in (-1, 1):
        b.box((x + sx * s / 2, y + h + hg / 2 + 0.3, z), (L, 1.2, dp + 2.0), roof_mat, rot=(0, 0, -sx * pitch))
    for i in range(3):
        f = (i + 0.5) / 3
        b.box((x, y + h + (i + 0.5) * hg / 3, z), (max(1.0, w * (1 - f)), hg / 3, dp - 0.4), wall, variant=1)
    b.box((x, y + h + hg + 0.6, z), (1.2, 1.2, dp + 2.4), M_["gold_glow"])
    b.box((x - face_x * w / 4, y + h + hg * 0.5 + 3, z + dp / 4), (2.4, 6.0, 2.4), M_["under"])


def build_quarter(variant):
    """variant 'a' or 'b': same skeleton, different architecture."""
    M_ = mats()
    mx = 1 if variant == "a" else -1
    m = Model(f"dn_city_quarter_{variant}", density=1.0, bounds=(28, 30, (0, 2, 0)), alts=("nightmare",))
    d = District(0.37 if variant == "a" else 0.71)
    root = m.bone("root")
    fl = m.bone("float", root)
    clouds(m, d, fl, R_ISLAND, 8, seed=3 if variant == "a" else 7)
    pl = m.bone("plaza", fl)
    for i, r_ in enumerate((0, 30, 60)):
        pl.box((0, 2, 0), (58 - i * 2, 4, 58 - i * 2), M_["under"], rot=(0, r_, 0) if r_ else None, mats={"up": M_["floor"]},
               variant=i)
    kl = m.bone("keel", fl, pivot=(0, 0, 0))
    h = 0
    for i, (w, dh) in enumerate(((44, 7), (32, 8), (20, 10), (9, 10))):
        kl.box((0, h - dh / 2, 0), (w, dh, w), M_["under"], rot=(0, 30 * i, 0), variant=i % 3)
        h -= dh
    kl.box((0, h - 2.5, 0), (4, 4, 4), M_["lamp"], rot=(45, 45, 0))
    for (x, z, L) in ((-10 * mx, 8, 26), (13 * mx, -6, 20)):
        kl.box((x, -L / 2 - 2, z), (7, L, 7), M_["wall3"])
        hh = -L - 2
        for j, ww in enumerate((8, 6, 4, 2)):
            kl.box((x, hh - 1.3, z), (ww, 2.6, ww), M_["roof_b"], rot=(0, 45 * (j % 2), 0))
            hh -= 2.6
        kl.box((x, hh - 1.3, z), (2, 2, 2), M_["lamp"], rot=(45, 45, 0))
    if variant == "a":
        specs = [(12, 12, "dome", [(14, 12), (13, 12), (12, 11), (11, 10), (9, 9)], M_["gold"], 3),
                 (-15, 14, "cone", [(11, 11), (10, 10), (9, 9)], M_["roof"], None),
                 (15, -16, "cone", [(10, 10), (9, 9), (8, 9), (7, 8)], M_["roof_b"], None)]
    else:
        specs = [(-12, 12, "onion", [(15, 11), (14, 11), (12, 10), (11, 10)], M_["roof_p"], 2),
                 (16, 13, "flat", [(12, 12), (11, 11), (10, 10)], M_["roof"], None),
                 (-15, -15, "dome", [(10, 11), (9, 10), (8, 10), (7, 9), (6, 8)], M_["roof_b"], None)]
    tops = []
    for k, (x, z, roof, floors, rm, bal) in enumerate(specs):
        tops.append(tower(m, d, f"tw{k + 1}", fl, x, z, 4, floors, roof=roof, roof_mat=rm, balcony=bal,
                          wall=[M_["wall"], M_["wall2"], M_["wall3"]][k], pennant=(k == 1)))
    # houses + gate (one bone each: they lean and stretch together)
    hb = m.bone("houses", fl, pivot=(0, 4, 0))
    hx = -15 * mx
    house(hb, hx, 4, -17, 11, 10, 10, M_["wall2"], M_["roof"], face_x=mx)
    house(hb, hx - 1 * mx, 4, -3, 9, 9, 8, M_["wall3"], M_["roof_b"], face_x=mx)
    house(hb, 25 * mx, 4, -2, 8, 10, 9, M_["wall2"], M_["roof_p"], face_x=-mx)
    gb = m.bone("gate", fl, pivot=(0, 4, -30))
    for s in (-1, 1):
        gb.box((s * 7, 4 + 9, -30), (3, 18, 3), M_["marble"])
        gb.box((s * 7, 4 + 18.6, -30), (4, 1.2, 4), M_["gold"])
    gb.box((0, 4 + 20.5, -30), (18, 3, 3.4), M_["marble"])
    gb.box((0, 4 + 23.5, -30), (8, 3, 3), M_["roof"], rot=(0, 0, 45))
    gb.plane("z", (0, 4 + 22, -31.9), 6, 6, M_["moon"])
    d.extras += ["houses", "gate"]
    # windows / doors
    x1, z1 = specs[0][0], specs[0][1]
    f1 = specs[0][3]
    y_of = lambda fl_, i: 4 + sum(h_ for _, h_ in fl_[:i]) + fl_[i][1] / 2
    wins = [(x1, z1, f1, 1, "n"), (x1, z1, f1, 1, "w" if mx > 0 else "e"), (x1, z1, f1, 2, "s"), (x1, z1, f1, 2, "e" if mx > 0 else "w"),
            (specs[2][0], specs[2][1], specs[2][3], 1, "n"), (specs[1][0], specs[1][1], specs[1][3], 1, "n")]
    for k, (x, z, fls, i, face) in enumerate(wins):
        px, pz, ax, nrm = face_of(x, z, fls[i][0], face, 0.5)
        window(m, d, f"win_{k + 1}", fl, (px, y_of(fls, i), pz), ax, nrm, 4.0, 6.5)
    px, pz, ax, _ = face_of(x1, z1, f1[0][0], "n", 1.35)
    door(m, d, "door_1", fl, px, 5.6, pz, ax, 5.0, 8.0)
    door(m, d, "door_2", fl, hx + mx * 5.6, 4.0, -17, "x", 4.0, 7.0)
    door(m, d, "door_3", fl, hx + mx * 3.6, 4.0, -3, "x", 4.0, 6.5)
    street(m, d, "st1", fl, (0, 20), 0, [16, 16, 16, 14], width=9.0)
    hang_stair(m, d, "hang1", fl, (0, 0, -22), 180 + 25 * mx, 3, 4)
    hang_stair(m, d, "hang2", fl, (0, 0, -22), 90 * mx, 2, 4)
    lamps(m, d, fl, [(s * 6.8, 4, z) for s in (-1, 1) for z in (-22, -6, 12)])
    d.top = (0, 44, 0)
    return m, d


# ====================================================================== district animations
def _scale_val(v, f, ch):
    if ch == "scl":
        return tuple(1 + (c - 1) * f for c in v)
    return tuple(c * f for c in v)


def night_pose(d, kind):
    """Bone -> {'rot'|'pos'|'scl': (x, y, z)} for the nightmare form."""
    P = {}
    for j, chain in enumerate(d.towers):
        sgn = 1 if j % 2 == 0 else -1
        for i, b in enumerate(chain):
            P[b] = {"rot": (0, sgn * (8 + 3 * i), sgn * (2.5 if i else 0) * (1 if j < 2 else -1)),
                    "scl": (0.95, 1.07 + 0.015 * i, 0.95)}
    for k, r in enumerate(d.roofs):
        P[r] = {"rot": (8 * (1 if k % 2 else -1), 0, 6), "scl": (0.8, 1.7, 0.8)}
    cx, cy, cz = d.top
    for k, (b, (x, y, z), ax, nrm) in enumerate(d.windows):
        # windows leave the walls and gather in two clusters of floating eyes
        side = 1 if k % 2 == 0 else -1
        a = math.radians(k * 47 + 20)
        tx = cx + side * 26 + 6 * math.cos(a)
        ty = cy + 6 * math.sin(a) + (k // 2) * 2
        tz = cz - 20 + 5 * math.sin(a * 1.7)
        P[b] = {"pos": (tx - x, ty - y, tz - z), "rot": (0, 0, 12 * side), "scl": (1.35, 1.35, 1.35)}
    for b in d.doors:
        P[b] = {"scl": (0.9, 2.6, 1.0), "rot": (0, 18, 0)}
    for base, segs in d.streets:
        P[base] = {"rot": (0, 25, 0)}
        for s, b in enumerate(segs):
            P[b] = {"rot": (14 + 12 * s, 0, 6 * (-1) ** s)}
    for base, segs in d.hangs:
        P[base] = {"pos": (0, -16, 0)}
        for s, b in enumerate(segs):
            P[b] = {"rot": (18, 28 * (s + 1), 0), "scl": (1, 1.3, 1.3)}
    for b in d.spiral:
        P[b] = {"scl": (1.0, 1.45, 1.0), "rot": (0, 40, 0)}
    for c in d.clouds:
        P[c] = {"scl": (1.18, 1.9, 1.18)}
    P["plaza"] = {"rot": (4, 0, -3)}
    P["keel"] = {"scl": (0.8, 1.7, 0.8), "rot": (0, 30, 0)}
    for b in d.lamps:
        P[b] = {"scl": (0.85, 1.3, 0.85)}
    for k, b in enumerate(d.extras):
        P[b] = {"rot": (0, 0, 7 * (-1) ** k), "scl": (1.0, 1.35, 1.0)}
    if "moon" in kind:
        P["moon"] = {"scl": (1.6, 1.6, 1.6)}
    return P


def district_anims(d, has_moon=False):
    A = []
    ph = d.phase
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    drift = Anim("drift", loop=True)
    drift.pos("float", (0, LIFE(1.4, 7.0, ph), 0))
    drift.rot("float", (LIFE(1.0, 9.0, ph), 0, LIFE(0.8, 11.0, ph + 0.3)))
    for i, c in enumerate(d.clouds):
        drift.rot(c, (0, spin(5 + 4 * i) * (1 if i % 2 == 0 else -1), 0))
    A.append(drift)

    # ---------------- Phase I: assembly
    asm = Anim("assemble", length=T_ASM, loop="hold")
    asm.pos("root", {0: (0, -14, 0), 2.2: (0, 1.5, 0), 3.2: (0, 0, 0)})
    for i, c in enumerate(d.clouds):
        asm.pos(c, {0: (-90 + 30 * i, -6, 40 - 20 * i), 1.5 + 0.2 * i: (0, 0, 0)})
        asm.scl(c, {0: (0.25, 0.4, 0.25), 1.0: (0.8, 0.9, 0.8), 1.6 + 0.2 * i: (1, 1, 1)})
    asm.scl("plaza", {0: 0.0, 0.8: 0.0, 1.4: (1.06, 1.0, 1.06), 1.7: 1.0})
    asm.scl("keel", {0: (0.3, 0.0, 0.3), 1.0: (0.3, 0.0, 0.3), 1.9: (1.05, 1.08, 1.05), 2.2: 1.0})
    for k, (base, segs) in enumerate(d.streets):
        for s, b in enumerate(segs):
            t0 = 1.6 + 0.2 * s + 0.1 * k
            asm.scl(b, {0: (1, 1, 0), t0: (1, 1, 0), t0 + 0.32: (1, 1, 1.06), t0 + 0.42: (1, 1, 1)})
    last = 0
    for j, chain in enumerate(d.towers):
        for i, b in enumerate(chain):
            t0 = 1.8 + 0.14 * j + 0.3 * i
            asm.scl(b, {0: (1, 0, 1), t0: (1, 0, 1), t0 + 0.28: (1, 1.1, 1), t0 + 0.4: (1, 1, 1)})
            last = max(last, t0 + 0.4)
        tr = 1.8 + 0.14 * j + 0.3 * len(chain)
        asm.scl(d.roofs[j], {0: 0.0, tr: 0.0, tr + 0.22: 1.2, tr + 0.36: 1.0})
    for k, b in enumerate(d.extras):
        t0 = 2.2 + 0.3 * k
        asm.scl(b, {0: (1, 0, 1), t0: (1, 0, 1), t0 + 0.35: (1, 1.1, 1), t0 + 0.5: 1.0})
    for k, b in enumerate(d.doors):
        t0 = 2.6 + 0.12 * k
        asm.scl(b, {0: (1, 0, 1), t0: (1, 0, 1), t0 + 0.25: 1.0})
    for k, b in enumerate(d.spiral):
        t0 = 3.0 + 0.28 * k
        asm.scl(b, {0: 0.0, t0: 0.0, t0 + 0.25: 1.08, t0 + 0.35: 1.0})
    for k, (base, segs) in enumerate(d.hangs):
        for s, b in enumerate(segs):
            t0 = 2.4 + 0.3 * s + 0.15 * k
            asm.scl(b, {0: (1, 0, 0), t0: (1, 0, 0), t0 + 0.3: (1, 1.08, 1.08), t0 + 0.4: 1.0})
    for k, (b, *_r) in enumerate(d.windows):     # windows light in a wave
        t0 = 3.7 + 0.11 * k
        asm.scl(b, {0: 0.0, t0: 0.0, t0 + 0.18: 1.35, t0 + 0.3: 1.0})
    for b in d.lamps:
        asm.scl(b, {0: 0.0, 4.2: 0.0, 4.45: (1.2, 1.2, 1.2), 4.6: 1.0})
    if has_moon:
        asm.scl("moon", {0: 0.0, 4.3: 0.0, 4.6: 1.4, 4.8: 1.0})
        asm.rot("moon", {0: (0, -180, 0), 4.3: (0, -180, 0), 4.8: (0, 0, 0)})
    A.append(asm)

    dream = Anim("dream", loop=True)
    for k, (b, *_r) in enumerate(d.windows):
        dream.scl(b, LIFE(0.06, 2.3, k * 0.17, base=1.0))
    for b in d.lamps:
        dream.scl(b, (1, LIFE(0.04, 1.7, 0, base=1.0), 1))
    if has_moon:
        dream.rot("moon", (0, LIFE(18, 8.0), LIFE(6, 5.0)))
    A.append(dream)

    # ---------------- Phase II: the streets begin to move
    liv = Anim("living", length=T_LIV, loop=True)
    for k, (base, segs) in enumerate(d.streets):
        liv.rot(base, (0, S(22, T_LIV, k * 0.25), 0))
        for s, b in enumerate(segs):
            liv.rot(b, (S(7, T_LIV / 2, k * 0.2 + s * 0.12), 0, S(4, T_LIV / 2, s * 0.2)))
    for k, (b, c, ax, nrm) in enumerate(d.windows):
        sl = S(3.5, T_LIV, k * 0.13)
        liv.pos(b, (sl, S(3.0, T_LIV / 2, k * 0.21), 0) if ax == "z" else (0, S(3.0, T_LIV / 2, k * 0.21), sl))
    for k, (base, segs) in enumerate(d.hangs):
        liv.pos(base, {0: (0, 0, 0), 1.4: (0, -12, 0), 4.4: (0, -12, 0), T_LIV: (0, 0, 0)})
        for s, b in enumerate(segs):
            liv.rot(b, {0: (0, 0, 0), 1.4 + 0.2 * s: (-14, 0, 0), 4.4: (-14, 0, 0), T_LIV: (0, 0, 0)})
    for j, chain in enumerate(d.towers):
        for i, b in enumerate(chain):
            if i % 2 == 1:
                liv.rot(b, (0, S(14 * (1 if j % 2 else -1), T_LIV, i * 0.1 + j * 0.2), 0))
    for k, r in enumerate(d.roofs):
        if k > 0:
            liv.rot(r, (0, S(30, T_LIV, k * 0.3), 0))
    for k, b in enumerate(d.doors):
        liv.rot(b, (0, S(38, T_LIV / 2, k * 0.2, base=-30), 0))
    for b in d.spiral:
        liv.rot(b, (0, M("q.anim_time*60", lambda t: t * 60), 0))
    for k, b in enumerate(d.extras):
        liv.pos(b, (0, S(1.6, T_LIV / 2, k * 0.3), 0))
    A.append(liv)

    # ---------------- Phase III: the nightmare under the facade
    P = night_pose(d, "moon" if has_moon else "")
    warp = Anim("warp", length=T_WARP, loop="hold")
    fs = {0: 0.0, 0.3: 0.18, 0.55: -0.08, 0.95: 0.62, 1.4: 1.12, T_WARP: 1.0}
    for b, chs in P.items():
        for ch, v in chs.items():
            keys = {t: _scale_val(v, f, ch) for t, f in fs.items()}
            getattr(warp, ch)(b, keys)
    A.append(warp)

    night = Anim("nightmare", length=T_NIGHT, loop=True)
    for b, chs in P.items():
        for ch, v in chs.items():
            getattr(night, ch)(b, tuple(v))
    for j, chain in enumerate(d.towers):        # towers breathe and writhe
        for i, b in enumerate(chain):
            r = P[b]["rot"]
            s_ = P[b]["scl"]
            night.rot(b, (r[0], LIFE(2.5 + i * 0.6, T_NIGHT, j * 0.21 + i * 0.07, base=r[1]), r[2]))
            if i == 0:
                night.scl(b, (s_[0], LIFE(0.035, T_NIGHT / 2, j * 0.3, base=s_[1]), s_[2]))
    for k, (b, *_r) in enumerate(d.windows):    # eyes drift and stare
        p = P[b]["pos"]
        night.pos(b, (LIFE(1.6, 3.3, k * 0.19, base=p[0]), LIFE(1.4, 2.7, k * 0.31, base=p[1]), p[2]))
        night.rot(b, (LIFE(8, 2.9, k * 0.2), LIFE(14, 3.7, k * 0.13), P[b]["rot"][2]))
    for k, b in enumerate(d.doors):             # elongated doors keep creaking
        night.rot(b, (0, LIFE(16, 3.1, k * 0.25, base=18), 0))
    for k, (base, segs) in enumerate(d.streets):
        for s, b in enumerate(segs):
            r = P[b]["rot"]
            night.rot(b, (LIFE(7, 2.6, k * 0.2 + s * 0.15, base=r[0]), 0, r[2]))
    A.append(night)

    # ---------------- Phase IV: the sleeping collapse
    col = Anim("collapse", length=T_COL, loop="hold")
    cx, cy, cz = d.top
    for b, chs in P.items():   # start exactly from the nightmare pose
        for ch, v in chs.items():
            getattr(col, ch)(b, {0: tuple(v), T_COL: tuple(v)})
    for k, (base, segs) in enumerate(d.streets):
        for s, b in enumerate(segs):
            r = P[b]["rot"]
            t0 = 0.2 + 0.12 * (len(segs) - s) + 0.08 * k
            col.rot(b, {0: r, t0: r, t0 + 0.6: (150, 0, r[2])})
            col.scl(b, {0: 1.0, t0 + 0.4: 1.0, t0 + 0.8: 0.0})
    for k, (b, (x, y, z), ax, nrm) in enumerate(d.windows):
        p, sc = P[b]["pos"], P[b]["scl"]
        t0 = 0.3 + 0.07 * k
        col.pos(b, {0: p, t0: p, t0 + 0.6: (cx - x, cy - y, cz - z)})
        col.scl(b, {0: sc, t0 + 0.3: sc, t0 + 0.7: 0.0})
    for j, chain in enumerate(d.towers):
        n = len(chain)
        for i, b in enumerate(chain):
            r, s_ = P[b]["rot"], P[b]["scl"]
            t0 = 0.6 + 0.16 * (n - 1 - i) + 0.1 * j
            col.scl(b, {0: s_, t0: s_, t0 + 0.35: (s_[0] * 0.8, 0.05, s_[2] * 0.8)})
            col.rot(b, {0: r, t0: r, t0 + 0.35: (r[0], r[1] + 60, r[2])})
    for k, r in enumerate(d.roofs):
        s_ = P[r]["scl"]
        col.scl(r, {0: s_, 0.4 + 0.05 * k: s_, 0.75 + 0.05 * k: 0.0})
    for b in d.doors:
        col.scl(b, {0: P[b]["scl"], 0.25: P[b]["scl"], 0.5: (0.9, 0.0, 1.0)})
    for base, segs in d.hangs:
        col.pos(base, {0: P[base]["pos"], 0.5: (0, 0, 0)})
        col.scl(base, {0: 1.0, 0.5: 1.0, 0.9: 0.0})
    for b in d.spiral:
        col.scl(b, {0: P[b]["scl"], 0.4: P[b]["scl"], 0.8: 0.0})
    for b in d.lamps:
        col.scl(b, {0: P[b]["scl"], 0.3: 0.0})
    for b in d.extras:
        col.scl(b, {0: P[b]["scl"], 0.9: P[b]["scl"], 1.3: (1.0, 0.0, 1.0)})
    col.scl("keel", {0: P["keel"]["scl"], 1.2: P["keel"]["scl"], 1.7: (0.6, 0.0, 0.6)})
    col.scl("plaza", {0: 1.0, 1.7: 1.0, 2.2: (0.3, 2.0, 0.3), 2.5: 0.0})
    for c in d.clouds:
        col.scl(c, {0: P[c]["scl"], 1.8: (0.7, 1.2, 0.7), 2.6: 0.0})
    if has_moon:
        col.scl("moon", {0: P["moon"]["scl"], 1.0: (2.2, 2.2, 2.2), 1.3: 0.0})
    col.rot("root", {0: (0, 0, 0), 1.4: (0, 90, 0), 2.3: (0, 330, 0), T_COL: (0, 720, 0)})
    col.scl("root", {0: 1.0, 1.6: 0.92, 2.3: 0.45, 2.8: 0.08, T_COL: 0.0})
    A.append(col)
    return A


# ====================================================================== the ring (bridges + ring road)
def build_ring():
    M_ = mats()
    m = Model("dn_city_ring", density=1.0, bounds=(44, 12, (0, 0, 0)), alts=("nightmare",))
    root = m.bone("root")
    fl = m.bone("float", root)
    bridges, arcs = [], []
    # bridges along the diagonals: spire edge -> quarter front edge, 4 hinged leaves each
    L = (R_QUARTER - R_ISLAND - R_SPIRE_EDGE + 2) / 4
    for k in range(4):
        base = m.bone(f"br{k + 1}", fl, pivot=(0, 4, 0), rot=(0, 45 + 90 * k, 0))
        par, z, segs = base, -R_SPIRE_EDGE + 1, []
        for s in range(4):
            b = m.bone(f"br{k + 1}_{s + 1}", par, pivot=(0, 4, z))
            b.cube((-4.5, 3.0, z - L), (9, 1.4, L), M_["street"], variant=s % 2)
            for sx in (-1, 1):
                b.cube((sx * 4.4 - 0.4, 4.4, z - L), (0.8, 2.4, L), M_["gold"])
            b.box((0, 1.6, z - L / 2), (6.5, 1.6, L - 1.0), M_["under"], variant=s % 3)
            b.box((0, -0.6, z - L / 2), (2.6, 3.0, 2.6), M_["marble"], rot=(0, 45, 0))
            if s % 2 == 0:
                b.box((4.4, 7.4, z - 0.6), (0.7, 5.0, 0.7), M_["gold"])
                b.box((4.4, 10.4, z - 0.6), (2.0, 2.0, 2.0), M_["lamp"], rot=(0, 45, 0))
            else:
                b.box((0, -3.4, z - L / 2), (1.6, 1.6, 1.6), M_["lamp"], rot=(45, 45, 0))
                for sx in (-1, 1):   # a dream archway over the middle of the bridge
                    b.box((sx * 4.4, 9.0, z - L / 2), (1.2, 9.0, 1.2), M_["marble"])
                b.box((0, 14.0, z - L / 2), (10.0, 1.6, 1.6), M_["gold_glow"])
                b.box((0, 15.8, z - L / 2), (3.0, 3.0, 1.0), M_["roof"], rot=(0, 0, 45))
            segs.append(b.name)
            par = b
            z -= L
        bridges.append((base.name, segs))
    # ring road arcs between the quarters (cardinal directions), 4 segments each
    R = R_QUARTER
    for k in range(4):
        base = m.bone(f"arc{k + 1}", fl, pivot=(0, 4, 0))
        segs = []
        c0 = k * 90
        for s in range(4):
            a = c0 - 27 + 13.5 * (s + 0.5)
            ar = math.radians(a)
            p = (R * math.cos(ar), 4.0, R * math.sin(ar))
            b = m.bone(f"arc{k + 1}_{s + 1}", base, pivot=p)
            tl = R * math.radians(13.5) + 0.6
            b.box((p[0], 3.6, p[2]), (10, 1.4, tl), M_["street"], rot=(0, -a, 0), pivot=(p[0], 3.6, p[2]), variant=s % 2)
            for sr in (-1, 1):
                q = ((R + sr * 5.2) * math.cos(ar), 5.0, (R + sr * 5.2) * math.sin(ar))
                b.box(q, (0.8, 2.4, tl), M_["gold"], rot=(0, -a, 0), pivot=q)
            q = (R * math.cos(ar), 1.6, R * math.sin(ar))
            b.box(q, (6, 2.2, tl - 2), M_["under"], rot=(0, -a, 0), pivot=q, variant=s % 3)
            q = ((R + 5.2) * math.cos(ar), 8.4, (R + 5.2) * math.sin(ar))
            b.box(q, (0.7, 5.0, 0.7), M_["gold"])
            b.box((q[0], 11.2, q[2]), (2.0, 2.0, 2.0), M_["lamp"], rot=(0, 45, 0))
            if s == 1:   # floating archway where the road is re-routed
                for sr in (-1, 1):
                    q = ((R + sr * 5.0) * math.cos(ar), 12.0, (R + sr * 5.0) * math.sin(ar))
                    b.box(q, (1.4, 16.0, 1.4), M_["marble"])
                q = (R * math.cos(ar), 20.5, R * math.sin(ar))
                b.box(q, (12.0, 2.0, 2.0), M_["gold_glow"], rot=(0, -a, 0), pivot=q)
                b.plane("x", (q[0], q[1] + 3.2, q[2]), 4.0, 4.0, M_["moon"], rot=(0, -a, 0), pivot=q)
            segs.append(b.name)
        arcs.append((base.name, segs))
    return m, bridges, arcs


def ring_anims(bridges, arcs):
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    drift = Anim("drift", loop=True)
    drift.pos("float", (0, LIFE(1.0, 7.0, 0.5), 0))
    A.append(drift)

    asm = Anim("assemble", length=T_ASM, loop="hold")
    for k, (base, segs) in enumerate(bridges):
        for s, b in enumerate(segs):
            t0 = 0.4 + 0.38 * s + 0.12 * k
            f = 165 if s % 2 == 0 else -165
            asm.rot(b, {0: (f, 0, 0), t0: (f, 0, 0), t0 + 0.32: (-8 if s % 2 == 0 else 8, 0, 0), t0 + 0.45: (0, 0, 0)})
            asm.scl(b, {0: 0.0, t0 - 0.02: 0.0, t0: 1.0})
    for k, (base, segs) in enumerate(arcs):
        asm.rot(base, {0: (0, -50, 0), 1.6: (0, -50, 0), 3.4: (0, 0, 0)})
        for s, b in enumerate(segs):
            t0 = 1.7 + 0.3 * s + 0.1 * k
            asm.scl(b, {0: 0.0, t0: 0.0, t0 + 0.3: (1.1, 1.1, 1.1), t0 + 0.42: 1.0})
    A.append(asm)
    A.append(Anim("dream", loop=True))

    liv = Anim("living", length=T_LIV, loop=True)
    for k, (base, segs) in enumerate(bridges):     # drawbridge-like folding, alternate pairs
        off = 0.0 if k % 2 == 0 else T_LIV / 2
        for s, b in enumerate(segs):
            f = (60 + 25 * s) * (1 if s % 2 == 0 else -1)
            keys = {0.0: (0, 0, 0), T_LIV: (0, 0, 0)}
            for t, v in ((0.05, 0), (0.9, 0.4), (1.6, 1.0), (2.2, 1.0), (2.95, 0)):
                keys[t + off] = (f * v, 0, 0)
            liv.rot(b, dict(sorted(keys.items())))
    for k, (base, segs) in enumerate(arcs):        # the ring road re-routes itself
        liv.rot(base, (0, S(14, T_LIV, k * 0.25), 0))
        for s, b in enumerate(segs):
            liv.pos(b, (0, S(4, T_LIV / 2, s * 0.2 + k * 0.1), 0))
            liv.rot(b, (0, 0, S(9, T_LIV / 2, s * 0.25)))
    A.append(liv)

    P = {}
    for k, (base, segs) in enumerate(bridges):
        for s, b in enumerate(segs):
            P[b] = {"rot": (-7 - 4 * s, 0, 9 * (-1) ** (s + k))}
    for k, (base, segs) in enumerate(arcs):
        P[base] = {"rot": (10 * (-1) ** k, 18, 7)}
        for s, b in enumerate(segs):
            P[b] = {"rot": (0, 12 * (-1) ** s, 22 * (-1) ** s), "pos": (0, 9 * (-1) ** (s + k), 0)}
    warp = Anim("warp", length=T_WARP, loop="hold")
    fs = {0: 0.0, 0.35: 0.2, 0.6: -0.1, 1.0: 0.6, 1.45: 1.12, T_WARP: 1.0}
    for b, chs in P.items():
        for ch, v in chs.items():
            getattr(warp, ch)(b, {t: _scale_val(v, f, ch) for t, f in fs.items()})
    A.append(warp)
    night = Anim("nightmare", length=T_NIGHT, loop=True)
    for b, chs in P.items():
        for ch, v in chs.items():
            if ch == "rot":
                night.rot(b, (v[0], v[1], LIFE(5, T_NIGHT, (len(b) * 0.37) % 1.0, base=v[2])))
            else:
                night.pos(b, (0, LIFE(2.5, T_NIGHT / 2, (len(b) * 0.53 + b.count('2') * 0.2) % 1.0, base=v[1]), 0))
    A.append(night)

    col = Anim("collapse", length=T_COL, loop="hold")
    for k, (base, segs) in enumerate(bridges):
        for s, b in enumerate(segs):
            r = P[b]["rot"]
            f = 170 if s % 2 == 0 else -170
            t0 = 0.1 + 0.12 * (3 - s)
            col.rot(b, {0: r, t0: r, t0 + 0.45: (f, 0, 0)})
            col.scl(b, {0: 1.0, t0 + 0.3: 1.0, t0 + 0.7: 0.0})
    for k, (base, segs) in enumerate(arcs):
        r = P[base]["rot"]
        col.rot(base, {0: r, 1.6: (r[0], r[1] + 200, r[2])})
        for s, b in enumerate(segs):
            col.rot(b, {0: P[b]["rot"], 1.2: P[b]["rot"]})
            col.pos(b, {0: P[b]["pos"], 0.6: (0, 0, 0)})
            col.scl(b, {0: 1.0, 0.6 + 0.12 * s: 1.0, 1.0 + 0.12 * s: 0.0})
    col.scl("root", {0: 1.0, 1.5: 0.7, 2.0: 0.0})
    A.append(col)
    return A


# ====================================================================== miniature + dream-wave
MINI_STATES = {0: ["hidden"], 1: ["form"], 2: ["idle"], 3: ["charge"], 4: ["release"], 5: ["wink"]}
T_MINI_FORM, T_MINI_CHARGE, T_MINI_RELEASE, T_MINI_WINK = 1.2, 1.6, 0.6, 0.6


def build_mini():
    M_ = mats()
    m = Model("dn_city_mini", density=4.0, bounds=(4, 4, (0, 0.5, 0)))
    root = m.bone("root")
    fl = m.bone("float", root, pivot=(0, 0, 0))
    cl = m.bone("cloud", fl)
    cl.plane("y", (0, -0.6, 0), 20, 20, mats()["cloud"].but(key="minicloud"), density=3.0)
    core = m.bone("core", fl, pivot=(0, 0, 0))
    core.box((0, 0, 0), (6, 1.2, 6), M_["marble"], mats={"up": M_["floor"]})
    core.box((0, 0, 0), (6, 1.2, 6), M_["marble"], rot=(0, 45, 0))
    core.box((0, -1.6, 0), (3, 2.2, 3), M_["under"], rot=(0, 45, 0))
    core.box((0, -3.2, 0), (1, 1.2, 1), M_["lamp"])
    y = 0.6
    for w, h in ((2.6, 2.2), (2.2, 2.0), (1.8, 1.8)):
        core.box((0, y + h / 2, 0), (w, h, w), M_["wall"], density=6.0)
        core.box((0, y + h - 0.1, 0), (w + 0.4, 0.25, w + 0.4), M_["gold"])
        y += h
    for f, h in ((1.0, 0.6), (0.8, 0.6), (0.5, 0.5), (0.25, 0.4)):
        core.box((0, y + h / 2, 0), (1.8 * f, h, 1.8 * f), M_["gold"])
        y += h
    core.box((0, y + 0.7, 0), (0.3, 1.4, 0.3), M_["gold_glow"])
    core.plane("z", (0, y + 1.8, 0), 1.6, 1.6, M_["moon"], density=8.0)
    for k in range(4):
        a = math.radians(k * 90 + 45)
        x, z = 7.5 * math.cos(a), 7.5 * math.sin(a)
        b = m.bone(f"isl_{k + 1}", fl, pivot=(x, 0, z))
        b.box((x, 0, z), (3.6, 0.8, 3.6), M_["marble"], rot=(0, 30, 0))
        b.box((x, -1.0, z), (1.8, 1.4, 1.8), M_["under"], rot=(0, 45, 0))
        b.box((x, 1.6 + k * 0.2, z), (1.4, 2.4 + k * 0.4, 1.4), M_["wall3" if k % 2 else "wall"], density=6.0)
        hh = 2.8 + k * 0.4
        for j, ww in enumerate((1.7, 1.2, 0.7, 0.3)):
            b.box((x, hh + 0.3, z), (ww, 0.6, ww), [M_["roof"], M_["roof_b"], M_["roof_p"], M_["roof"]][k], rot=(0, 45 * (j % 2), 0))
            hh += 0.6
        b.box((x + 1.2, 1.0, z - 0.8), (0.9, 1.4, 0.9), M_["wall2"], density=6.0)
    rg = m.bone("ring", fl, pivot=(0, 0.4, 0))
    ring(rg, (0, 0.4, 0), 7.5, 16, (2.6, 0.7, 0.3), M_["gold_glow"], axis="y")
    for k in range(4):
        a = k * 90 + 45
        rg.box((0, 0.5, 0), (0.6, 0.25, 7.0), M_["street"], rot=(0, -a + 90, 0), pivot=(0, 0.5, 0))
    return m


def mini_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    spinA = Anim("spin", loop=True)
    spinA.rot("float", (LIFE(4, 3.0), spin(28), LIFE(3, 3.7)))
    spinA.pos("float", (0, LIFE(0.8, 2.4), 0))
    spinA.rot("ring", (0, spin(-60), 0))
    form = Anim("form", length=T_MINI_FORM, loop="hold")    # the folded districts settle into the model
    form.scl("root", {0: 0.0, 0.15: 0.3, 0.6: 1.25, 0.9: 0.92, T_MINI_FORM: 1.0})
    for k in range(4):
        a = math.radians(k * 90 + 45)
        form.pos(f"isl_{k + 1}", {0: (math.cos(a) * 30, 12, math.sin(a) * 30), 0.3 + 0.08 * k: (math.cos(a) * 10, 4, math.sin(a) * 10),
                                  0.75 + 0.06 * k: (0, 0, 0)})
        form.rot(f"isl_{k + 1}", {0: (0, 360, 0), 0.8 + 0.06 * k: (0, 0, 0)})
    form.scl("core", {0: (1, 0, 1), 0.4: (1, 0, 1), 0.8: (1, 1.2, 1), T_MINI_FORM: 1.0})
    idle = Anim("idle", loop=True)
    idle.scl("core", LIFE(0.03, 1.6, base=1.0))
    charge = Anim("charge", length=T_MINI_CHARGE, loop="hold")    # rises, ring races, swells
    charge.pos("root", {0: (0, 0, 0), T_MINI_CHARGE: (0, 6, 0)})
    charge.scl("root", {0: 1.0, 0.8: 1.15, 1.2: 1.05, T_MINI_CHARGE: 1.35})
    charge.rot("ring", {0: (0, 0, 0), T_MINI_CHARGE: (0, -900, 0)})
    charge.scl("ring", {0: 1.0, T_MINI_CHARGE: 1.5})
    for k in range(4):
        a = math.radians(k * 90 + 45)
        charge.pos(f"isl_{k + 1}", {0: (0, 0, 0), T_MINI_CHARGE: (math.cos(a) * 3, 2, math.sin(a) * 3)})
    release = Anim("release", length=T_MINI_RELEASE, loop="hold")
    release.pos("root", {0: (0, 6, 0), T_MINI_RELEASE: (0, 4, 0)})
    release.scl("root", {0: 1.35, 0.08: 1.9, 0.3: 1.0, T_MINI_RELEASE: 1.05})
    release.scl("ring", {0: 1.5, 0.1: 3.0, 0.35: 1.0})
    wink = Anim("wink", length=T_MINI_WINK, loop="hold")      # squashes to a line of light and winks out
    wink.pos("root", {0: (0, 4, 0), T_MINI_WINK: (0, 4, 0)})
    wink.scl("root", {0: 1.05, 0.2: (1.4, 0.15, 1.4), 0.4: (0.05, 0.05, 0.05), T_MINI_WINK: 0.0})
    wink.rot("float", {0: (0, 0, 0), T_MINI_WINK: (0, 240, 0)})
    A += [hidden, spinA, form, idle, charge, release, wink]
    return A


WAVE_STATES = {0: ["hidden"], 1: ["expand"], 2: ["fade"]}
T_WAVE = 1.4
WAVE_KEYS = {0: 0.03, 0.35: 0.42, 0.7: 0.74, 1.0: 0.92, T_WAVE: 1.0}   # radius fraction over time (mirrored in TS)


def build_wave():
    """Dream-wave: a luminous ring with an aurora wall that leans inward like a dome.
    Base radius 1 block (16 units); the script sets grimoire:size = radius in blocks."""
    m = Model("dn_city_wave", density=3.0, bounds=(80, 20, (0, 2, 0)))
    root = m.bone("root")
    rim = m.bone("rim", root)
    rim.plane("y", (0, 0.15, 0), 34, 34, tex.shaped(tex.m_ring(0.86, 1.0), "#fff6e6", "#ffd9b8", glow=1.0, var=0, key="dncwrim"),
              faces=("up", "down"), density=2.5)
    rim.plane("y", (0, 0.1, 0), 34, 34, tex.shaped(tex.m_ring(0.7, 0.84), "#e8b4c8", "#bcd6f0", glow=0.9, var=0, key="dncwrim2"),
              faces=("up", "down"), density=2.5)

    def aurora(ctx):
        t = tex.tile(ctx, PINK, 1, 0.9)
        k0, k1, k2 = tex.rgb("#fff1e6"), tex.rgb(PINK), tex.rgb(BLUE)
        v = ctx.V[..., None]
        t[..., :3] = np.where(v > 0.5, tex.mix(k1, k0, (v - 0.5) * 2), tex.mix(k2, k1, v * 2))
        ix, iy = tex.px(ctx)
        n = tex.fbm(ix / 2.0 + ctx.variant * 5, iy / 3.0, 501, 2)
        t[..., 3] = np.clip(ctx.V ** 1.3 * (0.55 + 0.6 * n), 0, 0.85)
        return t
    am = Mat(aurora, "dncwaur", mode="blend")
    wall = m.bone("wall", root)
    n = 20
    for k in range(n):
        a = k * 360 / n
        pb = m.bone(f"w{k + 1}", wall, pivot=(0, 0, 0), rot=(0, -a, 0))
        pb.cube((16, 0, -(2 * math.pi * 16 / n + 0.4) / 2), (0, 5.0, 2 * math.pi * 16 / n + 0.4), am, rot=(0, 0, 18),
                pivot=(16, 0, 0), variant=k % 3)
    return m


def wave_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    expand = Anim("expand", length=T_WAVE, loop="hold")
    expand.scl("root", {t: (v, 1.0, v) for t, v in WAVE_KEYS.items()})
    expand.scl("wall", {0: (1, 0.4, 1), 0.3: (1, 1.0, 1), 0.9: (1, 0.8, 1), T_WAVE: (1, 0.35, 1)})
    expand.rot("rim", {0: (0, 0, 0), T_WAVE: (0, 120, 0)})
    fade = Anim("fade", length=0.5, loop="hold")
    fade.scl("root", {0: (1.0, 1.0, 1.0), 0.5: (1.12, 0.0, 1.12)})
    return [hidden, expand, fade]


# ====================================================================== particles + sounds
def build_fx(pack):
    fx = particles(pack)
    dn_dream = ["#fff6eaff", "#ffd9b8ee", "#e8b4c800"]
    fx.effect("dn_city_cloud", "puff", count=6, life=(1.6, 2.8), size=(0.9, 2.2), shape=("disc", 3.0), speed=(0.2, 0.6),
              accel=(0, 0.15, 0), drag=0.8, colors=["#fff6f0cc", "#f2c6d899", "#f2c6d800"], blend="blend", spin=(360, 20))
    fx.effect("dn_city_cloud_n", "smoke", count=6, life=(1.4, 2.4), size=(0.9, 2.0), shape=("disc", 3.0), speed=(0.2, 0.6),
              accel=(0, 0.1, 0), drag=0.8, colors=["#5a4a78cc", "#2a2d5299", "#2a2d5200"], blend="blend", spin=(360, 30))
    fx.effect("dn_city_mote", "dot", count=10, life=(1.2, 2.4), size=(0.09, 0.0), shape=("sphere", 3.0), speed=(0.05, 0.3),
              accel=(0, 0.3, 0), colors=["#fff3c4ff", "#ffd9b8cc", "#e9cf8a00"])
    fx.effect("dn_city_chime", "star", count=5, life=(0.5, 1.0), size=(0.22, 0.0), shape=("sphere", 0.8), speed=(0.4, 1.2),
              drag=1.5, colors=["#ffffffff", "#ffe3a0ff", "#e9cf8a00"], spin=(360, 120))
    fx.effect("dn_city_window", "window", count=4, life=(1.0, 1.8), size=(0.3, 0.1), shape=("sphere", 1.2), speed=(0.3, 0.8),
              accel=(0, 0.6, 0), drag=0.8, colors=["#fff0b8ff", "#ffd77acc", "#e9cf8a00"])
    fx.effect("dn_city_ward", "petal", count=8, life=(1.2, 2.0), size=(0.16, 0.06), shape=("sphere", 1.2, "surface"),
              direction="inwards", speed=(0.4, 0.9), drag=1.0, colors=["#ffd9b8ff", "#e8b4c8cc", "#bcd6f000"], blend="blend", spin=(360, 140))
    fx.effect("dn_city_dust", "puff", count=12, life=(0.6, 1.3), size=(0.4, 1.0), shape=("disc", 1.4), speed=(1.0, 2.6),
              accel=(0, 0.4, 0), drag=1.8, colors=["#f2e6d6cc", "#d8c4b099", "#b8a89000"], blend="blend", spin=(360, 40))
    fx.effect("dn_city_dust_n", "puff", count=12, life=(0.6, 1.3), size=(0.4, 1.0), shape=("disc", 1.4), speed=(1.0, 2.6),
              accel=(0, 0.4, 0), drag=1.8, colors=["#8b8f9acc", "#6a4a6e99", "#2a2d5200"], blend="blend", spin=(360, 40))
    fx.effect("dn_city_shard", "shard", count=10, life=(0.5, 1.0), size=(0.18, 0.05), shape=("sphere", 0.6), speed=(2.0, 5.0),
              accel=(0, -9, 0), drag=0.4, colors=["#f6efe0ff", "#e8b4c8ff", "#cfc6b000"], blend="alpha", spin=(360, 300))
    fx.effect("dn_city_glass", "shard", count=12, life=(0.6, 1.2), size=(0.16, 0.06), shape=("disc", 1.6), direction=(0, -1, 0),
              speed=(1.0, 3.0), accel=(0, -10, 0), colors=["#e0f0ffff", "#bcd6f0dd", "#9d7fc400"], spin=(360, 400))
    fx.effect("dn_city_stare", "beam", count=3, life=(0.25, 0.4), size=(0.22, 0.05), size_y=(0.6, 1.2), shape=("sphere", 0.2),
              speed=0.0, colors=["#ffd0e8ff", "#c45a90ff", "#6e2f3a00"], facing="lookat_y")
    fx.effect("dn_city_eye", "eye", count=3, life=(0.7, 1.2), size=(0.3, 0.1), shape=("sphere", 1.0), speed=(0.2, 0.6),
              accel=(0, 0.4, 0), colors=["#ffd0e8ff", "#c45a90cc", "#2a2d5200"])
    fx.effect("dn_city_door", "door", count=4, life=(0.6, 1.1), size=(0.35, 0.1), shape=("sphere", 0.8), speed=(0.3, 1.0),
              drag=1.0, colors=["#ff9ad0ff", "#6a4a6ecc", "#2a2d5200"], spin=(40, 60))
    fx.effect("dn_city_night", "smoke", count=8, life=(1.0, 2.0), size=(0.5, 1.4), shape=("sphere", 2.5), speed=(0.1, 0.5),
              accel=(0, 0.25, 0), drag=0.8, colors=["#6a4a6eaa", "#2a2d5288", "#2a2d5200"], blend="blend", spin=(360, 30))
    fx.effect("dn_city_fold", "diamond", count=10, life=(0.5, 0.9), size=(0.25, 0.04), shape=("sphere", 4.0, "surface"),
              direction="inwards", speed=(5.0, 9.0), drag=0.5, colors=["#fff3c4ff", "#e8b4c8ff", "#6a4a6e00"], spin=(360, 200))
    fx.effect("dn_city_streak", "spark", count=6, life=(0.4, 0.7), size=(0.3, 0.05), shape=("sphere", 0.4), speed=(0.5, 1.5),
              colors=["#ffffffff", "#ffd9b8ff", "#e8b4c800"])
    fx.effect("dn_city_ring", "ringthin", count=1, life=(0.6, 0.7), size=(0.5, 4.0), facing="emitter_transform_xz",
              colors=["#fff6e6ff", "#e8b4c8cc", "#bcd6f000"])
    fx.effect("dn_city_wave", "wave", count=14, life=(0.6, 1.1), size=(0.6, 0.2), shape=("disc", 1.5), speed=(4.0, 8.0),
              accel=(0, 1.0, 0), drag=0.6, colors=["#fff1e6ff", "#e8b4c8ff", "#bcd6f000"], spin=(360, 60))
    fx.effect("dn_city_key", None, sprites=["key", "moon", "star", "window"], count=6, life=(1.0, 1.8), size=(0.24, 0.08),
              shape=("sphere", 1.5), speed=(0.3, 1.0), accel=(0, 0.5, 0), drag=0.8, colors=["#fff6eaff", "#ffd9b8cc", "#bcd6f000"])


MOTIF = [0, 7, 16, 11, 18, 14]   # invented dream motif (semitones), irregular rhythm below


def semi(f, s):
    return f * 2 ** (s / 12.0)


def build_sounds(pack):
    lp = sy.lowpass
    # ---- Phase I: arrival -- airy pad, glass chimes, distant bells
    rhythm = [0.9, 1.45, 1.75, 2.6, 3.05, 3.9]
    bells = [(t, sy.bell(semi(698.5, s), 1.6, bright=1.2) * 0.32) for t, s in zip(rhythm, MOTIF)]
    arrive = sy.at(5.5, (0.0, sy.pad(174.6, 5.5, cutoff=900, attack=1.5, release=2.0) * 0.45),
                   (0.3, sy.pad(261.6, 5.0, wave_="tri", cutoff=1600, attack=1.8, release=2.0) * 0.3),
                   (0.0, sy.wind(5.5, 300, 900, q=1.2, gust=0.3) * 0.12), (0.6, sy.shimmer(4.2, 2600, 30) * 0.22),
                   (0.2, lp(sy.bell(196.0, 3.0, bright=0.5), 1400) * 0.4), (2.8, lp(sy.bell(220.0, 2.6, bright=0.5), 1400) * 0.32),
                   *bells)
    sy.save(pack, "dn_city_arrive", sy.reverb(arrive, 2.6, 0.5), max_distance=96)
    sy.save(pack, "dn_city_window", sy.reverb(sy.at(0.8, (0, sy.pluck(semi(1396.9, 0), 0.6, 0.9)), (0.09, sy.pluck(semi(1396.9, 7), 0.5, 0.9) * 0.7)), 1.2, 0.4),
            variants=[sy.reverb(sy.at(0.8, (0, sy.pluck(semi(1396.9, s), 0.6, 0.9)), (0.09, sy.pluck(semi(1396.9, s + 4), 0.5, 0.9) * 0.7)), 1.2, 0.4)
                      for s in (2, 11, -3)], volume=0.7, max_distance=64)
    rise = sy.at(1.8, (0, sy.rumble(1.6, 80, 5) * 0.5), (0, sy.wind(1.6, 200, 700, q=2.5) * 0.35), (1.3, sy.bell(392.0, 1.2) * 0.25))
    sy.save(pack, "dn_city_rise", sy.reverb(rise, 1.6, 0.4), variants=[sy.reverb(sy.pitch(rise, 1.12), 1.6, 0.4)], max_distance=80)
    ward = sy.at(2.2, (0, sy.pad(523.3, 2.0, wave_="tri", cutoff=2600, attack=0.3, release=1.0) * 0.4),
                 (0.1, sy.shimmer(1.6, 2000, 14) * 0.35), (0.05, sy.bell(1046.5, 1.6) * 0.3), (0.4, sy.bell(semi(1046.5, 7), 1.4) * 0.22))
    sy.save(pack, "dn_city_ward", sy.reverb(ward, 1.8, 0.45), max_distance=48)
    # ---- Phase II: moving streets (stone on rails)
    clacks = [(0.15 + i * 0.33 + 0.05 * (i % 2), sy.thump(0.16, 420 - 30 * (i % 3), 150, click=0.8) * 0.45) for i in range(8)]
    scrape = sy.bandpass(sy.noise(3.0), 1800, 3.0) * sy.env(3.0, 0.4, 0.2, 0.8, 0.6) * 0.18
    move = sy.at(3.0, (0, sy.rumble(3.0, 55, 2.5) * 0.6), (0, scrape), (0.2, lp(sy.creak(2.4, 70, 110, 0.3), 900) * 0.3), *clacks)
    sy.save(pack, "dn_city_move", sy.reverb(move, 1.5, 0.35), variants=[sy.reverb(sy.pitch(move, 0.9), 1.5, 0.35)], max_distance=96)
    fall = sy.at(1.7, (0, sy.whoosh(0.8, 2200, 300) * 0.5), (0.78, sy.thump(0.9, 120, 32, click=0.6)), (0.78, sy.crack(0.6, 5200, 18) * 0.5),
                 (0.85, sy.shimmer(0.7, 2400, 8) * 0.25))
    sy.save(pack, "dn_city_balcony", sy.reverb(fall, 1.3, 0.3), variants=[sy.reverb(sy.pitch(fall, 1.1), 1.3, 0.3)], max_distance=64)
    t = sy.t_axis(2.4)
    roll = sy.rumble(2.4, 70, 6.0) * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 5.5 * t))) + sy.bandpass(sy.noise(2.4), 700, 1.5) * 0.25
    sy.save(pack, "dn_city_street", sy.reverb(sy.fade(roll, 0.1, 0.4), 1.0, 0.25), max_distance=64)
    steps = [(0.12 * i + 0.01 * (i % 3), sy.thump(0.2, 320 - 18 * i, 120, click=0.7) * (0.5 + 0.04 * i)) for i in range(10)]
    stair = sy.at(1.9, *steps, (0.0, sy.creak(1.2, 160, 120, 0.2) * 0.2), (1.25, sy.bell(semi(784, 4), 0.8) * 0.3))
    sy.save(pack, "dn_city_stair", sy.reverb(stair, 1.4, 0.35), max_distance=64)
    # ---- Phase III: the nightmare (same motif detuned, groaning architecture)
    nbells = [(t_ * 0.8, sy.pitch(sy.bell(semi(698.5, s) * 0.94, 1.6, bright=0.8, inharm=1.25), 0.97) * 0.3)
              for t_, s in zip(rhythm, [0, 6, 13, 11, 17, 12])]
    warp = sy.at(4.2, (0, lp(sy.creak(3.2, 70, 45, 0.5), 700) * 0.5), (0.2, sy.rumble(3.6, 45, 1.3) * 0.5),
                 (0.0, sy.shimmer(2.0, 2600, 20)[::-1] * 0.3), (1.6, sy.pad(116.5, 2.6, cutoff=600, attack=0.6) * 0.4),
                 (1.6, sy.pad(164.8, 2.6, cutoff=700, attack=0.6) * 0.3), *nbells)
    sy.save(pack, "dn_city_warp", sy.reverb(warp, 3.0, 0.5), max_distance=96)
    groan = sy.at(2.6, (0, lp(sy.creak(2.5, 60, 95, 0.45), 800) * 0.7), (0.3, sy.rumble(2.2, 40, 0.8) * 0.4))
    sy.save(pack, "dn_city_groan", sy.reverb(groan, 2.0, 0.45), variants=[sy.reverb(sy.pitch(groan, 0.85), 2.0, 0.45)], max_distance=96)
    slam = sy.at(1.2, (0, sy.creak(0.45, 220, 150, 0.3) * 0.5), (0.42, sy.thump(0.6, 150, 48, click=0.7)), (0.42, sy.crack(0.3, 3000, 6) * 0.4))
    sy.save(pack, "dn_city_door", sy.reverb(slam, 1.2, 0.35), variants=[sy.reverb(sy.pitch(slam, 1.15), 1.2, 0.35),
                                                                        sy.reverb(sy.pitch(slam, 0.88), 1.2, 0.35)], max_distance=48)
    n = int(sy.SR * 0.004)
    click = np.zeros(int(sy.SR * 0.4))
    for o in (0.0, 0.11):
        i = int(sy.SR * o)
        click[i:i + n] += sy.highpass(sy.noise(0.004), 3000)[:n]
    squelch = sy.bandpass(sy.noise(0.18), 650, 2.5) * sy.decay(0.18, 0.05)
    blink = sy.at(0.4, (0, click * 0.9), (0.02, squelch * 0.5), (0.13, sy.pluck(2637, 0.25, 0.9) * 0.25))
    sy.save(pack, "dn_city_blink", sy.reverb(blink, 0.6, 0.25), volume=0.8, max_distance=40)
    t = sy.t_axis(1.5)
    hum = sy.lowpass(sy.osc(110, 1.5, "saw") + sy.osc(116.5, 1.5, "saw"), 1200) * 0.4
    whine = sy.osc(sy.sweep(800, 1700, 1.5, 0.6)) * 0.25
    stare = (hum + whine + sy.choir(330, 1.5, "ee", voices=3, attack=0.1) * 0.3) * sy.env(1.5, 0.15, 0.2, 0.85, 0.4)
    sy.save(pack, "dn_city_stare", sy.reverb(stare, 1.2, 0.3), max_distance=48)
    knocks = [(0.95 * (1 - (1 - i / 7) ** 1.6), sy.thump(0.15, 260 + 20 * i, 110, click=0.9) * 0.4) for i in range(7)]
    corr = sy.at(1.8, *knocks, (0.0, sy.creak(0.9, 150, 260, 0.3) * 0.3), (0.95, sy.whoosh(0.25, 3000, 600) * 0.5),
                 (1.05, sy.thump(0.7, 110, 36, click=0.8)), (1.05, sy.crack(0.4, 4000, 10) * 0.4))
    sy.save(pack, "dn_city_corridor", sy.reverb(corr, 1.4, 0.35), max_distance=56)
    sf = sy.at(0.9, (0, sy.thump(0.8, 90, 30, click=0.9)), (0, sy.crack(0.4, 3200, 10) * 0.45), (0.02, sy.rumble(0.7, 50) * 0.4))
    sy.save(pack, "dn_city_stairfall", sy.reverb(sf, 1.0, 0.3), variants=[sy.reverb(sy.pitch(sf, 1.1), 1.0, 0.3),
                                                                          sy.reverb(sy.pitch(sf, 0.9), 1.0, 0.3)], max_distance=56)
    chirp = sy.roar(0.3, f0=520, f1=380, growl=40, rough=0.3, formant=(900, 2100), breath=0.2, bend=0.6)
    hop = sy.at(0.7, (0, sy.crack(0.25, 2400, 6) * 0.5), (0.05, chirp * 0.6), (0.3, sy.thump(0.25, 200, 80, click=0.6) * 0.5))
    sy.save(pack, "dn_city_fragment", sy.reverb(hop, 0.7, 0.25), variants=[sy.reverb(sy.pitch(hop, 1.18), 0.7, 0.25),
                                                                           sy.reverb(sy.pitch(hop, 0.86), 0.7, 0.25)], volume=0.8, max_distance=40)
    snarl = sy.roar(0.4, f0=300, f1=180, growl=55, rough=0.7, formant=(700, 1700), breath=0.4)
    bite = sy.at(0.6, (0, snarl * 0.6), (0.18, sy.thump(0.3, 220, 70, click=0.9) * 0.6), (0.18, sy.crack(0.3, 3500, 8) * 0.4))
    sy.save(pack, "dn_city_bite", sy.reverb(bite, 0.7, 0.25), max_distance=40)
    # ---- Phase IV: accelerating folds, miniature, the dream-wave
    folds = []
    tt = 0.0
    for i in range(14):
        folds.append((tt, sy.thump(0.25, 160 + 25 * i, 70 + 6 * i, click=0.7) * (0.35 + 0.03 * i)))
        folds.append((tt, sy.whoosh(0.22, 600 + 120 * i, 2400 + 150 * i) * 0.25))
        tt += 0.34 * (0.86 ** i)
    col = sy.at(3.6, *folds, (0.0, sy.osc(sy.sweep(120, 520, 3.2, 1.6)) * sy.env(3.2, 0.4, 0.2, 0.8, 0.4) * 0.25),
                (1.8, sy.bell(semi(698.5, 7), 1.6)[::-1] * 0.3))
    sy.save(pack, "dn_city_collapse", sy.reverb(col, 2.0, 0.4), max_distance=96)
    box = [(0.12 * i, sy.pluck(semi(2093, s), 0.5, 0.95) * 0.4) for i, s in enumerate([0, 7, 16, 11, 18, 14, 19])]
    mini = sy.at(1.6, *box, (0, sy.pad(1046.5, 1.4, wave_="tri", cutoff=3000, attack=0.2) * 0.25))
    sy.save(pack, "dn_city_mini", sy.reverb(mini, 1.6, 0.45), volume=0.8, max_distance=48)
    charge = sy.at(2.4, (0, sy.pad(261.6, 2.3, wave_="tri", cutoff=1800, attack=1.6, release=0.3) * 0.4),
                   (0, sy.shimmer(2.2, 2400, 26)[::-1] * 0.4), (0, sy.osc(sy.sweep(200, 900, 2.3, 2.0)) * sy.env(2.3, 1.8, 0.1, 1, 0.2) * 0.25))
    sy.save(pack, "dn_city_charge", sy.reverb(charge, 1.6, 0.4), max_distance=80)
    wave = sy.at(4.5, (0, sy.bell(semi(1396.9, 0), 0.9) * 0.2), (0, sy.pluck(semi(2093, 7), 0.6, 0.9) * 0.15),
                 (0.35, sy.thump(2.0, 70, 22, click=0.6) * 1.0), (0.35, sy.rumble(3.6, 38, 0.7) * 0.6),
                 (0.38, sy.pad(130.8, 3.6, cutoff=1200, attack=0.05, release=2.2) * 0.5), (0.38, sy.pad(196.0, 3.6, cutoff=1500, attack=0.05, release=2.2) * 0.35),
                 (0.38, sy.wind(3.6, 2400, 300, q=1.0) * 0.4), (0.5, sy.bell(98.0, 3.5, bright=0.6) * 0.4), (0.6, sy.shimmer(3.0, 2000, 30) * 0.2))
    sy.save(pack, "dn_city_wave", sy.reverb(wave, 3.0, 0.45), max_distance=128)
    wink = sy.at(0.7, (0, sy.pluck(semi(2637, 0), 0.3, 0.9) * 0.5), (0.08, sy.pluck(semi(2637, -5), 0.3, 0.9) * 0.4),
                 (0.16, sy.pluck(semi(2637, -12), 0.4, 0.9) * 0.35))
    sy.save(pack, "dn_city_wink", sy.reverb(wink, 1.2, 0.5), volume=0.7, max_distance=40)


# ====================================================================== build
def build(pack):
    build_fx(pack)
    sp, dsp = build_spire()
    asp = district_anims(dsp, has_moon=True)
    pack.actor("dn_city_spire", sp, asp, DISTRICT_STATES, always=["drift"], scale=SCALE, lifetime=60,
               display="The Sleeping Spire")
    qa = {}
    for v in ("a", "b"):
        qm, dq = build_quarter(v)
        aq = district_anims(dq)
        pack.actor(f"dn_city_quarter_{v}", qm, aq, DISTRICT_STATES, always=["drift"], scale=SCALE, lifetime=60,
                   display="Dream Quarter")
        qa[v] = (qm, aq)
    rm, br, ar = build_ring()
    ra = ring_anims(br, ar)
    pack.actor("dn_city_ring", rm, ra, DISTRICT_STATES, always=["drift"], scale=SCALE, lifetime=60, display="Dream Causeways")
    mm = build_mini()
    ma = mini_anims()
    pack.actor("dn_city_mini", mm, ma, MINI_STATES, always=["spin"], scale=1.0, lifetime=60, display="Miniature City")
    wm = build_wave()
    wa = wave_anims()
    pack.actor("dn_city_wave", wm, wa, WAVE_STATES, size_prop=True, lifetime=60, display="Dream-Wave", blend=0.0)
    build_sounds(pack)

    # ---- previews
    by = {a.name: a for a in asp}
    views = ((30, 14), (150, -30), (0, 70))
    pack.preview("dn_city_spire_dream", sp, [None, (by["assemble"], 2.6), (by["living"], 1.5)], views=views, cell=(380, 380))
    pack.preview("dn_city_spire_night", sp, [(by["warp"], T_WARP), (by["collapse"], 1.6)], views=views, cell=(380, 380),
                 skin="nightmare")
    for v in ("a", "b"):
        qm, aq = qa[v]
        bq = {a.name: a for a in aq}
        pack.preview(f"dn_city_quarter_{v}", qm, [None, (bq["warp"], T_WARP)], views=views, cell=(340, 340))
    bra = {a.name: a for a in ra}
    pack.preview("dn_city_ring", rm, [None, (bra["assemble"], 1.2), (bra["living"], 1.8)], views=((20, 35), (0, 89)), cell=(420, 420))
    pack.preview("dn_city_ring_n", rm, [(bra["warp"], T_WARP)], views=((20, 35),), cell=(420, 420), skin="nightmare")
    bm = {a.name: a for a in ma}
    pack.preview("dn_city_mini", mm, [None, (bm["form"], 0.45)], views=((30, 25), (0, 80)), cell=(300, 300))
    bw = {a.name: a for a in wa}
    pack.preview("dn_city_wave", wm, [(bw["expand"], 0.8)], views=((20, 25),), cell=(300, 300))
    for nm, mdl in (("spire", sp), ("quarter_a", qa["a"][0]), ("quarter_b", qa["b"][0]), ("ring", rm), ("mini", mm), ("wave", wm)):
        print(f"    dn_city_{nm}: {mdl.cube_count()} cubes, {len(mdl.order)} bones, tex {mdl.tex_size}")
