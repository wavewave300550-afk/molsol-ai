import { Vector3 } from "@minecraft/server";

export type V3 = Vector3;

export const v = (x: number, y: number, z: number): V3 => ({ x, y, z });
export const add = (a: V3, b: V3): V3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a: V3, b: V3): V3 => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const mul = (a: V3, s: number): V3 => ({ x: a.x * s, y: a.y * s, z: a.z * s });
export const dot = (a: V3, b: V3): number => a.x * b.x + a.y * b.y + a.z * b.z;
export const len = (a: V3): number => Math.sqrt(dot(a, a));
export const dist = (a: V3, b: V3): number => len(sub(a, b));
export const hdist = (a: V3, b: V3): number => Math.hypot(a.x - b.x, a.z - b.z);
export const lerp = (a: V3, b: V3, t: number): V3 => add(a, mul(sub(b, a), t));
export const clamp = (x: number, lo: number, hi: number): number => (x < lo ? lo : x > hi ? hi : x);

export function norm(a: V3): V3 {
  const l = len(a);
  return l > 1e-9 ? mul(a, 1 / l) : { x: 0, y: 0, z: 0 };
}

export function flat(a: V3): V3 {
  return norm({ x: a.x, y: 0, z: a.z });
}

/** Minecraft yaw (degrees) of a direction: yaw 0 faces +Z, 90 faces -X. */
export function yawOf(d: V3): number {
  return (Math.atan2(-d.x, d.z) * 180) / Math.PI;
}

/** Pitch (degrees, positive = looking down) of a direction. */
export function pitchOf(d: V3): number {
  const h = Math.hypot(d.x, d.z);
  return (-Math.atan2(d.y, h) * 180) / Math.PI;
}

export function dirFromYaw(yaw: number, pitch = 0): V3 {
  const r = (yaw * Math.PI) / 180;
  const p = (pitch * Math.PI) / 180;
  return { x: -Math.sin(r) * Math.cos(p), y: -Math.sin(p), z: Math.cos(r) * Math.cos(p) };
}

export function wrapAngle(a: number): number {
  let x = ((a + 180) % 360 + 360) % 360 - 180;
  if (x === -180) x = 180;
  return x;
}

export function approachAngle(cur: number, target: number, maxStep: number): number {
  const d = wrapAngle(target - cur);
  if (Math.abs(d) <= maxStep) return wrapAngle(target);
  return wrapAngle(cur + Math.sign(d) * maxStep);
}

/**
 * World offset of a point given in Bedrock model units relative to an entity facing `yaw`.
 * Model space: -Z is forward, -X is the entity's right, +Y is up; 16 units per block.
 */
export function modelToWorld(origin: V3, yaw: number, mx: number, my: number, mz: number): V3 {
  const r = (yaw * Math.PI) / 180;
  const fwd = { x: -Math.sin(r), z: Math.cos(r) };
  const right = { x: -Math.cos(r), z: -Math.sin(r) };
  const f = -mz / 16;
  const rt = -mx / 16;
  return { x: origin.x + fwd.x * f + right.x * rt, y: origin.y + my / 16, z: origin.z + fwd.z * f + right.z * rt };
}

/** Distance from point p to the segment a-b. */
export function distToSegment(p: V3, a: V3, b: V3): number {
  const ab = sub(b, a);
  const t = clamp(dot(sub(p, a), ab) / Math.max(dot(ab, ab), 1e-9), 0, 1);
  return dist(p, add(a, mul(ab, t)));
}

/** Does the segment a-b pass through a vertical cylinder (centre c at base, radius r, height h)? */
export function segmentHitsCylinder(a: V3, b: V3, c: V3, r: number, h: number): boolean {
  const steps = Math.max(2, Math.ceil(dist(a, b) / 0.5));
  for (let i = 0; i <= steps; i++) {
    const p = lerp(a, b, i / steps);
    if (p.y >= c.y && p.y <= c.y + h && hdist(p, c) <= r) return true;
  }
  return false;
}

export function rand(lo: number, hi: number): number {
  return lo + Math.random() * (hi - lo);
}

export function pick<T>(arr: readonly T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}
