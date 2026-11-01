import { EntityDamageCause, GameMode } from "@minecraft/server";
import { BALANCE } from "./balance.js";
import { ACTION_TICKS, DRAGON_FAMILY, IMPACT_TICK, face, isLiving, lock, now, safe, sec, setAction, setProp, unlock, } from "./dragon.js";
import { SND, jetParticle, particle, sound } from "./fx.js";
import { AIM_STEPS, FIRE_PITCH_OFFSET_AIR, FIRE_PITCH_OFFSET_GROUND, MOUTH_BITE, MOUTH_BITE_AIR, MOUTH_FIRE_AIR, MOUTH_FIRE_GROUND, } from "./offsets.js";
import { DEG, add, aimDir, angleDiff, bearing, clamp, dist, dot, hdist, len, localToWorld, mul, norm, pitchTo, sub, turnToward, v3, yawTo, } from "./vec.js";
const SCALE = BALANCE.entity.scale;
const EXCLUDE_TYPES = ["minecraft:item", "minecraft:xp_orb", "minecraft:arrow", "minecraft:snowball",
    "minecraft:ender_pearl", "minecraft:fireball", "minecraft:small_fireball", "minecraft:armor_stand",
    "minecraft:painting", "minecraft:leash_knot", "minecraft:boat", "minecraft:chest_boat", "minecraft:minecart"];
/** Living things the dragon may hurt (never other red dragons, never creative/spectator players). */
export function victims(s, center, radius) {
    const e = s.entity;
    const list = safe(() => e.dimension.getEntities({
        location: center, maxDistance: radius, excludeFamilies: [DRAGON_FAMILY], excludeTypes: EXCLUDE_TYPES,
    })) ?? [];
    return list.filter((t) => t.id !== e.id && isLiving(t) && !isProtectedPlayer(t));
}
export function isProtectedPlayer(t) {
    if (t.typeId !== "minecraft:player")
        return false;
    const gm = safe(() => t.getGameMode());
    return gm === GameMode.Creative || gm === GameMode.Spectator;
}
export function centerOf(t) {
    const h = t.typeId === "minecraft:player" ? 0.9 : 0.6;
    return add(t.location, v3(0, h, 0));
}
function hurt(s, t, amount, cause) {
    return safe(() => t.applyDamage(amount, { cause, damagingEntity: s.entity })) ?? false;
}
function knock(s, t, strength, lift) {
    const d = sub(t.location, s.entity.location);
    const h = Math.sqrt(d.x * d.x + d.z * d.z) || 1;
    safe(() => t.applyKnockback({ x: (d.x / h) * strength, z: (d.z / h) * strength }, lift));
}
export function ready(s, k) {
    return now() >= s.ready[k];
}
/** Clear line of sight between two points (no solid block in between). */
export function lineOfSight(s, from, to) {
    const d = sub(to, from);
    const l = len(d);
    if (l < 0.5)
        return true;
    const hit = safe(() => s.entity.dimension.getBlockFromRay(from, norm(d), {
        maxDistance: l, includeLiquidBlocks: false, includePassableBlocks: false,
    }));
    return !hit;
}
/** Distance to the first solid block along a ray (or maxD). */
export function rayClear(s, from, dir, maxD) {
    const hit = safe(() => s.entity.dimension.getBlockFromRay(from, dir, {
        maxDistance: maxD, includeLiquidBlocks: false, includePassableBlocks: false,
    }));
    if (!hit)
        return maxD;
    const p = add(hit.block.location, hit.faceLocation);
    return Math.min(maxD, dist(from, p));
}
// ------------------------------------------------------------------------------------------------ actions
/** Start an action (attack, roar, idle animation). The caller guarantees nothing else is running. */
export function startAction(s, kind, faceTarget) {
    lock(s);
    if (faceTarget) {
        face(s, yawTo(s.entity.location, faceTarget.location), 0);
    }
    const length = kind === "fire_charge" ? sec(BALANCE.fire.charge_time) : ACTION_TICKS[kind] ?? 40;
    s.run = { kind, tick: 0, length, impactDone: false };
    setAction(s, kind);
    if (kind === "roar")
        sound(s.entity.dimension, SND.roarLayer, s.entity.location, 1.0, 0.9);
    if (kind === "fire_charge") {
        s.run.fireYaw = s.yaw;
        s.run.firePitch = 0;
    }
}
/** Called once the run finished or must be aborted: clears the property and starts the global gap. */
export function endAction(s) {
    s.run = undefined;
    setAction(s, "none");
    setProp(s, "dod:aim", 0);
    s.gapUntil = now() + sec(BALANCE.global_attack_gap);
    unlock(s);
}
/** Advance the running action by one tick. */
export function tickAction(s) {
    const r = s.run;
    if (!r)
        return;
    r.tick++;
    const e = s.entity;
    // bite / claw / buffet keep turning toward the target until just before the hit lands
    // (the tail smash must not: it sweeps the arc behind the dragon)
    if (s.target && (r.kind === "bite" || r.kind === "claw" || r.kind === "buffet") && r.tick < IMPACT_TICK[r.kind] - 2) {
        if (isLiving(s.target))
            face(s, turnToward(s.yaw, yawTo(e.location, s.target.location), 6), 0);
    }
    switch (r.kind) {
        case "bite":
        case "claw":
        case "tail":
        case "buffet":
            if (!r.impactDone && r.tick >= IMPACT_TICK[r.kind]) {
                r.impactDone = true;
                impact(s, r.kind);
            }
            break;
        case "fire_charge":
            tickFireAim(s, r, true);
            if (r.tick >= r.length) {
                // charge -> release; the client goes straight from the charge pose to the breath pose
                s.run = { kind: "fire_breath", tick: 0, length: sec(BALANCE.fire.breath_time), impactDone: false,
                    fireYaw: r.fireYaw, firePitch: r.firePitch };
                setAction(s, "fire_breath");
                return;
            }
            break;
        case "fire_breath":
            tickFireAim(s, r, false);
            tickBreath(s, r);
            break;
        default:
            break;
    }
    if (s.run && s.run.tick >= s.run.length)
        endAction(s);
}
function impact(s, kind) {
    const e = s.entity;
    const pos = e.location;
    const yaw = s.yaw;
    const dim = e.dimension;
    let hits = 0;
    if (kind === "bite") {
        const B = BALANCE.bite;
        const m = s.inAir ? MOUTH_BITE_AIR : MOUTH_BITE;
        const p = localToWorld(pos, yaw, m.fwd * SCALE, (m.up + 0.6) * SCALE, m.left * SCALE);
        for (const t of victims(s, p, B.hit_radius + 1)) {
            if (dist(centerOf(t), p) <= B.hit_radius && hurt(s, t, B.damage, EntityDamageCause.entityAttack))
                hits++;
        }
        s.ready.bite = now() + sec(B.cooldown);
        if (hits)
            particle(dim, "dod:claw_slash", p);
    }
    else if (kind === "claw") {
        const C = BALANCE.claw;
        for (const t of victims(s, pos, C.max_range + 1)) {
            const c = centerOf(t);
            if (hdist(c, pos) <= C.max_range && bearing(pos, yaw, c) <= C.max_angle && Math.abs(c.y - pos.y) < 4.5) {
                if (hurt(s, t, C.damage, EntityDamageCause.entityAttack)) {
                    hits++;
                    knock(s, t, C.knockback, 0.35);
                }
            }
        }
        s.ready.claw = now() + sec(C.cooldown);
    }
    else if (kind === "tail") {
        const T = BALANCE.tail;
        for (const t of victims(s, pos, T.max_range + 1)) {
            const c = centerOf(t);
            if (hdist(c, pos) <= T.max_range && bearing(pos, yaw, c) >= T.min_angle && Math.abs(c.y - pos.y) < 4) {
                if (hurt(s, t, T.damage, EntityDamageCause.entityAttack)) {
                    hits++;
                    knock(s, t, T.knockback, 0.45);
                }
            }
        }
        s.ready.tail = now() + sec(T.cooldown);
    }
    else {
        const W = BALANCE.buffet;
        for (const t of victims(s, pos, W.max_range + 1)) {
            const c = centerOf(t);
            if (hdist(c, pos) <= W.max_range && bearing(pos, yaw, c) <= W.max_angle && Math.abs(c.y - pos.y) < 5) {
                hurt(s, t, W.damage, EntityDamageCause.entityAttack);
                knock(s, t, W.knockback, W.lift);
                hits++;
            }
        }
        s.ready.buffet = now() + sec(W.cooldown);
    }
    if (hits)
        sound(dim, SND.hit, pos, 1.0, kind === "bite" ? 1.1 : 0.85);
    s.lastHits = hits;
}
// ------------------------------------------------------------------------------------------------ fire breath
function interp(table, aim) {
    const a = clamp(aim, AIM_STEPS[0], AIM_STEPS[AIM_STEPS.length - 1]);
    const step = AIM_STEPS[1] - AIM_STEPS[0];
    const i = Math.min(AIM_STEPS.length - 2, Math.floor((a - AIM_STEPS[0]) / step));
    const f = (a - AIM_STEPS[i]) / step;
    const p = table[i];
    const q = table[i + 1];
    return { fwd: p.fwd + (q.fwd - p.fwd) * f, up: p.up + (q.up - p.up) * f, left: p.left + (q.left - p.left) * f };
}
/** Mouth world position while breathing fire with synced aim property `aimProp`. */
export function mouthWorld(s, yaw, aimProp) {
    const m = interp(s.inAir ? MOUTH_FIRE_AIR : MOUTH_FIRE_GROUND, aimProp);
    return localToWorld(s.entity.location, yaw, m.fwd * SCALE, m.up * SCALE, m.left * SCALE);
}
/** Turn toward the target and pick the pitch so the head (and the jet bound to it) points at it. */
function tickFireAim(s, r, charging) {
    const F = BALANCE.fire;
    const t = s.target;
    let yaw = r.fireYaw ?? s.yaw;
    let pitch = r.firePitch ?? 0;
    if (isLiving(t)) {
        const goalYaw = yawTo(s.entity.location, t.location);
        yaw = turnToward(yaw, goalYaw, charging ? 4 : F.turn_rate_deg_per_tick);
        const offset = s.inAir ? FIRE_PITCH_OFFSET_AIR : FIRE_PITCH_OFFSET_GROUND;
        const mouth = mouthWorld(s, yaw, Math.round(pitch - offset));
        const want = clamp(pitchTo(mouth, centerOf(t)), -40, 55);
        pitch = pitch + clamp(want - pitch, -3, 3);
    }
    r.fireYaw = yaw;
    r.firePitch = pitch;
    face(s, yaw, pitch);
    const offset = s.inAir ? FIRE_PITCH_OFFSET_AIR : FIRE_PITCH_OFFSET_GROUND;
    setProp(s, "dod:aim", clamp(Math.round(pitch - offset), -60, 60));
}
function tickBreath(s, r) {
    const F = BALANCE.fire;
    const e = s.entity;
    const dim = e.dimension;
    const yaw = r.fireYaw ?? s.yaw;
    const pitch = r.firePitch ?? 0;
    const aimProp = Number(s.props["dod:aim"] ?? 0);
    const origin = mouthWorld(s, yaw, aimProp);
    const dir = aimDir(yaw, pitch);
    const reach = F.reach * SCALE;
    const clear = rayClear(s, origin, dir, reach);
    // the visible jet geometry is 12 blocks long; shorten it at walls so it never shows through them
    setProp(s, "dod:jet", clamp(Math.round(clear), 1, 12));
    // flame particles along the jet (world space, direction = aim) every other tick
    if (r.tick % 2 === 0) {
        for (const d of [3.5, 6.5, 9.5, 12.5, 15]) {
            if (d > clear - 0.5)
                break;
            jetParticle(dim, add(origin, mul(dir, d)), dir, 7 + d * 0.3);
        }
        if (clear < reach) {
            const p = add(origin, mul(dir, clear - 0.3));
            particle(dim, "dod:fire_impact", p);
            if (r.tick % 6 === 0) {
                particle(dim, "dod:smoke", p);
                particle(dim, "dod:embers", p);
            }
        }
    }
    if (r.tick % 8 === 0)
        sound(dim, SND.fireLoop, origin, 1.0, 0.8 + Math.random() * 0.2);
    // damage: everything inside the cone, up to the first wall, with line of sight to the mouth
    const every = Math.max(1, sec(F.tick_interval));
    if (r.tick % every !== 0)
        return;
    const tanA = Math.tan(F.cone_half_angle * DEG);
    for (const t of victims(s, add(origin, mul(dir, reach / 2)), reach / 2 + 3)) {
        const c = centerOf(t);
        const v = sub(c, origin);
        const along = dot(v, dir);
        if (along < 0 || along > Math.min(reach, clear + 0.8))
            continue;
        const perp = len(sub(v, mul(dir, along)));
        if (perp > 0.9 + along * tanA)
            continue;
        if (!lineOfSight(s, origin, c))
            continue;
        if (hurt(s, t, F.damage_per_tick, EntityDamageCause.fire)) {
            safe(() => t.setOnFire(F.burn_seconds, true));
            if (r.tick % (every * 2) === 0)
                particle(dim, "dod:fire_impact", c);
            sound(dim, SND.fireHit, c, 0.6, 1.0);
            s.fireHits = (s.fireHits ?? 0) + 1;
        }
    }
}
export function startFire(s) {
    startAction(s, "fire_charge");
    s.ready.fire = now() + sec(BALANCE.fire.cooldown + BALANCE.fire.charge_time + BALANCE.fire.breath_time);
    if (s.inAir)
        s.airFires++;
}
/** Choose the attack that fits where the target is. Returns undefined when nothing fits yet. */
export function chooseAttack(s, t, hostilesNear) {
    const pos = s.entity.location;
    const c = centerOf(t);
    const d = hdist(pos, c);
    const dy = c.y - pos.y;
    const b = bearing(pos, s.yaw, c);
    const options = [];
    if (s.inAir) {
        const m = MOUTH_BITE_AIR;
        const mouth = localToWorld(pos, s.yaw, m.fwd, m.up, m.left);
        if (ready(s, "bite") && dist(mouth, c) < BALANCE.bite.hit_radius + 2 && b < 40)
            options.push(["bite", 5]);
        if (ready(s, "fire") && d >= 6 && d <= BALANCE.fire.max_range + 4 && b <= 60 &&
            lineOfSight(s, mouthWorld(s, s.yaw, 20), c))
            options.push(["fire", 6]);
    }
    else {
        const B = BALANCE;
        if (ready(s, "claw") && d <= B.claw.max_range && b <= B.claw.max_angle && Math.abs(dy) < 4)
            options.push(["claw", 3]);
        if (ready(s, "bite") && d >= B.bite.min_range && d <= B.bite.max_range && b <= B.bite.max_angle && Math.abs(dy) < 4) {
            options.push(["bite", 4]);
        }
        if (ready(s, "tail") && d <= B.tail.max_range && b >= B.tail.min_angle && Math.abs(dy) < 4)
            options.push(["tail", 5]);
        if (ready(s, "buffet") && d <= B.buffet.max_range && b <= B.buffet.max_angle) {
            options.push(["buffet", hostilesNear >= 2 ? 7 : 1]);
        }
        if (ready(s, "fire") && d >= B.fire.min_range && d <= B.fire.max_range && b <= 50 &&
            lineOfSight(s, mouthWorld(s, s.yaw, 0), c))
            options.push(["fire", d > 10 ? 6 : 2]);
    }
    if (!options.length)
        return undefined;
    let sum = 0;
    for (const [, w] of options)
        sum += w;
    let roll = Math.random() * sum;
    for (const [k, w] of options) {
        roll -= w;
        if (roll <= 0)
            return k;
    }
    return options[options.length - 1][0];
}
export function startAttack(s, k) {
    if (k === "fire")
        startFire(s);
    else
        startAction(s, k, k === "tail" ? undefined : s.target);
}
export { angleDiff };
