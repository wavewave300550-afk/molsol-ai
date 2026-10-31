"""
TENKO (十尾の天狐) - the Ten-Tailed Fox of the Tenfold Moon. Remastered model.

A tall, slender celestial fox in warm white and gold with vermilion kitsune markings and socks,
a shimenawa rope with a golden suzu bell at the throat, the star pearl (hoshi-no-tama) floating
before her chest, a crescent moon halo, and nine great tails fanned like a sunburst with foxfire
tips. The tenth tail rises behind them bound with rope and ofuda - it unseals in phase III.
The same geometry with the 'illusion' palette (additive, pale blue) is the Foxfire Illusion.

Scale 1.7 -> 9.41 model units per block. Faces -Z.
"""
import math

from modelkit import Model
from shapes import bevel, orb, ring, spike, strut
from shapes2 import catmull, tube
import lmat as L

ID = "geometry.legends.tenko"
KEY = "tenko"
SCALE = 1.7
VARIANTS = {"default": "default", "illusion": "illusion"}
_CACHE = {}
TAIL_ROOT = (0.0, 33.0, 17.0)
N_TAILS = 9


def tail_points(i):
    th = math.radians(-100 + 200 * i / (N_TAILS - 1))
    r = TAIL_ROOT
    sx, cy = math.sin(th), math.cos(th)
    return [r,
            (r[0] + sx * 5, r[1] + 4 + cy * 4, r[2] + 7),
            (r[0] + sx * 15, r[1] + 8 + cy * 14, r[2] + 12),
            (r[0] + sx * 24, r[1] + 10 + cy * 23, r[2] + 9)]


def build():
    m = Model(ID, seed=53, density=3)
    FUR = L.fox_fur()
    FURS = L.fox_fur(sock="d0321c")
    VER = L.vermilion()
    ROPE = L.shimenawa()
    OF = L.ofuda()
    BELL = L.star_gold()
    TIP = L.glow("ffffff", "4aa8ff", "vb")
    EYE = L.glow("ffffff", "ffb020", "r")
    MOON = L.glow("ffffff", "b9c8ff", "u")
    PEARL = L.glow("ffffff", "6ab8ff", "r")

    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 30, 0), "root")
    bevel(body, (-7.6, 22, -19.5), (15.2, 17, 15), FUR, b=4.0)               # chest
    bevel(body, (-6.6, 24, -6), (13.2, 13, 14), FUR, b=3.6)                   # waist
    bevel(body, (-7.6, 23, 6), (15.2, 15, 13), FUR, b=4.0)                    # haunches
    for sx in (-1, 1):                                                         # vermilion flame marks
        x0 = sx * 7.65 - (0.3 if sx > 0 else 0)
        body.add((x0, 31, -15), (0.3, 4, 6), VER)
        body.add((x0, 30, 9), (0.3, 5, 6), VER)
    # neck, ruff, rope and bell
    neck = m.bone("neck", (0, 35, -15), "body")
    tube(neck, catmull([(0, 34, -14), (0, 41, -20), (0, 47, -24)], 2), 9.4, 7.0, FUR, depth_ratio=1.2)
    for k in range(11):                                                         # fur ruff
        ang = math.radians(-150 + k * 30)
        b0 = (math.sin(ang) * 4.2, 38 + math.cos(ang) * 3.0, -18)
        spike(neck, b0, (b0[0] * 2.0, b0[1] - 5, -16), 3.6, FUR, steps=2)
    ring(neck, (0, 37.5, -17.5), 5.4, 12, ROPE, thickness=1.7, width=1.7, plane="xz")
    bell = m.bone("bell", (0, 33.5, -22), "neck")
    orb(bell, (0, 32.5, -22.2), 1.7, BELL)
    bell.add((-0.3, 31, -24.0), (0.6, 1.2, 0.6), L.solid("2a1a0a", 0.02))
    for sx in (-1, 1):                                                          # ofuda tags on the rope
        neck.add((sx * 4.0 - 0.8, 32.2, -19.8), (1.6, 3.6, 0.3), OF)
    # head
    head = m.bone("head", (0, 48, -25), "neck")
    bevel(head, (-5.8, 43.5, -34), (11.6, 9.6, 11), FUR, b=2.8)
    head.add((-5.2, 46.4, -34.25), (10.4, 6.2, 0.4), FUR, decals={"north": L.kitsune_face()})
    strut(head, (0, 46.0, -33.5), (0, 44.2, -44.5), 6.0, FUR, depth=5.0, soft=True)     # snout
    head.add((-1.3, 44.9, -45.1), (2.6, 2.0, 1.6), L.solid("1d1414", 0.02))             # nose
    head.add((-2.6, 42.6, -43.0), (5.2, 0.8, 8.0), VER)                                  # mouth line
    for sx in (-1, 1):
        head.add((sx * 3.0 - 1.2, 48.2, -34.45), (2.4, 1.1, 0.4), EYE, glow=True, rotation=(0, 0, sx * -14), pivot=(sx * 3.0, 48.7, -34.3))
        er = m.bone(f"ear_{'r' if sx < 0 else 'l'}", (sx * 3.2, 52, -28), "head")
        spike(er, (sx * 3.3, 51.5, -28), (sx * 6.6, 64, -25.5), 5.6, FUR, steps=3)
        spike(er, (sx * 3.4, 52.5, -29.2), (sx * 6.2, 61.5, -27.0), 3.0, VER, steps=2)
        spike(head, (sx * 5.6, 45, -30), (sx * 9.0, 42.5, -27.5), 3.2, FUR, steps=2)       # cheek fluff
    jaw = m.bone("jaw", (0, 43.5, -33), "head")
    strut(jaw, (0, 43.2, -33), (0, 42.4, -42.6), 4.6, FUR, depth=2.0, soft=True)

    # star pearl and moon halo (floating)
    pearl = m.bone("pearl", (0, 30, -29), "body", floating=True)
    orb(pearl, (0, 30, -29), 2.6, PEARL, glow=True)
    spike(pearl, (0, 31.8, -29), (0, 36.5, -29), 2.6, PEARL, glow=True, steps=2)
    halo = m.bone("halo", (0, 60, -16), "body", floating=True)
    ring(halo, (0, 60, -16), 10.5, 16, MOON, thickness=1.7, width=0.9, plane="xy", glow=True, arc=(-60, 230))
    ring(halo, (0, 60, -16.1), 8.4, 12, L.glow("e8f0ff", "8aa0ff", "u"), thickness=0.6, width=0.5, plane="xy", glow=True, arc=(-40, 210))
    for k in range(3):                                                         # foxfire wisps
        fb = m.bone(f"wisp{k}", (0, 30, 0), "root", floating=True)
        ang = k / 3 * 2 * math.pi
        orb(fb, (math.cos(ang) * 16, 40 + k * 3, math.sin(ang) * 14), 1.6, TIP, glow=True)

    # legs (vermilion socks, gold anklets)
    def leg(name, a, b, c, d, parent="body"):
        u = m.bone(name, a, parent)
        tube(u, [a, b], 6.0, 4.4, FUR)
        lo = m.bone(f"{name}_lo", b, name)
        tube(lo, [b, c], 3.8, 3.0, FURS)
        lo.add((c[0] - 2.0, c[1] + 0.4, c[2] - 2.0), (4.0, 1.2, 4.0), BELL)
        pw = m.bone(f"{name}_paw", c, f"{name}_lo")
        tube(pw, [c, (d[0], 2.2, d[2] + 0.5)], 3.0, 2.8, FURS)
        bevel(pw, (d[0] - 2.2, 0, d[2] - 3.6), (4.4, 2.8, 5.6), VER, b=0.7)
    for side, sx in (("r", -1), ("l", 1)):
        leg(f"fleg_{side}", (sx * 5.0, 27, -14), (sx * 5.4, 15.5, -12.5), (sx * 5.4, 5.0, -14), (sx * 5.4, 0, -15))
        leg(f"hleg_{side}", (sx * 5.6, 28, 12), (sx * 5.8, 18.5, 6.5), (sx * 5.8, 9.0, 15.5), (sx * 5.8, 0, 13.5))

    # nine tails (smooth catmull curves, fluffy in the middle, foxfire tips)
    for i in range(N_TAILS):
        pts = catmull(tail_points(i), 3)
        parent = "body"
        widths = [(4.6, 7.4), (7.8, 7.0), (6.6, 3.0)]
        for j in range(3):
            seg = pts[j * 3: j * 3 + 4]
            tb = m.bone(f"tail{i}_{j}", seg[0], parent)
            tube(tb, seg, widths[j][0], widths[j][1], FUR, overlap=1.0)
            parent = f"tail{i}_{j}"
        tip = m.bone(f"tailtip{i}", pts[-1], parent)
        d = tuple(pts[-1][k] - pts[-2][k] for k in range(3))
        ln = math.sqrt(sum(x * x for x in d)) or 1.0
        e = tuple(pts[-1][k] + d[k] / ln * 5.0 for k in range(3))
        tube(tip, [tuple(pts[-1][k] - d[k] / ln * 3.5 for k in range(3)), e], 4.6, 1.2, TIP, glow=True, overlap=0.3)
    # the tenth tail: rises straight behind the fan, bound with rope and ofuda (unsealed in phase III)
    r = TAIL_ROOT
    tpts = [r, (0, r[1] + 6, r[2] + 4), (0, r[1] + 18, r[2] + 7), (0, r[1] + 30, r[2] + 4)]
    parent = "body"
    for j in range(3):
        tb = m.bone(f"tailx_{j}", tpts[j], parent)
        tube(tb, [tpts[j], tpts[j + 1]], [4.6, 7.6, 6.2][j], [7.4, 6.4, 2.8][j], FUR, overlap=1.2)
        parent = f"tailx_{j}"
    seal = m.bone("seal", tpts[1], "tailx_1")
    for k in range(3):
        y = tpts[1][1] + 2 + k * 4.2
        z = tpts[1][2] + 0.6 + k * 0.3
        seal.add((-4.4, y, z - 4.2), (8.8, 1.4, 8.4), ROPE)
        seal.add((-0.9, y - 3.6, z - 4.6), (1.8, 3.6, 0.3), OF)
    unseal = m.bone("unseal", tpts[3], "tailx_2")
    tube(unseal, [(0, tpts[3][1] - 2, tpts[3][2] + 0.5), (0, tpts[3][1] + 6, tpts[3][2] - 1)], 5.4, 1.6, MOON, glow=True, overlap=0.3)
    ring(unseal, (0, tpts[3][1] + 2, tpts[3][2]), 4.5, 8, MOON, thickness=0.8, width=0.6, plane="xz", glow=True)
    _CACHE["model"] = m
    return m


# =========================================================================== animation
from animkit import A, T, Act, cs, loop, merge, sn


def _tails(fn):
    """Pose for all nine tails: fn(i) -> (rot_root, rot_mid, rot_tip)."""
    out = {}
    for i in range(N_TAILS):
        r0, r1, r2 = fn(i)
        out[f"tail{i}_0"] = {"r": r0}
        out[f"tail{i}_1"] = {"r": r1}
        out[f"tail{i}_2"] = {"r": r2}
    return out


def loops():
    idle = {
        "body": {"p": [0, sn(70, amp=0.4), 0]},
        "neck": {"r": [sn(60, amp=2), sn(24, amp=6), 0]},
        "head": {"r": [sn(60, 60, 3), sn(32, amp=7), sn(22, amp=5)]},
        "ear_r": {"r": [sn(110, amp=6), 0, sn(45, amp=6)]}, "ear_l": {"r": [sn(110, 90, 6), 0, sn(45, 50, -6)]},
        "jaw": {"r": [f"2 + {sn(90, amp=2)}", 0, 0]},
        "bell": {"r": [sn(140, amp=10), 0, sn(110, amp=8)]},
        "pearl": {"p": [0, sn(90, amp=1.2), 0], "r": [0, f"{T} * 60", 0]},
        "halo": {"r": [0, 0, f"{T} * 18"]},
        "tailx_0": {"r": [sn(40, amp=3), sn(30, amp=4), 0]}, "tailx_1": {"r": [sn(40, 60, 4), 0, sn(35, amp=4)]},
        "unseal": {"s": f"1 + {sn(200, amp=0.1)}"},
    }
    for k in range(3):
        idle[f"wisp{k}"] = {"r": [0, f"{T} * {40 + k * 12}", 0], "p": [0, sn(80, k * 90, 2), 0]}
    for i in range(N_TAILS):
        ph = i * 37
        idle[f"tail{i}_0"] = {"r": [sn(45, ph, 3), sn(38, ph, 4), sn(30, ph, 3)]}
        idle[f"tail{i}_1"] = {"r": [sn(45, ph + 50, 5), sn(38, ph + 60, 6), sn(30, ph + 40, 5)]}
        idle[f"tail{i}_2"] = {"r": [sn(45, ph + 100, 7), sn(38, ph + 120, 8), sn(30, ph + 90, 7)]}
    w = "variable.dist * 85"
    walk = {
        "fleg_r": {"r": [f"math.sin({w}) * 30", 0, 0]}, "fleg_r_lo": {"r": [f"math.max(0, math.sin({w} + 90)) * -42", 0, 0]},
        "fleg_l": {"r": [f"math.sin({w} + 180) * 30", 0, 0]}, "fleg_l_lo": {"r": [f"math.max(0, math.sin({w} + 270)) * -42", 0, 0]},
        "hleg_r": {"r": [f"math.sin({w} + 200) * 26", 0, 0]}, "hleg_r_lo": {"r": [f"math.max(0, math.sin({w} + 290)) * 30", 0, 0]},
        "hleg_l": {"r": [f"math.sin({w} + 20) * 26", 0, 0]}, "hleg_l_lo": {"r": [f"math.max(0, math.sin({w} + 110)) * 30", 0, 0]},
        "body": {"p": [0, f"math.abs(math.cos({w})) * 1.4", 0], "r": [f"math.sin(({w}) * 2) * 2", 0, 0]},
        "neck": {"r": [f"math.sin(({w}) * 2) * -3", 0, 0]},
        **{f"tail{i}_0": {"r": [f"math.sin(({w}) * 2 - {i * 20}) * 3", 0, 0]} for i in range(N_TAILS)},
    }
    eclipse = {   # phase III: the moon halo swells, the tails flare wider
        "halo": {"s": 1.35}, **{f"tail{i}_0": {"r": [0, 0, (i - 4) * -3]} for i in range(N_TAILS)},
    }
    return {"idle": loop(idle), "walk": loop(walk), "eclipse": loop(eclipse)}


def acts():
    out = []
    j = lambda x: {"jaw": {"r": (x, 0, 0)}}
    rest = {"neck": {"r": (0, 0, 0)}, "head": {"r": (0, 0, 0)}, "body": {"r": (0, 0, 0), "p": (0, 0, 0)}}
    fan = lambda k: _tails(lambda i: ((0, 0, (i - 4) * -k * 0.8), (0, 0, (i - 4) * -k * 0.6), (k * 0.5, 0, 0)))
    furl = lambda k: _tails(lambda i: ((k, 0, (i - 4) * k * 0.6), (k * 0.6, 0, 0), (k * 0.4, 0, 0)))
    crouch = lambda d: {"body": {"p": (0, -d, d * 0.3), "r": (d * 0.8, 0, 0)}, "fleg_r": {"r": (-d * 3, 0, 0)}, "fleg_l": {"r": (-d * 3, 0, 0)},
                        "hleg_r": {"r": (-d * 4, 0, 0)}, "hleg_l": {"r": (-d * 4, 0, 0)}, "hleg_r_lo": {"r": (d * 5, 0, 0)}, "hleg_l_lo": {"r": (d * 5, 0, 0)}}
    # 1 manifest (60, 40): rises from a ring of foxfire, tails unfurl like a fan
    a = Act("manifest", 60, [40])
    a.at(0, {"root": {"s": 0.2, "p": (0, 2, 0)}, **furl(40)})
    a.at(36, {"root": {"s": 1.0, "p": (0, 0, 0)}, **furl(30), **crouch(3)}, "out")
    a.at(40, {**fan(14), **crouch(-1), "neck": {"r": (-20, 0, 0)}, "head": {"r": (-20, 0, 0)}, **j(30)}, "in")
    a.at(60, {**fan(0), **crouch(0), **rest, **j(2)})
    out.append(a)
    # 2 howl (44, 16)
    a = Act("howl", 44, [16])
    a.at(12, {**crouch(2), "neck": {"r": (10, 0, 0)}, **furl(10)})
    a.at(16, {**crouch(-1), "neck": {"r": (-34, 0, 0)}, "head": {"r": (-26, 0, 0)}, **j(36), **fan(16)}, "in")
    a.at(34, {"neck": {"r": (-32, 0, 0)}, **j(32)}, "lin")
    a.at(44, {**crouch(0), **rest, **j(2), **fan(0)})
    out.append(a)
    # 3 pounce (24, 9)
    a = Act("pounce", 24, [9])
    a.at(7, {**crouch(5), **furl(10)})
    a.at(10, {**crouch(-2), "body": {"r": (-14, 0, 0)}, "fleg_r": {"r": (-70, 0, 0)}, "fleg_l": {"r": (-70, 0, 0)}, "hleg_r": {"r": (40, 0, 0)}, "hleg_l": {"r": (40, 0, 0)}, **j(30)}, "in")
    a.at(20, {"body": {"r": (8, 0, 0)}, "fleg_r": {"r": (-20, 0, 0)}, "fleg_l": {"r": (-20, 0, 0)}, "hleg_r": {"r": (10, 0, 0)}, "hleg_l": {"r": (10, 0, 0)}}, "lin")
    a.at(24, {**crouch(0), **rest, "fleg_r": {"r": (0, 0, 0)}, "fleg_l": {"r": (0, 0, 0)}, **furl(0), **j(2)}, "out")
    out.append(a)
    # 4 swipe (20, 9)
    a = Act("swipe", 20, [9])
    a.at(6, {"fleg_r": {"r": (-70, 30, -20)}, "fleg_r_lo": {"r": (-40, 0, 0)}, "body": {"r": (0, -10, 0)}, "head": {"r": (0, 14, 0)}})
    a.at(9, {"fleg_r": {"r": (-20, -30, 20)}, "fleg_r_lo": {"r": (0, 0, 0)}, "body": {"r": (0, 12, 0)}, "head": {"r": (0, -10, 0)}, **j(20)}, "in")
    a.at(20, {"fleg_r": {"r": (0, 0, 0)}, **rest, **j(2)})
    out.append(a)
    # 5 tail_lash (32, 16): spins, the tails scythe around her
    a = Act("tail_lash", 32, [16])
    a.at(10, {**furl(-10), "root": {"r": (0, 50, 0)}, **crouch(2)})
    a.at(16, {**fan(20), "root": {"r": (0, -300, 0)}}, "in")
    a.at(32, {**fan(0), "root": {"r": (0, -360, 0)}, **crouch(0)}, "out")
    out.append(a)
    # 6 foxfire (32, 14)
    a = Act("foxfire", 32, [14])
    a.at(10, {**fan(12), "neck": {"r": (-12, 0, 0)}, "head": {"r": (-8, 0, 0)}, **j(18), "pearl": {"s": 1.4}})
    a.at(14, {**fan(6), "neck": {"r": (8, 0, 0)}, "head": {"r": (10, 0, 0)}, **j(26), "pearl": {"s": 1.0}}, "in")
    a.at(32, {**fan(0), **rest, **j(2)})
    out.append(a)
    # 7 lanterns (40, 20): rings the bell with a head toss
    a = Act("lanterns", 40, [20])
    a.at(14, {"neck": {"r": (-10, -20, 0)}, "head": {"r": (-10, -10, -10)}, "bell": {"r": (40, 0, 0)}})
    a.at(20, {"neck": {"r": (6, 20, 0)}, "head": {"r": (6, 10, 10)}, "bell": {"r": (-50, 0, 0)}}, "in")
    a.at(40, {**rest, "bell": {"r": (0, 0, 0)}})
    out.append(a)
    # 8 illusion (40, 24): twirls and blurs
    a = Act("illusion", 40, [24])
    a.at(18, {"root": {"r": (0, 360, 0)}, **fan(10)}, "io")
    a.at(24, {"root": {"r": (0, 400, 0), "s": 0.9}}, "in")
    a.at(40, {"root": {"r": (0, 360, 0), "s": 1.0}, **fan(0)}, "out")
    out.append(a)
    # 9 torii (44, 24): stamps, raising the gates
    a = Act("torii", 44, [24])
    a.at(18, {**crouch(-2), "fleg_r": {"r": (-50, 0, 0)}, "fleg_l": {"r": (-50, 0, 0)}, "body": {"r": (-16, 0, 0)}}, "out")
    a.at(24, {**crouch(2), "fleg_r": {"r": (6, 0, 0)}, "fleg_l": {"r": (6, 0, 0)}, "body": {"r": (4, 0, 0)}}, "in")
    a.at(44, {**crouch(0), **rest, "fleg_r": {"r": (0, 0, 0)}, "fleg_l": {"r": (0, 0, 0)}})
    out.append(a)
    # 10 tail_spikes (48, 20): drives the tails into the earth
    a = Act("tail_spikes", 48, [20])
    a.at(14, {**_tails(lambda i: ((-30, 0, (i - 4) * -2), (-20, 0, 0), (-10, 0, 0))), **crouch(2)}, "out")
    a.at(20, {**_tails(lambda i: ((40, 0, (i - 4) * 3), (50, 0, 0), (40, 0, 0))), **crouch(4)}, "in")
    a.at(40, {**_tails(lambda i: ((36, 0, (i - 4) * 3), (46, 0, 0), (36, 0, 0)))}, "lin")
    a.at(48, {**_tails(lambda i: ((0, 0, 0), (0, 0, 0), (0, 0, 0))), **crouch(0)})
    out.append(a)
    # 11 kagura (80, 12, 28, 44, 60): sacred dance - leaps and lands on each beat
    a = Act("kagura", 80, [12, 28, 44, 60])
    for i, mk in enumerate([12, 28, 44, 60]):
        s = 1 if i % 2 == 0 else -1
        a.at(mk - 6, {"body": {"p": (0, 6, 0), "r": (-8, s * 30, s * 10)}, **fan(16), "neck": {"r": (-16, s * -20, 0)}, "bell": {"r": (s * 40, 0, 0)}}, "out")
        a.at(mk, {"body": {"p": (0, -2, 0), "r": (4, s * 60, 0)}, **fan(4), "neck": {"r": (8, 0, 0)}, "bell": {"r": (-s * 30, 0, 0)}}, "in")
    a.at(80, {**rest, **fan(0), "neck": {"r": (0, 0, 0)}, "bell": {"r": (0, 0, 0)}})
    out.append(a)
    # 12 eclipse (220, 40, 192): ULT - rises into the moon, ten rays wheel, then implosion
    a = Act("eclipse", 220, [40, 192])
    a.at(36, {**fan(24), "body": {"r": (-12, 0, 0)}, "neck": {"r": (-20, 0, 0)}, "head": {"r": (-14, 0, 0)}, **j(20), "halo": {"s": 1.8},
              "fleg_r": {"r": (-40, 0, 0)}, "fleg_l": {"r": (-40, 0, 0)}, "hleg_r": {"r": (20, 0, 0)}, "hleg_l": {"r": (20, 0, 0)}}, "out")
    a.at(40, {"halo": {"s": 2.2}}, "in")
    a.at(176, {**fan(24), "halo": {"s": 2.2}}, "lin")
    a.at(186, {**furl(30), "body": {"r": (10, 0, 0)}, "halo": {"s": 0.6}, **j(40)}, "in")
    a.at(192, {**fan(30), "body": {"r": (-14, 0, 0)}, "halo": {"s": 2.6}, "neck": {"r": (-30, 0, 0)}}, "in")
    a.at(220, {**fan(0), **rest, "halo": {"s": 1.0}, **j(2), "fleg_r": {"r": (0, 0, 0)}, "fleg_l": {"r": (0, 0, 0)}, "hleg_r": {"r": (0, 0, 0)}, "hleg_l": {"r": (0, 0, 0)}}, "out")
    out.append(a.overlay("halo", "r", [0, 0, f"{A} * 240"]))
    # 13 unseal (80, 50): the ropes burn, the tenth tail blazes moon-silver
    a = Act("unseal", 80, [50])
    a.at(30, {**crouch(3), "tailx_0": {"r": (-20, 0, 0)}, "tailx_1": {"r": (-20, 0, 0)}, "neck": {"r": (16, 0, 0)}, "seal": {"s": 1.0}})
    a.at(50, {**crouch(-2), "tailx_0": {"r": (14, 0, 0)}, "tailx_1": {"r": (10, 0, 0)}, "neck": {"r": (-30, 0, 0)}, "head": {"r": (-20, 0, 0)}, **j(36), "seal": {"s": 0.01},
              **fan(20)}, "in")
    a.at(80, {**crouch(0), **rest, "tailx_0": {"r": (0, 0, 0)}, "tailx_1": {"r": (0, 0, 0)}, **j(2), **fan(0)})
    out.append(a)
    # 14 dash (20, loop)
    a = Act("dash", 20, [], loop=True)
    g = f"math.sin({A} * 1440)"
    a.at(0, {**furl(16), "neck": {"r": (16, 0, 0)}}).at(20, {**furl(16), "neck": {"r": (16, 0, 0)}}, "lin")
    a.overlay("fleg_r", "r", [f"{g} * 50", 0, 0]).overlay("fleg_l", "r", [f"{g} * 44", 0, 0])
    a.overlay("hleg_r", "r", [f"-{g} * 44", 0, 0]).overlay("hleg_l", "r", [f"-{g} * 50", 0, 0])
    out.append(a)
    # 15 death (80, 68): the tails fold into moonlight
    a = Act("death", 80, [68])
    a.at(20, {"neck": {"r": (-30, 0, 0)}, "head": {"r": (-24, 0, 0)}, **j(30), **fan(20)}, "out")
    a.at(50, {"body": {"p": (0, -10, 0), "r": (4, 0, 10)}, "fleg_r": {"r": (-60, 0, 0)}, "fleg_l": {"r": (-60, 0, 0)}, "fleg_r_lo": {"r": (-80, 0, 0)},
              "fleg_l_lo": {"r": (-80, 0, 0)}, "neck": {"r": (34, 0, 0)}, "head": {"r": (20, 0, 20)}, **furl(30)}, "io")
    a.at(68, {"root": {"s": 1.0}}, "lin")
    a.at(80, {"root": {"s": 0.02, "p": (0, 18, 0)}}, "in")
    out.append(a)
    # 16 procession (70, 16, 56): fox wedding - she bows, lanterns march, sun-shower falls
    a = Act("procession", 70, [16, 56])
    a.at(12, {**crouch(3), "neck": {"r": (26, 0, 0)}, "head": {"r": (14, 0, 0)}, **fan(8)}, "io")
    a.at(16, {"bell": {"r": (50, 0, 0)}}, "in")
    a.at(50, {"neck": {"r": (-10, 0, 0)}, "head": {"r": (-14, 0, 0)}, **fan(18), **crouch(0), "bell": {"r": (-20, 0, 0)}}, "io")
    a.at(56, {"neck": {"r": (6, 0, 0)}, **j(24), "bell": {"r": (40, 0, 0)}}, "in")
    a.at(70, {**rest, **fan(0), **j(2), "bell": {"r": (0, 0, 0)}})
    out.append(a)
    return out


def entity_cfg():
    return {
        "scale": SCALE,
        "textures": {"default": f"textures/entity/legends/{KEY}", "v1": f"textures/entity/legends/{KEY}"},
        "pre": [
            "variable.walkw = variable.mv * variable.calm;",
            "variable.ecl = math.lerp(variable.ecl ?? 0.0, variable.ph >= 3 ? 1.0 : 0.0, 0.05);",
        ],
        "animate": [{"idle": "variable.calm + 0.15"}, {"walk": "variable.walkw"}, {"eclipse": "variable.ecl"}, "ctrl_act"],
        "visibility": [{"seal": "variable.ph < 3"}, {"unseal": "variable.ph >= 3"}],
        "bounds": (10, 10, 3.0),
    }


def extra_entities(RP, m, built_acts):
    """The Foxfire Illusion: same geometry and animations, pale additive body."""
    import json
    import os
    desc = {
        "identifier": "legends:tenko_illusion",
        "materials": {"default": "entity_beam_additive", "glow": "entity_beam_additive"},
        "textures": {"default": "textures/entity/legends/tenko_illusion"},
        "geometry": {"default": ID, "glow": ID + ".glow"},
        "animations": {"idle": f"animation.legends.{KEY}.idle", "walk": f"animation.legends.{KEY}.walk",
                       **{f"a_{n}": f"animation.legends.{KEY}.act.{n}" for n in built_acts[KEY]},
                       "ctrl_act": f"controller.animation.legends.{KEY}.act"},
        "scripts": {"scale": str(SCALE), "pre_animation": [
            "variable.act = query.property('legends:act');", "variable.ph = query.property('legends:phase');",
            "variable.calm = math.lerp(variable.calm ?? 1.0, variable.act == 0 ? 1.0 : 0.15, 0.14);",
            "variable.mv = math.lerp(variable.mv ?? 0.0, query.property('legends:move'), 0.2);",
            "variable.dist = (variable.dist ?? 0.0) + query.delta_time * variable.mv * 6.0;",
            "variable.t = (variable.t ?? 0.0) + query.delta_time;", "variable.walkw = variable.mv * variable.calm;"],
            "animate": [{"idle": "variable.calm + 0.15"}, {"walk": "variable.walkw"}, "ctrl_act"]},
        "render_controllers": ["controller.render.legends.tenko_illusion"],
    }
    path = os.path.join(RP, "entity", "legends", "tenko_illusion.entity.json")
    with open(path, "w") as f:
        json.dump({"format_version": "1.10.0", "minecraft:client_entity": {"description": desc}}, f, indent=1)
    rc = {"format_version": "1.8.0", "render_controllers": {"controller.render.legends.tenko_illusion": {
        "geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"],
        "part_visibility": [{"*": True}, {"seal": False}, {"unseal": False}, {"halo": False}]}}}
    with open(os.path.join(RP, "render_controllers", "legends", "tenko_illusion.rc.json"), "w") as f:
        json.dump(rc, f, indent=1)


ALSO_PROVIDES = ["tenko_illusion"]


if __name__ == "__main__":
    import sys
    from modelkit import render_preview, zfight_report, island_report, deflicker
    out = sys.argv[1]
    m = build()
    m.paint()
    print(m.stats())
    print("islands", island_report(m))
    print("zfight", len(zfight_report(m)), "after deflicker", deflicker(m))
    render_preview([m], f"{out}/tenko_a.png", yaw=40, pitch=12, size=700, step=1, pose={"unseal": {"scale": 0.001}})
    render_preview([m], f"{out}/tenko_b.png", yaw=-150, pitch=12, size=700, step=1, pose={"seal": {"scale": 0.001}})
