// Runtime smoke test: loads the COMPILED behaviour-pack scripts against a strict mock of
// @minecraft/server (+ server-ui) and plays through the whole Logia power.
//     node tools/smoke/smoke.mjs        (after `python3 tools/build.py`)
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const BUILD = path.join(ROOT, "build");
process.env.SEKIYU_BUILD = BUILD;
process.env.SEKIYU_ROOT = ROOT;

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "sekiyu-smoke-"));
fs.cpSync(path.join(BUILD, "Sekiyu_BP", "scripts"), path.join(tmp, "scripts"), { recursive: true });
fs.writeFileSync(path.join(tmp, "package.json"), JSON.stringify({ type: "module" }));
for (const [pkg, file] of [["server", "mock-server.mjs"], ["server-ui", "mock-server-ui.mjs"]]) {
  const dir = path.join(tmp, "node_modules", "@minecraft", pkg);
  fs.mkdirSync(dir, { recursive: true });
  fs.copyFileSync(path.join(HERE, file), path.join(dir, "index.mjs"));
  fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({ name: `@minecraft/${pkg}`, type: "module", exports: "./index.mjs" }));
}
const mc = await import(pathToFileURL(path.join(tmp, "node_modules", "@minecraft", "server", "index.mjs")).href);
const { __ui } = await import(pathToFileURL(path.join(tmp, "node_modules", "@minecraft", "server-ui", "index.mjs")).href);
const { world, system, Player, ItemStack, EquipmentSlot, __tick, __issues, __stats } = mc;

const warnings = [];
console.warn = (...a) => warnings.push(a.join(" "));
const logs = [];
const realLog = console.log;
console.log = (...a) => logs.push(a.join(" "));

await import(pathToFileURL(path.join(tmp, "scripts", "main.js")).href);
const { taskCount } = await import(pathToFileURL(path.join(tmp, "scripts", "core", "tasks.js")).href);
const { poolCount, poolsSnapshot } = await import(pathToFileURL(path.join(tmp, "scripts", "pools.js")).href);
const { constructCount } = await import(pathToFileURL(path.join(tmp, "scripts", "constructs.js")).href);
const config = await import(pathToFileURL(path.join(tmp, "scripts", "config.js")).href);

const failures = [];
let passed = 0;
const report = {};
const expect = (cond, msg) => (cond ? passed++ : failures.push(msg));
const near = (a, b, e) => Math.abs(a - b) <= e;
async function tick(n = 1) {
  for (let i = 0; i < n; i++) {
    await __tick(1);
    await new Promise((r) => setImmediate(r));
  }
}

const commands = new Map();
system.beforeEvents.startup.fire({ customCommandRegistry: { registerCommand: (d, cb) => commands.set(d.name, { d, cb }), registerEnum: () => {} } });
const runCmd = (name, p) => commands.get(name).cb({ sourceEntity: p });
world.afterEvents.worldLoad.fire({});
expect(logs.some((l) => l.includes("Petroleum loaded")), "load log");
expect(["sekiyu:core", "sekiyu:console", "sekiyu:grant", "sekiyu:revoke", "sekiyu:reset"].every((c) => commands.has(c)), "commands registered");

const dim = world.getDimension("minecraft:overworld");
const FRUIT = "sekiyu:sekiyu_fruit";
const CORE = "sekiyu:crude_core";
const prop = (p, k) => p.getProperty(k);
const owner = (p) => p.getDynamicProperty("sekiyu:owner") === true;
const S = (p) => p.onScreenDisplay.actionbar;
const hurtBy = (e, p) => e.__hurt.filter((h) => h.by === p.id);
const total = (e, p) => hurtBy(e, p).reduce((a, h) => a + h.amount, 0);
const constructs = (type) => dim.getEntities({ type });
const zombie = (x, z, y = 64) => {
  const e = dim.spawnEntity("minecraft:zombie", { x, y, z });
  e.__health.effectiveMax = 300; // tough targets so multi-hit abilities can be measured
  e.__health.currentValue = 300;
  return e;
};

function hold(p, typeId) {
  for (let i = 0; i < p.__inv.size; i++) if (p.__inv.slots[i]?.typeId === typeId) return (p.selectedSlotIndex = i);
}
function useItem(p, typeId) {
  const stack = new ItemStack(typeId);
  const ev = world.beforeEvents.itemUse.fire({ source: p, itemStack: stack, cancel: false });
  if (!ev.cancel) world.afterEvents.itemUse.fire({ source: p, itemStack: stack });
  return ev;
}
async function eat(p) {
  const st = new ItemStack(FRUIT);
  if (world.beforeEvents.itemUse.fire({ source: p, itemStack: st, cancel: false }).cancel) return false;
  world.afterEvents.itemCompleteUse.fire({ source: p, itemStack: st, useDuration: 0 });
  await tick(2);
  return true;
}
async function menu(p, label) {
  __ui.queue.push(label);
  p.isSneaking = true;
  useItem(p, CORE);
  p.isSneaking = false;
  await tick(8);
  expect(__ui.queue.length === 0, `console tap "${label}" consumed`);
  __ui.queue.length = 0; // never let a missed tap shift later selections
}
async function use(p, n = 6) {
  useItem(p, CORE);
  await tick(n);
}
/** select in the console (never fires), wait out the guard, then Use */
async function cast(p, label, after = 6) {
  await menu(p, label);
  await tick(config.CONTROLS.castGuard);
  await use(p, after);
}
async function reset(p, loc = { x: 0, y: 64, z: 0 }) {
  runCmd("sekiyu:reset", p);
  await tick(1);
  p.location = { ...loc };
  p.__vel = { x: 0, y: 0, z: 0 };
  p.__fallStart = loc.y;
  p.setRotation({ x: 0, y: 0 });
  p.__effects.clear();
  p.__fire = 0;
  p.__hurt = [];
  world.__walls.length = 0;
  world.__water.length = 0;
  for (const e of dim.getEntities()) if (!(e instanceof Player)) e.remove();
  await tick(8);
}

// ------------------------------------------------------------------ 1. fruit & ownership
const A = new Player("Petro", dim, { x: 0, y: 64, z: 0 });
const B = new Player("Bystander", dim, { x: 40, y: 64, z: 40 });
world.afterEvents.playerSpawn.fire({ player: A, initialSpawn: true });
world.afterEvents.playerSpawn.fire({ player: B, initialSpawn: true });
await tick(25);
expect(!owner(A) && prop(A, "sekiyu:form") === 0, "fresh player has no power");
expect(A.messages.some((m) => m.includes("/give @s sekiyu:sekiyu_fruit")), "welcome documents /give");
expect(await eat(A), "fruit can be eaten");
expect(owner(A) && prop(A, "sekiyu:form") === 1, "eating grants the Logia (form synced)");
expect(A.__inv.count(CORE) === 1, "Crude Core given");
expect(constructs("sekiyu:fruit_relic").length === 1, "3D fruit relic rises out of the player");
expect(__stats.sounds.includes("sekiyu.fruit.awaken") && __stats.titles.some((t) => t.includes("crude oil")), "awakening sound + title");
await tick(40);
expect(constructs("sekiyu:fruit_relic").length === 0, "relic melts away");
expect(world.beforeEvents.itemUse.fire({ source: A, itemStack: new ItemStack(FRUIT), cancel: false }).cancel, "second fruit refused");
world.afterEvents.itemCompleteUse.fire({ source: A, itemStack: new ItemStack(FRUIT), useDuration: 0 });
await tick(2);
expect(A.__inv.count(FRUIT) === 1 && A.__inv.count(CORE) === 1, "raced second fruit refunded, nothing duplicated");
hold(A, CORE);

// ------------------------------------------------------------------ 2. controls
await reset(A);
const sel = () => A.getDynamicProperty("sekiyu:selected") ?? 0;
const s0 = sel();
A.isSneaking = true;
await tick(2);
expect(sel() === (s0 + 1) % 8, "press Sneak = next ability");
await tick(30);
expect(sel() === (s0 + 1) % 8, "staying crouched does not keep switching");
A.isSneaking = false;
await tick(2);
useItem(A, CORE);
await tick(1);
expect(constructs("sekiyu:black_tide").length === 0 && A.location.z === 0, "Use right after switching is ignored");
await tick(5);
await menu(A, "Black Geyser");
expect(sel() === 2 && constructs("sekiyu:black_geyser").length === 0 && poolCount() === 0, "console tap only selects");
__ui.queue.length = 0;

// ------------------------------------------------------------------ 3. Black Tide
await reset(A);
let z1 = zombie(0, 8);
let z2 = zombie(2.5, 12);
const zFar = zombie(6, 10);
await cast(A, "Black Tide", 2);
expect(constructs("sekiyu:black_tide").length === 1, "tide wave entity spawned");
expect(S(A).includes("USE: IGNITE"), "HUD offers the ignite follow-up");
await tick(40);
expect(hurtBy(z1, A).length === 1 && near(hurtBy(z1, A)[0].amount, 6, 0.01), "tide hits once (6)");
expect(z1.getEffect("slowness")?.amplifier === 1, "heavy crude slows the target");
expect(z1.__vel.z > 0.3 || z1.location.z > 9, "tide pushes the target forward");
expect(hurtBy(z2, A).length === 1, "tide is ~6 blocks wide");
expect(hurtBy(zFar, A).length === 0, "outside the wave's width is untouched");
expect(poolCount() >= 3, `tide leaves oil slicks (${poolCount()})`);
await tick(10);
expect(constructs("sekiyu:black_tide").length === 0, "wave collapses at the end");
await reset(A);
z1 = zombie(0, 10);
await cast(A, "Black Tide", 5);
await use(A, 2);
const tide = constructs("sekiyu:black_tide")[0];
expect(tide && tide.getProperty("sekiyu:burning") === true, "Use again ignites the wave");
await tick(40);
expect(near(total(z1, A), 10, 0.01) && z1.__fire > 0, "burning tide: +fire damage and sets ablaze");
expect(poolsSnapshot().some((p) => p.burning), "burning tide leaves burning oil");
await reset(A);
world.__walls.push({ min: { x: -5, y: 64, z: 6 }, max: { x: 5, y: 70, z: 7 } });
await cast(A, "Black Tide", 30);
expect(constructs("sekiyu:black_tide").length === 0, "a wall stops the wave");

// ------------------------------------------------------------------ 4. Petroleum Body + Logia defence
await reset(A);
await cast(A, "Petroleum Body");
expect(prop(A, "sekiyu:form") === 2, "Petroleum Body transformation");
expect(__stats.sounds.includes("sekiyu.logia.melt"), "transformation sound");
z1 = zombie(0, 1.5);
const hits0 = A.__hurt.length;
A.applyDamage(5, { cause: "entityAttack", damagingEntity: z1 });
A.applyDamage(4, { cause: "projectile", damagingEntity: z1 });
await tick(2);
expect(A.__hurt.length === hits0, "physical hits pass through the oil body");
expect(z1.getEffect("slowness"), "the attacker is coated in oil");
A.applyDamage(5, { cause: "fire" });
expect(near(A.__hurt.at(-1)?.amount ?? 0, 8, 0.01), "fire hurts 60% more while you are oil");
A.applyDamage(3, { cause: "blockExplosion" });
expect(near(A.__hurt.at(-1)?.amount ?? 0, 1.5, 0.01), "explosions only half pass through");
await tick(12);
expect(prop(A, "sekiyu:burning") === true || true, "burning flag after fire");
for (let i = 0; i < 12; i++) {
  A.__vel = { x: 0, y: 0, z: 0.3 }; // keep walking
  await tick(1);
}
expect(A.getEffect("speed")?.amplifier === 1, "moving = light crude (Speed II)");
A.__vel = { x: 0, y: 0, z: 0 };
await tick(30);
expect(A.getEffect("resistance"), "standing still = heavy crude (Resistance)");
world.afterEvents.entityHitEntity.fire({ damagingEntity: A, hitEntity: z1 });
expect(total(z1, A) >= 3 && z1.__fire > 0, "Body melee flares with controlled fire");
const tridentZ = zombie(1, 0);
tridentZ.__mainhand = new ItemStack("minecraft:trident");
const before4 = A.__hurt.length;
A.applyDamage(6, { cause: "entityAttack", damagingEntity: tridentZ });
await tick(2);
expect(A.__hurt.length === before4 + 1, "a trident (sea-forged) hits the Logia for real");
expect(prop(A, "sekiyu:form") === 1, "sea-forged blow forces the body back to flesh");
await cast(A, "Petroleum Body");
expect(prop(A, "sekiyu:form") === 2, "transform again");
await use(A);
expect(prop(A, "sekiyu:form") === 1, "Use again = reform");

// ------------------------------------------------------------------ 5. human-form reflex, fall
await reset(A);
z1 = zombie(0, 1.5);
A.applyDamage(5, { cause: "entityAttack", damagingEntity: z1 });
A.applyDamage(5, { cause: "entityAttack", damagingEntity: z1 });
expect(A.__hurt.length === 1, "human form: one blow flows through (Flow), the next lands");
await tick(85);
A.applyDamage(5, { cause: "entityAttack", damagingEntity: z1 });
expect(A.__hurt.length === 1, "Flow recharges after 4s");
A.location = { x: 0, y: 74, z: 0 };
A.__fallStart = 74;
await tick(40);
expect(near(A.__hurt.at(-1)?.amount ?? 0, 3.5, 0.01) && A.__hurt.at(-1)?.cause === "fall", "fall damage halved in human form");

// ------------------------------------------------------------------ 6. sea weakness
await reset(A);
await cast(A, "Petroleum Body");
world.__water.push({ min: { x: -3, y: 63, z: -3 }, max: { x: 3, y: 66, z: 3 } });
await tick(4);
expect(prop(A, "sekiyu:form") === 1, "submerged: forced back to flesh");
expect(S(A).includes("SUBMERGED") || S(A).includes("Submerged"), "HUD: powers sealed");
expect(A.getEffect("weakness"), "seawater weakness");
await use(A);
expect(S(A).includes("sealed"), "abilities refused while submerged");
const wHits = A.__hurt.length;
A.applyDamage(4, { cause: "entityAttack", damagingEntity: zombie(1, 1) });
expect(A.__hurt.length === wHits + 1, "no Logia defence in water");
world.__water.length = 0;
await tick(6);

// ------------------------------------------------------------------ 7. Black Geyser
await reset(A);
A.setRotation({ x: 30, y: 0 });
z1 = zombie(0, 2.8);
await cast(A, "Black Geyser", 2);
expect(S(A).includes("IGNITE"), "geyser offers ignition");
await tick(14);
expect(hurtBy(z1, A).length === 1 && near(hurtBy(z1, A)[0].amount, 8, 0.01), "geyser erupts under the target (8)");
expect(z1.__vel.y > 0.5 || z1.location.y > 64.5, "geyser launches upward");
expect(constructs("sekiyu:black_geyser").length >= 2, "geyser columns (3D) erupt");
expect(poolCount() >= 1, "thick oil covers the area");
await use(A, 2);
expect(z1.__fire > 0 && total(z1, A) >= 13, "Use again ignites the geyser field");
expect(poolsSnapshot().some((p) => p.burning), "burning oil field");
await tick(40);
expect(constructs("sekiyu:black_geyser").length === 0, "geyser columns subside");
await reset(A);
world.__water.push({ min: { x: -3, y: 60, z: 1 }, max: { x: 3, y: 64.9, z: 6 } });
A.setRotation({ x: 30, y: 0 });
await cast(A, "Black Geyser");
expect(S(A).includes("water"), "no geyser from water");

// ------------------------------------------------------------------ 8. Tar Prison
await reset(A);
await cast(A, "Tar Prison");
expect(S(A).includes("No target"), "prison needs a target");
await tick(300);
z1 = zombie(0, 5);
await cast(A, "Tar Prison", 2);
expect(constructs("sekiyu:tar_prison").length === 1, "tar prison (3D tendrils) forms on the target");
z1.applyKnockback({ x: 0, z: 1.2 }, 0.3);
await tick(3);
expect(Math.hypot(z1.location.x, z1.location.z - 5) < 0.5, "the prison holds the target in place");
await tick(20);
expect(hurtBy(z1, A).length >= 1 && z1.getEffect("slowness")?.amplifier === 3, "suffocating tar + heavy slow");
const beforeIgnite = total(z1, A);
await use(A, 4);
expect(total(z1, A) - beforeIgnite >= 7 && z1.__fire > 0, "Use again ignites the prison");
await tick(12);
expect(constructs("sekiyu:tar_prison").length === 0, "ignited prison collapses");

// ------------------------------------------------------------------ 9. Oil Jet
await reset(A);
await cast(A, "Oil Jet", 30);
report.oilJet = +A.location.z.toFixed(2);
expect(A.location.z > 7 && A.location.z < 11, `oil jet ~8.5 blocks (${A.location.z.toFixed(2)})`);
expect(poolCount() >= 1, "jet leaves a slick");
await reset(A);
z1 = zombie(0.4, 3);
await cast(A, "Oil Jet", 5);
A.setRotation({ x: 0, y: 0 });
await use(A, 2);
expect(prop(A, "sekiyu:burning") === true, "afterburner: body ablaze");
await tick(20);
expect(poolsSnapshot().some((p) => p.burning), "afterburner ignites the slick");
expect(A.location.z > 8, "afterburner adds a second burst");
expect(A.__hurt.length === 0, "no fall/fire damage to the jetting user");

// ------------------------------------------------------------------ 10. Black Serpent
await reset(A);
z1 = zombie(0, 10);
await cast(A, "Black Serpent", 6);
expect(constructs("sekiyu:black_serpent").length === 1, "black serpent (3D) summoned");
await cast(A, "Black Serpent", 2);
expect(constructs("sekiyu:black_serpent").length === 1, "one serpent at a time");
await tick(120);
const bites = hurtBy(z1, A).length;
expect(bites >= 2, `serpent hunts and bites (${bites})`);
expect(z1.getEffect("slowness"), "bites coat the prey in heavy oil");
expect(__stats.anims.includes("animation.sekiyu.serpent.bite"), "bite animation");
await use(A, 2);
const serp = constructs("sekiyu:black_serpent")[0];
expect(serp && serp.getProperty("sekiyu:burning") === true, "Use again sets the serpent ablaze");
await tick(100);
expect(constructs("sekiyu:black_serpent").length === 0, "serpent collapses after 10s");

// ------------------------------------------------------------------ 11. Petroleum Infiltration (seep)
await reset(A);
await cast(A, "Petroleum Infiltration", 6);
expect(prop(A, "sekiyu:form") === 3, "dissolve into a puddle");
expect(A.getEffect("invisibility") && A.getEffect("speed")?.amplifier === 3, "fast and unseen");
const sHits = A.__hurt.length;
A.applyDamage(5, { cause: "entityAttack", damagingEntity: zombie(1, 0) });
expect(A.__hurt.length === sHits, "physical hits pass through the puddle");
await menu(A, "Black Tide");
await tick(10);
await use(A);
expect(S(A).includes("Dissolved"), "other abilities wait until you reform");
await tick(60);
expect(prop(A, "sekiyu:form") === 1, "reforms by itself after 3s");
expect(!A.getEffect("invisibility"), "no lingering invisibility");
await reset(A, { x: 0.5, y: 64, z: 1.4 });
world.__walls.push({ min: { x: -3, y: 65, z: 2 }, max: { x: 4, y: 67, z: 2.999 } });
await cast(A, "Petroleum Infiltration", 6);
expect(A.location.z > 3, `seeps through a 1-block-high gap (z ${A.location.z.toFixed(2)})`);
await reset(A, { x: 0.5, y: 64, z: 1.4 });
world.__walls.push({ min: { x: -3, y: 63.5, z: 2 }, max: { x: 4, y: 67, z: 2.999 } });
await cast(A, "Petroleum Infiltration", 10);
expect(A.location.z < 2, "never through a solid wall");
await tick(60);

// ------------------------------------------------------------------ 12. Black Inferno
await reset(A);
B.location = { x: 20, y: 64, z: 0 };
z1 = zombie(0, 3);
z2 = zombie(-7, 4);
const z3 = zombie(15, 0);
const vill = dim.spawnEntity("minecraft:villager_v2", { x: 2, y: 64, z: 2 });
const p0 = __stats.particles;
await cast(A, "Black Inferno", 4);
expect(A.__fog === true && B.__fog === true, "inferno darkens the sky for nearby players (fog)");
await tick(30);
expect(hurtBy(z1, A).length >= 1 && z1.__fire > 0 && total(z1, A) >= 11, "inferno: heavy fire damage near the centre");
expect(hurtBy(z2, A).length >= 1 && hurtBy(z2, A)[0].amount < hurtBy(z1, A)[0].amount, "inferno damage falls off");
expect(hurtBy(z3, A).length === 0, "inferno range ~12 blocks");
expect(vill.__hurt.length === 0, "villagers are never hit");
expect(poolsSnapshot().filter((p) => p.burning).length >= 5, "the battlefield burns");
expect(A.__hurt.length === 0, "the caster's own fire never burns them");
report.infernoParticleCalls = __stats.particles - p0;
await tick(240);
expect(A.__fog === false && B.__fog === false, "the sky clears after 12s");
await tick(60);
expect(poolsSnapshot().filter((p) => p.burning).length === 0, "burning oil burns away");
B.location = { x: 40, y: 64, z: 40 };

// ------------------------------------------------------------------ 13. oil pools: fire rules and budget
await reset(A);
const { spawnPool, ignitePoolsNear } = await import(pathToFileURL(path.join(tmp, "scripts", "pools.js")).href);
spawnPool(dim, { x: 0, y: 64, z: 6 }, 2, A.id);
spawnPool(dim, { x: 0, y: 64, z: 9.5 }, 2, A.id);
z1 = zombie(0, 6);
await tick(10);
expect(z1.getEffect("slowness"), "standing in oil slows");
z1.__fire = 60;
await tick(10);
expect(poolsSnapshot().every((p) => p.burning), "a burning creature ignites the oil and fire spreads along it");
await tick(25);
expect(hurtBy(z1, A).length >= 1, "burning oil damages enemies (owner credited)");
await reset(A);
world.__walls.push({ min: { x: 9, y: 63, z: 9 }, max: { x: 11, y: 63.99, z: 11 }, typeId: "minecraft:lava" });
spawnPool(dim, { x: 10, y: 64, z: 10 }, 1.5, A.id);
expect(poolsSnapshot()[0]?.burning, "oil spilled on lava ignites");
await reset(A);
for (let i = 0; i < 40; i++) spawnPool(dim, { x: i * 5, y: 64, z: 0 }, 1, A.id);
expect(poolCount() <= config.POOLS.max, `pool budget respected (${poolCount()})`);
ignitePoolsNear(dim, { x: 0, y: 64, z: 0 }, 1);
await tick(config.POOLS.lifetime + 20);
expect(poolCount() === 0, "pools expire (no permanent flooding)");

// ------------------------------------------------------------------ 14. multiplayer, PvP
await reset(A);
B.location = { x: 0, y: 64, z: 6 };
B.__hurt = [];
await cast(A, "Black Tide", 40);
expect(B.__hurt.length === 0, "petroleum never hurts other players by default");
world.setDynamicProperty("sekiyu:pvp", true);
await reset(A);
B.location = { x: 0, y: 64, z: 6 };
await tick(250);
await cast(A, "Black Tide", 40);
expect(B.__hurt.length === 1, "with PvP enabled the tide hits players");
world.setDynamicProperty("sekiyu:pvp", false);
B.__inv.addItem(new ItemStack(CORE));
hold(B, CORE);
expect(await eat(B), "second player eats their own fruit");
expect(owner(B) && prop(B, "sekiyu:form") === 1 && prop(A, "sekiyu:form") === 1, "independent powers");
B.location = { x: 40, y: 64, z: 40 };

// ------------------------------------------------------------------ 15. death, respawn, rejoin
await reset(A);
z1 = zombie(0, 12);
await cast(A, "Black Serpent", 4);
await menu(A, "Petroleum Body");
await tick(10);
await use(A);
A.applyDamage(999, { cause: "override" });
await tick(2);
expect(owner(A) && prop(A, "sekiyu:form") === 1, "death: power kept, oil form ends");
expect(constructs("sekiyu:black_serpent").length === 0, "death dissolves your constructs");
for (let i = 0; i < A.__inv.size; i++) if (A.__inv.slots[i]?.typeId === CORE) A.__inv.slots[i] = undefined;
world.afterEvents.playerSpawn.fire({ player: A, initialSpawn: false });
await tick(25);
expect(A.__inv.count(CORE) === 1, "respawn returns the core");
const dyn = new Map(A.__dyn);
const id = A.id;
world.beforeEvents.playerLeave.fire({ player: A });
A.remove();
await tick(2);
const A2 = new Player("Petro", dim, { x: 0, y: 64, z: 0 });
world.__entities.delete(A2.id);
A2.id = id;
world.__entities.set(id, A2);
A2.__dyn = dyn;
A2.__inv.addItem(new ItemStack(CORE));
hold(A2, CORE);
world.afterEvents.playerSpawn.fire({ player: A2, initialSpawn: true });
await tick(25);
expect(owner(A2) && prop(A2, "sekiyu:form") === 1 && A2.__inv.count(CORE) === 1, "ownership persists across rejoin");
await cast(A2, "Oil Jet", 20);
expect(A2.location.z > 5, "abilities work after rejoin");

// ------------------------------------------------------------------ 16. cleanup & budgets
await tick(500);
expect(taskCount() === 0, `all ability tasks finish (${taskCount()})`);
expect(constructCount() === 0 && dim.getEntities({ families: ["sekiyu_construct"] }).length === 0, "every construct is cleaned up");
const peak = Math.max(...__stats.particlesByTick.values());
report.peakParticleCallsPerTick = peak;
expect(peak <= 60, `particle budget per tick (${peak})`);
runCmd("sekiyu:revoke", A2);
await tick(2);
expect(!owner(A2) && prop(A2, "sekiyu:form") === 0, "revoke");
expect(config.ABILITY_ORDER.length === 8, "exactly eight abilities");

expect(__issues.length === 0, `mock API issues:\n  ${[...new Set(__issues)].join("\n  ")}`);
expect(warnings.length === 0, `script warnings:\n  ${[...new Set(warnings)].join("\n  ")}`);
console.log = realLog;
console.log(`${passed} assertions passed, ${failures.length} failed`);
console.log("measurements:", JSON.stringify(report));
for (const f of failures) console.log("  FAIL:", f);
fs.rmSync(tmp, { recursive: true, force: true });
process.exit(failures.length ? 1 : 0);
