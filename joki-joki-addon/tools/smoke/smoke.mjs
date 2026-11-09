// Runtime smoke test: loads the COMPILED behaviour-pack scripts against a strict mock of
// @minecraft/server (+ server-ui) and plays through the whole power:
// eating the fruit, every ability, gears, heat, Overheat, death, rejoin, multiplayer, menus, HUD.
//     node tools/smoke/smoke.mjs        (after `python3 tools/build.py`)
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const BUILD = path.join(ROOT, "build");
process.env.JOKI_BUILD = BUILD;
process.env.JOKI_ROOT = ROOT;

// ------------------------------------------------------------------ stage scripts + mocks
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "joki-smoke-"));
fs.cpSync(path.join(BUILD, "Joki_BP", "scripts"), path.join(tmp, "scripts"), { recursive: true });
fs.writeFileSync(path.join(tmp, "package.json"), JSON.stringify({ type: "module" }));
for (const [pkg, file] of [["server", "mock-server.mjs"], ["server-ui", "mock-server-ui.mjs"]]) {
  const dir = path.join(tmp, "node_modules", "@minecraft", pkg);
  fs.mkdirSync(dir, { recursive: true });
  fs.copyFileSync(path.join(HERE, file), path.join(dir, "index.mjs"));
  fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({ name: `@minecraft/${pkg}`, type: "module", exports: "./index.mjs" }));
}
const mc = await import(pathToFileURL(path.join(tmp, "node_modules", "@minecraft", "server", "index.mjs")).href);
const { __ui } = await import(pathToFileURL(path.join(tmp, "node_modules", "@minecraft", "server-ui", "index.mjs")).href);
const { world, system, Player, ItemStack, __tick, __issues, __stats } = mc;

const warnings = [];
console.warn = (...a) => warnings.push(a.join(" "));
const logs = [];
const realLog = console.log;
console.log = (...a) => logs.push(a.join(" "));

await import(pathToFileURL(path.join(tmp, "scripts", "main.js")).href);
const { taskCount } = await import(pathToFileURL(path.join(tmp, "scripts", "core", "tasks.js")).href);
const config = await import(pathToFileURL(path.join(tmp, "scripts", "config.js")).href);

// ------------------------------------------------------------------ harness
const failures = [];
let passed = 0;
const report = {};
function expect(cond, msg) {
  if (cond) passed++;
  else failures.push(msg);
}
const near = (a, b, eps) => Math.abs(a - b) <= eps;
async function tick(n = 1) {
  for (let i = 0; i < n; i++) {
    await __tick(1);
    await new Promise((r) => setImmediate(r));
  }
}

// custom commands registered at startup
const commands = new Map();
system.beforeEvents.startup.fire({
  customCommandRegistry: {
    registerCommand: (def, cb) => commands.set(def.name, { def, cb }),
    registerEnum: () => {},
  },
});
const runCmd = (name, p) => commands.get(name).cb({ sourceEntity: p });
world.afterEvents.worldLoad.fire({});
expect(logs.some((l) => l.includes("Steam Pressure loaded")), "load log");
expect(["joki:valve", "joki:console", "joki:grant", "joki:revoke", "joki:cool"].every((c) => commands.has(c)), "5 custom commands registered");
expect(commands.get("joki:grant").def.cheatsRequired === true && commands.get("joki:valve").def.cheatsRequired === false, "command permissions");

const dim = world.getDimension("minecraft:overworld");
const FRUIT = "joki:joki_fruit";
const VALVE = "joki:steam_valve";
const prop = (p, k) => p.getProperty(k);
const owner = (p) => p.getDynamicProperty("joki:owner") === true;
const valves = (p) => p.__inv.count(VALVE);

function holdValve(p) {
  const inv = p.__inv;
  for (let i = 0; i < inv.size; i++) {
    if (inv.slots[i]?.typeId === VALVE) {
      p.selectedSlotIndex = i;
      return;
    }
  }
}
function useItem(p, typeId) {
  const stack = new ItemStack(typeId);
  const ev = world.beforeEvents.itemUse.fire({ source: p, itemStack: stack, cancel: false });
  if (!ev.cancel) world.afterEvents.itemUse.fire({ source: p, itemStack: stack });
  return ev;
}
async function eat(p) {
  const stack = new ItemStack(FRUIT);
  const ev = world.beforeEvents.itemUse.fire({ source: p, itemStack: stack, cancel: false });
  if (ev.cancel) return false;
  world.afterEvents.itemStartUse.fire({ source: p, itemStack: stack, useDuration: 32 });
  world.afterEvents.itemCompleteUse.fire({ source: p, itemStack: stack, useDuration: 0 });
  await tick(2);
  return true;
}
/** Open the Steam Console (Sneak + Use while looking down) and tap the button whose label contains `label`. */
async function menu(p, label) {
  __ui.queue.push(label);
  const rot = p.getRotation();
  p.setRotation({ x: 85, y: rot.y });
  p.isSneaking = true;
  useItem(p, VALVE);
  p.isSneaking = false;
  p.setRotation(rot);
  await tick(config.CONTROLS.cycleDebounce);
  expect(__ui.queue.length === 0, `console tap "${label}" was consumed`);
}
async function use(p) {
  useItem(p, VALVE);
  await tick(6);
}
/** Select an ability in the console (does NOT fire), wait out the cast guard, then Use to fire it. */
async function cast(p, label) {
  await menu(p, label);
  await tick(config.CONTROLS.castGuard);
  await use(p);
}
/** Sneak + Use at a given pitch (0 = level, -80 = looking up). */
async function sneakUse(p, pitch = 0) {
  const rot = p.getRotation();
  p.setRotation({ x: pitch, y: rot.y });
  p.isSneaking = true;
  useItem(p, VALVE);
  p.isSneaking = false;
  p.setRotation(rot);
  await tick(1);
}
async function reset(p, loc = { x: 0, y: 64, z: 0 }) {
  runCmd("joki:cool", p);
  await tick(1);
  p.location = { ...loc };
  p.__vel = { x: 0, y: 0, z: 0 };
  p.__fallStart = loc.y;
  p.setRotation({ x: 0, y: 0 });
  p.__effects.clear();
  p.__hurt = [];
  for (const e of dim.getEntities()) if (!(e instanceof Player)) e.remove();
  await tick(6);
}
const zombie = (x, z, y = 64) => dim.spawnEntity("minecraft:zombie", { x, y, z });
const S = (p) => p.onScreenDisplay.actionbar;
const hurtBy = (e, p) => e.__hurt.filter((h) => h.by === p.id);
const heatOf = (p) => {
  const m = S(p).match(/(\d+)% /);
  return m ? Number(m[1]) : NaN;
};

// ------------------------------------------------------------------ 1. join, fruit, ownership
const A = new Player("Steamer", dim, { x: 0, y: 64, z: 0 });
const B = new Player("Bystander", dim, { x: 40, y: 64, z: 40 });
world.afterEvents.playerSpawn.fire({ player: A, initialSpawn: true });
world.afterEvents.playerSpawn.fire({ player: B, initialSpawn: true });
await tick(25);
expect(prop(A, "joki:mode") === 0 && !owner(A), "fresh player has no power");
expect(A.messages.some((m) => m.includes("/give @s joki:joki_fruit")), "welcome message documents /give");

A.__inv.addItem(new ItemStack(VALVE));
holdValve(A);
__ui.shown.length = 0;
await use(A);
expect(__ui.shown.at(-1)?.title.includes("Steam Valve") && !owner(A), "valve does nothing for non-users (explains the fruit)");

expect(await eat(A), "first fruit can be eaten");
expect(owner(A), "eating grants ownership");
expect(prop(A, "joki:mode") === 1 && prop(A, "joki:overheat") === false, "properties synced to NORMAL");
expect(valves(A) === 1, "no duplicate valve when one is already carried");
expect(__stats.titles.some((t) => t.includes("Steam Pressure awakened")), "awakening title");
expect(__stats.sounds.includes("joki.fruit.awaken"), "awakening sound");

const second = world.beforeEvents.itemUse.fire({ source: A, itemStack: new ItemStack(FRUIT), cancel: false });
expect(second.cancel === true, "second fruit is refused before eating");
world.afterEvents.itemCompleteUse.fire({ source: A, itemStack: new ItemStack(FRUIT), useDuration: 0 });
await tick(2);
expect(A.__inv.count(FRUIT) === 1 && owner(A) && valves(A) === 1, "a raced second fruit is refunded, data intact");
expect(!owner(B) && prop(B, "joki:mode") === 0, "other player unaffected");

// ------------------------------------------------------------------ 1b. switching skills never casts
await reset(A);
const sel = () => A.getDynamicProperty("joki:selected") ?? 0;
const heat0 = S(A);
const hurt0 = __stats.anims.length;
const startSel = sel();
await sneakUse(A, 0);
expect(sel() === (startSel + 1) % 9, "Sneak + Use (level) selects the next skill");
expect(prop(A, "joki:mode") === 1 && __stats.anims.length === hurt0, "switching skills does not cast anything");
expect(__stats.titles.at(-1).includes("<"), "selected skill name flashes on screen");
await sneakUse(A, 0);
expect(sel() === (startSel + 1) % 9, "holding Sneak + Use steps at a readable pace (debounced)");
await tick(config.CONTROLS.cycleDebounce);
await sneakUse(A, 0);
expect(sel() === (startSel + 2) % 9, "next Sneak + Use step");
await tick(config.CONTROLS.cycleDebounce);
await sneakUse(A, -80);
expect(sel() === (startSel + 1) % 9, "Sneak + Use looking up selects the previous skill");
await tick(config.CONTROLS.cycleDebounce);
for (let i = 0; i < 12; i++) {
  await sneakUse(A, -80);
  await tick(config.CONTROLS.cycleDebounce);
}
expect(sel() >= 0 && sel() < 9, "selection wraps around both ways");
useItem(A, VALVE);
await tick(1);
expect(prop(A, "joki:mode") === 1, "Use right after a switch is ignored (cast guard)");
__ui.shown.length = 0;
await menu(A, "Pressure Dash");
expect(__ui.shown.at(-1)?.title.includes("Steam Console"), "Sneak + Use looking down opens the console");
expect(sel() === 1 && prop(A, "joki:mode") === 1 && A.location.z === 0, "tapping a skill in the console only selects it");
useItem(A, VALVE);
await tick(1);
expect(prop(A, "joki:mode") === 1, "the finger closing the console does not cast");
await tick(config.CONTROLS.castGuard);
await use(A);
expect(prop(A, "joki:mode") === 2 && A.location.z > 0.5, "after the guard, Use fires the selected skill");
void heat0;

// ------------------------------------------------------------------ 2. Steam Boost + auto ignition
await reset(A);
await cast(A, "Steam Boost");
expect(prop(A, "joki:mode") === 2, "casting from NORMAL auto-shifts to HEAT");
expect(A.getEffect("speed")?.amplifier === 1 && A.getEffect("strength")?.amplifier === 1, "boost adds +1 speed/strength on top of HEAT");
expect(near(heatOf(A), 15, 1), `boost heat 15 (hud says ${heatOf(A)})`);
expect(S(A).includes("HEAT") && S(A).includes("Steam Boost") && S(A).includes("BST"), "HUD shows mode, active skill and cooldowns");
expect(__stats.anims.includes("animation.joki.player.boost"), "boost animation");
await use(A);
expect(S(A).includes("recharging"), "recast during cooldown is refused with a notice");
await tick(165);
expect(A.getEffect("speed")?.amplifier === 0, "boost expires back to HEAT speed I");

// ------------------------------------------------------------------ 3. Pressure Dash
await reset(A);
await cast(A, "Pressure Dash");
await tick(30);
report.dashGroundHeat = +A.location.z.toFixed(2);
expect(A.location.z > 5.5 && A.location.z < 9 && Math.abs(A.location.x) < 0.01, `ground dash ~7 blocks forward (got ${A.location.z.toFixed(2)})`);
expect(A.__hurt.length === 0, "no damage from dash");

await reset(A);
world.__walls.push({ min: { x: -3, y: 63, z: 3 }, max: { x: 3, y: 70, z: 4 } });
await cast(A, "Pressure Dash");
await tick(30);
expect(A.location.z < 3, `walls stop the dash (z ${A.location.z.toFixed(2)})`);
world.__walls.length = 0;

await reset(A);
await menu(A, "Pressure Dash"); // pick it on the ground, then fire it in mid-air
await tick(config.CONTROLS.castGuard);
A.location = { x: 0, y: 70, z: 0 };
A.__fallStart = 70;
await use(A);
await tick(60);
report.dashAirHeat = +A.location.z.toFixed(2);
expect(A.location.y === 64 && A.location.z > 5, "mid-air dash works");
expect(A.__hurt.length === 0, "dash fall guard prevents fall damage");

// ------------------------------------------------------------------ 4. Boiler Jump
await reset(A);
await cast(A, "Boiler Jump");
let peak = 64;
for (let i = 0; i < 60; i++) {
  await tick(1);
  peak = Math.max(peak, A.location.y);
}
report.boilerJumpHeat = +(peak - 64).toFixed(2);
expect(peak - 64 > 5.5 && peak - 64 < 8.5, `boiler jump ~6.7 blocks (got ${(peak - 64).toFixed(2)})`);
expect(A.isOnGround && A.__hurt.length === 0, "landed without fall damage");
expect(__stats.sounds.includes("joki.steam.land"), "landing steam cushion");

await reset(A);
await menu(A, "Boiler Jump");
await tick(config.CONTROLS.castGuard);
A.location = { x: 0, y: 220, z: 0 };
A.__fallStart = 220;
await use(A);
expect(S(A).includes("Boiler Jump"), "mid-air boiler jump allowed once");
await tick(64);
expect(!A.isOnGround, "still airborne for the second attempt");
await use(A);
expect(S(A).includes("needs footing"), "second mid-air boiler jump refused");
A.location = { x: 0, y: 64, z: 0 };
A.__vel = { x: 0, y: 0, z: 0 };
A.__fallStart = 64;
await tick(2);

// ------------------------------------------------------------------ 5. Steam Cannon
await reset(A);
let z1 = zombie(0, 10);
await cast(A, "Steam Cannon");
await tick(10);
expect(hurtBy(z1, A).length === 1 && near(hurtBy(z1, A)[0].amount, 8 * 1.15, 0.01), "cannon hits a target 10 blocks ahead");
expect(z1.__vel.z > 0, "cannon knocks the target back along the shot");
expect(__stats.anims.includes("animation.joki.player.cannon"), "cannon pose");

await reset(A);
z1 = zombie(0, 30);
await cast(A, "Steam Cannon");
await tick(15);
expect(hurtBy(z1, A).length === 0, "cannon range is limited to 24 blocks");

await reset(A);
z1 = zombie(0, 10);
world.__walls.push({ min: { x: -3, y: 63, z: 5 }, max: { x: 3, y: 70, z: 6 } });
await cast(A, "Steam Cannon");
await tick(12);
expect(hurtBy(z1, A).length === 0, "cannon bolts collide with blocks");
world.__walls.length = 0;

await reset(A);
await menu(A, "Gear: PRESSURE");
expect(prop(A, "joki:mode") === 3, "menu shifts to PRESSURE");
z1 = zombie(0, 8);
await cast(A, "Steam Cannon");
await tick(20);
expect(hurtBy(z1, A).length === 2, `PRESSURE fires a 2-bolt burst (hits ${hurtBy(z1, A).length})`);

// ------------------------------------------------------------------ 6. Scald Burst
await reset(A);
z1 = zombie(0, 2);
const z2 = zombie(-3, 1.5);
let z3 = zombie(0, 9);
const vill = dim.spawnEntity("minecraft:villager_v2", { x: 2, y: 64, z: 0 });
const pet = dim.spawnEntity("minecraft:wolf", { x: -2, y: 64, z: 0 });
await cast(A, "Scald Burst");
await tick(3);
expect(hurtBy(z1, A).length === 1 && hurtBy(z2, A).length === 1, "scald hits enemies within ~4 blocks");
expect(hurtBy(z1, A)[0].amount > hurtBy(z2, A)[0].amount, "scald damage falls off with distance");
expect(z1.__vel.z > 0 && z2.__vel.x < 0, "scald knocks enemies outward");
expect(hurtBy(z3, A).length === 0, "scald does not reach 9 blocks");
expect(vill.__hurt.length === 0 && pet.__hurt.length === 0, "villagers and tamed pets are never hit");
expect(__stats.particles > 0 && __stats.sounds.includes("joki.steam.explode"), "scald cloud + explosion sound");

// ------------------------------------------------------------------ 7. Steam Knuckle
await reset(A);
z1 = zombie(0, 2.5);
const side = zombie(1.2, 2.2);
await cast(A, "Steam Knuckle");
expect(hurtBy(z1, A).length === 1 && near(hurtBy(z1, A)[0].amount, 10 * 1.15, 0.01), "knuckle punches the target in reach");
expect(hurtBy(side, A).length === 1 && near(hurtBy(side, A)[0].amount, 10 * 1.15 * 0.5, 0.01), "knuckle shockwave hits the cone");
expect(z1.__vel.z > 1 || z1.location.z > 4, `knuckle launches the target (z ${z1.location.z.toFixed(2)})`);

await reset(A);
await cast(A, "Steam Knuckle");
expect(S(A).includes("primed"), "no target: the fist is primed");
z1 = zombie(0, 6);
world.afterEvents.entityHitEntity.fire({ damagingEntity: A, hitEntity: z1 });
expect(hurtBy(z1, A).length === 1, "next melee hit detonates the primed knuckle");
world.afterEvents.entityHitEntity.fire({ damagingEntity: A, hitEntity: z1 });
expect(hurtBy(z1, A).length === 1, "primed knuckle is consumed by one hit");

// ------------------------------------------------------------------ 8. Jet Kick
await reset(A);
z1 = zombie(0, 3.2);
await cast(A, "Jet Kick");
await tick(10);
expect(hurtBy(z1, A).length === 1 && near(hurtBy(z1, A)[0].amount, 9 * 1.15, 0.01), "jet kick hits the first enemy in the lunge");
expect(z1.__vel.z > 2 || z1.location.z > 5, "jet kick blasts the target forward");
expect(A.location.z < z1.location.z, "kicker rebounds instead of passing through");
await reset(A);
await cast(A, "Jet Kick");
await tick(30);
report.kickLungeHeat = +A.location.z.toFixed(2);
expect(A.location.z > 2.5 && A.location.z < 6, `jet kick lunge is short (${A.location.z.toFixed(2)})`);

// ------------------------------------------------------------------ 9. Mist Veil
await reset(A);
z1 = zombie(0, 3);
z3 = zombie(0, 12);
await cast(A, "Mist Veil");
await tick(15);
expect(z1.getEffect("slowness")?.amplifier === 1 && z1.getEffect("blindness"), "mist slows and blinds enemies inside");
expect(!z3.getEffect("slowness"), "mist does not reach enemies outside");
expect(A.getEffect("invisibility"), "caster is invisible inside the mist");
A.location = { x: 0, y: 64, z: 12 };
await tick(40);
expect(!A.getEffect("invisibility"), "invisibility fades after leaving the mist");
await tick(170);
expect(!z1.getEffect("slowness"), "mist dissipates after ~8s");

// ------------------------------------------------------------------ 10. Redline
await reset(A);
await cast(A, "Redline");
expect(prop(A, "joki:mode") === 1, "redline needs an ignition first");
await tick(18);
expect(prop(A, "joki:mode") === 4, "REDLINE engaged after ignition");
expect(A.getEffect("speed")?.amplifier === 2 && A.getEffect("strength")?.amplifier === 2, "REDLINE gives speed III / strength III");
expect(__stats.titles.some((t) => t.includes("Maximum pressure")), "REDLINE title");
const h0 = heatOf(A);
await tick(40);
expect(heatOf(A) >= h0 + 7, `REDLINE heat climbs on its own (${h0} -> ${heatOf(A)})`);
z1 = zombie(0, 1.5);
world.afterEvents.entityHitEntity.fire({ damagingEntity: A, hitEntity: z1 });
expect(z1.__fire > 0 && z1.__vel.z > 0, "REDLINE melee scalds (fire) and shoves");
await cast(A, "Redline");
expect((S(A).includes("Already in REDLINE") || S(A).includes("Redline recharging")) && prop(A, "joki:mode") === 4, `redline cannot be stacked | ${S(A)}`);
await tick(200);
expect(prop(A, "joki:mode") === 2, "REDLINE ends after 12s and drops to HEAT");
expect(S(A).includes("RDL"), "redline cooldown is shown");

// ------------------------------------------------------------------ 11. heat accounting + independent cooldowns
await reset(A);
await cast(A, "Pressure Dash");
expect(near(heatOf(A), 12, 1), `dash costs 12 heat in HEAT (${heatOf(A)})`);
await tick(4);
await cast(A, "Boiler Jump");
expect(S(A).includes("Boiler Jump"), `cooldowns are independent (jump right after dash) | ${S(A)}`);
await tick(80);
await reset(A);
await menu(A, "Gear: PRESSURE");
const before = heatOf(A);
await cast(A, "Pressure Dash");
expect(near(heatOf(A) - before, 12 * 1.35, 1.2), `PRESSURE multiplies ability heat (+${heatOf(A) - before})`);

// ------------------------------------------------------------------ 12. Overheat
await reset(A);
A.location = { x: 0, y: 64, z: 0 };
await menu(A, "Gear: PRESSURE");
for (const name of ["Scald Burst", "Mist Veil", "Steam Cannon", "Steam Boost", "Steam Knuckle", "Jet Kick"]) {
  await cast(A, name);
  A.location = { x: 0, y: 64, z: 0 };
  A.__vel = { x: 0, y: 0, z: 0 };
  if (prop(A, "joki:overheat")) break;
}
expect(prop(A, "joki:overheat") === true, "reaching 100 heat triggers OVERHEAT");
expect(prop(A, "joki:mode") === 1, "OVERHEAT drops to NORMAL");
expect(A.getEffect("slowness")?.amplifier === 2, "OVERHEAT movement penalty");
expect(__stats.titles.some((t) => t.includes("Steam systems locked")) && __stats.sounds.includes("joki.overheat.alarm"), "OVERHEAT title + alarm");
await tick(5);
expect(S(A).includes("OVERHEAT"), "HUD shows the overheat warning");
await cast(A, "Pressure Dash");
expect(S(A).includes("OVERHEATED"), "abilities are locked while overheated");
await menu(A, "Gear: PRESSURE");
expect(prop(A, "joki:mode") === 1, "gears are locked while overheated");
await tick(200);
expect(prop(A, "joki:overheat") === false, "OVERHEAT ends on its own after ~10s");
expect(heatOf(A) <= 40, `gauge vented during the lockout (${heatOf(A)})`);
expect(__stats.sounds.includes("joki.overheat.cool"), "cooling sound on recovery");
await cast(A, "Pressure Dash");
expect(prop(A, "joki:mode") === 2 && !S(A).includes("OVERHEATED"), "abilities work again after recovery");
await tick(400);
expect(heatOf(A) === 0 || isNaN(heatOf(A)) || heatOf(A) < 5, "heat keeps cooling to zero");

// ------------------------------------------------------------------ 13. multiplayer separation + PvP
await reset(A);
B.location = { x: 1.5, y: 64, z: 0 };
B.__inv.addItem(new ItemStack(VALVE));
holdValve(B);
await cast(A, "Scald Burst");
expect(B.__hurt.length === 0, "steam abilities do not hurt other players by default");
expect(await eat(B), "second player can eat their own fruit");
expect(owner(B) && prop(B, "joki:mode") === 1, "B owns an independent power");
await cast(B, "Pressure Dash");
expect(prop(B, "joki:mode") === 2 && prop(A, "joki:mode") === 2, "both players run their own gears");
expect(!S(B).includes("recharging"), "A's cooldowns never block B");
world.setDynamicProperty("joki:pvp", true);
B.location = { x: 1.5, y: 64, z: 0 };
B.__vel = { x: 0, y: 0, z: 0 };
await reset(A);
B.location = { x: 1.5, y: 64, z: 0 };
B.__hurt = [];
await cast(A, "Scald Burst");
expect(B.__hurt.length === 1, "with PvP enabled steam hurts players");
world.setDynamicProperty("joki:pvp", false);

// ------------------------------------------------------------------ 14. melee enhancement
await reset(A);
await menu(A, "Gear: PRESSURE");
z1 = zombie(0, 1.5);
world.afterEvents.entityHitEntity.fire({ damagingEntity: A, hitEntity: z1 });
expect(z1.__vel.z > 1, "PRESSURE melee adds a steam shove");
expect(A.getEffect("strength")?.amplifier === 1, "PRESSURE melee strength II");

// ------------------------------------------------------------------ 15. touch: tapping a block with the valve
await reset(A);
await cast(A, "Pressure Dash"); // select dash
await tick(40);
A.location = { x: 0, y: 64, z: 0 };
A.__vel = { x: 0, y: 0, z: 0 };
world.afterEvents.playerInteractWithBlock.fire({ player: A, beforeItemStack: new ItemStack(VALVE), isFirstEvent: true, block: {} });
await tick(20);
expect(A.location.z > 4, "tapping a block with the valve casts the selected ability (touch)");

// ------------------------------------------------------------------ 16. death and respawn
await reset(A);
await menu(A, "Gear: PRESSURE");
await cast(A, "Steam Cannon");
A.applyDamage(999, { cause: "override" });
await tick(2);
expect(prop(A, "joki:mode") === 1 && owner(A), "death vents the boiler but keeps the power");
for (let i = 0; i < A.__inv.size; i++) if (A.__inv.slots[i]?.typeId === VALVE) A.__inv.slots[i] = undefined;
world.afterEvents.playerSpawn.fire({ player: A, initialSpawn: false });
await tick(25);
expect(valves(A) === 1, "respawn hands back a lost valve");
holdValve(A);

// ------------------------------------------------------------------ 17. leave / rejoin (world reload)
const savedDyn = new Map(A.__dyn);
const savedId = A.id;
world.beforeEvents.playerLeave.fire({ player: A });
A.remove();
await tick(2);
const A2 = new Player("Steamer", dim, { x: 0, y: 64, z: 0 });
world.__entities.delete(A2.id);
A2.id = savedId;
world.__entities.set(A2.id, A2);
A2.__dyn = savedDyn;
A2.__inv.addItem(new ItemStack(VALVE));
holdValve(A2);
world.afterEvents.playerSpawn.fire({ player: A2, initialSpawn: true });
await tick(25);
expect(owner(A2) && prop(A2, "joki:mode") === 1, "ownership survives leaving and rejoining");
expect(valves(A2) === 1, "no extra valve on rejoin");
await cast(A2, "Steam Boost");
expect(prop(A2, "joki:mode") === 2, "abilities work after rejoin");

// ------------------------------------------------------------------ 18. HUD toggle, guide, commands
await menu(A2, "Ability HUD");
expect(A2.getDynamicProperty("joki:hud") === false, "HUD can be turned off (persisted)");
await menu(A2, "Ability HUD");
__ui.queue.push("Power Guide", 0, undefined);
A2.setRotation({ x: 85, y: 0 });
A2.isSneaking = true;
useItem(A2, VALVE);
A2.isSneaking = false;
A2.setRotation({ x: 0, y: 0 });
await tick(8);
expect(__ui.shown.some((f) => f.title.includes("Steam Pressure Guide") && f.body.includes("Steam Knuckle")), "guide lists every ability");
__ui.queue.length = 0;
runCmd("joki:valve", B);
await tick(2);
expect(B.messages.some((m) => m.includes("already carry")), "/joki:valve does not duplicate");

// ------------------------------------------------------------------ 19. performance: redline + running for 5s
await reset(A2);
await cast(A2, "Redline");
await tick(20);
const p0 = __stats.particles;
const t0 = system.currentTick;
for (let i = 0; i < 100; i++) {
  A2.__vel = { x: 0, y: A2.__vel.y, z: 0.4 };
  await tick(1);
}
const perTick = (__stats.particles - p0) / (system.currentTick - t0);
report.redlineRunningServerParticlesPerTick = +perTick.toFixed(2);
expect(perTick < 3, `server particle rate while running in REDLINE is low (${perTick.toFixed(2)}/tick)`);
const peakTick = Math.max(...__stats.particlesByTick.values());
report.peakServerParticleCallsInOneTick = peakTick;
expect(peakTick <= 40, `no particle storms (peak ${peakTick} calls in one tick)`);
await tick(400);
expect(taskCount() === 0, `all multi-tick tasks finish (${taskCount()} left)`);

// ------------------------------------------------------------------ 20. revoke
runCmd("joki:revoke", A2);
await tick(2);
expect(!owner(A2) && prop(A2, "joki:mode") === 0, "revoke removes the power and clears the glow");
await use(A2);
expect(prop(A2, "joki:mode") === 0, "revoked players cannot cast");

// ------------------------------------------------------------------ config sanity
for (const id of config.ABILITY_ORDER) {
  const a = config.ABILITIES[id];
  expect(a.heat > 0 && a.cooldown > 0 && a.name && a.short.length === 3, `ability ${id} config`);
}
expect(config.ABILITIES.boost.heat === 15 && config.ABILITIES.dash.heat === 12 && config.ABILITIES.jump.heat === 14 && config.ABILITIES.cannon.heat === 16 &&
  config.ABILITIES.scald.heat === 25 && config.ABILITIES.knuckle.heat === 10 && config.ABILITIES.kick.heat === 12 && config.ABILITIES.mist.heat === 16, "heat table matches the spec");
expect(config.HEAT.lockout === 200 && config.TUNING.redline.duration === 240 && config.TUNING.boost.duration === 160, "timings match the spec");

// ------------------------------------------------------------------ result
expect(__issues.length === 0, `mock API issues:\n  ${[...new Set(__issues)].join("\n  ")}`);
expect(warnings.length === 0, `script warnings:\n  ${[...new Set(warnings)].join("\n  ")}`);
console.log = realLog;
console.log(`${passed} assertions passed, ${failures.length} failed`);
console.log("movement/perf:", JSON.stringify(report));
for (const f of failures) console.log("  FAIL:", f);
fs.rmSync(tmp, { recursive: true, force: true });
process.exit(failures.length ? 1 : 0);
