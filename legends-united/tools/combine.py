"""
Build Legends United: one Behavior Pack + one Resource Pack from the three released add-ons.

  python3 tools/combine.py

Inputs are the released .mcaddon files of the three add-ons in this repository (read only; the
original projects are never modified). Each host keeps its own files; scripts move into
scripts/<host>/, language files and item_texture.json are merged, any other path collision is an
error. Script patches (tools/patches.py) add the rivalry between hosts and the spawn-egg hook.
"""
import json
import os
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)
sys.path.insert(0, HERE)
import patches  # noqa: E402
import eggs as eggmod  # noqa: E402

# No on-screen text: every chat line, title, subtitle and action-bar text the hosts send becomes a
# no-op (`x.__quiet?.(...)` evaluates its arguments and does nothing). Menus the player opens
# (codex, bestiary) and replies to typed commands are unaffected.
QUIET = [(".sendMessage(", ".__quiet?.("),
         ("onScreenDisplay.setActionBar(", "onScreenDisplay?.__quiet?.("),
         ("onScreenDisplay?.setTitle(", "onScreenDisplay?.__quiet?.("),
         ("onScreenDisplay.setTitle(", "onScreenDisplay?.__quiet?.("),
         ("onScreenDisplay.updateSubtitle(", "onScreenDisplay?.__quiet?.(")]


def silence(scripts):
    n = 0
    for dp, _, fs in os.walk(scripts):
        for f in fs:
            if not f.endswith(".js"):
                continue
            path = os.path.join(dp, f)
            src = open(path, encoding="utf-8").read()
            out = src
            for a, b in QUIET:
                n += out.count(a)
                out = out.replace(a, b)
            for a in ("sendMessage(", "setActionBar(", "setTitle(", "updateSubtitle("):
                if a in out:
                    raise SystemExit(f"text output left in {path}: {a}")
            if out != src:
                open(path, "w", encoding="utf-8").write(out)
    return n

VERSION = [1, 1, 0]
NAME = "Clash of Legends"
HOSTS = [  # key, release, BP folder, RP folder, title
    ("dim11", "eleventh-addon/dist/Eleventh_Dimension.mcaddon", "Dim11_BP", "Dim11_RP", "Intelligent Beings of the 11th Dimension"),
    ("fb", "final-bosses/dist/Five_Final_Bosses.mcaddon", "FinalBosses_BP", "FinalBosses_RP", "Five Final Bosses"),
    ("legends", "legendary-remaster/dist/Legendary_and_Divine_Beings_Remastered.mcaddon", "Legends_BP", "Legends_RP", "Legendary & Divine Beings"),
]
UUID = {"bp": "8f8b51af-2416-4983-adab-54cd58085862", "bp_data": "cda777fb-618f-4408-8da5-09e61d1b17f8",
        "bp_script": "33ab7ade-a9c3-46c0-8da8-062dc1a1196d", "rp": "3607d547-1bd2-4f81-847b-b6610c3c8d71"}
BUILD = os.path.join(ROOT, "build")
BP = os.path.join(BUILD, "Clash_of_Legends_BP")
RP = os.path.join(BUILD, "Clash_of_Legends_RP")
DIST = os.path.join(ROOT, "dist", "Clash_of_Legends.mcaddon")

# Spawn eggs for the Legendary bosses (the other hosts already ship theirs).
LEGEND_EGGS = {
    "taotie": ("#3b2613", "#ff7a20", "Taotie, the Devouring Maw"),
    "nidhogg": ("#1d2619", "#45e83a", "Níðhöggr"),
    "hanuman": ("#f4eee0", "#d8263a", "Hanuman"),
    "alicorn": ("#f6f0ff", "#b58cff", "the Alicorn"),
    "tenko": ("#fffaf0", "#3aa8ff", "Tenko, the Ten-Tailed Fox"),
    "logos": ("#fff6d0", "#ffc640", "The Word of God"),
}
SKIP = {"manifest.json", "pack_icon.png", "texts/en_US.lang", "texts/languages.json", "textures/item_texture.json"}


def extract(rel, key):
    out = os.path.join(BUILD, "in", key)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    with zipfile.ZipFile(os.path.join(REPO, rel)) as z:
        z.extractall(out)
    return out


def copy_pack(src, dst, key, is_bp, owners):
    for dp, _, fs in os.walk(src):
        for f in fs:
            rel = os.path.relpath(os.path.join(dp, f), src).replace(os.sep, "/")
            if rel in SKIP:
                continue
            out = f"scripts/{key}/{rel[len('scripts/'):]}" if is_bp and rel.startswith("scripts/") else rel
            if out in owners:
                raise SystemExit(f"collision: {out} ({owners[out]} and {key})")
            owners[out] = key
            os.makedirs(os.path.dirname(os.path.join(dst, out)), exist_ok=True)
            shutil.copy2(os.path.join(dp, f), os.path.join(dst, out))


def merged_lang(srcs, extra=""):
    parts = []
    for key, path in srcs:
        if os.path.exists(path):
            parts.append(f"## ---- {key}\n" + open(path, encoding="utf-8").read().strip() + "\n")
    return "\n".join(parts) + extra


def merged_item_textures(paths):
    data = {}
    for key, path in paths:
        if not os.path.exists(path):
            continue
        td = json.load(open(path, encoding="utf-8")).get("texture_data", {})
        for k, v in td.items():
            if k in data and data[k] != v:
                raise SystemExit(f"item texture clash: {k}")
            data[k] = v
    return {"resource_pack_name": "clash_of_legends", "texture_name": "atlas.items", "texture_data": data}


def manifests():
    bp = {
        "format_version": 2,
        "header": {"name": NAME, "description": "§614 bosses, one battlefield - every boss fights every boss.\n§711th Dimension · Final Bosses · Legendary Beings",
                   "uuid": UUID["bp"], "version": VERSION, "min_engine_version": [1, 26, 60]},
        "modules": [{"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
                    {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION, "entry": "scripts/main.js"}],
        "dependencies": [{"uuid": UUID["rp"], "version": VERSION},
                         {"module_name": "@minecraft/server", "version": "2.11.0"},
                         {"module_name": "@minecraft/server-ui", "version": "2.3.0"}],
    }
    rp = {
        "format_version": 2,
        "header": {"name": NAME, "description": "Models, textures, effects and spawn eggs of Clash of Legends", "uuid": UUID["rp"], "version": VERSION, "min_engine_version": [1, 26, 60]},
        "modules": [{"type": "resources", "uuid": "a31a8e62-6d36-4c3a-9d43-3f5f0b2d6e71", "version": VERSION}],
        "dependencies": [{"uuid": UUID["bp"], "version": VERSION}],
    }
    return bp, rp


def icon(paths, out):
    from PIL import Image
    ims = [Image.open(p).convert("RGBA").resize((128, 128)) for p in paths if os.path.exists(p)]
    W = 256
    canvas = Image.new("RGBA", (W, W), (14, 10, 24, 255))
    spots = [(0, 0), (128, 0), (64, 128)]
    for im, s in zip(ims, spots):
        canvas.alpha_composite(im, s)
    canvas.save(out)


def legend_eggs():
    lines = []
    for key, (base, over, title) in LEGEND_EGGS.items():
        bpf = os.path.join(BP, "entities", "legends", f"{key}.json")
        d = json.load(open(bpf, encoding="utf-8"))
        d["minecraft:entity"]["description"]["is_spawnable"] = True
        json.dump(d, open(bpf, "w", encoding="utf-8"), indent=2)
        rpf = os.path.join(RP, "entity", "legends", f"{key}.entity.json")
        c = json.load(open(rpf, encoding="utf-8"))
        json.dump(c, open(rpf, "w", encoding="utf-8"), indent=2)
    return ""


def zipdir(z, folder, arc):
    for dp, _, fs in os.walk(folder):
        for f in sorted(fs):
            full = os.path.join(dp, f)
            z.write(full, os.path.join(arc, os.path.relpath(full, folder)))


def main():
    for d in (BP, RP):
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d)
    owners_bp, owners_rp = {}, {}
    ins = {}
    for key, rel, bpn, rpn, _ in HOSTS:
        src = extract(rel, key)
        ins[key] = (os.path.join(src, bpn), os.path.join(src, rpn))
        copy_pack(ins[key][0], BP, key, True, owners_bp)
        copy_pack(ins[key][1], RP, key, False, owners_rp)
    # shared scripts and entry point
    shutil.copytree(os.path.join(ROOT, "src", "scripts"), os.path.join(BP, "scripts"), dirs_exist_ok=True)
    n = patches.apply(os.path.join(BP, "scripts"))
    quiet = silence(os.path.join(BP, "scripts"))
    eggs = legend_eggs()
    for pack, idx in ((BP, 0), (RP, 1)):
        os.makedirs(os.path.join(pack, "texts"), exist_ok=True)
        lang = merged_lang([(k, os.path.join(ins[k][idx], "texts", "en_US.lang")) for k in ins], eggs if pack is RP else "")
        open(os.path.join(pack, "texts", "en_US.lang"), "w", encoding="utf-8").write(lang)
        json.dump(["en_US"], open(os.path.join(pack, "texts", "languages.json"), "w"))
    # spawn eggs: one portrait egg per boss, named after the boss and its add-on
    egg_tex, portraits = eggmod.write_eggs(RP)
    for eid in eggmod.BOSSES:
        host, k = eid.split(":")
        rpf = os.path.join(RP, "entity", host, f"{k}.entity.json")
        c = json.load(open(rpf, encoding="utf-8"))
        c["minecraft:client_entity"]["description"]["spawn_egg"] = {"texture": f"clash_egg_{eggmod.key(eid)}", "texture_index": 0}
        json.dump(c, open(rpf, "w", encoding="utf-8"), indent=2)
    lang_path = os.path.join(RP, "texts", "en_US.lang")
    lines = [ln for ln in open(lang_path, encoding="utf-8").read().splitlines() if not ln.startswith("item.spawn_egg.entity.")]
    open(lang_path, "w", encoding="utf-8").write("\n".join(lines + ["## ---- spawn eggs"] + eggmod.lang_lines()) + "\n")
    for pack in (BP, RP):
        eggmod.pack_icon(portraits, os.path.join(pack, "pack_icon.png"))
    eggmod.pack_icon(portraits, os.path.join(ROOT, "docs", "pack_icon.png"))
    eggmod.showcase(portraits, os.path.join(ROOT, "docs", "eggs.png"))
    item_tex = merged_item_textures([(k, os.path.join(ins[k][1], "textures", "item_texture.json")) for k in ins])
    item_tex["texture_data"].update(egg_tex)
    json.dump(item_tex,
              open(os.path.join(RP, "textures", "item_texture.json"), "w"), indent=1)
    bpm, rpm = manifests()
    json.dump(bpm, open(os.path.join(BP, "manifest.json"), "w"), indent=2)
    json.dump(rpm, open(os.path.join(RP, "manifest.json"), "w"), indent=2)
    os.makedirs(os.path.dirname(DIST), exist_ok=True)
    with zipfile.ZipFile(DIST, "w", zipfile.ZIP_DEFLATED) as z:
        zipdir(z, BP, "Clash_of_Legends_BP")
        zipdir(z, RP, "Clash_of_Legends_RP")
    print(f"{len(owners_bp)} BP files, {len(owners_rp)} RP files, {n} script patches, {quiet} on-screen texts removed")
    print(f"wrote {DIST} {os.path.getsize(DIST) // 1024} KB")


if __name__ == "__main__":
    main()
