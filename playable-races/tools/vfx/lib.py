"""Building blocks for layered Bedrock particle effects (v1.3).

Every builder registers one particle effect (identifier plrace:<name>) and returns its name.
`compose()` makes an entry effect that fires its layers on a timeline through particle
events, so a script still spawns ONE identifier and gets a charged, layered effect.
All layers draw the white sprites of vfx/atlas.py and take their colour from the tint.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple, Union

from vfx import atlas

NS = "plrace"
REG: Dict[str, dict] = {}

AGE = "(v.particle_age / v.particle_lifetime)"
FADE = f"math.clamp((1 - {AGE}) * 3, 0, 1)"                          # hold, then fade over the last third
IN_OUT = f"math.clamp(math.min({AGE} * 6, (1 - {AGE}) * 2.5), 0, 1)"  # quick rise, hold, soft fade
EASE_OUT = f"(1 - (1 - {AGE}) * (1 - {AGE}))"                         # fast start, slow end

Num = Union[float, str]


def rgb(hexstr: str) -> Tuple[float, float, float]:
    h = hexstr.lstrip("#")
    return tuple(round(int(h[i:i + 2], 16) / 255.0, 3) for i in (0, 2, 4))


def mix(a: str, b: str, t: float) -> str:
    ca, cb = rgb(a), rgb(b)
    return "#" + "".join(f"{int(round((x + (y - x) * t) * 255)):02x}" for x, y in zip(ca, cb))


def _f(x: Num) -> Num:
    return round(x, 4) if isinstance(x, float) else x


def tint(color: str, alpha: Num = 1.0) -> dict:
    r, g, b = rgb(color)
    return {"color": [r, g, b, _f(alpha)]}


def tint_grad(stops: Sequence[Tuple[float, str, float]]) -> dict:
    """[(t, '#rrggbb', alpha)] over the particle's life."""
    grad = {}
    for t, c, a in stops:
        r, g, b = rgb(c)
        grad[f"{t:.2f}"] = [r, g, b, round(a, 3)]
    return {"color": {"gradient": grad, "interpolant": AGE}}


def uv_flip(book: str, fps: Optional[float] = None, loop: bool = False) -> dict:
    x, y = atlas.FLIP[book]
    fb = {"base_UV": [x, y], "size_UV": [atlas.CELL, atlas.CELL], "step_UV": [atlas.CELL, 0], "max_frame": atlas.FRAMES,
          "loop": loop}
    if fps is None:
        fb["stretch_to_lifetime"] = True
        fb["frames_per_second"] = 8
    else:
        fb["stretch_to_lifetime"] = False
        fb["frames_per_second"] = round(fps, 3)
    return {"texture_width": atlas.W, "texture_height": atlas.H, "flipbook": fb}


def uv_frame(book: str, frame: int) -> dict:
    x, y = atlas.FLIP[book]
    return {"texture_width": atlas.W, "texture_height": atlas.H, "uv": [x + frame * atlas.CELL, y], "uv_size": [atlas.CELL, atlas.CELL]}


def uv_sprite(name: str) -> dict:
    x, y, w, h = atlas.SPR[name]
    return {"texture_width": atlas.W, "texture_height": atlas.H, "uv": [x, y], "uv_size": [w, h]}


def uv_pick(names: Sequence[str]) -> dict:
    """One of several consecutive sprites, picked per particle."""
    x0, y0, w, h = atlas.SPR[names[0]]
    for i, n_ in enumerate(names):
        assert atlas.SPR[n_] == (x0 + i * w, y0, w, h), "uv_pick needs consecutive sprites in one row"
    return {"texture_width": atlas.W, "texture_height": atlas.H,
            "uv": [f"{x0} + math.floor(v.particle_random_3 * {len(names)}) * {w}", y0], "uv_size": [w, h]}


def billboard(size: Sequence[Num], uv: dict, mode: str = "lookat_xyz", direction: Optional[dict] = None) -> dict:
    bb = {"size": [_f(size[0]), _f(size[1])], "facing_camera_mode": mode, "uv": uv}
    if direction is not None:
        bb["direction"] = direction
    return {"minecraft:particle_appearance_billboard": bb}


def effect(name: str, material: str, comps: dict, texture: str = atlas.TEX, events: Optional[dict] = None,
           curves: Optional[dict] = None) -> str:
    assert name not in REG, f"effect {name} defined twice"
    pe = {"description": {"identifier": f"{NS}:{name}", "basic_render_parameters": {"material": material, "texture": texture}}}
    if curves:
        pe["curves"] = curves
    if events:
        pe["events"] = events
    pe["components"] = comps
    REG[name] = {"format_version": "1.10.0", "particle_effect": pe}
    return name


def _once(n: int, active: float = 0.05) -> dict:
    return {"minecraft:emitter_rate_instant": {"num_particles": n}, "minecraft:emitter_lifetime_once": {"active_time": active}}


def _life(lo: float, hi: Optional[float] = None) -> dict:
    expr = lo if hi is None else f"{lo} + v.particle_random_1 * {round(hi - lo, 3)}"
    return {"minecraft:particle_lifetime_expression": {"max_lifetime": expr}}


def _offset(off) -> dict:
    return {"offset": [_f(o) for o in off]} if off and any(off) else {}


# ============================================================================= layers

def flash(name, color, size=1.6, life=0.32, alpha=1.0, offset=(0, 0, 0), material="particles_add"):
    """A starburst flash (8-frame flipbook) at the effect's position."""
    return effect(name, material, {**_once(1), "minecraft:emitter_shape_point": _offset(offset), **_life(life),
                                   **billboard([size, size], uv_flip("flash")), "minecraft:particle_appearance_tinting": tint(color, alpha)})


def ring(name, color, size=4.0, life=0.6, ground=True, alpha=1.0, offset=(0, 0, 0), material="particles_add", grow=0.0):
    """An expanding shockwave ring (flat on the ground, or facing the camera)."""
    s = size if not grow else f"{size} * (1 + {grow} * {AGE})"
    return effect(name, material, {**_once(1), "minecraft:emitter_shape_point": _offset(offset), **_life(life),
                                   **billboard([s, s], uv_flip("ring"), "emitter_transform_xz" if ground else "lookat_xyz"),
                                   "minecraft:particle_appearance_tinting": tint(color, alpha)})


def circle(name, color, size=4.0, life=2.0, draw=0.45, spin=18.0, alpha=0.95, offset=(0, 0.06, 0), material="particles_add",
           size_expr: Optional[str] = None, life_expr: Optional[str] = None):
    """A magic circle that draws itself in `draw` seconds, then turns slowly and fades."""
    s = size_expr or size
    life_c = {"minecraft:particle_lifetime_expression": {"max_lifetime": life_expr or life}}
    return effect(name, material, {**_once(1), "minecraft:emitter_shape_point": _offset(offset), **life_c,
                                   "minecraft:particle_initial_spin": {"rotation": "v.particle_random_2 * 360", "rotation_rate": spin},
                                   **billboard([s, s], uv_flip("circle", fps=atlas.FRAMES / draw), "emitter_transform_xz"),
                                   "minecraft:particle_appearance_tinting": tint(color, f"{alpha} * {FADE}")})


def slash(name, color, size=2.2, life=0.3, rot: Num = 0, offset=(0, 0, 0), material="particles_add", mode="lookat_xyz",
          size_expr: Optional[str] = None):
    s = size_expr or size
    return effect(name, material, {**_once(1), "minecraft:emitter_shape_point": _offset(offset), **_life(life),
                                   "minecraft:particle_initial_spin": {"rotation": rot, "rotation_rate": 0},
                                   **billboard([s, s], uv_flip("slash"), mode), "minecraft:particle_appearance_tinting": tint(color)})


def sparks(name, color, n=12, speed=(3.0, 6.0), life=(0.25, 0.5), gravity=-6.0, drag=2.5, width=0.05, length=0.32,
           radius=0.15, up=0.0, material="particles_add", hot: Optional[str] = None, offset=(0, 0, 0)):
    """Velocity-stretched sparks bursting outward (streak sprites aligned with their motion)."""
    col = tint_grad([(0.0, hot or "#ffffff", 1.0), (0.35, color, 1.0), (1.0, color, 0.0)])
    return effect(name, material, {
        **_once(n), "minecraft:emitter_shape_sphere": {"radius": radius, "direction": "outwards", **_offset(offset)},
        "minecraft:particle_initial_speed": f"{speed[0]} + v.particle_random_2 * {round(speed[1] - speed[0], 3)}",
        **_life(*life), "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, gravity, 0], "linear_drag_coefficient": drag},
        **billboard([width, f"{length} * (1 - {AGE} * 0.6)"], uv_sprite("streak"), "lookat_direction",
                    {"mode": "derive_from_velocity", "min_speed_threshold": 0.01}),
        "minecraft:particle_appearance_tinting": col})


def motes(name, color, n=8, radius=0.8, rise=0.6, life=(0.8, 1.4), size=0.08, sprite="dot", material="particles_add",
          rate: Optional[float] = None, active=0.05, offset=(0, 0, 0), alpha=1.0, spin=0.0, uv: Optional[dict] = None,
          texture: str = atlas.TEX, speed=0.1, drag=1.5):
    rate_c = _once(n, active) if rate is None else {"minecraft:emitter_rate_steady": {"spawn_rate": rate, "max_particles": n},
                                                    "minecraft:emitter_lifetime_once": {"active_time": active}}
    uvd = uv or (uv_sprite(sprite) if isinstance(sprite, str) else uv_pick(sprite))
    comps = {**rate_c, "minecraft:emitter_shape_sphere": {"radius": radius, "direction": "outwards", **_offset(offset)},
             "minecraft:particle_initial_speed": speed, **_life(*life),
             "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, rise, 0], "linear_drag_coefficient": drag},
             **billboard([f"{size} * {IN_OUT}", f"{size} * {IN_OUT}"], uvd),
             "minecraft:particle_appearance_tinting": tint(color, alpha)}
    if spin:
        comps["minecraft:particle_initial_spin"] = {"rotation": "v.particle_random_2 * 360", "rotation_rate": f"{spin} * (v.particle_random_4 * 2 - 1)"}
    return effect(name, material, comps, texture=texture)


def smoke(name, color, n=4, radius=0.4, size=(0.7, 1.4), life=(0.8, 1.3), rise=0.5, alpha=0.6, material="particles_blend",
          offset=(0, 0, 0), speed=0.4):
    return effect(name, material, {
        **_once(n), "minecraft:emitter_shape_sphere": {"radius": radius, "direction": "outwards", **_offset(offset)},
        "minecraft:particle_initial_speed": speed, **_life(*life),
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, rise, 0], "linear_drag_coefficient": 2.0},
        "minecraft:particle_initial_spin": {"rotation": "v.particle_random_2 * 360", "rotation_rate": "v.particle_random_3 * 40 - 20"},
        **billboard([f"{size[0]} + {AGE} * {round(size[1] - size[0], 3)}", f"{size[0]} + {AGE} * {round(size[1] - size[0], 3)}"],
                    uv_flip("smoke")),
        "minecraft:particle_appearance_tinting": tint(color, alpha)})


def debris(name, color, n=8, speed=(2.5, 4.5), life=(0.9, 1.3), size=0.13, sprite="chunk", gravity=-16.0, bounce=0.35,
           material="particles_blend", up=0.6, radius=0.3, offset=(0, 0, 0), uv: Optional[dict] = None, texture: str = atlas.TEX,
           lit: bool = True):
    """Chunks flung up and out that tumble, bounce on blocks and settle."""
    return effect(name, material, {
        **_once(n), "minecraft:emitter_shape_sphere": {"radius": radius, "direction": ["math.random(-1, 1)", f"{up} + v.emitter_random_1 * 0.2", "math.random(-1, 1)"],
                                                      **_offset(offset)},
        "minecraft:particle_initial_speed": f"{speed[0]} + v.particle_random_2 * {round(speed[1] - speed[0], 3)}",
        **_life(*life), "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, gravity, 0], "linear_drag_coefficient": 0.4},
        "minecraft:particle_motion_collision": {"collision_radius": 0.08, "coefficient_of_restitution": bounce, "collision_drag": 3.0},
        "minecraft:particle_initial_spin": {"rotation": "v.particle_random_2 * 360", "rotation_rate": "v.particle_random_3 * 600 - 300"},
        **billboard([size, size], uv or (uv_sprite(sprite) if isinstance(sprite, str) else uv_pick(sprite))),
        "minecraft:particle_appearance_tinting": tint(color, FADE), **({"minecraft:particle_appearance_lighting": {}} if lit else {})},
        texture=texture)


def pillar(name, color, height=3.0, width=0.7, life=0.8, alpha=0.9, offset=(0, 0, 0), material="particles_add", rise=0.0):
    """A column of light standing on the ground (faces the camera around the vertical axis)."""
    h = f"{height} * math.min(1, {AGE} * 5)"
    off = (offset[0], offset[1] + height / 2, offset[2])
    comps = {**_once(1), "minecraft:emitter_shape_point": _offset(off), **_life(life),
             **billboard([width, h], uv_sprite("streak"), "lookat_y"), "minecraft:particle_appearance_tinting": tint(color, f"{alpha} * {FADE}")}
    if rise:
        comps["minecraft:particle_initial_speed"] = 0
        comps["minecraft:particle_motion_dynamic"] = {"linear_acceleration": [0, rise, 0]}
    return effect(name, material, comps)


def converge(name, color, n=14, radius=1.6, life=0.4, size=0.07, material="particles_add", offset=(0, 0, 0)):
    """Charge-up: motes stream in from a sphere to the centre."""
    return effect(name, material, {
        **_once(n), "minecraft:emitter_shape_sphere": {"radius": radius, "surface_only": True, "direction": "inwards", **_offset(offset)},
        "minecraft:particle_initial_speed": round(radius / life * 0.95, 3), **_life(life),
        **billboard([size, f"{size} * 4"], uv_sprite("streak"), "lookat_direction",
                    {"mode": "derive_from_velocity", "min_speed_threshold": 0.01}),
        "minecraft:particle_appearance_tinting": tint_grad([(0.0, color, 0.0), (0.3, color, 1.0), (1.0, "#ffffff", 1.0)])})


def glyphs(name, color, n=6, radius=1.0, rise=0.9, life=(0.9, 1.4), size=0.24, sprites=("rune1", "rune2", "rune3", "rune4"),
           material="particles_add", offset=(0, 0, 0), uv: Optional[dict] = None, texture: str = atlas.TEX):
    return effect(name, material, {
        **_once(n), "minecraft:emitter_shape_disc": {"radius": radius, "plane_normal": "y", **_offset(offset)},
        "minecraft:particle_initial_speed": 0.0, **_life(*life),
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, rise, 0], "linear_drag_coefficient": 1.2},
        **billboard([f"{size} * {IN_OUT}", f"{size} * {IN_OUT}"], uv or uv_pick(list(sprites))),
        "minecraft:particle_appearance_tinting": tint(color)}, texture=texture)


def splash(name, color, size=1.6, life=0.45, material="particles_blend", offset=(0, 0, 0), alpha=1.0):
    return effect(name, material, {**_once(1), "minecraft:emitter_shape_point": _offset(offset), **_life(life),
                                   **billboard([size, size], uv_flip("splash")), "minecraft:particle_appearance_tinting": tint(color, alpha),
                                   "minecraft:particle_appearance_lighting": {}})


def crack(name, color, size=2.6, life=0.9, alpha=1.0, offset=(0, 0.04, 0), material="particles_add"):
    """A branching crack of light flat on the ground."""
    return effect(name, material, {**_once(1), "minecraft:emitter_shape_point": _offset(offset), **_life(life),
                                   "minecraft:particle_initial_spin": {"rotation": "v.particle_random_2 * 360", "rotation_rate": 0},
                                   **billboard([size, size], uv_flip("crack"), "emitter_transform_xz"),
                                   "minecraft:particle_appearance_tinting": tint(color, alpha)})


# ============================================================================= composition

def compose(name: str, parts: Sequence[Tuple[float, str]], own: Optional[dict] = None, material="particles_add",
            texture: str = atlas.TEX, curves: Optional[dict] = None) -> str:
    """An entry effect: fires each layer (child effect) at its time through particle events.
    `own` (optional components) gives the entry effect its own particles - layers that read
    the variables the script passes in (direction, length, colour...) belong there, since
    child emitters do not inherit them."""
    events, timeline, creation = {}, {}, []
    for i, (t, child) in enumerate(parts):
        ev = f"l{i}"
        events[ev] = {"particle_effect": {"effect": f"{NS}:{child}", "type": "emitter"}}
        if t <= 0.0:
            creation.append(ev)
        else:
            timeline.setdefault(f"{t:.2f}", []).append(ev)
    last = max([t for t, _ in parts] + [0.0])
    comps = dict(own) if own else {**_once(1), "minecraft:emitter_shape_point": {}, **_life(0.05),
                                   **billboard([0, 0], uv_sprite("dot"))}
    life_key = next((k for k in comps if k.startswith("minecraft:emitter_lifetime")), None)
    if life_key == "minecraft:emitter_lifetime_once":
        comps[life_key] = {"active_time": round(max(float(comps[life_key].get("active_time", 0.05)), last + 0.1), 3)}
    lev = {}
    if creation:
        lev["creation_event"] = creation if len(creation) > 1 else creation[0]
    if timeline:
        lev["timeline"] = {k: (v if len(v) > 1 else v[0]) for k, v in sorted(timeline.items(), key=lambda kv: float(kv[0]))}
    comps["minecraft:emitter_lifetime_events"] = lev
    return effect(name, material, comps, texture=texture, events=events, curves=curves)


def particle_count(name: str, seen=None) -> int:
    """Upper bound of particles one spawn of `name` creates (its own + every layer it fires)."""
    seen = seen or set()
    if name in seen or name not in REG:
        return 0
    seen.add(name)
    pe = REG[name]["particle_effect"]
    c = pe["components"]
    own = 0
    if "minecraft:emitter_rate_instant" in c:
        own = int(c["minecraft:emitter_rate_instant"]["num_particles"])
    elif "minecraft:emitter_rate_steady" in c:
        own = int(c["minecraft:emitter_rate_steady"]["max_particles"])
    kids = 0
    for ev in pe.get("events", {}).values():
        child = ev.get("particle_effect", {}).get("effect", "").split(":")[-1]
        kids += particle_count(child, set(seen))
    return own + kids
