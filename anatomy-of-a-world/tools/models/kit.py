"""
kit.py - procedural Bedrock entity model toolkit for THE ANATOMY OF A WORLD.

A model is a tree of bones made of cubes. Every cube face references a
*material* (a procedural painter) and a texel density. The kit:

  * allocates a texture region for every visible face (per-face UV, packed into
    a power-of-two atlas),
  * paints the atlas with the materials (alpha < 255 marks emissive texels for
    the `entity_emissive_alpha` material),
  * writes Bedrock geometry JSON (format 1.16.0),
  * bakes keyframe animations written as Python functions of time into Bedrock
    animation JSON, and exports sample poses for the three.js previewer.

Units: 1/16 block. Model faces -Z (north) = the creature's front.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

FACES = ("north", "south", "east", "west", "up", "down")
RGBA = Tuple[int, int, int, int]


def hx(s: str) -> np.ndarray:
    s = s.lstrip("#")
    return np.array([int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)], dtype=np.float32)


# ----------------------------------------------------------------------------- noise helpers
def value_noise(w: int, h: int, scale: float, seed: int, octaves: int = 3) -> np.ndarray:
    """Tileable-ish smooth value noise in [0,1], shape (h, w)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), dtype=np.float32)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        cell = max(1.0, scale / (2 ** o))
        gw = int(math.ceil(w / cell)) + 2
        gh = int(math.ceil(h / cell)) + 2
        grid = rng.random((gh, gw)).astype(np.float32)
        ys = np.arange(h) / cell
        xs = np.arange(w) / cell
        y0 = np.floor(ys).astype(int)
        x0 = np.floor(xs).astype(int)
        ty = (ys - y0)[:, None]
        tx = (xs - x0)[None, :]
        ty = ty * ty * (3 - 2 * ty)
        tx = tx * tx * (3 - 2 * tx)
        a = grid[np.ix_(y0, x0)]
        b = grid[np.ix_(y0, x0 + 1)]
        c = grid[np.ix_(y0 + 1, x0)]
        d = grid[np.ix_(y0 + 1, x0 + 1)]
        out += amp * ((a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty)
        norm += amp
        amp *= 0.5
    return out / norm


@dataclass
class FaceInfo:
    """What a painter knows about the face it paints."""
    face: str
    w: int  # texels
    h: int
    size_units: Tuple[float, float]  # face size in model units (u, v)
    origin: Tuple[float, float, float]  # cube origin (model units)
    cube_size: Tuple[float, float, float]
    seed: int
    tag: str = ""


Painter = Callable[[FaceInfo], np.ndarray]  # returns (h, w, 4) uint8


# ----------------------------------------------------------------------------- materials
def _rgba(rgb: np.ndarray, alpha: np.ndarray | float = 255) -> np.ndarray:
    h, w = rgb.shape[:2]
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8) if not np.isscalar(alpha) else int(alpha)
    return out


def _quantize(rgb: np.ndarray, levels: int = 10) -> np.ndarray:
    """Posterise a little so procedural noise reads as Minecraft pixel art."""
    lum = rgb.mean(axis=2, keepdims=True)
    q = np.round(lum / 255 * levels) / levels * 255
    return rgb * (0.55 + 0.45 * (q / np.maximum(lum, 1)))


def m_rock(base="#7d7d7d", dark="#5b5c5e", light="#a9a9a6", band_period=10.0, moss: float = 0.0, mossc="#5d7a35") -> Painter:
    b, d, l, mc = hx(base), hx(dark), hx(light), hx(mossc)

    def paint(f: FaceInfo) -> np.ndarray:
        h, w = f.h, f.w
        n = value_noise(w, h, 2.5, f.seed, 2)
        n2 = value_noise(w, h, 6, f.seed + 7, 2)
        rgb = b[None, None, :] * (0.82 + 0.36 * n[..., None])
        # strata bands along the face's vertical axis (or along u for up/down)
        if f.face in ("up", "down"):
            coord = np.arange(w)[None, :].repeat(h, 0) * f.size_units[0] / max(1, w)
        else:
            coord = (np.arange(h)[:, None].repeat(w, 1) / max(1, h)) * f.size_units[1]
            coord = f.origin[1] + f.cube_size[1] - coord
        wav = coord / 16 * 16 / band_period + n2 * 0.6
        band = np.floor(wav).astype(int) % 5
        rgb = np.where((band == 1)[..., None], d * (0.85 + 0.3 * n[..., None]), rgb)
        rgb = np.where((band == 3)[..., None], l * (0.85 + 0.2 * n[..., None]), rgb)
        # crack lines
        rnd = np.random.default_rng(f.seed + 3)
        for _ in range(max(1, (w * h) // 220)):
            x, y = rnd.integers(0, w), rnd.integers(0, h)
            for _k in range(rnd.integers(2, 6)):
                if 0 <= x < w and 0 <= y < h:
                    rgb[y, x] = d * 0.7
                x += rnd.integers(-1, 2)
                y += 1
        if moss > 0 and f.face != "down":
            mm = value_noise(w, h, 3.5, f.seed + 11, 2)
            thr = 1 - moss
            if f.face == "up":
                thr = 1 - moss * 1.8
            rgb = np.where((mm > thr)[..., None], mc * (0.8 + 0.4 * n[..., None]), rgb)
        return _rgba(_quantize(rgb))
    return paint


def m_muscle(base="#6e2328", dark="#3f1216", light="#9a3a3a", axis="v", glow_veins: float = 0.0, vein="#ff7a2a") -> Painter:
    """Lithic musculature: fibrous red-maroon with striations along an axis."""
    b, d, l, vc = hx(base), hx(dark), hx(light), hx(vein)

    def paint(f: FaceInfo) -> np.ndarray:
        h, w = f.h, f.w
        n = value_noise(w, h, 2.0, f.seed, 2)
        rgb = b[None, None, :] * (0.8 + 0.4 * n[..., None])
        along_u = (axis == "u") ^ (f.face in ("up", "down") and axis == "v")
        idx = np.arange(w)[None, :].repeat(h, 0) if not along_u else np.arange(h)[:, None].repeat(w, 1)
        jitter = (value_noise(w, h, 4, f.seed + 2, 1) * 3).astype(int)
        stripe = (idx + jitter) % 3
        rgb = np.where((stripe == 0)[..., None], d * (0.85 + 0.3 * n[..., None]), rgb)
        rgb = np.where(((stripe == 2) & (n > 0.6))[..., None], l, rgb)
        alpha = np.full((h, w), 255.0)
        if glow_veins > 0:
            # branching vein lines (1 texel wide) with a darker groove on one side
            rnd = np.random.default_rng(f.seed + 9)
            count = max(1, int(round((w * h) / 900 * glow_veins)))
            for _ in range(count):
                x = float(rnd.integers(0, w))
                y = float(rnd.integers(0, h))
                ang = rnd.uniform(0, math.pi * 2)
                for _step in range(int(rnd.integers(8, 26))):
                    ix, iy = int(x), int(y)
                    if 0 <= ix < w and 0 <= iy < h:
                        rgb[iy, ix] = vc
                        alpha[iy, ix] = 70
                        if iy + 1 < h:
                            rgb[iy + 1, ix] = d * 0.6
                    ang += rnd.uniform(-0.6, 0.6)
                    x += math.cos(ang)
                    y += math.sin(ang)
                    if rnd.random() < 0.06:
                        ang += rnd.choice([-1.2, 1.2])
        return _rgba(_quantize(rgb), alpha)
    return paint


def m_glow(color="#ff6a1a", core="#ffd27a", alpha=40) -> Painter:
    c, k = hx(color), hx(core)

    def paint(f: FaceInfo) -> np.ndarray:
        h, w = f.h, f.w
        n = value_noise(w, h, 1.6, f.seed, 2)
        rgb = c[None, None, :] * (0.8 + 0.3 * n[..., None])
        rgb = np.where((n > 0.62)[..., None], k, rgb)
        return _rgba(rgb, alpha + (1 - n) * 30)
    return paint


def m_crystal(base="#8b5cd6", dark="#4a2a8a", light="#e2c8ff", alpha=150, facet_seed=0) -> Painter:
    b, d, l = hx(base), hx(dark), hx(light)

    def paint(f: FaceInfo) -> np.ndarray:
        h, w = f.h, f.w
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        t = (xx / max(1, w - 1) + yy / max(1, h - 1)) * 0.5
        rgb = d[None, None, :] * (1 - t[..., None]) + b[None, None, :] * t[..., None]
        # facet highlight diagonal + sparkle texels
        diag = np.abs((xx / max(1, w)) - (yy / max(1, h))) < 0.08
        rgb = np.where(diag[..., None], l, rgb)
        rnd = np.random.default_rng(f.seed + facet_seed)
        sp = rnd.random((h, w)) > 0.93
        rgb = np.where(sp[..., None], l, rgb)
        edge = (xx == 0) | (yy == 0)
        rgb = np.where(edge[..., None], l * 0.9, rgb)
        a = np.full((h, w), float(alpha))
        a = np.where(diag | sp, alpha * 0.4, a)
        return _rgba(rgb, a)
    return paint


def m_grass_top(base="#5f9a3a", dark="#3f6e2a", light="#8cc157") -> Painter:
    b, d, l = hx(base), hx(dark), hx(light)

    def paint(f: FaceInfo) -> np.ndarray:
        h, w = f.h, f.w
        n = value_noise(w, h, 1.5, f.seed, 2)
        rgb = b[None, None, :] * (0.85 + 0.3 * n[..., None])
        rgb = np.where((n < 0.3)[..., None], d, rgb)
        rgb = np.where((n > 0.75)[..., None], l, rgb)
        return _rgba(rgb)
    return paint


def m_grass_side(rock: Painter, grass="#5f9a3a", fringe_px: int = 2) -> Painter:
    g = hx(grass)

    def paint(f: FaceInfo) -> np.ndarray:
        img = rock(f).copy()
        h, w = f.h, f.w
        rnd = np.random.default_rng(f.seed + 5)
        for x in range(w):
            depth = fringe_px + int(rnd.integers(0, 2))
            img[: min(h, depth), x, :3] = np.clip(g * (0.85 + 0.3 * rnd.random()), 0, 255)
        return img
    return paint


def m_leaves(base="#3e6b30", dark="#28471f", light="#5d8f43") -> Painter:
    b, d, l = hx(base), hx(dark), hx(light)

    def paint(f: FaceInfo) -> np.ndarray:
        h, w = f.h, f.w
        rnd = np.random.default_rng(f.seed)
        r = rnd.random((h, w))
        rgb = np.where((r < 0.3)[..., None], d, np.where((r > 0.8)[..., None], l, b)).astype(np.float32)
        return _rgba(rgb)
    return paint


def m_solid(color: str, alpha: int = 255, var: float = 0.08) -> Painter:
    c = hx(color)

    def paint(f: FaceInfo) -> np.ndarray:
        n = value_noise(f.w, f.h, 1.5, f.seed, 1)
        rgb = c[None, None, :] * (1 - var + 2 * var * n[..., None])
        return _rgba(rgb, alpha)
    return paint


# ----------------------------------------------------------------------------- geometry
@dataclass
class Cube:
    origin: Tuple[float, float, float]
    size: Tuple[float, float, float]
    mats: Dict[str, Painter]
    density: float
    rotation: Optional[Tuple[float, float, float]] = None
    pivot: Optional[Tuple[float, float, float]] = None
    inflate: float = 0.0
    tag: str = ""
    uv: Dict[str, dict] = field(default_factory=dict)


@dataclass
class Bone:
    name: str
    pivot: Tuple[float, float, float]
    parent: Optional[str] = None
    rotation: Optional[Tuple[float, float, float]] = None
    cubes: List[Cube] = field(default_factory=list)
    locators: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)

    def cube(self, origin, size, mat, density: float = 0.5, rotation=None, pivot=None, inflate=0.0, faces: Optional[Dict[str, Painter]] = None, skip: Sequence[str] = (), tag: str = "") -> Cube:
        mats = {f: mat for f in FACES if f not in skip}
        if faces:
            mats.update(faces)
        c = Cube(tuple(float(v) for v in origin), tuple(float(v) for v in size), mats, density,
                 tuple(float(v) for v in rotation) if rotation else None,
                 tuple(float(v) for v in pivot) if pivot else None, inflate, tag)
        self.cubes.append(c)
        return c


class Model:
    def __init__(self, identifier: str, seed: int = 1, visible_bounds=(8, 8, (0, 2, 0))):
        self.identifier = identifier
        self.bones: List[Bone] = []
        self.seed = seed
        self.visible_bounds = visible_bounds
        self.tex_w = 0
        self.tex_h = 0
        self.atlas: Optional[Image.Image] = None

    def bone(self, name, pivot=(0, 0, 0), parent=None, rotation=None) -> Bone:
        b = Bone(name, tuple(float(v) for v in pivot), parent, tuple(float(v) for v in rotation) if rotation else None)
        self.bones.append(b)
        return b

    def get(self, name: str) -> Bone:
        for b in self.bones:
            if b.name == name:
                return b
        raise KeyError(name)

    # -- packing ---------------------------------------------------------------------------
    @staticmethod
    def _face_dims(face: str, size) -> Tuple[float, float]:
        sx, sy, sz = size
        return {"north": (sx, sy), "south": (sx, sy), "east": (sz, sy), "west": (sz, sy), "up": (sx, sz), "down": (sx, sz)}[face]

    def build(self, max_size: int = 2048) -> None:
        regions = []
        k = 0
        for b in self.bones:
            for c in b.cubes:
                for face, mat in c.mats.items():
                    fu, fv = self._face_dims(face, c.size)
                    w = max(1, int(round(fu * c.density)))
                    h = max(1, int(round(fv * c.density)))
                    regions.append((h, w, b, c, face, mat, k))
                    k += 1
        # shelf packing, tallest first
        regions.sort(key=lambda r: (-r[0], -r[1]))
        for width in (64, 128, 256, 512, 1024, 2048):
            if width > max_size:
                break
            placed = []
            x = y = shelf_h = 0
            ok = True
            for r in regions:
                h, w = r[0], r[1]
                if w > width:
                    ok = False
                    break
                if x + w > width:
                    x = 0
                    y += shelf_h
                    shelf_h = 0
                placed.append((x, y, r))
                x += w
                shelf_h = max(shelf_h, h)
            total_h = y + shelf_h
            if ok and total_h <= width * 2:
                height = 1
                while height < total_h:
                    height *= 2
                self._paint(width, height, placed)
                return
        raise RuntimeError(f"{self.identifier}: texture too large")

    def _paint(self, width: int, height: int, placed) -> None:
        img = np.zeros((height, width, 4), dtype=np.uint8)
        for x, y, (h, w, b, c, face, mat, k) in placed:
            fu, fv = self._face_dims(face, c.size)
            info = FaceInfo(face, w, h, (fu, fv), c.origin, c.size, self.seed * 1000 + k, c.tag)
            tile = mat(info)
            img[y:y + h, x:x + w] = tile[:h, :w]
            c.uv[face] = {"uv": [x, y], "uv_size": [w, h]}
            if face in ("up", "down"):
                # Bedrock samples up/down faces flipped; give them the region as-is (orientation agnostic paint)
                pass
        self.tex_w, self.tex_h = width, height
        self.atlas = Image.fromarray(img, "RGBA")

    # -- export ----------------------------------------------------------------------------
    def geometry_json(self) -> dict:
        vb_w, vb_h, vb_off = self.visible_bounds
        bones = []
        for b in self.bones:
            jb = {"name": b.name, "pivot": [round(v, 4) for v in b.pivot]}
            if b.parent:
                jb["parent"] = b.parent
            if b.rotation:
                jb["rotation"] = [round(v, 4) for v in b.rotation]
            cubes = []
            for c in b.cubes:
                jc = {"origin": [round(v, 4) for v in c.origin], "size": [round(v, 4) for v in c.size], "uv": c.uv}
                if c.rotation:
                    jc["rotation"] = [round(v, 4) for v in c.rotation]
                    jc["pivot"] = [round(v, 4) for v in (c.pivot or b.pivot)]
                if c.inflate:
                    jc["inflate"] = c.inflate
                cubes.append(jc)
            if cubes:
                jb["cubes"] = cubes
            if b.locators:
                jb["locators"] = {k: [round(v, 4) for v in pos] for k, pos in b.locators.items()}
            bones.append(jb)
        return {
            "format_version": "1.16.0",
            "minecraft:geometry": [{
                "description": {
                    "identifier": self.identifier,
                    "texture_width": self.tex_w,
                    "texture_height": self.tex_h,
                    "visible_bounds_width": vb_w,
                    "visible_bounds_height": vb_h,
                    "visible_bounds_offset": list(vb_off),
                },
                "bones": bones,
            }],
        }

    def stats(self) -> str:
        n = sum(len(b.cubes) for b in self.bones)
        return f"{self.identifier}: {len(self.bones)} bones, {n} cubes, texture {self.tex_w}x{self.tex_h}"


# ----------------------------------------------------------------------------- animation baking
Pose = Dict[str, Dict[str, Sequence[float]]]


def bake_animation(name: str, fn: Callable[[float], Pose], length: float, loop: bool | str = True, fps: float = 10.0,
                   bones: Optional[Sequence[str]] = None, extra: Optional[dict] = None) -> dict:
    """Sample fn(t) -> {bone: {rotation:[..], position:[..], scale:[..]}} into keyframes."""
    n = max(2, int(round(length * fps)) + 1)
    times = [round(length * i / (n - 1), 4) for i in range(n)]
    tracks: Dict[str, Dict[str, Dict[str, List[float]]]] = {}
    for t in times:
        pose = fn(t)
        for bone, ch in pose.items():
            if bones is not None and bone not in bones:
                continue
            for chan, val in ch.items():
                tracks.setdefault(bone, {}).setdefault(chan, {})[f"{t:.4f}".rstrip("0").rstrip(".") if t else "0.0"] = [round(float(v), 3) for v in val]
    # drop constant channels to keep files small
    out_bones = {}
    for bone, chans in tracks.items():
        ob = {}
        for chan, keys in chans.items():
            vals = list(keys.values())
            if all(v == vals[0] for v in vals):
                if (chan == "scale" and vals[0] == [1, 1, 1]) or (chan != "scale" and vals[0] == [0, 0, 0]):
                    continue
                ob[chan] = vals[0]
            else:
                ob[chan] = keys
        if ob:
            out_bones[bone] = ob
    anim = {"animation_length": length, "bones": out_bones}
    if loop is True:
        anim["loop"] = True
    elif loop == "hold_on_last_frame":
        anim["loop"] = "hold_on_last_frame"
    if extra:
        anim.update(extra)
    return {name: anim}


def write_json(path: str, data: dict) -> None:
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1)


# ----------------------------------------------------------------------------- easing helpers
def ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_out_back(t: float, s: float = 1.6) -> float:
    t = max(0.0, min(1.0, t)) - 1
    return t * t * ((s + 1) * t + s) + 1


def ease_in(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * t


def seg(t: float, a: float, b: float) -> float:
    """0..1 progress of t across [a, b]."""
    if b <= a:
        return 1.0 if t >= b else 0.0
    return max(0.0, min(1.0, (t - a) / (b - a)))
