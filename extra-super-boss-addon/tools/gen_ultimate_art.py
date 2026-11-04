#!/usr/bin/env python3
"""
ULTIMATES - each one is the boss's own historical signature (see CLAUDE.md).

  Da Vinci  "IL GRAN CAVALLO"       esb:gran_cavallo  the colossal clay horse Leonardo modelled for the Duke of Milan
                                     (1482-1499): 7.2 m, never cast in bronze, shot apart by French archers in 1499.
  Edison    "MARY HAD A LITTLE LAMB" esb:phonograph    the tinfoil phonograph (1877) - the first recorded words ever
                                     esb:sound_ring    an expanding sound-wave ring sent out on every bar of the tune

Writes models, textures, animations, animation controllers and client entities for the three props.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_model as G  # noqa: E402
import gen_model_edison as GE  # noqa: E402
from gen_model import FACE_LIGHT, hexrgb, mix, outline, smooth_noise, tile_of, vgrad  # noqa: E402
from modelkit import FaceCtx, Model  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "extra_super_boss")
BAL = json.load(open(os.path.join(ROOT, "balance.json")))
HORSE_SCALE = 1.75
PHONO_SCALE = 2.2

CLAY = hexrgb("#B3643F")
CLAY_HI = hexrgb("#CF8456")
CLAY_SH = hexrgb("#7E4127")
TINFOIL = hexrgb("#C9CDD2")


def write(rel, data):
    p = os.path.join(RP, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=1)
        f.write("\n")


# ------------------------------------------------------------------------------ painters

def p_clay(ctx: FaceCtx):
    """Sculptor's terracotta: warm clay, tool strokes along the form, fine cracks (it was never fired)."""
    h, w = ctx.h, ctx.w
    n = smooth_noise(w, h, ctx.rng, 5.0)
    base = CLAY_SH if ctx.p.get("dark") else CLAY
    rgb = np.broadcast_to(base, (h, w, 3)) * (0.88 + 0.24 * n)[..., None]
    rgb = rgb * vgrad(ctx, 1.08, 0.86)[..., None]
    rng = ctx.rng
    along_u = w >= h
    for _ in range(max(2, (w * h) // 40)):  # spatula strokes
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        L = rng.uniform(3, 8)
        dx, dy = (1, rng.uniform(-0.3, 0.3)) if along_u else (rng.uniform(-0.3, 0.3), 1)
        col = CLAY_HI if rng.random() < 0.5 else CLAY_SH
        for k in range(int(L)):
            xi, yi = int(x + dx * k), int(y + dy * k)
            if 0 <= xi < w and 0 <= yi < h:
                rgb[yi, xi] = mix(rgb[yi, xi], col, 0.45)
    for _ in range(max(1, (w * h) // 500)):  # drying cracks
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        for _ in range(int(rng.integers(4, 10))):
            xi, yi = int(x), int(y)
            if 0 <= xi < w and 0 <= yi < h:
                rgb[yi, xi] = mix(rgb[yi, xi], CLAY_SH * 0.8, 0.5)
            x += rng.uniform(-1, 1)
            y += rng.uniform(-1, 1)
    if ctx.p.get("mane") and ctx.face in ("east", "west", "up"):
        for x in range(0, w, 2):  # sculpted mane grooves
            rgb[:, x] = mix(rgb[:, x], CLAY_SH, 0.45)
    if ctx.p.get("eye") == ctx.face and w >= 8:
        cy, cx = int(h * 0.35), int(w * 0.25)
        rgb[cy:cy + 2, cx:cx + 3] = CLAY_SH * 0.55  # carved eye
        rgb[cy - 1, cx:cx + 3] = CLAY_HI
    if ctx.p.get("nostril") and ctx.face == "north" and w >= 6:
        rgb[h // 2:h // 2 + 2, 1:3] = CLAY_SH * 0.5
        rgb[h // 2:h // 2 + 2, w - 3:w - 1] = CLAY_SH * 0.5
    return tile_of(outline(rgb, 0.82) * FACE_LIGHT[ctx.face])


def p_tinfoil(ctx: FaceCtx):
    """Tinfoil wrapped on the phonograph drum, with the recorded groove spiralling around it."""
    h, w = ctx.h, ctx.w
    U, V = ctx.grid()
    rgb = mix(hexrgb("#F2F4F6"), hexrgb("#8E949C"), np.clip(np.abs(V - 0.35) * 1.6, 0, 1))
    rgb = np.broadcast_to(rgb, (h, w, 3)).copy()
    if ctx.face in ("north", "south", "up", "down"):
        for x in range(0, w, 3):
            rgb[:, x] = rgb[:, x] * 0.82  # groove
    return tile_of(outline(rgb, 0.8) * FACE_LIGHT[ctx.face])


def p_horn(ctx: FaceCtx):
    """Brass horn; the mouth (north face of the last segment) shows the dark throat with rings."""
    if ctx.p.get("mouth") and ctx.face == "north":
        h, w = ctx.h, ctx.w
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.hypot((yy - (h - 1) / 2) / (h / 2), (xx - (w - 1) / 2) / (w / 2))
        rgb = mix(hexrgb("#1A120A"), G.BRASS, np.clip(r ** 2, 0, 1))
        rings = (np.sin(r * 26) > 0.85) & (r < 0.95)
        rgb[rings] = G.BRASS_SH
        rgb[r > 0.92] = G.BRASS_HI
        return tile_of(rgb)
    return G.p_brass(ctx)


PAINTERS = dict(GE.PAINTERS)
PAINTERS.update({"clay": p_clay, "tinfoil": p_tinfoil, "horn": p_horn})


# ------------------------------------------------------------------------------ Il Gran Cavallo

def build_horse() -> Model:
    m = Model("geometry.esb.gran_cavallo")
    m.bone("root", None, (0, 0, 0))
    m.bone("body", "root", (0, 0, 13))  # pivot at the hind hooves, so it can rear
    m.cube("body", (-7, 15, -15), (14, 14, 30), "clay")  # barrel
    m.cube("body", (-7.5, 16, -21), (15, 14.5, 8), "clay")  # deep chest
    m.cube("body", (-8.25, 18, -18.5), (16.5, 9, 7), "clay")  # shoulder muscles
    m.cube("body", (-7.25, 17, 8), (14.5, 15, 11), "clay")  # rump
    m.cube("body", (-8, 18.5, 10), (16, 9.5, 8), "clay")  # haunches
    m.cube("body", (-6, 13.75, -12), (12, 2, 22), "clay", dark=True)  # belly line
    # arched neck in two pieces with a flowing mane
    m.bone("neck", "body", (0, 26, -18), (-38, 0, 0))
    m.cube("neck", (-5, 20.5, -30), (10, 11.5, 13), "clay")
    m.cube("neck", (-1.5, 31.5, -30), (3, 3.5, 13.5), "clay", mane=True)
    m.bone("neck_2", "neck", (0, 27, -29), (-18, 0, 0))
    m.cube("neck_2", (-4, 22.5, -40), (8, 9.5, 12), "clay")
    m.cube("neck_2", (-1.5, 31.5, -40), (3, 3, 12), "clay", mane=True)
    m.cube("neck_2", (-2.5, 29.5, -38), (1.5, 4, 8), "clay", mane=True, rotation=(0, 0, 18), pivot=(-1.5, 31, -34))
    m.bone("head", "neck_2", (0, 27, -39), (98, 0, 0))
    m.cube("head", (-3.75, 22, -48), (7.5, 9, 9), "clay", eye="west")  # skull and cheeks
    m.cube("head", (-4.25, 21.5, -44.5), (8.5, 6, 5), "clay")  # cheek bones
    m.cube("head", (-3, 22.5, -55), (6, 7.5, 7.5), "clay")  # tapering face
    m.cube("head", (-3.25, 21.75, -58), (6.5, 6.5, 3.5), "clay", nostril=True)  # muzzle
    m.cube("head", (-3.25, 30.5, -42), (1.75, 4.5, 1.75), "clay", rotation=(-12, 0, -8), pivot=(-2.4, 31, -41))  # ears
    m.cube("head", (1.5, 30.5, -42), (1.75, 4.5, 1.75), "clay", rotation=(-12, 0, 8), pivot=(2.4, 31, -41))
    m.cube("head", (-1.25, 30.5, -50), (2.5, 1.5, 8), "clay", mane=True)  # forelock
    m.locator("head", "loc_muzzle", (0, 24, -58))
    x = 4.75
    # front legs: forearm, knee, cannon, hoof
    m.bone("leg_f_l", "body", (x, 19, -15))
    m.cube("leg_f_l", (x - 3, 9, -18), (6, 11, 6.5), "clay")
    m.bone("shin_f_l", "leg_f_l", (x, 9, -15))
    m.cube("shin_f_l", (x - 2.25, 6.5, -16.75), (4.5, 3, 4.5), "clay")  # knee
    m.cube("shin_f_l", (x - 1.75, 2.5, -16.25), (3.5, 4.5, 3.5), "clay")
    m.cube("shin_f_l", (x - 2.5, 0, -17.25), (5, 3, 5.5), "clay", dark=True)  # hoof
    # hind legs: gaskin, hock, cannon, hoof
    m.bone("leg_h_l", "body", (x, 22, 13))
    m.cube("leg_h_l", (x - 3.5, 9, 8.5), (7, 13.5, 9.5), "clay")
    m.bone("shin_h_l", "leg_h_l", (x, 9, 14))
    m.cube("shin_h_l", (x - 2.25, 6, 13), (4.5, 3.5, 4.5), "clay")  # hock
    m.cube("shin_h_l", (x - 1.75, 2.5, 12.5), (3.5, 4.5, 3.5), "clay")
    m.cube("shin_h_l", (x - 2.5, 0, 11.75), (5, 3, 5.5), "clay", dark=True)
    m.mirror(names={"leg_f_l", "shin_f_l", "leg_h_l", "shin_h_l"})
    m.bone("tail", "body", (0, 29, 19), (32, 0, 0))
    m.cube("tail", (-2.25, 15, 17.5), (4.5, 14.5, 4), "clay", mane=True)
    m.bone("tail_2", "tail", (0, 15.5, 19.5), (18, 0, 0))
    m.cube("tail_2", (-2, 2, 17.75), (4, 14, 3.5), "clay", mane=True)
    m.locator("body", "loc_back", (0, 31, 0))
    m.locator("root", "loc_hooves", (0, 1, -14))
    return m


# ------------------------------------------------------------------------------ the tinfoil phonograph

def build_phonograph() -> Model:
    m = Model("geometry.esb.phonograph")
    m.bone("root", None, (0, 0, 0))
    m.bone("base", "root", (0, 0, 0))
    m.cube("base", (-12, 0, -7), (24, 5, 14), "wood", brass_edge=True)
    for x in (-12.5, 10.5):
        for z in (-7.5, 5.5):
            m.cube("base", (x, 0, z), (2, 2, 2), "brass")
    m.cube("base", (-11, 5, -1), (1.5, 9, 2), "brass", rivets=True)  # uprights
    m.cube("base", (9.5, 5, -1), (1.5, 9, 2), "brass", rivets=True)
    m.bone("drum", "base", (0, 11, 0))
    m.cube("drum", (-9, 8, -3), (18, 6, 6), "tinfoil")
    m.cube("drum", (-8.9, 7.75, -2.25), (17.8, 6.5, 4.5), "tinfoil", rotation=(45, 0, 0), pivot=(0, 11, 0))
    m.cube("drum", (-9.6, 8.6, -2.4), (0.6, 4.8, 4.8), "brass")
    m.cube("drum", (9.0, 8.6, -2.4), (0.6, 4.8, 4.8), "brass")
    m.bone("crank", "base", (12, 11, 0))
    m.cube("crank", (10.5, 10.5, -0.5), (3.5, 1, 1), "brass")
    m.cube("crank", (13.5, 5.5, -0.5), (1, 6, 1), "brass")
    m.cube("crank", (14.0, 5, -1), (2.5, 2, 2), "handle")
    m.locator("crank", "loc_crank", (15, 6, 0))
    # the horn: from the stylus over the drum, sweeping forward (-Z) and widening
    m.bone("horn_1", "base", (0, 15, 0))
    m.cube("horn_1", (-1, 13.5, -1), (2, 3.5, 2), "brass")  # stylus arm
    m.cube("horn_1", (-1.5, 15.5, -6), (3, 3, 6), "horn", rotation=(-22, 0, 0), pivot=(0, 17, 0))
    m.bone("horn_2", "horn_1", (0, 18, -6))
    m.cube("horn_2", (-2.5, 16.5, -12), (5, 5, 6.5), "horn", rotation=(-16, 0, 0), pivot=(0, 18, -6))
    m.bone("horn_3", "horn_2", (0, 20, -12))
    m.cube("horn_3", (-4, 16.5, -18.5), (8, 8, 7), "horn", rotation=(-12, 0, 0), pivot=(0, 20, -12))
    m.bone("horn_4", "horn_3", (0, 21.5, -18.5))
    m.cube("horn_4", (-6.5, 15.5, -25), (13, 13, 7), "horn", rotation=(-8, 0, 0), pivot=(0, 21.5, -18.5))
    m.bone("horn_5", "horn_4", (0, 22.5, -25))
    m.cube("horn_5", (-10, 13, -29), (20, 20, 4.5), "horn", mouth=True, rotation=(-4, 0, 0), pivot=(0, 22.5, -25))
    m.locator("horn_5", "loc_horn", (0, 23, -30))
    return m


# ------------------------------------------------------------------------------ the sound ring

def sound_ring():
    W, H = 32, 32
    im = np.zeros((H, W, 4), dtype=np.uint8)
    v = np.linspace(0, 1, H)[:, None]
    stripes = (np.sin(np.arange(W) * 0.9)[None, :] * 0.15 + 0.85)
    col = np.array([255, 228, 160]) * ((1 - v) ** 1.6 * stripes)[..., None]
    im[..., :3] = np.clip(col, 0, 255).astype(np.uint8)
    im[..., 3] = 255
    Image.fromarray(im, "RGBA").save(os.path.join(RP, "textures", "entity", "sound_ring.png"))
    cubes = []
    n = 24
    seg = 2 * math.pi * 16 / n + 0.4
    for i in range(n):
        a = i * 360 / n
        cubes.append({"origin": [-seg / 2, 0, -16], "size": [round(seg, 3), 9, 0], "pivot": [0, 0, 0], "rotation": [0, round(a, 2), 0],
                      "uv": {"north": {"uv": [0, 0], "uv_size": [32, 32]}, "south": {"uv": [0, 0], "uv_size": [32, 32]}}})
    write("models/entity/sound_ring.geo.json", {"format_version": "1.12.0", "minecraft:geometry": [{
        "description": {"identifier": "geometry.esb.sound_ring", "texture_width": W, "texture_height": H,
                        "visible_bounds_width": 52, "visible_bounds_height": 2, "visible_bounds_offset": [0, 0.5, 0]},
        "bones": [{"name": "root", "pivot": [0, 0, 0]}, {"name": "ring", "parent": "root", "pivot": [0, 0, 0], "cubes": cubes}]}]})


def export(model, name, tex_w, ppu, bounds):
    used = model.pack(tex_w, pad=1, ppu=ppu)
    h = 1
    while h < used:
        h *= 2
    img = model.paint(tex_w, h, PAINTERS, seed=21)
    write(f"models/entity/{name}.geo.json", model.to_json(tex_w, h, *bounds))
    Image.fromarray(img, "RGBA").save(os.path.join(RP, "textures", "entity", f"{name}.png"))
    nb, nc = model.stats()
    print(f"{name}: {nb} bones, {nc} cubes, texture {tex_w}x{h}")


# ------------------------------------------------------------------------------ animations, controllers, client entities

def k(t, v):
    return {f"{round(t, 3)}": {"post": v, "lerp_mode": "catmullrom"}}


def keys(pairs):
    out = {}
    for t, v in pairs:
        out.update(k(t, v))
    return out


def animations():
    A = {}
    H = "animation.esb.gran_cavallo."
    A[H + "rise"] = {"animation_length": 2.4, "loop": "hold_on_last_frame", "bones": {
        "root": {"position": keys([(0, [0, -44, 0]), (1.4, [0, -2, 0]), (1.6, [0, 0, 0]), (2.4, [0, 0, 0])])},
        "body": {"rotation": keys([(0, [0, 0, 0]), (1.4, [0, 0, 0]), (1.8, [-28, 0, 0]), (2.1, [-30, 0, 0]), (2.4, [0, 0, 0])])},
        "leg_f_l": {"rotation": keys([(0, [0, 0, 0]), (1.5, [0, 0, 0]), (1.8, [-70, 0, 0]), (2.1, [-50, 0, 0]), (2.4, [0, 0, 0])])},
        "leg_f_r": {"rotation": keys([(0, [0, 0, 0]), (1.5, [0, 0, 0]), (1.8, [-40, 0, 0]), (2.1, [-75, 0, 0]), (2.4, [0, 0, 0])])},
        "shin_f_l": {"rotation": keys([(0, [0, 0, 0]), (1.8, [80, 0, 0]), (2.4, [0, 0, 0])])},
        "shin_f_r": {"rotation": keys([(0, [0, 0, 0]), (1.8, [60, 0, 0]), (2.4, [0, 0, 0])])},
        "leg_h_l": {"rotation": keys([(0, [0, 0, 0]), (1.8, [30, 0, 0]), (2.4, [0, 0, 0])])},
        "leg_h_r": {"rotation": keys([(0, [0, 0, 0]), (1.8, [30, 0, 0]), (2.4, [0, 0, 0])])},
        "neck": {"rotation": keys([(0, [20, 0, 0]), (1.4, [0, 0, 0]), (1.8, [-14, 0, 0]), (2.4, [0, 0, 0])])},
        "tail": {"rotation": keys([(0, [0, 0, 0]), (1.8, [-30, 0, 0]), (2.4, [0, 0, 0])])}},
        "particle_effects": {"0.0": {"effect": "dust", "locator": "loc_hooves"}, "0.8": {"effect": "dust", "locator": "loc_hooves"},
                             "1.8": {"effect": "clay", "locator": "loc_back"}}}
    A[H + "idle"] = {"animation_length": 2.0, "loop": True, "bones": {
        "body": {"scale": [1, "1 + math.sin(q.anim_time * 180) * 0.012", 1]},
        "leg_f_l": {"rotation": [-38, 0, 0]},
        "shin_f_l": {"rotation": [72, 0, 0]},
        "neck": {"rotation": ["math.sin(q.anim_time * 180) * 3", "math.sin(q.anim_time * 90) * 6", 0]},
        "tail": {"rotation": [0, 0, "math.sin(q.anim_time * 180) * 8"]}}}
    A[H + "paw"] = {"animation_length": 0.6, "loop": True, "bones": {
        "leg_f_r": {"rotation": keys([(0, [0, 0, 0]), (0.2, [-55, 0, 0]), (0.4, [8, 0, 0]), (0.6, [0, 0, 0])])},
        "shin_f_r": {"rotation": keys([(0, [0, 0, 0]), (0.2, [70, 0, 0]), (0.4, [0, 0, 0]), (0.6, [0, 0, 0])])},
        "neck": {"rotation": keys([(0, [16, 0, 0]), (0.3, [22, 0, 0]), (0.6, [16, 0, 0])])},
        "body": {"rotation": [4, 0, 0]},
        "tail": {"rotation": keys([(0, [0, 0, 10]), (0.3, [-10, 0, -10]), (0.6, [0, 0, 10])])}},
        "particle_effects": {"0.4": {"effect": "dust", "locator": "loc_hooves"}}}
    g = "q.anim_time * 720"  # 0.5 s gallop cycle
    A[H + "gallop"] = {"animation_length": 0.5, "loop": True, "bones": {
        "root": {"position": [0, f"math.abs(math.sin({g})) * 3", 0]},
        "body": {"rotation": [f"math.sin({g}) * 7", 0, 0]},
        "leg_f_l": {"rotation": [f"math.sin({g}) * 55", 0, 0]},
        "leg_f_r": {"rotation": [f"math.sin({g} - 40) * 55", 0, 0]},
        "shin_f_l": {"rotation": [f"math.max(0, math.sin({g} - 60)) * 70", 0, 0]},
        "shin_f_r": {"rotation": [f"math.max(0, math.sin({g} - 100)) * 70", 0, 0]},
        "leg_h_l": {"rotation": [f"math.sin({g} + 160) * 45", 0, 0]},
        "leg_h_r": {"rotation": [f"math.sin({g} + 120) * 45", 0, 0]},
        "shin_h_l": {"rotation": [f"math.max(0, math.sin({g} + 100)) * -40", 0, 0]},
        "shin_h_r": {"rotation": [f"math.max(0, math.sin({g} + 60)) * -40", 0, 0]},
        "neck": {"rotation": [f"10 + math.sin({g} + 90) * 9", 0, 0]},
        "tail": {"rotation": ["-45", 0, f"math.sin({g}) * 6"]},
        "tail_2": {"rotation": ["-20", 0, 0]}},
        "particle_effects": {"0.0": {"effect": "dust", "locator": "loc_hooves"}, "0.25": {"effect": "dust", "locator": "loc_hooves"}}}
    A[H + "crumble"] = {"animation_length": 2.4, "loop": "hold_on_last_frame", "bones": {
        "body": {"rotation": keys([(0, [0, 0, 0]), (0.4, [-20, 0, 0]), (1.0, [6, 0, 8]), (2.4, [10, 0, 16])]),
                 "position": keys([(0, [0, 0, 0]), (1.0, [0, -6, 0]), (2.4, [0, -30, 0])])},
        "root": {"scale": keys([(0, [1, 1, 1]), (1.2, [1, 0.92, 1]), (2.4, [0.55, 0.2, 0.55])])},
        "neck": {"rotation": keys([(0, [0, 0, 0]), (0.5, [-12, 0, 0]), (1.4, [38, 0, 14]), (2.4, [60, 0, 20])])},
        "head": {"scale": keys([(0, [1, 1, 1]), (1.4, [1, 1, 1]), (2.0, [0.4, 0.4, 0.4])])},
        "leg_f_l": {"rotation": keys([(0, [0, 0, 0]), (1.2, [-20, 0, -30]), (2.4, [-40, 0, -60])])},
        "leg_f_r": {"rotation": keys([(0, [0, 0, 0]), (1.0, [10, 0, 26]), (2.4, [20, 0, 60])])},
        "leg_h_l": {"rotation": keys([(0, [0, 0, 0]), (1.4, [30, 0, -24]), (2.4, [60, 0, -50])])},
        "leg_h_r": {"rotation": keys([(0, [0, 0, 0]), (1.2, [24, 0, 30]), (2.4, [50, 0, 60])])},
        "tail": {"scale": keys([(0, [1, 1, 1]), (0.8, [1, 1, 1]), (1.2, [0, 0, 0])])}},
        "particle_effects": {"0.0": {"effect": "clay", "locator": "loc_back"}, "0.6": {"effect": "clay", "locator": "loc_back"},
                             "1.2": {"effect": "dust", "locator": "loc_hooves"}, "1.6": {"effect": "clay", "locator": "loc_back"}}}
    P = "animation.esb.phonograph."
    A[P + "assemble"] = {"animation_length": 1.2, "loop": "hold_on_last_frame", "bones": {
        "root": {"scale": keys([(0, [0.05, 0.05, 0.05]), (0.7, [1.08, 1.08, 1.08]), (1.0, [1, 1, 1]), (1.2, [1, 1, 1])]),
                 "rotation": keys([(0, [0, -120, 0]), (0.8, [0, 8, 0]), (1.2, [0, 0, 0])])},
        "horn_1": {"rotation": keys([(0, [60, 0, 0]), (0.9, [-6, 0, 0]), (1.2, [0, 0, 0])])}},
        "particle_effects": {"0.0": {"effect": "notes", "locator": "loc_horn"}}}
    A[P + "play"] = {"animation_length": 1.08, "loop": True, "bones": {
        "drum": {"rotation": ["q.life_time * -300", 0, 0]},
        "crank": {"rotation": ["q.life_time * -300", 0, 0]},
        "horn_5": {"scale": "1 + math.pow(math.max(0, math.sin(q.anim_time * 333.3)), 8) * 0.12"},
        "horn_4": {"rotation": ["math.sin(q.anim_time * 666.7) * 1.2", 0, 0]}},
        "particle_effects": {"0.0": {"effect": "notes", "locator": "loc_horn"}, "0.54": {"effect": "notes", "locator": "loc_horn"}}}
    A[P + "blast"] = {"animation_length": 1.0, "loop": "hold_on_last_frame", "bones": {
        "horn_5": {"scale": keys([(0, [1, 1, 1]), (0.15, [1.45, 1.45, 1.1]), (0.5, [1.1, 1.1, 1]), (1.0, [1, 1, 1])])},
        "horn_4": {"scale": keys([(0, [1, 1, 1]), (0.1, [1.2, 1.2, 1]), (0.5, [1, 1, 1])])},
        "base": {"position": keys([(0, [0, 0, 0]), (0.1, [0, 0, 3]), (0.5, [0, 0, 0])])}},
        "particle_effects": {"0.0": {"effect": "notes", "locator": "loc_horn"}}}
    A[P + "fold"] = {"animation_length": 1.0, "loop": "hold_on_last_frame", "bones": {
        "root": {"scale": keys([(0, [1, 1, 1]), (0.3, [1.06, 1.06, 1.06]), (1.0, [0.02, 0.02, 0.02])]),
                 "rotation": keys([(0, [0, 0, 0]), (1.0, [0, 140, 0])])}}}
    speed = BAL["edison"]["ultimate"]["ring_speed"]
    A["animation.esb.sound_ring.grow"] = {"animation_length": 4.0, "loop": True, "bones": {
        "root": {"scale": [f"math.max(0.05, q.life_time * {speed})", f"math.max(0.2, 1 - q.life_time * 0.22)",
                           f"math.max(0.05, q.life_time * {speed})"]}}}
    write("animations/ultimate_props.animation.json", {"format_version": "1.8.0", "animations": A})

    def state(name, prop, values, loops):
        st = {}
        for v in values:
            st[v] = {"animations": [v], "blend_transition": 0.2,
                     "transitions": [{o: f"q.property('{prop}') == '{o}'"} for o in values if o != v]}
        return {"initial_state": values[0], "states": st}
    write("animation_controllers/ultimate_props.animation_controllers.json", {"format_version": "1.10.0", "animation_controllers": {
        "controller.animation.esb.gran_cavallo.state": state("h", "esb:state", ["rise", "idle", "paw", "gallop", "crumble"], None),
        "controller.animation.esb.phonograph.state": state("p", "esb:state", ["assemble", "play", "blast", "fold"], None),
    }})


def client_entities():
    def ce(ident, geo, tex, anims, animate, parts=None, scale=None, mat="entity_emissive"):
        d = {"identifier": ident, "materials": {"default": mat}, "textures": {"default": f"textures/entity/{tex}"},
             "geometry": {"default": f"geometry.esb.{geo}"}, "render_controllers": [f"controller.render.esb.{geo}"],
             "animations": anims, "scripts": {"animate": animate}}
        if parts:
            d["particle_effects"] = parts
        if scale:
            d["scripts"]["scale"] = str(scale)
        d["scripts"]["should_update_bones_and_effects_offscreen"] = "1.0"
        write(f"entity/{ident.split(':')[1]}.entity.json", {"format_version": "1.10.0", "minecraft:client_entity": {"description": d}})
    H = "animation.esb.gran_cavallo."
    ce("esb:gran_cavallo", "gran_cavallo", "gran_cavallo",
       {n: H + n for n in ("rise", "idle", "paw", "gallop", "crumble")} | {"state": "controller.animation.esb.gran_cavallo.state"},
       ["state"], {"dust": "esb:path_dust", "clay": "esb:clay_chunks"}, HORSE_SCALE)
    P = "animation.esb.phonograph."
    ce("esb:phonograph", "phonograph", "phonograph",
       {n: P + n for n in ("assemble", "play", "blast", "fold")} | {"state": "controller.animation.esb.phonograph.state"},
       ["state"], {"notes": "esb:music_note"}, PHONO_SCALE)
    ce("esb:sound_ring", "sound_ring", "sound_ring", {"grow": "animation.esb.sound_ring.grow"}, ["grow"], mat="entity_beam_additive")


if __name__ == "__main__":
    export(build_horse(), "gran_cavallo", 512, 2, (12, 12, [0, 4, 0]))
    export(build_phonograph(), "phonograph", 256, 2, (10, 8, [0, 3, 0]))
    sound_ring()
    animations()
    client_entities()
    print("ultimate props: Il Gran Cavallo, the tinfoil phonograph, sound rings")
