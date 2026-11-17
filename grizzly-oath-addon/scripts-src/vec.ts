import { Vector3 } from "@minecraft/server";

export const v = (x: number, y: number, z: number): Vector3 => ({ x, y, z });
export const UP: Vector3 = v(0, 1, 0);
export const add = (a: Vector3, b: Vector3): Vector3 => v(a.x + b.x, a.y + b.y, a.z + b.z);
export const sub = (a: Vector3, b: Vector3): Vector3 => v(a.x - b.x, a.y - b.y, a.z - b.z);
export const mul = (a: Vector3, s: number): Vector3 => v(a.x * s, a.y * s, a.z * s);
export const dot = (a: Vector3, b: Vector3): number => a.x * b.x + a.y * b.y + a.z * b.z;
export const len = (a: Vector3): number => Math.hypot(a.x, a.y, a.z);
export const dist = (a: Vector3, b: Vector3): number => len(sub(a, b));
export const lerp = (a: Vector3, b: Vector3, t: number): Vector3 => add(a, mul(sub(b, a), t));
export const up = (a: Vector3, h: number): Vector3 => v(a.x, a.y + h, a.z);

export function norm(a: Vector3): Vector3 {
  const l = len(a);
  return l < 1e-6 ? v(0, 0, 1) : mul(a, 1 / l);
}

export const cross = (a: Vector3, b: Vector3): Vector3 =>
  v(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x);

/** Horizontal (y = 0) unit vector of a direction. */
export function flat(a: Vector3): Vector3 {
  const f = v(a.x, 0, a.z);
  return len(f) < 1e-4 ? v(0, 0, 1) : norm(f);
}

/** Player's right-hand side for a facing direction (Minecraft: +x east, +z south). */
export const rightOf = (dir: Vector3): Vector3 => norm(cross(flat(dir), UP));

export function rotY(a: Vector3, degrees: number): Vector3 {
  const r = (degrees * Math.PI) / 180;
  const c = Math.cos(r);
  const s = Math.sin(r);
  return v(a.x * c - a.z * s, a.y, a.x * s + a.z * c);
}

export function distToSegment(p: Vector3, a: Vector3, b: Vector3): number {
  const ab = sub(b, a);
  const l2 = dot(ab, ab);
  if (l2 < 1e-9) return dist(p, a);
  const t = Math.max(0, Math.min(1, dot(sub(p, a), ab) / l2));
  return dist(p, add(a, mul(ab, t)));
}
