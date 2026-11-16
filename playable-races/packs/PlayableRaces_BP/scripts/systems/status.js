import { system } from "@minecraft/server";
import { particle } from "../core/fx.js";
import { v3 } from "../core/util.js";
const table = new Map();
const handles = new Map();
const MARKER = {
    misclassified: { id: "plrace:misclass_mark", every: 16, dy: 0.55 },
    sunmarked: { id: "plrace:sun_mark", every: 14, dy: 0.6 },
    observed: { id: "plrace:observed_mark", every: 12, dy: 0.75 },
    parallax: { id: "plrace:parallax_mark", every: 10, dy: 0.3 },
};
const idOf = (e) => (typeof e === "string" ? e : e.id);
export function setStatus(e, key, ticks, by) {
    if (!e.isValid)
        return;
    let m = table.get(e.id);
    if (!m)
        table.set(e.id, (m = new Map()));
    const now = system.currentTick;
    const cur = m.get(key);
    m.set(key, { until: Math.max(cur && cur.by === by ? cur.until : 0, now + ticks), by });
    handles.set(e.id, e);
}
export function hasStatus(e, key, by) {
    const st = table.get(idOf(e))?.get(key);
    return !!st && st.until > system.currentTick && (by === undefined || st.by === by);
}
export function statusBy(e, key) {
    const st = table.get(idOf(e))?.get(key);
    return st && st.until > system.currentTick ? st.by : undefined;
}
export function clearStatus(e, key) {
    table.get(idOf(e))?.delete(key);
}
export function withStatus(key, by) {
    const out = [];
    for (const [id, m] of table) {
        const st = m.get(key);
        const e = handles.get(id);
        if (st && st.by === by && st.until > system.currentTick && e?.isValid)
            out.push(e);
    }
    return out;
}
export function allWithStatus(key) {
    const out = [];
    for (const [id, m] of table) {
        const st = m.get(key);
        const e = handles.get(id);
        if (st && st.until > system.currentTick && e?.isValid)
            out.push(e);
    }
    return out;
}
export function clearStatusesBy(playerId) {
    for (const m of table.values())
        for (const [k, st] of m)
            if (st.by === playerId)
                m.delete(k);
}
export function tickStatuses() {
    const now = system.currentTick;
    for (const [id, m] of table) {
        const e = handles.get(id);
        if (!e || !e.isValid) {
            table.delete(id);
            handles.delete(id);
            continue;
        }
        for (const [k, st] of m) {
            if (st.until <= now) {
                m.delete(k);
                continue;
            }
            const mk = MARKER[k];
            if (Math.floor(now / 4) % Math.max(1, Math.round(mk.every / 4)) === 0) {
                try {
                    const h = e.getHeadLocation();
                    particle(e.dimension, mk.id, v3(h.x, h.y + mk.dy, h.z));
                }
                catch {
                }
            }
        }
        if (!m.size) {
            table.delete(id);
            handles.delete(id);
        }
    }
}
