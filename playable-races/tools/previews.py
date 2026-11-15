"""Render documentation previews from the exact geometry + textures in packs/.

    python3 tools/previews.py      (run tools/build.py first)
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw  # noqa: E402

from kit.geo import Model  # noqa: E402
from kit.render import render, sheet  # noqa: E402
from kit.tex import hx  # noqa: E402
from models import golem, jackalope, salamander  # noqa: E402

RP = os.path.join(ROOT, "packs", "PlayableRaces_RP")
OUT = os.path.join(ROOT, "docs", "images")
TEX = "textures/plrace/races"
HIDE = ["r_arm_fp", "l_arm_fp"]
BG = (236, 234, 230)


def tex(race, name):
    return Image.open(os.path.join(RP, TEX, race, f"{race}_{name}.png")).convert("RGBA")


def human() -> tuple:
    """Plain Steve-proportioned figure for scale comparisons."""
    m = Model("human", ppu=1, atlas_width=128)
    m.bone("root", None, (0, 0, 0))
    m.bone("body", "root", (0, 24, 0))
    m.box("body", (0, 18, 0), (8, 12, 4), "c")
    m.bone("head", "body", (0, 24, 0))
    m.box("head", (0, 28, 0), (8, 8, 8), "c")
    for x in (-6, 6):
        m.box("body", (x, 18, 0), (4, 12, 4), "c")
    for x in (-2, 2):
        m.box("root", (x, 6, 0), (4, 12, 4), "c")
    m.pack()
    from kit.tex import paint
    img = paint(m, {"c": lambda ctx: (hx("#9a9aa2") * (1 - 0.1 * (ctx.face == "down")), ctx.ones(), ctx.zeros())})
    return m, img


def keyframe_pose(anim_file, anim_name, t):
    """Evaluate numeric keyframes of an animation at time t -> render pose dict."""
    data = json.load(open(os.path.join(RP, "animations", "plrace", anim_file)))["animations"][anim_name]
    pose = {}
    for bone, chans in data.get("bones", {}).items():
        entry = {}
        for ch, key in (("rotation", "rot"), ("position", "pos")):
            v = chans.get(ch)
            if isinstance(v, dict):
                times = sorted(v.keys(), key=float)
                vals = [v[k] for k in times]
                if not all(isinstance(x, list) and all(isinstance(c, (int, float)) for c in x) for x in vals):
                    continue
                ts = [float(k) for k in times]
                if t <= ts[0]:
                    entry[key] = vals[0]
                elif t >= ts[-1]:
                    entry[key] = vals[-1]
                else:
                    for i in range(len(ts) - 1):
                        if ts[i] <= t <= ts[i + 1]:
                            k = (t - ts[i]) / (ts[i + 1] - ts[i])
                            entry[key] = [a + (b - a) * k for a, b in zip(vals[i], vals[i + 1])]
                            break
        if entry:
            pose[bone] = entry
    return pose


def label(img, text, sub=None):
    d = ImageDraw.Draw(img)
    d.text((10, 8), text, fill=(30, 30, 34))
    if sub:
        d.text((10, 22), sub, fill=(90, 90, 96))
    return img


def views(model, texture, variant, scale, cy, size=(300, 400), pose=None, yaws=((0, "front"), (35, "three-quarter"), (90, "side"), (180, "back"))):
    out = []
    for yaw, lab in yaws:
        im = render(model, texture, variant=variant, yaw=yaw, pitch=8, size=size, scale=scale, center=(0, cy, 1), hide=HIDE, pose=pose, bg=BG)
        out.append((im, lab))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    sal, gol, jak = salamander.build(), golem.build(), jackalope.build()
    hm, htex = human()

    # ---------------------------------------------------------------- lineup (same scale, same ground)
    cells = []
    sc = 7.2
    for m, t, v, name in ((hm, htex, "base", "Vanilla player (scale)"), (sal, tex("salamander", "bloom"), "bloom", "001 Aberrant Flora Salamander"),
                          (gol, tex("golem", "base"), "base", "002 Runic Titan Golem"), (jak, tex("jackalope", "base"), "base", "003 Blood Moon Jackalope")):
        im = render(m, t, variant=v, yaw=28, pitch=6, size=(330, 440), scale=sc, center=(0, 22, 1), hide=HIDE, bg=BG)
        cells.append(label(im, name))
    sheet(cells, cols=4, title="Playable Races - Foundation Release (rendered from the shipped geometry and textures)").save(os.path.join(OUT, "lineup.png"))

    # ---------------------------------------------------------------- salamander
    imgs, labs = [], []
    for im, lab in views(sal, tex("salamander", "base"), "base", 8.0, 19):
        imgs.append(im)
        labs.append(f"stable - {lab}")
    for v, tv in (("bloom", "bloom"), ("dormant", "dormant"), ("predatory", "predatory"), ("rooted", "bloom")):
        im = render(sal, tex("salamander", tv), variant=v, yaw=35, pitch=8, size=(300, 400), scale=8.0, center=(0, 19, 1), hide=HIDE, bg=BG)
        imgs.append(im)
        labs.append(f"{v} (three-quarter)")
    swim = {"root": {"rot": (78, 0, 0), "pos": (0, 6, 10)}, "tail0": {"rot": (-76, 10, 0)}, "tail1": {"rot": (0, 22, 0)}, "tail2": {"rot": (0, 28, 0)}, "tail3": {"rot": (0, 30, 0)},
            "rightArm": {"rot": (0, 0, 60)}, "leftArm": {"rot": (0, 0, -60)}}
    imgs.append(render(sal, tex("salamander", "bloom"), variant="bloom", yaw=70, pitch=30, size=(300, 400), scale=5.0, center=None, hide=HIDE, pose=swim, bg=(200, 222, 236)))
    labs.append("swimming pose + tail wave")
    snare = keyframe_pose("poses.animation.json", "animation.plrace.pose.sal_snare", 0.2)
    snare = {k.replace("rightarm", "rightArm").replace("body", "body"): v for k, v in snare.items()}
    imgs.append(render(sal, tex("salamander", "predatory"), variant="predatory", yaw=40, pitch=8, size=(300, 400), scale=8.0, center=(0, 19, 1), hide=HIDE, pose=snare, bg=BG))
    labs.append("Sundew Snare cast pose")
    sheet(imgs, cols=4, labels=labs, title="001 Aberrant Flora Salamander - turnaround, biological states and poses").save(os.path.join(OUT, "race_001_salamander.png"))

    # ---------------------------------------------------------------- golem
    imgs, labs = [], []
    for im, lab in views(gol, tex("golem", "base"), "base", 6.4, 21):
        imgs.append(im)
        labs.append(f"aligned - {lab}")
    edict = {"rightArm": {"rot": (-172, 0, 8)}, "leftArm": {"rot": (-160, 0, -8)}}
    for v, tv, pose, lab in (("siege", "charged", edict, "Siege: arm-stones fused into a hammer (Titan's Edict)"),
                             ("bastion", "charged", {"rightArm": {"rot": (-76, -26, 0)}, "leftArm": {"rot": (-76, 26, 0)}}, "Bastion: frontal shield wall"),
                             ("arcane", "charged", None, "Arcane: floating rune formation"),
                             ("scattered", "charged", "scatter", "Reassembly: fragments burst apart (t = 0.45 s)"),
                             ("disrupted", "disrupted", None, "Disrupted runes")):
        if pose == "scatter":
            pose = {k: v2 for k, v2 in keyframe_pose("golem.animation.json", "animation.plrace.golem.intro_scattered", 0.45).items()}
        im = render(gol, tex("golem", tv), variant=v, yaw=35, pitch=8, size=(300, 400), scale=5.4 if v in ("scattered", "arcane") else 6.4,
                    center=(0, 22, 1), hide=HIDE, pose=pose, bg=BG)
        imgs.append(im)
        labs.append(lab)
    imgs.append(render(gol, tex("golem", "base"), variant="base", yaw=20, pitch=-10, size=(300, 400), scale=13.0, center=(0, 27, -2), hide=HIDE, bg=(30, 30, 36)))
    labs.append("rune core: 3 rings + suspended crystal")
    imgs.append(render(gol, tex("golem", "base"), variant="base", yaw=35, pitch=8, size=(300, 400), scale=6.4, center=(0, 22, 1), hide=HIDE, bg=BG, accents=True))
    labs.append("armour assimilation accents (tinted in game)")
    sheet(imgs, cols=4, labels=labs, title="002 Runic Titan Golem - turnaround and living-architecture configurations").save(os.path.join(OUT, "race_002_golem.png"))

    # ---------------------------------------------------------------- jackalope
    imgs, labs = [], []
    for im, lab in views(jak, tex("jackalope", "base"), "base", 8.4, 18):
        imgs.append(im)
        labs.append(f"ordinary lunar - {lab}")
    for v, tv, lab, bg in (("hunt", "hunt", "Hunting (Antler Brand / Waltz)", BG), ("awakened", "awakened", "Blood Moon Awakening", (60, 20, 26)),
                           ("awakened_hunt", "awakened", "Blood Moon hunt", (60, 20, 26))):
        imgs.append(render(jak, tex("jackalope", tv), variant=v, yaw=35, pitch=8, size=(300, 400), scale=8.4, center=(0, 18, 1), hide=HIDE, bg=bg))
        labs.append(lab)
    bound = {"rightLeg": {"rot": (28, 0, 0)}, "leftLeg": {"rot": (28, 0, 0)}, "body": {"rot": (-10, 0, 0)},
             "rightArm": {"rot": (36, 0, 10)}, "leftArm": {"rot": (36, 0, -10)}, "r_ear": {"rot": (-22, 0, 0)}, "l_ear": {"rot": (-22, 0, 0)},
             "root": {"pos": (0, 6, 0)}}
    imgs.append(render(jak, tex("jackalope", "base"), variant="base", yaw=80, pitch=6, size=(300, 400), scale=8.4, center=(0, 21, 1), hide=HIDE, pose=bound, bg=BG))
    labs.append("Lunar Bound push-off")
    sheet(imgs, cols=4, labels=labs, title="003 Blood Moon Jackalope - turnaround, hunt and Blood Moon awakening").save(os.path.join(OUT, "race_003_jackalope.png"))

    # ---------------------------------------------------------------- atlases + icons
    atl = []
    for race, names in (("salamander", ("base", "bloom", "dormant", "predatory")), ("golem", ("base", "charged", "disrupted")), ("jackalope", ("base", "hunt", "awakened"))):
        for n in names:
            im = tex(race, n)
            big = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
            bgim = Image.new("RGBA", big.size, (40, 40, 46, 255))
            # show emissive mask: texels with alpha < 1 glow -> composite as opaque for display
            rgb = big.copy()
            rgb.putalpha(Image.eval(big.getchannel("A"), lambda a: 255 if a > 0 else 0))
            bgim.alpha_composite(rgb)
            atl.append(bgim.convert("RGB"))
    sheet(atl, cols=4, labels=[f"{r}_{n}" for r, ns in (("salamander", ("base", "bloom", "dormant", "predatory")), ("golem", ("base", "charged", "disrupted")), ("jackalope", ("base", "hunt", "awakened"))) for n in ns],
          title="Procedural texture atlases (per-face UV, 2 px per model unit)").save(os.path.join(OUT, "texture_atlases.png"))
    ic = []
    for p in ("ui/portrait_001", "ui/portrait_002", "ui/portrait_003", "items/crest_salamander", "items/crest_golem", "items/crest_jackalope",
              "items/focus_salamander", "items/focus_golem", "items/focus_jackalope", "items/codex"):
        im = Image.open(os.path.join(RP, TEX, p + ".png")).convert("RGBA").resize((160, 160), Image.NEAREST)
        bgim = Image.new("RGBA", (160, 160), (52, 52, 58, 255))
        bgim.alpha_composite(im)
        ic.append(bgim.convert("RGB"))
    sheet(ic, cols=5, labels=["portrait 001", "portrait 002", "portrait 003", "crest 001", "crest 002", "crest 003", "Dewheart focus", "Rune Keystone focus", "Moonbone focus", "Lineage Codex"],
          title="Selection portraits and item icons").save(os.path.join(OUT, "ui_and_items.png"))
    pk = Image.open(os.path.join(RP, "pack_icon.png"))
    pk.save(os.path.join(OUT, "pack_icon.png"))
    print("previews written to", OUT)


if __name__ == "__main__":
    main()
