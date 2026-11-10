// AI drivers. They produce the same inputs a player does (steer / throttle /
// brake / skill) and are bound by the same physics, cooldowns and recovery rules.
// No rubber banding and no warping: each AI has a fixed pace level for the race.
import { BALANCE } from '../data/balance.js';
import { angleDiff, clamp, damp, lerp } from './math.js';

const A = BALANCE.ai;
const V = BALANCE.vehicle;
const K = BALANCE.skills;
const tp = { x: 0, y: 0, z: 0, heading: 0, hw: 8 };

export function createAI(race, r, n) {
  const levels = A.skillLevels;
  if (!race._aiLevels) {
    // shuffle pace levels so a different rival is the favourite each race
    const l = levels.slice();
    for (let i = l.length - 1; i > 0; i--) {
      const j = Math.floor(race.rng() * (i + 1));
      [l[i], l[j]] = [l[j], l[i]];
    }
    race._aiLevels = l;
  }
  return {
    level: r.isPlayer ? 0.9 : race._aiLevels[n % levels.length],
    laneBias: (race.rng() * 2 - 1) * A.laneWander,
    lane: 0,
    laneInit: false,
    route: 'main',
    routeDecided: false,
    react: lerp(A.reactionMin, A.reactionMax, race.rng()),
    skillT: 0,
    startDelay: race.rng() * 0.25,
    waitForBridge: false,
  };
}

function cornerSpeed(kappa, r, level) {
  const c = A.cornerSafety * level * r.stats.turn;
  const k = Math.max(1e-4, Math.abs(kappa));
  return (c * V.turnLow) / (k + (c * (V.turnLow - V.turnHigh)) / V.maxSpeed);
}

function maxCurvAhead(track, s, from, to) {
  let m = 0;
  for (let d = from; d <= to; d += 6) {
    const c = Math.abs(track.sampleAt(s + d).curv);
    if (c > m) m = c;
  }
  return m;
}

export function updateAI(race, r, dt) {
  const ai = r.ai;
  const inp = r.input;
  const track = race.track;
  const br = track.branch;
  const L = track.length;
  const s = r.pm.s;
  const skillId = r.def.skill;
  const ready = r.sk.cd <= 0 && r.sk.phase === 'idle' && !r.finished;

  if (!ai.laneInit) {
    ai.lane = r.pm.d || (r.gridSlot % 2 === 0 ? -4.2 : 4.2);
    ai.laneInit = true;
  }
  inp.drift = false;
  inp.brake = 0;
  inp.throttle = 1;
  if (race.time < ai.startDelay) {
    inp.throttle = 0;
    inp.steer = 0;
    return;
  }

  // ── route choice at the bridge junction ──
  const speedNow = Math.max(10, r.speed);
  const distToA = (br.sA - s + L) % L;
  const sbNow = r.pb.s; // may be negative before the branch starts
  if (!ai.routeDecided && distToA < 70 && distToA > 3) {
    ai.routeDecided = true;
    const etaGap0 = (distToA + br.gap0) / speedNow;
    const etaGap1 = (distToA + br.gap1) / speedNow;
    const spanOk = track.bridgeSolidDuring(race.time + etaGap0 - 0.5, race.time + etaGap1 + 0.7);
    const canCross = (skillId === 'railMaker' || skillId === 'slingshot') && r.sk.cd < etaGap0 - 0.6 && !r.finished;
    ai.route = canCross || (spanOk && race.rng() < 0.85) ? 'branch' : 'main';
    ai.spanPlanned = spanOk;
  }
  const pastB = (s - br.sB + L) % L;
  if (ai.routeDecided && pastB < 60 && pastB > 6) {
    ai.routeDecided = false;
    ai.route = 'main';
  }
  const onBranchRoute = ai.route === 'branch' && sbNow > -75 && sbNow < br.length + 4 && (distToA < 80 || r.pb.valid);

  // ── lane choice ──
  const look = A.lookBase + A.lookPerSpeed * r.speed;
  const curvNear = track.sampleAt(s + 18).curv + track.sampleAt(s + 40).curv;
  const inside = clamp(curvNear * 26, -1, 1);
  const hwAhead = track.sampleAt(s + look).hw;
  let laneTarget = inside * (hwAhead - 3.6) * 0.62 + ai.laneBias * (1 - Math.abs(inside));
  const myLat = r.pm.d;

  // sliding teacups: aim for the open side at the predicted arrival time
  for (const cup of track.teacups) {
    const ds = (cup.s - s + L) % L;
    if (ds < 3 || ds > 75) continue;
    const eta = ds / speedNow;
    const lat = track.teacupLateral(cup, race.time + eta);
    if (Math.abs(laneTarget - lat) < 5.2) {
      const left = lat - 5.8;
      const right = lat + 5.8;
      const lim = hwAhead - 2.3;
      const leftOk = left > -lim;
      const rightOk = right < lim;
      if (leftOk && rightOk) laneTarget = Math.abs(left - myLat) < Math.abs(right - myLat) ? left : right;
      else laneTarget = leftOk ? left : right;
    }
  }
  // slower rival straight ahead: pull out to pass
  let rivalAhead = null;
  for (const o of race.racers) {
    if (o === r || o.respawning) continue;
    const ds = o.progress - r.progress;
    if (ds > 0 && ds < 15 && Math.abs(o.pm.d - myLat) < 3.3 && Math.abs(o.y - r.y) < 2) {
      if (!rivalAhead || ds < rivalAhead.ds) rivalAhead = { o, ds };
    }
  }
  if (rivalAhead && rivalAhead.o.speed < r.speed + 2) {
    const od = rivalAhead.o.pm.d;
    laneTarget = od > laneTarget ? od - 3.8 : od + 3.8;
  }
  // visible slick patches in my lane: steer around them
  let slickAhead = 0;
  if (race.slicks.length) {
    const fx = Math.sin(r.heading);
    const fz = Math.cos(r.heading);
    let side = 0;
    for (const p of race.slicks) {
      if (p.owner === r.idx) continue;
      const dx = p.x - r.x;
      const dz = p.z - r.z;
      const fwd = dx * fx + dz * fz;
      if (fwd < 2 || fwd > 34) continue;
      const lat = dx * -fz + dz * fx;
      if (Math.abs(lat) < p.r + 1.6) {
        side += lat > 0 ? -1 : 1;
        if (!slickAhead || fwd < slickAhead) slickAhead = fwd;
      }
    }
    if (side !== 0) laneTarget = myLat + (side > 0 ? 5 : -5);
  }
  const laneLim = hwAhead - 2.4;
  laneTarget = clamp(laneTarget, -laneLim, laneLim);
  ai.lane = damp(ai.lane, laneTarget, 2.6, dt);

  // ── pursuit target ──
  let gapStop = false;
  if (onBranchRoute) {
    const sbT = sbNow + look;
    const bl = clamp(ai.lane * 0.4, -(br.hw - 3), br.hw - 3);
    if (sbT < br.length) track.branchPointAt(Math.max(0, sbT), bl, tp);
    else track.pointAt(br.sB + (sbT - br.length), ai.lane, tp);
    // the gap: cross on the span, by rail, by jump — or stop and wait like at a drawbridge
    const dGap = br.gap0 - sbNow;
    if (dGap > 0 && dGap < 90) {
      const eta0 = dGap / speedNow;
      const eta1 = (br.gap1 - sbNow) / speedNow;
      const spanOk = track.bridgeSolidDuring(race.time + eta0 - 0.15, race.time + eta1 + 0.25);
      const hasSkill = (skillId === 'railMaker' || skillId === 'slingshot') && r.sk.cd < eta0 && r.sk.phase === 'idle' && !r.finished;
      if (!spanOk && !hasSkill && !r.onRail && !r.jumping) {
        const stopDist = (r.speed * r.speed) / (2 * V.brake * 0.8) + 7;
        if (dGap < stopDist) gapStop = true;
      }
      if (!spanOk && ready && r.grounded) {
        if (skillId === 'railMaker' && dGap < Math.max(4, r.speed * 0.3)) inp.skill = true;
        if (skillId === 'slingshot') {
          const c = K.slingshot;
          const vJump = Math.max(r.speed, V.maxSpeed * r.stats.speed * c.minSpeedMul);
          const spare = vJump * c.airTime - BALANCE.track.bridge.gapLength - 3;
          const pressAt = r.speed * c.windup + clamp(spare * 0.5, 1.5, 6);
          if (dGap <= pressAt && dGap > r.speed * c.windup + 0.6) inp.skill = true;
        }
      }
    }
  } else {
    track.pointAt(s + look, ai.lane, tp);
  }
  const desired = Math.atan2(tp.x - r.x, tp.z - r.z);
  const err = angleDiff(desired, r.heading);
  inp.steer = clamp(-err * A.steerGain, -1, 1);

  // ── speed planning (brake for what is coming, at the real controller limits) ──
  const paceTop = V.maxSpeed * r.stats.speed * ai.level;
  let allowed = Infinity;
  if (!onBranchRoute || sbNow > br.length - 40) {
    const horizon = (r.speed * r.speed) / (2 * A.brakeDecel) + 20;
    for (let d = 4; d <= horizon; d += 6) {
      const vc = cornerSpeed(track.sampleAt(s + d).curv, r, ai.level);
      const v = Math.sqrt(vc * vc + 2 * A.brakeDecel * d);
      if (v < allowed) allowed = v;
    }
  }
  if (Math.abs(err) > 0.9) allowed = Math.min(allowed, 12); // pointing the wrong way: slow down and turn
  const boosted = r.sk.phase === 'active' && skillId === 'pirouette';
  if (!boosted && r.vf > paceTop) inp.throttle = 0;
  if (r.vf > allowed + 2) {
    inp.throttle = 0;
    inp.brake = clamp((r.vf - allowed) / 7, 0.25, 1);
  } else if (r.vf > allowed) {
    inp.throttle = 0;
  }
  if (gapStop) {
    inp.throttle = 0;
    inp.brake = r.vf > 0.8 ? 1 : 0;
  }
  if (r.finished) {
    // cool-down lap after the flag: ease off, no more skills
    if (r.vf > paceTop * 0.6) inp.throttle = 0;
    return;
  }

  // ── contextual skill use ──
  if (!ready || inp.skill) return;
  let want = false;
  const farFromBridge = distToA > 620 || (pastB > 6 && pastB < 250);
  switch (skillId) {
    case 'railMaker':
      // away from the shortcut the rail is a way over slick trails
      want = farFromBridge && slickAhead > 5 && slickAhead < 18 && r.grounded;
      break;
    case 'tantrum': {
      const reach = K.tantrum.radiusLengths * V.standardLength * 0.72;
      for (const o of race.racers) {
        if (o === r || o.respawning || o.grace > 0 || o.finished) continue;
        if (Math.abs(o.y - r.y) > 2) continue;
        if (Math.hypot(o.x - r.x, o.z - r.z) < reach) want = true;
      }
      break;
    }
    case 'pirouette':
      want = r.vf > V.maxSpeed * 0.62 && !onBranchRoute && !slickAhead && r.grounded && maxCurvAhead(track, s, 0, 130) < 0.0125;
      break;
    case 'slingshot': {
      if (!farFromBridge || !r.grounded) break;
      const straight = maxCurvAhead(track, s, 0, 50) < 0.014;
      if (!straight) break;
      if (slickAhead > 6 && slickAhead < 15) want = true;
      if (rivalAhead && rivalAhead.ds > 4 && rivalAhead.ds < 11 && rivalAhead.o.speed < r.speed - 0.5) want = true;
      for (const cup of track.teacups) {
        const ds = (cup.s - s + L) % L;
        if (ds > 9 && ds < 17 && Math.abs(track.teacupLateral(cup, race.time + ds / speedNow) - myLat) < 3.4) want = true;
      }
      break;
    }
    case 'eternalLove': {
      if (!r.grounded) break;
      const bend = maxCurvAhead(track, s, 0, 45) > 0.011;
      for (const o of race.racers) {
        if (o === r || o.respawning || o.finished) continue;
        const behind = r.progress - o.progress;
        if (behind > 5 && behind < (bend ? 34 : 16) && Math.abs(o.pm.d - myLat) < 6.5) want = true;
      }
      break;
    }
    case 'hurricane': {
      const reach = K.hurricane.radius + 1.2;
      for (const o of race.racers) {
        if (o === r || o.respawning || o.grace > 0 || o.finished) continue;
        if (Math.abs(o.y - r.y) > 2) continue;
        if (Math.hypot(o.x - r.x, o.z - r.z) < reach && Math.abs(o.progress - r.progress) < 8) want = true;
      }
      break;
    }
  }
  if (want) {
    ai.skillT += dt;
    if (ai.skillT >= ai.react) {
      inp.skill = true;
      ai.skillT = 0;
      ai.react = lerp(A.reactionMin, A.reactionMax, race.rng());
    }
  } else {
    ai.skillT = 0;
  }
}
