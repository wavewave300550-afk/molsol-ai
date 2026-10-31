"""
HANUMAN (หนุมาน) - Son of the Wind. Remastered model.

Thai khon warrior: white diamond-haired monkey, khon face with gold-rimmed eyes and crystal fangs,
gold diadem with ear-wings (กรรเจียก), upturned shoulder flares (อินทรธนู), crossed sashes,
red silk breeches and apron with gold brocade, the trident (ตรีเพชร), and a long curling tail that
blazes in phase II. Phase III reveals four faces and eight arms holding the divine weapons.

Scale 1.5 -> 10.67 model units per block. Faces -Z. Tail tip ~ (0, 46, 32) (script: ahead(-3.2, 4.2)).
`variable.size` (tiny form / divine growth) scales the root.
"""
import math

from modelkit import Model
from shapes import bevel, orb, ring, spike, strut
from shapes2 import catmull, tube
import lmat as L

ID = "geometry.legends.hanuman"
KEY = "hanuman"
SCALE = 1.5
VARIANTS = {"default": "default"}
_CACHE = {}

XARMS = {  # extra arms (phase III): side, idx, shoulder, elbow, wrist, weapon
    "r2": (-1, (-8.0, 42.5, 2.0), (-15, 49, 3), (-19, 56, 2), "discus"),
    "r3": (-1, (-7.6, 40.5, 3.0), (-17, 41, 5), (-25, 42, 3), "sword"),
    "r4": (-1, (-7.2, 38.5, 3.5), (-15, 34, 6), (-21, 28, 4), "mace"),
    "l2": (1, (8.0, 42.5, 2.0), (15, 49, 3), (19, 56, 2), "conch"),
    "l3": (1, (7.6, 40.5, 3.0), (17, 41, 5), (25, 42, 3), "bow"),
    "l4": (1, (7.2, 38.5, 3.5), (15, 34, 6), (21, 28, 4), "arrow"),
}


def _weapon(bone, kind, w, sx):
    GD = L.thai_gold(gems=False)
    ST = L.steel()
    x, y, z = w
    if kind == "discus":
        ring(bone, (x, y + 4, z), 4.2, 12, GD, thickness=1.2, width=1.0, plane="xy")
        ring(bone, (x, y + 4, z - 0.1), 5.2, 12, L.glow("fff3b0", "ffb020", "u"), thickness=0.8, width=0.5, plane="xy", glow=True, jag=[1.0, 2.0])
        bone.add((x - 1, y + 3, z - 0.6), (2, 2, 1.2), GD)
        for a in range(4):
            ang = math.pi / 4 + a * math.pi / 2
            strut(bone, (x, y + 4, z), (x + math.cos(ang) * 4.0, y + 4 + math.sin(ang) * 4.0, z), 0.6, GD, depth=0.6)
    elif kind == "sword":
        strut(bone, (x, y, z), (x + sx * 16, y + 3, z - 1), 1.4, ST, depth=0.5)
        bone.add((x - 1.5, y - 1.5, z - 1.5), (3, 3, 3), GD)
    elif kind == "mace":
        strut(bone, (x, y, z), (x + sx * 3, y - 10, z - 1), 1.2, GD)
        orb(bone, (x + sx * 3.4, y - 11.5, z - 1), 2.6, GD)
        for d in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)):
            spike(bone, (x + sx * 3.4, y - 11.5, z - 1), (x + sx * 3.4 + d[0] * 4.2, y - 11.5, z - 1 + d[2] * 4.2), 1.2, GD, steps=2)
    elif kind == "conch":
        pts = [(x, y + 1, z), (x + sx * 1.6, y + 3.5, z - 0.5), (x + sx * 1.0, y + 6, z - 1), (x - sx * 0.4, y + 7.5, z - 1)]
        tube(bone, catmull(pts, 2), 3.6, 1.0, L.solid("f4eee0", 0.04))
    elif kind == "bow":
        pts = [(x + sx * 1, y - 9, z), (x + sx * 3.5, y - 3, z - 0.5), (x + sx * 3.5, y + 3, z - 0.5), (x + sx * 1, y + 9, z)]
        tube(bone, catmull(pts, 3), 1.1, 0.8, GD)
        strut(bone, (x + sx * 1, y - 9, z), (x + sx * 1, y + 9, z), 0.25, L.solid("fff6d8", 0.02))
    elif kind == "arrow":
        strut(bone, (x - sx * 2, y - 6, z), (x + sx * 2, y + 9, z - 1), 0.6, L.solid("8a5a2a", 0.05))
        spike(bone, (x + sx * 2, y + 9, z - 1), (x + sx * 2.6, y + 12, z - 1.2), 1.4, ST, steps=2)


def build():
    m = Model(ID, seed=31, density=3)
    FUR = L.white_fur()
    GD = L.thai_gold()
    GDP = L.thai_gold(gems=False)
    CL = L.thai_cloth()
    CLW = L.thai_cloth("f4efe2", "e3ad2e")
    CRY = L.crystal()
    ST = L.steel()
    EYE = L.glow("fffbd0", "f0a020", "r")
    FIRE = L.glow("fff3c0", "ff4a10", "vt")

    root = m.bone("root", (0, 0, 0))
    hips = m.bone("hips", (0, 26, 0), "root")
    bevel(hips, (-6.5, 22, -4), (13, 7, 8), CL, b=1.5)                       # breeches seat
    hips.add((-7.2, 25.2, -4.6), (14.4, 3.2, 9.2), GD)                         # belt
    bevel(hips, (-2.6, 23.6, -5.6), (5.2, 5.6, 1.4), GDP, b=0.6)               # buckle (ปั้นเหน่ง)
    hips.add((-1.0, 25.4, -6.1), (2.0, 2.0, 0.6), L.solid("d1172c", 0.02))
    apron = m.bone("apron", (0, 25, -4.8), "hips")
    apron.add((-3.6, 9.5, -5.4), (7.2, 15.5, 0.8), CL)                         # ห้อยหน้า
    apron.add((-3.0, 9.0, -5.6), (6.0, 1.4, 0.6), GDP)
    for sx in (-1, 1):                                                          # side flaps (เจียระบาด)
        fl = m.bone(f"flap_{'r' if sx < 0 else 'l'}", (sx * 7, 25, 0), "hips")
        fl.add((sx * 7 - (0.8 if sx > 0 else 0) - (0 if sx > 0 else 0), 13.5, -3.5), (0.8, 11.5, 7), CL)

    # legs: red breeches to the knee, white fur shins, gold knee guards and anklets
    for side, sx in (("r", -1), ("l", 1)):
        Hh, K, A = (sx * 4.6, 26, 0), (sx * 6.2, 15, -2.6), (sx * 6.2, 4.2, 1.2)
        lg = m.bone(f"leg_{side}", Hh, "hips")
        tube(lg, [Hh, K], 6.6, 5.8, CLW, soft=False)
        lg.add((sx * 6.2 - 3.4, 14.6, -6.0), (6.8, 2.0, 6.8), GDP)              # breeches gold hem
        sh = m.bone(f"shin_{side}", K, f"leg_{side}")
        tube(sh, [K, A], 4.6, 3.6, FUR)
        bevel(sh, (sx * 6.2 - 2.4, 11.5, -5.4), (4.8, 4.2, 2.0), GDP, b=0.5)    # knee guard
        sh.add((sx * 6.2 - 2.6, 4.6, -1.4), (5.2, 1.6, 5.2), GD)                # anklet
        ft = m.bone(f"foot_{side}", A, f"shin_{side}")
        bevel(ft, (sx * 6.2 - 2.4, 0, -5.5), (4.8, 3.2, 8.5), FUR, b=0.8)
        for k in range(3):
            ft.add((sx * 6.2 - 2.1 + k * 1.5, 0, -7.2), (1.2, 1.6, 2.0), FUR)

    torso = m.bone("torso", (0, 28, 0), "hips")
    bevel(torso, (-5.8, 27.5, -3.4), (11.6, 9, 6.8), FUR, b=1.6)               # abdomen
    chest = m.bone("chest", (0, 36, 0), "torso")
    bevel(chest, (-8.4, 34.5, -4.4), (16.8, 10.5, 8.8), FUR, b=2.2)
    for sx in (-1, 1):                                                          # pectorals
        bevel(chest, (sx * 4.2 - 3.4, 38.2, -5.0), (6.8, 5.2, 1.6), FUR, b=0.6)
    for sx in (-1, 1):                                                          # crossed sashes (สังวาล)
        strut(chest, (sx * 7.5, 44, -4.6), (-sx * 5.5, 30, -4.0), 1.0, GD, depth=0.8)
        strut(chest, (sx * 7.5, 44, 4.6), (-sx * 5.5, 30, 4.0), 1.0, GD, depth=0.8)
    bevel(chest, (-1.8, 35.5, -5.7), (3.6, 3.6, 1.2), GDP, b=0.4)              # sash medallion
    chest.add((-0.8, 36.4, -6.1), (1.6, 1.6, 0.6), L.solid("19a35a", 0.02))
    bevel(chest, (-8.2, 42.6, -5.2), (16.4, 2.8, 10.4), GD, b=0.6)             # collar (กรองศอ)
    for k in range(5):
        x = -6 + k * 3
        spike(chest, (x, 42.8, -5.4), (x, 39.6 + (k % 2), -5.8), 1.6, GDP, steps=2)
    for sx in (-1, 1):                                                          # shoulder flares (อินทรธนู)
        sb = m.bone(f"epaul_{'r' if sx < 0 else 'l'}", (sx * 8.5, 44, 0), "chest")
        bevel(sb, (sx * 9.0 - 3.2, 41.5, -3.4), (6.4, 3.2, 6.8), GD, b=0.6)
        pts = catmull([(sx * 10.5, 44, 0), (sx * 13.8, 45.6, 0.5), (sx * 16.0, 48.2, 1.0), (sx * 16.6, 50.6, 1.6)], 3)
        tube(sb, pts, 2.2, 0.6, GDP, soft=False)

    neck = m.bone("neck", (0, 45, 0), "chest")
    bevel(neck, (-2.8, 44, -2.8), (5.6, 4.5, 5.6), FUR, b=1)
    head = m.bone("head", (0, 47.5, -0.5), "neck")
    bevel(head, (-5.2, 47, -5.0), (10.4, 9.8, 9.8), FUR, b=2.2)                # cranium
    head.add((-5.0, 48.6, -5.6), (10.0, 7.2, 0.6), FUR, decals={"north": L.khon_face()})
    bevel(head, (-3.6, 46.4, -8.2), (7.2, 4.8, 3.4), FUR, b=1.0)               # muzzle
    head.add((-2.0, 49.6, -8.4), (4.0, 1.2, 0.8), L.solid("2a1a1c", 0.02))     # nose
    for sx in (-1, 1):
        head.add((sx * 2.45 - 1.15, 51.7, -5.95), (2.3, 1.9, 0.4), EYE, glow=True)
        spike(head, (sx * 1.9, 47.2, -7.6), (sx * 1.8, 44.6, -7.9), 1.1, CRY, steps=2)   # crystal fangs (เขี้ยวแก้ว)
        bevel(head, (sx * 5.4 - 1.2, 49.5, -1.8), (2.4, 3.4, 2.4), FUR, b=0.5)  # ear
        er = m.bone(f"kanjiak_{'r' if sx < 0 else 'l'}", (sx * 5.5, 51, 0.5), "head")   # ear wings (กรรเจียก)
        pts = catmull([(sx * 5.8, 50, 1.0), (sx * 7.2, 53.5, 3.0), (sx * 7.0, 57.5, 4.6), (sx * 5.6, 60.5, 5.0)], 3)
        tube(er, pts, 2.6, 0.8, GDP, soft=False)
        er.add((sx * 7.0 - 0.6, 53.3, 2.6), (1.2, 1.2, 1.2), L.solid("d1172c", 0.02))
    head.add((-3.4, 46.0, -7.9), (6.8, 1.2, 2.8), L.solid("8a1020", 0.04))     # mouth
    bevel(head, (-5.6, 55.4, -5.4), (11.2, 1.8, 10.6), GD, b=0.5)              # diadem band
    spike(head, (0, 57, -5.0), (0, 63, -4.2), 2.6, GDP, steps=3)               # kranok crest
    for sx in (-1, 1):
        spike(head, (sx * 3.2, 56.8, -5.3), (sx * 3.6, 60.2, -4.8), 1.6, GDP, steps=2)
    head.add((-0.9, 56.2, -5.9), (1.8, 1.8, 0.6), L.solid("d1172c", 0.02))
    jaw = m.bone("jaw", (0, 46.6, -4), "head")
    bevel(jaw, (-3.0, 44.6, -7.8), (6.0, 2.0, 3.6), FUR, b=0.5)
    for sx in (-1, 1):
        spike(jaw, (sx * 1.2, 46.4, -7.4), (sx * 1.1, 48.0, -7.6), 0.9, CRY, steps=2)
    # extra faces (phase III): right, left and back
    for nm, axis in (("face_r", -1), ("face_l", 1)):
        fb = m.bone(nm, (axis * 5.2, 51, -0.5), "head")
        fb.add((axis * 5.25 - (0.6 if axis > 0 else 0), 48.4, -4.6), (0.6, 7.2, 8.4), FUR,
               decals={"west" if axis > 0 else "east": L.khon_face()})
        for dz in (-2.2, 2.2):
            fb.add((axis * 5.6 - (0.4 if axis > 0 else 0) + (0 if axis > 0 else 0), 51.3, -0.5 + dz - 0.9), (0.4, 1.8, 1.8), EYE, glow=True)
        bevel(fb, (axis * 6.4 - 1.8, 46.6, -2.4), (3.6, 4.0, 3.8), FUR, b=0.6)
    fbk = m.bone("face_b", (0, 51, 4.8), "head")
    fbk.add((-5.0, 48.4, 4.8), (10.0, 7.2, 0.6), FUR, decals={"south": L.khon_face()})
    for sx in (-1, 1):
        fbk.add((sx * 2.45 - 1.15, 51.4, 5.35), (2.3, 1.9, 0.4), EYE, glow=True)
    bevel(fbk, (-3.4, 46.6, 5.2), (6.8, 4.4, 2.8), FUR, b=0.8)

    # main arms
    for side, sx in (("r", -1), ("l", 1)):
        Sh, El, Wr = (sx * 9.6, 43, 0), (sx * 11.2, 33.8, -0.6), (sx * 11.6, 25.4, -2.0)
        ua = m.bone(f"arm_{side}", Sh, "chest")
        tube(ua, [Sh, El], 4.8, 4.2, FUR)
        ua.add((sx * 10.4 - 2.6, 37.5, -3.2), (5.2, 1.8, 5.2), GD)             # armband (พาหุรัด)
        fa = m.bone(f"farm_{side}", El, f"arm_{side}")
        tube(fa, [El, Wr], 4.2, 3.6, FUR)
        fa.add((sx * 11.5 - 2.4, 26.4, -4.4), (4.8, 2.6, 4.8), GD)             # bracelet (ทองกร)
        hd = m.bone(f"hand_{side}", Wr, f"farm_{side}")
        bevel(hd, (sx * 11.7 - 2.2, 20.6, -4.4), (4.4, 5.0, 4.6), FUR, b=0.8)
    # the trident (ตรีเพชร) in the right hand
    tr = m.bone("trident", (-11.7, 23, -2.2), "hand_r")
    tr.add((-12.35, 2, -2.85), (1.3, 58, 1.3), L.solid("6b1e12", 0.05))          # lacquered shaft
    for y in (14, 30, 44):
        tr.add((-12.7, y, -3.2), (2.0, 1.2, 2.0), GDP)
    orb(tr, (-11.7, 1.5, -2.2), 1.4, GDP)
    bevel(tr, (-14.7, 59, -3.4), (6.0, 2.2, 2.4), GD, b=0.4)                    # guard
    spike(tr, (-11.7, 60.5, -2.2), (-11.7, 72, -2.2), 2.4, ST, steps=4)          # centre prong
    for sx in (-1, 1):
        pts = catmull([(-11.7 + sx * 2.4, 60.5, -2.2), (-11.7 + sx * 4.6, 63, -2.2), (-11.7 + sx * 4.4, 67.5, -2.2)], 2)
        tube(tr, pts, 1.6, 1.0, ST, soft=False)
        spike(tr, (-11.7 + sx * 4.4, 67, -2.2), (-11.7 + sx * 3.6, 70, -2.2), 1.2, ST, steps=2)
    tr.add((-12.2, 62.8, -2.7), (1.0, 1.0, 1.0), L.glow("e6fbff", "7fd6ff", "r"), glow=True)

    # extra arms (phase III)
    for nm, (sx, Sh, El, Wr, weapon) in XARMS.items():
        xa = m.bone(f"xarm_{nm}", Sh, "chest")
        tube(xa, [Sh, El], 4.0, 3.6, FUR)
        xa.add((El[0] - 2.2 + (Sh[0] - El[0]) * 0.3, El[1] - 1 + (Sh[1] - El[1]) * 0.3, El[2] - 2.2), (4.4, 1.6, 4.4), GD)
        xl = m.bone(f"xarm_{nm}_lo", El, f"xarm_{nm}")
        tube(xl, [El, Wr], 3.6, 3.0, FUR)
        bevel(xl, (Wr[0] - 2.0, Wr[1] - 2.0, Wr[2] - 2.0), (4.0, 4.0, 4.0), FUR, b=0.7)
        wb = m.bone(f"w_{weapon}", Wr, f"xarm_{nm}_lo")
        _weapon(wb, weapon, Wr, sx)

    # tail, curling up behind (fire in phase II)
    tp = [(0, 25, 3.5), (0, 21.5, 11), (0, 23, 20), (0, 30, 27), (0, 38.5, 31), (0, 45, 31.5), (0, 49, 28)]
    parent = "hips"
    for i in range(6):
        tb = m.bone(f"tail{i}", tp[i], parent)
        tube(tb, [tp[i], tp[i + 1]], 3.4 - i * 0.28, 3.1 - i * 0.28, FUR, overlap=0.9)
        if i >= 3:
            fb = m.bone(f"tailfire{i}", tp[i], f"tail{i}")
            mid = tuple((tp[i][k] + tp[i + 1][k]) / 2 for k in range(3))
            for j, d in enumerate(((1.2, 0.6), (-1.2, -0.4), (0.0, 1.2))):
                fb.add((mid[0] + d[0] - 1.0, mid[1] - 0.5, mid[2] + d[1] - 1.0), (2.0, 5.5 + j, 2.0), FIRE, glow=True)
        parent = f"tail{i}"
    tip = m.bone("tail_tip", tp[-1], parent)
    orb(tip, tp[-1], 2.0, FUR)
    tipf = m.bone("tailfire_tip", tp[-1], "tail_tip")
    tipf.add((-1.8, 48.5, 26.2), (3.6, 7.5, 3.6), FIRE, glow=True)
    tipf.add((-1.0, 50.0, 27.0), (2.0, 10.0, 2.0), L.glow("ffffff", "ffb040", "vt"), glow=True)
    _CACHE["model"] = m
    return m


# =========================================================================== animation
from animkit import A, T, Act, cs, loop, merge, mirror, sn, sym

STANCE = {   # khon stance: knees bent outward (ย่อเหลี่ยม)
    "hips": {"p": (0, -2.4, 0)},
    "leg_r": {"r": (-14, 0, -16)}, "leg_l": {"r": (-14, 0, 16)},
    "shin_r": {"r": (26, 0, 10)}, "shin_l": {"r": (26, 0, -10)},
    "foot_r": {"r": (-12, 0, 6)}, "foot_l": {"r": (-12, 0, -6)},
    "torso": {"r": (6, 0, 0)},
}


def loops():
    idle = {
        "hips": {"p": [0, f"-2.4 + {sn(80, amp=0.4)}", 0]},
        "leg_r": {"r": [-14, 0, -16]}, "leg_l": {"r": [-14, 0, 16]},
        "shin_r": {"r": [26, 0, 10]}, "shin_l": {"r": [26, 0, -10]},
        "foot_r": {"r": [-12, 0, 6]}, "foot_l": {"r": [-12, 0, -6]},
        "torso": {"r": [f"6 + {sn(80, amp=1.2)}", 0, 0]},
        "chest": {"r": [sn(80, 40, 1.0), sn(30, amp=3), 0]},
        "head": {"r": [sn(60, amp=3), sn(35, amp=8), sn(25, amp=3)]},
        "jaw": {"r": [f"6 + {sn(120, amp=3)}", 0, 0]},
        "arm_r": {"r": [f"-10 + {sn(80, amp=2)}", 0, -8]}, "farm_r": {"r": [-20, 0, 0]},
        "arm_l": {"r": [f"-6 + {sn(80, 90, 2)}", 0, 12]}, "farm_l": {"r": [-30, 0, 0]},
        "kanjiak_r": {"r": [0, 0, sn(90, amp=2)]}, "kanjiak_l": {"r": [0, 0, sn(90, 60, 2)]},
        "apron": {"r": [sn(70, amp=3), 0, sn(50, amp=2)]},
        "flap_r": {"r": [sn(70, 40, 3), 0, 0]}, "flap_l": {"r": [sn(70, 120, 3), 0, 0]},
        "tail_tip": {"r": [sn(100, amp=10), sn(70, amp=12), 0]},
    }
    for i in range(6):
        idle[f"tail{i}"] = {"r": [sn(60, -i * 40, 3 + i), sn(45, -i * 50, 4 + i * 2), 0]}
    for nm in XARMS:
        idle[f"xarm_{nm}"] = {"r": [sn(70, len(nm) * 40 + int(nm[1]) * 50, 4), 0, sn(55, int(nm[1]) * 60, 5)]}
    w = "variable.dist * 70"
    walk = {
        "leg_r": {"r": [f"math.sin({w}) * 28", 0, 0]}, "leg_l": {"r": [f"math.sin({w} + 180) * 28", 0, 0]},
        "shin_r": {"r": [f"math.max(0, math.sin({w} + 90)) * 34", 0, 0]}, "shin_l": {"r": [f"math.max(0, math.sin({w} + 270)) * 34", 0, 0]},
        "arm_r": {"r": [f"math.sin({w} + 180) * 18", 0, 0]}, "arm_l": {"r": [f"math.sin({w}) * 22", 0, 0]},
        "hips": {"p": [0, f"math.abs(math.cos({w})) * 1.2", 0], "r": [0, f"math.sin({w}) * 8", 0]},
        "chest": {"r": [0, f"math.sin({w}) * -10", 0]},
        "tail0": {"r": [0, f"math.sin({w}) * 10", 0]},
    }
    size = {"root": {"s": "variable.size"}}
    divine = {   # phase III: the eight arms fan out, weapons raised
        **{f"xarm_{nm}": {"r": [0, 0, ("-" if nm[0] == "r" else "") + "10"]} for nm in XARMS},
        "chest": {"r": [-4, 0, 0]},
    }
    return {"idle": loop(idle), "walk": loop(walk), "size": loop(size), "divine": loop(divine)}


def acts():
    out = []
    j = lambda x: {"jaw": {"r": (x, 0, 0)}}
    ar = lambda a, f=None, h=None: {**{"arm_r": {"r": a}}, **({"farm_r": {"r": f}} if f else {}), **({"hand_r": {"r": h}} if h else {})}
    al = lambda a, f=None: {**{"arm_l": {"r": a}}, **({"farm_l": {"r": f}} if f else {})}
    crouch = lambda d: {"hips": {"p": (0, -d, 0)}, "leg_r": {"r": (-d * 6, 0, -14)}, "leg_l": {"r": (-d * 6, 0, 14)},
                        "shin_r": {"r": (d * 12, 0, 8)}, "shin_l": {"r": (d * 12, 0, -8)}, "foot_r": {"r": (-d * 6, 0, 4)}, "foot_l": {"r": (-d * 6, 0, -4)}}
    rest_arms = {"arm_r": {"r": (0, 0, 0)}, "farm_r": {"r": (0, 0, 0)}, "hand_r": {"r": (0, 0, 0)}, "arm_l": {"r": (0, 0, 0)}, "farm_l": {"r": (0, 0, 0)},
                 "chest": {"r": (0, 0, 0)}, "torso": {"r": (0, 0, 0)}, "head": {"r": (0, 0, 0)}}
    # 1 descend (48, 7): lands from the sky in a crouch, trident planted
    a = Act("descend", 48, [7])
    a.at(0, {**crouch(0.5), **ar((-150, 0, 0), (0, 0, 0)), **al((-40, 0, 30)), "tail0": {"r": (-30, 0, 0)}})
    a.at(7, {**crouch(5), **ar((-40, 0, -10), (-40, 0, 0)), **al((-20, 0, 40), (-40, 0, 0)), "torso": {"r": (24, 0, 0)}, "head": {"r": (-14, 0, 0)}}, "in")
    a.at(30, {**crouch(4)}, "lin")
    a.at(48, {**crouch(0), **ar((0, 0, 0), (0, 0, 0)), **al((0, 0, 0), (0, 0, 0)), "torso": {"r": (0, 0, 0)}, "head": {"r": (0, 0, 0)}, "tail0": {"r": (0, 0, 0)}})
    out.append(a)
    # 2 taunt (44, 22): khon flourish - spins the trident and beckons
    a = Act("taunt", 44, [22])
    a.at(10, {**ar((-90, 0, -20), (-30, 0, 0)), "trident": {"r": (0, 0, 0)}, "head": {"r": (-8, 20, 0)}, **j(20)})
    a.at(22, {**ar((-80, 0, -30), (-40, 0, 0)), "trident": {"r": (0, 360, 0)}, **al((-70, 30, 20), (-60, 0, 0)), "head": {"r": (-10, -10, 8)}, **j(34)}, "io")
    a.at(34, {**al((-50, 20, 10), (-90, 0, 0)), "trident": {"r": (0, 720, 0)}}, "io")
    a.at(44, {**rest_arms, "trident": {"r": (0, 720, 0)}, **j(6)})
    out.append(a)
    # 3 combo (42, 9, 20, 33): thrust - spinning sweep - overhead slam
    a = Act("combo", 42, [9, 20, 33])
    a.at(6, {**ar((-40, 30, 0), (-60, 0, 0)), "trident": {"r": (-90, 0, 0)}, "chest": {"r": (0, 30, 0)}, **crouch(2)})
    a.at(9, {**ar((-90, 0, 0), (0, 0, 0)), "trident": {"r": (-90, 0, 0)}, "chest": {"r": (0, -20, 0)}, "torso": {"r": (10, 0, 0)}}, "in")
    a.at(15, {**ar((-60, 60, -40), (-20, 0, 0)), "trident": {"r": (-90, 0, 0)}, "chest": {"r": (0, 50, 0)}}, "out")
    a.at(20, {**ar((-70, -70, -30), (-10, 0, 0)), "chest": {"r": (0, -60, 0)}, "hips": {"r": (0, -20, 0)}}, "in")
    a.at(28, {**ar((-170, 0, -10), (-20, 0, 0)), "trident": {"r": (-20, 0, 0)}, "chest": {"r": (-14, 0, 0)}, "hips": {"r": (0, 0, 0)}, **crouch(1)}, "out")
    a.at(33, {**ar((-40, 0, 0), (-10, 0, 0)), "trident": {"r": (-80, 0, 0)}, "chest": {"r": (26, 0, 0)}, **crouch(5)}, "in")
    a.at(42, {**rest_arms, "trident": {"r": (0, 0, 0)}, **crouch(0)})
    out.append(a)
    # 4 jump (10, 7)
    a = Act("jump", 10, [7])
    a.at(6, {**crouch(6), **ar((20, 0, 0)), **al((20, 0, 0)), "torso": {"r": (20, 0, 0)}})
    a.at(10, {**crouch(-1), **ar((-160, 0, -20)), **al((-150, 0, 20)), "torso": {"r": (-10, 0, 0)}}, "in")
    out.append(a)
    # 5 air (20): tucked somersault with the trident overhead
    a = Act("air", 20)
    a.at(0, {**ar((-160, 0, -20)), **al((-150, 0, 20)), "leg_r": {"r": (-60, 0, 0)}, "leg_l": {"r": (-60, 0, 0)}, "shin_r": {"r": (80, 0, 0)}, "shin_l": {"r": (80, 0, 0)}})
    a.at(20, {**ar((-150, 0, -10), (-30, 0, 0)), "trident": {"r": (-40, 0, 0)}, "leg_r": {"r": (-40, 0, 0)}, "leg_l": {"r": (-40, 0, 0)}, "hips": {"r": (360, 0, 0)}}, "lin")
    out.append(a)
    # 6 slam (20, 3)
    a = Act("slam", 20, [3])
    a.at(0, {**ar((-150, 0, -10), (-30, 0, 0)), "trident": {"r": (-40, 0, 0)}, "hips": {"r": (0, 0, 0)}}, "hold")
    a.at(3, {**crouch(6), **ar((-30, 0, 0), (-20, 0, 0)), "trident": {"r": (-100, 0, 0)}, "torso": {"r": (30, 0, 0)}, **al((-30, 0, 40))}, "in")
    a.at(20, {**crouch(0), **rest_arms, "trident": {"r": (0, 0, 0)}, **al((0, 0, 0))})
    out.append(a)
    # 7 tail_whip (32, 16): spinning tail sweep
    a = Act("tail_whip", 32, [16])
    tw = lambda y, x=0: {f"tail{i}": {"r": (x, y, 0)} for i in range(6)}
    a.at(10, {**tw(-10, 20), "hips": {"r": (0, 60, 0)}, **crouch(3)})
    a.at(16, {**tw(30, -10), "hips": {"r": (0, -300, 0)}}, "in")
    a.at(32, {**tw(0), "hips": {"r": (0, -360, 0)}, **crouch(0)}, "out")
    out.append(a)
    # 8 dash (14, 6): wind-step thrust from behind
    a = Act("dash", 14, [6])
    a.at(3, {**ar((-30, 40, 0), (-70, 0, 0)), "trident": {"r": (-90, 0, 0)}, "chest": {"r": (0, 30, 0)}, **crouch(3)})
    a.at(6, {**ar((-95, 0, 0), (0, 0, 0)), "chest": {"r": (0, -20, 0)}, "torso": {"r": (16, 0, 0)}}, "in")
    a.at(14, {**rest_arms, "trident": {"r": (0, 0, 0)}, **crouch(0)})
    out.append(a)
    # 9 guard (52): Vajra guard - trident held across, still as a statue
    a = Act("guard", 52)
    a.at(8, {**ar((-70, 50, 0), (-50, 0, 0)), "trident": {"r": (0, 0, 90)}, **al((-70, -50, 0), (-50, 0, 0)), **crouch(3), "head": {"r": (8, 0, 0)}}, "out")
    a.at(52, {**ar((-70, 50, 0), (-50, 0, 0)), **crouch(3)}, "lin")
    out.append(a)
    # 10 counter (16, 5)
    a = Act("counter", 16, [5])
    a.at(2, {**ar((-20, 60, 0), (-80, 0, 0)), "trident": {"r": (-90, 0, 0)}, "chest": {"r": (0, 50, 0)}})
    a.at(5, {**ar((-100, -10, 0), (0, 0, 0)), "chest": {"r": (0, -30, 0)}, "torso": {"r": (20, 0, 0)}}, "in")
    a.at(16, {**rest_arms, "trident": {"r": (0, 0, 0)}})
    out.append(a)
    # 11 ignite (40, 24): the tail is set ablaze - he lifts it overhead
    a = Act("ignite", 40, [24])
    a.at(16, {**tw(0, -20), "tail3": {"r": (-30, 0, 0)}, "tail4": {"r": (-40, 0, 0)}, **al((-120, 0, 30), (-40, 0, 0)), "head": {"r": (-20, 30, 0)}})
    a.at(24, {"tail5": {"r": (-50, 0, 0)}, **j(40), "chest": {"r": (-10, 0, 0)}}, "in")
    a.at(40, {**tw(0), "tail3": {"r": (0, 0, 0)}, "tail4": {"r": (0, 0, 0)}, "tail5": {"r": (0, 0, 0)}, **al((0, 0, 0), (0, 0, 0)), "head": {"r": (0, 0, 0)}, **j(6), "chest": {"r": (0, 0, 0)}})
    out.append(a)
    # 12 fire_spin (32, 16)
    a = Act("fire_spin", 32, [16])
    a.at(10, {**ar((-90, 0, -60), (0, 0, 0)), "trident": {"r": (-90, 0, 0)}, **al((-90, 0, 60)), **crouch(2)})
    a.at(16, {"root": {"r": (0, 360, 0)}, **tw(20, 10)}, "in")
    a.at(26, {"root": {"r": (0, 720, 0)}}, "out")
    a.at(32, {"root": {"r": (0, 720, 0)}, **rest_arms, "trident": {"r": (0, 0, 0)}, **al((0, 0, 0)), **crouch(0), **tw(0)})
    out.append(a)
    # 13 shrunk (20, loop): tiny and darting
    a = Act("shrunk", 20, [], loop=True)
    a.at(0, {**crouch(4), **ar((-60, 0, -30)), **al((-60, 0, 30)), "torso": {"r": (30, 0, 0)}})
    a.at(20, {**crouch(4), **ar((-60, 0, -30)), **al((-60, 0, 30)), "torso": {"r": (30, 0, 0)}}, "lin")
    out.append(a.overlay("root", "p", [0, f"math.abs(math.sin({A} * 900)) * 2", 0]))
    # 14 grow (28, 21): bursts back to size with a stamp
    a = Act("grow", 28, [21])
    a.at(16, {**crouch(5), **ar((-150, 0, -40)), **al((-150, 0, 40)), **j(40)})
    a.at(21, {**crouch(7), **ar((30, 0, -50)), **al((30, 0, 50)), "torso": {"r": (24, 0, 0)}}, "in")
    a.at(28, {**crouch(0), **rest_arms, **al((0, 0, 0)), **j(6)})
    out.append(a)
    # 15 awaken (84, 52): four faces and eight arms unfold
    a = Act("awaken", 84, [52])
    xs = lambda k: {f"xarm_{nm}": {"r": (0, 0, (k if nm[0] == "r" else -k))} for nm in XARMS}
    a.at(0, {**xs(60)})
    a.at(40, {**crouch(3), **ar((-30, 0, -20)), **al((-30, 0, 20)), "head": {"r": (14, 0, 0)}, **xs(70)}, "io")
    a.at(52, {**crouch(-1), **ar((-170, 0, -20)), **al((-170, 0, 20)), "head": {"r": (-24, 0, 0)}, **j(44), **xs(-14), "chest": {"r": (-12, 0, 0)}}, "in")
    a.at(70, {**xs(-6), **j(36)}, "lin")
    a.at(84, {**crouch(0), **rest_arms, **al((0, 0, 0)), **xs(0), **j(6)})
    out.append(a)
    # 16 yawn (240): ULT - leaps up, yawns out the stars and moon, hurls the moons, then the Wind-Father's breath
    a = Act("yawn", 240, [32, 100, 112, 136, 160, 184, 228])
    a.at(24, {**crouch(-1), **ar((-120, 0, -30), (-30, 0, 0)), **al((-120, 0, 30), (-30, 0, 0)), "head": {"r": (-10, 0, 0)}}, "out")
    a.at(32, {"head": {"r": (-34, 0, 0)}, **j(70), "chest": {"r": (-18, 0, 0)}, **ar((-150, 0, -50)), **al((-150, 0, 50))}, "in")
    a.at(96, {"head": {"r": (-30, 0, 0)}, **j(64), "chest": {"r": (-14, 0, 0)}}, "lin")
    for i, mk in enumerate((112, 136, 160, 184)):
        s = -1 if i % 2 == 0 else 1
        a.at(mk - 8, {**ar((-150, s * 40, -40), (-30, 0, 0)), "trident": {"r": (0, 0, s * 40)}, "chest": {"r": (0, -s * 40, 0)}, **j(20), "head": {"r": (0, 0, 0)}}, "out")
        a.at(mk, {**ar((-60, -s * 60, -20), (0, 0, 0)), "trident": {"r": (-80, 0, 0)}, "chest": {"r": (0, s * 40, 0)}}, "in")
    a.at(204, {**ar((-40, 0, -40), (-60, 0, 0)), **al((-40, 0, 40), (-60, 0, 0)), "chest": {"r": (-20, 0, 0)}, "trident": {"r": (0, 0, 0)}, **j(70), "head": {"r": (-20, 0, 0)}}, "io")
    a.at(224, {"chest": {"r": (-26, 0, 0)}, **j(80)}, "lin")
    a.at(228, {**ar((-90, 0, -10), (0, 0, 0)), **al((-90, 0, 10), (0, 0, 0)), "chest": {"r": (16, 0, 0)}, **j(60), "head": {"r": (10, 0, 0)}}, "in")
    a.at(240, {**rest_arms, **al((0, 0, 0)), "trident": {"r": (0, 0, 0)}, **j(6)})
    out.append(a)
    # 17 barrage (50, six strikes): eight-armed weapon storm
    a = Act("barrage", 50, [10, 16, 22, 28, 34, 40])
    order = ["r2", "l2", "r3", "l3", "r4", "l4"]
    for i, mk in enumerate([10, 16, 22, 28, 34, 40]):
        nm = order[i]
        s = -1 if nm[0] == "r" else 1
        a.at(mk - 3, {f"xarm_{nm}": {"r": (-40, 0, -s * 30)}, "chest": {"r": (0, s * 20, 0)}}, "out")
        a.at(mk, {f"xarm_{nm}": {"r": (-100, s * 20, s * 10)}, "chest": {"r": (8, -s * 25, 0)}}, "in")
    a.at(50, {**{f"xarm_{nm}": {"r": (0, 0, 0)} for nm in order}, "chest": {"r": (0, 0, 0)}})
    out.append(a)
    # 18 discus (24, 12): hurls the twin discus
    a = Act("discus", 24, [12])
    a.at(8, {"xarm_r2": {"r": (30, 40, -30)}, "xarm_l2": {"r": (30, -40, 30)}, "chest": {"r": (-10, 0, 0)}})
    a.at(12, {"xarm_r2": {"r": (-110, -20, 10)}, "xarm_l2": {"r": (-110, 20, -10)}, "chest": {"r": (12, 0, 0)}}, "in")
    a.at(24, {"xarm_r2": {"r": (0, 0, 0)}, "xarm_l2": {"r": (0, 0, 0)}, "chest": {"r": (0, 0, 0)}})
    out.append(a)
    # 19 mountain (52, 40): lifts a mountain overhead and hurls it
    a = Act("mountain", 52, [40])
    a.at(18, {**crouch(5), **ar((-170, 0, -10), (-20, 0, 0)), **al((-170, 0, 10), (-20, 0, 0)), "xarm_r4": {"r": (-150, 0, 0)}, "xarm_l4": {"r": (-150, 0, 0)}}, "io")
    a.at(34, {**crouch(3), "chest": {"r": (-24, 0, 0)}, **ar((-190, 0, -10)), **al((-190, 0, 10))}, "out")
    a.at(40, {**crouch(1), "chest": {"r": (26, 0, 0)}, **ar((-60, 0, -10)), **al((-60, 0, 10)), "xarm_r4": {"r": (-40, 0, 0)}, "xarm_l4": {"r": (-40, 0, 0)}}, "in")
    a.at(52, {**crouch(0), **rest_arms, **al((0, 0, 0)), "xarm_r4": {"r": (0, 0, 0)}, "xarm_l4": {"r": (0, 0, 0)}})
    out.append(a)
    # 20 collapse (30): falls to one knee, the wind leaves him
    a = Act("collapse", 30)
    a.at(14, {"hips": {"p": (0, -9, 0)}, "leg_r": {"r": (-80, 0, -10)}, "shin_r": {"r": (100, 0, 0)}, "leg_l": {"r": (-20, 0, 10)}, "shin_l": {"r": (110, 0, 0)},
              "torso": {"r": (30, 0, 0)}, "head": {"r": (30, 0, 0)}, **ar((10, 0, -10)), **al((0, 0, 20)), "trident": {"r": (0, 0, -40)}}, "in")
    a.at(30, {"hips": {"p": (0, -9.5, 0)}}, "lin")
    out.append(a)
    # 21 revive (52, 40)
    a = Act("revive", 52, [40])
    a.at(0, {"hips": {"p": (0, -9.5, 0)}, "leg_r": {"r": (-80, 0, -10)}, "shin_r": {"r": (100, 0, 0)}, "leg_l": {"r": (-20, 0, 10)}, "shin_l": {"r": (110, 0, 0)},
             "torso": {"r": (30, 0, 0)}, "head": {"r": (30, 0, 0)}, **ar((10, 0, -10)), **al((0, 0, 20)), "trident": {"r": (0, 0, -40)}})
    a.at(34, {"hips": {"p": (0, -4, 0)}, "leg_r": {"r": (-30, 0, -14)}, "shin_r": {"r": (40, 0, 0)}, "leg_l": {"r": (-10, 0, 14)}, "shin_l": {"r": (40, 0, 0)},
              "torso": {"r": (10, 0, 0)}, "head": {"r": (-10, 0, 0)}, "trident": {"r": (0, 0, 0)}}, "io")
    a.at(40, {"hips": {"p": (0, 1, 0)}, "leg_r": {"r": (0, 0, -6)}, "shin_r": {"r": (0, 0, 0)}, "leg_l": {"r": (0, 0, 6)}, "shin_l": {"r": (0, 0, 0)},
              **ar((-170, 0, -20)), **al((-160, 0, 30)), "head": {"r": (-28, 0, 0)}, **j(50), "torso": {"r": (-10, 0, 0)}}, "in")
    a.at(52, {"hips": {"p": (0, 0, 0)}, **rest_arms, **al((0, 0, 0)), **j(6)})
    out.append(a)
    # 22 death (80, 68): bows to a worthy foe, then becomes wind
    a = Act("death", 80, [68])
    a.at(20, {"hips": {"p": (0, -9, 0)}, "leg_r": {"r": (-80, 0, -10)}, "shin_r": {"r": (100, 0, 0)}, "leg_l": {"r": (-20, 0, 10)}, "shin_l": {"r": (110, 0, 0)},
              "torso": {"r": (20, 0, 0)}, "head": {"r": (10, 0, 0)}, **ar((-30, 0, -10), (-20, 0, 0)), "trident": {"r": (0, 0, 0)}, **al((-60, 30, 30), (-80, 0, 0))}, "io")
    a.at(56, {"torso": {"r": (44, 0, 0)}, "head": {"r": (30, 0, 0)}, **al((-50, 40, 30), (-100, 0, 0))}, "io")
    a.at(68, {"root": {"s": 1.0}}, "lin")
    a.at(80, {"root": {"s": 0.02, "p": (0, 12, 0)}}, "in")
    out.append(a)
    return out


def entity_cfg():
    return {
        "scale": SCALE,
        "textures": {"default": f"textures/entity/legends/{KEY}"},
        "pre": [
            "variable.divine = math.lerp(variable.divine ?? 0.0, variable.ph >= 3 ? 1.0 : 0.0, 0.05);",
            "variable.size = math.lerp(variable.size ?? 1.0, query.property('legends:var') == 1 ? 0.35 : (variable.ph >= 3 ? 1.4 : 1.0), 0.1);",
            "variable.walkw = variable.mv * variable.calm;",
        ],
        "animate": [{"idle": "variable.calm + 0.15"}, {"walk": "variable.walkw"}, "size", {"divine": "variable.divine"}, "ctrl_act"],
        "visibility": [
            {"face_r": "variable.ph >= 3"}, {"face_l": "variable.ph >= 3"}, {"face_b": "variable.ph >= 3"},
            *[{f"xarm_{nm}": "variable.ph >= 3"} for nm in XARMS],
            *[{f"tailfire{i}": "variable.ph >= 2"} for i in (3, 4, 5)], {"tailfire_tip": "variable.ph >= 2"},
        ],
        "bounds": (6, 8, 3.5),
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
    st = {b: {"rot": v["r"], **({"pos": v["p"]} if "p" in v else {})} for b, v in STANCE.items() if "r" in v}
    st["hips"] = {"pos": (0, -2.4, 0)}
    hide = {f"xarm_{nm}": {"scale": 0.001} for nm in XARMS}
    hide.update({k: {"scale": 0.001} for k in ("face_r", "face_l", "face_b", "tailfire3", "tailfire4", "tailfire5", "tailfire_tip")})
    render_preview([m], f"{out}/han_p1.png", yaw=30, pitch=10, size=700, step=1, pose={**st, **hide})
    render_preview([m], f"{out}/han_p3.png", yaw=-150, pitch=10, size=700, step=1, pose=st)
