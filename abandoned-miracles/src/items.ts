/**
 * Items: the four summoning Seals, the four trophies and the Codex.
 *
 * A Seal is used on the floor where the fight should happen. The location is
 * checked first and nothing is ever changed to make room: an unsuitable place
 * simply refuses the summon and keeps the Seal.
 */
import {
  EntityComponentTypes, EntityEquippableComponent, EquipmentSlot, GameMode, Player, system, world,
} from "@minecraft/server";
import { BOSS_KEYS, BossKey, CONFIG } from "./config";
import { SEAL_ITEM, manager } from "./core/manager";
import { V3 } from "./core/math";
import { report } from "./core/trace";
import { openCodex } from "./ui";

export const CODEX_ITEM = "abm:codex";
export const TROPHY: Record<BossKey, string> = {
  vesperra: "abm:ivory_diadem",
  cantor: "abm:bell_fragment",
  nomos: "abm:sovereign_needle",
  orison: "abm:unlived_hourglass",
};
const SEAL_TO_KEY = new Map<string, BossKey>(BOSS_KEYS.map((k) => [SEAL_ITEM[k], k]));
const TROPHY_TO_KEY = new Map<string, BossKey>(BOSS_KEYS.map((k) => [TROPHY[k], k]));
const TROPHY_SOUND: Record<BossKey, string> = {
  vesperra: "abm.vesperra.trophy",
  cantor: "abm.cantor.trophy",
  nomos: "abm.nomos.trophy",
  orison: "abm.orison.trophy",
};

const lastUse = new Map<string, number>();

function debounce(p: Player): boolean {
  const now = system.currentTick;
  if (now - (lastUse.get(p.id) ?? -100) < 10) return false;
  lastUse.set(p.id, now);
  return true;
}

function consumeHeld(p: Player, typeId: string): void {
  try {
    if (p.getGameMode() === GameMode.Creative) return;
    const eq = p.getComponent(EntityComponentTypes.Equippable) as EntityEquippableComponent | undefined;
    const held = eq?.getEquipment(EquipmentSlot.Mainhand);
    if (!eq || !held || held.typeId !== typeId) return;
    if (held.amount > 1) {
      held.amount -= 1;
      eq.setEquipment(EquipmentSlot.Mainhand, held);
    } else {
      eq.setEquipment(EquipmentSlot.Mainhand, undefined);
    }
  } catch (e) {
    report("consumeHeld", e);
  }
}

/** Try to summon; tells the player exactly why when it cannot be done. */
export function useSeal(p: Player, key: BossKey, floor: V3, force = false): boolean {
  const stats = CONFIG.bosses[key];
  const res = manager.trySummon(p, key, floor, force);
  if (res.ok) {
    consumeHeld(p, SEAL_ITEM[key]);
    for (const q of p.dimension.getPlayers({ location: floor, maxDistance: 64 })) {
      q.sendMessage({ rawtext: [{ translate: `abm.summon.ok.${key}` }] });
    }
    return true;
  }
  const pct = String(Math.round((res.coverage ?? 0) * 100));
  p.sendMessage({ rawtext: [{ translate: `abm.summon.fail.${res.reason ?? "unknown"}`, with: [pct] }] });
  if (res.reason === "floor" || res.reason === "ceiling") {
    p.sendMessage({ rawtext: [{ translate: "abm.summon.need", with: [String(stats.arenaRadius * 2 + 1), String(stats.clearance)] }] });
  }
  return false;
}

export function initItems(): void {
  world.afterEvents.playerInteractWithBlock.subscribe((ev) => {
    if (!ev.isFirstEvent) return;
    const id = ev.beforeItemStack?.typeId ?? ev.itemStack?.typeId;
    const key = id ? SEAL_TO_KEY.get(id) : undefined;
    if (!key || !debounce(ev.player)) return;
    const b = ev.block;
    useSeal(ev.player, key, { x: b.x + 0.5, y: b.y + 1, z: b.z + 0.5 });
  });

  world.afterEvents.itemUse.subscribe((ev) => {
    const id = ev.itemStack.typeId;
    const p = ev.source;
    if (id === CODEX_ITEM) {
      if (debounce(p)) void openCodex(p);
      return;
    }
    const seal = SEAL_TO_KEY.get(id);
    if (seal) {
      // used in the air: take the block being looked at, if any
      if (!debounce(p)) return;
      try {
        const hit = p.getBlockFromViewDirection({ maxDistance: 10 });
        if (hit) {
          const b = hit.block;
          useSeal(p, seal, { x: b.x + 0.5, y: b.y + 1, z: b.z + 0.5 });
        }
      } catch (e) {
        report("seal raycast", e);
      }
      return;
    }
    const trophy = TROPHY_TO_KEY.get(id);
    if (trophy && debounce(p)) {
      try {
        p.dimension.playSound(TROPHY_SOUND[trophy], p.location, { volume: 0.8 });
        p.onScreenDisplay.setActionBar({ rawtext: [{ translate: `abm.trophy.${trophy}` }] });
      } catch (e) {
        report("trophy", e);
      }
    }
  });

  world.afterEvents.playerLeave.subscribe((ev) => lastUse.delete(ev.playerId));
}
