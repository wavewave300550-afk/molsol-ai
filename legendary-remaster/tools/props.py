"""
Remastered and new prop entities (script-driven models: no AI, no collision).

Remade:  crescent (Hanuman's moon blade), eden_sword (the flaming sword of Eden), tail_spike (fox tail),
         coal (the live coal), foxfire, light_spear, star_lance
New:     world_tree (Nidhogg's ultimate: the World-Tree falls), lantern (Tenko's fox-wedding procession),
         aurora_steed (Alicorn's ultimate: spectral steeds - reuses the Alicorn geometry)
`legends:act` drives prop states (0 idle, 1.. see each prop).
"""
import math
import os
from types import SimpleNamespace

from modelkit import Model
from shapes import bevel, orb, ring, spike, strut
from shapes2 import catmull, feather, tube
import lmat as L
from animkit import A, T, loop, sn

ACT = "query.property('legends:act')"
LT = "query.life_time"


def _prop_cfg(key, scale, bounds, animate=None, material="entity_alphatest"):
    return {"scale": scale, "textures": {"default": f"textures/entity/legends/{key}"}, "pre": [], "prop": True,
            "animate": animate or ["idle"], "visibility": [], "bounds": bounds, "overlay": False, "material": material}


def grow_in(bone="root"):
    return {bone: {"s": f"math.min(1.0, {LT} * 5)"}}


# --------------------------------------------------------------------------- crescent
def crescent_build():
    m = Model("geometry.legends.crescent", seed=81, density=3)
    root = m.bone("root", (0, 0, 0))
    blade = m.bone("blade", (0, 2, 0), "root")
    pts = [(x, 2.0, -6.0 * (1 - (x / 30.0) ** 2)) for x in range(-30, 31, 5)]
    half = len(pts) // 2
    left, right = pts[:half + 1][::-1], pts[half:]
    for side in (left, right):
        tube(blade, side, 5.2, 0.8, L.glow("ffffff", "a8c0ff", "u"), glow=True, overlap=0.5)
        tube(blade, side, 2.6, 0.4, L.solid("e8eeff", 0.03), overlap=0.5)
    return m


def crescent_loops():
    return {"idle": loop({**grow_in(), "blade": {"r": [0, 0, sn(900, amp=2, clock=LT)]}})}


# --------------------------------------------------------------------------- eden sword
def eden_build():
    m = Model("geometry.legends.eden_sword", seed=82, density=3)
    GD = L.star_gold()
    root = m.bone("root", (0, 0, 0))
    hilt = m.bone("hilt", (0, 10, 0), "root")
    hilt.add((-0.8, 6, -0.8), (1.6, 7, 1.6), L.solid("6b1e12", 0.04))
    orb(hilt, (0, 13.6, 0), 1.3, GD)
    bevel(hilt, (-4.5, 5.0, -1.0), (9, 1.6, 2.0), GD, b=0.4)
    for sx in (-1, 1):                                                   # cherub-wing guard
        for k in range(3):
            feather(hilt, (sx * 4.0, 5.8, 0), 4 - k, 1.4, sx * -90 + (k - 1) * sx * 18, -30 - k * 12, GD, thick=0.5)
    blade = m.bone("blade", (0, 5, 0), "root")
    bpts = catmull([(0, 5, 0), (0.9, 12, 0), (-0.8, 20, 0), (0.7, 28, 0), (0, 34, 0)], 2)
    tube(blade, bpts, 3.4, 0.8, L.glow("fffbe0", "ff6a10", "vt"), glow=True, overlap=0.4)
    tube(blade, bpts, 1.4, 0.4, L.glow("ffffff", "fff0b0", "u"), glow=True, overlap=0.4)
    flames = m.bone("flames", (0, 18, 0), "blade")
    for k in range(5):
        y = 9 + k * 5.4
        spike(flames, (0, y, 0), ((1 if k % 2 else -1) * 4.5, y + 4, 0), 2.2, L.glow("fff3b0", "ff4a10", "vt"), glow=True, steps=2)
    return m


def eden_loops():
    return {"idle": loop({**grow_in(), "flames": {"r": [0, f"{LT} * 160", 0]}, "blade": {"s": f"1 + {sn(700, amp=0.04, clock=LT)}"},
                          "hilt": {"p": [0, f"{ACT} == 1 ? math.max(0, 6 - {LT} * 12) : 0", 0]}})}


# --------------------------------------------------------------------------- tail spike
def tail_spike_build():
    m = Model("geometry.legends.tail_spike", seed=83, density=3)
    root = m.bone("root", (0, 0, 0))
    t = m.bone("tail", (0, 0, 0), "root")
    pts = catmull([(0, -2, 0), (1.5, 8, 0.5), (-1.0, 18, 0), (0.5, 27, -0.5)], 3)
    tube(t, pts, 6.4, 2.0, L.fox_fur(), overlap=1.0)
    tip = m.bone("tip", (0.5, 27, -0.5), "tail")
    tube(tip, [(0.5, 24.5, -0.5), (0.4, 33, -0.6)], 3.6, 1.0, L.glow("ffffff", "4aa8ff", "vb"), glow=True, overlap=0.3)
    for k in range(5):
        ang = k / 5 * 2 * math.pi
        spike(t, (math.cos(ang) * 2, 0, math.sin(ang) * 2), (math.cos(ang) * 6, -1, math.sin(ang) * 6), 2.2, L.stone("6b5a4a", "3e3328"), steps=2)
    return m


def tail_spike_loops():
    return {"idle": loop({"root": {"p": [0, f"-30 * math.max(0, 1 - {LT} * 7)", 0]}, "tail": {"r": [sn(300, amp=3, clock=LT), 0, sn(240, amp=3, clock=LT)]}})}


# --------------------------------------------------------------------------- small glowing projectiles
def coal_build():
    m = Model("geometry.legends.coal", seed=84, density=4)
    root = m.bone("root", (0, 2, 0))
    orb(root, (0, 2.5, 0), 2.6, L.glow("fff0c0", "ff3a10", "r"), glow=True)
    bevel(root, (-1.8, 1.0, -1.6), (3.6, 3.0, 3.2), L.stone("3a0a04", "180402"), b=0.6)
    return m


def foxfire_build():
    m = Model("geometry.legends.foxfire", seed=85, density=4)
    root = m.bone("root", (0, 2, 0))
    orb(root, (0, 3, 0), 2.6, L.glow("ffffff", "3a8cff", "r"), glow=True)
    spike(root, (0, 4.5, 0), (0, 10, 0), 3.2, L.glow("e8f4ff", "2a6cff", "vt"), glow=True, steps=3)
    return m


def spear_build(ident, core, edge, length=26):
    def b():
        m = Model(ident, seed=86, density=3)
        root = m.bone("root", (0, 0, 0))
        strut(root, (0, 0, length * 0.45), (0, 0, -length * 0.4), 1.2, L.glow(core, edge, "u"), glow=True, depth=1.2)
        spike(root, (0, 0, -length * 0.4), (0, 0, -length * 0.62), 3.2, L.glow("ffffff", edge, "u"), glow=True, steps=3)
        for k in range(3):
            feather(root, (0, 0, length * 0.3 + k * 2), 3, 2.6, 180, 0, L.glow(core, edge, "u"), thick=0.4, glow=True, roll=k * 60)
        return m
    return b


def spin_loops(axis="y", speed=360):
    r = [0, f"{LT} * {speed}", 0] if axis == "y" else [0, 0, f"{LT} * {speed}"]
    return lambda: {"idle": loop({**grow_in(), "root": {"r": r, "s": f"math.min(1.0, {LT} * 5)"}})}


# --------------------------------------------------------------------------- world tree (Nidhogg ultimate)
def world_tree_build():
    m = Model("geometry.legends.world_tree", seed=87, density=1)
    BARK = L.root_horn()
    VEN = L.glow("f0ffc0", "38e83a", "u")
    root = m.bone("root", (0, 0, 0))
    base = m.bone("trunk", (0, 0, 0), "root")                # pivot at the base: falls forward (-z)
    pts = [(0, 0, 0), (1.5, 30, 0.5), (-1.0, 62, 0), (0.8, 94, -0.6), (0, 124, 0)]
    tube(base, catmull(pts, 2), 22, 11, BARK, overlap=2.0, soft=False)
    for k, (y, ang, ln) in enumerate(((52, 30, 26), (74, 150, 30), (96, 260, 22), (112, 60, 18))):
        a = math.radians(ang)
        p0 = (0, y, 0)
        p1 = (math.cos(a) * ln * 0.6, y + ln * 0.5, math.sin(a) * ln * 0.6)
        p2 = (math.cos(a) * ln, y + ln * 0.75, math.sin(a) * ln)
        tube(base, [p0, p1, p2], 7, 2.5, BARK, overlap=1.0, soft=False)
    for k in range(6):                                          # roots at the base
        a = k / 6 * 2 * math.pi
        tube(base, catmull([(math.cos(a) * 6, 4, math.sin(a) * 6), (math.cos(a) * 14, 0, math.sin(a) * 14), (math.cos(a) * 22, -3, math.sin(a) * 22)], 2), 7, 2.5, BARK, overlap=1.0)
    for k in range(5):                                          # venom veins (glow)
        y = 12 + k * 22
        hw = 11.0 - 5.5 * (y + 7) / 124.0
        x0 = -hw - 0.2 if k % 2 == 0 else hw - 0.4
        base.add((x0, y, -1.0), (0.6, 14, 2.0), VEN, glow=True)
    return m


def world_tree_loops():
    # act 1: rises (0.6 s) - act 2: falls forward (0.9 s, ease-in) - act 3: crumbles into the ground
    rise = f"math.min(1, {LT} * 1.7)"
    fall = f"({ACT} >= 2 ? math.min(90, math.pow(math.max(0, variable.t2), 2) * 110) : 0)"
    return {"idle": loop({
        "root": {"p": [0, f"-130 * (1 - {rise})", 0], "s": f"{ACT} == 3 ? math.max(0.01, 1 - variable.t3 * 0.9) : 1"},
        "trunk": {"r": [fall, 0, 0]},
    })}


# --------------------------------------------------------------------------- lantern (Tenko procession)
def lantern_build():
    m = Model("geometry.legends.lantern", seed=88, density=3)
    root = m.bone("root", (0, 0, 0))
    lan = m.bone("lantern", (0, 14, 0), "root")
    for k in range(5):
        y = 6 + k * 3.2
        r = 4.2 + math.sin((k + 0.5) / 5 * math.pi) * 1.6
        bevel(lan, (-r, y, -r), (2 * r, 3.0, 2 * r), L.vermilion() if k % 2 == 0 else L.solid("f4eee0", 0.03), b=0.6)
    orb(lan, (0, 13.5, 0), 4.0, L.glow("fff0c0", "ff8a20", "r"), glow=True)
    for y in (5.0, 21.6):
        bevel(lan, (-3.0, y, -3.0), (6, 1.6, 6), L.star_gold(), b=0.4)
    lan.add((-0.4, 23.2, -0.4), (0.8, 4, 0.8), L.solid("2a1a0a", 0.03))
    return m


def lantern_loops():
    return {"idle": loop({**grow_in(), "lantern": {"r": [sn(160, amp=6, clock=LT), 0, sn(130, amp=6, clock=LT)], "p": [0, sn(200, amp=0.6, clock=LT), 0]}})}


# --------------------------------------------------------------------------- registry
def _ns(key, build, loops, scale, bounds, material="entity_alphatest"):
    return SimpleNamespace(KEY=key, build=build, loops=loops, VARIANTS={"default": "default"},
                           entity_cfg=lambda: _prop_cfg(key, scale, bounds, material=material))


ENTITIES = [
    _ns("crescent", crescent_build, crescent_loops, 2.0, (9, 3, 0.5)),
    _ns("eden_sword", eden_build, eden_loops, 1.6, (3, 5, 2.0)),
    _ns("tail_spike", tail_spike_build, tail_spike_loops, 1.4, (3, 4, 1.5)),
    _ns("coal", coal_build, spin_loops("y", 240), 1.3, (1, 1, 0.3)),
    _ns("foxfire", foxfire_build, spin_loops("y", 180), 1.3, (1, 1.5, 0.4)),
    _ns("light_spear", spear_build("geometry.legends.light_spear", "fffbe0", "ffc640"), spin_loops("z", 720), 1.2, (2, 2, 0)),
    _ns("star_lance", spear_build("geometry.legends.star_lance", "e8f8ff", "4ab0ff"), spin_loops("z", 720), 1.2, (2, 2, 0)),
    _ns("lantern", lantern_build, lantern_loops, 1.3, (2, 3, 1.0)),
]
WT = _ns("world_tree", world_tree_build, world_tree_loops, 2.5, (40, 40, 10))
WT.entity_cfg = lambda: {**_prop_cfg("world_tree", 2.5, (40, 40, 10)), "pre": [
    "variable.t2 = query.property('legends:act') >= 2 ? (variable.t2 ?? 0) + query.delta_time : 0;",
    "variable.t3 = query.property('legends:act') == 3 ? (variable.t3 ?? 0) + query.delta_time : 0;"]}
ENTITIES.append(WT)
