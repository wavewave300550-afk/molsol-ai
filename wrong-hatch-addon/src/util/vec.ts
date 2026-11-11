import { Vector3 } from "@minecraft/server";

export const v3 = (x: number, y: number, z: number): Vector3 => ({ x, y, z });
export const add = (a: Vector3, b: Vector3): Vector3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a: Vector3, b: Vector3): Vector3 => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const mul = (a: Vector3, k: number): Vector3 => ({ x: a.x * k, y: a.y * k, z: a.z * k });
export const len = (a: Vector3): number => Math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
export const hlen = (a: Vector3): number => Math.sqrt(a.x * a.x + a.z * a.z);
export const dist = (a: Vector3, b: Vector3): number => len(sub(a, b));
export const hdist = (a: Vector3, b: Vector3): number => hlen(sub(a, b));
export const norm = (a: Vector3): Vector3 => {
  const l = len(a) || 1;
  return { x: a.x / l, y: a.y / l, z: a.z / l };
};
export const hnorm = (a: Vector3): Vector3 => {
  const l = hlen(a) || 1;
  return { x: a.x / l, y: 0, z: a.z / l };
};
export const dot = (a: Vector3, b: Vector3): number => a.x * b.x + a.y * b.y + a.z * b.z;
export const lerp = (a: Vector3, b: Vector3, t: number): Vector3 => add(a, mul(sub(b, a), t));

/** Minecraft yaw (degrees) -> horizontal unit vector. Yaw 0 faces +Z (south), 90 faces -X. */
export function yawDir(yaw: number): Vector3 {
  const r = (yaw * Math.PI) / 180;
  return { x: -Math.sin(r), y: 0, z: Math.cos(r) };
}

/** Horizontal direction -> Minecraft yaw (degrees). */
export function dirYaw(d: Vector3): number {
  return (Math.atan2(-d.x, d.z) * 180) / Math.PI;
}

/** Signed smallest difference b - a in degrees, in (-180, 180]. */
export function angleDelta(a: number, b: number): number {
  let d = (b - a) % 360;
  if (d > 180) d -= 360;
  if (d <= -180) d += 360;
  return d;
}

/** Rotate a horizontal vector by deg around +Y (same sense as yaw). */
export function rotY(d: Vector3, deg: number): Vector3 {
  return yawDir(dirYaw(d) + deg);
}

/** Distance from point p to the segment a-b. */
export function segDist(p: Vector3, a: Vector3, b: Vector3): number {
  const ab = sub(b, a);
  const l2 = dot(ab, ab);
  if (l2 < 1e-9) return dist(p, a);
  const t = Math.max(0, Math.min(1, dot(sub(p, a), ab) / l2));
  return dist(p, add(a, mul(ab, t)));
}

export const clamp = (x: number, lo: number, hi: number): number => Math.max(lo, Math.min(hi, x));
export const rand = (lo: number, hi: number): number => lo + Math.random() * (hi - lo);
export function pick<T>(arr: readonly T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}
