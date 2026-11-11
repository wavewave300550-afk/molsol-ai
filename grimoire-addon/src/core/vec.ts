import type { Vector3 } from "@minecraft/server";

/** Small immutable vector helpers (Minecraft world space: +X east, +Y up, +Z south). */
export type V3 = Vector3;

export const v3 = (x: number, y: number, z: number): V3 => ({ x, y, z });
export const add = (a: V3, b: V3): V3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a: V3, b: V3): V3 => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const mul = (a: V3, s: number): V3 => ({ x: a.x * s, y: a.y * s, z: a.z * s });
export const dot = (a: V3, b: V3): number => a.x * b.x + a.y * b.y + a.z * b.z;
export const cross = (a: V3, b: V3): V3 => ({
  x: a.y * b.z - a.z * b.y,
  y: a.z * b.x - a.x * b.z,
  z: a.x * b.y - a.y * b.x,
});
export const len = (a: V3): number => Math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
export const dist = (a: V3, b: V3): number => len(sub(a, b));
export const dist2 = (a: V3, b: V3): number => {
  const dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
  return dx * dx + dy * dy + dz * dz;
};
export const hdist = (a: V3, b: V3): number => Math.hypot(a.x - b.x, a.z - b.z);
export const norm = (a: V3): V3 => {
  const l = len(a);
  return l < 1e-9 ? { x: 0, y: 0, z: 1 } : mul(a, 1 / l);
};
export const lerp = (a: V3, b: V3, t: number): V3 => add(a, mul(sub(b, a), t));
export const flat = (a: V3): V3 => ({ x: a.x, y: 0, z: a.z });
export const flatNorm = (a: V3): V3 => norm(flat(a));
export const clamp = (v: number, lo: number, hi: number): number => (v < lo ? lo : v > hi ? hi : v);
export const center = (l: V3): V3 => ({ x: Math.floor(l.x) + 0.5, y: Math.floor(l.y), z: Math.floor(l.z) + 0.5 });
export const floor3 = (l: V3): V3 => ({ x: Math.floor(l.x), y: Math.floor(l.y), z: Math.floor(l.z) });
export const DEG = Math.PI / 180;

/** Minecraft view vector from yaw (y) and pitch (x) in degrees. */
export function dirFromYawPitch(yaw: number, pitch: number): V3 {
  const cp = Math.cos(pitch * DEG);
  return { x: -Math.sin(yaw * DEG) * cp, y: -Math.sin(pitch * DEG), z: Math.cos(yaw * DEG) * cp };
}

/** Inverse of dirFromYawPitch. */
export function yawPitchOf(d: V3): { yaw: number; pitch: number } {
  const n = norm(d);
  const yaw = Math.atan2(-n.x, n.z) / DEG;
  const pitch = -Math.asin(clamp(n.y, -1, 1)) / DEG;
  return { yaw, pitch };
}

/** Rotate a vector around +Y by deg (Minecraft yaw sense: positive turns right / clockwise from above). */
export function rotY(v: V3, deg: number): V3 {
  const c = Math.cos(deg * DEG), s = Math.sin(deg * DEG);
  // yaw +90 maps south(+Z) to west(-X)
  return { x: v.x * c - v.z * s, y: v.y, z: v.x * s + v.z * c };
}

/** Orthonormal basis around a forward direction: right, up. */
export function basis(fwd: V3): { f: V3; r: V3; u: V3 } {
  const f = norm(fwd);
  const worldUp = Math.abs(f.y) > 0.97 ? v3(0, 0, 1) : v3(0, 1, 0);
  const r = norm(cross(f, worldUp));
  const u = norm(cross(r, f));
  return { f, r, u };
}

/** Point on a quadratic bezier. */
export function bezier2(a: V3, c: V3, b: V3, t: number): V3 {
  const u = 1 - t;
  return add(add(mul(a, u * u), mul(c, 2 * u * t)), mul(b, t * t));
}

/** Point on a cubic bezier. */
export function bezier3(a: V3, c1: V3, c2: V3, b: V3, t: number): V3 {
  const u = 1 - t;
  return add(add(mul(a, u * u * u), mul(c1, 3 * u * u * t)), add(mul(c2, 3 * u * t * t), mul(b, t * t * t)));
}

/** Distance from point p to segment ab, and the parametric t of the closest point. */
export function segDist(p: V3, a: V3, b: V3): { d: number; t: number } {
  const ab = sub(b, a);
  const l2 = dot(ab, ab);
  const t = l2 < 1e-9 ? 0 : clamp(dot(sub(p, a), ab) / l2, 0, 1);
  return { d: dist(p, add(a, mul(ab, t))), t };
}

export const ringPoint = (c: V3, r: number, deg: number, y = 0): V3 => ({
  x: c.x + Math.cos(deg * DEG) * r,
  y: c.y + y,
  z: c.z + Math.sin(deg * DEG) * r,
});

/** Deterministic small PRNG (mulberry32) for reproducible spell layouts. */
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
