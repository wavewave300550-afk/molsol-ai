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
from kit.render import render, render_scene, sheet  # noqa: E402
from kit.tex import hx  # noqa: E402
from models import bathyas, dinosauroid, golem, jackalope, nurariten, octamyces, salamander, spaghetti, xenentoma  # noqa: E402

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


def kpose(anim_file, anim_name, t):
    """Keyframe pose with player-skeleton bone names fixed up for the renderer."""
    fix = {"rightarm": "rightArm", "leftarm": "leftArm", "rightleg": "rightLeg", "leftleg": "leftLeg"}
    return {fix.get(k, k): v for k, v in keyframe_pose(anim_file, anim_name, t).items()}


def expansion(xen, fsm, nur):
    """Expansion 01 sheets: races 004-006, their helper entities and the unique ultimate."""
    # ---------------------------------------------------------------- 004 xenentoma
    imgs, labs = [], []
    for im, lab in views(xen, tex("xenentoma", "base"), "base", 7.4, 15):
        imgs.append(im)
        labs.append(f"base - {lab}")
    for v, tv, lab in (("survey", "sense", "Foretarsal Survey: sensory limbs raised"), ("glide", "base", "Interstitial Glide: flattened"),
                       ("surge", "sense", "Anamorphic Surge: segments extended"), ("teneral", "teneral", "teneral (fresh after Ecdysis)")):
        imgs.append(render(xen, tex("xenentoma", tv), variant=v, yaw=55 if v != "surge" else 70, pitch=10, size=(300, 400), scale=6.4 if v == "surge" else 7.4,
                           center=(0, 13 if v == "glide" else 15, 1), hide=HIDE, bg=BG))
        labs.append(lab)
    sheet(imgs, cols=4, labels=labs, title="004 Xenentoma - turnaround and configurations (eyeless; six limbs; twelve abdominal segments)").save(os.path.join(OUT, "race_004_xenentoma.png"))

    # ---------------------------------------------------------------- 005 flying spaghetti monster
    imgs, labs = [], []
    for im, lab in views(fsm, tex("spaghetti", "base"), "base", 7.4, 15):
        imgs.append(im)
        labs.append(f"base - {lab}")
    for v, tv, lab, sc, cy in (("rigid", "dente", "Al Dente Reversal: rigid lattice", 7.4, 15), ("detached", "base", "meatballs away (Meatball Ricochet)", 7.4, 15),
                               ("revelation", "holy", "The Great Pasta Revelation", 3.6, 20), ("brittle", "burnt", "brittle (fire)", 7.4, 15)):
        imgs.append(render(fsm, tex("spaghetti", tv), variant=v, yaw=35, pitch=14 if v == "revelation" else 8, size=(300, 400), scale=sc, center=(0, cy, 1), hide=HIDE, bg=BG))
        labs.append(lab)
    sheet(imgs, cols=4, labels=labs, title="005 Flying Spaghetti Monster - turnaround and configurations").save(os.path.join(OUT, "race_005_spaghetti.png"))

    # ---------------------------------------------------------------- 006 nurariten
    imgs, labs = [], []
    for im, lab in views(nur, tex("nurariten", "base"), "base", 6.6, 20):
        imgs.append(im)
        labs.append(f"base - {lab}")
    edict = kpose("poses.animation.json", "animation.plrace.pose.nur_edict", 0.4)
    final = kpose("poses.animation.json", "animation.plrace.pose.nur_final", 0.7)
    for v, tv, pose, lab, sc, cy, bg in (("nocturne", "nocturne", None, "Nocturne Radiance (night)", 6.6, 20, (34, 38, 56)),
                                         ("edict", "radiant", edict, "Edict of the Lowered Gaze", 6.6, 20, BG),
                                         ("court", "radiant", None, "The Uninvited Temple: the court unfolds", 5.2, 22, BG),
                                         ("throne", "radiant", final, "The Throne Without Permission / Final Edict", 4.6, 24, BG)):
        imgs.append(render(nur, tex("nurariten", tv), variant=v, yaw=30, pitch=8, size=(300, 400), scale=sc, center=(0, cy, 1), hide=HIDE, pose=pose, bg=bg))
        labs.append(lab)
    sheet(imgs, cols=4, labels=labs, title="006 Nurariten [UNIQUE] - the Uninvited Sovereign: turnaround and configurations").save(os.path.join(OUT, "race_006_nurariten.png"))

    # ---------------------------------------------------------------- helper entities
    def etex(race, name):
        return Image.open(os.path.join(RP, TEX, race, f"{name}.png")).convert("RGBA")
    imgs, labs = [], []
    imgs.append(render(xen, tex("xenentoma", "exuvia"), variant="exuvia", yaw=40, pitch=10, size=(300, 300), scale=6.0, center=(0, 13, 1), hide=HIDE, bg=BG))
    labs.append("004 shed exuvia (decoy)")
    imgs.append(render(spaghetti.build_meatball(), etex("spaghetti", "meatball"), yaw=30, pitch=10, size=(300, 300), scale=13.0, center=None, bg=BG))
    labs.append("005 detached meatball")
    imgs.append(render(nurariten.build_gate(), etex("nurariten", "celestial_gate"), yaw=20, pitch=8, size=(300, 300), scale=4.6, center=(0, 25, 0), bg=BG))
    labs.append("006 celestial gate (x3.6 in the sky)")
    imgs.append(render(nurariten.build_heralds(), etex("nurariten", "herald"), yaw=25, pitch=8, size=(300, 300), scale=11.0, center=(0, 6, 0), bg=BG))
    labs.append("006 heralds with the decree")
    imgs.append(render(nurariten.build_procession(), etex("nurariten", "procession"), yaw=35, pitch=14, size=(300, 300), scale=6.4, center=(0, 7, 0), bg=BG))
    labs.append("006 one procession column (12 attendants)")
    sheet(imgs, cols=5, labels=labs, title="Helper entities (script-owned, no AI, self-despawning)").save(os.path.join(OUT, "helper_entities.png"))

    # ---------------------------------------------------------------- HYAKUTEN CHUKO staged as in game (stage III-IV)
    B = 16.0
    items = [(nur, tex("nurariten", "radiant"), "throne", final, (0, 0, 0), 0, 1.0, HIDE),
             (nurariten.build_gate(), etex("nurariten", "celestial_gate"), None, None, (0, 2.5 * B, -9 * B), 0, 3.6, []),
             (nurariten.build_heralds(), etex("nurariten", "herald"), None, None, (0, 1.4 * B, -2.6 * B), 0, 2.2, [])]
    col = nurariten.build_procession()
    ctex = etex("nurariten", "procession")
    import math
    for k in range(8):
        ph = math.radians(k * 45 + 22.5)
        t = (-math.sin(ph), 0, math.cos(ph))
        items.append((col, ctex, None, None, (8.4 * B * math.cos(ph), 0, 8.4 * B * math.sin(ph)), math.degrees(math.atan2(-t[0], -t[2])), 2.0, []))

    def court(img, ss, proj):
        d = ImageDraw.Draw(img, "RGBA")
        for rad, colr, w in ((11 * B, (255, 214, 120, 160), 3), (12 * B, (255, 230, 170, 90), 2)):
            pts = [proj((rad * math.cos(math.radians(a)), 0.2, rad * math.sin(math.radians(a)))) for a in range(0, 361, 4)]
            d.line(pts, fill=colr, width=w * ss)
    shot = render_scene(items, yaw=120, pitch=18, size=(1100, 700), scale=1.55, center=(0, 60, -40), bg=(238, 226, 196), backdrop=court)
    ImageDraw.Draw(shot).text((14, 10), "HYAKUTEN CHUKO - stages III-IV: the gate in the sky, the heralds, eight columns (96 attendants) circling the throne", fill=(60, 40, 20))
    shot.save(os.path.join(OUT, "hyakuten_chuko.png"))


WHITE = (255, 255, 255)
EXP02 = {  # race -> (module, title, scale, centre y, texture per variant)
    "dinosauroid": (dinosauroid, "007 The Unknown Dinosauroid - the taxonomic impossibility", 7.0, 18),
    "bathyas": (bathyas, "008 Bathyas, the Sun-Impaled [UNIQUE] - impaled and unshackled", 6.6, 19),
    "octamyces": (octamyces, "009 Octamyces Undecimus - the witness of eleven realities", 7.0, 18),
}


def expansion02():
    """White-background turnarounds (front / three-quarter / side / back) and every form of races 007-009."""
    for k, (race, (mod, title, sc, cy)) in enumerate(EXP02.items()):
        m = mod.build()
        imgs, labs = [], []
        for yaw, lab in ((0, "front"), (35, "three-quarter"), (90, "side"), (180, "back")):
            imgs.append(render(m, tex(race, mod.VARIANT_TEXTURE["base"]), variant="base", yaw=yaw, pitch=6, size=(300, 400), scale=sc,
                               center=(0, cy, 1), hide=HIDE, bg=WHITE))
            labs.append(f"base - {lab}")
        for v in mod.VARIANTS:
            if v == "base":
                continue
            imgs.append(render(m, tex(race, mod.VARIANT_TEXTURE[v]), variant=v, yaw=32, pitch=6, size=(300, 400), scale=sc,
                               center=(0, cy, 1), hide=HIDE, bg=WHITE))
            labs.append(f"{v}")
        sheet(imgs, cols=4, labels=labs, title=title, bg=WHITE).save(os.path.join(OUT, f"race_00{7 + k}_{race}.png"))
    sw = bathyas.build_sword()
    from kit.tex import paint
    stex = paint(sw, bathyas.sword_materials(), bathyas.TEXTURES["base"]) if hasattr(bathyas, "sword_materials") else None
    if stex is not None:
        imgs = [render(sw, stex, yaw=y, pitch=8, size=(300, 400), scale=8.0, center=(0, 15, 0), bg=WHITE) for y in (0, 40, 90)]
        sheet(imgs, cols=3, labels=["the Impaled Sun - front", "three-quarter", "side"], title="008 Bathyas - the solar sword (embedded in the chest; drawn as THE IMPALED SUN)",
              bg=WHITE).save(os.path.join(OUT, "race_008_sword.png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    sal, gol, jak = salamander.build(), golem.build(), jackalope.build()
    hm, htex = human()

    # ---------------------------------------------------------------- lineup (same scale, same ground)
    cells = []
    sc = 7.2
    xen, fsm, nur = xenentoma.build(), spaghetti.build(), nurariten.build()
    for m, t, v, name in ((hm, htex, "base", "Vanilla player (scale)"), (sal, tex("salamander", "bloom"), "bloom", "001 Aberrant Flora Salamander"),
                          (gol, tex("golem", "base"), "base", "002 Runic Titan Golem"), (jak, tex("jackalope", "base"), "base", "003 Blood Moon Jackalope"),
                          (xen, tex("xenentoma", "base"), "base", "004 Xenentoma"), (fsm, tex("spaghetti", "base"), "base", "005 Flying Spaghetti Monster"),
                          (nur, tex("nurariten", "base"), "base", "006 Nurariten [UNIQUE]"),
                          (dinosauroid.build(), tex("dinosauroid", "base"), "base", "007 The Unknown Dinosauroid"),
                          (bathyas.build(), tex("bathyas", "base"), "base", "008 Bathyas [UNIQUE]"),
                          (octamyces.build(), tex("octamyces", "base"), "base", "009 Octamyces Undecimus")):
        im = render(m, t, variant=v, yaw=28, pitch=6, size=(330, 440), scale=sc, center=(0, 22, 1), hide=HIDE, bg=BG)
        cells.append(label(im, name))
    sheet(cells, cols=4, title="Playable Races - nine lineages at the same scale (rendered from the shipped geometry and textures)").save(os.path.join(OUT, "lineup.png"))

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

    expansion(xen, fsm, nur)
    expansion02()

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
    keys = ("salamander", "golem", "jackalope", "xenentoma", "spaghetti", "nurariten", "dinosauroid", "bathyas", "octamyces")
    for p in [f"ui/portrait_00{k}" for k in range(1, 10)] + [f"items/crest_{k}" for k in keys] + [f"items/focus_{k}" for k in keys] + ["items/codex", "items/sun_sword"]:
        im = Image.open(os.path.join(RP, TEX, p + ".png")).convert("RGBA").resize((160, 160), Image.NEAREST)
        bgim = Image.new("RGBA", (160, 160), (52, 52, 58, 255))
        bgim.alpha_composite(im)
        ic.append(bgim.convert("RGB"))
    sheet(ic, cols=9, labels=[f"portrait 00{k}" for k in range(1, 10)] + [f"crest 00{k}" for k in range(1, 10)]
          + ["Dewheart focus", "Rune Keystone focus", "Moonbone focus", "Sensillum focus", "Holy Colander focus", "Mandate Shaku focus",
             "Fossil Quill focus", "Abyssal Hilt focus", "Undecimal Lens focus", "Lineage Codex", "The Impaled Sun"],
          title="Selection portraits and item icons").save(os.path.join(OUT, "ui_and_items.png"))
    pk = Image.open(os.path.join(RP, "pack_icon.png"))
    pk.save(os.path.join(OUT, "pack_icon.png"))
    print("previews written to", OUT)


if __name__ == "__main__":
    main()
