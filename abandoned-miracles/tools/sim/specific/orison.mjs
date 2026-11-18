/**
 * Orison-specific scenarios: the bounded position history, echoes that land on recorded
 * footprints, predictions that lock, the previewed hour, hourglasses, the exchange, the shadow.
 */
export default async function suite({ test, check, begin, toPhase, forceAttack, place, run, sim, count, events, log, Bot, WALK }) {
  const HOLD = 1e9;
  const heal = (players) => players.forEach((p) => (p._health.currentValue = 20));
  const attack = (enc, index) => enc.controller.attacks.find((a) => a.index === index);
  const near = (a, b, tol) => Math.hypot(a.x - b.x, a.z - b.z) <= tol;
  /** A scripted walker usable wherever the harness accepts bots. */
  const walker = (p, step) => ({
    tick() {
      p._health.currentValue = 20;
      const d = step();
      if (d) {
        p._loc.x += d.x * WALK;
        p._loc.z += d.z * WALK;
      }
    },
  });

  await test("orison: position history is bounded, positions-only, and cleared", async () => {
    const ctx = await begin("orison", 2);
    const { enc, players } = ctx;
    const H = enc.controller.history;
    const K = H.constructor;
    toPhase(ctx, 1, []);
    check(K.CAPACITY === 64 && K.INTERVAL === 4 && K.MAX_PLAYERS === 8, "history limits changed without updating the spec");
    let worst = 0;
    for (let i = 0; i < 700; i++) {
      players.forEach((p, k) => {
        const a = i / 25 + k * 3;
        const q = enc.arena.clampInside(enc.arena.cx + Math.cos(a) * (6 + k * 4), enc.arena.cz + Math.sin(a) * (6 + k * 4), 1);
        p._loc.x = q.x;
        p._loc.z = q.z;
      });
      heal(players);
      run(1);
      worst = Math.max(worst, H.size(players[0].id), H.size(players[1].id));
      check(H.totalSamples() <= K.CAPACITY * K.MAX_PLAYERS, "history grew past its global cap");
    }
    check(worst === K.CAPACITY, `per-player history peaked at ${worst}, expected exactly ${K.CAPACITY}`);
    check(H.trackedPlayers() === 2, `${H.trackedPlayers()} players tracked with two fighting`);
    const sample = H.recent(players[0].id, 3);
    check(sample.length === 3 && sample.every((s) => Object.keys(s).sort().join() === "x,z"), "a history sample holds more than a position");
    check(near(sample[0], players[0]._loc, 1.2), "newest sample is not near the player's current position");
    // a player who leaves the world is forgotten at once
    players[1]._disconnect();
    run(3);
    check(H.size("" + players[1].id) === 0 && H.trackedPlayers() === 1, "a departed player's positions were kept");
    // and nothing survives the encounter
    enc.force("death");
    run(600, [], () => enc.ended);
    check(enc.ended, "encounter did not end");
    check(H.totalSamples() === 0 && H.trackedPlayers() === 0, "history was not cleared when the encounter ended");
    return `cap ${K.CAPACITY} samples x ${K.MAX_PLAYERS} players, one sample per ${K.INTERVAL} ticks`;
  });

  await test("orison: Footstep Echo strikes coordinates the target really occupied, oldest first", async () => {
    for (const phase of [1, 2]) {
      const ctx = await begin("orison");
      const { enc, players } = ctx;
      const p = players[0];
      toPhase(ctx, phase, []);
      enc.nextAttackAt = HOLD;
      place(p, enc, 8, -40);
      const visited = [];
      const dir = { x: 1, z: 0.15 };
      const w = walker(p, () => dir);
      for (let i = 0; i < 90; i++) {
        w.tick();
        run(1);
        visited.push({ x: p._loc.x, z: p._loc.z });
      }
      const h0 = log.hazards.length;
      const hits0 = count("player_hit", (e) => e.label === "footstep_echo");
      // the target stops and stands on its newest footprint
      forceAttack(enc, attack(enc, 1), [walker(p, () => null)]);
      const ev = events("orison_echo").slice(-1)[0];
      check(ev && ev.points.length >= 3, `echo marked ${ev ? ev.points.length : 0} footprints after a long walk`);
      for (const pt of ev.points) check(visited.some((v) => near(v, pt, 0.02)), `echo at (${pt.x.toFixed(2)}, ${pt.z.toFixed(2)}) is not a recorded position`);
      for (let i = 0; i < ev.points.length; i++) {
        for (let j = i + 1; j < ev.points.length; j++) check(!near(ev.points[i], ev.points[j], 1.99), "two echoes overlap almost completely");
      }
      const hz = log.hazards.slice(h0).filter((h) => h.label === "footstep_echo").sort((a, b) => a.at - b.at);
      check(hz.length === ev.points.length, `${hz.length} strikes for ${ev.points.length} footprints`);
      // newest-first in the trace, oldest-first in time
      hz.forEach((h, k) => check(near({ x: h.shape.cx, z: h.shape.cz }, ev.points[ev.points.length - 1 - k], 1e-6), "strike order does not walk the trail towards the target"));
      check(hz.every((h) => h.at - h.seen >= 20), "an echo detonated with less than a second of warning");
      check(count("player_hit", (e) => e.label === "footstep_echo") > hits0, "standing on your own newest footprint was not punished");
    }
    return "both phases";
  });

  await test("orison: Tomorrow's Witness locks its prediction; it punishes a straight line and can be misled", async () => {
    const scenario = async (phase, after) => {
      const ctx = await begin("orison");
      const { enc, players } = ctx;
      const p = players[0];
      toPhase(ctx, phase, []);
      enc.nextAttackAt = HOLD;
      p._loc.x = enc.arena.cx - 7;
      p._loc.z = enc.arena.cz - 7;
      let dir = { x: 1, z: 0 };
      const w = walker(p, () => dir);
      for (let i = 0; i < 36; i++) {
        w.tick();
        run(1);
      }
      const p0 = count("orison_predict");
      const hits0 = count("player_hit", (e) => e.label === "tomorrows_witness");
      const h0 = log.hazards.length;
      let since = -1;
      const reactive = walker(p, () => {
        if (since < 0 && count("orison_predict") > p0) since = 0;
        else if (since >= 0) since++;
        if (since >= 6) dir = after;
        return dir;
      });
      forceAttack(enc, attack(enc, 5), [reactive]);
      const ev = events("orison_predict").slice(-1)[0];
      check(count("orison_predict") === p0 + 1, "prediction was computed more than once");
      const hz = log.hazards.slice(h0).filter((h) => h.label === "tomorrows_witness");
      check(hz.length === ev.spots.length && hz.every((h, k) => near({ x: h.shape.cx, z: h.shape.cz }, ev.spots[k], 1e-6)), "strike is not at the locked prediction");
      check(JSON.stringify(enc.controller.lastPrediction) === JSON.stringify(ev.spots), "stored prediction differs from the traced one");
      check(Math.abs(ev.vx - WALK) < 0.02 && Math.abs(ev.vz) < 0.02, `velocity estimate (${ev.vx.toFixed(3)}, ${ev.vz.toFixed(3)}) for a player walking +x at ${WALK.toFixed(3)}`);
      check(near(ev.spots[0], { x: ev.from.x + WALK * ev.strikeIn, z: ev.from.z }, 0.6), "prediction is not the straight-line extrapolation");
      return { hits: count("player_hit", (e) => e.label === "tomorrows_witness") - hits0, spots: ev.spots.length };
    };
    const east = { x: 1, z: 0 };
    const west = { x: -1, z: 0 };
    const north = { x: 0, z: -1 };
    let r = await scenario(1, east);
    check(r.spots === 1 && r.hits === 1, `P1: walking straight on took ${r.hits} hits`);
    r = await scenario(1, west);
    check(r.hits === 0, "P1: doubling back after the lock was still hit - the prediction followed the player");
    r = await scenario(2, east);
    check(r.spots === 2 && r.hits === 1, `P2: walking straight on took ${r.hits} hits`);
    r = await scenario(2, west);
    check(r.hits === 1, "P2: the obvious double-back was not anticipated");
    r = await scenario(2, north);
    check(r.hits === 0, "P2: a sidestep after the lock was still hit");
    return "P1 one locked spot; P2 adds the double-back spot, a sidestep beats both";
  });

  await test("orison: The Hour That Never Occurred executes exactly the three previewed patterns", async () => {
    const seen = new Set();
    for (const phase of [1, 2]) {
      for (let rep = 0; rep < 3; rep++) {
        const ctx = await begin("orison");
        const { enc, players } = ctx;
        const bot = new Bot(players[0], enc, { mode: "dodge", speed: WALK, reaction: 6 });
        toPhase(ctx, phase, [bot]);
        place(players[0], enc, 6 + rep * 3, rep * 70);
        const h0 = log.hazards.length;
        const x0 = count("orison_execute");
        const hits0 = count("player_hit");
        forceAttack(enc, attack(enc, 7), [bot]);
        const pv = events("orison_preview").slice(-1)[0];
        const ex = events("orison_execute").slice(x0);
        check(pv.patterns.length === 3, "preview does not have three patterns");
        check(ex.length === 3 && ex.every((e, k) => e.index === k && e.pattern === pv.patterns[k]), `executed [${ex.map((e) => e.pattern)}] after previewing [${pv.patterns}]`);
        check(ex[1].at - ex[0].at >= 30 && ex[2].at - ex[1].at >= 30, "executions are closer together than the specified gap");
        const last = enc.controller.lastHour;
        check(JSON.stringify(last.previewed) === JSON.stringify(last.executed), "controller record: executed differs from previewed");
        check(new Set(pv.patterns).size === 3, "a pattern repeats exactly within one hour");
        if (phase === 2) check(pv.patterns[0].startsWith("checker") && pv.patterns[2].startsWith("checker"), "Phase II sequence is not the harder checker sequence");
        pv.patterns.forEach((s) => seen.add(s));
        // every pattern leaves real room: between a third and two thirds of the floor is dangerous
        const hz = log.hazards.slice(h0).filter((h) => /^hour_[123]$/.test(h.label));
        check(hz.length === 3, `${hz.length} hour strikes registered`);
        for (const h of hz) {
          let danger = 0;
          let total = 0;
          for (let x = -17; x <= 17; x += 0.5) {
            for (let z = -17; z <= 17; z += 0.5) {
              if (!enc.arena.contains(enc.arena.cx + x, enc.arena.cz + z, 0.5)) continue;
              total++;
              if (h.shape.contains(enc.arena.cx + x, enc.arena.cz + z)) danger++;
            }
          }
          const f = danger / total;
          check(f > 0.33 && f < 0.67, `${h.label} covers ${(f * 100).toFixed(0)}% of the arena`);
        }
        check(count("player_hit") === hits0, "a walking player who watched the preview was hit");
      }
    }
    return `${seen.size} distinct patterns seen`;
  });

  await test("orison: hourglasses are capped, breakable, expire, and never slow anyone indefinitely", async () => {
    for (const phase of [1, 2]) {
      const ctx = await begin("orison");
      const { enc, players } = ctx;
      const p = players[0];
      toPhase(ctx, phase, []);
      enc.nextAttackAt = HOLD;
      place(p, enc, 7, 0);
      const drain = attack(enc, 4);
      forceAttack(enc, drain, [walker(p, () => null)]);
      enc.nextAttackAt = HOLD;
      const want = phase === 1 ? 2 : 3;
      check(enc.helpers.count("drain") === want, `${enc.helpers.count("drain")} hourglasses in phase ${phase}`);
      check(drain.weight(enc) === 0, "Hourglass Drain can be chosen again while hourglasses stand");
      const glasses = enc.helpers.of("drain");
      check(glasses.every((h) => Math.hypot(h.data.x - p._loc.x, h.data.z - p._loc.z) >= 2), "an hourglass was placed on top of a player");
      // standing beside one: slowed in short doses, and pulsed
      const strikes0 = count("strike", (e) => e.label === "hourglass_drain");
      let slowMax = 0;
      run(120, [walker(p, () => null)], () => {
        slowMax = Math.max(slowMax, p.getEffect("slowness")?.duration ?? 0);
        return false;
      });
      check(count("orison_slow") > 0 && slowMax > 0, "standing in an hourglass's reach did not slow the player");
      check(slowMax <= 30, `slowness applied for ${slowMax} ticks at once`);
      check(count("strike", (e) => e.label === "hourglass_drain") > strikes0, "hourglasses never pulsed");
      // the pulses and the arena-wide attacks keep out of each other's way
      const verdict = attack(enc, 2);
      run(200, [walker(p, () => null)], () => log.hazards.some((h) => h.label === "hourglass_drain" && h.at > enc.timeline.now));
      check(verdict.weight(enc) === 0, "Pendulum Verdict may start on top of an announced hourglass pulse");
      // walk out of reach: the slow wears off by itself
      const far = enc.arena.clampInside(p._loc.x + (p._loc.x < enc.arena.cx ? 12 : -12), p._loc.z, 1);
      const clear = glasses.every((h) => Math.hypot(h.data.x - far.x, h.data.z - far.z) > 4.2);
      p._loc.x = far.x;
      p._loc.z = clear ? far.z : far.z + 9;
      const slow0 = count("orison_slow");
      run(34, [walker(p, () => null)]);
      check(p.getEffect("slowness") === undefined, "slowness outlasted leaving the area");
      check(count("orison_slow") === slow0 || !clear, "slowed outside every hourglass's reach");
      // breaking one jams Orison and stops that hourglass's pulses
      const st0 = count("stagger");
      const victim = enc.helpers.of("drain")[0];
      const tag = `hg${victim.id}`;
      victim.entity.applyDamage(100, { cause: "entityAttack", damagingEntity: p });
      run(3);
      check(enc.helpers.count("drain") === want - 1, "a broken hourglass is still counted");
      check(count("stagger") === st0 + 1, "breaking an hourglass did not stagger Orison");
      const now = enc.timeline.now;
      run(160, [walker(p, () => null)]);
      check(!log.hazards.some((h) => h.tag === tag && h.seen > sim.tick - 158), "a broken hourglass announced another pulse");
      check(now > 0, "");
      // the rest expire on their own
      run(400, [walker(p, () => null)], () => enc.helpers.count("drain") === 0);
      check(enc.helpers.count("drain") === 0, "hourglasses outlived their lifetime");
      const slow1 = count("orison_slow");
      run(60, [walker(p, () => null)]);
      check(count("orison_slow") === slow1, "slowness continued after every hourglass was gone");
      check(drain.weight(enc) > 0, "Hourglass Drain never becomes available again");
    }
    return "2 in phase I, 3 in phase II";
  });

  await test("orison: Secondhand Exchange marks both ends first, lands where it marked, and refuses a blocked destination", async () => {
    for (const phase of [1, 2]) {
      const ctx = await begin("orison");
      const { enc, players } = ctx;
      const p = players[0];
      toPhase(ctx, phase, []);
      enc.nextAttackAt = HOLD;
      place(p, enc, 12, 20);
      const h0 = log.hazards.length;
      const e0 = count("orison_exchange");
      let landed = 0;
      let seenSwaps = count("orison_swap");
      const watch = {
        tick() {
          p._health.currentValue = 20;
          if (count("orison_swap") > seenSwaps) {
            seenSwaps = count("orison_swap");
            const ev = events("orison_exchange").slice(-1)[0];
            if (near(enc.boss._loc, ev.to, 0.3)) landed++;
          }
        },
      };
      forceAttack(enc, attack(enc, 6), [watch]);
      const evs = events("orison_exchange").slice(e0);
      const swaps = phase === 1 ? 1 : 2;
      check(evs.length === swaps, `${evs.length} exchanges in phase ${phase}`);
      check(landed === swaps, `Orison arrived at the marked point ${landed}/${swaps} times`);
      const hz = log.hazards.slice(h0);
      for (const ev of evs) {
        check(ev.valid, "no valid destination on an open arena floor");
        check(Math.hypot(ev.to.x - ev.from.x, ev.to.z - ev.from.z) >= 6, "exchange destination is too close to be an exchange");
        check(enc.arena.contains(ev.to.x, ev.to.z, 3.5), "destination is outside the leash");
        const arrive = hz.find((h) => h.label === "exchange_arrive" && near({ x: h.shape.cx, z: h.shape.cz }, ev.to, 1e-6));
        const depart = hz.find((h) => h.label === "exchange_depart" && near({ x: h.shape.cx, z: h.shape.cz }, ev.from, 1e-6));
        check(arrive && depart, "arrival or departure hazard is not at the marked point");
        check(arrive.at - arrive.seen >= 40 && depart.at === arrive.at, "arrival was not announced well before the swap");
      }
      check(events("orison_swap").slice(-swaps).every((e) => e.ok), "a swap failed on open ground");
      check(enc.helpers.count("mark") <= 1, "exchange markers accumulated");
    }
    // nowhere to stand: it must not teleport at all
    const ctx = await begin("orison");
    const { enc, players } = ctx;
    toPhase(ctx, 1, []);
    enc.nextAttackAt = HOLD;
    place(players[0], enc, 12, 0);
    const at = { x: enc.boss._loc.x, z: enc.boss._loc.z };
    sim.blockAt = (x, y) => (y >= 64 && y <= 67 ? "solid" : null);
    const s0 = count("orison_swap");
    forceAttack(enc, attack(enc, 6), [walker(players[0], () => null)]);
    sim.blockAt = null;
    const ev = events("orison_exchange").slice(-1)[0];
    check(ev.valid === false, "a destination inside solid blocks was accepted");
    check(count("orison_swap") === s0 && near(enc.boss._loc, at, 1.5), "Orison relocated without a valid destination");
    check(sim.stats.blockWrites === 0, "blocks were modified");
    return "valid destinations only";
  });

  await test("orison: Phase II breaks the glass and frees one shadow that moves before the body", async () => {
    const ctx = await begin("orison");
    const { enc, players } = ctx;
    const p = players[0];
    toPhase(ctx, 1, []);
    check(enc.boss.getProperty("abm:glass") === 0 && enc.helpers.count("shadow") === 0, "glass broken or shadow present in phase I");
    enc.force("phase2");
    run(2000, [walker(p, () => null)], () => enc.sm.top === "PHASE_2");
    check(enc.sm.top === "PHASE_2", "never reached phase II");
    check(enc.boss.getProperty("abm:glass") === 1, "hourglass did not shatter");
    check(enc.controller.extra().glass === 1, "glass state is not part of the persisted state");
    check(enc.helpers.count("shadow") === 1, `${enc.helpers.count("shadow")} shadows after the transition`);
    // far target, no attacks: the shadow sets out first and the body follows its path
    enc.nextAttackAt = HOLD;
    run(30, [walker(p, () => null)]);
    place(p, enc, 15, 150);
    const sh = enc.helpers.of("shadow")[0];
    const s0 = { x: sh.entity._loc.x, z: sh.entity._loc.z };
    const b0 = { x: enc.boss._loc.x, z: enc.boss._loc.z };
    let shadowMoved = -1;
    let bodyMoved = -1;
    const trail = [];
    let bodyOnTrail = false;
    for (let i = 0; i < 120; i++) {
      p._health.currentValue = 20;
      run(1);
      trail.push({ x: sh.entity._loc.x, z: sh.entity._loc.z });
      if (shadowMoved < 0 && !near(sh.entity._loc, s0, 0.6)) shadowMoved = i;
      if (bodyMoved < 0 && !near(enc.boss._loc, b0, 0.6)) bodyMoved = i;
      if (bodyMoved >= 0 && i > bodyMoved + 20 && trail.slice(0, -5).some((t) => near(t, enc.boss._loc, 0.9))) bodyOnTrail = true;
      check(enc.helpers.count("shadow") === 1, "shadow count changed while walking");
    }
    check(shadowMoved >= 0 && bodyMoved >= 0, `shadow moved at ${shadowMoved}, body at ${bodyMoved}`);
    check(bodyMoved - shadowMoved >= 6, `the body (tick ${bodyMoved}) did not wait for the echo (tick ${shadowMoved})`);
    check(bodyOnTrail, "the body did not follow the path its shadow took");
    check(Math.hypot(sh.entity._loc.x - p._loc.x, sh.entity._loc.z - p._loc.z) < Math.hypot(b0.x - p._loc.x, b0.z - p._loc.z), "the shadow did not approach the target");
    // a lost shadow is replaced, never duplicated
    sh.entity.remove();
    run(5);
    check(enc.helpers.count("shadow") === 1, "shadow was not restored after being lost");
    // death: nothing of Orison's is left behind
    enc.force("death");
    run(3);
    check(enc.helpers.count() === 0, "helpers survived the start of the death sequence (the shadow must go first)");
    run(600, [], () => enc.ended);
    const left = [...sim.entities.values()].filter((e) => e.typeId === "abm:orison_shadow" || e.typeId === "abm:orison_hourglass");
    check(left.length === 0, `${left.length} helper entities left in the world`);
    return `echo leads by ${bodyMoved - shadowMoved} ticks`;
  });
}
