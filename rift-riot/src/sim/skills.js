// One signature skill per racer. Each skill only talks to the race through the
// shared rules (push limiter, slick patches, vehicle mods) so players and AI get
// exactly the same behaviour.
import { BALANCE } from '../data/balance.js';

const K = BALANCE.skills;
const V = BALANCE.vehicle;

function endActive(r) {
  r.sk.active = 0;
  r.sk.phase = 'idle';
  r.sk.t = 0;
}

export const SKILLS = {
  // ── 001 Uncle Boonsong — RAIL MAKER ───────────────────────────────────────
  railMaker: {
    cfg: K.railMaker,
    canUse(race, r) {
      return r.grounded ? null : 'ต้องอยู่บนพื้นก่อน';
    },
    start(race, r) {
      const c = K.railMaker;
      r.sk.phase = 'active';
      r.sk.active = r.sk.activeTotal = c.duration;
      r.onRail = true;
      r.grounded = false;
      r.airborne = false;
      r.drift = 0;
      r.railPts.length = 0;
      r.railFade = 0;
      r.sk.dist = c.pieceSpacing;
    },
    mods(r, m) {
      if (!r.onRail) return;
      const c = K.railMaker;
      m.turnMul *= c.turnMul; // rails bend, they never kink
      m.lockDrift = true;
      m.gripMul *= 3; // flanged wheels: no sliding off the rail
      m.minSpeed = V.maxSpeed * r.stats.speed * c.minSpeedMul;
    },
    update(race, r, dt) {
      const c = K.railMaker;
      if (r.sk.phase === 'active') {
        r.sk.active -= dt;
        r.sk.dist += r.speed * dt;
        if (r.sk.dist >= c.pieceSpacing) {
          r.sk.dist = 0;
          r.railPts.push({ x: r.x, y: r.y, z: r.z, heading: r.heading });
        }
        if (r.sk.active <= 0) this.cancel(race, r);
      } else if (r.railFade > 0) {
        r.railFade -= dt;
        if (r.railFade <= 0) {
          r.railFade = 0;
          r.railPts.length = 0; // rails never pile up on the track
        }
      }
    },
    cancel(race, r) {
      if (r.onRail) {
        r.onRail = false;
        r.airborne = true; // drops the last few centimetres — or into the rift
        r.vy = 0;
        r.railFade = K.railMaker.fadeTime;
        race.emit('railEnd', r);
      }
      endActive(r);
    },
  },

  // ── 002 Baby Havoc — HELLISH TANTRUM ──────────────────────────────────────
  tantrum: {
    cfg: K.tantrum,
    start(race, r) {
      const c = K.tantrum;
      r.sk.phase = 'windup';
      r.sk.t = c.windup;
      r.sk.active = r.sk.activeTotal = c.windup + c.recover;
      r.sk.hitOnce.clear();
    },
    update(race, r, dt) {
      const c = K.tantrum;
      const sk = r.sk;
      if (sk.phase === 'idle') return;
      sk.active = Math.max(0, sk.active - dt);
      sk.t -= dt;
      if (sk.phase === 'windup' && sk.t <= 0) {
        const radius = c.radiusLengths * V.standardLength;
        race.emit('tantrumWave', r, { radius });
        for (const o of race.racers) {
          if (o === r || sk.hitOnce.has(o.idx)) continue;
          const dx = o.x - r.x;
          const dz = o.z - r.z;
          const d = Math.hypot(dx, dz);
          if (d > radius + V.radius) continue;
          sk.hitOnce.add(o.idx); // one shove per use, even if it was blocked
          const inv = d > 0.01 ? 1 / d : 0;
          const falloff = 1 - 0.35 * Math.min(1, d / radius);
          race.applyPush(o, d > 0.01 ? dx * inv : Math.sin(r.heading), d > 0.01 ? dz * inv : Math.cos(r.heading), c.strength * falloff, r);
        }
        sk.phase = 'recover';
        sk.t = c.recover;
      } else if (sk.phase === 'recover' && sk.t <= 0) {
        endActive(r);
      }
    },
    cancel(race, r) {
      endActive(r);
    },
  },

  // ── 003 Celestine — PIROUETTE ─────────────────────────────────────────────
  pirouette: {
    cfg: K.pirouette,
    start(race, r) {
      r.sk.phase = 'active';
      r.sk.active = r.sk.activeTotal = K.pirouette.duration;
    },
    mods(r, m) {
      if (r.sk.phase !== 'active') return;
      const c = K.pirouette;
      m.speedMul *= c.speedMul;
      m.accelAdd += c.accel;
      m.turnMul *= c.turnMul;
      m.gripMul *= c.gripMul;
    },
    update(race, r, dt) {
      if (r.sk.phase !== 'active') return;
      r.sk.active -= dt;
      if (r.sk.active <= 0) endActive(r);
    },
    cancel(race, r) {
      endActive(r);
    },
  },

  // ── 004 Granny Cracklebone — SPINE SLINGSHOT ──────────────────────────────
  slingshot: {
    cfg: K.slingshot,
    canUse(race, r) {
      return r.grounded ? null : 'ต้องอยู่บนพื้นก่อน';
    },
    start(race, r) {
      const c = K.slingshot;
      r.sk.phase = 'windup';
      r.sk.t = c.windup;
      r.sk.active = r.sk.activeTotal = c.windup + c.airTime;
    },
    mods(r, m) {
      if (r.jumping) m.airControl = K.slingshot.airControl;
    },
    update(race, r, dt) {
      const c = K.slingshot;
      const sk = r.sk;
      if (sk.phase === 'idle') return;
      sk.active = Math.max(0, sk.active - dt);
      if (sk.phase === 'windup') {
        sk.t -= dt;
        if (sk.t <= 0) {
          if (!r.grounded) {
            endActive(r); // lost her footing during the wind-up: no launch
            return;
          }
          sk.phase = 'air';
          r.grounded = false;
          r.airborne = true;
          r.jumping = true;
          r.jumpGravity = c.gravity;
          r.vy = (c.gravity * c.airTime) / 2;
          r.drift = 0;
          // spring forward: never launch slower than a healthy share of top speed
          const minV = V.maxSpeed * r.stats.speed * c.minSpeedMul;
          const fx = Math.sin(r.heading);
          const fz = Math.cos(r.heading);
          const vf = r.vx * fx + r.vz * fz;
          if (vf < minV) {
            r.vx += fx * (minV - vf);
            r.vz += fz * (minV - vf);
          }
          race.emit('slingLaunch', r);
        }
      } else if (sk.phase === 'air') {
        if (!r.jumping) endActive(r); // landed (race.js clears r.jumping)
      }
    },
    cancel(race, r) {
      r.jumping = false;
      r.jumpGravity = 0;
      endActive(r);
    },
  },

  // ── 005 Love Never Sinks — ETERNAL LOVE ───────────────────────────────────
  eternalLove: {
    cfg: K.eternalLove,
    canUse(race, r) {
      return r.grounded ? null : 'ต้องอยู่บนพื้นก่อน';
    },
    start(race, r) {
      r.sk.phase = 'active';
      r.sk.active = r.sk.activeTotal = K.eternalLove.duration;
      r.sk.dist = K.eternalLove.patchSpacing; // first patch right away
    },
    update(race, r, dt) {
      const c = K.eternalLove;
      if (r.sk.phase !== 'active') return;
      r.sk.active -= dt;
      r.sk.dist += r.speed * dt;
      // patches are only laid on real road surface under the trolley
      if (r.sk.dist >= c.patchSpacing && r.grounded) {
        r.sk.dist = 0;
        const back = 2.4;
        race.addSlick(r.x - Math.sin(r.heading) * back, r.gy, r.z - Math.cos(r.heading) * back, r.idx);
      }
      if (r.sk.active <= 0) endActive(r);
    },
    cancel(race, r) {
      endActive(r);
    },
  },

  // ── 006 Uncle Gator — FLORIDA HURRICANE ───────────────────────────────────
  hurricane: {
    cfg: K.hurricane,
    start(race, r) {
      r.sk.phase = 'active';
      r.sk.active = r.sk.activeTotal = K.hurricane.duration;
      r.sk.lastHit.clear();
    },
    mods(r, m) {
      if (r.sk.phase !== 'active') return;
      m.gripMul *= K.hurricane.ownerGripMul;
      m.turnMul *= K.hurricane.ownerTurnMul;
    },
    update(race, r, dt) {
      const c = K.hurricane;
      const sk = r.sk;
      if (sk.phase !== 'active') return;
      sk.active -= dt;
      for (const o of race.racers) {
        if (o === r) continue;
        const dx = o.x - r.x;
        const dz = o.z - r.z;
        const d = Math.hypot(dx, dz);
        if (d > c.radius + V.radius) continue;
        const last = sk.lastHit.get(o.idx);
        if (last !== undefined && race.time - last < c.perTargetInterval) continue;
        const inv = d > 0.01 ? 1 / d : 0;
        let nx = d > 0.01 ? dx * inv : 1;
        let nz = d > 0.01 ? dz * inv : 0;
        // a little swirl so the shove reads as a storm, not a wall
        const sx = nx - nz * 0.3;
        const sz = nz + nx * 0.3;
        const sl = Math.hypot(sx, sz);
        nx = sx / sl;
        nz = sz / sl;
        if (race.applyPush(o, nx, nz, c.strength, r)) sk.lastHit.set(o.idx, race.time);
      }
      if (sk.active <= 0) endActive(r);
    },
    cancel(race, r) {
      endActive(r);
    },
  },
};

/** Shared activation gate. Returns null on success or a reason string. */
export function tryUseSkill(race, r) {
  if (race.phase !== 'racing' || r.finished || r.respawning) return 'ยังใช้ไม่ได้';
  const sk = r.sk;
  if (sk.cd > 0 || sk.phase !== 'idle') return 'คูลดาวน์';
  const S = SKILLS[r.def.skill];
  const why = S.canUse ? S.canUse(race, r) : null;
  if (why) {
    // failed precondition never burns the cooldown; tell the HUD why
    sk.denied = why;
    race.emit('skillDenied', r, { why });
    return why;
  }
  sk.cd = S.cfg.cooldown; // cooldown starts on a successful press
  sk.uses++;
  S.start(race, r);
  race.emit('skill', r, { skill: r.def.skill });
  return null;
}

export function updateSkill(race, r, dt) {
  const sk = r.sk;
  if (sk.cd > 0) sk.cd = Math.max(0, sk.cd - dt);
  SKILLS[r.def.skill].update(race, r, dt);
}

export function applySkillMods(r, m) {
  const S = SKILLS[r.def.skill];
  if (S.mods) S.mods(r, m);
}

export function cancelSkill(race, r) {
  SKILLS[r.def.skill].cancel(race, r);
}
