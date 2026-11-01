// Runs the compiled behavior-pack scripts against tools/smoke/mock-server.mjs and checks the
// basic attack and all four special skills end to end:  npm run smoke
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const ADDON = path.join(ROOT, "addon");
const SCRIPTS = path.join(ADDON, "behavior_packs", "grizzly_oath", "scripts");
process.env.GO_ADDON = ADDON;

// --- stage the compiled scripts next to a fake "@minecraft/server" package
const RUN = path.join(HERE, ".run");
fs.rmSync(RUN, { recursive: true, force: true });
fs.mkdirSync(path.join(RUN, "node_modules", "@minecraft", "server"), { recursive: true });
fs.writeFileSync(path.join(RUN, "package.json"), JSON.stringify({ type: "module" }));
fs.writeFileSync(path.join(RUN, "node_modules", "@minecraft", "server", "package.json"), JSON.stringify({ name: "@minecraft/server", type: "module", main: "index.js" }));
fs.writeFileSync(path.join(RUN, "node_modules", "@minecraft", "server", "index.js"), `export * from ${JSON.stringify(pathToFileURL(path.join(HERE, "mock-server.mjs")).href)};`);
for (const f of fs.readdirSync(SCRIPTS)) fs.copyFileSync(path.join(SCRIPTS, f), path.join(RUN, f));

const M = await import(pathToFileURL(path.join(RUN, "node_modules", "@minecraft", "server", "index.js")).href);
await import(pathToFileURL(path.join(RUN, "main.js")).href);

let pass = 0;
let fail = 0;
function check(cond, msg) {
  if (cond) pass++;
  else {
    fail++;
    console.log("  FAIL:", msg);
  }
}
const section = (name) => console.log(`- ${name}`);
const L = M.__log;
const dim = M.__dims.overworld;
const tick = (n = 1) => M.__tick(n);
const since = (list, t0) => list.filter((e) => e.tick >= t0);
const dmgTo = (e, t0 = 0) => since(L.damage, t0).filter((d) => d.target === e);
const dotFwd = (p, origin, dir) => (p.x - origin.x) * dir.x + (p.y - origin.y) * dir.y + (p.z - origin.z) * dir.z;

const AXE = "grizzly_oath:grizzlys_oath";
const AWAKE = "grizzly_oath:grizzlys_oath_awakened";
const mob = (type, x, z, opts = {}) => new M.Entity(type, { x, y: 64, z }, dim, { families: opts.families ?? ["monster", "mob"], ...opts });
const zombie = (x, z) => mob("minecraft:zombie", x, z, { families: ["zombie", "undead", "monster", "mob"] });
function clearMobs() {
  for (const e of [...dim.entities]) if (!(e instanceof M.Player)) e.remove();
  dim.solid.clear();
}
function reset(p, x = 0, z = 0, view = { x: 0, y: 0, z: 1 }, yaw = 0) {
  p.location = { x, y: 64, z };
  p.view = view;
  p.yaw = yaw;
  p.isSneaking = false;
}
function use(p) {
  M.world.afterEvents.itemUse.fire({ source: p, itemStack: p.inventory.getItem(p.selectedSlotIndex) });
}
function select(p, index) {
  for (let guard = 0; guard < 8; guard++) {
    const bar = L.actionbar.filter((a) => a.player === p).at(-1)?.text ?? "";
    if (bar.includes(`${index + 1}. `) && !bar.includes("Skill §8»")) break;
    p.isSneaking = true;
    use(p);
    p.isSneaking = false;
    tick(8);
    if (p.getDynamicProperty("grizzly_oath:skill") === index) break;
  }
  check(p.getDynamicProperty("grizzly_oath:skill") === index, `skill ${index + 1} selected`);
  tick(40);
}

// ---------------------------------------------------------------- setup
const p = new M.Player("Hugh", { x: 0, y: 64, z: 0 }, dim);
const axe = new M.ItemStack(AXE, 1);
p.inventory.setItem(0, axe);
M.world.afterEvents.worldLoad.fire({});
tick(5);

section("HUD + hint");
{
  const bar = L.actionbar.filter((a) => a.player === p).at(-1);
  check(bar && bar.text.includes("1. Grizzly Rend") && bar.text.includes("READY"), "action bar shows selected skill 1 + READY");
  check(bar && /\[1:§aOK§f\]/.test(bar.text) && bar.text.includes("4:"), "action bar lists all four cooldown slots");
  check(L.messages.filter((m) => m.player === p).length === 1, "controls hint shown once");
  tick(20);
  check(L.messages.filter((m) => m.player === p).length === 1, "hint not repeated");
}

section("Frontier Cleave (basic attack)");
{
  reset(p);
  const t0 = M.__now();
  M.world.afterEvents.playerSwingStart.fire({ player: p, heldItemStack: axe, swingSource: "Attack" });
  M.world.afterEvents.playerSwingStart.fire({ player: p, heldItemStack: axe, swingSource: "Attack" });
  const anims = since(L.anims, t0).map((a) => a.name);
  check(anims[0] === "animation.grizzly_oath.player.cleave_r" && anims[1] === "animation.grizzly_oath.player.cleave_l", "alternates right / left heavy slash");
  const eye = p.getHeadLocation();
  const parts = since(L.particles, t0);
  check(parts.length >= 10 && parts.every((x) => dotFwd(x.loc, eye, p.view) > 0.5), "slash FX are in front of the player (aim direction)");
  check(since(L.sounds, t0).some((s) => s.id === "grizzly_oath.cleave_swing"), "swing sound");
  // aim west
  reset(p, 0, 0, { x: -1, y: 0, z: 0 }, 90);
  const t1 = M.__now() + 0.5;
  tick(1);
  M.world.afterEvents.playerSwingStart.fire({ player: p, heldItemStack: axe, swingSource: "Attack" });
  const west = L.particles.filter((x) => x.tick >= t1);
  check(west.length > 0 && west.every((x) => x.loc.x < p.location.x - 0.5), "slash FX follow the aim when looking west");
  const n = L.anims.length;
  M.world.afterEvents.playerSwingStart.fire({ player: p, heldItemStack: axe, swingSource: "Mine" });
  M.world.afterEvents.playerSwingStart.fire({ player: p, heldItemStack: new M.ItemStack("minecraft:stone"), swingSource: "Attack" });
  check(L.anims.length === n, "no cleave when mining or holding another item");
  const z = zombie(0, 2);
  tick(1);
  const t2 = M.__now();
  M.world.afterEvents.entityHitEntity.fire({ damagingEntity: p, hitEntity: z });
  check(since(L.sounds, t2).some((s) => s.id === "grizzly_oath.cleave_hit"), "impact sound on hit");
  check(since(L.particles, t2).some((x) => x.id === "grizzly_oath:spark"), "impact sparks on hit");
  check(L.anims.filter((a) => a.tick >= t2).length === 0, "basic attack does not cast a special skill");
  clearMobs();
}

section("Skill 1 - Grizzly Rend");
{
  reset(p);
  tick(10);
  const front = zombie(0, 6);
  const far = zombie(0, 15);
  const behind = zombie(0, -5);
  const side = zombie(6, 3);
  const villager = mob("minecraft:villager_v2", 0.8, 5, { families: ["villager", "mob"] });
  const t0 = M.__now();
  use(p);
  tick(10);
  check(dmgTo(front, t0).filter((d) => d.amount === 8).length === 1, "enemy in front hit once for 8");
  check(dmgTo(far, t0).length === 0, "nothing past ~12 blocks");
  check(dmgTo(behind, t0).length === 0 && dmgTo(side, t0).length === 0, "nothing behind or to the side");
  check(dmgTo(villager, t0).length === 0, "villagers are never hurt");
  check(since(L.anims, t0).some((a) => a.name === "animation.grizzly_oath.player.rend"), "rend animation");
  const streaks = since(L.particles, t0).filter((x) => x.id === "grizzly_oath:claw_streak");
  const xs = streaks.map((s) => s.loc.x);
  check(streaks.length >= 30, "three claw lines drawn");
  check(streaks.every((s) => s.loc.z > 0 && s.loc.z < 13.5), "claw lines travel forward up to ~12 blocks");
  check(Math.min(...xs) < -0.5 && Math.max(...xs) > 0.5, "three parallel lines (left / centre / right)");
  check(since(L.knockback, t0).some((k) => k.target === front && k.h.z > 0), "pushed along the claw direction");
  tick(70);
  const bleed = dmgTo(front, t0).filter((d) => d.cause === "magic");
  check(bleed.length === 3 && bleed.every((d) => d.amount === 2), `short bleed: 3 x 2 damage (got ${bleed.length})`);
  check(since(L.particles, t0).some((x) => x.id === "grizzly_oath:blood"), "bleeding particles");

  // cooldown 7 s
  clearMobs();
  const z2 = zombie(0, 5);
  const t1 = M.__now();
  use(p);
  tick(10);
  check(dmgTo(z2, t1).length === 0, "on cooldown: no second cast");
  check(L.actionbar.some((a) => a.tick >= t1 && a.text.includes("recharging")), "cooldown message");
  tick(140);
  const t2 = M.__now();
  use(p);
  tick(10);
  check(dmgTo(z2, t2).length === 1, "castable again after the 7 s cooldown");
  // walls stop the claws, aiming works in any direction
  clearMobs();
  tick(140);
  for (let x = -3; x <= 3; x++) for (let y = 64; y <= 66; y++) dim.solid.add(`${x},${y},3`);
  const hidden = zombie(0, 6);
  const t3 = M.__now();
  use(p);
  tick(10);
  check(dmgTo(hidden, t3).length === 0, "claws do not pass through walls");
  check(since(L.particles, t3).filter((x) => x.id === "grizzly_oath:claw_streak").every((s) => s.loc.z < 3.2), "claw FX stop at the wall");
  clearMobs();
  tick(140);
  reset(p, 0, 0, { x: -1, y: 0, z: 0 }, 90);
  const west = zombie(-6, 0);
  const t4 = M.__now();
  use(p);
  tick(10);
  check(dmgTo(west, t4).length === 1, "follows the aimed direction (west)");
  clearMobs();
}

section("Skill switching (Sneak + Use)");
{
  reset(p);
  tick(10);
  const t0 = M.__now();
  p.isSneaking = true;
  use(p);
  use(p); // same tap reported twice -> must count once
  p.isSneaking = false;
  check(p.getDynamicProperty("grizzly_oath:skill") === 1, "sneak + use selects the next skill (debounced)");
  check(since(L.sounds, t0).some((s) => s.id === "grizzly_oath.select"), "selection sound");
  check(since(L.actionbar, t0).some((a) => a.text.includes("Relentless Pursuit")), "selected skill shown on screen");
  check(since(L.damage, t0).length === 0 && since(L.anims, t0).length === 0, "switching does not cast");
  tick(10);
}

section("Skill 2 - Relentless Pursuit");
{
  reset(p);
  const target = zombie(0.5, 8.2);
  const bystander = zombie(3, 6);
  const t0 = M.__now();
  use(p);
  tick(3);
  check(p.location.z > 2 && p.location.z < 7, "mid-dash");
  tick(10);
  check(Math.abs(p.location.z - 7) < 0.05 && p.location.x === 0, `dashed ~7 blocks forward (z=${p.location.z.toFixed(2)})`);
  check(dmgTo(target, t0).some((d) => d.amount === 10), "heavy slam damage at the end of the dash");
  check(since(L.knockback, t0).some((k) => k.target === bystander), "shockwave pushes nearby enemies");
  check(since(L.particles, t0).some((x) => x.id === "grizzly_oath:ring") && since(L.particles, t0).some((x) => x.id === "grizzly_oath:smoke"), "red-black trail + shockwave ring");
  check(since(L.commands, t0).length === 1, "camera shake");
  clearMobs();
  tick(260);
  reset(p);
  for (let x = -2; x <= 2; x++) for (let y = 64; y <= 66; y++) dim.solid.add(`${x},${y},4`);
  use(p);
  tick(12);
  check(p.location.z < 3.7 && p.location.z > 2, `dash stops in front of a wall (z=${p.location.z.toFixed(2)})`);
  clearMobs();
  tick(250);
}

section("Skill 3 - Unbroken Will");
{
  select(p, 2);
  reset(p);
  p.health = 20;
  const t0 = M.__now();
  use(p);
  tick(1);
  const shade = L.spawned.find((s) => s.tick >= t0 && s.entity.typeId === "grizzly_oath:grizzly_shade")?.entity;
  check(!!shade && shade.location.z < -1, "grizzly shade appears behind the player");
  check(since(L.sounds, t0).some((s) => s.id === "grizzly_oath.roar"), "roar");
  check(since(L.anims, t0).some((a) => a.name === "animation.grizzly_oath.player.will"), "axe-raise animation");
  tick(70);
  check(shade && !shade.isValid, "shade removed after its animation");
  const fx = since(L.effects, t0).filter((e) => e.target === p && e.name === "resistance");
  check(fx.length >= 3 && fx.every((e) => e.amplifier === 0), "full HP: Resistance I pulses");
  p.health = 4;
  const t1 = M.__now();
  tick(40);
  const low = since(L.effects, t1).filter((e) => e.target === p && e.name === "resistance");
  check(low.length >= 1 && low[0].amplifier === 2, "low HP: Resistance III (stronger)");
  check(low.every((e) => e.amplifier >= 1), "tier re-evaluated every second as HP recovers");
  check(p.health > 4 + 4, `low HP heals faster (hp ${p.health})`);
  check(L.effects.filter((e) => e.target === p).every((e) => e.tick + e.duration <= t0 + 161), "buff never outlasts 8 s");
  tick(60);
  const t2 = M.__now();
  tick(40);
  check(since(L.effects, t2).filter((e) => e.target === p).length === 0, "buff over after 8 s");
  check(since(L.particles, t0).some((x) => x.id === "grizzly_oath:ember") && since(L.particles, t0).some((x) => x.id === "grizzly_oath:smoke"), "red-black aura");
  tick(400);
}

section("Skill 4 - Oath of the Grizzly (Ultimate)");
{
  select(p, 3);
  reset(p, 0, 0, { x: 0, y: 0, z: 1 }, 0);
  p.health = 20;
  const held = p.inventory.getItem(0);
  held.getComponent("minecraft:durability").damage = 123;
  held.getComponent("minecraft:enchantable").addEnchantments([{ type: "sharpness", level: 3 }]);
  held.nameTag = "Glass";
  const near = zombie(0, 3);
  const edge = zombie(0, 8.6);
  const out = zombie(0, 11);
  const villager = mob("minecraft:villager_v2", 2, 2, { families: ["villager", "mob"] });
  const pet = mob("minecraft:wolf", -2, 2, { families: ["wolf", "mob"], tamed: true });
  const t0 = M.__now();
  use(p);
  check(p.inventory.getItem(0).typeId === AWAKE, "axe awakens (glowing crimson variant) on cast");
  tick(5);
  const bear = L.spawned.find((s) => s.tick >= t0 && s.entity.typeId === "grizzly_oath:oath_grizzly")?.entity;
  check(!!bear && bear.location.z < -2.5 && bear.yaw === 0, "giant grizzly appears behind the player, facing forward");
  tick(17);
  check(since(L.sounds, t0).some((s) => s.id === "grizzly_oath.titan_roar"), "grizzly roars");
  check(dmgTo(near, t0).length === 0, "no damage before the slam");
  tick(18);
  const slamTick = t0 + 39;
  const dn = dmgTo(near, t0)[0];
  const de = dmgTo(edge, t0)[0];
  check(dn && dn.tick === slamTick && dn.amount >= 16, `near enemy takes heavy slam damage at the synced tick (${dn?.amount})`);
  check(de && de.amount >= 10 && de.amount < dn.amount, `edge of the 8-block wave takes less (${de?.amount})`);
  check(dmgTo(out, t0).length === 0, "outside 8 blocks: unharmed");
  check(dmgTo(villager, t0).length === 0 && dmgTo(pet, t0).length === 0 && dmgTo(p, t0).length === 0, "villager, tamed pet and caster unharmed");
  check(since(L.knockback, t0).some((k) => k.target === near && k.h.z > 0), "shockwave knocks enemies away");
  check(since(L.effects, t0).some((e) => e.target === near && e.name === "slowness"), "slowed by the impact");
  check(since(L.particles, t0).filter((x) => x.id === "grizzly_oath:ring").some((x) => x.vars["variable.radius"] === 8), "8-block shockwave ring");
  check(since(L.anims, t0).some((a) => a.name === "animation.grizzly_oath.player.ult"), "player raise + slam animation");
  tick(27);
  check(bear.isValid, "grizzly still present while its animation plays (until 3.2 s)");
  tick(1);
  check(!bear.isValid, "grizzly model removed exactly when its animation ends");
  check(dim.getEntities({ families: ["grizzly_oath_fx"] }).length === 0, "no visual entity left in the world");
  tick(5);
  const back = p.inventory.getItem(0);
  check(back.typeId === AXE, "axe returns to normal after the Ultimate");
  check(back.getComponent("minecraft:durability").damage === 123 && back.nameTag === "Glass" && back.getComponent("minecraft:enchantable").getEnchantments().length === 1, "durability, name and enchantments preserved");
  const t1 = M.__now();
  use(p);
  tick(5);
  check(!L.spawned.some((s) => s.tick >= t1), "60 s cooldown respected");
  clearMobs();
}

section("Safety, cleanup, interaction");
{
  // Interacting with a chest must open it, not cast. A plain block tap casts (touch screens).
  tick(1300);
  select(p, 0);
  reset(p);
  const z = zombie(0, 5);
  const chest = { typeId: "minecraft:chest", getComponent: (id) => (id === "minecraft:inventory" ? {} : undefined) };
  const stone = { typeId: "minecraft:stone", getComponent: () => undefined };
  const t0 = M.__now();
  M.world.beforeEvents.playerInteractWithBlock.fire({ player: p, itemStack: axe, block: chest, isFirstEvent: true });
  tick(10);
  check(dmgTo(z, t0).length === 0, "tapping a chest does not cast");
  M.world.beforeEvents.playerInteractWithBlock.fire({ player: p, itemStack: p.inventory.getItem(0), block: stone, isFirstEvent: true });
  tick(10);
  check(dmgTo(z, t0).length === 1, "tapping the ground casts (iPhone)");
  // other players only with PvP on
  clearMobs();
  tick(150);
  const other = new M.Player("Fitzgerald", { x: 0, y: 64, z: 5 }, dim);
  const t1 = M.__now();
  use(p);
  tick(10);
  check(dmgTo(other, t1).length === 0, "PvP off: other players unharmed");
  tick(150);
  M.world.gameRules.pvp = true;
  const t2 = M.__now();
  use(p);
  tick(10);
  check(dmgTo(other, t2).length === 1, "PvP on: other players can be hit");
  other.remove();
  M.world.gameRules.pvp = false;
  // orphans from an old session get cleaned up; leaving mid-skill cleans up too
  const orphan = dim.spawnEntity("grizzly_oath:oath_grizzly", { x: 5, y: 64, z: 5 });
  M.world.afterEvents.worldLoad.fire({});
  check(!orphan.isValid, "leftover grizzly from a previous session removed on load");
  tick(600);
  select(p, 2);
  use(p);
  tick(2);
  M.world.afterEvents.playerLeave.fire({ playerId: p.id, playerName: p.name });
  check(dim.getEntities({ families: ["grizzly_oath_fx"] }).length === 0, "visuals removed when the caster leaves");
  // an awakened axe outside the Ultimate is always restored
  p.inventory.setItem(3, new M.ItemStack(AWAKE));
  tick(25);
  check(p.inventory.getItem(3).typeId === AXE, "stray awakened axe restored");
}

const peak = Math.max(...L.perTick.values());
console.log(`\nparticles spawned: ${L.particles.length}, peak per tick: ${peak}`);
check(peak <= 120, `particle budget per tick (peak ${peak})`);
for (const i of M.__issues) {
  fail++;
  console.log("  API ISSUE:", i);
}
console.log(`\n${pass} passed, ${fail} failed`);
fs.rmSync(RUN, { recursive: true, force: true });
process.exit(fail ? 1 : 0);
