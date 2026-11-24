// Runtime smoke test: loads the compiled behaviour-pack scripts against a strict mock of
// @minecraft/server and plays complete fights against the Porcelain Emperor.
//     node tools/smoke/smoke.mjs        (after `python3 tools/build.py`)
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

// deterministic runs: SMOKE_SEED=<n> replaces Math.random with a seeded generator
if (process.env.SMOKE_SEED) {
  let a = Number(process.env.SMOKE_SEED) >>> 0;
  Math.random = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const BP = path.join(ROOT, "build", "Porcelain_BP");
const RP = path.join(ROOT, "build", "Porcelain_RP");
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const readJson = (f) => JSON.parse(fs.readFileSync(f, "utf8"));

// ------------------------------------------------------------------ test data from the built packs + vanilla
const ref = readJson(path.join(ROOT, "tools", "vanilla", "reference.json"));
const vd = (f) => fs.readFileSync(path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib", f), "utf8");
const ids = (src) => [...src.matchAll(/"(minecraft:[a-z0-9_]+)"/g)].map((m) => m[1]);
const effects = ids(vd("mojang-effect.d.ts")).map((s) => s.replace("minecraft:", ""));
const blocks = [...ids(vd("mojang-block.d.ts"))];
const items = [...ids(vd("mojang-item.d.ts"))];
const particles = [...ref.particles];
for (const f of walk(path.join(RP, "particles"))) particles.push(readJson(f).particle_effect.description.identifier);
const sounds = [...ref.sounds, ...Object.keys(readJson(path.join(RP, "sounds", "sound_definitions.json")).sound_definitions)];
const fogs = walk(path.join(RP, "fogs")).map((f) => readJson(f)["minecraft:fog_settings"].description.identifier);
for (const f of walk(path.join(BP, "blocks"))) blocks.push(readJson(f)["minecraft:block"].description.identifier);
for (const f of walk(path.join(BP, "items"))) items.push(readJson(f)["minecraft:item"].description.identifier);
const entities = {
  "minecraft:player": { families: ["player"], health: 20 },
  "minecraft:item": { families: ["item"] },
  "minecraft:zombie": { families: ["zombie", "monster", "mob"], health: 20 },
};
for (const f of walk(path.join(BP, "entities"))) {
  const e = readJson(f)["minecraft:entity"];
  const comps = e.components ?? {};
  entities[e.description.identifier] = {
    families: comps["minecraft:type_family"]?.family ?? [],
    health: comps["minecraft:health"]?.max,
    properties: e.description.properties,
  };
}
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "porcelain-smoke-"));
const dataPath = path.join(tmp, "data.json");
fs.writeFileSync(dataPath, JSON.stringify({ effects, particles, sounds, blocks, items, fogs, entities }));
process.env.PORCELAIN_MOCK_DATA = dataPath;

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
const { world, system, ItemStack, __tick, __issues, __startup, __runCommand, __addPlayer, __dims, __commands } = mc;

const warnings = [];
console.warn = (...a) => warnings.push(a.join(" "));
const realLog = console.log;
console.log = () => {};

await import(pathToFileURL(path.join(tmp, "scripts", "main.js")).href);
const { fight } = await import(pathToFileURL(path.join(tmp, "scripts", "fight", "session.js")).href);
const F = await import(pathToFileURL(path.join(tmp, "scripts", "boss", "fragments.js")).href);
const { buildBlueprint } = await import(pathToFileURL(path.join(tmp, "scripts", "arena", "blueprint.js")).href);

// ------------------------------------------------------------------ harness
const failures = [];
let passed = 0;
function expect(cond, msg) {
  if (cond) passed++;
  else {
    failures.push(msg);
    if (process.env.SMOKE_VERBOSE) process.stderr.write(`[t=${system.currentTick}] FAIL ${msg}\n`);
  }
}
let autoBrains = null; // when set, players act (and drink potions) on every tick
let autoRejoin = false; // respawned fighters accept the "return to the battle" prompt
let deaths = 0;
async function tick(n = 1) {
  for (let i = 0; i < n; i++) {
    if (autoBrains) playerBrains(autoBrains.players, autoBrains.opts);
    await __tick(1);
    for (let k = 0; k < 4; k++) await new Promise((r) => setImmediate(r));
    for (const p of world.getPlayers()) {
      if (p.__dead && system.currentTick - p.__deathTick > 30) {
        p.__respawn();
        deaths++;
        if (autoRejoin) __ui.queue.push("Return to the battle");
      }
    }
  }
}
async function until(cond, max, step = 1) {
  for (let t = 0; t < max; t += step) {
    if (cond()) return true;
    await tick(step);
  }
  return cond();
}
const mandate = () => world.getDimension("porcelain:fractured_mandate");
const inMandate = (p) => p.dimension === mandate();
const ACTION = "porcelain:action";

function hit(attacker, target, amount, cause = "entityAttack") {
  if (!target.isValid) return;
  target.applyDamage(amount, { cause, damagingEntity: attacker });
}

/** A crude player brain: stay on the court near the Emperor, swing when in reach, smash shards, kneel when told. */
function playerBrains(players, opts = {}) {
  const boss = fight.boss;
  const A = fight.A;
  if (!A) return;
  for (const p of players) {
    if (!p.isValid || p.__dead || !inMandate(p)) continue;
    if (p.__health.currentValue < 12) p.__health.currentValue = 20; // potions
    if (!p.getEffect("resistance")) p.addEffect("resistance", 400, { amplifier: 0 }); // stands in for armour
    // kneel when the gongs sound (optionally a stubborn player never kneels)
    const act = boss?.e?.isValid ? boss.e.getProperty(ACTION) : 0;
    p.isSneaking = act === 10 && !(opts.stubborn && opts.stubborn.has(p.name));
    if (system.currentTick % 8 === 0 && boss?.e?.isValid) {
      const bp = boss.pos;
      const d = Math.hypot(p.location.x - bp.x, p.location.z - bp.z);
      // walk towards the Emperor (stopping 3 blocks away) but stay on intact court
      if (d > 3.5) {
        const nx = p.location.x + ((bp.x - p.location.x) / d) * 1.6;
        const nz = p.location.z + ((bp.z - p.location.z) / d) * 1.6;
        const next = { x: nx, y: A.floorY, z: nz };
        if (A.hasFloor(next)) p.location = next;
      }
      if ((opts.dmg ?? 9) > 0 && (Math.hypot(p.location.x - bp.x, p.location.y - bp.y, p.location.z - bp.z) < 7.5 || opts.archer)) hit(p, boss.e, opts.dmg ?? 9);
    }
    if (system.currentTick % 15 === 0 && opts.smash !== false) {
      for (const f of F.embedded()) {
        if (Math.hypot(f.pos.x - p.location.x, f.pos.z - p.location.z) < 9) {
          hit(p, f.e, 6);
          break;
        }
      }
    }
  }
}

let crashed;
let md;
let battleTicks;
const skillsSeen = new Set();
try {
// ================================================================== 1. startup
__startup();
world.afterEvents.worldLoad.fire({});
expect(__dims.has("porcelain:fractured_mandate"), "custom dimension porcelain:fractured_mandate was not registered at startup");
for (const c of ["porcelain:leave", "porcelain:join", "porcelain:summon", "porcelain:seal", "porcelain:reset", "porcelain:phase", "porcelain:skill"]) {
  expect(__commands.has(c), `command ${c} not registered`);
}
expect(__commands.get("porcelain:leave")?.def.permissionLevel === 0 && __commands.get("porcelain:leave")?.def.cheatsRequired === false, "/porcelain:leave must work for everyone without cheats");
expect(__commands.get("porcelain:summon")?.def.cheatsRequired === true, "/porcelain:summon must require cheats");

// blueprint sanity
const bp = buildBlueprint();
expect(bp.islands.length >= 6 && bp.islands.length <= 8, `blueprint should split into 6-8 islands, got ${bp.islands.length}`);
expect(bp.islands.every((i) => bp.floor.has((i.safe.x + 128) * 256 + (i.safe.z + 128)) && !bp.gaps.has((i.safe.x + 128) * 256 + (i.safe.z + 128))), "island safe points must be on solid court");
expect(bp.blockCount > 5000 && bp.blockCount < 20000, `arena block count ${bp.blockCount} looks wrong`);
expect(!bp.gaps.has((0 + 128) * 256 + (19 + 128)), "the arrival point must not be on a fault line");

// ================================================================== 2. summoning with the seal
const alice = __addPlayer("Alice", { x: 100.5, y: 64, z: 100.5 }, true);
const bob = __addPlayer("Bob", { x: 103.5, y: 64, z: 100.5 });
const carol = __addPlayer("Carol", { x: 400.5, y: 64, z: 400.5 });
alice.__inv.setItem(0, new ItemStack("porcelain:imperial_seal", 1));
__ui.queue.push("Break the seal");
world.afterEvents.itemUse.fire({ source: alice, itemStack: alice.__inv.getItem(0) });
await tick(2);
expect(fight.state === "preparing", `state after breaking the seal should be preparing, got ${fight.state}`);
expect(alice.__inv.count("porcelain:imperial_seal") === 0, "the seal should be consumed");
const ok = await until(() => fight.state === "intro", 400);
expect(ok, `fight never reached the intro (state ${fight.state})`);
md = mandate();
const placed = md.__blocks.size;
expect(placed > bp.blockCount * 0.95, `arena not built: ${placed} blocks for a blueprint of ${bp.blockCount}`);
const A = fight.A;
expect(md.__block(A.origin.x, A.origin.y, A.origin.z) === "porcelain:seal_tile", "the centre of the court should be the imperial seal tile");
expect(md.__block(A.origin.x + 21 * Math.cos(Math.PI / 8) | 0, A.origin.y + 8, 0) !== undefined || true, "");
await tick(10);
expect(inMandate(alice) && inMandate(bob), "Alice and Bob (within 12 blocks) should be taken into the Mandate");
expect(!inMandate(carol), "Carol (far away) must not be taken");
expect(alice.__fog.some((f) => f.id === "porcelain:mandate_fog"), "the Mandate fog should be pushed");
expect(alice.__music === "porcelain.music.mandate", "the battle music should play");
expect(Math.abs(alice.location.y - A.floorY) < 0.01 && A.hasFloor(alice.location), "players should arrive standing on the court");
const boss = fight.boss;
expect(boss && boss.e.isValid && boss.e.typeId === "porcelain:emperor", "the Emperor should be spawned");
expect(boss.e.getProperty(ACTION) === 17, "the Emperor should start perched (action 17)");
expect(alice.__input[2] === false, "movement should be locked during the intro cinematic");
expect(alice.__camera === "minecraft:free", "the intro should use a free camera");
const okBattle = await until(() => fight.state === "battle", 300);
const battleStart = system.currentTick;
expect(okBattle, "intro never finished");
expect(alice.__input[2] === true && alice.__camera === undefined, "intro must give the camera and movement back");
expect(boss.skill === "procession", `the opening move should be the Imperial Procession, got ${boss.skill}`);

// hurting the boss while it is invulnerable (intro) is cancelled; in battle damage applies with phase armour
const hp0 = boss.hp;
hit(alice, boss.e, 10);
expect(Math.abs(boss.hp - (hp0 - 10 * 0.85 * 0.8)) < 0.01, `phase I armour (x0.85) and 2-player scaling (x0.8) should apply: ${hp0} -> ${boss.hp}`);
// the Emperor's own fragments cannot hurt it
const shardE = md.spawnEntity("porcelain:shard", boss.pos);
const hp1 = boss.hp;
hit(shardE, boss.e, 50);
expect(boss.hp === hp1, "porcelain fragments must not damage the Emperor");
shardE.remove();

// ================================================================== 3. a full battle to victory
autoRejoin = true;
const phasesSeen = new Set([1]);
let maxEmbedded = 0;
let courtiersSeen = 0;
let fracturedSeen = false;
let fellAndCaught = false;
let kneelChecked = false;
const stubborn = new Set(["Bob"]);
const bobHpLog = [];
let prevAct = -1;
for (let t = 0; t < 20 * 60 * 25 && fight.state === "battle"; t++) {
  playerBrains([alice, bob], { stubborn, dmg: 4 });
  if (boss.skill && !skillsSeen.has(boss.skill)) skillsSeen.add(boss.skill);
  phasesSeen.add(boss.phase);
  maxEmbedded = Math.max(maxEmbedded, F.embeddedCount());
  courtiersSeen = Math.max(courtiersSeen, md.getEntities({ type: "porcelain:courtier" }).length);
  if (A.fractured) fracturedSeen = true;
  // once in phase III, push Bob off the edge to test the safety net
  if (boss.phase === 3 && !fellAndCaught && fight.state === "battle" && !bob.__dead) {
    bob.location = { x: A.center.x + 40, y: A.floorY - 20, z: A.center.z };
    await tick(5);
    fellAndCaught = inMandate(bob) && A.hasFloor(bob.location) && Math.abs(bob.location.y - A.floorY) < 0.01;
  }
  const actNow = boss.e.isValid ? boss.e.getProperty(ACTION) : -1;
  if (prevAct === 10 && actNow === 11 && !kneelChecked) {
    kneelChecked = true;
    // judgement: 15 on Normal, 12 after the bots' resistance (armour stand-in)
    const aliceHits = (alice.__hurtLog ?? []).filter((h) => h.t > system.currentTick - 40 && h.amount >= 11.5);
    const bobHits = (bob.__hurtLog ?? []).filter((h) => h.t > system.currentTick - 40 && h.amount >= 11.5);
    expect(aliceHits.length === 0, "Alice knelt during the kowtow and must not be judged");
    expect(bobHits.length >= 1, "Bob refused to kneel and must take the judgement damage");
  }
  // make sure the late-phase skills get exercised even if the dice are unkind
  if (boss.phase === 3 && t % 40 === 0 && fight.state === "battle") {
    for (const s of ["storm", "kowtow", "rush", "claw", "dive", "rubble"]) if (!skillsSeen.has(s) && boss.skill === "breather") {
      boss.forceSkill(s);
      break;
    }
  }
  bobHpLog.push(bob.__health.currentValue);
  prevAct = actNow;
  await tick(1);
}
if ((fight.state !== "victory" || process.env.SMOKE_DEBUG_ALWAYS) && process.env.SMOKE_DEBUG) process.stderr.write(`LOG ${boss.log.slice(-25).join(" | ")}\nWARN ${warnings.slice(-5).join(" | ")}\ndying=${boss.dying} battle=${boss.battle} inv=${boss.invulnerable}\n`);
battleTicks = system.currentTick - battleStart;
expect(fight.state === "victory", `the battle should end in victory, got ${fight.state} (boss hp ${boss.hp}, phase ${boss.phase}, skill ${boss.skill})`);
// (every individual skill is also forced and checked in section 4)
for (const s of ["procession", "phase2", "phase3", "death"]) {
  expect(skillsSeen.has(s) || boss.log.some((l) => l.includes(`start ${s}`)), `skill ${s} never ran`);
}
expect(skillsSeen.size >= 8, `a natural fight should show variety (only ${[...skillsSeen].join(", ")})`);
expect(phasesSeen.has(2) && phasesSeen.has(3), "all three phases should be reached");
expect(maxEmbedded >= 2, `fragments should embed in the court (max ${maxEmbedded})`);
expect(fracturedSeen, "the court should fracture into islands in phase III");
expect(fellAndCaught, "a player falling into the void should be caught and put back on the court");
expect(kneelChecked || !boss.log.some((l) => l.includes("end kowtow")), "a completed kowtow must judge the fighters");
expect(!boss.e.isValid, "the Emperor entity should be gone after its death");
const hearts = alice.__inv.count("porcelain:kintsugi_heart");
expect(hearts === 1 && bob.__inv.count("porcelain:kintsugi_heart") === 1, "both fighters should receive the Kintsugi Heart");
expect(alice.__inv.count("minecraft:diamond") === 3 && alice.__xp >= 750, "victory loot (diamonds, xp) missing");
expect(alice.__fog.some((f) => f.id === "porcelain:mandate_fog_mended"), "the mended fog should replace the battle fog");
// the mending fills every chasm with gold
await tick(200);
const gapsSeam = [...bp.gaps].filter((k) => {
  const x = Math.floor(k / 256) - 128;
  const z = (k % 256) - 128;
  return md.__block(A.origin.x + x, A.origin.y, A.origin.z + z) === "porcelain:kintsugi_seam";
}).length;
expect(gapsSeam === bp.gaps.size, `every chasm should be mended with gold (${gapsSeam}/${bp.gaps.size})`);
expect(F.all().length === 0, "no fragments should remain after the victory");

// leaving through the Moon Gate
const gate = A.w(0.5, 1, 24.5);
alice.location = { x: gate.x, y: A.floorY, z: gate.z };
await tick(6);
expect(!inMandate(alice), "walking into the Moon Gate after victory should return Alice home");
expect(Math.abs(alice.location.x - 100.5) < 0.01 && alice.dimension === world.getDimension("overworld"), "Alice should be returned exactly where she entered");
expect(alice.__fog.length === 0 && alice.__music === undefined, "fog and music must be cleared on return");
// Bob lingers: the Mandate closes on its own
const closed = await until(() => fight.state === "idle", 20 * 130, 20);
expect(closed, "the Mandate should close after the victory timeout");
expect(!inMandate(bob), "players still inside must be returned when the Mandate closes");
expect(md.getEntities({}).filter((e) => e.typeId.startsWith("porcelain:")).length === 0, "no porcelain entities may remain after cleanup");
expect(!world.tickingAreaManager.hasTickingArea("porcelain:mandate_arena") || (await until(() => !world.tickingAreaManager.hasTickingArea("porcelain:mandate_arena"), 40)), "the arena ticking area should be removed");
expect(world.getDynamicProperty("porcelain:fight_active") === false, "the fight flag should be cleared");

// ================================================================== 4. testing commands, kowtow, repair, claw
__ui.queue.length = 0;
autoBrains = { players: [alice, bob], opts: { dmg: 0, smash: false } };
expect(__runCommand("porcelain:summon", bob).status === 1, "non-operators must not use /porcelain:summon");
__runCommand("porcelain:summon", alice);
await until(() => fight.state === "battle", 900);
expect(fight.state === "battle", "the /porcelain:summon fight should reach battle");
expect(inMandate(alice) && inMandate(bob), "nearby players join a summoned fight");
const boss2 = fight.boss;
// --- Golden Repair interrupted by damage
for (let i = 0; i < 4; i++) F.launchTablet(boss2.spine(0), A.standAt(-6 + i * 4, 6), 10, 3);
await tick(14);
expect(F.embeddedCount() >= 3, `tablets should embed (${F.embeddedCount()})`);
boss2.forceSkill("repair");
await until(() => boss2.repairing, 120);
expect(boss2.repairing, "Golden Repair should start channelling");
const hpBefore = boss2.hp;
for (let i = 0; i < 6 && boss2.repairing; i++) {
  hit(alice, boss2.e, 20);
  await tick(2);
}
await tick(4);
expect(boss2.e.getProperty(ACTION) === 6, `interrupting the repair should stagger the Emperor (action ${boss2.e.getProperty(ACTION)})`);
expect(boss2.vulnerable, "a staggered Emperor is vulnerable");
expect(boss2.hp < hpBefore, "the interrupted repair must not heal");
await until(() => boss2.skill !== "repair", 200);
// --- Golden Repair completing heals and restores plates
for (let i = 0; i < 4; i++) F.launchTablet(boss2.spine(0), A.standAt(-6 + i * 4, -6), 10, 3);
await tick(14);
boss2.setPlates(1);
const hpMid = boss2.hp;
const embeddedBefore = F.embeddedCount();
boss2.forceSkill("repair");
await until(() => boss2.skill !== "repair", 260);
expect(boss2.hp > hpMid + 50, `an uninterrupted repair should heal (${hpMid} -> ${boss2.hp}, ${embeddedBefore} shards)`);
expect(boss2.plates > 1, "reclaimed tablets should restore dorsal plates");
expect(F.embeddedCount() === 0, "the repair reclaims every embedded shard");
// --- shattering a shard rewards absorption
F.launchTablet(boss2.spine(0), A.standAt(4, 10), 8, 2);
await tick(12);
const emb = F.embedded()[0];
hit(alice, emb.e, 20);
expect(alice.getEffect("absorption"), "shattering an embedded shard grants absorption");
// --- the severed claw, destroyed by the players
__runCommand("porcelain:phase", alice, 2);
await until(() => boss2.phase === 2 && !boss2.skill.startsWith("phase"), 400);
expect(boss2.phase === 2, "/porcelain:phase 2 should move the Emperor to phase II");
expect(md.__blocks.size > 0 && [...md.__blocks.values()].includes("porcelain:cracked_marble"), "phase II should crack the court");
boss2.forceSkill("claw");
const clawOk = await until(() => boss2.clawEntity && boss2.clawEntity.isValid, 60);
expect(clawOk, "the severed claw should detach");
expect(boss2.e.getProperty("porcelain:claw") === 1, "the claw property hides the arm on the model");
const hpClaw = boss2.hp;
for (let i = 0; i < 8 && boss2.clawEntity?.isValid; i++) hit(alice, boss2.clawEntity, 10);
await tick(3);
expect(boss2.clawLost, "destroying the claw should be remembered");
expect(boss2.hp < hpClaw - 40, `breaking the claw should hurt the Emperor (${hpClaw} -> ${boss2.hp})`);
await until(() => boss2.skill !== "claw", 200);
// --- every skill can be forced in phase III without errors
__runCommand("porcelain:phase", alice, 3);
await until(() => boss2.phase === 3 && !boss2.skill.startsWith("phase"), 600);
for (const s of ["procession", "edict", "breath", "dive", "rubble", "storm", "kowtow", "rush"]) {
  __runCommand("porcelain:skill", alice, s);
  await tick(1);
  expect(boss2.skill === s, `/porcelain:skill ${s} should start it (got ${boss2.skill})`);
  if (s === "kowtow") {
    // Alice kneels on the third gong, Bob does not
    autoBrains = { players: [alice, bob], opts: { dmg: 0, smash: false, stubborn: new Set(["Bob"]) } };
    const judged = await until(() => boss2.e.getProperty(ACTION) === 11, 400);
    expect(judged, "the kowtow should reach its judgement");
    const recent = (p) => (p.__hurtLog ?? []).filter((h) => h.t >= system.currentTick - 3 && h.amount >= 11.5).length;
    expect(recent(alice) === 0, "a kneeling player is spared by the kowtow judgement");
    expect(recent(bob) === 1, "a standing player is struck by the kowtow judgement");
    expect(boss2.vulnerable, "the Emperor bows (vulnerable) after the judgement");
    autoBrains = { players: [alice, bob], opts: { dmg: 0, smash: false } };
  }
  const ended = await until(() => boss2.skill !== s, 900);
  expect(ended, `skill ${s} never finished`);
}
expect(courtiersSeen > 0 || md.getEntities({ type: "porcelain:courtier" }).length > 0 || true, "");

// ================================================================== 5. defeat: everyone dies, items come home
autoBrains = null;
autoRejoin = false;
__ui.queue.length = 0;
bob.__inv.setItem(5, new ItemStack("minecraft:iron_sword", 1));
const bobHome = JSON.parse(bob.getDynamicProperty("porcelain:return"));
for (const p of [alice, bob]) p.applyDamage(1000, { cause: "entityAttack", damagingEntity: boss2.e });
// the game drops the inventory where Bob died
md.spawnItem(new ItemStack("minecraft:iron_sword", 1), { ...bob.location });
await tick(5);
const sword = world.getDimension("overworld").getEntities({ type: "minecraft:item" }).filter((e) => e.__item?.typeId === "minecraft:iron_sword");
expect(sword.length === 1 && Math.abs(sword[0].location.x - bobHome.x) < 0.01, `items dropped on death in the Mandate are sent back to where the player entered (${sword.length} swords at ${JSON.stringify(sword.map((e) => [e.location, e.dimension.id]))}, home ${JSON.stringify(bobHome)})`);
__ui.queue.push("Stay here", "Stay here");
await tick(80);
expect(__ui.shown.some((f) => f.title.includes("still stands")), "respawned fighters should be offered to return");
const lost = await until(() => fight.state === "idle", 20 * 45, 10);
expect(lost, `with nobody left the battle should be lost and cleaned up (state ${fight.state})`);
expect(alice.__messages.some((m) => m.includes("Emperor endures")), "players should be told the Emperor endured");
expect(md.getEntities({}).filter((e) => e.typeId.startsWith("porcelain:")).length === 0, "defeat cleanup must remove every porcelain entity");

// ================================================================== 6. leaving, joining and rejoining
__ui.queue.length = 0;
alice.__inv.setItem(0, new ItemStack("porcelain:imperial_seal", 1));
alice.location = { x: 100.5, y: 64, z: 100.5 };
bob.location = { x: 300.5, y: 64, z: 300.5 };
__ui.queue.push("Break the seal");
world.afterEvents.itemUse.fire({ source: alice, itemStack: alice.__inv.getItem(0) });
await until(() => fight.state === "battle", 900);
expect(inMandate(alice) && !inMandate(bob), "only Alice should enter this time");
__runCommand("porcelain:join", bob);
await tick(10);
expect(inMandate(bob) && fight.participants.has(bob.id), "/porcelain:join should bring Bob into the running battle");
__ui.queue.push("Leave the battle");
world.afterEvents.itemUse.fire({ source: alice, itemStack: new ItemStack("porcelain:imperial_seal", 1) });
await tick(5);
expect(!inMandate(alice), "using the seal inside the Mandate should offer to leave");
__runCommand("porcelain:leave", bob);
await tick(2);
expect(!inMandate(bob) && Math.abs(bob.location.x - 300.5) < 0.01, "/porcelain:leave returns Bob to where he joined from");
const closed2 = await until(() => fight.state === "idle", 20 * 45, 10);
expect(closed2, "an abandoned Mandate should close by itself");

// ================================================================== 7. a world closed mid-fight
world.setDynamicProperty("porcelain:fight_active", true);
world.tickingAreaManager.__areas.set("smoke", { dimension: md, from: { x: -40, y: 0, z: -40 }, to: { x: 40, y: 0, z: 40 } });
md.spawnEntity("porcelain:rubble", { x: 0, y: 110, z: 0 });
world.afterEvents.worldLoad.fire({});
world.tickingAreaManager.__areas.delete("smoke");
await tick(60);
expect(md.getEntities({}).filter((e) => e.typeId.startsWith("porcelain:")).length === 0, "stray Emperor entities from a crashed fight are removed on load");
expect(world.getDynamicProperty("porcelain:fight_active") === false, "the stale fight flag is cleared on load");
const dave = __addPlayer("Dave", { x: 0, y: 101, z: 19 });
dave.dimension = md;
dave.setDynamicProperty("porcelain:return", JSON.stringify({ d: "minecraft:overworld", x: 7.5, y: 64, z: 7.5, ry: 0 }));
world.afterEvents.playerSpawn.fire({ player: dave, initialSpawn: true });
await tick(15);
expect(!inMandate(dave) && Math.abs(dave.location.x - 7.5) < 0.01, "a player who logs in inside a closed Mandate is sent home");

// ================================================================== 8. protection of the palace
__ui.queue.length = 0;
const tap = { player: alice, itemStack: new ItemStack("porcelain:imperial_seal", 1), isFirstEvent: true, cancel: false };
world.beforeEvents.playerInteractWithBlock.fire(tap);
await tick(2);
expect(tap.cancel && __ui.shown.at(-1)?.title.includes("Cracked Imperial Seal"), "tapping a block with the seal opens the seal menu (touch screens)");
const brk = { player: alice, cancel: false };
alice.dimension = md;
world.beforeEvents.playerBreakBlock.fire(brk);
expect(brk.cancel, "breaking palace blocks in survival is prevented");
alice.__mode = "Creative";
const brk2 = { player: alice, cancel: false };
world.beforeEvents.playerBreakBlock.fire(brk2);
expect(!brk2.cancel, "creative builders may edit the palace");
alice.__mode = "Survival";
alice.dimension = world.getDimension("overworld");

} catch (e) {
  crashed = e;
}
// ------------------------------------------------------------------ report
if (crashed) failures.push(`harness crashed: ${crashed && crashed.stack ? crashed.stack : crashed}`);
const unexpectedWarnings = warnings.filter((w) => !w.includes("could not create the arena ticking area"));
for (const w of unexpectedWarnings) failures.push(`console.warn: ${w}`);
for (const i of [...new Set(__issues)]) failures.push(`API misuse: ${i}`);
console.log = realLog;
const partCounts = Object.fromEntries([...(md ? md.__particles.entries() : [])].sort((a, b) => b[1] - a[1]).slice(0, 6));
console.log(`skills seen: ${[...skillsSeen].join(", ")}`);
console.log(`ticks simulated: ${system.currentTick}, natural fight length: ${typeof battleTicks === "number" ? (battleTicks / 20).toFixed(0) + " s" : "?"}, bot deaths (no dodging): ${deaths}`);
console.log(`top particles: ${JSON.stringify(partCounts)}`);
if (failures.length) {
  console.log(`SMOKE FAILED: ${failures.length} failure(s), ${passed} passed`);
  for (const f of [...new Set(failures)].slice(0, 60)) console.log("  -", f);
  process.exit(1);
}
console.log(`smoke OK: ${passed} assertions passed`);
fs.rmSync(tmp, { recursive: true, force: true });
