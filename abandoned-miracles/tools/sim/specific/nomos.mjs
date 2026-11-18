/**
 * Nomos-specific scenarios: the logical survey grid, safe routes through every
 * Great Recalculation state, Unmapped Gate destinations, dart locks, ink borders.
 */
import fs from "node:fs";

const T = JSON.parse(fs.readFileSync(new URL("../../../shared/nomos.timings.json", import.meta.url), "utf8"));

export default async function suite({ test, check, begin, toPhase, forceAttack, place, run, sim, count, events, log, Bot, WALK }) {
  const attack = (enc, id) => enc.controller.attacks.find((a) => a.id === id);
  const hold = (enc) => {
    enc.nextAttackAt = enc.timeline.now + 100000;
  };
  /** Lattice of points half a block inside the arena, one block apart. */
  const lattice = (g, step = 1) => {
    const out = [];
    for (let x = g.cx - g.half + 0.5; x < g.cx + g.half; x += step) {
      for (let z = g.cz - g.half + 0.5; z < g.cz + g.half; z += step) out.push({ x, z });
    }
    return out;
  };
  /** Independent of the controller's own distance transform: brute force. */
  const worstWalk = (g, danger) => {
    const pts = lattice(g);
    const safe = pts.filter((p) => !danger.contains(p.x, p.z));
    let worst = 0;
    for (const p of pts) {
      if (!danger.contains(p.x, p.z)) continue;
      let best = Infinity;
      for (const s of safe) {
        const d = (s.x - p.x) ** 2 + (s.z - p.z) ** 2;
        if (d < best) best = d;
      }
      worst = Math.max(worst, Math.sqrt(best));
    }
    return { worst, safe: safe.length, total: pts.length };
  };

  await test("nomos: the logical grid is the arena (8x8 cells of 5, four quadrants, ruled lines)", async () => {
    const ctx = await begin("nomos");
    const { enc } = ctx;
    toPhase(ctx, 1, []);
    const g = enc.controller.grid;
    const a = enc.arena;
    check(g.cell === 5 && g.half === 20, `grid cell ${g.cell}, half ${g.half}`);
    check(Math.abs(g.cx - a.centre.x) < 1e-9 && Math.abs(g.cz - a.centre.z) < 1e-9, "grid origin is not the arena centre");
    for (let c = 0; c < 8; c++) {
      for (let r = 0; r < 8; r++) {
        const m = g.cellCentre(c, r);
        check(a.contains(m.x, m.z, 0), `cell ${c},${r} centre is outside the arena`);
        const back = g.cellOf(m.x, m.z);
        check(back.c === c && back.r === r, `cellOf(cellCentre(${c},${r})) = ${back.c},${back.r}`);
        check(Math.abs(((m.x - g.cx) / 2.5) % 2) === 1 && Math.abs(((m.z - g.cz) / 2.5) % 2) === 1, `cell ${c},${r} centre is off the lattice`);
      }
    }
    for (const v of [-19.9, -12.6, -7.4, -2.6, 0, 2.4, 7.6, 12.4, 19.9]) {
      for (const axis of ["x", "z"]) {
        const s = g.snapLine((axis === "x" ? g.cx : g.cz) + v, axis) - (axis === "x" ? g.cx : g.cz);
        check(Math.abs(s / 5 - Math.round(s / 5)) < 1e-9, `snapLine(${v}) = ${s} is not a ruled line`);
        check(Math.abs(s - v) <= 2.5 + 1e-9, `snapLine(${v}) = ${s} is not the nearest ruled line`);
      }
    }
    const q = (dx, dz) => g.quadrantOf(g.cx + dx, g.cz + dz);
    check(q(-1, -1) === 0 && q(1, -1) === 1 && q(-1, 1) === 2 && q(1, 1) === 3, "quadrant numbering");
    for (let i = 0; i < 4; i++) {
      const m = g.quadrantCentre(i);
      check(g.quadrantOf(m.x, m.z) === i && Math.abs(Math.abs(m.x - g.cx) - 10) < 1e-9, `quadrant ${i} centre`);
    }
    // the arena structure's floor pattern uses the same 5-block ruling and +-10 benchmarks (tools/bosses/nomos/arena.py)
    return "64 cells, 4 quadrants";
  });

  await test("nomos: every Great Recalculation state leaves a walkable safe route", async () => {
    let states = 0;
    let worstSeen = 0;
    const systems = new Set();
    for (const phase of [1, 2]) {
      const ctx = await begin("nomos");
      const { enc } = ctx;
      toPhase(ctx, phase, []);
      hold(enc);
      const ctrl = enc.controller;
      const g = ctrl.grid;
      const warn = T.great_recalculation[`p${phase}`].warn;
      // what a walking player can cover after a 0.4 s reaction (the bots in this harness react in 0.3 s)
      const allowed = (warn - 8) * WALK;
      const unsafe0 = count("unsafe_pattern");
      for (let i = 0; i < 40; i++) {
        const configs = ctrl.buildConfigurations(phase, warn);
        check(configs.length === 3, `${configs.length} configurations`);
        for (const cfg of configs) {
          states++;
          systems.add(cfg.system);
          const own = g.maxDistanceToSafety(cfg.danger);
          const { worst, safe, total } = worstWalk(g, cfg.danger);
          worstSeen = Math.max(worstSeen, worst);
          check(safe / total >= 0.25, `P${phase} system ${cfg.system}: only ${safe}/${total} of the floor is safe`);
          check(worst <= allowed, `P${phase} system ${cfg.system}: a player may need to walk ${worst.toFixed(2)} blocks, but only ${allowed.toFixed(2)} are possible`);
          check(own + 1e-9 >= worst - 1.01, `P${phase} system ${cfg.system}: the controller's own measure (${own.toFixed(2)}) underestimates the brute-force one (${worst.toFixed(2)})`);
          // the safe shape handed to the telegraph really is safe
          for (const p of cfg.safe.sample(enc.rng, 24)) {
            check(!cfg.danger.contains(p.x, p.z), `P${phase} system ${cfg.system}: a point marked safe is inside the danger region`);
          }
        }
      }
      check(count("unsafe_pattern") === unsafe0, `P${phase}: ${count("unsafe_pattern") - unsafe0} generated patterns failed validation and were replaced`);
    }
    check(systems.size === 3, "not all three coordinate systems were used");
    return `${states} states, worst walk ${worstSeen.toFixed(2)} blocks`;
  });

  await test("nomos: the Great Recalculation runs three validated strikes and cannot be interrupted", async () => {
    for (const phase of [1, 2]) {
      const ctx = await begin("nomos");
      const { enc, players } = ctx;
      const bot = new Bot(players[0], enc, { mode: "dodge" });
      toPhase(ctx, phase, [bot]);
      const def = attack(enc, "great_recalculation");
      check(def.ultimate === true && def.interruptible === false, "ultimate flags");
      place(players[0], enc, 9, 40);
      const h0 = log.hazards.length;
      const hits = count("player_hit");
      const staggers = count("stagger");
      // try to stagger it out of the ultimate half-way through
      let poked = false;
      const poke = { tick() {
        if (!poked && enc.currentAttack?.id === "great_recalculation" && log.hazards.length - h0 >= 2) {
          poked = true;
          enc.stagger(20);
        }
      } };
      forceAttack(enc, def, [bot, poke]);
      const mine = log.hazards.slice(h0).filter((h) => String(h.label).startsWith("recalculation_"));
      check(mine.length === 3, `${mine.length} recalculation strikes were telegraphed`);
      check(new Set(mine.map((h) => h.label)).size === 3, "strike labels are not distinct");
      const warn = T.great_recalculation[`p${phase}`].warn;
      for (const h of mine) check(h.at - h.seen >= warn - 1, `${h.label} had only ${h.at - h.seen} ticks of warning`);
      check(count("strike", (e) => String(e.label).startsWith("recalculation_")) >= 3, "not every recalculation strike resolved");
      check(count("player_hit") === hits, "a walking player was hit by the ultimate");
      check(count("stagger") === staggers, "the ultimate was interrupted by a stagger");
      const rec = events("recalculation").at(-1);
      check(rec && rec.systems.length === 3, "no recalculation trace");
    }
    return "3 + 3 strikes";
  });

  await test("nomos: Unmapped Gate only lands on validated ground inside the arena", async () => {
    let jumps = 0;
    let refused = 0;
    for (const phase of [1, 2]) {
      for (const [dist, bearing] of [[10, 0], [15, 180], [19, 90], [6, -120], [26, 45]]) {
        const ctx = await begin("nomos");
        const { enc, players } = ctx;
        const bot = new Bot(players[0], enc, { mode: "dodge" });
        toPhase(ctx, phase, [bot]);
        const ctrl = enc.controller;
        place(players[0], enc, dist, bearing);
        const y0 = enc.boss._loc.y;
        const n0 = ctrl.gateLog.length;
        let last = { ...enc.boss._loc };
        let far = 0;
        const watch = { tick() {
          const l = enc.boss._loc;
          far = Math.max(far, Math.hypot(l.x - last.x, l.z - last.z));
          last = { ...l };
        } };
        forceAttack(enc, attack(enc, "unmapped_gate"), [bot, watch]);
        const mine = ctrl.gateLog.slice(n0);
        check(mine.length === phase, `P${phase}: ${mine.length} gate(s) opened`);
        const lim = enc.arena.radius - enc.stats.leashInset - 0.5;
        for (const d of mine) {
          if (!d.ok) {
            // a refusal is only legitimate when Nomos already stands beside the nearest coordinate it may occupy
            // (the log then holds its own position); 3 blocks of slack for the player's movement since the mark
            const pl = players[0]._loc;
            const cx = Math.min(enc.arena.cx + lim, Math.max(enc.arena.cx - lim, pl.x));
            const cz = Math.min(enc.arena.cz + lim, Math.max(enc.arena.cz - lim, pl.z));
            check(Math.hypot(cx - d.x, cz - d.z) < 6 + 3, `no destination found (${dist}@${bearing}) although the target was ${Math.hypot(cx - d.x, cz - d.z).toFixed(1)} blocks away`);
            refused++;
            continue;
          }
          jumps++;
          check(enc.arena.contains(d.x, d.z, enc.stats.leashInset), `destination ${d.x.toFixed(1)},${d.z.toFixed(1)} is not inside the arena`);
          check(enc.loco.canStand({ x: d.x, y: enc.arena.floorY, z: d.z }), "destination is not standable");
        }
        if (mine.some((d) => d.ok)) check(far > 3, `Nomos never relocated (largest step ${far.toFixed(2)})`);
        const l = enc.boss._loc;
        check(enc.arena.contains(l.x, l.z, 0), "Nomos ended outside the arena");
        check(Math.abs(l.y - y0) < 1e-6, "Nomos changed height");
        check(count("gate_blocked") === 0, "a validated destination was refused at relocation time");
      }
    }
    // no valid ground anywhere: the gate must not move it, and the attack must still finish
    const ctx = await begin("nomos");
    const { enc, players } = ctx;
    const bot = new Bot(players[0], enc, { mode: "dodge" });
    toPhase(ctx, 1, [bot]);
    place(players[0], enc, 10, 0);
    const real = enc.loco.canStand.bind(enc.loco);
    enc.loco.canStand = () => false;
    let last = { ...enc.boss._loc };
    let far = 0;
    const watch = { tick() {
      const l = enc.boss._loc;
      far = Math.max(far, Math.hypot(l.x - last.x, l.z - last.z));
      last = { ...l };
    } };
    const n0 = enc.controller.gateLog.length;
    forceAttack(enc, attack(enc, "unmapped_gate"), [bot, watch]);
    enc.loco.canStand = real;
    check(enc.controller.gateLog.slice(n0).every((d) => !d.ok), "a destination was accepted although nowhere is standable");
    check(far < 1, `Nomos moved ${far.toFixed(2)} blocks in one tick without valid ground`);
    check(enc.sm.inCombat && !enc.sm.busy, "the fight did not continue");
    check(jumps >= 10, `only ${jumps} relocations happened`);
    return `${jumps} validated relocations, ${refused} refused beside the target, blocked case holds position`;
  });

  await test("nomos: Compass Darts never re-aim after the lock", async () => {
    let darts = 0;
    for (const phase of [1, 2]) {
      const ctx = await begin("nomos");
      const { enc, players } = ctx;
      const bot = new Bot(players[0], enc, { mode: "dodge" });
      toPhase(ctx, phase, [bot]);
      const ctrl = enc.controller;
      place(players[0], enc, 11, 15);
      const where = new Map();
      const watch = { tick() {
        where.set(enc.timeline.now, { x: players[0]._loc.x, z: players[0]._loc.z });
      } };
      const h0 = log.hazards.length;
      const n0 = ctrl.dartLocks.length;
      const start = { ...players[0]._loc };
      forceAttack(enc, attack(enc, "compass_darts"), [bot, watch]);
      const locks = ctrl.dartLocks.slice(n0);
      const flights = log.hazards.slice(h0).filter((h) => h.label === "compass_dart");
      check(locks.length === (phase === 1 ? 4 : 8), `P${phase}: ${locks.length} locks`);
      check(flights.length === locks.length, `${flights.length} flights for ${locks.length} locks`);
      locks.forEach((k, i) => {
        darts++;
        const f = flights[i];
        check(Math.abs(Math.hypot(k.dx, k.dz) - 1) < 1e-6, "lock bearing is not a unit vector");
        // the bearing pointed at the player when it locked ...
        const p = where.get(k.tick) ?? where.get(k.tick - 1);
        if (p) {
          const d = Math.hypot(p.x - k.ox, p.z - k.oz);
          const cos = ((p.x - k.ox) * k.dx + (p.z - k.oz) * k.dz) / d;
          check(cos > Math.cos((6 * Math.PI) / 180), `dart ${i} locked ${((Math.acos(Math.min(1, cos)) * 180) / Math.PI).toFixed(1)} deg off its target`);
        }
        // ... and every tick of the flight stays on that one line, wherever the player went afterwards
        for (let t = 0; t <= f.duration; t++) {
          const c = f.shapeAt(t);
          const vx = c.cx - k.ox;
          const vz = c.cz - k.oz;
          check(Math.abs(vx * k.dz - vz * k.dx) < 1e-6, `dart ${i} left its locked bearing at flight tick ${t}`);
          check(vx * k.dx + vz * k.dz > 0, `dart ${i} flew backwards`);
          check(enc.arena.contains(c.cx, c.cz, 0), `dart ${i} left the map`);
        }
        check(f.start - f.seen >= T.compass_darts[`p${phase}`].warn, `dart ${i} had ${f.start - f.seen} ticks between lock and flight`);
      });
      const moved = Math.hypot(players[0]._loc.x - start.x, players[0]._loc.z - start.z);
      check(moved > 0.5, "the player never moved, so the test proves nothing");
    }
    return `${darts} darts`;
  });

  await test("nomos: Ink Borders slow but never block, never enclose, and are wiped with the phase", async () => {
    const connected = (g, shape) => {
      const n = 80;
      const free = (i, j) => !shape.contains(g.cx - g.half + 0.25 + i * 0.5, g.cz - g.half + 0.25 + j * 0.5);
      const seen = new Uint8Array(n * n);
      let total = 0;
      let start = -1;
      for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (free(i, j)) {
        total++;
        if (start < 0) start = i * n + j;
      }
      const stack = [start];
      seen[start] = 1;
      let reached = 0;
      while (stack.length) {
        const k = stack.pop();
        reached++;
        const i = Math.floor(k / n);
        const j = k % n;
        for (const [a, b] of [[i + 1, j], [i - 1, j], [i, j + 1], [i, j - 1]]) {
          if (a < 0 || b < 0 || a >= n || b >= n || seen[a * n + b] || !free(a, b)) continue;
          seen[a * n + b] = 1;
          stack.push(a * n + b);
        }
      }
      return reached === total;
    };
    for (const phase of [1, 2]) {
      for (const [dist, bearing] of [[8, 0], [14, 135], [20, -60]]) {
        const ctx = await begin("nomos");
        const { enc, players } = ctx;
        const p = players[0];
        const stand = new Bot(p, enc, { mode: "stand" });
        toPhase(ctx, phase, [stand]);
        const ctrl = enc.controller;
        const def = attack(enc, "ink_borders");
        place(p, enc, dist, bearing);
        const h0 = log.hazards.length;
        const hits0 = count("player_hit");
        forceAttack(enc, def, [stand]);
        hold(enc);
        const stamp = log.hazards.slice(h0).find((h) => h.label === "ink_border");
        check(stamp && stamp.kind === "strike", "the stamp was not telegraphed");
        const ev = events("ink_borders").at(-1);
        check(ev.lanes === (phase === 1 ? 2 : 4), `P${phase}: ${ev.lanes} borders`);
        check(count("player_hit") === hits0 + 1, `a player standing on the first border took ${count("player_hit") - hits0} hits from the stamp`);
        check(connected(ctrl.grid, stamp.shape), `P${phase} ${dist}@${bearing}: the borders enclose part of the arena`);
        check(ctrl.bordersUntil > enc.timeline.now, "borders are not standing after the stamp");
        check(def.weight(enc) === 0, "Ink Borders can be stacked on standing borders");
        // standing on wet ink: slowed, not wounded, not moved
        p._health.currentValue = 20;
        const at = { ...p._loc };
        const touches = count("border_touch");
        run(45, [stand]);
        check(count("border_touch") > touches, "standing on a border was not noticed");
        check(count("player_hit") === hits0 + 1 && p._health.currentValue === 20, "a standing border wounded the player");
        check(Math.hypot(p._loc.x - at.x, p._loc.z - at.z) < 1e-9, "a standing border moved the player");
        const slow = p._effects.get("slowness");
        check(slow && slow.until > sim.tick && slow.amplifier === (phase === 1 ? 0 : 1), "no slowness from wet ink");
        if (phase === 1 && dist === 8) {
          // "THERE IS NO NORTH": the old map is void, borders included
          enc.force("phase2");
          run(4, [stand]);
          check(ctrl.bordersUntil === 0, "borders survived the phase change");
          const t1 = count("border_touch");
          run(60, [stand]);
          check(count("border_touch") === t1, "wiped borders still slow players");
        } else {
          run(ctrl.bordersUntil - enc.timeline.now + 3, [stand]);
          check(ctrl.bordersUntil === 0, "borders did not expire");
          const t1 = count("border_touch");
          run(30, [stand]);
          check(count("border_touch") === t1, "expired borders still slow players");
          check(def.weight(enc) > 0, "Ink Borders is never available again");
        }
        if (log.errors.length) throw new Error(log.errors[0]);
      }
    }
    return "stamp 1 hit, standing ink 0 hits, one connected floor";
  });

  await test("nomos: Phase II hands each quadrant to its own indicator; a reset leaves no arena state", async () => {
    const ctx = await begin("nomos");
    const { enc, players } = ctx;
    const bot = new Bot(players[0], enc, { mode: "dodge" });
    toPhase(ctx, 2, [bot]);
    const ctrl = enc.controller;
    const boss = enc.boss;
    const read = () => [1, 2, 3, 4].map((i) => boss.getProperty(`abm:q${i}`));
    for (const id of ["great_recalculation", "compass_darts", "ink_borders"]) {
      forceAttack(enc, attack(enc, id), [bot]);
      for (const v of read()) check(Number.isInteger(v) && v >= 0 && v <= 7, `indicator value ${v}`);
    }
    check(ctrl.bordersUntil > 0, "expected standing borders before the reset");
    // everyone leaves: the encounter resets
    players[0]._loc.x += 90;
    bot.mode = "stand";
    run(ctx.CONFIG.encounter.resetGraceTicks + 120, [bot]);
    check(enc.ended, "encounter did not reset");
    check(ctrl.bordersUntil === 0, "borders outlived the encounter");
    const touches = count("border_touch");
    const hz = log.hazards.length;
    run(200, []);
    check(count("border_touch") === touches && log.hazards.length === hz, "hazards kept running after the reset");
    check(sim.stats.blockWrites === undefined || sim.stats.blockWrites === 0, "blocks were written");
    if (log.errors.length) throw new Error(log.errors[0]);
    return `indicators ${read().join(",")}`;
  });
}
