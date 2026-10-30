import { Vector3 } from "@minecraft/server";

export const v = (x: number, y: number, z: number): Vector3 => ({ x, y, z });
export const add = (a: Vector3, b: Vector3): Vector3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a: Vector3, b: Vector3): Vector3 => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const scale = (a: Vector3, s: number): Vector3 => ({ x: a.x * s, y: a.y * s, z: a.z * s });
export const len = (a: Vector3): number => Math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
export const dist = (a: Vector3, b: Vector3): number => len(sub(a, b));
export const lerp = (a: Vector3, b: Vector3, t: number): Vector3 => add(a, scale(sub(b, a), t));

export function norm(a: Vector3): Vector3 {
  const l = len(a);
  return l < 1e-6 ? { x: 0, y: 0, z: 0 } : scale(a, 1 / l);
}

/** Normalised horizontal direction from `from` towards `to` (y ignored). */
export function flatDir(from: Vector3, to: Vector3): { x: number; z: number } {
  const dx = to.x - from.x;
  const dz = to.z - from.z;
  const l = Math.sqrt(dx * dx + dz * dz);
  if (l < 1e-4) {
    const a = Math.random() * Math.PI * 2;
    return { x: Math.cos(a), z: Math.sin(a) };
  }
  return { x: dx / l, z: dz / l };
}

/** Rotate a direction around the Y axis by `deg` degrees. */
export function yawRotate(d: Vector3, deg: number): Vector3 {
  const r = (deg * Math.PI) / 180;
  const c = Math.cos(r);
  const s = Math.sin(r);
  return { x: d.x * c - d.z * s, y: d.y, z: d.x * s + d.z * c };
}

export const clamp = (n: number, lo: number, hi: number): number => Math.max(lo, Math.min(hi, n));
