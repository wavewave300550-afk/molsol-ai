"""
SERAPH of the Burning Choir (Isaiah 6). Remastered model.

"Each had six wings: with two he covered his face, with two he covered his feet, and with two he
flew." A slender figure of white-gold flame almost hidden by six fiery wings; a radiant face shows
between the face-wings; in its hands the golden tongs holding the live coal from the altar.
Scale 1.5 (10.67 units per block). Faces -Z. Hovers (no legs: a flame-robe tapers below).
"""
import math

from modelkit import Model
from shapes import bevel, orb, spike, strut
from shapes2 import catmull, feather, tube
import lmat as L
from animkit import A, T, Act, loop, sn
from choir_common import cfg, death_act, spawn_act

ID = "geometry.legends.seraph"
KEY = "seraph"
SCALE = 1.5
VARIANTS = {"default": "default"}


def _wing(m, name, root, parent, yaw, pitch, length, n, spread, flame, gold):
    wb = m.bone(name, root, parent)
    for k in range(n):
        t = k / max(1, n - 1)
        ln = length * (0.7 + 0.3 * math.sin(t * math.pi))
        pk = pitch + (t - 0.5) * spread * 0.35
        feather(wb, (root[0], root[1] + 0.12 * k, root[2] + 0.1 * k), ln, 5.0, yaw + (t - 0.5) * spread, pk, flame, thick=0.6, glow=True)
        feather(wb, (root[0], root[1] + 0.12 * k - 0.45, root[2] + 0.1 * k), ln * 0.6, 1.4, yaw + (t - 0.5) * spread, pk, gold, thick=0.9)
    return wb


def build():
    m = Model(ID, seed=71, density=3)
    FL = L.glow("fffbe0", "ff5a14", "vt")
    FL2 = L.glow("ffffff", "ffb030", "vt")
    GD = L.star_gold()
    ROBE = L.glow("fffef0", "ffcf60", "vb")
    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 20, 0), "root")
    tube(body, catmull([(0, 4, 1), (0, 12, 0.5), (0, 22, 0), (0, 29, 0)], 2), 2.0, 6.4, ROBE, glow=True)
    bevel(body, (-3.4, 20, -2.2), (6.8, 9, 4.4), L.solid("fff6dc", 0.02), b=1.2)
    body.add((-3.8, 27.8, -2.6), (7.6, 1.2, 5.2), GD)                                 # gold collar
    head = m.bone("head", (0, 31, 0), "body")
    orb(head, (0, 33.5, 0), 3.0, L.glow("ffffff", "fff0b0", "r"), glow=True)
    bevel(head, (-2.2, 31.2, -2.2), (4.4, 4.6, 4.4), L.solid("fffaf0", 0.02), b=1.0)
    for sx in (-1, 1):
        head.add((sx * 1.0 - 0.45, 33.6, -2.45), (0.9, 0.7, 0.3), L.solid("ffb020", 0.02))   # burning eyes
    for side, sx in (("r", -1), ("l", 1)):
        arm = m.bone(f"arm_{side}", (sx * 3.6, 27, 0), "body")
        tube(arm, [(sx * 3.6, 27, 0), (sx * 4.6, 21.5, -2.5), (sx * 2.2, 18.5, -5.0)], 2.0, 1.5, L.solid("fff6dc", 0.02))
    tongs = m.bone("tongs", (0, 18.5, -5), "arm_r")
    for sx in (-1, 1):
        strut(tongs, (sx * 1.6, 18.5, -5), (sx * 0.5, 15.0, -9.5), 0.6, GD)
    coal = m.bone("coal", (0, 14.5, -10), "tongs")
    orb(coal, (0, 14.5, -10), 1.5, L.glow("fff0c0", "ff3a10", "r"), glow=True)
    bevel(coal, (-1.0, 13.6, -11.0), (2.0, 1.8, 2.0), L.solid("3a0a04", 0.08), b=0.3)
    # six wings
    _wing(m, "wing_t_r", (-3.0, 31.5, -1.0), "body", 38, -38, 14, 6, 34, FL2, GD)     # face-covering: cross before the face
    _wing(m, "wing_t_l", (3.0, 31.5, -1.4), "body", -38, -38, 14, 6, 34, FL2, GD)
    _wing(m, "wing_m_r", (-3.0, 27, 2), "body", -96, -14, 26, 8, 56, FL, GD)          # flying: spread wide
    _wing(m, "wing_m_l", (3.0, 27, 2), "body", 96, -14, 26, 8, 56, FL, GD)
    _wing(m, "wing_b_r", (-2.6, 12, -0.5), "body", 30, 42, 13, 6, 34, FL, GD)        # feet-covering: cross below
    _wing(m, "wing_b_l", (2.6, 12, -0.9), "body", -30, 42, 13, 6, 34, FL, GD)
    halo = m.bone("halo", (0, 39, 2), "head", floating=True)
    from shapes import ring
    ring(halo, (0, 39, 2), 4.0, 10, L.glow("ffffff", "ffcf50", "u"), thickness=0.6, width=0.5, plane="xz", glow=True)
    return m


def loops():
    flap = f"math.sin({T} * 220)"
    idle = {
        "root": {"p": [0, sn(90, amp=1.0), 0]},
        "wing_m_r": {"r": [0, f"{flap} * 14", f"{flap} * -26"]}, "wing_m_l": {"r": [0, f"{flap} * -14", f"{flap} * 26"]},
        "wing_t_r": {"r": [sn(220, 40, 5), 0, 0]}, "wing_t_l": {"r": [sn(220, 40, 5), 0, 0]},
        "wing_b_r": {"r": [sn(220, 80, 6), 0, 0]}, "wing_b_l": {"r": [sn(220, 80, 6), 0, 0]},
        "head": {"r": [sn(60, amp=4), sn(40, amp=8), 0]},
        "coal": {"s": f"1 + {sn(300, amp=0.12)}"}, "halo": {"r": [0, f"{T} * 60", 0]},
        "arm_r": {"r": [sn(70, amp=4), 0, 0]},
    }
    return {"idle": loop(idle)}


def acts():
    out = [spawn_act()]
    open_face = {"wing_t_r": {"r": (-30, -40, 0)}, "wing_t_l": {"r": (-30, 40, 0)}}
    shut = {"wing_t_r": {"r": (0, 0, 0)}, "wing_t_l": {"r": (0, 0, 0)}}
    # dive (32, 16)
    a = Act("dive", 32, [16])
    a.at(12, {"body": {"r": (20, 0, 0)}, "wing_m_r": {"r": (0, 0, -40)}, "wing_m_l": {"r": (0, 0, 40)}})
    a.at(16, {"body": {"r": (55, 0, 0)}, "wing_m_r": {"r": (0, -60, 10)}, "wing_m_l": {"r": (0, 60, -10)}, **open_face}, "in")
    a.at(32, {"body": {"r": (0, 0, 0)}, "wing_m_r": {"r": (0, 0, 0)}, "wing_m_l": {"r": (0, 0, 0)}, **shut}, "out")
    out.append(a)
    # coal (24, 12): the tongs fling the live coal
    a = Act("coal", 24, [12])
    a.at(8, {"arm_r": {"r": (-60, 0, -20)}, "tongs": {"r": (-40, 0, 0)}, **open_face})
    a.at(12, {"arm_r": {"r": (30, 0, 0)}, "tongs": {"r": (40, 0, 0)}, "coal": {"s": 0.01}}, "in")
    a.at(22, {"coal": {"s": 0.01}}, "lin")
    a.at(24, {"arm_r": {"r": (0, 0, 0)}, "tongs": {"r": (0, 0, 0)}, "coal": {"s": 1.0}, **shut})
    out.append(a)
    # sanctus (48, 12, 24, 36): three wingbeats
    a = Act("sanctus", 48, [12, 24, 36])
    for mk in (12, 24, 36):
        a.at(mk - 4, {"wing_m_r": {"r": (0, 0, -50)}, "wing_m_l": {"r": (0, 0, 50)}, "root": {"p": (0, 3, 0)}}, "out")
        a.at(mk, {"wing_m_r": {"r": (0, 0, 40)}, "wing_m_l": {"r": (0, 0, -40)}, "root": {"p": (0, -1, 0)}}, "in")
    a.at(48, {"wing_m_r": {"r": (0, 0, 0)}, "wing_m_l": {"r": (0, 0, 0)}, "root": {"p": (0, 0, 0)}})
    out.append(a)
    # trisagion (72, 18, 38, 58): "Holy, holy, holy" - face revealed, six wings blaze outward
    a = Act("trisagion", 72, [18, 38, 58])
    for i, mk in enumerate((18, 38, 58)):
        a.at(mk - 6, {**open_face, "wing_b_r": {"r": (30, 30, 0)}, "wing_b_l": {"r": (30, -30, 0)}, "head": {"r": (-20, 0, 0)},
                      "wing_m_r": {"r": (0, 0, -50)}, "wing_m_l": {"r": (0, 0, 50)}, "root": {"s": 1.0}}, "out")
        a.at(mk, {"wing_m_r": {"r": (0, 0, 30)}, "wing_m_l": {"r": (0, 0, -30)}, "root": {"s": 1.18}, "halo": {"s": 1.8}}, "in")
    a.at(72, {**shut, "wing_b_r": {"r": (0, 0, 0)}, "wing_b_l": {"r": (0, 0, 0)}, "head": {"r": (0, 0, 0)}, "wing_m_r": {"r": (0, 0, 0)},
              "wing_m_l": {"r": (0, 0, 0)}, "root": {"s": 1.0}, "halo": {"s": 1.0}})
    out.append(a)
    out.append(death_act(40, 32, {"wing_m_r": {"r": (0, 0, 50)}, "wing_m_l": {"r": (0, 0, -50)}, "body": {"r": (30, 0, 0)}}))
    # veil (50, 16): flies to the Word and folds its wings around it (projectile shield)
    a = Act("veil", 50, [16])
    a.at(12, {"wing_m_r": {"r": (0, -70, 20)}, "wing_m_l": {"r": (0, 70, -20)}, "wing_t_r": {"r": (0, -30, 0)}, "wing_t_l": {"r": (0, 30, 0)}}, "out")
    a.at(16, {"root": {"s": 1.1}}, "in")
    a.at(44, {"root": {"s": 1.1}}, "lin")
    a.at(50, {"wing_m_r": {"r": (0, 0, 0)}, "wing_m_l": {"r": (0, 0, 0)}, "wing_t_r": {"r": (0, 0, 0)}, "wing_t_l": {"r": (0, 0, 0)}, "root": {"s": 1.0}})
    out.append(a)
    # chorus (60, 24): sings with the Word (concord)
    a = Act("chorus", 60, [24])
    a.at(18, {**open_face, "head": {"r": (-24, 0, 0)}, "wing_m_r": {"r": (0, 0, -40)}, "wing_m_l": {"r": (0, 0, 40)}, "halo": {"s": 1.6}})
    a.at(24, {"halo": {"s": 2.2}}, "in")
    a.at(60, {**shut, "head": {"r": (0, 0, 0)}, "wing_m_r": {"r": (0, 0, 0)}, "wing_m_l": {"r": (0, 0, 0)}, "halo": {"s": 1.0}})
    out.append(a)
    return out


def entity_cfg():
    return cfg(KEY, SCALE, bounds=(6, 6, 2.0))


if __name__ == "__main__":
    import sys
    from modelkit import render_preview, island_report, deflicker
    m = build(); m.paint(); print(m.stats(), island_report(m), deflicker(m))
    render_preview([m], f"{sys.argv[1]}/seraph.png", yaw=25, pitch=8, size=500, step=1)
