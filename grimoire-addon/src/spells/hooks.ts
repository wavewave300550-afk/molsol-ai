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

export function onHurt(l: HurtListener): () => void {
  listeners.add(l);
  return () => listeners.delete(l);
}

function dispatch(e: EntityHurtAfterEvent): void {
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
