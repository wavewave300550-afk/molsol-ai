/**
 * Velvet Mirage decoys.  The decoy is a real (1 HP) entity with the "player" family, so
 * hostile mobs that hunt players will chase it; mobs near the caster are also provoked
 * by it directly.  Struck or expired, it bursts into velvet dust that dazzles enemies.
 */
import { Entity, EntityDamageCause, Player, system } from "@minecraft/server";
import { ENTITY_MIRAGE } from "../config.js";
import { effect } from "../core/combat.js";
import { particle, sound } from "../core/fx.js";
import { enemiesNear } from "../core/targets.js";
import { add, flat, mul, rotY, sub, v3 } from "../core/util.js";

interface Decoy {
  owner: string;
  entity: Entity;
  until: number;
  dir: ReturnType<typeof v3>;
  step: number;
}
const decoys = new Map<string, Decoy>();

export function spawnMirage(p: Player, ticks: number): Entity | undefined {
  const f = flat(p.getViewDirection());
  let e: Entity;
  try {
    e = p.dimension.spawnEntity(ENTITY_MIRAGE, p.location, { initialRotation: p.getRotation().y });
  } catch {
    return undefined;
  }
  decoys.set(e.id, { owner: p.id, entity: e, until: system.currentTick + ticks, dir: f, step: 0 });
  // provoke nearby hostiles into chasing the illusion
  for (const m of enemiesNear(p, p.location, 16)) {
    if (m.typeId === "minecraft:player") continue;
    try {
      m.applyDamage(1, { cause: EntityDamageCause.entityAttack, damagingEntity: e });
    } catch {
      /* ignore */
    }
  }
  particle(p.dimension, "plrace:velvet_burst", add(p.location, v3(0, 1, 0)));
  sound(p.dimension, "mob.allay.item_thrown", p.location, 1, 0.6);
  return e;
}

export const isMirage = (e: Entity) => decoys.has(e.id) || e.typeId === ENTITY_MIRAGE;

/** Every 4 ticks: the illusion zig-zags away; expires after its lifetime. */
export function tickMirages(): void {
  if (decoys.size === 0) return;
  const now = system.currentTick;
  for (const [id, d] of decoys) {
    const e = d.entity;
    if (!e.isValid) {
      decoys.delete(id);
      continue;
    }
    if (d.until <= now) {
      pop(e, false);
      continue;
    }
    d.step++;
    const dir = rotY(d.dir, d.step % 6 < 3 ? 32 : -32);
    try {
      e.applyImpulse(add(mul(dir, 0.22), v3(0, e.isOnGround ? 0.32 : 0, 0)));
    } catch {
      /* ignore */
    }
    if (d.step % 2 === 0) particle(e.dimension, "plrace:velvet_shimmer", e.location);
  }
}

/** Burst the decoy. `struck`: something hit it -> dazzle nearby enemies. */
export function pop(e: Entity, struck: boolean, ownerResolver?: (id: string) => Player | undefined, attacker?: Entity): void {
  const d = decoys.get(e.id);
  decoys.delete(e.id);
  if (!e.isValid) return;
  const loc = { ...e.location };
  const dim = e.dimension;
  particle(dim, "plrace:velvet_burst", add(loc, v3(0, 1, 0)));
  sound(dim, struck ? "mob.allay.death" : "random.pop", loc, 1, struck ? 0.8 : 1.4);
  if (struck && d) {
    const owner = ownerResolver?.(d.owner);
    if (owner) {
      const dazzled = enemiesNear(owner, loc, 3.5, dim);
      if (attacker && attacker.isValid && attacker.id !== owner.id && !dazzled.some((x) => x.id === attacker.id)) dazzled.push(attacker);
      for (const m of dazzled) {
        effect(m, "blindness", 60, 0);
        effect(m, "slowness", 60, 1);
      }
    }
  }
  system.run(() => {
    try {
      if (e.isValid) e.remove();
    } catch {
      /* ignore */
    }
  });
}

export function removeMiragesOf(ownerId: string): void {
  for (const [, d] of decoys) if (d.owner === ownerId) pop(d.entity, false);
}

export function mirageOwner(e: Entity): string | undefined {
  return decoys.get(e.id)?.owner;
}

export function away(p: Player, from: ReturnType<typeof v3>): ReturnType<typeof v3> {
  return flat(sub(p.location, from));
}
