// Runtime fight simulation: loads the compiled scripts against a strict mock of
// @minecraft/server and fights every being from summoning ritual to death.
//     node tools/smoke/smoke.mjs        (after `python3 tools/build.py`)
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const BP = path.join(ROOT, "build", "Dim11_BP");
const RP = path.join(ROOT, "build", "Dim11_RP");
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));

// ------------------------------------------------------------------ data for the strict mock
const ref = JSON.parse(fs.readFileSync(path.join(ROOT, "tools", "vanilla", "reference.json"), "utf8"));
const effects = [...fs.readFileSync(path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib", "mojang-effect.d.ts"), "utf8").matchAll(/"minecraft:([a-z_]+)"/g)].map((m) => m[1]);
const particles = [...ref.particles, ...walk(path.join(RP, "particles")).map((f) => JSON.parse(fs.readFileSync(f, "utf8")).particle_effect.description.identifier)];
const entities = {
  "minecraft:zombie": { families: ["zombie", "undead", "monster", "mob"], events: [], health: 20 },
  "minecraft:item": { families: [], events: [] },
  "minecraft:xp_orb": { families: [], events: [] },
};
for (const f of walk(path.join(BP, "entities"))) {
  const e = JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:entity"];
  const c = e.components ?? {};
  entities[e.description.identifier] = {
    families: c["minecraft:type_family"]?.family ?? [], events: Object.keys(e.events ?? {}), health: c["minecraft:health"]?.max,
    properties: e.description.properties,
  };
}
entities["minecraft:player"] = { families: ["player"], events: [], health: 20 };
const itemDefs = walk(path.join(BP, "items")).map((f) => JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:item"]);
const items = itemDefs.map((i) => i.description.identifier);
const cooldowns = itemDefs.map((i) => i.components["minecraft:cooldown"]?.category).filter(Boolean);

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dim11-smoke-"));
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

// ------------------------------------------------------------------ harness
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
system.beforeEvents.startup.fire({
  customCommandRegistry: {
    registerEnum(name) {
      expect(/^[a-z0-9_]+:[a-z_]+$/.test(name), `enum ${name} namespaced`);
    },
    registerCommand(def, cb) {
      expect(/^[a-z0-9_]+:[a-z_]+$/.test(def.name), `command ${def.name} namespaced`);
      commands[def.name] = cb;
    },
  },
});
expect(Object.keys(commands).length === 3, "3 custom commands registered");
world.afterEvents.worldLoad.fire({});
await tick(1);
expect(logs.some((l) => l.includes("11th Dimension loaded")), "load banner");

const dim = world.getDimension("minecraft:overworld");
const P1 = new Player("Alice", dim, { x: 0, y: 64, z: 0 });
const P2 = new Player("Bob", dim, { x: 6, y: 64, z: 6 });
for (const p of [P1, P2]) world.afterEvents.playerSpawn.fire({ player: p, initialSpawn: true });
const inv = (p) => p.__inv.slots.filter(Boolean).map((s) => s.typeId);

// ---- bestiary
__ui.queue.push(0, 1);
commands["dim11:bestiary"]({ sourceEntity: P1 });
await tick(6);
const page = __ui.shown.find((f) => f.title.includes("AEON-7"));
expect(page && page.body.includes("ULTIMATE") && page.body.includes("INTELLIGENCE") && !page.buttons.some((b) => b.text.includes("SUMMON")), "bestiary shows lore without summon button");

// ---- resonator
commands["dim11:resonator"]({ sourceEntity: P1 });
await tick(2);
expect(inv(P1).includes("dim11:resonator"), "resonator command gives the item");

const fights = [
  { key: "archon", button: "AEON-7", type: "dim11:archon", loot: "dim11:folded_petal", ult: "The Seven Unfold" },
  { key: "sovereign", button: "M5 Sovereign", type: "dim11:sovereign", loot: "dim11:string_of_creation", ult: "Genesis Collision" },
  { key: "observer", button: "Ophanim", type: "dim11:observer", loot: "dim11:eye_of_the_axis", ult: "The Eleventh Axis" },
];

const all = () => dim.getEntities();
function hit(boss, p, amount, cause) {
  if (!boss.isValid) return;
  boss.applyDamage(amount, { cause, damagingEntity: p });
}

for (const F of fights) {
  for (const e of all()) if (!(e instanceof Player)) e.remove();
  world.__drops.length = 0;
  P1.location = { x: 0, y: 64, z: 0 };
  P2.location = { x: 6, y: 64, z: 6 };
  P1.__rotation = { x: 0, y: 0 };
  // summon through the resonator UI: pick being -> SUMMON -> confirm
  __ui.queue.push(F.button, "SUMMON", 0);
  world.afterEvents.itemUse.fire({ source: P1, itemStack: new ItemStack("dim11:resonator") });
  await tick(30);
  expect(dim.getEntities({ type: F.type }).length === 0, `${F.key}: ritual takes time before arrival`);
  await tick(80);
  const boss = dim.getEntities({ type: F.type })[0];
  expect(!!boss, `${F.key}: being arrives after the ritual`);
  if (!boss) continue;
  const b = engine.beingOf(boss);
  expect(!!b, `${F.key}: adopted by the engine`);
  expect(P1.messages.some((m) => m.includes(b.def.name)), `${F.key}: intro dialogue`);
  expect(typeof boss.getDynamicProperty("dim11:home") === "object", `${F.key}: arena home stored`);

  // a second ritual nearby must be refused
  __ui.queue.push(F.button, "SUMMON", 0);
  world.afterEvents.itemUse.fire({ source: P1, itemStack: new ItemStack("dim11:resonator") });
  await tick(8);
  expect(P1.messages.some((m) => m.includes("already open")), `${F.key}: only one being per area`);

  const seen = new Set();
  const states = new Set();
  let adapted = null;
  let maxPhase = 1;
  let exposed = false;
  const startHp = boss.getComponent("minecraft:health").currentValue;
  P1.__hurtLog = [];
  P2.__hurtLog = [];
  let t = 0;
  // ---- the fight: players move, hide, shield, and hit with mostly melee
  while (boss.isValid && t < 9000) {
    await tick(1, () => {
      t++;
      const ang = t * 0.02;
      P1.location = { x: Math.cos(ang) * (t % 900 < 450 ? 4 : 18), y: 64, z: Math.sin(ang) * (t % 900 < 450 ? 4 : 18) };
      P1.__vel = { x: -Math.sin(ang) * 0.2, y: 0, z: Math.cos(ang) * 0.2 };
      P2.location = { x: 10 + Math.sin(t * 0.013) * 12, y: 64, z: -8 + Math.cos(t * 0.017) * 6 };
      P1.__air = t % 37 < 6 ? 3 : 0; // hop now and then (dodges ring waves)
      world.__wall = t % 600 > 450 && t % 600 < 560; // sometimes hide behind walls
      P1.isSneaking = t % 700 > 600;
      P1.__equip.Offhand = P1.isSneaking ? new ItemStack("minecraft:shield") : undefined;
      if (b.action) seen.add(b.action.name);
      states.add(boss.isValid ? boss.getProperty("dim11:state") : -1);
      if (b.adapted) adapted = b.adapted.kind;
      if (b.exhaustedUntil > system.currentTick) exposed = true;
      maxPhase = Math.max(maxPhase, b.phase);
      if (t % 10 === 0 && !b.dying) {
        hit(boss, P1, 6, t % 30 === 0 ? "projectile" : "entityAttack");
        hit(boss, P2, 4, "entityAttack");
      }
      for (const p of [P1, P2]) {
        const h = p.getComponent("minecraft:health");
        if (h.currentValue < 6) h.setCurrentValue(20); // potions!
      }
    });
  }
  world.__wall = false;
  const moves = b.def.moves.map((m) => m.name);
  const used = moves.filter((m) => seen.has(m));
  report.push(`${F.key}: ${t} ticks, moves used ${used.length}/${moves.length} [${[...seen].join(", ")}], states ${[...states].sort().join(",")}, adapted=${adapted}`);
  expect(!boss.isValid, `${F.key}: being defeated within the simulation (${t} ticks)`);
  expect(maxPhase === 3, `${F.key}: reached True Form (phase ${maxPhase})`);
  expect(seen.has(F.ult), `${F.key}: ultimate "${F.ult}" performed`);
  expect(used.length >= 4, `${F.key}: varied tactics - ${used.length}/5 moves used`);
  expect(seen.has(b.def.moves.find((m) => /Fold|Dive|Revelation/.test(m.name)).name), `${F.key}: reacts to hiding with its anti-cheese move`);
  expect(adapted === "melee", `${F.key}: adapted to the dominant damage type (${adapted})`);
  expect(exposed, `${F.key}: exposed window after ultimate`);
  expect([0, 1, 2, 3, 5].every((s) => states.has(s)), `${F.key}: animation states driven (${[...states]})`);
  expect(world.__drops.includes(F.loot), `${F.key}: dropped ${F.loot}`);
  expect(dim.getEntities({ type: "minecraft:xp_orb" }).length >= 20, `${F.key}: experience released`);
  expect(P1.fades > 0 && P1.shakes > 0, `${F.key}: cinematic camera fade/shake used`);
  expect(startHp >= 600, `${F.key}: high-tier health (${startHp})`);
  const dealt = [...P1.__hurtLog, ...P2.__hurtLog].filter((h) => h.by === F.type).reduce((a, h) => a + h.amount, 0);
  report.push(`   ${F.key} dealt ${Math.round(dealt)} damage to the two players`);
  expect(dealt > 60, `${F.key}: abilities actually hurt players (${Math.round(dealt)})`);
  await tick(200);
  const leftovers = all().filter((e) => e.typeId.startsWith("dim11:"));
  expect(leftovers.length === 0, `${F.key}: no illusions / wisps left behind (${leftovers.map((e) => e.typeId)})`);
}

// ---- relics
for (const e of all()) if (!(e instanceof Player)) e.remove();
P1.location = { x: 0, y: 64, z: 0 };
P1.__rotation = { x: 0, y: 0 };
const z = dim.spawnEntity("minecraft:zombie", { x: 0, y: 64, z: 8 });
world.afterEvents.itemUse.fire({ source: P1, itemStack: new ItemStack("dim11:string_of_creation") });
await tick(2);
expect(z.__hurtLog.length === 1, "String of Creation pierces a mob");
world.afterEvents.itemUse.fire({ source: P1, itemStack: new ItemStack("dim11:string_of_creation") });
await tick(2);
expect(z.__hurtLog.length === 1, "relic cooldown blocks immediate reuse");
const before = { ...P1.location };
await tick(5);
world.afterEvents.itemUse.fire({ source: P1, itemStack: new ItemStack("dim11:folded_petal") });
await tick(2);
expect(Math.hypot(P1.location.x - before.x, P1.location.z - before.z) > 5, "Folded Petal blinks forward");
P1.__inv.setItem(0, new ItemStack("dim11:eye_of_the_axis"));
P1.selectedSlotIndex = 0;
const anchor = { ...P1.location };
await tick(40);
P1.location = { x: 40, y: 64, z: 40 };
P1.getComponent("minecraft:health").setCurrentValue(5);
await tick(30);
world.afterEvents.itemUse.fire({ source: P1, itemStack: new ItemStack("dim11:eye_of_the_axis") });
await tick(2);
expect(Math.hypot(P1.location.x - anchor.x, P1.location.z - anchor.z) < 2 && P1.getComponent("minecraft:health").currentValue > 5, "Eye of the Axis rewinds position and health");

// ---- spawn egg path
const egg = dim.spawnEntity("dim11:observer", { x: 0, y: 70, z: 0 });
await tick(4);
expect(!!engine.beingOf(egg), "spawn-egg beings are adopted by the AI");
egg.remove();

const issues = [...__issues, ...warnings.map((w) => `console.warn: ${w}`)];
for (const i of [...new Set(issues)]) failures.push(`API misuse: ${i}`);
console.error(report.join("\n"));
console.error(`smoke test: ${passed} assertions passed, ${failures.length} failed`);
for (const f of failures) console.error("  FAIL:", f);
fs.rmSync(tmp, { recursive: true, force: true });
process.exit(failures.length ? 1 : 0);
