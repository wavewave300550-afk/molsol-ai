import { Dimension, MolangVariableMap, Player, Vector3 } from "@minecraft/server";
import { add, v3 } from "./vec.js";

/** Particle / sound helpers. Everything is wrapped: effects must never break gameplay. */
export function particle(dim: Dimension, id: string, at: Vector3, size?: number): void {
  try {
    if (size !== undefined) {
      const m = new MolangVariableMap();
      m.setFloat("variable.size", size);
      dim.spawnParticle(id, at, m);
    } else {
      dim.spawnParticle(id, at);
    }
  } catch {
    // unloaded chunk etc.
  }
}

export function sound(dim: Dimension, id: string, at: Vector3, volume = 1, pitch = 1): void {
  try {
    dim.playSound(id, at, { volume, pitch });
  } catch {
    // ignore
  }
}

/** Flat ground ring marker (telegraph). */
export function ring(dim: Dimension, center: Vector3, radius: number, danger = true): void {
  particle(dim, danger ? "wh:warn_ring" : "wh:gold_ring", add(center, v3(0, 0.08, 0)), radius);
}

/** Dotted line telegraph. */
export function line(dim: Dimension, from: Vector3, to: Vector3, step = 1.0, id = "wh:warn_dot"): void {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const dz = to.z - from.z;
  const l = Math.sqrt(dx * dx + dy * dy + dz * dz);
  const n = Math.min(48, Math.max(1, Math.floor(l / step)));
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    particle(dim, id, v3(from.x + dx * t, from.y + dy * t, from.z + dz * t));
  }
}

/** Points on a horizontal circle. */
export function circle(dim: Dimension, center: Vector3, radius: number, id: string, maxPoints = 40, y = 0.1): void {
  const n = Math.max(8, Math.min(maxPoints, Math.round(radius * 2 * Math.PI / 1.4)));
  const off = Math.random() * Math.PI * 2;
  for (let i = 0; i < n; i++) {
    const a = off + (i / n) * Math.PI * 2;
    particle(dim, id, v3(center.x + Math.sin(a) * radius, center.y + y, center.z + Math.cos(a) * radius));
  }
}

export function shake(p: Player, intensity: number, seconds: number): void {
  try {
    p.runCommand(`camerashake add @s ${intensity.toFixed(2)} ${seconds.toFixed(2)} positional`);
  } catch {
    // cheats-off worlds still allow addon commands, but never fail on it
  }
}
