#!/usr/bin/env python3
"""Merge result files from parallel BDS runs into one evidence file (logs are concatenated)."""
import json
import sys


def main(out, *inputs):
    replace = None
    if "--replace-with" in inputs:
        i = inputs.index("--replace-with")
        replace, inputs = inputs[i + 1], inputs[:i] + inputs[i + 2:]
    parts, results, problems, completed, version = [], [], [], True, None
    logs = []
    notes = []
    rep_suites = set()
    if replace:
        rr = json.load(open(replace))
        rep_suites = {x["suite"].split(":")[0] for x in rr["results"]}
        inputs = list(inputs) + [replace]
    for path in inputs:
        r = json.load(open(path))
        if replace and path != replace:
            dropped = [x for x in r["results"] if x["suite"].split(":")[0] in rep_suites]
            if dropped:
                notes.append(f"{len(dropped)} checks of `{', '.join(sorted(rep_suites))}` from {path.split('/')[-1]} were replaced by the re-run "
                             f"{replace.split('/')[-1]} ({sum(1 for x in dropped if not x['ok'])} of them had failed: " +
                             "; ".join(x["name"] for x in dropped if not x["ok"]) + ")")
            r["results"] = [x for x in r["results"] if x["suite"].split(":")[0] not in rep_suites]
        version = version or r["server_version"]
        suites = list(dict.fromkeys(x["suite"].split(":")[0] for x in r["results"]))
        parts.append({"file": path.split("/")[-1], "suites": suites, "passed": sum(1 for x in r["results"] if x["ok"]), "total": len(r["results"])})
        results += r["results"]
        problems += r["log_problems"]
        completed = completed and r["completed"]
        logs.append(open(path[:-5] + ".log", encoding="utf-8", errors="replace").read())
    rep = {"server_version": version, "completed": completed, "summary": {"total": len(results), "failed": sum(1 for x in results if not x["ok"])},
           "results": results, "log_problems": problems, "parts": parts, "notes": notes}
    json.dump(rep, open(out, "w"), indent=1)
    with open(out[:-5] + ".log", "w", encoding="utf-8") as f:
        f.write("\n\n======== next server ========\n\n".join(logs))
    print(f"{out}: {len(results)} checks, {rep['summary']['failed']} failed, {len(problems)} log problems")


if __name__ == "__main__":
    main(*sys.argv[1:])
