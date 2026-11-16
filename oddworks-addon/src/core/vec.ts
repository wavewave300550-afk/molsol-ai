import { Vector3 } from "@minecraft/server";

export const v = (x: number, y: number, z: number): Vector3 => ({ x, y, z });
export const ZERO: Vector3 = { x: 0, y: 0, z: 0 };
export const UP: Vector3 = { x: 0, y: 1, z: 0 };

export const add = (a: Vector3, b: Vector3): Vector3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a: Vector3, b: Vector3): Vector3 => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const scale = (a: Vector3, k: number): Vector3 => ({ x: a.x * k, y: a.y * k, z: a.z * k });
export const dot = (a: Vector3, b: Vector3): number => a.x * b.x + a.y * b.y + a.z * b.z;
export const cross = (a: Vector3, b: Vector3): Vector3 => ({
  x: a.y * b.z - a.z * b.y,
  y: a.z * b.x - a.x * b.z,
  z: a.x * b.y - a.y * b.x,
});
export const len = (a: Vector3): number => Math.sqrt(dot(a, a));
export const dist = (a: Vector3, b: Vector3): number => len(sub(a, b));
export const dist2 = (a: Vector3, b: Vector3): number => {
  const d = sub(a, b);
  return dot(d, d);
};
export function norm(a: Vector3): Vector3 {
  const l = len(a);
  return l > 1e-9 ? scale(a, 1 / l) : { x: 0, y: 0, z: 0 };
}
export const lerp = (a: Vector3, b: Vector3, t: number): Vector3 => add(a, scale(sub(b, a), t));
export const flat = (a: Vector3): Vector3 => norm({ x: a.x, y: 0, z: a.z });
export const floor = (a: Vector3): Vector3 => ({ x: Math.floor(a.x), y: Math.floor(a.y), z: Math.floor(a.z) });
export const center = (a: Vector3): Vector3 => ({ x: Math.floor(a.x) + 0.5, y: Math.floor(a.y) + 0.5, z: Math.floor(a.z) + 0.5 });

/** Right-hand vector for a view direction (Minecraft: +X east, +Z south). */
export const rightOf = (dir: Vector3): Vector3 => norm(cross(flat(dir), UP));

/** Angle in degrees between two directions. */
export function angleBetween(a: Vector3, b: Vector3): number {
  const c = dot(norm(a), norm(b));
  return (Math.acos(Math.max(-1, Math.min(1, c))) * 180) / Math.PI;
}

/** Closest distance from point p to segment ab, plus the segment parameter. */
export function pointSegment(p: Vector3, a: Vector3, b: Vector3): { d: number; t: number } {
  const ab = sub(b, a);
  const l2 = dot(ab, ab);
  const t = l2 > 1e-9 ? Math.max(0, Math.min(1, dot(sub(p, a), ab) / l2)) : 0;
  return { d: dist(p, add(a, scale(ab, t))), t };
}

/** Rotate vector around the Y axis by `deg` degrees. */
export function rotY(a: Vector3, deg: number): Vector3 {
  const r = (deg * Math.PI) / 180;
  const c = Math.cos(r);
  const s = Math.sin(r);
  return { x: a.x * c - a.z * s, y: a.y, z: a.x * s + a.z * c };
}

export const clamp = (x: number, lo: number, hi: number): number => (x < lo ? lo : x > hi ? hi : x);
export const rand = (lo: number, hi: number): number => lo + Math.random() * (hi - lo);
export const chance = (p: number): boolean => Math.random() < p;
