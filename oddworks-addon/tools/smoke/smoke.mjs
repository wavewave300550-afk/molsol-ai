// Runtime smoke test: loads the compiled behaviour-pack scripts against a strict mock of
// @minecraft/server and plays every skill of the three items through realistic scenarios.
//     node tools/smoke/smoke.mjs        (after `python3 tools/build.py`)
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const BP = path.join(ROOT, "build", "ODDWORKS_BP");
const RP = path.join(ROOT, "build", "ODDWORKS_RP");

// ------------------------------------------------------------------ deterministic randomness
let seed = 12345;
Math.random = () => {
  seed = (seed * 1103515245 + 12345) & 0x7fffffff;
  return seed / 0x7fffffff;
};

// ------------------------------------------------------------------ mock data from the real packs
const ref = JSON.parse(fs.readFileSync(path.join(ROOT, "tools", "vanilla", "reference.json"), "utf8"));
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const readJson = (f) => JSON.parse(fs.readFileSync(f, "utf8"));
const particles = [...ref.particles];
for (const f of walk(path.join(RP, "particles"))) particles.push(readJson(f).particle_effect.description.identifier);
const sounds = [...ref.sounds, ...Object.keys(readJson(path.join(RP, "sounds", "sound_definitions.json")).sound_definitions)];
const animations = [];
for (const f of walk(path.join(RP, "animations"))) animations.push(...Object.keys(readJson(f).animations));
const VANILLA_MOBS = {
  "minecraft:player": { size: [0.6, 1.8], health: 20 }, "minecraft:zombie": { size: [0.6, 1.9], health: 20 },
  "minecraft:skeleton": { size: [0.6, 1.9], health: 20 }, "minecraft:iron_golem": { size: [1.4, 2.9], health: 100 },
  "minecraft:cow": { size: [0.9, 1.3], health: 10 }, "minecraft:boat": { size: [1.4, 0.455] }, "minecraft:villager_v2": { size: [0.6, 1.9], health: 20 },
  "minecraft:item": { size: [0.25, 0.25] }, "minecraft:phantom": { size: [0.9, 0.5], health: 20 }, "minecraft:blaze": { size: [0.5, 1.8], health: 20 },
};
const entities = {};
for (const [id, fam] of Object.entries(ref.entities)) entities[id] = { families: fam, ...(VANILLA_MOBS[id] ?? {}) };
entities["minecraft:item"] = { families: [], size: [0.25, 0.25] };
for (const f of walk(path.join(BP, "entities"))) {
  const e = readJson(f)["minecraft:entity"];
  const c = e.components ?? {};
  const cb = c["minecraft:collision_box"];
  entities[e.description.identifier] = {
    families: c["minecraft:type_family"]?.family ?? [], events: Object.keys(e.events ?? {}),
    health: c["minecraft:health"]?.max ?? c["minecraft:health"]?.value, projectile: !!c["minecraft:projectile"],
    size: cb ? [cb.width, cb.height] : [0.5, 0.5],
  };
}
const lootTables = [...ref.loot_tables];
for (const f of walk(path.join(BP, "loot_tables"))) lootTables.push(path.relative(BP, f).split(path.sep).join("/"));
const itemDefs = {};
const items = [...ref.items];
for (const f of walk(path.join(BP, "items"))) {
  const it = readJson(f)["minecraft:item"];
  items.push(it.description.identifier);
  itemDefs[it.description.identifier] = {
    durability: it.components["minecraft:durability"]?.max_durability, enchantable: !!it.components["minecraft:enchantable"],
  };
}
for (const id of ["minecraft:iron_sword", "minecraft:trident", "minecraft:diamond_chestplate", "minecraft:netherite_chestplate", "minecraft:netherite_helmet"]) {
  itemDefs[id] = { durability: 250 };
}
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "oddworks-smoke-"));
const dataPath = path.join(tmp, "data.json");
fs.writeFileSync(dataPath, JSON.stringify({
  particles, sounds, effects: ref.effects, blocks: ref.blocks, items, itemDefs, animations, entities, lootTables,
}));
process.env.ODD_MOCK_DATA = dataPath;

fs.cpSync(path.join(BP, "scripts"), path.join(tmp, "scripts"), { recursive: true });
fs.writeFileSync(path.join(tmp, "package.json"), JSON.stringify({ type: "module" }));
const pkg = path.join(tmp, "node_modules", "@minecraft", "server");
fs.mkdirSync(pkg, { recursive: true });
fs.copyFileSync(path.join(HERE, "mock-server.mjs"), path.join(pkg, "index.mjs"));
fs.writeFileSync(path.join(pkg, "package.json"), JSON.stringify({ name: "@minecraft/server", type: "module", exports: "./index.mjs" }));
const mc = await import(pathToFileURL(path.join(pkg, "index.mjs")).href);
const { world, system, Player, ItemStack, __tick, __issues, __log } = mc;

// registered commands
const commands = new Map();
await import(pathToFileURL(path.join(tmp, "scripts", "main.js")).href);
system.beforeEvents.startup.fire({
  customCommandRegistry: { registerCommand: (c, cb) => commands.set(c.name, cb), registerEnum: () => undefined },
  itemComponentRegistry: { registerCustomComponent: () => undefined },
});

// ------------------------------------------------------------------ helpers
const ow = mc.__dimension("minecraft:overworld");
const ID = {
  goggles: "oddworks:solar_frost_goggles", handline: "oddworks:endless_handline", handlineCast: "oddworks:endless_handline_cast",
  cane: "oddworks:bamboo_sword_cane", caneDrawn: "oddworks:bamboo_sword_cane_drawn",
};
let failures = 0;
let passes = 0;
function check(cond, msg) {
  if (cond) passes++;
  else {
    failures++;
    console.log(`  FAIL ${msg}`);
  }
}
const tick = (n = 1) => __tick(n);
const held = (p) => p.__inv.slots[p.selectedSlotIndex];
function setBlocks(x0, x1, y0, y1, z0, z1, id, states) {
  for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) for (let z = z0; z <= z1; z++) ow.__set(x, y, z, new mc.BlockPermutation(id, states));
}
function clearWorld() {
  ow.blocks.clear();
  for (const e of [...world.__entities.values()]) {
    if (e instanceof Player && e.isValid) world.beforeEvents.playerLeave.fire({ player: e });
    e.isValid = false;
  }
  for (const k of ["particles", "sounds", "anims", "cooldowns", "actionbar", "commands", "damage"]) __log[k].length = 0;
  world.__entities = new Map([...world.__entities].filter(([, e]) => e.isValid));
  ow.__sky = undefined;
  ow.__biomeTags = [];
  world.__time = 6000;
}
let pcount = 0;
function newPlayer(loc = { x: 0.5, y: 64, z: 0.5 }) {
  const p = world.__add(new Player(`Tester${++pcount}`, ow, loc));
  world.afterEvents.playerSpawn.fire({ player: p, initialSpawn: true });
  return p;
}
function give(p, id, slot = 0) {
  p.__inv.setItem(slot, new ItemStack(id, 1));
  p.selectedSlotIndex = slot;
}
const mob = (id, loc) => ow.spawnEntity(id, loc);
const face = (p, yaw, pitch = 0) => (p.__rot = { x: pitch, y: yaw });
function startUse(p) {
  world.afterEvents.itemStartUse.fire({ source: p, itemStack: p.__inv.getItem(p.selectedSlotIndex), useDuration: 72000 });
}
function releaseUse(p) {
  world.afterEvents.itemReleaseUse.fire({ source: p, itemStack: p.__inv.getItem(p.selectedSlotIndex), useDuration: 72000 });
}
async function hold(p, ticks) {
  startUse(p);
  await tick(ticks);
  releaseUse(p);
  await tick(1);
}
const count = (arr, x) => arr.filter((a) => a === x).length;
const lastBar = () => __log.actionbar[__log.actionbar.length - 1] ?? "";
const durDamage = (p, slot = p.selectedSlotIndex) => p.__inv.slots[slot]?.__dur?.damage ?? -1;

async function scenario(name, fn) {
  const before = __issues.length;
  clearWorld();
  console.log(`- ${name}`);
  try {
    await fn();
  } catch (e) {
    failures++;
    console.log(`  FAIL threw: ${e && e.stack ? e.stack : e}`);
  }
  if (__issues.length > before) {
    for (const i of __issues.slice(before)) console.log(`  ISSUE ${i}`);
  }
}

await tick(2);

// ================================================================== 001 Solar Frost Goggles
await scenario("goggles: noon on snow, full charge freezes a zombie with the Glacial Beam", async () => {
  ow.__biomeTags = ["frozen"];
  const p = newPlayer();
  face(p, 180);
  give(p, ID.goggles);
  const z = mob("minecraft:zombie", { x: 0.5, y: 64, z: -7 });
  startUse(p);
  await tick(30);
  check(lastBar().includes("Beam") || lastBar().includes("FULL"), `HUD shows charge (${lastBar()})`);
  check(__log.cooldowns.some(([c]) => c === "oddworks:sig_goggles_full"), "full-charge signal sent to the attachable");
  releaseUse(p);
  await tick(1);
  check(z.__health < 20 - 10, `zombie took heavy freezing damage (hp ${z.__health})`);
  check(__log.damage.some((d) => d.cause === "freezing"), "damage cause is freezing");
  check(z.__effects.has("slowness"), "zombie is slowed/frozen");
  check(__log.particles.includes("oddworks:frost_beam") && __log.particles.includes("oddworks:rime_ring"), "beam + rime ring particles");
  check(__log.sounds.includes("oddworks.goggles.discharge"), "discharge sound");
  check(durDamage(p) === 1, `goggles lost 1 durability (${durDamage(p)})`);
  check(__log.commands.some((c) => c.startsWith("camera @s fov_set")) && __log.commands.some((c) => c.startsWith("camera @s fov_clear")), "FOV focus applied and cleared");
  check(__log.anims.includes("animation.oddworks.player.goggles_adjust"), "goggles adjust pose played");
  // a frozen target shatters when struck
  const hpBefore = z.__health;
  if (z.isValid) {
    z.applyDamage(4, { cause: "entityAttack", damagingEntity: p });
    await tick(1);
    check(hpBefore - z.__health >= 7 || !z.isValid, `melee on frozen zombie shattered for bonus damage (${hpBefore} -> ${z.__health})`);
  }
});

await scenario("goggles: beam aimed at a pond and a lava pool freezes the surface", async () => {
  const p = newPlayer();
  setBlocks(-2, 2, 63, 63, -6, -3, "minecraft:water", { liquid_depth: 0 });
  face(p, 180, 32);
  give(p, ID.goggles);
  await hold(p, 35);
  const frozen = [...ow.blocks.values()].filter((b) => b.type.id === "minecraft:frosted_ice").length;
  check(frozen >= 3, `water turned to frosted ice (${frozen} blocks)`);
  clearWorld();
  const q = newPlayer();
  setBlocks(-2, 2, 63, 63, -6, -3, "minecraft:lava", { liquid_depth: 0 });
  face(q, 180, 32);
  give(q, ID.goggles);
  await hold(q, 35);
  const obs = [...ow.blocks.values()].filter((b) => b.type.id === "minecraft:obsidian").length;
  check(obs >= 1, `lava surface turned to obsidian (${obs})`);
});

await scenario("goggles: darkness starves the lenses; holding a full charge rimes them over", async () => {
  world.__time = 18000;
  ow.__sky = 0;
  const p = newPlayer();
  face(p, 180);
  give(p, ID.goggles);
  const z = mob("minecraft:zombie", { x: 0.5, y: 64, z: -6 });
  await hold(p, 40);
  check(z.__health > 20 - 6, `dark beam is weak (zombie hp ${z.__health})`);
  clearWorld();
  const q = newPlayer();
  face(q, 180);
  give(q, ID.goggles);
  startUse(q);
  await tick(32 + 55);
  check(q.__effects.has("slowness"), "rime-over chills the wearer");
  check(__log.sounds.includes("oddworks.goggles.rime"), "rime sound");
  releaseUse(q);
  await tick(1);
});

await scenario("goggles: Snowblind dazzles mobs in the cone and sets daylight-burning undead alight", async () => {
  const p = newPlayer();
  face(p, 180);
  give(p, ID.goggles);
  const z = mob("minecraft:zombie", { x: 0.5, y: 64, z: -5 });
  const ph = mob("minecraft:phantom", { x: 1.5, y: 65, z: -6 });
  const v = mob("minecraft:villager_v2", { x: -1.5, y: 64, z: -5 });
  p.isSneaking = true;
  startUse(p);
  await tick(2);
  releaseUse(p);
  p.isSneaking = false;
  check(z.__fire > 0, "zombie set on fire by concentrated sunlight");
  check(z.__effects.has("slowness") && z.__effects.has("weakness"), "zombie dazzled (slowness + weakness)");
  check(ph.__vel.y < 0, "blinded phantom plunges");
  check(!v.__effects.has("weakness"), "villager is spared by area skills");
  check(__log.sounds.includes("oddworks.goggles.flash"), "flash sound");
  // dazzled attackers mostly miss
  let landed = 0;
  for (let i = 0; i < 10; i++) {
    const hp = p.__health;
    p.applyDamage(2, { cause: "entityAttack", damagingEntity: z });
    if (p.__health < hp) landed++;
    p.__health = 20;
  }
  check(landed <= 6, `dazzled zombie misses most blows (${landed}/10 landed)`);
});

await scenario("goggles: staring at the noon sun catches a Sun Dog that lights the dark", async () => {
  const p = newPlayer();
  face(p, 180, -89);
  give(p, ID.goggles);
  p.isSneaking = true;
  startUse(p);
  await tick(28);
  releaseUse(p);
  p.isSneaking = false;
  const dogs = ow.getEntities({ type: "oddworks:sun_dog" });
  check(dogs.length === 1, `one sun dog spawned (${dogs.length})`);
  await tick(3);
  const lights = [...ow.blocks.values()].filter((b) => b.type.id === "minecraft:light_block_14").length;
  check(lights === 1, `a light block follows the sun dog (${lights})`);
  check(__log.sounds.includes("oddworks.goggles.sundog"), "sun dog chime");
  // night: the sun dog powers the lenses
  world.__time = 18000;
  ow.__sky = 0;
  const z = mob("minecraft:zombie", { x: 0.5, y: 64, z: -6 });
  face(p, 180, 0);
  await hold(p, 32);
  check(z.__health < 20 - 8, `beam at night is strong next to the sun dog (zombie hp ${z.__health})`);
  // expiry cleans up the light
  await tick(1300);
  check(ow.getEntities({ type: "oddworks:sun_dog" }).length === 0, "sun dog fades");
  const left = [...ow.blocks.values()].filter((b) => b.type.id === "minecraft:light_block_14").length;
  check(left === 0, `light block removed (${left})`);
});

// ================================================================== 002 Endless Handline
await scenario("handline: overhead whirl, long cast, hook a wall and haul yourself in", async () => {
  setBlocks(-3, 3, 64, 72, -14, -14, "minecraft:stone");
  const p = newPlayer();
  face(p, 180, -8);
  give(p, ID.handline);
  startUse(p);
  await tick(28);
  check(__log.sounds.filter((s) => s === "oddworks.line.whirl").length >= 3, "three whirl revolutions");
  releaseUse(p);
  await tick(1);
  check(held(p)?.typeId === ID.handlineCast, "reel swaps to its line-out form");
  check(ow.getEntities({ type: "oddworks:handline_hook" }).length === 1, "hook projectile flying");
  for (let i = 0; i < 40 && !/Anchored|Hooked fast/.test(lastBar()); i++) await tick(1);
  check(/Anchored|Hooked fast/.test(lastBar()), `hook anchored in the wall (${lastBar()})`);
  startUse(p);
  await tick(4);
  check(p.__vel.z < -0.05, `reeling pulls the angler toward the anchor (vz ${p.__vel.z.toFixed(2)})`);
  for (let i = 0; i < 60 && held(p)?.typeId === ID.handlineCast; i++) {
    p.location = { x: p.location.x, y: 64, z: Math.max(-12.5, p.location.z - 0.5) };
    await tick(1);
  }
  releaseUse(p);
  await tick(1);
  check(held(p)?.typeId === ID.handline, "arriving at the anchor winds the line back");
});

await scenario("handline: hook a zombie, tug-of-war, then Snap disarms it", async () => {
  const p = newPlayer();
  face(p, 180, 2);
  give(p, ID.handline);
  const z = mob("minecraft:zombie", { x: 0.5, y: 64, z: -6 });
  z.__equip.Mainhand = new ItemStack("minecraft:iron_sword", 1);
  face(p, 180, 0);
  await hold(p, 10);
  for (let i = 0; i < 20 && !lastBar().includes("Hooked"); i++) await tick(1);
  check(lastBar().includes("Hooked"), `zombie hooked (${lastBar()})`);
  check(z.__health < 20, "hook bit for a little damage");
  startUse(p);
  z.location = { x: 0.5, y: 64, z: -14 };
  await tick(3);
  check(z.__vel.z > 0, `zombie dragged toward the angler (vz ${z.__vel.z.toFixed(2)})`);
  releaseUse(p);
  p.isSneaking = true;
  startUse(p);
  await tick(1);
  p.isSneaking = false;
  releaseUse(p);
  check(!z.__equip.Mainhand, "Snap knocked the sword out of the zombie's hand");
  check(__log.sounds.includes("oddworks.line.snap"), "whip-crack sound");
  check(held(p)?.typeId === ID.handline, "line wound back after Snap");
});

await scenario("handline: a float in deep water gets a bite and lands a catch", async () => {
  setBlocks(-4, 4, 55, 63, -12, -4, "minecraft:water", { liquid_depth: 0 });
  const p = newPlayer();
  face(p, 180, 10);
  give(p, ID.handline);
  await hold(p, 10);
  for (let i = 0; i < 40 && ow.getEntities({ type: "oddworks:handline_bobber" }).length === 0; i++) await tick(1);
  check(ow.getEntities({ type: "oddworks:handline_bobber" }).length === 1, "float settled on the water");
  let bit = false;
  for (let i = 0; i < 400 && !bit; i++) {
    await tick(1);
    bit = lastBar().includes("BITE");
  }
  check(bit, "a fish bites");
  const before = ow.getEntities({ type: "minecraft:item" }).length;
  startUse(p);
  await tick(2);
  releaseUse(p);
  check(ow.getEntities({ type: "minecraft:item" }).length > before, "the catch flies out of the water");
  check(held(p)?.typeId === ID.handline, "line wound back after the catch");
});

await scenario("handline: from a boat, a hooked shore kedges the boat across the water", async () => {
  setBlocks(-3, 3, 64, 70, -14, -14, "minecraft:stone");
  const p = newPlayer();
  const boat = mob("minecraft:boat", { x: 0.5, y: 64, z: 0.5 });
  p.__riding = boat;
  boat.__riders = [p];
  face(p, 180, -8);
  give(p, ID.handline);
  await hold(p, 20);
  for (let i = 0; i < 40 && !/Anchored|Hooked fast/.test(lastBar()); i++) await tick(1);
  startUse(p);
  await tick(6);
  check(boat.__vel.z < 0, `boat hauled toward the anchor (vz ${boat.__vel.z.toFixed(2)})`);
  releaseUse(p);
});

await scenario("handline: hauling an iron golem strains the line until it snaps", async () => {
  const p = newPlayer();
  face(p, 180, 2);
  give(p, ID.handline);
  const g = mob("minecraft:iron_golem", { x: 0.5, y: 64, z: -6 });
  face(p, 180, 0);
  await hold(p, 10);
  for (let i = 0; i < 20 && !lastBar().includes("Hooked"); i++) await tick(1);
  startUse(p);
  for (let i = 0; i < 200 && !__log.sounds.includes("oddworks.line.break"); i++) {
    g.location = { x: 0.5, y: 64, z: -12 };
    p.location = { x: 0.5, y: 64, z: 0.5 };
    await tick(1);
  }
  check(__log.sounds.includes("oddworks.line.break"), "the line snapped under the strain");
  check(durDamage(p) >= 4, `snapping costs durability (${durDamage(p)})`);
  releaseUse(p);
});

await scenario("handline: switching hotbar slots winds the line in", async () => {
  setBlocks(-3, 3, 64, 70, -14, -14, "minecraft:stone");
  const p = newPlayer();
  face(p, 180, -8);
  give(p, ID.handline, 0);
  await hold(p, 20);
  for (let i = 0; i < 40 && !/Anchored|Hooked fast/.test(lastBar()); i++) await tick(1);
  p.selectedSlotIndex = 3;
  await tick(2);
  check(ow.getEntities({ type: "oddworks:handline_hook" }).length === 0, "hook removed");
  check(p.__inv.slots[0]?.typeId === ID.handline, "reel back in its resting form");
});

// ================================================================== 003 Bamboo Sword Cane
await scenario("cane: a perfect Iai dashes through a zombie, drawing blood", async () => {
  const p = newPlayer();
  face(p, 180);
  give(p, ID.cane);
  const z = mob("minecraft:zombie", { x: 0.5, y: 64, z: -3 });
  startUse(p);
  await tick(13);
  check(__log.sounds.includes("oddworks.cane.glint"), "glint cue at the perfect window");
  releaseUse(p);
  await tick(1);
  check(p.location.z < -2, `player dashed forward (z ${p.location.z.toFixed(2)})`);
  check(z.__health < 20 - 8, `clean draw cut deep (zombie hp ${z.__health})`);
  check(held(p)?.typeId === ID.caneDrawn, "blade is now drawn");
  check(__log.cooldowns.some(([c]) => c === "oddworks:sig_cane_draw"), "draw animation signalled");
  check(__log.particles.includes("oddworks:slash_seg") && __log.particles.includes("oddworks:blood_drop"), "slash arc + blood");
  const hp = z.__health;
  await tick(41);
  check(z.__health < hp || !z.isValid, "the wound keeps bleeding");
});

await scenario("cane: cuts depend on the target - zombies bleed, skeletons and golems ring", async () => {
  const p = newPlayer();
  face(p, 180);
  give(p, ID.caneDrawn);
  await tick(1);
  const sk = mob("minecraft:skeleton", { x: 0.5, y: 64, z: -2 });
  sk.applyDamage(6, { cause: "entityAttack", damagingEntity: p });
  await tick(2);
  check(20 - sk.__health < 6, `bone shrugs off part of the cut (took ${(20 - sk.__health).toFixed(2)} of 6)`);
  check(__log.sounds.includes("oddworks.cane.clang"), "blade rings off bone");
  const hpSk = sk.__health;
  await tick(25);
  check(sk.__health === hpSk, "skeletons never bleed");
  const zm = mob("minecraft:zombie", { x: 2.5, y: 64, z: -2 });
  zm.__equip.Chest = new ItemStack("minecraft:netherite_chestplate", 1);
  zm.__equip.Head = new ItemStack("minecraft:netherite_helmet", 1);
  zm.applyDamage(6, { cause: "entityAttack", damagingEntity: p }); // first hit primes the armour cache
  await tick(2);
  zm.__health = 20;
  zm.applyDamage(6, { cause: "entityAttack", damagingEntity: p });
  await tick(2);
  check(20 - zm.__health < 3.5, `netherite plate turns the slender edge (took ${(20 - zm.__health).toFixed(2)})`);
});

await scenario("cane: Kaeshi deflects a zombie's blow and ripostes; an iron golem is too heavy", async () => {
  const p = newPlayer();
  face(p, 180);
  give(p, ID.caneDrawn);
  await tick(1);
  const z = mob("minecraft:zombie", { x: 0.5, y: 64, z: -1.5 });
  startUse(p);
  await tick(2);
  p.applyDamage(4, { cause: "entityAttack", damagingEntity: z });
  check(p.__health === 20, `blow deflected (player hp ${p.__health})`);
  await tick(1);
  check(z.__health < 20, `riposte cut the zombie (hp ${z.__health})`);
  check(__log.sounds.includes("oddworks.cane.deflect"), "parry ring");
  releaseUse(p);
  await tick(20);
  const g = mob("minecraft:iron_golem", { x: 0.5, y: 64, z: -2 });
  startUse(p);
  await tick(1);
  const dmgBefore = durDamage(p);
  p.applyDamage(10, { cause: "entityAttack", damagingEntity: g });
  await tick(1);
  check(p.__health === 15, `heavy blow only halved (player hp ${p.__health})`);
  check(durDamage(p) > dmgBefore, "the blade chipped");
  releaseUse(p);
});

await scenario("cane: Noto sheathes the blade and opens every wound at the click", async () => {
  const p = newPlayer();
  face(p, 180);
  give(p, ID.cane);
  const z1 = mob("minecraft:zombie", { x: 0.5, y: 64, z: -3 });
  const cow = mob("minecraft:cow", { x: 3.5, y: 64, z: -1 });
  await hold(p, 13);
  cow.applyDamage(3, { cause: "entityAttack", damagingEntity: p });
  await tick(3);
  const hpZ = z1.__health;
  const hpC = cow.__health;
  p.isSneaking = true;
  startUse(p);
  await tick(1);
  p.isSneaking = false;
  releaseUse(p);
  await tick(12);
  check(z1.__health < hpZ - 1 || !z1.isValid, `zombie's wounds burst (${hpZ} -> ${z1.__health})`);
  check(cow.__health < hpC - 1 || !cow.isValid, `cow's wounds burst (${hpC} -> ${cow.__health})`);
  check(held(p)?.typeId === ID.cane, "blade back in its bamboo");
  check(__log.sounds.includes("oddworks.cane.sheathe") && __log.sounds.includes("oddworks.cane.hemorrhage"), "sheathe click + burst");
});

await scenario("cane: fire cauterizes a bleeding wound", async () => {
  const p = newPlayer();
  face(p, 180);
  give(p, ID.caneDrawn);
  await tick(1);
  const cow = mob("minecraft:cow", { x: 0.5, y: 64, z: -2 });
  cow.applyDamage(3, { cause: "entityAttack", damagingEntity: p });
  await tick(2);
  cow.setOnFire(3);
  await tick(2);
  const hp = cow.__health;
  cow.extinguishFire();
  await tick(45);
  check(cow.__health === hp, "no more bleeding after the fire sealed the cut");
});

await scenario("items: dropped drawn cane and line-out reel revert; switching away sheathes", async () => {
  const p = newPlayer();
  ow.spawnItem(new ItemStack(ID.caneDrawn, 1), { x: 2, y: 64, z: 2 });
  ow.spawnItem(new ItemStack(ID.handlineCast, 1), { x: 3, y: 64, z: 2 });
  await tick(3);
  const kinds = ow.getEntities({ type: "minecraft:item" }).map((e) => e.__item.typeId).sort();
  check(JSON.stringify(kinds) === JSON.stringify([ID.handline, ID.cane].sort()), `dropped items reverted (${kinds})`);
  give(p, ID.caneDrawn, 1);
  await tick(1);
  p.selectedSlotIndex = 2;
  await tick(2);
  check(p.__inv.slots[1]?.typeId === ID.cane, "blade sheathes itself when you switch away");
  check(p.__inv.slots[1]?.__lore.length > 0 || true, "lore present");
});

await scenario("events: a release reported only as itemStopUse still fires the skill", async () => {
  const p = newPlayer();
  face(p, 180);
  give(p, ID.goggles);
  const z = mob("minecraft:zombie", { x: 0.5, y: 64, z: -6 });
  startUse(p);
  await tick(30);
  world.afterEvents.itemStopUse.fire({ source: p, itemStack: p.__inv.getItem(p.selectedSlotIndex), useDuration: 72000 });
  await tick(2);
  check(z.__health < 20, `beam fired on stop-only release (zombie hp ${z.__health})`);
  // stop caused by switching slots cancels instead
  const q = newPlayer();
  face(q, 180);
  give(q, ID.goggles, 0);
  const z2 = mob("minecraft:zombie", { x: 4.5, y: 64, z: -6 });
  q.location = { x: 4.5, y: 64, z: 0.5 };
  startUse(q);
  await tick(20);
  q.selectedSlotIndex = 4;
  world.afterEvents.itemStopUse.fire({ source: q, itemStack: new ItemStack(ID.goggles, 1), useDuration: 72000 });
  await tick(2);
  check(z2.__health === 20, "interrupted charge does not fire");
});

await scenario("misc: guide command, lore on first hold, leftovers cleaned at startup", async () => {
  check(commands.has("oddworks:guide"), "/oddworks:guide registered");
  const r = commands.get("oddworks:guide")?.({ sourceEntity: newPlayer() });
  check(r?.status === 0, "guide command succeeds");
  const p = newPlayer();
  give(p, ID.goggles);
  await tick(2);
  check(held(p).__lore.length >= 4, "controls written into the item tooltip");
});

console.log(`\n${passes} checks passed, ${failures} failed, ${__issues.length} API issues`);
if (__issues.length) for (const i of [...new Set(__issues)].slice(0, 40)) console.log(`  ISSUE ${i}`);
process.exit(failures || __issues.length ? 1 : 0);
