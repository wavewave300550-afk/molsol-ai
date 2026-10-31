"""
NIDHOGG (Níðhöggr) - Gnawer of the World-Root. Remastered model.

A corpse-dark wyvern: it walks on the wrists of its folded wings like a bat, with a long S-neck,
a skull crowned by gnarled antlers that look like torn roots of Yggdrasil, venom-green eyes and
veins, a pale bone belly, tattered membranes and a serpentine tail ending in a tuft of root
tendrils. Rest geometry = wings spread (flight). The ground stance is the `fold` loop (IK-solved).

Scale 1.8 -> ~8.9 model units per block. Faces -Z. Mouth ~ (0, 23, -86): 9.7 blocks ahead, 2.6 up.
"""
import math

from modelkit import Model
from shapes import bevel, spike, strut
from shapes2 import catmull, feather, tube
import lmat as L

ID = "geometry.legends.nidhogg"
KEY = "nidhogg"
SCALE = 1.8
VARIANTS = {"default": "default", "ragnarok": "v1"}
_CACHE = {}

S_R = (-8.0, 36.0, -16.0)      # wing shoulder (upper back)
E_R = (-32.0, 37.0, -18.0)     # elbow
W_R = (-60.0, 39.0, -24.0)     # wrist
FINGERS = {"wf1": (-90.0, 40.0, -29.0), "wf2": (-86.0, 39.0, 2.0), "wf3": (-66.0, 38.0, 20.0)}


def _yaw_to(dx, dz):
    return math.degrees(math.atan2(dx, -dz))


def _fan(bone, origin, a_tip, b_tip, k, mat, y_off=0.0, scallop=0.9):
    """Membrane between two rays from origin (tips a_tip, b_tip) built from k thin strips."""
    ax, az = a_tip[0] - origin[0], a_tip[2] - origin[2]
    bx, bz = b_tip[0] - origin[0], b_tip[2] - origin[2]
    th_a, th_b = math.atan2(ax, -az), math.atan2(bx, -bz)
    if th_b - th_a > math.pi:
        th_b -= 2 * math.pi
    if th_a - th_b > math.pi:
        th_b += 2 * math.pi
    la, lb = math.hypot(ax, az), math.hypot(bx, bz)
    dth = (th_b - th_a) / k
    for j in range(k):
        t = (j + 0.5) / k
        th = th_a + (th_b - th_a) * t
        ln = (la + (lb - la) * t) * scallop * (0.94 + 0.06 * math.cos((t - 0.5) * math.pi))
        w = 2 * ln * 0.6 * abs(math.tan(dth / 2)) * 1.45 + 0.8
        feather(bone, (origin[0], origin[1] + y_off + 0.07 * j, origin[2]), ln, w, math.degrees(th), 0, mat, thick=0.5)


def build():
    m = Model(ID, seed=23, density=2)
    SC = L.wyrm_scale()
    SCD = L.wyrm_scale("141a12", "2f3a22")
    BN = L.bone_plate()
    MEM = L.membrane()
    HORN = L.root_horn()
    CLAW = L.claw_dark()
    VEN = L.glow("f0ffc0", "38e83a", "r")
    EYE = L.glow("ffffe0", "7dff3a", "r")

    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 26, 0), "root")
    bevel(body, (-11.5, 17, -28), (23, 20, 24), SC, b=4)
    bevel(body, (-10.5, 16, -8), (21, 18.5, 22), SC, b=4)
    bevel(body, (-9.5, 18, 10), (19, 15.5, 17), SC, b=4)
    for z in range(-24, 24, 6):                                          # bone belly plates
        w = 14 if z < 10 else 11
        body.add((-w / 2, 15.2 if z < 10 else 17.2, z), (w, 2.2, 5.2), BN)
    for i, z in enumerate(range(-26, 26, 5)):                           # spinal thorns
        top = 37 if z < -6 else (34.5 if z < 10 else 33.5)
        h = 6 + (3 if i % 2 == 0 else 0) - (2 if z > 10 else 0)
        spike(body, (0, top - 1, z), (0, top + h, z + 4), 3.0, HORN, steps=3)
        if i % 2 == 1:
            for sx in (-1, 1):
                spike(body, (sx * 7, top - 2.5, z), (sx * 11, top + 2, z + 3), 1.8, HORN, steps=2)
    for sx in (-1, 1):                                                   # venom veins (glow)
        body.add((sx * 11.1 - 0.3, 24, -22), (0.6, 1.0, 30), VEN, glow=True)
        body.add((sx * 10.6 - 0.3, 28.5, -20), (0.6, 0.8, 22), VEN, glow=True)

    # ------------------------------------------------------------------ neck (S-curve) and skull
    npts = [(0, 30, -24), (0, 34, -34), (0, 35, -44), (0, 33, -54), (0, 29, -63)]
    parent = "body"
    for i in range(4):
        nb = m.bone(f"neck{i}", npts[i], parent)
        tube(nb, [npts[i], npts[i + 1]], 12 - i * 1.2, 10.6 - i * 1.2, SC, overlap=1.4)
        a, b = npts[i], npts[i + 1]
        mid = tuple((a[k] + b[k]) / 2 for k in range(3))
        spike(nb, (mid[0], mid[1] + 4.2 - i * 0.6, mid[2]), (mid[0], mid[1] + 10 - i, mid[2] + 4), 2.6, HORN, steps=2)
        nb.add((-3.5, mid[1] - 6.1 + i * 0.6, mid[2] - 3), (7, 1.6, 6), BN)    # throat plate
        parent = f"neck{i}"
    head = m.bone("head", (0, 29, -63), parent)
    bevel(head, (-9, 24, -83), (18, 12, 22), SC, b=3)                     # skull
    bevel(head, (-6.5, 22.6, -94), (13, 8.6, 12), SC, b=2.4)              # snout
    head.add((-4.5, 31.0, -94.4), (9, 0.9, 8), SCD)                         # nasal ridge
    for sx in (-1, 1):
        head.add((sx * 2.8 - 1.0, 28.6, -94.5), (2.0, 1.4, 0.8), L.solid("0b0f08", 0.02))   # nostrils
        bevel(head, (sx * 6.6 - 3.3, 33.4, -82), (6.6, 3.8, 10), SCD, b=0.9)   # brow ridge
        head.add((sx * 8.1 - 1.4, 30.2, -81), (2.8, 2.2, 4.2), EYE, glow=True)                   # eye
        spike(head, (sx * 8.6, 25, -71), (sx * 15, 22.5, -65), 2.6, HORN, steps=2)              # cheek spike
        spike(head, (sx * 8.0, 26, -76), (sx * 13, 25, -72), 1.8, HORN, steps=2)
        hb = m.bone(f"horn_{'r' if sx < 0 else 'l'}", (sx * 6, 35, -72), "head")
        main = catmull([(sx * 6, 35, -73), (sx * 11, 42, -66), (sx * 15, 47, -56), (sx * 15, 52, -45), (sx * 12, 55, -36)], 3)
        tube(hb, main, 4.4, 1.2, HORN, overlap=0.5)
        for (k, d) in ((3, (sx * 7, 7, -3)), (6, (sx * 8, 4, 3)), (9, (sx * 3, 8, 2))):
            p0 = main[k]
            tine = catmull([p0, (p0[0] + d[0] * 0.5, p0[1] + d[1] * 0.6, p0[2] + d[2] * 0.4), (p0[0] + d[0], p0[1] + d[1], p0[2] + d[2])], 2)
            tube(hb, tine, 2.2, 0.7, HORN, overlap=0.4)
    for k in range(6):                                                       # upper teeth
        for sx in (-1, 1):
            z = -92.5 + k * 3.2
            spike(head, (sx * 5.5, 23.2, z), (sx * 5.4, 19.8 if k % 2 == 0 else 20.9, z - 0.3), 1.3, L.ivory(), steps=2)
    jaw = m.bone("jaw", (0, 25, -70), "head")
    bevel(jaw, (-6, 18.6, -93), (12, 5.2, 25), SC, b=1.4)
    jaw.add((-4, 23.4, -90), (8, 0.9, 19), L.solid("4a1015", 0.05))      # tongue
    for k in range(6):
        for sx in (-1, 1):
            z = -91 + k * 3.2
            spike(jaw, (sx * 5.0, 23.4, z), (sx * 4.9, 26.0 if k % 2 else 27.0, z + 0.2), 1.2, L.ivory(), steps=2)
    for k in range(3):
        spike(jaw, (0, 18.8, -87 + k * 6), (0, 14.0, -86 + k * 6), 2.0, HORN, steps=2)   # chin spikes
    jaw.add((-2.5, 20.2, -80), (5, 0.6, 3), VEN, glow=True)                                 # venom drool glow

    # ------------------------------------------------------------------ wings (rest = spread)
    for side, sx in (("r", 1), ("l", -1)):
        S = (sx * S_R[0], S_R[1], S_R[2])
        E = (sx * E_R[0], E_R[1], E_R[2])
        Wp = (sx * W_R[0], W_R[1], W_R[2])
        wa = m.bone(f"wing_{side}", S, "body")
        tube(wa, [S, E], 7, 5.6, SC, overlap=1.2)
        wf = m.bone(f"wfore_{side}", E, f"wing_{side}")
        tube(wf, [E, Wp], 5.4, 4.0, SC, overlap=1.2)
        spike(wf, Wp, (Wp[0] + sx * -2, Wp[1] + 2, Wp[2] - 6), 2.4, CLAW, steps=3)          # thumb claw
        inner = m.bone(f"wmem0_{side}", S, f"wing_{side}")                                    # inner membrane
        hip = (sx * -9, 33.5, 18.0)
        _fan(inner, S, E, hip, 3, MEM, y_off=-0.6, scallop=0.97)
        inner2 = m.bone(f"wmem0b_{side}", E, f"wfore_{side}")
        f3 = (sx * FINGERS["wf3"][0], FINGERS["wf3"][1], FINGERS["wf3"][2])
        _fan(inner2, E, Wp, (hip[0] * 0.4 + f3[0] * 0.6, 34, hip[2] * 0.4 + f3[2] * 0.6), 3, MEM, y_off=-0.4, scallop=0.95)
        hand = m.bone(f"whand_{side}", Wp, f"wfore_{side}")
        tips = {}
        for fn, tip in FINGERS.items():
            tp = (sx * tip[0], tip[1], tip[2])
            tips[fn] = tp
            fb = m.bone(f"{fn}_{side}", Wp, f"whand_{side}")
            tube(fb, [Wp, tp], 3.4 if fn == "wf1" else 2.8, 1.0, SC, overlap=0.8)
            spike(fb, tp, (tp[0] + sx * -2.5 if fn == "wf1" else tp[0], tp[1], tp[2] - 3.5), 1.4, CLAW, steps=2)
        for i, (a, b) in enumerate((("wf1", "wf2"), ("wf2", "wf3"))):
            mb = m.bone(f"wmem{i + 1}_{side}", Wp, f"whand_{side}")
            _fan(mb, Wp, tips[a], tips[b], 5, MEM, y_off=-0.5 - 0.3 * i)
        mb = m.bone(f"wmem3_{side}", Wp, f"whand_{side}")
        _fan(mb, Wp, tips["wf3"], E, 3, MEM, y_off=-0.9, scallop=0.85)

    # ------------------------------------------------------------------ front legs
    for side, sx in (("r", -1), ("l", 1)):
        Sh, K, A, F = (sx * 10.5, 24, -20), (sx * 13, 14, -25), (sx * 13, 4, -21), (sx * 13, 1.5, -25)
        ua = m.bone(f"arm_{side}", Sh, "body")
        tube(ua, [Sh, K], 8.5, 6.5, SC, overlap=1.4)
        fa = m.bone(f"fore_{side}", K, f"arm_{side}")
        tube(fa, [K, A], 6.0, 4.6, SC, overlap=1.0)
        hd = m.bone(f"hand_{side}", A, f"fore_{side}")
        tube(hd, [A, F], 4.6, 4.2, SC, overlap=0.6)
        for dx in (-2.2, 0, 2.2):
            spike(hd, (F[0] + dx, 1.6, F[2] - 1), (F[0] + dx * 1.5, 0.2, F[2] - 7), 1.8, CLAW, steps=3)

    # ------------------------------------------------------------------ hind legs
    for side, sx in (("r", -1), ("l", 1)):
        Hh, K, A, F = (sx * 12, 28, 18), (sx * 14, 17, 9), (sx * 14.5, 7, 22), (sx * 14.5, 1.5, 17)
        th = m.bone(f"thigh_{side}", Hh, "body")
        tube(th, [Hh, K], 10, 7.5, SC, overlap=1.5)
        sh = m.bone(f"shin_{side}", K, f"thigh_{side}")
        tube(sh, [K, A], 6.5, 4.6, SC, overlap=1.0)
        ft = m.bone(f"foot_{side}", A, f"shin_{side}")
        tube(ft, [A, F], 4.6, 4.0, SC, overlap=0.8)
        for k, dx in enumerate((-2.4, 0, 2.4)):
            spike(ft, (F[0] + dx, 1.6, F[2] - 1), (F[0] + dx * 1.6, 0.2, F[2] - 8), 1.9, CLAW, steps=3)
        spike(ft, (F[0], 2.0, F[2] + 2), (F[0], 0.3, F[2] + 6), 1.6, CLAW, steps=2)

    # ------------------------------------------------------------------ tail with root tendrils
    tp = [(0, 29, 25), (0, 27, 37), (0, 23, 49), (0, 19, 61), (0, 16, 73), (0, 14, 85), (0, 13, 96)]
    parent = "body"
    for i in range(6):
        tb = m.bone(f"tail{i}", tp[i], parent)
        tube(tb, [tp[i], tp[i + 1]], 13 - i * 1.7, 11.5 - i * 1.7, SC, overlap=1.4)
        mid = tuple((tp[i][k] + tp[i + 1][k]) / 2 for k in range(3))
        spike(tb, (0, mid[1] + 4.5 - i * 0.7, mid[2]), (0, mid[1] + 9 - i * 1.0, mid[2] + 4), 2.6 - i * 0.25, HORN, steps=2)
        parent = f"tail{i}"
    tip = m.bone("tail_tip", tp[-1], parent)
    for d in ((5, 3, 9), (-5, 3, 9), (0, 6, 10), (3, -2, 10), (-3, -2, 9)):
        pts = catmull([tp[-1], (tp[-1][0] + d[0] * 0.5, tp[-1][1] + d[1] * 0.3, tp[-1][2] + d[2] * 0.6), (tp[-1][0] + d[0], tp[-1][1] + d[1], tp[-1][2] + d[2])], 2)
        tube(tip, pts, 2.4, 0.7, HORN, overlap=0.5)
    tip.add((-1.2, 12.2, 96.5), (2.4, 1.6, 2.4), VEN, glow=True)
    _CACHE["model"] = m
    return m


# =========================================================================== poses
from animkit import A, T, Act, cs, loop, merge, sn


def fold_pose(m=None):
    """Ground stance: the wings fold onto the back - elbows peak above the shoulders, forearms run
    back along the flanks, the closed hands point to the tail (2-bone IK)."""
    import aim
    m = m or _CACHE.get("model") or build()
    pose = {}
    for side, sx in (("r", 1), ("l", -1)):
        S = (sx * S_R[0], S_R[1], S_R[2])
        E = (sx * E_R[0], E_R[1], E_R[2])
        Wp = (sx * W_R[0], W_R[1], W_R[2])
        L1, L2 = math.dist(S, E), math.dist(E, Wp)
        wrist = (sx * -15, 33.0, 16.0)
        elbow = aim.two_bone(S, wrist, L1, L2, (sx * -0.55, 0.85, 0.0))
        pose, _ = aim.chain(m, pose, [
            (f"wing_{side}", E, elbow, (0, 1, 2)),
            (f"wfore_{side}", Wp, wrist, (0, 1, 2)),
        ])
        f2 = (sx * FINGERS["wf2"][0], FINGERS["wf2"][1], FINGERS["wf2"][2])
        pose, _ = aim.chain(m, pose, [(f"whand_{side}", f2, (sx * -14, 40, 40), (0, 1, 2))])
        pose[f"whand_{side}"]["scale"] = 0.75
        pose[f"wf1_{side}"] = {"rot": (0, sx * -38, 0)}
        pose[f"wf3_{side}"] = {"rot": (0, sx * 30, 0)}
        for k in ("wmem1", "wmem2", "wmem3"):
            pose[f"{k}_{side}"] = {"scale": 0.22}
        pose[f"wmem0_{side}"] = {"scale": 0.25}
        pose[f"wmem0b_{side}"] = {"scale": 0.3}
    return pose


def _r(p):
    return {b: {k: v for k, v in d.items()} for b, d in p.items()}


def loops():
    fp = fold_pose()
    fold = {}
    for b, d in fp.items():
        e = {}
        if "rot" in d:
            e["r"] = list(d["rot"])
        if "scale" in d:
            e["s"] = d["scale"]
        fold[b] = e
    fold["neck0"] = {"r": [-6, 0, 0]}
    fold["neck2"] = {"r": [10, 0, 0]}
    idle = {
        "body": {"p": [0, sn(55, amp=0.5), 0], "r": [sn(55, amp=0.6), 0, 0]},
        "neck0": {"r": [sn(40, amp=2.5), sn(18, amp=6), 0]},
        "neck1": {"r": [sn(40, 50, 2.5), sn(18, 40, 6), 0]},
        "neck2": {"r": [sn(40, 100, 3), sn(18, 80, 5), 0]},
        "head": {"r": [sn(40, 140, 3), sn(25, amp=4), sn(15, amp=3)]},
        "jaw": {"r": [f"4 + {sn(95, amp=3)}", 0, 0]},
        "horn_r": {"r": [0, 0, sn(30, amp=1)]}, "horn_l": {"r": [0, 0, sn(30, 90, 1)]},
        "tail_tip": {"r": [sn(60, amp=10), sn(45, amp=16), 0]},
    }
    for i in range(6):
        idle[f"tail{i}"] = {"r": [sn(40, -i * 35, 2 + i * 0.6), sn(30, -i * 45, 5 + i * 1.4), 0]}
    w = "variable.dist * 55"
    walk = {
        "thigh_r": {"r": [f"math.sin({w}) * 20", 0, 0]}, "shin_r": {"r": [f"math.max(0, math.sin({w} + 90)) * 22", 0, 0]},
        "thigh_l": {"r": [f"math.sin({w} + 180) * 20", 0, 0]}, "shin_l": {"r": [f"math.max(0, math.sin({w} + 270)) * 22", 0, 0]},
        "arm_r": {"r": [f"math.sin({w} + 270) * 18", 0, 0]}, "fore_r": {"r": [f"math.max(0, math.sin({w})) * -20", 0, 0]},
        "arm_l": {"r": [f"math.sin({w} + 90) * 18", 0, 0]}, "fore_l": {"r": [f"math.max(0, math.sin({w} + 180)) * -20", 0, 0]},
        "hand_r": {"r": [f"math.max(0, math.sin({w})) * 16", 0, 0]}, "hand_l": {"r": [f"math.max(0, math.sin({w} + 180)) * 16", 0, 0]},
        "body": {"r": [0, f"math.sin({w}) * 3", f"math.sin({w}) * 2"], "p": [0, f"math.cos(({w}) * 2) * 0.6", 0]},
        "neck0": {"r": [0, f"math.sin({w}) * -4", 0]},
        **{f"tail{i}": {"r": [0, f"math.sin({w} - {i * 40}) * {4 + i}", 0]} for i in range(6)},
    }
    flap = f"math.sin({T} * 150)"
    fly = {
        "wing_r": {"r": [0, 0, f"{flap} * -26 - 4"]}, "wing_l": {"r": [0, 0, f"{flap} * 26 + 4"]},
        "wfore_r": {"r": [0, 0, f"math.sin({T} * 150 - 40) * -16"]}, "wfore_l": {"r": [0, 0, f"math.sin({T} * 150 - 40) * 16"]},
        "whand_r": {"r": [0, 0, f"math.sin({T} * 150 - 80) * -12"]}, "whand_l": {"r": [0, 0, f"math.sin({T} * 150 - 80) * 12"]},
        "body": {"p": [0, f"math.sin({T} * 150 + 180) * 2.4", 0], "r": [f"-6 + math.sin({T} * 150) * 2", 0, 0]},
        "thigh_r": {"r": [48, 0, 0]}, "thigh_l": {"r": [48, 0, 0]}, "shin_r": {"r": [30, 0, 0]}, "shin_l": {"r": [30, 0, 0]},
        "foot_r": {"r": [40, 0, 0]}, "foot_l": {"r": [40, 0, 0]},
        "arm_r": {"r": [-50, 0, 0]}, "arm_l": {"r": [-50, 0, 0]}, "fore_r": {"r": [70, 0, 0]}, "fore_l": {"r": [70, 0, 0]},
        "neck0": {"r": [8, 0, 0]}, "neck2": {"r": [-8, 0, 0]},
        **{f"tail{i}": {"r": [f"math.sin({T} * 90 - {i * 40}) * {2 + i}", 0, 0]} for i in range(6)},
    }
    rage = {   # phase III: neck raised, horns flared, constant tremor
        "neck0": {"r": [-8, 0, 0]}, "head": {"r": [4, 0, f"math.sin({T} * 1100) * 0.8"]},
        "jaw": {"r": [f"6 + math.sin({T} * 300) * 2", 0, 0]},
        "horn_r": {"r": [0, 0, -6]}, "horn_l": {"r": [0, 0, 6]},
    }
    return {"idle": loop(idle), "walk": loop(walk), "fold": loop(fold), "fly": loop(fly), "rage": loop(rage)}


def acts():
    out = []
    jaw = lambda x: {"jaw": {"r": (x, 0, 0)}}
    neck = lambda a, b, c, y=0: {"neck0": {"r": (a, y, 0)}, "neck1": {"r": (b, y * 0.6, 0)}, "neck2": {"r": (c, y * 0.4, 0)}}
    # 1 emerge (72, 48): bursts from the roots
    a = Act("emerge", 72, [48])
    a.at(0, {"root": {"p": (0, -40, 6)}, **neck(-30, -10, 10), **jaw(20)})
    a.at(30, {"root": {"p": (0, -12, 2)}, **neck(-20, -10, 0)}, "out")
    a.at(44, {"root": {"p": (0, 0, 0)}, **neck(10, 6, 4), "head": {"r": (12, 0, 0)}, **jaw(4)}, "out")
    a.at(48, {**neck(-26, -14, -8), "head": {"r": (-20, 0, 0)}, **jaw(50), "body": {"r": (-6, 0, 0)}}, "in")
    a.at(64, {**neck(-24, -12, -8, 8), **jaw(46)}, "lin")
    a.at(72, {**neck(0, 0, 0), "head": {"r": (0, 0, 0)}, **jaw(5), "body": {"r": (0, 0, 0)}})
    a.overlay("root", "p", [f"math.sin({A} * 2400) * 0.35", 0, 0])
    out.append(a)
    # 2 roar (44, 12): Ragnarök - the veins blaze
    a = Act("roar", 44, [12])
    a.at(8, {**neck(10, 6, 6), "head": {"r": (14, 0, 0)}, **jaw(0), "body": {"p": (0, -2, 0)}})
    a.at(12, {**neck(-30, -16, -10), "head": {"r": (-24, 0, 0)}, **jaw(56), "body": {"p": (0, 2, 0), "r": (-8, 0, 0)},
              "horn_r": {"r": (0, 0, -10)}, "horn_l": {"r": (0, 0, 10)}}, "in")
    a.at(34, {**neck(-28, -14, -10, -10), **jaw(52)}, "lin")
    a.at(44, {**neck(0, 0, 0), "head": {"r": (0, 0, 0)}, **jaw(6), "body": {"p": (0, 0, 0), "r": (0, 0, 0)},
              "horn_r": {"r": (0, 0, 0)}, "horn_l": {"r": (0, 0, 0)}})
    out.append(a.overlay("head", "r", [0, 0, f"math.sin({A} * 1500) * 1.5"]))
    # 3 bite (26, 12): coil back, lunge
    a = Act("bite", 26, [12])
    a.at(9, {**neck(14, 18, -10), "head": {"r": (-12, 0, 0)}, **jaw(40), "body": {"p": (0, 0, 4), "r": (4, 0, 0)}}, "out")
    a.at(12, {**neck(-14, -8, 10), "head": {"r": (10, 0, 0)}, **jaw(-3), "body": {"p": (0, -1, -6), "r": (-2, 0, 0)}}, "in")
    a.at(26, {**neck(0, 0, 0), "head": {"r": (0, 0, 0)}, **jaw(4), "body": {"p": (0, 0, 0), "r": (0, 0, 0)}})
    out.append(a)
    # 4 tail_sweep (30, 15)
    a = Act("tail_sweep", 30, [15])
    tails = lambda y: {f"tail{i}": {"r": (0, y * (0.5 + i * 0.25), 0)} for i in range(6)}
    a.at(11, {**tails(-16), "body": {"r": (0, 10, 0)}, **neck(0, 0, 0, -14)}, "out")
    a.at(15, {**tails(22), "body": {"r": (0, -14, 0)}, **neck(0, 0, 0, 16)}, "in")
    a.at(21, {**tails(14), "body": {"r": (0, -6, 0)}}, "out")
    a.at(30, {**tails(0), "body": {"r": (0, 0, 0)}, **neck(0, 0, 0, 0)})
    out.append(a)
    # 5 burrow (32, 24): dives head-first into the ground
    a = Act("burrow", 32, [24])
    a.at(10, {**neck(10, 10, 10), "head": {"r": (24, 0, 0)}, **jaw(10), "body": {"r": (8, 0, 0)}})
    a.at(24, {"root": {"p": (0, -28, -6)}, "body": {"r": (24, 0, 0)}, **neck(24, 16, 10)}, "in")
    a.at(32, {"root": {"p": (0, -60, -6)}}, "lin")
    out.append(a.overlay("root", "p", [f"math.sin({A} * 2600) * 0.5", 0, 0]))
    # 6 underground (20): hidden
    a = Act("underground", 20, [], loop=True)
    a.at(0, {"root": {"p": (0, -80, 0)}}).at(20, {"root": {"p": (0, -80, 0)}}, "lin")
    out.append(a)
    # 7 erupt (32, 5)
    a = Act("erupt", 32, [5])
    a.at(0, {"root": {"p": (0, -50, 0)}, **neck(-36, -20, -10), "head": {"r": (-30, 0, 0)}, **jaw(50)})
    a.at(5, {"root": {"p": (0, 6, 0)}, "body": {"r": (-14, 0, 0)}}, "in")
    a.at(16, {"root": {"p": (0, 0, 0)}, **neck(-18, -10, -6), **jaw(40)}, "out")
    a.at(32, {"body": {"r": (0, 0, 0)}, **neck(0, 0, 0), "head": {"r": (0, 0, 0)}, **jaw(5)})
    out.append(a)
    # 8 root_snare (30, 16): claws the earth, roots answer
    a = Act("root_snare", 30, [16])
    a.at(10, {"wing_r": {"r": (-20, 0, 0)}, "wing_l": {"r": (-20, 0, 0)}, "body": {"p": (0, 3, 0), "r": (-8, 0, 0)}, **neck(-10, -6, 0), **jaw(30)})
    a.at(16, {"wing_r": {"r": (12, 0, 0)}, "wing_l": {"r": (12, 0, 0)}, "body": {"p": (0, -2, 0), "r": (4, 0, 0)}, **neck(14, 6, 6), **jaw(10)}, "in")
    a.at(30, {"wing_r": {"r": (0, 0, 0)}, "wing_l": {"r": (0, 0, 0)}, "body": {"p": (0, 0, 0), "r": (0, 0, 0)}, **neck(0, 0, 0), **jaw(4)})
    out.append(a)
    # 9 takeoff (36, 20): the wings unfurl, great downbeat
    a = Act("takeoff", 36, [20])
    a.at(12, {"body": {"p": (0, -4, 0), "r": (6, 0, 0)}, "thigh_r": {"r": (-16, 0, 0)}, "thigh_l": {"r": (-16, 0, 0)},
              "wing_r": {"r": (0, 0, 30)}, "wing_l": {"r": (0, 0, -30)}})
    a.at(20, {"body": {"p": (0, 6, 0), "r": (-10, 0, 0)}, "thigh_r": {"r": (30, 0, 0)}, "thigh_l": {"r": (30, 0, 0)},
              "wing_r": {"r": (0, 0, -34)}, "wing_l": {"r": (0, 0, 34)}, **neck(-16, -6, 0), **jaw(30)}, "in")
    a.at(36, {"body": {"p": (0, 0, 0), "r": (0, 0, 0)}, "wing_r": {"r": (0, 0, 0)}, "wing_l": {"r": (0, 0, 0)}, **neck(0, 0, 0), **jaw(4),
              "thigh_r": {"r": (0, 0, 0)}, "thigh_l": {"r": (0, 0, 0)}}, "out")
    out.append(a)
    # 10 land (28, 12)
    a = Act("land", 28, [12])
    a.at(10, {"wing_r": {"r": (0, 0, 24)}, "wing_l": {"r": (0, 0, -24)}, "body": {"p": (0, 4, 0)}})
    a.at(12, {"body": {"p": (0, -3, 0), "r": (5, 0, 0)}}, "in")
    a.at(28, {"wing_r": {"r": (0, 0, 0)}, "wing_l": {"r": (0, 0, 0)}, "body": {"p": (0, 0, 0), "r": (0, 0, 0)}}, "out")
    out.append(a)
    # 11 strafe (20, loop): low glide, venom pouring from the jaws
    a = Act("strafe", 20, [], loop=True)
    a.at(0, {**neck(14, 6, 8), "head": {"r": (14, 0, 0)}, **jaw(34), "wing_r": {"r": (0, 0, 10)}, "wing_l": {"r": (0, 0, -10)}, "body": {"r": (8, 0, 0)}})
    a.at(20, {**neck(14, 6, 8), "head": {"r": (14, 0, 0)}, **jaw(34), "wing_r": {"r": (0, 0, 10)}, "wing_l": {"r": (0, 0, -10)}, "body": {"r": (8, 0, 0)}}, "lin")
    out.append(a.overlay("jaw", "r", [f"math.sin({A} * 900) * 4", 0, 0]))
    # 12 breath (60, 16): rears, then sweeps venom-frost breath left to right
    a = Act("breath", 60, [16])
    a.at(12, {**neck(-24, -14, -4), "head": {"r": (-16, 0, 0)}, **jaw(16), "body": {"r": (-8, 0, 0)}}, "out")
    a.at(16, {**neck(8, 8, 10, -38), "head": {"r": (18, 0, 0)}, **jaw(48), "body": {"r": (4, 0, 0)}}, "in")
    a.at(52, {**neck(8, 8, 10, 38), "head": {"r": (18, 0, 0)}, **jaw(48)}, "lin")
    a.at(60, {**neck(0, 0, 0, 0), "head": {"r": (0, 0, 0)}, **jaw(5), "body": {"r": (0, 0, 0)}})
    out.append(a)
    # 13 gale (36, 14, 28): two crushing wingbeats
    a = Act("gale", 36, [14, 28])
    for mk in (14, 28):
        a.at(mk - 6, {"wing_r": {"r": (-10, 0, 46)}, "wing_l": {"r": (-10, 0, -46)}, "wfore_r": {"r": (0, 0, 20)}, "wfore_l": {"r": (0, 0, -20)},
                      "body": {"p": (0, -2, 2), "r": (-6, 0, 0)}}, "out")
        a.at(mk, {"wing_r": {"r": (14, 0, -40)}, "wing_l": {"r": (14, 0, 40)}, "wfore_r": {"r": (0, 0, -24)}, "wfore_l": {"r": (0, 0, 24)},
                  "body": {"p": (0, 3, -2), "r": (6, 0, 0)}}, "in")
    a.at(36, {"wing_r": {"r": (0, 0, 0)}, "wing_l": {"r": (0, 0, 0)}, "wfore_r": {"r": (0, 0, 0)}, "wfore_l": {"r": (0, 0, 0)}, "body": {"p": (0, 0, 0), "r": (0, 0, 0)}})
    out.append(a)
    # 14 dive (34, 23): folds the wings and falls like a spear
    a = Act("dive", 34, [23])
    a.at(10, {"wing_r": {"r": (0, 0, 40)}, "wing_l": {"r": (0, 0, -40)}, **neck(-10, -4, 0), **jaw(30)})
    a.at(14, {"wing_r": {"r": (-30, -40, -10)}, "wing_l": {"r": (-30, 40, 10)}, "body": {"r": (36, 0, 0)}, **neck(10, 6, 4), **jaw(46)}, "in")
    a.at(23, {"body": {"r": (30, 0, 0)}, **jaw(-3), "wing_r": {"r": (-10, -10, 30)}, "wing_l": {"r": (-10, 10, -30)}}, "lin")
    a.at(30, {"body": {"r": (-4, 0, 0)}, "wing_r": {"r": (0, 0, -20)}, "wing_l": {"r": (0, 0, 20)}}, "out")
    a.at(34, {"body": {"r": (0, 0, 0)}, "wing_r": {"r": (0, 0, 0)}, "wing_l": {"r": (0, 0, 0)}, **neck(0, 0, 0), **jaw(4)})
    out.append(a)
    # 15 ascend (48, 24): climbs into the sky
    a = Act("ascend", 48, [24])
    a.at(24, {"body": {"r": (-34, 0, 0)}, **neck(-20, -10, -6), **jaw(40), "wing_r": {"r": (0, 0, 20)}, "wing_l": {"r": (0, 0, -20)}}, "out")
    a.at(48, {"body": {"r": (-10, 0, 0)}, **neck(-10, -4, 0), **jaw(20), "wing_r": {"r": (0, 0, 0)}, "wing_l": {"r": (0, 0, 0)}})
    out.append(a.overlay("wing_r", "r", [0, 0, f"math.sin({A} * 500) * -30"]).overlay("wing_l", "r", [0, 0, f"math.sin({A} * 500) * 30"]))
    # 16 ragnarok (140): hovering high, howling the corpse-fire down
    a = Act("ragnarok", 140, [])
    a.at(16, {**neck(-28, -16, -10), "head": {"r": (-22, 0, 0)}, **jaw(58), "body": {"r": (-12, 0, 0)}}, "out")
    a.at(124, {**neck(-26, -14, -10), **jaw(54)}, "lin")
    a.at(140, {**neck(-10, -4, 0), "head": {"r": (-6, 0, 0)}, **jaw(20), "body": {"r": (-4, 0, 0)}})
    out.append(a.overlay("head", "r", [0, f"math.sin({A} * 140) * 14", f"math.sin({A} * 1700) * 1.4"]))
    # 17 rupture (44, 26): plunges into the World-Root
    a = Act("rupture", 44, [26])
    a.at(16, {"body": {"r": (40, 0, 0)}, **neck(16, 10, 6), **jaw(50), "wing_r": {"r": (-30, -30, 0)}, "wing_l": {"r": (-30, 30, 0)}}, "out")
    a.at(26, {"body": {"r": (20, 0, 0)}, **neck(30, 16, 10), "head": {"r": (20, 0, 0)}, **jaw(-4)}, "in")
    a.at(44, {"body": {"r": (6, 0, 0)}, **neck(20, 10, 6), **jaw(10), "wing_r": {"r": (0, 0, 30)}, "wing_l": {"r": (0, 0, -30)}}, "out")
    out.append(a)
    # 18 exhausted (80): collapsed, gasping - the reward window
    a = Act("exhausted", 80, [], loop=False)
    a.at(14, {"body": {"p": (0, -8, 0), "r": (6, 0, 6)}, **neck(24, 16, 10, -12), "head": {"r": (24, 0, 16)}, **jaw(26),
              "thigh_r": {"r": (-20, 0, 0)}, "thigh_l": {"r": (-20, 0, 0)}}, "out")
    a.at(80, {"body": {"p": (0, -8, 0), "r": (6, 0, 6)}, **neck(24, 16, 10, -12), **jaw(30)}, "lin")
    out.append(a.overlay("jaw", "r", [f"math.sin({A} * 260) * 8", 0, 0]).overlay("body", "p", [0, f"math.sin({A} * 260) * 0.6", 0]))
    # 19 coil (48, 36): the tail coils around the target, then constricts
    a = Act("coil", 48, [36])
    coil = lambda y, x=0: {f"tail{i}": {"r": (x, y * (0.6 + i * 0.25), 0)} for i in range(6)}
    a.at(14, {**coil(30, -4), "body": {"r": (0, -18, 0)}, **neck(0, 0, 0, 20), **jaw(20)}, "out")
    a.at(32, {**coil(44, -6), "body": {"r": (0, -24, 0)}}, "io")
    a.at(36, {**coil(56, 4), "body": {"r": (0, -8, 0)}, **jaw(46)}, "in")
    a.at(48, {**coil(0), "body": {"r": (0, 0, 0)}, **neck(0, 0, 0, 0), **jaw(4)})
    out.append(a)
    # 20 death (100, 84): the World-Root reclaims it
    a = Act("death", 100, [84])
    a.at(16, {**neck(-30, -16, -10), "head": {"r": (-24, 0, 0)}, **jaw(54), "body": {"r": (-8, 0, 0)}}, "out")
    a.at(50, {**neck(30, 20, 14, -20), "head": {"r": (30, 0, 20)}, **jaw(30), "body": {"p": (0, -10, 0), "r": (6, 0, 12)},
              "wing_r": {"r": (0, 0, 40)}, "wing_l": {"r": (0, 0, -20)}, "thigh_r": {"r": (-30, 0, 0)}}, "io")
    a.at(84, {"root": {"p": (0, -14, 0)}, **neck(36, 24, 16, -24), "head": {"r": (34, 0, 26)}, **jaw(36)}, "out")
    a.at(100, {"root": {"p": (0, -40, 0), "s": 0.6}}, "in")
    out.append(a.overlay("body", "p", [f"math.sin({A} * 1800) * 0.4", 0, 0]))
    return out


def entity_cfg():
    return {
        "scale": SCALE,
        "textures": {"default": f"textures/entity/legends/{KEY}", "v1": f"textures/entity/legends/{KEY}_v1"},
        "pre": [
            "variable.flyw = math.lerp(variable.flyw ?? 0.0, query.property('legends:var') == 1 ? 1.0 : 0.0, 0.08);",
            "variable.walkw = variable.mv * (1.0 - variable.flyw) * variable.calm;",
            "variable.rage = math.lerp(variable.rage ?? 0.0, variable.ph >= 3 ? 1.0 : 0.0, 0.05);",
        ],
        "animate": [{"idle": "variable.calm + 0.15"}, {"fold": "1.0 - variable.flyw"}, {"walk": "variable.walkw"},
                    {"fly": "variable.flyw"}, {"rage": "variable.rage"}, "ctrl_act"],
        "texture_expr": "Array.skins[variable.ph >= 3 ? 1 : 0]",
        "skins": ["Texture.default", "Texture.v1"],
        "visibility": [],
        "bounds": (24, 10, 2.0),
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
    render_preview([m], f"{out}/nid_fly.png", yaw=35, pitch=25, size=760, step=2)
    render_preview([m], f"{out}/nid_ground.png", yaw=35, pitch=15, size=760, step=2, pose=fp)
    render_preview([m], f"{out}/nid_side.png", yaw=-95, pitch=8, size=760, step=2, pose=fp)
