import { Entity, EntityDamageCause, EntityHurtBeforeEvent, system, world } from "@minecraft/server";
import { log } from "./log";

/**
 * Wards are real damage interceptors built on world.beforeEvents.entityHurt (stable 2.11.0).
 * The before-event runs in restricted execution, so a ward only decides how much damage it
 * absorbs; every world change it wants (animations, counterattacks) is deferred with system.run.
 */
export interface HurtInfo {
  hurt: Entity;
  damage: number;
  cause: EntityDamageCause;
  attacker?: Entity;
  projectile?: Entity;
}

export interface Ward {
  id: number;
  ownerId: string;
  label: string;
  /** Higher priority wards get the first chance to absorb. */
  priority: number;
  /** Only invoked for entities this returns true for. Must be cheap and side-effect free. */
  protects(e: Entity): boolean;
  /** Returns the damage that should still go through (0 = fully absorbed). */
  absorb(info: HurtInfo): number;
  /** Optional deferred reaction (runs next tick, outside restricted execution). */
  react?(info: HurtInfo, absorbed: number): void;
  alive: boolean;
}

const wards: Ward[] = [];
let nextWardId = 1;

export const PHYSICAL_CAUSES = new Set<string>([
  EntityDamageCause.entityAttack,
  EntityDamageCause.projectile,
  EntityDamageCause.entityExplosion,
  EntityDamageCause.blockExplosion,
  EntityDamageCause.ramAttack,
  EntityDamageCause.charging,
  EntityDamageCause.maceSmash,
  EntityDamageCause.sonicBoom,
  EntityDamageCause.fireworks,
  EntityDamageCause.contact,
]);

export function addWard(w: Omit<Ward, "id" | "alive">): Ward {
  const ward: Ward = { ...w, id: nextWardId++, alive: true };
  wards.push(ward);
  wards.sort((a, b) => b.priority - a.priority);
  return ward;
}

export function removeWard(w: Ward | undefined): void {
  if (!w) return;
  w.alive = false;
  const i = wards.indexOf(w);
  if (i >= 0) wards.splice(i, 1);
}

export function removeWardsOf(ownerId: string): void {
  for (const w of [...wards]) if (w.ownerId === ownerId) removeWard(w);
}

/** Simple timed fall-damage immunity used by movement spells. */
const fallImmune = new Map<string, number>();
export function grantFallImmunity(entityId: string, ticks: number): void {
  fallImmune.set(entityId, Math.max(fallImmune.get(entityId) ?? 0, system.currentTick + ticks));
}

function onBeforeHurt(ev: EntityHurtBeforeEvent): void {
  const hurt = ev.hurtEntity;
  const cause = ev.damageSource.cause;
  if (cause === EntityDamageCause.fall || cause === EntityDamageCause.flyIntoWall) {
    const until = fallImmune.get(hurt.id);
    if (until !== undefined && until >= system.currentTick) {
      ev.cancel = true;
      return;
    }
  }
  if (wards.length === 0) return;
  let damage = ev.damage;
  const info: HurtInfo = {
    hurt,
    damage,
    cause,
    attacker: ev.damageSource.damagingEntity,
    projectile: ev.damageSource.damagingProjectile,
  };
  const reactions: [Ward, number][] = [];
  for (const w of wards) {
    if (!w.alive || damage <= 0) continue;
    let protects = false;
    try {
      protects = w.protects(hurt);
    } catch {
      protects = false;
    }
    if (!protects) continue;
    info.damage = damage;
    let remaining = damage;
    try {
      remaining = Math.max(0, w.absorb(info));
    } catch (e) {
      log.error(`ward ${w.label} absorb failed`, e);
      continue;
    }
    if (remaining < damage) {
      reactions.push([w, damage - remaining]);
      damage = remaining;
    }
  }
  if (reactions.length === 0) return;
  if (damage <= 0.001) ev.cancel = true;
  else ev.damage = damage;
  const snapshot: HurtInfo = { ...info, damage: ev.damage };
  system.run(() => {
    for (const [w, absorbed] of reactions) {
      if (!w.react) continue;
      try {
        w.react(snapshot, absorbed);
      } catch (e) {
        log.error(`ward ${w.label} reaction failed`, e);
      }
    }
  });
}

export function initDefense(): void {
  world.beforeEvents.entityHurt.subscribe(onBeforeHurt);
  system.runInterval(() => {
    const now = system.currentTick;
    for (const [id, t] of fallImmune) if (t < now) fallImmune.delete(id);
  }, 100);
}
