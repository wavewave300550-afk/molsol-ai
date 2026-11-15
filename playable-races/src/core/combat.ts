/** Damage, knockback and status effects with consistent attribution and safety guards. */
import { Entity, EntityDamageCause, Player, Vector3 } from "@minecraft/server";
import { alive } from "./targets.js";
import { flat, sub, v3 } from "./util.js";

/** Deal ability damage attributed to the caster (so kills, aggro and PvP rules work). */
export function hurt(target: Entity, amount: number, caster: Player, cause: EntityDamageCause = EntityDamageCause.entityAttack): boolean {
  if (!alive(target) || amount <= 0) return false;
  try {
    return target.applyDamage(amount, { cause, damagingEntity: caster });
  } catch {
    return false;
  }
}

/** Push `target` away from `from` (horizontal strength, vertical lift). Works for players and mobs. */
export function knockFrom(target: Entity, from: Vector3, strength: number, lift: number): void {
  if (!target.isValid) return;
  const d = flat(sub(target.location, from));
  knock(target, v3(d.x * strength, 0, d.z * strength), lift);
}

export function knock(target: Entity, horizontal: Vector3, lift: number): void {
  if (!target.isValid) return;
  try {
    target.applyKnockback({ x: horizontal.x, z: horizontal.z }, lift);
  } catch {
    try {
      target.applyImpulse({ x: horizontal.x * 0.5, y: lift * 0.5, z: horizontal.z * 0.5 });
    } catch {
      /* immovable */
    }
  }
}

export function effect(target: Entity, id: string, ticks: number, amp = 0, particles = true): void {
  if (!target.isValid) return;
  try {
    target.addEffect(id, Math.max(1, Math.floor(ticks)), { amplifier: amp, showParticles: particles });
  } catch {
    /* effect not allowed on this entity */
  }
}

export function heal(target: Entity, amount: number): number {
  try {
    const h = target.getComponent("minecraft:health");
    if (!h) return 0;
    const before = h.currentValue;
    h.setCurrentValue(Math.min(h.effectiveMax, before + amount));
    return h.currentValue - before;
  } catch {
    return 0;
  }
}

export function healthFrac(e: Entity): number {
  try {
    const h = e.getComponent("minecraft:health");
    return h ? h.currentValue / Math.max(1, h.effectiveMax) : 1;
  } catch {
    return 1;
  }
}
