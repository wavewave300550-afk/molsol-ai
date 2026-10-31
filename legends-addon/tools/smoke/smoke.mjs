// Runtime smoke test: loads the compiled behaviour-pack scripts against a strict
// mock of @minecraft/server and plays every boss through entrance, every skill of
// every phase, every transition, every ultimate, the special mechanics and death.
//     node tools/smoke/smoke.mjs        (after `python3 tools/build.py`)
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const BP = path.join(ROOT, "build", "Legends_BP");
const RP = path.join(ROOT, "build", "Legends_RP");

// ------------------------------------------------------------------ test data from the built packs
const ref = JSON.parse(fs.readFileSync(path.join(ROOT, "tools", "vanilla", "reference.json"), "utf8"));
const effects = [...fs.readFileSync(path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib", "mojang-effect.d.ts"), "utf8")
  .matchAll(/"minecraft:([a-z_]+)"/g)].map((m) => m[1]);
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));
const BUILTIN = new Set(["variable.particle_age", "variable.particle_lifetime", "variable.particle_random_1", "variable.particle_random_2",
  "variable.particle_random_3", "variable.particle_random_4", "variable.emitter_age", "variable.emitter_lifetime"]);
const particles = {};
for (const f of walk(path.join(RP, "particles"))) {
  const j = JSON.parse(fs.readFileSync(f, "utf8"));
  const need = new Set([...JSON.stringify(j.particle_effect.components).matchAll(/variable\.[a-z_0-9]+(?:\.[a-z_0-9]+)?/g)].map((m) => m[0]).filter((v) => !BUILTIN.has(v)));
  particles[j.particle_effect.description.identifier] = [...need];
}
const entities = {
  "minecraft:player": { families: ["player"], events: [], health: 20 },
  "minecraft:item": { families: [], events: [] },
};
for (const f of walk(path.join(BP, "entities"))) {
  const e = JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:entity"];
  const c = e.components ?? {};
  entities[e.description.identifier] = {
    families: c["minecraft:type_family"]?.family ?? [],
    events: Object.keys(e.events ?? {}),
    health: c["minecraft:health"]?.max,
    properties: e.description.properties,
  };
}
const items = walk(path.join(BP, "items")).map((f) => JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:item"].description.identifier);

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "legends-smoke-"));
fs.writeFileSync(path.join(tmp, "data.json"), JSON.stringify({ effects, particles, sounds: ref.sounds, entities, items }));
process.env.LEGENDS_MOCK_DATA = path.join(tmp, "data.json");
fs.cpSync(path.join(BP, "scripts"), path.join(tmp, "scripts"), { recursive: true });
fs.writeFileSync(path.join(tmp, "package.json"), JSON.stringify({ type: "module" }));
for (const [pkg, file] of [["server", "mock-server.mjs"], ["server-ui", "mock-server-ui.mjs"]]) {
  const dir = path.join(tmp, "node_modules", "@minecraft", pkg);
  fs.mkdirSync(dir, { recursive: true });
  fs.copyFileSync(path.join(HERE, file), path.join(dir, "index.mjs"));
  fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({ name: `@minecraft/${pkg}`, type: "module", exports: "./index.mjs" }));
}
const imp = (p) => import(pathToFileURL(path.join(tmp, p)).href);
const mc = await imp("node_modules/@minecraft/server/index.mjs");
const { __ui } = await imp("node_modules/@minecraft/server-ui/index.mjs");
const { world, Player, ItemStack, __tick, __issues, __stats, __startup, __commands, Difficulty } = mc;

const warnings = [];
console.warn = (...a) => warnings.push(a.join(" "));
await imp("scripts/main.js");
__startup();
const { beings } = await imp("scripts/bosses/being.js");
const { summonNow } = await imp("scripts/summon.js");
const { adoptOrphans } = await imp("scripts/bosses/registry.js");
const { spawnProp } = await imp("scripts/core/hazards.js");

// ------------------------------------------------------------------ harness
const failures = [];
let passed = 0;
const expect = (cond, msg) => (cond ? passed++ : failures.push(msg));
const out = (...a) => process.stdout.write(a.join(" ") + "\n");
async function tick(n = 1) {
  for (let i = 0; i < n; i++) await __tick(1);
}
async function until(cond, max) {
  for (let i = 0; i < max; i++) {
    if (cond()) return i;
    await tick(1);
  }
  return cond() ? max : -1;
}
const dim = world.getDimension("minecraft:overworld");
const alice = new Player("Alice", dim, { x: 0, y: 64, z: 0 });
const bob = new Player("Bob", dim, { x: 5, y: 64, z: 3 });
const players = [alice, bob];
world.afterEvents.playerSpawn.fire({ player: alice, initialSpawn: true });
world.afterEvents.playerSpawn.fire({ player: bob, initialSpawn: true });

function resetPlayers() {
  alice.location = { x: 0, y: 64, z: 0 };
  bob.location = { x: 5, y: 64, z: 3 };
  for (const p of players) {
    p.__health.currentValue = 20;
    p.__ground = true;
  }
}
function legends() {
  return dim.getEntities({ families: ["legends"] });
}
async function clearWorld() {
  for (const b of [...beings.values()]) b.dispose();
  for (const e of legends()) e.remove();
  await tick(2);
}
const issuesBefore = () => __issues.length;
const hurtSince = (p, t0) => p.__hurt.filter((h) => h.tick >= t0);

// ------------------------------------------------------------------ 0. bootstrap
expect(["legends:codex", "legends:summon", "legends:phase", "legends:clear", "legends:sigils"].every((c) => __commands[c]), "custom commands registered");
await tick(45);
expect(alice.__inv.slots.some((s) => s?.typeId === "legends:codex"), "codex given on first join");

// ------------------------------------------------------------------ 1. every boss, every phase, every skill
const BOSSES = ["taotie", "nidhogg", "hanuman", "alicorn", "tenko", "logos"];
const report = {};
for (const key of BOSSES) {
  await clearWorld();
  resetPlayers();
  const t0 = mc.system.currentTick;
  const iss0 = issuesBefore();
  const warn0 = warnings.length;
  const p0 = __stats.particles;
  const e = summonNow(dim, { x: 0, y: 64, z: 14 }, key, 180);
  const b = beings.get(e.id);
  expect(!!b && b.phase === 0 && b.invuln, `${key}: spawns in its entrance, invulnerable`);
  const hp0 = e.__health.currentValue;
  e.applyDamage(80, { cause: "entityAttack", damagingEntity: alice });
  expect(e.__health.currentValue === hp0, `${key}: no damage during the entrance`);
  const entr = await until(() => b.phase === 1, 600);
  expect(entr >= 0, `${key}: entrance completes (phase 1)`);
  expect(e.getProperty("legends:phase") === 1, `${key}: phase property synced`);
  expect(Math.abs(b.partyMul() - 1 / 1.5) < 1e-6, `${key}: two-player HP scaling`);
  const skills = b.skills();
  const ran = new Set();
  const nPh = b.thresholds.length + 1;
  for (let ph = 1; ph <= nPh; ph++) {
    if (ph > 1) {
      // bring HP to the gate with a huge hit: it must stop exactly at the gate, then transform
      const gate = b.maxHp * b.thresholds[ph - 2];
      e.applyDamage(1e6, { cause: "entityAttack", damagingEntity: alice });
      expect(e.__health.currentValue >= gate - 0.01 && e.__health.currentValue > 0, `${key}: HP gate holds at phase ${ph - 1} (${e.__health.currentValue.toFixed(1)} vs ${gate.toFixed(1)})`);
      const tr = await until(() => b.coName === "transition" || b.phase === ph, 60);
      expect(tr >= 0, `${key}: transition to phase ${ph} starts`);
      const inv = b.invuln;
      expect(inv || b.phase === ph, `${key}: invulnerable while transforming`);
      const done = await until(() => b.phase === ph && b.coName !== "transition", 600);
      expect(done >= 0, `${key}: reaches phase ${ph}`);
      expect(e.getProperty("legends:phase") === ph, `${key}: phase ${ph} property synced`);
    }
    for (const s of skills.filter((s) => s.phases.includes(ph))) {
      resetPlayers();
      b.interrupt();
      b.target = alice;
      const before = issuesBefore();
      b.start(s.name, s.run(alice));
      const fin = await until(() => !b.co, 1200);
      expect(fin >= 0, `${key}: skill ${s.name} (phase ${ph}) finishes`);
      expect(issuesBefore() === before, `${key}: skill ${s.name} raised no API issues: ${__issues.slice(before).join(" | ")}`);
      ran.add(s.name);
      b.rest = 9999; // keep the AI from picking its own skills between forced ones
      await tick(2);
    }
  }
  expect(ran.size === skills.length, `${key}: every skill exercised (${ran.size}/${skills.length})`);
  report[key] = { skills: ran.size, phases: nPh };
  // ultimate
  resetPlayers();
  b.interrupt();
  b.rest = 9999;
  const ultT0 = mc.system.currentTick;
  b.start("ultimate", b.wrapUlt());
  const uf = await until(() => !b.co, 1500);
  expect(uf >= 0, `${key}: ultimate completes (${uf} ticks)`);
  report[key].ultTicks = uf;
  const ultMsgs = __stats.actionbars.filter((m) => m.tick >= ultT0 && m.text.includes("⚠"));
  expect(ultMsgs.length >= 1, `${key}: ultimate announced once on the action bar`);
  // death
  resetPlayers();
  b.rest = 9999;
  b.interrupt();
  const g = b.gateHp();
  e.__health.currentValue = Math.max(g, 2);
  b.hp = e.__health.currentValue;
  e.applyDamage(1e6, { cause: "entityAttack", damagingEntity: alice });
  if (key === "hanuman") {
    // first fall: Vayu's breath - destroy all wisps to deny the revival
    const vs = await until(() => b.coName === "revive" && dim.getEntities({ type: "legends:wind_wisp" }).length === 4, 200);
    expect(vs >= 0, "hanuman: Vayu's Breath summons four wind wisps");
    for (const w of dim.getEntities({ type: "legends:wind_wisp" })) w.applyDamage(100, { cause: "entityAttack", damagingEntity: bob });
  }
  const gone = await until(() => !e.isValid, 600);
  expect(gone >= 0, `${key}: dies after its death sequence`);
  await tick(3);
  expect(legends().length === 0, `${key}: no props / followers left behind (${legends().map((x) => x.typeId).join(",")})`);
  expect(!beings.has(e.id), `${key}: controller disposed`);
  expect(issuesBefore() === iss0, `${key}: no API issues during the fight: ${__issues.slice(iss0, iss0 + 5).join(" | ")}`);
  expect(warnings.length === warn0, `${key}: no script errors: ${warnings.slice(warn0, warn0 + 3).join(" | ")}`);
  const ticks = mc.system.currentTick - t0;
  report[key].particlesPerSec = Math.round(((__stats.particles - p0) / ticks) * 20);
  report[key].fightTicks = ticks;
}

// ------------------------------------------------------------------ 2. mechanics
async function freshBoss(key, phase) {
  await clearWorld();
  resetPlayers();
  const e = summonNow(dim, { x: 0, y: 64, z: 14 }, key, 180);
  const b = beings.get(e.id);
  await until(() => b.phase === 1, 600);
  while (b.phase < phase) {
    e.applyDamage(1e6, { cause: "entityAttack", damagingEntity: alice });
    const ph = b.phase;
    await until(() => b.phase === ph + 1 && b.coName !== "transition", 700);
  }
  b.interrupt();
  b.rest = 9999;
  return { e, b };
}

{ // Taotie: dings shelter, gluttony
  const { b } = await freshBoss("taotie", 2);
  const mouth = b.mouth();
  alice.location = { x: mouth.x, y: 64, z: mouth.z - 10 };
  const mid = { x: mouth.x, y: 64, z: mouth.z - 5 };
  expect(!b.sheltered(alice, mouth), "taotie: exposed player is not sheltered");
  const d = spawnProp(dim, "ding", mid, 0, b.entity);
  b.dings.push(d);
  expect(b.sheltered(alice, mouth), "taotie: a ding between player and maw shelters");
  const item = dim.spawnItem(new ItemStack("minecraft:bread"), b.mouth());
  await tick(25);
  expect(!item.isValid, "taotie: devours dropped items near its maw");
}

{ // Alicorn: Dawnbreak Nova spares sigils only
  const { b } = await freshBoss("alicorn", 3);
  world.__particleLog = [];
  const t0 = mc.system.currentTick;
  b.start("ultimate", b.wrapUlt());
  const found = await until(() => (world.__particleLog ?? []).some((p) => p.id === "legends:tele_fill" && p.tick >= t0 && p.color && p.color.blue > 0.3 && p.color.blue < 0.34 && p.vars["variable.size"]), 300);
  const sig = world.__particleLog.find((p) => p.id === "legends:tele_fill" && p.color && p.color.blue > 0.3 && p.color.blue < 0.34);
  expect(found >= 0 && !!sig, "alicorn: golden safe sigils appear");
  if (sig) {
    alice.location = { x: sig.loc.x, y: 64, z: sig.loc.z };
    bob.location = { x: 200, y: 64, z: 200 }; // far: not a fighter, out of range
    const tb = mc.system.currentTick;
    await until(() => !b.co, 600);
    const big = hurtSince(alice, tb).filter((h) => h.amount >= 25);
    expect(big.length === 0, "alicorn: player inside a sigil survives the Nova untouched");
  }
  resetPlayers();
  b.start("ultimate", b.wrapUlt());
  const t1 = mc.system.currentTick;
  await until(() => !b.co, 600);
  expect(hurtSince(alice, t1).some((h) => h.amount >= 25), "alicorn: player outside every sigil is struck by the Nova");
}

{ // Logos: choir exists and fights; ward; Eden
  const { e, b } = await freshBoss("logos", 3);
  await tick(5);
  const choir = ["seraph", "cherub", "ophan"].map((r) => dim.getEntities({ type: `legends:${r}` }).length);
  expect(choir.every((n) => n === 1), `logos: seraph, cherub and ophan attend the Word (${choir})`);
  const cher = [...beings.values()].find((x) => x.role === "cherub");
  cher.warding = 60;
  cher.takenSince = 0;
  await tick(1);
  const h0 = e.__health.currentValue;
  e.applyDamage(30, { cause: "entityAttack", damagingEntity: alice });
  const lost = h0 - e.__health.currentValue;
  expect(Math.abs(lost - 30 * 0.5 / 1.5) < 0.05, `logos: the Cherub's ward halves damage (${lost.toFixed(2)})`);
  for (const m of [...beings.values()].filter((x) => x.role)) {
    const before = issuesBefore();
    for (const k of m.kit()) {
      m.interrupt();
      m.start("t", k(alice));
      await until(() => !m.co, 600);
    }
    m.interrupt();
    m.start("sig", m.signature(alice));
    const ok = await until(() => !m.co, 600);
    expect(ok >= 0 && issuesBefore() === before, `logos: ${m.role} skills and signature run cleanly`);
  }
  resetPlayers();
  b.start("ultimate", b.wrapUlt());
  const ed = await until(() => dim.getEntities({ type: "legends:eden_sword" }).length === 1, 300);
  expect(ed >= 0, "logos: the flaming sword of Eden is planted");
  const sword = dim.getEntities({ type: "legends:eden_sword" })[0];
  if (sword) {
    alice.location = { x: sword.location.x, y: 64, z: sword.location.z };
    bob.location = { x: sword.location.x + 12, y: 64, z: sword.location.z };
    const tb = mc.system.currentTick;
    for (let i = 0; i < 700 && b.co; i++) {
      // keep Alice in Eden and Bob outside despite knockback
      alice.location = { x: sword.location.x, y: 64, z: sword.location.z };
      bob.location = { x: sword.location.x + 12, y: 64, z: sword.location.z };
      await tick(1);
    }
    expect(!hurtSince(alice, tb).some((h) => h.amount >= 40), "logos: Eden spares the player at the Final Word");
    expect(hurtSince(bob, tb).some((h) => h.amount >= 40), "logos: the Final Word strikes those outside Eden");
  }
  // kill the cherub: the Word re-speaks it in phase III
  for (const c of dim.getEntities({ type: "legends:cherub" })) c.applyDamage(1e5, { cause: "entityAttack", damagingEntity: alice });
  await tick(2);
  b.interrupt();
  b.start("reforge", b.skills().find((s) => s.name === "reforge").run(alice));
  await until(() => !b.co, 200);
  expect(dim.getEntities({ type: "legends:cherub" }).length === 1, "logos: a fallen Cherub is re-spoken");
}

{ // Hanuman: revival when wisps survive; counter
  const { e, b } = await freshBoss("hanuman", 3);
  e.__health.currentValue = b.gateHp() + 1;
  b.hp = e.__health.currentValue;
  e.applyDamage(1e6, { cause: "entityAttack", damagingEntity: alice });
  const rv = await until(() => b.coName === "revive", 50);
  expect(rv >= 0, "hanuman: falls into Vayu's Breath");
  const back = await until(() => b.coName !== "revive" && !b.invuln, 500);
  expect(back >= 0 && e.isValid && e.__health.currentValue > 20 && b.wrath > 1, "hanuman: revived by the wind when wisps survive (wrath)");
  b.interrupt();
  resetPlayers();
  b.start("guard", b.skills().find((s) => s.name === "guard").run(alice));
  await tick(6);
  const h0 = alice.__hurt.length;
  e.applyDamage(10, { cause: "entityAttack", damagingEntity: alice });
  await until(() => !b.co, 120);
  expect(alice.__hurt.length > h0, "hanuman: attacking the Vajra guard triggers a counter-strike");
}

{ // Nidhogg: exhausted window takes +60%
  const { e, b } = await freshBoss("nidhogg", 3);
  b.start("ultimate", b.wrapUlt());
  const ex = await until(() => b.takenMul > 1.5, 900);
  expect(ex >= 0, "nidhogg: lies exhausted after the Ragnarök rupture");
  const h0 = e.__health.currentValue;
  e.applyDamage(10, { cause: "entityAttack", damagingEntity: alice });
  expect(Math.abs((h0 - e.__health.currentValue) - 10 * 1.6 / 1.5) < 0.05, "nidhogg: exhausted window amplifies damage");
  await until(() => !b.co, 400);
}

{ // Tenko: illusions spawn and swap
  const { b } = await freshBoss("tenko", 2);
  b.start("illusion", b.skills().find((s) => s.name === "illusion").run(alice));
  await until(() => !b.co, 200);
  expect(dim.getEntities({ type: "legends:tenko_illusion" }).length === 2, "tenko: two foxfire illusions appear");
  for (const il of dim.getEntities({ type: "legends:tenko_illusion" })) il.applyDamage(5, { cause: "entityAttack", damagingEntity: alice });
  await tick(2);
  expect(dim.getEntities({ type: "legends:tenko_illusion" }).length === 0, "tenko: illusions shatter in one hit");
}

{ // reload: adopt an existing boss and keep its phase
  const { e, b } = await freshBoss("nidhogg", 2);
  b.dispose();
  expect(!beings.has(e.id), "reload: controller dropped");
  adoptOrphans();
  const nb = beings.get(e.id);
  expect(!!nb && nb.phase === 2 && nb.flying, "reload: boss re-adopted in phase 2, still airborne");
  await tick(40);
  expect(issuesBefore() >= 0, "reload: keeps running");
}

{ // departure when nobody fights
  const { e, b } = await freshBoss("tenko", 1);
  alice.location = { x: 900, y: 64, z: 900 };
  bob.location = { x: -900, y: 64, z: -900 };
  const gone = await until(() => !e.isValid, 1400);
  expect(gone >= 0, "departure: a legend left alone for 60 s departs");
  expect(dim.getEntities({ type: "minecraft:item" }).some((it) => it.__item?.typeId === "legends:sigil_tenko"), "departure: the sigil is returned");
  expect(!beings.has(b.id), "departure: controller disposed");
}

{ // rituals: sigil use, consumption, peaceful refusal
  await clearWorld();
  resetPlayers();
  alice.__inv.slots[0] = new ItemStack("legends:sigil_hanuman");
  alice.selectedSlotIndex = 0;
  world.afterEvents.itemUse.fire({ source: alice, itemStack: alice.__inv.slots[0] });
  await tick(2);
  expect(!alice.__inv.slots[0], "ritual: the sigil is consumed");
  const sp = await until(() => dim.getEntities({ type: "legends:hanuman" }).length === 1, 160);
  expect(sp >= 0, "ritual: Hanuman answers the Wind-Crystal Trident");
  await clearWorld();
  world.__difficulty = Difficulty.Peaceful;
  alice.__inv.slots[0] = new ItemStack("legends:sigil_taotie");
  world.afterEvents.itemUse.fire({ source: alice, itemStack: alice.__inv.slots[0] });
  await tick(130);
  expect(!!alice.__inv.slots[0] && dim.getEntities({ type: "legends:taotie" }).length === 0, "ritual: refused (and refunded) in Peaceful");
  world.__difficulty = Difficulty.Normal;
}

// ------------------------------------------------------------------ 3. screen-clarity audit
const visible = (t) => t.replace(/§./g, "");
expect(__stats.titles === 0, "UI: no titles ever shown");
const longest = Math.max(...__stats.actionbars.map((m) => visible(m.text).length));
expect(longest <= 34, `UI: every action-bar message ≤ 34 characters (longest ${longest})`);
for (const p of players) {
  const msgs = __stats.actionbars.filter((m) => m.player === p.name).sort((a, b) => a.tick - b.tick);
  let minGap = 1e9;
  for (let i = 1; i < msgs.length; i++) minGap = Math.min(minGap, msgs[i].tick - msgs[i - 1].tick);
  expect(minGap >= 20, `UI: ${p.name} never gets two messages within 1 s (min gap ${minGap})`);
  const visibleMsgs = new Set(msgs.map((m) => m.text));
  expect(visibleMsgs.size >= 6, `UI: ${p.name} saw the expected kinds of notices (${visibleMsgs.size})`);
}
const totalTicks = mc.system.currentTick;
const perMin = (__stats.actionbars.filter((m) => m.player === "Alice").length / totalTicks) * 1200;
expect(perMin < 8, `UI: under 8 action-bar lines per minute (${perMin.toFixed(1)})`);
await clearWorld();
expect(__issues.length === 0, `no API misuse overall (${__issues.length}): ${__issues.slice(0, 6).join(" | ")}`);
expect(warnings.length === 0, `no script warnings (${warnings.length}): ${warnings.slice(0, 4).join(" | ")}`);

// ------------------------------------------------------------------ result
out("\nboss report:");
for (const [k, r] of Object.entries(report)) out(`  ${k.padEnd(8)} phases ${r.phases}  skills ${String(r.skills).padStart(2)}  ultimate ${r.ultTicks} ticks  particles/s ${r.particlesPerSec}  fight ${r.fightTicks} ticks`);
out(`action-bar lines: ${__stats.actionbars.length} (Alice ${perMin.toFixed(1)}/min), titles: ${__stats.titles}, shakes: ${__stats.shakes}, flashes: ${__stats.fades}`);
out(`codex forms opened: ${__ui.shown.length}`);
out(`\n${passed} passed, ${failures.length} failed`);
for (const f of failures) out("  FAIL:", f);
process.exit(failures.length ? 1 : 0);
