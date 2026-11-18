/**
 * Boss-specific simulation scenarios for Cantor XIII, The Walking Requiem.
 *
 * What is special about this fight and therefore tested here:
 *   - everything starts on the beat (10 ticks);
 *   - The Silent Measure needs a rhythm to withhold and drives the abm:silent property;
 *   - Twin Resonance owns two helper bells: capped, cleaned up, destroyable, and a stagger when both fall;
 *   - the bells do not survive a phase change, a reset, or the death of the Cantor;
 *   - every measure of The Final Requiem can be walked to from anywhere in the answer before it.
 */
export default async function suite({ test, check, begin, toPhase, untilTop, forceAttack, place, run, sim, count, events, log, Bot, TOP, addPlayer, WALK }) {
  const BELL = "abm:cantor_bell";
  const bells = () => [...sim.entities.values()].filter((e) => e.isValid && e.typeId === BELL);
  const prop = (enc, name) => enc.boss.getProperty(name);
  const settle = (enc, bots, limit = 900) => run(limit, bots, () => !enc.sm.busy);
  const def = (enc, index) => enc.controller.attacks.find((a) => a.index === index);
  /** Force an attack and return as soon as it has started (the scenario watches it run). */
  const start = (enc, index, bots) => {
    const d = def(enc, index);
    const before = count("attack", (e) => e.id === d.id);
    enc.scheduler.forced = d.id;
    enc.nextAttackAt = 0;
    run(200, bots, () => count("attack", (e) => e.id === d.id) > before);
    check(count("attack", (e) => e.id === d.id) > before, `${d.id} was never started (sub ${enc.sm.sub})`);
  };

  await test("cantor: every attack begins on a beat", async () => {
    const ctx = await begin("cantor");
    const { enc, players } = ctx;
    players[0]._armor = 20;
    players[0]._prot = 16;
    const bot = new Bot(players[0], enc, { mode: "dodge" });
    place(players[0], enc, 9, 0);
    run(20 * 75, [bot], () => enc.ended);
    const starts = enc.controller.attackStarts;
    check(starts.length >= 6, `only ${starts.length} attacks in 75 seconds`);
    const off = starts.filter((t) => t % 10 !== 0);
    check(off.length === 0, `${off.length}/${starts.length} attacks started off the beat (${off.slice(0, 4).join(",")})`);
    const beat = sim.stats.particleIds ? sim.stats.particleIds.get?.("abm:cantor_beat") : undefined;
    if (beat !== undefined) check(beat > 20, `the visible pulse was drawn only ${beat} times`);
    return `${starts.length} attacks, all on multiples of 10 ticks`;
  });

  await test("cantor: the Silent Measure needs a rhythm, mutes the pulse and restores it", async () => {
    const ctx = await begin("cantor");
    const { enc, players } = ctx;
    const c = enc.controller;
    const bot = new Bot(players[0], enc, { mode: "dodge" });
    place(players[0], enc, 9, 0);
    const silent = def(enc, 5);
    c.sinceSilent = 0;
    check(silent.weight(enc) === 0, "eligible although no rhythmic attack has been played");
    c.sinceSilent = 2;
    check(silent.weight(enc) > 0, "not eligible after two rhythmic attacks");
    check(prop(enc, "abm:silent") === 0, "abm:silent set before the attack");
    start(enc, 5, [bot]);
    let sawSilent = false;
    let hpAtSilence = players[0]._health.currentValue;
    let hurtWhileSilent = false;
    run(900, [bot], () => {
      if (prop(enc, "abm:silent") === 1) {
        if (!sawSilent) hpAtSilence = players[0]._health.currentValue;
        sawSilent = true;
        if (players[0]._health.currentValue < hpAtSilence) hurtWhileSilent = true;
      }
      return sawSilent && !enc.sm.busy;
    });
    check(sawSilent, "abm:silent never became 1");
    check(!hurtWhileSilent, "damage was dealt during the silence itself");
    check(prop(enc, "abm:silent") === 0, "abm:silent still 1 after the attack");
    check(c.sinceSilent === 0, "rhythm counter was not reset");
    check(silent.weight(enc) === 0, "eligible again immediately after being used");
    // cancelled mid-silence (phase change): the property must not stick
    c.sinceSilent = 2;
    start(enc, 5, [bot]);
    run(400, [bot], () => prop(enc, "abm:silent") === 1);
    check(prop(enc, "abm:silent") === 1, "second silence never began");
    enc.force("phase2");
    run(40, [bot]);
    check(enc.sm.top !== TOP.P1, "the phase change did not begin");
    check(prop(enc, "abm:silent") === 0, "abm:silent stuck at 1 after the attack was cancelled");
    return "weight 0 without rhythm, property 1 only during the rest, cleared on finish and on cancel";
  });

  await test("cantor: Twin Resonance bells are capped at two, pulse, and are cleaned up", async () => {
    const ctx = await begin("cantor");
    const { enc, players } = ctx;
    players[0]._armor = 20;
    players[0]._prot = 16;
    const bot = new Bot(players[0], enc, { mode: "dodge" });
    place(players[0], enc, 9, 0);
    forceAttack(enc, def(enc, 6), [bot]);
    check(bells().length === 2, `${bells().length} bells after Twin Resonance`);
    check(prop(enc, "abm:bells_out") === 1, "abm:bells_out not set while the bells are on the floor");
    const twin = def(enc, 6);
    check(twin.weight(enc) === 0, "Twin Resonance eligible while its bells still stand");
    for (const b of bells()) {
      const l = b.location;
      check(enc.arena.contains(l.x, l.z, 1), `bell placed outside the arena at ${l.x.toFixed(1)},${l.z.toFixed(1)}`);
    }
    const before = count("strike", (e) => e.label === "bell_pulse");
    let most = 0;
    run(260, [bot], () => {
      most = Math.max(most, bells().length);
      return false;
    });
    check(most <= 2, `${most} bells alive at once`);
    const pulses = count("strike", (e) => e.label === "bell_pulse") - before;
    check(pulses >= 2, `bells pulsed only ${pulses} times in 13 seconds`);
    run(260, [bot], () => bells().length === 0);
    check(bells().length === 0, "bells never expired");
    check(prop(enc, "abm:bells_out") === 0, "abm:bells_out still set after the bells expired");
    check(enc.sm.sub !== "STAGGER", "expiry of the bells staggered the boss");
    return `2 bells, ${pulses} pulses, expired and cleaned up`;
  });

  await test("cantor: destroying both bells staggers the Cantor", async () => {
    const ctx = await begin("cantor");
    const { enc, players } = ctx;
    const bot = new Bot(players[0], enc, { mode: "dodge" });
    place(players[0], enc, 9, 0);
    forceAttack(enc, def(enc, 6), [bot]);
    const [b1, b2] = bells();
    check(b1 && b2, "bells were not spawned");
    b1._hurtAt = -100;
    b1.applyDamage(1000, { cause: "entityAttack", damagingEntity: players[0] });
    run(6, [bot]);
    check(enc.sm.sub !== "STAGGER", "staggered after only one bell");
    check(prop(enc, "abm:bells_out") === 1, "abm:bells_out cleared while one bell still stands");
    b2._hurtAt = -100;
    b2.applyDamage(1000, { cause: "entityAttack", damagingEntity: players[0] });
    let staggered = false;
    run(30, [bot], () => (staggered = staggered || enc.sm.sub === "STAGGER"));
    check(staggered, `no stagger after both bells were destroyed (sub ${enc.sm.sub})`);
    check(prop(enc, "abm:bells_out") === 0, "abm:bells_out still set");
    const hp = players[0]._health.currentValue;
    run(120, [bot]);
    check(bells().length === 0, "a destroyed bell is still present");
    check(count("strike", (e) => e.label === "bell_pulse" && e.at > sim.tick - 100) === 0, "a destroyed bell still pulsed");
    check(players[0]._health.currentValue >= hp || enc.currentAttack, "damaged by a bell that no longer exists");
    return "one bell: nothing; both bells: stagger, no orphan pulses";
  });

  await test("cantor: bells do not survive the phase change, the death or a reset", async () => {
    // phase change
    let ctx = await begin("cantor");
    let { enc, players } = ctx;
    let bot = new Bot(players[0], enc, { mode: "dodge" });
    place(players[0], enc, 9, 0);
    forceAttack(enc, def(enc, 6), [bot]);
    check(bells().length === 2, "bells were not spawned (phase change case)");
    toPhase(ctx, 2);
    run(20, [bot]);
    check(bells().length === 0, `${bells().length} bells survived the phase transition`);
    check(prop(enc, "abm:bells_out") === 0, "abm:bells_out survived the phase transition");
    check(prop(enc, "abm:silent") === 0, "abm:silent set in phase II");
    // death
    forceAttack(enc, def(enc, 6), [bot]);
    check(bells().length === 2, "bells were not spawned in phase II");
    enc.force("death");
    run(30, [bot]);
    check(enc.sm.top === TOP.Death, "the death sequence did not begin");
    check(bells().length === 0, `${bells().length} bells survived the Cantor's death`);
    // reset (everyone dead)
    ctx = await begin("cantor");
    ({ enc, players } = ctx);
    bot = new Bot(players[0], enc, { mode: "stand" });
    place(players[0], enc, 9, 0);
    forceAttack(enc, def(enc, 6), [bot]);
    check(bells().length === 2, "bells were not spawned (reset case)");
    players[0]._health.currentValue = 0;
    run(400, [], () => bells().length === 0);
    check(bells().length === 0, `${bells().length} bells survived the reset`);
    return "removed at phase change, at death and at reset";
  });

  await test("cantor: each Final Requiem measure is reachable from the whole of the previous answer", async () => {
    const out = [];
    for (const phase of [1, 2]) {
      const ctx = await begin("cantor");
      const { enc, players } = ctx;
      players[0]._armor = 20;
      players[0]._prot = 16;
      if (phase === 2) toPhase(ctx, 2);
      place(players[0], enc, 9, 0);
      const h0 = log.hazards.length;
      const hits0 = count("player_hit");
      const clock = sim.tick - enc.timeline.now;          // hazards are seen on the world clock, struck on the encounter's
      const bot = new Bot(players[0], enc, { mode: "dodge" });
      forceAttack(enc, def(enc, 7), [bot]);
      const hz = log.hazards.slice(h0).filter((h) => h.kind === "strike" && h.label.startsWith("requiem_"));
      check(hz.length === 4, `phase ${phase}: ${hz.length} measures traced`);
      const a = enc.arena;
      const pts = [];
      for (let x = -a.radius; x <= a.radius; x += 0.5) {
        for (let z = -a.radius; z <= a.radius; z += 0.5) {
          if (Math.hypot(x, z) <= a.radius - 0.8 && Math.hypot(x, z) >= 2.6) pts.push([a.cx + x, a.cz + z]);
        }
      }
      let prev = pts;                                   // before the first measure the player may be anywhere
      let worst = 0;
      hz.forEach((h, i) => {
        const safe = pts.filter(([x, z]) => !h.shape.contains(x, z));
        check(safe.length > 20, `phase ${phase} measure ${i + 1} has no safe floor`);
        const budget = (h.at - (h.seen - clock) - 6) * WALK;      // six ticks to react, then walk
        let far = 0;
        for (const [px, pz] of prev) {
          let best = Infinity;
          for (const [sx, sz] of safe) {
            const d = Math.hypot(sx - px, sz - pz);
            if (d < best) best = d;
          }
          if (best > far) far = best;
        }
        worst = Math.max(worst, far / budget);
        check(far <= budget, `phase ${phase} measure ${i + 1}: a player can be ${far.toFixed(1)} blocks from safety with time to walk ${budget.toFixed(1)}`);
        prev = safe;
      });
      check(count("player_hit") === hits0, `phase ${phase}: the dodging bot was hit ${count("player_hit") - hits0}x`);
      out.push(`P${phase} worst case uses ${(worst * 100).toFixed(0)}% of the time allowed`);
    }
    return out.join("; ");
  });

  await test("cantor: phase II doubles the tolls and keeps the centre while the players are near", async () => {
    const ctx = await begin("cantor");
    const { enc, players } = ctx;
    players[0]._armor = 20;
    players[0]._prot = 16;
    toPhase(ctx, 2);
    place(players[0], enc, 9, 0);
    const bot = new Bot(players[0], enc, { mode: "dodge" });
    const h0 = log.hazards.length;
    forceAttack(enc, def(enc, 1), [bot]);
    const labels = log.hazards.slice(h0).map((h) => h.label);
    check(labels.includes("downbeat") && labels.includes("downbeat_echo"), `phase II downbeat hazards: ${labels.join(",")}`);
    check(prop(enc, "abm:phase") === 2, "abm:phase is not 2");
    const b = enc.boss.location;
    check(enc.arena.contains(b.x, b.z, enc.arena.radius - 9), `the Cantor wandered to ${b.x.toFixed(1)},${b.z.toFixed(1)}`);
    return "second toll present, boss inside its leash";
  });
}
