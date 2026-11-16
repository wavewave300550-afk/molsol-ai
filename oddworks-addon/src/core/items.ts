import { EntityComponentTypes, GameMode, ItemComponentTypes, ItemStack, Player } from "@minecraft/server";
import { ID } from "../config.js";
import { fx, sound } from "./fx.js";

export function container(p: Player) {
  try {
    return p.getComponent(EntityComponentTypes.Inventory)?.container;
  } catch {
    return undefined;
  }
}

export function heldItem(p: Player): ItemStack | undefined {
  try {
    return container(p)?.getItem(p.selectedSlotIndex);
  } catch {
    return undefined;
  }
}

export function heldType(p: Player): string | undefined {
  return heldItem(p)?.typeId;
}

export function isCreative(p: Player): boolean {
  try {
    return p.getGameMode() === GameMode.Creative;
  } catch {
    return false;
  }
}

export function enchantLevel(item: ItemStack | undefined, id: string): number {
  try {
    return item?.getComponent(ItemComponentTypes.Enchantable)?.getEnchantment(id)?.level ?? 0;
  } catch {
    return 0;
  }
}

/** Copy durability, enchantments, name, lore, lock/keep flags and dynamic properties onto a new item type. */
export function convertStack(old: ItemStack, newType: string): ItemStack {
  const neu = new ItemStack(newType, 1);
  try {
    const od = old.getComponent(ItemComponentTypes.Durability);
    const nd = neu.getComponent(ItemComponentTypes.Durability);
    if (od && nd) nd.damage = Math.min(nd.maxDurability, od.damage);
  } catch {
    /* no durability */
  }
  try {
    const oe = old.getComponent(ItemComponentTypes.Enchantable);
    const ne = neu.getComponent(ItemComponentTypes.Enchantable);
    if (oe && ne) {
      for (const e of oe.getEnchantments()) {
        try {
          if (ne.canAddEnchantment(e)) ne.addEnchantment(e);
        } catch {
          /* incompatible enchantment */
        }
      }
    }
  } catch {
    /* not enchantable */
  }
  if (old.nameTag) neu.nameTag = old.nameTag;
  try {
    neu.setLore(old.getLore());
  } catch {
    /* lore too long */
  }
  try {
    neu.keepOnDeath = old.keepOnDeath;
    neu.lockMode = old.lockMode;
  } catch {
    /* ignore */
  }
  for (const k of old.getDynamicPropertyIds()) neu.setDynamicProperty(k, old.getDynamicProperty(k));
  return neu;
}

/** Swap the held stack to another ODDWORKS variant (sheathed <-> drawn, ready <-> line out). */
export function swapHeld(p: Player, from: string, to: string, slot = p.selectedSlotIndex): boolean {
  const inv = container(p);
  if (!inv) return false;
  const cur = inv.getItem(slot);
  if (!cur || cur.typeId !== from) return false;
  inv.setItem(slot, convertStack(cur, to));
  return true;
}

/** Durability loss honouring Unbreaking; breaks the item at 0. Returns false if it broke. */
export function wear(p: Player, amount: number, slot = p.selectedSlotIndex): boolean {
  if (amount <= 0 || isCreative(p)) return true;
  const inv = container(p);
  const item = inv?.getItem(slot);
  if (!inv || !item) return true;
  const dur = item.getComponent(ItemComponentTypes.Durability);
  if (!dur) return true;
  const unb = enchantLevel(item, "unbreaking");
  let dmg = 0;
  for (let i = 0; i < amount; i++) if (Math.random() < 1 / (unb + 1)) dmg++;
  if (dmg === 0) return true;
  if (dur.damage + dmg >= dur.maxDurability) {
    inv.setItem(slot, undefined);
    sound(p.dimension, "random.break", p.location);
    fx(p.dimension, "oddworks:clang_spark", p.getHeadLocation(), { count: 10 });
    return false;
  }
  dur.damage += dmg;
  inv.setItem(slot, item);
  return true;
}

/** Tooltip lore explaining the controls (added once to stacks that have none). */
export const LORE: Record<string, string[]> = {
  [ID.goggles]: [
    "§7Carved antler · sun-ice slits",
    "§e[Hold Use]§7 absorb sunlight, release: §bGlacial Beam",
    "§e[Sneak + Use]§7 §fSnowblind§7 glare flash",
    "§e[Sneak + Hold Use]§7 facing the sun: §6Sun Dog",
    "§8Snow glare strengthens it · darkness starves it",
  ],
  [ID.handline]: [
    "§7Drowned-silk line · 96 blocks on the spool",
    "§e[Hold Use]§7 whirl overhead, release: §bCast",
    "§e[Hold Use]§7 line out: §aReel / Haul§7 · §e[Sneak]§7 pay out",
    "§e[Sneak + Use]§7 line out: §cSnap",
    "§8Hooks blocks, mobs, boats, items and fish",
  ],
  [ID.cane]: [
    "§7Shikomizue · a blade asleep in bamboo",
    "§e[Hold Use]§7 grip, release on the glint: §fIai§7 draw-cut",
    "§e[Use]§7 drawn: §bDeflect§7 · §e[Sneak + Use]§7 §cNoto§7 sheathe",
    "§8Cuts bleed by creature · armour turns the edge",
  ],
};
LORE[ID.handlineCast] = LORE[ID.handline];
LORE[ID.caneDrawn] = LORE[ID.cane];

export function ensureLore(p: Player): void {
  const inv = container(p);
  const item = inv?.getItem(p.selectedSlotIndex);
  if (!inv || !item) return;
  const lore = LORE[item.typeId];
  if (!lore) return;
  try {
    if (item.getLore().length > 0) return;
    item.setLore(lore);
    inv.setItem(p.selectedSlotIndex, item);
  } catch {
    /* ignore */
  }
}
