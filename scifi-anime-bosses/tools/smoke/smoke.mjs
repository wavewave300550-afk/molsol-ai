// Runtime simulation of the VESPER-0 scripts on the strict mock server.
//   node tools/smoke/smoke.mjs            -> runs every scenario in its own process
//   node tools/smoke/smoke.mjs <scenario> -> runs one scenario (used internally)
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const BUILD = path.join(ROOT, "build");
const SCENARIOS = ["full_fight", "p1_rotation", "threshold_integrity", "reload_resume", "summon_rules_and_weapon"];

function prepare(name) {
  const dir = path.join(BUILD, `smoke-${name}`);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.cpSync(path.join(BUILD, "SAB_VESPER_BP", "scripts"), path.join(dir, "scripts"), { recursive: true });
  fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({ type: "module" }));
  const shim = path.join(dir, "node_modules", "@minecraft", "server");
  fs.mkdirSync(shim, { recursive: true });
  fs.writeFileSync(path.join(shim, "package.json"), JSON.stringify({ name: "@minecraft/server", type: "module", main: "index.js" }));
  fs.writeFileSync(path.join(shim, "index.js"), `export * from ${JSON.stringify(pathToFileURL(path.join(HERE, "mock-server.mjs")).href)};\n`);
  return dir;
}

// seeded RNG so runs are reproducible
let seed = 1234567;
Math.random = () => {
  seed = (seed * 1103515245 + 12345) & 0x7fffffff;
  return seed / 0x7fffffff;
};

const results = [];
function check(cond, msg) {
  results.push([!!cond, msg]);
}

async function load(dir) {
  process.env.SAB_BUILD = BUILD;
  const mock = await import(pathToFileURL(path.join(HERE, "mock-server.mjs")).href);
  await import(pathToFileURL(path.join(dir, "scripts", "main.js")).href);
  mock.__startup();
  return mock;
}

// ------------------------------------------------------------------ bot players
function botStep(mock, p, role, opts) {
  const ents = mock.__entities();
  const boss = ents.find((e) => e.typeId === "sab:vesper_0");
  const now = mock.__now();
  if (!boss) return;
  const censers = ents.filter((e) => e.typeId === "sab:censer");
  const parts = ents.filter((e) => e.typeId === "sab:vesper_part");
  const seraphs = ents.filter((e) => e.typeId === "sab:seraph" && e.getProperty("sab:mode") !== 3);
  const heartOpen = boss._groups.has("sab:hull_open");
  const phase = boss.getProperty("sab:phase");
  let target = boss;
  const ignoreCensers = opts.ignoreRequiemCensers && phase >= 2;
  if (censers.length && !ignoreCensers) target = censers.sort((a, b) => dist(a, p) - dist(b, p))[0];
  else if (heartOpen) target = parts.find((e) => e._groups.has("sab:heart")) ?? boss;
  else if (phase >= 2 && seraphs.length && (role === "melee" ? now % 400 < 260 : now % 400 < 120)) {
    target = seraphs.sort((a, b) => dist(a, p) - dist(b, p))[0];
  } else if (parts.length && role === "ranged") target = parts.find((e) => e._groups.has("sab:prow")) ?? boss;
  const want = role === "melee" ? 2.5 : 14;
  const tl = target.location;
  const dx = tl.x - p._loc.x;
  const dz = tl.z - p._loc.z;
  const d = Math.hypot(dx, dz) || 1;
  const step = Math.max(-0.3, Math.min(0.3, (d - want) * 0.25));
  p._loc.x += (dx / d) * step + Math.sin(now / 17 + (role === "melee" ? 0 : 2)) * 0.05;
  p._loc.z += (dz / d) * step;
  p.setRotation({ x: 0, y: (Math.atan2(-dx, dz) * 180) / Math.PI });
  if (now % 41 === (role === "melee" ? 3 : 20)) p._vel.y = 0.42; // occasional jump
  const every = role === "melee" ? 10 : 16;
  if (now % every !== 0) return;
  const bb = target.getAABB();
  const gap = Math.max(0, Math.hypot(Math.max(0, Math.abs(p._loc.x - bb.center.x) - bb.extent.x),
    Math.max(0, Math.abs(p._loc.z - bb.center.z) - bb.extent.z),
    Math.max(0, Math.abs(p._loc.y + 1.6 - bb.center.y) - bb.extent.y)));
  if (role === "melee" && gap < 3.2) mock.__hit(target, p, 9, "entityAttack");
  else if (role === "ranged" && gap < 40) mock.__hit(target, p, 9, "projectile");
}

function dist(e, p) {
  const a = e.location;
  const b = p.location;
  return Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
}

// ------------------------------------------------------------------ scenarios
async function fullFight(mock) {
  const melee = mock.__addPlayer("Seraphina", { x: 0.5, y: 64, z: 0.5 });
  const archer = mock.__addPlayer("Corvin", { x: 8.5, y: 64, z: 4.5 });
  melee._hand = new mock.ItemStack("sab:astral_psalter", 1);
  const ps = mock.__registries.components["sab:psalter"];
  check(ps && typeof ps.onUse === "function", "Psalter custom component registered (tap / right-click to use)");
  ps.onUse({ source: melee, itemStack: melee._hand });
  check(!!melee._hand, "Psalter kept while the hymn plays");
  let bossSeenAt = -1;
  let deathAt = -1;
  const phaseTimes = {};
  for (let i = 0; i < 16000; i++) {
    mock.__tick();
    const boss = mock.__entities().find((e) => e.typeId === "sab:vesper_0");
    if (boss && bossSeenAt < 0) {
      bossSeenAt = mock.__now();
      check(!melee._hand, "Psalter consumed once VESPER-0 arrives (survival)");
    }
    if (boss) {
      const ph = boss.getProperty("sab:phase");
      if (!(ph in phaseTimes)) phaseTimes[ph] = mock.__now();
      botStep(mock, melee, "melee", { ignoreRequiemCensers: true });
      botStep(mock, archer, "ranged", { ignoreRequiemCensers: true });
    }
    if (!boss && bossSeenAt > 0) {
      deathAt = mock.__now();
      for (let k = 0; k < 60; k++) mock.__tick();
      break;
    }
  }
  const L = mock.__log;
  const acts = new Set((L.props?.["sab:act"] ?? []).map((x) => x[1]));
  const phases = new Set((L.props?.["sab:phase"] ?? []).map((x) => x[1]));
  check(bossSeenAt > 150 && bossSeenAt < 200, `boss descends after the 8 s ritual (spawned at tick ${bossSeenAt})`);
  check(deathAt > 0, `boss defeated (fight length ${((deathAt - bossSeenAt) / 20).toFixed(1)} s)`);
  for (const p of [1, 2, 3]) check(phases.has(p), `phase ${p} reached`);
  const ACT = { arrive: 1, lance_charge: 3, lance_fire: 4, rite: 5, horizon: 6, choir: 7, genuflect: 8, vent_flare: 9,
    pray: 10, stunned: 11, lunge_windup: 12, lunge: 13, anchored: 14, talons: 15, nova_charge: 16, nova_release: 17 };
  const P1_CORE = ["lance_charge", "rite", "horizon", "choir", "genuflect"];
  const seenP1 = P1_CORE.filter((n) => acts.has(ACT[n]));
  check(seenP1.length >= 4, `phase I repertoire used (${seenP1.join(", ")})`);
  for (const [n, id] of Object.entries(ACT)) {
    if (P1_CORE.includes(n) || n === "vent_flare") continue; // every P1 ability is asserted in p1_rotation
    check(acts.has(id), `act ${n} played`);
  }
  const titles = L.titles.map((t) => t[1]).join(" | ");
  for (const t of ["VESPER-0", "VESPERS", "PRAYER BROKEN", "THE FALSE ASCENSION", "REQUIEM", "FALSE BENEDICTION", "HAS FALLEN SILENT"]) {
    check(titles.includes(t), `title shown: ${t}`);
  }
  const sp = L.spawned;
  check((sp["sab:vesper_part"] ?? 0) >= 3, "proxy hitboxes spawned");
  check((sp["sab:cherub"] ?? 0) >= 3, `cherub drones spawned (${sp["sab:cherub"]})`);
  check((sp["sab:plasma_orb"] ?? 0) >= 1, `plasma orbs fired (${sp["sab:plasma_orb"]})`);
  check((sp["sab:censer"] ?? 0) >= 7, `censers spawned for both prayers (${sp["sab:censer"]})`);
  check((sp["sab:seraph"] ?? 0) === 3, `three Seraph rings detached (${sp["sab:seraph"]})`);
  check((sp["sab:hull_plate"] ?? 0) >= 6, `hull plates fell as cover (${sp["sab:hull_plate"]})`);
  check((sp["sab:singularity"] ?? 0) >= 1, "Event Horizon singularities spawned");
  check((sp["sab:lance"] ?? 0) >= 1, "Litany Lance beam spawned");
  const items = L.items.map((x) => x[1]);
  check(items.filter((x) => x === "sab:orison_halo").length >= 2, "an Orison Halo for each participant (first kill)");
  check(items.filter((x) => x === "sab:vesper_alloy").length >= 2, "Vesper Alloy for each participant");
  check(L.xp === 1500, `1500 XP dropped (${L.xp})`);
  const left = mock.__entities().filter((e) => e.typeId.startsWith("sab:"));
  check(left.length === 0, `no add-on entities left after death (${left.map((e) => e.typeId).join(",")})`);
  check(L.music.some((m) => m[2] === "sab.music.vesper_p1") && L.music.some((m) => m[2] === "sab.music.vesper_p2"), "boss music for both phases");
  check(L.fog.some((f) => f[2] === "sab:fog_vesper_p2"), "phase II fog applied");
  check(L.camera.some((c) => c[2] === "minecraft:free") && L.camera.some((c) => c[2] === "clear"), "transformation cinematic camera set and released");
  check((L.effects["regeneration"] ?? 0) > 0, "Dying Star blessing applied regeneration");
  // damage report
  const byCause = {};
  for (const [, , dmg, cause] of L.damage) byCause[cause] = (byCause[cause] ?? 0) + dmg;
  const taken = { [melee.name]: Math.round(melee._taken ?? 0), [archer.name]: Math.round(archer._taken ?? 0) };
  const NAMES = Object.fromEntries(Object.entries(ACT).map(([k, v]) => [v, k]));
  Object.assign(NAMES, { 2: "depart", 18: "unhaloed", 19: "roar" });
  const timeline = (L.props?.["sab:act"] ?? []).filter((a) => a[1] !== 0).map((a) => `${(a[0] / 20).toFixed(1)}s ${NAMES[a[1]] ?? a[1]}`);
  const titlesSeen = L.titles.map((t) => `${(t[0] / 20).toFixed(1)}s ${t[1]}`);
  const players = [melee, archer].map((p) => `${p.name}@${Math.round(p.location.x)},${Math.round(p.location.z)}`);
  return { titlesSeen, players, timeline, phaseTimes, fightSeconds: (deathAt - bossSeenAt) / 20, damageTaken: taken, byCause,
    particles: Object.keys(L.particles).length, sounds: Object.keys(L.sounds).length };
}

async function reloadResume(mock) {
  const p = mock.__addPlayer("Lyra", { x: 0, y: 64, z: 12 });
  // a boss saved mid phase II (as if the world was reloaded)
  const boss = mock.__addEntity("sab:vesper_0", { x: 0, y: 70, z: 0 });
  boss.setProperty("sab:phase", 2);
  boss.setProperty("sab:skin", 1);
  boss.setProperty("sab:limbs", true);
  boss.setProperty("sab:rings", false);
  boss.setProperty("sab:plates", false);
  boss.setDynamicProperty("sab:arena", JSON.stringify({ x: 0, y: 64, z: 0 }));
  boss.setDynamicProperty("sab:flags", JSON.stringify({ prayers: 1, participants: [] }));
  boss._health._value = 420;
  // a second boss saved mid-transformation in another place
  const b2 = mock.__addEntity("sab:vesper_0", { x: 400, y: 80, z: 400 });
  b2.setProperty("sab:phase", 1);
  b2.setDynamicProperty("sab:arena", JSON.stringify({ x: 400, y: 64, z: 400 }));
  // orphaned helpers from the previous session must be cleaned up
  mock.__addEntity("sab:cherub", { x: 5, y: 70, z: 5 }).setDynamicProperty("sab:owner", "dead-boss");
  mock.__addEntity("sab:hull_plate", { x: 20, y: 64, z: 20 }).setDynamicProperty("sab:owner", "dead-boss");
  const strayHalo = mock.__addEntity("sab:orison_halo", { x: 3, y: 66, z: 3 });
  // ... but the live boss's landed cover plate must be adopted again (kept out of the nova's line of sight here)
  const plate = mock.__addEntity("sab:hull_plate", { x: -30, y: 64, z: -30 });
  plate.setDynamicProperty("sab:owner", boss.id);
  for (let i = 0; i < 900; i++) {
    mock.__tick();
    botStep(mock, p, "melee", {});
  }
  check((mock.__log.spawned["sab:seraph"] ?? 0) === 6, "Seraph rings recreated for both resumed phase II bosses");
  check((mock.__log.props["sab:phase"] ?? []).some((x) => x[1] === 2), "boss saved mid-transformation settles into phase II");
  check(!b2.isValid && mock.__log.items.some((x) => x[1] === "sab:astral_psalter"),
    "an unattended boss departs after 30 s and refunds the Psalter");
  check(boss.isValid, "the attended boss stays");
  check(!mock.__entities().some((e) => e.getDynamicProperty("sab:owner") === "dead-boss"), "orphaned helpers removed");
  check(plate.isValid, "the live boss's landed cover plate survives the reload (re-adopted)");
  check(!strayHalo.isValid, "an Orison Halo left mid-flight by a reload is removed");
  const acts = new Set((mock.__log.props?.["sab:act"] ?? []).map((x) => x[1]));
  check([12, 15, 16, 6].some((a) => acts.has(a)), "resumed boss keeps fighting with phase II abilities");
  return { acts: [...acts] };
}

async function p1Rotation(mock) {
  // three cautious players chip at VESPER-0 for three minutes: every phase I ability must cycle
  const ps = [mock.__addPlayer("Ira", { x: 0.5, y: 64, z: 0.5 }), mock.__addPlayer("Oda", { x: 9.5, y: 64, z: -6.5 }),
    mock.__addPlayer("Tam", { x: -8.5, y: 64, z: 7.5 })];
  ps[0]._hand = new mock.ItemStack("sab:astral_psalter", 1);
  mock.__registries.components["sab:psalter"].onUse({ source: ps[0], itemStack: ps[0]._hand });
  for (let i = 0; i < 3800; i++) {
    mock.__tick();
    const boss = mock.__entities().find((e) => e.typeId === "sab:vesper_0");
    if (boss && i % 20 === 0) for (const p of ps) mock.__hit(boss, p, 1, "projectile");
    if (boss) for (const [k, p] of ps.entries()) {
      const b = boss.location;
      const a = (mock.__now() / 60 + k * 2.1);
      p._loc.x = b.x + Math.cos(a) * 12;
      p._loc.z = b.z + Math.sin(a) * 12;
    }
  }
  const acts = (mock.__log.props?.["sab:act"] ?? []).map((x) => x[1]);
  const count = (id) => acts.filter((a) => a === id).length;
  check(count(9) >= 1, `vent flare warning played (${count(9)}x)`);
  check(mock.__log.damage.some((d) => d[3] === "fire"), "vent burst / scorch fire damage dealt");
  check(count(3) >= 2 && count(5) >= 2 && count(6) >= 2 && count(7) >= 1 && count(8) >= 2, `P1 abilities rotate (lance ${count(3)}, rite ${count(5)}, horizon ${count(6)}, choir ${count(7)}, genuflect ${count(8)})`);
  check(!(mock.__log.props?.["sab:phase"] ?? []).some((x) => x[1] > 0), "chip damage alone does not end phase I in 3 minutes");
  const boss = mock.__entities().find((e) => e.typeId === "sab:vesper_0");
  return { hp: boss ? Math.round(boss._health.currentValue) : -1, lance: count(3), rite: count(5), horizon: count(6),
    choir: count(7), genuflect: count(8) };
}

async function summonRulesAndWeapon(mock) {
  const ps = mock.__registries.components["sab:psalter"];
  const nether = mock.__addPlayer("Nyx", { x: 0, y: 64, z: 0 }, "minecraft:nether");
  nether._hand = new mock.ItemStack("sab:astral_psalter", 1);
  ps.onUse({ source: nether, itemStack: nether._hand });
  check(!!nether._hand, "Psalter refused (and kept) in the Nether");
  check(mock.__log.chat.some((c) => c[1] === "Nyx" && /\[VESPER-0\].*Overworld/.test(c[2])), "the refusal reason is also posted in chat");
  const roofed = mock.__addPlayer("Moss", { x: 100.5, y: 64, z: 100.5 });
  roofed._hand = new mock.ItemStack("sab:astral_psalter", 1);
  mock.terrain.boxes.push({ min: { x: 95, y: 70, z: 95 }, max: { x: 106, y: 71, z: 106 } });
  ps.onUse({ source: roofed, itemStack: roofed._hand });
  check(!!roofed._hand, "Psalter refused (and kept) under a roof");
  for (let i = 0; i < 41; i++) mock.__tick();
  check(mock.__log.actionbar.some((a) => a[1] === "Moss" && /open sky/.test(a[2])),
    "holding the Psalter under a roof shows why it can't be used here");
  mock.world._difficulty = "Peaceful";
  const calm = mock.__addPlayer("Wren", { x: -200.5, y: 64, z: -200.5 });
  calm._hand = new mock.ItemStack("sab:astral_psalter", 1);
  ps.onUse({ source: calm, itemStack: calm._hand });
  check(!!calm._hand, "Psalter refused (and kept) in Peaceful");
  mock.world._difficulty = "Normal";
  calm._mode = "Creative";
  ps.onUse({ source: calm, itemStack: calm._hand });
  check(!!calm._hand, "creative players keep their Psalter");
  // a ritual whose site unloads before the end fizzles and costs nothing
  const wander = mock.__addPlayer("Rook", { x: 900.5, y: 64, z: 900.5 });
  wander._hand = new mock.ItemStack("sab:astral_psalter", 1);
  ps.onUse({ source: wander, itemStack: wander._hand });
  mock.world.getDimension("minecraft:overworld")._unloaded.add(`${Math.floor(900.5 / 16)},${Math.floor(900.5 / 16)}`);
  for (let i = 0; i < 300; i++) mock.__tick();
  check(mock.__entities().filter((e) => e.typeId === "sab:vesper_0").length === 1, "exactly one boss from the valid ritual");
  check(mock.__log.chat.some((c) => c[1] === "Wren" && /Creative/.test(c[2])),
    "a boss with only Creative-mode players nearby explains that it ignores them");
  check(!!wander._hand && !mock.__entities().some((e) => e.typeId === "sab:vesper_0" && Math.abs(e.location.x - 900.5) < 64),
    "a ritual whose site unloaded fizzles and keeps the Psalter");
  // Orison Halo
  const hero = mock.__addPlayer("Ash", { x: 300.5, y: 64, z: 300.5 });
  hero._hand = new mock.ItemStack("sab:orison_halo", 1);
  hero.setRotation({ x: 0, y: 0 });
  const zombie = mock.__addEntity("minecraft:zombie", { x: 300.5, y: 64, z: 308.5 });
  const halo = mock.__registries.components["sab:orison"];
  check(halo && typeof halo.onUse === "function", "Orison Halo custom component registered");
  halo.onUse({ source: hero, itemStack: hero._hand });
  halo.onUse({ source: hero, itemStack: hero._hand });
  for (let i = 0; i < 60; i++) mock.__tick();
  check(zombie._health.currentValue < 20, `thrown halo damaged a mob on the way out/back (hp ${zombie._health.currentValue})`);
  check(mock.__log.actionbar.some((a) => a[1] === "Ash" && /Orison Halo/.test(a[2])), "picking up the Orison Halo explains how to throw it");
  check(hero.getItemCooldown("sab:orison") === 0 && hero._cooldowns["sab:orison"] > 0, "halo cooldown was applied");
  check(hero._hand && hero._hand.getComponent("minecraft:durability").damage === 2, "one throw costs 2 durability (cooldown blocked the second)");
  check(!mock.__entities().some((e) => e.typeId === "sab:orison_halo"), "thrown halo returned and despawned");
  // commands
  const cmd = mock.__registries.commands["sab:vesper"];
  const res = cmd.cb({ sourceEntity: hero, sourceType: "Entity" }, "status");
  check(res && res.status === 0 && /VESPER-0/.test(res.message), "/sab:vesper status reports the active boss");
  const cin = mock.__registries.commands["sab:vesper_cinematics"];
  cin.cb({ sourceType: "Server" }, "off");
  mock.__tick();
  check(mock.world.getDynamicProperty("sab:cinematics") === false, "/sab:vesper_cinematics off persists the setting");
  cmd.cb({ sourceEntity: hero, sourceType: "Entity" }, "despawn");
  for (let i = 0; i < 5; i++) mock.__tick();
  check(!mock.__entities().some((e) => e.typeId === "sab:vesper_0"), "/sab:vesper despawn removes the boss");
  return {};
}

async function thresholdIntegrity(mock) {
  // eight players hammer VESPER-0 with simultaneous hits every tick: every phase threshold must still be hit
  // exactly (no damage may leak past a pending threshold), and the fight must run prayer -> transform -> requiem
  const ps = [];
  for (let k = 0; k < 8; k++) ps.push(mock.__addPlayer(`Anvil${k}`, { x: 0.5 + k * 2, y: 64, z: 6.5 }));
  ps[0]._hand = new mock.ItemStack("sab:astral_psalter", 1);
  mock.__registries.components["sab:psalter"].onUse({ source: ps[0], itemStack: ps[0]._hand });
  const seen = [];
  let lastAct = -1;
  let lastPhase = -1;
  let gone = false;
  for (let i = 0; i < 14000 && !gone; i++) {
    mock.__tick();
    const boss = mock.__entities().find((e) => e.typeId === "sab:vesper_0");
    if (!boss) {
      gone = i > 400;
      continue;
    }
    const hp = Math.round(boss._health.currentValue * 10) / 10;
    const act = boss.getProperty("sab:act");
    const phase = boss.getProperty("sab:phase");
    if (act === 10 && lastAct !== 10) seen.push(`pray@${hp}`);
    if (phase !== lastPhase) seen.push(`phase${phase}@${hp}`);
    lastAct = act;
    lastPhase = phase;
    for (const p of ps) {
      p._loc.x = boss.location.x + 4;
      p._loc.z = boss.location.z + 4;
      mock.__hit(boss, p, 400, "entityAttack");
    }
  }
  const s = seen.join(" ");
  check(seen.includes("pray@900"), `75 % prayer starts exactly at 900 HP (${s})`);
  check(seen.includes("phase1@600"), "transformation starts exactly at 600 HP");
  check(seen.filter((x) => x.startsWith("pray@")).length === 2 && seen.includes("pray@300"), "Requiem starts exactly at 300 HP");
  const order = seen.filter((x) => x.startsWith("phase")).map((x) => Number(x[5]));
  check(JSON.stringify(order) === "[0,1,2,3]", `phases in order (${order})`);
  check(gone, "the boss still dies at the end");
  return { seen };
}

async function runOne(name) {
  const dir = prepare(name);
  const mock = await load(dir);
  let info = {};
  try {
    if (name === "full_fight") info = await fullFight(mock);
    else if (name === "p1_rotation") info = await p1Rotation(mock);
    else if (name === "reload_resume") info = await reloadResume(mock);
    else if (name === "threshold_integrity") info = await thresholdIntegrity(mock);
    else info = await summonRulesAndWeapon(mock);
  } catch (e) {
    check(false, `scenario threw: ${e.stack}`);
  }
  for (const msg of mock.__issues) check(false, `mock: ${msg}`);
  const bad = mock.__log.warnings.filter((w) => /crash|failed|ineffective/.test(w));
  for (const w of bad) check(false, `script warning: ${w}`);
  process.stdout.write(JSON.stringify({ name, results, info }) + "\n");
}

async function main() {
  const one = process.argv[2];
  if (one) return runOne(one);
  let failed = 0;
  let total = 0;
  for (const name of SCENARIOS) {
    const r = spawnSync(process.execPath, [fileURLToPath(import.meta.url), name], { encoding: "utf8", env: { ...process.env } });
    const line = (r.stdout || "").trim().split("\n").pop();
    let data;
    try {
      data = JSON.parse(line);
    } catch {
      console.log(`scenario ${name} crashed:\n${r.stdout}\n${r.stderr}`);
      failed++;
      continue;
    }
    console.log(`\n== ${name}`);
    for (const [okk, msg] of data.results) {
      total++;
      if (!okk) failed++;
      console.log(`  ${okk ? "PASS" : "FAIL"}  ${msg}`);
    }
    if (data.info && Object.keys(data.info).length) console.log("  info:", JSON.stringify(data.info));
  }
  console.log(`\n${total - failed}/${total} checks passed`);
  process.exit(failed ? 1 : 0);
}

main();
