"""Cross-check geometry conventions against Minecraft Creator Tools' renderer.

Builds a small asymmetric test model (coloured faces, a nose on the front, a
marker on the creature's right side, a gradient on the front face and two
rotated arms), renders it with our software renderer and with `mct render
model`, and writes both side by side so the conventions in geo.py can be
confirmed visually.

usage: python3 tools/check_conventions.py <out_dir>
"""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit.geo import Model  # noqa: E402
from kit.tex import paint, hx  # noqa: E402
from kit.render import render, sheet  # noqa: E402

FACE_COL = {"north": "#e03030", "south": "#3050e0", "east": "#30c040", "west": "#e0d030",
            "up": "#f4f4f4", "down": "#202020"}


def mat_faces(ctx):
    base = hx(FACE_COL[ctx.face])
    rgb = np.broadcast_to(base, (ctx.N, 3)).copy()
    # gradient along u (dark at u=0) and a dot near v=0 (top-left corner)
    k = 0.45 + 0.55 * (ctx.s / max(ctx.fw, 1e-6))
    rgb = rgb * k[:, None]
    tl = (ctx.s < ctx.fw * 0.25) & (ctx.t < ctx.fh * 0.25)
    rgb[tl] = [0, 0, 0]
    return rgb, ctx.ones(), ctx.zeros()


def mat_plain(col):
    def m(ctx):
        return np.broadcast_to(hx(col), (ctx.N, 3)), ctx.ones(), ctx.zeros()
    return m


def build():
    m = Model("conv", ppu=4, atlas_width=256)
    m.bone("root", None, (0, 0, 0))
    m.bone("body", "root", (0, 16, 0))
    m.box("body", (0, 8, 0), (8, 16, 4), "faces")
    m.bone("head", "body", (0, 16, 0))
    m.box("head", (0, 20, 0), (8, 8, 8), "faces")
    m.box("head", (0, 19, -5), (2, 2, 2), "nose")          # front (-Z)
    m.box("head", (-5, 22, 0), (2, 2, 2), "rightmark")     # creature's right (-X)
    m.bone("rightArm", "body", (-5, 15, 0), rot=(-90, 0, 0))  # should point forward
    m.box("rightArm", (-5, 9, 0), (2, 12, 2), "rarm")
    m.bone("leftArm", "body", (5, 15, 0), rot=(0, 0, 45))    # rz>0: left arm swings inward/up?
    m.box("leftArm", (5, 9, 0), (2, 12, 2), "larm")
    m.bone("tilt", "body", (0, 26, 0), rot=(0, 45, 0))      # ry>0 should turn to creature's right
    m.box("tilt", (0, 27, -4), (1, 1, 8), "rightmark")
    m.pack()
    mats = {"faces": mat_faces, "nose": mat_plain("#ff8800"), "rightmark": mat_plain("#ff00ff"),
            "rarm": mat_plain("#00e0e0"), "larm": mat_plain("#a060ff")}
    return m, paint(m, mats)


def main(out):
    os.makedirs(out, exist_ok=True)
    m, tex = build()
    proj = os.path.join(out, "proj")
    rp = os.path.join(proj, "resource_packs", "conv_rp")
    for d in ("models/entity", "textures/entity", "entity"):
        os.makedirs(os.path.join(rp, d), exist_ok=True)
    geo = {"format_version": "1.16.0", "minecraft:geometry": [m.geometry_json("geometry.conv", bounds=(3, 3, (0, 1, 0)))]}
    json.dump(geo, open(os.path.join(rp, "models/entity/conv.geo.json"), "w"), indent=1)
    tex.save(os.path.join(rp, "textures/entity/conv.png"))
    ce = {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": "conv:conv", "materials": {"default": "entity_alphatest"},
        "textures": {"default": "textures/entity/conv"}, "geometry": {"default": "geometry.conv"},
        "render_controllers": ["controller.render.default"]}}}
    json.dump(ce, open(os.path.join(rp, "entity/conv.entity.json"), "w"), indent=1)
    json.dump({"format_version": 2, "header": {"name": "conv", "description": "", "uuid": "4f0c9f43-8d8a-4a4c-9a55-0a1b2c3d4e5f",
                                               "version": [1, 0, 0], "min_engine_version": [1, 21, 0]},
               "modules": [{"type": "resources", "uuid": "5a1b2c3d-4e5f-4a4c-9a55-0a1b2c3d4e60", "version": [1, 0, 0]}]},
              open(os.path.join(rp, "manifest.json"), "w"))
    views = []
    for yaw, lab in ((0, "ours: front"), (90, "ours: creature's right side"), (180, "ours: back")):
        views.append((render(m, tex, yaw=yaw, pitch=10, size=(320, 320), bloom=False), lab))
    for view in ("front", "side", "back"):
        png = os.path.join(out, f"mct_{view}.png")
        cmd = ["npx", "-y", "@minecraft/creator-tools@0.21.0", "--offline", "-i", proj, "render", "model",
               os.path.join(rp, "models/entity/conv.geo.json"), png, "--view", view, "--no-vanilla",
               "--no-gpu", "--width", "320", "--height", "320", "--no-grid"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        if r.returncode != 0 or not os.path.exists(png):
            print("mct render failed:", r.stdout[-800:], r.stderr[-800:])
            continue
        from PIL import Image
        views.append((Image.open(png).convert("RGB").resize((320, 320)), f"mct: {view}"))
    s = sheet([v[0] for v in views], cols=3, labels=[v[1] for v in views])
    s.save(os.path.join(out, "conventions.png"))
    print("wrote", os.path.join(out, "conventions.png"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "build/conv")
