// Headless rule tests: node --test tests/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { BALANCE } from '../src/data/balance.js';
import { RACERS } from '../src/data/racers.js';
import { Track } from '../src/sim/track.js';
import { RIFT_JUNCTION } from '../src/sim/trackData.js';
import { Race, FixedLoop } from '../src/sim/race.js';
import { tryUseSkill, SKILLS } from '../src/sim/skills.js';

const track = new Track(RIFT_JUNCTION);
const DT = BALANCE.race.fixedDt;

function newRace(playerId = 'boonsong', opts = {}) {
  return new Race(track, { playerId, seed: 42, ...opts });
}
function toGo(race) {
  while (race.phase === 'countdown') race.step(DT);
}
/** Park every racer except `keep` far from the action so they do not interfere. */
function isolate(race, keep = []) {
  for (const r of race.racers) {
    if (keep.includes(r)) continue;
    r.respawning = true; // frozen: skipped by collisions, pushes and AI
    r.respawnTimer = 1e9;
    r.x = 9000 + r.idx * 50;
    r.z = 9000;
  }
}
/** Kinematically walk a racer through a list of world points (gates/constraints still apply). */
function walk(race, r, pts, step = 1.2) {
  for (let k = 1; k < pts.length; k++) {
    const [ax, az] = pts[k - 1];
    const [bx, bz] = pts[k];
    const n = Math.max(1, Math.ceil(Math.hypot(bx - ax, bz - az) / step));
    for (let i = 1; i <= n; i++) {
      r.px = r.x;
      r.pz = r.z;
      r.py = r.y;
      r.x = ax + ((bx - ax) * i) / n;
      r.z = az + ((bz - az) * i) / n;
      r.heading = Math.atan2(bx - ax, bz - az);
      race.time += DT;
      race._constrain(r, DT);
      race._gates(r);
    }
  }
}
function mainPath(s0, s1, lat = 0, step = 4) {
  const pts = [];
  const p = {};
  for (let s = s0; s <= s1; s += step) {
    track.pointAt(s, lat, p);
    pts.push([p.x, p.z]);
  }
  track.pointAt(s1, lat, p);
  pts.push([p.x, p.z]);
  return pts;
}

test('six racers: player picks one, AI drives the other five, all six distinct', () => {
  for (const def of RACERS) {
    const race = newRace(def.id);
    assert.equal(race.racers.length, 6);
    assert.equal(new Set(race.racers.map((r) => r.def.id)).size, 6);
    assert.equal(race.racers.filter((r) => r.isPlayer).length, 1);
    assert.equal(race.player.def.id, def.id);
  }
});

test('every racer has exactly one distinct skill', () => {
  const skills = RACERS.map((r) => r.skill);
  assert.equal(new Set(skills).size, 6);
  for (const s of skills) assert.ok(SKILLS[s], s);
});

test('skills cannot be used before GO, and are ready the moment the race starts', () => {
  const race = newRace('baby');
  const p = race.player;
  assert.equal(race.phase, 'countdown');
  assert.notEqual(tryUseSkill(race, p), null);
  assert.equal(p.sk.cd, 0);
  p.input.skill = true;
  race.step(DT); // queued presses during the countdown are discarded
  assert.equal(p.sk.uses, 0);
  toGo(race);
  assert.equal(tryUseSkill(race, p), null);
  assert.equal(p.sk.cd, BALANCE.skills.tantrum.cooldown);
});

test('a failed precondition does not burn the cooldown', () => {
  const race = newRace('granny');
  toGo(race);
  const p = race.player;
  p.grounded = false;
  p.airborne = true;
  const why = tryUseSkill(race, p);
  assert.ok(why);
  assert.equal(p.sk.cd, 0);
  assert.ok(race.events.some((e) => e.type === 'skillDenied'));
});

test('cooldown and active time are frame-rate independent', () => {
  const results = [];
  for (const fps of [20, 30, 60, 144]) {
    const race = newRace('celestine');
    toGo(race);
    const loop = new FixedLoop(race);
    tryUseSkill(race, race.player);
    let wall = 0;
    let activeEnded = null;
    let cdEnded = null;
    while (wall < 25) {
      loop.advance(1 / fps);
      wall += 1 / fps;
      if (activeEnded === null && race.player.sk.phase === 'idle') activeEnded = race.time;
      if (cdEnded === null && race.player.sk.cd <= 0) cdEnded = race.time;
    }
    results.push({ fps, activeEnded, cdEnded });
  }
  for (const r of results) {
    assert.ok(Math.abs(r.activeEnded - BALANCE.skills.pirouette.duration) < 0.05, JSON.stringify(r));
    assert.ok(Math.abs(r.cdEnded - BALANCE.skills.pirouette.cooldown) < 0.05, JSON.stringify(r));
  }
});

test('one lap on the main road counts; laps finish the race with a real time', () => {
  const race = newRace('boonsong', { laps: 1 });
  toGo(race);
  const p = race.player;
  isolate(race, [p]);
  const L = track.length;
  walk(race, p, mainPath(L - 10, L + 3));
  assert.equal(p.lap, 1);
  walk(race, p, mainPath(3, L - 2));
  assert.equal(p.finished, false);
  walk(race, p, mainPath(L - 2, L + 4));
  assert.equal(p.finished, true);
  assert.equal(p.place, 1);
  assert.ok(p.finishTime > 0);
});

test('the shortcut still counts the lap (no mid-shortcut waypoint required)', () => {
  const race = newRace('boonsong', { laps: 1 });
  toGo(race);
  const p = race.player;
  isolate(race, [p]);
  const br = track.branch;
  race.time = 0.1; // span is solid
  race.bridge = track.bridgeState(race.time, {});
  const L = track.length;
  walk(race, p, mainPath(L - 10, L + 3));
  walk(race, p, mainPath(3, br.sA + 2));
  // straight down the shortcut span
  const b = [];
  for (let s = 4; s <= br.length - 2; s += 4) b.push([br.ax + br.tx * s, br.az + br.tz * s]);
  // keep the span solid while crossing
  const solid = track.bridgeState;
  track.bridgeState = (t, o = {}) => Object.assign(o, { solid: true, warn: false, phase: 0, timeToChange: 9 });
  race.bridge = track.bridgeState(0);
  walk(race, p, b);
  track.bridgeState = solid;
  assert.equal(p.respawning, false);
  walk(race, p, mainPath(br.sB + 2, L - 2));
  walk(race, p, mainPath(L - 2, L + 4));
  assert.equal(p.finished, true, `nextGate=${p.nextGate} lap=${p.lap}`);
});

test('reversing over the line or cutting across the infield never adds a lap', () => {
  const race = newRace('baby', { laps: 3 });
  toGo(race);
  const p = race.player;
  isolate(race, [p]);
  const L = track.length;
  walk(race, p, mainPath(L - 10, L + 3));
  assert.equal(p.lap, 1);
  // back over the line, forward again, several times
  for (let k = 0; k < 4; k++) {
    walk(race, p, [mainPath(L + 3, L + 3)[0], mainPath(L - 8, L - 8)[0]]);
    walk(race, p, [mainPath(L - 8, L - 8)[0], mainPath(L + 3, L + 3)[0]]);
  }
  assert.equal(p.lap, 1);
  // teleport-style cut: jump to just before the line from the far side of the course
  const far = mainPath(L * 0.5, L * 0.5)[0];
  p.x = far[0];
  p.z = far[1];
  walk(race, p, [far, mainPath(L - 5, L - 5)[0], mainPath(L + 5, L + 5)[0]]);
  assert.equal(p.lap, 1);
});

test('falling returns you behind your last safe spot, never forward, cooldown untouched', () => {
  const race = newRace('boonsong');
  toGo(race);
  const p = race.player;
  isolate(race, [p]);
  const L = track.length;
  walk(race, p, mainPath(L - 10, L + 3));
  walk(race, p, mainPath(3, 600));
  const progressBefore = p.progress;
  const safeS = track.samples[p.lastSafeI].s;
  tryUseSkill(race, p);
  for (let i = 0; i < 30; i++) race.step(DT);
  const cd = p.sk.cd;
  race.startRespawn(p, 'fall');
  for (let i = 0; i < 200 && (p.respawning || p.grace > 1.3); i++) race.step(DT);
  assert.equal(p.respawning, false);
  assert.ok(p.pm.s <= safeS + 0.5, `respawned at ${p.pm.s} after safe ${safeS}`);
  assert.ok(p.progress <= progressBefore + 1, 'no free progress');
  assert.ok(p.sk.cd < cd && p.sk.cd > 0, 'cooldown kept running, not reset');
  assert.equal(p.onRail, false);
});

test('tantrum hits each rival at most once per use and only inside its radius', () => {
  const race = newRace('baby');
  toGo(race);
  const p = race.player;
  const [near, far, high] = race.racers.filter((r) => !r.isPlayer);
  isolate(race, [p, near, far, high]);
  for (const r of race.racers) r.ai && (r.ai = r.ai); // keep AI
  const R = BALANCE.skills.tantrum.radiusLengths * BALANCE.vehicle.standardLength;
  const put = (r, dx, dy = 0) => {
    r.x = p.x + dx;
    r.z = p.z;
    r.y = p.y + dy;
  };
  put(near, 4);
  put(far, R + 6);
  put(high, 3, 6); // stacked on another level
  let pushes = 0;
  tryUseSkill(race, p);
  for (let i = 0; i < 60; i++) {
    for (const r of [p, near, far, high]) {
      r.input.throttle = 0;
      r.vx = r.vz = 0;
    }
    race.events.length = 0;
    // keep the near rival inside the radius the whole time
    put(near, 4);
    race._skillOnly = true;
    for (const r of [p]) {
      const sk = SKILLS[r.def.skill];
      sk.update(race, r, DT);
    }
    pushes += race.events.filter((e) => e.type === 'pushed' && e.racer === near).length;
    assert.ok(!race.events.some((e) => e.type === 'pushed' && (e.racer === far || e.racer === high)));
    race.time += DT;
  }
  assert.equal(pushes, 1);
});

test('hurricane re-hits the same rival no more often than the per-target interval', () => {
  const race = newRace('gator');
  toGo(race);
  const p = race.player;
  const [o] = race.racers.filter((r) => !r.isPlayer);
  isolate(race, [p, o]);
  tryUseSkill(race, p);
  const hits = [];
  for (let i = 0; i < 240; i++) {
    race.events.length = 0;
    o.x = p.x + 3;
    o.z = p.z;
    o.y = p.y;
    SKILLS.hurricane.update(race, p, DT);
    o.pushLock = Math.max(0, o.pushLock - DT);
    if (race.events.some((e) => e.type === 'pushed' && e.racer === o)) hits.push(race.time);
    race.time += DT;
  }
  assert.ok(hits.length >= 3 && hits.length <= 5, `hits ${hits.length}`);
  for (let i = 1; i < hits.length; i++) assert.ok(hits[i] - hits[i - 1] >= BALANCE.skills.hurricane.perTargetInterval - 1e-6);
});

test('push velocity is capped and globally rate-limited', () => {
  const race = newRace('baby');
  toGo(race);
  const t = race.racers[1];
  for (let i = 0; i < 50; i++) {
    t.pushLock = 0;
    race.applyPush(t, 1, 0, 50, null);
  }
  assert.ok(Math.hypot(t.knockX, t.knockZ) <= BALANCE.push.maxKnock + 1e-6);
  t.pushLock = 0;
  assert.equal(race.applyPush(t, 1, 0, 5, null), true);
  assert.equal(race.applyPush(t, 1, 0, 5, null), false);
});

test('slick patches: ground racers (incl. the hovering potty) slip; jumpers, rails and owners do not', () => {
  const race = newRace('lovers');
  toGo(race);
  const owner = race.player;
  const gator = race.racers.find((r) => r.def.id === 'gator');
  const granny = race.racers.find((r) => r.def.id === 'granny');
  const rail = race.racers.find((r) => r.def.id === 'boonsong');
  race.addSlick(owner.x, owner.y, owner.z, owner.idx);
  for (const r of [gator, granny, rail]) {
    r.x = owner.x;
    r.z = owner.z;
    r.y = r.gy = owner.y;
    r.airborne = false;
    r.onRail = false;
  }
  granny.airborne = true;
  granny.y += 3;
  rail.onRail = true;
  rail.y += BALANCE.skills.railMaker.height;
  for (const r of [owner, gator, granny, rail]) race._slickCheck(r);
  assert.equal(gator.slickTarget, 1);
  assert.equal(granny.slickTarget, 0);
  assert.equal(rail.slickTarget, 0);
  assert.equal(owner.slickTarget, 0);
});

test('slick patches expire, are capped, and never pile up across races', () => {
  const race = newRace('lovers');
  toGo(race);
  for (let i = 0; i < 200; i++) race.addSlick(i, 0, 0, 99);
  assert.equal(race.slicks.length, BALANCE.skills.eternalLove.maxPatches);
  for (let i = 0; i < Math.ceil(BALANCE.skills.eternalLove.patchLife / DT) + 2; i++) race.step(DT);
  assert.equal(race.slicks.length, 0);
});

test('rail maker: lays rail while active, then the rail dissolves completely', () => {
  const race = newRace('boonsong');
  toGo(race);
  const p = race.player;
  isolate(race, [p]);
  for (let i = 0; i < 120; i++) {
    p.input.throttle = 1;
    race.step(DT);
  }
  assert.equal(tryUseSkill(race, p), null);
  assert.equal(p.onRail, true);
  for (let i = 0; i < 60; i++) race.step(DT);
  assert.ok(p.railPts.length > 5);
  for (let i = 0; i < (BALANCE.skills.railMaker.duration + 1) / DT; i++) race.step(DT);
  assert.equal(p.onRail, false);
  assert.equal(p.railPts.length, 0);
});

test('slingshot leaves the ground for about the configured air time, then lands', () => {
  const race = newRace('granny');
  toGo(race);
  const p = race.player;
  isolate(race, [p]);
  for (let i = 0; i < 90; i++) race.step(DT);
  tryUseSkill(race, p);
  let t0 = null;
  let t1 = null;
  for (let i = 0; i < 300; i++) {
    race.step(DT);
    if (t0 === null && p.jumping) t0 = race.time;
    if (t0 !== null && t1 === null && !p.jumping) t1 = race.time;
  }
  assert.ok(t0 !== null && t1 !== null);
  assert.ok(Math.abs(t1 - t0 - BALANCE.skills.slingshot.airTime) < 0.25, `air ${t1 - t0}`);
  assert.equal(p.grounded, true);
});

test('drift boost needs a sustained drift, lasts ~0.5 s and does not stack', () => {
  const race = newRace('celestine');
  toGo(race);
  const p = race.player;
  isolate(race, [p]);
  for (let i = 0; i < 200; i++) {
    p.input.throttle = 1;
    race.step(DT);
  }
  // tapping drift rapidly never earns a boost
  for (let i = 0; i < 60; i++) {
    p.input.throttle = 1;
    p.input.steer = 1;
    p.input.drift = i % 6 < 3;
    race.step(DT);
    assert.equal(p.boostTimer > 0, false, 'boost from drift spam');
  }
  p.input.drift = false;
  // back to the middle of the long opening straight at speed
  const q = track.pointAt(40, -3, {});
  Object.assign(p, { x: q.x, z: q.z, px: q.x, pz: q.z, heading: q.heading, mainHint: track.sampleAt(40).i, knockX: 0, knockZ: 0, drift: 0, boostTimer: 0 });
  p.vx = Math.sin(q.heading) * 30;
  p.vz = Math.cos(q.heading) * 30;
  // initiate right, then counter-steer to hold the slide without hitting the wall
  let i = 0;
  for (; i < 120 && !p.driftCharged; i++) {
    p.input.throttle = 1;
    p.input.steer = i < 18 ? 1 : -0.6;
    p.input.drift = true;
    race.step(DT);
    assert.notEqual(p.drift, 0, `drift dropped at step ${i} speed ${p.vf.toFixed(1)} lat ${p.pm.d.toFixed(1)}`);
  }
  assert.ok(p.driftCharged, 'charged');
  assert.ok(i * DT >= BALANCE.drift.chargeTime, 'charge needs the configured time');
  assert.ok(p.vf > BALANCE.vehicle.maxSpeed * 0.7, `drift kept speed: ${p.vf}`);
  p.input.drift = false;
  p.input.steer = 0;
  race.step(DT);
  assert.ok(p.boostTimer > 0 && p.boostTimer <= BALANCE.drift.boostTime + 1e-6);
});

test('full AI race: everyone finishes, places are unique and locked in finish order', () => {
  const uses = {};
  for (const seed of [3, 11]) {
    const race = new Race(track, { playerId: null, seed });
    const placesAtFinish = new Map();
    let guard = 0;
    while (!race.done && guard++ < 60 * 300) {
      race.step(DT);
      for (const e of race.events) if (e.type === 'finish') placesAtFinish.set(e.racer.idx, e.place);
      race.events.length = 0;
    }
    assert.ok(race.done, 'race finished');
    assert.ok(race.racers.every((r) => r.finished));
    const res = race.results();
    assert.deepEqual(res.map((r) => r.place), [1, 2, 3, 4, 5, 6]);
    for (let i = 1; i < res.length; i++) assert.ok(res[i].time >= res[i - 1].time);
    for (const r of race.racers) assert.equal(r.place, placesAtFinish.get(r.idx));
    // 2–3 minute race target with 3 laps
    assert.ok(race.time > 110 && race.time < 200, `race time ${race.time}`);
    for (const r of race.racers) uses[r.def.id] = (uses[r.def.id] || 0) + r.sk.uses;
  }
  // AI only uses skills when the situation suits them (e.g. a trap is pointless in last place),
  // but across races every racer's AI must use its skill
  assert.ok(Object.values(uses).every((n) => n > 0), JSON.stringify(uses));
});

function crossGapAttempt(id, useSkill) {
  const race = newRace(id);
  toGo(race);
  const p = race.player;
  isolate(race, [p]);
  const br = track.branch;
  // start on the shortcut, aimed down it, at speed, with the span closed for the whole attempt
  track.bridgeState = ((orig) => {
    const f = (t, o = {}) => Object.assign(o, { solid: false, warn: false, phase: 10, timeToChange: 9 });
    f.orig = orig;
    return f;
  })(track.bridgeState);
  const start = useSkill === 'rail' ? br.gap0 - 30 : br.gap0 - 30;
  Object.assign(p, { x: br.ax + br.tx * start, z: br.az + br.tz * start, y: br.ay, gy: br.ay, refY: br.ay, heading: br.heading, lap: 1, nextGate: 6 });
  p.px = p.x;
  p.pz = p.z;
  p.vx = br.tx * 30;
  p.vz = br.tz * 30;
  let fell = false;
  let fired = false;
  for (let i = 0; i < 60 * 4; i++) {
    p.input.throttle = 1;
    p.input.steer = 0;
    const sb = (p.x - br.ax) * br.tx + (p.z - br.az) * br.tz;
    const trigger = useSkill === 'rail' ? br.gap0 - 6 : br.gap0 - 13;
    if (useSkill && !fired && sb > trigger) {
      fired = tryUseSkill(race, p) === null;
    }
    race.step(DT);
    if (race.events.some((e) => e.type === 'fall')) fell = true;
    race.events.length = 0;
    if (sb > br.gap1 + 6 && p.grounded) break;
  }
  track.bridgeState = track.bridgeState.orig;
  const sb = (p.x - br.ax) * br.tx + (p.z - br.az) * br.tz;
  return { fell, past: sb > br.gap1, fired };
}

test('closed shortcut span: rail and slingshot cross the gap, a plain racer falls', () => {
  const rail = crossGapAttempt('boonsong', 'rail');
  assert.ok(rail.fired && !rail.fell && rail.past, 'rail ' + JSON.stringify(rail));
  const jump = crossGapAttempt('granny', 'jump');
  assert.ok(jump.fired && !jump.fell && jump.past, 'jump ' + JSON.stringify(jump));
  const plain = crossGapAttempt('celestine', null);
  assert.ok(plain.fell, 'plain ' + JSON.stringify(plain));
});
