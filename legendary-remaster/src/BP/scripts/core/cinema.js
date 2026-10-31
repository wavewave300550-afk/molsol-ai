// Ultimate cut-ins: for a moment the camera frames the legend from a low, front-side angle while
// it gathers its power, then eases back to the player's own eyes. Players are immune while their
// view is taken. Each player can switch cut-ins off with /legends:cinematic.
import { system } from "@minecraft/server";
import { effect } from "./combat.js";
import { dirOfYaw } from "./vec.js";
const OFF = "legends:no_cinematic";
const active = new Map(); // player id -> { p, until }
export function cinematicsOn(p) {
    try {
        return p.getDynamicProperty(OFF) !== true;
    }
    catch {
        return true;
    }
}
/** Flip the player's preference; returns the new state (applied next tick). */
export function toggleCinematics(p) {
    const on = !cinematicsOn(p);
    system.run(() => {
        try {
            p.setDynamicProperty(OFF, !on);
        }
        catch {
            // ignore
        }
    });
    return on;
}
function open(dim, at) {
    try {
        for (const dy of [0, 1]) {
            const b = dim.getBlock({ x: Math.floor(at.x), y: Math.floor(at.y) + dy, z: Math.floor(at.z) });
            if (!b || !b.isAir)
                return false;
        }
        return true;
    }
    catch {
        return false;
    }
}
/** Start a shot of `boss` for `players`, lasting about `ticks`. Returns the players who got it. */
export function cutIn(boss, players, ticks) {
    const g = boss.ground(boss.pos);
    const fwd = dirOfYaw(boss.yaw);
    const side = { x: -fwd.z, y: 0, z: fwd.x };
    const focus = boss.centre(boss.camFocus ?? 3.5);
    const far = boss.camDist ?? 12;
    let cam;
    for (const d of [far, far * 0.7, far * 0.5]) {
        const c = { x: g.x + fwd.x * d + side.x * d * 0.45, y: Math.max(g.y + 2.2 + d * 0.1, focus.y - 6), z: g.z + fwd.z * d + side.z * d * 0.45 };
        if (open(boss.dim, c)) {
            cam = c;
            break;
        }
    }
    if (!cam)
        return [];
    const shot = [];
    for (const p of players) {
        if (!p.isValid || !cinematicsOn(p))
            continue;
        try {
            p.camera.setCamera("minecraft:free", { location: cam, facingLocation: focus, easeOptions: { easeTime: 0.7, easeType: "InOutSine" } });
            effect(p, "resistance", ticks + 30, 4);
            active.set(p.id, { p, until: system.currentTick + ticks + 40 });
            shot.push(p);
        }
        catch {
            // camera control unavailable: the spectacle still plays
        }
    }
    return shot;
}
/** Ease each player's view back to their own eyes, then hand control back. */
export function cutOut(players, ease = 0.45) {
    for (const p of players) {
        try {
            const r = p.getRotation();
            p.camera.setCamera("minecraft:free", { location: p.getHeadLocation(), rotation: { x: r.x, y: r.y }, easeOptions: { easeTime: ease, easeType: "InOutSine" } });
        }
        catch {
            // ignore
        }
        const e = active.get(p.id);
        if (e)
            e.until = Math.min(e.until, system.currentTick + Math.ceil(ease * 20) + 1);
    }
}
/** Every tick: release any view whose shot is over (also covers a legend removed mid-shot). */
export function tickCinema() {
    if (!active.size)
        return;
    const now = system.currentTick;
    for (const [id, e] of active) {
        if (now < e.until && e.p.isValid)
            continue;
        try {
            e.p.camera.clear();
        }
        catch {
            // ignore
        }
        active.delete(id);
    }
}
