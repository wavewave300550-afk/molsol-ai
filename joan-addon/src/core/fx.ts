import { CameraShakeType, Dimension, MolangVariableMap, Player, RGBA, Vector3 } from "@minecraft/server";
import { add, dist, len, norm, sub, v, V3 } from "./vec.js";

/** Running counters (used by the smoke test to keep effects within a mobile budget). */
export const fxStats = { particles: 0, sounds: 0, dropped: 0 };

/** Hard cap of particle emitters per tick (phones): bursts beyond it are skipped. */
const BUDGET = 110;
let budget = BUDGET;
export function resetFxBudget(): void {
  budget = BUDGET;
}

export interface FxOpts {
  speed?: number;
  life?: number;
  color?: RGBA;
  size?: number;
  r0?: number;
  r1?: number;
  h?: number;
}

function vars(dir: V3 | undefined, length: number, o: FxOpts): MolangVariableMap {
  const m = new MolangVariableMap();
  m.setVector3("variable.dir", dir ?? { x: 0, y: 1, z: 0 });
  m.setFloat("variable.len", length);
  m.setFloat("variable.speed", o.speed ?? 4);
  m.setFloat("variable.life", o.life ?? 1);
  m.setFloat("variable.size", o.size ?? 1);
  m.setFloat("variable.r0", o.r0 ?? 1);
  m.setFloat("variable.r1", o.r1 ?? 3);
  m.setFloat("variable.h", o.h ?? 6);
  m.setColorRGBA("variable.color", o.color ?? { red: 1, green: 0.9, blue: 0.6, alpha: 1 });
  return m;
}

/** Spawn a particle effect; failures (unloaded chunk, outside world) are cosmetic and ignored. */
export function emit(dim: Dimension, effect: string, at: Vector3, o: FxOpts = {}, dir?: V3, length = 1): void {
  if (budget <= 0) {
    fxStats.dropped++;
    return;
  }
  budget--;
  try {
    dim.spawnParticle(effect, at, vars(dir, length, o));
    fxStats.particles++;
  } catch {
    // ignore
  }
}

/** Segment emitter from a to b (road ribbons). */
export function emitSegment(dim: Dimension, effect: string, a: V3, b: V3, o: FxOpts): void {
  const d = sub(b, a);
  const l = len(d);
  if (l < 0.05) return;
  emit(dim, effect, a, o, norm(d), l);
}

export function sound(dim: Dimension, id: string, at: Vector3, volume = 1, pitch = 1): void {
  try {
    dim.playSound(id, at, { volume, pitch });
    fxStats.sounds++;
  } catch {
    // ignore
  }
}

export function ring(dim: Dimension, center: V3, r0: number, r1: number, life: number, color: RGBA): void {
  emit(dim, "joan:ring", center, { r0: r0 * 2, r1: r1 * 2, life, color });
}

export function sigil(dim: Dimension, center: V3, size: number, life: number, color: RGBA, falseMark = false): void {
  emit(dim, falseMark ? "joan:sigil_false" : "joan:sigil", center, { size, life, color });
}

export function burst(dim: Dimension, at: V3, color: RGBA, size = 1): void {
  emit(dim, "joan:burst", at, { color, size });
}

export function flash(dim: Dimension, at: V3, color: RGBA, size = 2.5, life = 0.35): void {
  emit(dim, "joan:flash", at, { color, size, life });
}

export function pillar(dim: Dimension, base: V3, height: number, color: RGBA, life = 0.6, size = 1): void {
  emit(dim, "joan:pillar", base, { h: height, color, life, size });
}

/** Banner swing streaks along an arc around `center` (radius r) from yaw a0 to a1 (radians). */
export function swingArc(dim: Dimension, center: V3, r: number, a0: number, a1: number, y: number, color: RGBA): void {
  const steps = 6;
  for (let i = 0; i < steps; i++) {
    const t0 = a0 + ((a1 - a0) * i) / steps;
    const t1 = a0 + ((a1 - a0) * (i + 1)) / steps;
    const p0 = v(center.x + Math.cos(t0) * r, center.y + y, center.z + Math.sin(t0) * r);
    const p1 = v(center.x + Math.cos(t1) * r, center.y + y, center.z + Math.sin(t1) * r);
    emitSegment(dim, "joan:swing", p0, p1, { color, speed: 3, size: 1.2 });
  }
}

export function shake(players: Player[], intensity: number, seconds: number): void {
  for (const p of players) {
    try {
      p.camera.addShake({ intensity, duration: seconds, type: CameraShakeType.Positional });
    } catch {
      // camera API unavailable for this player
    }
  }
}

export function title(players: Player[], main: string, sub_: string, stay = 60): void {
  for (const p of players) {
    try {
      p.onScreenDisplay.setTitle(main, { fadeInDuration: 10, stayDuration: stay, fadeOutDuration: 20, subtitle: sub_ });
    } catch {
      // ignore
    }
  }
}

export function actionbar(p: Player, text: string): void {
  try {
    p.onScreenDisplay.setActionBar(text);
  } catch {
    // ignore
  }
}

export function center(e: { location: Vector3 }, h = 1.0): V3 {
  return add(e.location, { x: 0, y: h, z: 0 });
}

export { dist };
