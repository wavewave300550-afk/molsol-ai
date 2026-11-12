#!/usr/bin/env python3
"""Generate docs/SPELLS.md and docs/TESTING.md from the spell registry and real test evidence.

  python3 tools/docs.py [docs/test-evidence/final_run.json]

Nothing in TESTING.md is typed by hand: every PASS/FAIL comes from the BDS results file that
tests/run_bds.py wrote, and the static section from tools/validate.py.
"""
import json
import os
import subprocess
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
SCHOOLS = OrderedDict([("pressure", "Pressure Magic"), ("ice", "Ice Magic"), ("blood", "Blood Magic"),
                       ("plasma", "Plasma Magic"), ("darkness", "Darkness Magic"), ("prism_light", "Prism Light Magic")])
MOVEMENT = {"P10", "P11", "I10", "I11", "B10", "B11", "PL10", "PL11", "D10", "D11", "PR10", "PR11"}
KNOCKBACK_PLAYER = {"P11", "I11", "B11", "PL10", "PL11", "PR11"}
AI_MISDIRECTION = {"D07", "D09", "PR06", "PR08", "PR09"}


def fmt_params(p):
    return ", ".join(f"{k} {int(v) if float(v).is_integer() else v}" for k, v in p.items())


def spells_md(meta):
    out = ["# Spell reference", "",
           "Generated from the TypeScript spell registry (`src/spells/*/index.ts`) by `tools/docs.py`.",
           "Cooldowns are per player, per spell and start when the spell activates (I11 Wings of the Winter Seraph: when the",
           "flight ends). There is no mana, ammunition, health cost or consumable of any kind.",
           "",
           "*Prep* is the minimum time Use must be held before releasing casts the spell; releasing earlier fizzles",
           "without starting the cooldown. Holding longer is always safe: nothing fires until you release.",
           "",
           "*Empowerable*: **P13 Equilibrium Theft** stores one empowerment for 30 s. The next empowerable spell you cast",
           "(from any grimoire) consumes it for ×1.6 damage and ×1.25 area. It never stacks and costs nothing.",
           ""]
    for school, title in SCHOOLS.items():
        out += [f"## {title}", "", "| # | Spell | Cooldown | Prep | Empowerable | Description | Tuning |", "|---|---|---|---|---|---|---|"]
        for s in [s for s in meta["spells"] if s["school"] == school]:
            cd = f"{s['cooldown']} s" + (" after the flight" if s["cooldownAfterEnd"] else "")
            out.append(f"| {s['code']} | **{s['name']}** | {cd} | {s['charge'] / 20:.2f} s | {'yes' if s['enhanceable'] else 'no'} | "
                       f"{s['blurb']} | {fmt_params(s['params'])} |")
        out.append("")
    return "\n".join(out) + "\n"


def cooldown_table(meta):
    by = {k: [s for s in meta["spells"] if s["school"] == k] for k in SCHOOLS}
    rows = ["**Grimoires 01-03**", "", "| # | Pressure (orange) | CD | # | Ice (sapphire) | CD | # | Blood (crimson) | CD |", "|---|---|---|---|---|---|---|---|---|"]
    rows += _cd_rows(by, ("pressure", "ice", "blood"))
    rows += ["", "**Grimoires 04-06 (Expansion 02)**", "", "| # | Plasma (violet) | CD | # | Darkness (dark green) | CD | # | Prism Light (pearl) | CD |",
             "|---|---|---|---|---|---|---|---|---|"]
    rows += _cd_rows(by, ("plasma", "darkness", "prism_light"))
    rows.append("")
    rows.append("\\* I11's cooldown starts when the flight ends (the only exception).")
    return "\n".join(rows)


def _cd_rows(by, schools):
    rows = []
    for i in range(15):
        cells = []
        for k in schools:
            s = by[k][i]
            cells += [s["code"], s["name"], f"{s['cooldown']} s" + ("*" if s["cooldownAfterEnd"] else "")]
        rows.append("| " + " | ".join(cells) + " |")
    return rows


def bp_hash():
    """Content hash of the behaviour pack (file paths + bytes), independent of zip timestamps."""
    import hashlib
    h = hashlib.sha256()
    base = os.path.join(ROOT, "packs", "Grimoire_BP")
    for dirpath, _, files in sorted(os.walk(base)):
        for name in sorted(files):
            path = os.path.join(dirpath, name)
            h.update(os.path.relpath(path, base).encode())
            h.update(open(path, "rb").read())
    return h.hexdigest()


def log_facts(evidence):
    """Pull measurements and server build info out of the raw server log next to the results file."""
    facts = {}
    log = os.path.splitext(evidence)[0] + ".log"
    if not os.path.exists(log):
        return facts
    for line in open(log, encoding="utf-8", errors="replace"):
        if "Build ID:" in line:
            facts["build"] = line.split("Build ID:")[1].strip()
        if "Commit ID:" in line:
            facts["commit"] = line.split("Commit ID:")[1].strip()
        if '"measurement"' in line and "[HARNESS]" in line:
            try:
                facts["reuse"] = json.loads(line.split("[HARNESS]", 1)[1].strip())
            except ValueError:
                pass
    return facts


def testing_md(meta, report, validate_out, evidence_rel):
    res = report["results"]
    by_suite = OrderedDict()
    for r in res:
        by_suite.setdefault(r["suite"], []).append(r)
    total, passed = len(res), sum(1 for r in res if r["ok"])
    out = ["# Testing", "",
           f"Generated by `tools/docs.py` from `{evidence_rel}` (raw harness output: the `.log` next to it).", "",
           "## Status legend", "",
           "| Status | Meaning |", "|---|---|",
           "| **Verified in gameplay** | A person played it in a Bedrock client and saw it work. **Nothing in this project has this status**: no Bedrock client was available in the build environment. |",
           "| **Automated (in-engine)** | Exercised on the real Bedrock Dedicated Server engine by scripted simulated players that use the real inputs (crouch, hold Use, release Use, slot switching). Server-side behaviour, damage, cooldowns, constructs, blocks, summons and cleanup are observed in the running game. Client-only output (rendering, animation, particles, sound, fog, camera) is **not** observed. |",
           "| **Not tested** | No test exercised it. |",
           "| **Failed** | A test ran and failed (listed with the failing check). |",
           "",
           "## Environment", "",
           f"* Bedrock Dedicated Server **{report['server_version']}** (official Linux build, latest stable at the time of testing)",
           "* Add-on: `@minecraft/server` **2.11.0** (stable), no experiments enabled in the add-on's world settings",
           "* Test harness: a separate development-only behaviour pack (`tests/harness_bp`) that uses `@minecraft/server-gametest`"
           " (Beta APIs) **only in the generated test world**; it is not part of the shipped `.mcaddon`",
           f"* Run: `python3 tests/run_bds.py --bds <bds dir> {' '.join(report.get('suites', [])) or 'controls reuse_gap pressure ice blood plasma darkness prism_light robustness cleanup'}`",
           f"* Result: **{passed}/{total} checks passed**, {len(report['log_problems'])} Content Log errors/warnings,"
           f" run completed: {report['completed']}",
           f"* Behaviour pack under test: content hash `{bp_hash()[:16]}` (sha256 over `packs/Grimoire_BP`); it is the"
           " pack shipped in `dist/` (later commits changed only resource-pack visuals and documentation)",
           ""]
    facts = log_facts(os.path.join(ROOT, evidence_rel))
    if report.get("parts"):
        out.insert(len(out) - 1, "* Two servers ran side by side on the same build: " + "; ".join(
            f"`{', '.join(pt['suites'])}` ({pt['passed']}/{pt['total']})" for pt in report["parts"]))
    extra = []
    if facts.get("build"):
        extra.append(f"* Server build id {facts['build']}, commit {facts.get('commit', '?')[:12]}")
    if facts.get("reuse"):
        r = facts["reuse"]
        extra.append(f"* Measured engine re-use window: a new Use press is accepted from **{r.get('firstAcceptedGapTicks')} ticks**"
                     f" after a release (accepted by gap in ticks: `{json.dumps(r.get('acceptedByGap'))}`)")
    out[-1:-1] = extra
    if report["log_problems"]:
        out += ["Content Log problems:", ""] + [f"* `{p}`" for p in report["log_problems"]] + [""]

    # ----------------------------------------------------------------- per-spell matrix
    out += ["## Per-spell matrix", "",
            "*Server columns* come from the BDS run. *Client* is the same for every spell: models, animations, particles,",
            "sounds and fog exist and pass static validation, and models/animations were checked in offline renders",
            "(`docs/images/`), but none of it has been seen in a Bedrock client.", ""]
    for school, title in SCHOOLS.items():
        out += [f"### {title}", "", "| # | Spell | CD | Server (in-engine) | Checks | Client visuals / audio | Notes |", "|---|---|---|---|---|---|---|"]
        for s in [s for s in meta["spells"] if s["school"] == school]:
            checks = by_suite.get(f"{school}:{s['code']}", [])
            if not checks:
                status = "**Not tested**"
            elif all(c["ok"] for c in checks):
                status = "**Automated (in-engine): PASS**"
            else:
                status = "**Failed**: " + "; ".join(c["name"] for c in checks if not c["ok"])
            n_ok = sum(1 for c in checks if c["ok"])
            notes = []
            if s["code"] in KNOCKBACK_PLAYER:
                notes.append("player flight/dash velocity is applied with knockback, which simulated players ignore; the feel of the movement is unverified")
            elif s["code"] in MOVEMENT:
                notes.append("destination/route safety verified; movement feel unverified")
            if s["code"] in AI_MISDIRECTION:
                notes.append("mob retargeting relies on vanilla hurt_by_target reacting to the decoy; the decoy's existence is verified, mob behaviour per species is not")
            out.append(f"| {s['code']} | {s['name']} | {s['cooldown']} s | {status} | {n_ok}/{len(checks)} | Not tested in client (offline render only) | {'; '.join(notes)} |")
        out.append("")

    # ----------------------------------------------------------------- non-spell suites
    titles = OrderedDict([("controls", "Controls, selection, cooldowns, cancellation"),
                          ("reuse_gap", "Engine re-use window after a release"),
                          ("robust:dimension", "Dimension change"),
                          ("robust:pvp", "PvP and team rules, no costs"),
                          ("robust:multiplayer", "Two casters at once, ownership, disconnect"),
                          ("robust:blocks", "Temporary blocks and disconnect mid-spell"),
                          ("cleanup", "World state after every suite")])
    out += ["## Systems", ""]
    for key, title in titles.items():
        checks = by_suite.get(key, [])
        if not checks:
            continue
        ok = sum(1 for c in checks if c["ok"])
        out += [f"### {title} ({ok}/{len(checks)})", "", "| Result | Check |", "|---|---|"]
        for c in checks:
            out.append(f"| {'PASS' if c['ok'] else '**FAIL**'} | {c['name']} |")
        out.append("")

    # ----------------------------------------------------------------- per-spell check details
    out += ["## Per-spell checks (details)", ""]
    for school in SCHOOLS:
        for s in [s for s in meta["spells"] if s["school"] == school]:
            checks = by_suite.get(f"{school}:{s['code']}", [])
            if checks:
                out.append(f"* **{s['code']}** " + "; ".join(("" if c["ok"] else "FAIL: ") + c["name"].replace(s["code"] + " ", "") for c in checks))
    out.append("")

    out += ["## Static validation (`tools/validate.py`)", "", "```", validate_out.strip(), "```", "",
            "## Not verified", "",
            "* Anything a client draws or plays: the three book models in first and third person (attachable placement",
            "  was tuned from vanilla references and offline renders), page-flip / opening / charging / release",
            "  animations, all 75 construct models and their animations, the four summoned mobs' animations, 30 particle",
            "  effects, 67 sounds, 6 fogs, camera shake / fades, HUD layout on small screens.",
            "* The feel of knockback-driven player movement (P11 Skyline Pressure Rail, I11 Wings of the Winter Seraph,",
            "  B11 Arterial Current) and dash knockback on players: simulated players have no client and ignore knockback.",
            "* Frame rate on any device. No performance benchmark was run on mobile or desktop; no FPS figure is claimed.",
            "* Cooldown persistence across leaving and rejoining a world. It is implemented (player dynamic property, saved",
            "  on leave), but simulated players are not persisted between spawns, so it could not be exercised; survival of",
            "  cooldowns through death *is* tested.",
            "* Touch controls: crouch/use mapping on mobile follows the standard Bedrock controls (sneak button, hold the",
            "  screen / use button) but was not tried on a phone.",
            ""]
    return "\n".join(out) + "\n"


def main():
    meta = json.load(open(os.path.join(ROOT, ".build_meta.json")))
    evidence = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DOCS, "test-evidence", "final_run.json")
    with open(os.path.join(DOCS, "SPELLS.md"), "w") as f:
        f.write(spells_md(meta))
    readme = os.path.join(ROOT, "README.md")
    if os.path.exists(readme):
        txt = open(readme).read()
        a, b = "<!-- COOLDOWNS -->", "<!-- /COOLDOWNS -->"
        if a in txt and b in txt:
            txt = txt[: txt.index(a) + len(a)] + "\n" + cooldown_table(meta) + "\n" + txt[txt.index(b):]
            open(readme, "w").write(txt)
    if os.path.exists(evidence):
        report = json.load(open(evidence))
        parts = report.get("parts")
        if parts:
            report["suites"] = [x for part in parts for x in part["suites"]]
        v = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "validate.py")], capture_output=True, text=True)
        with open(os.path.join(DOCS, "TESTING.md"), "w") as f:
            f.write(testing_md(meta, report, v.stdout, os.path.relpath(evidence, ROOT)))
        print("wrote docs/SPELLS.md, docs/TESTING.md")
    else:
        print(f"wrote docs/SPELLS.md (no evidence file {evidence})")


if __name__ == "__main__":
    main()
