// Particle + sound helpers. Every call is wrapped: a particle in an unloaded chunk must never
// break a skill half-way through.
import { Dimension, MolangVariableMap, RGBA, Vector3 } from "@minecraft/server";

export const RED: RGBA = { red: 1, green: 0.12, blue: 0.08, alpha: 1 };
export const HOT: RGBA = { red: 1, green: 0.55, blue: 0.4, alpha: 1 };
export const DEEP_RED: RGBA = { red: 0.6, green: 0.02, blue: 0.04, alpha: 0.95 };
export const BLACK: RGBA = { red: 0.05, green: 0.01, blue: 0.015, alpha: 0.8 };

type Setup = (m: MolangVariableMap) => void;

export function emit(dim: Dimension, name: string, at: Vector3, setup?: Setup): void {
  try {
    const m = new MolangVariableMap();
    if (setup) setup(m);
    dim.spawnParticle(`grizzly_oath:${name}`, at, m);
  } catch {
    // chunk unloaded / out of world bounds: skip this particle
  }
}

export const glow = (dim: Dimension, at: Vector3, size: number, life: number, color: RGBA, rise = 0) =>
  emit(dim, "glow", at, (m) => {
    m.setFloat("variable.size", size);
    m.setFloat("variable.life", life);
    m.setFloat("variable.rise", rise);
    m.setColorRGBA("variable.color", color);
  });

export const slash = (dim: Dimension, at: Vector3, size: number, rot: number, color: RGBA) =>
  emit(dim, "slash", at, (m) => {
    m.setFloat("variable.size", size);
    m.setFloat("variable.rot", rot);
    m.setColorRGBA("variable.color", color);
  });

export const clawFlash = (dim: Dimension, at: Vector3, size: number, rot: number, color: RGBA) =>
  emit(dim, "claw_flash", at, (m) => {
    m.setFloat("variable.size", size);
    m.setFloat("variable.rot", rot);
    m.setColorRGBA("variable.color", color);
  });

export const clawStreak = (dim: Dimension, at: Vector3, dir: Vector3, color: RGBA, life = 0.5) =>
  emit(dim, "claw_streak", at, (m) => {
    m.setVector3("variable.dir", dir);
    m.setFloat("variable.life", life);
    m.setColorRGBA("variable.color", color);
  });

export const ring = (dim: Dimension, at: Vector3, radius: number, life: number, color: RGBA) =>
  emit(dim, "ring", at, (m) => {
    m.setFloat("variable.radius", radius);
    m.setFloat("variable.life", life);
    m.setColorRGBA("variable.color", color);
  });

export const smoke = (dim: Dimension, at: Vector3, size: number, color: RGBA = BLACK) =>
  emit(dim, "smoke", at, (m) => {
    m.setFloat("variable.size", size);
    m.setColorRGBA("variable.color", color);
  });

export const spark = (dim: Dimension, at: Vector3) => emit(dim, "spark", at);
export const ember = (dim: Dimension, at: Vector3) => emit(dim, "ember", at);
export const blood = (dim: Dimension, at: Vector3) => emit(dim, "blood", at);
export const shard = (dim: Dimension, at: Vector3) => emit(dim, "shard", at);

export function sound(dim: Dimension, id: string, at: Vector3, volume = 1, pitch = 1): void {
  try {
    dim.playSound(id, at, { volume, pitch });
  } catch {
    // ignore
  }
}
