"""
Render the documentation images (docs/images) from the real models, textures and
animations, through the offline Bedrock emulation in tools/rww.

    python3 tools/previews.py
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from rww import bedrock, icons, preview, render, swords  # noqa: E402
from rww.materials import TIER_ORDER, TIERS  # noqa: E402

OUT = os.path.join(ROOT, "docs", "images")
WEAPONS = ["rapier", "zweihander", "katana"]
TITLE = {"rapier": "Rapier", "zweihander": "Zweihänder", "katana": "Katana"}
BG = (34, 38, 46, 255)


def label(img, text, xy=(8, 6)):
    d = ImageDraw.Draw(img)
    d.text(xy, text, fill=(232, 234, 238, 255), font=preview.font(15))
    return img


def model_instance(weapon, tier, root=None):
    _, _, _, m, geo, _ = preview.weapon_assets(weapon)
    mats = bedrock.world_matrices(geo, bedrock.rest_pose(geo), root=root)
    return render.Instance(geo, preview.texture(weapon, tier), mats), m


def tiers_sheet():
    """3 rows (weapons) x 7 columns (tiers), flat side view, true relative scale."""
    colw, rowh = 136, 470
    img = Image.new("RGBA", (colw * 7, rowh * 3 + 24), (24, 26, 32, 255))
    d = ImageDraw.Draw(img)
    for c, t in enumerate(TIER_ORDER):
        d.text((c * colw + 8, 4), TIERS[t].name, fill=(220, 224, 230, 255), font=preview.font(14))
    for r, w in enumerate(WEAPONS):
        for c, t in enumerate(TIER_ORDER):
            inst, m = model_instance(w, t)
            cam = render.Camera(eye=(-80, 33, 0.001), target=(0, 33, 0), ortho=19.5)
            tile = render.render([inst], cam, size=(colw, rowh), bg=BG, light=(-0.85, 0.45, -0.25), ambient=0.55)
            if c == 0:
                label(tile, TITLE[w])
            img.paste(tile, (c * colw, 24 + r * rowh))
    img.save(os.path.join(OUT, "tiers.png"))


def hilts_sheet():
    tiles = []
    for w, yc, half in (("rapier", 24.8, 4.6), ("zweihander", 26.0, 7.2), ("katana", 24.0, 5.6)):
        for t in ("iron", "golden", "netherite"):
            inst, m = model_instance(w, t)
            cam = render.Camera(eye=(-30, yc + 14, -34), target=(0, yc, 0), ortho=half)
            tiles.append((f"{TITLE[w]} – {TIERS[t].name}",
                          render.render([inst], cam, size=(300, 300), bg=BG, light=preview.DOC_LIGHT, ambient=0.5)))
    preview.sheet(tiles, 3).save(os.path.join(OUT, "hilts.png"))


def icon_sheet():
    s = 4
    img = Image.new("RGBA", (32 * s * 7 + 8 * 8, 32 * s * 3 + 8 * 4), (52, 54, 60, 255))
    for r, w in enumerate(WEAPONS):
        for c, t in enumerate(TIER_ORDER):
            ic = icons.icon(w, t).resize((32 * s, 32 * s), Image.NEAREST)
            img.paste(ic, (8 + c * (32 * s + 8), 8 + r * (32 * s + 8)), ic)
    img.save(os.path.join(OUT, "icons.png"))


def stances(w):
    states = [("Guard / idle", {}, None), ("Walking", {"moving": 0.75, "distance": 1.2}, None),
              ("Sprinting", {"moving": 1.0, "sprinting": True, "distance": 2.0}, None), ("Sneaking", {"sneaking": True}, None),
              ("Jumping / falling", {"on_ground": False, "vertical_speed": -3.0}, None),
              ("Swimming", {"swimming": True, "swim_amount": 1.0, "in_water": True}, None),
              ("Equip (draw) 30%", {}, 0.3), ("Equip (draw) 70%", {}, 0.7)]
    tiles = []
    for name, st, eq in states:
        variables = {"rww_lat": 1e9, "rww_carry": 0.0} if (w == "zweihander" and name.startswith("Guard")) else None
        if variables:
            pose, ctx = preview.simulate(w, dict(st, first_person=False), variables=variables)
            pm = preview.player.player_matrices(pose)
            am = preview.attach(w, ctx, pm, False)
            _, _, _, m, geo, _ = preview.weapon_assets(w)
            img = render.render([render.Instance(preview.player.PLAYER_GEO, preview.skin(), pm),
                                 render.Instance(geo, preview.texture(w, "iron"), am)],
                                render.Camera(eye=(-46, 30, -52), target=(0, 19, -4), fov=44), size=(300, 320), bg=BG,
                                light=preview.DOC_LIGHT, ambient=0.5)
        else:
            img, _ = preview.frame(w, "iron", st, equip=eq, size=(300, 320), bg=BG)
        tiles.append((name, img))
    if w == "zweihander":
        img, _ = preview.frame(w, "iron", {}, size=(300, 320), bg=BG)
        tiles.insert(1, ("Out of combat: shoulder carry", img))
    preview.sheet(tiles, len(tiles) // 2 if len(tiles) % 2 == 0 else (len(tiles) + 1) // 2).save(
        os.path.join(OUT, f"stances_{w}.png"))


ATTACK_NAMES = {
    "rapier": ["Stoccata (lunge)", "Imbroccata (high descending thrust)", "Punta riversa (inside-line thrust)"],
    "katana": ["Kesa-giri (diagonal down)", "Kiri-age (rising diagonal)", "Kiri-oroshi + chiburi"],
    "zweihander": ["Oberhau (high diagonal)", "Unterhau (rising backhand)", "Mittelhau (horizontal)"],
}


def attacks(w):
    tiles = []
    for v in range(3):
        for t in (0.04, 0.1, 0.2, 0.32, 0.5, 0.75):
            img, _ = preview.frame(w, "iron", {}, attack=(v, t), size=(230, 270), bg=BG)
            tiles.append((f"{ATTACK_NAMES[w][v] if t == 0.04 else ''}  t={t}", img))
    preview.sheet(tiles, 6).save(os.path.join(OUT, f"attacks_{w}.png"))


def first_person(w):
    tiles = []
    img, _ = preview.frame(w, "iron", {}, first_person=True, size=(320, 180), bg=BG)
    tiles.append(("idle", img))
    for v in range(3):
        for t in (0.08, 0.2, 0.32):
            img, _ = preview.frame(w, "iron", {}, first_person=True, attack=(v, t), size=(320, 180), bg=BG)
            tiles.append((f"{ATTACK_NAMES[w][v].split(' (')[0]} t={t}", img))
    img, _ = preview.frame(w, "iron", {"moving": 0.8, "distance": 3.0}, first_person=True, size=(320, 180), bg=BG)
    tiles.append(("walking", img))
    img, _ = preview.frame(w, "golden", {}, first_person=True, size=(320, 180), bg=BG)
    tiles.append(("golden tier", img))
    preview.sheet(tiles, 4).save(os.path.join(OUT, f"first_person_{w}.png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    tiers_sheet()
    hilts_sheet()
    icon_sheet()
    for w in WEAPONS:
        stances(w)
        attacks(w)
        first_person(w)
    icons.pack_icon().save(os.path.join(OUT, "pack_icon.png"))
    print("wrote", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
