// Runs the compiled behavior-pack scripts against tools/smoke/mock-server.mjs and checks the boss fight
// end to end:  npm run smoke
// Each scenario runs far from the others (x offsets of 2000 blocks) so they cannot interfere.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const ADDON = path.join(ROOT, "addon");
const SCRIPTS = path.join(ADDON, "behavior_packs", "extra_super_boss", "scripts");
const BAL = JSON.parse(fs.readFileSync(path.join(ROOT, "balance.json"), "utf8"));
process.env.ESB_ADDON = ADDON;

// deterministic Math.random for reproducible runs
let seed = 4242;
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
const B = await import(pathToFileURL(path.join(RUN, "boss.js")).href);
const SPEC = await import(pathToFileURL(path.join(RUN, "spec.js")).href);

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
const st = (e) => B.bosses.get(e.id);
const actions = (e, t0 = 0) => L.props.filter((p) => p.entity === e && p.key === "esb:action" && p.tick >= t0).map((p) => p.value);
const actionTick = (e, a, t0 = 0) => L.props.find((p) => p.entity === e && p.key === "esb:action" && p.value === a && p.tick >= t0)?.tick;
const events = (e, t0 = 0) => L.events.filter((x) => x.entity === e && x.tick >= t0).map((x) => x.name);
const dmgTo = (t, t0 = 0) => L.damage.filter((d) => d.target === t && d.tick >= t0);
const ACT = SPEC.ACTIONS;
const FAR = 1e9;
/** Make only `which` available (others on a long cooldown). */
function only(e, which) {
  const s = st(e);
  for (const k of Object.keys(s.ready)) s.ready[k] = k === which ? 0 : FAR;
  s.gapUntil = 0;
  s.nextDecision = 0;
}
function waitFor(cond, max = 400) {
  for (let i = 0; i < max; i++) {
    if (cond()) return true;
    tick();
  }
  return cond();
}

// ------------------------------------------------------------------------------------------ 1. spawn + intro
section("spawn: intro, title, invulnerable while it plays");
{
  const p = M.__spawnPlayer("Steve", { x: 10, y: 64, z: 12 });
  const t0 = now();
  const e = M.__spawnBoss({ x: 10, y: 64, z: 0 });
  tick(1);
  check(actions(e, t0)[0] === "intro", "intro starts on a fresh spawn");
  check(events(e, t0).includes("esb:lock"), "movement locked during the intro");
  tick(sec(0.3));
  check(L.titles.some((x) => x.target === p), "boss title shown to the nearby player");
  check(!M.__dims.overworld.getEntities({ type: "esb:da_vinci" })[0].applyDamage(10, { cause: "entityAttack", damagingEntity: p }),
    "cannot be hurt during the intro");
  tick(sec(ACT.intro.length));
  check(st(e).run === undefined || st(e).run.kind !== "intro", "intro finished");
  check(events(e, t0).includes("esb:unlock"), "free to move after the intro");
  check(e.dyn["esb:intro_done"] === true, "intro remembered on the entity");
  check(st(e).invulnerable === false, "vulnerable again after the intro");
  p.remove();
  e.remove();
}

section("reload: no intro, clean state");
{
  const t0 = now();
  const e = M.__spawnBoss({ x: 2000, y: 64, z: 0 }, 0, { load: true });
  tick(2);
  check(!actions(e, t0).includes("intro"), "no intro when a saved boss loads");
  check(e.props["esb:action"] === "none", "action reset to none");
  check(events(e, t0).includes("esb:unlock"), "unlocked after load");
  e.remove();
}

// ------------------------------------------------------------------------------------------ 2. gear volley
section("gear volley: three shots on the animation frames, aimed at the target");
{
  const X = 4000;
  const e = M.__spawnBoss({ x: X, y: 64, z: 0 }, 0, { load: true });
  const p = M.__spawnPlayer("Alex", { x: X, y: 64, z: 15 });
  tick(2);
  only(e, "gear_volley");
  const t0 = now();
  check(waitFor(() => st(e).run?.kind === "gear_volley", 40), "gear volley chosen at 15 blocks");
  const start = actionTick(e, "gear_volley", t0);
  tick(sec(ACT.gear_volley.length) + 2);
  const shots = L.shots.filter((s) => s.tick >= start);
  check(shots.length === 3 * BAL.gear_volley.gears_phase1, `phase 1 fires ${3 * BAL.gear_volley.gears_phase1} gears (got ${shots.length})`);
  const ticks = [...new Set(shots.map((s) => s.tick - start))].sort((a, b) => a - b);
  const want = ["shot1", "shot2", "shot3"].map((k) => sec(ACT.gear_volley.moments[k]));
  check(JSON.stringify(ticks) === JSON.stringify(want), `shots on ticks ${want} (got ${ticks})`);
  check(shots.every((s) => s.owner === e), "every gear is owned by the boss");
  const centre = shots.filter((_, i) => i % 3 === 1);
  check(centre.every((s) => {
    const v = s.velocity;
    const l = Math.hypot(v.x, v.y, v.z);
    const d = { x: p.location.x - s.at.x, y: p.location.y + 0.9 - s.at.y, z: p.location.z - s.at.z };
    const dl = Math.hypot(d.x, d.y, d.z);
    return (v.x * d.x + v.y * d.y + v.z * d.z) / (l * dl) > 0.98 && Math.abs(l - BAL.gear_volley.speed) < 1e-6;
  }), "centre gear flies straight at the player at the balance speed");
  check(shots.every((s) => s.at.y > 66 && s.at.y < 68.5), "gears leave from the raised gauntlet (about 3.5 blocks up)");
  check(e.props["esb:action"] === "none" && events(e, t0).at(-1) === "esb:unlock", "volley ends unlocked");
  check(st(e).ready.gear_volley > now(), "gear volley on cooldown");
  p.remove();
  e.remove();
}

// ------------------------------------------------------------------------------------------ 3. quake
section("gauntlet quake: damage on the impact frame, falloff, knockback");
{
  const X = 6000;
  const e = M.__spawnBoss({ x: X, y: 64, z: 0 }, 0, { load: true });
  const near = M.__spawnPlayer("Near", { x: X, y: 64, z: 2.5 });
  const edge = M.__spawnPlayer("Edge", { x: X + 4, y: 64, z: 4.5 });
  const out = M.__spawnPlayer("Out", { x: X + 9, y: 64, z: 0 });
  const creative = M.__spawnPlayer("Builder", { x: X - 1, y: 64, z: 2 }, "Creative");
  tick(2);
  only(e, "quake");
  st(e).target = near;
  const t0 = now();
  check(waitFor(() => st(e).run?.kind === "quake", 40), "quake chosen at close range");
  const start = actionTick(e, "quake", t0);
  tick(sec(ACT.quake.length) + 2);
  const hit = start + sec(ACT.quake.moments.impact);
  const dn = dmgTo(near, t0);
  check(dn.length === 1 && dn[0].tick === hit, `near player hit once on tick ${hit} (got ${dn.map((d) => d.tick)})`);
  check(dn[0] && Math.abs(dn[0].amount - BAL.quake.damage) < 1e-6, "full damage close to the fist");
  const de = dmgTo(edge, t0);
  check(de.length === 1 && de[0].amount < BAL.quake.damage && de[0].amount >= BAL.quake.damage * 0.5, "reduced damage near the edge");
  check(dmgTo(out, t0).length === 0, "nothing outside the radius");
  check(dmgTo(creative, t0).length === 0, "creative players are never hurt");
  check(L.knockback.some((k) => k.target === near && k.tick === hit), "knockback on impact");
  check(L.particles.some((p) => p.id === "esb:shockwave" && p.tick === hit && p.vars?.["variable.radius"] === BAL.quake.radius),
    "shockwave sized to the damage radius");
  [near, edge, out, creative, e].forEach((x) => x.remove());
}

// ------------------------------------------------------------------------------------------ 4. vitruvian
section("vitruvian judgement: sigil telegraph, detonation inside the circle only");
{
  const X = 8000;
  const e = M.__spawnBoss({ x: X, y: 64, z: 0 }, 0, { load: true });
  const inside = M.__spawnPlayer("In", { x: X, y: 64, z: 6 });
  const outside = M.__spawnPlayer("Out", { x: X + 8.5, y: 64, z: 0 });
  tick(2);
  only(e, "vitruvian");
  st(e).target = inside;
  const t0 = now();
  check(waitFor(() => st(e).run?.kind === "vitruvian", 40), "vitruvian chosen");
  const start = actionTick(e, "vitruvian", t0);
  tick(sec(ACT.vitruvian.moments.sigil) + 1);
  const sig = M.__entities("esb:vitruvian_sigil");
  check(sig.length === 1 && sig[0].props["esb:radius"] === BAL.vitruvian.radius_phase1, "sigil spawned with the damage radius");
  check(sig[0] && Math.abs(sig[0].location.y - 64.02) < 0.05, "sigil lies on the ground");
  check(L.actionbars.some((a) => a.target === inside && a.tick >= start), "warning shown to the player in the circle");
  check(dmgTo(inside, t0).length === 0, "no damage before the detonation");
  tick(sec(ACT.vitruvian.length));
  const det = start + sec(ACT.vitruvian.moments.detonate);
  const di = dmgTo(inside, t0);
  check(di.length === 1 && di[0].tick === det && di[0].amount === BAL.vitruvian.damage, `inside hit on tick ${det}`);
  check(dmgTo(outside, t0).length === 0, "outside the circle: safe");
  check(M.__entities("esb:vitruvian_sigil").length === 0, "sigil removed after the detonation");
  check(L.particles.some((p) => p.id === "esb:sigil_edge" && p.tick > start && p.tick < det), "charging sparks on the circle edge");
  [inside, outside, e].forEach((x) => x.remove());
}

// ------------------------------------------------------------------------------------------ 5. transform
section("phase 2: transformation at 50% health");
{
  const X = 10000;
  const e = M.__spawnBoss({ x: X, y: 64, z: 0 }, 0, { load: true });
  const p = M.__spawnPlayer("Hero", { x: X, y: 64, z: 10 });
  tick(2);
  const t0 = now();
  e.health.currentValue = e.health.effectiveMax * 0.49;
  tick(1);
  check(st(e).run?.kind === "transform", "transform starts once health is at or below 50%");
  check(e.props["esb:phase"] === 2, "phase property switches to 2 (wings unfold on the client)");
  check(!e.applyDamage(20, { cause: "entityAttack", damagingEntity: p }), "invulnerable while transforming");
  tick(sec(ACT.transform.length) + 1);
  check(e.props["esb:action"] === "none", "transform finished");
  check(events(e, t0).includes("esb:unlock_fast"), "phase 2 uses the faster movement group");
  check(L.messages.some((m) => m.target === p && m.m.rawtext?.[0]?.translate === "esb.msg.phase2"), "phase 2 line sent");
  check(st(e).ready.dive <= now() + sec(3), "dive comes soon after the transformation");
  e.health.currentValue = 10;
  tick(5);
  check(!actions(e, now() - 5).includes("transform"), "transforms only once");
  [p, e].forEach((x) => x.remove());
}

// ------------------------------------------------------------------------------------------ 6. dive
section("ornithopter dive: rise, hover with a marker, strike the marked spot");
{
  const X = 12000;
  const e = M.__spawnBoss({ x: X, y: 64, z: 0 }, 0, { load: true });
  e.props["esb:phase"] = 2;
  const p = M.__spawnPlayer("Runner", { x: X + 2, y: 64, z: 12 });
  tick(2);
  st(e).phase = 2;
  only(e, "dive");
  const t0 = now();
  check(waitFor(() => st(e).run?.kind === "dive_rise", 40), "dive chosen in phase 2");
  const start = actionTick(e, "dive_rise", t0);
  tick(sec(ACT.dive_rise.moments.leap) + 1);
  check(events(e, t0).includes("esb:to_air"), "gravity off for the flight");
  waitFor(() => st(e).run?.kind === "dive_hover", 60);
  const peakY = e.location.y;
  check(peakY > 64 + BAL.dive.height - 0.5, `rises about ${BAL.dive.height} blocks (y ${peakY.toFixed(2)})`);
  const marker = M.__entities("esb:vitruvian_sigil")[0];
  check(!!marker && marker.props["esb:radius"] === BAL.dive.radius, "landing marker shows the strike radius");
  // the player moves during the hover: the marker follows until the last 0.6 s
  p.location = { x: X + 4, y: 64, z: 14 };
  tick(sec(0.2));
  check(marker && Math.abs(marker.location.x - (X + 4)) < 0.01, "marker follows the target early in the hover");
  waitFor(() => st(e).run?.kind === "dive_strike", 60);
  const strike = now();
  const hitTick = strike + sec(ACT.dive_strike.moments.impact) - 1;
  tick(sec(ACT.dive_strike.length) + 2);
  const d = dmgTo(p, t0);
  check(d.length === 1 && Math.abs(d[0].tick - hitTick) <= 1, `player hit on the impact frame (tick ${hitTick}, got ${d.map((x) => x.tick)})`);
  check(Math.abs(e.location.x - (X + 4)) < 0.01 && Math.abs(e.location.y - 64) < 0.01, "lands on the marked spot");
  check(events(e, t0).includes("esb:to_ground") && !st(e).inAir, "gravity back on after landing");
  check(M.__entities("esb:vitruvian_sigil").length === 0, "marker removed");
  check(e.props["esb:action"] === "none" && events(e, t0).at(-1) === "esb:unlock_fast", "dive ends unlocked");
  const seq = actions(e, t0);
  check(JSON.stringify(seq) === JSON.stringify(["dive_rise", "dive_hover", "dive_strike", "none"]), `action sequence ${seq}`);
  check(start !== undefined, "dive started");
  [p, e].forEach((x) => x.remove());
}

section("dive under a low ceiling is cancelled cleanly");
{
  const X = 14000;
  M.__solids.push({ min: { x: X - 4, y: 69, z: -4 }, max: { x: X + 4, y: 70, z: 4 } });
  const e = M.__spawnBoss({ x: X, y: 64, z: 0 }, 0, { load: true });
  e.props["esb:phase"] = 2;
  const p = M.__spawnPlayer("Cave", { x: X, y: 64, z: 10 });
  tick(2);
  st(e).phase = 2;
  only(e, "dive");
  const t0 = now();
  waitFor(() => st(e).run?.kind === "dive_rise", 40);
  tick(sec(ACT.dive_rise.length) + 4);
  check(!events(e, t0).includes("esb:to_air"), "never leaves the ground");
  check(e.props["esb:action"] === "none" && !st(e).inAir, "back to normal");
  [p, e].forEach((x) => x.remove());
}

// ------------------------------------------------------------------------------------------ 7. death
section("death: lethal hit becomes the death sequence, then the player gets the kill");
{
  const X = 16000;
  const e = M.__spawnBoss({ x: X, y: 64, z: 0 }, 0, { load: true });
  const p = M.__spawnPlayer("Slayer", { x: X, y: 64, z: 3 });
  tick(2);
  st(e).phase = 2;
  e.health.currentValue = 5;
  const t0 = now();
  check(!e.applyDamage(30, { cause: "entityAttack", damagingEntity: p }), "lethal hit is cancelled");
  tick(1);
  check(e.props["esb:action"] === "death" && st(e).dying, "death sequence starts");
  check(!e.applyDamage(30, { cause: "entityAttack", damagingEntity: p }), "no damage while dying");
  tick(sec(ACT.death.length) + 2);
  const died = L.died.find((x) => x.entity === e);
  check(!!died, "dies at the end of the sequence");
  check(died && died.src.damagingEntity === p, "the player is credited with the kill (loot + XP)");
  check(died && died.tick - t0 >= sec(ACT.death.length), "the whole death animation plays first");
  check(L.messages.some((m) => m.target === p && m.m.rawtext?.[0]?.translate === "esb.msg.death"), "farewell line sent");
  tick(30);
  p.remove();
}

// ------------------------------------------------------------------------------------------ 8. items
section("blueprint summons the boss after the ritual; codex grants its buffs with a cooldown");
{
  const X = 18000;
  const p = M.__spawnPlayer("Inventor", { x: X, y: 64, z: 0 });
  p.rotation = { x: 0, y: 0 }; // facing +Z
  p.container.setItem(0, { typeId: "esb:da_vinci_blueprint", amount: 2 });
  const t0 = now();
  M.__useItem(p, "esb:da_vinci_blueprint");
  check(p.container.getItem(0)?.amount === 1, "one blueprint consumed");
  check(M.__entities("esb:vitruvian_sigil").length === 1, "ritual circle drawn");
  tick(10);
  M.__useItem(p, "esb:da_vinci_blueprint");
  check(p.container.getItem(0)?.amount === 1, "a second ritual cannot start while one is pending");
  tick(50);
  const bossList = M.__entities("esb:da_vinci");
  check(bossList.length === 1, "boss summoned");
  const b = bossList[0];
  check(b && Math.abs(b.location.z - 6.5) < 1 && Math.abs(b.location.y - 64) < 0.01, "summoned 6 blocks in front, on the ground");
  check(b && actions(b, t0)[0] === "intro", "summoned boss plays its intro");
  check(M.__entities("esb:vitruvian_sigil").length === 0, "ritual circle removed");
  M.__useItem(p, "esb:da_vinci_blueprint");
  check(L.messages.some((m) => m.target === p && m.m.rawtext?.[0]?.translate === "esb.msg.summon_busy"), "busy message while he is nearby");
  // no space
  const q = M.__spawnPlayer("Miner", { x: X + 500, y: 64, z: 0 });
  M.__solids.push({ min: { x: X + 499, y: 64, z: 4 }, max: { x: X + 502, y: 72, z: 9 } }); // a wall
  q.container.setItem(0, { typeId: "esb:da_vinci_blueprint", amount: 1 });
  M.__useItem(q, "esb:da_vinci_blueprint");
  check(q.container.getItem(0)?.amount === 1, "not consumed when there is no room");
  check(L.messages.some((m) => m.target === q && m.m.rawtext?.[0]?.translate === "esb.msg.summon_space"), "explains the space rule");
  // codex
  M.__useItem(p, "esb:leonardo_codex");
  const fx = L.effects.filter((x) => x.target === p).map((x) => x.type).sort();
  check(JSON.stringify(fx) === JSON.stringify(["haste", "night_vision", "speed"]), `codex effects ${fx}`);
  check(L.effects.every((x) => x.duration === sec(BAL.codex.duration)), "codex effects last the configured time");
  M.__useItem(p, "esb:leonardo_codex");
  check(L.effects.filter((x) => x.target === p).length === 3, "second use is on cooldown");
  check(L.messages.some((m) => m.target === p && m.m.rawtext?.[0]?.translate === "esb.msg.codex_cd"), "cooldown message");
  b?.remove();
  [p, q].forEach((x) => x.remove());
}

// ------------------------------------------------------------------------------------------ 9. long fight soak
section("soak: 3 minutes of fighting two players, every action ends cleanly");
{
  const X = 20000;
  const e = M.__spawnBoss({ x: X, y: 64, z: 0 }, 0, { load: true });
  const a = M.__spawnPlayer("A", { x: X + 3, y: 64, z: 2 });
  const c = M.__spawnPlayer("C", { x: X - 6, y: 64, z: 14 });
  tick(2);
  const t0 = now();
  for (let i = 0; i < sec(180); i++) {
    // players circle around; the boss takes steady damage (phase 2 halfway)
    const ang = i / 40;
    a.location = { x: X + Math.cos(ang) * 4, y: 64, z: Math.sin(ang) * 4 };
    c.location = { x: X + Math.cos(-ang * 0.7) * 16, y: 64, z: Math.sin(-ang * 0.7) * 16 };
    a.health.currentValue = 20;
    c.health.currentValue = 20;
    // the close player and the far archer take turns hitting him, so he switches targets
    if (i % 40 === 0 && !st(e)?.dying) e.applyDamage(4, { cause: "entityAttack", damagingEntity: i % 80 === 0 ? a : c });
    tick();
  }
  const seen = new Set(actions(e, t0));
  for (const k of ["gear_volley", "quake", "vitruvian", "transform", "dive_rise", "dive_hover", "dive_strike", "ultimate"]) {
    check(seen.has(k), `soak used ${k}`);
  }
  const s = st(e);
  check(s && !s.inAir && (s.run === undefined || s.run.kind !== undefined), "state consistent after the soak");
  check(M.__entities("esb:vitruvian_sigil").length <= 1, "no sigils left behind");
  check(FX.fxStats.maxPerTick <= FX.FX_BUDGET_PER_TICK, `particle budget respected (max ${FX.fxStats.maxPerTick}/tick)`);
  [a, c, e].forEach((x) => x.remove());
}

// ================================================================================================ Boss 2: Edison
const EA = SPEC.EDISON_ACTIONS;
const EM = (m) => ACT.ultimate.moments[m];
const EM_LEN = () => ACT.ultimate.length;
const EEM = (m) => SPEC.EDISON_ACTIONS.ultimate.moments[m];
const EE_LEN = () => SPEC.EDISON_ACTIONS.ultimate.length;
const EB = BAL.edison;
const spawnE = (loc, yaw = 0, load = false) => M.__spawnBoss(loc, yaw, { load, type: "esb:edison" });
const dynamos = () => M.__entities("esb:dynamo");
const chairs = () => M.__entities("esb:electric_chair");
function onlyE(e, which) {
  const s = st(e);
  for (const k of Object.keys(s.ready)) s.ready[k] = k === which ? 0 : FAR;
  s.gapUntil = 0;
  s.nextDecision = 0;
}

section("Edison spawn: sits on his Dynamo, hops down, title");
{
  const X = 30000;
  const p = M.__spawnPlayer("Tesla", { x: X, y: 64, z: 14 });
  const t0 = now();
  const e = spawnE({ x: X, y: 64, z: 0 });
  tick(1);
  check(actions(e, t0)[0] === "intro", "intro on a fresh spawn");
  const d = dynamos();
  check(d.length === 1 && Math.abs(d[0].location.y - 64) < 0.01, "the Dynamo is placed where he spawned");
  check(Math.abs(e.location.y - (64 + 2.094)) < 0.01, "he sits on top of the Dynamo");
  check(events(e, t0).includes("esb:to_air"), "no gravity while sitting");
  check(!e.applyDamage(10, { cause: "entityAttack", damagingEntity: p }), "cannot be hurt during the intro");
  tick(sec(EA.intro.moments.light));
  check(L.titles.some((x) => x.target === p), "title shown");
  tick(sec(EA.intro.length));
  check(Math.abs(e.location.y - 64) < 0.05 && e.location.z > 2, `hopped down in front of the Dynamo (z ${e.location.z.toFixed(2)})`);
  check(events(e, t0).includes("esb:to_ground") && !st(e).inAir, "gravity back after landing");
  check(e.props["esb:action"] === "none" && events(e, t0).at(-1) === "esb:unlock", "free after the intro");
  check(st(e).dynamo === d[0], "he knows his Dynamo");
  [p, e].forEach((x) => x.remove());
  check(dynamos().length === 0, "Dynamo removed with him");
}

section("Edison bulb toss: three bulbs on the throw frames, shattering bursts");
{
  const X = 32000;
  const e = spawnE({ x: X, y: 64, z: 0 }, 0, true);
  const p = M.__spawnPlayer("Target", { x: X, y: 64, z: 12 });
  tick(2);
  onlyE(e, "bulb_toss");
  const t0 = now();
  check(waitFor(() => st(e).run?.kind === "bulb_toss", 40), "bulb toss chosen at 12 blocks");
  const start = actionTick(e, "bulb_toss", t0);
  tick(sec(EA.bulb_toss.length) + 2);
  const shots = L.shots.filter((x) => x.tick >= start && x.gear.typeId === "esb:volt_bulb");
  check(shots.length === 3, `3 bulbs in phase 1 (got ${shots.length})`);
  const want = ["throw1", "throw2", "throw3"].map((k) => start + sec(EA.bulb_toss.moments[k]));
  check(JSON.stringify(shots.map((x) => x.tick)) === JSON.stringify(want), `thrown on ticks ${want}`);
  check(shots.every((x) => x.owner === e && x.velocity.z > 0.5), "owned by Edison, thrown toward the player");
  const before = dmgTo(p).length;
  M.__projectileHitBlock(shots[0].gear, { x: p.location.x + 0.5, y: 64, z: p.location.z });
  check(dmgTo(p).length === before + 1 && dmgTo(p).at(-1).amount === EB.bulb_toss.burst_damage, "the burst hurts a player next to the impact");
  check(p.hasEffect("slowness"), "and slows them");
  check(L.particles.some((x) => x.id === "esb:glass_shards"), "glass shards");
  [p, e].forEach((x) => x.remove());
}

section("Edison blackout: darkness, invisible, telegraph, reappears behind and backstabs");
{
  const X = 34000;
  const e = spawnE({ x: X, y: 64, z: 0 }, 0, true);
  const p = M.__spawnPlayer("Watcher", { x: X, y: 64, z: 10 });
  p.rotation = { x: 0, y: 180 }; // looking back toward -Z (at Edison)
  tick(2);
  onlyE(e, "vanish");
  st(e).target = p;
  const t0 = now();
  check(waitFor(() => st(e).run?.kind === "vanish", 40), "vanish chosen");
  const start = actionTick(e, "vanish", t0);
  tick(sec(EA.vanish.moments.crush));
  check(p.hasEffect("darkness"), "the lights go out (darkness)");
  tick(sec(EA.vanish.moments.fade - EA.vanish.moments.crush) + 1);
  check(e.hasEffect("invisibility") && st(e).hidden, "Edison is invisible");
  tick(sec(EA.vanish.length - EA.vanish.moments.fade));
  const tel = () => L.particles.filter((x) => x.id === "esb:telegraph" && x.tick > start);
  tick(sec(EB.vanish.lurk));
  check(tel().length >= 2, `telegraph sparks mark where he will appear (${tel().length})`);
  check(tel().every((x) => x.at.z > 10.5), "the telegraph is behind the player");
  const bs = actionTick(e, "backstab", t0);
  check(bs !== undefined, "backstab after the lurk");
  check(!e.hasEffect("invisibility") && !st(e).hidden, "visible again when he strikes");
  check(e.location.z > 11 && Math.abs(e.location.z - 11.8) < 0.1, `reappeared behind the player (z ${e.location.z.toFixed(2)})`);
  tick(sec(EA.backstab.length) + 2);
  const d = dmgTo(p, t0);
  check(d.length === 1 && d[0].tick === bs + sec(EA.backstab.moments.stab) && d[0].amount === EB.vanish.damage,
    `backstab lands on the stab frame for ${EB.vanish.damage}`);
  check(e.props["esb:action"] === "none" && events(e, t0).at(-1) === "esb:unlock", "ends unlocked");
  [p, e].forEach((x) => x.remove());
}

section("Edison overload: chain lightning from the Dynamo, cover protects");
{
  const X = 36000;
  const e = spawnE({ x: X, y: 64, z: 0 }, 0, true);
  const dyn = M.__dims.overworld.spawnEntity("esb:dynamo", { x: X + 6, y: 64, z: 0 });
  st(e).dynamo = dyn;
  const a = M.__spawnPlayer("Open", { x: X + 6, y: 64, z: 10 });
  const b = M.__spawnPlayer("Friend", { x: X + 9, y: 64, z: 13 });
  const hid = M.__spawnPlayer("Hidden", { x: X + 6, y: 64, z: -10 });
  M.__solids.push({ min: { x: X + 2, y: 64, z: -7 }, max: { x: X + 11, y: 72, z: -6 } }); // a wall
  tick(2);
  onlyE(e, "overload");
  st(e).target = a;
  const t0 = now();
  check(waitFor(() => st(e).run?.kind === "overload", 40), "overload chosen while the Dynamo stands");
  const start = actionTick(e, "overload", t0);
  check(Math.hypot(e.location.x - (X + 6), e.location.z - 1.7) < 0.1, "blinked to the Dynamo's levers");
  tick(sec(EA.overload.moments.grab) + 1);
  check(dyn.props["esb:mode"] === "charging", "Dynamo charging (bulbs flare)");
  tick(sec(EA.overload.length));
  const dis = start + sec(EA.overload.moments.discharge);
  check(dmgTo(a, t0).some((x) => x.tick === dis && x.amount === EB.overload.damage), "player in the open is struck");
  check(dmgTo(b, t0).some((x) => x.tick === dis), "the bolt chains to the player next to them");
  check(dmgTo(hid, t0).length === 0, "the player behind the wall is safe");
  check(dyn.props["esb:mode"] === "idle", "Dynamo back to idle");
  check(L.particles.filter((x) => x.id === "esb:zap" && x.tick === dis).length >= 6, "bolt drawn with sparks");
  [a, b, hid, e].forEach((x) => x.remove());
}

section("Edison electric chair: strapped in when you stay, free when you step off or break it");
{
  const X = 38000;
  const e = spawnE({ x: X, y: 64, z: 0 }, 0, true);
  const p = M.__spawnPlayer("Condemned", { x: X, y: 64, z: 9 });
  const q = M.__spawnPlayer("Helper", { x: X + 2, y: 64, z: 9 });
  tick(2);
  onlyE(e, "chair");
  st(e).target = p;
  const t0 = now();
  check(waitFor(() => st(e).run?.kind === "chair", 40), "chair chosen");
  const start = actionTick(e, "chair", t0);
  tick(sec(EA.chair.moments.snap) + 1);
  const c = chairs()[0];
  check(!!c && Math.hypot(c.location.x - X, c.location.z - 9) < 0.01, "chair appears under the player");
  check(L.actionbars.some((x) => x.target === p && x.t.rawtext[0].translate === "esb.msg.chair"), "warning to step off");
  tick(sec(EA.chair.moments.lock - EA.chair.moments.snap));
  check(st(e).chair?.locked && c.props["esb:state"] === "locked", "player stayed: locked in");
  check(p.hasEffect("slowness") && Math.abs(p.location.y - (64 + 0.575)) < 0.01, "strapped to the seat");
  tick(25);
  const shocks = dmgTo(p, start).length;
  check(shocks >= 2, `shocked while strapped (${shocks} times)`);
  p.location = { x: X + 3, y: 64, z: 9 }; // tries to walk away
  tick(1);
  check(Math.hypot(p.location.x - X, p.location.z - 9) < 0.01, "pulled back into the chair");
  c.applyDamage(100, { cause: "entityAttack", damagingEntity: q }); // the helper breaks it
  tick(2);
  check(!st(e).chair && !p.hasEffect("slowness"), "breaking the chair frees the player");
  const after = dmgTo(p).length;
  tick(30);
  check(dmgTo(p).length === after, "no more shocks after escaping");
  // second cast: the player steps off in time
  tick(sec(EA.chair.length));
  onlyE(e, "chair");
  st(e).target = p;
  const t1 = now();
  waitFor(() => st(e).run?.kind === "chair", 40);
  tick(sec(EA.chair.moments.snap) + 1);
  p.location = { x: p.location.x + 3, y: 64, z: p.location.z };
  tick(sec(EA.chair.moments.lock - EA.chair.moments.snap) + 1);
  check(!st(e).chair && chairs().length === 0 && !p.hasEffect("slowness"), "stepping off dodges the chair");
  check(dmgTo(p, t1).length === 0, "no damage when dodged");
  [p, q, e].forEach((x) => x.remove());
}

section("Edison unplugged: breaking the Dynamo stuns him and he takes extra damage");
{
  const X = 40000;
  const e = spawnE({ x: X, y: 64, z: 0 }, 0, true);
  const dyn = M.__dims.overworld.spawnEntity("esb:dynamo", { x: X + 4, y: 64, z: 0 });
  st(e).dynamo = dyn;
  const p = M.__spawnPlayer("Breaker", { x: X + 4, y: 64, z: 3 });
  tick(2);
  const t0 = now();
  dyn.applyDamage(1000, { cause: "entityAttack", damagingEntity: p });
  tick(1);
  check(e.props["esb:action"] === "stunned", "stunned when the Dynamo breaks");
  check(L.messages.some((m) => m.target === p && m.m.rawtext[0].translate === "esb.msg.unplugged"), "players are told");
  const hp0 = e.health.currentValue;
  e.applyDamage(10, { cause: "entityAttack", damagingEntity: p });
  check(Math.abs(hp0 - e.health.currentValue - 10 * EB.dynamo.stun_damage_mult) < 1e-6, "takes 1.5x damage while stunned");
  tick(sec(EB.dynamo.stun_seconds) + 2);
  check(e.props["esb:action"] === "none" && events(e, t0).at(-1) === "esb:unlock", "recovers");
  onlyE(e, "overload");
  tick(20);
  check(!actions(e, t0).includes("overload"), "no overload without a Dynamo");
  [p, e].forEach((x) => x.remove());
}

section("Edison phase 2 (Current War): AC textures, Dynamo rebuilt, double blackout");
{
  const X = 42000;
  const e = spawnE({ x: X, y: 64, z: 0 }, 0, true);
  const p = M.__spawnPlayer("Westinghouse", { x: X, y: 64, z: 10 });
  p.rotation = { x: 0, y: 180 };
  tick(2);
  const t0 = now();
  e.health.currentValue = e.health.effectiveMax * 0.45;
  tick(2);
  check(st(e).run?.kind === "transform" && e.props["esb:phase"] === 2, "transforms at half health, phase 2");
  check(!e.applyDamage(20, { cause: "entityAttack", damagingEntity: p }), "invulnerable while transforming");
  tick(sec(EA.transform.length));
  const d = dynamos();
  check(d.length === 1 && d[0].props["esb:phase"] === 2, "Dynamo rebuilt and supercharged (AC)");
  check(d[0] && d[0].health.currentValue === EB.dynamo.health_phase2, "Dynamo at phase 2 health");
  check(events(e, t0).includes("esb:unlock_fast"), "faster in phase 2");
  onlyE(e, "vanish");
  st(e).target = p;
  const t1 = now();
  waitFor(() => st(e).run?.kind === "vanish", 40);
  tick(sec(EA.vanish.length + EB.vanish.lurk_phase2 + EA.backstab.length) * 2 + 10);
  const stabs = actions(e, t1).filter((a) => a === "backstab").length;
  check(stabs === 2, `blinks and backstabs twice in phase 2 (${stabs})`);
  check(dmgTo(p, t1).length === 2 && dmgTo(p, t1).every((x) => x.amount === EB.vanish.damage_phase2), "phase 2 backstab damage");
  check(L.particles.some((x) => x.id === "esb:telegraph" && x.tick > t1 && x.vars?.["variable.ac"] === 1), "AC blue sparks");
  [p, e].forEach((x) => x.remove());
}

section("Edison death: sequence, kill credit, the Dynamo powers down");
{
  const X = 44000;
  const e = spawnE({ x: X, y: 64, z: 0 }, 0, true);
  const dyn = M.__dims.overworld.spawnEntity("esb:dynamo", { x: X + 4, y: 64, z: 0 });
  st(e).dynamo = dyn;
  const p = M.__spawnPlayer("Victor", { x: X, y: 64, z: 3 });
  tick(2);
  e.health.currentValue = 4;
  const t0 = now();
  check(!e.applyDamage(30, { cause: "entityAttack", damagingEntity: p }), "lethal hit cancelled");
  tick(1);
  check(e.props["esb:action"] === "death", "death sequence");
  tick(sec(EA.death.moments.fade) + 1);
  check(!dyn.isValid, "the Dynamo powers down with him");
  tick(sec(EA.death.length));
  const died = L.died.find((x) => x.entity === e);
  check(died && died.src.damagingEntity === p && died.tick - t0 >= sec(EA.death.length), "dies after the animation, player credited");
  tick(30);
  p.remove();
}

section("Edison's Patent summons him; the Volt Shiv sparks on hits");
{
  const X = 46000;
  const p = M.__spawnPlayer("Inventor2", { x: X, y: 64, z: 0 });
  p.container.setItem(0, { typeId: "esb:edison_patent", amount: 1 });
  const t0 = now();
  M.__useItem(p, "esb:edison_patent");
  check(!p.container.getItem(0), "patent consumed");
  tick(55);
  const list = M.__entities("esb:edison");
  check(list.length === 1 && actions(list[0], t0)[0] === "intro", "Edison summoned with his intro");
  check(dynamos().length === 1, "with his Dynamo");
  list.forEach((x) => x.remove());
  p.container.setItem(0, { typeId: "esb:volt_shiv", amount: 1 });
  const mob = M.__spawnPlayer("Dummy", { x: X + 1, y: 64, z: 1 });
  let procs = 0;
  for (let i = 0; i < 30; i++) {
    const n0 = dmgTo(mob).length;
    M.__meleeHit(p, mob, 1);
    tick(1);
    if (dmgTo(mob).length === n0 + 2) procs++;
    mob.health.currentValue = 20;
  }
  check(procs > 3 && procs < 20, `bonus jolt procs sometimes (${procs}/30)`);
  check(L.particles.some((x) => x.id === "esb:volt_spark" && x.tick >= t0), "sparks on hit");
  [p, mob].forEach((x) => x.remove());
}

section("Edison soak: 3 minutes vs two players, Dynamo broken mid-fight");
{
  const X = 48000;
  const t0 = now();
  const e = spawnE({ x: X, y: 64, z: 0 });
  const a = M.__spawnPlayer("A2", { x: X + 3, y: 64, z: 4 });
  const c = M.__spawnPlayer("C2", { x: X - 6, y: 64, z: 14 });
  tick(2);
  for (let i = 0; i < sec(180); i++) {
    const ang = i / 40;
    if (!chairs().length) a.location = { x: X + Math.cos(ang) * 4, y: 64, z: Math.sin(ang) * 4 + 4 };
    c.location = { x: X + Math.cos(-ang * 0.7) * 15, y: 64, z: Math.sin(-ang * 0.7) * 15 };
    a.health.currentValue = 20;
    c.health.currentValue = 20;
    if (i % 40 === 0 && !st(e)?.dying && !st(e)?.invulnerable) e.applyDamage(4, { cause: "entityAttack", damagingEntity: i % 80 === 0 ? a : c });
    if (i === sec(40)) dynamos().forEach((d) => d.applyDamage(1000, { cause: "entityAttack", damagingEntity: c }));
    tick();
  }
  const seen = new Set(actions(e, t0));
  for (const k of ["intro", "bulb_toss", "vanish", "backstab", "overload", "chair", "stunned", "transform", "ultimate"]) check(seen.has(k), `soak used ${k}`);
  check(!st(e)?.hidden && !st(e)?.inAir, "not stuck invisible or in the air");
  check(chairs().length <= 1 && dynamos().length <= 1, "no leftover chairs / dynamos");
  check(FX.fxStats.maxPerTick <= FX.FX_BUDGET_PER_TICK, `particle budget respected (max ${FX.fxStats.maxPerTick}/tick)`);
  [a, c, e].forEach((x) => x.remove());
}

// ================================================================================================ ULTIMATES
const UD = BAL.ultimate;
const UE = EB.ultimate;
function onlyUlt(e) {
  const s = st(e);
  for (const k of Object.keys(s.ready)) s.ready[k] = k === "ultimate" ? 0 : FAR;
  s.gapUntil = 0;
  s.nextDecision = 0;
}

section("ULTIMATE Opus Magnum: rises over an arena sigil, gear spiral, the slam spares the 4 sanctuaries");
{
  const X = 60000;
  const e = M.__spawnBoss({ x: X, y: 64, z: 0 }, 0, { load: true });
  e.props["esb:phase"] = 2;
  const d = UD.radius * 0.62;
  const safeP = M.__spawnPlayer("Sheltered", { x: X + d + 0.5, y: 64, z: d - 0.5 });
  const open = M.__spawnPlayer("Exposed", { x: X + 5, y: 64, z: 3 });
  const far = M.__spawnPlayer("Faraway", { x: X + UD.radius + 6, y: 64, z: 0 });
  for (const p of [safeP, open, far]) p.health = { currentValue: 1000, effectiveMax: 1000 };
  tick(2);
  st(e).phase = 2;
  e.health.currentValue = e.health.effectiveMax * 0.3;
  onlyUlt(e);
  st(e).target = open;
  const t0 = now();
  check(waitFor(() => st(e).run?.kind === "ultimate", 40), "Opus Magnum starts below 35% health");
  const start = actionTick(e, "ultimate", t0);
  check(!e.applyDamage(50, { cause: "entityAttack", damagingEntity: open }), "invulnerable during the ultimate");
  tick(sec(EM("sigil")) + 3);
  const sig = L.spawned.filter((x) => x.typeId === "esb:vitruvian_sigil" && x.tick >= start).map((x) => x.entity);
  check(sig.length === 5 && sig.filter((x) => x.props["esb:radius"] === UD.radius).length === 1, "arena sigil (radius 16) + 4 sanctuaries");
  check(L.titles.some((x) => x.target === open && x.t.rawtext[0].translate === "esb.title.opus"), "OPUS MAGNUM title");
  check(e.location.y > 64 + UD.height - 0.6, `rises into the air (y ${e.location.y.toFixed(1)})`);
  tick(sec(EM("land")) - sec(EM("sigil")) - 3);
  const gears = L.shots.filter((x) => x.tick >= start && x.gear.typeId === "esb:brass_gear");
  const waves = Math.ceil((sec(EM("barrage_end")) - sec(EM("barrage"))) / UD.wave_every_ticks);
  check(gears.length === waves * UD.gears_per_wave, `gear spiral: ${gears.length} gears in ${waves} waves`);
  const dirs = new Set(gears.slice(0, 9).map((g) => Math.round(Math.atan2(g.velocity.x, g.velocity.z) * 10)));
  check(dirs.size === 9, "each wave rotates (spiral)");
  tick(2);
  const land = start + sec(EM("land"));
  check(dmgTo(open, t0).some((x) => x.tick === land && x.amount === UD.damage), `exposed player takes ${UD.damage} on the slam`);
  check(dmgTo(safeP, t0).length === 0, "player in a sanctuary is safe");
  check(dmgTo(far, t0).length === 0, "player outside the sigil is safe");
  check(L.commands.some((c) => c.tick === land && c.target === open), "screen shake on the slam");
  check(Math.abs(e.location.y - 64) < 0.05 && !st(e).inAir, "back on the ground");
  tick(sec(EM_LEN()) + 2);
  check(e.props["esb:action"] === "none" && sig.every((x) => !x.isValid), "ends cleanly, sigils removed");
  const ended = actionTick(e, "none", start);
  check(ended === start + sec(EM_LEN()) && st(e).ready.ultimate === ended + sec(UD.cooldown) && !st(e).invulnerable,
    "ends after 9 s, 45 s cooldown, vulnerable again");
  [safeP, open, far, e].forEach((x) => x.remove());
}

section("ULTIMATE Let There Be Light: darkness, Sun Bulbs, marked strikes, a flash weakened by broken bulbs");
{
  const X = 62000;
  const e = spawnE({ x: X, y: 64, z: 0 }, 0, true);
  e.props["esb:phase"] = 2;
  const a = M.__spawnPlayer("Open", { x: X, y: 64, z: 14 });
  const h = M.__spawnPlayer("Hider", { x: X, y: 64, z: -14 });
  M.__solids.push({ min: { x: X - 6, y: 64, z: -10 }, max: { x: X + 6, y: 80, z: -9 } }); // cover
  for (const p of [a, h]) p.health = { currentValue: 1000, effectiveMax: 1000 };
  tick(2);
  st(e).phase = 2;
  e.health.currentValue = e.health.effectiveMax * 0.3;
  onlyUlt(e);
  st(e).target = a;
  const t0 = now();
  check(waitFor(() => st(e).run?.kind === "ultimate", 40), "Let There Be Light starts below 35% health");
  const start = actionTick(e, "ultimate", t0);
  tick(sec(EEM("snap")) + 1);
  check(a.hasEffect("darkness") && h.hasEffect("darkness"), "the world goes dark");
  check(L.titles.some((x) => x.target === a && x.t.rawtext[0].translate === "esb.title.light"), "LET THERE BE LIGHT title");
  tick(sec(EEM("bulbs")) - sec(EEM("snap")) + 1);
  const bulbs = M.__entities("esb:sun_bulb");
  check(bulbs.length === UE.bulbs, `${UE.bulbs} Sun Bulbs rise around him`);
  check(bulbs.every((b) => Math.abs(Math.hypot(b.location.x - X, b.location.z) - UE.ring_radius) < 0.01), "in a ring");
  check(e.location.y > 64 + UE.hover - 0.6, `hovers like a sun (y ${e.location.y.toFixed(1)})`);
  check(!e.applyDamage(50, { cause: "entityAttack", damagingEntity: a }), "invulnerable during the ultimate");
  tick(sec(EEM("strikes")) - sec(EEM("bulbs")) + UE.strike_delay_ticks + 2);
  check(M.__entities("esb:volt_marker").length >= 1 || L.spawned.some((x) => x.typeId === "esb:volt_marker" && x.tick >= start), "strike marks appear under players");
  // smash 3 of the 6 bulbs
  for (const b of bulbs.slice(0, 3)) b.applyDamage(100, { cause: "entityAttack", damagingEntity: a });
  tick(sec(EEM("strikes_end")) - sec(EEM("strikes")));
  const strikes = dmgTo(a, start).filter((x) => x.amount === UE.strike_damage).length + dmgTo(h, start).filter((x) => x.amount === UE.strike_damage).length;
  check(strikes >= 3, `lightning strikes hit the marked spots (${strikes})`);
  check(L.spawned.some((x) => x.typeId === "esb:arc_bolt" && x.tick >= start), "lightning bolts drawn");
  tick(sec(EEM("flash")) - sec(EEM("strikes_end")) + 1);
  const flash = start + sec(EEM("flash"));
  const fa = dmgTo(a, t0).filter((x) => x.tick === flash);
  check(fa.length === 1 && Math.abs(fa[0].amount - UE.flash_damage * 3 / UE.bulbs) < 1e-6, `flash halved by 3 broken bulbs (${fa[0]?.amount})`);
  check(a.hasEffect("blindness"), "blinding flash");
  check(dmgTo(h, t0).filter((x) => x.tick === flash).length === 0, "the player behind cover is safe from the flash");
  check(M.__entities("esb:sun_bulb").length === 0, "bulbs shatter after the flash");
  check(L.commands.some((c) => c.tick === flash), "screen shake on the flash");
  tick(sec(EE_LEN()) - sec(EEM("flash")) + 2);
  check(Math.abs(e.location.y - 64) < 0.05 && !st(e).inAir && e.props["esb:action"] === "none", "lands and recovers");
  check(M.__entities("esb:volt_marker").length === 0 && M.__entities("esb:arc_bolt").length === 0, "no marks or bolts left behind");
  // second cast with every bulb broken: the light fizzles
  onlyUlt(e);
  st(e).ready.ultimate = 0;
  const t1 = now();
  waitFor(() => st(e).run?.kind === "ultimate", 40);
  const s1 = actionTick(e, "ultimate", t1);
  tick(sec(EEM("bulbs")) + 1);
  for (const b of M.__entities("esb:sun_bulb")) b.applyDamage(100, { cause: "entityAttack", damagingEntity: a });
  tick(sec(EEM("flash")) - sec(EEM("bulbs")) + 1);
  check(dmgTo(a, t1).filter((x) => x.tick === s1 + sec(EEM("flash"))).length === 0, "all bulbs broken: no flash damage");
  check(L.messages.some((m) => m.target === a && m.m.rawtext[0].translate === "esb.msg.light_fizzle" && m.tick >= t1), "players told the light fizzled");
  [a, h, e].forEach((x) => x.remove());
}

// ------------------------------------------------------------------------------------------ global checks
section("engine calls");
const VANILLA_SOUNDS = new Set(Object.values(FX.SND));
check(L.sounds.every((x) => VANILLA_SOUNDS.has(x.id)), "only the known vanilla sound events are played");
check(L.sounds.every((x) => x.opts && x.opts.volume > 0 && x.opts.pitch > 0), "sound options valid");
for (const i of M.__issues) check(false, `mock issue: ${i}`);
check(M.__issues.length === 0, "no invalid engine calls");

console.log(`\nsmoke: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
