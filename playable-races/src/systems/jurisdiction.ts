/**
 * Divine Jurisdiction - the system behind race 006 Nurariten (Unique).
 *
 *  Courts      temporary zones a Nurariten declares (the Uninvited Temple; the court of the
 *              Hundred Heavens during HYAKUTEN CHUKO).  A court never touches blocks, claims
 *              no land and protects nothing: it is a circle of authority that lasts seconds.
 *              Inside its own court the owner is "the master of the house"; enemies inside
 *              are slowed and accrue judgment; exiled creatures are turned away at the edge.
 *  Judgment    1-3 stacks on a creature (a golden seal above its head), applied by edicts,
 *              courts and the ultimate, consumed by Imperial Expulsion and the Final Edict.
 *              Marks fade 12 s after their last refresh.  Any number of Nurariten may judge
 *              the same creature; each one only sees and consumes its own marks.
 *
 * Everything here is runtime state: a reload ends courts and marks (nothing to restore),
 * and every entry is dropped as soon as its owner dies, leaves or changes dimension.
 */
import { Entity, Player, Vector3, system, world } from "@minecraft/server";
import { effect, knockFrom } from "../core/combat.js";
import { particle } from "../core/fx.js";
import { alive, enemiesNear } from "../core/targets.js";
import { add, hdist, v3 } from "../core/util.js";

export type CourtKind = "temple" | "heaven";
export type CourtEnd = "expired" | "broken" | "owner" | "replaced";

export interface Court {
  owner: string;
  kind: CourtKind;
  dim: string;
  center: Vector3;
  radius: number;
  born: number;
  until: number;
  /** entity id -> tick until which it may not enter */
  exiled: Map<string, number>;
  /** entity id -> tick it last gained judgment from standing inside */
  judged: Map<string, number>;
  /** called once when the court ends (any reason) */
  end?: (c: Court, reason: CourtEnd) => void;
}

export const MAX_MARKS = 3;
const MARK_TICKS = 240;
const COURT_JUDGE_EVERY = 60;

const courts: Court[] = [];

interface Judgment {
  stacks: number;
  until: number;
}
/** entity id -> judge id -> marks */
const judgments = new Map<string, Map<string, Judgment>>();

// ------------------------------------------------------------------ courts

export function declareCourt(owner: Player, kind: CourtKind, center: Vector3, radius: number, ticks: number, end?: Court["end"]): Court {
  endCourt(owner.id, kind, "replaced");
  const now = system.currentTick;
  const c: Court = { owner: owner.id, kind, dim: owner.dimension.id, center: { ...center }, radius, born: now, until: now + ticks,
    exiled: new Map(), judged: new Map(), end };
  courts.push(c);
  return c;
}

export function courtOf(ownerId: string, kind?: CourtKind): Court | undefined {
  return courts.find((c) => c.owner === ownerId && (kind === undefined || c.kind === kind));
}

export function endCourt(ownerId: string, kind: CourtKind | undefined, reason: CourtEnd): void {
  for (let i = courts.length - 1; i >= 0; i--) {
    const c = courts[i];
    if (c.owner !== ownerId || (kind !== undefined && c.kind !== kind)) continue;
    courts.splice(i, 1);
    try {
      c.end?.(c, reason);
    } catch {
      /* visuals only */
    }
  }
}

function inside(c: Court, dimId: string, loc: Vector3, pad = 0): boolean {
  return c.dim === dimId && hdist(loc, c.center) <= c.radius + pad && Math.abs(loc.y - c.center.y) <= 6;
}

/** Is the player standing inside one of their own courts (of `kind`, or any)? */
export function inOwnCourt(p: Player, kind?: CourtKind): boolean {
  return courts.some((c) => c.owner === p.id && (kind === undefined || c.kind === kind) && inside(c, p.dimension.id, p.location, 0.5));
}

/** Is `e` inside a court owned by `ownerId`? */
export function inCourtOf(ownerId: string, e: Entity): Court | undefined {
  return courts.find((c) => c.owner === ownerId && inside(c, e.dimension.id, e.location));
}

export function exile(c: Court, e: Entity, ticks: number): void {
  c.exiled.set(e.id, system.currentTick + ticks);
}

export function courtSecondsLeft(c: Court): number {
  return Math.max(0, (c.until - system.currentTick) / 20);
}

// ------------------------------------------------------------------ judgment marks

/** Add `n` judgment marks from `by` (capped at 3); returns the new count. */
export function judge(e: Entity, by: Player | string, n = 1): number {
  const id = typeof by === "string" ? by : by.id;
  let m = judgments.get(e.id);
  if (!m) {
    m = new Map();
    judgments.set(e.id, m);
  }
  const now = system.currentTick;
  const j = m.get(id);
  const have = j && j.until > now ? j.stacks : 0;
  const stacks = Math.min(MAX_MARKS, have + n);
  m.set(id, { stacks, until: now + MARK_TICKS });
  try {
    particle(e.dimension, "plrace:judgment_seal", add(e.location, v3(0, headroom(e), 0)), { stacks });
  } catch {
    /* ignore */
  }
  return stacks;
}

export function marksOn(e: Entity | string, by: string): number {
  const j = judgments.get(typeof e === "string" ? e : e.id)?.get(by);
  return j && j.until > system.currentTick ? j.stacks : 0;
}

/** Remove and return `by`'s marks on `e`. */
export function consumeMarks(e: Entity, by: string): number {
  const m = judgments.get(e.id);
  const n = marksOn(e, by);
  if (m) {
    m.delete(by);
    if (m.size === 0) judgments.delete(e.id);
  }
  return n;
}

/** Every creature currently judged by `by` (valid entities only). */
export function judgedBy(by: string): Entity[] {
  const out: Entity[] = [];
  const now = system.currentTick;
  for (const [id, m] of judgments) {
    const j = m.get(by);
    if (!j || j.until <= now) continue;
    let e: Entity | undefined;
    try {
      e = world.getEntity(id);
    } catch {
      e = undefined;
    }
    if (alive(e)) out.push(e);
  }
  return out;
}

export function clearJudgmentsBy(by: string): void {
  for (const [id, m] of judgments) {
    m.delete(by);
    if (m.size === 0) judgments.delete(id);
  }
}

/** Remove every court and mark a player owns (death, logout, dimension or lineage change). */
export function releaseJurisdiction(ownerId: string): void {
  endCourt(ownerId, undefined, "owner");
  clearJudgmentsBy(ownerId);
}

function headroom(e: Entity): number {
  return e.typeId === "minecraft:player" ? 2.3 : 2.1;
}

// ------------------------------------------------------------------ world tick (every 4 ticks)

let beat = 0;

export function tickJurisdiction(): void {
  beat++;
  const now = system.currentTick;
  if (courts.length) tickCourts(now);
  if (judgments.size && beat % 2 === 0) tickMarks(now);
}

function tickCourts(now: number): void {
  for (const c of [...courts]) {
    let owner: Entity | undefined;
    try {
      owner = world.getEntity(c.owner);
    } catch {
      owner = undefined;
    }
    if (!owner || !owner.isValid || !(owner instanceof Player) || owner.dimension.id !== c.dim) {
      endCourt(c.owner, c.kind, "owner");
      continue;
    }
    if (c.until <= now) {
      endCourt(c.owner, c.kind, "expired");
      continue;
    }
    // Broken Mandate: the master may not leave the house it has claimed
    if (c.kind === "temple" && !inside(c, owner.dimension.id, owner.location, 1.5)) {
      endCourt(c.owner, c.kind, "broken");
      continue;
    }
    const dim = owner.dimension;
    const age = now - c.born;
    // the boundary: eight pillars of light walking slowly around the circle, a ring on the ground
    if (age % 8 === 0) {
      for (let k = 0; k < 8; k++) {
        const a = ((k * 45 + age * 0.9) * Math.PI) / 180;
        particle(dim, "plrace:court_pillar", add(c.center, v3(Math.cos(a) * c.radius, 0.1, Math.sin(a) * c.radius)));
      }
    }
    if (age % 20 === 0) particle(dim, "plrace:court_ring", add(c.center, v3(0, 0.08, 0)), { size: c.radius * 2 });
    for (const e of enemiesNear(owner, c.center, c.radius + 2.5)) {
      const ex = c.exiled.get(e.id);
      const inNow = inside(c, dim.id, e.location);
      if (ex !== undefined && ex > now) {
        // exiled: turned away at the threshold
        if (inside(c, dim.id, e.location, 0.8)) knockFrom(e, c.center, 0.9, 0.15);
        continue;
      }
      if (!inNow) continue;
      effect(e, "slowness", 30, 0, false);
      const last = c.judged.get(e.id);
      if (last === undefined) c.judged.set(e.id, now - COURT_JUDGE_EVERY + 20); // first mark after 1 s inside
      else if (now - last >= COURT_JUDGE_EVERY) {
        c.judged.set(e.id, now);
        judge(e, c.owner, 1);
      }
    }
  }
}

function tickMarks(now: number): void {
  for (const [id, m] of judgments) {
    for (const [by, j] of m) if (j.until <= now) m.delete(by);
    if (m.size === 0) {
      judgments.delete(id);
      continue;
    }
    let e: Entity | undefined;
    try {
      e = world.getEntity(id);
    } catch {
      e = undefined;
    }
    if (!alive(e)) {
      judgments.delete(id);
      continue;
    }
    let stacks = 0;
    for (const j of m.values()) stacks = Math.max(stacks, j.stacks);
    particle(e.dimension, "plrace:judgment_seal", add(e.location, v3(0, headroom(e), 0)), { stacks });
  }
}
