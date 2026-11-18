/**
 * Repeat the simulation suite with several random seeds and summarise.
 *   node tools/sim/seeds.mjs [count=6] [--boss name]
 * Writes build/sim_seeds.json (read by tools/report.py).
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const BASE = process.env.ABM_OUT ? path.resolve(process.env.ABM_OUT) : ROOT;
const n = Number(process.argv[2] && !process.argv[2].startsWith("--") ? process.argv[2] : 6);
const extra = process.argv.slice(2).filter((a, i, all) => a.startsWith("--") || (i > 0 && all[i - 1].startsWith("--")));
const seeds = Array.from({ length: n }, (_, i) => 101 + i * 37);
let total = 0;
let passed = 0;
const failures = [];
for (const seed of seeds) {
  const out = path.join(BASE, "build", `sim_seed_${seed}.json`);
  const r = spawnSync(process.execPath, [path.join(HERE, "run.mjs"), "--seed", String(seed), "--json", out, ...extra], { encoding: "utf8" });
  if (!fs.existsSync(out)) {
    failures.push({ seed, name: "(suite crashed)", note: (r.stderr || r.stdout).slice(-300) });
    continue;
  }
  const res = JSON.parse(fs.readFileSync(out, "utf8")).results;
  fs.unlinkSync(out);
  total += res.length;
  passed += res.filter((x) => x.ok).length;
  for (const x of res.filter((y) => !y.ok)) failures.push({ seed, name: x.name, note: x.note });
  console.log(`seed ${seed}: ${res.filter((x) => x.ok).length}/${res.length}`);
}
fs.writeFileSync(path.join(BASE, "build", "sim_seeds.json"), JSON.stringify({ seeds, total, passed, failures }, null, 1));
for (const f of failures) console.log(`  FAIL seed ${f.seed}: ${f.name} - ${f.note}`);
console.log(`${passed}/${total} scenario runs passed over ${seeds.length} seeds`);
process.exit(failures.length ? 1 : 0);
