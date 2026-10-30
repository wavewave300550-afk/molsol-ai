import { Dimension, MolangVariableMap, Player, Vector3 } from "@minecraft/server";
import { add, dist, lerp, norm, sub, v } from "./vec.js";

/** Colours shipped as dim11:<kind>_<color> particles. */
export type Hue = "violet" | "cyan" | "gold" | "red" | "white" | "magenta" | "orange" | "yellow" | "green" | "blue";
export const SEVEN: Hue[] = ["red", "orange", "yellow", "green", "cyan", "blue", "violet"];

export function particle(dim: Dimension, id: string, at: Vector3, vars?: Record<string, number>): void {
  try {
    if (vars) {
      const m = new MolangVariableMap();
      for (const [k, val] of Object.entries(vars)) m.setFloat(`variable.${k}`, val);
      dim.spawnParticle(id, at, m);
    } else {
      dim.spawnParticle(id, at);
    }
  } catch {
    // unloaded chunk / outside world: cosmetic only
  }
}

export const mote = (dim: Dimension, c: Hue, at: Vector3) => particle(dim, `dim11:mote_${c}`, at);
export const burst = (dim: Dimension, c: Hue, at: Vector3) => particle(dim, `dim11:burst_${c}`, at);
export const sphereWave = (dim: Dimension, c: Hue, at: Vector3) => particle(dim, `dim11:sphere_${c}`, at);
export const groundWave = (dim: Dimension, c: Hue, at: Vector3) => particle(dim, `dim11:wave_${c}`, at);
export const column = (dim: Dimension, c: Hue, at: Vector3) => particle(dim, `dim11:column_${c}`, at);
/** Flat expanding ring sprite that reaches `radius` blocks after `life` seconds. */
export const ringWave = (dim: Dimension, c: Hue, at: Vector3, radius: number, life = 0.9) =>
  particle(dim, `dim11:ring_${c}`, at, { radius, life });
export const sigil = (dim: Dimension, at: Vector3, size: number, life: number) => particle(dim, "dim11:sigil", at, { size, life });
export const danger = (dim: Dimension, at: Vector3, size: number, life: number) => particle(dim, "dim11:danger", at, { size, life });
export const glyphs = (dim: Dimension, at: Vector3) => particle(dim, "dim11:glyphs", at);
export const flash = (dim: Dimension, at: Vector3) => particle(dim, "dim11:flash", at);
export const starfield = (dim: Dimension, at: Vector3) => particle(dim, "dim11:starfield", at);

export function beam(dim: Dimension, c: Hue, from: Vector3, to: Vector3, step = 0.4): void {
  const n = Math.max(1, Math.floor(dist(from, to) / step));
  for (let i = 0; i <= n; i++) mote(dim, c, lerp(from, to, i / n));
}

/** Double helix beam: two interleaved strands around the axis. */
export function helix(dim: Dimension, a: Hue, b: Hue, from: Vector3, to: Vector3, phase = 0, radius = 0.45): void {
  const d = sub(to, from);
  const L = dist(from, to);
  if (L < 0.01) return;
  const f = norm(d);
  const up = Math.abs(f.y) > 0.9 ? v(1, 0, 0) : v(0, 1, 0);
  const s1 = norm({ x: f.y * up.z - f.z * up.y, y: f.z * up.x - f.x * up.z, z: f.x * up.y - f.y * up.x });
  const s2 = { x: f.y * s1.z - f.z * s1.y, y: f.z * s1.x - f.x * s1.z, z: f.x * s1.y - f.y * s1.x };
  const n = Math.max(2, Math.floor(L / 0.35));
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const ang = t * L * 1.6 + phase;
    const c = Math.cos(ang) * radius;
    const s = Math.sin(ang) * radius;
    const p = lerp(from, to, t);
    mote(dim, a, add(p, { x: s1.x * c + s2.x * s, y: s1.y * c + s2.y * s, z: s1.z * c + s2.z * s }));
    mote(dim, b, add(p, { x: -s1.x * c - s2.x * s, y: -s1.y * c - s2.y * s, z: -s1.z * c - s2.z * s }));
  }
}

/** Vibrating string: a sine standing wave along the segment. */
export function stringWave(dim: Dimension, c: Hue, from: Vector3, to: Vector3, phase: number, amp = 0.6): void {
  const L = dist(from, to);
  const n = Math.max(2, Math.floor(L / 0.3));
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const p = lerp(from, to, t);
    const w = Math.sin(t * Math.PI * 6) * Math.sin(phase) * amp;
    mote(dim, c, add(p, v(0, w, 0)));
  }
}

export function moteRing(dim: Dimension, c: Hue, center: Vector3, radius: number, points?: number, phase = 0): void {
  const n = points ?? Math.max(10, Math.floor(radius * 6));
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2 + phase;
    mote(dim, c, add(center, v(Math.cos(a) * radius, 0, Math.sin(a) * radius)));
  }
}

/** Vertical membrane (brane) plane centred at `c`, spanning `width` along `axis` and `height` up. */
export function branePlane(dim: Dimension, c: Hue, center: Vector3, axis: Vector3, width: number, height: number, phase: number): void {
  for (let w = -width / 2; w <= width / 2; w += 1.6) {
    for (let h = 0; h <= height; h += 1.6) {
      const ripple = Math.sin(w * 0.6 + h * 0.4 + phase) * 0.35;
      mote(dim, c, { x: center.x + axis.x * w + axis.z * ripple, y: center.y + h, z: center.z + axis.z * w - axis.x * ripple });
    }
  }
}

export function sound(dim: Dimension, id: string, at: Vector3, volume = 1, pitch = 1): void {
  try {
    dim.playSound(id, at, { volume, pitch });
  } catch {
    // ignore
  }
}

// --------------------------------------------------------------------------- camera

export function fade(p: Player, rgb: [number, number, number], fadeIn: number, hold: number, fadeOut: number): void {
  try {
    p.camera.fade({ fadeColor: { red: rgb[0], green: rgb[1], blue: rgb[2] }, fadeTime: { fadeInTime: fadeIn, holdTime: hold, fadeOutTime: fadeOut } });
  } catch {
    // camera API unavailable in this context
  }
}

export function shake(p: Player, intensity: number, seconds: number): void {
  try {
    p.runCommand(`camerashake add @s ${intensity.toFixed(2)} ${seconds.toFixed(1)} positional`);
  } catch {
    // ignore
  }
}

export function title(p: Player, main: string, sub: string, stay = 50): void {
  p.onScreenDisplay.setTitle(main, { subtitle: sub, fadeInDuration: 5, stayDuration: stay, fadeOutDuration: 15 });
}
