/**
 * Kintsugi Heart (victory reward). Held in the off-hand, it mends its bearer
 * with gold when they fall below 30% health: Regeneration II and Absorption
 * for a moment, then it needs 90 seconds to cool.
 */
import { EquipmentSlot, Player, system, world } from "@minecraft/server";
import { FX, ITEM, SND } from "./config.js";
import { particle } from "./core/fx.js";
import { add, v } from "./core/vec.js";

const ready = new Map<string, number>();
const COOLDOWN = 20 * 90;

export function tickCharms(): void {
  const now = system.currentTick;
  for (const p of world.getPlayers()) {
    let off;
    try {
      off = p.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Offhand);
    } catch {
      continue;
    }
    if (off?.typeId !== ITEM.heart) continue;
    const h = p.getComponent("minecraft:health");
    if (!h || h.currentValue <= 0 || h.currentValue > h.effectiveMax * 0.3) continue;
    if ((ready.get(p.id) ?? 0) > now) continue;
    ready.set(p.id, now + COOLDOWN);
    mend(p);
  }
}

function mend(p: Player): void {
  try {
    p.addEffect("regeneration", 120, { amplifier: 1, showParticles: true });
    p.addEffect("absorption", 600, { amplifier: 0, showParticles: false });
    particle(p.dimension, FX.goldBurst, add(p.location, v(0, 1, 0)));
    p.playSound(SND.chime, { volume: 1, pitch: 1.3 });
    p.onScreenDisplay.setActionBar("§6The Kintsugi Heart mends you with gold.");
  } catch {
    // ignore
  }
}
