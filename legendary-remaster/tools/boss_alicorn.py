"""
ALICORN - Dawnstar Sovereign. Remastered model.

A great pearlescent winged unicorn: arched neck, refined head, a long twisted crystal horn whose
glow colour is the fight's language (none / RED ground strike / BLUE projectiles / GOLD charge),
an aurora mane and tail of living light, feathered fetlocks, gold hooves, a gold peytral with the
dawn-star, and swan wings that fold along the flanks on the ground and spread in flight.
Phase III: a crown of stars appears above the head.

Scale 1.6 -> 10 model units per block. Faces -Z. Horn tip ~ (0, 57, -54) (script horn(): ahead(5.2, 5.5)).
"""
import math

from modelkit import Model
from shapes import bevel, orb, ring, spike, strut
from shapes2 import catmull, feather, tube
import lmat as L

ID = "geometry.legends.alicorn"
KEY = "alicorn"
SCALE = 1.6
VARIANTS = {"default": "default"}
_CACHE = {}
WS, WE, WW, WT = (-7.0, 36.0, -9.0), (-21.0, 41.0, -7.0), (-37.0, 43.0, -11.0), (-62.0, 45.0, -10.0)
HUES = {"hue0": ("ffffff", "cfe8ff"), "hue1": ("fff0e8", "ff3a24"), "hue2": ("f0fbff", "3aa8ff"), "hue3": ("fffbe0", "ffb020")}


def build():
    m = Model(ID, seed=41, density=3)
    COAT = L.pearl_coat()
    AUR = L.aurora()
    FTH = L.feather_mat()
    GD = L.star_gold()
    HOOF = L.star_gold()
    CRY = L.crystal("f3eaff")
    EYE = L.glow("ffffff", "9a5cff", "r")

    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 28, 2), "root")
    bevel(body, (-8.5, 21, -14), (17, 15, 30), COAT, b=3.5)                 # barrel
    bevel(body, (-8, 19.6, -19), (16, 15, 9), COAT, b=3.5)                  # chest
    bevel(body, (-8.8, 23, 10), (17.6, 14.5, 11.5), COAT, b=3.5)            # rump
    bevel(body, (-4.2, 33.5, -14), (8.4, 4.2, 10), COAT, b=1.5)             # withers
    # gold peytral with the dawn-star
    bevel(body, (-8.4, 23, -19.9), (16.8, 6.5, 2.0), GD, b=0.6)
    for sx in (-1, 1):
        strut(body, (sx * 8.4, 27.5, -18.5), (sx * 8.8, 33, -6), 1.4, GD, depth=1.0)
    star = m.bone("dawnstar", (0, 26.5, -21), "body")
    for a in range(8):
        ang = a * math.pi / 4
        ln = 3.4 if a % 2 == 0 else 2.0
        strut(star, (0, 26.3, -21.2), (math.cos(ang) * ln, 26.3 + math.sin(ang) * ln, -21.2), 1.0, L.glow("fffbe8", "ffc84a", "r"), glow=True, depth=0.4)
    # saddle-cloth of starlight (subtle)
    body.add((-8.9, 31, -6), (17.8, 0.9, 12), L.thai_cloth("4a2e8c", "f2d27a"))

    # ------------------------------------------------------------------ neck, head, horn, mane
    neck = m.bone("neck", (0, 33, -14), "body")
    npts = catmull([(0, 32, -13), (0, 40, -20), (0, 48, -26), (0, 53, -30)], 2)
    tube(neck, npts, 8.6, 6.8, COAT, depth_ratio=1.45)
    head = m.bone("head", (0, 52, -30), "neck")
    strut(head, (0, 52.5, -30), (0, 46.5, -42), 7.2, COAT, depth=10, soft=True)        # skull
    strut(head, (0, 47.5, -40), (0, 42.5, -49), 6.0, COAT, depth=7.4, soft=True)       # muzzle
    bevel(head, (-3.8, 43.2, -40.5), (7.6, 6.5, 6.0), COAT, b=1.6)                     # cheeks
    head.add((-2.6, 41.6, -50.0), (5.2, 2.6, 2.4), L.solid("e8dff5", 0.02))           # lips
    for sx in (-1, 1):
        head.add((sx * 1.3 - 0.5, 43.3, -50.5), (1.0, 1.0, 0.6), L.solid("6a5a7a", 0.02))   # nostrils
        head.add((sx * 3.75 - (0.2 if sx > 0 else 0.0), 47.4, -40.2), (0.2 + 0.0, 1.8, 2.6), EYE, glow=True)
        ear = m.bone(f"ear_{'r' if sx < 0 else 'l'}", (sx * 2.2, 54, -32), "head")
        spike(ear, (sx * 2.2, 53.5, -32), (sx * 2.9, 59, -31.5), 2.4, COAT, steps=3)
    # chanfron (gold head ornament) and the horn
    bevel(head, (-3.0, 49.8, -40.2), (6.0, 3.0, 4.6), GD, b=0.6)
    horn = m.bone("horn", (0, 52, -40), "head")
    hp = [(0, 51.8, -40.5), (0, 54.4, -46.5), (0, 56.8, -52.5), (0, 59.0, -58.0)]
    tube(horn, catmull(hp, 3), 2.6, 0.7, CRY, soft=False)
    for k in range(5):                                                            # spiral ridges
        t = (k + 0.5) / 5
        p = (0, 51.8 + 7.2 * t, -40.5 - 17.5 * t)
        horn.add((-1.7 + 0.3 * t, p[1] - 0.35, p[2] - 0.6), (3.4 - 0.6 * t, 0.7, 1.2), GD, rotation=(0, 0, 25), pivot=p)
    for hb, (core, edge) in HUES.items():                                         # hue glow overlays
        gb = m.bone(f"horn_{hb}", (0, 52, -40), "horn")
        tube(gb, catmull([(0, 51.8, -40.5), (0, 54.4, -46.5), (0, 56.8, -52.5), (0, 59.6, -59.2)], 3), 3.2, 1.0,
             L.glow(core, edge, "u"), glow=True, overlap=0.3)
    # mane: aurora strands along the crest + forelock
    mane = m.bone("mane", (0, 50, -28), "neck")
    crest = catmull([(0, 54, -30.5), (0, 50, -26), (0, 44, -20), (0, 37, -14)], 2)
    for i, p in enumerate(crest[:-1]):
        side = -1 if i % 2 == 0 else 1
        tip = (p[0] + side * 3.5, p[1] - 9 - (i % 3), p[2] + 3.5)
        tube(mane, catmull([p, (p[0] + side * 2.5, p[1] - 1.5, p[2] + 2.0), tip], 2), 3.0, 1.0, AUR, glow=True, overlap=0.4)
    tube(mane, catmull([(0, 54.5, -32), (0, 53, -36.5), (0.6, 50.5, -38.2)], 2), 2.4, 0.8, AUR, glow=True, overlap=0.3)

    # ------------------------------------------------------------------ legs
    def leg(name, hip, knee, fet, hoof_z, front):
        a = m.bone(f"{name}", hip, "body")
        if front:
            tube(a, [hip, knee], 6.2, 4.6, COAT)
        else:
            k0 = (hip[0], (hip[1] + knee[1]) / 2 + 1, hip[2] - 4)
            tube(a, [hip, k0, knee], 8.0, 4.4, COAT)
        b = m.bone(f"{name}_lo", knee, f"{name}")
        tube(b, [knee, fet], 3.6, 3.0, COAT)
        c = m.bone(f"{name}_hoof", fet, f"{name}_lo")
        tube(c, [fet, (fet[0], 3.0, hoof_z)], 3.2, 3.0, COAT)
        bevel(c, (fet[0] - 2.3, 0, hoof_z - 2.6), (4.6, 3.2, 5.0), HOOF, b=0.7)
        for k in range(5):                                                  # feathered fetlock (glow)
            ang = k / 5 * 2 * math.pi
            strut(c, (fet[0] + math.cos(ang) * 1.2, fet[1] + 0.5, fet[2] + math.sin(ang) * 1.2),
                  (fet[0] + math.cos(ang) * 3.0, 2.6, fet[2] + math.sin(ang) * 3.0 + 0.8), 0.9, AUR, glow=True, depth=0.5)
    for side, sx in (("r", -1), ("l", 1)):
        leg(f"fleg_{side}", (sx * 5.4, 27, -12.5), (sx * 5.4, 15, -13.5), (sx * 5.4, 5.5, -13.5), -14.5, True)
        leg(f"hleg_{side}", (sx * 5.8, 29, 14), (sx * 5.8, 14, 20.5), (sx * 5.8, 5.0, 18.5), 17.5, False)

    # ------------------------------------------------------------------ tail of aurora
    tail = m.bone("tail", (0, 34, 21), "body")
    for k, d in enumerate(((0, 0), (2.4, 1.5), (-2.4, 1.0), (1.2, -1.8), (-1.4, -1.2))):
        pts = catmull([(d[0] * 0.3, 34.5, 21.5), (d[0] * 0.6, 32 + d[1], 28), (d[0], 23 + d[1], 33), (d[0] * 1.3, 12 + d[1], 36 + k)], 2)
        tube(tail, pts, 3.4 - k * 0.2, 1.2, AUR, glow=True, overlap=0.4)
    tail.add((-1.8, 32.6, 20.2), (3.6, 3.6, 3.0), COAT)

    # ------------------------------------------------------------------ wings (rest = spread)
    for side, sx in (("r", 1), ("l", -1)):
        S = (sx * WS[0], WS[1], WS[2]); E = (sx * WE[0], WE[1], WE[2]); W = (sx * WW[0], WW[1], WW[2]); Tp = (sx * WT[0], WT[1], WT[2])
        wa = m.bone(f"wing_{side}", S, "body")
        tube(wa, [S, E], 5.0, 4.2, FTH)
        wf = m.bone(f"wfore_{side}", E, f"wing_{side}")
        tube(wf, [E, W], 4.2, 3.4, FTH)
        wh = m.bone(f"whand_{side}", W, f"wfore_{side}")
        tube(wh, [W, Tp], 3.2, 1.6, FTH)
        # coverts along humerus + forearm (short, pointing back)
        for i in range(7):
            t = i / 6
            p = tuple(S[k] + (W[k] - S[k]) * t for k in range(3))
            bone = wa if t < 0.45 else wf
            feather(bone, (p[0], p[1] - 0.6, p[2] + 1.5), 9 - t * 2, 4.4, 180 + sx * -6, 0, FTH, thick=0.6)
        # secondaries along the forearm (long, pointing back)
        for i in range(6):
            t = i / 5
            p = tuple(E[k] + (W[k] - E[k]) * t for k in range(3))
            feather(wf, (p[0], p[1] - 1.2, p[2] + 2.0), 17 - t * 2, 4.2, 180 + sx * (-4 - t * 10), 0, FTH, thick=0.5)
        # primaries from the hand (long, fanned)
        for i in range(7):
            t = i / 6
            p = tuple(W[k] + (Tp[k] - W[k]) * (0.15 + t * 0.85) for k in range(3))
            feather(wh, (p[0], p[1] - 1.6 - 0.05 * i, p[2] + 1.0), 22 - t * 6, 4.0, 180 + sx * (-18 - t * 62), 0, FTH, thick=0.5)

    # ------------------------------------------------------------------ crown of stars (phase III)
    crown = m.bone("crown", (0, 63, -34), "head", floating=True)
    ring(crown, (0, 63, -34), 6, 10, L.glow("fffbe0", "ffc040", "u"), thickness=0.7, width=0.6, plane="xz", glow=True)
    for a in range(5):
        ang = a / 5 * 2 * math.pi
        c = (math.cos(ang) * 6, 63, -34 + math.sin(ang) * 6)
        spike(crown, c, (c[0] * 1.05, 67.5, c[2] + (math.sin(ang) * 0.3)), 1.6, L.glow("ffffff", "ffd860", "vb"), steps=2, glow=True)
    _CACHE["model"] = m
    return m


# =========================================================================== animation
from animkit import A, T, Act, cs, loop, merge, sn


def fold_pose(m=None):
    """Grounded: each wing swings back along the flank and rolls so its feathers hang down like a
    closed swan wing (humerus yaw -90 / roll -90), shifted outward so it rests on the coat."""
    pose = {}
    for side, sx in (("r", 1), ("l", -1)):
        pose[f"wing_{side}"] = {"rot": (6, sx * -90, sx * -90), "pos": (sx * -2.6, 1.0, 2.0)}
        pose[f"wfore_{side}"] = {"rot": (0, sx * 8, 0)}
        pose[f"whand_{side}"] = {"rot": (0, sx * 12, sx * -4), "scale": 0.72}
    return pose


def loops():
    fp = fold_pose()
    fold = {b: {**({"r": list(d["rot"])} if "rot" in d else {}), **({"p": list(d["pos"])} if "pos" in d else {}),
                **({"s": d["scale"]} if "scale" in d else {})} for b, d in fp.items()}
    idle = {
        "body": {"p": [0, sn(60, amp=0.35), 0]},
        "neck": {"r": [f"-4 + {sn(60, amp=2)}", sn(25, amp=5), 0]},
        "head": {"r": [sn(60, 50, 3), sn(30, amp=5), sn(20, amp=2)]},
        "ear_r": {"r": [sn(90, amp=8), 0, sn(40, amp=6)]}, "ear_l": {"r": [sn(90, 70, 8), 0, sn(40, 30, -6)]},
        "mane": {"r": [0, 0, sn(70, amp=3)], "p": [sn(55, amp=0.4), 0, 0]},
        "tail": {"r": [sn(50, amp=5), sn(35, amp=10), 0]},
        "dawnstar": {"r": [0, 0, f"{T} * 40"]},
        "crown": {"r": [0, f"{T} * 30", 0], "p": [0, sn(80, amp=0.8), 0]},
        "fleg_r": {"r": [sn(20, amp=1), 0, 0]},
        "horn_hue0": {"s": f"1 + {sn(200, amp=0.06)}"},
    }
    w = "variable.dist * 80"
    walk = {
        "fleg_r": {"r": [f"math.sin({w}) * 26", 0, 0]}, "fleg_r_lo": {"r": [f"math.max(0, math.sin({w} + 90)) * -40", 0, 0]},
        "fleg_l": {"r": [f"math.sin({w} + 180) * 26", 0, 0]}, "fleg_l_lo": {"r": [f"math.max(0, math.sin({w} + 270)) * -40", 0, 0]},
        "hleg_r": {"r": [f"math.sin({w} + 270) * 22", 0, 0]}, "hleg_r_lo": {"r": [f"math.max(0, math.sin({w})) * 34", 0, 0]},
        "hleg_l": {"r": [f"math.sin({w} + 90) * 22", 0, 0]}, "hleg_l_lo": {"r": [f"math.max(0, math.sin({w} + 180)) * 34", 0, 0]},
        "body": {"p": [0, f"math.abs(math.cos({w})) * 1.2", 0], "r": [f"math.sin(({w}) * 2) * 1.5", 0, 0]},
        "neck": {"r": [f"math.sin(({w}) * 2) * -4", 0, 0]},
        "tail": {"r": [f"math.sin(({w}) * 2) * 6", 0, 0]},
    }
    flap = f"math.sin({T} * 170)"
    fly = {
        "wing_r": {"r": [0, 0, f"{flap} * -30"]}, "wing_l": {"r": [0, 0, f"{flap} * 30"]},
        "wfore_r": {"r": [0, 0, f"math.sin({T} * 170 - 40) * -18"]}, "wfore_l": {"r": [0, 0, f"math.sin({T} * 170 - 40) * 18"]},
        "whand_r": {"r": [0, 0, f"math.sin({T} * 170 - 80) * -14"]}, "whand_l": {"r": [0, 0, f"math.sin({T} * 170 - 80) * 14"]},
        "body": {"p": [0, f"math.sin({T} * 170 + 180) * 1.5", 0], "r": [-4, 0, 0]},
        "fleg_r": {"r": [-40, 0, 0]}, "fleg_l": {"r": [-30, 0, 0]}, "fleg_r_lo": {"r": [-90, 0, 0]}, "fleg_l_lo": {"r": [-80, 0, 0]},
        "hleg_r": {"r": [30, 0, 0]}, "hleg_l": {"r": [36, 0, 0]}, "hleg_r_lo": {"r": [30, 0, 0]}, "hleg_l_lo": {"r": [26, 0, 0]},
        "tail": {"r": [f"-14 + {sn(120, amp=6)}", 0, 0]},
    }
    return {"idle": loop(idle), "walk": loop(walk), "fold": loop(fold), "fly": loop(fly)}


def acts():
    out = []
    rear = lambda k: {"body": {"r": (-k, 0, 0), "p": (0, k * 0.22, k * 0.25)}, "hleg_r": {"r": (k * 0.6, 0, 0)}, "hleg_l": {"r": (k * 0.6, 0, 0)},
                      "fleg_r": {"r": (-k * 1.6, 0, 0)}, "fleg_l": {"r": (-k * 1.3, 0, 0)}, "fleg_r_lo": {"r": (-k * 2.0, 0, 0)}, "fleg_l_lo": {"r": (-k * 1.8, 0, 0)},
                      "neck": {"r": (k * 0.4, 0, 0)}}
    spread = lambda z: {"wing_r": {"r": (0, 0, -z)}, "wing_l": {"r": (0, 0, z)}}
    rest_head = {"neck": {"r": (0, 0, 0)}, "head": {"r": (0, 0, 0)}}
    # 1 descend (60, 44): floats down with spread wings and touches the earth
    a = Act("descend", 60, [44])
    a.at(0, {**spread(20), "head": {"r": (-10, 0, 0)}, "fleg_r": {"r": (-30, 0, 0)}, "fleg_r_lo": {"r": (-60, 0, 0)}})
    a.at(40, {**spread(-10), "fleg_r": {"r": (-10, 0, 0)}, "fleg_r_lo": {"r": (-20, 0, 0)}}, "io")
    a.at(44, {**spread(10), "body": {"p": (0, -2, 0)}, "fleg_r": {"r": (0, 0, 0)}, "fleg_r_lo": {"r": (0, 0, 0)}}, "in")
    a.at(60, {**spread(0), "body": {"p": (0, 0, 0)}, "head": {"r": (0, 0, 0)}})
    out.append(a.overlay("wing_r", "r", [0, 0, f"math.sin({A} * 360) * -12"]).overlay("wing_l", "r", [0, 0, f"math.sin({A} * 360) * 12"]))
    # 2 rear (40, 26)
    a = Act("rear", 40, [26])
    a.at(20, {**rear(34), "head": {"r": (-16, 0, 0)}}, "out")
    a.at(26, {**rear(0), "head": {"r": (14, 0, 0)}, "body": {"r": (4, 0, 0)}}, "in")
    a.at(40, {**rear(0), **rest_head, "body": {"r": (0, 0, 0)}})
    out.append(a)
    # 3 stomp (28, 18): rears, crashes both forehooves down
    a = Act("stomp", 28, [18])
    a.at(13, {**rear(38), "head": {"r": (-18, 0, 0)}}, "out")
    a.at(18, {**rear(-4), "head": {"r": (16, 0, 0)}}, "in")
    a.at(28, {**rear(0), **rest_head})
    out.append(a)
    # 4 charge (20, loop): full gallop, horn levelled
    a = Act("charge", 20, [], loop=True)
    g = f"math.sin({A} * 1440)"
    a.at(0, {"neck": {"r": (18, 0, 0)}, "head": {"r": (16, 0, 0)}, "body": {"r": (4, 0, 0)}})
    a.at(20, {"neck": {"r": (18, 0, 0)}, "head": {"r": (16, 0, 0)}, "body": {"r": (4, 0, 0)}}, "lin")
    a.overlay("fleg_r", "r", [f"{g} * 46", 0, 0]).overlay("fleg_l", "r", [f"{g} * 40", 0, 0])
    a.overlay("hleg_r", "r", [f"-{g} * 40", 0, 0]).overlay("hleg_l", "r", [f"-{g} * 46", 0, 0])
    a.overlay("fleg_r_lo", "r", [f"math.max(0, -{g}) * -60", 0, 0]).overlay("fleg_l_lo", "r", [f"math.max(0, -{g}) * -60", 0, 0])
    a.overlay("body", "p", [0, f"math.abs({g}) * 2.4", 0]).overlay("tail", "r", [f"-20 + {g} * 6", 0, 0])
    out.append(a)
    # 5 lance (28, 14): head tossed up, horn flares, star lances fly
    a = Act("lance", 28, [14])
    a.at(10, {"neck": {"r": (12, 0, 0)}, "head": {"r": (18, 0, 0)}, "horn": {"s": 1.0}})
    a.at(14, {"neck": {"r": (-20, 0, 0)}, "head": {"r": (-20, 0, 0)}, "horn": {"s": 1.25}}, "in")
    a.at(28, {**rest_head, "horn": {"s": 1.0}})
    out.append(a)
    # 6 wing_gust (28, 14)
    a = Act("wing_gust", 28, [14])
    a.at(9, {"wing_r": {"r": (-30, -40, -50)}, "wing_l": {"r": (-30, 40, 50)}, **rear(10)}, "out")
    a.at(14, {"wing_r": {"r": (20, 30, 20)}, "wing_l": {"r": (20, -30, -20)}, **rear(-4)}, "in")
    a.at(28, {"wing_r": {"r": (0, 0, 0)}, "wing_l": {"r": (0, 0, 0)}, **rear(0)})
    out.append(a)
    # 7 takeoff (30, 14)
    a = Act("takeoff", 30, [14])
    a.at(10, {**rear(20), **spread(-30)}, "out")
    a.at(14, {**rear(8), **spread(40), "body": {"p": (0, 6, 0)}}, "in")
    a.at(30, {**rear(0), **spread(0)})
    out.append(a)
    # 8 land (24, 10)
    a = Act("land", 24, [10])
    a.at(8, {**spread(30), "fleg_r": {"r": (-20, 0, 0)}, "fleg_l": {"r": (-20, 0, 0)}})
    a.at(10, {**spread(10), "body": {"p": (0, -2, 0)}, "fleg_r": {"r": (6, 0, 0)}, "fleg_l": {"r": (6, 0, 0)}}, "in")
    a.at(24, {**spread(0), "body": {"p": (0, 0, 0)}, "fleg_r": {"r": (0, 0, 0)}, "fleg_l": {"r": (0, 0, 0)}})
    out.append(a)
    # 9 curtain (48, 20): wings raised high, the aurora wall is summoned
    a = Act("curtain", 48, [20])
    a.at(16, {"wing_r": {"r": (-10, 0, -50)}, "wing_l": {"r": (-10, 0, 50)}, "neck": {"r": (-20, 0, 0)}, "head": {"r": (-24, 0, 0)}, "horn": {"s": 1.2}}, "out")
    a.at(20, {"wing_r": {"r": (10, 0, 20)}, "wing_l": {"r": (10, 0, -20)}, "neck": {"r": (10, 0, 0)}, "head": {"r": (10, 0, 0)}}, "in")
    a.at(48, {"wing_r": {"r": (0, 0, 0)}, "wing_l": {"r": (0, 0, 0)}, **rest_head, "horn": {"s": 1.0}})
    out.append(a)
    # 10 comet (32, 22): dives horn-first
    a = Act("comet", 32, [22])
    a.at(12, {**spread(-30), "body": {"r": (-20, 0, 0)}, "neck": {"r": (-10, 0, 0)}}, "out")
    a.at(16, {"wing_r": {"r": (-20, -60, 0)}, "wing_l": {"r": (-20, 60, 0)}, "body": {"r": (40, 0, 0)}, "neck": {"r": (20, 0, 0)}, "head": {"r": (10, 0, 0)}}, "in")
    a.at(22, {"body": {"r": (30, 0, 0)}}, "lin")
    a.at(32, {**spread(0), "wing_r": {"r": (0, 0, 0)}, "wing_l": {"r": (0, 0, 0)}, "body": {"r": (0, 0, 0)}, **rest_head}, "out")
    out.append(a)
    # 11 barrier (40, 20): bows, the prisms rise
    a = Act("barrier", 40, [20])
    a.at(14, {"neck": {"r": (30, 0, 0)}, "head": {"r": (20, 0, 0)}, "fleg_r": {"r": (-50, 0, 0)}, "fleg_r_lo": {"r": (-100, 0, 0)}, "body": {"p": (0, -2, 0)}}, "io")
    a.at(20, {"horn": {"s": 1.3}}, "in")
    a.at(40, {**rest_head, "fleg_r": {"r": (0, 0, 0)}, "fleg_r_lo": {"r": (0, 0, 0)}, "body": {"p": (0, 0, 0)}, "horn": {"s": 1.0}})
    out.append(a)
    # 12 heal (80): kneels in moonlight, wings cupped
    a = Act("heal", 80)
    a.at(16, {"fleg_r": {"r": (-60, 0, 0)}, "fleg_r_lo": {"r": (-110, 0, 0)}, "fleg_l": {"r": (-60, 0, 0)}, "fleg_l_lo": {"r": (-110, 0, 0)},
              "body": {"p": (0, -7, 0), "r": (8, 0, 0)}, "neck": {"r": (-16, 0, 0)}, "head": {"r": (-14, 0, 0)}, "horn": {"s": 1.2}}, "io")
    a.at(80, {"body": {"p": (0, -7, 0), "r": (8, 0, 0)}}, "lin")
    out.append(a.overlay("horn", "s", f"math.sin({A} * 300) * 0.1"))
    # 13 nova (260): ULT - calls the aurora stampede three times, then becomes the dawn (look away!)
    a = Act("nova", 260, [20, 60, 100, 150, 220])
    for mk in (20, 60, 100):
        a.at(mk - 8, {"body": {"r": (-26, 0, 0)}, "neck": {"r": (-10, 0, 0)}, "head": {"r": (-22, 0, 0)}, "wing_r": {"r": (0, 0, -40)}, "wing_l": {"r": (0, 0, 40)},
                      "fleg_r": {"r": (-60, 0, 0)}, "fleg_l": {"r": (-50, 0, 0)}}, "out")
        a.at(mk, {"body": {"r": (-6, 0, 0)}, "head": {"r": (12, 0, 0)}, "wing_r": {"r": (0, 0, 24)}, "wing_l": {"r": (0, 0, -24)},
                  "fleg_r": {"r": (-10, 0, 0)}, "fleg_l": {"r": (-10, 0, 0)}, "horn": {"s": 1.3}}, "in")
    a.at(150, {"body": {"r": (-30, 0, 0)}, "neck": {"r": (-20, 0, 0)}, "head": {"r": (-30, 0, 0)}, "wing_r": {"r": (0, 0, -60)}, "wing_l": {"r": (0, 0, 60)}, "horn": {"s": 1.6},
               "fleg_r": {"r": (-70, 0, 0)}, "fleg_l": {"r": (-60, 0, 0)}, "fleg_r_lo": {"r": (-90, 0, 0)}, "fleg_l_lo": {"r": (-80, 0, 0)}}, "io")
    a.at(214, {"horn": {"s": 2.4}, "head": {"r": (-36, 0, 0)}, "wing_r": {"r": (0, 0, -70)}, "wing_l": {"r": (0, 0, 70)}}, "lin")
    a.at(220, {"horn": {"s": 3.0}, "wing_r": {"r": (-30, -40, 30)}, "wing_l": {"r": (-30, 40, -30)}, "body": {"r": (-10, 0, 0)}}, "in")
    a.at(260, {"horn": {"s": 1.0}, "body": {"r": (0, 0, 0)}, **rest_head, "wing_r": {"r": (0, 0, 0)}, "wing_l": {"r": (0, 0, 0)},
               "fleg_r": {"r": (0, 0, 0)}, "fleg_l": {"r": (0, 0, 0)}, "fleg_r_lo": {"r": (0, 0, 0)}, "fleg_l_lo": {"r": (0, 0, 0)}}, "out")
    out.append(a.overlay("crown", "r", [0, f"{A} * 160", 0]))
    # 14 hyper (20, loop): streaking dash, wings swept back
    a = Act("hyper", 20, [], loop=True)
    a.at(0, {"wing_r": {"r": (0, -60, 10)}, "wing_l": {"r": (0, 60, -10)}, "body": {"r": (6, 0, 0)}, "neck": {"r": (20, 0, 0)}, "head": {"r": (14, 0, 0)},
             "fleg_r": {"r": (-70, 0, 0)}, "fleg_l": {"r": (-70, 0, 0)}, "hleg_r": {"r": (50, 0, 0)}, "hleg_l": {"r": (50, 0, 0)}})
    a.at(20, {"wing_r": {"r": (0, -60, 10)}, "wing_l": {"r": (0, 60, -10)}, "body": {"r": (6, 0, 0)}, "neck": {"r": (20, 0, 0)}, "head": {"r": (14, 0, 0)},
              "fleg_r": {"r": (-70, 0, 0)}, "fleg_l": {"r": (-70, 0, 0)}, "hleg_r": {"r": (50, 0, 0)}, "hleg_l": {"r": (50, 0, 0)}}, "lin")
    out.append(a)
    # 15 spiral (60, 12): pirouette in the air, rainbow spiral
    a = Act("spiral", 60, [12])
    a.at(10, {**spread(30), "head": {"r": (-14, 0, 0)}, "horn": {"s": 1.2}}, "out")
    a.at(54, {"root": {"r": (0, 720, 0)}, **spread(30)}, "lin")
    a.at(60, {"root": {"r": (0, 720, 0)}, **spread(0), "head": {"r": (0, 0, 0)}, "horn": {"s": 1.0}})
    out.append(a)
    # 16 death (80, 68): folds to the ground and dissolves into dawnlight
    a = Act("death", 80, [68])
    a.at(16, {**rear(26), "head": {"r": (-24, 0, 0)}, **spread(30)}, "out")
    a.at(44, {"body": {"p": (0, -10, 0), "r": (4, 0, 14)}, "fleg_r": {"r": (-70, 0, 0)}, "fleg_r_lo": {"r": (-120, 0, 0)}, "fleg_l": {"r": (-70, 0, 0)},
              "fleg_l_lo": {"r": (-120, 0, 0)}, "hleg_r": {"r": (-20, 0, 0)}, "hleg_l": {"r": (-20, 0, 0)}, "neck": {"r": (30, 0, 0)}, "head": {"r": (24, 0, 20)},
              **spread(-20)}, "io")
    a.at(68, {"root": {"s": 1.0}}, "lin")
    a.at(80, {"root": {"s": 0.02, "p": (0, 20, 0)}}, "in")
    out.append(a)
    return out


def entity_cfg():
    hv = "query.property('legends:var')"
    return {
        "scale": SCALE,
        "textures": {"default": f"textures/entity/legends/{KEY}"},
        "pre": [
            "variable.flyw = math.lerp(variable.flyw ?? 0.0, query.property('legends:fly') == 1 ? 1.0 : 0.0, 0.08);",
            "variable.walkw = variable.mv * (1.0 - variable.flyw) * variable.calm;",
        ],
        "animate": [{"idle": "variable.calm + 0.15"}, {"fold": "1.0 - variable.flyw"}, {"walk": "variable.walkw"}, {"fly": "variable.flyw"}, "ctrl_act"],
        "visibility": [
            {"crown": "variable.ph >= 3"},
            {"horn_hue0": f"{hv} == 0"}, {"horn_hue1": f"{hv} == 1"}, {"horn_hue2": f"{hv} == 2"}, {"horn_hue3": f"{hv} == 3"},
        ],
        "bounds": (14, 9, 3.0),
    }


if __name__ == "__main__":
    import sys
    from modelkit import render_preview, zfight_report, island_report, deflicker
    out = sys.argv[1]
    m = build()
    m.paint()
    print(m.stats())
    print("islands", island_report(m))
    print("zfight", len(zfight_report(m)), "after deflicker", deflicker(m))
    fp = fold_pose(m)
    hide = {"crown": {"scale": 0.001}, "horn_hue1": {"scale": 0.001}, "horn_hue2": {"scale": 0.001}, "horn_hue3": {"scale": 0.001}}
    render_preview([m], f"{out}/ali_ground.png", yaw=40, pitch=12, size=700, step=1, pose={**fp, **hide})
    render_preview([m], f"{out}/ali_fly.png", yaw=-140, pitch=22, size=700, step=1, pose={"horn_hue0": {"scale": 0.001}, "horn_hue1": {"scale": 0.001}, "horn_hue2": {"scale": 0.001}})


def extra_entities(RP, m, built_acts):
    """Aurora Steed: a spectral copy of the Alicorn (additive, aurora-tinted) that gallops in the ultimate."""
    import json
    import os
    from PIL import Image
    src = os.path.join(RP, "textures", "entity", "legends", "alicorn.png")
    img = Image.open(src).convert("RGBA")
    px = img.load()
    W, H = img.size
    stops = [(255, 150, 230), (180, 140, 255), (120, 220, 255)]
    for y in range(H):
        for x in range(W):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            t = ((x + y) % 96) / 96 * 2
            i = min(1, int(t))
            f = t - i
            c = tuple(int(stops[i][k] * (1 - f) + stops[i + 1][k] * f) for k in range(3))
            lum = (r + g + b) / 765
            px[x, y] = (int(c[0] * lum * 0.85), int(c[1] * lum * 0.85), int(c[2] * lum * 0.85), a)
    img.save(os.path.join(RP, "textures", "entity", "legends", "aurora_steed.png"))
    desc = {
        "identifier": "legends:aurora_steed",
        "materials": {"default": "entity_beam_additive", "glow": "entity_beam_additive"},
        "textures": {"default": "textures/entity/legends/aurora_steed"},
        "geometry": {"default": ID, "glow": ID + ".glow"},
        "animations": {"idle": f"animation.legends.{KEY}.idle", "fold": f"animation.legends.{KEY}.fold",
                       "gallop": f"animation.legends.{KEY}.act.charge"},
        "scripts": {"scale": str(SCALE), "pre_animation": ["variable.t = (variable.t ?? 0.0) + query.delta_time;", "variable.open = 1.0;"],
                    "animate": ["idle", "fold", "gallop"]},
        "render_controllers": ["controller.render.legends.aurora_steed"],
    }
    with open(os.path.join(RP, "entity", "legends", "aurora_steed.entity.json"), "w") as f:
        json.dump({"format_version": "1.10.0", "minecraft:client_entity": {"description": desc}}, f, indent=1)
    rc = {"format_version": "1.8.0", "render_controllers": {"controller.render.legends.aurora_steed": {
        "geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"],
        "part_visibility": [{"*": True}, {"crown": False}, {"horn_hue1": False}, {"horn_hue2": False}, {"horn_hue3": False}]}}}
    with open(os.path.join(RP, "render_controllers", "legends", "aurora_steed.rc.json"), "w") as f:
        json.dump(rc, f, indent=1)


ALSO_PROVIDES = ["aurora_steed"]
