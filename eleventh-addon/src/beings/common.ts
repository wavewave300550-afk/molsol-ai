import { Entity, Player, Vector3 } from "@minecraft/server";
import { danger, Hue } from "../core/fx.js";
import { chest, hurt, playersNear, victimsNear } from "../core/targets.js";
import { add, dist, v } from "../core/vec.js";
import { Action, AnimState, Being } from "../engine.js";

export function act(name: string, state: AnimState, step: (age: number) => boolean, holdsPosition = false): Action {
  return { name, state, step, holdsPosition };
}

/** Ground point under a location (searches down a few blocks for a solid block). */
export function groundAt(b: Being, at: Vector3): Vector3 {
  try {
    const hit = b.dim.getBlockFromRay(add(at, v(0, 1, 0)), { x: 0, y: -1, z: 0 }, { maxDistance: 24, includeLiquidBlocks: true });
    if (hit) return { x: at.x, y: hit.block.location.y + 1.05, z: at.z };
  } catch {
    // outside world
  }
  return { x: at.x, y: Math.floor(at.y) + 0.05, z: at.z };
}

/** Red telegraph on the floor, then `onImpact` once. */
export function telegraphCircle(b: Being, at: Vector3, radius: number, ticks: number): void {
  danger(b.dim, groundAt(b, at), radius * 2, ticks / 20);
}

/** Damage everything in a sphere once; returns the entities hit. */
export function blast(b: Being, at: Vector3, radius: number, damage: number, falloff = false): Entity[] {
  const hit = victimsNear(b.dim, at, radius);
  for (const e of hit) {
    const d = dist(chest(e), at);
    hurt(e, falloff ? Math.max(1, damage * (1 - d / radius)) : damage, b.entity);
  }
  return hit;
}

export function nearestPlayers(b: Being, radius: number): Player[] {
  return playersNear(b.dim, b.entity.location, radius).sort((x, y) => dist(x.location, b.entity.location) - dist(y.location, b.entity.location));
}

/** How many players stand within `r` of `p` (used to prefer area attacks on clusters). */
export function crowd(b: Being, p: Vector3, r: number): number {
  return playersNear(b.dim, p, r).length;
}

export const HIT_ONCE = (): Set<string> => new Set<string>();

export function colorPair(h: Hue): [Hue, Hue] {
  return [h, "white"];
}
