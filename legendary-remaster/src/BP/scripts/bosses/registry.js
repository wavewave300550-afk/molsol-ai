/**
 * Creates controllers for boss entities (on summon, or when an existing boss is
 * found after a world reload) and ticks every live Being.
 */
import { world } from "@minecraft/server";
import { clearProps } from "../core/hazards.js";
import { Alicorn } from "./alicorn.js";
import { beings } from "./being.js";
import { Boss } from "./boss.js";
import { Hanuman } from "./hanuman.js";
import { Logos } from "./logos.js";
import { Nidhogg } from "./nidhogg.js";
import { Taotie } from "./taotie.js";
import { Tenko } from "./tenko.js";
const FACTORY = {
    "legends:taotie": (e, a) => new Taotie(e).init(a),
    "legends:nidhogg": (e, a) => new Nidhogg(e).init(a),
    "legends:hanuman": (e, a) => new Hanuman(e).init(a),
    "legends:alicorn": (e, a) => new Alicorn(e).init(a),
    "legends:tenko": (e, a) => new Tenko(e).init(a),
    "legends:logos": (e, a) => new Logos(e).init(a),
};
export const BOSS_IDS = Object.keys(FACTORY);
export function controlBoss(e, adopted) {
    const f = FACTORY[e.typeId];
    if (!f)
        return undefined;
    const existing = beings.get(e.id);
    if (existing instanceof Boss)
        return existing;
    return f(e, adopted);
}
export function bossOf(id) {
    const b = beings.get(id);
    return b instanceof Boss ? b : undefined;
}
export function beingOf(id) {
    return beings.get(id);
}
export function activeBoss(key) {
    for (const b of beings.values())
        if (b instanceof Boss && b.key === key && b.valid)
            return b;
    return undefined;
}
export function tickBeings() {
    for (const b of [...beings.values()]) {
        try {
            b.tick();
        }
        catch (e) {
            console.warn(`[legends] ${b.entity.typeId} tick failed: ${e}`);
        }
    }
}
const DIMS = ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"];
/** Adopt bosses that exist in the world but have no controller (world reload), and clear orphan props. */
export function adoptOrphans() {
    for (const id of DIMS) {
        let dim;
        try {
            dim = world.getDimension(id);
        }
        catch {
            continue;
        }
        let found = [];
        try {
            found = dim.getEntities({ families: ["legends"] });
        }
        catch {
            continue;
        }
        for (const e of found) {
            if (beings.has(e.id))
                continue;
            if (FACTORY[e.typeId]) {
                controlBoss(e, true);
                continue;
            }
            const owner = e.getDynamicProperty("legends:owner");
            const ownerAlive = typeof owner === "string" && beings.has(owner);
            if (ownerAlive)
                continue;
            if (e.matches({ families: ["legends_choir"] }))
                continue; // re-bound by the Word when it is adopted
            try {
                e.remove();
            }
            catch {
                // gone
            }
        }
    }
}
export function clearAll() {
    let n = 0;
    for (const id of DIMS) {
        try {
            for (const e of world.getDimension(id).getEntities({ families: ["legends"] })) {
                e.remove();
                n++;
            }
        }
        catch {
            // ignore
        }
    }
    for (const b of [...beings.values()])
        b.dispose();
    clearProps();
    return n;
}
