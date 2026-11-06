// Small helpers shared by every dragon.
import { system } from "@minecraft/server";

export const TPS = 20;
/** seconds -> ticks */
export const sec = (s) => Math.round(s * TPS);
export const now = () => system.currentTick;
export const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
export const lerp = (a, b, t) => a + (b - a) * t;
export const rand = (a = 0, b = 1) => a + Math.random() * (b - a);

/** Run fn and swallow engine errors (unloaded chunks, removed entities). */
export function safe(fn, fallback = undefined) {
  try {
    return fn();
  } catch {
    return fallback;
  }
}

/** Weighted random pick from [{item, w}]. */
export function weighted(list) {
  const total = list.reduce((s, x) => s + x.w, 0);
  if (total <= 0) return undefined;
  let r = Math.random() * total;
  for (const x of list) {
    r -= x.w;
    if (r <= 0) return x.item;
  }
  return list[list.length - 1].item;
}
