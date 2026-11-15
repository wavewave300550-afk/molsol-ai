import { system } from "@minecraft/server";
import { GLOBAL_CAST_LOCK } from "../config.js";
import { raceByCode } from "../races/registry.js";
import { privateSound } from "./fx.js";
import { showForm } from "./forms.js";
import { save } from "./session.js";
import { secs, warn } from "./util.js";
export function raceOf(s) {
    return s.data.race ? raceByCode(s.data.race) : undefined;
}
export function selected(s, race) {
    const i = ((s.data.sel % race.abilities.length) + race.abilities.length) % race.abilities.length;
    return race.abilities[i];
}
function ctxOf(p, s, race, ability) {
    return { p, s, race, ability };
}
export function maxCharges(p, s, race, a) {
    return Math.max(1, a.maxCharges ? a.maxCharges(ctxOf(p, s, race, a)) : a.charges ?? 1);
}
function cdTicks(p, s, race, a) {
    return Math.max(10, Math.round(a.cooldown * 20 * race.cooldownMul(p, s)));
}
export function charges(p, s, race, a) {
    const max = maxCharges(p, s, race, a);
    const now = system.currentTick;
    if (max <= 1)
        return (s.readyAt.get(a.id) ?? 0) <= now ? 1 : 0;
    let have = s.data.res[`chg:${a.id}`] ?? max;
    let at = s.chargeAt.get(a.id);
    while (at !== undefined && at <= now && have < max) {
        have++;
        at = have < max ? at + cdTicks(p, s, race, a) : undefined;
    }
    if (have >= max) {
        have = max;
        at = undefined;
    }
    if (at === undefined)
        s.chargeAt.delete(a.id);
    else
        s.chargeAt.set(a.id, at);
    if (s.data.res[`chg:${a.id}`] !== have) {
        s.data.res[`chg:${a.id}`] = have;
        s.dirty = true;
    }
    return have;
}
export function remaining(p, s, race, a) {
    const now = system.currentTick;
    if (maxCharges(p, s, race, a) <= 1)
        return Math.max(0, (s.readyAt.get(a.id) ?? 0) - now);
    if (charges(p, s, race, a) > 0)
        return 0;
    return Math.max(0, (s.chargeAt.get(a.id) ?? now) - now);
}
function spend(p, s, race, a) {
    const now = system.currentTick;
    const max = maxCharges(p, s, race, a);
    if (max <= 1) {
        s.readyAt.set(a.id, now + cdTicks(p, s, race, a));
        return;
    }
    const have = charges(p, s, race, a);
    s.data.res[`chg:${a.id}`] = Math.max(0, have - 1);
    if (!s.chargeAt.has(a.id))
        s.chargeAt.set(a.id, now + cdTicks(p, s, race, a));
}
export function refund(s, ticks, except) {
    const now = system.currentTick;
    for (const [id, at] of s.readyAt)
        if (id !== except)
            s.readyAt.set(id, Math.max(now, at - ticks));
    for (const [id, at] of s.chargeAt)
        if (id !== except)
            s.chargeAt.set(id, Math.max(now, at - ticks));
    s.dirty = true;
}
export function resetCooldowns(s) {
    s.readyAt.clear();
    s.chargeAt.clear();
    for (const k of Object.keys(s.data.res))
        if (k.startsWith("chg:"))
            delete s.data.res[k];
    s.dirty = true;
}
export function message(s, text, ticks = 40) {
    s.hudMsg = { text, until: system.currentTick + ticks };
    s.hudUntil = Math.max(s.hudUntil, system.currentTick + ticks);
}
export function fail(p, s, reason) {
    message(s, `§c${reason}`);
    privateSound(p, "note.bass", 0.6, 0.6);
}
export function cycle(p, s, dir = 1) {
    const race = raceOf(s);
    if (!race)
        return;
    s.data.sel = (((s.data.sel + dir) % race.abilities.length) + race.abilities.length) % race.abilities.length;
    s.dirty = true;
    save(p, s);
    const a = selected(s, race);
    const r = remaining(p, s, race, a);
    message(s, `${race.color}» ${a.name}${r > 0 ? ` §7(${secs(r)})` : " §a(ready)"}`, 30);
    privateSound(p, "random.click", 0.5, 1.5 + 0.1 * s.data.sel);
}
export function cast(p, s) {
    const race = raceOf(s);
    if (!race) {
        fail(p, s, "Choose a lineage first (Lineage Codex)");
        return;
    }
    const a = selected(s, race);
    const now = system.currentTick;
    if (s.channel) {
        if (s.channel.ability === a.id) {
            endChannel(p, s, "cancel");
            return;
        }
        const mode = s.channel.mode ?? "block";
        if (mode === "interrupt")
            endChannel(p, s, "interrupt");
        else if (mode === "block") {
            fail(p, s, "Busy");
            return;
        }
    }
    if (now - s.lastCast < GLOBAL_CAST_LOCK)
        return;
    const r = remaining(p, s, race, a);
    if (r > 0) {
        fail(p, s, `${a.name} recovering: ${secs(r)}`);
        return;
    }
    const ctx = ctxOf(p, s, race, a);
    const reason = a.check ? a.check(ctx) : undefined;
    if (reason) {
        fail(p, s, reason);
        return;
    }
    let result;
    try {
        result = a.cast(ctx);
    }
    catch (e) {
        warn(`${a.id} cast failed`, e);
        result = "The ability faltered";
    }
    if (result !== true) {
        fail(p, s, result);
        return;
    }
    spend(p, s, race, a);
    s.lastCast = now;
    s.data.stats.casts = (s.data.stats.casts ?? 0) + 1;
    s.dirty = true;
    s.hudUntil = now + 60;
    save(p, s);
}
export function startChannel(p, s, ch) {
    if (s.channel)
        endChannel(p, s, "interrupt");
    s.channel = { ...ch, started: system.currentTick };
}
export function endChannel(p, s, reason) {
    const ch = s.channel;
    if (!ch)
        return;
    s.channel = undefined;
    try {
        ch.end(s, p, reason);
    }
    catch (e) {
        warn(`channel ${ch.ability} end failed`, e);
    }
}
export function tickChannel(p, s) {
    const ch = s.channel;
    if (!ch)
        return;
    const t = system.currentTick;
    if (t >= ch.until) {
        endChannel(p, s, "complete");
        return;
    }
    try {
        ch.tick?.(s, p, t - ch.started);
    }
    catch (e) {
        warn(`channel ${ch.ability} tick failed`, e);
        endChannel(p, s, "interrupt");
    }
}
export function tempForm(p, s, variant, ticks) {
    s.tempVariant = { variant, until: system.currentTick + ticks };
    refreshForm(p, s);
}
export function clearTempForm(p, s) {
    s.tempVariant = undefined;
    refreshForm(p, s);
}
export function refreshForm(p, s) {
    const race = raceOf(s);
    if (!race || s.data.veiled)
        return;
    let v = race.variant(p, s);
    if (s.tempVariant) {
        if (s.tempVariant.until > system.currentTick)
            v = s.tempVariant.variant;
        else
            s.tempVariant = undefined;
    }
    showForm(p, race, s, v);
}
