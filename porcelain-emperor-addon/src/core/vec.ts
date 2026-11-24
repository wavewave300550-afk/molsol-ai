import { Vector3 } from "@minecraft/server";

export const v = (x: number, y: number, z: number): Vector3 => ({ x, y, z });
export const add = (a: Vector3, b: Vector3): Vector3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a: Vector3, b: Vector3): Vector3 => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const scale = (a: Vector3, s: number): Vector3 => ({ x: a.x * s, y: a.y * s, z: a.z * s });
export const len = (a: Vector3): number => Math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
export const dist = (a: Vector3, b: Vector3): number => len(sub(a, b));
export const distXZ = (a: Vector3, b: Vector3): number => Math.hypot(a.x - b.x, a.z - b.z);
export const lerp = (a: Vector3, b: Vector3, t: number): Vector3 => add(a, scale(sub(b, a), t));
export const clamp = (n: number, lo: number, hi: number): number => Math.max(lo, Math.min(hi, n));
export const copy = (a: Vector3): Vector3 => ({ x: a.x, y: a.y, z: a.z });

export function norm(a: Vector3): Vector3 {
  const l = len(a);
  return l < 1e-6 ? { x: 0, y: 0, z: 0 } : scale(a, 1 / l);
}

export function flat(a: Vector3): Vector3 {
  return { x: a.x, y: 0, z: a.z };
}

/** Unit horizontal direction for a Minecraft yaw (0 = south/+Z, 90 = west/-X). */
export function yawDir(yawDeg: number): Vector3 {
  const r = (yawDeg * Math.PI) / 180;
  return { x: -Math.sin(r), y: 0, z: Math.cos(r) };
}

/** Minecraft yaw that faces along a horizontal direction. */
export function dirYaw(d: Vector3): number {
  return (Math.atan2(-d.x, d.z) * 180) / Math.PI;
}

/** Smallest signed difference b - a between two angles in degrees, in (-180, 180]. */
export function angleDiff(a: number, b: number): number {
  let d = (b - a) % 360;
  if (d > 180) d -= 360;
  if (d <= -180) d += 360;
  return d;
}

/** Rotate a horizontal vector around Y by `deg` degrees (same sense as yaw). */
export function yawRotate(d: Vector3, deg: number): Vector3 {
  const r = (deg * Math.PI) / 180;
  const c = Math.cos(r);
  const s = Math.sin(r);
  return { x: d.x * c - d.z * s, y: d.y, z: d.x * s + d.z * c };
}

/** Distance from point p to the segment a-b. */
export function distToSegment(p: Vector3, a: Vector3, b: Vector3): number {
  const ab = sub(b, a);
  const l2 = ab.x * ab.x + ab.y * ab.y + ab.z * ab.z;
  if (l2 < 1e-6) return dist(p, a);
  const t = clamp(((p.x - a.x) * ab.x + (p.y - a.y) * ab.y + (p.z - a.z) * ab.z) / l2, 0, 1);
  return dist(p, add(a, scale(ab, t)));
}

/** Deterministic PRNG (mulberry32) used by the arena blueprint. */
export function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function pick<T>(arr: readonly T[], r: () => number = Math.random): T {
  return arr[Math.floor(r() * arr.length) % arr.length];
}
