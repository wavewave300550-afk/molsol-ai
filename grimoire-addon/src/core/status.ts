import { Dimension, Entity, system } from "@minecraft/server";
import { Fx, spawnFx } from "./fx";
import { effect, pin, release } from "./combat";
import { V3, add } from "./vec";

/**
 * Central registry for crowd-control states (binds, freezes, restraints). One place pins the
 * target every tick, keeps the visual shell attached, and *always* restores movement when the
 * state ends (expiry, target death, caster leaving, spell cleanup).
 */
export interface Bind {
  id: number;
  ownerId: string;
  target: Entity;
  until: number;
  anchor?: V3;
  shell?: Fx;
  shellOffset: V3;
  slowAmp: number;
  pull?: V3;
  pullSpeed: number;
  ended: boolean;
}

const binds = new Map<number, Bind>();
let nextBind = 1;

export interface BindOptions {
  /** Construct that follows the target while bound (ice shell, chains...). */
  shell?: string;
  shellInit?: { size?: number; variant?: number; yaw?: number };
  shellOffset?: V3;
  /** Pin the target in place (default true). */
  pin?: boolean;
  /** Slowness amplifier re-applied while bound (default 7 = immobile). */
  slowAmp?: number;
  /** Move the anchor toward this point every tick (pulling restraints). */
  pull?: V3;
  pullSpeed?: number;
}

export function bind(ownerId: string, dim: Dimension, target: Entity, ticks: number, o: BindOptions = {}): Bind | undefined {
  if (!target.isValid) return undefined;
  // refresh an existing bind of the same owner instead of stacking
  for (const b of binds.values()) {
    if (b.target.id === target.id && b.ownerId === ownerId && !b.ended) {
      b.until = Math.max(b.until, system.currentTick + ticks);
      return b;
    }
  }
  const b: Bind = {
    id: nextBind++,
    ownerId,
    target,
    until: system.currentTick + ticks,
    anchor: o.pin === false ? undefined : { ...target.location },
    shellOffset: o.shellOffset ?? { x: 0, y: 0, z: 0 },
    slowAmp: o.slowAmp ?? 7,
    pull: o.pull,
    pullSpeed: o.pullSpeed ?? 0.12,
    ended: false,
  };
  if (o.shell) b.shell = spawnFx(ownerId, dim, o.shell, add(target.location, b.shellOffset), { phase: 1, ...(o.shellInit ?? {}) });
  effect(target, "slowness", Math.min(ticks, 20 * 30), b.slowAmp);
  binds.set(b.id, b);
  return b;
}

export function endBind(b: Bind | undefined, shatter = true): void {
  if (!b || b.ended) return;
  b.ended = true;
  binds.delete(b.id);
  if (b.target.isValid) release(b.target);
  if (b.shell) {
    if (shatter) b.shell.phase(3);
    const s = b.shell;
    system.runTimeout(() => s.dissolve(10), shatter ? 6 : 1);
  }
}

export function endBindsOf(ownerId: string): void {
  for (const b of [...binds.values()]) if (b.ownerId === ownerId) endBind(b, false);
}

export function isBound(e: Entity): boolean {
  for (const b of binds.values()) if (b.target.id === e.id && !b.ended) return true;
  return false;
}

export function tickBinds(tick: number): void {
  for (const b of [...binds.values()]) {
    if (!b.target.isValid || tick >= b.until) {
      endBind(b, b.target.isValid);
      continue;
    }
    if (b.pull && b.anchor) {
      const dx = b.pull.x - b.anchor.x, dz = b.pull.z - b.anchor.z;
      const d = Math.hypot(dx, dz);
      if (d > 0.4) {
        const k = Math.min(b.pullSpeed, d) / d;
        b.anchor = { x: b.anchor.x + dx * k, y: b.anchor.y, z: b.anchor.z + dz * k };
      }
    }
    if (b.anchor) pin(b.target, b.anchor, 0.25);
    if (tick % 20 === 0) effect(b.target, "slowness", 40, b.slowAmp);
    b.shell?.follow(b.target, b.shellOffset, 0);
  }
}

export function bindCount(): number {
  return binds.size;
}
