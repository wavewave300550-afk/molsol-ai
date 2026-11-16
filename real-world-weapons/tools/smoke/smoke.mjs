// Runtime smoke test: loads the compiled behaviour-pack script against a strict mock of
// @minecraft/server and exercises every weapon, every rule and the animation lifecycle.
//     node tools/smoke/smoke.mjs        (after `python3 tools/build.py`)
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const BP = path.join(ROOT, "build", "RWW_BP");
const RP = path.join(ROOT, "build", "RWW_RP");
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));

// ------------------------------------------------------------------ test data from the built packs
const ref = JSON.parse(fs.readFileSync(path.join(ROOT, "tools", "vanilla_refs.json"), "utf8"));
const items = {};
for (const f of walk(path.join(BP, "items"))) {
  const it = JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:item"];
  const c = it.components;
  items[it.description.identifier] = { params: c["rww:weapon"], cooldown: c["minecraft:cooldown"], tags: c["minecraft:tags"].tags, damage: c["minecraft:damage"].value };
}
const animations = Object.keys(JSON.parse(fs.readFileSync(path.join(RP, "animations", "rww_player.animation.json"), "utf8")).animations);
const sounds = [...ref.sound_events, ...Object.keys(JSON.parse(fs.readFileSync(path.join(RP, "sounds", "sound_definitions.json"), "utf8")).sound_definitions)];
const mobs = {
  "minecraft:zombie": { health: 20 }, "minecraft:skeleton": { health: 20 }, "minecraft:villager_v2": { health: 20 },
  "minecraft:wolf": { health: 8, tameable: true }, "minecraft:iron_golem": { health: 100 }, "minecraft:armor_stand": { health: 6 },
};
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "rww-smoke-"));
const dataPath = path.join(tmp, "data.json");
fs.writeFileSync(dataPath, JSON.stringify({ items, animations, sounds, particles: ref.particles, mobs }));
process.env.RWW_MOCK_DATA = dataPath;

fs.cpSync(path.join(BP, "scripts"), path.join(tmp, "scripts"), { recursive: true });
fs.writeFileSync(path.join(tmp, "package.json"), JSON.stringify({ type: "module" }));
const dir = path.join(tmp, "node_modules", "@minecraft", "server");
fs.mkdirSync(dir, { recursive: true });
fs.copyFileSync(path.join(HERE, "mock-server.mjs"), path.join(dir, "index.mjs"));
fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({ name: "@minecraft/server", type: "module", exports: "./index.mjs" }));
const mc = await import(pathToFileURL(path.join(dir, "index.mjs")).href);
const { world, system, Player, Entity, ItemStack, __tick, __issues, __log, __dims, __remove } = mc;

let passed = 0;
const failures = [];
function ok(cond, msg) {
  if (cond) passed++;
  else failures.push(msg);
}

// ------------------------------------------------------------------ boot the add-on
const registered = {};
await import(pathToFileURL(path.join(tmp, "scripts", "main.js")).href);
system.beforeEvents.startup.fire({
  itemComponentRegistry: { registerCustomComponent: (name, comp) => { registered[name] = comp; } },
  blockComponentRegistry: {}, customCommandRegistry: {}, dimensionRegistry: {}, worldClockRegistry: {},
});
ok(typeof registered["rww:weapon"]?.onHitEntity === "function", "custom component rww:weapon registered with onHitEntity");
ok(typeof registered["rww:weapon"]?.onBeforeDurabilityDamage === "function", "custom component has onBeforeDurabilityDamage");
const comp = registered["rww:weapon"];

const alice = new Player("Alice", { x: 0, y: 64, z: 0 });
const bob = new Player("Bob", { x: 3, y: 64, z: 0 });
world.afterEvents.playerSpawn.fire({ player: alice, initialSpawn: true });
world.afterEvents.playerSpawn.fire({ player: bob, initialSpawn: true });
__tick(5);

const anims = (since) => __log.animations.slice(since);
function equip(p, id) {
  p.mainhand = id ? new ItemStack(id) : undefined;
}
function hurt(attacker, target, damage = 6, cause = "entityAttack") {
  world.__hurt(target, damage, { cause, damagingEntity: attacker });
  return __log.lastHurt.damage;
}

// ------------------------------------------------------------------ 1. every item equips with its animations
for (const id of Object.keys(items)) {
  const n = __log.animations.length;
  equip(alice, id);
  __tick(6);
  const type = items[id].params.type;
  const a = anims(n);
  ok(a.some((x) => x.name === `animation.rww.${type}.arms` && x.opts.controller === "controller.animation.rww.arms"), `${id}: arms animation started`);
  ok(a.some((x) => x.name === `animation.rww.${type}.body` && x.opts.controller === "controller.animation.rww.body"), `${id}: body animation started`);
  ok(a.every((x) => x.opts.stopExpression?.includes(`'rww:${type}'`)), `${id}: stop expression targets rww:${type}`);
  equip(alice, undefined);
  __tick(4);
}
ok(Object.keys(items).length === 21, "21 items in the behaviour pack");

// ------------------------------------------------------------------ 2. rapier: long-measure thrust
equip(alice, "rww:iron_rapier");
__tick(6);
const zombie = new Entity("minecraft:zombie", { x: 0, y: 64, z: 3.0 });
ok(Math.abs(hurt(alice, zombie, 7) - 7 * 1.25) < 1e-9, "rapier: +25% at long measure (3.0 blocks)");
zombie.location.z = 1.4;
ok(hurt(alice, zombie, 7) === 7, "rapier: no bonus at close measure (1.4 blocks)");
zombie.location.z = 3.0;
ok(hurt(alice, zombie, 7, "projectile") === 7, "rapier: projectiles never get the thrust bonus");
__tick(2);
ok(__log.particles.some((p) => p.id === "minecraft:critical_hit_emitter"), "rapier: long-measure feedback particle");

// ------------------------------------------------------------------ 3. katana: iai draw-cut
equip(alice, undefined);
__tick(4);
equip(alice, "rww:iron_katana");
__tick(4);
ok(Math.abs(hurt(alice, zombie, 10) - 15) < 1e-9, "katana: iai draw-cut +50% right after drawing");
ok(hurt(alice, zombie, 10) === 10, "katana: only the first strike is an iai cut");
equip(alice, undefined); __tick(4); equip(alice, "rww:iron_katana"); __tick(4);
ok(hurt(alice, zombie, 10) === 10, "katana: iai needs 4 s to recharge");
equip(alice, undefined); __tick(90); equip(alice, "rww:iron_katana"); __tick(4);
ok(Math.abs(hurt(alice, zombie, 10) - 15) < 1e-9, "katana: iai available again after recharge");
equip(alice, undefined); __tick(90); equip(alice, "rww:iron_katana"); __tick(30);
ok(hurt(alice, zombie, 10) === 10, "katana: iai window closes 1 s after the draw");

// ------------------------------------------------------------------ 4. zweihander: heft, sweep, knock-back
__remove(zombie);   // the rapier / katana test dummy
equip(alice, undefined); __tick(4);
const cd0 = __log.cooldowns.length;
equip(alice, "rww:iron_zweihander");
__tick(4);
ok(__log.cooldowns.length === cd0 + 1 && __log.cooldowns.at(-1).item === "rww:iron_zweihander", "zweihander: attack cooldown starts when hefted");
alice.view = { x: 0, y: 0, z: 1 };
const primary = new Entity("minecraft:zombie", { x: 0, y: 64, z: 2.5 });
const side = new Entity("minecraft:skeleton", { x: 1.5, y: 64, z: 2.0 });       // ~37° off-axis, in reach
const behind = new Entity("minecraft:zombie", { x: 0, y: 64, z: -2.0 });
const villager = new Entity("minecraft:villager_v2", { x: -1.0, y: 64, z: 2.0 });
const pet = new Entity("minecraft:wolf", { x: 0.8, y: 64, z: 1.6 }, { tamed: true });
const stand = new Entity("minecraft:armor_stand", { x: -0.6, y: 64, z: 2.6 });
const far = new Entity("minecraft:zombie", { x: 0, y: 64, z: 6.0 });
bob.location = { x: -1.2, y: 64, z: 1.5 };                                       // other player in the arc, PvP off
const params = items["rww:iron_zweihander"].params;
const dmg0 = __log.damage.length;
const kb0 = __log.knockback.length;
comp.onHitEntity({ attackingEntity: alice, hitEntity: primary, hadEffect: true, itemStack: alice.mainhand }, { params });
comp.onHitEntity({ attackingEntity: alice, hitEntity: primary, hadEffect: true, itemStack: alice.mainhand }, { params });
__tick(1);
const swept = __log.damage.slice(dmg0);
ok(swept.length === 1 && swept[0].target === side.id, `zweihander: sweep hits only the hostile in the arc (hit ${swept.map((d) => d.typeId).join(",")})`);
ok(swept[0]?.amount === Math.round(params.damage * 0.5), "zweihander: sweep deals 50% of the weapon damage");
ok(swept[0]?.options?.cause === "entityAttack" && swept[0]?.options?.damagingEntity === alice, "zweihander: sweep damage is attributed to the player");
ok(__log.knockback.slice(kb0).some((k) => k.target === primary.id), "zweihander: heavier knock-back on the primary target");
ok(__log.sounds.some((s) => s.id === "rww.zweihander.sweep"), "zweihander: sweep sound");
world.gameRules.pvp = true;
const dmg1 = __log.damage.length;
__tick(1);
comp.onHitEntity({ attackingEntity: alice, hitEntity: primary, hadEffect: true, itemStack: alice.mainhand }, { params });
__tick(1);
ok(__log.damage.slice(dmg1).some((d) => d.target === bob.id), "zweihander: sweep includes other players only when PvP is on");
world.gameRules.pvp = false;
const dmg2 = __log.damage.length;
__tick(1);
comp.onHitEntity({ attackingEntity: alice, hitEntity: primary, hadEffect: false, itemStack: alice.mainhand }, { params });
__tick(1);
ok(__log.damage.length === dmg2, "zweihander: no sweep when the hit had no effect (target immune)");
// sweep damage must not receive rapier / katana bonuses
ok(swept.every((d) => d.amount === Math.round(params.damage * 0.5)), "zweihander: sweep damage is not modified by other rules");

// ------------------------------------------------------------------ 5. durability: once per swing
const d1 = { attackingEntity: alice, hitEntity: primary, durabilityDamage: 1 };
const d2 = { attackingEntity: alice, hitEntity: side, durabilityDamage: 1 };
__tick(1);
comp.onBeforeDurabilityDamage(d1, { params });
comp.onBeforeDurabilityDamage(d2, { params });
ok(d1.durabilityDamage === 1 && d2.durabilityDamage === 0, "durability: a piercing swing through several targets costs 1");
__tick(1);
const d3 = { attackingEntity: alice, hitEntity: primary, durabilityDamage: 1 };
comp.onBeforeDurabilityDamage(d3, { params });
ok(d3.durabilityDamage === 1, "durability: the next swing costs 1 again");

// ------------------------------------------------------------------ 6. animation lifecycle
// a player joining sees the holder's pose (targeted send)
const n6 = __log.animations.length;
const carol = new Player("Carol", { x: 2, y: 64, z: 2 });
world.afterEvents.playerSpawn.fire({ player: carol, initialSpawn: true });
__tick(3);
ok(anims(n6).some((a) => a.holder === "Alice" && a.opts.players?.length === 1 && a.opts.players[0] === carol), "lifecycle: a joining player receives existing weapon poses");
// a viewer coming back into range gets a targeted re-send
carol.location = { x: 200, y: 64, z: 0 };
__tick(41);
const n7 = __log.animations.length;
carol.location = { x: 20, y: 64, z: 0 };
__tick(41);
ok(anims(n7).some((a) => a.holder === "Alice" && a.opts.players?.[0] === carol), "lifecycle: re-sent to a viewer re-entering range");
// sleeping suppresses (client stop expression), waking re-broadcasts
alice.isSleeping = true; __tick(4);
const n8 = __log.animations.length;
alice.isSleeping = false; __tick(4);
ok(anims(n8).some((a) => a.holder === "Alice" && !a.opts.players), "lifecycle: re-broadcast after waking up");
// respawn re-broadcasts
const n9 = __log.animations.length;
world.afterEvents.playerSpawn.fire({ player: alice, initialSpawn: false });
__tick(4);
ok(anims(n9).some((a) => a.holder === "Alice" && a.name === "animation.rww.zweihander.arms"), "lifecycle: re-broadcast after respawn");
// dimension change
const n10 = __log.animations.length;
alice.dimension = __dims.nether;
world.afterEvents.playerDimensionChange.fire({ player: alice, fromDimension: __dims.overworld, toDimension: __dims.nether });
__tick(14);
ok(anims(n10).some((a) => a.holder === "Alice"), "lifecycle: re-broadcast after a dimension change");
// switching weapons starts the new weapon's animations, unequipping sends nothing
const n11 = __log.animations.length;
equip(alice, "rww:golden_katana"); __tick(4);
ok(anims(n11).some((a) => a.name === "animation.rww.katana.arms"), "lifecycle: switching weapons starts the new pose");
const n12 = __log.animations.length;
equip(alice, "minecraft:stick"); __tick(10);
ok(anims(n12).length === 0, "lifecycle: holding a vanilla item sends nothing (client stop expression ends the pose)");
// leaving cleans up without errors
world.beforeEvents.playerLeave.fire({ player: carol });
__remove(carol);
__tick(50);
ok(true, "lifecycle: player leave handled");

// ------------------------------------------------------------------ report
for (const i of __issues) failures.push(`mock: ${i}`);
console.log(`${passed} assertions passed, ${failures.length} failed`);
for (const f of failures) console.log("  FAIL:", f);
fs.rmSync(tmp, { recursive: true, force: true });
process.exit(failures.length ? 1 : 0);
