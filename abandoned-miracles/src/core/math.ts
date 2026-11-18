/**
 * Small vector / angle toolkit shared by every system.
 *
 * Two angle conventions appear in the code and are never mixed implicitly:
 *   yaw    Minecraft entity yaw in degrees: 0 = +Z (south), 90 = -X (west).
 *   theta  mathematical bearing on the XZ plane in degrees: 0 = +X, 90 = +Z.
 * Hazard geometry and telegraph particles use theta; entities use yaw.
 */

export interface V3 {
  x: number;
  y: number;
  z: number;
}

export interface XZ {
  x: number;
  z: number;
}

export const DEG = 180 / Math.PI;
export const RAD = Math.PI / 180;

export const v3 = (x: number, y: number, z: number): V3 => ({ x, y, z });
export const add = (a: V3, b: V3): V3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a: V3, b: V3): V3 => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const mul = (a: V3, k: number): V3 => ({ x: a.x * k, y: a.y * k, z: a.z * k });
export const dot = (a: V3, b: V3): number => a.x * b.x + a.y * b.y + a.z * b.z;
export const len = (a: V3): number => Math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
export const dist = (a: V3, b: V3): number => len(sub(a, b));
export const distXZ = (a: XZ, b: XZ): number => Math.hypot(a.x - b.x, a.z - b.z);

export function norm(a: V3): V3 {
  const l = len(a);
  return l > 1e-9 ? mul(a, 1 / l) : { x: 0, y: 0, z: 0 };
}

export function normXZ(dx: number, dz: number): XZ {
  const l = Math.hypot(dx, dz);
  return l > 1e-9 ? { x: dx / l, z: dz / l } : { x: 0, z: 1 };
}

export const clamp = (v: number, lo: number, hi: number): number => (v < lo ? lo : v > hi ? hi : v);
export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

/** Wrap an angle into (-180, 180]. */
export function wrapDeg(a: number): number {
  a = ((a + 180) % 360 + 360) % 360 - 180;
  return a === -180 ? 180 : a;
}

/** Signed shortest rotation from a to b, degrees. */
export const angDiff = (a: number, b: number): number => wrapDeg(b - a);

/** Move `cur` towards `target` by at most `step` degrees along the shortest arc. */
export function approachAngle(cur: number, target: number, step: number): number {
  const d = angDiff(cur, target);
  return Math.abs(d) <= step ? wrapDeg(target) : wrapDeg(cur + Math.sign(d) * step);
}

export const yawToDir = (yaw: number): XZ => ({ x: -Math.sin(yaw * RAD), z: Math.cos(yaw * RAD) });
export const dirToYaw = (dx: number, dz: number): number => Math.atan2(-dx, dz) * DEG;
export const thetaToDir = (theta: number): XZ => ({ x: Math.cos(theta * RAD), z: Math.sin(theta * RAD) });
export const dirToTheta = (dx: number, dz: number): number => Math.atan2(dz, dx) * DEG;
export const yawToTheta = (yaw: number): number => wrapDeg(yaw + 90);
export const thetaToYaw = (theta: number): number => wrapDeg(theta - 90);

/**
 * Offset in an entity's own frame -> world position.
 * `right` is the entity's right-hand side, `fwd` the direction it faces.
 */
export function localToWorld(origin: V3, yaw: number, right: number, up: number, fwd: number): V3 {
  const f = yawToDir(yaw);
  // facing +Z (yaw 0) the right-hand side is -X
  const r = { x: -f.z, z: f.x };
  return { x: origin.x + r.x * right + f.x * fwd, y: origin.y + up, z: origin.z + r.z * right + f.z * fwd };
}

/** World position -> offset in an entity's frame (inverse of localToWorld). */
export function worldToLocal(origin: V3, yaw: number, p: V3): { right: number; up: number; fwd: number } {
  const f = yawToDir(yaw);
  const r = { x: -f.z, z: f.x };
  const dx = p.x - origin.x;
  const dz = p.z - origin.z;
  return { right: dx * r.x + dz * r.z, up: p.y - origin.y, fwd: dx * f.x + dz * f.z };
}

/** Deterministic PRNG (mulberry32). Each encounter owns one, so fights are reproducible in tests. */
export class Rng {
  private s: number;

  constructor(seed: number) {
    this.s = seed >>> 0 || 0x9e3779b9;
  }

  next(): number {
    let t = (this.s += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  range(lo: number, hi: number): number {
    return lo + (hi - lo) * this.next();
  }

  int(lo: number, hi: number): number {
    return Math.floor(this.range(lo, hi + 1));
  }

  chance(p: number): boolean {
    return this.next() < p;
  }

  pick<T>(items: readonly T[]): T {
    return items[Math.min(items.length - 1, Math.floor(this.next() * items.length))];
  }

  shuffle<T>(items: readonly T[]): T[] {
    const a = items.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(this.next() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  /** Weighted pick; returns undefined when every weight is zero. */
  weighted<T>(items: readonly T[], weight: (item: T) => number): T | undefined {
    const w = items.map((i) => Math.max(0, weight(i)));
    const total = w.reduce((a, b) => a + b, 0);
    if (total <= 0) return undefined;
    let r = this.next() * total;
    for (let i = 0; i < items.length; i++) {
      r -= w[i];
      if (r <= 0) return items[i];
    }
    return items[items.length - 1];
  }
}

export function hashString(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}
