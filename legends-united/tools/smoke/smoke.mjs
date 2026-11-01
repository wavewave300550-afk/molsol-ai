// Simulation tests for Legends United (all three hosts in one script runtime, strict mock).
//   python3 tools/combine.py && node tools/smoke/smoke.mjs
// 1. every boss hatches from a spawn egg and is taken over by its own engine
// 2. bosses of different hosts fight each other with no player around (several match-ups)
// 3. bosses of the same host stay allies
// 4. each host still fights players
// Every id (sound, particle, effect, entity, event, property range) is validated by the mock;
// script warnings fail the run.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const BP = path.join(ROOT, "build", "Legends_United_BP");
const RP = path.join(ROOT, "build", "Legends_United_RP");
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));

const ref = JSON.parse(fs.readFileSync(path.join(ROOT, "tools", "vanilla", "reference.json"), "utf8"));
const effects = JSON.parse(fs.readFileSync(path.join(ROOT, "tools", "vanilla", "effects.json"), "utf8"));
const particles = [...ref.particles, ...walk(path.join(RP, "particles")).map((f) => JSON.parse(fs.readFileSync(f, "utf8")).particle_effect.description.identifier)];
const entities = {
  "minecraft:item": { families: [], events: [] },
  "minecraft:xp_orb": { families: [], events: [] },
  "minecraft:player": { families: ["player"], events: [], health: 20 },
};
for (const f of walk(path.join(BP, "entities"))) {
  const e = JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:entity"];
  const c = e.components ?? {};
  entities[e.description.identifier] = { families: c["minecraft:type_family"]?.family ?? [], events: Object.keys(e.events ?? {}), health: c["minecraft:health"]?.max, properties: e.description.properties, spawnable: !!e.description.is_spawnable };
}
const items = walk(path.join(BP, "items")).map((f) => JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:item"].description.identifier);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "united-smoke-"));
fs.writeFileSync(path.join(tmp, "data.json"), JSON.stringify({ effects, particles, sounds: ref.sounds, entities, items, foods: [], cooldowns: [] }));
process.env.TRIBES_MOCK_DATA = path.join(tmp, "data.json");
fs.cpSync(path.join(BP, "scripts"), path.join(tmp, "scripts"), { recursive: true });
fs.writeFileSync(path.join(tmp, "package.json"), JSON.stringify({ type: "module" }));
for (const [pkg, file] of [["server", "mock-server.mjs"], ["server-ui", "mock-server-ui.mjs"]]) {
  const dir = path.join(tmp, "node_modules", "@minecraft", pkg);
  fs.mkdirSync(dir, { recursive: true });
  fs.copyFileSync(path.join(HERE, file), path.join(dir, "index.mjs"));
  fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({ name: `@minecraft/${pkg}`, type: "module", exports: "./index.mjs" }));
}
const url = (...p) => pathToFileURL(path.join(tmp, ...p)).href;
let seed = Number(process.env.SEED ?? 20261101) >>> 0;
Math.random = () => {
  seed = (seed + 0x6d2b79f5) >>> 0;
  let t = seed;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};
const mc = await import(url("node_modules", "@minecraft", "server", "index.mjs"));
const { world, system, Player, __tick, __issues } = mc;
const warnings = [];
console.warn = (...a) => warnings.push(a.join(" "));
const logs = [];
console.log = (...a) => logs.push(a.join(" "));
await import(url("scripts", "main.js"));
const d11 = await import(url("scripts", "dim11", "engine.js"));
const fbe = await import(url("scripts", "fb", "engine.js"));
const lreg = await import(url("scripts", "legends", "bosses", "registry.js"));
const united = await import(url("scripts", "united.js"));

const failures = [];
let passed = 0;
const expect = (c, m) => (c ? passed++ : failures.push(m));
async function tick(n = 1, each) {
  for (let i = 0; i < n; i++) {
    await __tick(1);
    if (each) each(i);
    await new Promise((r) => setImmediate(r));
  }
}
const commands = {};
system.beforeEvents.startup.fire({ customCommandRegistry: { registerEnum() {}, registerCommand(def, cb) { commands[def.name] = cb; } } });
const hosts = { dim11: 0, fb: 0, legends: 0, united: 0 };
for (const n of Object.keys(commands)) hosts[n.split(":")[0]] = (hosts[n.split(":")[0]] ?? 0) + 1;
expect(hosts.dim11 >= 3 && hosts.fb >= 3 && hosts.legends >= 6 && hosts.united === 1, `commands of all hosts registered ${JSON.stringify(hosts)}`);
world.afterEvents.worldLoad.fire({});
await tick(3);
const dim = world.getDimension("minecraft:overworld");
const FAR = { x: 400, y: 64, z: 400 };
const P1 = new Player("Alice", dim, { ...FAR });
world.afterEvents.playerSpawn.fire({ player: P1, initialSpawn: true });
await tick(20);

const TEAM = (id) => id.split(":")[0];
const ctl = (e) => {
  const t = TEAM(e.typeId);
  return t === "dim11" ? d11.beingOf(e) : t === "fb" ? fbe.bossOf(e) : lreg.bossOf(e.id);
};
function clearWorld() {
  lreg.clearAll();
  for (const e of dim.getEntities()) if (!(e instanceof Player)) e.remove();
}
const hatch = (id, at) => {
  const e = dim.spawnEntity(id, at);
  world.afterEvents.entitySpawn.fire({ entity: e, cause: "Spawned" });
  return e;
};
const report = [];

// ------------------------------------------------------------------ 1. spawn eggs
for (const id of united.EGGS) {
  expect(entities[id]?.spawnable, `${id} has a spawn egg`);
  clearWorld();
  await tick(2);
  const e = hatch(id, { x: 0, y: 64, z: 0 });
  await tick(6);
  expect(e.isValid && !!ctl(e), `${id}: hatched from its egg and taken over by its engine`);
}
const lang = fs.readFileSync(path.join(RP, "texts", "en_US.lang"), "utf8");
for (const id of united.EGGS) expect(lang.includes(`item.spawn_egg.entity.${id}.name=`), `${id}: spawn egg has a name`);

// ------------------------------------------------------------------ 2. clashes between hosts
const hpOf = (e) => (e.isValid ? e.getComponent("minecraft:health").currentValue : 0);
async function clash(ids, ticks) {
  clearWorld();
  P1.location = { ...FAR };
  await tick(2);
  const es = ids.map((id, i) => hatch(id, { x: Math.cos((i / ids.length) * 6.283) * 9, y: 64, z: Math.sin((i / ids.length) * 6.283) * 9 }));
  const hp0 = es.map((e) => e.getComponent("minecraft:health").__max);
  const hitBy = es.map(() => new Set());
  const targeted = es.map(() => new Set());
  const hurt0 = es.map((e) => e.__hurtLog.length);
  let firstDeath = -1;
  await tick(ticks, (k) => {
    es.forEach((e, i) => {
      const c = e.isValid ? ctl(e) : undefined;
      const tg = c?.target;
      if (tg && !(tg instanceof Player)) targeted[i].add(tg.typeId);
      if (!e.isValid && firstDeath < 0) firstDeath = k;
    });
    // fighters wander: keep them inside one arena so long fights stay in range
    es.forEach((e) => {
      if (e.isValid && Math.hypot(e.location.x, e.location.z) > 30) e.location = { x: e.location.x * 0.5, y: 64, z: e.location.z * 0.5 };
    });
  });
  es.forEach((e, i) => {
    for (const h of e.__hurtLog.slice(hurt0[i])) if (h.by) hitBy[i].add(h.by);
  });
  const line = es.map((e, i) => `${ids[i].split(":")[1]} ${Math.round(hpOf(e))}/${hp0[i]} hit by[${[...hitBy[i]].map((s) => s.split(":")[1]).join(",")}] aims[${[...targeted[i]].map((s) => s.split(":")[1]).join(",")}]`).join(" | ");
  report.push(`clash ${ids.map((s) => s.split(":")[1]).join(" vs ")} (${ticks}t, first death ${firstDeath}): ${line}`);
  return { es, hitBy, targeted, firstDeath };
}
const CLASHES = [
  ["legends:taotie", "fb:titan"],
  ["dim11:archon", "legends:hanuman"],
  ["fb:void_emperor", "dim11:sovereign"],
  ["legends:logos", "fb:devouring_star", "dim11:observer"],
  ["legends:alicorn", "fb:choir"],
  ["legends:tenko", "dim11:archon"],
  ["legends:nidhogg", "fb:void_emperor"],
];
for (const ids of CLASHES) {
  const r = await clash(ids, 6000);
  ids.forEach((id, i) => {
    const rivals = ids.filter((o) => TEAM(o) !== TEAM(id));
    expect([...r.targeted[i]].some((t) => rivals.includes(t)), `${id} targeted a rival boss`);
    expect([...r.hitBy[i]].some((t) => TEAM(t) !== TEAM(id)), `${id} was struck by a rival boss`);
  });
  expect(r.firstDeath >= 0, `clash ${ids.join(" vs ")}: a boss fell`);
}

// ------------------------------------------------------------------ 3. allies stay allies
for (const pair of [["legends:taotie", "legends:tenko"], ["fb:titan", "fb:void_emperor"], ["dim11:archon", "dim11:sovereign"]]) {
  const r = await clash(pair, 400);
  expect(r.hitBy.every((s) => s.size === 0) && r.targeted.every((s) => s.size === 0), `${pair.join(" + ")} stay allies`);
}

// ------------------------------------------------------------------ 4. players are still fought
for (const id of ["dim11:archon", "fb:titan", "legends:taotie"]) {
  clearWorld();
  await tick(2);
  P1.location = { x: 6, y: 64, z: 0 };
  P1.getComponent("minecraft:health").setCurrentValue(20);
  const e = hatch(id, { x: 0, y: 64, z: 0 });
  const h0 = P1.__hurtLog.length;
  let aimed = false;
  await tick(900, () => {
    if (ctl(e)?.target === P1) aimed = true;
    if (P1.getComponent("minecraft:health").currentValue < 8) P1.getComponent("minecraft:health").setCurrentValue(20);
  });
  expect(aimed, `${id}: still targets players`);
  expect(P1.__hurtLog.slice(h0).some((h) => h.by === id), `${id}: still hurts players`);
}
P1.location = { ...FAR };
clearWorld();
await tick(40);

// ------------------------------------------------------------------ results
const issues = __issues;
expect(issues.length === 0, `mock issues: ${issues.slice(0, 8).join(" | ")}`);
const bad = warnings.filter((w) => !/custom commands unavailable/.test(w));
expect(bad.length === 0, `script warnings: ${bad.slice(0, 8).join(" | ")}`);
console.info(report.join("\n"));
console.info(`\n${passed} checks passed, ${failures.length} failed`);
for (const f of failures) console.info(`FAIL ${f}`);
process.exit(failures.length ? 1 : 0);
