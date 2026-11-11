#!/usr/bin/env python3
"""Render preview contact sheets of the generated models/animations (headless Chromium + three.js).

  python3 tools/preview.py books            -> docs/images/books.png
  python3 tools/preview.py fx [name ...]    -> docs/images/fx_<school>.png (+ per-construct sheets)
These are offline renders using the same geometry/texture/animation files that ship in the RP;
they are NOT in-game screenshots.
"""
import json
import os
import subprocess
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "packs", "Grimoire_RP")
OUT = os.path.join(ROOT, "docs", "images")
TMP = os.path.join(ROOT, ".build", "preview")


def bundle():
    os.makedirs(os.path.join(ROOT, ".build"), exist_ok=True)
    subprocess.run(["npx", "esbuild", "tools/preview/viewer.js", "--bundle", "--format=iife", "--outfile=.build/preview_bundle.js",
                    "--log-level=warning"], cwd=ROOT, check=True)


def render(jobs):
    os.makedirs(TMP, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=TMP) as f:
        json.dump(jobs, f)
        name = f.name
    subprocess.run(["node", "tools/preview/render.mjs", name], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    os.remove(name)


def font(sz):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def sheet(cells, cols, out, title=None, cell=320):
    rows = (len(cells) + cols - 1) // cols
    top = 46 if title else 0
    img = Image.new("RGB", (cols * cell, rows * (cell + 26) + top), (12, 10, 16))
    d = ImageDraw.Draw(img)
    if title:
        d.text((12, 10), title, fill=(240, 230, 210), font=font(22))
    for i, (path, label) in enumerate(cells):
        x, y = (i % cols) * cell, top + (i // cols) * (cell + 26)
        if os.path.exists(path):
            im = Image.open(path).convert("RGB").resize((cell, cell), Image.LANCZOS)
            img.paste(im, (x, y))
        d.text((x + 8, y + cell + 4), label, fill=(220, 210, 200), font=font(14))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out, optimize=True)
    return out


def book_jobs():
    jobs, cells = [], []
    for s in ("pressure", "ice", "blood"):
        geo = f"{RP}/models/entity/grimoire/book_{s}.geo.json"
        anim = f"{RP}/animations/grimoire/book_{s}.animation.json"
        n = f"animation.grimoire.book_{s}"
        tex = {"default": f"{RP}/textures/entity/grimoire/book_{s}.png", "flow": f"{RP}/textures/entity/grimoire/book_{s}_flow.png"}
        anims = [{"file": anim, "name": f"{n}.{k}"} for k in ("closed", "open", "charge", "flip", "emblem", "release")]
        views = [
            ("closed (front cover)", 0.5, [0, 4], {"yaw": 90, "pitch": 12, "dist": 34}),
            ("closed 3/4", 1.0, [0, 4], {"yaw": 130, "pitch": 18, "dist": 34}),
            ("open + charging", 0.6, [1, 2, 4], {"yaw": 0, "pitch": 22, "dist": 38}),
            ("page flip (crouch)", 0.26, [3, 4], {"yaw": 20, "pitch": 30, "dist": 36}),
        ]
        for i, (label, t, use, cam) in enumerate(views):
            out = f"{TMP}/book_{s}_{i}.png"
            jobs.append({"out": out, "geo": geo, "textures": tex, "anims": anims, "flow": True, "size": 512,
                         "camera": {**cam, "target": [0, 1.0, 0], "fov": 30},
                         "frames": [{"t": t, "anims": use}]})
            cells.append((out, f"{s.title()} Grimoire - {label}"))
    return jobs, cells


def fx_jobs(names=None):
    meta = json.load(open(os.path.join(ROOT, ".build_meta.json")))
    jobs, groups = [], {}
    for ident in meta["constructs"]:
        name = ident.split(":")[1]
        if names and not any(name.startswith(n) for n in names):
            continue
        ent = json.load(open(f"{RP}/entity/grimoire/{name}.entity.json"))["minecraft:client_entity"]["description"]
        geo = f"{RP}/models/entity/grimoire/{name}.geo.json"
        anim = f"{RP}/animations/grimoire/{name}.animation.json"
        ctrl = json.load(open(f"{RP}/animation_controllers/grimoire/{name}.ac.json"))["animation_controllers"]
        states = list(ctrl.values())[0]["states"]
        all_anims = json.load(open(anim))["animations"]
        short = {k: v for k, v in ent["animations"].items() if v in all_anims}
        keys = list(short.keys())
        tex = {k: f"{RP}/{v}.png" for k, v in ent["textures"].items()}
        texkey = "v0" if "v0" in tex else "default"
        g = json.load(open(geo))["minecraft:geometry"][0]["description"]
        bw, bh, off = g["visible_bounds_width"], g["visible_bounds_height"], g["visible_bounds_offset"]
        span = max(bw, bh) * 16
        pv = PREVIEW_HINTS.get(name, {})
        cam = {"yaw": 35, "pitch": 26, "dist": max(30, span * 1.25), "target": [off[0] * 16, off[1] * 16, off[2] * 16], "fov": 38}
        cam.update(pv.get("camera", {}))
        anim_list = [{"file": anim, "name": v} for v in short.values()]
        frames = []
        wanted = pv.get("frames") or [("active", 1.2, "p2" if "p2" in states else "p1")]
        for (label, t, st) in wanted:
            use = states.get(st, {}).get("animations", []) if isinstance(st, str) else st
            idx = [keys.index(k) for k in use if k in keys] + ([keys.index("orient")] if "orient" in keys else [])
            frames.append({"t": t, "anims": idx, "texKey": texkey, "label": label, "props": pv.get("props", {}), "v": pv.get("v", {})})
        out = f"{TMP}/{name}.png"
        jobs.append({"out": out, "geo": geo, "textures": tex, "anims": anim_list, "size": 400, "camera": cam,
                     "frames": [{k: v for k, v in f.items() if k != "label"} for f in frames]})
        groups[name] = [(out.replace(".png", f"_{i}.png") if len(frames) > 1 else out, f"{name} - {f['label']}") for i, f in enumerate(frames)]
    return jobs, groups


PREVIEW_HINTS = {}
try:
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from gen.preview_hints import PREVIEW_HINTS  # noqa: F811
except Exception:
    pass


def main():
    bundle()
    what = sys.argv[1] if len(sys.argv) > 1 else "books"
    if what == "books":
        jobs, cells = book_jobs()
        render(jobs)
        print(sheet(cells, 4, os.path.join(OUT, "grimoires.png"), "The three Grimoires (offline render of the shipped geometry, textures and animations)"))
    elif what == "fx":
        names = sys.argv[2:] or None
        jobs, groups = fx_jobs(names)
        render(jobs)
        by_school = {}
        for name, cells in groups.items():
            school = {"p": "pressure", "i": "ice", "b": "blood"}.get(name.split("_")[1][0], "common") if name.startswith("fx_") else "summons"
            by_school.setdefault(school, []).extend(cells)
        for school, cells in by_school.items():
            print(sheet(cells, 4, os.path.join(OUT, f"constructs_{school}.png"), f"{school.title()} constructs (offline render)"))


if __name__ == "__main__":
    main()
