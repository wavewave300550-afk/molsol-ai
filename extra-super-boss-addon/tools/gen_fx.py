#!/usr/bin/env python3
"""Particle effects (RP particles/*.json). All use the 64 x 64 atlas textures/particle/esb_fx.png
(written by gen_art.py): cells of 16 px - (0,0) spark, (1,0) glow dot, (2,0) gear, (3,0) page,
(0,1) smoke, (1,1) ring, (2,1) ink blot, (3,1) streak."""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "extra_super_boss")
TEX = "textures/particle/esb_fx"


def cell(i, j):
    return {"texture_width": 64, "texture_height": 64, "uv": [i * 16, j * 16], "uv_size": [16, 16]}


def particle(ident, material, comps):
    return {"format_version": "1.10.0", "particle_effect": {
        "description": {"identifier": ident, "basic_render_parameters": {"material": material, "texture": TEX}},
        "components": comps}}


def once(n, active=0.05):
    return {"minecraft:emitter_rate_instant": {"num_particles": n},
            "minecraft:emitter_lifetime_once": {"active_time": active}}


FADE = "(1 - v.particle_age / v.particle_lifetime)"

EFFECTS = {
    # gold sparks: hits, gauntlet bursts, compass slash
    "gold_spark": particle("esb:gold_spark", "particles_add", {
        **once(16),
        "minecraft:emitter_shape_sphere": {"radius": 0.25, "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.35, 0.75)"},
        "minecraft:particle_initial_speed": "math.random(3, 8)",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -7, 0], "linear_drag_coefficient": 2.4},
        "minecraft:particle_appearance_billboard": {"size": [f"0.16 * {FADE} + 0.03", f"0.16 * {FADE} + 0.03"],
                                                    "facing_camera_mode": "rotate_xyz", "uv": cell(0, 0)},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.82, 0.42, 1.0]},
    }),
    # steam venting from the gauntlet
    "steam_puff": particle("esb:steam_puff", "particles_blend", {
        **once(7),
        "minecraft:emitter_shape_sphere": {"radius": 0.15, "direction": [0, 1, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.8, 1.4)"},
        "minecraft:particle_initial_speed": "math.random(0.6, 1.6)",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.2, 0], "linear_drag_coefficient": 1.5},
        "minecraft:particle_appearance_billboard": {"size": ["0.18 + v.particle_age * 0.6", "0.18 + v.particle_age * 0.6"],
                                                    "facing_camera_mode": "rotate_xyz", "uv": cell(0, 1)},
        "minecraft:particle_appearance_tinting": {"color": [0.95, 0.93, 0.9, f"0.7 * {FADE}"]},
    }),
    # sketchbook pages bursting out (intro, transform, death, summon)
    "page_burst": particle("esb:page_burst", "particles_alpha", {
        **once(22),
        "minecraft:emitter_shape_sphere": {"radius": 0.6, "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(1.6, 2.8)"},
        "minecraft:particle_initial_speed": "math.random(2.5, 6)",
        "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-240, 240)"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -1.2, 0], "linear_drag_coefficient": 2.0},
        "minecraft:particle_appearance_billboard": {"size": [0.22, 0.26], "facing_camera_mode": "rotate_xyz", "uv": cell(3, 0)},
        "minecraft:particle_appearance_lighting": {},
    }),
    # glints behind a flying gear
    "gear_trail": particle("esb:gear_trail", "particles_add", {
        **once(3),
        "minecraft:emitter_shape_sphere": {"radius": 0.2},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.35},
        "minecraft:particle_initial_speed": 0.2,
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_appearance_billboard": {"size": [f"0.14 * {FADE}", f"0.14 * {FADE}"],
                                                    "facing_camera_mode": "rotate_xyz", "uv": cell(1, 0)},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.72, 0.3, 1.0]},
    }),
    # quake: flat expanding ring on the ground + dust thrown outward
    "shockwave": particle("esb:shockwave", "particles_add", {
        **once(1),
        "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.5},
        "minecraft:particle_initial_speed": 0,
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_appearance_billboard": {
            "size": ["0.4 + v.particle_age * (variable.radius ?? 6) * 4", "0.4 + v.particle_age * (variable.radius ?? 6) * 4"],
            "facing_camera_mode": "emitter_transform_xz", "uv": cell(1, 1)},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.78, 0.45, FADE]},
    }),
    "dust_ring": particle("esb:dust_ring", "particles_blend", {
        **once(40),
        "minecraft:emitter_shape_disc": {"plane_normal": [0, 1, 0], "radius": 0.6, "surface_only": True, "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.6, 1.1)"},
        "minecraft:particle_initial_speed": "math.random(7, 11)",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.5, 0], "linear_drag_coefficient": 3.2},
        "minecraft:particle_appearance_billboard": {"size": ["0.35 + v.particle_age * 0.9", "0.35 + v.particle_age * 0.9"],
                                                    "facing_camera_mode": "rotate_xyz", "uv": cell(0, 1)},
        "minecraft:particle_appearance_tinting": {"color": [0.62, 0.52, 0.42, f"0.85 * {FADE}"]},
        "minecraft:particle_appearance_lighting": {},
    }),
    # vitruvian: sparks rising from the edge of the circle while it charges
    "sigil_edge": particle("esb:sigil_edge", "particles_add", {
        **once(10),
        "minecraft:emitter_shape_disc": {"plane_normal": [0, 1, 0], "radius": "variable.radius ?? 7", "surface_only": True,
                                         "direction": [0, 1, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.6, 1.0)"},
        "minecraft:particle_initial_speed": "math.random(1.5, 3)",
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 0.8},
        "minecraft:particle_appearance_billboard": {"size": [0.1, 0.1], "facing_camera_mode": "rotate_xyz", "uv": cell(1, 0)},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.8, 0.4, FADE]},
    }),
    # vitruvian / dive detonation: a wall of golden light along the circle and a central column
    "sigil_burst": particle("esb:sigil_burst", "particles_add", {
        **once(70),
        "minecraft:emitter_shape_disc": {"plane_normal": [0, 1, 0], "radius": "variable.radius ?? 7",
                                         "direction": [0, 1, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.6, 1.2)"},
        "minecraft:particle_initial_speed": "math.random(5, 11)",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -3, 0], "linear_drag_coefficient": 1.6},
        "minecraft:particle_appearance_billboard": {"size": [0.08, f"0.5 * {FADE} + 0.1"], "facing_camera_mode": "lookat_y",
                                                    "uv": cell(3, 1)},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.84, 0.48, 1.0]},
    }),
    # summoning / intro column: gears and sparks spiralling up
    "summon_pillar": particle("esb:summon_pillar", "particles_add", {
        "minecraft:emitter_rate_steady": {"spawn_rate": 40, "max_particles": 80},
        "minecraft:emitter_lifetime_once": {"active_time": 1.6},
        "minecraft:emitter_shape_disc": {"plane_normal": [0, 1, 0], "radius": 1.4, "surface_only": True, "direction": [0, 1, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.9, 1.5)"},
        "minecraft:particle_initial_speed": "math.random(2, 4)",
        "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": 200},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 0.6},
        "minecraft:particle_appearance_billboard": {"size": [0.16, 0.16], "facing_camera_mode": "rotate_xyz", "uv": cell(2, 0)},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.76, 0.36, FADE]},
    }),
    # ---------------------------------------------------------------- Edison: DC amber, AC blue (variable.ac = 1)
    "volt_spark": particle("esb:volt_spark", "particles_add", {
        **once(12),
        "minecraft:emitter_shape_sphere": {"radius": 0.2, "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.15, 0.4)"},
        "minecraft:particle_initial_speed": "math.random(3, 9)",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -4, 0], "linear_drag_coefficient": 4},
        "minecraft:particle_appearance_billboard": {"size": [0.05, f"0.22 * {FADE} + 0.05"], "facing_camera_mode": "lookat_direction",
                                                    "direction": {"mode": "velocity"}, "uv": cell(3, 1)},
        "minecraft:particle_appearance_tinting": {"color": ["(variable.ac ?? 0) > 0.5 ? 0.65 : 1.0", "(variable.ac ?? 0) > 0.5 ? 0.9 : 0.8",
                                                            "(variable.ac ?? 0) > 0.5 ? 1.0 : 0.4", 1.0]},
    }),
    "zap": particle("esb:zap", "particles_add", {
        **once(1),
        "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.25},
        "minecraft:particle_initial_speed": 0,
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_appearance_billboard": {"size": [f"0.32 * {FADE} + 0.06", f"0.32 * {FADE} + 0.06"],
                                                    "facing_camera_mode": "rotate_xyz", "uv": cell(1, 0)},
        "minecraft:particle_appearance_tinting": {"color": ["(variable.ac ?? 0) > 0.5 ? 0.7 : 1.0", "(variable.ac ?? 0) > 0.5 ? 0.92 : 0.85",
                                                            "(variable.ac ?? 0) > 0.5 ? 1.0 : 0.5", 1.0]},
    }),
    "glass_shards": particle("esb:glass_shards", "particles_blend", {
        **once(14),
        "minecraft:emitter_shape_sphere": {"radius": 0.15, "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.5, 0.9)"},
        "minecraft:particle_initial_speed": "math.random(2, 5)",
        "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-500, 500)"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -14, 0], "linear_drag_coefficient": 1},
        "minecraft:particle_appearance_billboard": {"size": [0.07, 0.07], "facing_camera_mode": "rotate_xyz", "uv": cell(0, 0)},
        "minecraft:particle_appearance_tinting": {"color": [0.9, 0.96, 1.0, 0.9]},
    }),
    "telegraph": particle("esb:telegraph", "particles_add", {
        **once(6),
        "minecraft:emitter_shape_disc": {"plane_normal": [0, 1, 0], "radius": 0.5, "direction": [0, 1, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.3, 0.6)"},
        "minecraft:particle_initial_speed": "math.random(1.5, 3.5)",
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 2},
        "minecraft:particle_appearance_billboard": {"size": [0.05, f"0.25 * {FADE} + 0.05"], "facing_camera_mode": "lookat_direction",
                                                    "direction": {"mode": "velocity"}, "uv": cell(3, 1)},
        "minecraft:particle_appearance_tinting": {"color": ["(variable.ac ?? 0) > 0.5 ? 0.6 : 1.0", "(variable.ac ?? 0) > 0.5 ? 0.85 : 0.75",
                                                            "(variable.ac ?? 0) > 0.5 ? 1.0 : 0.3", 1.0]},
    }),
    "blink_smoke": particle("esb:blink_smoke", "particles_blend", {
        **once(12),
        "minecraft:emitter_shape_sphere": {"radius": 0.7},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.6, 1.0)"},
        "minecraft:particle_initial_speed": "math.random(0.3, 1.2)",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.8, 0], "linear_drag_coefficient": 1.5},
        "minecraft:particle_appearance_billboard": {"size": ["0.4 + v.particle_age * 0.8", "0.4 + v.particle_age * 0.8"],
                                                    "facing_camera_mode": "rotate_xyz", "uv": cell(0, 1)},
        "minecraft:particle_appearance_tinting": {"color": [0.12, 0.11, 0.13, f"0.9 * {FADE}"]},
    }),
    # ---------------------------------------------------------------- ultimates
    "music_note": particle("esb:music_note", "particles_alpha", {
        **once(4),
        "minecraft:emitter_shape_sphere": {"radius": 0.8, "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(1.0, 1.6)"},
        "minecraft:particle_initial_speed": "math.random(1, 2.5)",
        "minecraft:particle_initial_spin": {"rotation": "math.random(-25, 25)", "rotation_rate": "math.random(-60, 60)"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.2, 0], "linear_drag_coefficient": 1.4},
        "minecraft:particle_appearance_billboard": {"size": [0.32, 0.32], "facing_camera_mode": "rotate_xyz",
                                                    "uv": {"texture_width": 64, "texture_height": 64,
                                                           "uv": [0, 32], "uv_size": [16, 16]}},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.86, 0.45, f"math.min(1, 3 * {FADE})"]},
    }),
    "path_dust": particle("esb:path_dust", "particles_blend", {
        **once(5),
        "minecraft:emitter_shape_disc": {"plane_normal": [0, 1, 0], "radius": 0.8, "direction": [0, 1, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.8, 1.4)"},
        "minecraft:particle_initial_speed": "math.random(0.5, 1.6)",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.6, 0], "linear_drag_coefficient": 1.5},
        "minecraft:particle_appearance_billboard": {"size": ["0.45 + v.particle_age * 0.7", "0.45 + v.particle_age * 0.7"],
                                                    "facing_camera_mode": "rotate_xyz", "uv": cell(0, 1)},
        "minecraft:particle_appearance_tinting": {"color": [0.72, 0.48, 0.34, f"0.8 * {FADE}"]},
        "minecraft:particle_appearance_lighting": {},
    }),
    "clay_chunks": particle("esb:clay_chunks", "particles_alpha", {
        **once(16),
        "minecraft:emitter_shape_box": {"half_dimensions": [1.5, 1.2, 2.5], "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.8, 1.5)"},
        "minecraft:particle_initial_speed": "math.random(1, 4)",
        "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-300, 300)"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -16, 0], "linear_drag_coefficient": 0.5},
        "minecraft:particle_motion_collision": {"coefficient_of_restitution": 0.2, "collision_drag": 4, "collision_radius": 0.1},
        "minecraft:particle_appearance_billboard": {"size": ["math.random(0.2, 0.45)", "math.random(0.2, 0.45)"],
                                                    "facing_camera_mode": "rotate_xyz", "uv": cell(2, 2)},
        "minecraft:particle_appearance_lighting": {},
    }),
}


def main():
    d = os.path.join(RP, "particles")
    os.makedirs(d, exist_ok=True)
    for name, data in EFFECTS.items():
        with open(os.path.join(d, f"{name}.json"), "w") as f:
            json.dump(data, f, indent=1)
            f.write("\n")
    print(f"particles: {len(EFFECTS)}")


if __name__ == "__main__":
    main()
