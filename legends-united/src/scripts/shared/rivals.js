// Clash of Legends: every boss is the enemy of every other boss - whichever add-on it came from,
// even two of the same kind. A boss only spares itself and its own followers (the Word's Choir).
// Bosses fight bosses and players, nothing else: ordinary mobs, pets and villagers are left alone.
import { Player } from "@minecraft/server";
export const BOSS_FAMILIES = ["dim11_being", "fb_boss", "legends_boss", "legends_choir"];
/** Damage multiplier when a boss strikes another boss (so a clash ends in a few minutes). */
export const RIVAL_DAMAGE = 3;
let acting;
/** The boss whose turn is running (set by each engine around its tick). */
export function setActing(e) {
    acting = e;
}
function alive(e) {
    try {
        if (!e.isValid)
            return false;
        const h = e.getComponent("minecraft:health");
        return !h || h.currentValue > 0;
    }
    catch {
        return false;
    }
}
export function isBoss(e) {
    try {
        return !(e instanceof Player) && BOSS_FAMILIES.some((f) => e.matches({ families: [f] }));
    }
    catch {
        return false;
    }
}
/** A boss and its followers share one group: the follower's owner id, otherwise its own id. */
export function groupOf(e) {
    try {
        if (e.matches({ families: ["legends_choir"] })) {
            const o = e.getDynamicProperty("legends:owner");
            if (typeof o === "string")
                return o;
        }
    }
    catch {
        // ignore
    }
    return e.id;
}
/** True when `e` is a living boss outside the group of the boss that is acting. */
export function isRivalOf(_team, e) {
    if (!e || e instanceof Player || !alive(e) || !isBoss(e))
        return false;
    return !(acting && acting.isValid && groupOf(acting) === groupOf(e));
}
/** Living rival bosses within `radius` of `at`. */
export function rivalsNear(_team, dim, at, radius) {
    const out = new Map();
    for (const f of BOSS_FAMILIES) {
        try {
            for (const e of dim.getEntities({ location: at, maxDistance: radius, families: [f] }))
                if (isRivalOf(undefined, e))
                    out.set(e.id, e);
        }
        catch {
            // unloaded
        }
    }
    return [...out.values()];
}
/** Damage from `src` to `victim` that the hosts' own-team guards must let through. */
export function bossDuel(src, victim) {
    return !!src && !!victim && isBoss(src) && isBoss(victim) && groupOf(src) !== groupOf(victim);
}
