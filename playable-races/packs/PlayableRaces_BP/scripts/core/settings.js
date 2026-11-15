import { world } from "@minecraft/server";
import { WORLD_SETTINGS } from "../config.js";
import { safeJson, warn } from "./util.js";
const DEFAULTS = { pvp: true, change: "cooldown", changeDays: 3, bloodChance: 34, bloodFog: true, autoOpen: true, hudAlways: false,
    uniqueExclusive: true, heavenFx: true };
let cache;
export function settings() {
    if (!cache) {
        let raw;
        try {
            raw = world.getDynamicProperty(WORLD_SETTINGS);
        }
        catch {
            raw = undefined;
        }
        cache = { ...DEFAULTS, ...safeJson(raw, {}) };
    }
    return cache;
}
export function updateSettings(patch) {
    cache = { ...settings(), ...patch };
    try {
        world.setDynamicProperty(WORLD_SETTINGS, JSON.stringify(cache));
    }
    catch (e) {
        warn("could not save settings", e);
    }
}
export function pvpAllowed() {
    let rule = true;
    try {
        rule = world.gameRules.pvp;
    }
    catch {
        rule = true;
    }
    return rule && settings().pvp;
}
