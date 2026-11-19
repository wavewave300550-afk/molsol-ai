/**
 * The reference loadout the fights are balanced around (enchanted diamond), handed out on request:
 * from the Codex (operators), with `/scriptevent abm:kit`, and to every newcomer in the test world.
 * Pieces go straight into empty armour slots; anything that does not fit is dropped at the player's feet.
 */
import {
  EnchantmentTypes, EntityComponentTypes, EntityEquippableComponent, EntityInventoryComponent, EquipmentSlot,
  ItemComponentTypes, ItemEnchantableComponent, ItemStack, Player,
} from "@minecraft/server";
import { report } from "./core/trace";

function enchanted(id: string, enchantments: Record<string, number>, amount = 1): ItemStack {
  const stack = new ItemStack(id, amount);
  try {
    const c = stack.getComponent(ItemComponentTypes.Enchantable) as ItemEnchantableComponent | undefined;
    if (c) {
      for (const [name, level] of Object.entries(enchantments)) {
        const type = EnchantmentTypes.get(name);
        if (!type) continue;
        try {
          c.addEnchantment({ type, level });
        } catch {
          /* not applicable to this item in this game version: the piece is still handed out */
        }
      }
    }
  } catch (e) {
    report("kit enchant", e);
  }
  return stack;
}

export function giveKit(p: Player): void {
  try {
    const eq = p.getComponent(EntityComponentTypes.Equippable) as EntityEquippableComponent | undefined;
    const inv = (p.getComponent(EntityComponentTypes.Inventory) as EntityInventoryComponent | undefined)?.container;
    const stow = (stack: ItemStack): void => {
      const left = inv ? inv.addItem(stack) : stack;
      if (left) p.dimension.spawnItem(left, p.location);
    };
    const wear = (slot: EquipmentSlot, stack: ItemStack): void => {
      if (eq && !eq.getEquipment(slot)) eq.setEquipment(slot, stack);
      else stow(stack);
    };
    const armour = { protection: 4, unbreaking: 3 };
    wear(EquipmentSlot.Head, enchanted("minecraft:diamond_helmet", armour));
    wear(EquipmentSlot.Chest, enchanted("minecraft:diamond_chestplate", armour));
    wear(EquipmentSlot.Legs, enchanted("minecraft:diamond_leggings", armour));
    wear(EquipmentSlot.Feet, enchanted("minecraft:diamond_boots", armour));
    wear(EquipmentSlot.Offhand, new ItemStack("minecraft:shield", 1));
    stow(enchanted("minecraft:diamond_sword", { sharpness: 5, unbreaking: 3 }));
    stow(new ItemStack("minecraft:cooked_beef", 32));
    stow(new ItemStack("minecraft:golden_apple", 8));
    p.sendMessage({ rawtext: [{ translate: "abm.kit.given" }] });
  } catch (e) {
    report("kit", e);
  }
}
