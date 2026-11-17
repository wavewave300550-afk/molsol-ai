// Frontier Cleave (basic attack) and the four special skills.
import { system } from "@minecraft/server";
import { awaken, restore } from "./awaken.js";
import { addBleed, bodyCenter, enemiesNear, hurt, push, spawnFx } from "./combat.js";
import { ANIM, OATH_GRIZZLY_ID, SHADE_ID, SKILLS, TUNING } from "./config.js";
import { BLACK, BLACK_FLAME, DEEP_RED, HOT, RED, WHITE_HOT, blood, emit, clawFlash, crack, dust, ember, flame, glow, ring, shard, slash, smoke, sound, sparks, star, streak } from "./fx.js";
import { now, state } from "./state.js";
import { add, cross, dist, distToSegment, flat, lerp, mul, norm, rightOf, rotY, up, v } from "./vec.js";
export function playAnim(p, name, blendOut = 0.15) {
    try {
        p.playAnimation(name, { blendOutTime: blendOut });
    }
    catch {
        // animation unavailable: gameplay still works
    }
}
function later(ticks, fn) {
    system.runTimeout(() => {
        try {
            fn();
        }
        catch (e) {
            console.warn(`[Grizzly's Oath] ${e}`);
        }
    }, ticks);
}
/** Free distance along a ray before the first solid block (skills never pass through walls). */
function clearDistance(dim, from, dir, max) {
    try {
        const hit = dim.getBlockFromRay(from, dir, { maxDistance: max, includeLiquidBlocks: false, includePassableBlocks: false });
        if (!hit)
            return max;
        return Math.max(0, dist(from, add(hit.block.location, hit.faceLocation)) - 0.3);
    }
    catch {
        return max;
    }
}
function shake(p, intensity, seconds, radius) {
    try {
        p.runCommand(`camerashake add @a[r=${radius}] ${intensity} ${seconds} positional`);
    }
    catch {
        // commands unavailable: purely cosmetic
    }
}
function heal(p, amount) {
    try {
        const h = p.getComponent("minecraft:health");
        if (h)
            h.setCurrentValue(Math.min(h.effectiveMax, h.currentValue + amount));
    }
    catch {
        // ignore
    }
}
export function healthRatio(p) {
    try {
        const h = p.getComponent("minecraft:health");
        if (h && h.effectiveMax > 0)
            return Math.max(0, Math.min(1, h.currentValue / h.effectiveMax));
    }
    catch {
        // ignore
    }
    return 1;
}
// ============================================================ basic attack: Frontier Cleave
function emitAfterglow(dim, at, rot) {
    // faint, wider dark-red smear behind the slash (anime motion blur)
    emit(dim, "slash", at, (m) => {
        m.setFloat("variable.size", 0.85);
        m.setFloat("variable.rot", rot - 8);
        m.setFloat("variable.life", 0.26);
        m.setColorRGBA("variable.color", { red: 0.55, green: 0.02, blue: 0.04, alpha: 0.55 });
    });
}
/** Heavy alternating slash with a red arc in the aimed direction (every attack swing). */
export function frontierCleave(p) {
    const st = state(p);
    st.parity ^= 1;
    const fromRight = st.parity === 1;
    playAnim(p, fromRight ? ANIM.cleaveRight : ANIM.cleaveLeft, 0.1);
    const dim = p.dimension;
    const eye = p.getHeadLocation();
    const d = p.getViewDirection();
    const r = rightOf(d);
    const u = norm(cross(r, d)); // screen-space up
    // Kept 2.6 blocks out and below the crosshair so the first-person view stays clear.
    const c = add(add(eye, mul(d, 2.6)), mul(u, -0.35));
    const arcAt = add(c, mul(r, fromRight ? 0.2 : -0.2));
    slash(dim, arcAt, 0.6, fromRight ? 35 : 145, RED, 0.2);
    emitAfterglow(dim, arcAt, fromRight ? 35 : 145);
    // energy wisps following the blade path: upper-right -> lower-left, or the mirror
    let prev = c;
    for (let k = 0; k <= 6; k++) {
        const t = k / 6;
        const x = fromRight ? 1 - 2 * t : -1 + 2 * t;
        const y = 0.55 - 1.1 * t;
        const pos = add(add(add(c, mul(r, x * 0.85)), mul(u, y * 0.6)), mul(d, Math.sin(Math.PI * t) * 0.3));
        if (k > 0)
            streak(dim, pos, norm(add(pos, mul(prev, -1))), 0.32, 0.05, k % 2 ? HOT : RED, 0.18);
        prev = pos;
    }
    sound(dim, "grizzly_oath.cleave_swing", eye, 0.6, 1);
}
/** Impact of a Frontier Cleave that connected. */
export function cleaveImpact(p, target) {
    const dim = target.dimension;
    const at = bodyCenter(target);
    star(dim, at, 0.4, HOT);
    sparks(dim, at, 10, 1);
    slash(dim, at, 0.42, Math.random() * 360, RED, 0.16);
    blood(dim, at);
    sound(dim, "grizzly_oath.cleave_hit", at, 0.9, 0.95 + Math.random() * 0.15);
    sound(dim, "game.player.attack.strong", at, 0.8, 0.8);
}
// ============================================================ skill 1: Grizzly Rend
function grizzlyRend(p) {
    const T = TUNING.rend;
    const dim = p.dimension;
    const view = p.getViewDirection();
    const dir = norm(v(view.x, Math.max(-0.45, Math.min(0.45, view.y)), view.z));
    const right = rightOf(view);
    const origin = up(p.location, 0.9);
    const ground = -0.7; // claw marks are drawn low, near the ground, so they never fill the screen
    playAnim(p, ANIM.rend);
    sound(dim, "grizzly_oath.rend", origin, 1, 1);
    sound(dim, "grizzly_oath.growl", origin, 0.9, 1);
    const eye = p.getHeadLocation();
    const screenUp = norm(cross(right, view));
    const flashAt = add(add(eye, mul(view, 3.2)), mul(screenUp, -0.45));
    clawFlash(dim, flashAt, 0.6, 0, RED);
    clawFlash(dim, flashAt, 0.45, 0, WHITE_HOT);
    const lines = [-1, 0, 1].map((i) => {
        const ldir = rotY(dir, i * T.fanDegrees);
        const start = add(add(origin, mul(right, i * T.lateral)), mul(ldir, 1.2));
        return { start, dir: ldir, max: clearDistance(dim, start, ldir, T.range) };
    });
    const hit = new Set();
    const steps = Math.ceil(T.range / T.blocksPerTick);
    for (let t = 0; t < steps; t++) {
        later(t + 1, () => {
            if (!p.isValid)
                return;
            for (const L of lines) {
                const a = t * T.blocksPerTick;
                const b = Math.min((t + 1) * T.blocksPerTick, L.max);
                if (a >= L.max)
                    continue;
                const head = add(L.start, mul(L.dir, b));
                const low = (q) => up(q, ground);
                // glowing claw scar left on the ground behind the racing claw head
                for (let s = a + 0.5; s < b; s += 1.0) {
                    const at = low(add(L.start, mul(L.dir, s)));
                    streak(dim, at, L.dir, 1.0, 0.3, DEEP_RED, 0.9); // dark-red under-glow of the scar
                    streak(dim, up(at, 0.02), L.dir, 0.95, 0.12, RED, 0.8); // the glowing gash
                }
                streak(dim, up(head, ground + 0.3), L.dir, 1.9, 0.5, RED, 0.2); // the racing claw
                streak(dim, up(head, ground + 0.3), L.dir, 1.6, 0.2, WHITE_HOT, 0.16);
                glow(dim, up(head, ground + 0.3), 0.45, 0.2, RED);
                if (t % 2 === 0)
                    sparks(dim, up(head, ground + 0.2), 3, 0.6);
                if (t % 2 === 1)
                    smoke(dim, low(head), 0.35, BLACK);
                const segA = add(L.start, mul(L.dir, a));
                for (const e of enemiesNear(p, lerp(segA, head, 0.5), (b - a) / 2 + 2)) {
                    if (hit.has(e.id))
                        continue;
                    const c = bodyCenter(e);
                    if (distToSegment(c, segA, head) > T.hitRadius)
                        continue;
                    hit.add(e.id);
                    hurt(p, e, T.damage);
                    addBleed(p, e);
                    push(e, p.location, 0.35, 0.15);
                    clawFlash(dim, c, 0.45, Math.random() * 360, RED);
                    star(dim, c, 0.3, HOT);
                    sparks(dim, c, 8, 1);
                    blood(dim, c);
                }
            }
        });
    }
}
// ============================================================ skill 2: Relentless Pursuit
function relentlessPursuit(p) {
    const T = TUNING.pursuit;
    const dim = p.dimension;
    const fwd = flat(p.getViewDirection());
    const right = rightOf(fwd);
    const start = p.location;
    const free = Math.min(clearDistance(dim, up(start, 0.3), fwd, T.distance + 0.6), clearDistance(dim, up(start, 1.5), fwd, T.distance + 0.6));
    const distance = Math.max(0, Math.min(T.distance, free - 0.4));
    playAnim(p, ANIM.pursuit);
    sound(dim, "grizzly_oath.dash", start, 1, 1);
    for (const side of [-1, 1])
        dust(dim, up(add(start, mul(right, side * 0.4)), 0.05), norm(add(mul(fwd, -1), mul(right, side * 0.6))), 3, 0.45);
    flame(dim, up(start, 0.05), 0.5, DEEP_RED);
    let prev = start;
    for (let i = 1; i <= T.dashTicks; i++) {
        later(i, () => {
            if (!p.isValid)
                return;
            const pos = add(start, mul(fwd, (distance * i) / T.dashTicks));
            try {
                p.teleport(pos, { keepVelocity: false });
            }
            catch {
                // ignore
            }
            // afterimage trail stays behind the player and low, so the camera never flies through it
            const tail = add(pos, mul(fwd, -0.9));
            const mid = lerp(prev, tail, 0.5);
            streak(dim, up(mid, 0.6), fwd, 2.2, 0.7, DEEP_RED, 0.4); // body afterimage
            streak(dim, up(mid, 0.6), fwd, 2.0, 0.24, RED, 0.3);
            streak(dim, up(add(mid, mul(right, 0.4)), 1.1), fwd, 1.8, 0.3, BLACK, 0.35);
            streak(dim, up(add(mid, mul(right, -0.4)), 0.25), fwd, 1.6, 0.16, HOT, 0.25);
            glow(dim, up(mid, 0.6), 0.35, 0.25, RED);
            flame(dim, up(mid, 0.05), 0.35, i % 2 ? BLACK_FLAME : DEEP_RED);
            dust(dim, up(tail, 0.05), mul(fwd, -1), 2.5, 0.35);
            prev = tail;
        });
    }
    later(T.dashTicks + T.slamDelay, () => {
        if (!p.isValid)
            return;
        try {
            p.clearVelocity();
        }
        catch {
            // ignore
        }
        const here = p.location;
        const c = add(here, mul(fwd, 1.4));
        for (const e of enemiesNear(p, c, T.slamRadius)) {
            hurt(p, e, T.damage);
            sparks(dim, bodyCenter(e), 8, 1);
            star(dim, bodyCenter(e), 0.28, HOT);
        }
        for (const e of enemiesNear(p, here, T.waveRadius))
            push(e, here, T.knockback, T.lift);
        const impact = add(here, mul(fwd, 2.2));
        crack(dim, up(impact, 0.06), 2.3, DEEP_RED, 1.3);
        ring(dim, up(impact, 0.12), T.waveRadius, 0.4, RED);
        later(2, () => ring(dim, up(impact, 0.1), T.waveRadius * 0.65, 0.3, HOT));
        for (let k = 0; k < 10; k++)
            dust(dim, up(impact, 0.1), rotY(fwd, k * 36), 4, 0.55);
        shard(dim, up(impact, 0.2), 10);
        star(dim, up(impact, 0.35), 0.9, HOT, 0.18);
        sparks(dim, up(impact, 0.3), 14, 1.2);
        slash(dim, up(impact, 0.55), 0.8, 90, RED, 0.22);
        later(3, () => {
            for (let k = 0; k < 6; k++)
                ember(dim, up(add(impact, v(Math.random() - 0.5, 0, Math.random() - 0.5)), 0.2));
        });
        sound(dim, "grizzly_oath.heavy_slam", c, 1, 1);
        sound(dim, "grizzly_oath.shockwave", c, 0.45, 1.1);
        shake(p, 0.35, 0.35, 12);
    });
}
// ============================================================ skill 3: Unbroken Will
function unbrokenWill(p, st) {
    const T = TUNING.will;
    const dim = p.dimension;
    const t = now();
    const fwd = flat(p.getViewDirection());
    const yaw = p.getRotation().y;
    playAnim(p, ANIM.will);
    sound(dim, "grizzly_oath.roar", p.location, 1, 1);
    sound(dim, "grizzly_oath.heartbeat", p.location, 1, 1);
    spawnFx(p, SHADE_ID, add(p.location, mul(fwd, -2.3)), yaw, T.shadeTicks);
    ring(dim, up(p.location, 0.1), 2.6, 0.45, DEEP_RED);
    crack(dim, up(p.location, 0.05), 1.7, DEEP_RED, 1.4);
    for (let i = 0; i < 10; i++) {
        const a = (i / 10) * Math.PI * 2;
        const at = add(p.location, v(Math.cos(a) * 1.1, 0.05, Math.sin(a) * 1.1));
        flame(dim, at, 0.45, i % 2 ? BLACK_FLAME : DEEP_RED);
        ember(dim, at);
    }
    // roar shockwave
    later(6, () => {
        if (p.isValid)
            ring(dim, up(p.location, 0.15), 3.8, 0.5, { red: 1, green: 0.1, blue: 0.07, alpha: 0.6 });
    });
    // Instant mending scales with how close to death the survivor is.
    heal(p, 2 + Math.round(6 * (1 - healthRatio(p))));
    st.willUntil = t + T.durationTicks;
    st.nextPulse = t;
}
export function willTier(ratio) {
    return ratio > 0.6 ? 1 : ratio > 0.3 ? 2 : 3;
}
/** Runs every tick for players with Unbroken Will active. */
export function tickWill(p, st, t) {
    if (st.willUntil <= t) {
        st.willTier = 0;
        return;
    }
    const dim = p.dimension;
    if (t % 2 === 0) {
        // aura hugs the body from the feet to the waist (never in front of the eyes)
        const a = Math.random() * Math.PI * 2;
        const at = add(p.location, v(Math.cos(a) * 0.8, 0.05 + Math.random() * 0.3, Math.sin(a) * 0.8));
        ember(dim, up(at, Math.random() * 0.5));
        if (t % 4 === 0)
            flame(dim, at, 0.28, (t / 4) % 2 ? BLACK_FLAME : DEEP_RED);
    }
    if (t >= st.nextPulse) {
        st.nextPulse = t + TUNING.will.pulseTicks;
        const tier = willTier(healthRatio(p));
        st.willTier = tier;
        const duration = Math.max(1, Math.min(30, st.willUntil - t));
        try {
            p.addEffect("resistance", duration, { amplifier: tier - 1, showParticles: false });
        }
        catch {
            // ignore
        }
        heal(p, tier);
        ring(dim, up(p.location, 0.1), 1.1 + tier * 0.25, 0.3, tier === 3 ? RED : DEEP_RED);
        if (tier >= 2)
            sound(dim, "grizzly_oath.heartbeat", p.location, 0.5 + tier * 0.15, 1);
    }
}
// ============================================================ skill 4: Oath of the Grizzly
function oathOfTheGrizzly(p, st) {
    const T = TUNING.oath;
    const dim = p.dimension;
    const t0 = now();
    const fwd = flat(p.getViewDirection());
    const right = rightOf(fwd);
    const yaw = p.getRotation().y;
    st.ultUntil = t0 + T.awakenTicks;
    awaken(p);
    playAnim(p, ANIM.ult, 0.2);
    sound(dim, "grizzly_oath.charge", p.location, 1, 1);
    ring(dim, up(p.location, 0.1), 1.8, 0.6, RED);
    crack(dim, up(p.location, 0.05), 1.6, DEEP_RED, 2.2);
    // charge-up: a spiral of crimson flames and embers climbs around the survivor, the raised axe
    // burns brighter (overhead, outside the first-person view) until the slam
    for (let k = 0; k < T.slamTick; k += 2) {
        later(k, () => {
            if (!p.isValid)
                return;
            const ang = k * 0.55;
            const h = Math.min(1.3, k * 0.035);
            const at = add(p.location, v(Math.cos(ang) * 1.15, h, Math.sin(ang) * 1.15));
            if (k % 4 === 0)
                flame(dim, at, 0.35, (k / 4) % 2 ? BLACK_FLAME : DEEP_RED);
            ember(dim, at);
            const axe = add(add(up(p.getHeadLocation(), 1.0), mul(right, 0.55)), mul(fwd, 0.3));
            if (k % 4 === 0)
                glow(dim, axe, 0.18 + k * 0.006, 0.25, RED, 0.5);
        });
    }
    let bearPos = add(p.location, mul(fwd, -6.0));
    later(T.spawnDelay, () => {
        if (!p.isValid)
            return;
        bearPos = add(p.location, mul(fwd, -6.0));
        spawnFx(p, OATH_GRIZZLY_ID, bearPos, yaw, T.grizzlyTicks);
        crack(dim, up(bearPos, 0.05), 3.2, DEEP_RED, 2.6);
        ring(dim, up(bearPos, 0.1), 3.6, 0.55, DEEP_RED);
        for (let i = 0; i < 10; i++) {
            const a = (i / 10) * Math.PI * 2;
            const at = add(bearPos, v(Math.cos(a) * 1.8, 0.05, Math.sin(a) * 1.8));
            flame(dim, at, 0.9, i % 2 ? BLACK_FLAME : DEEP_RED);
            if (i % 2 === 0)
                smoke(dim, up(at, 0.3), 1.0, BLACK);
        }
        shard(dim, up(bearPos, 0.2), 10);
        sound(dim, "grizzly_oath.shockwave", bearPos, 0.4, 0.5);
    });
    later(T.roarTick, () => {
        if (!p.isValid)
            return;
        sound(dim, "grizzly_oath.titan_roar", bearPos, 1, 1);
        sound(dim, "grizzly_oath.roar", bearPos, 1, 0.8);
        sound(dim, "grizzly_oath.thunder", bearPos, 0.6, 1);
        ring(dim, up(bearPos, 0.15), 6, 0.6, { red: 1, green: 0.1, blue: 0.07, alpha: 0.55 });
        for (let k = 0; k < 8; k++)
            dust(dim, up(bearPos, 0.1), rotY(fwd, k * 45), 3.5, 0.7);
        shake(p, 0.25, 0.9, 20);
    });
    later(T.slamTick, () => {
        if (!p.isValid)
            return;
        const center = add(p.location, mul(fwd, 1.2));
        for (const e of enemiesNear(p, center, T.radius)) {
            const d = Math.min(1, dist(e.location, center) / T.radius);
            hurt(p, e, Math.round(T.maxDamage - (T.maxDamage - T.minDamage) * d));
            push(e, center, T.knockback * (1 - d * 0.75) + 0.6, T.lift);
            try {
                e.addEffect("slowness", 40, { amplifier: 1 });
            }
            catch {
                // ignore
            }
            sparks(dim, bodyCenter(e), 8, 1);
            star(dim, bodyCenter(e), 0.28, HOT);
        }
        const ground = up(center, 0.12);
        crack(dim, up(center, 0.05), 6.5, DEEP_RED, 2.2);
        // where the grizzly's paws land, behind the survivor
        const paws = up(add(bearPos, mul(fwd, 2.3)), 0.05);
        crack(dim, paws, 3.2, DEEP_RED, 1.8);
        for (let k = 0; k < 6; k++)
            dust(dim, paws, rotY(fwd, k * 60), 4.5, 0.8);
        shard(dim, up(paws, 0.2), 10);
        ring(dim, ground, T.radius, 0.55, RED);
        later(2, () => ring(dim, ground, T.radius * 0.6, 0.4, HOT));
        later(4, () => ring(dim, up(center, 0.1), T.radius + 0.5, 0.75, DEEP_RED));
        for (let k = 0; k < 12; k++) {
            const dir = rotY(fwd, k * 30);
            streak(dim, add(ground, mul(dir, 1.8)), dir, 2.4, 0.22, k % 2 ? HOT : RED, 0.4);
            streak(dim, add(ground, mul(dir, 4.6)), dir, 2.0, 0.16, RED, 0.5);
            if (k % 3 === 0)
                dust(dim, add(ground, mul(dir, 1.5)), dir, 6, 0.9);
        }
        for (let k = 0; k < 6; k++)
            shard(dim, up(add(center, mul(rotY(fwd, k * 60 + 30), 2.4)), 0.2), 8);
        const flashAt = add(p.location, mul(fwd, 2.6));
        star(dim, up(flashAt, 0.4), 1.4, WHITE_HOT, 0.2);
        sparks(dim, up(flashAt, 0.3), 20, 1.5);
        for (let k = 0; k < 4; k++) {
            later(3 + k * 3, () => {
                for (let i = 0; i < 4; i++) {
                    const a = Math.random() * Math.PI * 2;
                    const at = add(center, v(Math.cos(a) * (2 + Math.random() * 4), 0.05, Math.sin(a) * (2 + Math.random() * 4)));
                    ember(dim, at);
                    if (i === 0)
                        flame(dim, at, 0.5, DEEP_RED);
                }
            });
        }
        sound(dim, "grizzly_oath.shockwave", center, 1, 1);
        sound(dim, "grizzly_oath.heavy_slam", center, 1, 0.8);
        shake(p, 0.8, 0.6, 24);
    });
    later(T.awakenTicks, () => {
        if (p.isValid)
            restore(p);
    });
}
// ============================================================ casting
export function castSelected(p) {
    const st = state(p);
    const t = now();
    if (t < st.busyUntil)
        return;
    const def = SKILLS[st.skill];
    const left = st.readyAt[st.skill] - t;
    if (left > 0) {
        flash(st, `${def.color}${def.name} §7recharging §f${(left / 20).toFixed(1)}s`, 25);
        sound(p.dimension, "grizzly_oath.not_ready", p.location, 0.6, 1);
        return;
    }
    st.readyAt[st.skill] = t + def.cooldownTicks;
    st.busyUntil = t + def.busyTicks;
    switch (def.id) {
        case "rend":
            grizzlyRend(p);
            break;
        case "pursuit":
            relentlessPursuit(p);
            break;
        case "will":
            unbrokenWill(p, st);
            break;
        case "oath":
            oathOfTheGrizzly(p, st);
            break;
    }
}
export function flash(st, text, ticks) {
    st.flashText = text;
    st.flashUntil = now() + ticks;
}
