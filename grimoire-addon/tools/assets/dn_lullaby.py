"""DN04 Lullaby and Scream -- the musical tapestry, dream ribbons and nightmare waveform rings.

Original design:
  * dn_lull_tapestry : a great hanging scroll of peach/gold fabric (nine pleated panels on two
    ribbon-bone chains that unfold from a centre panel) carrying a five-line stave on which
    note-shapes travel.  A nightmare layer of indigo bands is WOVEN through it (in front of
    even panels, behind odd ones), carrying a jagged audio waveform, unpicked thread curtains,
    dangling threads and embroidered eyes that tear open.  Texture skin 'torn' bruises, frays
    and holes the dream fabric so the two halves interleave.
  * dn_lull_ribbon   : three helical fabric ribbons (8 fluttering bones each) that spool out
    to an ally and orbit them as a loose cocoon, with a ribbon hem and a star-moon charm.
  * dn_lull_wave     : a ring of audio-waveform bars (glowing strokes + translucent haze)
    whose radius is driven by grimoire:size; bar heights compensate the scale so the wall
    stays ~2-3 blocks tall while the ring expands.
Sound: an original 6/8 lullaby motif (two phrases, 2.0 s each = 40 ticks) on music-box tines
and an 'oo' choir; dissonant versions (detuned doubling, tritone shadows, reversed tails); a
dual composition with an inverted nightmare counter-line, heartbeat and drifting clock; and a
formant-sweep scream with inharmonic bell clusters.
"""
import math

import numpy as np

from kit import glyphs, synth as sy, tex
from kit.anim import LIFE, Anim, M, S
from kit.geo import Mat, Model, ring
from kit.parts import wave

from .a_fx_common import particles

IVORY, PEACH, PINK, GOLD, BLUE = "#f7f0e2", "#ffd9b8", "#e8b4c8", "#e9cf8a", "#bcd6f0"
INDIGO, MAUVE, BURG, AGED, GRAY = "#2a2d52", "#6a4a6e", "#6e2f3a", "#cfc6b0", "#8b8f9a"
DG = {k: glyphs.bitmap(v) for k, v in glyphs.DREAM.items()}
rgb, mix = tex.rgb, tex.mix

# ---------------------------------------------------------------------------- shared timing
PHRASE = 2.0            # seconds per lullaby phrase (two bars of 6/8) == DN04 phraseTicks 40
E8 = PHRASE / 12.0      # one eighth note
UNFURL, DISSONANCE, SCREAM, UNRAVEL = 1.5, 1.6, 0.9, 1.8
WRAP, RECOIL, UNWIND, FADE = 0.8, 0.6, 1.0, 0.35

TAP_STATES = {0: ["hidden"], 1: ["unfurl"], 2: ["lullaby"], 3: ["dissonance"], 4: ["dual"], 5: ["scream"],
              6: ["unravel"]}
RIB_STATES = {0: ["hidden"], 1: ["travel"], 2: ["wrap"], 3: ["orbit"], 4: ["recoil"], 5: ["unwind"]}
WAVE_STATES = {0: ["hidden"], 1: ["scream"], 2: ["faint"], 3: ["fade"]}


def spin(rate):
    return M(f"q.life_time*{rate}", lambda t: t * rate)


def jit(amp, rate, seed):
    """Stepped nightmare jitter: holds a pseudo-random value for 1/rate s, then jumps."""
    return M(f"math.sin(math.floor(q.life_time*{rate})*{seed})*{amp}",
             lambda t: math.sin(math.radians(math.floor(t * rate) * seed)) * amp)


def blink(rate, phase):
    """Mostly open; snaps shut briefly once per cycle."""
    return M(f"1-0.94*math.pow(math.max(0,math.sin(q.life_time*{rate}+{phase})),24)",
             lambda t: 1 - 0.94 * max(0.0, math.sin(math.radians(t * rate + phase))) ** 24)


# ---------------------------------------------------------------------------- painters
def _h(a, k, seed):
    a = np.asarray(a)
    return tex._hash(a, np.full(a.shape, k), seed)


def _stamp(t, bm, x0, y0, color, glow, scale=1):
    if scale > 1:
        bm = np.kron(bm, np.ones((scale, scale), dtype=bool))
    h, w = bm.shape
    H, W = t.shape[:2]
    c = rgb(color)
    for yy in range(h):
        for xx in range(w):
            X, Y = x0 + xx, y0 + yy
            if bm[yy, xx] and 0 <= X < W and 0 <= Y < H:
                t[Y, X, :3] = c
                t[Y, X, 3] = 1.0
                t[Y, X, 4] = glow


def _crescent(t, cx, cy, r, color, glow, off=0.42):
    H, W = t.shape[:2]
    iy, ix = np.mgrid[0:H, 0:W]
    d = np.hypot(ix - cx, iy - cy)
    m = (d <= r) & (np.hypot(ix - cx - r * off, iy - cy - r * 0.15) > r * 0.8)
    t[..., :3] = np.where(m[..., None], rgb(color), t[..., :3])
    t[..., 4] = np.where(m, glow, t[..., 4])


def _bruise(ctx, t, ix, iy, holes=True, stain=MAUVE, k=0.55):
    n = tex.fbm(ix / 4.0 + ctx.variant * 3.1, iy / 4.0, 91)
    blot = np.clip((n - 0.5) * 3.0, 0, 1) * k
    t[..., :3] = mix(t[..., :3], rgb(stain), blot[..., None])
    t[..., 4] *= 1 - blot
    if holes:
        t[..., 3] = np.where(n > 0.74, 0.0, t[..., 3])
    return t


def dream_upper(center):
    def fn(ctx):
        torn = ctx.alt == "torn"
        ix, iy = tex.px(ctx)
        W, H = ctx.w, ctx.h
        t = tex.tile(ctx, PEACH, 1, 0.14)
        t[..., :3] = mix(rgb("#ffeedd"), rgb(PEACH), ctx.V[..., None] ** 0.8)
        t[..., :3] *= (1 - ((ix + iy) % 2) * 0.05)[..., None]
        t[..., :3] = np.clip(t[..., :3] * (1 + 0.07 * np.sin(ctx.U * math.pi * 2 + ctx.variant))[..., None], 0, 1)
        hem = iy < 3
        t[..., :3] = np.where(hem[..., None], rgb(GOLD), t[..., :3])
        t[..., 4] = np.where(hem, 0.55, t[..., 4])
        dots = (iy == 1) & (ix % 3 == 1)
        t[..., :3] = np.where(dots[..., None], rgb("#fff8e6"), t[..., :3])
        if torn:
            t = _bruise(ctx, t, ix, iy)
        # the stave: five gold threads (torn skin: bent into a jagged waveform, broken)
        for k, L in enumerate((0.40, 0.46, 0.52, 0.58, 0.64)):
            if torn:
                tri = np.abs(((ix / 3.0 + ctx.variant * 0.37 + k * 0.5) % 1.0) * 2 - 1)
                row = np.round((L + (tri - 0.5) * 0.07 * (1 + 0.3 * k)) * H).astype(int)
                m = (iy == row) & (_h(ix // 3, k, 7 + ctx.variant) > 0.22)
                col, g = rgb(AGED) * 0.5 + rgb(MAUVE) * 0.5, 0.65
            else:
                m = iy == int(round(L * H))
                col, g = rgb(GOLD), 0.7
            t[..., :3] = np.where(m[..., None], col, t[..., :3])
            t[..., 4] = np.where(m, g, t[..., 4])
            t[..., 3] = np.where(m, 1.0, t[..., 3])
        if center:
            _crescent(t, W * 0.5, H * 0.2, H * 0.14, MAUVE if torn else GOLD, 0.5 if torn else 0.9)
            _stamp(t, DG["star"], W // 2 + 2, int(H * 0.08), PINK, 0.6)
            for x in range(2, W - 2, 5):
                _stamp(t, np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool), x, int(H * 0.78), PINK, 0.5)
        else:
            g = ["moon", "star", "key", "star"][ctx.variant % 4]
            _stamp(t, DG["eye"] if torn and ctx.variant % 2 else DG[g], (W - 7) // 2, int(H * 0.1),
                   BURG if torn else PINK, 0.55)
            for x in range(1 + ctx.variant % 3, W - 2, 6):
                _stamp(t, np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool), x, int(H * 0.8), GOLD if not torn else MAUVE, 0.45)
        return t
    return Mat(fn, f"dl_upper{center}")


def dream_lower(center):
    def fn(ctx):
        torn = ctx.alt == "torn"
        ix, iy = tex.px(ctx)
        W, H = ctx.w, ctx.h
        t = tex.tile(ctx, PEACH, 1, 0.12)
        t[..., :3] = mix(rgb(PEACH), rgb(PINK), ctx.V[..., None])
        t[..., :3] *= (1 - ((ix + iy) % 2) * 0.05 - (ix % 4 == 0) * 0.04)[..., None]
        # scalloped lace hem with a fringe
        sc = (2.6 * np.abs(np.sin(math.pi * (ix + 0.5) / 5.0))).astype(int)
        cut = iy >= H - 1 - sc
        lace = (iy >= H - 6) & ~cut & ((ix + iy) % 3 == 0)
        t[..., :3] = np.where(lace[..., None], rgb(IVORY), t[..., :3])
        t[..., 4] = np.where(lace, 0.6, t[..., 4])
        t[..., 3] = np.where(cut, 0.0, 1.0)
        band = (iy == H - 8) | (iy == 2)
        t[..., :3] = np.where(band[..., None], rgb(GOLD), t[..., :3])
        t[..., 4] = np.where(band, 0.5, t[..., 4])
        if torn:
            st = np.clip(ctx.V * 1.4 - 0.55 + (tex.fbm(ix / 3.0, iy / 3.0, 93 + ctx.variant) - 0.5), 0, 1)
            t[..., :3] = mix(t[..., :3], rgb(INDIGO), st[..., None] * 0.8)
            t = _bruise(ctx, t, ix, iy, stain=BURG, k=0.35)
        if center:
            _stamp(t, DG["eye"], (W - 14) // 2, int(H * 0.3), BURG if torn else GOLD, 0.85, 2)
            _stamp(t, DG["star"], 2, int(H * 0.1), PINK, 0.5)
            _stamp(t, DG["star"], W - 9, int(H * 0.12), BLUE, 0.5)
        else:
            g = ["bed", "window", "door", "stair"][ctx.variant % 4]
            _stamp(t, DG["eye"] if torn else DG[g], (W - 14) // 2, int(H * 0.32), BURG if torn else GOLD,
                   0.6 if torn else 0.75, 2)
            for x in range(2, W - 2, 6):
                _stamp(t, np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]], bool) if torn else
                       np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool), x, int(H * 0.12), BLUE if not torn else MAUVE, 0.5)
        return t
    return Mat(fn, f"dl_lower{center}")


def nm_band():
    """Indigo strip woven through the weave: torn edges and an audio waveform."""
    def fn(ctx):
        ix, iy = tex.px(ctx)
        W, H = ctx.w, ctx.h
        t = tex.tile(ctx, INDIGO, 1, 0.05)
        n = tex.fbm(ix / 3.0 + ctx.variant, iy / 3.0, 95)
        t[..., :3] = mix(rgb(INDIGO), rgb(GRAY), (np.clip(n - 0.55, 0, 1) * 1.6)[..., None])
        jt = (1 + 3 * _h(ix, 0, 97 + ctx.variant)).astype(int)
        jb = (1 + 3 * _h(ix, 1, 98 + ctx.variant)).astype(int)
        t[..., 3] = np.where((iy < jt) | (iy >= H - jb), 0.0, 1.0)
        amp = 2 + (_h(ix, 2, 99 + ctx.variant) ** 1.5) * (H / 2 - 6)
        amp = amp * (0.55 + 0.45 * np.abs(np.sin(ix * 0.7 + ctx.variant)))
        c = H / 2.0
        core = np.abs(iy + 0.5 - c) <= amp
        rim = (np.abs(iy + 0.5 - c) <= amp + 1) & ~core
        t[..., :3] = np.where(rim[..., None], rgb(MAUVE), t[..., :3])
        t[..., 4] = np.where(rim, 0.55, t[..., 4])
        t[..., :3] = np.where(core[..., None], mix(rgb(AGED), rgb("#efe6d2"), (np.abs(iy + 0.5 - c) / (amp + 1))[..., None]), t[..., :3])
        t[..., 4] = np.where(core, 0.95, t[..., 4])
        mid = iy == int(c)
        t[..., :3] = np.where(mid[..., None], rgb("#fff4e0"), t[..., :3])
        t[..., 4] = np.where(mid, 1.0, t[..., 4])
        st = ((ix % 7 == 1) | (ix % 7 == 3)) & ((iy == jt + 1) | (iy == H - jb - 2)) | ((ix % 7 == 2) & ((iy == jt + 2) | (iy == H - jb - 3)))
        t[..., :3] = np.where(st[..., None], rgb(BURG), t[..., :3])
        return t
    return Mat(fn, "dl_nmband")


def nm_threads():
    """Curtain of unpicked threads hanging from the lower panels."""
    def fn(ctx):
        ix, iy = tex.px(ctx)
        W, H = ctx.w, ctx.h
        t = tex.tile(ctx, INDIGO, 0, 0.0)
        on = (ix % 2 == 0) | (_h(ix, 3, 101) > 0.7)
        L = (0.35 + 0.65 * _h(ix, 4, 102 + ctx.variant)) * H
        thr = on & (iy < L)
        cols = [rgb(INDIGO), rgb(MAUVE), rgb(GRAY) * 0.8, rgb(BURG)]
        pick = (_h(ix, 5, 103 + ctx.variant) * 3.99).astype(int)
        cc = np.stack([np.choose(pick, [c[i] for c in cols]) for i in range(3)], -1)
        t[..., :3] = cc
        t[..., 3] = np.where(thr, 1.0, 0.0)
        tip = on & (iy >= L - 2) & (iy < L)
        t[..., :3] = np.where(tip[..., None], rgb(AGED), t[..., :3])
        t[..., 4] = np.where(tip, 0.8, 0.12)
        knot = on & (np.abs(iy - L * 0.5) < 1) & (_h(ix, 6, 104) > 0.5)
        t[..., :3] = np.where(knot[..., None], rgb(BURG), t[..., :3])
        return t
    return Mat(fn, "dl_nmthreads")


def eye_cut(key):
    """Cut-out embroidered nightmare eye (almond with stitched lashes)."""
    def fn(ctx):
        u, v = ctx.U * 2 - 1, 1 - ctx.V * 2
        t = tex.tile(ctx, MAUVE, 0, 0)
        alm = (np.abs(v) <= (1 - u ** 2) * 0.62) & (np.abs(u) <= 0.97)
        rim = (np.abs(v) <= (1 - u ** 2) * 0.62 + 0.16) & ~alm & (np.abs(u) <= 1)
        lash = (v > 0) & ~alm & (np.abs(v - (1 - u ** 2) * 0.62 - 0.25) < 0.12) & (np.abs(np.sin(u * 9)) > 0.75)
        r = np.hypot(u * 1.15, v)
        ir, pu = alm & (r < 0.5), alm & (r < 0.2)
        t[..., :3] = np.where(alm[..., None], rgb(AGED), t[..., :3])
        t[..., :3] = np.where(ir[..., None], mix(rgb("#a8445a"), rgb(BURG), np.clip(r / 0.5, 0, 1)[..., None]), t[..., :3])
        t[..., :3] = np.where(pu[..., None], rgb("#0e0d16"), t[..., :3])
        t[..., :3] = np.where((rim | lash)[..., None], rgb(INDIGO), t[..., :3])
        t[..., 3] = (alm | rim | lash).astype(float)
        t[..., 4] = np.where(ir & ~pu, 0.9, np.where(alm, 0.45, 0.1))
        return t
    return Mat(fn, key, directional=True)


def ribbon_mat(c0, c1, edge, key):
    def fn(ctx):
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, c0, 1, 0.32)
        t[..., :3] = mix(rgb(c0), rgb(c1), np.abs(ctx.V - 0.5)[..., None] * 2)
        sheen = np.exp(-((ctx.V - 0.35 - 0.1 * np.sin(ctx.U * 6 + ctx.variant)) / 0.12) ** 2) * 0.12
        t[..., :3] = np.clip(t[..., :3] + sheen[..., None], 0, 1)
        e = (iy == 0) | (iy == ctx.h - 1)
        t[..., :3] = np.where(e[..., None], rgb(edge), t[..., :3])
        t[..., 4] = np.where(e, 0.8, t[..., 4])
        cy = ctx.h // 2
        q = (ix + ctx.variant * 2) % 7
        star = ((q == 3) & (np.abs(iy - cy) <= 1)) | (((q == 2) | (q == 4)) & (iy == cy))
        t[..., :3] = np.where(star[..., None], rgb("#fff4d8"), t[..., :3])
        t[..., 4] = np.where(star, 0.9, t[..., 4])
        return t
    return Mat(fn, key)


def wave_strokes():
    """Audio-waveform bars: glowing ivory/burgundy strokes, cut-out."""
    def fn(ctx):
        ix, iy = tex.px(ctx)
        W, H = ctx.w, ctx.h
        t = tex.tile(ctx, AGED, 0, 1.0)
        bar = ix % 3 != 2
        idx = ix // 3
        a = 0.18 + 0.8 * _h(idx, 7, 111 + ctx.variant) ** 1.3
        a = a * (0.6 + 0.4 * np.abs(np.sin(idx * 0.9 + ctx.variant)))
        d = np.abs((iy + 0.5) / H - 0.5) * 2
        on = bar & (d <= a)
        f = np.clip(d / np.maximum(a, 1e-3), 0, 1)
        t[..., :3] = mix(rgb("#f4ead6"), rgb(BURG), (f ** 1.6)[..., None])
        tip = on & (d > a - 0.06)
        t[..., :3] = np.where(tip[..., None], rgb("#fff6e8"), t[..., :3])
        t[..., 3] = on.astype(float)
        t[..., 4] = np.where(on, 1.0 - 0.45 * f, 0)
        mid = np.abs((iy + 0.5) / H - 0.5) < 0.012
        t[..., 3] = np.where(mid, 1.0, t[..., 3])
        t[..., :3] = np.where(mid[..., None], rgb("#ffffff"), t[..., :3])
        return t
    return Mat(fn, "dl_wavestroke")


def wave_haze():
    def fn(ctx):
        t = tex.tile(ctx, MAUVE, 0.4, 0)
        d = np.abs(ctx.V - 0.5) * 2
        t[..., :3] = mix(rgb("#8a5a86"), rgb(INDIGO), d[..., None])
        ix, iy = tex.px(ctx)
        t[..., 3] = np.clip(0.55 * (1 - d ** 1.4), 0, 1) * (0.75 + 0.25 * (ix % 2))
        return t
    return Mat(fn, "dl_wavehaze", mode="blend")


# ---------------------------------------------------------------------------- tapestry
SEGW, TOP, MID, BOT = 7.0, 40.0, 22.0, 4.0
ACC = [80, -160, 160, -160]   # accordion fold of each chain joint (right side; mirrored left)
PN = ["c"] + [f"r{i}" for i in range(1, 5)] + [f"l{i}" for i in range(1, 5)]
DIST = {n: (0 if n == "c" else int(n[1])) for n in PN}
CHR, CHL = [f"seg_r{i}" for i in range(1, 5)], [f"seg_l{i}" for i in range(1, 5)]
NM, NML, LOW = [f"nm_{n}" for n in PN], [f"nml_{n}" for n in PN], [f"low_{n}" for n in PN]
NOTES = [f"note_{n}" for n in PN]
EYES = ["eye_c", "eye_r2", "eye_l2", "eye_r3", "eye_l3"]
THR = {n: [f"thr_{n}_{k}" for k in range(1, 4)] for n in ("r1", "r3", "l1", "l3")}
# which stave position each panel's travelling note sits on (melodic contour across the cloth)
NOTE_Y = {"r4": 29.0, "r3": 31.6, "r2": 33.0, "r1": 30.4, "c": 32.2, "l1": 28.4, "l2": 31.0, "l3": 29.6, "l4": 27.8}
NOTE_RUN = 4.4


def tapestry_model():
    m = Model("dn_lull_tapestry", density=3.0, bounds=(10, 8, (0, 2.6, 0)), alts=("torn",))
    up_c, up_s = dream_upper(True), dream_upper(False)
    lo_c, lo_s = dream_lower(True), dream_lower(False)
    band, threads = nm_band(), nm_threads()
    cord = tex.metal(GOLD, "#fff1c8", "#9a7a3a", bands=2.0, glow=0.35)
    bead = tex.porcelain(IVORY, "#e8d8c0", crack=0.0, gilt=GOLD, glow=0.2)
    note = tex.bitmap_cut(["  ## ", "  # #", "  #  ", "  #  ", "###  ", "###  "], "#fffaf0", glow=1.0, color2=GOLD)
    eye_m = eye_cut("dl_eye")
    tassel = tex.bitmap_cut([" ## ", "####", " ## ", " ## ", "####", "# ##", "## #", "# # "], GOLD, glow=0.6,
                            color2="#c99a4a", key="dl_tassel")
    thread_m = tex.alt(tex.flat(MAUVE, 0.2), torn=tex.flat(INDIGO, 0.25))
    knot = tex.flat(BURG, 0.4)
    moon = tex.alt(tex.shaped(tex.m_crescent(0.42), "#fff3cf", GOLD, glow=0.9, var=0, key="dl_moon"),
                   torn=tex.shaped(tex.m_crescent(0.42), AGED, MAUVE, glow=0.55, var=0, outline=BURG, key="dl_moon_t"))
    star = tex.shaped(tex.m_star(5, 0.45), "#ffffff", PINK, glow=1.0, var=0, key="dl_star")
    tie = tex.fabric(PINK, GOLD, 0.06, 2, glow=0.25)
    roll = tex.alt(tex.trimmed(tex.fabric(PEACH, "#f7c9a6", 0.06, 2, glow=0.18), GOLD, 1, 0, glow=0.5),
                   torn=tex.trimmed(tex.fabric("#d9b9a6", MAUVE, 0.08, 2, glow=0.1), INDIGO, 1, 0, glow=0.2))
    fin = tex.shaped(tex.m_crescent(0.42), "#fff3cf", GOLD, glow=0.9, var=0, key="dl_fin")

    root = m.bone("root")
    sheet = m.bone("sheet", root, pivot=(0, TOP, 0))
    hang = m.bone("hanger", sheet, pivot=(0, TOP + 1, 0))
    hang.plane("z", (0, TOP + 9, 0), 13, 13, moon, faces=("north",))
    hang.plane("z", (3.2, TOP + 8, -0.3), 3.4, 3.4, star)
    for sx in (1, -1):
        hang.box((sx * 6, TOP + 3.2, 0), (9.5, 0.7, 0.3), tie, rot=(0, 0, -sx * 22))
    hang.box((0, TOP + 2.6, 0), (1.8, 1.8, 1.8), bead)

    for n in PN:
        d = DIST[n]
        if n == "c":
            seg = m.bone("seg_c", sheet, pivot=(0, TOP, 0))
            xc, sx = 0.0, 1
        else:
            sx = 1 if n[0] == "r" else -1
            par = "sheet" if d == 1 else f"seg_{n[0]}{d - 1}"
            px_ = sx * (SEGW / 2 + (d - 1) * SEGW)
            seg = m.bone(f"seg_{n}", par, pivot=(px_, TOP, 0))
            xc = px_ + sx * SEGW / 2
            seg.box((px_, TOP + 0.5, 0), (1.6, 1.6, 1.6), bead)
        vi = (d * 2 + (0 if sx > 0 else 1)) % 4
        seg.plane("z", (xc, (TOP + MID) / 2, 0), SEGW, TOP - MID, up_c if n == "c" else up_s, variant=vi)
        seg.box((xc, TOP + 0.5, 0), (SEGW, 0.9, 0.9), cord)
        low = m.bone(f"low_{n}", seg, pivot=(xc, MID, 0))
        low.plane("z", (xc, (MID + BOT) / 2, 0), SEGW, MID - BOT, lo_c if n == "c" else lo_s, variant=vi)
        low.plane("z", (xc + sx * SEGW / 2 - sx * 0.6, BOT - 2.2, 0), 1.6, 4.4, tassel)
        front = d % 2 == 0
        nm = m.bone(f"nm_{n}", seg, pivot=(xc, 31, 0))
        nm.plane("z", (xc, 31, -0.45 if front else 0.45), SEGW + 0.5, 12.5, band, variant=vi)
        nml = m.bone(f"nml_{n}", low, pivot=(xc, MID, 0))
        nml.plane("z", (xc, MID - 9.5, 0.45 if front else -0.45), SEGW - 0.4, 19, threads, variant=vi)
        nb = m.bone(f"note_{n}", seg, pivot=(xc, 30, 0))
        ny = NOTE_Y[n]
        for z, fc in ((-0.85, "north"), (0.85, "south")):
            nb.plane("z", (xc + SEGW / 2 - 1.3, ny, z), 2.3, 2.8, note, faces=(fc,))
        if d == 4:   # the rolled-up remainder of the scroll, with moon finials
            xr = xc + sx * (SEGW / 2 + 1.2)
            rb = m.bone(f"roll_{n[0]}", seg, pivot=(xr, TOP, 0))
            rb.box((xr, (TOP + BOT) / 2 + 0.5, 0), (2.8, TOP - BOT + 1, 2.8), roll)
            rb.box((xr, (TOP + BOT) / 2 + 0.5, 0), (2.8, TOP - BOT + 1, 2.8), roll, rot=(0, 45, 0), variant=1)
            for yy in (TOP + 2.2, BOT - 1.6):
                rb.box((xr, yy, 0), (3.6, 1.8, 3.6), cord)
            rb.plane("z", (xr, TOP + 5.6, 0), 4.2, 4.2, fin, faces=("north",))
        if n == "c":
            e = m.bone("eye_c", nm, pivot=(0, 31, -0.9))
            e.plane("z", (0, 31, -0.9), 7.5, 4.6, eye_m)
        if n in ("r2", "l2"):
            e = m.bone(f"eye_{n}", nm, pivot=(xc, 31.5, -0.9))
            e.plane("z", (xc, 31.5, -0.9), 5.0, 3.0, eye_m)
        if n in ("r3", "l3"):
            e = m.bone(f"eye_{n}", nml, pivot=(xc, MID - 6, -0.9))
            e.plane("z", (xc, MID - 6, -0.9), 4.4, 2.8, eye_m)
        if n in THR:
            par = nml.name
            x0 = xc - sx * 1.6
            for k in range(3):
                y0 = BOT - k * 5.0
                b = m.bone(THR[n][k], par, pivot=(x0, y0, 0.0))
                b.box((x0, y0 - 2.5, 0), (0.5, 5.0, 0.5), thread_m)
                if k == 2:
                    b.box((x0, y0 - 5.3, 0), (1.2, 1.2, 1.2), knot)
                par = b.name
    m.bones["sheet"].locator("tap_core", (0, 30, -2))
    return m


def _hide_nm(a):
    a.scl(NM + NML, 0.0)


def _chain_wave(a, amp, period, lag=0.1):
    wave(a, CHR, 1, amp, period, lag, clock="q.life_time")
    wave(a, CHL, 1, -amp, period, lag, clock="q.life_time")


def _lows(a, amp, period, lag=0.07):
    for n in PN:
        a.rot(f"low_{n}", (S(amp, period, -DIST[n] * lag, clock="q.life_time"), 0, 0))


def tapestry_anims():
    A = []
    breathe = Anim("breathe", loop=True)
    breathe.pos("sheet", (0, LIFE(1.0, 4.0), 0))
    for n in PN:   # notes travel along the stave toward the viewer's right, one per panel, seamless
        run = M(f"math.mod(q.life_time*{NOTE_RUN},{NOTE_RUN})", lambda t: (t * NOTE_RUN) % NOTE_RUN)
        breathe.pos(f"note_{n}", (-1 * run, LIFE(0.35, 1.0, DIST[n] * 0.13), 0))
        breathe.scl(f"note_{n}", M(f"math.clamp(math.sin(math.mod(q.life_time*{NOTE_RUN},{NOTE_RUN})/{NOTE_RUN}*180)*3,0,1)",
                                   lambda t: min(1, max(0, math.sin(((t * NOTE_RUN) % NOTE_RUN) / NOTE_RUN * math.pi) * 3))))
    A.append(breathe)

    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    u = Anim("unfurl", UNFURL, "hold")
    u.pos("root", {0: (0, -30, 10), 0.7: (0, 3, 0), 1.5: (0, 0, 0)})
    u.scl("root", {0: 0.05, 0.5: 0.55, 1.1: 1.05, 1.5: 1.0})
    u.rot("root", {0: (0, -160, 0), 1.0: (0, 8, 0), 1.5: (0, 0, 0)})
    for i in range(4):
        t0 = 0.45 + i * 0.18
        keys = {0: (0, ACC[i], 0), t0: (0, ACC[i], 0), t0 + 0.4: (0, -ACC[i] * 0.06, 0), 1.5: (0, 0, 0)}
        u.rot(CHR[i], keys)
        u.rot(CHL[i], {k: (0, -v[1], 0) for k, v in keys.items()})
    for n in PN:
        u.rot(f"low_{n}", {0: (-165, 0, 0), 0.55 + DIST[n] * 0.08: (-165, 0, 0), 1.15 + DIST[n] * 0.05: (14, 0, 0), 1.5: (0, 0, 0)})
    u.scl("hanger", {0: 0.0, 0.9: 0.0, 1.2: 1.3, 1.5: 1.0})
    u.rot("hanger", {0: (0, 0, 0), 0.9: (0, 0, -30), 1.5: (0, 0, 0)})
    _hide_nm(u)
    A.append(u)

    lull = Anim("lullaby", 4.0, True)
    _chain_wave(lull, 9, 4.0)
    _lows(lull, 8, 2.0)
    lull.rot("sheet", (LIFE(2.0, 4.0), 0, LIFE(1.2, 6.0)))
    lull.rot("hanger", (0, 0, LIFE(5, 4.0, 0.2)))
    _hide_nm(lull)
    A.append(lull)

    dis = Anim("dissonance", DISSONANCE, "hold")
    _chain_wave(dis, 4, 4.0)
    _lows(dis, 7, 1.0, 0.11)
    dis.rot("sheet", {0: (0, 0, 0), 0.22: (-7, 0, 4), 0.3: (5, 0, -5), 0.42: (-3, 0, 3), 0.6: (2, 0, -1), 0.95: (-4, 0, 2),
                      1.05: (3, 0, -2), 1.6: (0, 0, 0)}, smooth=False)
    for n in PN:
        s = DIST[n] * 0.06
        dis.scl(f"nm_{n}", {0: (1, 0, 1), 0.2 + s: (1, 0.55, 1), 0.32 + s: (1, 0.1, 1), 0.6 + s: (1, 0.95, 1), 0.75 + s: (1, 0.5, 1),
                            1.2 + s: (1, 1, 1), 1.6: (1, 1, 1)}, smooth=False)
        dis.scl(f"nml_{n}", {0: (1, 0, 1), 0.5 + s: (1, 0, 1), 1.1 + s: (1, 1.05, 1), 1.6: (1, 1, 1)})
    for e in EYES:
        dis.scl(e, {0: (1, 0.06, 1), 0.95: (1, 0.06, 1), 1.05: (1.15, 1.35, 1.15), 1.2: (1, 0.85, 1), 1.6: (1, 1, 1)})
    for n, ch in THR.items():
        for k, b in enumerate(ch):
            dis.rot(b, (S(10 + k * 4, 0.8, -k * 0.2), 0, 0))
    A.append(dis)

    dual = Anim("dual", 4.0, True)
    _chain_wave(dual, 8, 4.0)
    _lows(dual, 7, 2.0)
    dual.rot("sheet", (LIFE(1.5, 4.0), 0, LIFE(1.0, 6.0) + jit(0.8, 4, 77)))
    dual.rot("hanger", (0, 0, LIFE(4, 4.0) + jit(2.5, 3, 31)))
    for i, n in enumerate(PN):
        dual.rot(f"nm_{n}", (0, 0, jit(3.0, 6, 37 + i * 23)))
        dual.pos(f"nm_{n}", (0, jit(0.6, 5, 59 + i * 17), 0))
        dual.scl(f"nm_{n}", (1, 1 + jit(0.14, 8, 83 + i * 29), 1))
        dual.rot(f"nml_{n}", (jit(7, 5, 41 + i * 13), 0, 0))
        dual.scl(f"nml_{n}", (1, 1 + jit(0.16, 4, 67 + i * 11), 1))
    for i, e in enumerate(EYES):
        dual.scl(e, (1, blink(70 + i * 9, i * 67), 1))
        dual.pos(e, (jit(0.45, 2.5, 11 + i * 31), 0, 0))
    for j, (n, ch) in enumerate(THR.items()):
        wave(dual, ch, 0, 13, 1.1, 0.2, grow=1.2, clock="q.life_time")
    A.append(dual)

    sc = Anim("scream", SCREAM, "hold")   # inhale (0-0.26), shriek peak at 0.30-0.36 s (script: screamLead 6 ticks)
    sc.rot("sheet", {0: (0, 0, 0), 0.26: (12, 0, 0), 0.36: (-18, 0, 0), 0.55: (-7, 0, 0), 0.9: (0, 0, 0)})
    sc.pos("sheet", {0: (0, 0, 0), 0.26: (0, 2.5, 4), 0.36: (0, -1, -5), 0.9: (0, 0, 0)})
    for i in range(4):
        z = 22 * (-1) ** i
        keys = {0: (0, 0, 0), 0.26: (0, -5, 0), 0.36: (0, z, 0), 0.6: (0, z * 0.4, 0), 0.9: (0, 0, 0)}
        sc.rot(CHR[i], keys)
        sc.rot(CHL[i], {k: (0, -v[1], 0) for k, v in keys.items()})
    for n in PN:   # the dream half recoils from the shriek...
        sc.rot(f"low_{n}", {0: (0, 0, 0), 0.26: (8, 0, 0), 0.36 + DIST[n] * 0.02: (-42, 0, 0), 0.6: (-22, 0, 0), 0.9: (0, 0, 0)})
        # ...while the nightmare half lunges through it
        sc.scl(f"nm_{n}", {0: (1, 1, 1), 0.26: (1, 0.6, 1), 0.34: (1.12, 2.0, 1.12), 0.5: (1, 1.35, 1), 0.9: (1, 1, 1)})
        sc.rot(f"nml_{n}", {0: (0, 0, 0), 0.36: (62, 0, 0), 0.6: (28, 0, 0), 0.9: (0, 0, 0)})
        sc.scl(f"nml_{n}", {0: (1, 1, 1), 0.36: (1, 1.4, 1), 0.9: (1, 1, 1)})
    for e in EYES:
        sc.scl(e, {0: (1, 1, 1), 0.26: (1, 0.15, 1), 0.34: (1.4, 1.55, 1.4), 0.6: (1.1, 1.1, 1.1), 0.9: (1, 1, 1)})
    for n, ch in THR.items():
        for k, b in enumerate(ch):
            sc.rot(b, {0: (0, 0, 0), 0.36 + k * 0.04: (70 - k * 20, 0, 0), 0.62: (20, 0, 0), 0.9: (0, 0, 0)})
    sc.rot("hanger", {0: (0, 0, 0), 0.36: (0, 0, 14), 0.6: (0, 0, -6), 0.9: (0, 0, 0)})
    A.append(sc)

    un = Anim("unravel", UNRAVEL, "hold")
    for e in EYES:
        un.scl(e, {0: (1, 1, 1), 0.25: (1, 0.05, 1)})
    for n in PN:
        s = DIST[n] * 0.04
        un.scl(f"nm_{n}", {0: (1, 1, 1), 0.2 + s: (1, 1.2, 1), 0.7 + s: (1, 0, 1)})
        un.scl(f"nml_{n}", {0: (1, 1, 1), 0.5: (1, 0, 1)})
        un.rot(f"low_{n}", {0: (0, 0, 0), 0.5: (10, 0, 0), 1.2: (-165, 0, 0), 1.8: (-165, 0, 0)})
    for i in range(4):
        a, b = 0.55 + (3 - i) * 0.12, 1.25 + (3 - i) * 0.08
        keys = {0: (0, 0, 0), a: (0, 0, 0), b: (0, ACC[i], 0), 1.8: (0, ACC[i], 0)}
        un.rot(CHR[i], keys)
        un.rot(CHL[i], {k: (0, -v[1], 0) for k, v in keys.items()})
    un.scl("root", {0: 1.0, 1.0: 1.0, 1.35: 0.7, 1.8: 0.0})
    un.pos("root", {0: (0, 0, 0), 1.0: (0, 3, 0), 1.8: (0, -26, 8)})
    un.rot("root", {0: (0, 0, 0), 1.1: (0, 0, 0), 1.8: (0, 200, 0)})
    un.scl("hanger", {0: 1.0, 1.3: 1.25, 1.6: 0.0})
    A.append(un)
    return A


# ---------------------------------------------------------------------------- dream ribbon
STRANDS = [("a", 0, 1, 1.0), ("b", 180, -1, 1.0), ("c", 90, 1, 0.75)]
RSEG = 10


def ribbon_model():
    m = Model("dn_lull_ribbon", density=4.0, bounds=(4, 4, (0, 1.2, 0)))
    mats = {"a": ribbon_mat(PEACH, "#ffc9a0", GOLD, "dl_rib_a"), "b": ribbon_mat("#dcebfa", BLUE, IVORY, "dl_rib_b"),
            "c": ribbon_mat(PINK, "#f3cfdc", "#fff0d0", "dl_rib_c")}
    root = m.bone("root")
    body = m.bone("body", root)
    for s, a0, dr, wk in STRANDS:
        sp = m.bone(f"spin_{s}", body)
        pts = []
        for k in range(RSEG + 1):
            f = k / RSEG
            a = math.radians(a0 + dr * k * 32)
            R = (10.0 + 5.0 * math.sin(math.pi * f)) * (0.9 if s == "c" else 1.0)
            pts.append(np.array((R * math.cos(a), 2.5 + k * 3.3 + (1.5 if s == "c" else 0), R * math.sin(a))))
        for k in range(RSEG):   # each segment spans the chord between two helix points -> a continuous ribbon
            p0, p1 = pts[k], pts[k + 1]
            dv = p1 - p0
            mid = tuple((p0 + p1) / 2)
            yaw = math.degrees(math.atan2(-dv[2], dv[0]))
            tilt = math.degrees(math.atan2(dv[1], math.hypot(dv[0], dv[2])))
            b = m.bone(f"rb_{s}{k + 1}", sp, pivot=mid, rot=(0, yaw, 0))
            b.plane("z", mid, float(np.linalg.norm(dv)) + 0.7, 3.2 * wk, mats[s], variant=k % 3, rot=(0, 0, tilt), pivot=mid)
    hem = m.bone("hem", body)
    ring(hem, (0, 1.4, 0), 14.5, 14, (7.0, 0.3, 2.2), tex.fabric(PEACH, GOLD, 0.06, 3, glow=0.35))
    charm = m.bone("charm", body, pivot=(0, 40, 0))
    charm.plane("z", (0, 40, 0), 4.2, 4.2, tex.shaped(tex.m_star(5, 0.45), "#ffffff", GOLD, glow=1.0, var=0, key="dl_cstar"))
    charm.plane("x", (0, 40, 0), 4.2, 4.2, tex.shaped(tex.m_crescent(0.4), "#fff3cf", PINK, glow=0.9, var=0, key="dl_cmoon"))
    return m


def _segs():
    return [f"rb_{s}{k + 1}" for s, *_ in STRANDS for k in range(RSEG)]


def ribbon_anims():
    A = []
    segs = _segs()
    turn = Anim("turn", loop=True)
    turn.rot("spin_a", (0, spin(55), 0))
    turn.rot("spin_b", (0, spin(-42), 0))
    turn.rot("spin_c", (0, spin(78), 0))
    turn.rot("hem", (0, spin(-18), 0))
    turn.rot("charm", (0, spin(90), 0))
    turn.pos("charm", (0, LIFE(1.2, 2.0), 0))
    A.append(turn)
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    tr = Anim("travel", 1.0, True)   # a tight spinning spindle streaming through the air
    tr.scl("body", (0.3, 0.75, 0.3))
    tr.rot("body", (0, spin(420), 0))
    tr.pos("body", (0, -8, 0))
    for i, b in enumerate(segs):
        tr.rot(b, (S(18, 0.5, i * 0.05, clock="q.life_time"), 0, 0))
    tr.scl("hem", 0.0)
    A.append(tr)
    wr = Anim("wrap", WRAP, "hold")
    wr.scl("body", {0: (0.3, 0.75, 0.3), 0.45: (1.22, 1.08, 1.22), 0.65: (0.95, 1.0, 0.95), 0.8: (1, 1, 1)})
    wr.pos("body", {0: (0, -8, 0), 0.45: (0, 1, 0), 0.8: (0, 0, 0)})
    wr.scl("hem", {0: 0.0, 0.4: 0.0, 0.7: 1.15, 0.8: 1.0})
    for i, b in enumerate(segs):
        wr.rot(b, {0: (40, 0, 0), 0.35 + (i % RSEG) * 0.03: (-14, 0, 0), 0.8: (0, 0, 0)})
    A.append(wr)
    orb = Anim("orbit", 4.0, True)
    for i, b in enumerate(segs):
        k = i % RSEG
        orb.rot(b, (S(6, 2.0, k * 0.06 + i // RSEG * 0.3, clock="q.life_time"), 0, 0))
        orb.pos(b, (0, LIFE(0.6, 2.0, k * 0.06 + i // RSEG * 0.3), 0))
    orb.scl("body", (LIFE(0.04, 4.0, base=1.0), 1, LIFE(0.04, 4.0, base=1.0)))
    A.append(orb)
    rc = Anim("recoil", RECOIL, "hold")   # the scream passes: the cocoon flinches outward, then settles
    rc.scl("body", {0: (1, 1, 1), 0.1: (1.45, 0.9, 1.45), 0.3: (1.12, 1.0, 1.12), 0.6: (1, 1, 1)})
    for i, b in enumerate(segs):
        rc.rot(b, {0: (0, 0, 0), 0.1: (28, 0, 0), 0.35: (-10, 0, 0), 0.6: (0, 0, 0)})
    A.append(rc)
    uw = Anim("unwind", UNWIND, "hold")
    uw.pos("body", {0: (0, 0, 0), 1.0: (0, 30, 0)})
    uw.scl("body", {0: (1, 1, 1), 0.4: (0.6, 1.4, 0.6), 1.0: (0.05, 2.0, 0.05)})
    for i, b in enumerate(segs):
        uw.rot(b, {0: (0, 0, 0), 1.0: (80, 0, 0)})
    uw.scl("hem", {0: 1.0, 0.4: 0.0})
    uw.scl("root", {0: 1.0, 0.8: 1.0, 1.0: 0.0})
    A.append(uw)
    return A


# ---------------------------------------------------------------------------- nightmare waveform ring
NB, WR = 24, 16.0
INV = M("1/math.max(q.property('grimoire:size'),0.3)", lambda t: 1.0)


def wave_model():
    m = Model("dn_lull_wave", density=2.0, bounds=(40, 8, (0, 1.5, 0)))
    root = m.bone("root")
    strokes, haze = wave_strokes(), wave_haze()
    for i in range(NB):
        a = i * 360 / NB
        p = (WR * math.cos(math.radians(a)), 0, WR * math.sin(math.radians(a)))
        b = m.bone(f"bar{i + 1}", root, pivot=p, rot=(0, -(a + 90), 0))
        b.plane("z", (p[0], 18, p[2]), 4.3, 36, strokes, variant=i % 4, density=4)
        h = m.bone(f"haze{i + 1}", b, pivot=p)
        h.plane("z", (p[0], 18, p[2] + 0.3), 4.3, 30, haze, variant=i % 2)
    return m


def bar_h(i, amp):
    w1, p1 = 540 + (i * 37) % 300, (i * 71) % 360
    w2, p2 = 1300 + (i * 53) % 500, (i * 29) % 360
    base = 0.72 + 0.28 * ((i * 7) % 5) / 4
    mol = (f"({base * amp:.3f}+{0.32 * amp:.3f}*math.sin(q.life_time*{w1}+{p1})+{0.18 * amp:.3f}*math.sin(q.life_time*{w2}+{p2}))"
           f"*math.min(q.anim_time*6,1)/math.max(q.property('grimoire:size'),0.3)")
    return M(mol, lambda t: (base * amp + 0.32 * amp * math.sin(math.radians(t * w1 + p1))
                             + 0.18 * amp * math.sin(math.radians(t * w2 + p2))) * min(t * 6, 1))


def wave_anims():
    A = []
    turn = Anim("turn", loop=True)
    turn.rot("root", (0, spin(28), 0))
    A.append(turn)
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    for name, amp in (("scream", 1.0), ("faint", 0.55)):
        a = Anim(name, loop=True)
        for i in range(NB):
            a.scl(f"bar{i + 1}", (1, bar_h(i, amp), 1))
        A.append(a)
    fd = Anim("fade", FADE, "hold")
    for i in range(NB):
        fd.scl(f"bar{i + 1}", {0: (1, INV * 0.8, 1), FADE: (1, 0, 1)})
    A.append(fd)
    return A


# ---------------------------------------------------------------------------- sound design
SR = sy.SR


def hz(semi):
    return 293.66 * 2 ** (semi / 12)


def tine(f, dur=1.5, amp=1.0, wobble=0.0, bright=1.0):
    """Music-box comb tine: sine fundamental, octave and an inharmonic ping, with a tiny click."""
    t = sy.t_axis(dur)
    fr = f * (1 + wobble * np.sin(2 * np.pi * 0.8 * t + f * 0.01))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    s = (np.sin(ph) * np.exp(-t / 0.9) + 0.22 * bright * np.sin(2 * ph + 0.3) * np.exp(-t / 0.35)
         + 0.12 * bright * np.sin(5.43 * ph) * np.exp(-t / 0.06))
    n = int(SR * 0.004)
    s[:n] += sy.noise(n / SR)[:n] * 0.25 * bright * np.linspace(1, 0, n)
    return sy.fade(s * amp, 0.001, 0.05)


def dark_voice(f, dur, vowel="oh", slide=0.0):
    t = sy.t_axis(dur)
    fr = f * (1 + slide * t / dur) * (1 + 0.009 * np.sin(2 * np.pi * 4.1 * t))
    s = sy.osc(fr, wave_="saw") + 0.8 * sy.osc(fr * 1.013, wave_="saw") + 0.3 * sy.osc(fr * 0.5, wave_="saw")
    s = sy.lowpass(sy.formants(s, sy.VOWELS[vowel]), 1700)
    return sy.norm(s * sy.env(dur, 0.25, 0.1, 0.8, 0.4))


def morph_voice(freq, dur, vowels, detune=1.059, breath=0.3):
    """Shrieking voice: two detuned saws + breath through formants that morph vowel to vowel."""
    n = int(SR * dur)
    fr = np.asarray(freq)[:n]
    t = sy.t_axis(dur)
    fr = fr * (1 + (0.004 + 0.03 * t / dur) * np.sin(2 * np.pi * (5 + 4 * t / dur) * t))
    src = sy.osc(fr, wave_="saw") + 0.6 * sy.osc(fr * detune, wave_="saw") + breath * sy.noise(dur)[:n]
    out = np.zeros(n)
    blk = int(SR * 0.03)
    win = np.hanning(blk * 2)
    for i in range(0, n, blk):
        a = max(0, i - blk // 2)
        seg = src[a:a + blk * 2]
        if len(seg) < blk * 2:
            seg = np.pad(seg, (0, blk * 2 - len(seg)))
        x = min(1.0, i / n)
        for (x0, v0), (x1, v1) in zip(vowels, vowels[1:]):
            if x0 <= x <= x1:
                f = (x - x0) / max(1e-6, x1 - x0)
                pk = [(p0[0] + (p1[0] - p0[0]) * f, p0[1] + (p1[1] - p0[1]) * f, p0[2] + (p1[2] - p0[2]) * f)
                      for p0, p1 in zip(sy.VOWELS[v0][:3], sy.VOWELS[v1][:3])]
                break
        else:
            pk = sy.VOWELS[vowels[-1][1]][:3]
        y = sy.formants(seg * win, pk)
        out[a:a + blk * 2] += y[:min(blk * 2, n - a)]
    return sy.norm(out * sy.env(dur, 0.02, 0.1, 0.85, dur * 0.4))


# the motif: (semitones above D, eighth notes); two bars of 6/8 each
PH_A = [(9, 2), (7, 1), (14, 2), (11, 1), (12, 3), (9, 2), (7, 1)]
PH_B = [(4, 2), (7, 1), (11, 2), (9, 1), (2, 2), (4, 1), (0, 3)]
CH_A = [(-7, -3, 0), (-12, -8, -5)]     # G, D
CH_B = [(-8, -5, -1), (-12, -8, -5)]    # F#m, D


def phrase(notes, chords, mode="dream"):
    wob = {"dream": 0.0, "dis": 0.005, "dual": 0.003}[mode]
    parts = []
    t = 0.0
    for semi, n8 in notes:
        f = hz(semi + 12)
        parts.append((t, tine(f, 1.4, 0.9, wob)))
        if mode in ("dis", "dual"):
            parts.append((t + 0.018, tine(f * 2 ** (38 / 1200), 1.4, 0.5, wob * 1.6)))    # detuned doubling
        if mode == "dis":
            parts.append((t + E8 * 0.5, tine(hz(semi + 6), 1.1, 0.32, wob)))              # tritone shadow
        if mode == "dual" and n8 >= 2:                                                    # inverted nightmare line
            parts.append((t, dark_voice(hz(-4 - semi), n8 * E8 + 0.25, "oh" if semi % 2 else "ah") * 0.34))
        t += n8 * E8
    for b, (r, th, fi) in enumerate(chords):
        t0 = b * 6 * E8
        for k, s_ in ((0, r), (2, th), (3, fi), (5, th)):
            parts.append((t0 + k * E8, tine(hz(s_ + 12), 0.9, 0.5 if k == 0 else 0.3, wob, 0.6)))
        vow = "oo"
        parts.append((t0, sy.choir(hz(r), 1.15, vow, voices=4, attack=0.3, release=0.5) * 0.24))
        parts.append((t0, sy.choir(hz(th), 1.15, vow, voices=3, attack=0.35, release=0.5) * 0.16))
        parts.append((t0, sy.choir(hz(fi), 1.15, vow, voices=3, attack=0.35, release=0.5) * 0.14))
        if mode == "dis":
            parts.append((t0 + 0.2, sy.choir(hz(r + 1), 0.95, "oo", voices=3, attack=0.4) * 0.12))   # minor-2nd cluster
        if mode == "dual":
            parts.append((t0, sy.thump(0.4, 88, 38, 0.15) * 0.55))
            parts.append((t0 + 0.24, sy.thump(0.3, 70, 34, 0.1) * 0.35))
            parts.append((t0, sy.pad(hz(r - 6), 1.0, cutoff=500, attack=0.2, release=0.4) * 0.14))  # tritone drone
    if mode == "dual":   # a clock whose ticks drift out of time
        for k in range(12):
            ck = sy.highpass(sy.noise(0.012), 3500) * np.exp(-sy.t_axis(0.012) / 0.003)
            parts.append((k * E8 + 0.011 * k, ck * 0.18))
    sig = sy.at(PHRASE, *parts)
    if mode == "dis":   # reversed tail swelling into the next downbeat
        tail = sy.reverb(sy.at(0.5, (0, tine(hz(notes[0][0] + 12), 0.5)), (0, tine(hz(notes[0][0] + 18), 0.5, 0.6))), 1.2, 1.0)[::-1]
        sig = sy.at(PHRASE, (0, sig), (max(0.0, PHRASE - len(tail) / SR), sy.norm(tail) * 0.35))
    return sy.reverb(sig, 0.9, 0.35 if mode == "dream" else 0.4)


def scream(k=1.0):
    pre = sy.mixdown([sy.bell(1175 * k, 0.32, inharm=1.4), sy.bell(1245 * k, 0.32, inharm=1.3)])[::-1]
    dur = 1.3
    fc = np.concatenate([sy.sweep(330 * k, 660 * k, 0.12), sy.sweep(660 * k, 520 * k, 0.4), sy.sweep(520 * k, 360 * k, 0.8)])
    voice = morph_voice(fc, dur, [(0, "oo"), (0.15, "ah"), (0.45, "ee"), (1.0, "eh")])
    low = morph_voice(fc * 0.5, dur, [(0, "oh"), (0.4, "ah"), (1.0, "oo")], detune=1.0905, breath=0.15)
    cl = sy.mixdown([sy.bell(587 * k, 1.3, inharm=1.35), sy.bell(622 * k, 1.3, inharm=1.3), sy.bell(831 * k, 1.1, inharm=1.45) * 0.6])
    sig = sy.at(1.7, (0, pre, 0.45), (0.3, voice, 0.75), (0.3, low, 0.4), (0.3, cl, 0.55), (0.3, sy.thump(0.5, 72, 30, 0.3), 0.5),
                (0.31, sy.crack(0.35, 4500, 10), 0.25))
    return sy.reverb(sig, 1.2, 0.38)


def build_sounds(pack):
    # unfurl: a music box is wound, then a pentatonic glissando and an 'oo' swell
    clicks = [(i * (0.07 - i * 0.003), sy.crack(0.03, 5200, 2), 0.35) for i in range(11)]
    gl = [(0.6 + i * 0.06, tine(hz(s + 12), 1.2, 0.7)) for i, s in enumerate([0, 2, 4, 7, 9, 12, 14, 16, 19])]
    op = sy.at(2.2, *clicks, *gl, (0.5, sy.choir(hz(0), 1.5, "oo", voices=4, attack=0.6) * 0.35),
               (0.5, sy.choir(hz(7), 1.5, "oo", voices=3, attack=0.7) * 0.25), (0.8, sy.shimmer(1.2, 2400, 14) * 0.25),
               (1.25, tine(hz(26), 1.0, 0.6)))
    sy.save(pack, "dn_lull_open", sy.reverb(op, 1.2, 0.35), max_distance=48)
    sy.save(pack, "dn_lull_lull1", phrase(PH_A, CH_A, "dream"), max_distance=48)
    sy.save(pack, "dn_lull_lull2", phrase(PH_B, CH_B, "dream"), max_distance=48)
    sy.save(pack, "dn_lull_dis1", phrase(PH_A, CH_A, "dis"), max_distance=48)
    sy.save(pack, "dn_lull_dis2", phrase(PH_B, CH_B, "dis"), max_distance=48)
    sy.save(pack, "dn_lull_dual1", phrase(PH_A, CH_A, "dual"), max_distance=56)
    sy.save(pack, "dn_lull_dual2", phrase(PH_B, CH_B, "dual"), max_distance=56)
    # the stave tears: reversed music-box swell, then a fabric rip and a sinking drone
    rev = sy.reverb(sy.at(0.6, *[(i * 0.08, tine(hz(s + 12), 0.5, 0.7)) for i, s in enumerate([14, 12, 9, 7])]), 1.2, 0.9)[::-1]
    rip = sy.bandpass(sy.noise(0.4), 2600, 1.1) * np.exp(-sy.t_axis(0.4) / 0.12)
    drone = sy.norm(sy.lowpass(sy.osc(sy.sweep(hz(-12), hz(-13.5), 1.4), wave_="saw"), 650)) * sy.env(1.4, 0.05, 0.1, 0.8, 0.6)
    sw = sy.at(2.2, (0, sy.norm(rev), 0.5), (0.95, rip, 0.6), (0.95, sy.crack(0.4, 4000, 18), 0.4), (0.95, drone, 0.4),
               (1.0, sy.bell(hz(18), 1.0, inharm=1.4), 0.3))
    sy.save(pack, "dn_lull_tear", sy.reverb(sw, 1.0, 0.3), max_distance=48)
    sy.save(pack, "dn_lull_scream", scream(1.0), variants=[scream(0.93), scream(1.08)], max_distance=64)
    # the first faint wave: a whisper of the scream
    wh = morph_voice(sy.sweep(400, 560, 1.1), 1.1, [(0, "oo"), (0.5, "ee"), (1.0, "ah")], breath=2.5)
    faint = sy.at(1.4, (0, sy.highpass(wh, 900), 0.6), (0.05, sy.bell(hz(20), 1.2, inharm=1.3), 0.35),
                  (0.07, sy.bell(hz(20) * 2 ** (45 / 1200), 1.2, inharm=1.3), 0.25))
    sy.save(pack, "dn_lull_faint", sy.reverb(faint, 1.3, 0.45), volume=0.8, max_distance=48)
    # dream heal: two celesta tones, a breath of 'oo', glitter
    def healc(r):
        s = sy.at(1.2, (0, tine(hz(r + 12), 1.0, 0.9)), (0.11, tine(hz(r + 19), 1.0, 0.7)),
                  (0, sy.choir(hz(r), 1.0, "oo", voices=3, attack=0.15, release=0.6), 0.35), (0.05, sy.shimmer(0.8, 2400, 8), 0.2))
        return sy.reverb(s, 1.0, 0.35)
    sy.save(pack, "dn_lull_heal", healc(2), variants=[healc(4), healc(7)], volume=0.75, max_distance=24)
    rib = sy.at(1.1, (0, sy.lowpass(sy.whoosh(0.8, 900, 4200, 2.0), 5000), 0.45),
                *[(0.1 + i * 0.07, sy.pluck(hz(s + 12), 0.5, 0.7), 0.3) for i, s in enumerate([0, 4, 7, 9, 14])])
    sy.save(pack, "dn_lull_ribbon", sy.reverb(rib, 0.9, 0.3), volume=0.7, max_distance=32)
    sy.save(pack, "dn_lull_ward", sy.reverb(sy.at(0.6, (0, sy.lowpass(sy.thump(0.3, 170, 90, 0.4), 1200), 0.6),
                                                 (0.02, tine(hz(26), 0.5, 0.5))), 0.6, 0.3), volume=0.6, max_distance=20)
    def hitc(k):
        s = sy.at(0.7, (0, sy.crack(0.3, 3600, 9), 0.5), (0, sy.bell(233 * k, 0.7, inharm=1.55), 0.6),
                  (0, sy.bell(247 * k, 0.6, inharm=1.5), 0.4), (0, sy.bandpass(sy.noise(0.2), 900, 2) * np.exp(-sy.t_axis(0.2) / 0.05), 0.3))
        return sy.reverb(s, 0.7, 0.3)
    sy.save(pack, "dn_lull_hit", hitc(1.0), variants=[hitc(0.9), hitc(1.12)], volume=0.8, max_distance=32)
    calm = sy.at(1.0, (0, sy.choir(hz(9), 0.8, "oo", voices=3, attack=0.1, release=0.5), 0.5), (0.0, tine(hz(21), 0.9, 0.6)),
                 (0.12, tine(hz(26), 0.8, 0.4)))
    sy.save(pack, "dn_lull_calm", sy.reverb(calm, 0.9, 0.35), volume=0.6, max_distance=20)
    # unravel: the music box runs down while both halves wind back; a soft lid closes
    parts, t = [], 0.0
    for i, (s, n8) in enumerate(PH_B):
        r = 1 - 0.045 * i
        parts.append((t, tine(hz(s + 12) * r, 1.0, 0.8, 0.004 * i)))
        t += n8 * E8 * (1 + 0.16 * i) * 0.7
    parts += [(0, sy.whoosh(1.4, 3000, 500)[::-1], 0.3), (0, dark_voice(hz(-16), 1.6, "oo", slide=-0.15), 0.25),
              (t + 0.15, sy.thump(0.25, 220, 120, 0.6), 0.4), (t + 0.15, sy.crack(0.05, 3000, 2), 0.3)]
    sy.save(pack, "dn_lull_unravel", sy.reverb(sy.at(2.4, *parts), 1.0, 0.35), max_distance=48)


# ---------------------------------------------------------------------------- build
def build(pack):
    fx = particles(pack)
    fx.effect("dn_lull_note", "note", count=5, life=(1.2, 2.0), size=(0.16, 0.1), shape=("sphere", 1.8), speed=(0.2, 0.6),
              accel=(0, 0.6, 0), drag=0.8, colors=["#fff6dcff", "#e9cf8aee", "#e8b4c800"])
    fx.effect("dn_lull_mote", "dot", count=6, life=(1.0, 1.8), size=(0.08, 0.0), shape=("sphere", 1.0), speed=(0.05, 0.3),
              accel=(0, 0.4, 0), colors=["#ffe6cfff", "#e8b4c8aa", "#bcd6f000"])
    fx.effect("dn_lull_heal", None, sprites=["star", "petal", "dot"], count=10, life=(0.9, 1.5), size=(0.14, 0.04),
              shape=("disc", 0.9), direction=(0, 1, 0), speed=(0.6, 1.4), drag=1.0,
              colors=["#fff3e0ff", "#ffd9b8ff", "#e8b4c800"], spin=(360, 60))
    fx.effect("dn_lull_ward", "ringthin", count=1, life=(0.4, 0.5), size=(0.4, 1.4), facing="emitter_transform_xz",
              colors=["#fff1dcff", "#e9cf8acc", "#e8b4c800"])
    fx.effect("dn_lull_thread", None, sprites=["slash", "beam"], count=4, life=(1.0, 1.8), size=(0.06, 0.03), size_y=(0.45, 0.2),
              shape=("box", (2.2, 0.6, 0.2)), speed=(0.1, 0.4), accel=(0, -0.8, 0), drag=1.2,
              colors=["#6a4a6eff", "#2a2d52cc", "#2a2d5200"], blend="blend", spin=(30, 40))
    fx.effect("dn_lull_front", None, sprites=["wave", "shard"], count=2, life=(0.35, 0.6), size=(0.35, 0.1), shape=("sphere", 0.4),
              speed=(0.2, 0.8), accel=(0, 0.6, 0), colors=["#cfc6b0ff", "#6a4a6eee", "#6e2f3a00"], spin=(360, 0))
    fx.effect("dn_lull_scream_ring", "ringthin", count=1, life=(0.75, 0.8), size=(1.0, 10.5), facing="emitter_transform_xz",
              colors=["#cfc6b0ff", "#6a4a6ecc", "#2a2d5200"])
    fx.effect("dn_lull_eye", "eye", count=3, life=(0.5, 0.9), size=(0.22, 0.3), shape=("sphere", 0.5), speed=(0.3, 0.8),
              accel=(0, 0.8, 0), colors=["#cfc6b0ff", "#6e2f3aee", "#2a2d5200"])
    fx.effect("dn_lull_calm", None, sprites=["petal", "note", "star"], count=8, life=(0.8, 1.4), size=(0.14, 0.04),
              shape=("sphere", 0.8), speed=(0.3, 0.9), accel=(0, 0.5, 0), drag=1.0,
              colors=["#fff6dcff", "#bcd6f0ee", "#ffd9b800"], spin=(360, 90))
    fx.effect("dn_lull_unravel", None, sprites=["wave", "petal", "slash"], count=12, life=(0.8, 1.4), size=(0.18, 0.03),
              shape=("sphere", 2.0, "surface"), direction="inwards", speed=(1.5, 2.5), drag=0.8,
              colors=["#ffd9b8ff", "#6a4a6ecc", "#2a2d5200"], spin=(360, 120))

    tm, ta = tapestry_model(), tapestry_anims()
    pack.actor("dn_lull_tapestry", tm, ta, TAP_STATES, always=["breathe"], scale=1.25, lifetime=60,
               display="Lullaby Tapestry", blend=0.15)
    rm, ra = ribbon_model(), ribbon_anims()
    pack.actor("dn_lull_ribbon", rm, ra, RIB_STATES, always=["turn"], lifetime=60, display="Dream Ribbon", blend=0.12)
    wm, wa = wave_model(), wave_anims()
    pack.actor("dn_lull_wave", wm, wa, WAVE_STATES, always=["turn"], size_prop=True, lifetime=30,
               display="Nightmare Waveform", blend=0.0)
    build_sounds(pack)

    by = {a.name: a for a in ta}
    br = (by["breathe"], 0.35)
    pack.preview("dn_lull_tap_a", tm, [[(by["unfurl"], 0.8), br], [(by["lullaby"], 0.6), br], [(by["unravel"], 1.3), br]],
                 views=((0, 8), (35, 15), (90, 5)))
    pack.preview("dn_lull_tap_b", tm, [[(by["dissonance"], 0.8), br], [(by["dual"], 1.1), br], [(by["scream"], 0.36), br]],
                 views=((0, 8), (35, 15), (160, 10)), skin="torn")
    rb = {a.name: a for a in ra}
    pack.preview("dn_lull_ribbon", rm, [[(rb["orbit"], 0.5), (rb["turn"], 0.5)], [(rb["travel"], 0.3), (rb["turn"], 0.3)],
                                        [(rb["recoil"], 0.1), (rb["turn"], 0.5)]], views=((20, 15), (0, 70)))
    wb = {a.name: a for a in wa}
    pack.preview("dn_lull_wave", wm, [(wb["scream"], 0.4), (wb["faint"], 0.7)], views=((20, 20), (0, 60)))
    for nm_, mm in (("tapestry", tm), ("ribbon", rm), ("wave", wm)):
        print(f"    dn_lull_{nm_}: {mm.cube_count()} cubes, {len(mm.order)} bones, tex {mm.tex_size}")
