import { Dimension, MolangVariableMap, Player, Vector3 } from "@minecraft/server";
import { FX, SND } from "../generated/ids.js";

export type RGB = readonly [number, number, number];

export const COLORS = {
  gold: [1.0, 0.82, 0.42] as RGB,
  cyan: [0.38, 0.9, 1.0] as RGB,
  white: [1.0, 0.97, 0.9] as RGB,
  red: [1.0, 0.25, 0.2] as RGB,
  violet: [0.74, 0.34, 1.0] as RGB,
  magenta: [1.0, 0.32, 0.82] as RGB,
  orange: [1.0, 0.55, 0.18] as RGB,
};

let particleBudget = 0;
const PARTICLE_BUDGET_PER_TICK = 48;

/** Called once per tick by the main loop. */
export function resetFxBudget(): void {
  particleBudget = PARTICLE_BUDGET_PER_TICK;
}

function vars(o: { [k: string]: number | undefined }, color?: RGB): MolangVariableMap {
  const m = new MolangVariableMap();
  for (const k in o) {
    const val = o[k];
    if (val !== undefined) m.setFloat(`variable.${k}`, val);
  }
  if (color) {
    m.setFloat("variable.cr", color[0]);
    m.setFloat("variable.cg", color[1]);
    m.setFloat("variable.cb", color[2]);
  }
  return m;
}

/** Spawn a particle emitter; silently ignores unloaded chunks and enforces a per-tick budget. */
export function particle(dim: Dimension, id: keyof typeof FX, at: Vector3, params?: { [k: string]: number | undefined },
  color?: RGB): void {
  if (particleBudget <= 0) return;
  particleBudget--;
  try {
    if (params || color) dim.spawnParticle(FX[id], at, vars(params ?? {}, color));
    else dim.spawnParticle(FX[id], at);
  } catch {
    /* location unloaded / out of world */
  }
}

export function sound(dim: Dimension, id: keyof typeof SND, at: Vector3, volume = 1, pitch = 1): void {
  try {
    dim.playSound(SND[id], at, { volume, pitch });
  } catch {
    /* ignore */
  }
}

export function soundTo(p: Player, id: keyof typeof SND, volume = 1, pitch = 1): void {
  try {
    p.playSound(SND[id], { volume, pitch });
  } catch {
    /* ignore */
  }
}

// ------------------------------------------------------------------ telegraph helpers (one emitter each)

export function ringTelegraph(dim: Dimension, center: Vector3, radius: number, seconds: number, color: RGB, fill = true): void {
  const at = { x: center.x, y: center.y + 0.15, z: center.z };
  particle(dim, "telegraph_ring", at, { radius, life: seconds }, color);
  if (fill) particle(dim, "telegraph_fill", at, { radius: radius * 0.92, life: seconds }, color);
}

export function lineTelegraph(dim: Dimension, from: Vector3, dir: Vector3, length: number, seconds: number, color: RGB): void {
  particle(dim, "telegraph_line", { x: from.x, y: from.y + 0.15, z: from.z },
    { dir_x: dir.x, dir_y: dir.y, dir_z: dir.z, length, life: seconds }, color);
}

export function shockwave(dim: Dimension, center: Vector3, speed: number, life: number, color: RGB): void {
  particle(dim, "shockwave", center, { speed, life }, color);
}
