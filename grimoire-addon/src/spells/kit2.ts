// Shared helpers for the expansion 02 grimoires (Plasma, Darkness, Prism Light).
// Infrastructure only: every spell builds its own visuals and behaviour on top of these.
import { Entity, EntityDamageCause, EntityProjectileComponent, Player, system } from "@minecraft/server";
import type { Cast } from "./context";
import type { Routine } from "../core/tasks";
import { COLORS, Fx, Rgb } from "../core/fx";
import { bodyCenter, isAllyOrSelf, livingNear } from "../core/combat";
import { V3, add, dist, flatNorm, len, mul, norm, sub, v3 } from "../core/vec";
import { isPassable } from "./kit";

export const SPECTRUM: Rgb[] = [
  COLORS.sp_red,
  COLORS.sp_orange,
  COLORS.sp_yellow,
  COLORS.sp_green,
  COLORS.sp_blue,
  COLORS.sp_indigo,
  COLORS.sp_violet,
];

export interface Incoming {
  e: Entity;
  proj: EntityProjectileComponent;
  vel: V3;
}

/** Projectiles near `center` that were not fired by the caster or an ally (supported: projectile component). */
export function hostileProjectiles(c: Cast, center: V3, radius: number, skip?: Set<string>): Incoming[] {
  const out: Incoming[] = [];
  let list: Entity[] = [];
  try {
    list = c.dim.getEntities({ location: center, maxDistance: radius });
  } catch {
    return out;
  }
  for (const e of list) {
    if (skip?.has(e.id)) continue;
    let proj: EntityProjectileComponent | undefined;
    try {
      proj = e.getComponent(EntityProjectileComponent.componentId) as EntityProjectileComponent | undefined;
    } catch {
      continue;
    }
    if (!proj) continue;
    const owner = proj.owner;
    if (owner && (owner.id === c.player.id || isAllyOrSelf(c.player, owner))) continue;
    out.push({ e, proj, vel: e.getVelocity() });
  }
  return out;
}

/** Give a projectile a new direction at (scaled) speed; optionally claim it so it cannot hurt the caster. */
export function redirect(inc: Incoming, dir: V3, speedMul = 1, claim?: Player): boolean {
  try {
    const speed = Math.max(0.5, len(inc.vel)) * speedMul;
    inc.e.clearVelocity();
    inc.e.applyImpulse(mul(norm(dir), speed));
    if (claim) inc.proj.owner = claim;
    return true;
  } catch {
    return false;
  }
}

/** Stop a projectile dead (it drops or despawns on its own). */
export function neutralize(inc: Incoming): void {
  try {
    inc.e.clearVelocity();
    inc.e.remove();
  } catch {
    /* some projectiles refuse */
  }
}

/** Invisible lure entity: hostile mobs that are struck by it turn on it (vanilla hurt_by_target). */
export function spawnDecoy(c: Cast, at: V3): Fx | undefined {
  return c.fx("grimoire:decoy", at, {});
}

/**
 * Redirect a mob's targeting toward the decoy: the decoy "strikes" it for 1 damage, so vanilla
 * hurt_by_target picks the decoy as its target. Players are never lured (they get blindness instead).
 */
export function lure(mob: Entity, decoy: Fx | undefined): void {
  if (!decoy?.ok || !mob.isValid || mob.typeId === "minecraft:player") return;
  try {
    mob.applyDamage(1, { cause: EntityDamageCause.entityAttack, damagingEntity: decoy.entity });
  } catch {
    /* immune */
  }
}

/** Allies (incl. the caster and their summons) near a point. */
export function alliesNear(c: Cast, center: V3, radius: number): Entity[] {
  return livingNear(c.dim, center, radius).filter((e) => e.id === c.player.id || isAllyOrSelf(c.player, e));
}

const NEGATIVE = ["poison", "wither", "slowness", "weakness", "blindness", "nausea", "mining_fatigue", "hunger", "darkness", "levitation"];

/** Heal and cleanse an ally (Whitepoint Benediction). Returns HP actually restored. */
export function healAndCleanse(e: Entity, amount: number, cleanse: boolean): number {
  let restored = 0;
  try {
    const hp = e.getComponent("minecraft:health") as { currentValue: number; effectiveMax: number; setCurrentValue(v: number): boolean } | undefined;
    if (hp && hp.currentValue > 0) {
      const next = Math.min(hp.effectiveMax, hp.currentValue + amount);
      restored = next - hp.currentValue;
      if (restored > 0) hp.setCurrentValue(next);
    }
  } catch {
    /* no health */
  }
  if (cleanse) {
    for (const id of NEGATIVE) {
      try {
        e.removeEffect(id);
      } catch {
        /* not present */
      }
    }
  }
  return restored;
}

/**
 * Walk a route along the ground in `dir` (flattened): steps up at most `stepUp` blocks and down at most
 * `stepDown`, stops at walls. Every returned point is a safe standing position (feet + head passable).
 */
export function surfaceRoute(c: Cast, from: V3, dir: V3, maxDist: number, step = 0.5, stepUp = 1, stepDown = 3): V3[] {
  const f = flatNorm(dir);
  const pts: V3[] = [];
  let cur = { x: from.x, y: Math.floor(from.y), z: from.z };
  for (let d = step; d <= maxDist; d += step) {
    const nx = from.x + f.x * d;
    const nz = from.z + f.z * d;
    let found: V3 | undefined;
    for (let dy = stepUp; dy >= -stepDown; dy--) {
      const feet = { x: nx, y: cur.y + dy, z: nz };
      const below = { x: nx, y: cur.y + dy - 1, z: nz };
      if (isPassable(c.dim, feet) && isPassable(c.dim, add(feet, v3(0, 1, 0))) && !isPassable(c.dim, below)) {
        found = feet;
        break;
      }
    }
    if (!found) break;
    // no tunnelling: the straight step itself must be clear at head height
    if (!isPassable(c.dim, { x: nx, y: Math.max(found.y, cur.y) + 1, z: nz })) break;
    cur = found;
    pts.push(found);
  }
  return pts;
}

/** Clear straight segment for a body (feet and head passable every half block). */
export function segmentClear(c: Cast, a: V3, b: V3): boolean {
  const d = dist(a, b);
  const n = Math.max(1, Math.ceil(d * 2));
  for (let i = 1; i <= n; i++) {
    const p = add(a, mul(sub(b, a), i / n));
    if (!isPassable(c.dim, p) || !isPassable(c.dim, add(p, v3(0, 1, 0)))) return false;
  }
  return true;
}

/** Wait helper usable inside spells: yields until `ticks` passed or `stop()` returns true. */
export function* until(ticks: number, stop: () => boolean): Routine {
  for (let t = 0; t < ticks; t++) {
    if (stop()) return;
    yield 1;
  }
}

/** Points along a quadratic/curved path (for ribbons, streams). */
export function arcPoint(a: V3, ctrl: V3, b: V3, t: number): V3 {
  const u = 1 - t;
  return { x: u * u * a.x + 2 * u * t * ctrl.x + t * t * b.x, y: u * u * a.y + 2 * u * t * ctrl.y + t * t * b.y, z: u * u * a.z + 2 * u * t * ctrl.z + t * t * b.z };
}

export function centerOf(e: Entity): V3 {
  return bodyCenter(e);
}

export function now(): number {
  return system.currentTick;
}
