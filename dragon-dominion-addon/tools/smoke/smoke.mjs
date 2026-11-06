// End-to-end smoke tests: the real behavior-pack scripts running against tools/smoke/mock-server.mjs.
//   npm run smoke
// Each scenario clears the mock world. Checks fight logic, not rendering and not vanilla AI.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const ADDON = path.join(ROOT, "addon");
const SCRIPTS = path.join(ADDON, "behavior_packs", "dragon_dominion", "scripts");
process.env.DD_ADDON = ADDON;

let seed = 1234;
Math.random = () => {
  seed = (seed * 1103515245 + 12345) % 2147483648;
  return seed / 2147483648;
};

const RUN = path.join(HERE, ".run");
fs.rmSync(RUN, { recursive: true, force: true });
fs.mkdirSync(path.join(RUN, "node_modules", "@minecraft", "server"), { recursive: true });
fs.writeFileSync(path.join(RUN, "package.json"), JSON.stringify({ type: "module" }));
fs.writeFileSync(path.join(RUN, "node_modules", "@minecraft", "server", "package.json"),
  JSON.stringify({ name: "@minecraft/server", type: "module", main: "index.js" }));
fs.writeFileSync(path.join(RUN, "node_modules", "@minecraft", "server", "index.js"),
  `export * from ${JSON.stringify(pathToFileURL(path.join(HERE, "mock-server.mjs")).href)};`);
fs.cpSync(SCRIPTS, RUN, { recursive: true });

const M = await import(pathToFileURL(path.join(RUN, "node_modules", "@minecraft", "server", "index.js")).href);
await import(pathToFileURL(path.join(RUN, "main.js")).href);
const REG = await import(pathToFileURL(path.join(RUN, "core", "registry.js")).href);
const COMBAT = await import(pathToFileURL(path.join(RUN, "core", "combat.js")).href);
const { CONFIG } = await import(pathToFileURL(path.join(RUN, "dragons", "gharvok", "config.js")).href);
const { TIMINGS, ANIM } = await import(pathToFileURL(path.join(RUN, "dragons", "gharvok", "timings.js")).href);
const SUMMON = await import(pathToFileURL(path.join(RUN, "dragons", "gharvok", "summon.js")).href);

let pass = 0;
let fail = 0;
const check = (cond, msg) => {
  if (cond) pass++;
  else {
    fail++;
    console.log("  FAIL:", msg);
  }
};
const section = (n) => console.log(`- ${n}`);
const L = M.__log;
const tick = (n = 1) => M.__tick(n);
const now = () => M.__now();
const sec = (s) => Math.round(s * 20);
const A = CONFIG.attacks;
const ctl = (e) => REG.controllerOf(e);
const dmgTo = (t, t0) => L.damage.filter((d) => d.target === t && d.tick >= t0);
const animSet = (e, t0) => L.props.filter((p) => p.entity === e && p.key === "dragon_dominion:anim" && p.tick >= t0).map((p) => p.value);
const evts = (e, t0) => L.events.filter((x) => x.entity === e && x.tick >= t0).map((x) => x.name);
const heal = (p) => (p.health.currentValue = p.health.effectiveMax);

function fresh() {
  M.__clearWorld();
  tick(2); // let the registry drop invalid controllers
  COMBAT.__resetHitClock();
}
/** Spawn a boss in combat with a target, phase forced, all cooldowns cleared, nothing running. */
function arena({ phase = 1, players = [[0, 64, 6]], yaw = 0 } = {}) {
  fresh();
  const e = M.__summon({ x: 0.5, y: 64, z: 0.5 }, yaw);
  const ps = players.map((p, i) => M.__spawnPlayer(`P${i}`, { x: p[0], y: p[1], z: p[2] }));
  for (const p of ps) p.health.effectiveMax = p.health.currentValue = 1000; // big HP pool for measuring
  const c = ctl(e);
  tick(1);
  c.engage(ps[0]);
  c.endMove(true);
  c.queued = [];
  c.phase = phase;
  c.prop("phase", phase);
  c.save("phase", phase);
  c.cool = {};
  c.history = [];
  c.nextDecision = now() + 99999; // tests start moves explicitly
  c.target = ps[0];
  return { e, c, ps };
}
function runMove(c, name, maxTicks = 400) {
  c.startMove(name);
  let n = 0;
  while (c.move && n < maxTicks) {
    tick(1);
    n++;
  }
  return n;
}

// ======================================================================================= static facts
section("config and timings");
{
  const ent = M.DEFS.get("dragon_dominion:gharvok");
  for (let n = 1; n <= 4; n++) {
    const g = ent.component_groups[`dragon_dominion:hp_${n}`]["minecraft:health"];
    check(g.max === CONFIG.health.base + CONFIG.health.perExtraPlayer * (n - 1), `HP tier ${n} matches config (${g.max})`);
  }
  check(ent.components["minecraft:boss"] !== undefined, "minecraft:boss present (boss bar)");
  check(ent.description.is_summonable === true, "/summon dragon_dominion:gharvok enabled");
  check(!fs.existsSync(path.join(ADDON, "behavior_packs", "dragon_dominion", "spawn_rules")), "no natural spawn rules");
  check(TIMINGS.claw_combo.hits.length === 2, "twin claw has two hit frames");
}

// ======================================================================================= summoning
section("summon: Cliff Sigil ritual, duplicate guard, spot check");
{
  fresh();
  const p = M.__spawnPlayer("S", { x: 0.5, y: 64, z: 0.5 });
  p.inv.container.items[0] = new M.ItemStack("dragon_dominion:cliff_sigil", 2);
  M.world.afterEvents.itemUse.fire({ source: p, itemStack: p.inv.container.items[0] });
  check(p.inv.container.items[0].amount === 1, "one sigil consumed in survival");
  check(L.particles.some((x) => x.id === "dragon_dominion:summon_pillar" && x.tick >= now() - 1), "summoning effect plays");
  tick(sec(3) + 2);
  const bosses = M.__dim.getEntities({ type: "dragon_dominion:gharvok" });
  check(bosses.length === 1, "ritual spawns exactly one Gharvok");
  check(bosses.length && Math.abs(Math.hypot(bosses[0].location.x - 0.5, bosses[0].location.z - 0.5) - CONFIG.summon.distance) < 4,
    "spawned in front of the player at the configured distance");
  check(ctl(bosses[0]) !== undefined, "registry adopted the summoned boss");
  tick(sec(CONFIG.summon.cooldown) + 1);
  const r = SUMMON.useSigil(p);
  check(r === "duplicate", `second sigil refused while Gharvok lives (${r})`);
  check(p.inv.container.items[0]?.amount === 1, "refused sigil is not consumed");
  // blocked terrain: a wall all around -> no spot
  fresh();
  M.__solids.push({ min: { x: -40, y: 64, z: -40 }, max: { x: 40, y: 75, z: 40 } });
  const q = M.__spawnPlayer("Q", { x: 0.5, y: 75, z: 0.5 });
  M.__solids.push({ min: { x: -40, y: 75, z: 4 }, max: { x: 40, y: 95, z: 40 } });
  M.__solids.push({ min: { x: -40, y: 75, z: -40 }, max: { x: 40, y: 95, z: -3 } });
  M.__solids.push({ min: { x: -40, y: 75, z: -3 }, max: { x: -3, y: 95, z: 4 } });
  M.__solids.push({ min: { x: 4, y: 75, z: -3 }, max: { x: 40, y: 95, z: 4 } });
  const rr = SUMMON.useSigil(q);
  check(rr === "no_spot", `cramped space refuses to summon (${rr})`);
}

// ======================================================================================= detection, HP scaling
section("detection, alert roar, multiplayer HP scaling fixed at fight start");
{
  fresh();
  const e = M.__summon({ x: 0.5, y: 64, z: 0.5 });
  const c = ctl(e);
  tick(5);
  check(c.state === "IDLE" && !c.fight, "starts idle, not in a fight");
  check(e.groups.has("dragon_dominion:roam"), "vanilla roam AI while idle");
  const far = M.__spawnPlayer("Far", { x: 0.5, y: 64, z: 60 });
  tick(30);
  check(c.state === "IDLE", "a player 60 blocks away does not wake it");
  const t0 = now();
  const p1 = M.__spawnPlayer("A", { x: 0.5, y: 64, z: 18 });
  const p2 = M.__spawnPlayer("B", { x: 5, y: 64, z: 20 });
  M.__spawnPlayer("Creative", { x: 2, y: 64, z: 15 }, "Creative");
  tick(12);
  check(c.fight && c.state === "ALERT", "players inside the detection radius trigger ALERT");
  check(animSet(e, t0).includes(ANIM.roar), "alert roar animation");
  check(e.health.effectiveMax === 620 && e.health.currentValue === 620, `2 hunters -> 620 HP (${e.health.effectiveMax})`);
  check(e.groups.has("dragon_dominion:scripted") && !e.groups.has("dragon_dominion:roam"), "script takes over movement in combat");
  M.__spawnPlayer("Late", { x: -4, y: 64, z: 12 });
  tick(sec(4));
  check(e.health.effectiveMax === 620, "a player joining mid-fight does not change max HP");
  check(c.state === "PURSUE" || c.move, "after the roar it pursues / attacks");
  void far;
  void p1;
  void p2;
}

// ======================================================================================= skill 02 twin claw
section("Skill 02 Twin Claw: two swings, separate hit windows, once each");
{
  const { c, ps } = arena({ players: [[0.5, 64, 4.5]] });
  const t0 = now();
  runMove(c, "twin_claw");
  const d = dmgTo(ps[0], t0);
  check(d.length === 2, `two hits (${d.length})`);
  if (d.length === 2) {
    check(Math.abs(d[0].tick - t0 - sec(TIMINGS.claw_combo.hits[0])) <= 2, "first swing lands on its frame");
    check(Math.abs(d[1].tick - t0 - sec(TIMINGS.claw_combo.hits[1])) <= 2, "second swing lands on its frame");
    check(d.every((x) => x.amount >= 6 && x.amount <= 8), "6-8 damage per swing");
  }
  check(c.cool.twin_claw > now(), "cooldown set");
  const b = arena({ players: [[0.5, 64, -5]] });
  const t1 = now();
  runMove(b.c, "twin_claw");
  check(dmgTo(b.ps[0], t1).length === 0, "player behind is not clawed");
}

// ======================================================================================= skill 01 charge
section("Skill 01 Crushing Charge: commit, trample, knockback, wall stun");
{
  const { e, c, ps } = arena({ players: [[0.5, 64, 16]] });
  const t0 = now();
  c.startMove("crushing_charge");
  tick(sec(A.crushing_charge.lockAt) + 1);
  const locked = c.move.yaw;
  ps[0].location.x = 10; // dodge sideways after the commit
  tick(sec(0.3));
  check(c.move.yaw === locked, "direction does not follow the target after commit");
  ps[0].location.x = 0.5;
  let n = 0;
  while (c.move && n++ < 200) tick(1);
  const d = dmgTo(ps[0], t0);
  check(d.length === 1 && d[0].amount === 10, `charge hits once for 10 (${d.map((x) => x.amount)})`);
  check(L.knockback.some((k) => k.target === ps[0] && k.tick >= t0 && Math.hypot(k.h.x, k.h.z) > 2), "strong knockback");
  check(e.location.z > 10, `the dragon actually travelled (${e.location.z.toFixed(1)})`);

  // wall
  const w = arena({ players: [[0.5, 64, 22]] });
  M.__solids.push({ min: { x: -6, y: 64, z: 12 }, max: { x: 7, y: 70, z: 14 } });
  const t1 = now();
  w.c.startMove("crushing_charge");
  let k = 0;
  while (k++ < 120 && !(w.c.move && w.c.move.mv.name === "charge_impact")) tick(1);
  check(w.c.move?.mv.name === "charge_impact", "hitting a wall interrupts the charge");
  check(w.c.state === "STAGGERED", "and stuns Gharvok");
  check(w.e.location.z < 12, "the dragon stops before the wall (no clipping)");
  check(w.c.skullPts >= A.crushing_charge.skullDamageOnWall, `wall impact damages the crownshield (${w.c.skullPts})`);
  check(animSet(w.e, t1).includes(ANIM.charge_impact), "charge_impact animation");
  const stunStart = now();
  while (w.c.move && w.c.move.mv.name === "charge_impact") tick(1);
  const stun = (now() - stunStart) / 20;
  check(stun >= 2.5, `long stun window (${stun.toFixed(1)} s)`);
  check(L.particles.some((x) => x.id === "dragon_dominion:daze_stars" && x.tick >= t1), "daze effect");
}

// ======================================================================================= skill 03 tail
section("Skill 03 Rudder Sweep: sides and rear, not the front");
{
  const { c, ps } = arena({ players: [[0.5, 64, -5], [6, 64, 0.5], [0.5, 64, 5]] });
  const t0 = now();
  runMove(c, "rudder_sweep");
  check(dmgTo(ps[0], t0).length === 1 && dmgTo(ps[0], t0)[0].amount === 8, "player behind takes 8");
  check(dmgTo(ps[1], t0).length === 1, "player beside is hit");
  check(dmgTo(ps[2], t0).length === 0, "player in front is safe");
  const d = dmgTo(ps[0], t0)[0];
  check(d && d.tick - t0 >= sec(TIMINGS.tail_sweep.hit_start) - 1, "no damage during the telegraph");
}

// ======================================================================================= skill 04 wing pressure
section("Skill 04 Wing Pressure: frontal gust, light damage, big knockback");
{
  const { c, ps } = arena({ phase: 2, players: [[0.5, 64, 7], [0.5, 64, -3]] });
  const t0 = now();
  runMove(c, "wing_pressure");
  const d = dmgTo(ps[0], t0);
  check(d.length === 1 && d[0].amount >= 2 && d[0].amount <= 4, `2-4 damage (${d.map((x) => x.amount)})`);
  check(Math.abs(d[0]?.tick - t0 - sec(TIMINGS.wing_pressure.gust)) <= 1, "gust on its frame");
  check(L.knockback.some((k) => k.target === ps[0] && k.tick >= t0 && Math.hypot(k.h.x, k.h.z) >= 2.0), "strong knockback");
  check(dmgTo(ps[1], t0).length === 0 && L.knockback.some((k) => k.target === ps[1] && k.tick >= t0), "close player behind is pushed, not damaged");
  check(L.particles.some((x) => x.id === "dragon_dominion:wing_gust" && x.tick >= t0), "wind effect");
}

// ======================================================================================= skill 05 cliff dive
section("Skill 05 Cliff Dive: takeoff, marked landing, dive, shockwave, back to ground");
{
  const { e, c, ps } = arena({ phase: 2, players: [[0.5, 64, 15]] });
  const t0 = now();
  c.startMove("cliff_dive");
  let maxY = 0;
  let firstMark;
  let n = 0;
  while (c.move && n++ < 400) {
    tick(1);
    maxY = Math.max(maxY, e.location.y);
    if (firstMark === undefined && L.particles.some((x) => x.id === "dragon_dominion:warning_ring" && x.tick >= t0)) firstMark = now();
  }
  const d = dmgTo(ps[0], t0);
  check(maxY >= 64 + A.cliff_dive.height - 0.5, `rises ~${A.cliff_dive.height} blocks (${(maxY - 64).toFixed(1)})`);
  check(evts(e, t0).includes("dragon_dominion:to_air") && evts(e, t0).includes("dragon_dominion:to_ground"), "gravity off in the air, back on after");
  check(d.length === 1 && d[0].amount === A.cliff_dive.damage, `landing hits for 12 (${d.map((x) => x.amount)})`);
  if (d.length && firstMark) check((d[0].tick - firstMark) / 20 >= 0.9, `landing zone marked ${((d[0].tick - firstMark) / 20).toFixed(2)} s before impact`);
  check(Math.abs(e.location.y - 64) < 0.01, "ends standing on the ground");
  check(c.flightCode === 0 && !c.inAir, "flight state reset");
  check(animSet(e, t0).includes(ANIM.takeoff) && animSet(e, t0).includes(ANIM.cliff_dive) && animSet(e, t0).includes(ANIM.landing), "takeoff / dive / landing animations");
  // a player who runs out of the marked zone takes no damage
  const b = arena({ phase: 2, players: [[0.5, 64, 15]] });
  const t1 = now();
  b.c.startMove("cliff_dive");
  let m = 0;
  while (b.c.move && m++ < 400) {
    tick(1);
    if (b.c.move?.stage === "dive") b.ps[0].location.x = 12;
  }
  check(dmgTo(b.ps[0], t1).length === 0, "dodging out of the marked zone avoids all damage");
  // no sky: refuses to start / aborts safely
  const r = arena({ phase: 2, players: [[0.5, 64, 15]] });
  M.__solids.push({ min: { x: -20, y: 70, z: -20 }, max: { x: 20, y: 71, z: 20 } });
  r.c.startMove("cliff_dive");
  let q = 0;
  while (r.c.move && q++ < 400) tick(1);
  check(Math.abs(r.e.location.y - 64) < 0.01 && !r.c.inAir, "under a low ceiling it lands safely instead of clipping");
}

// ======================================================================================= skill 06 skullbreaker
section("Skill 06 Skullbreaker: warning, core damage, jumpable shockwave, long recovery");
{
  const { c, ps } = arena({ phase: 3, players: [[0.5, 64, 5], [0.5, 64, 19], [7, 64, 5]] });
  ps[2].isOnGround = false; // jumping
  const t0 = now();
  const len = runMove(c, "skullbreaker");
  const core = dmgTo(ps[0], t0);
  check(core.length >= 1 && core[0].amount >= 12 && core[0].amount <= 14, `core hit 12-14 (${core.map((x) => x.amount)})`);
  check(Math.abs(core[0]?.tick - t0 - sec(TIMINGS.skullbreaker.impact)) <= 1, "impact on the slam frame");
  const warn = L.particles.filter((x) => x.id === "dragon_dominion:warning_ring" && x.tick >= t0);
  check(warn.length > 0 && (core[0]?.tick - warn[0]?.tick) / 20 >= 0.8, `impact zone warned before the slam (${warn.length} marks)`);
  check(dmgTo(ps[1], t0).length === 0, "player beyond the wave is safe");
  check(dmgTo(ps[2], t0).length === 0, "jumping over the wave avoids it");
  const waver = arena({ phase: 3, players: [[0.5, 64, 25], [7, 64, 5]] });
  const t2 = now();
  runMove(waver.c, "skullbreaker");
  check(dmgTo(waver.ps[1], t2).length === 1 && dmgTo(waver.ps[1], t2)[0].amount === A.skullbreaker.waveDamage, `grounded player in the wave takes wave damage (${dmgTo(waver.ps[1], t2).map((x) => x.amount)})`);
  check(len / 20 >= TIMINGS.skullbreaker.length + A.skullbreaker.extraRecovery - 0.1, `significant recovery (${(len / 20).toFixed(1)} s total)`);
}

// ======================================================================================= phases
section("phases: thresholds, once each, attack gating");
{
  const { e, c, ps } = arena({ players: [[0.5, 64, 6]] });
  c.nextDecision = now();
  const hit = (n) => {
    for (let i = 0; i < n; i++) {
      e.applyDamage(20, { cause: "entityAttack", damagingEntity: ps[0] });
      tick(1);
    }
  };
  const max = e.health.effectiveMax;
  const tt = L.titles.length;
  hit(Math.ceil((max * 0.31) / 20));
  check(c.phase === 2 && e.props["dragon_dominion:phase"] === 2, "below 70 % -> phase II");
  hit(2);
  check(c.phase === 2, "stays phase II");
  const p2titles = L.titles.slice(tt).filter((t) => t.text.includes("Phase II") && !t.text.includes("III")).length;
  check(p2titles === 1, `phase II announced once (${p2titles})`);
  hit(Math.ceil((max * 0.36) / 20));
  check(c.phase === 3, "below 35 % -> phase III");
  check(c.queued.includes("roar") || animSet(e, 0).includes(ANIM.roar), "transition roar queued");
  // gating by simulation: which attacks does each phase choose?
  const seen = { 1: new Set(), 2: new Set(), 3: new Set() };
  for (const ph of [1, 2, 3]) {
    for (const [x, z] of [[0.5, 4], [0.5, 8], [0.5, 15], [0.5, 22], [0.5, -5], [6, 0.5]]) {
      const a = arena({ phase: ph, players: [[x, 64, z]] });
      for (let i = 0; i < 25; i++) {
        a.c.cool = {};
        a.c.history = [];
        const pick = a.c.chooseAttack(Math.hypot(x - 0.5, z - 0.5), Math.abs(require_rel(a.c, x, z)));
        if (pick) seen[ph].add(pick);
      }
    }
  }
  check(!seen[1].has("wing_pressure") && !seen[1].has("cliff_dive") && !seen[1].has("skullbreaker"), `phase I: ground set only (${[...seen[1]]})`);
  check(["twin_claw", "crushing_charge", "rudder_sweep"].every((a) => seen[1].has(a)), "phase I uses claw, charge and sweep");
  check(seen[2].has("wing_pressure") && seen[2].has("cliff_dive") && !seen[2].has("skullbreaker"), `phase II adds gust and dive (${[...seen[2]]})`);
  check(seen[3].has("skullbreaker"), `phase III adds Skullbreaker (${[...seen[3]]})`);
}
function require_rel(c, x, z) {
  const o = c.pos();
  let d = (Math.atan2(-(x - o.x), z - o.z) * 180) / Math.PI - c.yaw;
  d = ((d + 540) % 360) - 180;
  return d;
}

// ======================================================================================= no repeats
section("attack variety: no immediate repeats in a long fight");
{
  const { c, ps } = arena({ phase: 3, players: [[0.5, 64, 6]] });
  c.nextDecision = now();
  const picks = [];
  for (let i = 0; i < 120; i++) {
    c.cool = {};
    const p = c.chooseAttack(5.5, 0);
    if (p) {
      picks.push(p);
      c.history.push(p);
      if (c.history.length > 3) c.history.shift();
    }
  }
  let repeats = 0;
  for (let i = 1; i < picks.length; i++) if (picks[i] === picks[i - 1]) repeats++;
  check(repeats / picks.length < 0.2, `repeat rate ${(100 * repeats / picks.length).toFixed(0)} %`);
  void ps;
}

// ======================================================================================= skull fracture
section("skull fracture: head hits in vulnerable windows, visible states, gameplay effects");
{
  const { e, c, ps } = arena({ players: [[0.5, 64, 4.5]] });
  c.tickCombat = function () {
    if (this.move) this.runMove();
    return true;
  }; // freeze the brain: this section measures damage rules only
  // body-side hits (player at the flank) do not fracture
  ps[0].location = { x: 5, y: 64, z: -1 };
  for (let i = 0; i < 5; i++) {
    e.applyDamage(10, { cause: "entityAttack", damagingEntity: ps[0] });
    tick(10);
  }
  check(c.skullPts === 0, "flank hits do not damage the crown");
  ps[0].location = { x: 0.5, y: 64, z: 4.5 };
  e.applyDamage(10, { cause: "entityAttack", damagingEntity: ps[0] });
  tick(1);
  check(Math.abs(c.skullPts - 10 * CONFIG.skull.headRate) < 0.01, `head hit outside a window: ${CONFIG.skull.headRate} pts/dmg`);
  c.startMove("exhausted");
  const before = c.skullPts;
  e.applyDamage(10, { cause: "entityAttack", damagingEntity: ps[0] });
  tick(1);
  check(Math.abs(c.skullPts - before - 10) < 0.01, "head hit while exhausted: full points");
  const t0 = now();
  while (c.skull < 1) {
    e.applyDamage(10, { cause: "entityAttack", damagingEntity: ps[0] });
    tick(1);
  }
  check(e.props["dragon_dominion:skull"] === 1, "CRACKED state visible (skull property = 1)");
  tick(2);
  check(c.move?.mv.name === "skull_fracture" || c.queued.includes("skull_fracture"), "fracture reaction plays");
  check(L.particles.some((x) => x.id === "dragon_dominion:skull_shards" && x.tick >= t0), "bone shards burst");
  // cracked: damage bonus while staggered
  c.endMove(true);
  c.queued = [];
  c.startMove("charge_impact");
  heal(e);
  const hpA = e.health.currentValue;
  e.applyDamage(10, { cause: "entityAttack", damagingEntity: ps[0] });
  check(Math.abs(hpA - e.health.currentValue - 10 * CONFIG.skull.staggerDamageBonus) < 0.01 ||
    hpA - e.health.currentValue > 10, `cracked + staggered takes bonus damage (${(hpA - e.health.currentValue).toFixed(1)})`);
  while (c.skull < 2) {
    e.applyDamage(10, { cause: "entityAttack", damagingEntity: ps[0] });
    tick(1);
  }
  check(e.props["dragon_dominion:skull"] === 2, "BROKEN state visible (skull property = 2)");
  c.endMove(true);
  c.queued = [];
  c.setState("PURSUE");
  tick(1);
  heal(e);
  const hpB = e.health.currentValue;
  e.applyDamage(10, { cause: "entityAttack", damagingEntity: ps[0] });
  check(Math.abs(hpB - e.health.currentValue - 10 * CONFIG.skull.brokenHeadBonus) < 0.01, "broken: exposed weak point takes x1.5 head damage");
  // broken: weaker charge, exhaustion after major attacks
  const ch = arena({ players: [[0.5, 64, 16]] });
  ch.c.skull = 2;
  const t3 = now();
  runMove(ch.c, "crushing_charge");
  check(dmgTo(ch.ps[0], t3)[0]?.amount === Math.round(A.crushing_charge.damage * CONFIG.skull.brokenChargeScale), "broken crown: weaker charge");
  check(animSet(ch.e, t3).includes(ANIM.exhausted), "broken crown: exhausted after a major attack");
}

// ======================================================================================= death & reward
section("death sequence, reward, cleanup");
{
  const { e, c, ps } = arena({ players: [[0.5, 64, 5]] });
  c.skull = 2;
  e.health.currentValue = 30;
  c.dmgByPlayers = e.health.effectiveMax; // a real fight
  const t0 = now();
  e.applyDamage(50, { cause: "entityAttack", damagingEntity: ps[0] });
  check(e.isValid && e.health.currentValue >= 1, "lethal hit does not let the engine kill it");
  tick(1);
  check(c.state === "DEAD" && e.props["dragon_dominion:anim"] === ANIM.death, "death animation starts");
  e.applyDamage(50, { cause: "entityAttack", damagingEntity: ps[0] });
  check(dmgTo(e, t0).length === 1, "invulnerable while dying");
  tick(sec(5));
  check(!e.isValid, "removed after the death animation");
  const drop = L.items.filter((x) => x.typeId === "dragon_dominion:fractured_crownplate" && x.tick >= t0);
  check(drop.length === 1 && drop[0].amount === 2, `Fractured Crownplate x2 (broken crown bonus) (${drop.map((x) => x.amount)})`);
  tick(3);
  check(REG.ACTIVE.size === 0, "registry forgets it");
  check(M.__runCount() === 1, `no leftover boss loop (runs: ${M.__runCount()}, ritual loop only)`);
  // /kill style removal: no reward
  const k = arena({ players: [[0.5, 64, 5]] });
  const t1 = now();
  k.e.applyDamage(99999, { cause: "selfDestruct" });
  tick(sec(6));
  check(!k.e.isValid && L.items.filter((x) => x.tick >= t1).length === 0, "/kill removes it without a reward");
}

// ======================================================================================= reset
section("reset: lost target / boundary -> walk home, full heal, phase I");
{
  const { e, c, ps } = arena({ phase: 2, players: [[0.5, 64, 6]] });
  e.health.currentValue = 200;
  c.skull = 1;
  ps[0].gm = "Creative";
  c.nextDecision = now();
  tick(sec(CONFIG.detection.loseTargetAfter + CONFIG.reset.walkBack + 2));
  check(c.state === "IDLE" && !c.fight, `resets to IDLE (${c.state})`);
  check(e.health.currentValue === e.health.effectiveMax && e.health.effectiveMax === 500, "full health, tier 1");
  check(c.phase === 1 && c.skull === 0 && e.props["dragon_dominion:skull"] === 0, "phase and crown restored");
  check(e.groups.has("dragon_dominion:roam"), "vanilla roam AI restored");
  const b = arena({ players: [[0.5, 64, 6]] });
  const hpBefore = b.e.health.currentValue;
  b.c.startReset("test");
  b.e.applyDamage(30, { cause: "entityAttack", damagingEntity: b.ps[0] });
  check(b.e.health.currentValue === hpBefore, "invulnerable while resetting");
  const far = arena({ players: [[0.5, 64, 6]] });
  far.e.location = { x: CONFIG.detection.boundary + 5, y: 64, z: 0.5 };
  far.c.nextDecision = now();
  tick(2);
  check(far.c.state === "RESET", "leaving the combat boundary triggers a reset");
}

// ======================================================================================= unload / reload / disconnect
section("chunk unload + reload keeps fight state; disconnects are safe");
{
  const { e, c, ps } = arena({ phase: 2, players: [[0.5, 64, 6]] });
  c.addSkull(70, "test");
  tick(5);
  e.__unload();
  tick(2);
  check(!REG.controllerOf(e), "unloaded boss is dropped from the registry");
  M.__reload(e);
  const c2 = REG.controllerOf(e);
  check(c2 && c2 !== c, "re-adopted on load");
  check(c2 && c2.fight && c2.phase === 2 && c2.skull === 1, "phase and crown state restored from dynamic properties");
  M.world.afterEvents.playerLeave.fire({ playerId: ps[0].id });
  ps[0].__unload();
  let err = false;
  try {
    tick(sec(2));
  } catch {
    err = true;
  }
  check(!err && c2.target === undefined, "target that disconnected is cleared");
}

// ======================================================================================= multiplayer targeting
section("multiplayer: target switching, no player-vs-player damage");
{
  const { c, ps } = arena({ players: [[0.5, 64, 8], [8, 64, 8], [-8, 64, 8]] });
  const seen = new Set();
  for (let i = 0; i < 40; i++) {
    c.nextRetarget = 0;
    c.pickTarget(now());
    seen.add(c.target?.id);
  }
  check(seen.size >= 2, `switches between participants (${seen.size} different targets)`);
  const t0 = now();
  runMove(c, "wing_pressure");
  check(L.damage.filter((d) => d.tick >= t0 && d.source && d.source.typeId === "minecraft:player").length === 0, "boss attacks never credit a player as the attacker");
}

// ======================================================================================= long free fight (stability)
section("free-running fight: 3 minutes, moving players, invariants hold");
{
  const { e, c, ps } = arena({ players: [[0.5, 64, 10], [10, 64, -6]] });
  c.nextDecision = now();
  const moves = new Set();
  let maxStateTicks = 0;
  let resets = 0;
  let lastState = c.state;
  let since = now();
  for (let i = 0; i < sec(180); i++) {
    // players circle the dragon and poke it
    // a melee hunter strafing near the arena centre, a ranged hunter drifting around at 14 blocks
    const a = i / 60;
    ps[0].location = { x: Math.sin(a) * 5, y: 64, z: Math.cos(a * 0.8) * 5 };
    ps[1].location = { x: Math.sin(-a * 0.3) * 14, y: 64, z: Math.cos(-a * 0.3) * 14 };
    for (const p of ps) heal(p);
    if (i % 18 === 0 && e.isValid && c.state !== "DEAD") e.applyDamage(4, { cause: "entityAttack", damagingEntity: ps[i % 2] });
    tick(1);
    if (c.move) moves.add(c.move.mv.name);
    if (c.state !== lastState) {
      if (process.env.DEBUG) console.log(now(), lastState, "->", c.state, c.resetWhy ?? "", c.move?.mv.name ?? "", e.location);
      lastState = c.state;
      if (c.state === "RESET") resets++;
      since = now();
    }
    maxStateTicks = Math.max(maxStateTicks, now() - since);
    if (!e.isValid) break;
  }
  check(["twin_claw", "crushing_charge", "rudder_sweep"].every((m) => moves.has(m)), `uses its phase I attacks (${[...moves]})`);
  check(["wing_pressure", "cliff_dive", "skullbreaker"].filter((m) => moves.has(m)).length >= 2, "uses its later-phase attacks");
  check(resets === 0, `no spurious resets (${resets})`);
  check(c.phase >= 2, `damage drove it through the phases (phase ${c.phase})`);
  check(!c.inAir || c.move?.mv.airborne, "never left stranded in the air");
  check(Number.isFinite(e.location.x) && Math.abs(e.location.y - 64) < 12, "position stays sane");
}

// ======================================================================================= engine contract
section("engine contract");
check(M.__issues.length === 0, `mock reported ${M.__issues.length} issue(s): ${M.__issues.join("; ")}`);

console.log(`smoke: ${pass} passed, ${fail} failed`);
fs.rmSync(RUN, { recursive: true, force: true });
process.exit(fail ? 1 : 0);
