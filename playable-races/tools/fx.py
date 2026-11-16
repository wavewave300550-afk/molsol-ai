"""Particle atlas + particle effect definitions + fog."""
from __future__ import annotations

import math
from typing import Dict, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

NS = "plrace"
TEX = "textures/plrace/races/particles/particles"
W = H = 128
CELL = 16
SPRITES = ["dot", "spore", "drop", "leaf", "flake", "bubble", "root", "strand",
           "shard", "glyph_a", "glyph_b", "glyph_c", "glyph_d", "spark", "ring", "crescent",
           "ember", "sigil", "dust", "ping", "reticle", "petal", "smoke", "rune_ring",
           "seal", "decree", "fracture", "procession", "gate"]
BIG = {"slash": (0, 64, 64, 64), "circle": (64, 64, 64, 64)}


def cell(name) -> Tuple[int, int, int, int]:
    if name in BIG:
        return BIG[name]
    i = SPRITES.index(name)
    return ((i % 8) * CELL, (i // 8) * CELL, CELL, CELL)


def atlas() -> Image.Image:
    S = 8  # supersample
    big = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)

    def box(name):
        x, y, w, h = cell(name)
        return x * S, y * S, w * S, h * S

    def circ(cx, cy, r, fill, width=0, outline=None):
        if width:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=outline or fill, width=width)
        else:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)

    W_ = (255, 255, 255, 255)
    for name in SPRITES:
        x, y, w, h = box(name)
        cx, cy = x + w / 2, y + h / 2
        if name == "dot":
            for k in range(10, 0, -1):
                circ(cx, cy, w * 0.05 * k, (255, 255, 255, int(255 * (1 - k / 11) ** 1.2)))
        elif name == "spore":
            for k in range(8, 0, -1):
                circ(cx, cy, w * 0.045 * k, (255, 255, 255, int(255 * (1 - k / 9))))
            for a in range(8):
                ang = a * math.pi / 4
                d.line([cx, cy, cx + math.cos(ang) * w * 0.42, cy + math.sin(ang) * w * 0.42], fill=(255, 255, 255, 120), width=S)
        elif name == "drop":
            d.ellipse([cx - w * 0.22, cy - h * 0.05, cx + w * 0.22, cy + h * 0.38], fill=W_)
            d.polygon([(cx, y + h * 0.08), (cx - w * 0.2, cy + h * 0.08), (cx + w * 0.2, cy + h * 0.08)], fill=W_)
        elif name == "leaf":
            d.ellipse([x + w * 0.2, y + h * 0.1, x + w * 0.8, y + h * 0.9], fill=W_)
            d.line([cx, y + h * 0.1, cx, y + h * 0.9], fill=(170, 170, 170, 255), width=S)
        elif name == "flake":
            d.polygon([(x + w * 0.2, y + h * 0.3), (x + w * 0.7, y + h * 0.15), (x + w * 0.85, y + h * 0.6), (x + w * 0.35, y + h * 0.85)], fill=W_)
        elif name == "bubble":
            circ(cx, cy, w * 0.36, W_, width=int(S * 1.5))
            circ(cx - w * 0.12, cy - h * 0.12, w * 0.07, W_)
        elif name == "root":
            d.line([x + w * 0.2, y + h * 0.1, cx, cy, x + w * 0.75, y + h * 0.9], fill=W_, width=3 * S)
            d.line([cx, cy, x + w * 0.85, y + h * 0.35], fill=W_, width=2 * S)
        elif name == "strand":
            d.rounded_rectangle([x + w * 0.38, y, x + w * 0.62, y + h], radius=w * 0.12, fill=W_)
        elif name == "shard":
            d.polygon([(cx, y + h * 0.05), (x + w * 0.85, cy), (cx + w * 0.1, y + h * 0.95), (x + w * 0.18, y + h * 0.55)], fill=W_)
        elif name.startswith("glyph"):
            wid = int(S * 1.6)
            k = "abcd".index(name[-1])
            d.line([cx, y + h * 0.1, cx, y + h * 0.9], fill=W_, width=wid)
            if k == 0:
                d.line([cx, y + h * 0.3, x + w * 0.8, y + h * 0.1], fill=W_, width=wid)
                d.line([cx, y + h * 0.5, x + w * 0.8, y + h * 0.3], fill=W_, width=wid)
            elif k == 1:
                d.line([cx, y + h * 0.1, x + w * 0.8, y + h * 0.35], fill=W_, width=wid)
                d.line([x + w * 0.8, y + h * 0.35, cx, y + h * 0.6], fill=W_, width=wid)
            elif k == 2:
                d.line([x + w * 0.2, y + h * 0.35, x + w * 0.8, y + h * 0.65], fill=W_, width=wid)
                d.line([x + w * 0.2, y + h * 0.65, x + w * 0.8, y + h * 0.35], fill=W_, width=wid)
            else:
                d.line([cx, y + h * 0.45, x + w * 0.2, y + h * 0.2], fill=W_, width=wid)
                d.line([cx, y + h * 0.45, x + w * 0.8, y + h * 0.2], fill=W_, width=wid)
                d.line([x + w * 0.3, y + h * 0.75, x + w * 0.7, y + h * 0.75], fill=W_, width=wid)
        elif name == "spark":
            for ang in (0, 90):
                a = math.radians(ang)
                pts = [(cx + math.cos(a) * w * 0.48, cy + math.sin(a) * h * 0.48), (cx + math.cos(a + math.pi / 2) * w * 0.08, cy + math.sin(a + math.pi / 2) * h * 0.08),
                       (cx - math.cos(a) * w * 0.48, cy - math.sin(a) * h * 0.48), (cx - math.cos(a + math.pi / 2) * w * 0.08, cy - math.sin(a + math.pi / 2) * h * 0.08)]
                d.polygon(pts, fill=W_)
            circ(cx, cy, w * 0.12, W_)
        elif name == "ring":
            circ(cx, cy, w * 0.42, W_, width=int(S * 1.4))
        elif name == "crescent":
            circ(cx, cy, w * 0.42, W_)
            circ(cx + w * 0.17, cy - h * 0.08, w * 0.36, (0, 0, 0, 0))
        elif name == "ember":
            d.polygon([(cx, y + h * 0.15), (x + w * 0.75, cy), (cx, y + h * 0.85), (x + w * 0.25, cy)], fill=W_)
        elif name == "sigil":
            circ(cx, cy, w * 0.44, W_, width=int(S * 1.2))
            circ(cx, cy, w * 0.26, W_)
            circ(cx + w * 0.1, cy - h * 0.05, w * 0.22, (0, 0, 0, 0))
            for a in range(4):
                ang = a * math.pi / 2 + math.pi / 4
                circ(cx + math.cos(ang) * w * 0.44, cy + math.sin(ang) * h * 0.44, w * 0.06, W_)
        elif name == "dust":
            for k in range(6, 0, -1):
                circ(cx, cy, w * 0.07 * k, (255, 255, 255, int(200 * (1 - k / 7))))
            d.line([cx, y + h * 0.1, cx, y + h * 0.9], fill=(255, 255, 255, 160), width=S)
            d.line([x + w * 0.1, cy, x + w * 0.9, cy], fill=(255, 255, 255, 160), width=S)
        elif name == "ping":
            d.polygon([(cx, y + h * 0.15), (x + w * 0.85, y + h * 0.55), (x + w * 0.66, y + h * 0.66), (cx, y + h * 0.4),
                       (x + w * 0.34, y + h * 0.66), (x + w * 0.15, y + h * 0.55)], fill=W_)
        elif name == "reticle":
            L = w * 0.3
            for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                px, py = cx + sx * w * 0.42, cy + sy * h * 0.42
                d.line([px, py, px - sx * L, py], fill=W_, width=int(S * 1.4))
                d.line([px, py, px, py - sy * L], fill=W_, width=int(S * 1.4))
            circ(cx, cy, w * 0.06, W_)
        elif name == "petal":
            d.ellipse([x + w * 0.3, y + h * 0.1, x + w * 0.7, y + h * 0.9], fill=W_)
        elif name == "smoke":
            for k in range(9, 0, -1):
                circ(cx, cy, w * 0.05 * k, (255, 255, 255, int(110 * (1 - k / 10))))
        elif name == "rune_ring":
            circ(cx, cy, w * 0.44, W_, width=int(S * 1.0))
            circ(cx, cy, w * 0.3, W_, width=int(S * 0.8))
            for a in range(6):
                ang = a * math.pi / 3
                d.line([cx + math.cos(ang) * w * 0.3, cy + math.sin(ang) * h * 0.3, cx + math.cos(ang) * w * 0.44,
                        cy + math.sin(ang) * h * 0.44], fill=W_, width=S)
    # ---- celestial sprites (race 006)
    x, y, w, h = box("seal")
    cx, cy = x + w / 2, y + h / 2
    circ(cx, cy, w * 0.44, W_, width=int(S * 1.4))
    d.rectangle([cx - w * 0.22, cy - h * 0.22, cx + w * 0.22, cy + h * 0.22], outline=W_, width=int(S * 1.2))
    d.line([cx - w * 0.14, cy - h * 0.06, cx + w * 0.14, cy - h * 0.06], fill=W_, width=S)
    d.line([cx, cy - h * 0.16, cx, cy + h * 0.16], fill=W_, width=S)
    d.line([cx - w * 0.12, cy + h * 0.12, cx + w * 0.12, cy + h * 0.12], fill=W_, width=S)
    x, y, w, h = box("decree")
    for (a, b2, c2, e) in ((0.25, 0.22, 0.75, 0.22), (0.5, 0.12, 0.5, 0.88), (0.2, 0.5, 0.8, 0.5), (0.3, 0.88, 0.7, 0.7), (0.32, 0.32, 0.22, 0.62)):
        d.line([x + w * a, y + h * b2, x + w * c2, y + h * e], fill=W_, width=int(S * 1.3))
    x, y, w, h = box("fracture")
    cx, cy = x + w / 2, y + h / 2
    for a in range(5):
        ang = a * 2 * math.pi / 5 + 0.3
        px, py = cx, cy
        for k in range(3):
            nx = px + math.cos(ang + (k % 2) * 0.5 - 0.25) * w * 0.15
            ny = py + math.sin(ang + (k % 2) * 0.5 - 0.25) * h * 0.15
            d.line([px, py, nx, ny], fill=W_, width=int(S * (1.4 - k * 0.3)))
            px, py = nx, ny
    x, y, w, h = box("procession")
    for k in range(5):
        fx_ = x + w * (0.12 + k * 0.19)
        d.rectangle([fx_ - w * 0.05, y + h * 0.42, fx_ + w * 0.05, y + h * 0.86], fill=W_)
        circ(fx_, y + h * 0.36, w * 0.045, W_)
        if k % 2 == 0:
            d.line([fx_ + w * 0.07, y + h * 0.12, fx_ + w * 0.07, y + h * 0.86], fill=W_, width=S)
            d.rectangle([fx_ + w * 0.07, y + h * 0.12, fx_ + w * 0.15, y + h * 0.32], fill=W_)
    x, y, w, h = box("gate")
    d.rectangle([x + w * 0.22, y + h * 0.25, x + w * 0.3, y + h * 0.92], fill=W_)
    d.rectangle([x + w * 0.7, y + h * 0.25, x + w * 0.78, y + h * 0.92], fill=W_)
    d.rectangle([x + w * 0.08, y + h * 0.12, x + w * 0.92, y + h * 0.2], fill=W_)
    d.rectangle([x + w * 0.16, y + h * 0.32, x + w * 0.84, y + h * 0.37], fill=W_)
    # big crescent slash
    x, y, w, h = [v * S for v in BIG["slash"]]
    cx, cy = x + w / 2, y + h / 2
    for k in range(12):
        t = k / 11
        a = int(255 * (1 - t) ** 0.8)
        d.ellipse([cx - w * 0.46, cy - h * 0.46, cx + w * 0.46, cy + h * 0.46], fill=(255, 255, 255, 0))
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([w * 0.04, h * 0.04, w * 0.96, h * 0.96], fill=255)
    md.ellipse([w * 0.18, h * 0.0, w * 1.08, h * 0.86], fill=0)
    mask = mask.filter(ImageFilter.GaussianBlur(S * 0.8))
    big.paste(Image.new("RGBA", (w, h), (255, 255, 255, 255)), (x, y), mask)
    # rune circle decal
    x, y, w, h = [v * S for v in BIG["circle"]]
    cx, cy = x + w / 2, y + h / 2
    for rr, wd in ((0.47, 2.2), (0.40, 1.2), (0.22, 1.6)):
        circ(cx, cy, w * rr, W_, width=int(S * wd))
    for a in range(12):
        ang = a * math.pi / 6
        gx, gy = cx + math.cos(ang) * w * 0.435, cy + math.sin(ang) * h * 0.435
        d.line([gx - S * 2, gy, gx + S * 2, gy], fill=W_, width=int(S * 1.1))
        d.line([gx, gy - S * 2, gx, gy + S * 2], fill=W_, width=int(S * 1.1))
    for a in range(6):
        a1, a2 = a * math.pi / 3, a * math.pi / 3 + 2 * math.pi / 3
        d.line([cx + math.cos(a1) * w * 0.4, cy + math.sin(a1) * h * 0.4, cx + math.cos(a2) * w * 0.4,
                cy + math.sin(a2) * h * 0.4], fill=(255, 255, 255, 200), width=int(S * 0.9))
    img = big.resize((W, H), Image.LANCZOS)
    return img


# ----------------------------------------------------------------------------- particle JSON

def _uv(name):
    x, y, w, h = cell(name)
    return {"texture_width": W, "texture_height": H, "uv": [x, y], "uv_size": [w, h]}


def _uv_flip(names):
    """Pick one of several sprites per particle (by random)."""
    x0, y0, w, h = cell(names[0])
    return {"texture_width": W, "texture_height": H,
            "uv": [f"{x0} + math.floor(variable.particle_random_3 * {len(names)}) * {w}", y0], "uv_size": [w, h]}


def grad(stops, interp="v.particle_age / v.particle_lifetime"):
    return {"gradient": {str(k): v for k, v in stops}, "interpolant": interp}


def effect(ident: str, material: str, comps: dict) -> dict:
    return {"format_version": "1.10.0", "particle_effect": {
        "description": {"identifier": f"{NS}:{ident}",
                        "basic_render_parameters": {"material": material, "texture": TEX}},
        "components": comps}}


def burst(n, life="0.1"):
    return {"minecraft:emitter_rate_instant": {"num_particles": n},
            "minecraft:emitter_lifetime_once": {"active_time": life}}


def bb(size, uv, mode="lookat_xyz"):
    return {"minecraft:particle_appearance_billboard": {"size": size, "facing_camera_mode": mode, "uv": uv}}


def particles() -> Dict[str, dict]:
    P: Dict[str, dict] = {}
    fade = "math.clamp((1 - v.particle_age / v.particle_lifetime) * 3, 0, 1)"

    def add(name, material, comps):
        P[name] = effect(name, material, comps)

    # ---- salamander (attachable ambient)
    add("spore_drift", "particles_alpha", {**burst(3), "minecraft:emitter_shape_sphere": {"radius": 0.45, "direction": "outwards"},
        "minecraft:particle_initial_speed": 0.25, "minecraft:particle_lifetime_expression": {"max_lifetime": "2.2 + variable.particle_random_1"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.12, 0], "linear_drag_coefficient": 1.2},
        **bb(["0.07 * " + fade, "0.07 * " + fade], _uv("spore")),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ffdff7a0"), (1.0, "#ff9be060")])}})
    add("pollen", "particles_add", {**burst(4), "minecraft:emitter_shape_sphere": {"radius": 0.25, "direction": "outwards"},
        "minecraft:particle_initial_speed": 0.4, "minecraft:particle_lifetime_expression": {"max_lifetime": 1.6},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.2, 0], "linear_drag_coefficient": 1.6},
        **bb(["0.05", "0.05"], _uv("dot")), "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#fffff09a"), (1.0, "#00ffd060")])}})
    add("dew_burst", "particles_alpha", {**burst(14), "minecraft:emitter_shape_sphere": {"radius": 0.6, "direction": "outwards"},
        "minecraft:particle_initial_speed": 1.4, "minecraft:particle_lifetime_expression": {"max_lifetime": 0.9},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -6, 0], "linear_drag_coefficient": 0.6},
        **bb(["0.08", "0.08"], _uv("drop")), "minecraft:particle_appearance_tinting": {"color": "#ffc8f5ff"},
        "minecraft:particle_appearance_lighting": {}})
    add("dry_flake", "particles_alpha", {**burst(3), "minecraft:emitter_shape_sphere": {"radius": 0.5},
        "minecraft:particle_initial_speed": 0.2, "minecraft:particle_lifetime_expression": {"max_lifetime": 1.8},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -0.6, 0], "linear_drag_coefficient": 2},
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_1 * 360", "rotation_rate": 90},
        **bb(["0.06", "0.06"], _uv("flake")), "minecraft:particle_appearance_tinting": {"color": "#ff8c7a4a"},
        "minecraft:particle_appearance_lighting": {}})
    add("sticky_drip", "particles_alpha", {**burst(2), "minecraft:emitter_shape_sphere": {"radius": 0.15},
        "minecraft:particle_initial_speed": 0.0, "minecraft:particle_lifetime_expression": {"max_lifetime": 1.0},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -3.5, 0]},
        **bb(["0.06", "0.09"], _uv("drop")), "minecraft:particle_appearance_tinting": {"color": "#ffe9ff8a"},
        "minecraft:particle_appearance_lighting": {}})
    add("root_burst", "particles_alpha", {**burst(18), "minecraft:emitter_shape_disc": {"radius": 0.8, "plane_normal": "y", "direction": "outwards"},
        "minecraft:particle_initial_speed": 1.8, "minecraft:particle_lifetime_expression": {"max_lifetime": 1.0},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -7, 0], "linear_drag_coefficient": 0.5},
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_1 * 360", "rotation_rate": 200},
        **bb(["0.12", "0.12"], _uv("root")), "minecraft:particle_appearance_tinting": {"color": "#ff6b4a2a"},
        "minecraft:particle_appearance_lighting": {}})
    add("bubble_trail", "particles_alpha", {**burst(4), "minecraft:emitter_shape_sphere": {"radius": 0.3},
        "minecraft:particle_initial_speed": 0.3, "minecraft:particle_lifetime_expression": {"max_lifetime": 1.2},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.5, 0], "linear_drag_coefficient": 1.5},
        **bb(["0.08", "0.08"], _uv("bubble")), "minecraft:particle_appearance_tinting": {"color": "#ccdffcff"}})
    # ---- salamander (script) ----
    add("snare_strand", "particles_alpha", {
        "minecraft:emitter_rate_instant": {"num_particles": 26}, "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "0.9 + variable.particle_random_2 * 0.4"},
        "minecraft:particle_motion_parametric": {"relative_position": [
            "v.dx * v.len * variable.particle_random_1 * math.min(1, v.particle_age * 7)",
            "v.dy * v.len * variable.particle_random_1 * math.min(1, v.particle_age * 7) + math.sin(variable.particle_random_1 * 180) * 0.25 - v.particle_age * 0.3 * variable.particle_random_1",
            "v.dz * v.len * variable.particle_random_1 * math.min(1, v.particle_age * 7)"]},
        **bb(["0.07", "0.07"], _uv("drop")),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#fff0ffd8"), (0.6, "#ffd9f07a"), (1.0, "#00ffffff")])}})
    add("ensnared", "particles_alpha", {**burst(5), "minecraft:emitter_shape_box": {"half_dimensions": [0.35, 0.8, 0.35], "direction": "outwards"},
        "minecraft:particle_initial_speed": 0.05, "minecraft:particle_lifetime_expression": {"max_lifetime": 0.8},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -2.5, 0]},
        **bb(["0.06", "0.08"], _uv("drop")), "minecraft:particle_appearance_tinting": {"color": "#ffe6ff8f"}})
    add("trap_snap", "particles_alpha", {**burst(22), "minecraft:emitter_shape_sphere": {"radius": 0.5, "direction": "inwards"},
        "minecraft:particle_initial_speed": 3.5, "minecraft:particle_lifetime_expression": {"max_lifetime": 0.35},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 3},
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_1 * 360", "rotation_rate": 300},
        **bb(["0.14", "0.14"], _uv("leaf")),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ff4fb83a"), (1.0, "#ffc0193a")])}})
    add("heal_leaf", "particles_alpha", {**burst(8), "minecraft:emitter_shape_sphere": {"radius": 0.5},
        "minecraft:particle_initial_speed": 0.5, "minecraft:particle_lifetime_expression": {"max_lifetime": 1.2},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.9, 0], "linear_drag_coefficient": 1.5},
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_1 * 360", "rotation_rate": 90},
        **bb(["0.1", "0.1"], _uv("leaf")), "minecraft:particle_appearance_tinting": {"color": "#ff8ae25a"}})
    add("hydrate", "particles_add", {**burst(10), "minecraft:emitter_shape_sphere": {"radius": 1.2, "direction": "inwards"},
        "minecraft:particle_initial_speed": 1.5, "minecraft:particle_lifetime_expression": {"max_lifetime": 0.7},
        **bb(["0.06", "0.06"], _uv("dot")), "minecraft:particle_appearance_tinting": {"color": "#ff6fd7ff"}})
    add("jet_trail", "particles_alpha", {"minecraft:emitter_rate_steady": {"spawn_rate": 45, "max_particles": 40},
        "minecraft:emitter_lifetime_once": {"active_time": 0.5}, "minecraft:emitter_shape_sphere": {"radius": 0.35},
        "minecraft:particle_initial_speed": 0.3, "minecraft:particle_lifetime_expression": {"max_lifetime": 1.3},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.4, 0], "linear_drag_coefficient": 1.5},
        "minecraft:emitter_local_space": {"position": False, "rotation": False},
        **bb(["0.1", "0.1"], _uv("bubble")), "minecraft:particle_appearance_tinting": {"color": "#d9e6ffff"}})
    add("jet_ring", "particles_alpha", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.45},
        **bb(["0.4 + v.particle_age * 5", "0.4 + v.particle_age * 5"], _uv("ring"), "lookat_xyz"),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ffdff8ff"), (1.0, "#00bfe8ff")])}})
    # ---- golem (attachable) ----
    add("rune_mote", "particles_add", {**burst(2), "minecraft:emitter_shape_sphere": {"radius": 0.35, "direction": "outwards"},
        "minecraft:particle_initial_speed": 0.25, "minecraft:particle_lifetime_expression": {"max_lifetime": 1.6},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.35, 0], "linear_drag_coefficient": 1.2},
        **bb(["0.08", "0.08"], _uv_flip(["glyph_a", "glyph_b", "glyph_c", "glyph_d"])),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ffffe39a"), (1.0, "#00ff9a2a")])}})
    add("rune_burst", "particles_add", {**burst(24), "minecraft:emitter_shape_sphere": {"radius": 0.4, "direction": "outwards"},
        "minecraft:particle_initial_speed": 3.2, "minecraft:particle_lifetime_expression": {"max_lifetime": 0.7},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 3},
        **bb(["0.12", "0.12"], _uv_flip(["glyph_a", "glyph_b", "glyph_c", "glyph_d"])),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#fffff0b8"), (1.0, "#00ff7a1e")])}})
    add("rune_pulse", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.4},
        **bb(["0.3 + v.particle_age * 4", "0.3 + v.particle_age * 4"], _uv("rune_ring")),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ffffd27a"), (1.0, "#00ff9a2a")])}})
    add("rune_spark", "particles_add", {**burst(6), "minecraft:emitter_shape_sphere": {"radius": 0.5, "direction": "outwards"},
        "minecraft:particle_initial_speed": 2.0, "minecraft:particle_lifetime_expression": {"max_lifetime": 0.45},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -4, 0], "linear_drag_coefficient": 1},
        **bb(["0.07", "0.07"], _uv("spark")), "minecraft:particle_appearance_tinting": {"color": "#ffff5a2a"}})
    # footfall / landing dust (attachable animations: golem stomps, heavy landings, jackalope thump)
    add("step_dust", "particles_alpha", {**burst(6), "minecraft:emitter_shape_disc": {"radius": 0.3, "plane_normal": "y", "direction": "outwards"},
        "minecraft:particle_initial_speed": "0.8 + variable.particle_random_1 * 0.6",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "0.55 + variable.particle_random_2 * 0.4"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.5, 0], "linear_drag_coefficient": 3.2},
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_3 * 360", "rotation_rate": 30},
        **bb(["(0.08 + v.particle_age * 0.16) * " + fade, "(0.08 + v.particle_age * 0.16) * " + fade], _uv("smoke")),
        "minecraft:particle_appearance_tinting": {"color": "#c09a9088"},
        "minecraft:particle_appearance_lighting": {}})
    add("land_dust", "particles_alpha", {**burst(14), "minecraft:emitter_shape_disc": {"radius": 0.5, "plane_normal": "y", "direction": "outwards"},
        "minecraft:particle_initial_speed": "1.6 + variable.particle_random_1 * 1.2",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "0.7 + variable.particle_random_2 * 0.5"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.6, 0], "linear_drag_coefficient": 3.0},
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_3 * 360", "rotation_rate": 40},
        **bb(["(0.1 + v.particle_age * 0.22) * " + fade, "(0.1 + v.particle_age * 0.22) * " + fade], _uv("smoke")),
        "minecraft:particle_appearance_tinting": {"color": "#c09a9088"},
        "minecraft:particle_appearance_lighting": {}})
    # ---- xenentoma (attachable + script) ----
    add("sensilla_mote", "particles_add", {**burst(2), "minecraft:emitter_shape_sphere": {"radius": 0.12, "direction": "outwards"},
        "minecraft:particle_initial_speed": 0.15, "minecraft:particle_lifetime_expression": {"max_lifetime": "0.9 + variable.particle_random_1 * 0.6"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.25, 0], "linear_drag_coefficient": 1.5},
        **bb(["0.045 * " + fade, "0.045 * " + fade], _uv("spark")),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ffe9dcff"), (1.0, "#ff9a7ad8")])}})
    add("sensilla_ripple", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.5},
        **bb(["0.1 + v.particle_age * 1.2", "0.1 + v.particle_age * 1.2"], _uv("ring")),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ffd9c8ff"), (1.0, "#00a07ae0")])}})
    add("vibration_ping", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.9},
        **bb(["0.25 + v.particle_age * 1.6", "0.25 + v.particle_age * 1.6"], _uv("ring"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#fff4ecff"), (0.4, "#ffc0a4f2"), (1.0, "#00a07ae0")])}})
    add("vibration_trace", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.7},
        **bb(["0.15 + v.particle_age * 0.9", "0.15 + v.particle_age * 0.9"], _uv("ring"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#a08c78c0"), (1.0, "#005a4a80")])}})
    add("molt_fluid", "particles_alpha", {**burst(3), "minecraft:emitter_shape_sphere": {"radius": 0.35},
        "minecraft:particle_initial_speed": 0.2, "minecraft:particle_lifetime_expression": {"max_lifetime": 0.9},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -4.0, 0]},
        **bb(["0.05", "0.07"], _uv("drop")), "minecraft:particle_appearance_tinting": {"color": "#ccdfc8f2"},
        "minecraft:particle_appearance_lighting": {}})
    add("chitin_shards", "particles_alpha", {**burst(16), "minecraft:emitter_shape_box": {"half_dimensions": [0.3, 0.8, 0.3], "direction": "outwards"},
        "minecraft:particle_initial_speed": "1.6 + variable.particle_random_1 * 1.4", "minecraft:particle_lifetime_expression": {"max_lifetime": 1.1},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -9, 0], "linear_drag_coefficient": 0.6},
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_1 * 360", "rotation_rate": 360},
        **bb(["0.11", "0.11"], _uv("shard")), "minecraft:particle_appearance_tinting": {"color": "#ffe6e0d2"},
        "minecraft:particle_appearance_lighting": {}})
    add("surge_strike", "particles_add", {**burst(6), "minecraft:emitter_shape_sphere": {"radius": 0.2, "direction": "outwards"},
        "minecraft:particle_initial_speed": 2.2, "minecraft:particle_lifetime_expression": {"max_lifetime": 0.35},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 4},
        **bb(["0.09", "0.09"], _uv("spark")), "minecraft:particle_appearance_tinting": {"color": "#ffd2b4ff"}})
    # ---- flying spaghetti monster (attachable + script) ----
    add("sauce_drip", "particles_alpha", {**burst(2), "minecraft:emitter_shape_point": {},
        "minecraft:particle_initial_speed": 0.0, "minecraft:particle_lifetime_expression": {"max_lifetime": 1.0},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -6, 0]},
        **bb(["0.06", "0.09"], _uv("drop")), "minecraft:particle_appearance_tinting": {"color": "#ffc22a1c"},
        "minecraft:particle_appearance_lighting": {}})
    add("sauce_splash", "particles_alpha", {**burst(14), "minecraft:emitter_shape_sphere": {"radius": 0.5, "direction": "outwards"},
        "minecraft:particle_initial_speed": "1.5 + variable.particle_random_1 * 1.5", "minecraft:particle_lifetime_expression": {"max_lifetime": 0.8},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -9, 0], "linear_drag_coefficient": 0.8},
        **bb(["0.07", "0.07"], _uv("drop")), "minecraft:particle_appearance_tinting": {"color": "#ffd23620"},
        "minecraft:particle_appearance_lighting": {}})
    add("sauce_spiral", "particles_alpha", {"minecraft:emitter_rate_steady": {"spawn_rate": 30, "max_particles": 30},
        "minecraft:emitter_lifetime_once": {"active_time": 0.6}, "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.0},
        "minecraft:particle_initial_speed": 0.0,
        "minecraft:particle_motion_parametric": {"relative_position": [
            "math.cos(v.particle_age * 540 + v.particle_random_1 * 360) * (0.4 + v.particle_age * 0.5)",
            "v.particle_age * 1.6",
            "math.sin(v.particle_age * 540 + v.particle_random_1 * 360) * (0.4 + v.particle_age * 0.5)"]},
        **bb(["0.08 * " + fade, "0.08 * " + fade], _uv("drop")), "minecraft:particle_appearance_tinting": {"color": "#ffd8402a"}})
    add("dente_crack", "particles_alpha", {**burst(10), "minecraft:emitter_shape_sphere": {"radius": 0.6, "direction": "outwards"},
        "minecraft:particle_initial_speed": 1.4, "minecraft:particle_lifetime_expression": {"max_lifetime": 0.7},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -8, 0]},
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_1 * 360", "rotation_rate": 300},
        **bb(["0.08", "0.08"], _uv("shard")), "minecraft:particle_appearance_tinting": {"color": "#fff0d070"},
        "minecraft:particle_appearance_lighting": {}})
    add("pasta_steam", "particles_alpha", {**burst(3), "minecraft:emitter_shape_sphere": {"radius": 0.4},
        "minecraft:particle_initial_speed": 0.2, "minecraft:particle_lifetime_expression": {"max_lifetime": 1.6},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.6, 0], "linear_drag_coefficient": 1.5},
        **bb(["(0.12 + v.particle_age * 0.2) * " + fade, "(0.12 + v.particle_age * 0.2) * " + fade], _uv("smoke")),
        "minecraft:particle_appearance_tinting": {"color": "#90706864"}})
    add("pasta_vortex", "particles_alpha", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.6},
        "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 400},
        **bb(["1.0 + v.particle_age * 5", "1.0 + v.particle_age * 5"], _uv("ring"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#e0ffd060"), (0.5, "#c0e04a30"), (1.0, "#00c0302a")])}})
    add("sauce_wave", "particles_alpha", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.7},
        **bb(["0.6 + v.particle_age * 11", "0.6 + v.particle_age * 11"], _uv("ring"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ffe0402a"), (1.0, "#00b0201a")])}})
    add("meatball_trail", "particles_alpha", {"minecraft:emitter_rate_steady": {"spawn_rate": 18, "max_particles": 20},
        "minecraft:emitter_lifetime_looping": {"active_time": 1}, "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.5},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -4, 0]},
        **bb(["0.06", "0.06"], _uv("drop")), "minecraft:particle_appearance_tinting": {"color": "#ffb82418"},
        "minecraft:particle_appearance_lighting": {}})
    add("noodle_strand", "particles_alpha", {
        "minecraft:emitter_rate_instant": {"num_particles": 22}, "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.7},
        "minecraft:particle_initial_speed": 0,
        "minecraft:particle_motion_parametric": {"relative_position": [
            "v.dx * (v.particle_random_1) * math.sin(math.min(v.particle_age / 0.35, 1) * 90) * (v.particle_age < 0.35 ? 1 : (1 - (v.particle_age - 0.35) / 0.35))",
            "v.dy * (v.particle_random_1) * (v.particle_age < 0.35 ? 1 : (1 - (v.particle_age - 0.35) / 0.35)) + math.sin(v.particle_random_1 * 900) * 0.12",
            "v.dz * (v.particle_random_1) * math.sin(math.min(v.particle_age / 0.35, 1) * 90) * (v.particle_age < 0.35 ? 1 : (1 - (v.particle_age - 0.35) / 0.35))"]},
        **bb(["0.07", "0.07"], _uv("dot")), "minecraft:particle_appearance_tinting": {"color": "#fff3dc98"},
        "minecraft:particle_appearance_lighting": {}})
    # ---- nurariten (attachable + script) ----
    add("royal_mote", "particles_add", {**burst(3), "minecraft:emitter_shape_sphere": {"radius": 0.5},
        "minecraft:particle_initial_speed": 0.05, "minecraft:particle_lifetime_expression": {"max_lifetime": "1.6 + variable.particle_random_1"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.15, 0], "linear_drag_coefficient": 1.0},
        **bb(["0.05 * " + fade, "0.05 * " + fade], _uv("spark")), "minecraft:particle_appearance_tinting": {"color": "#fff6d47a"}})
    add("decree_burst", "particles_add", {**burst(10), "minecraft:emitter_shape_sphere": {"radius": 0.3, "direction": "outwards"},
        "minecraft:particle_initial_speed": 1.2, "minecraft:particle_lifetime_expression": {"max_lifetime": 0.9},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 2.5},
        **bb(["0.16 * " + fade, "0.16 * " + fade], _uv("decree")), "minecraft:particle_appearance_tinting": {"color": "#ffffdc8a"}})
    add("procession_shadow", "particles_alpha", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 3.2},
        "minecraft:particle_motion_parametric": {"relative_position": ["v.particle_age * 0.45 - 0.7", 0, 0]},
        **bb(["1.3", "0.5"], _uv("procession"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#00000000"), (0.2, "#5a000000"), (0.8, "#5a000000"), (1.0, "#00000000")])}})
    add("court_pillar", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.0},
        "minecraft:particle_motion_parametric": {"relative_position": [0, "v.particle_age * 0.6", 0]},
        **bb(["0.12", "1.4 * " + fade], _uv("dot"), "lookat_y"),
        "minecraft:particle_appearance_tinting": {"color": "#ffffd67a"}})
    add("court_ring", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.2},
        **bb(["v.size * 0.5", "v.size * 0.5"], _uv("rune_ring"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#00ffe08a"), (0.3, "#b0ffe08a"), (1.0, "#00ffd070")])}})
    add("judgment_seal", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.5},
        **bb(["0.25 + v.stacks * 0.12", "0.25 + v.stacks * 0.12"], _uv("seal")),
        "minecraft:particle_appearance_tinting": {"color": "#ffffc24a"}})
    add("arrival_gate", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.9},
        **bb(["2.4", "2.4"], _uv("gate")),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#00ffe8a0"), (0.25, "#ffffe8a0"), (1.0, "#00ffd060")])}})
    add("gate_shadow", "particles_alpha", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 2.4},
        **bb(["3.2", "3.2"], _uv("gate"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#00a07818"), (0.3, "#80a07818"), (1.0, "#00a07818")])}})
    add("sky_fracture", "particles_add", {**burst(12), "minecraft:emitter_shape_disc": {"radius": 7.0, "plane_normal": "y"},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "1.2 + variable.particle_random_1"},
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_2 * 360", "rotation_rate": 6},
        **bb(["1.0 + v.particle_random_3 * 1.4", "1.0 + v.particle_random_3 * 1.4"], _uv("fracture")),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#00fff8e0"), (0.2, "#fffff8e0"), (1.0, "#00ffe0a0")])}})
    add("heaven_ring", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.8},
        **bb(["2 + v.particle_age * 9", "2 + v.particle_age * 9"], _uv("rune_ring"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#fffff2c0"), (1.0, "#00ffd070")])}})
    add("seal_converge", "particles_add", {
        "minecraft:emitter_rate_instant": {"num_particles": 16}, "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.8},
        "minecraft:particle_initial_speed": 0,
        "minecraft:particle_motion_parametric": {"relative_position": [
            "v.dx * math.clamp(v.particle_age / 0.6 - v.particle_random_1 * 0.4, 0, 1)",
            "v.dy * math.clamp(v.particle_age / 0.6 - v.particle_random_1 * 0.4, 0, 1)",
            "v.dz * math.clamp(v.particle_age / 0.6 - v.particle_random_1 * 0.4, 0, 1)"]},
        **bb(["0.18", "0.18"], _uv("seal")), "minecraft:particle_appearance_tinting": {"color": "#ffffd24a"}})
    add("dissolve_light", "particles_add", {**burst(20), "minecraft:emitter_shape_box": {"half_dimensions": [1.4, 1.0, 1.4]},
        "minecraft:particle_initial_speed": 0.2, "minecraft:particle_lifetime_expression": {"max_lifetime": "1.0 + variable.particle_random_1"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.4, 0], "linear_drag_coefficient": 1.0},
        **bb(["0.08 * " + fade, "0.08 * " + fade], _uv("spark")), "minecraft:particle_appearance_tinting": {"color": "#ffffefb0"}})
    # ---- golem (script) ----
    add("shock_rupture", "particles_alpha", {**burst(9), "minecraft:emitter_shape_disc": {"radius": 0.7, "plane_normal": "y", "direction": [0, 1, 0]},
        "minecraft:particle_initial_speed": "3.2 + variable.particle_random_1 * 2", "minecraft:particle_lifetime_expression": {"max_lifetime": 0.8},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -14, 0]},
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_1 * 360", "rotation_rate": 400},
        **bb(["0.18", "0.18"], _uv("shard")), "minecraft:particle_appearance_tinting": {"color": "#ff3a3a40"},
        "minecraft:particle_appearance_lighting": {}})
    add("shock_glow", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.5},
        **bb(["0.8 + v.particle_age * 3", "0.8 + v.particle_age * 3"], _uv("rune_ring"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ffffc94a"), (1.0, "#00ff6a10")])}})
    add("impact_ring", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.6},
        **bb(["0.5 + v.particle_age * 9", "0.5 + v.particle_age * 9"], _uv("ring"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ffffd27a"), (1.0, "#00ff8a2a")])}})
    add("glyph_circle", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "v.life"},
        "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 14},
        **bb(["v.radius * math.min(1, v.particle_age * 3)", "v.radius * math.min(1, v.particle_age * 3)"], _uv("circle"), "emitter_transform_xz"),
        "minecraft:particle_appearance_tinting": {"color": ["1.0", "0.82", "0.35", "0.85 * math.clamp((v.life - v.particle_age) * 2, 0, 1)"]}})
    add("glyph_pillar", "particles_add", {**burst(6), "minecraft:emitter_shape_point": {},
        "minecraft:particle_initial_speed": 0, "minecraft:particle_lifetime_expression": {"max_lifetime": "0.8 + variable.particle_random_1 * 0.6"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 2.2, 0]},
        **bb(["0.16", "0.16"], _uv_flip(["glyph_a", "glyph_b", "glyph_c", "glyph_d"])),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ffffe39a"), (1.0, "#00ff9a2a")])}})
    add("shard_stream", "particles_alpha", {
        "minecraft:emitter_rate_instant": {"num_particles": 18}, "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_sphere": {"radius": 0.8},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.55},
        "minecraft:particle_motion_parametric": {"relative_position": [
            "v.dx * v.len * math.pow(v.particle_age / 0.55, 1.4) + math.sin(v.particle_age * 600 + variable.particle_random_1 * 360) * 0.3",
            "v.dy * v.len * math.pow(v.particle_age / 0.55, 1.4) + math.sin(v.particle_age / 0.55 * 180) * 1.2",
            "v.dz * v.len * math.pow(v.particle_age / 0.55, 1.4) + math.cos(v.particle_age * 600 + variable.particle_random_2 * 360) * 0.3"]},
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_1 * 360", "rotation_rate": 500},
        **bb(["0.2", "0.2"], _uv("shard")), "minecraft:particle_appearance_tinting": {"color": "#ff35353b"},
        "minecraft:particle_appearance_lighting": {}})
    add("bastion_flash", "particles_add", {**burst(16), "minecraft:emitter_shape_disc": {"radius": 1.1, "plane_normal": "z"},
        "minecraft:emitter_local_space": {"position": True, "rotation": True},
        "minecraft:particle_initial_speed": 0.2, "minecraft:particle_lifetime_expression": {"max_lifetime": 0.6},
        **bb(["0.14", "0.14"], _uv_flip(["glyph_a", "glyph_b", "glyph_c", "glyph_d"])),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ffffeab0"), (1.0, "#00ffb04a")])}})
    # ---- jackalope (attachable) ----
    add("moon_mote", "particles_add", {**burst(2), "minecraft:emitter_shape_sphere": {"radius": 0.4},
        "minecraft:particle_initial_speed": 0.15, "minecraft:particle_lifetime_expression": {"max_lifetime": 2.0},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.25, 0], "linear_drag_coefficient": 1.0},
        **bb(["0.05", "0.05"], _uv("dot")), "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ffe9ecff"), (1.0, "#00a9b6ff")])}})
    add("blood_ember", "particles_add", {**burst(3), "minecraft:emitter_shape_sphere": {"radius": 0.35, "direction": "outwards"},
        "minecraft:particle_initial_speed": 0.45, "minecraft:particle_lifetime_expression": {"max_lifetime": "0.9 + variable.particle_random_1 * 0.5"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.9, 0], "linear_drag_coefficient": 1.2},
        **bb(["0.06", "0.06"], _uv("ember")), "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ffff6a6a"), (0.5, "#ffd10a2a"), (1.0, "#00400008")])}})
    add("blood_mist", "particles_blend", {**burst(2), "minecraft:emitter_shape_sphere": {"radius": 0.4},
        "minecraft:particle_initial_speed": 0.1, "minecraft:particle_lifetime_expression": {"max_lifetime": 1.6},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -0.1, 0], "linear_drag_coefficient": 1.0},
        **bb(["0.3 + v.particle_age * 0.3", "0.3 + v.particle_age * 0.3"], _uv("smoke")),
        "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#80a0101e"), (1.0, "#00400008")])}})
    add("awaken_spiral", "particles_add", {"minecraft:emitter_rate_steady": {"spawn_rate": 60, "max_particles": 90},
        "minecraft:emitter_lifetime_once": {"active_time": 1.4}, "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.2},
        "minecraft:particle_motion_parametric": {"relative_position": [
            "math.cos(v.emitter_age * 520 + variable.particle_random_1 * 60) * (1.2 - v.particle_age)",
            "-1.6 + v.particle_age * 1.8",
            "math.sin(v.emitter_age * 520 + variable.particle_random_1 * 60) * (1.2 - v.particle_age)"]},
        **bb(["0.07", "0.07"], _uv("ember")), "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ffff4a5a"), (1.0, "#00b0001a")])}})
    # ---- jackalope (script) ----
    add("crescent_trail", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.7},
        "minecraft:particle_initial_spin": {"rotation": "variable.particle_random_1 * 360"},
        **bb(["0.55", "0.55"], _uv("crescent")),
        "minecraft:particle_appearance_tinting": {"color": ["v.red", "v.green", "v.blue", "math.clamp(1 - v.particle_age / 0.7, 0, 1) * 0.85"]}})
    add("crimson_slash", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.35},
        "minecraft:particle_initial_spin": {"rotation": "v.spin"},
        **bb(["1.6 * v.scale", "1.6 * v.scale"], _uv("slash")),
        "minecraft:particle_appearance_tinting": {"color": ["1.0", "0.2 + v.particle_age", "0.25", "1 - v.particle_age / 0.35"]}})
    add("moon_sigil", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.55},
        "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 90},
        **bb(["0.35", "0.35"], _uv("sigil")),
        "minecraft:particle_appearance_tinting": {"color": ["v.red", "v.green", "v.blue", "0.9"]}})
    add("velvet_burst", "particles_add", {**burst(30), "minecraft:emitter_shape_sphere": {"radius": 0.6, "direction": "outwards"},
        "minecraft:particle_initial_speed": "2 + variable.particle_random_1 * 2", "minecraft:particle_lifetime_expression": {"max_lifetime": 1.0},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 2.4},
        **bb(["0.12", "0.12"], _uv("dust")), "minecraft:particle_appearance_tinting": {"color": grad([(0.0, "#ffd7c9ff"), (1.0, "#008a60c8")])}})
    add("velvet_shimmer", "particles_add", {**burst(4), "minecraft:emitter_shape_box": {"half_dimensions": [0.35, 0.9, 0.35]},
        "minecraft:particle_initial_speed": 0.1, "minecraft:particle_lifetime_expression": {"max_lifetime": 0.8},
        **bb(["0.06", "0.06"], _uv("dust")), "minecraft:particle_appearance_tinting": {"color": "#ffcdb7ff"}})
    add("sense_ping", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.0},
        **bb(["0.3", "0.3"], _uv("ping")),
        "minecraft:particle_appearance_tinting": {"color": ["v.red", "v.green", "v.blue", "math.clamp(1 - v.particle_age, 0, 1) * 0.9"]}})
    # ---- shared ----
    add("target_reticle", "particles_add", {**burst(1), "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.3},
        **bb(["0.6", "0.6"], _uv("reticle")),
        "minecraft:particle_appearance_tinting": {"color": ["v.red", "v.green", "v.blue", "0.95"]}})
    add("rite_aura", "particles_add", {"minecraft:emitter_rate_steady": {"spawn_rate": 50, "max_particles": 80},
        "minecraft:emitter_lifetime_once": {"active_time": 1.6}, "minecraft:emitter_shape_disc": {"radius": 1.0, "plane_normal": "y"},
        "minecraft:particle_initial_speed": 0, "minecraft:particle_lifetime_expression": {"max_lifetime": 1.4},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.8, 0]},
        **bb(["0.1", "0.1"], _uv_flip(["glyph_a", "glyph_b", "glyph_c", "glyph_d"])),
        "minecraft:particle_appearance_tinting": {"color": ["v.red", "v.green", "v.blue", "1 - v.particle_age / 1.4"]}})
    # v1.2: races 004-006 are redrawn on their own full-colour atlas (fx_ex); same identifiers
    import fx_ex
    redrawn = fx_ex.particles()
    assert set(redrawn) == set(fx_ex.RACE_PARTICLES) and set(redrawn) <= set(P), "fx_ex must only redraw existing effects"
    P.update(redrawn)
    # v1.3: every ability effect of all six races becomes a layered entry effect on the
    # animated white atlas (vfx/); identifiers stay, layers are new plrace:vx_* effects
    from vfx import races as vfx_races
    P.update(vfx_races.build())
    return P


def heaven_fog() -> dict:
    """Nurariten's ultimate: a golden haze pushed only on players near it (never the sky)."""
    return {"format_version": "1.16.100", "minecraft:fog_settings": {
        "description": {"identifier": f"{NS}:heaven_light"},
        "distance": {
            "air": {"fog_start": 0.55, "fog_end": 1.0, "fog_color": "#f6e2a2", "render_distance_type": "render"},
            "weather": {"fog_start": 0.4, "fog_end": 0.9, "fog_color": "#efd894", "render_distance_type": "render"},
        }}}


def fog() -> dict:
    return {"format_version": "1.16.100", "minecraft:fog_settings": {
        "description": {"identifier": f"{NS}:blood_moon"},
        "distance": {
            "air": {"fog_start": 0.45, "fog_end": 1.0, "fog_color": "#3a0b12", "render_distance_type": "render"},
            "weather": {"fog_start": 0.3, "fog_end": 0.85, "fog_color": "#2e080e", "render_distance_type": "render"},
        }}}
