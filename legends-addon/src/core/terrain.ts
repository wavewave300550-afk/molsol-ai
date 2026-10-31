/**
 * Terrain queries used to keep script-moved bosses, props and telegraphs on
 * the ground.
 */
import { Block, Dimension, Vector3 } from "@minecraft/server";

const PASSABLE = ["short_grass", "tall_grass", "fern", "large_fern", "dead_bush", "flower", "tulip", "orchid", "allium",
  "bluet", "daisy", "dandelion", "poppy", "cornflower", "lily_of_the_valley", "sapling", "vine", "torch", "snow_layer",
  "carpet", "seagrass", "kelp", "sugar_cane", "sweet_berry_bush", "rail", "button", "lever", "pressure_plate",
  "mushroom", "fire", "web", "lantern", "sign", "banner", "rose", "lilac", "peony", "sunflower", "bush"];

export function isGround(b: Block | undefined): boolean {
  if (!b) return false;
  try {
    if (b.isAir || b.isLiquid) return false;
    const id = b.typeId;
    if (id === "minecraft:grass_block") return true;
    for (const k of PASSABLE) if (id.includes(k)) return false;
    return true;
  } catch {
    return false;
  }
}

function block(dim: Dimension, x: number, y: number, z: number): Block | undefined {
  try {
    return dim.getBlock({ x, y, z });
  } catch {
    return undefined;
  }
}

/**
 * Height of the walkable surface at (x, z), searching from refY + up down to
 * refY - down. Returns refY when nothing is found (open air / unloaded).
 */
export function groundY(dim: Dimension, x: number, z: number, refY: number, upward = 4, down = 10): number {
  const bx = Math.floor(x);
  const bz = Math.floor(z);
  const top = Math.floor(refY) + upward;
  for (let y = top; y >= Math.floor(refY) - down; y--) {
    const b = block(dim, bx, y, bz);
    if (isGround(b)) {
      const above = block(dim, bx, y + 1, bz);
      if (!isGround(above)) return y + 1;
    }
  }
  return refY;
}

export function onGround(dim: Dimension, p: Vector3, refY?: number): Vector3 {
  return { x: p.x, y: groundY(dim, p.x, p.z, refY ?? p.y), z: p.z };
}

/** Is there a solid block between a and b (coarse sampling)? */
export function blocked(dim: Dimension, a: Vector3, b: Vector3): boolean {
  const d = Math.hypot(b.x - a.x, b.y - a.y, b.z - a.z);
  const n = Math.max(1, Math.floor(d / 0.8));
  for (let i = 1; i < n; i++) {
    const t = i / n;
    const bl = block(dim, Math.floor(a.x + (b.x - a.x) * t), Math.floor(a.y + (b.y - a.y) * t), Math.floor(a.z + (b.z - a.z) * t));
    if (isGround(bl)) return true;
  }
  return false;
}
