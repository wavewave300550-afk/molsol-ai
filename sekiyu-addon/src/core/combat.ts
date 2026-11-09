import { Dimension, Entity, EntityDamageCause, EntityHealthComponent, GameMode, Player, Vector3, world } from "@minecraft/server";
import { CONSTRUCT_FAMILY, PROTECTED_TYPES, WORLD_PVP } from "../config.js";
import { dist, dot, flat, flatDir, norm, sub } from "./vec.js";

export function pvpEnabled(): boolean {
  return world.getDynamicProperty(WORLD_PVP) === true;
}

/** Can `caster`'s petroleum harm entity `e`? */
export function isEnemy(e: Entity, caster: Player | undefined): boolean {
  if (!e.isValid || (caster && e.id === caster.id)) return false;
  if (PROTECTED_TYPES.has(e.typeId) || e.typeId.startsWith("sekiyu:")) return false;
  if (e instanceof Player) {
    if (!pvpEnabled()) return false;
    const gm = e.getGameMode();
    return gm !== GameMode.Creative && gm !== GameMode.Spectator;
  }
  if (!e.getComponent(EntityHealthComponent.componentId)) return false;
  if (e.getComponent("minecraft:is_tamed")) return false;
  return true;
}

export function enemiesNear(dim: Dimension, at: Vector3, radius: number, caster: Player | undefined, maxCount = 32): Entity[] {
  let found: Entity[] = [];
  try {
    found = dim.getEntities({ location: at, maxDistance: radius, excludeFamilies: ["inanimate", CONSTRUCT_FAMILY] });
  } catch {
    return [];
  }
  return found
    .filter((e) => isEnemy(e, caster))
    .sort((a, b) => dist(a.location, at) - dist(b.location, at))
    .slice(0, maxCount);
}

export function enemiesInCone(caster: Player, range: number, minDot: number): Entity[] {
  const origin = caster.location;
  const fwd = flat(caster.getViewDirection());
  return enemiesNear(caster.dimension, origin, range, caster).filter((e) => dot(flat(sub(e.location, origin)), fwd) >= minDot);
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

export function knockAlong(target: Entity, dir: Vector3, strength: number, vertical: number): void {
  if (!target.isValid) return;
  const d = flat(norm(dir));
  try {
    target.applyKnockback({ x: d.x * strength, z: d.z * strength }, vertical);
  } catch {
    // some entities refuse knockback
  }
}

export function knockFrom(target: Entity, from: Vector3, strength: number, vertical: number): void {
  knockAlong(target, flatDir(from, target.location), strength, vertical);
}

export function ignite(target: Entity, seconds: number): void {
  try {
    target.setOnFire(seconds, true);
  } catch {
    // fire immune
  }
}

/** Heavy crude: thick oil clinging to the target. */
export function oilSlow(target: Entity, ticks: number, amp: number): void {
  try {
    target.addEffect("slowness", ticks, { amplifier: amp, showParticles: false });
  } catch {
    // immune / dead
  }
}

export function enemyInSight(player: Player, reach: number): Entity | undefined {
  try {
    return player
      .getEntitiesFromViewDirection({ maxDistance: reach })
      .filter((h) => isEnemy(h.entity, player))
      .sort((a, b) => a.distance - b.distance)[0]?.entity;
  } catch {
    return undefined;
  }
}

export function onFire(e: Entity): boolean {
  try {
    const c = e.getComponent("minecraft:onfire");
    return !!c && c.onFireTicksRemaining > 0;
  } catch {
    return false;
  }
}
