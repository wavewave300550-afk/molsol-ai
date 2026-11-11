import {
  Dimension,
  Entity,
  EntityDamageCause,
  EntityTameableComponent,
  EntityTypeFamilyComponent,
  Player,
  system,
  world,
} from "@minecraft/server";
import { rules } from "../config";
import { V3, dist, flatNorm, len, mul, norm, segDist, sub } from "./vec";
import { log } from "./log";

/** Families that are always valid enemies (vanilla 1.26.63 families; hoglin/dragon are not "monster"). */
const ENEMY_FAMILIES = ["monster", "dragon", "hoglin_adult"];
/** Never targeted (unless they attacked the caster recently, see aggressors). */
const PROTECTED_FAMILIES = ["villager", "wandering_trader", "irongolem", "snowgolem", "copper_golem", "allay", "npc", "tripodcamera"];
/** Never targeted at all. */
const IGNORED_FAMILIES = ["inanimate", "projectile", "grimoire_fx", "lightning", "armor_stand"];
const IGNORED_TYPES = new Set([
  "minecraft:item",
  "minecraft:xp_orb",
  "minecraft:area_effect_cloud",
  "minecraft:ender_crystal",
  "minecraft:eye_of_ender_signal",
  "minecraft:ominous_item_spawner",
  "minecraft:agent",
  "minecraft:painting",
  "minecraft:leash_knot",
  "minecraft:falling_block",
  "minecraft:tnt",
]);

export const FX_FAMILY = "grimoire_fx";
export const SUMMON_FAMILY = "grimoire_summon";
export const OWNER_PROP = "grimoire:owner";

/** Entities that recently attacked a player become valid targets for that player's spells. */
const aggressors = new Map<string, Map<string, number>>();
const AGGRO_TICKS = 20 * 20;

export function noteAggressor(victim: Entity, attacker: Entity | undefined): void {
  if (!attacker || attacker.id === victim.id) return;
  const ownerId = victim.typeId === "minecraft:player" ? victim.id : ownerOf(victim);
  if (!ownerId) return;
  let m = aggressors.get(ownerId);
  if (!m) aggressors.set(ownerId, (m = new Map()));
  m.set(attacker.id, system.currentTick + AGGRO_TICKS);
}

function isAggressor(casterId: string, e: Entity): boolean {
  const until = aggressors.get(casterId)?.get(e.id);
  return until !== undefined && until > system.currentTick;
}

export function pruneAggressors(): void {
  const now = system.currentTick;
  for (const [k, m] of aggressors) {
    for (const [id, until] of m) if (until <= now) m.delete(id);
    if (m.size === 0) aggressors.delete(k);
  }
}

export function ownerOf(e: Entity): string | undefined {
  try {
    const o = e.getDynamicProperty(OWNER_PROP);
    return typeof o === "string" ? o : undefined;
  } catch {
    return undefined;
  }
}

function families(e: Entity): EntityTypeFamilyComponent | undefined {
  return e.getComponent(EntityTypeFamilyComponent.componentId) as EntityTypeFamilyComponent | undefined;
}

function hasAnyFamily(f: EntityTypeFamilyComponent | undefined, list: string[]): boolean {
  if (!f) return false;
  for (const x of list) if (f.hasTypeFamily(x)) return true;
  return false;
}

function teamOf(p: Entity): string | undefined {
  for (const t of p.getTags()) if (t.startsWith("grimoire_team:")) return t;
  return undefined;
}

export type Relation = "self" | "ally" | "enemy" | "neutral" | "ignore";

/** The single source of truth for "may this caster's spell hurt that entity?". */
export function relation(caster: Player | string, e: Entity): Relation {
  const casterId = typeof caster === "string" ? caster : caster.id;
  if (!e.isValid) return "ignore";
  if (e.id === casterId) return "self";
  if (IGNORED_TYPES.has(e.typeId)) return "ignore";
  const fam = families(e);
  if (hasAnyFamily(fam, IGNORED_FAMILIES)) return "ignore";
  const r = rules();
  if (e.typeId === "minecraft:player") {
    if (!r.pvp) return "ally";
    if (!r.friendlyFire && typeof caster !== "string") {
      const t = teamOf(caster);
      if (t && e.hasTag(t)) return "ally";
    }
    return "enemy";
  }
  if (fam?.hasTypeFamily(SUMMON_FAMILY)) {
    const o = ownerOf(e);
    if (o === casterId) return "ally";
    return r.pvp ? "enemy" : "ally";
  }
  if (isAggressor(casterId, e)) return "enemy";
  if (hasAnyFamily(fam, ENEMY_FAMILIES)) return "enemy";
  if (hasAnyFamily(fam, PROTECTED_FAMILIES)) return "neutral";
  const tame = e.getComponent(EntityTameableComponent.componentId) as EntityTameableComponent | undefined;
  if (tame?.isTamed) return tame.tamedToPlayerId === casterId ? "ally" : "neutral";
  if (e.nameTag && e.nameTag.length > 0) return "neutral"; // named pets / mobs are protected
  if (!e.getComponent("minecraft:health")) return "ignore";
  return r.harmPassiveMobs ? "enemy" : "neutral";
}

export const isEnemy = (caster: Player | string, e: Entity): boolean => relation(caster, e) === "enemy";
export const isAllyOrSelf = (caster: Player | string, e: Entity): boolean => {
  const rel = relation(caster, e);
  return rel === "self" || rel === "ally";
};

/** Living entities around a point. Uses a single engine query; never scans the whole world. */
export function livingNear(dim: Dimension, center: V3, radius: number): Entity[] {
  try {
    return dim.getEntities({ location: center, maxDistance: radius, excludeFamilies: IGNORED_FAMILIES, excludeTypes: [...IGNORED_TYPES] });
  } catch {
    return [];
  }
}

export function enemiesNear(caster: Player | string, dim: Dimension, center: V3, radius: number): Entity[] {
  return livingNear(dim, center, radius).filter((e) => isEnemy(caster, e));
}

/** Entities whose body comes within `radius` of the segment a→b. */
export function enemiesAlong(caster: Player | string, dim: Dimension, a: V3, b: V3, radius: number): Entity[] {
  const mid = mul({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z }, 0.5);
  const reach = dist(a, b) / 2 + radius + 2;
  return enemiesNear(caster, dim, mid, reach).filter((e) => {
    const c = bodyCenter(e);
    return segDist(c, a, b).d <= radius + bodyRadius(e);
  });
}

export function bodyCenter(e: Entity): V3 {
  const l = e.location;
  return { x: l.x, y: l.y + bodyHeight(e) * 0.5, z: l.z };
}

const SIZE_CACHE = new Map<string, [number, number]>();
export function bodyHeight(e: Entity): number {
  return entitySize(e)[1];
}
export function bodyRadius(e: Entity): number {
  return entitySize(e)[0] * 0.5;
}
function entitySize(e: Entity): [number, number] {
  const c = SIZE_CACHE.get(e.typeId);
  if (c) return c;
  // Script API does not expose collision boxes; use head height as a robust proxy.
  let h = 1.8;
  try {
    h = Math.max(0.3, (e.getHeadLocation().y - e.location.y) * 1.12);
  } catch {
    /* keep default */
  }
  const w = Math.min(4, Math.max(0.4, h * 0.45));
  const r: [number, number] = [w, h];
  SIZE_CACHE.set(e.typeId, r);
  return r;
}

// ---------------------------------------------------------------------------------------------
// Damage bus: respects Bedrock's ~10 tick hurt cooldown by merging rapid hits into one
// application, so barrages deliver their full intended damage instead of being swallowed.
// ---------------------------------------------------------------------------------------------

export type DamageKind = "spell" | "reflect" | "transfer";

interface Pending {
  target: Entity;
  casterId: string;
  amount: number;
  kind: DamageKind;
  due: number;
}

const lastApplied = new Map<string, number>();
const pending = new Map<string, Pending>();
const HURT_COOLDOWN = 10;

/** Ids of entities currently receiving damage from this add-on (used by recursion guards). */
export const damageInFlight = new Map<string, DamageKind>();

export interface HitOptions {
  kind?: DamageKind;
  /** Bypass the merge window (e.g. a single huge finishing blow). */
  immediate?: boolean;
}

function scaleFor(target: Entity): number {
  const r = rules();
  return target.typeId === "minecraft:player" ? r.damagePvP : r.damagePvE;
}

export function hit(caster: Player | string, target: Entity, amount: number, opts: HitOptions = {}): void {
  if (!target.isValid || amount <= 0) return;
  const casterId = typeof caster === "string" ? caster : caster.id;
  const kind = opts.kind ?? "spell";
  const now = system.currentTick;
  const last = lastApplied.get(target.id) ?? -999;
  const p = pending.get(target.id);
  if (p) {
    p.amount += amount;
    return;
  }
  if (opts.immediate || now - last >= HURT_COOLDOWN) {
    apply(target, casterId, amount, kind);
  } else {
    pending.set(target.id, { target, casterId, amount, kind, due: last + HURT_COOLDOWN });
  }
}

function causeFor(kind: DamageKind): EntityDamageCause {
  return kind === "reflect" ? EntityDamageCause.thorns : EntityDamageCause.magic;
}

function apply(target: Entity, casterId: string, amount: number, kind: DamageKind): void {
  if (!target.isValid) return;
  const scaled = amount * scaleFor(target);
  if (scaled <= 0) return;
  const caster = world.getEntity(casterId);
  lastApplied.set(target.id, system.currentTick);
  damageInFlight.set(target.id, kind);
  try {
    target.applyDamage(scaled, { cause: causeFor(kind), damagingEntity: caster?.isValid ? caster : undefined });
  } catch (e) {
    log.debug("applyDamage failed", String(e));
  } finally {
    damageInFlight.delete(target.id);
  }
}

export function flushDamage(tick: number): void {
  for (const [id, p] of pending) {
    if (tick >= p.due) {
      pending.delete(id);
      apply(p.target, p.casterId, p.amount, p.kind);
    }
  }
  if (tick % 200 === 0) {
    for (const [id, t] of lastApplied) if (tick - t > 100) lastApplied.delete(id);
  }
}

// ---------------------------------------------------------------------------------------------
// Movement effects on targets
// ---------------------------------------------------------------------------------------------

/** Push an entity: horizontal strength along `dir` (XZ) plus vertical strength. */
export function push(e: Entity, dir: V3, horizontal: number, vertical: number): void {
  if (!e.isValid) return;
  const d = flatNorm(dir);
  try {
    e.applyKnockback({ x: d.x * horizontal, z: d.z * horizontal }, vertical);
  } catch {
    /* some entities (e.g. riding players) reject knockback */
  }
}

/** Pull toward a point with a speed proportional to distance (capped). */
export function pullToward(e: Entity, point: V3, strength: number): void {
  const d = sub(point, e.location);
  const l = len(d);
  if (l < 0.6) return;
  const n = norm(d);
  push(e, n, Math.min(strength, l * 0.25), Math.max(-0.1, Math.min(0.25, n.y * strength)));
}

export function effect(e: Entity, id: string, ticks: number, amplifier = 0, particles = false): void {
  if (!e.isValid) return;
  try {
    e.addEffect(id, ticks, { amplifier, showParticles: particles });
  } catch {
    /* entity immune or invalid effect for this entity type */
  }
}

/**
 * Hard immobilisation used by binding/freeze spells: strong slowness + weakness. Callers that
 * need an exact anchor additionally pin the target with `pin()` every tick.
 */
export function immobilize(e: Entity, ticks: number): void {
  effect(e, "slowness", ticks, 7);
  effect(e, "mining_fatigue", ticks, 2);
  effect(e, "weakness", ticks, 1);
}

/** Keep an entity at an anchor (bounded correction, never into blocks: the anchor is its own earlier position). */
export function pin(e: Entity, anchor: V3, tolerance = 0.35): void {
  if (!e.isValid) return;
  const l = e.location;
  const dx = l.x - anchor.x, dz = l.z - anchor.z;
  if (dx * dx + dz * dz > tolerance * tolerance || l.y > anchor.y + 0.8) {
    try {
      e.teleport({ x: anchor.x, y: Math.min(l.y, anchor.y + 0.1), z: anchor.z }, { keepVelocity: false });
    } catch {
      /* chunk unloading etc. */
    }
  }
}

export function release(e: Entity): void {
  if (!e.isValid) return;
  for (const id of ["slowness", "mining_fatigue", "weakness"]) {
    try {
      e.removeEffect(id);
    } catch {
      /* not present */
    }
  }
}
