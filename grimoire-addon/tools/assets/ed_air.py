"""Air Dragon -- the Four-Winged Aether Raptor (Microraptor-inspired), plus its ED04 constructs.

Hero actor ``dragon_air`` (SCALE 1.5, ACTOR "dragon_air").  Rendered ~13 blocks nose to tail-fan,
~16 blocks wingspan.  Front faces -Z, right side +X.  Units below are model units (1/16 block,
multiply by SCALE/16 for blocks).

RIG (bone names; right side ``_r`` at +X, left ``_l`` mirrored)
  root                      entity origin; perched feet touch y=0.  Every FLIGHT animation moves
                            root by (0, -22, 0) so the body centre rides ~0.9 blocks above the
                            origin (scripts fly the origin along the path).
  fly      pivot (0,31,0)   flight attitude: pitch (rx, - = nose down), bank / roll (rz, + = left
                            wing down), yaw (ry).  Parent of everything.
  body     pivot (0,31,0)   slender feathered torso z -12..+12.
  neck1..neck4  pivot (0,34,-11) chain authored horizontally toward -Z (lengths 6,6,6,5); the
                            S-curve is posed by rx (+ = lift).  head pivot (0,34,-34), jaw pivot
                            (0,33,-38), crest pivot (0,38.5,-37).  Locator ``mouth``.
  tail1..tail7  pivot (0,32,13) chain toward +Z, 8 units each (stiff Microraptor tail; rx + = tip
                            down, ry = rudder).  fan pivot (0,32,69) + feathers fan_c, fan_{s}1..3.
                            Locator ``tail_tip``.
  wf_{s}_a1/a2/a3           FORE wing: humerus 15 / forearm 19 / hand 15 along +-X from the
                            shoulder (+-5,34,-9).  rz + = wing up, ry - = sweep back.  Flight
                            feathers (each its own bone, quill at pivot, vane toward +Z):
                            wf_{s}_f1_1..3 tertials, wf_{s}_f2_1..5 secondaries,
                            wf_{s}_f3_1..5 primaries, wf_{s}_t1..3 wing-tip primaries.
                            Locators tip_r / tip_l.
  leg_{s}_1..leg_{s}_4      HIND wing / leg: thigh 10, shin 13, metatarsus 9, toes 5 from the hip
                            (+-5,29,9).  BIND POSE = flight pose (legs trail straight back);
                            perched legs are posed by rx (thigh 120, shin -60, tarsus 35, toes 85).
                            Leg flight feathers: leg_{s}_f2_1..4 (shin), leg_{s}_f3_1..4 (tarsus).
  Bind pose of both wing pairs = fully spread.  Every feather bone's rest yaw is its fan angle.

LOCOMOTION SPEEDS (script side): ``move`` (flap, 0.8 s cycle) 8-16 blocks/s, ``glide`` and banks
14-24 blocks/s, ``stoop`` 26-40 blocks/s, ``flutter`` 0-4 blocks/s (hover), ``land`` covers the
last ~2.5 blocks of descent in 1.0 s.  Perched states (idle, rest) are stationary.

STATES / STATE_IDS: see below.  Contract names: hidden arrive idle move turn_l turn_r attack_a
attack_b power react rest depart; extra: glide roll stoop flare land flutter.
Skins: 0 default (pale silver-blue iridescent), 1 "aether" (glowing feather edges, used by power).
Timing constants that scripts mirror: ARRIVE 2.4 s, ROLL 1.0 s, LAND 1.0 s, ATTACK_A hit 0.3 s,
ATTACK_B hit 0.35 s, DEPART 1.6 s.
"""
import math

import numpy as np

from kit import synth as sy, tex
from kit.anim import LIFE, Anim, M, S
from kit.geo import FaceCtx, Mat, Model, ring
from kit.parts import flutter, sym, wave

from .a_fx_common import particles

ACTOR = "dragon_air"
SCALE = 1.5
LIFETIME = 150

# palette: pale silver-blue iridescent plumage, storm-dark barring, bone-ivory claws, aether glow
PALE, SILVER, MID, DARK, BAR = "#e6eef7", "#c3d2e4", "#93a9c4", "#4c5f7e", "#33425c"
SHEEN_A, SHEEN_B, AETHER, IVORY, BRONZE = "#a8c6ff", "#c2b3ec", "#bff3ff", "#e9dfc6", "#8a6a3a"

FLY_DY = -22          # root offset used by every flight animation
SHOULDER = (5.0, 34.0, -9.0)
FW_SEG = [15, 19, 15]
# per arm segment: n feathers, length inner->outer, width, fan angle inner->outer (deg, + = outward)
FW_ROWS = [(3, 15, 18, 7.0, 0, 3), (5, 19, 23, 6.5, 3, 10), (5, 24, 30, 6.0, 14, 44)]
FW_TIPS = [(30, 6.0, 54), (28, 5.5, 66), (25, 5.0, 79)]
HIP = (5.0, 29.0, 9.0)
LEG_SEG = [10, 13, 9, 5]
HW_ROWS = {2: (4, 11, 15, 5.0, 84, 64), 3: (4, 18, 22, 5.5, 56, 26)}
TAIL_START, TAIL_N, TAIL_L = (0.0, 32.0, 13.0), 7, 8
FAN = [("fan_c", 0, 26), ("fan_{s}1", 13, 24), ("fan_{s}2", 26, 22), ("fan_{s}3", 39, 19)]


# ============================================================================ materials
def qz(base):
    """Feather plane whose quill (tile top) points to -Z in bone space on every face it shows."""
    def fn(ctx):
        f = ctx.face
        if f in ("up", "down"):
            t = np.asarray(base.fn(ctx), dtype=float)
            return t[::-1].copy() if f == "down" else t
        if f in ("east", "west"):
            c = FaceCtx()
            c.w, c.h, c.face, c.group = ctx.h, ctx.w, ctx.face, ctx.group
            c.size, c.rng, c.variant, c.alt = ctx.size, ctx.rng, ctx.variant, ctx.alt
            c.U, c.V = ctx.V.T, ctx.U.T
            c.X, c.Y, c.Z = ctx.X.T, ctx.Y.T, ctx.Z.T
            t = np.asarray(base.fn(c), dtype=float).transpose(1, 0, 2)
            return t[:, ::-1].copy() if f == "east" else t.copy()
        return base.fn(ctx)
    return Mat(fn, base.key + "|qz", mode=base.mode, directional=True)


def feather_mat(base, tip, rachis, bars=0, taper=0.75, notch=0.15, key=""):
    """Iridescent flight feather with dark distal barring; 'aether' skin lights vane edges."""
    kbar, ka, kc, kg = tex.rgb(BAR), tex.rgb(SHEEN_A), tex.rgb(SHEEN_B), tex.rgb(AETHER)

    def make(gl, gtip, edge_glow):
        f = tex.feather(base, tip, rachis, glow=gl, glow_tip=gtip, taper=taper, notch=notch)

        def post(ctx, t):
            u, v = ctx.U, ctx.V
            if bars:
                m = (((v * bars * 2) % 2.0) > 1.3) & (v > 0.42)
                t[..., :3] = np.where(m[..., None], tex.mix(t[..., :3], kbar, 0.62), t[..., :3])
            s = 0.5 + 0.5 * np.sin(u * 6.0 + v * 9.0 + ctx.variant * 1.7)
            t[..., :3] = tex.mix(t[..., :3], tex.mix(ka, kc, s[..., None]), 0.16)
            if edge_glow:
                ix, iy = tex.px(ctx)
                inside = t[..., 3] > 0.5
                pad = np.pad(inside, 1)
                nb = pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:]
                rim = inside & ~nb
                mid = (np.abs(ix - (ctx.w - 1) / 2) < 0.75) & inside
                lit = (rim & (v > 0.55)) | (mid & (v > 0.15))
                t[..., :3] = np.where(lit[..., None], tex.mix(t[..., :3], kg, 0.7), t[..., :3])
                t[..., 4] = np.where(lit, edge_glow, t[..., 4])
            return t
        return tex.overlay(f, post, f"edf{bars}{edge_glow}{key}")
    return qz(tex.alt(make(0.0, 0.1, 0), aether=make(0.0, 0.25, 0.95)))


def plumage(top, belly, edge, cell=4, edge_glow=0.0, key="plum"):
    """Body covering of small overlapping contour feathers (rounded tips, shafts, sheen)."""
    kt, kb, ke = tex.rgb(top), tex.rgb(belly), tex.rgb(edge)
    ka, kc, kg = tex.rgb(SHEEN_A), tex.rgb(SHEEN_B), tex.rgb(AETHER)

    def paint(ctx, eg):
        ix, iy = tex.px(ctx)
        row = iy // cell
        ox = ix + (row % 2) * (cell // 2)
        lx, ly = ox % cell, iy % cell
        if ctx.face == "up":
            base = np.broadcast_to(kt, (ctx.h, ctx.w, 3)).copy()
        elif ctx.face == "down":
            base = np.broadcast_to(kb, (ctx.h, ctx.w, 3)).copy()
        else:
            base = tex.mix(kt, kb, np.clip((ctx.V - 0.2) / 0.75, 0, 1)[..., None])
        cx = (lx - (cell - 1) / 2) / (cell / 2)
        rounded = (ly == cell - 1) | ((ly == cell - 2) & (np.abs(cx) > 0.62))
        shaft = (np.abs(cx) < 0.3) & (ly < cell - 2)
        n = tex.fbm(ix / 6 + ctx.variant * 7, iy / 6, 5)
        col = tex.mix(base, tex.mix(ka, kc, n[..., None]), 0.18)
        col = np.where(rounded[..., None], tex.mix(col, ke, 0.5), col)
        col = np.where(shaft[..., None], np.clip(col * 1.06 + 0.03, 0, 1), col)
        t = tex.tile(ctx, top, 1.0, 0.0)
        t[..., :3] = col * (0.93 + 0.12 * tex._hash(ox // cell, row, 3 + ctx.variant))[..., None]
        if eg:
            lit = rounded & (tex._hash(ox // cell, row, 9) > 0.55)
            t[..., :3] = np.where(lit[..., None], tex.mix(t[..., :3], kg, 0.6), t[..., :3])
            t[..., 4] = np.where(lit, eg, 0.0)
        return tex.grain(ctx, t, 0.03)
    base = Mat(lambda c: paint(c, edge_glow), f"{key}{top}{belly}{edge}{cell}{edge_glow}")
    lit = Mat(lambda c: paint(c, 0.75), f"{key}{top}{belly}{edge}{cell}lit")
    return tex.alt(base, aether=lit)


def cloud_mat(top, bottom, a=0.82, key="edcloud"):
    kt, kb = tex.rgb(top), tex.rgb(bottom)

    def fn(ctx):
        ix, iy = tex.px(ctx)
        n = tex.fbm(ix / 5 + ctx.variant * 9.3, iy / 5, 81)
        if ctx.face == "up":
            col = np.broadcast_to(kt, (ctx.h, ctx.w, 3))
        elif ctx.face == "down":
            col = np.broadcast_to(kb, (ctx.h, ctx.w, 3))
        else:
            col = tex.mix(kt, kb, ctx.V[..., None] ** 1.3)
        t = tex.tile(ctx, top, a)
        t[..., :3] = np.clip(col * (0.88 + 0.22 * n[..., None]), 0, 1)
        d = np.minimum(np.minimum(ctx.U, 1 - ctx.U), np.minimum(ctx.V, 1 - ctx.V)) * 2
        t[..., 3] = a * np.clip(d * 2.4 + (n - 0.5) * 0.9, 0, 1)
        return t
    return Mat(fn, f"{key}{top}{bottom}{a}", mode="blend")


def current_mat(color, edge, a=0.5, key="edcur"):
    """Translucent air current: longitudinal streaks along the tile V axis, soft edges across U."""
    kc, ke = tex.rgb(color), tex.rgb(edge)

    def fn(ctx):
        u, v = ctx.U, ctx.V
        ix, iy = tex.px(ctx)
        n = tex.vnoise(ix / 1.5 + ctx.variant * 5, iy / 9.0, 91)
        streak = 0.5 + 0.5 * np.sin(u * 23.0 + n * 3.0)
        side = np.clip(np.sin(u * math.pi) * 1.4, 0, 1)
        t = tex.tile(ctx, color, a)
        t[..., :3] = tex.mix(kc, ke, (streak * (1 - side * 0.4))[..., None])
        t[..., 3] = np.clip(a * side * (0.35 + 0.75 * streak) * (0.6 + 0.4 * np.sin(v * math.pi)), 0, 1)
        return t
    return Mat(fn, f"{key}{color}{edge}{a}", mode="blend")


def teeth_mat():
    return tex.bitmap_cut(["###############", "# # # # # # # #", "#   #   #   #  "], IVORY, glow=0.0, color2="#cfc3a2")


# ============================================================================ model
def _feather(m, name, parent, pivot, length, width, mat, ang, side, variant=0, dens=1.5):
    b = m.bone(name, parent, pivot=pivot, rot=(0, side * ang, 0))
    px, py, pz = pivot
    b.plane("y", (px, py, pz + length / 2), width, length, mat, density=dens, variant=variant)
    return b


def build_model():
    m = Model("dragon_air", density=1.0, bounds=(40, 30, (0, 2, 0)), alts=("aether",))
    plum = plumage("#9fb3cc", PALE, DARK)
    plum_dark = plumage("#6f84a3", MID, BAR, key="plumd")
    plum_fine = plumage("#a9bcd3", PALE, DARK, cell=3, key="plumf")
    claw = tex.bone_mat(IVORY, "#b8a985", glow=0.0)
    beak = tex.bone_mat("#d9d2c0", "#9a8f78")
    bronze = tex.metal(BRONZE, "#d9b77a", "#4a3820", bands=1.5)
    f_prim = feather_mat("#c6d4e6", BAR, "#8a9bb3", bars=4, key="prim")
    f_sec = feather_mat("#cfdbea", "#5a7093", "#9aabc2", bars=3, key="sec")
    f_ter = feather_mat("#d6e1ee", "#7c92b2", "#b0bfd2", bars=2, key="ter")
    f_cov = feather_mat("#a9bcd3", "#7d93b3", "#a9b9cd", bars=0, taper=0.9, notch=0.0, key="cov")
    f_leg = feather_mat("#c9d6e6", "#46597a", "#8a9bb3", bars=3, key="leg")
    f_tail = feather_mat("#d3dfec", BAR, "#8a9bb3", bars=5, key="tail")
    f_crest = feather_mat("#eef4fb", "#7fa3d6", "#c3d2e4", bars=0, taper=0.6, notch=0.0, key="crest")
    f_small = feather_mat("#b4c6db", "#8197b6", "#b6c4d6", bars=0, taper=0.85, notch=0.05, key="small")
    eye = tex.eye_mat(iris="#7fe0ff", sclera="#f2f6ff", pupil="#0d1424", lid=MID, glow=0.95, slit=True,
                      ring="#fff3c4")

    info = {"fw": [], "hw": [], "fan": []}
    root = m.bone("root")
    fly = m.bone("fly", root, pivot=(0, 31, 0))
    body = m.bone("body", fly, pivot=(0, 31, 0))
    body.locator("chest", (0, 27, -8))
    # slender torso: chest, belly, pelvis -- all plumage
    body.box((0, 31, -1), (10, 10.5, 22), plum)
    body.box((0, 29.6, -9.5), (9, 9, 7), plum, variant=1)                 # keel / chest
    body.box((0, 30.6, 10), (9, 8.5, 7), plum, variant=2)                 # pelvis
    body.box((0, 36.6, -2), (6, 1.2, 20), plum_dark)                      # dark dorsal stripe
    # mantle of contour feathers over the back (layered planes, tips backward)
    for i, z in enumerate((-12, -7, -2, 3, 8)):
        body.plane("y", (0, 36.9 + 0.12 * (i % 2), z + 5), 9 - abs(i - 2) * 0.6, 10, f_small, variant=i % 3,
                   density=1.2)
    # flank contour feathers
    for s in (1, -1):
        for i, z in enumerate((-9, -3, 3)):
            body.plane("x", (s * 5.15, 30 - i * 0.4, z + 5), 10, 7, f_small, rot=(0, s * 8, 0),
                       pivot=(s * 5.15, 30, z), variant=(i + 1) % 3, density=1.2)
        body.plane("x", (s * 4.7, 28.5, 15.5), 8, 6, f_small, variant=2, density=1.2)   # thigh drape

    # neck chain authored straight toward -Z; posed into an S by animation
    par = body
    z = -11.0
    for i, (L, w) in enumerate(zip((6, 6, 6, 5), (6.6, 6.0, 5.4, 5.0))):
        nb = m.bone(f"neck{i + 1}", par, pivot=(0, 34, z))
        nb.box((0, 34, z - L / 2), (w, w, L + 1.5), plum_fine, variant=i % 3)
        nb.plane("y", (0, 34 + w / 2 + 0.2, z - L / 2 + 3), w + 1, 7, f_small, variant=i % 3, density=1.2)
        for s in (1, -1):
            nb.plane("x", (s * (w / 2 + 0.15), 33.4, z - L / 2 + 3.5), 7, w * 0.8, f_small, variant=(i + 2) % 3,
                     density=1.2)
        par, z = nb, z - L
    head = m.bone("head", par, pivot=(0, 34, -34))
    head.box((0, 35.5, -38), (6.4, 6.4, 8), plum_fine, variant=1)            # cranium
    head.box((0, 35.0, -46.5), (4.2, 3.6, 9), beak)                          # long narrow snout
    head.box((0, 34.7, -51.6), (3.2, 2.8, 1.6), beak, variant=1)
    head.box((0, 38.0, -40.5), (6.8, 1.0, 4.2), bronze)                      # brow ridge
    head.box((0, 36.6, -45.0), (3.0, 0.8, 9.0), plum_dark)                   # dark culmen stripe
    for s in (1, -1):
        head.plane("x", (s * 3.25, 36.3, -39.6), 3.4, 2.8, eye)
        head.plane("x", (s * 2.15, 32.85, -47.0), 9.0, 1.3, teeth_mat())
        head.plane("x", (s * 3.3, 35.0, -34.5), 6, 4.5, f_small, variant=s % 3, density=1.2)   # ear tufts
    head.locator("mouth", (0, 33.5, -52))
    jaw = m.bone("jaw", head, pivot=(0, 33, -38))
    jaw.box((0, 32.4, -45.0), (3.8, 1.5, 13), beak, variant=2)
    for s in (1, -1):
        jaw.plane("x", (s * 1.95, 33.45, -46.5), 9.5, 0.9, teeth_mat())
    crest = m.bone("crest", head, pivot=(0, 38.5, -37))
    for k, (rx, ry, L) in enumerate(((-28, 0, 13), (-40, 0, 11), (-18, 9, 10), (-18, -9, 10), (-52, 0, 8))):
        cb = m.bone(f"crest{k + 1}", crest, pivot=(0, 38.5, -38 + k * 0.6), rot=(rx, ry, 0))
        cb.plane("x", (0, 38.5, -38 + k * 0.6 + L / 2), L, 3.6, f_crest, variant=k % 3, density=1.5)

    # tail: stiff chain with a frond of paired feathers and a terminal fan
    par = body
    tx, ty, tz = TAIL_START
    for i in range(TAIL_N):
        tb = m.bone(f"tail{i + 1}", par, pivot=(0, ty, tz))
        w = 5.0 - i * 0.45
        tb.box((0, ty, tz + TAIL_L / 2), (w, w * 0.95, TAIL_L + 0.6), plum_fine if i < 3 else plum, variant=i % 3)
        if i >= 2:
            L = 8 + 2.3 * (i - 2)
            for s in (1, -1):
                ang = 40 - 4 * i
                tb.plane("y", (s * 1.2, ty + 0.15 * (i % 2), tz + 2 + L / 2), 4.4, L, f_tail, rot=(0, s * ang, 0),
                         pivot=(s * 1.2, ty, tz + 2), variant=i % 3, density=1.3)
        par, tz = tb, tz + TAIL_L
    fan = m.bone("fan", par, pivot=(0, ty, tz))
    fan.locator("tail_tip", (0, ty, tz + 24))
    for k, (pat, ang, L) in enumerate(FAN):
        for s, sx in (("r", 1), ("l", -1)):
            name = pat.format(s=s)
            if name in m.bones:
                continue
            _feather(m, name, fan, (sx * 0.6 * (k > 0), ty + 0.12 * k, tz - 1), L, 5.2, f_tail, ang, sx, variant=k % 3)
        info["fan"].append((pat, ang))

    # fore wings (arms with individually boned flight feathers)
    for s, sx in (("r", 1), ("l", -1)):
        px, py, pz = SHOULDER
        x = sx * px
        par = body
        covert_rows = [(3, 9, 7.0), (4, 10, 6.4), (3, 10, 6.0)]
        for j, L in enumerate(FW_SEG):
            ab = m.bone(f"wf_{s}_a{j + 1}", par, pivot=(x, py, pz))
            x0 = x if sx > 0 else x - L
            th = 3.4 - 0.5 * j
            ab.cube((x0, py - th / 2, pz - 2.2), (L, th, 4.2 - 0.5 * j), plum_fine, variant=j)
            n, l0, l1, wdt, a0, a1 = FW_ROWS[j]
            mats = [f_ter, f_sec, f_prim][j]
            for k in range(n):
                f = (k + 0.5) / n
                fx = x + sx * L * f
                fl = l0 + (l1 - l0) * f
                ang = a0 + (a1 - a0) * f
                name = f"wf_{s}_f{j + 1}_{k + 1}"
                _feather(m, name, ab, (fx, py - 0.25 - 0.14 * (k % 3), pz + 0.6), fl, wdt, mats, ang, sx, variant=k % 3)
                if s == "r":
                    info["fw"].append((f"wf_{{s}}_f{j + 1}_{k + 1}", j, ang))
            cn, cl, cw = covert_rows[j]
            for k in range(cn):      # covert layer on top (not boned)
                f = (k + 0.5) / cn
                fx = x + sx * L * f
                ang = sx * (a0 + (a1 - a0) * f) * 0.7
                ab.plane("y", (fx, py + 0.55 + 0.1 * (k % 2), pz + cl / 2 - 0.5), cw, cl, f_cov, rot=(0, ang, 0),
                         pivot=(fx, py, pz - 0.5), variant=k % 3, density=1.2)
            if j == 2:                # clawed fingers at the wrist and alula
                for c in range(2):
                    ab.box((x + sx * (1.2 + c * 1.6), py + 0.6, pz - 3.6), (0.9, 0.9, 2.6), claw, rot=(18, sx * 10, 0),
                           pivot=(x + sx * 1.5, py, pz - 2.4))
                ab.plane("y", (x + sx * 2.5, py + 0.9, pz - 2.0), 3.0, 7, f_cov, rot=(0, sx * 150, 0),
                         pivot=(x + sx * 1.0, py, pz - 1.0), variant=2, density=1.2)
            par = ab.name
            x = x + sx * L
        m[par].locator(f"tip_{s}", (x + sx * 14, py, pz + 18))
        for k, (L, wdt, ang) in enumerate(FW_TIPS):
            name = f"wf_{s}_t{k + 1}"
            _feather(m, name, par, (x - sx * 0.4 * k, py - 0.2 - 0.14 * k, pz + 0.4), L, wdt, f_prim, ang, sx, variant=k % 3)
            if s == "r":
                info["fw"].append((f"wf_{{s}}_t{k + 1}", 2, ang))

    # hind wings: legs whose bind pose trails straight back (flight); feathered shin and metatarsus
    for s, sx in (("r", 1), ("l", -1)):
        hx, hy, hz = HIP
        x, z = sx * hx, hz
        par = body
        dims = [(4.4, 5.4), (2.8, 3.0), (1.9, 1.9), (1.3, 1.2)]
        for j, L in enumerate(LEG_SEG):
            lb = m.bone(f"leg_{s}_{j + 1}", par, pivot=(x, hy, z))
            w, h = dims[j]
            if j < 3:
                lb.box((x, hy, z + L / 2), (w, h, L + 0.8), plum if j == 0 else (plum_fine if j == 1 else claw), variant=j)
            else:   # three forward toes + the raised sickle claw (toe II)
                for t_ang in (-22, 0, 22):
                    lb.box((x + sx * math.sin(math.radians(t_ang)) * 2.5, hy, z + 2.5), (1.1, 1.1, 5.0), claw,
                           rot=(0, sx * t_ang, 0), pivot=(x, hy, z))
                    lb.box((x + sx * math.sin(math.radians(t_ang)) * 5.2, hy - 0.3, z + 5.4), (0.7, 0.8, 1.6), bronze,
                           rot=(25, sx * t_ang, 0), pivot=(x, hy, z + 5))
                lb.box((x - sx * 0.9, hy + 1.3, z + 1.2), (0.8, 2.6, 0.9), bronze, rot=(-30, 0, 0), pivot=(x, hy, z))
            if j == 0:   # thigh coverts
                for k in range(3):
                    lb.plane("y", (x + sx * 1.6, hy + 2.8 + 0.1 * k, z + 2 + k * 2.5 + 3), 5.5, 7, f_small,
                             rot=(0, sx * (25 + 10 * k), 0), pivot=(x + sx * 1.6, hy + 2.8, z + 2 + k * 2.5), variant=k)
            if j + 1 in HW_ROWS:
                n, l0, l1, wdt, a0, a1 = HW_ROWS[j + 1]
                for k in range(n):
                    f = (k + 0.5) / n
                    fz = z + L * f
                    name = f"leg_{s}_f{j + 1}_{k + 1}"
                    _feather(m, name, lb, (x + sx * 0.6, hy - 0.2 - 0.13 * (k % 3), fz), l0 + (l1 - l0) * f, wdt, f_leg,
                             a0 + (a1 - a0) * f, sx, variant=k % 3)
                    if s == "r":
                        info["hw"].append((f"leg_{{s}}_f{j + 1}_{k + 1}", j, a0 + (a1 - a0) * f))
            par, z = lb.name, z + L
    return m, info


# ============================================================================ pose algebra
DEFAULT = {"rot": (0, 0, 0), "pos": (0, 0, 0), "scl": (1, 1, 1)}


def _neg(v):
    return -v


def _mirror(ch, v):
    if ch == "rot":
        return (v[0], _neg(v[1]), _neg(v[2]))
    if ch == "pos":
        return (_neg(v[0]), v[1], v[2])
    return tuple(v)


def P(raw):
    """Normalise a raw pose {'@bone': pos, '%bone': scale, 'bone': rot, 'wf_{s}_a1': rot (mirrored),
    'R:x_{s}': right only, 'L:x_{s}': left only (given in right-side terms)} -> {(bone, ch): value}."""
    out = {}
    for k, v in raw.items():
        ch = "rot"
        if k[0] == "@":
            ch, k = "pos", k[1:]
        elif k[0] == "%":
            ch, k = "scl", k[1:]
        only = None
        if k[:2] in ("R:", "L:"):
            only, k = k[0].lower(), k[2:]
        if ch == "scl" and not isinstance(v, (tuple, list)):
            v = (v, v, v)
        if "{s}" in k:
            for s in ("r", "l"):
                if only and s != only:
                    continue
                out[(k.format(s=s), ch)] = _mirror(ch, v) if s == "l" else tuple(v)
        else:
            out[(k, ch)] = tuple(v)
    return out


def merge(*ps):
    out = {}
    for p in ps:
        out.update(p)
    return out


def side_only(raw, side):
    return {(f"{side}:{k}" if "{s}" in k and k[0] not in "@%" else k): v for k, v in raw.items()}


def flip(p):
    """Mirror a normalised pose left<->right (bank right -> bank left)."""
    out = {}
    for (b, ch), v in p.items():
        if b.count("_r_") or b.endswith("_r") or (b.startswith("fan_r")):
            nb = b.replace("_r_", "_l_") if "_r_" in b else (b[:-2] + "_l" if b.endswith("_r") else b.replace("fan_r", "fan_l"))
            out[(nb, ch)] = v
        elif b.count("_l_") or b.endswith("_l") or b.startswith("fan_l"):
            nb = b.replace("_l_", "_r_") if "_l_" in b else (b[:-2] + "_r" if b.endswith("_l") else b.replace("fan_l", "fan_r"))
            out[(nb, ch)] = v
        else:
            out[(b, ch)] = _mirror(ch, v) if ch != "scl" else v
    return out


def keys(a, tp, smooth=True):
    """Write keyframes {time: normalised pose} into an Anim (missing bones use bind values)."""
    allk = set()
    for p in tp.values():
        allk |= set(p)
    for (bone, ch) in sorted(allk):
        kv = {t: p.get((bone, ch), DEFAULT[ch]) for t, p in tp.items()}
        vals = list(kv.values())
        fn = getattr(a, ch)
        if all(v == vals[0] for v in vals):
            if vals[0] != DEFAULT[ch]:
                fn(bone, vals[0])
        else:
            fn(bone, kv, smooth)
    return a


class Poser:
    def __init__(self, info):
        self.info = info

    def fw(self, a1, a2, a3, fan=1.0, fold=0.0, twist=0.0, spread=1.5):
        """Fore-wing pose (right-side terms).  fold 0..1 lays feathers parallel, pointing backward."""
        raw = {"wf_{s}_a1": a1, "wf_{s}_a2": a2, "wf_{s}_a3": a3}
        cum = [a1[1], a1[1] + a2[1], a1[1] + a2[1] + a3[1]]
        for k, (pat, seg, ang) in enumerate(self.info["fw"]):
            d_fold = -(cum[seg] + ang) + k * spread * 0.4
            d_fan = max(min((fan - 1) * ang, 100 - ang), -ang)
            raw[pat] = (twist * (seg + 1) / 3, fold * d_fold + (1 - fold) * d_fan, 0)
        return raw

    def hw(self, l1, l2, l3, l4, fan=1.0, fold=0.0, twist=0.0, perch=True):
        """Hind-wing pose.  fold with perch=True swings the leg feathers to trail backward as vertical
        'trousers' behind a standing leg; perch=False lays them along the trailing leg."""
        raw = {"leg_{s}_1": l1, "leg_{s}_2": l2, "leg_{s}_3": l3, "leg_{s}_4": l4}
        for k, (pat, seg, ang) in enumerate(self.info["hw"]):
            d_fan = max(min((fan - 1) * ang, 105 - ang), -ang)
            if perch:
                rxf = (-40 if seg == 1 else -82) + 5 * (k % 4)
                raw[pat] = (fold * rxf + twist, fold * (80 - ang) + (1 - fold) * d_fan, 0)
            else:
                raw[pat] = (twist, fold * (-ang + 4 + 2 * (k % 4)) + (1 - fold) * d_fan, 0)
        return raw

    def tail(self, rx=(0,) * 7, ry=(0,) * 7, fan=1.0, fan_rx=0.0, fan_rz=0.0):
        raw = {f"tail{i + 1}": (rx[i], ry[i], 0) for i in range(TAIL_N)}
        raw["fan"] = (fan_rx, 0, fan_rz)
        for pat, ang in self.info["fan"]:
            if ang:
                raw[pat] = (0, (fan - 1) * ang, 0)
        return raw

    @staticmethod
    def neck(n1, n2, n3, n4, head, jaw=0.0, crest=0.0, ry=0.0, rz=0.0):
        return {"neck1": (n1, ry * 0.2, rz * 0.2), "neck2": (n2, ry * 0.2, rz * 0.2), "neck3": (n3, ry * 0.25, rz * 0.25),
                "neck4": (n4, ry * 0.15, rz * 0.15), "head": (head, ry * 0.2, rz * 0.2), "jaw": (jaw, 0, 0),
                "crest": (crest, 0, 0)}


def build_poses(info):
    q = Poser(info)
    Z = {}
    flight = {"@root": (0, FLY_DY, 0)}
    Z["glide"] = P({**flight, **q.neck(12, 2, -6, -6, -2),
                    **q.fw((0, 0, 6), (0, 0, -2), (0, 2, -3)),
                    **q.hw((8, 18, 0), (0, 4, 0), (-4, 2, 0), (10, 0, 0)),
                    **q.tail(fan=1.0)})
    Z["perch"] = P({"@root": (0, 0, 0), **q.neck(40, 10, -14, -18, -18),
                    **q.fw((0, -78, -62), (0, 160, 0), (0, -158, 0), fold=1.0),
                    **q.hw((120, 0, 0), (-60, 0, 0), (35, 0, 0), (85, 0, 0), fold=1.0),
                    **q.tail((-10, -2, 2, 3, 3, 2, 2), fan=0.35)})
    # flap keys (move): up / down / mid-upstroke (wing partly folded on the recovery)
    Z["flap_up"] = merge(Z["glide"], P({"@fly": (0, -1.6, 0), **q.fw((0, 10, 40), (0, 0, 8), (0, 0, -4), fan=1.0),
                                        **q.hw((10, 16, 0), (0, 2, 0), (-4, 0, 0), (10, 0, 0)),
                                        **q.tail(rx=(2, 0, 0, 0, 0, 0, 0)), **q.neck(14, 2, -6, -8, -2)}))
    Z["flap_down"] = merge(Z["glide"], P({"@fly": (0, 2.2, 0), **q.fw((0, -4, -30), (0, 0, -10), (0, 0, -14), fan=1.12, twist=8),
                                          **q.hw((14, 22, 0), (0, 4, 0), (-2, 4, 0), (10, 0, 0), fan=1.1),
                                          **q.tail(rx=(-3, 0, 0, 0, 0, 0, 0), fan=1.1), **q.neck(10, 2, -6, -4, -2)}))
    Z["flap_mid"] = merge(Z["glide"], P({"@fly": (0, 0.6, 0), **q.fw((0, -22, 10), (0, 26, -14), (0, -38, -10), fan=0.6),
                                         **q.hw((12, 18, 0), (0, 3, 0), (-3, 2, 0), (10, 0, 0))}))
    bank_r = merge(Z["glide"], P({"fly": (4, -6, -38), **q.neck(12, 2, -6, -6, -2, ry=-30, rz=40),
                                  **side_only(q.fw((6, -8, 2), (0, -4, -4), (0, -6, -6), fan=0.9, twist=6), "R"),
                                  **side_only(q.fw((-4, 6, 12), (0, 2, 0), (0, 4, 0), fan=1.12), "L"),
                                  **side_only(q.hw((24, 10, 0), (6, 0, 0), (0, 0, 0), (10, 0, 0), fan=0.85), "R"),
                                  **side_only(q.hw((2, 28, 0), (0, 6, 0), (-4, 4, 0), (10, 0, 0), fan=1.15), "L"),
                                  **q.tail(ry=(-4, -3, -3, -2, -2, -1, -1), fan=1.15, fan_rz=18)}))
    Z["bank_r"] = bank_r
    Z["bank_l"] = flip(bank_r)
    Z["stoop"] = P({**flight, "fly": (-40, 0, 0), **q.neck(4, 0, 0, 0, 8, crest=10),
                    **q.fw((0, -64, -16), (0, 118, 0), (0, -114, 0), fold=0.9),
                    **q.hw((-6, 3, 0), (0, 0, 0), (0, 0, 0), (-20, 0, 0), fan=0.25),
                    **q.tail(rx=(4, 0, 0, 0, 0, 0, 0), fan=0.15)})
    Z["flare"] = P({**flight, "fly": (48, 0, 0), **q.neck(-8, -10, -10, -10, -12, jaw=-12, crest=-14),
                    **q.fw((0, 24, 18), (0, -6, 0), (0, 10, 6), fan=1.25, twist=-14),
                    **q.hw((128, 22, 0), (-30, 4, 0), (10, 0, 0), (60, 0, 0), fan=1.2),
                    **q.tail(rx=(16, 10, 6, 0, 0, 0, 0), fan=1.4, fan_rx=12)})
    Z["power"] = P({**flight, "fly": (-6, 0, 0), **q.neck(18, 4, -8, -8, -10, jaw=-30, crest=-24),
                    **q.fw((0, 6, 16), (0, 0, 2), (0, 4, 4), fan=1.3),
                    **q.hw((6, 32, 0), (0, 6, 0), (0, 4, 0), (12, 0, 0), fan=1.3),
                    **q.tail(rx=(-6, 0, 0, 0, 0, 0, 0), fan=1.5)})
    Z["hover"] = P({**flight, "fly": (30, 0, 0), **q.neck(-2, -6, -6, -8, -8),
                    **q.fw((0, 8, 20), (0, 0, 4), (0, 4, 0), fan=1.1),
                    **q.hw((110, 14, 0), (-40, 0, 0), (20, 0, 0), (70, 0, 0), fan=0.9),
                    **q.tail(rx=(14, 6, 2, 0, 0, 0, 0), fan=1.2)})
    Z["tuck"] = P({**flight, "fly": (-30, 0, 0), **q.neck(6, 0, 0, 0, 6, crest=12),
                   **q.fw((0, -66, -22), (0, 130, 0), (0, -128, 0), fold=1.0),
                   **q.hw((-4, 2, 0), (0, 0, 0), (0, 0, 0), (-20, 0, 0), fold=0.8, perch=False),
                   **q.tail(fan=0.1)})
    Z["rest"] = merge(Z["perch"], P({"@root": (0, -3.5, 0), "fly": (6, 0, 0), **q.neck(14, 4, -2, -6, 22, crest=14),
                                     **q.fw((0, -80, -66), (0, 160, 0), (0, -158, 0), fold=1.0, spread=3.0),
                                     **q.hw((128, 0, 0), (-74, 0, 0), (48, 0, 0), (84, 0, 0), fold=1.0),
                                     **q.tail((8, 6, 4, 3, 2, 1, 0), fan=0.6)}))
    Z["_q"] = q
    return Z


# ============================================================================ animations
def _flip_roll(a, t0, t1, ease=True, amp=360):
    """Linear barrel roll on 'fly' rz from t0..t1 that wraps at 180 so blends never unwind."""
    d = t1 - t0
    sgn = 1 if amp > 0 else -1
    k = {0.0: (0, 0, 0), t0: (0, 0, 0), t0 + d * 0.18: (0, 0, sgn * 40), t0 + d * 0.5: (0, 0, sgn * 180),
         t0 + d * 0.5 + 0.0005: (0, 0, -sgn * 180), t0 + d * 0.82: (0, 0, -sgn * 40), t1: (0, 0, 0)}
    return k


def build_anims(info):
    Z = build_poses(info)
    q = Z["_q"]
    A = []
    fw_feathers = [p.format(s=s) for p, _, _ in info["fw"] for s in "rl"]
    tips = [f for f in fw_feathers if "_t" in f or "_f3_" in f]
    hw_feathers = [p.format(s=s) for p, _, _ in info["hw"] for s in "rl"]
    fan_bones = sorted({p.format(s=s) for p, _ in info["fan"] for s in "rl"})

    # ---- always: breathing and feather life
    breathe = Anim("breathe", loop=True)
    breathe.scl("body", (LIFE(0.025, 2.2, base=1.0), LIFE(0.03, 2.2, base=1.0), 1.0))
    breathe.rot("neck1", (LIFE(1.2, 2.2, 0.2), 0, 0))
    breathe.rot("crest", (LIFE(4, 3.1), LIFE(2, 4.3), 0))
    A.append(breathe)
    life = Anim("life", loop=True)
    flutter(life, tips, amp=1.4, period=1.3, spread=0.11)
    flutter(life, hw_feathers, amp=1.2, period=1.7, spread=0.17)
    for i, f in enumerate(fan_bones):
        life.rot(f, (S(1.5, 1.1, i * 0.13, clock="q.life_time"), S(1.2, 1.5, i * 0.2, clock="q.life_time"), 0))
    wave(life, [f"tail{i + 1}" for i in range(2, TAIL_N)], 1, 0.6, 3.4, lag=0.12, clock="q.life_time")
    A.append(life)

    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    # ---- perched idle: raptor head snaps, tail counterbalance, a wing rouse
    idle = Anim("idle", length=6.0, loop=True)
    perch = Z["perch"]
    keys(idle, {0: perch})
    idle.rot("head", {0: (-18, 0, 0), 0.9: (-18, 0, 0), 1.0: (-20, 26, 4), 2.2: (-20, 26, 4), 2.3: (-14, -22, -6),
                      3.4: (-14, -22, -6), 3.5: (-24, 4, 0), 4.6: (-24, 4, 0), 4.7: (-16, 12, 10), 5.6: (-16, 12, 10),
                      6.0: (-18, 0, 0)}, smooth=False)
    idle.rot("neck4", {0: (-18, 0, 0), 2.3: (-18, 0, 0), 2.6: (-12, -6, 0), 3.4: (-12, -6, 0), 3.7: (-18, 0, 0), 6.0: (-18, 0, 0)})
    idle.rot("tail1", {0: (-10, 0, 0), 1.5: (-12, 4, 0), 3.0: (-9, -3, 0), 4.5: (-11, 3, 0), 6.0: (-10, 0, 0)})
    fold = q.fw((0, -78, -62), (0, 160, 0), (0, -158, 0), fold=1.0)
    rouse = q.fw((0, -70, -50), (0, 150, 0), (0, -150, 0), fold=0.9)
    for b in ("wf_{s}_a1", "wf_{s}_a2", "wf_{s}_a3"):
        sym(idle, b, rot={0: fold[b], 4.8: fold[b], 5.1: rouse[b], 5.4: fold[b], 6.0: fold[b]})
    idle.pos("body", {0: (0, 0, 0), 4.8: (0, 0, 0), 5.0: (0, 0.6, 0), 5.3: (0, -0.3, 0), 5.6: (0, 0, 0), 6.0: (0, 0, 0)})
    A.append(idle)

    # ---- move: the four-surface flap cycle (forewings drive, hindwings stabilise in counter-phase)
    move = Anim("move", length=0.8, loop=True)
    keys(move, {0: Z["flap_up"], 0.36: Z["flap_down"], 0.6: Z["flap_mid"], 0.8: Z["flap_up"]})
    move.sound(0.22, "flap")
    A.append(move)

    glide = Anim("glide", length=2.6, loop=True)
    keys(glide, {0: Z["glide"]})
    glide.pos("fly", (0, LIFE(1.2, 2.6), 0))
    glide.rot("fly", (LIFE(2.0, 2.6, 0.25), 0, LIFE(3.0, 3.9)))
    for b in ("wf_{s}_a1", "wf_{s}_a3"):
        base = Z["glide"][(b.format(s="r"), "rot")]
        sym(glide, b, rot=(base[0], base[1], LIFE(2.5, 2.6, 0.1, base=base[2])))
    glide.particle(0.1, "trail", locator="tip_r")
    glide.particle(0.1, "trail", locator="tip_l")
    A.append(glide)

    for nm, key in (("turn_r", "bank_r"), ("turn_l", "bank_l")):
        b = Anim(nm, length=1.6, loop=True)
        keys(b, {0: Z[key]})
        b.pos("fly", (0, LIFE(0.8, 1.6), 0))
        b.particle(0.0, "trail", locator="tip_r")
        b.particle(0.0, "trail", locator="tip_l")
        A.append(b)

    roll = Anim("roll", length=1.0, loop="hold")      # tucks, rolls through 360, re-spreads
    keys(roll, {0: Z["glide"], 0.3: merge(Z["glide"], P(q.fw((0, -30, 4), (0, 50, 0), (0, -60, 0), fan=0.5))),
                0.7: merge(Z["glide"], P(q.fw((0, -30, 4), (0, 50, 0), (0, -60, 0), fan=0.5))), 1.0: Z["glide"]})
    roll.rot("fly", _flip_roll(roll, 0.08, 0.92), smooth=False)
    roll.sound(0.1, "rattle")
    A.append(roll)

    stoop = Anim("stoop", length=0.45, loop="hold")
    keys(stoop, {0: Z["power"], 0.25: Z["tuck"], 0.45: Z["stoop"]})
    stoop.sound(0.05, "rattle")
    A.append(stoop)

    flare = Anim("flare", length=0.5, loop="hold")
    keys(flare, {0: Z["stoop"], 0.22: merge(Z["flare"], P({"fly": (30, 0, 0)})), 0.5: Z["flare"]})
    flare.sound(0.05, "flare")
    A.append(flare)

    land = Anim("land", length=1.0, loop="hold")
    beat = merge(Z["flare"], P(q.fw((0, 14, -26), (0, 0, -8), (0, 0, -10), fan=1.2)))
    touch = merge(Z["perch"], P({"@root": (0, -3, 0), "fly": (10, 0, 0), **q.fw((0, -10, 30), (0, 20, -10), (0, -30, -8), fan=0.8)}))
    keys(land, {0: Z["flare"], 0.25: beat, 0.5: merge(Z["hover"], P({"@root": (0, -12, 0)})), 0.72: touch, 1.0: Z["perch"]})
    land.sound(0.68, "land")
    A.append(land)

    flut = Anim("flutter", length=0.4, loop=True)
    hv_up = merge(Z["hover"], P(q.fw((0, 12, 34), (0, 0, 6), (0, 4, 0), fan=1.0)))
    hv_dn = merge(Z["hover"], P({"@fly": (0, 1.5, 0), **q.fw((0, 18, -18), (0, 0, -8), (0, 0, -10), fan=1.15)}))
    keys(flut, {0: hv_up, 0.18: hv_dn, 0.4: hv_up})
    flut.sound(0.12, "flap")
    A.append(flut)

    # ---- attacks (both end in the glide pose so scripts can keep flying)
    atk_a = Anim("attack_a", length=0.7, loop="hold")      # wing slash: raise, whip down-forward, recover
    wind_up = merge(Z["glide"], P({"fly": (-6, 0, 8), **q.neck(18, 4, -8, -8, -6, jaw=-10, crest=-12),
                                   **q.fw((0, 18, 54), (0, -6, 10), (0, 8, 6), fan=0.9),
                                   **q.hw((-2, 26, 0), (0, 4, 0), (0, 0, 0), (0, 0, 0))}))
    strike = merge(Z["glide"], P({"fly": (8, 0, -10), **q.neck(6, 0, -4, -2, 4, jaw=-26),
                                  **q.fw((0, -14, -34), (0, -4, -14), (0, -10, -16), fan=1.2, twist=10),
                                  **q.hw((20, 30, 0), (6, 6, 0), (0, 0, 0), (20, 0, 0), fan=1.2)}))
    keys(atk_a, {0: Z["glide"], 0.16: wind_up, 0.3: strike, 0.45: strike, 0.7: Z["glide"]})
    atk_a.sound(0.18, "slash")
    A.append(atk_a)

    atk_b = Anim("attack_b", length=0.8, loop="hold")      # talon rake: legs swing forward, jaws snap
    rake0 = merge(Z["glide"], P({"fly": (14, 0, 0), **q.neck(4, -4, -6, -6, -6, jaw=-6, crest=-16),
                                 **q.fw((0, 12, 30), (0, 0, 4), (0, 4, 0), fan=1.1),
                                 **q.hw((70, 20, 0), (-30, 0, 0), (10, 0, 0), (40, 0, 0), fan=1.1)}))
    rake1 = merge(Z["glide"], P({"fly": (26, 0, 0), **q.neck(-6, -6, -8, -8, -10, jaw=-34, crest=-20),
                                 **q.fw((0, 4, -20), (0, 0, -8), (0, 0, -10), fan=1.2),
                                 **q.hw((150, 16, 0), (-20, 0, 0), (0, 0, 0), (90, 0, 0), fan=1.25)}))
    keys(atk_b, {0: Z["glide"], 0.2: rake0, 0.35: rake1, 0.5: rake1, 0.8: Z["glide"]})
    atk_b.sound(0.12, "shriek")
    A.append(atk_b)

    power = Anim("power", length=0.9, loop="hold")       # every surface fully extended, shriek
    keys(power, {0: Z["glide"], 0.35: merge(Z["power"], P(q.fw((0, -6, 34), (0, 0, 8), (0, 4, 6), fan=1.1))),
                 0.9: Z["power"]})
    power.sound(0.2, "shriek")
    A.append(power)

    react = Anim("react", length=0.6, loop="hold")
    jolt = merge(Z["glide"], P({"fly": (-14, 8, 22), **q.neck(-10, -8, -6, -4, 20, jaw=-18, crest=-26),
                                **q.fw((0, -20, 30), (0, 30, -16), (0, -40, -10), fan=0.6),
                                **q.hw((30, 30, 0), (-10, 0, 0), (0, 0, 0), (20, 0, 0), fan=1.3)}))
    keys(react, {0: Z["glide"], 0.1: jolt, 0.3: merge(Z["glide"], P({"fly": (4, -3, -8)})), 0.6: Z["glide"]})
    react.scl(fw_feathers[:6], {0: 1.0, 0.1: 1.12, 0.6: 1.0})
    react.sound(0.02, "chirr")
    A.append(react)

    rest = Anim("rest", length=4.0, loop=True)
    keys(rest, {0: Z["rest"]})
    rest.rot("head", (LIFE(2.5, 4.0, base=22), LIFE(4, 7.0), 0))
    rest.scl("body", (LIFE(0.03, 4.0, base=1.06), LIFE(0.04, 4.0, base=1.08), 1.03))   # fluffed plumage
    A.append(rest)

    # ---- arrive: emerges from the cloud gap furled, rolls gracefully and unfurls four surfaces
    arrive = Anim("arrive", length=2.4, loop="hold")
    half_fw = merge(Z["tuck"], P(q.fw((0, -20, 10), (0, 30, 0), (0, -40, 0), fan=0.5)))
    open_fw = merge(Z["tuck"], P({"fly": (-18, 0, 0), **q.fw((0, 0, 24), (0, 0, 0), (0, 0, 0), fan=1.0)}))
    open_hw = merge(open_fw, P({"fly": (-10, 0, 0), **q.hw((8, 22, 0), (0, 4, 0), (-4, 2, 0), (10, 0, 0), fan=1.1)}))
    full = merge(Z["power"], P({"fly": (-4, 0, 0)}))
    keys(arrive, {0: Z["tuck"], 0.55: Z["tuck"], 0.9: half_fw, 1.2: open_fw, 1.45: open_hw, 1.75: full,
                  2.0: merge(Z["flap_down"], P({"fly": (0, 0, 0)})), 2.4: Z["glide"]})
    arrive.rot("fly", {0: (-30, 0, 0), 0.55: (-30, 0, 0), 0.65: (-30, 0, 40), 0.95: (-26, 0, 180), 0.9505: (-26, 0, -180),
                       1.3: (-16, 0, -50), 1.6: (-8, 0, 0), 2.0: (0, 0, 0), 2.4: (0, 0, 0)}, smooth=False)
    arrive.scl("root", {0: 0.15, 0.4: 1.05, 0.55: 1.0, 2.4: 1.0})
    arrive.sound(0.05, "whistle")
    arrive.sound(1.7, "call")
    A.append(arrive)

    # ---- depart: rises with wings high and dissolves into drifting feathers and wind
    depart = Anim("depart", length=1.6, loop="hold")
    lift = merge(Z["perch"], P({"@root": (0, 2, 0), **q.neck(30, 6, -16, -14, -22, jaw=-22, crest=-24),
                                **q.fw((0, 10, 62), (0, 0, 10), (0, 4, 6), fan=1.2),
                                **q.tail((-14, -2, 0, 0, 0, 0, 0), fan=1.4)}))
    keys(depart, {0: Z["perch"], 0.4: lift, 1.6: merge(lift, P({"@root": (0, 10, 0)}))})
    groups = [[f for f in fw_feathers if "_t" in f], [f for f in fw_feathers if "_f3_" in f],
              [f for f in fw_feathers if "_f2_" in f] + fan_bones, [f for f in fw_feathers if "_f1_" in f] + hw_feathers,
              ["crest", "tail5", "tail6", "tail7"]]
    for g, bones in enumerate(groups):
        t0 = 0.45 + g * 0.16
        depart.scl(bones, {0: 1.0, t0: 1.0, t0 + 0.12: 1.15, t0 + 0.4: 0.0})
    depart.scl("fly", {0: 1.0, 1.0: 1.0, 1.25: (1.08, 0.9, 1.08), 1.6: 0.0})
    depart.pos("fly", {0: (0, 0, 0), 1.0: (0, 2, 0), 1.6: (0, 14, 0)})
    depart.sound(0.1, "shriek")
    A.append(depart)
    return A


STATES = {0: ["hidden"], 1: ["arrive"], 2: ["idle"], 3: ["move"], 4: ["glide"], 5: ["turn_l"], 6: ["turn_r"],
          7: ["roll"], 8: ["stoop"], 9: ["flare"], 10: ["land"], 11: ["attack_a"], 12: ["attack_b"],
          13: ["power"], 14: ["react"], 15: ["rest"], 16: ["depart"], 17: ["flutter"]}
STATE_IDS = {v[0]: k for k, v in STATES.items()}
ALWAYS = ["breathe", "life"]


# ============================================================================ constructs
def cloud_model():
    """Cloud bank, ~11 blocks wide at size 1: two halves that part along X."""
    m = Model("ed_air_cloud", density=0.5, bounds=(30, 10, (0, 1, 0)))
    root = m.bone("root")
    cm = [cloud_mat("#f6f9ff", "#aab9d0"), cloud_mat("#eef3fb", "#9aaac4", a=0.72, key="edcl2")]
    rng = np.random.default_rng(404)
    for s, sx in (("r", 1), ("l", -1)):
        h = m.bone(f"half_{s}", root, pivot=(0, 0, 0))
        for k in range(9):
            x = sx * (10 + rng.uniform(0, 70))
            z = rng.uniform(-40, 40)
            y = rng.uniform(-6, 8) - abs(x) * 0.05
            w = rng.uniform(26, 46) * (1.15 - abs(x) / 160)
            pb = m.bone(f"puff_{s}{k + 1}", h, pivot=(x, y, z))
            pb.box((x, y, z), (w, w * 0.55, w * 0.9), cm[k % 2], variant=k % 3)
    shaft = m.bone("shafts", root, pivot=(0, 0, 0))
    sm = tex.vgrad("#f4fbff", "#bfe9ff", var=0, a=0.38, mode="blend", edge_dark=0)
    for k in range(3):
        shaft.plane("z", (0, -60, 0), 14 - k * 3, 120, sm, rot=(0, k * 60, 0), pivot=(0, -60, 0))
    return m


def cloud_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    churn = Anim("churn", loop=True)
    for s in "rl":
        for k in range(9):
            churn.pos(f"puff_{s}{k + 1}", (LIFE(2.0, 3.0 + k * 0.4, k * 0.1), LIFE(1.5, 2.4 + k * 0.3, k * 0.17), 0))
            churn.scl(f"puff_{s}{k + 1}", LIFE(0.05, 2.8 + k * 0.2, k * 0.13, base=1.0))
    form = Anim("form", length=0.8, loop="hold")
    for s in "rl":
        for k in range(9):
            t0 = 0.04 * k
            form.scl(f"puff_{s}{k + 1}", {0: 0.0, t0: 0.0, t0 + 0.4: 1.1, 0.8: 1.0})
    form.scl("shafts", 0.0)
    part = Anim("part", length=1.2, loop="hold")      # halves slide apart, light shafts pour through
    sym(part, "half_{s}", pos={0: (0, 0, 0), 0.25: (-4, 0, 0), 1.2: (52, 6, 0)}, rot={0: (0, 0, 0), 1.2: (0, -10, 6)})
    part.scl("shafts", {0: (0.0, 1.0, 0.0), 0.4: (0.3, 1.0, 0.3), 1.2: (1.0, 1.0, 1.0)})
    fade = Anim("fade", length=1.0, loop="hold")
    sym(fade, "half_{s}", pos={0: (52, 6, 0), 1.0: (90, 18, 0)}, rot=(0, -10, 6), scl={0: 1.0, 1.0: 0.0})
    fade.scl("shafts", {0: 1.0, 0.5: 0.0})
    return [hidden, churn, form, part, fade]


def ribbon_model():
    """Air-current ribbon segment: ~4.5 blocks long (model Z), twisted translucent strip with
    travelling glow streaks.  Front (-Z) is the direction the dragon flew."""
    m = Model("ed_air_ribbon", density=1.0, bounds=(8, 4, (0, 0, 0)))
    root = m.bone("root")
    cur = current_mat("#e9fbff", "#7fd6ff", a=0.55)
    cur2 = current_mat("#ffffff", "#a8c6ff", a=0.4, key="edcur2")
    streak = tex.glow_flat("#d8f6ff", 1.0, core="#ffffff")
    chevron = tex.bitmap_cut(["#   #", " # # ", "  #  "], "#e8fbff", glow=1.0, color2="#9fe8ff")
    n, seg = 6, 12.0
    for i in range(n):
        z0 = 36 - seg * (i + 1)                     # r1 at the back (+Z) ... r6 at the front
        rb = m.bone(f"r{i + 1}", root, pivot=(0, 0, z0 + seg), rot=(0, 0, i * 28))
        rb.plane("y", (0, 0, z0 + seg / 2), 30, seg + 0.6, cur, variant=i % 3)
        rb.plane("y", (0, 0.4, z0 + seg / 2), 16, seg + 0.6, cur2, rot=(0, 0, 55), pivot=(0, 0, z0 + seg / 2), variant=(i + 1) % 3)
        sb = m.bone(f"s{i + 1}", rb, pivot=(0, 0, z0 + seg))
        for k, x in enumerate((-12, -4, 7, 13)):
            sb.plane("y", (x, 0.3 + 0.1 * k, z0 + seg / 2), 0.8, seg * (0.5 + 0.12 * k), streak)
        if i % 2 == 0:
            sb.plane("y", (0, 0.5, z0 + seg / 2), 5, 3, chevron)
    return m


def ribbon_anims():
    n = 6
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    flow = Anim("flow", length=0.6, loop=True)
    for i in range(n):
        flow.pos(f"s{i + 1}", {0: (0, 0, 6), 0.6: (0, 0, -6)}, smooth=False)
        flow.scl(f"s{i + 1}", {0: (1, 1, 0.2), 0.12: (1, 1, 1), 0.48: (1, 1, 1), 0.6: (1, 1, 0.2)}, smooth=False)
    twist = Anim("twist", loop=True)
    for i in range(n):
        twist.rot(f"r{i + 1}", (0, LIFE(3, 2.2, i * 0.12), M(f"q.life_time*{90 + i * 12}", lambda t, i=i: t * (90 + i * 12))))
        twist.pos(f"r{i + 1}", (0, LIFE(2.0, 1.8, i * 0.15), 0))
    draw = Anim("draw", length=0.5, loop="hold")     # unrolls from the back to the front
    for i in range(n):
        t0 = 0.06 * i
        draw.scl(f"r{i + 1}", {0: (0.0, 1, 0.0), t0: (0.0, 1, 0.0), t0 + 0.14: (1.35, 1, 1.0), t0 + 0.26: (1.0, 1, 1.0)})
    hold = Anim("hold", loop=True)
    fray = Anim("fray", length=0.8, loop="hold")     # frays apart and lifts away
    for i in range(n):
        t0 = 0.05 * i
        fray.scl(f"r{i + 1}", {0: 1.0, t0: 1.0, t0 + 0.3: (1.6, 1, 0.7), t0 + 0.5: (0.0, 1, 0.0)})
        fray.pos(f"r{i + 1}", {0: (0, 0, 0), 0.8: ((i - 2.5) * 3, 10 + i * 2, 0)})
    return [hidden, flow, twist, draw, hold, fray]


def vortex_model():
    """Localized wind vortex: a funnel of five counter-spinning current rings, a core, and orbiting feathers.
    ~5.5 blocks tall, ~3 blocks top radius at size 1."""
    m = Model("ed_air_vortex", density=1.0, bounds=(10, 8, (0, 3, 0)))
    root = m.bone("root")
    wind = current_mat("#f2fcff", "#8fd8ff", a=0.5, key="edvx")
    streak = tex.glow_flat("#cdf3ff", 1.0, core="#ffffff")
    for i in range(5):
        y = 6 + i * 14
        r = 10 + i * 7.5
        vb = m.bone(f"v{i + 1}", root, pivot=(0, y, 0), rot=(0, i * 23, (i % 2) * 6 - 3))
        ring(vb, (0, y, 0), r, 10, (2 * math.pi * r / 10 + 1.5, 0, 7 + i), wind, axis="y")
        cb = m.bone(f"c{i + 1}", vb, pivot=(0, y, 0))
        ring(cb, (0, y + 2.5, 0), r + 0.6, 8, (2 * math.pi * r / 16, 0.6, 0.6), streak, axis="y", sweep=180)
        ring(cb, (0, y - 2.5, 0), r + 0.6, 6, (2 * math.pi * r / 16, 0.6, 0.6), streak, axis="y", start=180, sweep=150)
    core = m.bone("core", root, pivot=(0, 0, 0))
    cm = current_mat("#ffffff", "#bff3ff", a=0.42, key="edvxc")
    for k in range(3):
        core.plane("z", (0, 34, 0), 9 - k * 2, 68, cm, rot=(0, k * 60, 0), pivot=(0, 34, 0), variant=k)
    orbit = m.bone("orbit", root, pivot=(0, 0, 0))
    fm = feather_mat("#e6eef7", DARK, "#8a9bb3", bars=3, key="vxf")
    for k in range(6):
        a = k * 60
        x, z = math.cos(math.radians(a)) * 20, math.sin(math.radians(a)) * 20
        orbit.plane("y", (x, 18 + k * 7, z + 3), 3.5, 9, fm, rot=(0, -a, 0), pivot=(x, 18 + k * 7, z), variant=k % 3)
    return m


def vortex_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    spin = Anim("spin", loop=True)
    for i in range(5):
        rate = (520 - i * 60) * (1 if i % 2 == 0 else -0.8)
        spin.rot(f"v{i + 1}", (LIFE(4, 1.3, i * 0.2), M(f"q.life_time*{rate:.0f}", lambda t, r=rate: t * r), 0))
    spin.rot("core", (0, M("q.life_time*-300", lambda t: -300 * t), 0))
    spin.rot("orbit", (0, M("q.life_time*420", lambda t: 420 * t), 0))
    spin.scl("core", (LIFE(0.12, 0.4, base=1.0), 1.0, LIFE(0.12, 0.4, base=1.0)))
    form = Anim("form", length=0.6, loop="hold")       # spins up bottom to top
    for i in range(5):
        t0 = 0.07 * i
        form.scl(f"v{i + 1}", {0: 0.0, t0: 0.0, t0 + 0.22: 1.2, t0 + 0.32: 1.0})
    form.scl("core", {0: (0.0, 0.0, 0.0), 0.4: (1.0, 1.0, 1.0)})
    form.scl("orbit", {0: 0.0, 0.3: 0.0, 0.6: 1.0})
    hold = Anim("hold", loop=True)
    hold.pos("root", (LIFE(1.2, 0.9), 0, LIFE(1.2, 1.1, 0.3)))
    burst = Anim("burst", length=0.6, loop="hold")      # flings outward and up, then gone
    for i in range(5):
        burst.scl(f"v{i + 1}", {0: 1.0, 0.25: 1.7 + i * 0.1, 0.6: 0.0})
        burst.pos(f"v{i + 1}", {0: (0, 0, 0), 0.6: (0, 12 + i * 5, 0)})
    burst.scl("core", {0: 1.0, 0.2: (0.4, 1.4, 0.4), 0.45: 0.0})
    burst.scl("orbit", {0: 1.0, 0.3: 1.8, 0.6: 0.0})
    return [hidden, spin, form, hold, burst]


def shock_model():
    """Sonic shockwave: a vertical ring standing across the dive route (front -Z = route direction),
    a ground ripple and swept-back pressure streaks.  Radius ~1.2 blocks at size 1 before it blasts."""
    m = Model("ed_air_shock", density=1.0, bounds=(14, 10, (0, 2, 0)))
    root = m.bone("root")
    glow = tex.glow_flat("#e8fbff", 1.0, core="#ffffff")
    band = tex.vgrad("#ffffff", "#9fe0ff", var=0, a=0.45, mode="blend", edge_dark=0)
    hoop = m.bone("hoop", root, pivot=(0, 20, 0))
    ring(hoop, (0, 20, 0), 18, 16, (7.4, 1.0, 1.0), glow, axis="z")
    hb = m.bone("hoop_band", hoop, pivot=(0, 20, 0))
    ring(hb, (0, 20, 0), 15.5, 16, (6.3, 4.0, 0), band, axis="z")
    ground = m.bone("ground", root, pivot=(0, 0.3, 0))
    ring(ground, (0, 0.4, 0), 18, 18, (6.5, 1.2, 0.3), glow, axis="y")
    gb = m.bone("ground_band", ground, pivot=(0, 0.3, 0))
    ring(gb, (0, 0.3, 0), 14, 18, (5.2, 6.0, 0), band, axis="y")
    streaks = m.bone("streaks", root, pivot=(0, 20, 0))
    for k in range(8):
        a = k * 45
        streaks.box((math.cos(math.radians(a)) * 20, 20 + math.sin(math.radians(a)) * 20, 8), (0.8, 0.8, 16), glow)
    return m


def shock_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    charge = Anim("charge", length=0.6, loop=True)     # the delayed pressure knot trembles in place
    charge.scl("hoop", (LIFE(0.08, 0.15, base=0.4), LIFE(0.08, 0.15, 0.25, base=0.4), 1.0))
    charge.rot("hoop", (0, 0, M("q.life_time*240", lambda t: 240 * t)))
    charge.scl("ground", LIFE(0.06, 0.2, base=0.35))
    charge.scl("streaks", 0.3)
    blast = Anim("blast", length=0.55, loop="hold")
    blast.scl("hoop", {0: 0.4, 0.12: 2.2, 0.55: 3.6})
    blast.scl("hoop_band", {0: 1.0, 0.3: 1.0, 0.55: 0.0})
    blast.scl("ground", {0: 0.35, 0.18: 2.6, 0.55: 4.2})
    blast.scl("ground_band", {0: 1.0, 0.35: 0.6, 0.55: 0.0})
    blast.scl("streaks", {0: 0.3, 0.15: 2.4, 0.4: 3.0, 0.55: 0.0})
    blast.pos("streaks", {0: (0, 0, 0), 0.55: (0, 0, 20)})
    blast.scl("root", {0: 1.0, 0.45: 1.0, 0.55: 0.0})
    return [hidden, charge, blast]


# ============================================================================ sounds
def _shriek(dur=0.8, f0=1900, f1=2900, f2=1500, rasp=0.25):
    t = sy.t_axis(dur)
    x = t / dur
    f = f0 + (f1 - f0) * (1 - np.exp(-x * 14)) - (f1 - f2) * x ** 1.6
    f = f * (1 + 0.018 * np.sin(2 * np.pi * 37 * t))
    src = sy.osc(f, wave_="saw") * 0.6 + sy.osc(f * 2.01, wave_="saw") * 0.22
    src += sy.highpass(sy.noise(dur), 2500) * rasp * (0.5 + 0.5 * np.sin(2 * np.pi * 85 * t))
    v = sy.formants(src, [(2300, 500, 1.0), (3500, 700, 0.6), (5100, 900, 0.3)])
    return sy.norm(v * sy.env(dur, 0.012, 0.08, 0.8, dur * 0.5))


def _chirr(dur=0.6, f=2300, rate=26):
    t = sy.t_axis(dur)
    pulses = np.clip(np.sin(2 * np.pi * rate * t), 0, 1) ** 3
    src = sy.osc(f * (1 - 0.12 * t / dur) * (1 + 0.03 * np.sin(2 * np.pi * 7 * t)), wave_="tri") * pulses
    src += sy.bandpass(sy.noise(dur), f * 1.4, 3) * pulses * 0.3
    return sy.norm(sy.formants(src, [(f, 600, 1.0), (f * 1.6, 800, 0.5)]) * sy.env(dur, 0.01, 0.05, 0.85, 0.15))


def _rattle(dur=0.5, n=70, lo=3500, hi=7000):
    out = np.zeros(int(sy.SR * dur))
    rng = np.random.default_rng(77)
    for _ in range(n):
        i = int(rng.random() ** 0.7 * len(out) * 0.92)
        L = int(sy.SR * 0.006)
        tt = np.arange(L) / sy.SR
        g = np.sin(2 * np.pi * rng.uniform(lo, hi) * tt) * np.exp(-tt / 0.0015) * rng.uniform(0.3, 1.0)
        out[i:i + L] += g[:len(out) - i]
    return sy.norm(sy.fade(out, 0.002, 0.04))


def _whistle(dur, f0, f1, q=14):
    tone = sy.wind(dur, f0, f1, q=q, gust=0.0)
    glide = sy.osc(sy.sweep(f0, f1, dur, 1.4)) * sy.env(dur, dur * 0.3, 0.1, 0.8, dur * 0.3) * 0.25
    return sy.norm(tone + glide)


def sounds(pack):
    def save(name, sig, **kw):
        sy.save(pack, name, sig, **kw)
    shriek = sy.at(1.0, (0.0, _shriek(0.75)), (0.05, _shriek(0.6, 3100, 3900, 2500, 0.15) * 0.35))
    save("ed_air_shriek", sy.reverb(shriek, 1.1, 0.25), max_distance=72,
         variants=[sy.reverb(sy.pitch(shriek, 1.08), 1.1, 0.25), sy.reverb(sy.pitch(shriek, 0.93), 1.1, 0.25)])
    call = sy.at(1.3, (0.0, _shriek(0.22, 2600, 3300, 2900, 0.1) * 0.8), (0.24, _shriek(0.7, 2000, 2700, 1400, 0.3)),
                 (0.7, _chirr(0.45, 2100) * 0.4))
    save("ed_air_call", sy.reverb(call, 1.6, 0.35), max_distance=80)
    save("ed_air_chirr", sy.reverb(_chirr(0.6), 0.8, 0.2), volume=0.8, max_distance=40,
         variants=[sy.reverb(_chirr(0.5, 2600, 31), 0.8, 0.2)])
    flap = sy.at(0.45, (0.0, sy.whoosh(0.32, 180, 900, 1.2)), (0.02, _rattle(0.25, 40) * 0.35), (0.12, sy.thump(0.25, 90, 50, 0.05) * 0.4))
    save("ed_air_flap", flap, volume=0.9, max_distance=40, variants=[sy.pitch(flap, 1.1), sy.pitch(flap, 0.9)])
    save("ed_air_rattle", _rattle(0.5), volume=0.7, max_distance=32)
    save("ed_air_whistle", sy.at(1.4, (0.0, _whistle(1.3, 900, 2400) * 0.7), (0.0, sy.wind(1.3, 300, 1100, 1.2) * 0.5)),
         max_distance=64)
    dive = sy.at(1.8, (0.0, _whistle(1.6, 700, 3400, 18) * 0.8), (0.0, sy.wind(1.7, 250, 2200, 1.0, gust=0.2) * 0.7))
    dive = dive * np.linspace(0.3, 1.0, len(dive)) ** 1.5
    save("ed_air_dive", dive, max_distance=80)
    boom = sy.at(1.2, (0.0, sy.crack(0.35, 5200, 18) * 0.6), (0.0, sy.thump(0.9, 95, 28, 0.6)), (0.02, sy.whoosh(0.5, 2500, 300) * 0.5),
                 (0.1, sy.rumble(1.0, 60, 4) * 0.4))
    save("ed_air_boom", sy.reverb(boom, 1.4, 0.3), max_distance=80,
         variants=[sy.reverb(sy.pitch(boom, 1.12), 1.4, 0.3), sy.reverb(sy.pitch(boom, 0.9), 1.4, 0.3)])
    slash = sy.at(0.6, (0.0, sy.whoosh(0.28, 1200, 5200, 1.4)), (0.12, _rattle(0.3, 50) * 0.5), (0.14, sy.crack(0.2, 4200, 6) * 0.3))
    save("ed_air_slash", slash, max_distance=48, variants=[sy.pitch(slash, 1.12), sy.pitch(slash, 0.9)])
    t = sy.t_axis(2.0)
    vort = sy.wind(2.0, 300, 1500, 2.0, gust=0.1) * (0.6 + 0.4 * np.sin(2 * np.pi * 6 * t * (1 + t)))
    vort = sy.mixdown([vort, _whistle(2.0, 1200, 2000, 20) * 0.4]) * sy.env(2.0, 0.3, 0.1, 0.9, 0.5)
    save("ed_air_vortex", sy.reverb(vort, 0.9, 0.2), max_distance=48)
    rib = sy.at(1.0, (0.0, sy.whoosh(0.8, 400, 2600, 1.4)), (0.15, sy.shimmer(0.7, 3200, 10) * 0.25))
    save("ed_air_ribbon", sy.reverb(rib, 1.0, 0.3), volume=0.8, max_distance=48)
    cloud = sy.at(2.2, (0.0, sy.wind(2.0, 120, 520, 0.8, gust=0.3)), (0.3, sy.wind(1.6, 1800, 900, 3.0) * 0.3),
                  (0.6, sy.shimmer(1.2, 2600, 12) * 0.18))
    save("ed_air_cloud", sy.reverb(cloud, 1.8, 0.4), max_distance=80)
    tt = sy.t_axis(0.7)
    flare = sy.bandpass(sy.noise(0.7), 1100, 0.8) * (0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 18 * tt))) * sy.env(0.7, 0.02, 0.1, 0.8, 0.3)
    save("ed_air_flare", sy.at(0.9, (0.0, sy.norm(flare)), (0.0, sy.thump(0.4, 120, 60, 0.2) * 0.5), (0.05, _rattle(0.5) * 0.4)),
         max_distance=56)
    save("ed_air_land", sy.at(0.8, (0.0, sy.thump(0.4, 110, 50, 0.3)), (0.05, _rattle(0.6, 60) * 0.5)), volume=0.8, max_distance=40)
    dep = sy.at(2.0, (0.0, sy.wind(1.8, 1400, 300, 1.4, gust=0.2) * 0.7), (0.1, sy.shimmer(1.4, 2800, 16)[::-1] * 0.4),
                (0.3, sy.pitch(_chirr(0.5, 2400), 1.15) * 0.25))
    save("ed_air_depart", sy.reverb(dep, 2.0, 0.45), max_distance=64)


# ============================================================================ build
def build(pack):
    fx = particles(pack)
    fx.effect("ed_air_feather", "feather", count=6, life=(1.6, 2.8), size=(0.24, 0.16), shape=("sphere", 1.6), speed=(0.4, 1.4),
              accel=(0, -0.9, 0), drag=1.8, colors=["#f2f7ffff", "#a8c6ffdd", "#4c5f7e00"], blend="blend", spin=(360, 140))
    fx.effect("ed_air_feather_burst", "feather", count=14, life=(1.2, 2.4), size=(0.3, 0.18), shape=("sphere", 1.0),
              speed=(3.0, 6.0), accel=(0, -1.2, 0), drag=2.6, colors=["#ffffffff", "#c3d2e4ee", "#4c5f7e00"], blend="blend",
              spin=(360, 260))
    fx.effect("ed_air_streak", None, sprites=["wave", "slash", "arc"], count=5, life=(0.35, 0.7), size=(0.6, 0.15),
              shape=("sphere", 1.4), speed=(4.0, 9.0), drag=2.5, colors=["#ffffffff", "#bff3ffcc", "#7fd6ff00"])
    fx.effect("ed_air_gust", "puff", count=8, life=(0.5, 1.0), size=(0.5, 1.4), shape=("disc", 1.0), speed=(3.0, 6.0),
              drag=3.0, colors=["#eef6ffaa", "#c3d2e400"], blend="blend", spin=(360, 60))
    fx.effect("ed_air_cloud", "smoke", count=6, life=(1.6, 2.6), size=(1.6, 3.2), shape=("sphere", 3.0), speed=(0.2, 0.8),
              drag=0.8, colors=["#f6f9ffcc", "#aab9d000"], blend="blend", spin=(360, 20))
    fx.effect("ed_air_spark", None, sprites=["star", "spark"], count=8, life=(0.4, 0.9), size=(0.18, 0.0), shape=("sphere", 0.8),
              speed=(1.5, 4.0), drag=1.6, colors=["#ffffffff", "#bff3ffff", "#7fd6ff00"], spin=(360, 300))
    fx.effect("ed_air_shock", "ringthin", count=1, life=(0.5, 0.6), size=(0.6, 7.5), facing="emitter_transform_xz",
              colors=["#ffffffff", "#bff3ffcc", "#7fd6ff00"])
    fx.effect("ed_air_boom", "ring", count=1, life=(0.35, 0.45), size=(0.5, 4.5), colors=["#ffffffff", "#bff3ff00"])
    fx.effect("ed_air_trail", "dot", count=2, life=(0.4, 0.7), size=(0.16, 0.0), shape=("sphere", 0.2), speed=(0.0, 0.3),
              colors=["#ffffffff", "#bff3ffaa", "#7fd6ff00"])
    fx.effect("ed_air_motes", "dot", count=10, life=(1.0, 2.0), size=(0.08, 0.0), shape=("sphere", 3.0), speed=(0.1, 0.5),
              accel=(0, 0.5, 0), colors=["#e8fbffff", "#a8c6ff00"])
    sounds(pack)

    m, info = build_model()
    anims = build_anims(info)
    pack.actor(ACTOR, m, anims, STATES, always=ALWAYS, scale=SCALE, lifetime=LIFETIME, blend=0.25,
               display="Aether Raptor", sounds={"flap": "grimoire.ed_air_flap", "rattle": "grimoire.ed_air_rattle",
                                               "flare": "grimoire.ed_air_flare", "land": "grimoire.ed_air_land",
                                               "slash": "grimoire.ed_air_slash", "shriek": "grimoire.ed_air_shriek",
                                               "chirr": "grimoire.ed_air_chirr", "call": "grimoire.ed_air_call",
                                               "whistle": "grimoire.ed_air_whistle"},
               particles={"trail": "grimoire:ed_air_trail"})
    by = {a.name: a for a in anims}
    al = [(by["breathe"], 1.0), (by["life"], 1.0)]
    views = ((28, 22), (-90, 4), (0, 88), (205, -38))
    pack.preview("ed_air_a", m, [[(by["glide"], 0.0)] + al, [(by["idle"], 0.5)] + al, [(by["move"], 0.36)] + al], views=views)
    pack.preview("ed_air_b", m, [[(by["turn_r"], 0.0)] + al, [(by["stoop"], 0.45)] + al, [(by["flare"], 0.5)] + al,
                                 [(by["move"], 0.62)] + al], views=((20, 15), (-90, 4), (180, 20)))
    pack.preview("ed_air_c", m, [[(by["power"], 0.9)] + al, [(by["attack_a"], 0.3)] + al, [(by["attack_b"], 0.35)] + al,
                                 [(by["rest"], 0.0)] + al, [(by["arrive"], 0.95)] + al, [(by["depart"], 1.0)] + al],
                 views=((30, 18), (-90, 6)), skin="aether")
    print(f"    {ACTOR}: {m.cube_count()} cubes, {len(m.order)} bones, tex {m.tex_size}")

    cl = cloud_model()
    cla = cloud_anims()
    pack.actor("ed_air_cloud", cl, cla, {0: ["hidden"], 1: ["form"], 2: ["part"], 3: ["fade"]}, always=["churn"],
               size_prop=True, lifetime=60, display="Cloud Bank", blend=0.2)
    rb = ribbon_model()
    rba = ribbon_anims()
    pack.actor("ed_air_ribbon", rb, rba, {0: ["hidden"], 1: ["draw"], 2: ["hold"], 3: ["fray"]}, always=["flow", "twist"],
               size_prop=True, lifetime=60, display="Air Current", blend=0.15)
    vx = vortex_model()
    vxa = vortex_anims()
    pack.actor("ed_air_vortex", vx, vxa, {0: ["hidden"], 1: ["form"], 2: ["hold"], 3: ["burst"]}, always=["spin"],
               size_prop=True, lifetime=60, display="Wind Vortex", blend=0.1)
    sh = shock_model()
    sha = shock_anims()
    pack.actor("ed_air_shock", sh, sha, {0: ["hidden"], 1: ["charge"], 2: ["blast"]}, size_prop=True, lifetime=60,
               display="Shockwave", blend=0.0)
    cb = {a.name: a for a in cla}
    pack.preview("ed_air_cloud", cl, [(cb["churn"], 0.5), [(cb["part"], 1.2), (cb["churn"], 0.5)]], views=((20, 20), (0, -30)))
    rbb = {a.name: a for a in rba}
    vb = {a.name: a for a in vxa}
    sb = {a.name: a for a in sha}
    pack.preview("ed_air_ribbon", rb, [[(rbb["twist"], 0.4), (rbb["flow"], 0.3)]], views=((60, 30), (0, 80)))
    pack.preview("ed_air_vortex", vx, [[(vb["spin"], 0.3), (vb["hold"], 0.1)]], views=((20, 15),))
    pack.preview("ed_air_shock", sh, [(sb["blast"], 0.12)], views=((30, 15),))
    print(f"    constructs: cloud {cl.cube_count()} / ribbon {rb.cube_count()} / vortex {vx.cube_count()} / shock {sh.cube_count()}")
