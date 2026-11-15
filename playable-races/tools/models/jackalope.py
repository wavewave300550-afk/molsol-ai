"""Race 003 - Blood Moon Jackalope.

Lagomorph anatomy with living lunar antlers.  Variants:
  base | hunt (antlers blaze, ears pinned) | awakened (Blood Moon: extra tines,
  raised dorsal fur, crimson veins) | awakened_hunt
"""
from __future__ import annotations

import math

import numpy as np

from kit.geo import Model
from kit.tex import Ctx, hx
from kit import noise as nz
from models.common import humanoid, side_rot, fp_sleeves, ramp, bevel, face_light, mix3, desat, clamp01, accents, mat_accent

ID = "jackalope"
VARIANTS = ["base", "hunt", "awakened", "awakened_hunt"]
TEXTURES = {
    "base": {"blood": 0.0, "hunt": 0.0},
    "hunt": {"blood": 0.0, "hunt": 1.0},
    "awakened": {"blood": 1.0, "hunt": 0.6},
}
VARIANT_TEXTURE = {"base": "base", "hunt": "hunt", "awakened": "awakened", "awakened_hunt": "awakened"}
AWAKE = {"awakened", "awakened_hunt"}
HUNT = {"hunt", "awakened_hunt"}

THIGH_RX, SHIN_RX, FOOT_RX = -30.0, 62.0, -32.0


def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=512)
    humanoid(m)
    _legs(m)
    _torso(m)
    _head(m)
    _arms(m)
    _tail(m)
    fp_sleeves(m, "fur", width=4.8)
    accents(m, [
        ("c", "chest", "torso", (0, 20.0, -2.15), (5.0, 4.0, 0.5)),
        ("c", "rsh", "r_arm_g", (-4.6, 22.2, 0.2), (3.6, 1.2, 3.8)),
        ("c", "lsh", "l_arm_g", (4.6, 22.2, 0.2), (3.6, 1.2, 3.8)),
        ("l", "r", "r_thigh", (-5.35, 10.6, 0.8), (0.5, 3.2, 4.4)),
        ("l", "l", "l_thigh", (5.35, 10.6, 0.8), (0.5, 3.2, 4.4)),
        ("f", "r", "r_shin", (-2.5, 3.6, -1.35), (2.4, 4.4, 0.5)),
        ("f", "l", "l_shin", (2.5, 3.6, -1.35), (2.4, 4.4, 0.5)),
    ])
    m.pack()
    return m


def _legs(m: Model) -> None:
    for side, g, p in ((-1, "r_leg_g", "r"), (1, "l_leg_g", "l")):
        hx_ = 1.9 * side
        x = 2.5 * side
        th = m.bone(f"{p}_thigh", g, (hx_, 12, 0), (THIGH_RX, 0, 0))
        m.cube(th.name, (x - 2.1, 6.0, -2.2), (4.2, 6.9, 5.0), "fur")
        m.box(th.name, (x + 0.2 * side, 10.6, 0.8), (4.8, 3.8, 5.4), "fur", faces={"north", "south", "up", "down", "west" if side < 0 else "east"})
        m.box(th.name, (x + 0.2 * side, 10.6, 0.8), (4.8, 3.8, 5.4), "flank", faces={"east" if side < 0 else "west"})
        sh = m.bone(f"{p}_shin", th.name, (x, 6.3, 0.2), (SHIN_RX, 0, 0))
        m.cube(sh.name, (x - 1.3, -0.1, -1.1), (2.6, 6.4, 2.6), "fur")
        ft = m.bone(f"{p}_foot", sh.name, (x, -0.1, 0.2), (FOOT_RX, 0, 0))
        ft.locators[f"{p}_step"] = (x, -1.4, -3.0)
        m.cube(ft.name, (x - 1.5, -1.6, -6.6), (3.0, 1.5, 7.4), "fur")
        m.cube(ft.name, (x - 1.3, -1.7, -6.4), (2.6, 0.1, 6.8), "pad", faces={"down"})
        for k, dx in enumerate((-0.9, 0.0, 0.9)):
            m.cube(ft.name, (x + dx - 0.4, -1.5, -7.6), (0.8, 1.0, 1.1), "claw")


def _torso(m: Model) -> None:
    t = m.bone("torso", "torso_g", (0, 13, 0.6), (9, 0, 0))
    m.box(t.name, (0, 18.2, 0.5), (6.4, 9.6, 4.6), "fur")
    m.box(t.name, (0, 13.8, 1.1), (7.0, 3.2, 5.4), "fur")                        # haunches/pelvis
    m.box(t.name, (0, 20.8, -1.95), (5.0, 3.8, 0.8), "ruff")                     # chest ruff
    m.box(t.name, (0, 17.0, -1.9), (4.2, 4.6, 0.4), "belly")
    m.box(t.name, (0, 23.0, 0.4), (5.4, 1.4, 4.0), "fur")                        # shoulders/neck
    for side in (-1, 1):
        m.cube(t.name, (3.2 * side - (0.0 if side > 0 else 0.2), 15.0, -1.2), (0.2, 7.0, 4.4), "flank",
               faces={"east"} if side < 0 else {"west"})
    # dorsal crest: fur tufts that rise when the Blood Moon awakens the creature
    for k in range(6):
        y = 22.6 - k * 1.7
        b = m.bone(f"dorsal{k}", t.name, (0, y, 2.8), (-64, 0, 0))
        b.variant.update({v: ((0, 0, 0), (-10, 0, 0)) for v in AWAKE})
        m.cube(b.name, (0, y, 2.8), (0.0, 2.6 - k * 0.15, 1.8), "tuft", cutout=True, faces={"east", "west"})
    t.locators["chest"] = (0, 20, -2.5)


def _head(m: Model) -> None:
    s = m.bone("skull", "head_g", (0, 23.6, 0.3))
    s.variant.update({v: ((0, 0, 0), (14, 0, 0)) for v in HUNT})               # head lowers for the charge
    m.box(s.name, (0, 25.2, -0.6), (5.0, 4.6, 5.6), "fur")                       # cranium
    m.box(s.name, (0, 24.3, -4.4), (3.8, 3.4, 3.0), "muzzle")                    # muzzle
    m.box(s.name, (0, 25.2, -6.3), (2.8, 2.0, 1.2), "muzzle")
    nb = m.bone("nose", s.name, (0, 25.4, -6.9))
    m.box(nb.name, (0, 25.4, -7.0), (1.4, 0.9, 0.3), "nose")
    for side in (-1, 1):
        p = "r" if side < 0 else "l"
        m.box(s.name, (0.38 * side, 23.25, -6.55), (0.6, 1.3, 0.35), "tooth")
        m.box(s.name, (2.55 * side, 25.5, -1.8), (0.5, 1.9, 2.3), "eye")
        # eyelid: thin brow at rest, scale y ~6.9 closes it over the eye
        lid = m.bone(f"{p}_lid", s.name, (2.6 * side, 26.55, -1.8))
        m.cube(lid.name, (2.6 * side - 0.33, 26.25, -3.05), (0.66, 0.3, 2.5), "fur")
        m.box(s.name, (2.35 * side, 23.6, -1.4), (1.2, 2.2, 2.8), "fur")          # cheek
        wb = m.bone(f"{p}_whisker", s.name, (1.6 * side, 24.2, -5.5))
        m.cube(wb.name, (1.6 * side - (2.6 if side < 0 else 0), 24.2, -6.2), (2.6, 0.0, 1.4), "whisker",
               cutout=True, faces={"up", "down"})
    jb = m.bone("jaw", s.name, (0, 23.0, -2.3))                                  # chewing lower jaw
    m.box(jb.name, (0, 22.7, -3.9), (2.8, 0.7, 3.4), "muzzle")
    # long, independently animated ears (inner surface faces forward)
    for side, p in ((-1, "r"), (1, "l")):
        ex = 1.25 * side
        e = m.bone(f"{p}_ear", s.name, (ex, 27.3, 1.3), side_rot((-16, 0, -13), side))
        e.variant.update({v: ((0, 0, 0), side_rot((-62, 0, -18), side)) for v in HUNT})
        m.cube(e.name, (ex - 1.2, 27.3, 0.85), (2.4, 4.6, 0.9), "ear")
        m.cube(e.name, (ex - 0.9, 27.6, 0.80), (1.8, 4.2, 0.05), "inner_ear", faces={"north"})
        et = m.bone(f"{p}_ear_tip", e.name, (ex, 31.9, 1.3), (-8, 0, 0))
        m.cube(et.name, (ex - 1.1, 31.9, 0.9), (2.2, 3.4, 0.8), "ear")
        m.cube(et.name, (ex - 0.8, 31.9, 0.85), (1.6, 3.0, 0.05), "inner_ear", faces={"north"})
        m.cube(et.name, (ex - 0.7, 35.3, 0.95), (1.4, 0.7, 0.6), "ear")
    # obsidian antlers with crimson channels; extra tines grow during the Blood Moon
    for side, p in ((-1, "r"), (1, "l")):
        ax = 1.45 * side
        a1 = m.bone(f"{p}_antler", s.name, (ax, 26.9, -1.0), side_rot((-10, 0, -22), side))
        m.cube(a1.name, (ax - 0.45, 26.9, -1.45), (0.9, 3.6, 0.9), "antler")
        a2 = m.bone(f"{p}_antler2", a1.name, (ax, 30.4, -1.0), side_rot((-8, 0, -18), side))
        m.cube(a2.name, (ax - 0.4, 30.4, -1.4), (0.8, 3.4, 0.8), "antler")
        a3 = m.bone(f"{p}_antler3", a2.name, (ax, 33.7, -1.0), side_rot((6, 0, 16), side))
        m.cube(a3.name, (ax - 0.35, 33.7, -1.35), (0.7, 2.2, 0.7), "antler")
        tines = (("brow", a1, 28.6, (64, 0, -8), 2.6, None), ("out", a2, 31.8, (-6, 0, -46), 2.3, None),
                 ("back", a2, 32.9, (-55, 0, -14), 2.5, AWAKE), ("low", a1, 28.0, (12, 0, -64), 1.9, AWAKE),
                 ("crown", a3, 35.0, (30, 0, -32), 1.7, AWAKE), ("crown2", a3, 35.3, (-34, 0, 22), 1.5, AWAKE))
        for nm, parent, y, rot, ln, only in tines:
            tb = m.bone(f"{p}_tine_{nm}", parent.name, (ax, y, -1.0), side_rot(rot, side), only=only)
            m.cube(tb.name, (ax - 0.32, y, -1.32), (0.64, ln, 0.64), "antler", only=only)
    s.locators["antlers"] = (0, 31, -1)
    s.locators["eyes"] = (0, 25.5, -2.0)


def _arms(m: Model) -> None:
    for side, g, p in ((-1, "r_arm_g", "r"), (1, "l_arm_g", "l")):
        ax = 4.9 * side
        m.box(g, (ax + 0.4 * -side, 20.6, 0.2), (2.9, 3.0, 3.1), "fur")
        m.box(g, (ax, 18.0, 0.2), (2.4, 4.4, 2.5), "fur")
        fo = m.bone(f"{p}_fore", g, (ax, 15.8, 0.2), (-8, 0, 0))
        m.box(fo.name, (ax, 14.0, 0.1), (2.3, 3.8, 2.4), "fur")
        m.box(fo.name, (ax, 11.9, -0.1), (2.6, 1.8, 2.8), "muzzle")               # paw
        for k, dz in enumerate((-1.0, 0.0, 1.0)):
            m.box(fo.name, (ax, 10.6, -0.1 + dz * 0.85), (0.8, 1.0, 0.8), "claw")
        m.box(fo.name, (ax - 1.1 * side, 11.4, -1.4), (0.7, 1.4, 0.7), "claw")    # thumb


def _tail(m: Model) -> None:
    t = m.bone("scut", "tail_g", (0, 13.8, 3.6), (0, 0, 0))
    m.box(t.name, (0, 14.2, 4.8), (3.6, 3.4, 2.6), "tail")
    m.box(t.name, (0, 14.4, 6.2), (2.6, 2.4, 0.8), "tail")
    t.locators["tail"] = (0, 14.2, 6.4)


# ============================================================================= materials

def materials():
    return {"fur": mat_fur, "ruff": mat_ruff, "belly": mat_belly, "flank": mat_flank, "marking": mat_marking,
            "muzzle": mat_muzzle, "nose": mat_nose, "tooth": mat_tooth, "eye": mat_eye, "whisker": mat_whisker,
            "ear": mat_fur, "inner_ear": mat_inner_ear, "antler": mat_antler, "claw": mat_claw, "pad": mat_pad,
            "tail": mat_tail, "tuft": mat_tuft, "accent": mat_accent}


def _P(ctx):
    return ctx.params.get("blood", 0.0), ctx.params.get("hunt", 0.0)


def _fur_base(ctx: Ctx, light=0.0):
    blood, hunt = _P(ctx)
    p = ctx.p
    # anisotropic strands: stretched noise along the limb/body axis (mostly vertical)
    strands = nz.value(p * np.array([3.2, 0.55, 3.2]), 1.0, seed=3)
    broad = nz.fbm(p, 0.35, 3, seed=7)
    c = ramp([(0, "#0f0d1f"), (0.4, "#1b1833"), (0.7, "#28244a"), (1, "#3a3463")],
             broad * 0.6 + strands * 0.4 + light)
    # sheen on top-facing fur
    if ctx.face == "up":
        c = c * 1.25
    # crimson veins surface during the Blood Moon
    if blood > 0:
        r = nz.ridged(nz.warp(p, 1.0, 0.2, seed=2), 0.42, 3, seed=6)
        vein = nz.smoothstep(0.86, 0.95, r) * blood
        c = mix3(c, hx("#c0132c"), vein * 0.85)
        return c, vein * 0.7
    return c, ctx.zeros()


def mat_fur(ctx):
    c, g = _fur_base(ctx)
    return bevel(ctx, face_light(ctx, c, 0.10, 0.2), 0.14, 0.6), ctx.ones(), g


def mat_ruff(ctx):
    c, g = _fur_base(ctx, light=0.25)
    c = mix3(c, hx("#5b5687"), 0.35)
    tuft = np.mod(ctx.s * 2.5 + nz.value(ctx.p, 2.0) * 0.8, 1.0) < 0.5
    c = np.where(tuft[:, None], c * 1.15, c * 0.92)
    return c, ctx.ones(), g


def mat_belly(ctx):
    c, g = _fur_base(ctx, light=0.18)
    return mix3(c, hx("#4b4670"), 0.3), ctx.ones(), g


def _crescent(u, v, cu=0.5, cv=0.5, r1=0.36, r2=0.33, off=(0.13, -0.05)):
    d1 = np.sqrt((u - cu) ** 2 + (v - cv) ** 2) < r1
    d2 = np.sqrt((u - cu - off[0]) ** 2 + (v - cv - off[1]) ** 2) < r2
    return d1 & ~d2


def mat_flank(ctx):
    """Torso flank with the curved silver-grey lunar crescent markings."""
    blood, hunt = _P(ctx)
    c, g = _fur_base(ctx)
    u = ctx.s / ctx.fw
    v = ctx.t / ctx.fh
    cres = _crescent(u, v, 0.5, 0.42, 0.40, 0.36, (0.16 if ctx.face == "west" else -0.16, -0.06))
    small = _crescent(u, v, 0.5, 0.80, 0.16, 0.14, (0.07 if ctx.face == "west" else -0.07, -0.03))
    mark = cres | small
    silver = mix3(hx("#a7a9bd"), hx("#dfe0ee"), nz.fbm(ctx.p, 1.5, 2))
    silver = mix3(silver, hx("#ff4a5a"), 0.55 * blood)
    c = np.where(mark[:, None], silver, c)
    g = np.where(mark, 0.18 + 0.5 * blood, g)
    return c, ctx.ones(), g


def mat_marking(ctx):
    blood, hunt = _P(ctx)
    c = mix3(hx("#a7a9bd"), hx("#e6e7f2"), nz.fbm(ctx.p, 1.5, 2))
    c = mix3(c, hx("#ff4a5a"), 0.55 * blood)
    return c, ctx.ones(), ctx.zeros() + 0.18 + 0.5 * blood


def mat_muzzle(ctx):
    blood, hunt = _P(ctx)
    n = nz.value(ctx.p * np.array([3, 0.8, 3]), 1.0, seed=9)
    c = ramp([(0, "#3a3657"), (0.5, "#5a5580"), (1, "#7c78a2")], n * 0.7 + 0.2)
    return bevel(ctx, face_light(ctx, c), 0.12, 0.4), ctx.ones(), ctx.zeros()


def mat_nose(ctx):
    return mix3(hx("#5d2c3e"), hx("#9a4a63"), ctx.local[:, 1]), ctx.ones(), ctx.zeros()


def mat_tooth(ctx):
    return mix3(hx("#e8e3d0"), hx("#fffdf2"), ctx.local[:, 1]), ctx.ones(), ctx.zeros()


def mat_eye(ctx):
    blood, hunt = _P(ctx)
    c = np.broadcast_to(hx("#0d0b18"), (ctx.N, 3)).copy()
    glow = ctx.zeros()
    if ctx.face in ("east", "west"):
        u = ctx.s / ctx.fw - 0.5
        v = ctx.t / ctx.fh - 0.5
        rr = np.sqrt(u * u + v * v * 1.2)
        iris = rr < 0.42
        silver = ramp([(0, "#ffffff"), (0.5, "#c9cbe0"), (1, "#7f82a3")], rr / 0.42)
        red = ramp([(0, "#ffd0d0"), (0.5, "#ff2a3a"), (1, "#7d0612")], rr / 0.42)
        k = clamp01(blood + 0.65 * hunt)
        irc = silver * (1 - k) + red * k
        c = np.where(iris[:, None], irc, c)
        pupil = rr < 0.16
        c = np.where(pupil[:, None], hx("#05040a"), c)
        hl = ((u + 0.14) ** 2 + (v + 0.16) ** 2) < 0.01
        c = np.where(hl[:, None], hx("#ffffff"), c)
        glow = np.where(iris & ~pupil, 0.45 + 0.4 * k, 0.0)
    return c, ctx.ones(), glow


def mat_whisker(ctx):
    u = ctx.s / ctx.fw
    v = ctx.t / ctx.fh
    line = (np.abs(v - 0.25 - u * 0.15) < 0.07) | (np.abs(v - 0.7 + u * 0.12) < 0.07)
    return np.broadcast_to(hx("#d9d9e8"), (ctx.N, 3)), np.where(line & (u > 0.05), 1.0, 0.0), ctx.zeros()


def mat_inner_ear(ctx):
    blood, hunt = _P(ctx)
    c = ramp([(0, "#5a2638"), (1, "#b45670")], ctx.local[:, 1])
    r = nz.ridged(ctx.p * np.array([2.0, 0.7, 2.0]), 0.9, 2, seed=4)
    vein = nz.smoothstep(0.82, 0.93, r)
    c = mix3(c, hx("#ff1f3e"), vein * (0.6 + 0.4 * max(blood, hunt)))
    g = vein * (0.25 + 0.6 * max(blood, hunt))
    return c, ctx.ones(), g


def mat_antler(ctx):
    blood, hunt = _P(ctx)
    p = ctx.p
    n = nz.fbm(p, 1.6, 3, seed=8)
    c = ramp([(0, "#050507"), (0.6, "#121018"), (0.85, "#2a2540"), (1, "#5a4f86")], n)
    sheen = nz.hash_points(p, 0.5, 2) < 0.06
    c = np.where(sheen[:, None], mix3(c, hx("#8b7fd1"), 0.6), c)
    # glowing channel running along the antler (face-centre groove)
    u = ctx.s / ctx.fw
    chan = (np.abs(u - 0.5) < 0.17) & (ctx.face in ("north", "south", "east", "west"))
    k = clamp01(0.35 + 0.45 * hunt + 0.6 * blood)
    c = np.where(chan[:, None], mix3(hx("#7a0a18"), hx("#ff3348"), k), c)
    g = np.where(chan, 0.35 + 0.6 * k, 0.0)
    return c, ctx.ones(), g


def mat_claw(ctx):
    return mix3(hx("#1a1724"), hx("#3a3550"), ctx.local[:, 1]), ctx.ones(), ctx.zeros()


def mat_pad(ctx):
    return mix3(hx("#2c2638"), hx("#4a3d55"), nz.fbm(ctx.p, 2, 2)), ctx.ones(), ctx.zeros()


def mat_tail(ctx):
    blood, hunt = _P(ctx)
    n = nz.fbm(ctx.p, 1.8, 3, seed=5)
    c = ramp([(0, "#3a3560"), (0.6, "#6a6596"), (1, "#a9a6cf")], n)
    ring = np.abs(np.sqrt((ctx.s / ctx.fw - 0.5) ** 2 + (ctx.t / ctx.fh - 0.5) ** 2) - 0.32) < 0.07
    k = clamp01(max(hunt, blood))
    c = np.where(ring[:, None], mix3(hx("#4a2a44"), hx("#ff2c44"), k), c)
    return bevel(ctx, c, 0.18, 0.6), ctx.ones(), np.where(ring, 0.8 * k, 0.0)


def mat_tuft(ctx):
    blood, hunt = _P(ctx)
    u = ctx.s / ctx.fw
    v = ctx.t / ctx.fh
    strands = np.mod(u * 4 + v * 0.6, 1.0) < 0.55
    shape = v > (np.abs(u - 0.5) * 1.4) ** 1.5
    alpha = np.where(strands & shape, 1.0, 0.0)
    c = mix3(hx("#1d1a36"), hx("#3d3768"), 1 - v)
    c = mix3(c, hx("#b3122c"), 0.6 * blood * (1 - v))
    return c, alpha, ctx.zeros()
