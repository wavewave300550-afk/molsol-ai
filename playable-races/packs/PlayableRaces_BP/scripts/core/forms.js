import { EnchantmentType, EquipmentSlot, ItemLockMode, ItemStack, system } from "@minecraft/server";
import { NS, TAG_FORM } from "../config.js";
import { warn } from "./util.js";
export function crestId(race, variant) {
    return variant ? `${NS}:form_${race.key}_${variant}` : `${NS}:form_${race.key}`;
}
export function staticId(race) {
    return `${NS}:form_${race.key}_static`;
}
export function wantsStill(s, race) {
    return !!s.data.still?.includes(race.code);
}
function equippable(p) {
    try {
        return p.getComponent("minecraft:equippable");
    }
    catch {
        return undefined;
    }
}
export function headItem(p) {
    try {
        return equippable(p)?.getEquipment(EquipmentSlot.Head);
    }
    catch {
        return undefined;
    }
}
export function isCrest(item) {
    return !!item && item.hasTag(TAG_FORM);
}
function makeCrest(id, s) {
    const it = new ItemStack(id, 1);
    it.lockMode = ItemLockMode.slot;
    it.keepOnDeath = true;
    if (s.data.ench.length > 0) {
        try {
            const ench = it.getComponent("minecraft:enchantable");
            if (ench) {
                for (const [id, level] of s.data.ench) {
                    try {
                        ench.addEnchantment({ type: new EnchantmentType(id), level });
                    }
                    catch {
                    }
                }
            }
        }
        catch (e) {
            warn("crest enchant copy failed", e);
        }
    }
    return it;
}
export function captureEnchantments(p, s) {
    const it = headItem(p);
    if (!isCrest(it))
        return;
    try {
        const ench = it.getComponent("minecraft:enchantable");
        if (!ench)
            return;
        s.data.ench = ench.getEnchantments().map((e) => [e.type.id, e.level]);
        s.dirty = true;
    }
    catch {
    }
}
export function showForm(p, race, s, variant) {
    if (s.data.veiled)
        return true;
    const eq = equippable(p);
    if (!eq)
        return false;
    const want = wantsStill(s, race) ? staticId(race) : crestId(race, variant);
    const cur = headItem(p);
    if (cur && cur.typeId === want) {
        s.shownVariant = variant;
        return true;
    }
    if (cur && !isCrest(cur)) {
        const inv = p.getComponent("minecraft:inventory")?.container;
        if (!inv || inv.emptySlotsCount === 0)
            return false;
        try {
            const left = inv.addItem(cur);
            if (left)
                return false;
        }
        catch {
            return false;
        }
    }
    try {
        eq.setEquipment(EquipmentSlot.Head, makeCrest(want, s));
        s.shownVariant = variant;
        return true;
    }
    catch (e) {
        warn("could not equip form", e);
        return false;
    }
}
export function hideForm(p) {
    const eq = equippable(p);
    if (!eq)
        return;
    const cur = headItem(p);
    if (cur && isCrest(cur)) {
        try {
            eq.setEquipment(EquipmentSlot.Head, undefined);
        }
        catch (e) {
            warn("could not remove form", e);
        }
    }
}
export function purgeStrayCrests(p) {
    const inv = p.getComponent("minecraft:inventory")?.container;
    if (!inv)
        return;
    for (let i = 0; i < inv.size; i++) {
        const it = inv.getItem(i);
        if (it && it.hasTag(TAG_FORM)) {
            try {
                inv.setItem(i, undefined);
            }
            catch {
            }
        }
    }
}
export function ensureFocus(p, race) {
    const inv = p.getComponent("minecraft:inventory")?.container;
    if (!inv)
        return false;
    for (let i = 0; i < inv.size; i++) {
        const it = inv.getItem(i);
        if (it && it.typeId === race.focusItem)
            return false;
    }
    try {
        const off = equippable(p)?.getEquipment(EquipmentSlot.Offhand);
        if (off && off.typeId === race.focusItem)
            return false;
    }
    catch {
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
                }
                catch {
                }
            });
        }
        return true;
    }
    catch {
        return false;
    }
}
export function purgeFoci(p, keep) {
    const inv = p.getComponent("minecraft:inventory")?.container;
    if (!inv)
        return;
    for (let i = 0; i < inv.size; i++) {
        const it = inv.getItem(i);
        if (it && it.hasTag(`${NS}:focus`) && it.typeId !== keep) {
            try {
                inv.setItem(i, undefined);
            }
            catch {
            }
        }
    }
}
export function holdingFocus(p, race) {
    if (!race)
        return false;
    try {
        const it = p.getComponent("minecraft:inventory")?.container?.getItem(p.selectedSlotIndex);
        return !!it && it.typeId === race.focusItem;
    }
    catch {
        return false;
    }
}
