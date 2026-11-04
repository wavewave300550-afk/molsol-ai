// npm run package  ->  dist/Extra_Super_Boss_Da_Vinci_v1.mcaddon
// Uses Minecraft Creator Tools `exportaddon`, then checks the archive holds both packs and every asset.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DIST = path.join(ROOT, "dist");
const NAME = "Extra_Super_Boss_Da_Vinci_v1.mcaddon";

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "ct-export-"));
execFileSync("npx", ["-y", "@minecraft/creator-tools@0.20.0", "exportaddon", "-i", path.join(ROOT, "addon"), "-o", tmp],
  { stdio: ["ignore", "inherit", "inherit"] });
const built = fs.readdirSync(tmp).find((f) => f.endsWith(".mcaddon"));
if (!built) throw new Error("exportaddon produced no .mcaddon");
fs.mkdirSync(DIST, { recursive: true });
const target = path.join(DIST, NAME);
fs.copyFileSync(path.join(tmp, built), target);
fs.rmSync(tmp, { recursive: true, force: true });

// minimal zip central-directory reader to verify the contents
const buf = fs.readFileSync(target);
const eocd = buf.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));
const count = buf.readUInt16LE(eocd + 10);
let off = buf.readUInt32LE(eocd + 16);
const names = [];
for (let i = 0; i < count; i++) {
  const nameLen = buf.readUInt16LE(off + 28);
  const extra = buf.readUInt16LE(off + 30);
  const comment = buf.readUInt16LE(off + 32);
  names.push(buf.toString("utf8", off + 46, off + 46 + nameLen));
  off += 46 + nameLen + extra + comment;
}
// every file of both packs must be in the archive
const missing = [];
for (const pack of ["behavior_packs", "resource_packs"]) {
  const dir = path.join(ROOT, "addon", pack, "extra_super_boss");
  for (const f of fs.readdirSync(dir, { recursive: true })) {
    const full = path.join(dir, f);
    if (fs.statSync(full).isDirectory()) continue;
    const rel = f.split(path.sep).join("/");
    if (!names.some((n) => n.endsWith(rel))) missing.push(`${pack}/${rel}`);
  }
}
if (missing.length) throw new Error(`archive is missing: ${missing.join(", ")}`);
if (names.some((n) => n.includes(".mct/"))) throw new Error("archive contains the .mct tool folder");
console.log(`${path.relative(ROOT, target)}  (${(buf.length / 1024).toFixed(1)} KB, ${names.length} entries)`);
