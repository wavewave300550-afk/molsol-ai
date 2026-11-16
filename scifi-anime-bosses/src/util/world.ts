import {
  Difficulty,
  Dimension,
  Entity,
  EntityDamageCause,
  GameMode,
  Player,
  Vector3,
  world,
} from "@minecraft/server";
import { ENT } from "../generated/ids.js";
import { add, dist, hdist, mul, norm, segmentHitsCylinder, sub, V3 } from "./vec.js";

/** Players that can be targeted: alive, survival/adventure, same dimension, within range. */
export function combatants(dim: Dimension, center: Vector3, range: number): Player[] {
  const out: Player[] = [];
  let players: Player[] = [];
  try {
    players = dim.getPlayers({ location: center, maxDistance: range });
  } catch {
    return out;
  }
  for (const p of players) {
    if (!p.isValid) continue;
    let mode: GameMode | undefined;
    try {
      mode = p.getGameMode();
    } catch {
      continue;
    }
    if (mode === GameMode.Creative || mode === GameMode.Spectator) continue;
    const hp = p.getComponent("minecraft:health");
    if (!hp || hp.currentValue <= 0) continue;
    out.push(p);
  }
  return out;
}

/** All players nearby, any game mode (for music / fog / titles). */
export function spectators(dim: Dimension, center: Vector3, range: number): Player[] {
  try {
    return dim.getPlayers({ location: center, maxDistance: range }).filter((p) => p.isValid);
  } catch {
    return [];
  }
}

export function chest(p: Entity): Vector3 {
  const l = p.location;
  return { x: l.x, y: l.y + 0.9, z: l.z };
}

/** Highest solid block surface under (x, z); falls back to `fallback`. */
export function groundY(dim: Dimension, x: number, z: number, fallback: number, below?: number): number {
  try {
    if (below !== undefined) {
      const hit = dim.getBlockFromRay({ x, y: below, z }, { x: 0, y: -1, z: 0 },
        { maxDistance: 96, includeLiquidBlocks: true, includePassableBlocks: false });
      if (hit) return hit.block.location.y + 1;
    }
    const b = dim.getTopmostBlock({ x, z });
    if (b) return b.location.y + 1;
  } catch {
    /* unloaded chunk */
  }
  return fallback;
}

export interface Cover {
  location: Vector3;
  radius: number;
  height: number;
}

/** Line of sight from `from` to `to`: blocked by solid blocks or by any cover cylinder. */
export function hasLineOfSight(dim: Dimension, from: Vector3, to: Vector3, covers: Cover[] = [],
  onCoverHit?: (c: Cover) => void): boolean {
  const d = sub(to, from);
  const L = Math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z);
  if (L < 0.5) return true;
  for (const c of covers) {
    if (segmentHitsCylinder(from, to, c.location, c.radius, c.height)) {
      onCoverHit?.(c);
      return false;
    }
  }
  try {
    const hit = dim.getBlockFromRay(from, norm(d), { maxDistance: L - 0.6, includeLiquidBlocks: false,
      includePassableBlocks: false });
    if (hit) return false;
  } catch {
    /* unloaded: treat as visible */
  }
  return true;
}

/** Is there a non-passable block between a and b (exclusive of b's own cell)? */
export function blockedBetween(dim: Dimension, a: Vector3, b: Vector3): boolean {
  const d = sub(b, a);
  const L = Math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z);
  if (L < 1e-3) return false;
  try {
    return !!dim.getBlockFromRay(a, norm(d), { maxDistance: L, includeLiquidBlocks: false, includePassableBlocks: false });
  } catch {
    return true;
  }
}

export function difficultyScale(): number {
  try {
    switch (world.getDifficulty()) {
      case Difficulty.Easy: return 0.7;
      case Difficulty.Hard: return 1.3;
      case Difficulty.Peaceful: return 0.0;
      default: return 1.0;
    }
  } catch {
    return 1.0;
  }
}

export function isPeaceful(): boolean {
  try {
    return world.getDifficulty() === Difficulty.Peaceful;
  } catch {
    return false;
  }
}

/** Damage a player on behalf of the boss (difficulty scaled). */
export function hurt(target: Entity, amount: number, source: Entity | undefined,
  cause: EntityDamageCause = EntityDamageCause.entityAttack): boolean {
  if (!target.isValid) return false;
  const a = Math.max(0.5, amount * difficultyScale());
  try {
    if (source && source.isValid) return target.applyDamage(a, { cause, damagingEntity: source });
    return target.applyDamage(a, { cause });
  } catch {
    return false;
  }
}

/** Knock an entity away from `from` (players via applyKnockback, mobs via impulse). */
export function knock(target: Entity, from: Vector3, horizontal: number, vertical: number): void {
  const d = target.location;
  let dx = d.x - from.x;
  let dz = d.z - from.z;
  const l = Math.hypot(dx, dz) || 1;
  dx /= l;
  dz /= l;
  push(target, { x: dx * horizontal, y: vertical, z: dz * horizontal });
}

export function push(target: Entity, vel: Vector3): void {
  try {
    if (target.typeId === "minecraft:player") target.applyKnockback({ x: vel.x, z: vel.z }, vel.y);
    else target.applyImpulse(vel);
  } catch {
    /* some entities refuse impulses */
  }
}

export function safeRemove(e: Entity | undefined): void {
  try {
    if (e && e.isValid) e.remove();
  } catch {
    /* already gone */
  }
}

export function setProp(e: Entity, id: string, value: number | boolean | string): void {
  try {
    if (e.isValid) e.setProperty(id, value);
  } catch {
    /* ignore */
  }
}

/** Entities that may be harmed by area attacks (players + hostile/neutral mobs, never our own helpers). */
export function areaVictims(dim: Dimension, center: Vector3, radius: number): Entity[] {
  try {
    return dim.getEntities({ location: center, maxDistance: radius, excludeFamilies: ["sab_vesper", "inanimate"],
      excludeTypes: ["minecraft:item", "minecraft:xp_orb", ENT.halo] });
  } catch {
    return [];
  }
}

export function isPlayer(e: Entity | undefined): e is Player {
  return !!e && e.typeId === "minecraft:player";
}

export function within(a: Vector3, b: Vector3, r: number): boolean {
  return dist(a, b) <= r;
}

export function hwithin(a: Vector3, b: Vector3, r: number): boolean {
  return hdist(a, b) <= r;
}

export function above(p: V3, h: number): V3 {
  return add(p, { x: 0, y: h, z: 0 });
}

export function scaleVec(a: V3, s: number): V3 {
  return mul(a, s);
}
