"""
TAOTIE (饕餮) - the Devouring Maw. Remastered model.

A Shang-dynasty ritual bronze come alive, after Paoxiao of the Shan Hai Jing: goat body,
human hands with tiger claws, a colossal taotie-mask head with curled ram horns, a gaping maw and
eyes that open beneath its armpits (phase II). In phase III it has devoured its own body and the
head flies on a vortex of bronze shards.

Scale 1.6 -> 10 model units = 1 block. Model faces -Z. Mouth ~ (0, 30, -58): 5.6 blocks ahead, 3 up
(matches Taotie.mouth() in the script). Phase III head offset is applied by the `form3` animation.
"""
import math

from modelkit import Model
from shapes import bevel, orb, ring, spike, strut
from shapes2 import catmull, stepped_flange, tube
import lmat as L

ID = "geometry.legends.taotie"


def build():
    m = Model(ID, seed=11, density=2)
    BZ = L.bronze("cast", lei=True)
    BZP = L.bronze("plate", lei=False, patina=0.05)
    BZL = L.bronze("plate", lei=True, cell=6)
    BZD = L.bronze("dark", patina=0.0)
    GD = L.gold()
    IV = L.ivory()
    GUL = L.gullet()
    HOOF = L.hoof()
    EYE = L.solid("f1dfa0", 0.03)

    root = m.bone("root", (0, 0, 0))
    hull = m.bone("hull", (0, 34, 0), "root")

    # ------------------------------------------------------------------ torso: heavy front, tapering rump
    t = m.bone("torso", (0, 34, 0), "hull")
    bevel(t, (-17, 20, -24), (34, 32, 18), BZ, b=4)                 # chest
    bevel(t, (-15.5, 23, -8), (31, 27, 20), BZ, b=4)                # barrel
    bevel(t, (-14, 27, 10), (28, 21, 12), BZ, b=4)                  # rump
    bevel(t, (-15, 46, -23), (30, 10, 17), BZ, b=4)                 # shoulder hump
    bevel(t, (-11, 18, -18), (22, 6, 26), BZD, b=2)                 # belly
    # armour bands with leiwen, gold rims
    for z, w in ((-7.4, 18.2), (11.0, 16.8)):
        bevel(t, (-w, 21.6, z), (2 * w, 30.6 if z < 0 else 27.8, 2.8), BZL, b=1.0)
        t.add((-w - 0.4, (51.6 if z < 0 else 48.8), z + 0.5), (2 * w + 0.8, 0.9, 1.8), GD)
    # flank taotie masks (relief plates) with rivets
    for side in (-1, 1):
        x0 = -16.6 if side < 0 else 15.4
        t.add((x0, 25, -3.6), (1.2, 22, 14.2), BZP, decals={"east" if side < 0 else "west": L.taotie_mask_decal()})
        for k in range(8):
            a = k / 8 * 2 * math.pi
            xr = x0 - 0.5 if side < 0 else x0 + 0.9
            t.add((xr, 36 + math.sin(a) * 12 - 0.7, 3.5 + math.cos(a) * 8.6 - 0.7), (0.8, 1.4, 1.4), GD)
    # chest pectoral plate
    bevel(t, (-12, 25, -25.8), (24, 20, 2.4), BZP, b=1, decals={"north": L.taotie_mask_decal()})
    # spine flanges (扉棱): tall at the shoulders, lower towards the rump
    for i, (z, base, hs) in enumerate(((-21, 55.2, [7, 11, 8, 12]), (-14, 55.2, [9, 12, 10, 8]), (-6, 49.4, [6, 9, 7, 9]),
                                        (1, 49.4, [5, 8, 6, 7]), (8, 49.4, [4, 7, 5, 6]), (15, 47.4, [3, 5, 4, 3]))):
        fb = m.bone(f"flange{i}", (0, base, z + 3), "torso")
        stepped_flange(fb, -1.2, 1.2, base, z, z + 6.4, hs, BZP)
        fb.add((-1.5, base + max(hs) - 0.8, z + 2.2), (3.0, 1.4, 2.0), GD)

    # ------------------------------------------------------------------ armpit eyes (Paoxiao)
    for side, sx in (("r", -1), ("l", 1)):
        xo = -18.6 if sx < 0 else 16.6
        sock = m.bone(f"pit_{side}", (sx * 17.5, 31, -15), "torso")
        sock.add((xo, 26.5, -21), (2.0, 10, 12), BZD)
        for yy in (25.8, 36.2):
            sock.add((xo + (-0.3 if sx < 0 else 0.3), yy, -21.6), (2.0, 1.2, 13.2), GD)
        lid = m.bone(f"lid_{side}", (sx * 18.5, 31.5, -15), f"pit_{side}")
        lid.add((xo + (-0.7 if sx < 0 else 0.7), 27, -20.4), (2.0, 9, 10.8), BZP)
        lid.add((xo + (-0.9 if sx < 0 else 0.9), 31.1, -20.6), (2.0, 0.8, 11.2), BZD)
        ge = m.bone(f"pitglow_{side}", (sx * 18.5, 31.5, -15), f"pit_{side}")
        ge.add((xo + (-0.6 if sx < 0 else 0.6), 27.6, -19.8), (2.0, 7.8, 9.6), L.glow("fff0a0", "ff5a10", "r"), glow=True,
               decals={"east" if sx < 0 else "west": L.bulging_eye("fff7c8", "3a0800")})

    # ------------------------------------------------------------------ front limbs (human hands with tiger claws)
    for side, sx in (("r", -1), ("l", 1)):
        X = sx * 18
        sh = m.bone(f"shoulder_{side}", (X, 42, -16), "hull")
        bevel(sh, (X - 7, 35, -23), (14, 14, 14), BZP, b=2.5)
        sh.add((X - 7.4, 48.4, -23.4), (14.8, 1.0, 14.8), GD)
        sh.add((X - 2, 49.2, -18), (4, 4, 4), GD)                             # boss stud
        arm = m.bone(f"arm_{side}", (X, 40, -16), f"shoulder_{side}")
        bevel(arm, (X - 5.5, 21, -21.5), (11, 19, 11), BZ, b=2.2)
        fo = m.bone(f"fore_{side}", (X, 22, -16), f"arm_{side}")
        bevel(fo, (X - 5, 6, -21), (10, 17, 10), BZ, b=2)
        fo.add((X - 5.5, 14.5, -21.5), (11, 2.6, 11), GD)                    # bracer
        fo.add((X - 5.5, 9.5, -21.5), (11, 1.8, 11), BZL)
        hand = m.bone(f"hand_{side}", (X, 6.5, -16), f"fore_{side}")
        bevel(hand, (X - 6, 0.6, -28), (12, 7, 17), BZ, b=1.6)
        hand.add((X - 4.5, 7.4, -26), (9, 0.9, 10), BZP)
        for k in range(4):
            fx = X - 4.6 + k * 3.0
            fg = m.bone(f"fing_{side}{k}", (fx + 1.2, 3.5, -28), f"hand_{side}")
            bevel(fg, (fx, 0.4, -34.5), (2.5, 4.4, 7), BZ, b=0.5)
            spike(fg, (fx + 1.25, 1.8, -34.5), (fx + 1.25, -0.2, -39.5), 2.0, IV, steps=3)
        thx = X + (6.4 if sx < 0 else -6.4)
        th = m.bone(f"thumb_{side}", (thx, 3.5, -22), f"hand_{side}")
        bevel(th, (thx - 1.4, 0.6, -28.5), (2.8, 3.8, 6.5), BZ, b=0.5)
        spike(th, (thx, 1.6, -28.5), (thx + (1.0 if sx < 0 else -1.0), 0, -32.5), 1.7, IV, steps=2)

    # ------------------------------------------------------------------ hind limbs (goat legs)
    for side, sx in (("r", -1), ("l", 1)):
        X = sx * 13
        th = m.bone(f"thigh_{side}", (X, 38, 15), "hull", rotation=(-18, 0, 0))
        bevel(th, (X - 6.5, 22, 7), (13, 20, 15), BZ, b=3)
        th.add((X - 6.9, 33, 6.6), (13.8, 2.2, 15.8), GD)
        sh = m.bone(f"shin_{side}", (X, 23.5, 15), f"thigh_{side}", rotation=(44, 0, 0))
        bevel(sh, (X - 4.2, 9.5, 11), (8.4, 16, 8), BZ, b=1.6)
        cn = m.bone(f"cannon_{side}", (X, 10, 15), f"shin_{side}", rotation=(-26, 0, 0))
        bevel(cn, (X - 3.2, 0.6, 12), (6.4, 10.4, 6), BZ, b=1.2)
        cn.add((X - 3.6, 7, 11.6), (7.2, 1.6, 6.8), GD)
        hf = m.bone(f"hoof_{side}", (X, 0.6, 15), f"cannon_{side}")
        for ox in (-1, 1):
            bevel(hf, (X + ox * 1.9 - 1.8, -2.2, 10.2), (3.6, 3.2, 6.6), HOOF, b=0.6)
        hf.add((X - 1.2, 0.8, 17.3), (2.4, 2.2, 1.6), HOOF)

    # ------------------------------------------------------------------ tail
    tl0 = m.bone("tail0", (0, 44, 20), "hull")
    pts0 = catmull([(0, 44, 19), (0, 42, 26), (0, 38, 31)], 2)
    tube(tl0, pts0, 9.0, 7.5, BZ)
    tl1 = m.bone("tail1", (0, 38, 31), "tail0")
    pts1 = catmull([(0, 38, 31), (0, 35, 36), (0, 36, 41), (0, 40, 44)], 2)
    tube(tl1, pts1, 7.0, 4.5, BZ)
    tl2 = m.bone("tail2", (0, 40, 44), "tail1")
    stepped_flange(tl2, -1.0, 1.0, 38.5, 41.5, 49, [4, 7, 9, 6], BZP)          # flame finial
    tl2.add((-2.6, 39.5, 42.5), (5.2, 4, 3), GD)

    # ------------------------------------------------------------------ neck + head
    neck = m.bone("neck", (0, 46, -22), "root")
    nm = m.bone("neck_mesh", (0, 46, -22), "neck")
    bevel(nm, (-12, 34, -37), (24, 20, 16), BZ, b=4)
    for k in range(3):
        stepped_flange(nm, -1.0, 1.0, 53.4, -36 + k * 5, -31 + k * 5, [3, 5, 4], BZP)

    head = m.bone("head", (0, 44, -36), "neck")
    bevel(head, (-17, 37, -60), (34, 25, 26), BZ, b=4.5)                 # cranium
    bevel(head, (-20, 52, -63.5), (40, 7, 10), BZP, b=2)                 # brow ridge
    head.add((-20.5, 58.6, -63.9), (41, 1.0, 9.6), GD)
    head.add((-1.7, 41, -63.6), (3.4, 17, 3.8), BZP)                     # central nose flange
    head.add((-2.4, 58.8, -62.5), (4.8, 3.6, 4.8), GD)                   # forehead boss
    for sx in (-1, 1):
        ex = sx * 9.8
        bevel(head, (ex - 6, 41, -62.6), (12, 10.4, 5), EYE, b=1.2)        # bulging eyeball
        head.add((ex - 6.6, 50.6, -63.2), (13.2, 2.0, 6), BZP)            # upper lid
        head.add((ex - 6.6, 40.0, -63.0), (13.2, 1.6, 5.6), BZP)          # lower lid
        head.add((ex - 4.6, 42.4, -62.95), (9.2, 7.8, 0.4), L.glow("fff6c0", "ff8a1a", "r"), glow=True,
                 decals={"north": L.bulging_eye()})
        ch = m.bone(f"cheek_{'r' if sx < 0 else 'l'}", (sx * 17, 44, -46), "head")
        cx0 = sx * 17 + (-5 if sx < 0 else 0)
        stepped_flange(ch, cx0, cx0 + 5, 31, -59, -38, [16, 21, 23, 21, 15], BZP)
        ch.add((cx0 - 0.2, 42, -57), (5.4, 1.4, 16), GD)
    # snout / upper jaw
    bevel(head, (-14, 30, -68), (28, 13, 18), BZ, b=3)
    head.add((-14.5, 42.4, -68.4), (29, 1.2, 8), GD)
    for sx in (-1, 1):
        head.add((sx * 5.5 - 2.4, 37.5, -68.6), (4.8, 3.2, 1.0), L.solid("1d0f06", 0.02))
    for k in range(7):
        x = -7.5 + k * 2.5
        head.add((x - 0.8, 27.8, -67.4), (1.6, 2.4, 1.6), IV)
    for sx in (-1, 1):
        for k in range(4):
            head.add((sx * 12.4 - 0.8, 27.8, -64 + k * 3.8), (1.6, 2.4, 1.6), IV)
        spike(head, (sx * 9.4, 30.5, -66.2), (sx * 8.8, 19.5, -66.6), 3.0, IV, steps=4)   # tiger fangs
    head.add((-11, 27, -62), (22, 10, 14), GUL)
    head.add((-7, 28.5, -51.2), (14, 7, 1.0), L.glow("ffd27a", "ff3a12", "r"), glow=True)
    # great curled horns framing the face
    for side, sx in (("r", -1), ("l", 1)):
        hb = m.bone(f"horn_{side}", (sx * 12, 60, -42), "head")
        ctrl = [(12, 58, -40), (17, 67, -35), (26, 70, -33), (34, 64, -36), (36, 54, -43), (32, 46, -50), (27, 47, -55), (25.5, 52, -56)]
        pts = catmull([(sx * p[0], p[1], p[2]) for p in ctrl], 3)
        tube(hb, pts, 8.0, 2.4, L.horn_bronze(), overlap=0.7)
        for k in (3, 7, 11):
            a, b = pts[k], pts[k + 1]
            strut(hb, a, tuple(a[i] + (b[i] - a[i]) * 0.4 for i in range(3)), 8.6 - k * 0.42, GD)
        tip = pts[-1]
        spike(hb, tip, (tip[0] - sx * 1.5, tip[1] + 2.5, tip[2] - 2.0), 2.4, GD, steps=2)

    # lower jaw
    jaw = m.bone("jaw", (0, 33, -46), "head")
    bevel(jaw, (-13, 21, -66.5), (26, 9, 23), BZ, b=2.5)
    jaw.add((-13.5, 20.4, -67), (27, 1.2, 9), GD)
    jaw.add((-7, 29.6, -62), (14, 1.4, 15), L.solid("8c2333", 0.06))
    for k in range(7):
        x = -7.5 + k * 2.5
        jaw.add((x - 0.75, 29.8, -65.6), (1.5, 2.2, 1.5), IV)
    for sx in (-1, 1):
        for k in range(4):
            jaw.add((sx * 11.4 - 0.75, 29.8, -62 + k * 3.8), (1.5, 2.2, 1.5), IV)
        spike(jaw, (sx * 5.6, 29.5, -65), (sx * 5.4, 37.5, -65.4), 2.4, IV, steps=3)
    stepped_flange(jaw, -1.1, 1.1, 16.5, -65, -50, [4, 6, 5, 3], BZP)

    # ------------------------------------------------------------------ vortex (phase III only)
    vx = m.bone("vortex", (0, 10, -12), "root", floating=True)
    SH = L.bronze("plate", lei=True, cell=5)
    for name, y, r, n, sp in (("vortex_a", 12, 15, 14, 0), ("vortex_b", 2, 11, 11, 0.4), ("vortex_c", -8, 7, 8, 0.8)):
        vb = m.bone(name, (0, y, -12), "vortex", floating=True)
        ring(vb, (0, y, -12), r, n, SH, thickness=2.6, width=2.0, plane="xz", jag=[1.0, 1.7, 0.8, 1.4], phase=sp)
        ring(vb, (0, y + 2.2, -12), r * 0.75, max(6, n - 4), BZD, thickness=1.6, width=1.2, plane="xz", phase=sp + 0.2)
    core = m.bone("vortex_core", (0, 4, -12), "vortex", floating=True)
    orb(core, (0, 4, -12), 6, L.glow("f3d2ff", "6a2a9a", "r"), glow=True)
    orb(core, (0, -6, -12), 3.5, L.glow("ffb3e8", "4a1a6a", "r"), glow=True)
    return m


# =========================================================================== animation
from animkit import A, T, Act, cs, loop, merge, mirror, sn, sym

KEY = "taotie"
SCALE = 1.6
VARIANTS = {"default": "default", "heated": "v1"}       # texture variants (phase II+)
W = "variable.dist * 60"                                # stride clock (deg)


def loops():
    idle = {
        "hull": {"p": [0, sn(70, amp=0.5), 0], "r": [sn(70, amp=0.5), 0, 0]},
        "neck": {"r": [sn(45, amp=2), sn(22, amp=5), 0]},
        "head": {"r": [sn(45, 40, 2), sn(28, amp=3), sn(19, amp=1.5)]},
        "jaw": {"r": [f"3 + {sn(110, amp=3)}", 0, 0]},
        "tail0": {"r": [sn(50, amp=4), sn(33, amp=10), 0]},
        "tail1": {"r": [sn(50, 40, 6), sn(33, 50, 14), 0]},
        "tail2": {"r": [sn(50, 80, 6), sn(33, 100, 16), 0]},
        "pitglow_r": {"s": f"1 + {sn(160, amp=0.07)}"}, "pitglow_l": {"s": f"1 + {sn(160, 90, 0.07)}"},
        "vortex_a": {"r": [0, f"{T} * 90", 0]}, "vortex_b": {"r": [0, f"-{T} * 140", 0]},
        "vortex_c": {"r": [0, f"{T} * 220", 0]}, "vortex_core": {"s": f"1 + {sn(200, amp=0.12)}"},
        "vortex": {"p": [sn(40, amp=1.2), sn(60, amp=1.5), 0], "r": [sn(30, amp=4), 0, cs(30, amp=4)]},
    }
    for k in range(4):
        for sd in ("r", "l"):
            idle[f"fing_{sd}{k}"] = {"r": [sn(70, k * 30, 4), 0, 0]}
    w = W
    walk = {
        "hull": {"p": [0, f"math.cos(({w}) * 2) * 0.9", 0], "r": [0, 0, f"math.sin({w}) * 1.6"]},
        "neck": {"r": [f"math.cos(({w}) * 2) * -2", f"math.sin({w}) * 3", 0]},
        "shoulder_r": {"r": [f"math.sin({w} + 90) * 17", 0, 0]},
        "fore_r": {"r": [f"math.max(0, math.sin({w} + 180)) * -26", 0, 0]},
        "hand_r": {"r": [f"math.sin({w} + 90) * -17 + math.max(0, math.sin({w} + 180)) * 22", 0, 0]},
        "shoulder_l": {"r": [f"math.sin({w} + 270) * 17", 0, 0]},
        "fore_l": {"r": [f"math.max(0, math.sin({w})) * -26", 0, 0]},
        "hand_l": {"r": [f"math.sin({w} + 270) * -17 + math.max(0, math.sin({w})) * 22", 0, 0]},
        "thigh_r": {"r": [f"math.sin({w}) * 16", 0, 0]},
        "shin_r": {"r": [f"math.max(0, math.sin({w} + 90)) * 18", 0, 0]},
        "cannon_r": {"r": [f"math.max(0, math.sin({w} + 90)) * -14", 0, 0]},
        "thigh_l": {"r": [f"math.sin({w} + 180) * 16", 0, 0]},
        "shin_l": {"r": [f"math.max(0, math.sin({w} + 270)) * 18", 0, 0]},
        "cannon_l": {"r": [f"math.max(0, math.sin({w} + 270)) * -14", 0, 0]},
        "tail0": {"r": [0, f"math.sin({w}) * 9", 0]},
    }
    form3 = {   # phase III: the body is gone, the head flies on the vortex
        "neck": {"p": [0, -11, 34]},
        "head": {"r": [6, 0, 0]},
    }
    return {"idle": loop(idle), "walk": loop(walk), "form3": loop(form3)}


def tremble(a: Act, bone="root", amp=0.4, f=2400):
    a.overlay(bone, "p", [f"math.sin({A} * {f}) * {amp}", 0, f"math.cos({A} * {f * 0.83:.0f}) * {amp}"])
    return a


def acts():
    out = []
    jaw = lambda x: {"jaw": {"r": (x, 0, 0)}}
    # 1 emerge: rises from the earth and roars
    a = Act("emerge", 64, [48])
    a.at(0, {"root": {"p": (0, -48, 0)}, "head": {"r": (-28, 0, 0)}, "jaw": {"r": (8, 0, 0)}, "shoulder_r": {"r": (-30, 0, 0)}, "shoulder_l": {"r": (-10, 0, 0)}})
    a.at(18, {"root": {"p": (0, -26, 0)}, "shoulder_r": {"r": (-5, 0, 0)}, "shoulder_l": {"r": (-35, 0, 0)}}, "out")
    a.at(38, {"root": {"p": (0, 0, 0)}, "head": {"r": (12, 0, 0)}, "shoulder_r": {"r": (0, 0, 0)}, "shoulder_l": {"r": (0, 0, 0)}}, "out")
    a.at(45, {"neck": {"r": (8, 0, 0)}, "head": {"r": (18, 0, 0)}, **jaw(2), "hull": {"p": (0, -3, 2)}}, "io")
    a.at(48, {"neck": {"r": (-18, 0, 0)}, "head": {"r": (-22, 0, 0)}, **jaw(48), "hull": {"p": (0, 1, 0), "r": (-6, 0, 0)}}, "in")
    a.at(58, {"neck": {"r": (-16, 6, 0)}, "head": {"r": (-20, -6, 4)}, **jaw(44)}, "lin")
    a.at(64, {"neck": {"r": (0, 0, 0)}, "head": {"r": (0, 0, 0)}, **jaw(6), "hull": {"p": (0, 0, 0), "r": (0, 0, 0)}}, "io")
    out.append(tremble(a, amp=0.5))
    # 2 roar: rears up, the armpit eyes tear open
    a = Act("roar", 44, [14])
    a.at(0, {"pitglow_r": {"s": 0.2}, "pitglow_l": {"s": 0.2}})
    a.at(9, {"hull": {"p": (0, -3, 1), "r": (5, 0, 0)}, "neck": {"r": (12, 0, 0)}, "head": {"r": (14, 0, 0)}, **jaw(0)})
    a.at(14, {"hull": {"p": (0, 3, 0), "r": (-12, 0, 0)}, "neck": {"r": (-26, 0, 0)}, "head": {"r": (-14, 0, 0)}, **jaw(52),
              "pitglow_r": {"s": 1.45}, "pitglow_l": {"s": 1.45}, "shoulder_r": {"r": (-22, 0, -14)}, "shoulder_l": {"r": (-22, 0, 14)}}, "in")
    a.at(32, {"neck": {"r": (-24, 5, 0)}, "head": {"r": (-12, -5, 5)}, **jaw(48), "pitglow_r": {"s": 1.0}, "pitglow_l": {"s": 1.0}}, "lin")
    a.at(44, {"hull": {"p": (0, 0, 0), "r": (0, 0, 0)}, "neck": {"r": (0, 0, 0)}, "head": {"r": (0, 0, 0)}, **jaw(5),
              "shoulder_r": {"r": (0, 0, 0)}, "shoulder_l": {"r": (0, 0, 0)}})
    out.append(a.overlay("head", "r", [0, 0, f"math.sin({A} * 1500) * 1.2"]))
    # 3 claw: right then left swipe with human hands
    a = Act("claw", 28, [10, 18])
    a.at(6, {"shoulder_r": {"r": (-58, 8, -26)}, "fore_r": {"r": (-34, 0, 0)}, "hull": {"r": (0, -8, 0)}, "head": {"r": (0, 8, 0)},
             **{f"fing_r{k}": {"r": (-25, 0, 0)} for k in range(4)}})
    a.at(10, {"shoulder_r": {"r": (16, -18, 12)}, "fore_r": {"r": (0, 0, 0)}, "hull": {"r": (0, 10, 0)}, "head": {"r": (4, -10, 0)},
              **{f"fing_r{k}": {"r": (50, 0, 0)} for k in range(4)}, **jaw(18)}, "in")
    a.at(14, {"shoulder_r": {"r": (0, 0, 0)}, **{f"fing_r{k}": {"r": (0, 0, 0)} for k in range(4)},
              "shoulder_l": {"r": (-58, -8, 26)}, "fore_l": {"r": (-34, 0, 0)}, "hull": {"r": (0, 8, 0)},
              **{f"fing_l{k}": {"r": (-25, 0, 0)} for k in range(4)}}, "out")
    a.at(18, {"shoulder_l": {"r": (16, 18, -12)}, "fore_l": {"r": (0, 0, 0)}, "hull": {"r": (0, -10, 0)}, "head": {"r": (4, 10, 0)},
              **{f"fing_l{k}": {"r": (50, 0, 0)} for k in range(4)}, **jaw(26)}, "in")
    a.at(28, {"shoulder_l": {"r": (0, 0, 0)}, "hull": {"r": (0, 0, 0)}, "head": {"r": (0, 0, 0)}, **jaw(3),
              **{f"fing_l{k}": {"r": (0, 0, 0)} for k in range(4)}})
    out.append(a)
    # 4 charge: galloping (looped while dashing)
    a = Act("charge", 20, [], loop=True)
    g = f"math.sin({A} * 1080)"
    a.at(0, {"hull": {"r": (6, 0, 0), "p": (0, -1, 0)}, "neck": {"r": (14, 0, 0)}, "head": {"r": (10, 0, 0)}, **jaw(24)})
    a.at(20, {"hull": {"r": (6, 0, 0), "p": (0, -1, 0)}, "neck": {"r": (14, 0, 0)}, "head": {"r": (10, 0, 0)}, **jaw(24)}, "lin")
    a.overlay("shoulder_r", "r", [f"{g} * 34", 0, 0]).overlay("shoulder_l", "r", [f"{g} * 30", 0, 0])
    a.overlay("thigh_r", "r", [f"-{g} * 30", 0, 0]).overlay("thigh_l", "r", [f"-{g} * 34", 0, 0])
    a.overlay("hull", "p", [0, f"math.abs({g}) * 2.2", 0]).overlay("tail0", "r", [f"{g} * 10", 0, 0])
    out.append(a)
    # 5 windup: lowers the horns and paws the ground like a bull
    a = Act("windup", 18)
    a.at(4, {"hull": {"p": (0, -3, 3), "r": (6, 0, 0)}, "neck": {"r": (16, 0, 0)}, "head": {"r": (18, 0, 0)}, "shoulder_r": {"r": (-28, 0, 0)}, "fore_r": {"r": (-30, 0, 0)}})
    a.at(8, {"shoulder_r": {"r": (6, 0, 0)}, "fore_r": {"r": (0, 0, 0)}}, "in")
    a.at(12, {"shoulder_r": {"r": (-26, 0, 0)}, "fore_r": {"r": (-28, 0, 0)}}, "out")
    a.at(16, {"shoulder_r": {"r": (6, 0, 0)}, "fore_r": {"r": (0, 0, 0)}, **jaw(14)}, "in")
    a.at(18, {"shoulder_r": {"r": (0, 0, 0)}})
    out.append(a)
    # 6 inhale: the maw gapes and drinks the world, then snaps
    a = Act("inhale", 64, [55])
    a.at(10, {"neck": {"r": (8, 0, 0), "p": (0, -2, -3)}, "head": {"r": (-6, 0, 0)}, **jaw(58), "hull": {"p": (0, -2, 2), "r": (4, 0, 0)},
              "shoulder_r": {"r": (-8, 0, -6)}, "shoulder_l": {"r": (-8, 0, 6)}}, "out")
    a.at(50, {"neck": {"r": (10, 0, 0), "p": (0, -2, -4)}, **jaw(64)}, "lin")
    a.at(53, {"neck": {"p": (0, -1, 2)}, **jaw(70)}, "out")
    a.at(55, {"neck": {"r": (2, 0, 0), "p": (0, -2, -8)}, "head": {"r": (8, 0, 0)}, **jaw(-4)}, "in")
    a.at(64, {"neck": {"r": (0, 0, 0), "p": (0, 0, 0)}, "head": {"r": (0, 0, 0)}, **jaw(3), "hull": {"p": (0, 0, 0), "r": (0, 0, 0)},
              "shoulder_r": {"r": (0, 0, 0)}, "shoulder_l": {"r": (0, 0, 0)}})
    out.append(a.overlay("head", "r", [f"math.sin({A} * 2200) * 1.2", 0, f"math.cos({A} * 1900) * 1.2"]))
    # 7 quake: rears and slams both hands down
    a = Act("quake", 34, [20])
    a.at(14, {"hull": {"r": (-16, 0, 0), "p": (0, 4, 2)}, "shoulder_r": {"r": (-62, 0, -10)}, "shoulder_l": {"r": (-62, 0, 10)},
              "fore_r": {"r": (-30, 0, 0)}, "fore_l": {"r": (-30, 0, 0)}, "neck": {"r": (-18, 0, 0)}, **jaw(40)}, "out")
    a.at(20, {"hull": {"r": (5, 0, 0), "p": (0, -2, 0)}, "shoulder_r": {"r": (14, 0, -6)}, "shoulder_l": {"r": (14, 0, 6)},
              "fore_r": {"r": (0, 0, 0)}, "fore_l": {"r": (0, 0, 0)}, "neck": {"r": (14, 0, 0)}, "head": {"r": (8, 0, 0)}, **jaw(12)}, "in")
    a.at(26, {"hull": {"r": (3, 0, 0), "p": (0, -1, 0)}}, "out")
    a.at(34, {"hull": {"r": (0, 0, 0), "p": (0, 0, 0)}, "shoulder_r": {"r": (0, 0, 0)}, "shoulder_l": {"r": (0, 0, 0)},
              "neck": {"r": (0, 0, 0)}, "head": {"r": (0, 0, 0)}, **jaw(3)})
    out.append(a)
    # 8 gaze: lifts both arms, the armpit eyes blaze and sweep
    a = Act("gaze", 52, [16])
    a.at(12, {"shoulder_r": {"r": (-14, 0, -30)}, "shoulder_l": {"r": (-14, 0, 30)}, "fore_r": {"r": (-20, 0, 0)}, "fore_l": {"r": (-20, 0, 0)},
              "hull": {"p": (0, 3, 0)}, "neck": {"r": (-14, 0, 0)}, **jaw(26), "pitglow_r": {"s": 1.0}, "pitglow_l": {"s": 1.0}}, "out")
    a.at(16, {"pitglow_r": {"s": 1.6}, "pitglow_l": {"s": 1.6}}, "in")
    a.at(44, {"hull": {"r": (0, 0, 0)}, "pitglow_r": {"s": 1.4}, "pitglow_l": {"s": 1.4}}, "lin")
    a.at(52, {"shoulder_r": {"r": (0, 0, 0)}, "shoulder_l": {"r": (0, 0, 0)}, "fore_r": {"r": (0, 0, 0)}, "fore_l": {"r": (0, 0, 0)},
              "hull": {"p": (0, 0, 0)}, "neck": {"r": (0, 0, 0)}, **jaw(3), "pitglow_r": {"s": 1.0}, "pitglow_l": {"s": 1.0}})
    out.append(a.overlay("hull", "r", [0, f"math.sin(math.min({A}, 2.2) * 120) * 6", 0]))
    # 9 summon: howls at the sky - the ding vessels fall
    a = Act("summon", 30, [12])
    a.at(8, {"hull": {"p": (0, -2, 2), "r": (5, 0, 0)}, "neck": {"r": (10, 0, 0)}, **jaw(4)})
    a.at(12, {"hull": {"p": (0, 2, 0), "r": (-9, 0, 0)}, "neck": {"r": (-38, 0, 0)}, "head": {"r": (-22, 0, 0)}, **jaw(55)}, "in")
    a.at(24, {"neck": {"r": (-34, 0, 0)}, **jaw(46)}, "lin")
    a.at(30, {"hull": {"p": (0, 0, 0), "r": (0, 0, 0)}, "neck": {"r": (0, 0, 0)}, "head": {"r": (0, 0, 0)}, **jaw(3)})
    out.append(a)
    # 10 pounce
    a = Act("pounce", 22, [7])
    a.at(6, {"hull": {"p": (0, -5, 2), "r": (10, 0, 0)}, "thigh_r": {"r": (-14, 0, 0)}, "thigh_l": {"r": (-14, 0, 0)}, "neck": {"r": (10, 0, 0)}})
    a.at(9, {"hull": {"p": (0, 1, 0), "r": (-16, 0, 0)}, "shoulder_r": {"r": (-64, 0, 0)}, "shoulder_l": {"r": (-64, 0, 0)},
             "fore_r": {"r": (-10, 0, 0)}, "fore_l": {"r": (-10, 0, 0)}, "thigh_r": {"r": (40, 0, 0)}, "thigh_l": {"r": (40, 0, 0)}, **jaw(40)}, "in")
    a.at(18, {"hull": {"r": (6, 0, 0)}, "shoulder_r": {"r": (-30, 0, 0)}, "shoulder_l": {"r": (-30, 0, 0)}, "thigh_r": {"r": (10, 0, 0)}, "thigh_l": {"r": (10, 0, 0)}}, "lin")
    a.at(21, {"hull": {"r": (8, 0, 0), "p": (0, -3, 0)}, "shoulder_r": {"r": (12, 0, 0)}, "shoulder_l": {"r": (12, 0, 0)}, "thigh_r": {"r": (0, 0, 0)},
              "thigh_l": {"r": (0, 0, 0)}, **jaw(10)}, "in")
    a.at(22, {"hull": {"r": (2, 0, 0), "p": (0, -1, 0)}}, "out")
    out.append(a)
    # 11 spit
    a = Act("spit", 24, [12])
    a.at(9, {"neck": {"p": (0, 2, 5), "r": (-8, 0, 0)}, "head": {"r": (-14, 0, 0)}, **jaw(10)}, "out")
    a.at(12, {"neck": {"p": (0, -1, -5), "r": (8, 0, 0)}, "head": {"r": (6, 0, 0)}, **jaw(42)}, "in")
    a.at(24, {"neck": {"p": (0, 0, 0), "r": (0, 0, 0)}, "head": {"r": (0, 0, 0)}, **jaw(3)})
    out.append(a)
    # 12 devour: it eats its own body, bite by bite (the hull shrinks into the ground)
    a = Act("devour", 84, [20, 36, 52, 66])
    sides = [(1, 112, 18), (-1, -112, 18), (1, 142, 32), (-1, -146, 34)]
    scl = [0.84, 0.66, 0.46, 0.24]
    last = 0
    for i, m in enumerate([20, 36, 52, 66]):
        sx, ry, rx = sides[i]
        a.at(m - 7, {"neck": {"r": (rx, ry, 0), "p": (sx * 2, -2, 2)}, "head": {"r": (14, 0, sx * 14)}, **jaw(52)}, "io")
        a.at(m, {"neck": {"r": (rx + 6, ry * 1.04, 0)}, **jaw(-4),
                 "hull": {"s": scl[i], "p": (0, -34 * (1 - scl[i]), 0)}}, "in")
        last = m
    a.at(80, {"neck": {"r": (0, 0, 0), "p": (0, 0, 0)}, "head": {"r": (0, 0, 0)}, **jaw(20), "hull": {"s": 0.08, "p": (0, -31, 0)}}, "io")
    a.at(84, {**jaw(10)})
    out.append(tremble(a, "hull", 0.6, 2000))
    # 13 maw: the ultimate - the head swells into a world-swallowing maw, then snaps shut
    a = Act("maw", 180, [168])
    a.at(36, {"head": {"s": 1.6, "r": (-12, 0, 0)}, **jaw(72), "neck": {"p": (0, 6, 4)}}, "out")
    a.at(150, {"head": {"s": 1.7, "r": (-10, 0, 0)}, **jaw(76)}, "lin")
    a.at(164, {"head": {"s": 1.85, "r": (-20, 0, 0)}, **jaw(84), "neck": {"p": (0, 8, 8)}}, "out")
    a.at(168, {"head": {"s": 1.9, "r": (10, 0, 0)}, **jaw(-6), "neck": {"p": (0, 2, -12)}}, "in")
    a.at(180, {"head": {"s": 1.0, "r": (0, 0, 0)}, **jaw(4), "neck": {"p": (0, 0, 0)}}, "out")
    a.overlay("head", "r", [f"math.sin({A} * 2600) * 1.5", f"math.cos({A} * 2100) * 1.5", 0])
    a.overlay("vortex_a", "r", [0, f"{A} * 520", 0]).overlay("vortex_b", "r", [0, f"-{A} * 640", 0])
    out.append(a)
    # 14 ram (phase III head)
    a = Act("ram", 26, [11])
    a.at(8, {"neck": {"p": (0, 3, 8)}, "head": {"r": (-16, 0, 0)}, **jaw(6)}, "out")
    a.at(11, {"neck": {"p": (0, -2, -6)}, "head": {"r": (26, 0, 0)}, **jaw(30)}, "in")
    a.at(22, {"neck": {"p": (0, -2, -6)}, "head": {"r": (24, 0, 0)}}, "lin")
    a.at(26, {"neck": {"p": (0, 0, 0)}, "head": {"r": (0, 0, 0)}, **jaw(4)})
    out.append(a.overlay("vortex", "r", [0, f"{A} * 900", 0]))
    # 15 bites: three snapping lunges
    a = Act("bites", 32, [7, 16, 25])
    for i, m in enumerate([7, 16, 25]):
        sz = 12 if i % 2 == 0 else -12
        a.at(m - 4, {"neck": {"p": (0, 1, 4)}, "head": {"r": (-14, 0, sz)}, **jaw(60)}, "out")
        a.at(m, {"neck": {"p": (0, -2, -8)}, "head": {"r": (10, 0, -sz * 0.5)}, **jaw(-4)}, "in")
    a.at(32, {"neck": {"p": (0, 0, 0)}, "head": {"r": (0, 0, 0)}, **jaw(4)})
    out.append(a)
    # 16 spiral: the head whirls, spitting leiwen bolts
    a = Act("spiral", 60, [10])
    a.at(8, {"head": {"r": (-8, 0, 0)}, **jaw(40)}, "out")
    a.at(54, {"head": {"r": (-8, 720, 0)}, **jaw(40)}, "lin")
    a.at(60, {"head": {"r": (0, 720, 0)}, **jaw(5)})
    out.append(a.overlay("vortex", "r", [0, f"-{A} * 700", 0]))
    # 17 death: the hunger is stilled - the head sags, cracks and crumbles to dust
    a = Act("death", 80, [72])
    a.at(10, {"head": {"r": (-20, 0, 6)}, **jaw(50), "neck": {"p": (0, 2, 0)}}, "out")
    a.at(40, {"head": {"r": (24, 8, 18)}, **jaw(38), "neck": {"p": (0, -10, 0)}, "vortex": {"s": 0.6},
              "horn_r": {"r": (0, 0, -10)}, "horn_l": {"r": (0, 0, 12)}}, "io")
    a.at(66, {"head": {"r": (34, 10, 26)}, **jaw(46), "neck": {"p": (0, -16, 0)}, "vortex": {"s": 0.2}}, "io")
    a.at(72, {"root": {"s": 1.08}}, "out")
    a.at(80, {"root": {"s": 0.02, "p": (0, -6, 0)}}, "in")
    out.append(tremble(a, "head", 0.8, 1800))
    return out


# =========================================================================== client entity / render controller
def entity_cfg():
    return {
        "scale": SCALE,
        "textures": {"default": f"textures/entity/legends/{KEY}", "v1": f"textures/entity/legends/{KEY}_v1"},
        "pre": [
            "variable.p3 = math.lerp(variable.p3 ?? 0.0, variable.ph >= 3 ? 1.0 : 0.0, 0.06);",
            "variable.walkw = variable.mv * (1.0 - variable.p3) * variable.calm;",
        ],
        "animate": [{"idle": "variable.calm + 0.15"}, {"walk": "variable.walkw"}, {"form3": "variable.p3"}, "ctrl_act"],
        "texture_expr": "Array.skins[variable.ph >= 2 ? 1 : 0]",
        "skins": ["Texture.default", "Texture.v1"],
        "visibility": [
            {"hull": "variable.ph < 3"}, {"neck_mesh": "variable.ph < 3"},
            {"lid_r": "variable.ph < 2"}, {"lid_l": "variable.ph < 2"},
            {"pitglow_r": "variable.ph == 2"}, {"pitglow_l": "variable.ph == 2"},
            {"vortex": "variable.ph >= 3"},
        ],
        "bounds": (14, 9, 4.0),
    }


if __name__ == "__main__":
    import sys
    from modelkit import render_preview, zfight_report, island_report
    out = sys.argv[1]
    m = build()
    img = m.paint()
    print(m.stats())
    print("zfight", len(zfight_report(m)), zfight_report(m)[:8])
    print("islands", island_report(m))
    from modelkit import deflicker
    print("after deflicker", deflicker(m))
    hide = {"vortex": {"scale": 0.001}}
    render_preview([m], f"{out}/taotie_a.png", yaw=35, pitch=18, size=720, step=2, pose=hide)
    render_preview([m], f"{out}/taotie_b.png", yaw=-120, pitch=12, size=720, step=2, pose=hide)
