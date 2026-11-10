#!/usr/bin/env python3
"""Pack icons (BP + RP pack_icon.png, 256 px) and the README hero image, rendered from the real
model in the reference-art pose (gauntlet thrust forward, compass held low)."""
from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kinematics as K  # noqa: E402
import preview_sheets as PS  # noqa: E402
import render_preview as R  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(ROOT, "addon")


def hero(size, yaw=-38, pitch=6, scale=None, target=(0, 21, 0), phase=1, t=3.2, action="intro", wings=None):
    W, H = size
    pose = PS.layered_pose(action, t, phase, wings, life=1.0)
    cam = K.Camera(target, yaw, pitch, scale=scale or H / 44, size=size)
    img = R.draw(cam, pose, ground=False)
    return img


def frame(img, title=True):
    W, H = img.size
    d = ImageDraw.Draw(img, "RGBA")
    gold = (214, 172, 92, 255)
    d.rectangle([3, 3, W - 4, H - 4], outline=gold, width=max(2, W // 128))
    d.rectangle([9, 9, W - 10, H - 10], outline=(150, 110, 50, 200), width=1)
    if title:
        f = R.font(max(12, W // 12))
        txt = "EXTRA SUPER BOSS"
        tw = d.textlength(txt, font=f)
        d.rectangle([0, H - W // 7 - 6, W, H], fill=(25, 14, 12, 210))
        d.text(((W - tw) / 2, H - W // 7), txt, font=f, fill=gold)
    return img


def edison_hero(size, yaw=-30, pitch=6, scale=None, target=(0, 22, 0), phase=1, t=0.6, action="intro", dynamo=True):
    W, H = size
    pose = PS.edison_pose(action, t, phase, life=1.0)
    off = (0, 33.5, 0) if dynamo else (0, 0, 0)
    cam = K.Camera(target, yaw, pitch, scale=scale or H / 60, size=size)
    tex = PS.E_TEX2 if phase == 2 else PS.E_TEX
    extra = [(PS.D_GEO, PS.D_TEX2 if phase == 2 else PS.D_TEX, None, False)] if dynamo else []
    return R.draw(cam, PS.scaled(pose, offset=off), ground=False, geo=PS.E_GEO, tex=tex, extra=extra)


def main():
    # pack icon: both bosses, Da Vinci on the left and Edison on his Dynamo on the right
    left = hero((128, 256), yaw=-30, scale=256 / 36, target=(0, 21, 0))
    right = edison_hero((128, 256), yaw=-58, scale=256 / 80, target=(0, 35, 0))
    both = Image.new("RGB", (256, 256))
    both.paste(left, (0, 0))
    both.paste(right, (128, 0))
    icon = frame(both)
    for pack in ("behavior_packs", "resource_packs"):
        icon.save(os.path.join(ADDON, pack, "extra_super_boss", "pack_icon.png"))
    os.makedirs(R.OUT, exist_ok=True)
    icon.save(os.path.join(R.OUT, "pack_icon.png"))
    # README hero: phase 1 and phase 2 side by side
    a = hero((560, 640), yaw=-38, scale=640 / 50, target=(0, 20, 0))
    b = hero((560, 640), yaw=20, scale=640 / 56, target=(0, 22, 0), phase=2, t=2.35, action="transform",
             wings="wings_unfold")
    out = Image.new("RGB", (1120, 640))
    out.paste(a, (0, 0))
    out.paste(b, (560, 0))
    d = ImageDraw.Draw(out)
    d.text((16, 12), "Phase 1 - the Clockwork Maestro", fill=(240, 215, 170), font=R.font(22))
    d.text((576, 12), "Phase 2 - ornithopter wings unfold", fill=(240, 215, 170), font=R.font(22))
    out.save(os.path.join(R.OUT, "hero.png"))
    # Edison hero: on the Dynamo in the reference pose / phase 2 (AC) backstab
    a = edison_hero((560, 640), yaw=-58, pitch=-2, scale=640 / 88, target=(0, 36, 0))
    b = edison_hero((560, 640), yaw=24, scale=640 / 72, target=(0, 26, 0), phase=2, t=2.3, action="transform", dynamo=False)
    out = Image.new("RGB", (1120, 640))
    out.paste(a, (0, 0))
    out.paste(b, (560, 0))
    d = ImageDraw.Draw(out)
    d.text((16, 12), "Thomas Edison on the Dynamo", fill=(240, 215, 170), font=R.font(22))
    d.text((576, 12), "Phase 2: the Current War (AC)", fill=(200, 235, 255), font=R.font(22))
    out.save(os.path.join(R.OUT, "edison_hero.png"))
    print("icons + heroes written")


if __name__ == "__main__":
    main()
