import {
  Entity, EntityDamageCause, EquipmentSlot, GameMode, ItemComponentUseEvent, Player, system, Vector3,
} from "@minecraft/server";
import { ENT } from "./generated/ids.js";
import { bosses, parts } from "./registry.js";
import { particle, sound } from "./util/fx.js";
import { add, len, mul, norm, sub } from "./util/vec.js";
import { blockedBetween, safeRemove } from "./util/world.js";

/** The Orison Halo: a thrown, piercing chakram that returns to its owner. */
interface Flight {
  e: Entity;
  owner: Player;
  dir: Vector3;
  age: number;
  back: boolean;
  out: number;
  hit: Set<string>;
}

const flights: Flight[] = [];
const COOLDOWN = "sab:orison";
const COOLDOWN_TICKS = 50;
/** Script-side throw gate (player id -> tick of the last throw); independent of when the engine starts the
 * item's own `minecraft:cooldown`, which is kept for the hotbar cooldown overlay. */
const lastThrow = new Map<string, number>();

/** True while a thrown halo entity is still flying (anything else is a leftover from a reload). */
export function haloInFlight(id: string): boolean {
  return flights.some((f) => f.e.isValid && f.e.id === id);
}
const OUT_SPEED = 1.15;
const BACK_SPEED = 1.35;
const RANGE = 16;
const DAMAGE = 8;

const SAFE_TYPES = new Set(["minecraft:villager_v2", "minecraft:wandering_trader", "minecraft:iron_golem",
  "minecraft:snow_golem", "minecraft:item", "minecraft:xp_orb", "minecraft:armor_stand", "minecraft:painting"]);

export function onHaloUse(ev: ItemComponentUseEvent): void {
  const p = ev.source;
  if (!(p instanceof Player)) return;
  const now = system.currentTick;
  const last = lastThrow.get(p.id);
  if (last !== undefined && now - last < COOLDOWN_TICKS) return;
  lastThrow.set(p.id, now);
  if (lastThrow.size > 64) for (const [k, t] of lastThrow) if (now - t > COOLDOWN_TICKS) lastThrow.delete(k);
  try {
    p.startItemCooldown(COOLDOWN, COOLDOWN_TICKS);
  } catch {
    /* ignore */
  }
  const dir = p.getViewDirection();
  const start = add(p.getHeadLocation(), mul(dir, 1.2));
  system.run(() => {
    try {
      const e = p.dimension.spawnEntity(ENT.halo, start);
      flights.push({ e, owner: p, dir: norm(dir), age: 0, back: false, out: 0, hit: new Set() });
      sound(p.dimension, "halo_throw", start, 1.0, 1.0 + Math.random() * 0.1);
      wear(p, 2);
    } catch {
      /* ignore */
    }
  });
}

function wear(p: Player, amount: number): void {
  try {
    if (p.getGameMode() === GameMode.Creative) return;
    const eq = p.getComponent("minecraft:equippable");
    const item = eq?.getEquipment(EquipmentSlot.Mainhand);
    if (!item || item.typeId !== "sab:orison_halo") return;
    const dur = item.getComponent("minecraft:durability");
    if (!dur) return;
    if (dur.damage + amount >= dur.maxDurability) {
      eq!.setEquipment(EquipmentSlot.Mainhand, undefined);
      p.playSound("random.break");
      return;
    }
    dur.damage += amount;
    eq!.setEquipment(EquipmentSlot.Mainhand, item);
  } catch {
    /* ignore */
  }
}

function insideAABB(e: Entity, p: Vector3, pad: number): boolean {
  try {
    const bb = e.getAABB();
    return Math.abs(p.x - bb.center.x) <= bb.extent.x + pad && Math.abs(p.y - bb.center.y) <= bb.extent.y + pad &&
      Math.abs(p.z - bb.center.z) <= bb.extent.z + pad;
  } catch {
    return false;
  }
}

function strike(f: Flight, at: Vector3): void {
  let near: Entity[] = [];
  try {
    near = f.e.dimension.getEntities({ location: at, maxDistance: 8, excludeTypes: [ENT.halo] });
  } catch {
    return;
  }
  for (const t of near) {
    if (t.id === f.owner.id || f.hit.has(t.id) || SAFE_TYPES.has(t.typeId)) continue;
    if (t.typeId === "minecraft:player") continue; // no PvP from the halo
    try {
      const tamed = t.getComponent("minecraft:tameable");
      if (tamed?.isTamed) continue;
    } catch {
      /* ignore */
    }
    const part = parts.get(t.id);
    const isBoss = bosses.has(t.id);
    if (!insideAABB(t, at, 0.6)) continue;
    f.hit.add(t.id);
    try {
      if (part) part.owner.forwardDamage(DAMAGE * part.owner.multiplierFor(part.kind, EntityDamageCause.projectile), f.owner, EntityDamageCause.projectile);
      else if (isBoss) t.applyDamage(DAMAGE, { cause: EntityDamageCause.projectile, damagingEntity: f.owner });
      else t.applyDamage(DAMAGE, { cause: EntityDamageCause.projectile, damagingEntity: f.owner });
      particle(f.e.dimension, "plasma_pop_gold", at);
    } catch {
      /* ignore */
    }
  }
}

export function tickHalos(): void {
  for (const f of flights) {
    f.age++;
    if (!f.e.isValid || !f.owner.isValid || f.owner.dimension.id !== f.e.dimension.id || f.age > 80) {
      safeRemove(f.e);
      f.age = 999;
      continue;
    }
    const pos = f.e.location;
    let next: Vector3;
    if (!f.back) {
      next = add(pos, mul(f.dir, OUT_SPEED));
      f.out += OUT_SPEED;
      const blocked = blockedBetween(f.e.dimension, pos, next);
      if (blocked || f.out >= RANGE) {
        f.back = true;
        f.hit.clear();
        next = pos;
        if (blocked) particle(f.e.dimension, "hull_spark", pos);
      }
    } else {
      const home = add(f.owner.location, { x: 0, y: 1.2, z: 0 });
      const d = sub(home, pos);
      if (len(d) < 1.3) {
        sound(f.e.dimension, "halo_catch", home, 0.9);
        safeRemove(f.e);
        f.age = 999;
        continue;
      }
      next = add(pos, mul(norm(d), Math.min(BACK_SPEED, len(d))));
    }
    try {
      f.e.teleport(next, { keepVelocity: false });
    } catch {
      /* ignore */
    }
    strike(f, next);
  }
  for (let i = flights.length - 1; i >= 0; i--) if (flights[i].age >= 999) flights.splice(i, 1);
}

export function haloFlights(): number {
  return flights.length;
}

