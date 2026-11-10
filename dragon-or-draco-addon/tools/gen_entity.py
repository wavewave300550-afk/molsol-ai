#!/usr/bin/env python3
"""
Behavior-side data for the Red Dragon, generated from balance.json:

    BP entities/red_dragon.json        custom entity dod:red_dragon (new entity, nothing vanilla replaced)
    BP spawn_rules/red_dragon.json     rare natural spawning in mountains / windswept hills / badlands
    scripts-src/balance.ts             the same trial numbers for the scripts
    RP texts/*.lang, RP textures/item_texture.json

Component groups (switched by the script with events, never two of a kind at once):
    dod:ground  gravity + walk navigation            dod:air     no gravity, script-steered flight
    dod:free    walk speed + stroll/look/chase AI     dod:locked  movement 0, body follows head (attacks)
    dod:territorial  attacks players inside danger_radius   dod:enraged  ... inside warn_radius
    dod:natural despawns far from players (natural spawns only)
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "addon", "behavior_packs", "dragon_or_draco")
RP = os.path.join(ROOT, "addon", "resource_packs", "dragon_or_draco")
B = json.load(open(os.path.join(ROOT, "balance.json")))
E = B["entity"]
T = B["territory"]

PLAYER = {"test": "is_family", "subject": "other", "value": "player"}


def target_group(radius):
    return {
        "minecraft:behavior.nearest_attackable_target": {
            "priority": 2,
            "must_see": True,
            "must_see_forget_duration": 6,
            "reselect_targets": True,
            "within_radius": radius,
            "entity_types": [{"filters": PLAYER, "max_dist": radius}],
        }
    }


def entity():
    base_groups = ["dod:ground", "dod:free", "dod:territorial"]
    keep = B["spawn"]["keep_chance_percent"]
    return {
        "format_version": "1.21.90",
        "minecraft:entity": {
            "description": {
                "identifier": "dod:red_dragon",
                "is_spawnable": True,
                "is_summonable": True,
                "properties": {
                    "dod:flight": {"type": "enum",
                                   "values": ["ground", "takeoff", "launch", "fly", "glide", "landing", "touchdown"],
                                   "default": "ground", "client_sync": True},
                    "dod:action": {"type": "enum",
                                   "values": ["none", "alert", "roar", "bite", "claw", "tail", "buffet", "fire_charge",
                                              "fire_breath", "step_back", "death"],
                                   "default": "none", "client_sync": True},
                    "dod:idle": {"type": "enum",
                                 "values": ["none", "look_left", "look_right", "sniff", "scratch", "tail_sway",
                                            "wing_adjust", "stretch", "yawn", "rest", "rise"],
                                 "default": "none", "client_sync": True},
                    "dod:aim": {"type": "int", "range": [-60, 60], "default": 0, "client_sync": True},
                    "dod:run": {"type": "bool", "default": False, "client_sync": True},
                    "dod:jet": {"type": "int", "range": [0, 16], "default": 12, "client_sync": True},
                },
            },
            "component_groups": {
                "dod:ground": {
                    "minecraft:physics": {"has_gravity": True, "has_collision": True},
                    "minecraft:movement.basic": {},
                    "minecraft:jump.static": {},
                    "minecraft:navigation.walk": {
                        "can_path_over_water": True,
                        "avoid_water": True,
                        "can_path_over_lava": True,
                        "can_walk_in_lava": True,
                        "avoid_damage_blocks": False,
                        "can_sink": True,
                    },
                    "minecraft:variable_max_auto_step": {"base_value": 1.5625, "jump_prevented_value": 1.0625},
                },
                "dod:air": {
                    "minecraft:physics": {"has_gravity": False, "has_collision": True},
                },
                "dod:free": {
                    "minecraft:movement": {"value": E["walk_speed"]},
                    "minecraft:behavior.move_towards_target": {
                        "priority": 3, "speed_multiplier": E["chase_speed_multiplier"], "within_radius": E["follow_range"],
                    },
                    "minecraft:behavior.random_stroll": {
                        "priority": 7, "speed_multiplier": 0.8, "xz_dist": 16, "y_dist": 4, "interval": 160,
                    },
                    "minecraft:behavior.look_at_player": {
                        "priority": 8, "look_distance": T["warn_radius"], "probability": 0.04,
                    },
                    "minecraft:behavior.random_look_around": {"priority": 9},
                },
                "dod:locked": {
                    "minecraft:movement": {"value": 0.0},
                    "minecraft:body_rotation_always_follows_head": {},
                },
                "dod:territorial": target_group(T["danger_radius"]),
                "dod:enraged": target_group(T["warn_radius"]),
                "dod:natural": {
                    "minecraft:despawn": {"despawn_from_distance": {"min_distance": 64, "max_distance": 128}},
                },
                "dod:discard": {"minecraft:instant_despawn": {}},
            },
            "components": {
                "minecraft:type_family": {"family": ["red_dragon", "dragon", "dod_dragon", "monster", "mob"]},
                "minecraft:collision_box": {"width": E["collision_width"], "height": E["collision_height"]},
                "minecraft:custom_hit_test": {
                    "hitboxes": [{"width": E["hitbox_width"], "height": E["hitbox_height"],
                                  "pivot": [0, E["hitbox_height"] / 2, 0]}],
                },
                "minecraft:scale": {"value": E["scale"]},
                "minecraft:health": {"value": E["health"], "max": E["health"]},
                "minecraft:knockback_resistance": {"value": E["knockback_resistance"]},
                "minecraft:follow_range": {"value": E["follow_range"], "max": E["follow_range"]},
                "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
                "minecraft:push_through": {"value": 0},
                "minecraft:fire_immune": True,
                "minecraft:damage_sensor": {
                    "triggers": [
                        {"cause": "fire", "deals_damage": "no"},
                        {"cause": "fire_tick", "deals_damage": "no"},
                        {"cause": "lava", "deals_damage": "no"},
                        {"cause": "magma", "deals_damage": "no"},
                        {"cause": "campfire", "deals_damage": "no"},
                        {"cause": "fall", "deals_damage": "no"},
                        {"cause": "fly_into_wall", "deals_damage": "no"},
                        {"cause": "suffocation", "deals_damage": "no"},
                    ]
                },
                "minecraft:behavior.float": {"priority": 0},
                "minecraft:behavior.hurt_by_target": {"priority": 1},
                "minecraft:experience_reward": {"on_death": f"q.last_hit_by_player ? {E['experience_on_death']} : 0"},
                "minecraft:nameable": {},
                "minecraft:conditional_bandwidth_optimization": {},
            },
            "events": {
                "minecraft:entity_spawned": {"add": {"component_groups": base_groups}},
                # natural spawns (spawn rule) are thinned out here: only keep_chance_percent survive
                "dod:natural_spawn": {
                    "randomize": [
                        {"weight": keep, "add": {"component_groups": base_groups + ["dod:natural"]}},
                        {"weight": 100 - keep, "add": {"component_groups": ["dod:discard"]}},
                    ]
                },
                "dod:lock": {"remove": {"component_groups": ["dod:free"]}, "add": {"component_groups": ["dod:locked"]}},
                "dod:unlock": {"remove": {"component_groups": ["dod:locked"]}, "add": {"component_groups": ["dod:free"]}},
                "dod:to_air": {"remove": {"component_groups": ["dod:ground", "dod:free"]},
                               "add": {"component_groups": ["dod:air", "dod:locked"]}},
                "dod:to_ground": {"remove": {"component_groups": ["dod:air"]}, "add": {"component_groups": ["dod:ground"]}},
                "dod:enrage": {"remove": {"component_groups": ["dod:territorial"]},
                               "add": {"component_groups": ["dod:enraged"]}},
                "dod:calm": {"remove": {"component_groups": ["dod:enraged"]},
                             "add": {"component_groups": ["dod:territorial"]}},
                "dod:dying": {"remove": {"component_groups": ["dod:free", "dod:territorial", "dod:enraged", "dod:air"]},
                              "add": {"component_groups": ["dod:locked", "dod:ground"]}},
            },
        },
    }


def spawn_rules():
    S = B["spawn"]
    common = {
        "minecraft:spawns_on_surface": {},
        "minecraft:weight": {"default": S["weight"]},
        "minecraft:herd": {"min_size": 1, "max_size": 1},
        "minecraft:density_limit": {"surface": 1},
        "minecraft:distance_filter": {"min": 32, "max": 96},
        "minecraft:difficulty_filter": {"min": "easy", "max": "hard"},
        "minecraft:spawn_event": {"event": "dod:natural_spawn"},
    }
    mountains = dict(common)
    mountains["minecraft:height_filter"] = {"min": S["min_height_mountains"], "max": 320}
    mountains["minecraft:biome_filter"] = {"any_of": [
        {"test": "has_biome_tag", "operator": "==", "value": "extreme_hills"},
        {"all_of": [
            {"test": "has_biome_tag", "operator": "==", "value": "mountains"},
            {"test": "has_biome_tag", "operator": "!=", "value": "frozen"},
            {"test": "has_biome_tag", "operator": "!=", "value": "meadow"},
        ]},
    ]}
    badlands = dict(common)
    badlands["minecraft:height_filter"] = {"min": S["min_height_badlands"], "max": 320}
    badlands["minecraft:biome_filter"] = [{"test": "has_biome_tag", "operator": "==", "value": "mesa"}]
    return {
        "format_version": "1.8.0",
        "minecraft:spawn_rules": {
            "description": {"identifier": "dod:red_dragon", "population_control": "monster"},
            "conditions": [mountains, badlands],
        },
    }


def balance_ts():
    lines = [
        "// GENERATED by tools/gen_entity.py from balance.json - edit balance.json, then `npm run build`.",
        "// Trial values awaiting approval; see README (Thai) for what each number does.",
        "export const BALANCE = " + json.dumps({k: v for k, v in B.items() if not k.startswith("_")}, indent=2) + " as const;",
        "",
    ]
    return "\n".join(lines)


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")


def main():
    write(os.path.join(BP, "entities", "red_dragon.json"), entity())
    write(os.path.join(BP, "spawn_rules", "red_dragon.json"), spawn_rules())
    write(os.path.join(ROOT, "scripts-src", "balance.ts"), balance_ts())
    en = ("entity.dod:red_dragon.name=Red Dragon\n"
          "item.spawn_egg.entity.dod:red_dragon.name=Red Dragon Spawn Egg\n"
          "action.hint.exit.dod:red_dragon=\n")
    th = ("entity.dod:red_dragon.name=มังกรแดง\n"
          "item.spawn_egg.entity.dod:red_dragon.name=ไข่เกิดมังกรแดง\n")
    write(os.path.join(RP, "texts", "en_US.lang"), en.replace("action.hint.exit.dod:red_dragon=\n", ""))
    # Bedrock has no Thai UI language (th_TH is not in its language list), so only en_US ships
    write(os.path.join(RP, "texts", "languages.json"), ["en_US"])
    write(os.path.join(RP, "textures", "item_texture.json"), {
        "resource_pack_name": "dragon_or_draco",
        "texture_name": "atlas.items",
        "texture_data": {"dod_red_dragon_spawn_egg": {"textures": "textures/items/dod_red_dragon_spawn_egg"}},
    })
    print("entity, spawn rules, balance.ts, lang, item_texture written")


if __name__ == "__main__":
    main()
