import { Vector3 } from "@minecraft/server";

export const v3 = (x: number, y: number, z: number): Vector3 => ({ x, y, z });
export const add = (a: Vector3, b: Vector3): Vector3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a: Vector3, b: Vector3): Vector3 => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const mul = (a: Vector3, k: number): Vector3 => ({ x: a.x * k, y: a.y * k, z: a.z * k });
export const dot = (a: Vector3, b: Vector3): number => a.x * b.x + a.y * b.y + a.z * b.z;
export const len = (a: Vector3): number => Math.sqrt(dot(a, a));
export const dist = (a: Vector3, b: Vector3): number => len(sub(a, b));
export const hdist = (a: Vector3, b: Vector3): number => Math.hypot(a.x - b.x, a.z - b.z);

export function norm(a: Vector3): Vector3 {
  const l = len(a);
  return l > 1e-6 ? mul(a, 1 / l) : v3(0, 0, 0);
}

/** Horizontal unit vector of a direction (falls back to +Z). */
export function flat(a: Vector3): Vector3 {
  const l = Math.hypot(a.x, a.z);
  return l > 1e-6 ? v3(a.x / l, 0, a.z / l) : v3(0, 0, 1);
}

/** Rotate a horizontal vector around Y by `deg` degrees (counter-clockwise seen from above). */
export function rotY(a: Vector3, deg: number): Vector3 {
  const r = (deg * Math.PI) / 180;
  const c = Math.cos(r);
  const s = Math.sin(r);
  return v3(a.x * c - a.z * s, a.y, a.x * s + a.z * c);
}

/** Angle in degrees between two vectors. */
export function angleBetween(a: Vector3, b: Vector3): number {
  const la = len(a);
  const lb = len(b);
  if (la < 1e-6 || lb < 1e-6) return 180;
  const c = Math.max(-1, Math.min(1, dot(a, b) / (la * lb)));
  return (Math.acos(c) * 180) / Math.PI;
}

export const clamp = (x: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, x));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const center = (b: { x: number; y: number; z: number }): Vector3 => v3(b.x + 0.5, b.y, b.z + 0.5);
export const floorV = (a: Vector3): Vector3 => v3(Math.floor(a.x), Math.floor(a.y), Math.floor(a.z));

/** "12.5s" / "3s" formatting for cooldown displays. */
export function secs(ticks: number): string {
  const s = Math.max(0, ticks) / 20;
  return s >= 10 ? `${Math.ceil(s)}s` : `${s.toFixed(1)}s`;
}

/** Text meter like "||||||....". */
export function meter(frac: number, width = 10, on = "|", off = "."): string {
  const n = Math.round(clamp(frac, 0, 1) * width);
  return on.repeat(n) + off.repeat(width - n);
}

export function safeJson<T>(raw: unknown, fallback: T): T {
  if (typeof raw !== "string" || raw.length === 0) return fallback;
  try {
    const v = JSON.parse(raw) as T;
    return v && typeof v === "object" ? v : fallback;
  } catch {
    return fallback;
  }
}

export function warn(msg: string, err?: unknown): void {
  console.warn(`[plrace] ${msg}${err !== undefined ? `: ${err instanceof Error ? err.message : String(err)}` : ""}`);
}
