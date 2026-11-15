/** Particles, sounds, camera shake and other presentation helpers. */
import { CameraShakeType, Dimension, MolangVariableMap, Player, Vector3 } from "@minecraft/server";
import { V3 } from "./vec.js";

export interface FxVars {
  size?: number;
  life?: number;
  radius?: number;
  gap?: number;
  gapDir?: number;
  intensity?: number;
  /** direction + speed -> variable.dir.{speed,direction_x,direction_y,direction_z} */
  dir?: V3;
  speed?: number;
}

let fxBudget = 0;
const FX_PER_TICK = 160;

/** Called once per tick by the manager: limits particle spam. */
export function resetFxBudget(): void {
  fxBudget = FX_PER_TICK;
}

export function particle(dim: Dimension, id: string, loc: Vector3, vars?: FxVars): boolean {
  if (fxBudget <= 0) return false;
  fxBudget--;
  try {
    if (vars) {
      const m = new MolangVariableMap();
      if (vars.size !== undefined) m.setFloat("variable.size", vars.size);
      if (vars.life !== undefined) m.setFloat("variable.life", vars.life);
      if (vars.radius !== undefined) m.setFloat("variable.radius", vars.radius);
      if (vars.gap !== undefined) m.setFloat("variable.gap", vars.gap);
      if (vars.gapDir !== undefined) m.setFloat("variable.gap_dir", vars.gapDir);
      if (vars.intensity !== undefined) m.setFloat("variable.intensity", vars.intensity);
      if (vars.dir) m.setSpeedAndDirection("variable.dir", vars.speed ?? 1, vars.dir);
      dim.spawnParticle(id, loc, m);
    } else dim.spawnParticle(id, loc);
    return true;
  } catch {
    return false;
  }
}

export function sound(dim: Dimension, id: string, loc: Vector3, volume = 1, pitch = 1): void {
  try {
    dim.playSound(id, loc, { volume, pitch });
  } catch {
    /* sound ids are validated at build time; ignore unloaded-chunk failures */
  }
}

export function shake(players: Player[], intensity: number, seconds: number, rotational = false): void {
  for (const p of players) {
    try {
      p.camera.addShake({ intensity: Math.min(4, intensity), duration: seconds, type: rotational ? CameraShakeType.Rotational : CameraShakeType.Positional });
    } catch {
      /* camera can be unavailable for a player that is dying/respawning */
    }
  }
}

/** Shake scaled by distance from an epicentre. */
export function quake(players: Player[], at: V3, intensity: number, seconds: number, radius = 60): void {
  for (const p of players) {
    const d = Math.hypot(p.location.x - at.x, p.location.y - at.y, p.location.z - at.z);
    const k = Math.max(0, 1 - d / radius);
    if (k > 0.05) shake([p], intensity * k, seconds);
  }
}

export function title(players: Player[], main: string, sub = "", stay = 50, fadeIn = 8, fadeOut = 16): void {
  for (const p of players) {
    try {
      p.onScreenDisplay.setTitle(main, { subtitle: sub, fadeInDuration: fadeIn, stayDuration: stay, fadeOutDuration: fadeOut });
    } catch {
      /* ignore */
    }
  }
}

export function actionbar(players: Player[], text: string): void {
  for (const p of players) {
    try {
      p.onScreenDisplay.setActionBar(text);
    } catch {
      /* ignore */
    }
  }
}

/** Particles along a line (one emitter every `step` blocks). */
export function line(dim: Dimension, id: string, a: V3, b: V3, step: number, vars?: FxVars): void {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const dz = b.z - a.z;
  const L = Math.sqrt(dx * dx + dy * dy + dz * dz);
  const n = Math.max(1, Math.floor(L / step));
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    particle(dim, id, { x: a.x + dx * t, y: a.y + dy * t, z: a.z + dz * t }, vars);
  }
}
