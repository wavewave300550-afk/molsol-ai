"""
Script-driven spectacle particles that use the second atlas (textures/particle/legends_fx2.png).
Every effect is parameterised by the MolangVariableMap the scripts pass in:
  variable.color (rgb), variable.size, variable.life, variable.count, variable.speed,
  variable.radius, variable.height, variable.spin, variable.u / variable.v (atlas cell)
"""
import json
import os

TEX = "textures/particle/legends_fx2"

CELL = {
    "sig_taotie": (0, 0), "sig_nidhogg": (1, 0), "sig_hanuman": (2, 0), "sig_alicorn": (3, 0),
    "sig_tenko": (0, 1), "sig_logos": (1, 1), "crack": (2, 1), "rays": (3, 1),
    "bolt_a": (0, 2), "bolt_b": (1, 2), "rim": (2, 2), "flare": (3, 2),
    "comet": (0, 3), "sakura": (1, 3), "wind": (2, 3), "dome": (3, 3),
}

AGE = "variable.particle_age"
LIFE = "variable.particle_lifetime"
T = f"({AGE} / {LIFE})"


def uv(cell=None, expr=None):
    if expr is None:
        c, r = CELL[cell]
        expr = [c * 32, r * 32]
    return {"texture_width": 128, "texture_height": 128, "uv": expr, "uv_size": [32, 32]}


def tint(alpha):
    return {"color": ["variable.color.r", "variable.color.g", "variable.color.b", alpha]}


def effect(ident, comps, material="particles_add"):
    return {
        "format_version": "1.10.0",
        "particle_effect": {
            "description": {"identifier": ident,
                            "basic_render_parameters": {"material": material, "texture": TEX}},
            "components": comps,
        },
    }


def once(n=1):
    return {"minecraft:emitter_lifetime_once": {"active_time": 0.05},
            "minecraft:emitter_rate_instant": {"num_particles": n}}


def stream(rate, mx):
    return {"minecraft:emitter_lifetime_once": {"active_time": "variable.life"},
            "minecraft:emitter_rate_steady": {"spawn_rate": rate, "max_particles": mx}}


def fade_io(fin, fout):
    return f"math.min(1.0, {AGE} * {fin}) * math.clamp(({LIFE} - {AGE}) * {fout}, 0.0, 1.0)"


P = {}

# Boss sigil: a flat rune circle that unfolds, turns, and fades.
grow = f"variable.size * (1.0 - math.pow(1.0 - math.min(1.0, {AGE} / 0.35), 3) * 0.7)"
P["legends:sigil"] = effect("legends:sigil", {
    **once(),
    "minecraft:emitter_shape_point": {},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life"},
    "minecraft:particle_initial_speed": 0,
    "minecraft:particle_motion_dynamic": {},
    "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_1 * 360", "rotation_rate": "variable.spin"},
    "minecraft:particle_appearance_tinting": tint(fade_io(4.0, 2.5)),
    "minecraft:particle_appearance_billboard": {"facing_camera_mode": "emitter_transform_xz",
                                                "uv": uv(expr=["variable.u", "variable.v"]), "size": [grow, grow]},
})

# Glowing ground fissures under heavy impacts.
csize = f"variable.size * math.min(1.0, 0.4 + {AGE} * 6.0)"
P["legends:crack"] = effect("legends:crack", {
    **once(),
    "minecraft:emitter_shape_point": {},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life"},
    "minecraft:particle_initial_speed": 0,
    "minecraft:particle_motion_dynamic": {},
    "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_2 * 360", "rotation_rate": 0},
    "minecraft:particle_appearance_tinting": tint(f"math.min(1.0, {AGE} * 10.0) * math.clamp(({LIFE} - {AGE}) / ({LIFE} * 0.5), 0.0, 1.0)"),
    "minecraft:particle_appearance_billboard": {"facing_camera_mode": "emitter_transform_xz",
                                                "uv": uv("crack"), "size": [csize, csize]},
})

# Radiant god-rays behind a detonation.
rsize = f"variable.size * (0.35 + 0.65 * math.min(1.0, {AGE} * 6.0))"
P["legends:rays"] = effect("legends:rays", {
    **once(),
    "minecraft:emitter_shape_point": {},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life"},
    "minecraft:particle_initial_speed": 0,
    "minecraft:particle_motion_dynamic": {},
    "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_1 * 360", "rotation_rate": "variable.spin"},
    "minecraft:particle_appearance_tinting": tint(f"math.pow(math.clamp(1.0 - {T}, 0.0, 1.0), 1.5)"),
    "minecraft:particle_appearance_billboard": {"facing_camera_mode": "lookat_xyz", "uv": uv("rays"), "size": [rsize, rsize]},
})

# Horizontal lens flare.
P["legends:flare"] = effect("legends:flare", {
    **once(),
    "minecraft:emitter_shape_point": {},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life"},
    "minecraft:particle_initial_speed": 0,
    "minecraft:particle_motion_dynamic": {},
    "minecraft:particle_appearance_tinting": tint(f"math.pow(math.clamp(1.0 - {T}, 0.0, 1.0), 2.0)"),
    "minecraft:particle_appearance_billboard": {
        "facing_camera_mode": "rotate_xyz", "uv": uv("flare"),
        "size": [f"variable.size * 1.6 * (0.6 + 0.4 * math.min(1.0, {AGE} * 8.0))", "variable.size * 0.5"]},
})

# Lightning bolt: an upright sprite that always faces the camera, flickering.
P["legends:bolt"] = effect("legends:bolt", {
    **once(),
    "minecraft:emitter_shape_point": {},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life"},
    "minecraft:particle_initial_speed": 0,
    "minecraft:particle_motion_dynamic": {},
    "minecraft:particle_appearance_tinting": tint(
        f"(math.mod(math.floor({AGE} * 24.0), 2) == 0 ? 1.0 : 0.45) * math.clamp(1.0 - {T} * 0.8, 0.0, 1.0)"),
    "minecraft:particle_appearance_billboard": {
        "facing_camera_mode": "lookat_y",
        "uv": uv(expr=["variable.particle_random_1 > 0.5 ? 32 : 0", 64]),
        "size": ["variable.height * 0.3", "variable.height * 0.5"]},
})

# Rings of light rising up a column (ascension / charge).
P["legends:ascend"] = effect("legends:ascend", {
    **stream("variable.count / math.max(0.1, variable.life)", 40),
    "minecraft:emitter_shape_point": {"direction": [0, 1, 0]},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.height / math.max(0.1, variable.speed)"},
    "minecraft:particle_initial_speed": "variable.speed",
    "minecraft:particle_motion_dynamic": {},
    "minecraft:particle_appearance_tinting": tint(f"math.min(1.0, {AGE} * 6.0) * math.clamp(1.0 - {T}, 0.0, 1.0)"),
    "minecraft:particle_appearance_billboard": {
        "facing_camera_mode": "emitter_transform_xz", "uv": uv("rim"),
        "size": [f"variable.size * (1.0 - 0.6 * {T})", f"variable.size * (1.0 - 0.6 * {T})"]},
})

# A funnel of wind sprites spiralling upward.
ang = "variable.particle_random_1 * 360 + variable.particle_age * variable.spin"
rad = f"variable.radius * (0.3 + 0.7 * {T})"
P["legends:vortex"] = effect("legends:vortex", {
    **stream("variable.count", 160),
    "minecraft:emitter_shape_point": {},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.height / math.max(0.1, variable.speed)"},
    "minecraft:particle_motion_parametric": {
        "relative_position": [f"math.cos({ang}) * {rad}", f"{AGE} * variable.speed", f"math.sin({ang}) * {rad}"]},
    "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_2 * 360", "rotation_rate": 320},
    "minecraft:particle_appearance_tinting": tint(f"math.min(1.0, {AGE} * 5.0) * math.clamp(1.0 - {T}, 0.0, 1.0)"),
    "minecraft:particle_appearance_billboard": {
        "facing_camera_mode": "lookat_xyz", "uv": uv("wind"),
        "size": [f"variable.size * (0.6 + 0.8 * {T})", f"variable.size * (0.6 + 0.8 * {T})"]},
})

# Falling stars / meteors over a disc: spawn the emitter `height` above the ground.
P["legends:rain"] = effect("legends:rain", {
    **stream("variable.count", 220),
    "minecraft:emitter_shape_disc": {"radius": "variable.radius", "direction": [0, -1, 0]},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.height / math.max(0.1, variable.speed)"},
    "minecraft:particle_initial_speed": "variable.speed",
    "minecraft:particle_motion_dynamic": {},
    "minecraft:particle_appearance_tinting": tint(f"math.min(1.0, {AGE} * 8.0)"),
    "minecraft:particle_appearance_billboard": {
        "facing_camera_mode": "lookat_y", "uv": uv("comet"),
        "size": ["variable.size * 0.5", "variable.size * 1.6"]},
})

# An expanding sphere of force (fresnel disc reads as a shell from every angle).
dsize = f"variable.size * (1.0 - math.pow(1.0 - math.min(1.0, {T} * 1.15), 3))"
P["legends:dome"] = effect("legends:dome", {
    **once(),
    "minecraft:emitter_shape_point": {},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life"},
    "minecraft:particle_initial_speed": 0,
    "minecraft:particle_motion_dynamic": {},
    "minecraft:particle_appearance_tinting": tint(f"math.pow(math.clamp(1.0 - {T}, 0.0, 1.0), 1.2) * 0.9"),
    "minecraft:particle_appearance_billboard": {"facing_camera_mode": "lookat_xyz", "uv": uv("dome"), "size": [dsize, dsize]},
})

# A storm of blossom petals (opaque blend so they read as petals, not light).
P["legends:petals"] = effect("legends:petals", {
    **stream("variable.count", 150),
    "minecraft:emitter_shape_sphere": {"radius": "variable.radius", "direction": "outwards"},
    "minecraft:particle_lifetime_expression": {"max_lifetime": "2.0 + variable.particle_random_3"},
    "minecraft:particle_initial_speed": "variable.speed",
    "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -0.8, 0], "linear_drag_coefficient": 1.1},
    "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_2 * 360",
                                        "rotation_rate": "(variable.particle_random_4 - 0.5) * 600"},
    "minecraft:particle_appearance_tinting": tint(f"math.min(1.0, {AGE} * 6.0) * math.clamp((1.0 - {T}) * 3.0, 0.0, 1.0)"),
    "minecraft:particle_appearance_billboard": {
        "facing_camera_mode": "lookat_xyz", "uv": uv("sakura"),
        "size": ["variable.size * (0.7 + 0.5 * variable.particle_random_1)",
                 "variable.size * (0.7 + 0.5 * variable.particle_random_1)"]},
}, material="particles_blend")

# Atlas cell lookup for the scripts (sigils by boss key).
SIGIL_UV = {k.split("_", 1)[1]: [c * 32, r * 32] for k, (c, r) in CELL.items() if k.startswith("sig_")}


def write_particles(rp):
    d = os.path.join(rp, "particles", "legends")
    os.makedirs(d, exist_ok=True)
    for ident, js in P.items():
        with open(os.path.join(d, ident.split(":")[1] + ".json"), "w") as f:
            json.dump(js, f, indent=1)
    return len(P)
