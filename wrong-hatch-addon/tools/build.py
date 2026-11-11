"""
Build script for "BOSS 001: The Wrong Hatch".

    python3 tools/build.py

Generates every resource/behaviour pack file (models, textures, animations,
controllers, render controllers, client + server entities, particles, sounds,
items, recipes, loot, language), writes src/generated/spec.ts, compiles the
TypeScript gameplay scripts and packages dist/The_Wrong_Hatch.mcaddon.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import anims  # noqa: E402
import boss_model  # noqa: E402
import icons  # noqa: E402
import minion_models  # noqa: E402
import sounds  # noqa: E402
import spec  # noqa: E402
import voxkit  # noqa: E402

BUILD = os.path.join(ROOT, "build")
BP = os.path.join(BUILD, "WrongHatch_BP")
RP = os.path.join(BUILD, "WrongHatch_RP")
DIST = os.path.join(ROOT, "dist")
NS = "wh"

ADDON_NAME = "BOSS 001: The Wrong Hatch"
VERSION = [1, 0, 0]
MIN_ENGINE = [1, 21, 100]
SERVER_VERSION = "2.1.0"   # stable since Bedrock 1.21.100 (Sept 2025): runs on every current client
UUID = {
    "bp_header": "3b9f0c1e-7d24-4a51-9e6b-2f8a1c0d5e11",
    "bp_data": "3b9f0c1e-7d24-4a51-9e6b-2f8a1c0d5e12",
    "bp_script": "3b9f0c1e-7d24-4a51-9e6b-2f8a1c0d5e13",
    "rp_header": "a6e2d4c8-1f37-4b90-8c5d-7e3f9a2b6c21",
    "rp_res": "a6e2d4c8-1f37-4b90-8c5d-7e3f9a2b6c22",
}

ITEMS = {
    # id: (english name, stack, extra components)
    "guillotine_pinion": ("Guillotine Pinion", 1),
    "golden_yolk": ("Golden Yolk", 16),
    "eggshell_plate": ("Living Eggshell Plate", 64),
    "hatch_core": ("Hatch Core", 16),
    "suspicious_egg": ("Suspicious Egg", 16),
}

ENTITY_NAMES = {
    "wrong_hatch": "The Wrong Hatch",
    "wrong_chick": "Wrong Chick",
    "hatch_egg": "Hatch Egg",
    "lobbed_egg": "Lobbed Egg",
    "brood_shell": "Brood Shell",
    "feather_dart": "Feather Dart",
    "wrong_hatch_remains": "The Wrong Hatch",
}

# particle definitions: id -> parameters
PARTICLES = {
    "gold_burst": dict(sprite="spark", color=(1.0, 0.78, 0.2), count=24, speed=6.0, life=(0.4, 0.8), size=0.16, drag=3.0),
    "gold_mote": dict(sprite="spark", color=(1.0, 0.82, 0.3), count=1, speed=0.2, life=(0.5, 0.9), size=0.14, drag=1.0),
    "beam": dict(sprite="flare", color=(1.0, 0.92, 0.55), count=1, speed=0.0, life=(0.12, 0.18), size=0.55, drag=0.0),
    "feather_burst": dict(sprite="feather", color=(0.97, 0.93, 0.84), count=16, speed=4.0, life=(1.4, 2.4), size=0.22,
                          drag=2.6, gravity=1.2, material="particles_alpha", spin=True),
    "feather_fall": dict(sprite="feather", color=(0.97, 0.93, 0.84), count=3, speed=1.0, life=(1.6, 2.6), size=0.2,
                         drag=2.0, gravity=0.9, material="particles_alpha", spin=True),
    "shell_burst": dict(sprite="shard", color=(0.97, 0.95, 0.9), count=22, speed=7.0, life=(0.9, 1.6), size=0.2,
                        drag=0.6, gravity=12.0, material="particles_alpha", spin=True),
    "shell_chip": dict(sprite="shard", color=(0.97, 0.95, 0.9), count=5, speed=3.0, life=(0.5, 0.9), size=0.12,
                       drag=0.6, gravity=10.0, material="particles_alpha", spin=True),
    "dust": dict(sprite="puff", color=(0.58, 0.48, 0.36), count=10, speed=3.0, life=(0.6, 1.1), size=0.4, drag=3.5,
                 material="particles_alpha", rise=0.6),
    "ring_dust": dict(sprite="puff", color=(0.75, 0.66, 0.52), count=2, speed=0.8, life=(0.4, 0.7), size=0.45, drag=2.0,
                      material="particles_alpha", rise=1.5),
    "warn_ring": dict(sprite="ring", color=(1.0, 0.28, 0.15), count=1, speed=0.0, life=(0.22, 0.22), size=1.0, drag=0.0,
                      flat=True, sized=True),
    "gold_ring": dict(sprite="ring", color=(1.0, 0.8, 0.25), count=1, speed=0.0, life=(0.22, 0.22), size=1.0, drag=0.0,
                      flat=True, sized=True),
    "warn_dot": dict(sprite="spark", color=(1.0, 0.3, 0.15), count=1, speed=0.0, life=(0.25, 0.3), size=0.22, drag=0.0),
    "rot_cloud": dict(sprite="puff", color=(0.45, 0.62, 0.2), count=6, speed=1.2, life=(1.0, 1.6), size=0.6, drag=2.0,
                      material="particles_alpha", rise=0.4),
    "stink": dict(sprite="puff", color=(0.5, 0.66, 0.25), count=1, speed=0.3, life=(0.8, 1.3), size=0.35, drag=1.0,
                  material="particles_alpha", rise=0.8),
    "stun_star": dict(sprite="star", color=(1.0, 0.92, 0.3), count=1, speed=0.4, life=(0.5, 0.8), size=0.3, drag=1.0),
    "flash": dict(sprite="flare", color=(1.0, 0.96, 0.75), count=1, speed=0.0, life=(0.25, 0.3), size=7.0, drag=0.0),
    "nova": dict(sprite="spark", color=(1.0, 0.8, 0.25), count=60, speed=14.0, life=(0.7, 1.2), size=0.32, drag=2.2),
    "ember": dict(sprite="spark", color=(1.0, 0.45, 0.12), count=8, speed=2.5, life=(0.4, 0.8), size=0.14, drag=2.0,
                  rise=0.8),
    "heal": dict(sprite="spark", color=(0.75, 1.0, 0.45), count=12, speed=1.5, life=(0.6, 1.0), size=0.16, drag=1.5,
                 rise=1.2),
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


def save_png(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)


# --------------------------------------------------------------------------- manifests

def manifests(icon_img):
    meta = {"authors": ["The Wrong Hatch team"], "product_type": "addon"}
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
        icon_img.save(os.path.join(p, "pack_icon.png"))


# --------------------------------------------------------------------------- models & textures

def glow_layer(tex: Image.Image) -> Image.Image:
    """Pulse overlay: only the emissive texels, opaque and brightened."""
    a = np.asarray(tex.convert("RGBA"), dtype=np.float32)
    out = np.zeros_like(a)
    emissive = a[..., 3] < 250
    k = (1 - a[..., 3] / 255.0)[..., None]
    out[..., :3] = np.clip(a[..., :3] * 0.6 + 255 * 0.4, 0, 255)
    out[..., 3] = np.where(emissive, 255 * k[..., 0], 0)
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def build_models():
    tex_dir = os.path.join(RP, "textures", "entity", "wrong_hatch")
    geo_dir = os.path.join(RP, "models", "entity", "wrong_hatch")
    boss = boss_model.build()
    write_json(os.path.join(geo_dir, "boss.geo.json"), boss.geometry_json(14, 8, 2.6))
    texs = []
    for v, name in enumerate(("boss_intact", "boss_cracked", "boss_awakened")):
        t = boss.paint(v)
        save_png(t, os.path.join(tex_dir, f"{name}.png"))
        texs.append(t)
    save_png(glow_layer(texs[2]), os.path.join(tex_dir, "boss_glow.png"))
    built = {"boss": (boss, texs)}
    variants = {"chick": ["chick", "yolkling"], "egg": ["egg_brood", "egg_rotten", "egg_gilded"],
                "brood_shell": ["brood_shell"], "feather_dart": ["feather_dart"]}
    bounds = {"chick": (1.5, 1.5, 0.5), "egg": (1.5, 1.5, 0.5), "brood_shell": (3, 3, 1), "feather_dart": (1.5, 1.5, 0.2)}
    for key, fn in minion_models.ALL.items():
        m = fn()
        bw, bh, oy = bounds[key]
        write_json(os.path.join(geo_dir, f"{key}.geo.json"), m.geometry_json(bw, bh, oy))
        ts = []
        for v, tn in enumerate(variants[key]):
            t = m.paint(v)
            save_png(t, os.path.join(tex_dir, f"{tn}.png"))
            ts.append(t)
        built[key] = (m, ts)
    return built


def build_icons():
    data = {}
    for name in icons.ICONS:
        save_png(icons.icon(name), os.path.join(RP, "textures", "items", "wrong_hatch", f"{name}.png"))
        data[f"{NS}_{name}"] = {"textures": f"textures/items/wrong_hatch/{name}"}
    write_json(os.path.join(RP, "textures", "item_texture.json"),
               {"resource_pack_name": "wrong_hatch", "texture_name": "atlas.items", "texture_data": data})
    save_png(icons.particle_atlas(), os.path.join(RP, "textures", "particle", "wrong_hatch.png"))


# --------------------------------------------------------------------------- particles

def particle_json(pid, p):
    r, g, b = p["color"]
    u, v = icons.PARTICLE_UV[p["sprite"]]
    size = p["size"]
    if p.get("sized"):
        sz = "math.max(variable.size, 0.5)"
        size_expr = [sz, sz]
    else:
        fade = f"{size} * (1.0 - variable.particle_age / variable.particle_lifetime * 0.6)"
        size_expr = [fade, fade]
    comps = {
        "minecraft:emitter_rate_instant": {"num_particles": p["count"]},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:particle_initial_speed": p["speed"],
        "minecraft:particle_lifetime_expression": {
            "max_lifetime": f"{p['life'][0]} + variable.particle_random_1 * {round(p['life'][1] - p['life'][0], 3)}"},
        "minecraft:particle_motion_dynamic": {
            "linear_acceleration": [0, p.get("rise", 0.0) - p.get("gravity", 0.0), 0],
            "linear_drag_coefficient": p["drag"]},
        "minecraft:particle_appearance_billboard": {
            "size": size_expr,
            "facing_camera_mode": "emitter_transform_xz" if p.get("flat") else "rotate_xyz",
            "uv": {"texture_width": 64, "texture_height": 64, "uv": [u, v], "uv_size": [16, 16]},
        },
        "minecraft:particle_appearance_tinting": {
            "color": [r, g, b, "1.0 - variable.particle_age / variable.particle_lifetime * 0.7"]},
    }
    if p.get("spin"):
        comps["minecraft:particle_initial_spin"] = {"rotation": "variable.particle_random_2 * 360",
                                                    "rotation_rate": "(variable.particle_random_3 - 0.5) * 400"}
    if p["count"] > 1 and p["speed"] > 0:
        comps["minecraft:emitter_shape_sphere"] = {"radius": 0.3, "surface_only": False, "direction": "outwards"}
    else:
        comps["minecraft:emitter_shape_point"] = {
            "direction": ["math.random(-1, 1)", "math.random(-0.2, 1)", "math.random(-1, 1)"]}
    return {
        "format_version": "1.10.0",
        "particle_effect": {
            "description": {"identifier": f"{NS}:{pid}",
                            "basic_render_parameters": {"material": p.get("material", "particles_add"),
                                                        "texture": "textures/particle/wrong_hatch"}},
            "components": comps,
        },
    }


def build_particles():
    for pid, p in PARTICLES.items():
        write_json(os.path.join(RP, "particles", "wrong_hatch", f"{pid}.json"), particle_json(pid, p))


# --------------------------------------------------------------------------- animations

SOUND_EFFECTS = {
    "crow": "wrong_hatch.crow", "peck": "wrong_hatch.peck", "wing_whoosh": "wrong_hatch.wing_whoosh",
    "guillotine": "wrong_hatch.guillotine", "scratch": "wrong_hatch.scratch", "fluff": "wrong_hatch.fluff",
    "shell_close": "wrong_hatch.shell_close", "cluck": "wrong_hatch.cluck", "charge": "wrong_hatch.charge",
    "pulse": "wrong_hatch.pulse", "flap": "wrong_hatch.flap", "molt": "wrong_hatch.molt", "nova": "wrong_hatch.nova",
}


def build_animations():
    boss_anims = anims.boss_animations()
    write_json(os.path.join(RP, "animations", "wrong_hatch.animation.json"),
               {"format_version": "1.8.0", "animations": boss_anims})
    write_json(os.path.join(RP, "animations", "wrong_hatch_minions.animation.json"),
               {"format_version": "1.8.0", "animations": anims.minion_animations()})
    ctrl = anims.boss_controller()
    ctrl.update(anims.minion_controller())
    write_json(os.path.join(RP, "animation_controllers", "wrong_hatch.animation_controllers.json"),
               {"format_version": "1.10.0", "animation_controllers": ctrl})
    return boss_anims


# --------------------------------------------------------------------------- render controllers + client entities

def build_render_controllers():
    rc = {
        "controller.render.wrong_hatch.boss": {
            "arrays": {"textures": {"Array.skins": ["Texture.intact", "Texture.cracked", "Texture.awakened"]}},
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}],
            "textures": ["Array.skins[math.clamp(query.property('wh:phase') - 1, 0, 2)]"],
        },
        "controller.render.wrong_hatch.glow": {
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.glow"}],
            "textures": ["Texture.glow"],
            "ignore_lighting": True,
            "color": {"r": 1.0, "g": 0.92, "b": 0.6, "a": "variable.glow"},
        },
        "controller.render.wrong_hatch.chick": {
            "arrays": {"textures": {"Array.skins": ["Texture.chick", "Texture.yolkling"]}},
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}],
            "textures": ["Array.skins[math.clamp(query.variant, 0, 1)]"],
        },
        "controller.render.wrong_hatch.egg": {
            "arrays": {"textures": {"Array.skins": ["Texture.brood", "Texture.rotten", "Texture.gilded"]}},
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}],
            "textures": ["Array.skins[query.property('wh:kind') == 3 ? 0 : math.clamp(query.property('wh:kind'), 0, 2)]"],
        },
        "controller.render.wrong_hatch.default": {
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}],
            "textures": ["Texture.default"],
        },
    }
    write_json(os.path.join(RP, "render_controllers", "wrong_hatch.render_controllers.json"),
               {"format_version": "1.8.0", "render_controllers": rc})


def boss_client(boss_anims):
    A = spec.ACTION_ID
    act = "variable.act"
    glow = (
        "variable.glow = math.clamp("
        "(variable.phase >= 3 ? 0.32 + math.sin(query.life_time * 240) * 0.14 : (variable.phase == 2 ? 0.1 : 0.0))"
        f" + (({act} == {A['beam_charge']} || {act} == {A['beam_fire']}) ? 0.6 : 0.0)"
        f" + ({act} == {A['dawn_flash']} ? 0.35 + math.sin(query.life_time * 420) * 0.3 : 0.0)"
        f" + ({act} == {A['final_hatch']} ? 0.5 + math.sin(query.life_time * 720) * 0.4 : 0.0)"
        f" + (({act} == {A['hatch_nova']} || {act} == {A['death']} || {act} == {A['crow']}) ? 0.7 : 0.0)"
        f" + ({act} == {A['stunned']} ? -0.2 : 0.0)"
        ", 0.0, 1.0);"
    )
    anim_map = {"idle": "animation.wrong_hatch.idle", "walk": "animation.wrong_hatch.walk",
                "turn": "animation.wrong_hatch.turn", "look": "animation.wrong_hatch.look",
                "hurt": "animation.wrong_hatch.hurt", "action_ctrl": "controller.animation.wrong_hatch.action"}
    for name, _, _ in spec.ACTIONS:
        if name != "none":
            anim_map[name] = f"animation.wrong_hatch.{name}"
    busy = f"{act} != 0"
    return {
        "format_version": "1.10.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": f"{NS}:wrong_hatch",
                "materials": {"default": "entity_emissive_alpha", "glow": "warden_bioluminescent_layer"},
                "textures": {
                    "intact": "textures/entity/wrong_hatch/boss_intact",
                    "cracked": "textures/entity/wrong_hatch/boss_cracked",
                    "awakened": "textures/entity/wrong_hatch/boss_awakened",
                    "glow": "textures/entity/wrong_hatch/boss_glow",
                },
                "geometry": {"default": "geometry.wrong_hatch.boss"},
                "animations": anim_map,
                "scripts": {
                    "pre_animation": [
                        "variable.phase = query.has_property('wh:phase') ? query.property('wh:phase') : 1;",
                        "variable.act = query.has_property('wh:anim') ? query.property('wh:anim') : 0;",
                        glow,
                    ],
                    "animate": [
                        "idle",
                        {"walk": f"query.modified_move_speed > 0.01 && !({busy})"},
                        {"turn": f"!({busy}) && query.modified_move_speed < 0.05"},
                        {"look": f"!({busy})"},
                        {"hurt": "query.hurt_time > 0"},
                        "action_ctrl",
                    ],
                },
                "render_controllers": ["controller.render.wrong_hatch.boss",
                                       {"controller.render.wrong_hatch.glow": "variable.glow > 0.02"}],
                "spawn_egg": {"texture": f"{NS}_spawn_egg", "texture_index": 0},
                "sound_effects": {k: {"effect": v} for k, v in SOUND_EFFECTS.items()},
                "enable_attachables": False,
            }
        },
    }


def simple_client(identifier, geometry, textures, materials, rcs, animations=None, animate=None, pre=None):
    desc = {
        "identifier": identifier,
        "materials": materials,
        "textures": textures,
        "geometry": {"default": geometry},
        "render_controllers": rcs,
    }
    if animations:
        desc["animations"] = animations
        desc["scripts"] = {"animate": animate}
        if pre:
            desc["scripts"]["pre_animation"] = pre
    return {"format_version": "1.10.0", "minecraft:client_entity": {"description": desc}}


def build_client_entities(boss_anims):
    ed = os.path.join(RP, "entity", "wrong_hatch")
    write_json(os.path.join(ed, "wrong_hatch.entity.json"), boss_client(boss_anims))
    remains = boss_client(boss_anims)
    rd = remains["minecraft:client_entity"]["description"]
    rd["identifier"] = f"{NS}:wrong_hatch_remains"
    del rd["spawn_egg"]
    write_json(os.path.join(ed, "wrong_hatch_remains.entity.json"), remains)
    T = "textures/entity/wrong_hatch/"
    write_json(os.path.join(ed, "wrong_chick.entity.json"), simple_client(
        f"{NS}:wrong_chick", "geometry.wrong_hatch.chick",
        {"chick": T + "chick", "yolkling": T + "yolkling"}, {"default": "entity_emissive_alpha"},
        ["controller.render.wrong_hatch.chick"],
        {"move": "animation.wrong_hatch.chick.move", "fuse": "animation.wrong_hatch.chick.fuse",
         "ctrl": "controller.animation.wrong_hatch.chick"}, ["ctrl"]))
    write_json(os.path.join(ed, "hatch_egg.entity.json"), simple_client(
        f"{NS}:hatch_egg", "geometry.wrong_hatch.egg",
        {"brood": T + "egg_brood", "rotten": T + "egg_rotten", "gilded": T + "egg_gilded"},
        {"default": "entity_emissive_alpha"}, ["controller.render.wrong_hatch.egg"],
        {"wobble": "animation.wrong_hatch.egg.wobble"}, ["wobble"]))
    write_json(os.path.join(ed, "lobbed_egg.entity.json"), simple_client(
        f"{NS}:lobbed_egg", "geometry.wrong_hatch.egg", {"default": T + "egg_brood"},
        {"default": "entity_emissive_alpha"}, ["controller.render.wrong_hatch.default"],
        {"spin": "animation.wrong_hatch.egg.lobbed"}, ["spin"]))
    write_json(os.path.join(ed, "brood_shell.entity.json"), simple_client(
        f"{NS}:brood_shell", "geometry.wrong_hatch.brood_shell", {"default": T + "brood_shell"},
        {"default": "entity_emissive_alpha"}, ["controller.render.wrong_hatch.default"],
        {"pulse": "animation.wrong_hatch.brood_shell.pulse"}, ["pulse"]))
    write_json(os.path.join(ed, "feather_dart.entity.json"), simple_client(
        f"{NS}:feather_dart", "geometry.wrong_hatch.feather_dart", {"default": T + "feather_dart"},
        {"default": "entity_emissive_alpha"}, ["controller.render.wrong_hatch.default"],
        {"fly": "animation.wrong_hatch.feather_dart.fly"}, ["fly"]))


def build_sounds():
    defs = sounds.build(RP)
    write_json(os.path.join(RP, "sounds", "sound_definitions.json"), defs)
    write_json(os.path.join(RP, "sounds.json"), {
        "entity_sounds": {"entities": {
            f"{NS}:wrong_hatch": {"volume": 1.0, "pitch": [0.9, 1.0], "events": {
                "ambient": "wrong_hatch.cluck",
                "hurt": {"sound": "wrong_hatch.hurt", "volume": 1.0},
                "step": {"sound": "wrong_hatch.step", "volume": 0.8},
            }},
            f"{NS}:wrong_chick": {"volume": 0.8, "pitch": [0.9, 1.1], "events": {
                "ambient": "wrong_hatch.chick",
                "hurt": "mob.baby_chicken.hurt",
                "death": "mob.baby_chicken.death",
            }},
            f"{NS}:hatch_egg": {"volume": 1.0, "pitch": [0.9, 1.1], "events": {
                "hurt": "wrong_hatch.crack",
            }},
            f"{NS}:brood_shell": {"volume": 1.0, "pitch": [0.7, 0.8], "events": {
                "hurt": "wrong_hatch.crack",
            }},
        }}
    })
    return defs


# --------------------------------------------------------------------------- behaviour entities

def despawn_group():
    return {f"{NS}:despawn": {"minecraft:instant_despawn": {}}}


def event_add(*groups, remove=()):
    e = {"add": {"component_groups": list(groups)}}
    if remove:
        e["remove"] = {"component_groups": list(remove)}
    return e


PLAYER_FILTER = {"test": "is_family", "subject": "other", "value": "player"}


def dmode_trigger(mode, deals=None, mul=None):
    t = {"on_damage": {"filters": {"test": "int_property", "subject": "self", "domain": f"{NS}:dmode", "operator": "==",
                                   "value": mode}}}
    if deals:
        t["deals_damage"] = deals
    if mul:
        t["damage_multiplier"] = mul
    return t


def boss_entity():
    hp_groups = {}
    hp_events = {}
    hp_names = [f"{NS}:hp_{i}" for i in range(1, 5)]
    for i, hp in enumerate((600, 900, 1200, 1500), start=1):
        hp_groups[f"{NS}:hp_{i}"] = {"minecraft:health": {"value": hp, "max": hp}}
        hp_events[f"{NS}:hp_{i}"] = event_add(f"{NS}:hp_{i}", remove=[n for n in hp_names if n != f"{NS}:hp_{i}"])
    chase = lambda speed: {  # noqa: E731
        "minecraft:movement": {"value": speed},
        "minecraft:behavior.melee_box_attack": {"priority": 3, "speed_multiplier": 1.0, "track_target": True,
                                                "require_complete_path": False, "cooldown_time": 1.0},
    }
    return {
        "format_version": "1.21.50",
        "minecraft:entity": {
            "description": {
                "identifier": f"{NS}:wrong_hatch",
                "is_spawnable": True,
                "is_summonable": True,
                "properties": {
                    f"{NS}:anim": {"type": "int", "range": [0, 63], "default": 0, "client_sync": True},
                    f"{NS}:phase": {"type": "int", "range": [0, 3], "default": 1, "client_sync": True},
                    # 0 normal, 1 invulnerable, 2 Shell Fortress (x0.15), 3 exposed (x1.5), 4 dazed (x1.35)
                    f"{NS}:dmode": {"type": "int", "range": [0, 4], "default": 0, "client_sync": False},
                },
            },
            "component_groups": {
                f"{NS}:chase": chase(0.27),
                f"{NS}:chase_fast": chase(0.33),
                f"{NS}:busy": {"minecraft:movement": {"value": 0.0}},
                f"{NS}:airborne": {"minecraft:physics": {"has_gravity": False, "has_collision": True}},
                **hp_groups,
                **despawn_group(),
            },
            "components": {
                "minecraft:type_family": {"family": ["wrong_hatch", "boss", "monster", "mob"]},
                "minecraft:health": {"value": 600, "max": 600},
                "minecraft:boss": {"hud_range": 64, "should_darken_sky": False, "name": "The Wrong Hatch"},
                "minecraft:collision_box": {"width": 2.8, "height": 4.8},
                "minecraft:custom_hit_test": {"hitboxes": [{"width": 4.4, "height": 5.0, "pivot": [0, 2.5, 0]}]},
                "minecraft:attack": {"damage": 0},
                "minecraft:movement": {"value": 0.27},
                "minecraft:movement.basic": {},
                "minecraft:navigation.walk": {"can_path_over_water": True, "avoid_water": False,
                                              "avoid_damage_blocks": True, "can_open_doors": False},
                "minecraft:jump.static": {},
                "minecraft:variable_max_auto_step": {"base_value": 1.0625, "jump_prevented_value": 1.0625},
                "minecraft:physics": {},
                "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
                "minecraft:knockback_resistance": {"value": 1.0},
                "minecraft:fire_immune": {},
                "minecraft:nameable": {},
                "minecraft:persistent": {},
                "minecraft:follow_range": {"value": 64, "max": 64},
                "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0, "breathes_water": True},
                "minecraft:damage_sensor": {"triggers": [
                    {"cause": "fall", "deals_damage": "no"},
                    {"cause": "suffocation", "deals_damage": "no"},
                    {"cause": "drowning", "deals_damage": "no"},
                    {"on_damage": {"filters": {"test": "is_family", "subject": "other", "value": "wrong_hatch_minion"}},
                     "deals_damage": "no"},
                    dmode_trigger(1, deals="no"),
                    dmode_trigger(2, mul=0.15),
                    dmode_trigger(3, mul=1.5),
                    dmode_trigger(4, mul=1.35),
                ]},
                "minecraft:behavior.hurt_by_target": {"priority": 1},
                "minecraft:behavior.nearest_attackable_target": {
                    "priority": 2, "must_see": False, "reselect_targets": True, "within_radius": 48,
                    "entity_types": [{"filters": PLAYER_FILTER, "max_dist": 48}],
                },
                "minecraft:conditional_bandwidth_optimization": {},
            },
            "events": {
                "minecraft:entity_spawned": event_add(f"{NS}:busy"),
                f"{NS}:chase": event_add(f"{NS}:chase", remove=[f"{NS}:busy", f"{NS}:chase_fast"]),
                f"{NS}:chase_fast": event_add(f"{NS}:chase_fast", remove=[f"{NS}:busy", f"{NS}:chase"]),
                f"{NS}:busy": event_add(f"{NS}:busy", remove=[f"{NS}:chase", f"{NS}:chase_fast"]),
                f"{NS}:airborne_on": event_add(f"{NS}:airborne"),
                f"{NS}:airborne_off": {"remove": {"component_groups": [f"{NS}:airborne"]}},
                **hp_events,
                f"{NS}:despawn": event_add(f"{NS}:despawn"),
            },
        },
    }


def chick_entity():
    hostile = {
        "minecraft:type_family": {"family": ["wrong_hatch_minion", "monster", "mob"]},
        "minecraft:behavior.melee_attack": {"priority": 3, "speed_multiplier": 1.15, "track_target": True},
        "minecraft:behavior.nearest_attackable_target": {
            "priority": 2, "must_see": False, "reselect_targets": True, "within_radius": 32,
            "entity_types": [{"filters": PLAYER_FILTER, "max_dist": 32}]},
        "minecraft:behavior.hurt_by_target": {"priority": 1},
        "minecraft:timer": {"looping": False, "time": 90, "randomInterval": False,
                            "time_down_event": {"event": f"{NS}:despawn", "target": "self"}},
    }
    friendly = {
        "minecraft:type_family": {"family": ["wrong_hatch_pet", "mob"]},
        "minecraft:is_tamed": {},
        "minecraft:tameable": {"probability": 0.0, "tame_items": "minecraft:golden_carrot"},
        "minecraft:behavior.melee_attack": {"priority": 3, "speed_multiplier": 1.2, "track_target": True},
        "minecraft:behavior.owner_hurt_by_target": {"priority": 1},
        "minecraft:behavior.owner_hurt_target": {"priority": 2},
        "minecraft:behavior.nearest_attackable_target": {
            "priority": 4, "must_see": True, "reselect_targets": True, "within_radius": 16,
            "entity_types": [{"filters": {"all_of": [{"test": "is_family", "subject": "other", "value": "monster"},
                                                     {"test": "is_family", "subject": "other", "operator": "!=",
                                                      "value": "creeper"}]}, "max_dist": 16}]},
        "minecraft:behavior.follow_owner": {"priority": 5, "speed_multiplier": 1.3, "start_distance": 8,
                                            "stop_distance": 2},
        "minecraft:health": {"value": 30, "max": 30},
        "minecraft:attack": {"damage": 5},
        "minecraft:variant": {"value": 1},
        "minecraft:nameable": {},
        "minecraft:persistent": {},
    }
    return {
        "format_version": "1.21.50",
        "minecraft:entity": {
            "description": {
                "identifier": f"{NS}:wrong_chick", "is_spawnable": False, "is_summonable": True,
                "properties": {f"{NS}:fuse": {"type": "bool", "default": False, "client_sync": True}},
            },
            "component_groups": {
                f"{NS}:hostile": hostile,
                f"{NS}:yolkling": {"minecraft:variant": {"value": 1}, "minecraft:health": {"value": 6, "max": 6},
                                   "minecraft:movement": {"value": 0.36}, "minecraft:attack": {"damage": 1}},
                f"{NS}:friendly": friendly,
                **despawn_group(),
            },
            "components": {
                "minecraft:health": {"value": 8, "max": 8},
                "minecraft:attack": {"damage": 3},
                "minecraft:variant": {"value": 0},
                "minecraft:collision_box": {"width": 0.5, "height": 0.8},
                "minecraft:movement": {"value": 0.32},
                "minecraft:movement.basic": {},
                "minecraft:navigation.walk": {"can_path_over_water": True, "avoid_damage_blocks": True},
                "minecraft:jump.static": {},
                "minecraft:physics": {},
                "minecraft:pushable": {"is_pushable": True, "is_pushable_by_piston": True},
                "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0},
                "minecraft:damage_sensor": {"triggers": [{"cause": "fall", "deals_damage": "no"}]},
                "minecraft:behavior.float": {"priority": 0},
                "minecraft:behavior.random_stroll": {"priority": 7, "speed_multiplier": 1.0},
                "minecraft:behavior.random_look_around": {"priority": 9},
                "minecraft:conditional_bandwidth_optimization": {},
            },
            "events": {
                "minecraft:entity_spawned": event_add(f"{NS}:hostile"),
                f"{NS}:become_yolkling": event_add(f"{NS}:yolkling"),
                f"{NS}:become_friendly": event_add(f"{NS}:friendly", remove=[f"{NS}:hostile", f"{NS}:yolkling"]),
                f"{NS}:despawn": event_add(f"{NS}:despawn"),
            },
        },
    }


def prop_entity(identifier, families, width, height, health=None, properties=None, groups=None, events=None,
                lifetime=None, vulnerable=True):
    comps = {
        "minecraft:type_family": {"family": families},
        "minecraft:collision_box": {"width": width, "height": height},
        "minecraft:physics": {"has_gravity": vulnerable, "has_collision": vulnerable},
        "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
        "minecraft:knockback_resistance": {"value": 1.0},
        "minecraft:fire_immune": {},
        "minecraft:conditional_bandwidth_optimization": {},
    }
    if health:
        comps["minecraft:health"] = {"value": health, "max": health}
    if vulnerable:
        comps["minecraft:damage_sensor"] = {"triggers": [{"cause": "fall", "deals_damage": "no"},
                                                         {"cause": "suffocation", "deals_damage": "no"}]}
    else:
        comps["minecraft:damage_sensor"] = {"triggers": [{"cause": "all", "deals_damage": "no"}]}
    if lifetime:
        comps["minecraft:timer"] = {"looping": False, "time": lifetime, "randomInterval": False,
                                    "time_down_event": {"event": f"{NS}:despawn", "target": "self"}}
    desc = {"identifier": identifier, "is_spawnable": False, "is_summonable": True}
    if properties:
        desc["properties"] = properties
    g = despawn_group()
    g.update(groups or {})
    ev = {f"{NS}:despawn": event_add(f"{NS}:despawn")}
    ev.update(events or {})
    return {"format_version": "1.21.50",
            "minecraft:entity": {"description": desc, "component_groups": g, "components": comps, "events": ev}}


def build_bp_entities():
    ed = os.path.join(BP, "entities", "wrong_hatch")
    write_json(os.path.join(ed, "wrong_hatch.json"), boss_entity())
    write_json(os.path.join(ed, "wrong_chick.json"), chick_entity())
    write_json(os.path.join(ed, "hatch_egg.json"), prop_entity(
        f"{NS}:hatch_egg", ["wrong_hatch_egg", "inanimate"], 0.7, 0.75, health=4,
        properties={f"{NS}:kind": {"type": "int", "range": [0, 3], "default": 0, "client_sync": True}},
        groups={f"{NS}:rotten": {"minecraft:health": {"value": 10, "max": 10}}},
        events={f"{NS}:rotten": event_add(f"{NS}:rotten")}, lifetime=30))
    shell_groups = {f"{NS}:shell_{i}": {"minecraft:health": {"value": hp, "max": hp}}
                    for i, hp in enumerate((40, 50, 60, 70), start=1)}
    write_json(os.path.join(ed, "brood_shell.json"), prop_entity(
        f"{NS}:brood_shell", ["wrong_hatch_egg", "brood_shell", "inanimate"], 1.1, 1.7, health=40,
        groups=shell_groups, events={k: event_add(k) for k in shell_groups}, lifetime=60))
    write_json(os.path.join(ed, "wrong_hatch_remains.json"), prop_entity(
        f"{NS}:wrong_hatch_remains", ["wrong_hatch_remains", "inanimate"], 2.8, 4.8,
        properties={f"{NS}:anim": {"type": "int", "range": [0, 63], "default": 0, "client_sync": True},
                    f"{NS}:phase": {"type": "int", "range": [0, 3], "default": 1, "client_sync": True}},
        lifetime=30, vulnerable=False))
    write_json(os.path.join(ed, "lobbed_egg.json"), prop_entity(
        f"{NS}:lobbed_egg", ["wrong_hatch_projectile", "inanimate"], 0.3, 0.3, lifetime=8, vulnerable=False))
    write_json(os.path.join(ed, "feather_dart.json"), prop_entity(
        f"{NS}:feather_dart", ["wrong_hatch_projectile", "inanimate"], 0.25, 0.25, lifetime=6, vulnerable=False))


# --------------------------------------------------------------------------- items, recipes, loot

def build_items():
    for key, (_, stack) in ITEMS.items():
        comps = {
            "minecraft:icon": {"textures": {"default": f"{NS}_{key}"}},
            "minecraft:display_name": {"value": f"item.{NS}:{key}.name"},
            "minecraft:max_stack_size": stack,
            "minecraft:tags": {"tags": [f"{NS}:boss_reward"]},
        }
        category = "items"
        if key == "guillotine_pinion":
            category = "equipment"
            comps.update({
                "minecraft:hand_equipped": True,
                "minecraft:damage": 9,
                "minecraft:durability": {"max_durability": 1200},
                "minecraft:enchantable": {"slot": "sword", "value": 14},
                "minecraft:cooldown": {"category": f"{NS}:feather_fan", "duration": 6.0},
            })
        elif key == "golden_yolk":
            comps.update({
                "minecraft:food": {"nutrition": 6, "saturation_modifier": 1.2, "can_always_eat": True},
                "minecraft:use_animation": "eat",
                "minecraft:use_modifiers": {"use_duration": 1.6, "movement_modifier": 0.35},
            })
        elif key == "hatch_core":
            comps["minecraft:cooldown"] = {"category": f"{NS}:hatch_core", "duration": 2.0}
        item = {"format_version": "1.21.60", "minecraft:item": {
            "description": {"identifier": f"{NS}:{key}", "menu_category": {"category": category}},
            "components": comps}}
        write_json(os.path.join(BP, "items", "wrong_hatch", f"{key}.json"), item)
    recipes = {
        "suspicious_egg": {"format_version": "1.20.10", "minecraft:recipe_shapeless": {
            "description": {"identifier": f"{NS}:suspicious_egg"},
            "tags": ["crafting_table"],
            "ingredients": [{"item": "minecraft:egg"}, {"item": "minecraft:gold_block"},
                            {"item": "minecraft:fermented_spider_eye"}],
            "result": {"item": f"{NS}:suspicious_egg"},
            "unlock": [{"item": "minecraft:egg"}]}},
        "suspicious_egg_from_plate": {"format_version": "1.20.10", "minecraft:recipe_shapeless": {
            "description": {"identifier": f"{NS}:suspicious_egg_from_plate"},
            "tags": ["crafting_table"],
            "ingredients": [{"item": "minecraft:egg"}, {"item": f"{NS}:eggshell_plate"},
                            {"item": "minecraft:gold_ingot"}],
            "result": {"item": f"{NS}:suspicious_egg"},
            "unlock": [{"item": f"{NS}:eggshell_plate"}]}},
    }
    for k, r in recipes.items():
        write_json(os.path.join(BP, "recipes", f"{k}.json"), r)
    loot = {"pools": [
        {"rolls": 1, "entries": [{"type": "item", "name": f"{NS}:guillotine_pinion", "weight": 1}]},
        {"rolls": 1, "entries": [{"type": "item", "name": f"{NS}:hatch_core", "weight": 1}]},
        {"rolls": 1, "entries": [{"type": "item", "name": f"{NS}:eggshell_plate", "weight": 1,
                                  "functions": [{"function": "set_count", "count": {"min": 6, "max": 10}}]}]},
        {"rolls": 1, "entries": [{"type": "item", "name": f"{NS}:golden_yolk", "weight": 1,
                                  "functions": [{"function": "set_count", "count": {"min": 3, "max": 5}}]}]},
        {"rolls": 1, "entries": [{"type": "item", "name": "minecraft:gold_ingot", "weight": 1,
                                  "functions": [{"function": "set_count", "count": {"min": 8, "max": 16}}]}]},
        {"rolls": 1, "entries": [{"type": "item", "name": "minecraft:egg", "weight": 1,
                                  "functions": [{"function": "set_count", "count": {"min": 8, "max": 16}}]}]},
    ]}
    write_json(os.path.join(BP, "loot_tables", "entities", "wrong_hatch.json"), loot)


# --------------------------------------------------------------------------- language

def build_lang():
    en = [
        f"pack.name={ADDON_NAME}",
        "pack.description=A monstrous chicken wrapped in a living eggshell. 3 phases, 18 abilities.",
    ]
    for key, (name, _) in ITEMS.items():
        en.append(f"item.{NS}:{key}.name={name}")
    for key, name in ENTITY_NAMES.items():
        en.append(f"entity.{NS}:{key}.name={name}")
    en.append(f"item.spawn_egg.entity.{NS}:wrong_hatch.name=Spawn The Wrong Hatch")
    for root in (BP, RP):
        write_text(os.path.join(root, "texts", "en_US.lang"), "\n".join(en if root == RP else en[:2]) + "\n")
        write_text(os.path.join(root, "texts", "languages.json"), json.dumps(["en_US"], indent=2) + "\n")


# --------------------------------------------------------------------------- scripts

def build_scripts():
    write_text(os.path.join(ROOT, "src", "generated", "spec.ts"), spec.ts_source())
    out = os.path.join(BP, "scripts")
    tsc = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        raise SystemExit("TypeScript not installed: run `npm install` in wrong-hatch-addon/")
    res = subprocess.run([tsc, "-p", os.path.join(ROOT, "tsconfig.json"), "--outDir", out],
                         capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout, res.stderr)
        raise SystemExit("TypeScript compilation failed")


# --------------------------------------------------------------------------- packaging

def zip_dir(zf, folder, arc_root):
    for dirpath, _, files in sorted(os.walk(folder)):
        for fn in sorted(files):
            full = os.path.join(dirpath, fn)
            zf.write(full, os.path.join(arc_root, os.path.relpath(full, folder)))


def package():
    os.makedirs(DIST, exist_ok=True)
    base = "The_Wrong_Hatch"
    addon = os.path.join(DIST, f"{base}.mcaddon")
    with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as zf:
        zip_dir(zf, BP, "WrongHatch_BP")
        zip_dir(zf, RP, "WrongHatch_RP")
    for folder, suffix in ((BP, "BP"), (RP, "RP")):
        with zipfile.ZipFile(os.path.join(DIST, f"{base}_{suffix}.mcpack"), "w", zipfile.ZIP_DEFLATED) as zf:
            zip_dir(zf, folder, "")
    return addon


def main():
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    built = build_models()
    boss, texs = built["boss"]
    front = voxkit.render(boss, texs[0], yaw=20, pitch=8, size=256, margin=0.02)
    manifests(icons.pack_icon(front))
    build_icons()
    build_particles()
    boss_anims = build_animations()
    build_render_controllers()
    build_client_entities(boss_anims)
    build_sounds()
    build_bp_entities()
    build_items()
    build_lang()
    if "--no-scripts" not in sys.argv:
        build_scripts()
        addon = package()
        print("built", os.path.relpath(addon, ROOT), boss.stats())
    else:
        print("built packs (scripts skipped)", boss.stats())


if __name__ == "__main__":
    main()
