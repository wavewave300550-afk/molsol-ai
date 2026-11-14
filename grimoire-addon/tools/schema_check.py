#!/usr/bin/env python3
"""Validate generated behaviour-pack JSON against Mojang's official JSON schemas.

The schemas ship in the public Mojang/bedrock-samples repository (metadata/json_schemas).
Point GRIMOIRE_SCHEMAS at that folder (or pass it as argv[1]); the check is skipped when absent.

  git clone --depth 1 --filter=blob:none --sparse https://github.com/Mojang/bedrock-samples
  (cd bedrock-samples && git sparse-checkout set metadata)
  GRIMOIRE_SCHEMAS=bedrock-samples/metadata/json_schemas python3 tools/schema_check.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
from urllib.parse import quote

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GRIMOIRE_SCHEMAS", ""))
    if not base or not os.path.isdir(base):
        print("schema check skipped (official schemas not available; see tools/schema_check.py)")
        return 0
    from jsonschema import Draft7Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT7

    resources = []
    by_id = {}
    for p in glob.glob(os.path.join(base, "**", "*.json"), recursive=True):
        try:
            sch = json.load(open(p, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        sid = sch.get("$id") or "/" + os.path.relpath(p, base).replace(os.sep, "/")
        by_id[sid] = sch
        res = Resource(contents=sch, specification=DRAFT7)
        from urllib.parse import unquote as _u
        for key in {sid, quote(_u(sid), safe="/"), _u(sid)}:
            resources.append((key, res))
    registry = Registry().with_resources(resources)

    def check(doc_id, instance, label):
        from urllib.parse import unquote
        sch = by_id.get(doc_id) or by_id.get(unquote(doc_id)) or by_id.get(quote(unquote(doc_id), safe="/"))
        if sch is None:
            print(f"  (schema {doc_id} not found, skipped)")
            return 0
        v = Draft7Validator({"$ref": quote(unquote(doc_id), safe="/")}, registry=registry)
        n = 0
        for e in sorted(v.iter_errors(instance), key=lambda e: [str(x) for x in e.absolute_path]):
            path = "/".join(str(x) for x in e.absolute_path)
            if path.endswith("minecraft:timer/time") and isinstance(e.instance, (int, float)):
                continue   # schema lists only the {min,max} form; vanilla 1.26.50 entities use plain numbers
            n += 1
            print(f"  SCHEMA {label}: {path}: {e.message[:200]}")
        return n

    bad = 0
    items = sorted(glob.glob(os.path.join(ROOT, "behavior_packs/grimoire_bp/items/*.json")))
    for p in items:
        j = json.load(open(p))
        bad += check("/server/item/1.26.50/ItemDocument.json", j["minecraft:item"], os.path.basename(p))
    ents = sorted(glob.glob(os.path.join(ROOT, "behavior_packs/grimoire_bp/entities/*.json")))
    for p in ents:
        j = json.load(open(p))
        for ver in ("1.21.90", "1.26.60"):   # the declared format and the newest strict one
            bad += check(f"/server/entity/{ver}/ActorDocument.json", j["minecraft:entity"], f"{os.path.basename(p)} @{ver}")
    parts = sorted(glob.glob(os.path.join(ROOT, "resource_packs/grimoire_rp/particles/*.json")))
    for p in parts:
        j = json.load(open(p))
        bad += check("/client/particles/1.21.10/Particle%20Effect%20Data.json", j["particle_effect"], os.path.basename(p))
    print(f"schema check: {len(items)} items, {len(ents)} entities, {len(parts)} particles, {bad} violations")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
