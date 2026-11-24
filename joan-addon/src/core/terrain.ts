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

/**
 * Room for a body standing at p: nothing with a collision box between p and
 * p + height. Uses the engine's own notion of passable blocks (grass, flowers,
 * snow layers, torches, crops...), exactly like groundY, so plants never count
 * as walls.
 */
export function bodyClear(dim: Dimension, p: Vector3, height = 1.7): boolean {
  try {
    const hit = dim.getBlockFromRay({ x: p.x, y: p.y + 0.05, z: p.z }, { x: 0, y: 1, z: 0 }, {
      maxDistance: height,
      includeLiquidBlocks: false,
      includePassableBlocks: false,
    });
    return !hit;
  } catch {
    return true;
  }
}
