"""Particle kit: one shared sprite sheet + a compact builder for Bedrock particle effects.

    fx = Particles(pack)
    fx.effect("dw_glyph_rise", "glyph1", count=6, life=(0.8, 1.4), size=(0.18, 0.0),
              shape=("sphere", 0.6), speed=(0.3, 0.8), accel=(0, 0.6, 0), colors=["#fff3c4", "#c9a24a00"])
Scripts spawn it as "grimoire:dw_glyph_rise"; animations reference it through the actor's
`particles={...}` map.  Sprites are 16x16 cells in textures/particle/grimoire_particles.png.
"""
from __future__ import annotations

import math
import os

import numpy as np
from PIL import Image

from . import glyphs
from .pack import _write

CELL = 16
COLS = 8
SHEET = "textures/particle/grimoire_particles"


def _grid():
    y, x = np.mgrid[0:CELL, 0:CELL]
    return (x + 0.5) / CELL * 2 - 1, 1 - (y + 0.5) / CELL * 2


def _soft(power=2.0, r=1.0):
    u, v = _grid()
    return np.clip(1 - np.hypot(u, v) / r, 0, 1) ** power


def _bitmap(rows):
    bm = glyphs.bitmap(rows).astype(float)
    h, w = bm.shape
    out = np.zeros((CELL, CELL))
    s = max(1, min(CELL // w, CELL // h))
    big = np.kron(bm, np.ones((s, s)))
    oy, ox = (CELL - big.shape[0]) // 2, (CELL - big.shape[1]) // 2
    out[oy:oy + big.shape[0], ox:ox + big.shape[1]] = big
    return out


def _sprites():
    u, v = _grid()
    r = np.hypot(u, v)
    a = np.arctan2(v, u)
    sp = {}
    sp["dot"] = _soft(1.6)
    sp["glow"] = _soft(3.0)
    sp["hard"] = (r < 0.55).astype(float)
    sp["spark"] = np.clip(np.maximum(1 - np.abs(u) * 9, 0) * (1 - np.abs(v)) + np.maximum(1 - np.abs(v) * 9, 0) * (1 - np.abs(u)), 0, 1)
    sp["star"] = np.clip((0.42 + 0.58 * np.abs(np.cos(a * 2.5)) ** 3 - r) * 6, 0, 1)
    sp["ring"] = np.clip(1 - np.abs(r - 0.72) * 7, 0, 1)
    sp["ringthin"] = np.clip(1 - np.abs(r - 0.82) * 14, 0, 1)
    sp["diamond"] = np.clip((0.85 - (np.abs(u) + np.abs(v))) * 8, 0, 1)
    sp["shard"] = np.clip((1 - np.abs(u) * 3.2 - np.abs(v) * 0.9) * 5, 0, 1)
    sp["ember"] = np.clip(_soft(1.2, 0.7) * 1.4, 0, 1)
    sp["petal"] = np.clip((1 - (u / 0.55) ** 2 - ((v - 0.1) / 0.95) ** 2) * 4, 0, 1)
    sp["feather"] = np.clip((1 - (u / (0.2 + 0.25 * (1 - v))) ** 2 - (v / 1.0) ** 2) * 3, 0, 1)
    sp["leaf"] = np.clip((1 - np.abs(u) * (2.2 + v) - np.abs(v) * 0.95) * 5, 0, 1)
    sp["moon"] = np.clip(((r < 0.85) & (np.hypot(u - 0.38, v) > 0.72)).astype(float), 0, 1)
    sp["drop"] = np.clip((1 - np.hypot(u * (1.6 + v * 0.8), v + 0.2) / 0.8) * 5, 0, 1)
    sp["flake"] = np.clip(np.maximum.reduce([1 - np.abs(np.sin(a * 3)) * r * 9 - (r > 0.95) * 9, (r < 0.18) * 1.0]), 0, 1) * (r < 0.98)
    sp["puff"] = np.clip(_soft(0.8, 1.0) * (0.75 + 0.25 * np.sin(a * 5 + r * 6)), 0, 1)
    sp["smoke"] = np.clip(_soft(0.6, 1.0) * (0.6 + 0.4 * np.cos(a * 3 - r * 4)), 0, 1)
    sp["slash"] = np.clip(1 - np.abs(u - v * 0.9) * 5 - np.abs(v) * 0.35, 0, 1)
    sp["beam"] = np.clip((1 - np.abs(u) * 2.6), 0, 1)
    sp["wave"] = np.clip(1 - np.abs(v - 0.45 * np.sin(u * math.pi * 1.5)) * 6, 0, 1)
    sp["arc"] = np.clip(1 - np.abs(r - 0.8) * 9, 0, 1) * (v > 0.1)
    sp["cross"] = np.clip(np.maximum(1 - np.abs(u) * 5, 1 - np.abs(v) * 5), 0, 1) * (np.maximum(np.abs(u), np.abs(v)) < 0.85)
    sp["eye"] = np.clip(((np.abs(v) <= (1 - u ** 2) * 0.55) & (r > 0.22)).astype(float) + (r < 0.12), 0, 1)
    sp["scale"] = np.clip(((r < 0.8) & (v < 0.35)).astype(float) * (0.55 + 0.45 * (v + 1) / 1.4), 0, 1)
    sp["bone"] = np.clip(((np.abs(v) < 0.14) & (np.abs(u) < 0.7)).astype(float) + (np.hypot(np.abs(u) - 0.7, np.abs(v) - 0.16) < 0.2), 0, 1)
    sp["rock"] = np.clip(((np.abs(u) * 0.9 + np.abs(v) * 1.1 + 0.18 * np.sin(a * 4)) < 0.8).astype(float), 0, 1)
    sp["note"] = _bitmap(["  ## ", "  # #", "  #  ", "  #  ", "###  ", "###  "])
    sp["door"] = _bitmap(glyphs.DREAM["door"])
    sp["key"] = _bitmap(glyphs.DREAM["key"])
    sp["window"] = _bitmap(glyphs.DREAM["window"])
    for i in range(8):
        sp[f"glyph{i + 1}"] = _bitmap(glyphs.FIRST_WORD[i])
    for i in range(6):
        sp[f"rune{i + 1}"] = _bitmap(glyphs.DRACONIC[i])
    return sp


class Particles:
    def __init__(self, pack):
        self.pack = pack
        self.sprites = _sprites()
        self.names = list(self.sprites)
        self._sheet_written = False

    def write_sheet(self):
        rows = math.ceil(len(self.names) / COLS)
        h = 1
        while h < rows * CELL:
            h *= 2
        img = np.zeros((h, COLS * CELL, 4), dtype=np.uint8)
        for i, n in enumerate(self.names):
            cx, cy = (i % COLS) * CELL, (i // COLS) * CELL
            a = np.clip(self.sprites[n], 0, 1)
            img[cy:cy + CELL, cx:cx + CELL, :3] = 255
            img[cy:cy + CELL, cx:cx + CELL, 3] = np.round(a * 255)
        p = os.path.join(self.pack.rp, SHEET + ".png")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        Image.fromarray(img, "RGBA").save(p, optimize=True)
        self.sheet_h = h
        self._sheet_written = True

    def effect(self, name, sprite, *, count=1, rate=None, emit_time=0.1, loop=False, life=(0.6, 1.0),
               size=(0.2, 0.0), shape="point", direction="outwards", speed=0.0, accel=(0, 0, 0), drag=0.0,
               colors=("#ffffffff", "#ffffff00"), blend="add", spin=None, facing="lookat_xyz", sprites=None,
               offset=(0, 0, 0), size_y=None, light=False, collide=False, stretch=None):
        """Register a particle effect `grimoire:<name>`.

        count: burst size (instant) unless rate (particles/second, steady over emit_time) is given.
        life: seconds (min, max).  size: (start, end) half-extent in blocks, linear over lifetime.
        shape: 'point' | ('sphere', r) | ('disc', r) | ('box', (hx, hy, hz)) ; add 'surface' as 3rd item for shell.
        direction: 'outwards' | 'inwards' | (x, y, z).   speed: number or (min, max).
        colors: gradient stops over lifetime '#rrggbb' or '#rrggbbaa' (alpha fades).
        blend: 'add' (luminous) | 'blend' | 'alpha'.   spin: (start_deg_range, rate) e.g. (360, 90).
        facing: lookat_xyz | rotate_xyz | lookat_y | direction_z | emitter_transform_xz (flat on ground) ...
        sprites: list of sprite names to pick randomly per particle (overrides sprite).
        """
        if not self._sheet_written:
            self.write_sheet()
        comps = {}
        if rate is not None:
            comps["minecraft:emitter_rate_steady"] = {"spawn_rate": rate, "max_particles": max(8, int(rate * life[1] * 1.5) + 8)}
        else:
            comps["minecraft:emitter_rate_instant"] = {"num_particles": int(count)}
        comps["minecraft:emitter_lifetime_looping" if loop else "minecraft:emitter_lifetime_once"] = {"active_time": emit_time}
        dirv = direction if isinstance(direction, str) else [float(x) for x in direction]
        if shape == "point":
            comps["minecraft:emitter_shape_point"] = {"offset": list(offset), **({"direction": dirv} if not isinstance(dirv, str) else {})}
        else:
            kind, dim = shape[0], shape[1]
            surf = len(shape) > 2
            if kind == "sphere":
                comps["minecraft:emitter_shape_sphere"] = {"offset": list(offset), "radius": dim, "surface_only": surf, "direction": dirv}
            elif kind == "disc":
                comps["minecraft:emitter_shape_disc"] = {"offset": list(offset), "radius": dim, "plane_normal": "y", "surface_only": surf, "direction": dirv}
            else:
                comps["minecraft:emitter_shape_box"] = {"offset": list(offset), "half_dimensions": list(dim), "surface_only": surf, "direction": dirv}
        comps["minecraft:particle_lifetime_expression"] = {"max_lifetime": f"math.random({life[0]}, {life[1]})"}
        sp = speed if isinstance(speed, (tuple, list)) else (speed, speed)
        comps["minecraft:particle_initial_speed"] = sp[0] if sp[0] == sp[1] else f"math.random({sp[0]}, {sp[1]})"
        comps["minecraft:particle_motion_dynamic"] = {"linear_acceleration": [float(x) for x in accel],
                                                     "linear_drag_coefficient": float(drag)}
        if spin:
            comps["minecraft:particle_initial_spin"] = {"rotation": f"math.random(0, {spin[0]})", "rotation_rate": spin[1]}
            comps["minecraft:particle_motion_dynamic"]["rotation_drag_coefficient"] = 0.0
        t = "(v.particle_age / v.particle_lifetime)"
        sx = f"{size[0]} + ({size[1] - size[0]}) * {t}"
        sy = sx if size_y is None else f"{size_y[0]} + ({size_y[1] - size_y[0]}) * {t}"
        names = sprites or [sprite]
        idx = [self.names.index(n) for n in names]
        if len(idx) == 1:
            uv = [(idx[0] % COLS) * CELL, (idx[0] // COLS) * CELL]
        else:
            sel = "v.particle_random_1 * " + str(len(idx))
            us = "".join(f"{sel} < {k + 1} ? {(i % COLS) * CELL} : (" for k, i in enumerate(idx[:-1])) + str((idx[-1] % COLS) * CELL) + ")" * (len(idx) - 1)
            vs = "".join(f"{sel} < {k + 1} ? {(i // COLS) * CELL} : (" for k, i in enumerate(idx[:-1])) + str((idx[-1] // COLS) * CELL) + ")" * (len(idx) - 1)
            uv = [us, vs]
        bb = {"size": [sx, sy], "facing_camera_mode": facing,
              "uv": {"texture_width": COLS * CELL, "texture_height": self.sheet_h, "uv": uv, "uv_size": [CELL, CELL]}}
        if stretch:
            bb["direction"] = {"mode": "derive_from_velocity", "min_speed_threshold": 0.01}
        comps["minecraft:particle_appearance_billboard"] = bb
        stops = {}
        n = len(colors)
        for i, c in enumerate(colors):
            c = c.lstrip("#")
            if len(c) == 6:
                c += "ff"
            stops[f"{i / (n - 1) if n > 1 else 0:.3f}"] = [round(int(c[k:k + 2], 16) / 255, 3) for k in (0, 2, 4, 6)]
        comps["minecraft:particle_appearance_tinting"] = {"color": {"interpolant": "v.particle_age / v.particle_lifetime",
                                                                    "gradient": stops}}
        if light:
            comps["minecraft:particle_appearance_lighting"] = {}
        if collide:
            comps["minecraft:particle_motion_collision"] = {"collision_radius": 0.05, "coefficient_of_restitution": 0.2,
                                                            "collision_drag": 4.0}
        mat = {"add": "particles_add", "blend": "particles_blend", "alpha": "particles_alpha"}[blend]
        _write(os.path.join(self.pack.rp, "particles", f"{name}.particle.json"), {
            "format_version": "1.10.0",
            "particle_effect": {
                "description": {"identifier": f"grimoire:{name}",
                                "basic_render_parameters": {"material": mat, "texture": SHEET}},
                "components": comps,
            },
        })
        return f"grimoire:{name}"
