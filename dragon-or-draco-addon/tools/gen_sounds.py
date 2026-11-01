#!/usr/bin/env python3
"""Writes RP sounds/sound_definitions.json and RP sounds.json for the Red Dragon.

Every sound event is layered from Minecraft Bedrock's own vanilla sound files (re-pitched for
a creature this size), referenced by path, so the pack ships no audio and redistributes
nothing: the files are already installed with the game.  Each path is checked against
Mojang's bedrock-samples sound_definitions.json when that file is passed as an argument:

    python3 tools/gen_sounds.py <bedrock-samples>/resource_pack/sounds/sound_definitions.json
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "dragon_or_draco")


def v(base, n, pitch, volume, start=1, sep=""):
    return [{"name": f"{base}{sep}{i}", "pitch": pitch, "volume": volume} for i in range(start, start + n)]


def one(name, pitch, volume):
    return [{"name": name, "pitch": pitch, "volume": volume}]


D = "mob.dod.red_dragon."
EVENTS = {
    # creature voice
    "ambient": (v("sounds/mob/ravager/idle", 8, 0.5, 0.9), 48),
    "growl": (v("sounds/mob/enderdragon/growl", 4, 0.85, 0.7), 48),
    "roar": (v("sounds/mob/enderdragon/growl", 4, 0.62, 1.0), 96),
    "roar_layer": (v("sounds/mob/ravager/roar", 4, 0.55, 1.0), 96),
    "sniff": (v("sounds/mob/sniffer/scenting", 3, 0.6, 0.8), 32),
    "hurt": (v("sounds/mob/enderdragon/hit", 4, 0.75, 1.0), 48),
    "death": (v("sounds/mob/ravager/death", 3, 0.5, 1.0) + v("sounds/mob/enderdragon/growl", 2, 0.48, 1.0), 96),
    "death_thud": (one("sounds/item/mace/smash_ground_heavy", 0.55, 1.0), 64),
    # body and wings
    "step": (v("sounds/mob/ravager/step", 5, 0.6, 0.75), 32),
    "flap": (v("sounds/mob/enderdragon/wings", 6, 0.8, 0.95), 64),
    "wing_unfold": (v("sounds/mob/enderdragon/wings", 6, 1.15, 0.45), 32),
    "glide": (one("sounds/elytra/elytra_loop", 0.55, 0.35), 32),
    "takeoff": (v("sounds/mob/enderdragon/wings", 6, 0.65, 1.0), 64),
    "land": (one("sounds/item/mace/smash_ground_heavy", 0.6, 0.9), 64),
    # attacks
    "bite": (v("sounds/mob/ravager/bite", 3, 0.7, 1.0), 48),
    "swipe": (v("sounds/item/mace/smash_air", 3, 0.6, 1.0), 48),
    "hit": (v("sounds/item/mace/smash_ground", 4, 0.9, 0.9), 48),
    "tail_slam": (one("sounds/item/mace/smash_ground_heavy", 0.72, 1.0), 64),
    "buffet": (v("sounds/mob/breeze/wind_burst", 3, 0.55, 1.0), 64),
    "fire_charge": (v("sounds/mob/blaze/breathe", 4, 0.5, 1.0), 64),
    "fire_charge_layer": (one("sounds/mob/ghast/charge", 0.6, 0.8), 64),
    "fire_breath": (one("sounds/mob/ghast/fireball4", 0.5, 1.0), 96),
    "fire_loop": (one("sounds/fire/fire", 0.7, 1.0), 64),
    "fire_hit": (one("sounds/fire/ignite", 0.8, 0.8), 32),
}


def main():
    defs = {}
    for k, (sounds, maxd) in EVENTS.items():
        defs[D + k] = {"category": "hostile", "max_distance": maxd, "min_distance": 4.0, "sounds": sounds}
    data = {"format_version": "1.20.20", "sound_definitions": defs}
    os.makedirs(os.path.join(RP, "sounds"), exist_ok=True)
    with open(os.path.join(RP, "sounds", "sound_definitions.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    # vanilla entity sound events (ambient / hurt / death / step) for dod:red_dragon
    sounds_json = {
        "entity_sounds": {
            "entities": {
                "dod:red_dragon": {
                    "volume": 1.0,
                    "pitch": [0.9, 1.05],
                    "events": {
                        "ambient": D + "ambient",
                        "hurt": D + "hurt",
                        "death": D + "death_thud",
                        "step": {"sound": D + "step", "volume": 0.8, "pitch": [0.9, 1.1]},
                    },
                }
            }
        }
    }
    with open(os.path.join(RP, "sounds.json"), "w", encoding="utf-8") as f:
        json.dump(sounds_json, f, indent=2)
        f.write("\n")
    print(f"{len(EVENTS)} sound events written")
    if len(sys.argv) > 1:
        vanilla = json.load(open(sys.argv[1]))["sound_definitions"]
        known = set()
        for d in vanilla.values():
            for s in d.get("sounds", []):
                known.add(s if isinstance(s, str) else s.get("name"))
        missing = [s["name"] for sounds, _ in EVENTS.values() for s in sounds if s["name"] not in known]
        if missing:
            print("MISSING vanilla sound files:", missing)
            sys.exit(1)
        print("all", sum(len(s) for s, _ in EVENTS.values()), "sound files exist in vanilla bedrock-samples")


if __name__ == "__main__":
    main()
