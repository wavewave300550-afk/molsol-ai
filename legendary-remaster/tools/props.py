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
    # the trunk sways slightly while standing; rise / fall / sink are acts (controller states)
    return {"idle": loop({"trunk": {"r": [sn(60, amp=1.2, clock=LT), 0, sn(45, amp=1.2, clock=LT)]}})}


def world_tree_acts():
    from animkit import Act
    rise = Act("rise", 20)                                   # act 1: bursts up out of the ground
    rise.at(0, {"root": {"p": (0, -130, 0)}}).at(14, {"root": {"p": (0, 4, 0)}}, "out").at(20, {"root": {"p": (0, 0, 0)}})
    fall = Act("fall", 22)                                   # act 2: topples forward, accelerating
    fall.at(0, {"trunk": {"r": (0, 0, 0)}}).at(18, {"trunk": {"r": (90, 0, 0)}}, "in").at(20, {"trunk": {"r": (84, 0, 0)}}, "out")
    fall.at(22, {"trunk": {"r": (90, 0, 0)}}, "in")
    sink = Act("sink", 30)                                   # act 3: crumbles into the earth
    sink.at(0, {"trunk": {"r": (90, 0, 0)}, "root": {"p": (0, 0, 0), "s": 1.0}})
    sink.at(30, {"trunk": {"r": (90, 0, 0)}, "root": {"p": (0, -12, 0), "s": 0.02}}, "in")
    return [rise, fall, sink]


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
WT.acts = world_tree_acts
WT.entity_cfg = lambda: {**_prop_cfg("world_tree", 2.5, (40, 40, 10)), "animate": ["idle", "ctrl_act"]}
ENTITIES.append(WT)

# =========================================================================== 2.0.5 set-pieces
# Decorative 3D set-pieces that appear inside skills and ultimates (no collision, no damage).

def _hold(name, ticks, *frames):
    from animkit import Act
    a = Act(name, ticks)
    for f in frames:
        a.at(*f)
    return a


# --------------------------------------------------------------------------- spirit maw (Taotie ultimate)
def spirit_maw_build():
    """A colossal spectral taotie mask whose jaws gape over the arena and snap shut."""
    m = Model("geometry.legends.spirit_maw", seed=91, density=2)
    BR = L.bronze("plate", lei=True, cell=6.0)
    DK = L.bronze("dark")
    TOOTH = L.glow("fff6d8", "ff7a20", "v")
    EYE = L.glow("ffffff", "ff5a10", "r")
    root = m.bone("root", (0, 0, 0))
    mask = m.bone("mask", (0, 30, 6), "root")
    upper = m.bone("upper", (0, 26, 8), "mask")            # hinge at the back of the jaws
    lower = m.bone("lower", (0, 22, 8), "root")
    # the mask: brow plate with leiwen, curled horns and burning eyes
    bevel(mask, (-18, 32, -10), (36, 16, 6), BR, b=1.0)
    bevel(mask, (-12, 46, -9), (24, 6, 5), DK, b=0.8)
    for sx in (-1, 1):
        orb(mask, (sx * 9, 39, -10.5), 3.4, EYE, glow=True)
        ring(mask, (sx * 9, 39, -10.2), 4.6, 12, BR, thickness=1.2, width=1.4, plane="xy")
        pts = [(sx * 16, 44, -7), (sx * 26, 52, -4), (sx * 32, 46, 0), (sx * 28, 38, 2), (sx * 23, 42, 2)]
        tube(mask, catmull(pts, 3), 5.5, 1.6, L.horn_bronze(), overlap=0.8)
    # upper jaw: a horseshoe of bronze with fangs pointing down
    ring(upper, (0, 28, 2), 16, 14, BR, thickness=3.2, width=5.0, plane="xz", arc=(190, 350))
    for i in range(9):
        a = math.radians(196 + i * 148 / 8)
        x, z = 16 * math.cos(a), 2 + 16 * math.sin(a)
        big = i in (1, 7)
        spike(upper, (x, 27, z), (x * 0.94, 27 - (16 if big else 11), z * 0.94), 4.2 if big else 3.0, TOOTH, steps=3, glow=True)
    # lower jaw
    ring(lower, (0, 20, 2), 15, 14, DK, thickness=3.0, width=4.0, plane="xz", arc=(190, 350))
    for i in range(8):
        a = math.radians(200 + i * 140 / 7)
        x, z = 15 * math.cos(a), 2 + 15 * math.sin(a)
        big = i in (0, 7)
        spike(lower, (x, 21, z), (x * 0.94, 21 + (14 if big else 9), z * 0.94), 3.8 if big else 2.8, TOOTH, steps=3, glow=True)
    return m


def spirit_maw_loops():
    return {"idle": loop({"mask": {"p": [0, sn(120, amp=0.8, clock=LT), 0]}})}


def spirit_maw_acts():
    gape = _hold("gape", 24,
                 (0, {"root": {"s": 0.05, "p": (0, -10, 0)}, "upper": {"r": (0, 0, 0)}, "lower": {"r": (0, 0, 0)}}),
                 (16, {"root": {"s": 1.05, "p": (0, 1, 0)}, "upper": {"r": (-38, 0, 0)}, "lower": {"r": (30, 0, 0)}}, "out"),
                 (24, {"root": {"s": 1.0, "p": (0, 0, 0)}, "upper": {"r": (-34, 0, 0)}, "lower": {"r": (27, 0, 0)}}))
    snap = _hold("snap", 10,
                 (0, {"root": {"s": 1.0}, "upper": {"r": (-40, 0, 0)}, "lower": {"r": (32, 0, 0)}}),
                 (5, {"root": {"s": 1.08}, "upper": {"r": (4, 0, 0)}, "lower": {"r": (-3, 0, 0)}}, "in"),
                 (10, {"root": {"s": 1.0}, "upper": {"r": (0, 0, 0)}, "lower": {"r": (0, 0, 0)}}, "out"))
    fade = _hold("fade", 20,
                 (0, {"root": {"s": 1.0, "p": (0, 0, 0)}}),
                 (20, {"root": {"s": 0.02, "p": (0, 14, 0)}}, "in"))
    return [gape, snap, fade]


# --------------------------------------------------------------------------- runestone (Nidhogg)
def runestone_build():
    m = Model("geometry.legends.runestone", seed=92, density=3)
    ST = L.stone("6f746c", "3f4540")
    RUNE = L.glow("f0ffd0", "38e83a", "v")
    root = m.bone("root", (0, 0, 0))
    slab = m.bone("slab", (0, 0, 0), "root")
    bevel(slab, (-7, 0, -3), (14, 30, 6), ST, b=1.2)
    bevel(slab, (-5.5, 30, -2.6), (11, 8, 5.2), ST, b=1.2)
    bevel(slab, (-3.5, 38, -2.2), (7, 4, 4.4), ST, b=1.0)
    rng = __import__("random").Random(5)
    for face in (-3.15, 2.55):                               # runes carved on both faces
        y = 6
        while y < 36:
            x = rng.uniform(-3.5, 2.5)
            slab.add((x, y, face), (0.8, 5, 0.6), RUNE, glow=True)
            kind = rng.randrange(3)
            if kind == 0:
                strut(slab, (x + 0.4, y + 3.5, face + 0.3), (x + 2.8, y + 5, face + 0.3), 0.7, RUNE, glow=True, depth=0.6)
            elif kind == 1:
                strut(slab, (x + 0.4, y + 1.5, face + 0.3), (x + 2.6, y + 3.5, face + 0.3), 0.7, RUNE, glow=True, depth=0.6)
                strut(slab, (x + 0.4, y + 3.5, face + 0.3), (x + 2.6, y + 1.5, face + 0.3), 0.7, RUNE, glow=True, depth=0.6)
            else:
                strut(slab, (x + 0.4, y + 4.6, face + 0.3), (x - 1.8, y + 2.8, face + 0.3), 0.7, RUNE, glow=True, depth=0.6)
            y += 7.5
    for k in range(5):                                       # roots clutching the base
        a = k / 5 * 2 * math.pi + 0.3
        tube(slab, catmull([(math.cos(a) * 5, 9, math.sin(a) * 3), (math.cos(a) * 9, 3, math.sin(a) * 6), (math.cos(a) * 13, -1, math.sin(a) * 10)], 2),
             3.2, 1.0, L.root_horn(), overlap=0.8)
    return m


def runestone_loops():
    return {"idle": loop({"slab": {"p": [0, 0, 0]}})}


def runestone_acts():
    rise = _hold("rise", 16, (0, {"root": {"p": (0, -46, 0)}}), (11, {"root": {"p": (0, 3, 0)}}, "out"), (16, {"root": {"p": (0, 0, 0)}}))
    pulse = _hold("pulse", 10, (0, {"slab": {"s": 1.0}}), (4, {"slab": {"s": 1.06}}, "out"), (10, {"slab": {"s": 1.0}}))
    sink = _hold("sink", 24, (0, {"root": {"p": (0, 0, 0)}}), (24, {"root": {"p": (0, -46, 0)}}, "in"))
    return [rise, pulse, sink]


# --------------------------------------------------------------------------- golden lotus (Hanuman)
LOTUS_OUT, LOTUS_IN = 8, 8


def golden_lotus_build():
    m = Model("geometry.legends.golden_lotus", seed=93, density=2)
    OUT = L.thai_gold(gems=False)
    INN = L.glow("fff8e8", "ffb0c8", "v")
    root = m.bone("root", (0, 0, 0))
    pod = m.bone("pod", (0, 0, 0), "root")
    orb(pod, (0, 4, 0), 5.0, L.star_gold())
    for k in range(7):
        a = k / 7 * 2 * math.pi
        orb(pod, (math.cos(a) * 2.6, 7.8, math.sin(a) * 2.6), 0.8, L.glow("ffffff", "ffd040", "r"), glow=True)
    for i in range(LOTUS_OUT):
        b = m.bone(f"po{i}", (0, 2, 0), "root", rotation=(-58, i * 360 / LOTUS_OUT, 0))
        for t, (w, z0, z1) in enumerate(((9.0, -3, -12), (11.0, -12, -20), (7.0, -20, -25), (3.0, -25, -27))):
            b.add((-w / 2, 1.2 - t * 0.3, z1), (w, 1.0, z0 - z1), OUT)
    for i in range(LOTUS_IN):
        b = m.bone(f"pi{i}", (0, 3, 0), "root", rotation=(-72, (i + 0.5) * 360 / LOTUS_IN, 0))
        for t, (w, z0, z1) in enumerate(((7.0, -3, -10), (8.6, -10, -16), (5.0, -16, -20), (2.0, -20, -22))):
            b.add((-w / 2, 1.2 - t * 0.3, z1), (w, 0.8, z0 - z1), INN, glow=True)
    return m


def golden_lotus_loops():
    return {"idle": loop({"root": {"r": [0, f"{LT} * 12", 0]}})}


def golden_lotus_acts():
    def petals(o, i):
        d = {f"po{k}": {"r": (o, 0, 0)} for k in range(LOTUS_OUT)}
        d.update({f"pi{k}": {"r": (i, 0, 0)} for k in range(LOTUS_IN)})
        return d
    bloom = _hold("bloom", 30,
                  (0, {"root": {"s": 0.1}, **petals(0, 0)}),
                  (12, {"root": {"s": 1.0}}, "out"),
                  (26, {**petals(48, 36)}, "out"),
                  (30, {"root": {"s": 1.0}, **petals(44, 33)}))
    close = _hold("close", 20,
                  (0, {"root": {"s": 1.0, "p": (0, 0, 0)}, **petals(44, 33)}),
                  (12, {**petals(0, 0)}, "in"),
                  (20, {"root": {"s": 0.05, "p": (0, -4, 0)}, **petals(0, 0)}, "in"))
    return [bloom, close]


# --------------------------------------------------------------------------- sun halo (Alicorn)
def sun_halo_build():
    m = Model("geometry.legends.sun_halo", seed=94, density=2)
    G = L.star_gold()
    RAY = L.glow("ffffff", "ffc640", "v")
    root = m.bone("root", (0, 0, 0))
    outer = m.bone("outer", (0, 0, 0), "root")
    inner = m.bone("inner", (0, 0, 0), "root")
    core = m.bone("core", (0, 0, 0), "root")
    ring(outer, (0, 0, 0), 24, 28, G, thickness=1.6, width=1.6, plane="xy")
    ring(outer, (0, 0, 0), 27, 30, G, thickness=0.9, width=1.0, plane="xy")
    for k in range(16):
        a = math.radians(k * 22.5)
        r1 = 36 if k % 2 == 0 else 31
        spike(outer, (math.cos(a) * 25, math.sin(a) * 25, 0), (math.cos(a) * r1, math.sin(a) * r1, 0), 2.6 if k % 2 == 0 else 1.8, RAY, steps=3, glow=True)
    ring(inner, (0, 0, 0), 17, 24, G, thickness=1.4, width=1.4, plane="xy")
    for k in range(12):
        a = math.radians(k * 30 + 15)
        orb(inner, (math.cos(a) * 17, math.sin(a) * 17, 0), 1.3, RAY, glow=True)
    ring(inner, (0, 0, 0), 12, 20, G, thickness=0.8, width=1.0, plane="xy")
    for k in range(8):                                       # spokes tie the inner wheel together
        a = math.radians(k * 45)
        strut(inner, (math.cos(a) * 12, math.sin(a) * 12, 0), (math.cos(a) * 17, math.sin(a) * 17, 0), 0.7, G)
    for t in (0, 1):
        ring(core, (0, 0, 0.6 * t), 6 + t * 2.5, 16, RAY, thickness=4.5, width=1.0, plane="xy", glow=True)
    orb(core, (0, 0, 0), 4.2, L.glow("ffffff", "ffe9a0", "r"), glow=True)
    return m


def sun_halo_loops():
    return {"idle": loop({"outer": {"r": [0, 0, f"{LT} * 18"]}, "inner": {"r": [0, 0, f"-{LT} * 32"]},
                          "core": {"s": f"1.0 + math.sin({LT} * 400) * 0.06"}})}


def sun_halo_acts():
    rise = _hold("rise", 30, (0, {"root": {"s": 0.05, "p": (0, -16, 0)}}), (22, {"root": {"s": 1.06, "p": (0, 1, 0)}}, "out"),
                 (30, {"root": {"s": 1.0, "p": (0, 0, 0)}}))
    flare = _hold("flare", 12, (0, {"root": {"s": 1.0}}), (4, {"root": {"s": 1.25}}, "out"), (12, {"root": {"s": 1.1}}))
    fade = _hold("fade", 16, (0, {"root": {"s": 1.1}}), (16, {"root": {"s": 0.02}}, "in"))
    return [rise, flare, fade]


# --------------------------------------------------------------------------- kagura suzu (Tenko)
def suzu_bell_build():
    m = Model("geometry.legends.suzu_bell", seed=95, density=3)
    GD = L.star_gold()
    root = m.bone("root", (0, 0, 0))
    bells = m.bone("bells", (0, 0, 0), "root")
    bevel(bells, (-1.2, -12, -1.2), (2.4, 30, 2.4), L.vermilion(), b=0.4)        # handle
    bevel(bells, (-1.8, -14, -1.8), (3.6, 3, 3.6), GD, b=0.5)
    for tier, (y, r, n) in enumerate(((10, 9.0, 7), (16.5, 6.4, 5), (22, 3.6, 3))):
        ring(bells, (0, y, 0), r, 12, GD, thickness=0.6, width=0.8, plane="xz")
        for k in range(4):                                   # wire arms from the handle to the ring
            a4 = k / 4 * 2 * math.pi + tier * 0.4
            strut(bells, (math.cos(a4) * 0.8, y - 2.5, math.sin(a4) * 0.8), (math.cos(a4) * r, y, math.sin(a4) * r), 0.6, GD)
        for k in range(n):
            a = k / n * 2 * math.pi + tier * 0.4
            orb(bells, (math.cos(a) * r, y - 2.2, math.sin(a) * r), 2.3, GD)
            bells.add((math.cos(a) * r - 0.4, y - 4.8, math.sin(a) * r - 0.4), (0.8, 0.8, 0.8), L.solid("2a1a08", 0.02))
    orb(bells, (0, 25.5, 0), 2.2, GD)
    strut(bells, (0, 17, 0), (0, 24, 0), 1.2, GD)
    cols = ["d8263a", "f2c84b", "3a9a5a", "f4f0e6", "7a3aa8"]
    for k, c in enumerate(cols):
        a = k / 5 * 2 * math.pi
        rb = m.bone(f"rib{k}", (0, -14, 0), "root", rotation=(round(14 * math.sin(a), 2), 0, round(14 * math.cos(a), 2)))
        x, z = math.cos(a) * 1.4, math.sin(a) * 1.4
        rb.add((x - 1.1, -40, z - 0.2), (2.2, 27, 0.4), L.solid(c, 0.03))
    return m


def suzu_bell_loops():
    rib = {f"rib{k}": {"r": [sn(110 + k * 13, amp=7, clock=LT, ph=k * 60), 0, sn(90 + k * 11, amp=9, clock=LT, ph=k * 45)]} for k in range(5)}
    return {"idle": loop({**grow_in(), "root": {"p": [0, sn(80, amp=1.2, clock=LT), 0], "s": f"math.min(1.0, {LT} * 5)"}, **rib})}


def suzu_bell_acts():
    ring_ = _hold("ring", 12, (0, {"bells": {"r": (0, 0, 0)}}), (2, {"bells": {"r": (0, 0, 16)}}, "out"), (5, {"bells": {"r": (0, 0, -12)}}, "io"),
                  (8, {"bells": {"r": (0, 0, 7)}}, "io"), (12, {"bells": {"r": (0, 0, 0)}}, "io"))
    fade = _hold("fade", 12, (0, {"root": {"s": 1.0}}), (12, {"root": {"s": 0.02}}, "in"))
    return [ring_, fade]


# --------------------------------------------------------------------------- herald trumpet (The Word)
def herald_trumpet_build():
    m = Model("geometry.legends.herald_trumpet", seed=96, density=3)
    GD = L.divine_gold(glyphs=False)
    root = m.bone("root", (0, 0, 0))
    horn = m.bone("horn", (0, 0, 6), "root", rotation=(-32, 0, 0))
    tube(horn, [(0, 0, 14), (0, 0, 0), (0, 0, -14)], 2.2, 1.6, GD, overlap=0.6)
    for k, (z, r) in enumerate(((-15, 2.4), (-17.5, 3.4), (-19.5, 4.6), (-21, 6.0))):
        ring(horn, (0, 0, z), r, 14, GD, thickness=1.0, width=2.2, plane="xy")
    ring(horn, (0, 0, -21.6), 5.4, 16, L.glow("ffffff", "ffd860", "r"), thickness=2.2, width=0.6, plane="xy", glow=True)
    orb(horn, (0, 0, 15), 1.6, GD)
    for z in (-4, 6):
        ring(horn, (0, 0, z), 2.5, 10, L.star_gold(), thickness=0.8, width=1.2, plane="xy")
    ban = m.bone("banner", (0, -2, -2), "horn")
    ban.add((-5, -16, -2.3), (10, 14, 0.5), L.parchment())
    orb(ban, (0, -9, -2.6), 1.8, L.wax_seal())
    for x in (-5, 5):
        strut(ban, (x * 0.9, -2, -2), (x * 0.4, 0, -2), 0.4, GD)
    return m


def herald_trumpet_loops():
    return {"idle": loop({**grow_in(), "root": {"p": [0, sn(70, amp=0.8, clock=LT), 0], "s": f"math.min(1.0, {LT} * 5)"},
                          "banner": {"r": [sn(90, amp=8, clock=LT), 0, sn(70, amp=4, clock=LT)]}})}


def herald_trumpet_acts():
    blast = _hold("blast", 14, (0, {"horn": {"r": (0, 0, 0), "p": (0, 0, 0)}}), (3, {"horn": {"r": (-10, 0, 0), "p": (0, 0, 3)}}, "out"),
                  (14, {"horn": {"r": (0, 0, 0), "p": (0, 0, 0)}}, "io"))
    fade = _hold("fade", 10, (0, {"root": {"s": 1.0}}), (10, {"root": {"s": 0.02}}, "in"))
    return [blast, fade]


# --------------------------------------------------------------------------- debris chunk (heavy impacts)
def debris_build():
    m = Model("geometry.legends.debris", seed=97, density=3)
    root = m.bone("root", (0, 0, 0))
    rock = m.bone("rock", (0, 4, 0), "root")
    ST = L.stone("7d7468", "4d463e")
    rock.add((-4, 0.5, -3.5), (8, 7, 7), ST)
    rock.add((-3, 1.5, -4.5), (6, 5, 9), ST, pivot=(0, 4, 0), rotation=(18, 25, 0))
    rock.add((-3.5, 2, -3), (7, 6, 6), ST, pivot=(0, 4, 0), rotation=(0, 40, 22))
    rock.add((-1.8, 6.6, -1.6), (3.6, 1.2, 3.2), L.stone("8f8a6c", "5c5a44"))
    return m


def debris_loops():
    return {"idle": loop({"rock": {"r": [f"{LT} * 420", f"{LT} * 260", f"{LT} * 170"]}})}


def _set(key, build, loops, acts, scale, bounds):
    ns = _ns(key, build, loops, scale, bounds)
    if acts:
        ns.acts = acts
        ns.entity_cfg = lambda: {**_prop_cfg(key, scale, bounds), "animate": ["idle", "ctrl_act"]}
    return ns


SETPIECES = [
    _set("spirit_maw", spirit_maw_build, spirit_maw_loops, spirit_maw_acts, 3.0, (14, 14, 4)),
    _set("runestone", runestone_build, runestone_loops, runestone_acts, 1.7, (3, 6, 2)),
    _set("golden_lotus", golden_lotus_build, golden_lotus_loops, golden_lotus_acts, 2.4, (8, 5, 1)),
    _set("sun_halo", sun_halo_build, sun_halo_loops, sun_halo_acts, 2.6, (14, 14, 0)),
    _set("suzu_bell", suzu_bell_build, suzu_bell_loops, suzu_bell_acts, 2.2, (4, 9, 0)),
    _set("herald_trumpet", herald_trumpet_build, herald_trumpet_loops, herald_trumpet_acts, 1.7, (4, 4, 0)),
    _set("debris", debris_build, debris_loops, None, 1.6, (2, 2, 0)),
]
ENTITIES.extend(SETPIECES)
