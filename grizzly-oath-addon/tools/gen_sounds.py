#!/usr/bin/env python3
"""Writes resource_packs/grizzly_oath/sounds/sound_definitions.json.

Every Grizzly's Oath sound event is layered from vanilla Bedrock sound files (re-pitched and
re-mixed), so the pack ships no audio of its own and stays small for iPhone. Each path below
exists in Mojang's bedrock-samples 1.26.60 sound_definitions.json; pass that file as the first
argument to check them:  python3 tools/gen_sounds.py <vanilla sound_definitions.json>
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "addon", "resource_packs", "grizzly_oath", "sounds", "sound_definitions.json")


def variants(base, n, pitch, volume, start=1, sep=""):
    return [{"name": f"{base}{sep}{i}", "pitch": pitch, "volume": volume} for i in range(start, start + n)]


EVENTS = {
    # Frontier Cleave
    "grizzly_oath.cleave_swing": variants("sounds/item/mace/smash_air", 3, 0.8, 0.6),
    "grizzly_oath.cleave_hit": variants("sounds/item/mace/smash_ground", 4, 1.2, 0.8),
    # Grizzly Rend
    "grizzly_oath.rend": variants("sounds/mob/breeze/wind_burst", 3, 0.7, 1.0),
    "grizzly_oath.growl": variants("sounds/mob/polarbear/hurt", 4, 0.55, 0.9),
    # Relentless Pursuit
    "grizzly_oath.dash": [{"name": "sounds/item/trident/riptide_mono1", "pitch": 1.3, "volume": 0.9}],
    "grizzly_oath.heavy_slam": [{"name": "sounds/item/mace/smash_ground_heavy", "pitch": 0.85, "volume": 1.0}],
    # Unbroken Will
    "grizzly_oath.roar": variants("sounds/mob/polarbear/warning", 4, 0.6, 1.0),
    "grizzly_oath.heartbeat": variants("sounds/mob/warden/heartbeat_", 4, 0.9, 0.6),
    # Oath of the Grizzly
    "grizzly_oath.charge": variants("sounds/block/respawn_anchor/charge", 3, 0.7, 0.9),
    "grizzly_oath.titan_roar": variants("sounds/mob/ravager/roar", 4, 0.6, 1.0),
    "grizzly_oath.shockwave": variants("sounds/random/explode", 4, 0.55, 0.8),
    "grizzly_oath.thunder": variants("sounds/item/trident/thunder", 2, 0.8, 0.5),
    # UI
    "grizzly_oath.select": [{"name": "sounds/block/bell/bell_use01", "pitch": 1.8, "volume": 0.35}],
    "grizzly_oath.not_ready": [{"name": "sounds/note/bass", "pitch": 0.6, "volume": 0.6}],
    "grizzly_oath.ready": [{"name": "sounds/random/orb", "pitch": 0.55, "volume": 0.35}],
}


def main():
    data = {
        "format_version": "1.20.20",
        "sound_definitions": {k: {"category": "player", "sounds": v} for k, v in EVENTS.items()},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"{len(EVENTS)} sound events written")
    if len(sys.argv) > 1:
        vanilla = json.load(open(sys.argv[1]))["sound_definitions"]
        known = set()
        for v in vanilla.values():
            for s in v.get("sounds", []):
                known.add(s if isinstance(s, str) else s.get("name"))
        missing = [s["name"] for v in EVENTS.values() for s in v if s["name"] not in known]
        if missing:
            print("MISSING vanilla sound files:", missing)
            sys.exit(1)
        print("all", sum(len(v) for v in EVENTS.values()), "sound files exist in vanilla")


if __name__ == "__main__":
    main()
