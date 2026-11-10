// Cross-fruit test for the combined pack: both fruit powers loaded together, one fruit per body,
// no interference between the steam and petroleum systems. Uses the strict mock from sekiyu-addon.
//     node tools/smoke/cross.mjs   (after python3 tools/build.py)
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const MOCKS = path.resolve(ROOT, "..", "sekiyu-addon", "tools", "smoke");
process.env.SEKIYU_BUILD = path.join(ROOT, "build");
process.env.SEKIYU_ROOT = path.resolve(ROOT, "..", "sekiyu-addon");
process.env.SMOKE_BP = "Forbidden_BP";
process.env.SMOKE_RP = "Forbidden_RP";

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "forbidden-cross-"));
fs.cpSync(path.join(ROOT, "build", "Forbidden_BP", "scripts"), path.join(tmp, "scripts"), { recursive: true });
fs.writeFileSync(path.join(tmp, "package.json"), JSON.stringify({ type: "module" }));
for (const [pkg, file] of [["server", "mock-server.mjs"], ["server-ui", "mock-server-ui.mjs"]]) {
  const dir = path.join(tmp, "node_modules", "@minecraft", pkg);
  fs.mkdirSync(dir, { recursive: true });
  fs.copyFileSync(path.join(MOCKS, file), path.join(dir, "index.mjs"));
  fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({ name: `@minecraft/${pkg}`, type: "module", exports: "./index.mjs" }));
}
const mc = await import(pathToFileURL(path.join(tmp, "node_modules", "@minecraft", "server", "index.mjs")).href);
const { __ui } = await import(pathToFileURL(path.join(tmp, "node_modules", "@minecraft", "server-ui", "index.mjs")).href);
const { world, system, Player, ItemStack, __tick, __issues } = mc;
const warnings = [];
console.warn = (...a) => warnings.push(a.join(" "));
const logs = [];
const realLog = console.log;
console.log = (...a) => logs.push(a.join(" "));
await import(pathToFileURL(path.join(tmp, "scripts", "main.js")).href);
const { spawnPool } = await import(pathToFileURL(path.join(tmp, "scripts", "oil", "pools.js")).href);

const failures = [];
let passed = 0;
const expect = (c, m) => (c ? passed++ : failures.push(m));
const tick = async (n = 1) => {
  for (let i = 0; i < n; i++) {
    await __tick(1);
    await new Promise((r) => setImmediate(r));
  }
};
const commands = new Map();
system.beforeEvents.startup.fire({ customCommandRegistry: { registerCommand: (d, cb) => commands.set(d.name, cb), registerEnum: () => {} } });
world.afterEvents.worldLoad.fire({});
expect(logs.some((l) => l.includes("Steam Pressure loaded")) && logs.some((l) => l.includes("Petroleum loaded")), "both fruit systems load");
expect(["joki:valve", "joki:revoke", "sekiyu:core", "sekiyu:revoke"].every((c) => commands.has(c)), "both command sets registered");

const dim = world.getDimension("minecraft:overworld");
const STEAM = "joki:joki_fruit";
const OIL = "sekiyu:sekiyu_fruit";
const isSteam = (p) => p.getDynamicProperty("joki:owner") === true;
const isOil = (p) => p.getDynamicProperty("sekiyu:owner") === true;
async function eat(p, item) {
  const st = new ItemStack(item);
  const ev = world.beforeEvents.itemUse.fire({ source: p, itemStack: st, cancel: false });
  if (ev.cancel) return false;
  world.afterEvents.itemCompleteUse.fire({ source: p, itemStack: st, useDuration: 0 });
  await tick(3);
  return true;
}

const A = new Player("Steam", dim, { x: 0, y: 64, z: 0 });
const B = new Player("Oil", dim, { x: 30, y: 64, z: 0 });
for (const p of [A, B]) world.afterEvents.playerSpawn.fire({ player: p, initialSpawn: true });
await tick(25);
const welcome = A.messages.filter((m) => m.includes("Forbidden Fruits"));
expect(welcome.length === 1 && welcome[0].includes("/give @s joki:joki_fruit") && welcome[0].includes("/give @s sekiyu:sekiyu_fruit"), "one combined welcome listing both fruits");
expect(!A.messages.some((m) => m.includes("add-on active")), "no per-fruit welcome spam");

expect(await eat(A, STEAM) && isSteam(A), "A eats the steam fruit");
expect(await eat(B, OIL) && isOil(B), "B eats the petroleum fruit");
expect(A.getProperty("joki:mode") === 1 && A.getProperty("sekiyu:form") === 0, "A: steam properties only");
expect(B.getProperty("sekiyu:form") === 1 && B.getProperty("joki:mode") === 0, "B: petroleum properties only");

const refusedA = world.beforeEvents.itemUse.fire({ source: A, itemStack: new ItemStack(OIL), cancel: false });
await tick(2);
expect(refusedA.cancel && A.messages.some((m) => m.includes("One body can only hold one fruit")), "steam user cannot eat the petroleum fruit");
world.afterEvents.itemCompleteUse.fire({ source: A, itemStack: new ItemStack(OIL), useDuration: 0 });
await tick(3);
expect(!isOil(A) && isSteam(A) && A.__inv.count(OIL) === 1, "a raced second fruit is refunded, power unchanged");
const refusedB = world.beforeEvents.itemUse.fire({ source: B, itemStack: new ItemStack(STEAM), cancel: false });
expect(refusedB.cancel, "petroleum user cannot eat the steam fruit");
world.afterEvents.itemCompleteUse.fire({ source: B, itemStack: new ItemStack(STEAM), useDuration: 0 });
await tick(3);
expect(!isSteam(B) && isOil(B) && B.__inv.count(STEAM) === 1, "refund the other way too");

// steam attacks never hit petroleum constructs (the mock flags any damage to a construct)
const pool = spawnPool(dim, { x: 1.5, y: 64, z: 1 }, 2, B.id);
const zombie = dim.spawnEntity("minecraft:zombie", { x: 0, y: 64, z: 2 });
zombie.__health.effectiveMax = zombie.__health.currentValue = 300;
for (let i = 0; i < A.__inv.size; i++) if (A.__inv.slots[i]?.typeId === "joki:steam_valve") A.selectedSlotIndex = i;
__ui.queue.push("Scald Burst");
A.isSneaking = true;
world.afterEvents.itemUse.fire({ source: A, itemStack: new ItemStack("joki:steam_valve") });
A.isSneaking = false;
await tick(14);
world.afterEvents.itemUse.fire({ source: A, itemStack: new ItemStack("joki:steam_valve") });
await tick(4);
expect(zombie.__hurt.some((h) => h.by === A.id), "steam Scald Burst hits the zombie");
expect(pool && pool.e && pool.e.isValid, "the oil pool is untouched by steam");
expect(A.onScreenDisplay.actionbar.includes("HEAT") && !A.onScreenDisplay.actionbar.includes("PETROLEUM"), "steam HUD only for the steam user");
B.selectedSlotIndex = 0;
for (let i = 0; i < B.__inv.size; i++) if (B.__inv.slots[i]?.typeId === "sekiyu:crude_core") B.selectedSlotIndex = i;
await tick(8);
expect(B.onScreenDisplay.actionbar.includes("PETROLEUM") && !B.onScreenDisplay.actionbar.includes("HEAT "), "petroleum HUD only for the oil user");

// revoking frees the body for the other fruit
commands.get("joki:revoke")({ sourceEntity: A });
await tick(3);
expect(!isSteam(A) && (await eat(A, OIL)) && isOil(A), "after /joki:revoke the other fruit can be eaten");
expect(A.getProperty("joki:mode") === 0 && A.getProperty("sekiyu:form") === 1, "properties follow the new power");

expect(__issues.length === 0, `mock issues:\n  ${[...new Set(__issues)].join("\n  ")}`);
expect(warnings.length === 0, `warnings:\n  ${[...new Set(warnings)].join("\n  ")}`);
console.log = realLog;
console.log(`${passed} assertions passed, ${failures.length} failed`);
for (const f of failures) console.log("  FAIL:", f);
fs.rmSync(tmp, { recursive: true, force: true });
process.exit(failures.length ? 1 : 0);
