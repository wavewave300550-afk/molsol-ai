#!/usr/bin/env python3
"""Merge result files from parallel BDS runs into one evidence file (logs are concatenated)."""
import json
import sys


def main(out, *inputs):
    parts, results, problems, completed, version = [], [], [], True, None
    logs = []
    for path in inputs:
        r = json.load(open(path))
        version = version or r["server_version"]
        suites = list(dict.fromkeys(x["suite"].split(":")[0] for x in r["results"]))
        parts.append({"file": path.split("/")[-1], "suites": suites, "passed": sum(1 for x in r["results"] if x["ok"]), "total": len(r["results"])})
        results += r["results"]
        problems += r["log_problems"]
        completed = completed and r["completed"]
        logs.append(open(path[:-5] + ".log", encoding="utf-8", errors="replace").read())
    rep = {"server_version": version, "completed": completed, "summary": {"total": len(results), "failed": sum(1 for x in results if not x["ok"])},
           "results": results, "log_problems": problems, "parts": parts}
    json.dump(rep, open(out, "w"), indent=1)
    with open(out[:-5] + ".log", "w", encoding="utf-8") as f:
        f.write("\n\n======== next server ========\n\n".join(logs))
    print(f"{out}: {len(results)} checks, {rep['summary']['failed']} failed, {len(problems)} log problems")


if __name__ == "__main__":
    main(*sys.argv[1:])
