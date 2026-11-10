// Runs every runtime test against the combined build: the full Jōki and Sekiyu smoke tests on the
// merged scripts, then the cross-fruit test.   node tools/smoke/run.mjs
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const REPO = path.dirname(ROOT);
const env = { ...process.env, SMOKE_BUILD: path.join(ROOT, "build"), SMOKE_BP: "Forbidden_BP", SMOKE_RP: "Forbidden_RP" };
const runs = [
  ["steam (Jōki smoke test)", path.join(REPO, "joki-joki-addon", "tools", "smoke", "smoke.mjs"), { SMOKE_PREFIX: "steam" }],
  ["petroleum (Sekiyu smoke test)", path.join(REPO, "sekiyu-addon", "tools", "smoke", "smoke.mjs"), { SMOKE_PREFIX: "oil" }],
  ["cross-fruit", path.join(ROOT, "tools", "smoke", "cross.mjs"), {}],
];
let failed = 0;
for (const [name, file, extra] of runs) {
  const r = spawnSync(process.execPath, [file], { env: { ...env, ...extra }, encoding: "utf8" });
  const out = (r.stdout + r.stderr).trim().split("\n");
  console.log(`== ${name}: ${out.find((l) => l.includes("assertions")) ?? "no result"}`);
  for (const l of out.filter((l) => l.includes("FAIL") || l.includes("Error"))) console.log("   " + l);
  if (r.status !== 0) failed++;
}
process.exit(failed ? 1 : 0);
