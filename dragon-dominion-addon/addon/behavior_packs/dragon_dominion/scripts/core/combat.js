// Reusable combat rules: who can be hit, hit-once registries, damage + knockback, area tests.
import { EntityDamageCause, GameMode } from "@minecraft/server";
import { now, safe } from "./util.js";
import { distXZ, relAngle, yawTo, dirOf } from "./vec.js";

const lastHitTick = new Map(); // player id -> tick of the last boss hit (fairness guard)

/** Players a boss may target / damage: alive survival or adventure players in the same dimension. */
export function validTarget(p, dim) {
  if (!p || !safe(() => p.isValid, false)) return false;
  if (dim && safe(() => p.dimension.id) !== dim.id) return false;
  const gm = safe(() => p.getGameMode());
  if (gm !== GameMode.Survival && gm !== GameMode.Adventure) return false;
  const hp = safe(() => p.getComponent("minecraft:health")?.currentValue, 0);
  return hp > 0;
}

/** Valid players within r blocks of loc (engine-side distance filter, no global scans). */
export function playersNear(dim, loc, r) {
  return (safe(() => dim.getPlayers({ location: loc, maxDistance: r })) ?? []).filter((p) => validTarget(p, dim));
}

/** Every player (any game mode) near loc - used for HUD text and screen shake. */
export function viewersNear(dim, loc, r) {
  return safe(() => dim.getPlayers({ location: loc, maxDistance: r })) ?? [];
}

/** One attack instance: each target can be hit at most once by it. */
export class HitSet {
  constructor() {
    this.ids = new Set();
  }
  has(e) {
    return this.ids.has(e.id);
  }
  add(e) {
    this.ids.add(e.id);
  }
}

/**
 * Damage a player once for this HitSet, then knock them away from `from`.
 * `minGap` ticks: a player is never hit twice by the boss inside that window (stacked hitboxes / overlapping waves).
 */
export function strike(boss, p, hits, dmg, kb, from, minGap = 8) {
  if (hits.has(p) || !validTarget(p, boss.dimension)) return false;
  const t = now();
  const last = lastHitTick.get(p.id) ?? -999;
  if (t - last < minGap) return false;
  hits.add(p);
  lastHitTick.set(p.id, t);
  if (dmg > 0) safe(() => p.applyDamage(dmg, { cause: EntityDamageCause.entityAttack, damagingEntity: boss }));
  if (kb) knockAway(p, from, kb.h, kb.v);
  return true;
}

export function knockAway(p, from, h, v) {
  const loc = safe(() => p.location);
  if (!loc) return;
  let dx = loc.x - from.x;
  let dz = loc.z - from.z;
  const d = Math.hypot(dx, dz);
  if (d < 1e-3) {
    dx = 0;
    dz = 1;
  } else {
    dx /= d;
    dz /= d;
  }
  safe(() => p.applyKnockback({ x: dx * h, z: dz * h }, v));
}

/** Push along a direction (charges carry victims forward and sideways). */
export function knockDir(p, dir, h, v) {
  safe(() => p.applyKnockback({ x: dir.x * h, z: dir.z * h }, v));
}

/** In a horizontal cone in front of origin: range, half-angle (deg), optional centre offset angle. */
export function inCone(origin, yaw, p, range, half, offset = 0, minRange = 0) {
  const d = distXZ(origin, p);
  if (d > range || d < minRange) return false;
  const a = relAngle(origin, yaw + offset, p);
  return Math.abs(a) <= half;
}

/** Vertical overlap test against a band [y0, y1]. */
export const inBand = (p, y0, y1) => p.y >= y0 - 0.2 && p.y <= y1;

/** Distance from point p to segment a-b on the XZ plane. */
export function segDistXZ(p, a, b) {
  const vx = b.x - a.x;
  const vz = b.z - a.z;
  const l2 = vx * vx + vz * vz || 1e-9;
  let t = ((p.x - a.x) * vx + (p.z - a.z) * vz) / l2;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(p.x - (a.x + vx * t), p.z - (a.z + vz * t));
}

export { yawTo, dirOf };

/** Testing hook: forget the fairness window. */
export function __resetHitClock() {
  lastHitTick.clear();
}
