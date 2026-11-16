import { Entity, EntityComponentTypes, EntityDamageCause, Player, system, Vector3 } from "@minecraft/server";
import { CANE } from "../config.js";
import { fx, Rgba, sound } from "../core/fx.js";
import { alive, centerOf, constitutionOf, heightOf } from "../core/targets.js";
import { add, dist, v } from "../core/vec.js";
import { scriptDamage } from "./damage.js";

interface Wound {
  stacks: number;
  until: number;
  next: number;
  by: string;
  mult: number;
  color: Rgba;
  entity: Entity;
}

const wounds = new Map<string, Wound>();

export function bleedingStacks(e: Entity): number {
  return wounds.get(e.id)?.stacks ?? 0;
}

function onFire(e: Entity): boolean {
  try {
    return !!e.getComponent(EntityComponentTypes.OnFire);
  } catch {
    return false;
  }
}

/** Blood spray coloured by creature (droplets that fall and splat, plus a fine mist). */
export function spray(e: Entity, color: Rgba, count: number, dir?: Vector3, speed = 1): void {
  const c = centerOf(e);
  fx(e.dimension, "oddworks:blood_drop", c, { color, count, dir: dir ?? v(0, 0.6, 0), speed });
  if (count >= 6) fx(e.dimension, "oddworks:blood_mist", c, { color });
}

function splat(e: Entity, color: Rgba, size = 1): void {
  try {
    const below = e.dimension.getBlockBelow(add(e.location, v(0, 0.2, 0)), { maxDistance: 4 });
    if (!below) return;
    const at = v(e.location.x + (Math.random() - 0.5) * 0.6, below.location.y + 1.02, e.location.z + (Math.random() - 0.5) * 0.6);
    fx(e.dimension, "oddworks:blood_splat", at, { color, size });
  } catch {
    /* ignore */
  }
}

/** Adds wound stacks. `chance` already accounts for armour. Returns stacks actually opened. */
export function wound(e: Entity, by: Player, n: number, chance: number): number {
  const con = constitutionOf(e);
  if (con.bleed <= 0 || !alive(e)) return 0;
  let opened = 0;
  for (let i = 0; i < n; i++) if (Math.random() < chance) opened++;
  if (opened === 0) return 0;
  const t = system.currentTick;
  const w = wounds.get(e.id) ?? { stacks: 0, until: 0, next: t + 20, by: by.id, mult: con.bleed, color: con.color, entity: e };
  w.stacks = Math.min(CANE.woundMax, w.stacks + opened);
  w.until = t + CANE.woundTicks;
  w.by = by.id;
  w.entity = e;
  wounds.set(e.id, w);
  return opened;
}

export function tickBleed(players: Map<string, Player>): void {
  const t = system.currentTick;
  for (const [id, w] of wounds) {
    const e = w.entity;
    if (!alive(e)) {
      wounds.delete(id);
      continue;
    }
    if (onFire(e)) {
      // fire cauterizes: wounds seal with a hiss
      wounds.delete(id);
      fx(e.dimension, "oddworks:frost_mist", centerOf(e), { count: 3, size: 0.5 });
      sound(e.dimension, "random.fizz", centerOf(e), 1.4, 0.6);
      continue;
    }
    if (t >= w.until) {
      wounds.delete(id);
      continue;
    }
    if (t % 6 === 0) fx(e.dimension, "oddworks:blood_drop", add(e.location, v(0, heightOf(e) * 0.55, 0)), { color: w.color, count: Math.min(3, w.stacks), speed: 0.3 });
    if (t < w.next) continue;
    w.next = t + 20;
    let dmg = CANE.bleedPerStack * w.stacks * w.mult;
    try {
      if (e.getEffect("regeneration")) dmg *= 0.5;
    } catch {
      /* ignore */
    }
    const by = players.get(w.by);
    scriptDamage(e, dmg, EntityDamageCause.magic, by);
    sound(e.dimension, "oddworks.cane.bleed", centerOf(e), 0.9 + Math.random() * 0.3, 0.5);
    if (Math.random() < 0.5) splat(e, w.color, 0.7);
  }
}

/** Noto's closing click: every wound inflicted by `by` within 24 blocks opens at once. */
export function hemorrhage(by: Player): { hit: number; killed: number } {
  const t = system.currentTick;
  let hit = 0;
  let killed = 0;
  for (const [id, w] of wounds) {
    if (w.by !== by.id) continue;
    const e = w.entity;
    if (!alive(e) || e.dimension.id !== by.dimension.id || dist(e.location, by.location) > 24) continue;
    const secondsLeft = Math.max(1.5, (w.until - t) / 20);
    const dmg = CANE.bleedPerStack * w.stacks * w.mult * secondsLeft * CANE.hemorrhageMult;
    wounds.delete(id);
    hit++;
    spray(e, w.color, 14 + w.stacks * 3, v(0, 1, 0), 1.6);
    splat(e, w.color, 1.4);
    sound(e.dimension, "oddworks.cane.hemorrhage", centerOf(e), 0.9 + Math.random() * 0.2);
    try {
      e.addEffect("slowness", 10, { amplifier: 2, showParticles: false });
    } catch {
      /* ignore */
    }
    scriptDamage(e, dmg, EntityDamageCause.magic, by);
    if (!alive(e)) killed++;
    else {
      try {
        const hp = e.getComponent(EntityComponentTypes.Health);
        if (hp && hp.currentValue <= 0) killed++;
      } catch {
        /* ignore */
      }
    }
  }
  return { hit, killed };
}

export function countBleeding(byId: string): number {
  let n = 0;
  for (const w of wounds.values()) if (w.by === byId && alive(w.entity)) n++;
  return n;
}

export function clearWounds(id: string): void {
  wounds.delete(id);
}
