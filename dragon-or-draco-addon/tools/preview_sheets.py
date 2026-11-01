"""Contact sheets of every animation, sampled from the real animation file (see render_preview.py)."""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kinematics as K  # noqa: E402
import render_preview as R  # noqa: E402

P = "animation.dod.red_dragon."
SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview_spec.json")
REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anim_report.json")
# frames that show the phases of an attack (anticipation / action / impact / recovery) or the key
# poses of a transition; everything else is sampled evenly
KEY_FRAMES = {
    "bite": [0.2, 0.36, 0.45, 0.7],
    "claw_swipe": [0.3, 0.46, 0.55, 0.85],
    "tail_smash": [0.4, 0.6, 0.72, 1.0],
    "wing_buffet": [0.35, 0.55, 0.7, 1.15],
    "roar": [0.45, 0.9, 1.3, 2.0],
    "alert": [0.15, 0.35, 0.7, 1.2],
    "fire_breath_charge": [0.2, 0.6, 1.0, 1.3],
    "fire_breath_release": [0.05, 0.3, 1.2, 2.4],
    "hurt": [0.0, 0.06, 0.18, 0.4],
    "death": [0.5, 1.2, 1.9, 3.1],
    "launch": [0.05, 0.25, 0.55, 0.95],
    "landing_impact": [0.0, 0.15, 0.5, 1.2],
    "idle_blink": [0.0, 0.08, 0.15, 0.25],
}
CAM = {"C": (150, 16), "A": (130, 14), "B": (95, 6), "D": (120, 10)}
TW, TH = 300, 200


def specs_by_category():
    specs = {s["name"]: s for s in json.load(open(SPEC))}
    rep = json.load(open(REPORT))
    cats = {}
    for name, meta in rep.items():
        cats.setdefault(meta["category"], []).append((name, meta, specs[name]))
    return cats


def frames_for(name, length):
    return KEY_FRAMES.get(name) or [round(length * f, 2) for f in (0.0, 0.3, 0.55, 0.8)]


def sheet(rows, path, cols=4):
    label_w = 210
    img = Image.new("RGB", (label_w + cols * TW, len(rows) * TH), (16, 10, 11))
    d = ImageDraw.Draw(img)
    f, fs = R.font(16), R.font(12)
    for r, (name, meta, spec) in enumerate(rows):
        layers = [l for l, _ in spec["layers"]]
        weights = [w for _, w in spec["layers"]]
        length = spec.get("length") or meta["length"]
        yaw, pitch = CAM.get(meta["category"][0], (120, 12))
        d.text((12, r * TH + TH // 2 - 18), name, fill=(255, 205, 87), font=f)
        d.text((12, r * TH + TH // 2 + 4), f"{meta['kind']}, {length:g}s", fill=(200, 170, 160), font=fs)
        for c, t in enumerate(frames_for(name, length)):
            env = dict(spec.get("env", {}))
            pose = R.pose_of([P + n for n in layers], t, env, weights)
            target = (0, 44, 4) if meta["category"][0] != "C" else (0, 52, 4)
            cam = K.Camera(target, yaw, pitch, scale=0.9, size=(TW, TH))
            tile = R.draw(cam, pose, fire=spec.get("fire", False), ground=meta["category"][0] != "C" or name in ("pre_takeoff", "landing_impact"))
            img.paste(tile, (label_w + c * TW, r * TH))
            d.text((label_w + c * TW + 6, r * TH + 4), f"t={t:g}s", fill=(230, 200, 190), font=fs)
    img.save(path)
    print("wrote", os.path.relpath(path, R.ROOT))


def label(img, text, xy, size=20, color=(255, 205, 87)):
    ImageDraw.Draw(img).text(xy, text, fill=color, font=R.font(size))


def model_views():
    """Reference views like the concept sheet: front / side / top (wings spread) / three-quarter."""
    idle = R.pose_of([P + "idle_breathe"], 0.0, {})
    spread = R.pose_of([P + "flight_glide"], 0.0, {})
    W, H = 760, 460
    views = [
        ("Front (idle)", idle, K.Camera((0, 50, 0), 0, 6, scale=2.6, size=(W, H)), True),
        ("Side (idle)", idle, K.Camera((0, 46, 10), 90, 4, scale=1.85, size=(W, H)), True),
        ("Top (wings spread)", spread, K.Camera((0, 50, 6), 180, 89, scale=1.2, size=(W, H)), False),
        ("Three-quarter (idle)", idle, K.Camera((0, 48, 10), 140, 20, scale=1.75, size=(W, H)), True),
    ]
    sheet = Image.new("RGB", (W * 2, H * 2))
    for i, (name, pose, cam, ground) in enumerate(views):
        tile = R.draw(cam, pose, ground=ground)
        label(tile, name, (14, 10))
        sheet.paste(tile, ((i % 2) * W, (i // 2) * H))
    lo, hi = R.extents(idle)
    slo, shi = R.extents(spread)
    txt = (f"Final size (scale 1.0): length {(hi[2] - lo[2]) / 16:.1f} blocks, height {(hi[1] - max(lo[1], 0)) / 16:.1f} blocks, "
           f"wingspan {(shi[0] - slo[0]) / 16:.1f} blocks")
    label(sheet, txt, (14, H * 2 - 30), size=18, color=(240, 230, 220))
    sheet.save(os.path.join(R.OUT, "model_views.png"))
    print("wrote model_views.png |", txt)


def rig_view():
    """Bones drawn over a dimmed model: every joint the animations drive."""
    pose = R.pose_of([P + "flight_glide"], 0.0, {})
    cam = K.Camera((0, 50, 8), 150, 28, scale=1.55, size=(1200, 800))
    base = R.draw(cam, pose, ground=False)
    base = Image.blend(base, Image.new("RGB", base.size, (12, 8, 9)), 0.55)
    d = ImageDraw.Draw(base)
    mats = K.bone_matrices(R.GEO, pose)
    by = {b["name"]: b for b in R.GEO["bones"]}
    for b in R.GEO["bones"]:
        if not b.get("parent") or b["name"] in ("body",):
            continue
        p = mats[b["name"]] @ np.array(list(b["pivot"]) + [1.0])
        par = by[b["parent"]]
        q = mats[par["name"]] @ np.array(list(par["pivot"]) + [1.0])
        S = cam.project(np.array([p[:3], q[:3]]))
        col = (255, 205, 87) if "wing" in b["name"] else (255, 107, 30) if "tail" in b["name"] or "neck" in b["name"] \
            else (90, 220, 255) if b["name"].startswith(("toes_", "eyelid_", "jaw")) else (240, 240, 240)
        if "_mem_" in b["name"]:
            continue
        d.line([(S[0, 0], S[0, 1]), (S[1, 0], S[1, 1])], fill=col, width=2)
        d.ellipse([S[0, 0] - 3.5, S[0, 1] - 3.5, S[0, 0] + 3.5, S[0, 1] + 3.5], fill=col)
    n = len(R.GEO["bones"])
    c = sum(len(b.get("cubes", [])) for b in R.GEO["bones"])
    label(base, f"Rig: {n} bones, {c} cubes  (white = body/legs, orange = neck/tail, gold = wings, cyan = toes/eyelids/jaw)", (16, 14), 22)
    base.save(os.path.join(R.OUT, "rig.png"))
    print("wrote rig.png")


def fire_hero():
    pose = R.pose_of([P + "idle_breathe", P + "fire_breath_charge", P + "fire_breath_release"], 1.2, {"prop:dod:aim": 0, "prop:dod:jet": 12}, [1, 0, 1])
    cam = K.Camera((0, 60, -150), 118, 8, scale=1.9, size=(1400, 700))
    img = R.draw(cam, pose, fire=True)
    label(img, "fire_breath_release - jet geometry bound to the head, origin = mouth locator, points along the aim", (16, 14), 20)
    img.save(os.path.join(R.OUT, "fire_breath.png"))
    pose = R.pose_of([P + "flight_flap"], 0.3, {})
    cam = K.Camera((0, 56, 0), 150, -12, scale=1.25, size=(1400, 700))
    img = R.draw(cam, pose, ground=False)
    label(img, "flight_flap (downstroke)", (16, 14), 20)
    img.save(os.path.join(R.OUT, "flying.png"))
    tex = Image.open(os.path.join(R.RP, "textures", "entity", "red_dragon.png")).convert("RGBA")
    bg = Image.new("RGBA", tex.size, (30, 20, 22, 255))
    bg.alpha_composite(tex)
    bg.convert("RGB").resize((1024, 1024), Image.NEAREST).save(os.path.join(R.OUT, "texture_atlas.png"))
    print("wrote fire_breath.png, flying.png, texture_atlas.png")


def main():
    os.makedirs(R.OUT, exist_ok=True)
    model_views()
    rig_view()
    fire_hero()
    for old in ("animations_locomotion.png", "animations_combat.png"):
        if os.path.exists(os.path.join(R.OUT, old)):
            os.remove(os.path.join(R.OUT, old))
    files = {"A": "animations_A_living.png", "B": "animations_B_ground.png", "C": "animations_C_aerial.png",
             "D": "animations_D_combat.png"}
    for cat, rows in sorted(specs_by_category().items()):
        if cat[0] in files:
            sheet(rows, os.path.join(R.OUT, files[cat[0]]))


if __name__ == "__main__":
    main()
