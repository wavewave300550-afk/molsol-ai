"""Ophanim -- the wheels within wheels of the Divine Word (DW03, reused by DW05).

Original design: an armillary engine of five golden wheels.
  * w1  great outer wheel (rim + silver rail + teeth + blue struts), spins in its own plane;
  * w2  gimbal wheel pinned to w1 on a vertical diameter, tumbles about that diameter;
  * w3  inner gimbal pinned to w2 on a horizontal diameter, tumbles about it;
  * c1 / c2 a counter-rotating toothed pair on their own oblique axis;
  * core  a hovering seal of First-Word text (three crossed inscription discs + a white-gold gem).
Twenty-two mechanical eyes sit on the rims (front and back faces alternate).  Every eye has a
swivelling eyeball bone and separate upper / lower lid bones, so eyes open, blink, squint and look
around independently.  The in-plane spin of the wheels is integrated in Molang (v.ph), so wheel
speed changes smoothly with the state: slow precession while surveying, a near-stop at the lock,
an aligned blur in the sweep.
"""
import math
import random

import numpy as np

from kit import glyphs, synth as sy, tex
from kit.anim import LIFE, Anim, M
from kit.geo import Mat, Model, ring

from .a_fx_common import particles

IVORY, GOLD, WGOLD, SILVER, BLUE = "#f5f0e1", "#c9a24a", "#fff3c4", "#d8dde3", "#2b3f8f"
FW = glyphs.FIRST_WORD

# ---- state ids (mirror in src/spells/dw03_ophanim.ts and any spell that reuses the Ophanim)
STATES_DOC = {0: "hidden", 1: "arrive", 2: "survey", 3: "lock", 4: "sweep", 5: "verdict", 6: "depart"}
# animation lengths in seconds (the script timeline uses the same numbers)
T_ARRIVE, T_LOCK, T_VERDICT, T_DEPART, T_SURVEY_LOOP = 2.0, 0.6, 1.1, 1.8, 6.0
# in-plane wheel speed (deg/s of the master phase v.ph) per state; preview assumes PV
SPEED = {1: 120.0, 2: 45.0, 3: 15.0, 4: 520.0, 5: 300.0, 6: 140.0}
PV = 45.0
LID_OPEN, LID_SQUINT, LID_WIDE = 88, 40, 100

# wheel geometry: name -> (rim radius, rim radial width, rim thickness, rail radius, eye count, eye scale)
WHEELS = {
    "w1": dict(R=48.0, rw=6.0, th=5.0, rail=41.0, n_rim=28, n_rail=24, eyes=10, es=1.0, face="rim_face"),
    "w2": dict(R=35.0, rw=5.0, th=4.5, rail=30.0, n_rim=22, n_rail=20, eyes=6, es=0.85, face="rim_face2"),
    "w3": dict(R=24.0, rw=4.5, th=4.0, rail=20.0, n_rim=18, n_rail=16, eyes=6, es=0.72, face="rim_face3"),
}


def lm(expr, fn):
    """Molang expression with a python twin (for previews)."""
    return M(expr, fn)


def life_spin(rate, offset=0.0):
    return lm(f"math.mod(q.life_time*{rate}+{offset}, 360.0)", lambda t: (t * rate + offset) % 360)


def life_spin_neg(rate, offset=0.0):
    return lm(f"-math.mod(q.life_time*{rate}+{offset}, 360.0)", lambda t: -((t * rate + offset) % 360))


def phase(k):
    """In-plane wheel angle: master phase v.ph (integrated per state speed) times a wheel ratio."""
    return lm(f"v.ph*{k}", lambda t: t * PV * k)


# survey motions (also the end keys of the arrive so the hand-over is seamless)
EW2 = life_spin(28.0)
EW3 = life_spin_neg(21.0, 320.0)
ECF = life_spin(17.0)
EBY = life_spin(9.0)
EBX = LIFE(9, 7.0)
EBZ = LIFE(7, 5.2)
CF_BIND = (55, 0, 35)
CF_FLAT = (-55, 0, -35)


# ---------------------------------------------------------------------------------- materials
def mats():
    m = {}
    gold = tex.metal(GOLD, "#ffe9a3", "#7a5a1e", bands=1.5)
    m["rim_face"] = tex.trimmed(gold, WGOLD, 1, 1, glow=0.75)
    m["rim_face2"] = tex.trimmed(tex.marble(IVORY, "#d9c79a", scale=5), GOLD, 1, 0, glow=0.2)
    m["rim_face3"] = tex.trimmed(tex.metal("#f0d98a", "#fffbe8", "#b08a3a", bands=2.0, glow=0.25), "#ffffff", 1, 1, glow=0.9)
    m["sun"] = tex.trimmed(tex.metal("#e9c766", "#fff6d0", "#9a7a2e", bands=1.0, glow=0.3), "#fff3c4", 1, 0, glow=0.8)
    m["rim_edge"] = tex.glyph_rows(FW, WGOLD, glow=1.0, color2="#ffd76a", bg="#4a3410", bg_glow=0.08, seed=3, key="ophedge")
    m["rim_in"] = tex.metal("#a8842f", "#e9cf8a", "#5e4314", bands=1.0)
    m["rail"] = tex.metal(SILVER, "#ffffff", "#7d8592", bands=2.0, glow=0.12)
    m["teeth"] = tex.metal("#e9c766", "#fff6d0", "#9a7a2e", bands=1.0, glow=0.45)
    m["strut"] = tex.trimmed(tex.speck(BLUE, 0.05, edge_dark=0.2), GOLD, 1, 0, glow=0.35)
    m["pin"] = tex.metal(SILVER, "#ffffff", "#6d7482", bands=1.0, glow=0.2)
    m["housing"] = tex.trimmed(tex.speck("#24367d", 0.05, edge_dark=0.25), WGOLD, 1, 0, glow=0.8)
    m["eye_side"] = tex.metal("#8a6a26", "#d9b45a", "#4a3410", bands=1.0)
    m["eye"] = tex.alt(tex.eye_mat(iris=BLUE, sclera=IVORY, pupil="#0d1030", lid="#c9a24a", glow=0.9, ring=WGOLD),
                       judging=tex.eye_mat(iris="#fff3c4", sclera="#fffaf0", pupil=BLUE, lid="#e9c766", glow=1.0,
                                           slit=True, ring="#ffffff"))
    lid = tex.metal("#d9b45a", "#fff3c4", "#8a6a26", bands=1.2)
    m["lid"] = tex.alt(tex.trimmed(lid, "#6a4c16", 1, 0), judging=tex.trimmed(lid, "#fff3c4", 1, 0, glow=0.9))
    m["c_rim"] = tex.trimmed(tex.metal("#e4e8ee", "#ffffff", "#8a909c", bands=1.5, glow=0.1), GOLD, 1, 0, glow=0.5)
    m["c_rim2"] = tex.trimmed(tex.metal("#d9b45a", "#fff3c4", "#8a6a26", bands=2.0, glow=0.1), BLUE, 1, 0)
    m["seal"] = tex.magic_circle(FW, "#ffffff", WGOLD, bands=((0.56, 0.95, 10),), lines=(0.5, 0.98), star=6,
                                 star_r=(0.15, 0.5), core=0.1, key="ophseal")
    m["seal2"] = tex.magic_circle(FW, WGOLD, "#ffd76a", bands=((0.6, 0.96, 12),), lines=(0.55,), star=5,
                                  star_r=(0.12, 0.55), key="ophseal2")
    m["gem"] = tex.glow_flat("#fff3c4", 1.0, core="#ffffff")
    m["ring_plane"] = tex.magic_circle(FW, WGOLD, "#ffffff", bands=((0.86, 0.97, 32),), lines=(0.84, 0.99), key="ophring")
    m["blur"] = blur_mat()
    return m


def blur_mat():
    """Translucent motion-blur disc for the aligned sweep: bright bands at every wheel radius."""
    radii = [(52 / 54, 0.035, 0.55), (48 / 54, 0.06, 0.45), (41 / 54, 0.02, 0.35), (35 / 54, 0.05, 0.4),
             (24 / 54, 0.045, 0.38), (16 / 54, 0.04, 0.3), (12.5 / 54, 0.03, 0.25)]

    def fn(ctx):
        u, v = ctx.U * 2 - 1, ctx.V * 2 - 1
        r = np.hypot(u, v)
        a = np.arctan2(v, u)
        alpha = np.zeros_like(r)
        for rr, w, k in radii:
            alpha = np.maximum(alpha, k * np.exp(-((r - rr) / w) ** 2))
        alpha *= 0.75 + 0.25 * np.sin(a * 14 + r * 30)
        alpha = np.where(r > 1.0, 0, alpha)
        t = np.zeros((ctx.h, ctx.w, 5))
        col = tex.mix(tex.rgb("#c9a24a"), tex.rgb("#fffbe8"), np.clip(alpha * 2, 0, 1)[..., None])
        t[..., :3] = col
        t[..., 3] = np.clip(alpha, 0, 1)
        t[..., 4] = 0.9
        return t
    return Mat(fn, "ophblur", mode="blend", directional=True)


# ---------------------------------------------------------------------------------- model
EYES = []   # (eye bone, wheel, index on wheel, group)


def build_wheel(m, M_, bone, w, name):
    R, rw, th = w["R"], w["rw"], w["th"]
    face = M_[w["face"]]
    mats_rim = {"east": M_["rim_edge"], "west": M_["rim_in"]}
    ring(bone, (0, 0, 0), R, w["n_rim"], (2 * math.pi * R / w["n_rim"] + 0.3, rw, th), face, axis="z",
         density=2.0, mats=mats_rim, cycle=2)
    ring(bone, (0, 0, 0), w["rail"], w["n_rail"], (2 * math.pi * w["rail"] / w["n_rail"] + 0.3, 1.8, th * 0.6),
         M_["rail"], axis="z", density=1.5)
    n_eyes = w["eyes"]
    # blue struts tie the rim to the rail between the eyes
    for k in range(n_eyes):
        a = (k + 0.5) * 360 / n_eyes
        r0, r1 = w["rail"] + 0.6, R - rw / 2 + 0.2
        c = ((r0 + r1) / 2 * math.cos(math.radians(a)), (r0 + r1) / 2 * math.sin(math.radians(a)), 0)
        bone.box(c, (r1 - r0, 2.0, th * 0.5), M_["strut"], rot=(0, 0, a), pivot=c)
    # eyes (alternating front / back faces)
    es = w["es"]
    bw, bh = 10.5 * es, 6.2 * es
    for k in range(n_eyes):
        a = k * 360 / n_eyes
        back = k % 2 == 1
        zs = 1 if back else -1
        x, y = R * math.cos(math.radians(a)), R * math.sin(math.radians(a))
        rot = (0, 180 if back else 0, a - 90)
        hc = (x, y, zs * (th / 2 + 0.5))
        bone.box(hc, (bw + 2.6 * es, bh + 2.4 * es, 1.0), M_["housing"], rot=rot, pivot=hc, density=2.0)
        sc = (x, y, zs * (th / 2 + 0.25))   # gilded diamond sun-plate behind the eye
        bone.box(sc, (bh + 5 * es, bh + 5 * es, 0.5), M_["sun"], rot=(rot[0], rot[1], rot[2] + 45), pivot=sc)
        P = (x, y, zs * (th / 2 + 1.0))
        en = f"{name}_e{k + 1}"
        eb = m.bone(en, bone, pivot=P, rot=rot)
        # canonical eye (front = -Z) built around P; the bone's bind rotation places it on the rim
        eb.box(P, (bw, bh, 2.0), M_["eye_side"], mats={"north": M_["eye"]}, density=2.0)
        lh = bh / 2 + 0.35
        ub = m.bone(en + "u", eb, pivot=P)
        ub.box((P[0], P[1] + lh / 2, P[2] - 1.3), (bw + 0.6 * es, lh, 0.5), M_["lid"], density=2.0)
        lb = m.bone(en + "l", eb, pivot=P)
        lb.box((P[0], P[1] - lh / 2, P[2] - 1.3), (bw + 0.6 * es, lh, 0.5), M_["lid"], density=2.0, variant=1)
        group = {"w1": k % 2, "w2": 2, "w3": 3}[name]
        EYES.append((en, name, k, group))


def build_model():
    EYES.clear()
    M_ = mats()
    m = Model("ophanim", density=1.0, bounds=(34, 34, (0, 0, 0)), alts=("judging",))
    root = m.bone("root")
    body = m.bone("body", root)

    # ---- the great outer wheel: spins in its own plane
    w1 = m.bone("w1", body)
    w1g = m.bone("w1g", w1)
    W = WHEELS["w1"]
    build_wheel(m, M_, w1g, W, "w1")
    ring(w1g, (0, 0, 0), W["R"] + W["rw"] / 2 + 1.4, 14, (2.6, 3.0, W["th"] * 0.6), M_["teeth"], axis="z", start=360 / 28)
    for sy_ in (1, -1):   # axle pins that carry the second wheel
        w1g.box((0, sy_ * 39.0, 0), (2.4, 3.6, 2.4), M_["pin"])
        w1g.box((0, sy_ * 40.6, 0), (4.2, 1.2, 4.2), M_["teeth"])

    # ---- gimbal wheel 2: pinned on the vertical diameter of w1, tumbles about it
    w2 = m.bone("w2", w1)
    w2g = m.bone("w2g", w2)
    W = WHEELS["w2"]
    build_wheel(m, M_, w2g, W, "w2")
    for sx in (1, -1):    # pins on the horizontal diameter carry wheel 3
        w2g.box((sx * 27.4, 0, 0), (3.2, 2.2, 2.2), M_["pin"])
        w2g.box((sx * 29.2, 0, 0), (1.0, 3.6, 3.6), M_["teeth"])
    for sy_ in (1, -1):   # bearing collars where the pins of w1 enter
        w2g.box((0, sy_ * 37.0, 0), (3.6, 1.6, W["th"] + 1.2), M_["teeth"])

    # ---- gimbal wheel 3: pinned on the horizontal diameter of w2, tumbles about it
    w3 = m.bone("w3", w2)
    W = WHEELS["w3"]
    build_wheel(m, M_, w3, W, "w3")
    for sx in (1, -1):
        w3.box((sx * 25.6, 0, 0), (1.4, 3.2, W["th"] + 1.0), M_["teeth"])

    # ---- counter-rotating toothed pair on an oblique axis
    cf = m.bone("cf", body, rot=CF_BIND)
    c1 = m.bone("c1", cf)
    ring(c1, (0, 0, -1.6), 16.0, 14, (7.5, 3.0, 2.4), M_["c_rim"], axis="z", density=1.5)
    ring(c1, (0, 0, -1.6), 18.6, 10, (2.2, 2.2, 2.0), M_["teeth"], axis="z")
    for k in range(2):
        c1.box((0, 0, -1.6), (29.0, 1.2, 1.0), M_["rail"], rot=(0, 0, k * 90 + 22.5), pivot=(0, 0, -1.6))
    c2 = m.bone("c2", cf)
    ring(c2, (0, 0, 1.6), 12.5, 12, (7.0, 2.6, 2.2), M_["c_rim2"], axis="z", density=1.5)
    ring(c2, (0, 0, 1.6), 10.4, 8, (2.0, 1.8, 1.8), M_["teeth"], axis="z")
    for k in range(3):
        c2.box((0, 0, 1.6), (22.0, 1.0, 0.8), M_["strut"], rot=(0, 0, k * 60), pivot=(0, 0, 1.6))

    # ---- core: a hovering seal of text, not an eye
    core = m.bone("core", body)
    core.box((0, 0, 0), (4.4, 4.4, 4.4), M_["gem"], rot=(45, 45, 0), pivot=(0, 0, 0))
    core.box((0, 0, 0), (3.2, 7.2, 3.2), M_["gem"], rot=(0, 45, 0), pivot=(0, 0, 0))
    ca = m.bone("core_a", core)
    ca.plane("z", (0, 0, 0), 17, 17, M_["seal"], density=4.0)
    cb = m.bone("core_b", core)
    cb.plane("x", (0, 0, 0), 14, 14, M_["seal2"], density=4.0)
    cc = m.bone("core_c", core)
    cc.plane("y", (0, 0, 0), 12, 12, M_["seal2"], density=4.0, variant=1)
    for k in range(6):
        g = tex.bitmap_cut(FW[(k * 7 + 3) % len(FW)], "#ffffff", glow=1.0, color2=WGOLD)
        cc.box((0, 0, -8.5), (2.6, 3.6, 0), g, rot=(0, k * 60, 0), pivot=(0, 0, 0), faces=("north", "south"))

    # ---- motion-blur disc (sweep only) and the departing ring of letters (depart only)
    blur = m.bone("blur", body)
    blur.plane("z", (0, 0, 0), 108, 108, M_["blur"], density=0.75)
    letters = m.bone("letters", root)
    letters.plane("y", (0, 0.2, 0), 84, 84, M_["ring_plane"], density=1.0)
    seqi = glyphs.seq(11, 16)
    for k in range(16):
        g = tex.bitmap_cut(FW[seqi[k] % len(FW)], WGOLD, glow=1.0, color2="#ffffff")
        letters.box((0, 5.5, -38), (6, 8.4, 0), g, rot=(0, k * 22.5, 0), pivot=(0, 0, 0), faces=("north", "south"))
    return m


# ---------------------------------------------------------------------------------- animations
def lids(a, eye, keys, smooth=False):
    a.rot(eye + "u", {t: (v, 0, 0) for t, v in keys.items()}, smooth)
    a.rot(eye + "l", {t: (-v, 0, 0) for t, v in keys.items()}, smooth)


def build_anims():
    A = []
    turn = Anim("turn", loop=True)                     # always on: wheel spin, seals, breathing bob
    turn.rot("w1", (0, 0, phase(0.55)))
    turn.rot("c1", (0, 0, phase(1.6)))
    turn.rot("c2", (0, 0, phase(-1.9)))
    turn.rot("core_a", (0, 0, life_spin(60)))
    turn.rot("core_b", (life_spin_neg(45), 0, 0))
    turn.rot("core_c", (0, life_spin(80), 0))
    turn.rot("letters", (0, life_spin(36), 0))
    turn.pos("body", (0, LIFE(1.6, 3.8), 0))
    A.append(turn)

    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    # ---- arrive: assembled from the inside out, one wheel at a time, then the eyes open
    ar = Anim("arrive", length=T_ARRIVE, loop="hold")
    ar.scl("core", {0: 0.0, 0.1: 0.0, 0.4: 1.5, 0.55: 1.0})
    ar.scl("cf", {0: 0.0, 0.3: 0.0, 0.6: 1.15, 0.72: 1.0})
    ar.rot("cf", {0: (0, 0, -160), 0.3: (0, 0, -160), 0.75: (ECF, 0, 0)})
    ar.scl("w3", {0: 0.0, 0.55: 0.0, 0.88: 1.12, 1.0: 1.0})
    ar.rot("w3", {0: (-170, 0, 0), 0.55: (-170, 0, 0), 1.0: (EW3, 0, 0)})
    ar.scl("w2g", {0: 0.0, 0.85: 0.0, 1.18: 1.1, 1.3: 1.0})
    ar.rot("w2", {0: (0, -170, 0), 0.85: (0, -170, 0), 1.3: (0, EW2, 0)})
    ar.scl("w1g", {0: 0.0, 1.15: 0.0, 1.5: 1.08, 1.65: 1.0})
    ar.rot("w1g", {0: (0, 0, -90), 1.15: (0, 0, -90), 1.65: (0, 0, 0)})
    ar.rot("body", {0: (0, 0, 0), 1.0: (0, 0, 0), 2.0: (EBX, EBY, EBZ)})
    ar.pos("root", {0: (0, 22, 0), 1.6: (0, -1.5, 0), 2.0: (0, 0, 0)})
    for t in (0.35, 0.65, 0.95, 1.25, 1.55):
        ar.sound(t, "clank")
    ar.sound(1.62, "chime")
    for i, (e, *_r) in enumerate(EYES):
        t0 = 1.62 + 0.016 * i
        lids(ar, e, {0: 0, t0: 0, t0 + 0.1: LID_OPEN + 10, t0 + 0.2: LID_OPEN})
    A.append(ar)

    # ---- survey: slow precession, gimbals tumbling, every eye group searching its own region
    sv = Anim("survey", length=T_SURVEY_LOOP, loop=True)
    sv.rot("w2", (0, EW2, 0))
    sv.rot("w3", (EW3, 0, 0))
    sv.rot("cf", (ECF, 0, 0))
    sv.rot("body", (EBX, EBY, EBZ))
    sv.scl("core", LIFE(0.08, 1.3, base=1.0))
    L = T_SURVEY_LOOP
    group_targets = {}
    for g in range(4):
        rng = random.Random(300 + g)
        ts, t = [], 0.0
        while t < L - 0.9:
            ts.append((t, (rng.uniform(-18, 18), rng.uniform(-30, 30))))
            t += rng.uniform(0.7, 1.4)
        group_targets[g] = ts
    for i, (e, wname, k, g) in enumerate(EYES):
        rng = random.Random(900 + i)
        ts = group_targets[g]
        d = 0.035 * (k // (2 if wname == "w1" else 1))
        jit = lambda: rng.uniform(-4, 4)    # noqa: E731
        first = (ts[0][1][0] + jit(), ts[0][1][1] + jit(), 0)
        keys, prev = {0.0: first}, first
        for (tt, (rx, ry)) in ts[1:]:
            cur = (rx + jit(), ry + jit(), 0)
            keys[round(tt + d, 3)] = prev
            keys[round(tt + d + 0.1, 3)] = cur
            prev = cur
        keys[round(L - 0.18, 3)] = prev
        keys[L] = first
        sv.rot(e, keys, smooth=False)
        lk = {0: LID_OPEN}
        bt = sorted(rng.uniform(0.3, L - 0.5) for _ in range(rng.choice((1, 2))))
        if len(bt) == 2 and bt[1] - bt[0] < 0.5:
            bt = bt[:1]
        for b in bt:
            lk.update({round(b, 3): LID_OPEN, round(b + 0.07, 3): 0, round(b + 0.2, 3): LID_OPEN})
        lk[L] = LID_OPEN
        lids(sv, e, lk)
    A.append(sv)

    # ---- lock: gimbals whirl into one plane, the plane turns to the route, every eye narrows
    lk = Anim("lock", length=T_LOCK, loop="hold")
    lk.rot("w2", {0: (0, 14, 0), 0.3: (0, -5, 0), 0.6: (0, 0, 0)})
    lk.rot("w3", {0: (-14, 0, 0), 0.3: (5, 0, 0), 0.6: (0, 0, 0)})
    lk.rot("cf", {0: (-40, 0, -25), 0.35: (-58, 0, -37), 0.6: CF_FLAT})
    lk.rot("body", {0: (0, 30, 0), 0.4: (0, 96, 0), 0.6: (0, 90, 0)})
    lk.pos("root", {0: (0, 0, 0), 0.25: (0, -2, 0), 0.6: (0, 1, 0)})
    lk.rot("root", {0: (0, 0, 0), 0.6: (-6, 0, 0)})
    lk.scl("core", {0: 1.0, 0.2: 0.7, 0.6: 1.3})
    for e, *_r in EYES:
        lk.rot(e, {0: (0, 0, 0)})
        lids(lk, e, {0: LID_OPEN, 0.15: 18, 0.3: LID_SQUINT}, smooth=True)
    A.append(lk)

    # ---- sweep: aligned blur, leaning into the cut
    sw = Anim("sweep", length=1.0, loop=True)
    sw.rot("w2", (0, 0, 0))
    sw.rot("w3", (0, 0, 0))
    sw.rot("cf", CF_FLAT)
    sw.rot("body", (0, 90, 0))
    sw.rot("root", (-12, 0, 0))
    sw.pos("root", (0, LIFE(0.5, 0.21), 0))
    sw.scl("core", LIFE(0.15, 0.3, base=1.3))
    for e, *_r in EYES:
        sw.rot(e, (0, 0, 0))
        lids(sw, e, {0: LID_WIDE})
    A.append(sw)

    # ---- verdict: contracts, then bursts open into an armillary sphere of three orthogonal wheels
    vd = Anim("verdict", length=T_VERDICT, loop="hold")
    vd.rot("body", {0: (0, 90, 0), 0.45: (0, 20, 0), 0.6: (0, 0, 0)})
    vd.rot("w2", {0: (0, 0, 0), 0.35: (0, -20, 0), 0.55: (0, 96, 0), 0.75: (0, 90, 0)})
    vd.rot("w3", {0: (0, 0, 0), 0.35: (20, 0, 0), 0.55: (96, 0, 0), 0.75: (90, 0, 0)})
    vd.rot("cf", {0: CF_FLAT, 0.55: (35, 0, 0)})
    vd.scl("body", {0: 1.0, 0.35: 0.84, 0.55: 1.25, 0.8: 1.16, 1.1: 1.18})
    vd.rot("root", {0: (-12, 0, 0), 0.4: (0, 0, 0)})
    vd.pos("root", {0: (0, 0, 0), 0.35: (0, 4, 0), 0.55: (0, -3, 0), 1.1: (0, -1, 0)})
    vd.scl("core", {0: 1.3, 0.35: 0.6, 0.55: 2.6, 1.1: 2.0})
    for e, *_r in EYES:
        vd.rot(e, (0, 0, 0))
        lids(vd, e, {0: LID_WIDE, 0.3: 15, 0.5: LID_WIDE + 6}, smooth=True)
    A.append(vd)

    # ---- depart: wheels separate, fold flat into one ring, become a ring of letters and rise away
    dp = Anim("depart", length=T_DEPART, loop="hold")
    for i, (e, *_r) in enumerate(EYES):
        t0 = 0.12 + 0.01 * i
        dp.rot(e, (0, 0, 0))
        lids(dp, e, {0: LID_OPEN, t0: LID_OPEN, t0 + 0.16: 0})
    dp.pos("w1g", {0: (0, 0, 0), 0.45: (0, 0, -10), 0.95: (0, 0, 0)})
    dp.pos("w2g", {0: (0, 0, 0), 0.45: (0, 0, 9), 0.95: (0, 0, 0)})
    dp.pos("w3", {0: (0, 0, 0), 0.45: (9, 0, 0), 0.95: (0, 0, 0)})
    dp.rot("w2", {0: (0, 90, 0), 0.45: (0, 140, 0), 0.95: (0, 180, 0)})
    dp.rot("w3", {0: (90, 0, 0), 0.45: (150, 0, 0), 0.95: (180, 0, 0)})
    dp.rot("body", {0: (0, 0, 0), 0.45: (25, 70, 10), 0.95: (90, 180, 0), 1.8: (90, 180, 0)})
    dp.scl("w1g", {0: 1.0, 0.95: 0.76, 1.12: 0.8, 1.28: 0.0})
    dp.scl("w2g", {0: 1.0, 0.95: 1.03, 1.12: 1.08, 1.28: 0.0})
    dp.scl("w3", {0: 1.0, 0.95: 1.5, 1.12: 1.55, 1.28: 0.0})
    dp.scl("cf", {0: 1.0, 0.6: 1.0, 1.0: 0.0})
    dp.scl("core", {0: 1.6, 0.9: 1.2, 1.0: 1.8, 1.15: 0.0})
    dp.scl("letters", {0: 0.0, 0.95: 0.0, 1.15: 1.0, 1.45: 1.25, 1.8: 0.0})
    dp.pos("letters", {0: (0, 0, 0), 1.15: (0, 0, 0), 1.8: (0, 28, 0)})
    dp.pos("root", {0: (0, 0, 0), 1.8: (0, 6, 0)})
    A.append(dp)
    return A


STATES = {0: ["hidden"], 1: ["arrive"], 2: ["survey"], 3: ["lock"], 4: ["sweep"], 5: ["verdict"], 6: ["depart"]}


def pre_anim():
    q = "q.property('grimoire:state')"
    s = SPEED
    tgt = (f"v.tgt = {q} == 4 ? {s[4]} : ({q} == 5 ? {s[5]} : ({q} == 3 ? {s[3]} : "
           f"({q} == 6 ? {s[6]} : ({q} == 1 ? {s[1]} : {s[2]}))));")
    return [tgt,
            "v.spd = v.spd + (v.tgt - v.spd) * math.min(1.0, q.delta_time * 2.2);",
            "v.ph = math.mod(v.ph + v.spd * q.delta_time, 36000.0);"]


# ---------------------------------------------------------------------------------- sounds
def hum(dur=1.6, base=55.0):
    t = sy.t_axis(dur)
    s = sy.osc(base, dur) * 0.6 + sy.osc(base * 1.013, dur) * 0.5
    s += sy.lowpass(sy.osc(base * 2.0, dur, "saw"), 380) * 0.35
    am = 1 + 0.35 * np.sin(2 * np.pi * 3.1 * t)
    for r, a in ((2.76, 0.16), (4.07, 0.11), (5.41, 0.08), (6.83, 0.05)):
        s += np.sin(2 * np.pi * base * r * t + r) * a * am
    s += sy.rumble(dur, 45) * 0.25
    return s * sy.env(dur, 0.25, 0.1, 0.9, 0.4)


def build_sounds(pack):
    clank = sy.at(0.8, (0.0, sy.thump(0.45, 170, 60, 0.6) * 0.8), (0.0, sy.bell(392.0, 0.7, inharm=1.45) * 0.45),
                  (0.0, sy.crack(0.15, 4500, 5) * 0.25))
    sy.save(pack, "dw_ophan_clank", sy.reverb(clank, 1.0, 0.3), max_distance=48,
            variants=[sy.reverb(sy.pitch(clank, 1.15), 1.0, 0.3), sy.reverb(sy.pitch(clank, 0.88), 1.0, 0.3)])
    arrive = sy.at(2.4, (0.0, sy.rumble(2.2, 50) * 0.5), (0.1, hum(2.2, 41.0) * 0.6),
                   (0.0, sy.whoosh(1.4, 3200, 300) * 0.35), (1.6, sy.shimmer(0.8, 2400, 14) * 0.3),
                   (1.65, sy.bell(659.3 * 1.07, 0.9, inharm=1.3) * 0.3))
    sy.save(pack, "dw_ophan_arrive", sy.reverb(arrive, 1.8, 0.4), max_distance=72)
    h = hum(1.6, 55.0)
    sy.save(pack, "dw_ophan_hum", sy.reverb(h, 0.8, 0.2), max_distance=56, volume=0.9)
    rng = np.random.default_rng(7)
    eyes = sy.at(1.0, *[(0.05 * i + rng.uniform(0, 0.02), sy.bell(f, 0.6, bright=1.6, inharm=1.2) * 0.35)
                        for i, f in enumerate((1903.0, 2219.0, 1661.0, 2531.0, 2087.0, 2876.0))])
    sy.save(pack, "dw_ophan_eyes", sy.reverb(eyes, 1.4, 0.4), max_distance=48)
    ping = sy.osc(sy.sweep(1650, 1180, 0.35, 0.5)) * sy.decay(0.35, 0.09)
    ping = sy.at(0.6, (0.0, ping), (0.0, sy.pluck(3300, 0.3, 0.9) * 0.25))
    sy.save(pack, "dw_ophan_scan", sy.reverb(ping, 1.0, 0.45), max_distance=48, volume=0.8)
    mark = sy.at(0.6, (0.0, sy.bell(1480.0, 0.45, bright=1.4, inharm=1.15) * 0.6), (0.06, sy.bell(2217.0, 0.45, inharm=1.15) * 0.4),
                 (0.0, sy.crack(0.12, 7000, 4) * 0.15))
    sy.save(pack, "dw_ophan_mark", sy.reverb(mark, 0.9, 0.35), max_distance=40, volume=0.8)
    hl = hum(0.9, 55.0) * np.linspace(1, 0.4, int(sy.SR * 0.9))
    clicks = sy.crack(0.6, 3200, 18) * 0.5
    lock = sy.at(1.0, (0.0, sy.pitch(hl, 0.8) * 0.7), (0.0, clicks), (0.45, sy.thump(0.4, 140, 70, 0.5) * 0.6),
                 (0.45, sy.shimmer(0.5, 3000, 8) * 0.3))
    sy.save(pack, "dw_ophan_lock", sy.reverb(lock, 1.0, 0.3), max_distance=56)
    sw = sy.at(1.2, (0.0, sy.whoosh(1.1, 180, 2600, 1.2) * 0.8), (0.0, hum(1.1, 82.0) * 0.4), (0.3, sy.whoosh(0.7, 900, 4200) * 0.35))
    sy.save(pack, "dw_ophan_sweep", sy.reverb(sw, 0.9, 0.25), max_distance=56,
            variants=[sy.reverb(sy.pitch(sw, 1.1), 0.9, 0.25)])
    hit = sy.at(1.6, (0.0, sy.bell(311.1 * 1.03, 1.5, bright=1.3, inharm=1.25) * 0.7), (0.0, sy.thump(0.5, 150, 50, 0.6) * 0.6),
                (0.0, sy.crack(0.3, 6000, 10) * 0.35), (0.01, sy.bell(1244.0, 0.8, inharm=1.25) * 0.25))
    sy.save(pack, "dw_ophan_bell", sy.reverb(hit, 1.4, 0.35), max_distance=56,
            variants=[sy.reverb(sy.pitch(hit, 1.12), 1.4, 0.35), sy.reverb(sy.pitch(hit, 0.92), 1.4, 0.35)])
    vd = sy.at(2.4, (0.0, sy.thump(0.4, 90, 60, 0.2) * 0.4), (0.45, sy.thump(1.2, 120, 28, 0.8)),
               (0.47, sy.bell(207.7, 2.0, bright=1.4, inharm=1.3) * 0.7), (0.47, sy.bell(277.2 * 1.04, 1.8, inharm=1.3) * 0.5),
               (0.48, sy.bell(830.6, 1.4, inharm=1.3) * 0.3), (0.5, sy.shimmer(1.4, 2600, 22) * 0.35),
               (0.45, sy.crack(0.6, 5000, 16) * 0.3))
    sy.save(pack, "dw_ophan_verdict", sy.reverb(vd, 2.4, 0.45), max_distance=80)
    gl = sy.osc(sy.sweep(880, 220, 1.4, 0.7)) * sy.env(1.4, 0.05, 0.1, 0.8, 0.5) * 0.25
    dep = sy.at(2.2, (0.0, hum(1.2, 49.0) * np.linspace(1, 0, int(sy.SR * 1.2)) * 0.6), (0.2, gl),
                (0.3, sy.bell(554.4 * 1.05, 1.0, inharm=1.35) * 0.3), (0.9, sy.shimmer(1.2, 2200, 18)[::-1] * 0.45),
                (0.95, sy.whoosh(1.0, 400, 3600) * 0.35))
    sy.save(pack, "dw_ophan_depart", sy.reverb(dep, 2.0, 0.45), max_distance=72)


# ---------------------------------------------------------------------------------- particles
def build_particles(pack):
    fx = particles(pack)
    fx.effect("dw_ophan_scan", "glow", count=1, life=(0.35, 0.5), size=(0.32, 0.08),
              colors=["#ffffffff", "#fff3c4dd", "#c9a24a00"])
    fx.effect("dw_ophan_ping", "ringthin", count=1, life=(0.5, 0.6), size=(0.3, 2.4), facing="emitter_transform_xz",
              colors=["#ffffffff", "#9fb3ffcc", "#2b3f8f00"])
    fx.effect("dw_ophan_eye", "eye", count=1, life=(0.7, 0.9), size=(0.45, 0.75), colors=["#fff3c4ff", "#fff3c4ff", "#c9a24a00"])
    fx.effect("dw_ophan_route", "glow", count=1, life=(0.9, 1.15), size=(0.26, 0.1),
              colors=["#ffffffff", "#fff3c4ee", "#c9a24a00"])
    fx.effect("dw_ophan_rim", "slash", count=2, life=(0.22, 0.38), size=(0.9, 0.3), shape=("sphere", 0.5), speed=(0.5, 1.5),
              colors=["#ffffffff", "#ffe9a3cc", "#c9a24a00"], spin=(360, 0))
    fx.effect("dw_ophan_sparks", "spark", count=8, life=(0.3, 0.6), size=(0.13, 0.0), shape=("sphere", 0.3),
              speed=(3.0, 7.0), accel=(0, -7, 0), drag=0.9, colors=["#ffffffff", "#ffe9a3ff", "#c9a24a00"], spin=(360, 180))
    fx.effect("dw_ophan_impact", "star", count=1, life=(0.3, 0.4), size=(0.6, 2.2), colors=["#ffffffff", "#fff3c400"])
    fx.effect("dw_ophan_letters", None, sprites=[f"glyph{i}" for i in range(1, 9)], count=6, life=(1.0, 1.6),
              size=(0.22, 0.1), shape=("disc", 3.0, "surface"), direction=(0, 1, 0), speed=(0.8, 1.6), drag=0.5,
              colors=["#ffffffff", "#fff3c4ff", "#c9a24a00"])


def build(pack):
    build_particles(pack)
    m = build_model()
    anims = build_anims()
    pack.actor("ophanim", m, anims, STATES, always=["turn"], scale=2.0, lifetime=120,
               init=["v.spd = 0.0;", "v.ph = 0.0;", "v.tgt = 0.0;"], pre_anim=pre_anim(),
               visibility=[{"letters": "q.property('grimoire:state') == 6"},
                           {"blur": "q.property('grimoire:state') == 4"}],
               sounds={"clank": "grimoire.dw_ophan_clank", "chime": "grimoire.dw_ophan_eyes"},
               display="Ophanim", blend=0.35)
    build_sounds(pack)
    by = {a.name: a for a in anims}
    tr = by["turn"]
    hide = ("letters", "blur")
    pack.preview("ophanim_a", m, [[(by["survey"], 1.3), (tr, 1.3)], [(by["survey"], 3.7), (tr, 3.7)],
                                  [(by["lock"], T_LOCK), (tr, 2.0)], [(by["verdict"], T_VERDICT), (tr, 2.0)]],
                 views=((25, 18), (120, 10), (0, 80)), cell=(380, 380), hide=hide)
    pack.preview("ophanim_b", m, [[(by["arrive"], t), (tr, t)] for t in (0.5, 0.95, 1.4, 1.75)],
                 views=((25, 25),), cell=(300, 300), hide=hide)
    pack.preview("ophanim_d", m, [[(by["depart"], t), (tr, t)] for t in (0.45, 0.95, 1.2, 1.5)],
                 views=((25, 25),), cell=(300, 300), hide=("blur",), skin="judging")
    pack.preview("ophanim_c", m, [[(by["sweep"], 0.0), (tr, 0.5)]], views=((90, 8), (30, 20)), cell=(420, 420), hide=("letters",),
                 skin="judging")
    print(f"    ophanim: {m.cube_count()} cubes, {len(m.order)} bones, tex {m.tex_size}, eyes {len(EYES)}")
