import { Player, system, world } from "@minecraft/server";
import { effect, knockFrom } from "../core/combat.js";
import { particle } from "../core/fx.js";
import { alive, enemiesNear } from "../core/targets.js";
import { add, hdist, v3 } from "../core/util.js";
export const MAX_MARKS = 3;
const MARK_TICKS = 240;
const COURT_JUDGE_EVERY = 60;
const courts = [];
const judgments = new Map();
export function declareCourt(owner, kind, center, radius, ticks, end) {
    endCourt(owner.id, kind, "replaced");
    const now = system.currentTick;
    const c = { owner: owner.id, kind, dim: owner.dimension.id, center: { ...center }, radius, born: now, until: now + ticks,
        exiled: new Map(), judged: new Map(), end };
    courts.push(c);
    return c;
}
export function courtOf(ownerId, kind) {
    return courts.find((c) => c.owner === ownerId && (kind === undefined || c.kind === kind));
}
export function endCourt(ownerId, kind, reason) {
    for (let i = courts.length - 1; i >= 0; i--) {
        const c = courts[i];
        if (c.owner !== ownerId || (kind !== undefined && c.kind !== kind))
            continue;
        courts.splice(i, 1);
        try {
            c.end?.(c, reason);
        }
        catch {
        }
    }
}
function inside(c, dimId, loc, pad = 0) {
    return c.dim === dimId && hdist(loc, c.center) <= c.radius + pad && Math.abs(loc.y - c.center.y) <= 6;
}
export function inOwnCourt(p, kind) {
    return courts.some((c) => c.owner === p.id && (kind === undefined || c.kind === kind) && inside(c, p.dimension.id, p.location, 0.5));
}
export function inCourtOf(ownerId, e) {
    return courts.find((c) => c.owner === ownerId && inside(c, e.dimension.id, e.location));
}
export function exile(c, e, ticks) {
    c.exiled.set(e.id, system.currentTick + ticks);
}
export function courtSecondsLeft(c) {
    return Math.max(0, (c.until - system.currentTick) / 20);
}
export function judge(e, by, n = 1) {
    const id = typeof by === "string" ? by : by.id;
    let m = judgments.get(e.id);
    if (!m) {
        m = new Map();
        judgments.set(e.id, m);
    }
    const now = system.currentTick;
    const j = m.get(id);
    const have = j && j.until > now ? j.stacks : 0;
    const stacks = Math.min(MAX_MARKS, have + n);
    m.set(id, { stacks, until: now + MARK_TICKS });
    try {
        particle(e.dimension, "plrace:judgment_seal", add(e.location, v3(0, headroom(e), 0)), { stacks });
    }
    catch {
    }
    return stacks;
}
export function marksOn(e, by) {
    const j = judgments.get(typeof e === "string" ? e : e.id)?.get(by);
    return j && j.until > system.currentTick ? j.stacks : 0;
}
export function consumeMarks(e, by) {
    const m = judgments.get(e.id);
    const n = marksOn(e, by);
    if (m) {
        m.delete(by);
        if (m.size === 0)
            judgments.delete(e.id);
    }
    return n;
}
export function judgedBy(by) {
    const out = [];
    const now = system.currentTick;
    for (const [id, m] of judgments) {
        const j = m.get(by);
        if (!j || j.until <= now)
            continue;
        let e;
        try {
            e = world.getEntity(id);
        }
        catch {
            e = undefined;
        }
        if (alive(e))
            out.push(e);
    }
    return out;
}
export function clearJudgmentsBy(by) {
    for (const [id, m] of judgments) {
        m.delete(by);
        if (m.size === 0)
            judgments.delete(id);
    }
}
export function releaseJurisdiction(ownerId) {
    endCourt(ownerId, undefined, "owner");
    clearJudgmentsBy(ownerId);
}
function headroom(e) {
    return e.typeId === "minecraft:player" ? 2.3 : 2.1;
}
let beat = 0;
export function tickJurisdiction() {
    beat++;
    const now = system.currentTick;
    if (courts.length)
        tickCourts(now);
    if (judgments.size && beat % 2 === 0)
        tickMarks(now);
}
function tickCourts(now) {
    for (const c of [...courts]) {
        let owner;
        try {
            owner = world.getEntity(c.owner);
        }
        catch {
            owner = undefined;
        }
        if (!owner || !owner.isValid || !(owner instanceof Player) || owner.dimension.id !== c.dim) {
            endCourt(c.owner, c.kind, "owner");
            continue;
        }
        if (c.until <= now) {
            endCourt(c.owner, c.kind, "expired");
            continue;
        }
        if (c.kind === "temple" && !inside(c, owner.dimension.id, owner.location, 1.5)) {
            endCourt(c.owner, c.kind, "broken");
            continue;
        }
        const dim = owner.dimension;
        const age = now - c.born;
        if (Math.floor(age / 8) !== Math.floor((age - 4) / 8)) {
            for (let k = 0; k < 8; k++) {
                const a = ((k * 45 + age * 0.9) * Math.PI) / 180;
                particle(dim, "plrace:court_pillar", add(c.center, v3(Math.cos(a) * c.radius, 0.1, Math.sin(a) * c.radius)));
            }
        }
        if (Math.floor(age / 20) !== Math.floor((age - 4) / 20))
            particle(dim, "plrace:court_ring", add(c.center, v3(0, 0.08, 0)), { size: c.radius * 2 });
        for (const e of enemiesNear(owner, c.center, c.radius + 2.5)) {
            const ex = c.exiled.get(e.id);
            const inNow = inside(c, dim.id, e.location);
            if (ex !== undefined && ex > now) {
                if (inside(c, dim.id, e.location, 0.8))
                    knockFrom(e, c.center, 0.9, 0.15);
                continue;
            }
            if (!inNow)
                continue;
            effect(e, "slowness", 30, 0, false);
            const last = c.judged.get(e.id);
            if (last === undefined)
                c.judged.set(e.id, now - COURT_JUDGE_EVERY + 20);
            else if (now - last >= COURT_JUDGE_EVERY) {
                c.judged.set(e.id, now);
                judge(e, c.owner, 1);
            }
        }
    }
}
function tickMarks(now) {
    for (const [id, m] of judgments) {
        for (const [by, j] of m)
            if (j.until <= now)
                m.delete(by);
        if (m.size === 0) {
            judgments.delete(id);
            continue;
        }
        let e;
        try {
            e = world.getEntity(id);
        }
        catch {
            e = undefined;
        }
        if (!alive(e)) {
            judgments.delete(id);
            continue;
        }
        let stacks = 0;
        for (const j of m.values())
            stacks = Math.max(stacks, j.stacks);
        particle(e.dimension, "plrace:judgment_seal", add(e.location, v3(0, headroom(e), 0)), { stacks });
    }
}
