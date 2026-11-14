import { Entity, EntityDamageCause, Player, Vector3, system, world } from "@minecraft/server";
import { Scene } from "./scene";
import { isAlive } from "./targeting";
import { flat, norm, sub } from "./vec";

/** Damage attributed to the caster.  Returns true when the hit landed. */
export function damage(target: Entity, amount: number, caster: Player, cause: EntityDamageCause = EntityDamageCause.magic): boolean {
  if (!isAlive(target) || amount <= 0) return false;
  try {
    return target.applyDamage(amount, { cause, damagingEntity: caster.isValid ? caster : undefined });
  } catch {
    return false;
  }
}

/** Push target away from `from` (horizontal strength h, vertical v). */
export function knockback(target: Entity, from: Vector3, h: number, v: number): void {
  if (!isAlive(target)) return;
  const d = norm(flat(sub(target.location, from)));
  try {
    target.applyKnockback({ x: d.x * h, z: d.z * h }, v);
  } catch {
    try { target.applyImpulse({ x: d.x * h * 0.4, y: v * 0.4, z: d.z * h * 0.4 }); } catch { /* immovable */ }
  }
}

/** Push along an explicit direction. */
export function shove(target: Entity, dir: Vector3, h: number, v: number): void {
  if (!isAlive(target)) return;
  const d = norm(flat(dir));
  try { target.applyKnockback({ x: d.x * h, z: d.z * h }, v); } catch { /* immovable */ }
}

export function heal(e: Entity, amount: number): number {
  if (!isAlive(e)) return 0;
  try {
    const h = e.getComponent("minecraft:health");
    if (!h) return 0;
    const before = h.currentValue;
    h.setCurrentValue(Math.min(h.effectiveMax, before + amount));
    return h.currentValue - before;
  } catch {
    return 0;
  }
}

export function effect(e: Entity, id: string, ticks: number, amplifier = 0, particles = false): void {
  if (!isAlive(e)) return;
  try { e.addEffect(id, Math.max(1, Math.round(ticks)), { amplifier, showParticles: particles }); } catch { /* immune */ }
}

/**
 * Hold a target in place for `ticks` (real restraint: it is pinned to its anchor every tick and
 * slowed so AI cannot walk away).  Ends early if the scene ends.  Returns a release function.
 */
export function restrain(scene: Scene, target: Entity, ticks: number, anchor?: Vector3): () => void {
  let on = true;
  const hold = anchor ? { ...anchor } : { ...target.location };
  const until = scene.tick + ticks;
  effect(target, "slowness", ticks + 2, 6);
  scene.every(1, () => {
    if (!on || !isAlive(target)) return;
    try {
      target.teleport(hold, { keepVelocity: false });
      target.clearVelocity();
    } catch { /* ignore */ }
  }, scene.tick, until);
  const release = () => {
    if (!on) return;
    on = false;
    try { if (target.isValid) target.removeEffect("slowness"); } catch { /* ignore */ }
  };
  scene.at(until, release);
  scene.onEnd(release);
  return release;
}

/** Move a restrained/held target smoothly toward a point over time (e.g. a drag). */
export function drag(target: Entity, to: Vector3): void {
  if (!isAlive(target)) return;
  try { target.teleport(to, { keepVelocity: false }); } catch { /* ignore */ }
}

// ---------------------------------------------------------------------------------------------
// Wards: real damage mitigation for protected entities, applied in the entityHurt before-event.
export interface Ward {
  scene: Scene;
  /** Which entities this ward protects. */
  protects(e: Entity): boolean;
  /** Fraction of incoming damage that still gets through (0 = immune, 1 = no protection). */
  factor: number;
  /** Optional finite pool of damage the ward can absorb before it breaks. */
  pool?: number;
  /** Called (next tick, unrestricted) with the absorbed amount and the attacker if known. */
  onAbsorb?(amount: number, attacker: Entity | undefined, victim: Entity): void;
  /** Called once when the pool is exhausted. */
  onBreak?(): void;
  broken?: boolean;
}

const wards = new Set<Ward>();

export function addWard(w: Ward): Ward {
  wards.add(w);
  w.scene.onEnd(() => wards.delete(w));
  return w;
}
export function removeWard(w: Ward): void {
  wards.delete(w);
}

let wardHooked = false;
export function installWards(): void {
  if (wardHooked) return;
  wardHooked = true;
  world.beforeEvents.entityHurt.subscribe((ev) => {
    if (wards.size === 0) return;
    for (const w of wards) {
      if (w.scene.ended || w.broken) { continue; }
      let ok = false;
      try { ok = w.protects(ev.hurtEntity); } catch { ok = false; }
      if (!ok) continue;
      let absorbed = ev.damage * (1 - w.factor);
      if (w.pool !== undefined) {
        absorbed = Math.min(absorbed, w.pool);
        w.pool -= absorbed;
      }
      if (absorbed <= 0) continue;
      ev.damage = Math.max(0, ev.damage - absorbed);
      if (ev.damage < 0.05) ev.cancel = true;
      const attacker = ev.damageSource.damagingEntity;
      const victim = ev.hurtEntity;
      const breakNow = w.pool !== undefined && w.pool <= 0.0001 && !w.broken;
      if (breakNow) w.broken = true;
      // before-events are read-only: defer reactions (also prevents reactive recursion)
      system.run(() => {
        if (w.scene.ended) return;
        try { w.onAbsorb?.(absorbed, attacker, victim); } catch (e) { console.warn(`[grimoire] ward: ${e}`); }
        if (breakNow) { try { w.onBreak?.(); } catch (e) { console.warn(`[grimoire] ward break: ${e}`); } }
      });
    }
  });
}

/** Hostile projectile types wards and barriers are allowed to dissolve. */
export const PROJECTILES = ["minecraft:arrow", "minecraft:fireball", "minecraft:small_fireball", "minecraft:shulker_bullet",
  "minecraft:wither_skull", "minecraft:wither_skull_dangerous", "minecraft:dragon_fireball", "minecraft:llama_spit",
  "minecraft:thrown_trident", "minecraft:snowball", "minecraft:wind_charge_projectile", "minecraft:breeze_wind_charge_projectile",
  "minecraft:splash_potion", "minecraft:lingering_potion"];

/** Remove hostile projectiles inside a sphere; returns how many were dissolved (with their positions). */
export function dissolveProjectiles(scene: Scene, center: Vector3, radius: number): Vector3[] {
  const out: Vector3[] = [];
  for (const type of PROJECTILES) {
    let found: Entity[] = [];
    try { found = scene.dim.getEntities({ location: center, maxDistance: radius, type }); } catch { continue; }
    for (const p of found) {
      try {
        const owner = p.getComponent("minecraft:projectile")?.owner;
        if (owner && owner.typeId === "minecraft:player") continue; // leave allied shots alone
        out.push({ ...p.location });
        p.remove();
      } catch { /* ignore */ }
    }
  }
  return out;
}
