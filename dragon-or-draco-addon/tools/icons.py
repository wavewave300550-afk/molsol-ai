#!/usr/bin/env python3
"""Pack icons (256x256) rendered from the real model: roaring head + a little fire glow."""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kinematics as K  # noqa: E402
import render_preview as R  # noqa: E402

P = "animation.dod.red_dragon."


def main():
    pose = R.pose_of([P + "idle_breathe", P + "roar"], 1.15, {})
    mouth = K.locator_world(R.GEO, pose, "head", "mouth")
    cam = K.Camera((mouth[0] + 2, mouth[1] + 4, mouth[2] + 18), 38, 8, scale=5.2, size=(512, 512))
    img = R.draw(cam, pose, ground=False)
    # warm radial backdrop glow behind the head
    a = np.array(img).astype(float)
    yy, xx = np.mgrid[0:512, 0:512]
    d = np.sqrt((xx - 330) ** 2 + (yy - 300) ** 2) / 360
    glow = np.clip(1 - d, 0, 1)[..., None] ** 2 * np.array([110, 40, 10])
    a = np.clip(a + glow, 0, 255).astype(np.uint8)
    icon = Image.fromarray(a).resize((256, 256), Image.LANCZOS)
    dr = ImageDraw.Draw(icon)
    dr.rectangle([0, 0, 255, 255], outline=(255, 205, 87), width=3)
    for pack in ("behavior_packs", "resource_packs"):
        icon.save(os.path.join(R.ROOT, "addon", pack, "dragon_or_draco", "pack_icon.png"))
    icon.save(os.path.join(R.OUT, "pack_icon.png"))
    print("pack icons written")


if __name__ == "__main__":
    main()
