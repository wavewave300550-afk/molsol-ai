// Runtime smoke test: loads the compiled behaviour-pack scripts against a strict mock of
// @minecraft/server and plays a complete two-player fight against The Wrong Hatch:
// intro -> phase I -> First Crack -> phase II -> Final Hatch (botched) -> phase III ->
// Final Hatch (nova) -> death + rewards, then the summoning ritual, items and reload.
//     node tools/smoke/smoke.mjs        (after `python3 tools/build.py`)
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

// deterministic run: seeded PRNG for every Math.random() in the add-on
let seed = Number(process.env.WH_SEED ?? 20261111) >>> 0;
Math.random = () => {
  seed = (seed + 0x6d2b79f5) >>> 0;
  let t = seed;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const BP = path.join(ROOT, "build", "WrongHatch_BP");
const RP = path.join(ROOT, "build", "WrongHatch_RP");

// ------------------------------------------------------------------ test data from the built packs
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const json = (f) => JSON.parse(fs.readFileSync(f, "utf8"));
const ref = json(path.join(ROOT, "tools", "vanilla", "reference.json"));
const effectsSrc = fs.readFileSync(path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib", "mojang-effect.d.ts"), "utf8");
const effects = [...effectsSrc.matchAll(/"minecraft:([a-z_]+)"/g)].map((m) => m[1]);
const particles = [...ref.particles];
for (const f of walk(path.join(RP, "particles"))) particles.push(json(f).particle_effect.description.identifier);
const sounds = [...ref.sounds, ...Object.keys(json(path.join(RP, "sounds", "sound_definitions.json")).sound_definitions)];
const entities = { "minecraft:player": { description: { identifier: "minecraft:player" }, components: { "minecraft:health": { value: 20, max: 20 } } }, "minecraft:item": { description: {} } };
for (const f of walk(path.join(BP, "entities"))) {
  const e = json(f)["minecraft:entity"];
  entities[e.description.identifier] = e;
}
const items = [];
const itemCooldowns = [];
for (const f of walk(path.join(BP, "items"))) {
  const it = json(f)["minecraft:item"];
  items.push(it.description.identifier);
  if (it.components["minecraft:cooldown"]) itemCooldowns.push(it.description.identifier);
}
items.push("minecraft:gold_ingot", "minecraft:egg");
const lootTables = walk(path.join(BP, "loot_tables")).map((f) => path.relative(path.join(BP, "loot_tables"), f).replace(/\\/g, "/").replace(/\.json$/, ""));

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "wh-smoke-"));
const dataPath = path.join(tmp, "data.json");
fs.writeFileSync(dataPath, JSON.stringify({ effects, particles, sounds, entities, items, itemCooldowns, lootTables }));
process.env.WH_MOCK_DATA = dataPath;

fs.cpSync(path.join(BP, "scripts"), path.join(tmp, "scripts"), { recursive: true });
fs.writeFileSync(path.join(tmp, "package.json"), JSON.stringify({ type: "module" }));
const pkgDir = path.join(tmp, "node_modules", "@minecraft", "server");
fs.mkdirSync(pkgDir, { recursive: true });
fs.copyFileSync(path.join(HERE, "mock-server.mjs"), path.join(pkgDir, "index.mjs"));
fs.writeFileSync(path.join(pkgDir, "package.json"), JSON.stringify({ name: "@minecraft/server", type: "module", exports: "./index.mjs" }));
const mc = await import(pathToFileURL(path.join(pkgDir, "index.mjs")).href);
const { world, system, Player, ItemStack, __tick, __issues, __log, __terrain } = mc;

const spec = fs.readFileSync(path.join(ROOT, "src", "generated", "spec.ts"), "utf8");
const actBlock = spec.slice(spec.indexOf("export const ACT = {"), spec.indexOf("} as const;"));
const ACT = Object.fromEntries([...actBlock.matchAll(/^ {2}([a-z_]+): (\d+),$/gm)].map((m) => [m[1], Number(m[2])]));
const NAME = Object.fromEntries(Object.entries(ACT).map(([k, v]) => [v, k]));

// ------------------------------------------------------------------ load the add-on
const commands = {};
await import(pathToFileURL(path.join(tmp, "scripts", "main.js")).href);
system.beforeEvents.startup.fire({
  customCommandRegistry: {
    registerEnum() {},
    registerCommand(def, cb) {
      if (!/^wh:[a-z_]+$/.test(def.name)) __issues.push(`bad command name ${def.name}`);
      commands[def.name] = cb;
    },
  },
});

const failures = [];
const check = (cond, msg) => {
  if (!cond) failures.push(msg);
  return cond;
};
const ow = world.getDimension("overworld");
// arena walls (rush can slam into them)
__terrain.walls.push({ x0: -26, x1: -25, y0: 0, y1: 6, z0: -26, z1: 26 }, { x0: 25, x1: 26, y0: 0, y1: 6, z0: -26, z1: 26 },
  { x0: -26, x1: 26, y0: 0, y1: 6, z0: -26, z1: -25 }, { x0: -26, x1: 26, y0: 0, y1: 6, z0: 25, z1: 26 });

const p1 = new Player("Alex", ow, { x: 0, y: 0, z: 9 });
const p2 = new Player("Steve", ow, { x: 3, y: 0, z: 11 });
for (const p of [p1, p2]) world.__entities.set(p.id, p);

// ------------------------------------------------------------------ spawn + intro
const boss = ow.spawnEntity("wh:wrong_hatch", { x: 0, y: 0, z: 0 });
await __tick(2);
const hp = () => boss.getComponent("minecraft:health");
check(hp().effectiveMax === 900, `2 players should scale health to 900 (got ${hp().effectiveMax})`);
const preIntro = hp().currentValue;
boss.applyDamage(50, { cause: "entityAttack", damagingEntity: p1 });
check(hp().currentValue === preIntro, "boss must be invulnerable during the intro");
await __tick(70);
check(__log.anims.includes(ACT.intro), "intro animation played");
check(String(boss.nameTag).includes("Phase I"), `boss bar name shows phase (got ${boss.nameTag})`);

// ------------------------------------------------------------------ fight driver
const seen = { 1: new Set(), 2: new Set(), 3: new Set() };
let phaseNow = () => boss.getProperty("wh:phase");
let lastLen = 0;
function collect() {
  for (let i = lastLen; i < __log.anims.length; i++) seen[phaseNow()]?.add(NAME[__log.anims[i]]);
  lastLen = __log.anims.length;
}
const fwd = () => {
  const y = (boss.rotation.y * Math.PI) / 180;
  return { x: -Math.sin(y), z: Math.cos(y) };
};
const rel = (b, f, side) => {
  const d = fwd();
  return { x: b.x + d.x * f - d.z * side, z: b.z + d.z * f + d.x * side };
};
const patterns = [
  (b) => [rel(b, 4, 0.5), rel(b, -5, 0.5)], // one in front, one behind (back scratch / sickle sweep)
  (b) => [rel(b, 3.5, -1), rel(b, -4.5, 1)],
  (b) => [{ x: b.x, z: b.z + 4 }, { x: b.x + 2, z: b.z + 5 }], // close in front-ish
  (b) => [{ x: b.x, z: b.z - 5 }, { x: b.x - 1, z: b.z - 6 }], // behind / around
  (b) => [{ x: b.x + 16, z: b.z }, { x: b.x - 18, z: b.z + 3 }], // far apart (ranged)
  (b) => [rel(b, 12, 0), rel(b, 9, 6)], // mid range in front (rush / beam / volley)
  (b) => [{ x: b.x + 1.5, z: b.z + 1.5 }, { x: b.x - 1.5, z: b.z + 1 }], // crowding
  (b) => [{ x: b.x + 9, z: b.z + 9 }, { x: b.x, z: b.z + 3 }], // mixed
];
const clampArena = (v) => Math.max(-22, Math.min(22, v));
async function fight(ticks, { keepAbove, burstEvery = 600, smashEggs = true, breakFortress = true } = {}) {
  let fortressBroken = 0;
  for (let t = 0; t < ticks; t++) {
    if (!boss.isValid) break;
    if (t % 50 === 0) {
      const pat = patterns[Math.floor(t / 50) % patterns.length](boss.location);
      [p1, p2].forEach((p, i) => {
        p.location = { x: clampArena(pat[i].x), y: 0, z: clampArena(pat[i].z) };
        // face the boss most of the time so Dawn Flash can blind someone
        const dx = boss.location.x - p.location.x, dz = boss.location.z - p.location.z;
        p.rotation = { x: 0, y: (Math.atan2(-dx, dz) * 180) / Math.PI + (i === 1 && t % 100 === 0 ? 180 : 0) };
      });
    }
    p1.__jumping = t % 9 < 3; // hop now and then (shockwave rings)
    if (t % 20 === 0) {
      boss.applyDamage(5, { cause: "entityAttack", damagingEntity: p1 });
      boss.applyDamage(4, { cause: "projectile", damagingEntity: p2 });
    }
    if (t % burstEvery === 300) for (let k = 0; k < 8; k++) boss.applyDamage(12, { cause: "entityAttack", damagingEntity: p1 });
    if (breakFortress && String(boss.nameTag).includes("Shell Fortress") && fortressBroken < 1 && t % 10 === 0) {
      for (let k = 0; k < 6; k++) boss.applyDamage(40, { cause: "entityAttack", damagingEntity: p2 });
      fortressBroken++;
    }
    if (t % 70 === 0) {
      // players clean up the brood now and then
      const chick = ow.getEntities({ type: "wh:wrong_chick", families: ["wrong_hatch_minion"] })[0];
      if (chick) chick.applyDamage(50, { cause: "entityAttack", damagingEntity: p2 });
    }
    if (smashEggs && t % 45 === 0) {
      const egg = ow.getEntities({ type: "wh:hatch_egg" })[0];
      if (egg) egg.applyDamage(50, { cause: "entityAttack", damagingEntity: p1 });
    }
    if (keepAbove !== undefined && hp().currentValue < hp().effectiveMax * (keepAbove + 0.04)) hp().setCurrentValue(hp().effectiveMax * (keepAbove + 0.2));
    await __tick(1);
    collect();
  }
}

// ------------------------------------------------------------------ phase I
await fight(3600, { keepAbove: 0.65 });
check(phaseNow() === 1, "still phase I during coverage");
// cross into phase II with one huge hit: must stop at the 65 % gate
boss.applyDamage(5000, { cause: "entityAttack", damagingEntity: p1 });
check(Math.abs(hp().currentValue / hp().effectiveMax - 0.65) < 0.01, `phase gate holds at 65 % (got ${(hp().currentValue / hp().effectiveMax).toFixed(3)})`);
await __tick(80);
collect();
check(phaseNow() === 2, "First Crack -> phase II");
check(seen[2].has("crow") || seen[1].has("crow"), "crow transition played");

// ------------------------------------------------------------------ phase II
await fight(7000, { keepAbove: 0.3, breakFortress: false });
// Final Hatch I: break every shell -> botched hatch
boss.applyDamage(5000, { cause: "entityAttack", damagingEntity: p1 });
await __tick(12);
collect();
const shells = ow.getEntities({ type: "wh:brood_shell" });
check(shells.length === 4, `Final Hatch spawns 3 + 1 brood shells for 2 players (got ${shells.length})`);
const preHp = hp().currentValue;
boss.applyDamage(100, { cause: "entityAttack", damagingEntity: p1 });
check(hp().currentValue === preHp, "boss is sealed during the Final Hatch");
for (const s of shells) s.applyDamage(500, { cause: "entityAttack", damagingEntity: p2 });
await __tick(10);
collect();
check(String(boss.nameTag).includes("EXPOSED"), `botched hatch exposes the boss (name: ${boss.nameTag})`);
const exposedBefore = hp().currentValue;
boss.applyDamage(10, { cause: "entityAttack", damagingEntity: p1 });
check(Math.abs(exposedBefore - hp().currentValue - 15) < 0.01, "exposed boss takes x1.5 damage");
await __tick(140);
collect();
check(phaseNow() === 3, "phase III after the first Final Hatch");

// ------------------------------------------------------------------ phase III
await fight(7000, { keepAbove: 0.1 });
// Final Hatch II: leave the shells alone -> Hatch Nova
const p1HpBefore = p1.__deaths ?? 0;
boss.applyDamage(5000, { cause: "entityAttack", damagingEntity: p1 });
await __tick(240);
collect();
check(seen[3].has("hatch_nova"), "Hatch Nova fired when shells survive");
check(__log.particles.get("wh:nova") > 0, "nova particles");
void p1HpBefore;
await __tick(40);
collect();

// ------------------------------------------------------------------ death
for (let i = 0; i < 40 && boss.isValid; i++) {
  boss.applyDamage(200, { cause: "entityAttack", damagingEntity: p1 });
  await __tick(1);
}
check(boss.isValid, "boss is kept alive for its death sequence");
check(hp().currentValue >= 1, "lethal damage leaves 1 HP for the death sequence");
await __tick(120);
collect();
check(!boss.isValid, "boss removed after the death sequence");
check(seen[3].has("death"), "death animation played");
check(__log.spawned.get("loot:entities/wrong_hatch") === 1, "loot table spawned once");
check(p1.__xp > 0 && p2.__xp > 0, "participants received experience");
check(ow.getEntities({ type: "wh:wrong_chick" }).length === 0, "brood despawned with the boss");
check(ow.getEntities({ type: "wh:hatch_egg" }).length === 0, "eggs cleared with the boss");

// ------------------------------------------------------------------ coverage report
const ABILITY_ANIMS = {
  peck: "peck", peck_combo: "peck (phase II+)", guillotine: "wing guillotine", guillotine_double: "double guillotine",
  back_scratch: "back scratch", sickle_sweep: "sickle sweep", broodquake: "broodquake", egg_mortar: "egg mortar",
  feather_volley: "feather volley", fortress_enter: "shell fortress", fortress_burst: "fortress burst", rotten_hatch: "rotten hatch",
  rush_windup: "rooster rush", rush_charge: "rush charge", beam_charge: "yolk beam", beam_fire: "beam fire", dawn_flash: "dawn flash",
  brood_call: "brood call", wing_hop: "wing hop", sky_rise: "sky drop", sky_hover: "sky hover", sky_dive: "sky dive",
  land_slam: "sky drop landing", molt_storm: "molt storm", molt_burst: "molt burst", final_hatch: "final hatch",
  hatch_nova: "hatch nova", stunned: "stun", crow: "crow", intro: "intro", death: "death",
};
const all = new Set([...seen[1], ...seen[2], ...seen[3], "intro"]);
const missing = Object.keys(ABILITY_ANIMS).filter((k) => !all.has(k));
check(missing.length === 0, `actions never used during the fight: ${missing.join(", ")}`);
const counts = {};
for (const a of __log.anims) counts[NAME[a]] = (counts[NAME[a]] ?? 0) + 1;
console.log("action starts:", Object.entries(counts).filter(([k]) => k !== "none").sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k}=${v}`).join(" "));
for (const [ph, set] of Object.entries(seen)) console.log(`phase ${ph}: ${[...set].filter(Boolean).sort().join(", ")}`);

// ------------------------------------------------------------------ eggs, darts, minions were really used
check((__log.spawned.get("wh:lobbed_egg") ?? 0) > 0, "eggs were lobbed");
check((__log.spawned.get("wh:hatch_egg") ?? 0) > 0, "eggs landed");
check((__log.spawned.get("wh:feather_dart") ?? 0) > 0, "feather darts flew");
check((__log.spawned.get("wh:wrong_chick") ?? 0) > 0, "chicks hatched");
const playerDamage = __log.damage.filter((d) => d.to === "minecraft:player");
check(playerDamage.length > 50, `the boss actually hurt players (${playerDamage.length} hits)`);
check(__log.damage.some((d) => d.to === "wh:hatch_egg"), "players smashed eggs");

// ------------------------------------------------------------------ summoning ritual
p1.__inv.setItem(0, new ItemStack("wh:suspicious_egg", 2));
world.afterEvents.playerInteractWithBlock.fire({ player: p1, block: ow.getBlock({ x: 4, y: -1, z: 4 }), blockFace: "Up", faceLocation: { x: 0.5, y: 1, z: 0.5 }, isFirstEvent: true, itemStack: p1.__inv.getItem(0) });
check(p1.__inv.getItem(0)?.amount === 1, "ritual consumed one Suspicious Egg");
await __tick(110);
const summoned = ow.getEntities({ type: "wh:wrong_hatch" });
check(summoned.length === 1, "ritual summoned the boss");
// second ritual next to a living boss is refused
world.afterEvents.playerInteractWithBlock.fire({ player: p1, block: ow.getBlock({ x: 6, y: -1, z: 6 }), blockFace: "Up", faceLocation: { x: 0.5, y: 1, z: 0.5 }, isFirstEvent: true, itemStack: p1.__inv.getItem(0) });
check(p1.__inv.getItem(0)?.amount === 1, "no second ritual near an active boss");
await __tick(30);
commands["wh:clear"]({ sourceEntity: p1 });
await __tick(3);
check(ow.getEntities({ type: "wh:wrong_hatch" }).length === 0, "/wh:clear removes bosses");

// ------------------------------------------------------------------ reload: controller re-attaches from dynamic properties
const animsBeforeReload = __log.anims.length;
const restored = ow.spawnEntity("wh:wrong_hatch", { x: 0, y: 0, z: 0 });
restored.setDynamicProperty("wh:init", true);
restored.setDynamicProperty("wh:phase", 2);
restored.setDynamicProperty("wh:hpScale", 2);
// pretend this entity came from a saved chunk: remove the queued spawn event by firing load first
world.afterEvents.entityLoad.fire({ entity: restored });
await __tick(3);
check(restored.getProperty("wh:phase") === 2, "restored boss keeps its phase visuals");
check(!__log.anims.slice(animsBeforeReload).includes(ACT.intro), "a reloaded boss does not replay its intro");
commands["wh:clear"]({ sourceEntity: p1 });
await __tick(3);

// ------------------------------------------------------------------ reward items
p1.__effects.clear();
world.afterEvents.itemCompleteUse.fire({ source: p1, itemStack: new ItemStack("wh:golden_yolk", 1), useDuration: 0 });
check(p1.getEffect("absorption") && p1.getEffect("regeneration"), "Golden Yolk grants absorption + regeneration");
p1.isSneaking = true;
p1.location = { x: 0, y: 0, z: 4 };
p1.rotation = { x: 4, y: 0 };
const dartsBefore = __log.spawned.get("wh:feather_dart") ?? 0;
world.afterEvents.itemUse.fire({ source: p1, itemStack: new ItemStack("wh:guillotine_pinion", 1) });
check((__log.spawned.get("wh:feather_dart") ?? 0) - dartsBefore === 5, "Guillotine Pinion fires a fan of 5 darts");
const dummy = ow.spawnEntity("wh:wrong_chick", { x: 0, y: 0.3, z: 14 });
await __tick(30);
check(__log.damage.some((d) => d.to === "wh:wrong_chick" && d.from === "minecraft:player"), "player feather darts hit mobs");
void dummy;
p1.isSneaking = false;
p1.__inv.setItem(0, new ItemStack("wh:hatch_core", 1));
world.afterEvents.itemUse.fire({ source: p1, itemStack: p1.__inv.getItem(0) });
await __tick(4);
const pet = ow.getEntities({ type: "wh:wrong_chick", families: ["wrong_hatch_pet"] })[0];
check(pet && pet.__owner === p1.id, "Hatch Core hatches a tamed companion");
check(p1.__inv.getItem(0) === undefined, "Hatch Core consumed");

// ------------------------------------------------------------------ result
const issues = [...__issues];
console.log(`ticks simulated: ${system.currentTick}`);
console.log(`player hits taken: ${playerDamage.length}, chicks: ${__log.spawned.get("wh:wrong_chick") ?? 0}, eggs: ${__log.spawned.get("wh:hatch_egg") ?? 0}, darts: ${__log.spawned.get("wh:feather_dart") ?? 0}`);
console.log(`distinct particles: ${__log.particles.size}, distinct sounds: ${__log.sounds.size}`);
if (issues.length || failures.length) {
  for (const i of issues) console.log("ISSUE:", i);
  for (const f of failures) console.log("FAIL:", f);
  console.log(`smoke test FAILED (${issues.length} API issues, ${failures.length} failed checks)`);
  process.exit(1);
}
console.log("smoke test passed: full fight, rewards, ritual, items and reload behave correctly");
