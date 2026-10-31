import { Entity, Player, Vector3, system } from "@minecraft/server";
import { burst, Hue } from "../core/fx.js";
import { chest, hurt, playersNear, victimsNear } from "../core/targets.js";
import { add, dist, v } from "../core/vec.js";
import { Action, Boss, S } from "../engine.js";

export function act(name: string, state: S, step: (age: number) => boolean, opts: { hold?: boolean; invulnerable?: boolean } = {}): Action {
  return { name, state, step, holdsPosition: opts.hold, invulnerable: opts.invulnerable };
}

export function ground(b: Boss, at: Vector3): Vector3 {
  return { ...b.groundBelow(at), y: b.groundBelow(at).y + 0.05 };
}

export function blast(b: Boss, at: Vector3, r: number, dmg: number, falloff = false): Entity[] {
  const hit = victimsNear(b.dim, at, r);
  for (const e of hit) hurt(e, falloff ? Math.max(1, dmg * (1 - dist(chest(e), at) / r)) : dmg, b.entity);
  return hit;
}

export function crowd(b: Boss, p: Vector3, r: number): number {
  return playersNear(b.dim, p, r).length;
}

export function flatDir(from: Vector3, to: Vector3): Vector3 {
  const dx = to.x - from.x;
  const dz = to.z - from.z;
  const l = Math.hypot(dx, dz) || 1;
  return { x: dx / l, y: 0, z: dz / l };
}

export function rotY(d: Vector3, deg: number): Vector3 {
  const r = (deg * Math.PI) / 180;
  return { x: d.x * Math.cos(r) - d.z * Math.sin(r), y: d.y, z: d.x * Math.sin(r) + d.z * Math.cos(r) };
}

/** Is player `p` looking at point `at` (within the given cosine)? */
export function looksAt(p: Player, at: Vector3, cos = 0.5): boolean {
  const eye = p.getHeadLocation();
  const d = { x: at.x - eye.x, y: at.y - eye.y, z: at.z - eye.z };
  const l = Math.hypot(d.x, d.y, d.z) || 1;
  const view = p.getViewDirection();
  return (d.x * view.x + d.y * view.y + d.z * view.z) / l > cos;
}

export function exhaust(b: Boss, ticks: number): void {
  b.exhaustedUntil = system.currentTick + ticks;
}

/** Simulated arcing projectile: moves a particle head along a parabola, calls onImpact at the end. */
export function arc(b: Boss, from: Vector3, to: Vector3, ticks: number, hue: Hue, height: number, onImpact: (at: Vector3) => void): (age: number) => boolean {
  return (age: number) => {
    if (age > ticks) return false;
    const t = age / ticks;
    const p = { x: from.x + (to.x - from.x) * t, y: from.y + (to.y - from.y) * t + Math.sin(t * Math.PI) * height, z: from.z + (to.z - from.z) * t };
    burst(b.dim, hue, p);
    if (age === ticks) onImpact(to);
    return age < ticks;
  };
}

export const up = (p: Vector3, h: number) => add(p, v(0, h, 0));
