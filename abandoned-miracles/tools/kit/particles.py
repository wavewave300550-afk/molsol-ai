"""
particles.py - Bedrock particle effect builders.

Two families:

  * decorative effects (bursts, motes, trails) attached to bosses, and
  * TELEGRAPH primitives whose shape is supplied by the script through Molang
    variables, so one `spawnParticle` call draws a whole line / arc / disc that
    exactly matches the hazard geometry computed on the server.

Script-supplied variables (set with MolangVariableMap):
    variable.dx, variable.dz   unit direction on the ground plane (lines)
    variable.len               length in blocks (lines)
    variable.r                 radius in blocks (arcs, discs)
    variable.a0, variable.sweep   start angle / sweep in degrees (arcs)
    variable.w                 half width in blocks (lanes)
    variable.yaw               rotation in degrees (lanes)
    variable.life              particle lifetime in seconds
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Union

Num = Union[int, float, str]


class Sprite:
    """A cell in a particle sheet."""

    def __init__(self, texture: str, sheet: int, x: int, y: int, w: int, h: int):
        self.texture, self.sheet, self.x, self.y, self.w, self.h = texture, sheet, x, y, w, h

    def uv(self, frames: int = 1, fps: float = 8.0, loop: bool = True, stretch: bool = False) -> dict:
        d = {"texture_width": self.sheet, "texture_height": self.sheet}
        if frames > 1:
            d["flipbook"] = {"base_UV": [self.x, self.y], "size_UV": [self.w, self.h],
                             "step_UV": [self.w, 0], "frames_per_second": fps, "max_frame": frames,
                             "stretch_to_lifetime": stretch, "loop": loop}
        else:
            d["uv"] = [self.x, self.y]
            d["uv_size"] = [self.w, self.h]
        return d


def effect(identifier: str, sprite: Sprite, components: Dict[str, object], *, material: str = "particles_alpha",
           curves: Optional[dict] = None, frames: int = 1, fps: float = 8.0, stretch: bool = False) -> dict:
    comps = dict(components)
    bb = comps.get("minecraft:particle_appearance_billboard")
    if bb is not None and "uv" not in bb:
        bb["uv"] = sprite.uv(frames, fps, True, stretch)
    d = {"description": {"identifier": identifier,
                         "basic_render_parameters": {"material": material, "texture": sprite.texture}},
         "components": comps}
    if curves:
        d["curves"] = curves
    return {"format_version": "1.10.0", "particle_effect": d}


# --------------------------------------------------------------------------- component helpers

def once(count: Num, active: float = 0.05) -> dict:
    return {"minecraft:emitter_rate_instant": {"num_particles": count},
            "minecraft:emitter_lifetime_once": {"active_time": active}}


def steady(rate: Num, max_particles: Num, active: Num) -> dict:
    return {"minecraft:emitter_rate_steady": {"spawn_rate": rate, "max_particles": max_particles},
            "minecraft:emitter_lifetime_once": {"active_time": active}}


def point(offset=(0, 0, 0), direction=(0, 1, 0)) -> dict:
    return {"minecraft:emitter_shape_point": {"offset": list(offset), "direction": list(direction)}}


def sphere(radius: Num, direction="outwards", surface: bool = False, offset=(0, 0, 0)) -> dict:
    return {"minecraft:emitter_shape_sphere": {"offset": list(offset), "radius": radius, "surface_only": surface,
                                               "direction": direction}}


def disc(radius: Num, direction="outwards", surface: bool = False, offset=(0, 0, 0), normal=(0, 1, 0)) -> dict:
    return {"minecraft:emitter_shape_disc": {"offset": list(offset), "radius": radius, "plane_normal": list(normal),
                                             "surface_only": surface, "direction": direction}}


def box(half=(1, 1, 1), direction="outwards", offset=(0, 0, 0)) -> dict:
    return {"minecraft:emitter_shape_box": {"offset": list(offset), "half_dimensions": list(half),
                                            "direction": direction}}


def speed(v: Num) -> dict:
    return {"minecraft:particle_initial_speed": v}


def spin(rotation: Num = 0, rate: Num = 0) -> dict:
    return {"minecraft:particle_initial_spin": {"rotation": rotation, "rotation_rate": rate}}


def dynamic(accel=(0, 0, 0), drag: Num = 0, rot_accel: Num = 0, rot_drag: Num = 0) -> dict:
    d = {"linear_acceleration": list(accel), "linear_drag_coefficient": drag}
    if rot_accel or rot_drag:
        d["rotation_acceleration"] = rot_accel
        d["rotation_drag_coefficient"] = rot_drag
    return {"minecraft:particle_motion_dynamic": d}


def life(seconds: Num) -> dict:
    return {"minecraft:particle_lifetime_expression": {"max_lifetime": seconds}}


def billboard(size, facing: str = "rotate_xyz", direction: Optional[dict] = None) -> dict:
    d = {"size": list(size), "facing_camera_mode": facing}
    if direction:
        d["direction"] = direction
    return {"minecraft:particle_appearance_billboard": d}


def tint(r: Num, g: Num, b: Num, a: Num = 1) -> dict:
    return {"minecraft:particle_appearance_tinting": {"color": [r, g, b, a]}}


def gradient(stops: Dict[float, str], interpolant: str = "v.particle_age / v.particle_lifetime") -> dict:
    return {"minecraft:particle_appearance_tinting": {
        "color": {"interpolant": interpolant, "gradient": {f"{k:.2f}": v for k, v in stops.items()}}}}


def collide(drag: Num = 4, bounce: Num = 0.2, radius: Num = 0.05, expire: bool = False) -> dict:
    return {"minecraft:particle_motion_collision": {"collision_drag": drag, "coefficient_of_restitution": bounce,
                                                    "collision_radius": radius, "expire_on_contact": expire}}


def merge(*parts: dict) -> dict:
    out: dict = {}
    for p in parts:
        out.update(p)
    return out


AGE = "(v.particle_age / v.particle_lifetime)"
FADE_IN_OUT = f"math.clamp({AGE} * 8, 0, 1) * math.clamp((1 - {AGE}) * 5, 0, 1)"
FLAT = "emitter_transform_xz"


# --------------------------------------------------------------------------- telegraph primitives

def tg_line(identifier: str, sprite: Sprite, color, *, width: float = 0.34, density: float = 2.2,
            draw_time: float = 0.2, pulse: float = 0.25, material: str = "particles_blend") -> dict:
    """Ground line drawn from the emitter along (v.dx, v.dz) for v.len blocks; marks live for v.life s."""
    r, g, b = color
    prog = f"(v.emitter_age / {draw_time})"
    return effect(identifier, sprite, merge(
        steady(f"v.len * {density} / {draw_time}", 400, draw_time),
        point([f"v.dx * v.len * {prog}", 0, f"v.dz * v.len * {prog}"], [0, 0, 0]),
        speed(0), life("v.life"),
        billboard([width, width], FLAT),
        tint(r, g, b, f"({FADE_IN_OUT}) * ({1 - pulse} + {pulse} * math.sin(v.particle_age * 900))"),
    ), material=material)


def tg_arc(identifier: str, sprite: Sprite, color, *, width: float = 0.34, density: float = 2.0,
           draw_time: float = 0.2, pulse: float = 0.25, material: str = "particles_blend") -> dict:
    """Ground arc of radius v.r from angle v.a0 sweeping v.sweep degrees (0 = +X, 90 = +Z)."""
    r, g, b = color
    ang = f"(v.a0 + v.sweep * v.emitter_age / {draw_time})"
    return effect(identifier, sprite, merge(
        steady(f"math.max(4, v.r * math.abs(v.sweep) * 0.01745 * {density}) / {draw_time}", 500, draw_time),
        point([f"math.cos({ang}) * v.r", 0, f"math.sin({ang}) * v.r"], [0, 0, 0]),
        speed(0), life("v.life"),
        billboard([width, width], FLAT),
        tint(r, g, b, f"({FADE_IN_OUT}) * ({1 - pulse} + {pulse} * math.sin(v.particle_age * 900))"),
    ), material=material)


def tg_disc(identifier: str, sprite: Sprite, color, *, alpha: float = 0.55, grow: bool = True,
            material: str = "particles_blend") -> dict:
    """One flat quad of radius v.r that fills from the centre as the strike approaches."""
    r, g, b = color
    size = f"v.r * {AGE}" if grow else "v.r"
    return effect(identifier, sprite, merge(
        once(1), point(), speed(0), life("v.life"),
        billboard([size, size], FLAT),
        tint(r, g, b, f"{alpha} * math.clamp({AGE} * 6, 0, 1)"),
    ), material=material)


def tg_lane(identifier: str, sprite: Sprite, color, *, alpha: float = 0.5,
            material: str = "particles_blend") -> dict:
    """One flat quad: half-length v.len / 2, half-width v.w, yaw v.yaw; emitter at the lane centre.
    The fill brightens until the strike."""
    r, g, b = color
    return effect(identifier, sprite, merge(
        once(1), point(), speed(0), spin("v.yaw", 0), life("v.life"),
        billboard(["v.len * 0.5", "v.w"], FLAT),
        tint(r, g, b, f"{alpha} * (0.25 + 0.75 * {AGE}) * math.clamp({AGE} * 8, 0, 1)"),
    ), material=material)


def burst(identifier: str, sprite: Sprite, *, count: Num = 12, radius: Num = 0.3, vel: Num = 4,
          size: Num = 0.16, lifetime: Num = "0.4 + v.particle_random_1 * 0.5", gravity: float = 9,
          drag: float = 1.5, color=None, grad: Optional[Dict[float, str]] = None, spin_rate: Num = 0,
          material: str = "particles_alpha", frames: int = 1, shrink: bool = True, up: float = 0.0) -> dict:
    """Radial burst of debris/sparks."""
    s = f"{size} * (1 - {AGE} * 0.6)" if shrink else size
    parts = [once(count), sphere(radius), speed(f"{vel} * (0.5 + v.particle_random_2)"), life(lifetime),
             dynamic([0, up - gravity, 0], drag, 0, 0.4),
             billboard([s, s], "rotate_xyz" if not spin_rate else "lookat_xyz")]
    if spin_rate:
        parts.append(spin("v.particle_random_3 * 360", f"({spin_rate}) * (v.particle_random_4 - 0.5) * 2"))
    if grad:
        parts.append(gradient(grad))
    elif color:
        parts.append(tint(color[0], color[1], color[2], f"math.clamp((1 - {AGE}) * 3, 0, 1)"))
    return effect(identifier, sprite, merge(*parts), material=material, frames=frames)


def mote(identifier: str, sprite: Sprite, *, size: Num = 0.12, lifetime: Num = 0.8, rise: float = 0.3,
         color=(1, 1, 1), material: str = "particles_blend", drift: float = 0.15, frames: int = 1) -> dict:
    """A single gentle mote - spawned repeatedly by script or animation timelines."""
    r, g, b = color
    return effect(identifier, sprite, merge(
        once(1), point([0, 0, 0], [f"math.random(-{drift}, {drift})", 1, f"math.random(-{drift}, {drift})"]),
        speed(rise), life(lifetime), dynamic([0, 0, 0], 0.6),
        billboard([f"{size} * (1 - {AGE} * 0.5)", f"{size} * (1 - {AGE} * 0.5)"]),
        tint(r, g, b, FADE_IN_OUT),
    ), material=material, frames=frames)


def flyer(identifier: str, sprite: Sprite, *, size=(0.5, 0.5), color=(1, 1, 1), spin_rate: Num = 0,
          align: bool = False, material: str = "particles_alpha", frames: int = 1, fps: float = 10) -> dict:
    """A projectile visual: travels along v.dir (set with setSpeedAndDirection: variable.dir.speed,
    variable.dir.direction_x/y/z) for v.life seconds at constant speed. The script mirrors the motion
    for collision, so the sprite and the hit region stay together."""
    r, g, b = color
    bb = billboard(list(size), "lookat_direction" if align else "rotate_xyz",
                   {"mode": "derive_from_velocity"} if align else None)
    parts = [once(1), point([0, 0, 0], ["v.dir.direction_x", "v.dir.direction_y", "v.dir.direction_z"]),
             speed("v.dir.speed"), life("v.life"), dynamic([0, 0, 0], 0), bb,
             tint(r, g, b, f"math.clamp((1 - {AGE}) * 6, 0, 1)")]
    if spin_rate and not align:
        parts.append(spin("v.particle_random_1 * 360", spin_rate))
    return effect(identifier, sprite, merge(*parts), material=material, frames=frames, fps=fps)
