import { MoonPhase, world } from "@minecraft/server";
import { FOG_BLOOD_MOON, FOG_USER, WORLD_BLOODMOON } from "../config.js";
import { isOverworld, timeOfDay } from "../core/env.js";
import { settings } from "../core/settings.js";
import { safeJson, warn } from "../core/util.js";
let st;
const listeners = [];
function state() {
    if (!st) {
        let raw;
        try {
            raw = world.getDynamicProperty(WORLD_BLOODMOON);
        }
        catch {
            raw = undefined;
        }
        st = { phase: "idle", day: -1, missed: 0, force: false, checkedDay: -1, manual: false, sawNight: false, ...safeJson(raw, {}) };
    }
    return st;
}
function persist() {
    try {
        world.setDynamicProperty(WORLD_BLOODMOON, JSON.stringify(state()));
    }
    catch (e) {
        warn("blood moon save failed", e);
    }
}
export function onBloodMoonChange(fn) {
    listeners.push(fn);
}
export function bloodMoonActive() {
    return state().phase === "active";
}
export function bloodMoonStatus() {
    const s = state();
    let phase = "idle";
    try {
        phase = MoonPhase[world.getMoonPhase()] ?? "?";
    }
    catch {
    }
    return `Blood Moon: ${s.phase}${s.manual ? " (manual)" : ""}; moon phase ${phase}; full moons since last: ${s.missed}; forced next: ${s.force}; chance ${settings().bloodChance}%`;
}
const isNight = (t) => t >= 12542 && t < 23460;
export function bloodMoonTick() {
    const s = state();
    const t = timeOfDay();
    let day = 0;
    try {
        day = world.getDay();
    }
    catch {
        day = 0;
    }
    if (s.phase === "active") {
        if (s.manual) {
            if (isNight(t))
                s.sawNight = true;
            if (s.sawNight && !isNight(t))
                end("dawn");
            return;
        }
        if (!isNight(t) || day !== s.day)
            end("dawn");
        return;
    }
    if (s.phase === "omen") {
        if (day !== s.day) {
            s.phase = "idle";
            persist();
        }
        else if (t >= 13000 && isNight(t))
            start(false);
        return;
    }
    if (t >= 12000 && t < 23000 && s.checkedDay !== day) {
        s.checkedDay = day;
        let phase = MoonPhase.NewMoon;
        try {
            phase = world.getMoonPhase();
        }
        catch {
        }
        if (phase === MoonPhase.FullMoon) {
            const roll = s.force || s.missed >= 3 || Math.random() * 100 < settings().bloodChance;
            if (roll) {
                s.phase = "omen";
                s.day = day;
                announce("§4The full moon is rising... red.", "§cSomething stirs in the lunar blood");
                if (t >= 13000)
                    start(false);
            }
            else
                s.missed++;
        }
        persist();
    }
}
export function start(manual) {
    const s = state();
    s.phase = "active";
    s.manual = manual;
    s.sawNight = isNight(timeOfDay());
    try {
        s.day = world.getDay();
    }
    catch {
        s.day = 0;
    }
    s.missed = 0;
    s.force = false;
    persist();
    announce("§4§lTHE BLOOD MOON RISES", "§cJackalopes awaken until dawn");
    for (const p of world.getPlayers())
        applyFog(p);
    for (const fn of listeners)
        fn(true);
}
export function end(reason) {
    const s = state();
    if (s.phase === "idle")
        return;
    const wasActive = s.phase === "active";
    s.phase = "idle";
    s.manual = false;
    persist();
    for (const p of world.getPlayers())
        removeFog(p);
    if (wasActive) {
        announce("§7The Blood Moon wanes", reason === "dawn" ? "§8dawn breaks" : "§8the sky clears");
        for (const fn of listeners)
            fn(false);
    }
}
export function forceNext() {
    state().force = true;
    persist();
}
function announce(title, sub) {
    for (const p of world.getPlayers()) {
        if (!isOverworld(p))
            continue;
        try {
            p.onScreenDisplay.setTitle(title, { subtitle: sub, fadeInDuration: 20, stayDuration: 60, fadeOutDuration: 30 });
            p.playSound("ambient.weather.thunder", { volume: 0.5, pitch: 0.5 });
        }
        catch {
        }
    }
}
export function applyFog(p) {
    removeFog(p);
    if (!bloodMoonActive() || !settings().bloodFog || !isOverworld(p))
        return;
    try {
        p.runCommand(`fog @s push ${FOG_BLOOD_MOON} ${FOG_USER}`);
    }
    catch {
    }
}
export function removeFog(p) {
    try {
        p.runCommand(`fog @s remove ${FOG_USER}`);
    }
    catch {
    }
}
