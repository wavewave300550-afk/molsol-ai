import { BALANCE } from "./balance.js";
import { chooseAttack, centerOf, isProtectedPlayer, lineOfSight, startAction, startAttack, startStepBack, tickAction, victims, } from "./combat.js";
import { ACTION_TICKS, IDLE_TICKS, event, face, isLiving, lock, now, safe, sec, setAction, setFlight, setIdle, setProp, unlock, } from "./dragon.js";
import { canTakeOff, startTakeoff, tickFlight } from "./flight.js";
import { add, bearing, dist, hdist, turnToward, v3, yawTo } from "./vec.js";
const TR = BALANCE.territory;
const BUSY_FLIGHT = new Set(["takeoff", "launch", "landing", "touchdown"]);
/** One tick of a dragon's life. */
export function think(s) {
    if (s.dying) {
        tickDying(s);
        return;
    }
    const t = now();
    if (s.run)
        tickAction(s);
    if (s.idle)
        tickIdle(s);
    if (s.flight !== "ground")
        tickFlight(s);
    // perceive after advancing: anything it starts begins on the next tick, exactly like attacks do
    if ((t + s.id.length) % 5 === 0)
        perceive(s);
    updateRunFlag(s);
    if (s.run || s.idle || t < s.gapUntil)
        return;
    if (BUSY_FLIGHT.has(s.flight))
        return;
    const target = isLiving(s.target) ? s.target : undefined;
    if (target)
        combat(s, target);
    else if (s.flight === "ground")
        idle(s);
}
// ------------------------------------------------------------------------------------------------ perception
function players(s, radius) {
    const e = s.entity;
    const list = safe(() => e.dimension.getPlayers({ location: e.location, maxDistance: radius })) ?? [];
    return list.filter((p) => isLiving(p) && !isProtectedPlayer(p));
}
const nearCountCache = new Map();
function perceive(s) {
    const e = s.entity;
    const pos = e.location;
    const t = now();
    if (s.target) {
        const tg = s.target;
        const valid = isLiving(tg) && tg.dimension.id === e.dimension.id && !isProtectedPlayer(tg);
        if (valid && dist(tg.location, pos) <= TR.warn_radius + 8 && hdist(tg.location, s.home) <= TR.leash_radius + 16) {
            s.lastTargetSeen = t;
        }
        if (!valid || t - s.lastTargetSeen > sec(TR.forget_after))
            calmDown(s);
    }
    const near = players(s, TR.warn_radius);
    near.sort((a, b) => dist(a.location, pos) - dist(b.location, pos));
    if (!s.target && near.length) {
        const p = near[0];
        const d = dist(p.location, pos);
        const seen = lineOfSight(s, add(pos, v3(0, 4, 0)), centerOf(p));
        // anyone in range wakes a resting dragon: it gets up before anything else
        if (s.idle?.kind === "rest") {
            startRise(s);
            return;
        }
        if (d <= TR.danger_radius && seen) {
            becomeHostile(s, p);
        }
        else if (seen && s.flight === "ground" && !s.run && s.idle?.kind !== "rise") {
            const warnedAt = s.warned.get(p.id);
            if (warnedAt !== undefined && t - warnedAt >= sec(TR.linger_before_attack) && t - warnedAt < sec(TR.warn_cooldown * 2)) {
                becomeHostile(s, p);
            }
            else if (t - s.lastWarn >= sec(TR.warn_cooldown) && t >= s.gapUntil) {
                // notice -> alert (head snaps up, tense) -> warning roar; no damage
                stopIdle(s);
                s.lastWarn = t;
                s.warned.set(p.id, t);
                s.queue = ["roar"];
                startAction(s, "alert", p);
            }
        }
    }
    for (const [id, at] of s.warned)
        if (t - at > sec(TR.warn_cooldown * 3))
            s.warned.delete(id);
    nearCountCache.set(s.id, s.target ? victims(s, pos, BALANCE.buffet.max_range).length : 0);
}
export function becomeHostile(s, who) {
    if (!isLiving(who) || isProtectedPlayer(who))
        return;
    const fresh = !s.target;
    s.target = who;
    s.lastTargetSeen = now();
    s.chaseBest = 1e9;
    s.chaseBestTick = now();
    if (!s.enraged && dist(who.location, s.entity.location) > TR.danger_radius - 1) {
        s.enraged = true;
        event(s, "dod:enrage");
    }
    if (s.idle?.kind === "rest")
        startRise(s);
    else
        stopIdle(s);
    if (fresh && s.flight === "ground" && !s.run)
        s.combatRoarPending = true;
}
function calmDown(s) {
    s.target = undefined;
    s.combatRoarPending = false;
    if (s.enraged) {
        s.enraged = false;
        event(s, "dod:calm");
    }
}
function updateRunFlag(s) {
    const tg = s.target;
    const run = !!tg && isLiving(tg) && s.flight === "ground" && !s.locked && hdist(tg.location, s.entity.location) > 8;
    setProp(s, "dod:run", run);
}
// ------------------------------------------------------------------------------------------------ combat
function combat(s, target) {
    const pos = s.entity.location;
    const t = now();
    const d = hdist(pos, target.location);
    const dy = target.location.y - pos.y;
    if (s.flight === "ground") {
        if (s.combatRoarPending && t - s.lastCombatRoar >= sec(BALANCE.roar.combat_roar_cooldown) && d > 5) {
            s.combatRoarPending = false;
            s.lastCombatRoar = t;
            s.queue = ["roar"];
            startAction(s, "alert", target); // alert -> roar flows into the fight
            return;
        }
        s.combatRoarPending = false;
        if (d > 9) {
            if (d < s.chaseBest - 1) {
                s.chaseBest = d;
                s.chaseBestTick = t;
            }
        }
        else {
            s.chaseBest = d;
            s.chaseBestTick = t;
        }
        const stuck = t - s.chaseBestTick > sec(8);
        if ((dy > BALANCE.flight.takeoff_when_target_above && d < 32) || stuck) {
            if (canTakeOff(s)) {
                startTakeoff(s, "combat");
                s.chaseBestTick = t;
                return;
            }
            s.chaseBestTick = t;
        }
        const b = bearing(pos, s.yaw, target.location);
        // pressed against the chest: back off a couple of steps to make room for the jaws
        if (d < 4 && b < 60 && t >= s.nextStepBack && Math.random() < 0.35) {
            s.nextStepBack = t + sec(7);
            startStepBack(s);
            return;
        }
        const k = chooseAttack(s, target, nearCountCache.get(s.id) ?? 0);
        if (k) {
            s.turnTicks = 0;
            if (k === "fire" && d > 12 && Math.random() < 0.3 && canTakeOff(s)) {
                startTakeoff(s, "combat");
                return;
            }
            startAttack(s, k);
            return;
        }
        // close but not facing it and nothing fits: turn in place toward it (the client plays turn_left/right)
        if (d < 12 && b > 50 && s.turnTicks < 40) {
            lock(s);
            s.turnTicks++;
            face(s, turnToward(s.yaw, yawTo(pos, target.location), 3.5), 0);
            return;
        }
        if (s.turnTicks > 0) {
            s.turnTicks = b > 50 && s.turnTicks >= 40 ? -60 : 0; // give the walking AI a go before turning again
            unlock(s);
        }
        else if (s.turnTicks < 0) {
            s.turnTicks++;
        }
        return;
    }
    if (s.flight === "fly" || s.flight === "glide") {
        if (s.landingGoal)
            return;
        const k = chooseAttack(s, target, 0);
        if (k)
            startAttack(s, k);
    }
}
// ------------------------------------------------------------------------------------------------ living behaviour
const IDLE_WEIGHTS = [
    ["look_left", 14], ["look_right", 14], ["sniff", 13], ["scratch", 10], ["tail_sway", 12], ["wing_adjust", 10],
    ["stretch", 8], ["yawn", 8], ["rest", 7],
];
function idle(s) {
    const t = now();
    if (t < s.nextIdle)
        return;
    const I = BALANCE.idle;
    s.nextIdle = t + sec(I.action_interval_min + Math.random() * (I.action_interval_max - I.action_interval_min));
    if (Math.random() < BALANCE.flight.patrol_flight_chance && canTakeOff(s)) {
        startTakeoff(s, "patrol");
        return;
    }
    const quiet = players(s, 40).length === 0;
    const options = IDLE_WEIGHTS.filter(([k]) => k !== "rest" || (quiet && t - s.restSince > sec(90)));
    let sum = 0;
    for (const [, w] of options)
        sum += w;
    let r = Math.random() * sum;
    for (const [k, w] of options) {
        r -= w;
        if (r <= 0) {
            startIdle(s, k);
            return;
        }
    }
}
export function startIdle(s, kind) {
    lock(s);
    const length = kind === "rest" ? IDLE_TICKS.rest + sec(20 + Math.random() * 25) : IDLE_TICKS[kind] ?? 40;
    s.idle = { kind, tick: 0, length };
    if (kind === "rest")
        s.restSince = now();
    setIdle(s, kind);
}
function startRise(s) {
    if (s.idle?.kind !== "rest")
        return;
    s.idle = { kind: "rise", tick: 0, length: IDLE_TICKS.rise };
    setIdle(s, "rise");
}
/** Interrupt a living behaviour (a resting dragon must get up first). */
function stopIdle(s) {
    if (!s.idle)
        return;
    if (s.idle.kind === "rest") {
        startRise(s);
        return;
    }
    if (s.idle.kind === "rise")
        return;
    s.idle = undefined;
    setIdle(s, "none");
    unlock(s);
}
function tickIdle(s) {
    const r = s.idle;
    if (!r)
        return;
    r.tick++;
    if (r.tick < r.length)
        return;
    if (r.kind === "rest") {
        startRise(s);
        return;
    }
    s.idle = undefined;
    setIdle(s, "none");
    s.gapUntil = now() + sec(0.6);
    unlock(s);
}
// ------------------------------------------------------------------------------------------------ death
/** Called (deferred) when a hit would kill the dragon: play the death animation, then really die. */
export function beginDying(s) {
    if (s.dying)
        return;
    s.dying = true;
    s.dyingTick = now();
    s.run = undefined;
    s.idle = undefined;
    s.queue = [];
    s.target = undefined;
    s.landingGoal = undefined;
    event(s, "dod:dying");
    s.inAir = false;
    s.locked = true;
    setFlight(s, "ground");
    setProp(s, "dod:aim", 0);
    setProp(s, "dod:run", false);
    setIdle(s, "none");
    setAction(s, "death");
    safe(() => s.entity.clearVelocity());
}
function tickDying(s) {
    if (now() - s.dyingTick >= ACTION_TICKS.death && !s.allowKill) {
        s.allowKill = true;
        safe(() => s.entity.kill());
    }
}
export { unlock };
