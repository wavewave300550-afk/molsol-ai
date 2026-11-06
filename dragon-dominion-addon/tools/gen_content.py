#!/usr/bin/env python3
"""
Everything in the two packs that is not the model or the animations:
manifests, behavior entity, client entity, render controller, items, particles (+ atlas), item icons,
pack icons, language files.

    python3 tools/gen_content.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
BP = os.path.join(ROOT, "addon", "behavior_packs", "dragon_dominion")
RP = os.path.join(ROOT, "addon", "resource_packs", "dragon_dominion")
NS = "dragon_dominion"
ID = f"{NS}:gharvok"
RIG = json.load(open(os.path.join(HERE, ".rig.json")))
AN = json.load(open(os.path.join(HERE, ".anim.json")))

VERSION = [1, 1, 0]
MIN_ENGINE = [1, 26, 60]          # Script API @minecraft/server 2.11.0 (current stable on npm) ships with 1.26.6x
SCRIPT_API = "2.11.0"
UUIDS = {  # generated once; never change them (players update packs in place by UUID)
    "bp": "5beff867-825e-487d-880e-a1d336104536",
    "bp_data": "1e635a49-4239-4d52-8e04-4d603ee93a26",
    "bp_script": "ff9141cb-2c0d-458e-af2d-3b0071617372",
    "rp": "bc3eee27-d96d-43a7-98b7-fa1e23547ba0",
    "rp_res": "029bc848-a7be-4172-8dec-d37ff2172e33",
}
SCALE = 0.76  # visual scale of the model (client entity); config.js geometry is measured at this scale


def wj(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=1)


# =========================================================================== manifests
def manifests():
    wj(os.path.join(BP, "manifest.json"), {
        "format_version": 2,
        "header": {"name": "Dragon Dominion", "description": "Behavior Pack - Boss 1: Gharvok, the Cliffbreaker (v1.1.0)",
                   "uuid": UUIDS["bp"], "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [
            {"type": "data", "uuid": UUIDS["bp_data"], "version": VERSION},
            {"type": "script", "language": "javascript", "uuid": UUIDS["bp_script"], "version": VERSION,
             "entry": "scripts/main.js"},
        ],
        "dependencies": [
            {"uuid": UUIDS["rp"], "version": VERSION},
            {"module_name": "@minecraft/server", "version": SCRIPT_API},
        ],
        "metadata": {"authors": ["Dragon Dominion"]},
    })
    wj(os.path.join(RP, "manifest.json"), {
        "format_version": 2,
        "header": {"name": "Dragon Dominion", "description": "Resource Pack - Boss 1: Gharvok, the Cliffbreaker (v1.1.0)",
                   "uuid": UUIDS["rp"], "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "resources", "uuid": UUIDS["rp_res"], "version": VERSION}],
        "metadata": {"authors": ["Dragon Dominion"]},
    })


# =========================================================================== behavior entity
HP_TIERS = [500, 620, 740, 860]   # mirrored in scripts config (validated)


def behavior_entity():
    G = {
        f"{NS}:roam": {
            "minecraft:movement": {"value": 0.17},
            "minecraft:behavior.random_stroll": {"priority": 6, "speed_multiplier": 0.75, "xz_dist": 10, "y_dist": 3,
                                                 "interval": 220},
            "minecraft:behavior.look_at_player": {"priority": 7, "look_distance": 24, "probability": 0.02},
            "minecraft:behavior.random_look_around": {"priority": 8},
        },
        f"{NS}:scripted": {"minecraft:movement": {"value": 0.0}},
        f"{NS}:ground": {"minecraft:physics": {"has_gravity": True, "has_collision": True}},
        f"{NS}:air": {"minecraft:physics": {"has_gravity": False, "has_collision": True}},
        f"{NS}:despawn": {"minecraft:instant_despawn": {}},
    }
    for i, hp in enumerate(HP_TIERS, start=1):
        G[f"{NS}:hp_{i}"] = {"minecraft:health": {"value": hp, "max": hp}}
    tiers = [f"{NS}:hp_{i}" for i in range(1, 5)]
    E = {
        "minecraft:entity_spawned": {"add": {"component_groups": [f"{NS}:roam", f"{NS}:ground", f"{NS}:hp_1"]}},
        f"{NS}:to_scripted": {"remove": {"component_groups": [f"{NS}:roam"]}, "add": {"component_groups": [f"{NS}:scripted"]}},
        f"{NS}:to_roam": {"remove": {"component_groups": [f"{NS}:scripted"]}, "add": {"component_groups": [f"{NS}:roam"]}},
        f"{NS}:to_air": {"remove": {"component_groups": [f"{NS}:ground"]}, "add": {"component_groups": [f"{NS}:air"]}},
        f"{NS}:to_ground": {"remove": {"component_groups": [f"{NS}:air"]}, "add": {"component_groups": [f"{NS}:ground"]}},
        f"{NS}:despawn": {"add": {"component_groups": [f"{NS}:despawn"]}},
    }
    for i in range(1, 5):
        E[f"{NS}:hp_tier_{i}"] = {"remove": {"component_groups": [t for t in tiers if t != f"{NS}:hp_{i}"]},
                                  "add": {"component_groups": [f"{NS}:hp_{i}"]}}
    props = {
        f"{NS}:anim": {"type": "int", "range": [0, len(AN["codes"]) - 1], "default": 0, "client_sync": True},
        f"{NS}:flight": {"type": "int", "range": [0, len(AN["flight"]) - 1], "default": 0, "client_sync": True},
        f"{NS}:gait": {"type": "int", "range": [0, len(AN["gait"]) - 1], "default": 0, "client_sync": True},
        f"{NS}:skull": {"type": "int", "range": [0, 2], "default": 0, "client_sync": True},
        f"{NS}:phase": {"type": "int", "range": [1, 3], "default": 1, "client_sync": True},
    }
    no = lambda c: {"cause": c, "deals_damage": "no"}
    ent = {
        "format_version": "1.21.90",
        "minecraft:entity": {
            "description": {"identifier": ID, "is_spawnable": False, "is_summonable": True, "properties": props},
            "component_groups": G,
            "components": {
                "minecraft:type_family": {"family": ["dragon_dominion_boss", "gharvok", "dragon", "monster", "mob"]},
                "minecraft:collision_box": {"width": 3.2, "height": 3.6},
                "minecraft:custom_hit_test": {"hitboxes": [{"width": 7.0, "height": 4.4, "pivot": [0, 2.2, 0]}]},
                "minecraft:health": {"value": HP_TIERS[0], "max": HP_TIERS[0]},
                "minecraft:boss": {"hud_range": 64, "should_darken_sky": False},
                "minecraft:knockback_resistance": {"value": 1.0},
                "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
                "minecraft:push_through": {"value": 1},
                "minecraft:follow_range": {"value": 48, "max": 48},
                "minecraft:movement.basic": {},
                "minecraft:navigation.walk": {"avoid_water": True, "can_path_over_water": False, "can_sink": True,
                                              "avoid_damage_blocks": True},
                "minecraft:jump.static": {},
                "minecraft:variable_max_auto_step": {"base_value": 1.0625, "jump_prevented_value": 0.5625},
                "minecraft:physics": {"has_gravity": True, "has_collision": True},
                "minecraft:persistent": {},
                "minecraft:nameable": {"always_show": False, "allow_name_tag_renaming": False},
                "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0, "breathes_water": True, "breathes_air": True},
                "minecraft:damage_sensor": {"triggers": [no("fall"), no("suffocation"), no("flyIntoWall"), no("fallingBlock"),
                                                         no("drowning")]},
                "minecraft:behavior.float": {"priority": 0},
                "minecraft:conditional_bandwidth_optimization": {},
            },
            "events": E,
        },
    }
    wj(os.path.join(BP, "entities", "gharvok.json"), ent)


# =========================================================================== items
ITEMS = {
    "cliff_sigil": {"name": "Cliff Sigil", "stack": 16, "glint": True, "category": "items"},
    "fractured_crownplate": {"name": "Fractured Crownplate", "stack": 64, "glint": False, "category": "items"},
}


def items():
    tex = {}
    for k, v in ITEMS.items():
        comps = {
            "minecraft:icon": f"{NS}_{k}",
            "minecraft:display_name": {"value": f"item.{NS}:{k}.name"},
            "minecraft:max_stack_size": v["stack"],
        }
        if v["glint"]:
            comps["minecraft:glint"] = True
        if k == "fractured_crownplate":
            comps["minecraft:rarity"] = "epic"
        else:
            comps["minecraft:rarity"] = "rare"
            comps["minecraft:use_modifiers"] = {"use_duration": 0.0, "movement_modifier": 1.0}
            comps["minecraft:cooldown"] = {"category": "dragon_dominion_sigil", "duration": 3.0}
        wj(os.path.join(BP, "items", f"{k}.json"), {
            "format_version": "1.21.90",
            "minecraft:item": {"description": {"identifier": f"{NS}:{k}", "menu_category": {"category": v["category"]}},
                               "components": comps}})
        tex[f"{NS}_{k}"] = {"textures": [f"textures/items/{NS}_{k}"]}
    wj(os.path.join(RP, "textures", "item_texture.json"),
       {"resource_pack_name": NS, "texture_name": "atlas.items", "texture_data": tex})


# =========================================================================== client entity + render controller
PARTICLES = {  # short name used in animations -> particle id
    "step": f"{NS}:step_dust",
    "dust_ring": f"{NS}:dust_ring",
    "dust_puff": f"{NS}:dust_puff",
    "wing_gust": f"{NS}:wing_gust",
    "roar_breath": f"{NS}:roar_breath",
    "claw_slash": f"{NS}:claw_slash",
    "impact_burst": f"{NS}:impact_burst",
    "daze_stars": f"{NS}:daze_stars",
    "tail_trail": f"{NS}:tail_trail",
    "skull_shards": f"{NS}:skull_shards",
}
SOUNDS = {"step": "mob.ravager.step", "snort": "mob.ravager.ambient", "flap": "mob.enderdragon.flap",
          "land": "mob.ravager.step"}


def client_entity():
    anims = {n: f"animation.{NS}.gharvok.{n}" for n in AN["anims"]}
    for c in AN["controllers"]:
        anims[c] = f"controller.animation.{NS}.gharvok.{c}"
    wj(os.path.join(RP, "entity", "gharvok.entity.json"), {
        "format_version": "1.10.0",
        "minecraft:client_entity": {"description": {
            "identifier": ID,
            "materials": {"default": "entity_alphatest"},
            "textures": {"intact": "textures/entity/gharvok_intact", "cracked": "textures/entity/gharvok_cracked",
                         "broken": "textures/entity/gharvok_broken"},
            "geometry": {"default": RIG["geometry"]},
            "scripts": {"scale": str(SCALE), "pre_animation": AN["pre_animation"], "animate": AN["animate"],
                        "should_update_bones_and_effects_offscreen": "1.0"},
            "animations": anims,
            "particle_effects": PARTICLES,
            "sound_effects": SOUNDS,
            "render_controllers": [f"controller.render.{NS}.gharvok"],
            "enable_attachables": False,
        }}})
    skull = f"q.property('{NS}:skull')"
    wj(os.path.join(RP, "render_controllers", "gharvok.render_controllers.json"), {
        "format_version": "1.8.0",
        "render_controllers": {f"controller.render.{NS}.gharvok": {
            "arrays": {"textures": {"Array.skull": ["Texture.intact", "Texture.cracked", "Texture.broken"]}},
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}],
            "textures": [f"Array.skull[{skull}]"],
            "part_visibility": [{"*": True}, {"crown_break_a": f"{skull} < 2"}, {"crown_break_b": f"{skull} < 2"},
                                {"crown_stubs": f"{skull} >= 2"}],
        }}})


# =========================================================================== particles
ATLAS = "textures/particle/dragon_dominion_fx"
# atlas cells (16x16 each in a 64x64 texture)
CELL = {"puff": (0, 0), "ring": (16, 0), "star": (32, 0), "shard": (48, 0), "slash": (0, 16), "streak": (16, 16),
        "dot": (32, 16), "chip": (48, 16)}


def particle(pid, comps, cell, size, tint, material="particles_blend", lit=True):
    u, v = CELL[cell]
    c = {
        **comps,
        "minecraft:particle_appearance_billboard": {
            "size": size, "facing_camera_mode": comps.pop("_facing", "rotate_xyz"),
            "uv": {"texture_width": 64, "texture_height": 64, "uv": [u, v], "uv_size": [16, 16]}},
        "minecraft:particle_appearance_tinting": {"color": tint},
    }
    if lit:
        c["minecraft:particle_appearance_lighting"] = {}
    wj(os.path.join(RP, "particles", pid.split(":")[1] + ".json"), {
        "format_version": "1.10.0",
        "particle_effect": {"description": {"identifier": pid, "basic_render_parameters": {"material": material, "texture": ATLAS}},
                            "components": c}})


def once(n, t=0.05):
    return {"minecraft:emitter_rate_instant": {"num_particles": n}, "minecraft:emitter_lifetime_once": {"active_time": t}}


DUST = [0.62, 0.55, 0.45, "0.8 * (1 - v.particle_age / v.particle_lifetime)"]


def particles():
    particle(PARTICLES["step"], {**once(10), "minecraft:emitter_shape_disc": {"plane_normal": [0, 1, 0], "radius": 0.9, "direction": "outwards"},
             "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.5, 0.9)"},
             "minecraft:particle_initial_speed": "math.random(1.5, 3)",
             "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1, 0], "linear_drag_coefficient": 3}},
             "puff", ["0.3 + v.particle_age * 0.6", "0.3 + v.particle_age * 0.6"], DUST)
    particle(PARTICLES["dust_ring"], {**once(48), "minecraft:emitter_shape_disc": {"plane_normal": [0, 1, 0], "radius": 1.0, "surface_only": True, "direction": "outwards"},
             "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.7, 1.2)"},
             "minecraft:particle_initial_speed": "math.random(7, 11)",
             "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.2, 0], "linear_drag_coefficient": 3}},
             "puff", ["0.45 + v.particle_age * 1.1", "0.45 + v.particle_age * 1.1"], DUST)
    particle(PARTICLES["dust_puff"], {**once(8), "minecraft:emitter_shape_sphere": {"radius": 0.4, "direction": "outwards"},
             "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.4, 0.8)"},
             "minecraft:particle_initial_speed": "math.random(1, 2.5)",
             "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.8, 0], "linear_drag_coefficient": 2}},
             "puff", ["0.3 + v.particle_age * 0.5", "0.3 + v.particle_age * 0.5"], DUST)
    particle(PARTICLES["wing_gust"], {**once(60, 0.15), "minecraft:emitter_shape_sphere": {"radius": 1.5, "direction": [0, 0, -1]},
             "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.5, 0.9)"},
             "minecraft:particle_initial_speed": "math.random(12, 18)",
             "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)"},
             "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 2.5}},
             "streak", ["0.25 + v.particle_age * 0.8", "0.12"], [0.9, 0.88, 0.82, "0.55 * (1 - v.particle_age / v.particle_lifetime)"],
             )
    particle(PARTICLES["roar_breath"], {**once(14, 0.3), "minecraft:emitter_shape_point": {"direction": ["math.random(-0.3, 0.3)", "math.random(-0.1, 0.3)", "-1"]},
             "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.6, 1.0)"},
             "minecraft:particle_initial_speed": "math.random(2, 4)",
             "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.6, 0], "linear_drag_coefficient": 1.5}},
             "puff", ["0.2 + v.particle_age * 0.9", "0.2 + v.particle_age * 0.9"], [0.85, 0.85, 0.85, "0.4 * (1 - v.particle_age / v.particle_lifetime)"])
    particle(PARTICLES["claw_slash"], {**once(6, 0.1), "minecraft:emitter_shape_sphere": {"radius": 0.6, "direction": "outwards"},
             "minecraft:particle_lifetime_expression": {"max_lifetime": 0.3},
             "minecraft:particle_initial_speed": 1.0,
             "minecraft:particle_motion_dynamic": {}},
             "slash", ["1.2", "1.2"], [1.0, 0.95, 0.85, "0.9 * (1 - v.particle_age / v.particle_lifetime)"], lit=False)
    particle(PARTICLES["impact_burst"], {**once(26), "minecraft:emitter_shape_sphere": {"radius": 0.5, "direction": "outwards"},
             "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.5, 1.1)"},
             "minecraft:particle_initial_speed": "math.random(4, 9)",
             "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-200, 200)"},
             "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -14, 0], "linear_drag_coefficient": 0.6}},
             "chip", ["0.18", "0.18"], [0.66, 0.6, 0.5, 1.0])
    particle(PARTICLES["daze_stars"], {**once(5, 0.05), "minecraft:emitter_shape_disc": {"plane_normal": [0, 1, 0], "radius": 1.2, "surface_only": True, "direction": [0, 0.3, 0]},
             "minecraft:particle_lifetime_expression": {"max_lifetime": 1.4},
             "minecraft:particle_initial_speed": 0.6,
             "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 1}},
             "star", ["0.3", "0.3"], [1.0, 0.86, 0.45, "1 - v.particle_age / v.particle_lifetime"], lit=False)
    particle(PARTICLES["tail_trail"], {**once(10, 0.1), "minecraft:emitter_shape_sphere": {"radius": 0.8, "direction": "outwards"},
             "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.3, 0.5)"},
             "minecraft:particle_initial_speed": "math.random(0.5, 1.5)",
             "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 2}},
             "streak", ["0.4", "0.1"], [0.9, 0.86, 0.78, "0.6 * (1 - v.particle_age / v.particle_lifetime)"])
    particle(PARTICLES["skull_shards"], {**once(30), "minecraft:emitter_shape_sphere": {"radius": 0.8, "direction": "outwards"},
             "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.8, 1.4)"},
             "minecraft:particle_initial_speed": "math.random(3, 7)",
             "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-300, 300)"},
             "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -16, 0], "linear_drag_coefficient": 0.4},
             "minecraft:particle_motion_collision": {"coefficient_of_restitution": 0.3, "collision_drag": 4, "collision_radius": 0.1}},
             "shard", ["0.22", "0.22"], [0.86, 0.82, 0.72, 1.0])
    # script-only effects ------------------------------------------------------------------------
    particle(f"{NS}:warning_ring", {
        "minecraft:emitter_rate_instant": {"num_particles": "math.min(80, 6 + v.radius * 7)"},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_disc": {"plane_normal": [0, 1, 0], "radius": "v.radius", "surface_only": True, "direction": [0, 1, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.3},
        "minecraft:particle_initial_speed": 0.2,
        "minecraft:particle_motion_dynamic": {}},
        "dot", ["0.22", "0.22"], [1.0, 0.35, 0.15, "0.95 * (1 - v.particle_age / v.particle_lifetime)"], lit=False)
    particle(f"{NS}:warning_fill", {
        "minecraft:emitter_rate_instant": {"num_particles": "math.min(40, 4 + v.radius * 3)"},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_disc": {"plane_normal": [0, 1, 0], "radius": "v.radius", "direction": [0, 1, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.35},
        "minecraft:particle_initial_speed": 0.3,
        "minecraft:particle_motion_dynamic": {}},
        "dot", ["0.14", "0.14"], [1.0, 0.55, 0.2, "0.6 * (1 - v.particle_age / v.particle_lifetime)"], lit=False)
    particle(f"{NS}:shockwave", {
        "minecraft:emitter_rate_instant": {"num_particles": "math.min(90, 10 + v.radius * 8)"},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_disc": {"plane_normal": [0, 1, 0], "radius": "v.radius", "surface_only": True, "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.4, 0.7)"},
        "minecraft:particle_initial_speed": "math.random(1, 3)",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 2.5, 0], "linear_drag_coefficient": 2}},
        "puff", ["0.5 + v.particle_age", "0.5 + v.particle_age"], DUST)
    particle(f"{NS}:charge_line", {
        "minecraft:emitter_rate_instant": {"num_particles": 3},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_sphere": {"radius": 0.6, "direction": [0, 1, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.5},
        "minecraft:particle_initial_speed": 0.4,
        "minecraft:particle_motion_dynamic": {}},
        "dot", ["0.2", "0.2"], [1.0, 0.4, 0.15, "0.9 * (1 - v.particle_age / v.particle_lifetime)"], lit=False)
    particle(f"{NS}:summon_pillar", {
        "minecraft:emitter_rate_steady": {"spawn_rate": 70, "max_particles": 140},
        "minecraft:emitter_lifetime_once": {"active_time": 1.5},
        "minecraft:emitter_shape_disc": {"plane_normal": [0, 1, 0], "radius": 3.0, "direction": [0, 1, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(1.0, 1.6)"},
        "minecraft:particle_initial_speed": "math.random(3, 7)",
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 1}},
        "chip", ["0.16", "0.16"], [0.75, 0.68, 0.55, "1 - v.particle_age / v.particle_lifetime"])
    particle(f"{NS}:defeat_dust", {
        **once(90, 0.2), "minecraft:emitter_shape_box": {"half_dimensions": [3, 1.5, 4], "direction": "outwards"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(1.0, 2.0)"},
        "minecraft:particle_initial_speed": "math.random(0.5, 2)",
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.5, 0], "linear_drag_coefficient": 1.5}},
        "puff", ["0.5 + v.particle_age * 0.8", "0.5 + v.particle_age * 0.8"], DUST)
    atlas()


def atlas():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # puff
    for r, a in ((7, 70), (5, 150), (3, 230)):
        d.ellipse((8 - r, 8 - r, 8 + r - 1, 8 + r - 1), fill=(255, 255, 255, a))
    # ring
    d.ellipse((17, 1, 30, 14), outline=(255, 255, 255, 255), width=2)
    # star
    cx, cy = 40, 8
    pts = []
    for k in range(10):
        rr = 7 if k % 2 == 0 else 3
        ang = math.pi / 2 + k * math.pi / 5
        pts.append((cx + rr * math.cos(ang), cy - rr * math.sin(ang)))
    d.polygon(pts, fill=(255, 255, 255, 255))
    # shard
    d.polygon([(50, 3), (60, 6), (57, 13), (51, 12)], fill=(255, 255, 255, 255))
    # slash arc
    for w, a in ((3, 255), (5, 90)):
        d.arc((1, 3, 15, 24), 290, 70, fill=(255, 255, 255, a), width=w)
    # streak
    d.rectangle((16, 22, 31, 25), fill=(255, 255, 255, 200))
    # dot
    d.ellipse((35, 19, 44, 28), fill=(255, 255, 255, 255))
    # chip (rock)
    d.polygon([(50, 19), (59, 18), (62, 26), (54, 30), (49, 26)], fill=(255, 255, 255, 255))
    os.makedirs(os.path.join(RP, "textures", "particle"), exist_ok=True)
    img.save(os.path.join(RP, "textures", "particle", "dragon_dominion_fx.png"))


# =========================================================================== icons
def icons():
    os.makedirs(os.path.join(RP, "textures", "items"), exist_ok=True)
    # Cliff Sigil: a weathered stone disc carved with Gharvok's crownshield, amber glyph
    S = 32
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((2, 2, 29, 29), fill=(92, 86, 74, 255), outline=(40, 36, 30, 255), width=2)
    d.ellipse((6, 6, 25, 25), fill=(120, 112, 96, 255))
    for k in range(7):  # fan of crown plates
        ang = math.radians(-90 + (k - 3) * 26)
        x0, y0 = 16 + 4 * math.cos(ang), 19 + 4 * math.sin(ang)
        x1, y1 = 16 + 10 * math.cos(ang), 19 + 10 * math.sin(ang)
        d.line((x0, y0, x1, y1), fill=(232, 168, 58, 255), width=2)
    d.polygon([(13, 18), (19, 18), (16, 25)], fill=(232, 168, 58, 255))
    d.point([(9, 22), (23, 10), (11, 9), (22, 23)], fill=(60, 54, 46, 255))
    im.save(os.path.join(RP, "textures", "items", f"{NS}_cliff_sigil.png"))
    # Fractured Crownplate: a pale bone plate shard with a dark crack and a jagged tip
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    plate = [(5, 27), (9, 9), (15, 3), (19, 8), (24, 4), (27, 14), (25, 27), (15, 29)]
    d.polygon(plate, fill=(206, 196, 170, 255), outline=(86, 80, 66, 255))
    d.polygon([(9, 12), (15, 6), (18, 11), (13, 15)], fill=(228, 220, 198, 255))
    d.line([(16, 8), (14, 14), (18, 18), (15, 24), (17, 28)], fill=(52, 42, 34, 255), width=1)
    d.line([(18, 18), (23, 20)], fill=(52, 42, 34, 255), width=1)
    d.line([(7, 25), (24, 25)], fill=(150, 140, 118, 255), width=1)
    im.save(os.path.join(RP, "textures", "items", f"{NS}_fractured_crownplate.png"))


def lang():
    lines = [
        f"entity.{ID}.name=Gharvok, the Cliffbreaker",
        f"item.{NS}:cliff_sigil.name=Cliff Sigil",
        f"item.{NS}:fractured_crownplate.name=Fractured Crownplate",
        f"action.hint.exit.{ID}=Gharvok",
    ]
    for p in (RP, BP):
        os.makedirs(os.path.join(p, "texts"), exist_ok=True)
        with open(os.path.join(p, "texts", "en_US.lang"), "w") as f:
            f.write("\n".join(lines) + "\n")
        wj(os.path.join(p, "texts", "languages.json"), ["en_US"])
    with open(os.path.join(BP, "texts", "en_US.lang"), "w") as f:
        f.write("pack.name=Dragon Dominion\npack.description=Behavior Pack - Boss 1: Gharvok, the Cliffbreaker\n")
    with open(os.path.join(RP, "texts", "en_US.lang"), "a") as f:
        f.write("pack.name=Dragon Dominion\npack.description=Resource Pack - Boss 1: Gharvok, the Cliffbreaker\n")


def pack_icons():
    """A head close-up rendered from the real model files."""
    import kinematics as K
    geo = K.load_json(os.path.join(RP, "models", "entity", "gharvok.geo.json"))["minecraft:geometry"][0]
    tex = np.array(Image.open(os.path.join(RP, "textures", "entity", "gharvok_intact.png")).convert("RGBA"))
    W = 512
    cam = K.Camera((0, 52, -72), 30, 10, scale=8.5, size=(W, W))
    yy, xx = np.mgrid[0:W, 0:W]
    r = np.hypot(xx - W / 2, yy - W / 2) / (W * 0.7)
    bg = np.clip(np.array([0.36, 0.33, 0.27]) * (1 - r[..., None]) + np.array([0.12, 0.11, 0.09]) * r[..., None], 0, 1)
    img, _, _, _ = K.render(list(K.world_faces(geo, None)), tex, cam, image=bg, zbuf=np.full((W, W), np.inf),
                            emissive_alpha=0, ambient=0.5)
    icon = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).resize((256, 256), Image.LANCZOS)
    for p in (BP, RP):
        icon.save(os.path.join(p, "pack_icon.png"))


if __name__ == "__main__":
    manifests()
    behavior_entity()
    items()
    client_entity()
    particles()
    icons()
    lang()
    pack_icons()
    print("content written")
