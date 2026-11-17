import { Dimension, Entity, EntityDamageCause, EntityHealthComponent, GameMode, Player, Vector3, world } from "@minecraft/server";
import { PROTECTED_TYPES, WORLD_PVP } from "../config.js";
import { dist, dot, flat, flatDir, norm, sub } from "./vec.js";

export function pvpEnabled(): boolean {
  return world.getDynamicProperty(WORLD_PVP) === true;
}

/** Can `caster`'s steam abilities harm entity `e`? */
export function isEnemy(e: Entity, caster: Player): boolean {
  if (!e.isValid || e.id === caster.id) return false;
  if (PROTECTED_TYPES.has(e.typeId)) return false;
  if (e instanceof Player) {
    if (!pvpEnabled()) return false;
    const gm = e.getGameMode();
    return gm !== GameMode.Creative && gm !== GameMode.Spectator;
  }
  if (!e.getComponent(EntityHealthComponent.componentId)) return false;
  // Tamed pets (wolves, cats, parrots...) are left alone.
  if (e.getComponent("minecraft:is_tamed")) return false;
  return true;
}

export function enemiesNear(dim: Dimension, at: Vector3, radius: number, caster: Player, maxCount = 32): Entity[] {
  let found: Entity[] = [];
  try {
    found = dim.getEntities({ location: at, maxDistance: radius, excludeFamilies: ["inanimate"] });
  } catch {
    return [];
  }
  return found
    .filter((e) => isEnemy(e, caster))
    .sort((a, b) => dist(a.location, at) - dist(b.location, at))
    .slice(0, maxCount);
}

/** Enemies within `range` in front of the caster whose direction is within the cone (dot >= minDot). */
export function enemiesInCone(caster: Player, range: number, minDot: number): Entity[] {
  const origin = caster.location;
  const fwd = flat(caster.getViewDirection());
  return enemiesNear(caster.dimension, origin, range, caster).filter((e) => {
    const to = flat(sub(e.location, origin));
    return dist(e.location, origin) < 1.0 || dot(to, fwd) >= minDot;
  });
}

export function hurt(target: Entity, amount: number, caster: Player | undefined, cause = EntityDamageCause.entityAttack): boolean {
  if (!target.isValid || amount <= 0) return false;
  try {
    if (caster && caster.isValid) return target.applyDamage(amount, { cause, damagingEntity: caster });
    return target.applyDamage(amount, { cause: EntityDamageCause.magic });
  } catch {
    return false;
  }
}

/** Push `target` horizontally along `dir` (normalised here) with an upward kick. */
export function knockAlong(target: Entity, dir: Vector3, strength: number, vertical: number): void {
  if (!target.isValid) return;
  const d = flat(norm(dir));
  try {
    target.applyKnockback({ x: d.x * strength, z: d.z * strength }, vertical);
  } catch {
    // some entities refuse knockback
  }
}

/** Push `target` away from a point. */
export function knockFrom(target: Entity, from: Vector3, strength: number, vertical: number): void {
  if (!target.isValid) return;
  knockAlong(target, flatDir(from, target.location), strength, vertical);
}

/** Closest enemy along the player's crosshair within `reach`, or undefined. */
export function enemyInSight(player: Player, reach: number): Entity | undefined {
  try {
    const hits = player
      .getEntitiesFromViewDirection({ maxDistance: reach })
      .filter((h) => isEnemy(h.entity, player))
      .sort((a, b) => a.distance - b.distance);
    return hits[0]?.entity;
  } catch {
    return undefined;
  }
}
