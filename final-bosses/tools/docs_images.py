"""Showcase renders for the README: each boss at rest and in an ultimate pose."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw  # noqa: E402

import registry  # noqa: E402
from modelkit import deflicker, render_preview  # noqa: E402

POSES = {
    "void_emperor": {"hand_r": {"pos": (-16, 10, 0), "rot": (0, 0, -40)}, "hand_l": {"pos": (16, 10, 0), "rot": (0, 0, 40)},
                     "mask": {"pos": (0, 12, -6), "scale": 1.3}, "rift": {"scale": 1.5}, "mask_halo": {"scale": 1.7}},
    "titan": {"arm_r": {"rot": (-170, 0, -20)}, "arm_l": {"rot": (-170, 0, 20)}, "gear_halo": {"scale": 1.4}, "astrolabe": {"scale": 1.4}},
    "devouring_star": {"jaw": {"rot": (45, 0, 0)}, "mandible_r": {"rot": (0, -40, 0)}, "mandible_l": {"rot": (0, 40, 0)},
                       "body": {"rot": (-20, 0, 0)}, **{f"fin_{s}{k}": {"rot": (0, 0, 30 * g)} for s, g in (("l", 1), ("r", -1)) for k in range(3)}},
    "world_parasite": {"maw": {"rot": (-45, 0, 0)}, "eyelid_r": {"rot": (-100, 0, 0)}, "eyelid_l": {"rot": (-100, 0, 0)},
                       **{f"root{k}_0": {"rot": (0, 0, -35 if k < 2 else 35)} for k in range(4)}},
    "choir": {**{f"wing_{s}{t}": {"rot": (0, 15 * g, 30 * g)} for s, g in (("l", 1), ("r", -1)) for t in range(3)},
              "halo": {"scale": 1.6}, "chorus": {"scale": 1.4}, "mask_shard": {"pos": (6, 4, -2)}},
}
LABEL = {"void_emperor": "The Void Emperor", "titan": "The Titan of Creation", "devouring_star": "The Devouring Star",
         "world_parasite": "The World Parasite", "choir": "The Choir of Mirrors"}


def main(out):
    os.makedirs(out, exist_ok=True)
    tiles = []
    for key, fn in registry.MODELS.items():
        m = fn()
        deflicker(m)
        m.paint()
        paths = []
        for tag, yaw, pitch, pose in (("rest", 32, 16, None), ("back", 210, 22, None), ("ultimate", 28, 12, POSES[key])):
            p = os.path.join(out, f"{key}_{tag}.png")
            render_preview([m], p, yaw=yaw, pitch=pitch, size=520, pose=pose, step=1 if key == "world_parasite" else 2)
            paths.append(p)
        sheet = Image.new("RGBA", (1560, 560), (14, 12, 20, 255))
        for i, p in enumerate(paths):
            sheet.paste(Image.open(p), (i * 520, 40))
        d = ImageDraw.Draw(sheet)
        d.text((12, 12), f"{LABEL[key]}  -  rest / back / ultimate pose", fill=(235, 230, 245, 255))
        sheet.save(os.path.join(out, f"{key}.png"))
        tiles.append(paths[0])
        print("rendered", key)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/images")
