/**
 * DamageSystem - deterministic damage to players.
 *
 * Design damage is reduced by a documented mitigation curve computed from the
 * player's real equipment and effects, then applied EXACTLY:
 *
 *   1. a 1-point native hit supplies everything the engine is good at (hurt flash,
 *      sound, attribution to the boss, shield blocking for blockable attacks,
 *      invulnerability frames, armour wear);
 *   2. health is then set to `before - final`, so the result does not depend on
 *      the engine's armour arithmetic;
 *   3. if the hit would be lethal it is delivered as one overwhelming native hit
 *      instead, so death messages and Totems of Undying behave normally.
 *
 * Creative and spectator players are never damaged. Each player can be hit by a
 * given encounter at most once per `playerHitIntervalTicks`.
 */
import {
  EntityComponentTypes,
  EntityDamageCause,
  EntityEquippableComponent,
  EntityHealthComponent,
  EquipmentSlot,
  GameMode,
  ItemEnchantableComponent,
  Entity,
  Player,
} from "@minecraft/server";
import { CONFIG, difficulty } from "../config";
import { XZ, normXZ } from "./math";
import { trace } from "./trace";

export interface HitSpec {
  /** Design damage before difficulty and mitigation. */
  damage: number;
  /** Shields stop it (melee sweeps, thrown objects). Ground and sound hazards are not blockable. */
  blockable?: boolean;
  /** Horizontal knockback strength and its origin (defaults to the damage source entity). */
  knock?: number;
  knockUp?: number;
  from?: XZ;
  effects?: ReadonlyArray<{ id: string; ticks: number; amp?: number }>;
  /** Label for telemetry. */
  label?: string;
}

const ARMOR_SLOTS = [EquipmentSlot.Head, EquipmentSlot.Chest, EquipmentSlot.Legs, EquipmentSlot.Feet];

/** Share of design damage removed by armour, Protection and Resistance (0..1). */
export function mitigation(p: Player): number {
  const d = CONFIG.damage;
  let armor = 0;
  let prot = 0;
  try {
    const eq = p.getComponent(EntityComponentTypes.Equippable) as EntityEquippableComponent | undefined;
    if (eq) {
      armor = eq.totalArmor;
      for (const slot of ARMOR_SLOTS) {
        const item = eq.getEquipment(slot);
        const ench = item?.getComponent("minecraft:enchantable") as ItemEnchantableComponent | undefined;
        prot += ench?.getEnchantment("protection")?.level ?? 0;
      }
    }
  } catch {
    /* equipment unavailable: treat as unarmoured */
  }
  let m = Math.min(d.armorCap, armor * d.armorPerPoint) + Math.min(d.protectionCap, prot * d.protectionPerLevel);
  let res = 0;
  try {
    const e = p.getEffect("resistance");
    if (e) res = Math.min(d.resistanceCap, (e.amplifier + 1) * d.resistancePerLevel);
  } catch {
    res = 0;
  }
  m = 1 - (1 - m) * (1 - res);
  return Math.min(1 - d.minShare, Math.max(0, m));
}

export class DamageSystem {
  private lastHit = new Map<string, number>();
  /** Running totals for telemetry / tests. */
  hits = 0;
  totalDealt = 0;

  constructor(private readonly source: () => Entity | undefined) {}

  canHit(p: Player, now: number): boolean {
    const last = this.lastHit.get(p.id);
    return last === undefined || now - last >= CONFIG.encounter.playerHitIntervalTicks;
  }

  /** Apply a hazard hit. Returns the health actually removed (0 when nothing happened). */
  hit(p: Player, spec: HitSpec, now: number): number {
    if (!p.isValid || !this.canHit(p, now)) return 0;
    let mode: GameMode;
    try {
      mode = p.getGameMode();
    } catch {
      return 0;
    }
    if (mode === GameMode.Creative || mode === GameMode.Spectator) return 0;
    const health = p.getComponent("minecraft:health") as EntityHealthComponent | undefined;
    if (!health || health.currentValue <= 0) return 0;

    const final = Math.max(0.5, spec.damage * difficulty().damage * (1 - mitigation(p)));
    const before = health.currentValue;
    const src = this.source();
    const cause = spec.blockable ? EntityDamageCause.entityAttack : EntityDamageCause.magic;
    const opts = src && src.isValid ? { cause, damagingEntity: src } : { cause };
    let dealt = 0;
    try {
      if (final >= before) {
        if (!p.applyDamage(100000, opts)) return 0;
        dealt = before;
      } else {
        if (!p.applyDamage(1, opts)) return 0;
        health.setCurrentValue(Math.max(0.5, before - final));
        dealt = final;
      }
    } catch {
      return 0;
    }
    this.lastHit.set(p.id, now);
    this.hits++;
    this.totalDealt += dealt;

    if (spec.knock || spec.knockUp) {
      const o = spec.from ?? (src && src.isValid ? src.location : p.location);
      const d = normXZ(p.location.x - o.x, p.location.z - o.z);
      try {
        p.applyKnockback({ x: d.x * (spec.knock ?? 0), z: d.z * (spec.knock ?? 0) }, spec.knockUp ?? 0);
      } catch {
        /* dead or teleporting: ignore */
      }
    }
    if (spec.effects && final < before) {
      for (const e of spec.effects) {
        try {
          p.addEffect(e.id, e.ticks, { amplifier: e.amp ?? 0, showParticles: true });
        } catch {
          /* ignore */
        }
      }
    }
    trace("player_hit", { player: p.name, dealt, design: spec.damage, label: spec.label ?? "" });
    return dealt;
  }

  forget(playerId: string): void {
    this.lastHit.delete(playerId);
  }

  clear(): void {
    this.lastHit.clear();
  }
}
