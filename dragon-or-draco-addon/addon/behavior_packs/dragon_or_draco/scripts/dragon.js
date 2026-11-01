import { system } from "@minecraft/server";
import { BALANCE } from "./balance.js";
import { ANIM_LENGTH } from "./offsets.js";
export const DRAGON_ID = "dod:red_dragon";
export const DRAGON_FAMILY = "red_dragon";
export const sec = (s) => Math.round(s * 20);
/** Length (ticks) of the client animation that belongs to each action (read from the animation file). */
export const ACTION_TICKS = {
    alert: sec(ANIM_LENGTH.alert),
    roar: sec(ANIM_LENGTH.roar),
    bite: sec(ANIM_LENGTH.bite),
    claw: sec(ANIM_LENGTH.claw_swipe),
    tail: sec(ANIM_LENGTH.tail_smash),
    buffet: sec(ANIM_LENGTH.wing_buffet),
    step_back: sec(ANIM_LENGTH.step_backward),
    death: sec(ANIM_LENGTH.death),
    pre_takeoff: sec(ANIM_LENGTH.pre_takeoff),
    takeoff: sec(ANIM_LENGTH.pre_takeoff) + sec(ANIM_LENGTH.launch),
    touchdown: sec(ANIM_LENGTH.landing_impact),
};
/** Living-behaviour animations played between other activities (dod:idle). */
export const IDLE_TICKS = {
    look_left: sec(ANIM_LENGTH.idle_look_left),
    look_right: sec(ANIM_LENGTH.idle_look_right),
    sniff: sec(ANIM_LENGTH.idle_sniff),
    scratch: sec(ANIM_LENGTH.idle_ground_scratch),
    tail_sway: sec(ANIM_LENGTH.idle_tail_sway),
    wing_adjust: sec(ANIM_LENGTH.idle_wing_adjust),
    stretch: sec(ANIM_LENGTH.idle_stretch),
    yawn: sec(ANIM_LENGTH.idle_yawn),
    rest: sec(ANIM_LENGTH.rest_lower),
    rise: sec(ANIM_LENGTH.rest_rise),
};
/** Damage frames inside the attack animations (seconds -> ticks). */
export const IMPACT_TICK = { bite: sec(0.45), claw: sec(0.55), tail: sec(0.72), buffet: sec(0.7) };
export const dragons = new Map();
export function now() {
    return system.currentTick;
}
export function newState(e) {
    const t = now();
    const homeProp = safe(() => e.getDynamicProperty("dod:home"));
    const home = homeProp && typeof homeProp === "object" ? homeProp : { ...e.location };
    if (!homeProp)
        safe(() => e.setDynamicProperty("dod:home", home));
    const rot = safe(() => e.getRotation()) ?? { x: 0, y: 0 };
    return {
        id: e.id,
        entity: e,
        flight: "ground",
        inAir: false,
        locked: false,
        enraged: false,
        gapUntil: t + 20,
        ready: { bite: t, claw: t, tail: t, buffet: t, fire: t + sec(4) },
        lastTargetSeen: 0,
        warned: new Map(),
        lastWarn: -99999,
        lastCombatRoar: -99999,
        nextIdle: t + sec(BALANCE.idle.action_interval_min),
        home,
        flightPhaseTick: 0,
        airSince: 0,
        airFires: 0,
        airReason: "patrol",
        patrolUntil: 0,
        orbitAngle: Math.random() * 360,
        yaw: rot.y,
        pitch: 0,
        glideSince: 0,
        nextTakeoff: t + sec(3),
        chaseBest: 1e9,
        chaseBestTick: t,
        dying: false,
        dyingTick: 0,
        allowKill: false,
        props: {},
        queue: [],
        turnTicks: 0,
        nextStepBack: t,
        restSince: 0,
    };
}
export function safe(f) {
    try {
        return f();
    }
    catch {
        return undefined;
    }
}
/** Set a synced entity property only when it changes (keeps network traffic low). */
export function setProp(s, key, value) {
    if (s.props[key] === value)
        return;
    s.props[key] = value;
    safe(() => s.entity.setProperty(key, value));
}
export function event(s, name) {
    safe(() => s.entity.triggerEvent(name));
}
export function lock(s) {
    if (!s.locked) {
        s.locked = true;
        event(s, "dod:lock");
    }
}
export function unlock(s) {
    if (s.locked && !s.inAir && !s.dying) {
        s.locked = false;
        event(s, "dod:unlock");
    }
}
export function setFlight(s, f) {
    s.flight = f;
    s.flightPhaseTick = 0;
    setProp(s, "dod:flight", f);
}
export function setAction(s, a) {
    setProp(s, "dod:action", a);
}
export function setIdle(s, i) {
    setProp(s, "dod:idle", i);
}
export function face(s, yaw, pitch = 0) {
    s.yaw = yaw;
    s.pitch = pitch;
    safe(() => s.entity.setRotation({ x: pitch, y: yaw }));
}
export function isLiving(e) {
    if (!e || !e.isValid)
        return false;
    const h = safe(() => e.getComponent("minecraft:health"));
    return !!h && h.currentValue > 0;
}
