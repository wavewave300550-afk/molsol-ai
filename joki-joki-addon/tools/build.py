"""
Build script for "Jōki Jōki no Mi — Steam Pressure".

    python3 tools/build.py      -> build/Joki_BP, build/Joki_RP, dist/*.mcaddon + *.mcpack

Generates every pack file (manifests, player overrides, render controllers, animation
controller, player animations, particles, items, textures, sounds, language files),
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

import art  # noqa: E402
import fruit_icon  # noqa: E402
import sounds  # noqa: E402

BUILD = os.path.join(ROOT, "build")
BP = os.path.join(BUILD, "Joki_BP")
RP = os.path.join(BUILD, "Joki_RP")
DIST = os.path.join(ROOT, "dist")

ADDON_NAME = "Jōki Jōki no Mi - Steam Pressure"
FILE_BASE = "Joki_Joki_no_Mi_Steam_Pressure"
VERSION = [1, 0, 1]
MIN_ENGINE = [1, 26, 60]
SERVER_VERSION = "2.11.0"
SERVER_UI_VERSION = "2.3.0"
UUID = {
    "bp_header": "bbaa72b5-9e74-4d2d-bddb-a71201c38771",
    "bp_data": "d9465054-05cb-4294-8188-4abb203b8100",
    "bp_script": "282c3c86-71c1-4280-9099-8870a4adaa30",
    "rp_header": "bc1297c7-bf77-4d21-811b-7f6b5d6fc35e",
    "rp_res": "8464ec70-31ce-4242-89bc-40c7c8468443",
}

# Entity-local axes for particles bound to the player: +Z is assumed to be the facing direction
# (so "back" vents sit at -Z). If vents appear on the chest in game, flip this sign.
FORWARD = 1.0

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


def save_png(img, rel_path):
    p = os.path.join(RP, rel_path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    img.save(p)


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
            {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION, "entry": "scripts/main.js"},
        ],
        "dependencies": [
            {"module_name": "@minecraft/server", "version": SERVER_VERSION},
            {"module_name": "@minecraft/server-ui", "version": SERVER_UI_VERSION},
            {"uuid": UUID["rp_header"], "version": VERSION},
        ],
        "metadata": {"authors": ["Joki Joki no Mi add-on (fan-made)"], "product_type": "addon"},
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
        "metadata": {"authors": ["Joki Joki no Mi add-on (fan-made)"], "product_type": "addon"},
    }
    write_json(os.path.join(BP, "manifest.json"), bp)
    write_json(os.path.join(RP, "manifest.json"), rp)
    icon = fruit_icon.pack_icon()
    for p in (BP, RP):
        icon.save(os.path.join(p, "pack_icon.png"))


# --------------------------------------------------------------------------- textures


def build_textures():
    save_png(fruit_icon.fruit_icon(128), "textures/items/joki/joki_fruit.png")
    save_png(art.valve_icon(32), "textures/items/joki/steam_valve.png")
    save_png(art.particle_atlas(), "textures/particle/joki_steam.png")
    for name in art.UI_ICONS:
        save_png(art.ui_icon(name), f"textures/joki/ui/{name}.png")
    write_json(os.path.join(RP, "textures", "item_texture.json"), {
        "resource_pack_name": "joki",
        "texture_name": "atlas.items",
        "texture_data": {
            "joki_fruit": {"textures": "textures/items/joki/joki_fruit"},
            "joki_steam_valve": {"textures": "textures/items/joki/steam_valve"},
        },
    })


# --------------------------------------------------------------------------- particles

TEX = "textures/particle/joki_steam"
A = 128  # atlas size
C = 32  # cell size


def cell_uv(name):
    c, r = art.ATLAS_CELLS[name]
    return [c * C, r * C]


def uv_random_row(row_name):
    """UV picking one of the 4 cells of an atlas row at random per particle."""
    _, r = art.ATLAS_CELLS[row_name + "0"]
    return {"texture_width": A, "texture_height": A, "uv": ["math.floor(variable.particle_random_3 * 3.99) * 32", r * C], "uv_size": [C, C]}


def uv_cell(name):
    return {"texture_width": A, "texture_height": A, "uv": cell_uv(name), "uv_size": [C, C]}


AGE = "(variable.particle_age / variable.particle_lifetime)"


def alpha_expr(peak, fade_in=0.08):
    return f"math.min({AGE} / {fade_in}, 1.0) * (1.0 - {AGE}) * {peak}"


def grow(s0, s1, power=0.6):
    return f"{s0} + ({s1} - {s0}) * math.pow({AGE}, {power})"


def tint(rgb_start, rgb_end, peak, fade_in=0.08):
    """Colour gradient over life with the alpha envelope in the 4th channel."""
    a = alpha_expr(peak, fade_in)
    return {"color": [
        f"{rgb_start[0]} + ({rgb_end[0]} - {rgb_start[0]}) * math.min({AGE} * 3.0, 1.0)",
        f"{rgb_start[1]} + ({rgb_end[1]} - {rgb_start[1]}) * math.min({AGE} * 3.0, 1.0)",
        f"{rgb_start[2]} + ({rgb_end[2]} - {rgb_start[2]}) * math.min({AGE} * 3.0, 1.0)",
        a,
    ]}


WHITE = (1.0, 1.0, 1.0)
STEAM = (0.93, 0.94, 0.97)
WARM = (1.0, 0.78, 0.6)
HOT = (1.0, 0.45, 0.2)
MIST = (0.86, 0.89, 0.95)


def particle(ident, comps, material="particles_blend"):
    return {
        "format_version": "1.10.0",
        "particle_effect": {
            "description": {"identifier": ident, "basic_render_parameters": {"material": material, "texture": TEX}},
            "components": comps,
        },
    }


def steam_look(size0, size1, peak=0.8, start=WARM, end=STEAM, row="puff", fade_in=0.08, spin=True):
    comps = {
        "minecraft:particle_appearance_billboard": {
            "size": [grow(size0, size1), grow(size0, size1)],
            "facing_camera_mode": "rotate_xyz",
            "uv": uv_random_row(row),
        },
        "minecraft:particle_appearance_tinting": tint(start, end, peak, fade_in),
        "minecraft:particle_appearance_lighting": {},
    }
    if spin:
        comps["minecraft:particle_initial_spin"] = {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-50, 50)"}
    return comps


def jet_look(length0, length1, width0, width1, peak=0.85, start=WARM, end=STEAM, cell="streak"):
    """Velocity-aligned streak: billboard width runs along the motion (lookat_direction)."""
    return {
        "minecraft:particle_appearance_billboard": {
            "size": [grow(length0, length1), grow(width0, width1)],
            "facing_camera_mode": "lookat_direction",
            "direction": {"mode": "derive_from_velocity", "min_speed_threshold": 0.01},
            "uv": uv_cell(cell),
        },
        "minecraft:particle_appearance_tinting": tint(start, end, peak, 0.05),
    }


def life(lo, hi):
    return {"max_lifetime": f"{lo} + variable.particle_random_1 * {round(hi - lo, 3)}"}


def motion(rise=0.0, drag=2.0, gravity=0.0):
    return {"linear_acceleration": [0, rise - gravity, 0], "linear_drag_coefficient": drag}


def once(n):
    return {"minecraft:emitter_rate_instant": {"num_particles": n}, "minecraft:emitter_lifetime_once": {"active_time": 0.05}}


def looping(rate, max_particles):
    return {
        "minecraft:emitter_rate_steady": {"spawn_rate": rate, "max_particles": max_particles},
        "minecraft:emitter_lifetime_looping": {"active_time": 1.0},
        "minecraft:emitter_local_space": {"position": True, "rotation": True},
    }


DIR = "variable.direction"


def directed_dir(spread):
    return [f"({DIR}.x ?? 0) + math.random(-{spread}, {spread})", f"({DIR}.y ?? 1) + math.random(-{spread}, {spread})",
            f"({DIR}.z ?? 0) + math.random(-{spread}, {spread})"]


POWER = "(variable.power ?? 1.0)"
RADIUS = "(variable.radius ?? 1.5)"


def server_particles():
    P = {}
    # --- high-pressure jets (direction + power)
    P["joki:jet"] = particle("joki:jet", {
        **once(16),
        "minecraft:emitter_shape_point": {"direction": directed_dir(0.1)},
        "minecraft:particle_initial_speed": f"(7.0 + math.random(0, 5)) * {POWER}",
        "minecraft:particle_lifetime_expression": life(0.3, 0.55),
        "minecraft:particle_motion_dynamic": motion(rise=0.8, drag=4.5),
        **jet_look(0.5, 1.4, 0.2, 0.55, peak=0.9),
    })
    P["joki:dash_jet"] = particle("joki:dash_jet", {
        **once(9),
        "minecraft:emitter_shape_point": {"direction": directed_dir(0.22)},
        "minecraft:particle_initial_speed": f"(4.5 + math.random(0, 3.5)) * {POWER}",
        "minecraft:particle_lifetime_expression": life(0.3, 0.55),
        "minecraft:particle_motion_dynamic": motion(rise=0.6, drag=3.2),
        **jet_look(0.4, 1.0, 0.18, 0.5, peak=0.8),
    })
    P["joki:downjet"] = particle("joki:downjet", {
        **once(12),
        "minecraft:emitter_shape_point": {"direction": directed_dir(0.28)},
        "minecraft:particle_initial_speed": f"(6.0 + math.random(0, 3.0)) * {POWER}",
        "minecraft:particle_lifetime_expression": life(0.6, 0.95),
        "minecraft:particle_motion_dynamic": motion(rise=0.9, drag=3.0),
        "minecraft:particle_motion_collision": {"collision_radius": 0.12, "coefficient_of_restitution": 0.25, "collision_drag": 2.0},
        **steam_look(0.3, 1.1, 0.85, row="billow"),
    })
    P["joki:cone_blast"] = particle("joki:cone_blast", {
        **once(18),
        "minecraft:emitter_shape_point": {"direction": directed_dir(0.42)},
        "minecraft:particle_initial_speed": f"(6.0 + math.random(0, 4.0)) * {POWER}",
        "minecraft:particle_lifetime_expression": life(0.45, 0.8),
        "minecraft:particle_motion_dynamic": motion(rise=0.6, drag=4.0),
        **steam_look(0.35, 1.4, 0.85, row="billow"),
    })
    # --- puffs, wakes, clouds
    P["joki:puff"] = particle("joki:puff", {
        **once(7),
        "minecraft:emitter_shape_sphere": {"radius": 0.3, "direction": "outwards"},
        "minecraft:particle_initial_speed": "math.random(0.6, 1.3)",
        "minecraft:particle_lifetime_expression": life(0.8, 1.3),
        "minecraft:particle_motion_dynamic": motion(rise=0.6, drag=2.0),
        **steam_look(0.4, 1.1, 0.8),
    })
    P["joki:wake"] = particle("joki:wake", {
        **once(2),
        "minecraft:emitter_shape_sphere": {"radius": 0.15, "direction": "outwards"},
        "minecraft:particle_initial_speed": 0.15,
        "minecraft:particle_lifetime_expression": life(0.9, 1.4),
        "minecraft:particle_motion_dynamic": motion(rise=0.4, drag=1.5),
        **steam_look(0.3, 0.85, 0.55, start=STEAM),
    })
    P["joki:shock_ring"] = particle("joki:shock_ring", {
        **once(20),
        "minecraft:emitter_shape_disc": {"radius": 0.3, "plane_normal": [0, 1, 0], "direction": "outwards"},
        "minecraft:particle_initial_speed": f"{RADIUS} * 2.6",
        "minecraft:particle_lifetime_expression": life(0.5, 0.8),
        "minecraft:particle_motion_dynamic": motion(rise=0.3, drag=3.0),
        **steam_look(0.35, 0.95, 0.75, start=STEAM),
    })
    P["joki:land"] = particle("joki:land", {
        **once(16),
        "minecraft:emitter_shape_disc": {"radius": 0.3, "plane_normal": [0, 1, 0], "direction": "outwards"},
        "minecraft:particle_initial_speed": "math.random(2.5, 3.5)",
        "minecraft:particle_lifetime_expression": life(0.6, 0.9),
        "minecraft:particle_motion_dynamic": motion(rise=0.4, drag=4.0),
        **steam_look(0.3, 0.9, 0.75, start=STEAM),
    })
    P["joki:scald_cloud"] = particle("joki:scald_cloud", {
        **once(70),
        "minecraft:emitter_shape_sphere": {"radius": 0.5, "direction": "outwards"},
        "minecraft:particle_initial_speed": "math.random(7, 11)",
        "minecraft:particle_lifetime_expression": life(1.6, 2.4),
        "minecraft:particle_motion_dynamic": motion(rise=0.3, drag=5.0),
        **steam_look(0.6, 2.2, 0.85, start=WARM, row="billow"),
    })
    P["joki:cloud_linger"] = particle("joki:cloud_linger", {
        **once(8),
        "minecraft:emitter_shape_sphere": {"radius": RADIUS, "direction": "outwards"},
        "minecraft:particle_initial_speed": 0.2,
        "minecraft:particle_lifetime_expression": life(1.6, 2.0),
        "minecraft:particle_motion_dynamic": motion(rise=0.15, drag=1.0),
        **steam_look(1.2, 2.0, 0.6, start=STEAM, row="billow", fade_in=0.25),
    })
    P["joki:mist_cloud"] = particle("joki:mist_cloud", {
        **once(14),
        "minecraft:emitter_shape_sphere": {"radius": RADIUS, "direction": "outwards"},
        "minecraft:particle_initial_speed": 0.3,
        "minecraft:particle_lifetime_expression": life(1.6, 2.2),
        "minecraft:particle_motion_dynamic": motion(rise=0.05, drag=1.0),
        **steam_look(1.5, 2.6, 0.7, start=MIST, end=MIST, row="billow", fade_in=0.3),
    })
    P["joki:mist_fade"] = particle("joki:mist_fade", {
        **once(7),
        "minecraft:emitter_shape_sphere": {"radius": RADIUS, "direction": "outwards"},
        "minecraft:particle_initial_speed": 0.6,
        "minecraft:particle_lifetime_expression": life(1.0, 1.4),
        "minecraft:particle_motion_dynamic": motion(rise=0.4, drag=1.0),
        **steam_look(1.6, 2.4, 0.4, start=MIST, end=MIST, row="billow", fade_in=0.2),
    })
    # --- impacts and bolts
    P["joki:impact"] = particle("joki:impact", {
        **once(22),
        "minecraft:emitter_shape_sphere": {"radius": 0.1, "direction": "outwards"},
        "minecraft:particle_initial_speed": "math.random(6, 10)",
        "minecraft:particle_lifetime_expression": life(0.25, 0.5),
        "minecraft:particle_motion_dynamic": motion(rise=0.5, drag=6.0),
        **jet_look(0.6, 1.1, 0.2, 0.45, peak=0.95, start=(1.0, 0.85, 0.7)),
    })
    P["joki:bolt_core"] = particle("joki:bolt_core", {
        **once(2),
        "minecraft:emitter_shape_point": {},
        "minecraft:particle_initial_speed": 0,
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.14},
        "minecraft:particle_appearance_billboard": {"size": [0.75, 0.75], "facing_camera_mode": "rotate_xyz", "uv": uv_cell("flash")},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.75, 0.5, f"1.0 - {AGE}"]},
    }, material="particles_add")
    P["joki:bolt_trail"] = particle("joki:bolt_trail", {
        **once(2),
        # vapour shed backwards along the shot (variable.direction = bolt travel direction)
        "minecraft:emitter_shape_point": {"direction": [f"-({DIR}.x ?? 0) + math.random(-0.35, 0.35)", f"-({DIR}.y ?? 0) + math.random(-0.2, 0.5)",
                                                        f"-({DIR}.z ?? 0) + math.random(-0.35, 0.35)"]},
        "minecraft:particle_initial_speed": f"math.random(0.4, 1.0) * {POWER}",
        "minecraft:particle_lifetime_expression": life(0.4, 0.7),
        "minecraft:particle_motion_dynamic": motion(rise=0.5, drag=2.0),
        **steam_look(0.25, 0.75, 0.85, start=(1.0, 0.6, 0.35)),
    })
    P["joki:hand_steam"] = particle("joki:hand_steam", {
        **once(3),
        "minecraft:emitter_shape_sphere": {"radius": 0.15, "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "math.random(0.3, 0.6)",
        "minecraft:particle_lifetime_expression": life(0.4, 0.7),
        "minecraft:particle_motion_dynamic": motion(rise=0.8, drag=1.5),
        **steam_look(0.12, 0.38, 0.85, start=HOT),
    })
    # --- transformations
    P["joki:ignite_swirl"] = particle("joki:ignite_swirl", {
        **once(10),
        "minecraft:emitter_shape_point": {
            "offset": ["math.cos(variable.particle_random_2 * 360) * 0.75", "math.random(0, 0.3)", "math.sin(variable.particle_random_2 * 360) * 0.75"],
            "direction": ["-math.sin(variable.particle_random_2 * 360) * 1.2", "1.0", "math.cos(variable.particle_random_2 * 360) * 1.2"],
        },
        "minecraft:particle_initial_speed": "math.random(2.5, 3.5)",
        "minecraft:particle_lifetime_expression": life(0.6, 0.9),
        "minecraft:particle_motion_dynamic": motion(rise=1.2, drag=1.5),
        **steam_look(0.3, 0.9, 0.8, start=HOT),
    })
    P["joki:redline_burst"] = particle("joki:redline_burst", {
        **once(50),
        "minecraft:emitter_shape_disc": {"radius": 0.45, "plane_normal": [0, 1, 0], "direction": ["math.random(-0.25, 0.25)", 1, "math.random(-0.25, 0.25)"]},
        "minecraft:particle_initial_speed": "math.random(8, 14)",
        "minecraft:particle_lifetime_expression": life(0.8, 1.2),
        "minecraft:particle_motion_dynamic": motion(rise=0.5, drag=2.5),
        **steam_look(0.5, 1.6, 0.9, start=(1.0, 0.3, 0.15), row="billow"),
    })
    P["joki:vent_release"] = particle("joki:vent_release", {
        **once(26),
        "minecraft:emitter_shape_point": {
            "offset": ["math.cos(variable.particle_random_2 * 360) * 0.35", "math.random(0.3, 1.7)", "math.sin(variable.particle_random_2 * 360) * 0.35"],
            "direction": ["math.cos(variable.particle_random_2 * 360) * 0.6", "1.0", "math.sin(variable.particle_random_2 * 360) * 0.6"],
        },
        "minecraft:particle_initial_speed": "math.random(2, 4)",
        "minecraft:particle_lifetime_expression": life(1.0, 1.6),
        "minecraft:particle_motion_dynamic": motion(rise=1.0, drag=2.0),
        **steam_look(0.4, 1.4, 0.8, row="billow"),
    })
    P["joki:fruit_aura"] = particle("joki:fruit_aura", {
        **once(30),
        "minecraft:emitter_shape_sphere": {"radius": 0.5, "direction": "outwards"},
        "minecraft:particle_initial_speed": "math.random(2, 4)",
        "minecraft:particle_lifetime_expression": life(0.9, 1.5),
        "minecraft:particle_motion_dynamic": motion(rise=0.8, drag=2.5),
        **steam_look(0.3, 1.2, 0.85, start=(1.0, 0.25, 0.15), row="billow"),
    })
    P["joki:ember"] = particle("joki:ember", {
        **once(10),
        "minecraft:emitter_shape_sphere": {"radius": 0.4, "direction": "outwards"},
        "minecraft:particle_initial_speed": "math.random(1, 2.5)",
        "minecraft:particle_lifetime_expression": life(0.5, 1.0),
        "minecraft:particle_motion_dynamic": motion(rise=1.5, drag=1.5),
        "minecraft:particle_appearance_billboard": {"size": ["0.09 + variable.particle_random_2 * 0.06", "0.09 + variable.particle_random_2 * 0.06"],
                                                    "facing_camera_mode": "rotate_xyz", "uv": uv_cell("ember")},
        "minecraft:particle_appearance_tinting": {"color": [1.0, "0.55 + variable.particle_random_4 * 0.3", 0.2, f"1.0 - {AGE}"]},
    }, material="particles_add")
    P["joki:cool_wisp"] = particle("joki:cool_wisp", {
        **once(3),
        "minecraft:emitter_shape_sphere": {"radius": 0.35, "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "math.random(0.4, 0.8)",
        "minecraft:particle_lifetime_expression": life(1.2, 1.8),
        "minecraft:particle_motion_dynamic": motion(rise=0.4, drag=1.0),
        "minecraft:particle_appearance_billboard": {"size": [grow(0.15, 0.3), grow(0.4, 0.8)], "facing_camera_mode": "lookat_y",
                                                    "uv": {"texture_width": A, "texture_height": A,
                                                           "uv": ["variable.particle_random_3 < 0.5 ? 32 : 64", 96], "uv_size": [C, C]}},
        "minecraft:particle_appearance_tinting": tint(STEAM, STEAM, 0.55, 0.15),
    })
    return P


# Body vent points in entity-local space (x: side, y: height, z: forward*FORWARD)
SIDE = "(variable.particle_random_2 < 0.5 ? -1.0 : 1.0)"


def body_vents(points):
    """Pick one vent per particle from `points` [(x, y, z, dx, dy, dz)], mirrored left/right."""
    n = len(points)
    sel = "variable.particle_random_1"

    def pick(idx):
        expr = None
        for i in range(n - 1, -1, -1):
            val = points[i][idx]
            term = f"{SIDE} * {val}" if idx in (0, 3) else (f"{val * FORWARD}" if idx in (2, 5) else f"{val}")
            if expr is None:
                expr = term
            else:
                expr = f"({sel} < {round((i + 1) / n, 4)} ? {term} : {expr})"
        return expr

    return {"offset": [pick(0), pick(1), pick(2)], "direction": [pick(3) + " + math.random(-0.15, 0.15)", pick(4), pick(5) + " + math.random(-0.15, 0.15)"]}


SHOULDER = (0.42, 1.38, -0.02, 0.6, 1.0, -0.35)
ARM = (0.47, 1.0, 0.0, 1.0, 0.25, -0.2)
BACK = (0.13, 1.18, -0.2, 0.15, 0.55, -1.0)
LEG = (0.16, 0.38, -0.05, 0.55, -0.15, -0.55)
HIP = (0.22, 0.8, -0.12, 0.6, 0.2, -0.6)


def vent(ident, points, rate, speed, size0, size1, peak, life_rng, rise=0.8, drag=2.5, start=WARM, maxp=None):
    return particle(ident, {
        **looping(rate, maxp or int(rate * life_rng[1] * 1.3) + 4),
        "minecraft:emitter_shape_point": body_vents(points),
        "minecraft:particle_initial_speed": f"math.random({speed[0]}, {speed[1]})",
        "minecraft:particle_lifetime_expression": life(*life_rng),
        "minecraft:particle_motion_dynamic": motion(rise=rise, drag=drag),
        **jet_look(size0, size1, size0 * 0.55, size1 * 0.75, peak=peak, start=start, cell="streak"),
    })


def cylinder_steam(ident, rate, y_rng, radius, speed, size0, size1, peak, life_rng, rise, start=STEAM, row="puff", maxp=None, swirl=0.0, out=0.4):
    ang = "variable.particle_random_2 * 360"
    return particle(ident, {
        **looping(rate, maxp or int(rate * life_rng[1] * 1.3) + 4),
        "minecraft:emitter_shape_point": {
            "offset": [f"math.cos({ang}) * {radius}", f"math.random({y_rng[0]}, {y_rng[1]})", f"math.sin({ang}) * {radius}"],
            "direction": [f"math.cos({ang}) * {out} - math.sin({ang}) * {swirl}", "1.0", f"math.sin({ang}) * {out} + math.cos({ang}) * {swirl}"],
        },
        "minecraft:particle_initial_speed": f"math.random({speed[0]}, {speed[1]})",
        "minecraft:particle_lifetime_expression": life(*life_rng),
        "minecraft:particle_motion_dynamic": motion(rise=rise, drag=2.0),
        **steam_look(size0, size1, peak, start=start, row=row),
    })


def shimmer(ident, rate, peak):
    ang = "variable.particle_random_2 * 360"
    return particle(ident, {
        **looping(rate, int(rate * 1.6) + 4),
        "minecraft:emitter_shape_point": {
            "offset": [f"math.cos({ang}) * 0.3", "math.random(0.4, 1.6)", f"math.sin({ang}) * 0.3"],
            "direction": [0, 1, 0],
        },
        "minecraft:particle_initial_speed": "math.random(0.3, 0.6)",
        "minecraft:particle_lifetime_expression": life(0.7, 1.2),
        "minecraft:particle_motion_dynamic": motion(rise=0.3, drag=1.0),
        "minecraft:particle_appearance_billboard": {"size": [grow(0.15, 0.25), grow(0.35, 0.6)], "facing_camera_mode": "lookat_y", "uv": uv_cell("shimmer")},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.6, 0.3, alpha_expr(peak, 0.3)]},
    }, material="particles_add")


def ember_loop(ident, rate):
    ang = "variable.particle_random_2 * 360"
    return particle(ident, {
        **looping(rate, int(rate * 1.2) + 4),
        "minecraft:emitter_shape_point": {
            "offset": [f"math.cos({ang}) * 0.35", "math.random(0.3, 1.7)", f"math.sin({ang}) * 0.35"],
            "direction": [f"math.cos({ang})", "1.5", f"math.sin({ang})"],
        },
        "minecraft:particle_initial_speed": "math.random(0.6, 1.4)",
        "minecraft:particle_lifetime_expression": life(0.5, 0.9),
        "minecraft:particle_motion_dynamic": motion(rise=1.0, drag=1.0),
        "minecraft:particle_appearance_billboard": {"size": ["0.07 + variable.particle_random_3 * 0.05", "0.07 + variable.particle_random_3 * 0.05"],
                                                    "facing_camera_mode": "rotate_xyz", "uv": uv_cell("ember")},
        "minecraft:particle_appearance_tinting": {"color": [1.0, "0.5 + variable.particle_random_4 * 0.35", 0.15, f"1.0 - {AGE}"]},
    }, material="particles_add")


def body_particles():
    """Looping emitters bound to the player by the animation controller (client side, follow the body)."""
    B = {}
    # HEAT: small jets at shoulders and arms
    B["joki:vent_heat"] = vent("joki:vent_heat", [SHOULDER, ARM], 9, (1.2, 2.0), 0.25, 0.6, 0.6, (0.35, 0.6))
    B["joki:shimmer"] = shimmer("joki:shimmer", 4, 0.22)
    # PRESSURE: shoulders, arms, back, hips + legs
    B["joki:vent_press_upper"] = vent("joki:vent_press_upper", [SHOULDER, ARM, BACK], 22, (1.8, 3.0), 0.3, 0.9, 0.75, (0.4, 0.7))
    B["joki:vent_press_legs"] = vent("joki:vent_press_legs", [LEG, HIP], 10, (1.4, 2.4), 0.25, 0.7, 0.65, (0.35, 0.6), rise=1.0)
    B["joki:shimmer_press"] = shimmer("joki:shimmer_press", 7, 0.3)
    # REDLINE: big directional jets + surrounding steam + embers
    B["joki:vent_red_jets"] = vent("joki:vent_red_jets", [SHOULDER, BACK, ARM], 32, (3.0, 4.6), 0.4, 1.2, 0.9, (0.4, 0.7), rise=1.0, start=(1.0, 0.5, 0.35))
    B["joki:vent_red_legs"] = vent("joki:vent_red_legs", [LEG, HIP], 16, (2.2, 3.4), 0.3, 0.9, 0.8, (0.35, 0.65), rise=1.0, start=(1.0, 0.5, 0.35))
    B["joki:vent_red_swirl"] = cylinder_steam("joki:vent_red_swirl", 18, (0.1, 1.8), 0.7, (0.6, 1.1), 0.5, 1.2, 0.5, (0.9, 1.4), rise=0.5, swirl=1.2, out=0.2)
    B["joki:embers"] = ember_loop("joki:embers", 7)
    # OVERHEAT: violent venting from the whole body
    B["joki:vent_over"] = cylinder_steam("joki:vent_over", 45, (0.2, 1.8), 0.35, (2.0, 3.5), 0.4, 1.4, 0.8, (0.8, 1.2), rise=1.5, start=WARM, row="billow", maxp=70)
    B["joki:over_embers"] = ember_loop("joki:over_embers", 10)
    # First person: soft steam rising from the lower body only (never in front of the eyes)
    for key, rate, peak in (("heat", 4, 0.35), ("press", 8, 0.4), ("red", 14, 0.45), ("over", 20, 0.5)):
        B[f"joki:fp_{key}"] = cylinder_steam(f"joki:fp_{key}", rate, (0.2, 0.9), 0.5, (0.3, 0.6), 0.25, 0.7, peak, (0.7, 1.1), rise=0.6,
                                             start=WARM if key != "heat" else STEAM)
    return B


# Animation-controller state -> looping effects (short names are registered in player.entity.json)
STATE_FX = {
    "heat_tp": ["vent_heat", "shimmer"],
    "pressure_tp": ["vent_press_upper", "vent_press_legs", "shimmer_press"],
    "redline_tp": ["vent_red_jets", "vent_red_legs", "vent_red_swirl", "embers"],
    "overheat_tp": ["vent_over", "over_embers"],
    "heat_fp": ["fp_heat"],
    "pressure_fp": ["fp_press"],
    "redline_fp": ["fp_red"],
    "overheat_fp": ["fp_over"],
}
STATE_KEY = {  # value of variable.joki_fx_key for each state
    "off": 0, "heat_tp": 2, "heat_fp": 3, "pressure_tp": 4, "pressure_fp": 5,
    "redline_tp": 6, "redline_fp": 7, "overheat_tp": 8, "overheat_fp": 9,
}


def build_particles():
    allp = {**server_particles(), **body_particles()}
    for ident, data in allp.items():
        write_json(os.path.join(RP, "particles", "joki", ident.split(":")[1] + ".json"), data)
    return allp


# --------------------------------------------------------------------------- player client entity

PRE_ANIMATION = [
    "variable.joki_mode = query.has_property('joki:mode') ? query.property('joki:mode') : 0;",
    "variable.joki_heat = query.has_property('joki:heat') ? query.property('joki:heat') : 0;",
    "variable.joki_over = query.has_property('joki:overheat') ? query.property('joki:overheat') : 0;",
    # target glow: per gear, pulsing faster the hotter the gear, plus residual heat
    "variable.joki_target = variable.joki_mode <= 0 ? 0.0 : (variable.joki_over ? 0.5 + math.sin(query.life_time * 900.0) * 0.14 : "
    "(variable.joki_mode == 4 ? 0.6 + math.sin(query.life_time * 720.0) * 0.08 : "
    "(variable.joki_mode == 3 ? 0.42 + math.sin(query.life_time * 360.0) * 0.05 : "
    "(variable.joki_mode == 2 ? 0.25 + math.sin(query.life_time * 180.0) * 0.03 : 0.0))) + variable.joki_heat * 0.012);",
    # smooth transition (about 0.3s time constant), frame-rate independent
    "variable.joki_glow = (variable.joki_glow ?? 0.0) + (variable.joki_target - (variable.joki_glow ?? 0.0)) * math.clamp(query.delta_time * 3.5, 0.0, 1.0);",
    # particle state key: 0 off, 2/3 heat, 4/5 pressure, 6/7 redline, 8/9 overheat (odd = first person)
    "variable.joki_fx_key = (query.is_alive && !query.is_spectator && variable.joki_mode > 0) ? "
    "((variable.joki_over ? 8 : (variable.joki_mode >= 2 ? variable.joki_mode * 2 - 2 : 0)) + "
    "((variable.joki_over || variable.joki_mode >= 2) && variable.is_first_person ? 1 : 0)) : 0;",
]

GLOW_OVERLAY = {
    "r": "variable.joki_glow > 0.01 ? 1.0 : this",
    "g": "variable.joki_glow > 0.01 ? 0.1 + variable.joki_glow * 0.12 : this",
    "b": "variable.joki_glow > 0.01 ? 0.04 : this",
    "a": "variable.joki_glow > 0.01 ? math.max(this, variable.joki_glow) : this",
}

RC_SWAP = {
    "controller.render.player.third_person": "controller.render.joki.player.third_person",
    "controller.render.player.first_person": "controller.render.joki.player.first_person",
}


def build_player_rp():
    van_rc = load_json(os.path.join(HERE, "vanilla", "player.render_controllers.json"))["render_controllers"]
    rcs = {}
    for vname, jname in RC_SWAP.items():
        rc = copy.deepcopy(van_rc[vname])
        rc["overlay_color"] = GLOW_OVERLAY
        rcs[jname] = rc
    write_json(os.path.join(RP, "render_controllers", "joki_player.render_controllers.json"),
               {"format_version": "1.8.0", "render_controllers": rcs})

    pe = load_json(os.path.join(HERE, "vanilla", "player.entity.json"))
    desc = pe["minecraft:client_entity"]["description"]
    desc["scripts"]["initialize"] = desc["scripts"].get("initialize", []) + ["variable.joki_glow = 0.0;", "variable.joki_fx_key = 0;"]
    desc["scripts"]["pre_animation"] = desc["scripts"].get("pre_animation", []) + PRE_ANIMATION
    desc["animations"]["joki_steam"] = "controller.animation.joki.steam"
    desc["scripts"]["animate"].append("joki_steam")
    fx = {}
    for effects in STATE_FX.values():
        for e in effects:
            fx[e] = f"joki:{e}"
    desc["particle_effects"] = {**desc.get("particle_effects", {}), **fx}
    new_rcs = []
    for entry in desc["render_controllers"]:
        name = entry if isinstance(entry, str) else list(entry.keys())[0]
        if name in RC_SWAP:
            new_rcs.append({RC_SWAP[name]: entry[name]} if isinstance(entry, dict) else RC_SWAP[name])
        else:
            new_rcs.append(entry)
    desc["render_controllers"] = new_rcs
    write_json(os.path.join(RP, "entity", "player.entity.json"), pe)

    # steam state machine: each state's looping emitters live exactly as long as the state
    states = {}
    for st, key in STATE_KEY.items():
        s = {"transitions": [{other: f"variable.joki_fx_key == {k}"} for other, k in STATE_KEY.items() if other != st]}
        if st in STATE_FX:
            s["particle_effects"] = [{"effect": e} for e in STATE_FX[st]]
        states[st] = s
    write_json(os.path.join(RP, "animation_controllers", "joki_steam.animation_controllers.json"), {
        "format_version": "1.10.0",
        "animation_controllers": {"controller.animation.joki.steam": {"initial_state": "off", "states": states}},
    })


# --------------------------------------------------------------------------- player animations (playAnimation)


def tp(value):
    """Third-person only: the first-person arm/item is left to vanilla."""
    return value if value == 0 else f"variable.is_first_person ? 0 : {value}"


def kf(frames):
    """{time: (x, y, z)} -> keyframes with catmull-rom smoothing."""
    return {f"{t:.2f}": {"post": [tp(c) for c in rot], "lerp_mode": "catmullrom"} for t, rot in frames.items()}


def player_anim(length, bones):
    return {"animation_length": length, "loop": False, "bones": {b: {"rotation": kf(fr)} for b, fr in bones.items()}}


def build_player_animations():
    z = (0, 0, 0)
    anims = {
        # right straight: wind-up, thrust, hold, recover
        "animation.joki.player.knuckle": player_anim(0.45, {
            "rightArm": {0.0: z, 0.08: (35, 0, -15), 0.14: (-95, 5, -5), 0.26: (-92, 5, -5), 0.45: z},
            "leftArm": {0.0: z, 0.14: (30, 0, 10), 0.45: z},
            "body": {0.0: z, 0.08: (0, 25, 0), 0.14: (8, -20, 0), 0.26: (8, -18, 0), 0.45: z},
        }),
        # front kick with the right leg
        "animation.joki.player.kick": player_anim(0.5, {
            "rightLeg": {0.0: z, 0.06: (30, 0, 0), 0.15: (-85, 0, 0), 0.3: (-80, 0, 0), 0.5: z},
            "leftLeg": {0.0: z, 0.15: (10, 0, 0), 0.5: z},
            "body": {0.0: z, 0.15: (-12, 0, 0), 0.3: (-10, 0, 0), 0.5: z},
            "rightArm": {0.0: z, 0.15: (-30, 0, -35), 0.5: z},
            "leftArm": {0.0: z, 0.15: (-30, 0, 35), 0.5: z},
        }),
        # arm extended forward like a cannon barrel
        "animation.joki.player.cannon": player_anim(0.5, {
            "rightArm": {0.0: z, 0.05: (-90, 0, 0), 0.35: (-88, 0, 0), 0.5: z},
            "leftArm": {0.0: z, 0.05: (-25, 0, 10), 0.5: z},
            "body": {0.0: z, 0.05: (0, -10, 0), 0.35: (0, -10, 0), 0.5: z},
        }),
        # Scald Burst: arms flung outward
        "animation.joki.player.burst": player_anim(0.6, {
            "rightArm": {0.0: z, 0.06: (20, 0, 15), 0.14: (-20, 0, -80), 0.35: (-15, 0, -75), 0.6: z},
            "leftArm": {0.0: z, 0.06: (20, 0, -15), 0.14: (-20, 0, 80), 0.35: (-15, 0, 75), 0.6: z},
            "body": {0.0: z, 0.06: (12, 0, 0), 0.14: (-8, 0, 0), 0.6: z},
            "head": {0.0: z, 0.14: (-15, 0, 0), 0.6: z},
        }),
        # Redline ignition: hunch and clench, then explode outward
        "animation.joki.player.ignite": player_anim(0.9, {
            "rightArm": {0.0: z, 0.3: (20, 0, 25), 0.65: (25, 0, 28), 0.75: (-40, 0, -85), 0.9: z},
            "leftArm": {0.0: z, 0.3: (20, 0, -25), 0.65: (25, 0, -28), 0.75: (-40, 0, 85), 0.9: z},
            "body": {0.0: z, 0.3: (18, 0, 0), 0.65: (20, 0, 0), 0.75: (-10, 0, 0), 0.9: z},
            "head": {0.0: z, 0.3: (15, 0, 0), 0.75: (-25, 0, 0), 0.9: z},
        }),
        # Boiler Jump: arms swept down and back
        "animation.joki.player.jump": player_anim(0.45, {
            "rightArm": {0.0: z, 0.1: (35, 0, -20), 0.45: z},
            "leftArm": {0.0: z, 0.1: (35, 0, 20), 0.45: z},
            "rightLeg": {0.0: z, 0.1: (-15, 0, 0), 0.45: z},
            "leftLeg": {0.0: z, 0.1: (10, 0, 0), 0.45: z},
        }),
        # Pressure Dash: lean into the thrust
        "animation.joki.player.dash": player_anim(0.4, {
            "body": {0.0: z, 0.06: (25, 0, 0), 0.25: (22, 0, 0), 0.4: z},
            "rightArm": {0.0: z, 0.06: (50, 0, -15), 0.25: (45, 0, -15), 0.4: z},
            "leftArm": {0.0: z, 0.06: (50, 0, 15), 0.25: (45, 0, 15), 0.4: z},
        }),
        # Mist Veil: arms spread to release the cloud
        "animation.joki.player.veil": player_anim(0.6, {
            "rightArm": {0.0: z, 0.15: (-60, 0, -40), 0.4: (-55, 0, -45), 0.6: z},
            "leftArm": {0.0: z, 0.15: (-60, 0, 40), 0.4: (-55, 0, 45), 0.6: z},
        }),
        # Steam Boost: pump both fists
        "animation.joki.player.boost": player_anim(0.5, {
            "rightArm": {0.0: z, 0.12: (-35, 0, -10), 0.25: (15, 0, -10), 0.5: z},
            "leftArm": {0.0: z, 0.12: (-35, 0, 10), 0.25: (15, 0, 10), 0.5: z},
            "body": {0.0: z, 0.12: (6, 0, 0), 0.5: z},
        }),
    }
    write_json(os.path.join(RP, "animations", "joki_player.animation.json"), {"format_version": "1.10.0", "animations": anims})
    return anims


# --------------------------------------------------------------------------- behaviour pack: player + items

PROPERTIES = {
    "joki:mode": {"type": "int", "range": [0, 4], "default": 0, "client_sync": True},
    "joki:heat": {"type": "int", "range": [0, 10], "default": 0, "client_sync": True},
    "joki:overheat": {"type": "bool", "default": False, "client_sync": True},
}


def build_bp():
    pl = load_json(os.path.join(HERE, "vanilla", "player.json"))
    pl["minecraft:entity"]["description"]["properties"] = PROPERTIES
    write_json(os.path.join(BP, "entities", "player.json"), pl)

    fruit = {
        "format_version": "1.21.60",
        "minecraft:item": {
            "description": {"identifier": "joki:joki_fruit", "menu_category": {"category": "equipment"}},
            "components": {
                "minecraft:icon": {"textures": {"default": "joki_fruit"}},
                "minecraft:display_name": {"value": "item.joki:joki_fruit.name"},
                "minecraft:max_stack_size": 16,
                "minecraft:food": {"nutrition": 4, "saturation_modifier": 0.6, "can_always_eat": True},
                "minecraft:use_animation": "eat",
                "minecraft:use_modifiers": {"use_duration": 1.6, "movement_modifier": 0.35},
                "minecraft:tags": {"tags": ["joki:devil_fruit"]},
            },
        },
    }
    valve = {
        "format_version": "1.21.60",
        "minecraft:item": {
            "description": {"identifier": "joki:steam_valve", "menu_category": {"category": "equipment"}},
            "components": {
                "minecraft:icon": {"textures": {"default": "joki_steam_valve"}},
                "minecraft:display_name": {"value": "item.joki:steam_valve.name"},
                "minecraft:max_stack_size": 1,
                "minecraft:hand_equipped": True,
                "minecraft:glint": True,
                "minecraft:tags": {"tags": ["joki:control"]},
            },
        },
    }
    write_json(os.path.join(BP, "items", "joki_fruit.json"), fruit)
    write_json(os.path.join(BP, "items", "steam_valve.json"), valve)


# --------------------------------------------------------------------------- sounds


def build_sounds():
    table = sounds.build(os.path.join(RP, "sounds", "joki"))
    defs = {}
    for event, stems in table.items():
        _, _, vol = sounds.SOUNDS[event]
        defs[event] = {
            "category": "player",
            "min_distance": 1.0,
            "max_distance": 32.0,
            "sounds": [{"name": f"sounds/joki/{s}", "volume": vol, "load_on_low_memory": True} for s in stems],
        }
    write_json(os.path.join(RP, "sounds", "sound_definitions.json"), {"format_version": "1.20.20", "sound_definitions": defs})
    return defs


# --------------------------------------------------------------------------- language


def build_lang():
    rp = [
        f"pack.name={ADDON_NAME}",
        "pack.description=Original fan-made Paramecia: control body heat and steam pressure. 9 abilities, 4 gears, Overheat.",
        "item.joki:joki_fruit.name=§cJōki Jōki no Mi",
        "item.joki:steam_valve.name=§6Steam Valve",
    ]
    bp = rp[:2]
    write_text(os.path.join(RP, "texts", "en_US.lang"), "\n".join(rp) + "\n")
    write_text(os.path.join(BP, "texts", "en_US.lang"), "\n".join(bp) + "\n")
    for root in (BP, RP):
        write_text(os.path.join(root, "texts", "languages.json"), json.dumps(["en_US"], indent=2) + "\n")


# --------------------------------------------------------------------------- scripts


def build_scripts():
    tsc = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        raise SystemExit("TypeScript not installed: run `npm install` in joki-joki-addon/")
    res = subprocess.run([tsc, "-p", os.path.join(ROOT, "tsconfig.json"), "--outDir", os.path.join(BP, "scripts")],
                         capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout, res.stderr)
        raise SystemExit("TypeScript compilation failed")


# --------------------------------------------------------------------------- packaging


def zip_dir(zf, folder, arc_root):
    for dirpath, dirs, files in os.walk(folder):
        dirs.sort()
        for fn in sorted(files):
            full = os.path.join(dirpath, fn)
            info = zipfile.ZipInfo(os.path.join(arc_root, os.path.relpath(full, folder)).replace(os.sep, "/"), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(full, "rb") as f:
                zf.writestr(info, f.read())


def package():
    os.makedirs(DIST, exist_ok=True)
    addon = os.path.join(DIST, f"{FILE_BASE}.mcaddon")
    with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as zf:
        zip_dir(zf, BP, "Joki_BP")
        zip_dir(zf, RP, "Joki_RP")
    for folder, suffix in ((BP, "BP"), (RP, "RP")):
        with zipfile.ZipFile(os.path.join(DIST, f"{FILE_BASE}_{suffix}.mcpack"), "w", zipfile.ZIP_DEFLATED) as zf:
            zip_dir(zf, folder, "")
    return addon


def main():
    if os.path.exists(BP):
        shutil.rmtree(BP)
    if os.path.exists(RP):
        shutil.rmtree(RP)
    manifests()
    build_textures()
    build_particles()
    build_player_rp()
    build_player_animations()
    build_bp()
    build_sounds()
    build_lang()
    build_scripts()
    addon = package()
    print("built", os.path.relpath(addon, ROOT))


if __name__ == "__main__":
    main()
