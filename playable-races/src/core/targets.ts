/** Target selection, filtering and spatial queries shared by every race. */
import { Block, Dimension, Entity, GameMode, Player, Vector3 } from "@minecraft/server";
import { PROTECTED_FAMILIES, PROTECTED_TYPES } from "../config.js";
import { pvpAllowed } from "./settings.js";
import { add, angleBetween, dist, mul, norm, sub, v3 } from "./util.js";

export function alive(e: Entity | undefined): e is Entity {
  if (!e || !e.isValid) return false;
  try {
    const h = e.getComponent("minecraft:health");
    return !!h && h.currentValue > 0;
  } catch {
    return false;
  }
}

function isPetOf(e: Entity): boolean {
  try {
    const t = e.getComponent("minecraft:tameable");
    if (t && t.isTamed) return true;
    const tm = e.getComponent("minecraft:is_tamed");
    if (tm) return true;
  } catch {
    /* ignore */
  }
  return false;
}

/** Can `caster`'s offensive ability affect `e`? */
export function hostileTo(caster: Player, e: Entity): boolean {
  if (!alive(e) || e.id === caster.id) return false;
  if (PROTECTED_TYPES.includes(e.typeId)) return false;
  try {
    const fam = e.getComponent("minecraft:type_family");
    if (fam && PROTECTED_FAMILIES.some((f) => fam.hasTypeFamily(f))) return false;
  } catch {
    /* ignore */
  }
  if (e instanceof Player || e.typeId === "minecraft:player") {
    if (!pvpAllowed()) return false;
    const gm = (e as Player).getGameMode();
    return gm === GameMode.Survival || gm === GameMode.Adventure;
  }
  if (isPetOf(e)) return false;
  return true;
}

/** Friendly players that support effects may target. */
export function ally(caster: Player, e: Entity): boolean {
  return e instanceof Player && e.id !== caster.id && !pvpAllowed();
}

export function eye(p: Entity): Vector3 {
  try {
    return p.getHeadLocation();
  } catch {
    return add(p.location, v3(0, 1.6, 0));
  }
}

export function chest(e: Entity): Vector3 {
  return add(e.location, v3(0, 0.9, 0));
}

/** Enemies in a sphere. */
export function enemiesNear(caster: Player, center: Vector3, radius: number, dim: Dimension = caster.dimension): Entity[] {
  let list: Entity[] = [];
  try {
    list = dim.getEntities({ location: center, maxDistance: radius, excludeTypes: PROTECTED_TYPES, excludeFamilies: PROTECTED_FAMILIES });
  } catch {
    return [];
  }
  return list.filter((e) => hostileTo(caster, e));
}

/** Enemies whose body is within `radius` of the segment a -> b (swept hit test for dashes). */
export function enemiesAlongSegment(caster: Player, a: Vector3, b: Vector3, radius: number): Entity[] {
  const mid = mul(add(a, b), 0.5);
  const half = dist(a, b) / 2;
  const ab = sub(b, a);
  const L2 = ab.x * ab.x + ab.y * ab.y + ab.z * ab.z;
  return enemiesNear(caster, mid, half + radius + 1.5).filter((e) => {
    const c = add(e.location, v3(0, 0.9, 0));
    let t = L2 > 1e-9 ? ((c.x - a.x) * ab.x + (c.y - a.y) * ab.y + (c.z - a.z) * ab.z) / L2 : 0;
    t = Math.max(0, Math.min(1, t));
    return dist(c, add(a, mul(ab, t))) <= radius;
  });
}

/** True when no solid block interrupts the segment a -> b. */
export function lineOfSight(dim: Dimension, a: Vector3, b: Vector3): boolean {
  const d = sub(b, a);
  const L = Math.hypot(d.x, d.y, d.z);
  if (L < 0.5) return true;
  try {
    const hit = dim.getBlockFromRay(a, norm(d), { maxDistance: L, includeLiquidBlocks: false, includePassableBlocks: false });
    return !hit;
  } catch {
    return true;
  }
}

/**
 * Best target in front of the caster: inside `range`, within `cone` degrees of the
 * view direction, in line of sight.  Aim-assisted (prefers small angles, then distance).
 */
export function aimTarget(p: Player, range: number, cone = 14, prefer?: (e: Entity) => boolean): Entity | undefined {
  const from = eye(p);
  const dir = p.getViewDirection();
  let best: Entity | undefined;
  let bestScore = Infinity;
  for (const e of enemiesNear(p, from, range + 1.5)) {
    const c = chest(e);
    const ang = angleBetween(dir, sub(c, from));
    const d = dist(from, c);
    if (d > range + 0.8 || ang > cone + Math.min(25, 30 / Math.max(d, 1))) continue;
    if (!lineOfSight(p.dimension, from, c)) continue;
    const score = ang * 1.0 + d * 0.6 - (prefer && prefer(e) ? 40 : 0);
    if (score < bestScore) {
      bestScore = score;
      best = e;
    }
  }
  return best;
}

export function isSolid(b: Block | undefined): boolean {
  if (!b) return false;
  try {
    if (b.isAir || b.isLiquid) return false;
  } catch {
    return false;
  }
  const id = b.typeId;
  return !/(short_grass|tall_grass|fern|flower|sapling|torch|snow_layer|vine|carpet|button|lever|rail|sign|banner|bush|dead_bush|seagrass|kelp|coral_fan|pressure_plate|tripwire|redstone_wire|cobweb|azalea$|_roots$|mushroom$|sugar_cane|wheat|carrots|potatoes|beetroot|light_block|structure_void|fire)/.test(id);
}

export function isOpen(b: Block | undefined): boolean {
  if (!b) return false;
  try {
    if (b.isAir) return true;
    if (b.isLiquid) return b.typeId.includes("water");
  } catch {
    return false;
  }
  return !isSolid(b);
}

/** Find a standable spot at/below `loc` (search down `down` blocks, need `height` open blocks). */
export function groundSpot(dim: Dimension, loc: Vector3, down = 6, height = 2, up = 1): Vector3 | undefined {
  const x = Math.floor(loc.x);
  const z = Math.floor(loc.z);
  const y0 = Math.floor(loc.y);
  for (let y = y0 + up; y >= y0 - down; y--) {
    try {
      const below = dim.getBlock({ x, y: y - 1, z });
      if (!isSolid(below)) continue;
      let ok = true;
      for (let k = 0; k < height; k++) {
        if (!isOpen(dim.getBlock({ x, y: y + k, z }))) {
          ok = false;
          break;
        }
      }
      if (ok) return { x: x + 0.5, y, z: z + 0.5 };
    } catch {
      return undefined;
    }
  }
  return undefined;
}

/** Point along the view ray, stopped short of the first solid block. */
export function rayPoint(p: Player, range: number): Vector3 {
  const from = eye(p);
  const dir = p.getViewDirection();
  try {
    const hit = p.dimension.getBlockFromRay(from, dir, { maxDistance: range, includeLiquidBlocks: false, includePassableBlocks: false });
    if (hit) {
      const hp = add(hit.block.location, hit.faceLocation);
      return sub(hp, mul(dir, 0.6));
    }
  } catch {
    /* ignore */
  }
  return add(from, mul(dir, range));
}
