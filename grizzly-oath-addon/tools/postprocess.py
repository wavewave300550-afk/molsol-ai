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
            if a and is_glow(r, g, b):
                # vivid crimson: the designModel crack overlay is blended toward the dark steel
                px[x, y] = (255, min(110, int(g * 1.5) + 18), min(90, int(b * 1.3) + 12), GLOW_ALPHA)
                n += 1
            elif a and hot_edges and is_hot_edge(r, g, b):
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
    geo["format_version"] = "1.16.0"  # bone "binding" needs geometry format 1.16.0+ (as vanilla trident)
    for bone in g["bones"]:
        if bone["name"] == "grizzlys_oath":
            bone["binding"] = "q.item_slot_to_bone_name(c.item_slot)"
            bone["pivot"] = [0, -1, 0]  # the hand grips the leather wrap here
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
    geo["format_version"] = "1.16.0"
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

def build_fx():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fx_assets

    fx_assets.build_atlas(p(RP, "textures", "particle", "grizzly_oath_fx.png"))
    n = fx_assets.write_defs(p(RP, "particles"))
    print(f"particles: 256x256 atlas, {n} definitions")


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
    build_fx()
    build_pack_icons()
