"""DN06 hero: THE DREAMER -- a colossal faceless porcelain sleeper with a house inside it.

Original design: an elongated porcelain mannequin whose anatomy is dream architecture.
  * chest = a doll's-house cabinet (two doors with arched lights) holding three lit miniature
    bedrooms (beds, lamps, moonlit windows, an inner staircase); the rooms are bones so they can
    be fired out as expanding room-cubes;
  * ribs are staircases climbing the flanks, a stair-ladder runs up its back;
  * forearms are two telescoping arcades you can see through (inner spiral steps, a lamp, a
    newel core that slides out when the arm extends impossibly far);
  * dormer windows slide along the rooftop shoulders, tiny doors sit on the elbows and knees;
  * the faceless oval head carries one small panelled DOOR; behind it a shadow-box holds a
    glowing night sea with a paper moon and a paper boat (the "other world" that pours out as a
    beam in the finale);
  * porcelain plates are separate shard bones: they lift away to reveal indigo corridors full
    of window-eyes and tooth-like stair edges (nightmare beneath), and fly off when it breaks;
  * its blanket clings to it as a flowing gown.
Voice: breath, humming and creaking ceramic (see dn_dreamer_sfx).
This module also owns the Dream & Nightmare palette and painters shared by the other
dn_dreamer_* modules.
"""
import math

import numpy as np

from kit import tex
from kit.anim import LIFE, Anim, M, S
from kit.geo import Mat, Model, ring

# ---------------------------------------------------------------- palette
IVORY, PEACH, PINK, SGOLD, PBLUE = "#f6efe2", "#ffd9b8", "#e8b4c8", "#e9cf8a", "#bcd6f0"
INDIGO, MAUVE, BURG, AGED, CGRAY = "#2a2d52", "#6a4a6e", "#6e2f3a", "#cfc6b0", "#8b8f9a"
SCALE = 2.2                       # rendered scale of the Dreamer (1 unit = SCALE/16 blocks)
BPU = SCALE / 16.0


# ---------------------------------------------------------------- shared painters
def _px(ctx):
    return tex.px(ctx)


def gilt(glow=0.15, key=""):
    return tex.metal(SGOLD, "#fff3cf", "#9a7b3a", bands=2.0, glow=glow)


def crackled(base=AGED, shade="#b3a88f", c1="#9a3a50", c2=INDIGO, glow=0.8, gilt_c="#a88f55", scale=7.0):
    """Nightmare skin of the porcelain: aged glaze split by glowing burgundy fissures."""
    kb, ks, k1, k2, kg = (tex.rgb(c) for c in (base, shade, c1, c2, gilt_c))

    def fn(ctx):
        ix, iy = _px(ctx)
        t = tex.tile(ctx, base)
        t[..., :3] = tex.mix(kb, ks, np.clip((ctx.V - 0.3) * 0.9, 0, 1)[..., None])
        s = ctx.variant * 17.0
        c = np.abs(tex.vnoise(ix / scale + s, iy / scale, 81) - tex.vnoise(ix / scale + 19.0, iy / scale + s, 82))
        core = c < 0.022
        halo = (c >= 0.022) & (c < 0.05)
        t[..., :3] = np.where(halo[..., None], tex.mix(t[..., :3], k2, 0.35), t[..., :3])
        t[..., :3] = np.where(core[..., None], k1, t[..., :3])
        t[..., 4] = np.where(core, glow, 0.0)
        if min(ctx.w, ctx.h) >= 6:
            d = np.minimum(np.minimum(ix, ctx.w - 1 - ix), np.minimum(iy, ctx.h - 1 - iy))
            t[..., :3] = np.where((d == 0)[..., None], kg, t[..., :3])
        return tex.grain(ctx, t, 0.03)
    return Mat(fn, f"dnd_crk{base}{shade}{c1}{c2}{glow}{scale}")


def porc(base=IVORY, shade="#e2d6c2", crack=0.35, gilt_c=None, glow=0.0):
    """Dream porcelain with gilt hairline seams; nightmare skin = crackled."""
    return tex.alt(tex.porcelain(base, shade, "#c4b59c", crack=crack, gilt=gilt_c, glow=glow), nightmare=crackled())


def eyewall(key="dnd_eyes", glow=0.9):
    """Indigo corridors packed with too many lit window-eyes and tooth-like stair edges."""
    ki, km, ks, kp, kt = (tex.rgb(c) for c in (INDIGO, MAUVE, "#f3e3b0", "#1a1026", AGED))

    def fn(ctx):
        ix, iy = _px(ctx)
        t = tex.tile(ctx, INDIGO)
        depth = np.abs(ctx.U - 0.5) * 2
        t[..., :3] = tex.mix(ki * 0.55, ki, depth[..., None])
        cx, cy = ix % 5, iy % 6
        t[..., :3] = np.where((cx == 0)[..., None], km, t[..., :3])
        h = tex._hash(ix // 5, iy // 6, 7 + ctx.variant)
        eye = (h > 0.22) & (((cy == 2) & (cx >= 1) & (cx <= 3)) | ((cy == 3) & (cx == 2)))
        pupil = eye & (cy == 2) & (cx == 2)
        t[..., :3] = np.where(eye[..., None], ks, t[..., :3])
        t[..., :3] = np.where(pupil[..., None], kp, t[..., :3])
        t[..., 4] = np.where(eye & ~pupil, glow, 0.0)
        teeth = (cy == 5) & (cx % 2 == 1) & (h < 0.6)
        t[..., :3] = np.where(teeth[..., None], kt, t[..., :3])
        return t
    return Mat(fn, f"{key}{glow}")


def wallpaper(c0, c1, dots="#fff6e6", key=None, glow=0.12):
    k0, k1, kd = tex.rgb(c0), tex.rgb(c1), tex.rgb(dots)

    def fn(ctx):
        ix, iy = _px(ctx)
        t = tex.tile(ctx, c0, 1, glow)
        t[..., :3] = np.where(((ix // 2) % 2 == 1)[..., None], k1, k0)
        d = ((ix % 4) == 1) & ((iy % 4) == 1)
        t[..., :3] = np.where(d[..., None], kd, t[..., :3])
        return tex.grain(ctx, t, 0.03)
    return Mat(fn, key or f"dnd_wp{c0}{c1}{dots}{glow}")


def door_mat(base=IVORY, line=SGOLD, glass=None, knob=True, key=None, glow=0.0, alt_night=True):
    """Panelled door: border, two raised panels (the upper one an arched light when glass)."""
    kb, kl = tex.rgb(base), tex.rgb(line)
    kg = tex.rgb(glass) if glass else None

    def fn(ctx):
        u, v = ctx.U, ctx.V
        t = tex.tile(ctx, base, 1, glow)
        t[..., :3] = tex.mix(kb, kb * 0.86, np.clip(v - 0.2, 0, 1)[..., None])
        def rect(u0, u1, v0, v1):
            return (u >= u0) & (u <= u1) & (v >= v0) & (v <= v1)
        pu = rect(0.2, 0.8, 0.1, 0.46)
        pl = rect(0.2, 0.8, 0.54, 0.9)
        pw = 1.0 / max(ctx.w, 1)
        ph = 1.0 / max(ctx.h, 1)
        for p, (u0, u1, v0, v1) in ((pu, (0.2, 0.8, 0.1, 0.46)), (pl, (0.2, 0.8, 0.54, 0.9))):
            rim = p & ~rect(u0 + pw * 1.01, u1 - pw * 1.01, v0 + ph * 1.01, v1 - ph * 1.01)
            t[..., :3] = np.where(rim[..., None], kl, t[..., :3])
        if kg is not None:
            arch = rect(0.3, 0.7, 0.2, 0.44) | (np.hypot((u - 0.5) / 0.2, (v - 0.2) / 0.1) < 1)
            t[..., :3] = np.where(arch[..., None], kg, t[..., :3])
            t[..., 4] = np.where(arch, 0.9, t[..., 4])
        if knob and ctx.w >= 4:
            ix, iy = _px(ctx)
            kn = (ix == int(ctx.w * 0.84)) & (iy == int(ctx.h * 0.52))
            t[..., :3] = np.where(kn[..., None], kl, t[..., :3])
        return tex.grain(ctx, t, 0.02)
    m = Mat(fn, key or f"dnd_door{base}{line}{glass}{knob}{glow}", directional=True)
    if alt_night:
        return tex.alt(m, nightmare=door_mat(AGED, "#8e3446", "#f3e3b0" if glass else None, knob, (key or "dd") + "n",
                                            glow, alt_night=False))
    return m


def sky_mat(key="dnd_sky"):
    """Night sea sky: deep blue zenith to peach horizon, scattered stars; fully self-lit."""
    top, mid, hor = tex.rgb("#18204a"), tex.rgb("#5868a8"), tex.rgb(PEACH)

    def fn(ctx):
        ix, iy = _px(ctx)
        v = ctx.V
        c = np.where((v < 0.6)[..., None], tex.mix(top, mid, (v / 0.6)[..., None]),
                     tex.mix(mid, hor, ((v - 0.6) / 0.4)[..., None]))
        t = tex.tile(ctx, "#000000", 1, 0.85)
        t[..., :3] = c
        st = (tex._hash(ix, iy, 99 + ctx.variant) > 0.93) & (v < 0.6)
        t[..., :3] = np.where(st[..., None], tex.rgb("#fff6dc"), t[..., :3])
        t[..., 4] = np.where(st, 1.0, 0.85)
        return t
    return Mat(fn, key, directional=True)


def starwall(key="dnd_starwall"):
    def fn(ctx):
        ix, iy = _px(ctx)
        t = tex.tile(ctx, "#1d2350", 1, 0.6)
        st = tex._hash(ix, iy, 31 + ctx.variant) > 0.88
        t[..., :3] = np.where(st[..., None], tex.rgb("#ffe9b8"), t[..., :3])
        t[..., 4] = np.where(st, 1.0, 0.55)
        return t
    return Mat(fn, key)


def m_wave(amp=0.25, freq=2.5, level=0.1, phase=0.0):
    return lambda u, v: (v < level + amp * np.sin((u + phase) * math.pi * freq)).astype(float)


def m_arch(half=0.62, spring=0.3):
    """Frame around an arched opening (opening = transparent), for arcades and gates."""
    def fn(u, v):
        opening = (np.abs(u) < half) & ((v < spring) | ((u / half) ** 2 + ((v - spring) / (0.92 - spring)) ** 2 < 1))
        return (~opening).astype(float)
    return fn


def arch_mat(color=IVORY, color2="#eadfcc", outline=SGOLD, key="dnd_arch", glow=0.0):
    return tex.shaped(m_arch(), color, color2, glow=glow, outline=outline, key=key + color + str(glow), var=0.02)


def quilt(base=PBLUE, line="#e9f2fb", stitch=SGOLD, moon=True, fringe=False, key=None, glow=0.06):
    """Blanket: diamond quilting, gold stitching, embroidered little moons, optional fringe."""
    kb, kl, ks = tex.rgb(base), tex.rgb(line), tex.rgb(stitch)

    def fn(ctx):
        ix, iy = _px(ctx)
        t = tex.tile(ctx, base, 1, glow)
        q = ((ix + iy) % 6 == 0) | ((ix - iy) % 6 == 0)
        t[..., :3] = np.where(q[..., None], kl, kb)
        st = q & ((ix % 2) == 0)
        t[..., :3] = np.where(st[..., None], ks, t[..., :3])
        if moon:
            mc = ((ix % 12) - 6) ** 2 + ((iy % 12) - 3) ** 2
            mo = (mc <= 2) & ((((ix % 12) - 7) ** 2 + ((iy % 12) - 3) ** 2) > 1) & (((ix // 12) + (iy // 12)) % 2 == 0)
            t[..., :3] = np.where(mo[..., None], ks, t[..., :3])
        fold = np.sin(ctx.U * math.pi * 2 + ctx.variant) * 0.05
        t[..., :3] = np.clip(t[..., :3] * (1 + fold[..., None]), 0, 1)
        if fringe:
            cut = (iy >= ctx.h - 2) & (ix % 2 == 0)
            t[..., 3] = np.where(cut, 0.0, 1.0)
            band = (iy >= ctx.h - 4) & (iy < ctx.h - 2)
            t[..., :3] = np.where(band[..., None], ks, t[..., :3])
        return tex.grain(ctx, t, 0.025)
    return Mat(fn, key or f"dnd_quilt{base}{line}{stitch}{moon}{fringe}{glow}")


def lamp_mat(c=PEACH):
    return tex.glow_flat(c, 1.0, core="#fffbe8")


def window_mat(glass="#ffe7b0", frame=SGOLD, wall=IVORY, arch=True, glow=0.9):
    return tex.windowed(wall, frame, glass, glow=glow, cols=1, rows=1, arch=arch)


def spin(rate):
    return M(f"q.life_time*{rate}", lambda t: t * rate)


# ---------------------------------------------------------------- pose helpers
def mirror(v):
    return (v[0], -v[1], -v[2])


def expand(d, kind):
    """{pattern: value} -> {bone: value}; '{s}' patterns expand to r (as given) and l (mirrored)."""
    out = {}
    for k, v in d.items():
        if "{s}" in k:
            out[k.format(s="r")] = v
            if kind == "rot":
                out[k.format(s="l")] = tuple(-c if i else c for i, c in enumerate(v)) if not isinstance(v, (int, float)) else v
            elif kind == "pos":
                out[k.format(s="l")] = (-v[0], v[1], v[2])
            else:
                out[k.format(s="l")] = v
    for k, v in d.items():
        if "{s}" not in k:
            out[k] = v
    return out


def P(base=None, rot=None, pos=None, scl=None):
    """Pose = dict(rot, pos, scl) of bone -> value; later dicts override earlier ones."""
    b = base or {"rot": {}, "pos": {}, "scl": {}}
    return {"rot": {**b["rot"], **expand(rot or {}, "rot")}, "pos": {**b["pos"], **expand(pos or {}, "pos")},
            "scl": {**b["scl"], **expand(scl or {}, "scl")}}


def keyed(anim, keys, smooth=True, skip=()):
    """Write {t: pose} keyframes for every bone mentioned in any pose (defaults fill the gaps)."""
    ts = sorted(keys)
    for ch, dflt in (("rot", (0, 0, 0)), ("pos", (0, 0, 0)), ("scl", (1, 1, 1))):
        bones = set()
        for t in ts:
            bones |= set(keys[t][ch])
        for b in sorted(bones):
            if b in skip:
                continue
            vals = {}
            for t in ts:
                v = keys[t][ch].get(b, dflt)
                if ch == "scl" and isinstance(v, (int, float)):
                    v = (v, v, v)
                vals[t] = v
            if len(set(vals.values())) == 1:
                getattr(anim, ch)(b, next(iter(vals.values())))
            else:
                getattr(anim, ch)(b, vals, smooth=smooth)
    return anim


# ---------------------------------------------------------------- model
SHARDS = {}   # name -> (normal, tilt-per-unit (rx, ry, rz))


def _shard(m, name, parent, center, dims, normal, tilt, mat, patch, teeth=3):
    """Porcelain plate (own bone) over a nightmare patch with tooth-like stair edges."""
    n = np.array(normal, dtype=float)
    c = np.array(center, dtype=float)
    ax = int(np.argmax(np.abs(n)))
    size = list(dims)
    size[ax] = 1.0
    pc = c + n * 1.7
    hinge = pc.copy()
    hinge[1] += dims[1] / 2 if ax != 1 else 0
    b = m.bone(name, parent, pivot=tuple(hinge))
    b.box(tuple(pc), tuple(size), mat)
    psize = [max(0.0, d - 1.0) for d in dims]
    psize[ax] = 0.0
    m[parent if isinstance(parent, str) else parent.name].box(tuple(c + n * 0.08), tuple(psize), patch)
    if teeth:
        tsz = [1.0, 1.0, 1.0]
        tsz[ax] = 1.0
        for k in range(teeth):
            f = (k + 0.5) / teeth - 0.5
            p = c + n * 0.6
            off = [0, 0, 0]
            other = [i for i in range(3) if i != ax and i != 1]
            if ax == 1:
                other = [0]
            off[other[0]] = f * dims[other[0]] * 0.8
            off[1] = -dims[1] / 2 + 0.6 if ax != 1 else 0
            m[parent if isinstance(parent, str) else parent.name].box(tuple(p + np.array(off)), tuple(tsz),
                                                                      tex.flat(AGED, jitter=0.04), )
    SHARDS[name] = (tuple(n), tilt)
    return b


def _arcade(m, bone, cx, y0, y1, w, colm, archm, band, inner=None, core=False):
    """See-through arcade section of a forearm between y0 (bottom) and y1 (top)."""
    h = y1 - y0
    k = w / 2 - 1
    for sx in (-1, 1):
        for sz in (-1, 1):
            bone.box((cx + sx * k, y0 + h / 2, sz * k), (2, h, 2), colm, variant=(sx + sz) % 2)
    bone.box((cx, y1 - 1, 0), (w + 1, 2, w + 1), band)
    for i, (ax, off) in enumerate((("z", -w / 2), ("z", w / 2), ("x", -w / 2), ("x", w / 2))):
        if ax == "z":
            bone.plane("z", (cx, y0 + (h - 2) / 2, off), w - 1, h - 2, archm)
        else:
            bone.plane("x", (cx + off, y0 + (h - 2) / 2, 0), w - 1, h - 2, archm)
    if inner == "stairs":   # spiral steps around the newel and a little lamp
        st = tex.wood(IVORY, "#d8c8a8", plank=3)
        for j in range(4):
            a = j * 90 + 45
            px = cx + math.cos(math.radians(a)) * 2.6
            pz = math.sin(math.radians(a)) * 2.6
            bone.box((px, y0 + 3 + j * (h - 6) / 4, pz), (3, 1, 3), st, variant=j % 2)
        bone.box((cx, y1 - 4, 0), (2, 2, 2), lamp_mat())
    if core:
        bone.box((cx, y1 + h / 2, 0), (4, h, 4), porc(), variant=3)


def build_model():
    SHARDS.clear()
    m = Model("dreamer", density=1.5, bounds=(64, 48, (0, 6, 0)), alts=("nightmare",))
    P0 = porc()
    P1 = porc(base="#f3eadb", shade="#ddd0bb")
    PT = tex.alt(tex.trimmed(tex.porcelain(IVORY, "#e2d6c2", "#c4b59c", crack=0.15), SGOLD, 1, 1, glow=0.25),
                 nightmare=crackled(glow=0.85))
    G = gilt()
    G2 = gilt(glow=0.4)
    EYES = eyewall()
    shard_m = tex.alt(tex.trimmed(tex.porcelain("#fbf6ec", "#e6dccb", "#c4b59c", crack=0.1), SGOLD, 1, 0, glow=0.35),
                      nightmare=crackled(base="#ddd3bd", glow=0.9))
    drape_m = tex.alt(quilt(PBLUE, "#e9f2fb", SGOLD, fringe=False, key="drape_a"),
                      nightmare=quilt(MAUVE, "#8a6a8e", "#a88f55", fringe=False, key="drape_an", glow=0.02))
    drape_e = tex.alt(quilt(PBLUE, "#e9f2fb", SGOLD, fringe=True, key="drape_e"),
                      nightmare=quilt(MAUVE, "#8a6a8e", "#a88f55", fringe=True, key="drape_en", glow=0.02))
    arch_a = tex.alt(arch_mat(), nightmare=arch_mat(AGED, "#bdb39b", "#8e3446", key="dnd_archn", glow=0.2))
    win = window_mat()

    root = m.bone("root")
    body = m.bone("body", root)

    # ---- pelvis + gown (the blanket clinging to it)
    pelvis = m.bone("pelvis", body)
    pelvis.box((0, 2, 0), (30, 14, 18), P0)
    pelvis.box((0, 8.5, 0), (31, 1.6, 19), G)
    pelvis.box((0, -5.5, 0), (24, 3, 15), P1, variant=1)
    drapes = []
    for i, (x0, z0, ax, w) in enumerate([(-8, -10.6, "z", 16), (8, -10.6, "z", 16), (-16.2, 0, "x", 19),
                                         (16.2, 0, "x", 19), (-8, 10.6, "z", 16), (8, 10.6, "z", 16)]):
        par = pelvis
        chain = []
        for s in range(3):
            y1 = 6 - s * 29
            b = m.bone(f"drape{i + 1}_{s + 1}", par, pivot=(x0, y1, z0))
            b.plane(ax, (x0, y1 - 15, z0), w, 30, drape_e if s == 2 else drape_m, variant=(i + s) % 3)
            par = b
            chain.append(b.name)
        drapes.append((chain, ax))

    # ---- legs (children of body so they can be revealed first)
    for s, sx in (("r", 1), ("l", -1)):
        th = m.bone(f"thigh_{s}", body, pivot=(sx * 9, -2, 0))
        th.box((sx * 9, -24, 0), (12, 42, 12), P0, variant=2)
        th.box((sx * 9, -46, 0), (12.6, 6, 12.6), PT)
        th.plane("z", (sx * 9, -46, -6.4), 4, 5, door_mat(PEACH, SGOLD, key="kneedoor"))      # little door at the knee
        sh = m.bone(f"shin_{s}", th, pivot=(sx * 9, -46, 0))
        sh.box((sx * 9, -68, 0), (10, 42, 10), P1, variant=3)
        sh.box((sx * 9, -88.5, 0), (10.6, 2, 10.6), G)
        ft = m.bone(f"foot_{s}", sh, pivot=(sx * 9, -89, 0))
        ft.box((sx * 9, -93, -2), (8, 7, 12), P0, variant=4)
        ft.box((sx * 9, -95, -10), (6, 4, 6), P1, variant=4)
    _shard(m, "shard_thigh_r", "thigh_r", (9, -26, -6), (8, 18, 0), (0, 0, -1), (-25, 0, 8), shard_m, EYES)
    _shard(m, "shard_thigh_l", "thigh_l", (-9, -22, -6), (8, 16, 0), (0, 0, -1), (-25, 0, -8), shard_m, EYES)
    _shard(m, "shard_pelvis", pelvis, (0, 1, -9), (16, 9, 0), (0, 0, -1), (-30, 0, 0), shard_m, EYES)

    # ---- spine with staircase ribs
    st_m = tex.alt(tex.wood("#fbf3e4", "#dccdb0", plank=2), nightmare=tex.flat(AGED, jitter=0.05))
    sp1 = m.bone("spine1", pelvis, pivot=(0, 9, 0))
    sp1.box((0, 16, 0), (22, 14, 15), P0, variant=5)
    sp1.plane("z", (0, 15.5, -7.6), 5, 8, win)                                        # navel window
    sp1.box((0, 22.2, 0), (23, 1.2, 16), G)
    sp2 = m.bone("spine2", sp1, pivot=(0, 23, 0))
    sp2.box((0, 30, 0), (25, 14, 16), P0, variant=6)
    sp3 = m.bone("spine3", sp2, pivot=(0, 37, 0))
    sp3.box((0, 43.5, 0), (29, 13, 18), P0, variant=7)
    for s, sx in (("r", 1), ("l", -1)):
        for j in range(6):   # ribs = staircases climbing the flanks, back to front
            y = 24.5 + j * 2.2
            z = 6 - j * 2.4
            sp2.box((sx * (12.5 + 1.0), y, z), (2.4, 1.4, 2.6), st_m, variant=j % 2)
        for j in range(5):
            y = 38 + j * 2.4
            z = 7 - j * 3.2
            sp3.box((sx * (14.5 + 1.0), y, z), (2.4, 1.4, 3.0), st_m, variant=j % 2)
    _shard(m, "shard_belly", sp2, (0, 30, -8), (14, 10, 0), (0, 0, -1), (-30, 0, 0), shard_m, EYES)
    _shard(m, "shard_back", sp3, (0, 43, 9), (18, 10, 0), (0, 0, 1), (30, 0, 0), shard_m, EYES)

    # ---- chest: the doll's-house cabinet
    ch = m.bone("chest", sp3, pivot=(0, 50, 0))
    ch.cube((-23, 50, 0), (46, 32, 13), P0, variant=8)
    ch.cube((-23, 50, -13), (2, 32, 13), PT)
    ch.cube((21, 50, -13), (2, 32, 13), PT)
    ch.cube((-23, 80, -13), (46, 2, 13), PT)
    ch.cube((-23, 50, -13), (46, 2, 13), PT)
    ch.cube((-21, 65, -13), (42, 2, 13), G)
    ch.cube((-1, 67, -13), (2, 13, 13), PT)
    for j in range(7):      # stair-ladder up its back
        ch.box((0, 52 + j * 4.3, 14), (9, 1.6, 2.4), st_m, variant=j % 2)
    ch.box((-5.2, 66, 14), (1, 32, 1), G)
    ch.box((5.2, 66, 14), (1, 32, 1), G)
    rooms = [("room_1", -11, 73.5, 20, 13, (PINK, "#f4cfdc")), ("room_2", 11, 73.5, 20, 13, (PBLUE, "#d9e8f7")),
             ("room_3", 0, 58.5, 42, 13, (PEACH, "#ffe7d1"))]
    rug = tex.fabric("#c98aa4", "#e9cf8a", stripe_w=2, glow=0.1)
    bedm = tex.fabric("#fff6ea", None, glow=0.15)
    blanket = tex.fabric("#e8b4c8", "#f6d9e4", stripe_w=1, glow=0.15)
    for i, (rn, cx, cy, w, h, (c0, c1)) in enumerate(rooms):
        rb = m.bone(rn, ch, pivot=(cx, cy - h / 2, -6))
        rb.plane("z", (cx, cy, -0.3), w, h, wallpaper(c0, c1, glow=0.3))
        rb.plane("y", (cx, cy - h / 2 + 0.2, -6.5), w - 1, 12, rug, faces=("up",))
        rb.plane("z", (cx + (4 if i != 2 else 12), cy + 1.5, -0.6), 5, 6, win)
        if i < 2:
            bx = cx - 4
            rb.box((bx, cy - h / 2 + 1.5, -5), (9, 2.5, 6), bedm)
            rb.box((bx - 0.5, cy - h / 2 + 2.9, -5.2), (7, 0.6, 6.2), blanket)
            rb.box((bx + 3.4, cy - h / 2 + 3.2, -5), (1.6, 1, 4), bedm)
            rb.box((bx + 5, cy - h / 2 + 3.5, -4), (1, 5, 6), tex.wood("#c9a27a", "#8a6a48"))
            rb.box((cx + 6.5, cy - h / 2 + 3, -8), (0.8, 5, 0.8), G)
            rb.box((cx + 6.5, cy - h / 2 + 6.2, -8), (3, 2, 3), lamp_mat())
        else:   # the stair room: an inner staircase and a lit door on the side wall
            for j in range(6):
                rb.box((cx - 14 + j * 3, cy - h / 2 + 1 + j * 1.8, -5), (3, 1.2 + j * 1.8, 7), st_m, variant=j % 2)
            rb.plane("x", (cx - 19.8, cy - 1.5, -5), 5, 8, door_mat(PEACH, SGOLD, glass="#fff0c8", key="roomdoor"))
            rb.box((cx + 4, cy + 4.5, -6), (3, 2, 3), lamp_mat("#ffe2c4"))
            rb.box((cx + 4, cy + 6, -6), (0.6, 2, 0.6), G)
    ch.locator("chest_c", (0, 66, -16))
    for s, sx in (("r", 1), ("l", -1)):   # cabinet doors with arched lights (you can see the rooms)
        d = m.bone(f"cdoor_{s}", ch, pivot=(sx * 23, 66, -13))
        x0 = 0.15 if sx > 0 else -23
        d.cube((x0, 51, -14.6), (22.85, 30, 1.6), door_mat(IVORY, SGOLD, glass=None, key="cabdoor"),
               mats={"north": cabinet_door_face(), "south": cabinet_door_face()})
        d.box((sx * 3.2, 66, -15.2), (1.4, 1.4, 1.2), G2)
    yoke = tex.alt(tex.plates("#f3ebdd", "#d8c8a6", cell=(6, 4), glow_line=0.0), nightmare=crackled())
    ch.box((0, 85, 0), (54, 6, 24), P0, variant=9)
    ch.box((0, 88.6, 0), (44, 1.4, 18), yoke)                      # rooftop slates of the shoulders
    ch.box((0, 82.4, -12.3), (48, 1.4, 0.8), G)
    for s, sx in (("r", 1), ("l", -1)):
        for k, z in enumerate((-5, 5)):
            wb = m.bone(f"win_{s}{k + 1}", ch, pivot=(sx * 15, 88, z))
            wb.box((sx * 15, 91.5, z), (5, 6, 5), win, variant=k)
            wb.box((sx * 15, 95, z), (6.2, 1.2, 6.2), G)
            wb.box((sx * 15, 96.2, z), (3, 1.4, 3), G2)
    for k, w in enumerate((18, 12, 6)):          # dollhouse gable over the cabinet doors
        ch.box((0, 88.5 + k * 1.6, -11.6 + k * 0.2), (w, 1.6, 2), PT if k == 0 else P0, variant=k)
    ch.box((0, 90.3, -12.7), (3, 2.4, 0.4), window_mat(arch=False), faces=("north",))
    capes = []
    for i, (x0, w) in enumerate(((-15, 17), (0, 17), (15, 17))):   # its blanket, worn as a cape
        par = ch
        chain = []
        for k in range(4):
            y1 = 87 - k * 26
            cb_ = m.bone(f"cape{i + 1}_{k + 1}", par, pivot=(x0, y1, 16.5 + k * 0.1))
            cb_.plane("z", (x0 * (1 + k * 0.18), y1 - 13.5, 16.5 + k * 0.1), w + k * 5, 27, drape_e if k == 3 else drape_m,
                      variant=(i + k) % 3)
            par = cb_
            chain.append(cb_.name)
        capes.append(chain)
    _shard(m, "shard_chest_l", ch, (-17, 85, -12), (16, 5, 0), (0, 0, -1), (-35, 0, -6), shard_m, EYES, teeth=2)
    _shard(m, "shard_chest_r", ch, (17, 85, -12), (16, 5, 0), (0, 0, -1), (-35, 0, 6), shard_m, EYES, teeth=2)
    # stairs that spill out of the lower room (folded flat inside until used)
    par = ch
    for k in range(4):
        sb = m.bone(f"stair_{k + 1}", par, pivot=(0, 52, -13 - k * 12))
        for j in range(3):
            sb.box((0, 52 - j * 2.6 - 0.6, -13 - k * 12 - j * 4 - 2), (14 - k, 1.4, 4), st_m, variant=j % 2)
        sb.box((7.4 - k / 2, 51.5 - 4, -13 - k * 12 - 6), (0.8, 6, 0.8), G)
        par = sb

    # ---- neck and the faceless head with its door
    n1 = m.bone("neck1", ch, pivot=(0, 88, 0))
    n1.box((0, 92, 0), (11, 8, 11), P0, variant=10)
    n1.box((0, 88.8, 0), (13, 1.6, 13), G)
    n2 = m.bone("neck2", n1, pivot=(0, 96, 0))
    n2.box((0, 100, 0), (10, 8, 10), P1, variant=10)
    n2.box((0, 103.6, 0), (11.4, 1.2, 11.4), G)
    hd = m.bone("head", n2, pivot=(0, 104, 0))
    HP = porc(crack=0.12)
    hd.box((0, 105.5, 1), (12, 3, 14), HP)
    hd.box((0, 109.5, 0.5), (18, 5, 20), HP, variant=1)
    hd.cube((-12, 113, -1), (24, 16, 13), HP, variant=2)
    hd.cube((-11, 113, -12), (7, 16, 11), HP, variant=3)
    hd.cube((4, 113, -12), (7, 16, 11), HP, variant=3)
    hd.cube((-4, 113, -12), (8, 1, 11), HP)
    hd.cube((-4, 127, -12), (8, 2, 11), HP)
    hd.cube((-10, 114, -13), (6, 14, 1), HP, variant=6)
    hd.cube((4, 114, -13), (6, 14, 1), HP, variant=6)
    hd.box((0, 131, 0), (21, 4, 22), HP, variant=1)
    hd.box((0, 134.5, 0.5), (17, 3, 18), HP, variant=4)
    hd.box((0, 137, 1), (11, 2, 12), HP, variant=4)
    hd.box((12.5, 121, 0), (1, 13, 18), HP, variant=5)
    hd.box((-12.5, 121, 0), (1, 13, 18), HP, variant=5)
    hd.box((0, 121, 12.5), (20, 14, 1), HP, variant=5)
    hd.box((0, 121.5, 13.6), (14, 10, 1.2), HP, variant=7)
    hd.box((-4.6, 120.5, -13.3), (1.2, 15, 0.8), G2)                  # gilt door frame
    hd.box((4.6, 120.5, -13.3), (1.2, 15, 0.8), G2)
    hd.box((0, 128.3, -13.3), (10.4, 1.4, 0.8), G2)
    hd.box((0, 112.8, -14.2), (11, 0.8, 2.6), G)                       # doorstep
    hd.locator("door_c", (0, 120.5, -14))
    _shard(m, "shard_head_l", hd, (-8, 121, -13), (6, 11, 0), (0, 0, -1), (-20, -18, 0), shard_m, EYES, teeth=2)
    _shard(m, "shard_head_r", hd, (12.6, 121, 2), (0, 10, 12), (1, 0, 0), (0, 0, -24), shard_m, EYES, teeth=2)
    _shard(m, "shard_crown", hd, (0, 137, 0), (10, 0, 12), (0, 1, 0), (18, 0, 12), shard_m, EYES, teeth=0)

    # the other world behind the face-door: a night sea with a paper moon
    db = m.bone("dream_box", hd, pivot=(0, 120, -7))
    db.plane("z", (0, 120.5, -1.3), 8, 13, sky_mat())
    db.plane("x", (-3.9, 120.5, -7), 11.4, 13, starwall())
    db.plane("x", (3.9, 120.5, -7), 11.4, 13, starwall())
    db.plane("y", (0, 127.8, -7), 8, 11.4, starwall(), faces=("down",))
    sea = tex.flat("#24407e", glow=0.7)
    db.plane("y", (0, 114.3, -7), 8, 11.4, sea, faces=("up",))
    mo = m.bone("dream_moon", db, pivot=(1.5, 124, -3.5))
    mo.plane("z", (1.5, 124, -3.5), 3.6, 3.6, tex.shaped(tex.m_crescent(0.42), "#fff3c8", "#ffd99a", glow=1.0,
                                                         key="papermoon", var=0.0))
    mo.box((1.5, 126.5, -3.5), (0.2, 1.4, 0.2), tex.flat("#fff3c8", glow=1.0))
    for k, (z, c) in enumerate(((-9.5, "#6c8fd0"), (-5.5, "#a9c8f0"))):
        wv = m.bone(f"dream_wave{k + 1}", db, pivot=(0, 115, z))
        wv.plane("z", (0, 115.6, z), 9.5, 3, tex.shaped(m_wave(0.22, 3.0, 0.15, k * 0.3), c, "#e6f2ff", glow=0.85,
                                                       key=f"wave{k}", var=0.0))
    boat = tex.flat("#fff8ea", glow=0.6)
    db.box((-1.5, 115.8, -7.5), (2.4, 0.8, 1), boat)
    db.box((-1.4, 117.2, -7.5), (0.2, 2, 1.2), boat)
    fd = m.bone("face_door", hd, pivot=(-4, 114, -13))
    fd.cube((-4, 114, -13.8), (8, 13, 1), door_mat(IVORY, SGOLD, key="facedoor"), )
    fd.box((2.6, 120, -14.5), (0.9, 0.9, 0.8), G2)
    fd.box((0, 123.5, -14.4), (1.2, 1.6, 0.6), G)                    # tiny knocker
    # beam of the other world (shown only in the finale; see visibility in build())
    bm = m.bone("beam", hd, pivot=(0, 120.5, -14))
    L = BEAM_LEN
    def beam_mat(w0, w1, c0, c1, alpha, key, stars=True):
        k0, k1 = tex.rgb(c0), tex.rgb(c1)

        def fn(ctx):
            f = np.clip((-14 - ctx.Z) / L, 0, 1)
            half = w0 + (w1 - w0) * f
            inside = np.abs(ctx.Y - 120.5) <= half
            t = tex.tile(ctx, c0, 0.0, 1.0)
            t[..., :3] = tex.mix(k0, k1, f[..., None])
            edge_f = np.clip(1 - np.abs(ctx.Y - 120.5) / np.maximum(half, 1e-3), 0, 1)
            t[..., 3] = np.where(inside, alpha * (0.35 + 0.65 * edge_f), 0.0)
            if stars:
                ix, iy = tex.px(ctx)
                st = inside & (tex._hash(ix // 2, iy // 2, 5) > 0.94)
                t[..., :3] = np.where(st[..., None], tex.rgb("#fff3c8"), t[..., :3])
                t[..., 3] = np.where(st, 0.95, t[..., 3])
            return t
        return Mat(fn, key, mode="blend", spatial=True, density=0.5)
    cone = beam_mat(2.0, 26.0, "#fff4dc", "#7fa6ea", 0.5, "beamcone")
    core = beam_mat(0.8, 6.0, "#ffffff", "#ffe2b8", 0.85, "beamcore", stars=False)
    for k in range(4):
        bm.plane("x", (0, 120.5, -14 - L / 2), L, 54, cone, rot=(0, 0, k * 45), pivot=(0, 120.5, -14))
    for k in range(2):
        bm.plane("x", (0, 120.5, -14 - L / 2), L, 14, core, rot=(0, 0, 22 + k * 90), pivot=(0, 120.5, -14))
    hd.locator("beam_end", (0, 120.5, -14 - L))

    # paper keys and moons drifting round the head like moths
    orb = m.bone("orbit", hd, pivot=(0, 122, 0))
    from kit import glyphs
    for k, g in enumerate(("moon", "key", "star", "moon", "door", "star")):
        a = k * 60
        r = 22 + (k % 2) * 4
        mat = tex.bitmap_cut(glyphs.DREAM[g], "#fff3c8" if k % 2 == 0 else PEACH, glow=1.0, color2=SGOLD)
        orb.box((math.cos(math.radians(a)) * r, 128 + (k % 3) * 5, math.sin(math.radians(a)) * r), (4, 4, 0), mat,
                rot=(0, -a + 90, 0), faces=("north", "south"))

    # ---- arms: rooftop shoulders, arcade forearms that telescope, long fingers
    for s, sx in (("r", 1), ("l", -1)):
        cx = sx * 30
        a1 = m.bone(f"arm_{s}_1", ch, pivot=(sx * 28, 82, 0))
        a1.box((cx, 81, 0), (14, 10, 15), PT)
        a1.box((cx, 86.3, 0), (10, 1.2, 11), G)
        a1.box((cx, 58, 0), (11, 40, 11), P0, variant=11)
        a1.box((cx, 66, 0), (11.8, 1.4, 11.8), G)
        _shard(m, f"shard_arm_{s}", a1, (cx + sx * 5.5, 56, 0), (0, 22, 8), (sx, 0, 0), (0, 0, sx * -26), shard_m, EYES)
        a2 = m.bone(f"arm_{s}_2", a1, pivot=(cx, 37, 0))
        a2.box((cx, 36, 0), (12, 7, 12), PT)
        ed = m.bone(f"edoor_{s}", a2, pivot=(cx + sx * 6.1, 33.5, 2))
        ed.plane("x", (cx + sx * 6.15, 36, 0), 4, 5, door_mat(PEACH, SGOLD, glass="#fff0c8", key="elbowdoor"))
        _arcade(m, a2, cx, 9, 33, 11, P1, arch_a, G, inner="stairs")
        a3 = m.bone(f"arm_{s}_3", a2, pivot=(cx, 9, 0))
        _arcade(m, a3, cx, -15, 9, 10, P1, arch_a, G, inner=None, core=True)
        a3.box((cx, -14.5, 0), (11, 2, 11), G2)
        a3.box((cx, -3, 0), (2.2, 2.2, 2.2), lamp_mat("#fff0d0"))
        a3.locator(f"arm_{s}_mid", (cx, -3, 0))
        hb = m.bone(f"hand_{s}", a3, pivot=(cx, -15, 0))
        hb.box((cx, -22.5, 0), (5, 15, 12), P0, variant=12)
        hb.box((cx, -16, 0), (6, 2, 12.6), G)
        for k, (z, w) in enumerate(((-4.3, 2.8), (-1.2, 2.8), (2.4, 4.2))):
            f1 = m.bone(f"fing_{s}{k + 1}_1", hb, pivot=(cx, -30, z))
            f1.box((cx, -36.5 - k * 0.5, z), (3, 13 + (1 - k) * 1.5, w), P1, variant=k)
            f2 = m.bone(f"fing_{s}{k + 1}_2", f1, pivot=(cx, -43 - k, z))
            f2.box((cx, -48.5 - k, z), (2.6, 11, w * 0.85), P0, variant=k + 3)
            f2.box((cx, -54.4 - k, z), (2.0, 1.2, w * 0.7), G2)
            if k == 1:
                f2.locator(f"tip_{s}", (cx, -55, z))
        t1 = m.bone(f"thumb_{s}_1", hb, pivot=(cx - sx * 0.5, -19, -6))
        t1.box((cx - sx * 0.5, -24, -7.5), (3, 10, 3), P1, rot=(18, 0, 0), pivot=(cx, -19, -6))
        t2 = m.bone(f"thumb_{s}_2", t1, pivot=(cx - sx * 0.5, -28.5, -9))
        t2.box((cx - sx * 0.5, -32, -10), (2.6, 8, 2.6), P0, rot=(12, 0, 0), pivot=(cx, -28.5, -9))
    return m, (drapes, capes)


def cabinet_door_face():
    """Cabinet door face: porcelain panel with two arched lights (cut out: the rooms show through)."""
    kb, kl = tex.rgb(IVORY), tex.rgb(SGOLD)

    def mk(night):
        base = tex.rgb(AGED) if night else kb
        line = tex.rgb("#8e3446") if night else kl

        def fn(ctx):
            u, v = ctx.U, ctx.V
            t = tex.tile(ctx, IVORY, 1, 0.0)
            t[..., :3] = tex.mix(base, base * 0.88, np.clip(v - 0.2, 0, 1)[..., None])
            border = (u < 0.08) | (u > 0.92) | (v < 0.05) | (v > 0.95)
            t[..., :3] = np.where(border[..., None], line, t[..., :3])
            hole = (np.abs(u - 0.5) < 0.26) & (v > 0.16) & (v < 0.5)
            hole |= (np.hypot((u - 0.5) / 0.26, (v - 0.16) / 0.1) < 1)
            rim = ((np.abs(u - 0.5) < 0.32) & (v > 0.1) & (v < 0.55)) & ~hole
            t[..., :3] = np.where(rim[..., None], line, t[..., :3])
            t[..., 3] = np.where(hole, 0.0, 1.0)
            low = (np.abs(u - 0.5) < 0.3) & (v > 0.62) & (v < 0.9)
            lowrim = low & ~((np.abs(u - 0.5) < 0.26) & (v > 0.65) & (v < 0.87))
            t[..., :3] = np.where(lowrim[..., None], line, t[..., :3])
            if night:
                ix, iy = tex.px(ctx)
                c = np.abs(tex.vnoise(ix / 4.0, iy / 4.0, 81) - tex.vnoise(ix / 4.0 + 19.0, iy / 4.0, 82)) < 0.05
                t[..., :3] = np.where(c[..., None] & ~border[..., None], tex.rgb("#8e3446"), t[..., :3])
                t[..., 4] = np.where(c, 0.7, 0.0)
            return tex.grain(ctx, t, 0.02)
        return Mat(fn, f"dnd_cabface{night}", directional=True)
    return tex.alt(mk(False), nightmare=mk(True))


BEAM_LEN = 166.0


# ---------------------------------------------------------------- poses
SH_LIFT = {0: 0.0, 1: 2.5, 2: 6.0, 3: 9.0}


def shards(level):
    rot, pos = {}, {}
    k = SH_LIFT[level]
    for n, (nv, tilt) in SHARDS.items():
        pos[n] = tuple(c * k for c in nv)
        rot[n] = tuple(c * min(1.0, k / 6.0) for c in tilt)
    return {"rot": rot, "pos": pos, "scl": {}}


def with_shards(p, level):
    s = shards(level)
    return {"rot": {**p["rot"], **s["rot"]}, "pos": {**p["pos"], **s["pos"]}, "scl": dict(p["scl"])}


CURL = lambda c1, c2: {f"fing_{{s}}{k}_1": (0, 0, -c1 - (k - 1) * 3) for k in (1, 2, 3)} | \
    {f"fing_{{s}}{k}_2": (0, 0, -c2 - (k - 1) * 3) for k in (1, 2, 3)}

BASE = P(rot={"body": (0, 0, 0), "head": (0, 0, 0), "neck1": (0, 0, 0), "neck2": (0, 0, 0), "spine1": (0, 0, 0),
              "spine2": (0, 0, 0), "spine3": (0, 0, 0), "chest": (0, 0, 0), "face_door": (0, 0, 0),
              "cdoor_{s}": (0, 0, 0), "arm_{s}_1": (0, 0, 0), "arm_{s}_2": (0, 0, 0), "hand_{s}": (0, 0, 0),
              "thigh_{s}": (0, 0, 0), "shin_{s}": (0, 0, 0), "foot_{s}": (0, 0, 0), "thumb_{s}_1": (0, 0, 0),
              "edoor_{s}": (0, 0, 0), **CURL(0, 0),
              **{f"drape{i}_1": (0, 0, 0) for i in range(1, 7)}, **{f"drape{i}_2": (0, 0, 0) for i in range(1, 7)},
              **{f"stair_{k}": (0, 0, 0) for k in range(1, 5)}},
         pos={"root": (0, 0, 0), "arm_{s}_3": (0, 0, 0), **{f"room_{k}": (0, 0, 0) for k in (1, 2, 3)}},
         scl={"root": 1.0, **{f"stair_{k}": 1.0 for k in range(1, 5)}, **{f"room_{k}": 1.0 for k in (1, 2, 3)},
              "face_door": 1.0, "beam": 1.0})

STAIRS_IN = {f"stair_{k}": 0.0 for k in range(1, 5)}

LYING = P(BASE, rot={"body": (90, 0, 0), "neck1": (-10, 0, 0), "head": (-6, 0, 0), "arm_{s}_1": (0, 0, 6),
                     "arm_{s}_2": (6, 0, 0), **CURL(14, 18), "foot_{s}": (40, 0, 0)},
          scl={"root": 0.52, **STAIRS_IN})

SIT = P(BASE, rot={"body": (-4, 0, 0), "thigh_{s}": (94, 0, 2), "foot_{s}": (40, 0, 0), "spine2": (-6, 0, 0),
                   "neck1": (-8, 0, 0), "head": (-14, 0, 0), "arm_{s}_1": (22, 0, 10), "arm_{s}_2": (34, 0, -4),
                   "hand_{s}": (10, 0, 0), **CURL(16, 22),
                   **{f"drape{i}_1": (88, 0, 0) for i in (1, 2)}, **{f"drape{i}_1": (-10, 0, 0) for i in (5, 6)}},
        scl={"root": 0.62, **STAIRS_IN})

DOOR_OPEN = {"face_door": (0, 108, 0)}
HOVER = P(BASE, rot={"body": (-3, 0, 0), "thigh_{s}": (34, 0, 4), "shin_{s}": (-72, 0, 0), "foot_{s}": (30, 0, 0),
                     "spine2": (-2, 0, 0), "neck1": (-6, 0, 0), "head": (-12, 0, 0), "arm_{s}_1": (8, 0, 13),
                     "arm_{s}_2": (18, 0, 0), "hand_{s}": (6, 0, 0), **CURL(12, 18), **DOOR_OPEN,
                     **{f"drape{i}_1": (30, 0, 0) for i in (1, 2)}, **{f"drape{i}_2": (-26, 0, 0) for i in (1, 2)},
                     "thumb_{s}_1": (0, 0, -6)},
          scl={"root": 1.0, **STAIRS_IN})


def lerp_pose(a, b, f):
    out = {"rot": {}, "pos": {}, "scl": {}}
    for ch, d in (("rot", (0, 0, 0)), ("pos", (0, 0, 0)), ("scl", 1.0)):
        for k in set(a[ch]) | set(b[ch]):
            va, vb = a[ch].get(k, d), b[ch].get(k, d)
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                out[ch][k] = va + (vb - va) * f
            else:
                va = va if not isinstance(va, (int, float)) else (va, va, va)
                vb = vb if not isinstance(vb, (int, float)) else (vb, vb, vb)
                out[ch][k] = tuple(va[i] + (vb[i] - va[i]) * f for i in range(3))
    return out


# animation lengths (mirrored as constants in src/spells/dn06_the_dreamer.ts)
LEN = dict(manifest=4.5, sit=3.0, awaken=1.5, rise=3.0, sweep=3.0, cabinet=2.0, raise_=2.0, fire_arms=1.6,
           fire_rooms=1.6, finale=3.0, slam=1.0, forget=5.0)
SWEEP_HIT = (1.25, 2.0)      # seconds into "sweep" while the hand rakes the ground


def build_anims(m, rig):
    drapes, capes = rig
    A = []
    # ---- always: breathing, drifting gown, sliding dormer windows, the sea in its head
    br = Anim("breathe", loop=True)
    br.scl("chest", (LIFE(0.018, 5.4, base=1.0), LIFE(0.012, 5.4, 0.1, base=1.0), LIFE(0.02, 5.4, base=1.0)))
    br.rot("spine3", (LIFE(1.4, 5.4, 0.3), 0, 0))
    br.rot("neck2", (LIFE(1.6, 7.1), LIFE(2.5, 9.3), 0))
    for i, (chain, ax) in enumerate(drapes):
        a = 0 if ax == "z" else 2
        for j, b in enumerate(chain):
            v = [0, 0, 0]
            sgn = -1 if (ax == "x" and i % 2 == 0) else 1
            v[a] = LIFE(3.5 + j * 2.2, 3.6 + i * 0.17, -j * 0.16 + i * 0.11) * sgn
            v[1] = LIFE(2.0 + j, 4.4 + i * 0.3, i * 0.2)
            br.rot(b, tuple(v))
    for i, chain in enumerate(capes):
        for j, b in enumerate(chain):
            br.rot(b, (LIFE(3 + j * 2.5, 4.2 + i * 0.3, -j * 0.14 + i * 0.2, base=9 + j * 4), LIFE(2 + j, 5.1, i * 0.3),
                       LIFE(1.5 + j, 3.7 + i * 0.4, i * 0.25, base=(i - 1) * -5)))
    for s in ("r", "l"):
        for k in (1, 2):
            br.pos(f"win_{s}{k}", (LIFE(4.5 if s == "r" else -4.5, 6.0 + k * 1.3, k * 0.37), 0, 0))
    br.pos("dream_moon", (0, LIFE(0.7, 4.0), 0))
    br.rot("dream_moon", (0, 0, LIFE(6, 5.0)))
    br.pos("dream_wave1", (LIFE(1.1, 3.1), LIFE(0.25, 1.7), 0))
    br.pos("dream_wave2", (LIFE(-1.1, 3.7, 0.2), LIFE(0.25, 2.1, 0.3), 0))
    br.rot("orbit", (LIFE(6, 9.0), spin(18), LIFE(5, 7.0, 0.25)))
    for s in ("r", "l"):
        for k in (1, 2, 3):
            br.rot(f"fing_{s}{k}_2", (0, 0, LIFE(3, 3.3 + k * 0.4, k * 0.2) * (1 if s == "r" else -1)))
    A.append(br)

    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    # ---- 1 manifest: lying in the bed, appearing section by section (feet first, head last)
    mf = Anim("manifest", length=LEN["manifest"], loop="hold")
    keyed(mf, {0: LYING, LEN["manifest"]: LYING}, skip=())
    reveal = [("thigh_{s}", 0.0, 0.7), ("pelvis", 0.55, 1.25), ("spine1", 1.1, 1.7), ("spine2", 1.5, 2.1),
              ("spine3", 1.9, 2.5), ("chest", 2.3, 3.0), ("arm_{s}_1", 2.9, 3.5), ("neck1", 3.3, 3.8),
              ("head", 3.7, 4.4)]
    for pat, t0, t1 in reveal:
        keys = {0: 0.0, t0: 0.0, t0 + (t1 - t0) * 0.75: 1.07, t1: 1.0}
        if t0 == 0:
            keys = {0: 0.0, t1 * 0.75: 1.07, t1: 1.0}
        for b in ([pat.format(s="r"), pat.format(s="l")] if "{s}" in pat else [pat]):
            mf.scl(b, keys, smooth=False)
    mf.particle(1.0, "porcelain", "chest_c")
    mf.particle(2.6, "porcelain", "chest_c")
    mf.particle(4.0, "glint", "door_c")
    A.append(mf)

    # ---- 2 sit up in bed (with weight: press down, heave, overshoot, settle)
    sit = Anim("sit", length=LEN["sit"], loop="hold")
    press = P(LYING, rot={"body": (93, 0, 0), "arm_{s}_1": (-14, 0, 10), "arm_{s}_2": (10, 0, 0)},
              pos={"root": (0, -1.5, 0)})
    mid = lerp_pose(LYING, SIT, 0.55)
    mid = P(mid, rot={"head": (-30, 0, 0), "neck1": (-14, 0, 0), "arm_{s}_1": (-30, 0, 18)}, scl={"root": 0.57})
    over = P(SIT, rot={"body": (-11, 0, 0), "thigh_{s}": (101, 0, 2), "head": (-24, 0, 0)})
    keyed(sit, {0: LYING, 0.45: press, 1.6: mid, 2.45: over, 3.0: SIT})
    A.append(sit)

    # ---- 3 awaken: the head turns toward the enemies and the small door opens
    aw = Anim("awaken", length=LEN["awaken"], loop="hold")
    look = P(SIT, rot={"head": (-16, -32, -4), "neck2": (0, -10, 0)})
    look2 = P(SIT, rot={"head": (-20, 6, 2), "neck2": (-4, 4, 0), "face_door": (0, 40, 0)})
    opened = P(SIT, rot={"head": (-18, 0, 0), "neck2": (-4, 0, 0), "face_door": (0, 116, 0)})
    done = P(SIT, rot={"head": (-18, 0, 0), "neck2": (-4, 0, 0), **DOOR_OPEN})
    keyed(aw, {0: SIT, 0.5: look, 0.9: look2, 1.25: opened, 1.5: done})
    A.append(aw)

    # ---- 4 rise: leaves the bed and grows to its full colossal height
    ri = Anim("rise", length=LEN["rise"], loop="hold")
    d_sit = P(done)
    push = P(d_sit, rot={"body": (-22, 0, 0), "arm_{s}_1": (-6, 0, 22), "arm_{s}_2": (6, 0, 0), "head": (-26, 0, 0)},
             pos={"root": (0, -2, 0)})
    lift = lerp_pose(push, HOVER, 0.5)
    lift = P(lift, rot={"body": (-14, 0, 0), "arm_{s}_1": (18, 0, 34), "arm_{s}_2": (30, 0, 0), "head": (6, 0, 0)},
             scl={"root": 0.84})
    up_ = P(HOVER, rot={"body": (4, 0, 0), "arm_{s}_1": (4, 0, 22), "head": (-2, 0, 0)}, scl={"root": 1.03})
    keyed(ri, {0: d_sit, 0.6: push, 1.7: lift, 2.55: up_, 3.0: HOVER})
    ri.particle(1.0, "porcelain", "chest_c")
    A.append(ri)

    hov = Anim("hover", loop=True)
    keyed(hov, {0: HOVER})
    A.append(hov)

    # ---- 6 sweep: right hand rakes the ground in an arc (right side -> left side)
    sw = Anim("sweep", length=LEN["sweep"], loop="hold")
    wind = P(HOVER, rot={"body": (6, 0, 0), "spine1": (0, -16, 0), "spine3": (0, -14, 0), "head": (-6, -20, 0),
                         "arm_r_1": (-20, 0, 74), "arm_r_2": (40, 0, 0), "arm_l_1": (40, 0, -8), "arm_l_2": (40, 0, 0)},
             pos={"arm_r_3": (0, -8, 0)})
    def reach(tw, rz):
        return P(HOVER, rot={"body": (-38, 0, 0), "spine1": (-8, tw, 0), "spine2": (-8, 0, 0), "spine3": (-6, tw * 0.7, 0),
                             "head": (-14, tw * 0.8, 0), "arm_r_1": (70, 0, rz), "arm_r_2": (8, 0, 0), "hand_r": (-10, 0, 0),
                             "arm_l_1": (30, 0, -30 - tw * 0.5), "arm_l_2": (50, 0, 0), "thigh_{s}": (50, 0, 4),
                             **{f"fing_r{k}_1": (0, 0, 8) for k in (1, 2, 3)}},
                 pos={"arm_r_3": (0, -16, 0)})
    reach0, reach1 = reach(-16, -8), reach(18, -12)
    keyed(sw, {0: HOVER, 0.85: wind, SWEEP_HIT[0]: reach0, SWEEP_HIT[1]: reach1,
               2.3: P(reach1, rot={"body": (-24, 0, 0)}, pos={"arm_r_3": (0, -12, 0)}), 3.0: HOVER})
    sw.particle(SWEEP_HIT[0] + 0.1, "dust", "tip_r")
    sw.particle(SWEEP_HIT[0] + 0.4, "dust", "tip_r")
    A.append(sw)

    # ---- 7 cabinet: doors open, a staircase spills out of the lowest room
    cb = Anim("cabinet", length=LEN["cabinet"], loop="hold")
    opn = P(HOVER, rot={"cdoor_r": (0, -118, 0), "cdoor_l": (0, 118, 0), "body": (-10, 0, 0), "head": (-22, 0, 0),
                        "arm_{s}_1": (14, 0, 36), "arm_{s}_2": (30, 0, 0)})
    unfold = P(opn, rot={"stair_1": (-22, 0, 0), "stair_2": (-10, 0, 0), "stair_3": (-8, 0, 0), "stair_4": (-6, 0, 0)},
               scl={f"stair_{k}": 1.0 for k in range(1, 5)})
    keyed(cb, {0: HOVER, 0.5: P(opn, scl=STAIRS_IN), 0.6: P(opn, scl={**STAIRS_IN, "stair_1": 0.2}),
               1.3: unfold, 2.0: unfold}, smooth=True)
    A.append(cb)

    # ---- 8 raise both hands (dream right, nightmare left); 9 conjure loop
    RAISE = P(HOVER, rot={"body": (6, 0, 0), "head": (6, 0, 0), "arm_r_1": (128, -20, 34), "arm_r_2": (20, 0, 0),
                          "hand_r": (30, 0, 0), "arm_l_1": (128, 20, -34), "arm_l_2": (24, 0, 0), "hand_l": (40, 0, 0),
                          **{f"fing_r{k}_1": (0, 0, 6 - k * 2) for k in (1, 2, 3)},
                          **{f"fing_r{k}_2": (0, 0, 4) for k in (1, 2, 3)},
                          **{f"fing_l{k}_1": (0, 0, 52) for k in (1, 2, 3)},
                          **{f"fing_l{k}_2": (0, 0, 64) for k in (1, 2, 3)}, "edoor_{s}": (0, 0, 0)})
    RAISE = with_shards(RAISE, 1)
    rs = Anim("raise", length=LEN["raise_"], loop="hold")
    ant = P(HOVER, rot={"body": (-10, 0, 0), "arm_{s}_1": (-10, 0, 20), "head": (-24, 0, 0)})
    keyed(rs, {0: HOVER, 0.6: with_shards(ant, 0), 1.5: P(RAISE, rot={"body": (9, 0, 0)}), 2.0: RAISE})
    A.append(rs)
    cj = Anim("conjure", loop=True, length=2.0)
    keyed(cj, {0: RAISE}, skip=("arm_r_1", "arm_l_1", "body"))
    cj.rot("arm_r_1", (S(14, 2.0, 0, base=128), -20, S(8, 2.0, 0.1, base=34)))
    cj.rot("arm_l_1", (S(14, 2.0, 0.5, base=128), 20, S(-8, 2.0, 0.6, base=-34)))
    cj.rot("body", (6, S(4, 2.0, 0.25), 0))
    A.append(cj)

    # ---- 10 conduct: the Great Unreality (loop)
    COND = with_shards(P(HOVER, rot={"cdoor_r": (0, -30, 0), "cdoor_l": (0, 30, 0), "edoor_{s}": (0, 0, 0),
                                     "head": (-14, 0, 0)}), 2)
    cd = Anim("conduct", loop=True, length=4.0)
    keyed(cd, {0: COND}, skip=("arm_r_1", "arm_l_1", "arm_r_2", "arm_l_2", "body", "spine3", "head", "edoor_r", "edoor_l"))
    cd.rot("arm_r_1", (S(30, 4.0, 0, base=80), S(20, 4.0, 0.25), S(28, 2.0, 0, base=40)))
    cd.rot("arm_l_1", (S(30, 4.0, 0.5, base=80), S(-20, 4.0, 0.75), S(-28, 2.0, 0.5, base=-40)))
    cd.rot("arm_r_2", (S(20, 4.0, 0.15, base=34), 0, 0))
    cd.rot("arm_l_2", (S(20, 4.0, 0.65, base=34), 0, 0))
    cd.rot("body", (S(5, 4.0, 0.1, base=-6), S(8, 4.0, 0.3), S(3, 4.0)))
    cd.rot("spine3", (0, S(10, 4.0, 0.35), 0))
    cd.rot("head", (S(6, 4.0, 0.2, base=-14), S(-12, 4.0, 0.4), 0))
    cd.rot("edoor_r", (0, 0, S(40, 2.0, 0, base=50)))
    cd.rot("edoor_l", (0, 0, S(-40, 2.0, 0.5, base=-50)))
    A.append(cd)

    # ---- 11 fire_arms: the forearm arcades thrust and release window-shards
    fa = Anim("fire_arms", length=LEN["fire_arms"], loop="hold")
    back = P(COND, rot={"body": (6, 0, 0), "arm_{s}_1": (40, 0, 60), "arm_{s}_2": (90, 0, 0), "head": (-4, 0, 0)},
             pos={"arm_{s}_3": (0, 0, 0)})
    thrust = P(COND, rot={"body": (-16, 0, 0), "arm_{s}_1": (86, 0, 14), "arm_{s}_2": (4, 0, 0), "hand_{s}": (-30, 0, 0),
                          "head": (-20, 0, 0)}, pos={"arm_{s}_3": (0, -22, 0)})
    keyed(fa, {0: COND, 0.45: back, 0.65: thrust, 0.9: P(thrust, rot={"body": (-12, 0, 0)}), 1.6: P(thrust, pos={"arm_{s}_3": (0, -10, 0)})})
    fa.particle(0.65, "glint", "arm_r_mid")
    fa.particle(0.65, "glint", "arm_l_mid")
    A.append(fa)

    # ---- 12 fire_rooms: the cabinet flings open and fires its little rooms
    fr = Anim("fire_rooms", length=LEN["fire_rooms"], loop="hold")
    flung = P(COND, rot={"cdoor_r": (0, -150, 0), "cdoor_l": (0, 150, 0), "body": (10, 0, 0), "arm_{s}_1": (10, 0, 70),
                         "arm_{s}_2": (20, 0, 0), "head": (6, 0, 0)})
    shot = P(flung, rot={"body": (-18, 0, 0), "head": (-24, 0, 0)},
             pos={"room_1": (0, 0, -30), "room_2": (0, 0, -30), "room_3": (0, 0, -30)},
             scl={"room_1": 0.0, "room_2": 0.0, "room_3": 0.0})
    keyed(fr, {0: COND, 0.3: flung, 0.5: P(flung, rot={"body": (14, 0, 0)}), 0.62: P(shot, pos={"room_1": (0, 0, -10)},
                                                                                    scl={"room_1": 1.2, "room_2": 1.2, "room_3": 1.2}),
               0.8: shot, 1.6: P(shot, rot={"body": (-10, 0, 0)})})
    fr.particle(0.62, "glint", "chest_c")
    A.append(fr)

    # ---- 13 finale: the face-door opens fully and the other world pours out
    FIN = with_shards(P(COND, rot={"body": (-26, 0, 0), "spine2": (-6, 0, 0), "neck1": (-14, 0, 0), "neck2": (-12, 0, 0),
                                   "head": (-28, 0, 0), "arm_{s}_1": (30, 0, 76), "arm_{s}_2": (34, 0, 0),
                                   "hand_{s}": (0, 0, 30), "face_door": (0, 168, 0), "cdoor_r": (0, -90, 0),
                                   "cdoor_l": (0, 90, 0), **CURL(-6, -4)}), 3)
    fn = Anim("finale", length=LEN["finale"], loop="hold")
    pre = P(COND, rot={"body": (6, 0, 0), "head": (8, 0, 0), "arm_{s}_1": (60, 0, 40), "arm_{s}_2": (70, 0, 0)})
    keyed(fn, {0: COND, 0.4: pre, 1.0: FIN, 3.0: FIN}, skip=("beam",))
    fn.scl("beam", {0: (1, 1, 0.0), 0.5: (1, 1, 0.0), 1.2: (1.25, 1.25, 1.0), 1.5: (1.0, 1.0, 1.0), 3.0: (1.1, 1.1, 1.0)},
           smooth=False)
    fn.scl("face_door", {0: 1.0, 0.8: 1.0, 1.1: 1.3, 3.0: 1.3}, smooth=False)
    fn.rot("beam", (0, 0, spin(40)))
    fn.particle(1.0, "glint", "door_c")
    A.append(fn)
    FIN_T = 1.0

    # ---- 14 slam: the door slams shut -- final strike
    sl = Anim("slam", length=LEN["slam"], loop="hold")
    shut = P(FIN, rot={"face_door": (0, -8, 0), "head": (-10, 0, 0), "body": (-34, 0, 0), "arm_{s}_1": (96, 0, 10),
                       "arm_{s}_2": (10, 0, 0), "hand_{s}": (-20, 0, 0)})
    rest = P(shut, rot={"face_door": (0, 0, 0), "body": (-24, 0, 0)})
    keyed(sl, {0: FIN, 0.15: shut, 0.35: P(rest, rot={"face_door": (0, 4, 0)}), 1.0: rest}, skip=("beam",))
    sl.scl("beam", {0: (1.1, 1.1, 1.0), 0.15: (0.2, 0.2, 0.0)}, smooth=False)
    sl.scl("face_door", {0: 1.3, 0.15: 1.0}, smooth=False)
    A.append(sl)

    # ---- 15 forget: lies back and breaks into drifting porcelain panels
    fg = Anim("forget", length=LEN["forget"], loop="hold")
    lie = P(HOVER, rot={"body": (36, 0, 0), "head": (16, 0, 0), "arm_{s}_1": (40, 0, 60), "arm_{s}_2": (10, 0, 0),
                        **CURL(4, 6), "thigh_{s}": (10, 0, 6), "shin_{s}": (-20, 0, 0), "face_door": (0, 0, 0)})
    keyed(fg, {0: P(rest), 1.2: lie, 5.0: P(lie, rot={"body": (48, 0, 0)})},
          skip=tuple(SHARDS) + ("head", "arm_r_1", "arm_l_1", "chest", "pelvis", "thigh_r", "thigh_l", "root"))
    order = sorted(SHARDS, key=lambda n: (0 if "head" in n or "crown" in n else 1 if "chest" in n or "arm" in n else 2, n))
    for i, n in enumerate(order):
        nv, tilt = SHARDS[n]
        t0 = 0.3 + i * 0.12
        far = tuple(c * 40 for c in nv)
        fg.pos(n, {0: tuple(c * 9 for c in nv), t0: tuple(c * 10 for c in nv), t0 + 1.2: (far[0], far[1] + 18, far[2]),
                   t0 + 2.4: (far[0] * 1.6, far[1] + 46, far[2] * 1.6)})
        fg.rot(n, {0: tilt, t0 + 2.4: (tilt[0] * 6 + 90, 140 + i * 30, tilt[2] * 6)})
        fg.scl(n, {0: 1.0, t0 + 1.6: 1.0, t0 + 2.4: 0.0}, smooth=False)
    drift = [("head", 2.0, (0, 40, 30), (40, 30, 0)), ("arm_r_1", 2.4, (40, 20, 0), (0, 0, 60)),
             ("arm_l_1", 2.5, (-40, 20, 0), (0, 0, -60)), ("chest", 3.1, (0, 10, -20), (-20, 0, 0)),
             ("thigh_r", 3.3, (10, -20, 0), (0, 0, 20)), ("thigh_l", 3.4, (-10, -20, 0), (0, 0, -20)),
             ("pelvis", 3.8, (0, -6, 0), (10, 0, 0))]
    for b, t0, dp, dr in drift:
        base_rot = lie["rot"].get(b, (0, 0, 0))
        fg.pos(b, {0: (0, 0, 0), t0: (0, 0, 0), t0 + 1.0: dp})
        fg.rot(b, {0: base_rot, t0: base_rot, t0 + 1.0: tuple(base_rot[i] + dr[i] for i in range(3))})
        fg.scl(b, {0: 1.0, t0: 1.0, t0 + 0.4: 1.04, t0 + 1.0: 0.0}, smooth=False)
    fg.scl("root", {0: 1.0, 4.2: 1.0, 5.0: 0.0}, smooth=False)
    fg.particle(0.4, "porcelain", "door_c")
    fg.particle(2.2, "porcelain", "chest_c")
    fg.particle(3.4, "porcelain", "chest_c")
    A.append(fg)
    return A


STATES = {0: ["hidden"], 1: ["manifest"], 2: ["sit"], 3: ["awaken"], 4: ["rise"], 5: ["hover"], 6: ["sweep"],
          7: ["cabinet"], 8: ["raise"], 9: ["conjure"], 10: ["conduct"], 11: ["fire_arms"], 12: ["fire_rooms"],
          13: ["finale"], 14: ["slam"], 15: ["forget"]}


# ---------------------------------------------------------------- geometry probes (for the script)
def probe(m, pose, bone, p):
    mats = m.bone_matrices(pose)
    v = mats[bone] @ np.array([p[0], p[1], p[2], 1.0])
    return v[:3]


def blocks(v):
    """bb units -> (right, up, forward) in blocks for the script (forward = model front = -Z)."""
    return (round(float(v[0]) * BPU, 2), round(float(v[1]) * BPU, 2), round(float(-v[2]) * BPU, 2))


def report(m, anims):
    by = {a.name: a for a in anims}
    tip_bone, tip = "fing_r2_2", m["fing_r2_2"].locators["tip_r"]
    out = {}
    for t in (SWEEP_HIT[0], (SWEEP_HIT[0] + SWEEP_HIT[1]) / 2, SWEEP_HIT[1]):
        out[f"sweep@{t}"] = blocks(probe(m, by["sweep"].pose(t), tip_bone, tip))
    out["chest_hover"] = blocks(probe(m, by["hover"].pose(0), "chest", m["chest"].locators["chest_c"]))
    out["chest_rooms"] = blocks(probe(m, by["fire_rooms"].pose(0.62), "chest", m["chest"].locators["chest_c"]))
    out["door_hover"] = blocks(probe(m, by["hover"].pose(0), "head", m["head"].locators["door_c"]))
    out["arm_r_fire"] = blocks(probe(m, by["fire_arms"].pose(0.65), "arm_r_3", m["arm_r_3"].locators["arm_r_mid"]))
    out["arm_l_fire"] = blocks(probe(m, by["fire_arms"].pose(0.65), "arm_l_3", m["arm_l_3"].locators["arm_l_mid"]))
    fp = by["finale"].pose(2.0)
    out["door_finale"] = blocks(probe(m, fp, "head", m["head"].locators["door_c"]))
    out["beam_end"] = blocks(probe(m, fp, "head", m["head"].locators["beam_end"]))
    out["right_hand_raise"] = blocks(probe(m, by["raise"].pose(2.0), "fing_r2_2", tip))
    lo, hi = m.bbox(by["manifest"].pose(4.5))
    out["lying_min_y"] = round(float(lo[1]) * BPU, 2)
    out["lying_z"] = (round(float(-hi[2]) * BPU, 2), round(float(-lo[2]) * BPU, 2))
    lo, hi = m.bbox(by["hover"].pose(0))
    out["hover_y"] = (round(float(lo[1]) * BPU, 2), round(float(hi[1]) * BPU, 2))
    return out


def build(pack):
    m, rig = build_model()
    anims = build_anims(m, rig)
    pack.actor("dreamer", m, anims, STATES, always=["breathe"], scale=SCALE, lifetime=120,
               visibility=[{"beam": "q.property('grimoire:state') == 13"}],
               particles={"porcelain": "grimoire:dn_dreamer_porcelain", "glint": "grimoire:dn_dreamer_glint",
                          "dust": "grimoire:dn_dreamer_dust"},
               display="The Dreamer", blend=0.35)
    by = {a.name: a for a in anims}
    br = (by["breathe"], 1.0)
    pack.preview("dreamer_a", m, [[(by["hover"], 0), br]], views=((20, 8), (160, 10), (-90, 4), (0, 2)), cell=(520, 520),
                 hide=("beam",))
    pack.preview("dreamer_b", m, [[(by["manifest"], 2.4)], [(by["sit"], 3.0)], [(by["sweep"], 1.6)],
                                  [(by["raise"], 2.0)], [(by["finale"], 2.0)], [(by["forget"], 2.9)]],
                 views=((30, 12), (-70, 10)), cell=(360, 360), skin="nightmare", hide=("beam",))
    pack.preview("dreamer_d", m, [[(by["finale"], 2.0)]], views=((30, 10), (-80, 5)), cell=(480, 480))
    pack.preview("dreamer_c", m, [[(by["cabinet"], 2.0)], [(by["fire_rooms"], 0.3)]], views=((8, 6), (40, 25)),
                 cell=(520, 520), hide=("beam",))
    print(f"    dreamer: {m.cube_count()} cubes, {len(m.order)} bones, tex {m.tex_size}")
    for k, v in report(m, anims).items():
        print(f"      probe {k}: {v}")
