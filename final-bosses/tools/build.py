"""
Build FIVE FINAL BOSSES:   python3 tools/build.py  ->  build/ packs + dist/Five_Final_Bosses.mcaddon

Models (solid + additive energy layer, auto-deflickered), HD textures, animations, animation
controllers, render controllers, client and behaviour entities, items, particles, language,
manifests, compiled scripts and packaging.
"""
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
import art  # noqa: E402
import registry  # noqa: E402
from modelkit import deflicker, island_report, zfight_report  # noqa: E402

BUILD = os.path.join(ROOT, "build")
BP = os.path.join(BUILD, "FinalBosses_BP")
RP = os.path.join(BUILD, "FinalBosses_RP")
DIST = os.path.join(ROOT, "dist")
NAME = "Five Final Bosses"
VERSION = [1, 0, 0]
MIN_ENGINE = [1, 26, 60]
UUID = {"bp": "810ed5c5-f352-4f3c-a74b-4e3c0e602551", "bp_data": "ee84db5d-0530-4aaa-afe8-5f589d23ef1f",
        "bp_script": "790f2122-b6ad-4a4d-85e0-8982adaf3c06", "rp": "d7c4c2eb-ab87-48e5-97de-9cdc4bebc62c",
        "rp_res": "b710577f-504c-4b5f-b8c6-60966b276e5a"}

BOSSES = {
    # key: (name, hp, collision w, h, client scale, egg base, egg overlay, bounds (w, h, offset))
    "void_emperor": ("The Void Emperor", 900, 2.6, 4.2, 1.15, "#14081f", "#a64dff", (8, 8, 3)),
    "titan": ("The Titan of Creation", 1100, 3.0, 6.4, 1.0, "#5a3a14", "#ffb347", (8, 9, 3.5)),
    "devouring_star": ("The Devouring Star", 820, 3.2, 3.0, 1.0, "#1a0d06", "#ff7a1a", (10, 6, 2.5)),
    "world_parasite": ("The World Parasite", 1000, 5.0, 3.6, 1.0, "#3b6b2a", "#b5485b", (10, 8, 2.5)),
    "choir": ("The Choir of Mirrors", 780, 2.2, 4.4, 1.1, "#d9e6f2", "#ffd27a", (8, 8, 3.5)),
}
STATES = ["idle", "move", "atk_a", "atk_b", "atk_c", "channel", "ultimate", "stagger", "death", "spawn", "dormant", "burrow", "atk_d"]
ITEMS = {
    "boss_sigil": "Sigil of the Final Hour",
    "crown_of_absence": "Crown of Absence",
    "forge_heart": "Heart of the Forge",
    "star_heart": "Heart of the Devouring Star",
    "parasite_seed": "Parasite Seed",
    "shard_of_truth": "Shard of Truth",
}
COOLDOWNS = {"crown_of_absence": ("fb_crown", 30), "forge_heart": ("fb_forge", 20), "star_heart": ("fb_star", 5),
             "parasite_seed": ("fb_seed", 30), "shard_of_truth": ("fb_shard", 45)}
HUES = {"void": (0.62, 0.3, 1.0), "gold": (1.0, 0.82, 0.35), "orange": (1.0, 0.55, 0.15), "blue": (0.35, 0.7, 1.0),
        "star": (1.0, 0.95, 0.6), "flame": (1.0, 0.42, 0.1), "green": (0.45, 1.0, 0.35), "red": (1.0, 0.2, 0.2),
        "silver": (0.85, 0.92, 1.0), "white": (1.0, 1.0, 1.0), "cyan": (0.3, 0.95, 1.0)}
TONES = {"void": (0.12, 0.02, 0.2), "dust": (0.45, 0.38, 0.3), "spore": (0.45, 0.6, 0.2), "ash": (0.25, 0.24, 0.26)}


def wj(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def wt(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def save(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)


def manifests():
    wj(os.path.join(BP, "manifest.json"), {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["bp"], "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
                    {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION, "entry": "scripts/main.js"}],
        "dependencies": [{"module_name": "@minecraft/server", "version": "2.11.0"}, {"module_name": "@minecraft/server-ui", "version": "2.3.0"},
                         {"uuid": UUID["rp"], "version": VERSION}],
        "metadata": {"authors": ["Five Final Bosses team"], "product_type": "addon"},
    })
    wj(os.path.join(RP, "manifest.json"), {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["rp"], "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
        "dependencies": [{"uuid": UUID["bp"], "version": VERSION}],
        "metadata": {"authors": ["Five Final Bosses team"], "product_type": "addon"},
    })
    icon = art.boss_pack_icon()
    save(icon, os.path.join(BP, "pack_icon.png"))
    save(icon, os.path.join(RP, "pack_icon.png"))


QA = {}


def build_models():
    for key, fn in registry.MODELS.items():
        m = fn()
        remaining = deflicker(m)
        img = m.paint()
        QA[key] = {"stats": m.stats(), "zfight": zfight_report(m), "islands": island_report(m), "deflicker_left": remaining}
        bw, bh, oy = BOSSES[key][7]
        wj(os.path.join(RP, "models", "entity", "fb", f"{key}.geo.json"), m.geometry_json(bw, bh, oy, glow=False))
        wj(os.path.join(RP, "models", "entity", "fb", f"{key}.glow.geo.json"), m.geometry_json(bw, bh, oy, glow=True, identifier=m.identifier + ".glow"))
        save(img, os.path.join(RP, "textures", "entity", "fb", f"{key}.png"))
    wj(os.path.join(BUILD, "model_qa.json"), QA)


def build_animations():
    for key, fn in anims.ALL.items():
        a = fn()
        out = {f"animation.fb.{key}.{st}": body for st, body in a.items()}
        wj(os.path.join(RP, "animations", f"fb_{key}.animation.json"), {"format_version": "1.8.0", "animations": out})
        prop = "query.property('fb:state')"
        states = {}
        avail = [st for st in STATES if st in a]
        for st in avail:
            idx = STATES.index(st)
            if st == "idle":
                states["default"] = {"animations": ["idle"], "blend_transition": 0.25,
                                     "transitions": [{o: f"{prop} == {STATES.index(o)}"} for o in avail if o != "idle"]}
            else:
                layers = [st] if st in ("dormant", "death", "burrow") else ["idle", st]
                states[st] = {"animations": layers, "blend_transition": 0.25, "transitions": [{"default": f"{prop} != {idx}"}]}
        wj(os.path.join(RP, "animation_controllers", f"fb_{key}.animation_controllers.json"),
           {"format_version": "1.10.0", "animation_controllers": {f"controller.animation.fb.{key}": {"initial_state": "default", "states": states}}})


def build_render_controllers():
    wj(os.path.join(RP, "render_controllers", "fb.render_controllers.json"), {"format_version": "1.8.0", "render_controllers": {
        "controller.render.fb.solid": {"geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"]},
        "controller.render.fb.glow": {"geometry": "Geometry.glow", "materials": [{"*": "Material.glow"}], "textures": ["Texture.default"]},
        "controller.render.fb.ghost": {"geometry": "Geometry.default", "materials": [{"*": "Material.glow"}], "textures": ["Texture.default"]},
    }})


def client_entity(ident, model, animations, animate, scale, egg=None, ghost=False):
    d = {
        "identifier": ident,
        "materials": {"default": "entity_alphatest", "glow": "entity_beam_additive"},
        "textures": {"default": f"textures/entity/fb/{model}"},
        "geometry": {"default": f"geometry.fb.{model}", "glow": f"geometry.fb.{model}.glow"},
        "animations": animations,
        "scripts": {
            "pre_animation": [
                "variable.spd = query.has_property('fb:phase') ? 1.0 + (query.property('fb:phase') - 1.0) * 0.4 : 1.0;",
                "variable.t = (variable.t ?? 0.0) + query.delta_time * variable.spd;",
            ],
            "animate": animate,
            "scale": str(scale),
        },
        "render_controllers": ["controller.render.fb.ghost", "controller.render.fb.glow"] if ghost else ["controller.render.fb.solid", "controller.render.fb.glow"],
    }
    if egg:
        d["spawn_egg"] = {"base_color": egg[0], "overlay_color": egg[1]}
    return {"format_version": "1.10.0", "minecraft:client_entity": {"description": d}}


def build_client_entities():
    for key, (_, _, _, _, scale, eb, eo, _) in BOSSES.items():
        a = anims.ALL[key]()
        an = {st: f"animation.fb.{key}.{st}" for st in a}
        an["controller"] = f"controller.animation.fb.{key}"
        wj(os.path.join(RP, "entity", "fb", f"{key}.entity.json"), client_entity(f"fb:{key}", key, an, ["controller"], scale, (eb, eo)))
    wj(os.path.join(RP, "entity", "fb", "choir_echo.entity.json"),
       client_entity("fb:choir_echo", "choir", {"idle": "animation.fb.choir.idle"}, ["idle"], 0.6, ghost=True))


# --------------------------------------------------------------------------- particles

def pe(ident, tex, comps, material="particles_add"):
    return {"format_version": "1.10.0", "particle_effect": {
        "description": {"identifier": ident, "basic_render_parameters": {"material": material, "texture": tex}}, "components": comps}}


def bb(size, uv=(0, 0, 16, 16), tex=(16, 16), facing="rotate_xyz"):
    return {"size": [size, size], "facing_camera_mode": facing,
            "uv": {"texture_width": tex[0], "texture_height": tex[1], "uv": list(uv[:2]), "uv_size": list(uv[2:])}}


def tint(rgb, alpha="1.0 - variable.particle_age / variable.particle_lifetime * 0.6"):
    return {"color": [rgb[0], rgb[1], rgb[2], alpha]}


SPARK = "textures/particle/fb_spark"
SHRINK = "(1.0 - variable.particle_age / variable.particle_lifetime * 0.7)"
ONCE = {"minecraft:emitter_lifetime_once": {"active_time": 0.05}}


def build_particles():
    P = os.path.join(RP, "particles", "fb")
    for hue, rgb in HUES.items():
        defs = {
            f"fb:mote_{hue}": ({"minecraft:emitter_rate_instant": {"num_particles": 1}, **ONCE,
                                "minecraft:emitter_shape_point": {"direction": ["math.random(-1, 1)", "math.random(-1, 1)", "math.random(-1, 1)"]},
                                "minecraft:particle_initial_speed": 0.08,
                                "minecraft:particle_lifetime_expression": {"max_lifetime": "0.45 + variable.particle_random_1 * 0.4"},
                                "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 1.0},
                                "minecraft:particle_appearance_billboard": bb(f"0.14 * {SHRINK}"),
                                "minecraft:particle_appearance_tinting": tint(rgb)}, SPARK),
            f"fb:burst_{hue}": ({"minecraft:emitter_rate_instant": {"num_particles": 26}, **ONCE,
                                 "minecraft:emitter_shape_sphere": {"radius": 0.3, "direction": "outwards"},
                                 "minecraft:particle_initial_speed": "3.0 + variable.particle_random_2 * 3.0",
                                 "minecraft:particle_lifetime_expression": {"max_lifetime": "0.55 + variable.particle_random_1 * 0.5"},
                                 "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 3.5},
                                 "minecraft:particle_appearance_billboard": bb(f"0.18 * {SHRINK}"),
                                 "minecraft:particle_appearance_tinting": tint(rgb)}, SPARK),
            f"fb:sphere_{hue}": ({"minecraft:emitter_rate_instant": {"num_particles": 140}, **ONCE,
                                  "minecraft:emitter_shape_sphere": {"radius": 0.6, "surface_only": True, "direction": "outwards"},
                                  "minecraft:particle_initial_speed": 15,
                                  "minecraft:particle_lifetime_expression": {"max_lifetime": "0.75 + variable.particle_random_1 * 0.2"},
                                  "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 2.4},
                                  "minecraft:particle_appearance_billboard": bb(f"0.32 * {SHRINK}"),
                                  "minecraft:particle_appearance_tinting": tint(rgb)}, SPARK),
            f"fb:wave_{hue}": ({"minecraft:emitter_rate_instant": {"num_particles": 110}, **ONCE,
                                "minecraft:emitter_shape_disc": {"radius": 1.0, "surface_only": True, "plane_normal": "y", "direction": "outwards"},
                                "minecraft:particle_initial_speed": 17,
                                "minecraft:particle_lifetime_expression": {"max_lifetime": 0.8},
                                "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 2.2},
                                "minecraft:particle_appearance_billboard": bb(f"0.3 * {SHRINK}"),
                                "minecraft:particle_appearance_tinting": tint(rgb)}, SPARK),
            f"fb:column_{hue}": ({"minecraft:emitter_rate_steady": {"spawn_rate": 90, "max_particles": 80},
                                  "minecraft:emitter_lifetime_once": {"active_time": 0.6},
                                  "minecraft:emitter_shape_box": {"half_dimensions": [0.35, 0.1, 0.35], "direction": [0, 1, 0]},
                                  "minecraft:particle_initial_speed": "12 + variable.particle_random_2 * 6",
                                  "minecraft:particle_lifetime_expression": {"max_lifetime": 0.75},
                                  "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 1.2},
                                  "minecraft:particle_appearance_billboard": bb(f"0.28 * {SHRINK}"),
                                  "minecraft:particle_appearance_tinting": tint(rgb)}, SPARK),
            f"fb:ring_{hue}": ({"minecraft:emitter_rate_instant": {"num_particles": 1}, **ONCE, "minecraft:emitter_shape_point": {},
                                "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life ?? 0.8"},
                                "minecraft:particle_appearance_billboard": bb("(variable.radius ?? 6.0) * variable.particle_age / variable.particle_lifetime + 0.2",
                                                                              (0, 0, 64, 64), (64, 64), "emitter_transform_xz"),
                                "minecraft:particle_appearance_tinting": tint(rgb, "1.0 - variable.particle_age / variable.particle_lifetime")},
                               "textures/particle/fb_ring"),
        }
        for ident, (comps, tex) in defs.items():
            wj(os.path.join(P, ident.split(":")[1] + ".json"), pe(ident, tex, comps))
    for tone, rgb in TONES.items():
        ident = f"fb:smoke_{tone}"
        wj(os.path.join(P, f"smoke_{tone}.json"), pe(ident, "textures/particle/fb_smoke", {
            "minecraft:emitter_rate_instant": {"num_particles": 3}, **ONCE,
            "minecraft:emitter_shape_sphere": {"radius": 0.5, "direction": [0, 1, 0]},
            "minecraft:particle_initial_speed": 0.4,
            "minecraft:particle_lifetime_expression": {"max_lifetime": "1.4 + variable.particle_random_1 * 0.8"},
            "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.3, 0], "linear_drag_coefficient": 0.8},
            "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_2 * 360", "rotation_rate": 20},
            "minecraft:particle_appearance_billboard": bb("0.5 + variable.particle_age * 0.6", (0, 0, 32, 32), (32, 32)),
            "minecraft:particle_appearance_tinting": {"color": [rgb[0], rgb[1], rgb[2], "0.85 * (1.0 - variable.particle_age / variable.particle_lifetime)"]},
        }, "particles_blend"))
    specials = {
        "fb:debris": ("textures/particle/fb_debris", "particles_alpha", {
            "minecraft:emitter_rate_instant": {"num_particles": 18}, **ONCE,
            "minecraft:emitter_shape_sphere": {"radius": 0.6, "direction": ["math.random(-1, 1)", "math.random(0.6, 1.6)", "math.random(-1, 1)"]},
            "minecraft:particle_initial_speed": "4 + variable.particle_random_2 * 4",
            "minecraft:particle_lifetime_expression": {"max_lifetime": "1.0 + variable.particle_random_1 * 0.6"},
            "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -18, 0], "linear_drag_coefficient": 0.6},
            "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_3 * 360", "rotation_rate": 200},
            "minecraft:particle_motion_collision": {"coefficient_of_restitution": 0.3, "collision_drag": 4, "collision_radius": 0.1},
            "minecraft:particle_appearance_billboard": bb("0.12 + variable.particle_random_4 * 0.12"),
            "minecraft:particle_appearance_tinting": {"color": [0.55, 0.47, 0.38, 1.0]}}),
        "fb:shards": ("textures/particle/fb_shard", "particles_add", {
            "minecraft:emitter_rate_instant": {"num_particles": 14}, **ONCE,
            "minecraft:emitter_shape_sphere": {"radius": 0.6, "direction": "outwards"},
            "minecraft:particle_initial_speed": "2 + variable.particle_random_2 * 3",
            "minecraft:particle_lifetime_expression": {"max_lifetime": "0.8 + variable.particle_random_1 * 0.5"},
            "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -6, 0], "linear_drag_coefficient": 1.0},
            "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_3 * 360", "rotation_rate": 360},
            "minecraft:particle_appearance_billboard": bb(f"0.16 * {SHRINK}"),
            "minecraft:particle_appearance_tinting": {"color": [0.85, 0.93, 1.0, "1.0 - variable.particle_age / variable.particle_lifetime * 0.5"]}}),
        "fb:embers": (SPARK, "particles_add", {
            "minecraft:emitter_rate_instant": {"num_particles": 10}, **ONCE,
            "minecraft:emitter_shape_sphere": {"radius": 0.8, "direction": [0, 1, 0]},
            "minecraft:particle_initial_speed": "0.8 + variable.particle_random_2 * 1.5",
            "minecraft:particle_lifetime_expression": {"max_lifetime": "1.0 + variable.particle_random_1 * 0.8"},
            "minecraft:particle_motion_dynamic": {"linear_acceleration": ["math.random(-0.5, 0.5)", 1.2, "math.random(-0.5, 0.5)"], "linear_drag_coefficient": 0.6},
            "minecraft:particle_appearance_billboard": bb(f"0.1 * {SHRINK}"),
            "minecraft:particle_appearance_tinting": {"color": [1.0, "0.45 + variable.particle_random_3 * 0.35", 0.1, "1.0 - variable.particle_age / variable.particle_lifetime"]}}),
        "fb:danger": ("textures/particle/fb_danger", "particles_add", {
            "minecraft:emitter_rate_instant": {"num_particles": 1}, **ONCE, "minecraft:emitter_shape_point": {},
            "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life ?? 1.2"},
            "minecraft:particle_appearance_billboard": bb("(variable.size ?? 4.0) * 0.5", (0, 0, 64, 64), (64, 64), "emitter_transform_xz"),
            "minecraft:particle_appearance_tinting": {"color": [1, 1, 1, "0.55 + 0.45 * math.sin(variable.particle_age * 1400)"]}}),
        "fb:safe": ("textures/particle/fb_safe", "particles_add", {
            "minecraft:emitter_rate_instant": {"num_particles": 1}, **ONCE, "minecraft:emitter_shape_point": {},
            "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life ?? 1.0"},
            "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 30},
            "minecraft:particle_appearance_billboard": bb("(variable.size ?? 4.0) * 0.5", (0, 0, 64, 64), (64, 64), "emitter_transform_xz"),
            "minecraft:particle_appearance_tinting": {"color": [1, 1, 1, 1]}}),
        "fb:sigil": ("textures/particle/fb_sigil", "particles_add", {
            "minecraft:emitter_rate_instant": {"num_particles": 1}, **ONCE, "minecraft:emitter_shape_point": {},
            "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life ?? 2.0"},
            "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 40},
            "minecraft:particle_appearance_billboard": bb("(variable.size ?? 4.0) * 0.5 * math.min(1.0, variable.particle_age * 4.0)", (0, 0, 128, 128), (128, 128), "emitter_transform_xz"),
            "minecraft:particle_appearance_tinting": {"color": [1, 1, 1, "math.min(1.0, (variable.particle_lifetime - variable.particle_age) * 3.0)"]}}),
        "fb:flash": ("textures/particle/fb_flash", "particles_add", {
            "minecraft:emitter_rate_instant": {"num_particles": 1}, **ONCE, "minecraft:emitter_shape_point": {},
            "minecraft:particle_lifetime_expression": {"max_lifetime": 0.45},
            "minecraft:particle_appearance_billboard": bb("2.0 + variable.particle_age * 22.0", (0, 0, 32, 32), (32, 32)),
            "minecraft:particle_appearance_tinting": {"color": [1, 1, 1, "1.0 - variable.particle_age / variable.particle_lifetime"]}}),
        "fb:blackhole": ("textures/particle/fb_smoke", "particles_blend", {
            "minecraft:emitter_rate_steady": {"spawn_rate": 60, "max_particles": 120},
            "minecraft:emitter_lifetime_expression": {"activation_expression": 1, "expiration_expression": "variable.emitter_age > (variable.life ?? 2.0)"},
            "minecraft:emitter_shape_sphere": {"radius": "variable.size ?? 3.0", "surface_only": True, "direction": "inwards"},
            "minecraft:particle_initial_speed": "(variable.size ?? 3.0) * 1.2",
            "minecraft:particle_lifetime_expression": {"max_lifetime": 0.8},
            "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 0.5},
            "minecraft:particle_appearance_billboard": bb(f"0.35 * {SHRINK}", (0, 0, 32, 32), (32, 32)),
            "minecraft:particle_appearance_tinting": {"color": [0.05, 0.0, 0.08, 0.9]}}),
    }
    for ident, (tex, mat, comps) in specials.items():
        wj(os.path.join(P, ident.split(":")[1] + ".json"), pe(ident, tex, comps, mat))
    T = os.path.join(RP, "textures", "particle")
    save(art.spark(), os.path.join(T, "fb_spark.png"))
    save(art.soft_ring(), os.path.join(T, "fb_ring.png"))
    save(art.sigil(), os.path.join(T, "fb_sigil.png"))
    save(art.danger(), os.path.join(T, "fb_danger.png"))
    save(art.safe_circle(), os.path.join(T, "fb_safe.png"))
    save(art.flash_sprite(), os.path.join(T, "fb_flash.png"))
    save(art.smoke_sprite(), os.path.join(T, "fb_smoke.png"))
    save(art.debris_sprite(), os.path.join(T, "fb_debris.png"))
    save(art.shard_sprite(), os.path.join(T, "fb_shard.png"))


# --------------------------------------------------------------------------- behaviour entities

def boss_entity(key):
    name, hp, w, h, *_ = BOSSES[key]
    comps = {
        "minecraft:type_family": {"family": ["fb_boss", "boss", "monster", "mob"]},
        "minecraft:health": {"value": hp, "max": hp},
        "minecraft:collision_box": {"width": w, "height": h},
        "minecraft:physics": {"has_gravity": False, "has_collision": False},
        "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
        "minecraft:knockback_resistance": {"value": 1.0},
        "minecraft:fire_immune": {},
        "minecraft:persistent": {},
        "minecraft:nameable": {"always_show": False, "allow_name_tag_renaming": False},
        "minecraft:damage_sensor": {"triggers": [{"cause": c, "deals_damage": "no"} for c in
                                                 ("fall", "fire", "fire_tick", "lava", "drowning", "suffocation", "lightning", "magma",
                                                  "freezing", "wither", "contact", "fly_into_wall", "falling_block")]},
        "minecraft:experience_reward": {"on_death": "300"},
        "minecraft:conditional_bandwidth_optimization": {},
    }
    groups, events = {}, {}
    boss_bar = {"minecraft:boss": {"should_darken_sky": True, "hud_range": 72}}
    if key == "world_parasite":
        groups["fb:awake"] = boss_bar           # no boss bar while it pretends to be a hill
        events["fb:awaken"] = {"add": {"component_groups": ["fb:awake"]}}
    else:
        comps.update(boss_bar)
    return {"format_version": "1.21.0", "minecraft:entity": {
        "description": {"identifier": f"fb:{key}", "is_spawnable": True, "is_summonable": True, "properties": {
            "fb:state": {"type": "int", "range": [0, 12], "default": 10 if key == "world_parasite" else 9, "client_sync": True},
            "fb:phase": {"type": "int", "range": [1, 3], "default": 1, "client_sync": True}}},
        **({"component_groups": groups} if groups else {}), "components": comps, **({"events": events} if events else {})}}


def build_bp_entities():
    for key in BOSSES:
        wj(os.path.join(BP, "entities", "fb", f"{key}.json"), boss_entity(key))
    wj(os.path.join(BP, "entities", "fb", "choir_echo.json"), {"format_version": "1.21.0", "minecraft:entity": {
        "description": {"identifier": "fb:choir_echo", "is_spawnable": False, "is_summonable": True},
        "components": {
            "minecraft:type_family": {"family": ["fb_illusion", "mob"]},
            "minecraft:health": {"value": 100, "max": 100},
            "minecraft:collision_box": {"width": 1.2, "height": 2.6},
            "minecraft:physics": {"has_gravity": False, "has_collision": False},
            "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
            "minecraft:knockback_resistance": {"value": 1.0},
            "minecraft:fire_immune": {},
            "minecraft:timer": {"looping": False, "time": 15, "randomInterval": False, "time_down_event": {"event": "fb:despawn", "target": "self"}},
            "minecraft:conditional_bandwidth_optimization": {},
        },
        "component_groups": {"fb:despawn": {"minecraft:instant_despawn": {}}},
        "events": {"fb:despawn": {"add": {"component_groups": ["fb:despawn"]}}}}})


def build_items():
    tex = {}
    for key, name in ITEMS.items():
        save(art.icon(key), os.path.join(RP, "textures", "items", "fb", f"{key}.png"))
        tex[f"fb_{key}"] = {"textures": f"textures/items/fb/{key}"}
        comps = {"minecraft:icon": {"textures": {"default": f"fb_{key}"}}, "minecraft:display_name": {"value": f"item.fb:{key}.name"},
                 "minecraft:max_stack_size": 1, "minecraft:glint": True, "minecraft:hand_equipped": key != "boss_sigil"}
        if key in COOLDOWNS:
            comps["minecraft:cooldown"] = {"category": COOLDOWNS[key][0], "duration": COOLDOWNS[key][1]}
        wj(os.path.join(BP, "items", "fb", f"{key}.json"), {"format_version": "1.21.60", "minecraft:item": {
            "description": {"identifier": f"fb:{key}", "menu_category": {"category": "equipment"}}, "components": comps}})
    wj(os.path.join(RP, "textures", "item_texture.json"), {"resource_pack_name": "fb", "texture_name": "atlas.items", "texture_data": tex})
    wj(os.path.join(BP, "recipes", "boss_sigil.json"), {"format_version": "1.20.10", "minecraft:recipe_shaped": {
        "description": {"identifier": "fb:boss_sigil"}, "tags": ["crafting_table"],
        "pattern": ["GEG", "DND", "GEG"],
        "key": {"G": {"item": "minecraft:gold_block"}, "E": {"item": "minecraft:ender_eye"}, "D": {"item": "minecraft:diamond"},
                "N": {"item": "minecraft:echo_shard"}},
        "unlock": [{"item": "minecraft:echo_shard"}], "result": {"item": "fb:boss_sigil"}}})


def build_lang():
    en = [f"pack.name={NAME}", "pack.description=Five final bosses with unique models, mechanics and ultimates."]
    for k, n in ITEMS.items():
        en.append(f"item.fb:{k}.name={n}")
    for k, (n, *_r) in BOSSES.items():
        en += [f"entity.fb:{k}.name={n}", f"item.spawn_egg.entity.fb:{k}.name=Spawn {n}"]
    en.append("entity.fb:choir_echo.name=Mirror Image")
    for root in (BP, RP):
        wt(os.path.join(root, "texts", "en_US.lang"), "\n".join(en if root == RP else en[:2]) + "\n")
        wt(os.path.join(root, "texts", "languages.json"), json.dumps(["en_US"], indent=2) + "\n")


def build_scripts():
    tsc = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    r = subprocess.run([tsc, "-p", os.path.join(ROOT, "tsconfig.json"), "--outDir", os.path.join(BP, "scripts")], capture_output=True, text=True)
    if r.returncode:
        print(r.stdout, r.stderr)
        raise SystemExit("TypeScript compilation failed")


def zip_dir(zf, folder, arc):
    for dp, _, files in os.walk(folder):
        for fn in sorted(files):
            full = os.path.join(dp, fn)
            zf.write(full, os.path.join(arc, os.path.relpath(full, folder)))


def package():
    os.makedirs(DIST, exist_ok=True)
    base = "Five_Final_Bosses"
    with zipfile.ZipFile(os.path.join(DIST, f"{base}.mcaddon"), "w", zipfile.ZIP_DEFLATED) as zf:
        zip_dir(zf, BP, "FinalBosses_BP")
        zip_dir(zf, RP, "FinalBosses_RP")
    for folder, sfx in ((BP, "BP"), (RP, "RP")):
        with zipfile.ZipFile(os.path.join(DIST, f"{base}_{sfx}.mcpack"), "w", zipfile.ZIP_DEFLATED) as zf:
            zip_dir(zf, folder, "")
    return os.path.join(DIST, f"{base}.mcaddon")


def main():
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    manifests()
    build_models()
    build_animations()
    build_render_controllers()
    build_client_entities()
    build_particles()
    build_bp_entities()
    build_items()
    build_lang()
    build_scripts()
    print("built", os.path.relpath(package(), ROOT))
    for k, q in QA.items():
        print(f"  {k}: {q['stats']['cubes']} cubes, {q['stats']['bones']} bones, zfight={len(q['zfight'])}, islands={len(q['islands'])}")


if __name__ == "__main__":
    main()
