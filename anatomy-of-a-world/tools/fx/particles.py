"""Particle effects + particle texture atlas for THE ANATOMY OF A WORLD (Boss 001 set).

All effects are format 1.10.0 particle files. Effects that need runtime data
read Molang variables the script sets with MolangVariableMap:
  variable.size, variable.life, variable.radius, variable.gap, variable.gap_dir,
  variable.dir (vec3), variable.speed, variable.color (rgba)
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image

TEX = "textures/particle/anatomy_particles"
W = H = 128

# atlas cells: name -> (u, v, w, h)
CELLS = {
    "blob": (0, 0, 32, 32),
    "dust": (32, 0, 32, 32),
    "ring": (64, 0, 32, 32),
    "target": (96, 0, 32, 32),
    "debris0": (0, 32, 8, 8),
    "debris1": (8, 32, 8, 8),
    "ember": (16, 32, 8, 8),
    "mote": (24, 32, 8, 8),
    "shard": (32, 32, 8, 8),
    "leaf": (40, 32, 8, 8),
    "hex": (48, 32, 16, 16),
    "spark": (64, 32, 8, 8),
    "streak": (64, 40, 32, 8),
    "pillar": (96, 32, 16, 32),
    "mist": (0, 64, 64, 64),
    "crack": (64, 64, 32, 32),
    "wave": (96, 64, 32, 32),
}


def build_atlas() -> Image.Image:
    img = np.zeros((H, W, 4), dtype=np.float32)
    rng = np.random.default_rng(7)

    def put(name, arr):
        u, v, w, h = CELLS[name]
        img[v:v + h, u:u + w] = arr

    def radial(n, power=2.0):
        y, x = np.mgrid[0:n, 0:n].astype(np.float32)
        c = (n - 1) / 2
        d = np.sqrt((x - c) ** 2 + (y - c) ** 2) / (n / 2)
        return np.clip(1 - d, 0, 1) ** power

    a = radial(32, 1.6)
    put("blob", np.dstack([np.ones_like(a)] * 3 + [a]))
    # dust: noisy blob
    n = rng.random((32, 32)).astype(np.float32)
    from_scipy = None
    a2 = radial(32, 1.2) * (0.55 + 0.45 * n)
    a2 = np.where(a2 > 0.18, a2, 0)
    put("dust", np.dstack([np.ones_like(a2) * (0.85 + 0.15 * n)] * 3 + [a2]))
    # ring outline
    y, x = np.mgrid[0:32, 0:32].astype(np.float32)
    d = np.sqrt((x - 15.5) ** 2 + (y - 15.5) ** 2)
    ringa = np.clip(1 - np.abs(d - 14.0) / 1.8, 0, 1)
    put("ring", np.dstack([np.ones_like(ringa)] * 3 + [ringa]))
    # target: segmented ring + centre dot
    ang = np.arctan2(y - 15.5, x - 15.5)
    seg = (np.floor((ang + math.pi) / (math.pi / 6)) % 2) == 0
    ta = np.clip(1 - np.abs(d - 13.5) / 1.6, 0, 1) * np.where(seg, 1.0, 0.35) + np.clip(1 - d / 2.5, 0, 1)
    ta += np.clip(1 - np.abs(d - 8.0) / 0.9, 0, 1) * 0.5
    put("target", np.dstack([np.ones_like(ta)] * 3 + [np.clip(ta, 0, 1)]))
    # debris chunks (grey pixel rocks)
    for name, seed in (("debris0", 1), ("debris1", 2)):
        r = np.random.default_rng(seed)
        c = 0.45 + 0.35 * r.random((8, 8))
        m = np.zeros((8, 8))
        m[1:7, 1:7] = 1
        m[0, 2:6] = 1
        m[2:6, 7] = 1
        m[7, 3:5] = r.integers(0, 2)
        put(name, np.dstack([c, c, c * 0.98, m]))
    em = radial(8, 1.0)
    put("ember", np.dstack([np.ones_like(em)] * 3 + [np.clip(em * 1.6, 0, 1)]))
    # mote: small diamond
    yy, xx = np.mgrid[0:8, 0:8].astype(np.float32)
    dm = np.clip(1 - (np.abs(xx - 3.5) + np.abs(yy - 3.5)) / 4.0, 0, 1)
    put("mote", np.dstack([np.ones_like(dm)] * 3 + [np.clip(dm * 1.8, 0, 1)]))
    sh = np.clip(1 - (np.abs(xx - 3.5) / 2.0 + np.abs(yy - 3.5) / 4.0), 0, 1)
    put("shard", np.dstack([np.ones_like(sh)] * 3 + [np.clip(sh * 2.5, 0, 1)]))
    lf = np.zeros((8, 8))
    lf[2:6, 1:7] = 1
    lf[1, 3:6] = 1
    lf[6, 2:5] = 1
    put("leaf", np.dstack([np.ones_like(lf)] * 3 + [lf]))
    # hex shimmer
    y16, x16 = np.mgrid[0:16, 0:16].astype(np.float32)
    hexa = np.zeros((16, 16))
    for k in range(6):
        t = k * math.pi / 3
        px = 7.5 + 6.5 * math.cos(t)
        py = 7.5 + 6.5 * math.sin(t)
        qx = 7.5 + 6.5 * math.cos(t + math.pi / 3)
        qy = 7.5 + 6.5 * math.sin(t + math.pi / 3)
        for s in np.linspace(0, 1, 30):
            ix, iy = int(round(px + (qx - px) * s)), int(round(py + (qy - py) * s))
            hexa[iy, ix] = 1
    put("hex", np.dstack([np.ones_like(hexa)] * 3 + [hexa]))
    sp = np.zeros((8, 8))
    sp[3:5, :] = 0.6
    sp[:, 3:5] = 0.6
    sp[3:5, 3:5] = 1
    put("spark", np.dstack([np.ones_like(sp)] * 3 + [sp]))
    ys, xs = np.mgrid[0:8, 0:32].astype(np.float32)
    st = np.clip(1 - np.abs(ys - 3.5) / 4, 0, 1) * np.clip(xs / 32, 0, 1) ** 0.6
    put("streak", np.dstack([np.ones_like(st)] * 3 + [st]))
    yp, xp = np.mgrid[0:32, 0:16].astype(np.float32)
    pil = np.clip(1 - np.abs(xp - 7.5) / 8, 0, 1) ** 1.5 * (yp / 31) ** 0.8
    put("pillar", np.dstack([np.ones_like(pil)] * 3 + [pil]))
    # mist: big soft cloud from several blobs
    mist = np.zeros((64, 64))
    ym, xm = np.mgrid[0:64, 0:64].astype(np.float32)
    for _ in range(14):
        cx, cy, r = rng.uniform(16, 48), rng.uniform(18, 46), rng.uniform(8, 18)
        mist = np.maximum(mist, np.clip(1 - np.sqrt((xm - cx) ** 2 + (ym - cy) ** 2) / r, 0, 1) ** 1.4)
    mist *= np.clip(1 - np.sqrt((xm - 31.5) ** 2 + (ym - 31.5) ** 2) / 32, 0, 1) ** 0.5
    put("mist", np.dstack([np.ones_like(mist)] * 3 + [mist * 0.9]))
    # crack: branching glowing fissure on transparent
    cr = np.zeros((32, 32))
    r = np.random.default_rng(11)
    for start in ((2, 16), (16, 2), (30, 18)):
        x0, y0 = start
        a0 = math.atan2(16 - y0, 16 - x0)
        x, y = float(x0), float(y0)
        for _ in range(28):
            ix, iy = int(x), int(y)
            if 0 <= ix < 32 and 0 <= iy < 32:
                cr[iy, ix] = 1
                if iy + 1 < 32:
                    cr[iy + 1, ix] = max(cr[iy + 1, ix], 0.5)
            a0 += r.uniform(-0.5, 0.5)
            x += math.cos(a0)
            y += math.sin(a0)
    put("crack", np.dstack([np.ones_like(cr)] * 3 + [cr]))
    # wave: soft thick ring for expanding pulses
    yw, xw = np.mgrid[0:32, 0:32].astype(np.float32)
    dw = np.sqrt((xw - 15.5) ** 2 + (yw - 15.5) ** 2)
    wa = np.clip(1 - np.abs(dw - 13) / 3.2, 0, 1) ** 1.3
    put("wave", np.dstack([np.ones_like(wa)] * 3 + [wa]))
    out = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def uv(name, flip=None):
    u, v, w, h = CELLS[name]
    return {"texture_width": W, "texture_height": H, "uv": [u, v], "uv_size": [w, h]}


def effect(identifier, material, components):
    return {
        "format_version": "1.10.0",
        "particle_effect": {
            "description": {"identifier": identifier, "basic_render_parameters": {"material": material, "texture": TEX}},
            "components": components,
        },
    }


def fade(c0, c1=None, mid=None):
    """Colour gradient over particle life; colours are [r,g,b,a] 0..1."""
    grad = {"0.0": c0}
    if mid:
        grad["0.5"] = mid
    grad["1.0"] = c1 if c1 else [c0[0], c0[1], c0[2], 0.0]
    return {"color": {"interpolant": "v.particle_age / v.particle_lifetime", "gradient": grad}}


def effects() -> dict:
    E = {}
    E["mm_dust"] = effect("anatomy:mm_dust", "particles_blend", {
        "minecraft:emitter_rate_instant": {"num_particles": "math.clamp(v.size * 10, 6, 48)"},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_sphere": {"radius": "math.max(v.size, 0.5)", "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(1.6, 3.2)"},
        "minecraft:particle_initial_speed": "math.random(0.5, 3.0)",
        "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-40, 40)"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.35, 0], "linear_drag_coefficient": 1.6},
        "minecraft:particle_appearance_billboard": {"size": ["(0.6 + v.particle_age * 0.9) * math.clamp(v.size, 0.7, 2.2)", "(0.6 + v.particle_age * 0.9) * math.clamp(v.size, 0.7, 2.2)"], "facing_camera_mode": "rotate_xyz", "uv": uv("dust")},
        "minecraft:particle_appearance_tinting": fade([0.62, 0.6, 0.57, 0.85], [0.7, 0.69, 0.66, 0.0], [0.6, 0.58, 0.55, 0.55]),
        "minecraft:particle_appearance_lighting": {},
    })
    E["mm_debris"] = effect("anatomy:mm_debris", "particles_alpha", {
        "minecraft:emitter_rate_instant": {"num_particles": "math.clamp(v.size * 8, 4, 40)"},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_sphere": {"radius": "math.max(v.size * 0.6, 0.4)", "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(1.2, 2.4)"},
        "minecraft:particle_initial_speed": "math.random(3, 9)",
        "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-400, 400)"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -18, 0], "linear_drag_coefficient": 0.4},
        "minecraft:particle_motion_collision": {"collision_drag": 6, "coefficient_of_restitution": 0.25, "collision_radius": 0.12},
        "minecraft:particle_appearance_billboard": {"size": ["0.12 + v.particle_random_1 * 0.16", "0.12 + v.particle_random_1 * 0.16"], "facing_camera_mode": "rotate_xyz",
                                                    "uv": {"texture_width": W, "texture_height": H, "uv": ["v.particle_random_2 > 0.5 ? 8 : 0", 32], "uv_size": [8, 8]}},
        "minecraft:particle_appearance_tinting": {"color": [0.78, 0.76, 0.74, 1.0]},
        "minecraft:particle_appearance_lighting": {},
    })
    E["mm_crack"] = effect("anatomy:mm_crack", "particles_add", {
        "minecraft:emitter_rate_instant": {"num_particles": 6},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_disc": {"radius": 0.6, "plane_normal": "y", "direction": [0, 1, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.6, 1.2)"},
        "minecraft:particle_initial_speed": "math.random(0.6, 2.0)",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.5, 0], "linear_drag_coefficient": 1.0},
        "minecraft:particle_appearance_billboard": {"size": ["0.14 * (1 - v.particle_age / v.particle_lifetime * 0.6)", "0.14 * (1 - v.particle_age / v.particle_lifetime * 0.6)"], "facing_camera_mode": "lookat_xyz", "uv": uv("ember")},
        "minecraft:particle_appearance_tinting": fade([1.0, 0.55, 0.15, 1.0], [0.9, 0.1, 0.05, 0.0]),
    })
    E["mm_fault"] = effect("anatomy:mm_fault", "particles_add", {
        "minecraft:emitter_rate_instant": {"num_particles": 1},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {"offset": [0, 0.08, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.max(v.life, 0.3)"},
        "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)"},
        "minecraft:particle_appearance_billboard": {"size": ["0.9 + 0.15 * math.sin(v.particle_age * 900)", "0.9 + 0.15 * math.sin(v.particle_age * 900)"], "facing_camera_mode": "emitter_transform_xz", "uv": uv("crack")},
        "minecraft:particle_appearance_tinting": fade([1.0, 0.35, 0.12, 0.95], [1.0, 0.75, 0.3, 0.0], [1.0, 0.45, 0.15, 1.0]),
    })
    E["mm_target"] = effect("anatomy:mm_target", "particles_add", {
        "minecraft:emitter_rate_instant": {"num_particles": 1},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {"offset": [0, 0.12, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.max(v.life, 0.3)"},
        "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 45},
        "minecraft:particle_appearance_billboard": {"size": ["v.radius * (1.25 - 0.25 * v.particle_age / v.particle_lifetime)", "v.radius * (1.25 - 0.25 * v.particle_age / v.particle_lifetime)"], "facing_camera_mode": "emitter_transform_xz", "uv": uv("target")},
        "minecraft:particle_appearance_tinting": fade([1.0, 0.45, 0.1, 0.55], [1.0, 0.1, 0.05, 1.0], [1.0, 0.3, 0.08, 0.8]),
    })
    # Resonance ring segment: emitted on a circle of radius v.radius, skipping two opposite gaps
    # (gap centre v.gap_dir degrees, gap width v.gap degrees). v.gap = 0 -> full ring.
    ang = "(v.gap_dir + v.gap * 0.5 + math.random(0, 180 - v.gap) + (math.random(0, 1) > 0.5 ? 180 : 0))"
    E["mm_resonance_ring"] = effect("anatomy:mm_resonance_ring", "particles_add", {
        "minecraft:emitter_rate_instant": {"num_particles": "math.clamp(v.radius * 4.5, 12, 140)"},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_custom": {"offset": [f"v.radius * math.cos({ang})", "math.random(0, 1.9)", f"v.radius * math.sin({ang})"], "direction": [0, 1, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.18, 0.32)"},
        "minecraft:particle_initial_speed": 0.4,
        "minecraft:particle_appearance_billboard": {"size": ["0.22", "0.3"], "facing_camera_mode": "lookat_y", "uv": uv("mote")},
        "minecraft:particle_appearance_tinting": fade([0.85, 0.55, 1.0, 1.0], [0.55, 0.25, 1.0, 0.0]),
    })
    E["mm_resonance_wave"] = effect("anatomy:mm_resonance_wave", "particles_add", {
        "minecraft:emitter_rate_instant": {"num_particles": 1},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {"offset": [0, 0.15, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.max(v.life, 0.3)"},
        "minecraft:particle_appearance_billboard": {"size": ["0.5 + v.radius * v.particle_age / v.particle_lifetime", "0.5 + v.radius * v.particle_age / v.particle_lifetime"], "facing_camera_mode": "emitter_transform_xz", "uv": uv("wave")},
        "minecraft:particle_appearance_tinting": fade([0.75, 0.45, 1.0, 0.9], [0.45, 0.2, 0.9, 0.0]),
    })
    E["mm_beam"] = effect("anatomy:mm_beam", "particles_add", {
        "minecraft:emitter_rate_instant": {"num_particles": 3},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {"direction": ["v.dir.direction_x", "v.dir.direction_y", "v.dir.direction_z"]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.max(v.life, 0.2)"},
        "minecraft:particle_initial_speed": "v.dir.speed * math.random(0.96, 1.04)",
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_appearance_billboard": {"size": [0.2, 0.2], "facing_camera_mode": "lookat_xyz", "uv": uv("mote")},
        "minecraft:particle_appearance_tinting": fade([0.95, 0.75, 1.0, 1.0], [0.7, 0.4, 1.0, 0.6]),
    })
    E["mm_mist"] = effect("anatomy:mm_mist", "particles_blend", {
        "minecraft:emitter_rate_instant": {"num_particles": "math.clamp(v.size * 2, 2, 14)"},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_disc": {"radius": "math.max(v.size, 1)", "plane_normal": "y", "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(3, 6)"},
        "minecraft:particle_initial_speed": "math.random(0.2, 0.9)",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.08, 0], "linear_drag_coefficient": 0.4},
        "minecraft:particle_appearance_billboard": {"size": ["2.5 + v.particle_age * 0.7", "2.0 + v.particle_age * 0.5"], "facing_camera_mode": "lookat_xyz", "uv": uv("mist")},
        "minecraft:particle_appearance_tinting": fade([1.0, 1.0, 1.0, 0.0], [1.0, 1.0, 1.0, 0.0], [0.97, 0.98, 1.0, 0.75]),
    })
    E["mm_shard"] = effect("anatomy:mm_shard", "particles_add", {
        "minecraft:emitter_rate_instant": {"num_particles": "math.clamp(v.size * 14, 8, 70)"},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_sphere": {"radius": "math.max(v.size * 0.5, 0.4)", "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.9, 1.8)"},
        "minecraft:particle_initial_speed": "math.random(3, 10)",
        "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-600, 600)"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -12, 0], "linear_drag_coefficient": 0.6},
        "minecraft:particle_motion_collision": {"collision_drag": 5, "coefficient_of_restitution": 0.35, "collision_radius": 0.08},
        "minecraft:particle_appearance_billboard": {"size": ["0.14 + v.particle_random_1 * 0.18", "0.24 + v.particle_random_1 * 0.24"], "facing_camera_mode": "rotate_xyz", "uv": uv("shard")},
        "minecraft:particle_appearance_tinting": fade([0.85, 0.6, 1.0, 1.0], [0.55, 0.3, 1.0, 0.0], [0.75, 0.5, 1.0, 1.0]),
    })
    E["mm_heart_glow"] = effect("anatomy:mm_heart_glow", "particles_add", {
        "minecraft:emitter_rate_steady": {"spawn_rate": "v.intensity > 0 ? 8 + v.intensity * 20 : 8", "max_particles": 80},
        "minecraft:emitter_lifetime_looping": {"active_time": 1},
        "minecraft:emitter_shape_sphere": {"radius": 3.2, "surface_only": True, "direction": "inwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.4},
        "minecraft:particle_initial_speed": 1.8,
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 0.6},
        "minecraft:particle_appearance_billboard": {"size": [0.16, 0.16], "facing_camera_mode": "lookat_xyz", "uv": uv("mote")},
        "minecraft:particle_appearance_tinting": fade([0.7, 0.4, 1.0, 0.0], [1.0, 0.85, 1.0, 0.0], [0.9, 0.65, 1.0, 1.0]),
    })
    E["mm_shield"] = effect("anatomy:mm_shield", "particles_add", {
        "minecraft:emitter_rate_instant": {"num_particles": 40},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_sphere": {"radius": "math.max(v.radius, 1)", "surface_only": True, "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.5, 0.9)"},
        "minecraft:particle_initial_speed": 0.05,
        "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)"},
        "minecraft:particle_appearance_billboard": {"size": [0.45, 0.45], "facing_camera_mode": "lookat_xyz", "uv": uv("hex")},
        "minecraft:particle_appearance_tinting": fade([0.6, 0.35, 1.0, 0.0], [0.6, 0.35, 1.0, 0.0], [0.75, 0.5, 1.0, 0.7]),
    })
    E["mm_safe"] = effect("anatomy:mm_safe", "particles_add", {
        "minecraft:emitter_rate_instant": {"num_particles": 6},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_disc": {"radius": "math.max(v.radius, 0.5)", "plane_normal": "y", "surface_only": True, "direction": [0, 1, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.9},
        "minecraft:particle_initial_speed": 2.2,
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 1.0},
        "minecraft:particle_appearance_billboard": {"size": [0.18, 0.4], "facing_camera_mode": "lookat_y", "uv": uv("mote")},
        "minecraft:particle_appearance_tinting": fade([0.45, 1.0, 0.75, 1.0], [0.3, 0.9, 1.0, 0.0]),
    })
    E["mm_vent"] = effect("anatomy:mm_vent", "particles_blend", {
        "minecraft:emitter_rate_instant": {"num_particles": 16},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_disc": {"radius": 0.8, "plane_normal": "y", "direction": [0, 1, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.8, 1.6)"},
        "minecraft:particle_initial_speed": "math.random(6, 12)",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -4, 0], "linear_drag_coefficient": 1.2},
        "minecraft:particle_appearance_billboard": {"size": ["0.4 + v.particle_age", "0.4 + v.particle_age"], "facing_camera_mode": "lookat_xyz", "uv": uv("blob")},
        "minecraft:particle_appearance_tinting": fade([1.0, 0.6, 0.3, 0.9], [0.5, 0.45, 0.45, 0.0], [0.9, 0.5, 0.4, 0.6]),
    })
    E["mm_leaf"] = effect("anatomy:mm_leaf", "particles_alpha", {
        "minecraft:emitter_rate_instant": {"num_particles": 10},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_box": {"half_dimensions": [1.5, 1.5, 1.5], "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(2, 4)"},
        "minecraft:particle_initial_speed": "math.random(0.5, 2)",
        "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-120, 120)"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": ["math.sin(v.particle_age * 200) * 2", -1.4, 0], "linear_drag_coefficient": 1.8},
        "minecraft:particle_motion_collision": {"collision_drag": 10, "coefficient_of_restitution": 0, "collision_radius": 0.05},
        "minecraft:particle_appearance_billboard": {"size": [0.12, 0.12], "facing_camera_mode": "rotate_xyz", "uv": uv("leaf")},
        "minecraft:particle_appearance_tinting": {"color": [0.3, 0.55, 0.22, 1.0]},
        "minecraft:particle_appearance_lighting": {},
    })
    E["mm_guide"] = effect("anatomy:mm_guide", "particles_add", {
        "minecraft:emitter_rate_instant": {"num_particles": 2},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_sphere": {"radius": 0.6, "direction": [0, 1, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.6},
        "minecraft:particle_initial_speed": 0.4,
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 0.5},
        "minecraft:particle_appearance_billboard": {"size": [0.12, 0.12], "facing_camera_mode": "lookat_xyz", "uv": uv("mote")},
        "minecraft:particle_appearance_tinting": fade([1.0, 0.85, 0.45, 0.0], [1.0, 0.85, 0.45, 0.0], [1.0, 0.9, 0.55, 0.9]),
    })
    E["mm_pillar"] = effect("anatomy:mm_pillar", "particles_add", {
        "minecraft:emitter_rate_instant": {"num_particles": 1},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {"offset": [0, 2.5, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.max(v.life, 0.3)"},
        "minecraft:particle_appearance_billboard": {"size": ["math.max(v.radius, 0.5)", 3.0], "facing_camera_mode": "lookat_y", "uv": uv("pillar")},
        "minecraft:particle_appearance_tinting": fade([0.4, 1.0, 0.7, 0.0], [0.4, 1.0, 0.8, 0.0], [0.45, 1.0, 0.75, 0.75]),
    })
    # a tall soft light pillar over each remaining Resonance Node (downwards for the hanging one)
    E["mm_node_beacon"] = effect("anatomy:mm_node_beacon", "particles_add", {
        "minecraft:emitter_rate_instant": {"num_particles": 1},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {"offset": [0, "12 * v.up", 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.2},
        "minecraft:particle_appearance_billboard": {"size": [1.1, 12.0], "facing_camera_mode": "lookat_y", "uv": uv("pillar")},
        "minecraft:particle_appearance_tinting": fade([0.8, 0.4, 1.0, 0.0], [0.75, 0.35, 1.0, 0.0], [0.85, 0.45, 1.0, 0.85]),
    })
    return E


def main(out_rp: str) -> None:
    os.makedirs(os.path.join(out_rp, "particles"), exist_ok=True)
    os.makedirs(os.path.join(out_rp, "textures", "particle"), exist_ok=True)
    build_atlas().save(os.path.join(out_rp, "textures", "particle", "anatomy_particles.png"))
    for name, data in effects().items():
        with open(os.path.join(out_rp, "particles", f"{name}.particle.json"), "w") as fh:
            json.dump(data, fh, indent=1)
    print(f"particles: {len(effects())} effects")


if __name__ == "__main__":
    main(sys.argv[1])
