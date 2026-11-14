"""ED06 -- dominion structures (Phase III) and the Fourfold Concord set-pieces (Phase IV).

ed6_bridge    crystalline arch bridge laid along -Z: 12 blocks long, 4.5 blocks high at size 1.
              STATES 0 hidden / 1 form (1.2 s, grows from its +Z end to its -Z end) / 2 hold /
              3 shatter (0.8 s)
ed6_debris    aerial debris formation carried by the Air Dragon's wind: a horizontal ring of rock,
              a tilted ring of leaf clumps, a counter-tilted ring of ice and a central helix
              (radius ~4 blocks at size 1, centred ~7 blocks above its origin).
              STATES 0 hidden / 1 lift (1.6 s, lifted off the ground) / 2 orbit / 3 scatter (1.0 s)
ed6_ring      the Nature Dragon's enclosing ring: 8 colossal basalt-strata pillars (~9 blocks tall) on
              radius 6 blocks (size 1), ten slots with the two slots on the actor's front / back axis left
              open as doorways (-Z and +Z), a ground fissure ring.  Skins: 0 stone, 1 'frost' (ice
              sheathed), 2 'glass' (vitrified, glowing).  STATES 0 hidden / 1 rise (1.6 s) / 2 hold /
              3 quake (0.6 s) / 4 burst (1.2 s, pillars thrown outward) / 5 sink (1.0 s)
ed6_iceshell  layered ice formations inside the ring: three concentric shells (radius 2.2 / 3.6 / 5.0
              blocks at size 1).  STATES 0 hidden / 1 grow (2.4 s, layer by layer) / 2 hold /
              3 shatter (0.8 s, fragments fly up into the wind)
ed6_spiral    spiral wind column (16 blocks tall at size 1): three helical wind sheets and orbiting
              ice fragments, leaves and dust.  STATES 0 hidden / 1 form (1.0 s) / 2 spin / 3 burst (0.8 s)
ed6_blast     controlled thermal detonation: an expanding dome of superheated air, a ground shock
              ring and twelve glass spikes thrust outward (radius ~5 blocks at size 1).
              STATES 0 hidden / 1 blast (1.2 s) / 2 hold / 3 fade (1.0 s)
"""
import math

import numpy as np

from kit import tex
from kit.anim import LIFE, Anim, M
from kit.geo import Mat, Model, ring

from .ed6_common import DR, T, mix, px, rgb, rune_plate, spin, stone_skins, worley


def _ice(glow=0.35, key=""):
    return tex.crystal("#e8f8ff", "#6fb2e8", "#ffffff", a=1.0, mode="solid", glow=glow, facets=3.0)


def _ice_blend(a=0.6):
    return tex.crystal("#d4f1ff", "#5aa4e0", "#ffffff", a=a, mode="blend", facets=2.5)


def _wind_mat(key, a=0.5):
    """Translucent streaked wind sheet."""
    def fn(ctx):
        u, v = ctx.U, ctx.V
        ix, iy = px(ctx)
        n = tex.fbm(u * 3, v * 12, 7)
        streak = np.clip(1 - np.abs(((v * 9 + u * 2 + n * 1.5) % 1.0) - 0.5) * 3.2, 0, 1)
        t = T(ctx, mix(rgb("#e4f7ff"), rgb("#ffffff"), streak[..., None]), 0.8, 0)
        t[..., 3] = a * (0.12 + 0.88 * streak ** 1.5) * np.clip(np.minimum(u, 1 - u) * 5, 0, 1)
        return t
    return Mat(fn, f"ed6wind{key}{a}", mode="blend")


# ============================================================================== bridge
BR_N = 12
BR_L = 192.0
BR_H = 72.0


def bridge_model():
    m = Model("ed6_bridge", density=1.0, bounds=(18, 10, (0, 3, -6)))
    root = m.bone("root")
    deck = _ice(0.4)
    rail = tex.crystal("#f6fdff", "#9fd2f4", "#ffffff", a=1.0, mode="solid", glow=0.6, facets=2.0)
    for k in range(BR_N):
        z0 = -BR_L * k / BR_N
        z1 = -BR_L * (k + 1) / BR_N
        y0 = BR_H * math.sin(math.pi * k / BR_N)
        y1 = BR_H * math.sin(math.pi * (k + 1) / BR_N)
        slope = math.degrees(math.atan2(y1 - y0, z0 - z1))
        b = m.bone(f"s{k + 1}", root, pivot=(0, y0, z0))
        c = (0, (y0 + y1) / 2, (z0 + z1) / 2)
        L = math.hypot(y1 - y0, z1 - z0) + 1.0
        b.box(c, (24, 4, L), deck, rot=(slope, 0, 0), pivot=c, variant=k % 3)
        for s in (1, -1):        # crystal railing spikes
            b.box((s * 11, c[1] + 6, c[2]), (2.2, 10, 2.2), rail, rot=(slope + 12 * s, 0, s * 14), pivot=(s * 11, c[1] + 1, c[2]),
                  variant=k % 2)
        ic = m.bone(f"ic{k + 1}", b, pivot=c)
        for j, x in enumerate((-8, 0, 8)):     # hanging icicles
            h = 8 + 6 * ((k + j) % 3)
            ic.box((x, c[1] - 2 - h / 2, c[2]), (2.6, h, 2.6), _ice_blend(0.65), rot=(0, 45, 0), pivot=(x, c[1], c[2]),
                   variant=j % 3)
    for end, z in (("a", 0.0), ("b", -BR_L)):  # crystalline abutments
        e = m.bone(f"end_{end}", root, pivot=(0, 0, z))
        for j in range(5):
            a = j * 72
            x, dz = 9 * math.cos(math.radians(a)), 9 * math.sin(math.radians(a))
            h = 18 + 8 * (j % 3)
            e.box((x, h / 2 - 2, z + dz), (5, h, 5), rail, rot=(10 * math.sin(a), a, 14 * math.cos(a)), pivot=(x, 0, z + dz),
                  variant=j % 2)
    return m


def bridge_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    form = Anim("form", length=1.2, loop="hold")
    form.scl("end_a", {0: 0.0, 0.2: 1.15, 0.3: 1.0})
    for k in range(BR_N):
        t0 = 0.05 + k * 0.075
        form.scl(f"s{k + 1}", {0: 0.0, t0: 0.0, t0 + 0.12: (1.0, 1.0, 1.15), t0 + 0.2: 1.0})
        form.scl(f"ic{k + 1}", {0: (1, 0, 1), t0 + 0.15: (1, 0, 1), t0 + 0.4: 1.0})
    form.scl("end_b", {0: 0.0, 1.0: 0.0, 1.15: 1.15, 1.2: 1.0})
    A.append(form)
    hold = Anim("hold", loop=True)
    A.append(hold)
    sh = Anim("shatter", length=0.8, loop="hold")
    for k in range(BR_N):
        t0 = 0.03 * abs(k - BR_N / 2)
        sh.pos(f"s{k + 1}", {0: (0, 0, 0), t0: (0, 1, 0), t0 + 0.6: (0, -30, 0)})
        sh.scl(f"s{k + 1}", {0: 1.0, t0 + 0.2: 0.9, t0 + 0.6: 0.0})
        sh.rot(f"s{k + 1}", {0: (0, 0, 0), t0 + 0.6: ((k % 3 - 1) * 40, 0, (k % 2 * 2 - 1) * 30)})
    for e in ("end_a", "end_b"):
        sh.scl(e, {0: 1.0, 0.7: 0.0})
    A.append(sh)
    return A


# ============================================================================== debris formation
def debris_model():
    m = Model("ed6_debris", density=1.0, bounds=(14, 14, (0, 7, 0)))
    root = m.bone("root")
    cy = 112.0
    rock = tex.stone("#7a7064", "#4a443c", "#9a9082", scale=2, cracks=0.3)
    mossr = tex.mottled("#6a6458", "#5a7a34", scale=1.4, thresh=0.5)
    leaf = tex.foliage("#3f7a35", "#8ac05a", holes=0.2)
    ice = _ice(0.45)
    ringspec = [("ra", 0, 64, 10, (0, 0, 0), "rock"), ("rb", 1, 52, 8, (24, 0, 10), "leaf"), ("rc", 2, 44, 8, (-28, 30, -8), "ice")]
    for name, idx, R, n, tilt, kind in ringspec:
        tb = m.bone(f"t_{name}", root, pivot=(0, cy, 0), rot=tilt)
        rb = m.bone(name, tb, pivot=(0, cy, 0))
        for j in range(n):
            a = j * 360 / n + idx * 13
            x, z = R * math.cos(math.radians(a)), R * math.sin(math.radians(a))
            s = 6 + (j % 3) * 3
            if kind == "rock":
                rb.box((x, cy + (j % 2) * 6 - 3, z), (s, s * 0.8, s * 1.1), rock if j % 3 else mossr,
                       rot=(j * 23, j * 41, j * 17), variant=j % 3)
            elif kind == "leaf":
                for q in range(2):
                    rb.plane("y", (x, cy + q * 2, z), s + 4, s + 4, leaf, rot=(30 * q - 15, a + q * 60, 20), pivot=(x, cy, z),
                             faces=("up", "down"), variant=(j + q) % 3)
            else:
                rb.box((x, cy, z), (3, s + 5, 3), ice, rot=(j * 31, a, 35), pivot=(x, cy, z), variant=j % 2)
    hx = m.bone("helix", root, pivot=(0, cy, 0))
    for j in range(10):
        a = j * 70
        y = cy - 60 + j * 13
        r = 14 + j * 1.5
        mat = (rock, leaf, ice)[j % 3]
        if j % 3 == 1:
            hx.plane("y", (r * math.cos(math.radians(a)), y, r * math.sin(math.radians(a))), 8, 8, leaf, faces=("up", "down"),
                     rot=(25, a, 0), pivot=(r * math.cos(math.radians(a)), y, r * math.sin(math.radians(a))))
        else:
            hx.box((r * math.cos(math.radians(a)), y, r * math.sin(math.radians(a))), (4, 4, 4), mat, rot=(j * 30, a, j * 13),
                   variant=j % 2)
    sw = m.bone("swirl", root, pivot=(0, cy, 0))
    for j in range(3):
        sw.plane("y", (0, cy - 10 + j * 10, 0), 150 - j * 24, 150 - j * 24, tex.shaped(tex.m_ring(0.82, 0.92), "#e8f8ff", "#ffffff",
                                                                                     glow=0.6, a=0.45, mode="blend",
                                                                                     key=f"ed6swr{j}"), faces=("up",))
    return m


def debris_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    sp = Anim("spin", loop=True)
    sp.rot("ra", (0, spin(42), 0))
    sp.rot("rb", (0, spin(-58), 0))
    sp.rot("rc", (0, spin(75), 0))
    sp.rot("helix", (0, spin(-90), 0))
    sp.rot("swirl", (0, spin(140), 0))
    sp.pos("root", (0, LIFE(3, 4.0), 0))
    A.append(sp)
    lift = Anim("lift", length=1.6, loop="hold")
    for i, b in enumerate(("ra", "rb", "rc", "helix")):
        lift.pos(b, {0: (0, -110, 0), 0.15 * i: (0, -110, 0), 1.1 + 0.1 * i: (0, 6, 0), 1.6: (0, 0, 0)})
        lift.scl(b, {0: 0.4, 0.15 * i: 0.4, 1.2 + 0.1 * i: 1.05, 1.6: 1.0})
    lift.scl("swirl", {0: 0.0, 0.8: 0.0, 1.4: 1.1, 1.6: 1.0})
    A.append(lift)
    orbit = Anim("orbit", loop=True)
    A.append(orbit)
    sc = Anim("scatter", length=1.0, loop="hold")
    for i, b in enumerate(("ra", "rb", "rc", "helix")):
        sc.scl(b, {0: 1.0, 0.2: 1.4 + 0.2 * i, 1.0: 2.2})
        sc.pos(b, {0: (0, 0, 0), 0.2: (0, 6, 0), 1.0: (0, -120, 0)})
    sc.scl("swirl", {0: 1.0, 0.3: 0.0})
    sc.scl("root", {0: 1.0, 0.75: 1.0, 1.0: 0.0})
    A.append(sc)
    return A


# ============================================================================== pillar ring
RING_R = 96.0
RING_SLOTS = 10            # slots 0 (-Z) and 5 (+Z) are doorways


def _strata_basalt(seed):
    """Column of stacked strata: basalt, ochre, sandstone, moss; skins frost / glass."""
    bands = [rgb(c) for c in ("#3b3a3c", "#6a6460", "#b89a68", "#8f6a42", "#4a4844", "#a07a4a")]

    def fn(ctx):
        ix, iy = px(ctx)
        n = tex.fbm(ix / 3.0 + seed, iy / 3.0, 61 + seed)
        y = ctx.Y
        bi = np.floor(y / 9.0 + n * 0.8 + seed).astype(int) % len(bands)
        col = np.array(bands)[bi]
        col = col * (0.85 + 0.25 * n)[..., None]
        f1, e = worley(ix, iy, 6, 9 + seed)
        crack = e < 0.6
        if ctx.alt == "glass":
            col = mix(rgb("#ffc060"), rgb("#b8380c"), np.clip(n * 1.3 - 0.1, 0, 1)[..., None])
            col = mix(col, rgb("#fff0c0"), (np.clip(1 - f1 / 4.0, 0, 1) * 0.35)[..., None])
            t = T(ctx, col, 0.65)
            thin = crack & (tex.fbm(ix / 4.0, iy / 4.0, 3 + seed) > 0.45)
            t[..., :3] = np.where(thin[..., None], rgb("#fffbe8"), t[..., :3])
            t[..., 4] = np.where(thin, 1.0, 0.65)
            return t
        t = T(ctx, np.clip(col, 0, 1))
        t[..., :3] = np.where(crack[..., None], t[..., :3] * 0.6, t[..., :3])
        if ctx.alt == "frost":
            fr = (tex.fbm(ix / 2.0, iy / 2.0, 19) > 0.42) | (ctx.V < 0.25)
            t[..., :3] = np.where(fr[..., None], mix(rgb("#e8f8ff"), rgb("#9fd2f4"), tex._hash(ix, iy, 5)[..., None] * 0.6),
                                  t[..., :3])
            t[..., 4] = np.where(fr, 0.3, 0.0)
        return tex.grain(ctx, t, 0.05)
    return Mat(fn, f"ed6strb{seed}", spatial=True)


def _fissure_ring():
    def fn(ctx):
        u, v = ctx.U * 2 - 1, ctx.V * 2 - 1
        r = np.hypot(u, v)
        a = np.arctan2(v, u)
        n = tex.fbm(u * 8, v * 8, 4)
        main = np.abs(r - (0.86 + 0.03 * np.sin(a * 9) + 0.02 * (n - 0.5))) < 0.012
        spokes = (np.abs(np.sin(a * 13 + n * 3)) < 0.06) & (r > 0.62) & (r < 0.98) & (n > 0.45)
        inner = np.abs(r - (0.6 + 0.02 * np.sin(a * 17))) < 0.008
        on = main | spokes | inner
        t = T(ctx, mix(rgb("#fff2c8"), rgb("#ffb24a"), np.clip((r - 0.6) * 2.5, 0, 1)[..., None]), 1.0, 0)
        t[..., 3] = on * 1.0
        return t
    return Mat(fn, "ed6fissure", directional=True)


def ring_model():
    m = Model("ed6_ring", density=1.0, bounds=(18, 12, (0, 4, 0)), alts=("frost", "glass"))
    root = m.bone("root")
    fis = m.bone("fissure", root)
    fis.plane("y", (0, 0.3, 0), 2 * RING_R * 1.18, 2 * RING_R * 1.18, _fissure_ring(), faces=("up",), density=0.5)
    vine = tex.foliage("#2f5a1e", "#6a9a3a", holes=0.35)
    pi = 0
    for slot in range(RING_SLOTS):
        if slot in (0, 5):
            continue
        pi += 1
        a = slot * 360 / RING_SLOTS
        b = m.bone(f"p{pi}", root, pivot=(0, 0, 0), rot=(0, a, 0))
        z = -RING_R
        base = m.bone(f"pb{pi}", b, pivot=(0, 0, z))
        H = 128 + 20 * ((pi * 3) % 3)
        for j, (dx, dz, w, h, lean) in enumerate(((0, 0, 22, H, 0), (-14, 5, 15, H * 0.78, -6), (14, 4, 16, H * 0.64, 7),
                                                   (2, 9, 12, H * 0.5, 3))):
            base.box((dx, h / 2, z + dz), (w, h, w * 0.9), _strata_basalt(pi * 3 + j), rot=(lean * 0.5, 30 * j, lean),
                     pivot=(dx, 0, z + dz), density=0.6)
        base.box((0, H + 4, z), (26, 8, 22), _strata_basalt(pi + 40), rot=(0, 15, 6), pivot=(0, H, z), density=0.6)   # cap stone
        base.plane("z", (0, H * 0.6, z - 10.5), 12, 16, tex.alt(rune_plate(pi, "#c8ff9a", glow=1.0, key=f"ed6rgr{pi}"),
                                                               frost=rune_plate(pi, "#dff8ff", glow=1.0, key=f"ed6rgf{pi}"),
                                                               glass=rune_plate(pi, "#ffffff", glow=1.0, key=f"ed6rgg{pi}")))
        base.plane("z", (0, H * 0.35, z - 11.0), 20, H * 0.5, vine, variant=pi % 3)                         # hanging roots / moss
        for k in range(3):
            base.box((-16 + k * 16, 3.5, z - 13 + (k % 2) * 4), (9, 7, 9), _strata_basalt(pi + 60 + k), rot=(k * 20, k * 35, 0),
                     density=0.6)
    return m


def ring_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    rise = Anim("rise", length=1.6, loop="hold")
    rise.scl("fissure", {0: 0.0, 0.3: 1.1, 0.5: 1.0})
    for i in range(1, 9):
        t0 = 0.1 + (i - 1) * 0.1
        rise.pos(f"pb{i}", {0: (0, -170, 0), t0: (0, -170, 0), t0 + 0.55: (0, 8, 0), t0 + 0.75: (0, -2, 0), min(1.6, t0 + 0.9): (0, 0, 0)})
        rise.rot(f"pb{i}", {0: (12, 0, 0), t0 + 0.55: (-3, 0, 0), min(1.6, t0 + 0.9): (0, 0, 0)})
    A.append(rise)
    hold = Anim("hold", loop=True)
    A.append(hold)
    quake = Anim("quake", length=0.6, loop="hold")
    quake.scl("fissure", {0: 1.0, 0.08: 1.2, 0.4: 1.0})
    for i in range(1, 9):
        quake.pos(f"pb{i}", {0: (0, 0, 0), 0.05: (0, 6, 1.5), 0.16: (0, -2, -0.5), 0.3: (0, 1, 0), 0.6: (0, 0, 0)})
        quake.rot(f"pb{i}", {0: (0, 0, 0), 0.05: (-4, 0, 2), 0.2: (3, 0, -1), 0.6: (0, 0, 0)})
    A.append(quake)
    burst = Anim("burst", length=1.2, loop="hold")
    for i in range(1, 9):
        t0 = 0.02 * (i % 4)
        burst.rot(f"pb{i}", {0: (0, 0, 0), t0 + 0.12: (8, 0, 0), t0 + 0.7: (-70, 0, (i % 3 - 1) * 20), 1.2: (-95, 0, 0)})
        burst.pos(f"pb{i}", {0: (0, 0, 0), t0 + 0.12: (0, 10, 0), t0 + 0.7: (0, 4, -40), 1.2: (0, -50, -60)})
        burst.scl(f"pb{i}", {0: 1.0, 0.8: 0.9, 1.2: 0.0})
    burst.scl("fissure", {0: 1.0, 0.15: 1.3, 1.0: 0.0})
    A.append(burst)
    sink = Anim("sink", length=1.0, loop="hold")
    for i in range(1, 9):
        sink.pos(f"pb{i}", {0: (0, 0, 0), 0.9: (0, -170, 0)})
    sink.scl("fissure", {0: 1.0, 0.8: 0.0})
    A.append(sink)
    return A


# ============================================================================== ice shells
SHELLS = [(35.0, 10, 16, 36), (58.0, 14, 26, 50), (80.0, 18, 36, 66)]   # radius, n slabs, height min, max


def iceshell_model():
    m = Model("ed6_iceshell", density=1.0, bounds=(14, 7, (0, 2, 0)))
    root = m.bone("root")
    frost = m.bone("frost", root)
    frost.plane("y", (0, 0.25, 0), 180, 180, tex.shaped(lambda u, v: (np.hypot(u, v) < 0.98) & (tex.fbm(u * 6 + 3, v * 6, 2) > 0.38),
                                                         "#f4fcff", "#9fd2f4", glow=0.35, key="ed6frostdisc"), faces=("up",), density=0.5)
    for li, (R, n, h0, h1) in enumerate(SHELLS):
        lb = m.bone(f"layer{li + 1}", root)
        tb = m.bone(f"tr{li + 1}", root)
        for j in range(n):
            a = j * 360 / n + li * 11
            x, z = R * math.cos(math.radians(a)), R * math.sin(math.radians(a))
            h = h0 + (h1 - h0) * (0.5 + 0.5 * math.sin(j * 2.3 + li))
            lean = 18 + 6 * li
            lb.box((x, h / 2 - 2, z), (10 + li * 2, h, 4 + li), _ice(0.3 + 0.1 * li), rot=(0, -a + 90, 0), pivot=(x, 0, z),
                   variant=j % 3)
            # inward lean: tilt the slab around the tangent axis by the bone-free trick of a second rotated box
            tb.box((x * 0.92, h * 0.55, z * 0.92), (5 + li, h * 0.75, 5 + li), _ice_blend(0.55), rot=(lean, -a + 90, 0),
                   pivot=(x, 0, z), variant=j % 3)
    return m


def iceshell_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    grow = Anim("grow", length=2.4, loop="hold")
    grow.scl("frost", {0: 0.0, 0.4: 1.0})
    for li in range(3):
        t0 = 0.05 + li * 0.75
        for b in (f"layer{li + 1}", f"tr{li + 1}"):
            grow.scl(b, {0: (1, 0, 1), t0: (1, 0, 1), t0 + 0.45: (1.04, 1.12, 1.04), t0 + 0.65: 1.0})
    A.append(grow)
    hold = Anim("hold", loop=True)
    A.append(hold)
    sh = Anim("shatter", length=0.8, loop="hold")
    for li in range(3):
        t0 = 0.08 * li
        for b in (f"layer{li + 1}", f"tr{li + 1}"):
            sh.scl(b, {0: 1.0, t0 + 0.1: 1.12, t0 + 0.6: (1.6, 0.0, 1.6)})
            sh.pos(b, {0: (0, 0, 0), t0 + 0.6: (0, 40 + li * 10, 0)})
            sh.rot(b, {0: (0, 0, 0), t0 + 0.6: (0, 60 - li * 40, 0)})
    sh.scl("frost", {0: 1.0, 0.8: 0.0})
    A.append(sh)
    return A


# ============================================================================== spiral wind column
SP_H = 256.0


def spiral_model():
    m = Model("ed6_spiral", density=0.5, bounds=(16, 20, (0, 8, 0)))
    root = m.bone("root")
    col = m.bone("col", root)
    wm = _wind_mat("sp", 0.55)
    for s in range(3):
        hb = m.bone(f"hx{s + 1}", col)
        n = 14
        for j in range(n):
            f = j / n
            y = 8 + f * (SP_H - 16)
            a = s * 120 + f * 540
            r = 26 + 46 * f
            x, z = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
            hb.plane("z", (x, y, z), 30 + 20 * f, 22, wm, rot=(18, -a, 0), pivot=(x, y, z), variant=j % 3)
    core = m.bone("core", col)
    core.plane("x", (0, SP_H / 2, 0), 24, SP_H, _wind_mat("core", 0.35))
    core.plane("z", (0, SP_H / 2, 0), 24, SP_H, _wind_mat("core", 0.35), variant=1)
    ice = _ice(0.5)
    leaf = tex.foliage("#3f7a35", "#8ac05a", holes=0.2)
    dust = tex.mottled("#9a8a72", "#6a5e4e", scale=1.2)
    for o in range(3):
        ob = m.bone(f"orb{o + 1}", root)
        n = 9
        for j in range(n):
            a = j * 360 / n + o * 20
            y = 30 + o * 70 + (j % 3) * 18
            r = 40 + o * 16 + (j % 2) * 8
            x, z = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
            k = (j + o) % 3
            if k == 0:
                ob.box((x, y, z), (3, 12, 3), ice, rot=(j * 29, a, 40), pivot=(x, y, z), variant=j % 2)
            elif k == 1:
                ob.plane("y", (x, y, z), 9, 9, leaf, rot=(30, a, 25), pivot=(x, y, z), faces=("up", "down"), variant=j % 3)
            else:
                ob.box((x, y, z), (5, 4, 5), dust, rot=(j * 17, a, j * 11), variant=j % 2)
    base = m.bone("base", root)
    base.plane("y", (0, 1.0, 0), 200, 200, tex.shaped(tex.m_ring(0.55, 0.95), "#ffffff", "#bfe9ff", glow=0.7, a=0.5, mode="blend",
                                                    key="ed6spbase"), faces=("up",))
    return m


def spiral_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    sp = Anim("whirl", loop=True)
    for s in range(3):
        sp.rot(f"hx{s + 1}", (0, spin(-160 - s * 25), 0))
    sp.rot("core", (0, spin(220), 0))
    for o in range(3):
        sp.rot(f"orb{o + 1}", (0, spin(-120 - o * 45), 0))
        sp.pos(f"orb{o + 1}", (0, LIFE(10, 2.4 + o * 0.5, o * 0.3), 0))
    sp.rot("base", (0, spin(-260), 0))
    A.append(sp)
    form = Anim("form", length=1.0, loop="hold")
    form.scl("col", {0: (0.3, 0.0, 0.3), 0.7: (1.05, 1.0, 1.05), 1.0: 1.0})
    form.scl("base", {0: 0.0, 0.4: 1.2, 0.7: 1.0})
    for o in range(3):
        form.scl(f"orb{o + 1}", {0: 0.0, 0.3 + o * 0.15: 0.0, 0.8 + o * 0.07: 1.0})
    A.append(form)
    spin_s = Anim("spin", loop=True)
    A.append(spin_s)
    burst = Anim("burst", length=0.8, loop="hold")
    burst.scl("col", {0: 1.0, 0.25: (1.5, 1.05, 1.5), 0.8: (2.4, 0.0, 2.4)})
    for o in range(3):
        burst.scl(f"orb{o + 1}", {0: 1.0, 0.6: 2.6, 0.8: 0.0})
    burst.scl("base", {0: 1.0, 0.8: 0.0})
    A.append(burst)
    return A


# ============================================================================== thermal blast
def _heat_shell():
    def fn(ctx):
        u, v = ctx.U, ctx.V
        n = tex.fbm(u * 5, v * 5, 23)
        t = T(ctx, mix(rgb("#ffffff"), rgb("#ff8a2a"), np.clip(v * 1.2 + (n - 0.5) * 0.4, 0, 1)[..., None]), 1.0, 0)
        t[..., 3] = np.clip(0.55 - v * 0.35 + (n - 0.5) * 0.3, 0.05, 0.8)
        return t
    return Mat(fn, "ed6heatshell", mode="blend")


def blast_model():
    m = Model("ed6_blast", density=1.0, bounds=(16, 10, (0, 3, 0)), alts=("cool",))
    root = m.bone("root")
    dome = m.bone("dome", root)
    hs = _heat_shell()
    for li, (lat, n) in enumerate(((10, 14), (35, 12), (60, 9))):
        R = 80.0
        y = R * math.sin(math.radians(lat))
        r = R * math.cos(math.radians(lat))
        ring(dome, (0, y, 0), r, n, (2 * math.pi * r / n * 1.15, 0, 30), hs, axis="y")
    dome.plane("y", (0, 76, 0), 60, 60, tex.shaped(tex.m_disc(0.95), "#fff6dc", "#ffb24a", glow=1.0, a=0.5, mode="blend",
                                                  key="ed6domecap"), faces=("up", "down"))
    core = m.bone("core", root)
    core.box((0, 12, 0), (16, 22, 16), tex.glow_flat("#fff6dc", 1.0, core="#ffffff"))
    shock = m.bone("shock", root)
    shock.plane("y", (0, 0.5, 0), 190, 190, tex.shaped(tex.m_ring(0.8, 0.98), "#ffffff", "#ff9a3a", glow=1.0, key="ed6blring"),
                faces=("up",))
    spk = m.bone("spikes", root)
    glass = tex.alt(tex.crystal("#ffd27a", "#d0400c", "#fffbe8", a=1.0, mode="solid", glow=0.95, facets=2.0),
                    cool=tex.crystal("#3a2a3a", "#120a10", "#9a90b0", a=1.0, mode="solid", glow=0.1, facets=2.0))
    for j in range(12):
        a = j * 30 + (j % 2) * 9
        r = 34 + (j % 3) * 14
        x, z = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
        h = 22 + (j % 4) * 7
        b = m.bone(f"k{j + 1}", spk, pivot=(x, 0, z), rot=(0, -a + 90, 0))
        b.box((x, h / 2, z), (4.5, h, 4.0), glass, rot=(-34, 0, 0), pivot=(x, 0, z), variant=j % 2)
    return m


def blast_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    blast = Anim("blast", length=1.2, loop="hold")
    blast.scl("dome", {0: 0.1, 0.25: 1.0, 0.6: 1.35, 1.2: (1.6, 0.0, 1.6)})
    blast.scl("core", {0: 0.0, 0.08: 1.6, 0.4: 0.6, 0.9: 0.0})
    blast.scl("shock", {0: 0.1, 0.5: 1.3, 1.0: 0.0})
    for j in range(12):
        t0 = 0.08 + (j % 4) * 0.04
        blast.scl(f"k{j + 1}", {0: (1, 0, 1), t0: (1, 0, 1), t0 + 0.15: (1.1, 1.25, 1.1), t0 + 0.35: 1.0})
    A.append(blast)
    hold = Anim("hold", loop=True)
    hold.scl("dome", 0.0)
    hold.scl("core", 0.0)
    hold.scl("shock", 0.0)
    A.append(hold)
    fade = Anim("fade", length=1.0, loop="hold")
    fade.scl("dome", 0.0)
    fade.scl("core", 0.0)
    fade.scl("shock", 0.0)
    for j in range(12):
        fade.pos(f"k{j + 1}", {0: (0, 0, 0), 0.05 * (j % 4): (0, 0, 0), 0.9: (0, -36, 0)})
    A.append(fade)
    return A


# ============================================================================== build
def build(pack):
    bm = bridge_model()
    pack.actor("ed6_bridge", bm, bridge_anims(), {0: ["hidden"], 1: ["form"], 2: ["hold"], 3: ["shatter"]}, size_prop=True,
               lifetime=150, display="Crystalline Bridge", blend=0.1)
    dm = debris_model()
    da = debris_anims()
    pack.actor("ed6_debris", dm, da, {0: ["hidden"], 1: ["lift"], 2: ["orbit"], 3: ["scatter"]}, always=["spin"], size_prop=True,
               lifetime=150, display="Aerial Formation", blend=0.15)
    rm = ring_model()
    ra = ring_anims()
    pack.actor("ed6_ring", rm, ra, {0: ["hidden"], 1: ["rise"], 2: ["hold"], 3: ["quake"], 4: ["burst"], 5: ["sink"]},
               size_prop=True, lifetime=150, display="Enclosing Pillars", blend=0.1)
    im = iceshell_model()
    ia = iceshell_anims()
    pack.actor("ed6_iceshell", im, ia, {0: ["hidden"], 1: ["grow"], 2: ["hold"], 3: ["shatter"]}, size_prop=True, lifetime=150,
               display="Layered Ice", blend=0.1)
    sm = spiral_model()
    sa = spiral_anims()
    pack.actor("ed6_spiral", sm, sa, {0: ["hidden"], 1: ["form"], 2: ["spin"], 3: ["burst"]}, always=["whirl"], size_prop=True,
               lifetime=150, display="Spiral Wind", blend=0.1)
    xm = blast_model()
    xa = blast_anims()
    pack.actor("ed6_blast", xm, xa, {0: ["hidden"], 1: ["blast"], 2: ["hold"], 3: ["fade"]}, size_prop=True, lifetime=150,
               display="Thermal Detonation", blend=0.05)

    import os
    from PIL import Image
    from kit.pack import PREVIEW
    from kit.render import render
    if getattr(pack.preview, "enabled", False):
        items = [(bm, {a.name: a for a in bridge_anims()}["hold"].pose(0), None, (60, 18)),
                 (dm, da[1].pose(0.3), None, (25, 18)),
                 (rm, ra[2].pose(0), None, (20, 28)), (rm, ra[2].pose(0), "glass", (20, 28)),
                 (im, ia[2].pose(0), None, (20, 30)), (sm, sa[1].pose(0.4), None, (20, 10)),
                 (xm, xa[1].pose(0.3), None, (25, 20)), (xm, xa[2].pose(0.3), "cool", (25, 30))]
        out = Image.new("RGBA", (4 * 340, 2 * 340))
        for i, (mdl, pose, skin, (yw, pt)) in enumerate(items):
            out.paste(render(mdl, pose, yaw=yw, pitch=pt, size=(340, 340), skin=skin), (340 * (i % 4), 340 * (i // 4)))
        out.save(os.path.join(PREVIEW, "ed6_concord.png"))
    print(f"    bridge {bm.cube_count()}c, debris {dm.cube_count()}c, ring {rm.cube_count()}c tex {rm.tex_size}, "
          f"iceshell {im.cube_count()}c, spiral {sm.cube_count()}c, blast {xm.cube_count()}c")
