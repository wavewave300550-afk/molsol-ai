// "The axe glows deep crimson" during Oath of the Grizzly: the held axe is swapped for an
// identical awakened copy (its own glowing texture + flame particles) and swapped back after.
// All item data (durability, enchantments, name, lore, lock / keep-on-death) is carried over both
// ways, and any awakened copy found outside an active Ultimate is restored automatically.
import { EntityComponentTypes, EquipmentSlot, ItemStack } from "@minecraft/server";
import { AWAKENED_ID, AXE_ID } from "./config.js";
function copyItemData(src, dst) {
    try {
        if (src.nameTag)
            dst.nameTag = src.nameTag;
    }
    catch {
        // ignore
    }
    try {
        const lore = src.getLore();
        if (lore.length)
            dst.setLore(lore);
    }
    catch {
        // ignore
    }
    try {
        dst.keepOnDeath = src.keepOnDeath;
        dst.lockMode = src.lockMode;
    }
    catch {
        // ignore
    }
    try {
        const a = src.getComponent("minecraft:durability");
        const b = dst.getComponent("minecraft:durability");
        if (a && b)
            b.damage = Math.min(a.damage, b.maxDurability - 1);
    }
    catch {
        // ignore
    }
    try {
        const a = src.getComponent("minecraft:enchantable");
        const b = dst.getComponent("minecraft:enchantable");
        if (a && b) {
            const list = a.getEnchantments();
            if (list.length)
                b.addEnchantments(list);
        }
    }
    catch {
        // ignore
    }
    try {
        for (const id of src.getDynamicPropertyIds())
            dst.setDynamicProperty(id, src.getDynamicProperty(id));
    }
    catch {
        // ignore
    }
}
function convert(item, toId) {
    const next = new ItemStack(toId, 1);
    copyItemData(item, next);
    return next;
}
/** Swaps the axe in the main hand for its awakened copy. */
export function awaken(p) {
    try {
        const inv = p.getComponent(EntityComponentTypes.Inventory)?.container;
        if (!inv)
            return false;
        const slot = p.selectedSlotIndex;
        const item = inv.getItem(slot);
        if (!item || item.typeId !== AXE_ID)
            return false;
        inv.setItem(slot, convert(item, AWAKENED_ID));
        return true;
    }
    catch {
        return false;
    }
}
/** Turns every awakened copy the player carries back into the normal axe. */
export function restore(p) {
    let n = 0;
    try {
        const inv = p.getComponent(EntityComponentTypes.Inventory)?.container;
        if (inv) {
            for (let i = 0; i < inv.size; i++) {
                const item = inv.getItem(i);
                if (item && item.typeId === AWAKENED_ID) {
                    inv.setItem(i, convert(item, AXE_ID));
                    n++;
                }
            }
        }
        const eq = p.getComponent(EntityComponentTypes.Equippable);
        const off = eq?.getEquipment(EquipmentSlot.Offhand);
        if (eq && off && off.typeId === AWAKENED_ID) {
            eq.setEquipment(EquipmentSlot.Offhand, convert(off, AXE_ID));
            n++;
        }
    }
    catch {
        // ignore
    }
    return n;
}
