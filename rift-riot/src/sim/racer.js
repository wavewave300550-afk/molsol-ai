// Shared arcade vehicle controller. Every racer — handcar, stroller, crystal ball,
// granny, manatee or porta-potty — moves through this one function. Visuals are
// layered on top elsewhere and never feed back into the simulation.
import { BALANCE } from '../data/balance.js';
import { approach, clamp, damp, lerp } from './math.js';

export function createRacer(idx, def, isPlayer) {
  return {
    idx,
    def,
    stats: def.stats,
    isPlayer,
    // pose
    x: 0,
    y: 0,
    z: 0,
    heading: 0,
    vx: 0,
    vz: 0,
    vy: 0,
    // externally applied push velocity (decays)
    knockX: 0,
    knockZ: 0,
    pushLock: 0,
    // input (filled by player input or AI every step)
    input: { throttle: 0, brake: 0, steer: 0, drift: false, skill: false },
    steer: 0,
    // movement state
    grounded: true,
    airborne: false,
    onRail: false,
    jumping: false,
    jumpGravity: 0,
    drift: 0,
    driftTime: 0,
    driftCharged: false,
    boostTimer: 0,
    slickAmount: 0,
    slickTarget: 0,
    speed: 0,
    vf: 0,
    slip: 0,
    yawRate: 0,
    // track bookkeeping
    mainHint: 0,
    pm: { i: 0, s: 0, d: 0, hw: 8, y: 0, wall: true, along: 0, dist2: 0 },
    pb: { s: 0, d: 0, valid: false, y: 0, inGap: false },
    insideMain: true,
    prevSide: 0,
    onBranch: false,
    gy: 0,
    refY: 0,
    slope: 0,
    lap: 0,
    nextGate: 0,
    sLap: 0,
    progress: 0,
    lastSafeI: 0,
    wrongWay: false,
    wrongWayTime: 0,
    // race result
    finished: false,
    finishTime: 0,
    place: 0,
    rank: idx + 1,
    lapTimes: [],
    lapStart: 0,
    // recovery
    respawnTimer: 0,
    respawning: false,
    grace: 0,
    stuckTimer: 0,
    cupLock: 0,
    falls: 0,
    // skill state (filled by skills.js)
    sk: {
      cd: 0,
      active: 0,
      activeTotal: 0,
      phase: 'idle',
      t: 0,
      hitOnce: new Set(),
      lastHit: new Map(),
      dist: 0,
      uses: 0,
      denied: '',
    },
    railPts: [],
    railFade: 0,
    mods: { speedMul: 1, accelAdd: 0, turnMul: 1, gripMul: 1, lockDrift: false, minSpeed: 0, airControl: 0 },
    ai: null,
  };
}

function resetMods(m) {
  m.speedMul = 1;
  m.accelAdd = 0;
  m.turnMul = 1;
  m.gripMul = 1;
  m.lockDrift = false;
  m.minSpeed = 0;
  m.airControl = 0;
}

/**
 * Advance one racer by dt. `applyMods` lets the skill system adjust the shared
 * controller (speed cap, steering authority, grip) without bypassing it.
 */
export function stepVehicle(r, dt, applyMods) {
  const V = BALANCE.vehicle;
  const D = BALANCE.drift;
  const SL = BALANCE.slick;
  const st = r.stats;
  const inp = r.input;
  const m = r.mods;
  resetMods(m);
  if (applyMods) applyMods(r, m);

  r.steer = damp(r.steer, clamp(inp.steer, -1, 1), V.steerSmoothing, dt);

  let fx = Math.sin(r.heading);
  let fz = Math.cos(r.heading);
  let vf = r.vx * fx + r.vz * fz;
  const speedAbs = Math.abs(vf);
  const supported = r.grounded || r.onRail;

  // ── slick blend ──
  if (r.slickTarget > r.slickAmount) r.slickAmount = Math.min(1, r.slickAmount + dt * 9);
  else r.slickAmount = Math.max(r.slickTarget, r.slickAmount - dt / SL.recoverTime);

  // ── drift state (shared mechanic, not a skill) ──
  const wantsDrift = inp.drift && supported && !m.lockDrift && !r.onRail;
  if (r.drift === 0) {
    if (wantsDrift && Math.abs(inp.steer) > 0.25 && vf > D.minSpeed) {
      r.drift = inp.steer > 0 ? 1 : -1;
      r.driftTime = 0;
      r.driftCharged = false;
    }
  } else if (!wantsDrift || vf < D.minSpeed * 0.8) {
    if (r.driftCharged && r.boostTimer <= 0) r.boostTimer = D.boostTime; // never stacks
    r.drift = 0;
    r.driftTime = 0;
    r.driftCharged = false;
  }

  // ── steering ──
  let yawAuth = lerp(V.turnLow, V.turnHigh, clamp(speedAbs / V.maxSpeed, 0, 1)) * st.turn * m.turnMul;
  yawAuth *= Math.min(1, speedAbs / V.turnRampSpeed);
  yawAuth *= lerp(1, SL.steerMul, r.slickAmount);
  if (!supported) yawAuth *= m.airControl || V.airControl;
  let steerEff = r.steer;
  if (r.drift !== 0) {
    const into = (r.steer * r.drift + 1) * 0.5; // 0 = full counter-steer, 1 = steering into the drift
    steerEff = r.drift * lerp(D.outerSteer, D.innerSteer, into) * D.turnMul;
  }
  const yaw = -steerEff * yawAuth * (vf >= -0.5 ? 1 : -1);
  r.yawRate = yaw;
  r.heading += yaw * dt;

  // ── velocity in the new heading frame ──
  fx = Math.sin(r.heading);
  fz = Math.cos(r.heading);
  const rx = -fz;
  const rz = fx;
  vf = r.vx * fx + r.vz * fz;
  let vl = r.vx * rx + r.vz * rz;

  let grip = V.grip * st.grip * m.gripMul;
  if (r.drift !== 0) grip = D.grip;
  grip = lerp(grip, Math.min(grip, SL.grip), r.slickAmount);
  if (!supported) grip = 0.6;
  vl *= Math.exp(-grip * dt);

  // ── throttle / brake ──
  let maxS = V.maxSpeed * st.speed * m.speedMul;
  let accel = V.accel * st.accel + m.accelAdd;
  if (r.boostTimer > 0) {
    r.boostTimer -= dt;
    maxS *= D.boostSpeedMul;
    accel = Math.max(accel, D.boostAccel);
  }
  if (supported) {
    const total = Math.hypot(vf, vl);
    if (inp.brake > 0.05) {
      if (vf > 0.6) vf = Math.max(0, vf - V.brake * inp.brake * dt);
      else vf = approach(vf, -V.reverseSpeed * inp.brake, accel * 0.7 * dt);
    } else if (inp.throttle > 0.05) {
      if (total < maxS) {
        const ratio = clamp(vf / maxS, 0, 1);
        vf += accel * inp.throttle * (1 - 0.5 * ratio * ratio) * dt;
      } else if (total > maxS + 0.2) {
        vf = Math.max(0, vf - V.coastDrag * 1.6 * dt);
      }
    } else {
      vf = approach(vf, 0, V.coastDrag * dt);
    }
    if (m.minSpeed > 0 && vf < m.minSpeed) vf = approach(vf, m.minSpeed, V.accel * 2.5 * dt);
  }

  // drift charge: must genuinely be sliding at speed, continuously
  r.slip = Math.atan2(Math.abs(vl), Math.max(1, Math.abs(vf)));
  if (r.drift !== 0) {
    if (r.slip > D.minSlip && vf > D.minSpeed) {
      r.driftTime += dt;
      if (r.driftTime >= D.chargeTime) r.driftCharged = true;
    }
  }

  r.vx = fx * vf + rx * vl;
  r.vz = fz * vf + rz * vl;
  r.vf = vf;
  r.speed = Math.hypot(r.vx, r.vz);

  // ── external pushes ──
  const P = BALANCE.push;
  const k = Math.exp(-P.decay * dt);
  r.knockX *= k;
  r.knockZ *= k;
  if (r.pushLock > 0) r.pushLock -= dt;
  if (r.cupLock > 0) r.cupLock -= dt;
  if (r.grace > 0) r.grace -= dt;

  r.x += (r.vx + r.knockX) * dt;
  r.z += (r.vz + r.knockZ) * dt;
}
