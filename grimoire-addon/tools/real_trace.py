#!/usr/bin/env python3
"""Turn a Bedrock Dedicated Server log written by the probe harness (tests/probe/) into the trace
files tools/scene.py reads:  tests/.out/trace/<spell>_real[_<tag>].json

  python3 tools/real_trace.py <bds.log> [tag]
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "tests", ".out", "trace")


def main():
    log, tag = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "")
    terr = {}
    rec, done, noise = None, [], []
    for line in open(log, encoding="utf-8", errors="replace"):
        m = re.search(r"\[probe\] (\{.*\})\s*$", line)
        if not m:
            if rec is not None and ("ERROR" in line or "[grimoire]" in line or ("WARN" in line and "[Scripting]" in line)):
                if "debugger" not in line.lower():
                    rec["log"].append(line.strip()[:400])
            continue
        try:
            o = json.loads(m.group(1))
        except Exception:
            continue
        k = o.get("k")
        if k == "terr":
            terr.setdefault("rows", {})[o["zi"]] = o["row"]
            terr.update(x0=o["x0"], z0=o["z0"], n=o["n"])
        elif k == "start":
            rec = {"id": o["id"], "mode": o["mode"], "t": 0, "release": 0, "particles": [], "sounds": [], "blocks": [],
                   "actors": {}, "mobs": [], "caster": [], "problems": [], "log": [], "events": []}
        elif rec is None:
            continue
        elif k == "a":
            a = rec["actors"].setdefault(o["i"], {"type": o["r"][0], "spawn": o["t"], "end": -1, "f": []})
            a["f"].append([o["t"]] + o["r"][1:])
        elif k == "x":
            if o["i"] in rec["actors"]:
                rec["actors"][o["i"]]["end"] = o["t"]
        elif k == "p":
            rec["caster"].append([o["t"]] + o["c"])
            rec["mobs"].append([o["t"]] + o["m"])
        elif k == "ev":
            rec["events"].append(o)
            if o["e"] == "stopUsingItem":
                rec["release"] = o["t"]
        elif k == "err":
            rec["problems"].append(o)
        elif k == "end":
            rec["ticks"] = o["ticks"]
            rec["dmg"] = o.get("hp", [])
            rec["seen"] = o.get("seen")
            done.append(rec)
            rec = None
    T = None
    if terr.get("rows") and len(terr["rows"]) == terr["n"]:
        h = []
        for zi in range(terr["n"]):
            h += terr["rows"][zi]
        T = {"x0": terr["x0"], "z0": terr["z0"], "n": terr["n"], "h": h}
    os.makedirs(OUT, exist_ok=True)
    for r in done:
        if T:
            r["terrain"] = T
        if not r["mobs"]:
            r["mobs"] = [[0]]
        name = f"{r['id']}_real{('_' + tag) if tag else ''}{'' if r['mode'] == 'mobs' else '_' + r['mode']}.json"
        json.dump(r, open(os.path.join(OUT, name), "w"))
        ev = [e["e"] for e in r["events"]]
        print(f"{r['id']:5s} {r['mode']:5s} ticks {r['ticks']:5d} actors {len(r['actors']):4d} seen {r['seen']} hp {r['dmg']} "
              f"input {'ok' if 'itemStartUse' in ev and 'itemReleaseUse' in ev else ev} problems {len(r['problems'])} log {len(r['log'])}")
        for l in (r["log"][:6] + [json.dumps(p)[:300] for p in r["problems"][:3]]):
            print("      ", l)


if __name__ == "__main__":
    main()
