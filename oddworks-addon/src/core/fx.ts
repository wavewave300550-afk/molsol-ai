import { CameraShakeType, Dimension, MolangVariableMap, Player, Vector3, world } from "@minecraft/server";
import { add, dist, lerp, norm, scale, sub, v } from "./vec.js";

export interface Rgba {
  r: number;
  g: number;
  b: number;
  a?: number;
}

export interface FxVars {
  dir?: Vector3;
  len?: number;
  color?: Rgba;
  size?: number;
  count?: number;
  speed?: number;
  life?: number;
}

function molang(vars?: FxVars): MolangVariableMap | undefined {
  if (!vars) return undefined;
  const m = new MolangVariableMap();
  if (vars.dir) m.setVector3("variable.dir", vars.dir);
  if (vars.len !== undefined) m.setFloat("variable.len", vars.len);
  if (vars.color) m.setColorRGBA("variable.color", { red: vars.color.r, green: vars.color.g, blue: vars.color.b, alpha: vars.color.a ?? 1 });
  if (vars.size !== undefined) m.setFloat("variable.size", vars.size);
  if (vars.count !== undefined) m.setFloat("variable.count", vars.count);
  if (vars.speed !== undefined) m.setFloat("variable.speed", vars.speed);
  if (vars.life !== undefined) m.setFloat("variable.life", vars.life);
  return m;
}

/** World particle (seen by everyone nearby). Cosmetic: failures (unloaded chunk) are ignored. */
export function fx(dim: Dimension, id: string, at: Vector3, vars?: FxVars): void {
  try {
    dim.spawnParticle(id, at, molang(vars));
  } catch {
    /* cosmetic */
  }
}

/** Particle visible only to one player (first-person-only effects). */
export function fxFor(player: Player, id: string, at: Vector3, vars?: FxVars): void {
  try {
    player.spawnParticle(id, at, molang(vars));
  } catch {
    /* cosmetic */
  }
}

/** Particle visible to everyone except `except` (effects drawn on someone's face). */
export function fxOthers(except: Player, id: string, at: Vector3, vars?: FxVars): void {
  for (const p of world.getAllPlayers()) {
    if (p.id === except.id || p.dimension.id !== except.dimension.id) continue;
    if (dist(p.location, at) > 64) continue;
    fxFor(p, id, at, vars);
  }
}

/** Stretched billboard spanning a -> b (beams, lines, slash arcs). */
export function segment(dim: Dimension, id: string, a: Vector3, b: Vector3, extra?: FxVars): void {
  const d = sub(b, a);
  const l = Math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z);
  if (l < 0.01) return;
  fx(dim, id, lerp(a, b, 0.5), { ...extra, dir: scale(d, 1 / l), len: l });
}

export function sound(dim: Dimension, id: string, at: Vector3, pitch = 1, volume = 1): void {
  try {
    dim.playSound(id, at, { pitch, volume });
  } catch {
    /* cosmetic */
  }
}

export function soundTo(player: Player, id: string, pitch = 1, volume = 1): void {
  try {
    player.playSound(id, { pitch, volume });
  } catch {
    /* cosmetic */
  }
}

export function shake(player: Player, intensity: number, duration: number): void {
  try {
    player.camera.addShake({ intensity, duration, type: CameraShakeType.Positional });
  } catch {
    /* cosmetic */
  }
}

export function flash(player: Player, r: number, g: number, b: number, inT = 0.04, hold = 0.02, outT = 0.25): void {
  try {
    player.camera.fade({ fadeColor: { red: r, green: g, blue: b }, fadeTime: { fadeInTime: inT, holdTime: hold, fadeOutTime: outT } });
  } catch {
    /* cosmetic */
  }
}

/** Narrow / restore the field of view (focus effect while aiming the goggles or gripping the cane). */
export function focusFov(player: Player, on: boolean, fov = 60): void {
  try {
    player.runCommand(on ? `camera @s fov_set ${fov} 0.35 in_out_sine` : "camera @s fov_clear 0.2 out_sine");
  } catch {
    /* camera command unavailable - purely cosmetic */
  }
}

/** Points on a circle (XZ plane) around a centre. */
export function circle(c: Vector3, r: number, n: number, phase = 0): Vector3[] {
  const out: Vector3[] = [];
  for (let i = 0; i < n; i++) {
    const a = phase + (i / n) * Math.PI * 2;
    out.push(v(c.x + Math.cos(a) * r, c.y, c.z + Math.sin(a) * r));
  }
  return out;
}

/** Crescent slash drawn as tangent segments along an arc in the plane spanned by u/w. */
export function slashArc(dim: Dimension, centerPt: Vector3, u: Vector3, w: Vector3, radius: number, from: number, to: number,
  segments = 7, size = 1): void {
  const pts: Vector3[] = [];
  for (let i = 0; i <= segments; i++) {
    const a = from + ((to - from) * i) / segments;
    pts.push(add(centerPt, add(scale(u, Math.cos(a) * radius), scale(w, Math.sin(a) * radius))));
  }
  for (let i = 0; i < segments; i++) {
    const taper = Math.sin(((i + 0.5) / segments) * Math.PI);
    segment(dim, "oddworks:slash_seg", pts[i], pts[i + 1], { size: size * (0.4 + taper) });
  }
}

export const dirTo = (a: Vector3, b: Vector3): Vector3 => norm(sub(b, a));
