import { Dimension, Vector3 } from "@minecraft/server";

/**
 * World height limits per dimension.  The engine refuses to spawn, teleport or play anything outside
 * them (LocationOutOfWorldBoundariesError) - on a superflat world the ground is only 4 blocks above
 * the bottom, so an effect that starts a few blocks underground would silently not exist.
 */
const LIMITS = new Map<string, { min: number; max: number }>();

function limits(dim: Dimension): { min: number; max: number } {
  let b = LIMITS.get(dim.id);
  if (!b) {
    try {
      const r = dim.heightRange;
      b = { min: r.min, max: r.max };
    } catch {
      b = { min: -64, max: 320 };
    }
    LIMITS.set(dim.id, b);
  }
  return b;
}

/** The location moved vertically into the world's height limits (unchanged when already inside). */
export function inWorld(dim: Dimension, loc: Vector3): Vector3 {
  const b = limits(dim);
  if (loc.y >= b.min + 0.01 && loc.y <= b.max - 0.01) return loc;
  return { x: loc.x, y: Math.min(Math.max(loc.y, b.min + 0.01), b.max - 0.01), z: loc.z };
}
