import { system } from "@minecraft/server";
import { PROP_DATA } from "../config.js";
import { safeJson, warn } from "./util.js";
export function defaultData() {
    return { v: 1, race: "", sel: 0, cd: {}, charges: {}, res: {}, st: {}, veiled: false, ench: [], joined: false,
        lastChange: -999, locks: [], stats: {} };
}
const sessions = new Map();
export function load(p) {
    let s = sessions.get(p.id);
    if (s)
        return s;
    let data = defaultData();
    try {
        data = { ...defaultData(), ...safeJson(p.getDynamicProperty(PROP_DATA), {}) };
    }
    catch (e) {
        warn("could not read player data", e);
    }
    s = {
        id: p.id, name: p.name, data, dirty: false, readyAt: new Map(), chargeAt: new Map(), lastCast: -999,
        lastInput: -999, lastRawInput: -999, hudUntil: 0, shownVariant: "", flags: new Map(), num: new Map(), menuOpen: false,
    };
    const t = system.currentTick;
    for (const [id, rem] of Object.entries(data.cd))
        if (rem > 0)
            s.readyAt.set(id, t + rem);
    for (const [id, rem] of Object.entries(data.charges))
        if (rem > 0)
            s.chargeAt.set(id, t + rem);
    sessions.set(p.id, s);
    return s;
}
export function get(p) {
    return sessions.get(p.id) ?? load(p);
}
export function peek(id) {
    return sessions.get(id);
}
export function all() {
    return sessions.values();
}
export function drop(id) {
    sessions.delete(id);
}
export function save(p, s, force = false) {
    if (!s.dirty && !force)
        return;
    const t = system.currentTick;
    const cd = {};
    for (const [id, at] of s.readyAt)
        if (at > t)
            cd[id] = at - t;
    const ch = {};
    for (const [id, at] of s.chargeAt)
        if (at > t)
            ch[id] = at - t;
    s.data.cd = cd;
    s.data.charges = ch;
    try {
        p.setDynamicProperty(PROP_DATA, JSON.stringify(s.data));
        s.dirty = false;
    }
    catch (e) {
        warn("could not save player data", e);
    }
}
export function flag(s, name, ticks) {
    s.flags.set(name, system.currentTick + ticks);
}
export function hasFlag(s, name) {
    const at = s.flags.get(name);
    return at !== undefined && at > system.currentTick;
}
export function clearFlag(s, name) {
    s.flags.delete(name);
}
