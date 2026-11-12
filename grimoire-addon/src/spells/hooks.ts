import { Entity, EntityDamageCause, EntityHurtAfterEvent, world } from "@minecraft/server";
import { log } from "../core/log";

/**
 * Bounded registry of after-hurt listeners used by spells that react to damage dealt to
 * *other* entities (e.g. Sovereign's Pulse). Listeners are removed by their spell's cleanup.
 */
export interface HurtListener {
  ownerId: string;
  watch: Set<string>;
  fn(victim: Entity, damage: number, cause: EntityDamageCause, attacker?: Entity): void;
}

const listeners = new Set<HurtListener>();

/** Fires when `attackerId` hurts anything (D12 mirrors the caster's attacks). */
export interface AttackListener {
  attackerId: string;
  fn(victim: Entity, damage: number, cause: EntityDamageCause): void;
}

const attackListeners = new Set<AttackListener>();

export function onAttack(l: AttackListener): () => void {
  attackListeners.add(l);
  return () => attackListeners.delete(l);
}

export function onHurt(l: HurtListener): () => void {
  listeners.add(l);
  return () => listeners.delete(l);
}

function dispatch(e: EntityHurtAfterEvent): void {
  const src = e.damageSource.damagingEntity;
  if (src && attackListeners.size > 0) {
    for (const l of [...attackListeners]) {
      if (l.attackerId !== src.id) continue;
      try {
        l.fn(e.hurtEntity, e.damage, e.damageSource.cause);
      } catch (err) {
        log.error("attack listener failed", err);
      }
    }
  }
  if (listeners.size === 0) return;
  const id = e.hurtEntity.id;
  for (const l of [...listeners]) {
    if (!l.watch.has(id)) continue;
    try {
      l.fn(e.hurtEntity, e.damage, e.damageSource.cause, e.damageSource.damagingEntity);
    } catch (err) {
      log.error("hurt listener failed", err);
    }
  }
}

export function initHooks(): void {
  world.afterEvents.entityHurt.subscribe(dispatch);
}
