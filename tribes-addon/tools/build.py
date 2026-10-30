"""
Build script for "Tribes of the Cosmos".

    python3 tools/build.py            -> build/ packs + dist/*.mcaddon

Generates every resource/behavior pack file (models, textures, animations,
render controllers, entities, items, particles, language files, manifests),
compiles the TypeScript gameplay scripts and packages the add-on.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import icons  # noqa: E402
import models  # noqa: E402

BUILD = os.path.join(ROOT, "build")
BP = os.path.join(BUILD, "Tribes_BP")
RP = os.path.join(BUILD, "Tribes_RP")
DIST = os.path.join(ROOT, "dist")

ADDON_NAME = "Tribes of the Cosmos"
VERSION = [1, 0, 0]
MIN_ENGINE = [1, 26, 60]
SERVER_VERSION = "2.11.0"
SERVER_UI_VERSION = "2.3.0"
UUID = {
    "bp_header": "6f1f3c52-8a4e-4f0e-9b3e-1b7d2a9c4e01",
    "bp_data": "6f1f3c52-8a4e-4f0e-9b3e-1b7d2a9c4e02",
    "bp_script": "6f1f3c52-8a4e-4f0e-9b3e-1b7d2a9c4e03",
    "rp_header": "0c9d8e7f-3b2a-4c1d-8e9f-5a6b7c8d9e01",
    "rp_res": "0c9d8e7f-3b2a-4c1d-8e9f-5a6b7c8d9e02",
}

TRIBES = [
    # race index, key, overlay model, display name
    (1, "dinosauroid", "overlay_dinosauroid"),
    (2, "anunnaki", "overlay_anunnaki"),
    (3, "pastafarian", "overlay_pastafarian"),
    (4, "spacer", "overlay_spacer"),
]

ITEMS = {
    "tribal_codex": ("Tribal Codex", "Codex แห่งเผ่า"),
    "primal_fang": ("Primal Fang Totem", "เขี้ยวบรรพกาล"),
    "tablet_of_destinies": ("Tablet of Destinies", "แผ่นจารึกแห่งชะตา"),
    "holy_colander": ("Holy Colander", "กระชอนศักดิ์สิทธิ์"),
    "omni_gauntlet": ("Omni-Gauntlet", "ถุงมือออมนิ"),
}

ENTITIES = {
    # id: (english name, model, texture, lifetime seconds)
    "raptor": ("Dinosauroid Pack Raptor", "raptor"),
    "lamassu": ("Lamassu, Guardian of Anu", "lamassu"),
    "noodle_avatar": ("Avatar of the Flying Spaghetti Monster", "noodle_avatar"),
    "meatball": ("Holy Meatball", "meatball"),
    "drone": ("Spacer Combat Drone", "drone"),
}

PARTICLE_COLORS = {
    "gold": (1.0, 0.82, 0.25),
    "cyan": (0.30, 0.92, 1.0),
    "green": (0.45, 0.95, 0.35),
    "sauce": (0.85, 0.12, 0.08),
    "noodle": (0.98, 0.86, 0.42),
    "purple": (0.72, 0.38, 1.0),
    "orange": (1.0, 0.52, 0.16),
    "white": (1.0, 1.0, 1.0),
}


# --------------------------------------------------------------------------- io helpers

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- manifests

def manifests():
    bp = {
        "format_version": 2,
        "header": {
            "name": "pack.name",
            "description": "pack.description",
            "uuid": UUID["bp_header"],
            "version": VERSION,
            "min_engine_version": MIN_ENGINE,
        },
        "modules": [
            {"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
            {"type": "script", "language": "javascript", "uuid": UUID["bp_script"],
             "version": VERSION, "entry": "scripts/main.js"},
        ],
        "dependencies": [
            {"module_name": "@minecraft/server", "version": SERVER_VERSION},
            {"module_name": "@minecraft/server-ui", "version": SERVER_UI_VERSION},
            {"uuid": UUID["rp_header"], "version": VERSION},
        ],
        "metadata": {"authors": ["Tribes of the Cosmos team"], "product_type": "addon"},
    }
    rp = {
        "format_version": 2,
        "header": {
            "name": "pack.name",
            "description": "pack.description",
            "uuid": UUID["rp_header"],
            "version": VERSION,
            "min_engine_version": MIN_ENGINE,
        },
        "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
        "dependencies": [{"uuid": UUID["bp_header"], "version": VERSION}],
        "metadata": {"authors": ["Tribes of the Cosmos team"], "product_type": "addon"},
    }
    write_json(os.path.join(BP, "manifest.json"), bp)
    write_json(os.path.join(RP, "manifest.json"), rp)
    icon = icons.pack_icon()
    for p in (BP, RP):
        icon.save(os.path.join(p, "pack_icon.png"))


# --------------------------------------------------------------------------- models & textures

def build_models():
    built = {}
    bounds = {
        "raptor": (2.5, 2.5, 1.0), "lamassu": (4, 4, 1.5), "noodle_avatar": (4, 4, 1.0),
        "meatball": (1, 1, 0.25), "drone": (2, 2, 0.5),
    }
    for name, fn in models.ALL.items():
        m = fn()
        img = m.paint()
        bw, bh, oy = bounds.get(name, (3, 3.5, 1.25))
        write_json(os.path.join(RP, "models", "entity", "tribes", f"{name}.geo.json"),
                   m.geometry_json(bw, bh, oy))
        tex = os.path.join(RP, "textures", "entity", "tribes", f"{name}.png")
        os.makedirs(os.path.dirname(tex), exist_ok=True)
        img.save(tex)
        built[name] = m
    return built


def build_icons():
    data = {}
    for name in icons.ICONS:
        p = os.path.join(RP, "textures", "items", "tribes", f"{name}.png")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        icons.icon(name).save(p)
        data[f"tribes_{name}"] = {"textures": f"textures/items/tribes/{name}"}
    write_json(os.path.join(RP, "textures", "item_texture.json"),
               {"resource_pack_name": "tribes", "texture_name": "atlas.items", "texture_data": data})
    p = os.path.join(RP, "textures", "particle", "tribes_spark.png")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    icons.particle_sprite().save(p)


# --------------------------------------------------------------------------- particles

def particle(identifier, color, *, count=1, speed=0.25, lifetime=(0.45, 0.8), size=0.12,
             material="particles_add", gravity=0.0, drag=1.5, radius=0.0, rise=0.25):
    r, g, b = color
    comps = {
        "minecraft:emitter_rate_instant": {"num_particles": count},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:particle_initial_speed": speed,
        "minecraft:particle_lifetime_expression": {
            "max_lifetime": f"{lifetime[0]} + variable.particle_random_1 * {round(lifetime[1] - lifetime[0], 3)}"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, rise - gravity, 0],
                                              "linear_drag_coefficient": drag},
        "minecraft:particle_appearance_billboard": {
            "size": [f"{size} * (1.0 - variable.particle_age / variable.particle_lifetime * 0.7)",
                     f"{size} * (1.0 - variable.particle_age / variable.particle_lifetime * 0.7)"],
            "facing_camera_mode": "rotate_xyz",
            "uv": {"texture_width": 16, "texture_height": 16, "uv": [0, 0], "uv_size": [16, 16]},
        },
        "minecraft:particle_appearance_tinting": {
            "color": [r, g, b, "1.0 - variable.particle_age / variable.particle_lifetime * 0.5"]},
    }
    if radius > 0:
        comps["minecraft:emitter_shape_sphere"] = {"radius": radius, "surface_only": False, "direction": "outwards"}
    else:
        comps["minecraft:emitter_shape_point"] = {
            "direction": ["math.random(-1, 1)", "math.random(-0.3, 1)", "math.random(-1, 1)"]}
    return {
        "format_version": "1.10.0",
        "particle_effect": {
            "description": {"identifier": identifier,
                            "basic_render_parameters": {"material": material,
                                                        "texture": "textures/particle/tribes_spark"}},
            "components": comps,
        },
    }


def build_particles():
    ids = []
    for name, col in PARTICLE_COLORS.items():
        mat = "particles_alpha" if name in ("sauce", "noodle") else "particles_add"
        mote = particle(f"tribes:{name}_mote", col, size=0.14, speed=0.05, material=mat, rise=0.0)
        burst = particle(f"tribes:{name}_burst", col, count=16, speed=3.2, size=0.16, drag=3.5,
                         radius=0.2, material=mat, gravity=1.0 if name == "sauce" else 0.0)
        big = particle(f"tribes:{name}_flare", col, count=1, speed=0, size=0.5, lifetime=(0.35, 0.5), material=mat,
                       rise=0.0)
        for p in (mote, burst, big):
            ident = p["particle_effect"]["description"]["identifier"]
            ids.append(ident)
            write_json(os.path.join(RP, "particles", "tribes", ident.split(":")[1] + ".json"), p)
    return ids


# --------------------------------------------------------------------------- animations

def anim(loop=True, bones=None, length=None):
    a = {"loop": loop, "bones": bones or {}}
    if length:
        a["animation_length"] = length
    return a


def build_animations():
    t = "query.life_time"
    walk = "query.modified_distance_moved"
    speed = "query.modified_move_speed"
    overlay = {
        "animation.tribes.overlay.dinosauroid": anim(bones={
            "dino_tail1": {"rotation": [f"math.sin({t} * 120) * 3", f"math.sin({t} * 150) * 9 + math.sin({walk} * 25) * 10 * {speed}", 0]},
            "dino_tail2": {"rotation": [0, f"math.sin({t} * 150 - 45) * 11 + math.sin({walk} * 25 - 40) * 12 * {speed}", 0]},
            "dino_tail3": {"rotation": [0, f"math.sin({t} * 150 - 90) * 14 + math.sin({walk} * 25 - 80) * 14 * {speed}", 0]},
        }),
        "animation.tribes.overlay.anunnaki": anim(bones={
            "anu_wing_ru": {"rotation": [0, f"-math.sin({t} * 70) * 5", f"-math.sin({t} * 70) * 7 - (query.is_on_ground ? 0 : 24)"]},
            "anu_wing_lu": {"rotation": [0, f"math.sin({t} * 70) * 5", f"math.sin({t} * 70) * 7 + (query.is_on_ground ? 0 : 24)"]},
            "anu_wing_rl": {"rotation": [0, f"-math.sin({t} * 70 - 30) * 4", f"-math.sin({t} * 70 - 30) * 5 - (query.is_on_ground ? 0 : 30)"]},
            "anu_wing_ll": {"rotation": [0, f"math.sin({t} * 70 - 30) * 4", f"math.sin({t} * 70 - 30) * 5 + (query.is_on_ground ? 0 : 30)"]},
        }),
        "animation.tribes.overlay.pastafarian": anim(bones=dict(
            {f"fsm_ten{i}_a": {"rotation": [f"math.sin({t} * 110 + {i * 60}) * 10", f"math.cos({t} * 80 + {i * 47}) * 14", 0]} for i in range(6)},
            **{f"fsm_ten{i}_b": {"rotation": [f"math.sin({t} * 110 + {i * 60 - 50}) * 16", 0, f"math.cos({t} * 90 + {i * 33}) * 8"]} for i in range(6)},
            **{f"fsm_ten{i}_c": {"rotation": [f"math.sin({t} * 110 + {i * 60 - 100}) * 22", 0, 0]} for i in range(6)},
            fsm_stalk_r={"rotation": [f"math.sin({t} * 60) * 6", 0, f"math.sin({t} * 45) * 7"]},
            fsm_stalk_l={"rotation": [f"math.sin({t} * 60 + 90) * 6", 0, f"math.sin({t} * 45 + 120) * 7"]},
        )),
        "animation.tribes.overlay.spacer": anim(bones={
            "space_flame_r": {"scale": [1, f"0.55 + math.sin({t} * 1900) * 0.15 + (query.is_on_ground ? 0 : 0.9)", 1]},
            "space_flame_l": {"scale": [1, f"0.55 + math.sin({t} * 1900 + 60) * 0.15 + (query.is_on_ground ? 0 : 0.9)", 1]},
        }),
    }
    write_json(os.path.join(RP, "animations", "tribes_overlays.animation.json"),
               {"format_version": "1.8.0", "animations": overlay})

    leg = f"math.cos({walk} * 38.17) * 40.0 * {speed}"
    leg_inv = f"-math.cos({walk} * 38.17) * 40.0 * {speed}"
    mobs = {
        "animation.tribes.raptor.walk": anim(bones={
            "leg_r": {"rotation": [leg, 0, 0]},
            "leg_l": {"rotation": [leg_inv, 0, 0]},
            "arm_r": {"rotation": [f"math.sin({walk} * 38.17) * 10 * {speed}", 0, 0]},
            "arm_l": {"rotation": [f"-math.sin({walk} * 38.17) * 10 * {speed}", 0, 0]},
            "body": {"position": [0, f"math.abs(math.sin({walk} * 38.17)) * 0.8 * {speed}", 0]},
        }),
        "animation.tribes.raptor.idle": anim(bones={
            "tail1": {"rotation": [f"math.sin({t} * 80) * 3", f"math.sin({t} * 100) * 10", 0]},
            "tail2": {"rotation": [0, f"math.sin({t} * 100 - 40) * 12", 0]},
            "tail3": {"rotation": [0, f"math.sin({t} * 100 - 80) * 16", 0]},
            "neck": {"rotation": [f"math.sin({t} * 90) * 2", 0, 0]},
            "head": {"rotation": ["query.target_x_rotation * 0.6", "query.target_y_rotation * 0.8", 0]},
            "jaw": {"rotation": [f"query.has_target ? (math.sin({t} * 900) * 14 + 16) : (math.sin({t} * 60) * 3 + 3)", 0, 0]},
        }),
        "animation.tribes.lamassu.walk": anim(bones={
            "leg_fr": {"rotation": [leg, 0, 0]},
            "leg_bl": {"rotation": [leg, 0, 0]},
            "leg_fl": {"rotation": [leg_inv, 0, 0]},
            "leg_br": {"rotation": [leg_inv, 0, 0]},
        }),
        "animation.tribes.lamassu.idle": anim(bones={
            "head": {"rotation": ["query.target_x_rotation * 0.5", "query.target_y_rotation * 0.7", 0]},
            "wing_r": {"rotation": [f"math.sin({t} * 50) * 4", 0, f"math.sin({t} * 50) * 5 + (query.has_target ? 18 : 0)"]},
            "wing_l": {"rotation": [f"math.sin({t} * 50) * 4", 0, f"-math.sin({t} * 50) * 5 - (query.has_target ? 18 : 0)"]},
            "body": {"position": [0, f"math.sin({t} * 50) * 0.25", 0]},
        }),
        "animation.tribes.noodle_avatar.float": anim(bones=dict(
            body={"position": [0, f"math.sin({t} * 80) * 1.6", 0], "rotation": [0, f"math.sin({t} * 30) * 8", 0]},
            stalk_r={"rotation": [f"math.sin({t} * 55) * 8", 0, f"math.sin({t} * 40) * 10"]},
            stalk_l={"rotation": [f"math.sin({t} * 55 + 100) * 8", 0, f"math.sin({t} * 40 + 140) * 10"]},
            meatball_r={"rotation": [f"math.sin({t} * 70) * 6", 0, 0]},
            meatball_l={"rotation": [f"math.sin({t} * 70 + 120) * 6", 0, 0]},
            **{f"ten{i}_a": {"rotation": [f"math.sin({t} * 120 + {i * 45}) * 14", 0, f"math.cos({t} * 100 + {i * 45}) * 14"]} for i in range(8)},
            **{f"ten{i}_b": {"rotation": [f"math.sin({t} * 120 + {i * 45 - 60}) * 20", 0, f"math.cos({t} * 100 + {i * 45 - 60}) * 18"]} for i in range(8)},
            **{f"ten{i}_c": {"rotation": [f"math.sin({t} * 120 + {i * 45 - 120}) * 26", 0, f"math.cos({t} * 100 + {i * 45 - 120}) * 22"]} for i in range(8)},
        )),
        "animation.tribes.meatball.spin": anim(bones={
            "ball": {"rotation": [f"{t} * 720", f"{t} * 360", 0]},
        }),
        "animation.tribes.drone.hover": anim(bones=dict(
            body={"position": [0, f"math.sin({t} * 160) * 0.6", 0],
                  "rotation": [f"math.sin({t} * 90) * 4", 0, f"math.cos({t} * 70) * 4"]},
            **{f"rotor{i}": {"rotation": [0, f"{t} * {1440 + i * 120}", 0]} for i in range(4)},
        )),
    }
    write_json(os.path.join(RP, "animations", "tribes_mobs.animation.json"),
               {"format_version": "1.8.0", "animations": mobs})
    return overlay, mobs


# --------------------------------------------------------------------------- render controllers + client entities

def build_render_controllers():
    rc = {"controller.render.tribes.default": {
        "geometry": "Geometry.default",
        "materials": [{"*": "Material.default"}],
        "textures": ["Texture.default"],
    }}
    for idx, key, model in TRIBES:
        rc[f"controller.render.tribes.overlay_{key}"] = {
            "geometry": f"Geometry.tribes_{key}",
            "materials": [{"*": "Material.tribes_overlay"}],
            "textures": [f"Texture.tribes_{key}"],
        }
    write_json(os.path.join(RP, "render_controllers", "tribes.render_controllers.json"),
               {"format_version": "1.8.0", "render_controllers": rc})


def client_entity(identifier, model, animations, animate):
    return {
        "format_version": "1.10.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": identifier,
                "materials": {"default": "entity_alphatest"},
                "textures": {"default": f"textures/entity/tribes/{model}"},
                "geometry": {"default": models.ALL[model]().identifier},
                "animations": animations,
                "scripts": {"animate": animate},
                "render_controllers": ["controller.render.tribes.default"],
            }
        },
    }


def build_client_entities():
    ents = {
        "raptor": client_entity("tribes:raptor", "raptor",
                                {"walk": "animation.tribes.raptor.walk", "idle": "animation.tribes.raptor.idle"},
                                ["walk", "idle"]),
        "lamassu": client_entity("tribes:lamassu", "lamassu",
                                 {"walk": "animation.tribes.lamassu.walk", "idle": "animation.tribes.lamassu.idle"},
                                 ["walk", "idle"]),
        "noodle_avatar": client_entity("tribes:noodle_avatar", "noodle_avatar",
                                       {"float": "animation.tribes.noodle_avatar.float"}, ["float"]),
        "meatball": client_entity("tribes:meatball", "meatball",
                                  {"spin": "animation.tribes.meatball.spin"}, ["spin"]),
        "drone": client_entity("tribes:drone", "drone", {"hover": "animation.tribes.drone.hover"}, ["hover"]),
    }
    for name, data in ents.items():
        write_json(os.path.join(RP, "entity", "tribes", f"{name}.entity.json"), data)

    # ---- player override: vanilla player + tribe overlays driven by the tribes:race property
    pe = load_json(os.path.join(HERE, "vanilla", "player.entity.json"))
    desc = pe["minecraft:client_entity"]["description"]
    desc["materials"]["tribes_overlay"] = "entity_alphatest"
    for idx, key, model in TRIBES:
        desc["textures"][f"tribes_{key}"] = f"textures/entity/tribes/{model}"
        desc["geometry"][f"tribes_{key}"] = models.ALL[model]().identifier
        desc["animations"][f"tribes_{key}"] = f"animation.tribes.overlay.{key}"
        cond = f"query.has_property('tribes:race') && query.property('tribes:race') == {idx}"
        desc["scripts"]["animate"].append({f"tribes_{key}": cond})
        desc["render_controllers"].append({
            f"controller.render.tribes.overlay_{key}":
                f"!variable.is_first_person && !variable.map_face_icon && !query.is_spectator && {cond}"})
    write_json(os.path.join(RP, "entity", "player.entity.json"), pe)


# --------------------------------------------------------------------------- behaviour entities

def summon_entity(identifier, families, components, extra_groups=None, extra_events=None, lifetime=60):
    groups = {"tribes:despawn": {"minecraft:instant_despawn": {}}}
    groups.update(extra_groups or {})
    events = {"tribes:despawn": {"add": {"component_groups": ["tribes:despawn"]}}}
    events.update(extra_events or {})
    base = {
        "minecraft:type_family": {"family": families},
        "minecraft:timer": {"looping": False, "time": lifetime, "randomInterval": False,
                            "time_down_event": {"event": "tribes:despawn", "target": "self"}},
        "minecraft:conditional_bandwidth_optimization": {},
    }
    base.update(components)
    return {
        "format_version": "1.21.0",
        "minecraft:entity": {
            "description": {"identifier": identifier, "is_spawnable": False, "is_summonable": True},
            "component_groups": groups,
            "components": base,
            "events": events,
        },
    }


MONSTER_FILTER = {"all_of": [{"test": "is_family", "subject": "other", "value": "monster"},
                             {"test": "is_family", "subject": "other", "operator": "!=", "value": "creeper"}]}


def guardian_components(health, damage, speed, width, height, attack_family_creeper=False):
    return {
        "minecraft:health": {"value": health, "max": health},
        "minecraft:attack": {"damage": damage},
        "minecraft:movement": {"value": speed},
        "minecraft:movement.basic": {},
        "minecraft:navigation.walk": {"can_path_over_water": True, "avoid_damage_blocks": True, "can_open_doors": False},
        "minecraft:jump.static": {},
        "minecraft:can_climb": {},
        "minecraft:collision_box": {"width": width, "height": height},
        "minecraft:physics": {},
        "minecraft:pushable": {"is_pushable": True, "is_pushable_by_piston": True},
        "minecraft:knockback_resistance": {"value": 0.5},
        "minecraft:nameable": {},
        "minecraft:fire_immune": {},
        "minecraft:damage_sensor": {"triggers": [
            {"cause": "fall", "deals_damage": "no"},
            {"cause": "lightning", "deals_damage": "no"},
            {"cause": "fire", "deals_damage": "no"},
            {"cause": "fire_tick", "deals_damage": "no"},
            {"on_damage": {"filters": {"test": "is_family", "subject": "other", "value": "player"}}, "deals_damage": "no"},
        ]},
        "minecraft:behavior.float": {"priority": 0},
        "minecraft:behavior.melee_box_attack": {"priority": 3, "speed_multiplier": 1.35, "track_target": True},
        "minecraft:behavior.nearest_attackable_target": {
            "priority": 4, "must_see": False, "reselect_targets": True, "within_radius": 24,
            "entity_types": [{"filters": {"all_of": [{"test": "is_family", "subject": "other", "value": "monster"}]},
                              "max_dist": 24}],
        },
        "minecraft:behavior.hurt_by_target": {"priority": 2,
                                              "entity_types": {"filters": {"test": "is_family", "subject": "other",
                                                                           "operator": "!=", "value": "player"}}},
        "minecraft:behavior.random_stroll": {"priority": 8, "speed_multiplier": 0.9},
        "minecraft:behavior.look_at_player": {"priority": 9, "look_distance": 8, "probability": 0.05},
        "minecraft:behavior.random_look_around": {"priority": 10},
        "minecraft:tameable": {"probability": 0, "tame_items": "bone",
                               "tame_event": {"event": "tribes:on_tame", "target": "self"}},
    }


TAMED_GROUP = {
    "tribes:tamed": {
        "minecraft:is_tamed": {},
        "minecraft:behavior.owner_hurt_by_target": {"priority": 1},
        "minecraft:behavior.owner_hurt_target": {"priority": 2},
        "minecraft:behavior.follow_owner": {"priority": 6, "speed_multiplier": 1.3, "start_distance": 10,
                                            "stop_distance": 3},
    }
}
TAME_EVENT = {"tribes:on_tame": {"add": {"component_groups": ["tribes:tamed"]}}}


def floating_components(width, height):
    return {
        "minecraft:health": {"value": 100, "max": 100},
        "minecraft:collision_box": {"width": width, "height": height},
        "minecraft:physics": {"has_gravity": False, "has_collision": False},
        "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
        "minecraft:knockback_resistance": {"value": 1.0},
        "minecraft:fire_immune": {},
        "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": "no"}]},
    }


def build_bp_entities():
    write_json(os.path.join(BP, "entities", "tribes", "raptor.json"), summon_entity(
        "tribes:raptor", ["tribes_summon", "raptor", "mob"],
        guardian_components(26, 5, 0.36, 0.8, 1.4), TAMED_GROUP, TAME_EVENT, lifetime=45))
    write_json(os.path.join(BP, "entities", "tribes", "lamassu.json"), summon_entity(
        "tribes:lamassu", ["tribes_summon", "lamassu", "mob"],
        dict(guardian_components(90, 11, 0.3, 1.5, 2.6), **{"minecraft:knockback_resistance": {"value": 1.0}}),
        TAMED_GROUP, TAME_EVENT, lifetime=50))
    write_json(os.path.join(BP, "entities", "tribes", "noodle_avatar.json"), summon_entity(
        "tribes:noodle_avatar", ["tribes_summon", "inanimate"], floating_components(1.0, 1.5), lifetime=35))
    write_json(os.path.join(BP, "entities", "tribes", "drone.json"), summon_entity(
        "tribes:drone", ["tribes_summon", "inanimate"], floating_components(0.5, 0.5), lifetime=45))
    meatball = {
        "format_version": "1.21.0",
        "minecraft:entity": {
            "description": {"identifier": "tribes:meatball", "is_spawnable": False, "is_summonable": True},
            "components": {
                "minecraft:type_family": {"family": ["tribes_projectile", "inanimate"]},
                "minecraft:collision_box": {"width": 0.4, "height": 0.4},
                "minecraft:projectile": {
                    "on_hit": {"impact_damage": {"damage": 4, "knockback": True},
                               "remove_on_hit": {}},
                    "power": 1.4, "gravity": 0.03, "inertia": 1.0, "liquid_inertia": 0.9,
                    "anchor": 1, "offset": [0, -0.1, 0], "uncertainty_base": 0, "uncertainty_multiplier": 0,
                    "hit_sound": "mob.slime.big",
                },
                "minecraft:physics": {},
                "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": True},
                "minecraft:timer": {"looping": False, "time": 8, "randomInterval": False,
                                    "time_down_event": {"event": "tribes:despawn", "target": "self"}},
                "minecraft:conditional_bandwidth_optimization": {
                    "default_values": {"max_optimized_distance": 80.0, "max_dropped_ticks": 5,
                                       "use_motion_prediction_hints": True}},
            },
            "component_groups": {"tribes:despawn": {"minecraft:instant_despawn": {}}},
            "events": {"tribes:despawn": {"add": {"component_groups": ["tribes:despawn"]}}},
        },
    }
    write_json(os.path.join(BP, "entities", "tribes", "meatball.json"), meatball)

    # ---- player override: vanilla player + synced tribe property used by the client renderer
    pl = load_json(os.path.join(HERE, "vanilla", "player.json"))
    pl["minecraft:entity"]["description"]["properties"] = {
        "tribes:race": {"type": "int", "range": [0, 4], "default": 0, "client_sync": True}
    }
    write_json(os.path.join(BP, "entities", "player.json"), pl)


def build_items():
    for key in ITEMS:
        item = {
            "format_version": "1.21.60",
            "minecraft:item": {
                "description": {"identifier": f"tribes:{key}", "menu_category": {"category": "equipment"}},
                "components": {
                    "minecraft:icon": {"textures": {"default": f"tribes_{key}"}},
                    "minecraft:display_name": {"value": f"item.tribes:{key}.name"},
                    "minecraft:max_stack_size": 1,
                    "minecraft:hand_equipped": key != "tribal_codex",
                    "minecraft:glint": key != "tribal_codex",
                    "minecraft:tags": {"tags": ["tribes:relic"] if key != "tribal_codex" else ["tribes:codex"]},
                },
            },
        }
        write_json(os.path.join(BP, "items", "tribes", f"{key}.json"), item)
    recipe = {
        "format_version": "1.20.10",
        "minecraft:recipe_shapeless": {
            "description": {"identifier": "tribes:tribal_codex"},
            "tags": ["crafting_table"],
            "ingredients": [{"item": "minecraft:book"}, {"item": "minecraft:ender_pearl"}],
            "result": {"item": "tribes:tribal_codex"},
            "unlock": [{"item": "minecraft:book"}],
        },
    }
    write_json(os.path.join(BP, "recipes", "tribal_codex.json"), recipe)


# --------------------------------------------------------------------------- language

def build_lang():
    en = [
        f"pack.name={ADDON_NAME}",
        "pack.description=Four playable tribes: Dinosauroid, Anunnaki, Flying Spaghetti Monster and Spacer.",
    ]
    th = [
        f"pack.name={ADDON_NAME}",
        "pack.description=สี่เผ่าที่เล่นได้: Dinosauroid, Anunnaki, Flying Spaghetti Monster และ Spacer",
    ]
    for key, (name_en, name_th) in ITEMS.items():
        en.append(f"item.tribes:{key}.name={name_en}")
        th.append(f"item.tribes:{key}.name={name_th}")
    for key, (name_en, _) in ENTITIES.items():
        en.append(f"entity.tribes:{key}.name={name_en}")
        th.append(f"entity.tribes:{key}.name={name_en}")
    for root in (BP, RP):
        write_text(os.path.join(root, "texts", "en_US.lang"), "\n".join(en if root == RP else en[:2]) + "\n")
        write_text(os.path.join(root, "texts", "languages.json"), json.dumps(["en_US"], indent=2) + "\n")
    # Bedrock ships no Thai UI language; keep a Thai reference file next to the sources.
    write_text(os.path.join(ROOT, "docs", "th_TH.reference.lang"), "\n".join(th) + "\n")


# --------------------------------------------------------------------------- scripts

def build_scripts():
    out = os.path.join(BP, "scripts")
    tsc = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        raise SystemExit("TypeScript not installed: run `npm install` in tribes-addon/")
    res = subprocess.run([tsc, "-p", os.path.join(ROOT, "tsconfig.json"), "--outDir", out],
                         capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout, res.stderr)
        raise SystemExit("TypeScript compilation failed")


# --------------------------------------------------------------------------- packaging

def zip_dir(zf, folder, arc_root):
    for dirpath, _, files in os.walk(folder):
        for fn in sorted(files):
            full = os.path.join(dirpath, fn)
            zf.write(full, os.path.join(arc_root, os.path.relpath(full, folder)))


def package():
    os.makedirs(DIST, exist_ok=True)
    base = "Tribes_of_the_Cosmos"
    addon = os.path.join(DIST, f"{base}.mcaddon")
    with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as zf:
        zip_dir(zf, BP, "Tribes_BP")
        zip_dir(zf, RP, "Tribes_RP")
    for folder, suffix in ((BP, "BP"), (RP, "RP")):
        with zipfile.ZipFile(os.path.join(DIST, f"{base}_{suffix}.mcpack"), "w", zipfile.ZIP_DEFLATED) as zf:
            zip_dir(zf, folder, "")
    return addon


def main():
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    manifests()
    build_models()
    build_icons()
    build_particles()
    build_animations()
    build_render_controllers()
    build_client_entities()
    build_bp_entities()
    build_items()
    build_lang()
    build_scripts()
    addon = package()
    print("built", os.path.relpath(addon, ROOT))


if __name__ == "__main__":
    main()
