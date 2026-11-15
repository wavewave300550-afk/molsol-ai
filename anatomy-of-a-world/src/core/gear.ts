/**
 * Gear earned from THE MIGRATING MOUNTAIN.
 *
 *   Strata Breaker (anatomy:strata_breaker) - use: "Fold Slam", a ridge of rock bursts forward along
 *     the ground for 7 blocks; mobs on it take 8 damage and are thrown up. 8 s cooldown, 2 durability.
 *     Never breaks blocks and never hurts other players.
 *   Anchorage Greaves (anatomy:anchorage_greaves) - no fall damage; while sneaking the wearer is
 *     rooted (Resistance I).
 */
import { EntityDamageCause, EntityHurtBeforeEvent, EquipmentSlot, GameMode, ItemStack, MolangVariableMap, Player, system } from "@minecraft/server";

export const STRATA_BREAKER = "anatomy:strata_breaker";
export const ANCHORAGE_GREAVES = "anatomy:anchorage_greaves";

function feet(p: Player): ItemStack | undefined {
  try {
    return p.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Feet);
  } catch {
    return undefined;
  }
}

/** Fold Slam cooldown (ticks), kept by the script: the engine may or may not start the item cooldown on use itself. */
const SLAM_COOLDOWN = 160;
const lastSlam = new Map<string, number>();

/** Strata Breaker: Fold Slam (runs outside restricted execution; called from both onUse and onUseOn). */
export function foldSlam(p: Player): void {
  const inv = p.getComponent("minecraft:inventory")?.container;
  if (!inv) return;
  const slot = p.selectedSlotIndex;
  const it = inv.getItem(slot);
  if (it?.typeId !== STRATA_BREAKER) return;
  const now = system.currentTick;
  if (now - (lastSlam.get(p.id) ?? -SLAM_COOLDOWN) < SLAM_COOLDOWN - 2) return;
  lastSlam.set(p.id, now);
  try {
    it.getComponent("minecraft:cooldown")?.startCooldown(p); // the hotbar overlay
  } catch {
    /* ignore */
  }
  if (p.getGameMode() !== GameMode.Creative) {
    const dur = it.getComponent("minecraft:durability");
    if (dur) {
      dur.damage = Math.min(dur.maxDurability, dur.damage + 2);
      inv.setItem(slot, dur.damage >= dur.maxDurability ? undefined : it);
    }
  }
  const dim = p.dimension;
  const base = { ...p.location };
  // along the ground where the player faces (yaw, so it also works while looking straight down)
  const yaw = (p.getRotation().y * Math.PI) / 180;
  const dx = -Math.sin(yaw);
  const dz = Math.cos(yaw);
  try {
    dim.playSound("anatomy.mm.quake", base, { volume: 0.8, pitch: 1.35 });
    dim.playSound("anatomy.mm.crack", base, { volume: 0.7, pitch: 1.2 });
  } catch {
    /* ignore */
  }
  const hit = new Set<string>([p.id]);
  for (let i = 1; i <= 7; i++)
    system.runTimeout(() => {
      if (!p.isValid) return;
      const pt = { x: base.x + dx * i, y: base.y, z: base.z + dz * i };
      try {
        const m = new MolangVariableMap();
        m.setFloat("variable.size", 0.9);
        dim.spawnParticle("anatomy:mm_debris", pt, m);
        dim.spawnParticle("anatomy:mm_dust", pt, m);
      } catch {
        /* unloaded */
      }
      let near: import("@minecraft/server").Entity[] = [];
      try {
        near = dim.getEntities({ location: pt, maxDistance: 1.9, excludeTypes: ["minecraft:item", "minecraft:xp_orb"], excludeFamilies: ["player"] });
      } catch {
        near = [];
      }
      for (const e of near) {
        if (hit.has(e.id)) continue;
        hit.add(e.id);
        try {
          e.applyDamage(8, { cause: EntityDamageCause.entityAttack, damagingEntity: p });
          e.applyImpulse({ x: dx * 0.35, y: 0.6, z: dz * 0.35 });
        } catch {
          /* immovable or gone */
        }
      }
    }, i * 2);
}

/** Anchorage Greaves: no fall damage (world.beforeEvents.entityHurt). */
export function greavesHurtBefore(ev: EntityHurtBeforeEvent): void {
  if (ev.damageSource.cause !== EntityDamageCause.fall) return;
  const p = ev.hurtEntity;
  if (!(p instanceof Player)) return;
  if (feet(p)?.typeId === ANCHORAGE_GREAVES) ev.cancel = true;
}

/** Anchorage Greaves: rooted while sneaking (call every 10 ticks). */
export function greavesTick(players: Player[]): void {
  for (const p of players) {
    try {
      if (!p.isSneaking || feet(p)?.typeId !== ANCHORAGE_GREAVES) continue;
      p.addEffect("resistance", 15, { amplifier: 0, showParticles: false });
    } catch {
      /* ignore */
    }
  }
}
