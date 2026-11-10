"""
Docs previews rendered from the same generators the build uses (not in-game screenshots).

    python3 tools/preview.py      -> docs/preview/*.png
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import art  # noqa: E402
import fruit_icon  # noqa: E402

OUT = os.path.join(ROOT, "docs", "preview")


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    # reference art vs. the 64x64 item texture (shown at 8x, on the inventory slot grey)
    ref = fruit_icon.source().resize((512, 512), Image.LANCZOS)
    icon = fruit_icon.fruit_icon(128).resize((512, 512), Image.NEAREST)
    sheet = Image.new("RGBA", (1064, 552), (139, 139, 139, 255))
    sheet.alpha_composite(ref, (16, 20))
    sheet.alpha_composite(icon, (536, 20))
    d = ImageDraw.Draw(sheet)
    d.text((16, 535), "reference art", fill=(20, 20, 20, 255))
    d.text((536, 535), "joki_fruit.png (128x128, shown at 4x)", fill=(20, 20, 20, 255))
    sheet.save(os.path.join(OUT, "fruit_reference_vs_icon.png"))
    # valve + Steam Console icons
    icons = [art.valve_icon()] + [art.ui_icon(n) for n in art.UI_ICONS]
    strip = Image.new("RGBA", (len(icons) * 68 + 4, 72), (139, 139, 139, 255))
    for i, ic in enumerate(icons):
        strip.alpha_composite(ic.resize((64, 64), Image.NEAREST), (i * 68 + 4, 4))
    strip.save(os.path.join(OUT, "valve_and_console_icons.png"))
    # particle atlas on a dark sky colour
    atlas = art.particle_atlas().resize((512, 512), Image.NEAREST)
    bg = Image.new("RGBA", (512, 512), (52, 64, 88, 255))
    bg.alpha_composite(atlas)
    bg.save(os.path.join(OUT, "particle_atlas_x4.png"))
    fruit_icon.pack_icon().save(os.path.join(OUT, "pack_icon.png"))
    print("previews ->", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
