"""
Second-opinion validation with Microsoft's Minecraft Creator Tools (run after the build):

    python3 tools/mct_validate.py

Runs `@minecraft/creator-tools validate` (pinned below) on build/ and lists its
errors, warnings and recommendations. npx downloads the tool on first use, so
this step needs network access; tools/validate.py does not.
Exit code 1 when Creator Tools reports errors, 2 when it could not run.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

CREATOR_TOOLS = "@minecraft/creator-tools@0.21.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERROR_TYPES = {"error", "testFail", "internalProcessingError"}


def main():
    build = os.path.join(ROOT, "build")
    if not os.path.isdir(build):
        print("[mct] build/ is missing: run `python3 tools/build.py` first")
        sys.exit(2)
    npx = shutil.which("npx")
    if not npx:
        print("[mct] npx not found: install Node.js")
        sys.exit(2)
    with tempfile.TemporaryDirectory() as reports:
        # Reports go to a temp folder; --force skips the tool's result cache.
        result = subprocess.run([npx, "-y", CREATOR_TOOLS, "validate", "-i", build, "-o", reports, "--json", "--force"],
                                capture_output=True, text=True)
    start = result.stdout.find("{")
    if start < 0:
        print(f"[mct] Creator Tools produced no report (exit {result.returncode}):\n{result.stderr[-2000:]}")
        sys.exit(2)
    report = json.loads(result.stdout[start:])
    items = [i for p in report.get("projects", []) for i in p.get("items", [])]
    if not items:
        print("[mct] Creator Tools found no packs in build/")
        sys.exit(2)
    buckets = {"ERROR": [], "WARNING": [], "RECOMMENDATION": []}
    for item in items:
        kind = item.get("type")
        if kind in ERROR_TYPES:
            buckets["ERROR"].append(item)
        elif kind == "warning":
            buckets["WARNING"].append(item)
        elif kind == "recommendation":
            buckets["RECOMMENDATION"].append(item)
    print(f"[mct] {CREATOR_TOOLS}: {len(items)} results, {len(buckets['ERROR'])} errors, "
          f"{len(buckets['WARNING'])} warnings, {len(buckets['RECOMMENDATION'])} recommendations")
    for label, found in buckets.items():
        for item in found:
            where = item.get("projectItemPath") or item.get("itemId") or ""
            print(f"  {label}: [{item.get('generatorId')}] {item.get('message')} {where}".rstrip())
    sys.exit(1 if buckets["ERROR"] else 0)


if __name__ == "__main__":
    main()
