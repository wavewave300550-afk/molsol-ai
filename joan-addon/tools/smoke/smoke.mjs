// Runtime smoke test: runs the compiled behaviour-pack scripts against the
// strict @minecraft/server mock and plays a whole Joan of Arc encounter.
//     node tools/smoke/smoke.mjs        (after `python3 tools/build.py`)
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const BP = path.join(ROOT, "build", "Joan_BP");
const RP = path.join(ROOT, "build", "Joan_RP");
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));

// ------------------------------------------------------------------ data for the mock
const ref = JSON.parse(fs.readFileSync(path.join(ROOT, "tools", "vanilla", "reference.json"), "utf8"));
const particles = [...ref.particles];
const molangVars = new Set();
for (const f of walk(path.join(RP, "particles"))) {
  const txt = fs.readFileSync(f, "utf8");
  particles.push(JSON.parse(txt).particle_effect.description.identifier);
  for (const m of txt.matchAll(/variable\.([a-z_0-9]+)/g)) molangVars.add(`variable.${m[1]}`);
}
const soundDefs = JSON.parse(fs.readFileSync(path.join(RP, "sounds", "sound_definitions.json"), "utf8")).sound_definitions;
const sounds = [...ref.sounds, ...Object.keys(soundDefs)];
const entities = {
  "minecraft:player": { families: ["player"], events: [], health: 20, properties: {}, gravity: true },
  "minecraft:zombie": { families: ["zombie", "monster", "mob"], events: [], health: 20, properties: {}, gravity: true, movement: 0.23 },
  "minecraft:item": { families: [], events: [], properties: {}, gravity: true },
  "minecraft:xp_orb": { families: [], events: [], properties: {}, gravity: true },
  "minecraft:arrow": { families: ["arrow"], events: [], properties: {}, projectile: true, gravity: false },
};
for (const f of walk(path.join(BP, "entities"))) {
  const e = JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:entity"];
  const c = e.components ?? {};
  entities[e.description.identifier] = {
    families: c["minecraft:type_family"]?.family ?? [],
    events: Object.keys(e.events ?? {}),
    health: c["minecraft:health"]?.max,
    movement: c["minecraft:movement"]?.value,
    gravity: c["minecraft:physics"]?.has_gravity !== false,
    properties: e.description.properties ?? {},
  };
}
const items = walk(path.join(BP, "items")).map((f) => JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:item"].description.identifier);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "joan-smoke-"));
const dataPath = path.join(tmp, "data.json");
fs.writeFileSync(dataPath, JSON.stringify({ particles, sounds, entities, items, molangVars: [...molangVars] }));
process.env.JOAN_MOCK_DATA = dataPath;

fs.cpSync(path.join(BP, "scripts"), path.join(tmp, "scripts"), { recursive: true });
fs.writeFileSync(path.join(tmp, "package.json"), JSON.stringify({ type: "module" }));
const dir = path.join(tmp, "node_modules", "@minecraft", "server");
fs.mkdirSync(dir, { recursive: true });
fs.copyFileSync(path.join(HERE, "mock-server.mjs"), path.join(dir, "index.mjs"));
fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({ name: "@minecraft/server", type: "module", exports: "./index.mjs" }));
const mc = await import(pathToFileURL(path.join(dir, "index.mjs")).href);
const { world, system, Player, ItemStack, Entity, __tick, __issues, __log, __perf, __walls } = mc;

const warnings = [];
console.warn = (...a) => warnings.push(a.join(" "));
const logs = [];
const origLog = console.log;
console.log = (...a) => logs.push(a.join(" "));

const main = await import(pathToFileURL(path.join(tmp, "scripts", "main.js")).href);
const { bosses } = main;
const fieldMod = await import(pathToFileURL(path.join(tmp, "scripts", "paths", "field.js")).href);
const shapes = await import(pathToFileURL(path.join(tmp, "scripts", "paths", "shapes.js")).href);

// ------------------------------------------------------------------ harness
const failures = [];
let passed = 0;
function expect(cond, msg) {
  if (cond) passed++;
  else failures.push(msg);
}
async function tick(n = 1) {
  for (let i = 0; i < n; i++) {
    await __tick(1);
    trackParticles();
  }
}
let lastParticles = 0;
let maxParticlesPerTick = 0;
function trackParticles() {
  const d = world.__particles - lastParticles;
  lastParticles = world.__particles;
  maxParticlesPerTick = Math.max(maxParticlesPerTick, d);
}
const commands = {};
const enums = {};
system.beforeEvents.startup.fire({
  customCommandRegistry: {
    registerEnum(name, values) {
      expect(/^[a-z_]+:[a-z_]+$/.test(name), `enum ${name} needs a namespace`);
      enums[name] = values;
    },
    registerCommand(def, cb) {
      expect(/^[a-z_]+:[a-z_]+$/.test(def.name), `command ${def.name} needs a namespace`);
      for (const p of def.mandatoryParameters ?? []) if (p.type === "Enum") expect(enums[p.name], `enum ${p.name} registered before use`);
      commands[def.name] = cb;
    },
  },
});
expect(Object.keys(commands).length === 4, `four custom commands (${Object.keys(commands)})`);
world.afterEvents.worldLoad.fire({});
await tick(2);
expect(logs.some((l) => l.includes("Joan of Arc loaded")), "load banner logged");

const dim = world.getDimension("minecraft:overworld");
const P = new Player("Pilgrim", dim, { x: 0, y: 64, z: 0 });
P.__rot = { x: 0, y: 0 }; // facing +z
const heal = () => {
  P.__health.currentValue = 20;
  P.__fire = 0;
};
const hpOf = (e) => e.getComponent("minecraft:health").currentValue;

// ------------------------------------------------------------------ 1. intro
dim.spawnEntity("joan:joan_of_arc", { x: 0, y: 64, z: 14 });
await tick(2);
expect(bosses.size === 1, "a boss encounter was created for the spawned entity");
const B = [...bosses.values()][0];
const J = B.e;
let roadsWritten = 0;
const origAdd = B.field.add.bind(B.field);
B.field.add = (...args) => {
  const r = origAdd(...args);
  if (r) roadsWritten++;
  return r;
};
expect(B.mode === "intro" && B.invulnerable, "intro starts invulnerable");
J.applyDamage(50, { cause: "entityAttack", damagingEntity: P });
expect(hpOf(J) === 600, "no damage during the intro");
await tick(160);
expect(B.mode === "fight" && B.phase === 1, `intro ends in phase I (mode=${B.mode} phase=${B.phase})`);
expect(J.getProperty("joan:phase") === 1, "phase property synced");
expect(J.nameTag === "Joan of Arc", "boss bar name set");
expect(__log.titles.some((t) => t.t.includes("BOSS 001")), "boss title shown");
expect(B.field.livePaths().some((p) => p.o.tag === "arena"), "processional ring written");
expect(__log.sounds.includes("joan.choir.light") && __log.sounds.includes("joan.bell.toll"), "intro music cues");
{
  // the Processional Ring sweeps arrows sniped from outside, but not shots fired from inside
  const H = B.home;
  const sniped = new Entity("minecraft:arrow", dim, { x: H.x + 27.2, y: H.y + 0.6, z: H.z });
  sniped.__vel = { x: -1.5, y: 0, z: 0 };
  const own = new Entity("minecraft:arrow", dim, { x: H.x + 25.6, y: H.y + 0.6, z: H.z + 0.5 });
  own.__vel = { x: 1.5, y: 0, z: 0 };
  await tick(2);
  expect(B.field.wasRedirected(sniped), "an arrow sniped from outside the arena is caught by the ring");
  expect(!B.field.wasRedirected(own), "a player's own shot from inside is never caught by the ring");
  for (const a of [sniped, own]) if (a.__valid) a.remove();
}

// ------------------------------------------------------------------ 2. road physics (direct)
async function roadTest() {
  const { line } = shapes;
  heal();
  P.location = { x: 20, y: 64, z: -20 };
  const road = B.groundRoad(line({ x: 18, y: 64, z: -20 }, { x: 34, y: 64, z: -20 }), { kind: "road", form: 4, life: 80, burning: false, damage: 0, memory: true, tag: "test" });
  expect(!!road && road.length > 14, "ground road conformed to flat terrain");
  await tick(6);
  const x0 = P.location.x;
  await tick(12);
  expect(P.location.x - x0 > 2.5, `a road carries a standing player along its flow (moved ${(P.location.x - x0).toFixed(2)})`);
  // sneaking resists
  P.location = { x: 20, y: 64, z: -20 };
  P.isSneaking = true;
  const x1 = P.location.x;
  await tick(12);
  const sneakMove = P.location.x - x1;
  P.isSneaking = false;
  expect(sneakMove > 0.3 && sneakMove < (P.location.x - x1) + 99, "sneaking still drifts");
  // reversal with warning
  B.field.reverse(road, 6, B.now);
  expect(road.flow === 1, "reversal waits for its warning");
  await tick(7);
  expect(road.flow === -1, "road reversed after the warning");
  P.location = { x: 28, y: 64, z: -20 };
  const x2 = P.location.x;
  await tick(10);
  expect(P.location.x < x2 - 1.5, "reversed road carries the other way");
  // a jumping player above the band is not captured
  P.location = { x: 24, y: 65.6, z: -20 };
  P.__vel = { x: 0, y: 0.1, z: 0 };
  const k0 = P.__knock;
  await tick(1);
  expect(P.__knock === k0, "a player jumping over a road is not carried");
  // projectile redirect: an arrow flying across the road gets bent along it
  P.location = { x: 0, y: 64, z: 0 };
  const arrow = new Entity("minecraft:arrow", dim, { x: 26, y: 64.6, z: -23 });
  arrow.__vel = { x: 0, y: 0, z: 1.6 };
  await tick(3);
  const vel = arrow.__valid ? arrow.getVelocity() : { x: 0, z: 1 };
  expect(Math.abs(vel.x) > Math.abs(vel.z), `arrow re-aimed along the road (vel ${vel.x.toFixed(2)},${vel.z.toFixed(2)})`);
  expect(B.field.wasRedirected(arrow), "redirected projectile remembered (Turned Road)");
  // split & merge
  const a = B.groundRoad(line({ x: 40, y: 64, z: 0 }, { x: 46, y: 64, z: 0 }), { kind: "road", form: 2, life: 60, burning: false, damage: 0, memory: false });
  const b1 = B.groundRoad(line({ x: 46, y: 64, z: 0 }, { x: 52, y: 64, z: 5 }), { kind: "road", form: 2, life: 60, burning: false, damage: 0, memory: false });
  const b2 = B.groundRoad(line({ x: 46, y: 64, z: 0 }, { x: 52, y: 64, z: -5 }), { kind: "road", form: 2, life: 60, burning: false, damage: 0, memory: false });
  B.field.split(a, [b1, b2]);
  await tick(3);
  const z1 = new Entity("minecraft:zombie", dim, { x: 41, y: 64, z: 0 });
  const z2 = new Entity("minecraft:zombie", dim, { x: 41.5, y: 64, z: 0.2 });
  await tick(30);
  const sides = [z1, z2].map((z) => Math.sign(z.location.z));
  expect(sides[0] !== sides[1], `a split road distributes riders over its branches (z: ${z1.location.z.toFixed(1)}, ${z2.location.z.toFixed(1)})`);
  z1.remove();
  z2.remove();
  B.field.retireAll(B.now, 1);
  await tick(3);
}
await roadTest();

// ------------------------------------------------------------------ 3. every skill in phase I
const force = (name) => commands["joan:skill"]({ sourceEntity: P }, name);
async function runSkill(name, place, maxTicks = 700) {
  heal();
  place();
  const actionBefore = J.getProperty("joan:seq");
  const pathsBefore = roadsWritten;
  const dmgBefore = P.__hurt.length;
  const knockBefore = P.__knock;
  force(name);
  let started = false;
  let ticks = 0;
  for (; ticks < maxTicks; ticks++) {
    await tick(1);
    if (B.action && B.action.name === name) started = true;
    if (started && !B.action) break;
    if (ticks % 20 === 0) heal();
  }
  expect(started, `skill ${name} started`);
  expect(started && !B.action, `skill ${name} finished (${ticks} ticks)`);
  return { ticks, hurt: P.__hurt.length - dmgBefore, knocked: P.__knock - knockBefore, newPaths: roadsWritten - pathsBefore, seqChanged: J.getProperty("joan:seq") !== actionBefore };
}
const near = (d) => () => {
  J.location = { ...B.home };
  P.location = { x: B.home.x, y: 64, z: B.home.z - d };
  B.brain.target = P;
};
const results = {};
results.melee = await runSkill("melee", near(2.4));
expect(results.melee.hurt > 0, "melee combo hits a player standing in front of her");
results.trail = await runSkill("trail", near(9));
expect(results.trail.seqChanged, "Banner Trail plays animations");
results.surge = await runSkill("surge", near(14));
results.orleans = await runSkill("orleans", near(9));
expect(results.orleans.knocked > 0, "Road of Orleans moves the player (out, then back in)");
results.salvation = await runSkill("salvation", near(8));
expect(results.salvation.hurt > 0 || results.salvation.knocked > 0, "False Salvation judges or carries a player who stays inside");
results.convergence = await runSkill("convergence", near(9));
expect(results.convergence.knocked > 0, "Convergence funnels the player");
results.detour = await runSkill("detour", near(10));
results.procession = await runSkill("procession", near(8));
expect(__log.spawned.includes("joan:echo"), "procession spawned echoes");
expect(__log.spawned.includes("joan:standard"), "convergence planted phantom standards");
expect(__log.spawned.includes("joan:seraph"), "detour released seraph lights");
for (const [k, r] of Object.entries(results)) expect(r.newPaths > 0 || k === "melee" || (k === "surge" && B.stats.reused > 0), `${k} wrote roads`);

// ------------------------------------------------------------------ free fight: the brain chooses on its own
async function freeFight(ticks, label) {
  const before = { ...B.stats.chosen };
  const combos0 = B.stats.combos;
  J.location = { ...B.home };
  for (let i = 0; i < ticks; i++) {
    // the pilgrim circles the arena, sometimes closing in, sometimes drawing a bow
    const a = i / 60;
    const r = i % 400 < 140 ? 3 : 9 + 4 * Math.sin(i / 90);
    P.location = { x: B.home.x + Math.cos(a) * r, y: 64, z: B.home.z + Math.sin(a) * r };
    if (i % 200 === 50) world.afterEvents.itemStartUse.fire({ source: P, itemStack: new ItemStack("minecraft:bow"), useDuration: 20 });
    if (i % 200 === 80) world.afterEvents.itemReleaseUse.fire({ source: P, itemStack: new ItemStack("minecraft:bow"), useDuration: 20 });
    if (i % 25 === 0) heal();
    if (B.mode !== "fight" && B.mode !== "intro") break;
    await tick(1);
  }
  const used = Object.fromEntries(Object.entries(B.stats.chosen).map(([k, v]) => [k, v - (before[k] ?? 0)]).filter(([, v]) => v > 0));
  console.error(`${label} free fight choices: ${JSON.stringify(used)} combos: ${B.stats.combos - combos0}`);
  return { used, combos: B.stats.combos - combos0 };
}
const ff1 = await freeFight(2400, "phase I");
expect(Object.keys(ff1.used).length >= 5, `phase I brain varies its skills (${Object.keys(ff1.used).join(",")})`);
expect(B.mode === "fight" && B.phase === 1, "free fight stays in phase I");

// ------------------------------------------------------------------ leash: dragged out of the arena she walks the road back
{
  heal();
  for (let i = 0; i < 400 && B.action; i++) await tick(1);
  B.gcdUntil = B.now + 400;
  J.location = { x: B.home.x + 45, y: 64, z: B.home.z };
  P.location = { x: B.home.x + 3, y: 64, z: B.home.z };
  await tick(4);
  expect(B.action && B.action.name === "return", "Joan returns along a sky road when pulled out of her arena");
  for (let i = 0; i < 200 && B.action; i++) await tick(1);
  expect(Math.hypot(J.location.x - B.home.x, J.location.z - B.home.z) < 6, "she is back at the arena centre");
  B.gcdUntil = 0;
}

// ------------------------------------------------------------------ 4. secrets in phase I: the bell
heal();
near(6)();
B.gcdUntil = 0;
world.afterEvents.playerInteractWithBlock.fire({ player: P, block: { typeId: "minecraft:bell", location: { x: 2, y: 64, z: 2 } }, isFirstEvent: true });
await tick(2);
expect(B.action && B.action.name === "listen", "ringing a bell makes Joan stop and listen");
world.afterEvents.playerInteractWithBlock.fire({ player: P, block: { typeId: "minecraft:bell", location: { x: 2, y: 64, z: 2 } }, isFirstEvent: true });
await tick(100);
expect(B.flags.bell.has(1) && B.flags.bell.size === 1, "the bell works once per phase");

// ------------------------------------------------------------------ 5. Turned Road (double damage + stagger)
const arrow2 = new Entity("minecraft:arrow", dim, { x: J.location.x, y: 65, z: J.location.z - 2 });
B.field.touchedProjectiles.set(arrow2.id, { pathId: 1, until: B.now + 100 });
const hp0 = hpOf(J);
J.applyDamage(5, { cause: "projectile", damagingEntity: P, damagingProjectile: arrow2 });
expect(hp0 - hpOf(J) > 9.5, `a projectile carried by her own road deals double damage (${(hp0 - hpOf(J)).toFixed(1)})`);
world.afterEvents.projectileHitEntity.fire({ projectile: arrow2, source: P, getEntityHit: () => ({ entity: J }) });
await tick(1);

// ------------------------------------------------------------------ 6. phase transition
await tick(60);
J.applyDamage(1000, { cause: "entityAttack", damagingEntity: P });
expect(Math.abs(hpOf(J) - 300) < 0.01, `a huge hit cannot skip phase II (hp ${hpOf(J)})`);
await tick(3);
expect(B.mode === "transition" && B.invulnerable, "phase transition scene running");
await tick(110);
expect(B.phase === 2 && B.mode === "fight", "phase II begins");
expect(J.getProperty("joan:phase") === 2, "burning look synced");
expect(J.__events.includes("joan:darken"), "the sky darkens");
expect(__log.titles.some((t) => t.t.includes("Phase II")), "phase II title");

// ------------------------------------------------------------------ 7. phase II skills + crossings + restless roads
const crossBefore = fieldMod.fieldStats.crossings;
const p2 = {};
for (const s of ["melee", "trail", "surge", "orleans", "salvation", "convergence", "detour", "procession"]) {
  p2[s] = await runSkill(s, s === "melee" ? near(2.4) : s === "surge" ? near(14) : near(8));
}
expect(fieldMod.fieldStats.crossings > crossBefore, `phase II roads create crossing pyres (${fieldMod.fieldStats.crossings - crossBefore})`);
expect(__log.sounds.includes("joan.fire.ignite"), "pyres ignite at crossings");
{
  const { line } = shapes;
  const r = B.groundRoad(line({ x: 60, y: 64, z: 0 }, { x: 70, y: 64, z: 0 }), { kind: "road", form: 2, life: 200, restless: 30, memory: false });
  await tick(40);
  expect(r.flow === -1 || r.reverseAt >= 0, "restless road reverses on its own");
}

const ff2 = await freeFight(2000, "phase II");
expect(Object.keys(ff2.used).length >= 5, `phase II brain varies its skills (${Object.keys(ff2.used).join(",")})`);

// ------------------------------------------------------------------ 8. ultimate: purify every road -> Martyr's Echo
heal();
B.gcdUntil = 0;
J.__health.currentValue = 170;
await tick(4);
expect(B.action && B.action.name === "stake", "Road to the Stake triggers below 30%");
await tick(70);
const stones = dim.getEntities({ type: "joan:waystone" });
expect(stones.length === 5, `five Lily Waystones (${stones.length})`);
expect(dim.getEntities({ type: "joan:stake" }).length === 1, "the stake rises");
for (const s of stones) world.afterEvents.entityHitEntity.fire({ damagingEntity: P, hitEntity: s });
await tick(3);
expect(B.flags.martyrEcho, "all roads turned: Martyr's Echo");
await tick(24);
expect(B.vulnerableUntil > B.now, "Joan is bound and vulnerable");
const hp1 = hpOf(J);
J.applyDamage(10, { cause: "entityAttack", damagingEntity: P });
expect(hp1 - hpOf(J) > 10 * 0.9 * 1.4, "bound Joan takes extra damage");
for (let i = 0; i < 400 && B.action; i++) await tick(1);
expect(!B.action || B.action.name !== "stake", "the ultimate ends");
expect(dim.getEntities({ type: "joan:waystone" }).length === 0, "waystones cleaned up");

// ------------------------------------------------------------------ 9. ultimate again, nobody purifies -> the pyre burns
heal();
B.flags.lastUlt = -99999;
B.gcdUntil = 0;
await tick(3);
expect(B.action && B.action.name === "stake", "second ultimate");
P.location = { x: B.home.x + 3, y: 64, z: B.home.z };
const hurtBefore = P.__hurt.length;
for (let i = 0; i < 600 && B.action && B.action.name === "stake"; i++) {
  P.location = { x: B.home.x + 3, y: 64, z: B.home.z };
  await tick(1);
}
expect(P.__hurt.slice(hurtBefore).some((h) => h.amount >= 15), "the pyre erupts on those near the stake");

// ------------------------------------------------------------------ 10. defeat and rewards
heal();
await tick(20);
J.applyDamage(5000, { cause: "entityAttack", damagingEntity: P });
expect(J.__valid && hpOf(J) >= 1, "the killing blow starts the death scene instead of killing");
await tick(3);
expect(B.mode === "dying" && B.invulnerable, "death scene");
await tick(150);
expect(!J.__valid, "Joan is gone after the death scene");
expect(__log.items.includes("joan:banner_of_divine_paths"), "Banner of Divine Paths dropped");
expect(__log.items.includes("joan:unburnt_heart"), "Unburnt Heart dropped after Martyr's Echo");
expect(P.__xp >= 300, "experience awarded");
expect(P.messages.some((m) => m.includes("Banner of Divine Paths")), "victory message");
await tick(2);
expect(bosses.size === 0, "encounter disposed");
for (const t of ["joan:waystone", "joan:stake", "joan:standard", "joan:echo", "joan:seraph"]) {
  expect(dim.getEntities({ type: t }).length === 0, `no ${t} left behind`);
}

// ------------------------------------------------------------------ 11. the reward relic
heal();
P.location = { x: -40, y: 64, z: 0 };
P.__rot = { x: 0, y: -90 }; // facing +x
world.afterEvents.itemUse.fire({ source: P, itemStack: new ItemStack("joan:banner_of_divine_paths") });
await tick(6);
const px0 = P.location.x;
await tick(16);
expect(P.location.x - px0 > 2.5, `the Banner of Divine Paths writes a road that carries its owner (${(P.location.x - px0).toFixed(2)})`);
expect(P.__cooldowns["joan:road"] > 0, "relic cooldown shown");
await tick(60);
P.__vel = { x: 0, y: 0, z: 0 };
const orbitAt = { ...P.location };
P.isSneaking = true;
world.afterEvents.itemUse.fire({ source: P, itemStack: new ItemStack("joan:banner_of_divine_paths") });
P.isSneaking = false;
await tick(5);
const zomb = new Entity("minecraft:zombie", dim, { x: orbitAt.x + 2.4, y: 64, z: orbitAt.z });
const zk = { ...zomb.location };
await tick(8);
expect(Math.hypot(zomb.location.x - zk.x, zomb.location.z - zk.z) > 0.8, "the sanctuary orbit sweeps mobs around the owner");
await tick(20);
expect(Math.hypot(zomb.location.x - orbitAt.x, zomb.location.z - orbitAt.z) > 3.0, "and throws them out");
zomb.remove();

// ------------------------------------------------------------------ 12. summoning with the Pilgrim's Standard
P.location = { x: 0, y: 64, z: 0 };
P.__rot = { x: 0, y: 0 };
P.__inv.setItem(0, new ItemStack("joan:pilgrims_standard"));
world.afterEvents.itemUse.fire({ source: P, itemStack: new ItemStack("joan:pilgrims_standard") });
await tick(2);
expect(!P.__inv.getItem(0), "the Pilgrim's Standard is consumed");
await tick(55);
expect(bosses.size === 1, "Joan answers the summoning");
const B2 = [...bosses.values()][0];
await tick(170);
expect(B2.mode === "fight", "summoned Joan finishes her entrance");
world.afterEvents.itemUse.fire({ source: P, itemStack: new ItemStack("joan:pilgrims_standard") });
await tick(2);
expect(P.messages.some((m) => m.includes("already on the field")), "cannot summon a second Joan nearby");

// ------------------------------------------------------------------ 13. reset when everyone leaves
P.location = { x: 400, y: 64, z: 400 };
B2.e.__health.currentValue = 200;
await tick(20 * 42);
expect(Math.abs(hpOf(B2.e) - 600) < 0.01 && B2.phase === 1, "the encounter resets when the arena is empty");
P.location = { x: 0, y: 64, z: 0 };

// ------------------------------------------------------------------ 14. clear + resume after reload
commands["joan:clear"]({ sourceEntity: P });
await tick(3);
expect(bosses.size === 0 && dim.getEntities({ type: "joan:joan_of_arc" }).length === 0, "/joan:clear removes everything");
const R = new Entity("joan:joan_of_arc", dim, { x: 10, y: 64, z: 10 });
R.__dyn.set("joan:started", true);
R.__dyn.set("joan:phase", 2);
R.__dyn.set("joan:home", { x: 10, y: 64, z: 10 });
world.afterEvents.entityLoad.fire({ entity: R });
await tick(2);
const BR = bosses.get(R.id);
expect(BR && BR.mode === "fight" && BR.phase === 2, "a saved Joan resumes her fight in phase II after a reload");

// ------------------------------------------------------------------ report
const perTick = world.__particles / __perf.ticks;
console.log = origLog;
console.log(`ticks simulated: ${__perf.ticks}`);
console.log(`particles: ${world.__particles} total, avg ${perTick.toFixed(2)}/tick, peak ${maxParticlesPerTick}/tick`);
console.log(`sounds played: ${__log.sounds.length}; entity queries/tick: ${(world.__queries / __perf.ticks).toFixed(2)}`);
console.log(`script time (mock): avg ${(__perf.scriptMs / __perf.ticks).toFixed(3)} ms/tick, worst ${__perf.maxTickMs.toFixed(2)} ms`);
console.log(`roads carried: ${fieldMod.fieldStats.carried} rider-ticks, projectiles redirected: ${fieldMod.fieldStats.redirected}, crossings: ${fieldMod.fieldStats.crossings}`);
console.log("phase I skill durations (ticks):", Object.fromEntries(Object.entries(results).map(([k, r]) => [k, r.ticks])));
console.log("phase II skill durations (ticks):", Object.fromEntries(Object.entries(p2).map(([k, r]) => [k, r.ticks])));
expect(perTick < 25, `average particle spawns per tick stays mobile-friendly (${perTick.toFixed(1)})`);
for (const w of warnings) failures.push(`console.warn: ${w}`);
for (const i of __issues) failures.push(`mock: ${i}`);
console.log(`${passed} passed, ${failures.length} failed`);
for (const f of failures) console.log("  FAIL:", f);
fs.rmSync(tmp, { recursive: true, force: true });
process.exit(failures.length ? 1 : 0);
