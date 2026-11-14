"""DN05 constructs released by the sleeping city.

Phase II (dream, telegraphed):
  dn_city_stair      staircase that unrolls from the city down to the ground; its pavilion is cover
  dn_city_balcony    balcony block that breaks off and falls on a telegraphed spot
  dn_city_street     a rolled-up street that rolls across the field, unrolling road behind it
Phase III (nightmare hunters):
  dn_city_door       flying doorframe -- swoops; whoever it passes through is thrown out the other side
  dn_city_window     window with an eye -- hovers, blinks, stares (beam), finally shatters into glass rain
  dn_city_corridor   folding corridor -- unfolds along the ground to a target, then snaps shut (restraint)
  dn_city_stairfall  a stair-flight that slams down chunk after chunk along a line
  dn_city_fragment   living roof-and-chimney fragment on baluster legs -- hops and bites
State tables are the *_STATES dicts below; the spell mirrors them.
"""
from __future__ import annotations

import math

from kit import glyphs, tex
from kit.anim import LIFE, Anim
from kit.geo import Mat, Model, ring
from kit.parts import sym

from .dn_city import AGED, BLUE, BURG, GOLD, INDIGO, MAUVE, PINK, mats, spin

# ---- timings (seconds), mirrored in src/spells/dn05_sleeping_city.ts
T_STAIR_DOWN, T_STAIR_UP = 1.6, 1.2
T_BAL_DROP, T_BAL_HIT = 0.8, 0.9
T_ST_APPEAR, T_ST_CRUMBLE = 0.6, 0.6
T_DOOR_ARRIVE, T_DOOR_SWOOP, T_DOOR_DEPART = 1.0, 0.8, 0.8
T_WIN_ARRIVE, T_WIN_BLINK, T_WIN_STARE, T_WIN_SHATTER = 0.8, 0.8, 1.0, 0.7
T_COR_UNFOLD, T_COR_SNAP, T_COR_FOLD = 1.0, 0.35, 0.8
T_SF_SLAM, T_SF_SINK = 2.2, 0.8
SF_CHUNKS, SF_FIRST, SF_STEP = 5, 0.45, 0.3      # chunk k lands at SF_FIRST + k * SF_STEP
T_FR_ARRIVE, T_FR_HOP, T_FR_BITE, T_FR_CRUMBLE = 0.8, 0.6, 0.5, 0.7

STAIR_STATES = {0: ["hidden"], 1: ["descend"], 2: ["stand"], 3: ["retract"]}
BAL_STATES = {0: ["hidden"], 1: ["drop"], 2: ["impact"]}
STREET_STATES = {0: ["hidden"], 1: ["appear"], 2: ["roll"], 3: ["crumble"]}
DOOR_STATES = {0: ["hidden"], 1: ["arrive"], 2: ["fly"], 3: ["swoop"], 4: ["depart"]}
WIN_STATES = {0: ["hidden"], 1: ["arrive"], 2: ["hover"], 3: ["blink"], 4: ["stare"], 5: ["shatter"]}
COR_STATES = {0: ["hidden"], 1: ["unfold"], 2: ["snap"], 3: ["clamp"], 4: ["fold"]}
SF_STATES = {0: ["hidden"], 1: ["slam"], 2: ["rest"], 3: ["sink"]}
FR_STATES = {0: ["hidden"], 1: ["arrive"], 2: ["idle"], 3: ["hop"], 4: ["bite"], 5: ["crumble"]}


def forced(mat, alt="nightmare"):
    """Paint a skinned material permanently as one of its skins."""
    def fn(ctx):
        old = ctx.alt
        ctx.alt = alt
        try:
            return mat.fn(ctx)
        finally:
            ctx.alt = old
    return Mat(fn, mat.key + "|forced" + alt, mode=mat.mode, spatial=mat.spatial, directional=mat.directional,
               density=mat.density)


_N = None


def nm():
    global _N
    if _N is None:
        _N = {k: forced(v) for k, v in mats().items()}
    return _N


def hidden_anim():
    a = Anim("hidden", loop=True)
    a.scl("root", 0.0)
    return a


# ====================================================================== Phase II: cover staircase
def build_stair():
    M_ = mats()
    m = Model("dn_city_stair", density=1.0, bounds=(20, 24, (0, 8, 3)))
    root = m.bone("root")
    flights = []
    for k in range(6):
        yt, zt = 96 - 16 * k, 60 - 10 * k
        b = m.bone(f"fl_{k + 1}", root, pivot=(0, yt, zt))
        for i in range(4):
            b.box((0, yt - 4 * i - 2.6, zt - 2.5 * i - 1.25), (14, 1.4, 3.4), M_["marble"], variant=(i + k) % 3)
            b.box((0, yt - 4 * i - 3.6, zt - 2.5 * i - 2.6), (13, 2.6, 0.8), M_["gold"])          # gilt riser
        ang = math.degrees(math.atan2(16, 10))
        for sx in (-1, 1):
            b.box((sx * 7.6, yt - 7.0, zt - 5.0), (1.2, 2.2, 19.5), M_["gold"], rot=(-ang, 0, 0))   # stringer / rail
            b.box((sx * 7.6, yt - 3.0, zt - 5.0), (0.6, 0.6, 19.0), M_["gold_glow"], rot=(-ang, 0, 0))
            for j in range(2):
                b.box((sx * 7.6, yt - 4 * j * 2 - 3.0, zt - 5 * j - 1.5), (0.6, 4.0, 0.6), M_["gold"])
        b.box((0, yt - 9.5, zt - 4.0), (12, 1.0, 18), M_["under"], rot=(-ang, 0, 0))                  # soffit
        if k % 2 == 1:
            b.box((0, yt - 14.0, zt - 5.0), (2.0, 2.0, 2.0), M_["lamp"], rot=(45, 45, 0))
        flights.append(b.name)
    # the pavilion at the foot: four columns, a pink roof, golden lanterns -- allies shelter here
    pav = m.bone("pavilion", root, pivot=(0, 0, -6))
    pav.box((0, 1.0, -8), (30, 2.0, 20), M_["marble"], mats={"up": M_["floor"]})
    for sx in (-1, 1):
        for z in (-16, 0):
            pav.box((sx * 11, 15, z), (3, 26, 3), M_["marble"], variant=1)
            pav.box((sx * 11, 28.4, z), (4.2, 1.6, 4.2), M_["gold"])
            pav.box((sx * 11, 2.6, z), (4.2, 1.6, 4.2), M_["gold"])
    pav.box((0, 30.5, -8), (28, 2.4, 20), M_["gold"])
    s = 16.0
    for sx in (-1, 1):
        pav.box((sx * s / 2, 34.5, -8), (s / math.cos(math.radians(30)) + 1, 1.4, 23), M_["roof"], rot=(0, 0, -sx * 30))
    pav.box((0, 39.6, -8), (1.4, 1.4, 24), M_["gold_glow"])
    pav.box((0, 26.0, -16), (2.6, 2.6, 2.6), M_["lamp"], rot=(45, 45, 0))
    pav.plane("z", (0, 34.5, -19.6), 6, 6, M_["moon"])
    return m, flights


def stair_anims(flights):
    A = [hidden_anim()]
    down = Anim("descend", length=T_STAIR_DOWN, loop="hold")
    for k, b in enumerate(flights):
        t0 = 0.05 + 0.19 * k
        down.scl(b, {0: (1, 0, 0), t0: (1, 0, 0), t0 + 0.2: (1, 1.07, 1.07), t0 + 0.3: 1.0})
        down.rot(b, {0: (30, 0, 0), t0: (30, 0, 0), t0 + 0.24: (-4, 0, 0), t0 + 0.32: (0, 0, 0)})
    down.scl("pavilion", {0: 0.0, 1.15: 0.0, 1.4: (1.1, 1.15, 1.1), T_STAIR_DOWN: 1.0})
    stand = Anim("stand", loop=True)
    for k, b in enumerate(flights):
        stand.pos(b, (0, LIFE(0.5, 3.0, k * 0.12), 0))
    stand.scl("pavilion", (1, LIFE(0.015, 2.0, base=1.0), 1))
    up = Anim("retract", length=T_STAIR_UP, loop="hold")
    up.scl("pavilion", {0: 1.0, 0.1: 1.08, 0.3: 0.0})
    n = len(flights)
    for k, b in enumerate(flights):
        t0 = 0.15 + 0.15 * (n - 1 - k)
        up.scl(b, {0: 1.0, t0: 1.0, t0 + 0.2: (1, 0, 0)})
    A += [down, stand, up]
    return A


# ====================================================================== Phase II: falling balcony
def build_balcony():
    M_ = mats()
    m = Model("dn_city_balcony", density=1.0, bounds=(6, 6, (0, 1, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 8, 0))
    slab = m.bone("slab", body, pivot=(0, 0, 0))
    slab.box((0, 1, -2), (26, 2.4, 16), M_["marble"], mats={"up": M_["floor"]})
    for x in (-9, 0, 9):
        slab.box((x, -2.2, 2), (3, 4, 8), M_["under"], rot=(-30, 0, 0))
        slab.box((x, -5.0, 4.5), (1.6, 1.6, 1.6), M_["gold"])
    slab.box((0, -3.0, -2), (2, 2, 2), M_["lamp"], rot=(45, 45, 0))
    rail = m.bone("rail", body, pivot=(0, 2, -9))
    rail.box((0, 9.4, -9.6), (26, 1.4, 1.6), M_["gold"])
    for k in range(9):
        rail.box((-12 + k * 3, 5.8, -9.6), (1.2, 6.0, 1.2), M_["marble"], variant=k % 2)
    for sx in (-1, 1):
        rail.box((sx * 12.6, 9.4, -2), (1.6, 1.4, 15), M_["gold"])
    flw = m.bone("flowers", rail, pivot=(0, 10, -10))
    flw.box((0, 11.0, -10.2), (14, 2.0, 3.0), M_["wall2"])
    flw.box((0, 13.2, -10.2), (13, 3.4, 2.6), tex.foliage("#c97a9e", "#f2b8cf", holes=0.2, flowers="#fff4c8"))
    wall = m.bone("wall", body, pivot=(0, 2, 6))
    wall.box((0, 12, 6.5), (26, 20, 3), M_["wall"], mats={"north": M_["wall2"]})
    wall.plane("z", (0, 10.5, 4.8), 8, 14, M_["door"])
    wall.box((0, 23.5, 6.5), (28, 3, 4), M_["gold"])
    wall.box((0, 26.5, 6.5), (10, 3, 3), M_["roof"], rot=(0, 0, 45))
    return m


def balcony_anims():
    A = [hidden_anim()]
    drop = Anim("drop", length=T_BAL_DROP, loop="hold")       # breaks off, tumbles slowly like a dream object
    drop.rot("body", {0: (0, 0, 0), 0.15: (-12, 0, 6), 0.45: (18, 30, -10), T_BAL_DROP: (8, 70, 4)})
    drop.scl("root", {0: 0.3, 0.2: 1.1, 0.35: 1.0})
    drop.pos("flowers", {0: (0, 0, 0), T_BAL_DROP: (0, 3, -1)})
    hit = Anim("impact", length=T_BAL_HIT, loop="hold")       # squash, then the pieces scatter and fade
    hit.rot("body", {0: (8, 70, 4), 0.12: (0, 70, 0)})
    hit.scl("body", {0: 1.0, 0.08: (1.25, 0.55, 1.25), 0.2: (1.0, 1.0, 1.0)})
    hit.pos("rail", {0: (0, 0, 0), 0.2: (0, 6, -8), T_BAL_HIT: (0, -6, -18)})
    hit.rot("rail", {0: (0, 0, 0), T_BAL_HIT: (-70, 0, 20)})
    hit.pos("wall", {0: (0, 0, 0), 0.25: (0, 4, 8), T_BAL_HIT: (0, -10, 14)})
    hit.rot("wall", {0: (0, 0, 0), T_BAL_HIT: (60, 0, -15)})
    hit.pos("flowers", {0: (0, 3, -1), 0.3: (6, 14, -6), T_BAL_HIT: (10, 2, -10)})
    hit.scl("root", {0: 1.0, 0.45: 1.0, T_BAL_HIT: 0.0})
    A += [drop, hit]
    return A


# ====================================================================== Phase II: rolling street
def build_street():
    M_ = mats()
    m = Model("dn_city_street", density=1.0, bounds=(10, 6, (0, 1, 2)))
    root = m.bone("root")
    roll = m.bone("roll", root, pivot=(0, 10, 0))
    ring(roll, (0, 10, 0), 8.6, 12, (4.8, 2.4, 30), M_["street"], axis="x", cycle=2)
    ring(roll, (0, 10, 0), 6.0, 8, (4.8, 2.0, 26), M_["under"], axis="x")
    cap = tex.magic_circle(list(glyphs.DREAM.values()), "#fff3d8", GOLD, bands=((0.6, 0.9, 8),), lines=(0.55, 0.96),
                           core=0.15, key="dncstreetcap")
    for sx in (-1, 1):
        roll.plane("x", (sx * 15.2, 10, 0), 21, 21, cap, density=2.0)
    roll.box((0, 10, 0), (34, 2.0, 2.0), M_["gold_glow"])
    tail = m.bone("tail", root, pivot=(0, 0, 4))
    tail.cube((-13, 0.2, 4), (26, 1.0, 44), M_["street"])
    for sx in (-1, 1):
        tail.cube((sx * 13.5 - 0.6, 0.0, 4), (1.2, 1.8, 44), M_["gold"])
        for z in (16, 38):
            tail.box((sx * 13.5, 4.5, z), (0.8, 8.0, 0.8), M_["gold"])
            tail.box((sx * 13.5, 9.2, z), (2.0, 2.0, 2.0), M_["lamp"], rot=(0, 45, 0))
    return m


def street_anims():
    A = [hidden_anim()]
    app = Anim("appear", length=T_ST_APPEAR, loop="hold")
    app.pos("root", {0: (0, 60, 0), 0.3: (0, 0, 0), 0.42: (0, 5, 0), T_ST_APPEAR: (0, 0, 0)})
    app.scl("roll", {0: 0.2, 0.3: (1.15, 0.85, 0.85), 0.45: 1.0})
    app.scl("tail", {0: (1, 1, 0), 0.3: (1, 1, 0), T_ST_APPEAR: (1, 1, 0.2)})
    rl = Anim("roll", loop=True)
    rl.rot("roll", (spin(-430), 0, 0))
    rl.scl("tail", (1, 1, 1))
    rl.pos("root", (0, LIFE(0.6, 0.25), 0))
    cr = Anim("crumble", length=T_ST_CRUMBLE, loop="hold")
    cr.scl("roll", {0: 1.0, 0.15: 1.2, T_ST_CRUMBLE: 0.0})
    cr.rot("roll", {0: (0, 0, 0), T_ST_CRUMBLE: (-200, 0, 0)})
    cr.scl("tail", {0: 1.0, 0.4: (1, 0, 1)})
    A += [app, rl, cr]
    return A


# ====================================================================== Phase III: flying doorframe
def build_door():
    N = nm()
    m = Model("dn_city_door", density=1.0, bounds=(8, 8, (0, 2, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 22, 0))
    body.box((-9.5, 22, 0), (3.4, 48, 4.4), N["marble"])
    body.box((9.5, 22, 0), (3.4, 48, 4.4), N["marble"], variant=1)
    body.box((0, 47.5, 0), (24, 4, 5.4), N["gold"])
    body.box((0, 51, 0), (10, 4.4, 4.0), N["roof"], rot=(0, 0, 45))
    body.box((0, -1.0, 0), (22, 2.0, 6.0), N["marble"], variant=2)
    body.plane("z", (0, 51, -2.4), 4.5, 4.5, N["moon"])
    for sx in (-1, 1):
        for y in (8, 36):
            body.box((sx * 9.5, y, -2.6), (2.0, 2.0, 1.0), N["lamp"])
    import numpy as np

    def void2(ctx):
        t = tex.tile(ctx, INDIGO, 0.9, 0.3)
        k0, k1 = tex.rgb("#0c0b1c"), tex.rgb(MAUVE)
        t[..., :3] = tex.mix(k1, k0, ctx.V[..., None])
        ix, iy = tex.px(ctx)
        st = tex._hash(ix, iy, 911) > 0.965
        t[..., :3] = np.where(st[..., None], tex.rgb("#ffd0f0"), t[..., :3])
        t[..., 3] = np.where(st, 1.0, 0.86)
        return t
    vb = m.bone("void", body)
    vb.plane("z", (0, 22.5, 0.6), 15.6, 45, Mat(void2, "dncvoid", mode="blend"))
    leaf = m.bone("leaf", body, pivot=(-7.8, 0, -0.8))
    leaf.plane("z", (0, 22.5, -0.8), 15.6, 45, N["door"])
    for s, sx in (("r", 1), ("l", -1)):
        par = body
        for i in range(3):
            b = m.bone(f"rib_{s}_{i + 1}", par, pivot=(sx * 11, 49 - i * 9, 1))
            b.plane("x", (sx * 11, 49 - i * 9 - 4.5, 1), 3.4, 9, N["fabric"], variant=i % 2)
            par = b
    return m


def door_anims():
    A = [hidden_anim()]
    ribs = [[f"rib_{s}_{i + 1}" for i in range(3)] for s in "rl"]
    always = Anim("flutter", loop=True)
    for ch in ribs:
        for i, b in enumerate(ch):
            always.rot(b, (LIFE(14 + 6 * i, 0.9, -i * 0.15), 0, LIFE(10, 1.3, i * 0.2)))
    A.append(always)
    arr = Anim("arrive", length=T_DOOR_ARRIVE, loop="hold")
    arr.scl("body", {0: (1, 0, 1), 0.25: (1, 0.2, 1), 0.65: (1.05, 1.15, 1), T_DOOR_ARRIVE: 1.0})
    arr.rot("leaf", {0: (0, 0, 0), 0.6: (0, 0, 0), 0.8: (0, -100, 0), T_DOOR_ARRIVE: (0, -70, 0)})
    arr.rot("body", {0: (0, 180, 0), 0.7: (0, 0, 0)})
    fly = Anim("fly", loop=True, length=1.2)
    fly.rot("leaf", {0: (0, -70, 0), 0.6: (0, -20, 0), 1.2: (0, -70, 0)})
    fly.rot("body", (LIFE(8, 2.2), 0, LIFE(12, 1.8)))
    fly.pos("body", (0, LIFE(2.0, 1.2), 0))
    sw = Anim("swoop", length=T_DOOR_SWOOP, loop="hold")     # leaf flung wide, slams as the victim passes, flies open
    sw.rot("leaf", {0: (0, -70, 0), 0.2: (0, -120, 0), 0.38: (0, -2, 0), 0.5: (0, -20, 0), T_DOOR_SWOOP: (0, -110, 0)})
    sw.rot("body", {0: (-20, 0, 0), 0.38: (15, 0, 0), T_DOOR_SWOOP: (-10, 0, 0)})
    sw.scl("body", {0: 1.0, 0.38: (1.12, 0.92, 1.0), 0.5: 1.0})
    dep = Anim("depart", length=T_DOOR_DEPART, loop="hold")
    dep.rot("leaf", {0: (0, -110, 0), 0.3: (0, 0, 0)})
    dep.scl("body", {0: 1.0, 0.35: (1, 1, 1), T_DOOR_DEPART: (0.0, 1.4, 0.0)})
    dep.rot("body", {0: (0, 0, 0), T_DOOR_DEPART: (0, 540, 0)})
    A += [arr, fly, sw, dep]
    return A


# ====================================================================== Phase III: window eye
def build_window():
    N = nm()
    m = Model("dn_city_window", density=1.5, bounds=(8, 8, (0, 0, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 0, 0))
    fr = N["marble"]
    for sx in (-1, 1):
        body.box((sx * 11, 0, 0), (3, 34, 4), fr)
    body.box((0, -17.5, -0.5), (26, 3, 6), N["gold"])
    for k in range(5):     # pointed arch from stepped blocks
        w = 22 - k * 4.8
        body.box((0, 17 + k * 2.2, 0), (w + 3, 2.2, 3.6), fr, variant=k % 2)
    body.box((0, 28.5, 0), (1.4, 5, 1.4), N["gold_glow"])
    glass = tex.alt(tex.crystal("#b8a0d8", "#3a2a5a", "#ffe0f0", a=0.65, glow=0.35), nightmare=tex.crystal("#b8a0d8", "#3a2a5a", "#ffe0f0", a=0.65, glow=0.35))
    panes = []
    for k, (x, y) in enumerate(((-5, 10), (5, 10), (-5, -10), (5, -10))):
        pb = m.bone(f"pane_{k + 1}", body, pivot=(x, y, 0.4))
        pb.plane("z", (x, y, 0.4), 9.4, 11, glass, variant=k % 3)
        panes.append(pb.name)
    for y in (0.5, 15.5, -15.5):
        body.box((0, y, 0), (19, 1.2, 1.4), N["gold"])
    body.box((0, 0, 0), (1.2, 32, 1.4), N["gold"])
    eye = m.bone("eye", body, pivot=(0, 0, -1.2))
    eye.plane("z", (0, 0, -1.2), 16, 11, tex.eye_mat(iris="#d0508a", sclera="#f2e8d6", pupil="#0c0814", lid=BURG, glow=1.0, slit=True,
                                                    ring="#ffe0ec"), density=3.0)
    lid = tex.fabric("#7a3446", "#5a2232", stripe_w=1, weave=0.12)
    lt = m.bone("lid_t", eye, pivot=(0, 6.0, -1.6))
    lt.cube((-8.4, 0.0, -1.6), (16.8, 6.0, 0), lid)
    lb = m.bone("lid_b", eye, pivot=(0, -6.0, -1.6))
    lb.cube((-8.4, -6.0, -1.6), (16.8, 6.0, 0), lid, variant=1)
    for s, sx in (("r", 1), ("l", -1)):
        sh = m.bone(f"sh_{s}", body, pivot=(sx * 12.5, 0, -1.5))
        sh.cube((sx * 12.5 + (0 if sx > 0 else -11), -15, -1.5), (11, 30, 1.0),
                tex.banded(N["wall3"], "#3a2440", every=3, width=1), variant=1)
        sh.box((sx * 18, 0, -2.2), (1.2, 1.2, 1.2), N["lamp"])
    cur = m.bone("curtain", body, pivot=(0, 15, -2.8))
    cur.plane("z", (0, 11, -2.8), 22, 8, N["fabric"])
    teeth = tex.bitmap_cut(["# # # # # #", "# # # # # #", " # # # # # ", " #   #   # "], "#f2e8d6", glow=0.2, color2="#bcaeb8")
    body.plane("z", (0, -20.5, -0.5), 22, 4, teeth)
    return m, panes


def window_anims(panes):
    A = [hidden_anim()]
    bob = Anim("bob", loop=True)
    bob.pos("body", (LIFE(1.2, 3.1), LIFE(2.0, 2.2), 0))
    bob.rot("body", (LIFE(4, 2.9), 0, LIFE(5, 3.7)))
    bob.rot("curtain", (LIFE(10, 1.4), 0, 0))
    A.append(bob)
    arr = Anim("arrive", length=T_WIN_ARRIVE, loop="hold")
    arr.scl("body", {0: 0.0, 0.3: (1.2, 0.3, 1.0), 0.55: (0.95, 1.1, 1.0), T_WIN_ARRIVE: 1.0})
    sym(arr, "sh_{s}", rot={0: (0, 0, 0), 0.4: (0, 0, 0), 0.65: (0, -120, 0), T_WIN_ARRIVE: (0, -100, 0)})
    arr.scl("lid_t", {0: 1.0, 0.6: 1.0, T_WIN_ARRIVE: (1, 0.05, 1)})
    arr.scl("lid_b", {0: 1.0, 0.6: 1.0, T_WIN_ARRIVE: (1, 0.05, 1)})
    hov = Anim("hover", loop=True, length=2.0)
    sym(hov, "sh_{s}", rot={0: (0, -100, 0), 1.0: (0, -70, 0), 2.0: (0, -100, 0)})
    hov.scl("lid_t", (1, 0.05, 1))
    hov.scl("lid_b", (1, 0.05, 1))
    hov.pos("eye", (LIFE(1.2, 1.7), LIFE(0.8, 2.3), 0))
    blink = Anim("blink", length=T_WIN_BLINK, loop="hold")
    for lid in ("lid_t", "lid_b"):
        blink.scl(lid, {0: (1, 0.05, 1), 0.12: (1, 1.0, 1), 0.24: (1, 0.05, 1), 0.42: (1, 0.05, 1), 0.52: (1, 1.0, 1),
                        0.64: (1, 0.05, 1), T_WIN_BLINK: (1, 0.05, 1)}, smooth=False)
    sym(blink, "sh_{s}", rot={0: (0, -100, 0), 0.12: (0, -10, 0), 0.3: (0, -100, 0), 0.52: (0, -10, 0), 0.7: (0, -100, 0)})
    blink.sound(0.12, "blink")
    blink.sound(0.52, "blink")
    stare = Anim("stare", length=T_WIN_STARE, loop="hold")
    stare.scl("eye", {0: 1.0, 0.3: 0.85, 0.45: 1.45, T_WIN_STARE: 1.3})
    stare.pos("eye", {0: (0, 0, 0), 0.45: (0, 0, -4), T_WIN_STARE: (0, 0, -3)})
    stare.pos("body", {0: (0, 0, 0), 0.3: (0, 0, -2), 0.45: (0, 0, 4), T_WIN_STARE: (0, 0, 2)})
    sym(stare, "sh_{s}", rot={0: (0, -100, 0), 0.45: (0, -170, 0), T_WIN_STARE: (0, -150, 0)})
    stare.scl("lid_t", (1, 0.05, 1))
    stare.scl("lid_b", (1, 0.05, 1))
    sh = Anim("shatter", length=T_WIN_SHATTER, loop="hold")
    for k, p in enumerate(panes):
        sx, sy_ = (-1 if k % 2 == 0 else 1), (1 if k < 2 else -1)
        sh.pos(p, {0: (0, 0, 0), 0.15: (sx * 6, sy_ * 4 + 4, -6), T_WIN_SHATTER: (sx * 10, -40, -8)})
        sh.rot(p, {0: (0, 0, 0), T_WIN_SHATTER: (120 * sx, 60, 80)})
    sh.scl("eye", {0: 1.3, 0.1: 1.7, 0.3: 0.0})
    sh.scl("body", {0: 1.0, 0.3: 1.0, T_WIN_SHATTER: 0.0})
    sym(sh, "sh_{s}", rot={0: (0, -150, 0), T_WIN_SHATTER: (60, -260, 0)})
    A += [arr, hov, blink, stare, sh]
    return A


# ====================================================================== Phase III: folding corridor
COR_SEGS, COR_LEN = 5, 16.0


def build_corridor():
    N = nm()
    m = Model("dn_city_corridor", density=1.0, bounds=(12, 8, (0, 1, -5)))
    root = m.bone("root")
    paper = tex.fabric(MAUVE, "#5a3a5e", stripe_w=2, weave=0.05)
    carpet = tex.banded(tex.fabric(BURG, "#5a2430", stripe_w=3), "#c9a24a", every=8, width=1, glow=0.3, horizontal=False)
    frame = tex.trimmed(tex.eye_mat(iris="#c0508a", sclera="#e8dccb", pupil="#0c0814", lid="#3a2440", glow=0.8, slit=True), GOLD, 1)
    segs, walls = [], []
    for k in range(COR_SEGS):
        z0 = -COR_LEN * k
        s = m.bone(f"seg{k + 1}", root, pivot=(0, 0, z0))
        s.cube((-12, 0, z0 - COR_LEN), (24, 1.0, COR_LEN), N["marble"], mats={"up": carpet})
        s.cube((-13, 30, z0 - COR_LEN), (26, 2.0, COR_LEN), N["under"], variant=k % 2)
        s.box((0, 29.5, z0 - COR_LEN / 2), (2, 1.2, 2), N["lamp"])
        segs.append(s.name)
        for side, sx in (("r", 1), ("l", -1)):
            w = m.bone(f"w{side}{k + 1}", s, pivot=(sx * 12, 0, z0 - COR_LEN / 2))
            w.cube((sx * 12 - (0 if sx > 0 else 1.5), 0, z0 - COR_LEN), (1.5, 30, COR_LEN), paper, variant=k % 2,
                   mats={"up": N["gold"], "down": N["gold"]})
            w.plane("x", (sx * 11.6, 17, z0 - COR_LEN / 2), 8, 6, frame)
            w.box((sx * 11.2, 22, z0 - 2), (1.2, 2.4, 1.2), N["lamp"])
            walls.append((w.name, sx))
    end = m.bone("enddoor", root, pivot=(0, 0, -COR_LEN * COR_SEGS))
    ez = -COR_LEN * COR_SEGS
    end.box((0, 15, ez - 0.5), (26, 32, 2), N["wall3"], mats={"south": N["wall3"]})
    end.plane("z", (0, 12, ez + 0.7), 12, 22, N["door"])
    back = m.bone("backdoor", root, pivot=(0, 0, 0))
    back.box((0, 31, 0), (28, 4, 3), N["gold"])
    for sx in (-1, 1):
        back.box((sx * 13, 15, 0), (2.4, 32, 3), N["marble"])
    return m, segs, walls


def corridor_anims(segs, walls):
    A = [hidden_anim()]
    unf = Anim("unfold", length=T_COR_UNFOLD, loop="hold")
    for k, s in enumerate(segs):
        t0 = 0.05 + 0.16 * k
        unf.scl(s, {0: (1, 1, 0), t0: (1, 1, 0), t0 + 0.16: (1, 1.06, 1.1), t0 + 0.24: 1.0})
    unf.scl("enddoor", {0: 0.0, 0.85: 0.0, T_COR_UNFOLD: 1.0})
    unf.pos("enddoor", {0: (0, 0, COR_LEN * COR_SEGS), 0.85: (0, 0, 0)})
    for w, sx in walls:
        unf.rot(w, {0: (0, 0, -sx * 10), T_COR_UNFOLD: (0, 0, -sx * 8)})
    CLOSED = {w: (0, 0, sx * 72) for w, sx in walls}
    snap = Anim("snap", length=T_COR_SNAP, loop="hold")
    for i, (w, sx) in enumerate(walls):
        k = i // 2
        t1 = 0.06 + 0.04 * (COR_SEGS - 1 - k)
        snap.rot(w, {0: (0, 0, -sx * 8), t1: (0, 0, -sx * 14), t1 + 0.12: CLOSED[w], T_COR_SNAP: CLOSED[w]})
    snap.scl("root", {0: 1.0, 0.2: (1.0, 0.92, 1.0), T_COR_SNAP: 1.0})
    clamp = Anim("clamp", loop=True)
    for i, (w, sx) in enumerate(walls):
        clamp.rot(w, (LIFE(1.2, 0.3, i * 0.1), 0, LIFE(2.5, 0.45, i * 0.13, base=sx * 72)))
    fold = Anim("fold", length=T_COR_FOLD, loop="hold")
    for w, sx in walls:
        fold.rot(w, {0: CLOSED[w], 0.2: (0, 0, sx * 90)})
    n = len(segs)
    for k, s in enumerate(segs):
        t0 = 0.1 + 0.1 * k
        fold.scl(s, {0: 1.0, t0: 1.0, t0 + 0.18: (1, 1, 0)})
    fold.scl("root", {0: 1.0, 0.55: 1.0, T_COR_FOLD: 0.0})
    A += [unf, snap, clamp, fold]
    return A


# ====================================================================== Phase III: descending staircase slam
def build_stairfall():
    N = nm()
    m = Model("dn_city_stairfall", density=1.0, bounds=(10, 10, (0, 2, -6)))
    root = m.bone("root")
    runner = tex.banded(tex.fabric(BURG, "#4a1a26", stripe_w=2), "#c9a24a", every=10, width=1, glow=0.4, horizontal=False)
    chunks = []
    for k in range(SF_CHUNKS):
        zc = -32 * k - 16
        b = m.bone(f"ch{k + 1}", root, pivot=(0, 0, zc))
        b.box((0, 3, zc), (24, 6, 32), N["under"], variant=k % 3)
        for i in range(3):     # steps descend toward the target
            hh = 4.0 * (3 - i)
            b.box((0, 6 + hh / 2, zc + 10.6 - 10.6 * i), (24, hh, 10.6),
                  N["marble"], variant=(i + k) % 3, mats={"up": runner})
        for sx in (-1, 1):
            b.box((sx * 12.6, 18, zc + 4), (1.0, 1.0, 26), N["gold"], rot=(-22, 0, 0))
            for z in (-10, 2, 13):
                b.box((sx * 12.6, 12 + (z + 10) * 0.25, zc + z), (0.8, 8 + (z + 10) * 0.4, 0.8), N["gold"])
        b.box((0, 0.6, zc - 16.4), (24, 1.2, 0.8), N["gold_glow"])
        chunks.append(b.name)
    return m, chunks


def stairfall_anims(chunks):
    A = [hidden_anim()]
    sl = Anim("slam", length=T_SF_SLAM, loop="hold")
    for k, b in enumerate(chunks):
        t = SF_FIRST + SF_STEP * k
        sl.pos(b, {0: (0, 240, 0), t - 0.26: (0, 240, 0), t: (0, 0, 0), t + 0.06: (0, 3, 0), t + 0.14: (0, 0, 0)}, smooth=False)
        sl.scl(b, {0: 1.0, t - 0.01: (0.85, 1.25, 0.85), t + 0.05: (1.18, 0.7, 1.18), t + 0.16: 1.0}, smooth=False)
        sl.rot(b, {0: (0, 25 * (-1) ** k, 0), t - 0.26: (0, 25 * (-1) ** k, 0), t: (0, 0, 0)}, smooth=False)
    rest = Anim("rest", loop=True)
    for k, b in enumerate(chunks):
        rest.rot(b, (LIFE(0.8, 0.5, k * 0.2), 0, LIFE(0.8, 0.6, k * 0.1)))
    sink = Anim("sink", length=T_SF_SINK, loop="hold")
    for k, b in enumerate(chunks):
        t0 = 0.08 * k
        sink.pos(b, {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.45: (0, -36, 0)})
        sink.scl(b, {0: 1.0, t0 + 0.2: 1.0, t0 + 0.45: (1.2, 0.0, 1.2)})
    A += [sl, rest, sink]
    return A


# ====================================================================== Phase III: living fragment
def build_fragment():
    N = nm()
    m = Model("dn_city_fragment", density=1.5, bounds=(4, 4, (0, 1, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 10, 0))
    body.box((0, 15, 0), (16, 10, 14), N["wall2"], mats={"north": N["wall3"]})
    body.box((0, 10.4, 0), (17, 1.2, 15), N["gold"])
    body.plane("z", (0, 15.5, -7.2), 8, 5.5, tex.eye_mat(iris="#e070a8", sclera="#efe3cf", pupil="#0c0814", lid=BURG, glow=1.0,
                                                          slit=True), density=3.0)
    teeth = tex.bitmap_cut(["##########", "# # # # # ", "#   #   # "], "#f2e8d6", glow=0.25, color2="#bcaeb8")
    for s, sx in (("r", 1), ("l", -1)):
        rb = m.bone(f"roof_{s}", body, pivot=(0, 27, 0))
        rb.box((sx * 5.0, 24, 0), (13, 1.6, 18), N["roof"], rot=(0, 0, -sx * 40), pivot=(0, 27, 0))
        rb.plane("z", (sx * 4.6, 21.8, -8.6), 7, 2.6, teeth, rot=(0, 0, -sx * 40), pivot=(0, 27, -8.6))
        rb.plane("z", (sx * 4.6, 21.8, 8.6), 7, 2.6, teeth, rot=(0, 0, -sx * 40), pivot=(0, 27, 8.6))
    body.box((0, 27.6, 0), (1.4, 1.4, 19), N["gold_glow"])
    ch = m.bone("chimney", "roof_r", pivot=(5, 25, 3))
    ch.box((5, 29, 3), (4, 10, 4), N["under"])
    ch.box((5, 34.5, 3), (5.4, 1.6, 5.4), N["gold"])
    ch.box((5, 36, 3), (2.4, 1.6, 2.4), N["lamp"])
    legs = []
    for nme, (x, z) in (("fr", (6, -5)), ("fl", (-6, -5)), ("br", (6, 5)), ("bl", (-6, 5))):
        u = m.bone(f"leg_{nme}_1", body, pivot=(x, 10, z))
        u.box((x, 7.0, z), (2.2, 6.0, 2.2), N["marble"])
        u.box((x, 9.3, z), (3.2, 1.2, 3.2), N["gold"])
        lo = m.bone(f"leg_{nme}_2", u, pivot=(x, 4, z))
        lo.box((x, 2.5, z), (1.6, 3.4, 1.6), N["marble"], variant=1)
        lo.box((x, 0.6, z), (2.6, 1.2, 2.6), N["gold"])
        legs.append((u.name, lo.name, x, z))
    return m, legs


def fragment_anims(legs):
    A = [hidden_anim()]
    br = Anim("breathe", loop=True)
    br.scl("body", (1, LIFE(0.04, 1.4, base=1.0), 1))
    br.rot("chimney", (LIFE(5, 1.7), 0, LIFE(4, 2.1)))
    A.append(br)
    arr = Anim("arrive", length=T_FR_ARRIVE, loop="hold")
    arr.pos("root", {0: (0, 70, 0), 0.35: (0, 0, 0), 0.45: (0, 3, 0), 0.55: (0, 0, 0)}, smooth=False)
    arr.scl("body", {0: 1.0, 0.35: (1.2, 0.7, 1.2), 0.55: 1.0})
    for u, lo, x, z in legs:
        arr.rot(u, {0: (0, 0, 70 * (1 if x > 0 else -1)), 0.4: (0, 0, 70 * (1 if x > 0 else -1)), T_FR_ARRIVE: (0, 0, 0)})
    idle = Anim("idle", loop=True, length=1.2)
    for i, (u, lo, x, z) in enumerate(legs):
        idle.rot(u, (0, 0, LIFE(4, 1.2, i * 0.25)))
    idle.rot("body", (LIFE(3, 2.4), LIFE(6, 3.0), 0))
    idle.rot("roof_r", (0, 0, LIFE(4, 1.1, base=-4)))
    idle.rot("roof_l", (0, 0, LIFE(-4, 1.1, base=4)))
    hop = Anim("hop", length=T_FR_HOP, loop="hold")
    hop.pos("body", {0: (0, 0, 0), 0.12: (0, -3.5, 0), 0.22: (0, 2, 0), 0.45: (0, 0, 0), 0.5: (0, -2.5, 0), T_FR_HOP: (0, 0, 0)})
    hop.scl("body", {0: 1.0, 0.12: (1.15, 0.8, 1.15), 0.22: (0.88, 1.2, 0.88), 0.45: 1.0, 0.5: (1.15, 0.82, 1.15), T_FR_HOP: 1.0})
    hop.rot("body", {0: (0, 0, 0), 0.12: (10, 0, 0), 0.3: (-14, 0, 0), 0.5: (6, 0, 0), T_FR_HOP: (0, 0, 0)})
    for u, lo, x, z in legs:
        f = 1 if z < 0 else -1
        hop.rot(u, {0: (0, 0, 0), 0.12: (-20 * f, 0, 0), 0.25: (40 * f, 0, 0), 0.45: (-10 * f, 0, 0), T_FR_HOP: (0, 0, 0)})
        hop.rot(lo, {0: (0, 0, 0), 0.12: (40 * f, 0, 0), 0.25: (-20 * f, 0, 0), 0.5: (30 * f, 0, 0), T_FR_HOP: (0, 0, 0)})
    hop.rot("roof_r", {0: (0, 0, 0), 0.25: (0, 0, -18), 0.45: (0, 0, 0)})
    hop.rot("roof_l", {0: (0, 0, 0), 0.25: (0, 0, 18), 0.45: (0, 0, 0)})
    hop.sound(0.05, "hop")
    bite = Anim("bite", length=T_FR_BITE, loop="hold")      # the roof gapes like jaws and snaps shut
    bite.rot("roof_r", {0: (0, 0, 0), 0.18: (0, 0, -58), 0.27: (0, 0, 4), 0.35: (0, 0, -6), T_FR_BITE: (0, 0, 0)})
    bite.rot("roof_l", {0: (0, 0, 0), 0.18: (0, 0, 58), 0.27: (0, 0, -4), 0.35: (0, 0, 6), T_FR_BITE: (0, 0, 0)})
    bite.rot("body", {0: (0, 0, 0), 0.18: (-16, 0, 0), 0.27: (14, 0, 0), T_FR_BITE: (0, 0, 0)})
    bite.pos("body", {0: (0, 0, 0), 0.27: (0, 0, -5), T_FR_BITE: (0, 0, 0)})
    cr = Anim("crumble", length=T_FR_CRUMBLE, loop="hold")
    cr.rot("roof_r", {0: (0, 0, 0), T_FR_CRUMBLE: (0, 0, -100)})
    cr.rot("roof_l", {0: (0, 0, 0), T_FR_CRUMBLE: (0, 0, 100)})
    cr.scl("root", {0: 1.0, 0.3: (1.2, 0.6, 1.2), T_FR_CRUMBLE: 0.0})
    for u, lo, x, z in legs:
        cr.rot(u, {0: (0, 0, 0), 0.3: (0, 0, 80 * (1 if x > 0 else -1))})
    A += [arr, idle, hop, bite, cr]
    return A


# ====================================================================== build
def build(pack):
    st, fls = build_stair()
    sa = stair_anims(fls)
    pack.actor("dn_city_stair", st, sa, STAIR_STATES, size_prop=True, scale=2.0, lifetime=60, display="Sky Stair")
    bal = build_balcony()
    ba = balcony_anims()
    pack.actor("dn_city_balcony", bal, ba, BAL_STATES, scale=2.0, lifetime=30, display="Falling Balcony")
    sr = build_street()
    sra = street_anims()
    pack.actor("dn_city_street", sr, sra, STREET_STATES, scale=2.0, lifetime=30, display="Rolling Street")
    dr = build_door()
    da = door_anims()
    pack.actor("dn_city_door", dr, da, DOOR_STATES, always=["flutter"], scale=2.0, lifetime=40, display="Flying Doorframe")
    wn, panes = build_window()
    wa = window_anims(panes)
    pack.actor("dn_city_window", wn, wa, WIN_STATES, always=["bob"], scale=2.0, lifetime=40, display="Watching Window",
               sounds={"blink": "grimoire.dn_city_blink"})
    co, segs, walls = build_corridor()
    ca = corridor_anims(segs, walls)
    pack.actor("dn_city_corridor", co, ca, COR_STATES, scale=1.5, lifetime=40, display="Folding Corridor")
    sf, chunks = build_stairfall()
    sfa = stairfall_anims(chunks)
    pack.actor("dn_city_stairfall", sf, sfa, SF_STATES, scale=1.5, lifetime=40, display="Descending Stair")
    fr, legs = build_fragment()
    fra = fragment_anims(legs)
    pack.actor("dn_city_fragment", fr, fra, FR_STATES, always=["breathe"], scale=1.5, lifetime=40, display="Living Fragment",
               sounds={"hop": "grimoire.dn_city_fragment"})

    def by(anims):
        return {a.name: a for a in anims}
    v3 = ((30, 15), (150, 15), (0, 70))
    b = by(sa)
    pack.preview("dn_city_stair", st, [None, (b["descend"], 0.8)], views=((60, 10), (-30, 25)), cell=(340, 340))
    b = by(ba)
    pack.preview("dn_city_balcony", bal, [None, (b["impact"], 0.4)], views=v3, cell=(300, 300))
    b = by(sra)
    pack.preview("dn_city_street", sr, [(b["roll"], 0.3)], views=v3, cell=(300, 300))
    b = by(da)
    pack.preview("dn_city_door", dr, [[(b["fly"], 0.3), (b["flutter"], 0.4)], (b["swoop"], 0.38)], views=v3, cell=(300, 300))
    b = by(wa)
    pack.preview("dn_city_window", wn, [(b["hover"], 0.5), (b["blink"], 0.12), (b["stare"], 0.6)], views=((20, 10), (110, 10)),
                 cell=(300, 300))
    b = by(ca)
    pack.preview("dn_city_corridor", co, [(b["unfold"], T_COR_UNFOLD), (b["snap"], T_COR_SNAP)], views=((35, 25), (160, 30), (0, 80)),
                 cell=(320, 320))
    b = by(sfa)
    pack.preview("dn_city_stairfall", sf, [(b["slam"], 1.0), (b["slam"], T_SF_SLAM)], views=((50, 20), (0, 70)), cell=(320, 320))
    b = by(fra)
    pack.preview("dn_city_fragment", fr, [(b["idle"], 0.2), (b["hop"], 0.25), (b["bite"], 0.18)], views=((30, 12), (120, 12)),
                 cell=(280, 280))
    for nme, mdl in (("stair", st), ("balcony", bal), ("street", sr), ("door", dr), ("window", wn), ("corridor", co),
                     ("stairfall", sf), ("fragment", fr)):
        print(f"    dn_city_{nme}: {mdl.cube_count()} cubes, {len(mdl.order)} bones, tex {mdl.tex_size}")
