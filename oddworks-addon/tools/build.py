"""
Build script for ODDWORKS - Fantasy Equipment, Set 01.

    python3 tools/build.py            -> build/ODDWORKS_BP + build/ODDWORKS_RP + dist/*.mcaddon

Generates every pack file (models, textures, icons, attachables, animations, controllers,
entities, items, recipes, particles, synthesized sounds, language files, manifests),
compiles the TypeScript gameplay scripts and packages the add-on.
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
import sfx  # noqa: E402

BUILD = os.path.join(ROOT, "build")
BP = os.path.join(BUILD, "ODDWORKS_BP")
RP = os.path.join(BUILD, "ODDWORKS_RP")
DIST = os.path.join(ROOT, "dist")
BASENAME = "ODDWORKS_Set01"

VERSION = [1, 0, 0]
MIN_ENGINE = [1, 26, 60]
SERVER_VERSION = "2.11.0"
ITEM_FORMAT = "1.21.130"
UUID = {
    "bp_header": "4a6f2d1e-93c7-4b8a-a2f1-0dd1e5a01001",
    "bp_data": "4a6f2d1e-93c7-4b8a-a2f1-0dd1e5a01002",
    "bp_script": "4a6f2d1e-93c7-4b8a-a2f1-0dd1e5a01003",
    "rp_header": "b81c3e70-5d24-4f61-9c0e-7aa8f2c02001",
    "rp_res": "b81c3e70-5d24-4f61-9c0e-7aa8f2c02002",
}

NS = "oddworks"
SIGNALS = {
    "goggles_full": "oddworks:sig_goggles_full",
    "cane_draw": "oddworks:sig_cane_draw",
    "cane_noto": "oddworks:sig_cane_noto",
    "cane_deflect": "oddworks:sig_cane_deflect",
}

ITEM_NAMES = {
    "solar_frost_goggles": "Solar Frost Goggles",
    "endless_handline": "Endless Handline",
    "endless_handline_cast": "Endless Handline (Line Out)",
    "bamboo_sword_cane": "Bamboo Sword Cane",
    "bamboo_sword_cane_drawn": "Bamboo Sword Cane (Drawn)",
}
ENTITY_NAMES = {
    "handline_hook": "Handline Hook",
    "handline_bobber": "Handline Float",
    "sun_dog": "Sun Dog",
    "ice_shell": "Ice Shell",
}


# =========================================================================== io helpers

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# =========================================================================== manifests

def manifests(pack_icon):
    meta = {"authors": ["ODDWORKS"], "product_type": "addon"}
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
        "metadata": meta,
    }
    rp = {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["rp_header"],
                   "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
        "dependencies": [{"uuid": UUID["bp_header"], "version": VERSION}],
        "metadata": meta,
    }
    write_json(os.path.join(BP, "manifest.json"), bp)
    write_json(os.path.join(RP, "manifest.json"), rp)
    for p in (BP, RP):
        pack_icon.save(os.path.join(p, "pack_icon.png"))


# =========================================================================== geometry + textures

def build_models():
    built = {}
    for name, fn in list(models.ALL_ITEM_MODELS.items()) + list(models.ALL_ENTITY_MODELS.items()):
        m = fn()
        img = m.paint()
        write_json(os.path.join(RP, "models", "entity", NS, f"{name}.geo.json"), m.geometry_json())
        tex = os.path.join(RP, "textures", "entity", NS, f"{name}.png")
        os.makedirs(os.path.dirname(tex), exist_ok=True)
        img.save(tex)
        built[name] = m
    return built


def build_icons():
    data = {}
    for name, fn in icons.ICONS.items():
        p = os.path.join(RP, "textures", "items", NS, f"{name}.png")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        fn().save(p)
        data[f"{NS}_{name}"] = {"textures": f"textures/items/{NS}/{name}"}
    write_json(os.path.join(RP, "textures", "item_texture.json"),
               {"resource_pack_name": NS, "texture_name": "atlas.items", "texture_data": data})
    for s in icons.SPRITES:
        p = os.path.join(RP, "textures", "particle", NS, f"{s}.png")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        icons.sprite(s).save(p)


def build_particles():
    ids = []
    for ident, data in particles.all_effects().items():
        write_json(os.path.join(RP, "particles", NS, ident.split(":")[1] + ".json"), data)
        ids.append(ident)
    return ids


def build_sounds():
    defs = sfx.render_all(RP)
    write_json(os.path.join(RP, "sounds", "sound_definitions.json"),
               {"format_version": "1.20.20", "sound_definitions": defs})
    return defs


# =========================================================================== attachables

def _anim_file(name, animations):
    write_json(os.path.join(RP, "animations", f"{NS}_{name}.animation.json"),
               {"format_version": "1.10.0", "animations": animations})


def _ctrl_file(name, controllers):
    write_json(os.path.join(RP, "animation_controllers", f"{NS}_{name}.animation_controllers.json"),
               {"format_version": "1.10.0", "animation_controllers": controllers})


def _state(anims_, transitions, blend=0.12):
    return {"animations": anims_, "transitions": [{k: v} for k, v in transitions], "blend_transition": blend}


def _attachable(item, geometry, texture, animations, pre, animate, render_controller, materials=None,
                extra_textures=None):
    mats = materials or {"default": "entity_emissive_alpha", "enchanted": "entity_alphatest_glint"}
    tex = {"default": f"textures/entity/{NS}/{texture}", "enchanted": "textures/misc/enchanted_item_glint"}
    tex.update(extra_textures or {})
    return {
        "format_version": "1.10.0",
        "minecraft:attachable": {
            "description": {
                "identifier": f"{NS}:{item}",
                "materials": mats,
                "textures": tex,
                "geometry": {"default": geometry},
                "animations": animations,
                "scripts": {"pre_animation": pre, "animate": animate},
                "render_controllers": [render_controller],
            }
        },
    }


USING = "v.using = q.main_hand_item_use_duration > 0.0;"


def sig(key):
    return f"q.cooldown_time_remaining('{SIGNALS[key]}')"


def build_attachables():
    A = anims
    # ------------------------------------------------------------------ goggles
    gp = A.goggles_poses()
    ganims = {f"animation.{NS}.goggles.{k}": A.static_anim(v) for k, v in gp.items()}
    pulse = "math.sin(q.life_time * 900.0) * 0.12"
    ganims[f"animation.{NS}.goggles.glow"] = {"loop": True, "bones": {
        "tp_glow": {"scale": f"(v.using && !v.full) ? (1.0 + {pulse}) : 0.0"},
        "tp_glow_full": {"scale": f"(v.using && v.full) ? (1.15 + {pulse}) : 0.0"},
        "fp_glow": {"scale": 0.0},
        "fp_glow_full": {"scale": 0.0},
        "fp_mask_rim": {"scale": [1.0, f"v.full ? 1.35 : (1.0 + {pulse} * 0.5)", 1.0]},
    }}
    _anim_file("goggles", ganims)
    tr_tp = [("tp_down", "!c.is_first_person && v.using"), ("tp_up", "!c.is_first_person && !v.using"),
             ("fp_raised", "c.is_first_person && v.using"), ("fp_held", "c.is_first_person && !v.using")]

    def without(name):
        return [t for t in tr_tp if t[0] != name]
    _ctrl_file("goggles", {f"controller.animation.{NS}.goggles": {
        "initial_state": "tp_up",
        "states": {name: _state([name], without(name), 0.14) for name in ("tp_up", "tp_down", "fp_held", "fp_raised")},
    }})
    write_json(os.path.join(RP, "attachables", "solar_frost_goggles.json"), _attachable(
        "solar_frost_goggles", "geometry.oddworks.solar_frost_goggles", "solar_frost_goggles",
        {"ctrl": f"controller.animation.{NS}.goggles", "glow": f"animation.{NS}.goggles.glow",
         **{k: f"animation.{NS}.goggles.{k}" for k in gp}},
        [USING, f"v.full = {sig('goggles_full')} > 0.0;"], ["ctrl", "glow"],
        f"controller.render.{NS}.goggles",
        materials={"default": "entity_emissive_alpha", "mask": "entity_alphablend"}))

    # ------------------------------------------------------------------ handline (ready + line out)
    hp = A.handline_poses()
    hanims = {f"animation.{NS}.handline.{k}": A.static_anim(v) for k, v in hp.items()}
    hanims[f"animation.{NS}.handline.whirl_spin"] = {"loop": True, "bones": {
        "whirl": {"rotation": [0, "q.life_time * 820.0", 0]}}}
    hanims[f"animation.{NS}.handline.reel_spin"] = {"loop": True, "bones": {
        "drum": {"rotation": [0, "-q.life_time * 1150.0", 0]},
        "reel": {"position": [0, "math.sin(q.life_time * 1400.0) * 0.25", 0]}}}
    hanims[f"animation.{NS}.handline.sway"] = {"loop": True, "bones": {
        "sinker_rig": {"rotation": ["math.sin(q.life_time * 160.0) * 6.0", 0, "math.cos(q.life_time * 120.0) * 5.0"]}}}
    _anim_file("handline", hanims)

    def hl_ctrl(active_tp, active_fp, extra_active):
        states = {
            "tp_idle": _state(["tp_idle"] + (["sway"] if extra_active == "whirl_spin" else []),
                              [(active_tp, "!c.is_first_person && v.using"), ("fp_idle", "c.is_first_person")]),
            active_tp: _state([active_tp, extra_active],
                              [("tp_idle", "!c.is_first_person && !v.using"), (active_fp, "c.is_first_person")]),
            "fp_idle": _state(["fp_idle"] + (["sway"] if extra_active == "whirl_spin" else []),
                              [(active_fp, "c.is_first_person && v.using"), ("tp_idle", "!c.is_first_person")]),
            active_fp: _state([active_fp, extra_active],
                              [("fp_idle", "c.is_first_person && !v.using"), (active_tp, "!c.is_first_person")]),
        }
        return {"initial_state": "tp_idle", "states": states}
    _ctrl_file("handline", {
        f"controller.animation.{NS}.handline": hl_ctrl("tp_whirl", "fp_whirl", "whirl_spin"),
        f"controller.animation.{NS}.handline_cast": hl_ctrl("tp_reel", "fp_reel", "reel_spin"),
    })
    names = {k: f"animation.{NS}.handline.{k}" for k in list(hp) + ["whirl_spin", "reel_spin", "sway"]}
    write_json(os.path.join(RP, "attachables", "endless_handline.json"), _attachable(
        "endless_handline", "geometry.oddworks.endless_handline", "endless_handline",
        {"ctrl": f"controller.animation.{NS}.handline", **names}, [USING], ["ctrl"],
        "controller.render.item_default"))
    write_json(os.path.join(RP, "attachables", "endless_handline_cast.json"), _attachable(
        "endless_handline_cast", "geometry.oddworks.endless_handline_cast", "endless_handline_cast",
        {"ctrl": f"controller.animation.{NS}.handline_cast", **names}, [USING], ["ctrl"],
        "controller.render.item_default"))

    # ------------------------------------------------------------------ bamboo sword cane
    cp = A.cane_poses()
    canims = {f"animation.{NS}.cane.{k}": A.static_anim(v) for k, v in cp.items()}
    HIDE0 = {"scale": 0}
    canims[f"animation.{NS}.cane.fp_draw"] = A.keyframed([
        (0.0, {"cane": cp["fp_grip"]["cane"], "sheath": {"position": [0, 0, 0], "scale": 1}}),
        (0.06, {"sheath": {"position": [0, -5, 0], "scale": 1}}),
        (0.1, {"cane": cp["fp_grip"]["cane"], "sheath": {"position": [0, -13, 0], "scale": 1}}),
        (0.11, {"sheath": {"position": [0, -13, 0], "scale": 0}}),
        (0.19, {"cane": cp["fp_cut_mid"]["cane"]}),
        (0.34, {"cane": cp["fp_drawn"]["cane"], "sheath": {"position": [0, -13, 0], "scale": 0}}),
    ], 0.34, bones_override={"hip_sheath": HIDE0})
    canims[f"animation.{NS}.cane.fp_noto"] = A.keyframed([
        (0.0, {"cane": cp["fp_drawn"]["cane"], "sheath": {"position": [0, -13, 0], "scale": 0}}),
        (0.1, {"cane": cp["fp_flick"]["cane"]}),
        (0.24, {"sheath": {"position": [0, -13, 0], "scale": 0}}),
        (0.25, {"cane": cp["fp_grip"]["cane"], "sheath": {"position": [0, -13, 0], "scale": 1}}),
        (0.42, {"sheath": {"position": [0, 0, 0], "scale": 1}}),
        (0.55, {"cane": cp["fp_grip"]["cane"], "sheath": {"position": [0, 0, 0], "scale": 1}}),
    ], 0.55, bones_override={"hip_sheath": HIDE0})
    _anim_file("cane", canims)
    sheathed = {
        "initial_state": "tp_cane",
        "states": {
            "tp_cane": _state(["tp_cane"], [("tp_grip", "!c.is_first_person && v.using"), ("fp_guard", "c.is_first_person")]),
            "tp_grip": _state(["tp_grip"], [("tp_cane", "!c.is_first_person && !v.using"), ("fp_grip", "c.is_first_person")]),
            "fp_guard": _state(["fp_guard"], [("fp_grip", "c.is_first_person && v.using"), ("tp_cane", "!c.is_first_person")]),
            "fp_grip": _state(["fp_grip"], [("fp_guard", "c.is_first_person && !v.using"), ("tp_grip", "!c.is_first_person")]),
        }}
    drawn = {
        "initial_state": "tp_drawn",
        "states": {
            "tp_drawn": _state(["tp_drawn"], [("tp_deflect", "!c.is_first_person && v.deflect"), ("fp_drawn", "c.is_first_person")]),
            "tp_deflect": _state(["tp_deflect"], [("tp_drawn", "!c.is_first_person && !v.deflect"), ("fp_drawn", "c.is_first_person")], 0.06),
            "fp_drawn": _state(["fp_drawn"], [("fp_draw", "c.is_first_person && v.draw"), ("fp_noto", "c.is_first_person && v.noto"),
                                              ("fp_deflect", "c.is_first_person && v.deflect"), ("tp_drawn", "!c.is_first_person")]),
            "fp_draw": _state(["fp_draw"], [("fp_drawn", "q.all_animations_finished || !c.is_first_person")], 0.0),
            "fp_noto": _state(["fp_noto"], [("fp_drawn", "(q.all_animations_finished && !v.noto) || !c.is_first_person")], 0.0),
            "fp_deflect": _state(["fp_deflect"], [("fp_drawn", "!v.deflect || !c.is_first_person")], 0.06),
        }}
    _ctrl_file("cane", {f"controller.animation.{NS}.cane": sheathed, f"controller.animation.{NS}.cane_drawn": drawn})
    cnames = {k: f"animation.{NS}.cane.{k}" for k in list(cp) + ["fp_draw", "fp_noto"]}
    cane_mats = {"default": "entity_alphatest", "enchanted": "entity_alphatest_glint"}
    write_json(os.path.join(RP, "attachables", "bamboo_sword_cane.json"), _attachable(
        "bamboo_sword_cane", "geometry.oddworks.bamboo_sword_cane", "bamboo_sword_cane",
        {"ctrl": f"controller.animation.{NS}.cane", **cnames}, [USING], ["ctrl"],
        "controller.render.item_default", materials=cane_mats))
    write_json(os.path.join(RP, "attachables", "bamboo_sword_cane_drawn.json"), _attachable(
        "bamboo_sword_cane_drawn", "geometry.oddworks.bamboo_sword_cane_drawn", "bamboo_sword_cane_drawn",
        {"ctrl": f"controller.animation.{NS}.cane_drawn", **cnames},
        [USING, f"v.draw = {sig('cane_draw')} > 0.0;", f"v.noto = {sig('cane_noto')} > 0.0;",
         f"v.deflect = {sig('cane_deflect')} > 0.0;"], ["ctrl"],
        "controller.render.item_default", materials=cane_mats))

    # ------------------------------------------------------------------ render controllers
    write_json(os.path.join(RP, "render_controllers", f"{NS}.render_controllers.json"), {
        "format_version": "1.10.0",
        "render_controllers": {
            f"controller.render.{NS}.goggles": {
                "geometry": "Geometry.default",
                "materials": [{"*": "Material.default"}, {"fp_mask": "Material.mask"}],
                "textures": ["Texture.default"],
            },
            f"controller.render.{NS}.entity": {
                "geometry": "Geometry.default",
                "materials": [{"*": "Material.default"}],
                "textures": ["Texture.default"],
            },
        }})
    # third-person player poses played from scripts (Entity.playAnimation)
    _anim_file("player", A.player_anims())


# =========================================================================== entities (client + server)

def build_client_entities():
    t = "q.life_time"
    ent_anims = {
        f"animation.{NS}.hook.spin": {"loop": True, "bones": {"body": {"rotation": [f"{t} * 360", 0, 0]}}},
        f"animation.{NS}.bobber.bob": {"loop": True, "bones": {"body": {
            "position": [0, f"math.sin({t} * 160) * 0.5", 0],
            "rotation": [f"math.sin({t} * 110) * 6", 0, f"math.cos({t} * 90) * 6"]}}},
        f"animation.{NS}.sun_dog.idle": {"loop": True, "bones": {
            "core": {"position": [0, f"math.sin({t} * 90) * 0.6", 0], "rotation": [0, f"{t} * 40", 0],
                     "scale": f"1 + math.sin({t} * 300) * 0.06"},
            "halo": {"rotation": [0, f"-{t} * 40", f"{t} * 25"]},
            "dogs": {"rotation": [0, f"-{t} * 40", 0], "scale": f"0.9 + math.sin({t} * 520) * 0.15"}}},
    }
    _anim_file("entities", ent_anims)

    def ce(ident, model, material, animations=None, animate=None):
        d = {
            "identifier": f"{NS}:{ident}",
            "materials": {"default": material},
            "textures": {"default": f"textures/entity/{NS}/{model}"},
            "geometry": {"default": f"geometry.{NS}.{model}"},
            "render_controllers": [f"controller.render.{NS}.entity"],
        }
        if animations:
            d["animations"] = animations
            d["scripts"] = {"animate": animate}
        return {"format_version": "1.10.0", "minecraft:client_entity": {"description": d}}
    write_json(os.path.join(RP, "entity", NS, "handline_hook.entity.json"),
               ce("handline_hook", "handline_hook", "entity_alphatest"))
    write_json(os.path.join(RP, "entity", NS, "handline_bobber.entity.json"),
               ce("handline_bobber", "handline_bobber", "entity_emissive_alpha",
                  {"bob": f"animation.{NS}.bobber.bob"}, ["bob"]))
    write_json(os.path.join(RP, "entity", NS, "sun_dog.entity.json"),
               ce("sun_dog", "sun_dog", "entity_emissive_alpha", {"idle": f"animation.{NS}.sun_dog.idle"}, ["idle"]))
    write_json(os.path.join(RP, "entity", NS, "ice_shell.entity.json"),
               ce("ice_shell", "ice_shell", "entity_alphablend"))


def _fx_entity(ident, families, components, groups=None, events=None, lifetime=None):
    comps = {
        "minecraft:type_family": {"family": families},
        "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
        "minecraft:conditional_bandwidth_optimization": {},
    }
    comps.update(components)
    groups = dict(groups or {})
    events = dict(events or {})
    groups[f"{NS}:despawn"] = {"minecraft:instant_despawn": {}}
    events[f"{NS}:despawn"] = {"add": {"component_groups": [f"{NS}:despawn"]}}
    if lifetime:
        comps["minecraft:timer"] = {"looping": False, "time": lifetime, "randomInterval": False,
                                    "time_down_event": {"event": f"{NS}:despawn", "target": "self"}}
    return {
        "format_version": "1.26.50",
        "minecraft:entity": {
            "description": {"identifier": f"{NS}:{ident}", "is_spawnable": False, "is_summonable": True},
            "component_groups": groups,
            "components": comps,
            "events": events,
        },
    }


INVULNERABLE = {"minecraft:health": {"value": 1, "max": 1},
                "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": "no"}]},
                "minecraft:fire_immune": {}}


def build_bp_entities():
    hook = _fx_entity("handline_hook", ["oddworks_line", "inanimate"], {
        "minecraft:collision_box": {"width": 0.25, "height": 0.25},
        "minecraft:projectile": {
            "on_hit": {"impact_damage": {"damage": {"min": 0, "max": 0}, "knockback": False, "destroy_on_hit": True,
                                         "destroy_on_hit_requires_damage": False},
                       "stick_in_ground": {"shake_time": 0.0}},
            "power": 1.6, "gravity": 0.045, "inertia": 0.985, "liquid_inertia": 0.55,
            "anchor": "eye_height", "offset": [0, -0.1, 0], "uncertainty_base": 0, "uncertainty_multiplier": 0,
            "hit_sound": "oddworks.line.hook_flesh", "hit_ground_sound": "oddworks.line.hook_block",
            "isolated_physics": False},
        "minecraft:physics": {},
        "minecraft:conditional_bandwidth_optimization": {
            "default_values": {"max_optimized_distance": 96.0, "max_dropped_ticks": 4, "use_motion_prediction_hints": True}},
    }, lifetime=600)
    write_json(os.path.join(BP, "entities", NS, "handline_hook.json"), hook)
    bobber = _fx_entity("handline_bobber", ["oddworks_line", "inanimate"], {
        "minecraft:collision_box": {"width": 0.3, "height": 0.3},
        "minecraft:physics": {},
        "minecraft:buoyant": {"base_buoyancy": 1.0, "apply_gravity": True, "simulate_waves": True,
                              "big_wave_probability": 0.03, "big_wave_speed": 10.0, "drag_down_on_buoyancy_removed": 0.0,
                              "liquid_blocks": ["minecraft:water", "minecraft:flowing_water"]},
        **INVULNERABLE,
    }, lifetime=600)
    write_json(os.path.join(BP, "entities", NS, "handline_bobber.json"), bobber)
    sun = _fx_entity("sun_dog", ["oddworks_fx", "inanimate"], {
        "minecraft:collision_box": {"width": 0.4, "height": 0.4},
        "minecraft:physics": {"has_gravity": False, "has_collision": False},
        **INVULNERABLE,
    }, lifetime=120)
    write_json(os.path.join(BP, "entities", NS, "sun_dog.json"), sun)
    sizes = {"s": 0.7, "m": 1.25, "l": 2.0, "xl": 3.2}
    groups = {f"{NS}:size_{k}": {"minecraft:scale": {"value": v}} for k, v in sizes.items()}
    events = {f"{NS}:size_{k}": {"add": {"component_groups": [f"{NS}:size_{k}"]}} for k in sizes}
    shell = _fx_entity("ice_shell", ["oddworks_fx", "inanimate"], {
        "minecraft:collision_box": {"width": 0.1, "height": 0.1},
        "minecraft:physics": {"has_gravity": False, "has_collision": False},
        **INVULNERABLE,
    }, groups, events, lifetime=20)
    write_json(os.path.join(BP, "entities", NS, "ice_shell.json"), shell)


# =========================================================================== items + recipes

def _item(key, components, category="equipment", hidden=False):
    desc = {"identifier": f"{NS}:{key}", "menu_category": {"category": "none" if hidden else category}}
    if hidden:
        desc["menu_category"]["is_hidden_in_commands"] = False
    base = {
        "minecraft:icon": f"{NS}_{key}",
        "minecraft:display_name": {"value": f"item.{NS}:{key}.name"},
        "minecraft:max_stack_size": 1,
        "minecraft:hand_equipped": True,
        "minecraft:allow_off_hand": False,
        "minecraft:tags": {"tags": [f"{NS}:equipment"]},
    }
    base.update(components)
    return {"format_version": ITEM_FORMAT, "minecraft:item": {"description": desc, "components": base}}


def build_items():
    goggles = _item("solar_frost_goggles", {
        "minecraft:durability": {"max_durability": 420, "damage_chance": {"min": 100, "max": 100}},
        "minecraft:repairable": {"repair_items": [
            {"items": ["minecraft:bone"], "repair_amount": "query.max_durability * 0.25"},
            {"items": ["minecraft:packed_ice"], "repair_amount": "query.max_durability * 0.1"}]},
        "minecraft:enchantable": {"slot": "bow", "value": 12},
        "minecraft:use_modifiers": {"use_duration": 3600, "movement_modifier": 0.55, "emit_vibrations": False},
        "minecraft:use_animation": "none",
        "minecraft:interact_button": "Absorb Sunlight",
        "minecraft:rarity": "rare",
        "minecraft:damage": 1,
    })
    handline = _item("endless_handline", {
        "minecraft:durability": {"max_durability": 384, "damage_chance": {"min": 100, "max": 100}},
        "minecraft:repairable": {"repair_items": [
            {"items": ["minecraft:string"], "repair_amount": "query.max_durability * 0.25"}]},
        "minecraft:enchantable": {"slot": "fishing_rod", "value": 12},
        "minecraft:use_modifiers": {"use_duration": 3600, "movement_modifier": 0.7, "emit_vibrations": False},
        "minecraft:use_animation": "spear",
        "minecraft:interact_button": "Whirl & Cast",
        "minecraft:rarity": "rare",
        "minecraft:damage": 1,
    })
    handline_cast = _item("endless_handline_cast", {
        "minecraft:durability": {"max_durability": 384, "damage_chance": {"min": 100, "max": 100}},
        "minecraft:enchantable": {"slot": "fishing_rod", "value": 12},
        "minecraft:use_modifiers": {"use_duration": 3600, "movement_modifier": 0.85, "emit_vibrations": False},
        "minecraft:use_animation": "brush",
        "minecraft:interact_button": "Reel In",
        "minecraft:rarity": "rare",
        "minecraft:damage": 1,
        "minecraft:should_despawn": True,
    }, hidden=True)
    cane = _item("bamboo_sword_cane", {
        "minecraft:durability": {"max_durability": 520, "damage_chance": {"min": 100, "max": 100}},
        "minecraft:repairable": {"repair_items": [
            {"items": ["minecraft:iron_ingot"], "repair_amount": "query.max_durability * 0.3"},
            {"items": ["minecraft:bamboo"], "repair_amount": "query.max_durability * 0.08"}]},
        "minecraft:enchantable": {"slot": "sword", "value": 14},
        "minecraft:use_modifiers": {"use_duration": 3600, "movement_modifier": 0.4, "emit_vibrations": False},
        "minecraft:use_animation": "none",
        "minecraft:interact_button": "Grip (Iai Draw)",
        "minecraft:damage": 2,
        "minecraft:rarity": "rare",
        "minecraft:swing_sounds": {"attack_hit": "oddworks.cane.tap", "attack_miss": "oddworks.cane.swish"},
    })
    cane_drawn = _item("bamboo_sword_cane_drawn", {
        "minecraft:durability": {"max_durability": 520, "damage_chance": {"min": 100, "max": 100}},
        "minecraft:repairable": {"repair_items": [
            {"items": ["minecraft:iron_ingot"], "repair_amount": "query.max_durability * 0.3"}]},
        "minecraft:enchantable": {"slot": "sword", "value": 14},
        "minecraft:use_modifiers": {"use_duration": 3600, "movement_modifier": 0.9, "emit_vibrations": False},
        "minecraft:use_animation": "none",
        "minecraft:interact_button": "Deflect",
        "minecraft:damage": 5,
        "minecraft:rarity": "rare",
        "minecraft:swing_duration": {"value": 0.2},
        "minecraft:swing_sounds": {"attack_hit": "oddworks.cane.cut", "attack_miss": "oddworks.cane.swish",
                                   "attack_critical_hit": "oddworks.cane.cut_crit"},
    }, hidden=True)
    for key, data in (("solar_frost_goggles", goggles), ("endless_handline", handline),
                      ("endless_handline_cast", handline_cast), ("bamboo_sword_cane", cane),
                      ("bamboo_sword_cane_drawn", cane_drawn)):
        write_json(os.path.join(BP, "items", NS, f"{key}.json"), data)

    def shaped(name, pattern, key, result):
        return {"format_version": "1.20.10", "minecraft:recipe_shaped": {
            "description": {"identifier": f"{NS}:{name}"}, "tags": ["crafting_table"],
            "pattern": pattern, "key": key, "result": {"item": f"{NS}:{result}"},
            "unlock": [{"item": next(iter(key.values()))["item"]}]}}
    write_json(os.path.join(BP, "recipes", "solar_frost_goggles.json"), shaped(
        "solar_frost_goggles", ["BBB", "IGI", "S S"],
        {"B": {"item": "minecraft:bone"}, "I": {"item": "minecraft:packed_ice"},
         "G": {"item": "minecraft:glowstone_dust"}, "S": {"item": "minecraft:string"}}, "solar_frost_goggles"))
    write_json(os.path.join(BP, "recipes", "endless_handline.json"), shaped(
        "endless_handline", ["PSP", "SES", " TI"],
        {"S": {"item": "minecraft:string"}, "P": {"item": "minecraft:oak_planks"}, "E": {"item": "minecraft:ender_pearl"},
         "T": {"item": "minecraft:stick"}, "I": {"item": "minecraft:iron_ingot"}}, "endless_handline"))
    write_json(os.path.join(BP, "recipes", "bamboo_sword_cane.json"), shaped(
        "bamboo_sword_cane", [" B ", " W ", " B "],
        {"B": {"item": "minecraft:bamboo"}, "W": {"item": "minecraft:iron_sword"}}, "bamboo_sword_cane"))
    # deep-water handline catches: the vanilla fishing pools with treasure/fish weighted up
    write_json(os.path.join(BP, "loot_tables", NS, "handline_deep.json"), {"pools": [{"rolls": 1, "entries": [
        {"type": "loot_table", "name": "loot_tables/gameplay/fishing/fish.json", "weight": 70},
        {"type": "loot_table", "name": "loot_tables/gameplay/fishing/treasure.json", "weight": 22},
        {"type": "loot_table", "name": "loot_tables/gameplay/fishing/junk.json", "weight": 8}]}]})


# =========================================================================== language

LORE_NOTE = "(controls are listed in the item's tooltip in game)"


def build_lang():
    en = ["pack.name=ODDWORKS - Fantasy Equipment (Set 01)",
          "pack.description=Solar Frost Goggles, Endless Handline and Bamboo Sword Cane - three odd tools, three skills each."]
    for key, name in ITEM_NAMES.items():
        en.append(f"item.{NS}:{key}.name={name}")
    for key, name in ENTITY_NAMES.items():
        en.append(f"entity.{NS}:{key}.name={name}")
    for root, lines in ((RP, en), (BP, en[:2])):
        write_text(os.path.join(root, "texts", "en_US.lang"), "\n".join(lines) + "\n")
        write_text(os.path.join(root, "texts", "languages.json"), json.dumps(["en_US"], indent=2) + "\n")


# =========================================================================== scripts + packaging

def build_scripts():
    out = os.path.join(BP, "scripts")
    tsc = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        raise SystemExit("TypeScript not installed: run `npm install` in oddworks-addon/")
    res = subprocess.run([tsc, "-p", os.path.join(ROOT, "tsconfig.json"), "--outDir", out], capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout, res.stderr)
        raise SystemExit("TypeScript compilation failed")


def zip_dir(zf, folder, arc_root):
    for dirpath, _, files in sorted(os.walk(folder)):
        for fn in sorted(files):
            full = os.path.join(dirpath, fn)
            zf.write(full, os.path.join(arc_root, os.path.relpath(full, folder)))


def package():
    os.makedirs(DIST, exist_ok=True)
    addon = os.path.join(DIST, f"{BASENAME}.mcaddon")
    with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as zf:
        zip_dir(zf, BP, "ODDWORKS_BP")
        zip_dir(zf, RP, "ODDWORKS_RP")
    for folder, suffix in ((BP, "BP"), (RP, "RP")):
        with zipfile.ZipFile(os.path.join(DIST, f"{BASENAME}_{suffix}.mcpack"), "w", zipfile.ZIP_DEFLATED) as zf:
            zip_dir(zf, folder, "")
    return addon


def pack_icon_image(built):
    import preview
    renders = [
        preview.showcase(preview.emissive_model(models.goggles()), anims.mk.rh((0, 28, -4.9)), 24, -24, 12,
                         hide=("fp_root", "fp_mask", "fp_mask_rim", "fp_mask_carve", "tp_glow_full"), size=(300, 300)),
        preview.showcase(preview.emissive_model(models.handline(False)), anims.mk.rh((0, 25, -1)), 30, -35, 18,
                         size=(300, 300)),
        preview.showcase(preview.emissive_model(models.cane(True)), anims.mk.rh((0, 17, 0)), 40, -30, 8,
                         hide=("hip_sheath",), pose={"sheath": {"position": [0, -9, 0]}}, size=(300, 300)),
    ]
    clear = []
    for r in renders:
        r = r.convert("RGBA")
        px = r.load()
        bg = px[0, 0]
        for y in range(r.height):
            for x in range(r.width):
                p = px[x, y]
                if abs(p[0] - bg[0]) + abs(p[1] - bg[1]) + abs(p[2] - bg[2]) < 18:
                    px[x, y] = (0, 0, 0, 0)
        clear.append(r)
    return icons.pack_icon(clear)


def main(skip_scripts=False):
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    built = build_models()
    manifests(pack_icon_image(built))
    build_icons()
    build_particles()
    build_sounds()
    build_attachables()
    build_client_entities()
    build_bp_entities()
    build_items()
    build_lang()
    if not skip_scripts:
        build_scripts()
    addon = package()
    print("built", os.path.relpath(addon, ROOT))


if __name__ == "__main__":
    main(skip_scripts="--no-scripts" in sys.argv)
