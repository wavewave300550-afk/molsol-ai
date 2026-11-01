#!/usr/bin/env python3
"""Turns the raw Creator Tools `designModel` output (art/raw/) into the files the packs use.

    python3 tools/postprocess.py            # rebuild every generated texture / geometry
    python3 tools/postprocess.py --import   # first move fresh designModel output into art/raw/

What it does
  * axe geometry: binds the root bone to the hand (`q.item_slot_to_bone_name`), adds the blade
    locators used by the ember particles, pads the atlas to a power of two
  * glow: every bright-red pixel (cracks, edge, eyes, claw marks) gets a low alpha, which the
    `entity_emissive` material renders as full-bright
  * awakened axe texture (used during the Ultimate) and the translucent Grizzly Shade texture
  * the particle atlas and both pack icons
"""
import json
import math
import os
import random
import shutil
import sys

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(ROOT, "addon")
RP = os.path.join(ADDON, "resource_packs", "grizzly_oath")
BP = os.path.join(ADDON, "behavior_packs", "grizzly_oath")
RAW = os.path.join(ROOT, "art", "raw")
GLOW_ALPHA = 10  # ~96% emissive with entity_emissive


def p(*parts):
    return os.path.join(*parts)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def import_design_output():
    """Move a fresh designModel run (it writes straight into the resource pack) into art/raw."""
    moves = [
        (p(RP, "textures", "items", "grizzlys_oath.png"), p(RAW, "grizzlys_oath_model.png")),
        (p(RP, "models", "item", "grizzlys_oath.geo.json"), p(RAW, "grizzlys_oath.geo.json")),
    ]
    for src, dst in moves:
        if os.path.exists(src):
            shutil.move(src, dst)
            print("imported", os.path.relpath(src, ROOT))
    for name in ("oath_grizzly.png",):
        src = p(RP, "textures", "entity", name)
        if os.path.exists(src):
            shutil.copy(src, p(RAW, name))
    src = p(RP, "models", "entity", "oath_grizzly.geo.json")
    if os.path.exists(src):
        g = json.load(open(src))
        if "binding" not in json.dumps(g) and g["minecraft:geometry"][0]["description"]["texture_height"] != 128:
            shutil.copy(src, p(RAW, "oath_grizzly.geo.json"))


def pad_pow2(im):
    w, h = im.size
    nh = 1 << (h - 1).bit_length()
    nw = 1 << (w - 1).bit_length()
    if (nw, nh) == (w, h):
        return im
    out = Image.new("RGBA", (nw, nh), (0, 0, 0, 0))
    out.paste(im, (0, 0))
    return out


def is_glow(r, g, b):
    return r >= 170 and r >= 1.6 * g and r >= 1.6 * b


def is_hot_edge(r, g, b):
    """pale-pink highlight drawn along the axe's cutting edge"""
    return r >= 230 and g >= 150 and b >= 130 and r - b >= 40


def emissive(im, hot_edges=False):
    px = im.load()
    n = 0
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            r, g, b, a = px[x, y]
            if a and (is_glow(r, g, b) or (hot_edges and is_hot_edge(r, g, b))):
                px[x, y] = (r, g, b, GLOW_ALPHA)
                n += 1
    return n


# ----------------------------------------------------------------------------- axe

def build_axe():
    geo = json.load(open(p(RAW, "grizzlys_oath.geo.json")))
    g = geo["minecraft:geometry"][0]
    tex = pad_pow2(Image.open(p(RAW, "grizzlys_oath_model.png")).convert("RGBA"))
    g["description"]["texture_width"], g["description"]["texture_height"] = tex.size
    g["description"]["visible_bounds_width"] = 4
    g["description"]["visible_bounds_height"] = 4
    g["description"]["visible_bounds_offset"] = [0, 1, 0]
    for bone in g["bones"]:
        if bone["name"] == "grizzlys_oath":
            bone["binding"] = "q.item_slot_to_bone_name(c.item_slot)"
        if bone["name"] == "blade":
            bone["locators"] = {
                "blade_top": [0, 23, -13],
                "blade_mid": [0, 16.5, -16.5],
                "blade_low": [0, 9, -14],
            }
    write_json(p(RP, "models", "entity", "grizzlys_oath.geo.json"), geo)

    normal = tex.copy()
    n = emissive(normal)  # hot edges glow only when awakened
    os.makedirs(p(RP, "textures", "attachables"), exist_ok=True)
    normal.save(p(RP, "textures", "attachables", "grizzlys_oath.png"))

    # Awakened: steel flushed crimson, the whole head faintly glowing, edges fully emissive.
    awake = tex.copy()
    px = awake.load()
    for y in range(awake.size[1]):
        for x in range(awake.size[0]):
            r, gg, b, a = px[x, y]
            if not a:
                continue
            if is_glow(r, gg, b):
                px[x, y] = (255, min(255, gg + 70), min(255, b + 40), GLOW_ALPHA)
            elif max(r, gg, b) < 70 and max(r, gg, b) - min(r, gg, b) < 18:  # grey-black steel only
                px[x, y] = (min(255, 60 + r * 2), max(0, gg - 6), max(0, b - 6), 150)
            elif r > 200 and gg > 150:  # edge highlights
                px[x, y] = (255, 210, 190, GLOW_ALPHA)
    awake.save(p(RP, "textures", "attachables", "grizzlys_oath_awakened.png"))
    print(f"axe: {tex.size} atlas, {n} emissive pixels")


# ----------------------------------------------------------------------------- grizzly

def build_grizzly():
    geo = json.load(open(p(RAW, "oath_grizzly.geo.json")))
    g = geo["minecraft:geometry"][0]
    tex = pad_pow2(Image.open(p(RAW, "oath_grizzly.png")).convert("RGBA"))
    g["description"]["texture_width"], g["description"]["texture_height"] = tex.size
    # Visible bounds in blocks (before the 2.6x entity scale is applied it already has to cover the
    # reared-up pose), generous so the giant never gets frustum-culled mid-animation.
    g["description"]["visible_bounds_width"] = 6
    g["description"]["visible_bounds_height"] = 6
    g["description"]["visible_bounds_offset"] = [0, 2.5, 0]
    write_json(p(RP, "models", "entity", "oath_grizzly.geo.json"), geo)

    grizzly = tex.copy()
    n = emissive(grizzly)
    grizzly.save(p(RP, "textures", "entity", "oath_grizzly.png"))

    shade = tex.copy()
    px = shade.load()
    for y in range(shade.size[1]):
        for x in range(shade.size[0]):
            r, gg, b, a = px[x, y]
            if not a:
                continue
            if is_glow(r, gg, b):
                px[x, y] = (255, 40, 30, 255)
            else:
                lum = (r + gg + b) / 3
                px[x, y] = (int(18 + lum * 0.35), int(4 + lum * 0.08), int(6 + lum * 0.08), 165)
    shade.save(p(RP, "textures", "entity", "grizzly_shade.png"))
    print(f"grizzly: {tex.size} atlas, {n} emissive pixels")


# ----------------------------------------------------------------------------- particles

CELL = 32


def cell_box(cx, cy):
    return cx * CELL, cy * CELL


def soft_dot(draw_img, ox, oy, sharp=2.2):
    for y in range(CELL):
        for x in range(CELL):
            d = math.hypot(x + 0.5 - CELL / 2, y + 0.5 - CELL / 2) / (CELL / 2)
            a = max(0.0, 1 - d) ** sharp
            if a > 0.003:
                draw_img.putpixel((ox + x, oy + y), (255, 255, 255, int(255 * min(1, a * 1.25))))


def supersample(fn, size=CELL, ss=4):
    big = Image.new("L", (size * ss, size * ss), 0)
    fn(ImageDraw.Draw(big), size * ss)
    return big.resize((size, size), Image.LANCZOS)


def paste_mask(atlas, mask, ox, oy):
    white = Image.new("RGBA", mask.size, (255, 255, 255, 0))
    white.putalpha(mask)
    atlas.alpha_composite(white, (ox, oy))


def build_particles():
    atlas = Image.new("RGBA", (CELL * 4, CELL * 4), (0, 0, 0, 0))

    # (0,0) glow dot
    soft_dot(atlas, *cell_box(0, 0))

    # (1,0) crescent slash (opens to the left; particles rotate it)
    def crescent(d, s):
        c = s / 2
        d.ellipse([c - s * 0.46, c - s * 0.46, c + s * 0.46, c + s * 0.46], fill=255)
        d.ellipse([c - s * 0.52, c - s * 0.40, c + s * 0.30, c + s * 0.40], fill=0)
    m = supersample(crescent)
    paste_mask(atlas, m.filter(ImageFilter.GaussianBlur(0.6)), *cell_box(1, 0))

    # (2,0) shockwave ring
    def ring(d, s):
        c = s / 2
        d.ellipse([c - s * 0.48, c - s * 0.48, c + s * 0.48, c + s * 0.48], fill=255)
        d.ellipse([c - s * 0.40, c - s * 0.40, c + s * 0.40, c + s * 0.40], fill=60)
        d.ellipse([c - s * 0.30, c - s * 0.30, c + s * 0.30, c + s * 0.30], fill=0)
    m = supersample(ring)
    paste_mask(atlas, m.filter(ImageFilter.GaussianBlur(0.5)), *cell_box(2, 0))

    # (3,0) triple claw slash
    def claws(d, s):
        for i in range(3):
            off = (i - 1) * s * 0.17
            pts = []
            for t in [k / 20 for k in range(21)]:
                x = s * 0.30 + t * s * 0.40 + off
                y = s * 0.10 + t * s * 0.80 - off * 0.30
                w = s * 0.055 * math.sin(math.pi * t) + 1
                pts.append((x, y, w))
            for x, y, w in pts:
                d.ellipse([x - w, y - w, x + w, y + w], fill=255)
    m = supersample(claws)
    paste_mask(atlas, m.filter(ImageFilter.GaussianBlur(0.4)), *cell_box(3, 0))

    # (0,1) streak (long axis = texture Y)
    def streak(d, s):
        for k in range(60):
            t = k / 59
            y = s * 0.04 + t * s * 0.92
            w = s * 0.16 * math.sin(math.pi * t) ** 0.8 + 0.5
            d.ellipse([s / 2 - w, y - w * 0.6, s / 2 + w, y + w * 0.6], fill=255)
    m = supersample(streak)
    paste_mask(atlas, m.filter(ImageFilter.GaussianBlur(1.0)), *cell_box(0, 1))

    # (1,1) smoke puff
    rnd = random.Random(9)
    def smoke(d, s):
        for _ in range(14):
            r = s * rnd.uniform(0.12, 0.24)
            x = s / 2 + rnd.uniform(-0.18, 0.18) * s
            y = s / 2 + rnd.uniform(-0.18, 0.18) * s
            d.ellipse([x - r, y - r, x + r, y + r], fill=rnd.randint(120, 220))
    m = supersample(smoke).filter(ImageFilter.GaussianBlur(1.4))
    paste_mask(atlas, m, *cell_box(1, 1))

    # (2,1) blood drop
    def drop(d, s):
        d.ellipse([s * 0.32, s * 0.42, s * 0.68, s * 0.80], fill=255)
        d.polygon([(s * 0.5, s * 0.12), (s * 0.34, s * 0.55), (s * 0.66, s * 0.55)], fill=255)
    paste_mask(atlas, supersample(drop), *cell_box(2, 1))

    # (3,1) shard
    def shard(d, s):
        d.polygon([(s * 0.50, s * 0.08), (s * 0.80, s * 0.55), (s * 0.55, s * 0.92), (s * 0.22, s * 0.60)], fill=255)
    paste_mask(atlas, supersample(shard), *cell_box(3, 1))

    os.makedirs(p(RP, "textures", "particle"), exist_ok=True)
    atlas.save(p(RP, "textures", "particle", "grizzly_oath_fx.png"))
    print("particles: atlas", atlas.size)


# ----------------------------------------------------------------------------- particle definitions

T = "(v.particle_age / v.particle_lifetime)"
COLOR = ["(v.color.r ?? 1)", "(v.color.g ?? 0.15)", "(v.color.b ?? 0.1)"]


def uv(cx, cy):
    return {"texture_width": 128, "texture_height": 128, "uv": [cx * CELL, cy * CELL], "uv_size": [CELL, CELL]}


def particle(name, comps, material="particles_blend"):
    return name, {
        "format_version": "1.10.0",
        "particle_effect": {
            "description": {
                "identifier": f"grizzly_oath:{name}",
                "basic_render_parameters": {"material": material, "texture": "textures/particle/grizzly_oath_fx"},
            },
            "components": comps,
        },
    }


def instant(n=1):
    return {"minecraft:emitter_lifetime_once": {}, "minecraft:emitter_rate_instant": {"num_particles": n}}


def billboard(size, cell, mode="lookat_xyz", direction=None):
    b = {"size": size if isinstance(size, list) else [size, size], "facing_camera_mode": mode, "uv": uv(*cell)}
    if direction is not None:
        b["direction"] = {"mode": "custom", "custom_direction": direction}
    return {"minecraft:particle_appearance_billboard": b}


def fade(alpha="(v.color.a ?? 1)", power=1):
    a = f"{alpha} * (1 - {T})" if power == 1 else f"{alpha} * (1 - {T} * {T})"
    return {"minecraft:particle_appearance_tinting": {"color": COLOR + [a]}}


def build_particle_defs():
    defs = [
        # hit / blade sparks: a short burst of hot red sparks with gravity
        particle("spark", {
            **instant(7),
            "minecraft:emitter_shape_sphere": {"radius": 0.15, "direction": "outwards"},
            "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.2, 0.4)"},
            "minecraft:particle_initial_speed": "math.random(3, 7)",
            "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -10, 0], "linear_drag_coefficient": 3.5},
            **billboard(f"0.075 * (1 - {T}) + 0.02", (0, 0)),
            "minecraft:particle_appearance_tinting": {"color": [1, f"0.75 - 0.55 * {T}", f"0.45 - 0.4 * {T}", 1]},
        }),
        # generic configurable glow point (v.size, v.life, v.rise, v.color)
        particle("glow", {
            **instant(1),
            "minecraft:emitter_shape_point": {},
            "minecraft:particle_lifetime_expression": {"max_lifetime": "(v.life ?? 0.3)"},
            "minecraft:particle_initial_speed": 0,
            "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, "(v.rise ?? 0)", 0]},
            **billboard(f"(v.size ?? 0.2) * (1 - 0.5 * {T})", (0, 0)),
            **fade(),
        }),
        # crescent slash flash (v.size, v.rot, v.color)
        particle("slash", {
            **instant(1),
            "minecraft:emitter_shape_point": {},
            "minecraft:particle_lifetime_expression": {"max_lifetime": 0.22},
            "minecraft:particle_initial_spin": {"rotation": "(v.rot ?? 0)", "rotation_rate": 0},
            **billboard(f"(v.size ?? 1) * (0.85 + 0.3 * {T})", (1, 0)),
            **fade(power=2),
        }),
        # three-claw flash in front of the player (Grizzly Rend)
        particle("claw_flash", {
            **instant(1),
            "minecraft:emitter_shape_point": {},
            "minecraft:particle_lifetime_expression": {"max_lifetime": 0.32},
            "minecraft:particle_initial_spin": {"rotation": "(v.rot ?? 0)", "rotation_rate": 0},
            **billboard(f"(v.size ?? 1.5) * (0.8 + 0.4 * {T})", (3, 0)),
            **fade(power=2),
        }),
        # energy claw streak, long axis along v.dir
        particle("claw_streak", {
            **instant(1),
            "minecraft:emitter_shape_point": {},
            "minecraft:particle_lifetime_expression": {"max_lifetime": "(v.life ?? 0.5)"},
            **billboard([0.28, 1.2], (0, 1), "direction_y", ["(v.dir.x ?? 0)", "(v.dir.y ?? 0)", "(v.dir.z ?? 1)"]),
            **fade(),
        }),
        # flat ground shockwave ring that grows to v.radius over v.life
        particle("ring", {
            **instant(1),
            "minecraft:emitter_shape_point": {},
            "minecraft:particle_lifetime_expression": {"max_lifetime": "(v.life ?? 0.4)"},
            **billboard(f"(v.radius ?? 4) * math.min(1, {T} * 1.6) + 0.2", (2, 0), "direction_y", [0, 0, 1]),
            **fade(),
        }),
        # smoke puff (dark aura / dash trail / summon)
        particle("smoke", {
            **instant(1),
            "minecraft:emitter_shape_sphere": {"radius": 0.1, "direction": "outwards"},
            "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.7, 1.1)"},
            "minecraft:particle_initial_speed": "math.random(0.2, 0.6)",
            "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.8, 0], "linear_drag_coefficient": 1.5},
            "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-40, 40)"},
            **billboard(f"(v.size ?? 0.5) * (0.6 + 0.6 * {T})", (1, 1)),
            **fade(),
        }),
        # rising red embers (aura, charge-up)
        particle("ember", {
            **instant(1),
            "minecraft:emitter_shape_point": {"direction": ["math.random(-0.3, 0.3)", 1, "math.random(-0.3, 0.3)"]},
            "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.6, 1.0)"},
            "minecraft:particle_initial_speed": "math.random(0.6, 1.4)",
            "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.6, 0], "linear_drag_coefficient": 0.8},
            **billboard(f"0.06 * (1 - {T}) + 0.02", (0, 0)),
            "minecraft:particle_appearance_tinting": {"color": [1, f"0.35 - 0.25 * {T}", 0.15, f"1 - {T} * {T}"]},
        }),
        # bleeding drops
        particle("blood", {
            **instant(2),
            "minecraft:emitter_shape_sphere": {"radius": 0.2, "direction": "outwards"},
            "minecraft:particle_lifetime_expression": {"max_lifetime": 0.6},
            "minecraft:particle_initial_speed": "math.random(0.5, 1.5)",
            "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -12, 0]},
            **billboard([0.06, 0.08], (2, 1)),
            "minecraft:particle_appearance_tinting": {"color": [0.65, 0.02, 0.03, 1]},
        }),
        # ground debris for slams (purely visual, blocks are never touched)
        particle("shard", {
            **instant(10),
            "minecraft:emitter_shape_point": {"direction": ["math.random(-1, 1)", "math.random(0.8, 1.6)", "math.random(-1, 1)"]},
            "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.6, 0.9)"},
            "minecraft:particle_initial_speed": "math.random(4, 8)",
            "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -22, 0], "linear_drag_coefficient": 0.5},
            "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-360, 360)"},
            **billboard(0.12, (3, 1)),
            "minecraft:particle_appearance_tinting": {"color": ["0.18 + 0.3 * v.particle_random_1", 0.05, 0.05, f"1 - {T} * {T}"]},
        }),
        # embers that drift off the blade of the held axe (attachable locators)
        particle("blade_ember", {
            **instant(2),
            "minecraft:emitter_shape_sphere": {"radius": 0.12, "direction": "outwards"},
            "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.35, 0.6)"},
            "minecraft:particle_initial_speed": "math.random(0.2, 0.6)",
            "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 1.2, 0]},
            **billboard(f"0.035 * (1 - {T}) + 0.012", (0, 0)),
            "minecraft:particle_appearance_tinting": {"color": [1, f"0.3 - 0.2 * {T}", 0.12, f"1 - {T}"]},
        }),
        # crimson flames licking off the awakened axe during the Ultimate
        particle("awakened_flame", {
            **instant(4),
            "minecraft:emitter_shape_sphere": {"radius": 0.2, "direction": "outwards"},
            "minecraft:particle_lifetime_expression": {"max_lifetime": "math.random(0.3, 0.55)"},
            "minecraft:particle_initial_speed": "math.random(0.4, 1.0)",
            "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 2.4, 0]},
            **billboard(f"0.09 * (1 - {T}) + 0.02", (0, 0)),
            "minecraft:particle_appearance_tinting": {"color": [1, f"0.45 - 0.35 * {T}", f"0.2 - 0.15 * {T}", f"1 - {T}"]},
        }),
    ]
    out = p(RP, "particles")
    os.makedirs(out, exist_ok=True)
    for name, data in defs:
        write_json(p(out, f"{name}.json"), data)
    print(f"particles: {len(defs)} definitions")


# ----------------------------------------------------------------------------- pack icons

def build_pack_icons():
    S = 256
    bg = Image.new("RGBA", (S, S), (0, 0, 0, 255))
    px = bg.load()
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - S * 0.55, y - S * 0.42) / S
            t = max(0.0, 1 - d * 1.6)
            px[x, y] = (int(12 + 120 * t ** 2), int(6 + 8 * t), int(8 + 8 * t), 255)
    icon = Image.open(p(RP, "textures", "items", "grizzlys_oath_icon.png")).convert("RGBA")
    big = icon.resize((S - 24, S - 24), Image.NEAREST)
    glow = Image.new("RGBA", big.size, (255, 30, 20, 0))
    glow.putalpha(big.split()[3].filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.8)))
    bg.alpha_composite(glow, (12, 16))
    bg.alpha_composite(big, (12, 12))
    d = ImageDraw.Draw(bg)
    d.rectangle([0, 0, S - 1, S - 1], outline=(150, 20, 24, 255), width=6)
    d.text((14, S - 30), "001", fill=(255, 210, 190, 255))
    for target in (p(RP, "pack_icon.png"), p(BP, "pack_icon.png")):
        bg.convert("RGB").save(target)
    print("pack icons written")


if __name__ == "__main__":
    if "--import" in sys.argv:
        import_design_output()
    build_axe()
    build_grizzly()
    build_particles()
    build_particle_defs()
    build_pack_icons()
