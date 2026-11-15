/** Small vector helpers (plain objects, no allocations hidden in classes). */
export interface V3 {
  x: number;
  y: number;
  z: number;
}

export const v3 = (x: number, y: number, z: number): V3 => ({ x, y, z });
export const add = (a: V3, b: V3): V3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a: V3, b: V3): V3 => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const mul = (a: V3, s: number): V3 => ({ x: a.x * s, y: a.y * s, z: a.z * s });
export const len = (a: V3): number => Math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
export const dist = (a: V3, b: V3): number => len(sub(a, b));
export const distXZ = (a: V3, b: V3): number => Math.hypot(a.x - b.x, a.z - b.z);
export const norm = (a: V3): V3 => {
  const l = len(a) || 1;
  return { x: a.x / l, y: a.y / l, z: a.z / l };
};
export const lerp3 = (a: V3, b: V3, t: number): V3 => ({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t });
export const floor3 = (a: V3): V3 => ({ x: Math.floor(a.x), y: Math.floor(a.y), z: Math.floor(a.z) });
export const center = (x: number, y: number, z: number): V3 => ({ x: x + 0.5, y: y + 0.5, z: z + 0.5 });

export function clamp(v: number, lo: number, hi: number): number {
  return v < lo ? lo : v > hi ? hi : v;
}

/** Distance from point (px,pz) to the segment (ax,az)-(bx,bz) and the segment parameter. */
export function segDist2D(px: number, pz: number, ax: number, az: number, bx: number, bz: number): { d: number; t: number } {
  const dx = bx - ax;
  const dz = bz - az;
  const l2 = dx * dx + dz * dz || 1;
  const t = clamp(((px - ax) * dx + (pz - az) * dz) / l2, 0, 1);
  const qx = ax + dx * t - px;
  const qz = az + dz * t - pz;
  return { d: Math.sqrt(qx * qx + qz * qz), t };
}

export function angleDeg(a: number): number {
  let d = a % 360;
  if (d < 0) d += 360;
  return d;
}

/** Signed smallest difference a-b in degrees, in (-180, 180]. */
export function angleDiffDeg(a: number, b: number): number {
  let d = (a - b) % 360;
  if (d > 180) d -= 360;
  if (d <= -180) d += 360;
  return d;
}
