// Race state machine: grid → countdown → racing → finished.
// Owns the rules every racer shares: walls, ground, falls, gates, laps, ranking,
// pushes, slick patches, obstacles and returning to the track.
import { BALANCE } from '../data/balance.js';
import { RACERS } from '../data/racers.js';
import { createRacer, stepVehicle } from './racer.js';
import { applySkillMods, cancelSkill, tryUseSkill, updateSkill } from './skills.js';
import { createAI, updateAI } from './ai.js';
import { angleDiff, clamp, makeRng } from './math.js';

const V = BALANCE.vehicle;
const tmpCup = { x: 0, y: 0, z: 0, lat: 0 };

export class Race {
  /**
   * @param {Track} track
   * @param {{playerId?: string|null, laps?: number, seed?: number}} opts
   *   playerId = null runs an all-AI race (used by tests and the attract mode).
   */
  constructor(track, opts = {}) {
    this.track = track;
    this.laps = opts.laps ?? BALANCE.race.laps;
    this.rng = makeRng(opts.seed ?? 1234);
    this.time = 0; // race clock (starts at GO)
    this.clock = 0; // total simulated time including the countdown
    this.countdown = BALANCE.race.countdown;
    this.phase = 'countdown';
    this.events = [];
    this.slicks = [];
    this.bridge = { solid: true, warn: false, phase: 0, timeToChange: 0 };
    this.finishOrder = [];
    this.playerFinishedAt = -1;
    this.done = false;
    this.racers = [];
    this.player = null;
    this.autopilot = !!opts.autopilot; // dev/test: AI drives the player's racer too

    // Player takes one racer; the AI drives every remaining one, so all six appear.
    const order = [];
    const playerDef = opts.playerId ? RACERS.find((d) => d.id === opts.playerId) : null;
    const others = RACERS.filter((d) => d !== playerDef);
    // shuffle AI grid order deterministically
    for (let i = others.length - 1; i > 0; i--) {
      const j = Math.floor(this.rng() * (i + 1));
      [others[i], others[j]] = [others[j], others[i]];
    }
    const slot = clamp(BALANCE.race.playerGridSlot, 0, RACERS.length - 1);
    for (let i = 0, k = 0; i < RACERS.length; i++) {
      if (playerDef && i === slot) order.push(playerDef);
      else order.push(others[k++]);
    }
    let aiN = 0;
    order.forEach((def, gridSlot) => {
      const r = createRacer(this.racers.length, def, def === playerDef);
      r.ai = createAI(this, r, aiN);
      if (!r.isPlayer) aiN++;
      this._placeOnGrid(r, gridSlot);
      this.racers.push(r);
      if (r.isPlayer) this.player = r;
    });
    this.ranking = this.racers.slice();
    this._updateRanking();
  }

  emit(type, racer, data) {
    this.events.push({ type, racer, ...(data || {}) });
  }

  _placeOnGrid(r, slot) {
    const t = this.track;
    const row = Math.floor(slot / 2);
    const col = slot % 2 === 0 ? -1 : 1;
    const s = t.length - 9 - row * 7.5 - (col > 0 ? 3 : 0);
    const p = t.pointAt(s, col * 4.2, {});
    r.x = p.x;
    r.z = p.z;
    r.y = p.y;
    r.heading = p.heading;
    r.mainHint = t.sampleAt(s).i;
    r.lastSafeI = r.mainHint;
    r.gy = r.refY = p.y;
    r.gridSlot = slot;
  }

  // ── shared rules ───────────────────────────────────────────────────────────

  /** Central push limiter. Returns true when the push was actually applied. */
  applyPush(target, nx, nz, strength, source) {
    const P = BALANCE.push;
    if (target.respawning || target.grace > 0 || target.finished) return false;
    if (source && Math.abs(target.y - source.y) > P.verticalReach) return false;
    if (target.pushLock > 0) return false;
    const kv = strength / target.stats.stability;
    target.knockX += nx * kv;
    target.knockZ += nz * kv;
    const mag = Math.hypot(target.knockX, target.knockZ);
    if (mag > P.maxKnock) {
      target.knockX *= P.maxKnock / mag;
      target.knockZ *= P.maxKnock / mag;
    }
    target.pushLock = P.globalLock;
    this.emit('pushed', target, { by: source ? source.idx : -1 });
    return true;
  }

  addSlick(x, y, z, owner) {
    const c = BALANCE.skills.eternalLove;
    if (this.slicks.length >= c.maxPatches) this.slicks.shift();
    this.slicks.push({ x, y, z, owner, life: c.patchLife, r: c.patchRadius });
  }

  // ── main step ──────────────────────────────────────────────────────────────

  /** Advance the whole race by one fixed step. */
  step(dt) {
    this.clock += dt;
    if (this.phase === 'countdown') {
      this.countdown -= dt;
      if (this.countdown <= 0) {
        this.phase = 'racing';
        this.emit('go', null);
      }
      // racers idle on the grid: no inputs, no skills, no cooldowns ticking
      for (const r of this.racers) r.input.skill = false;
      return;
    }
    if (this.done) return;
    this.time += dt;
    const track = this.track;
    track.bridgeState(this.time, this.bridge);

    // slick patches age out
    for (let i = this.slicks.length - 1; i >= 0; i--) {
      this.slicks[i].life -= dt;
      if (this.slicks[i].life <= 0) this.slicks.splice(i, 1);
    }

    const racers = this.racers;
    for (const r of racers) {
      if (r.respawning) {
        this._tickRespawn(r, dt);
        updateSkill(this, r, dt); // cooldown keeps running, nothing is refunded
        continue;
      }
      if (!r.isPlayer || r.finished || this.autopilot) updateAI(this, r, dt);
      if (r.input.skill) {
        r.input.skill = false;
        if (!r.finished) tryUseSkill(this, r);
      }
      r.px = r.x;
      r.pz = r.z;
      r.py = r.y;
      stepVehicle(r, dt, applySkillMods);
    }

    this._collideRacers();
    this._collideTeacups();

    for (const r of racers) {
      if (r.respawning) continue;
      this._constrain(r, dt);
      this._slickCheck(r);
      updateSkill(this, r, dt);
      this._gates(r);
      this._watchdog(r, dt);
    }

    this._updateRanking();

    if (this.playerFinishedAt >= 0 || !this.player) {
      const allDone = racers.every((r) => r.finished);
      const since = this.player ? this.time - this.playerFinishedAt : 0;
      if (allDone || (this.player && since > BALANCE.race.finishTimeout)) this.done = true;
    }
  }

  _collideRacers() {
    const R = V.radius;
    const racers = this.racers;
    for (let i = 0; i < racers.length; i++) {
      const a = racers[i];
      if (a.respawning) continue;
      for (let j = i + 1; j < racers.length; j++) {
        const b = racers[j];
        if (b.respawning) continue;
        if (Math.abs(a.y - b.y) > 1.9) continue; // jumping over someone is a real dodge
        const dx = b.x - a.x;
        const dz = b.z - a.z;
        const d2 = dx * dx + dz * dz;
        if (d2 >= 4 * R * R || d2 < 1e-6) continue;
        const d = Math.sqrt(d2);
        const nx = dx / d;
        const nz = dz / d;
        const overlap = 2 * R - d;
        const wa = b.stats.stability / (a.stats.stability + b.stats.stability);
        const wb = 1 - wa;
        a.x -= nx * overlap * wa;
        a.z -= nz * overlap * wa;
        b.x += nx * overlap * wb;
        b.z += nz * overlap * wb;
        const closing = (a.vx - b.vx) * nx + (a.vz - b.vz) * nz;
        if (closing > 0) {
          const imp = closing * (1 + V.bumpRestitution) * 0.5;
          a.vx -= nx * imp * wa * 2;
          a.vz -= nz * imp * wa * 2;
          b.vx += nx * imp * wb * 2;
          b.vz += nz * imp * wb * 2;
          if (closing > 3) this.emit('bump', a, { other: b.idx, power: closing });
        }
      }
    }
  }

  _collideTeacups() {
    const C = BALANCE.track.teacup;
    const track = this.track;
    for (const cup of track.teacups) {
      track.teacupPos(cup, this.time, tmpCup);
      for (const r of this.racers) {
        if (r.respawning) continue;
        if (r.y - tmpCup.y > C.height) continue; // low obstacle: can be jumped
        const dx = r.x - tmpCup.x;
        const dz = r.z - tmpCup.z;
        const lim = C.radius + V.radius;
        const d2 = dx * dx + dz * dz;
        if (d2 >= lim * lim) continue;
        const d = Math.sqrt(d2) || 0.001;
        const nx = dx / d;
        const nz = dz / d;
        r.x = tmpCup.x + nx * lim;
        r.z = tmpCup.z + nz * lim;
        const vn = r.vx * nx + r.vz * nz;
        if (vn < 0) {
          r.vx -= nx * vn;
          r.vz -= nz * vn;
        }
        if (r.cupLock <= 0) {
          r.cupLock = C.hitLock;
          r.vx *= C.hitSpeedMul;
          r.vz *= C.hitSpeedMul;
          r.knockX += nx * C.hitKnock;
          r.knockZ += nz * C.hitKnock;
          this.emit('cupHit', r);
        }
      }
    }
  }

  /** Walls, ground support, falling, landing. */
  _constrain(r, dt) {
    const track = this.track;
    const br = track.branch;
    const pm = track.projectMain(r.x, r.z, r.mainHint, r.pm);
    const pb = track.projectBranch(r.x, r.z, r.pb);
    const inBranch = pb.valid && Math.abs(pb.d) <= br.hw;
    const branchSolid = inBranch && (!pb.inGap || this.bridge.solid);

    // walls (tall, block everyone — including rails and jumps)
    if (pm.wall && !branchSolid) {
      const side = pm.d >= 0 ? 1 : -1;
      let target = null;
      if (r.insideMain) {
        const lim = pm.hw - V.radius;
        if (Math.abs(pm.d) > lim) target = side * lim;
      } else if (Math.abs(pm.d) < pm.hw + V.radius && r.prevSide === side) {
        target = side * (pm.hw + V.radius);
      }
      if (target !== null) {
        const a = track.samples[pm.i];
        const delta = target - pm.d;
        r.x += a.rx * delta;
        r.z += a.rz * delta;
        const inward = r.insideMain ? -side : side;
        const nx = a.rx * -inward;
        const nz = a.rz * -inward;
        const vn = r.vx * nx + r.vz * nz;
        if (vn > 0) {
          r.vx -= nx * vn * (1 + V.wallBounce);
          r.vz -= nz * vn * (1 + V.wallBounce);
          const hard = Math.min(1, vn / 16);
          const keep = 1 - V.wallScrub * hard;
          r.vx *= keep;
          r.vz *= keep;
          if (vn > 4) this.emit('wallHit', r, { power: vn });
        }
        // arcade forgiveness: scraping a wall steers you along it rather than pinning you
        const fwd = Math.sin(r.heading) * a.tx + Math.cos(r.heading) * a.tz;
        const along = a.heading + (fwd >= 0 ? 0 : Math.PI);
        const into = Math.sin(r.heading) * nx + Math.cos(r.heading) * nz;
        if (into > 0.02) r.heading += clamp(angleDiff(along, r.heading), -V.wallAlign * dt, V.wallAlign * dt);
        const kn = r.knockX * nx + r.knockZ * nz;
        if (kn > 0) {
          r.knockX -= nx * kn;
          r.knockZ -= nz * kn;
        }
        pm.d = target;
      }
    }
    r.insideMain = Math.abs(pm.d) <= pm.hw;
    r.prevSide = pm.d >= 0 ? 1 : -1;
    r.mainHint = pm.i;

    // ground support
    const onMain = r.insideMain;
    let support = null;
    if (onMain) support = pm.y;
    else if (branchSolid) support = pb.y;
    r.onBranch = !onMain && inBranch;
    r.slope = onMain ? track.samples[pm.i].slope : 0;

    if (r.onRail) {
      if (support !== null) r.refY = support;
      const target = r.refY + BALANCE.skills.railMaker.height;
      r.y += clamp(target - r.y, -5 * dt, 5 * dt);
      r.vy = 0;
      r.gy = r.refY;
    } else if (r.airborne) {
      const g = r.jumpGravity || V.gravity;
      r.vy -= g * dt;
      r.y += r.vy * dt;
      if (support !== null) r.gy = support;
      if (support !== null && r.vy <= 0 && r.y <= support && r.py >= support - 0.9) {
        r.y = support;
        r.vy = 0;
        r.airborne = false;
        r.grounded = true;
        r.refY = support;
        if (r.jumping) {
          r.jumping = false;
          r.jumpGravity = 0;
          this.emit('land', r);
        }
      }
    } else if (support !== null) {
      r.y = support;
      r.gy = r.refY = support;
      r.grounded = true;
    } else {
      // drove off an open edge: nothing underneath
      r.grounded = false;
      r.airborne = true;
      r.vy = 0;
      this.emit('edge', r);
    }

    // lap-relative progress used for ranking
    let s = pm.s;
    if (br && pb.valid && !onMain) {
      const dMain = Math.abs(pm.d) - pm.hw;
      const dBranch = Math.abs(pb.d) - br.hw;
      if (dBranch < dMain) s = br.sA + (pb.s / br.length) * br.mainLength;
    }
    r.sLap = s;

    // last safe place actually driven over (main road only, well inside the edges)
    if (r.grounded && onMain && Math.abs(pm.d) < pm.hw - 2 && r.lap > 0) {
      const g = this.track.gates;
      const lo = g[(r.nextGate - 1 + g.length) % g.length].s;
      const hi = r.nextGate === 0 ? track.length : g[r.nextGate].s;
      if (pm.s >= lo && pm.s <= hi) r.lastSafeI = pm.i;
    }

    // wrong-way detection for the HUD
    const a = track.samples[pm.i];
    const along = Math.sin(r.heading) * a.tx + Math.cos(r.heading) * a.tz;
    if (along < -0.25 && r.vf > 3 && onMain) r.wrongWayTime += dt;
    else r.wrongWayTime = 0;
    r.wrongWay = r.wrongWayTime > 0.7;
  }

  _slickCheck(r) {
    r.slickTarget = 0;
    if (!this.slicks.length) return;
    // on the ground (the hovering porta-potty counts); rails and jumps pass above
    if (r.onRail || r.airborne || r.y - r.gy > BALANCE.slick.groundTolerance) return;
    for (const p of this.slicks) {
      if (p.owner === r.idx) continue; // owners keep their footing on their own trail
      if (Math.abs(p.y - r.y) > 1.5) continue;
      const dx = r.x - p.x;
      const dz = r.z - p.z;
      if (dx * dx + dz * dz < p.r * p.r) {
        r.slickTarget = 1; // overlapping patches never stack
        return;
      }
    }
  }

  _gates(r) {
    if (r.finished) return;
    const track = this.track;
    const gates = track.gates;
    const g = gates[r.nextGate];
    const a = track.samples[g.i];
    const before = (r.px - a.x) * a.tx + (r.pz - a.z) * a.tz;
    const after = (r.x - a.x) * a.tx + (r.z - a.z) * a.tz;
    if (before < 0 && after >= 0 && before > -12) {
      const lat = (r.x - a.x) * a.rx + (r.z - a.z) * a.rz;
      if (Math.abs(lat) <= a.hw + 3) {
        if (r.nextGate === 0) {
          if (r.lap > 0) {
            r.lapTimes.push(this.time - r.lapStart);
            this.emit('lap', r, { lap: r.lap });
          }
          r.lapStart = this.time;
          r.lap++;
          if (r.lap > this.laps) this._finish(r);
        }
        r.nextGate = (r.nextGate + 1) % gates.length;
      }
    }
    // progress: laps done + distance inside the current gate window
    const L = track.length;
    if (r.lap === 0) {
      r.progress = (r.sLap > L / 2 ? r.sLap - L : 0) - L;
    } else {
      const lo = gates[(r.nextGate - 1 + gates.length) % gates.length].s;
      let hi = r.nextGate === 0 ? L : gates[r.nextGate].s;
      let s = r.sLap;
      if (r.nextGate === 0 && s < L / 2) s = L;
      if (r.nextGate === 1 && s > L / 2) s = 0;
      if (hi < lo) hi = L;
      r.progress = (r.lap - 1) * L + clamp(s, lo, hi);
    }
  }

  _finish(r) {
    r.finished = true;
    r.finishTime = this.time;
    r.lap = this.laps;
    this.finishOrder.push(r);
    r.place = this.finishOrder.length; // locked in: never re-sorted afterwards
    cancelSkill(this, r);
    this.emit('finish', r, { place: r.place });
    if (r.isPlayer) {
      this.playerFinishedAt = this.time;
      this.phase = 'finished';
    }
  }

  _watchdog(r, dt) {
    const RS = BALANCE.respawn;
    let why = null;
    if (r.y < r.refY - RS.killDepth) why = 'fall';
    else if (r.pm.dist2 > RS.outOfBounds * RS.outOfBounds) why = 'bounds';
    else if (!r.finished) {
      if (r.input.throttle > 0.5 && r.speed < RS.stuckSpeed && r.grounded) r.stuckTimer += dt;
      else r.stuckTimer = Math.max(0, r.stuckTimer - dt * 2);
      if (r.stuckTimer > RS.stuckTime) why = 'stuck';
    }
    if (why) this.startRespawn(r, why);
  }

  startRespawn(r, why) {
    if (r.respawning) return;
    r.respawning = true;
    r.respawnTimer = BALANCE.respawn.delay;
    r.falls++;
    cancelSkill(this, r); // active effect ends; the cooldown is NOT refunded
    r.onRail = false;
    r.drift = 0;
    r.driftTime = 0;
    r.driftCharged = false;
    r.boostTimer = 0;
    r.stuckTimer = 0;
    this.emit('fall', r, { why });
  }

  _tickRespawn(r, dt) {
    // keep falling visually until the timer runs out
    if (r.airborne) {
      r.vy -= V.gravity * dt;
      r.y += r.vy * dt;
      r.x += r.vx * dt * 0.5;
      r.z += r.vz * dt * 0.5;
    }
    r.respawnTimer -= dt;
    if (r.respawnTimer > 0) return;
    const track = this.track;
    // last safe spot that was really driven over, backed off a little — never forward
    const back = Math.round(BALANCE.respawn.backOff / track.step);
    let i = (r.lastSafeI - back + track.n) % track.n;
    if (r.lap === 0) i = r.lastSafeI;
    const a = track.samples[i];
    r.x = a.x;
    r.z = a.z;
    r.y = a.y;
    r.gy = r.refY = a.y;
    r.heading = a.heading;
    r.vx = r.vz = r.vy = 0;
    r.knockX = r.knockZ = 0;
    r.steer = 0;
    r.mainHint = i;
    r.insideMain = true;
    r.airborne = false;
    r.grounded = true;
    r.jumping = false;
    r.jumpGravity = 0;
    r.slickAmount = r.slickTarget = 0;
    r.respawning = false;
    r.grace = BALANCE.respawn.grace;
    r.px = r.x;
    r.pz = r.z;
    r.py = r.y;
    if (r.ai) r.ai.route = 'main';
    this.emit('respawn', r);
  }

  _updateRanking() {
    const list = this.ranking;
    list.sort((a, b) => {
      if (a.finished && b.finished) return a.place - b.place;
      if (a.finished) return -1;
      if (b.finished) return 1;
      return b.progress - a.progress;
    });
    for (let i = 0; i < list.length; i++) list[i].rank = i + 1;
  }

  /** Real results only: finished racers carry their recorded time, others are still racing. */
  results() {
    return this.ranking.map((r) => ({
      id: r.def.id,
      name: r.def.name,
      nameTh: r.def.nameTh,
      isPlayer: r.isPlayer,
      finished: r.finished,
      place: r.finished ? r.place : r.rank,
      time: r.finished ? r.finishTime : null,
      bestLap: r.lapTimes.length ? Math.min(...r.lapTimes) : null,
      lap: Math.min(this.laps, Math.max(1, r.lap)),
    }));
  }
}

/** Fixed-step driver: the same simulation regardless of display frame rate. */
export class FixedLoop {
  constructor(race) {
    this.race = race;
    this.acc = 0;
    this.alpha = 0;
  }
  advance(frameDt) {
    const dt = BALANCE.race.fixedDt;
    this.acc += Math.min(frameDt, dt * BALANCE.race.maxStepsPerFrame);
    let steps = 0;
    while (this.acc >= dt - 1e-9) {
      this.race.step(dt);
      this.acc -= dt;
      steps++;
    }
    this.alpha = this.acc / dt;
    return steps;
  }
}
