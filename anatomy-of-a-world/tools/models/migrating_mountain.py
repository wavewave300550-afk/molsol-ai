"""
Boss 001 - THE MIGRATING MOUNTAIN: entity models and animations.

  anatomy:mm_root_leg        Anchorage Root / Mantle Musculature legs (12 around the rim)
  anatomy:mm_resonance_node  the three Resonance Nodes (crystal in a rock socket)
  anatomy:mm_lithic_heart    the Lithic Heart core (crystal, iris plates, gyroscope rings, radial spokes)
  anatomy:mm_strata_slab     Geological Shedding projectile (a slab of living strata)
  anatomy:mm_petal           shell petal of The Great Unfolding (Phase 2 crown)
  anatomy:mm_strata_plate    Inverted Strata flipping plate (terrain plate / rib plate variants)

Colours follow the concept sheet: pale stratified grey rock, maroon lithic
musculature with red-orange mineral circulation, amethyst-purple heart.
"""
from __future__ import annotations

import math
import os
import sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(__file__))
from kit import (Model, bake_animation, ease_in, ease_in_out, ease_out_back, m_crystal, m_glow, m_grass_side,  # noqa: E402
                 m_grass_top, m_leaves, m_muscle, m_rock, m_solid, seg)

ROCK = m_rock("#8c8c89", "#606164", "#b9b9b3", band_period=9)
ROCK_MOSS = m_rock("#8c8c89", "#606164", "#b9b9b3", band_period=9, moss=0.35)
ROCK_MOSSY = m_rock("#8c8c89", "#606164", "#b9b9b3", band_period=9, moss=0.6)
ROCK_DARK = m_rock("#6f6f70", "#4c4c50", "#9a9a98", band_period=7)
MUSCLE = m_muscle("#6b262b", "#3c1216", "#9b4040", axis="v")
MUSCLE_U = m_muscle("#6b262b", "#3c1216", "#9b4040", axis="u")
MUSCLE_VEINS = m_muscle("#6b262b", "#3c1216", "#9b4040", axis="v", glow_veins=1.0)
VEIN = m_glow("#ff5a1f", "#ffc070", 30)
VEIN_SOFT = m_glow("#d8401c", "#ff9a4a", 90)
CRYSTAL = m_crystal("#9160e0", "#4a2890", "#f2dcff", alpha=120)
CRYSTAL_BRIGHT = m_crystal("#b98cff", "#6a3cc0", "#ffffff", alpha=40)
GRASS = m_grass_top("#5f9b3b", "#3f6d29", "#8cc35a")
GRASS_SIDE = m_grass_side(ROCK, "#5f9b3b", 2)
LEAVES = m_leaves("#355f2c", "#223f1d", "#4f8040")
BARK = m_solid("#4a3420")
DIRT = m_solid("#6b4a33")
OBSIDIAN = m_solid("#2a1240", 200)


def ring(bone, radius: float, y: float, segments: int, seg_len: float, thick: float, height: float, mat, density=0.75,
         axis: str = "y", phase: float = 0.0, teeth: float = 0.0, tooth_mat=None):
    """A ring of cubes around the bone pivot. axis 'y' = horizontal ring, 'x' = vertical ring facing Z."""
    px, py, pz = bone.pivot
    for k in range(segments):
        a = 360.0 * k / segments + phase
        if axis == "y":
            origin = (px - seg_len / 2, y - height / 2, pz + radius - thick / 2)
            size = (seg_len, height, thick)
            rot = (0, a, 0)
        elif axis == "x":
            # vertical ring in the Y-Z plane (rotates about X)
            origin = (px - height / 2, y + radius - thick / 2, pz - seg_len / 2)
            size = (height, thick, seg_len)
            rot = (a, 0, 0)
        else:  # 'z': vertical ring in the X-Y plane
            origin = (px - seg_len / 2, y + radius - thick / 2, pz - height / 2)
            size = (seg_len, thick, height)
            rot = (0, 0, a)
        bone.cube(origin, size, mat, density, rotation=rot, pivot=(px, y, pz))
        if teeth and k % 2 == 0:
            if axis == "y":
                o2 = (px - seg_len / 4, y - height / 2 - 1, pz + radius + thick / 2 - 1)
                s2 = (seg_len / 2, height + 2, teeth)
            elif axis == "x":
                o2 = (px - height / 2 - 1, y + radius + thick / 2 - 1, pz - seg_len / 4)
                s2 = (height + 2, teeth, seg_len / 2)
            else:
                o2 = (px - seg_len / 4, y + radius + thick / 2 - 1, pz - height / 2 - 1)
                s2 = (seg_len / 2, teeth, height + 2)
            bone.cube(o2, s2, tooth_mat or mat, density, rotation=rot, pivot=(px, y, pz))


# ============================================================================ LEG
LEG = {
    "upper_len": 160.0,
    "mid_len": 120.0,
    "lower_len": 150.0,
    "rest": {"upper": 30.0, "knee": 25.0, "lower": 25.0, "foot": -80.0},
}


def build_leg() -> Model:
    """Anchorage Root: a massive root-limb of mantle musculature armoured with living strata."""
    m = Model("geometry.anatomy.mm_root_leg", seed=11, visible_bounds=(48, 48, (0, -10, 0)))
    L = LEG
    root = m.bone("root", (0, 0, 0))
    # shoulder mass that blends into the underside arches
    root.cube((-84, -56, -64), (168, 80, 120), MUSCLE_VEINS, 0.5)
    root.cube((-92, 4, -72), (184, 28, 132), ROCK_MOSS, 0.5)
    root.cube((-70, -76, -40), (140, 26, 84), MUSCLE, 0.5)

    z0 = -40.0
    up = m.bone("upper", (0, -12, z0), "root", (L["rest"]["upper"], 0, 0))
    ul = L["upper_len"]
    up.cube((-68, -64, z0 - ul), (136, 104, ul + 12), MUSCLE_VEINS, 0.5)
    up.cube((-74, -54, z0 - ul * 0.8), (148, 70, ul * 0.5), MUSCLE, 0.5)  # belly bulge
    up.cube((-76, 32, z0 - ul + 6), (152, 26, ul + 4), ROCK_MOSS, 0.5, faces={"up": ROCK_MOSSY})  # dorsal strata armour
    up.cube((-56, 56, z0 - ul * 0.7), (100, 14, ul * 0.55), ROCK_MOSS, 0.5, faces={"up": ROCK_MOSSY})
    up.cube((66, -36, z0 - ul + 8), (10, 60, ul * 0.7), ROCK, 0.5)
    up.cube((-76, -30, z0 - ul * 0.6), (10, 56, ul * 0.55), ROCK, 0.5)
    up.cube((64, -46, z0 - ul + 4), (5, 5, ul - 6), VEIN, 0.5)
    up.cube((-69, -20, z0 - ul + 4), (5, 5, ul - 6), VEIN, 0.5)
    up.cube((-3, -66, z0 - ul + 12), (6, 4, ul - 30), VEIN, 0.5)
    for (x, z, ln, r) in [(-34, -50, 30, (16, 0, 12)), (38, -100, 40, (-12, 0, -14)), (-10, -140, 24, (10, 0, 16))]:
        up.cube((x - 11, -64 - ln, z0 + z - 11), (22, ln, 22), MUSCLE, 0.5, rotation=r, pivot=(x, -64, z0 + z))
        up.cube((x - 8, -64 - ln - 16, z0 + z - 8), (16, 18, 16), ROCK_DARK, 0.5, rotation=r, pivot=(x, -64, z0 + z))

    kz = z0 - ul
    mid = m.bone("knee", (0, -12, kz), "upper", (L["rest"]["knee"], 0, 0))
    ml = L["mid_len"]
    mid.cube((-58, -58, kz - ml), (116, 96, ml + 10), MUSCLE_VEINS, 0.5)
    mid.cube((-64, 24, kz - ml + 4), (128, 26, ml), ROCK_MOSS, 0.5, faces={"up": ROCK_MOSSY})
    mid.cube((-66, -40, kz - ml * 0.7), (132, 50, ml * 0.4), ROCK_DARK, 0.5)
    mid.cube((56, -30, kz - ml + 6), (5, 5, ml - 8), VEIN, 0.5)
    mid.cube((-61, -10, kz - ml + 6), (5, 5, ml - 8), VEIN, 0.5)

    lz = kz - ml
    lower = m.bone("lower", (0, -12, lz), "knee", (L["rest"]["lower"], 0, 0))
    ll = L["lower_len"]
    lower.cube((-46, -52, lz - ll), (92, 84, ll + 10), ROCK_DARK, 0.5)
    lower.cube((-52, -40, lz - ll * 0.5), (104, 60, ll * 0.5), MUSCLE_VEINS, 0.5)
    lower.cube((-50, 20, lz - ll + 6), (100, 22, ll * 0.7), ROCK, 0.5)
    lower.cube((-49, -30, lz - ll * 0.95), (5, 5, ll * 0.85), VEIN, 0.5)
    lower.cube((44, -12, lz - ll * 0.95), (5, 5, ll * 0.85), VEIN, 0.5)

    fz = lz - ll
    foot = m.bone("foot", (0, -12, fz), "lower", (L["rest"]["foot"], 0, 0))
    foot.locators["foot"] = (0.0, -56.0, fz - 18)
    foot.cube((-62, -52, fz - 60), (124, 56, 84), ROCK_DARK, 0.5)
    foot.cube((-52, -62, fz - 52), (104, 12, 68), MUSCLE, 0.5)
    toes = [(-70, -1.0), (-36, -0.55), (0, 0.0), (36, 0.55), (70, 1.0), (180, 0.0)]
    for i, (yaw, side) in enumerate(toes):
        back = yaw == 180
        tb = m.bone(f"toe{i}", (side * 40, -28, fz - 20 if not back else fz - 10), "foot", (16, yaw, 0))
        tz = fz - 20 if not back else fz - 10
        tl = 110 if not back else 70
        tb.cube((side * 40 - 16, -46, tz - tl), (32, 30, tl), ROCK, 0.5)
        tb.cube((side * 40 - 11, -52, tz - tl - 40), (22, 22, 46), ROCK_DARK, 0.5)
        tb.cube((side * 40 - 12, -32, tz - tl * 0.8), (24, 8, tl * 0.6), MUSCLE, 0.5)
        tb.cube((side * 40 - 1.5, -24, tz - tl * 0.9), (3, 2, tl * 0.7), VEIN, 0.5)
    m.build()
    return m


def leg_pose(rot: Dict[str, float], toe_curl: float = 0.0, yaw: float = 0.0) -> dict:
    p = {k: {"rotation": [v, 0, 0]} for k, v in rot.items()}
    if yaw:
        p["root"] = {"rotation": [0, yaw, 0]}
    for i in range(6):
        p[f"toe{i}"] = {"rotation": [toe_curl, 0, 0]}
    return p


def leg_animations() -> dict:
    anims = {}

    # Migration gait (loop 6 s): lift, swing forward, plant, push back. Offsets per leg come from
    # anim_time_update in the client entity, giving a peristaltic wave around the rim.
    def walk(t: float) -> dict:
        ph = (t / 6.0) * 2 * math.pi
        lift = max(0.0, math.sin(ph))  # swing phase
        swing = math.cos(ph)
        return leg_pose({
            "upper": -12 * lift + 3 * swing,
            "knee": 10 * lift - 2 * swing,
            "lower": 6 * lift,
            "foot": -8 * lift,
        }, toe_curl=10 * lift - 3, yaw=7 * swing)
    anims.update(bake_animation("animation.anatomy.mm_root_leg.walk", walk, 6.0, True, fps=8, extra={
        "anim_time_update": "q.life_time + v.phase",
        "sound_effects": {"3.0": {"effect": "step"}},
        "particle_effects": {"3.0": {"effect": "mist", "locator": "foot"}},
    }))

    def idle(t: float) -> dict:
        ph = (t / 4.0) * 2 * math.pi
        return leg_pose({"upper": 1.5 * math.sin(ph), "knee": -2 * math.sin(ph + 0.6), "lower": 1.2 * math.sin(ph + 1.2)}, toe_curl=3 * math.sin(ph + 2))
    anims.update(bake_animation("animation.anatomy.mm_root_leg.idle", idle, 4.0, True, fps=6))

    def stomp(t: float) -> dict:
        up = ease_in_out(seg(t, 0.0, 0.8))
        down = ease_in(seg(t, 0.8, 1.05))
        settle = ease_in_out(seg(t, 1.05, 1.8))
        k = up * (1 - down)
        shake = (math.sin(t * 60) * 2.5 * (1 - settle)) if t > 1.05 else 0
        return leg_pose({"upper": -26 * k + 4 * down * (1 - settle) + shake, "knee": 22 * k - 3 * down * (1 - settle), "lower": 10 * k, "foot": -14 * k},
                        toe_curl=18 * k - 6 * down * (1 - settle))
    anims.update(bake_animation("animation.anatomy.mm_root_leg.stomp", stomp, 1.8, False, fps=20))

    def flinch(t: float) -> dict:
        k = math.sin(seg(t, 0, 1.2) * math.pi)
        tremor = math.sin(t * 45) * 3 * k
        return leg_pose({"upper": -10 * k + tremor, "knee": 8 * k - tremor, "lower": 4 * k}, toe_curl=14 * k)
    anims.update(bake_animation("animation.anatomy.mm_root_leg.flinch", flinch, 1.2, False, fps=20))

    # Phase 2 pose: legs splay outward to brace the opened body.
    def splay(t: float) -> dict:
        return leg_pose({"upper": -18, "knee": -14, "lower": -6, "foot": 34}, toe_curl=-6)
    anims.update(bake_animation("animation.anatomy.mm_root_leg.splay", splay, 1.0, True, fps=2))

    def collapse(t: float) -> dict:
        k = ease_in(seg(t, 0, 3.5))
        return leg_pose({"upper": 30 * k, "knee": -30 * k, "lower": 20 * k, "foot": 40 * k}, toe_curl=-20 * k)
    anims.update(bake_animation("animation.anatomy.mm_root_leg.collapse", collapse, 4.0, "hold_on_last_frame", fps=10))
    return anims


# ============================================================================ RESONANCE NODE
def build_node() -> Model:
    m = Model("geometry.anatomy.mm_resonance_node", seed=21, visible_bounds=(5, 5, (0, 1.5, 0)))
    root = m.bone("root", (0, 0, 0))
    root.cube((-22, 0, -22), (44, 10, 44), ROCK_MOSS, 1.0)
    root.cube((-17, 10, -17), (34, 5, 34), ROCK, 1.0)
    root.cube((-14, 14, -14), (28, 3, 28), OBSIDIAN, 1.0)
    for k in range(6):
        a = k * 60 + 15
        root.cube((-4, 0, 18), (8, 7, 16), MUSCLE, 1.0, rotation=(0, a, 0), pivot=(0, 0, 0))
        root.cube((-1, 6, 18), (2, 2, 14), VEIN, 1.0, rotation=(0, a, 0), pivot=(0, 0, 0))
    core = m.bone("core", (0, 30, 0), "root")
    core.cube((-6, 16, -6), (12, 32, 12), CRYSTAL_BRIGHT, 1.0, rotation=(0, 45, 0), pivot=(0, 30, 0))
    core.cube((-3, 46, -3), (6, 8, 6), CRYSTAL_BRIGHT, 1.0, rotation=(0, 45, 0), pivot=(0, 30, 0))
    for k, (rx, rz, h) in enumerate([(22, 0, 22), (-20, 6, 18), (4, 24, 20), (-6, -22, 16), (14, 16, 12)]):
        core.cube((-3.5, 16, -3.5), (7, h, 7), CRYSTAL, 1.0, rotation=(rx, k * 72, rz), pivot=(0, 16, 0))
    ring_a = m.bone("ring_a", (0, 30, 0), "root")
    ring(ring_a, 17, 30, 12, 9.5, 3, 4, ROCK, 1.0, axis="y", teeth=3, tooth_mat=VEIN)
    ring_b = m.bone("ring_b", (0, 30, 0), "root", (0, 0, 60))
    ring(ring_b, 21, 30, 14, 9.6, 2, 3, MUSCLE_U, 1.0, axis="x")
    shards = m.bone("shards", (0, 34, 0), "root")
    for k in range(4):
        a = math.radians(k * 90)
        x, z = math.cos(a) * 26, math.sin(a) * 26
        shards.cube((x - 2, 30, z - 2), (4, 9, 4), CRYSTAL_BRIGHT, 1.0, rotation=(0, 45, 20), pivot=(x, 34, z))
    m.build()
    return m


def node_animations() -> dict:
    anims = {}

    def idle(t: float) -> dict:
        ph = t / 4.0 * 2 * math.pi
        pulse = 1 + 0.045 * math.sin(ph * 2)
        return {
            "core": {"scale": [pulse, pulse, pulse], "position": [0, 0.8 * math.sin(ph), 0]},
            "ring_a": {"rotation": [0, t / 4.0 * 360, 0]},
            "ring_b": {"rotation": [t / 4.0 * -720, 0, 0]},
            "shards": {"rotation": [0, -t / 4.0 * 360, 0], "position": [0, 1.5 * math.sin(ph * 2), 0]},
        }
    anims.update(bake_animation("animation.anatomy.mm_resonance_node.idle", idle, 4.0, True, fps=10))

    def charge(t: float) -> dict:
        k = math.sin(seg(t, 0, 1.6) * math.pi)
        s = 1 + 0.25 * k
        return {"core": {"scale": [s, s, s]}, "ring_a": {"scale": [1 + 0.3 * k] * 3}, "ring_b": {"rotation": [t * 900, 0, 0]}, "shards": {"position": [0, 6 * k, 0], "scale": [1 + 0.5 * k] * 3}}
    anims.update(bake_animation("animation.anatomy.mm_resonance_node.charge", charge, 1.6, False, fps=20))

    def death(t: float) -> dict:
        k = seg(t, 0, 0.6)
        g = seg(t, 0.6, 1.4)
        s = (1 + 0.6 * ease_out_back(k)) * (1 - ease_in(g))
        return {"core": {"scale": [max(0.001, s)] * 3}, "shards": {"scale": [max(0.001, 1 - g)] * 3, "position": [0, 10 * k, 0]},
                "ring_a": {"position": [0, -14 * ease_in(g), 0], "rotation": [25 * g, 0, 0]}, "ring_b": {"scale": [max(0.001, 1 - g)] * 3}}
    anims.update(bake_animation("animation.anatomy.mm_resonance_node.death", death, 1.6, "hold_on_last_frame", fps=20))

    anims.update(bake_animation("animation.anatomy.mm_resonance_node.hang", lambda t: {"root": {"rotation": [180, 0, 0], "position": [0, 56, 0]}}, 1.0, True, fps=2))
    return anims


# ============================================================================ LITHIC HEART
HEART_C = 48.0  # heart centre height above the entity position (units)


def build_heart() -> Model:
    m = Model("geometry.anatomy.mm_lithic_heart", seed=31, visible_bounds=(14, 12, (0, 3, 0)))
    c = HEART_C
    root = m.bone("root", (0, c, 0))
    root.locators["core"] = (0.0, c, 0.0)
    crystal = m.bone("crystal", (0, c, 0), "root")
    # elongated octahedron: stacked diamond slices
    slices = 10
    for i in range(slices):
        y0 = c - 50 + i * 10.0
        mid = (y0 + 5.0 - c) / 50
        half = 3 + 20 * (1 - abs(mid)) ** 0.85
        crystal.cube((-half, y0, -half), (half * 2, 10.0, half * 2), CRYSTAL if i % 3 else CRYSTAL_BRIGHT, 0.75, rotation=(0, 45, 0), pivot=(0, c, 0))
    crystal.cube((-5, c - 20, -5), (10, 40, 10), CRYSTAL_BRIGHT, 1.0, rotation=(0, 45, 0), pivot=(0, c, 0), inflate=0.5)
    for k in range(6):
        crystal.cube((-3, c + 4, -3), (6, 22, 6), CRYSTAL, 1.0, rotation=(28 if k % 2 else -28, k * 60, 12), pivot=(0, c, 0))
    # iris plates (8) enclosing the crystal when closed
    for k in range(8):
        b = m.bone(f"plate{k}", (0, c, 0), "root", (0, k * 45, 0))
        leaf = m.bone(f"plate{k}_leaf", (0, c - 34, -25), f"plate{k}")
        leaf.cube((-14, c - 34, -31), (28, 66, 7), ROCK, 0.75)
        leaf.cube((-11, c - 30, -33), (22, 58, 3), MUSCLE, 0.75)
        leaf.cube((-1.5, c - 28, -34), (3, 52, 2), VEIN, 0.75)
        leaf.cube((-12, c + 28, -27), (24, 8, 6), ROCK_DARK, 0.75)
    # gyroscope rings
    ring_h = m.bone("ring_h", (0, c, 0), "root")
    ring(ring_h, 44, c, 18, 15.8, 5, 7, ROCK, 0.75, axis="y", teeth=4, tooth_mat=VEIN)
    ring_v = m.bone("ring_v", (0, c, 0), "root")
    ring(ring_v, 56, c, 22, 16.4, 5, 7, MUSCLE_U, 0.75, axis="x", teeth=3, tooth_mat=ROCK)
    ring_v2 = m.bone("ring_v2", (0, c, 0), "root", (0, 90, 0))
    ring(ring_v2, 63, c, 24, 16.8, 4, 5, ROCK_DARK, 0.75, axis="x")
    # radial spokes + outer wheel (the "eye" of the cutaway)
    wheel = m.bone("wheel", (0, c, 0), "root")
    for k in range(12):
        a = k * 30
        wheel.cube((-4, c - 5, 48), (8, 9, 42), MUSCLE, 0.5, rotation=(0, a, 0), pivot=(0, c, 0))
        wheel.cube((-1.5, c + 4, 50), (3, 2, 38), VEIN, 0.5, rotation=(0, a, 0), pivot=(0, c, 0))
    ring(wheel, 90, c, 24, 24, 7, 10, ROCK_MOSS, 0.5, axis="y")
    m.build()
    return m


def heart_animations() -> dict:
    anims = {}

    def plates(open_k: float) -> dict:
        return {f"plate{k}_leaf": {"rotation": [62 * open_k, 0, 0], "position": [0, -4 * open_k, -6 * open_k]} for k in range(8)}

    anims.update(bake_animation("animation.anatomy.mm_lithic_heart.closed", lambda t: plates(0.0), 1.0, True, fps=2))
    anims.update(bake_animation("animation.anatomy.mm_lithic_heart.opened", lambda t: plates(1.0), 1.0, True, fps=2))

    def beat(t: float) -> dict:
        # double heartbeat every 1.6 s
        k = 0.0
        for c0 in (0.0, 0.28):
            d = t - c0
            if 0 <= d < 0.3:
                k = max(k, math.sin(d / 0.3 * math.pi))
        s = 1 + 0.07 * k
        return {"crystal": {"scale": [s, s * 1.02, s]}, "wheel": {"scale": [1 + 0.02 * k] * 3}}
    anims.update(bake_animation("animation.anatomy.mm_lithic_heart.beat", beat, 1.6, True, fps=20))

    def rings(t: float) -> dict:
        return {
            "ring_h": {"rotation": [0, t / 12.0 * 360, 0]},
            "ring_v": {"rotation": [0, -t / 12.0 * 720, 0]},
            "ring_v2": {"rotation": [t / 12.0 * 360, 0, 0]},
            "wheel": {"rotation": [0, -t / 12.0 * 90, 0]},
            "root": {"position": [0, 1.2 * math.sin(t / 12.0 * 2 * math.pi * 3), 0]},
        }
    anims.update(bake_animation("animation.anatomy.mm_lithic_heart.rings", rings, 12.0, True, fps=8))

    def charge(t: float) -> dict:
        k = math.sin(seg(t, 0, 2.0) * math.pi)
        return {"crystal": {"scale": [1 + 0.22 * k] * 3}, "ring_h": {"scale": [1 + 0.25 * k] * 3}, "ring_v": {"rotation": [0, t * 540, 0]},
                "wheel": {"rotation": [0, 0, 0], "scale": [1 + 0.06 * k] * 3}}
    anims.update(bake_animation("animation.anatomy.mm_lithic_heart.charge", charge, 2.0, False, fps=20))

    def hurt(t: float) -> dict:
        k = math.sin(seg(t, 0, 0.5) * math.pi)
        return {"crystal": {"scale": [1 - 0.08 * k, 1 + 0.06 * k, 1 - 0.08 * k], "rotation": [0, 0, 6 * k * math.sin(t * 50)]}}
    anims.update(bake_animation("animation.anatomy.mm_lithic_heart.hurt", hurt, 0.5, False, fps=20))

    def death(t: float) -> dict:
        a = seg(t, 0.0, 3.0)
        b = seg(t, 3.0, 4.2)
        shake = math.sin(t * 40) * 6 * a * (1 - b)
        s = (1 + 0.35 * ease_in_out(a)) * (1 - ease_in(b))
        pose = {
            "crystal": {"scale": [max(0.001, s)] * 3, "rotation": [shake, 0, shake]},
            "ring_h": {"position": [0, -40 * ease_in(seg(t, 1.0, 3.5)), 0], "rotation": [30 * a, 0, 0]},
            "ring_v": {"position": [0, -46 * ease_in(seg(t, 1.4, 3.6)), 0]},
            "ring_v2": {"position": [0, -52 * ease_in(seg(t, 1.8, 3.8)), 0]},
            "wheel": {"position": [0, -10 * ease_in(seg(t, 2.0, 4.0)), 0], "rotation": [0, 0, 8 * a]},
        }
        pose.update({f"plate{k}_leaf": {"rotation": [90 * ease_in(seg(t, 0.5 + k * 0.1, 2.5 + k * 0.1)), 0, 0], "position": [0, -30 * ease_in(seg(t, 1.0, 3.0)), -10]} for k in range(8)})
        return pose
    anims.update(bake_animation("animation.anatomy.mm_lithic_heart.death", death, 4.2, "hold_on_last_frame", fps=15))
    return anims


# ============================================================================ STRATA SLAB (projectile)
def build_slab() -> Model:
    m = Model("geometry.anatomy.mm_strata_slab", seed=41, visible_bounds=(5, 5, (0, 1, 0)))
    root = m.bone("root", (0, 20, 0))
    root.cube((-32, 26, -32), (64, 8, 64), GRASS_SIDE, 1.0, faces={"up": GRASS, "down": DIRT})
    root.cube((-30, 8, -30), (60, 18, 60), ROCK, 1.0)
    root.cube((-25, 1, -25), (50, 8, 50), MUSCLE, 1.0)
    root.cube((-2, 2, -28), (4, 4, 56), VEIN, 1.0)
    root.cube((-12, 34, -8), (18, 14, 18), LEAVES, 1.0)
    root.cube((-5, 34, -1), (4, 6, 4), BARK, 1.0)
    root.cube((14, 34, 10), (10, 8, 10), LEAVES, 1.0)
    for i, (x, z, ln) in enumerate([(-18, -12, 14), (10, 16, 18), (16, -20, 10), (-8, 20, 12)]):
        root.cube((x - 2, 1 - ln, z - 2), (4, ln, 4), MUSCLE, 1.0)
    m.build()
    return m


def slab_animations() -> dict:
    def tumble(t: float) -> dict:
        return {"root": {"rotation": [t / 2.0 * 360, t / 2.0 * 140, t / 2.0 * 220]}}
    return bake_animation("animation.anatomy.mm_strata_slab.tumble", tumble, 2.0, True, fps=10)


# ============================================================================ PETAL
PETAL_SEGS = [(336, 64), (316, 60), (290, 56), (256, 50), (214, 44), (168, 38), (118, 30), (68, 24)]  # (width, thickness)
PETAL_SEG_LEN = 90.0
PETAL_CLOSED = {"root": 0.0, "segs": [6, 10, 11, 12, 12, 12, 12, 12]}
PETAL_OPEN = {"root": -36.0, "segs": [-2, -1, 1, 3, 4, 5, 6, 8]}
PETAL_FOLDED = {"root": 64.0, "segs": [8, 10, 12, 12, 12, 12, 12, 14]}


def build_petal() -> Model:
    m = Model("geometry.anatomy.mm_petal", seed=51, visible_bounds=(60, 60, (0, 20, 0)))
    root = m.bone("root", (0, 0, 0))
    root.cube((-180, -24, -40), (360, 30, 80), MUSCLE, 0.375)  # hinge into the rim
    parent = "root"
    y = 0.0
    for i, (w, th) in enumerate(PETAL_SEGS):
        b = m.bone(f"s{i}", (0, y, 0), parent)
        L = PETAL_SEG_LEN + 6
        # outer shell (+Z) strata with moss, inner (-Z) musculature
        b.cube((-w / 2, y, 0), (w, L, th * 0.6), ROCK_MOSS, 0.375)
        b.cube((-w / 2 + 6, y + 2, -th * 0.4), (w - 12, L - 4, th * 0.4), MUSCLE_VEINS, 0.375)
        # inner radial ribs with circulation veins
        for rx in (-w * 0.28, w * 0.28):
            b.cube((rx - 9, y, -th * 0.4 - 10), (18, L, 10), MUSCLE, 0.375)
            b.cube((rx - 2, y + 4, -th * 0.4 - 12), (4, L - 8, 2), VEIN, 0.375)
        b.cube((-3, y, -th * 0.4 - 7), (6, L, 7), MUSCLE, 0.375)
        # outer strata ledges and forest clumps
        if i < 7 and i % 2 == 0:
            b.cube((-w / 2 + 8, y + L * 0.45, th * 0.6), (w - 16, 10, 14), ROCK, 0.375, faces={"up": GRASS})
        if i in (0, 1, 2, 3, 4):
            for j, fx in enumerate((-0.3, 0.05, 0.32)):
                if (i >= 3 and j != 1) or (i % 2 == 1 and j == 1):
                    continue
                tx = fx * w
                ty = y + L * (0.55 if j != 1 else 0.2)
                b.cube((tx - 4, ty, th * 0.6), (8, 22, 14), BARK, 0.375, rotation=(-70, 0, 0), pivot=(tx, ty, th * 0.6))
                b.cube((tx - 18, ty - 8, th * 0.6 + 12), (36, 34, 30), LEAVES, 0.375)
        parent = b.name
        y += PETAL_SEG_LEN
    m.build()
    return m


def petal_pose(p: dict) -> dict:
    pose = {"root": {"rotation": [p["root"], 0, 0]}}
    for i, r in enumerate(p["segs"]):
        pose[f"s{i}"] = {"rotation": [r, 0, 0]}
    return pose


def lerp_pose(a: dict, b: dict, k: float) -> dict:
    return {"root": a["root"] + (b["root"] - a["root"]) * k, "segs": [x + (y - x) * k for x, y in zip(a["segs"], b["segs"])]}


def petal_animations() -> dict:
    anims = {}
    anims.update(bake_animation("animation.anatomy.mm_petal.closed", lambda t: petal_pose(PETAL_CLOSED), 1.0, True, fps=2))

    def open_idle(t: float) -> dict:
        ph = t / 6.0 * 2 * math.pi
        p = dict(PETAL_OPEN)
        p = {"root": PETAL_OPEN["root"] + 2.0 * math.sin(ph), "segs": [s + 1.2 * math.sin(ph + i * 0.5) for i, s in enumerate(PETAL_OPEN["segs"])]}
        return petal_pose(p)
    anims.update(bake_animation("animation.anatomy.mm_petal.open", open_idle, 6.0, True, fps=6))
    anims.update(bake_animation("animation.anatomy.mm_petal.folded", lambda t: petal_pose(PETAL_FOLDED), 1.0, True, fps=2))

    def unfold(t: float) -> dict:
        # peel: the tip unrolls first, then the whole petal swings out and overshoots
        k = ease_out_back(seg(t, 0.3, 3.2), 1.2)
        return petal_pose(lerp_pose(PETAL_CLOSED, PETAL_OPEN, k))
    anims.update(bake_animation("animation.anatomy.mm_petal.unfold", unfold, 3.6, "hold_on_last_frame", fps=20))

    def collapse(t: float) -> dict:
        k = ease_in(seg(t, 0, 3.0))
        p = {"root": PETAL_OPEN["root"] - 60 * k, "segs": [s - 6 * k * (i + 1) for i, s in enumerate(PETAL_OPEN["segs"])]}
        pose = petal_pose(p)
        pose["root"]["position"] = [0, -160 * ease_in(seg(t, 1.5, 4.0)), 0]
        return pose
    anims.update(bake_animation("animation.anatomy.mm_petal.collapse", collapse, 4.0, "hold_on_last_frame", fps=12))
    return anims


# ============================================================================ STRATA PLATE (Inverted Strata)
PLATE_VARIANTS = {
    "geometry.anatomy.mm_strata_plate": (5, 3, 11),
    "geometry.anatomy.mm_rib_plate": (3, 3, 9),
}


def build_plate(identifier: str, w_blocks: int, t_blocks: int, l_blocks: int, rib: bool) -> Model:
    m = Model(identifier, seed=61 + w_blocks, visible_bounds=(14, 14, (0, 3, 0)))
    W, T, L = w_blocks * 16, t_blocks * 16, l_blocks * 16
    # 'hinge' spins the plate about its own centre line (wall flip: symmetric, so the final block
    # placement never depends on the rotation direction); 'roll' flips it over a raised axis (ceiling)
    hinge = m.bone("hinge", (0, T / 2, 0))
    roll = m.bone("roll", (0, 72, 0), "hinge")
    top = GRASS if not rib else m_solid("#7a2a2a")
    side = GRASS_SIDE if not rib else MUSCLE
    roll.cube((-W / 2, T - 16, -L / 2), (W, 16, L), side, 1.0, faces={"up": top, "down": DIRT})
    roll.cube((-W / 2, 0, -L / 2), (W, T - 16, L), ROCK if not rib else MUSCLE_VEINS, 1.0, faces={"down": MUSCLE})
    if rib:
        roll.cube((-1, T, -L / 2 + 4), (2, 0.5, L - 8), VEIN, 1.0)
    m.build()
    return m


def plate_animations() -> dict:
    anims = {}

    def wall(t: float) -> dict:
        k = ease_out_back(seg(t, 0.15, 1.0), 1.4)
        return {"hinge": {"rotation": [0, 0, -90 * k]}}
    anims.update(bake_animation("animation.anatomy.mm_strata_plate.flip_wall", wall, 1.2, "hold_on_last_frame", fps=20))

    def ceil(t: float) -> dict:
        k = ease_in_out(seg(t, 0.15, 1.3))
        return {"roll": {"rotation": [0, 0, 180 * k]}}
    anims.update(bake_animation("animation.anatomy.mm_strata_plate.flip_ceiling", ceil, 1.4, "hold_on_last_frame", fps=20))

    def unflip(t: float) -> dict:
        k = ease_in_out(seg(t, 0.0, 1.0))
        return {"hinge": {"rotation": [0, 0, -90 * (1 - k)]}}
    anims.update(bake_animation("animation.anatomy.mm_strata_plate.unflip_wall", unflip, 1.0, "hold_on_last_frame", fps=20))

    def unroll(t: float) -> dict:
        k = ease_in_out(seg(t, 0.0, 1.1))
        return {"roll": {"rotation": [0, 0, 180 * (1 - k)]}}
    anims.update(bake_animation("animation.anatomy.mm_strata_plate.unflip_ceiling", unroll, 1.1, "hold_on_last_frame", fps=20))
    return anims


# ============================================================================ registry
def build_all():
    """Returns [(short_name, Model)] and {anim_file_name: animations}."""
    models = [
        ("mm_root_leg", build_leg()),
        ("mm_resonance_node", build_node()),
        ("mm_lithic_heart", build_heart()),
        ("mm_strata_slab", build_slab()),
        ("mm_petal", build_petal()),
        ("mm_strata_plate", build_plate("geometry.anatomy.mm_strata_plate", 5, 3, 11, False)),
        ("mm_rib_plate", build_plate("geometry.anatomy.mm_rib_plate", 3, 3, 9, True)),
    ]
    anims = {
        "mm_root_leg": leg_animations(),
        "mm_resonance_node": node_animations(),
        "mm_lithic_heart": heart_animations(),
        "mm_strata_slab": slab_animations(),
        "mm_petal": petal_animations(),
        "mm_strata_plate": plate_animations(),
    }
    return models, anims
