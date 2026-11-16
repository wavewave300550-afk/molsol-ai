"""Ready-to-play test world (.mcworld) with the current packs embedded.

    python3 tools/test_world.py            # -> dist/PlayableRaces_TestWorld.mcworld

Importing the file creates a new world ("Playable Races Test <version>") that already has
both packs active, so nothing has to be removed from an existing world first.  The world
is superflat, creative, cheats on, coordinates shown, keep-inventory and immediate respawn,
no experiments.  The terrain is generated on first load (the world ships no chunk data).

tools/world_template/level.dat was exported once by Minecraft Creator Tools
(`exportworld`) and then edited with kit/nbt.py: experiments removed, test-friendly
game rules.  Only LevelName and the pack list change per build.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from kit import nbt  # noqa: E402

DIST = os.path.join(ROOT, "dist")
TEMPLATE = os.path.join(HERE, "world_template", "level.dat")


def manifest(pack: str) -> dict:
    with zipfile.ZipFile(os.path.join(DIST, pack)) as z:
        return json.loads(z.read("manifest.json"))


def build(out: str | None = None) -> str:
    bp, rp = manifest("PlayableRaces_BP.mcpack"), manifest("PlayableRaces_RP.mcpack")
    ver = bp["header"]["version"]
    name = f"Playable Races Test {'.'.join(map(str, ver))}"
    sver, sname, root = nbt.read_level(TEMPLATE)
    root[1]["LevelName"] = (8, name)
    with tempfile.TemporaryDirectory() as td:
        lvl = os.path.join(td, "level.dat")
        nbt.write_level(lvl, sver, sname, root)
        level = open(lvl, "rb").read()
    out = out or os.path.join(DIST, "PlayableRaces_TestWorld.mcworld")

    def packs_json(m):
        return json.dumps([{"pack_id": m["header"]["uuid"], "version": m["header"]["version"]}], indent=2)

    def history(m, folder):
        return json.dumps({"packs": [{"uuid": m["header"]["uuid"], "version": m["header"]["version"], "name": folder,
                                      "can_be_redownloaded": False}]}, indent=2)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("level.dat", level)
        z.writestr("level.dat_old", level)
        z.writestr("levelname.txt", name)
        z.writestr("world_behavior_packs.json", packs_json(bp))
        z.writestr("world_resource_packs.json", packs_json(rp))
        z.writestr("world_behavior_pack_history.json", history(bp, "PlayableRaces_BP"))
        z.writestr("world_resource_pack_history.json", history(rp, "PlayableRaces_RP"))
        for pack, folder in (("PlayableRaces_BP.mcpack", "behavior_packs/PlayableRaces_BP/"),
                             ("PlayableRaces_RP.mcpack", "resource_packs/PlayableRaces_RP/")):
            with zipfile.ZipFile(os.path.join(DIST, pack)) as src:
                for n in src.namelist():
                    if not n.endswith("/"):
                        z.writestr(folder + n, src.read(n))   # byte-for-byte copy of the released pack
    # self-check: zip sound, level.dat readable, names and versions consistent
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "level.dat")
            open(p, "wb").write(z.read("level.dat"))
            assert nbt.plain(nbt.read_level(p)[2])["LevelName"] == name
        assert json.loads(z.read("behavior_packs/PlayableRaces_BP/manifest.json"))["header"]["version"] == ver
    return out


if __name__ == "__main__":
    path = build(sys.argv[1] if len(sys.argv) > 1 else None)
    print(os.path.relpath(path, ROOT), os.path.getsize(path) // 1024, "KB")
