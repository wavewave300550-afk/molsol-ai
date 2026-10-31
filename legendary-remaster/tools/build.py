"""
Build the remastered Legendary & Divine Beings add-on.

src/BP          behaviour pack sources (scripts reviewed + remastered)
src/RP_static   resource-pack files kept from the original (texts, particles, item textures)
tools/boss_*.py remastered models + textures + animations + client entities (generated here)
extracted/      the untouched original (read as data only) - used for entities not yet remastered

Output: build/Legends_BP, build/Legends_RP, dist/Legendary_and_Divine_Beings_Remastered.mcaddon
"""
import importlib
import json
import os
import re
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
ORIG = os.path.join(ROOT, "extracted")
BUILD = os.path.join(ROOT, "build")
BP = os.path.join(BUILD, "Legends_BP")
RP = os.path.join(BUILD, "Legends_RP")
DIST = os.path.join(ROOT, "dist")
VERSION = [2, 0, 0]

MODULES = ["boss_taotie", "boss_nidhogg", "boss_hanuman", "boss_alicorn", "boss_tenko", "boss_logos", "choir_seraph", "choir_cherub", "choir_ophan", "props"]                 # remastered entities (module per entity family)
ORIGINAL_ENTITIES = []      # every entity is remastered or kept as-is in src/RP_static (ding, root_spike, ...)

COMMON_PRE = [
    "variable.act = query.property('legends:act');",
    "variable.ph = query.property('legends:phase');",
    "variable.calm = math.lerp(variable.calm ?? 1.0, variable.act == 0 ? 1.0 : 0.15, 0.14);",
    "variable.mv = math.lerp(variable.mv ?? 0.0, query.property('legends:move'), 0.2);",
    "variable.dist = (variable.dist ?? 0.0) + query.delta_time * variable.mv * 6.0;",
    "variable.t = (variable.t ?? 0.0) + query.delta_time * (1.0 + 0.2 * math.max(0, variable.ph - 1));",
    "variable.fx = query.property('legends:fx');",
    "variable.ova = variable.fx == 0 ? 0.0 : (0.30 + math.sin(query.life_time * 540.0) * 0.12);",
    "variable.ovr = variable.fx == 3 ? 0.35 : 1.0;",
    "variable.ovg = variable.fx == 2 ? 0.25 : (variable.fx == 3 ? 0.65 : (variable.fx == 1 || variable.fx == 4 ? 0.82 : 1.0));",
    "variable.ovb = variable.fx == 2 ? 0.2 : (variable.fx == 3 ? 1.0 : (variable.fx == 1 || variable.fx == 4 ? 0.3 : 1.0));",
]
PROP_PRE = ["variable.act = query.property('legends:act');", "variable.t = (variable.t ?? 0.0) + query.delta_time;"]


def wj(path, data, compact=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if compact:
            json.dump(data, f, separators=(",", ":"))
        else:
            json.dump(data, f, indent=1)


def copy_tree(a, b):
    shutil.copytree(a, b, dirs_exist_ok=True)


# --------------------------------------------------------------------------- entity generation

def gen_entity(mod, built_acts):
    import lmat
    from modelkit import deflicker, island_report
    key = mod.KEY
    m = mod.build()
    left = deflicker(m)
    isl = island_report(m)
    if left or isl:
        print(f"  ! {key}: zfight left {left}, islands {isl}")
    tex_dir = os.path.join(RP, "textures", "entity", "legends")
    os.makedirs(tex_dir, exist_ok=True)
    variants = getattr(mod, "VARIANTS", {"default": "default"})
    for vname, tkey in variants.items():
        lmat.VARIANT["name"] = vname
        img = m.paint()
        suffix = "" if tkey == "default" else f"_{tkey}"
        img.save(os.path.join(tex_dir, f"{key}{suffix}.png"))
    lmat.VARIANT["name"] = "default"
    m.paint()
    cfg = mod.entity_cfg()
    bw, bh, oy = cfg["bounds"]
    geo_id = m.identifier
    wj(os.path.join(RP, "models", "entity", "legends", f"{key}.geo.json"), m.geometry_json(bw, bh, oy, glow=False), compact=True)
    has_glow = any(c.glow for b in m.bones for c in b.cubes)
    if has_glow:
        wj(os.path.join(RP, "models", "entity", "legends", f"{key}.glow.geo.json"),
           m.geometry_json(bw, bh, oy, glow=True, identifier=geo_id + ".glow"), compact=True)
    # animations
    anims = {}
    for name, a in mod.loops().items():
        anims[f"animation.legends.{key}.{name}"] = a
    acts = mod.acts() if hasattr(mod, "acts") and callable(getattr(mod, "acts")) else []
    for a in acts:
        anims[f"animation.legends.{key}.act.{a.name}"] = a.to_json()
    wj(os.path.join(RP, "animations", "legends", f"{key}.animation.json"), {"format_version": "1.8.0", "animations": anims}, compact=True)
    # act controller
    if acts:
        states = {"default": {"transitions": [{a.name: f"variable.act == {i + 1}"} for i, a in enumerate(acts)]}}
        for i, a in enumerate(acts):
            states[a.name] = {"animations": [f"a_{a.name}"], "blend_transition": cfg.get("blend", 0.18),
                              "transitions": [{"default": f"variable.act != {i + 1}"}]}
        wj(os.path.join(RP, "animation_controllers", "legends", f"{key}.ac.json"),
           {"format_version": "1.10.0", "animation_controllers": {f"controller.animation.legends.{key}.act": {"initial_state": "default", "states": states}}})
        built_acts[key] = {a.name: {"id": i + 1, "ticks": a.ticks, "marks": a.marks} for i, a in enumerate(acts)}
    # render controllers
    vis = [{"*": True}] + cfg.get("visibility", [])
    solid = {"geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "part_visibility": vis}
    if cfg.get("skins"):
        solid["arrays"] = {"textures": {"Array.skins": cfg["skins"]}}
        solid["textures"] = [cfg["texture_expr"]]
    else:
        solid["textures"] = ["Texture.default"]
    if cfg.get("overlay", True):
        solid["overlay_color"] = {"r": "variable.ovr", "g": "variable.ovg", "b": "variable.ovb", "a": "variable.ova"}
    rcs = {f"controller.render.legends.{key}": solid}
    if has_glow:
        rcs[f"controller.render.legends.{key}.glow"] = {"geometry": "Geometry.glow", "materials": [{"*": "Material.glow"}],
                                                       "textures": ["Texture.default"], "part_visibility": vis}
    wj(os.path.join(RP, "render_controllers", "legends", f"{key}.rc.json"), {"format_version": "1.8.0", "render_controllers": rcs})
    # client entity
    anim_map = {name: f"animation.legends.{key}.{name}" for name in mod.loops()}
    for a in acts:
        anim_map[f"a_{a.name}"] = f"animation.legends.{key}.act.{a.name}"
    if acts:
        anim_map["ctrl_act"] = f"controller.animation.legends.{key}.act"
    desc = {
        "identifier": f"legends:{key}",
        "materials": {"default": cfg.get("material", "entity_alphatest"), "glow": "entity_beam_additive"},
        "textures": cfg["textures"],
        "geometry": {"default": geo_id, **({"glow": geo_id + ".glow"} if has_glow else {})},
        "animations": anim_map,
        "scripts": {"scale": str(cfg["scale"]), "pre_animation": (PROP_PRE if cfg.get("prop") else COMMON_PRE) + cfg.get("pre", []),
                    "animate": cfg["animate"]},
        "render_controllers": list(rcs.keys()),
    }
    if cfg.get("spawn_egg"):
        desc["spawn_egg"] = cfg["spawn_egg"]
    wj(os.path.join(RP, "entity", "legends", f"{key}.entity.json"), {"format_version": "1.10.0", "minecraft:client_entity": {"description": desc}})
    extra = getattr(mod, "extra_entities", None)
    if extra:
        extra(RP, m, built_acts)
    st = m.stats()
    print(f"  {key}: {st['bones']} bones, {st['cubes']} cubes ({st['glow_cubes']} glow), texture {st['texture_px']}, {len(acts)} acts")
    return key


def copy_original(key):
    o = os.path.join(ORIG, "Legends_RP")
    pairs = [
        (f"models/entity/legends/{key}.geo.json", None),
        (f"animations/legends/{key}.animation.json", None),
        (f"animation_controllers/legends/{key}.ac.json", None),
        (f"entity/legends/{key}.entity.json", None),
        (f"render_controllers/legends/{key}.rc.json", None),
    ]
    for rel, _ in pairs:
        a = os.path.join(o, rel)
        if os.path.exists(a):
            b = os.path.join(RP, rel)
            os.makedirs(os.path.dirname(b), exist_ok=True)
            shutil.copyfile(a, b)
    tdir = os.path.join(o, "textures", "entity", "legends")
    for fn in os.listdir(tdir):
        if fn == f"{key}.png" or re.fullmatch(rf"{re.escape(key)}_v\d+\.png", fn) or (key == "tenko" and fn == "tenko_illusion.png"):
            os.makedirs(os.path.join(RP, "textures", "entity", "legends"), exist_ok=True)
            shutil.copyfile(os.path.join(tdir, fn), os.path.join(RP, "textures", "entity", "legends", fn))


def data_constants():
    """Non-act constants of generated/data.js (kept from the source copy in src/BP)."""
    txt = open(os.path.join(SRC, "BP", "scripts", "generated", "data.js"), encoding="utf-8").read()
    return [ln for ln in txt.splitlines() if ln.startswith("export const") and "_ACTS" not in ln]


def write_data_js(acts_by_key, rest):
    lines = ["// AUTO-GENERATED by tools/build.py - do not edit.",
             "// Act ids / lengths / impact marks (ticks) shared with the resource pack animations."]
    order = ["taotie", "nidhogg", "hanuman", "alicorn", "tenko", "logos", "seraph", "cherub", "ophan"]
    for k in order:
        lines.append(f"export const {k.upper()}_ACTS = {json.dumps(acts_by_key[k], separators=(', ', ': '))};")
    lines += rest
    path = os.path.join(BP, "scripts", "generated", "data.js")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def bump_manifest(path, name_suffix=True):
    d = json.load(open(path, encoding="utf-8"))
    d["header"]["version"] = VERSION
    for mdl in d.get("modules", []):
        mdl["version"] = VERSION
    for dep in d.get("dependencies", []):
        if "uuid" in dep:
            dep["version"] = VERSION
    wj(path, d)


def set_lang(path):
    txt = open(path, encoding="utf-8").read()
    txt = re.sub(r"pack\.name=.*", "pack.name=Legendary & Divine Beings - Remastered", txt)
    txt = re.sub(r"pack\.description=.*", "pack.description=Remastered: six god-tier extra bosses - Taotie, Nidhogg, Hanuman, Alicorn, the Ten-Tailed Fox and The Word of God with its Choir.", txt)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)


def zip_dir(z, folder, arc_root):
    for dp, _, files in os.walk(folder):
        for fn in sorted(files):
            full = os.path.join(dp, fn)
            z.write(full, os.path.join(arc_root, os.path.relpath(full, folder)))


def main():
    sys.path.insert(0, HERE)
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    copy_tree(os.path.join(SRC, "BP"), BP)
    copy_tree(os.path.join(SRC, "RP_static"), RP)
    bump_manifest(os.path.join(BP, "manifest.json"))
    bump_manifest(os.path.join(RP, "manifest.json"))
    for p in (os.path.join(BP, "texts", "en_US.lang"), os.path.join(RP, "texts", "en_US.lang")):
        set_lang(p)
    rest = data_constants()
    built_acts = {}
    done = set()
    for name in MODULES:
        mod = importlib.import_module(name)
        print(f"building {name}")
        for ent in getattr(mod, "ENTITIES", [mod]):
            done.add(gen_entity(ent, built_acts))
        for k in getattr(mod, "ALSO_PROVIDES", []):
            done.add(k)
    for key in ORIGINAL_ENTITIES:
        if key not in done:
            copy_original(key)
    write_data_js(built_acts, rest)
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, "Legendary_and_Divine_Beings_Remastered.mcaddon")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        zip_dir(z, BP, "Legends_BP")
        zip_dir(z, RP, "Legends_RP")
    print("wrote", out, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main()
