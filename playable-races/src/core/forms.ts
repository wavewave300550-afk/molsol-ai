/**
 * Race forms are worn as a locked "crest" in the head slot.  The crest's attachable
 * renders the creature on the player's own animated skeleton (no player override).
 * Visual states are separate crest items (e.g. plrace:form_golem_siege) - swapping the
 * item swaps the configuration, and its attachable plays the transition animation.
 * Enchantments infused into the crest are carried across every swap.
 */
import { EnchantmentType, EquipmentSlot, ItemLockMode, ItemStack, Player, system } from "@minecraft/server";
import { NS, TAG_FORM } from "../config.js";
import { RaceDef } from "../races/types.js";
import { Session } from "./session.js";
import { warn } from "./util.js";

export function crestId(race: RaceDef, variant: string): string {
  return variant ? `${NS}:form_${race.key}_${variant}` : `${NS}:form_${race.key}`;
}

function equippable(p: Player) {
  try {
    return p.getComponent("minecraft:equippable");
  } catch {
    return undefined;
  }
}

export function headItem(p: Player): ItemStack | undefined {
  try {
    return equippable(p)?.getEquipment(EquipmentSlot.Head);
  } catch {
    return undefined;
  }
}

export function isCrest(item: ItemStack | undefined): boolean {
  return !!item && item.hasTag(TAG_FORM);
}

function makeCrest(race: RaceDef, variant: string, s: Session): ItemStack {
  const it = new ItemStack(crestId(race, variant), 1);
  it.lockMode = ItemLockMode.slot;
  it.keepOnDeath = true;
  if (s.data.ench.length > 0) {
    try {
      const ench = it.getComponent("minecraft:enchantable");
      if (ench) {
        for (const [id, level] of s.data.ench) {
          try {
            ench.addEnchantment({ type: new EnchantmentType(id), level });
          } catch {
            /* incompatible or unknown enchantment: skip */
          }
        }
      }
    } catch (e) {
      warn("crest enchant copy failed", e);
    }
  }
  return it;
}

/** Remember the enchantments currently on the worn crest. */
export function captureEnchantments(p: Player, s: Session): void {
  const it = headItem(p);
  if (!isCrest(it)) return;
  try {
    const ench = it!.getComponent("minecraft:enchantable");
    if (!ench) return;
    s.data.ench = ench.getEnchantments().map((e) => [e.type.id, e.level] as [string, number]);
    s.dirty = true;
  } catch {
    /* ignore */
  }
}

/**
 * Ensure the correct crest variant is worn.  Returns false if the head slot holds a
 * non-crest item that could not be moved (the form then stays veiled until there is room).
 */
export function showForm(p: Player, race: RaceDef, s: Session, variant: string): boolean {
  if (s.data.veiled) return true;
  const eq = equippable(p);
  if (!eq) return false;
  const want = crestId(race, variant);
  const cur = headItem(p);
  if (cur && cur.typeId === want) {
    s.shownVariant = variant;
    return true;
  }
  if (cur && !isCrest(cur)) {
    // a real helmet is worn: move it into the inventory to make room
    const inv = p.getComponent("minecraft:inventory")?.container;
    if (!inv || inv.emptySlotsCount === 0) return false;
    try {
      const left = inv.addItem(cur);
      if (left) return false;
    } catch {
      return false;
    }
  }
  try {
    eq.setEquipment(EquipmentSlot.Head, makeCrest(race, variant, s));
    s.shownVariant = variant;
    return true;
  } catch (e) {
    warn("could not equip form", e);
    return false;
  }
}

/** Remove any crest from the head slot (veil / race removal). */
export function hideForm(p: Player): void {
  const eq = equippable(p);
  if (!eq) return;
  const cur = headItem(p);
  if (cur && isCrest(cur)) {
    try {
      eq.setEquipment(EquipmentSlot.Head, undefined);
    } catch (e) {
      warn("could not remove form", e);
    }
  }
}

/** Remove stray crests from the inventory (e.g. after /give or old race). */
export function purgeStrayCrests(p: Player): void {
  const inv = p.getComponent("minecraft:inventory")?.container;
  if (!inv) return;
  for (let i = 0; i < inv.size; i++) {
    const it = inv.getItem(i);
    if (it && it.hasTag(TAG_FORM)) {
      try {
        inv.setItem(i, undefined);
      } catch {
        /* ignore */
      }
    }
  }
}

/** Give the race focus if the player does not have one; returns true if given. */
export function ensureFocus(p: Player, race: RaceDef): boolean {
  const inv = p.getComponent("minecraft:inventory")?.container;
  if (!inv) return false;
  for (let i = 0; i < inv.size; i++) {
    const it = inv.getItem(i);
    if (it && it.typeId === race.focusItem) return false;
  }
  try {
    const off = equippable(p)?.getEquipment(EquipmentSlot.Offhand);
    if (off && off.typeId === race.focusItem) return false;
  } catch {
    /* ignore */
  }
  const focus = new ItemStack(race.focusItem, 1);
  focus.lockMode = ItemLockMode.inventory;
  focus.keepOnDeath = true;
  try {
    const left = inv.addItem(focus);
    if (left) {
      system.run(() => {
        try {
          p.dimension.spawnItem(focus, p.location);
        } catch {
          /* ignore */
        }
      });
    }
    return true;
  } catch {
    return false;
  }
}

/** Remove focus items that do not belong to the player's current race. */
export function purgeFoci(p: Player, keep?: string): void {
  const inv = p.getComponent("minecraft:inventory")?.container;
  if (!inv) return;
  for (let i = 0; i < inv.size; i++) {
    const it = inv.getItem(i);
    if (it && it.hasTag(`${NS}:focus`) && it.typeId !== keep) {
      try {
        inv.setItem(i, undefined);
      } catch {
        /* ignore */
      }
    }
  }
}

export function holdingFocus(p: Player, race: RaceDef | undefined): boolean {
  if (!race) return false;
  try {
    const it = p.getComponent("minecraft:inventory")?.container?.getItem(p.selectedSlotIndex);
    return !!it && it.typeId === race.focusItem;
  } catch {
    return false;
  }
}
