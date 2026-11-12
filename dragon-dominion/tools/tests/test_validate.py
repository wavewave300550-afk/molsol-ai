"""
Tests for tools/validate.py and tools/version.py (run after the build):

    python3 -m unittest discover -s tools/tests -p "test_*.py"

Each test copies the real build/ into a temporary project, optionally adds a
synthetic test entity ("validator_fixture": one cube, no art) exercising the
whole asset pipeline, applies one defect and checks that the validator reports
it. Fixtures exist only in temp folders and never reach the packs.
"""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import validate  # noqa: E402

FIXTURE = "dragon_dominion:validator_fixture"


def png_bytes(width, height):
    raw = b"".join(b"\x00" + b"\x80\x80\x80\xff" * width for _ in range(height))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def fixture_files():
    """A complete, valid set of files for one entity, keyed by (pack, path)."""
    geo = {
        "format_version": "1.12.0",
        "minecraft:geometry": [{
            "description": {"identifier": "geometry.dragon_dominion.validator_fixture", "texture_width": 32,
                            "texture_height": 32},
            "bones": [
                {"name": "root", "pivot": [0, 0, 0]},
                {"name": "body", "parent": "root", "pivot": [0, 4, 0],
                 "cubes": [{"origin": [-4, 0, -4], "size": [8, 8, 8], "uv": [0, 0]}]},
            ],
        }],
    }
    return {
        ("BP", "entities/validator_fixture.json"): {
            "format_version": "1.21.0",
            "minecraft:entity": {
                "description": {"identifier": FIXTURE, "is_spawnable": True, "is_summonable": True,
                                "properties": {"dragon_dominion:phase": {"type": "int", "range": [0, 1], "default": 0,
                                                                          "client_sync": True}}},
                "component_groups": {"dragon_dominion:enraged": {"minecraft:variant": {"value": 1}}},
                "components": {"minecraft:health": {"value": 10, "max": 10},
                               "minecraft:loot": {"table": "loot_tables/entities/validator_fixture.json"}},
                "events": {"dragon_dominion:enrage": {"add": {"component_groups": ["dragon_dominion:enraged"]}}},
            },
        },
        ("BP", "loot_tables/entities/validator_fixture.json"): {"pools": []},
        ("BP", "spawn_rules/validator_fixture.json"): {
            "format_version": "1.8.0",
            "minecraft:spawn_rules": {"description": {"identifier": FIXTURE, "population_control": "monster"},
                                      "conditions": []},
        },
        ("RP", "entity/validator_fixture.entity.json"): {
            "format_version": "1.10.0",
            "minecraft:client_entity": {"description": {
                "identifier": FIXTURE,
                "materials": {"default": "entity_alphatest"},
                "textures": {"default": "textures/entity/validator_fixture/validator_fixture"},
                "geometry": {"default": "geometry.dragon_dominion.validator_fixture"},
                "animations": {"idle": "animation.dragon_dominion.validator_fixture.idle",
                               "general": "controller.animation.dragon_dominion.validator_fixture.general",
                               "look_at_target": "animation.common.look_at_target"},
                "scripts": {"animate": ["general", "look_at_target"]},
                "render_controllers": ["controller.render.dragon_dominion.validator_fixture"],
                "particle_effects": {"aura": "dragon_dominion:validator_fixture_aura"},
                "spawn_egg": {"base_color": "#202020", "overlay_color": "#c0a040"},
            }},
        },
        ("RP", "models/entity/validator_fixture/validator_fixture.geo.json"): geo,
        ("RP", "textures/entity/validator_fixture/validator_fixture.png"): png_bytes(32, 32),
        ("RP", "animations/validator_fixture/validator_fixture.animation.json"): {
            "format_version": "1.8.0",
            "animations": {"animation.dragon_dominion.validator_fixture.idle": {
                "loop": True, "bones": {"body": {"rotation": [0, "math.sin(query.anim_time * 90) * 5", 0]}}}},
        },
        ("RP", "animation_controllers/validator_fixture.animation_controllers.json"): {
            "format_version": "1.10.0",
            "animation_controllers": {"controller.animation.dragon_dominion.validator_fixture.general": {
                "initial_state": "default",
                "states": {"default": {"animations": ["idle"], "transitions": [{"default": "0"}]}}}},
        },
        ("RP", "render_controllers/validator_fixture.render_controllers.json"): {
            "format_version": "1.8.0",
            "render_controllers": {"controller.render.dragon_dominion.validator_fixture": {
                "geometry": "Geometry.default", "materials": [{"*": "Material.default"}],
                "textures": ["Texture.default"]}},
        },
        ("RP", "particles/validator_fixture/aura.particle.json"): {
            "format_version": "1.10.0",
            "particle_effect": {"description": {
                "identifier": "dragon_dominion:validator_fixture_aura",
                "basic_render_parameters": {"material": "particles_alpha",
                                            "texture": "textures/particle/validator_fixture/aura"}},
                "components": {}},
        },
        ("RP", "textures/particle/validator_fixture/aura.png"): png_bytes(16, 16),
        ("RP", "sounds/sound_definitions.json"): {
            "format_version": "1.20.20",
            "sound_definitions": {"dragon_dominion.validator_fixture.ambient": {
                "category": "hostile", "sounds": ["sounds/validator_fixture/ambient1"]}},
        },
        ("RP", "sounds/validator_fixture/ambient1.ogg"): b"OggS",
        ("RP", "sounds.json"): {"entity_sounds": {"entities": {FIXTURE: {
            "events": {"ambient": "dragon_dominion.validator_fixture.ambient"}}}}},
    }


class ValidatorTest(unittest.TestCase):
    def setUp(self):
        if not os.path.isdir(os.path.join(ROOT, "build")):
            self.skipTest("run `python3 tools/build.py` first")
        self.tmp = tempfile.mkdtemp(prefix="dd-validate-")
        shutil.copytree(os.path.join(ROOT, "build"), os.path.join(self.tmp, "build"))
        for name in ("package.json", "package-lock.json"):
            shutil.copy(os.path.join(ROOT, name), self.tmp)
        os.makedirs(os.path.join(self.tmp, "src"))
        shutil.copy(os.path.join(ROOT, "src", "config.ts"), os.path.join(self.tmp, "src"))
        os.symlink(os.path.join(ROOT, "node_modules"), os.path.join(self.tmp, "node_modules"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---------------------------------------------------------------- helpers
    def path(self, pack, rel):
        folder = "behavior_packs" if pack == "BP" else "resource_packs"
        return os.path.join(self.tmp, "build", folder, "dragon_dominion", *rel.split("/"))

    def put(self, pack, rel, content):
        path = self.path(pack, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if isinstance(content, (bytes, str)):
            with open(path, "wb") as f:
                f.write(content if isinstance(content, bytes) else content.encode("utf-8"))
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2)

    def read(self, pack, rel):
        with open(self.path(pack, rel), encoding="utf-8") as f:
            return json.load(f)

    def add_fixture(self, files=None):
        files = files or fixture_files()
        for (pack, rel), content in files.items():
            self.put(pack, rel, content)
        with open(self.path("RP", "texts/en_US.lang"), "a", encoding="utf-8") as f:
            f.write(f"entity.{FIXTURE}.name=Validator Fixture\nitem.spawn_egg.entity.{FIXTURE}.name=Spawn Fixture\n")

    def report(self):
        return validate.validate(self.tmp)

    def assertValid(self):
        r = self.report()
        self.assertEqual(r.errors, [], "\n".join(r.errors))
        return r

    def assertError(self, fragment):
        errors = self.report().errors
        self.assertTrue(any(fragment in e for e in errors), f"no error containing {fragment!r} in:\n" + "\n".join(errors))

    def mutated(self, key, change):
        files = fixture_files()
        change(files[key])
        self.add_fixture(files)

    # ---------------------------------------------------------------- baseline
    def test_real_build_is_valid(self):
        r = self.assertValid()
        self.assertEqual(r.warnings, [])

    def test_complete_fixture_entity_is_valid(self):
        self.add_fixture()
        self.assertValid()

    # ---------------------------------------------------------------- structure
    def test_uppercase_file_name(self):
        self.put("RP", "textures/entity/Bad_Name.png", png_bytes(16, 16))
        self.assertError("use lowercase ASCII")

    def test_source_files_rejected(self):
        self.put("RP", "models/entity/dragon.bbmodel", "{}")
        self.assertError("does not belong in a pack")

    def test_invalid_json(self):
        self.put("BP", "entities/broken.json", '{"format_version": "1.21.0",}')
        self.assertError("invalid JSON")

    def test_byte_order_mark(self):
        self.put("BP", "loot_tables/bom.json", b'\xef\xbb\xbf{"pools": []}')
        self.assertError("byte order mark")

    # ---------------------------------------------------------------- manifests & versions
    def test_changed_uuid(self):
        m = self.read("BP", "manifest.json")
        m["header"]["uuid"] = "11111111-2222-4333-8444-555555555555"
        self.put("BP", "manifest.json", m)
        self.assertError("header.uuid changed")

    def test_pack_versions_must_match(self):
        m = self.read("RP", "manifest.json")
        m["header"]["version"] = [9, 9, 9]
        m["modules"][0]["version"] = [9, 9, 9]
        self.put("RP", "manifest.json", m)
        self.assertError("BP and RP header versions must match")
        self.assertError("BP must depend on the RP")

    def test_script_api_must_match_typings(self):
        m = self.read("BP", "manifest.json")
        next(d for d in m["dependencies"] if d.get("module_name") == "@minecraft/server")["version"] = "2.0.0"
        self.put("BP", "manifest.json", m)
        self.assertError("installed typings")

    def test_beta_script_api_rejected(self):
        m = self.read("BP", "manifest.json")
        next(d for d in m["dependencies"] if d.get("module_name") == "@minecraft/server")["version"] = "2.13.0-beta"
        self.put("BP", "manifest.json", m)
        self.assertError("only stable Script API versions")

    def test_package_json_version_sync(self):
        with open(os.path.join(self.tmp, "package.json"), encoding="utf-8") as f:
            pkg = json.load(f)
        pkg["version"] = "9.9.9"
        with open(os.path.join(self.tmp, "package.json"), "w", encoding="utf-8") as f:
            json.dump(pkg, f)
        self.assertError("package.json version")

    # ---------------------------------------------------------------- scripts
    def test_script_import_without_extension(self):
        self.put("BP", "scripts/extra.js", 'import { x } from "./core/log";\n')
        self.assertError("must end with .js")

    def test_script_import_wrong_case(self):
        self.put("BP", "scripts/extra.js", 'import { x } from "./core/Log.js";\n')
        self.assertError("does not resolve")

    def test_undeclared_script_module(self):
        self.put("BP", "scripts/extra.js", 'import { ActionFormData } from "@minecraft/server-ui";\n')
        self.assertError("not a dependency in the BP manifest")

    # ---------------------------------------------------------------- asset pipeline
    def test_texture_case_mismatch(self):
        def change(e):
            e["minecraft:client_entity"]["description"]["textures"]["default"] = "textures/entity/validator_fixture/Validator_Fixture"
        self.mutated(("RP", "entity/validator_fixture.entity.json"), change)
        self.assertError("differs in case")

    def test_missing_geometry(self):
        def change(e):
            e["minecraft:client_entity"]["description"]["geometry"]["default"] = "geometry.dragon_dominion.missing"
        self.mutated(("RP", "entity/validator_fixture.entity.json"), change)
        self.assertError("geometry 'geometry.dragon_dominion.missing' not found")

    def test_geometry_namespace(self):
        def change(g):
            g["minecraft:geometry"][0]["description"]["identifier"] = "geometry.validator_fixture"
        self.mutated(("RP", "models/entity/validator_fixture/validator_fixture.geo.json"), change)
        self.assertError("must start with 'geometry.dragon_dominion.'")

    def test_box_uv_out_of_bounds(self):
        def change(g):
            g["minecraft:geometry"][0]["bones"][1]["cubes"][0]["uv"] = [8, 0]
        self.mutated(("RP", "models/entity/validator_fixture/validator_fixture.geo.json"), change)
        self.assertError("box UV")

    def test_animation_bone_missing_from_geometry(self):
        def change(a):
            a["animations"]["animation.dragon_dominion.validator_fixture.idle"]["bones"]["left_wing"] = {"rotation": [0, 0, 0]}
        self.mutated(("RP", "animations/validator_fixture/validator_fixture.animation.json"), change)
        self.assertError("moves bone 'left_wing'")

    def test_controller_uses_unknown_animation(self):
        def change(c):
            c["animation_controllers"]["controller.animation.dragon_dominion.validator_fixture.general"]["states"]["default"]["animations"] = ["fly"]
        self.mutated(("RP", "animation_controllers/validator_fixture.animation_controllers.json"), change)
        self.assertError("'fly' is not in the entity's animations")

    def test_render_controller_unknown_texture_key(self):
        def change(r):
            r["render_controllers"]["controller.render.dragon_dominion.validator_fixture"]["textures"] = ["Texture.glow"]
        self.mutated(("RP", "render_controllers/validator_fixture.render_controllers.json"), change)
        self.assertError("Texture.glow")

    def test_missing_client_entity(self):
        files = fixture_files()
        del files[("RP", "entity/validator_fixture.entity.json")]
        self.add_fixture(files)
        self.assertError("has no client entity")

    def test_missing_lang_name(self):
        for (pack, rel), content in fixture_files().items():
            self.put(pack, rel, content)
        self.assertError(f"no 'entity.{FIXTURE}.name'")

    def test_missing_loot_table(self):
        files = fixture_files()
        del files[("BP", "loot_tables/entities/validator_fixture.json")]
        self.add_fixture(files)
        self.assertError("minecraft:loot table")

    def test_unknown_component_group(self):
        def change(e):
            e["minecraft:entity"]["events"]["dragon_dominion:enrage"]["add"]["component_groups"] = ["dragon_dominion:nope"]
        self.mutated(("BP", "entities/validator_fixture.json"), change)
        self.assertError("unknown component group 'dragon_dominion:nope'")

    def test_vanilla_entity_override_rejected(self):
        def change(e):
            e["minecraft:entity"]["description"]["identifier"] = "minecraft:ender_dragon"
        self.mutated(("BP", "entities/validator_fixture.json"), change)
        self.assertError("no vanilla overrides")

    def test_missing_sound_file(self):
        files = fixture_files()
        del files[("RP", "sounds/validator_fixture/ambient1.ogg")]
        self.add_fixture(files)
        self.assertError("sound file 'sounds/validator_fixture/ambient1' not found")

    def test_spawn_rule_for_unknown_entity(self):
        def change(s):
            s["minecraft:spawn_rules"]["description"]["identifier"] = "dragon_dominion:ghost"
        self.mutated(("BP", "spawn_rules/validator_fixture.json"), change)
        self.assertError("spawn rule for unknown entity")


class VersionScriptTest(unittest.TestCase):
    def test_bump_keeps_project_valid(self):
        if not os.path.isdir(os.path.join(ROOT, "node_modules")):
            self.skipTest("run `npm ci` first")
        tmp = tempfile.mkdtemp(prefix="dd-version-")
        try:
            project = os.path.join(tmp, "project")
            shutil.copytree(ROOT, project, ignore=shutil.ignore_patterns("node_modules", "build", "dist", "__pycache__"))
            os.symlink(os.path.join(ROOT, "node_modules"), os.path.join(project, "node_modules"))
            run = lambda *args: subprocess.run([sys.executable, *args], cwd=project, capture_output=True, text=True)  # noqa: E731
            self.assertEqual(run("tools/version.py", "0.1.0").returncode, 1, "must refuse a non-increasing version")
            self.assertEqual(run("tools/version.py", "0.2.0").returncode, 0)
            self.assertEqual(run("tools/build.py").returncode, 0)
            report = validate.validate(project)
            self.assertEqual(report.errors, [], "\n".join(report.errors))
            with open(os.path.join(project, "resource_packs", "dragon_dominion", "manifest.json"), encoding="utf-8") as f:
                rp = json.load(f)
            self.assertEqual(rp["header"]["version"], [0, 2, 0])
            self.assertEqual(rp["dependencies"][0]["version"], [0, 2, 0])
            self.assertEqual(rp["header"]["uuid"], validate.PERMANENT_UUIDS["rp_header"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
