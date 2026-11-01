"""Contact sheets of every animation, sampled from the real animation file (see render_preview.py)."""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kinematics as K  # noqa: E402
import render_preview as R  # noqa: E402

P = "animation.dod.red_dragon."
# (title, layers, frames, fire, camera yaw, pitch, moving)
SETS = [
    ("1. Idle Breathing", ["idle", "breathe"], [0, 1, 2, 3], False, 120, 14, False),
    ("2. Look Around", ["idle", "breathe", "look_around"], [0.6, 1.2, 2.2, 2.8], False, 150, 14, False),
    ("3. Walk", ["idle", "breathe", "walk"], [0, 0.25, 0.5, 0.75], False, 90, 6, "walk"),
    ("4. Run", ["idle", "breathe", "run"], [0, 0.25, 0.5, 0.75], False, 90, 6, "run"),
    ("5a. Wing Spread", ["idle", "wing_spread"], [0, 0.3, 0.6, 0.9], False, 150, 18, False),
    ("5b. Wing Fold", ["idle", "wing_fold"], [0, 0.3, 0.6, 0.9], False, 150, 18, False),
    ("6. Takeoff", ["takeoff"], [0.2, 0.4, 0.62, 1.2], False, 120, 10, False),
    ("7. Flying", ["fly"], [0, 0.28, 0.55, 0.82], False, 150, 14, False),
    ("8. Glide", ["glide"], [0, 0.75, 1.5, 2.25], False, 150, 20, False),
    ("9. Landing", ["landing"], [0.25, 0.5, 0.85, 1.3], False, 120, 10, False),
    ("10. Roar", ["idle", "breathe", "roar"], [0.5, 0.8, 1.2, 1.9], False, 125, 10, False),
    ("11. Bite", ["idle", "breathe", "bite"], [0.15, 0.3, 0.45, 0.7], False, 100, 8, False),
    ("12. Claw Swipe", ["idle", "breathe", "claw"], [0.2, 0.4, 0.55, 0.8], False, 40, 10, False),
    ("13. Tail Smash", ["idle", "breathe", "tail_smash"], [0.3, 0.45, 0.62, 0.72], False, 200, 30, False),
    ("14. Wing Buffet", ["idle", "breathe", "wing_buffet"], [0.25, 0.45, 0.7, 1.0], False, 30, 10, False),
    ("15. Fire Breath Charge", ["idle", "breathe", "fire_charge"], [0.2, 0.6, 1.0, 1.3], False, 110, 8, False),
    ("16. Fire Breath Release", ["idle", "breathe", "fire_breath"], [0.05, 0.3, 1.2, 2.4], True, 115, 12, False),
    ("17. Hurt", ["idle", "breathe", "hurt"], [0, 0.08, 0.2, 0.4], False, 110, 10, False),
    ("18. Death", ["idle", "death"], [0.4, 1.0, 1.6, 2.8], False, 120, 14, False),
    ("Idle: Wing Stretch", ["idle", "breathe", "wing_stretch"], [0.3, 0.6, 1.0, 1.4], False, 150, 16, False),
]
TW, TH = 330, 220


def sheet(sets, path, cols=4):
    rows = len(sets)
    label_w = 190
    img = Image.new("RGB", (label_w + cols * TW, rows * TH), (16, 10, 11))
    d = ImageDraw.Draw(img)
    f = R.font(17)
    fs = R.font(12)
    for r, (title, layers, frames, fire, yaw, pitch, moving) in enumerate(sets):
        d.text((12, r * TH + TH // 2 - 10), title, fill=(255, 205, 87), font=f)
        for c, t in enumerate(frames):
            env = {"prop:dod:aim": 0, "v.walk_w": 1 if moving == "walk" else 0, "v.run_w": 1 if moving == "run" else 0}
            if moving:
                env["q.modified_distance_moved"] = t * (360 / 22 if moving == "walk" else 360 / 17)
            weights = [1.0] * len(layers)
            pose = R.pose_of([P + n for n in layers], t, env, weights)
            cam = K.Camera((0, 44, 4), yaw, pitch, scale=0.95, size=(TW, TH))
            tile = R.draw(cam, pose, fire=fire)
            img.paste(tile, (label_w + c * TW, r * TH))
            d.text((label_w + c * TW + 6, r * TH + 4), f"t={t:g}s", fill=(230, 200, 190), font=fs)
    img.save(path)
    print("wrote", path)


def label(img, text, xy, size=20, color=(255, 205, 87)):
    ImageDraw.Draw(img).text(xy, text, fill=color, font=R.font(size))


def model_views():
    """Reference views like the concept sheet: front / side / top (wings spread) / three-quarter."""
    idle = R.pose_of([P + "idle", P + "breathe"], 0.0, {})
    spread = R.pose_of([P + "glide"], 0.0, {})
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
    pose = R.pose_of([P + "glide"], 0.0, {})
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
        col = (255, 205, 87) if "wing" in b["name"] else (255, 107, 30) if "tail" in b["name"] or "neck" in b["name"] else (240, 240, 240)
        if "_mem_" in b["name"]:
            continue
        d.line([(S[0, 0], S[0, 1]), (S[1, 0], S[1, 1])], fill=col, width=2)
        d.ellipse([S[0, 0] - 3.5, S[0, 1] - 3.5, S[0, 0] + 3.5, S[0, 1] + 3.5], fill=col)
    n = len(R.GEO["bones"])
    c = sum(len(b.get("cubes", [])) for b in R.GEO["bones"])
    label(base, f"Rig: {n} bones, {c} cubes  (white = body/legs, orange = neck/tail, gold = wings)", (16, 14), 22)
    base.save(os.path.join(R.OUT, "rig.png"))
    print("wrote rig.png")


def fire_hero():
    pose = R.pose_of([P + "idle", P + "breathe", P + "fire_breath"], 1.2, {"prop:dod:aim": 0, "prop:dod:jet": 12})
    cam = K.Camera((0, 60, -150), 118, 8, scale=1.9, size=(1400, 700))
    img = R.draw(cam, pose, fire=True)
    label(img, "16. Fire Breath Release - jet geometry bound to the head, origin = mouth locator, points along the aim", (16, 14), 20)
    img.save(os.path.join(R.OUT, "fire_breath.png"))
    pose = R.pose_of([P + "fly"], 0.5, {})
    cam = K.Camera((0, 56, 0), 150, -12, scale=1.25, size=(1400, 700))
    img = R.draw(cam, pose, ground=False)
    label(img, "7. Flying (downstroke)", (16, 14), 20)
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
    sheet(SETS[:10], os.path.join(R.OUT, "animations_locomotion.png"))
    sheet(SETS[10:], os.path.join(R.OUT, "animations_combat.png"))


if __name__ == "__main__":
    main()
