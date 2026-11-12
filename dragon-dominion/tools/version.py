"""
Set the add-on version everywhere it is recorded:

    python3 tools/version.py 0.2.0        (or: npm run set-version -- 0.2.0)

Updates package.json, package-lock.json, src/config.ts and both manifests
(header, modules and the BP<->RP dependency versions). UUIDs never change.
Bedrock only replaces an installed pack when its header version increases,
so raise the version for every build that leaves your machine.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFESTS = [os.path.join(ROOT, p, "dragon_dominion", "manifest.json") for p in ("behavior_packs", "resource_packs")]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def manifest_text(data):
    """2-space JSON with version triples kept on one line, matching the committed style."""
    text = json.dumps(data, indent=2, ensure_ascii=False)
    return re.sub(r"\[\s+(\d+),\s+(\d+),\s+(\d+)\s+\]", r"[\1, \2, \3]", text) + "\n"


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        sys.exit("usage: python3 tools/version.py MAJOR.MINOR.PATCH")
    version = sys.argv[1]
    triple = [int(n) for n in version.split(".")]

    manifests = [load(p) for p in MANIFESTS]
    current = manifests[0]["header"]["version"]
    if triple <= current:
        sys.exit(f"new version {version} must be higher than the current {'.'.join(map(str, current))}")
    pack_uuids = {m["header"]["uuid"] for m in manifests}
    for path, data in zip(MANIFESTS, manifests):
        data["header"]["version"] = triple
        for module in data.get("modules", []):
            module["version"] = triple
        for dep in data.get("dependencies", []):
            if dep.get("uuid") in pack_uuids:
                dep["version"] = triple
        write(path, manifest_text(data))

    for name in ("package.json", "package-lock.json"):
        path = os.path.join(ROOT, name)
        data = load(path)
        data["version"] = version
        if name == "package-lock.json" and "" in data.get("packages", {}):
            data["packages"][""]["version"] = version
        write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    config = os.path.join(ROOT, "src", "config.ts")
    with open(config, encoding="utf-8") as f:
        text = f.read()
    text, count = re.subn(r'export const VERSION = "[^"]+";', f'export const VERSION = "{version}";', text)
    if count != 1:
        sys.exit("src/config.ts: VERSION constant not found")
    write(config, text)
    print(f"version set to {version}; run `npm run package` to rebuild dist/")


if __name__ == "__main__":
    main()
