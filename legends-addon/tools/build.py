"""
Build script for "Legendary & Divine Beings".

    python3 tools/build.py          -> build/Legends_BP + build/Legends_RP + dist/*.mcaddon

Generates every pack file from the Python creature specs (models, textures,
animations, animation controllers, render controllers, client + server
entities, items, recipes, loot tables, particles, languages), writes the
act/timing table the TypeScript scripts import (src/generated/data.ts),
compiles the scripts and packages the add-on.
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

import icons  # noqa: E402
from creatures import registry  # noqa: E402
from creatures.common import Creature  # noqa: E402

BUILD = os.path.join(ROOT, "build")
BP = os.path.join(BUILD, "Legends_BP")
RP = os.path.join(BUILD, "Legends_RP")
DIST = os.path.join(ROOT, "dist")
GEN_TS = os.path.join(ROOT, "src", "generated", "data.ts")

ADDON_NAME = "Legendary & Divine Beings"
DIST_BASE = "Legendary_and_Divine_Beings"
VERSION = [1, 0, 0]
MIN_ENGINE = [1, 26, 60]
SERVER_VERSION = "2.11.0"
SERVER_UI_VERSION = "2.3.0"
UUID = {
    "bp_header": "b3a1c7e2-5d4f-4a8b-9c0e-7f1a2b3c4d51",
    "bp_data": "b3a1c7e2-5d4f-4a8b-9c0e-7f1a2b3c4d52",
    "bp_script": "b3a1c7e2-5d4f-4a8b-9c0e-7f1a2b3c4d53",
    "rp_header": "e8d2f4a6-1b3c-4e5f-8a7b-2c4d6e8f0a11",
    "rp_res": "e8d2f4a6-1b3c-4e5f-8a7b-2c4d6e8f0a12",
}

# --------------------------------------------------------------------------- gameplay stats
# hp / collision (w, h in blocks) / hitbox (w, h) / boss bar sky darkening / xp
BOSSES = {
    "taotie": dict(name="Taotie, the Devouring Maw", hp=1600, col=(3.0, 3.4), hit=(5.2, 4.6), darken=False, xp=1500),
    "nidhogg": dict(name="Nidhogg, Gnawer of the World-Root", hp=2000, col=(3.0, 3.0), hit=(6.0, 4.2), darken=True, xp=1800),
    "hanuman": dict(name="Hanuman, Son of the Wind", hp=1500, col=(1.4, 4.0), hit=(2.0, 4.4), darken=False, xp=1600,
                    forms={"legends:form_divine": dict(col=(2.0, 5.6), hit=(2.8, 6.2)),
                           "legends:form_tiny": dict(col=(0.6, 1.4), hit=(0.8, 1.6))}),
    "alicorn": dict(name="Alicorn, Dawnstar Sovereign", hp=1400, col=(2.2, 3.4), hit=(3.2, 3.8), darken=False, xp=1500),
    "tenko": dict(name="Tenko, the Ten-Tailed Fox", hp=1700, col=(2.2, 3.2), hit=(3.6, 3.8), darken=False, xp=1600),
    "logos": dict(name="The Word of God", hp=2600, col=(4.0, 8.0), hit=(6.0, 8.5), darken=False, xp=3000),
}
CHOIR = {
    "seraph": dict(name="Seraph of the Burning Choir", hp=220, col=(1.6, 3.0)),
    "cherub": dict(name="Cherub of the Eastern Gate", hp=300, col=(1.6, 3.4)),
    "ophan": dict(name="Ophan of the Thrones", hp=260, col=(2.6, 3.4)),
}
ILLUSIONS = {"tenko_illusion": dict(name="Foxfire Illusion", hp=1, col=(2.0, 3.0), model="tenko")}
# props: hp (0 = invulnerable), collision, lifetime safety timer (s)
PROPS = {
    "ding": dict(name="Ritual Ding", hp=0, col=(2.6, 2.6), life=60),
    "root_spike": dict(name="Yggdrasil Root", hp=0, col=(1.0, 3.0), life=20),
    "nid_meteor": dict(name="Corpse-Fire", hp=0, col=(1.0, 1.0), life=20),
    "discus": dict(name="Divine Discus", hp=0, col=(1.0, 0.5), life=20),
    "boulder": dict(name="Uprooted Mountain", hp=0, col=(2.5, 2.5), life=20),
    "wind_wisp": dict(name="Breath of Vayu", hp=14, col=(1.0, 1.4), life=30),
    "crescent": dict(name="Crescent of the Night", hp=0, col=(1.0, 0.6), life=30),
    "prism": dict(name="Prism of Dawn", hp=40, col=(1.2, 2.4), life=60),
    "star_lance": dict(name="Starlight Lance", hp=0, col=(0.6, 0.6), life=15),
    "foxfire": dict(name="Foxfire", hp=0, col=(0.6, 0.6), life=20),
    "torii": dict(name="Torii of the Fox", hp=0, col=(1.0, 3.0), life=30),
    "tail_spike": dict(name="Tail of the Fox", hp=0, col=(1.0, 3.0), life=15),
    "tablet": dict(name="Tablet of the Word", hp=0, col=(1.4, 1.6), life=20),
    "light_spear": dict(name="Spear of Light", hp=0, col=(0.6, 0.6), life=15),
    "eden_sword": dict(name="Flaming Sword of Eden", hp=0, col=(1.0, 3.0), life=30),
    "coal": dict(name="Live Coal", hp=0, col=(0.6, 0.6), life=20),
}

ITEMS = {
    # id: (english, thai, icon, glint)
    "sigil_taotie": ("Bronze Ding of Gluttony", "ติ่งสำริดแห่งความตะกละ", True),
    "sigil_nidhogg": ("Gnawed Root of Yggdrasil", "รากอิกดราซิลที่ถูกแทะ", True),
    "sigil_hanuman": ("Wind-Crystal Trident", "ตรีเพชรแห่งวายุ", True),
    "sigil_alicorn": ("Horn of the Dawnstar", "เขาแห่งดาวรุ่ง", True),
    "sigil_tenko": ("Ten-Tailed Star Pearl", "ดวงแก้วจิ้งจอกสิบหาง", True),
    "sigil_logos": ("The Unspoken Word", "พระวจนะที่ยังไม่ถูกเปล่ง", True),
    "core_taotie": ("Gluttony Heart of Taotie", "หัวใจแห่งความตะกละ", True),
    "core_nidhogg": ("Venom Fang of Nidhogg", "เขี้ยวพิษนิดฮ็อกก์", True),
    "core_hanuman": ("Diamond Hair of Hanuman", "ขนเพชรหนุมาน", True),
    "core_alicorn": ("Dawn Feather of the Alicorn", "ขนนกแห่งรุ่งอรุณ", True),
    "core_tenko": ("Flame of the Tenth Tail", "เปลวไฟหางที่สิบ", True),
    "core_logos": ("Seal of Alpha and Omega", "ตราประทับอัลฟาและโอเมกา", True),
    "codex": ("Codex of Legends", "คัมภีร์แห่งตำนาน", False),
}

# particle colour presets are chosen by scripts; particle shapes are fixed here
PARTICLES = {
    # id: (cell, material, facing, behaviour)
    "tele_ring": ("ring", "particles_blend", "emitter_transform_xz", "decal_pulse"),
    "tele_fill": ("disc", "particles_blend", "emitter_transform_xz", "decal_grow"),
    "tele_dot": ("disc", "particles_blend", "emitter_transform_xz", "decal_dot"),
    "shock": ("ring", "particles_add", "emitter_transform_xz", "decal_expand"),
    "pillar": ("dot", "particles_add", "lookat_y", "pillar"),
    "bullet": ("star", "particles_add", "rotate_xyz", "bullet"),
    "burst": ("dot", "particles_add", "rotate_xyz", "burst"),
    "mote": ("dot", "particles_add", "rotate_xyz", "mote"),
    "glint": ("glint", "particles_add", "rotate_xyz", "flash"),
    "smoke": ("cloud", "particles_blend", "rotate_xyz", "smoke"),
    "feather": ("feather", "particles_blend", "rotate_xyz", "fall"),
    "petal": ("petal", "particles_blend", "rotate_xyz", "fall"),
    "flame": ("flame", "particles_add", "rotate_xyz", "rise"),
    "rune": ("rune", "particles_add", "rotate_xyz", "rise_slow"),
    "drip": ("drop", "particles_blend", "rotate_xyz", "drip"),
    "shard": ("shard", "particles_blend", "rotate_xyz", "debris"),
    "spiral": ("spiral", "particles_add", "emitter_transform_xz", "decal_spin"),
}
PARTICLE_VARS = {"variable.size", "variable.life", "variable.color.r", "variable.color.g", "variable.color.b",
                 "variable.color.a", "variable.count", "variable.speed", "variable.radius", "variable.height",
                 "variable.dir.speed", "variable.dir.direction_x", "variable.dir.direction_y", "variable.dir.direction_z"}


# --------------------------------------------------------------------------- io

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# --------------------------------------------------------------------------- manifests

def manifests():
    meta = {"authors": ["Legendary & Divine Beings"], "product_type": "addon"}
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
            {"module_name": "@minecraft/server-ui", "version": SERVER_UI_VERSION},
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
    ic = icons.pack_icon()
    for p in (BP, RP):
        ic.save(os.path.join(p, "pack_icon.png"))


# --------------------------------------------------------------------------- creatures (RP)

def illusion_texture(img):
    """Ghostly foxfire copy of a texture: cyan-lavender tint with dithered cut-outs (glow texels kept)."""
    out = img.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            lum = (r * 0.3 + g * 0.59 + b * 0.11) / 255
            nr, ng, nb = int(120 + lum * 110), int(170 + lum * 80), int(230 + lum * 25)
            if a > 100 and (x + y) % 3 == 0 and (x * 7 + y * 3) % 5 == 0:
                px[x, y] = (0, 0, 0, 0)
            else:
                px[x, y] = (min(255, nr), min(255, ng), min(255, nb), a)
    return out


def creature_rp(key: str, c: Creature, extra_textures=None):
    m = c.model
    bw, bh, oy = m.bounds
    m.bounds = (bw * c.scale, bh * c.scale, oy * c.scale)
    tex_dir = os.path.join(RP, "textures", "entity", "legends")
    os.makedirs(tex_dir, exist_ok=True)
    m.paint()
    tex_names = []
    for v in range(c.variants):
        img = m.paint(variant=v) if v else m.texture
        name = key if v == 0 else f"{key}_v{v}"
        img.save(os.path.join(tex_dir, f"{name}.png"))
        tex_names.append(name)
    write_json(os.path.join(RP, "models", "entity", "legends", f"{key}.geo.json"), m.geometry_json())

    # animations
    anims = {}
    short = {}
    for s, a, w in c.loops:
        full = f"animation.legends.{key}.{s}"
        anims[full] = a.json()
        short[s] = full
    for act in c.acts:
        full = f"animation.legends.{key}.act.{act.name}"
        anims[full] = act.anim.json()
        short[f"a_{act.name}"] = full
    write_json(os.path.join(RP, "animations", "legends", f"{key}.animation.json"),
               {"format_version": "1.8.0", "animations": anims})
    animate = []
    for s, a, w in c.loops:
        animate.append({s: w} if w else s)
    if c.acts:
        ctrl = f"controller.animation.legends.{key}.act"
        states = {"default": {"transitions": [{act.name: f"variable.act == {act.id}"} for act in c.acts]}}
        for act in c.acts:
            states[act.name] = {"animations": [f"a_{act.name}"], "blend_transition": 0.12,
                                "transitions": [{"default": f"variable.act != {act.id}"}]}
        write_json(os.path.join(RP, "animation_controllers", "legends", f"{key}.ac.json"),
                   {"format_version": "1.10.0", "animation_controllers": {ctrl: {"initial_state": "default", "states": states}}})
        short["ctrl_act"] = ctrl
        animate.append("ctrl_act")

    # render controller
    rc_name = f"controller.render.legends.{key}"
    rc = {"geometry": "Geometry.default",
          "materials": [{"*": "Material.default"}, {"glow_*": "Material.glow"}]}
    tex_keys = ["default"] + [f"v{i}" for i in range(1, c.variants)]
    if c.variants > 1:
        rc["arrays"] = {"textures": {"Array.skins": [f"Texture.{t}" for t in tex_keys]}}
        rc["textures"] = [f"Array.skins[{c.variant_expr}]"]
    else:
        rc["textures"] = ["Texture.default"]
    if c.visibility:
        pv = [{"*": True}]
        for bone, expr in c.visibility:
            pv.append({bone: expr})
        rc["part_visibility"] = pv
    if any("variable.ova" in s for s in c.pre):
        rc["overlay_color"] = {"r": "variable.ovr", "g": "variable.ovg", "b": "variable.ovb", "a": "variable.ova"}
    write_json(os.path.join(RP, "render_controllers", "legends", f"{key}.rc.json"),
               {"format_version": "1.8.0", "render_controllers": {rc_name: rc}})

    def client(identifier, textures, rc_names):
        desc = {
            "identifier": identifier,
            "materials": {"default": "entity_alphatest", "glow": "entity_emissive_alpha"},
            "textures": textures,
            "geometry": {"default": m.identifier},
            "animations": short,
            "scripts": {"scale": str(c.scale), "animate": animate},
            "render_controllers": rc_names,
        }
        if c.pre:
            desc["scripts"]["pre_animation"] = [s.rstrip(";") + ";" for s in c.pre]
        return {"format_version": "1.10.0", "minecraft:client_entity": {"description": desc}}

    textures = {k: f"textures/entity/legends/{n}" for k, n in zip(tex_keys, tex_names)}
    write_json(os.path.join(RP, "entity", "legends", f"{key}.entity.json"), client(f"legends:{key}", textures, [rc_name]))
    for ident, tex in (extra_textures or {}).items():
        # alternate skins sharing geometry + animations (e.g. foxfire illusions)
        tex.save(os.path.join(tex_dir, f"{ident}.png"))
        rc2 = dict(rc)
        rc2.pop("arrays", None)
        rc2["textures"] = ["Texture.default"]
        rc2_name = f"controller.render.legends.{ident}"
        write_json(os.path.join(RP, "render_controllers", "legends", f"{ident}.rc.json"),
                   {"format_version": "1.8.0", "render_controllers": {rc2_name: rc2}})
        write_json(os.path.join(RP, "entity", "legends", f"{ident}.entity.json"),
                   client(f"legends:{ident}", {"default": f"textures/entity/legends/{ident}"}, [rc2_name]))
    return {"acts": {a.name: a for a in c.acts}}


# --------------------------------------------------------------------------- server entities (BP)

def creature_props(full=True):
    if not full:
        return {"legends:act": {"type": "int", "range": [0, 4], "default": 0, "client_sync": True}}
    return {
        "legends:act": {"type": "int", "range": [0, 40], "default": 0, "client_sync": True},
        "legends:phase": {"type": "int", "range": [0, 5], "default": 0, "client_sync": True},
        "legends:var": {"type": "int", "range": [0, 15], "default": 0, "client_sync": True},
        "legends:fly": {"type": "int", "range": [0, 1], "default": 0, "client_sync": True},
        "legends:fx": {"type": "int", "range": [0, 7], "default": 0, "client_sync": True},
        "legends:move": {"type": "float", "range": [0.0, 1.0], "default": 0.0, "client_sync": True},
    }


IMMUNE = ["fall", "fire", "fire_tick", "lava", "drowning", "suffocation", "freezing", "magma", "contact",
          "fly_into_wall", "falling_block", "stalactite", "stalagmite", "campfire", "soul_campfire", "temperature"]


def damage_sensor(kind):
    trig = [{"cause": c, "deals_damage": "no"} for c in IMMUNE]
    if kind in ("boss", "choir"):
        trig += [
            {"cause": "entity_explosion", "deals_damage": "yes", "damage_multiplier": 0.35},
            {"cause": "block_explosion", "deals_damage": "yes", "damage_multiplier": 0.35},
            {"cause": "projectile", "deals_damage": "yes", "damage_multiplier": 0.6},
            {"cause": "magic", "deals_damage": "yes", "damage_multiplier": 0.5},
            {"cause": "wither", "deals_damage": "no"},
            {"cause": "lightning", "deals_damage": "yes", "damage_multiplier": 0.5},
        ]
    return {"triggers": trig}


def entity_bp(ident, families, comps, groups=None, events=None, props=None):
    groups = dict(groups or {})
    groups["legends:despawn"] = {"minecraft:instant_despawn": {}}
    ev = dict(events or {})
    ev["legends:despawn"] = {"add": {"component_groups": ["legends:despawn"]}}
    base = {
        "minecraft:type_family": {"family": families},
        "minecraft:physics": {"has_gravity": False, "has_collision": False},
        "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
        "minecraft:knockback_resistance": {"value": 1.0},
        "minecraft:fire_immune": {},
        "minecraft:conditional_bandwidth_optimization": {
            "default_values": {"max_optimized_distance": 0.0, "max_dropped_ticks": 0, "use_motion_prediction_hints": True}},
    }
    base.update(comps)
    desc = {"identifier": ident, "is_spawnable": False, "is_summonable": True}
    if props:
        desc["properties"] = props
    return {"format_version": "1.21.0",
            "minecraft:entity": {"description": desc, "component_groups": groups, "components": base, "events": ev}}


def box(w, h):
    return {"minecraft:collision_box": {"width": w, "height": h},
            "minecraft:custom_hit_test": {"hitboxes": [{"pivot": [0, round(h / 2, 3), 0], "width": w, "height": h}]}}


def build_bp_entities():
    d = os.path.join(BP, "entities", "legends")
    for key, st in BOSSES.items():
        comps = {
            "minecraft:health": {"value": st["hp"], "max": st["hp"]},
            "minecraft:boss": {"hud_range": 72, "should_darken_sky": st["darken"]},
            "minecraft:collision_box": {"width": st["col"][0], "height": st["col"][1]},
            "minecraft:custom_hit_test": {"hitboxes": [{"pivot": [0, round(st["hit"][1] / 2, 3), 0],
                                                        "width": st["hit"][0], "height": st["hit"][1]}]},
            "minecraft:damage_sensor": damage_sensor("boss"),
            "minecraft:persistent": {},
            "minecraft:body_rotation_always_follows_head": {},
            "minecraft:loot": {"table": f"loot_tables/entities/legends/{key}.json"},
            "minecraft:experience_reward": {"on_death": f"query.last_hit_by_player ? {st['xp']} : 0"},
            "minecraft:mob_effect_immunity": {"mob_effects": ["poison", "wither", "slowness", "weakness", "levitation",
                                                              "instant_damage", "fatal_poison", "nausea", "blindness"]},
        }
        groups, events = {}, {}
        for gname, f in st.get("forms", {}).items():
            groups[gname] = box(*f["col"])
            events[gname] = {"add": {"component_groups": [gname]},
                             "remove": {"component_groups": [g for g in st["forms"] if g != gname]}}
        if st.get("forms"):
            events["legends:form_base"] = {"remove": {"component_groups": list(st["forms"])},
                                           "add": {"component_groups": ["legends:form_reset"]}}
            groups["legends:form_reset"] = box(*st["col"])
        write_json(os.path.join(d, f"{key}.json"), entity_bp(
            f"legends:{key}", ["legends", "legends_boss", key, "monster", "mob"], comps, groups, events, creature_props()))
    for key, st in CHOIR.items():
        comps = {"minecraft:health": {"value": st["hp"], "max": st["hp"]}, **box(*st["col"]),
                 "minecraft:damage_sensor": damage_sensor("choir"), "minecraft:persistent": {},
                 "minecraft:body_rotation_always_follows_head": {},
                 "minecraft:experience_reward": {"on_death": "query.last_hit_by_player ? 60 : 0"}}
        write_json(os.path.join(d, f"{key}.json"), entity_bp(
            f"legends:{key}", ["legends", "legends_choir", key, "monster", "mob"], comps, props=creature_props()))
    for key, st in ILLUSIONS.items():
        comps = {"minecraft:health": {"value": st["hp"], "max": st["hp"]}, **box(*st["col"]),
                 "minecraft:damage_sensor": damage_sensor("prop"),
                 "minecraft:body_rotation_always_follows_head": {},
                 "minecraft:timer": {"looping": False, "time": 40, "randomInterval": False,
                                     "time_down_event": {"event": "legends:despawn", "target": "self"}}}
        write_json(os.path.join(d, f"{key}.json"), entity_bp(
            f"legends:{key}", ["legends", "legends_illusion", "monster", "mob"], comps, props=creature_props()))
    for key, st in PROPS.items():
        hp = st["hp"]
        comps = {"minecraft:health": {"value": max(1, hp), "max": max(1, hp)}, **box(*st["col"]),
                 "minecraft:timer": {"looping": False, "time": st["life"], "randomInterval": False,
                                     "time_down_event": {"event": "legends:despawn", "target": "self"}}}
        if hp <= 0:
            comps["minecraft:damage_sensor"] = {"triggers": [{"cause": "all", "deals_damage": "no"}]}
            fam = ["legends", "legends_prop", "inanimate"]
        else:
            comps["minecraft:damage_sensor"] = damage_sensor("prop")
            fam = ["legends", "legends_prop", "legends_breakable"]
        write_json(os.path.join(d, f"{key}.json"), entity_bp(f"legends:{key}", fam, comps,
                                                              props=creature_props(full=False)))


# --------------------------------------------------------------------------- items, recipes, loot

def build_items():
    data = {}
    tdir = os.path.join(RP, "textures", "items", "legends")
    os.makedirs(tdir, exist_ok=True)
    for key, (en, th, glint) in ITEMS.items():
        icons.icon_image(key).save(os.path.join(tdir, f"{key}.png"))
        data[f"legends_{key}"] = {"textures": f"textures/items/legends/{key}"}
        item = {
            "format_version": "1.21.60",
            "minecraft:item": {
                "description": {"identifier": f"legends:{key}", "menu_category": {"category": "items"}},
                "components": {
                    "minecraft:icon": {"textures": {"default": f"legends_{key}"}},
                    "minecraft:display_name": {"value": f"item.legends:{key}.name"},
                    "minecraft:max_stack_size": 1 if key.startswith(("sigil", "codex")) else 16,
                    "minecraft:glint": glint,
                    "minecraft:tags": {"tags": ["legends:sigil"] if key.startswith("sigil") else
                                       (["legends:codex"] if key == "codex" else ["legends:core"])},
                },
            },
        }
        write_json(os.path.join(BP, "items", "legends", f"{key}.json"), item)
    write_json(os.path.join(RP, "textures", "item_texture.json"),
               {"resource_pack_name": "legends", "texture_name": "atlas.items", "texture_data": data})


RECIPES = {
    "sigil_taotie": (["CGC", "FSF", "CBC"], {"C": "minecraft:copper_block", "G": "minecraft:gold_block",
                                              "F": "minecraft:cake", "S": "minecraft:nether_star",
                                              "B": "minecraft:golden_carrot"}),
    "sigil_nidhogg": (["ERE", "RSR", "EDE"], {"E": "minecraft:echo_shard", "R": "minecraft:mangrove_roots",
                                               "S": "minecraft:nether_star", "D": "minecraft:dragon_breath"}),
    "sigil_hanuman": (["DDD", "GSG", " B "], {"D": "minecraft:diamond", "G": "minecraft:gold_block",
                                               "S": "minecraft:nether_star", "B": "minecraft:breeze_rod"}),
    "sigil_alicorn": (["  A", "MSF", "GM "], {"A": "minecraft:amethyst_shard", "M": "minecraft:phantom_membrane",
                                               "S": "minecraft:nether_star", "F": "minecraft:feather",
                                               "G": "minecraft:glowstone"}),
    "sigil_tenko": (["BEB", "LSL", "BPB"], {"B": "minecraft:blaze_powder", "E": "minecraft:ender_eye",
                                             "L": "minecraft:soul_lantern", "S": "minecraft:nether_star",
                                             "P": "minecraft:glow_berries"}),
    "sigil_logos": (["TNH", "ASF", "KBK"], {"T": "legends:core_taotie", "N": "legends:core_nidhogg",
                                             "H": "legends:core_hanuman", "A": "legends:core_alicorn",
                                             "F": "legends:core_tenko", "S": "minecraft:nether_star",
                                             "B": "minecraft:book", "K": "minecraft:gold_block"}),
}


def build_recipes():
    for key, (pattern, keys) in RECIPES.items():
        write_json(os.path.join(BP, "recipes", f"{key}.json"), {
            "format_version": "1.20.10",
            "minecraft:recipe_shaped": {
                "description": {"identifier": f"legends:{key}"},
                "tags": ["crafting_table"],
                "pattern": pattern,
                "key": {k: {"item": v} for k, v in keys.items()},
                "result": {"item": f"legends:{key}"},
                "unlock": [{"item": "minecraft:nether_star"}],
            }})
    write_json(os.path.join(BP, "recipes", "codex.json"), {
        "format_version": "1.20.10",
        "minecraft:recipe_shapeless": {
            "description": {"identifier": "legends:codex"},
            "tags": ["crafting_table"],
            "ingredients": [{"item": "minecraft:book"}, {"item": "minecraft:amethyst_shard"}],
            "result": {"item": "legends:codex"},
            "unlock": [{"item": "minecraft:book"}],
        }})


LOOT = {
    "taotie": [("minecraft:gold_block", 2, 5), ("minecraft:copper_block", 4, 10), ("minecraft:enchanted_golden_apple", 1, 2)],
    "nidhogg": [("minecraft:netherite_scrap", 2, 4), ("minecraft:echo_shard", 3, 6), ("minecraft:dragon_breath", 2, 5)],
    "hanuman": [("minecraft:diamond", 4, 8), ("minecraft:gold_block", 2, 4), ("minecraft:breeze_rod", 3, 6)],
    "alicorn": [("minecraft:amethyst_block", 4, 8), ("minecraft:phantom_membrane", 3, 6), ("minecraft:experience_bottle", 8, 16)],
    "tenko": [("minecraft:glow_berries", 8, 16), ("minecraft:ender_pearl", 4, 8), ("minecraft:netherite_scrap", 1, 3)],
    "logos": [("minecraft:netherite_ingot", 2, 4), ("minecraft:enchanted_golden_apple", 2, 3), ("minecraft:nether_star", 1, 2)],
}


def build_loot():
    for key, extra in LOOT.items():
        pools = [{"rolls": 1, "entries": [{"type": "item", "name": f"legends:core_{key}", "weight": 1}]},
                 {"rolls": len(extra), "entries": [{"type": "item", "name": n, "weight": 1,
                                                    "functions": [{"function": "set_count", "count": {"min": a, "max": b}}]}
                                                   for n, a, b in extra]}]
        write_json(os.path.join(BP, "loot_tables", "entities", "legends", f"{key}.json"), {"pools": pools})


# --------------------------------------------------------------------------- particles

def particle(ident, cell, material, facing, behaviour):
    uv = {"texture_width": 128, "texture_height": 128, "uv": icons.particle_uv(cell), "uv_size": [32, 32]}
    col = ["variable.color.r", "variable.color.g", "variable.color.b"]
    age = "variable.particle_age / variable.particle_lifetime"
    comps = {"minecraft:emitter_lifetime_once": {"active_time": 0.05}}
    bill = {"facing_camera_mode": facing, "uv": uv}
    if behaviour.startswith("decal"):
        comps["minecraft:emitter_rate_instant"] = {"num_particles": 1}
        comps["minecraft:emitter_shape_point"] = {}
        comps["minecraft:particle_lifetime_expression"] = {"max_lifetime": "variable.life"}
        comps["minecraft:particle_initial_speed"] = 0
        comps["minecraft:particle_motion_dynamic"] = {}
        if behaviour == "decal_pulse":
            bill["size"] = ["variable.size", "variable.size"]
            alpha = f"(0.55 + math.sin(variable.particle_age * 900) * 0.25) * math.min(1.0, (1.0 - {age}) * 6.0)"
        elif behaviour == "decal_grow":
            bill["size"] = [f"variable.size * {age}", f"variable.size * {age}"]
            alpha = "0.42"
        elif behaviour == "decal_dot":
            bill["size"] = [f"variable.size * (0.4 + {age} * 0.6)", f"variable.size * (0.4 + {age} * 0.6)"]
            alpha = f"0.35 + {age} * 0.45"
        elif behaviour == "decal_spin":
            bill["size"] = ["variable.size", "variable.size"]
            comps["minecraft:particle_initial_spin"] = {"rotation": 0, "rotation_rate": 220}
            alpha = f"0.7 * (1.0 - {age})"
        else:  # expand
            bill["size"] = [f"variable.size * {age}", f"variable.size * {age}"]
            alpha = f"1.0 - {age}"
        comps["minecraft:particle_appearance_tinting"] = {"color": col + [alpha]}
    elif behaviour == "pillar":
        comps["minecraft:emitter_rate_instant"] = {"num_particles": 1}
        comps["minecraft:emitter_shape_point"] = {"offset": [0, "variable.height * 0.5", 0]}
        comps["minecraft:particle_lifetime_expression"] = {"max_lifetime": "variable.life"}
        comps["minecraft:particle_initial_speed"] = 0
        comps["minecraft:particle_motion_dynamic"] = {}
        bill["size"] = [f"variable.size * (1.0 - {age} * 0.6)", "variable.height * 0.5"]
        comps["minecraft:particle_appearance_tinting"] = {"color": col + [f"1.0 - {age}"]}
    elif behaviour == "bullet":
        comps["minecraft:emitter_rate_instant"] = {"num_particles": 1}
        comps["minecraft:emitter_shape_point"] = {"direction": ["variable.dir.direction_x", "variable.dir.direction_y",
                                                                "variable.dir.direction_z"]}
        comps["minecraft:particle_lifetime_expression"] = {"max_lifetime": "variable.life"}
        comps["minecraft:particle_initial_speed"] = "variable.dir.speed"
        comps["minecraft:particle_motion_dynamic"] = {}
        bill["size"] = ["variable.size", "variable.size"]
        comps["minecraft:particle_appearance_tinting"] = {"color": col + ["1.0"]}
    else:
        comps["minecraft:emitter_rate_instant"] = {"num_particles": "math.max(1, variable.count)"}
        comps["minecraft:emitter_shape_sphere"] = {"radius": "variable.radius", "surface_only": False,
                                                   "direction": "outwards"}
        life = {"burst": "0.45 + variable.particle_random_1 * 0.4", "mote": "variable.life",
                "flash": "0.18", "smoke": "0.9 + variable.particle_random_1 * 0.8",
                "fall": "1.6 + variable.particle_random_1 * 1.2", "rise": "0.6 + variable.particle_random_1 * 0.5",
                "rise_slow": "1.2 + variable.particle_random_1 * 0.8", "drip": "0.9 + variable.particle_random_1 * 0.5",
                "debris": "0.8 + variable.particle_random_1 * 0.6"}[behaviour]
        comps["minecraft:particle_lifetime_expression"] = {"max_lifetime": life}
        speed = {"burst": "variable.speed", "mote": "variable.speed", "flash": "0", "smoke": "variable.speed",
                 "fall": "variable.speed", "rise": "variable.speed", "rise_slow": "variable.speed",
                 "drip": "variable.speed", "debris": "variable.speed"}[behaviour]
        comps["minecraft:particle_initial_speed"] = speed
        acc = {"burst": [0, 0, 0], "mote": [0, 0.3, 0], "flash": [0, 0, 0], "smoke": [0, 1.2, 0], "fall": [0, -1.2, 0],
               "rise": [0, 3.0, 0], "rise_slow": [0, 0.8, 0], "drip": [0, -12, 0], "debris": [0, -16, 0]}[behaviour]
        drag = {"burst": 3.0, "mote": 1.0, "flash": 0, "smoke": 1.5, "fall": 2.0, "rise": 2.0, "rise_slow": 1.0,
                "drip": 0.4, "debris": 0.6}[behaviour]
        comps["minecraft:particle_motion_dynamic"] = {"linear_acceleration": acc, "linear_drag_coefficient": drag}
        if behaviour in ("fall", "debris", "smoke"):
            comps["minecraft:particle_initial_spin"] = {"rotation": "variable.particle_random_2 * 360",
                                                        "rotation_rate": "(variable.particle_random_3 - 0.5) * 360"}
        shrink = "1.0" if behaviour in ("fall", "smoke") else f"(1.0 - {age} * 0.7)"
        if behaviour == "flash":
            shrink = f"(1.0 + {age} * 0.6)"
        bill["size"] = [f"variable.size * {shrink}", f"variable.size * {shrink}"]
        alpha = "1.0" if behaviour in ("fall",) else f"1.0 - {age} * {0.6 if behaviour == 'smoke' else 0.9}"
        comps["minecraft:particle_appearance_tinting"] = {"color": col + [alpha]}
    comps["minecraft:particle_appearance_billboard"] = bill
    return {"format_version": "1.10.0",
            "particle_effect": {"description": {"identifier": ident,
                                                "basic_render_parameters": {"material": material,
                                                                            "texture": "textures/particle/legends_fx"}},
                                "components": comps}}


def build_particles():
    p = os.path.join(RP, "textures", "particle", "legends_fx.png")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    icons.particle_atlas().save(p)
    for name, (cell, mat, facing, beh) in PARTICLES.items():
        write_json(os.path.join(RP, "particles", "legends", f"{name}.json"), particle(f"legends:{name}", cell, mat, facing, beh))


# --------------------------------------------------------------------------- language

def build_lang():
    en = [f"pack.name={ADDON_NAME}",
          "pack.description=Six god-tier extra bosses: Taotie, Nidhogg, Hanuman, Alicorn, the Ten-Tailed Fox and The Word of God."]
    th = [f"pack.name={ADDON_NAME}",
          "pack.description=บอสพิเศษระดับเทพหกตน: เทาเที่ย นิดฮ็อกก์ หนุมาน อลิคอร์น จิ้งจอกสิบหาง และพระวัจนะแห่งพระเจ้า"]
    for key, (n, t, _) in ITEMS.items():
        en.append(f"item.legends:{key}.name={n}")
        th.append(f"item.legends:{key}.name={t}")
    for group in (BOSSES, CHOIR, ILLUSIONS, PROPS):
        for key, st in group.items():
            en.append(f"entity.legends:{key}.name={st['name']}")
            th.append(f"entity.legends:{key}.name={st['name']}")
    write_text(os.path.join(RP, "texts", "en_US.lang"), "\n".join(en) + "\n")
    write_text(os.path.join(RP, "texts", "languages.json"), json.dumps(["en_US"], indent=2) + "\n")
    write_text(os.path.join(BP, "texts", "en_US.lang"), "\n".join(en[:2]) + "\n")
    write_text(os.path.join(BP, "texts", "languages.json"), json.dumps(["en_US"], indent=2) + "\n")
    write_text(os.path.join(ROOT, "docs", "th_TH.reference.lang"), "\n".join(th) + "\n")


# --------------------------------------------------------------------------- generated TS

def write_generated(acts_by_key):
    lines = ["// AUTO-GENERATED by tools/build.py — do not edit.",
             "// Act ids / lengths / impact marks (ticks) shared with the resource pack animations.",
             "", "export interface ActInfo { readonly id: number; readonly ticks: number; readonly marks: readonly number[] }", ""]
    for key, acts in acts_by_key.items():
        body = ", ".join(f"{name}: {{ id: {a.id}, ticks: {round(a.length * 20)}, marks: [{', '.join(str(round(mk * 20)) for mk in a.marks)}] }}"
                         for name, a in acts.items())
        lines.append(f"export const {key.upper()}_ACTS = {{ {body} }} as const;")
    lines.append("")
    stats = {k: {"hp": v["hp"], "name": v["name"]} for k, v in BOSSES.items()}
    lines.append(f"export const BOSS_STATS = {json.dumps(stats)} as const;")
    choir = {k: {"hp": v["hp"], "name": v["name"]} for k, v in CHOIR.items()}
    lines.append(f"export const CHOIR_STATS = {json.dumps(choir)} as const;")
    lines.append(f"export const PROP_IDS = {json.dumps(['legends:' + k for k in PROPS])} as const;")
    lines.append(f"export const ITEM_IDS = {json.dumps(['legends:' + k for k in ITEMS])} as const;")
    write_text(GEN_TS, "\n".join(lines) + "\n")


# --------------------------------------------------------------------------- scripts + packaging

def build_scripts():
    tsc = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        raise SystemExit("TypeScript not installed: run `npm install` in legends-addon/")
    res = subprocess.run([tsc, "-p", os.path.join(ROOT, "tsconfig.json"), "--outDir", os.path.join(BP, "scripts")],
                         capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout, res.stderr)
        raise SystemExit("TypeScript compilation failed")


def zip_dir(zf, folder, arc_root):
    for dirpath, _, files in os.walk(folder):
        for fn in sorted(files):
            full = os.path.join(dirpath, fn)
            zf.write(full, os.path.join(arc_root, os.path.relpath(full, folder)))


def package():
    os.makedirs(DIST, exist_ok=True)
    addon = os.path.join(DIST, f"{DIST_BASE}.mcaddon")
    with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as zf:
        zip_dir(zf, BP, "Legends_BP")
        zip_dir(zf, RP, "Legends_RP")
    for folder, suffix in ((BP, "BP"), (RP, "RP")):
        with zipfile.ZipFile(os.path.join(DIST, f"{DIST_BASE}_{suffix}.mcpack"), "w", zipfile.ZIP_DEFLATED) as zf:
            zip_dir(zf, folder, "")
    return addon


def build_creatures():
    acts = {}
    for key, fn in registry.ALL.items():
        c = fn()
        extra = None
        if key == "tenko":
            c.model.paint()
            extra = {"tenko_illusion": illusion_texture(c.model.texture)}
        info = creature_rp(key, c, extra)
        if key in BOSSES or key in CHOIR:
            acts[key] = info["acts"]
    return acts


def main(skip_scripts=False):
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    manifests()
    acts = build_creatures()
    write_generated(acts)
    build_bp_entities()
    build_items()
    build_recipes()
    build_loot()
    build_particles()
    build_lang()
    if skip_scripts:
        return
    build_scripts()
    addon = package()
    print("built", os.path.relpath(addon, ROOT))


if __name__ == "__main__":
    main(skip_scripts="--no-scripts" in sys.argv)
