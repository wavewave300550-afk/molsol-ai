import { Vector3 } from "@minecraft/server";

export const v = (x: number, y: number, z: number): Vector3 => ({ x, y, z });
export const add = (a: Vector3, b: Vector3): Vector3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a: Vector3, b: Vector3): Vector3 => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const scale = (a: Vector3, s: number): Vector3 => ({ x: a.x * s, y: a.y * s, z: a.z * s });
export const dot = (a: Vector3, b: Vector3): number => a.x * b.x + a.y * b.y + a.z * b.z;
export const len = (a: Vector3): number => Math.sqrt(dot(a, a));
export const dist = (a: Vector3, b: Vector3): number => len(sub(a, b));
export const lerp = (a: Vector3, b: Vector3, t: number): Vector3 => add(a, scale(sub(b, a), t));
export const clamp = (n: number, lo: number, hi: number): number => Math.max(lo, Math.min(hi, n));

export function norm(a: Vector3): Vector3 {
  const l = len(a);
  return l < 1e-6 ? { x: 0, y: 0, z: 0 } : scale(a, 1 / l);
}

/** Horizontal unit vector of a direction (falls back to +Z when looking straight up/down). */
export function flat(d: Vector3): Vector3 {
  const l = Math.sqrt(d.x * d.x + d.z * d.z);
  return l < 1e-4 ? { x: 0, y: 0, z: 1 } : { x: d.x / l, y: 0, z: d.z / l };
}

/** Normalised horizontal direction from `from` towards `to` (random if they overlap). */
export function flatDir(from: Vector3, to: Vector3): Vector3 {
  const dx = to.x - from.x;
  const dz = to.z - from.z;
  const l = Math.sqrt(dx * dx + dz * dz);
  if (l < 1e-4) {
    const a = Math.random() * Math.PI * 2;
    return { x: Math.cos(a), y: 0, z: Math.sin(a) };
  }
  return { x: dx / l, y: 0, z: dz / l };
}

/**
 * The player's right-hand side for a facing direction. Minecraft yaw 0 faces +Z (south),
 * where the right hand points to -X (west): right = (-z, 0, x).
 */
export function rightOf(d: Vector3): Vector3 {
  const f = flat(d);
  return { x: -f.z, y: 0, z: f.x };
}

/** Rotate a direction around the Y axis by `deg` degrees. */
export function yawRotate(d: Vector3, deg: number): Vector3 {
  const r = (deg * Math.PI) / 180;
  const c = Math.cos(r);
  const s = Math.sin(r);
  return { x: d.x * c - d.z * s, y: d.y, z: d.x * s + d.z * c };
}

/** Distance from point p to the segment a-b. */
export function segmentDistance(p: Vector3, a: Vector3, b: Vector3): number {
  const ab = sub(b, a);
  const l2 = dot(ab, ab);
  const t = l2 < 1e-9 ? 0 : clamp(dot(sub(p, a), ab) / l2, 0, 1);
  return dist(p, add(a, scale(ab, t)));
}
