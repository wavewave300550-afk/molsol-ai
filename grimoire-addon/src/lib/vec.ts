import type { Vector3 } from "@minecraft/server";

export type V3 = Vector3;
export const v = (x: number, y: number, z: number): V3 => ({ x, y, z });
export const add = (a: V3, b: V3): V3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a: V3, b: V3): V3 => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const mul = (a: V3, s: number): V3 => ({ x: a.x * s, y: a.y * s, z: a.z * s });
export const dot = (a: V3, b: V3): number => a.x * b.x + a.y * b.y + a.z * b.z;
export const len = (a: V3): number => Math.hypot(a.x, a.y, a.z);
export const dist = (a: V3, b: V3): number => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
export const distXZ = (a: V3, b: V3): number => Math.hypot(a.x - b.x, a.z - b.z);
export const lerp = (a: V3, b: V3, t: number): V3 => ({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t });
export const up = (a: V3, h: number): V3 => ({ x: a.x, y: a.y + h, z: a.z });
export function norm(a: V3): V3 {
  const l = len(a);
  return l < 1e-6 ? { x: 0, y: 0, z: 1 } : { x: a.x / l, y: a.y / l, z: a.z / l };
}
export const flat = (a: V3): V3 => ({ x: a.x, y: 0, z: a.z });
/** Horizontal unit vector for a Minecraft yaw (0 = +Z/south, 90 = -X/west). */
export function fromYaw(yawDeg: number): V3 {
  const r = (yawDeg * Math.PI) / 180;
  return { x: -Math.sin(r), y: 0, z: Math.cos(r) };
}
/** Minecraft yaw that faces along a direction. */
export function yawOf(d: V3): number {
  return (Math.atan2(-d.x, d.z) * 180) / Math.PI;
}
export function pitchOf(d: V3): number {
  return (-Math.atan2(d.y, Math.hypot(d.x, d.z)) * 180) / Math.PI;
}
/** Right-hand perpendicular (horizontal) of a direction. */
export function right(d: V3): V3 {
  const f = norm(flat(d));
  return { x: -f.z, y: 0, z: f.x };
}
/** Point on a horizontal circle; angle in degrees, 0 = +X. */
export function polar(center: V3, radius: number, angleDeg: number, dy = 0): V3 {
  const r = (angleDeg * Math.PI) / 180;
  return { x: center.x + Math.cos(r) * radius, y: center.y + dy, z: center.z + Math.sin(r) * radius };
}
export const clamp = (x: number, lo: number, hi: number): number => Math.max(lo, Math.min(hi, x));
export const smooth = (t: number): number => { const c = clamp(t, 0, 1); return c * c * (3 - 2 * c); };
export const easeOut = (t: number): number => 1 - Math.pow(1 - clamp(t, 0, 1), 3);
export const easeIn = (t: number): number => Math.pow(clamp(t, 0, 1), 3);
/** Quadratic bezier. */
export function bezier(a: V3, b: V3, c: V3, t: number): V3 {
  return lerp(lerp(a, b, t), lerp(b, c, t), t);
}
/** Catmull-Rom through a list of points, t in 0..1 over the whole path. */
export function spline(pts: V3[], t: number): V3 {
  const n = pts.length - 1;
  const f = clamp(t, 0, 1) * n;
  const i = Math.min(Math.floor(f), n - 1);
  const u = f - i;
  const p0 = pts[Math.max(i - 1, 0)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(i + 2, n)];
  const c = (a: number, b: number, cc: number, d: number) =>
    0.5 * (2 * b + (-a + cc) * u + (2 * a - 5 * b + 4 * cc - d) * u * u + (-a + 3 * b - 3 * cc + d) * u * u * u);
  return { x: c(p0.x, p1.x, p2.x, p3.x), y: c(p0.y, p1.y, p2.y, p3.y), z: c(p0.z, p1.z, p2.z, p3.z) };
}
/** Shortest signed angle from a to b in degrees. */
export function angleDelta(a: number, b: number): number {
  let d = (b - a) % 360;
  if (d > 180) d -= 360;
  if (d < -180) d += 360;
  return d;
}
/** Distance from point p to segment a-b. */
export function distToSegment(p: V3, a: V3, b: V3): number {
  const ab = sub(b, a);
  const t = clamp(dot(sub(p, a), ab) / Math.max(dot(ab, ab), 1e-9), 0, 1);
  return dist(p, add(a, mul(ab, t)));
}
