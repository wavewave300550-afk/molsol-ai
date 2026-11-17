import { BALANCE } from "./balance.js";
import { ACTION_TICKS, event, face, isLiving, lock, now, safe, sec, setFlight, unlock } from "./dragon.js";
import { rayClear } from "./combat.js";
import { add, clamp, hdist, mul, turnToward, v3, yawDir, yawTo } from "./vec.js";
/**
 * Script-steered flight.  Phases (synced to the client as dod:flight):
 *   takeoff (crouch, leap at 0.55 s, climb)  ->  fly / glide  ->  landing (descend, touch down, fold)
 * The dragon is in the dod:air component group (no gravity, movement locked) only between the leap
 * and the touch-down.  Air time is capped twice (max_air_time -> lands, hard_air_limit -> drops),
 * and a reload always puts it back on the ground, so it can never stay stuck in the air.
 */
const FL = BALANCE.flight;
const LEAP_TICK = ACTION_TICKS.pre_takeoff; // crouch/anticipation length (0.55 s)
const LAUNCH_TICKS = ACTION_TICKS.takeoff - LEAP_TICK; // leap + climbing strokes (1.05 s)
const TOUCHDOWN_TICKS = ACTION_TICKS.touchdown; // landing impact + wing fold (1.4 s)
export function groundY(s, at, maxDown = 48) {
    const hit = safe(() => s.entity.dimension.getBlockFromRay(at, v3(0, -1, 0), {
        maxDistance: maxDown, includeLiquidBlocks: true, includePassableBlocks: false,
    }));
    return hit ? hit.block.location.y + 1 : undefined;
}
/** Enough open sky above and not swimming. */
export function canTakeOff(s) {
    const e = s.entity;
    if (s.dying || s.run || s.flight !== "ground" || e.isInWater || now() < s.nextTakeoff)
        return false;
    const top = add(e.location, v3(0, 4, 0));
    return rayClear(s, top, v3(0, 1, 0), 10) >= 10;
}
export function startTakeoff(s, reason) {
    lock(s);
    s.airReason = reason;
    s.airFires = 0;
    if (reason === "patrol")
        s.patrolUntil = now() + sec(12 + Math.random() * 8);
    setFlight(s, "takeoff");
}
export function beginLanding(s, near) {
    const pos = s.entity.location;
    let goal;
    if (near) {
        // touch down a little short of `near`, on the side the dragon is coming from
        const d = hdist(pos, near);
        const k = d > 9 ? (d - 9) / d : 0;
        goal = v3(pos.x + (near.x - pos.x) * k, near.y, pos.z + (near.z - pos.z) * k);
    }
    else {
        goal = add(pos, mul(yawDir(s.yaw), 8));
    }
    const gy = groundY(s, v3(goal.x, Math.max(pos.y, goal.y) + 2, goal.z), 80);
    s.landingGoal = v3(goal.x, gy ?? pos.y - 10, goal.z);
    setFlight(s, "glide");
    s.glideSince = now();
}
/** Emergency: switch gravity back on right where it is. */
export function forceGround(s) {
    s.nextTakeoff = now() + sec(10);
    event(s, "dod:to_ground");
    s.inAir = false;
    s.landingGoal = undefined;
    setFlight(s, "ground");
    unlock(s);
}
function applyVelocity(s, vel) {
    safe(() => {
        s.entity.clearVelocity();
        s.entity.applyImpulse(vel);
    });
}
export function tickFlight(s) {
    const e = s.entity;
    s.flightPhaseTick++;
    const t = s.flightPhaseTick;
    const pos = e.location;
    if (s.flight === "takeoff") {
        // pre-takeoff crouch on the ground; the leap happens exactly when the client starts "launch"
        if (t >= LEAP_TICK) {
            event(s, "dod:to_air");
            s.inAir = true;
            s.locked = true;
            s.airSince = now();
            setFlight(s, "launch");
        }
        return;
    }
    if (s.flight === "launch") {
        const k = Math.min(1, t / LAUNCH_TICKS);
        if (isLiving(s.target))
            face(s, turnToward(s.yaw, yawTo(pos, s.target.location), 3), 0);
        applyVelocity(s, add(mul(yawDir(s.yaw), 0.05 + 0.25 * k), v3(0, 0.62 - 0.32 * k, 0)));
        if (t >= LAUNCH_TICKS)
            setFlight(s, "fly");
        return;
    }
    if (s.flight === "landing") {
        // final approach (flare); on contact gravity comes back and the touch-down animation plays
        const gy = groundY(s, add(pos, v3(0, 1, 0)), 16);
        const h = gy === undefined ? 99 : pos.y - gy;
        if (h < 0.4 || e.isOnGround || t > 60) {
            event(s, "dod:to_ground");
            s.inAir = false;
            applyVelocity(s, v3(0, -0.1, 0));
            setFlight(s, "touchdown");
        }
        else {
            applyVelocity(s, add(mul(yawDir(s.yaw), 0.1), v3(0, -clamp(h * 0.1, 0.08, 0.24), 0)));
        }
        return;
    }
    if (s.flight === "touchdown") {
        if (t >= TOUCHDOWN_TICKS) {
            s.landingGoal = undefined;
            setFlight(s, "ground");
            s.airFires = 0;
            s.nextTakeoff = now() + sec(10); // no yo-yo: stay on the ground for a while after landing
            unlock(s);
        }
        return;
    }
    if (s.flight !== "fly" && s.flight !== "glide")
        return;
    const airTime = now() - s.airSince;
    if (airTime > sec(FL.hard_air_limit)) {
        forceGround(s);
        return;
    }
    // ---- decide where to go
    const busy = s.run !== undefined;
    const target = isLiving(s.target) ? s.target : undefined;
    if (!busy && !s.landingGoal) {
        const tired = airTime > sec(FL.max_air_time);
        if (tired || (s.airReason === "combat" && !target))
            beginLanding(s, target?.location);
        else if (s.airReason === "combat" && target && s.airFires >= FL.air_fire_attacks_before_landing &&
            now() >= s.ready.fire - sec(BALANCE.fire.cooldown * 0.5))
            beginLanding(s, target.location);
        else if (s.airReason === "patrol" && now() > s.patrolUntil)
            beginLanding(s);
    }
    let goal;
    if (s.landingGoal) {
        goal = add(s.landingGoal, v3(0, 3, 0));
    }
    else if (target) {
        s.orbitAngle += 2.2;
        const a = (s.orbitAngle * Math.PI) / 180;
        goal = add(target.location, v3(Math.cos(a) * FL.orbit_radius, FL.cruise_height - 2, Math.sin(a) * FL.orbit_radius));
    }
    else {
        s.orbitAngle += 1.4;
        const a = (s.orbitAngle * Math.PI) / 180;
        const gy = groundY(s, v3(s.home.x, pos.y + 4, s.home.z), 80) ?? s.home.y;
        goal = v3(s.home.x + Math.cos(a) * 18, gy + FL.cruise_height, s.home.z + Math.sin(a) * 18);
    }
    // ---- steer
    const fire = s.run && (s.run.kind === "fire_charge" || s.run.kind === "fire_breath");
    if (!fire) {
        const yawGoal = yawTo(pos, goal);
        s.yaw = turnToward(s.yaw, yawGoal, FL.turn_rate_deg_per_tick);
    }
    let vy = clamp((goal.y - pos.y) * 0.07, -0.32, 0.3);
    let speed = s.flight === "glide" ? FL.glide_speed : FL.fly_speed;
    if (fire)
        speed = 0.08;
    else if (busy)
        speed *= 0.5;
    if (now() % 2 === 0 || s.landingGoal) {
        const gy = groundY(s, add(pos, v3(0, 1, 0)), 24);
        const h = gy === undefined ? 99 : pos.y - gy;
        if (s.landingGoal && (h < 3.5 || hdist(pos, s.landingGoal) < 3)) {
            setFlight(s, "landing");
            return;
        }
        if (!s.landingGoal && h < 5)
            vy = Math.max(vy, 0.25);
        const ahead = rayClear(s, add(pos, v3(0, 2.5, 0)), yawDir(s.yaw), 7);
        if (ahead < 7) {
            vy = 0.4;
            speed *= 0.4;
        }
    }
    if (s.landingGoal)
        speed *= clamp(hdist(pos, s.landingGoal) / 14, 0.35, 1);
    // ---- flap or glide (with hysteresis so the animation never flickers)
    if (now() - s.glideSince > 30 && !fire) {
        const wantGlide = vy < -0.1 || (s.landingGoal !== undefined);
        if (wantGlide && s.flight === "fly") {
            setFlight(s, "glide");
            s.glideSince = now();
        }
        else if (!wantGlide && (vy > 0.06 || busy) && s.flight === "glide") {
            setFlight(s, "fly");
            s.glideSince = now();
        }
    }
    if (fire && s.flight === "glide")
        setFlight(s, "fly");
    if (!fire)
        face(s, s.yaw, 0);
    applyVelocity(s, add(mul(yawDir(s.yaw), speed), v3(0, vy, 0)));
}
