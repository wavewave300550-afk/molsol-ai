"""
Build script for "BOSS 001 - Joan of Arc: The Banner of Divine Paths".

    python3 tools/build.py      -> build/Joan_BP, build/Joan_RP and dist/*.mcaddon

Generates every pack file (geometry, HD textures + glow layers, animations,
controllers, render controllers, client/server entities, items, particles,
sounds, language, manifests), compiles the TypeScript gameplay and packages it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import anims  # noqa: E402
import icons  # noqa: E402
import models  # noqa: E402
import particles  # noqa: E402
import sounds  # noqa: E402
from modelkit import render  # noqa: E402

BUILD = os.path.join(ROOT, "build")
BP = os.path.join(BUILD, "Joan_BP")
RP = os.path.join(BUILD, "Joan_RP")
DIST = os.path.join(ROOT, "dist")
CACHE = os.path.join(BUILD, ".cache")

ADDON_NAME = "BOSS 001 - Joan of Arc"
VERSION = [1, 0, 0]
MIN_ENGINE = [1, 26, 60]
SERVER_VERSION = "2.11.0"
UUID = {
    "bp_header": "3a1f0c2e-5b7d-4e61-9a43-1431a0c0b001",
    "bp_data": "3a1f0c2e-5b7d-4e61-9a43-1431a0c0b002",
    "bp_script": "3a1f0c2e-5b7d-4e61-9a43-1431a0c0b003",
    "rp_header": "7e52b9d4-0c31-4f8a-b6d2-1431a0c0f001",
    "rp_res": "7e52b9d4-0c31-4f8a-b6d2-1431a0c0f002",
}

ITEMS = {
    # id: (name, lore summary, stack, extra components)
    "banner_of_divine_paths": "Banner of Divine Paths",
    "unburnt_heart": "Unburnt Heart",
    "pilgrims_standard": "Pilgrim's Standard",
}

ENTITY_NAMES = {
    "joan_of_arc": "Joan of Arc",
    "echo": "Procession Echo",
    "standard": "Phantom Standard",
    "stake": "The Stake",
    "waystone": "Lily Waystone",
    "seraph": "Seraph Light",
}

# timeline sound / particle cues inside action animations (seconds)
SOUND_CUES = {
    "spawn_land": {"0.15": "plant", "2.2": "swing", "2.55": "swing"},
    "melee_sweep": {"0.2": "snap", "0.34": "swing"},
    "melee_backsweep": {"0.28": "swing"},
    "melee_thrust": {"0.38": "swing"},
    "melee_plant": {"0.3": "snap", "0.5": "plant"},
    "melee_wrap": {"0.42": "swing", "0.72": "snap"},
    "trail_windup": {"0.4": "snap"},
    "surge_windup": {"0.35": "snap"},
    "surge_slam": {"0.12": "plant"},
    "orleans_plant": {"0.48": "plant"},
    "orleans_breaker": {"0.25": "snap", "0.44": "plant"},
    "false_point": {"0.5": "swing"},
    "converge_throw": {"0.32": "snap", "0.64": "snap", "0.96": "snap"},
    "detour_release": {"0.34": "swing"},
    "procession_raise": {"0.9": "snap"},
    "phase_kneel": {"0.75": "plant"},
    "phase_rise": {"1.2": "swing"},
    "recover": {"0.3": "snap"},
    "taunt": {"0.4": "swing"},
}


# --------------------------------------------------------------------------- io helpers
def write_json(path, data, compact=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if compact:
            json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
        else:
            json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# --------------------------------------------------------------------------- manifests & icons
def manifests():
    bp = {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["bp_header"],
                   "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [
            {"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
            {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION,
             "entry": "scripts/main.js"},
        ],
        "dependencies": [
            {"module_name": "@minecraft/server", "version": SERVER_VERSION},
            {"uuid": UUID["rp_header"], "version": VERSION},
        ],
        "metadata": {"authors": ["Joan of Arc boss add-on"], "product_type": "addon"},
    }
    rp = {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["rp_header"],
                   "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
        "dependencies": [{"uuid": UUID["bp_header"], "version": VERSION}],
        "metadata": {"authors": ["Joan of Arc boss add-on"], "product_type": "addon"},
    }
    write_json(os.path.join(BP, "manifest.json"), bp)
    write_json(os.path.join(RP, "manifest.json"), rp)


def pack_icon(joan_model):
    """Joan rendered from her real model over a road of light."""
    from PIL import Image, ImageFilter
    bg = icons.pack_icon()
    tmp = os.path.join(CACHE, "pack_joan.png")
    os.makedirs(CACHE, exist_ok=True)
    sampler = anims.Sampler()
    pose = sampler.body_pose(anims.P(anims.GUARD, **anims.OVERHEAD, head=(-10, 0, 0),
                                     arm_l=(-20, 0, -60), forearm_l=(-10, 0, 0)))
    sampler.rig.solve_banner(pose, anims.d(0.18, 1, 0.05), anims.BACK)
    for i in range(6):
        pose[f"cloth_{i}"] = {"rotation": (-4 - i, 18 - i * 6, 0)}
    render([(joan_model, pose, "base", "glow1", (0, 0, 0))], tmp, yaw=28, pitch=8, size=256,
           bg=(0, 0, 0, 0), span=70, center=(-2, 33, 6), ground=False)
    joan = Image.open(tmp).convert("RGBA")
    glow = joan.split()[3].filter(ImageFilter.GaussianBlur(6))
    halo = Image.new("RGBA", joan.size, (255, 226, 140, 0))
    halo.putalpha(glow.point(lambda v: int(v * 0.8)))
    bg.alpha_composite(halo)
    bg.alpha_composite(joan)
    return bg


# --------------------------------------------------------------------------- models & textures
def build_models():
    built = {}
    bounds = {"joan": (7.0, 7.0, 2.5), "standard": (3.0, 4.0, 1.5), "stake": (4.0, 6.0, 2.0),
              "waystone": (2.0, 2.0, 1.0), "seraph": (1.5, 1.5, 0.3)}
    for name, fn in models.ALL.items():
        m = fn()
        bw, bh, oy = bounds[name]
        write_json(os.path.join(RP, "models", "entity", "joan", f"{name}.geo.json"), m.geometry_json(bw, bh, oy))
        for variant in models.VARIANTS[name]:
            img = m.paint(variant)
            p = os.path.join(RP, "textures", "entity", "joan", f"{name}_{variant}.png")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            img.save(p)
        built[name] = m
    return built


def build_icons(joan_model):
    data = {}
    for name, fn in icons.ICONS.items():
        p = os.path.join(RP, "textures", "items", "joan", f"{name}.png")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        fn().save(p)
        data[f"joan_{name}"] = {"textures": f"textures/items/joan/{name}"}
    p = os.path.join(RP, "textures", "items", "joan", "spawn_egg.png")
    icons.spawn_egg().save(p)
    data["joan_spawn_egg"] = {"textures": "textures/items/joan/spawn_egg"}
    write_json(os.path.join(RP, "textures", "item_texture.json"),
               {"resource_pack_name": "joan", "texture_name": "atlas.items", "texture_data": data})
    icon = pack_icon(joan_model)
    for root in (BP, RP):
        icon.save(os.path.join(root, "pack_icon.png"))


# --------------------------------------------------------------------------- render controllers
def build_render_controllers():
    rc = {
        "controller.render.joan.body": {
            "arrays": {"textures": {"Array.skins": ["Texture.base", "Texture.burning", "Texture.white"]}},
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}],
            "textures": ["Array.skins[query.property('joan:phase') >= 3 ? 2 : (query.property('joan:phase') >= 2 ? 1 : 0)]"],
        },
        "controller.render.joan.glow": {
            "arrays": {"textures": {"Array.glows": ["Texture.glow1", "Texture.glow2"]}},
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.glow"}],
            "textures": ["Array.glows[query.property('joan:phase') == 2 ? 1 : 0]"],
            "ignore_lighting": True,
        },
        "controller.render.joan.ghost": {
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.ghost"}],
            "textures": ["Texture.ghost"],
            "ignore_lighting": True,
        },
        "controller.render.joan.echo_fire": {
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.glow"}],
            "textures": ["Texture.glow2"],
            "ignore_lighting": True,
        },
        "controller.render.joan.standard": {
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.ghost"}],
            "textures": ["Texture.ghost"],
            "ignore_lighting": True,
        },
        "controller.render.joan.standard_glow": {
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.glow"}],
            "textures": ["Texture.glow1"],
            "ignore_lighting": True,
        },
        "controller.render.joan.stake": {
            "arrays": {"textures": {"Array.skins": ["Texture.base", "Texture.burning", "Texture.white"]}},
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}],
            "textures": ["Array.skins[query.property('joan:state')]"],
        },
        "controller.render.joan.stake_glow": {
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.glow"}],
            "textures": ["Texture.glow2"],
            "ignore_lighting": True,
        },
        "controller.render.joan.simple": {
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}],
            "textures": ["Texture.base"],
        },
        "controller.render.joan.switch_glow": {
            "arrays": {"textures": {"Array.glows": ["Texture.glow1", "Texture.glow2"]}},
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.glow"}],
            "textures": ["Array.glows[query.property('joan:fire') ? 1 : 0]"],
            "ignore_lighting": True,
        },
    }
    write_json(os.path.join(RP, "render_controllers", "joan.render_controllers.json"),
               {"format_version": "1.8.0", "render_controllers": rc})
    return rc


# --------------------------------------------------------------------------- client entities
def tex(name, variant):
    return f"textures/entity/joan/{name}_{variant}"


def build_client_entities(meta):
    actions = meta["actions"]
    animations = {
        "base": "animation.joan.base",
        "walk": "animation.joan.walk",
        "run": "animation.joan.run",
        "look": "animation.joan.look",
        "cloth_breeze": "animation.joan.cloth_breeze",
        "cloth_stream": "animation.joan.cloth_stream",
        "cloth_turn": "animation.joan.cloth_turn",
        "flutter": "animation.joan.flutter",
        "ambient_p1": "animation.joan.ambient_p1",
        "ambient_p2": "animation.joan.ambient_p2",
        "action_ctrl": "controller.animation.joan.action",
    }
    for name, _aid, _length, _loop in actions:
        animations[name] = f"animation.joan.{name}"
    joan = {
        "format_version": "1.10.0",
        "minecraft:client_entity": {"description": {
            "identifier": "joan:joan_of_arc",
            "materials": {"default": "entity_alphatest", "glow": "entity_alphatest"},
            "textures": {v: tex("joan", v) for v in ("base", "burning", "white", "glow1", "glow2")},
            "geometry": {"default": "geometry.joan.joan_of_arc"},
            "spawn_egg": {"texture": "joan_spawn_egg"},
            "particle_effects": {"aura_p1": "joan:aura_p1", "aura_p2": "joan:aura_p2", "glint": "joan:banner_glint"},
            "sound_effects": {"swing": "joan.banner.swing", "snap": "joan.banner.snap", "plant": "joan.banner.plant",
                              "step": "joan.step"},
            "animations": animations,
            "scripts": {
                "initialize": ["variable.p2 = 0.0;", "variable.turn = 0.0;", "variable.joan_seq = 0;",
                               "variable.last_yaw = query.body_y_rotation;"],
                "pre_animation": [
                    "variable.p2 = math.lerp(variable.p2, query.property('joan:phase') == 2 ? 1.0 : 0.0, math.min(1.0, query.delta_time * 1.5));",
                    "variable.dyaw = query.body_y_rotation - variable.last_yaw;",
                    "variable.dyaw = variable.dyaw > 180 ? variable.dyaw - 360 : (variable.dyaw < -180 ? variable.dyaw + 360 : variable.dyaw);",
                    "variable.last_yaw = query.body_y_rotation;",
                    "variable.turn = math.lerp(variable.turn, variable.dyaw / math.max(query.delta_time, 0.01), 0.12);",
                    "variable.run = math.clamp((query.ground_speed - 3.5) / 3.0, 0.0, 1.0);",
                    "variable.moving = math.clamp(query.ground_speed / 4.0, 0.0, 1.0);",
                    "variable.idle = query.property('joan:action') == 0 ? 1.0 : 0.0;",
                ],
                "animate": [
                    "base",
                    {"walk": "variable.idle * (1.0 - variable.run)"},
                    {"run": "variable.idle * variable.run"},
                    {"cloth_breeze": "1.0 - variable.moving"},
                    {"cloth_stream": "variable.moving"},
                    "cloth_turn",
                    "action_ctrl",
                    "flutter",
                    {"look": "variable.idle"},
                    {"ambient_p1": "query.property('joan:phase') == 1"},
                    {"ambient_p2": "query.property('joan:phase') == 2"},
                ],
            },
            "render_controllers": ["controller.render.joan.body", "controller.render.joan.glow"],
        }},
    }
    write_json(os.path.join(RP, "entity", "joan_of_arc.entity.json"), joan)

    echo = {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": "joan:echo",
        "materials": {"ghost": "entity_alphablend", "glow": "entity_alphatest"},
        "textures": {"ghost": tex("joan", "ghost"), "glow2": tex("joan", "glow2")},
        "geometry": {"default": "geometry.joan.joan_of_arc"},
        "animations": {"base": "animation.joan.base", "march": "animation.joan.echo.march",
                       "flutter": "animation.joan.flutter"},
        "scripts": {"initialize": ["variable.p2 = 0.0;", "variable.turn = 0.0;"],
                    "pre_animation": ["variable.p2 = query.property('joan:fire') ? 1.0 : 0.0;"],
                    "animate": ["base", "march", "flutter"]},
        "render_controllers": ["controller.render.joan.ghost",
                               {"controller.render.joan.echo_fire": "query.property('joan:fire')"}],
    }}}
    write_json(os.path.join(RP, "entity", "echo.entity.json"), echo)

    standard = {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": "joan:standard",
        "materials": {"ghost": "entity_alphablend", "glow": "entity_alphatest"},
        "textures": {"ghost": tex("standard", "ghost"), "glow1": tex("standard", "glow1")},
        "geometry": {"default": "geometry.joan.phantom_standard"},
        "animations": {"idle": "animation.joan.standard.idle", "rise": "animation.joan.standard.rise"},
        "scripts": {"animate": ["idle", {"rise": "query.life_time < 0.7"}]},
        "render_controllers": ["controller.render.joan.standard", "controller.render.joan.standard_glow"],
    }}}
    write_json(os.path.join(RP, "entity", "standard.entity.json"), standard)

    stake = {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": "joan:stake",
        "materials": {"default": "entity_alphatest", "glow": "entity_alphatest"},
        "textures": {"base": tex("stake", "base"), "burning": tex("stake", "burning"), "white": tex("stake", "white"),
                     "glow2": tex("stake", "glow2")},
        "geometry": {"default": "geometry.joan.stake"},
        "animations": {"rise": "animation.joan.stake.rise", "idle": "animation.joan.stake.idle",
                       "purified": "animation.joan.stake.purified", "sink": "animation.joan.stake.sink"},
        "scripts": {"animate": [{"rise": "query.life_time < 2.1"}, "idle",
                                {"purified": "query.property('joan:state') == 2"},
                                {"sink": "query.property('joan:sinking')"}]},
        "render_controllers": ["controller.render.joan.stake",
                               {"controller.render.joan.stake_glow": "query.property('joan:state') != 2"}],
    }}}
    write_json(os.path.join(RP, "entity", "stake.entity.json"), stake)

    waystone = {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": "joan:waystone",
        "materials": {"default": "entity_alphatest", "glow": "entity_alphatest"},
        "textures": {"base": tex("waystone", "base"), "glow1": tex("waystone", "glow1"), "glow2": tex("waystone", "glow2")},
        "geometry": {"default": "geometry.joan.waystone"},
        "animations": {"idle": "animation.joan.waystone.idle", "turned": "animation.joan.waystone.turned"},
        "scripts": {"animate": ["idle", {"turned": "!query.property('joan:fire')"}]},
        "render_controllers": ["controller.render.joan.simple", "controller.render.joan.switch_glow"],
    }}}
    write_json(os.path.join(RP, "entity", "waystone.entity.json"), waystone)

    seraph = {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": "joan:seraph",
        "materials": {"default": "entity_alphatest", "glow": "entity_alphatest"},
        "textures": {"base": tex("seraph", "base"), "glow1": tex("seraph", "glow1"), "glow2": tex("seraph", "glow2")},
        "geometry": {"default": "geometry.joan.seraph_light"},
        "animations": {"fly": "animation.joan.seraph.fly"},
        "scripts": {"animate": ["fly"]},
        "render_controllers": ["controller.render.joan.simple", "controller.render.joan.switch_glow"],
    }}}
    write_json(os.path.join(RP, "entity", "seraph.entity.json"), seraph)


def add_ambient_and_cues():
    """Ambient particle loops + timeline sound cues inside the generated animation file."""
    p = os.path.join(RP, "animations", "joan.animation.json")
    with open(p) as f:
        data = json.load(f)
    A = data["animations"]
    A["animation.joan.ambient_p1"] = {"loop": True, "animation_length": 2.0, "particle_effects": {
        "0.0": [{"effect": "aura_p1", "locator": "chest"}, {"effect": "glint", "locator": "banner_top"}]}}
    A["animation.joan.ambient_p2"] = {"loop": True, "animation_length": 2.0, "particle_effects": {
        "0.0": [{"effect": "aura_p2", "locator": "chest"}, {"effect": "aura_p2", "locator": "banner_mid"}]}}
    for name, cues in SOUND_CUES.items():
        key = f"animation.joan.{name}"
        A[key]["sound_effects"] = {t: {"effect": e} for t, e in cues.items()}
    # armoured footsteps on the walk/run cycles
    with open(p, "w") as f:
        json.dump(data, f, separators=(",", ":"))


# --------------------------------------------------------------------------- behaviour entities
def despawn_group():
    return {"joan:despawn": {"minecraft:instant_despawn": {}}}


def minion(identifier, families, comps, props=None, lifetime=60.0):
    base = {
        "minecraft:type_family": {"family": families},
        "minecraft:timer": {"looping": False, "time": lifetime, "randomInterval": False,
                            "time_down_event": {"event": "joan:despawn", "target": "self"}},
        "minecraft:physics": {"has_gravity": False, "has_collision": False},
        "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
        "minecraft:knockback_resistance": {"value": 1.0},
        "minecraft:fire_immune": {},
        "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0, "breathes_water": True},
    }
    base.update(comps)
    desc = {"identifier": identifier, "is_spawnable": False, "is_summonable": True}
    if props:
        desc["properties"] = props
    return {"format_version": "1.21.0", "minecraft:entity": {
        "description": desc,
        "component_groups": despawn_group(),
        "components": base,
        "events": {"joan:despawn": {"add": {"component_groups": ["joan:despawn"]}}},
    }}


def build_bp_entities():
    joan = {"format_version": "1.21.0", "minecraft:entity": {
        "description": {
            "identifier": "joan:joan_of_arc", "is_spawnable": True, "is_summonable": True,
            "properties": {
                "joan:phase": {"type": "int", "range": [0, 3], "default": 0, "client_sync": True},
                "joan:action": {"type": "int", "range": [0, 63], "default": 0, "client_sync": True},
                "joan:seq": {"type": "int", "range": [0, 15], "default": 0, "client_sync": True},
            },
        },
        "component_groups": {
            "joan:despawn": {"minecraft:instant_despawn": {}},
            "joan:dark_sky": {"minecraft:boss": {"hud_range": 64, "should_darken_sky": True}},
        },
        "components": {
            "minecraft:type_family": {"family": ["joan", "boss", "monster", "mob"]},
            "minecraft:health": {"value": 600, "max": 600},
            "minecraft:boss": {"hud_range": 64, "should_darken_sky": False},
            "minecraft:collision_box": {"width": 0.9, "height": 2.3},
            "minecraft:physics": {},
            "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
            "minecraft:knockback_resistance": {"value": 0.9},
            "minecraft:movement": {"value": 0.3},
            "minecraft:movement.basic": {},
            "minecraft:navigation.walk": {"can_path_over_water": True, "avoid_water": True,
                                          "avoid_damage_blocks": True, "can_open_doors": False},
            "minecraft:jump.static": {},
            "minecraft:can_climb": {},
            "minecraft:follow_range": {"value": 48, "max": 64},
            "minecraft:persistent": {},
            "minecraft:nameable": {},
            "minecraft:body_rotation_always_follows_head": {},
            "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0, "breathes_water": True},
            "minecraft:damage_sensor": {"triggers": [
                {"cause": "fall", "deals_damage": "no"},
                {"cause": "suffocation", "deals_damage": "no"},
                {"cause": "drowning", "deals_damage": "no"},
                {"cause": "fly_into_wall", "deals_damage": "no"},
            ]},
            "minecraft:behavior.float": {"priority": 0},
            "minecraft:behavior.hurt_by_target": {"priority": 1},
            "minecraft:behavior.nearest_attackable_target": {
                "priority": 2, "must_see": False, "reselect_targets": True, "within_radius": 40.0,
                "entity_types": [{"filters": {"test": "is_family", "subject": "other", "value": "player"},
                                  "max_dist": 40}]},
            "minecraft:behavior.move_towards_target": {"priority": 3, "speed_multiplier": 1.0, "within_radius": 48.0},
            "minecraft:behavior.random_stroll": {"priority": 8, "speed_multiplier": 0.7},
            "minecraft:behavior.look_at_player": {"priority": 9, "look_distance": 12.0, "probability": 0.2},
            "minecraft:behavior.random_look_around": {"priority": 10},
        },
        "events": {
            "joan:despawn": {"add": {"component_groups": ["joan:despawn"]}},
            "joan:darken": {"add": {"component_groups": ["joan:dark_sky"]}},
            "joan:brighten": {"remove": {"component_groups": ["joan:dark_sky"]}},
        },
    }}
    write_json(os.path.join(BP, "entities", "joan_of_arc.json"), joan)

    echo = minion("joan:echo", ["joan_minion", "monster"], {
        "minecraft:health": {"value": 8, "max": 8},
        "minecraft:collision_box": {"width": 0.7, "height": 2.2},
        "minecraft:damage_sensor": {"triggers": [{"cause": "fire", "deals_damage": "no"},
                                                 {"cause": "fire_tick", "deals_damage": "no"},
                                                 {"cause": "fall", "deals_damage": "no"}]},
    }, {"joan:fire": {"type": "bool", "default": False, "client_sync": True}}, lifetime=40.0)
    write_json(os.path.join(BP, "entities", "echo.json"), echo)

    standard = minion("joan:standard", ["joan_minion", "monster"], {
        "minecraft:health": {"value": 30, "max": 30},
        "minecraft:collision_box": {"width": 0.8, "height": 2.8},
        "minecraft:damage_sensor": {"triggers": [{"cause": "fire", "deals_damage": "no"},
                                                 {"cause": "fire_tick", "deals_damage": "no"},
                                                 {"cause": "fall", "deals_damage": "no"}]},
    }, lifetime=45.0)
    write_json(os.path.join(BP, "entities", "standard.json"), standard)

    stake = minion("joan:stake", ["joan_minion", "inanimate"], {
        "minecraft:health": {"value": 100, "max": 100},
        "minecraft:collision_box": {"width": 1.4, "height": 3.6},
        "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": "no"}]},
    }, {"joan:state": {"type": "int", "range": [0, 2], "default": 0, "client_sync": True},
        "joan:stake": {"type": "float", "range": [0.0, 1.0], "default": 0.0, "client_sync": True},
        "joan:sinking": {"type": "bool", "default": False, "client_sync": True}}, lifetime=90.0)
    write_json(os.path.join(BP, "entities", "stake.json"), stake)

    waystone = minion("joan:waystone", ["joan_minion", "inanimate"], {
        "minecraft:health": {"value": 100, "max": 100},
        "minecraft:collision_box": {"width": 1.0, "height": 1.6},
        "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": "no"}]},
    }, {"joan:fire": {"type": "bool", "default": True, "client_sync": True}}, lifetime=60.0)
    write_json(os.path.join(BP, "entities", "waystone.json"), waystone)

    seraph = minion("joan:seraph", ["joan_minion", "monster"], {
        "minecraft:health": {"value": 2, "max": 2},
        "minecraft:collision_box": {"width": 0.5, "height": 0.5},
        "minecraft:damage_sensor": {"triggers": [{"cause": "fire", "deals_damage": "no"},
                                                 {"cause": "fire_tick", "deals_damage": "no"}]},
    }, {"joan:fire": {"type": "bool", "default": False, "client_sync": True}}, lifetime=12.0)
    write_json(os.path.join(BP, "entities", "seraph.json"), seraph)


# --------------------------------------------------------------------------- items & recipes
def build_items():
    for key, name in ITEMS.items():
        comps = {
            "minecraft:icon": {"textures": {"default": f"joan_{key}"}},
            "minecraft:display_name": {"value": f"item.joan:{key}.name"},
            "minecraft:max_stack_size": 1,
            "minecraft:glint": True,
            "minecraft:tags": {"tags": [f"joan:{key}"]},
        }
        if key == "banner_of_divine_paths":
            comps["minecraft:hand_equipped"] = True
            comps["minecraft:damage"] = {"value": 7}
            comps["minecraft:cooldown"] = {"category": "joan:road", "duration": 4.0}
            comps["minecraft:rarity"] = {"value": "epic"}
        else:
            comps["minecraft:rarity"] = {"value": "rare"}
        item = {"format_version": "1.21.60", "minecraft:item": {
            "description": {"identifier": f"joan:{key}", "menu_category": {"category": "equipment"}},
            "components": comps}}
        write_json(os.path.join(BP, "items", f"{key}.json"), item)
    recipe = {"format_version": "1.20.10", "minecraft:recipe_shaped": {
        "description": {"identifier": "joan:pilgrims_standard"},
        "tags": ["crafting_table"],
        "pattern": ["LWL", "GWG", " S "],
        "key": {"L": {"item": "minecraft:lapis_lazuli"}, "W": {"item": "minecraft:white_wool"},
                "G": {"item": "minecraft:gold_ingot"}, "S": {"item": "minecraft:stick"}},
        "unlock": [{"item": "minecraft:gold_ingot"}],
        "result": {"item": "joan:pilgrims_standard"}}}
    write_json(os.path.join(BP, "recipes", "pilgrims_standard.json"), recipe)


# --------------------------------------------------------------------------- particles & sounds
def build_particles():
    return particles.build(RP)


def build_sounds():
    files = sounds.build(RP, os.path.join(CACHE, "sounds"))
    write_json(os.path.join(RP, "sounds", "sound_definitions.json"), sounds.sound_definitions(files))
    return files


# --------------------------------------------------------------------------- language
def build_lang():
    en = [
        f"pack.name={ADDON_NAME}",
        "pack.description=BOSS 001: Joan of Arc, The Banner of Divine Paths. A two-phase boss who writes, bends, "
        "splits, merges and reverses roads of light.",
    ]
    for key, name in ENTITY_NAMES.items():
        en.append(f"entity.joan:{key}.name={name}")
    en.append("item.spawn_egg.entity.joan:joan_of_arc.name=Spawn Joan of Arc")
    for key, name in ITEMS.items():
        en.append(f"item.joan:{key}.name={name}")
    text = "\n".join(en) + "\n"
    for root in (BP, RP):
        write_text(os.path.join(root, "texts", "en_US.lang"), text if root == RP else "\n".join(en[:2]) + "\n")
        write_text(os.path.join(root, "texts", "languages.json"), json.dumps(["en_US"], indent=2) + "\n")


# --------------------------------------------------------------------------- scripts
def build_scripts():
    out = os.path.join(BP, "scripts")
    tsc = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        raise SystemExit("TypeScript not installed: run `npm install` in joan-addon/")
    res = subprocess.run([tsc, "-p", os.path.join(ROOT, "tsconfig.json"), "--outDir", out],
                         capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout, res.stderr)
        raise SystemExit("TypeScript compilation failed")


# --------------------------------------------------------------------------- packaging
def zip_dir(zf, folder, arc_root):
    for dirpath, dirs, files in os.walk(folder):
        dirs.sort()
        for fn in sorted(files):
            full = os.path.join(dirpath, fn)
            zf.write(full, os.path.join(arc_root, os.path.relpath(full, folder)))


def package():
    os.makedirs(DIST, exist_ok=True)
    base = "Joan_of_Arc_Boss"
    addon = os.path.join(DIST, f"{base}.mcaddon")
    with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as zf:
        zip_dir(zf, BP, "Joan_of_Arc_BP")
        zip_dir(zf, RP, "Joan_of_Arc_RP")
    for folder, suffix in ((BP, "BP"), (RP, "RP")):
        with zipfile.ZipFile(os.path.join(DIST, f"{base}_{suffix}.mcpack"), "w", zipfile.ZIP_DEFLATED) as zf:
            zip_dir(zf, folder, "")
    return addon


def main():
    for d in (BP, RP):
        if os.path.exists(d):
            shutil.rmtree(d)
    manifests()
    built = build_models()
    build_icons(built["joan"])
    meta = anims.build(RP, os.path.join(ROOT, "src", "generated", "anims.ts"))
    add_ambient_and_cues()
    build_render_controllers()
    build_client_entities(meta)
    build_bp_entities()
    build_items()
    ids = build_particles()
    write_json(os.path.join(BUILD, "particle_ids.json"), ids)
    build_sounds()
    build_lang()
    build_scripts()
    addon = package()
    print("built", os.path.relpath(addon, ROOT))


if __name__ == "__main__":
    main()
