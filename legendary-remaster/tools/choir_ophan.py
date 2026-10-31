"""
OPHAN of the Thrones (Ezekiel 1:15-21). Remastered model.

"Their appearance was like beryl ... a wheel within a wheel ... and their rims were full of eyes
all around." Two great beryl wheels crossed at right angles with an inner gold wheel, every rim
set with eyes, fiery spokes and a burning heart; it rolls in any direction without turning.
Scale 1.5 (10.67 units per block). Floats; centre ~ (0, 22, 0).
"""
import math

from modelkit import Model
from shapes import bevel, orb, ring, spike, strut
import lmat as L
from animkit import A, T, Act, loop, sn
from choir_common import cfg, death_act, spawn_act

ID = "geometry.legends.ophan"
KEY = "ophan"
SCALE = 1.5
VARIANTS = {"default": "default"}
C = (0.0, 22.0, 0.0)


def _eyes_on_ring(bone, center, r, n, plane, eye, phase=0.0):
    cx, cy, cz = center
    for k in range(n):
        a = phase + k / n * 2 * math.pi
        if plane == "xy":
            p = (cx + math.cos(a) * r, cy + math.sin(a) * r, cz - 1.3)
        else:
            p = (cx - 1.3, cy + math.cos(a) * r, cz + math.sin(a) * r)
        orb(bone, p, 1.05, eye, glow=True)


def build():
    m = Model(ID, seed=79, density=3)
    BE = L.beryl()
    GD = L.star_gold()
    EYE = L.glow("ffffff", "3a9cff", "r")
    FIRE = L.glow("fff6c0", "ff6a14", "vt")
    root = m.bone("root", (0, 0, 0))
    wa = m.bone("wheel_a", C, "root")
    ring(wa, C, 15, 22, BE, thickness=2.6, width=3.2, plane="xy")
    ring(wa, C, 13.2, 22, GD, thickness=0.8, width=3.6, plane="xy")
    _eyes_on_ring(wa, C, 15, 10, "xy", EYE)
    for k in range(6):
        a = k / 6 * 2 * math.pi
        strut(wa, C, (math.cos(a) * 13, C[1] + math.sin(a) * 13, 0), 1.0, FIRE, glow=True, depth=0.8)
    wb = m.bone("wheel_b", C, "root")
    ring(wb, C, 12.5, 20, BE, thickness=2.4, width=3.0, plane="yz")
    ring(wb, C, 10.9, 20, GD, thickness=0.8, width=3.4, plane="yz")
    _eyes_on_ring(wb, C, 12.5, 8, "yz", EYE, phase=0.4)
    wc = m.bone("wheel_c", C, "root")
    ring(wc, C, 8.5, 14, GD, thickness=1.4, width=1.6, plane="xz")
    core = m.bone("core", C, "root")
    orb(core, C, 4.2, L.glow("ffffff", "ffa030", "r"), glow=True)
    orb(core, C, 2.8, L.solid("fff2c8", 0.02))
    for k in range(6):
        a = k / 6 * 2 * math.pi
        spike(core, (math.cos(a) * 3.5, C[1] + 3, math.sin(a) * 3.5), (math.cos(a) * 5, C[1] + 9, math.sin(a) * 5), 1.6, FIRE, glow=True, steps=2)
    return m


def loops():
    idle = {
        "root": {"p": [0, sn(70, amp=1.2), 0]},
        "wheel_a": {"r": [0, 0, f"{T} * 45"]}, "wheel_b": {"r": [f"{T} * -60", 0, 0]}, "wheel_c": {"r": [0, f"{T} * 90", 0]},
        "core": {"s": f"1 + {sn(240, amp=0.1)}"},
    }
    return {"idle": loop(idle)}


def acts():
    out = [spawn_act()]
    # roll (32, 12): stands up and rolls like a wheel
    a = Act("roll", 32, [12])
    a.at(10, {"root": {"r": (0, 0, 0)}, "wheel_b": {"s": 0.85}})
    a.at(12, {"root": {"r": (0, 0, 0)}}, "in")
    a.at(32, {"wheel_b": {"s": 1.0}})
    out.append(a.overlay("wheel_a", "r", [0, 0, f"-{A} * 900"]))
    # eyes (48, 16): every eye opens wide
    a = Act("eyes", 48, [16])
    a.at(12, {"wheel_a": {"s": 1.15}, "wheel_b": {"s": 1.15}, "core": {"s": 0.8}})
    a.at(16, {"core": {"s": 1.5}}, "in")
    a.at(48, {"wheel_a": {"s": 1.0}, "wheel_b": {"s": 1.0}, "core": {"s": 1.0}})
    out.append(a)
    # restore (80): beams its fire into the Word
    a = Act("restore", 80)
    a.at(16, {"core": {"s": 1.4}, "wheel_c": {"s": 1.4}}, "out")
    a.at(80, {"core": {"s": 1.4}, "wheel_c": {"s": 1.4}}, "lin")
    out.append(a.overlay("wheel_c", "r", [0, f"{A} * 400", 0]))
    # wheels (80, 20): wheels within wheels - a gravity well of fiery spokes
    a = Act("wheels", 80, [20])
    a.at(16, {"wheel_a": {"r": (90, 0, 0), "s": 1.4}, "wheel_b": {"s": 1.3}, "core": {"s": 1.6}}, "io")
    a.at(20, {"core": {"s": 2.0}}, "in")
    a.at(72, {"wheel_a": {"r": (90, 0, 0), "s": 1.4}}, "lin")
    a.at(80, {"wheel_a": {"r": (0, 0, 0), "s": 1.0}, "wheel_b": {"s": 1.0}, "core": {"s": 1.0}})
    out.append(a.overlay("wheel_a", "r", [0, 0, f"{A} * 720"]).overlay("wheel_b", "r", [f"{A} * 600", 0, 0]))
    out.append(death_act(40, 32, {"wheel_a": {"r": (40, 0, 60)}, "wheel_b": {"r": (0, 40, 0)}}))
    # chorus (60, 24)
    a = Act("chorus", 60, [24])
    a.at(18, {"wheel_a": {"s": 1.3}, "wheel_b": {"s": 1.3}, "core": {"s": 1.6}})
    a.at(24, {"core": {"s": 2.0}}, "in")
    a.at(60, {"wheel_a": {"s": 1.0}, "wheel_b": {"s": 1.0}, "core": {"s": 1.0}})
    out.append(a.overlay("wheel_c", "r", [0, f"{A} * 500", 0]))
    # mark (40, 14): the Eyes of the Throne single out a player
    a = Act("mark", 40, [14])
    a.at(10, {"wheel_a": {"s": 0.9}, "wheel_b": {"s": 0.9}})
    a.at(14, {"wheel_a": {"s": 1.25}, "wheel_b": {"s": 1.25}, "core": {"s": 1.3}}, "in")
    a.at(40, {"wheel_a": {"s": 1.0}, "wheel_b": {"s": 1.0}, "core": {"s": 1.0}})
    out.append(a)
    return out


def entity_cfg():
    return cfg(KEY, SCALE, bounds=(6, 6, 2.0))


if __name__ == "__main__":
    import sys
    from modelkit import render_preview, island_report, deflicker
    m = build(); m.paint(); print(m.stats(), island_report(m), deflicker(m))
    render_preview([m], f"{sys.argv[1]}/ophan.png", yaw=35, pitch=12, size=500, step=1)
