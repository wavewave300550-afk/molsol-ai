// Legends United: the three hosts (Eleventh Dimension, Final Bosses, Legendary Beings) are rival
// teams. A boss treats the bosses of the other two hosts as enemies - it targets them, its attacks
// hit them, and it hits them harder than it hits players so a clash ends in a few minutes.
// Bosses of the same host stay allies.
import { Player } from "@minecraft/server";
export const TEAMS = {
    dim11: ["dim11_being"],
    fb: ["fb_boss"],
    legends: ["legends_boss", "legends_choir"],
};
/** Damage multiplier when a boss strikes a rival boss. */
export const RIVAL_DAMAGE = 3;
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
export function teamOf(e) {
    try {
        for (const [team, fams] of Object.entries(TEAMS))
            for (const f of fams)
                if (e.matches({ families: [f] }))
                    return team;
    }
    catch {
        // invalid entity
    }
    return undefined;
}
/** True when `e` is a living boss of another host than `team`. */
export function isRivalOf(team, e) {
    if (!e || e instanceof Player || !alive(e))
        return false;
    const t = teamOf(e);
    return t !== undefined && t !== team;
}
/** Living rival bosses within `radius` of `at`. */
export function rivalsNear(team, dim, at, radius) {
    const out = [];
    for (const [t, fams] of Object.entries(TEAMS)) {
        if (t === team)
            continue;
        for (const f of fams) {
            try {
                for (const e of dim.getEntities({ location: at, maxDistance: radius, families: [f] }))
                    if (alive(e))
                        out.push(e);
            }
            catch {
                // unloaded
            }
        }
    }
    return out;
}
