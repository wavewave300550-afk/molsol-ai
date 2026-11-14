"""ED06 -- the temporary primordial atmosphere set (non-destructive scenery, all script actors).

ed6_horizon  ring of far silhouettes around the domain: a smoking volcano with lava streams, giant
             araucarias, tree-fern / cycad thickets and a jagged ridge, as large thin cut-out panels.
             Radius 52 blocks (scale 1), panels 14-26 blocks tall; the volcano sits on the actor's
             front (-Z).  STATES 0 hidden / 1 rise (3.0 s) / 2 hold / 3 sink (2.4 s)
ed6_fog      low translucent primordial mist: four layered planes (all below a standing player's eye,
             0.3-1.3 blocks) + a curtain at the domain edge (radius ~30 blocks).  STATES 0 hidden /
             1..4 = density level (each heartbeat adds a layer; controller blend 1.2 s) / 5 clear
ed6_flora    kinds 0 tree-fern / 1 cycad / 2 horsetail stand / 3 giant fern clump (scale 2.0,
             3-7.5 blocks tall).  STATES 0 hidden / 1 sprout (2.0 s: trunk grows, fronds unfurl)
             / 2 sway / 3 wither (1.4 s)
ed6_stone    cluster of three rune-carved standing stones (~3.5 blocks).  Skins: 0 weathered stone,
             1 'glass' vitrified glowing amber glass, 2 'obsidian' cooled dark glass.
             STATES 0 hidden / 1 rise (1.2 s) / 2 hold / 3 sink (1.0 s) / 4 flare (0.5 s heat jolt)
"""
import math

import numpy as np

from kit import tex
from kit.anim import LIFE, Anim, M, S
from kit.geo import Mat, Model

from .ed6_common import DR, T, mix, px, rgb, rune_plate, spin, stone_skins

# ============================================================================== horizon panels
HZ_R = 52 * 16.0


def _panel_mat(kind, key):
    """Distant silhouette painted in aerial-perspective colours (a cut-out sheet)."""
    far, near, top = rgb("#3c4a4a"), rgb("#26302c"), rgb("#6a7a70")

    def fn(ctx):
        u, v = ctx.U, 1 - ctx.V           # v = 0 at the bottom
        ix, iy = px(ctx)
        n = tex.fbm(u * 18, v * 6, 13 + kind)
        col = mix(near, far, np.clip(v * 1.4, 0, 1)[..., None])
        glow = np.full(u.shape, 0.12)
        if kind == 0:          # volcano: broad cone, crater notch, glowing lava rivulets
            prof = 0.92 - np.abs(u - 0.5) * 1.75 + 0.03 * (n - 0.5)
            notch = (np.abs(u - 0.5) < 0.06) & (v > 0.84)
            mask = (v < prof) & ~notch & (v < 0.93)
            lava = mask & (np.abs(((u - 0.5) * 9 + np.sin(v * 14 + u * 5) * 0.35) % 1.0 - 0.5) < 0.045 * (v + 0.1)) & (v > 0.15)
            col = np.where(lava[..., None], mix(rgb("#ffb24a"), rgb("#ff4a10"), (1 - v)[..., None]), col)
            glow = np.where(lava, 1.0, glow)
            rim = mask & (v > prof - 0.04) & (v > 0.7)
            col = np.where(rim[..., None], rgb("#ff7a2a"), col)
            glow = np.where(rim, 0.8, glow)
        elif kind == 1:        # giant araucarias: tall bare trunks with umbrella crowns
            mask = v < 0.08 + 0.05 * n
            for c, h, w in ((0.12, 0.78, 0.13), (0.33, 0.95, 0.17), (0.55, 0.7, 0.12), (0.78, 0.88, 0.16), (0.93, 0.6, 0.09)):
                trunk = (np.abs(u - c) < 0.008 + 0.004 * (1 - v)) & (v < h)
                crown = (np.abs(u - c) < w * (1 - np.abs(v - h) / 0.09) * (0.85 + 0.3 * n)) & (np.abs(v - h) < 0.09)
                tiers = (np.abs(u - c) < w * 0.6 * (1 - np.abs(v - (h - 0.13)) / 0.05)) & (np.abs(v - (h - 0.13)) < 0.05)
                mask |= trunk | crown | tiers
        elif kind == 2:        # tree-fern and cycad thicket
            mask = v < 0.18 + 0.08 * tex.fbm(u * 30, 0, 4)
            for c, h in ((0.08, 0.55), (0.22, 0.75), (0.4, 0.5), (0.58, 0.82), (0.75, 0.62), (0.9, 0.7)):
                trunk = (np.abs(u - c) < 0.012) & (v < h)
                da, dv = (u - c) / 0.14, (v - h) / 0.12
                ang = np.arctan2(dv, da)
                fr = (np.hypot(da, dv) < 1.0) & (np.abs(np.sin(ang * 5)) > 0.35) & (dv > -0.9 + 0.5 * np.abs(da))
                mask |= trunk | fr
        else:                  # jagged ridge with a cascade
            prof = 0.45 + 0.25 * np.abs(np.sin(u * 7.3)) * (0.7 + 0.6 * tex.fbm(u * 9, 0, 9)) + 0.12 * np.sin(u * 2.1)
            mask = v < prof
            fall = mask & (np.abs(u - 0.62) < 0.012) & (v < prof - 0.05)
            col = np.where(fall[..., None], rgb("#b8e0ff"), col)
            glow = np.where(fall, 0.6, glow)
        rim = mask & ~np.roll(mask, -1, axis=0)
        col = np.where(rim[..., None], top, col)
        t = T(ctx, col, glow)
        t[..., 3] = mask * 1.0
        return tex.grain(ctx, t, 0.04)
    return Mat(fn, key, directional=True)


def _plume_mat():
    def fn(ctx):
        u, v = ctx.U * 2 - 1, 1 - ctx.V
        n = tex.fbm(ctx.U * 5, ctx.V * 4, 31)
        w = 0.25 + 0.6 * v
        a = np.clip((1 - np.abs(u) / w) * 1.4, 0, 1) * (0.25 + 0.5 * n) * np.clip(1 - v * 0.9, 0, 1)
        t = T(ctx, mix(rgb("#5a4a44"), rgb("#9a8a80"), v[..., None]), 0.05, 0)
        t[..., 3] = a * 0.8
        return t
    return Mat(fn, "ed6plume", mode="blend")


# (angle deg, kind, width blocks, height blocks)
HZ = [(0, 0, 50, 24), (34, 1, 38, 25), (70, 3, 44, 17), (104, 2, 36, 15), (140, 1, 40, 22), (176, 3, 42, 14),
      (212, 2, 38, 15), (246, 1, 36, 21), (282, 3, 46, 18), (318, 2, 38, 15)]


def horizon_model():
    m = Model("ed6_horizon", density=0.14, bounds=(120, 40, (0, 12, 0)))
    root = m.bone("root")
    mats = [_panel_mat(k, f"ed6hz{k}") for k in range(4)]
    for i, (ang, kind, w, h) in enumerate(HZ):
        b = m.bone(f"p{i + 1}", root, pivot=(0, 0, 0), rot=(0, ang, 0))
        W, H = w * 16, h * 16
        b.plane("z", (0, H / 2 - 12, -HZ_R - (i % 2) * 40), W, H, mats[kind], variant=i % 2)
        if kind == 0:
            pl = m.bone(f"plume{i + 1}", b, pivot=(0, H - 10, -HZ_R))
            pl.plane("z", (0, H + 110, -HZ_R + 6), 220, 260, _plume_mat(), density=0.2)
    return m


def horizon_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    hold = Anim("hold", loop=True)
    A.append(hold)
    life = Anim("life", loop=True)
    for i, (ang, kind, w, h) in enumerate(HZ):
        if kind == 0:
            life.rot(f"plume{i + 1}", (0, 0, LIFE(4, 7.0)))
            life.scl(f"plume{i + 1}", (LIFE(0.08, 5.0, base=1.0), LIFE(0.1, 6.3, base=1.0), 1))
    A.append(life)
    rise = Anim("rise", length=3.0, loop="hold")
    sink = Anim("sink", length=2.4, loop="hold")
    for i, (ang, kind, w, h) in enumerate(HZ):
        H = h * 16
        t0 = 0.12 * ((i * 3) % 10)
        rise.pos(f"p{i + 1}", {0: (0, -H - 10, 0), t0: (0, -H - 10, 0), t0 + 1.6: (0, 6, 0), min(3.0, t0 + 1.9): (0, 0, 0)})
        sink.pos(f"p{i + 1}", {0: (0, 0, 0), 0.1 * i: (0, 4, 0), 0.1 * i + 1.3: (0, -H - 10, 0)})
    A.extend([rise, sink])
    return A


# ============================================================================== fog
FOG_R = 30 * 16.0


def _fog_mat(seed, a0, hole=0.0):
    def fn(ctx):
        u, v = ctx.U * 2 - 1, ctx.V * 2 - 1
        r = np.hypot(u, v)
        n = tex.fbm(ctx.U * 7 + seed, ctx.V * 7, 50 + seed, 4)
        a = a0 * np.clip((n - 0.32) * 2.2, 0, 1) * np.clip((1 - r) * 5, 0, 1) * np.clip((r - hole) * 6, 0, 1)
        t = T(ctx, mix(rgb("#c8d2bc"), rgb("#e8eedc"), n[..., None]), 0.08, 0)
        t[..., 3] = a
        return t
    return Mat(fn, f"ed6fog{seed}{a0}{hole}", mode="blend")


def _curtain_mat():
    def fn(ctx):
        u, v = ctx.U, 1 - ctx.V
        n = tex.fbm(u * 6, v * 3, 77, 3)
        a = 0.42 * np.clip(1 - v, 0, 1) ** 1.6 * (0.5 + 0.7 * n) * np.clip(np.minimum(u, 1 - u) * 6, 0, 1)
        t = T(ctx, mix(rgb("#b8c4ac"), rgb("#dfe6d2"), v[..., None]), 0.06, 0)
        t[..., 3] = np.clip(a, 0, 1)
        return t
    return Mat(fn, "ed6curtain", mode="blend")


def fog_model():
    m = Model("ed6_fog", density=0.09, bounds=(70, 10, (0, 2, 0)))
    root = m.bone("root")
    D = FOG_R * 2
    for i, (y, a, hole) in enumerate(((5, 0.3, 0.0), (10, 0.24, 0.06), (15, 0.2, 0.12), (21, 0.16, 0.2))):
        b = m.bone(f"layer{i + 1}", root, pivot=(0, y, 0))
        b.plane("y", (0, y, 0), D * (1 - 0.04 * i), D * (1 - 0.04 * i), _fog_mat(i * 13, a, hole), faces=("up",))
    cur = m.bone("curtain", root)
    n = 14
    for k in range(n):
        a = k * 360 / n
        cb = m.bone(f"cur{k + 1}", cur, pivot=(0, 0, 0), rot=(0, a, 0))
        cb.plane("z", (0, 56, -FOG_R * 0.98), 2 * math.pi * FOG_R / n * 1.15, 112, _curtain_mat(), variant=k % 3)
    return m


def fog_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    drift = Anim("drift", loop=True)
    for i in range(4):
        drift.rot(f"layer{i + 1}", (0, spin((3.0 + i) * (1 if i % 2 else -1)), 0))
    drift.rot("curtain", (0, spin(1.5), 0))
    A.append(drift)
    for lvl in range(1, 5):
        a = Anim(f"lv{lvl}", loop=True)
        for i in range(4):
            a.scl(f"layer{i + 1}", (1.0, 1.0, 1.0) if i < lvl else (0.0, 0.0, 0.0))
        a.scl("curtain", (1.0, 0.25 + 0.25 * lvl, 1.0))
        A.append(a)
    clear = Anim("clear", length=2.5, loop="hold")
    clear.scl("root", {0: 1.0, 2.5: (1.25, 0.0, 1.25)})
    clear.pos("root", {0: (0, 0, 0), 2.5: (0, -6, 0)})
    A.append(clear)
    return A


FOG_STATES = {0: ["hidden"], 1: {"animations": ["lv1"], "blend": 1.2}, 2: {"animations": ["lv2"], "blend": 1.2},
              3: {"animations": ["lv3"], "blend": 1.2}, 4: {"animations": ["lv4"], "blend": 1.2},
              5: {"animations": ["lv4", "clear"], "blend": 0.2}}

# ============================================================================== flora
NF = 12


def frond_mat(c0, c1, stiff=False, key="fr"):
    """Pinnate frond on a plane: rachis down the long axis (tile V), leaflets tapering to the tip."""
    k0, k1 = rgb(c0), rgb(c1)

    def fn(ctx):
        u, v = ctx.U * 2 - 1, ctx.V              # v = 0 at the base (tile top), 1 at the tip
        ix, iy = px(ctx)
        width = (1 - v) ** (0.5 if stiff else 0.8) * np.clip(v * 6, 0, 1)
        rach = np.abs(u) < 0.07
        per = 7 if stiff else 5
        seg = ((iy + np.abs(u) * ctx.h * (0.35 if stiff else 0.6)) % per) < (per - 2)
        leaf = (np.abs(u) < width) & seg
        t = T(ctx, mix(k0, k1, (np.abs(u) * 0.8 + tex._hash(ix, iy // per, 3) * 0.3)[..., None]))
        t[..., :3] = np.where(rach[..., None], k0 * 0.7, t[..., :3])
        t[..., 3] = (leaf | (rach & (v < 0.97))) * 1.0
        return tex.grain(ctx, t, 0.05)
    return Mat(fn, f"ed6frond{key}{c0}{c1}{stiff}", directional=True)


def _bark(kind):
    if kind == 0:   # tree-fern: shaggy fibrous trunk with leaf scars
        return tex.overlay(tex.wood("#4a3420", "#2a1c10", vertical=True),
                           lambda c, t: _scars(c, t, "#6a5232"), "ed6tfbark")
    if kind == 1:   # cycad: diamond leaf-base armour
        return tex.scales("#6a5a3a", "#3a2e1c", "#8a7a52", size=4)
    return tex.mottled("#5a7a34", "#7a9a4a", scale=2.0)


def _scars(ctx, t, col):
    ix, iy = px(ctx)
    m = ((ix + (iy // 3) * 2) % 5 == 0) & (iy % 3 == 0)
    t[..., :3] = np.where(m[..., None], rgb(col), t[..., :3])
    return t


def flora_model(kind):
    m = Model(f"ed6_flora_{kind}", density=1.0, bounds=(10, 8, (0, 3, 0)))
    root = m.bone("root")
    base = m.bone("base", root)
    green = [("#2f5a1e", "#7ab84a"), ("#3a5a22", "#8ab858"), ("#3a6a2a", "#6aa83a"), ("#2a5420", "#86c050")][kind]
    fr = frond_mat(*green, stiff=(kind == 1), key=str(kind))
    fr2 = frond_mat("#44622a", "#a0c860", stiff=(kind == 1), key=f"{kind}b")
    moss = tex.mottled("#4a5a3a", "#6f8a3a", scale=1.5, thresh=0.55)
    rock = tex.stone("#6a6458", "#4a443c", "#8a8274", scale=2, cracks=0.2)
    crown_y = 0.0
    if kind in (0, 1):
        H = [26, 24, 22] if kind == 0 else [12, 10, 8]
        Wd = [4.6, 4.0, 3.6] if kind == 0 else [10, 9, 7.5]
        y = 0.0
        par = base
        for i in range(3):
            st = m.bone(f"stem{i + 1}", par, pivot=(0, y, 0))
            st.box((0, y + H[i] / 2, 0), (Wd[i], H[i], Wd[i]), _bark(kind), variant=i)
            if kind == 0:   # shaggy skirt of dead frond bases
                st.box((0, y + H[i] * 0.8, 0), (Wd[i] + 1.6, 3, Wd[i] + 1.6), tex.wood("#5a4024", "#2e1e10"), variant=i)
            y += H[i]
            par = st
        crown_y = y
        base.box((0, 1.0, 0), (Wd[0] + 4, 2, Wd[0] + 4), moss)
        crown = m.bone("crown", par, pivot=(0, crown_y, 0))
        if kind == 1:
            crown.box((0, crown_y + 4, 0), (6, 8, 6), tex.scales("#c86a2a", "#7a3a14", "#f0a050", size=2))   # cone
        n, L, Wf = (10, 46, 15) if kind == 0 else (12, 40, 11)
        for j in range(n):
            ang = j * 360 / n + (j % 2) * 9
            droop = (-38 if kind == 0 else -14) - (j % 3) * 7
            fb = m.bone(f"f{j + 1}", crown, pivot=(0, crown_y, 0), rot=(droop, ang, 0))
            fb.plane("y", (0, crown_y, -L / 2 - 1), Wf, L, fr if j % 2 == 0 else fr2, faces=("up", "down"), variant=j % 3)
            if kind == 0:   # second, arching half of the frond (droops further)
                fb2 = m.bone(f"g{j + 1}", fb, pivot=(0, crown_y, -L - 0.5), rot=(-28, 0, 0))
                fb2.plane("y", (0, crown_y, -L - 0.5 - 12), Wf * 0.55, 24, fr2 if j % 2 == 0 else fr, faces=("up", "down"))
        if kind == 0:       # fiddleheads
            for j in range(3):
                fh = m.bone(f"x{j + 1}", crown, pivot=(0, crown_y, 0), rot=(0, j * 120 + 40, 0))
                fh.box((0, crown_y + 2.5, -2.5), (1.4, 5, 1.4), tex.flat("#5a8a2a"), rot=(-20, 0, 0), pivot=(0, crown_y, -2.5))
                fh.box((0, crown_y + 5.5, -4.2), (3.0, 3.0, 1.6), tex.flat("#7aa83a"))
    elif kind == 2:         # horsetail stand: jointed stems with whorls and strobili
        base.box((0, 1.0, 0), (22, 2, 20), moss)
        rnd = np.random.default_rng(5)
        for j in range(9):
            a, r = j * 40 + rnd.uniform(-12, 12), 3 + (j % 3) * 3.5
            x, z = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
            h = 44 + 22 * rnd.random()
            fb = m.bone(f"f{j + 1}", base, pivot=(x, 0, z), rot=(rnd.uniform(-8, 8), 0, rnd.uniform(-8, 8)))
            fb.box((x, h / 2, z), (2.4, h, 2.4), tex.banded(tex.vgrad("#7aa84a", "#4a7a2a", var=0.04), "#2a3a1a", every=7, width=1))
            for w in range(int(h // 9)):
                yy = 7 + w * 9
                fb.plane("y", (x, yy, z), 9 - w * 0.5, 9 - w * 0.5, tex.shaped(tex.m_star(8, 0.12), "#6a9a3a", "#9ac860"),
                         faces=("up", "down"), variant=w % 2)
            fb.box((x, h + 2.5, z), (3.4, 5, 3.4), tex.scales("#8a6a3a", "#4a361c", "#b8945a", size=2))
    else:                   # giant fern clump around a mossy boulder
        base.box((3, 4, 2), (12, 8, 10), rock, rot=(0, 25, 8))
        base.box((3, 8.4, 2), (10, 1.2, 8), moss, rot=(0, 25, 8))
        for j in range(NF - 2):
            ang = j * 36 + (j % 2) * 14
            fb = m.bone(f"f{j + 1}", base, pivot=(0, 2, 0), rot=(62 - (j % 3) * 9, ang, 0))
            fb.plane("y", (0, 2, -26), 15, 50, fr if j % 2 == 0 else fr2, faces=("up", "down"), variant=j % 3)
            fb2 = m.bone(f"g{j + 1}", fb, pivot=(0, 2, -50), rot=(-70, 0, 0))
            fb2.plane("y", (0, 2, -61), 8, 22, fr2, faces=("up", "down"))
        for j in range(3):
            fh = m.bone(f"x{j + 1}", base, pivot=(-4 + j * 4, 0, -3 + j * 2))
            fh.box((-4 + j * 4, 7, -3 + j * 2), (1.6, 14, 1.6), tex.flat("#5a8a2a"))
            fh.box((-4 + j * 4, 15, -4.5 + j * 2), (4, 4, 1.8), tex.flat("#86b84a"))
    return m


def flora_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    sprout = Anim("sprout", length=2.0, loop="hold")
    sprout.scl("root", {0: 0.15, 0.25: 0.5, 1.3: 1.05, 2.0: 1.0})
    sprout.pos("root", {0: (0, -10, 0), 0.6: (0, 0, 0)})
    for i in range(3):
        sprout.scl(f"stem{i + 1}", {0: (1, 0.1, 1), 0.2 + i * 0.25: (1, 0.1, 1), 0.65 + i * 0.25: (1, 1.06, 1), 1.2 + i * 0.2: 1.0})
    for j in range(NF):
        t0 = 0.7 + (j % 6) * 0.1
        sprout.rot(f"f{j + 1}", {0: (75, 0, 0), t0: (70, 0, 0), t0 + 0.6: (-6, 0, 0), min(2.0, t0 + 0.9): (0, 0, 0)})
        if j < NF - 2:   # only ten second-half frond bones exist in any kind
            sprout.rot(f"g{j + 1}", {0: (110, 0, 0), t0 + 0.2: (100, 0, 0), min(2.0, t0 + 0.9): (0, 0, 0)})
    for j in range(3):
        sprout.scl(f"x{j + 1}", {0: 0.0, 1.0 + j * 0.15: 0.0, 1.6 + j * 0.1: 1.0})
    A.append(sprout)
    sway = Anim("sway", loop=True)
    for j in range(NF):
        sway.rot(f"f{j + 1}", (LIFE(3.5, 2.6 + (j % 4) * 0.37, j * 0.11), 0, LIFE(2.5, 3.3, j * 0.17)))
        if j < NF - 2:
            sway.rot(f"g{j + 1}", (LIFE(5, 2.2, j * 0.13 + 0.2), 0, 0))
    for i in range(3):
        sway.rot(f"stem{i + 1}", (LIFE(0.8, 4.1, i * 0.1), 0, LIFE(1.0, 5.3, i * 0.13)))
    for j in range(3):
        sway.rot(f"x{j + 1}", (LIFE(4, 3.0, j * 0.3), 0, 0))
    A.append(sway)
    wither = Anim("wither", length=1.4, loop="hold")
    for j in range(NF):
        wither.rot(f"f{j + 1}", {0: (0, 0, 0), 0.6: (60, 0, 0)})
        if j < NF - 2:
            wither.rot(f"g{j + 1}", {0: (0, 0, 0), 0.6: (90, 0, 0)})
    wither.scl("root", {0: 1.0, 0.5: 0.95, 1.4: 0.0})
    wither.pos("root", {0: (0, 0, 0), 0.5: (0, 0, 0), 1.4: (0, -14, 0)})
    A.append(wither)
    return A


FLORA_STATES = {0: ["hidden"], 1: ["sprout"], 2: ["sway"], 3: ["wither"]}

# ============================================================================== standing stones
def stone_model():
    m = Model("ed6_stone", density=1.0, bounds=(8, 6, (0, 2, 0)), alts=("glass", "obsidian"))
    root = m.bone("root")
    rub = m.bone("rubble", root)
    mats = [stone_skins(s, key="ed6ms") for s in range(3)]
    rune_on = tex.alt(rune_plate(0, "#7fd0ff", glow=0.7, key="ed6r0"), glass=rune_plate(0, "#fffbe8", glow=1.0, key="ed6r0g"),
                      obsidian=rune_plate(0, "#ff8a3a", glow=0.6, key="ed6r0o"))
    specs = [((0, 0, 0), (12, 56, 9), (0, 10, 3)), ((15, 0, 7), (9, 40, 8), (-6, -25, -7)), ((-12, 0, 9), (8, 30, 7), (8, 40, 12))]
    for i, (p, s, r) in enumerate(specs):
        b = m.bone(f"m{i + 1}", root, pivot=p, rot=r)
        b.box((p[0], p[1] + s[1] / 2 - 2, p[2]), s, mats[i], variant=i)
        b.box((p[0], p[1] + s[1] - 2.5, p[2]), (s[0] - 2, 3, s[2] - 2), mats[(i + 1) % 3], variant=(i + 1) % 3)
        rb = m.bone(f"rn{i + 1}", b, pivot=(p[0], p[1] + s[1] * 0.55, p[2] - s[2] / 2))
        rb.plane("z", (p[0], p[1] + s[1] * 0.55, p[2] - s[2] / 2 - 0.15), s[0] * 0.6, s[0] * 0.85,
                 tex.alt(rune_plate(i * 2 + 1, "#7fd0ff", glow=0.7, key=f"ed6rr{i}"),
                         glass=rune_plate(i * 2 + 1, "#fffbe8", glow=1.0, key=f"ed6rg{i}"),
                         obsidian=rune_plate(i * 2 + 1, "#ff8a3a", glow=0.6, key=f"ed6ro{i}")))
    for k in range(6):
        a = k * 60 + 20
        x, z = 16 * math.cos(math.radians(a)), 16 * math.sin(math.radians(a))
        rub.box((x, 1.5, z), (5 + k % 3, 3 + k % 2, 4 + k % 2), mats[k % 3], rot=(k * 11, k * 37, k * 7), variant=k % 3)
    rub.plane("y", (0, 0.4, 0), 10, 10, rune_on, faces=("up",))
    return m


def stone_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    rise = Anim("rise", length=1.2, loop="hold")
    for i in range(3):
        rise.pos(f"m{i + 1}", {0: (0, -60, 0), 0.1 + i * 0.15: (0, -60, 0), 0.8 + i * 0.12: (0, 2, 0), min(1.2, 1.0 + i * 0.1): (0, 0, 0)})
    rise.scl("rubble", {0: 0.0, 0.5: 1.1, 0.8: 1.0})
    A.append(rise)
    hold = Anim("hold", loop=True)
    for i in range(3):
        hold.scl(f"rn{i + 1}", LIFE(0.05, 2.0 + i * 0.3, base=1.0))
    A.append(hold)
    flare = Anim("flare", length=0.5, loop="hold")
    for i in range(3):
        flare.pos(f"m{i + 1}", {0: (0, 0, 0), 0.06: (0.6, 0.4, -0.4), 0.14: (-0.4, 0, 0.3), 0.3: (0, 0, 0)})
        flare.scl(f"m{i + 1}", {0: 1.0, 0.08: 1.04, 0.3: 1.0})
    A.append(flare)
    sink = Anim("sink", length=1.0, loop="hold")
    for i in range(3):
        sink.pos(f"m{i + 1}", {0: (0, 0, 0), 0.1 * i: (0, 1, 0), 0.8 + 0.06 * i: (0, -60, 0)})
    sink.scl("rubble", {0: 1.0, 0.8: 0.0})
    A.append(sink)
    return A


STONE_STATES = {0: ["hidden"], 1: ["rise"], 2: ["hold"], 3: ["sink"], 4: ["flare"]}


# ============================================================================== build
def build(pack):
    hm = horizon_model()
    ha = horizon_anims()
    pack.actor("ed6_horizon", hm, ha, {0: ["hidden"], 1: ["rise"], 2: ["hold"], 3: ["sink"]}, always=["life"], lifetime=150,
               display="Primordial Horizon", blend=0.3)
    fm = fog_model()
    fa = fog_anims()
    pack.actor("ed6_fog", fm, fa, FOG_STATES, always=["drift"], lifetime=150, display="Primordial Mist", blend=1.2)
    fl = [flora_model(k) for k in range(4)]
    fla = flora_anims()
    pack.actor("ed6_flora", fl[0], fla, FLORA_STATES, kinds=fl[1:], scale=2.0, lifetime=150, display="Primordial Growth",
               blend=0.3)
    sm = stone_model()
    sa = stone_anims()
    pack.actor("ed6_stone", sm, sa, STONE_STATES, scale=1.0, lifetime=150, display="Standing Stones", blend=0.1)

    hb = {a.name: a for a in ha}
    pack.preview("ed6_horizon", hm, [(hb["hold"], 0)], views=((0, 8), (0, 70)), cell=(640, 360))
    fb = {a.name: a for a in fla}
    import os
    from PIL import Image
    from kit.pack import PREVIEW
    from kit.render import render
    if getattr(pack.preview, "enabled", False):
        out = Image.new("RGBA", (4 * 320, 2 * 320))
        for k in range(4):
            out.paste(render(fl[k], fb["sway"].pose(0.3), yaw=25, pitch=12, size=(320, 320)), (320 * k, 0))
            out.paste(render(fl[k], fb["sprout"].pose(1.1), yaw=25, pitch=12, size=(320, 320)), (320 * k, 320))
        out.save(os.path.join(PREVIEW, "ed6_flora.png"))
        out = Image.new("RGBA", (3 * 320, 320))
        for i, sk in enumerate((None, "glass", "obsidian")):
            out.paste(render(sm, None, yaw=25, pitch=14, size=(320, 320), skin=sk), (320 * i, 0))
        out.save(os.path.join(PREVIEW, "ed6_stone.png"))
        render(fm, {a.name: a for a in fa}["lv4"].pose(0), yaw=20, pitch=25, size=(480, 320)).save(os.path.join(PREVIEW, "ed6_fog.png"))
    print(f"    horizon {hm.cube_count()}c tex {hm.tex_size}; fog {fm.cube_count()}c tex {fm.tex_size}; "
          f"flora {[f.cube_count() for f in fl]}c tex {[f.tex_size for f in fl]}; stone {sm.cube_count()}c")
