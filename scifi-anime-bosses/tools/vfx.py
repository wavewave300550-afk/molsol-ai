"""
vfx.py - particle sprite atlas + particle effect definitions for VESPER-0.

Script-spawned effects read parameters from MolangVariableMap variables:
  variable.radius, variable.length, variable.life, variable.speed, variable.height,
  variable.dir_x / dir_y / dir_z, variable.cr / cg / cb (colour).
Animation-triggered effects (bound to locators) use fixed parameters.
Budget (mobile): every emitter is short lived and emits <= 140 particles.
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

import numpy as np

import tex

ATLAS = "textures/particle/sab_vesper"
AW = AH = 128

# sprite cells (u, v, w, h) in the atlas
SPR = {
    "dot": (0, 0, 16, 16), "star": (16, 0, 16, 16), "ring": (32, 0, 16, 16), "streak": (48, 0, 16, 16),
    "shard": (64, 0, 16, 16), "cross": (80, 0, 16, 16), "ember": (96, 0, 16, 16), "eye": (112, 0, 16, 16),
}
FLIP = {  # name: (base_u, base_v, frames)
    "glyph": (0, 16, 8), "smoke": (0, 32, 8), "wave": (0, 48, 8),
}

GOLD = (1.0, 0.82, 0.42)
CYAN = (0.38, 0.9, 1.0)
WHITE = (1.0, 0.97, 0.9)
VIOLET = (0.74, 0.34, 1.0)
MAGENTA = (1.0, 0.32, 0.82)
ORANGE = (1.0, 0.55, 0.18)
STEAM = (0.86, 0.9, 0.95)


# ----------------------------------------------------------------------------- sprite atlas

def _radial(n, power=1.6):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    r = np.sqrt(((xx + 0.5 - n / 2) / (n / 2)) ** 2 + ((yy + 0.5 - n / 2) / (n / 2)) ** 2)
    return np.clip(1 - r, 0, 1) ** power, r


def atlas_image() -> np.ndarray:
    img = np.zeros((AH, AW, 4), np.float32)

    def put(cell, a, rgb=(1, 1, 1)):
        u, v, w, h = cell
        img[v:v + h, u:u + w, :3] = np.array(rgb, np.float32)
        img[v:v + h, u:u + w, 3] = a

    d, r = _radial(16, 1.8)
    put(SPR["dot"], d)
    yy, xx = np.mgrid[0:16, 0:16].astype(np.float32)
    cx = np.abs(xx + 0.5 - 8) / 8
    cy = np.abs(yy + 0.5 - 8) / 8
    star = np.clip(1 - (cx * 6) * (cy + 0.05), 0, 1) * np.clip(1 - cy, 0, 1) + np.clip(1 - (cy * 6) * (cx + 0.05), 0, 1) * np.clip(1 - cx, 0, 1)
    put(SPR["star"], np.clip(star + d * 0.6, 0, 1))
    put(SPR["ring"], np.clip(1 - np.abs(r - 0.72) * 7, 0, 1))
    put(SPR["streak"], np.clip(1 - cy * 5, 0, 1) * np.clip(1 - cx, 0, 1) ** 0.7)
    shard = ((xx + yy * 0.6) > 5) & ((xx - yy) < 6) & (yy > 2) & (xx < 13) & ((xx + yy) < 22)
    put(SPR["shard"], shard.astype(np.float32), (0.95, 0.96, 1.0))
    cross = ((np.abs(xx + 0.5 - 8) < 1.6) & (np.abs(yy + 0.5 - 7) < 6.5)) | ((np.abs(yy + 0.5 - 5) < 1.6) & (np.abs(xx + 0.5 - 8) < 4.5))
    put(SPR["cross"], np.clip(cross.astype(np.float32) + d * 0.35, 0, 1))
    put(SPR["ember"], np.clip(d * 1.6, 0, 1) ** 0.6)
    eye_a, er = _radial(16, 1.0)
    eye = np.clip((er < 0.85).astype(np.float32) * 0.5 + np.clip(1 - np.abs(er - 0.45) * 5, 0, 1), 0, 1)
    eye[np.abs(xx + 0.5 - 8) < 1.0] *= 0.15
    put(SPR["eye"], eye)
    # glyph flipbook
    gu, gv, n = FLIP["glyph"]
    for k in range(n):
        g = tex.glyph_bitmap(900 + k * 7, 5, 7)
        cell = np.zeros((16, 16), np.float32)
        big = np.kron(g, np.ones((2, 2), np.float32))
        cell[1:15, 3:13] = big
        glow = tex.blur(cell, 1, 1)
        put((gu + k * 16, gv, 16, 16), np.clip(cell + glow * 0.6, 0, 1))
    # smoke flipbook (puff grows and frays)
    su, sv, n = FLIP["smoke"]
    for k in range(n):
        base = tex.fbm(16, 16, 6, 3, 300 + k)
        dd, rr = _radial(16, 1.0)
        rad = 0.55 + 0.45 * k / (n - 1)
        a = np.clip((1 - rr / rad) * 1.6, 0, 1) * (0.55 + 0.6 * base) * (1 - 0.55 * k / n)
        put((su + k * 16, sv, 16, 16), np.clip(a, 0, 1))
    # expanding ring flipbook
    wu, wv, n = FLIP["wave"]
    for k in range(n):
        rad = 0.25 + 0.7 * k / (n - 1)
        a = np.clip(1 - np.abs(r - rad) * (10 - k), 0, 1) * (1 - 0.5 * k / n)
        put((wu + k * 16, wv, 16, 16), a)
    return img


# ----------------------------------------------------------------------------- effect builders

def _uv(sprite, flip=None, fps=None, stretch=True):
    if flip:
        bu, bv, n = FLIP[flip]
        fb = {"base_UV": [bu, bv], "size_UV": [16, 16], "step_UV": [16, 0], "max_frame": n}
        if stretch:
            fb["stretch_to_lifetime"] = True
        else:
            fb["frames_per_second"] = fps or 12
            fb["loop"] = True
        return {"texture_width": AW, "texture_height": AH, "flipbook": fb}
    u, v, w, h = SPR[sprite]
    return {"texture_width": AW, "texture_height": AH, "uv": [u, v], "uv_size": [w, h]}


def _color(rgb, fade="1 - variable.particle_age / variable.particle_lifetime", alpha=1.0):
    if rgb == "var":
        r, g, b = "variable.cr", "variable.cg", "variable.cb"
    else:
        r, g, b = (round(c, 3) for c in rgb)
    a = f"({fade}) * {alpha}" if fade else alpha
    return {"color": [r, g, b, a]}


def effect(identifier, components, material="particles_add"):
    return {
        "format_version": "1.10.0",
        "particle_effect": {
            "description": {"identifier": identifier,
                            "basic_render_parameters": {"material": material, "texture": ATLAS}},
            "components": components,
        },
    }


def burst(identifier, rgb, count=24, speed=(2.0, 5.0), life=(0.4, 0.9), size=0.18, sprite="dot", gravity=0.0,
          drag=2.0, shape=("sphere", 0.3), material="particles_add", flip=None, collide=False, spin=False,
          direction="outwards", shrink=True):
    sp_lo, sp_hi = speed
    comps = {
        "minecraft:emitter_rate_instant": {"num_particles": count},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:particle_initial_speed": f"math.random({sp_lo}, {sp_hi})",
        "minecraft:particle_lifetime_expression": {"max_lifetime": f"math.random({life[0]}, {life[1]})"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -gravity, 0], "linear_drag_coefficient": drag},
        "minecraft:particle_appearance_tinting": _color(rgb),
    }
    kind, rad = shape
    if kind == "sphere":
        comps["minecraft:emitter_shape_sphere"] = {"radius": rad, "direction": direction}
    elif kind == "disc":
        comps["minecraft:emitter_shape_disc"] = {"radius": rad, "direction": direction, "surface_only": False}
    else:
        comps["minecraft:emitter_shape_point"] = {}
    s = f"{size} * (1 - variable.particle_age / variable.particle_lifetime * 0.6)" if shrink else size
    bb = {"size": [s, s], "facing_camera_mode": "rotate_xyz", "uv": _uv(sprite, flip)}
    if sprite == "streak":
        bb["facing_camera_mode"] = "lookat_direction"
        bb["size"] = [size * 0.35, size * 1.6]
        bb["direction"] = {"mode": "derive_from_velocity", "min_speed_threshold": 0.01}
    comps["minecraft:particle_appearance_billboard"] = bb
    if collide:
        comps["minecraft:particle_motion_collision"] = {"collision_drag": 4, "coefficient_of_restitution": 0.2,
                                                         "collision_radius": 0.08}
    if spin:
        comps["minecraft:particle_initial_spin"] = {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-480, 480)"}
    return effect(identifier, comps, material)


def gather(identifier, rgb, radius=4.0, life=0.8, count=40, size=0.16, sprite="dot"):
    """Particles spawn on a sphere and converge on the emitter."""
    comps = {
        "minecraft:emitter_rate_instant": {"num_particles": count},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_sphere": {"radius": radius, "surface_only": True, "direction": "inwards"},
        "minecraft:particle_initial_speed": round(radius / life, 3),
        "minecraft:particle_lifetime_expression": {"max_lifetime": life},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 0.0},
        "minecraft:particle_appearance_billboard": {"size": [f"{size} * (0.4 + variable.particle_age / variable.particle_lifetime)"] * 2,
                                                    "facing_camera_mode": "rotate_xyz", "uv": _uv(sprite)},
        "minecraft:particle_appearance_tinting": _color(rgb, fade="0.3 + variable.particle_age / variable.particle_lifetime * 0.7"),
    }
    return effect(identifier, comps)


def ring_wave(identifier, rgb, speed=12.0, life=0.9, count=72, size=0.3, radius=0.6, sprite="dot", vertical=False):
    comps = {
        "minecraft:emitter_rate_instant": {"num_particles": count},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_disc": {"radius": radius, "surface_only": True, "direction": "outwards",
                                         "plane_normal": "z" if vertical else "y"},
        "minecraft:particle_initial_speed": speed,
        "minecraft:particle_lifetime_expression": {"max_lifetime": life},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 0.6},
        "minecraft:particle_appearance_billboard": {"size": [size, size], "facing_camera_mode": "rotate_xyz", "uv": _uv(sprite)},
        "minecraft:particle_appearance_tinting": _color(rgb),
    }
    return effect(identifier, comps)


def steam(identifier, rgb, rate=40, active=0.8, life=(0.8, 1.4), size=0.6, speed=(1.0, 2.5), spread=1.5,
          rise=1.2, material="particles_blend"):
    comps = {
        "minecraft:emitter_rate_steady": {"spawn_rate": rate, "max_particles": int(rate * life[1] * 1.2) + 4},
        "minecraft:emitter_lifetime_once": {"active_time": active},
        "minecraft:emitter_shape_sphere": {"radius": spread, "direction": "outwards"},
        "minecraft:particle_initial_speed": f"math.random({speed[0]}, {speed[1]})",
        "minecraft:particle_lifetime_expression": {"max_lifetime": f"math.random({life[0]}, {life[1]})"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, rise, 0], "linear_drag_coefficient": 1.5},
        "minecraft:particle_appearance_billboard": {"size": [f"{size} * (0.5 + variable.particle_age / variable.particle_lifetime)"] * 2,
                                                    "facing_camera_mode": "rotate_xyz", "uv": _uv(None, flip="smoke")},
        "minecraft:particle_appearance_tinting": _color(rgb, alpha=0.8),
    }
    return effect(identifier, comps, material)


# ----------------------------------------------------------------------------- script-parameterised effects

def telegraph_ring():
    """Glowing outline circle on the ground: radius / life / colour from script."""
    comps = {
        "minecraft:emitter_initialization": {"creation_expression": "variable.rr = math.max(variable.radius, 0.5);"},
        "minecraft:emitter_rate_steady": {"spawn_rate": "math.min(30 + variable.rr * 18, 140)", "max_particles": 140},
        "minecraft:emitter_lifetime_once": {"active_time": "math.max(variable.life, 0.1)"},
        "minecraft:emitter_shape_disc": {"radius": "variable.rr", "surface_only": True, "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": 0.25,
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.45},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 1.0},
        "minecraft:particle_appearance_billboard": {"size": [0.22, 0.22], "facing_camera_mode": "rotate_xyz", "uv": _uv("dot")},
        "minecraft:particle_appearance_tinting": _color("var", fade="1 - variable.particle_age / variable.particle_lifetime * 0.8"),
    }
    return effect("sab:telegraph_ring", comps)


def telegraph_fill():
    comps = {
        "minecraft:emitter_initialization": {"creation_expression": "variable.rr = math.max(variable.radius, 0.5);"},
        "minecraft:emitter_rate_steady": {"spawn_rate": "math.min(10 + variable.rr * variable.rr * 2, 90)", "max_particles": 110},
        "minecraft:emitter_lifetime_once": {"active_time": "math.max(variable.life, 0.1)"},
        "minecraft:emitter_shape_disc": {"radius": "variable.rr", "surface_only": False, "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "math.random(0.3, 1.2)",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.5, 1.0)"},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 1.2},
        "minecraft:particle_appearance_billboard": {"size": [0.14, 0.14], "facing_camera_mode": "rotate_xyz", "uv": _uv("ember")},
        "minecraft:particle_appearance_tinting": _color("var", alpha=0.7),
    }
    return effect("sab:telegraph_fill", comps)


def telegraph_line():
    """Particles scattered along dir * length from the emitter (lance / lunge paths)."""
    comps = {
        "minecraft:emitter_rate_steady": {"spawn_rate": "math.min(20 + variable.length * 6, 140)", "max_particles": 140},
        "minecraft:emitter_lifetime_once": {"active_time": "math.max(variable.life, 0.1)"},
        "minecraft:emitter_shape_point": {"offset": [
            "variable.lt = math.random(0, 1); return variable.dir_x * variable.length * variable.lt;",
            "return variable.dir_y * variable.length * variable.lt + 0.05;",
            "return variable.dir_z * variable.length * variable.lt;"], "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": 0.2,
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.5},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 1.0},
        "minecraft:particle_appearance_billboard": {"size": [0.2, 0.2], "facing_camera_mode": "rotate_xyz", "uv": _uv("dot")},
        "minecraft:particle_appearance_tinting": _color("var"),
    }
    return effect("sab:telegraph_line", comps)


def shockwave():
    """Expanding ring: speed / life / colour from script (Halo Rite, hymn pulses, roar)."""
    comps = {
        "minecraft:emitter_rate_instant": {"num_particles": 120},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_disc": {"radius": 0.8, "surface_only": True, "direction": "outwards"},
        "minecraft:particle_initial_speed": "variable.speed",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.max(variable.life, 0.2)"},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 0.0},
        "minecraft:particle_appearance_billboard": {"size": [0.42, 0.42], "facing_camera_mode": "rotate_xyz", "uv": _uv("star")},
        "minecraft:particle_appearance_tinting": _color("var", fade="1 - variable.particle_age / variable.particle_lifetime * 0.5"),
    }
    return effect("sab:shockwave", comps)


def implosion():
    comps = {
        "minecraft:emitter_rate_instant": {"num_particles": 90},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_sphere": {"radius": "math.max(variable.radius, 1)", "surface_only": True, "direction": "inwards"},
        "minecraft:particle_initial_speed": "math.max(variable.radius, 1) / math.max(variable.life, 0.2)",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.max(variable.life, 0.2)"},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 0.0},
        "minecraft:particle_appearance_billboard": {"size": [0.3, 0.3], "facing_camera_mode": "rotate_xyz", "uv": _uv("star")},
        "minecraft:particle_appearance_tinting": _color("var", fade="0.3 + variable.particle_age / variable.particle_lifetime * 0.7"),
    }
    return effect("sab:implosion", comps)


def spiral_in():
    """Singularity accretion spiral (parametric orbit shrinking to the centre)."""
    comps = {
        "minecraft:emitter_rate_steady": {"spawn_rate": 60, "max_particles": 90},
        "minecraft:emitter_lifetime_once": {"active_time": "math.max(variable.life, 0.2)"},
        "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.2},
        "minecraft:particle_motion_parametric": {"relative_position": [
            "variable.a = variable.particle_random_1 * 360 + variable.particle_age * 300; variable.rad = math.max(variable.radius, 1) * (1 - variable.particle_age / variable.particle_lifetime); return math.cos(variable.a) * variable.rad;",
            "return 0.2 + variable.particle_random_2 * 0.6 + (1 - variable.particle_age / variable.particle_lifetime) * 0.4;",
            "return math.sin(variable.a) * variable.rad;"]},
        "minecraft:particle_appearance_billboard": {"size": [0.2, 0.2], "facing_camera_mode": "rotate_xyz", "uv": _uv("dot")},
        "minecraft:particle_appearance_tinting": _color("var", fade="0.4 + variable.particle_age / variable.particle_lifetime * 0.6"),
    }
    return effect("sab:spiral_in", comps)


def light_pillar(identifier="sab:light_pillar", rgb="var", height="math.max(variable.height, 2)", life="math.max(variable.life, 0.3)",
                 rate=70, width=0.5):
    comps = {
        "minecraft:emitter_rate_steady": {"spawn_rate": rate, "max_particles": 120},
        "minecraft:emitter_lifetime_once": {"active_time": life},
        "minecraft:emitter_shape_box": {"offset": [0, f"({height}) * 0.5", 0], "half_dimensions": [width, f"({height}) * 0.5", width],
                                        "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "math.random(1, 4)",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.4, 0.9)"},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 1.0},
        "minecraft:particle_appearance_billboard": {"size": [0.3, 0.9], "facing_camera_mode": "lookat_y", "uv": _uv("streak")},
        "minecraft:particle_appearance_tinting": _color(rgb),
    }
    return effect(identifier, comps)


def scorch():
    comps = {
        "minecraft:emitter_rate_steady": {"spawn_rate": 14, "max_particles": 40},
        "minecraft:emitter_lifetime_once": {"active_time": "math.max(variable.life, 0.5)"},
        "minecraft:emitter_shape_disc": {"radius": 1.0, "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "math.random(0.2, 0.8)",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.6, 1.2)"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.8, 0], "linear_drag_coefficient": 1.0},
        "minecraft:particle_appearance_billboard": {"size": [0.12, 0.12], "facing_camera_mode": "rotate_xyz", "uv": _uv("ember")},
        "minecraft:particle_appearance_tinting": {"color": {"gradient": [[1, 0.95, 0.8, 1], [1, 0.55, 0.15, 0.9], [0.4, 0.1, 0.05, 0]],
                                                           "interpolant": "variable.particle_age / variable.particle_lifetime"}},
    }
    return effect("sab:scorch", comps)


def drift(identifier, rgb, sprite, rate=6, active=3.0, life=(2.0, 3.0), size=0.3, radius=1.5, rise=0.6, flip=None,
          material="particles_add", fps=None):
    comps = {
        "minecraft:emitter_rate_steady": {"spawn_rate": rate, "max_particles": int(rate * life[1]) + 4},
        "minecraft:emitter_lifetime_once": {"active_time": active},
        "minecraft:emitter_shape_sphere": {"radius": radius, "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": rise,
        "minecraft:particle_lifetime_expression": {"max_lifetime": f"math.random({life[0]}, {life[1]})"},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 0.4},
        "minecraft:particle_appearance_billboard": {"size": [size, size], "facing_camera_mode": "rotate_xyz",
                                                    "uv": _uv(sprite, flip, fps=fps, stretch=fps is None)},
        "minecraft:particle_appearance_tinting": _color(rgb, fade="math.sin(variable.particle_age / variable.particle_lifetime * 180)"),
    }
    return effect(identifier, comps, material)


def trail(identifier, rgb, rate=30, active=1.0, life=0.5, size=0.25, sprite="dot", speed=0.4):
    comps = {
        "minecraft:emitter_rate_steady": {"spawn_rate": rate, "max_particles": int(rate * life * 1.3) + 4},
        "minecraft:emitter_lifetime_once": {"active_time": active},
        "minecraft:emitter_shape_sphere": {"radius": 0.15, "direction": "outwards"},
        "minecraft:emitter_local_space": {"position": False, "rotation": False},
        "minecraft:particle_initial_speed": speed,
        "minecraft:particle_lifetime_expression": {"max_lifetime": life},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 2.0},
        "minecraft:particle_appearance_billboard": {"size": [f"{size} * (1 - variable.particle_age / variable.particle_lifetime)"] * 2,
                                                    "facing_camera_mode": "rotate_xyz", "uv": _uv(sprite)},
        "minecraft:particle_appearance_tinting": _color(rgb),
    }
    return effect(identifier, comps)


# ----------------------------------------------------------------------------- registry

def all_effects() -> Dict[str, dict]:
    fx = {}

    def add(e):
        fx[e["particle_effect"]["description"]["identifier"]] = e

    # script-parameterised
    for e in (telegraph_ring(), telegraph_fill(), telegraph_line(), shockwave(), implosion(), spiral_in(),
              light_pillar(), scorch()):
        add(e)
    # script-spawned, fixed look
    add(burst("sab:beam_impact", WHITE, 26, (2, 6), (0.25, 0.6), 0.2, "streak", gravity=6, collide=True))
    add(burst("sab:hull_spark", (1.0, 0.85, 0.6), 12, (2, 5), (0.2, 0.45), 0.14, "streak", gravity=10))
    add(burst("sab:shield_spark", CYAN, 18, (1.5, 4), (0.3, 0.6), 0.2, "star"))
    add(burst("sab:heart_hit", MAGENTA, 22, (1.5, 4.5), (0.3, 0.7), 0.26, "star"))
    add(burst("sab:holy_blast", GOLD, 120, (6, 16), (0.6, 1.3), 0.45, "star", drag=1.2, shape=("sphere", 1.5)))
    add(burst("sab:nova_blast", VIOLET, 130, (8, 20), (0.6, 1.4), 0.5, "star", drag=1.0, shape=("sphere", 2.0)))
    add(burst("sab:debris", (0.92, 0.93, 0.96), 26, (3, 9), (1.0, 1.8), 0.32, "shard", gravity=14, drag=0.6, collide=True, spin=True,
              material="particles_alpha", shrink=False))
    add(burst("sab:dust", (0.55, 0.5, 0.45), 30, (1.5, 4), (0.8, 1.4), 0.9, None, gravity=-0.6, drag=2.5,
              shape=("disc", 1.0), material="particles_blend", flip="smoke"))
    add(burst("sab:plasma_pop", CYAN, 20, (1, 3.5), (0.25, 0.5), 0.2, "dot"))
    add(burst("sab:plasma_pop_gold", GOLD, 24, (1, 4), (0.25, 0.5), 0.22, "star"))
    add(burst("sab:censer_break", GOLD, 40, (2, 7), (0.5, 1.0), 0.28, "star", gravity=4))
    add(burst("sab:seraph_break", VIOLET, 40, (2, 7), (0.5, 1.0), 0.28, "star", gravity=4))
    add(burst("sab:vent_burst", ORANGE, 60, (4, 9), (0.4, 0.8), 0.4, "ember", gravity=-1, drag=2.2, shape=("sphere", 1.0)))
    add(burst("sab:summon_flash", WHITE, 80, (5, 14), (0.5, 1.1), 0.5, "star", drag=1.5))
    add(steam("sab:steam", STEAM, rate=36, active=0.9))
    add(drift("sab:glyph_rise", CYAN, None, rate=10, active=2.5, life=(1.6, 2.4), size=0.45, radius=4.0, rise=0.9, flip="glyph", fps=6))
    add(drift("sab:glyph_rise_dark", VIOLET, None, rate=10, active=2.5, life=(1.6, 2.4), size=0.45, radius=4.0, rise=0.9, flip="glyph", fps=6))
    add(drift("sab:dying_star", GOLD, "star", rate=12, active=3.0, life=(2.0, 3.0), size=0.3, radius=2.5, rise=0.8))
    add(drift("sab:incense", (0.95, 0.85, 0.7), None, rate=8, active=2.0, life=(1.5, 2.5), size=0.6, radius=0.3, rise=0.6,
              flip="smoke", material="particles_blend"))
    add(light_pillar("sab:summon_pillar", WHITE, "40", "2.0", rate=90, width=0.8))
    add(ring_wave("sab:hymn_wave", GOLD, speed=10.0, life=1.2, count=90, size=0.35, sprite="star"))
    # animation-triggered (bound to locators)
    add(burst("sab:arrival_flash", WHITE, 70, (4, 12), (0.4, 0.9), 0.5, "star", drag=1.5, shape=("sphere", 2.0)))
    add(ring_wave("sab:choir_burst", GOLD, speed=9.0, life=1.0, count=80, size=0.35, sprite="cross", vertical=True))
    add(burst("sab:ring_spark", CYAN, 36, (2, 6), (0.4, 0.8), 0.22, "star", shape=("sphere", 1.5)))
    add(gather("sab:lance_gather", CYAN, radius=5.0, life=0.7, count=50))
    add(burst("sab:spire_spark", CYAN, 10, (0.5, 2), (0.3, 0.6), 0.2, "star"))
    add(burst("sab:lance_muzzle", WHITE, 50, (3, 9), (0.3, 0.6), 0.4, "star", drag=2.5, shape=("sphere", 1.0)))
    add(gather("sab:horizon_gather", VIOLET, radius=6.0, life=1.0, count=60, sprite="star"))
    add(burst("sab:core_flare", GOLD, 60, (3, 8), (0.3, 0.7), 0.4, "star", drag=2.0, shape=("sphere", 1.2)))
    add(burst("sab:nova_flash", VIOLET, 70, (4, 10), (0.3, 0.8), 0.45, "star", drag=2.0, shape=("sphere", 1.5)))
    add(burst("sab:drone_launch", CYAN, 18, (1, 4), (0.3, 0.6), 0.24, "star"))
    add(steam("sab:vent_steam", STEAM, rate=30, active=0.7, size=0.8, spread=3.0, rise=1.6))
    add(burst("sab:heart_sparks", MAGENTA, 16, (0.5, 2), (0.6, 1.0), 0.2, "star", gravity=-0.5, shape=("sphere", 1.2)))
    add(drift("sab:prayer_glyphs", CYAN, None, rate=12, active=3.0, life=(1.8, 2.6), size=0.5, radius=5.0, rise=1.2, flip="glyph", fps=6))
    add(burst("sab:stun_sparks", WHITE, 24, (1, 4), (0.3, 0.6), 0.22, "streak", gravity=8, shape=("sphere", 2.5)))
    add(ring_wave("sab:roar_wave", VIOLET, speed=14.0, life=0.8, count=80, size=0.4, sprite="dot", vertical=True))
    add(trail("sab:lunge_trail", VIOLET, rate=60, active=0.7, life=0.6, size=0.5, sprite="dot", speed=0.2))
    add(burst("sab:talon_dust", (0.5, 0.45, 0.42), 18, (1, 3), (0.6, 1.0), 0.8, None, gravity=-0.4, drag=2.5,
              shape=("disc", 0.8), material="particles_blend", flip="smoke"))
    add(gather("sab:nova_gather", VIOLET, radius=7.0, life=1.1, count=70, sprite="star"))
    add(gather("sab:core_implode", WHITE, radius=5.0, life=0.45, count=60, sprite="star"))
    add(burst("sab:debris_burst", (0.92, 0.93, 0.96), 30, (4, 10), (1.0, 1.8), 0.36, "shard", gravity=14, drag=0.6,
              shape=("sphere", 3.0), material="particles_alpha", spin=True, shrink=False))
    add(trail("sab:engine_trail", CYAN, rate=20, active=1.0, life=0.6, size=0.45, sprite="dot", speed=0.6))
    add(trail("sab:engine_trail_dark", VIOLET, rate=20, active=1.0, life=0.6, size=0.45, sprite="dot", speed=0.6))
    add(trail("sab:orb_trail", CYAN, rate=24, active=1.0, life=0.4, size=0.3, sprite="dot", speed=0.1))
    add(trail("sab:halo_trail", GOLD, rate=24, active=1.0, life=0.3, size=0.25, sprite="star", speed=0.1))
    add(drift("sab:censer_smoke", (0.95, 0.85, 0.7), None, rate=6, active=1.0, life=(1.2, 2.0), size=0.5, radius=0.2, rise=0.5,
              flip="smoke", material="particles_blend"))
    add(burst("sab:ember_drip", VIOLET, 4, (0.1, 0.4), (0.8, 1.2), 0.14, "ember", gravity=3.0, shape=("sphere", 0.4)))
    return fx


# short names used by client entities / animations -> identifiers
def short_map():
    return {k.split(":", 1)[1]: k for k in all_effects()}
