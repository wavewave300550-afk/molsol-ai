import { world } from "@minecraft/server";
import { WORLD_UNIQUE } from "../config.js";
import { settings } from "../core/settings.js";
import { safeJson, warn } from "../core/util.js";
let cache;
function holders() {
    if (!cache) {
        let raw;
        try {
            raw = world.getDynamicProperty(WORLD_UNIQUE);
        }
        catch {
            raw = undefined;
        }
        cache = safeJson(raw, {});
    }
    return cache;
}
function store() {
    try {
        world.setDynamicProperty(WORLD_UNIQUE, JSON.stringify(holders()));
    }
    catch (e) {
        warn("could not save unique holders", e);
    }
}
export const isUnique = (r) => (r?.rarity ?? "normal") === "unique";
export function holderOf(code) {
    return holders()[code];
}
export function uniqueBlocked(p, race) {
    if (!isUnique(race) || !settings().uniqueExclusive)
        return undefined;
    const h = holderOf(race.code);
    if (!h || h.id === p.id)
        return undefined;
    return `${race.name} is a Unique lineage already held by ${h.name}. Only one may hold it in this world.`;
}
export function claim(p, race, day) {
    if (!isUnique(race))
        return;
    const h = holders()[race.code];
    if (h && h.id !== p.id && settings().uniqueExclusive)
        return;
    holders()[race.code] = { id: p.id, name: p.name, day };
    store();
}
export function releasePlayer(id, keep) {
    let changed = false;
    for (const [code, h] of Object.entries(holders())) {
        if (h.id === id && code !== keep) {
            delete holders()[code];
            changed = true;
        }
    }
    if (changed)
        store();
}
export function releaseCode(code) {
    if (!holders()[code])
        return false;
    delete holders()[code];
    store();
    return true;
}
export function uniqueStatus() {
    const list = Object.entries(holders());
    if (list.length === 0)
        return "No Unique lineage is held.";
    return list.map(([code, h]) => `${code}: ${h.name}`).join(", ");
}
