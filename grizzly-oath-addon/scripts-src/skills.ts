// Frontier Cleave (basic attack) and the four special skills.
import { Dimension, Entity, Player, system, Vector3 } from "@minecraft/server";
import { awaken, restore } from "./awaken.js";
import { addBleed, bodyCenter, enemiesNear, hurt, push, spawnFx } from "./combat.js";
import { ANIM, OATH_GRIZZLY_ID, SHADE_ID, SKILLS, TUNING } from "./config.js";
import { BLACK, DEEP_RED, HOT, RED, clawFlash, clawStreak, ember, glow, ring, shard, slash, smoke, sound, spark } from "./fx.js";
import { PlayerState, now, state } from "./state.js";
import { add, cross, dist, distToSegment, flat, lerp, mul, norm, rightOf, rotY, up, v } from "./vec.js";

export function playAnim(p: Player, name: string, blendOut = 0.15): void {
  try {
    p.playAnimation(name, { blendOutTime: blendOut });
  } catch {
    // animation unavailable: gameplay still works
  }
}

function later(ticks: number, fn: () => void): void {
  system.runTimeout(() => {
    try {
      fn();
    } catch (e) {
      console.warn(`[Grizzly's Oath] ${e}`);
    }
  }, ticks);
}

/** Free distance along a ray before the first solid block (skills never pass through walls). */
function clearDistance(dim: Dimension, from: Vector3, dir: Vector3, max: number): number {
  try {
    const hit = dim.getBlockFromRay(from, dir, { maxDistance: max, includeLiquidBlocks: false, includePassableBlocks: false });
    if (!hit) return max;
    return Math.max(0, dist(from, add(hit.block.location, hit.faceLocation)) - 0.3);
  } catch {
    return max;
  }
}

function shake(p: Player, intensity: number, seconds: number, radius: number): void {
  try {
    p.runCommand(`camerashake add @a[r=${radius}] ${intensity} ${seconds} positional`);
  } catch {
    // commands unavailable: purely cosmetic
  }
}

function heal(p: Player, amount: number): void {
  try {
    const h = p.getComponent("minecraft:health");
    if (h) h.setCurrentValue(Math.min(h.effectiveMax, h.currentValue + amount));
  } catch {
    // ignore
  }
}

export function healthRatio(p: Player): number {
  try {
    const h = p.getComponent("minecraft:health");
    if (h && h.effectiveMax > 0) return Math.max(0, Math.min(1, h.currentValue / h.effectiveMax));
  } catch {
    // ignore
  }
  return 1;
}

// ============================================================ basic attack: Frontier Cleave

/** Heavy alternating slash with a red arc in the aimed direction (every attack swing). */
export function frontierCleave(p: Player): void {
  const st = state(p);
  st.parity ^= 1;
  const fromRight = st.parity === 1;
  playAnim(p, fromRight ? ANIM.cleaveRight : ANIM.cleaveLeft, 0.1);

  const dim = p.dimension;
  const eye = p.getHeadLocation();
  const d = p.getViewDirection();
  const r = rightOf(d);
  const u = norm(cross(r, d)); // screen-space up
  const c = add(eye, mul(d, 1.9));
  slash(dim, c, 0.85, fromRight ? 35 : 145, RED);
  // energy trail following the blade: upper-right -> lower-left, or the mirror
  for (let k = 0; k <= 5; k++) {
    const t = k / 5;
    const x = fromRight ? 1 - 2 * t : -1 + 2 * t;
    const y = 0.8 - 1.6 * t;
    const bulge = Math.sin(Math.PI * t) * 0.35;
    const pos = add(add(add(c, mul(r, x * 0.95)), mul(u, y * 0.75)), mul(d, bulge));
    glow(dim, pos, 0.13, 0.22, k % 2 ? HOT : RED);
  }
  sound(dim, "grizzly_oath.cleave_swing", eye, 0.6, 1);
}

/** Impact of a Frontier Cleave that connected. */
export function cleaveImpact(p: Player, target: Entity): void {
  const dim = target.dimension;
  const at = bodyCenter(target);
  spark(dim, at);
  slash(dim, at, 0.8, Math.random() * 360, HOT);
  glow(dim, at, 0.55, 0.14, RED);
  sound(dim, "grizzly_oath.cleave_hit", at, 0.9, 0.95 + Math.random() * 0.15);
  sound(dim, "game.player.attack.strong", at, 0.8, 0.8);
}

// ============================================================ skill 1: Grizzly Rend

function grizzlyRend(p: Player): void {
  const T = TUNING.rend;
  const dim = p.dimension;
  const view = p.getViewDirection();
  const dir = norm(v(view.x, Math.max(-0.45, Math.min(0.45, view.y)), view.z));
  const right = rightOf(view);
  const origin = up(p.location, 0.9);

  playAnim(p, ANIM.rend);
  sound(dim, "grizzly_oath.rend", origin, 1, 1);
  sound(dim, "grizzly_oath.growl", origin, 0.9, 1);
  clawFlash(dim, add(p.getHeadLocation(), mul(view, 2.2)), 0.8, 0, RED);

  const lines = [-1, 0, 1].map((i) => {
    const ldir = rotY(dir, i * T.fanDegrees);
    const start = add(add(origin, mul(right, i * T.lateral)), mul(ldir, 0.6));
    return { start, dir: ldir, max: clearDistance(dim, start, ldir, T.range) };
  });
  const hit = new Set<string>();
  const steps = Math.ceil(T.range / T.blocksPerTick);
  for (let t = 0; t < steps; t++) {
    later(t + 1, () => {
      if (!p.isValid) return;
      for (const L of lines) {
        const a = t * T.blocksPerTick;
        const b = Math.min((t + 1) * T.blocksPerTick, L.max);
        if (a >= L.max) continue;
        for (let s = a; s < b; s += 0.7) clawStreak(dim, add(L.start, mul(L.dir, s)), L.dir, RED, 0.45);
        const head = add(L.start, mul(L.dir, b));
        glow(dim, head, 0.35, 0.2, HOT);
        const segA = add(L.start, mul(L.dir, a));
        for (const e of enemiesNear(p, lerp(segA, head, 0.5), (b - a) / 2 + 2)) {
          if (hit.has(e.id)) continue;
          const c = bodyCenter(e);
          if (distToSegment(c, segA, head) > T.hitRadius) continue;
          hit.add(e.id);
          hurt(p, e, T.damage);
          addBleed(p, e);
          push(e, p.location, 0.35, 0.15);
          spark(dim, c);
          clawFlash(dim, c, 0.6, Math.random() * 360, RED);
        }
      }
    });
  }
}

// ============================================================ skill 2: Relentless Pursuit

function relentlessPursuit(p: Player): void {
  const T = TUNING.pursuit;
  const dim = p.dimension;
  const fwd = flat(p.getViewDirection());
  const right = rightOf(fwd);
  const start = p.location;
  const free = Math.min(clearDistance(dim, up(start, 0.3), fwd, T.distance + 0.6), clearDistance(dim, up(start, 1.5), fwd, T.distance + 0.6));
  const distance = Math.max(0, Math.min(T.distance, free - 0.4));

  playAnim(p, ANIM.pursuit);
  sound(dim, "grizzly_oath.dash", start, 1, 1);
  let prev = start;
  for (let i = 1; i <= T.dashTicks; i++) {
    later(i, () => {
      if (!p.isValid) return;
      const pos = add(start, mul(fwd, (distance * i) / T.dashTicks));
      try {
        p.teleport(pos, { keepVelocity: false });
      } catch {
        // ignore
      }
      for (let s = 0; s < 1; s += 0.34) {
        const pt = up(lerp(prev, pos, s), 1.0);
        glow(dim, pt, 0.3, 0.35, RED);
        smoke(dim, up(pt, -0.3), 0.45, BLACK);
        clawStreak(dim, add(pt, mul(right, 0.45)), fwd, DEEP_RED, 0.35);
        clawStreak(dim, add(pt, mul(right, -0.45)), fwd, BLACK, 0.35);
      }
      prev = pos;
    });
  }
  later(T.dashTicks + T.slamDelay, () => {
    if (!p.isValid) return;
    try {
      p.clearVelocity();
    } catch {
      // ignore
    }
    const here = p.location;
    const c = add(here, mul(fwd, 1.4));
    for (const e of enemiesNear(p, c, T.slamRadius)) {
      hurt(p, e, T.damage);
      spark(dim, bodyCenter(e));
    }
    for (const e of enemiesNear(p, here, T.waveRadius)) push(e, here, T.knockback, T.lift);
    ring(dim, up(add(here, mul(fwd, 0.8)), 0.15), T.waveRadius, 0.35, RED);
    later(2, () => ring(dim, up(here, 0.12), T.waveRadius * 0.7, 0.3, DEEP_RED));
    shard(dim, up(c, 0.2));
    spark(dim, up(c, 0.5));
    slash(dim, up(c, 1.0), 1.6, 90, RED);
    glow(dim, up(c, 0.4), 1.2, 0.18, HOT);
    sound(dim, "grizzly_oath.heavy_slam", c, 1, 1);
    sound(dim, "grizzly_oath.shockwave", c, 0.45, 1.1);
    shake(p, 0.35, 0.35, 12);
  });
}

// ============================================================ skill 3: Unbroken Will

function unbrokenWill(p: Player, st: PlayerState): void {
  const T = TUNING.will;
  const dim = p.dimension;
  const t = now();
  const fwd = flat(p.getViewDirection());
  const yaw = p.getRotation().y;

  playAnim(p, ANIM.will);
  sound(dim, "grizzly_oath.roar", p.location, 1, 1);
  sound(dim, "grizzly_oath.heartbeat", p.location, 1, 1);
  spawnFx(p, SHADE_ID, add(p.location, mul(fwd, -1.8)), yaw, T.shadeTicks);
  ring(dim, up(p.location, 0.1), 2.6, 0.45, DEEP_RED);
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2;
    const at = add(p.location, v(Math.cos(a) * 0.9, 0.3, Math.sin(a) * 0.9));
    smoke(dim, at, 0.7, BLACK);
    ember(dim, at);
  }
  // Instant mending scales with how close to death the survivor is.
  heal(p, 2 + Math.round(6 * (1 - healthRatio(p))));
  st.willUntil = t + T.durationTicks;
  st.nextPulse = t;
}

export function willTier(ratio: number): number {
  return ratio > 0.6 ? 1 : ratio > 0.3 ? 2 : 3;
}

/** Runs every tick for players with Unbroken Will active. */
export function tickWill(p: Player, st: PlayerState, t: number): void {
  if (st.willUntil <= t) {
    st.willTier = 0;
    return;
  }
  const dim = p.dimension;
  if (t % 2 === 0) {
    const a = Math.random() * Math.PI * 2;
    const h = 0.2 + Math.random() * 1.4;
    const at = add(p.location, v(Math.cos(a) * 0.65, h, Math.sin(a) * 0.65));
    ember(dim, at);
    if (t % 4 === 0) smoke(dim, at, 0.35, BLACK);
  }
  if (t >= st.nextPulse) {
    st.nextPulse = t + TUNING.will.pulseTicks;
    const tier = willTier(healthRatio(p));
    st.willTier = tier;
    const duration = Math.max(1, Math.min(30, st.willUntil - t));
    try {
      p.addEffect("resistance", duration, { amplifier: tier - 1, showParticles: false });
    } catch {
      // ignore
    }
    heal(p, tier);
    ring(dim, up(p.location, 0.1), 1.1 + tier * 0.25, 0.3, tier === 3 ? RED : DEEP_RED);
    if (tier >= 2) sound(dim, "grizzly_oath.heartbeat", p.location, 0.5 + tier * 0.15, 1);
  }
}

// ============================================================ skill 4: Oath of the Grizzly

function oathOfTheGrizzly(p: Player, st: PlayerState): void {
  const T = TUNING.oath;
  const dim = p.dimension;
  const t0 = now();
  const fwd = flat(p.getViewDirection());
  const right = rightOf(fwd);
  const yaw = p.getRotation().y;
  st.ultUntil = t0 + T.awakenTicks;

  awaken(p);
  playAnim(p, ANIM.ult, 0.2);
  sound(dim, "grizzly_oath.charge", p.location, 1, 1);
  ring(dim, up(p.location, 0.1), 1.8, 0.6, RED);

  // the raised axe burns brighter until the slam
  for (let k = 0; k < T.slamTick; k += 3) {
    later(k, () => {
      if (!p.isValid) return;
      const axe = add(up(p.getHeadLocation(), 0.9), mul(right, 0.35));
      glow(dim, axe, 0.35 + k * 0.012, 0.22, RED, 0.5);
      ember(dim, axe);
      if (k % 9 === 0) {
        const a = Math.random() * Math.PI * 2;
        ember(dim, add(p.location, v(Math.cos(a) * 1.2, 0.2, Math.sin(a) * 1.2)));
      }
    });
  }

  let bearPos = add(p.location, mul(fwd, -3.2));
  later(T.spawnDelay, () => {
    if (!p.isValid) return;
    bearPos = add(p.location, mul(fwd, -3.2));
    spawnFx(p, OATH_GRIZZLY_ID, bearPos, yaw, T.grizzlyTicks);
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2;
      smoke(dim, add(bearPos, v(Math.cos(a) * 1.6, 0.4, Math.sin(a) * 1.6)), 1.3, BLACK);
    }
    shard(dim, up(bearPos, 0.2));
    ring(dim, up(bearPos, 0.1), 3.5, 0.5, DEEP_RED);
    sound(dim, "grizzly_oath.shockwave", bearPos, 0.4, 0.5);
  });

  later(T.roarTick, () => {
    if (!p.isValid) return;
    sound(dim, "grizzly_oath.titan_roar", bearPos, 1, 1);
    sound(dim, "grizzly_oath.roar", bearPos, 1, 0.8);
    sound(dim, "grizzly_oath.thunder", bearPos, 0.6, 1);
    shake(p, 0.25, 0.9, 20);
  });

  later(T.slamTick, () => {
    if (!p.isValid) return;
    const center = add(p.location, mul(fwd, 1.2));
    for (const e of enemiesNear(p, center, T.radius)) {
      const d = Math.min(1, dist(e.location, center) / T.radius);
      hurt(p, e, Math.round(T.maxDamage - (T.maxDamage - T.minDamage) * d));
      push(e, center, T.knockback * (1 - d * 0.75) + 0.6, T.lift);
      try {
        e.addEffect("slowness", 40, { amplifier: 1 });
      } catch {
        // ignore
      }
      spark(dim, bodyCenter(e));
    }
    const ground = up(center, 0.15);
    ring(dim, ground, T.radius, 0.55, RED);
    later(2, () => ring(dim, ground, T.radius * 0.6, 0.4, HOT));
    later(4, () => ring(dim, up(center, 0.1), T.radius + 0.5, 0.7, DEEP_RED));
    for (let k = 0; k < 10; k++) {
      const dir = rotY(fwd, k * 36);
      for (const s of [1.5, 3, 4.5, 6]) clawStreak(dim, add(ground, mul(dir, s)), dir, RED, 0.6);
    }
    for (let k = 0; k < 4; k++) shard(dim, up(add(center, mul(rotY(fwd, k * 90 + 45), 2.5)), 0.2));
    spark(dim, up(center, 0.5));
    glow(dim, up(center, 0.6), 2.4, 0.2, HOT);
    sound(dim, "grizzly_oath.shockwave", center, 1, 1);
    sound(dim, "grizzly_oath.heavy_slam", center, 1, 0.8);
    shake(p, 0.8, 0.6, 24);
  });

  later(T.awakenTicks, () => {
    if (p.isValid) restore(p);
  });
}

// ============================================================ casting

export function castSelected(p: Player): void {
  const st = state(p);
  const t = now();
  if (t < st.busyUntil) return;
  const def = SKILLS[st.skill];
  const left = st.readyAt[st.skill] - t;
  if (left > 0) {
    flash(st, `${def.color}${def.name} §7recharging §f${(left / 20).toFixed(1)}s`, 25);
    sound(p.dimension, "grizzly_oath.not_ready", p.location, 0.6, 1);
    return;
  }
  st.readyAt[st.skill] = t + def.cooldownTicks;
  st.busyUntil = t + def.busyTicks;
  switch (def.id) {
    case "rend":
      grizzlyRend(p);
      break;
    case "pursuit":
      relentlessPursuit(p);
      break;
    case "will":
      unbrokenWill(p, st);
      break;
    case "oath":
      oathOfTheGrizzly(p, st);
      break;
  }
}

export function flash(st: PlayerState, text: string, ticks: number): void {
  st.flashText = text;
  st.flashUntil = now() + ticks;
}
