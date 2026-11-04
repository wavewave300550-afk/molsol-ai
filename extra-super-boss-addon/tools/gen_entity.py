#!/usr/bin/env python3
"""
Writes every behavior/resource JSON of Extra Super Boss except the animations and the boss's client
entity (tools/gen_animations.py owns those), plus scripts-src/balance.ts and scripts-src/spec.ts.
Numbers come from balance.json and tools/spec.py.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(ROOT, "addon")
BP = os.path.join(ADDON, "behavior_packs", "extra_super_boss")
RP = os.path.join(ADDON, "resource_packs", "extra_super_boss")
SRC = os.path.join(ROOT, "scripts-src")
BAL = json.load(open(os.path.join(ROOT, "balance.json")))
B = BAL["boss"]

VERSION = [1, 2, 0]
ENGINE = [1, 26, 60]
SERVER_API = [2, 11, 0]
UUID = {
    "bp": "6e5d1038-8b6d-4289-bbd5-0042510ea511",
    "bp_data": "fd35b219-14fe-44cc-afde-917cca133c3a",
    "bp_script": "f28c6bc7-7759-47aa-8641-272f8ed3fdb2",
    "rp": "444fca9a-af9f-45d5-bc08-3a573e2784ef",
    "rp_res": "20d09311-9d43-4947-bf46-beaded42baf8",
}
ENTITY_FMT = "1.21.90"
PACK_NAME = "Extra Super Boss"
PACK_DESC = "Boss 1: Leonardo da Vinci - Boss 2: Thomas Edison (v1.2.0, Ultimates)"


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")


# ------------------------------------------------------------------------------ manifests

def manifests():
    write(os.path.join(BP, "manifest.json"), {
        "format_version": 2,
        "header": {"name": PACK_NAME, "description": PACK_DESC, "uuid": UUID["bp"],
                   "version": VERSION, "min_engine_version": ENGINE},
        "modules": [
            {"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
            {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION,
             "entry": "scripts/main.js"},
        ],
        "dependencies": [{"uuid": UUID["rp"], "version": VERSION},
                         {"module_name": "@minecraft/server", "version": SERVER_API}],
        "metadata": {"authors": ["Extra Super Boss team"]},
    })
    write(os.path.join(RP, "manifest.json"), {
        "format_version": 2,
        "header": {"name": PACK_NAME, "description": PACK_DESC, "uuid": UUID["rp"],
                   "version": VERSION, "min_engine_version": ENGINE},
        "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
        "metadata": {"authors": ["Extra Super Boss team"]},
    })


# ------------------------------------------------------------------------------ boss (behavior)

def damage_sensor():
    no = lambda c: {"cause": c, "deals_damage": "no"}  # noqa: E731
    return {"triggers": [
        {"on_damage": {"filters": {"test": "is_family", "subject": "damager", "value": "esb_boss"}}, "deals_damage": "no"},
        no("fall"), no("suffocation"), no("fly_into_wall"), no("drowning"),
    ]}


def free_group(speed, attack_duration, hit_pct=None, cooldown=0.5):
    return {
        "minecraft:movement": {"value": speed},
        "minecraft:behavior.delayed_attack": {
            "priority": 3, "attack_once": False, "track_target": True, "require_complete_path": False,
            "random_stop_interval": 0, "reach_multiplier": 1.3, "speed_multiplier": 1.0,
            "attack_duration": attack_duration, "hit_delay_pct": hit_pct if hit_pct is not None else spec.SLASH["hit_pct"],
            "cooldown_time": cooldown,
        },
        "minecraft:behavior.random_stroll": {"priority": 8, "speed_multiplier": 0.6, "xz_dist": 10, "y_dist": 3, "interval": 200},
        "minecraft:behavior.look_at_player": {"priority": 9, "look_distance": 24, "probability": 0.05},
        "minecraft:behavior.random_look_around": {"priority": 10},
    }


def boss_entity(ident=spec.BOSS_ID, family="da_vinci", values=spec.ACTION_VALUES, B=B, attack=spec.SLASH, p2_speed=0.8,
                cooldown=0.5, hitbox=(1.6, 3.8), loot="loot_tables/entities/da_vinci.json", file="da_vinci.json"):
    p2_len = round(attack["length"] * p2_speed, 2)
    ent = {
        "format_version": ENTITY_FMT,
        "minecraft:entity": {
            "description": {
                "identifier": ident,
                "is_spawnable": True,
                "is_summonable": True,
                "properties": {
                    "esb:action": {"type": "enum", "values": values, "default": "none", "client_sync": True},
                    "esb:phase": {"type": "int", "range": [1, 2], "default": 1, "client_sync": True},
                },
            },
            "component_groups": {
                "esb:ground": {
                    "minecraft:physics": {"has_gravity": True, "has_collision": True},
                    "minecraft:movement.basic": {},
                    "minecraft:jump.static": {},
                    "minecraft:navigation.walk": {"can_path_over_water": True, "avoid_water": True, "can_open_doors": False,
                                                  "avoid_damage_blocks": True, "can_sink": False},
                    "minecraft:variable_max_auto_step": {"base_value": 1.0625, "jump_prevented_value": 0.5625},
                },
                "esb:air": {"minecraft:physics": {"has_gravity": False, "has_collision": True}},
                "esb:free": free_group(B["speed"], attack["length"], attack["hit_pct"], cooldown),
                "esb:free_fast": free_group(B["speed_phase2"], p2_len, attack["hit_pct"], cooldown),
                "esb:locked": {"minecraft:movement": {"value": 0.0}, "minecraft:body_rotation_always_follows_head": {}},
                "esb:discard": {"minecraft:instant_despawn": {}},
            },
            "events": {
                "minecraft:entity_spawned": {"add": {"component_groups": ["esb:ground", "esb:free"]}},
                "esb:lock": {"remove": {"component_groups": ["esb:free", "esb:free_fast"]},
                             "add": {"component_groups": ["esb:locked"]}},
                "esb:unlock": {"remove": {"component_groups": ["esb:locked", "esb:free_fast"]},
                               "add": {"component_groups": ["esb:free"]}},
                "esb:unlock_fast": {"remove": {"component_groups": ["esb:locked", "esb:free"]},
                                    "add": {"component_groups": ["esb:free_fast"]}},
                "esb:to_air": {"remove": {"component_groups": ["esb:ground", "esb:free", "esb:free_fast"]},
                               "add": {"component_groups": ["esb:air", "esb:locked"]}},
                "esb:to_ground": {"remove": {"component_groups": ["esb:air"]}, "add": {"component_groups": ["esb:ground"]}},
                "esb:dying": {"remove": {"component_groups": ["esb:free", "esb:free_fast", "esb:air"]},
                              "add": {"component_groups": ["esb:locked", "esb:ground"]}},
                "esb:despawn": {"add": {"component_groups": ["esb:discard"]}},
            },
            "components": {
                "minecraft:type_family": {"family": [family, "esb_boss", "monster", "mob"]},
                "minecraft:collision_box": {"width": B["collision_width"], "height": B["collision_height"]},
                "minecraft:custom_hit_test": {"hitboxes": [{"width": hitbox[0], "height": hitbox[1], "pivot": [0, hitbox[1] / 2, 0]}]},
                "minecraft:health": {"value": B["health"], "max": B["health"]},
                "minecraft:attack": {"damage": B["melee_damage"]},
                "minecraft:boss": {"should_darken_sky": False, "hud_range": 48},
                "minecraft:knockback_resistance": {"value": 1.0},
                "minecraft:follow_range": {"value": B["follow_range"], "max": B["follow_range"]},
                "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
                "minecraft:push_through": {"value": 0},
                "minecraft:persistent": {},
                "minecraft:damage_sensor": damage_sensor(),
                "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0, "breathes_water": True},
                "minecraft:loot": {"table": loot},
                "minecraft:experience_reward": {"on_death": f"q.last_hit_by_player ? {B['xp']} : 0"},
                "minecraft:behavior.float": {"priority": 0},
                "minecraft:behavior.hurt_by_target": {"priority": 1},
                "minecraft:behavior.nearest_attackable_target": {
                    "priority": 2, "must_see": False, "reselect_targets": True, "within_radius": B["aggro_range"],
                    "entity_types": [
                        {"filters": {"test": "is_family", "subject": "other", "value": "player"}, "max_dist": B["aggro_range"]},
                        {"filters": {"test": "is_family", "subject": "other", "value": "irongolem"}, "max_dist": 20},
                    ],
                },
                "minecraft:nameable": {},
                "minecraft:conditional_bandwidth_optimization": {},
            },
        },
    }
    write(os.path.join(BP, "entities", file), ent)


def gear_entity():
    g = BAL["gear_volley"]
    write(os.path.join(BP, "entities", "brass_gear.json"), {
        "format_version": ENTITY_FMT,
        "minecraft:entity": {
            "description": {"identifier": spec.GEAR_ID, "is_spawnable": False, "is_summonable": True},
            "component_groups": {"esb:expire": {"minecraft:instant_despawn": {}}},
            "events": {"esb:expire": {"add": {"component_groups": ["esb:expire"]}}},
            "components": {
                "minecraft:type_family": {"family": ["esb_projectile", "inanimate"]},
                "minecraft:collision_box": {"width": 0.5, "height": 0.5},
                "minecraft:projectile": {
                    "on_hit": {
                        "impact_damage": {"damage": g["damage"], "knockback": True, "semi_random_diff_damage": False,
                                          "destroy_on_hit": True},
                        "remove_on_hit": {},
                    },
                    "power": g["speed"], "gravity": 0.0, "inertia": 1.0, "liquid_inertia": 0.8,
                    "uncertainty_base": 0, "uncertainty_multiplier": 0, "anchor": 1, "offset": [0, 0, 0],
                    "hit_sound": "bow.hit", "reflect_on_hurt": True,
                },
                "minecraft:physics": {},
                "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": True},
                "minecraft:timer": {"looping": False, "time": 4, "time_down_event": {"event": "esb:expire"}},
                "minecraft:conditional_bandwidth_optimization": {
                    "default_values": {"max_optimized_distance": 80.0, "max_dropped_ticks": 5, "use_motion_prediction_hints": True}},
            },
        },
    })


def sigil_entity():
    write(os.path.join(BP, "entities", "vitruvian_sigil.json"), {
        "format_version": ENTITY_FMT,
        "minecraft:entity": {
            "description": {
                "identifier": spec.SIGIL_ID, "is_spawnable": False, "is_summonable": True,
                "properties": {"esb:radius": {"type": "int", "range": [1, 20], "default": 7, "client_sync": True}},
            },
            "component_groups": {"esb:expire": {"minecraft:instant_despawn": {}}},
            "events": {"esb:expire": {"add": {"component_groups": ["esb:expire"]}}},
            "components": {
                "minecraft:type_family": {"family": ["esb_fx", "inanimate"]},
                "minecraft:collision_box": {"width": 0.2, "height": 0.2},
                "minecraft:health": {"value": 1, "max": 1},
                "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": "no"}]},
                "minecraft:physics": {"has_gravity": False, "has_collision": False},
                "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
                "minecraft:knockback_resistance": {"value": 1.0},
                "minecraft:fire_immune": True,
                "minecraft:timer": {"looping": False, "time": 9, "time_down_event": {"event": "esb:expire"}},
            },
        },
    })


# ------------------------------------------------------------------------------ items, loot, recipe

def items():
    write(os.path.join(BP, "items", "da_vinci_blueprint.json"), {
        "format_version": "1.21.70",
        "minecraft:item": {
            "description": {"identifier": spec.BLUEPRINT_ID, "menu_category": {"category": "items"}},
            "components": {
                "minecraft:icon": "esb_da_vinci_blueprint",
                "minecraft:display_name": {"value": "item.esb:da_vinci_blueprint.name"},
                "minecraft:max_stack_size": 16,
                "minecraft:glint": True,
            },
        },
    })
    write(os.path.join(BP, "items", "leonardo_codex.json"), {
        "format_version": "1.21.70",
        "minecraft:item": {
            "description": {"identifier": spec.CODEX_ID, "menu_category": {"category": "items"}},
            "components": {
                "minecraft:icon": "esb_leonardo_codex",
                "minecraft:display_name": {"value": "item.esb:leonardo_codex.name"},
                "minecraft:max_stack_size": 1,
                "minecraft:glint": True,
            },
        },
    })
    write(os.path.join(BP, "recipes", "da_vinci_blueprint.json"), {
        "format_version": "1.20.10",
        "minecraft:recipe_shaped": {
            "description": {"identifier": spec.BLUEPRINT_ID},
            "tags": ["crafting_table"],
            "pattern": ["PGP", "GCG", "PDP"],
            "key": {"P": {"item": "minecraft:paper"}, "G": {"item": "minecraft:gold_ingot"},
                    "C": {"item": "minecraft:clock"}, "D": {"item": "minecraft:diamond"}},
            "unlock": [{"item": "minecraft:clock"}],
            "result": {"item": spec.BLUEPRINT_ID, "count": 1},
        },
    })
    entry = lambda item, lo, hi, w=1: {"type": "item", "name": item, "weight": w,  # noqa: E731
                                       "functions": [{"function": "set_count", "count": {"min": lo, "max": hi}}]}
    write(os.path.join(BP, "loot_tables", "entities", "da_vinci.json"), {"pools": [
        {"rolls": 1, "entries": [{"type": "item", "name": spec.CODEX_ID, "weight": 1}]},
        {"rolls": 1, "entries": [entry("minecraft:diamond", 4, 8)]},
        {"rolls": 1, "entries": [entry("minecraft:gold_ingot", 8, 16)]},
        {"rolls": 1, "entries": [entry("minecraft:emerald", 6, 12)]},
        {"rolls": 1, "entries": [entry("minecraft:experience_bottle", 8, 16)]},
        {"rolls": 1, "conditions": [{"condition": "random_chance", "chance": 0.5}],
         "entries": [entry("minecraft:netherite_scrap", 1, 2)]},
        {"rolls": 1, "conditions": [{"condition": "random_chance", "chance": 0.35}],
         "entries": [{"type": "item", "name": "minecraft:totem_of_undying", "weight": 1}]},
    ]})


# ------------------------------------------------------------------------------ Boss 2: Edison

E = BAL["edison"]


def construct(ident, family, health, box, props=None, extra=None, max_health=None):
    comps = {
        "minecraft:type_family": {"family": [family, "esb_construct"]},
        "minecraft:collision_box": {"width": box[0], "height": box[1]},
        "minecraft:health": {"value": health, "max": max_health or health},
        "minecraft:physics": {},
        "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
        "minecraft:knockback_resistance": {"value": 1.0},
        "minecraft:fire_immune": True,
        "minecraft:damage_sensor": {"triggers": [
            {"on_damage": {"filters": {"test": "is_family", "subject": "damager", "value": "esb_boss"}}, "deals_damage": "no"},
            {"cause": "fall", "deals_damage": "no"}, {"cause": "suffocation", "deals_damage": "no"},
            {"cause": "drowning", "deals_damage": "no"}, {"cause": "projectile", "deals_damage": "yes"}]},
        "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0, "breathes_water": True},
    }
    comps.update(extra or {})
    d = {"identifier": ident, "is_spawnable": False, "is_summonable": True}
    if props:
        d["properties"] = props
    return {"format_version": ENTITY_FMT, "minecraft:entity": {
        "description": d,
        "component_groups": {"esb:expire": {"minecraft:instant_despawn": {}}},
        "events": {"esb:expire": {"add": {"component_groups": ["esb:expire"]}}},
        "components": comps}}


def edison_entities():
    boss_entity(ident=spec.EDISON_ID, family="edison", values=spec.EDISON_ACTION_VALUES, B=E, attack=spec.SHANK,
                p2_speed=0.85, cooldown=0.35, hitbox=(1.3, 3.2), loot="loot_tables/entities/edison.json", file="edison.json")
    D = E["dynamo"]
    write(os.path.join(BP, "entities", "dynamo.json"), construct(
        spec.DYNAMO_ID, "esb_dynamo", D["health"], (1.4, 2.1),
        props={"esb:mode": {"type": "enum", "values": ["idle", "charging"], "default": "idle", "client_sync": True},
               "esb:phase": {"type": "int", "range": [1, 2], "default": 1, "client_sync": True}},
        extra={"minecraft:persistent": {}, "minecraft:custom_hit_test": {"hitboxes": [{"width": 1.6, "height": 2.2, "pivot": [0, 1.1, 0]}]}},
        max_health=D["health_phase2"]))
    write(os.path.join(BP, "entities", "electric_chair.json"), construct(
        spec.CHAIR_ID, "esb_chair", E["chair"]["health"], (0.9, 1.4),
        props={"esb:state": {"type": "enum", "values": ["armed", "locked"], "default": "armed", "client_sync": True}},
        extra={"minecraft:timer": {"looping": False, "time": 12, "time_down_event": {"event": "esb:expire"}}}))
    b = E["bulb_toss"]
    write(os.path.join(BP, "entities", "volt_bulb.json"), {
        "format_version": ENTITY_FMT,
        "minecraft:entity": {
            "description": {"identifier": spec.VOLT_BULB_ID, "is_spawnable": False, "is_summonable": True},
            "component_groups": {"esb:expire": {"minecraft:instant_despawn": {}}},
            "events": {"esb:expire": {"add": {"component_groups": ["esb:expire"]}}},
            "components": {
                "minecraft:type_family": {"family": ["esb_projectile", "inanimate"]},
                "minecraft:collision_box": {"width": 0.4, "height": 0.4},
                "minecraft:projectile": {
                    "on_hit": {"impact_damage": {"damage": b["impact_damage"], "knockback": False, "semi_random_diff_damage": False,
                                                 "destroy_on_hit": True},
                               "remove_on_hit": {}},
                    "power": b["speed"], "gravity": 0.03, "inertia": 1.0, "liquid_inertia": 0.8, "uncertainty_base": 0,
                    "uncertainty_multiplier": 0, "anchor": 1, "offset": [0, 0, 0], "hit_sound": "glass",
                },
                "minecraft:physics": {},
                "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": True},
                "minecraft:timer": {"looping": False, "time": 5, "time_down_event": {"event": "esb:expire"}},
                "minecraft:conditional_bandwidth_optimization": {
                    "default_values": {"max_optimized_distance": 80.0, "max_dropped_ticks": 5, "use_motion_prediction_hints": True}},
            },
        },
    })


def fx_entity(ident, family="esb_fx", props=None, lifetime=9):
    d = {"identifier": ident, "is_spawnable": False, "is_summonable": True}
    if props:
        d["properties"] = props
    return {"format_version": ENTITY_FMT, "minecraft:entity": {
        "description": d,
        "component_groups": {"esb:expire": {"minecraft:instant_despawn": {}}},
        "events": {"esb:expire": {"add": {"component_groups": ["esb:expire"]}}},
        "components": {
            "minecraft:type_family": {"family": [family, "esb_fx", "inanimate"]},
            "minecraft:collision_box": {"width": 0.2, "height": 0.2},
            "minecraft:health": {"value": 1, "max": 1},
            "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": "no"}]},
            "minecraft:physics": {"has_gravity": False, "has_collision": False},
            "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
            "minecraft:knockback_resistance": {"value": 1.0},
            "minecraft:fire_immune": True,
            "minecraft:timer": {"looping": False, "time": lifetime, "time_down_event": {"event": "esb:expire"}},
        }}}


def ultimate_entities():
    U = E["ultimate"]
    write(os.path.join(BP, "entities", "sun_bulb.json"), construct(
        spec.SUN_BULB_ID, "esb_sun_bulb", U["bulb_health"], (1.0, 1.5),
        extra={"minecraft:physics": {"has_gravity": False, "has_collision": False},
               "minecraft:timer": {"looping": False, "time": 15, "time_down_event": {"event": "esb:expire"}},
               "minecraft:custom_hit_test": {"hitboxes": [{"width": 1.3, "height": 1.8, "pivot": [0, 0.9, 0]}]}}))
    write(os.path.join(BP, "entities", "volt_marker.json"), fx_entity(
        spec.MARKER_ID, props={"esb:radius": {"type": "int", "range": [1, 12], "default": 3, "client_sync": True}}, lifetime=4))
    write(os.path.join(BP, "entities", "arc_bolt.json"), fx_entity(spec.ARC_BOLT_ID, lifetime=2))


def edison_items():
    write(os.path.join(BP, "items", "volt_shiv.json"), {
        "format_version": "1.21.70",
        "minecraft:item": {
            "description": {"identifier": spec.SHIV_ID, "menu_category": {"category": "equipment"}},
            "components": {
                "minecraft:icon": "esb_volt_shiv",
                "minecraft:display_name": {"value": "item.esb:volt_shiv.name"},
                "minecraft:max_stack_size": 1,
                "minecraft:hand_equipped": True,
                "minecraft:damage": 8,
                "minecraft:durability": {"max_durability": 900},
                "minecraft:enchantable": {"value": 14, "slot": "sword"},
                "minecraft:can_destroy_in_creative": False,
                "minecraft:glint": True,
                "minecraft:tags": {"tags": ["minecraft:is_sword", "esb:boss_weapon"]},
            },
        },
    })
    write(os.path.join(BP, "items", "edison_patent.json"), {
        "format_version": "1.21.70",
        "minecraft:item": {
            "description": {"identifier": spec.PATENT_ID, "menu_category": {"category": "items"}},
            "components": {
                "minecraft:icon": "esb_edison_patent",
                "minecraft:display_name": {"value": "item.esb:edison_patent.name"},
                "minecraft:max_stack_size": 16,
                "minecraft:glint": True,
            },
        },
    })
    write(os.path.join(BP, "recipes", "edison_patent.json"), {
        "format_version": "1.20.10",
        "minecraft:recipe_shaped": {
            "description": {"identifier": spec.PATENT_ID},
            "tags": ["crafting_table"],
            "pattern": ["RGR", "CLC", "RPR"],
            "key": {"R": {"item": "minecraft:redstone"}, "G": {"item": "minecraft:gold_ingot"},
                    "C": {"item": "minecraft:copper_ingot"}, "L": {"item": "minecraft:glowstone"},
                    "P": {"item": "minecraft:paper"}},
            "unlock": [{"item": "minecraft:copper_ingot"}],
            "result": {"item": spec.PATENT_ID, "count": 1},
        },
    })
    entry = lambda item, lo, hi: {"type": "item", "name": item, "weight": 1,  # noqa: E731
                                  "functions": [{"function": "set_count", "count": {"min": lo, "max": hi}}]}
    write(os.path.join(BP, "loot_tables", "entities", "edison.json"), {"pools": [
        {"rolls": 1, "entries": [{"type": "item", "name": spec.SHIV_ID, "weight": 1}]},
        {"rolls": 1, "entries": [entry("minecraft:copper_ingot", 10, 20)]},
        {"rolls": 1, "entries": [entry("minecraft:gold_ingot", 6, 12)]},
        {"rolls": 1, "entries": [entry("minecraft:diamond", 3, 6)]},
        {"rolls": 1, "entries": [entry("minecraft:glowstone", 8, 16)]},
        {"rolls": 1, "entries": [entry("minecraft:emerald", 4, 8)]},
        {"rolls": 1, "conditions": [{"condition": "random_chance", "chance": 0.5}], "entries": [entry("minecraft:netherite_scrap", 1, 2)]},
        {"rolls": 1, "conditions": [{"condition": "random_chance", "chance": 0.35}],
         "entries": [{"type": "item", "name": "minecraft:totem_of_undying", "weight": 1}]},
    ]})


# ------------------------------------------------------------------------------ resource side

def client_entities():
    write(os.path.join(RP, "entity", "brass_gear.entity.json"), {
        "format_version": "1.10.0",
        "minecraft:client_entity": {"description": {
            "identifier": spec.GEAR_ID,
            "materials": {"default": "entity_emissive"},
            "textures": {"default": "textures/entity/brass_gear"},
            "geometry": {"default": "geometry.esb.brass_gear"},
            "animations": {"spin": "animation.esb.brass_gear.spin"},
            "particle_effects": {"trail": "esb:gear_trail"},
            "scripts": {"animate": ["spin"]},
            "render_controllers": ["controller.render.esb.brass_gear"],
        }},
    })
    write(os.path.join(RP, "entity", "vitruvian_sigil.entity.json"), {
        "format_version": "1.10.0",
        "minecraft:client_entity": {"description": {
            "identifier": spec.SIGIL_ID,
            "materials": {"default": "entity_beam_additive"},
            "textures": {"default": "textures/entity/vitruvian_sigil"},
            "geometry": {"default": "geometry.esb.vitruvian_sigil"},
            "animations": {"grow": "animation.esb.vitruvian_sigil.grow"},
            "scripts": {"animate": ["grow"]},
            "render_controllers": ["controller.render.esb.vitruvian_sigil"],
        }},
    })
    no_tint = {"r": 0.0, "g": 0.0, "b": 0.0, "a": 0.0}
    write(os.path.join(RP, "render_controllers", "esb.render_controllers.json"), {
        "format_version": "1.8.0",
        "render_controllers": {
            "controller.render.esb.da_vinci": {
                "geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"]},
            "controller.render.esb.brass_gear": {
                "geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"],
                "is_hurt_color": no_tint, "on_fire_color": no_tint},
            "controller.render.esb.vitruvian_sigil": {
                "geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"],
                "is_hurt_color": no_tint, "on_fire_color": no_tint},
            # Edison and his Dynamo switch to the blue AC texture in phase 2
            "controller.render.esb.edison": {
                "arrays": {"textures": {"Array.skin": ["Texture.default", "Texture.charged"]}},
                "geometry": "Geometry.default", "materials": [{"*": "Material.default"}],
                "textures": ["Array.skin[q.property('esb:phase') == 2 ? 1 : 0]"]},
            "controller.render.esb.dynamo": {
                "arrays": {"textures": {"Array.skin": ["Texture.default", "Texture.charged"]}},
                "geometry": "Geometry.default", "materials": [{"*": "Material.default"}],
                "textures": ["Array.skin[q.property('esb:phase') == 2 ? 1 : 0]"]},
            "controller.render.esb.electric_chair": {
                "geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"]},
            # ultimates: Da Vinci's halo and Edison's sun aura are extra additive layers, rendered only during the ultimate
            "controller.render.esb.da_vinci_halo": {
                "geometry": "Geometry.halo", "materials": [{"*": "Material.halo"}], "textures": ["Texture.halo"],
                "is_hurt_color": no_tint, "on_fire_color": no_tint},
            "controller.render.esb.edison_aura": {
                "geometry": "Geometry.aura", "materials": [{"*": "Material.aura"}], "textures": ["Texture.aura"],
                "is_hurt_color": no_tint, "on_fire_color": no_tint},
            "controller.render.esb.sun_bulb": {
                "geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"]},
            "controller.render.esb.volt_marker": {
                "geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"],
                "is_hurt_color": no_tint, "on_fire_color": no_tint},
            "controller.render.esb.arc_bolt": {
                "geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"],
                "is_hurt_color": no_tint, "on_fire_color": no_tint},
            "controller.render.esb.volt_bulb": {
                "geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"],
                "is_hurt_color": no_tint, "on_fire_color": no_tint},
        },
    })
    write(os.path.join(RP, "textures", "item_texture.json"), {
        "resource_pack_name": "extra_super_boss", "texture_name": "atlas.items",
        "texture_data": {
            "esb_da_vinci_blueprint": {"textures": "textures/items/esb_da_vinci_blueprint"},
            "esb_leonardo_codex": {"textures": "textures/items/esb_leonardo_codex"},
            "esb_volt_shiv": {"textures": "textures/items/esb_volt_shiv"},
            "esb_edison_patent": {"textures": "textures/items/esb_edison_patent"},
        },
    })


LANG = {
    "en_US": {
        "pack.name": PACK_NAME,
        "pack.description": "Boss 1: Leonardo da Vinci, Boss 2: Thomas Edison",
        "entity.esb:da_vinci.name": "Leonardo da Vinci",
        "item.spawn_egg.entity.esb:da_vinci.name": "Spawn Leonardo da Vinci",
        "entity.esb:brass_gear.name": "Brass Gear",
        "entity.esb:vitruvian_sigil.name": "Vitruvian Sigil",
        "item.esb:da_vinci_blueprint.name": "Da Vinci's Sealed Blueprint",
        "item.esb:leonardo_codex.name": "Leonardo's Codex",
        "esb.title.boss": "§6Leonardo da Vinci",
        "esb.subtitle.boss": "§7The Clockwork Maestro",
        "esb.msg.intro": "§6Leonardo da Vinci§r: \"Learning never exhausts the mind.\"",
        "esb.msg.phase2": "§6Leonardo da Vinci§r: \"Once you have tasted flight, you will forever walk the earth with your eyes turned skyward!\"",
        "esb.msg.death": "§6Leonardo da Vinci§r: \"Art is never finished... only abandoned.\"",
        "esb.msg.vitruvian": "§eStep out of the golden circle!",
        "esb.msg.dive": "§eHe is diving at the marked circle!",
        "esb.msg.summon": "§eThe blueprint unrolls... something is being drawn into the world.",
        "esb.msg.summon_busy": "§cLeonardo da Vinci is already nearby.",
        "esb.msg.summon_space": "§cThe blueprint needs open ground: clear a 3x3 area 4 blocks high in front of you.",
        "esb.msg.codex": "§6Inventor's Insight§r: Haste, Speed and Night Vision for %s seconds.",
        "esb.msg.codex_cd": "§7The codex needs %s more seconds.",
        "entity.esb:edison.name": "Thomas Edison",
        "item.spawn_egg.entity.esb:edison.name": "Spawn Thomas Edison",
        "entity.esb:dynamo.name": "The Dynamo",
        "entity.esb:electric_chair.name": "Electric Chair",
        "entity.esb:volt_bulb.name": "Volt Bulb",
        "item.esb:volt_shiv.name": "Volt Shiv",
        "item.esb:edison_patent.name": "Edison's Patent",
        "esb.title.edison": "§eThomas Edison",
        "esb.subtitle.edison": "§7The Wizard of Menlo Park",
        "esb.msg.edison_intro": "§eThomas Edison§r: \"I have not failed. I've just found 10,000 ways that won't work.\"",
        "esb.msg.edison_phase2": "§eThomas Edison§r: \"Genius is one percent inspiration and ninety-nine percent perspiration!\"",
        "esb.msg.edison_death": "§eThomas Edison§r: \"It is very beautiful over there...\"",
        "esb.msg.blackout": "§8The lights go out...",
        "esb.msg.overload": "§eThe Dynamo is overloading! Get away or break line of sight!",
        "esb.msg.chair": "§cYou have been sentenced! Step off the chair!",
        "esb.msg.strapped": "§cStrapped in! Break the chair to escape!",
        "esb.msg.unplugged": "§aThe Dynamo is down! Edison is unplugged!",
        "esb.msg.patent": "§eThe patent is filed... a current hums through the ground.",
        "esb.msg.patent_busy": "§cThomas Edison is already nearby.",
        "entity.esb:sun_bulb.name": "Sun Bulb",
        "entity.esb:volt_marker.name": "Strike Mark",
        "entity.esb:arc_bolt.name": "Arc Bolt",
        "esb.title.opus": "§6§lOPUS MAGNUM",
        "esb.subtitle.opus": "§eStand in a golden sanctuary!",
        "esb.msg.opus": "§6Leonardo da Vinci§r: \"Behold - the measure of all things!\"",
        "esb.msg.opus_judgement": "§6Judgement is coming - get into a golden sanctuary!",
        "esb.title.light": "§e§lLET THERE BE LIGHT",
        "esb.subtitle.light": "§7Smash the bulbs. Hide from the light.",
        "esb.msg.light": "§eThomas Edison§r: \"We will make electricity so cheap that only the rich will burn candles!\"",
        "esb.msg.light_charge": "§eThe bulbs are charging - break line of sight!",
        "esb.msg.light_fizzle": "§aThe broken bulbs fizzle - the light is weakened!",
    },
}


def texts():
    # Bedrock has no Thai UI language (th_TH is not in its language list), so in-game text is English;
    # the Thai guide lives in README.md.
    write(os.path.join(RP, "texts", "languages.json"), list(LANG))
    for code, d in LANG.items():
        write(os.path.join(RP, "texts", f"{code}.lang"), "".join(f"{k}={v}\n" for k, v in d.items() if not k.startswith("pack.")))


# ------------------------------------------------------------------------------ script constants

def ts_constants():
    lines = ["// GENERATED by tools/gen_entity.py from balance.json - do not edit.",
             f"export const BALANCE = {json.dumps({k: v for k, v in BAL.items() if not k.startswith('_')}, indent=2)} as const;", ""]
    write(os.path.join(SRC, "balance.ts"), "\n".join(lines))
    acts = {k: {"length": v["length"], "moments": v["moments"]} for k, v in spec.ACTIONS.items()}
    out = ["// GENERATED by tools/gen_entity.py from tools/spec.py - do not edit.",
           f'export const BOSS_ID = "{spec.BOSS_ID}";',
           f'export const GEAR_ID = "{spec.GEAR_ID}";',
           f'export const SIGIL_ID = "{spec.SIGIL_ID}";',
           f'export const BLUEPRINT_ID = "{spec.BLUEPRINT_ID}";',
           f'export const CODEX_ID = "{spec.CODEX_ID}";',
           f"export const ACTION_VALUES = {json.dumps(spec.ACTION_VALUES)} as const;",
           "export type Action = (typeof ACTION_VALUES)[number];",
           "/** Action lengths and named moments in seconds (identical to the animation files). */",
           f"export const ACTIONS = {json.dumps(acts, indent=2)} as const;",
           f'export const EDISON_ID = "{spec.EDISON_ID}";',
           f'export const SUN_BULB_ID = "{spec.SUN_BULB_ID}";',
           f'export const MARKER_ID = "{spec.MARKER_ID}";',
           f'export const ARC_BOLT_ID = "{spec.ARC_BOLT_ID}";',
           f'export const DYNAMO_ID = "{spec.DYNAMO_ID}";',
           f'export const CHAIR_ID = "{spec.CHAIR_ID}";',
           f'export const VOLT_BULB_ID = "{spec.VOLT_BULB_ID}";',
           f'export const SHIV_ID = "{spec.SHIV_ID}";',
           f'export const PATENT_ID = "{spec.PATENT_ID}";',
           f"export const EDISON_ACTION_VALUES = {json.dumps(spec.EDISON_ACTION_VALUES)} as const;",
           "export type EdisonAction = (typeof EDISON_ACTION_VALUES)[number];",
           f"export const EDISON_ACTIONS = {json.dumps({k: {'length': v['length'], 'moments': v['moments']} for k, v in spec.EDISON_ACTIONS.items()}, indent=2)} as const;",
           ""]
    write(os.path.join(SRC, "spec.ts"), "\n".join(out))


if __name__ == "__main__":
    manifests()
    boss_entity()
    gear_entity()
    sigil_entity()
    items()
    edison_entities()
    ultimate_entities()
    edison_items()
    client_entities()
    texts()
    ts_constants()
    print("entities, items, loot, recipe, client entities, texts, script constants written")
