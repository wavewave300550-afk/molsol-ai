import type { Vesper } from "./boss/controller.js";
import type { Minion } from "./boss/minions.js";

/** Live boss controllers by boss entity id. */
export const bosses = new Map<string, Vesper>();

/** Proxy hitbox entity id -> owner + part kind. */
export type PartKind = "prow" | "stern" | "heart";
export const parts = new Map<string, { owner: Vesper; kind: PartKind }>();

/** Helper entity id -> minion object. */
export const minions = new Map<string, Minion>();

/**
 * Damage the script forwards to a boss (from proxy hitboxes / reflected orbs) is already scaled;
 * the boss's own hurt handler must not scale it again. Entries live for two ticks.
 */
const ledger = new Map<string, { amount: number; until: number }[]>();

export function ledgerAdd(bossId: string, amount: number, tick: number): void {
  const list = ledger.get(bossId) ?? [];
  list.push({ amount, until: tick + 2 });
  ledger.set(bossId, list);
}

export function ledgerTake(bossId: string, amount: number, tick: number): boolean {
  const list = ledger.get(bossId);
  if (!list) return false;
  const i = list.findIndex((e) => e.until >= tick && Math.abs(e.amount - amount) < 0.01);
  if (i < 0) return false;
  list.splice(i, 1);
  if (!list.length) ledger.delete(bossId);
  return true;
}

export function ledgerPrune(tick: number): void {
  for (const [k, list] of ledger) {
    const keep = list.filter((e) => e.until >= tick);
    if (keep.length) ledger.set(k, keep);
    else ledger.delete(k);
  }
}

/** Feedback throttles keyed by "<entity>|<kind>". */
const throttles = new Map<string, number>();

export function throttle(key: string, tick: number, every: number): boolean {
  const last = throttles.get(key);
  if (last !== undefined && tick - last < every) return false;
  throttles.set(key, tick);
  if (throttles.size > 512) {
    for (const [k, t] of throttles) if (tick - t > 200) throttles.delete(k);
  }
  return true;
}

let worldTick = 0;
export const clock = {
  get now(): number {
    return worldTick;
  },
  advance(): void {
    worldTick++;
  },
};
