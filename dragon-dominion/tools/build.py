"""
Build and package Dragon Dominion.

    python3 tools/build.py              stage build/ (copy packs + compile TypeScript)
    python3 tools/build.py --package    stage, validate, then write dist/*.mcaddon and *.mcpack

Source packs live in behavior_packs/ and resource_packs/. The build copies them
(skipping dotfiles and Markdown) into build/, compiles src/ into the behavior
pack's scripts/ folder, and packages the result. Archives are deterministic:
sorted entries and fixed timestamps, so the same sources give identical bytes.
Only the Python standard library and the project's npm dev dependencies are used.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "build")
DIST = os.path.join(ROOT, "dist")

PACK_DIR = "dragon_dominion"
# (source folder, folder name inside the .mcaddon, .mcpack label)
PACKS = [
    ("behavior_packs", "dragon_dominion_bp", "BP"),
    ("resource_packs", "dragon_dominion_rp", "RP"),
]
ADDON_FILE_STEM = "Dragon_Dominion"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
EXCLUDED_SUFFIXES = (".md",)


def log(msg):
    print(f"[build] {msg}")


def ignore_sources(_dir, names):
    return [n for n in names if n.startswith(".") or n.endswith(EXCLUDED_SUFFIXES)]


def stage():
    if os.path.isdir(BUILD):
        shutil.rmtree(BUILD)
    for source, _, _ in PACKS:
        src = os.path.join(ROOT, source, PACK_DIR)
        dst = os.path.join(BUILD, source, PACK_DIR)
        shutil.copytree(src, dst, ignore=ignore_sources)
        log(f"copied {source}/{PACK_DIR}")
    compile_scripts()


def compile_scripts():
    tsc = os.path.join(ROOT, "node_modules", "typescript", "bin", "tsc")
    if not os.path.exists(tsc):
        sys.exit("[build] TypeScript is not installed: run `npm ci` first")
    result = subprocess.run(["node", tsc, "-p", os.path.join(ROOT, "tsconfig.json")], cwd=ROOT)
    if result.returncode != 0:
        sys.exit("[build] TypeScript compilation failed")
    log("compiled src/ -> behavior pack scripts/")


def pack_version():
    with open(os.path.join(BUILD, "behavior_packs", PACK_DIR, "manifest.json"), encoding="utf-8") as f:
        return ".".join(str(n) for n in json.load(f)["header"]["version"])


def pack_files(folder):
    """Sorted (absolute path, archive-relative path) pairs, forward slashes only."""
    out = []
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames.sort()
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            out.append((path, os.path.relpath(path, folder).replace(os.sep, "/")))
    return out


def write_zip(target, entries):
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path, arcname in entries:
            info = zipfile.ZipInfo(arcname, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(path, "rb") as f:
                zf.writestr(info, f.read())


def package():
    version = pack_version()
    os.makedirs(DIST, exist_ok=True)
    for name in os.listdir(DIST):
        if name.endswith((".mcaddon", ".mcpack")) or name == "SHA256SUMS":
            os.remove(os.path.join(DIST, name))

    outputs = []
    addon_entries = []
    for source, addon_folder, label in PACKS:
        folder = os.path.join(BUILD, source, PACK_DIR)
        files = pack_files(folder)
        addon_entries += [(p, f"{addon_folder}/{rel}") for p, rel in files]
        mcpack = os.path.join(DIST, f"{ADDON_FILE_STEM}_{label}_v{version}.mcpack")
        write_zip(mcpack, files)
        outputs.append(mcpack)
    mcaddon = os.path.join(DIST, f"{ADDON_FILE_STEM}_v{version}.mcaddon")
    write_zip(mcaddon, addon_entries)
    outputs.insert(0, mcaddon)

    lines = []
    for path in outputs:
        with open(path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        lines.append(f"{digest}  {os.path.basename(path)}")
        log(f"wrote dist/{os.path.basename(path)} ({os.path.getsize(path)} bytes)")
    with open(os.path.join(DIST, "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--package", action="store_true", help="validate and write dist/ archives after staging")
    args = parser.parse_args()
    stage()
    if args.package:
        sys.path.insert(0, HERE)
        import validate  # noqa: E402

        report = validate.validate(ROOT)
        report.print()
        if report.errors:
            sys.exit("[build] validation failed: nothing was packaged")
        package()
    log("done")


if __name__ == "__main__":
    main()
