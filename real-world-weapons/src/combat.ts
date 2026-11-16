import {
  Entity,
  EntityComponentTypes,
  EntityDamageCause,
  EntityHurtBeforeEvent,
  EntityTameableComponent,
  ItemComponentBeforeDurabilityDamageEvent,
  ItemComponentHitEntityEvent,
  ItemComponentTypes,
  ItemCooldownComponent,
  ItemStack,
  Player,
  system,
  Vector3,
  world,
} from "@minecraft/server";
import { heldWeapon, RULES, WeaponParams, WeaponType } from "./weapons.js";

/** Entities the Zweihänder sweep must never catch (beyond the primary target the player chose). */
const PROTECTED_TYPES = new Set([
  "minecraft:villager",
  "minecraft:villager_v2",
  "minecraft:wandering_trader",
  "minecraft:iron_golem",
  "minecraft:snow_golem",
  "minecraft:allay",
  "minecraft:armor_stand",
  "minecraft:item",
  "minecraft:xp_orb",
]);

interface KatanaState {
  drawnTick: number;
  iaiReady: boolean;
  rechargeTick: number;
}

function horizontal(a: Vector3, b: Vector3): { x: number; z: number; d: number } {
  const x = b.x - a.x;
  const z = b.z - a.z;
  return { x, z, d: Math.hypot(x, z) };
}

export class Combat {
  private readonly katana = new Map<string, KatanaState>();
  /** entities hit by a player's swing during the current tick (piercing weapons may hit several) */
  private readonly hitThisTick = new Map<string, { tick: number; ids: Set<string>; durability: boolean; swept: boolean }>();
  private sweeping = false;

  // ------------------------------------------------------------------ equip rules
  onEquip(player: Player, weapon: WeaponType, item: ItemStack | undefined): void {
    if (weapon === "katana") {
      const s = this.katana.get(player.id) ?? { drawnTick: -1, iaiReady: false, rechargeTick: 0 };
      s.drawnTick = system.currentTick;
      s.iaiReady = system.currentTick >= s.rechargeTick;
      this.katana.set(player.id, s);
    } else if (weapon === "zweihander" && item) {
      // Hefting the great sword: its attack cooldown starts when it is drawn.
      try {
        (item.getComponent(ItemComponentTypes.Cooldown) as ItemCooldownComponent | undefined)?.startCooldown(player);
      } catch {
        // ignore: the item may have changed this tick
      }
    }
  }

  // ------------------------------------------------------------------ damage modifiers (before event)
  onBeforeHurt(ev: EntityHurtBeforeEvent): void {
    if (this.sweeping) return;
    const attacker = ev.damageSource.damagingEntity;
    if (!(attacker instanceof Player) || ev.damageSource.damagingProjectile) return;
    const weapon = heldWeapon(attacker);
    if (!weapon) return;
    if (weapon.type === "rapier") {
      const h = horizontal(attacker.location, ev.hurtEntity.location);
      if (h.d >= RULES.rapier.measureDistance) {
        ev.damage = ev.damage * RULES.rapier.measureBonus;
        this.feedback(ev.hurtEntity, "minecraft:critical_hit_emitter");
      }
    } else if (weapon.type === "katana") {
      const s = this.katana.get(attacker.id);
      if (s && s.iaiReady && system.currentTick - s.drawnTick <= RULES.katana.iaiWindowTicks) {
        s.iaiReady = false;
        s.rechargeTick = system.currentTick + RULES.katana.iaiRechargeTicks;
        ev.damage = ev.damage * RULES.katana.iaiBonus;
        this.feedback(ev.hurtEntity, "minecraft:magic_critical_hit_emitter");
      }
    }
  }

  private feedback(target: Entity, particle: string): void {
    const loc = { ...target.location };
    const dim = target.dimension;
    system.run(() => {
      try {
        dim.spawnParticle(particle, { x: loc.x, y: loc.y + 1, z: loc.z });
      } catch {
        // chunk unloaded
      }
    });
  }

  private record(player: Entity): { tick: number; ids: Set<string>; durability: boolean; swept: boolean } {
    let r = this.hitThisTick.get(player.id);
    if (!r || r.tick !== system.currentTick) {
      r = { tick: system.currentTick, ids: new Set(), durability: false, swept: false };
      this.hitThisTick.set(player.id, r);
    }
    return r;
  }

  // ------------------------------------------------------------------ custom component hooks
  onHitEntity(ev: ItemComponentHitEntityEvent, params: WeaponParams): void {
    const player = ev.attackingEntity;
    if (!(player instanceof Player)) return;
    const r = this.record(player);
    r.ids.add(ev.hitEntity.id);
    if (params.type !== "zweihander" || !ev.hadEffect) return;
    // heavier knock-back on the primary target
    try {
      const h = horizontal(player.location, ev.hitEntity.location);
      if (h.d > 0.01 && ev.hitEntity.isValid) {
        ev.hitEntity.applyKnockback(
          { x: (h.x / h.d) * RULES.zweihander.primaryKnockback, z: (h.z / h.d) * RULES.zweihander.primaryKnockback },
          0.22,
        );
      }
    } catch {
      // some entities cannot be knocked back
    }
    if (!r.swept) {
      r.swept = true;
      system.run(() => this.sweep(player, params, r.ids));
    }
  }

  onBeforeDurabilityDamage(ev: ItemComponentBeforeDurabilityDamageEvent): void {
    // a piercing thrust / cut that hits several targets wears the blade once per swing
    const r = this.record(ev.attackingEntity);
    ev.durabilityDamage = r.durability ? 0 : Math.min(1, Math.max(0, ev.durabilityDamage));
    r.durability = true;
  }

  // ------------------------------------------------------------------ Zweihänder sweep
  sweep(player: Player, params: WeaponParams, primary: Set<string>): void {
    if (!player.isValid) return;
    const view = player.getViewDirection();
    const vl = Math.hypot(view.x, view.z) || 1;
    const fx = view.x / vl;
    const fz = view.z / vl;
    const damage = Math.max(1, Math.round((params.damage || 8) * RULES.zweihander.sweepDamageFactor));
    let targets: Entity[] = [];
    try {
      targets = player.dimension.getEntities({ location: player.location, maxDistance: RULES.zweihander.sweepRadius });
    } catch {
      return;
    }
    let hits = 0;
    for (const t of targets) {
      if (!t.isValid || t.id === player.id || primary.has(t.id)) continue;
      if (!this.canSweep(player, t)) continue;
      const h = horizontal(player.location, t.location);
      if (h.d < 0.01 || (h.x * fx + h.z * fz) / h.d < RULES.zweihander.sweepCone) continue;
      this.sweeping = true;
      try {
        t.applyDamage(damage, { cause: EntityDamageCause.entityAttack, damagingEntity: player });
        t.applyKnockback({ x: (h.x / h.d) * RULES.zweihander.sweepKnockback, z: (h.z / h.d) * RULES.zweihander.sweepKnockback }, 0.16);
        hits++;
      } catch {
        // target died or was removed
      } finally {
        this.sweeping = false;
      }
      try {
        t.dimension.spawnParticle("minecraft:critical_hit_emitter", { x: t.location.x, y: t.location.y + 1, z: t.location.z });
      } catch {
        // ignore
      }
    }
    if (hits > 0) {
      try {
        player.dimension.playSound("rww.zweihander.sweep", player.location, { volume: 0.8 });
      } catch {
        // ignore
      }
    }
  }

  private canSweep(player: Player, t: Entity): boolean {
    if (PROTECTED_TYPES.has(t.typeId)) return false;
    if (!t.getComponent(EntityComponentTypes.Health)) return false;
    if (t instanceof Player) return world.gameRules.pvp;
    try {
      const tame = t.getComponent(EntityComponentTypes.Tameable) as EntityTameableComponent | undefined;
      if (tame?.isTamed) return false;
    } catch {
      // not tameable
    }
    return true;
  }

  onLeave(id: string): void {
    this.katana.delete(id);
    this.hitThisTick.delete(id);
  }
}
