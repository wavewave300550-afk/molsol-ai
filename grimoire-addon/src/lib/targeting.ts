import { Dimension, Entity, Player, Vector3 } from "@minecraft/server";
import { CONFIG } from "../config/global";
import { add, dist, mul, norm, yawOf, flat, fromYaw } from "./vec";

const NEVER = ["minecraft:item", "minecraft:xp_orb", "minecraft:arrow", "minecraft:armor_stand", "minecraft:painting",
  "minecraft:leash_knot", "minecraft:fishing_hook", "minecraft:lightning_bolt", "minecraft:npc"];

export function isAlive(e: Entity | undefined): e is Entity {
  if (!e || !e.isValid) return false;
  try {
    const h = e.getComponent("minecraft:health");
    return h === undefined || h.currentValue > 0;
  } catch {
    return false;
  }
}

/** True for entities spells are allowed to hurt on behalf of `caster`. */
export function isHostile(e: Entity, caster: Player): boolean {
  if (!isAlive(e) || e.id === caster.id) return false;
  try {
    if (e.matches({ families: ["grimoire_construct"] })) return false;
    if (e.typeId === "minecraft:player") return CONFIG.targeting.pvp;
    if (e.hasTag(CONFIG.targeting.testTag)) return true;
    for (const f of CONFIG.targeting.hostileFamilies) if (e.matches({ families: [f] })) return true;
  } catch { /* entity vanished mid-check */ }
  return false;
}

/** Hostile entities within radius of center, nearest first. */
export function hostiles(dim: Dimension, center: Vector3, radius: number, caster: Player,
  max: number = CONFIG.targeting.maxTargets): Entity[] {
  let found: Entity[] = [];
  try {
    found = dim.getEntities({ location: center, maxDistance: radius, excludeTypes: NEVER, excludeFamilies: ["grimoire_construct"] });
  } catch {
    return [];
  }
  const out = found.filter((e) => isHostile(e, caster));
  out.sort((a, b) => dist(a.location, center) - dist(b.location, center));
  return out.slice(0, max);
}

/** Players the caster's support magic applies to (always includes the caster when in range). */
export function allies(dim: Dimension, center: Vector3, radius: number, caster: Player): Player[] {
  if (CONFIG.targeting.pvp) return caster.isValid && dist(caster.location, center) <= radius ? [caster] : [];
  try {
    return dim.getPlayers({ location: center, maxDistance: radius }).filter((p) => isAlive(p));
  } catch {
    return [];
  }
}

/**
 * Standing surface for a point: if the point is inside terrain (aimed at a wall or a slope) it first
 * climbs out, then drops to the first solid block below.  Falls back to the point itself.
 */
export function groundBelow(dim: Dimension, loc: Vector3, maxDrop = 40): Vector3 {
  try {
    let y = loc.y;
    for (let i = 0; i < 24; i++) {
      const b = dim.getBlock({ x: loc.x, y: y + 0.01, z: loc.z });
      if (!b || b.isAir || b.isLiquid) break;
      y = Math.floor(y) + 1;
    }
    const hit = dim.getBlockFromRay({ x: loc.x, y: y + 1.5, z: loc.z }, { x: 0, y: -1, z: 0 },
      { maxDistance: maxDrop + 2, includePassableBlocks: false, includeLiquidBlocks: true });
    if (hit) return { x: loc.x, y: hit.block.location.y + 1, z: loc.z };
  } catch { /* unloaded */ }
  return { x: loc.x, y: loc.y, z: loc.z };
}

export interface Aim {
  /** Where the caster is pointing (entity position, block surface, or a point along the view ray). */
  point: Vector3;
  /** Ground position under `point`. */
  ground: Vector3;
  /** Hostile entity directly under the crosshair, if any. */
  entity?: Entity;
  /** Unit view direction and its horizontal projection. */
  dir: Vector3;
  forward: Vector3;
  /** Minecraft yaw of the caster's facing. */
  yaw: number;
  /** Caster feet position at cast time. */
  from: Vector3;
}

export function takeAim(caster: Player, range: number = CONFIG.targeting.aimRange): Aim {
  const dir = caster.getViewDirection();
  const head = caster.getHeadLocation();
  const dim = caster.dimension;
  let point: Vector3 | undefined;
  let entity: Entity | undefined;
  try {
    for (const h of caster.getEntitiesFromViewDirection({ maxDistance: range, excludeFamilies: ["grimoire_construct"] })) {
      if (isHostile(h.entity, caster)) { entity = h.entity; point = { ...h.entity.location }; break; }
    }
  } catch { /* ignore */ }
  if (!point) {
    try {
      const b = caster.getBlockFromViewDirection({ maxDistance: range, includePassableBlocks: false });
      if (b) {
        // step back out of the surface that was hit, so the point is in open air in front of it
        point = { x: b.block.location.x + b.faceLocation.x - dir.x * 0.6, y: b.block.location.y + b.faceLocation.y - dir.y * 0.6,
          z: b.block.location.z + b.faceLocation.z - dir.z * 0.6 };
      }
    } catch { /* ignore */ }
  }
  if (!point) point = add(head, mul(dir, range * 0.55));
  // facing comes from the body yaw so it stays defined when looking straight up or down
  let forward = norm(flat(dir));
  try { forward = fromYaw(caster.getRotation().y); } catch { /* keep view-based */ }
  const feet = caster.location;
  const minD = CONFIG.targeting.minAimDistance;
  if (!entity && Math.hypot(point.x - feet.x, point.z - feet.z) < minD) {
    point = { x: feet.x + forward.x * minD, y: feet.y + 1, z: feet.z + forward.z * minD };
  }
  return { point, ground: groundBelow(dim, point), entity, dir, forward, yaw: yawOf(forward), from: { ...caster.location } };
}

/**
 * Pick the fight location for an area spell: the aimed hostile, else the nearest hostile
 * to the aim point within `snap`, else the aimed ground point.
 */
export function focus(caster: Player, aim: Aim, snap = 10): { center: Vector3; target?: Entity } {
  if (aim.entity && isAlive(aim.entity)) return { center: groundBelow(caster.dimension, aim.entity.location), target: aim.entity };
  const near = hostiles(caster.dimension, aim.ground, snap, caster, 1);
  if (near.length) return { center: groundBelow(caster.dimension, near[0].location), target: near[0] };
  return { center: aim.ground };
}
