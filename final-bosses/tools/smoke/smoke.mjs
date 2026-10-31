// Fight simulation: the compiled scripts run against a strict mock of @minecraft/server and every
// final boss is fought from summoning to death by two simulated players.
//     node tools/smoke/smoke.mjs        (after `python3 tools/build.py`)
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const BP = path.join(ROOT, "build", "FinalBosses_BP");
const RP = path.join(ROOT, "build", "FinalBosses_RP");
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));

const ref = JSON.parse(fs.readFileSync(path.join(ROOT, "tools", "vanilla", "reference.json"), "utf8"));
const effects = [...fs.readFileSync(path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib", "mojang-effect.d.ts"), "utf8").matchAll(/"minecraft:([a-z_]+)"/g)].map((m) => m[1]);
const particles = [...ref.particles, ...walk(path.join(RP, "particles")).map((f) => JSON.parse(fs.readFileSync(f, "utf8")).particle_effect.description.identifier)];
const entities = {
  "minecraft:item": { families: [], events: [] },
  "minecraft:xp_orb": { families: [], events: [] },
  "minecraft:player": { families: ["player"], events: [], health: 20 },
};
for (const f of walk(path.join(BP, "entities"))) {
  const e = JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:entity"];
  const c = e.components ?? {};
  entities[e.description.identifier] = { families: c["minecraft:type_family"]?.family ?? [], events: Object.keys(e.events ?? {}), health: c["minecraft:health"]?.max, properties: e.description.properties };
}
const itemDefs = walk(path.join(BP, "items")).map((f) => JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:item"]);
const items = itemDefs.map((i) => i.description.identifier);
const cooldowns = itemDefs.map((i) => i.components["minecraft:cooldown"]?.category).filter(Boolean);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "fb-smoke-"));
fs.writeFileSync(path.join(tmp, "data.json"), JSON.stringify({ effects, particles, sounds: ref.sounds, entities, items, foods: [], cooldowns }));
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
const mc = await import(url("node_modules", "@minecraft", "server", "index.mjs"));
const { __ui } = await import(url("node_modules", "@minecraft", "server-ui", "index.mjs"));
const { world, system, Player, ItemStack, __tick, __issues } = mc;
const warnings = [];
const logs = [];
console.warn = (...a) => warnings.push(a.join(" "));
console.log = (...a) => logs.push(a.join(" "));
await import(url("scripts", "main.js"));
const engine = await import(url("scripts", "engine.js"));
const blocks = await import(url("scripts", "core", "blocks.js"));
const starMod = await import(url("scripts", "bosses", "star.js"));
const minions = await import(url("scripts", "minions.js"));

const failures = [];
let passed = 0;
const expect = (c, m) => (c ? passed++ : failures.push(m));
const report = [];
async function tick(n = 1, each) {
  for (let i = 0; i < n; i++) {
    await __tick(1);
    if (each) each(i);
    await new Promise((r) => setImmediate(r));
  }
}
const commands = {};
system.beforeEvents.startup.fire({ customCommandRegistry: { registerEnum() {}, registerCommand(def, cb) { commands[def.name] = cb; } } });
expect(Object.keys(commands).length === 3, "3 custom commands registered");
world.afterEvents.worldLoad.fire({});
await tick(1);
expect(logs.some((l) => l.includes("Five Final Bosses loaded")), "load banner");

const dim = world.getDimension("minecraft:overworld");
const P1 = new Player("Alice", dim, { x: 0, y: 64, z: 0 });
const P2 = new Player("Bob", dim, { x: 6, y: 64, z: 6 });

// ---- bestiary + sigil
__ui.queue.push(0, 1);
commands["fb:bosses"]({ sourceEntity: P1 });
await tick(6);
const pg = __ui.shown.find((f) => f.title.includes("Void Emperor"));
expect(pg && pg.body.includes("ULTIMATE") && pg.body.includes("SIGNATURE") && !pg.buttons.some((b) => b.text.includes("SUMMON")), "bestiary page (read-only)");
commands["fb:sigil"]({ sourceEntity: P1 });
await tick(2);

const FIGHTS = [
  { key: "void_emperor", button: "Void Emperor", loot: "fb:crown_of_absence", ult: "Coronation of Nothing" },
  { key: "titan", button: "Titan of Creation", loot: "fb:forge_heart", ult: "Prime Mover" },
  { key: "devouring_star", button: "Devouring Star", loot: "fb:star_heart", ult: "Event Horizon" },
  { key: "world_parasite", button: "World Parasite", loot: "fb:parasite_seed", ult: "Continental Bite" },
  { key: "choir", button: "Choir of Mirrors", loot: "fb:shard_of_truth", ult: "Hall of Infinite Reflections" },
];

function aimAt(p, target) {
  const dx = target.x - p.location.x;
  const dz = target.z - p.location.z;
  p.__rotation = { x: 0, y: (Math.atan2(-dx, dz) * 180) / Math.PI };
}

for (const F of FIGHTS) {
  for (const e of dim.getEntities()) if (!(e instanceof Player)) e.remove();
  world.__drops.length = 0;
  P1.location = { x: 0, y: 64, z: 0 };
  P2.location = { x: 6, y: 64, z: 6 };
  for (const p of [P1, P2]) p.getComponent("minecraft:health").setCurrentValue(20);
  __ui.queue.push(F.button, "SUMMON", 0);
  world.afterEvents.itemUse.fire({ source: P1, itemStack: new ItemStack("fb:boss_sigil") });
  await tick(F.key === "world_parasite" ? 4 : 110);
  const boss = dim.getEntities({ type: `fb:${F.key}` })[0];
  expect(!!boss, `${F.key}: summoned`);
  if (!boss) continue;
  const b = engine.bossOf(boss);
  expect(!!b, `${F.key}: adopted by the engine`);

  if (F.key === "world_parasite") {
    expect(boss.getProperty("fb:state") === 10, "parasite: spawns dormant (disguised as a hill)");
    const hp0 = boss.getComponent("minecraft:health").currentValue;
    boss.applyDamage(10, { cause: "entityAttack", damagingEntity: P1 });
    await tick(3);
    expect(boss.getComponent("minecraft:health").currentValue === hp0 && !b.dormant, "parasite: first strike is absorbed and wakes it");
    await tick(70);
  } else {
    expect(boss.getProperty("fb:state") === 9, `${F.key}: plays its spawn animation`);
    await tick(90);
  }

  // second summon refused nearby
  __ui.queue.push(F.button, "SUMMON", 0);
  world.afterEvents.itemUse.fire({ source: P1, itemStack: new ItemStack("fb:boss_sigil") });
  await tick(8);
  expect(P1.messages.some((m) => m.includes("already walks nearby")), `${F.key}: one final boss per area`);

  const seen = new Set();
  const states = new Set();
  let maxPhase = 1;
  let exposed = false;
  let swallowed = 0;
  let escaped = 0;
  let mirrorsBroken = 0;
  let maxEdits = 0;
  let gazePunished = 0;
  let gazeSpared = 0;
  P1.__hurtLog = [];
  P2.__hurtLog = [];
  let t = 0;
  while (boss.isValid && t < 12000) {
    await tick(1, () => {
      t++;
      const bl = boss.isValid ? boss.location : { x: 0, y: 64, z: 0 };
      const ang = t * 0.018;
      const r1 = t % 800 < 400 ? 4 : 16;
      P1.location = { x: bl.x + Math.cos(ang) * r1, y: 64, z: bl.z + Math.sin(ang) * r1 };
      P1.__vel = { x: -Math.sin(ang) * 0.2, y: 0, z: Math.cos(ang) * 0.2 };
      P2.location = { x: bl.x + 9 + Math.sin(t * 0.013) * 8, y: 64, z: bl.z - 6 + Math.cos(t * 0.017) * 6 };
      P1.__air = t % 41 < 6 ? 3 : 0;
      world.__wall = t % 700 > 520 && t % 700 < 640;
      // P1 looks at the boss half of the time; P2 never does (tests the Emperor's decree)
      if (t % 200 < 100) aimAt(P1, bl);
      else P1.__rotation = { x: 0, y: (t * 7) % 360 };
      aimAt(P2, { x: bl.x + 40, y: 64, z: bl.z + 40 });
      P2.__rotation.y += 180;
      if (b.action) seen.add(b.action.name);
      if (boss.isValid) states.add(boss.getProperty("fb:state"));
      if (b.exhaustedUntil > system.currentTick) exposed = true;
      maxPhase = Math.max(maxPhase, b.phase);
      maxEdits = Math.max(maxEdits, blocks.editsActive());
      // the Star's devour: mash sneak to escape
      if (F.key === "devouring_star" && starMod.STAR_TEST.meals.size) {
        const meal = [...starMod.STAR_TEST.meals.values()][0];
        if (!meal.__counted) {
          meal.__counted = true;
          swallowed++;
        }
        if (t % 4 === 0) world.afterEvents.entityStartSneaking.fire({ entity: meal.playerId === P1.id ? P1 : P2 });
        if (meal.struggles >= 4) escaped++;
      }
      // the Choir's hall: P1 searches the mirrors and strikes them one by one
      if (F.key === "choir" && t % 15 === 0) {
        const mirrors = minions.illusionsOf(b);
        const pickM = mirrors.find((m) => m.tag !== "image") ?? mirrors[0];
        if (pickM && pickM.entity.isValid) {
          pickM.entity.applyDamage(5, { cause: "entityAttack", damagingEntity: P1 });
          mirrorsBroken++;
        }
      }
      if (t % 10 === 0 && !b.dying) {
        boss.isValid && boss.applyDamage(4, { cause: t % 30 === 0 ? "projectile" : "entityAttack", damagingEntity: P1 });
        boss.isValid && boss.applyDamage(3, { cause: "entityAttack", damagingEntity: P2 });
      }
      for (const p of [P1, P2]) {
        const h = p.getComponent("minecraft:health");
        if (h.currentValue < 6) h.setCurrentValue(20);
      }
    });
    if (F.key === "void_emperor") {
      gazePunished = P1.__hurtLog.filter((h) => h.amount === 9).length;
      gazeSpared = P2.__hurtLog.filter((h) => h.amount === 9).length;
    }
  }
  world.__wall = false;
  const moves = b.def.moves.map((m) => m.name);
  const used = moves.filter((m) => seen.has(m));
  const dealt = [...P1.__hurtLog, ...P2.__hurtLog].filter((h) => h.by === `fb:${F.key}`).reduce((a, h) => a + h.amount, 0);
  report.push(`${F.key}: ${t} ticks | moves ${used.length}/5 [${[...seen].join(", ")}] | states ${[...states].sort((a, c) => a - c).join(",")} | dealt ${Math.round(dealt)} | maxBlockEdits ${maxEdits}`);
  expect(!boss.isValid, `${F.key}: defeated (${t} ticks)`);
  expect(maxPhase === 3, `${F.key}: reached final phase`);
  expect(seen.has(F.ult), `${F.key}: ultimate "${F.ult}" performed`);
  expect(used.length >= 4, `${F.key}: varied tactics (${used.length}/5 moves)`);
  expect(exposed, `${F.key}: exposed window after an ultimate`);
  expect((states.has(0) || states.has(1)) && [2, 5, 6, 7, 8].every((s) => states.has(s)), `${F.key}: animation states driven (${[...states]})`);
  expect(world.__drops.includes(F.loot), `${F.key}: dropped ${F.loot}`);
  expect(dim.getEntities({ type: "minecraft:xp_orb" }).length >= 25, `${F.key}: experience released`);
  expect(dealt > 80, `${F.key}: hurts players (${Math.round(dealt)})`);
  expect(P1.fades > 0 && P1.shakes > 0, `${F.key}: cinematic camera`);
  if (F.key === "void_emperor") expect(gazePunished > 0, `void_emperor: decree punishes those who meet its gaze (${gazePunished}/${gazeSpared})`);
  if (F.key === "titan") expect(maxEdits >= 40, `titan: builds real blocks (${maxEdits})`);
  if (F.key === "world_parasite") expect(maxEdits >= 100, `world_parasite: infects terrain (${maxEdits} blocks)`);
  if (F.key === "devouring_star") expect(swallowed > 0, `devouring_star: devours a player and the struggle works (${swallowed} swallowed, ${escaped} struggle ticks)`);
  if (F.key === "choir") expect(mirrorsBroken > 0, "choir: mirrors can be struck");
  await tick(320);
  expect(blocks.editsActive() === 0, `${F.key}: every temporary block restored (${blocks.editsActive()} left)`);
  expect(world.__edits.size === 0, `${F.key}: terrain identical to before the fight (${world.__edits.size} changed)`);
  const left = dim.getEntities().filter((e) => e.typeId.startsWith("fb:"));
  expect(left.length === 0, `${F.key}: nothing left behind (${left.map((e) => e.typeId)})`);
}

// ---- trophies
for (const e of dim.getEntities()) if (!(e instanceof Player)) e.remove();
P1.location = { x: 0, y: 64, z: 0 };
P1.__rotation = { x: 0, y: 0 };
const before = { ...P1.location };
world.afterEvents.itemUse.fire({ source: P1, itemStack: new ItemStack("fb:crown_of_absence") });
await tick(2);
expect(Math.hypot(P1.location.x - before.x, P1.location.z - before.z) > 4 && P1.getEffect("invisibility"), "Crown of Absence: void step + invisibility");
await tick(6);
world.afterEvents.itemUse.fire({ source: P1, itemStack: new ItemStack("fb:forge_heart") });
await tick(2);
expect(world.__edits.size >= 10, `Forge Heart raises a wall (${world.__edits.size})`);
await tick(220);
expect(world.__edits.size === 0, "Forge Heart wall crumbles back to air");
world.afterEvents.itemUse.fire({ source: P1, itemStack: new ItemStack("fb:shard_of_truth") });
await tick(6);
world.afterEvents.itemUse.fire({ source: P1, itemStack: new ItemStack("fb:parasite_seed") });
await tick(6);
world.afterEvents.itemUse.fire({ source: P1, itemStack: new ItemStack("fb:star_heart") });
await tick(2);

const issues = [...new Set([...__issues, ...warnings.map((w) => `console.warn: ${w}`)])];
for (const i of issues) failures.push(`API misuse: ${i}`);
console.error(report.join("\n"));
console.error(`fight simulation: ${passed} assertions passed, ${failures.length} failed`);
for (const f of failures) console.error("  FAIL:", f);
fs.rmSync(tmp, { recursive: true, force: true });
process.exit(failures.length ? 1 : 0);
