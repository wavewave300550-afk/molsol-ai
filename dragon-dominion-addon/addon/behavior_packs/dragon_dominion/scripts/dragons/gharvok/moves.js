// Gharvok's moves: the six boss attacks, the roar, reactions and the reposition leap.
// Each move is a small timeline: tick(b, m) runs once per game tick (m.t = ticks since start) and returns true
// when it is finished. Telegraph, hit frames, sounds and effects are all keyed to the animation timings that
// tools/gen_anims.py writes to timings.js, so damage lands on the frame the animation draws it.
import { CONFIG } from "./config.js";
import { TIMINGS } from "./timings.js";
import { HitSet, inBand, inCone, knockAway, knockDir, playersNear, segDistXZ, strike } from "../../core/combat.js";
import { particle, shake, sound } from "../../core/fx.js";
import { clearAbove, groundAt, probeFront } from "../../core/terrain.js";
import { clamp, lerp, sec } from "../../core/util.js";
import { dirOf, distXZ, local, relAngle, yawTo } from "../../core/vec.js";

const A = CONFIG.attacks;
const T = TIMINGS;
const NS = "dragon_dominion";
const at = (m, s) => m.t === sec(s);
const between = (m, a, b) => m.t >= sec(a) && m.t <= sec(b);

function dmgRange(v, phase) {
  if (!Array.isArray(v)) return v;
  return phase >= 3 ? v[v.length - 1] : v[0];
}

// ===================================================================================== ROAR (alert / phase / idle)
export const roar = {
  name: "roar",
  interruptible: false,
  start(b, m) {
    b.anim("roar");
    b.setState(m.args?.idle ? "IDLE" : "ALERT");
  },
  tick(b, m) {
    if (!m.args?.idle && b.target && m.t < sec(0.7)) b.face(b.target.location, 6);
    if (at(m, T.roar.shout)) {
      sound(b.dim, "mob.ravager.roar", b.mouth(), m.args?.idle ? 2.5 : 4, 0.72);
      if (!m.args?.idle) shake(b.viewers(28), 0.25, 1.0);
    }
    return m.t >= sec(T.roar.length);
  },
};

export const headScan = {
  name: "idle_head_scan",
  interruptible: true,
  start(b) {
    b.anim("idle_head_scan");
  },
  tick(b, m) {
    return m.t >= sec(T.idle_head_scan.length);
  },
};

// ===================================================================================== SKILL 02 - TWIN CLAW
export const twinClaw = {
  name: "twin_claw",
  interruptible: true,
  start(b, m) {
    b.anim("claw_combo");
    b.setState("ATTACK_WINDUP");
    m.hits = [new HitSet(), new HitSet()];
    sound(b.dim, "mob.polarbear.warning", b.mouth(), 2, 0.6);
  },
  tick(b, m) {
    const c = A.twin_claw;
    // keeps tracking a little during the wind-ups, never during a swing
    if (m.t < sec(0.35) || between(m, 0.66, 0.85)) b.face(b.target?.location, 3);
    T.claw_combo.hits.forEach((h, i) => {
      if (m.t === sec(h) - 2) b.setState("ATTACK_ACTIVE");
      if (between(m, h - 0.05, h + 0.05)) {
        const o = b.pos();
        const offset = i === 0 ? 20 : -20; // left paw sweeps the dragon's left side first
        for (const p of playersNear(b.dim, o, c.range + 1)) {
          if (inCone(o, b.yaw, p.location, c.range, c.halfAngle, offset) && inBand(p.location, o.y - 1, o.y + 4)) {
            if (strike(b.e, p, m.hits[i], dmgRange(c.damage, b.phase), c.knockback, o)) {
              sound(b.dim, "mob.ravager.bite", p.location, 1.2, 0.8);
            }
          }
        }
        if (m.t === sec(h)) {
          particle(b.dim, `${NS}:claw_slash`, local(o, b.yaw, c.range * 0.6, i === 0 ? -1.5 : 1.5, 1.2));
          sound(b.dim, "mob.ravager.attack", o, 1.5, 0.75 + i * 0.1);
        }
      }
      if (m.t === sec(h + 0.1)) b.setState(i === 0 ? "ATTACK_WINDUP" : "RECOVERY");
    });
    return m.t >= sec(T.claw_combo.length);
  },
  end(b) {
    b.cooldown("twin_claw", A.twin_claw.cooldown);
  },
};

// ===================================================================================== SKILL 01 - CRUSHING CHARGE
export const crushingCharge = {
  name: "crushing_charge",
  interruptible: true,
  start(b, m) {
    b.anim("charge_windup");
    b.setState("ATTACK_WINDUP");
    m.stage = "windup";
    m.hits = new HitSet();
    m.travelled = 0;
    sound(b.dim, "mob.ravager.roar", b.mouth(), 3, 1.1);
  },
  tick(b, m) {
    const c = A.crushing_charge;
    const broken = b.skull >= 2;
    if (m.stage === "windup") {
      if (m.t < sec(c.lockAt)) b.face(b.target?.location, 7);
      if (m.t === sec(c.lockAt)) {
        m.yaw = b.yaw; // commit: the charge direction no longer follows the target
        m.dir = dirOf(m.yaw);
        // run through the target's position and a little beyond, never across the combat boundary
        const d0 = b.target ? distXZ(b.pos(), b.target.location) : c.maxRange;
        m.maxTravel = clamp(d0 + 7, 10, c.maxRange + 4);
        const o = b.pos();
        for (let k = 3; k <= 20; k += 2.5) particle(b.dim, `${NS}:charge_line`, local(o, m.yaw, k, 0, 0.2));
        sound(b.dim, "mob.ravager.stun", o, 2, 0.6);
      }
      if (m.t === sec(0.8) || m.t === sec(1.2)) particle(b.dim, `${NS}:dust_puff`, local(b.pos(), b.yaw, 2.5, 1.5, 0.2));
      if (m.t >= sec(T.charge_windup.length)) {
        m.stage = "run";
        m.runT = 0;
        b.anim("charge");
        b.setState("ATTACK_ACTIVE");
      }
      return false;
    }
    if (m.stage === "run") {
      m.runT++;
      const scale = broken ? CONFIG.skull.brokenChargeScale : 1;
      const speed = c.speed * scale * clamp(m.runT / c.accelTicks, 0.3, 1);
      const o = b.pos();
      // obstacle ahead? (3 wide x 3 tall wall slab just in front of the skull)
      const wall = probeFront(b.dim, o, m.yaw, CONFIG.geometry.bodyRadius + 1.6, 3, 3, 1);
      if (wall.hard >= 4 || wall.solid >= 6) return this.impact(b, m, true);
      const res = b.step(speed, m.yaw, { maxDrop: 3 });
      m.travelled += res.moved;
      if (res.blocked) return this.impact(b, m, res.hard);
      if (res.drop) return this.stop(b, m);
      // trample: players in front of / beside the charging body
      const head = local(b.pos(), m.yaw, CONFIG.geometry.headForward, 0, 0);
      const tail = local(b.pos(), m.yaw, -1.5, 0, 0);
      for (const p of playersNear(b.dim, b.pos(), 8)) {
        const l = p.location;
        if (segDistXZ(l, tail, head) <= c.hitRadius && inBand(l, o.y - 1, o.y + 4)) {
          const side = relAngle(b.pos(), m.yaw, l) >= 0 ? 1 : -1;
          if (strike(b.e, p, m.hits, Math.round(c.damage * scale), null, head)) {
            const f = m.dir;
            knockDir(p, { x: f.x * 0.8 + -f.z * side * 0.6, z: f.z * 0.8 + f.x * side * 0.6 }, c.knockback.h, c.knockback.v);
            sound(b.dim, "mob.ravager.attack", l, 2, 0.6);
          }
        }
      }
      if (m.runT >= c.maxTicks || m.travelled >= m.maxTravel) return this.stop(b, m);
      if (distXZ(local(b.pos(), m.yaw, 3), b.home) > CONFIG.detection.boundary) return this.stop(b, m);
      return false;
    }
    if (m.stage === "brake") {
      m.brakeT++;
      b.step(c.speed * 0.4 * (1 - m.brakeT / 10), m.yaw, { maxDrop: 2 });
      return m.brakeT >= sec(1.0);
    }
    return true;
  },
  stop(b, m) {
    m.stage = "brake";
    m.brakeT = 0;
    b.anim("none");
    b.gait(0);
    b.setState("RECOVERY");
    particle(b.dim, `${NS}:dust_ring`, b.pos());
    return false;
  },
  impact(b, m, hard) {
    const o = b.pos();
    particle(b.dim, `${NS}:impact_burst`, local(o, m.yaw, CONFIG.geometry.headForward, 0, 2.5));
    particle(b.dim, `${NS}:dust_ring`, local(o, m.yaw, 3, 0, 0));
    sound(b.dim, "random.explode", o, 1.2, 0.7);
    sound(b.dim, "mob.irongolem.hit", o, 3, 0.5);
    shake(b.viewers(24), 0.45, 0.6);
    if (!hard) return this.stop(b, m);
    // a solid wall: the skull takes the blow, the dragon is stunned (the crown state makes it longer)
    m.impacted = true;
    b.queueReaction("charge_impact");
    return true;
  },
  end(b, m) {
    b.cooldown("crushing_charge", A.crushing_charge.cooldown);
    b.gait(0);
    if (!m.impacted) b.majorAttackDone();
  },
};

// ===================================================================================== SKILL 03 - RUDDER SWEEP
export const rudderSweep = {
  name: "rudder_sweep",
  interruptible: true,
  start(b, m) {
    b.anim("tail_sweep");
    b.setState("ATTACK_WINDUP");
    m.hits = new HitSet();
    sound(b.dim, "mob.ravager.ambient", b.pos(), 2.5, 0.6);
  },
  tick(b, m) {
    const c = A.rudder_sweep;
    const t0 = T.tail_sweep.hit_start;
    const t1 = T.tail_sweep.hit_end;
    if (m.t < sec(0.4)) particle(b.dim, `${NS}:dust_puff`, local(b.pos(), b.yaw, -CONFIG.geometry.tailBack, 0, 0.3));
    if (m.t === sec(t0) - 1) b.setState("ATTACK_ACTIVE");
    if (between(m, t0, t1)) {
      // the tail sweeps from the dragon's left flank (-60 deg), across the back, to its right flank (+60 deg)
      const o = b.pos();
      const k = (m.t - sec(t0)) / Math.max(1, sec(t1) - sec(t0));
      for (const p of playersNear(b.dim, o, c.radius + 1)) {
        const l = p.location;
        const a = relAngle(o, b.yaw, l); // negative = dragon's left
        if (distXZ(o, l) > c.radius || Math.abs(a) < c.minAngle || !inBand(l, o.y - 1, o.y + 3)) continue;
        const prog = ((((-60 - a) % 360) + 360) % 360) / 240; // 0 at the start of the arc, 1 at its end
        if (prog <= Math.min(1.0, k + 0.12)) strike(b.e, p, m.hits, c.damage, c.knockback, o);
      }
      if (m.t % 3 === 0) {
        const bearing = -60 - k * 240;
        particle(b.dim, `${NS}:tail_trail`, local(o, b.yaw + bearing, CONFIG.geometry.tailBack * 0.9, 0, 0.8));
      }
      if (m.t === sec(t0) + 2) sound(b.dim, "mob.enderdragon.flap", o, 2, 0.5);
    }
    if (m.t === sec(t1) + 1) b.setState("RECOVERY");
    return m.t >= sec(T.tail_sweep.length);
  },
  end(b) {
    b.cooldown("rudder_sweep", A.rudder_sweep.cooldown);
  },
};

// ===================================================================================== SKILL 04 - WING PRESSURE
export const wingPressure = {
  name: "wing_pressure",
  interruptible: true,
  start(b, m) {
    b.anim("wing_pressure");
    b.setState("ATTACK_WINDUP");
    m.hits = new HitSet();
    sound(b.dim, "mob.enderdragon.growl", b.mouth(), 3, 0.8);
  },
  tick(b, m) {
    const c = A.wing_pressure;
    if (m.t < sec(0.7)) b.face(b.target?.location, 4);
    if (m.t === sec(0.5) || m.t === sec(0.75)) sound(b.dim, "mob.enderdragon.flap", b.pos(), 2, 0.7);
    if (at(m, T.wing_pressure.gust)) {
      b.setState("ATTACK_ACTIVE");
      const o = b.pos();
      sound(b.dim, "mob.enderdragon.flap", o, 4, 0.45);
      sound(b.dim, "mob.ravager.roar", o, 2, 1.3);
      for (let k = 2; k <= c.range; k += 3) {
        particle(b.dim, `${NS}:wing_gust`, local(o, b.yaw, k, 0, 1.5));
      }
      particle(b.dim, `${NS}:dust_ring`, o);
      shake(b.viewers(20), 0.2, 0.5);
      for (const p of playersNear(b.dim, o, c.range + 1)) {
        const l = p.location;
        if (inCone(o, b.yaw, l, c.range, c.halfAngle) && inBand(l, o.y - 2, o.y + 6)) {
          const d = distXZ(o, l);
          const scale = clamp(1.25 - d / c.range, 0.5, 1.1);
          strike(b.e, p, m.hits, dmgRange(c.damage, b.phase), { h: c.knockback.h * scale, v: c.knockback.v }, o, 4);
        } else if (distXZ(o, l) <= c.pushRadius) {
          knockAway(p, o, c.pushKnockback.h, c.pushKnockback.v); // creates space all around, no damage
        }
      }
    }
    if (m.t === sec(T.wing_pressure.gust + 0.2)) b.setState("RECOVERY");
    return m.t >= sec(T.wing_pressure.length);
  },
  end(b) {
    b.cooldown("wing_pressure", A.wing_pressure.cooldown);
  },
};

// ===================================================================================== SKILL 05 - CLIFF DIVE
/** Pick a landing spot near the target: on ground, inside the combat boundary, with sky above. */
export function diveSpot(b, target) {
  const c = A.cliff_dive;
  const base = target.location;
  const tries = [[0, 0], [2, 0], [-2, 0], [0, 2], [0, -2], [3, 3], [-3, -3]];
  for (const [dx, dz] of tries) {
    const x = base.x + dx;
    const z = base.z + dz;
    const g = groundAt(b.dim, x, z, base.y, 3, 6);
    if (g === undefined) continue;
    if (!clearAbove(b.dim, x, g, z, 6)) continue;
    if (distXZ(b.home, { x, z }) > CONFIG.detection.boundary) continue;
    return { x, y: g, z };
  }
  return undefined;
}

export function skyClear(b) {
  const o = b.pos();
  return clearAbove(b.dim, o.x, o.y + 4, o.z, A.cliff_dive.height);
}

export const cliffDive = {
  name: "cliff_dive",
  interruptible: false, // airborne: fractures/phase changes are queued until it lands
  airborne: true,
  start(b, m) {
    b.anim("takeoff");
    b.setState("ATTACK_WINDUP");
    m.stage = "takeoff";
    m.hits = new HitSet();
    m.from = b.pos();
    sound(b.dim, "mob.enderdragon.growl", b.mouth(), 3, 0.7);
  },
  tick(b, m) {
    const c = A.cliff_dive;
    const o = b.pos();
    if (m.t > sec(c.maxAirTime) && m.stage !== "land") return this.abort(b, m);
    switch (m.stage) {
      case "takeoff": {
        b.face(b.target?.location, 5);
        if (m.t === sec(T.takeoff.liftoff)) {
          b.toAir();
          b.flight(1);
          particle(b.dim, `${NS}:dust_ring`, o);
          sound(b.dim, "mob.enderdragon.flap", o, 3, 0.6);
          m.stage = "rise";
          m.st = 0;
          m.rise0 = o;
          m.peak = { x: o.x, y: o.y + c.height, z: o.z };
        }
        return false;
      }
      case "rise": {
        m.st++;
        const k = clamp(m.st / sec(c.riseTime), 0, 1);
        const e = 1 - (1 - k) * (1 - k);
        const fwd = b.target ? dirOf(yawTo(o, b.target.location)) : dirOf(b.yaw);
        const p = { x: m.rise0.x + fwd.x * 3 * e, y: lerp(m.rise0.y, m.peak.y, e), z: m.rise0.z + fwd.z * 3 * e };
        if (!clearAbove(b.dim, p.x, p.y + 1, p.z, 4)) return this.abort(b, m);
        b.place(p);
        if (b.target) b.face(b.target.location, 6);
        if (m.st % 16 === 0) sound(b.dim, "mob.enderdragon.flap", p, 2, 0.7);
        if (k >= 1) {
          if (!b.target) return this.abort(b, m);
          m.spot = diveSpot(b, b.target);
          if (!m.spot) return this.abort(b, m);
          m.stage = "mark";
          m.st = 0;
          b.setState("AIRBORNE");
          sound(b.dim, "mob.enderdragon.growl", p, 3, 1.0);
        }
        return false;
      }
      case "mark": {
        // the landing zone is fixed now and marked on the ground; the dragon hovers and lines up
        m.st++;
        b.face(m.spot, 8);
        if (m.st % 4 === 1) {
          particle(b.dim, `${NS}:warning_ring`, { x: m.spot.x, y: m.spot.y + 0.15, z: m.spot.z }, { "variable.radius": c.innerRadius + 0.5 });
          particle(b.dim, `${NS}:warning_fill`, { x: m.spot.x, y: m.spot.y + 0.1, z: m.spot.z }, { "variable.radius": c.innerRadius });
        }
        if (m.st >= sec(c.warning - c.diveTime)) {
          m.stage = "dive";
          m.st = 0;
          m.dive0 = b.pos();
          b.flight(2);
          b.anim("cliff_dive");
          b.setState("ATTACK_ACTIVE");
          sound(b.dim, "mob.enderdragon.flap", o, 3, 0.4);
        }
        return false;
      }
      case "dive": {
        m.st++;
        const n = sec(c.diveTime);
        const k = clamp(m.st / n, 0, 1);
        const e = k * k; // accelerating dive
        const p = { x: lerp(m.dive0.x, m.spot.x, k), y: lerp(m.dive0.y, m.spot.y, e), z: lerp(m.dive0.z, m.spot.z, k) };
        b.place(p);
        if (m.st % 3 === 0) {
          particle(b.dim, `${NS}:warning_ring`, { x: m.spot.x, y: m.spot.y + 0.15, z: m.spot.z }, { "variable.radius": c.innerRadius + 0.5 });
        }
        if (k >= 1) return this.land(b, m, true);
        return false;
      }
      case "land": {
        m.st++;
        if (m.st === sec(0.6)) b.setState("RECOVERY");
        return m.st >= sec(T.landing.length + 0.6);
      }
    }
    return true;
  },
  land(b, m, strikeGround) {
    const c = A.cliff_dive;
    b.toGround();
    b.flight(0);
    b.anim("landing");
    m.stage = "land";
    m.st = 0;
    const o = b.pos();
    if (strikeGround) {
      particle(b.dim, `${NS}:dust_ring`, o);
      particle(b.dim, `${NS}:shockwave`, o, { "variable.radius": c.outerRadius * 0.6 });
      particle(b.dim, `${NS}:impact_burst`, o);
      sound(b.dim, "random.explode", o, 1.5, 0.6);
      shake(b.viewers(28), 0.6, 0.8);
      for (const p of playersNear(b.dim, o, c.outerRadius + 1)) {
        const l = p.location;
        const d = distXZ(o, l);
        if (!inBand(l, o.y - 2, o.y + 5)) continue;
        if (d <= c.innerRadius) strike(b.e, p, m.hits, c.damage, c.knockback, o, 4);
        else if (d <= c.outerRadius) strike(b.e, p, m.hits, c.outerDamage, { h: c.knockback.h * 0.7, v: c.knockback.v * 0.7 }, o, 4);
      }
    }
    return false;
  },
  abort(b, m) {
    // no safe dive: glide straight down to the ground below and land without a shockwave
    const o = b.pos();
    const g = groundAt(b.dim, o.x, o.z, o.y, 1, 40);
    if (g !== undefined) b.place({ x: o.x, y: g, z: o.z });
    else b.place(m.from);
    return this.land(b, m, false);
  },
  end(b, m) {
    if (b.flightCode !== 0 || b.inAir) {
      b.toGround();
      b.flight(0);
    }
    b.cooldown("cliff_dive", A.cliff_dive.cooldown);
    b.majorAttackDone();
  },
};

// ===================================================================================== SKILL 06 - SKULLBREAKER
export const skullbreaker = {
  name: "skullbreaker",
  interruptible: true,
  start(b, m) {
    b.anim("skullbreaker");
    b.setState("ATTACK_WINDUP");
    m.hits = new HitSet();
    sound(b.dim, "mob.ravager.roar", b.mouth(), 3, 0.55);
  },
  tick(b, m) {
    const c = A.skullbreaker;
    const tImpact = T.skullbreaker.impact;
    if (m.t < sec(c.warningFrom)) b.face(b.target?.location, 5);
    if (m.t === sec(c.warningFrom)) {
      const o = b.pos();
      const g = groundAt(b.dim, local(o, b.yaw, CONFIG.geometry.headForward + 0.5).x, local(o, b.yaw, CONFIG.geometry.headForward + 0.5).z, o.y, 2, 4);
      m.point = { ...local(o, b.yaw, CONFIG.geometry.headForward + 0.5), y: g ?? o.y };
    }
    if (m.point && m.t >= sec(c.warningFrom) && m.t < sec(tImpact) && (m.t - sec(c.warningFrom)) % 4 === 0) {
      const p = { x: m.point.x, y: m.point.y + 0.15, z: m.point.z };
      particle(b.dim, `${NS}:warning_ring`, p, { "variable.radius": c.coreRadius });
      particle(b.dim, `${NS}:warning_ring`, p, { "variable.radius": c.waveMax * 0.6 });
    }
    if (m.t === sec(1.1)) sound(b.dim, "mob.ravager.stun", b.pos(), 2.5, 0.5);
    if (at(m, tImpact)) {
      b.setState("ATTACK_ACTIVE");
      const p = m.point;
      sound(b.dim, "random.explode", p, 2, 0.5);
      sound(b.dim, "mob.irongolem.hit", p, 3, 0.4);
      particle(b.dim, `${NS}:impact_burst`, { x: p.x, y: p.y + 0.5, z: p.z });
      particle(b.dim, `${NS}:dust_ring`, p);
      shake(b.viewers(32), 0.8, 1.0);
      for (const pl of playersNear(b.dim, p, c.coreRadius + 0.5)) {
        if (inBand(pl.location, p.y - 2, p.y + 4)) {
          strike(b.e, pl, m.hits, dmgRange(c.damage, distXZ(p, pl.location) < c.coreRadius * 0.5 ? 3 : 1), c.knockback, p, 4);
        }
      }
      m.wave = 0;
    }
    if (m.wave !== undefined && m.wave <= c.waveTicks) {
      // expanding shockwave along the ground: jump over it or be outside it
      const p = m.point;
      const r = lerp(c.coreRadius, c.waveMax, m.wave / c.waveTicks);
      if (m.wave % 2 === 0) particle(b.dim, `${NS}:shockwave`, p, { "variable.radius": r });
      for (const pl of playersNear(b.dim, p, r + 1)) {
        const d = distXZ(p, pl.location);
        const grounded = pl.isOnGround !== false && pl.location.y <= p.y + 1.2;
        if (d >= r - 1.2 && d <= r + 0.4 && grounded) {
          strike(b.e, pl, m.hits, c.waveDamage, { h: 1.0, v: 0.7 }, p, 4);
        }
      }
      m.wave++;
    }
    if (m.t === sec(tImpact + 0.4)) b.setState("RECOVERY");
    return m.t >= sec(T.skullbreaker.length + c.extraRecovery);
  },
  end(b) {
    b.cooldown("skullbreaker", A.skullbreaker.cooldown);
    b.majorAttackDone();
  },
  // head is on the ground for a long time after the slam: a vulnerable window for the skull fracture
  vulnerable(m) {
    return m.t >= sec(T.skullbreaker.impact) && m.t <= sec(T.skullbreaker.length + A.skullbreaker.extraRecovery);
  },
};

// ===================================================================================== REPOSITION LEAP
export const repositionLeap = {
  name: "reposition_leap",
  interruptible: true,
  start(b, m) {
    b.anim("jump");
    b.setState("REPOSITION");
    // leap to the side away from the target's bearing, slightly backward
    const a = b.target ? relAngle(b.pos(), b.yaw, b.target.location) : 0;
    m.yaw = b.yaw + (a > 0 ? -110 : 110);
  },
  tick(b, m) {
    const leave = sec(T.jump.leave);
    const land = sec(T.jump.land);
    if (m.t >= leave && m.t < land) {
      const k = (m.t - leave) / (land - leave);
      const res = b.step(A.reposition_leap.distance / (land - leave), m.yaw, { maxDrop: 3, hop: Math.sin(k * Math.PI) * 1.6 });
      if (res.blocked) m.t = land; // cut short against walls
    }
    if (m.t === land) {
      b.settle();
      particle(b.dim, `${NS}:dust_ring`, b.pos());
      sound(b.dim, "mob.ravager.step", b.pos(), 3, 0.6);
    }
    if (m.t > land && b.target) b.face(b.target.location, 8);
    return m.t >= sec(T.jump.length + 0.2);
  },
  end(b) {
    b.cooldown("reposition_leap", A.reposition_leap.cooldown);
  },
};

// ===================================================================================== REACTIONS
export const chargeImpact = {
  name: "charge_impact",
  interruptible: false,
  vulnerableAll: true,
  start(b, m) {
    b.anim("charge_impact");
    b.setState("STAGGERED");
    b.addSkull(A.crushing_charge.skullDamageOnWall, "wall");
    particle(b.dim, `${NS}:daze_stars`, b.headPoint());
  },
  tick(b, m) {
    const L = sec(T.charge_impact.length);
    const S = sec(T.stagger.length);
    if (m.t === L) sound(b.dim, "mob.ravager.stun", b.pos(), 2, 0.7);
    if (m.t >= L && (m.t - L) % S === 0) b.anim("stagger");
    if (m.t > L && (m.t - L) % S === S - 2) b.anim("none"); // 2-tick gap so a long stun replays the stagger
    const stun = CONFIG.skull.impactStun[b.skull];
    if (m.t % 20 === 0) particle(b.dim, `${NS}:daze_stars`, b.headPoint());
    return m.t >= sec(T.charge_impact.length + stun);
  },
  end(b) {
    b.majorAttackDone();
  },
};

export const skullFracture = {
  name: "skull_fracture",
  interruptible: false,
  vulnerableAll: true,
  start(b, m) {
    b.anim("skull_fracture");
    b.setState("STAGGERED");
    const h = b.headPoint();
    particle(b.dim, `${NS}:skull_shards`, h);
    particle(b.dim, `${NS}:impact_burst`, h);
    sound(b.dim, "mob.irongolem.crack", h, 3, 0.6);
    sound(b.dim, "mob.ravager.roar", h, 3, 1.4);
    shake(b.viewers(24), 0.35, 0.6);
  },
  tick(b, m) {
    return m.t >= sec(T.skull_fracture.length + 0.3);
  },
};

export const exhausted = {
  name: "exhausted",
  interruptible: true,
  vulnerableAll: true,
  start(b, m) {
    b.anim("exhausted");
    b.setState("RECOVERY");
    m.len = sec(CONFIG.skull.exhaustSeconds[b.phase - 1]);
    sound(b.dim, "mob.ravager.ambient", b.mouth(), 2, 0.5);
  },
  tick(b, m) {
    if (m.t % 30 === 0) sound(b.dim, "mob.ravager.ambient", b.mouth(), 1.2, 0.45);
    return m.t >= m.len;
  },
};

export const MOVES = { roar, headScan, twinClaw, crushingCharge, rudderSweep, wingPressure, cliffDive, skullbreaker,
  repositionLeap, chargeImpact, skullFracture, exhausted };
export const ATTACKS = ["twin_claw", "crushing_charge", "rudder_sweep", "wing_pressure", "cliff_dive", "skullbreaker"];
export const BY_NAME = Object.fromEntries(Object.values(MOVES).map((mv) => [mv.name, mv]));
