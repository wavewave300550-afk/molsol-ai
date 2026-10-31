/**
 * The only path from the bosses to on-screen text.
 *
 * Rules enforced here (screen clarity during fights, mobile-friendly):
 *   - text goes to the action bar (small, above the hotbar) - never a centred title;
 *   - one line, short (hard cap 34 visible characters);
 *   - one message at a time per player: a lower-priority message is dropped while
 *     a higher one is showing, and nothing is shown more often than every 2.5 s;
 *   - identical messages are never repeated within 20 s.
 * Bosses therefore only announce: awakening, phase change, ultimate, defeat, retreat.
 */
import { system } from "@minecraft/server";
export var Pri;
(function (Pri) {
    Pri[Pri["Info"] = 0] = "Info";
    Pri[Pri["Phase"] = 1] = "Phase";
    Pri[Pri["Ultimate"] = 2] = "Ultimate";
})(Pri || (Pri = {}));
const slots = new Map();
const MIN_GAP = 50; // ticks between any two messages
const SHOW = 50; // a message "owns" the bar for this long
const REPEAT = 400; // identical text is suppressed for 20 s
const HARD_GAP = 24; // even urgent lines wait this long after the previous one (queued, never stacked)
const PENDING_TTL = 60; // a queued line older than 3 s is dropped
export const MAX_CHARS = 34;
function visible(text) {
    return text.replace(/§./g, "");
}
export function clampText(text) {
    if (visible(text).length <= MAX_CHARS)
        return text;
    let out = "";
    let n = 0;
    for (let i = 0; i < text.length && n < MAX_CHARS - 1; i++) {
        out += text[i];
        if (text[i] === "§" && i + 1 < text.length) {
            out += text[++i];
            continue;
        }
        n++;
    }
    return out + "…";
}
function show(p, s, msg, pri, now) {
    try {
        p.onScreenDisplay.setActionBar(msg);
        s.until = now + SHOW;
        s.pri = pri;
        s.shownAt = now;
        s.recent.set(msg, now);
        return true;
    }
    catch {
        return false; // player left / UI unavailable
    }
}
/** Returns true if the message was shown (or queued) for at least one player. */
export function notify(players, text, pri = Pri.Info) {
    const now = system.currentTick;
    const msg = clampText(text);
    let shown = false;
    for (const p of players) {
        if (!p.isValid)
            continue;
        let s = slots.get(p.id);
        if (!s) {
            s = { until: -1000, pri: Pri.Info, shownAt: -1000, recent: new Map() };
            slots.set(p.id, s);
        }
        const last = s.recent.get(msg);
        if (last !== undefined && now - last < REPEAT)
            continue;
        const busy = now < s.until;
        if (busy && pri <= s.pri)
            continue;
        if (!busy && now - s.shownAt < MIN_GAP && pri < Pri.Ultimate)
            continue;
        if (now - s.shownAt < HARD_GAP) {
            // never stack two lines: queue the most important one
            if (!s.pending || pri >= s.pending.pri)
                s.pending = { msg, pri, at: now, player: p };
            shown = true;
            continue;
        }
        shown = show(p, s, msg, pri, now) || shown;
    }
    return shown;
}
/** Called every tick: shows queued lines once the hard gap has passed. */
export function flushNotices() {
    const now = system.currentTick;
    for (const s of slots.values()) {
        const q = s.pending;
        if (!q)
            continue;
        if (now - q.at > PENDING_TTL || !q.player.isValid) {
            s.pending = undefined;
            continue;
        }
        if (now - s.shownAt >= HARD_GAP) {
            s.pending = undefined;
            show(q.player, s, q.msg, q.pri, now);
        }
    }
}
export function forget(playerId) {
    slots.delete(playerId);
}
