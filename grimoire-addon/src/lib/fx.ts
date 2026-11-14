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

/**
 * Screen shake (Bedrock /camerashake, positional) for the players within `radius` of `at`, weaker with
 * distance: an impact the caster can feel.  intensity ~0.1 = rumble, ~0.5 = slam, ~1 = detonation.
 */
export function shake(dim: Dimension, at: Vector3, radius: number, intensity: number, seconds: number): void {
  try {
    for (const p of dim.getPlayers({ location: at, maxDistance: radius })) {
      const d = Math.hypot(p.location.x - at.x, p.location.y - at.y, p.location.z - at.z);
      const k = Math.max(0, Math.min(1, 1 - d / radius));
      const i = Math.round(intensity * (0.4 + 0.6 * k) * 100) / 100;
      if (i < 0.02) continue;
      p.runCommand(`camerashake add @s ${i} ${Math.round(seconds * 100) / 100} positional`);
    }
  } catch {
    /* no players / command refused: the effect is optional */
  }
}

/**
 * A brief full-screen flash (camera fade to `rgb` 0..1 and back) for the players within `radius` of
 * `at`.  Keep it for the one climax of a spell: in 0.05 s, hold 0.05 s, out 0.6 s reads as a flash.
 */
export function flash(dim: Dimension, at: Vector3, radius: number, rgb: [number, number, number],
  fadeIn = 0.05, hold = 0.05, fadeOut = 0.6): void {
  try {
    for (const p of dim.getPlayers({ location: at, maxDistance: radius })) {
      p.camera.fade({ fadeColor: { red: rgb[0], green: rgb[1], blue: rgb[2] }, fadeTime: { fadeInTime: fadeIn, holdTime: hold, fadeOutTime: fadeOut } });
    }
  } catch {
    /* camera control unavailable: the effect is optional */
  }
}
