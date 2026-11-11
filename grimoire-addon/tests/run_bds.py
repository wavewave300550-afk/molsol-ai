#!/usr/bin/env python3
"""Run the in-engine test harness on the official Bedrock Dedicated Server.

Usage: python3 tests/run_bds.py --bds /path/to/bedrock-server-1.26.63.1 [suite ...]

  * creates a fresh flat test world whose level.dat enables the Beta APIs experiment
    (needed only by the dev harness pack; the add-on itself uses stable APIs only),
  * installs packs/Grimoire_BP + packs/Grimoire_RP + tests/harness_bp into that world,
  * starts the server, triggers `scriptevent harness:run <suites>` from the console,
  * collects [HARNESS] result lines and every Content Log error/warning, then stops the server.
Results are written to tests/results/latest.json and tests/results/latest.md.
"""
import argparse
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests", "bdstools"))
import make_world  # noqa: E402

WORLD = "grimoire_test"
HARNESS_UUID = "5c0b7a4e-2b0e-4a3e-9d55-7f1d3c0a9e11"


def read_manifest(path):
    with open(os.path.join(path, "manifest.json")) as f:
        m = json.load(f)
    return m["header"]["uuid"], m["header"]["version"]


def start_server(bds):
    env = dict(os.environ, LD_LIBRARY_PATH=bds)
    p = subprocess.Popen(["./bedrock_server"], cwd=bds, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, bufsize=1)
    q = queue.Queue()

    def pump():
        for line in p.stdout:
            q.put(line.rstrip("\n"))
        q.put(None)

    threading.Thread(target=pump, daemon=True).start()
    return p, q


def ensure_template(bds):
    tpl = os.path.join(bds, "grimoire_level_template.dat")
    if os.path.exists(tpl):
        return tpl
    wdir = os.path.join(bds, "worlds", WORLD)
    shutil.rmtree(wdir, ignore_errors=True)
    p, q = start_server(bds)
    t0 = time.time()
    while time.time() - t0 < 60:
        try:
            line = q.get(timeout=1)
        except queue.Empty:
            continue
        if line is None or "Server started" in line:
            break
    p.stdin.write("stop\n")
    p.stdin.flush()
    p.wait(timeout=60)
    shutil.copy(os.path.join(wdir, "level.dat"), tpl)
    return tpl


def configure(bds):
    props = os.path.join(bds, "server.properties")
    s = open(props).read()
    for k, v in {"level-name": WORLD, "allow-cheats": "true", "online-mode": "false", "content-log-console-output-enabled": "true",
                 "content-log-file-enabled": "true", "content-log-level": "info", "difficulty": "normal", "allow-list": "false",
                 "view-distance": "10", "tick-distance": "6", "gamemode": "survival"}.items():
        s = re.sub(rf"^{re.escape(k)}=.*$", f"{k}={v}", s, flags=re.M)
    open(props, "w").write(s)


def install(bds):
    wdir = os.path.join(bds, "worlds", WORLD)
    make_world.make(wdir, ensure_template(bds), beta=True)
    bp_dir = os.path.join(wdir, "behavior_packs")
    rp_dir = os.path.join(wdir, "resource_packs")
    os.makedirs(bp_dir)
    os.makedirs(rp_dir)
    shutil.copytree(os.path.join(ROOT, "packs", "Grimoire_BP"), os.path.join(bp_dir, "Grimoire_BP"))
    shutil.copytree(os.path.join(ROOT, "tests", "harness_bp"), os.path.join(bp_dir, "Grimoire_Harness"))
    shutil.copytree(os.path.join(ROOT, "packs", "Grimoire_RP"), os.path.join(rp_dir, "Grimoire_RP"))
    bpu, bpv = read_manifest(os.path.join(bp_dir, "Grimoire_BP"))
    rpu, rpv = read_manifest(os.path.join(rp_dir, "Grimoire_RP"))
    with open(os.path.join(wdir, "world_behavior_packs.json"), "w") as f:
        json.dump([{"pack_id": bpu, "version": bpv}, {"pack_id": HARNESS_UUID, "version": [1, 0, 0]}], f)
    with open(os.path.join(wdir, "world_resource_packs.json"), "w") as f:
        json.dump([{"pack_id": rpu, "version": rpv}], f)


LOG_PROBLEM = re.compile(r"\b(ERROR|WARN)\]")


def run(bds, suites, timeout):
    configure(bds)
    install(bds)
    p, q = start_server(bds)
    results, problems, lines = [], [], []
    started = done = False
    t0 = time.time()
    summary = None
    while time.time() - t0 < timeout:
        try:
            line = q.get(timeout=1)
        except queue.Empty:
            continue
        if line is None:
            break
        lines.append(line)
        if "[HARNESS]" in line:
            payload = line.split("[HARNESS]", 1)[1].strip()
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                obj = {"raw": payload}
            if obj.get("ready") and not started:
                started = True
                p.stdin.write(f"scriptevent harness:run {' '.join(suites)}\n")
                p.stdin.flush()
            elif "ok" in obj:
                results.append(obj)
                mark = "PASS" if obj["ok"] else "FAIL"
                print(f"  {mark} [{obj['suite']}] {obj['name']}" + ("" if obj["ok"] else f"  -> {json.dumps(obj.get('detail'))[:300]}"))
            elif obj.get("DONE"):
                summary = obj
                done = True
                break
            elif "suiteStart" in obj:
                print(f"== suite {obj['suiteStart']}")
            elif "fatal" in obj or "error" in obj:
                problems.append(payload)
                print("  !!", payload)
        elif LOG_PROBLEM.search(line) and "Unknown command" not in line and "TELEMETRY" not in line.upper() and "[Grimoire] loaded" not in line:
            problems.append(line)
            print("  LOG", line[:400])
    try:
        p.stdin.write("stop\n")
        p.stdin.flush()
        p.wait(timeout=60)
    except Exception:
        p.kill()
    return results, problems, summary, done, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bds", default=os.environ.get("GRIMOIRE_BDS"))
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("suites", nargs="*")
    a = ap.parse_args()
    if not a.bds or not os.path.exists(os.path.join(a.bds, "bedrock_server")):
        sys.exit("Bedrock Dedicated Server not found: pass --bds or set GRIMOIRE_BDS")
    results, problems, summary, done, lines = run(a.bds, a.suites, a.timeout)
    os.makedirs(os.path.join(ROOT, "tests", "results"), exist_ok=True)
    version = next((l.split("Version:")[1].strip() for l in lines if "Version:" in l), "unknown")
    report = {"server_version": version, "completed": done, "summary": summary, "results": results, "log_problems": problems}
    tag = "_".join(a.suites) if a.suites else "all"
    with open(os.path.join(ROOT, "tests", "results", f"{tag}.json"), "w") as f:
        json.dump(report, f, indent=1)
    with open(os.path.join(ROOT, "tests", "results", f"{tag}.log"), "w") as f:
        f.write("\n".join(lines))
    passed = sum(1 for r in results if r["ok"])
    print(f"\nBDS {version}: {passed}/{len(results)} checks passed, {len(problems)} log problems, completed={done}")
    sys.exit(0 if done and passed == len(results) and not problems else 1)


if __name__ == "__main__":
    main()
