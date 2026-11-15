// End-to-end simulation of THE ANATOMY OF A WORLD / Boss 001 against the strict mock.
//   node tools/sim/run.mjs           (after python3 tools/build.py)
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const BP = path.join(ROOT, "build", "packs", "BP");
const RP = path.join(ROOT, "build", "packs", "RP");
const walk = (d) => (fs.existsSync(d) ? fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)])) : []);
const J = (f) => JSON.parse(fs.readFileSync(f, "utf8"));

// ------------------------------------------------------------------ reference data
const ref = J(path.join(ROOT, "tools", "vanilla", "reference.json"));
const blocks = J(path.join(ROOT, "tools", "vanilla", "blocks.json"));
const vd = (f) => fs.readFileSync(path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib", f), "utf8");
const effects = new Set([...vd("mojang-effect.d.ts").matchAll(/"minecraft:([a-z_]+)"/g)].map((m) => m[1]));
const vanillaItems = new Set([...vd("mojang-item.d.ts").matchAll(/"(minecraft:[a-z0-9_]+)"/g)].map((m) => m[1]));
const cameraPresets = new Set([...vd("mojang-cameraPresets.d.ts").matchAll(/"(minecraft:[a-z_]+)"/g)].map((m) => m[1]));
const entities = {};
for (const f of walk(path.join(BP, "entities"))) {
  const e = J(f)["minecraft:entity"];
  const c = e.components ?? {};
  entities[e.description.identifier] = { families: c["minecraft:type_family"]?.family ?? [], health: c["minecraft:health"]?.max, projectile: !!c["minecraft:projectile"], gravity: c["minecraft:projectile"]?.gravity, properties: e.description.properties ?? {} };
}
const BUILTIN = new Set(["particle_age", "particle_lifetime", "particle_random_1", "particle_random_2", "particle_random_3", "particle_random_4", "emitter_age", "emitter_lifetime", "emitter_random_1", "emitter_random_2", "emitter_random_3", "emitter_random_4"]);
const particles = {};
for (const f of walk(path.join(RP, "particles"))) {
  const p = J(f).particle_effect;
  const txt = JSON.stringify(p.components);
  const vars = [...new Set([...txt.matchAll(/\bv(?:ariable)?\.([a-z0-9_]+)/g)].map((m) => m[1]))].filter((v) => !BUILTIN.has(v)).map((v) => `variable.${v}`);
  particles[p.description.identifier] = { vars, optional: ["variable.intensity", "variable.gap"] };
}
const soundDefs = J(path.join(RP, "sounds", "sound_definitions.json")).sound_definitions;
const sounds = new Set([...Object.keys(soundDefs), ...ref.sounds]);
const music = new Set(Object.entries(soundDefs).filter(([, d]) => d.category === "music").map(([k]) => k));
const animations = new Set();
for (const f of walk(path.join(RP, "animations"))) for (const k of Object.keys(J(f).animations)) animations.add(k);
const animUsers = {};
for (const f of walk(path.join(RP, "entity"))) {
  const d = J(f)["minecraft:client_entity"].description;
  for (const a of Object.values(d.animations)) (animUsers[a] ??= []).push(d.identifier);
}
const fogs = new Set(walk(path.join(RP, "fogs")).map((f) => J(f)["minecraft:fog_settings"].description.identifier));
const items = new Set(walk(path.join(BP, "items")).map((f) => J(f)["minecraft:item"].description.identifier));
const dimensions = new Set(walk(path.join(BP, "dimensions")).map((f) => J(f)["minecraft:dimension"].description.identifier));
globalThis.__SIM_DATA = {
  blocks, effects, vanillaItems, cameraPresets, entities, particles, sounds, music, animations, animUsers, fogs, items, dimensions,
  vanillaParticles: new Set(ref.particles), vanillaEntities: new Set(["minecraft:item", "minecraft:xp_orb", "minecraft:player"]),
};

// ------------------------------------------------------------------ load scripts against the mocks
const SCR = path.join(ROOT, "build", "sim_scripts");
fs.rmSync(SCR, { recursive: true, force: true });
const mockUrl = pathToFileURL(path.join(HERE, "mock-server.mjs")).href;
const uiUrl = pathToFileURL(path.join(HERE, "mock-server-ui.mjs")).href;
for (const f of walk(path.join(BP, "scripts"))) {
  const out = path.join(SCR, path.relative(path.join(BP, "scripts"), f));
  fs.mkdirSync(path.dirname(out), { recursive: true });
  let src = fs.readFileSync(f, "utf8");
  src = src.replaceAll('"@minecraft/server"', JSON.stringify(mockUrl)).replaceAll('"@minecraft/server-ui"', JSON.stringify(uiUrl));
  fs.writeFileSync(out, src);
}
const mock = await import(mockUrl);
const t0 = Date.now();
await import(pathToFileURL(path.join(SCR, "main.js")).href);
const { manager } = await import(pathToFileURL(path.join(SCR, "core", "manager.js")).href);
const MMmod = await import(pathToFileURL(path.join(SCR, "gen", "mountain.js")).href);
const runtime = await import(pathToFileURL(path.join(SCR, "bosses", "migrating_mountain", "runtime.js")).href);
const MM = MMmod.MM;

// ------------------------------------------------------------------ harness helpers
let passed = 0;
const failures = [];
function check(cond, msg) {
  if (cond) passed++;
  else {
    failures.push(msg);
    console.log("  FAIL", msg);
  }
}
const log = (m) => console.log(`[t${mock.currentTick()}] ${m}`);
async function until(pred, max, label) {
  for (let i = 0; i < max; i++) {
    if (pred()) return true;
    if (process.env.SIM_DEBUG && i % 200 === 0 && manager.active) log(`  .. ${label}: ${manager.active.status()} | tasks: ${manager.active.tasks.tasks.filter((t) => !t.done).map((t) => t.name + "(w" + t.wait + ")").join(",")}`);
    await mock.advance(1);
  }
  check(false, `timeout waiting for ${label}`);
  return false;
}
const enc = () => manager.active;
const arena = () => mock.dimensionFor(MM.dimensionId);
const abilityTasks = () => enc()?.tasks?.count("mm:ability") ?? 0;

// command registries captured at startup
const reg = { commands: {}, enums: {}, items: {} };
mock.system.beforeEvents.startup.fire(
  {
    customCommandRegistry: {
      registerCommand: (c, cb) => {
        if (!/^[a-z0-9_]+:[a-z0-9_]+$/.test(c.name)) failures.push(`bad command name ${c.name}`);
        for (const p of [...(c.mandatoryParameters ?? []), ...(c.optionalParameters ?? [])]) if (p.type === "Enum" && !reg.enums[p.name]) failures.push(`command ${c.name} uses unregistered enum ${p.name}`);
        reg.commands[c.name] = { def: c, cb };
      },
      registerEnum: (n, v) => {
        if (!/^[a-z0-9_]+:[a-z0-9_]+$/.test(n)) failures.push(`bad enum name ${n}`);
        reg.enums[n] = v;
      },
    },
    itemComponentRegistry: { registerCustomComponent: (n, c) => (reg.items[n] = c) },
    blockComponentRegistry: { registerCustomComponent: () => undefined },
    dimensionRegistry: { registerCustomDimension: () => undefined },
    worldClockRegistry: {},
  },
  true,
);
check(reg.items["anatomy:atlas"]?.onUse && reg.items["anatomy:summoner"]?.onUse, "item custom components registered");
check(reg.commands["anatomy:boss"] && reg.commands["anatomy:ability"] && reg.commands["anatomy:atlas"], "custom commands registered");
mock.world.afterEvents.worldLoad.fire({});

// overworld floor
const ow = mock.dimensionFor("minecraft:overworld");
for (let x = -8; x <= 8; x++) for (let z = -8; z <= 8; z++) ow.setBlockPermutation({ x, y: 64, z }, mock.BlockPermutation.resolve("minecraft:stone"));
const alex = mock.addPlayer("Alex");
const sam = mock.addPlayer("Sam", { x: 3.5, y: 65, z: 0.5 });
for (const p of [alex, sam]) mock.world.afterEvents.playerSpawn.fire({ player: p, initialSpawn: true });
await mock.advance(60);
const hasItem = (p, id) => p.inventory.container.slots.some((s) => s?.typeId === id);
check(hasItem(alex, "anatomy:anatomical_atlas") && hasItem(sam, "anatomy:anatomical_atlas"), "players receive the Anatomical Atlas on first join");

function useItem(p, id) {
  const stack = p.inventory.container.slots.find((s) => s?.typeId === id) ?? new mock.ItemStack(id, 1);
  const comp = id === "anatomy:anatomical_atlas" ? reg.items["anatomy:atlas"] : reg.items["anatomy:summoner"];
  comp.onUse({ source: p, itemStack: stack }, { params: {} });
  mock.world.afterEvents.itemUse.fire({ source: p, itemStack: stack });
}

// ------------------------------------------------------------------ A. summon and intro
log("A. summoning");
alex.inventory.container.addItem(new mock.ItemStack("anatomy:restless_lodestone", 1));
useItem(alex, "anatomy:restless_lodestone");
await mock.advance(2);
check(!!enc(), "using the Restless Lodestone starts an encounter");
check(!hasItem(alex, "anatomy:restless_lodestone"), "the lodestone is consumed in survival");
const tStart = mock.currentTick();
await until(() => enc()?.state === "phase1", 3000, "phase 1");
log(`phase 1 after ${mock.currentTick() - tStart} ticks; ${arena().blocks.size} blocks in the arena`);
check(alex.dimension.id === MM.dimensionId && sam.dimension.id === MM.dimensionId, "party moved into the migration path dimension");
check(arena().blocks.size > 150000, `mountain built (${arena().blocks.size} blocks)`);
const ents = (t) => mock.allEntities().filter((e) => e.typeId === t && e.dimension === arena());
check(ents("anatomy:mm_root_leg").length === 14, "14 anchorage root legs");
check(ents("anatomy:mm_resonance_node").length === 3, "3 resonance nodes");
check(ents("anatomy:mm_lithic_heart").length === 1, "1 lithic heart");
check(ents("anatomy:mm_resonance_node").filter((e) => e.getProperty("anatomy:hanging")).length === 1, "the root node hangs");
check(new Set(ents("anatomy:mm_root_leg").map((e) => e.getProperty("anatomy:leg_index"))).size === 14, "legs have distinct gait indices");
// an entity is lit by the light level at its anchor: an anchor inside rock renders the whole model black
const buried = (types) => mock.allEntities().filter((e) => e.dimension === arena() && types.includes(e.typeId) && arena().isSolidAt(e.location.x, e.location.y, e.location.z));
check(buried(["anatomy:mm_root_leg", "anatomy:mm_resonance_node", "anatomy:mm_lithic_heart"]).length === 0, `every Phase 1 part is anchored in open air (buried: ${buried(["anatomy:mm_root_leg", "anatomy:mm_resonance_node", "anatomy:mm_lithic_heart"]).map((e) => e.typeId.slice(11) + "@" + Math.floor(e.location.y)).join(" ")})`);
check(ents("anatomy:mm_lithic_heart")[0]?.nameTag === "The Migrating Mountain", "the heart carries its boss bar name");
check(alex.fogStack.some((f) => f.id === "anatomy:migration_mist"), "migration mist fog pushed");
check(alex.music === "anatomy.music.mm_phase1", "phase 1 music playing");
check(alex.inputs[2] !== false && alex.cameraState === "default", "controls restored after the intro");
check(alex.titles.some((t) => t.includes("THE MIGRATING MOUNTAIN")), "title card shown");
const ar = MM.arrival;
check(Math.hypot(alex.location.x - ar.x, alex.location.z - ar.z) < ar.r + 2 && Math.abs(alex.location.y - (ar.y + 1)) < 1.5, "party stands on the arrival shelf");

// ------------------------------------------------------------------ B. phase 1 abilities
const m = runtime.mountain();
const surfaceAt = (x, z) => enc().terrain.topAt(Math.floor(x), Math.floor(z)) + 1.02;
function placeOnPath(p, idx) {
  const q = m.pathPoints[idx];
  p.teleport({ x: q.x, y: surfaceAt(q.x, q.z), z: q.z }, { dimension: arena() });
}
async function runAbility(id, label, max = 2400) {
  const before = { a: alex.health.currentValue, s: sam.health.currentValue };
  alex.health.currentValue = 20;
  sam.health.currentValue = 20;
  const ok = enc().forceAbility(id);
  check(ok, `${label}: ${id} can be forced`);
  await mock.advance(1);
  await until(() => abilityTasks() === 0 || !["phase1", "phase2"].includes(enc()?.state), max, `${label} ${id} to finish`);
  void before;
}
// keep the director from interfering while abilities are exercised one at a time
const quiet = () => enc().director.reset(mock.currentTick() + 999999 - mock.currentTick(), 999999);
quiet();
const mid = Math.floor(m.pathPoints.length * 0.45);
for (const id of ["continental_fold", "lithic_peristalsis", "inverted_strata", "geological_shedding"]) {
  placeOnPath(alex, mid);
  placeOnPath(sam, mid + 2);
  await mock.advance(5);
  const hpA = alex.health.currentValue + sam.health.currentValue;
  await runAbility(id, "P1");
  log(`P1 ${id}: done, party took ${(40 - (alex.health.currentValue + sam.health.currentValue)).toFixed(1)} dmg (from ${hpA})`);
}
// resonance at the summit node
const dorsal = m.nodes.find((n) => n.id === "dorsal");
alex.teleport({ x: dorsal.pos.x + 5, y: dorsal.pos.y + 0.1, z: dorsal.pos.z }, { dimension: arena() });
sam.teleport({ x: dorsal.pos.x - 5, y: dorsal.pos.y + 0.1, z: dorsal.pos.z }, { dimension: arena() });
await runAbility("resonance_network", "P1");
log(`P1 resonance_network done; Alex ${alex.health.currentValue.toFixed(1)} Sam ${sam.health.currentValue.toFixed(1)}`);
// contraction inside the cavern
const cv = MM.cavern;
alex.teleport({ x: cv.x - 14, y: cv.floorY + 1.02, z: cv.z + 2 }, { dimension: arena() });
sam.teleport({ x: cv.x + 4, y: cv.floorY + 1.02, z: cv.z - 12 }, { dimension: arena() });
await mock.advance(5);
check(enc().zoneOf(alex) === "cavern", "zone detection: cavern");
await runAbility("mantle_contraction", "P1");
log(`P1 mantle_contraction done; Alex ${alex.health.currentValue.toFixed(1)} Sam ${sam.health.currentValue.toFixed(1)}`);
// settle: terrain back to base, trees regrown, contraction relaxed
await mock.advance(500);
const t = enc().terrain;
let diff = 0;
for (let i = 0; i < t.cur.length; i++) if (t.cur[i] !== m.top[i]) diff++;
check(diff === 0, `terrain settles back to its base shape (${diff} columns differ)`);
let mismatch = 0;
let sampled = 0;
const g = MM.grid;
for (let i = 0; i < 4000; i++) {
  const x = g.x0 + Math.floor(Math.random() * g.sx);
  const z = g.z0 + Math.floor(Math.random() * g.sz);
  for (let y = g.y0; y < g.y0 + g.sy; y += 3) {
    const want = runtime.pristineBlock(x, y, z);
    const have = arena().getBlockId(x, y, z);
    const wantId = want >= 2 ? (await import(pathToFileURL(path.join(SCR, "gen", "palette.js")).href)).paletteEntries()[want].id : "minecraft:air";
    sampled++;
    if (wantId !== have) mismatch++;
  }
}
check(mismatch / sampled < 0.002, `world matches the pristine body after abilities (${mismatch}/${sampled} sampled cells differ)`);

// ------------------------------------------------------------------ C. destroy the nodes -> unfolding
log("C. destroying resonance nodes");
enc().director.reset(mock.currentTick(), 40); // let the boss fight back while we attack
for (const site of m.nodes) {
  const node = ents("anatomy:mm_resonance_node").find((e) => Math.hypot(e.location.x - site.pos.x, e.location.z - site.pos.z) < 1);
  check(!!node, `node ${site.id} present`);
  if (!node) continue;
  alex.teleport({ x: site.safe.x, y: site.safe.y + 0.05, z: site.safe.z }, { dimension: arena() });
  sam.teleport({ x: site.safe.x, y: site.safe.y + 0.05, z: site.safe.z }, { dimension: arena() });
  // the heart is shielded in phase 1
  const heart = ents("anatomy:mm_lithic_heart")[0];
  const hp0 = heart.health.currentValue;
  mock.playerAttack(alex, heart, 10);
  check(heart.health.currentValue === hp0, "the heart is shielded during phase 1");
  let hits = 0;
  while (node.isValid && !node.getProperty("anatomy:dying") && hits < 200) {
    mock.playerAttack(alex, node, 9);
    alex.health.currentValue = 20;
    sam.health.currentValue = 20;
    hits++;
    await mock.advance(8);
  }
  check(node.getProperty("anatomy:dying") === true, `node ${site.id} destroyed after ${hits} hits`);
  await mock.advance(40);
  check(!node.isValid, `node ${site.id} entity removed after its death animation`);
}
const heart = ents("anatomy:mm_lithic_heart")[0];
await until(() => enc()?.state === "unfolding", 400, "the great unfolding");
check(Math.abs(heart.health.currentValue - 1000 * (1 - 3 * 0.1333)) < 2, `heart health drops with each node (${heart.health.currentValue.toFixed(0)})`);
await mock.advance(45);
check(alex.cameraState === "minecraft:free", "cinematic camera during the unfolding");
check(alex.inputs[2] === false, "movement locked during the cinematic");
await until(() => enc()?.state === "phase2", 3000, "phase 2");
log(`phase 2 reached; petals ${ents("anatomy:mm_petal").length}`);
check(ents("anatomy:mm_petal").length === 12, "12 petals form the crown");
check(ents("anatomy:mm_petal").every((e) => e.getProperty("anatomy:petal_state") === 1), "petals unfolded");
check(buried(["anatomy:mm_petal", "anatomy:mm_root_leg", "anatomy:mm_lithic_heart"]).length === 0, `every Phase 2 part is anchored in open air (buried: ${buried(["anatomy:mm_petal", "anatomy:mm_root_leg", "anatomy:mm_lithic_heart"]).map((e) => e.typeId.slice(11) + "@" + Math.floor(e.location.y)).join(" ")})`);
check(ents("anatomy:mm_root_leg").every((e) => e.getProperty("anatomy:pose") === 1), "legs splay for phase 2");
check(heart.getProperty("anatomy:phase") === 2, "heart in phase 2");
const D = MM.disk;
let above = 0;
for (let i = 0; i < 3000; i++) {
  const x = g.x0 + Math.floor(Math.random() * g.sx);
  const z = g.z0 + Math.floor(Math.random() * g.sz);
  for (let y = D.y + 1; y < g.y0 + g.sy; y += 2) if (arena().getBlockId(x, y, z) !== "minecraft:air" && !arena().getBlockId(x, y, z).includes("water")) above++;
}
check(above < 40, `the shell above the cut is gone (${above} stray blocks sampled)`);
let walkCells = 0;
let walkOk = 0;
for (let r = 6; r < 33; r += 1)
  for (let a = 0; a < 360; a += 7) {
    const x = Math.floor(MM.heart.x + Math.cos((a * Math.PI) / 180) * r);
    const z = Math.floor(MM.heart.z + Math.sin((a * Math.PI) / 180) * r);
    if (!enc().isWalkway(x, z)) continue;
    walkCells++;
    if (arena().getBlockId(x, D.y, z) !== "minecraft:air") walkOk++;
  }
check(walkCells > 100 && walkOk / walkCells > 0.97, `phase 2 disk walkways placed (${walkOk}/${walkCells})`);
check(Math.abs(alex.location.y - (D.y + 1)) < 2 && Math.hypot(alex.location.x - MM.heart.x, alex.location.z - MM.heart.z) > 25, "players land on the outer ring");
check(alex.music === "anatomy.music.mm_phase2", "phase 2 music");
check(alex.inputs[2] !== false && alex.hud === 1 && alex.cameraState === "default", "controls/HUD/camera restored after the unfolding");

// ------------------------------------------------------------------ D. phase 2 abilities and the heart
log("D. phase 2");
quiet();
const ringPos = (a, r) => ({ x: MM.heart.x + Math.cos(a) * r, y: D.y + 1.02, z: MM.heart.z + Math.sin(a) * r });
for (const id of ["continental_fold", "lithic_peristalsis", "inverted_strata", "geological_shedding", "mantle_contraction"]) {
  alex.teleport(ringPos(0.3, 20), { dimension: arena() });
  sam.teleport(ringPos(2.2, 26), { dimension: arena() });
  await runAbility(id, "P2");
  log(`P2 ${id} done; Alex ${alex.health.currentValue.toFixed(1)} Sam ${sam.health.currentValue.toFixed(1)}`);
}
// closed heart deflects
const hpClosed = heart.health.currentValue;
heart.setProperty("anatomy:open", false);
enc().exposedUntil = 0;
mock.playerAttack(alex, heart, 20);
check(heart.health.currentValue === hpClosed, "a sealed heart deflects hits");
let cycles = 0;
let rebloomSeen = false;
while (enc()?.state === "phase2" && cycles < 40) {
  cycles++;
  alex.teleport(ringPos(0.0, 5.5), { dimension: arena() });
  sam.teleport(ringPos(3.1, 5.5), { dimension: arena() });
  if (!enc().forceAbility("resonance_network")) {
    await mock.advance(20);
    continue;
  }
  await until(() => heart.getProperty("anatomy:open") === true || enc()?.state !== "phase2", 900, "heart to open");
  let hits = 0;
  while (heart.getProperty("anatomy:open") && enc()?.state === "phase2" && hits < 60) {
    mock.playerAttack(alex, heart, 14);
    mock.playerAttack(sam, heart, 14);
    alex.health.currentValue = 20;
    sam.health.currentValue = 20;
    hits++;
    await mock.advance(10);
  }
  if (enc()?.layout === 1) rebloomSeen = true;
  await until(() => (enc()?.tasks.count("mm:ability:resonance_network") ?? 0) === 0 || enc()?.state !== "phase2", 1500, "phase 2 resonance to finish");
  if (enc()?.layout === 1) rebloomSeen = true;
}
log(`phase 2 ended after ${cycles} cycles; state ${enc()?.state}`);
check(rebloomSeen, "the world refolds (re-bloom to the rotated rib layout) at low health");
check(["victory", "aftermath", "ending", "finished"].includes(enc()?.state ?? "finished"), "the heart can be defeated");
await until(() => enc()?.state === "aftermath" || !enc(), 600, "aftermath");
const loot = mock.allEntities().filter((e) => e.typeId === "minecraft:item");
check(loot.some((e) => e.item?.typeId === "anatomy:lithic_heart_shard"), "loot includes Lithic Heart Shards");
check(ents("anatomy:mm_root_leg").every((e) => e.getProperty("anatomy:pose") === 2), "legs collapse on victory");
await until(() => !enc(), 1400, "encounter cleanup");
check(alex.dimension.id === "minecraft:overworld" && Math.hypot(alex.location.x - 0.5, alex.location.z - 0.5) < 2, "players are returned home");
check(alex.fogStack.length === 0 && alex.music === undefined, "fog and music cleared");
check(mock.allEntities().filter((e) => e.dimension === arena() && e.typeId.startsWith("anatomy:")).length === 0, "boss entities removed");
let left = 0;
for (const k of arena().blocks.keys()) {
  const [x, y, z] = k.split(",").map(Number);
  if (x >= g.x0 && x < g.x0 + g.sx && z >= g.z0 && z < g.z0 + g.sz && y >= g.y0) left++;
}
check(left === 0, `arena cleared (${left} blocks left)`);
check(mock.tickingAreaIds().length === 0, "ticking area released");
check(mock.world.getDynamicProperty("anatomy:active") === undefined, "saved encounter cleared");
check(mock.allEntities().filter((e) => e.typeId === "minecraft:item" && e.dimension.id === "minecraft:overworld").some((e) => e.item?.typeId === "anatomy:lithic_heart_shard"), "uncollected loot is carried home with the players");
const st = JSON.parse(mock.world.getDynamicProperty("anatomy:stats") ?? "{}");
check(st.migrating_mountain?.victories === 1, "victory recorded in the Atlas");

// ------------------------------------------------------------------ E. resume after reload (phase 1 and phase 2)
log("E. resume");
manager.start((await import(pathToFileURL(path.join(SCR, "bosses", "migrating_mountain", "index.js")).href)).MIGRATING_MOUNTAIN, alex);
await until(() => enc()?.state === "phase1", 3000, "phase 1 (second run)");
quiet();
const n1 = ents("anatomy:mm_resonance_node")[0];
while (n1.isValid && !n1.getProperty("anatomy:dying")) {
  mock.playerAttack(alex, n1, 30);
  await mock.advance(2);
}
await mock.advance(60);
manager.save();
const saved = mock.world.getDynamicProperty("anatomy:active");
check(typeof saved === "string" && JSON.parse(saved).data.nodeDead.length === 1, "encounter saved with one destroyed node");
manager.active = undefined; // simulate a world reload: scripts restart, entities persist
manager.restore();
await until(() => enc()?.state === "phase1", 3000, "resumed phase 1");
check(ents("anatomy:mm_resonance_node").length === 2, "resume keeps destroyed nodes destroyed");
check(ents("anatomy:mm_root_leg").length === 14, "resume respawns legs without duplicates");
check(Math.abs(ents("anatomy:mm_lithic_heart")[0].health.currentValue - 1000 * (1 - 0.1333)) < 2, "resume restores heart health");
enc().forcePhase(2);
await until(() => enc()?.state === "phase2", 4000, "phase 2 (second run)");
manager.save();
manager.active = undefined;
manager.restore();
await until(() => enc()?.state === "phase2", 4000, "resumed phase 2");
check(ents("anatomy:mm_petal").length === 12, "resume in phase 2 rebuilds the crown (no duplicate petals)");
check(ents("anatomy:mm_lithic_heart").length === 1, "single heart after resume");

// ------------------------------------------------------------------ F. respawn pull-back, then defeat
log("F. respawn and defeat");
alex.teleport(ringPos(1.0, 20), { dimension: arena() });
alex.applyDamage(1000, { cause: "entityAttack" });
check(alex.dimension.id === "minecraft:overworld", "dead player respawns at home");
await until(() => alex.dimension.id === MM.dimensionId, 200, "respawned player pulled back into the fight");
for (const p of [alex, sam]) {
  p.teleport({ x: 0.5, y: 65, z: 0.5 }, { dimension: ow });
  p.setDynamicProperty("anatomy:return", undefined);
}
await until(() => !enc(), 1600, "defeat after the party leaves");
check(mock.world.getDynamicProperty("anatomy:active") === undefined, "defeat clears the saved encounter");

// ------------------------------------------------------------------ G. commands
log("G. commands");
const run = (name, ...args) => {
  const r = reg.commands[name].cb({ sourceEntity: alex, sourceType: "Entity" }, ...args);
  return r;
};
check(run("anatomy:boss", "start", "migrating_mountain")?.status === 0, "/anatomy:boss start");
await mock.advance(2);
check(!!enc(), "command started an encounter");
await until(() => enc()?.state === "phase1", 3000, "phase 1 via command");
check(run("anatomy:ability", "lithic_peristalsis")?.status === 0, "/anatomy:ability");
await mock.advance(5);
mock.system.afterEvents.scriptEventReceive.fire({ id: "anatomy:status", message: "", sourceEntity: alex });
mock.system.afterEvents.scriptEventReceive.fire({ id: "anatomy:stop", message: "", sourceEntity: alex });
await until(() => !enc(), 1600, "abort via /scriptevent");

// ------------------------------------------------------------------ G2. the reward
alex.inventory.container.slots[0] = new mock.ItemStack("anatomy:lithic_heart_shard", 2);
alex.selectedSlotIndex = 0;
reg.items["anatomy:heart_shard"].onUse({ source: alex, itemStack: alex.inventory.container.slots[0] }, { params: {} });
await mock.advance(2);
check(alex.inventory.container.slots[0]?.amount === 1, "using a Lithic Heart Shard consumes one");

// ------------------------------------------------------------------ H. the Anatomical Atlas flow
log("H. atlas");
const ui = await import(uiUrl);
sam.inventory.container.addItem(new mock.ItemStack("anatomy:restless_lodestone", 1));
sam.playerPermissionLevel = 0;
ui.answers.push(0, 0, 1); // specimen 001 -> Begin the encounter -> confirm
useItem(sam, "anatomy:anatomical_atlas");
await mock.advance(6);
check(!!enc(), "the Atlas can start the encounter (consuming the lodestone)");
check(!hasItem(sam, "anatomy:restless_lodestone"), "the Atlas start consumes the lodestone");
await until(() => enc()?.state === "phase1", 3000, "phase 1 via the Atlas");
ui.answers.push(0); // "Leave the encounter"
useItem(sam, "anatomy:anatomical_atlas");
await mock.advance(4);
check(sam.dimension.id === "minecraft:overworld", "the Atlas lets a player leave the fight");
ui.answers.push(0); // "Join the encounter"
useItem(sam, "anatomy:anatomical_atlas");
await mock.advance(4);
check(sam.dimension.id === MM.dimensionId, "the Atlas lets a player rejoin the fight");
manager.stop("abort");
await until(() => !enc(), 1600, "abort after the Atlas test");

// ------------------------------------------------------------------ I. a small chunk budget
// Parts wait for their chunks, survive unload/reload with new handles, stale parts are removed,
// and block edits in unloaded chunks are deferred and swept with short-lived ticking areas.
if (!mock.chunkSim.enabled) log("I. skipped (chunk emulation off)");
else await (async () => {
log("I. small chunk budget");
const tam = mock.world.tickingAreaManager;
const fullBudget = tam.maxChunkCount;
tam.maxChunkCount = Number(process.env.SIM_LOW_BUDGET ?? 12);
for (const p of [alex, sam]) {
  p.gameMode = "Survival";
  p.health.currentValue = 20;
}
const inArena = (e) => e.dimension === arena() && e.typeId.startsWith("anatomy:");
check(run("anatomy:boss", "start", "migrating_mountain")?.status === 0, "start with a small chunk budget");
await mock.advance(2);
await until(() => enc()?.state === "phase1", 6000, "phase 1 with a small chunk budget");
check(mock.tickingAreaChunks() <= tam.maxChunkCount, `ticking areas stay inside the budget (${mock.tickingAreaChunks()}/${tam.maxChunkCount})`);
// the nodes and the heart share a 3-chunk strip: with room for it (plus one spare chunk) they never wait
const roomy = tam.maxChunkCount >= 4;
if (roomy) check(ents("anatomy:mm_resonance_node").length === 3 && ents("anatomy:mm_lithic_heart").length === 1, "nodes and heart spawn (highest-priority region)");
check(Math.hypot(alex.location.x - ar.x, alex.location.z - ar.z) < ar.r + 2 && Math.abs(alex.location.y - (ar.y + 1)) < 1.5, "party stands on the arrival shelf (small budget)");
const legSum = () => enc().parts.summary("leg:");
log(`small budget: ${enc().keeper.kept}/${enc().keeper.wanted} chunks kept, legs spawned ${legSum().spawned}/14, refused spawns ${mock.stats.refusedSpawns}`);
if (process.env.SIM_DEBUG) console.log(enc().status());
check((!roomy || /parts: nodes 3\/3\/3/.test(enc().status())) && /chunks: kept \d+\/100 ticking/.test(enc().status()), "status reports parts and chunk coverage");
alex.gameMode = "Creative"; // tour the rim so every leg's chunk loads once
for (const l of m.legs) {
  alex.teleport({ x: l.pos.x, y: l.pos.y + 4, z: l.pos.z }, { dimension: arena() });
  await mock.advance(8);
}
check(legSum().spawned === 14, `all 14 legs spawn once their chunks load (${legSum().spawned})`);
const staleId = mock.storeEntity("anatomy:mm_resonance_node", arena(), { x: 60.5, y: 150, z: 50.5 }, ["anatomy_mm"]);
alex.teleport({ x: 60.5, y: 160, z: 50.5 }, { dimension: arena() });
await mock.advance(8);
check(!mock.allEntities().some((e) => e.id === staleId) && !mock.storedEntities().some((e) => e.id === staleId), "a stale boss part from an earlier fight is removed when its chunk loads");
// every ticking area is lost and everyone walks away: the nodes unload with their chunks ...
quiet();
await until(() => enc().writer.deferredOps === 0, 8000, "phase 1 backlog swept (no short-lived areas left)");
const radius0 = mock.chunkSim.radius;
mock.chunkSim.radius = Math.min(radius0, 4);
tam.removeAllTickingAreas();
for (const p of [alex, sam]) p.teleport({ x: ar.x + 0.5, y: ar.y + 1.05, z: ar.z + 0.5 }, { dimension: arena() });
await mock.advance(12);
check(ents("anatomy:mm_resonance_node").length === 0 && mock.storedEntities().filter((e) => e.typeId === "anatomy:mm_resonance_node").length === 3, "nodes unload with their chunks");
check(/nearest:.*Node.*\d+m/.test(alex.actionbar ?? ""), `the HUD points to the nearest node while it is unloaded (${alex.actionbar})`);
check(alex.locatorBar.list.size === 3, `3 node markers on the locator bar (${alex.locatorBar.list.size})`);
check(sam.locatorBar.list.size === 3, "every player gets the markers");
// ... and come back with new handles when a player returns; they can still be destroyed
quiet();
alex.gameMode = "Survival";
const dn = m.nodes.find((n) => n.id === "dorsal");
alex.teleport({ x: dn.safe.x, y: dn.safe.y + 0.05, z: dn.safe.z }, { dimension: arena() });
await mock.advance(10);
const back = ents("anatomy:mm_resonance_node").find((e) => Math.hypot(e.location.x - dn.pos.x, e.location.z - dn.pos.z) < 1);
check(!!back, "the dorsal node reloads with its chunk");
mock.chunkSim.radius = radius0;
if (back) {
  let hits = 0;
  while (back.isValid && !back.getProperty("anatomy:dying") && hits < 200) {
    mock.playerAttack(alex, back, 9);
    alex.health.currentValue = 20;
    hits++;
    await mock.advance(8);
  }
  if (process.env.SIM_DEBUG) log(`node loop exit: valid=${back.isValid} hits=${hits} alex=${JSON.stringify(alex.location)} hp=${back.health.currentValue} last=${alex.lastTeleport?.tick}:${alex.lastTeleport?.stack} msgs=${mock.stats.messages.slice(-3).join(" / ")}`);
  check(back.getProperty("anatomy:dying") === true, `a reloaded node can still be destroyed (${hits} hits)`);
}
await mock.advance(50);
check(enc().parts.respawns === 0, `reloads never duplicate parts (re-created: ${enc().parts.respawns})`);
check(alex.locatorBar.list.size === 2, `the destroyed node's marker is removed (${alex.locatorBar.list.size} left)`);
check(/destroyed §f1\/3/.test(alex.actionbar ?? ""), "HUD counts the destroyed node");
// the Great Unfolding cuts the whole body; edits in chunks nobody is near are deferred and swept
enc().forcePhase(2);
await until(() => enc()?.state === "phase2", 6000, "phase 2 with a small chunk budget");
quiet(); // sample the cut without phase 2 abilities (flesh, rubble) in the way
await until(() => abilityTasks() === 0 && enc()?.writer.deferredOps === 0, 9000, "deferred edits swept");
if (process.env.SIM_DEBUG && enc()?.writer.deferredOps) console.log(`  deferred left: ${enc().writer.deferredOps} in ${JSON.stringify(enc().writer.deferredChunks())}; areas ${JSON.stringify(mock.tickingAreaIds())} chunks ${mock.tickingAreaChunks()}/${tam.maxChunkCount}; tasks ${enc().tasks.tasks.filter((t) => !t.done).map((t) => t.name + "(w" + t.wait + ")").join(",")}; focusing=${enc().focusing}`);
check(alex.suffocatingTicks === 0 && sam.suffocatingTicks === 0, "players land on the disk, not inside uncut rock");
let strays = 0;
for (let i = 0; i < 3000; i++) {
  const x = g.x0 + Math.floor(Math.random() * g.sx);
  const z = g.z0 + Math.floor(Math.random() * g.sz);
  for (let y = D.y + 1; y < g.y0 + g.sy; y += 2) if (arena().getBlockId(x, y, z) !== "minecraft:air" && !arena().getBlockId(x, y, z).includes("water")) strays++;
}
if (process.env.SIM_DEBUG && strays >= 40) {
  const seen = new Map();
  for (const k of arena().blocks.keys()) {
    const [x, y, z] = k.split(",").map(Number);
    if (y <= D.y || x < g.x0 || x >= g.x0 + g.sx || z < g.z0 || z >= g.z0 + g.sz) continue;
    const id = arena().getBlockId(x, y, z);
    if (id.includes("water")) continue;
    const ck = `${Math.floor(x / 16)},${Math.floor(z / 16)}`;
    const e = seen.get(ck) ?? { n: 0, ids: new Map(), ys: [1e9, -1e9] };
    e.n++;
    e.ids.set(id, (e.ids.get(id) ?? 0) + 1);
    e.ys = [Math.min(e.ys[0], y), Math.max(e.ys[1], y)];
    seen.set(ck, e);
  }
  for (const [ck, e] of [...seen].sort((a, b) => b[1].n - a[1].n).slice(0, 12)) console.log(`  strays chunk ${ck}: ${e.n} blocks y${e.ys[0]}..${e.ys[1]} ${[...e.ids].slice(0, 4).map(([i, n]) => i.replace("minecraft:", "") + "x" + n).join(" ")}`);
  console.log(`  writer deferred chunks: ${JSON.stringify(enc().writer.deferredChunks())} queued cells ${mock.queuedStructureCells()}`);
}
check(strays < 40, `the whole shell is cut, far chunks included (${strays} stray blocks sampled)`);
let walk2 = 0;
let walk2ok = 0;
for (let r = 6; r < 33; r += 1)
  for (let a = 0; a < 360; a += 7) {
    const x = Math.floor(MM.heart.x + Math.cos((a * Math.PI) / 180) * r);
    const z = Math.floor(MM.heart.z + Math.sin((a * Math.PI) / 180) * r);
    if (!enc().isWalkway(x, z)) continue;
    walk2++;
    if (arena().getBlockId(x, D.y, z) !== "minecraft:air") walk2ok++;
  }
check(walk2 > 100 && walk2ok / walk2 > 0.97, `disk walkways placed with a small budget (${walk2ok}/${walk2})`);
check(enc().parts.summary("petal:").total === 12, "12 petals wanted");
alex.gameMode = "Creative"; // petals in chunks nobody was near appear once a player comes close
for (let k = 0; k < 12; k++) {
  const a = ((15 + 30 * k) * Math.PI) / 180;
  alex.teleport({ x: MM.heart.x + Math.cos(a) * MM.A * 0.8, y: D.y + 6, z: MM.heart.z + Math.sin(a) * MM.B * 0.8 }, { dimension: arena() });
  await mock.advance(6);
}
check(enc().parts.summary("petal:").spawned === 12, `all 12 petals spawn once their chunks load (${enc().parts.summary("petal:").spawned})`);
check(enc().petals.every((e) => e.getProperty("anatomy:petal_state") === 1), "late petals spawn already unfolded");
alex.gameMode = "Survival";
check(alex.locatorBar.list.size === 0, "node markers cleared in phase 2");
log(`small budget stats: refused writes ${mock.stats.refusedWrites}, refused spawns ${mock.stats.refusedSpawns}, unloads ${mock.stats.unloads}, reloads ${mock.stats.reloads}, queued structure cells ${mock.stats.queuedStructureCells}`);
manager.stop("abort");
await until(() => !enc(), 8000, "clean-up with a small chunk budget");
let left2 = 0;
for (const k of arena().blocks.keys()) {
  const [x, y, z] = k.split(",").map(Number);
  if (x >= g.x0 && x < g.x0 + g.sx && z >= g.z0 && z < g.z0 + g.sz && y >= g.y0) left2++;
}
check(left2 === 0 && mock.queuedStructureCells() === 0, `arena fully cleared with a small budget (${left2} blocks left, ${mock.queuedStructureCells()} queued cells)`);
check(mock.allEntities().filter(inArena).length === 0 && mock.storedEntities().filter(inArena).length === 0, "no boss parts left behind, loaded or stored");
check(mock.tickingAreaIds().length === 0, "ticking areas released after the small-budget fight");
check(alex.dimension.id === "minecraft:overworld" && alex.locatorBar.list.size === 0, "players home, locator bar clean");
check(mock.stats.queuedStructureCells === 0, `no structure placement ever left to the engine's unloaded-chunk queue (${mock.stats.queuedStructureCells} cells)`);
tam.maxChunkCount = fullBudget;
})();

// ------------------------------------------------------------------ J. the engine refuses or misplaces boss parts
log("J. spawn faults");
await (async () => {
  const F = mock.spawnFaults;
  const ui = await import(uiUrl);
  for (const p of [alex, sam]) {
    p.gameMode = "Survival";
    p.health.currentValue = 20;
  }
  // spawnEntity refuses the nodes but /summon works: they are created with the command
  F.refuse = new Set(["anatomy:mm_resonance_node"]);
  check(run("anatomy:boss", "start", "migrating_mountain")?.status === 0, "start while spawnEntity refuses the nodes");
  await mock.advance(2);
  await until(() => enc()?.state === "phase1", 4000, "phase 1 (spawnEntity refuses nodes)");
  check(ents("anatomy:mm_resonance_node").length === 3, "nodes are created with /summon when spawnEntity refuses them");
  check(enc().parts.report("node:").every((r) => r.via === "command" && r.state === "ok"), "the part report records the /summon fallback");
  const m0 = mock.stats.messages.length;
  ui.answers.push(1); // Atlas in a fight: Leave, Check the fight, ...
  useItem(alex, "anatomy:anatomical_atlas");
  await mock.advance(4);
  check(mock.stats.messages.slice(m0).some((t) => t.includes("[Anatomy] Fight check") && t.includes("Lithic Heart") && t.includes("✔")), "the Atlas 'Check the fight' button prints the part report");
  manager.stop("abort");
  await until(() => !enc(), 3000, "abort (summon fallback)");
  // the node type was never registered (its behaviour file rejected): the self-check says so in chat
  F.refuse = new Set();
  F.missing = new Set(["anatomy:mm_resonance_node"]);
  const m1 = mock.stats.messages.length;
  run("anatomy:boss", "start", "migrating_mountain");
  await mock.advance(2);
  await until(() => enc()?.state === "phase1", 4000, "phase 1 (node type missing)");
  await mock.advance(260);
  const said = mock.stats.messages.slice(m1).join("\n");
  check(/Problem found/.test(said) && /did not load: §fanatomy:mm_resonance_node/.test(said), "the self-check reports an entity type the game did not load");
  check(/could not be created: §fspawnEntity: InvalidArgumentError: Invalid entity identifier/.test(said), "the self-check quotes the engine's error");
  check(ents("anatomy:mm_resonance_node").length === 0 && ents("anatomy:mm_lithic_heart").length === 1 && ents("anatomy:mm_root_leg").length === 14, "other parts are not affected");
  alex.setDynamicProperty("anatomy:lang", "th");
  check(/ชนิดเอนทิตีที่เกมไม่ได้โหลด/.test(enc().checkReport(alex)) && /สร้างไม่ได้/.test(enc().checkReport(alex)), "the check report is available in Thai");
  alex.setDynamicProperty("anatomy:lang", undefined);
  manager.stop("abort");
  await until(() => !enc(), 3000, "abort (missing type)");
  F.missing = new Set();
  // the engine creates parts away from where they were asked for: they are moved back
  F.offset = { x: 0, y: -40, z: 0 };
  run("anatomy:boss", "start", "migrating_mountain");
  await mock.advance(2);
  await until(() => enc()?.state === "phase1", 4000, "phase 1 (misplaced spawns)");
  F.offset = null;
  const h = ents("anatomy:mm_lithic_heart")[0];
  check(!!h && Math.hypot(h.location.x - MM.heart.x, h.location.y - MM.heart.y, h.location.z - MM.heart.z) < 0.5, "a heart created away from its place is moved back");
  check(enc().parts.report("heart")[0]?.offsite === 40 && ents("anatomy:mm_resonance_node").every((e) => m.nodes.some((n) => Math.hypot(e.location.x - n.pos.x, e.location.y - n.pos.y, e.location.z - n.pos.z) < 0.5)), "misplaced parts are reported and every node is back on its site");
  manager.stop("abort");
  await until(() => !enc(), 3000, "abort (misplaced spawns)");
})();

// ------------------------------------------------------------------ report
console.log("");
console.log(`simulation: ${passed} checks passed, ${failures.length} failed, ${mock.issues.length} API issues, ${((Date.now() - t0) / 1000).toFixed(1)} s wall`);
console.log(`stats: block writes ${mock.stats.blockWrites}, fills ${mock.stats.fills}, structures ${mock.stats.structuresPlaced}, particles ${mock.stats.particles}, sounds ${mock.stats.sounds}, max writes/tick ${mock.stats.maxWritesPerTick}`);
console.log(`chunks: refused writes ${mock.stats.refusedWrites}, refused spawns ${mock.stats.refusedSpawns}, entity unloads ${mock.stats.unloads}, reloads ${mock.stats.reloads}, queued structure cells ${mock.stats.queuedStructureCells}`);
console.log(`animations: ${JSON.stringify(mock.stats.animations)}`);
for (const i of mock.issues.slice(0, 60)) console.log("  ISSUE", i);
for (const f of failures) console.log("  FAILED", f);
process.exit(failures.length || mock.issues.length ? 1 : 0);
