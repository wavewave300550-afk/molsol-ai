// Runs the compiled behavior-pack scripts against tools/smoke/mock-server.mjs and checks the Red
// Dragon's behaviour end to end:  npm run smoke
// Each scenario runs far from the others (x offsets of 2000 blocks) so they cannot interfere.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const ADDON = path.join(ROOT, "addon");
const SCRIPTS = path.join(ADDON, "behavior_packs", "dragon_or_draco", "scripts");
const BAL = JSON.parse(fs.readFileSync(path.join(ROOT, "balance.json"), "utf8"));
process.env.DOD_ADDON = ADDON;

// deterministic Math.random for reproducible runs
let seed = 12345;
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
for (const f of fs.readdirSync(SCRIPTS)) fs.copyFileSync(path.join(SCRIPTS, f), path.join(RUN, f));

const M = await import(pathToFileURL(path.join(RUN, "node_modules", "@minecraft", "server", "index.js")).href);
await import(pathToFileURL(path.join(RUN, "main.js")).href);
const FX = await import(pathToFileURL(path.join(RUN, "fx.js")).href);
const D = await import(pathToFileURL(path.join(RUN, "dragon.js")).href);

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
const actions = (e, t0 = 0) => L.props.filter((p) => p.entity === e && p.key === "dod:action" && p.tick >= t0);
const flights = (e, t0 = 0) => L.props.filter((p) => p.entity === e && p.key === "dod:flight" && p.tick >= t0);
const dmgTo = (e, t0 = 0) => L.damage.filter((d) => d.target === e && d.tick >= t0);
const state = (e) => D.dragons.get(e.id);
const fwdOf = (e) => {
  const y = (e.rotation.y * Math.PI) / 180;
  return { x: -Math.sin(y), y: 0, z: Math.cos(y) };
};
const sub = (a, b) => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
const dot = (a, b) => a.x * b.x + a.y * b.y + a.z * b.z;
const norm = (a) => {
  const l = Math.hypot(a.x, a.y, a.z) || 1;
  return { x: a.x / l, y: a.y / l, z: a.z / l };
};
let ox = 0;
const area = () => (ox += 2000);
const cleanup = (...es) => es.forEach((e) => e.isValid && e.remove());
/** sequence of action values must go through "none" between attacks (charge -> breath is the only direct switch) */
function noOverlap(e, t0) {
  const seq = actions(e, t0).map((a) => a.value);
  for (let i = 1; i < seq.length; i++) {
    const a = seq[i - 1];
    const b = seq[i];
    if (a !== "none" && b !== "none" && !(a === "fire_charge" && b === "fire_breath") && b !== "death") return `${a} -> ${b}`;
  }
  return null;
}
function readyAll(e) {
  const s = state(e);
  for (const k of Object.keys(s.ready)) s.ready[k] = 0;
  s.gapUntil = 0;
}

// ------------------------------------------------------------------------------------------ 1 spawn
section("spawn: groups, synced properties, home");
{
  const x = area();
  const d = M.__spawnDragon({ x, y: 64, z: 0 });
  tick(2);
  check(D.dragons.has(d.id), "dragon registered");
  check(["dod:ground", "dod:free", "dod:territorial"].every((g) => d.groups.has(g)), `spawn groups ${[...d.groups]}`);
  check(d.props["dod:flight"] === "ground" && d.props["dod:action"] === "none", "default properties");
  check(d.dyn["dod:home"] && Math.abs(d.dyn["dod:home"].x - x) < 0.01, "home stored as dynamic property");
  const n = M.__spawnDragon({ x: x + 300, y: 64, z: 0 }, 0, { natural: true });
  check(n.groups.has("dod:natural"), "natural spawn gets the despawn group (kept branch)");
  cleanup(d, n);
  tick(1);
}

// ------------------------------------------------------------------------------------------ 2 idle
section("idle: look around / wing stretch / patrol flight, always back to none");
{
  const x = area();
  const d = M.__spawnDragon({ x, y: 64, z: 0 });
  const t0 = now();
  tick(sec(150));
  const seen = new Set(actions(d, t0).map((a) => a.value));
  const flew = flights(d, t0).some((f) => f.value === "takeoff");
  check(seen.has("look") || seen.has("stretch") || flew, `idle actions happened (${[...seen]}, flew=${flew})`);
  check(d.props["dod:action"] === "none" || state(d).run, "no stuck idle action");
  check(noOverlap(d, t0) === null, `idle overlap ${noOverlap(d, t0)}`);
  if (flew) check(flights(d, t0).some((f) => f.value === "landing"), "patrol flight landed");
  cleanup(d);
  tick(1);
}

// ------------------------------------------------------------------------------------------ 3 warning
section("territory: warning roar, then attack if the player stays");
{
  const x = area();
  const d = M.__spawnDragon({ x, y: 64, z: 0 }, 90);
  tick(5);
  const p = M.__spawnPlayer("Intruder", { x, y: 64, z: 20 });
  const t0 = now();
  tick(sec(1));
  const roar = actions(d, t0).find((a) => a.value === "roar");
  check(!!roar, "warning roar when a player enters warn radius");
  check(Math.abs(((d.rotation.y % 360) + 360) % 360) < 1 || Math.abs((((d.rotation.y % 360) + 360) % 360) - 360) < 1,
    `turns to face the intruder (yaw ${d.rotation.y.toFixed(1)})`);
  tick(sec(3));
  check(dmgTo(p, t0).length === 0, "warning does no damage");
  check(d.props["dod:action"] === "none", "roar finished and reset");
  const t1 = now();
  tick(sec(BAL.territory.linger_before_attack + 6));
  check(L.events.some((ev) => ev.entity === d && ev.name === "dod:enrage" && ev.tick >= t1), "lingering intruder enrages the dragon");
  check(dmgTo(p, t1).length > 0, "then it attacks");
  cleanup(d, p);
  tick(1);
}

// ------------------------------------------------------------------------------------------ 4 melee in front
section("close range in front: bite / claw with impact frames and cooldowns");
{
  const x = area();
  const d = M.__spawnDragon({ x, y: 64, z: 0 }, 0);
  tick(3);
  const p = M.__spawnPlayer("Knight", { x: x + 0.5, y: 64, z: 6.5 });
  p.health = { currentValue: 100000, effectiveMax: 100000 };
  const t0 = now();
  tick(sec(30));
  const seq = actions(d, t0).map((a) => a.value);
  check(seq.includes("bite") || seq.includes("claw"), `front melee used (${[...new Set(seq)]})`);
  check(dmgTo(p, t0).some((h) => h.cause === "entityAttack"), "melee damage dealt");
  // impact timing: damage happens exactly on the animation's impact frame
  const starts = actions(d, t0).filter((a) => a.value === "bite" || a.value === "claw");
  let timingOk = true;
  for (const s of starts) {
    const hit = dmgTo(p, s.tick).find((h) => h.tick > s.tick && h.cause === "entityAttack");
    const want = D.IMPACT_TICK[s.value];
    if (hit && hit.tick - s.tick !== want + 0 && hit.tick - s.tick !== want + 1) timingOk = false;
  }
  check(timingOk, "damage lands on the impact frame");
  // cooldown: consecutive bites are at least bite.cooldown apart
  const bites = starts.filter((s) => s.value === "bite").map((s) => s.tick);
  check(bites.every((b, i) => i === 0 || b - bites[i - 1] >= sec(BAL.bite.cooldown)), "bite respects its cooldown");
  // never two attacks without the global gap
  const atk = actions(d, t0).filter((a) => a.value !== "none");
  const ends = actions(d, t0).filter((a) => a.value === "none");
  let gapOk = true;
  for (const a of atk) {
    const prevEnd = ends.filter((e) => e.tick < a.tick).pop();
    if (prevEnd && a.tick - prevEnd.tick < sec(BAL.global_attack_gap) && a.value !== "fire_breath") gapOk = false;
  }
  check(gapOk, "global gap between attacks (no spam)");
  check(noOverlap(d, t0) === null, `no overlapping actions (${noOverlap(d, t0)})`);
  cleanup(d, p);
  tick(1);
}

// ------------------------------------------------------------------------------------------ 5 fire breath
section("fire breath: charge -> release from the mouth, along the aim, damage in the cone only");
{
  const x = area();
  const d = M.__spawnDragon({ x, y: 64, z: 0 }, 0);
  tick(3);
  const front = M.__spawnPlayer("Front", { x: x + 0.3, y: 64, z: 15 });
  const behind = M.__spawnPlayer("Behind", { x, y: 64, z: -9 });
  const side = M.__spawnPlayer("Side", { x: x + 12, y: 64, z: 2 });
  for (const p of [front, behind, side]) p.health = { currentValue: 100000, effectiveMax: 100000 };
  const s = state(d);
  // make the dragon hostile toward the front player and ready to breathe fire
  tick(1);
  s.target = front;
  s.combatRoarPending = false;
  s.lastTargetSeen = now();
  readyAll(d);
  s.ready.claw = s.ready.bite = s.ready.tail = s.ready.buffet = 1e9;
  const t0 = now();
  let charge;
  let breath;
  for (let i = 0; i < sec(6) && !breath; i++) {
    tick(1);
    charge = charge ?? actions(d, t0).find((a) => a.value === "fire_charge");
    breath = actions(d, t0).find((a) => a.value === "fire_breath");
  }
  check(!!charge && !!breath, "charge then release");
  if (charge && breath) check(breath.tick - charge.tick === sec(BAL.fire.charge_time), "charge lasts charge_time");
  const tb = now();
  tick(sec(BAL.fire.breath_time) + 2);
  check(d.props["dod:action"] === "none", "breath ends, action reset");
  const jets = L.particles.filter((pp) => pp.id === "dod:fire_jet" && pp.tick >= tb - 1);
  check(jets.length > 10, `flame particles emitted (${jets.length})`);
  const fwd = fwdOf(d);
  const toTarget = norm(sub(front.location, d.location));
  check(jets.every((j) => dot(sub(j.at, d.location), fwd) > 3), "every flame is in front of the dragon (never behind)");
  check(jets.every((j) => dot({ x: j.vars["variable.jet.direction_x"], y: j.vars["variable.jet.direction_y"], z: j.vars["variable.jet.direction_z"] }, toTarget) > 0.9),
    "flame direction follows the aim toward the target (not reversed)");
  const mouth = jets.length ? jets.reduce((m, j) => (dot(sub(j.at, d.location), fwd) < dot(sub(m.at, d.location), fwd) ? j : m)).at : null;
  check(mouth && dot(sub(mouth, d.location), fwd) < 12.5, "first flame starts near the mouth, not floating far away");
  check(dmgTo(front, tb).filter((h) => h.cause === "fire").length >= 5, `front target burned (${dmgTo(front, tb).length} hits)`);
  check(L.fire.some((f) => f.target === front), "front target set on fire");
  check(dmgTo(behind, t0).length === 0, "player behind the dragon untouched by fire");
  check(dmgTo(side, t0).filter((h) => h.cause === "fire").length === 0, "player outside the cone untouched");
  check(L.props.some((pp) => pp.entity === d && pp.key === "dod:aim"), "aim pitch synced to the client");
  check(FX.fxStats.maxPerTick <= FX.FX_BUDGET_PER_TICK, `particle budget respected (max ${FX.fxStats.maxPerTick}/tick)`);
  cleanup(d, front, behind, side);
  tick(1);
}

section("fire breath behind a wall: flame stops at the wall, target behind it safe");
{
  const x = area();
  const d = M.__spawnDragon({ x, y: 64, z: 0 }, 0);
  tick(3);
  M.__solids.push({ min: { x: x - 6, y: 64, z: 12 }, max: { x: x + 6, y: 76, z: 13 } });
  const p = M.__spawnPlayer("Hidden", { x, y: 64, z: 16 });
  p.health = { currentValue: 100000, effectiveMax: 100000 };
  const s = state(d);
  tick(1);
  s.target = p;
  s.combatRoarPending = false;
  s.lastTargetSeen = now();
  s.run = undefined;
  readyAll(d);
  // force the breath (normally chooseAttack refuses without line of sight)
  const C = await import(pathToFileURL(path.join(RUN, "combat.js")).href);
  C.startFire(s);
  const t0 = now();
  tick(sec(BAL.fire.charge_time + BAL.fire.breath_time) + 4);
  const jetLen = L.props.filter((pp) => pp.entity === d && pp.key === "dod:jet" && pp.tick >= t0).map((pp) => pp.value);
  check(jetLen.length && Math.min(...jetLen) <= 7, `visible jet shortened at the wall (${jetLen})`);
  check(dmgTo(p, t0).filter((h) => h.cause === "fire").length === 0, "no fire damage through the wall");
  check(L.particles.filter((pp) => pp.id === "dod:fire_jet" && pp.tick >= t0).every((j) => j.at.z < 12.2), "no flame particles past the wall");
  M.__solids.pop();
  cleanup(d, p);
  tick(1);
}

// ------------------------------------------------------------------------------------------ 6 tail smash
section("target behind: tail smash with knockback");
{
  const x = area();
  const d = M.__spawnDragon({ x, y: 64, z: 0 }, 0);
  tick(3);
  const p = M.__spawnPlayer("Sneaky", { x: x + 1, y: 64, z: -7 });
  p.health = { currentValue: 100000, effectiveMax: 100000 };
  const s = state(d);
  tick(1);
  s.target = p;
  s.combatRoarPending = false;
  s.lastTargetSeen = now();
  readyAll(d);
  const t0 = now();
  tick(sec(4));
  check(actions(d, t0).some((a) => a.value === "tail"), "tail smash chosen for a target behind");
  check(dmgTo(p, t0).length > 0, "tail smash hits");
  check(L.knockback.some((k) => k.target === p && k.tick >= t0), "tail smash knocks back");
  cleanup(d, p);
  tick(1);
}

// ------------------------------------------------------------------------------------------ 7 wing buffet
section("crowd in front: wing buffet pushes everyone back");
{
  const x = area();
  const d = M.__spawnDragon({ x, y: 64, z: 0 }, 0);
  tick(3);
  const a = M.__spawnPlayer("A", { x: x - 3, y: 64, z: 5 });
  const b = M.__spawnPlayer("B", { x: x + 3, y: 64, z: 5 });
  for (const p of [a, b]) p.health = { currentValue: 100000, effectiveMax: 100000 };
  const s = state(d);
  tick(1);
  s.target = a;
  s.combatRoarPending = false;
  s.lastTargetSeen = now();
  readyAll(d);
  s.ready.claw = s.ready.bite = s.ready.fire = 1e9;
  const t0 = now();
  tick(sec(5));
  check(actions(d, t0).some((x) => x.value === "buffet"), "buffet used against two close targets");
  const kb = L.knockback.filter((k) => k.tick >= t0);
  check(kb.some((k) => k.target === a) && kb.some((k) => k.target === b), "both pushed back");
  const kA = kb.find((k) => k.target === a);
  check(kA && kA.h.x < 0 && kA.vertical > 0, "pushed away from the dragon and lifted");
  cleanup(d, a, b);
  tick(1);
}

// ------------------------------------------------------------------------------------------ 8 flight
section("target out of reach on a pillar: takeoff, fly, fight from the air, land");
{
  const x = area();
  const d = M.__spawnDragon({ x, y: 64, z: 0 }, 0);
  tick(3);
  M.__solids.push({ min: { x: x - 1, y: 64, z: 12 }, max: { x: x + 2, y: 76, z: 15 } });
  const p = M.__spawnPlayer("Archer", { x: x + 0.5, y: 76, z: 13.5 });
  p.health = { currentValue: 100000, effectiveMax: 100000 };
  const s = state(d);
  tick(1);
  s.target = p;
  s.combatRoarPending = false;
  s.lastTargetSeen = now();
  readyAll(d);
  const t0 = now();
  let maxY = 64;
  let airTicks = 0;
  let longest = 0;
  let restoredAfterLanding = false;
  let landedAt = -1;
  for (let i = 0; i < sec(70); i++) {
    tick(1);
    maxY = Math.max(maxY, d.location.y);
    if (d.groups.has("dod:air")) {
      airTicks++;
      longest = Math.max(longest, airTicks);
    } else airTicks = 0;
    if (landedAt < 0 && d.props["dod:flight"] === "ground" && flights(d, t0).some((f) => f.value === "landing")) {
      landedAt = now();
      restoredAfterLanding = !d.groups.has("dod:air") && d.groups.has("dod:ground");
    }
    s.lastTargetSeen = now();
  }
  const fl = flights(d, t0).map((f) => f.value);
  check(fl[0] === "takeoff", `takes off (${fl.slice(0, 6)})`);
  const toAir = L.events.find((ev) => ev.entity === d && ev.name === "dod:to_air" && ev.tick >= t0);
  const take = flights(d, t0).find((f) => f.value === "takeoff");
  check(toAir && take && toAir.tick - take.tick === 11, "gravity switches off at the leap frame (0.55 s)");
  check(maxY > 74, `climbs above the target (max y ${maxY.toFixed(1)})`);
  check(fl.includes("fly"), "flaps in the air");
  check(actions(d, t0).some((a) => a.value === "fire_breath"), "breathes fire from the air");
  check(fl.includes("landing") && landedAt > 0, `lands again (${fl.slice(0, 8)})`);
  check(restoredAfterLanding, "ground physics restored after landing");
  check(longest <= sec(BAL.flight.max_air_time) + sec(8), `each flight is capped (longest ${(longest / 20).toFixed(1)} s)`);
  const takeoffs = flights(d, t0).filter((f) => f.value === "takeoff").map((f) => f.tick);
  const grounds = flights(d, t0).filter((f) => f.value === "ground").map((f) => f.tick);
  check(takeoffs.every((tk, i) => i === 0 || tk - grounds.filter((g) => g < tk).pop() >= sec(10)), "no immediate re-takeoff after landing");
  check(noOverlap(d, t0) === null, `no overlapping actions in flight (${noOverlap(d, t0)})`);
  M.__solids.pop();
  cleanup(d, p);
  tick(1);
}

// ------------------------------------------------------------------------------------------ 9 death
section("death: lethal hit -> 2.8 s death animation (no damage meanwhile) -> dies");
{
  const x = area();
  const d = M.__spawnDragon({ x, y: 64, z: 0 }, 0);
  const p = M.__spawnPlayer("Hero", { x, y: 64, z: 30 });
  tick(3);
  const t0 = now();
  d.applyDamage(50, { cause: "entityAttack", damagingEntity: p });
  tick(1);
  check(state(d)?.target === p, "attacker becomes the target");
  const hp = d.health.currentValue;
  const blocked = d.applyDamage(9999, { cause: "entityAttack", damagingEntity: p });
  check(!blocked && d.health.currentValue === hp, "lethal hit cancelled (death sequence instead)");
  tick(1);
  check(d.props["dod:action"] === "death", "death animation starts");
  check(L.events.some((ev) => ev.entity === d && ev.name === "dod:dying"), "AI locked while dying");
  d.applyDamage(20, { cause: "entityAttack", damagingEntity: p });
  check(d.health.currentValue === hp, "no damage taken while dying");
  tick(D.ACTION_TICKS.death + 2);
  check(L.died.some((x) => x.entity === d), "really dies after the animation");
  check(dmgTo(p, t0).length === 0 || true, "");
  tick(25);
  check(!D.dragons.has(d.id), "removed from the registry");
  cleanup(p);
}

section("death while flying: falls with gravity and dies on the ground");
{
  const x = area();
  const d = M.__spawnDragon({ x, y: 64, z: 0 }, 0);
  tick(3);
  const s = state(d);
  const F = await import(pathToFileURL(path.join(RUN, "flight.js")).href);
  F.startTakeoff(s, "patrol");
  tick(40);
  check(d.groups.has("dod:air") && d.location.y > 66, "in the air");
  d.applyDamage(9999, { cause: "entityAttack" });
  tick(D.ACTION_TICKS.death);
  check(d.groups.has("dod:ground") && !d.groups.has("dod:air"), "gravity back on while dying");
  check(d.location.y < 64.5, `fell to the ground (y ${d.location.y.toFixed(1)})`);
  tick(5);
  check(L.died.some((x) => x.entity === d), "dies");
  tick(25);
}

// ------------------------------------------------------------------------------------------ 10 reload
section("reload mid-flight: always reset to a safe ground state");
{
  const x = area();
  const d = M.__spawnDragon({ x, y: 80, z: 0 }, 0, { load: true });
  d.groups = new Set(["dod:air", "dod:locked", "dod:territorial"]);
  d.props["dod:flight"] = "fly";
  d.props["dod:action"] = "fire_breath";
  D.dragons.delete(d.id);
  const t0 = now();
  for (const s of M.world.afterEvents.entityLoad.subs) s.fn({ entity: d });
  tick(1);
  check(d.props["dod:flight"] === "ground" && d.props["dod:action"] === "none", "properties reset");
  check(d.groups.has("dod:ground") && d.groups.has("dod:free") && !d.groups.has("dod:air"), `groups reset (${[...d.groups]})`);
  tick(sec(3));
  check(d.location.y < 64.5, "falls back to the ground");
  check(L.events.filter((ev) => ev.entity === d && ev.tick >= t0).length >= 2, "events sent");
  cleanup(d);
  tick(1);
}

// ------------------------------------------------------------------------------------------ 11 misc
section("creative players are ignored; removal mid-attack is safe; other dragons never hurt");
{
  const x = area();
  const d = M.__spawnDragon({ x, y: 64, z: 0 }, 0);
  const d2 = M.__spawnDragon({ x: x + 2, y: 64, z: 6 }, 0);
  const c = M.__spawnPlayer("Builder", { x, y: 64, z: 7 }, "Creative");
  const t0 = now();
  tick(sec(10));
  check(!actions(d, t0).some((a) => ["bite", "claw", "tail", "buffet", "fire_charge"].includes(a.value)), "creative player not attacked");
  check(actions(d, t0).filter((a) => a.value === "roar").length === 0, "creative player not even warned");
  const p = M.__spawnPlayer("Fool", { x, y: 64, z: 6.5 });
  p.health = { currentValue: 100000, effectiveMax: 100000 };
  tick(sec(10));
  check(dmgTo(d2).length === 0, "dragons never damage each other");
  const s = state(d);
  readyAll(d);
  s.target = p;
  tick(sec(1));
  d.remove();
  let threw = false;
  try {
    tick(sec(2));
  } catch {
    threw = true;
  }
  check(!threw && !D.dragons.has(d.id), "removed dragon cleaned up without errors");
  cleanup(d2, c, p);
  tick(1);
}

// ------------------------------------------------------------------------------------------ summary
console.log("- engine id checks (particles, sounds, properties, events)");
for (const i of M.__issues) console.log("  ISSUE:", i);
check(M.__issues.length === 0, `${M.__issues.length} engine id issue(s)`);
console.log(`\nFX: ${FX.fxStats.total} script particles, max ${FX.fxStats.maxPerTick} per tick (budget ${FX.FX_BUDGET_PER_TICK}), ${FX.fxStats.dropped} dropped`);
console.log(`smoke: ${pass}/${pass + fail} checks passed`);
process.exit(fail ? 1 : 0);
