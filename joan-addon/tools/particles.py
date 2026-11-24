"""
Particle atlas + particle effects of the add-on.

Every road effect is a SEGMENT emitter: the script spawns one emitter per road
segment (a few blocks long) and passes Molang variables:
    variable.dir   (vec3)  unit flow direction of the segment
    variable.len   (float) segment length in blocks
    variable.speed (float) visual flow speed (blocks/s)
    variable.life  (float) emitter duration (s)
    variable.color (rgba)  tint
    variable.size  (float) particle scale
One network packet per segment then draws a continuous, flowing ribbon for the
emitter's whole life, which keeps phones and multiplayer light.

Materials: only the ones vanilla packs use (particles_alpha / particles_blend).
"""
from __future__ import annotations

import math
import os
from typing import Dict, List

from PIL import Image, ImageDraw, ImageFilter

from art import fleur_image

CELL = 32
ATLAS = 128
TEX = "textures/particle/joan_paths"

SPRITES = {
    "glow": (0, 0), "streak": (1, 0), "chevron": (2, 0), "fleur": (3, 0),
    "ring": (0, 1), "ring_soft": (1, 1), "sigil": (2, 1), "sigil_false": (3, 1),
    "flame0": (0, 2), "flame1": (1, 2), "flame2": (2, 2), "flame3": (3, 2),
    "ember": (0, 3), "smoke": (1, 3), "star": (2, 3), "petal": (3, 3),
}


# =========================================================================== atlas painting
def _cell(draw_fn, ss: int = 4) -> Image.Image:
    big = Image.new("RGBA", (CELL * ss, CELL * ss), (255, 255, 255, 0))
    draw_fn(big, ss)
    return big.resize((CELL, CELL), Image.LANCZOS)


def _radial(im, ss, r_in, r_out, power=1.6, color=(255, 255, 255)):
    px = im.load()
    S = CELL * ss
    c = S / 2
    for y in range(S):
        for x in range(S):
            d = math.hypot(x + 0.5 - c, y + 0.5 - c) / c
            if d <= r_in:
                a = 1.0
            elif d >= r_out:
                a = 0.0
            else:
                a = (1 - (d - r_in) / (r_out - r_in)) ** power
            px[x, y] = color + (int(255 * a),)


def atlas() -> Image.Image:
    img = Image.new("RGBA", (ATLAS, ATLAS), (255, 255, 255, 0))

    def put(name, cell_img):
        cx, cy = SPRITES[name]
        img.alpha_composite(cell_img, (cx * CELL, cy * CELL))

    put("glow", _cell(lambda im, ss: _radial(im, ss, 0.05, 1.0, 2.2)))

    def streak(im, ss):
        px = im.load()
        S = CELL * ss
        for y in range(S):
            for x in range(S):
                u = (x + 0.5) / S
                v = abs((y + 0.5) / S - 0.5) * 2
                head = u ** 1.7                      # brighter towards +u (the front)
                a = max(0.0, 1 - v * 1.6) ** 1.3 * (0.15 + 0.85 * head) * min(1.0, (1 - u) * 14)
                px[x, y] = (255, 255, 255, int(255 * max(0.0, min(1.0, a))))
    put("streak", _cell(streak))

    def chevron(im, ss):
        d = ImageDraw.Draw(im)
        S = CELL * ss
        w = S * 0.16
        pts_outer = [(S * 0.22, S * 0.16), (S * 0.80, S * 0.5), (S * 0.22, S * 0.84)]
        for k in range(2):     # two nested chevrons
            off = -S * 0.18 * k
            p = [(x + off, y) for x, y in pts_outer]
            d.line(p, fill=(255, 255, 255, 255 if k == 0 else 150), width=int(w), joint="curve")
        im2 = im.filter(ImageFilter.GaussianBlur(ss * 0.6))
        im.paste(im2)
    put("chevron", _cell(chevron))
    put("fleur", fleur_image(CELL, (255, 255, 255, 255), soft=True))

    def ring(width, soft):
        def f(im, ss):
            px = im.load()
            S = CELL * ss
            c = S / 2
            for y in range(S):
                for x in range(S):
                    dd = math.hypot(x + 0.5 - c, y + 0.5 - c) / c
                    a = max(0.0, 1 - abs(dd - (0.92 - width)) / width)
                    if soft:
                        a = a ** 0.7 + max(0.0, 0.9 - dd) * 0.12
                    px[x, y] = (255, 255, 255, int(255 * min(1.0, a)))
        return f
    put("ring", _cell(ring(0.05, False)))
    put("ring_soft", _cell(ring(0.16, True)))

    def sigil(false_mark):
        def f(im, ss):
            ring(0.04, False)(im, ss)
            S = CELL * ss
            fl = fleur_image(int(S * 0.62), (255, 255, 255, 255), soft=True)
            if false_mark:
                fl = fl.rotate(180)
            im.alpha_composite(fl, (int(S * 0.19), int(S * 0.17)))
            d = ImageDraw.Draw(im)
            for k in range(8):       # small ticks around the circle
                a = k * math.pi / 4
                r0, r1 = S * 0.40, S * 0.46
                d.line([(S / 2 + math.cos(a) * r0, S / 2 + math.sin(a) * r0),
                        (S / 2 + math.cos(a) * r1, S / 2 + math.sin(a) * r1)], fill=(255, 255, 255, 255), width=ss)
            if false_mark:          # a broken circle marks the lie
                d.arc([S * 0.08, S * 0.08, S * 0.92, S * 0.92], 250, 290, fill=(0, 0, 0, 0), width=ss * 3)
        return f
    put("sigil", _cell(sigil(False)))
    put("sigil_false", _cell(sigil(True)))

    for k in range(4):
        def flame(im, ss, k=k):
            d = ImageDraw.Draw(im)
            S = CELL * ss
            sway = math.sin(k * 1.6) * S * 0.06
            body = [(S * 0.5 + sway, S * (0.08 + 0.04 * k % 0.08)), (S * 0.78, S * 0.62), (S * 0.66, S * 0.92),
                    (S * 0.34, S * 0.92), (S * 0.22, S * 0.62)]
            d.polygon(body, fill=(255, 255, 255, 230))
            d.ellipse([S * 0.3, S * 0.55, S * 0.7, S * 0.95], fill=(255, 255, 255, 255))
            im2 = im.filter(ImageFilter.GaussianBlur(ss * 1.2))
            im.paste(im2)
        put(f"flame{k}", _cell(flame))
    put("ember", _cell(lambda im, ss: _radial(im, ss, 0.12, 0.45, 1.2)))

    def smoke(im, ss):
        px = im.load()
        S = CELL * ss
        c = S / 2
        for y in range(S):
            for x in range(S):
                dd = math.hypot(x + 0.5 - c, y + 0.5 - c) / c
                n = (math.sin(x * 0.21) * math.sin(y * 0.17) + 1) / 2
                a = max(0.0, 1 - dd) ** 1.2 * (0.6 + 0.4 * n)
                px[x, y] = (255, 255, 255, int(255 * a))
    put("smoke", _cell(smoke))

    def star(im, ss):
        d = ImageDraw.Draw(im)
        S = CELL * ss
        c = S / 2
        for ang, ln in ((0, 0.48), (90, 0.48), (45, 0.24), (135, 0.24)):
            a = math.radians(ang)
            dx, dy = math.cos(a) * S * ln, math.sin(a) * S * ln
            d.line([(c - dx, c - dy), (c + dx, c + dy)], fill=(255, 255, 255, 255), width=int(ss * 1.6))
        im2 = im.filter(ImageFilter.GaussianBlur(ss * 0.8))
        im.alpha_composite(im2)
        _radial_overlay = Image.new("RGBA", im.size, (255, 255, 255, 0))
        _radial(_radial_overlay, ss, 0.0, 0.35, 2.0)
        im.alpha_composite(_radial_overlay)
    put("star", _cell(star))

    def petal(im, ss):
        d = ImageDraw.Draw(im)
        S = CELL * ss
        d.ellipse([S * 0.32, S * 0.1, S * 0.68, S * 0.9], fill=(255, 255, 255, 255))
        im2 = im.filter(ImageFilter.GaussianBlur(ss * 1.0))
        im.paste(im2)
    put("petal", _cell(petal))
    return img


# =========================================================================== effect builders
def _uv(name: str, flip: int = 0) -> dict:
    cx, cy = SPRITES[name]
    uv = {"texture_width": ATLAS, "texture_height": ATLAS, "uv": [cx * CELL, cy * CELL], "uv_size": [CELL, CELL]}
    if flip:
        uv["flipbook"] = {"base_UV": [cx * CELL, cy * CELL], "size_UV": [CELL, CELL], "step_UV": [CELL, 0],
                          "frames_per_second": 10, "max_frame": flip, "loop": True}
    return uv


INIT = ("variable.dir ?? { variable.dir.x = 0.0; variable.dir.y = 0.0; variable.dir.z = 1.0; }; "
        "variable.color ?? { variable.color.r = 1.0; variable.color.g = 0.9; variable.color.b = 0.6; variable.color.a = 1.0; }; "
        "variable.len = variable.len ?? 2.0; variable.speed = variable.speed ?? 4.0; "
        "variable.life = variable.life ?? 1.0; variable.size = variable.size ?? 1.0; "
        "variable.r0 = variable.r0 ?? 1.0; variable.r1 = variable.r1 ?? 3.0; variable.h = variable.h ?? 6.0;")

ALONG = ["variable.dir.x * variable.len * Math.random(0, 1)", "variable.dir.y * variable.len * Math.random(0, 1)",
         "variable.dir.z * variable.len * Math.random(0, 1)"]
DIR = ["variable.dir.x", "variable.dir.y", "variable.dir.z"]
TINT = ["variable.color.r", "variable.color.g", "variable.color.b"]
AGE = "(variable.particle_age / variable.particle_lifetime)"


def effect(ident: str, material: str, comps: dict) -> dict:
    base = {"minecraft:emitter_initialization": {"creation_expression": INIT}}
    base.update(comps)
    return {"format_version": "1.10.0", "particle_effect": {
        "description": {"identifier": ident, "basic_render_parameters": {"material": material, "texture": TEX}},
        "components": base}}


def effects() -> Dict[str, dict]:
    E: Dict[str, dict] = {}
    fade_in_out = f"math.clamp({AGE} * 6.0, 0, 1) * math.clamp((1.0 - {AGE}) * 3.0, 0, 1)"

    # ----- active road: flowing streaks
    E["road_flow"] = effect("joan:road_flow", "particles_blend", {
        "minecraft:emitter_rate_steady": {"spawn_rate": "math.max(3, variable.len * 6.5)", "max_particles": 60},
        "minecraft:emitter_lifetime_once": {"active_time": "variable.life"},
        "minecraft:emitter_shape_custom": {"offset": ALONG, "direction": DIR},
        "minecraft:particle_initial_speed": "variable.speed",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.clamp(variable.len / math.max(variable.speed, 0.5), 0.15, 0.7)"},
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_appearance_billboard": {
            "size": ["0.42 * variable.size", "0.11 * variable.size"], "facing_camera_mode": "lookat_direction",
            "direction": {"mode": "derive_from_velocity", "min_speed_threshold": 0.01}, "uv": _uv("streak")},
        "minecraft:particle_appearance_tinting": {"color": [
            "math.lerp(variable.color.r, 1.0, variable.particle_random_2 * 0.6)",
            "math.lerp(variable.color.g, 1.0, variable.particle_random_2 * 0.6)",
            "math.lerp(variable.color.b, 1.0, variable.particle_random_2 * 0.6)",
            f"variable.color.a * {fade_in_out}"]},
    })
    # ----- active road: chevrons showing the direction of the current
    E["road_chevron"] = effect("joan:road_chevron", "particles_blend", {
        "minecraft:emitter_rate_steady": {"spawn_rate": "math.max(1.5, variable.len * 1.3)", "max_particles": 16},
        "minecraft:emitter_lifetime_once": {"active_time": "variable.life"},
        "minecraft:emitter_shape_custom": {"offset": ALONG, "direction": DIR},
        "minecraft:particle_initial_speed": "variable.speed * 0.55",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.clamp(variable.len / math.max(variable.speed * 0.55, 0.3), 0.3, 1.2)"},
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_appearance_billboard": {
            "size": ["0.32 * variable.size", "0.32 * variable.size"], "facing_camera_mode": "lookat_direction",
            "direction": {"mode": "custom", "custom_direction": DIR}, "uv": _uv("chevron")},
        "minecraft:particle_appearance_tinting": {"color": TINT + [f"variable.color.a * {fade_in_out}"]},
    })
    # ----- forming road (telegraph): ink dots + still chevrons pointing the future flow
    E["road_ink"] = effect("joan:road_ink", "particles_alpha", {
        "minecraft:emitter_rate_instant": {"num_particles": "math.max(3, variable.len * 3.0)"},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_custom": {"offset": ALONG, "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": 0.0,
        "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life"},
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_appearance_billboard": {
            "size": [f"0.09 * variable.size * (0.6 + {AGE} * 0.8)", f"0.09 * variable.size * (0.6 + {AGE} * 0.8)"],
            "facing_camera_mode": "lookat_xyz", "uv": _uv("glow")},
        "minecraft:particle_appearance_tinting": {"color": TINT + [f"math.clamp({AGE} * 3, 0.35, 1) * (0.75 + math.sin(variable.particle_age * 900) * 0.25)"]},
    })
    E["road_ink_chevron"] = effect("joan:road_ink_chevron", "particles_alpha", {
        "minecraft:emitter_rate_instant": {"num_particles": "math.max(1, math.floor(variable.len / 1.6))"},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_custom": {"offset": ALONG, "direction": DIR},
        "minecraft:particle_initial_speed": 0.35,
        "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life"},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 0.6},
        "minecraft:particle_appearance_billboard": {
            "size": ["0.26 * variable.size", "0.26 * variable.size"], "facing_camera_mode": "lookat_direction",
            "direction": {"mode": "custom", "custom_direction": DIR}, "uv": _uv("chevron")},
        "minecraft:particle_appearance_tinting": {"color": TINT + [f"0.45 + math.clamp({AGE}, 0, 1) * 0.55"]},
    })
    # ----- burning road (phase II)
    E["road_fire"] = effect("joan:road_fire", "particles_blend", {
        "minecraft:emitter_rate_steady": {"spawn_rate": "math.max(3, variable.len * 5)", "max_particles": 60},
        "minecraft:emitter_lifetime_once": {"active_time": "variable.life"},
        "minecraft:emitter_shape_custom": {"offset": ALONG, "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "Math.random(0.6, 1.6)",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "Math.random(0.35, 0.7)"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.2, 0], "linear_drag_coefficient": 1.0},
        "minecraft:particle_appearance_billboard": {
            "size": [f"0.28 * variable.size * (1 - {AGE} * 0.6)", f"0.38 * variable.size * (1 - {AGE} * 0.5)"],
            "facing_camera_mode": "lookat_y", "uv": _uv("flame0", flip=4)},
        "minecraft:particle_appearance_tinting": {"color": {"gradient": {
            "0.0": [1.0, 0.95, 0.65, 0.95], "0.35": [1.0, 0.62, 0.18, 0.9], "1.0": [0.75, 0.15, 0.05, 0.0]},
            "interpolant": AGE}},
    })
    # ----- remembered road (scar)
    E["road_scar"] = effect("joan:road_scar", "particles_blend", {
        "minecraft:emitter_rate_instant": {"num_particles": "math.max(1, variable.len * 1.2)"},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_custom": {"offset": ALONG, "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": 0.15,
        "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life"},
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_appearance_billboard": {
            "size": ["0.07 * variable.size", "0.07 * variable.size"], "facing_camera_mode": "lookat_xyz", "uv": _uv("glow")},
        "minecraft:particle_appearance_tinting": {"color": TINT + [f"0.55 * math.sin({AGE} * 180)"]},
    })
    # ----- ground sigil (strike telegraph) and rings (closing loops / shock waves)
    E["sigil"] = effect("joan:sigil", "particles_blend", {
        "minecraft:emitter_rate_instant": {"num_particles": 1},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {"offset": [0, 0.06, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life"},
        "minecraft:particle_initial_spin": {"rotation": "Math.random(0, 360)", "rotation_rate": 25},
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_appearance_billboard": {
            "size": [f"variable.size * (0.25 + {AGE} * 0.75)", f"variable.size * (0.25 + {AGE} * 0.75)"],
            "facing_camera_mode": "emitter_transform_xz", "uv": _uv("sigil")},
        "minecraft:particle_appearance_tinting": {"color": TINT + [f"variable.color.a * (0.55 + {AGE} * 0.45)"]},
    })
    E["sigil_false"] = effect("joan:sigil_false", "particles_blend", {
        **{k: v for k, v in E["sigil"]["particle_effect"]["components"].items() if k != "minecraft:emitter_initialization"},
        "minecraft:particle_appearance_billboard": {
            "size": ["variable.size", "variable.size"], "facing_camera_mode": "emitter_transform_xz",
            "uv": _uv("sigil_false")},
        "minecraft:particle_appearance_tinting": {"color": TINT + ["variable.color.a * (0.6 + math.sin(variable.particle_age * 1400) * 0.25)"]},
    })
    E["ring"] = effect("joan:ring", "particles_blend", {
        "minecraft:emitter_rate_instant": {"num_particles": 1},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {"offset": [0, 0.08, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life"},
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_appearance_billboard": {
            "size": [f"math.lerp(variable.r0, variable.r1, {AGE}) * 1.09", f"math.lerp(variable.r0, variable.r1, {AGE}) * 1.09"],
            "facing_camera_mode": "emitter_transform_xz", "uv": _uv("ring")},
        "minecraft:particle_appearance_tinting": {"color": TINT + [f"variable.color.a * math.clamp((1 - {AGE}) * 4, 0, 1)"]},
    })
    # ----- bursts, pillars, flashes, embers, motes, smoke, swing streaks
    E["burst"] = effect("joan:burst", "particles_blend", {
        "minecraft:emitter_rate_instant": {"num_particles": "math.floor(14 * variable.size + 6)"},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_sphere": {"radius": 0.25, "direction": "outwards"},
        "minecraft:particle_initial_speed": "Math.random(2.5, 6.0) * variable.size",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "Math.random(0.3, 0.65)"},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 3.5, "linear_acceleration": [0, -2, 0]},
        "minecraft:particle_appearance_billboard": {
            "size": [f"0.16 * (1 - {AGE})", f"0.16 * (1 - {AGE})"], "facing_camera_mode": "lookat_xyz", "uv": _uv("star")},
        "minecraft:particle_appearance_tinting": {"color": TINT + [f"1 - {AGE} * 0.7"]},
    })
    E["pillar"] = effect("joan:pillar", "particles_blend", {
        "minecraft:emitter_rate_steady": {"spawn_rate": 70, "max_particles": 120},
        "minecraft:emitter_lifetime_once": {"active_time": "variable.life"},
        "minecraft:emitter_shape_custom": {
            "offset": ["Math.random(-0.6, 0.6) * variable.size", "Math.random(0, variable.h)", "Math.random(-0.6, 0.6) * variable.size"],
            "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "Math.random(3, 7)",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "Math.random(0.25, 0.5)"},
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_appearance_billboard": {
            "size": ["0.6", "0.08"], "facing_camera_mode": "lookat_direction",
            "direction": {"mode": "derive_from_velocity", "min_speed_threshold": 0.01}, "uv": _uv("streak")},
        "minecraft:particle_appearance_tinting": {"color": TINT + [fade_in_out]},
    })
    E["flash"] = effect("joan:flash", "particles_blend", {
        "minecraft:emitter_rate_instant": {"num_particles": 1},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "math.max(0.15, variable.life)"},
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_appearance_billboard": {
            "size": [f"variable.size * (0.6 + {AGE} * 0.6)", f"variable.size * (0.6 + {AGE} * 0.6)"],
            "facing_camera_mode": "lookat_xyz", "uv": _uv("glow")},
        "minecraft:particle_appearance_tinting": {"color": TINT + [f"(1 - {AGE}) * variable.color.a"]},
    })
    E["ember"] = effect("joan:ember", "particles_blend", {
        "minecraft:emitter_rate_steady": {"spawn_rate": "8 * variable.size", "max_particles": 40},
        "minecraft:emitter_lifetime_once": {"active_time": "variable.life"},
        "minecraft:emitter_shape_sphere": {"radius": "0.9 * variable.size", "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "Math.random(0.4, 1.2)",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "Math.random(0.8, 1.8)"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": ["math.sin(variable.particle_age * 300) * 1.5", 0.8, "math.cos(variable.particle_age * 260) * 1.5"],
                                              "linear_drag_coefficient": 1.2},
        "minecraft:particle_appearance_billboard": {
            "size": [f"0.07 * (1 - {AGE} * 0.5)", f"0.07 * (1 - {AGE} * 0.5)"], "facing_camera_mode": "lookat_xyz",
            "uv": _uv("ember")},
        "minecraft:particle_appearance_tinting": {"color": {"gradient": {
            "0.0": [1.0, 0.92, 0.55, 1.0], "0.6": [1.0, 0.5, 0.12, 0.9], "1.0": [0.6, 0.1, 0.05, 0.0]}, "interpolant": AGE}},
    })
    E["mote"] = effect("joan:mote", "particles_blend", {
        "minecraft:emitter_rate_steady": {"spawn_rate": "6 * variable.size", "max_particles": 40},
        "minecraft:emitter_lifetime_once": {"active_time": "variable.life"},
        "minecraft:emitter_shape_sphere": {"radius": "variable.size", "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "Math.random(0.2, 0.8) * variable.speed",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "Math.random(0.9, 1.6)"},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 0.6},
        "minecraft:particle_appearance_billboard": {
            "size": ["0.08", "0.08"], "facing_camera_mode": "lookat_xyz", "uv": _uv("glow")},
        "minecraft:particle_appearance_tinting": {"color": TINT + [f"math.sin({AGE} * 180) * variable.color.a"]},
    })
    E["smoke"] = effect("joan:smoke", "particles_blend", {
        "minecraft:emitter_rate_steady": {"spawn_rate": "10 * variable.size", "max_particles": 50},
        "minecraft:emitter_lifetime_once": {"active_time": "variable.life"},
        "minecraft:emitter_shape_sphere": {"radius": "0.7 * variable.size", "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "Math.random(0.6, 1.4)",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "Math.random(1.2, 2.2)"},
        "minecraft:particle_initial_spin": {"rotation": "Math.random(0, 360)", "rotation_rate": "Math.random(-40, 40)"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0.3, 0.6, 0], "linear_drag_coefficient": 0.8},
        "minecraft:particle_appearance_billboard": {
            "size": [f"0.5 + {AGE} * 0.9", f"0.5 + {AGE} * 0.9"], "facing_camera_mode": "lookat_xyz", "uv": _uv("smoke")},
        "minecraft:particle_appearance_tinting": {"color": [0.16, 0.13, 0.12, f"0.55 * math.sin({AGE} * 180)"]},
    })
    E["swing"] = effect("joan:swing", "particles_blend", {
        "minecraft:emitter_rate_instant": {"num_particles": 3},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_custom": {"offset": ALONG, "direction": DIR},
        "minecraft:particle_initial_speed": "variable.speed",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "Math.random(0.18, 0.32)"},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 4.0},
        "minecraft:particle_appearance_billboard": {
            "size": ["0.9 * variable.size", "0.16 * variable.size"], "facing_camera_mode": "lookat_direction",
            "direction": {"mode": "custom", "custom_direction": DIR}, "uv": _uv("streak")},
        "minecraft:particle_appearance_tinting": {"color": TINT + [f"(1 - {AGE}) * variable.color.a"]},
    })
    E["petals"] = effect("joan:petals", "particles_blend", {
        "minecraft:emitter_rate_steady": {"spawn_rate": "12 * variable.size", "max_particles": 60},
        "minecraft:emitter_lifetime_once": {"active_time": "variable.life"},
        "minecraft:emitter_shape_sphere": {"radius": "1.2 * variable.size", "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "Math.random(0.5, 1.6)",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "Math.random(1.5, 3.0)"},
        "minecraft:particle_initial_spin": {"rotation": "Math.random(0, 360)", "rotation_rate": "Math.random(-90, 90)"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": ["math.sin(variable.particle_age * 120) * 0.8", 0.5, 0],
                                              "linear_drag_coefficient": 0.9},
        "minecraft:particle_appearance_billboard": {
            "size": ["0.09", "0.14"], "facing_camera_mode": "lookat_xyz", "uv": _uv("petal")},
        "minecraft:particle_appearance_tinting": {"color": TINT + [f"math.sin({AGE} * 180)"]},
    })
    # ----- entity-attached ambience (spawned by client animations, no server traffic)
    E["aura_p1"] = effect("joan:aura_p1", "particles_blend", {
        "minecraft:emitter_local_space": {"position": True, "rotation": False},
        "minecraft:emitter_rate_steady": {"spawn_rate": 4, "max_particles": 20},
        "minecraft:emitter_lifetime_once": {"active_time": 2.0},
        "minecraft:emitter_shape_sphere": {"radius": 0.9, "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "Math.random(0.1, 0.4)",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "Math.random(1.0, 1.8)"},
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_appearance_billboard": {
            "size": ["0.06", "0.06"], "facing_camera_mode": "lookat_xyz", "uv": _uv("glow")},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.92, 0.62, f"math.sin({AGE} * 180) * 0.8"]},
    })
    E["aura_p2"] = effect("joan:aura_p2", "particles_blend", {
        "minecraft:emitter_local_space": {"position": True, "rotation": False},
        "minecraft:emitter_rate_steady": {"spawn_rate": 10, "max_particles": 40},
        "minecraft:emitter_lifetime_once": {"active_time": 2.0},
        "minecraft:emitter_shape_sphere": {"radius": 1.0, "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "Math.random(0.6, 1.4)",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "Math.random(0.8, 1.4)"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": ["math.sin(variable.particle_age * 300) * 1.5", 0.6, 0]},
        "minecraft:particle_appearance_billboard": {
            "size": [f"0.07 * (1 - {AGE} * 0.5)", f"0.07 * (1 - {AGE} * 0.5)"], "facing_camera_mode": "lookat_xyz",
            "uv": _uv("ember")},
        "minecraft:particle_appearance_tinting": {"color": {"gradient": {
            "0.0": [1.0, 0.9, 0.5, 1.0], "0.6": [1.0, 0.45, 0.1, 0.9], "1.0": [0.6, 0.1, 0.05, 0.0]}, "interpolant": AGE}},
    })
    E["banner_glint"] = effect("joan:banner_glint", "particles_blend", {
        "minecraft:emitter_local_space": {"position": True, "rotation": False},
        "minecraft:emitter_rate_steady": {"spawn_rate": 3, "max_particles": 10},
        "minecraft:emitter_lifetime_once": {"active_time": 2.0},
        "minecraft:emitter_shape_sphere": {"radius": 0.3, "direction": "outwards"},
        "minecraft:particle_initial_speed": 0.2,
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.6},
        "minecraft:particle_motion_dynamic": {},
        "minecraft:particle_appearance_billboard": {
            "size": [f"0.12 * math.sin({AGE} * 180)", f"0.12 * math.sin({AGE} * 180)"], "facing_camera_mode": "lookat_xyz",
            "uv": _uv("star")},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.95, 0.7, 1.0]},
    })
    return E


def build(rp_dir: str) -> List[str]:
    tex = os.path.join(rp_dir, TEX + ".png")
    os.makedirs(os.path.dirname(tex), exist_ok=True)
    atlas().save(tex)
    ids = []
    import json
    for name, data in effects().items():
        p = os.path.join(rp_dir, "particles", "joan", f"{name}.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            json.dump(data, f, indent=1)
        ids.append(data["particle_effect"]["description"]["identifier"])
    return ids


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "build/particles_test"
    print(build(out))
    a = atlas().resize((ATLAS * 4, ATLAS * 4), Image.NEAREST)
    bg = Image.new("RGBA", a.size, (30, 40, 70, 255))
    bg.alpha_composite(a)
    bg.save(os.path.join(out, "atlas_preview.png"))
