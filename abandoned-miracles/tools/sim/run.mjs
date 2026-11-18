/**
 * Headless test suite: runs the shipped script bundle through whole encounters.
 *
 *   node tools/sim/run.mjs [--boss vesperra] [--only attacks] [--verbose] [--json out.json]
 *
 * What a pass means: the scripts behaved as specified against the strict mock
 * (see mock-server.mjs). What it does not mean: that the game renders, sounds
 * or paces things the same way. In-game verification is tracked separately.
 */
import fs from "node:fs";
import path from "node:path";
import { addPlayer } from "./mock-server.mjs";
import { uiSim } from "./mock-server-ui.mjs";
import { Bot, ROOT, WALK, count, events, freshWorld, log, run, setSeed, sim, useSeal } from "./harness.mjs";

const args = process.argv.slice(2);
const opt = (name) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};
const VERBOSE = args.includes("--verbose");
const ONLY = opt("--only");
const BOSS = opt("--boss");
if (opt("--seed")) setSeed(Number(opt("--seed")));
const ALL_KEYS = ["vesperra", "cantor", "nomos", "orison"];
const CENTRE = { x: 0.5, y: 64, z: 0.5 };
const TOP = { Intro: "INTRO", P1: "PHASE_1", Tr: "PHASE_TRANSITION", P2: "PHASE_2", Death: "DEATH" };

const results = [];
const metrics = {};
let current = "";

function check(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function test(name, fn) {
  if (ONLY && !name.includes(ONLY)) return;
  current = name;
  const t0 = Date.now();
  try {
    const note = await fn();
    if (log.errors.length) throw new Error("script errors: " + log.errors.slice(0, 3).join(" | "));
    if (sim.errors.length) throw new Error("mock violations: " + sim.errors.slice(0, 3).join(" | "));
    results.push({ name, ok: true, ms: Date.now() - t0, note: note ?? "" });
    if (VERBOSE) console.log(`  ok   ${name}${note ? "  - " + note : ""}`);
  } catch (e) {
    results.push({ name, ok: false, ms: Date.now() - t0, note: String(e.message ?? e) });
    console.log(`  FAIL ${name}\n       ${String(e.message ?? e).split("\n")[0]}`);
  }
}

/** Summon `key` with `n` players standing south of the centre; returns the encounter. */
async function begin(key, n = 1, at = null) {
  const w = await freshWorld();
  const players = [];
  for (let i = 0; i < n; i++) {
    const a = ((i - (n - 1) / 2) * 30 * Math.PI) / 180;
    players.push(addPlayer(`Bot${i + 1}`, at?.[i] ?? { x: CENTRE.x + Math.sin(a) * 8, y: 64, z: CENTRE.z - Math.cos(a) * 8 }));
  }
  useSeal(w.mc, players[0], key, CENTRE);
  const enc = w.manager.list()[0];
  check(enc, `summon of ${key} failed: ${JSON.stringify(sim.stats.messages.slice(-2))}`);
  return { ...w, enc, players };
}

function untilTop(enc, top, bots = [], max = 4000) {
  run(max, bots, () => enc.sm.top === top || enc.ended);
  check(enc.sm.top === top, `never reached ${top} (stuck in ${enc.sm.top}/${enc.sm.sub})`);
}

function toPhase(ctx, phase, bots = []) {
  untilTop(ctx.enc, TOP.P1, bots);
  if (phase === 2) {
    ctx.enc.force("phase2");
    untilTop(ctx.enc, TOP.P2, bots);
  }
}

/** Force one attack and run until the boss is idle again. Returns ticks taken. */
function forceAttack(enc, def, bots, max = 900) {
  enc.scheduler.forced = def.id;
  enc.nextAttackAt = 0;
  const before = count("attack", (e) => e.id === def.id);
  run(200, bots, () => count("attack", (e) => e.id === def.id) > before);
  check(count("attack", (e) => e.id === def.id) > before, `${def.id} was never started (sub ${enc.sm.sub})`);
  const tag = enc.currentAttack ? `atk` : "";
  const n = run(max, bots, () => !enc.sm.busy);
  check(!enc.sm.busy, `${def.id} never finished (sub ${enc.sm.sub})`);
  check(tag !== undefined, "");
  return n;
}

function place(player, enc, dist, bearing) {
  const yaw = ((enc.loco.yaw + bearing) * Math.PI) / 180;
  const b = enc.boss._loc;
  const p = enc.arena.clampInside(b.x - Math.sin(yaw) * dist, b.z + Math.cos(yaw) * dist, 1);
  player._loc.x = p.x;
  player._loc.z = p.z;
  player._vel = { x: 0, y: 0, z: 0 };
  player._hurtAt = -100;
  player._health.currentValue = 20;
}

const STAND_SPOTS = [[4, 0], [9, 0], [3.5, 90], [3.5, -90], [5, 180], [13, 20], [7, 45]];
const DODGE_SPOTS = [[4, 0], [9, 10], [3.5, 100], [12, -30]];

// --------------------------------------------------------------------------- generic suites

async function suiteSummon(key) {
  await test(`${key}: summon on suitable ground`, async () => {
    const { enc, players, CONFIG } = await begin(key);
    check(enc.key === key, "wrong boss");
    check(sim.stats.spawned.filter((t) => t.startsWith("abm:")).length === 1, "expected exactly one boss entity");
    check(players[0]._held === undefined, "seal was not consumed in survival");
    check(enc.invulnerable && enc.sm.top === TOP.Intro, "boss should start protected in INTRO");
    check(sim.stats.blockWrites === 0, "blocks were modified");
    const s = CONFIG.bosses[key];
    return `arena ${s.arenaShape} r=${s.arenaRadius}`;
  });
  for (const [label, blockAt, reason] of [
    ["a floor full of holes", (x, y, z) => (y < 64 && (x + z) % 2 === 0 ? "air" : null), "floor"],
    ["a low ceiling", (x, y, z) => (y >= 68 ? "solid" : null), "ceiling"],
    ["unloaded chunks", (x) => (x > 6 ? undefined : null), "unloaded"],
    ["water", (x, y) => (y === 63 ? "liquid" : null), "floor"],
  ]) {
    await test(`${key}: summon refused on ${label}`, async () => {
      const w = await freshWorld();
      sim.blockAt = blockAt;
      const p = addPlayer("Bot1", { x: 0.5, y: 64, z: -8 });
      useSeal(w.mc, p, key, CENTRE);
      check(w.manager.list().length === 0, "an encounter was created anyway");
      check(sim.stats.spawned.length === 0, "an entity was spawned anyway");
      check(p._held !== undefined, "the seal was consumed by a failed summon");
      check(sim.stats.messages.some((m) => m.text.includes(`abm.summon.fail.${reason}`)), `no '${reason}' explanation was sent`);
      check(sim.stats.blockWrites === 0, "blocks were modified");
    });
  }
  await test(`${key}: second summon too close is refused`, async () => {
    const ctx = await begin(key);
    const p2 = addPlayer("Bot2", { x: 20, y: 64, z: 0 });
    useSeal(ctx.mc, p2, key, { x: 25.5, y: 64, z: 0.5 });
    check(ctx.manager.list().length === 1, "overlapping encounter was allowed");
    check(sim.stats.messages.some((m) => m.text.includes("abm.summon.fail.overlap")), "no overlap explanation");
  });
  await test(`${key}: /summon entity is adopted into an encounter`, async () => {
    const w = await freshWorld();
    addPlayer("Bot1", { x: 0.5, y: 64, z: -8 });
    const type = { vesperra: "abm:vesperra", cantor: "abm:cantor_xiii", nomos: "abm:nomos", orison: "abm:orison" }[key];
    w.mc.world.getDimension("overworld").spawnEntity(type, CENTRE);
    run(3);
    check(w.manager.list().length === 1, "spawned boss was not adopted");
  });
}

async function suiteAttacks(key) {
  for (const phase of [1, 2]) {
    for (let idx = 1; idx <= 7; idx++) {
      await test(`${key}: P${phase} attack ${idx} executes and can hit`, async () => {
        let name = "";
        let hitSpots = 0;
        let strikes = 0;
        for (const [dist, bearing] of STAND_SPOTS) {
          const ctx = await begin(key);
          const bot = new Bot(ctx.players[0], ctx.enc, { mode: "stand" });
          toPhase(ctx, phase, [bot]);
          const def = ctx.enc.controller.attacks.find((a) => a.index === idx);
          check(def, `no attack with index ${idx}`);
          name = def.name;
          place(ctx.players[0], ctx.enc, dist, bearing);
          const hp0 = ctx.players[0]._health.currentValue;
          const s0 = count("strike");
          const usedBefore = ctx.enc.scheduler.usage.get(def.id) ?? 0;
          forceAttack(ctx.enc, def, [bot]);
          check((ctx.enc.scheduler.usage.get(def.id) ?? 0) === usedBefore + 1, "usage not recorded");
          check(!ctx.enc.scheduler.ready(def), "no cooldown after use");
          run(90, [bot], () => ctx.players[0]._health.currentValue < hp0);
          strikes += count("strike") - s0;
          if (ctx.players[0]._health.currentValue < hp0) hitSpots++;
          check(ctx.enc.sm.inCombat, `left combat state: ${ctx.enc.sm.top}`);
          if (log.errors.length) throw new Error(log.errors[0]);
        }
        check(strikes > 0 || key === "vesperra" && idx === 6, `${name}: no hazard ever resolved`);
        check(hitSpots > 0, `${name}: a stationary player was never damaged in any of ${STAND_SPOTS.length} positions`);
        return `${name}: hit in ${hitSpots}/${STAND_SPOTS.length} standing positions`;
      });
      await test(`${key}: P${phase} attack ${idx} is avoidable at walking speed`, async () => {
        let name = "";
        let taken = 0;
        const detail = [];
        for (const [dist, bearing] of DODGE_SPOTS) {
          const ctx = await begin(key);
          const bot = new Bot(ctx.players[0], ctx.enc, { mode: "dodge", speed: WALK, reaction: 6 });
          toPhase(ctx, phase, [bot]);
          const def = ctx.enc.controller.attacks.find((a) => a.index === idx);
          name = def.name;
          place(ctx.players[0], ctx.enc, dist, bearing);
          const h0 = count("player_hit");
          forceAttack(ctx.enc, def, [bot]);
          run(90, [bot]);
          const h = count("player_hit") - h0;
          taken += h;
          if (h) detail.push(`${dist}@${bearing}:${events("player_hit").slice(-h).map((e) => e.label).join(",")}`);
          if (log.errors.length) throw new Error(log.errors[0]);
        }
        check(taken === 0, `${name}: a walking player with 0.3 s reaction was hit ${taken}x (${detail.join(" ")})`);
        return name;
      });
    }
  }
}

async function suiteFlow(key) {
  await test(`${key}: full encounter loop (solo)`, async () => {
    const ctx = await begin(key);
    const { enc, players, CONFIG } = ctx;
    const stats = CONFIG.bosses[key];
    players[0]._armor = 20;
    players[0]._prot = 16;
    const bot = new Bot(players[0], enc, { mode: "fight", side: 150 });
    let transitionHp = -1;
    let blockedDuringTransition = true;
    let deaths = 0;
    const limit = 20 * 60 * 14;
    const t0 = sim.tick;
    let fightStart = 0;
    for (let i = 0; i < limit && !enc.ended; i++) {
      bot.tick();
      if (enc.sm.top === TOP.P1 && !fightStart) fightStart = sim.tick;
      if (enc.sm.top === TOP.Tr) {
        if (transitionHp < 0) transitionHp = enc.healthFraction();
        const before = enc.boss._health.currentValue;
        enc.boss._hurtAt = -100;
        enc.boss.applyDamage(50, { cause: "entityAttack", damagingEntity: players[0] });
        if (enc.boss._health.currentValue < before) blockedDuringTransition = false;
      }
      if (players[0]._health.currentValue <= 0) {
        deaths++;
        players[0]._health.currentValue = 20;      // respawn in place: the loop under test is the boss's
        players[0]._hurtAt = sim.tick;
      }
      sim.step();
    }
    check(enc.ended, `encounter did not end within ${limit / 1200} minutes (state ${enc.sm.top}, hp ${enc.healthFraction().toFixed(2)})`);
    const hist = enc.sm.history.join(">");
    check(hist === "INTRO>PHASE_1>PHASE_TRANSITION>PHASE_2>DEATH", `state history ${hist}`);
    check(Math.abs(transitionHp - stats.phase2At) < 0.002, `phase II began at ${(transitionHp * 100).toFixed(1)}% not ${stats.phase2At * 100}%`);
    check(blockedDuringTransition, "boss took damage during the phase transition");
    check(sim.stats.items.some((i) => i.typeId.startsWith("abm:") && !i.typeId.includes("seal")), "no trophy was awarded");
    check(sim.stats.commands.some((c) => c.includes(`"abm/${key}"`)), "loot table was not rolled");
    check(enc.boss._events.includes("abm:hide_bar") && enc.boss._events.includes("abm:become_remnant"), "remnant events not triggered");
    check(ctx.manager.list().length === 0, "encounter still registered after defeat");
    check(enc.timeline.pending() === 0, `${enc.timeline.pending()} tasks left on the timeline`);
    const helpers = [...sim.entities.values()].filter((e) => e.isValid && e.hasTag("abm_helper"));
    check(helpers.length === 0, `${helpers.length} helper entities left behind`);
    const used = [...enc.scheduler.usage.entries()];
    check(used.length === 7, `only ${used.length}/7 attacks were ever chosen by the AI: ${used.map((u) => u[0]).join(",")}`);
    const hp0 = players[0]._health.currentValue;
    run(200, [bot]);
    check(players[0]._health.currentValue >= hp0, "player was damaged after the encounter ended");
    run(700);
    check(!enc.boss.isValid, "remnant never despawned");
    const secs = (sim.tick - 900 - fightStart) / 20;
    metrics[key] = { ...(metrics[key] ?? {}), soloSeconds: Math.round(secs), soloDeaths: deaths, hitsTaken: count("player_hit"),
      attacksUsed: Object.fromEntries(used), maxParticlesPerTick: sim.stats.maxParticlesPerTick, particles: sim.stats.particles,
      maxEntities: sim.stats.maxEntities, swings: bot.swings, landed: bot.landed };
    return `${Math.floor(secs / 60)}m${String(Math.round(secs % 60)).padStart(2, "0")}s, bot hit ${count("player_hit")}x, died ${deaths}x, ` +
      `peak ${sim.stats.maxParticlesPerTick} particle calls/tick, ${sim.stats.maxEntities} entities`;
  });

  await test(`${key}: boss death during an attack leaves nothing behind`, async () => {
    const ctx = await begin(key);
    const bot = new Bot(ctx.players[0], ctx.enc, { mode: "stand" });
    toPhase(ctx, 2, [bot]);
    const ult = ctx.enc.controller.attacks.find((a) => a.ultimate);
    ctx.enc.scheduler.forced = ult.id;
    ctx.enc.nextAttackAt = 0;
    run(200, [bot], () => ctx.enc.currentAttack?.id === ult.id);
    check(ctx.enc.currentAttack?.id === ult.id, "ultimate did not start");
    run(30, [bot]);
    place(ctx.players[0], ctx.enc, 4, 0);
    ctx.enc.force("death");
    run(2, [bot]);
    check(ctx.enc.sm.top === TOP.Death, "death did not begin");
    const hits = count("player_hit");
    const hp = ctx.players[0]._health.currentValue;
    run(400, [bot]);
    check(count("player_hit") === hits && ctx.players[0]._health.currentValue >= hp, "a hazard struck after the boss began dying");
  });

  await test(`${key}: stagger and cancellation cannot deadlock the state machine`, async () => {
    const ctx = await begin(key);
    const bot = new Bot(ctx.players[0], ctx.enc, { mode: "dodge" });
    toPhase(ctx, 1, [bot]);
    let started = 0;
    for (let round = 0; round < 12; round++) {
      const def = ctx.enc.controller.attacks[round % 7];
      ctx.enc.scheduler.forced = def.id;
      ctx.enc.nextAttackAt = 0;
      run(120, [bot], () => ctx.enc.currentAttack?.id === def.id);
      if (ctx.enc.currentAttack?.id === def.id) started++;
      run(5 + round * 3, [bot]);
      const ok = ctx.enc.stagger(20);
      if (def.interruptible === false) check(!ok || !ctx.enc.currentAttack, "uninterruptible attack state inconsistent");
      run(400, [bot], () => !ctx.enc.sm.busy && ctx.enc.sm.sub !== "STAGGER");
      check(!ctx.enc.sm.busy && ctx.enc.sm.sub !== "STAGGER", `stuck in ${ctx.enc.sm.sub} after staggering ${def.id}`);
    }
    check(started >= 10, `only ${started}/12 forced attacks started`);
    run(600, [bot]);
    check(count("attack") > started, "the AI stopped choosing attacks after the stagger storm");
  });
}

async function suiteMultiplayer(key) {
  await test(`${key}: four players - scaling, targeting, death, leaving, reset`, async () => {
    const ctx = await begin(key, 4);
    const { enc, players, CONFIG } = ctx;
    for (const p of players) {
      p._armor = 20;
      p._prot = 16;
    }
    // different swing cadences, so hits interleave instead of one bot always landing first
    const bots = players.map((p, i) => new Bot(p, enc, { mode: "fight", side: i * 90, damage: i === 2 ? 26 : 8, regen: 20,
      swingEvery: [13, 17, 11, 19][i] }));
    toPhase(ctx, 1, bots);
    const want = 1 + CONFIG.encounter.hpPerExtraPlayer * 3;
    check(Math.abs(enc.hpScale - want) < 1e-6, `hp scale ${enc.hpScale} != ${want}`);
    run(600, bots);
    const focus = enc.targeting.primary(enc.timeline.now);
    check(focus && focus.id === players[2].id, `highest-threat player is not the focus (focus ${focus?.name})`);
    const attacksBefore = count("attack");
    // one player dies, one disconnects mid-fight
    players[0]._health.currentValue = 0;
    players[1]._disconnect();
    run(300, bots);
    check(enc.targeting.count() === 2, `participants ${enc.targeting.count()} after a death and a disconnect`);
    check(Math.abs(enc.hpScale - want) < 1e-6, "hp scale shrank mid-fight");
    check(count("attack") > attacksBefore, "boss stopped attacking after players dropped");
    check(!enc.ended, "encounter ended unexpectedly");
    // the rest walk away: grace period, then reset with the seal refunded
    for (const p of [players[2], players[3]]) {
      p._loc.x += 80;
    }
    for (const b of bots) b.mode = "stand";
    run(60, bots);
    check(enc.sm.sub === "RESET", `expected RESET wait, got ${enc.sm.sub}`);
    const hits = count("player_hit");
    run(CONFIG.encounter.resetGraceTicks + 40, bots);
    check(enc.ended && ctx.manager.list().length === 0, "encounter did not reset after being abandoned");
    check(!enc.boss.isValid, "boss entity was not removed on reset");
    check(sim.stats.items.some((i) => i.typeId.includes("seal")), "seal was not refunded");
    check(count("player_hit") === hits, "players were hit after leaving");
    check([...sim.entities.values()].filter((e) => e.isValid && e.hasTag("abm_helper")).length === 0, "helpers left after reset");
    return `scale x${want.toFixed(2)}`;
  });

  await test(`${key}: a player joining mid-fight is included and raises the scale`, async () => {
    const ctx = await begin(key, 1);
    const { enc, players, CONFIG } = ctx;
    const bots = [new Bot(players[0], enc, { mode: "fight" })];
    toPhase(ctx, 1, bots);
    run(200, bots);
    const late = addPlayer("Late", { x: 6, y: 64, z: -6 });
    bots.push(new Bot(late, enc, { mode: "fight", side: 120 }));
    run(40, bots);
    check(enc.targeting.count() === 2, "late player is not a participant");
    check(Math.abs(enc.hpScale - (1 + CONFIG.encounter.hpPerExtraPlayer)) < 1e-6, `scale ${enc.hpScale} did not grow for the late player`);
  });

  await test(`${key}: two encounters at once stay independent`, async () => {
    const w = await freshWorld();
    const a = addPlayer("A", { x: 0.5, y: 64, z: -8 });
    const b = addPlayer("B", { x: 300.5, y: 64, z: -8 });
    useSeal(w.mc, a, key, CENTRE);
    useSeal(w.mc, b, key, { x: 300.5, y: 64, z: 0.5 });
    const [ea, eb] = w.manager.list();
    check(ea && eb, "second encounter was not created");
    const bots = [new Bot(a, ea, { mode: "stand" }), new Bot(b, eb, { mode: "dodge" })];
    run(700, bots, () => ea.sm.top === TOP.P1 && eb.sm.top === TOP.P1);
    run(900, bots);
    check(ea.targeting.participants().every((p) => p.id === a.id), "encounter A sees players from B");
    check(eb.targeting.participants().every((p) => p.id === b.id), "encounter B sees players from A");
    w.manager.cancel(ea);
    run(200, bots);
    check(!eb.ended && eb.sm.inCombat, "cancelling one encounter disturbed the other");
    check(count("attack", (e) => e.boss === key) > 2, "bosses did not attack");
  });
}

async function suitePersistence(key) {
  await test(`${key}: unload and reload resumes in the same phase without replaying the intro`, async () => {
    const ctx = await begin(key);
    const { enc, players } = ctx;
    const bot = new Bot(players[0], enc, { mode: "dodge" });
    toPhase(ctx, 2, [bot]);
    run(120, [bot]);
    const boss = enc.boss;
    const extra = JSON.stringify(enc.controller.extra());
    const hp = boss._health.currentValue;
    // the chunk unloads
    boss._valid = false;
    sim.entities.delete(boss.id);
    run(5, [bot]);
    check(enc.ended && ctx.manager.list().length === 0, "encounter was not released when the boss unloaded");
    check(enc.timeline.pending() === 0, "tasks left pending on an unloaded encounter");
    const hits = count("player_hit");
    run(200, [bot]);
    check(count("player_hit") === hits, "hazards kept striking after the boss unloaded");
    // ... and loads again
    boss._valid = true;
    sim.entities.set(boss.id, boss);
    ctx.mc.world.afterEvents.entityLoad._fire({ entity: boss });
    run(3, [bot]);
    const again = ctx.manager.list()[0];
    check(again && again !== enc, "boss was not re-adopted after loading");
    check(again.phase === 2 && again.sm.top === TOP.P2, `resumed in ${again.sm.top}`);
    check(!again.invulnerable, "resumed encounter is stuck invulnerable");
    check(JSON.stringify(again.controller.extra()) === extra, "boss-specific state was not restored");
    check(boss._health.currentValue === hp, "health changed across the reload");
    const b2 = new Bot(players[0], again, { mode: "dodge" });
    const resumedAt = sim.tick;
    run(600, [b2]);
    check(count("attack", (e) => e.at > resumedAt) > 0, "boss did not resume attacking");
  });

  await test(`${key}: native death (/kill) still cleans up`, async () => {
    const ctx = await begin(key);
    const bot = new Bot(ctx.players[0], ctx.enc, { mode: "dodge" });
    toPhase(ctx, 1, [bot]);
    run(100, [bot]);
    ctx.enc.boss._die({ cause: "selfDestruct" });
    run(5, [bot]);
    check(ctx.enc.ended && ctx.manager.list().length === 0, "encounter survived the boss's native death");
    check([...sim.entities.values()].filter((e) => e.isValid && e.hasTag("abm_helper")).length === 0, "helpers left behind");
  });
}

async function suiteDamageModel(key) {
  await test(`${key}: player damage model (gear, creative, shield, hit interval)`, async () => {
    const ctx = await begin(key);
    const { enc, players, CONFIG } = ctx;
    toPhase(ctx, 1, []);
    const p = players[0];
    const hit = (spec) => enc.damage.hit(p, spec, enc.timeline.now);
    p._hurtAt = -100;
    let d = hit({ damage: 10 });
    check(Math.abs(d - 10) < 1e-6 && Math.abs(p._health.currentValue - 10) < 1e-6, `unarmoured 10 damage dealt ${d}, hp ${p._health.currentValue}`);
    check(hit({ damage: 10 }) === 0, "second hit inside the hit interval was not refused");
    run(CONFIG.encounter.playerHitIntervalTicks + 1);
    p._health.currentValue = 20;
    p._armor = 20;
    p._prot = 16;
    p._hurtAt = -100;
    d = hit({ damage: 10 });
    const want = 10 * (1 - (CONFIG.damage.armorCap + CONFIG.damage.protectionCap));
    check(Math.abs(d - want) < 1e-6, `enchanted diamond: dealt ${d}, model says ${want}`);
    check(Math.abs(p._health.currentValue - (20 - want)) < 1e-6, "health after hit does not match the model exactly");
    run(12);
    p._mode = "Creative";
    p._hurtAt = -100;
    check(hit({ damage: 30 }) === 0, "creative player was damaged");
    p._mode = "Survival";
    p._shield = true;
    check(hit({ damage: 10, blockable: true }) === 0, "blockable hit went through a shield");
    check(hit({ damage: 10, blockable: false }) > 0, "unblockable hit was stopped by a shield");
    run(12);
    p._shield = false;
    p._hurtAt = -100;
    p._health.currentValue = 3;
    p._armor = 0;
    p._prot = 0;
    hit({ damage: 40 });
    check(p._health.currentValue === 0 && p._deaths === 1, "lethal hit did not kill through the native path");
    return `diamond+ProtIV takes ${(100 - (CONFIG.damage.armorCap + CONFIG.damage.protectionCap) * 100).toFixed(0)}%`;
  });

  await test(`${key}: damage from outside the arena is ignored`, async () => {
    const ctx = await begin(key);
    toPhase(ctx, 1, []);
    const far = addPlayer("Sniper", { x: 70, y: 64, z: 0 });
    const hp = ctx.enc.boss._health.currentValue;
    ctx.enc.boss.applyDamage(20, { cause: "projectile", damagingEntity: far });
    run(2);
    check(ctx.enc.boss._health.currentValue === hp, "boss was damaged from outside its arena");
    check(sim.stats.messages.some((m) => m.to === "Sniper" && m.text.includes("abm.msg.outside")), "outsider was not told why");
    ctx.enc.boss._hurtAt = -100;
    ctx.enc.boss.applyDamage(20, { cause: "fall" });
    check(ctx.enc.boss._health.currentValue === hp, "boss took fall damage");
  });
}

async function suiteCommands(key) {
  await test(`${key}: commands, codex and explicit arena placement`, async () => {
    const w = await freshWorld();
    const p = addPlayer("Op", { x: 0.5, y: 64, z: 0.5 });
    let r = sim.runCommand("abm:summon", p, key);
    check(r.status === 0, "abm:summon failed");
    run(3);
    check(w.manager.list().length === 1, "abm:summon did not create an encounter");
    r = sim.runCommand("abm:debug", p, "info");
    check(r.status === 0 && r.message.includes(key), "abm:debug info");
    r = sim.runCommand("abm:debug", p, "attack", 3);
    check(r.status === 0, "abm:debug attack");
    r = sim.runCommand("abm:dismiss", p);
    run(3);
    check(w.manager.list().length === 0, "abm:dismiss did not end the encounter");
    const placedBefore = sim.stats.structures.length;
    sim.runCommand("abm:arena", p, key);
    run(2);
    check(sim.stats.structures.length === placedBefore + 1, "abm:arena did not place the arena structure");
    // codex: operator opens settings and changes difficulty
    uiSim.answers = [{ canceled: false, selection: w.manager.list().length + countBosses(w) }, { canceled: false, formValues: [2, true, true, false] }];
    const stack = new w.mc.ItemStack("abm:codex");
    w.mc.world.afterEvents.itemUse._fire({ source: p, itemStack: stack });
    await new Promise((res) => setTimeout(res, 5));
    check(w.CONFIG.difficulty === "hard" && w.CONFIG.vfx.density === 0.5, `settings not applied (${w.CONFIG.difficulty}, ${w.CONFIG.vfx.density})`);
    check(typeof sim.worldProps.get("abm:settings") === "string", "settings were not persisted");
    // codex: arena placement asks for confirmation and does nothing when cancelled
    const n = sim.stats.structures.length;
    uiSim.answers = [{ canceled: false, selection: countBosses(w) + 1 }, { canceled: false, selection: 0 }, { canceled: false, selection: 0 }];
    p._hurtAt = -100;
    run(12);
    w.mc.world.afterEvents.itemUse._fire({ source: p, itemStack: stack });
    await new Promise((res) => setTimeout(res, 5));
    check(sim.stats.structures.length === n, "arena was placed without confirmation");
  });
}

function countBosses(w) {
  return ALL_KEYS.filter((k) => w.manager.has(k)).length;
}

// --------------------------------------------------------------------------- main

const t0 = Date.now();
const probe = await freshWorld();
const keys = ALL_KEYS.filter((k) => probe.manager.has(k) && (!BOSS || BOSS === k));
console.log(`simulation: bosses under test: ${keys.join(", ") || "(none)"}`);
for (const key of keys) {
  console.log(`\n== ${key}`);
  await suiteSummon(key);
  await suiteDamageModel(key);
  await suiteAttacks(key);
  await suiteFlow(key);
  await suiteMultiplayer(key);
  await suitePersistence(key);
  await suiteCommands(key);
  // boss-specific scenarios live next to this file: tools/sim/specific/<boss>.mjs
  const specific = path.join(path.dirname(new URL(import.meta.url).pathname), "specific", `${key}.mjs`);
  if (fs.existsSync(specific)) {
    const mod = await import(specific);
    await mod.default({ test, check, begin, toPhase, untilTop, forceAttack, place, run, sim, count, events, log, Bot, TOP, addPlayer, WALK });
  }
}

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} passed in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
for (const [k, m] of Object.entries(metrics)) console.log(`metrics ${k}: ${JSON.stringify(m)}`);
const out = opt("--json") ?? path.join(process.env.ABM_OUT ?? ROOT, "build", "sim_results.json");
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify({ results, metrics }, null, 1));
process.exit(failed.length ? 1 : 0);
