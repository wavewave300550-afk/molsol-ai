/**
 * Visual / audio effects.
 *
 * Every particle effect in the resource pack is parameterised by Molang
 * variables (size, lifetime, colour, count, speed...) so one definition
 * serves every boss. Telegraphs follow one colour language across all six
 * fights: RED = damage will land here, GOLD = safe zone. They are flat decals
 * on the ground: an outline plus a fill that grows until the moment of impact,
 * so players read *where* and *when* without any text.
 */
import { MolangVariableMap } from "@minecraft/server";
import { add, dirOfYaw, rotY, scale, v, yawOf } from "./vec.js";
export const C = {
    danger: { red: 1.0, green: 0.28, blue: 0.14 },
    warn: { red: 1.0, green: 0.62, blue: 0.12 },
    safe: { red: 1.0, green: 0.86, blue: 0.32 },
    white: { red: 1.0, green: 1.0, blue: 1.0 },
    holy: { red: 1.0, green: 0.94, blue: 0.68 },
    gold: { red: 1.0, green: 0.78, blue: 0.25 },
    bronze: { red: 0.53, green: 0.83, blue: 0.66 },
    ember: { red: 1.0, green: 0.45, blue: 0.12 },
    hunger: { red: 0.32, green: 0.2, blue: 0.38 },
    venom: { red: 0.45, green: 1.0, blue: 0.32 },
    frost: { red: 0.62, green: 0.9, blue: 1.0 },
    root: { red: 0.42, green: 0.3, blue: 0.18 },
    fire: { red: 1.0, green: 0.52, blue: 0.1 },
    wind: { red: 0.78, green: 1.0, blue: 0.93 },
    star: { red: 1.0, green: 0.96, blue: 0.75 },
    moon: { red: 0.85, green: 0.9, blue: 1.0 },
    aurora: { red: 0.78, green: 0.62, blue: 1.0 },
    pink: { red: 1.0, green: 0.72, blue: 0.92 },
    sky: { red: 0.55, green: 0.85, blue: 1.0 },
    fox: { red: 0.25, green: 0.66, blue: 1.0 },
    crimson: { red: 0.85, green: 0.07, blue: 0.18 },
    beryl: { red: 0.36, green: 0.86, blue: 0.72 },
    dark: { red: 0.08, green: 0.06, blue: 0.1 },
};
function vars(col, extra) {
    const m = new MolangVariableMap();
    m.setColorRGB("variable.color", col);
    for (const k in extra)
        m.setFloat(`variable.${k}`, extra[k]);
    return m;
}
export function spawn(dim, id, at, map) {
    try {
        dim.spawnParticle(id, at, map);
    }
    catch {
        // unloaded chunk / outside the world: cosmetic only
    }
}
const lift = (p, h = 0.06) => ({ x: p.x, y: p.y + h, z: p.z });
// ------------------------------------------------------------------ telegraphs
/** Circular danger (or safe) zone: pulsing outline + fill that grows until impact. */
export function teleCircle(dim, center, radius, ticks, col = C.danger) {
    const life = Math.max(0.1, ticks / 20);
    spawn(dim, "legends:tele_ring", lift(center), vars(col, { size: radius, life }));
    spawn(dim, "legends:tele_fill", lift(center, 0.05), vars(col, { size: radius, life }));
    if (radius >= 2.5)
        spawn(dim, "legends:circle", lift(center, 0.07), vars(col, { size: radius, life }));
}
export const teleSafe = (dim, center, radius, ticks) => teleCircle(dim, center, radius, ticks, C.safe);
/** Rectangular strip (line attacks) drawn as a dotted floor marking. */
export function teleLine(dim, from, dir, length, width, ticks, col = C.danger) {
    const life = Math.max(0.1, ticks / 20);
    const yaw = yawOf(dir);
    const fwd = dirOfYaw(yaw);
    const side = dirOfYaw(yaw + 90);
    const cols = Math.max(1, Math.round(width / 1.3));
    const step = 1.3;
    for (let d = 0.8; d <= length; d += step) {
        for (let c = 0; c < cols; c++) {
            const off = cols === 1 ? 0 : (c / (cols - 1) - 0.5) * (width - 0.6);
            const p = add(add(from, scale(fwd, d)), scale(side, off));
            spawn(dim, "legends:tele_dot", lift(p), vars(col, { size: 0.42, life }));
        }
    }
}
/** Cone telegraph (apex at the attacker) drawn as dotted arcs. */
export function teleCone(dim, apex, dir, angle, range, ticks, col = C.danger) {
    const life = Math.max(0.1, ticks / 20);
    for (let r = 1.6; r <= range; r += 1.5) {
        const n = Math.max(2, Math.round(((angle * Math.PI) / 180) * r / 1.4));
        for (let i = 0; i <= n; i++) {
            const a = -angle / 2 + (angle * i) / n;
            const p = add(apex, scale(rotY(dir, a), r));
            spawn(dim, "legends:tele_dot", lift(p), vars(col, { size: r >= range - 1.5 ? 0.55 : 0.4, life }));
        }
    }
}
/** Donut (ring) telegraph between two radii: danger outside the inner circle. */
export function teleRing(dim, center, inner, outer, ticks, col = C.danger) {
    const life = Math.max(0.1, ticks / 20);
    spawn(dim, "legends:tele_ring", lift(center), vars(col, { size: outer, life }));
    spawn(dim, "legends:tele_ring", lift(center), vars(C.safe, { size: inner, life }));
    for (let r = inner + 1; r < outer; r += 1.6) {
        const n = Math.round((Math.PI * 2 * r) / 1.8);
        for (let i = 0; i < n; i++) {
            const a = (i / n) * 360;
            spawn(dim, "legends:tele_dot", lift(add(center, scale(dirOfYaw(a), r))), vars(col, { size: 0.38, life }));
        }
    }
}
// ------------------------------------------------------------------ impact & ambience
// Effects are sized for god-sized bosses: every scripted particle is scaled up so it reads at
// distance and on small (mobile) screens.
const FX_SIZE = 1.7;
const FX_COUNT = 1.5;
const n = (c) => Math.min(60, Math.round(c * FX_COUNT));
/** Ground impact: double shock ring, a flash of the magic circle, sparks, dust, debris and light. */
export function shock(dim, center, radius, ticks, col) {
    const life = Math.max(0.1, ticks / 20);
    spawn(dim, "legends:shock", lift(center, 0.12), vars(col, { size: radius, life }));
    if (radius >= 4)
        spawn(dim, "legends:shock", lift(center, 0.14), vars(C.white, { size: radius * 0.62, life: life * 0.7 }));
    if (radius >= 5) {
        spawn(dim, "legends:fx_dust", lift(center, 0.3));
        spawn(dim, "legends:spark", lift(center, 0.4), vars(col, { count: Math.min(40, Math.round(radius * 2.5)), speed: 4 + radius * 0.6, size: 0.45, radius: 0 }));
    }
    if (radius >= 6)
        crack(dim, center, Math.min(10, radius * 0.6), col, 50);
    if (radius >= 8) {
        spawn(dim, "legends:fx_debris", lift(center, 0.5));
        spawn(dim, "legends:circle", lift(center, 0.1), vars(col, { size: radius * 1.1, life: 0.7 }));
        spawn(dim, "legends:orb", lift(center, 1.0), vars(col, { size: Math.min(9, radius * 0.6), life: 0.35 }));
    }
    if (radius >= 12)
        spawn(dim, "legends:fx_flash", lift(center, 1.2));
}
export function pillar(dim, base, height, width, ticks, col) {
    spawn(dim, "legends:pillar", base, vars(col, { size: width * 1.3, height, life: Math.max(0.1, ticks / 20) }));
    spawn(dim, "legends:burst", lift(base, 0.3), vars(col, { count: 10, speed: 3, size: 0.5, radius: width * 0.6 }));
    spawn(dim, "legends:orb", lift(base, 0.6), vars(col, { size: width * 2.4, life: Math.min(1.2, Math.max(0.2, ticks / 20)) }));
}
export function burst(dim, at, col, count = 16, speed = 4, size = 0.22, radius = 0.25) {
    spawn(dim, "legends:burst", at, vars(col, { count: n(count), speed: speed * 1.2, size: size * FX_SIZE, radius }));
    if (count >= 16)
        spawn(dim, "legends:spark", at, vars(col, { count: Math.min(30, count), speed: speed * 1.6, size: 0.35, radius: 0 }));
    if (count >= 24)
        spawn(dim, "legends:glint", at, vars(col, { count: 1, speed: 0, size: 2.4 + radius, radius: 0 }));
}
// ------------------------------------------------------------------ spectacle (ultimates, phases, deaths)
/** A rotating rune circle on the ground. */
export function magicCircle(dim, at, radius, ticks, col) {
    spawn(dim, "legends:circle", lift(at, 0.09), vars(col, { size: radius, life: Math.max(0.2, ticks / 20) }));
}
/** A growing orb of light. */
export function orb(dim, at, col, size, ticks) {
    spawn(dim, "legends:orb", at, vars(col, { size, life: Math.max(0.1, ticks / 20) }));
}
/** Energy streaming in from a sphere of `radius` into `at` over `ticks`, with a swelling core. */
export function chargeUp(dim, at, col, ticks, radius = 4) {
    const life = Math.max(0.3, ticks / 20);
    spawn(dim, "legends:converge", at, vars(col, { count: 48, radius, speed: radius / (life * 0.6), size: 0.45, life }));
    spawn(dim, "legends:orb", at, vars(col, { size: Math.min(3.2, Math.max(1.2, radius * 0.45)), life: life + 0.1 }));
}
/** A detonation of light: core flash, sparks, burst and a double ring. */
export function nova(dim, at, col, radius = 6) {
    spawn(dim, "legends:orb", at, vars(col, { size: radius * 1.1, life: 0.4 }));
    spawn(dim, "legends:orb", at, vars(C.white, { size: radius * 0.6, life: 0.25 }));
    spawn(dim, "legends:burst", at, vars(col, { count: 50, speed: radius * 1.6, size: 0.8, radius: 0.5 }));
    spawn(dim, "legends:spark", at, vars(col, { count: 40, speed: radius * 2.2, size: 0.5, radius: 0 }));
    spawn(dim, "legends:shock", lift(at, -0.5), vars(col, { size: radius * 1.6, life: 0.7 }));
    rays(dim, at, col, radius * 1.4, 18);
    flare(dim, at, C.white, radius * 1.3, 10);
    dome(dim, at, col, radius * 1.5, 14);
}
// ------------------------------------------------------------------ spectacle II (second atlas)
const SIGIL_UV = { taotie: [0, 0], nidhogg: [32, 0], hanuman: [64, 0], alicorn: [96, 0], tenko: [0, 32], logos: [32, 32] };
/** The legend's own rune circle, flat on the ground, unfolding and turning. */
export function sigil(dim, at, key, radius, ticks, col, spin = 24) {
    const uv = SIGIL_UV[key] ?? SIGIL_UV.logos;
    spawn(dim, "legends:sigil", lift(at, 0.08), vars(col, { size: radius, life: Math.max(0.3, ticks / 20), spin, u: uv[0], v: uv[1] }));
}
/** Glowing fissures torn into the ground. */
export function crack(dim, at, radius, col, ticks = 50) {
    spawn(dim, "legends:crack", lift(at, 0.05), vars(col, { size: radius, life: Math.max(0.3, ticks / 20) }));
}
/** Radiant god-rays. */
export function rays(dim, at, col, size, ticks = 16, spin = 30) {
    spawn(dim, "legends:rays", at, vars(col, { size, life: Math.max(0.2, ticks / 20), spin }));
}
/** Horizontal lens flare. */
export function flare(dim, at, col, size, ticks = 10) {
    spawn(dim, "legends:flare", at, vars(col, { size, life: Math.max(0.1, ticks / 20) }));
}
/** An expanding shell of force. */
export function dome(dim, at, col, radius, ticks = 14) {
    spawn(dim, "legends:dome", at, vars(col, { size: radius, life: Math.max(0.2, ticks / 20) }));
}
/** A lightning strike from the sky onto `ground` (cosmetic; damage is up to the caller). */
export function lightning(dim, ground, col, height = 22) {
    for (const o of [0, 1]) {
        const at = { x: ground.x + (o ? 0.7 : 0), y: ground.y + height / 2, z: ground.z + (o ? -0.5 : 0) };
        spawn(dim, "legends:bolt", at, vars(col, { height: o ? height * 0.9 : height, life: o ? 0.22 : 0.32 }));
    }
    spawn(dim, "legends:bolt", { x: ground.x, y: ground.y + height / 2, z: ground.z }, vars(C.white, { height: height * 0.95, life: 0.12 }));
    spawn(dim, "legends:orb", lift(ground, 0.6), vars(col, { size: 2.6, life: 0.3 }));
    spawn(dim, "legends:spark", lift(ground, 0.4), vars(col, { count: 22, speed: 9, size: 0.45, radius: 0 }));
    spawn(dim, "legends:shock", lift(ground, 0.12), vars(col, { size: 3.2, life: 0.4 }));
    crack(dim, ground, 2.8, col, 30);
    flare(dim, lift(ground, 1.0), C.white, 4, 6);
}
/** Rings of light rising up a column. */
export function ascend(dim, at, col, radius, height = 10, ticks = 30, count = 8) {
    const life = Math.max(0.3, ticks / 20);
    spawn(dim, "legends:ascend", lift(at, 0.2), vars(col, { size: radius, height, speed: height / 1.2, life, count: count * life }));
}
/** A spiralling funnel of wind. */
export function vortex(dim, at, col, radius, height = 10, ticks = 40, count = 30, spin = 360) {
    spawn(dim, "legends:vortex", at, vars(col, { radius, height, speed: height / 1.4, life: Math.max(0.3, ticks / 20), count, spin, size: 0.9 + radius * 0.12 }));
}
/** Stars / meteors raining onto a disc around `center` (on the ground) for `ticks`. */
export function starRain(dim, center, col, radius, ticks, count = 20, height = 24, speed = 30) {
    spawn(dim, "legends:rain", { x: center.x, y: center.y + height, z: center.z }, vars(col, { radius, height, speed, life: Math.max(0.3, ticks / 20), count, size: 1.6 }));
}
/** A storm of blossom petals. */
export function petals(dim, at, col, radius = 2, ticks = 40, count = 30, speed = 5) {
    spawn(dim, "legends:petals", at, vars(col, { radius, speed, life: Math.max(0.3, ticks / 20), count, size: 0.45 }));
}
export function mote(dim, at, col, size = 0.18, life = 0.6) {
    spawn(dim, "legends:mote", at, vars(col, { count: 1, speed: 0.1, size: size * FX_SIZE, radius: 0, life }));
}
export function glint(dim, at, col, size = 1.2) {
    spawn(dim, "legends:glint", at, vars(col, { count: 1, speed: 0, size: size * 1.4, radius: 0 }));
}
export function deco(dim, kind, at, col, count = 6, radius = 1, size = 0.3, speed = 1) {
    spawn(dim, `legends:${kind}`, at, vars(col, { count: n(count), radius, size: size * FX_SIZE, speed }));
}
export function spiralMark(dim, at, col, size, ticks) {
    spawn(dim, "legends:spiral", lift(at, 0.1), vars(col, { size, life: Math.max(0.1, ticks / 20) }));
}
/** A client-simulated bullet: one particle flying in a straight line (server checks hits analytically). */
export function bullet(dim, from, dir, speed, ticks, col, size = 0.35) {
    const m = vars(col, { size: size * 1.4, life: ticks / 20 });
    m.setSpeedAndDirection("variable.dir", speed, dir);
    spawn(dim, "legends:bullet", from, m);
}
/** Beam drawn as a stream of fast bullets (cheap: a few particles per call). */
export function beam(dim, from, to, col, size = 0.45) {
    const d = { x: to.x - from.x, y: to.y - from.y, z: to.z - from.z };
    const l = Math.hypot(d.x, d.y, d.z);
    if (l < 0.1)
        return;
    const dir = scale(d, 1 / l);
    const speed = 60;
    const ticks = Math.max(1, Math.round((l / speed) * 20));
    for (let k = 0; k < 3; k++)
        bullet(dim, add(from, scale(dir, (k * l) / 3)), dir, speed, Math.max(1, Math.round(ticks * (1 - k / 3))), col, size);
}
export function ring(dim, center, radius, col, n) {
    const count = n ?? Math.max(8, Math.round(radius * 3));
    for (let i = 0; i < count; i++)
        mote(dim, add(center, scale(dirOfYaw((i / count) * 360), radius)), col, 0.22, 0.5);
}
// ------------------------------------------------------------------ sound & camera
export function sound(dim, id, at, volume = 1, pitch = 1) {
    try {
        dim.playSound(id, at, { volume, pitch });
    }
    catch {
        // ignore
    }
}
export function shake(players, intensity = 0.3, seconds = 0.5) {
    const i = Math.max(0.05, Math.min(1, intensity)).toFixed(2);
    const s = Math.max(0.1, seconds).toFixed(2);
    for (const p of players) {
        try {
            p.runCommand(`camerashake add @s ${i} ${s} positional`);
        }
        catch {
            // camera shake unavailable: purely cosmetic
        }
    }
}
/** Very short full-screen flash used only at the climax of an ultimate (never held). */
export function flash(players, col = C.white) {
    for (const p of players) {
        try {
            p.camera.fade({ fadeColor: col, fadeTime: { fadeInTime: 0.08, holdTime: 0.0, fadeOutTime: 0.45 } });
        }
        catch {
            // ignore
        }
    }
}
export const up = (p, h) => v(p.x, p.y + h, p.z);
