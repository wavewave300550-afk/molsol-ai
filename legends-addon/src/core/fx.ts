/**
 * Visual / audio effects.
 *
 * Every particle effect in the resource pack is parameterised by Molang
 * variables (size, lifetime, colour, count, speed...) so one definition
 * serves every boss. Telegraphs follow one colour language across all six
 * fights: RED = damage will land here, GOLD = safe zone. They are flat decals
 * on the ground: an outline plus a fill that grows until the moment of impact,
 * so players read *where* and *when* without any text.
 */
import { Dimension, MolangVariableMap, Player, RGB, Vector3 } from "@minecraft/server";
import { add, dirOfYaw, rotY, scale, v, yawOf } from "./vec.js";

export type Col = RGB;
export const C = {
  danger: { red: 1.0, green: 0.28, blue: 0.14 },
  warn: { red: 1.0, green: 0.62, blue: 0.12 },
  safe: { red: 1.0, green: 0.86, blue: 0.32 },
  white: { red: 1.0, green: 1.0, blue: 1.0 },
  holy: { red: 1.0, green: 0.94, blue: 0.68 },
  gold: { red: 1.0, green: 0.78, blue: 0.25 },
  bronze: { red: 0.53, green: 0.83, blue: 0.66 },
  ember: { red: 1.0, green: 0.45, blue: 0.12 },
  hunger: { red: 0.32, green: 0.2, blue: 0.38 },
  venom: { red: 0.45, green: 1.0, blue: 0.32 },
  frost: { red: 0.62, green: 0.9, blue: 1.0 },
  root: { red: 0.42, green: 0.3, blue: 0.18 },
  fire: { red: 1.0, green: 0.52, blue: 0.1 },
  wind: { red: 0.78, green: 1.0, blue: 0.93 },
  star: { red: 1.0, green: 0.96, blue: 0.75 },
  moon: { red: 0.85, green: 0.9, blue: 1.0 },
  aurora: { red: 0.78, green: 0.62, blue: 1.0 },
  pink: { red: 1.0, green: 0.72, blue: 0.92 },
  sky: { red: 0.55, green: 0.85, blue: 1.0 },
  fox: { red: 0.25, green: 0.66, blue: 1.0 },
  crimson: { red: 0.85, green: 0.07, blue: 0.18 },
  beryl: { red: 0.36, green: 0.86, blue: 0.72 },
  dark: { red: 0.08, green: 0.06, blue: 0.1 },
} as const;

function vars(col: Col, extra: Record<string, number>): MolangVariableMap {
  const m = new MolangVariableMap();
  m.setColorRGB("variable.color", col);
  for (const k in extra) m.setFloat(`variable.${k}`, extra[k]);
  return m;
}

export function spawn(dim: Dimension, id: string, at: Vector3, map?: MolangVariableMap): void {
  try {
    dim.spawnParticle(id, at, map);
  } catch {
    // unloaded chunk / outside the world: cosmetic only
  }
}

const lift = (p: Vector3, h = 0.06): Vector3 => ({ x: p.x, y: p.y + h, z: p.z });

// ------------------------------------------------------------------ telegraphs

/** Circular danger (or safe) zone: pulsing outline + fill that grows until impact. */
export function teleCircle(dim: Dimension, center: Vector3, radius: number, ticks: number, col: Col = C.danger): void {
  const life = Math.max(0.1, ticks / 20);
  spawn(dim, "legends:tele_ring", lift(center), vars(col, { size: radius, life }));
  spawn(dim, "legends:tele_fill", lift(center, 0.05), vars(col, { size: radius, life }));
}

export const teleSafe = (dim: Dimension, center: Vector3, radius: number, ticks: number): void =>
  teleCircle(dim, center, radius, ticks, C.safe);

/** Rectangular strip (line attacks) drawn as a dotted floor marking. */
export function teleLine(dim: Dimension, from: Vector3, dir: Vector3, length: number, width: number, ticks: number, col: Col = C.danger): void {
  const life = Math.max(0.1, ticks / 20);
  const yaw = yawOf(dir);
  const fwd = dirOfYaw(yaw);
  const side = dirOfYaw(yaw + 90);
  const cols = Math.max(1, Math.round(width / 1.3));
  const step = 1.3;
  for (let d = 0.8; d <= length; d += step) {
    for (let c = 0; c < cols; c++) {
      const off = cols === 1 ? 0 : (c / (cols - 1) - 0.5) * (width - 0.6);
      const p = add(add(from, scale(fwd, d)), scale(side, off));
      spawn(dim, "legends:tele_dot", lift(p), vars(col, { size: 0.42, life }));
    }
  }
}

/** Cone telegraph (apex at the attacker) drawn as dotted arcs. */
export function teleCone(dim: Dimension, apex: Vector3, dir: Vector3, angle: number, range: number, ticks: number, col: Col = C.danger): void {
  const life = Math.max(0.1, ticks / 20);
  for (let r = 1.6; r <= range; r += 1.5) {
    const n = Math.max(2, Math.round(((angle * Math.PI) / 180) * r / 1.4));
    for (let i = 0; i <= n; i++) {
      const a = -angle / 2 + (angle * i) / n;
      const p = add(apex, scale(rotY(dir, a), r));
      spawn(dim, "legends:tele_dot", lift(p), vars(col, { size: r >= range - 1.5 ? 0.55 : 0.4, life }));
    }
  }
}

/** Donut (ring) telegraph between two radii: danger outside the inner circle. */
export function teleRing(dim: Dimension, center: Vector3, inner: number, outer: number, ticks: number, col: Col = C.danger): void {
  const life = Math.max(0.1, ticks / 20);
  spawn(dim, "legends:tele_ring", lift(center), vars(col, { size: outer, life }));
  spawn(dim, "legends:tele_ring", lift(center), vars(C.safe, { size: inner, life }));
  for (let r = inner + 1; r < outer; r += 1.6) {
    const n = Math.round((Math.PI * 2 * r) / 1.8);
    for (let i = 0; i < n; i++) {
      const a = (i / n) * 360;
      spawn(dim, "legends:tele_dot", lift(add(center, scale(dirOfYaw(a), r))), vars(col, { size: 0.38, life }));
    }
  }
}

// ------------------------------------------------------------------ impact & ambience

export function shock(dim: Dimension, center: Vector3, radius: number, ticks: number, col: Col): void {
  spawn(dim, "legends:shock", lift(center, 0.12), vars(col, { size: radius, life: Math.max(0.1, ticks / 20) }));
}

export function pillar(dim: Dimension, base: Vector3, height: number, width: number, ticks: number, col: Col): void {
  spawn(dim, "legends:pillar", base, vars(col, { size: width, height, life: Math.max(0.1, ticks / 20) }));
}

export function burst(dim: Dimension, at: Vector3, col: Col, count = 16, speed = 4, size = 0.22, radius = 0.25): void {
  spawn(dim, "legends:burst", at, vars(col, { count, speed, size, radius }));
}

export function mote(dim: Dimension, at: Vector3, col: Col, size = 0.18, life = 0.6): void {
  spawn(dim, "legends:mote", at, vars(col, { count: 1, speed: 0.1, size, radius: 0, life }));
}

export function glint(dim: Dimension, at: Vector3, col: Col, size = 1.2): void {
  spawn(dim, "legends:glint", at, vars(col, { count: 1, speed: 0, size, radius: 0 }));
}

type Deco = "smoke" | "feather" | "petal" | "flame" | "rune" | "drip" | "shard";
export function deco(dim: Dimension, kind: Deco, at: Vector3, col: Col, count = 6, radius = 1, size = 0.3, speed = 1): void {
  spawn(dim, `legends:${kind}`, at, vars(col, { count, radius, size, speed }));
}

export function spiralMark(dim: Dimension, at: Vector3, col: Col, size: number, ticks: number): void {
  spawn(dim, "legends:spiral", lift(at, 0.1), vars(col, { size, life: Math.max(0.1, ticks / 20) }));
}

/** A client-simulated bullet: one particle flying in a straight line (server checks hits analytically). */
export function bullet(dim: Dimension, from: Vector3, dir: Vector3, speed: number, ticks: number, col: Col, size = 0.35): void {
  const m = vars(col, { size, life: ticks / 20 });
  m.setSpeedAndDirection("variable.dir", speed, dir);
  spawn(dim, "legends:bullet", from, m);
}

/** Beam drawn as a stream of fast bullets (cheap: a few particles per call). */
export function beam(dim: Dimension, from: Vector3, to: Vector3, col: Col, size = 0.45): void {
  const d = { x: to.x - from.x, y: to.y - from.y, z: to.z - from.z };
  const l = Math.hypot(d.x, d.y, d.z);
  if (l < 0.1) return;
  const dir = scale(d, 1 / l);
  const speed = 60;
  const ticks = Math.max(1, Math.round((l / speed) * 20));
  for (let k = 0; k < 3; k++) bullet(dim, add(from, scale(dir, (k * l) / 3)), dir, speed, Math.max(1, Math.round(ticks * (1 - k / 3))), col, size);
}

export function ring(dim: Dimension, center: Vector3, radius: number, col: Col, n?: number): void {
  const count = n ?? Math.max(8, Math.round(radius * 3));
  for (let i = 0; i < count; i++) mote(dim, add(center, scale(dirOfYaw((i / count) * 360), radius)), col, 0.22, 0.5);
}

// ------------------------------------------------------------------ sound & camera

export function sound(dim: Dimension, id: string, at: Vector3, volume = 1, pitch = 1): void {
  try {
    dim.playSound(id, at, { volume, pitch });
  } catch {
    // ignore
  }
}

export function shake(players: Player[], intensity = 0.3, seconds = 0.5): void {
  const i = Math.max(0.05, Math.min(1, intensity)).toFixed(2);
  const s = Math.max(0.1, seconds).toFixed(2);
  for (const p of players) {
    try {
      p.runCommand(`camerashake add @s ${i} ${s} positional`);
    } catch {
      // camera shake unavailable: purely cosmetic
    }
  }
}

/** Very short full-screen flash used only at the climax of an ultimate (never held). */
export function flash(players: Player[], col: Col = C.white): void {
  for (const p of players) {
    try {
      p.camera.fade({ fadeColor: col, fadeTime: { fadeInTime: 0.08, holdTime: 0.0, fadeOutTime: 0.45 } });
    } catch {
      // ignore
    }
  }
}

export const up = (p: Vector3, h: number): Vector3 => v(p.x, p.y + h, p.z);
