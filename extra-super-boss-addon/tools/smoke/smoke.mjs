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
  for (const k of ["gear_volley", "quake", "vitruvian", "transform", "dive_rise", "dive_hover", "dive_strike"]) {
    check(seen.has(k), `soak used ${k}`);
  }
  const s = st(e);
  check(s && !s.inAir && (s.run === undefined || s.run.kind !== undefined), "state consistent after the soak");
  check(M.__entities("esb:vitruvian_sigil").length <= 1, "no sigils left behind");
  check(FX.fxStats.maxPerTick <= FX.FX_BUDGET_PER_TICK, `particle budget respected (max ${FX.fxStats.maxPerTick}/tick)`);
  [a, c, e].forEach((x) => x.remove());
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
