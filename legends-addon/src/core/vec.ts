import { Vector3 } from "@minecraft/server";

export const v = (x: number, y: number, z: number): Vector3 => ({ x, y, z });
export const add = (a: Vector3, b: Vector3): Vector3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a: Vector3, b: Vector3): Vector3 => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const scale = (a: Vector3, k: number): Vector3 => ({ x: a.x * k, y: a.y * k, z: a.z * k });
export const len = (a: Vector3): number => Math.hypot(a.x, a.y, a.z);
export const dist = (a: Vector3, b: Vector3): number => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
export const flatDist = (a: Vector3, b: Vector3): number => Math.hypot(a.x - b.x, a.z - b.z);
export const lerp = (a: Vector3, b: Vector3, t: number): Vector3 => ({
  x: a.x + (b.x - a.x) * t,
  y: a.y + (b.y - a.y) * t,
  z: a.z + (b.z - a.z) * t,
});
export const clamp = (x: number, lo: number, hi: number): number => Math.max(lo, Math.min(hi, x));

export function norm(a: Vector3): Vector3 {
  const l = len(a);
  return l > 1e-6 ? scale(a, 1 / l) : { x: 0, y: 0, z: 1 };
}

/** Horizontal unit direction from a to b (falls back to +Z). */
export function flatDir(a: Vector3, b: Vector3): Vector3 {
  const dx = b.x - a.x;
  const dz = b.z - a.z;
  const l = Math.hypot(dx, dz);
  return l > 1e-6 ? { x: dx / l, y: 0, z: dz / l } : { x: 0, y: 0, z: 1 };
}

/** Minecraft yaw (degrees, 0 = +Z/south, 90 = -X/west) of a horizontal direction. */
export const yawOf = (d: Vector3): number => (Math.atan2(-d.x, d.z) * 180) / Math.PI;
export const dirOfYaw = (yaw: number): Vector3 => {
  const r = (yaw * Math.PI) / 180;
  return { x: -Math.sin(r), y: 0, z: Math.cos(r) };
};
export const pitchOf = (d: Vector3): number => (-Math.atan2(d.y, Math.hypot(d.x, d.z)) * 180) / Math.PI;

/** Rotate a horizontal vector by `deg` degrees around +Y (same sense as yaw). */
export function rotY(d: Vector3, deg: number): Vector3 {
  return dirOfYaw(yawOf(d) + deg);
}

export function angleDiff(a: number, b: number): number {
  let d = (b - a) % 360;
  if (d > 180) d -= 360;
  if (d < -180) d += 360;
  return d;
}

/** Distance from point p to the segment ab, and the projection parameter t (0..1). */
export function segDist(p: Vector3, a: Vector3, b: Vector3): { d: number; t: number } {
  const ab = sub(b, a);
  const l2 = ab.x * ab.x + ab.y * ab.y + ab.z * ab.z;
  const t = l2 > 1e-9 ? clamp(((p.x - a.x) * ab.x + (p.y - a.y) * ab.y + (p.z - a.z) * ab.z) / l2, 0, 1) : 0;
  return { d: dist(p, add(a, scale(ab, t))), t };
}

/** Horizontal (XZ) distance from p to segment ab. */
export function flatSegDist(p: Vector3, a: Vector3, b: Vector3): { d: number; t: number } {
  return segDist({ x: p.x, y: 0, z: p.z }, { x: a.x, y: 0, z: a.z }, { x: b.x, y: 0, z: b.z });
}

export function randIn(lo: number, hi: number): number {
  return lo + Math.random() * (hi - lo);
}

export function pick<T>(arr: readonly T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}
