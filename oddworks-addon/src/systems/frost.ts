import { Entity, EntityComponentTypes, Player, system } from "@minecraft/server";
import { ID } from "../config.js";
import { fx, sound } from "../core/fx.js";
import { alive, centerOf, heightOf, widthOf } from "../core/targets.js";
import { add, v } from "../core/vec.js";

/** Frost buildup -> chill (slowness tiers) -> frozen solid (encased in an ice shell). */
interface Frost {
  value: number;
  frozenUntil: number;
  shellId?: string;
  by?: string;
}

const frost = new Map<string, Frost>();
const COLD_NATIVE = new Set(["minecraft:stray", "minecraft:polar_bear", "minecraft:snow_golem", "minecraft:wither"]);
const FIRE_BORN = new Set(["minecraft:blaze", "minecraft:magma_cube", "minecraft:strider", "minecraft:ghast"]);

export const isColdNative = (e: Entity): boolean => COLD_NATIVE.has(e.typeId);
export const isFireBorn = (e: Entity): boolean => FIRE_BORN.has(e.typeId);

export function isFrozen(e: Entity): boolean {
  const f = frost.get(e.id);
  return !!f && f.frozenUntil > system.currentTick;
}

function burning(e: Entity): boolean {
  try {
    return !!e.getComponent(EntityComponentTypes.OnFire);
  } catch {
    return false;
  }
}

function effect(e: Entity, id: string, ticks: number, amp: number): void {
  try {
    e.addEffect(id, ticks, { amplifier: amp, showParticles: false });
  } catch {
    /* immune / invalid */
  }
}

/** Adds frost; returns true if the target froze solid this call. heat < 1 shortens the freeze. */
export function addFrost(e: Entity, amount: number, by: Player | undefined, heat = 1): boolean {
  if (!alive(e) || isColdNative(e)) return false;
  trackEntity(e);
  const t = system.currentTick;
  const f = frost.get(e.id) ?? { value: 0, frozenUntil: 0 };
  if (burning(e)) {
    // ice meets fire: the flames die first, the frost mostly turns to steam
    try {
      e.extinguishFire(true);
    } catch {
      /* ignore */
    }
    fx(e.dimension, "oddworks:frost_mist", centerOf(e), { count: 4, size: 0.8 });
    sound(e.dimension, "random.fizz", centerOf(e), 1.2, 0.7);
    amount *= 0.4;
  }
  f.value += amount;
  f.by = by?.id;
  frost.set(e.id, f);
  if (f.frozenUntil > t) return false;
  if (f.value >= 100) {
    freeze(e, Math.round((40 + amount * 0.6) * heat));
    return true;
  }
  const tier = f.value >= 70 ? 2 : f.value >= 35 ? 1 : 0;
  effect(e, "slowness", 60, tier);
  return false;
}

export function freeze(e: Entity, ticks: number): void {
  trackEntity(e);
  const t = system.currentTick;
  const f = frost.get(e.id) ?? { value: 100, frozenUntil: 0 };
  f.frozenUntil = t + ticks;
  f.value = 100;
  effect(e, "slowness", ticks, 6);
  effect(e, "weakness", ticks, 2);
  if (e instanceof Player) effect(e, "mining_fatigue", ticks, 2);
  try {
    const h = heightOf(e);
    const w = widthOf(e);
    const s = Math.max(h, w);
    const size = s <= 0.8 ? "s" : s <= 1.5 ? "m" : s <= 2.4 ? "l" : "xl";
    removeShellById(f);
    const shell = e.dimension.spawnEntity(ID.iceShell, e.location, { spawnEvent: `oddworks:size_${size}` });
    f.shellId = shell.id;
    shellLookup.set(shell.id, shell);
  } catch {
    /* entity limit / unloaded */
  }
  frost.set(e.id, f);
  const c = centerOf(e);
  fx(e.dimension, "oddworks:frost_burst", c, { count: 14 });
  fx(e.dimension, "oddworks:frost_mist", c, { count: 6, size: 1 });
  sound(e.dimension, "oddworks.goggles.freeze", c, 0.9);
}

function removeShell(f: Frost, e?: Entity): void {
  if (!f.shellId) return;
  const shell = (e && shellEntity(e, f)) ?? shellLookup.get(f.shellId);
  try {
    if (shell && alive(shell)) shell.remove();
  } catch {
    /* gone */
  }
  shellLookup.delete(f.shellId);
  f.shellId = undefined;
}

/** Shatter a frozen target (melee follow-up). Returns bonus damage dealt by the shatter. */
export function shatter(e: Entity): boolean {
  const f = frost.get(e.id);
  if (!f || f.frozenUntil <= system.currentTick) return false;
  f.frozenUntil = 0;
  f.value = 20;
  removeShell(f, e);
  try {
    e.removeEffect("slowness");
    e.removeEffect("weakness");
  } catch {
    /* ignore */
  }
  const c = centerOf(e);
  fx(e.dimension, "oddworks:frost_burst", c, { count: 22 });
  sound(e.dimension, "random.glass", c, 0.8, 1);
  return true;
}

export function tickFrost(): void {
  const t = system.currentTick;
  for (const [id, f] of frost) {
    const e = findEntity(id, f);
    if (!e) {
      removeShellById(f);
      frost.delete(id);
      continue;
    }
    if (f.frozenUntil > t) {
      // keep the shell wrapped around the frozen body; fire thaws it early
      const shell = shellEntity(e, f);
      if (shell) {
        try {
          shell.teleport(e.location);
        } catch {
          /* ignore */
        }
      }
      if (t % 10 === 0) fx(e.dimension, "oddworks:frost_aura", add(e.location, v(0, heightOf(e) / 2, 0)), { count: 3, size: Math.max(0.6, heightOf(e) / 1.8) });
      if (burning(e)) f.frozenUntil = t;
      continue;
    }
    if (f.shellId) {
      removeShell(f, e);
      fx(e.dimension, "oddworks:frost_burst", centerOf(e), { count: 10 });
      sound(e.dimension, "random.glass", centerOf(e), 1.2, 0.6);
      f.value = 30;
    }
    f.value -= burning(e) ? 8 : 1.2;
    if (f.value > 0 && t % 12 === 0) fx(e.dimension, "oddworks:frost_aura", add(e.location, v(0, heightOf(e) / 2, 0)), { count: 1, size: 0.7 });
    if (f.value <= 0) frost.delete(id);
  }
}

const shellLookup = new Map<string, Entity>();
function shellEntity(e: Entity, f: Frost): Entity | undefined {
  if (!f.shellId) return undefined;
  const cached = shellLookup.get(f.shellId);
  if (cached && alive(cached)) return cached;
  const found = e.dimension.getEntities({ type: ID.iceShell, location: e.location, maxDistance: 4 }).find((x) => x.id === f.shellId);
  if (found) shellLookup.set(f.shellId, found);
  return found;
}

function removeShellById(f: Frost): void {
  if (!f.shellId) return;
  const s = shellLookup.get(f.shellId);
  try {
    if (s && alive(s)) s.remove();
  } catch {
    /* gone */
  }
  shellLookup.delete(f.shellId);
}

const entityLookup = new Map<string, Entity>();
export function trackEntity(e: Entity): void {
  entityLookup.set(e.id, e);
}
function findEntity(id: string, _f: Frost): Entity | undefined {
  const e = entityLookup.get(id);
  if (e && alive(e)) return e;
  entityLookup.delete(id);
  return undefined;
}

export function forgetFrost(id: string): void {
  const f = frost.get(id);
  if (f) removeShellById(f);
  frost.delete(id);
  entityLookup.delete(id);
}
