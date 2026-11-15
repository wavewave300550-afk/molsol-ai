import { system, world } from "@minecraft/server";
import { hurt } from "../core/combat.js";
import { particle, rgb, RGB } from "../core/fx.js";
import { add, v3 } from "../core/util.js";
const marks = new Map();
export function brand(e, by, ticks, blood) {
    marks.set(e.id, { by: by.id, until: system.currentTick + ticks, blood });
}
export function markedBy(e) {
    const id = typeof e === "string" ? e : e.id;
    const m = marks.get(id);
    return m && m.until > system.currentTick ? m.by : undefined;
}
export function consume(e) {
    marks.delete(e.id);
}
export function clearMarksBy(playerId) {
    for (const [k, m] of marks)
        if (m.by === playerId)
            marks.delete(k);
}
export function tickMarks() {
    if (marks.size === 0)
        return;
    const now = system.currentTick;
    for (const [id, m] of marks) {
        let e;
        try {
            e = world.getEntity(id);
        }
        catch {
            e = undefined;
        }
        if (!e || !e.isValid) {
            marks.delete(id);
            continue;
        }
        const head = add(e.location, v3(0, 2.2, 0));
        if (m.until <= now) {
            marks.delete(id);
            if (m.blood) {
                const owner = world.getPlayers().find((p) => p.id === m.by);
                particle(e.dimension, "plrace:crimson_slash", head, { spin: 0, scale: 0.8 });
                if (owner)
                    hurt(e, 4, owner);
            }
            continue;
        }
        particle(e.dimension, "plrace:moon_sigil", head, rgb(m.blood ? RGB.crimson : RGB.silver));
    }
}
