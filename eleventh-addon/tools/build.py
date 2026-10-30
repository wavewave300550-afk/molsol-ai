"""
Build "Intelligent Beings of the 11th Dimension":

    python3 tools/build.py   ->  build/ packs  +  dist/Eleventh_Dimension.mcaddon

Generates models (solid + additive energy layer), textures, animations, animation
controllers, render controllers, client/behaviour entities, items, particles, language
files and manifests; compiles the TypeScript; packages the add-on.
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

import art  # noqa: E402
import beings  # noqa: E402

BUILD = os.path.join(ROOT, "build")
BP = os.path.join(BUILD, "Dim11_BP")
RP = os.path.join(BUILD, "Dim11_RP")
DIST = os.path.join(ROOT, "dist")

NAME = "Intelligent Beings of the 11th Dimension"
VERSION = [1, 0, 0]
MIN_ENGINE = [1, 26, 60]
SERVER_VERSION = "2.11.0"
SERVER_UI_VERSION = "2.3.0"
UUID = {
    "bp": "85c96781-f7e0-4ebb-b515-248f35447c31",
    "bp_data": "f066d8b1-a0f7-4071-8c06-3c11362f1593",
    "bp_script": "6baefa13-1ccf-47b3-8dcd-f36f008c7bdb",
    "rp": "bbacb1ab-6258-400e-99d6-5c805f95769a",
    "rp_res": "f078e6cb-5a0f-4972-9afb-77fa8980401c",
}

BOSSES = {
    # key: (display name, health, collision w, h, scale, egg base, egg overlay)
    "archon": ("AEON-7, the Calabi-Yau Archon", 720, 1.6, 4.2, 1.2, "#1a0b33", "#c45bff"),
    "sovereign": ("The M5 Sovereign", 680, 3.0, 1.8, 1.2, "#06262e", "#38e8ff"),
    "observer": ("The Ophanim of the Eleventh Axis", 640, 2.4, 3.2, 1.15, "#2a1a04", "#ffd27a"),
}
ITEMS = {
    "resonator": "Eleventh-Dimensional Resonator",
    "folded_petal": "Folded Petal of AEON-7",
    "string_of_creation": "String of Creation",
    "eye_of_the_axis": "Eye of the Eleventh Axis",
}
HUES = {
    "violet": (0.69, 0.42, 1.0), "cyan": (0.25, 0.92, 1.0), "gold": (1.0, 0.8, 0.32), "red": (1.0, 0.18, 0.22),
    "white": (1.0, 1.0, 1.0), "magenta": (1.0, 0.32, 0.9), "orange": (1.0, 0.58, 0.18), "yellow": (1.0, 0.9, 0.3),
    "green": (0.3, 1.0, 0.48), "blue": (0.3, 0.42, 1.0),
}
STATES = ["default", "cast", "channel", "ultimate", "stagger", "dying", "shift"]
STATE_VALUE = {"cast": 1, "channel": 2, "ultimate": 3, "stagger": 4, "dying": 5, "shift": 6}


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


# --------------------------------------------------------------------------- manifests

def manifests():
    wj(os.path.join(BP, "manifest.json"), {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["bp"], "version": VERSION,
                   "min_engine_version": MIN_ENGINE},
        "modules": [
            {"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
            {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION, "entry": "scripts/main.js"},
        ],
        "dependencies": [
            {"module_name": "@minecraft/server", "version": SERVER_VERSION},
            {"module_name": "@minecraft/server-ui", "version": SERVER_UI_VERSION},
            {"uuid": UUID["rp"], "version": VERSION},
        ],
        "metadata": {"authors": ["Eleventh Dimension team"], "product_type": "addon"},
    })
    wj(os.path.join(RP, "manifest.json"), {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["rp"], "version": VERSION,
                   "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
        "dependencies": [{"uuid": UUID["bp"], "version": VERSION}],
        "metadata": {"authors": ["Eleventh Dimension team"], "product_type": "addon"},
    })
    icon = art.pack_icon()
    save(icon, os.path.join(BP, "pack_icon.png"))
    save(icon, os.path.join(RP, "pack_icon.png"))


# --------------------------------------------------------------------------- models

BOUNDS = {"archon": (6, 6, 2.5), "sovereign": (8, 4, 1.5), "observer": (5, 5, 2.0), "wisp": (1.5, 1.5, 0.5)}


def build_models():
    out = {}
    for name, fn in beings.ALL.items():
        m = fn()
        img = m.paint()
        bw, bh, oy = BOUNDS[name]
        base = m.identifier
        wj(os.path.join(RP, "models", "entity", "dim11", f"{name}.geo.json"), m.geometry_json(bw, bh, oy, glow=False, identifier=base))
        wj(os.path.join(RP, "models", "entity", "dim11", f"{name}.glow.geo.json"), m.geometry_json(bw, bh, oy, glow=True, identifier=base + ".glow"))
        save(img, os.path.join(RP, "textures", "entity", "dim11", f"{name}.png"))
        out[name] = m
    return out


# --------------------------------------------------------------------------- animations

def anim(bones, loop=True):
    return {"loop": loop, "bones": bones}


E = "math.min(query.anim_time * 4.0, 1.0)"   # ease-in factor for state animations
T = "variable.t"


def s(expr, k):
    return f"math.sin({expr} * {k})"


def archon_anims():
    a = {}
    idle = {
        "body": {"position": [0, f"{s(T, 90)} * 1.2", 0]},
        "ring_a": {"rotation": [0, f"{T} * 45", 0]},
        "ring_b": {"rotation": [0, 0, f"-{T} * 60"]},
        "ring_c": {"rotation": [f"{T} * 75", 0, 0]},
        "petals": {"rotation": [0, f"{T} * 28", 0]},
        "crown": {"rotation": [0, f"-{T} * 70", 0]},
        "halo": {"rotation": [0, 0, f"{T} * 35"]},
        "head": {"rotation": [f"{s(T, 50)} * 3", f"{s(T, 30)} * 6", 0]},
        "arm_r": {"rotation": [f"{s(T, 70)} * 5", 0, f"-{s(T, 60)} * 4"]},
        "arm_l": {"rotation": [f"-{s(T, 70)} * 5", 0, f"{s(T, 60)} * 4"]},
        "forearm_r": {"rotation": [f"{s(T, 55)} * 6", 0, 0]},
        "forearm_l": {"rotation": [f"-{s(T, 55)} * 6", 0, 0]},
    }
    for k in range(6):
        idle[f"petal{k}"] = {"rotation": [0, 0, f"math.sin({T} * 120 + {k * 60}) * 8"]}
    for i in range(4):
        idle[f"robe{i}"] = {"rotation": [f"math.sin({T} * 80 - {i * 40}) * {3 + i * 2}", 0, f"math.cos({T} * 60 - {i * 40}) * {2 + i}"]}
    a["animation.dim11.archon.idle"] = anim(idle)
    a["animation.dim11.archon.cast"] = anim({
        "arm_r": {"rotation": [f"-75 * {E}", 0, f"-15 * {E}"]}, "arm_l": {"rotation": [f"-75 * {E}", 0, f"15 * {E}"]},
        "forearm_r": {"rotation": [f"-20 * {E}", 0, 0]}, "forearm_l": {"rotation": [f"-20 * {E}", 0, 0]},
        "head": {"rotation": [f"-10 * {E}", 0, 0]}, "ring_a": {"scale": f"1 + 0.15 * {E}"},
    })
    a["animation.dim11.archon.channel"] = anim({
        "arm_r": {"rotation": [f"-160 * {E}", 0, f"-25 * {E}"]}, "arm_l": {"rotation": [f"-160 * {E}", 0, f"25 * {E}"]},
        "head": {"rotation": [f"-20 * {E}", 0, 0]}, "crown": {"position": [0, f"3 * {E}", 0]},
        "ring_b": {"rotation": [f"25 * {E}", 0, 0]}, "ring_c": {"rotation": [0, f"25 * {E}", 0]},
    })
    a["animation.dim11.archon.ultimate"] = anim({
        "ring_a": {"scale": f"1 + 0.7 * {E}"}, "ring_b": {"scale": f"1 + 0.9 * {E}"}, "ring_c": {"scale": f"1 + 1.1 * {E}"},
        "petals": {"rotation": [0, "query.anim_time * 240", 0], "scale": f"1 + 0.3 * {E}"},
        **{f"petal{k}": {"rotation": [0, 0, f"45 * {E}"]} for k in range(6)},
        "crown": {"position": [0, f"6 * {E}", 0], "rotation": [0, "query.anim_time * -400", 0], "scale": f"1 + 0.5 * {E}"},
        "arm_r": {"rotation": [f"-30 * {E}", 0, f"-75 * {E}"]}, "arm_l": {"rotation": [f"-30 * {E}", 0, f"75 * {E}"]},
        "head": {"rotation": [f"-25 * {E}", 0, 0]}, "halo": {"scale": f"1 + 0.6 * {E}"},
    })
    a["animation.dim11.archon.stagger"] = anim({
        "head": {"rotation": [f"25 * {E}", 0, 0]}, "body": {"position": [0, f"-3 * {E}", 0]},
        "ring_a": {"rotation": ["math.sin(query.anim_time * 400) * 10", 0, 0]}, "ring_b": {"rotation": [0, "math.sin(query.anim_time * 380) * 12", 0]},
        "arm_r": {"rotation": [f"20 * {E}", 0, f"10 * {E}"]}, "arm_l": {"rotation": [f"20 * {E}", 0, f"-10 * {E}"]},
    })
    a["animation.dim11.archon.shift"] = anim({
        "body": {"rotation": [0, "query.anim_time * 360", 0], "scale": "1 + math.sin(query.anim_time * 720) * 0.08"},
        "crown": {"scale": "1.4"},
    })
    a["animation.dim11.archon.dying"] = anim({
        "body": {"rotation": [0, "query.anim_time * 120 * (1 + query.anim_time)", "math.sin(query.anim_time * 300) * 8"],
                 "position": [0, "-query.anim_time * 1.5", 0]},
        "ring_a": {"scale": "math.max(0, 1 - query.anim_time / 4.5)", "position": [0, "query.anim_time * 4", 0]},
        "ring_b": {"scale": "math.max(0, 1 - query.anim_time / 4)", "position": ["query.anim_time * 3", 0, 0]},
        "ring_c": {"scale": "math.max(0, 1 - query.anim_time / 3.5)", "position": [0, 0, "query.anim_time * 3"]},
        "crown": {"position": [0, "query.anim_time * 10", 0], "scale": "1 + query.anim_time * 0.4"},
        "petals": {"scale": "1 + query.anim_time * 0.5"},
    })
    return a


def sovereign_anims():
    a = {}
    idle = {
        "body": {"position": [0, f"{s(T, 60)} * 1.5", 0], "rotation": [f"math.sin({T} * 60 + 90) * 3", 0, 0]},
        "heart": {"scale": f"1 + {s(T, 240)} * 0.12"},
        "head": {"rotation": [f"{s(T, 50)} * 3", 0, 0]},
    }
    for k in range(5):
        amp = 6 + k * 3
        idle[f"wing_l{k}"] = {"rotation": [0, 0, f"math.sin({T} * 110 - {k * 50}) * {amp}"]}
        idle[f"wing_r{k}"] = {"rotation": [0, 0, f"-math.sin({T} * 110 - {k * 50}) * {amp}"]}
    for i in range(4):
        idle[f"tail{i}"] = {"rotation": [0, f"math.sin({T} * 90 - {i * 45}) * {5 + i * 2}", 0]}
    for k in range(9):
        idle[f"string{k}"] = {"rotation": [f"math.sin({T} * 700 + {k * 40}) * 2.5", 0, f"math.cos({T} * 900 + {k * 60}) * 2.5"]}
    a["animation.dim11.sovereign.idle"] = anim(idle)
    a["animation.dim11.sovereign.cast"] = anim({
        "head": {"rotation": [f"-18 * {E}", 0, 0]},
        **{f"string{k}": {"scale": f"1 + 0.2 * {E}"} for k in range(9)},
        **{f"wing_l{k}": {"rotation": [0, 0, f"10 * {E}"]} for k in range(1)},
        **{f"wing_r{k}": {"rotation": [0, 0, f"-10 * {E}"]} for k in range(1)},
    })
    a["animation.dim11.sovereign.channel"] = anim({
        **{f"wing_l{k}": {"rotation": [0, 0, f"(12 + math.sin(query.anim_time * 1500 + {k * 30}) * 4) * {E}"]} for k in range(5)},
        **{f"wing_r{k}": {"rotation": [0, 0, f"-(12 + math.sin(query.anim_time * 1500 + {k * 30}) * 4) * {E}"]} for k in range(5)},
        "body": {"rotation": [f"-10 * {E}", 0, 0]},
    })
    a["animation.dim11.sovereign.ultimate"] = anim({
        "wing_l0": {"rotation": [0, 0, f"55 * {E}"]}, "wing_r0": {"rotation": [0, 0, f"-55 * {E}"]},
        **{f"wing_l{k}": {"rotation": [0, 0, f"10 * {E}"]} for k in range(1, 5)},
        **{f"wing_r{k}": {"rotation": [0, 0, f"-10 * {E}"]} for k in range(1, 5)},
        "heart": {"scale": f"1 + 1.2 * {E} + math.sin(query.anim_time * 600) * 0.2"},
        **{f"string{k}": {"scale": f"1 + 0.5 * {E}"} for k in range(9)},
        "body": {"rotation": [f"-15 * {E}", 0, 0]},
    })
    a["animation.dim11.sovereign.stagger"] = anim({
        "wing_l0": {"rotation": [0, 0, f"-20 * {E}"]}, "wing_r0": {"rotation": [0, 0, f"20 * {E}"]},
        "head": {"rotation": [f"20 * {E}", 0, 0]}, "body": {"position": [0, f"-2 * {E}", 0]},
        **{f"tail{i}": {"rotation": [f"8 * {E}", 0, 0]} for i in range(4)},
    })
    a["animation.dim11.sovereign.shift"] = anim({"body": {"rotation": [0, 0, "math.sin(query.anim_time * 400) * 10"]}, "heart": {"scale": "2"}})
    a["animation.dim11.sovereign.dying"] = anim({
        "body": {"rotation": ["query.anim_time * 10", 0, "query.anim_time * 25"], "position": [0, "-query.anim_time * 3", 0]},
        "wing_l0": {"rotation": [0, 0, "-query.anim_time * 12"]}, "wing_r0": {"rotation": [0, 0, "query.anim_time * 12"]},
        "heart": {"scale": "1 + query.anim_time * 0.6"},
    })
    return a


def observer_anims():
    a = {}
    idle = {
        "tesseract_outer": {"rotation": [f"{T} * 22", f"{T} * 31", 0]},
        "tesseract_inner": {"rotation": [f"-{T} * 37", f"-{T} * 26", f"{T} * 17"]},
        "wheel_a": {"rotation": [0, 0, f"{T} * 65"]},
        "wheel_b": {"rotation": [f"-{T} * 55", 0, 0]},
        "halo": {"rotation": [0, f"{T} * 40", 0]},
        "body": {"position": [0, f"{s(T, 70)}", 0]},
        "eye": {"rotation": [f"{s(T, 37)} * 6", f"{s(T, 23)} * 10", 0]},
        "eyelid": {"position": [0, "(math.mod(query.life_time, 5.0) < 0.18) ? -3.0 : 0.0", 0]},
    }
    for side, sign in (("l", 1), ("r", -1)):
        for tier in range(3):
            idle[f"wing_{side}{tier}"] = {"rotation": [0, f"{sign} * math.sin({T} * 80 + {tier * 30}) * 8", f"{sign} * math.sin({T} * 80 + {tier * 30}) * 6"]}
    for k in range(3):
        idle[f"trail{k}"] = {"rotation": [f"math.sin({T} * 90 + {k * 60}) * 6", 0, f"math.cos({T} * 70 + {k * 40}) * 6"]}
    a["animation.dim11.observer.idle"] = anim(idle)
    a["animation.dim11.observer.cast"] = anim({
        "eye": {"scale": f"1 + 0.15 * {E}"}, "wheel_a": {"rotation": [0, 0, "query.anim_time * 400"]},
        "wheel_b": {"rotation": ["query.anim_time * -360", 0, 0]},
    })
    a["animation.dim11.observer.channel"] = anim({
        **{f"wing_l{t}": {"rotation": [0, 0, f"25 * {E}"]} for t in range(3)},
        **{f"wing_r{t}": {"rotation": [0, 0, f"-25 * {E}"]} for t in range(3)},
        "eye": {"scale": f"1 + 0.25 * {E}"}, "halo": {"scale": f"1 + 0.3 * {E}"},
    })
    a["animation.dim11.observer.ultimate"] = anim({
        "body": {"rotation": [0, "query.anim_time * 180", 0]},
        "wheel_a": {"scale": f"1 + 0.4 * {E}"}, "wheel_b": {"scale": f"1 + 0.5 * {E}"},
        "tesseract_inner": {"scale": "1 + math.sin(query.anim_time * 360) * 0.5"},
        "tesseract_outer": {"scale": "1 - math.sin(query.anim_time * 360) * 0.15"},
        "halo": {"position": [0, f"4 * {E}", 0], "scale": f"1 + 0.6 * {E}"},
        **{f"wing_l{t}": {"rotation": [0, 0, f"35 * {E}"]} for t in range(3)},
        **{f"wing_r{t}": {"rotation": [0, 0, f"-35 * {E}"]} for t in range(3)},
    })
    a["animation.dim11.observer.stagger"] = anim({
        "eyelid": {"position": [0, f"-3.5 * {E}", 0]}, "body": {"position": [0, f"-2 * {E}", 0]},
        "wheel_a": {"rotation": ["math.sin(query.anim_time * 300) * 8", 0, 0]},
    })
    a["animation.dim11.observer.shift"] = anim({"tesseract_inner": {"scale": "1 + math.sin(query.anim_time * 720) * 0.6"}})
    a["animation.dim11.observer.dying"] = anim({
        "tesseract_outer": {"scale": "math.max(0, 1 - query.anim_time / 4)"},
        "wheel_a": {"scale": "math.max(0, 1 - query.anim_time / 3.5)"},
        "wheel_b": {"scale": "math.max(0, 1 - query.anim_time / 3)"},
        "eye": {"scale": "1 + query.anim_time * 0.25"},
        "body": {"rotation": ["query.anim_time * 40", "query.anim_time * 200", 0]},
    })
    return a


def wisp_anims():
    return {"animation.dim11.wisp.spin": anim({
        "loop_a": {"rotation": [0, 0, "query.life_time * 360"]},
        "loop_b": {"rotation": ["query.life_time * -300", 0, 0]},
        "body": {"rotation": [0, "query.life_time * 90", 0], "position": [0, "math.sin(query.life_time * 200) * 0.6", 0]},
    })}


def controller(name):
    states = {}
    prop = "query.property('dim11:state')"
    for st in STATES:
        if st == "default":
            states[st] = {"animations": ["idle"], "blend_transition": 0.3,
                          "transitions": [{k: f"{prop} == {v}"} for k, v in STATE_VALUE.items()]}
        else:
            states[st] = {"animations": ["idle", st], "blend_transition": 0.3,
                          "transitions": [{"default": f"{prop} != {STATE_VALUE[st]}"}]}
    return {f"controller.animation.dim11.{name}": {"initial_state": "default", "states": states}}


def build_animations():
    allanims = {}
    allanims.update(archon_anims())
    allanims.update(sovereign_anims())
    allanims.update(observer_anims())
    allanims.update(wisp_anims())
    wj(os.path.join(RP, "animations", "dim11.animation.json"), {"format_version": "1.8.0", "animations": allanims})
    ctrls = {}
    for b in BOSSES:
        ctrls.update(controller(b))
    wj(os.path.join(RP, "animation_controllers", "dim11.animation_controllers.json"),
       {"format_version": "1.10.0", "animation_controllers": ctrls})
    return allanims


# --------------------------------------------------------------------------- render controllers / client entities

def build_render_controllers():
    rc = {
        "controller.render.dim11.solid": {"geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"]},
        "controller.render.dim11.glow": {"geometry": "Geometry.glow", "materials": [{"*": "Material.glow"}], "textures": ["Texture.default"]},
        "controller.render.dim11.ghost": {"geometry": "Geometry.default", "materials": [{"*": "Material.glow"}], "textures": ["Texture.default"]},
    }
    wj(os.path.join(RP, "render_controllers", "dim11.render_controllers.json"), {"format_version": "1.8.0", "render_controllers": rc})


def client_entity(ident, model, anims, animate, scale, egg=None, ghost=False):
    desc = {
        "identifier": ident,
        "materials": {"default": "entity_alphatest", "glow": "entity_beam_additive"},
        "textures": {"default": f"textures/entity/dim11/{model}"},
        "geometry": {"default": f"geometry.dim11.{model}", "glow": f"geometry.dim11.{model}.glow"},
        "animations": anims,
        "scripts": {
            "pre_animation": [
                "variable.spd = query.has_property('dim11:phase') ? 1.0 + (query.property('dim11:phase') - 1.0) * 0.45 : 1.0;",
                "variable.t = (variable.t ?? 0.0) + query.delta_time * variable.spd;",
            ],
            "animate": animate,
            "scale": str(scale),
        },
        "render_controllers": ["controller.render.dim11.ghost", "controller.render.dim11.glow"] if ghost
        else ["controller.render.dim11.solid", "controller.render.dim11.glow"],
    }
    if egg:
        desc["spawn_egg"] = {"base_color": egg[0], "overlay_color": egg[1]}
    return {"format_version": "1.10.0", "minecraft:client_entity": {"description": desc}}


def build_client_entities():
    for key, (_, _, _, _, scale, eb, eo) in BOSSES.items():
        anims = {st: f"animation.dim11.{key}.{'idle' if st == 'default' else st}" for st in STATES}
        anims["idle"] = anims.pop("default")
        anims["controller"] = f"controller.animation.dim11.{key}"
        wj(os.path.join(RP, "entity", "dim11", f"{key}.entity.json"),
           client_entity(f"dim11:{key}", key, anims, ["controller"], scale, (eb, eo)))
    wj(os.path.join(RP, "entity", "dim11", "wisp.entity.json"),
       client_entity("dim11:wisp", "wisp", {"spin": "animation.dim11.wisp.spin"}, ["spin"], 1.0))
    wj(os.path.join(RP, "entity", "dim11", "echo.entity.json"),
       client_entity("dim11:echo", "observer", {"idle": "animation.dim11.observer.idle", "cast": "animation.dim11.observer.cast"},
                     ["idle", "cast"], 0.9, ghost=True))
    wj(os.path.join(RP, "entity", "dim11", "phantom.entity.json"),
       client_entity("dim11:phantom", "sovereign", {"idle": "animation.dim11.sovereign.idle", "ult": "animation.dim11.sovereign.ultimate"},
                     ["idle", "ult"], 1.2, ghost=True))


# --------------------------------------------------------------------------- particles

def particle(ident, texture, comps, material="particles_add"):
    return {"format_version": "1.10.0", "particle_effect": {
        "description": {"identifier": ident, "basic_render_parameters": {"material": material, "texture": texture}},
        "components": comps}}


def billboard(size, uv=(0, 0, 16, 16), tex=(16, 16), facing="rotate_xyz"):
    return {"size": [size, size], "facing_camera_mode": facing,
            "uv": {"texture_width": tex[0], "texture_height": tex[1], "uv": list(uv[:2]), "uv_size": list(uv[2:])}}


def tint(rgb, alpha="1.0 - variable.particle_age / variable.particle_lifetime * 0.6"):
    return {"color": [rgb[0], rgb[1], rgb[2], alpha]}


SPARK = "textures/particle/dim11_spark"
SHRINK = "(1.0 - variable.particle_age / variable.particle_lifetime * 0.7)"


def build_particles():
    out = []
    P = os.path.join(RP, "particles", "dim11")
    for hue, rgb in HUES.items():
        defs = {
            f"dim11:mote_{hue}": {
                "minecraft:emitter_rate_instant": {"num_particles": 1},
                "minecraft:emitter_lifetime_once": {"active_time": 0.05},
                "minecraft:emitter_shape_point": {"direction": ["math.random(-1, 1)", "math.random(-1, 1)", "math.random(-1, 1)"]},
                "minecraft:particle_initial_speed": 0.08,
                "minecraft:particle_lifetime_expression": {"max_lifetime": "0.45 + variable.particle_random_1 * 0.4"},
                "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 1.0},
                "minecraft:particle_appearance_billboard": billboard(f"0.13 * {SHRINK}"),
                "minecraft:particle_appearance_tinting": tint(rgb),
            },
            f"dim11:burst_{hue}": {
                "minecraft:emitter_rate_instant": {"num_particles": 26},
                "minecraft:emitter_lifetime_once": {"active_time": 0.05},
                "minecraft:emitter_shape_sphere": {"radius": 0.3, "direction": "outwards"},
                "minecraft:particle_initial_speed": "3.0 + variable.particle_random_2 * 3.0",
                "minecraft:particle_lifetime_expression": {"max_lifetime": "0.55 + variable.particle_random_1 * 0.5"},
                "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 3.5},
                "minecraft:particle_appearance_billboard": billboard(f"0.18 * {SHRINK}"),
                "minecraft:particle_appearance_tinting": tint(rgb),
            },
            f"dim11:sphere_{hue}": {
                "minecraft:emitter_rate_instant": {"num_particles": 140},
                "minecraft:emitter_lifetime_once": {"active_time": 0.05},
                "minecraft:emitter_shape_sphere": {"radius": 0.6, "surface_only": True, "direction": "outwards"},
                "minecraft:particle_initial_speed": 15,
                "minecraft:particle_lifetime_expression": {"max_lifetime": "0.75 + variable.particle_random_1 * 0.2"},
                "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 2.4},
                "minecraft:particle_appearance_billboard": billboard(f"0.32 * {SHRINK}"),
                "minecraft:particle_appearance_tinting": tint(rgb),
            },
            f"dim11:wave_{hue}": {
                "minecraft:emitter_rate_instant": {"num_particles": 110},
                "minecraft:emitter_lifetime_once": {"active_time": 0.05},
                "minecraft:emitter_shape_disc": {"radius": 1.0, "surface_only": True, "plane_normal": "y", "direction": "outwards"},
                "minecraft:particle_initial_speed": 17,
                "minecraft:particle_lifetime_expression": {"max_lifetime": "0.8"},
                "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 2.2},
                "minecraft:particle_appearance_billboard": billboard(f"0.3 * {SHRINK}"),
                "minecraft:particle_appearance_tinting": tint(rgb),
            },
            f"dim11:column_{hue}": {
                "minecraft:emitter_rate_steady": {"spawn_rate": 90, "max_particles": 80},
                "minecraft:emitter_lifetime_once": {"active_time": 0.6},
                "minecraft:emitter_shape_box": {"half_dimensions": [0.35, 0.1, 0.35], "direction": [0, 1, 0]},
                "minecraft:particle_initial_speed": "12 + variable.particle_random_2 * 6",
                "minecraft:particle_lifetime_expression": {"max_lifetime": "0.75"},
                "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 1.2},
                "minecraft:particle_appearance_billboard": billboard(f"0.28 * {SHRINK}"),
                "minecraft:particle_appearance_tinting": tint(rgb),
            },
            f"dim11:ring_{hue}": {
                "minecraft:emitter_rate_instant": {"num_particles": 1},
                "minecraft:emitter_lifetime_once": {"active_time": 0.05},
                "minecraft:emitter_shape_point": {},
                "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life ?? 0.9"},
                "minecraft:particle_appearance_billboard": billboard(
                    "(variable.radius ?? 6.0) * variable.particle_age / variable.particle_lifetime + 0.2",
                    (0, 0, 64, 64), (64, 64), "emitter_transform_xz"),
                "minecraft:particle_appearance_tinting": tint(rgb, "1.0 - variable.particle_age / variable.particle_lifetime"),
            },
        }
        for ident, comps in defs.items():
            tex = "textures/particle/dim11_ring" if ident.startswith("dim11:ring_") else SPARK
            wj(os.path.join(P, ident.split(":")[1] + ".json"), particle(ident, tex, comps))
            out.append(ident)

    specials = {
        "dim11:sigil": ("textures/particle/dim11_sigil", {
            "minecraft:emitter_rate_instant": {"num_particles": 1},
            "minecraft:emitter_lifetime_once": {"active_time": 0.05},
            "minecraft:emitter_shape_point": {},
            "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life ?? 2.0"},
            "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 40},
            "minecraft:particle_appearance_billboard": billboard(
                "(variable.size ?? 4.0) * 0.5 * math.min(1.0, variable.particle_age * 4.0)", (0, 0, 128, 128), (128, 128), "emitter_transform_xz"),
            "minecraft:particle_appearance_tinting": {"color": [1, 1, 1, "math.min(1.0, (variable.particle_lifetime - variable.particle_age) * 3.0)"]},
        }),
        "dim11:danger": ("textures/particle/dim11_danger", {
            "minecraft:emitter_rate_instant": {"num_particles": 1},
            "minecraft:emitter_lifetime_once": {"active_time": 0.05},
            "minecraft:emitter_shape_point": {},
            "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life ?? 1.5"},
            "minecraft:particle_appearance_billboard": billboard("(variable.size ?? 4.0) * 0.5", (0, 0, 64, 64), (64, 64), "emitter_transform_xz"),
            "minecraft:particle_appearance_tinting": {"color": [1, 1, 1, "0.55 + 0.45 * math.sin(variable.particle_age * 1400)"]},
        }),
        "dim11:glyphs": ("textures/particle/dim11_runes", {
            "minecraft:emitter_rate_instant": {"num_particles": 16},
            "minecraft:emitter_lifetime_once": {"active_time": 0.05},
            "minecraft:emitter_shape_sphere": {"radius": 2.6, "direction": [0, 1, 0]},
            "minecraft:particle_initial_speed": 1.2,
            "minecraft:particle_lifetime_expression": {"max_lifetime": "1.6 + variable.particle_random_1 * 0.6"},
            "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 0.5},
            "minecraft:particle_appearance_billboard": billboard(
                "0.22", ("math.floor(variable.particle_random_3 * 8) * 8", 0, 8, 8), (64, 8)),
            "minecraft:particle_appearance_tinting": {"color": ["0.85 + variable.particle_random_2 * 0.15", "0.6 + variable.particle_random_2 * 0.3", 1.0,
                                                               "1.0 - variable.particle_age / variable.particle_lifetime"]},
        }),
        "dim11:flash": ("textures/particle/dim11_flash", {
            "minecraft:emitter_rate_instant": {"num_particles": 1},
            "minecraft:emitter_lifetime_once": {"active_time": 0.05},
            "minecraft:emitter_shape_point": {},
            "minecraft:particle_lifetime_expression": {"max_lifetime": 0.45},
            "minecraft:particle_appearance_billboard": billboard("2.0 + variable.particle_age * 22.0", (0, 0, 32, 32), (32, 32)),
            "minecraft:particle_appearance_tinting": {"color": [1, 1, 1, "1.0 - variable.particle_age / variable.particle_lifetime"]},
        }),
        "dim11:starfield": (SPARK, {
            "minecraft:emitter_rate_instant": {"num_particles": 180},
            "minecraft:emitter_lifetime_once": {"active_time": 0.05},
            "minecraft:emitter_shape_sphere": {"radius": 18, "direction": "outwards"},
            "minecraft:particle_initial_speed": 0.2,
            "minecraft:particle_lifetime_expression": {"max_lifetime": "2.5 + variable.particle_random_1 * 1.5"},
            "minecraft:particle_appearance_billboard": billboard("0.07 + variable.particle_random_2 * 0.08"),
            "minecraft:particle_appearance_tinting": {"color": ["0.8 + variable.particle_random_3 * 0.2", "0.85", 1.0,
                                                               "0.6 + 0.4 * math.sin(variable.particle_age * 600 + variable.particle_random_4 * 360)"]},
        }),
    }
    for ident, (tex, comps) in specials.items():
        wj(os.path.join(P, ident.split(":")[1] + ".json"), particle(ident, tex, comps))
        out.append(ident)

    T = os.path.join(RP, "textures", "particle")
    save(art.spark(), os.path.join(T, "dim11_spark.png"))
    save(art.soft_ring(), os.path.join(T, "dim11_ring.png"))
    save(art.sigil(), os.path.join(T, "dim11_sigil.png"))
    save(art.danger(), os.path.join(T, "dim11_danger.png"))
    save(art.runes(), os.path.join(T, "dim11_runes.png"))
    save(art.flash_sprite(), os.path.join(T, "dim11_flash.png"))
    return out


# --------------------------------------------------------------------------- behaviour entities

def boss_entity(key):
    name, hp, w, h, _, _, _ = BOSSES[key]
    return {
        "format_version": "1.21.0",
        "minecraft:entity": {
            "description": {
                "identifier": f"dim11:{key}", "is_spawnable": True, "is_summonable": True,
                "properties": {
                    "dim11:state": {"type": "int", "range": [0, 6], "default": 0, "client_sync": True},
                    "dim11:phase": {"type": "int", "range": [1, 3], "default": 1, "client_sync": True},
                },
            },
            "components": {
                "minecraft:type_family": {"family": ["dim11_being", "boss", "monster", "mob"]},
                "minecraft:health": {"value": hp, "max": hp},
                "minecraft:boss": {"should_darken_sky": True, "hud_range": 64},
                "minecraft:collision_box": {"width": w, "height": h},
                "minecraft:physics": {"has_gravity": False, "has_collision": False},
                "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
                "minecraft:knockback_resistance": {"value": 1.0},
                "minecraft:fire_immune": {},
                "minecraft:persistent": {},
                "minecraft:nameable": {"always_show": False, "allow_name_tag_renaming": False},
                "minecraft:damage_sensor": {"triggers": [
                    {"cause": c, "deals_damage": "no"} for c in
                    ("fall", "fire", "fire_tick", "lava", "drowning", "suffocation", "lightning", "magma", "freezing", "wither", "contact", "fly_into_wall")
                ]},
                "minecraft:experience_reward": {"on_death": "200"},
                "minecraft:conditional_bandwidth_optimization": {},
            },
        },
    }


def helper_entity(key, families, hp, w, h, invulnerable, lifetime):
    comps = {
        "minecraft:type_family": {"family": families},
        "minecraft:health": {"value": hp, "max": hp},
        "minecraft:collision_box": {"width": w, "height": h},
        "minecraft:physics": {"has_gravity": False, "has_collision": False},
        "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
        "minecraft:knockback_resistance": {"value": 1.0},
        "minecraft:fire_immune": {},
        "minecraft:timer": {"looping": False, "time": lifetime, "randomInterval": False,
                            "time_down_event": {"event": "dim11:despawn", "target": "self"}},
        "minecraft:conditional_bandwidth_optimization": {},
        "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": "no"}] if invulnerable
                                    else [{"cause": c, "deals_damage": "no"} for c in ("fall", "fire", "fire_tick", "suffocation")]},
    }
    return {
        "format_version": "1.21.0",
        "minecraft:entity": {
            "description": {"identifier": f"dim11:{key}", "is_spawnable": False, "is_summonable": True},
            "components": comps,
            "component_groups": {"dim11:despawn": {"minecraft:instant_despawn": {}}},
            "events": {"dim11:despawn": {"add": {"component_groups": ["dim11:despawn"]}}},
        },
    }


def build_bp_entities():
    for key in BOSSES:
        wj(os.path.join(BP, "entities", "dim11", f"{key}.json"), boss_entity(key))
    wj(os.path.join(BP, "entities", "dim11", "wisp.json"), helper_entity("wisp", ["dim11_minion", "monster", "mob"], 12, 0.8, 0.8, False, 12))
    wj(os.path.join(BP, "entities", "dim11", "echo.json"), helper_entity("echo", ["dim11_illusion", "inanimate"], 100, 1, 1, True, 10))
    wj(os.path.join(BP, "entities", "dim11", "phantom.json"), helper_entity("phantom", ["dim11_illusion", "inanimate"], 100, 1, 1, True, 12))


def build_items():
    tex = {}
    for key in ITEMS:
        save(art.icon(key), os.path.join(RP, "textures", "items", "dim11", f"{key}.png"))
        tex[f"dim11_{key}"] = {"textures": f"textures/items/dim11/{key}"}
        comps = {
            "minecraft:icon": {"textures": {"default": f"dim11_{key}"}},
            "minecraft:display_name": {"value": f"item.dim11:{key}.name"},
            "minecraft:max_stack_size": 1,
            "minecraft:glint": True,
            "minecraft:hand_equipped": key != "resonator",
        }
        cd = {"folded_petal": ("dim11_petal", 2.5), "string_of_creation": ("dim11_string", 1.5), "eye_of_the_axis": ("dim11_eye", 60)}.get(key)
        if cd:
            comps["minecraft:cooldown"] = {"category": cd[0], "duration": cd[1]}
        wj(os.path.join(BP, "items", "dim11", f"{key}.json"), {
            "format_version": "1.21.60",
            "minecraft:item": {"description": {"identifier": f"dim11:{key}", "menu_category": {"category": "equipment"}}, "components": comps},
        })
    wj(os.path.join(RP, "textures", "item_texture.json"), {"resource_pack_name": "dim11", "texture_name": "atlas.items", "texture_data": tex})
    wj(os.path.join(BP, "recipes", "resonator.json"), {
        "format_version": "1.20.10",
        "minecraft:recipe_shaped": {
            "description": {"identifier": "dim11:resonator"},
            "tags": ["crafting_table"],
            "pattern": ["ADA", "DED", "ACA"],
            "key": {"A": {"item": "minecraft:amethyst_shard"}, "D": {"item": "minecraft:diamond"},
                    "E": {"item": "minecraft:ender_eye"}, "C": {"item": "minecraft:crying_obsidian"}},
            "unlock": [{"item": "minecraft:amethyst_shard"}],
            "result": {"item": "dim11:resonator"},
        },
    })


def build_lang():
    en = [f"pack.name={NAME}", "pack.description=Three intelligent high-tier beings from the 11th dimension - with adaptive AI and cinematic ultimates."]
    for key, name in ITEMS.items():
        en.append(f"item.dim11:{key}.name={name}")
    for key, (name, *_rest) in BOSSES.items():
        en.append(f"entity.dim11:{key}.name={name}")
        en.append(f"item.spawn_egg.entity.dim11:{key}.name=Summon {name}")
    en += ["entity.dim11:wisp.name=Closed-String Wisp", "entity.dim11:echo.name=Timeline Echo", "entity.dim11:phantom.name=Brane Image"]
    for root in (BP, RP):
        wt(os.path.join(root, "texts", "en_US.lang"), "\n".join(en if root == RP else en[:2]) + "\n")
        wt(os.path.join(root, "texts", "languages.json"), json.dumps(["en_US"], indent=2) + "\n")


def build_scripts():
    tsc = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        raise SystemExit("run `npm install` first")
    res = subprocess.run([tsc, "-p", os.path.join(ROOT, "tsconfig.json"), "--outDir", os.path.join(BP, "scripts")],
                         capture_output=True, text=True)
    if res.returncode:
        print(res.stdout, res.stderr)
        raise SystemExit("TypeScript compilation failed")


def zip_dir(zf, folder, arc):
    for dp, _, files in os.walk(folder):
        for fn in sorted(files):
            full = os.path.join(dp, fn)
            zf.write(full, os.path.join(arc, os.path.relpath(full, folder)))


def package():
    os.makedirs(DIST, exist_ok=True)
    base = "Eleventh_Dimension"
    with zipfile.ZipFile(os.path.join(DIST, f"{base}.mcaddon"), "w", zipfile.ZIP_DEFLATED) as zf:
        zip_dir(zf, BP, "Dim11_BP")
        zip_dir(zf, RP, "Dim11_RP")
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


if __name__ == "__main__":
    main()
