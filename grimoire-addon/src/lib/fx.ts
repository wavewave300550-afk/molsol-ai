import { Dimension, MolangVariableMap, Vector3, system } from "@minecraft/server";
import { CONFIG } from "../config/global";
import { inWorld } from "./bounds";
import { NS } from "./scene";

let budgetTick = -1;
let budget = 0;

function take(n = 1): boolean {
  if (system.currentTick !== budgetTick) { budgetTick = system.currentTick; budget = CONFIG.limits.maxParticlesPerTick; }
  if (budget < n) return false;
  budget -= n;
  return true;
}

/** Spawn one particle effect ("name" -> grimoire:name).  Silently skipped when over budget. */
export function particle(dim: Dimension, id: string, loc: Vector3, vars?: MolangVariableMap): void {
  if (!take()) return;
  try { dim.spawnParticle(id.includes(":") ? id : `${NS}:${id}`, inWorld(dim, loc), vars); } catch { /* unloaded */ }
}

/** n particles evenly on a horizontal ring. */
export function ring(dim: Dimension, id: string, center: Vector3, radius: number, n: number, phaseDeg = 0): void {
  for (let i = 0; i < n; i++) {
    const a = ((phaseDeg + (360 * i) / n) * Math.PI) / 180;
    particle(dim, id, { x: center.x + Math.cos(a) * radius, y: center.y, z: center.z + Math.sin(a) * radius });
  }
}

/** n particles along a segment. */
export function line(dim: Dimension, id: string, a: Vector3, b: Vector3, n: number): void {
  for (let i = 0; i < n; i++) {
    const t = n === 1 ? 0.5 : i / (n - 1);
    particle(dim, id, { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t });
  }
}

/** n particles scattered in a sphere (deterministic golden-angle spiral, no RNG spikes). */
export function burst(dim: Dimension, id: string, center: Vector3, radius: number, n: number): void {
  for (let i = 0; i < n; i++) {
    const y = 1 - (2 * (i + 0.5)) / n;
    const r = Math.sqrt(1 - y * y) * radius;
    const a = i * 2.39996;
    particle(dim, id, { x: center.x + Math.cos(a) * r, y: center.y + y * radius, z: center.z + Math.sin(a) * r });
  }
}

/** Play a positional sound ("name" -> grimoire.name). */
export function sound(dim: Dimension, id: string, loc: Vector3, volume = 1, pitch = 1): void {
  try { dim.playSound(id.includes(".") ? id : `${NS}.${id}`, inWorld(dim, loc), { volume, pitch }); } catch { /* unloaded */ }
}

/** Colour helper for particles that read variable.color. */
export function tint(r: number, g: number, b: number, a = 1): MolangVariableMap {
  const m = new MolangVariableMap();
  m.setColorRGBA("variable.color", { red: r, green: g, blue: b, alpha: a });
  return m;
}
