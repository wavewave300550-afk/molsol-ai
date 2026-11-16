"""
docs_images.py - render the documentation images / GIFs from the real model, textures and
animation data (through the client simulator).

    python3 tools/docs_images.py [--gifs]
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import aux_models  # noqa: E402
import icons  # noqa: E402
import preview_anims as pa  # noqa: E402
import render  # noqa: E402
import vesper_model as vm  # noqa: E402

OUT = os.path.join(ROOT, "docs", "images")


def player_figure(sc: render.Scene, at=(0.0, 0.0, 0.0)):
    """A 0.6 x 1.8 block player silhouette for scale (Steve colours)."""
    def box(lo, hi, rgb):
        tex = np.zeros((1, 1, 4), np.float32)
        tex[0, 0, :3] = rgb
        tex[0, 0, 3] = 1
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        corners = {
            "f": [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)],
            "b": [(x1, y1, z1), (x0, y1, z1), (x0, y0, z1), (x1, y0, z1)],
            "l": [(x0, y1, z1), (x0, y1, z0), (x0, y0, z0), (x0, y0, z1)],
            "r": [(x1, y1, z0), (x1, y1, z1), (x1, y0, z1), (x1, y0, z0)],
            "t": [(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)],
        }
        for q in corners.values():
            P = np.array(q, np.float32)
            for tri in ((0, 1, 2), (0, 2, 3)):
                sc._raster(P[list(tri)], [(0, 0)] * 3, tex, "main", 0.95, (1, 1, 1, 1))
    x, y, z = at
    box((x - 0.15, y, z - 0.12), (x + 0.15, y + 0.75, z + 0.12), (0.22, 0.24, 0.55))
    box((x - 0.25, y + 0.75, z - 0.14), (x + 0.25, y + 1.4, z + 0.14), (0.0, 0.62, 0.66))
    box((x - 0.2, y + 1.4, z - 0.2), (x + 0.2, y + 1.8, z + 0.2), (0.8, 0.6, 0.45))


def hero(model, textures, phase, path, eye, target, size=(1280, 720), pose=None, hidden=None, player_at=None, bg=None,
         ground=-9.0):
    skin = "p2" if phase == 2 else "p1"
    top, bot = bg or (((8, 10, 26), (52, 40, 86)) if skin == "p1" else ((14, 4, 22), (62, 20, 70)))
    sc = render.Scene(size[0], size[1], bg_top=top, bg_bottom=bot)
    sc.set_camera(eye, target, 42)
    render.ground_plane(sc, y=ground, size=56, checker=4)
    sc.add_model(model, {"main": textures[skin], "glow": textures["glow_" + skin]}, pose=pose or {}, hidden=hidden or [])
    if player_at:
        player_figure(sc, player_at)
    sc.image().save(path)


def main():
    os.makedirs(OUT, exist_ok=True)
    model, main_atlas, glow_atlas, _ = vm.build()
    T = {"p1": main_atlas.render("p1"), "p2": main_atlas.render("p2"),
         "glow_p1": glow_atlas.render("p1"), "glow_p2": glow_atlas.render("p2")}
    sim = pa.build_sim()
    props = dict(pa.DEFAULTS)
    pose1 = None
    for _ in range(30):
        pose1 = sim.step(0.05, dict(props))
    p1_hidden = vm.LIMB_BONES + ["shield"]
    hero(model, T, 1, os.path.join(OUT, "vesper_p1_hero.png"), (33, 1, 30), (0, 1.5, 0), pose=pose1, hidden=p1_hidden,
         player_at=(5.0, -9.0, 7.0))
    hero(model, T, 1, os.path.join(OUT, "vesper_p1_below.png"), (14, -8, 20), (0, 4.0, 0), pose=pose1, hidden=p1_hidden)
    # phase II rest pose through the client simulator
    sim2 = pa.build_sim()
    p2 = dict(pa.DEFAULTS)
    p2.update({"sab:phase": 2, "sab:skin": 1, "sab:rings": False, "sab:plates": False, "sab:limbs": True, "sab:censers": False})
    pose2 = None
    for _ in range(40):
        pose2 = sim2.step(0.05, dict(p2))
    p2_hidden = vm.PLATE_BONES + vm.RING_BONES + vm.CENSER_BONES + ["shield"]
    hero(model, T, 2, os.path.join(OUT, "vesper_p2_hero.png"), (22, 3, 22), (0, 1.5, 0), pose=pose2, hidden=p2_hidden,
         player_at=(5.0, -4.6, 8.0), ground=-4.6)
    hero(model, T, 2, os.path.join(OUT, "vesper_p2_below.png"), (11, -3.5, 16), (0, 2.0, 0), pose=pose2, hidden=p2_hidden,
         ground=-4.6)
    # helper entities
    aux = aux_models.build_all(main_atlas, glow_atlas)
    cells = []
    for name, (eye, tgt, var, hidden) in {
        "Cherub Drone": ((-2.2, 1.6, 2.6), (0, 0.8, 0), "p1", []),
        "Plasma Orison": ((-1.0, 0.8, 1.2), (0, 0.25, 0), "p2", []),
        "Psalm Censer": ((-2.6, 2.0, 3.0), (0, 1.3, 0), "p1", []),
        "Seraph Halo": ((-6, 3, 7), (0, 1, 0), "p2", ["rim_b", "rim_c"]),
        "Reliquary Plate": ((-4.5, 3.0, 5.0), (0, 1.8, 0), "p2", []),
        "Event Horizon": ((-3.5, 3.0, 4.0), (0, 1.5, 0), "p2", []),
        "Orison Halo": ((-1.2, 1.2, 1.4), (0, 0.4, 0), "p1", []),
    }.items():
        key = {"Cherub Drone": "cherub", "Plasma Orison": "plasma_orb", "Psalm Censer": "censer", "Seraph Halo": "seraph",
               "Reliquary Plate": "hull_plate", "Event Horizon": "singularity", "Orison Halo": "orison_halo"}[name]
        sc = render.Scene(400, 320)
        sc.set_camera(eye, tgt, 40)
        sc.add_model(aux[key], {"main": T[var], "glow": T["glow_" + var]}, hidden=hidden)
        im = sc.image()
        ImageDraw.Draw(im).text((8, 8), name, fill=(240, 240, 240))
        cells.append(im)
    icon_cell = Image.new("RGB", (400, 320), (24, 22, 36))
    for i, (k, fn) in enumerate(icons.ICONS.items()):
        ic = Image.fromarray(fn(), "RGBA").resize((96, 96), Image.NEAREST)
        icon_cell.paste(ic, (24 + i * 124, 112), ic)
    ImageDraw.Draw(icon_cell).text((8, 8), "Items: Psalter / Orison Halo / Vesper Alloy", fill=(240, 240, 240))
    cells.append(icon_cell)
    sheet = Image.new("RGB", (400 * 4, 320 * 2))
    for i, im in enumerate(cells):
        sheet.paste(im, ((i % 4) * 400, (i // 4) * 320))
    sheet.save(os.path.join(OUT, "helpers_and_items.png"))
    if "--stills" in sys.argv:
        print("stills written to", OUT)
        return
    # animation sequences: contact sheets (+ GIFs on request)
    for name in ("transform", "lance", "rite", "pray_p1", "p2_lunge", "p2_nova", "death"):
        pa.run(name, OUT, model, T, fps=8, size=(560, 340), cam=((30, 9, 26), (0, 4, 0)), sheet_cols=6, sheet_n=12,
               gif="--gifs" in sys.argv and name in ("transform", "lance", "p2_lunge"))
    for f in os.listdir(OUT):
        if f.endswith("_sheet.png"):
            os.replace(os.path.join(OUT, f), os.path.join(OUT, "anim_" + f))
    print("docs images written to", OUT)


if __name__ == "__main__":
    main()
