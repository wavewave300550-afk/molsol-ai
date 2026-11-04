/**
 * Boss 2: Thomas Edison (esb:edison) - the assassin of the Current War.
 *
 * Vanilla AI chases and does the quick broken-bulb shank (minecraft:behavior.delayed_attack); this module adds
 * the intro on his Dynamo, the bulb toss, Blackout (vanish + backstab), Overload (chain lightning from the
 * Dynamo), the Electric Chair, the stun when the Dynamo is destroyed, phase 2 ("Current War", AC blue) and the
 * death sequence.
 */
import { EntityDamageCause } from "@minecraft/server";
import { BALANCE } from "./balance.js";
import { actionBar, at, centerOf, clearUlt, event, groundBelow, health, hpFrac, isLiving, isProtectedPlayer, knockFrom, lock, message, newUlt, now, playersNear, rayClear, safe, sec, setAction, setProp, shake, title, turnTo, unlock, victims, } from "./boss.js";
import { PFX, SND, particle, sound } from "./fx.js";
import { CHAIR_SEAT, DYNAMO_TOP, E_BULB_REST, E_BULB_THROW, E_CHEST, E_HEAD } from "./offsets.js";
import { ARC_BOLT_ID, CHAIR_ID, DYNAMO_ID, EDISON_ACTIONS, MARKER_ID, SUN_BULB_ID, VOLT_BULB_ID } from "./spec.js";
import { DEG, add, dist, hdist, lerp, mul, norm, sub, v3, yawDir, yawTo } from "./vec.js";
const E = BALANCE.edison;
const ticksOf = (k) => sec(EDISON_ACTIONS[k].length);
const moment = (k, m) => sec(EDISON_ACTIONS[k].moments[m]);
const COOLDOWN = {
    bulb_toss: E.bulb_toss.cooldown, vanish: E.vanish.cooldown, overload: E.overload.cooldown, chair: E.chair.cooldown,
};
const DECIDE_EVERY = 8;
/** Electric FX use amber (DC) in phase 1 and blue-white (AC) in phase 2. */
function zap(s, id, p) {
    particle(s.entity.dimension, id, p, undefined, s.phase === 2 ? 1 : 0);
}
// ------------------------------------------------------------------------------------------ action plumbing
export function startE(s, kind) {
    lock(s);
    s.run = { kind, tick: 0, length: ticksOf(kind), fired: new Set() };
    setAction(s, kind);
    if (kind === "transform" || kind === "intro" || kind === "ultimate")
        s.invulnerable = true;
}
function fire(s, name) {
    const run = s.run;
    if (!run || run.fired.has(name))
        return false;
    if (run.tick < moment(run.kind, name))
        return false;
    run.fired.add(name);
    return true;
}
export function endE(s, ability) {
    const kind = s.run?.kind;
    s.run = undefined;
    if (kind === "intro" || kind === "transform" || kind === "ultimate")
        s.invulnerable = false;
    if (kind === "ultimate") {
        clearUlt(s);
        s.ready.ultimate = now() + sec(E.ultimate.cooldown);
    }
    if (kind === "flourish")
        s.nextFlourish = now() + sec(lerp(E.flourish.every_min, E.flourish.every_max, Math.random()));
    if (s.hidden)
        reveal(s);
    setAction(s, "none");
    if (s.dynamo?.isValid)
        safe(() => s.dynamo.setProperty("esb:mode", "idle"));
    s.gapUntil = now() + sec(E.global_gap);
    if (ability)
        s.ready[ability] = now() + sec(COOLDOWN[ability] * (s.phase === 2 ? 0.8 : 1));
    unlock(s);
}
function targetPoint(s) {
    return isLiving(s.target) ? centerOf(s.target) : undefined;
}
function hurtBy(s, t, amount) {
    return safe(() => t.applyDamage(amount, { cause: EntityDamageCause.entityAttack, damagingEntity: s.entity })) ?? false;
}
function airAt(s, p, height) {
    for (let dy = 0; dy < height; dy++) {
        const b = safe(() => s.entity.dimension.getBlock(v3(p.x, p.y + dy + 0.1, p.z)));
        if (!b || !b.isAir)
            return false;
    }
    return true;
}
// ------------------------------------------------------------------------------------------ the Dynamo
export function dynamoAlive(s) {
    return !!s.dynamo && s.dynamo.isValid && isLiving(s.dynamo);
}
function spawnDynamo(s, p, yaw) {
    const d = safe(() => s.entity.dimension.spawnEntity(DYNAMO_ID, p));
    if (!d)
        return undefined;
    safe(() => d.setRotation({ x: 0, y: yaw }));
    safe(() => d.setProperty("esb:phase", s.phase));
    s.dynamo = d;
    return d;
}
/** The Dynamo was destroyed: Edison is unplugged (stunned, takes extra damage). */
export function onDynamoDestroyed(s) {
    const dim = s.entity.dimension;
    const p = s.dynamo?.location;
    s.dynamo = undefined;
    if (p) {
        particle(dim, PFX.voltSpark, add(p, v3(0, 1.2, 0)), undefined, s.phase === 2 ? 1 : 0);
        particle(dim, PFX.smoke, add(p, v3(0, 1, 0)));
        sound(dim, SND.boom, p, 1, 1.3);
    }
    if (s.dying || s.run?.kind === "intro" || s.run?.kind === "transform" || s.run?.kind === "ultimate")
        return;
    if (s.hidden)
        reveal(s);
    if (s.inAir) {
        event(s, "esb:to_ground");
        s.inAir = false;
    }
    s.hop = undefined;
    s.run = undefined;
    s.blinksLeft = 0;
    s.stunUntil = now() + sec(E.dynamo.stun_seconds);
    message(playersNear(s, 48), "esb.msg.unplugged");
    startE(s, "stunned");
}
// ------------------------------------------------------------------------------------------ intro (sits on the Dynamo)
export function startIntroE(s) {
    const pos = { ...s.entity.location };
    spawnDynamo(s, pos, s.yaw);
    startE(s, "intro");
    event(s, "esb:to_air");
    s.inAir = true;
    s.locked = true;
    safe(() => s.entity.teleport(add(pos, v3(0, DYNAMO_TOP.up, 0)), { rotation: { x: 0, y: s.yaw }, keepVelocity: false }));
    const fwd = yawDir(s.yaw);
    const land = add(pos, mul(fwd, 2.6));
    const y = groundBelow(s, add(land, v3(0, 2, 0)), 8);
    s.hop = { from: add(pos, v3(0, DYNAMO_TOP.up, 0)), to: v3(land.x, y ?? pos.y, land.z) };
}
function tickIntro(s) {
    const dim = s.entity.dimension;
    if (fire(s, "light")) {
        zap(s, PFX.voltSpark, at(s, E_HEAD));
        sound(dim, SND.click, s.entity.location, 1, 1.4);
        for (const p of playersNear(s, 48)) {
            safe(() => p.onScreenDisplay.setTitle({ rawtext: [{ translate: "esb.title.edison" }] }, {
                subtitle: { rawtext: [{ translate: "esb.subtitle.edison" }] }, fadeInDuration: 10, stayDuration: 50, fadeOutDuration: 20,
            }));
        }
        message(playersNear(s, 48), "esb.msg.edison_intro");
    }
    const run = s.run;
    const hop = moment("intro", "hop");
    const land = moment("intro", "land");
    if (s.hop && run.tick >= hop && run.tick <= land) {
        const k = (run.tick - hop) / Math.max(1, land - hop);
        const p = v3(lerp(s.hop.from.x, s.hop.to.x, k), lerp(s.hop.from.y, s.hop.to.y, k) + Math.sin(k * Math.PI) * 0.8, lerp(s.hop.from.z, s.hop.to.z, k));
        safe(() => s.entity.teleport(p, { rotation: { x: 0, y: s.yaw }, keepVelocity: false }));
    }
    if (fire(s, "land")) {
        event(s, "esb:to_ground");
        s.inAir = false;
        s.hop = undefined;
        particle(dim, PFX.dust, add(s.entity.location, v3(0, 0.2, 0)));
    }
    const tp = targetPoint(s);
    if (tp && run.tick > land)
        turnTo(s, tp, 8);
}
// ------------------------------------------------------------------------------------------ bulb toss
function tickToss(s) {
    const tp = targetPoint(s);
    if (tp && s.run.tick < moment("bulb_toss", "throw3"))
        turnTo(s, tp, 14);
    for (const name of ["throw1", "throw2", "throw3"]) {
        if (!fire(s, name))
            continue;
        const from = at(s, E_BULB_THROW);
        const goal = tp ?? add(from, mul(yawDir(s.yaw), 8));
        const n = s.phase === 2 ? 2 : 1;
        const d = dist(from, goal);
        const tFlight = d / E.bulb_toss.speed; // ticks
        const vel = isLiving(s.target) ? safe(() => s.target.getVelocity()) ?? v3(0, 0, 0) : v3(0, 0, 0);
        const aim = add(goal, v3(vel.x * tFlight * 0.6, 0.5 * 0.03 * tFlight * tFlight * 0.9, vel.z * tFlight * 0.6));
        const base = norm(sub(aim, from));
        for (let i = 0; i < n; i++) {
            const a = (n === 1 ? 0 : (i - 0.5) * 16) * DEG;
            const dir = v3(base.x * Math.cos(a) - base.z * Math.sin(a), base.y, base.x * Math.sin(a) + base.z * Math.cos(a));
            throwBulb(s, from, mul(dir, E.bulb_toss.speed));
        }
        sound(s.entity.dimension, SND.throw, from, 1, 1.3);
    }
}
function throwBulb(s, from, velocity) {
    const b = safe(() => s.entity.dimension.spawnEntity(VOLT_BULB_ID, from));
    if (!b)
        return;
    const proj = safe(() => b.getComponent("minecraft:projectile"));
    if (!proj) {
        safe(() => b.remove());
        return;
    }
    safe(() => {
        proj.owner = s.entity;
    });
    safe(() => proj.shoot(velocity, { uncertainty: 0 }));
}
/** A thrown bulb shattered: glass and a small electric burst around the impact. */
export function bulbBurst(s, dim, p) {
    const b = E.bulb_toss;
    particle(dim, PFX.glass, p);
    particle(dim, PFX.voltSpark, p, undefined, s?.phase === 2 ? 1 : 0);
    sound(dim, SND.glass, p, 1, 1.0);
    if (!s)
        return;
    for (const t of victims(s, p, b.burst_radius, 2, 2)) {
        if (hurtBy(s, t, b.burst_damage))
            safe(() => t.addEffect("slowness", sec(b.slow_seconds), { amplifier: 1, showParticles: false }));
    }
}
// ------------------------------------------------------------------------------------------ blackout: vanish + backstab
function reveal(s) {
    s.hidden = false;
    safe(() => s.entity.removeEffect("invisibility"));
    particle(s.entity.dimension, PFX.smoke, add(s.entity.location, v3(0, 1.4, 0)));
}
/** Where to reappear: behind the target (by its view direction), else beside it, else in front. */
function blinkSpot(s, t) {
    const view = safe(() => t.getViewDirection()) ?? v3(0, 0, 1);
    const h = Math.sqrt(view.x * view.x + view.z * view.z) || 1;
    const fwd = v3(view.x / h, 0, view.z / h);
    const side = v3(-fwd.z, 0, fwd.x);
    for (const off of [mul(fwd, -1.8), mul(side, 1.8), mul(side, -1.8), mul(fwd, 1.8)]) {
        const p = add(t.location, off);
        const y = groundBelow(s, add(p, v3(0, 1.5, 0)), 5);
        if (y === undefined)
            continue;
        const q = v3(p.x, y, p.z);
        if (airAt(s, q, 3))
            return q;
    }
    return undefined;
}
function tickVanish(s) {
    const dim = s.entity.dimension;
    const run = s.run;
    if (fire(s, "crush")) {
        const bulb = at(s, E_BULB_REST);
        particle(dim, PFX.glass, bulb);
        zap(s, PFX.voltSpark, bulb);
        sound(dim, SND.glass, bulb, 1.2, 0.8);
        for (const p of playersNear(s, 20)) {
            if (isProtectedPlayer(p))
                continue;
            safe(() => p.addEffect("darkness", sec(E.vanish.darkness_seconds), { amplifier: 0, showParticles: false }));
        }
        actionBar(playersNear(s, 20), "esb.msg.blackout");
    }
    if (fire(s, "fade")) {
        s.hidden = true;
        safe(() => s.entity.addEffect("invisibility", sec(4), { amplifier: 0, showParticles: false }));
        particle(dim, PFX.smoke, add(s.entity.location, v3(0, 1.4, 0)));
        sound(dim, SND.portal, s.entity.location, 0.8, 1.4);
    }
    // after the vanish clip: lurk (telegraph at the destination), then strike
    const lurk = sec(s.phase === 2 ? E.vanish.lurk_phase2 : E.vanish.lurk);
    const end = ticksOf("vanish");
    if (run.tick === end) {
        s.blinkTo = isLiving(s.target) ? blinkSpot(s, s.target) : undefined;
    }
    if (run.tick > end && run.tick < end + lurk && s.blinkTo && (run.tick - end) % 4 === 1) {
        zap(s, PFX.telegraph, add(s.blinkTo, v3(0, 0.1, 0)));
        sound(dim, SND.fizz, s.blinkTo, 0.6, 1.6);
    }
    if (run.tick >= end + lurk) {
        if (s.blinkTo) {
            const t = s.target;
            const yaw = t && t.isValid ? yawTo(s.blinkTo, t.location) : s.yaw;
            s.yaw = yaw;
            safe(() => s.entity.teleport(s.blinkTo, { rotation: { x: 0, y: yaw }, keepVelocity: false }));
        }
        s.blinkTo = undefined;
        reveal(s);
        s.run = { kind: "backstab", tick: 0, length: ticksOf("backstab"), fired: new Set() };
        setAction(s, "backstab");
    }
}
function tickBackstab(s) {
    const tp = targetPoint(s);
    if (tp && s.run.tick < moment("backstab", "stab"))
        turnTo(s, tp, 20);
    if (fire(s, "stab")) {
        const t = s.target;
        if (isLiving(t) && !isProtectedPlayer(t) && hdist(t.location, s.entity.location) <= 3.4) {
            if (hurtBy(s, t, s.phase === 2 ? E.vanish.damage_phase2 : E.vanish.damage))
                knockFrom(t, s.entity.location, 0.5, 0.25);
            zap(s, PFX.voltSpark, centerOf(t));
            particle(s.entity.dimension, PFX.glass, centerOf(t));
        }
        sound(s.entity.dimension, SND.glass, s.entity.location, 1, 1.4);
    }
    if (s.run.tick >= s.run.length) {
        if (s.blinksLeft > 0 && isLiving(s.target)) {
            s.blinksLeft--;
            s.run = { kind: "vanish", tick: moment("vanish", "crush"), length: ticksOf("vanish"), fired: new Set(["crush"]) };
            setAction(s, "vanish");
            return;
        }
        endE(s, "vanish");
    }
}
// ------------------------------------------------------------------------------------------ overload (chain lightning)
function tickOverload(s) {
    const dim = s.entity.dimension;
    const d = s.dynamo;
    if (!d || !d.isValid) {
        endE(s, "overload");
        return;
    }
    if (fire(s, "grab"))
        safe(() => d.setProperty("esb:mode", "charging"));
    if (fire(s, "pull"))
        sound(dim, SND.anvil, d.location, 0.8, 1.6);
    if (!fire(s, "discharge"))
        return;
    const o = E.overload;
    const top = add(d.location, v3(0, DYNAMO_TOP.up + 0.3, 0));
    const dmg = s.phase === 2 ? o.damage_phase2 : o.damage;
    const hit = new Set();
    const struck = [];
    for (const t of victims(s, d.location, o.radius, 6, 10)) {
        const c = centerOf(t);
        const dir = sub(c, top);
        const l = Math.sqrt(dir.x * dir.x + dir.y * dir.y + dir.z * dir.z);
        if (rayClear(s, top, norm(dir), l) < l - 0.8)
            continue; // behind cover
        if (hurtBy(s, t, dmg)) {
            hit.add(t.id);
            struck.push(t);
            bolt(s, top, c);
        }
    }
    // each bolt jumps once more to the nearest other creature
    for (const t of struck) {
        const next = victims(s, t.location, o.chain_radius, 3, 3).filter((x) => !hit.has(x.id))
            .sort((a, b) => dist(a.location, t.location) - dist(b.location, t.location))[0];
        if (next && hurtBy(s, next, dmg * 0.5)) {
            hit.add(next.id);
            bolt(s, centerOf(t), centerOf(next));
        }
    }
    sound(dim, SND.thunder, top, 1, 1.2);
    zap(s, PFX.voltSpark, top);
}
/** A jagged line of sparks between two points (stays inside the particle budget). */
function bolt(s, a, b) {
    const n = 6;
    for (let i = 1; i <= n; i++) {
        const k = i / (n + 1);
        const j = i === n ? 0 : 0.35;
        const p = v3(lerp(a.x, b.x, k) + (Math.random() - 0.5) * j, lerp(a.y, b.y, k) + (Math.random() - 0.5) * j, lerp(a.z, b.z, k) + (Math.random() - 0.5) * j);
        zap(s, PFX.zap, p);
    }
}
export function startOverload(s) {
    const d = s.dynamo;
    const dyaw = safe(() => d.getRotation().y) ?? 0;
    const spot = add(d.location, mul(yawDir(dyaw), 1.7));
    const y = groundBelow(s, add(spot, v3(0, 2, 0)), 6);
    particle(s.entity.dimension, PFX.smoke, add(s.entity.location, v3(0, 1.4, 0)));
    const p = v3(spot.x, y ?? d.location.y, spot.z);
    s.yaw = yawTo(p, d.location);
    safe(() => s.entity.teleport(p, { rotation: { x: 0, y: s.yaw }, keepVelocity: false }));
    particle(s.entity.dimension, PFX.smoke, add(p, v3(0, 1.4, 0)));
    startE(s, "overload");
    actionBar(playersNear(s, E.overload.radius + 8), "esb.msg.overload");
}
// ------------------------------------------------------------------------------------------ electric chair
function tickChairCast(s) {
    const t = s.target;
    const tp = targetPoint(s);
    if (tp && s.run.tick < moment("chair", "lock"))
        turnTo(s, tp, 12);
    const dim = s.entity.dimension;
    if (fire(s, "snap")) {
        if (!isLiving(t) || t.typeId !== "minecraft:player" || s.chair)
            return;
        const y = groundBelow(s, add(t.location, v3(0, 1, 0)), 4) ?? t.location.y;
        const p = v3(t.location.x, y, t.location.z);
        const c = safe(() => dim.spawnEntity(CHAIR_ID, p));
        if (!c)
            return;
        safe(() => c.setRotation({ x: 0, y: yawTo(p, s.entity.location) }));
        s.chair = { entity: c, victim: t, locked: false, until: 0, seat: add(p, v3(0, CHAIR_SEAT.up - 0.05, 0)) };
        zap(s, PFX.telegraph, add(p, v3(0, 0.1, 0)));
        sound(dim, SND.fizz, p, 1, 0.8);
        actionBar([t], "esb.msg.chair");
    }
    if (fire(s, "lock") && s.chair && !s.chair.locked) {
        const ch = s.chair;
        const v = ch.victim;
        if (ch.entity.isValid && isLiving(v) && hdist(v.location, ch.entity.location) <= E.chair.catch_radius &&
            Math.abs(v.location.y - ch.entity.location.y) < 1.5) {
            ch.locked = true;
            ch.until = now() + sec(E.chair.strap_seconds);
            safe(() => ch.entity.setProperty("esb:state", "locked"));
            safe(() => v.teleport(ch.seat, { keepVelocity: false }));
            safe(() => v.addEffect("slowness", sec(E.chair.strap_seconds) + 5, { amplifier: 255, showParticles: false }));
            actionBar([v], "esb.msg.strapped");
            sound(dim, SND.anvil, ch.seat, 0.8, 0.6);
        }
        else {
            releaseChair(s);
        }
    }
}
/** Runs every tick while a chair exists (independent of Edison's own actions). */
function tickChair(s) {
    const ch = s.chair;
    if (!ch)
        return;
    if (!ch.entity.isValid || !isLiving(ch.entity) || !isLiving(ch.victim)) {
        releaseChair(s);
        return;
    }
    if (!ch.locked)
        return;
    const t = now();
    if (dist(ch.victim.location, ch.seat) > 0.8)
        safe(() => ch.victim.teleport(ch.seat, { keepVelocity: false }));
    if ((ch.until - t) % 10 === 0) {
        hurtBy(s, ch.victim, s.phase === 2 ? E.chair.tick_damage_phase2 : E.chair.tick_damage);
        zap(s, PFX.voltSpark, add(ch.seat, v3(0, 1.2, 0)));
        sound(s.entity.dimension, SND.fizz, ch.seat, 0.8, 1.2);
    }
    if (t >= ch.until)
        releaseChair(s);
}
export function releaseChair(s) {
    const ch = s.chair;
    if (!ch)
        return;
    s.chair = undefined;
    if (ch.locked && ch.victim.isValid)
        safe(() => ch.victim.removeEffect("slowness"));
    if (ch.entity.isValid) {
        zap(s, PFX.voltSpark, add(ch.entity.location, v3(0, 1, 0)));
        safe(() => ch.entity.remove());
    }
}
// ------------------------------------------------------------------------------------------ transform (Current War)
function tickTransformE(s) {
    const run = s.run;
    if (run.tick === 1) {
        s.phase = 2;
        setProp(s, "esb:phase", 2);
        if (s.dynamo?.isValid)
            safe(() => s.dynamo.setProperty("esb:phase", 2));
    }
    if (!fire(s, "burst"))
        return;
    const dim = s.entity.dimension;
    const pos = s.entity.location;
    if (!dynamoAlive(s)) {
        // the Dynamo is rebuilt for the Current War, behind him
        const back = add(pos, mul(yawDir(s.yaw), -3));
        const y = groundBelow(s, add(back, v3(0, 2, 0)), 6);
        spawnDynamo(s, v3(back.x, y ?? pos.y, back.z), s.yaw);
    }
    const h = s.dynamo ? health(s.dynamo) : undefined;
    safe(() => h?.setCurrentValue?.(E.dynamo.health_phase2));
    zap(s, PFX.voltSpark, at(s, E_CHEST));
    particle(dim, PFX.shockwave, add(pos, v3(0, 0.15, 0)), 7);
    sound(dim, SND.thunder, pos, 1.2, 1.0);
    sound(dim, SND.totem, pos, 0.8, 1.3);
    message(playersNear(s, 64), "esb.msg.edison_phase2");
    for (const t of victims(s, pos, 7, 2, 4))
        knockFrom(t, pos, 1.3, 0.45);
    s.ready.vanish = now() + sec(2);
}
// ------------------------------------------------------------------------------------------ ULTIMATE: Let There Be Light
/** Snaps the lights out, rises as a sun over a ring of giant Sun Bulbs that call lightning onto marked spots, then
 *  a blinding flash hits everyone who can see him - weaker for every bulb the players smashed. */
function startLight(s) {
    startE(s, "ultimate");
    s.ult = newUlt(s.entity.location);
}
function aliveBulbs(s) {
    return (s.ult?.bulbs ?? []).filter((b) => b.isValid && isLiving(b));
}
function tickLight(s) {
    const u = s.ult;
    if (!u)
        return;
    const U = E.ultimate;
    const dim = s.entity.dimension;
    const run = s.run;
    const t = run.tick;
    if (fire(s, "snap")) {
        const ps = playersNear(s, 40).filter((p) => !isProtectedPlayer(p));
        for (const p of ps)
            safe(() => p.addEffect("darkness", sec(U.darkness_seconds), { amplifier: 0, showParticles: false }));
        title(playersNear(s, 64), "esb.title.light", "esb.subtitle.light");
        message(playersNear(s, 64), "esb.msg.light");
        sound(dim, SND.click, s.entity.location, 2, 0.6);
        sound(dim, SND.portal, s.entity.location, 1.4, 0.5);
    }
    const r0 = moment("ultimate", "rise");
    const r1 = r0 + 12;
    if (t === r0) {
        const head = add(u.center, v3(0, 3.2, 0));
        const h = Math.min(U.hover, rayClear(s, head, v3(0, 1, 0), U.hover + 1) - 1);
        if (h >= 2) {
            event(s, "esb:to_air");
            s.inAir = true;
            s.locked = true;
            u.peak = add(u.center, v3(0, h, 0));
        }
    }
    if (s.inAir && t > r0 && t <= r1) {
        const k = (t - r0) / (r1 - r0);
        safe(() => s.entity.teleport(v3(u.center.x, lerp(u.center.y, u.peak.y, 1 - (1 - k) * (1 - k)), u.center.z), { rotation: { x: 0, y: s.yaw }, keepVelocity: false }));
    }
    if (fire(s, "bulbs")) {
        for (let i = 0; i < U.bulbs; i++) {
            const a = (i * 360 / U.bulbs) * DEG;
            const p = v3(u.center.x - Math.sin(a) * U.ring_radius, u.center.y + 4, u.center.z + Math.cos(a) * U.ring_radius);
            const y = groundBelow(s, p, 10) ?? u.center.y;
            const b = safe(() => dim.spawnEntity(SUN_BULB_ID, v3(p.x, y + 1.6, p.z)));
            if (b) {
                u.bulbs.push(b);
                particle(dim, PFX.pillar, v3(p.x, y, p.z));
            }
        }
        sound(dim, SND.charge, u.center, 2, 1.3);
    }
    // strikes: a mark under a player, then lightning from the nearest bulb (no bulbs left, no strikes)
    const st0 = moment("ultimate", "strikes");
    const st1 = moment("ultimate", "strikes_end");
    if (t >= st0 && t < st1 && (t - st0) % U.strike_every_ticks === 0) {
        const bulbs = aliveBulbs(s);
        const ps = playersNear(s, 40).filter((p) => !isProtectedPlayer(p) && dist(p.location, u.center) <= 32);
        if (bulbs.length && ps.length) {
            const p = ps[Math.floor(Math.random() * ps.length)];
            const y = groundBelow(s, add(p.location, v3(0, 1, 0)), 4) ?? p.location.y;
            const pos = v3(p.location.x, y, p.location.z);
            const m = safe(() => dim.spawnEntity(MARKER_ID, v3(pos.x, pos.y + 0.03, pos.z)));
            if (m)
                safe(() => m.setProperty("esb:radius", Math.round(U.strike_radius)));
            const from = bulbs.sort((a, b) => dist(a.location, pos) - dist(b.location, pos))[0];
            u.strikes.push({ pos, at: now() + U.strike_delay_ticks, marker: m, from: add(from.location, v3(0, 0.8, 0)) });
            sound(dim, SND.fizz, pos, 1, 1.8);
        }
    }
    for (const st of [...u.strikes]) {
        if (now() < st.at)
            continue;
        u.strikes.splice(u.strikes.indexOf(st), 1);
        if (st.marker?.isValid)
            safe(() => st.marker.remove());
        const bolt3 = safe(() => dim.spawnEntity(ARC_BOLT_ID, st.pos));
        if (bolt3)
            u.bolts.push({ e: bolt3, until: now() + 7 });
        if (st.from)
            bolt(s, st.from, add(st.pos, v3(0, 0.5, 0)));
        for (const v of victims(s, st.pos, U.strike_radius, 2, 3)) {
            if (hurtBy(s, v, U.strike_damage))
                safe(() => v.addEffect("slowness", 30, { amplifier: 1, showParticles: false }));
        }
        particle(dim, PFX.voltSpark, add(st.pos, v3(0, 0.3, 0)), undefined, 1);
        particle(dim, PFX.dust, add(st.pos, v3(0, 0.2, 0)));
        sound(dim, SND.thunder, st.pos, 0.9, 1.1);
    }
    for (const b of [...u.bolts]) {
        if (now() >= b.until) {
            u.bolts.splice(u.bolts.indexOf(b), 1);
            if (b.e.isValid)
                safe(() => b.e.remove());
        }
    }
    if (fire(s, "charge")) {
        actionBar(playersNear(s, U.flash_radius + 8), "esb.msg.light_charge");
        sound(dim, SND.charge, s.entity.location, 2, 0.5);
    }
    if (t > moment("ultimate", "charge") && t < moment("ultimate", "flash") && t % 5 === 0) {
        for (const b of aliveBulbs(s))
            bolt(s, add(b.location, v3(0, 0.8, 0)), add(s.entity.location, v3(0, 2, 0)));
    }
    if (fire(s, "flash")) {
        const alive = aliveBulbs(s);
        const dmg = (U.flash_damage * alive.length) / U.bulbs;
        const eye = add(s.entity.location, v3(0, 2.2, 0));
        if (dmg > 0) {
            for (const v of victims(s, eye, U.flash_radius, 40, 40)) {
                const c = centerOf(v);
                const d = sub(c, eye);
                const l = Math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z);
                if (rayClear(s, eye, norm(d), l) < l - 0.8)
                    continue; // hidden behind cover
                if (hurtBy(s, v, dmg))
                    safe(() => v.addEffect("blindness", 40, { amplifier: 0, showParticles: false }));
            }
        }
        else {
            message(playersNear(s, 64), "esb.msg.light_fizzle");
        }
        for (const b of u.bulbs) {
            if (!b.isValid)
                continue;
            particle(dim, PFX.glass, add(b.location, v3(0, 0.8, 0)));
            safe(() => b.remove());
        }
        u.bulbs = [];
        for (const st of u.strikes)
            if (st.marker?.isValid)
                safe(() => st.marker.remove());
        u.strikes = [];
        particle(dim, PFX.voltSpark, eye, undefined, 1);
        particle(dim, PFX.shockwave, add(u.center, v3(0, 0.2, 0)), U.ring_radius + 3);
        shake(playersNear(s, 64), 0.9, 1.2);
        sound(dim, SND.thunder, eye, 2, 0.7);
        sound(dim, SND.glass, eye, 2, 0.6);
        sound(dim, SND.totem, eye, 1, 1.4);
    }
    const fl = moment("ultimate", "flash");
    const ld = moment("ultimate", "land");
    if (s.inAir && t > fl && t <= ld) {
        const k = (t - fl) / Math.max(1, ld - fl);
        safe(() => s.entity.teleport(v3(u.center.x, lerp(u.peak.y, u.center.y, k * k), u.center.z), { rotation: { x: 0, y: s.yaw }, keepVelocity: false }));
    }
    if (fire(s, "land") && s.inAir) {
        event(s, "esb:to_ground");
        s.inAir = false;
        particle(dim, PFX.dust, add(s.entity.location, v3(0, 0.2, 0)));
    }
}
// ------------------------------------------------------------------------------------------ death
export function beginDyingE(s) {
    if (s.dying)
        return;
    releaseChair(s);
    clearUlt(s);
    if (s.hidden)
        reveal(s);
    if (s.inAir) {
        event(s, "esb:to_ground");
        s.inAir = false;
    }
    s.hop = undefined;
    s.run = undefined;
    s.dying = true;
    s.dyingTick = now();
    s.invulnerable = true;
    event(s, "esb:dying");
    s.locked = true;
    setAction(s, "death");
    safe(() => s.entity.clearVelocity());
    sound(s.entity.dimension, SND.glass, s.entity.location, 1, 0.6);
}
function tickDyingE(s) {
    const t = now() - s.dyingTick;
    const dim = s.entity.dimension;
    if (t === moment("death", "kneel"))
        sound(dim, SND.fizz, s.entity.location, 1, 0.6);
    if (t === moment("death", "fade")) {
        particle(dim, PFX.glass, at(s, E_BULB_REST));
        message(playersNear(s, 64), "esb.msg.edison_death");
        if (s.dynamo?.isValid) {
            // the Dynamo powers down with him
            particle(dim, PFX.smoke, add(s.dynamo.location, v3(0, 1.5, 0)));
            sound(dim, SND.fizz, s.dynamo.location, 1, 0.5);
            const d = s.dynamo;
            s.dynamo = undefined;
            safe(() => d.remove());
        }
    }
    if (t >= ticksOf("death") && !s.allowKill) {
        s.allowKill = true;
        const h = health(s.entity);
        const amount = (h?.currentValue ?? 1) + 1000;
        const killer = s.killer && s.killer.isValid ? s.killer : undefined;
        const done = killer
            ? safe(() => s.entity.applyDamage(amount, { cause: EntityDamageCause.entityAttack, damagingEntity: killer }))
            : false;
        if (!done)
            safe(() => s.entity.kill());
    }
}
// ------------------------------------------------------------------------------------------ brain
function ready(s, a) {
    return now() >= s.ready[a];
}
function lineOfSight(s, t) {
    const from = add(s.entity.location, v3(0, 2.6, 0));
    const to = centerOf(t);
    const d = sub(to, from);
    const l = Math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z);
    return rayClear(s, from, norm(d), l) >= l - 0.6;
}
function validTarget(s, t) {
    if (!isLiving(t) || isProtectedPlayer(t))
        return false;
    if (t.dimension.id !== s.entity.dimension.id)
        return false;
    return dist(t.location, s.entity.location) <= E.leash_range;
}
function nearestPlayer(s) {
    let best;
    let bd = Infinity;
    for (const p of playersNear(s, E.aggro_range)) {
        if (isProtectedPlayer(p))
            continue;
        const d = dist(p.location, s.entity.location);
        if (d < bd) {
            bd = d;
            best = p;
        }
    }
    return best;
}
function tickRunE(s) {
    const run = s.run;
    run.tick++;
    switch (run.kind) {
        case "intro":
            tickIntro(s);
            break;
        case "bulb_toss":
            tickToss(s);
            break;
        case "vanish":
            tickVanish(s);
            return; // manages its own end (lurk, then backstab)
        case "backstab":
            tickBackstab(s);
            return;
        case "overload":
            tickOverload(s);
            break;
        case "chair":
            tickChairCast(s);
            break;
        case "transform":
            tickTransformE(s);
            break;
        case "flourish":
            if (fire(s, "catch"))
                zap(s, PFX.voltSpark, at(s, E_BULB_REST));
            break;
        case "ultimate":
            tickLight(s);
            break;
        default:
            break;
    }
    if (s.run && s.run.tick >= s.run.length) {
        const k = run.kind;
        endE(s, k === "bulb_toss" || k === "overload" || k === "chair" ? k : undefined);
    }
}
export function thinkEdison(s) {
    tickChair(s);
    if (s.dying) {
        tickDyingE(s);
        return;
    }
    if (s.run) {
        tickRunE(s);
        return;
    }
    if (!validTarget(s, s.target))
        s.target = nearestPlayer(s);
    if (s.phase === 1 && hpFrac(s) <= E.phase2_at) {
        startE(s, "transform");
        return;
    }
    const t = s.target;
    if (!validTarget(s, t)) {
        s.target = undefined;
        if (now() >= s.nextFlourish && safe(() => s.entity.isOnGround) !== false)
            startE(s, "flourish");
        return;
    }
    if (now() < s.gapUntil || now() < s.nextDecision)
        return;
    s.nextDecision = now() + DECIDE_EVERY;
    // ULTIMATE: Let There Be Light below 35% health, then on its own long cooldown
    if (hpFrac(s) <= E.ultimate.hp_threshold && now() >= s.ready.ultimate) {
        if (s.hidden)
            reveal(s);
        startLight(s);
        return;
    }
    const d = hdist(t.location, s.entity.location);
    const options = [];
    if (d <= E.vanish.range && ready(s, "vanish"))
        options.push(["vanish", 3]);
    if (d >= E.bulb_toss.range_min && d <= E.bulb_toss.range_max && ready(s, "bulb_toss") && lineOfSight(s, t)) {
        options.push(["bulb_toss", d > 8 ? 3 : 1]);
    }
    if (dynamoAlive(s) && ready(s, "overload") && dist(s.dynamo.location, s.entity.location) <= 30 &&
        victims(s, s.dynamo.location, E.overload.radius, 6, 10).length > 0)
        options.push(["overload", 2]);
    if (t.typeId === "minecraft:player" && !s.chair && d <= E.chair.range && ready(s, "chair"))
        options.push(["chair", 2]);
    if (!options.length || (d < 2.6 && Math.random() < 0.5))
        return;
    const total = options.reduce((a, [, w]) => a + w, 0);
    let r = Math.random() * total;
    let pick = options[0][0];
    for (const [a, w] of options) {
        r -= w;
        if (r <= 0) {
            pick = a;
            break;
        }
    }
    if (pick === "overload")
        startOverload(s);
    else if (pick === "vanish") {
        s.blinksLeft = s.phase === 2 ? 1 : 0;
        startE(s, "vanish");
    }
    else
        startE(s, pick);
}
export function isStunned(s) {
    return s.kind === "edison" && now() < s.stunUntil;
}
