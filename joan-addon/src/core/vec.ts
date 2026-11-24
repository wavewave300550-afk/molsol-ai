import { Vector3 } from "@minecraft/server";

/** Small, allocation-friendly vector helpers. */
export type V3 = Vector3;

export const v = (x: number, y: number, z: number): V3 => ({ x, y, z });
export const add = (a: V3, b: V3): V3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a: V3, b: V3): V3 => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const scale = (a: V3, s: number): V3 => ({ x: a.x * s, y: a.y * s, z: a.z * s });
export const dot = (a: V3, b: V3): number => a.x * b.x + a.y * b.y + a.z * b.z;
export const cross = (a: V3, b: V3): V3 => ({ x: a.y * b.z - a.z * b.y, y: a.z * b.x - a.x * b.z, z: a.x * b.y - a.y * b.x });
export const len = (a: V3): number => Math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
export const len2 = (a: V3): number => a.x * a.x + a.y * a.y + a.z * a.z;
export const dist = (a: V3, b: V3): number => len(sub(a, b));
export const dist2 = (a: V3, b: V3): number => len2(sub(a, b));
export const hdist = (a: V3, b: V3): number => Math.hypot(a.x - b.x, a.z - b.z);
export const lerp = (a: V3, b: V3, t: number): V3 => ({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t });
export const flat = (a: V3): V3 => ({ x: a.x, y: 0, z: a.z });
export const clamp = (x: number, lo: number, hi: number): number => (x < lo ? lo : x > hi ? hi : x);

export function norm(a: V3): V3 {
  const l = len(a);
  return l < 1e-9 ? { x: 0, y: 0, z: 0 } : { x: a.x / l, y: a.y / l, z: a.z / l };
}

/** Horizontal unit direction from a to b (zero vector if they coincide). */
export function flatDir(a: V3, b: V3): V3 {
  return norm({ x: b.x - a.x, y: 0, z: b.z - a.z });
}

/** Rotate around the world Y axis (radians, counter-clockwise seen from above with +X east, +Z south). */
export function rotY(a: V3, ang: number): V3 {
  const c = Math.cos(ang);
  const s = Math.sin(ang);
  return { x: a.x * c - a.z * s, y: a.y, z: a.x * s + a.z * c };
}

/** Minecraft yaw (degrees) that faces direction d. */
export function yawOf(d: V3): number {
  return (Math.atan2(-d.x, d.z) * 180) / Math.PI;
}

/** Unit horizontal direction for a Minecraft yaw in degrees. */
export function dirOfYaw(yaw: number): V3 {
  const r = (yaw * Math.PI) / 180;
  return { x: -Math.sin(r), y: 0, z: Math.cos(r) };
}

export function perpXZ(d: V3): V3 {
  return { x: -d.z, y: 0, z: d.x };
}

export const finite = (a: V3): boolean => Number.isFinite(a.x) && Number.isFinite(a.y) && Number.isFinite(a.z);

export function fmt(a: V3): string {
  return `${a.x.toFixed(1)},${a.y.toFixed(1)},${a.z.toFixed(1)}`;
}

/** Deterministic-enough RNG helpers. */
export const rand = (lo: number, hi: number): number => lo + Math.random() * (hi - lo);
export const pick = <T>(arr: readonly T[]): T => arr[Math.floor(Math.random() * arr.length)];
export function chance(p: number): boolean {
  return Math.random() < p;
}
