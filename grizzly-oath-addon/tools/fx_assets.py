#!/usr/bin/env python3
"""Particle art + particle definitions for Grizzly's Oath (anime dark-fantasy FX).

Atlas: textures/particle/grizzly_oath_fx.png, 256x256, 64 px cells (white + alpha, tinted per
particle):
    row 0: glow | 4-point star sparkle | spark streak (long axis = u) | shard
    row 1: crescent slash flipbook (4 frames: draw-in, draw-in, full, dissipate)
    row 2: three-claw gash (long axis = u) | ground cracks | shock ring | smoke puff
    row 3: dark flame flipbook (4 frames)

Facing modes, checked against Mojang's own particles (bedrock-samples 1.26.60):
  * lookat_direction: x axis follows the direction (ominous_spawning: size [1, 0.5]) -> streaks
  * emitter_transform_xz: lies in the emitter's xz plane; script-spawned emitters are
    world-aligned, so these are flat on the ground (rings, cracks, claw scars). particle spin
    rotates them around the vertical axis.
  * lookat_xyz / lookat_y: camera-facing / upright camera-facing (flames)
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter

C = 64  # cell size
ATLAS = 256

# ----------------------------------------------------------------------------- drawing helpers


def ss_canvas(ss=4):
    img = Image.new("L", (C * ss, C * ss), 0)
    return img, ImageDraw.Draw(img), ss


def tapered_line(d, pts, width, ss, value=255):
    """pts: list of (x, y) in cell units; width profile follows sin(pi*t)."""
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        t = i / (n - 1)
        w = max(0.4, width * math.sin(math.pi * t) ** 0.7) * ss
        d.ellipse([x * ss - w, y * ss - w, x * ss + w, y * ss + w], fill=value)


def glow_cell():
    import numpy as np

    yy, xx = np.mgrid[0:C, 0:C]
    r = np.hypot(xx + 0.5 - C / 2, yy + 0.5 - C / 2) / (C / 2)
    a = np.clip(np.exp(-(r ** 2) * 5.5) + 0.6 * np.clip(1 - r * 3.2, 0, 1), 0, 1)
    return Image.fromarray((a * 255).astype("uint8"))


def star_cell():
    import numpy as np

    yy, xx = np.mgrid[0:C, 0:C]
    x = (xx + 0.5 - C / 2) / (C / 2)
    y = (yy + 0.5 - C / 2) / (C / 2)
    r = np.hypot(x, y)
    ray_h = np.exp(-(y ** 2) / 0.0016) * np.clip(1 - np.abs(x), 0, 1) ** 1.5
    ray_v = np.exp(-(x ** 2) / 0.0016) * np.clip(1 - np.abs(y), 0, 1) ** 1.5
    u, v = (x + y) / math.sqrt(2), (x - y) / math.sqrt(2)
    diag = (np.exp(-(v ** 2) / 0.0012) * np.clip(1 - np.abs(u) * 1.8, 0, 1) ** 2 + np.exp(-(u ** 2) / 0.0012) * np.clip(1 - np.abs(v) * 1.8, 0, 1) ** 2) * 0.7
    core = np.exp(-(r ** 2) * 30)
    a = np.clip(ray_h + ray_v + diag + core, 0, 1)
    return Image.fromarray((a * 255).astype("uint8"))


def streak_cell():
    """Fat tapered gash: bright head at u=1, fading tail, glowing core."""
    import numpy as np

    yy, xx = np.mgrid[0:C, 0:C]
    t = (xx + 0.5) / C
    y = (yy + 0.5 - C / 2) / (C / 2)
    body = np.sin(math.pi * t) ** 0.55
    prof = body * (0.35 + 0.65 * t)
    width = 0.1 + 0.62 * body ** 0.9
    a = np.exp(-((y / (width + 1e-3)) ** 2) * 2.2) * prof
    core = np.exp(-((y / (0.18 * width + 1e-3)) ** 2)) * prof
    return Image.fromarray((np.clip(a * 0.85 + core * 0.6, 0, 1) * 255).astype("uint8"))


def shard_cell():
    img, d, ss = ss_canvas()
    d.polygon([(32 * ss, 6 * ss), (50 * ss, 30 * ss), (36 * ss, 58 * ss), (16 * ss, 36 * ss)], fill=255)
    d.polygon([(32 * ss, 6 * ss), (36 * ss, 58 * ss), (16 * ss, 36 * ss)], fill=190)
    return img.resize((C, C), Image.LANCZOS)


def slash_frame(k):
    """Crescent opening to the left; frames 0-1 draw the arc in, 2 is full, 3 dissipates."""
    img, d, ss = ss_canvas()
    a0, a1 = -105.0, 105.0
    reveal = [0.45, 0.8, 1.0, 1.0][k]
    thick = [3.6, 4.4, 4.0, 2.0][k]
    cx, cy, R = 24.0, 32.0, 27.0
    n = 90
    end = a0 + (a1 - a0) * reveal
    for i in range(n + 1):
        t = i / n
        ang = math.radians(a0 + (end - a0) * t)
        # thickness: tapered tail, fat middle, sharp leading tip
        w = max(0.3, thick * math.sin(math.pi * t) ** 1.3) * ss
        if k == 3 and (int(t * 9) % 3 == 1):
            continue  # broken, dissipating arc
        x = cx + R * math.cos(ang)
        y = cy + R * math.sin(ang)
        d.ellipse([x * ss - w, y * ss - w, x * ss + w, y * ss + w], fill=255)
    small = img.resize((C, C), Image.LANCZOS)
    import numpy as np

    halo = np.asarray(small.filter(ImageFilter.GaussianBlur(3.0)), float) * 0.55
    core = np.asarray(small, float)
    return Image.fromarray(np.clip(np.maximum(core, halo), 0, 255).astype("uint8"))


def claw_cell():
    img, d, ss = ss_canvas()
    for off in (-12, 0, 12):
        pts = []
        for i in range(40):
            t = i / 39
            x = 4 + t * 56
            y = 32 + off + math.sin(t * math.pi) * -3.5 + (t - 0.5) * 3
            pts.append((x, y))
        tapered_line(d, pts, 3.4, ss)
    small = img.resize((C, C), Image.LANCZOS)
    import numpy as np

    halo = np.asarray(small.filter(ImageFilter.GaussianBlur(2.5)), float) * 0.6
    return Image.fromarray(np.clip(np.maximum(np.asarray(small, float), halo), 0, 255).astype("uint8"))


def crack_cell():
    rnd = random.Random(31)
    img, d, ss = ss_canvas()

    def branch(x, y, ang, length, width, depth):
        steps = int(length / 2.5)
        for _ in range(steps):
            ang += rnd.uniform(-0.45, 0.45)
            nx, ny = x + math.cos(ang) * 2.5, y + math.sin(ang) * 2.5
            d.line([(x * ss, y * ss), (nx * ss, ny * ss)], fill=255, width=max(1, int(width * ss)))
            x, y = nx, ny
            width *= 0.93
            if depth < 2 and rnd.random() < 0.12:
                branch(x, y, ang + rnd.choice([-1, 1]) * rnd.uniform(0.5, 1.0), length * 0.45, width * 0.8, depth + 1)

    for i in range(8):
        branch(32, 32, i * math.pi / 4 + rnd.uniform(-0.25, 0.25), rnd.uniform(25, 31), 3.0, 0)
    d.ellipse([(32 - 5) * ss, (32 - 5) * ss, (32 + 5) * ss, (32 + 5) * ss], fill=200)
    small = img.resize((C, C), Image.LANCZOS)
    import numpy as np

    halo = np.asarray(small.filter(ImageFilter.GaussianBlur(1.6)), float) * 0.7
    return Image.fromarray(np.clip(np.maximum(np.asarray(small, float), halo), 0, 255).astype("uint8"))


def ring_cell():
    import numpy as np

    yy, xx = np.mgrid[0:C, 0:C]
    r = np.hypot(xx + 0.5 - C / 2, yy + 0.5 - C / 2) / (C / 2)
    edge = np.exp(-((r - 0.9) ** 2) / 0.0025)
    inner = np.clip((r - 0.45) / 0.45, 0, 1) ** 2 * 0.45 * (r < 0.92)
    a = np.clip(edge + inner, 0, 1)
    return Image.fromarray((a * 255).astype("uint8"))


def puff_cell():
    rnd = random.Random(9)
    img, d, ss = ss_canvas()
    for _ in range(18):
        r = rnd.uniform(7, 15) * ss
        x = (32 + rnd.uniform(-11, 11)) * ss
        y = (32 + rnd.uniform(-11, 11)) * ss
        d.ellipse([x - r, y - r, x + r, y + r], fill=rnd.randint(110, 210))
    return img.resize((C, C), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2.2))


def flame_frame(k):
    import numpy as np

    rnd = np.random.default_rng(100 + k)
    yy, xx = np.mgrid[0:C, 0:C]
    x = (xx + 0.5 - C / 2) / (C / 2)
    y = (yy + 0.5) / C  # 0 top -> 1 bottom
    wobble = 0.12 * np.sin(y * 9 + k * 1.6) + 0.05 * np.sin(y * 21 + k * 2.9)
    width = 0.55 * np.clip(y, 0, 1) ** 0.9 * np.clip((1.05 - y) * 4, 0, 1)
    body = np.clip(1 - np.abs(x - wobble * (1 - y)) / (width + 1e-3), 0, 1)
    tongue = body * np.clip(y * 1.4, 0, 1)
    noise = rnd.random((C, C)) * 0.18
    a = np.clip(tongue ** 0.8 - noise * (1 - y), 0, 1)
    return Image.fromarray((a * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(0.8))


def build_atlas(path):
    atlas = Image.new("RGBA", (ATLAS, ATLAS), (255, 255, 255, 0))
    cells = {
        (0, 0): glow_cell(),
        (1, 0): star_cell(),
        (2, 0): streak_cell(),
        (3, 0): shard_cell(),
        (0, 2): claw_cell(),
        (1, 2): crack_cell(),
        (2, 2): ring_cell(),
        (3, 2): puff_cell(),
    }
    for k in range(4):
        cells[(k, 1)] = slash_frame(k)
        cells[(k, 3)] = flame_frame(k)
    for (cx, cy), mask in cells.items():
        tile = Image.new("RGBA", (C, C), (255, 255, 255, 0))
        tile.putalpha(mask)
        atlas.paste(tile, (cx * C, cy * C))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    atlas.save(path)
    return atlas


# ----------------------------------------------------------------------------- particle JSON

T = "(v.particle_age / v.particle_lifetime)"
COL = ["(v.color.r ?? 1)", "(v.color.g ?? 0.15)", "(v.color.b ?? 0.1)"]
A = "(v.color.a ?? 1)"


def uv(cx, cy, frames=0):
    u = {"texture_width": ATLAS, "texture_height": ATLAS, "uv": [cx * C, cy * C], "uv_size": [C, C]}
    if frames:
        u = {
            "texture_width": ATLAS,
            "texture_height": ATLAS,
            "flipbook": {"base_UV": [cx * C, cy * C], "size_UV": [C, C], "step_UV": [C, 0], "frames_per_second": 20, "max_frame": frames, "stretch_to_lifetime": True},
        }
    return u


def bb(size, cell, mode="lookat_xyz", direction=None, frames=0):
    b = {"size": size if isinstance(size, list) else [size, size], "facing_camera_mode": mode, "uv": uv(*cell, frames=frames)}
    if direction == "velocity":
        b["direction"] = {"mode": "derive_from_velocity", "min_speed_threshold": 0.01}
    elif direction is not None:
        b["direction"] = {"mode": "custom", "custom_direction": direction}
    return {"minecraft:particle_appearance_billboard": b}


def tint(alpha):
    return {"minecraft:particle_appearance_tinting": {"color": COL + [alpha]}}


def one():
    return {"minecraft:emitter_lifetime_once": {}, "minecraft:emitter_rate_instant": {"num_particles": 1}, "minecraft:emitter_shape_point": {}}


def life(expr):
    return {"minecraft:particle_lifetime_expression": {"max_lifetime": expr}}


def defs():
    D = {}
    DIR = ["(v.dir.x ?? 0)", "(v.dir.y ?? 0)", "(v.dir.z ?? 1)"]
    # configurable soft glow point
    D["glow"] = {**one(), **life("(v.life ?? 0.3)"),
                 "minecraft:particle_initial_speed": 0,
                 "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, "(v.rise ?? 0)", 0]},
                 **bb(f"(v.size ?? 0.2) * (1 - 0.5 * {T})", (0, 0)), **tint(f"{A} * (1 - {T})")}
    # anime 4-point impact sparkle: pops in, holds, shrinks
    D["star"] = {**one(), **life("(v.life ?? 0.16)"),
                 "minecraft:particle_initial_spin": {"rotation": "(v.rot ?? 0)", "rotation_rate": 0},
                 **bb(f"(v.size ?? 0.5) * ({T} < 0.2 ? 0.4 + 3 * {T} : 1.15 - 0.95 * ({T} - 0.2))", (1, 0)),
                 **tint(f"{A} * (1 - {T} * {T})")}
    # burst of hot spark streaks, stretched along their velocity
    D["sparks"] = {"minecraft:emitter_lifetime_once": {}, "minecraft:emitter_rate_instant": {"num_particles": "(v.count ?? 8)"},
                   "minecraft:emitter_shape_sphere": {"radius": 0.1, "direction": "outwards"},
                   **life("math.random(0.18, 0.34)"),
                   "minecraft:particle_initial_speed": "math.random(4, 9) * (v.speed ?? 1)",
                   "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -7, 0], "linear_drag_coefficient": 5},
                   **bb([f"0.26 * (1 - {T}) + 0.05", f"0.035 * (1 - 0.5 * {T})"], (2, 0), "lookat_direction", "velocity"),
                   "minecraft:particle_appearance_tinting": {"color": [1, f"0.92 - 0.8 * {T}", f"0.65 - 0.6 * {T}", f"1 - {T} * {T}"]}}
    # crescent slash, drawn in over its life (flipbook)
    D["slash"] = {**one(), **life("(v.life ?? 0.2)"),
                  "minecraft:particle_initial_spin": {"rotation": "(v.rot ?? 0)", "rotation_rate": 0},
                  **bb(f"(v.size ?? 1) * (0.92 + 0.16 * {T})", (0, 1), frames=4),
                  **tint(f"{A} * (1 - {T} * {T} * {T})")}
    # camera-facing triple claw slash (Grizzly Rend cast, hits)
    D["claw_flash"] = {**one(), **life("(v.life ?? 0.28)"),
                       "minecraft:particle_initial_spin": {"rotation": "(v.rot ?? 0)", "rotation_rate": 0},
                       **bb(f"(v.size ?? 1) * ({T} < 0.15 ? 0.6 + {T} * 2.7 : 1)", (0, 2)),
                       **tint(f"{A} * (1 - {T} * {T})")}
    # glowing claw scar flat on the ground; grows along its length, then fades
    D["claw_decal"] = {**one(), **life("(v.life ?? 1.0)"),
                       "minecraft:particle_initial_spin": {"rotation": "(v.rot ?? 0)", "rotation_rate": 0},
                       **bb(["(v.len ?? 1) * math.min(1, v.particle_age * 10)", "(v.wid ?? 0.35)"], (0, 2), "emitter_transform_xz"),
                       **tint(f"{A} * math.pow(1 - {T}, 1.6)")}
    # radial ground cracks
    D["crack"] = {**one(), **life("(v.life ?? 1.2)"),
                  "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": 0},
                  **bb("(v.radius ?? 2) * math.min(1, v.particle_age * 14)", (1, 2), "emitter_transform_xz"),
                  **tint(f"{A} * (1 - {T} * {T})")}
    # flat shockwave ring with an ease-out expansion
    D["ring"] = {**one(), **life("(v.life ?? 0.45)"),
                 **bb(f"(v.radius ?? 4) * (1 - math.pow(1 - math.min(1, {T} * 1.25), 3)) + 0.3", (2, 2), "emitter_transform_xz"),
                 **tint(f"{A} * (1 - {T})")}
    # dark smoke puff
    D["smoke"] = {**one(), **life("math.random(0.7, 1.1)"),
                  "minecraft:emitter_shape_sphere": {"radius": 0.1, "direction": "outwards"},
                  "minecraft:particle_initial_speed": "math.random(0.2, 0.6)",
                  "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.8, 0], "linear_drag_coefficient": 1.5},
                  "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-40, 40)"},
                  **bb(f"(v.size ?? 0.5) * (0.6 + 0.6 * {T})", (3, 2)), **tint(f"{A} * (1 - {T})")}
    del D["smoke"]["minecraft:emitter_shape_point"]
    # ground dust kicked outward along v.dir (slams, dash steps)
    D["dust"] = {"minecraft:emitter_lifetime_once": {}, "minecraft:emitter_rate_instant": {"num_particles": 1},
                 "minecraft:emitter_shape_point": {"direction": DIR},
                 **life("math.random(0.6, 0.9)"),
                 "minecraft:particle_initial_speed": "(v.speed ?? 3)",
                 "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.6, 0], "linear_drag_coefficient": 3.5},
                 "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-60, 60)"},
                 **bb(f"(v.size ?? 0.5) * (0.5 + 0.9 * {T})", (3, 2)),
                 "minecraft:particle_appearance_tinting": {"color": [0.45, 0.39, 0.36, f"0.65 * (1 - {T})"]}}
    # rising red embers
    D["ember"] = {"minecraft:emitter_lifetime_once": {}, "minecraft:emitter_rate_instant": {"num_particles": 1},
                  "minecraft:emitter_shape_point": {"direction": ["math.random(-0.3, 0.3)", 1, "math.random(-0.3, 0.3)"]},
                  **life("math.random(0.6, 1.0)"),
                  "minecraft:particle_initial_speed": "math.random(0.6, 1.4)",
                  "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.6, 0], "linear_drag_coefficient": 0.8},
                  **bb(f"0.06 * (1 - {T}) + 0.02", (0, 0)),
                  "minecraft:particle_appearance_tinting": {"color": [1, f"0.4 - 0.3 * {T}", 0.15, f"1 - {T} * {T}"]}}
    # dark crimson flame tongue (aura, summons, awakened axe), stays upright
    D["flame"] = {"minecraft:emitter_lifetime_once": {}, "minecraft:emitter_rate_instant": {"num_particles": 1},
                  "minecraft:emitter_shape_sphere": {"radius": 0.08, "direction": [0, 1, 0]},
                  **life("math.random(0.45, 0.75)"),
                  "minecraft:particle_initial_speed": "math.random(0.5, 1.1)",
                  "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.4, 0], "linear_drag_coefficient": 1.2},
                  **bb([f"(v.size ?? 0.4) * (1 - 0.35 * {T})", f"(v.size ?? 0.4) * 1.4 * (1 - 0.2 * {T})"], (0, 3), "lookat_y", frames=4),
                  **tint(f"{A} * (1 - {T})")}
    # afterimage / energy trail streak along v.dir
    D["streak"] = {**one(), **life("(v.life ?? 0.3)"),
                   **bb([f"(v.len ?? 1) * (1 - 0.4 * {T})", f"(v.wid ?? 0.1) * (1 - {T})"], (2, 0), "lookat_direction", DIR),
                   **tint(f"{A} * (1 - {T})")}
    # bleeding drops
    D["blood"] = {"minecraft:emitter_lifetime_once": {}, "minecraft:emitter_rate_instant": {"num_particles": 2},
                  "minecraft:emitter_shape_sphere": {"radius": 0.2, "direction": "outwards"},
                  **life("0.6"), "minecraft:particle_initial_speed": "math.random(0.5, 1.5)",
                  "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -12, 0]},
                  **bb([0.05, 0.07], (0, 0)), "minecraft:particle_appearance_tinting": {"color": [0.6, 0.02, 0.03, 1]}}
    # ground debris for slams (purely visual, blocks are never touched)
    D["shard"] = {"minecraft:emitter_lifetime_once": {}, "minecraft:emitter_rate_instant": {"num_particles": "(v.count ?? 8)"},
                  "minecraft:emitter_shape_point": {"direction": ["math.random(-1, 1)", "math.random(0.8, 1.6)", "math.random(-1, 1)"]},
                  **life("math.random(0.6, 0.9)"), "minecraft:particle_initial_speed": "math.random(4, 8)",
                  "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -22, 0], "linear_drag_coefficient": 0.5},
                  "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-360, 360)"},
                  **bb(0.11, (3, 0)),
                  "minecraft:particle_appearance_tinting": {"color": ["0.16 + 0.25 * v.particle_random_1", 0.05, 0.05, f"1 - {T} * {T}"]}}
    # embers drifting off the held axe (attachable locators)
    D["blade_ember"] = {"minecraft:emitter_lifetime_once": {}, "minecraft:emitter_rate_instant": {"num_particles": 2},
                        "minecraft:emitter_shape_sphere": {"radius": 0.12, "direction": "outwards"},
                        **life("math.random(0.35, 0.6)"), "minecraft:particle_initial_speed": "math.random(0.2, 0.6)",
                        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.2, 0]},
                        **bb(f"0.035 * (1 - {T}) + 0.012", (0, 0)),
                        "minecraft:particle_appearance_tinting": {"color": [1, f"0.3 - 0.2 * {T}", 0.12, f"1 - {T}"]}}
    # crimson flames licking off the awakened axe during the Ultimate
    D["awakened_flame"] = {"minecraft:emitter_lifetime_once": {}, "minecraft:emitter_rate_instant": {"num_particles": 2},
                           "minecraft:emitter_shape_sphere": {"radius": 0.18, "direction": [0, 1, 0]},
                           **life("math.random(0.3, 0.5)"), "minecraft:particle_initial_speed": "math.random(0.4, 0.9)",
                           "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 2.4, 0]},
                           **bb([f"0.16 * (1 - 0.4 * {T})", f"0.22 * (1 - 0.2 * {T})"], (0, 3), "lookat_y", frames=4),
                           "minecraft:particle_appearance_tinting": {"color": [1, f"0.35 - 0.3 * {T}", f"0.18 - 0.15 * {T}", f"1 - {T}"]}}
    return D


def write_defs(particles_dir):
    import json

    os.makedirs(particles_dir, exist_ok=True)
    for f in os.listdir(particles_dir):
        if f.endswith(".json"):
            os.remove(os.path.join(particles_dir, f))
    D = defs()
    for name, comps in D.items():
        data = {
            "format_version": "1.10.0",
            "particle_effect": {
                "description": {
                    "identifier": f"grizzly_oath:{name}",
                    "basic_render_parameters": {"material": "particles_blend", "texture": "textures/particle/grizzly_oath_fx"},
                },
                "components": comps,
            },
        }
        with open(os.path.join(particles_dir, f"{name}.json"), "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
    return len(D)
