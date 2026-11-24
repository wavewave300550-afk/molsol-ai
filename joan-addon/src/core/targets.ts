import { Dimension, Entity, EntityDamageCause, GameMode, Player, Vector3 } from "@minecraft/server";
import { JOAN, MINIONS, PROJECTILES, UNTOUCHABLE, difficultyScale } from "../config.js";
import { dist, flatDir, V3 } from "./vec.js";

export function isPlayer(e: Entity): e is Player {
  return e.typeId === "minecraft:player";
}

export function isFighter(p: Player): boolean {
  if (!p.isValid) return false;
  try {
    const gm = p.getGameMode();
    return gm !== GameMode.Creative && gm !== GameMode.Spectator;
  } catch {
    return false;
  }
}

export function isJoanSide(e: Entity): boolean {
  return e.typeId === JOAN || MINIONS.includes(e.typeId);
}

/** Can Joan's attacks harm this entity? Players (survival/adventure) and any mob that is not hers. */
export function isFoe(e: Entity): boolean {
  if (!e.isValid) return false;
  if (isPlayer(e)) return isFighter(e);
  if (isJoanSide(e) || UNTOUCHABLE.has(e.typeId) || PROJECTILES.has(e.typeId)) return false;
  return e.getComponent("minecraft:health") !== undefined;
}

export function fightersNear(dim: Dimension, at: Vector3, radius: number): Player[] {
  try {
    return dim.getPlayers({ location: at, maxDistance: radius }).filter(isFighter);
  } catch {
    return [];
  }
}

export function allPlayersNear(dim: Dimension, at: Vector3, radius: number): Player[] {
  try {
    return dim.getPlayers({ location: at, maxDistance: radius });
  } catch {
    return [];
  }
}

export function foesNear(dim: Dimension, at: Vector3, radius: number): Entity[] {
  try {
    return dim
      .getEntities({ location: at, maxDistance: radius, excludeTypes: [JOAN, ...MINIONS] })
      .filter(isFoe)
      .sort((a, b) => dist(a.location, at) - dist(b.location, at));
  } catch {
    return [];
  }
}

/** Damage scaled by world difficulty, credited to Joan so armour and kill messages work. */
export function hurt(target: Entity, amount: number, source: Entity | undefined, cause = EntityDamageCause.entityAttack): boolean {
  if (!target.isValid || amount <= 0) return false;
  const dmg = Math.max(0.5, amount * difficultyScale().damage);
  try {
    if (source && source.isValid) return target.applyDamage(dmg, { cause, damagingEntity: source });
    return target.applyDamage(dmg, { cause: EntityDamageCause.magic });
  } catch {
    return false;
  }
}

/** Push horizontally away from `from` (negative strength pulls) with an upward component. */
export function knockFrom(target: Entity, from: V3, strength: number, up: number): void {
  const d = flatDir(from, target.location);
  push(target, { x: d.x * strength, y: up, z: d.z * strength });
}

/** Velocity-style push that works for players (knockback) and everything else (impulse). */
export function push(target: Entity, vel: V3): void {
  if (!target.isValid) return;
  try {
    if (isPlayer(target)) target.applyKnockback({ x: vel.x, z: vel.z }, vel.y);
    else {
      target.clearVelocity();
      target.applyImpulse(vel);
    }
  } catch {
    // some entities refuse impulses
  }
}

export function burn(target: Entity, seconds: number): void {
  try {
    target.setOnFire(seconds, true);
  } catch {
    // ignore
  }
}
