import { system } from "@minecraft/server";
import { warn } from "./util.js";
let queue = [];
export function after(ticks, fn, owner, tag) {
    const t = { at: system.currentTick + Math.max(1, Math.floor(ticks)), fn, owner, tag, alive: true };
    queue.push(t);
    return t;
}
export function repeat(every, times, fn, owner, tag, delay = 0) {
    for (let i = 0; i < times; i++) {
        const k = i;
        after(Math.max(1, delay + every * i), () => fn(k), owner, tag);
    }
}
export function cancel(owner, tag) {
    let n = 0;
    for (const t of queue) {
        if (t.alive && t.owner === owner && (tag === undefined || t.tag === tag)) {
            t.alive = false;
            n++;
        }
    }
    return n;
}
export function pending(owner, tag) {
    return queue.some((t) => t.alive && t.owner === owner && (tag === undefined || t.tag === tag));
}
export function startScheduler() {
    system.runInterval(() => {
        if (queue.length === 0)
            return;
        const now = system.currentTick;
        const due = queue.filter((t) => t.alive && t.at <= now);
        if (due.length === 0) {
            if (queue.length > 64)
                queue = queue.filter((t) => t.alive);
            return;
        }
        queue = queue.filter((t) => t.alive && t.at > now);
        for (const t of due) {
            try {
                t.fn();
            }
            catch (e) {
                warn(`task ${t.tag ?? "?"} failed`, e);
            }
        }
    }, 1);
}
