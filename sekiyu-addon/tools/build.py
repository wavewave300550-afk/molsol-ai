"""
Build script for "Sekiyu Sekiyu no Mi - Petroleum".

    python3 tools/build.py      -> build/Sekiyu_BP, build/Sekiyu_RP, dist/*.mcaddon + *.mcpack

Generates every pack file (models, textures, attachable, entities, render controllers,
animations, controllers, particles, sounds, fog, items, language, manifests), compiles the
TypeScript and packages the add-on.
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
import fruit_model  # noqa: E402
import models  # noqa: E402
import sounds  # noqa: E402

# The combined "Forbidden Fruits" add-on reuses this script to generate the assets into its own
# build folder (ADDON_BUILD_DIR) and compiles the scripts itself (ADDON_ASSETS_ONLY=1).
BUILD = os.environ.get("ADDON_BUILD_DIR") or os.path.join(ROOT, "build")
ASSETS_ONLY = os.environ.get("ADDON_ASSETS_ONLY") == "1"
BP = os.path.join(BUILD, "Sekiyu_BP")
RP = os.path.join(BUILD, "Sekiyu_RP")
DIST = os.path.join(ROOT, "dist")

ADDON_NAME = "Sekiyu Sekiyu no Mi - Petroleum"
FILE_BASE = "Sekiyu_Sekiyu_no_Mi_Petroleum"
VERSION = [1, 0, 1]
MIN_ENGINE = [1, 26, 60]
SERVER_VERSION = "2.11.0"
SERVER_UI_VERSION = "2.3.0"
UUID = {
    "bp_header": "802929c4-fd97-4467-b779-d21f80e6dcc7",
    "bp_data": "634392d0-7fde-48a8-bab3-c9d33ff9b05a",
    "bp_script": "d211dd40-30c9-4f98-b416-c83feff99570",
    "rp_header": "218d4ee4-b987-45e1-aa30-0110024463b6",
    "rp_res": "01113aa7-47da-4e9e-8538-8f9717a5d489",
}
# Entity-local +Z is assumed to be the facing direction for player-bound particle emitters.
FORWARD = 1.0

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


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_png(img, rel):
    p = os.path.join(RP, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    img.save(p)


# --------------------------------------------------------------------------- manifests


def manifests():
    meta = {"authors": ["Sekiyu Sekiyu no Mi add-on (fan-made)"], "product_type": "addon"}
    bp = {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["bp_header"], "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [
            {"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
            {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION, "entry": "scripts/main.js"},
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
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["rp_header"], "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
        "dependencies": [{"uuid": UUID["bp_header"], "version": VERSION}],
        "metadata": meta,
    }
    write_json(os.path.join(BP, "manifest.json"), bp)
    write_json(os.path.join(RP, "manifest.json"), rp)
    icon = fruit_icon.pack_icon()
    for p in (BP, RP):
        icon.save(os.path.join(p, "pack_icon.png"))


# --------------------------------------------------------------------------- models & textures

GEO = {}  # name -> (geometry identifier, normal texture path, burning texture path)


def build_models():
    # held fruit (attachable, bound to the hand) + the same model for the awakening relic
    fm = fruit_model.build(binding=True, identifier="geometry.sekiyu.fruit")
    tex = fm.paint()
    write_json(os.path.join(RP, "models", "entity", "sekiyu", "fruit.geo.json"), fm.geometry(bounds=(3, 3), offset=(0, 1, 0)))
    save_png(tex, "textures/entity/sekiyu/fruit.png")
    rm = fruit_model.build(binding=False, identifier="geometry.sekiyu.fruit_relic")
    rm.paint()
    write_json(os.path.join(RP, "models", "entity", "sekiyu", "fruit_relic.geo.json"), rm.geometry(bounds=(3, 3), offset=(0, 1, 0)))
    GEO["fruit"] = ("geometry.sekiyu.fruit", "textures/entity/sekiyu/fruit", None)
    GEO["relic"] = ("geometry.sekiyu.fruit_relic", "textures/entity/sekiyu/fruit", None)
    bounds = {"oil_body": ((3, 3), (0, 1, 0)), "puddle": ((3, 1), (0, 0.5, 0)), "serpent": ((14, 6), (0, 2, 0)), "tide": ((10, 6), (0, 2, 0)),
              "prison": ((5, 4), (0, 1.5, 0)), "pool": ((14, 2), (0, 0.5, 0)), "geyser": ((5, 10), (0, 4, 0))}
    for name, fn in models.ALL.items():
        m = fn()
        normal, burning = models.painted_twice(m)
        b, off = bounds[name]
        write_json(os.path.join(RP, "models", "entity", "sekiyu", f"{name}.geo.json"), m.geometry(bounds=b, offset=off))
        save_png(normal, f"textures/entity/sekiyu/{name}.png")
        save_png(burning, f"textures/entity/sekiyu/{name}_burning.png")
        GEO[name] = (m.identifier, f"textures/entity/sekiyu/{name}", f"textures/entity/sekiyu/{name}_burning")
    # pool scale reference: the model's radius at scale 1 (blocks)
    pm = models.pool()
    xs = [abs(c.origin[0] + s) for b in pm.bones for c in b.cubes for s in (0, c.size[0])]
    GEO["pool_radius"] = max(xs) / 16.0


def build_2d():
    save_png(fruit_icon.fruit_icon(128), "textures/items/sekiyu/sekiyu_fruit.png")
    save_png(art.core_icon(32), "textures/items/sekiyu/crude_core.png")
    save_png(art.particle_atlas(), "textures/particle/sekiyu_oil.png")
    for name in art.UI_ICONS:
        save_png(art.ui_icon(name), f"textures/sekiyu/ui/{name}.png")
    write_json(os.path.join(RP, "textures", "item_texture.json"), {
        "resource_pack_name": "sekiyu",
        "texture_name": "atlas.items",
        "texture_data": {
            "sekiyu_fruit": {"textures": "textures/items/sekiyu/sekiyu_fruit"},
            "sekiyu_crude_core": {"textures": "textures/items/sekiyu/crude_core"},
        },
    })


# --------------------------------------------------------------------------- particles

TEX = "textures/particle/sekiyu_oil"
A, C = art.ATLAS, art.CELL
AGE = "(variable.particle_age / variable.particle_lifetime)"
DIR = "variable.direction"
POWER = "(variable.power ?? 1.0)"
RADIUS = "(variable.radius ?? 1.5)"


def cell(name):
    c, r = art.ATLAS_CELLS[name]
    return [c * C, r * C]


def uv_row(row):
    _, r = art.ATLAS_CELLS[row + "0"]
    return {"texture_width": A, "texture_height": A, "uv": ["math.floor(variable.particle_random_3 * 3.99) * 32", r * C], "uv_size": [C, C]}


def uv_cell(name):
    return {"texture_width": A, "texture_height": A, "uv": cell(name), "uv_size": [C, C]}


FLAME_UV = {"texture_width": A, "texture_height": A,
            "flipbook": {"base_UV": cell("flame0"), "size_UV": [C, C], "step_UV": [C, 0], "frames_per_second": 14, "max_frame": 4, "loop": True}}


def life(lo, hi):
    return {"max_lifetime": f"{lo} + variable.particle_random_1 * {round(hi - lo, 3)}"}


def motion(rise=0.0, drag=1.5, gravity=0.0):
    return {"linear_acceleration": [0, rise - gravity, 0], "linear_drag_coefficient": drag}


def once(n):
    return {"minecraft:emitter_rate_instant": {"num_particles": n}, "minecraft:emitter_lifetime_once": {"active_time": 0.05}}


def looping(rate, maxp):
    return {"minecraft:emitter_rate_steady": {"spawn_rate": rate, "max_particles": maxp},
            "minecraft:emitter_lifetime_looping": {"active_time": 1.0},
            "minecraft:emitter_local_space": {"position": True, "rotation": True}}


def grow(a, b, pw=0.7):
    return f"{a} + ({b} - {a}) * math.pow({AGE}, {pw})"


def part(ident, comps, material):
    return {"format_version": "1.10.0", "particle_effect": {
        "description": {"identifier": ident, "basic_render_parameters": {"material": material, "texture": TEX}}, "components": comps}}


def droplets(size=(0.08, 0.16), shrink=True):
    s = f"({size[0]} + variable.particle_random_2 * {round(size[1] - size[0], 3)})" + (f" * (1 - {AGE} * 0.4)" if shrink else "")
    return {"minecraft:particle_appearance_billboard": {"size": [s, s], "facing_camera_mode": "rotate_xyz", "uv": uv_row("drop")},
            "minecraft:particle_appearance_lighting": {}}


def collide(r=0.05):
    return {"minecraft:particle_motion_collision": {"collision_radius": r, "coefficient_of_restitution": 0.05, "collision_drag": 6.0}}


def flames(size=(0.3, 0.6), peak=1.0):
    s = f"({size[0]} + variable.particle_random_2 * {round(size[1] - size[0], 3)}) * (1 - {AGE} * 0.5)"
    return {"minecraft:particle_appearance_billboard": {"size": [s, f"{s} * 1.3"], "facing_camera_mode": "lookat_y", "uv": FLAME_UV},
            "minecraft:particle_appearance_tinting": {"color": [1, 1, 1, f"(1 - {AGE}) * {peak}"]}}


def smoke_look(s0, s1, peak=0.85):
    return {"minecraft:particle_appearance_billboard": {"size": [grow(s0, s1), grow(s0, s1)], "facing_camera_mode": "rotate_xyz", "uv": uv_row("smoke")},
            "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-30, 30)"},
            "minecraft:particle_appearance_tinting": {"color": [1, 1, 1, f"math.min({AGE} * 6, 1) * (1 - {AGE}) * {peak}"]}}


def directed_dir(spread, up=0.0):
    return [f"({DIR}.x ?? 0) + math.random(-{spread}, {spread})", f"({DIR}.y ?? 1) + {up} + math.random(-{spread}, {spread})",
            f"({DIR}.z ?? 0) + math.random(-{spread}, {spread})"]


def server_particles():
    P = {}
    G = 16.0  # oil is heavy: strong gravity for droplets
    P["sekiyu:oil_splash"] = part("sekiyu:oil_splash", {
        **once(18), "minecraft:emitter_shape_sphere": {"radius": 0.25, "direction": ["math.random(-1,1)", "math.random(0.4,1.4)", "math.random(-1,1)"]},
        "minecraft:particle_initial_speed": "math.random(2.5, 5.5)", "minecraft:particle_lifetime_expression": life(0.6, 1.0),
        "minecraft:particle_motion_dynamic": motion(gravity=G, drag=0.6), **collide(), **droplets()}, "particles_alpha")
    P["sekiyu:oil_spray"] = part("sekiyu:oil_spray", {
        **once(10), "minecraft:emitter_shape_point": {"direction": directed_dir(0.25, 0.2)},
        "minecraft:particle_initial_speed": f"math.random(5, 8) * {POWER}", "minecraft:particle_lifetime_expression": life(0.4, 0.8),
        "minecraft:particle_motion_dynamic": motion(gravity=G, drag=1.0), **collide(), **droplets((0.07, 0.14))}, "particles_alpha")
    P["sekiyu:oil_drip"] = part("sekiyu:oil_drip", {
        **once(7), "minecraft:emitter_shape_sphere": {"radius": 0.45, "direction": [0, -1, 0]},
        "minecraft:particle_initial_speed": 0.3, "minecraft:particle_lifetime_expression": life(0.6, 1.0),
        "minecraft:particle_motion_dynamic": motion(gravity=10, drag=0.5), **collide(), **droplets((0.07, 0.12), shrink=False)}, "particles_alpha")
    P["sekiyu:oil_ring"] = part("sekiyu:oil_ring", {
        **once(26), "minecraft:emitter_shape_disc": {"radius": 0.3, "plane_normal": [0, 1, 0], "direction": "outwards"},
        "minecraft:particle_initial_speed": f"{RADIUS} * 2.8", "minecraft:particle_lifetime_expression": life(0.5, 0.8),
        "minecraft:particle_motion_dynamic": motion(gravity=8, drag=2.2), **collide(), **droplets((0.09, 0.18))}, "particles_alpha")
    P["sekiyu:oil_column"] = part("sekiyu:oil_column", {
        **once(40), "minecraft:emitter_shape_disc": {"radius": 0.5, "plane_normal": [0, 1, 0], "direction": ["math.random(-0.25,0.25)", 1, "math.random(-0.25,0.25)"]},
        "minecraft:particle_initial_speed": "math.random(9, 15)", "minecraft:particle_lifetime_expression": life(1.1, 1.7),
        "minecraft:particle_motion_dynamic": motion(gravity=G, drag=0.4), **collide(), **droplets((0.1, 0.22))}, "particles_alpha")
    P["sekiyu:oil_bubble"] = part("sekiyu:oil_bubble", {
        **once(3), "minecraft:emitter_shape_disc": {"radius": 0.6, "plane_normal": [0, 1, 0], "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": 0.15, "minecraft:particle_lifetime_expression": life(0.4, 0.7),
        "minecraft:particle_motion_dynamic": motion(rise=0.4, drag=2),
        "minecraft:particle_appearance_billboard": {"size": [grow(0.05, 0.22), grow(0.05, 0.22)], "facing_camera_mode": "rotate_xyz", "uv": uv_cell("bubble")},
        "minecraft:particle_appearance_lighting": {}}, "particles_blend")
    P["sekiyu:oil_trail"] = part("sekiyu:oil_trail", {
        **once(3), "minecraft:emitter_shape_disc": {"radius": 0.35, "plane_normal": [0, 1, 0], "direction": "outwards"},
        "minecraft:particle_initial_speed": 0.3, "minecraft:particle_lifetime_expression": life(1.0, 1.6),
        "minecraft:particle_motion_dynamic": motion(gravity=6, drag=3), **collide(0.03), **droplets((0.1, 0.18), shrink=False)}, "particles_alpha")
    P["sekiyu:tar_rise"] = part("sekiyu:tar_rise", {
        **once(12), "minecraft:emitter_shape_disc": {"radius": 1.1, "plane_normal": [0, 1, 0], "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "math.random(2, 4)", "minecraft:particle_lifetime_expression": life(0.7, 1.1),
        "minecraft:particle_motion_dynamic": motion(gravity=5, drag=1), **droplets((0.12, 0.2))}, "particles_alpha")
    P["sekiyu:dissolve"] = part("sekiyu:dissolve", {
        **once(22), "minecraft:emitter_shape_box": {"offset": [0, 1.0, 0], "half_dimensions": [0.35, 0.9, 0.35], "direction": [0, -1, 0]},
        "minecraft:particle_initial_speed": "math.random(0.5, 2)", "minecraft:particle_lifetime_expression": life(0.4, 0.7),
        "minecraft:particle_motion_dynamic": motion(gravity=12, drag=0.5), **collide(), **droplets((0.1, 0.2))}, "particles_alpha")
    P["sekiyu:reform"] = part("sekiyu:reform", {
        **once(24), "minecraft:emitter_shape_disc": {"radius": 0.7, "plane_normal": [0, 1, 0], "direction": ["-math.random(0.2,0.5)", 1, "math.random(-0.2,0.2)"]},
        "minecraft:particle_initial_speed": "math.random(3, 6)", "minecraft:particle_lifetime_expression": life(0.4, 0.7),
        "minecraft:particle_motion_dynamic": motion(gravity=10, drag=1), **droplets((0.1, 0.18))}, "particles_alpha")
    P["sekiyu:logia_splash"] = part("sekiyu:logia_splash", {
        **once(20), "minecraft:emitter_shape_box": {"offset": [0, 0, 0], "half_dimensions": [0.3, 0.6, 0.3], "direction": "outwards"},
        "minecraft:particle_initial_speed": "math.random(2, 5)", "minecraft:particle_lifetime_expression": life(0.4, 0.8),
        "minecraft:particle_motion_dynamic": motion(gravity=G, drag=1), **collide(), **droplets((0.08, 0.16))}, "particles_alpha")
    # fire
    P["sekiyu:fire_burst"] = part("sekiyu:fire_burst", {
        **once(18), "minecraft:emitter_shape_sphere": {"radius": 0.5, "direction": [f"({DIR}.x ?? 0) * 0.8 + math.random(-0.5,0.5)", "math.random(0.5, 1.5)", f"({DIR}.z ?? 0) * 0.8 + math.random(-0.5,0.5)"]},
        "minecraft:particle_initial_speed": f"math.random(1, 2.5) * {POWER}", "minecraft:particle_lifetime_expression": life(0.4, 0.8),
        "minecraft:particle_motion_dynamic": motion(rise=2.0, drag=2), **flames()}, "particles_add")
    P["sekiyu:fire_ring"] = part("sekiyu:fire_ring", {
        "minecraft:emitter_rate_instant": {"num_particles": f"12 + {RADIUS} * 4"}, "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_disc": {"radius": RADIUS, "plane_normal": [0, 1, 0], "surface_only": True, "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "math.random(1, 2.5)", "minecraft:particle_lifetime_expression": life(0.6, 1.0),
        "minecraft:particle_motion_dynamic": motion(rise=1.5, drag=1.5), **flames((0.5, 0.9))}, "particles_add")
    P["sekiyu:fire_column"] = part("sekiyu:fire_column", {
        **once(30), "minecraft:emitter_shape_disc": {"radius": 0.6, "plane_normal": [0, 1, 0], "direction": ["math.random(-0.2,0.2)", 1, "math.random(-0.2,0.2)"]},
        "minecraft:particle_initial_speed": "math.random(5, 10)", "minecraft:particle_lifetime_expression": life(0.5, 0.9),
        "minecraft:particle_motion_dynamic": motion(rise=2, drag=2.5), **flames((0.5, 1.0))}, "particles_add")
    P["sekiyu:pool_fire"] = part("sekiyu:pool_fire", {
        "minecraft:emitter_rate_instant": {"num_particles": f"4 + {RADIUS} * 3"}, "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_disc": {"radius": f"{RADIUS} * 0.85", "plane_normal": [0, 1, 0], "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "math.random(0.3, 1.0)", "minecraft:particle_lifetime_expression": life(0.5, 0.9),
        "minecraft:particle_motion_dynamic": motion(rise=1.6, drag=1.5), **flames((0.45, 0.85))}, "particles_add")
    P["sekiyu:black_smoke"] = part("sekiyu:black_smoke", {
        **once(7), "minecraft:emitter_shape_sphere": {"radius": 0.6, "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "math.random(0.5, 1.2)", "minecraft:particle_lifetime_expression": life(2.0, 3.0),
        "minecraft:particle_motion_dynamic": motion(rise=0.5, drag=0.8), **smoke_look(0.6, 2.4)}, "particles_blend")
    P["sekiyu:embers"] = part("sekiyu:embers", {
        **once(16), "minecraft:emitter_shape_sphere": {"radius": 1.0, "direction": "outwards"},
        "minecraft:particle_initial_speed": "math.random(1, 3)", "minecraft:particle_lifetime_expression": life(0.6, 1.2),
        "minecraft:particle_motion_dynamic": motion(rise=2, drag=1),
        "minecraft:particle_appearance_billboard": {"size": ["0.08 + variable.particle_random_2 * 0.06", "0.08 + variable.particle_random_2 * 0.06"], "facing_camera_mode": "rotate_xyz", "uv": uv_cell("ember")},
        "minecraft:particle_appearance_tinting": {"color": [1, "0.5 + variable.particle_random_4 * 0.4", 0.2, f"1 - {AGE}"]}}, "particles_add")
    P["sekiyu:ignite_flash"] = part("sekiyu:ignite_flash", {
        **once(1), "minecraft:emitter_shape_point": {}, "minecraft:particle_initial_speed": 0,
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.25},
        "minecraft:particle_appearance_billboard": {"size": [grow(1.0, 3.2, 0.5), grow(1.0, 3.2, 0.5)], "facing_camera_mode": "rotate_xyz", "uv": uv_cell("flash")},
        "minecraft:particle_appearance_tinting": {"color": [1, 0.75, 0.4, f"1 - {AGE}"]}}, "particles_add")
    # held fruit: subtle heated vapour (attachable timeline)
    P["sekiyu:fruit_vapor"] = part("sekiyu:fruit_vapor", {
        **once(1), "minecraft:emitter_shape_sphere": {"radius": 0.05, "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": 0.25, "minecraft:particle_lifetime_expression": life(0.8, 1.3),
        "minecraft:particle_motion_dynamic": motion(rise=0.4, drag=1.2), **smoke_look(0.08, 0.3, 0.35)}, "particles_blend")
    return P


def bound_flames(ident, offset, half, rate):
    return part(ident, {
        **looping(rate, int(rate * 1.1) + 4), "minecraft:emitter_shape_box": {"offset": offset, "half_dimensions": half, "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "math.random(0.4, 1.2)", "minecraft:particle_lifetime_expression": life(0.4, 0.8),
        "minecraft:particle_motion_dynamic": motion(rise=1.8, drag=1.5), **flames((0.4, 0.8))}, "particles_add")


def bound_drips(ident, offset, half, rate):
    return part(ident, {
        **looping(rate, int(rate * 1.2) + 4), "minecraft:emitter_shape_box": {"offset": offset, "half_dimensions": half, "direction": [0, -1, 0]},
        "minecraft:particle_initial_speed": 0.2, "minecraft:particle_lifetime_expression": life(0.5, 0.9),
        "minecraft:particle_motion_dynamic": motion(gravity=10, drag=0.5), **droplets((0.07, 0.13), shrink=False)}, "particles_alpha")


def bound_particles():
    B = {}
    B["sekiyu:body_drips"] = part("sekiyu:body_drips", {
        **looping(9, 14),
        "minecraft:emitter_shape_point": {
            "offset": ["(variable.particle_random_2 < 0.5 ? -1 : 1) * (variable.particle_random_1 < 0.5 ? 0.38 : 0.25)",
                       "variable.particle_random_1 < 0.5 ? 0.78 : (variable.particle_random_1 < 0.8 ? 1.55 : 0.1)",
                       f"{0.05 * FORWARD}"],
            "direction": [0, -1, 0]},
        "minecraft:particle_initial_speed": 0.2, "minecraft:particle_lifetime_expression": life(0.5, 0.8),
        "minecraft:particle_motion_dynamic": motion(gravity=10, drag=0.5), **droplets((0.06, 0.11), shrink=False)}, "particles_alpha")
    B["sekiyu:body_flames"] = bound_flames("sekiyu:body_flames", [0, 1.0, 0], [0.35, 0.9, 0.25], 22)
    B["sekiyu:puddle_bubbles"] = part("sekiyu:puddle_bubbles", {
        **looping(5, 8), "minecraft:emitter_shape_disc": {"radius": 0.55, "plane_normal": [0, 1, 0], "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": 0.1, "minecraft:particle_lifetime_expression": life(0.4, 0.7),
        "minecraft:particle_motion_dynamic": motion(rise=0.3, drag=2),
        "minecraft:particle_appearance_billboard": {"size": [grow(0.05, 0.18), grow(0.05, 0.18)], "facing_camera_mode": "rotate_xyz", "uv": uv_cell("bubble")},
        "minecraft:particle_appearance_lighting": {}}, "particles_blend")
    B["sekiyu:tide_flames"] = bound_flames("sekiyu:tide_flames", [0, 2.2, 0], [3.0, 1.4, 0.8], 40)
    B["sekiyu:tide_drips"] = bound_drips("sekiyu:tide_drips", [0, 3.0, -0.6 * FORWARD], [2.8, 0.2, 0.3], 12)
    B["sekiyu:serpent_flames"] = bound_flames("sekiyu:serpent_flames", [0, 1.4, 2.5 * FORWARD], [0.55, 0.6, 4.5], 34)
    B["sekiyu:serpent_drips"] = bound_drips("sekiyu:serpent_drips", [0, 1.4, 2.5 * FORWARD], [0.4, 0.3, 4.5], 10)
    B["sekiyu:prison_flames"] = bound_flames("sekiyu:prison_flames", [0, 1.3, 0], [1.2, 1.2, 1.2], 26)
    B["sekiyu:geyser_flames"] = bound_flames("sekiyu:geyser_flames", [0, 3.5, 0], [0.5, 3.3, 0.5], 30)
    B["sekiyu:geyser_drips"] = bound_drips("sekiyu:geyser_drips", [0, 6.5, 0], [0.8, 0.3, 0.8], 14)
    return B


def build_particles():
    allp = {**server_particles(), **bound_particles()}
    for ident, data in allp.items():
        write_json(os.path.join(RP, "particles", "sekiyu", ident.split(":")[1] + ".json"), data)
    return allp


# --------------------------------------------------------------------------- animations helpers


def tp(value):
    return value if value == 0 else f"variable.is_first_person ? 0 : {value}"


def kf(frames, wrap=tp):
    return {f"{t:.2f}": {"post": [wrap(c) for c in rot], "lerp_mode": "catmullrom"} for t, rot in frames.items()}


def clip(length, bones, wrap=tp):
    return {"animation_length": length, "loop": False, "bones": {b: {"rotation": kf(fr, wrap)} for b, fr in bones.items()}}


Z = (0, 0, 0)

# --------------------------------------------------------------------------- player


PRE = [
    "variable.sekiyu_form = query.has_property('sekiyu:form') ? query.property('sekiyu:form') : 0;",
    "variable.sekiyu_burning = query.has_property('sekiyu:burning') ? query.property('sekiyu:burning') : 0;",
    "variable.sekiyu_fx = (query.is_alive && !query.is_spectator) ? (variable.sekiyu_form == 2 ? (variable.is_first_person ? 3 : 2) : (variable.sekiyu_form == 3 ? 4 : 0)) : 0;",
    "variable.sekiyu_fire = (query.is_alive && variable.sekiyu_burning && variable.sekiyu_form > 0 && !variable.is_first_person) ? 1 : 0;",
]
NOT_DISSOLVED = "variable.sekiyu_form != 3"
OIL_TINT = {
    "r": "variable.sekiyu_form == 2 ? (variable.sekiyu_burning ? 1.0 : 0.05) : this",
    "g": "variable.sekiyu_form == 2 ? (variable.sekiyu_burning ? 0.35 : 0.03) : this",
    "b": "variable.sekiyu_form == 2 ? 0.02 : this",
    "a": "variable.sekiyu_form == 2 ? math.max(this, variable.sekiyu_burning ? 0.55 + math.sin(query.life_time * 900) * 0.1 : 0.82) : this",
}
SWAP = {"controller.render.player.third_person": "controller.render.sekiyu.player.third_person",
        "controller.render.player.first_person": "controller.render.sekiyu.player.first_person"}


def tex_array_rc(geo_key, tex_keys, material="Material.sekiyu_oil", cond_var="variable.sekiyu_burning"):
    return {
        "arrays": {"textures": {"Array.skins": tex_keys}},
        "geometry": geo_key,
        "materials": [{"*": material}],
        "textures": [f"Array.skins[{cond_var} ? 1 : 0]"],
    }


def build_player():
    # behaviour pack: vanilla player + synced properties
    pl = load_json(os.path.join(HERE, "vanilla", "player.json"))
    pl["minecraft:entity"]["description"]["properties"] = {
        "sekiyu:form": {"type": "int", "range": [0, 3], "default": 0, "client_sync": True},
        "sekiyu:burning": {"type": "bool", "default": False, "client_sync": True},
    }
    write_json(os.path.join(BP, "entities", "player.json"), pl)

    # render controllers: vanilla copies (+ oily tint, hidden while dissolved) and the overlays
    van = load_json(os.path.join(HERE, "vanilla", "player.render_controllers.json"))["render_controllers"]
    rcs = {}
    for vname, sname in SWAP.items():
        rc = copy.deepcopy(van[vname])
        vis = []
        for entry in rc["part_visibility"]:
            (bone, expr), = entry.items()
            if expr is True:
                vis.append({bone: NOT_DISSOLVED})
            elif expr is False:
                vis.append({bone: False})
            else:
                vis.append({bone: f"({expr}) && {NOT_DISSOLVED}"})
        rc["part_visibility"] = vis
        rc["overlay_color"] = OIL_TINT
        rcs[sname] = rc
    rcs["controller.render.sekiyu.oil_body"] = tex_array_rc("Geometry.sekiyu_oil_body", ["Texture.sekiyu_oil_body", "Texture.sekiyu_oil_body_burning"])
    rcs["controller.render.sekiyu.puddle"] = tex_array_rc("Geometry.sekiyu_puddle", ["Texture.sekiyu_puddle", "Texture.sekiyu_puddle_burning"])
    write_json(os.path.join(RP, "render_controllers", "sekiyu_player.render_controllers.json"), {"format_version": "1.8.0", "render_controllers": rcs})

    pe = load_json(os.path.join(HERE, "vanilla", "player.entity.json"))
    d = pe["minecraft:client_entity"]["description"]
    d["materials"]["sekiyu_oil"] = "entity_emissive"
    for n in ("oil_body", "puddle"):
        gid, tex, burn = GEO[n]
        d["geometry"][f"sekiyu_{n}"] = gid
        d["textures"][f"sekiyu_{n}"] = tex
        d["textures"][f"sekiyu_{n}_burning"] = burn
    d["scripts"]["pre_animation"] = d["scripts"].get("pre_animation", []) + PRE
    d["scripts"]["initialize"] = d["scripts"].get("initialize", []) + ["variable.sekiyu_fx = 0;", "variable.sekiyu_fire = 0;"]
    d["animations"].update({
        "sekiyu_oil_idle": "animation.sekiyu.oil_body.idle",
        "sekiyu_puddle_idle": "animation.sekiyu.puddle.idle",
        "sekiyu_forms": "controller.animation.sekiyu.forms",
        "sekiyu_flames": "controller.animation.sekiyu.player_flames",
        "sekiyu_melt_in": "animation.sekiyu.oil_body.melt_in",
    })
    d["scripts"]["animate"] += [{"sekiyu_oil_idle": "variable.sekiyu_form == 2"}, {"sekiyu_puddle_idle": "variable.sekiyu_form == 3"}, "sekiyu_forms", "sekiyu_flames"]
    d["particle_effects"] = {**d.get("particle_effects", {}), "body_drips": "sekiyu:body_drips", "body_flames": "sekiyu:body_flames", "puddle_bubbles": "sekiyu:puddle_bubbles"}
    new_rc = []
    for entry in d["render_controllers"]:
        (k, cond), = entry.items()
        new_rc.append({SWAP.get(k, k): cond})
    new_rc.append({"controller.render.sekiyu.oil_body": "variable.sekiyu_form == 2 && !variable.is_first_person && !variable.map_face_icon"})
    new_rc.append({"controller.render.sekiyu.puddle": "variable.sekiyu_form == 3 && !variable.map_face_icon"})
    d["render_controllers"] = new_rc
    write_json(os.path.join(RP, "entity", "player.entity.json"), pe)

    # controllers: form particles (+ melt-in), burning flames
    keys = {"human": 0, "body_tp": 2, "body_fp": 3, "puddle": 4}
    states = {}
    for st, k in keys.items():
        s = {"transitions": [{o: f"variable.sekiyu_fx == {ok}"} for o, ok in keys.items() if o != st]}
        if st == "body_tp":
            s["particle_effects"] = [{"effect": "body_drips"}]
            s["animations"] = ["sekiyu_melt_in"]
        if st == "puddle":
            s["particle_effects"] = [{"effect": "puddle_bubbles"}]
        states[st] = s
    write_json(os.path.join(RP, "animation_controllers", "sekiyu_player.animation_controllers.json"), {
        "format_version": "1.10.0",
        "animation_controllers": {
            "controller.animation.sekiyu.forms": {"initial_state": "human", "states": states},
            "controller.animation.sekiyu.player_flames": {"initial_state": "off", "states": {
                "off": {"transitions": [{"on": "variable.sekiyu_fire"}]},
                "on": {"particle_effects": [{"effect": "body_flames"}], "transitions": [{"off": "!variable.sekiyu_fire"}]},
            }},
        },
    })

    t = "query.life_time"
    overlay = {
        "animation.sekiyu.oil_body.idle": {"loop": True, "bones": {
            **{f"oil_drip_{i}": {"scale": [1, f"1 + math.mod({t} * {0.7 + (i % 3) * 0.2} + {i * 0.37}, 1) * 1.4", 1]} for i in range(len(models.DRIPS))},
            "oil_torso": {"scale": [f"1 + math.sin({t} * 160) * 0.025", 1, f"1 + math.cos({t} * 140) * 0.03"]},
            "oil_head": {"scale": [f"1 + math.sin({t} * 130 + 40) * 0.03", f"1 + math.sin({t} * 170) * 0.02", 1]},
        }},
        "animation.sekiyu.oil_body.melt_in": {"loop": False, "animation_length": 0.5, "bones": {
            b: {"scale": {"0.0": [1.25, 0.3, 1.25], "0.25": [1.1, 0.95, 1.1], "0.5": [1, 1, 1]}} for b in models.SHELL_BONES.values()}},
        "animation.sekiyu.puddle.idle": {"loop": True, "bones": {
            "puddle_hump": {"scale": [f"1 + math.sin({t} * 120) * 0.08", f"1 + math.sin({t} * 120 + 90) * 0.2", f"1 + math.sin({t} * 120) * 0.08"],
                            "position": [0, f"math.sin({t} * 240) * 0.3", 0]},
            **{f"bubble_{i}": {"scale": f"math.mod({t} * 0.8 + {i * 0.27}, 1) * 1.3"} for i in range(4)},
            "puddle": {"rotation": [0, f"{t} * 25", 0]},
        }},
    }
    # one-shot casting poses (playAnimation), third person only
    poses = {
        "tide": clip(0.6, {"rightArm": {0.0: Z, 0.12: (-30, 0, -40), 0.3: (-100, 0, -20), 0.6: Z}, "leftArm": {0.0: Z, 0.12: (-30, 0, 40), 0.3: (-100, 0, 20), 0.6: Z},
                           "body": {0.0: Z, 0.3: (12, 0, 0), 0.6: Z}}),
        "geyser": clip(0.7, {"rightArm": {0.0: Z, 0.2: (-170, 0, -10), 0.4: (-60, 0, -10), 0.7: Z}, "body": {0.0: Z, 0.4: (15, 0, 0), 0.7: Z}}),
        "prison": clip(0.6, {"rightArm": {0.0: Z, 0.15: (-90, 0, -5), 0.35: (-95, 0, 15), 0.6: Z}, "leftArm": {0.0: Z, 0.35: (-60, 0, 20), 0.6: Z}}),
        "jet": clip(0.45, {"body": {0.0: Z, 0.08: (28, 0, 0), 0.3: (24, 0, 0), 0.45: Z}, "rightArm": {0.0: Z, 0.08: (55, 0, -15), 0.45: Z},
                           "leftArm": {0.0: Z, 0.08: (55, 0, 15), 0.45: Z}}),
        "serpent": clip(0.6, {"rightArm": {0.0: Z, 0.1: (-40, 30, -10), 0.3: (-100, -20, -10), 0.6: Z}, "body": {0.0: Z, 0.3: (0, -20, 0), 0.6: Z}}),
        "inferno": clip(1.2, {"rightArm": {0.0: Z, 0.5: (-170, 0, -25), 1.0: (-175, 0, -30), 1.2: Z}, "leftArm": {0.0: Z, 0.5: (-170, 0, 25), 1.0: (-175, 0, 30), 1.2: Z},
                              "head": {0.0: Z, 0.5: (-25, 0, 0), 1.2: Z}, "body": {0.0: Z, 1.0: (-8, 0, 0), 1.2: Z}}),
        "ignite": clip(0.35, {"rightArm": {0.0: Z, 0.1: (-80, 0, 0), 0.2: (-95, 0, 10), 0.35: Z}}),
        "melt": clip(0.6, {"body": {0.0: Z, 0.25: (25, 0, 0), 0.6: Z}, "head": {0.0: Z, 0.25: (20, 0, 0), 0.6: Z},
                           "rightArm": {0.0: Z, 0.25: (20, 0, -25), 0.6: Z}, "leftArm": {0.0: Z, 0.25: (20, 0, 25), 0.6: Z}}),
    }
    anims = {**overlay, **{f"animation.sekiyu.player.{k}": v for k, v in poses.items()}}
    write_json(os.path.join(RP, "animations", "sekiyu_player.animation.json"), {"format_version": "1.10.0", "animations": anims})


# --------------------------------------------------------------------------- constructs

PROP_BURNING = {"sekiyu:burning": {"type": "bool", "default": False, "client_sync": True}}
CONSTRUCTS = {
    # name: (entity id suffix, model key, lifetime safety (s), extra properties, client particle sets)
    "oil_pool": ("pool", 40, {"sekiyu:radius": {"type": "float", "range": [0.3, 6.0], "default": 2.0, "client_sync": True}}, None),
    "black_tide": ("tide", 12, {}, ("tide_drips", "tide_flames")),
    "black_geyser": ("geyser", 6, {}, ("geyser_drips", "geyser_flames")),
    "tar_prison": ("prison", 10, {}, (None, "prison_flames")),
    "black_serpent": ("serpent", 15, {}, ("serpent_drips", "serpent_flames")),
    "fruit_relic": ("relic", 4, None, None),
}


def construct_bp(ident, lifetime, props):
    desc = {"identifier": ident, "is_spawnable": False, "is_summonable": True}
    if props is not None:
        desc["properties"] = {**PROP_BURNING, **props}
    return {"format_version": "1.21.0", "minecraft:entity": {
        "description": desc,
        "component_groups": {"sekiyu:despawn": {"minecraft:instant_despawn": {}}},
        "components": {
            "minecraft:type_family": {"family": ["sekiyu_construct", "inanimate"]},
            "minecraft:collision_box": {"width": 0.2, "height": 0.2},
            "minecraft:physics": {"has_gravity": False, "has_collision": False},
            "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
            "minecraft:knockback_resistance": {"value": 1.0},
            "minecraft:health": {"value": 100, "max": 100},
            "minecraft:fire_immune": {},
            "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": "no"}]},
            "minecraft:timer": {"looping": False, "time": lifetime, "randomInterval": False,
                                "time_down_event": {"event": "sekiyu:despawn", "target": "self"}},
            "minecraft:conditional_bandwidth_optimization": {},
        },
        "events": {"sekiyu:despawn": {"add": {"component_groups": ["sekiyu:despawn"]}}},
    }}


def construct_anims():
    t = "query.life_time"
    r0 = GEO["pool_radius"]
    a = {
        "animation.sekiyu.pool.idle": {"loop": True, "bones": {
            "pool": {"scale": [f"query.property('sekiyu:radius') / {r0:.3f}", 1, f"query.property('sekiyu:radius') / {r0:.3f}"]},
            **{f"pool_bubble_{i}": {"scale": f"math.mod({t} * 0.9 + {i * 0.33}, 1) * 1.2"} for i in range(3)}}},
        "animation.sekiyu.tide.roll": {"loop": True, "bones": {
            "wave": {"scale": [1, f"math.min(1, 0.25 + {t} * 3)", 1]},
            **{f"crest_{i}": {"rotation": [f"math.sin({t} * 320 + {i * 47}) * 9", 0, 0]} for i in range(8)},
            **{f"col_{i}": {"position": [0, f"math.sin({t} * 220 + {i * 61}) * 1.4", 0]} for i in range(8)}}},
        "animation.sekiyu.geyser.erupt": {"loop": True, "bones": {
            "column": {"scale": [f"1 + math.sin({t} * 1100) * 0.05",
                                 f"{t} < 0.15 ? {t} / 0.15 : ({t} < 1.05 ? 1 + math.sin({t} * 900) * 0.05 : math.max(0.02, 1 - ({t} - 1.05) / 0.4))",
                                 f"1 + math.cos({t} * 1000) * 0.05"]},
            "crown": {"rotation": [0, f"{t} * 300", 0]}}},
        "animation.sekiyu.prison.grip": {"loop": True, "bones": {
            **{f"tendril_{i}": {"scale": [1, f"math.min(1, 0.05 + {t} * 2.6)", 1], "rotation": [0, 0, f"math.sin({t} * 200 + {i * 45}) * 5"]} for i in range(8)},
            **{f"tendril_{i}_c": {"rotation": [f"math.sin({t} * 260 + {i * 30}) * 8", 0, 0]} for i in range(8)}}},
        "animation.sekiyu.serpent.slither": {"loop": True, "bones": {
            **{f"seg_{i}": {"rotation": [0, f"math.sin({t} * 420 - {i * 38}) * {10 + i * 0.8:.1f}", 0]} for i in range(models.SERPENT_SEGMENTS)},
            "neck": {"rotation": [f"math.sin({t} * 180) * 4", f"math.sin({t} * 420 + 38) * 6", 0]},
            "jaw": {"rotation": [f"math.max(0, math.sin({t} * 90)) * 5", 0, 0]}}},
        "animation.sekiyu.relic.float": {"loop": True, "bones": {
            "fruit": {"position": [0, f"{t} * 10", 0], "rotation": [0, f"{t} * 260", 0],
                      "scale": f"0.5 * math.max(0.05, 1 - math.max(0, {t} - 1.2) / 0.6)"}}},
    }
    # one-shot serpent actions (played by the script with playAnimation)
    a["animation.sekiyu.serpent.rise"] = {"loop": False, "animation_length": 0.6, "bones": {
        "root": {"position": {"0.0": [0, -40, 0], "0.4": [0, 3, 0], "0.6": [0, 0, 0]}, "scale": {"0.0": [1, 0.3, 1], "0.6": [1, 1, 1]}}}}
    a["animation.sekiyu.serpent.bite"] = {"loop": False, "animation_length": 0.5, "bones": {
        "neck": {"rotation": {"0.0": [0, 0, 0], "0.15": [-14, 0, 0], "0.25": [22, 0, 0], "0.5": [0, 0, 0]}, "position": {"0.0": [0, 0, 0], "0.25": [0, -4, -8], "0.5": [0, 0, 0]}},
        "jaw": {"rotation": {"0.0": [0, 0, 0], "0.15": [38, 0, 0], "0.25": [0, 0, 0], "0.5": [0, 0, 0]}}}}
    a["animation.sekiyu.serpent.sweep"] = {"loop": False, "animation_length": 0.6, "bones": {
        f"seg_{i}": {"rotation": {"0.0": [0, 0, 0], "0.2": [0, -40 + i * 2, 0], "0.4": [0, 45 - i * 2, 0], "0.6": [0, 0, 0]}} for i in range(4, models.SERPENT_SEGMENTS)}}
    write_json(os.path.join(RP, "animations", "sekiyu_constructs.animation.json"), {"format_version": "1.10.0", "animations": a})
    return a


def build_constructs():
    anims = construct_anims()
    rcs = {
        "controller.render.sekiyu.construct": {
            "arrays": {"textures": {"Array.skins": ["Texture.default", "Texture.burning"]}},
            "geometry": "Geometry.default", "materials": [{"*": "Material.default"}],
            "textures": ["Array.skins[query.property('sekiyu:burning') ? 1 : 0]"]},
        "controller.render.sekiyu.single": {"geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"]},
    }
    write_json(os.path.join(RP, "render_controllers", "sekiyu_constructs.render_controllers.json"), {"format_version": "1.8.0", "render_controllers": rcs})
    idle = {"oil_pool": "animation.sekiyu.pool.idle", "black_tide": "animation.sekiyu.tide.roll", "black_geyser": "animation.sekiyu.geyser.erupt",
            "tar_prison": "animation.sekiyu.prison.grip", "black_serpent": "animation.sekiyu.serpent.slither", "fruit_relic": "animation.sekiyu.relic.float"}
    controllers = {}
    for name, (model, lifetime, props, fx) in CONSTRUCTS.items():
        ident = f"sekiyu:{name}"
        write_json(os.path.join(BP, "entities", "sekiyu", f"{name}.json"), construct_bp(ident, lifetime, props))
        gid, tex, burn = GEO[model]
        desc = {
            "identifier": ident,
            "materials": {"default": "entity_emissive"},
            "textures": {"default": tex, **({"burning": burn} if burn else {})},
            "geometry": {"default": gid},
            "animations": {"idle": idle[name]},
            "scripts": {"animate": ["idle"]},
            "render_controllers": ["controller.render.sekiyu.construct" if burn else "controller.render.sekiyu.single"],
        }
        if fx:
            drips, fire = fx
            cname = f"controller.animation.sekiyu.{name}_fx"
            desc["particle_effects"] = {k: f"sekiyu:{v}" for k, v in (("drips", drips), ("flames", fire)) if v}
            desc["animations"]["fx"] = cname
            desc["scripts"]["animate"].append("fx")
            oil_state = {"transitions": [{"fire": "query.property('sekiyu:burning')"}]}
            if drips:
                oil_state["particle_effects"] = [{"effect": "drips"}]
            controllers[cname] = {"initial_state": "oil", "states": {
                "oil": oil_state,
                "fire": {"particle_effects": [{"effect": "flames"}], "transitions": [{"oil": "!query.property('sekiyu:burning')"}]}}}
        write_json(os.path.join(RP, "entity", "sekiyu", f"{name}.entity.json"), {"format_version": "1.10.0", "minecraft:client_entity": {"description": desc}})
    write_json(os.path.join(RP, "animation_controllers", "sekiyu_constructs.animation_controllers.json"),
               {"format_version": "1.10.0", "animation_controllers": controllers})
    return anims


# --------------------------------------------------------------------------- fruit item + attachable

HOLD_FP = {"rotation": [-120, -90, 0], "position": [0, 20, -5], "scale": 0.34}
HOLD_TP = {"rotation": [0, 90, 0], "position": [0, 24, 0], "scale": 0.45}
EAT_FP_DELTA = [3, -6, -8]  # added to HOLD_FP while eating: brings the fruit to the mouth


def build_items():
    fruit = {"format_version": "1.21.60", "minecraft:item": {
        "description": {"identifier": "sekiyu:sekiyu_fruit", "menu_category": {"category": "equipment"}},
        "components": {
            "minecraft:icon": {"textures": {"default": "sekiyu_fruit"}},
            "minecraft:display_name": {"value": "item.sekiyu:sekiyu_fruit.name"},
            "minecraft:max_stack_size": 16,
            "minecraft:food": {"nutrition": 4, "saturation_modifier": 0.6, "can_always_eat": True},
            "minecraft:use_animation": "eat",
            "minecraft:use_modifiers": {"use_duration": 1.6, "movement_modifier": 0.35},
            "minecraft:tags": {"tags": ["sekiyu:devil_fruit"]},
        }}}
    core = {"format_version": "1.21.60", "minecraft:item": {
        "description": {"identifier": "sekiyu:crude_core", "menu_category": {"category": "equipment"}},
        "components": {
            "minecraft:icon": {"textures": {"default": "sekiyu_crude_core"}},
            "minecraft:display_name": {"value": "item.sekiyu:crude_core.name"},
            "minecraft:max_stack_size": 1,
            "minecraft:hand_equipped": True,
            "minecraft:glint": True,
            "minecraft:tags": {"tags": ["sekiyu:control"]},
        }}}
    write_json(os.path.join(BP, "items", "sekiyu_fruit.json"), fruit)
    write_json(os.path.join(BP, "items", "crude_core.json"), core)

    gid, tex, _ = GEO["fruit"]
    att = {"format_version": "1.10.0", "minecraft:attachable": {"description": {
        "identifier": "sekiyu:sekiyu_fruit",
        "materials": {"default": "entity_emissive"},
        "textures": {"default": tex},
        "geometry": {"default": gid},
        "particle_effects": {"vapor": "sekiyu:fruit_vapor"},
        "animations": {"hold_fp": "animation.sekiyu.fruit.hold_first_person", "hold_tp": "animation.sekiyu.fruit.hold_third_person",
                       "eat_fp": "animation.sekiyu.fruit.eat_first_person", "vapor": "animation.sekiyu.fruit.vapor"},
        "scripts": {"animate": [{"hold_fp": "c.is_first_person"}, {"hold_tp": "!c.is_first_person"},
                                {"eat_fp": "c.is_first_person && query.main_hand_item_use_duration > 0.0"}, "vapor"]},
        "render_controllers": ["controller.render.sekiyu.single"],
    }}}
    write_json(os.path.join(RP, "attachables", "sekiyu_fruit.attachable.json"), att)
    ramp = "math.min(1, query.anim_time / 0.25)"
    bob = "math.sin(query.anim_time * 1400) * 0.6"
    fa = {
        "animation.sekiyu.fruit.hold_first_person": {"loop": True, "bones": {"fruit": HOLD_FP}},
        "animation.sekiyu.fruit.hold_third_person": {"loop": True, "bones": {"fruit": HOLD_TP}},
        "animation.sekiyu.fruit.eat_first_person": {"loop": "hold_on_last_frame", "animation_length": 3.0, "bones": {"fruit": {
            "position": [f"{EAT_FP_DELTA[0]} * {ramp}", f"{EAT_FP_DELTA[1]} * {ramp} + {bob} * {ramp}", f"{EAT_FP_DELTA[2]} * {ramp}"]}}},
        "animation.sekiyu.fruit.vapor": {"loop": True, "animation_length": 0.9, "particle_effects": {
            "0.0": {"effect": "vapor", "locator": "vapor_a"}, "0.3": {"effect": "vapor", "locator": "vapor_b"}, "0.6": {"effect": "vapor", "locator": "vapor_c"}}},
    }
    write_json(os.path.join(RP, "animations", "sekiyu_fruit.animation.json"), {"format_version": "1.10.0", "animations": fa})


# --------------------------------------------------------------------------- sounds, fog, lang


def build_sounds():
    table = sounds.build(os.path.join(RP, "sounds", "sekiyu"))
    defs = {}
    for ev, stems in table.items():
        vol = sounds.SOUNDS[ev][2]
        defs[ev] = {"category": "player", "min_distance": 1.0, "max_distance": 40.0,
                    "sounds": [{"name": f"sounds/sekiyu/{s}", "volume": vol, "load_on_low_memory": True} for s in stems]}
    write_json(os.path.join(RP, "sounds", "sound_definitions.json"), {"format_version": "1.20.20", "sound_definitions": defs})


def build_fog():
    dist = {"fog_start": 4.0, "fog_end": 46.0, "fog_color": "#3a1406", "render_distance_type": "fixed"}
    write_json(os.path.join(RP, "fogs", "sekiyu_inferno.json"), {"format_version": "1.16.100", "minecraft:fog_settings": {
        "description": {"identifier": "sekiyu:inferno_fog"}, "distance": {"air": dist, "weather": dist}}})


def build_lang():
    rp = [
        f"pack.name={ADDON_NAME}",
        "pack.description=Original fan-made Logia: become crude oil. 8 abilities, oil that slows, burns and spreads.",
        "item.sekiyu:sekiyu_fruit.name=§6Sekiyu Sekiyu no Mi",
        "item.sekiyu:crude_core.name=§6Crude Core",
    ] + [f"entity.sekiyu:{n}.name={n.replace('_', ' ').title()}" for n in CONSTRUCTS]
    write_text(os.path.join(RP, "texts", "en_US.lang"), "\n".join(rp) + "\n")
    write_text(os.path.join(BP, "texts", "en_US.lang"), "\n".join(rp[:2]) + "\n")
    for root in (BP, RP):
        write_text(os.path.join(root, "texts", "languages.json"), json.dumps(["en_US"], indent=2) + "\n")


def build_scripts():
    tsc = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        raise SystemExit("TypeScript not installed: run `npm install` in sekiyu-addon/")
    res = subprocess.run([tsc, "-p", os.path.join(ROOT, "tsconfig.json"), "--outDir", os.path.join(BP, "scripts")], capture_output=True, text=True)
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
        zip_dir(zf, BP, "Sekiyu_BP")
        zip_dir(zf, RP, "Sekiyu_RP")
    for folder, suffix in ((BP, "BP"), (RP, "RP")):
        with zipfile.ZipFile(os.path.join(DIST, f"{FILE_BASE}_{suffix}.mcpack"), "w", zipfile.ZIP_DEFLATED) as zf:
            zip_dir(zf, folder, "")
    return addon


def main():
    for p in (BP, RP):
        if os.path.exists(p):
            shutil.rmtree(p)
    manifests()
    build_models()
    build_2d()
    build_particles()
    build_player()
    build_constructs()
    build_items()
    build_sounds()
    build_fog()
    build_lang()
    if ASSETS_ONLY:
        print("assets built in", BUILD)
        return
    build_scripts()
    print("built", os.path.relpath(package(), ROOT))


if __name__ == "__main__":
    main()
