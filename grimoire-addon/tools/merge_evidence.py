#!/usr/bin/env python3
"""Merge result files from parallel BDS runs into one evidence file (logs are concatenated)."""
import json
import sys


def main(out, *inputs):
    # --replace-with <file> (repeatable): a re-run whose suites replace the same suites in the other inputs
    replaces = []
    inputs = list(inputs)
    while "--replace-with" in inputs:
        i = inputs.index("--replace-with")
        replaces.append(inputs[i + 1])
        inputs = inputs[:i] + inputs[i + 2:]
    parts, results, problems, completed, version = [], [], [], True, None
    logs = []
    notes = []
    rep_suites = {}
    for rp in replaces:
        rr = json.load(open(rp))
        for x in rr["results"]:
            rep_suites[x["suite"].split(":")[0]] = rp
    inputs = inputs + replaces
    for path in inputs:
        r = json.load(open(path))
        if path not in replaces:
            dropped = [x for x in r["results"] if x["suite"].split(":")[0] in rep_suites]
            if dropped:
                names = sorted({x["suite"].split(":")[0] for x in dropped})
                srcs = sorted({rep_suites[n].split("/")[-1] for n in names})
                notes.append(f"{len(dropped)} checks of `{', '.join(names)}` from {path.split('/')[-1]} were replaced by the re-run "
                             f"{', '.join(srcs)} ({sum(1 for x in dropped if not x['ok'])} of them had failed: " +
                             "; ".join(x["name"] for x in dropped if not x["ok"]) + ")")
            r["results"] = [x for x in r["results"] if x["suite"].split(":")[0] not in rep_suites]
            # a suite name the harness did not know ran nothing; it is reported, not counted as an add-on problem,
            # and only when a re-run of the real suite is part of the evidence
            unknown = [p_ for p_ in r["log_problems"] if '"error":"unknown suite' in p_]
            for u in unknown:
                bad = u.split("unknown suite")[1].strip(' "}')
                real = [n for n in rep_suites if n.startswith(bad)]
                if real:
                    notes.append(f"{path.split('/')[-1]} was started with the misspelled suite name `{bad}`; the harness "
                                 f"rejected it and ran nothing for it. That suite was run separately ({rep_suites[real[0]].split('/')[-1]}).")
                    r["log_problems"] = [p_ for p_ in r["log_problems"] if p_ != u]
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
