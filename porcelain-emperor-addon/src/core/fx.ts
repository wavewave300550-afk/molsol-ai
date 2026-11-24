import { Dimension, MolangVariableMap, Player, Vector3 } from "@minecraft/server";
import { FX } from "../config.js";
import { add, dist, lerp, v } from "./vec.js";

export type RGB = { red: number; green: number; blue: number };
export const GOLD: RGB = { red: 1.0, green: 0.78, blue: 0.3 };
export const RED: RGB = { red: 1.0, green: 0.2, blue: 0.15 };
export const IVORY: RGB = { red: 1.0, green: 0.95, blue: 0.85 };

/** Spawn a particle, ignoring unloaded chunks / out-of-world positions (purely cosmetic). */
export function particle(dim: Dimension, id: string, at: Vector3, vars?: MolangVariableMap): void {
  try {
    dim.spawnParticle(id, at, vars);
  } catch {
    // cosmetic only
  }
}

/** Flat ground marker (imperial seal) that warns where an attack will land. */
export function telegraph(dim: Dimension, at: Vector3, radius: number, seconds: number, color: RGB = RED): void {
  const m = new MolangVariableMap();
  m.setFloat("variable.size", radius);
  m.setFloat("variable.life", seconds);
  m.setColorRGB("variable.color", color);
  particle(dim, FX.telegraph, at, m);
}

export function crackDecal(dim: Dimension, at: Vector3, size: number, seconds: number): void {
  const m = new MolangVariableMap();
  m.setFloat("variable.size", size);
  m.setFloat("variable.life", seconds);
  particle(dim, FX.crackDecal, at, m);
}

export function ringWave(dim: Dimension, at: Vector3, radius: number): void {
  const m = new MolangVariableMap();
  m.setFloat("variable.size", radius * 2);
  particle(dim, FX.ringWave, at, m);
}

export function breathPuff(dim: Dimension, at: Vector3, dir: Vector3, speed: number): void {
  const m = new MolangVariableMap();
  m.setFloat("variable.dir_x", dir.x);
  m.setFloat("variable.dir_y", dir.y);
  m.setFloat("variable.dir_z", dir.z);
  m.setFloat("variable.speed", speed);
  particle(dim, FX.breath, at, m);
}

/** Line of gold motes between two points (golden threads, beams). */
export function goldLine(dim: Dimension, from: Vector3, to: Vector3, step = 0.6, id: string = FX.goldMote): void {
  const d = dist(from, to);
  const n = Math.max(1, Math.min(60, Math.floor(d / step)));
  for (let i = 0; i <= n; i++) particle(dim, id, lerp(from, to, i / n));
}

export function ring(dim: Dimension, center: Vector3, radius: number, points: number, id: string = FX.goldMote): void {
  for (let i = 0; i < points; i++) {
    const a = (i / points) * Math.PI * 2;
    particle(dim, id, add(center, v(Math.cos(a) * radius, 0, Math.sin(a) * radius)));
  }
}

export function sound(dim: Dimension, id: string, at: Vector3, volume = 1, pitch = 1): void {
  try {
    dim.playSound(id, at, { volume, pitch });
  } catch {
    // ignore
  }
}

export function playerSound(p: Player, id: string, volume = 1, pitch = 1): void {
  try {
    p.playSound(id, { volume, pitch });
  } catch {
    // ignore
  }
}
