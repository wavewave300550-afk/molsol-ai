"""Particle sprite atlas + particle effect definitions (colour/size/radius/count/dir from script)."""
import math
import numpy as np
from PIL import Image
from .fxdefs import dump

CELL = 16
ATLAS = 128
TEX = "textures/particle/grimoire_particles"

SPRITES = ["soft", "ring", "thin_ring", "spark", "snowflake", "shard", "droplet", "petal",
           "hex", "rune_a", "rune_b", "smoke", "streak", "crescent", "heart", "hoofprint",
           "ripple", "fragment", "square", "dot", "star", "thorn", "root", "prism",
           # expansion 02 (appended: existing atlas cells keep their positions)
           "filament", "triangle", "footprint", "glint", "lens", "slit"]


def _heart(cx, cy, s):
    pts = []
    for i in range(40):
        t = math.tau * i / 40
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s, cy - y * s))
    return pts


def sprite(name):
    """Draw one 16x16 white sprite (tinted by particles). Returns RGBA float array."""
    from .art import Art
    a = Art(CELL, CELL, ss=8)
    W = (255, 255, 255)
    c = CELL / 2
    if name == "soft":
        a.radial_glow(c, c, 7.5, W, 1.0)
    elif name == "ring":
        a.circle(c, c, 6.6, outline=W, width=1.4)
        a.radial_glow(c, c, 7.5, (90, 90, 90), 0.3)
    elif name == "thin_ring":
        a.circle(c, c, 7.0, outline=W, width=0.6)
    elif name == "spark":
        a.poly([(c, 0.5), (c + 1.2, c - 1.2), (15.5, c), (c + 1.2, c + 1.2), (c, 15.5), (c - 1.2, c + 1.2), (0.5, c), (c - 1.2, c - 1.2)], fill=W)
        a.radial_glow(c, c, 4, W, 0.8)
    elif name == "snowflake":
        a.star6(c, c, 6.8, W, 0.9)
    elif name == "shard":
        a.poly([(c, 0.5), (c + 3, c), (c, 15.5), (c - 2, c + 2)], fill=W)
    elif name == "droplet":
        a.circle(c, c + 2, 4.2, fill=W)
        a.poly([(c - 3.6, c + 0.5), (c, 1.0), (c + 3.6, c + 0.5)], fill=W)
    elif name == "petal":
        a.poly([(c, 1), (c + 5, 5), (c + 4, 12), (c, 15), (c - 4, 12), (c - 5, 5)], fill=W)
    elif name == "hex":
        a.hexagon(c, c, 6.8, W, 1.2)
    elif name in ("rune_a", "rune_b"):
        rs = np.random.RandomState(7 if name == "rune_a" else 9)
        a.circle(c, c, 6.8, outline=W, width=0.6)
        for _ in range(5):
            x0, y0 = rs.randint(4, 12), rs.randint(4, 12)
            a.line([(x0, y0), (rs.randint(4, 12), rs.randint(4, 12))], W, 0.9)
    elif name == "smoke":
        for i in range(5):
            ang = i * 1.256
            a.radial_glow(c + math.cos(ang) * 2.5, c + math.sin(ang) * 2.5, 5, (200, 200, 200), 0.6)
    elif name == "streak":
        a.poly([(c - 0.9, 0.5), (c + 0.9, 0.5), (c + 0.4, 15.5), (c - 0.4, 15.5)], fill=W)
    elif name == "crescent":
        a.circle(c, c, 6.8, fill=W)
        a.circle(c + 3.2, c - 1.2, 6.2, fill=(0, 0, 0))
    elif name == "heart":
        a.poly(_heart(c, c + 0.5, 0.42), fill=W)
    elif name == "hoofprint":
        a.poly([(c - 4.5, 3), (c - 0.6, 3), (c - 0.6, 13), (c - 4.5, 11)], fill=W)
        a.poly([(c + 0.6, 3), (c + 4.5, 3), (c + 4.5, 11), (c + 0.6, 13)], fill=W)
    elif name == "ripple":
        pts = [(c + math.cos(t / 30 * math.tau) * (6 + math.sin(t / 30 * math.tau * 6) * 0.8),
                c + math.sin(t / 30 * math.tau) * (6 + math.sin(t / 30 * math.tau * 6) * 0.8)) for t in range(31)]
        a.line(pts, W, 0.9)
    elif name == "fragment":
        a.poly([(c, 1), (c + 4.5, c), (c, 15), (c - 4.5, c)], fill=W)
    elif name == "square":
        a.rect(1.5, 1.5, 14.5, 14.5, outline=W, width=1.0)
    elif name == "dot":
        a.circle(c, c, 2.2, fill=W)
    elif name == "star":
        pts = []
        for i in range(10):
            r = 7 if i % 2 == 0 else 2.6
            ang = -math.pi / 2 + i * math.pi / 5
            pts.append((c + math.cos(ang) * r, c + math.sin(ang) * r))
        a.poly(pts, fill=W)
    elif name == "thorn":
        a.poly([(c - 2.2, 15), (c + 2.2, 15), (c + 0.4, 0.5), (c - 0.4, 0.5)], fill=W)
    elif name == "root":
        a.line([(2, 14), (6, 9), (8, 10), (12, 4), (14, 2)], W, 1.0)
        a.line([(6, 9), (5, 5)], W, 0.7)
    elif name == "prism":
        a.hexagon(c, c, 6.5, W, 1.0, fill=(200, 200, 200))
    elif name == "filament":
        a.line([(c + math.sin(t / 15 * math.tau * 1.5) * 2.4, 0.5 + t) for t in range(16)], W, 0.9)
        a.radial_glow(c, c, 3, W, 0.5)
    elif name == "triangle":
        a.poly([(c, 1.5), (14.5, 14), (1.5, 14)], fill=W)
    elif name == "footprint":
        a.poly([(c - 2.5, 4), (c + 2.5, 3.5), (c + 3, 9), (c + 1.5, 14.5), (c - 2, 14.5), (c - 3.2, 9)], fill=W)
        for k in range(4):
            a.circle(c - 2.4 + k * 1.6, 1.8, 0.8, fill=W)
    elif name == "glint":
        a.poly([(c, 0.5), (c + 0.8, c - 0.8), (15.5, c), (c + 0.8, c + 0.8), (c, 15.5), (c - 0.8, c + 0.8), (0.5, c), (c - 0.8, c - 0.8)], fill=W)
        a.poly([(c - 3, c - 3), (c, c - 0.8), (c + 3, c - 3), (c + 0.8, c), (c + 3, c + 3), (c, c + 0.8), (c - 3, c + 3), (c - 0.8, c)], fill=(150, 150, 150))
    elif name == "lens":
        a.circle(c, c, 6.6, outline=W, width=0.8)
        a.circle(c - 1.8, c - 1.8, 1.6, fill=W)
    elif name == "slit":
        a.poly([(c, 0.5), (c + 2.2, c), (c, 15.5), (c - 2.2, c)], fill=W)
    out = a.finish(emissive=False, alpha_from_glow=False)
    lum = out[..., :3].max(-1)
    out[..., 3] = np.clip(lum, 0, 255)
    out[..., :3] = 255
    return out


def write_atlas(rp):
    img = np.zeros((ATLAS, ATLAS, 4), np.float32)
    for i, n in enumerate(SPRITES):
        x, y = (i % 8) * CELL, (i // 8) * CELL
        img[y:y + CELL, x:x + CELL] = sprite(n)
    Image.fromarray(img.astype(np.uint8), 'RGBA').save(f"{rp}/{TEX}.png")


def uv(name):
    i = SPRITES.index(name)
    return {"texture_width": ATLAS, "texture_height": ATLAS, "uv": [(i % 8) * CELL, (i // 8) * CELL], "uv_size": [CELL, CELL]}


FADE = "math.clamp(1 - variable.particle_age / variable.particle_lifetime, 0, 1)"
FADE_IN_OUT = "math.clamp(math.min(variable.particle_age * 8, (1 - variable.particle_age / variable.particle_lifetime) * 2.5), 0, 1)"


def effect(ident, sprite_name, *, material="particles_add", rate=None, burst=None, life_emitter=0.1, looping_time=None,
           shape=("point", {}), lifetime="0.6", speed=None, accel=(0, 0, 0), drag=0.0, size="0.1",
           facing="lookat_xyz", direction=None, tint=None, alpha=FADE, rotation=None, rot_rate=None,
           init_expr=None, collision=False, lit=False):
    comps = {}
    if init_expr:
        comps["minecraft:emitter_initialization"] = {"creation_expression": init_expr}
    if burst is not None:
        comps["minecraft:emitter_rate_instant"] = {"num_particles": burst}
        comps["minecraft:emitter_lifetime_once"] = {"active_time": life_emitter}
    else:
        comps["minecraft:emitter_rate_steady"] = {"spawn_rate": rate, "max_particles": 400}
        comps["minecraft:emitter_lifetime_once"] = {"active_time": looping_time or life_emitter}
    kind, sargs = shape
    comps[f"minecraft:emitter_shape_{kind}"] = sargs
    comps["minecraft:particle_lifetime_expression"] = {"max_lifetime": lifetime}
    if speed is not None:
        comps["minecraft:particle_initial_speed"] = speed
    if rotation is not None or rot_rate is not None:
        comps["minecraft:particle_initial_spin"] = {"rotation": rotation or "variable.particle_random_3 * 360", "rotation_rate": rot_rate or 0}
    motion = {"linear_acceleration": list(accel), "linear_drag_coefficient": drag}
    if rot_rate is not None:
        motion["rotation_acceleration"] = 0
    comps["minecraft:particle_motion_dynamic"] = motion
    bb = {"size": size if isinstance(size, list) else [size, size], "facing_camera_mode": facing, "uv": uv(sprite_name)}
    if direction is not None:
        bb["direction"] = direction
    comps["minecraft:particle_appearance_billboard"] = bb
    col = tint or ["variable.color.r", "variable.color.g", "variable.color.b"]
    comps["minecraft:particle_appearance_tinting"] = {"color": col + [alpha]}
    if lit:
        comps["minecraft:particle_appearance_lighting"] = {}
    if collision:
        comps["minecraft:particle_motion_collision"] = {"collision_radius": 0.05, "coefficient_of_restitution": 0.1, "collision_drag": 4, "expire_on_contact": False}
    return {
        "format_version": "1.10.0",
        "particle_effect": {
            "description": {"identifier": ident, "basic_render_parameters": {"material": material, "texture": TEX}},
            "components": comps,
        },
    }


R = "variable.particle_random_"
DIR = ["variable.dir.direction_x", "variable.dir.direction_y", "variable.dir.direction_z"]
MIX = [f"math.lerp(variable.color.r, variable.color2.r, {R}4)", f"math.lerp(variable.color.g, variable.color2.g, {R}4)",
       f"math.lerp(variable.color.b, variable.color2.b, {R}4)"]


def all_effects():
    E = {}
    for school, spr in (("pressure", "ring"), ("ice", "snowflake"), ("blood", "droplet")):
        E[f"grimoire:{school}_charge"] = effect(
            f"grimoire:{school}_charge", "spark" if school == "pressure" else spr, burst="6 + variable.size * 6",
            shape=("sphere", {"radius": "0.6 * variable.radius + 0.2", "surface_only": True, "direction": "inwards"}),
            lifetime="0.35", speed="2.2 * variable.radius + 0.5", drag=1.0, size="0.06 + 0.06 * variable.size",
            alpha=FADE_IN_OUT, rotation=f"{R}3 * 360")
    E["grimoire:spark_burst"] = effect("grimoire:spark_burst", "spark", burst="10 * variable.count",
        shape=("sphere", {"radius": "0.25 * variable.radius", "direction": "outwards"}), lifetime=f"0.35 + {R}1 * 0.4",
        speed=f"(3 + {R}2 * 5) * variable.radius", drag=3.5, size=f"(0.06 + {R}3 * 0.08) * variable.size", tint=MIX)
    E["grimoire:glow_flash"] = effect("grimoire:glow_flash", "soft", burst="1", lifetime="0.25 * variable.life + 0.05",
        size=f"variable.size * (0.6 + variable.particle_age / variable.particle_lifetime * 0.8)")
    E["grimoire:ring_h"] = effect("grimoire:ring_h", "ring", burst="1", lifetime="0.45 * variable.life",
        size="variable.radius * (0.15 + 0.85 * math.sqrt(variable.particle_age / variable.particle_lifetime))",
        facing="emitter_transform_xz", tint=MIX)
    E["grimoire:ripple_h"] = effect("grimoire:ripple_h", "ripple", burst="2", lifetime=f"0.5 * variable.life + {R}1 * 0.1",
        size=f"variable.radius * (0.2 + 0.8 * variable.particle_age / variable.particle_lifetime) * (0.9 + {R}2 * 0.2)",
        facing="emitter_transform_xz", rotation=f"{R}3 * 360", alpha=f"0.7 * {FADE}")
    E["grimoire:ring_dir"] = effect("grimoire:ring_dir", "ring", burst="1", lifetime="0.4 * variable.life",
        shape=("point", {"direction": DIR}), speed="0.01",
        size="variable.radius * (0.2 + 0.8 * math.sqrt(variable.particle_age / variable.particle_lifetime))",
        facing="direction_z", direction={"mode": "custom", "custom_direction": DIR}, tint=MIX)
    E["grimoire:ripple_dir"] = effect("grimoire:ripple_dir", "ripple", burst="2", lifetime="0.45 * variable.life",
        shape=("point", {"direction": DIR}), speed="0.01",
        size=f"variable.radius * (0.25 + 0.75 * variable.particle_age / variable.particle_lifetime) * (0.85 + {R}2 * 0.3)",
        facing="direction_z", direction={"mode": "custom", "custom_direction": DIR}, rotation=f"{R}3 * 360", alpha=f"0.6 * {FADE}")
    E["grimoire:trail"] = effect("grimoire:trail", "soft", burst="1 + variable.count", lifetime=f"0.4 * variable.life + {R}1 * 0.2",
        shape=("sphere", {"radius": "0.12 * variable.radius"}), speed="0.3", drag=2, size=f"0.12 * variable.size * {FADE}", tint=MIX)
    E["grimoire:streak_dir"] = effect("grimoire:streak_dir", "streak", burst="4 * variable.count", lifetime=f"0.25 + {R}1 * 0.15",
        shape=("sphere", {"radius": "0.5 * variable.radius", "direction": DIR}), speed=f"(8 + {R}2 * 6) * variable.dir.speed",
        drag=2, size=["0.04 * variable.size", "0.5 * variable.size"], facing="lookat_direction", tint=MIX)
    E["grimoire:shard_burst"] = effect("grimoire:shard_burst", "shard", burst="12 * variable.count",
        shape=("sphere", {"radius": "0.3 * variable.radius", "direction": "outwards"}), lifetime=f"0.6 + {R}1 * 0.6",
        speed=f"(3 + {R}2 * 5) * variable.radius", accel=(0, -14, 0), drag=1.2, size=f"(0.08 + {R}3 * 0.12) * variable.size",
        rotation=f"{R}3 * 360", rot_rate=f"({R}4 - 0.5) * 720", tint=MIX, collision=True)
    E["grimoire:snow_burst"] = effect("grimoire:snow_burst", "snowflake", burst="14 * variable.count",
        shape=("sphere", {"radius": "0.4 * variable.radius", "direction": "outwards"}), lifetime=f"0.8 + {R}1 * 0.8",
        speed=f"(1 + {R}2 * 2.5) * variable.radius", accel=(0, -1.2, 0), drag=2.0, size=f"(0.06 + {R}3 * 0.08) * variable.size",
        rotation=f"{R}3 * 360", rot_rate=f"({R}4 - 0.5) * 240", tint=MIX)
    E["grimoire:snow_storm"] = effect("grimoire:snow_storm", "snowflake", burst="30 * variable.count",
        shape=("disc", {"radius": "variable.radius", "plane_normal": "y", "offset": [0, f"{R}1 * 3", 0]}),
        lifetime=f"0.9 + {R}2 * 0.6", speed="2",
        accel=(f"math.sin(variable.particle_age * 300 + {R}3 * 360) * 6", -3, f"math.cos(variable.particle_age * 300 + {R}3 * 360) * 6"),
        drag=0.6, size=f"(0.05 + {R}4 * 0.07) * variable.size", rotation=f"{R}3 * 360", rot_rate="200", tint=MIX, alpha=FADE_IN_OUT)
    E["grimoire:snow_still"] = effect("grimoire:snow_still", "snowflake", burst="40 * variable.count",
        shape=("box", {"half_dimensions": ["variable.radius", "variable.radius * 0.35", "variable.radius"], "offset": [0, "variable.radius * 0.3", 0]}),
        lifetime=f"2.6 + {R}1 * 1.2", speed="0.02", accel=(0, 0.02, 0), drag=0.2,
        size=f"(0.05 + {R}2 * 0.08) * variable.size", rotation=f"{R}3 * 360", rot_rate="12", tint=MIX, alpha=FADE_IN_OUT)
    E["grimoire:mist"] = effect("grimoire:mist", "smoke", material="particles_blend", burst="6 * variable.count",
        shape=("sphere", {"radius": "variable.radius", "direction": "outwards"}), lifetime=f"1.2 * variable.life + {R}1 * 0.8",
        speed="0.4", drag=1.0, size=f"(0.6 + {R}2 * 0.6) * variable.size * (0.6 + 0.4 * variable.particle_age / variable.particle_lifetime)",
        rotation=f"{R}3 * 360", rot_rate="20", tint=MIX, alpha=f"0.45 * {FADE_IN_OUT}")
    E["grimoire:droplet_burst"] = effect("grimoire:droplet_burst", "droplet", material="particles_blend", burst="12 * variable.count",
        shape=("sphere", {"radius": "0.25 * variable.radius", "direction": "outwards"}), lifetime=f"0.7 + {R}1 * 0.6",
        speed=f"(2 + {R}2 * 4) * variable.radius", accel=(0, -16, 0), drag=0.8, size=f"(0.06 + {R}3 * 0.08) * variable.size",
        tint=MIX, collision=True, alpha="1")
    E["grimoire:blood_rain"] = effect("grimoire:blood_rain", "streak", material="particles_blend", burst="40 * variable.count",
        shape=("disc", {"radius": "variable.radius", "plane_normal": "y", "offset": [0, "6", 0], "direction": [0, -1, 0]}),
        lifetime="0.9", speed=f"16 + {R}2 * 6", accel=(0, -10, 0), size=["0.03 * variable.size", "0.35 * variable.size"],
        facing="lookat_direction", tint=MIX, collision=True, alpha="0.9")
    E["grimoire:petal_burst"] = effect("grimoire:petal_burst", "petal", material="particles_blend", burst="12 * variable.count",
        shape=("sphere", {"radius": "0.5 * variable.radius", "direction": "outwards"}), lifetime=f"1.0 + {R}1 * 0.8",
        speed=f"(1 + {R}2 * 3) * variable.radius", accel=(0, -2.5, 0), drag=1.6, size=f"(0.08 + {R}3 * 0.1) * variable.size",
        rotation=f"{R}3 * 360", rot_rate=f"({R}4 - 0.5) * 400", tint=MIX, alpha=FADE_IN_OUT)
    E["grimoire:converge"] = effect("grimoire:converge", "spark", burst="18 * variable.count",
        shape=("sphere", {"radius": "variable.radius", "surface_only": True, "direction": "inwards"}), lifetime="0.55 * variable.life",
        speed="variable.radius * 1.9 / variable.life", drag=0.0, size=f"(0.05 + {R}3 * 0.07) * variable.size", tint=MIX, alpha=FADE_IN_OUT)
    E["grimoire:hoofprint"] = effect("grimoire:hoofprint", "hoofprint", burst="1", lifetime="1.6", size="0.22 * variable.size",
        facing="emitter_transform_xz", rotation="variable.dir.direction_x * 0", alpha=f"0.9 * {FADE}")
    E["grimoire:rune_flash"] = effect("grimoire:rune_flash", "rune_a", burst="3 * variable.count",
        shape=("sphere", {"radius": "variable.radius"}), lifetime=f"0.5 + {R}1 * 0.3", speed="0.5",
        size=f"0.25 * variable.size * {FADE_IN_OUT}", rotation=f"{R}3 * 360", tint=MIX)
    E["grimoire:outline_point"] = effect("grimoire:outline_point", "square", burst="1", lifetime="0.6", size="0.12 * variable.size",
        alpha=FADE_IN_OUT)
    E["grimoire:fragment_burst"] = effect("grimoire:fragment_burst", "fragment", burst="14 * variable.count",
        shape=("sphere", {"radius": "0.4 * variable.radius", "direction": "outwards"}), lifetime=f"0.7 + {R}1 * 0.7",
        speed=f"(2 + {R}2 * 4) * variable.radius", accel=(0, -6, 0), drag=1.5, size=f"(0.05 + {R}3 * 0.08) * variable.size",
        rotation=f"{R}3 * 360", rot_rate=f"({R}4 - 0.5) * 900", tint=MIX)
    E["grimoire:heart_pulse"] = effect("grimoire:heart_pulse", "heart", burst="1", lifetime="0.5 * variable.life",
        size=f"variable.size * (0.4 + 0.8 * variable.particle_age / variable.particle_lifetime)", alpha=f"0.9 * {FADE}")
    E["grimoire:dust_ring"] = effect("grimoire:dust_ring", "smoke", material="particles_blend", burst="24 * variable.count",
        shape=("disc", {"radius": "0.4 * variable.radius", "plane_normal": "y", "direction": "outwards"}), lifetime=f"0.6 + {R}1 * 0.5",
        speed=f"(4 + {R}2 * 3) * variable.radius * 0.5", drag=3.5, size=f"(0.3 + {R}3 * 0.4) * variable.size",
        rotation=f"{R}3 * 360", tint=MIX, alpha=f"0.55 * {FADE_IN_OUT}", lit=True)
    E["grimoire:beam_up"] = effect("grimoire:beam_up", "streak", burst="16 * variable.count",
        shape=("disc", {"radius": "0.5 * variable.radius", "plane_normal": "y", "direction": [0, 1, 0]}), lifetime=f"0.5 + {R}1 * 0.4",
        speed=f"(6 + {R}2 * 6) * variable.size", drag=0.5, size=["0.05 * variable.size", "0.6 * variable.size"],
        facing="lookat_direction", tint=MIX)
    E["grimoire:hex_flash"] = effect("grimoire:hex_flash", "hex", burst="1", lifetime="0.35 * variable.life",
        size=f"variable.radius * (0.3 + 0.7 * variable.particle_age / variable.particle_lifetime)", facing="emitter_transform_xz", tint=MIX)
    E["grimoire:thorn_burst"] = effect("grimoire:thorn_burst", "thorn", burst="10 * variable.count",
        shape=("disc", {"radius": "0.5 * variable.radius", "plane_normal": "y", "direction": [0, 1, 0]}), lifetime=f"0.4 + {R}1 * 0.3",
        speed=f"(3 + {R}2 * 4) * variable.size", accel=(0, -10, 0), drag=1.0, size=["0.08 * variable.size", "0.3 * variable.size"],
        facing="lookat_direction", tint=MIX)
    E["grimoire:star_burst"] = effect("grimoire:star_burst", "star", burst="8 * variable.count",
        shape=("sphere", {"radius": "0.3 * variable.radius", "direction": "outwards"}), lifetime=f"0.5 + {R}1 * 0.4",
        speed=f"(2 + {R}2 * 3) * variable.radius", drag=2.5, size=f"(0.08 + {R}3 * 0.1) * variable.size",
        rotation=f"{R}3 * 360", rot_rate="180", tint=MIX)
    E.update(expansion_effects())
    return E


RAINBOW = [f"0.55 + 0.45 * math.cos(({R}4) * 360)", f"0.55 + 0.45 * math.cos(({R}4) * 360 - 120)",
           f"0.55 + 0.45 * math.cos(({R}4) * 360 - 240)"]


def expansion_effects():
    E = {}
    # preparation streams (templated by casting.ts: grimoire:<school>_charge)
    E["grimoire:plasma_charge"] = effect("grimoire:plasma_charge", "filament", burst="5 + variable.size * 6",
        shape=("sphere", {"radius": "0.6 * variable.radius + 0.25", "surface_only": True, "direction": "inwards"}),
        lifetime="0.38", speed="2.4 * variable.radius + 0.6", drag=1.0, size=["0.05 + 0.04 * variable.size", "0.18 + 0.1 * variable.size"],
        facing="lookat_direction", alpha=FADE_IN_OUT, tint=MIX)
    E["grimoire:darkness_charge"] = effect("grimoire:darkness_charge", "triangle", material="particles_blend", burst="4 + variable.size * 5",
        shape=("sphere", {"radius": "0.6 * variable.radius + 0.25", "surface_only": True, "direction": "inwards"}),
        lifetime="0.45", speed="1.8 * variable.radius + 0.4", drag=1.2, size="0.05 + 0.06 * variable.size",
        rotation=f"{R}3 * 360", rot_rate="160", tint=MIX, alpha=f"0.85 * {FADE_IN_OUT}")
    E["grimoire:prism_light_charge"] = effect("grimoire:prism_light_charge", "glint", burst="5 + variable.size * 6",
        shape=("sphere", {"radius": "0.6 * variable.radius + 0.25", "surface_only": True, "direction": "inwards"}),
        lifetime="0.35", speed="2.2 * variable.radius + 0.5", drag=1.0, size="0.05 + 0.06 * variable.size",
        rotation=f"{R}3 * 360", tint=RAINBOW, alpha=FADE_IN_OUT)
    # plasma
    E["grimoire:plasma_arc"] = effect("grimoire:plasma_arc", "filament", burst="6 * variable.count",
        shape=("sphere", {"radius": "0.3 * variable.radius", "direction": "outwards"}), lifetime=f"0.25 + {R}1 * 0.2",
        speed=f"(4 + {R}2 * 5) * variable.radius",
        accel=(f"math.sin(variable.particle_age * 900 + {R}3 * 360) * 18", f"math.cos(variable.particle_age * 700) * 10", f"math.cos(variable.particle_age * 900 + {R}3 * 360) * 18"),
        drag=3.0, size=["0.05 * variable.size", "0.32 * variable.size"], facing="lookat_direction", tint=MIX)
    E["grimoire:plasma_trail"] = effect("grimoire:plasma_trail", "filament", burst="2 + variable.count", lifetime=f"0.45 * variable.life + {R}1 * 0.25",
        shape=("sphere", {"radius": "0.15 * variable.radius"}), speed="0.2", drag=2,
        size=["0.06 * variable.size", f"0.22 * variable.size * {FADE}"], facing="lookat_direction", rotation=f"{R}3 * 360", tint=MIX)
    E["grimoire:plasma_burst"] = effect("grimoire:plasma_burst", "spark", burst="16 * variable.count",
        shape=("sphere", {"radius": "0.25 * variable.radius", "direction": "outwards"}), lifetime=f"0.3 + {R}1 * 0.35",
        speed=f"(4 + {R}2 * 7) * variable.radius",
        accel=(f"math.sin(variable.particle_age * 600 + {R}3 * 360) * 10", 0, f"math.cos(variable.particle_age * 600 + {R}3 * 360) * 10"),
        drag=3.0, size=f"(0.05 + {R}3 * 0.1) * variable.size", tint=MIX)
    # darkness (alpha-blended: dark shapes that absorb light, never glowing smoke)
    E["grimoire:shadow_sheets"] = effect("grimoire:shadow_sheets", "triangle", material="particles_blend", burst="12 * variable.count",
        shape=("sphere", {"radius": "0.4 * variable.radius", "direction": "outwards"}), lifetime=f"0.7 + {R}1 * 0.6",
        speed=f"(1 + {R}2 * 2.5) * variable.radius", accel=(0, -2.5, 0), drag=2.2, size=f"(0.1 + {R}3 * 0.16) * variable.size",
        rotation=f"{R}3 * 360", rot_rate=f"({R}4 - 0.5) * 300", tint=MIX, alpha=f"0.9 * {FADE}")
    E["grimoire:shadow_fold"] = effect("grimoire:shadow_fold", "square", material="particles_blend", burst="10 * variable.count",
        shape=("sphere", {"radius": "variable.radius", "surface_only": True, "direction": "inwards"}), lifetime="0.4",
        speed="2.4 * variable.radius", drag=1.0, size=f"(0.12 + {R}3 * 0.1) * variable.size * {FADE}",
        rotation=f"{R}3 * 360", rot_rate="240", tint=MIX, alpha="0.9")
    E["grimoire:shadow_print"] = effect("grimoire:shadow_print", "footprint", material="particles_blend", burst="1",
        lifetime="3.2 * variable.life", size="0.22 * variable.size", facing="emitter_transform_xz",
        rotation="variable.dir.direction_x * 0 + variable.radius * 57.3", tint=MIX, alpha=f"0.85 * {FADE_IN_OUT}")
    E["grimoire:outline_mark"] = effect("grimoire:outline_mark", "slit", burst="3 * variable.count",
        shape=("sphere", {"radius": "0.5 * variable.radius", "surface_only": True}), lifetime=f"0.5 + {R}1 * 0.3", speed="0.2",
        size=["0.03 * variable.size", "0.16 * variable.size"], facing="lookat_direction", tint=MIX, alpha=f"0.7 * {FADE_IN_OUT}")
    # prism light
    E["grimoire:spectral_glint"] = effect("grimoire:spectral_glint", "glint", burst="10 * variable.count",
        shape=("sphere", {"radius": "0.4 * variable.radius", "direction": "outwards"}), lifetime=f"0.5 + {R}1 * 0.5",
        speed=f"(1 + {R}2 * 3) * variable.radius", drag=2.5, size=f"(0.05 + {R}3 * 0.08) * variable.size",
        rotation=f"{R}3 * 360", rot_rate="180", tint=RAINBOW, alpha=FADE_IN_OUT)
    E["grimoire:light_motes"] = effect("grimoire:light_motes", "soft", burst="12 * variable.count",
        shape=("disc", {"radius": "variable.radius", "plane_normal": "y"}), lifetime=f"0.9 + {R}1 * 0.7", speed="0.6",
        accel=(0, 1.6, 0), drag=1.0, size=f"(0.05 + {R}3 * 0.07) * variable.size", tint=MIX, alpha=FADE_IN_OUT)
    E["grimoire:glass_sparkle"] = effect("grimoire:glass_sparkle", "lens", burst="14 * variable.count",
        shape=("sphere", {"radius": "variable.radius"}), lifetime=f"0.7 + {R}1 * 0.8", speed="0.4", accel=(0, -1.0, 0), drag=1.5,
        size=f"(0.04 + {R}3 * 0.06) * variable.size", rotation=f"{R}3 * 360", tint=RAINBOW, alpha=f"0.8 * {FADE_IN_OUT}")
    return E


def write_particles(rp):
    write_atlas(rp)
    effects = all_effects()
    for ident, data in effects.items():
        dump(f"{rp}/particles/grimoire/{ident.split(':')[1]}.json", data)
    return sorted(effects)
