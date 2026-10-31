"""
CHERUB of the Eastern Gate (Ezekiel 1 & 10, Genesis 3:24). Remastered model.

A tall guardian of burnished bronze with four faces - man (front), lion (right), ox (left) and
eagle (behind) - four wings full of eyes (two raised, two folded over the body), straight legs
ending in calf's hooves, and the flaming sword that turns every way.
Scale 1.5 (10.67 units per block). Faces -Z.
"""
import math

from modelkit import Model
from shapes import bevel, orb, ring, spike, strut
from shapes2 import catmull, feather, tube
import lmat as L
from animkit import A, T, Act, loop, sn
from choir_common import cfg, death_act, spawn_act

ID = "geometry.legends.cherub"
KEY = "cherub"
SCALE = 1.5
VARIANTS = {"default": "default"}


def _eyed_feathers(m, name, root, parent, yaw, pitch, length, n, spread, mat, eye, eyes=True):
    wb = m.bone(name, root, parent)
    for k in range(n):
        t = k / max(1, n - 1)
        ln = length * (0.75 + 0.25 * math.sin(t * math.pi))
        feather(wb, (root[0], root[1] + 0.1 * k, root[2] + 0.1 * k), ln, 4.6, yaw + (t - 0.5) * spread, pitch + (t - 0.5) * spread * 0.4, mat, thick=0.7)
    for k in range(3 if eyes else 0):
        t = (k + 0.5) / 3
        ang = math.radians(yaw + (t - 0.5) * spread)
        p = (root[0] + math.sin(ang) * length * 0.55 * math.cos(math.radians(pitch)), root[1] + 0.6 - math.sin(math.radians(pitch)) * length * 0.55,
             root[2] - math.cos(ang) * length * 0.55)
        orb(wb, p, 0.9, eye, glow=True)
    return wb


def build():
    m = Model(ID, seed=73, density=3)
    BR = L.burnished_bronze()
    GD = L.star_gold()
    FTH = L.burnished_bronze()
    EYE = L.glow("ffffff", "4ab0ff", "r")
    SWORD = L.glow("fffbe0", "ff6a10", "vt")
    root = m.bone("root", (0, 0, 0))
    hips = m.bone("hips", (0, 20, 0), "root")
    bevel(hips, (-4.6, 17.5, -2.8), (9.2, 5, 5.6), BR, b=1.2)
    for k in range(8):                                                       # bronze lamellar skirt
        ang = k / 8 * 2 * math.pi
        hips.add((math.cos(ang) * 4.6 - 1.4, 12.5, math.sin(ang) * 3.4 - 1.4), (2.8, 6, 2.8), L.burnished_bronze(), rotation=(0, -math.degrees(ang), 0),
                 pivot=(math.cos(ang) * 4.6, 15.5, math.sin(ang) * 3.4))
    for side, sx in (("r", -1), ("l", 1)):                     # straight legs, calf hooves
        lg = m.bone(f"leg_{side}", (sx * 2.6, 19, 0), "hips")
        tube(lg, [(sx * 2.6, 19, 0), (sx * 2.8, 9, 0), (sx * 2.8, 2.4, 0)], 3.6, 2.8, BR)
        lg.add((sx * 2.8 - 2.0, 9.0, -2.0), (4.0, 1.4, 4.0), GD)
        for ox in (-0.8, 0.8):
            bevel(lg, (sx * 2.8 + ox - 0.8, 0, -2.2), (1.6, 2.6, 3.8), L.solid("3a2810", 0.05), b=0.3)
    torso = m.bone("torso", (0, 24, 0), "hips")
    bevel(torso, (-5.6, 22, -3.4), (11.2, 12, 6.8), BR, b=2)
    torso.add((-5.9, 31.2, -3.7), (11.8, 1.4, 7.4), GD)
    torso.add((-1.4, 25, -3.9), (2.8, 5, 0.6), GD)
    head = m.bone("head", (0, 36, 0), "torso")
    bevel(head, (-3.4, 34.5, -3.4), (6.8, 7, 6.8), BR, b=1.5)
    # man (front)
    head.add((-2.6, 36.2, -3.7), (5.2, 4.2, 0.4), L.solid("e8c08a", 0.03))
    for sx in (-1, 1):
        head.add((sx * 1.1 - 0.4, 38.4, -3.95), (0.8, 0.6, 0.3), L.solid("4ab0ff", 0.02))
    # lion (right, -x): mane + muzzle
    for k in range(7):
        ang = math.radians(-90 + k * 30)
        spike(head, (-3.4, 38 + math.sin(ang) * 2.5, math.cos(ang) * 2.5), (-5.6, 38 + math.sin(ang) * 4.6, math.cos(ang) * 4.6), 2.0, GD, steps=2)
    bevel(head, (-5.0, 35.8, -1.5), (1.8, 2.6, 3.0), BR, b=0.4)
    # ox (left, +x): horns + broad snout
    bevel(head, (3.2, 35.6, -1.6), (2.2, 2.8, 3.2), BR, b=0.5)
    for dz in (-2.0, 2.0):
        pts = catmull([(3.6, 40.4, dz), (6.0, 41.4, dz * 1.3), (6.8, 43.6, dz * 1.1)], 2)
        tube(head, pts, 1.4, 0.6, L.ivory())
    # eagle (back, +z): beak
    spike(head, (0, 38, 3.4), (0, 36.4, 7.2), 2.4, GD, steps=3)
    for sx in (-1, 1):
        head.add((sx * 1.6 - 0.4, 38.6, 3.25), (0.8, 0.7, 0.3), L.solid("ffcc30", 0.02))
    # arms; the flaming sword
    for side, sx in (("r", -1), ("l", 1)):
        arm = m.bone(f"arm_{side}", (sx * 6.2, 32.5, 0), "torso")
        tube(arm, [(sx * 6.2, 32.5, 0), (sx * 7.2, 26.5, -1.0), (sx * 6.4, 21.5, -3.0)], 2.8, 2.2, BR)
        bevel(arm, (sx * 6.4 - 1.4, 19.6, -4.4), (2.8, 2.6, 2.8), BR, b=0.4)
    sword = m.bone("sword", (-6.4, 20.8, -3.2), "arm_r")
    bevel(sword, (-8.4, 20.0, -4.2), (4.0, 1.2, 2.0), GD, b=0.3)
    sword.add((-6.9, 21.0, -3.7), (1.0, 3.6, 1.0), GD)
    blade = catmull([(-6.4, 24.6, -3.2), (-7.6, 31, -3.2), (-5.4, 38, -3.2), (-7.2, 45, -3.2), (-6.4, 51.5, -3.2)], 2)
    tube(sword, blade, 3.4, 0.8, SWORD, glow=True, overlap=0.4)
    tube(sword, blade, 1.0, 0.4, L.glow("ffffff", "fff0b0", "u"), glow=True, overlap=0.4)
    # four wings full of eyes: two raised, two folded over the body
    _eyed_feathers(m, "wing_u_r", (-3.2, 33, 3), "torso", -140, -58, 26, 8, 50, FTH, EYE)     # raised high
    _eyed_feathers(m, "wing_u_l", (3.2, 33, 3), "torso", 140, -58, 26, 8, 50, FTH, EYE)
    _eyed_feathers(m, "wing_c_r", (-4.6, 31.5, -0.5), "torso", -16, 72, 18, 6, 30, FTH, EYE, eyes=False)   # folded over the body
    _eyed_feathers(m, "wing_c_l", (4.6, 31.5, -0.9), "torso", 16, 72, 18, 6, 30, FTH, EYE, eyes=False)
    ward = m.bone("ward", (0, 26, 0), "root", floating=True)
    ring(ward, (0, 26, 0), 9.0, 16, L.glow("fffbe0", "ffc040", "u"), thickness=0.6, width=0.6, plane="xz", glow=True)
    return m


def loops():
    idle = {
        "root": {"p": [0, sn(80, amp=0.8), 0]},
        "wing_u_r": {"r": [sn(120, amp=6), sn(90, amp=6), 0]}, "wing_u_l": {"r": [sn(120, amp=6), sn(90, amp=-6), 0]},
        "wing_c_r": {"r": [sn(120, 60, 3), 0, 0]}, "wing_c_l": {"r": [sn(120, 60, 3), 0, 0]},
        "head": {"r": [0, f"{T} * 22", 0]},             # the four faces slowly turn every way
        "sword": {"r": [0, f"{T} * 90", 0]},            # the sword that turns every way
        "ward": {"s": "query.property('legends:var') == 1 ? 1.0 : 0.001", "r": [0, f"{T} * 80", 0]},
        "arm_l": {"r": [sn(70, amp=4), 0, 0]},
    }
    return {"idle": loop(idle)}


def acts():
    out = [spawn_act()]
    # sweep (32, 16): the flaming sword sweeps every way
    a = Act("sweep", 32, [16])
    a.at(10, {"arm_r": {"r": (-90, 0, -40)}, "sword": {"r": (0, 0, 70)}, "torso": {"r": (0, 40, 0)}})
    a.at(16, {"arm_r": {"r": (-80, 0, 30)}, "torso": {"r": (0, -320, 0)}}, "in")
    a.at(32, {"arm_r": {"r": (0, 0, 0)}, "sword": {"r": (0, 0, 0)}, "torso": {"r": (0, -360, 0)}}, "out")
    out.append(a)
    # ward (40, 16): wings raised in blessing over the Word
    a = Act("ward", 40, [16])
    a.at(12, {"wing_u_r": {"r": (-30, 30, 0)}, "wing_u_l": {"r": (-30, -30, 0)}, "arm_l": {"r": (-140, 0, 0)}})
    a.at(16, {"root": {"s": 1.1}}, "in")
    a.at(40, {"wing_u_r": {"r": (0, 0, 0)}, "wing_u_l": {"r": (0, 0, 0)}, "arm_l": {"r": (0, 0, 0)}, "root": {"s": 1.0}})
    out.append(a)
    # gaze4 (48, 12, 24, 36): the four faces turn to judge
    a = Act("gaze4", 48, [12, 24, 36])
    for i, mk in enumerate((12, 24, 36)):
        a.at(mk - 3, {"head": {"r": (-10, 90 * i - 20, 0)}}, "out")
        a.at(mk, {"head": {"r": (6, 90 * (i + 1), 0)}, "root": {"s": 1.06 if i % 2 == 0 else 1.0}}, "in")
    a.at(48, {"head": {"r": (0, 360, 0)}, "root": {"s": 1.0}})
    out.append(a)
    # gate (60, 40): descends and plants the flaming sword - the gate of Eden
    a = Act("gate", 60, [40])
    a.at(30, {"arm_r": {"r": (-160, 0, -10)}, "sword": {"r": (180, 0, 0)}, "wing_u_r": {"r": (-40, 30, 0)}, "wing_u_l": {"r": (-40, -30, 0)}}, "io")
    a.at(40, {"arm_r": {"r": (-40, 0, 10)}, "hips": {"p": (0, -3, 0)}}, "in")
    a.at(60, {"hips": {"p": (0, -3, 0)}}, "lin")
    out.append(a)
    out.append(death_act(40, 32, {"wing_u_r": {"r": (40, 0, 0)}, "wing_u_l": {"r": (40, 0, 0)}, "torso": {"r": (30, 0, 0)}}))
    # chorus (60, 24): concord with the Word
    a = Act("chorus", 60, [24])
    a.at(18, {"wing_u_r": {"r": (-40, 40, 0)}, "wing_u_l": {"r": (-40, -40, 0)}, "arm_r": {"r": (-170, 0, 0)}, "sword": {"r": (0, 0, 0)}})
    a.at(24, {"root": {"s": 1.12}}, "in")
    a.at(60, {"wing_u_r": {"r": (0, 0, 0)}, "wing_u_l": {"r": (0, 0, 0)}, "arm_r": {"r": (0, 0, 0)}, "root": {"s": 1.0}})
    out.append(a)
    return out


def entity_cfg():
    return cfg(KEY, SCALE, bounds=(6, 7, 2.5))


if __name__ == "__main__":
    import sys
    from modelkit import render_preview, island_report, deflicker
    m = build(); m.paint(); print(m.stats(), island_report(m), deflicker(m))
    render_preview([m], f"{sys.argv[1]}/cherub.png", yaw=30, pitch=8, size=500, step=1, pose={"ward": {"scale": 0.001}})
