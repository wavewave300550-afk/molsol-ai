"""
Static validation of the built packs (run after `python3 tools/build.py`):

    python3 tools/validate.py [project_root]

Checks the files Minecraft will load, in build/:
  * structure: allowed file types, lowercase ASCII paths (iOS and Android file
    systems are case-sensitive), UTF-8 without BOM, strict JSON syntax
  * manifests: format, permanent UUIDs, BP<->RP dependencies, script module,
    Script API versions vs installed typings, version sync with package.json
    and src/config.ts
  * namespace: every identifier the packs define uses "dragon_dominion"
  * entity asset pipeline cross references: BP entity <-> client entity,
    geometry, textures (exact case), animations and their bones, animation and
    render controllers, particles, sounds, loot tables, spawn rules, lang keys
  * scripts: relative imports resolve (exact case, .js), bare imports are
    declared manifest dependencies
Only the Python standard library is used. Exit code 1 when there are errors.
"""
import json
import math
import os
import re
import struct
import sys

NAMESPACE = "dragon_dominion"
PACK_DIR = "dragon_dominion"
MANIFEST_FORMAT = 2
# Permanent pack identity. Changing any of these breaks every world that uses the add-on.
PERMANENT_UUIDS = {
    "bp_header": "207ddd61-776d-4c01-89be-5babddf6d88b",
    "bp_data": "a6d0d735-46ec-429b-9156-36babf467988",
    "bp_script": "5bfabe09-af07-4e8a-86a2-f2813a47d0d3",
    "rp_header": "87494967-a706-43dc-91fc-2704ce550f10",
    "rp_resources": "50560be4-b4ca-4c74-a63e-a23b63e9e5c8",
}
ALLOWED_EXTENSIONS = {".json", ".js", ".png", ".tga", ".jpg", ".jpeg", ".lang", ".ogg", ".wav", ".fsb",
                      ".mcstructure", ".mcfunction"}
TEXT_EXTENSIONS = {".json", ".js", ".lang", ".mcfunction"}
TEXTURE_EXTENSIONS = (".png", ".tga", ".jpg", ".jpeg")
SOUND_EXTENSIONS = (".ogg", ".wav", ".fsb")
PATH_PATTERN = re.compile(r"^[a-z0-9_\-./]+$")
LANG_PATH_PATTERN = re.compile(r"^texts/[a-z]{2}_[A-Z]{2}\.lang$")
LONG_PATH = 80
UUID_V4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
LOCAL_ID = r"[a-z][a-z0-9_]*"
OWN_ID = re.compile(rf"^{NAMESPACE}:{LOCAL_ID}$")
PREFIX = {
    "geometry": f"geometry.{NAMESPACE}.",
    "animation": f"animation.{NAMESPACE}.",
    "animation_controller": f"controller.animation.{NAMESPACE}.",
    "render_controller": f"controller.render.{NAMESPACE}.",
    "sound": f"{NAMESPACE}.",
}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.checks = 0

    def check(self, cond, msg):
        self.checks += 1
        if not cond:
            self.errors.append(msg)
        return bool(cond)

    def warn(self, cond, msg):
        self.checks += 1
        if not cond:
            self.warnings.append(msg)
        return bool(cond)

    def print(self):
        print(f"[validate] {self.checks} checks, {len(self.errors)} errors, {len(self.warnings)} warnings")
        for e in self.errors:
            print(f"  ERROR: {e}")
        for w in self.warnings:
            print(f"  WARNING: {w}")


class Pack:
    """Files of one built pack, keyed by forward-slash relative path."""

    def __init__(self, label, folder):
        self.label = label
        self.folder = folder
        self.files = {}
        for dirpath, _, filenames in os.walk(folder):
            for name in filenames:
                path = os.path.join(dirpath, name)
                self.files[os.path.relpath(path, folder).replace(os.sep, "/")] = path
        self.lower = {rel.lower(): rel for rel in self.files}
        self.json = {}

    def where(self, rel):
        return f"{self.label}/{rel}"

    def resolve(self, report, ref, extensions, what, context):
        """Checks that `ref` (an extensionless pack path) exists with exact case."""
        for ext in extensions:
            if ref + ext in self.files:
                return True
        for ext in extensions:
            actual = self.lower.get((ref + ext).lower())
            if actual:
                return report.check(False, f"{context}: {what} '{ref}' differs in case from '{actual}' "
                                           "(case-sensitive on iOS/Android)")
        return report.check(False, f"{context}: {what} '{ref}' not found in {self.label}")

    def json_with(self, key, folder=None):
        for rel, data in sorted(self.json.items()):
            if isinstance(data, dict) and key in data and (folder is None or rel.startswith(folder + "/")):
                yield rel, data


# --------------------------------------------------------------------------- files

def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def check_files(report, pack):
    for rel, path in sorted(pack.files.items()):
        where = pack.where(rel)
        ext = os.path.splitext(rel)[1].lower()
        report.check(ext in ALLOWED_EXTENSIONS, f"{where}: file type '{ext}' does not belong in a pack "
                                                "(keep sources such as .bbmodel/.psd/.ts outside the packs)")
        report.check(PATH_PATTERN.match(rel) or LANG_PATH_PATTERN.match(rel),
                     f"{where}: use lowercase ASCII letters, digits, '_', '-', '.' only (no spaces or capitals)")
        report.warn(len(rel) <= LONG_PATH, f"{where}: path longer than {LONG_PATH} characters")
        if ext == ".js":
            report.check(pack.label == "BP" and rel.startswith("scripts/"), f"{where}: scripts belong in BP/scripts/")
        if ext == ".png":
            report.check(png_size(path) is not None, f"{where}: not a valid PNG file")
        if ext not in TEXT_EXTENSIONS:
            continue
        with open(path, "rb") as f:
            raw = f.read()
        if not report.check(not raw.startswith(b"\xef\xbb\xbf"), f"{where}: remove the UTF-8 byte order mark"):
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as e:
            report.check(False, f"{where}: not valid UTF-8 ({e})")
            continue
        if ext == ".json":
            try:
                pack.json[rel] = json.loads(text)
            except json.JSONDecodeError as e:
                report.check(False, f"{where}: invalid JSON at line {e.lineno} column {e.colno}: {e.msg}")


# --------------------------------------------------------------------------- manifests & versions

def is_version(v):
    return isinstance(v, list) and len(v) == 3 and all(isinstance(n, int) and n >= 0 for n in v)


def installed_version(root, module_name):
    path = os.path.join(root, "node_modules", *module_name.split("/"), "package.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("version")


def check_manifest_header(report, pack, manifest, expected_uuid):
    where = pack.where("manifest.json")
    report.check(manifest.get("format_version") == MANIFEST_FORMAT, f"{where}: format_version must be {MANIFEST_FORMAT}")
    header = manifest.get("header", {})
    for field in ("name", "description"):
        report.check(isinstance(header.get(field), str) and header[field].strip(), f"{where}: header.{field} is required")
    report.check(header.get("uuid") == expected_uuid,
                 f"{where}: header.uuid changed (expected permanent {expected_uuid}); changing it breaks existing worlds")
    report.check(is_version(header.get("version")), f"{where}: header.version must be [major, minor, patch]")
    report.check(is_version(header.get("min_engine_version")), f"{where}: header.min_engine_version must be [1, x, y]")
    for module in manifest.get("modules", []):
        report.check(module.get("version") == header.get("version"),
                     f"{where}: module '{module.get('type')}' version must equal header.version")
    for dep in manifest.get("dependencies", []):
        report.check(("uuid" in dep) != ("module_name" in dep), f"{where}: dependency needs exactly one of uuid/module_name")
    return header


def check_manifests(report, root, bp, rp):
    bpm, rpm = bp.json.get("manifest.json"), rp.json.get("manifest.json")
    if not report.check(isinstance(bpm, dict) and isinstance(rpm, dict), "manifest.json missing or invalid in BP or RP"):
        return None
    bph = check_manifest_header(report, bp, bpm, PERMANENT_UUIDS["bp_header"])
    rph = check_manifest_header(report, rp, rpm, PERMANENT_UUIDS["rp_header"])

    uuids = [m.get("uuid") for m in (bph, rph, *bpm.get("modules", []), *rpm.get("modules", []))]
    report.check(len(set(uuids)) == len(uuids), "manifest UUIDs must all be different")
    for u in uuids:
        report.check(isinstance(u, str) and UUID_V4.match(u), f"manifest UUID '{u}' is not a lowercase UUID v4")

    bp_modules = {m.get("type"): m for m in bpm.get("modules", [])}
    report.check(sorted(m.get("type") for m in bpm.get("modules", [])) == ["data", "script"],
                 "BP manifest must have exactly one 'data' and one 'script' module")
    report.check(bp_modules.get("data", {}).get("uuid") == PERMANENT_UUIDS["bp_data"], "BP data module UUID changed")
    script = bp_modules.get("script", {})
    report.check(script.get("uuid") == PERMANENT_UUIDS["bp_script"], "BP script module UUID changed")
    report.check(script.get("language") == "javascript", "BP script module language must be 'javascript'")
    report.check(script.get("entry") in bp.files, f"BP script entry '{script.get('entry')}' not found (did the build run?)")
    rp_modules = rpm.get("modules", [])
    report.check(len(rp_modules) == 1 and rp_modules[0].get("type") == "resources", "RP manifest must have one 'resources' module")
    report.check(bool(rp_modules) and rp_modules[0].get("uuid") == PERMANENT_UUIDS["rp_resources"], "RP resources module UUID changed")

    report.check(bph.get("version") == rph.get("version"), "BP and RP header versions must match")
    report.check(bph.get("min_engine_version") == rph.get("min_engine_version"), "BP and RP min_engine_version must match")
    bp_pack_deps = [d for d in bpm.get("dependencies", []) if "uuid" in d]
    rp_pack_deps = [d for d in rpm.get("dependencies", []) if "uuid" in d]
    report.check(bp_pack_deps == [{"uuid": rph.get("uuid"), "version": rph.get("version")}],
                 "BP must depend on the RP (uuid + current version) and on no other pack")
    report.check(rp_pack_deps == [{"uuid": bph.get("uuid"), "version": bph.get("version")}],
                 "RP must depend on the BP (uuid + current version) and on no other pack")
    report.check(not any("module_name" in d for d in rpm.get("dependencies", [])), "RP must not declare script modules")

    modules = {d["module_name"]: d.get("version") for d in bpm.get("dependencies", []) if "module_name" in d}
    report.check("@minecraft/server" in modules, "BP must depend on @minecraft/server")
    for name, version in modules.items():
        installed = installed_version(root, name)
        if report.check(installed is not None, f"typings for {name} are not installed (run `npm ci`)"):
            report.check(version == installed, f"BP depends on {name} {version} but the installed typings are {installed}; "
                                               "keep them identical so the typecheck matches the runtime API")
        report.check(isinstance(version, str) and "beta" not in version,
                     f"{name} {version}: only stable Script API versions are allowed")
    return ".".join(str(n) for n in bph.get("version", [])), set(modules)


def check_version_sync(report, root, version):
    with open(os.path.join(root, "package.json"), encoding="utf-8") as f:
        report.check(json.load(f).get("version") == version, f"package.json version must be {version}")
    lock = os.path.join(root, "package-lock.json")
    if os.path.exists(lock):
        with open(lock, encoding="utf-8") as f:
            report.check(json.load(f).get("version") == version, f"package-lock.json version must be {version}")
    with open(os.path.join(root, "src", "config.ts"), encoding="utf-8") as f:
        m = re.search(r'export const VERSION = "([^"]+)"', f.read())
    report.check(m and m.group(1) == version, f'src/config.ts VERSION must be "{version}"')


def check_icons(report, pack):
    path = pack.files.get("pack_icon.png")
    if report.check(path, f"{pack.label}: pack_icon.png is missing"):
        size = png_size(path)
        report.check(size and size[0] == size[1], f"{pack.label}: pack_icon.png must be square, got {size}")


# --------------------------------------------------------------------------- lang

def load_lang(report, rp):
    languages = rp.json.get("texts/languages.json")
    report.check(isinstance(languages, list) and "en_US" in languages, "RP texts/languages.json must list en_US")
    keys = {}
    for code in languages if isinstance(languages, list) else []:
        rel = f"texts/{code}.lang"
        if not report.check(rel in rp.files, f"RP: {rel} listed in languages.json but missing"):
            continue
        seen = set()
        with open(rp.files[rel], encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                text = line.rstrip("\r\n")
                if not text.strip() or text.lstrip().startswith("##"):
                    continue
                key, sep, _ = text.partition("=")
                report.check(sep and key and " " not in key and "\t" not in key,
                             f"RP/{rel} line {n}: expected 'key=value' with no spaces in the key")
                report.check(key not in seen, f"RP/{rel} line {n}: duplicate key '{key}'")
                seen.add(key)
        keys[code] = seen
    return keys


# --------------------------------------------------------------------------- resource pack definitions

def walk_actions(node, found):
    """Collects component group names referenced by add/remove anywhere in an event tree."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("add", "remove") and isinstance(v, dict):
                found.update(v.get("component_groups", []))
            walk_actions(v, found)
    elif isinstance(node, list):
        for v in node:
            walk_actions(v, found)


def check_geometry(report, rp):
    geometries = {}
    for rel, data in rp.json.items():
        if not isinstance(data, dict):
            continue
        legacy = [k for k in data if k.startswith("geometry.")]
        report.check(not legacy, f"RP/{rel}: legacy geometry format; export with Blockbench 'Bedrock Entity' (1.12.0+)")
        for geo in data.get("minecraft:geometry", []):
            desc = geo.get("description", {})
            gid = desc.get("identifier", "")
            where = f"RP/{rel} {gid}"
            report.check(gid.startswith(PREFIX["geometry"]), f"{where}: identifier must start with '{PREFIX['geometry']}'")
            report.check(gid not in geometries, f"{where}: geometry defined more than once")
            tw, th = desc.get("texture_width", 16), desc.get("texture_height", 16)
            bones = geo.get("bones", [])
            names = [b.get("name") for b in bones]
            report.check(len(names) == len(set(n.lower() for n in names if n)) and all(names),
                         f"{where}: bone names must be present and unique")
            parents = {b.get("name"): b.get("parent") for b in bones}
            for b in bones:
                bname = b.get("name")
                if b.get("parent") is not None:
                    report.check(b["parent"] in parents, f"{where}: bone '{bname}' has unknown parent '{b['parent']}'")
                seen, cur = set(), bname
                while cur in parents and cur not in seen:
                    seen.add(cur)
                    cur = parents[cur]
                report.check(cur not in seen, f"{where}: bone parent cycle at '{bname}'")
                for cube in b.get("cubes", []):
                    check_cube_uv(report, f"{where} bone '{bname}'", cube, tw, th)
            geometries[gid] = {"bones": {n.lower() for n in names if n}, "size": (tw, th), "rel": rel}
    return geometries


def check_cube_uv(report, where, cube, tw, th):
    uv = cube.get("uv")
    eps = 1e-6
    if isinstance(uv, list) and len(uv) == 2:
        x, y, z = (math.floor(s) for s in cube.get("size", [0, 0, 0]))
        u, v = uv
        report.check(u >= 0 and v >= 0 and u + 2 * (x + z) <= tw + eps and v + z + y <= th + eps,
                     f"{where}: box UV {uv} with size {cube.get('size')} exceeds the {tw}x{th} texture")
    elif isinstance(uv, dict):
        for face, f in uv.items():
            (u, v), (w, h) = f.get("uv", [0, 0]), f.get("uv_size", [0, 0])
            report.check(min(u, u + w) >= -eps and min(v, v + h) >= -eps and max(u, u + w) <= tw + eps
                         and max(v, v + h) <= th + eps, f"{where}: {face} UV exceeds the {tw}x{th} texture")


def collect_definitions(report, pack, root_key, prefix, folder):
    out = {}
    for rel, data in pack.json_with(root_key):
        report.check(rel.startswith(folder + "/"), f"{pack.where(rel)}: '{root_key}' files belong in {folder}/")
        defs = data[root_key]
        if not report.check(isinstance(defs, dict), f"{pack.where(rel)}: '{root_key}' must be an object"):
            continue
        for name, definition in defs.items():
            report.check(name.startswith(prefix), f"{pack.where(rel)}: '{name}' must start with '{prefix}'")
            report.check(name not in out, f"{pack.where(rel)}: '{name}' defined more than once")
            out[name] = definition
    return out


def check_particles(report, rp):
    particles = set()
    for rel, data in rp.json_with("particle_effect"):
        desc = data["particle_effect"].get("description", {})
        pid = desc.get("identifier", "")
        where = f"RP/{rel}"
        report.check(rel.startswith("particles/"), f"{where}: particle files belong in particles/")
        report.check(OWN_ID.match(pid), f"{where}: identifier must be '{NAMESPACE}:<name>'")
        particles.add(pid)
        texture = desc.get("basic_render_parameters", {}).get("texture")
        if texture:
            rp.resolve(report, texture, TEXTURE_EXTENSIONS, "texture", where)
    return particles


def check_sounds(report, rp, entity_ids):
    sound_names = set()
    data = rp.json.get("sounds/sound_definitions.json")
    if isinstance(data, dict):
        for name, definition in data.get("sound_definitions", {}).items():
            where = f"RP/sounds/sound_definitions.json {name}"
            report.check(name.startswith(PREFIX["sound"]), f"{where}: sound names must start with '{PREFIX['sound']}'")
            sound_names.add(name)
            for entry in definition.get("sounds", []):
                ref = entry.get("name") if isinstance(entry, dict) else entry
                if isinstance(entry, dict) and entry.get("is_event"):
                    continue
                if report.check(isinstance(ref, str), f"{where}: sound entry without a file name"):
                    rp.resolve(report, ref, SOUND_EXTENSIONS, "sound file", where)
    sounds = rp.json.get("sounds.json")
    if isinstance(sounds, dict):
        for eid, entry in sounds.get("entity_sounds", {}).get("entities", {}).items():
            where = f"RP/sounds.json {eid}"
            report.check(eid in entity_ids, f"{where}: not an entity of this add-on")
            for event, value in entry.get("events", {}).items():
                name = value.get("sound") if isinstance(value, dict) else value
                if isinstance(name, str) and name.startswith(PREFIX["sound"]):
                    report.check(name in sound_names, f"{where} event '{event}': sound '{name}' is not defined")
    return sound_names


def check_render_controller_refs(report, where, rc, desc):
    keys = {"geometry": desc.get("geometry", {}), "texture": desc.get("textures", {}), "material": desc.get("materials", {})}
    text = json.dumps(rc)
    for kind, key in re.findall(r"\b(Geometry|Texture|Material)\.([A-Za-z0-9_]+)", text, re.IGNORECASE):
        report.check(key in keys[kind.lower()], f"{where}: render controller uses {kind}.{key} but the entity defines no such {kind.lower()}")


def check_client_entities(report, rp, geometries, animations, controllers, render_controllers, particles, bp_entities):
    client_ids = set()
    for rel, data in rp.json_with("minecraft:client_entity"):
        desc = data["minecraft:client_entity"].get("description", {})
        eid = desc.get("identifier", "")
        where = f"RP/{rel} ({eid})"
        report.check(rel.startswith("entity/"), f"RP/{rel}: client entity files belong in entity/")
        report.check(eid not in client_ids, f"{where}: client entity defined more than once")
        client_ids.add(eid)
        report.check(eid in bp_entities, f"{where}: no behavior pack entity with this identifier")

        bones = set()
        for key, gid in desc.get("geometry", {}).items():
            if report.check(gid in geometries, f"{where}: geometry '{gid}' not found"):
                bones |= geometries[gid]["bones"]
        for key, tex in desc.get("textures", {}).items():
            rp.resolve(report, tex, TEXTURE_EXTENSIONS, f"texture '{key}'", where)

        anim_map = desc.get("animations", {})
        for short, name in anim_map.items():
            if name.startswith(PREFIX["animation"]):
                if report.check(name in animations, f"{where}: animation '{name}' not found"):
                    for bone in animations[name].get("bones", {}):
                        report.check(bone.lower() in bones, f"{where}: animation '{name}' moves bone '{bone}' "
                                                            "which none of the entity's geometries has")
            elif name.startswith(PREFIX["animation_controller"]):
                if report.check(name in controllers, f"{where}: animation controller '{name}' not found"):
                    check_controller(report, f"{where} {name}", controllers[name], anim_map)
            # Any other name is a vanilla animation/controller, resolved by the game.
        for entry in desc.get("scripts", {}).get("animate", []):
            short = entry if isinstance(entry, str) else next(iter(entry), "")
            report.check(short in anim_map, f"{where}: scripts.animate uses '{short}' which is not in animations")
        for entry in desc.get("render_controllers", []):
            name = entry if isinstance(entry, str) else next(iter(entry), "")
            if name.startswith(PREFIX["render_controller"]):
                if report.check(name in render_controllers, f"{where}: render controller '{name}' not found"):
                    check_render_controller_refs(report, f"{where} {name}", render_controllers[name], desc)
        for key, pid in desc.get("particle_effects", {}).items():
            if pid.startswith(f"{NAMESPACE}:"):
                report.check(pid in particles, f"{where}: particle '{pid}' not found")
    return client_ids


def check_controller(report, where, controller, anim_map):
    states = controller.get("states", {})
    initial = controller.get("initial_state", "default")
    report.check(initial in states, f"{where}: initial state '{initial}' not defined")
    for sname, state in states.items():
        for entry in state.get("animations", []):
            short = entry if isinstance(entry, str) else next(iter(entry), "")
            report.check(short in anim_map, f"{where} state '{sname}': '{short}' is not in the entity's animations")
        for transition in state.get("transitions", []):
            for target in transition:
                report.check(target in states, f"{where} state '{sname}': transition to unknown state '{target}'")


# --------------------------------------------------------------------------- behavior pack definitions

def check_bp(report, bp, lang):
    entities = {}
    for rel, data in bp.json_with("minecraft:entity"):
        entity = data["minecraft:entity"]
        eid = entity.get("description", {}).get("identifier", "")
        where = f"BP/{rel} ({eid})"
        report.check(rel.startswith("entities/"), f"BP/{rel}: entity files belong in entities/")
        report.check(OWN_ID.match(eid), f"{where}: identifier must be '{NAMESPACE}:<name>' (no vanilla overrides)")
        report.check(eid not in entities, f"{where}: entity defined more than once")
        report.check(isinstance(data.get("format_version"), str), f"{where}: format_version is required")
        entities[eid] = entity
        groups = entity.get("component_groups", {})
        used = set()
        walk_actions(entity.get("events", {}), used)
        for g in sorted(used):
            report.check(g in groups, f"{where}: an event adds/removes unknown component group '{g}'")
        for prop in entity.get("description", {}).get("properties", {}):
            report.check(OWN_ID.match(prop), f"{where}: property '{prop}' must be '{NAMESPACE}:<name>'")
        for comps in [entity.get("components", {}), *groups.values()]:
            for comp in ("minecraft:loot", "minecraft:equipment"):
                table = comps.get(comp, {}).get("table")
                if table:
                    ref, ext = os.path.splitext(table)
                    report.check(ext == ".json", f"{where}: {comp} table must be a .json path")
                    bp.resolve(report, ref, (".json",), f"{comp} table", where)
        report.check(f"entity.{eid}.name" in lang.get("en_US", set()), f"{where}: en_US.lang has no 'entity.{eid}.name'")
        if entity.get("description", {}).get("is_spawnable"):
            key = f"item.spawn_egg.entity.{eid}.name"
            report.warn(key in lang.get("en_US", set()), f"{where}: spawnable entity without '{key}' in en_US.lang")

    for rel, data in bp.json_with("minecraft:spawn_rules"):
        eid = data["minecraft:spawn_rules"].get("description", {}).get("identifier", "")
        report.check(rel.startswith("spawn_rules/"), f"BP/{rel}: spawn rules belong in spawn_rules/")
        report.check(eid in entities, f"BP/{rel}: spawn rule for unknown entity '{eid}'")
    for key in ("minecraft:item", "minecraft:block"):
        for rel, data in bp.json_with(key):
            ident = data[key].get("description", {}).get("identifier", "")
            report.check(OWN_ID.match(ident), f"BP/{rel}: identifier must be '{NAMESPACE}:<name>'")
    for rel, data in bp.json.items():
        if rel.startswith("loot_tables/"):
            report.check(isinstance(data, dict) and isinstance(data.get("pools"), list), f"BP/{rel}: loot table needs 'pools'")
    return entities


# --------------------------------------------------------------------------- scripts

IMPORT_RE = re.compile(r"""(?:\bfrom\s*|\bimport\s*\(?\s*)["']([^"']+)["']""")


def check_scripts(report, bp, declared_modules):
    for rel in sorted(r for r in bp.files if r.endswith(".js")):
        with open(bp.files[rel], encoding="utf-8") as f:
            source = f.read()
        for spec in IMPORT_RE.findall(source):
            where = f"BP/{rel}: import '{spec}'"
            if spec.startswith("."):
                target = os.path.normpath(os.path.join(os.path.dirname(rel), spec)).replace(os.sep, "/")
                report.check(spec.endswith(".js"), f"{where} must end with .js")
                report.check(target in bp.files, f"{where} does not resolve to a file (paths are case-sensitive)")
            else:
                report.check(spec in declared_modules, f"{where} is not a dependency in the BP manifest")


# --------------------------------------------------------------------------- entry point

def validate(root):
    report = Report()
    build = os.path.join(root, "build")
    bp_dir = os.path.join(build, "behavior_packs", PACK_DIR)
    rp_dir = os.path.join(build, "resource_packs", PACK_DIR)
    if not report.check(os.path.isdir(bp_dir) and os.path.isdir(rp_dir), "build/ is missing: run `python3 tools/build.py`"):
        return report
    bp, rp = Pack("BP", bp_dir), Pack("RP", rp_dir)
    for pack in (bp, rp):
        check_files(report, pack)
        check_icons(report, pack)
    manifest_info = check_manifests(report, root, bp, rp)
    declared_modules = set()
    if manifest_info:
        version, declared_modules = manifest_info
        check_version_sync(report, root, version)
    lang = load_lang(report, rp)

    bp_entities = check_bp(report, bp, lang)
    geometries = check_geometry(report, rp)
    animations = collect_definitions(report, rp, "animations", PREFIX["animation"], "animations")
    controllers = collect_definitions(report, rp, "animation_controllers", PREFIX["animation_controller"], "animation_controllers")
    render_controllers = collect_definitions(report, rp, "render_controllers", PREFIX["render_controller"], "render_controllers")
    particles = check_particles(report, rp)
    client_ids = check_client_entities(report, rp, geometries, animations, controllers, render_controllers, particles, bp_entities)
    for eid in sorted(set(bp_entities) - client_ids):
        report.check(False, f"BP entity '{eid}' has no client entity in RP/entity/")
    check_sounds(report, rp, set(bp_entities))
    for name in ("animations", "animation_controllers"):
        for rel, _ in bp.json_with(name):
            report.check(False, f"BP/{rel}: server-side {name} are not covered by this validator yet; extend tools/validate.py first")
    check_scripts(report, bp, declared_modules)
    return report


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report = validate(root)
    report.print()
    sys.exit(1 if report.errors else 0)


if __name__ == "__main__":
    main()
