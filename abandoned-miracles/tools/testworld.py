"""
Build the demonstration world: dist/The_Abandoned_Miracles_Test_World.mcworld

    python3 tools/testworld.py

The world is a flat survival world with the add-on applied plus a tiny,
commands-only "test world kit" behaviour pack. On first load the kit raises a
central plaza and the four demonstration arenas with `structure load`, sets
calm game rules and hands every arriving player the Codex and the four Seals.

Nothing here hand-writes chunk data: level.dat starts from the skeleton that
Mojang's Minecraft Creator Tools exports for a flat world (stored as
tools/testworld/level.template.dat) and is patched field by field; the world
database is left for the game to create.
"""
from __future__ import annotations

import importlib
import json
import math
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from kit import nbt                    # noqa: E402
from kit import pack as K              # noqa: E402
from kit.arena import Arena, blk, bone, froglight, lantern, pillar, slab   # noqa: E402

OUT = os.path.abspath(os.environ.get("ABM_OUT", ROOT))
PACKS = os.path.join(OUT, "packs")
BP = os.path.join(PACKS, "behavior_packs", "The_Abandoned_Miracles_BP")
RP = os.path.join(PACKS, "resource_packs", "The_Abandoned_Miracles_RP")
KIT = os.path.join(OUT, "build", "testworld_kit")
DIST = os.path.join(OUT, "dist")
WORLD_NAME = "The Abandoned Miracles - Test World " + ".".join(str(n) for n in K.VERSION)
SURFACE = -60                           # walking surface of the flat world (bedrock, 2 dirt, grass from -64)
FLOOR = SURFACE - 1                     # the block layer every structure's floor replaces
SITES = {                               # boss -> (centre x, centre z, compass word, path block)
    "vesperra": (0, -72, "NORTH", blk("smooth_quartz", pillar_axis="y")),
    "cantor": (72, 0, "EAST", blk("waxed_oxidized_cut_copper")),
    "nomos": (0, 72, "SOUTH", blk("birch_planks")),
    "orison": (-72, 0, "WEST", blk("polished_blackstone")),
}
SEALS = {"vesperra": "abm:seal_vesperra", "cantor": "abm:seal_cantor", "nomos": "abm:seal_nomos", "orison": "abm:seal_orison"}
TITLES = {"vesperra": "Vesperra - The Hall of Endless Succession", "cantor": "Cantor XIII - The Basilica of the Last Note",
          "nomos": "Nomos - The Observatory of Unwritten Borders", "orison": "Orison - The Court of Unlived Hours"}


def hub() -> Arena:
    """Central plaza: a ring with four themed causeways pointing at the arenas."""
    a = Arena(41, 8, floor=0, seed=7)
    stone, dark = blk("smooth_stone"), blk("polished_blackstone_bricks")

    def floor(r, th):
        if r < 1.2:
            return blk("lodestone")
        if r < 3.5:
            return blk("chiseled_stone_bricks")
        if 8.5 <= r < 9.5:
            return dark
        if r >= 14.5:
            return None
        return stone if a.rng.random() < 0.85 else blk("stone_bricks")
    a.disc(0, 15.5, 0, floor)
    for key, (cx, cz, _, path) in SITES.items():
        dx, dz = (cx > 0) - (cx < 0), (cz > 0) - (cz < 0)
        for d in range(4, 21):
            for w in (-1, 0, 1):
                x, z = a.c + dx * d + (w if dx == 0 else 0), a.c + dz * d + (w if dz == 0 else 0)
                a.put(x, 0, z, path if w == 0 or d % 4 else dark)
        # a gate of two themed pillars where each causeway leaves the plaza
        for w in (-3, 3):
            x, z = a.c + dx * 13 + (w if dx == 0 else 0), a.c + dz * 13 + (w if dz == 0 else 0)
            for y in range(1, 5):
                a.put(x, y, z, path)
            a.put(x, 5, z, lantern("soul_lantern", False))
    for th in range(0, 360, 45):
        if th % 90:
            x, z = a.polar(11.5, th)
            a.put(x, 0, z, froglight("pearlescent"))
    return a


def site_info():
    """Arena structures that exist in the built packs."""
    out = {}
    for key, (cx, cz, word, _) in SITES.items():
        try:
            mod = importlib.import_module(f"bosses.{key}.arena")
        except ModuleNotFoundError:
            continue
        path = os.path.join(BP, "structures", "abm", f"{mod.NAME}.mcstructure")
        if not os.path.exists(path):
            continue
        st = mod.build()
        sx, sy, sz = st.size
        floor_layer = getattr(st, "floor", 0)
        marker = st.get(sx // 2, floor_layer, sz // 2)
        out[key] = {"name": mod.NAME, "size": (sx, sy, sz), "centre": (cx, cz), "word": word, "marker": marker,
                    "origin": (cx - sx // 2, FLOOR - floor_layer, cz - sz // 2)}
    return out


def functions(sites: dict, hub_size) -> dict:
    hx, hy, hz = hub_size
    areas = {"hub": ((-hx // 2, FLOOR, -hz // 2), (hx // 2, FLOOR + hy, hz // 2))}
    loads = [f"execute unless block 0 {FLOOR} 0 minecraft:lodestone run structure load abmtw:hub {-(hx // 2)} {FLOOR} {-(hz // 2)}"]
    for key, s in sites.items():
        x0, y0, z0 = s["origin"]
        sx, sy, sz = s["size"]
        areas[key] = ((x0, y0, z0), (x0 + sx - 1, y0 + sy, z0 + sz - 1))
        cx, cz = s["centre"]
        loads.append(f"execute unless block {cx} {FLOOR} {cz} {s['marker']} run structure load abm:{s['name']} {x0} {y0} {z0}")
    prepare = ["gamerule domobspawning false", "gamerule dodaylightcycle false", "gamerule doweathercycle false",
               "gamerule showcoordinates true", "gamerule keepinventory true", "gamerule mobgriefing false",
               "time set 6000", "weather clear"]
    prepare += [f"tickingarea add {a[0]} {a[1]} {a[2]} {b[0]} {b[1]} {b[2]} abmtw_{k}" for k, (a, b) in areas.items()]
    finish = [f"tickingarea remove abmtw_{k}" for k in areas] + [f"setworldspawn 0 {SURFACE} 0", "scoreboard players set abmtwclock abm_tw 1000"]
    # the section sign is written literally (UTF-8), not as a \u escape: function files are plain text
    say = lambda text: 'tellraw @s {"rawtext":[{"text":' + json.dumps(text, ensure_ascii=False) + "}]}"      # noqa: E731
    greet = [f"tp @s 0.5 {SURFACE} 0.5", "give @s abm:codex 1"]
    greet += [f"give @s {SEALS[k]} 1" for k in sites]
    greet += [say("§l§6The Abandoned Miracles§r §7- test world"),
              say("§7Four arenas stand around this plaza. Follow a causeway, walk to the middle of the arena and §fuse its Seal on the floor§7.")]
    greet += [say(f"§f{sites[k]['word']}§7: {TITLES[k]}") for k in sites]
    greet += [say("§7The §fCodex§7 explains each Miracle and holds the settings. §f/abm:wake <boss>§7 works anywhere."),
              say("§7This world is in §fSurvival§7 so the fights are real; you keep your inventory when you die."),
              # the reference loadout (enchanted diamond) comes from the add-on's script
              "scriptevent abm:kit give",
              "tag @s add abm_tw"]
    tick = ["scoreboard objectives add abm_tw dummy", "scoreboard players add abmtwclock abm_tw 0",
            "execute if score abmtwclock abm_tw matches 0..299 run scoreboard players add abmtwclock abm_tw 1",
            "execute if score abmtwclock abm_tw matches 2 run function abmtw/prepare"]
    tick += [f"execute if score abmtwclock abm_tw matches {t} run function abmtw/build" for t in (100, 150, 200, 250)]
    tick += ["execute if score abmtwclock abm_tw matches 299 run function abmtw/finish",
             "execute as @a[tag=!abm_tw] at @s if score abmtwclock abm_tw matches 250.. run function abmtw/greet"]
    return {"tick": tick, "prepare": prepare, "build": loads, "finish": finish, "greet": greet}


def level_dat() -> bytes:
    with open(os.path.join(HERE, "testworld", "level.template.dat"), "rb") as f:
        root = nbt.loads(f.read()[8:])
    v = root.v

    def put(key, value):
        if key not in v:
            raise SystemExit(f"level.dat template has no field {key}")
        v[key] = nbt.T(v[key].tag, value, v[key].elem)
    put("LevelName", WORLD_NAME)
    put("GameType", 0)                # survival: in creative the bosses cannot hurt anyone, so nothing could be judged
    put("Difficulty", 2)
    put("SpawnX", 0)
    put("SpawnY", SURFACE)
    put("SpawnZ", 0)
    put("Time", 6000)
    for rule, val in (("domobspawning", 0), ("dodaylightcycle", 0), ("doweathercycle", 0), ("keepinventory", 1),
                      ("showcoordinates", 1), ("mobgriefing", 0), ("cheatsEnabled", 1), ("commandsEnabled", 1)):
        put(rule, val)
    # no experiments: the add-on uses stable APIs only
    v["experiments"] = nbt.compound({"saved_with_toggled_experiments": nbt.byte(0), "experiments_ever_used": nbt.byte(0)})
    return nbt.level_dat(root)


def main() -> None:
    sites = site_info()
    if not sites:
        raise SystemExit("no arenas built - run tools/build.py first")
    import shutil
    shutil.rmtree(KIT, ignore_errors=True)
    h = hub()
    errs = h.validate()
    if errs:
        raise SystemExit("hub: " + "; ".join(errs))
    K.write_json(os.path.join(KIT, "manifest.json"), {
        "format_version": 2,
        "header": {"name": "The Abandoned Miracles - Test World Kit",
                   "description": "Commands-only helper for the test world: raises the plaza and the four arenas on first load.",
                   "uuid": K.UUID["tw_header"], "version": K.VERSION, "min_engine_version": K.MIN_ENGINE},
        "modules": [{"type": "data", "uuid": K.UUID["tw_data"], "version": K.VERSION}],
        "dependencies": [{"uuid": K.UUID["bp_header"], "version": K.VERSION}],
    })
    shutil.copyfile(os.path.join(BP, "pack_icon.png"), os.path.join(KIT, "pack_icon.png"))
    os.makedirs(os.path.join(KIT, "structures", "abmtw"), exist_ok=True)
    with open(os.path.join(KIT, "structures", "abmtw", "hub.mcstructure"), "wb") as f:
        f.write(h.to_bytes())
    fn = functions(sites, h.size)
    K.write_json(os.path.join(KIT, "functions", "tick.json"), {"values": ["abmtw/tick"]})
    for name, lines in fn.items():
        K.write_text(os.path.join(KIT, "functions", "abmtw", f"{name}.mcfunction"), "\n".join(lines) + "\n")

    os.makedirs(DIST, exist_ok=True)
    dst = os.path.join(DIST, "The_Abandoned_Miracles_Test_World.mcworld")
    if os.path.exists(dst):
        os.remove(dst)
    bp_manifest = json.load(open(os.path.join(BP, "manifest.json")))
    rp_manifest = json.load(open(os.path.join(RP, "manifest.json")))
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        def add(name, data):
            zi = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)
        add("level.dat", level_dat())
        add("levelname.txt", WORLD_NAME)
        add("world_behavior_packs.json", json.dumps([
            {"pack_id": bp_manifest["header"]["uuid"], "version": bp_manifest["header"]["version"]},
            {"pack_id": K.UUID["tw_header"], "version": K.VERSION}], indent=1))
        add("world_resource_packs.json", json.dumps([
            {"pack_id": rp_manifest["header"]["uuid"], "version": rp_manifest["header"]["version"]}], indent=1))
    n = 4
    n += K.zip_dir(BP, dst, "behavior_packs/The_Abandoned_Miracles_BP")
    n += K.zip_dir(KIT, dst, "behavior_packs/The_Abandoned_Miracles_Test_World_Kit")
    n += K.zip_dir(RP, dst, "resource_packs/The_Abandoned_Miracles_RP")
    K.write_json(os.path.join(OUT, "build", "testworld.json"), {
        "world": WORLD_NAME, "surface_y": SURFACE,
        "sites": {k: {"structure": "abm:" + s["name"], "centre": list(s["centre"]), "origin": list(s["origin"]), "size": list(s["size"]),
                      "direction": s["word"]} for k, s in sites.items()},
        "hub": {"structure": "abmtw:hub", "size": list(h.size)}, "files": n})
    print(f"[testworld] {os.path.basename(dst)}: {n} files, {os.path.getsize(dst) / 1024:.0f} KiB, arenas: {', '.join(sites)}")


if __name__ == "__main__":
    main()
