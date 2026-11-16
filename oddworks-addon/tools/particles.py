"""
Particle effects for ODDWORKS. Scripts feed per-spawn data through MolangVariableMap:
  variable.dir   (vector)  direction / orientation axis
  variable.len   (float)   segment length (stretched billboards)
  variable.color (rgba)    tint (blood colour per creature, line strain colour ...)
  variable.size  (float)   overall scale
  variable.count (float)   particle count for bursts
Every script variable has a default in emitter_initialization so the effects also work
when spawned bare (e.g. from /particle).
"""
from __future__ import annotations

TEX = "textures/particle/oddworks/{}"

DEFAULTS = (
    "variable.dir ?? { variable.dir.x = 0.0; variable.dir.y = 1.0; variable.dir.z = 0.0; };"
    "variable.color ?? { variable.color.r = 1.0; variable.color.g = 1.0; variable.color.b = 1.0; variable.color.a = 1.0; };"
    "variable.len = variable.len ?? 1.0;"
    "variable.size = variable.size ?? 1.0;"
    "variable.count = variable.count ?? 8.0;"
    "variable.speed = variable.speed ?? 1.0;"
    "variable.life = variable.life ?? 1.0;"
)

AGE = "(variable.particle_age / variable.particle_lifetime)"


def effect(ident, sprite, *, material="particles_add", count="1", shape=None, speed="0", direction=None,
           lifetime="0.5", accel=(0, 0, 0), drag=0.0, size=("0.1", "0.1"), facing="lookat_xyz",
           face_dir=None, color=None, gradient=None, collision=None, spin=None, parametric=None, steady=None):
    comps = {
        "minecraft:emitter_initialization": {"creation_expression": DEFAULTS},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05 if steady is None else steady[1]},
        "minecraft:particle_initial_speed": speed,
        "minecraft:particle_lifetime_expression": {"max_lifetime": lifetime},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": list(accel), "linear_drag_coefficient": drag},
    }
    if steady is None:
        comps["minecraft:emitter_rate_instant"] = {"num_particles": count}
    else:
        comps["minecraft:emitter_rate_steady"] = {"spawn_rate": steady[0], "max_particles": 200}
    if shape is None:
        shape = ("point", {})
    kind, opts = shape
    sh = dict(opts)
    if direction is not None and kind in ("point", "custom"):
        sh["direction"] = list(direction)
    comps[f"minecraft:emitter_shape_{kind}"] = sh
    bb = {"size": list(size), "facing_camera_mode": facing,
          "uv": {"texture_width": 1, "texture_height": 1, "uv": [0, 0], "uv_size": [1, 1]}}
    if face_dir is not None:
        bb["direction"] = ({"mode": "derive_from_velocity", "min_speed_threshold": 0.01} if face_dir == "velocity"
                           else {"mode": "custom", "custom_direction": list(face_dir)})
    comps["minecraft:particle_appearance_billboard"] = bb
    if gradient:
        comps["minecraft:particle_appearance_tinting"] = {"color": {"gradient": gradient, "interpolant": AGE}}
    else:
        comps["minecraft:particle_appearance_tinting"] = {"color": list(color or [1, 1, 1, f"1 - {AGE}"])}
    if collision:
        comps["minecraft:particle_motion_collision"] = collision
    if spin:
        comps["minecraft:particle_initial_spin"] = {"rotation": spin[0], "rotation_rate": spin[1]}
    if parametric:
        comps.pop("minecraft:particle_motion_dynamic")
        comps["minecraft:particle_motion_parametric"] = parametric
    return {
        "format_version": "1.10.0",
        "particle_effect": {
            "description": {"identifier": ident,
                            "basic_render_parameters": {"material": material, "texture": TEX.format(sprite)}},
            "components": comps,
        },
    }


def fade(r, g, b, a=1.0, power=1.0):
    return [r, g, b, f"{a} * math.pow(1 - {AGE}, {power})"]


VAR_COL = ["variable.color.r", "variable.color.g", "variable.color.b", f"variable.color.a * (1 - {AGE})"]
DIR = ["variable.dir.x", "variable.dir.y", "variable.dir.z"]
RAND_SPREAD = lambda k: [f"variable.dir.x + (variable.particle_random_1 - 0.5) * {k}",
                         f"variable.dir.y + (variable.particle_random_2 - 0.5) * {k}",
                         f"variable.dir.z + (variable.particle_random_3 - 0.5) * {k}"]
ALONG = [f"variable.dir.x * variable.len * variable.particle_random_1",
         f"variable.dir.y * variable.len * variable.particle_random_1",
         f"variable.dir.z * variable.len * variable.particle_random_1"]


def all_effects() -> dict:
    E = {}

    def add(e):
        E[e["particle_effect"]["description"]["identifier"]] = e

    # ------------------------------------------------------------------ 001 goggles
    add(effect("oddworks:sun_mote", "dot", speed="variable.speed", direction=DIR, lifetime="variable.life",
               size=["0.07 * variable.size * (0.6 + 0.4 * math.sin(variable.particle_age * 900))",
                     "0.07 * variable.size * (0.6 + 0.4 * math.sin(variable.particle_age * 900))"],
               gradient={"0.0": [1.0, 0.75, 0.3, 0.0], "0.15": [1.0, 0.82, 0.4, 0.95], "0.8": [1.0, 0.95, 0.75, 0.9],
                         "1.0": [1.0, 1.0, 1.0, 0.0]}))
    add(effect("oddworks:albedo_glint", "spark", count="2", shape=("box", {"half_dimensions": [0.4, 0.05, 0.4]}),
               speed="0.3", direction=[0, 1, 0], lifetime="0.6 + variable.particle_random_1 * 0.5",
               size=[f"0.09 * math.sin({AGE} * 180)", f"0.09 * math.sin({AGE} * 180)"],
               color=[0.85, 0.97, 1.0, 1.0], spin=["variable.particle_random_2 * 90", "120"]))
    add(effect("oddworks:slit_glow", "flare", lifetime="0.12", size=["0.32 * variable.size", "0.05 * variable.size"],
               color=fade(1.0, 0.8, 0.35, 0.9)))
    add(effect("oddworks:frost_beam", "streak", lifetime="0.28", facing="lookat_direction", face_dir=DIR,
               size=["variable.len * 0.5", f"variable.size * 0.11 * (1 - {AGE} * 0.6)"],
               gradient={"0.0": [1.0, 1.0, 1.0, 1.0], "0.35": [0.6, 0.92, 1.0, 0.85], "1.0": [0.3, 0.7, 1.0, 0.0]}))
    add(effect("oddworks:frost_beam_glow", "streak", lifetime="0.4", facing="lookat_direction", face_dir=DIR,
               size=["variable.len * 0.5", f"variable.size * 0.32 * (1 - {AGE} * 0.3)"],
               color=fade(0.35, 0.8, 1.0, 0.45, 1.5)))
    add(effect("oddworks:frost_beam_sparkle", "flake", material="particles_blend", count="variable.count",
               shape=("custom", {"offset": ALONG}), speed="0.6",
               direction=["variable.particle_random_2 - 0.5", "variable.particle_random_3 - 0.5",
                          "variable.particle_random_4 - 0.5"],
               lifetime="0.5 + variable.particle_random_2 * 0.6", accel=(0, -0.6, 0), drag=1.5,
               size=["0.06 + variable.particle_random_3 * 0.05", "0.06 + variable.particle_random_3 * 0.05"],
               color=fade(0.9, 0.98, 1.0, 1.0), spin=["variable.particle_random_4 * 360", "90"]))
    add(effect("oddworks:rime_ring", "ring", lifetime="0.3", facing="direction_z", face_dir=DIR,
               size=[f"variable.size * (0.15 + {AGE} * 0.75)", f"variable.size * (0.15 + {AGE} * 0.75)"],
               color=fade(0.75, 0.95, 1.0, 0.9)))
    add(effect("oddworks:frost_burst", "shard", material="particles_blend", count="variable.count",
               shape=("sphere", {"radius": 0.25, "surface_only": False, "direction": "outwards"}),
               speed="3 + variable.particle_random_1 * 4", lifetime="0.6 + variable.particle_random_2 * 0.6",
               accel=(0, -9, 0), drag=0.8, facing="lookat_direction", face_dir="velocity",
               size=["0.06 + variable.particle_random_3 * 0.05", "0.16 + variable.particle_random_3 * 0.1"],
               gradient={"0.0": [1, 1, 1, 1], "0.7": [0.75, 0.92, 1.0, 0.9], "1.0": [0.6, 0.85, 1.0, 0.0]},
               collision={"collision_radius": 0.05, "coefficient_of_restitution": 0.35, "collision_drag": 4}))
    add(effect("oddworks:frost_mist", "mist", material="particles_blend", count="variable.count",
               shape=("sphere", {"radius": "0.6 * variable.size", "surface_only": False, "direction": "outwards"}),
               speed="0.4", lifetime="1.2 + variable.particle_random_1 * 0.9", accel=(0, -0.35, 0), drag=1.2,
               size=[f"(0.35 + {AGE} * 0.9) * variable.size", f"(0.35 + {AGE} * 0.9) * variable.size"],
               color=fade(0.86, 0.95, 1.0, 0.55, 1.4)))
    add(effect("oddworks:frost_aura", "flake", material="particles_blend", count="variable.count",
               shape=("box", {"half_dimensions": ["0.5 * variable.size", "0.9 * variable.size", "0.5 * variable.size"]}),
               speed="0.15", direction=[0, -1, 0], lifetime="0.9 + variable.particle_random_1 * 0.8",
               accel=(0, -0.4, 0), drag=1.0, size=["0.05", "0.05"], color=fade(0.92, 0.98, 1.0, 1.0),
               spin=["variable.particle_random_2 * 360", "60"]))
    add(effect("oddworks:glare_flare", "flare", lifetime="0.38",
               size=[f"variable.size * (1.6 + {AGE} * 1.6)", f"variable.size * 0.22 * (1 - {AGE})"],
               color=fade(1.0, 0.97, 0.85, 1.0)))
    add(effect("oddworks:glare_burst", "dot", lifetime="0.3",
               size=[f"variable.size * (0.4 + {AGE} * 1.4)", f"variable.size * (0.4 + {AGE} * 1.4)"],
               color=fade(1.0, 0.95, 0.8, 0.85, 2)))
    add(effect("oddworks:glare_cone", "spark", count="variable.count", speed="10 + variable.particle_random_4 * 8",
               direction=RAND_SPREAD(1.1), lifetime="0.35 + variable.particle_random_1 * 0.35", drag=5,
               size=["0.08", "0.08"], color=fade(1.0, 0.95, 0.7, 1.0), spin=["0", "360"]))
    add(effect("oddworks:dazzle_stars", "spark", count="3", lifetime="0.55",
               parametric={"relative_position": [
                   "math.cos(variable.particle_age * 540 + variable.particle_random_1 * 360) * 0.42 * variable.size",
                   "math.sin(variable.particle_age * 900) * 0.05",
                   "math.sin(variable.particle_age * 540 + variable.particle_random_1 * 360) * 0.42 * variable.size"]},
               size=["0.09", "0.09"], color=fade(1.0, 0.92, 0.45, 1.0, 0.5)))
    add(effect("oddworks:sun_ray", "streak", lifetime="0.18", facing="lookat_direction", face_dir=DIR,
               size=["variable.len * 0.5", "0.06 * variable.size"], color=fade(1.0, 0.85, 0.45, 0.8)))
    add(effect("oddworks:sundog_halo", "halo", lifetime="variable.life",
               size=["variable.size", "variable.size"],
               gradient={"0.0": [1.0, 0.88, 0.7, 0.0], "0.2": [1.0, 0.9, 0.75, 0.7], "0.75": [0.95, 0.95, 1.0, 0.6],
                         "1.0": [0.9, 0.95, 1.0, 0.0]}))
    add(effect("oddworks:sundog_spark", "spark", count="2", shape=("sphere", {"radius": 0.45, "surface_only": True}),
               speed="0.25", lifetime="0.7", size=[f"0.08 * (1 - {AGE})", f"0.08 * (1 - {AGE})"],
               color=fade(1.0, 0.9, 0.55, 1.0), spin=["variable.particle_random_1 * 90", "180"]))

    # ------------------------------------------------------------------ 002 handline
    add(effect("oddworks:line_segment", "line", material="particles_blend", lifetime="0.11", facing="lookat_direction",
               face_dir=DIR, size=["variable.len * 0.5", "0.016 * variable.size"],
               color=["variable.color.r", "variable.color.g", "variable.color.b", "variable.color.a"]))
    add(effect("oddworks:line_glow", "streak", lifetime="0.11", facing="lookat_direction", face_dir=DIR,
               size=["variable.len * 0.5", "0.05 * variable.size"], color=[0.5, 0.95, 0.85, 0.22]))
    add(effect("oddworks:whirl_trail", "dot", lifetime="0.35", accel=(0, -1, 0),
               size=[f"0.07 * (1 - {AGE})", f"0.07 * (1 - {AGE})"], color=fade(0.9, 0.95, 0.95, 0.8)))
    add(effect("oddworks:hook_spark", "spark", count="variable.count", speed="2.5 + variable.particle_random_1 * 2.5",
               direction=RAND_SPREAD(1.6), lifetime="0.25 + variable.particle_random_2 * 0.25", accel=(0, -8, 0),
               drag=1, size=["0.05", "0.05"], color=VAR_COL))
    add(effect("oddworks:snap_pulse", "spark", lifetime="0.18", size=[f"0.22 * (1 - {AGE})", f"0.22 * (1 - {AGE})"],
               color=VAR_COL, spin=["variable.particle_random_1 * 90", "720"]))
    add(effect("oddworks:line_burn", "dot", count="6", speed="0.6", direction=RAND_SPREAD(2), lifetime="0.6",
               accel=(0, -3, 0), size=["0.05", "0.05"],
               gradient={"0.0": [1, 0.85, 0.4, 1], "0.5": [1, 0.4, 0.1, 0.9], "1.0": [0.2, 0.2, 0.2, 0]}))
    add(effect("oddworks:bobber_ripple", "ring", material="particles_blend", lifetime="1.1", facing="direction_z",
               face_dir=[0, 1, 0], size=[f"0.12 + {AGE} * 0.9 * variable.size", f"0.12 + {AGE} * 0.9 * variable.size"],
               color=fade(0.85, 0.95, 1.0, 0.7)))
    add(effect("oddworks:water_spray", "dot", material="particles_blend", count="variable.count",
               shape=("disc", {"radius": 0.25, "plane_normal": [0, 1, 0], "direction": "outwards"}),
               speed="1.5 + variable.particle_random_1 * 2", direction=[0, 1, 0], lifetime="0.6",
               accel=(0, -10, 0), size=["0.05", "0.05"], color=fade(0.7, 0.85, 1.0, 0.9),
               collision={"collision_radius": 0.04, "expire_on_contact": True}))

    # ------------------------------------------------------------------ 003 cane
    add(effect("oddworks:slash_seg", "streak", lifetime="0.2", facing="lookat_direction", face_dir=DIR,
               size=["variable.len * 0.55", f"variable.size * 0.07 * (1 - {AGE})"],
               gradient={"0.0": [1, 1, 1, 1], "0.5": [0.8, 0.9, 1.0, 0.8], "1.0": [0.6, 0.75, 1.0, 0]}))
    add(effect("oddworks:iai_streak", "streak", material="particles_blend", lifetime="0.35",
               facing="lookat_direction", face_dir=DIR, size=["variable.len * 0.5", f"0.35 * (1 - {AGE})"],
               color=fade(0.75, 0.85, 1.0, 0.35)))
    add(effect("oddworks:blood_drop", "drop", material="particles_blend", count="variable.count",
               speed="1.8 + variable.particle_random_4 * 2.6 * variable.speed", direction=RAND_SPREAD(1.4),
               lifetime="1.2", accel=(0, -14, 0), drag=0.4, facing="lookat_direction", face_dir="velocity",
               size=["0.035 + variable.particle_random_2 * 0.03", "0.05 + variable.particle_random_2 * 0.04"],
               color=["variable.color.r", "variable.color.g", "variable.color.b", "variable.color.a"],
               collision={"collision_radius": 0.03, "expire_on_contact": True}))
    add(effect("oddworks:blood_mist", "mist", material="particles_blend", count="3",
               shape=("sphere", {"radius": 0.15, "surface_only": False, "direction": "outwards"}), speed="0.6",
               lifetime="0.45", drag=2, size=[f"0.15 + {AGE} * 0.35", f"0.15 + {AGE} * 0.35"],
               color=["variable.color.r", "variable.color.g", "variable.color.b", f"0.55 * (1 - {AGE})"]))
    add(effect("oddworks:blood_splat", "splat", material="particles_blend", lifetime="4", facing="direction_z",
               face_dir=[0, 1, 0], size=["0.22 * variable.size", "0.22 * variable.size"],
               spin=["variable.particle_random_1 * 360", "0"],
               color=["variable.color.r * 0.8", "variable.color.g * 0.8", "variable.color.b * 0.8",
                      f"math.min(1, (1 - {AGE}) * 3) * 0.85"]))
    add(effect("oddworks:clang_spark", "spark", count="variable.count", speed="3 + variable.particle_random_1 * 4",
               direction=RAND_SPREAD(2.2), lifetime="0.22 + variable.particle_random_2 * 0.25", accel=(0, -12, 0),
               drag=0.5, size=["0.045", "0.045"],
               gradient={"0.0": [1, 1, 0.85, 1], "0.5": [1, 0.75, 0.3, 1], "1.0": [1, 0.4, 0.1, 0]}))
    add(effect("oddworks:vital_glint", "spark", lifetime="0.3",
               size=[f"0.45 * math.sin({AGE} * 180) * variable.size", f"0.45 * math.sin({AGE} * 180) * variable.size"],
               color=[1, 1, 1, 1], spin=["0", "240"]))
    add(effect("oddworks:deflect_flash", "ring", lifetime="0.22",
               size=[f"0.2 + {AGE} * 1.1", f"0.2 + {AGE} * 1.1"], color=fade(1.0, 0.95, 0.75, 1.0)))
    add(effect("oddworks:focus_ring", "ring", material="particles_blend", lifetime="0.5", facing="direction_z",
               face_dir=[0, 1, 0], size=[f"1.3 - {AGE} * 0.9", f"1.3 - {AGE} * 0.9"],
               color=["0.85", "0.95", "1.0", f"0.55 * math.sin({AGE} * 180)"]))
    return E
