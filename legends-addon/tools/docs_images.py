"""Render the documentation images (docs/images) from the real models, textures and animations."""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from creatures import registry  # noqa: E402
from mk.render import render_views  # noqa: E402
from preview import pose_for  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "docs", "images")
BG = (24, 26, 36)

# (creature, label, props, act, time, variant)
SHOTS = {
    "taotie": [("Phase I", {"legends:phase": 1}, None, 0, 0), ("Phase II · armpit eyes", {"legends:phase": 2}, "gaze", 1.2, 1),
               ("Phase III · the head", {"legends:phase": 3}, None, 0, 1), ("ULT · Maw", {"legends:phase": 3}, "maw", 5.0, 1)],
    "nidhogg": [("Phase I · ground", {"legends:phase": 1}, None, 0, 0), ("Phase II · flight", {"legends:phase": 2, "legends:var": 1}, None, 0, 0),
                ("Phase III · Ragnarök", {"legends:phase": 3, "legends:var": 1}, "breath", 1.6, 1), ("ULT · rupture", {"legends:phase": 3, "legends:var": 1}, "rupture", 1.2, 1)],
    "hanuman": [("Phase I", {"legends:phase": 1}, "taunt", 1.5, 0), ("Phase II · burning tail", {"legends:phase": 2}, "fire_spin", 0.8, 0),
                ("Phase III · 4 faces 8 arms", {"legends:phase": 3}, None, 0, 0), ("ULT · Yawning Stars", {"legends:phase": 3}, "yawn", 3.0, 0)],
    "alicorn": [("Phase I", {"legends:phase": 1}, None, 0, 0), ("Phase II · flight", {"legends:phase": 2, "legends:fly": 1, "legends:var": 2}, None, 0, 0),
                ("Phase III · star crown", {"legends:phase": 3, "legends:fly": 1, "legends:var": 3}, None, 0, 0), ("ULT · Dawnbreak", {"legends:phase": 3, "legends:fly": 1, "legends:var": 3}, "nova", 5.0, 0)],
    "tenko": [("Phase I", {"legends:phase": 1}, None, 0, 0), ("Phase II · foxfire", {"legends:phase": 2}, "foxfire", 0.5, 0),
              ("Phase III · moon tail", {"legends:phase": 3}, "howl", 1.0, 1), ("ULT · Eclipse wheel", {"legends:phase": 3}, "eclipse", 5.0, 1)],
    "logos": [("Phase I · sealed", {"legends:phase": 1, "legends:var": 0}, None, 0, 0), ("Phase II · seals break", {"legends:phase": 2, "legends:var": 3}, None, 0, 0),
              ("Phase III · the eye opens", {"legends:phase": 3, "legends:var": 7}, None, 0, 0), ("ULT · The Final Word", {"legends:phase": 3, "legends:var": 7}, "apocalypse", 6.0, 0)],
}


def shot(c, props, act, t, variant, yaw=-35, pitch=14, size=360):
    m = c.model
    tex0 = m.texture
    if variant:
        m.texture = m.paint(variant=variant)
    pose, vis = pose_for(c, act, t, props)
    img = render_views([(m, pose, vis)], [(yaw, pitch)], size=size, bg=BG)
    m.texture = tex0
    return img


def sheet(rows, cols, tiles, labels, title, size):
    top = 34
    W, H = cols * size, rows * (size + 20) + top
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((10, 10), title, fill=(240, 220, 160))
    for i, (t, l) in enumerate(zip(tiles, labels)):
        x, y = (i % cols) * size, top + (i // cols) * (size + 20)
        img.paste(t, (x, y + 20))
        d.text((x + 8, y + 4), l, fill=(210, 210, 225))
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    heroes = []
    for key, shots in SHOTS.items():
        c = registry.ALL[key]()
        c.model.paint()
        tiles = [shot(c, p, a, t, v) for _, p, a, t, v in shots]
        sheet(1, 4, tiles, [s[0] for s in shots], c.description, 360).save(os.path.join(OUT, f"{key}.png"))
        heroes.append(shot(c, shots[0][1], None, 0, 0, size=330))
        print("rendered", key)
    names = [registry.ALL[k]().description for k in SHOTS]
    sheet(2, 3, heroes, names, "Legendary & Divine Beings — the six extra bosses", 330).save(os.path.join(OUT, "bosses.png"))
    choir = []
    for key in registry.CHOIR:
        c = registry.ALL[key]()
        c.model.paint()
        choir.append(shot(c, {"legends:phase": 1}, None, 0, 0, size=330))
    sheet(1, 3, choir, ["Seraph", "Cherub", "Ophan (Thrones)"], "The Choir of the Word", 330).save(os.path.join(OUT, "choir.png"))
    props = []
    for key in registry.PROPS:
        c = registry.ALL[key]()
        c.model.paint()
        pose, vis = pose_for(c, life=2.0)
        props.append(render_views([(c.model, pose, vis)], [(-35, 20)], size=200, bg=BG))
    sheet(2, 8, props, registry.PROPS, "Hazards, projectiles and ritual props", 200).save(os.path.join(OUT, "props.png"))


if __name__ == "__main__":
    main()
