import {
  Dimension,
  Entity,
  EntityDamageCause,
  EntityHealthComponent,
  GameMode,
  Player,
  Vector3,
  world,
} from "@minecraft/server";
import { add, dist, flatDir, scale } from "./vec.js";

/** Entity types abilities never touch. */
const PROTECTED_TYPES = new Set<string>([
  "minecraft:item",
  "minecraft:xp_orb",
  "minecraft:armor_stand",
  "minecraft:villager",
  "minecraft:villager_v2",
  "minecraft:wandering_trader",
  "minecraft:iron_golem",
  "minecraft:snow_golem",
  "minecraft:allay",
  "minecraft:npc",
  "minecraft:agent",
  "minecraft:painting",
  "minecraft:leash_knot",
  "minecraft:ender_crystal",
]);

export const PVP_PROPERTY = "tribes:pvp";

export function pvpEnabled(): boolean {
  return world.getDynamicProperty(PVP_PROPERTY) === true;
}

export function isSummonOf(e: Entity, owner: Player): boolean {
  return e.getDynamicProperty("tribes:owner") === owner.id;
}

/** Can `caster`'s abilities harm entity `e`? */
export function isEnemy(e: Entity, caster: Player): boolean {
  if (!e.isValid || e.id === caster.id) return false;
  if (PROTECTED_TYPES.has(e.typeId)) return false;
  if (e.typeId.startsWith("tribes:")) return false;
  if (e instanceof Player) {
    if (!pvpEnabled()) return false;
    const gm = e.getGameMode();
    return gm !== GameMode.Creative && gm !== GameMode.Spectator;
  }
  if (!e.getComponent(EntityHealthComponent.componentId)) return false;
  if (e.getComponent("minecraft:is_tamed")) return false;
  return true;
}

export function isAlly(e: Entity, caster: Player): boolean {
  if (e.id === caster.id) return true;
  if (e instanceof Player) return !pvpEnabled() || e.getDynamicProperty("tribes:race") === caster.getDynamicProperty("tribes:race");
  return isSummonOf(e, caster);
}

export function enemiesNear(dim: Dimension, at: Vector3, radius: number, caster: Player, maxCount = 64): Entity[] {
  const found = dim.getEntities({ location: at, maxDistance: radius, excludeFamilies: ["inanimate"] });
  return found
    .filter((e) => isEnemy(e, caster))
    .sort((a, b) => dist(a.location, at) - dist(b.location, at))
    .slice(0, maxCount);
}

export function alliesNear(dim: Dimension, at: Vector3, radius: number, caster: Player): Player[] {
  return dim.getPlayers({ location: at, maxDistance: radius }).filter((p) => isAlly(p, caster));
}

export function hurt(target: Entity, amount: number, caster: Player | undefined, cause = EntityDamageCause.entityAttack): void {
  if (!target.isValid) return;
  try {
    if (caster && caster.isValid) target.applyDamage(amount, { cause, damagingEntity: caster });
    else target.applyDamage(amount, { cause: EntityDamageCause.magic });
  } catch {
    // entity cannot be damaged (e.g. creative player) - ignore
  }
}

/** Horizontal knock away from (or towards, with negative strength) a point. */
export function knockFrom(target: Entity, from: Vector3, strength: number, vertical: number): void {
  if (!target.isValid) return;
  const d = flatDir(from, target.location);
  try {
    target.applyKnockback({ x: d.x * strength, z: d.z * strength }, vertical);
  } catch {
    // some entities refuse knockback
  }
}

export function heal(target: Entity, amount: number): void {
  const h = target.getComponent(EntityHealthComponent.componentId);
  if (!h) return;
  h.setCurrentValue(Math.min(h.effectiveMax, h.currentValue + amount));
}

export interface AimResult {
  entity?: Entity;
  point: Vector3;
  distance: number;
}

/** Ray-cast from the player's eyes: the first enemy or block, whichever is closer. */
export function aim(player: Player, maxDistance: number): AimResult {
  const eye = player.getHeadLocation();
  const dir = player.getViewDirection();
  let best: AimResult = { point: add(eye, scale(dir, maxDistance)), distance: maxDistance };
  try {
    const blockHit = player.getBlockFromViewDirection({ maxDistance, includeLiquidBlocks: false, includePassableBlocks: false });
    if (blockHit) {
      const p = add(blockHit.block.location, blockHit.faceLocation);
      const d = dist(eye, p);
      if (d < best.distance) best = { point: p, distance: d };
    }
  } catch {
    // ray left the world
  }
  try {
    const hits = player
      .getEntitiesFromViewDirection({ maxDistance })
      .filter((h) => isEnemy(h.entity, player))
      .sort((a, b) => a.distance - b.distance);
    if (hits.length && hits[0].distance <= best.distance) {
      const e = hits[0].entity;
      best = { entity: e, point: { x: e.location.x, y: e.location.y + 0.9, z: e.location.z }, distance: hits[0].distance };
    }
  } catch {
    // ignore
  }
  return best;
}
