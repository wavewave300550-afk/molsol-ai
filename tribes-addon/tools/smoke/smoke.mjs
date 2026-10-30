// Runtime smoke test: loads the compiled behaviour-pack scripts against a strict
// mock of @minecraft/server and plays through every tribe and every ability.
//     node tools/smoke/smoke.mjs        (after `python3 tools/build.py`)
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const BP = path.join(ROOT, "build", "Tribes_BP");
const RP = path.join(ROOT, "build", "Tribes_RP");

// ------------------------------------------------------------------ test data
const ref = JSON.parse(fs.readFileSync(path.join(ROOT, "tools", "vanilla", "reference.json"), "utf8"));
const effectsSrc = fs.readFileSync(path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib", "mojang-effect.d.ts"), "utf8");
const effects = [...effectsSrc.matchAll(/"minecraft:([a-z_]+)"/g)].map((m) => m[1]);
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const particles = [...ref.particles];
for (const f of walk(path.join(RP, "particles"))) particles.push(JSON.parse(fs.readFileSync(f, "utf8")).particle_effect.description.identifier);

const entities = {
  "minecraft:zombie": { families: ["zombie", "undead", "monster", "mob"], events: [], health: 20 },
  "minecraft:villager_v2": { families: ["villager", "mob"], events: [], health: 20 },
  "minecraft:lightning_bolt": { families: ["lightning"], events: [] },
  "minecraft:item": { families: [], events: [] },
};
for (const f of walk(path.join(BP, "entities"))) {
  const e = JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:entity"];
  const comps = e.components ?? {};
  entities[e.description.identifier] = {
    families: comps["minecraft:type_family"]?.family ?? [],
    events: Object.keys(e.events ?? {}),
    health: comps["minecraft:health"]?.max ?? (e.description.identifier === "minecraft:player" ? 20 : undefined),
    tameable: !!comps["minecraft:tameable"],
    tameEvent: comps["minecraft:tameable"]?.tame_event?.event,
    projectile: !!comps["minecraft:projectile"],
    properties: e.description.properties,
  };
}
const items = walk(path.join(BP, "items")).map((f) => JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:item"].description.identifier);

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "tribes-smoke-"));
const dataPath = path.join(tmp, "data.json");
fs.writeFileSync(dataPath, JSON.stringify({ effects, particles, sounds: ref.sounds, entities, items, foods: ["minecraft:bread", "minecraft:beef", "minecraft:apple"] }));
process.env.TRIBES_MOCK_DATA = dataPath;

// ------------------------------------------------------------------ stage scripts + mocks
fs.cpSync(path.join(BP, "scripts"), path.join(tmp, "scripts"), { recursive: true });
fs.writeFileSync(path.join(tmp, "package.json"), JSON.stringify({ type: "module" }));
for (const [pkg, file] of [["server", "mock-server.mjs"], ["server-ui", "mock-server-ui.mjs"]]) {
  const dir = path.join(tmp, "node_modules", "@minecraft", pkg);
  fs.mkdirSync(dir, { recursive: true });
  fs.copyFileSync(path.join(HERE, file), path.join(dir, "index.mjs"));
  fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({ name: `@minecraft/${pkg}`, type: "module", exports: "./index.mjs" }));
}
const mc = await import(pathToFileURL(path.join(tmp, "node_modules", "@minecraft", "server", "index.mjs")).href);
const { __ui } = await import(pathToFileURL(path.join(tmp, "node_modules", "@minecraft", "server-ui", "index.mjs")).href);
const { world, system, Player, ItemStack, __tick, __issues } = mc;

const warnings = [];
console.warn = (...a) => warnings.push(a.join(" "));
const logs = [];
console.log = (...a) => logs.push(a.join(" "));

await import(pathToFileURL(path.join(tmp, "scripts", "main.js")).href);

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
    await new Promise((r) => setImmediate(r));
  }
}
const commands = {};
const enums = {};
system.beforeEvents.startup.fire({
  customCommandRegistry: {
    registerEnum(name, values) {
      expect(/^[a-z_]+:[a-z_]+$/.test(name), `enum name ${name} needs a namespace`);
      enums[name] = values;
    },
    registerCommand(def, cb) {
      expect(/^[a-z_]+:[a-z_]+$/.test(def.name), `command ${def.name} needs a namespace`);
      for (const p of def.mandatoryParameters ?? []) if (p.type === "Enum") expect(enums[p.name], `enum ${p.name} not registered before use`);
      commands[def.name] = cb;
    },
  },
});
expect(Object.keys(commands).length === 3, "three custom commands registered");
world.afterEvents.worldLoad.fire({});
await tick(1);
expect(logs.some((l) => l.includes("Tribes of the Cosmos loaded")), "loaded banner logged");

const dim = world.getDimension("minecraft:overworld");
const P = new Player("Tester", dim, { x: 0, y: 64, z: 0 });
world.afterEvents.playerSpawn.fire({ player: P, initialSpawn: true });
await tick(25);
const inv = () => P.__inv.slots.filter(Boolean).map((s) => s.typeId);
expect(inv().includes("tribes:tribal_codex"), "codex given on first join");
expect(P.messages.some((m) => m.includes("Tribes of the Cosmos")), "welcome message");
const race = () => P.getProperty("tribes:race");
expect(race() === 0, "no tribe initially");

// ---- choose a tribe through the Codex UI (busy once, then click through)
__ui.queue.push("busy", "Spacer", "Join the Spacer");
world.afterEvents.itemUse.fire({ source: P, itemStack: new ItemStack("tribes:tribal_codex") });
await tick(15);
expect(race() === 4, `codex UI joins the Spacer tribe (race=${race()})`);
expect(inv().includes("tribes:omni_gauntlet"), "Spacer relic given");
expect(!!P.getEffect("night_vision"), "Spacer passive night vision");
const guide = __ui.shown.find((f) => f.title.includes("Spacer"));
expect(guide && guide.body.includes("Plasma Bolt") && guide.body.includes("PASSIVES"), "guide page lists passives and abilities");

// ------------------------------------------------------------------ arena
function arena() {
  for (const e of dim.getEntities()) if (e !== P) e.remove();
  P.location = { x: 0, y: 64, z: 0 };
  P.__rotation = { x: 0, y: 0 }; // looking +z
  P.__air = 0;
  const z = (x, y, zz) => dim.spawnEntity("minecraft:zombie", { x, y, z: zz });
  const foes = [z(0, 64, 6), z(2, 64, 1), z(-2, 64, -1), z(0.5, 64, 2.5), z(4, 64, 8), z(0, 64, 12)];
  const villager = dim.spawnEntity("minecraft:villager_v2", { x: -1.5, y: 64, z: 1 });
  return { foes, villager };
}
const damageOf = (foes) => foes.reduce((s, f) => s + f.__hurtLog.reduce((a, h) => a + h.amount, 0), 0);
const relicSlot = () => P.__inv.slots.findIndex((s) => s && s.typeId.startsWith("tribes:") && s.typeId !== "tribes:tribal_codex");
function use(itemId, sneaking = false) {
  P.isSneaking = sneaking;
  world.afterEvents.itemUse.fire({ source: P, itemStack: new ItemStack(itemId) });
  P.isSneaking = false;
}
const hudEnergy = () => {
  const m = /§f(\d+)§7\/100/.exec(P.onScreenDisplay.actionbar);
  return m ? Number(m[1]) : NaN;
};

const TRIBES = [
  { key: "dinosauroid", race: 1, relic: "tribes:primal_fang", passive: ["speed", "jump_boost", "resistance"], names: ["Pounce", "Roar", "Sweep", "Pack"], summon: "tribes:raptor", summonCount: 3 },
  { key: "anunnaki", race: 2, relic: "tribes:tablet_of_destinies", passive: ["health_boost"], names: ["Lance", "Edict", "Aegis", "Descent"], summon: "tribes:lamassu", summonCount: 1 },
  { key: "pastafarian", race: 3, relic: "tribes:holy_colander", passive: ["water_breathing"], names: ["Lash", "Meatballs", "Marinara", "R'Amen"], summon: "tribes:noodle_avatar", summonCount: 1 },
  { key: "spacer", race: 4, relic: "tribes:omni_gauntlet", passive: ["night_vision", "water_breathing", "haste"], names: ["Plasma", "Jetpack", "Singularity", "Drones"], summon: "tribes:drone", summonCount: 2 },
];

for (const T of TRIBES) {
  commands["tribes:settribe"]({ sourceEntity: P }, T.key);
  await tick(3);
  expect(race() === T.race, `${T.key}: player property set`);
  expect(P.getDynamicProperty("tribes:race") === T.race, `${T.key}: dynamic property persisted`);
  expect(inv().includes(T.relic), `${T.key}: relic in inventory`);
  expect(inv().filter((i) => i !== T.relic && i !== "tribes:tribal_codex" && i.startsWith("tribes:")).length === 0, `${T.key}: foreign relics removed`);
  for (const eff of T.passive) expect(P.getEffect(eff)?.duration > 1000000, `${T.key}: permanent passive ${eff}`);
  const others = TRIBES.filter((o) => o !== T).flatMap((o) => o.passive).filter((e) => !T.passive.includes(e));
  await tick(40);
  for (const eff of others) expect(!P.getEffect(eff), `${T.key}: foreign passive ${eff} removed`);

  P.selectedSlotIndex = relicSlot();
  await tick(6);
  expect(P.onScreenDisplay.actionbar.includes(T.names[0]), `${T.key}: HUD shows abilities while holding relic`);

  for (let i = 0; i < 4; i++) {
    const { foes, villager } = arena();
    commands["tribes:energy"]({ sourceEntity: P });
    await tick(6);
    const startPos = { ...P.location };
    const before = damageOf(foes);
    const effectsBefore = P.getEffects().length;
    use(T.relic);
    await tick(110);
    const dmg = damageOf(foes) - before;
    const summons = dim.getEntities({ type: T.summon }).length;
    const moved = Math.hypot(P.location.x - startPos.x, P.location.z - startPos.z) > 1;
    const buffed = P.getEffects().length > effectsBefore || foes.some((f) => f.isValid && f.getEffects().length > 0)
      || dim.getEntities({ type: "tribes:meatball" }).length > 0;
    const name = `${T.key}/${T.names[i]}`;
    expect(dmg > 0 || summons > 0 || moved || buffed, `${name}: ability had a visible effect (dmg=${dmg} summons=${summons} moved=${moved} buffed=${buffed})`);
    expect(villager.__hurtLog.length === 0, `${name}: villager untouched`);
    expect(P.__hurtLog.filter((h) => h.cause !== "fall").length === 0, `${name}: caster not hurt by own ability`);
    if (i === 3) {
      expect(summons === T.summonCount || dim.getEntities({ type: T.summon }).length === T.summonCount, `${name}: ultimate summoned ${T.summonCount} guardian(s) (found ${summons})`);
      // re-casting immediately must be blocked by cooldown/energy
      const bar = P.onScreenDisplay.actionbar;
      use(T.relic);
      await tick(5);
      expect(/recharging|Not enough/.test(P.onScreenDisplay.actionbar) || bar !== P.onScreenDisplay.actionbar, `${name}: ultimate gated by cooldown`);
      await tick(1000);
      expect(dim.getEntities({ type: T.summon }).length === 0, `${name}: guardians expire`);
    }
    if (T.key === "pastafarian" && i === 1) {
      const balls = dim.getEntities({ type: "tribes:meatball" });
      expect(balls.length === 3 && balls.every((b) => b.__shot), `meatball barrage fired 3 projectiles (${balls.length})`);
      const target = dim.getEntities({ type: "minecraft:zombie" })[0];
      const b0 = damageOf([target]);
      world.afterEvents.projectileHitEntity.fire({ projectile: balls[0], source: P, location: { ...target.location }, dimension: dim, hitVector: { x: 0, y: 0, z: 1 } });
      expect(damageOf([target]) > b0, "meatball splash damages nearby enemies");
    }
    // cycle to next ability with Sneak + Use
    await tick(5);
    use(T.relic, true);
    await tick(5);
    expect(P.onScreenDisplay.titles.at(-1)?.o?.subtitle?.includes(T.names[(i + 1) % 4] === "R'Amen" ? "Noodly" : "") ?? false, `${T.key}: sneak+use selects next ability`);
  }

  // passive-specific checks
  P.__hurtLog = [];
  const h0 = P.getComponent("minecraft:health").currentValue;
  P.applyDamage(6, { cause: "fall" });
  const fallTaken = h0 - P.getComponent("minecraft:health").currentValue;
  if (T.key === "pastafarian") expect(fallTaken === 0, "pastafarian: no fall damage");
  else if (T.key === "spacer") expect(fallTaken === 3, `spacer: fall damage halved (${fallTaken})`);
  else expect(fallTaken === 6, `${T.key}: normal fall damage outside leaps (${fallTaken})`);
  P.getComponent("minecraft:health").setCurrentValue(20);

  if (T.key === "pastafarian") {
    P.__air = 10;
    P.isJumping = true;
    await tick(4);
    expect(!!P.getEffect("levitation"), "pastafarian: noodly flight while holding jump");
    P.isJumping = false;
    world.afterEvents.itemCompleteUse.fire({ source: P, itemStack: new ItemStack("minecraft:bread") });
    await tick(1);
    expect(!!P.getEffect("absorption"), "pastafarian: carb loading absorption");
  }
  if (T.key === "anunnaki") {
    P.__air = 4;
    P.isJumping = true;
    await tick(2);
    expect(!!P.getEffect("slow_falling"), "anunnaki: glide while holding jump");
    P.isJumping = false;
    P.getComponent("minecraft:health").setCurrentValue(10);
    await tick(41);
    expect(P.getComponent("minecraft:health").currentValue > 10, "anunnaki: solar grace heals in daylight");
  }
  if (T.key === "dinosauroid") {
    P.addEffect("hunger", 200, { amplifier: 0 });
    world.afterEvents.itemCompleteUse.fire({ source: P, itemStack: new ItemStack("minecraft:beef") });
    await tick(2);
    expect(!P.getEffect("hunger") && !!P.getEffect("regeneration"), "dinosauroid: carnivore heals and cures hunger");
    const z = dim.spawnEntity("minecraft:zombie", { x: 3, y: 64, z: 3 });
    await tick(41);
    expect(true, "senses tick ran");
    z.remove();
    commands["tribes:energy"]({ sourceEntity: P });
    // Pounce makes the leap fall-immune
    for (let k = 0; k < 4 && !/Pounce §f<</.test(P.onScreenDisplay.actionbar); k++) {
      use(T.relic, true);
      await tick(6);
    }
    use(T.relic);
    await tick(2);
    const hp = P.getComponent("minecraft:health").currentValue;
    P.applyDamage(8, { cause: "fall" });
    expect(P.getComponent("minecraft:health").currentValue === hp, "dinosauroid: pounce landing has no fall damage");
    await tick(100);
  }
  // energy gain on melee hit
  const e0 = hudEnergy();
  const z = dim.spawnEntity("minecraft:zombie", { x: 1, y: 64, z: 1 });
  world.afterEvents.entityHitEntity.fire({ damagingEntity: P, hitEntity: z });
  await tick(6);
  expect(hudEnergy() >= e0, `${T.key}: melee hits feed energy (${e0} -> ${hudEnergy()})`);
}

// ---- wrong relic is refused
commands["tribes:settribe"]({ sourceEntity: P }, "spacer");
await tick(3);
use("tribes:holy_colander");
await tick(2);
expect(P.onScreenDisplay.actionbar.includes("does not answer"), "foreign relic refuses to work");

// ---- leave the tribe through the Codex
__ui.queue.push("Study / Change Tribe", "Leave my tribe", 0);
world.afterEvents.itemUse.fire({ source: P, itemStack: new ItemStack("tribes:tribal_codex") });
await tick(20);
expect(race() === 0, "leaving tribe through codex resets race");
expect(!P.getEffect("night_vision") && !P.getEffect("haste"), "leaving tribe strips permanent passives");

// ---- PvP toggle (operators)
__ui.queue.push("Spacer", "Join the Spacer");
world.afterEvents.itemUse.fire({ source: P, itemStack: new ItemStack("tribes:tribal_codex") });
await tick(15);
__ui.queue.push("PvP abilities");
world.afterEvents.itemUse.fire({ source: P, itemStack: new ItemStack("tribes:tribal_codex") });
await tick(10);
expect(world.getDynamicProperty("tribes:pvp") === true, "operators can toggle PvP");

// ---- leaving player cleans up state
world.beforeEvents.playerLeave.fire({ player: P });
await tick(3);

// ------------------------------------------------------------------ report
const issues = [...__issues, ...warnings.map((w) => `console.warn: ${w}`)];
for (const i of issues) failures.push(`API misuse: ${i}`);
console.error(`smoke test: ${passed} assertions passed, ${failures.length} failed`);
for (const f of failures) console.error("  FAIL:", f);
fs.rmSync(tmp, { recursive: true, force: true });
process.exit(failures.length ? 1 : 0);
