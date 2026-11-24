// Dump the compiled arena blueprint as JSON (used by tools/arena_preview.py and the tests).
import { pathToFileURL } from "node:url";
import path from "node:path";
const dir = process.argv[2];
const out = process.argv[3];
const bp = await import(pathToFileURL(path.join(dir, "arena", "blueprint.js")).href);
const b = bp.buildBlueprint();
const fs = await import("node:fs");
fs.writeFileSync(out, JSON.stringify({
  fills: b.fills, lanterns: b.lanterns,
  floor: [...b.floor], faults: [...b.faults], gaps: [...b.gaps], minor: [...b.minorSeams],
  islands: b.islands.map((i) => ({ id: i.id, n: i.cells.length, safe: i.safe })),
  pillars: b.pillars, bottom: b.bottom, blockCount: b.blockCount,
}));
console.log("fills", b.fills.length, "blocks", b.blockCount, "islands", b.islands.map((i) => i.cells.length).join(","), "faults", b.faults.size, "gaps", b.gaps.size);
