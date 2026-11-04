import { Entity, EntityDamageCause, GameMode, Player, system, Vector3 } from "@minecraft/server";
import { BALANCE } from "./balance.js";
import { Action, BOSS_ID, EDISON_ID } from "./spec.js";
import { add, angleDiff, clamp, localToWorld, turnToward, v3, yawTo } from "./vec.js";
import { LocalOffset } from "./offsets.js";

export const BOSS_FAMILY = "esb_boss";
export const EXCLUDE_FAMILIES = ["esb_boss", "esb_fx", "esb_projectile", "esb_construct", "inanimate"];
export const EXCLUDE_TYPES = ["minecraft:item", "minecraft:xp_orb", "minecraft:arrow", "minecraft:snowball",
  "minecraft:armor_stand", "minecraft:painting", "minecraft:leash_knot", "minecraft:boat", "minecraft:chest_boat",
  "minecraft:minecart", "minecraft:ender_pearl", "minecraft:fireball", "minecraft:small_fireball"];

export type Ability = "gear_volley" | "quake" | "vitruvian" | "dive";
export type EdisonAbility = "bulb_toss" | "vanish" | "overload" | "chair";
export type BossKind = "da_vinci" | "edison";

export const sec = (s: number): number => Math.round(s * 20);
export const now = (): number => system.currentTick;

export function safe<T>(fn: () => T): T | undefined {
  try {
    return fn();
  } catch {
    return undefined;
  }
}

/** A running scripted action. `tick` counts from 0; moments fire once when reached. */
export interface Run {
  kind: string;
  tick: number;
  length: number;
  fired: Set<string>;
}

export interface Dive {
  stage: "rise" | "hover" | "strike";
  stageTick: number;
  from: Vector3;
  peak: Vector3;
  landing: Vector3;
  lockAt: number; // hover tick from which the landing point no longer follows the target
  hoverTicks: number;
  marker?: Entity;
}

/** Edison's electric chair in play: armed under a player, then locked with the player strapped in. */
export interface Chair {
  entity: Entity;
  victim: Entity;
  locked: boolean;
  until: number;
  seat: { x: number; y: number; z: number };
}

export interface BossState {
  kind: BossKind;
  entity: Entity;
  id: string;
  phase: 1 | 2;
  run?: Run;
  target?: Entity;
  ready: Record<string, number>;
  gapUntil: number;
  nextDecision: number;
  locked: boolean;
  inAir: boolean;
  dying: boolean;
  dyingTick: number;
  allowKill: boolean;
  invulnerable: boolean;
  killer?: Entity;
  nextFlourish: number;
  yaw: number;
  props: Record<string, string | number | boolean>;
  sigil?: Entity;
  dive?: Dive;
  // Edison
  dynamo?: Entity;
  chair?: Chair;
  hidden: boolean;
  blinkTo?: Vector3;
  blinksLeft: number;
  stunUntil: number;
  hop?: { from: Vector3; to: Vector3 };
}

export const bosses = new Map<string, BossState>();

export function newState(e: Entity, kind: BossKind = "da_vinci"): BossState {
  const t = now();
  return {
    kind,
    entity: e,
    id: e.id,
    phase: 1,
    ready: kind === "edison"
      ? { bulb_toss: t + sec(2), vanish: t + sec(4), overload: t + sec(8), chair: t + sec(6) }
      : { gear_volley: t + sec(3), quake: t + sec(2), vitruvian: t + sec(8), dive: t + sec(4) },
    gapUntil: t,
    nextDecision: t,
    locked: false,
    inAir: false,
    dying: false,
    dyingTick: 0,
    allowKill: false,
    invulnerable: false,
    nextFlourish: t + sec(BALANCE.flourish.every_min),
    yaw: safe(() => e.getRotation().y) ?? 0,
    props: {},
    hidden: false,
    blinksLeft: 0,
    stunUntil: 0,
  };
}

// ------------------------------------------------------------------------------------------ properties & events

export function setProp(s: BossState, key: string, value: string | number | boolean): void {
  if (s.props[key] === value) return;
  s.props[key] = value;
  safe(() => s.entity.setProperty(key, value));
}

export function event(s: BossState, name: string): void {
  safe(() => s.entity.triggerEvent(name));
}

export function setAction(s: BossState, a: Action | string): void {
  setProp(s, "esb:action", a);
}

export function lock(s: BossState): void {
  if (!s.locked) {
    s.locked = true;
    event(s, "esb:lock");
  }
}

/** Back to walking / melee. Phase 2 uses the faster group. Never while airborne or dying. */
export function unlock(s: BossState): void {
  if (s.locked && !s.inAir && !s.dying) {
    s.locked = false;
    event(s, s.phase === 2 ? "esb:unlock_fast" : "esb:unlock");
  }
}

export function face(s: BossState, yaw: number): void {
  s.yaw = yaw;
  safe(() => s.entity.setRotation({ x: 0, y: yaw }));
}

/** Turn toward a point by at most `step` degrees this tick. */
export function turnTo(s: BossState, p: Vector3, step: number): void {
  s.yaw = safe(() => s.entity.getRotation().y) ?? s.yaw;
  const goal = yawTo(s.entity.location, p);
  if (Math.abs(angleDiff(s.yaw, goal)) < 0.5) return;
  face(s, turnToward(s.yaw, goal, step));
}

export function at(s: BossState, o: LocalOffset): Vector3 {
  return localToWorld(s.entity.location, s.yaw, o.fwd, o.up, o.left);
}

// ------------------------------------------------------------------------------------------ queries

export function health(e: Entity): { currentValue: number; effectiveMax: number } | undefined {
  return safe(() => e.getComponent("minecraft:health")) as { currentValue: number; effectiveMax: number } | undefined;
}

export function hpFrac(s: BossState): number {
  const h = health(s.entity);
  return h ? h.currentValue / Math.max(1, h.effectiveMax) : 1;
}

export function isLiving(e: Entity | undefined): e is Entity {
  if (!e || !e.isValid) return false;
  const h = health(e);
  return !!h && h.currentValue > 0;
}

export function isProtectedPlayer(t: Entity): boolean {
  if (t.typeId !== "minecraft:player") return false;
  const gm = safe(() => (t as Player).getGameMode());
  return gm === GameMode.Creative || gm === GameMode.Spectator;
}

export const BOSS_IDS: string[] = [BOSS_ID, EDISON_ID];

export function isBoss(e: Entity | undefined): boolean {
  return !!e && BOSS_IDS.includes(e.typeId);
}

export function centerOf(t: Entity): Vector3 {
  return add(t.location, v3(0, t.typeId === "minecraft:player" ? 0.9 : 0.6, 0));
}

/** Living things the boss may hurt within a horizontal radius and a vertical band. */
export function victims(s: BossState, center: Vector3, radius: number, below = 2, above = 3): Entity[] {
  const list = safe(() => s.entity.dimension.getEntities({
    location: center, maxDistance: radius + above + 2, excludeFamilies: EXCLUDE_FAMILIES, excludeTypes: EXCLUDE_TYPES,
  })) ?? [];
  return list.filter((t) => {
    if (t.id === s.id || !isLiving(t) || isProtectedPlayer(t)) return false;
    const dx = t.location.x - center.x;
    const dz = t.location.z - center.z;
    const dy = t.location.y - center.y;
    return Math.sqrt(dx * dx + dz * dz) <= radius && dy >= -below && dy <= above;
  });
}

export function playersNear(s: BossState, radius: number): Player[] {
  const list = safe(() => s.entity.dimension.getPlayers({ location: s.entity.location, maxDistance: radius })) ?? [];
  return list.filter((p) => isLiving(p));
}

export function hurt(s: BossState, t: Entity, amount: number): boolean {
  return safe(() => t.applyDamage(amount, { cause: EntityDamageCause.entityAttack, damagingEntity: s.entity })) ?? false;
}

export function knockFrom(t: Entity, from: Vector3, strength: number, lift: number): void {
  const dx = t.location.x - from.x;
  const dz = t.location.z - from.z;
  const h = Math.sqrt(dx * dx + dz * dz) || 1;
  safe(() => t.applyKnockback({ x: (dx / h) * strength, z: (dz / h) * strength }, lift));
}

/** Y of the first solid block surface below `p` (searching `depth` blocks), or undefined. */
export function groundBelow(s: BossState, p: Vector3, depth = 24): number | undefined {
  const hit = safe(() => s.entity.dimension.getBlockFromRay(p, v3(0, -1, 0), {
    maxDistance: depth, includeLiquidBlocks: true, includePassableBlocks: false,
  }));
  return hit ? hit.block.location.y + 1 : undefined;
}

/** Free distance along a ray before a solid block (or maxD). */
export function rayClear(s: BossState, from: Vector3, dir: Vector3, maxD: number): number {
  const hit = safe(() => s.entity.dimension.getBlockFromRay(from, dir, {
    maxDistance: maxD, includeLiquidBlocks: false, includePassableBlocks: false,
  }));
  if (!hit) return maxD;
  const p = add(hit.block.location, hit.faceLocation);
  const d = { x: p.x - from.x, y: p.y - from.y, z: p.z - from.z };
  return clamp(Math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z), 0, maxD);
}

export function message(players: Player[], key: string, withArgs?: string[]): void {
  for (const p of players) safe(() => p.sendMessage({ rawtext: [{ translate: key, with: withArgs }] }));
}

export function actionBar(players: Player[], key: string): void {
  for (const p of players) safe(() => p.onScreenDisplay.setActionBar({ rawtext: [{ translate: key }] }));
}
