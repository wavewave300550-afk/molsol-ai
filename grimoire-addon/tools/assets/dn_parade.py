"""DN01 Reverie Procession: Parade of the Sleeping Moon.

Four original parade creatures, each with its own rig and gait:
  dn_parade_horse  porcelain carousel horse (rotary gallop with suspension, ribbon mane/tail)
  dn_parade_stag   mist-glass stag (blend glass shell over a lit inner frame, window-pane antlers,
                   pronking bound: all four feet together, long hang time)
  dn_parade_bird   curtain-winged bird (wings are curtain rods with rings, valances, velvet curtains
                   and tassels; glide / swoop / bank; curtain-reveal arrival, curtain-call departure)
  dn_parade_doll   floating star doll (ball-jointed porcelain marionette with a five-point star body,
                   no strings - only a cut control bar drifting above; tick-tock tilts, stillness, spin)
Plus the unrolling dream-road (dn_parade_road, 4 kinds of segment architecture), the Sleeping Moon
that hangs over the road (dn_parade_moon) and the stacking crescent hit mark (dn_parade_mark).
"""
import math

import numpy as np

from kit import synth as sy, tex
from kit.anim import LIFE, Anim, M, S
from kit.geo import Mat, Model, ring
from kit.parts import sym, wave

from .a_fx_common import particles

IVORY, PEACH, PINK, SGOLD, PBLUE, LAV = "#f7f1e3", "#ffd9b8", "#e8b4c8", "#e9cf8a", "#bcd6f0", "#cdbfe8"
TILT = {"tilt": {"type": "float", "range": [-60.0, 60.0], "default": 0.0, "client_sync": True}}


def spin(rate):
    return M(f"q.life_time*{rate}", lambda t: t * rate)


def tilt_expr():
    return M("q.property('grimoire:tilt')", lambda t: 0.0)


def cyc(T, fn, n=12):
    """Keyframes sampled from fn(p) over one loop (p in 0..1)."""
    return {round(T * i / n, 4): fn(i / n) for i in range(n + 1)}


def sstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# ================================================================= shared materials
def porc(base="#f8f3e8", shade="#ddd2c0", crack=0.6, gilt=None, glow=0.0):
    return tex.porcelain(base, shade, "#c2b49c", crack=crack, gilt=gilt, glow=glow)


GILT = tex.metal("#e2c27a", "#fff1c8", "#9a7838", bands=2.0, glow=0.18)
GILT_B = tex.metal("#f0d78e", "#fffbe6", "#b08a3e", bands=3.0, glow=0.45)


def garland(base, color=PINK, leaf="#b9d4a8", key="garl"):
    """Painted carousel swag: a looping pink garland with gold dots."""
    kc, kl, kg = tex.rgb(color), tex.rgb(leaf), tex.rgb(SGOLD)

    def post(ctx, t):
        if ctx.group != "side" or min(ctx.w, ctx.h) < 6:
            return t
        c = 0.42 + 0.2 * np.sin(ctx.U * math.pi * 2 * max(1, round(ctx.w / 10)))
        d = np.abs(ctx.V - c)
        t[..., :3] = np.where((d < 0.07)[..., None], kc, t[..., :3])
        t[..., :3] = np.where(((d >= 0.07) & (d < 0.11))[..., None], kl, t[..., :3])
        ix, iy = tex.px(ctx)
        dots = (iy == 1) & (ix % 4 == 1)
        t[..., :3] = np.where(dots[..., None], kg, t[..., :3])
        t[..., 4] = np.where(dots, 0.6, t[..., 4])
        return t
    return tex.overlay(base, post, key)


def ribbon(color, edge=SGOLD, glow=0.15):
    kc, ke = tex.rgb(color), tex.rgb(edge)

    def fn(ctx):
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, color, 1, glow)
        sh = 0.9 + 0.1 * np.sin(ctx.V * math.pi * 4 + ctx.variant)
        t[..., :3] = np.clip(kc * sh[..., None], 0, 1)
        e = (ix == 0) | (ix == ctx.w - 1)
        t[..., :3] = np.where(e[..., None], ke, t[..., :3])
        t[..., 4] = np.where(e, 0.5, glow)
        tip = (iy == ctx.h - 1) & (ix % 2 == 1)                     # notched ribbon end
        t[..., 3] = np.where(tip, 0.0, 1.0)
        return t
    return Mat(fn, f"ribbon{color}{edge}{glow}")


def curtain(base, shade, fringe=SGOLD, glow=0.08, folds=3.0, key=None):
    """Velvet curtain: vertical folds, gold top band and a cut-out tasselled fringe."""
    kb, ks, kf = tex.rgb(base), tex.rgb(shade), tex.rgb(fringe)

    def fn(ctx):
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, base, 1, glow)
        f = 0.5 + 0.5 * np.cos(ctx.U * math.pi * 2 * folds + ctx.variant)
        t[..., :3] = tex.mix(ks, kb, f[..., None] ** 0.8)
        hl = f > 0.93
        t[..., :3] = np.where(hl[..., None], np.clip(kb + 0.08, 0, 1), t[..., :3])
        top = iy < 1
        bot = iy >= ctx.h - 2
        t[..., :3] = np.where((top | bot)[..., None], kf, t[..., :3])
        t[..., 4] = np.where(top | bot, 0.45, glow)
        t[..., 3] = np.where((iy == ctx.h - 1) & (ix % 2 == 1), 0.0, 1.0)
        return tex.grain(ctx, t, 0.03)
    return Mat(fn, key or f"curtain{base}{shade}{fringe}{glow}{folds}")


def window_mat(frame="#eef1f8", lit0="#fff2c8", lit1="#ffc9a8"):
    """Arched lit window with a cross mullion; transparent outside the arch."""
    kf, k0, k1 = tex.rgb(frame), tex.rgb(lit0), tex.rgb(lit1)

    def fn(ctx):
        u, v = ctx.U * 2 - 1, 1 - ctx.V * 2
        t = np.zeros((ctx.h, ctx.w, 5))
        arch = (np.abs(u) <= 1) & ((v <= 0.3) | (np.hypot(u, (v - 0.3) / 0.7) <= 1))
        inner = (np.abs(u) <= 0.68) & (v >= -0.8) & ((v <= 0.3) | (np.hypot(u / 0.68, (v - 0.3) / 0.5) <= 1))
        mull = inner & ((np.abs(u) < 0.13) | (np.abs(v + 0.2) < 0.1))
        glass = inner & ~mull
        t[..., :3] = np.where(glass[..., None], tex.mix(k1, k0, ((v + 1) / 2)[..., None]), kf)
        t[..., 3] = arch * 1.0
        t[..., 4] = np.where(glass, 0.95, 0.35)
        return t
    return Mat(fn, f"window{frame}{lit0}{lit1}", directional=True)


def flagstones():
    """Ivory flagstones in offset courses, soft-gold glowing grout, a few pastel stones and star inlays."""
    stones = [tex.rgb(c) for c in ("#f7f1e3", "#f3ead8", "#fbf6ec", "#f0e4d6", "#f6e6e6", "#e9eef7")]
    kg, ks = tex.rgb("#f0d78e"), tex.rgb("#ffe9a8")

    def fn(ctx):
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, IVORY, 1, 0.1)
        row = iy // 7
        off = (row * 5) % 11
        col = (ix + off) // 11
        h = tex._hash(col, row, 7)
        idx = np.clip((h * len(stones)).astype(int), 0, len(stones) - 1)
        base = np.stack(stones)[idx]
        n = tex.vnoise(ix / 3.0, iy / 3.0, 3)[..., None]
        t[..., :3] = np.clip(base * (0.94 + 0.08 * n), 0, 1)
        grout = (iy % 7 == 0) | ((ix + off) % 11 == 0)
        t[..., :3] = np.where(grout[..., None], kg, t[..., :3])
        t[..., 4] = np.where(grout, 0.55, 0.1)
        lx, ly = (ix + off) % 11, iy % 7
        star = (h > 0.82) & (((lx == 5) & (ly >= 2) & (ly <= 5)) | ((ly == 3) & (lx >= 4) & (lx <= 6)))
        t[..., :3] = np.where(star[..., None], ks, t[..., :3])
        t[..., 4] = np.where(star, 0.9, t[..., 4])
        return t
    return Mat(fn, "dnflag")


def bunting():
    cols = [tex.rgb(c) for c in (PINK, PBLUE, PEACH, LAV)]

    def fn(ctx):
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, PINK, 1, 0.2)
        k = ix // 6
        lx = (ix % 6) - 2.5
        tri = (iy < 1) | (iy <= (ctx.h - 1) * (1 - np.abs(lx) / 3.0))
        t[..., :3] = np.stack(cols)[k % len(cols)]
        t[..., :3] = np.where((iy < 1)[..., None], tex.rgb(SGOLD), t[..., :3])
        t[..., 3] = tri * 1.0
        return t
    return Mat(fn, "dnbunting", directional=True)


def mist(a=0.35):
    def fn(ctx):
        ix, iy = tex.px(ctx)
        n = tex.fbm(ix / 3.0 + ctx.variant * 4, iy / 2.5, 13)
        t = tex.tile(ctx, "#e4eefc", 1, 0.35)
        t[..., :3] = tex.mix(tex.rgb("#c6d6f2"), tex.rgb("#f6f0ff"), n[..., None])
        t[..., 3] = np.clip(a * (0.6 + n) * (1 - ctx.V ** 1.5), 0, 1)
        return t
    return Mat(fn, f"dnmist{a}", mode="blend")


def glass(a=0.36):
    return tex.crystal("#dbe9fb", "#a9bfe9", "#ffffff", a=a, mode="blend", glow=0.35, facets=4.0)


# ================================================================= 1. PORCELAIN HORSE
HORSE_LEGS = ("fore_r", "fore_l", "hind_r", "hind_l")


def horse_model():
    m = Model("dn_parade_horse", density=1.0, bounds=(6, 6, (0, 2, 0)))
    body_m = garland(porc(), key="hgarl")
    pm = porc()
    blanket = tex.trimmed(tex.fabric("#e8b4c8", "#f3cbd8", stripe_w=3, glow=0.06, fringe=True), SGOLD, 1, 0, glow=0.4)
    blue_bl = tex.trimmed(tex.fabric("#bcd6f0", "#d2e3f5", stripe_w=2, glow=0.06), SGOLD, 1, 0, glow=0.4)
    jewel = tex.glow_flat("#9fd0ff", 0.9, core="#ffffff")
    pink_j = tex.glow_flat("#ffb8d8", 0.9, core="#ffffff")
    pole_m = tex.banded(tex.metal("#f3ead2", "#ffffff", "#c9b88f", bands=1.0, glow=0.15), "#e2b862", every=4, width=2, glow=0.4)
    star_m = tex.shaped(tex.m_star(5, 0.45), "#fff3c4", SGOLD, glow=1.0, var=0, outline="#d9a94a", key="hstar")
    eye = ["      ", " #### ", "#    #", "      "]
    head_m = tex.stamped(porc(crack=0.3), eye, "#7a6a8a", glow=0.0, key="heye")

    root = m.bone("root")
    tilt = m.bone("tilt", root)
    body = m.bone("body", tilt, pivot=(0, 25, 0))
    body.box((0, 26, 0), (10, 11, 20), body_m)
    body.box((0, 27, -10.5), (10.6, 12, 6), pm, variant=1)              # chest
    body.box((0, 27.5, 9.5), (11, 11.5, 7), body_m, variant=2)          # rump
    body.box((0, 32.1, 1), (11.8, 1.0, 11.5), blanket)                  # saddle cloth (top)
    for sx in (1, -1):
        body.plane("x", (sx * 5.95, 28.6, 1), 11.5, 7.5, blanket)        # saddle cloth (sides)
        body.box((sx * 6.1, 24.8, 1), (0.6, 0.6, 11.5), GILT)            # gold hem
        for k in range(3):
            body.box((sx * 6.2, 23.6, -3 + k * 4), (0.8, 1.8, 0.8), GILT_B, variant=k)   # tassels
    body.box((0, 33.2, 1.5), (7.2, 1.6, 7.5), blue_bl)                  # seat
    body.box((0, 34.6, -2.2), (4, 2.2, 1.4), GILT)                      # pommel
    body.box((0, 34.8, 5.2), (7, 2.6, 1.3), GILT, variant=1)            # cantle
    body.box((0, 25.5, -13.6), (11.2, 1.6, 1.0), GILT)                  # breast collar
    body.box((0, 25.5, -14.2), (2.2, 2.2, 0.8), jewel)
    for sx in (1, -1):
        body.box((sx * 3.6, 24.8, -14.0), (1.4, 1.4, 0.6), pink_j)
    body.box((0, 21.0, 0), (6, 1.0, 16), tex.vgrad("#e7dccb", "#d2c5b0", var=0.02))   # belly shade
    body.box((0, 18.5, 1.5), (2.4, 2.4, 2.4), GILT)                     # pole knob under belly
    body.locator("heart", (0, 28, 0))

    # carousel pole: the horse carries its own gilt pole and star finial
    pole = m.bone("pole", body, pivot=(0, 34, 1.5))
    pole.box((0, 47, 1.5), (1.8, 26, 1.8), pole_m)
    pole.box((0, 60.6, 1.5), (3.4, 1.4, 3.4), GILT)
    pole.box((0, 35.6, 1.5), (3.0, 1.2, 3.0), GILT, variant=1)
    star = m.bone("pole_star", pole, pivot=(0, 65, 1.5))
    star.plane("z", (0, 65, 1.5), 7, 7, star_m)
    star.plane("x", (0, 65, 1.5), 7, 7, star_m)

    # neck (authored upright, bent by bind rotations)
    n1 = m.bone("neck1", body, pivot=(0, 30, -11), rot=(-26, 0, 0))
    n1.box((0, 35, -11), (6.8, 11, 7.6), pm, variant=2)
    n2 = m.bone("neck2", n1, pivot=(0, 40, -11), rot=(-8, 0, 0))
    n2.box((0, 43.5, -11), (6, 8, 6.6), pm)
    head = m.bone("head", n2, pivot=(0, 47, -11), rot=(-82, 0, 0))
    head.box((0, 50.5, -11.2), (6.4, 7.5, 7), pm, mats={"east": head_m, "west": head_m}, density=2)   # skull (+Y = forward after the bend)
    head.box((0, 56.5, -11.6), (5, 6.5, 5.6), pm, variant=1)            # muzzle
    head.box((0, 59.6, -11.6), (4.6, 0.8, 5.2), tex.flat("#d9b8b0"))    # nose tip
    head.box((0, 54.5, -11.6), (5.4, 1.0, 6.0), GILT)                   # noseband
    head.box((0, 50.0, -11.2), (6.8, 1.0, 7.4), GILT, variant=1)        # browband
    head.box((0, 50.0, -7.4), (1.8, 1.8, 0.6), pink_j)
    for sx in (1, -1):
        head.box((sx * 2.0, 48.5, -6.4), (1.4, 1.2, 3.6), pm, rot=(0, 0, sx * -12))   # ears
    plume = m.bone("plume", n2, pivot=(0, 47, -8.6))
    for k, (c0, c1) in enumerate(((PINK, "#fff0f6"), (PEACH, "#fff6ea"), (PBLUE, "#f2f8ff"))):
        f = tex.feather(c0, c1, SGOLD, glow=0.1, glow_tip=0.4)
        plume.box((0, 53, -8.6), (5, 12, 0), f, rot=(-20, k * 60, 180), pivot=(0, 47, -8.6), faces=("north", "south"))

    # ribbon mane: 4 strands down the back of the neck, 3 bones each
    mane_cols = (PINK, PEACH, PBLUE, LAV)
    for i in range(4):
        par = "neck1" if i < 2 else "neck2"
        y = 33 + i * 3.6
        z = -7.0
        prev = par
        for j in range(3):
            b = m.bone(f"mane{i + 1}_{j + 1}", prev, pivot=(0, y - j * 4.2, z), rot=((-30 if j == 0 else -10), 0, 0))
            b.plane("x", (0.1 * (i % 2), y - j * 4.2 - 2.1, z + 0.4), 2.8, 4.4, ribbon(mane_cols[(i + j) % 4]), variant=j)
            prev = b.name

    # ribbon tail
    prev = "body"
    for j in range(4):
        y = 30 - j * 4.6
        b = m.bone(f"tail{j + 1}", prev, pivot=(0, y, 13), rot=((-40 if j == 0 else -8), 0, 0))
        for k, c in enumerate((PINK, PEACH, PBLUE)):
            b.box((0, y - 2.3, 13), (0, 4.8, 3.0), ribbon(c), rot=(0, (k - 1) * 28, 0), pivot=(0, y, 13),
                  faces=("east", "west"), variant=k)
        prev = b.name

    # legs: thigh, cannon, gilt hoof
    for leg in HORSE_LEGS:
        fore = leg.startswith("fore")
        sx = 1 if leg.endswith("r") else -1
        x, z = sx * 3.4, (-10 if fore else 9.5)
        top = 22 if fore else 22.5
        u = m.bone(f"{leg}_1", body, pivot=(x, top, z))
        u.box((x, top - 4.5, z), (4.0, 10, 4.8), pm, variant=1)
        lo = m.bone(f"{leg}_2", u, pivot=(x, 13, z))
        lo.box((x, 8.6, z), (2.8, 9, 3.0), pm, variant=2)
        lo.box((x, 5.0, z), (3.3, 1.0, 3.5), GILT_B)                     # fetlock band
        lo.box((x, 12.6, z), (3.4, 1.0, 3.6), GILT, variant=1)            # knee band
        hf = m.bone(f"{leg}_3", lo, pivot=(x, 4.2, z))
        hf.box((x, 1.7, z - 0.3), (3.6, 3.4, 3.9), GILT)
        hf.locator(f"hoof_{leg}", (x, 0.2, z))
    return m


def leg_pose(q, fore, amp=1.0):
    q %= 1.0
    st = 0.36
    af, ab = (28, -24) if fore else (20, -32)
    if q < st:
        f = q / st
        up = af + (ab - af) * f
        lo = -6 * math.sin(math.pi * f)
        hf = -up * 0.6
    else:
        f = (q - st) / (1 - st)
        up = ab + (af - ab) * sstep(f)
        fold = math.sin(math.pi * min(1.0, f * 1.15))
        lo = (-100 if fore else -48) * fold
        hf = (-30 if fore else 25) * fold
    return up * amp, lo * amp, hf * amp


def horse_gallop(name, T, amp, lift, pitch, head_low=0.0, loop=True):
    a = Anim(name, length=T, loop=loop)
    offs = {"hind_l": 0.0, "hind_r": 0.1, "fore_l": 0.3, "fore_r": 0.42}
    for leg, o in offs.items():
        fore = leg.startswith("fore")
        k = [{}, {}, {}]
        for i in range(13):
            p = i / 12
            v = leg_pose(p - o, fore, amp)
            for j in range(3):
                k[j][round(T * p, 4)] = (v[j], 0, 0)
        for j in range(3):
            a.rot(f"{leg}_{j + 1}", k[j])
    a.pos("body", cyc(T, lambda p: (0, lift * (0.5 + 0.5 * math.cos(2 * math.pi * (p - 0.78))), 0)))
    a.rot("body", cyc(T, lambda p: (pitch * math.sin(2 * math.pi * (p - 0.12)), 0, 0)))
    a.rot("neck1", cyc(T, lambda p: (-head_low - pitch * 0.9 * math.sin(2 * math.pi * (p - 0.2)), 0, 0)))
    a.rot("head", cyc(T, lambda p: (head_low * 0.4 + pitch * 0.6 * math.sin(2 * math.pi * (p - 0.3)), 0, 0)))
    a.rot("pole_star", cyc(T, lambda p: (0, 0, 8 * math.sin(2 * math.pi * p))))
    a.sound(0.0, "hoof")
    a.sound(round(T * 0.32, 3), "hoof")
    a.particle(round(T * 0.05, 3), "hoofdust", locator="hoof_hind_l")
    a.particle(round(T * 0.36, 3), "hoofdust", locator="hoof_fore_l")
    return a


def horse_anims():
    A = []
    life = Anim("life", loop=True)
    life.rot("tilt", (tilt_expr(), 0, 0))
    for i in range(4):
        wave(life, [f"mane{i + 1}_{j + 1}" for j in range(3)], 0, 9, 0.9, lag=0.16, grow=1.2, clock="q.life_time")
    wave(life, [f"tail{j + 1}" for j in range(4)], 2, 8, 1.3, lag=0.14, grow=1.25, clock="q.life_time")
    life.rot("plume", (LIFE(6, 1.1), 0, LIFE(5, 1.7)))
    life.rot("pole_star", (0, spin(90), 0))
    life.scl("body", (LIFE(0.015, 2.2, base=1.0), LIFE(0.02, 2.2, base=1.0), 1.0))
    A.append(life)

    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    arrive = Anim("arrive", length=1.0, loop="hold")      # glaze sets, the carousel horse rears and lands
    arrive.scl("root", {0: (0.3, 0.0, 0.3), 0.25: (1.08, 1.12, 1.08), 0.4: 1.0, 1.0: 1.0})
    arrive.pos("root", {0: (0, 14, 0), 0.25: (0, 3, 0), 0.4: (0, 0, 0), 1.0: (0, 0, 0)})
    arrive.rot("body", {0: (0, 0, 0), 0.4: (0, 0, 0), 0.62: (30, 0, 0), 0.8: (24, 0, 0), 1.0: (0, 0, 0)})
    arrive.pos("body", {0: (0, 0, 0), 0.4: (0, 0, 0), 0.62: (0, 5, 3), 1.0: (0, 0, 0)})
    for s in ("r", "l"):
        ph = 0.0 if s == "r" else 0.07
        arrive.rot(f"fore_{s}_1", {0: (60, 0, 0), 0.4: (40, 0, 0), 0.55 + ph: (70, 0, 0), 0.68 + ph: (20, 0, 0),
                                  0.8 + ph: (60, 0, 0), 1.0: (0, 0, 0)})
        arrive.rot(f"fore_{s}_2", {0: (-100, 0, 0), 0.55 + ph: (-110, 0, 0), 0.7 + ph: (-30, 0, 0), 0.82: (-90, 0, 0), 1.0: (0, 0, 0)})
        arrive.rot(f"hind_{s}_1", {0: (40, 0, 0), 0.4: (0, 0, 0), 0.62: (-26, 0, 0), 1.0: (0, 0, 0)})
        arrive.rot(f"hind_{s}_2", {0: (-60, 0, 0), 0.4: (0, 0, 0), 1.0: (0, 0, 0)})
    arrive.rot("neck1", {0: (0, 0, 0), 0.62: (-18, 0, 0), 1.0: (0, 0, 0)})
    arrive.rot("head", {0: (0, 0, 0), 0.62: (-14, 0, 0), 0.8: (10, 0, 0), 1.0: (0, 0, 0)})
    arrive.sound(0.6, "neigh")
    A.append(arrive)

    A.append(horse_gallop("parade", 0.7, 0.85, 2.6, 5.0))
    A.append(horse_gallop("charge", 0.5, 1.15, 4.0, 7.0, head_low=14))

    depart = Anim("depart", length=1.1, loop="hold")       # rears, then gallops up into the sky and dissolves
    depart.rot("body", {0: (0, 0, 0), 0.3: (34, 0, 0), 0.55: (18, 0, 0), 1.1: (-10, 0, 0)})
    depart.pos("body", {0: (0, 0, 0), 0.3: (0, 6, 4), 1.1: (0, 6, 0)})
    depart.pos("root", {0: (0, 0, 0), 0.4: (0, 0, 0), 1.1: (0, 56, -30)})
    depart.scl("root", {0: 1.0, 0.5: 1.0, 0.85: (0.7, 0.9, 0.7), 1.1: 0.0})
    for s in ("r", "l"):
        depart.rot(f"fore_{s}_1", {0: (0, 0, 0), 0.3: (70, 0, 0), 0.6: (40, 0, 0), 1.1: (60, 0, 0)})
        depart.rot(f"fore_{s}_2", {0: (0, 0, 0), 0.3: (-110, 0, 0), 1.1: (-100, 0, 0)})
        depart.rot(f"hind_{s}_1", {0: (0, 0, 0), 0.3: (-30, 0, 0), 0.7: (-40, 0, 0), 1.1: (-30, 0, 0)})
        depart.rot(f"hind_{s}_2", {0: (0, 0, 0), 0.7: (-20, 0, 0), 1.1: (-40, 0, 0)})
    depart.rot("neck1", {0: (0, 0, 0), 0.3: (-20, 0, 0), 1.1: (-10, 0, 0)})
    A.append(depart)
    return A


HORSE_STATES = {0: ["hidden"], 1: ["arrive"], 2: ["parade"], 3: ["charge"], 4: ["depart"]}


# ================================================================= 2. MIST-GLASS STAG
STAG_LEGS = ("fore_r", "fore_l", "hind_r", "hind_l")


def stag_model():
    m = Model("dn_parade_stag", density=1.0, bounds=(6, 7, (0, 2.5, 0)))
    frame = tex.metal("#eef1f8", "#ffffff", "#9aa6c4", bands=2.0, glow=0.35)
    frame_b = tex.metal("#f3ead2", "#ffffff", "#b8a57a", bands=3.0, glow=0.5)
    gl, gl2 = glass(0.34), glass(0.44)
    heart = tex.glow_flat("#ffe2c0", 1.0, core="#ffffff")
    light = tex.glow_flat("#fff2c8", 1.0, core="#ffffff")
    blue_l = tex.glow_flat("#cfe4ff", 1.0, core="#ffffff")
    win = window_mat()
    hoof = tex.metal("#d8deea", "#ffffff", "#7d88a8", bands=2.0, glow=0.5)

    root = m.bone("root")
    tilt = m.bone("tilt", root)
    body = m.bone("body", tilt, pivot=(0, 30, 0))
    body.box((0, 35.5, 0), (1.6, 1.6, 23), frame)                        # spine
    body.box((0, 26.8, -3.5), (1.2, 1.2, 12), frame, variant=1)          # sternum
    for k, z in enumerate((-7, -3.5, 0, 3.5)):
        ring(body, (0, 31.2, z), 4.6 - 0.25 * k, 8, (3.6, 0.9, 0.9), frame_b if k % 2 == 0 else frame, axis="z")
    body.box((0, 33, 9), (5, 3, 4), frame, variant=2)                    # pelvis
    body.box((0, 31, -2), (2.2, 2.2, 2.2), heart, rot=(45, 45, 0))      # lantern heart
    body.locator("heart", (0, 31, -2))
    bg = m.bone("body_g", body, pivot=(0, 30, 0))
    bg.box((0, 31, 0), (10, 10.5, 20), gl)
    bg.box((0, 31.5, -10.5), (9, 10, 4), gl, variant=1)
    bg.box((0, 32, 10.5), (9, 9.5, 4), gl, variant=2)
    for k in range(3):       # mist veils trailing under the belly
        v = m.bone(f"veil{k + 1}", body, pivot=(0, 26, -6 + k * 6))
        v.plane("x", (0, 22.5, -6 + k * 6 + 2), 7, 7, mist(0.42), variant=k)
        v.plane("z", (0, 22.5, -6 + k * 6 + 2), 9, 7, mist(0.42), variant=k + 1)

    n1 = m.bone("neck1", body, pivot=(0, 34, -11), rot=(-14, 0, 0))
    n1.box((0, 40, -11), (1.3, 12, 1.3), frame)
    n1g = m.bone("neck1_g", n1, pivot=(0, 34, -11))
    n1g.box((0, 40, -11.2), (5.4, 12.5, 6.2), gl2)
    n2 = m.bone("neck2", n1, pivot=(0, 46, -11), rot=(-6, 0, 0))
    n2.box((0, 48.5, -11), (1.2, 5, 1.2), frame, variant=1)
    head = m.bone("head", n2, pivot=(0, 51, -11), rot=(-72, 0, 0))
    head.box((0, 54.5, -11), (1.2, 8, 1.2), frame)                       # skull bar (forward after bend)
    head.box((0, 51.5, -12.3), (3.8, 1.2, 1.2), frame, variant=1)  # brow
    for s_ in (1, -1):
        head.box((s_ * 2.0, 52.0, -12.6), (0.9, 0.9, 0.9), blue_l)       # eyes
    hg = m.bone("head_g", head, pivot=(0, 51, -11))
    hg.box((0, 54.2, -11.3), (5.0, 8.5, 5.4), gl2)
    hg.box((0, 59.5, -11.6), (3.4, 3.2, 3.8), gl2, variant=1)
    for s_ in (1, -1):
        hg.box((s_ * 3.4, 51.6, -9.2), (2.6, 0, 1.6), gl2, faces=("up", "down"))
        hg.box((s_ * 3.2, 51.6, -9.4), (0, 1.6, 3.4), gl2, rot=(0, 0, s_ * 20), faces=("east", "west"))

    # antlers: frame beams branching into tiny lit window panes and lights
    for s, sx in (("r", 1), ("l", -1)):
        a1 = m.bone(f"antler_{s}_1", head, pivot=(sx * 1.5, 51.5, -9), rot=(88, 0, -sx * 30))
        a1.box((sx * 1.5, 56, -9), (1.1, 9, 1.1), frame_b)
        a1.box((sx * 1.5, 54.5, -10.5), (0.8, 0.8, 3.5), frame_b, variant=1)     # brow tine
        a1.box((sx * 1.5, 54.5, -12.6), (1.2, 1.2, 1.2), light)
        a2 = m.bone(f"antler_{s}_2", a1, pivot=(sx * 1.5, 60.5, -9), rot=(10, 0, -sx * 12))
        a2.box((sx * 1.5, 65, -9), (0.9, 9, 0.9), frame_b, variant=2)
        a2.box((sx * 3.5, 63, -9), (4, 0.8, 0.8), frame_b, variant=1)            # outward tine
        a2.box((sx * 5.8, 63, -9), (1.2, 1.2, 1.2), light)
        a2.plane("z", (sx * 3.2, 65.4, -9), 3.2, 4.0, win, density=4)            # window between tines
        a2.box((sx * 1.5, 69.8, -9), (1.3, 1.3, 1.3), light)
        a3 = m.bone(f"antler_{s}_3", a2, pivot=(sx * 1.5, 67, -9), rot=(-30, 0, -sx * 10))
        a3.box((sx * 1.5, 67, -11.5), (0.8, 0.8, 5), frame_b)                   # forward tine
        a3.box((sx * 1.5, 70.2, -13.6), (0.8, 6, 0.8), frame_b, variant=1)
        a3.box((sx * 1.5, 73.4, -13.6), (1.2, 1.2, 1.2), light)
        a3.plane("x", (sx * 1.5, 69.8, -11.2), 4.2, 4.6, win, density=4)
        a3.box((sx * 1.5, 67, -6.8), (0.8, 0.8, 4), frame_b, variant=2)         # back tine
        a3.box((sx * 1.5, 67, -4.6), (1.1, 1.1, 1.1), light)
        a1.locator(f"antler_tip_{s}", (sx * 5.8, 63, -9))

    # tail tuft
    tl = m.bone("tail", body, pivot=(0, 35, 12))
    tl.box((0, 34, 13.5), (0, 5, 4), gl2, faces=("east", "west"), rot=(30, 0, 0), pivot=(0, 35, 12))
    tl.box((0, 34, 13.5), (3, 5, 0), gl2, faces=("north", "south"), rot=(30, 0, 0), pivot=(0, 35, 12))

    # long slender legs: frame bones with glass shells
    for leg in STAG_LEGS:
        fore = leg.startswith("fore")
        sx = 1 if leg.endswith("r") else -1
        x, z = sx * 3.0, (-8.5 if fore else 9.0)
        top = 27
        u = m.bone(f"{leg}_1", body, pivot=(x, top, z))
        u.box((x, 22, z), (1.2, 10, 1.2), frame)
        u.box((x, 17, z), (1.8, 1.8, 1.8), frame_b)                    # joint
        ug = m.bone(f"{leg}_1g", u, pivot=(x, top, z))
        ug.box((x, 22.5, z), (3.4, 10, 4.0), gl)
        lo = m.bone(f"{leg}_2", u, pivot=(x, 17, z))
        lo.box((x, 10.5, z), (0.9, 13, 0.9), frame, variant=1)
        lg = m.bone(f"{leg}_2g", lo, pivot=(x, 17, z))
        lg.box((x, 10.8, z), (2.0, 12.5, 2.2), gl, variant=1)
        hf = m.bone(f"{leg}_3", lo, pivot=(x, 4, z))
        hf.box((x, 2, z - 0.4), (2.2, 4, 2.6), hoof)
        hf.box((x, 4.6, z), (1.6, 1.6, 1.6), blue_l)
        hf.locator(f"hoof_{leg}", (x, 0.2, z))
    return m


STAG_GLASS = ["body_g", "neck1_g", "head_g"] + [f"{l}_{k}g" for l in STAG_LEGS for k in (1, 2)]


def stag_leg(fore, phase):
    """Pronk/bound poses: 'crouch' 'push' 'tuck' 'reach' 'land' -> (upper, lower, hoof)."""
    P = {"stand": (0, 0, 0),
         "crouch": ((22, -46, 24) if fore else (-26, 50, -24)),
         "push": ((-14, 0, 20) if fore else (14, -6, 30)),
         "tuck": ((58, -110, -20) if fore else (-50, 96, 20)),
         "reach": ((24, -8, 0) if fore else (-22, 14, 0)),
         "land": ((10, -24, 14) if fore else (-12, 26, -12))}
    return P[phase]


def stag_bound(name, T, keys, lift_keys, loop):
    """keys: [(t_frac, phase)]; lift_keys: {t_frac: body y}."""
    a = Anim(name, length=T, loop=loop)
    for leg in STAG_LEGS:
        fore = leg.startswith("fore")
        lag = 0.0 if fore else 0.03
        for j in range(3):
            a.rot(f"{leg}_{j + 1}", {round(min(T, (t + (lag if 0 < t < 1 else 0)) * T), 4): (stag_leg(fore, ph)[j], 0, 0)
                                    for t, ph in keys})
    a.pos("body", {round(t * T, 4): (0, y, 0) for t, y in lift_keys.items()})
    return a


def stag_anims():
    A = []
    life = Anim("life", loop=True)
    life.rot("tilt", (tilt_expr(), 0, 0))
    for k in range(3):
        life.rot(f"veil{k + 1}", (LIFE(12, 1.6, k * 0.2), 0, LIFE(6, 2.3, k * 0.3)))
    life.rot("tail", (LIFE(10, 0.9), 0, 0))
    life.scl("body_g", LIFE(0.025, 2.6, base=1.0))
    for s in ("r", "l"):
        life.rot(f"antler_{s}_3", (0, 0, LIFE(2, 3.1, 0.3 if s == "r" else 0)))
    A.append(life)
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    arrive = Anim("arrive", length=1.2, loop="hold")      # the frame is drawn in light, then mist-glass condenses
    arrive.scl("root", {0: (1.0, 0.0, 1.0), 0.35: (1.0, 1.05, 1.0), 0.45: 1.0, 1.2: 1.0})
    for g in STAG_GLASS:
        arrive.scl(g, {0: 0.0, 0.35: 0.0, 0.75: 1.15, 0.95: 1.0, 1.2: 1.0})
    for s in ("r", "l"):
        for j in (1, 2, 3):
            arrive.scl(f"antler_{s}_{j}", {0: 0.0, 0.5 + j * 0.12: 0.0, 0.62 + j * 0.12: 1.15, 0.75 + j * 0.12: 1.0})
    arrive.rot("neck1", {0: (20, 0, 0), 0.75: (20, 0, 0), 1.0: (-12, 0, 0), 1.2: (0, 0, 0)})
    arrive.rot("head", {0: (10, 0, 0), 0.9: (10, 0, 0), 1.1: (-14, 0, 0), 1.2: (0, 0, 0)})
    arrive.sound(0.6, "bell")
    A.append(arrive)

    par = stag_bound("parade", 1.0,
                     [(0, "land"), (0.12, "crouch"), (0.24, "push"), (0.4, "tuck"), (0.68, "tuck"), (0.82, "reach"),
                      (0.94, "land"), (1.0, "land")],
                     {0: -2.0, 0.12: -3.5, 0.24: 3, 0.4: 12, 0.55: 14, 0.7: 11, 0.85: 2, 0.94: -1.5, 1.0: -2.0}, True)
    par.rot("body", cyc(1.0, lambda p: (6 * math.sin(2 * math.pi * (p - 0.25)), 0, 0)))
    par.rot("neck1", cyc(1.0, lambda p: (-8 * math.sin(2 * math.pi * (p - 0.3)), 0, 0)))
    par.sound(0.94, "step")
    par.particle(0.95, "mistpuff", locator="hoof_fore_r")
    par.particle(0.97, "mistpuff", locator="hoof_hind_l")
    A.append(par)

    # one leap = 1.1 s (22 ticks): crouch, launch at 0.25, hang, land at 0.85 (hit frame), recover
    def leap(nm):
        a = stag_bound(nm, 1.1,
                       [(0, "stand"), (0.2, "crouch"), (0.3, "push"), (0.45, "tuck"), (0.68, "tuck"), (0.75, "reach"),
                        (0.78, "land"), (0.92, "crouch"), (1.0, "stand")],
                       {0: 0, 0.2: -5, 0.3: 2, 0.5: 4, 0.7: 2, 0.78: -3, 0.9: -2, 1.0: 0}, "hold")
        a.rot("body", {0: (0, 0, 0), 0.2: (-8, 0, 0), 0.3: (14, 0, 0), 0.55: (0, 0, 0), 0.72: (-14, 0, 0), 0.8: (4, 0, 0), 1.1: (0, 0, 0)})
        a.rot("neck1", {0: (0, 0, 0), 0.2: (16, 0, 0), 0.4: (-18, 0, 0), 0.72: (-6, 0, 0), 0.82: (22, 0, 0), 1.1: (0, 0, 0)})
        a.rot("head", {0: (0, 0, 0), 0.2: (-10, 0, 0), 0.82: (18, 0, 0), 1.1: (0, 0, 0)})
        a.scl("body_g", {0: 1.0, 0.78: 1.0, 0.83: (1.12, 0.92, 1.12), 0.95: 1.0})
        a.sound(0.3, "step")
        a.particle(0.86, "mistpuff", locator="hoof_fore_r")
        a.particle(0.86, "mistpuff", locator="hoof_hind_l")
        return a
    A.append(leap("leap_a"))
    A.append(leap("leap_b"))

    depart = Anim("depart", length=1.2, loop="hold")       # lifts its head, the glass mists away, the frame unthreads
    depart.rot("neck1", {0: (0, 0, 0), 0.4: (-24, 0, 0), 1.2: (-24, 0, 0)})
    depart.rot("head", {0: (0, 0, 0), 0.4: (-20, 0, 0), 1.2: (-20, 0, 0)})
    for g in STAG_GLASS:
        depart.scl(g, {0: 1.0, 0.35: 1.0, 0.7: 1.35, 0.9: 0.0})
    depart.pos("root", {0: (0, 0, 0), 0.5: (0, 2, 0), 1.2: (0, 22, 0)})
    depart.scl("root", {0: 1.0, 0.7: 1.0, 1.2: (0.2, 1.6, 0.2)})
    depart.scl("root", {0: 1.0, 0.7: 1.0, 1.05: (0.3, 1.5, 0.3), 1.2: 0.0})
    A.append(depart)
    return A


STAG_STATES = {0: ["hidden"], 1: ["arrive"], 2: ["parade"], 3: ["leap_a"], 4: ["leap_b"], 5: ["depart"]}


# ================================================================= 3. CURTAIN-WINGED BIRD
def bird_model():
    m = Model("dn_parade_bird", density=1.0, bounds=(8, 6, (0, 0, 0)))
    body_m = tex.sgrad("#fbf6ee", "#d9e6f6", axis="y", lo=-6, hi=6, glow0=0.05, glow1=0.15)
    pm = porc(crack=0.3)
    velvet = curtain("#e8b4c8", "#b9809b", key="velvet")
    lining = curtain("#ffd9b8", "#e8b494", fringe="#ffffff", folds=2.0, key="lining")
    valance = tex.trimmed(tex.fabric("#c98aa6", "#d9a0b8", stripe_w=2, glow=0.1, fringe=True), SGOLD, 1, 0, glow=0.5)
    rod = tex.metal("#e6c77e", "#fff4d0", "#9a7838", bands=2.0, glow=0.3)
    tassel = tex.vgrad("#ffe6a0", "#d9a94a", glow_top=0.4, glow_bottom=0.2)
    star = tex.shaped(tex.m_star(5, 0.45), "#fff3c4", SGOLD, glow=1.0, var=0, key="bstar")
    moon = tex.shaped(tex.m_crescent(0.4), "#fff3c4", SGOLD, glow=1.0, var=0, key="bmoon")
    eye = ["     ", " ### ", "#   #", "     "]
    head_m = tex.stamped(porc(crack=0.0), eye, "#6a5a7a", key="beye")

    root = m.bone("root")
    tilt = m.bone("tilt", root)
    body = m.bone("body", tilt, pivot=(0, 0, 0))
    body.box((0, 0, 0), (8, 7.5, 14), body_m)
    body.box((0, -0.4, -7.6), (7.4, 7, 3.4), pm)                        # breast
    body.box((0, 3.9, 0), (6.5, 0.8, 10), tex.trimmed(tex.fabric("#bcd6f0", "#cfe2f6", stripe_w=2), SGOLD, 1, 0, 0.4))
    body.box((0, -3.8, -1), (5, 1, 8), tex.vgrad("#e8dfd2", "#cfc3b0"))
    for sx in (1, -1):                                                   # tucked gilt feet
        body.box((sx * 1.6, -5, 2), (1, 2.6, 1), GILT)
        body.box((sx * 1.6, -6.2, 1.2), (1.6, 0.6, 2.4), GILT, variant=1)
    body.locator("heart", (0, 0, 0))

    n1 = m.bone("neck1", body, pivot=(0, 1.5, -8.5), rot=(-50, 0, 0))
    n1.box((0, 4.5, -8.5), (4.0, 6.5, 4.2), pm, variant=1)
    n2 = m.bone("neck2", n1, pivot=(0, 7.5, -8.5), rot=(30, 0, 0))
    n2.box((0, 10.5, -8.5), (3.4, 6.5, 3.6), pm, variant=2)
    head = m.bone("head", n2, pivot=(0, 13.5, -8.5), rot=(30, 0, 0))
    head.box((0, 15.5, -9.0), (4.2, 4.4, 5.4), head_m, density=2)
    head.box((0, 15.0, -13.4), (1.6, 1.4, 4.2), GILT)                   # beak
    head.box((0, 14.4, -14.8), (1.0, 0.8, 2.0), GILT_B)
    head.box((0, 17.9, -9.0), (4.4, 0.8, 5.6), GILT, variant=1)         # little crown band
    for k in range(3):
        head.box((-1.4 + k * 1.4, 19, -9.0), (0.8, 1.6, 0.8), GILT_B, variant=k)
    head.plane("z", (0, 21.6, -9.0), 3, 3, moon)
    crest = m.bone("crest", head, pivot=(0, 18, -7))
    for k, c in enumerate((PINK, PEACH, PBLUE)):
        f = tex.feather(c, "#ffffff", SGOLD, glow=0.1, glow_tip=0.45)
        crest.box((-1.5, 18, -7 + k * 1.4), (3, 9, 0), f, rot=(-130 + k * 18, 0, 0), pivot=(0, 18, -7 + k * 1.4),
                  faces=("north", "south"), variant=k)

    # wings: curtain rods with rings and valance; curtains hang from them; tassels at the corners
    for s, sx in (("r", 1), ("l", -1)):
        x0 = sx * 3.5
        segs = [(f"wing_{s}_1", 15), (f"wing_{s}_2", 14)]
        par = "body"
        x = x0
        for wi, (nm, L) in enumerate(segs):
            b = m.bone(nm, par, pivot=(x, 2.5, -3))
            xa, xb = (x, x + sx * L)
            cx = (xa + xb) / 2
            b.box((cx, 2.5, -3), (L, 1.3, 1.3), rod, variant=wi)
            for k in range(4):
                rx = xa + sx * L * (k + 0.5) / 4
                b.box((rx, 2.5, -3), (0.6, 2.4, 2.4), GILT, variant=k % 2)          # curtain rings
            b.plane("z", (cx, 1.0, -3.9), L, 3.0, valance, variant=wi)              # valance on the front
            # two curtain panels per rod segment, each its own bone
            for k in range(2):
                px_ = xa + sx * L * (0.25 + 0.5 * k)
                cb = m.bone(f"cur_{s}_{wi + 1}_{k + 1}", b.name, pivot=(px_, 1.5, -3))
                h = 15 - wi * 2 - k * 1.5
                cb.plane("z", (px_, 1.5 - h / 2, -3), L / 2 + 0.4, h, velvet, variant=wi * 2 + k,
                         mats={"south": lining})
                if wi == 1 and k == 1:                                   # tassel on the outer corner
                    cb.box((xb - sx * 0.5, 1.5 - h - 1.0, -3), (0.4, 2.0, 0.4), GILT)
                    cb.box((xb - sx * 0.5, 1.5 - h - 3.2, -3), (1.6, 2.6, 1.6), tassel)
            x = xb
            par = b.name
        fin = m.bone(f"finial_{s}", f"wing_{s}_2", pivot=(x, 2.5, -3))
        fin.box((x + sx * 0.9, 2.5, -3), (1.8, 1.8, 1.8), GILT_B, rot=(45, 0, 45), pivot=(x + sx * 0.9, 2.5, -3))
        fin.plane("z", (x + sx * 2.8, 2.5, -3), 3.4, 3.4, star)
        fin.locator(f"wingtip_{s}", (x + sx * 2.8, 2.5, -3))

    # tail: a train of three curtain ribbons with tassels
    prev = "body"
    for j in range(3):
        z = 7 + j * 6
        b = m.bone(f"tail{j + 1}", prev, pivot=(0, 1, z), rot=((8 if j == 0 else 4), 0, 0))
        b.plane("y", (0, 1, z + 3), 7 - j * 1.5, 6.4, velvet, variant=j, mats={"down": lining})
        b.box((0, 1, z + 3), (0, 3.5, 6.4), lining, faces=("east", "west"), variant=j)
        prev = b.name
    b.box((0, 0.2, 25.5), (1.8, 2.4, 1.8), tassel)
    return m


def bird_anims():
    A = []
    life = Anim("life", loop=True)
    life.rot("tilt", (tilt_expr(), 0, 0))
    wave(life, ["tail1", "tail2", "tail3"], 0, 7, 1.4, lag=0.15, grow=1.2, clock="q.life_time")
    life.rot("crest", (LIFE(6, 1.2), 0, 0))
    life.rot("neck1", (LIFE(3, 2.4), 0, 0))
    life.rot("finial_r", (spin(120), 0, 0))
    life.rot("finial_l", (spin(-120), 0, 0))
    A.append(life)
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    curtains = [f"cur_{s}_{w}_{k}" for s in "rl" for w in (1, 2) for k in (1, 2)]

    def curt(a, rx_fn, lagstep=0.07):
        """rx_fn(i) -> channel value for curtain panel i (inner->outer)."""
        for s in "rl":
            for i, (w, k) in enumerate(((1, 1), (1, 2), (2, 1), (2, 2))):
                a.rot(f"cur_{s}_{w}_{k}", rx_fn(i))

    # glide: wings spread, curtains streaming back and billowing in travelling waves; gentle bank
    glide = Anim("glide", loop=True, length=2.4)
    sym(glide, "wing_{s}_1", rot=(0, LIFE(4, 4.8), LIFE(9, 2.4, 0.0, base=8)))
    sym(glide, "wing_{s}_2", rot=(0, LIFE(3, 4.8, 0.1), LIFE(7, 2.4, -0.12, base=-4)))
    curt(glide, lambda i: (LIFE(10, 1.2, -i * 0.12, base=-68), 0, LIFE(4, 0.8, -i * 0.1)))
    glide.rot("body", (LIFE(4, 2.4, 0.25), 0, LIFE(10, 4.8)))
    glide.pos("body", (0, LIFE(1.5, 2.4, 0.1), 0))
    glide.sound(0.0, "flap")
    A.append(glide)

    def swoop(nm):
        a = Anim(nm, length=1.2, loop="hold")            # rise, fold back, dive, skim, pull up wide
        sym(a, "wing_{s}_1", rot={0: (0, 0, 8), 0.25: (0, -38, 26), 0.45: (0, -52, 4), 0.7: (0, -46, 0), 0.9: (0, 6, 30), 1.2: (0, 0, 8)})
        sym(a, "wing_{s}_2", rot={0: (0, 0, -4), 0.25: (0, -20, -10), 0.45: (0, -30, -2), 0.9: (0, 0, -16), 1.2: (0, 0, -4)})
        curt(a, lambda i: {0: (-68, 0, 0), 0.25: (-60 + i * 3, 0, 0), 0.45: (-86, 0, 0), 0.7: (-84, 0, 0), 0.9: (-30 - i * 6, 0, 0), 1.2: (-68, 0, 0)})
        a.rot("body", {0: (0, 0, 0), 0.25: (14, 0, 12), 0.45: (-30, 0, -14), 0.7: (-6, 0, -18), 0.9: (22, 0, 8), 1.2: (0, 0, 0)})
        a.rot("neck1", {0: (0, 0, 0), 0.45: (18, 0, 0), 0.7: (10, 0, 0), 1.2: (0, 0, 0)})
        a.rot("head", {0: (0, 0, 0), 0.45: (-24, 0, 0), 0.7: (-10, 0, 0), 1.2: (0, 0, 0)})
        a.sound(0.35, "flap")
        a.particle(0.6, "ribbon", locator="wingtip_r")
        a.particle(0.6, "ribbon", locator="wingtip_l")
        return a
    A.append(swoop("swoop_a"))
    A.append(swoop("swoop_b"))

    # arrival: a closed theatre curtain (rods swept forward, curtains hanging) that draws open into wings
    CLOSED_W1, CLOSED_W2 = (0, 78, -6), (0, 30, 0)
    arrive = Anim("arrive", length=1.3, loop="hold")
    arrive.scl("root", {0: 0.0, 0.2: 1.05, 0.3: 1.0})
    sym(arrive, "wing_{s}_1", rot={0: CLOSED_W1, 0.5: CLOSED_W1, 0.9: (0, -10, 20), 1.3: (0, 0, 8)})
    sym(arrive, "wing_{s}_2", rot={0: CLOSED_W2, 0.5: CLOSED_W2, 1.0: (0, 0, -6), 1.3: (0, 0, -4)})
    curt(arrive, lambda i: {0: (0, 0, 0), 0.5: (0, 0, 0), 0.75: (12, 0, 0), 1.0: (-40, 0, 0), 1.3: (-68, 0, 0)})
    arrive.scl("head", {0: 0.0, 0.45: 0.0, 0.7: 1.15, 0.85: 1.0})
    arrive.sound(0.5, "flap")
    A.append(arrive)

    depart = Anim("depart", length=1.2, loop="hold")     # curtain call: the curtains draw closed, then it rises away
    sym(depart, "wing_{s}_1", rot={0: (0, 0, 8), 0.45: CLOSED_W1, 1.2: CLOSED_W1})
    sym(depart, "wing_{s}_2", rot={0: (0, 0, -4), 0.45: CLOSED_W2, 1.2: CLOSED_W2})
    curt(depart, lambda i: {0: (-68, 0, 0), 0.45: (6, 0, 0), 0.6: (0, 0, 0), 1.2: (0, 0, 0)})
    depart.rot("body", {0: (0, 0, 0), 0.5: (16, 0, 0), 0.65: (0, 0, 0), 1.2: (0, 0, 0)})   # a bow
    depart.pos("root", {0: (0, 0, 0), 0.65: (0, 0, 0), 1.2: (0, 30, 0)})
    depart.scl("root", {0: 1.0, 0.65: 1.0, 1.0: (0.6, 1.1, 0.6), 1.2: 0.0})
    A.append(depart)
    return A


BIRD_STATES = {0: ["hidden"], 1: ["arrive"], 2: ["glide"], 3: ["swoop_a"], 4: ["swoop_b"], 5: ["depart"]}


# ================================================================= 4. FLOATING STAR DOLL
def doll_model():
    m = Model("dn_parade_doll", density=1.0, bounds=(5, 6, (0, 2, 0)))
    pm = porc(crack=0.25)
    dress = tex.trimmed(tex.fabric("#bcd6f0", "#d6e6f8", stripe_w=2, glow=0.1), SGOLD, 1, 0, glow=0.5)
    ruff = tex.fabric("#fff6f0", "#ffe6ee", stripe_w=1, glow=0.15, fringe=True)
    joint = tex.metal("#f0d78e", "#fffbe6", "#b08a3e", bands=2.0, glow=0.4)
    hair = tex.mottled("#f3c78e", "#ffd9b8", scale=2.0, glow=0.08)
    star_pt = tex.sgrad("#fff6dc", "#f0c86a", axis="y", lo=0, hi=12, glow0=0.35, glow1=0.9)
    shoe = tex.metal("#e8b4c8", "#fff0f6", "#a8708a", bands=2.0, glow=0.2)
    sm_star = tex.shaped(tex.m_star(5, 0.45), "#fff3c4", SGOLD, glow=1.0, var=0, key="dstar")
    thread = tex.glow_flat("#fff0c8", 0.9)
    face = ["          ", "          ", " ##    ## ", "#  #  #  #", "          ", "          ",
            "          ", "    ##    ", "          ", "          "]
    face_m = tex.stamped(tex.stamped(porc(crack=0.0), face, "#6a5070", key="dface"),
                         ["##      ##", "##      ##"], "#f2a8b8", offset=(0, 2), key="dcheek")
    root = m.bone("root")
    tilt = m.bone("tilt", root)
    spinb = m.bone("spin", tilt, pivot=(0, 22, 0))
    sway = m.bone("sway", spinb, pivot=(0, 30, 0))
    body = m.bone("body", sway, pivot=(0, 22, 0))
    body.box((0, 23, 0), (5.6, 8, 4.2), dress)
    body.box((0, 27.6, 0), (7, 1.2, 5.4), ruff)                          # collar ruff
    body.box((0, 19.0, 0), (6.4, 1.4, 5.0), ruff, variant=1)             # waist frill
    body.box((0, 23.5, -2.3), (1.6, 1.6, 0.6), tex.glow_flat("#ffe9a8", 1.0, core="#ffffff"))   # star brooch
    body.locator("heart", (0, 23, 0))
    # five-point star body
    for k in range(5):
        a = k * 72
        sb = m.bone(f"star{k + 1}", body, pivot=(0, 23, 1.6), rot=(0, 0, a))
        sb.box((0, 29.5, 1.6), (4.6, 7, 1.2), star_pt, variant=k % 2)
        sb.box((0, 34.5, 1.6), (2.4, 4, 1.0), star_pt, variant=2)
        sb.box((0, 37.0, 1.6), (1.2, 1.4, 1.2), tex.glow_flat("#ffffff", 1.0, core="#ffffff"))
    sbk = m.bone("star_core", body, pivot=(0, 23, 2.4))
    sbk.box((0, 23, 2.4), (8, 8, 1.0), tex.trimmed(tex.flat("#fff3d0", glow=0.6), SGOLD, 1, 0, 0.9), rot=(0, 0, 45))

    head = m.bone("head", body, pivot=(0, 28.5, 0))
    head.box((0, 29.4, 0), (2.2, 1.6, 2.2), joint)
    head.box((0, 33.8, 0), (8, 7.6, 7.2), pm, mats={"north": face_m}, density=2)
    head.box((0, 37.9, 0.6), (8.6, 1.6, 7.8), hair)                       # hair cap
    head.box((0, 34.5, 3.6), (8.4, 6, 1.2), hair, variant=1)             # back hair
    for sx in (1, -1):
        for k in range(3):                                               # ringlets
            head.box((sx * 4.4, 35 - k * 2.4, 1.4), (1.4, 2.2, 1.4), hair, variant=k)
    tiara = m.bone("tiara", head, pivot=(0, 38.8, 0))
    for k in range(3):
        tiara.plane("z", (-3 + k * 3, 40.0 + (1.2 if k == 1 else 0), -2.0), 2.6 + (1.0 if k == 1 else 0),
                    2.6 + (1.0 if k == 1 else 0), sm_star)
    halo = m.bone("halo", head, pivot=(0, 34, 4.5))
    for k in range(8):
        a = math.radians(k * 45)
        halo.plane("z", (math.cos(a) * 8.5, 34 + math.sin(a) * 8.5, 4.5), 2.6, 2.6, sm_star)

    # dangling ball-jointed limbs
    for s, sx in (("r", 1), ("l", -1)):
        sh = m.bone(f"arm_{s}_1", body, pivot=(sx * 3.6, 26.4, 0))
        sh.box((sx * 3.6, 26.4, 0), (2.2, 2.2, 2.2), joint)
        sh.box((sx * 3.7, 23.3, 0), (1.8, 4.6, 1.8), pm)
        el = m.bone(f"arm_{s}_2", sh, pivot=(sx * 3.7, 20.6, 0))
        el.box((sx * 3.7, 20.6, 0), (1.7, 1.7, 1.7), joint, variant=1)
        el.box((sx * 3.7, 17.8, 0), (1.6, 4.4, 1.6), pm, variant=1)
        el.box((sx * 3.7, 15.0, 0), (1.9, 2.2, 1.3), pm, variant=2)
        el.locator(f"hand_{s}", (sx * 3.7, 14.5, 0))
        hp = m.bone(f"leg_{s}_1", body, pivot=(sx * 1.6, 18.6, 0))
        hp.box((sx * 1.6, 18.4, 0), (2.2, 2.2, 2.2), joint, variant=1)
        hp.box((sx * 1.6, 15.0, 0), (2.2, 5.2, 2.2), pm, variant=1)
        kn = m.bone(f"leg_{s}_2", hp, pivot=(sx * 1.6, 12.2, 0))
        kn.box((sx * 1.6, 12.2, 0), (2.0, 2.0, 2.0), joint)
        kn.box((sx * 1.6, 9.0, 0), (1.9, 5.0, 1.9), pm, variant=2)
        kn.box((sx * 1.6, 5.8, -0.6), (2.3, 1.8, 3.4), shoe)
        kn.box((sx * 1.6, 6.4, -2.5), (1.0, 1.0, 1.0), tex.glow_flat("#fff3f8", 0.6))

    # the marionette control bar - no strings, only cut thread ends drifting below it
    ctl = m.bone("control", root, pivot=(0, 52, 0))
    ctl.box((0, 52, 0), (14, 1.0, 1.0), GILT)
    ctl.box((0, 52, 0), (1.0, 1.0, 9), GILT, variant=1)
    ctl.box((0, 53.2, 0), (1.6, 1.6, 1.6), GILT_B, rot=(45, 45, 0))
    for k, (x, z) in enumerate(((-6.5, 0), (6.5, 0), (0, -4), (0, 4))):
        ctl.box((x, 49.8 - k % 2, z), (0.25, 4 + (k % 2) * 2, 0.25), thread)
    return m


def doll_anims():
    A = []
    life = Anim("life", loop=True)
    life.rot("tilt", (tilt_expr(), 0, 0))
    life.rot("halo", (0, 0, spin(40)))
    life.pos("control", (LIFE(1.2, 3.3), LIFE(1.6, 2.1), 0))
    life.rot("control", (LIFE(6, 2.7), spin(25), LIFE(8, 3.1)))
    for k in range(5):
        life.scl(f"star{k + 1}", LIFE(0.05, 1.6, k * 0.2, base=1.0))
    life.pos("body", (0, LIFE(0.8, 2.4, 0.3), 0))
    A.append(life)
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    # float: tick . tock . (stillness) . slow spin - syncopated; limbs swing a beat late
    T = 2.4
    fl = Anim("float", loop=True, length=T)
    fl.rot("sway", {0: (0, 0, 0), 0.16: (0, 0, 0), 0.2: (0, 0, 15), 0.56: (0, 0, 15), 0.6: (0, 0, -13), 0.96: (0, 0, -13),
                    1.0: (0, 0, 0), T: (0, 0, 0)}, smooth=False)
    fl.rot("spin", {0: (0, 0, 0), 1.45: (0, 0, 0), T: (0, 360, 0)}, smooth=False)
    for s, sg in (("r", 1), ("l", -1)):
        lag = 0.04 if s == "r" else 0.0
        fl.rot(f"arm_{s}_1", {0: (0, 0, 0), 0.2 + lag: (6, 0, -22), 0.4: (-4, 0, -8), 0.6 + lag: (-6, 0, 20), 0.8: (4, 0, 6),
                              1.0 + lag: (0, 0, -10), 1.3: (0, 0, 2), 1.6: (0, 0, sg * 8), T: (0, 0, 0)})
        fl.rot(f"arm_{s}_2", {0: (0, 0, 0), 0.25: (-14, 0, -10), 0.65: (-6, 0, 14), 1.05: (-10, 0, -4), 1.6: (-20, 0, sg * 6), T: (0, 0, 0)})
        fl.rot(f"leg_{s}_1", {0: (0, 0, 0), 0.24 + lag: (-8, 0, -18), 0.64 + lag: (8, 0, 16), 1.04: (0, 0, -6), 1.4: (0, 0, 0),
                              1.9: (14, 0, sg * 4), T: (0, 0, 0)})
        fl.rot(f"leg_{s}_2", {0: (0, 0, 0), 0.3: (16, 0, 0), 0.7: (6, 0, 0), 1.1: (12, 0, 0), 1.9: (30, 0, 0), T: (0, 0, 0)})
    fl.rot("head", {0: (0, 0, 0), 0.36: (0, 0, 0), 0.4: (0, -12, -16), 0.76: (0, -12, -16), 0.8: (0, 14, 12), 1.16: (0, 14, 12),
                    1.2: (0, 0, 0), T: (0, 0, 0)}, smooth=False)
    fl.sound(0.2, "tick")
    fl.sound(0.6, "tick")
    fl.sound(1.0, "tick")
    A.append(fl)

    def pulse(nm):
        a = Anim(nm, length=0.5, loop="hold")             # starburst: limbs fling out, the star flares
        sym(a, "arm_{s}_1", rot={0: (0, 0, 0), 0.08: (0, 0, 20), 0.16: (0, 0, 118), 0.32: (0, 0, 108), 0.5: (0, 0, 30)})
        sym(a, "arm_{s}_2", rot={0: (0, 0, 0), 0.16: (0, 0, 14), 0.5: (0, 0, 0)})
        sym(a, "leg_{s}_1", rot={0: (0, 0, 0), 0.16: (0, 0, 36), 0.32: (0, 0, 30), 0.5: (0, 0, 8)})
        for k in range(5):
            a.scl(f"star{k + 1}", {0: 1.0, 0.16: 1.55, 0.3: 1.4, 0.5: 1.0})
        a.scl("star_core", {0: 1.0, 0.14: 1.8, 0.5: 1.0})
        a.scl("halo", {0: 1.0, 0.16: 1.5, 0.5: 1.0})
        a.rot("head", {0: (0, 0, 0), 0.16: (-14, 0, 0), 0.5: (0, 0, 0)})
        a.pos("body", {0: (0, 0, 0), 0.06: (0, -1.5, 0), 0.16: (0, 2.0, 0), 0.5: (0, 0, 0)})
        a.particle(0.15, "starpop", locator="heart")
        return a
    A.append(pulse("pulse_a"))
    A.append(pulse("pulse_b"))

    arrive = Anim("arrive", length=1.3, loop="hold")       # a falling star unfolds: points first, limbs drop one by one
    arrive.scl("root", {0: 0.0, 0.15: 0.8, 0.3: 1.0})
    arrive.rot("spin", {0: (0, -540, 0), 0.6: (0, 0, 0)})
    for i, (b, t0) in enumerate((("head", 0.45), ("arm_r_1", 0.6), ("leg_l_1", 0.72), ("arm_l_1", 0.84), ("leg_r_1", 0.95))):
        arrive.scl(b, {0: 0.0, t0: 0.0, t0 + 0.12: 1.15, t0 + 0.22: 1.0})
    arrive.scl("control", {0: 0.0, 1.0: 0.0, 1.3: 1.0})
    arrive.sound(0.6, "tick")
    A.append(arrive)

    depart = Anim("depart", length=1.2, loop="hold")       # spins up, folds back into a star, the star winks out
    depart.rot("spin", {0: (0, 0, 0), 1.2: (0, 900, 0)})
    for b in ("head", "arm_r_1", "arm_l_1", "leg_r_1", "leg_l_1"):
        depart.scl(b, {0: 1.0, 0.4: 1.0, 0.7: 0.0})
    depart.scl("control", {0: 1.0, 0.3: 0.0})
    depart.scl("root", {0: 1.0, 0.8: 1.0, 0.95: 1.4, 1.2: 0.0})
    A.append(depart)
    return A


DOLL_STATES = {0: ["hidden"], 1: ["arrive"], 2: ["float"], 3: ["pulse_a"], 4: ["pulse_b"], 5: ["depart"]}


# ================================================================= the dream-road (4 kinds)
ROAD_L, ROAD_W = 56, 44   # units (3.5 x 2.75 blocks); deck top at y = 0


def road_model(kind):
    names = ["dn_parade_road", "dn_parade_road_arch", "dn_parade_road_banner", "dn_parade_road_cloud"]
    m = Model(names[kind], density=1.0, bounds=(8, 8, (0, 1, 0)))
    flag = flagstones()
    under = tex.sgrad("#f3dfe8", "#c9c2ea", axis="y", lo=-4, hi=0, glow0=0.3, glow1=0.15)
    side = tex.trimmed(tex.vgrad("#f7ecd8", "#e8c9b8", glow_top=0.3, glow_bottom=0.2), SGOLD, 1, 0, glow=0.6)
    cloud = tex.mottled("#fffaf4", "#e2e8f8", scale=3.0, glow=0.25, edge_dark=0.04)
    lantern = tex.glow_flat("#ffd9a0", 1.0, core="#fff8e0")
    pm = porc(crack=0.4)
    root = m.bone("root")
    tilt = m.bone("tilt", root)
    deck = m.bone("deck", tilt, pivot=(0, 0, ROAD_L / 2))
    deck.box((0, -1.5, 0), (ROAD_W, 3, ROAD_L), side, mats={"up": flag, "down": under})
    for sx in (1, -1):                                                  # bunting under the edges
        deck.plane("x", (sx * (ROAD_W / 2 + 0.1), -5.0, 0), ROAD_L, 4, bunting())
    deck.locator("mid", (0, 1, 0))
    und = m.bone("under", deck, pivot=(0, -3, 0))
    for k, (x, z, w) in enumerate(((-10, -16, 14), (12, -4, 16), (-4, 10, 18), (14, 20, 10), (-16, 22, 9))):
        und.box((x, -5, z), (w, 4, w * 0.8), cloud, variant=k % 3)
        und.box((x + 2, -7.5, z + 1), (w * 0.6, 3, w * 0.5), cloud, variant=(k + 1) % 3)
    roll = m.bone("roll", tilt, pivot=(0, 2.4, ROAD_L / 2))
    roll.box((0, 2.4, ROAD_L / 2), (ROAD_W + 1, 4.8, 4.8), side, rot=(45, 0, 0))
    for s, sx in (("r", 1), ("l", -1)):
        x = sx * (ROAD_W / 2 - 1.2)
        r = m.bone(f"rail_{s}", tilt, pivot=(x, 0, 0))
        for k, z in enumerate((-24, -8, 8, 24)):
            r.box((x, 3.5, z), (1.6, 7, 1.6), GILT, variant=k % 2)
            r.box((x, 7.6, z), (2.4, 1.2, 2.4), GILT_B, variant=k % 2)
        r.box((x, 6.4, 0), (1.0, 1.0, ROAD_L - 2), GILT)
        r.box((x, 2.8, 0), (0.6, 0.6, ROAD_L - 2), GILT, variant=1)
        ln = m.bone(f"lantern_{s}", r.name, pivot=(x, 8.2, -24))
        ln.box((x, 9.6, -24), (0.4, 3, 0.4), GILT)
        ln.box((x, 12.6, -24), (3, 3.6, 3), lantern)
        ln.box((x, 14.8, -24), (3.6, 0.8, 3.6), GILT_B)
        ln.box((x, 10.4, -24), (3.6, 0.8, 3.6), GILT_B, variant=1)
    if kind == 1:   # moon-arch to pass under
        arch = m.bone("arch", tilt, pivot=(0, 0, 0))
        col = tex.banded(pm, SGOLD, every=8, width=1, glow=0.5)
        for sx in (1, -1):
            arch.box((sx * 25, 21, 0), (4.5, 42, 4.5), col)
            arch.box((sx * 25, 1.5, 0), (6.5, 3, 6.5), GILT)
            arch.box((sx * 25, 42.5, 0), (6, 2, 6), GILT, variant=1)
        ring(arch, (0, 43, 0), 25, 12, (7.2, 4.4, 4.4), pm, axis="z", start=0, sweep=180)
        ring(arch, (0, 43, 0), 22.2, 12, (6.2, 1.0, 4.8), GILT_B, axis="z", start=0, sweep=180)
        arch.plane("z", (0, 75, 0), 14, 14, tex.shaped(tex.m_crescent(0.38), "#fff3c4", SGOLD, glow=1.0, var=0,
                                                         outline="#d9a94a", key="archmoon"))
        pend = m.bone("pendant", arch, pivot=(0, 63, 0))
        pend.box((0, 59, 0), (0.4, 8, 0.4), GILT)
        pend.plane("z", (0, 53.5, 0), 5, 5, tex.shaped(tex.m_star(5, 0.45), "#fff3c4", SGOLD, glow=1.0, var=0, key="pstar"))
        pend.plane("x", (0, 53.5, 0), 5, 5, tex.shaped(tex.m_star(5, 0.45), "#fff3c4", SGOLD, glow=1.0, var=0, key="pstar"))
    elif kind == 2:  # ceremonial banners outside the rails
        for s, sx in (("r", 1), ("l", -1)):
            p = m.bone(f"pole_{s}", tilt, pivot=(sx * 25, 0, 0))
            p.box((sx * 25, 26, 0), (1.8, 52, 1.8), tex.banded(GILT, IVORY, every=6, width=2))
            p.box((sx * 29, 50, 0), (9, 1.2, 1.2), GILT)
            p.plane("z", (sx * 25, 56, 0), 6, 6, tex.shaped(tex.m_crescent(0.4), "#fff3c4", SGOLD, glow=1.0, var=0, key="polemoon"))
            emblem = ["   #   ", "  ###  ", " ##### ", "  ###  ", "   #   "] if s == "r" else \
                ["  ###  ", " ##    ", "##     ", " ##    ", "  ###  "]
            bmat = tex.stamped(tex.fabric(PINK if s == "r" else PBLUE, None, glow=0.15), emblem, "#fff3c4", glow=0.9,
                               scale=1, key=f"banner{s}")
            prev = p.name
            for j in range(3):
                y = 49.4 - j * 6
                b = m.bone(f"banner_{s}{j + 1}", prev, pivot=(sx * 29.5, y, 0))
                b.plane("z", (sx * 29.5, y - 3, 0), 8, 6, bmat if j == 1 else tex.fabric(PINK if s == "r" else PBLUE, None, glow=0.15),
                        variant=j)
                prev = b.name
            tail = tex.shaped(lambda u, v: (np.abs(u) * 0.9 < (v + 1) / 2 + 0.15) * 1.0 * ((v > -0.2) | (np.abs(u) > 0.25)),
                              PINK if s == "r" else PBLUE, SGOLD, glow=0.2, var=0, key=f"bntail{s}")
            m.bones[prev].plane("z", (sx * 29.5, y - 9, 0), 8, 6, tail)
    elif kind == 3:  # little cloud terraces with miniature celestial decorations
        for s, sx in (("r", 1), ("l", -1)):
            c = m.bone(f"cloud_{s}", tilt, pivot=(sx * 30, -4, 0))
            for k, (dx, dy, dz, w) in enumerate(((0, -4, 0, 14), (3, 0, -8, 10), (-2, 2, 9, 9), (2, 5, 2, 8))):
                c.box((sx * (30 + dx), dy, dz), (w, 4.5, w * 0.9), cloud, variant=k % 3)
            orb = m.bone(f"orbit_{s}", c.name, pivot=(sx * 30, 12, 0))
            orb.box((sx * 30, 9, 0), (0.5, 6, 0.5), GILT)
            ring(orb, (sx * 30, 12, 0), 6, 10, (3.6, 0.4, 0.4), GILT_B, axis="y")
            orb.box((sx * 30, 12, 0), (3.2, 3.2, 3.2), tex.glow_flat("#ffe9a8", 1.0, core="#ffffff"))
            for k, col in enumerate(("#bcd6f0", "#e8b4c8", "#cdbfe8")):
                a = math.radians(k * 120 + 20)
                orb.box((sx * 30 + math.cos(a) * 6, 12, math.sin(a) * 6), (1.8, 1.8, 1.8),
                        tex.glow_flat(col, 0.6, core="#ffffff"), variant=k)
            orb.plane("z", (sx * 30, 18.5, 0), 4, 4, tex.shaped(tex.m_star(5, 0.45), "#fff3c4", SGOLD, glow=1.0, var=0, key="ostar"))
    return m


def road_anims():
    A = []
    deco = ["arch", "pole_r", "pole_l", "cloud_r", "cloud_l"]
    life = Anim("life", loop=True)
    life.rot("tilt", (tilt_expr(), 0, 0))
    for s in "rl":
        life.rot(f"lantern_{s}", (LIFE(8, 2.2, 0.3 if s == "r" else 0), 0, LIFE(5, 1.7)))
        wave(life, [f"banner_{s}{j + 1}" for j in range(3)], 0, 10, 1.6, lag=0.15, grow=1.2, clock="q.life_time")
        life.rot(f"orbit_{s}", (0, spin(50 if s == "r" else -50), 0))
        life.pos(f"cloud_{s}", (0, LIFE(1.0, 3.3, 0.2 if s == "r" else 0), 0))
    life.rot("pendant", (LIFE(4, 2.0), 0, LIFE(7, 2.6)))
    A.append(life)
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    unroll = Anim("unroll", length=0.8, loop="hold")      # a carpet of flagstones unrolls from the back edge
    unroll.scl("deck", {0: (1, 1, 0.02), 0.35: (1, 1, 1.04), 0.45: 1.0, 0.8: 1.0})
    unroll.pos("roll", {0: (0, 0, 0), 0.35: (0, 0, -ROAD_L), 0.8: (0, 0, -ROAD_L)})
    unroll.scl("roll", {0: 1.0, 0.3: 0.6, 0.4: 0.0, 0.8: 0.0})
    unroll.scl("under", {0: 0.0, 0.3: 0.0, 0.6: 1.1, 0.8: 1.0})
    for s in "rl":
        unroll.scl(f"rail_{s}", {0: (1, 0, 1), 0.2: (1, 0, 1), 0.45: (1, 1.15, 1), 0.55: 1.0})
    for d in deco:
        unroll.scl(d, {0: (1, 0, 1), 0.3: (1, 0, 1), 0.65: (1.05, 1.1, 1.05), 0.8: 1.0})
    A.append(unroll)
    hold = Anim("hold", loop=True)
    A.append(hold)
    rollup = Anim("rollup", length=0.8, loop="hold")      # architecture folds, the road rolls back up
    for d in deco:
        rollup.scl(d, {0: 1.0, 0.3: (1, 0, 1)})
    for s in "rl":
        rollup.scl(f"rail_{s}", {0: 1.0, 0.2: 1.0, 0.4: (1, 0, 1)})
    rollup.scl("under", {0: 1.0, 0.3: 0.0})
    rollup.scl("deck", {0: 1.0, 0.3: 1.0, 0.75: (1, 1, 0.0)})
    rollup.pos("roll", {0: (0, 0, -ROAD_L), 0.3: (0, 0, -ROAD_L), 0.75: (0, 0, 0)})
    rollup.scl("roll", {0: 0.0, 0.29: 0.0, 0.31: 0.4, 0.7: 1.2, 0.8: 0.0})
    A.append(rollup)
    return A


ROAD_STATES = {0: ["hidden"], 1: ["unroll"], 2: ["hold"], 3: ["rollup"]}


# ================================================================= the Sleeping Moon
def moon_model():
    m = Model("dn_parade_moon", density=1.0, bounds=(10, 10, (0, 0, 0)))
    mat = porc("#fbf0c8", "#e9d49a", crack=0.35, glow=0.45)
    rim = tex.trimmed(porc("#fff6d8", "#efdcaa", crack=0.0, glow=0.55), SGOLD, 1, 0, 0.9)
    cap = tex.stamped(tex.fabric("#8fa6d8", "#a3b8e2", stripe_w=3, glow=0.12), ["#  ", "   ", "  #"], "#fff3c4", glow=0.9,
                      repeat=True, key="capstars")
    root = m.bone("root")
    rock = m.bone("rock", root, pivot=(0, 0, 0))
    R = 20.0
    n = 15
    for i in range(n):                    # crescent: thick at the back (-X), tapering to the horns
        f = (i + 0.5) / n
        a = 180 + (-150 + 300 * f)
        th = 2.2 + 9.0 * math.cos(math.radians(a - 180)) ** 1.6 if abs(a - 180) < 90 else 2.2 + 0.6 * (1 - abs(a - 180) / 150)
        rr = R - th / 2
        p = (rr * math.cos(math.radians(a)), rr * math.sin(math.radians(a)), 0)
        tl = 2 * math.pi * R / n * 1.05
        rock.box(p, (th, tl, 7), mat if i % 3 else rim, rot=(0, 0, a), pivot=p, variant=i % 3)
    # the profile face on the inner edge: nose, closed eye, cheek
    face = m.bone("face", rock, pivot=(-8, 0, 0))
    face.box((-6.6, -1.5, 0), (3, 3, 5), mat, variant=1)                              # nose
    face.box((-7.6, -5.2, 0), (2.2, 1.6, 4.6), tex.flat("#e9a8a8", glow=0.3))         # lips
    face.plane("z", (-11.5, 3.5, -3.6), 5, 2.4, tex.bitmap_cut(["#     #", " #   # ", "  ###  ", " # # # "], "#7a6a8a"))
    face.plane("z", (-11.5, -3.0, -3.6), 3.4, 3.4, tex.shaped(tex.m_disc(1.0), "#f4b0b8", glow=0.4, var=0, key="mcheek"))
    # nightcap draped over the upper horn, star pompom
    cp = m.bone("cap1", rock, pivot=(-4, 16, 0), rot=(0, 0, -30))
    cp.box((-4, 19, 0), (10, 6, 8), cap)
    c2 = m.bone("cap2", "cap1", pivot=(-4, 22, 0), rot=(0, 0, -40))
    c2.box((-4, 24.5, 0), (7, 5, 6), cap, variant=1)
    c3 = m.bone("cap3", "cap2", pivot=(-4, 27, 0), rot=(0, 0, -50))
    c3.box((-4, 29, 0), (4.5, 4, 4), cap, variant=2)
    c3.box((-4, 32.5, 0), (3.6, 3.6, 3.6), tex.glow_flat("#fff3c4", 1.0, core="#ffffff"), rot=(45, 45, 0))
    # tiny stars dangling from the lower horn
    for k, (x, l) in enumerate(((6, 8), (12, 5), (2, 11))):
        b = m.bone(f"dangle{k + 1}", rock, pivot=(x, -14 - k, 0))
        b.box((x, -14 - k - l / 2, 0), (0.3, l, 0.3), tex.glow_flat("#fff0c8", 0.8))
        st = tex.shaped(tex.m_star(5, 0.45), "#fff3c4", SGOLD, glow=1.0, var=0, key="mdstar")
        b.plane("z", (x, -14 - k - l - 1.6, 0), 3.4, 3.4, st)
        b.plane("x", (x, -14 - k - l - 1.6, 0), 3.4, 3.4, st)
    return m


def moon_anims():
    life = Anim("life", loop=True)
    life.rot("rock", (LIFE(3, 5.0), LIFE(8, 7.0), LIFE(7, 4.2)))
    life.pos("rock", (0, LIFE(1.6, 3.6), 0))
    life.scl("face", (1.0, LIFE(0.03, 3.4, base=1.0), 1.0))          # slow sleeping breath
    for k in range(3):
        life.rot(f"dangle{k + 1}", (LIFE(10, 2.1 + k * 0.3, k * 0.2), 0, LIFE(12, 2.6 + k * 0.2)))
    life.rot("cap3", (0, 0, LIFE(6, 3.0)))
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    rise = Anim("rise", length=1.4, loop="hold")
    rise.scl("root", {0: 0.0, 0.8: 1.08, 1.1: 0.98, 1.4: 1.0})
    rise.pos("root", {0: (0, -26, 0), 1.0: (0, 2, 0), 1.4: (0, 0, 0)})
    rise.rot("root", {0: (0, 0, -120), 1.1: (0, 0, 6), 1.4: (0, 0, 0)})
    sleep = Anim("sleep", loop=True)
    sett = Anim("set", length=1.4, loop="hold")
    sett.rot("root", {0: (0, 0, 0), 1.4: (0, 0, 90)})
    sett.pos("root", {0: (0, 0, 0), 0.4: (0, 3, 0), 1.4: (0, -30, 0)})
    sett.scl("root", {0: 1.0, 1.0: 0.8, 1.4: 0.0})
    return [life, hidden, rise, sleep, sett]


MOON_STATES = {0: ["hidden"], 1: ["rise"], 2: ["sleep"], 3: ["set"]}


# ================================================================= crescent hit mark (skins = 1..4 crescents)
def mark_model():
    m = Model("dn_parade_mark", density=2.0, bounds=(3, 3, (0, 1, 0)), alts=("two", "three", "four"))
    root = m.bone("root")
    spinb = m.bone("wheel", root, pivot=(0, 8, 0))
    order = ("default", "two", "three", "four")
    cols = ("#ffe9b8", "#ffd2e4", "#d8e8ff", "#fff6d8")
    for k in range(4):
        dim = tex.shaped(tex.m_crescent(0.42), "#8a7aa8", "#6a5a8a", glow=0.15, var=0, key=f"mkd{k}")
        lit = [tex.shaped(tex.m_crescent(0.42), cols[k], "#fffbe8", glow=0.55 + 0.15 * lv, var=0, outline=SGOLD,
                          key=f"mkl{k}{lv}") for lv in range(4)]
        # crescent k lights from skin index k; every lit crescent gets brighter as the count grows
        skins = {order[i]: (lit[i] if i >= k else dim) for i in range(1, 4)}
        b = m.bone(f"cres{k + 1}", spinb, pivot=(0, 8, 0), rot=(0, 0, k * 90))
        b.plane("z", (0, 13, 0), 5.5, 5.5, tex.alt(lit[0] if k == 0 else dim, **skins))
    core = m.bone("core", spinb, pivot=(0, 8, 0))
    full = tex.shaped(tex.m_disc(0.9), "#fffbe8", "#ffe2a0", glow=1.0, var=0, key="mkfull")
    small = tex.shaped(tex.m_star(4, 0.4), "#fff3c4", "#ffd9b8", glow=0.9, var=0, key="mkstar")
    core.plane("z", (0, 8, 0), 4.5, 4.5, tex.alt(small, four=full))
    return m


def mark_anims():
    life = Anim("life", loop=True)
    life.rot("root", (0, spin(70), 0))
    life.rot("wheel", (0, 0, spin(-45)))
    life.pos("root", (0, LIFE(0.8, 1.4), 0))
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    appear = Anim("appear", length=0.35, loop="hold")
    appear.scl("root", {0: 0.0, 0.2: 1.35, 0.35: 1.0})
    hold = Anim("hold", loop=True)
    flare = Anim("flare", length=0.4, loop="hold")
    flare.scl("root", {0: 1.0, 0.12: 1.6, 0.4: 1.15})
    flare.rot("wheel", {0: (0, 0, 0), 0.4: (0, 0, 180)})
    vanish = Anim("vanish", length=0.4, loop="hold")
    vanish.scl("root", {0: 1.0, 0.15: 1.4, 0.4: 0.0})
    vanish.pos("root", {0: (0, 0, 0), 0.4: (0, 12, 0)})
    return [life, hidden, appear, hold, flare, vanish]


MARK_STATES = {0: ["hidden"], 1: ["appear"], 2: ["hold"], 3: ["flare"], 4: ["vanish"]}


# ================================================================= sounds (original synthesis)
def note(semi, base=587.33):
    return base * 2 ** (semi / 12.0)


def music_box(seq, step, dur_extra=1.2, base=587.33, bright=0.9, inst="box"):
    parts = []
    t = 0.0
    for s, d in seq:
        if s is not None:
            f = note(s, base)
            if inst == "box":
                sig = sy.at(0.0, (0.0, sy.pluck(f, 0.9, bright), 0.7), (0.0, sy.bell(f * 2, 0.6, 0.6), 0.18))
            elif inst == "celesta":
                sig = sy.at(0.0, (0.0, sy.bell(f, 1.0, 0.8, inharm=0.35), 0.7), (0.0, sy.pluck(f, 0.6, 0.7), 0.3))
            elif inst == "glass":
                tt = sy.t_axis(1.2)
                sig = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.01 * tt)) * sy.env(1.2, 0.12, 0.2, 0.6, 0.6) * 0.55
            elif inst == "flute":
                tt = sy.t_axis(0.9)
                vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * tt)
                tone = sy.osc(f * vib, 0.9) * 0.8 + sy.bandpass(sy.noise(0.9), f, 6) * 0.25
                sig = tone * sy.env(0.9, 0.08, 0.15, 0.7, 0.35) * 0.6
            else:  # toy
                sig = sy.pluck(f, 0.5, 1.0) * 0.6 + sy.pluck(f * 1.006, 0.5, 1.0) * 0.4
            parts.append((t, sig))
        t += d * step
    return sy.at(t + dur_extra, *parts)


def build_sounds(pack):
    # the invented parade motif (lilting long-short rhythm); each creature adds a voice in the same key/tempo
    motif = [(0, 2), (9, 1), (7, 2), (14, 1), (11, 2), (7, 1), (16, 3), (14, 1), (9, 2), (11, 1), (4, 2), (7, 4)]
    step = 0.13
    theme = sy.mixdown([music_box(motif, step), sy.pad(note(-12), 3.4, cutoff=1100, attack=0.6, release=1.0) * 0.25])
    sy.save(pack, "dn_parade_theme", sy.reverb(theme, 1.6, 0.35), max_distance=64)
    horse_v = [(-5, 3), (2, 3), (0, 3), (4, 3), (2, 3), (-1, 3), (0, 6)]
    stag_v = [(None, 1), (19, 5), (16, 6), (21, 6), (19, 6)]
    bird_v = [(14, 1), (16, 1), (19, 4), (None, 2), (21, 1), (19, 1), (16, 4), (14, 4)]
    doll_v = [(None, 1), (12, 1), (None, 2), (11, 1), (None, 2), (12, 1), (None, 1), (7, 1), (None, 2), (12, 1), (None, 2), (14, 2)]
    sy.save(pack, "dn_parade_voice_horse", sy.reverb(music_box(horse_v, step, inst="celesta", base=note(-12)), 1.4, 0.3))
    sy.save(pack, "dn_parade_voice_stag", sy.reverb(music_box(stag_v, step, inst="glass", base=note(-12)), 2.0, 0.4))
    sy.save(pack, "dn_parade_voice_bird", sy.reverb(music_box(bird_v, step, inst="flute", base=note(-12)), 1.6, 0.35))
    sy.save(pack, "dn_parade_voice_doll", sy.reverb(music_box(doll_v, step, inst="toy"), 1.0, 0.25))

    arp = sy.at(0.1, *[(i * 0.08, sy.bell(note(s), 0.9, 1.0, inharm=0.4) * 0.5) for i, s in enumerate((0, 4, 7, 11, 14, 18, 21, 23))])
    opn = sy.at(2.2, (0.0, sy.whoosh(1.2, 250, 1800) * 0.4), (0.05, arp), (0.3, sy.shimmer(1.6, 2400, 20) * 0.35),
                (0.0, sy.pad(note(-12), 2.0, cutoff=1500, attack=0.3) * 0.3))
    sy.save(pack, "dn_parade_open", sy.reverb(opn, 1.8, 0.4), max_distance=64)
    ro = sy.at(1.8, (0.0, sy.whoosh(1.0, 1800, 260) * 0.45), (0.1, sy.at(0.1, *[(i * 0.09, sy.bell(note(s), 0.8, 0.8, inharm=0.4) * 0.45)
                                                                                for i, s in enumerate((23, 19, 16, 12, 9, 4, 0))])),
                (0.0, sy.shimmer(1.4, 2200, 16)[::-1] * 0.3))
    sy.save(pack, "dn_parade_rollup", sy.reverb(ro, 1.6, 0.4), max_distance=64)
    moon = sy.at(2.2, (0.0, sy.choir(note(-17), 2.0, "oo", voices=4, attack=0.6, release=1.0) * 0.6),
                 (0.0, sy.choir(note(-10), 2.0, "oo", voices=3, attack=0.8, release=1.0) * 0.35),
                 (0.6, sy.bell(note(7), 1.4, 0.6) * 0.3), (1.1, sy.bell(note(14), 1.2, 0.6) * 0.2))
    sy.save(pack, "dn_parade_moon", sy.reverb(moon, 2.2, 0.45), max_distance=72)

    # creature footfalls and voices
    def hoof(p):
        return sy.at(0.4, (0.0, sy.bell(2350 * p, 0.35, 1.2, inharm=1.3) * 0.5), (0.0, sy.crack(0.12, 7000, 4) * 0.25),
                     (0.0, sy.thump(0.15, 220, 90, 0.6) * 0.35), (0.07, sy.bell(3100 * p, 0.25, 1.0, inharm=1.2) * 0.25))
    sy.save(pack, "dn_parade_hoof", hoof(1.0), variants=[hoof(1.06), hoof(0.94)], volume=0.55, max_distance=32)
    neigh_f = sy.sweep(900, 1500, 0.5) * (1 + 0.04 * np.sin(2 * np.pi * 14 * sy.t_axis(0.5)))
    neigh = sy.at(1.2, (0.0, sy.formants(sy.osc(neigh_f, None, "saw"), [(1200, 200, 1.0), (2600, 300, 0.4)]) * 0.12),
                  (0.0, sy.at(0.1, *[(i * 0.045, sy.bell(note(s + 12), 0.4, 1.0, inharm=0.4) * 0.4) for i, s in enumerate((0, 7, 12, 16, 19, 16, 12))])),
                  (0.3, sy.shimmer(0.8, 3000, 10) * 0.25))
    sy.save(pack, "dn_parade_neigh", sy.reverb(neigh, 1.2, 0.3), max_distance=48)
    charge = sy.at(1.5, (0.0, sy.whoosh(1.0, 300, 3500) * 0.45), (0.0, sy.at(0.1, *[(i * 0.11, hoof(1 + 0.03 * (i % 3)) * 0.6) for i in range(10)])),
                   (0.05, sy.bell(note(0), 1.2, 1.0) * 0.4))
    sy.save(pack, "dn_parade_charge", sy.reverb(charge, 1.0, 0.25), max_distance=56)

    def step_(p):
        return sy.at(0.8, (0.0, sy.bell(1480 * p, 0.7, 1.0, inharm=1.45) * 0.55), (0.0, sy.thump(0.2, 160, 70, 0.3) * 0.3),
                     (0.02, sy.bell(2960 * p, 0.5, 0.8, inharm=1.2) * 0.2))
    sy.save(pack, "dn_parade_step", sy.reverb(step_(1.0), 0.9, 0.3), variants=[sy.reverb(step_(1.12), 0.9, 0.3)], volume=0.6, max_distance=32)
    land = sy.at(1.4, (0.0, sy.thump(0.6, 140, 40, 0.5) * 0.8), (0.0, sy.bell(988, 1.3, 1.1, inharm=1.4) * 0.55),
                 (0.0, sy.crack(0.4, 8000, 10) * 0.25), (0.05, sy.shimmer(1.0, 2600, 14) * 0.3))
    sy.save(pack, "dn_parade_land", sy.reverb(land, 1.4, 0.35), variants=[sy.reverb(sy.pitch(land, 1.1), 1.4, 0.35),
                                                                          sy.reverb(sy.pitch(land, 1.22), 1.4, 0.35)], max_distance=56)
    sy.save(pack, "dn_parade_bell", sy.reverb(sy.at(1.0, (0.0, sy.bell(1760, 0.9, 0.9, inharm=1.4) * 0.6),
                                                    (0.1, sy.shimmer(0.7, 2800, 10) * 0.3)), 1.4, 0.4), max_distance=40)

    def flap():
        n = sy.lowpass(sy.noise(0.18), 900) * sy.env(0.18, 0.02, 0.05, 0.5, 0.1)
        return sy.at(0.6, (0.0, n * 0.7), (0.22, n * 0.5), (0.0, sy.whoosh(0.4, 200, 900) * 0.3))
    sy.save(pack, "dn_parade_flap", flap(), volume=0.6, max_distance=32)
    sw = sy.at(1.2, (0.0, sy.whoosh(0.9, 2200, 300) * 0.6), (0.0, flap() * 0.6),
               (0.05, sy.at(0.1, *[(i * 0.06, sy.bell(note(s), 0.5, 0.8, inharm=0.4) * 0.35) for i, s in enumerate((21, 19, 16, 14, 12, 9))])))
    sy.save(pack, "dn_parade_swoop", sy.reverb(sw, 1.0, 0.3), variants=[sy.reverb(sy.pitch(sw, 1.08), 1.0, 0.3)], max_distance=48)

    def tick(p):
        k = sy.bandpass(sy.noise(0.05), 3200 * p, 5) * sy.decay(0.05, 0.01)
        return sy.at(0.35, (0.0, k * 0.8), (0.0, sy.pluck(note(12) * p, 0.3, 1.0) * 0.3))
    sy.save(pack, "dn_parade_tick", tick(1.0), variants=[tick(0.8), tick(1.19)], volume=0.6, max_distance=32)

    def pulse(p):
        ch = sy.at(0.1, *[(0.0, sy.bell(note(s) * p, 0.9, 1.2, inharm=0.5) * 0.3) for s in (0, 7, 12, 16)])
        return sy.at(1.0, (0.0, ch), (0.0, sy.shimmer(0.7, 3000, 16) * 0.35), (0.0, sy.thump(0.3, 200, 80, 0.4) * 0.3))
    sy.save(pack, "dn_parade_pulse", sy.reverb(pulse(1.0), 1.0, 0.3), variants=[sy.reverb(pulse(1.12), 1.0, 0.3),
                                                                                sy.reverb(pulse(0.89), 1.0, 0.3)], max_distance=48)

    def hit(p):
        return sy.at(0.8, (0.0, sy.pluck(note(12) * p, 0.6, 0.9) * 0.6), (0.06, sy.pluck(note(19) * p, 0.6, 0.9) * 0.5),
                     (0.0, sy.crack(0.2, 9000, 6) * 0.25), (0.02, sy.bell(note(24) * p, 0.7, 0.8) * 0.3))
    sy.save(pack, "dn_parade_hit", sy.reverb(hit(1.0), 0.9, 0.3), variants=[sy.reverb(hit(1.06), 0.9, 0.3)], max_distance=40)
    full = sy.at(2.0, (0.0, sy.thump(0.8, 120, 35, 0.4) * 0.6),
                 (0.0, sy.at(0.1, *[(i * 0.05, sy.bell(note(s), 1.6, 1.0, inharm=0.4) * 0.3) for i, s in enumerate((0, 4, 7, 11, 12, 16, 19, 24))])),
                 (0.05, sy.choir(note(0), 1.6, "ah", voices=4, attack=0.05, release=0.9) * 0.35), (0.1, sy.shimmer(1.6, 2600, 24) * 0.35))
    sy.save(pack, "dn_parade_fullmoon", sy.reverb(full, 2.2, 0.45), max_distance=64)
    arr = sy.at(0.9, (0.0, sy.crack(0.25, 7000, 8) * 0.3), (0.0, sy.shimmer(0.8, 2400, 14)[::-1] * 0.4),
                (0.55, sy.bell(note(7), 0.5, 0.8) * 0.35))
    sy.save(pack, "dn_parade_arrive", sy.reverb(arr, 1.0, 0.3), max_distance=48)
    dep = sy.at(1.2, (0.0, sy.bell(note(19), 1.1, 0.7)[::-1] * 0.4), (0.3, sy.shimmer(0.9, 3200, 14) * 0.3),
                (0.0, sy.whoosh(1.0, 600, 3000) * 0.25))
    sy.save(pack, "dn_parade_depart", sy.reverb(dep, 1.4, 0.4), max_distance=48)


# ================================================================= particles
def build_particles(pack):
    fx = particles(pack)
    fx.effect("dn_parade_crescent", "moon", count=6, life=(0.6, 1.1), size=(0.32, 0.08), shape=("sphere", 0.5), speed=(2.0, 4.5),
              accel=(0, -1.5, 0), drag=1.8, colors=["#fffbe8ff", "#ffd9b8ff", "#e8b4c800"], spin=(360, 200))
    fx.effect("dn_parade_shard", None, sprites=["shard", "diamond", "star"], count=12, life=(0.5, 1.2), size=(0.14, 0.02),
              shape=("sphere", 0.4), speed=(2.5, 6.0), accel=(0, -6, 0), drag=0.8,
              colors=["#ffffffff", "#bcd6f0ff", "#e8b4c8ff", "#cdbfe800"], spin=(360, 300))
    fx.effect("dn_parade_groundmoon", "moon", count=1, life=(0.7, 0.8), size=(0.6, 2.6), facing="emitter_transform_xz",
              colors=["#fff6d8ff", "#ffd9b8cc", "#e8b4c800"])
    fx.effect("dn_parade_confetti", None, sprites=["petal", "star", "moon", "diamond"], count=8, life=(1.2, 2.2), size=(0.12, 0.06),
              shape=("sphere", 1.4), speed=(0.4, 1.4), accel=(0, -0.6, 0), drag=1.6,
              colors=["#ffd9b8ff", "#e8b4c8ff", "#bcd6f0ff", "#e9cf8a00"], blend="blend", spin=(360, 160))
    fx.effect("dn_parade_note", "note", count=2, life=(1.0, 1.6), size=(0.16, 0.12), shape=("sphere", 0.8), speed=(0.3, 0.7),
              accel=(0, 0.8, 0), drag=0.8, colors=["#fff3c4ff", "#ffd9b8ff", "#e8b4c800"])
    fx.effect("dn_parade_mistpuff", "puff", count=6, life=(0.6, 1.2), size=(0.3, 0.8), shape=("disc", 0.4), speed=(0.6, 1.6),
              accel=(0, 0.4, 0), drag=1.6, colors=["#e8f1ffcc", "#cdbfe800"], blend="blend", spin=(360, 40))
    fx.effect("dn_parade_hoofdust", None, sprites=["spark", "dot"], count=4, life=(0.3, 0.6), size=(0.1, 0.0), shape=("disc", 0.3),
              speed=(0.8, 2.0), accel=(0, -2, 0), drag=1.0, colors=["#fffbe8ff", "#e9cf8a00"])
    fx.effect("dn_parade_ribbon", "wave", count=3, life=(0.6, 1.0), size=(0.25, 0.1), shape=("sphere", 0.3), speed=(0.2, 0.6),
              drag=1.2, colors=["#e8b4c8ff", "#ffd9b8cc", "#bcd6f000"], spin=(360, 90))
    fx.effect("dn_parade_starpop", "star", count=10, life=(0.4, 0.8), size=(0.22, 0.04), shape=("sphere", 0.4), speed=(3, 6),
              drag=2.0, colors=["#ffffffff", "#fff3c4ff", "#e9cf8a00"], spin=(360, 240))
    fx.effect("dn_parade_pulse", "ringthin", count=1, life=(0.45, 0.5), size=(0.4, 4.8), facing="emitter_transform_xz",
              colors=["#fff6d8ff", "#e8b4c8cc", "#cdbfe800"])
    fx.effect("dn_parade_trail", None, sprites=["star", "dot", "moon"], count=3, life=(0.6, 1.2), size=(0.12, 0.0),
              shape=("sphere", 0.6), speed=(0.1, 0.4), accel=(0, -0.3, 0), colors=["#fff3c4ff", "#ffd9b8ff", "#bcd6f000"], spin=(360, 90))
    fx.effect("dn_parade_lane", "moon", count=1, life=(0.5, 0.6), size=(0.5, 0.2), facing="emitter_transform_xz",
              colors=["#ffd9b8ff", "#e8b4c800"])
    fx.effect("dn_parade_glint", "spark", count=1, life=(0.4, 0.6), size=(0.3, 0.0), colors=["#ffffffff", "#fff3c400"])
    return fx


# ================================================================= build
def build(pack):
    build_particles(pack)

    hm = horse_model()
    ha = horse_anims()
    pack.actor("dn_parade_horse", hm, ha, HORSE_STATES, always=["life"], scale=1.5, lifetime=40, props=TILT,
               sounds={"hoof": "grimoire.dn_parade_hoof", "neigh": "grimoire.dn_parade_neigh"},
               particles={"hoofdust": "grimoire:dn_parade_hoofdust"}, display="Porcelain Horse", blend=0.15)
    sm = stag_model()
    sa = stag_anims()
    pack.actor("dn_parade_stag", sm, sa, STAG_STATES, always=["life"], scale=1.3, lifetime=40, props=TILT,
               sounds={"step": "grimoire.dn_parade_step", "bell": "grimoire.dn_parade_bell"},
               particles={"mistpuff": "grimoire:dn_parade_mistpuff"}, display="Mist-Glass Stag", blend=0.12)
    bm = bird_model()
    ba = bird_anims()
    pack.actor("dn_parade_bird", bm, ba, BIRD_STATES, always=["life"], scale=1.4, lifetime=40, props=TILT,
               sounds={"flap": "grimoire.dn_parade_flap"}, particles={"ribbon": "grimoire:dn_parade_ribbon"},
               display="Curtain-Winged Bird", blend=0.15)
    dm = doll_model()
    da = doll_anims()
    pack.actor("dn_parade_doll", dm, da, DOLL_STATES, always=["life"], scale=1.4, lifetime=40, props=TILT,
               sounds={"tick": "grimoire.dn_parade_tick"}, particles={"starpop": "grimoire:dn_parade_starpop"},
               display="Floating Star Doll", blend=0.1)
    roads = [road_model(k) for k in range(4)]
    ra = road_anims()
    pack.actor("dn_parade_road", roads[0], ra, ROAD_STATES, always=["life"], kinds=roads[1:], lifetime=40, props=TILT,
               display="Dream-Road", blend=0.0)
    mm = moon_model()
    ma = moon_anims()
    pack.actor("dn_parade_moon", mm, ma, MOON_STATES, always=["life"], scale=2.5, lifetime=40, display="Sleeping Moon", blend=0.2)
    mk = mark_model()
    mka = mark_anims()
    pack.actor("dn_parade_mark", mk, mka, MARK_STATES, always=["life"], lifetime=40, display="Crescent Mark", blend=0.0)

    build_sounds(pack)

    # ---- previews
    H = {a.name: a for a in ha}
    pack.preview("dn_parade_horse", hm, [None, [(H["parade"], 0.15), (H["life"], 1.0)], [(H["parade"], 0.45), (H["life"], 1.0)],
                                         [(H["charge"], 0.3), (H["life"], 1.0)], (H["arrive"], 0.62)],
                 views=((30, 12), (90, 5), (-150, 15)))
    St = {a.name: a for a in sa}
    pack.preview("dn_parade_stag", sm, [None, (St["parade"], 0.5), (St["leap_a"], 0.55), (St["leap_a"], 0.86), (St["arrive"], 0.6)],
                 views=((30, 12), (90, 5), (-150, 15)))
    B = {a.name: a for a in ba}
    pack.preview("dn_parade_bird", bm, [None, [(B["glide"], 0.6), (B["life"], 1.0)], (B["swoop_a"], 0.45), (B["arrive"], 0.3),
                                        (B["swoop_a"], 0.9)], views=((30, 15), (0, 70), (90, 5)))
    D = {a.name: a for a in da}
    pack.preview("dn_parade_doll", dm, [None, (D["float"], 0.4), (D["float"], 0.8), (D["pulse_a"], 0.2)],
                 views=((0, 8), (40, 15), (90, 5)))
    for k, r in enumerate(roads):
        pack.preview(f"dn_parade_road{k}", r, [None], views=((35, 25), (0, 8)), cell=(360, 300))
    pack.preview("dn_parade_moon", mm, [None], views=((0, 0), (40, 15)), cell=(360, 360))
    pack.preview("dn_parade_mark", mk, [None], views=((0, 0),), cell=(240, 240), skin="three")
    for nm, mdl in (("horse", hm), ("stag", sm), ("bird", bm), ("doll", dm), ("moon", mm), ("road", roads[1]), ("mark", mk)):
        print(f"    {nm}: {mdl.cube_count()} cubes, {len(mdl.order)} bones, tex {mdl.tex_size}")
