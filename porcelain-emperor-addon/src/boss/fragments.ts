/**
 * Fragments of the Emperor: edict tablets, porcelain shards and palace rubble.
 *
 * They are real entities moved kinematically by the script. "Every shard has
 * a fate": a fragment that lands embeds itself in the court and glows. Players
 * can shatter it (a few hits) for a burst of golden absorption. If they leave
 * it, the Emperor's Golden Repair pulls it back to heal (phases I-II) or, once
 * the Mandate is fractured (phase III), it rises as a Porcelain Courtier.
 */
import { Entity, ItemStack, Player, system, Vector3 } from "@minecraft/server";
import { Arena } from "../arena/arena.js";
import { DMG, ENT, FX, ITEM, PROP, SND } from "../config.js";
import { GOLD, particle, ringWave, sound, telegraph } from "../core/fx.js";
import { add, dist, distXZ, lerp, norm, scale, sub, v } from "../core/vec.js";

export type FragKind = "tablet" | "shard" | "rubble";
type State = "flight" | "slide" | "embedded" | "rise" | "orbit" | "hurl" | "pull" | "drift" | "ring";

export interface Frag {
  e: Entity;
  kind: FragKind;
  state: State;
  pos: Vector3;
  t: number;
  from?: Vector3;
  to?: Vector3;
  dur?: number;
  apex?: number;
  vel?: Vector3;
  angle?: number;
  radius?: number;
  height?: number;
  speed?: number;
  embeddedAt?: number;
  hit: Set<string>;
  damage: number;
  onArrive?: (f: Frag) => void;
}

export interface FightCtx {
  arena: Arena;
  players(): Player[];
  hurt(p: Player, amount: number, from?: Vector3, push?: number, lift?: number): void;
  phase(): number;
  bossPos(): Vector3 | undefined;
}

const frags = new Map<string, Frag>();
let ctx: FightCtx | undefined;
let courtiers: Entity[] = [];

export function initFragments(c: FightCtx): void {
  ctx = c;
}

function spawn(kind: FragKind, at: Vector3): Entity | undefined {
  if (!ctx) return undefined;
  const id = kind === "tablet" ? ENT.tablet : kind === "shard" ? ENT.shard : ENT.rubble;
  try {
    return ctx.arena.dim.spawnEntity(id, at);
  } catch (e) {
    console.warn(`[porcelain] could not spawn ${id}: ${e}`);
    return undefined;
  }
}

function register(e: Entity, kind: FragKind, state: State, pos: Vector3, damage: number): Frag {
  const f: Frag = { e, kind, state, pos, t: 0, hit: new Set(), damage };
  frags.set(e.id, f);
  return f;
}

function place(f: Frag): void {
  try {
    if (f.e.isValid) f.e.teleport(f.pos, { keepVelocity: false, checkForBlocks: false });
  } catch {
    // entity unloaded or removed
  }
}

function remove(f: Frag, shatter = true): void {
  frags.delete(f.e.id);
  if (shatter && ctx) {
    particle(ctx.arena.dim, FX.chipBurst, f.pos);
    particle(ctx.arena.dim, FX.goldBurst, f.pos);
  }
  try {
    if (f.e.isValid) f.e.remove();
  } catch {
    // ignore
  }
}

// ------------------------------------------------------------------ launching

/** Throw an edict tablet in an arc onto the court. The landing spot is telegraphed. */
export function launchTablet(from: Vector3, to: Vector3, dur: number, apex: number): Frag | undefined {
  const e = spawn("tablet", from);
  if (!e || !ctx) return undefined;
  telegraph(ctx.arena.dim, to, 2.4, dur / 20 + 0.2);
  const f = register(e, "tablet", "flight", { ...from }, DMG.tablet);
  f.from = { ...from };
  f.to = { ...to };
  f.dur = dur;
  f.apex = apex;
  return f;
}

/** A small shard skidding across the court (dive impact, phase transitions). */
export function slideShard(from: Vector3, dir: Vector3, speed: number): Frag | undefined {
  const e = spawn("shard", from);
  if (!e) return undefined;
  const f = register(e, "shard", "slide", { ...from }, DMG.diveShard);
  f.vel = scale(norm(v(dir.x, 0, dir.z)), speed);
  return f;
}

/** Tear a chunk of the court out and lift it (Rubble Ascension / broken pillars). */
export function raiseRubble(at: Vector3, orbitRadius: number, orbitHeight: number, angle: number): Frag | undefined {
  const e = spawn("rubble", at);
  if (!e) return undefined;
  const f = register(e, "rubble", "rise", { ...at }, DMG.rubble);
  f.radius = orbitRadius;
  f.height = orbitHeight;
  f.angle = angle;
  return f;
}

/** Floating debris high above the court (pillar crowns); purely atmospheric until used. */
export function driftRubble(at: Vector3): Frag | undefined {
  const e = spawn("rubble", at);
  if (!e || !ctx) return undefined;
  const f = register(e, "rubble", "drift", { ...at }, DMG.rubble);
  const c = ctx.arena.center;
  f.angle = Math.atan2(at.z - c.z, at.x - c.x);
  f.radius = Math.max(8, distXZ(at, c));
  f.height = at.y + 4 + Math.random() * 6;
  return f;
}

export function ringShard(at: Vector3): Frag | undefined {
  const e = spawn("shard", at);
  if (!e) return undefined;
  return register(e, "shard", "ring", { ...at }, DMG.storm);
}

export function hurl(f: Frag, target: Vector3, speed: number): void {
  f.state = "hurl";
  f.t = 0;
  f.from = { ...f.pos };
  f.to = { ...target };
  f.speed = speed;
  f.vel = scale(norm(sub(target, f.pos)), speed);
}

export function moveTo(f: Frag, p: Vector3): void {
  f.pos = { ...p };
  place(f);
}

// ------------------------------------------------------------------ queries

export const all = (): Frag[] => [...frags.values()];
export const ofState = (s: State): Frag[] => all().filter((f) => f.state === s && f.e.isValid);
export const embedded = (): Frag[] => ofState("embedded");
export const embeddedCount = (): number => embedded().length;
export const get = (e: Entity): Frag | undefined => frags.get(e.id);

/** Pull every embedded fragment back to the Emperor (Golden Repair). */
export function pullAll(onArrive: (f: Frag) => void): number {
  let n = 0;
  for (const f of embedded()) {
    f.state = "pull";
    f.t = 0;
    f.from = { ...f.pos };
    f.onArrive = onArrive;
    if (f.kind === "tablet") {
      try {
        f.e.setProperty(PROP.embedded, false);
      } catch {
        // entity gone
      }
    }
    n++;
  }
  return n;
}

export function clearAll(): void {
  for (const f of all()) remove(f, false);
  for (const c of courtiers) {
    try {
      if (c.isValid) c.remove();
    } catch {
      // ignore
    }
  }
  courtiers = [];
}

export function removeFrag(f: Frag, shatter = true): void {
  remove(f, shatter);
}

// ------------------------------------------------------------------ lifecycle

function embed(f: Frag): void {
  if (!ctx) return;
  const A = ctx.arena;
  if (!A.hasFloor(f.pos)) {
    // fell into a chasm: gone into the void
    f.state = "flight";
    f.vel = v(0, -0.6, 0);
    f.dur = undefined;
    return;
  }
  f.state = "embedded";
  f.t = 0;
  f.embeddedAt = system.currentTick;
  f.pos = v(Math.floor(f.pos.x) + 0.5, A.floorY - (f.kind === "tablet" ? 0.15 : 0.05), Math.floor(f.pos.z) + 0.5);
  place(f);
  if (f.kind === "tablet") {
    try {
      f.e.setProperty(PROP.embedded, true);
    } catch {
      // ignore
    }
  }
}

function impact(f: Frag, radius: number): void {
  if (!ctx) return;
  for (const p of ctx.players()) {
    if (dist(p.location, f.pos) <= radius + 0.6) ctx.hurt(p, f.damage, f.pos, 0.9, 0.35);
  }
  particle(ctx.arena.dim, FX.chipBurst, f.pos);
  particle(ctx.arena.dim, FX.dust, f.pos);
  ringWave(ctx.arena.dim, v(f.pos.x, ctx.arena.floorY, f.pos.z), radius);
  sound(ctx.arena.dim, SND.crack, f.pos, 1.2, 0.9 + Math.random() * 0.2);
}

function riseAsCourtier(f: Frag): void {
  if (!ctx) return;
  courtiers = courtiers.filter((c) => c.isValid);
  if (courtiers.length >= 4) return;
  const at = v(f.pos.x, ctx.arena.floorY, f.pos.z);
  remove(f, true);
  try {
    const c = ctx.arena.dim.spawnEntity(ENT.courtier, at);
    courtiers.push(c);
    sound(ctx.arena.dim, SND.chime, at, 1.0, 0.6);
    telegraph(ctx.arena.dim, at, 1.6, 1.2, GOLD);
  } catch {
    // ignore
  }
}

export function tickFragments(): void {
  if (!ctx) return;
  const A = ctx.arena;
  const players = ctx.players();
  const phase = ctx.phase();
  const now = system.currentTick;
  for (const f of all()) {
    if (!f.e.isValid) {
      frags.delete(f.e.id);
      continue;
    }
    f.t++;
    switch (f.state) {
      case "flight": {
        if (f.dur && f.from && f.to) {
          const k = Math.min(1, f.t / f.dur);
          const p = lerp(f.from, f.to, k);
          p.y += (f.apex ?? 4) * 4 * k * (1 - k);
          f.pos = p;
          place(f);
          if (f.t % 2 === 0) particle(A.dim, FX.goldMote, p);
          if (k >= 1) {
            impact(f, 2.2);
            embed(f);
          }
        } else {
          // falling into the void
          f.pos = add(f.pos, f.vel ?? v(0, -0.6, 0));
          place(f);
          if (f.pos.y < A.floorY + A.bp.bottom - 6) remove(f, false);
        }
        break;
      }
      case "slide": {
        const vel = f.vel ?? v(0, 0, 0);
        f.pos = add(f.pos, vel);
        f.pos.y = A.floorY + 0.1;
        f.vel = scale(vel, 0.9);
        place(f);
        for (const p of players) {
          if (!f.hit.has(p.id) && dist(p.location, f.pos) < 1.2) {
            f.hit.add(p.id);
            ctx.hurt(p, f.damage, f.pos, 0.6, 0.2);
          }
        }
        if (!A.isInside(f.pos, -0.5) || !A.hasFloor(f.pos)) {
          if (!A.hasFloor(f.pos)) {
            f.state = "flight";
            f.dur = undefined;
            f.vel = v(0, -0.6, 0);
          } else embed(f);
        } else if ((f.vel.x * f.vel.x + f.vel.z * f.vel.z) < 0.004 || f.t > 60) embed(f);
        break;
      }
      case "embedded": {
        if (f.t % 20 === 0) particle(A.dim, FX.goldMote, add(f.pos, v(0, f.kind === "tablet" ? 1.4 : 0.4, 0)));
        if (!A.hasFloor(f.pos)) {
          // the chasm opened under it
          f.state = "flight";
          f.dur = undefined;
          f.vel = v(0, -0.6, 0);
          break;
        }
        const age = now - (f.embeddedAt ?? now);
        if (phase >= 3 && age > 200) riseAsCourtier(f);
        else if (age > 900) remove(f, true);
        break;
      }
      case "rise": {
        const boss = ctx.bossPos() ?? A.center;
        const k = Math.min(1, f.t / 30);
        f.angle = (f.angle ?? 0) + 0.05;
        const target = v(boss.x + Math.cos(f.angle) * (f.radius ?? 6), A.floorY + (f.height ?? 6), boss.z + Math.sin(f.angle) * (f.radius ?? 6));
        f.pos = lerp(f.pos, target, 0.06 + k * 0.1);
        place(f);
        if (f.t % 3 === 0) particle(A.dim, FX.dust, f.pos);
        if (f.t >= 30) f.state = "orbit";
        break;
      }
      case "orbit": {
        const boss = ctx.bossPos() ?? A.center;
        f.angle = (f.angle ?? 0) + 0.06;
        f.pos = v(boss.x + Math.cos(f.angle) * (f.radius ?? 6), A.floorY + (f.height ?? 6) + Math.sin(f.t * 0.1) * 0.4,
          boss.z + Math.sin(f.angle) * (f.radius ?? 6));
        place(f);
        break;
      }
      case "drift": {
        const c = A.center;
        f.angle = (f.angle ?? 0) + 0.004;
        const target = v(c.x + Math.cos(f.angle) * (f.radius ?? 20), (f.height ?? A.floorY + 18) + Math.sin(f.t * 0.03) * 0.8,
          c.z + Math.sin(f.angle) * (f.radius ?? 20));
        f.pos = lerp(f.pos, target, 0.03);
        if (f.t % 2 === 0) place(f);
        break;
      }
      case "hurl": {
        const vel = f.vel ?? v(0, -1, 0);
        f.pos = add(f.pos, vel);
        place(f);
        if (f.t % 2 === 0) particle(A.dim, FX.redMote, f.pos);
        let hitNow = false;
        for (const p of players) if (dist(add(p.location, v(0, 0.9, 0)), f.pos) < 1.5) hitNow = true;
        const reached = f.to ? dist(f.pos, f.to) < (f.speed ?? 1) + 0.2 : false;
        const floor = f.pos.y <= A.floorY + 0.3 && A.hasFloor(f.pos);
        if (hitNow || reached || floor || f.t > 80) {
          impact(f, 1.8);
          remove(f, true);
        }
        break;
      }
      case "pull": {
        const boss = ctx.bossPos();
        if (!boss || !f.from) {
          remove(f, true);
          break;
        }
        const k = Math.min(1, f.t / 16);
        const p = lerp(f.from, add(boss, v(0, 2, 0)), k * k);
        p.y += Math.sin(k * Math.PI) * 3;
        f.pos = p;
        place(f);
        particle(A.dim, FX.goldMote, p);
        if (k >= 1) {
          f.onArrive?.(f);
          remove(f, false);
          particle(A.dim, FX.goldBurst, p);
        }
        break;
      }
      case "ring":
        break;
    }
  }
}

/** A player shattered a fragment: reward them with golden absorption (and sometimes a shard). */
export function onFragmentDestroyed(e: Entity, killer?: Entity): boolean {
  const f = frags.get(e.id);
  if (!f || !ctx) return false;
  frags.delete(e.id);
  particle(ctx.arena.dim, FX.chipBurst, f.pos);
  particle(ctx.arena.dim, FX.goldBurst, f.pos);
  sound(ctx.arena.dim, SND.chime, f.pos, 1.0, 1.2 + Math.random() * 0.3);
  if (killer instanceof Player) {
    try {
      killer.addEffect("absorption", 200, { amplifier: f.kind === "tablet" ? 1 : 0, showParticles: false });
      killer.onScreenDisplay.setActionBar(f.state === "embedded" ? "§6Shard shattered §7- the Emperor cannot reclaim it" : "§6Fragment shattered in the air!");
    } catch {
      // ignore
    }
    if (Math.random() < (f.kind === "tablet" ? 0.25 : 0.1)) {
      try {
        ctx.arena.dim.spawnItem(new ItemStack(ITEM.shard, 1), f.pos);
      } catch {
        // ignore
      }
    }
  }
  return true;
}

export const courtierCount = (): number => (courtiers = courtiers.filter((c) => c.isValid)).length;
