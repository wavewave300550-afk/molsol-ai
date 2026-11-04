import { EntityDamageCause } from "@minecraft/server";
import { BALANCE } from "./balance.js";
import { actionBar, at, centerOf, clearUlt, event, face, groundBelow, hurt, isLiving, knockFrom, lock, message, newUlt, now, playersNear, rayClear, safe, sec, setAction, setProp, shake, title, turnTo, unlock, victims, } from "./boss.js";
import { PFX, SND, particle, sound } from "./fx.js";
import { CHEST, CORE, PALM_DIVE, PALM_QUAKE, PALM_SHOT } from "./offsets.js";
import { ACTIONS, GEAR_ID, SIGIL_ID } from "./spec.js";
import { DEG, add, clamp, hdist, lerp, mul, norm, sub, v3, yawTo } from "./vec.js";
const COOLDOWN = {
    gear_volley: BALANCE.gear_volley.cooldown,
    quake: BALANCE.quake.cooldown,
    vitruvian: BALANCE.vitruvian.cooldown,
    dive: BALANCE.dive.cooldown,
};
function ticksOf(kind) {
    return kind === "none" ? 0 : sec(ACTIONS[kind].length);
}
function moment(kind, name) {
    if (kind === "none")
        return 0;
    const m = ACTIONS[kind].moments;
    return sec(m[name]);
}
/** Start a scripted action: movement is locked and the client plays the matching animation. */
export function startAction(s, kind) {
    lock(s);
    s.run = { kind, tick: 0, length: ticksOf(kind), fired: new Set() };
    setAction(s, kind);
    const dim = s.entity.dimension;
    const pos = s.entity.location;
    if (kind === "gear_volley")
        sound(dim, SND.click, pos, 1, 0.6);
    if (kind === "quake")
        sound(dim, SND.spell, pos, 0.8, 1.4);
    if (kind === "vitruvian")
        sound(dim, SND.charge, pos, 1.2, 1.1);
    if (kind === "transform") {
        s.invulnerable = true;
        s.phase = 2;
        setProp(s, "esb:phase", 2);
        sound(dim, SND.summon, pos, 1.4, 0.8);
    }
    if (kind === "intro") {
        s.invulnerable = true;
        sound(dim, SND.bell, pos, 1.6, 0.7);
    }
}
/** Ends the current action and frees the boss (cooldowns and the global gap start here). */
export function endAction(s, ability) {
    const kind = s.run?.kind;
    s.run = undefined;
    removeSigil(s);
    if (kind === "intro" || kind === "transform" || kind === "ultimate")
        s.invulnerable = false;
    if (kind === "ultimate") {
        clearUlt(s);
        s.ready.ultimate = now() + sec(BALANCE.ultimate.cooldown);
    }
    if (kind === "flourish")
        s.nextFlourish = now() + sec(lerp(BALANCE.flourish.every_min, BALANCE.flourish.every_max, Math.random()));
    setAction(s, "none");
    s.gapUntil = now() + sec(BALANCE.global_gap);
    if (ability)
        s.ready[ability] = now() + sec(COOLDOWN[ability] * (s.phase === 2 ? 0.8 : 1));
    unlock(s);
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
function targetPoint(s) {
    return isLiving(s.target) ? centerOf(s.target) : undefined;
}
// ------------------------------------------------------------------------------------------ per-tick driver
export function tickRun(s) {
    const run = s.run;
    if (!run)
        return;
    run.tick++;
    switch (run.kind) {
        case "intro":
            tickIntro(s);
            break;
        case "gear_volley":
            tickGears(s);
            break;
        case "quake":
            tickQuake(s);
            break;
        case "vitruvian":
            tickVitruvian(s);
            break;
        case "transform":
            tickTransform(s);
            break;
        case "dive_rise":
        case "dive_hover":
        case "dive_strike":
            tickDive(s);
            return; // the dive manages its own end
        case "flourish":
            break;
        case "ultimate":
            tickOpus(s);
            break;
        default:
            break;
    }
    if (s.run && s.run.tick >= s.run.length) {
        const ab = run.kind === "gear_volley" || run.kind === "quake" || run.kind === "vitruvian"
            ? run.kind : undefined;
        endAction(s, ab);
    }
}
// ------------------------------------------------------------------------------------------ intro
function tickIntro(s) {
    const dim = s.entity.dimension;
    const pos = s.entity.location;
    if (fire(s, "burst")) {
        particle(dim, PFX.pillar, pos);
        particle(dim, PFX.pages, at(s, CHEST));
        sound(dim, SND.page, pos, 1.2, 0.8);
        for (const p of playersNear(s, 48)) {
            safe(() => p.onScreenDisplay.setTitle({ rawtext: [{ translate: "esb.title.boss" }] }, {
                subtitle: { rawtext: [{ translate: "esb.subtitle.boss" }] }, fadeInDuration: 10, stayDuration: 50, fadeOutDuration: 20,
            }));
        }
    }
    if (fire(s, "rise"))
        message(playersNear(s, 48), "esb.msg.intro");
    if (fire(s, "flex")) {
        particle(dim, PFX.steam, at(s, CORE));
        particle(dim, PFX.spark, at(s, PALM_SHOT));
        sound(dim, SND.anvil, pos, 0.6, 1.6);
    }
    const tp = targetPoint(s);
    if (tp && s.run && s.run.tick > moment("intro", "rise"))
        turnTo(s, tp, 6);
}
// ------------------------------------------------------------------------------------------ gear volley
const SHOTS = ["shot1", "shot2", "shot3"];
function tickGears(s) {
    const tp = targetPoint(s);
    const run = s.run;
    if (tp && run.tick <= moment("gear_volley", "shot3"))
        turnTo(s, tp, 12);
    for (const name of SHOTS) {
        if (!fire(s, name))
            continue;
        const dim = s.entity.dimension;
        const palm = at(s, PALM_SHOT);
        const goal = tp ?? add(palm, v3(-Math.sin(s.yaw * DEG) * 10, -1, Math.cos(s.yaw * DEG) * 10));
        const base = norm(sub(goal, palm));
        const n = s.phase === 2 ? BALANCE.gear_volley.gears_phase2 : BALANCE.gear_volley.gears_phase1;
        for (let i = 0; i < n; i++) {
            const a = (i - (n - 1) / 2) * BALANCE.gear_volley.spread_deg * DEG;
            const dir = v3(base.x * Math.cos(a) - base.z * Math.sin(a), base.y, base.x * Math.sin(a) + base.z * Math.cos(a));
            shootGear(s, palm, mul(dir, BALANCE.gear_volley.speed));
        }
        particle(dim, PFX.spark, palm);
        sound(dim, SND.shot, palm, 1, 1.5);
        sound(dim, SND.click, palm, 1, 0.8);
    }
}
export function shootGear(s, from, velocity) {
    const g = safe(() => s.entity.dimension.spawnEntity(GEAR_ID, from));
    if (!g)
        return undefined;
    const proj = safe(() => g.getComponent("minecraft:projectile"));
    if (!proj) {
        safe(() => g.remove());
        return undefined;
    }
    safe(() => {
        proj.owner = s.entity;
    });
    safe(() => proj.shoot(velocity, { uncertainty: 0 }));
    return g;
}
// ------------------------------------------------------------------------------------------ gauntlet quake
function tickQuake(s) {
    const tp = targetPoint(s);
    if (tp && s.run.tick < moment("quake", "impact") - 4)
        turnTo(s, tp, 10);
    if (!fire(s, "impact"))
        return;
    const dim = s.entity.dimension;
    const q = BALANCE.quake;
    const fist = at(s, PALM_QUAKE);
    const center = v3(fist.x, s.entity.location.y, fist.z);
    for (const t of victims(s, center, q.radius, 2, 3)) {
        const d = hdist(t.location, center);
        const k = d <= 2.5 ? 1 : lerp(1, 0.5, clamp((d - 2.5) / (q.radius - 2.5), 0, 1));
        if (hurt(s, t, q.damage * k))
            knockFrom(t, center, q.knockback, q.lift);
    }
    particle(dim, PFX.shockwave, add(center, v3(0, 0.15, 0)), q.radius);
    particle(dim, PFX.dust, add(center, v3(0, 0.3, 0)));
    particle(dim, PFX.spark, add(center, v3(0, 0.5, 0)));
    sound(dim, SND.boom, center, 1.2, 0.9);
    sound(dim, SND.anvil, center, 1, 0.6);
}
// ------------------------------------------------------------------------------------------ vitruvian judgement
export function vitruvianRadius(s) {
    return s.phase === 2 ? BALANCE.vitruvian.radius_phase2 : BALANCE.vitruvian.radius_phase1;
}
function spawnSigil(s, p, radius) {
    const e = safe(() => s.entity.dimension.spawnEntity(SIGIL_ID, p));
    if (e)
        safe(() => e.setProperty("esb:radius", Math.round(clamp(radius, 1, 20))));
    return e;
}
export function removeSigil(s) {
    if (s.sigil && s.sigil.isValid)
        safe(() => s.sigil.remove());
    s.sigil = undefined;
    if (s.dive?.marker && s.dive.marker.isValid)
        safe(() => s.dive.marker.remove());
    if (s.dive)
        s.dive.marker = undefined;
}
function tickVitruvian(s) {
    const dim = s.entity.dimension;
    const R = vitruvianRadius(s);
    const pos = s.entity.location;
    const feet = v3(pos.x, (groundBelow(s, add(pos, v3(0, 0.5, 0)), 4) ?? pos.y) + 0.02, pos.z);
    if (fire(s, "sigil")) {
        removeSigil(s);
        s.sigil = spawnSigil(s, feet, R);
        actionBar(playersNear(s, R + 8), "esb.msg.vitruvian");
        sound(dim, SND.spell, pos, 1.2, 0.7);
    }
    const run = s.run;
    const sig = moment("vitruvian", "sigil");
    const det = moment("vitruvian", "detonate");
    if (run.tick > sig && run.tick < det && (run.tick - sig) % 5 === 0)
        particle(dim, PFX.sigilEdge, add(feet, v3(0, 0.1, 0)), R);
    if (!fire(s, "detonate"))
        return;
    const v = BALANCE.vitruvian;
    for (const t of victims(s, feet, R, 2, 4)) {
        if (hurt(s, t, v.damage))
            knockFrom(t, feet, 0.5, v.lift);
    }
    particle(dim, PFX.sigilBurst, add(feet, v3(0, 0.1, 0)), R);
    particle(dim, PFX.spark, add(feet, v3(0, 1.2, 0)));
    sound(dim, SND.boom, feet, 1.3, 0.8);
    sound(dim, SND.totem, feet, 0.7, 1.4);
    removeSigil(s);
}
// ------------------------------------------------------------------------------------------ transform (phase 2)
function tickTransform(s) {
    if (!fire(s, "burst"))
        return;
    const dim = s.entity.dimension;
    const pos = s.entity.location;
    particle(dim, PFX.pages, at(s, CHEST));
    particle(dim, PFX.shockwave, add(pos, v3(0, 0.15, 0)), 7);
    particle(dim, PFX.spark, at(s, CORE));
    sound(dim, SND.totem, pos, 1.2, 0.8);
    sound(dim, SND.flap, pos, 1.4, 0.8);
    message(playersNear(s, 64), "esb.msg.phase2");
    for (const t of victims(s, pos, 7, 2, 4))
        knockFrom(t, pos, 1.4, 0.5);
    // phase 2 opens with the ornithopter dive soon after
    s.ready.dive = now() + sec(3);
}
// ------------------------------------------------------------------------------------------ ornithopter dive (phase 2)
const RISE_TICKS = 12;
const STRIKE_TICKS = moment("dive_strike", "impact");
function teleport(s, p) {
    safe(() => s.entity.teleport(p, { rotation: { x: 0, y: s.yaw }, keepVelocity: false, checkForBlocks: false }));
}
export function startDive(s) {
    startAction(s, "dive_rise");
    const pos = s.entity.location;
    s.dive = { stage: "rise", stageTick: 0, from: { ...pos }, peak: { ...pos }, landing: { ...pos }, lockAt: 0, hoverTicks: 0 };
    sound(s.entity.dimension, SND.flap, pos, 1.2, 1.1);
}
function landingFor(s) {
    const t = s.target;
    const p = isLiving(t) ? t.location : add(s.entity.location, v3(-Math.sin(s.yaw * DEG) * 6, 0, Math.cos(s.yaw * DEG) * 6));
    const y = groundBelow(s, add(p, v3(0, 2, 0)), 30);
    return v3(p.x, y ?? p.y, p.z);
}
function tickDive(s) {
    const d = s.dive;
    const run = s.run;
    if (!d) {
        endAction(s, "dive");
        return;
    }
    const dim = s.entity.dimension;
    const tp = targetPoint(s);
    if (tp && d.stage !== "strike")
        turnTo(s, tp, 10);
    if (d.stage === "rise") {
        if (run.tick < moment("dive_rise", "leap"))
            return;
        if (run.tick === moment("dive_rise", "leap")) {
            const pos = s.entity.location;
            const head = add(pos, v3(0, 3.6, 0));
            const room = rayClear(s, head, v3(0, 1, 0), BALANCE.dive.height + 1);
            const h = Math.min(BALANCE.dive.height, room - 1);
            if (h < 3) {
                // no head room: cancel the dive cleanly
                s.dive = undefined;
                endAction(s, "dive");
                return;
            }
            event(s, "esb:to_air");
            s.inAir = true;
            s.locked = true;
            d.from = { ...pos };
            d.peak = add(pos, v3(0, h, 0));
            particle(dim, PFX.dust, add(pos, v3(0, 0.3, 0)));
            sound(dim, SND.flap, pos, 1.4, 0.9);
        }
        d.stageTick++;
        const k = clamp(d.stageTick / RISE_TICKS, 0, 1);
        const e = 1 - (1 - k) * (1 - k);
        teleport(s, v3(d.from.x, lerp(d.from.y, d.peak.y, e), d.from.z));
        if (d.stageTick >= RISE_TICKS) {
            d.stage = "hover";
            d.stageTick = 0;
            d.hoverTicks = sec(BALANCE.dive.hover);
            d.lockAt = d.hoverTicks - sec(0.6);
            d.landing = landingFor(s);
            d.marker = spawnSigil(s, v3(d.landing.x, d.landing.y + 0.02, d.landing.z), BALANCE.dive.radius);
            s.run = { kind: "dive_hover", tick: 0, length: d.hoverTicks, fired: new Set() };
            setAction(s, "dive_hover");
            actionBar(playersNear(s, 40), "esb.msg.dive");
        }
        return;
    }
    if (d.stage === "hover") {
        d.stageTick++;
        if (d.stageTick % 6 === 0)
            sound(dim, SND.flap, s.entity.location, 0.9, 1.2);
        teleport(s, v3(d.peak.x, d.peak.y + Math.sin(d.stageTick * 0.3) * 0.15, d.peak.z));
        if (d.stageTick < d.lockAt) {
            d.landing = landingFor(s);
            if (d.marker?.isValid)
                safe(() => d.marker.teleport(v3(d.landing.x, d.landing.y + 0.02, d.landing.z)));
        }
        if (d.stageTick >= d.hoverTicks) {
            // keep the landing point if the straight path is clear, otherwise drop straight down
            const path = sub(d.landing, d.peak);
            const len = Math.sqrt(path.x * path.x + path.y * path.y + path.z * path.z);
            if (len > 0.5 && rayClear(s, add(d.peak, v3(0, 1, 0)), norm(path), len) < len - 1.5) {
                const y = groundBelow(s, d.peak, 40);
                d.landing = v3(d.peak.x, y ?? d.from.y, d.peak.z);
            }
            face(s, yawTo(d.peak, d.landing));
            d.stage = "strike";
            d.stageTick = 0;
            s.run = { kind: "dive_strike", tick: 0, length: ticksOf("dive_strike"), fired: new Set() };
            setAction(s, "dive_strike");
        }
        return;
    }
    // strike: straight line from the peak to the landing point, arriving exactly on the impact frame
    d.stageTick++;
    run.tick = d.stageTick;
    if (d.stageTick <= STRIKE_TICKS) {
        const k = d.stageTick / STRIKE_TICKS;
        const e = k * k;
        teleport(s, v3(lerp(d.peak.x, d.landing.x, e), lerp(d.peak.y, d.landing.y, e), lerp(d.peak.z, d.landing.z, e)));
    }
    if (d.stageTick === STRIKE_TICKS) {
        event(s, "esb:to_ground");
        s.inAir = false;
        const dv = BALANCE.dive;
        const fist = at(s, PALM_DIVE);
        const center = v3(fist.x, d.landing.y, fist.z);
        for (const t of victims(s, center, dv.radius, 2, 3)) {
            if (hurt(s, t, dv.damage))
                knockFrom(t, center, 1.2, dv.lift);
        }
        particle(dim, PFX.shockwave, add(center, v3(0, 0.15, 0)), dv.radius);
        particle(dim, PFX.dust, add(center, v3(0, 0.3, 0)));
        particle(dim, PFX.sigilBurst, add(center, v3(0, 0.1, 0)), dv.radius);
        sound(dim, SND.boom, center, 1.3, 0.8);
        if (d.marker?.isValid)
            safe(() => d.marker.remove());
        d.marker = undefined;
    }
    if (d.stageTick >= ticksOf("dive_strike")) {
        s.dive = undefined;
        endAction(s, "dive");
    }
}
/** Emergency: back on the ground with gravity, wherever it is. */
export function forceGround(s) {
    if (s.inAir) {
        event(s, "esb:to_ground");
        s.inAir = false;
    }
    removeSigil(s);
    s.dive = undefined;
}
// ------------------------------------------------------------------------------------------ ULTIMATE: Opus Magnum
/** Rises in the Vitruvian pose with a giant halo over an arena-sized sigil with four golden sanctuaries, spins
 *  spraying a spiral of gears, gathers, then slams down: everything inside the sigil but outside the sanctuaries is hit. */
export function startOpus(s) {
    startAction(s, "ultimate");
    s.invulnerable = true;
    s.ult = newUlt(s.entity.location);
    sound(s.entity.dimension, SND.summon, s.entity.location, 1.6, 0.6);
}
function tickOpus(s) {
    const u = s.ult;
    const run = s.run;
    if (!u)
        return;
    const U = BALANCE.ultimate;
    const dim = s.entity.dimension;
    const t = run.tick;
    const rise0 = moment("ultimate", "rise");
    const rise1 = moment("ultimate", "sigil") + 4;
    if (t === rise0) {
        const head = add(u.center, v3(0, 3.6, 0));
        const h = Math.min(U.height, rayClear(s, head, v3(0, 1, 0), U.height + 1) - 1);
        if (h >= 3) {
            event(s, "esb:to_air");
            s.inAir = true;
            s.locked = true;
            u.peak = add(u.center, v3(0, h, 0));
        }
        message(playersNear(s, 64), "esb.msg.opus");
    }
    if (s.inAir && t > rise0 && t <= rise1) {
        const k = (t - rise0) / (rise1 - rise0);
        teleport(s, v3(u.center.x, lerp(u.center.y, u.peak.y, 1 - (1 - k) * (1 - k)), u.center.z));
    }
    if (fire(s, "sigil")) {
        const gy = (groundBelow(s, add(u.center, v3(0, 1, 0)), 6) ?? u.center.y) + 0.02;
        const big = spawnSigil(s, v3(u.center.x, gy, u.center.z), U.radius);
        if (big)
            u.extras.push(big);
        const d = U.radius * 0.62;
        for (const [sx, sz] of [[d, d], [-d, d], [d, -d], [-d, -d]]) {
            const p = v3(u.center.x + sx, u.center.y + 3, u.center.z + sz);
            const y = groundBelow(s, p, 10) ?? u.center.y;
            const q = v3(p.x, y + 0.03, p.z);
            u.sanctuaries.push(q);
            const e = spawnSigil(s, q, 3);
            if (e)
                u.extras.push(e);
            particle(dim, PFX.pillar, q);
        }
        const ps = playersNear(s, 64);
        title(ps, "esb.title.opus", "esb.subtitle.opus");
        shake(ps, 0.25, 1.0);
        sound(dim, SND.bell, u.center, 2, 0.5);
    }
    const b0 = moment("ultimate", "barrage");
    const b1 = moment("ultimate", "barrage_end");
    if (t >= b0 && t < b1 && (t - b0) % U.wave_every_ticks === 0) {
        u.wave++;
        const from = add(s.entity.location, v3(0, 2.4, 0));
        const base = u.wave * U.spiral_step_deg;
        for (let k = 0; k < U.gears_per_wave; k++) {
            const a = (base + (k * 360) / U.gears_per_wave) * DEG;
            const dir = norm(v3(-Math.sin(a), s.inAir ? -0.33 : 0.02, Math.cos(a)));
            shootGear(s, from, mul(dir, U.gear_speed));
        }
        if (u.wave % 2 === 0)
            sound(dim, SND.click, from, 1, 1.4);
        if (u.wave % 3 === 0)
            particle(dim, PFX.spark, from);
    }
    if (fire(s, "gather")) {
        actionBar(playersNear(s, U.radius + 10), "esb.msg.opus_judgement");
        sound(dim, SND.charge, s.entity.location, 2, 0.6);
    }
    const slam = moment("ultimate", "slam");
    const land = moment("ultimate", "land");
    if (t > moment("ultimate", "gather") && t < slam && t % 6 === 0) {
        particle(dim, PFX.sigilEdge, add(u.center, v3(0, 0.1, 0)), U.radius);
        for (const q of u.sanctuaries)
            particle(dim, PFX.sigilEdge, add(q, v3(0, 0.1, 0)), 3);
    }
    if (s.inAir && t > slam && t <= land) {
        const k = (t - slam) / Math.max(1, land - slam);
        teleport(s, v3(u.center.x, lerp(u.peak.y, u.center.y, k * k), u.center.z));
    }
    if (fire(s, "land")) {
        if (s.inAir) {
            event(s, "esb:to_ground");
            s.inAir = false;
        }
        const c = v3(u.center.x, u.center.y, u.center.z);
        for (const v of victims(s, c, U.radius, 3, 8)) {
            const safeSpot = u.sanctuaries.some((q) => hdist(v.location, q) <= U.sanctuary_radius);
            if (safeSpot)
                continue;
            if (hurt(s, v, U.damage))
                knockFrom(v, c, 0.8, U.lift);
        }
        particle(dim, PFX.sigilBurst, add(c, v3(0, 0.1, 0)), U.radius);
        particle(dim, PFX.sigilBurst, add(c, v3(0, 0.1, 0)), U.radius * 0.5);
        particle(dim, PFX.shockwave, add(c, v3(0, 0.15, 0)), U.radius);
        particle(dim, PFX.dust, add(c, v3(0, 0.3, 0)));
        particle(dim, PFX.pages, add(c, v3(0, 1.5, 0)));
        shake(playersNear(s, 64), 0.8, 1.4);
        sound(dim, SND.boom, c, 2, 0.6);
        sound(dim, SND.totem, c, 1.2, 0.8);
        sound(dim, SND.anvil, c, 1.4, 0.5);
    }
}
// ------------------------------------------------------------------------------------------ death
export function beginDying(s) {
    if (s.dying)
        return;
    forceGround(s);
    clearUlt(s);
    s.run = undefined;
    s.dying = true;
    s.dyingTick = now();
    s.invulnerable = true;
    event(s, "esb:dying");
    s.locked = true;
    setAction(s, "death");
    safe(() => s.entity.clearVelocity());
    sound(s.entity.dimension, SND.anvilBreak, s.entity.location, 1, 0.7);
}
export function tickDying(s) {
    const t = now() - s.dyingTick;
    const dim = s.entity.dimension;
    const kneel = sec(ACTIONS.death.moments.kneel);
    const pages = sec(ACTIONS.death.moments.pages);
    if (t === kneel)
        sound(dim, SND.anvil, s.entity.location, 0.7, 0.5);
    if (t === pages) {
        particle(dim, PFX.pages, at(s, CHEST));
        sound(dim, SND.page, s.entity.location, 1.2, 0.7);
        message(playersNear(s, 64), "esb.msg.death");
    }
    if (t >= sec(ACTIONS.death.length) && !s.allowKill) {
        s.allowKill = true;
        const h = s.entity.getComponent("minecraft:health");
        const amount = (h?.currentValue ?? 1) + 1000;
        const killer = s.killer && s.killer.isValid ? s.killer : undefined;
        const done = killer
            ? safe(() => s.entity.applyDamage(amount, { cause: EntityDamageCause.entityAttack, damagingEntity: killer }))
            : false;
        if (!done)
            safe(() => s.entity.kill());
    }
}
