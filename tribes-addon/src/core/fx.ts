import { Dimension, Entity, Player, Vector3 } from "@minecraft/server";
import { add, dist, lerp, v } from "./vec.js";

/** Particle colours shipped in the resource pack: tribes:<color>_mote|_burst|_flare */
export type FxColor = "gold" | "cyan" | "green" | "sauce" | "noodle" | "purple" | "orange" | "white";

export function particle(dim: Dimension, id: string, at: Vector3): void {
  try {
    dim.spawnParticle(id, at);
  } catch {
    // unloaded chunk or out of world bounds - purely cosmetic, ignore
  }
}

export const mote = (dim: Dimension, c: FxColor, at: Vector3) => particle(dim, `tribes:${c}_mote`, at);
export const burst = (dim: Dimension, c: FxColor, at: Vector3) => particle(dim, `tribes:${c}_burst`, at);
export const flare = (dim: Dimension, c: FxColor, at: Vector3) => particle(dim, `tribes:${c}_flare`, at);

/** Straight particle beam between two points. */
export function beam(dim: Dimension, c: FxColor, from: Vector3, to: Vector3, step = 0.35): void {
  const d = dist(from, to);
  const n = Math.max(1, Math.floor(d / step));
  for (let i = 0; i <= n; i++) mote(dim, c, lerp(from, to, i / n));
}

/** Wavy "noodle" line between two points. */
export function noodleLine(dim: Dimension, from: Vector3, to: Vector3, phase = 0): void {
  const d = dist(from, to);
  const n = Math.max(2, Math.floor(d / 0.3));
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const p = lerp(from, to, t);
    const w = Math.sin(t * Math.PI * 4 + phase) * 0.25 * Math.sin(t * Math.PI);
    mote(dim, "noodle", add(p, v(w, Math.cos(t * Math.PI * 3 + phase) * 0.18, -w)));
  }
}

export function ring(dim: Dimension, c: FxColor, center: Vector3, radius: number, points?: number): void {
  const n = points ?? Math.max(8, Math.floor(radius * 7));
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    mote(dim, c, add(center, v(Math.cos(a) * radius, 0, Math.sin(a) * radius)));
  }
}

export function sphere(dim: Dimension, c: FxColor, center: Vector3, radius: number, points = 40): void {
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < points; i++) {
    const y = 1 - (i / (points - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const a = golden * i;
    mote(dim, c, add(center, v(Math.cos(a) * r * radius, y * radius, Math.sin(a) * r * radius)));
  }
}

export function column(dim: Dimension, c: FxColor, base: Vector3, height: number): void {
  for (let y = 0; y <= height; y += 0.4) mote(dim, c, add(base, v(0, y, 0)));
}

export function spiral(dim: Dimension, c: FxColor, center: Vector3, radius: number, age: number, arms = 3): void {
  for (let k = 0; k < arms; k++) {
    for (let s = 0; s < 6; s++) {
      const r = radius * (1 - s / 6);
      const a = age * 0.35 + (k / arms) * Math.PI * 2 + s * 0.45;
      mote(dim, c, add(center, v(Math.cos(a) * r, Math.sin(age * 0.2 + s) * 0.3, Math.sin(a) * r)));
    }
  }
}

export function sound(dim: Dimension, id: string, at: Vector3, volume = 1, pitch = 1): void {
  try {
    dim.playSound(id, at, { volume, pitch });
  } catch {
    // ignore unknown/unloaded
  }
}

export function center(e: Entity): Vector3 {
  const l = e.location;
  return { x: l.x, y: l.y + 0.9, z: l.z };
}

export function privateParticle(p: Player, id: string, at: Vector3): void {
  try {
    p.spawnParticle(id, at);
  } catch {
    // ignore
  }
}
