import { Entity, Vector3, system } from "@minecraft/server";
import { BALANCE } from "./balance.js";
import { ANIM_LENGTH } from "./offsets.js";

export const DRAGON_ID = "dod:red_dragon";
export const DRAGON_FAMILY = "red_dragon";

export type Flight = "ground" | "takeoff" | "fly" | "glide" | "landing";
export type Action =
  | "none" | "roar" | "bite" | "claw" | "tail" | "buffet" | "fire_charge" | "fire_breath" | "look" | "stretch" | "death";
export type AttackKind = "bite" | "claw" | "tail" | "buffet" | "fire";

export const sec = (s: number): number => Math.round(s * 20);

/** Length (ticks) of the client animation that belongs to each action. */
export const ACTION_TICKS: Record<string, number> = {
  roar: sec(ANIM_LENGTH.roar),
  bite: sec(ANIM_LENGTH.bite),
  claw: sec(ANIM_LENGTH.claw),
  tail: sec(ANIM_LENGTH.tail_smash),
  buffet: sec(ANIM_LENGTH.wing_buffet),
  look: sec(ANIM_LENGTH.look_around),
  stretch: sec(ANIM_LENGTH.wing_stretch),
  death: sec(ANIM_LENGTH.death),
  takeoff: sec(ANIM_LENGTH.takeoff),
  landing: sec(ANIM_LENGTH.landing),
};

/** Damage frames inside the attack animations (seconds -> ticks). */
export const IMPACT_TICK: Record<string, number> = { bite: sec(0.45), claw: sec(0.55), tail: sec(0.72), buffet: sec(0.7) };

export interface ActionRun {
  kind: Action;
  tick: number; // ticks since start
  length: number;
  impactDone: boolean;
  /** fire breath only */
  fireYaw?: number;
  firePitch?: number;
}

export interface DragonState {
  id: string;
  entity: Entity;
  flight: Flight;
  inAir: boolean; // dod:air component group active
  locked: boolean; // dod:locked active
  enraged: boolean;
  run?: ActionRun;
  gapUntil: number;
  ready: Record<AttackKind, number>;
  target?: Entity;
  lastTargetSeen: number;
  warned: Map<string, number>;
  lastWarn: number;
  lastCombatRoar: number;
  combatRoarPending?: boolean;
  nextIdle: number;
  home: Vector3;
  // flight
  flightPhaseTick: number;
  airSince: number;
  airFires: number;
  airReason: "combat" | "patrol";
  patrolUntil: number;
  orbitAngle: number;
  yaw: number;
  pitch: number;
  glideSince: number;
  landingGoal?: Vector3;
  nextTakeoff: number;
  // chase / stuck detection
  chaseBest: number;
  chaseBestTick: number;
  // dying
  dying: boolean;
  dyingTick: number;
  allowKill: boolean;
  props: Record<string, string | number | boolean>;
  /** debug counters read by the smoke test */
  lastHits?: number;
  fireHits?: number;
}

export const dragons = new Map<string, DragonState>();

export function now(): number {
  return system.currentTick;
}

export function newState(e: Entity): DragonState {
  const t = now();
  const homeProp = safe(() => e.getDynamicProperty("dod:home"));
  const home = homeProp && typeof homeProp === "object" ? (homeProp as Vector3) : { ...e.location };
  if (!homeProp) safe(() => e.setDynamicProperty("dod:home", home));
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
  };
}

export function safe<T>(f: () => T): T | undefined {
  try {
    return f();
  } catch {
    return undefined;
  }
}

/** Set a synced entity property only when it changes (keeps network traffic low). */
export function setProp(s: DragonState, key: string, value: string | number | boolean): void {
  if (s.props[key] === value) return;
  s.props[key] = value;
  safe(() => s.entity.setProperty(key, value));
}

export function event(s: DragonState, name: string): void {
  safe(() => s.entity.triggerEvent(name));
}

export function lock(s: DragonState): void {
  if (!s.locked) {
    s.locked = true;
    event(s, "dod:lock");
  }
}

export function unlock(s: DragonState): void {
  if (s.locked && !s.inAir && !s.dying) {
    s.locked = false;
    event(s, "dod:unlock");
  }
}

export function setFlight(s: DragonState, f: Flight): void {
  s.flight = f;
  s.flightPhaseTick = 0;
  setProp(s, "dod:flight", f);
}

export function setAction(s: DragonState, a: Action): void {
  setProp(s, "dod:action", a);
}

export function face(s: DragonState, yaw: number, pitch = 0): void {
  s.yaw = yaw;
  s.pitch = pitch;
  safe(() => s.entity.setRotation({ x: pitch, y: yaw }));
}

export function isLiving(e: Entity | undefined): e is Entity {
  if (!e || !e.isValid) return false;
  const h = safe(() => e.getComponent("minecraft:health")) as { currentValue: number } | undefined;
  return !!h && h.currentValue > 0;
}
