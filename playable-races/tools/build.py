"""Build the Playable Races add-on (behavior pack + resource pack + packages).

    python3 tools/build.py            # generate packs/, compile scripts, package dist/
    python3 tools/build.py --no-tsc   # skip TypeScript compilation

Everything in packs/ is generated from tools/ (models, textures, animations,
attachables, particles, items, entities, manifests) and src/ (scripts).
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

from kit.tex import paint  # noqa: E402
from kit.render import render  # noqa: E402
from anims import core as acore  # noqa: E402
from anims import races as aset  # noqa: E402
from models import salamander, golem, jackalope, common  # noqa: E402
import fx  # noqa: E402

NS = "plrace"
VERSION = [1, 0, 1]
MIN_ENGINE = [1, 26, 60]
SERVER_API = "2.11.0"
UI_API = "2.3.0"
BP_NAME, RP_NAME = "PlayableRaces_BP", "PlayableRaces_RP"
# permanent identifiers (never change: existing worlds depend on them)
UUID = {
    "bp": "6a3f2c1e-8d4b-4f7a-9c2e-1b5d7e9f0a21",
    "bp_data": "7b4e3d2f-9e5c-4a8b-8d3f-2c6e8f0a1b32",
    "bp_script": "8c5f4e3a-af6d-4b9c-9e4a-3d7f9a1b2c43",
    "rp": "9d6a5f4b-b07e-4cad-8f5b-4e8a0b2c3d54",
    "rp_res": "ae7b6a5c-c18f-4dbe-9a6c-5f9b1c3d4e65",
}
PACKS = os.path.join(ROOT, "packs")
BP = os.path.join(PACKS, BP_NAME)
RP = os.path.join(PACKS, RP_NAME)
DIST = os.path.join(ROOT, "dist")
TEXROOT = "textures/plrace/races"

RACES = {
    "salamander": {"code": "001", "mod": salamander, "bounds": (3.2, 3.2, (0, 1.2, 0.4)), "fx_bones": None},
    "golem": {"code": "002", "mod": golem, "bounds": (4.6, 4.2, (0, 1.6, 0)), "fx_bones": None},
    "jackalope": {"code": "003", "mod": jackalope, "bounds": (3.0, 3.2, (0, 1.2, 0)), "fx_bones": None},
}
DISPLAY = {"salamander": "Aberrant Flora Salamander", "golem": "Runic Titan Golem", "jackalope": "Blood Moon Jackalope"}
VARIANT_NAMES = {
    "salamander": {"base": "Stable", "bloom": "Blooming", "dormant": "Dormant", "predatory": "Predatory", "rooted": "Rooted"},
    "golem": {"base": "Aligned", "siege": "Siege Configuration", "bastion": "Bastion Configuration",
              "arcane": "Arcane Configuration", "scattered": "Reassembling", "disrupted": "Disrupted"},
    "jackalope": {"base": "Ordinary Lunar", "hunt": "Hunting", "awakened": "Blood Moon Awakened",
                  "awakened_hunt": "Blood Moon Hunt"},
}
ARMOR_TINT = [  # (item-name fragment, rgb) for armour assimilation accents
    ("leather", (0.62, 0.42, 0.26)), ("chainmail", (0.62, 0.64, 0.68)), ("golden", (1.0, 0.82, 0.30)),
    ("diamond", (0.36, 0.90, 0.86)), ("netherite", (0.30, 0.26, 0.29)), ("copper", (0.86, 0.52, 0.34)),
    ("turtle", (0.38, 0.66, 0.32)), ("iron", (0.86, 0.86, 0.88)),
]


def wjson(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")


def item_id(race, variant):
    return f"{NS}:form_{race}" if variant == "base" else f"{NS}:form_{race}_{variant}"


# ============================================================================= models & attachables

def build_races(report):
    lang = []
    geo_index = {}
    for race, info in RACES.items():
        mod = info["mod"]
        model = mod.build()
        info["model"] = model
        mats = mod.materials()
        # textures
        texpaths = {}
        for tv, params in mod.TEXTURES.items():
            img = paint(model, mats, params)
            rel = f"{TEXROOT}/{race}/{race}_{tv}"
            os.makedirs(os.path.dirname(os.path.join(RP, rel)), exist_ok=True)
            img.save(os.path.join(RP, rel + ".png"))
            texpaths[tv] = rel
            info.setdefault("tex_img", {})[tv] = img
        # geometry per variant: solid / cutout / accent passes
        geos = []
        for v in mod.VARIANTS:
            gid = f"geometry.{NS}.{race}.{v}"
            geos.append(model.geometry_json(gid, variant=v, cutout=False, bounds=info["bounds"]))
            if model.has_layer(v, cutout=True):
                geos.append(model.geometry_json(gid + ".cutout", variant=v, cutout=True, bounds=info["bounds"]))
            if model.has_layer(v, accent=True):
                geos.append(model.geometry_json(gid + ".accent", variant=v, cutout=False, accent=True, bounds=info["bounds"]))
        wjson(os.path.join(RP, f"models/entity/plrace/{race}.geo.json"), {"format_version": "1.16.0", "minecraft:geometry": geos})
        geo_index[race] = [g["description"]["identifier"] for g in geos]
        nb, nc = model.stats("base")
        report.append(f"{race}: atlas {model.tex_w}x{model.tex_h}, base form {nb} bones / {nc} cubes, "
                      f"{len(mod.VARIANTS)} variants, {len(mod.TEXTURES)} texture sets")
        # animations
        if race == "salamander":
            A = aset.salamander(model)
        elif race == "golem":
            A = aset.golem(model, list(golem.MOVABLE))
        else:
            A = aset.jackalope(model)
        wjson(os.path.join(RP, f"animations/plrace/{race}.animation.json"), acore.file(A["anims"]))
        if A["controllers"]:
            wjson(os.path.join(RP, f"animation_controllers/plrace/{race}.ac.json"), acore.controller_file(A["controllers"]))
        short = {a.name.split(f"animation.{NS}.{race}.")[1]: a.name for a in A["anims"]}
        for cid in A["controllers"]:
            short[cid.split(".")[-1]] = cid
        # attachables (one per form item)
        for v in mod.VARIANTS:
            iid = item_id(race, v)
            gid = f"geometry.{NS}.{race}.{v}"
            geometry = {"default": gid}
            rcs = [f"controller.render.{NS}.form"]
            materials = {"default": "entity_emissive_alpha"}
            if model.has_layer(v, cutout=True):
                geometry["cutout"] = gid + ".cutout"
                materials["cutout"] = "entity_alphatest"
                rcs.append(f"controller.render.{NS}.form_cutout")
            if model.has_layer(v, accent=True):
                geometry["accent"] = gid + ".accent"
                materials["accent"] = "entity_alphatest"
                rcs += [f"controller.render.{NS}.{race}_accent_{s}" for s in ("c", "l", "f")]
            animate = []
            used = {}
            for nm, cond in A["animate"][v]:
                if nm not in short:
                    raise KeyError(f"{race}/{v}: animation {nm} missing")
                used[nm] = short[nm]
                animate.append(nm if cond is None else {nm: cond})
            if race == "jackalope":
                used["land"] = short["land"]
            att = {"format_version": "1.10.0", "minecraft:attachable": {"description": {
                "identifier": iid,
                "materials": materials,
                "textures": {"default": texpaths[mod.VARIANT_TEXTURE[v]]},
                "geometry": geometry,
                "animations": used,
                "particle_effects": A["particles"],
                "scripts": {"animate": animate},
                "render_controllers": rcs,
            }}}
            wjson(os.path.join(RP, f"attachables/plrace/form_{race}_{v}.json"), att)
            lang.append((f"item.{iid}", f"{DISPLAY[race]} Form ({VARIANT_NAMES[race][v]})"))
    # player-skeleton pose animations (scripts trigger these with playAnimation)
    wjson(os.path.join(RP, "animations/plrace/poses.animation.json"), acore.file(aset.poses()))
    return lang, geo_index


def render_controllers():
    rc = {
        f"controller.render.{NS}.form": {
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}],
            "textures": ["Texture.default"],
            "is_hurt_color": {"r": 1.0, "g": 0.2, "b": 0.2, "a": 0.45},
            "on_fire_color": {"r": 1.0, "g": 0.55, "b": 0.2, "a": 0.35},
        },
        f"controller.render.{NS}.form_cutout": {
            "geometry": "Geometry.cutout",
            "materials": [{"*": "Material.cutout"}],
            "textures": ["Texture.default"],
            "is_hurt_color": {"r": 1.0, "g": 0.2, "b": 0.2, "a": 0.45},
        },
    }
    # armour assimilation: one pass per armour slot, tinted by the worn armour's material
    for race, info in RACES.items():
        model = info["model"]
        for s, slot in common.ARMOR_SLOTS.items():
            bones = sorted({bn for v in info["mod"].VARIANTS for bn in model.accent_bones(v, f"acc_{s}_")})
            others = sorted({bn for v in info["mod"].VARIANTS for bn in model.accent_bones(v, "acc_")} - set(bones))
            worn = f"query.has_armor_slot({ {'c': 1, 'l': 2, 'f': 3}[s] })"
            vis = [{"*": False}] + [{b: worn} for b in bones] + [{b: False} for b in others]
            rc[f"controller.render.{NS}.{race}_accent_{s}"] = {
                "geometry": "Geometry.accent",
                "materials": [{"*": "Material.accent"}],
                "textures": ["Texture.default"],
                "part_visibility": vis,
                "overlay_color": _tint_expr(slot),
            }
    return {"format_version": "1.10.0", "render_controllers": rc}


def _tint_expr(slot):
    def chan(i):
        expr = str({0: 0.72, 1: 0.74, 2: 0.82}[i])
        for frag, rgb in reversed(ARMOR_TINT):
            names = [f"'minecraft:{frag}_{p}'" for p in ("helmet", "chestplate", "leggings", "boots")]
            expr = f"(query.is_item_name_any('{slot}', 0, {', '.join(names)}) ? {rgb[i]} : {expr})"
        return expr
    return {"r": chan(0), "g": chan(1), "b": chan(2), "a": "0.62"}


def form_hidden_expr():
    """Client-side test 'a race form crest is worn'. Uses explicit item names (always known
    to clients); regenerated automatically when future races add crest items."""
    names = [item_id(r, v) for r, info in RACES.items() for v in info["mod"].VARIANTS]
    return "query.is_item_name_any('slot.armor.head', 0, " + ", ".join(f"'{n}'" for n in names) + ")"


def player_overrides():
    FORM_HIDDEN = form_hidden_expr()
    """Minimal override of two vanilla render controllers.  Everything is the vanilla
    1.26.60 definition; the only addition is '&& !<form worn>' on every part, which
    hides the player's own skin/armour while a race form is manifested."""
    tp_parts = [
        ("*", "true"), ("helmet", "variable.helmet_layer_visible"), ("leftLegging", "variable.leg_layer_visible"),
        ("rightLegging", "variable.leg_layer_visible"), ("leftBoot", "variable.boot_layer_visible"),
        ("rightBoot", "variable.boot_layer_visible"),
        ("leftSock", "variable.boot_layer_visible && variable.leg_layer_visible"),
        ("rightSock", "variable.boot_layer_visible && variable.leg_layer_visible"),
        ("bodyArmor", "variable.chest_layer_visible"), ("leftArmArmor", "variable.chest_layer_visible"),
        ("rightArmArmor", "variable.chest_layer_visible"), ("belt", "variable.chest_layer_visible && variable.leg_layer_visible"),
    ]
    vis = [{p: (f"!{FORM_HIDDEN}" if c == "true" else f"({c}) && !{FORM_HIDDEN}")} for p, c in tp_parts]
    player_rc = {"format_version": "1.8.0", "render_controllers": {
        "controller.render.player.third_person": {
            "geometry": "Geometry.default", "materials": [{"*": "Material.default"}],
            "textures": ["Texture.default"], "part_visibility": vis}}}
    armor_rc = {"format_version": "1.8.0", "render_controllers": {
        "controller.render.armor": {
            "geometry": "Geometry.default",
            "materials": [{"*": "variable.is_enchanted ? Material.enchanted : Material.default"}],
            "textures": ["variable.has_trim ? variable.trim_path : Texture.default", "Texture.enchanted"],
            "part_visibility": [{"*": f"!{FORM_HIDDEN}"}]}}}
    return player_rc, armor_rc


# ============================================================================= items

def items(lang):
    out = {}
    for race, info in RACES.items():
        mod = info["mod"]
        for v in mod.VARIANTS:
            iid = item_id(race, v)
            out[iid] = {"format_version": "1.21.90", "minecraft:item": {
                "description": {"identifier": iid, "menu_category": {"category": "none", "is_hidden_in_commands": True}},
                "components": {
                    "minecraft:icon": f"{NS}:crest_{race}",
                    "minecraft:display_name": {"value": f"item.{iid}"},
                    "minecraft:max_stack_size": 1,
                    "minecraft:wearable": {"slot": "slot.armor.head", "protection": {"salamander": 2, "golem": 3, "jackalope": 1}[race]},
                    "minecraft:enchantable": {"slot": "armor_head", "value": 10},
                    "minecraft:tags": {"tags": [f"{NS}:form", f"{NS}:form_{info['code']}", f"{NS}:form_{race}"]},
                    "minecraft:hover_text_color": {"salamander": "green", "golem": "gold", "jackalope": "red"}[race],
                }}}
    focus = {"salamander": ("Dewheart Focus", "green"), "golem": ("Rune Keystone Focus", "gold"),
             "jackalope": ("Moonbone Focus", "red")}
    for race, (name, col) in focus.items():
        iid = f"{NS}:focus_{race}"
        out[iid] = {"format_version": "1.21.90", "minecraft:item": {
            "description": {"identifier": iid, "menu_category": {"category": "equipment", "is_hidden_in_commands": False}},
            "components": {
                "minecraft:icon": f"{NS}:focus_{race}",
                "minecraft:display_name": {"value": f"item.{iid}"},
                "minecraft:max_stack_size": 1,
                "minecraft:hand_equipped": True,
                "minecraft:glint": False,
                "minecraft:hover_text_color": col,
                "minecraft:use_modifiers": {"use_duration": 1000, "movement_modifier": 1.0},
                "minecraft:tags": {"tags": [f"{NS}:focus"]},
                f"{NS}:focus": {},
            }}}
        lang.append((f"item.{iid}", name))
    out[f"{NS}:codex"] = {"format_version": "1.21.90", "minecraft:item": {
        "description": {"identifier": f"{NS}:codex", "menu_category": {"category": "items"}},
        "components": {
            "minecraft:icon": f"{NS}:codex",
            "minecraft:display_name": {"value": f"item.{NS}:codex"},
            "minecraft:max_stack_size": 64,
            "minecraft:use_modifiers": {"use_duration": 1000, "movement_modifier": 1.0},
            f"{NS}:codex": {},
        }}}
    lang.append((f"item.{NS}:codex", "Lineage Codex"))
    for iid, data in out.items():
        wjson(os.path.join(BP, f"items/plrace/{iid.split(':')[1]}.json"), data)
    recipe = {"format_version": "1.20.10", "minecraft:recipe_shapeless": {
        "description": {"identifier": f"{NS}:codex"}, "tags": ["crafting_table"],
        "ingredients": [{"item": "minecraft:book"}, {"item": "minecraft:lapis_lazuli"}, {"item": "minecraft:bone_meal"}],
        "unlock": [{"item": "minecraft:book"}],
        "result": {"item": f"{NS}:codex"}}}
    wjson(os.path.join(BP, "recipes/plrace/codex.json"), recipe)


# ============================================================================= mirage entity

def mirage_entity(lang):
    ident = f"{NS}:velvet_mirage"
    bp = {"format_version": "1.21.90", "minecraft:entity": {
        "description": {"identifier": ident, "is_spawnable": False, "is_summonable": True},
        "component_groups": {f"{NS}:expire": {"minecraft:instant_despawn": {}}},
        "components": {
            "minecraft:type_family": {"family": [f"{NS}_mirage", "player", "mob"]},
            "minecraft:health": {"value": 1, "max": 1},
            "minecraft:collision_box": {"width": 0.6, "height": 1.7},
            "minecraft:physics": {},
            "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": True},
            "minecraft:movement": {"value": 0.32},
            "minecraft:movement.basic": {},
            "minecraft:jump.static": {},
            "minecraft:navigation.walk": {"can_walk": True, "avoid_water": True},
            "minecraft:knockback_resistance": {"value": 1.0},
            "minecraft:fire_immune": {},
            "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0, "breathes_water": True},
            "minecraft:loot": {"table": "loot_tables/empty.json"},
            "minecraft:experience_reward": {"on_death": "0"},
            "minecraft:conditional_bandwidth_optimization": {},
            "minecraft:timer": {"time": 12, "looping": False, "time_down_event": {"event": f"{NS}:expire"}},
            "minecraft:damage_sensor": {"triggers": [{"cause": "fall", "deals_damage": "no"},
                                                     {"cause": "suffocation", "deals_damage": "no"}]},
        },
        "events": {f"{NS}:expire": {"add": {"component_groups": [f"{NS}:expire"]}}}}}
    wjson(os.path.join(BP, "entities/plrace/velvet_mirage.json"), bp)
    # client: re-uses the jackalope form geometry with a translucent spectral texture
    anim = acore.Anim(f"animation.{NS}.mirage.run")
    sw = "math.cos(q.modified_distance_moved * 38.17) * q.modified_move_speed * 57.3"
    anim.bone("rightLeg", rot=[f"{sw} * 1.2", 0, 0]).bone("leftLeg", rot=[f"-{sw} * 1.2", 0, 0])
    anim.bone("rightArm", rot=[f"-{sw} * 0.8", 0, 0]).bone("leftArm", rot=[f"{sw} * 0.8", 0, 0])
    anim.bone("body", rot=[8, 0, 0], pos=[0, "math.abs(math.sin(q.life_time * 540)) * 0.8", 0])
    anim.bone("r_ear", rot=[-20, 0, aset.osc(1.4, 6)]).bone("l_ear", rot=[-20, 0, aset.osc(1.3, -6, 50)])
    for b in common.FIRST_PERSON_ONLY:
        anim.bone(b, scale=0)
    look = acore.Anim(f"animation.{NS}.mirage.look")
    look.bone("head", rot=["q.target_x_rotation", "q.target_y_rotation", 0])
    wjson(os.path.join(RP, "animations/plrace/mirage.animation.json"), acore.file([anim, look]))
    rp = {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": ident,
        "materials": {"default": "entity_alphablend", "cutout": "entity_alphablend"},
        "textures": {"default": f"{TEXROOT}/jackalope/jackalope_mirage"},
        "geometry": {"default": f"geometry.{NS}.jackalope.base", "cutout": f"geometry.{NS}.jackalope.base.cutout"},
        "animations": {"run": f"animation.{NS}.mirage.run", "look": f"animation.{NS}.mirage.look"},
        "scripts": {"animate": ["run", "look"]},
        "particle_effects": {"shimmer": f"{NS}:velvet_shimmer"},
        "render_controllers": [f"controller.render.{NS}.mirage", f"controller.render.{NS}.mirage_cutout"],
        "enable_attachables": False}}}
    wjson(os.path.join(RP, "entity/plrace/velvet_mirage.entity.json"), rp)
    lang.append((f"entity.{ident}.name", "Velvet Mirage"))
    # spectral texture: the jackalope atlas washed into translucent moonlight-violet
    base = RACES["jackalope"]["tex_img"]["base"].convert("RGBA")
    px = base.load()
    out = Image.new("RGBA", base.size)
    po = out.load()
    for y in range(base.size[1]):
        for x in range(base.size[0]):
            r, g, b, a = px[x, y]
            if a == 0:
                po[x, y] = (0, 0, 0, 0)
                continue
            lum = (r + g + b) / 3
            po[x, y] = (int(150 + lum * 0.5), int(140 + lum * 0.45), int(230 + lum * 0.1), 150)
    out.save(os.path.join(RP, f"{TEXROOT}/jackalope/jackalope_mirage.png"))


def mirage_render_controllers(rc):
    rc["render_controllers"][f"controller.render.{NS}.mirage"] = {
        "geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"],
        "color": {"r": 1.0, "g": 1.0, "b": 1.0, "a": "0.55 + math.sin(q.life_time * 300) * 0.15"}}
    rc["render_controllers"][f"controller.render.{NS}.mirage_cutout"] = {
        "geometry": "Geometry.cutout", "materials": [{"*": "Material.cutout"}], "textures": ["Texture.default"],
        "color": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 0.5}}


# ============================================================================= icons

def _render_icon(race, size, yaw=28, pitch=12, focus="head"):
    info = RACES[race]
    model = info["model"]
    tex = info["tex_img"][{"salamander": "bloom", "golem": "base", "jackalope": "awakened"}[race]]
    v = {"salamander": "bloom", "golem": "base", "jackalope": "awakened"}[race]
    if focus == "head":
        center = {"salamander": (0, 27.5, -2), "golem": (0, 37.5, 0), "jackalope": (0, 28.5, -1)}[race]
        scale = {"salamander": 4.3, "golem": 3.7, "jackalope": 3.4}[race] * size / 32
    else:
        center = {"salamander": (0, 19, 3), "golem": (0, 22, 0), "jackalope": (0, 19, 0)}[race]
        scale = {"salamander": 5.4, "golem": 4.7, "jackalope": 5.8}[race] * size / 128
    img = render(model, tex, variant=v, yaw=yaw, pitch=pitch, size=(size * 2, size * 2), scale=scale,
                 center=center, ss=2, bg=(0, 0, 0), bloom=False, ground=False, hide=["r_arm_fp", "l_arm_fp"])
    return img


def _key_out_black(img):
    img = img.convert("RGBA")
    px = img.load()
    for y in range(img.size[1]):
        for x in range(img.size[0]):
            r, g, b, a = px[x, y]
            if r < 3 and g < 3 and b < 3:
                px[x, y] = (0, 0, 0, 0)
    return img


def icons():
    d = os.path.join(RP, TEXROOT, "items")
    ui = os.path.join(RP, TEXROOT, "ui")
    os.makedirs(d, exist_ok=True)
    os.makedirs(ui, exist_ok=True)
    tex_entries = {}
    for race, info in RACES.items():
        # crest icon: mini head portrait (32px)
        head = _key_out_black(_render_icon(race, 32)).resize((32, 32), Image.LANCZOS)
        head.save(os.path.join(d, f"crest_{race}.png"))
        tex_entries[f"{NS}:crest_{race}"] = {"textures": f"{TEXROOT}/items/crest_{race}"}
        # UI portraits for the lineage selection forms
        por = _render_icon(race, 128, yaw=24, pitch=8, focus="body")
        por = _key_out_black(por).resize((128, 128), Image.LANCZOS)
        bgc = {"salamander": (24, 58, 30), "golem": (52, 40, 18), "jackalope": (46, 14, 26)}[race]
        bg = Image.new("RGBA", (128, 128), bgc + (255,))
        g = Image.new("L", (128, 128), 0)
        ImageDraw.Draw(g).ellipse([8, 8, 120, 120], fill=150)
        bg = Image.composite(Image.new("RGBA", (128, 128), tuple(min(255, c * 2) for c in bgc) + (255,)), bg,
                             g.filter(ImageFilter.GaussianBlur(14)))
        bg.alpha_composite(por)
        bg.save(os.path.join(ui, f"portrait_{info['code']}.png"))
    for race, img in _focus_icons().items():
        img.save(os.path.join(d, f"focus_{race}.png"))
        tex_entries[f"{NS}:focus_{race}"] = {"textures": f"{TEXROOT}/items/focus_{race}"}
    _codex_icon().save(os.path.join(d, "codex.png"))
    tex_entries[f"{NS}:codex"] = {"textures": f"{TEXROOT}/items/codex"}
    wjson(os.path.join(RP, "textures/item_texture.json"),
          {"resource_pack_name": RP_NAME, "texture_name": "atlas.items", "texture_data": tex_entries})


def _pix(size=32):
    S = 8
    img = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), S


def _finish(img, size=32):
    return img.resize((size, size), Image.LANCZOS)


def _focus_icons():
    out = {}
    # Dewheart: a dew-filled seed pod cradled by leaves
    img, d, S = _pix()
    d.polygon([(4 * S, 22 * S), (14 * S, 12 * S), (13 * S, 26 * S)], fill=(52, 140, 48, 255))
    d.polygon([(28 * S, 22 * S), (18 * S, 12 * S), (19 * S, 26 * S)], fill=(70, 170, 60, 255))
    d.ellipse([9 * S, 7 * S, 23 * S, 23 * S], fill=(40, 90, 50, 255))
    d.ellipse([11 * S, 9 * S, 21 * S, 21 * S], fill=(230, 70, 110, 255))
    d.ellipse([13 * S, 10 * S, 17 * S, 14 * S], fill=(255, 220, 235, 255))
    for k in range(7):
        a = k * 2 * math.pi / 7
        x, y = 16 * S + math.cos(a) * 8 * S, 15 * S + math.sin(a) * 8 * S
        d.ellipse([x - S, y - S, x + S, y + S], fill=(200, 30, 60, 255))
    out["salamander"] = _finish(img)
    # Rune Keystone: basalt wedge with a glowing glyph
    img, d, S = _pix()
    d.polygon([(8 * S, 6 * S), (24 * S, 6 * S), (27 * S, 26 * S), (5 * S, 26 * S)], fill=(44, 44, 52, 255))
    d.polygon([(8 * S, 6 * S), (24 * S, 6 * S), (22 * S, 9 * S), (10 * S, 9 * S)], fill=(80, 80, 92, 255))
    w = int(1.6 * S)
    d.line([16 * S, 10 * S, 16 * S, 23 * S], fill=(255, 196, 70, 255), width=w)
    d.line([16 * S, 13 * S, 21 * S, 10 * S], fill=(255, 196, 70, 255), width=w)
    d.line([16 * S, 17 * S, 11 * S, 14 * S], fill=(255, 196, 70, 255), width=w)
    d.line([12 * S, 22 * S, 20 * S, 22 * S], fill=(255, 225, 140, 255), width=w)
    d.rectangle([5 * S, 25 * S, 27 * S, 27 * S], fill=(200, 150, 50, 255))
    out["golem"] = _finish(img)
    # Moonbone: a crescent of black bone with a blood-red gem
    img, d, S = _pix()
    d.ellipse([4 * S, 4 * S, 28 * S, 28 * S], fill=(30, 26, 44, 255))
    d.ellipse([10 * S, 2 * S, 32 * S, 24 * S], fill=(0, 0, 0, 0))
    d.ellipse([6 * S, 6 * S, 26 * S, 26 * S], outline=(200, 205, 225, 255), width=S)
    d.ellipse([9 * S, 17 * S, 15 * S, 23 * S], fill=(210, 20, 40, 255))
    d.ellipse([10 * S, 18 * S, 12 * S, 20 * S], fill=(255, 160, 170, 255))
    out["jackalope"] = _finish(img)
    return out


def _codex_icon():
    img, d, S = _pix()
    d.rectangle([6 * S, 4 * S, 26 * S, 28 * S], fill=(58, 38, 70, 255))
    d.rectangle([8 * S, 5 * S, 26 * S, 27 * S], fill=(232, 222, 196, 255))
    d.rectangle([6 * S, 4 * S, 24 * S, 27 * S], fill=(70, 44, 86, 255))
    d.rectangle([6 * S, 4 * S, 8 * S, 27 * S], fill=(40, 24, 50, 255))
    for k, col in enumerate(((80, 200, 90), (255, 190, 60), (220, 40, 60))):
        a = -math.pi / 2 + k * 2 * math.pi / 3
        x, y = 16 * S + math.cos(a) * 5 * S, 15 * S + math.sin(a) * 5 * S
        d.ellipse([x - 2.6 * S, y - 2.6 * S, x + 2.6 * S, y + 2.6 * S], fill=col + (255,))
    d.ellipse([12.5 * S, 11.5 * S, 19.5 * S, 18.5 * S], outline=(230, 210, 140, 255), width=S)
    return _finish(img)


def pack_icon(path_bp, path_rp):
    imgs = []
    for race in ("salamander", "golem", "jackalope"):
        imgs.append(_key_out_black(_render_icon(race, 128, yaw=26, pitch=6, focus="body")).resize((128, 128), Image.LANCZOS))
    icon = Image.new("RGBA", (256, 256), (20, 16, 30, 255))
    g = Image.new("L", (256, 256), 0)
    ImageDraw.Draw(g).ellipse([30, 10, 226, 206], fill=160)
    icon = Image.composite(Image.new("RGBA", (256, 256), (120, 30, 50, 255)), icon, g.filter(ImageFilter.GaussianBlur(40)))
    ImageDraw.Draw(icon).ellipse([150, 18, 214, 82], fill=(200, 30, 50, 255))
    icon.alpha_composite(imgs[1].resize((150, 150), Image.LANCZOS), (53, 70))
    icon.alpha_composite(imgs[0].resize((120, 120), Image.LANCZOS), (-4, 128))
    icon.alpha_composite(imgs[2].resize((120, 120), Image.LANCZOS), (140, 128))
    icon.save(path_bp)
    icon.save(path_rp)


# ============================================================================= particles, sounds, texts, manifests

def particles():
    fx.atlas().save(_mk(os.path.join(RP, f"{TEXROOT}/particles/particles.png")))
    for name, data in fx.particles().items():
        wjson(os.path.join(RP, f"particles/plrace/{name}.json"), data)
    wjson(os.path.join(RP, "fogs/plrace_blood_moon.json"), fx.fog())


def _mk(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def texts(lang_rp, lang_bp):
    lines = ["## Playable Races - Foundation Release (Races 001-003)"]
    lines += [f"{k}={v}" for k, v in lang_rp]
    os.makedirs(os.path.join(RP, "texts"), exist_ok=True)
    with open(os.path.join(RP, "texts/en_US.lang"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    wjson(os.path.join(RP, "texts/languages.json"), ["en_US"])
    os.makedirs(os.path.join(BP, "texts"), exist_ok=True)
    with open(os.path.join(BP, "texts/en_US.lang"), "w", encoding="utf-8") as f:
        f.write("\n".join([f"{k}={v}" for k, v in lang_bp]) + "\n")
    wjson(os.path.join(BP, "texts/languages.json"), ["en_US"])


def manifests():
    bp = {"format_version": 2, "header": {
        "name": "pack.name", "description": "pack.description", "uuid": UUID["bp"], "version": VERSION,
        "min_engine_version": MIN_ENGINE},
        "modules": [
            {"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
            {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION, "entry": "scripts/main.js"}],
        "dependencies": [
            {"uuid": UUID["rp"], "version": VERSION},
            {"module_name": "@minecraft/server", "version": SERVER_API},
            {"module_name": "@minecraft/server-ui", "version": UI_API}],
        "metadata": {"authors": ["Playable Races project"], "product_type": "addon",
                     "generated_with": {"plrace_build": ["1.0.0"]}}}
    rp = {"format_version": 2, "header": {
        "name": "pack.name", "description": "pack.description", "uuid": UUID["rp"], "pack_scope": "world",
        "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
        "dependencies": [{"uuid": UUID["bp"], "version": VERSION}],
        "metadata": {"authors": ["Playable Races project"], "product_type": "addon",
                     "generated_with": {"plrace_build": ["1.0.0"]}}}
    wjson(os.path.join(BP, "manifest.json"), bp)
    wjson(os.path.join(RP, "manifest.json"), rp)


def compile_scripts():
    tsc = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        print("!! node_modules missing - run `npm install` (skipping script compile)")
        return False
    r = subprocess.run([tsc, "-p", os.path.join(ROOT, "tsconfig.json")], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-6000:], r.stderr[-2000:])
        raise SystemExit("TypeScript compilation failed")
    return True


def package():
    os.makedirs(DIST, exist_ok=True)

    def zipdir(zf, folder, arc_root):
        for base, _, files in os.walk(folder):
            for fn in sorted(files):
                full = os.path.join(base, fn)
                rel = os.path.relpath(full, folder)
                zf.write(full, os.path.join(arc_root, rel) if arc_root else rel)

    paths = {}
    for name, folder in ((BP_NAME, BP), (RP_NAME, RP)):
        p = os.path.join(DIST, f"{name}.mcpack")
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
            zipdir(zf, folder, "")
        paths[name] = p
    addon = os.path.join(DIST, "PlayableRaces.mcaddon")
    with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as zf:
        zipdir(zf, BP, BP_NAME)
        zipdir(zf, RP, RP_NAME)
    paths["addon"] = addon
    return paths


def main():
    no_tsc = "--no-tsc" in sys.argv
    for d in (BP, RP):
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
    report = []
    lang_rp, _ = build_races(report)
    rc = render_controllers()
    mirage_entity(lang_rp)
    mirage_render_controllers(rc)
    wjson(os.path.join(RP, "render_controllers/plrace/forms.render_controllers.json"), rc)
    prc, arc = player_overrides()
    wjson(os.path.join(RP, "render_controllers/plrace/player_form_visibility.render_controllers.json"), prc)
    wjson(os.path.join(RP, "render_controllers/plrace/armor_form_visibility.render_controllers.json"), arc)
    items(lang_rp)
    icons()
    particles()
    pack_icon(os.path.join(BP, "pack_icon.png"), os.path.join(RP, "pack_icon.png"))
    lang_rp = [("pack.name", "Playable Races: Foundation (Resources)"),
               ("pack.description", "Races 001-003: Flora Salamander, Runic Titan Golem, Blood Moon Jackalope")] + lang_rp
    lang_bp = [("pack.name", "Playable Races: Foundation"),
               ("pack.description", "Become an Aberrant Flora Salamander, a Runic Titan Golem or a Blood Moon Jackalope")]
    texts(lang_rp, lang_bp)
    manifests()
    compiled = False if no_tsc else compile_scripts()
    paths = package()
    for line in report:
        print(" -", line)
    print("scripts compiled:", compiled)
    for k, p in paths.items():
        print(f" {k}: {os.path.relpath(p, ROOT)} ({os.path.getsize(p) // 1024} KB)")


if __name__ == "__main__":
    main()
