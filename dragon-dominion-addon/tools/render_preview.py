#!/usr/bin/env python3
"""
Software render of the add-on's real files (geometry + texture + animation keyframes).

    python3 tools/render_preview.py                 -> docs/preview/gharvok_four_view.png  (pure white, no labels)
    python3 tools/render_preview.py --pose <anim> <t> [--tex cracked]  -> docs/preview/_pose.png
    python3 tools/render_preview.py --sheet         -> docs/preview/animation_sheet.png (labelled key poses)

It draws the .geo.json, the texture PNG and the .animation.json keyframes exactly as stored in the
resource pack (kinematics.py).  It is NOT a capture from Minecraft.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kinematics as K  # noqa: E402

ROOT = os.path.dirname(HERE)
RP = os.path.join(ROOT, "addon", "resource_packs", "dragon_dominion")
OUT = os.path.join(ROOT, "docs", "preview")
GEO = K.load_json(os.path.join(RP, "models", "entity", "gharvok.geo.json"))["minecraft:geometry"][0]


def tex(name="intact"):
    return np.array(Image.open(os.path.join(RP, "textures", "entity", f"gharvok_{name}.png")).convert("RGBA"))


def anims():
    p = os.path.join(RP, "animations", "gharvok.animation.json")
    return K.load_json(p)["animations"] if os.path.exists(p) else {}


def pose_of(spec, env=None):
    """spec: list of (anim_name, time, weight)."""
    A = anims()
    env = dict(env or {})
    full = {k if k.startswith("animation.") else k: v for k, v in A.items()}
    names = [s[0] if s[0].startswith("animation.") else f"animation.dragon_dominion.gharvok.{s[0]}" for s in spec]
    return K.sample_pose([full[n] for n in names], [s[2] for s in spec], [s[1] for s in spec], env)


def render(cam, pose=None, texture="intact", hidden=(), bg=(255, 255, 255)):
    W, H = cam.size
    img = np.ones((H, W, 3)) * (np.array(bg) / 255.0)
    faces = list(K.world_faces(GEO, pose, hidden))
    img, _, _, _ = K.render(faces, tex(texture), cam, image=img, zbuf=np.full((H, W), np.inf), emissive_alpha=0,
                            ambient=0.55)
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


def font(size):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()


def four_view(pose=None, name="gharvok_four_view.png", texture="intact", size=(880, 520), scale=2.6, hidden=(),
              ss=2):
    """Same layout as the reference sheet: front, profile (head left), profile (head right), rear."""
    views = [(0, 6), (90, 4), (-90, 4), (180, 6)]
    tiles = []
    for yaw, pitch in views:
        cam = K.Camera((0, 40, 0), yaw, pitch, scale=scale * ss, size=(size[0] * ss, size[1] * ss))
        t = render(cam, pose, texture, hidden).resize(size, Image.LANCZOS)
        tiles.append(t)
    sheet = Image.new("RGB", (size[0] * 2, size[1] * 2), (255, 255, 255))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 2) * size[0], (i // 2) * size[1]))
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    sheet.save(p)
    print("wrote", p)
    return p


def close_up(pose=None, name="_head.png", texture="intact"):
    tiles = []
    for yaw, pitch in ((0, 8), (40, 10), (90, 2), (150, 25)):
        cam = K.Camera((0, 52, -80), yaw, pitch, scale=6, size=(520, 420))
        tiles.append(render(cam, pose, texture))
    sheet = Image.new("RGB", (1040, 840), (255, 255, 255))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 2) * 520, (i // 2) * 420))
    p = os.path.join(OUT, name)
    sheet.save(p)
    print("wrote", p)


def sheet(entries, name, cols=4, size=(440, 320), scale=1.4, yaw=55, pitch=12, texture="intact"):
    rows = (len(entries) + cols - 1) // cols
    out = Image.new("RGB", (cols * size[0], rows * size[1]), (255, 255, 255))
    d = ImageDraw.Draw(out)
    for i, (label, spec) in enumerate(entries):
        cam = K.Camera((0, 36, 10), yaw, pitch, scale=scale, size=size)
        t = render(cam, pose_of(spec) if spec else None, texture)
        out.paste(t, ((i % cols) * size[0], (i // cols) * size[1]))
        d.text(((i % cols) * size[0] + 8, (i // cols) * size[1] + 6), label, fill=(40, 40, 40), font=font(16))
    p = os.path.join(OUT, name)
    out.save(p)
    print("wrote", p)


def top(pose=None, name="_top.png"):
    cam = K.Camera((0, 40, 0), 0, 89, scale=2.2, size=(800, 700))
    render(cam, pose).save(os.path.join(OUT, name))
    print("wrote", os.path.join(OUT, name))


# wing layer weights per action: same rules as the client entity's pre_animation (tools/gen_anims.py)
import gen_anims as GA  # noqa: E402

RUNNING = {"run", "charge"}


def wing_weights(anim):
    fold = GA.FOLD_TARGET.get(anim, 1.0)
    if anim in ("wing_flap", "glide"):
        fold = 0.0
    disp = 0.0 if (anim in GA.DISPLAY_OFF or anim in ("wing_flap", "glide")) else (0.2 if anim in RUNNING else
                                                                                   0.85 if anim == "walk" else 1.0)
    return fold, disp


KEY_POSES = [
    ("idle_breathing", 1.0), ("idle_head_scan", 0.8), ("walk", 0.4), ("run", 0.2), ("turn", 0.25), ("jump", 0.42),
    ("takeoff", 0.62), ("wing_flap", 0.0), ("glide", 0.5), ("landing", 0.42), ("roar", 1.2), ("claw_combo", 0.4),
    ("claw_combo", 0.55), ("charge_windup", 1.3), ("charge", 0.15), ("charge_impact", 0.12), ("tail_sweep", 0.5),
    ("tail_sweep", 0.88), ("wing_pressure", 0.85), ("wing_pressure", 1.05), ("cliff_dive", 0.0), ("skullbreaker", 1.35),
    ("skullbreaker", 1.6), ("hit_reaction", 0.08), ("stagger", 0.6), ("skull_fracture", 0.3), ("exhausted", 0.5),
    ("death", 3.6),
]


def pose_spec(anim, t, fold=None, disp=None):
    spec = [(anim, t, 1.0)]
    f, d = wing_weights(anim)
    f = f if fold is None else fold
    d = d if disp is None else disp
    if f:
        spec.append(("wing_fold", 0.0, f))
    if d:
        spec.append(("wing_display", 0.0, d))
    if anim not in ("idle_breathing", "death"):
        spec.append(("idle_breathing", 0.0, 1.0))
    return spec


def key_sheet(name="animation_sheet.png", yaw=55, poses=None):
    entries = [(f"{a} @ {t:.2f}s", pose_spec(a, t)) for a, t in (poses or KEY_POSES)]
    sheet(entries, name, cols=4, yaw=yaw)


if __name__ == "__main__":
    a = sys.argv[1:]
    texture = a[a.index("--tex") + 1] if "--tex" in a else "intact"
    if "--pose" in a:
        i = a.index("--pose")
        four_view(pose_of(pose_spec(a[i + 1], float(a[i + 2]))), "_pose.png", texture)
    elif "--rest" in a:
        four_view(None, "_rest.png", texture)
        close_up(None, "_head.png", texture)
    elif "--top" in a:
        top()
    elif "--sheet" in a:
        key_sheet()
    else:
        display = pose_spec("idle_breathing", 0.0)
        four_view(pose_of(display), "gharvok_four_view.png", texture)
        four_view(pose_of(pose_spec("idle_breathing", 0.0, disp=0.0)), "gharvok_four_view_folded.png", texture)
        four_view(pose_of(display), "gharvok_four_view_broken_crown.png", "broken")
