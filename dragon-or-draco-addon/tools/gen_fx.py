#!/usr/bin/env python3
"""
Particles + particle texture + client entity + render controllers for the Red Dragon.

    RP particles/*.json                   (dod:* particle effects)
    RP textures/particle/dod_fx.png       (128x128 atlas painted here)
    RP entity/red_dragon.entity.json      (client entity)
    RP render_controllers/red_dragon.render_controllers.json

Performance budget (iPhone): every emitter is finite (emitter_lifetime_once / looping with
a short active time and max_particles caps), particle lifetimes are <= 2 s, and nothing is
spawned as an entity.  The fire breath's heavy element is the flame-jet geometry, which costs
17 cubes, not particles.  Worst case measured by the smoke test is reported in the README.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "dragon_or_draco")
TEX = "textures/particle/dod_fx"

# atlas layout (128 x 128)
FLAME = (0, 0)      # 4 frames 16x16 along x
SMOKE = (0, 16)     # 4 frames
DUST = (0, 32)      # 4 frames
GLOW = (64, 0)      # 32x32
SPARK = (96, 0)     # 8x8
EMBER = (104, 0)    # 8x8
WISP = (64, 32)     # 32x16


# ----------------------------------------------------------------------------- atlas

def radial(n, power=1.0):
    y, x = np.mgrid[0:n, 0:n] + 0.5
    d = np.sqrt((x - n / 2) ** 2 + (y - n / 2) ** 2) / (n / 2)
    return np.clip(1 - d, 0, 1) ** power


def paint_atlas():
    rng = np.random.default_rng(11)
    img = np.zeros((128, 128, 4), dtype=float)

    def put(x, y, rgba):
        h, w = rgba.shape[:2]
        img[y:y + h, x:x + w] = rgba

    # flames: white-hot core, ragged edge, 4 frames getting wispier (tinted by particles)
    for f in range(4):
        n = 16
        yy, xx = np.mgrid[0:n, 0:n] + 0.5
        cx, cy = n / 2, n / 2 + 1
        d = np.sqrt(((xx - cx) / 7.0) ** 2 + ((yy - cy) / (7.5 - f * 0.6)) ** 2)
        noise = rng.random((n, n)) * (0.35 + f * 0.12)
        a = np.clip(1.15 - d - noise + (yy < cy) * 0.0, 0, 1)
        a = np.where(a > 0.12, a, 0)
        core = np.clip(1 - d * 1.7, 0, 1)
        col = np.stack([np.ones_like(a), 0.55 + core * 0.45, 0.25 + core * 0.7], -1)
        put(FLAME[0] + f * 16, FLAME[1], np.concatenate([col, a[..., None]], -1))
    # smoke puffs: soft grey blobs
    for f in range(4):
        n = 16
        base = radial(n, 0.8)
        noise = rng.random((n, n)) * 0.25
        a = np.clip(base * 1.3 - noise - f * 0.08, 0, 1) * 0.85
        col = np.full((n, n, 3), 0.55 + 0.1 * f) * (0.85 + 0.15 * rng.random((n, n, 1)))
        put(SMOKE[0] + f * 16, SMOKE[1], np.concatenate([col, a[..., None]], -1))
    # dust (warm stone colour, tinted further in JSON)
    for f in range(4):
        n = 16
        base = radial(n, 0.6)
        speck = rng.random((n, n))
        a = np.clip(base * 1.4 - speck * 0.5 - f * 0.12, 0, 1)
        col = np.stack([np.full((n, n), 0.82), np.full((n, n), 0.72), np.full((n, n), 0.6)], -1)
        put(DUST[0] + f * 16, DUST[1], np.concatenate([col, a[..., None]], -1))
    # glow
    g = radial(32, 1.8)
    put(GLOW[0], GLOW[1], np.concatenate([np.ones((32, 32, 3)), g[..., None]], -1))
    # spark (bright pixel cross) and ember (round)
    s = np.zeros((8, 8, 4))
    s[3:5, :, :] = [1, 1, 1, 1]
    s[:, 3:5, :] = [1, 1, 1, 1]
    s[2:6, 2:6, 3] = np.maximum(s[2:6, 2:6, 3], 0.6)
    put(SPARK[0], SPARK[1], s)
    e = radial(8, 0.7)
    put(EMBER[0], EMBER[1], np.concatenate([np.ones((8, 8, 3)), np.clip(e * 1.6, 0, 1)[..., None]], -1))
    # wind wisp: a soft horizontal streak
    yy, xx = np.mgrid[0:16, 0:32] + 0.5
    a = np.clip(1 - np.abs(yy - 8 - np.sin(xx / 32 * math.pi * 2) * 2) / 3.5, 0, 1) * np.sin(xx / 32 * math.pi)
    put(WISP[0], WISP[1], np.concatenate([np.ones((16, 32, 3)), (a * 0.9)[..., None]], -1))
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


# ----------------------------------------------------------------------------- particle helpers

def billboard(size, uv, uv_size, flip=None, facing="rotate_xyz", direction=None):
    b = {"size": size, "facing_camera_mode": facing,
         "uv": {"texture_width": 128, "texture_height": 128}}
    if flip:
        b["uv"]["flipbook"] = {"base_UV": list(uv), "size_UV": list(uv_size), "step_UV": [uv_size[0], 0],
                               "max_frame": flip, "stretch_to_lifetime": True}
    else:
        b["uv"]["uv"] = list(uv)
        b["uv"]["uv_size"] = list(uv_size)
    if direction:
        b["direction"] = direction
    return b


def tint(stops):
    return {"color": {"interpolant": "v.particle_age / v.particle_lifetime", "gradient": stops}}


def effect(ident, material, components):
    return {
        "format_version": "1.10.0",
        "particle_effect": {
            "description": {"identifier": ident, "basic_render_parameters": {"material": material, "texture": TEX}},
            "components": components,
        },
    }


FIRE_TINT = tint({"0.0": "#FFFFF4C8", "0.18": "#FFFFCD57", "0.45": "#FFFF6B1E", "0.75": "#E0B8281A",
                  "1.0": "#00401010"})
SMOKE_TINT = tint({"0.0": "#B0402A26", "0.4": "#A0302424", "1.0": "#00181414"})

PARTICLES = {}

# 1) charge glow at the mouth: pulsing glow + sparks drawn inward (follows the head: position local)
PARTICLES["fire_charge_glow"] = effect("dod:fire_charge_glow", "particles_add", {
    "minecraft:emitter_local_space": {"position": True, "rotation": False},
    "minecraft:emitter_lifetime_once": {"active_time": 1.3},
    "minecraft:emitter_rate_steady": {"spawn_rate": 26, "max_particles": 30},
    "minecraft:emitter_shape_sphere": {"radius": 1.4, "surface_only": True, "direction": "inwards"},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.25, 0.45)"},
    "minecraft:particle_initial_speed": "math.random(2.5, 4)",
    "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 1.0},
    "minecraft:particle_appearance_billboard": billboard(["0.12 + v.emitter_age * 0.05", "0.12 + v.emitter_age * 0.05"],
                                                         EMBER, (8, 8)),
    "minecraft:particle_appearance_tinting": tint({"0.0": "#00FFCD57", "0.3": "#FFFFCD57", "1.0": "#FFFF6B1E"}),
})
PARTICLES["fire_charge_core"] = effect("dod:fire_charge_core", "particles_add", {
    "minecraft:emitter_local_space": {"position": True, "rotation": False},
    "minecraft:emitter_lifetime_once": {"active_time": 1.3},
    "minecraft:emitter_rate_steady": {"spawn_rate": 10, "max_particles": 6},
    "minecraft:emitter_shape_point": {},
    "minecraft:particle_lifetime_expression": {"max_lifetime": 0.35},
    "minecraft:particle_appearance_billboard": billboard(
        ["(0.6 + v.emitter_age * 0.9) * (1 + math.sin(v.particle_age * 1400) * 0.15)",
         "(0.6 + v.emitter_age * 0.9) * (1 + math.sin(v.particle_age * 1400) * 0.15)"], GLOW, (32, 32)),
    "minecraft:particle_appearance_tinting": tint({"0.0": "#00FF6B1E", "0.4": "#C8FF8A2A", "1.0": "#00FF6B1E"}),
})

# 2) mouth burst while breathing (world space puffs around the mouth, no direction needed)
PARTICLES["fire_mouth_burst"] = effect("dod:fire_mouth_burst", "particles_blend", {
    "minecraft:emitter_lifetime_once": {"active_time": 0.8},
    "minecraft:emitter_rate_steady": {"spawn_rate": 18, "max_particles": 14},
    "minecraft:emitter_shape_sphere": {"radius": 0.5, "direction": "outwards"},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.3, 0.5)"},
    "minecraft:particle_initial_speed": "math.random(0.6, 1.6)",
    "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 2.5, 0], "linear_drag_coefficient": 2.0},
    "minecraft:particle_appearance_billboard": billboard(["0.5 + v.particle_age * 2.2", "0.5 + v.particle_age * 2.2"],
                                                         FLAME, (16, 16), flip=4),
    "minecraft:particle_appearance_tinting": FIRE_TINT,
})

# 3) flame jet puffs spawned by the script along the aim, direction/speed from variable.jet
PARTICLES["fire_jet"] = effect("dod:fire_jet", "particles_blend", {
    "minecraft:emitter_lifetime_once": {},
    "minecraft:emitter_rate_instant": {"num_particles": 4},
    "minecraft:emitter_shape_sphere": {
        "radius": "0.25 + v.jet_spread",
        "direction": ["variable.jet.direction_x + math.random(-0.12, 0.12)",
                      "variable.jet.direction_y + math.random(-0.12, 0.12)",
                      "variable.jet.direction_z + math.random(-0.12, 0.12)"],
    },
    "minecraft:emitter_initialization": {"creation_expression":
                                         "variable.jet.speed ?? { variable.jet.speed = 10; }; v.jet_spread = 0.2;"},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.32, 0.5)"},
    "minecraft:particle_initial_speed": "variable.jet.speed * math.random(0.8, 1.1)",
    "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 3, 0], "linear_drag_coefficient": 2.4},
    "minecraft:particle_appearance_billboard": billboard(["0.6 + v.particle_age * 4.5", "0.6 + v.particle_age * 4.5"],
                                                         FLAME, (16, 16), flip=4),
    "minecraft:particle_appearance_tinting": FIRE_TINT,
})

# 4) impact where the jet meets a surface or a target
PARTICLES["fire_impact"] = effect("dod:fire_impact", "particles_blend", {
    "minecraft:emitter_lifetime_once": {},
    "minecraft:emitter_rate_instant": {"num_particles": 6},
    "minecraft:emitter_shape_sphere": {"radius": 0.6, "direction": "outwards"},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.4, 0.7)"},
    "minecraft:particle_initial_speed": "math.random(0.8, 2.2)",
    "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 3.5, 0], "linear_drag_coefficient": 2.0},
    "minecraft:particle_appearance_billboard": billboard(["0.5 + v.particle_age * 2.4", "0.5 + v.particle_age * 2.4"],
                                                         FLAME, (16, 16), flip=4),
    "minecraft:particle_appearance_tinting": FIRE_TINT,
})
PARTICLES["embers"] = effect("dod:embers", "particles_add", {
    "minecraft:emitter_lifetime_once": {},
    "minecraft:emitter_rate_instant": {"num_particles": 5},
    "minecraft:emitter_shape_sphere": {"radius": 0.8, "direction": [0, 1, 0]},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.6, 1.2)"},
    "minecraft:particle_initial_speed": "math.random(1.0, 2.5)",
    "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.2, 0], "linear_drag_coefficient": 1.2},
    "minecraft:particle_appearance_billboard": billboard([0.09, 0.09], EMBER, (8, 8)),
    "minecraft:particle_appearance_tinting": tint({"0.0": "#FFFFF0B0", "0.5": "#FFFF8A2A", "1.0": "#00B8281A"}),
})
PARTICLES["smoke"] = effect("dod:smoke", "particles_alpha", {
    "minecraft:emitter_lifetime_once": {},
    "minecraft:emitter_rate_instant": {"num_particles": 3},
    "minecraft:emitter_shape_sphere": {"radius": 0.6, "direction": [0, 1, 0]},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.9, 1.5)"},
    "minecraft:particle_initial_speed": "math.random(0.6, 1.4)",
    "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.8, 0], "linear_drag_coefficient": 1.0},
    "minecraft:particle_appearance_billboard": billboard(["0.6 + v.particle_age * 1.6", "0.6 + v.particle_age * 1.6"],
                                                         SMOKE, (16, 16), flip=4),
    "minecraft:particle_appearance_tinting": SMOKE_TINT,
    "minecraft:particle_appearance_lighting": {},
})

# 5) nostril smoke (follows the head position)
PARTICLES["nostril_smoke"] = effect("dod:nostril_smoke", "particles_alpha", {
    "minecraft:emitter_local_space": {"position": True, "rotation": False},
    "minecraft:emitter_lifetime_once": {"active_time": 0.5},
    "minecraft:emitter_rate_steady": {"spawn_rate": 8, "max_particles": 5},
    "minecraft:emitter_shape_point": {"direction": [0, 1, 0]},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.8, 1.2)"},
    "minecraft:particle_initial_speed": 0.5,
    "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.6, 0], "linear_drag_coefficient": 0.8},
    "minecraft:particle_appearance_billboard": billboard(["0.18 + v.particle_age * 0.5", "0.18 + v.particle_age * 0.5"],
                                                         SMOKE, (16, 16), flip=4),
    "minecraft:particle_appearance_tinting": tint({"0.0": "#90554A48", "1.0": "#00302828"}),
    "minecraft:particle_appearance_lighting": {},
})

# 6) roar: hot breath cloud + embers bursting around the mouth (spherical, direction independent)
PARTICLES["roar_breath"] = effect("dod:roar_breath", "particles_blend", {
    "minecraft:emitter_lifetime_once": {"active_time": 0.8},
    "minecraft:emitter_rate_steady": {"spawn_rate": 22, "max_particles": 18},
    "minecraft:emitter_shape_sphere": {"radius": 0.4, "direction": "outwards"},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.5, 0.9)"},
    "minecraft:particle_initial_speed": "math.random(1.5, 3.0)",
    "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.0, 0], "linear_drag_coefficient": 2.2},
    "minecraft:particle_appearance_billboard": billboard(["0.4 + v.particle_age * 1.8", "0.4 + v.particle_age * 1.8"],
                                                         SMOKE, (16, 16), flip=4),
    "minecraft:particle_appearance_tinting": tint({"0.0": "#C0FF8A2A", "0.25": "#A0A04030", "1.0": "#00302828"}),
})

# 7) dust ring on the ground (horizontal disc: yaw independent)
PARTICLES["dust_ring"] = effect("dod:dust_ring", "particles_alpha", {
    "minecraft:emitter_lifetime_once": {},
    "minecraft:emitter_rate_instant": {"num_particles": 22},
    "minecraft:emitter_shape_disc": {"radius": 2.5, "plane_normal": "y", "surface_only": True, "direction": "outwards"},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.8, 1.3)"},
    "minecraft:particle_initial_speed": "math.random(2.5, 5)",
    "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.4, 0], "linear_drag_coefficient": 2.6},
    "minecraft:particle_appearance_billboard": billboard(["0.7 + v.particle_age * 1.6", "0.7 + v.particle_age * 1.6"],
                                                         DUST, (16, 16), flip=4),
    "minecraft:particle_appearance_tinting": tint({"0.0": "#C09A8670", "1.0": "#005A4E44"}),
    "minecraft:particle_appearance_lighting": {},
})

# 7b) small dust puff where a foot lands or a claw rakes the ground (horizontal disc, yaw independent)
PARTICLES["dust_puff"] = effect("dod:dust_puff", "particles_alpha", {
    "minecraft:emitter_lifetime_once": {},
    "minecraft:emitter_rate_instant": {"num_particles": 5},
    "minecraft:emitter_shape_disc": {"radius": 0.5, "plane_normal": "y", "direction": "outwards"},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.5, 0.9)"},
    "minecraft:particle_initial_speed": "math.random(0.8, 1.8)",
    "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.5, 0], "linear_drag_coefficient": 2.8},
    "minecraft:particle_appearance_billboard": billboard(["0.35 + v.particle_age * 0.9", "0.35 + v.particle_age * 0.9"],
                                                         DUST, (16, 16), flip=4),
    "minecraft:particle_appearance_tinting": tint({"0.0": "#A09A8670", "1.0": "#005A4E44"}),
    "minecraft:particle_appearance_lighting": {},
})

# 8) claw slash sparks + dust at the swiping foot
PARTICLES["claw_slash"] = effect("dod:claw_slash", "particles_add", {
    "minecraft:emitter_lifetime_once": {},
    "minecraft:emitter_rate_instant": {"num_particles": 12},
    "minecraft:emitter_shape_sphere": {"radius": 0.5, "direction": "outwards"},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.2, 0.4)"},
    "minecraft:particle_initial_speed": "math.random(3, 6)",
    "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -6, 0], "linear_drag_coefficient": 1.5},
    "minecraft:particle_appearance_billboard": billboard([0.1, 0.1], SPARK, (8, 8)),
    "minecraft:particle_appearance_tinting": tint({"0.0": "#FFFFF4C8", "1.0": "#00FF6B1E"}),
})

# 9) wing buffet gust: wisps rushing outward on a horizontal disc at chest height
PARTICLES["wind_burst"] = effect("dod:wind_burst", "particles_alpha", {
    "minecraft:emitter_lifetime_once": {},
    "minecraft:emitter_rate_instant": {"num_particles": 18},
    "minecraft:emitter_shape_disc": {"radius": 1.5, "plane_normal": "y", "direction": "outwards"},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.45, 0.7)"},
    "minecraft:particle_initial_speed": "math.random(8, 12)",
    "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 3.0},
    "minecraft:particle_appearance_billboard": billboard([1.4, 0.7], WISP, (32, 16), facing="lookat_direction",
                                                         direction={"mode": "derive_from_velocity",
                                                                    "min_speed_threshold": 0.05}),
    "minecraft:particle_appearance_tinting": tint({"0.0": "#A0FFF0E0", "1.0": "#00FFFFFF"}),
})

# 10) death embers rising from the body
PARTICLES["death_embers"] = effect("dod:death_embers", "particles_add", {
    "minecraft:emitter_lifetime_once": {"active_time": 1.6},
    "minecraft:emitter_rate_steady": {"spawn_rate": 16, "max_particles": 28},
    "minecraft:emitter_shape_box": {"half_dimensions": [2.5, 1.0, 4.0], "direction": [0, 1, 0]},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(1.0, 1.8)"},
    "minecraft:particle_initial_speed": "math.random(0.6, 1.6)",
    "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.6, 0], "linear_drag_coefficient": 0.6},
    "minecraft:particle_appearance_billboard": billboard([0.11, 0.11], EMBER, (8, 8)),
    "minecraft:particle_appearance_tinting": tint({"0.0": "#FFFFCD57", "0.6": "#FFFF6B1E", "1.0": "#00601010"}),
})


# ----------------------------------------------------------------------------- client entity + render controllers

PFX = {"fire_charge_glow": "dod:fire_charge_glow", "fire_charge_core": "dod:fire_charge_core",
       "fire_mouth_burst": "dod:fire_mouth_burst", "nostril_smoke": "dod:nostril_smoke", "roar_breath": "dod:roar_breath",
       "dust_ring": "dod:dust_ring", "dust_puff": "dod:dust_puff", "claw_slash": "dod:claw_slash",
       "wind_burst": "dod:wind_burst", "death_embers": "dod:death_embers"}
CONTROLLER_KEYS = {
    "move_controller": "controller.animation.dod.red_dragon.move",
    "idle_controller": "controller.animation.dod.red_dragon.idle",
    "action_controller": "controller.animation.dod.red_dragon.action",
    "look_controller": "controller.animation.dod.red_dragon.look",
    "blink_controller": "controller.animation.dod.red_dragon.blink",
    "hurt_controller": "controller.animation.dod.red_dragon.hurt",
}


def client_entity():
    man = json.load(open(os.path.join(ROOT, "tools", "anim_manifest.json")))
    prefix = "animation.dod.red_dragon."
    anims = {a[len(prefix):]: a for a in man["animations"]}
    anims.update(CONTROLLER_KEYS)
    missing = [k for k in man["particle_keys"] if k not in PFX]
    assert not missing, f"particle keys without an effect: {missing}"
    return {
        "format_version": "1.10.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": "dod:red_dragon",
                "materials": {"default": "entity_emissive", "fire": "entity_beam_additive"},
                "textures": {"default": "textures/entity/red_dragon", "fire": "textures/entity/red_dragon_fire"},
                "geometry": {"default": "geometry.dod.red_dragon", "fire": "geometry.dod.red_dragon_fire"},
                "scripts": {
                    "pre_animation": man["pre_animation"],
                    "animate": list(CONTROLLER_KEYS),
                    "should_update_bones_and_effects_offscreen": "1.0",
                },
                "animations": anims,
                "particle_effects": PFX,
                "sound_effects": {k: f"mob.dod.red_dragon.{k}" for k in man["sound_keys"]},
                "render_controllers": [
                    "controller.render.dod.red_dragon",
                    {"controller.render.dod.red_dragon_fire": "q.property('dod:action') == 'fire_breath'"},
                ],
                "spawn_egg": {"texture": "dod_red_dragon_spawn_egg"},
                "enable_attachables": False,
            }
        },
    }


def render_controllers():
    return {
        "format_version": "1.8.0",
        "render_controllers": {
            "controller.render.dod.red_dragon": {
                "geometry": "Geometry.default",
                "materials": [{"*": "Material.default"}],
                "textures": ["Texture.default"],
            },
            "controller.render.dod.red_dragon_fire": {
                "geometry": "Geometry.fire",
                "materials": [{"*": "Material.fire"}],
                "textures": ["Texture.fire"],
                "uv_anim": {"offset": [0.0, "q.life_time * -1.8"], "scale": [1.0, 1.0]},
                "is_hurt_color": {"r": 0.0, "g": 0.0, "b": 0.0, "a": 0.0},
            },
        },
    }


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def main():
    pdir = os.path.join(RP, "particles")
    os.makedirs(pdir, exist_ok=True)
    for f in os.listdir(pdir):
        if f.endswith(".json"):
            os.remove(os.path.join(pdir, f))
    for name, data in PARTICLES.items():
        write(os.path.join(pdir, f"{name}.json"), data)
    os.makedirs(os.path.join(RP, "textures", "particle"), exist_ok=True)
    Image.fromarray(paint_atlas(), "RGBA").save(os.path.join(RP, f"{TEX}.png"))
    write(os.path.join(RP, "entity", "red_dragon.entity.json"), client_entity())
    write(os.path.join(RP, "render_controllers", "red_dragon.render_controllers.json"), render_controllers())
    print(f"{len(PARTICLES)} particles, client entity, render controllers")


if __name__ == "__main__":
    main()
