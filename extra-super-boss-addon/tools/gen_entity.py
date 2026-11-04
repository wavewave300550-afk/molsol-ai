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

VERSION = [1, 0, 1]
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
PACK_DESC = "Boss 1: Leonardo da Vinci, the Clockwork Maestro / บอสที่ 1: เลโอนาร์โด ดา วินชี (v1.0.1)"


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


def free_group(speed, attack_duration):
    return {
        "minecraft:movement": {"value": speed},
        "minecraft:behavior.delayed_attack": {
            "priority": 3, "attack_once": False, "track_target": True, "require_complete_path": False,
            "random_stop_interval": 0, "reach_multiplier": 1.3, "speed_multiplier": 1.0,
            "attack_duration": attack_duration, "hit_delay_pct": spec.SLASH["hit_pct"], "cooldown_time": 0.5,
        },
        "minecraft:behavior.random_stroll": {"priority": 8, "speed_multiplier": 0.6, "xz_dist": 10, "y_dist": 3, "interval": 200},
        "minecraft:behavior.look_at_player": {"priority": 9, "look_distance": 24, "probability": 0.05},
        "minecraft:behavior.random_look_around": {"priority": 10},
    }


def boss_entity():
    p2_len = round(spec.SLASH["length"] * 0.8, 2)
    ent = {
        "format_version": ENTITY_FMT,
        "minecraft:entity": {
            "description": {
                "identifier": spec.BOSS_ID,
                "is_spawnable": True,
                "is_summonable": True,
                "properties": {
                    "esb:action": {"type": "enum", "values": spec.ACTION_VALUES, "default": "none", "client_sync": True},
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
                "esb:free": free_group(B["speed"], spec.SLASH["length"]),
                "esb:free_fast": free_group(B["speed_phase2"], p2_len),
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
                "minecraft:type_family": {"family": ["da_vinci", "esb_boss", "monster", "mob"]},
                "minecraft:collision_box": {"width": B["collision_width"], "height": B["collision_height"]},
                "minecraft:custom_hit_test": {"hitboxes": [{"width": 1.6, "height": 3.8, "pivot": [0, 1.9, 0]}]},
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
                "minecraft:loot": {"table": "loot_tables/entities/da_vinci.json"},
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
    write(os.path.join(BP, "entities", "da_vinci.json"), ent)


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
                "properties": {"esb:radius": {"type": "int", "range": [1, 12], "default": 7, "client_sync": True}},
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
        },
    })
    write(os.path.join(RP, "textures", "item_texture.json"), {
        "resource_pack_name": "extra_super_boss", "texture_name": "atlas.items",
        "texture_data": {
            "esb_da_vinci_blueprint": {"textures": "textures/items/esb_da_vinci_blueprint"},
            "esb_leonardo_codex": {"textures": "textures/items/esb_leonardo_codex"},
        },
    })


LANG = {
    "en_US": {
        "pack.name": PACK_NAME,
        "pack.description": "Boss 1: Leonardo da Vinci, the Clockwork Maestro",
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
           f"export const ACTIONS = {json.dumps(acts, indent=2)} as const;", ""]
    write(os.path.join(SRC, "spec.ts"), "\n".join(out))


if __name__ == "__main__":
    manifests()
    boss_entity()
    gear_entity()
    sigil_entity()
    items()
    client_entities()
    texts()
    ts_constants()
    print("entities, items, loot, recipe, client entities, texts, script constants written")
