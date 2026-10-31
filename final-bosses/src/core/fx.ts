import { Dimension, MolangVariableMap, Player, Vector3 } from "@minecraft/server";
import { add, dist, lerp, v } from "./vec.js";

/** Additive colours shipped as fb:<kind>_<hue>. */
export type Hue = "void" | "gold" | "orange" | "blue" | "star" | "flame" | "green" | "red" | "silver" | "white" | "cyan";
/** Alpha-blended smoke colours shipped as fb:smoke_<tone> (dark effects additive blending cannot show). */
export type Tone = "void" | "dust" | "spore" | "ash";

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
    // unloaded chunk / outside the world: purely cosmetic
  }
}

export const mote = (d: Dimension, h: Hue, at: Vector3) => particle(d, `fb:mote_${h}`, at);
export const burst = (d: Dimension, h: Hue, at: Vector3) => particle(d, `fb:burst_${h}`, at);
export const sphereWave = (d: Dimension, h: Hue, at: Vector3) => particle(d, `fb:sphere_${h}`, at);
export const groundWave = (d: Dimension, h: Hue, at: Vector3) => particle(d, `fb:wave_${h}`, at);
export const column = (d: Dimension, h: Hue, at: Vector3) => particle(d, `fb:column_${h}`, at);
export const ringWave = (d: Dimension, h: Hue, at: Vector3, radius: number, life = 0.8) => particle(d, `fb:ring_${h}`, at, { radius, life });
export const smoke = (d: Dimension, t: Tone, at: Vector3) => particle(d, `fb:smoke_${t}`, at);
export const debris = (d: Dimension, at: Vector3) => particle(d, "fb:debris", at);
export const shards = (d: Dimension, at: Vector3) => particle(d, "fb:shards", at);
export const embers = (d: Dimension, at: Vector3) => particle(d, "fb:embers", at);
export const danger = (d: Dimension, at: Vector3, size: number, life: number) => particle(d, "fb:danger", at, { size, life });
export const safe = (d: Dimension, at: Vector3, size: number, life: number) => particle(d, "fb:safe", at, { size, life });
export const sigil = (d: Dimension, at: Vector3, size: number, life: number) => particle(d, "fb:sigil", at, { size, life });
export const flash = (d: Dimension, at: Vector3) => particle(d, "fb:flash", at);
export const blackhole = (d: Dimension, at: Vector3, size: number, life: number) => particle(d, "fb:blackhole", at, { size, life });

export function beam(dim: Dimension, h: Hue, from: Vector3, to: Vector3, step = 0.4): void {
  const n = Math.max(1, Math.floor(dist(from, to) / step));
  for (let i = 0; i <= n; i++) mote(dim, h, lerp(from, to, i / n));
}

export function dangerLine(dim: Dimension, from: Vector3, to: Vector3, width: number, life: number): void {
  const n = Math.max(1, Math.floor(dist(from, to) / (width * 0.9)));
  for (let i = 0; i <= n; i++) danger(dim, lerp(from, to, i / n), width, life);
}

export function moteRing(dim: Dimension, h: Hue, center: Vector3, radius: number, points?: number, phase = 0): void {
  const n = points ?? Math.max(10, Math.floor(radius * 5));
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2 + phase;
    mote(dim, h, add(center, v(Math.cos(a) * radius, 0, Math.sin(a) * radius)));
  }
}

export function sound(dim: Dimension, id: string, at: Vector3, volume = 1, pitch = 1): void {
  try {
    dim.playSound(id, at, { volume, pitch });
  } catch {
    // ignore
  }
}

export function fade(p: Player, rgb: [number, number, number], fadeIn: number, hold: number, fadeOut: number): void {
  try {
    p.camera.fade({ fadeColor: { red: rgb[0], green: rgb[1], blue: rgb[2] }, fadeTime: { fadeInTime: fadeIn, holdTime: hold, fadeOutTime: fadeOut } });
  } catch {
    // camera unavailable
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
