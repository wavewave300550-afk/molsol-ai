import { Dimension, Vector3 } from "@minecraft/server";
import { dist, norm, sub, V3 } from "./vec.js";

/** Height of the walkable surface under (x, z), searching downwards from refY + 3. */
export function groundY(dim: Dimension, x: number, z: number, refY: number, depth = 10): number | undefined {
  try {
    const hit = dim.getBlockFromRay({ x, y: refY + 3, z }, { x: 0, y: -1, z: 0 }, {
      maxDistance: depth + 3,
      includeLiquidBlocks: true,
      includePassableBlocks: false,
    });
    if (!hit) return undefined;
    return hit.block.location.y + hit.faceLocation.y;
  } catch {
    return undefined;
  }
}

/** True when nothing solid blocks the straight line a -> b. */
export function lineClear(dim: Dimension, a: V3, b: V3): boolean {
  const d = dist(a, b);
  if (d < 0.2) return true;
  try {
    const hit = dim.getBlockFromRay(a, norm(sub(b, a)), { maxDistance: d, includeLiquidBlocks: false, includePassableBlocks: false });
    return !hit;
  } catch {
    return true;
  }
}

/** Is the block cell at p open (air / passable / liquid)? */
export function isOpen(dim: Dimension, p: Vector3): boolean {
  try {
    const b = dim.getBlock({ x: Math.floor(p.x), y: Math.floor(p.y), z: Math.floor(p.z) });
    if (!b) return true;
    return b.isAir || b.isLiquid;
  } catch {
    return true;
  }
}
