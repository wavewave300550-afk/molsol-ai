import { Dimension, Entity, EntityDamageCause, EntityHealthComponent, GameMode, Player, Vector3 } from "@minecraft/server";
import { add, dist, scale, sub } from "./vec.js";

const IGNORED_FAMILIES = new Set(["dim11_being", "dim11_minion", "dim11_illusion", "inanimate"]);
const IGNORED_TYPES = new Set(["minecraft:item", "minecraft:xp_orb", "minecraft:armor_stand", "minecraft:arrow", "minecraft:painting"]);

export function isCombatPlayer(p: Player): boolean {
  if (!p.isValid) return false;
  const gm = p.getGameMode();
  return gm === GameMode.Survival || gm === GameMode.Adventure;
}

export function playersNear(dim: Dimension, at: Vector3, radius: number): Player[] {
  return dim.getPlayers({ location: at, maxDistance: radius }).filter(isCombatPlayer);
}

/** Anything a being may damage: combat players plus ordinary mobs (pets, golems, monsters). */
export function victimsNear(dim: Dimension, at: Vector3, radius: number): Entity[] {
  return dim.getEntities({ location: at, maxDistance: radius }).filter(isVictim);
}

export function isVictim(e: Entity): boolean {
  if (!e.isValid) return false;
  if (e instanceof Player) return isCombatPlayer(e);
  if (IGNORED_TYPES.has(e.typeId) || e.typeId.startsWith("dim11:")) return false;
  if (!e.getComponent(EntityHealthComponent.componentId)) return false;
  for (const f of IGNORED_FAMILIES) if (e.matches({ families: [f] })) return false;
  return true;
}

export function hurt(target: Entity, amount: number, source: Entity | undefined, cause = EntityDamageCause.entityAttack): boolean {
  if (!target.isValid || amount <= 0) return false;
  try {
    if (source && source.isValid) return target.applyDamage(amount, { cause, damagingEntity: source });
    return target.applyDamage(amount, { cause: EntityDamageCause.magic });
  } catch {
    return false;
  }
}

export function knock(target: Entity, from: Vector3, strength: number, vertical: number): void {
  if (!target.isValid) return;
  const dx = target.location.x - from.x;
  const dz = target.location.z - from.z;
  const l = Math.hypot(dx, dz) || 1;
  try {
    target.applyKnockback({ x: (dx / l) * strength, z: (dz / l) * strength }, vertical);
  } catch {
    // knockback-immune entity
  }
}

export function effect(target: Entity, id: string, ticks: number, amp = 0): void {
  try {
    target.addEffect(id, ticks, { amplifier: amp, showParticles: true });
  } catch {
    // immune
  }
}

export function chest(e: Entity): Vector3 {
  return { x: e.location.x, y: e.location.y + 1.0, z: e.location.z };
}

/** Where `e` will probably be in `ticks` ticks (linear prediction from current velocity). */
export function predict(e: Entity, ticks: number): Vector3 {
  try {
    const vel = e.getVelocity();
    const p = add(e.location, scale({ x: vel.x, y: 0, z: vel.z }, ticks));
    return p;
  } catch {
    return e.location;
  }
}

/** Distance from point p to segment ab. */
export function distToSegment(p: Vector3, a: Vector3, b: Vector3): number {
  const ab = sub(b, a);
  const L2 = ab.x * ab.x + ab.y * ab.y + ab.z * ab.z;
  if (L2 < 1e-6) return dist(p, a);
  let t = ((p.x - a.x) * ab.x + (p.y - a.y) * ab.y + (p.z - a.z) * ab.z) / L2;
  t = Math.max(0, Math.min(1, t));
  return dist(p, { x: a.x + ab.x * t, y: a.y + ab.y * t, z: a.z + ab.z * t });
}

/** Entities whose body (feet..head) passes within `width` of the segment. */
export function victimsOnLine(dim: Dimension, a: Vector3, b: Vector3, width: number): Entity[] {
  const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, z: (a.z + b.z) / 2 };
  const reach = dist(a, b) / 2 + width + 2;
  return victimsNear(dim, mid, reach).filter((e) => {
    const feet = e.location;
    const head = { x: feet.x, y: feet.y + 1.6, z: feet.z };
    return Math.min(distToSegment(feet, a, b), distToSegment(chest(e), a, b), distToSegment(head, a, b)) <= width;
  });
}

/** True when no solid block lies between the two points. */
export function lineOfSight(dim: Dimension, from: Vector3, to: Vector3): boolean {
  const d = sub(to, from);
  const L = Math.hypot(d.x, d.y, d.z);
  if (L < 0.5) return true;
  try {
    const hit = dim.getBlockFromRay(from, { x: d.x / L, y: d.y / L, z: d.z / L }, { maxDistance: L, includeLiquidBlocks: false, includePassableBlocks: false });
    return !hit;
  } catch {
    return true;
  }
}

export function healthOf(e: Entity): EntityHealthComponent | undefined {
  try {
    return e.getComponent(EntityHealthComponent.componentId);
  } catch {
    return undefined;
  }
}
