import { Dimension, Entity, Player, Vector3, world } from "@minecraft/server";
import { CONFIG } from "../config/global";
import { FLOOR_ACTORS, GROUND_ACTORS, GROUND_NEAR, GROUND_NEAR_TOLERANCE } from "../config/ground";
import { inWorld } from "./bounds";
import { groundBelow, plateau, terrainTop } from "./targeting";

export const NS = "grimoire";
/** Seconds -> ticks. */
export const secs = (s: number): number => Math.max(0, Math.round(s * 20));

export interface SpawnOpts {
  /** Facing in Minecraft yaw degrees (0 = south). */
  yaw?: number;
  state?: number;
  kind?: number;
  size?: number;
  skin?: number;
}

let warned = new Set<string>();
function warnOnce(key: string, msg: string): void {
  if (warned.has(key)) return;
  warned.add(key);
  console.warn(`[grimoire] ${msg}`);
}

/**
 * Ground-bound actor types stand on the terrain under their own position (see config/ground.ts).
 * Returns the height to use, or undefined when the type is free to be anywhere.
 */
function settledY(dim: Dimension, key: string, loc: Vector3, size: number): number | undefined {
  let radius = GROUND_ACTORS[key];
  let tolerance = 24;
  if (radius === undefined) {
    radius = GROUND_NEAR[key];
    if (radius === undefined) return undefined;
    tolerance = GROUND_NEAR_TOLERANCE;
  }
  const g = groundBelow(dim, loc);
  if (Math.abs(g.y - loc.y) > tolerance) return undefined;
  return radius * size >= 2 ? plateau(dim, g, radius * size).y : g.y;
}
const isBound = (key: string): boolean => GROUND_ACTORS[key] !== undefined || GROUND_NEAR[key] !== undefined;

/** Safe wrapper around a spell entity.  Every method is a no-op once the entity is gone. */
export class Actor {
  private lastYaw = 0;
  private sz = 1;
  private gKey = "";
  private gY: number | undefined;
  private readonly key: string;
  constructor(public readonly entity: Entity | undefined, public readonly typeId: string) {
    this.key = typeId.startsWith(`${NS}:`) ? typeId.slice(NS.length + 1) : typeId;
  }
  /**
   * Terrain handling for a requested position.  Ground-bound actors follow the surface (eased, so
   * walking over steps is not a jolt); free-moving ones are only lifted out of terrain they would
   * otherwise sink into.
   */
  private settle(loc: Vector3): Vector3 {
    const bound = isBound(this.key);
    if (!bound && !FLOOR_ACTORS.has(this.key)) return loc;
    const k = `${Math.floor(loc.x)},${Math.floor(loc.z)},${Math.round(loc.y * 4)}`;
    if (k !== this.gKey) {
      this.gKey = k;
      const dim = this.entity!.dimension;
      this.gTarget = bound ? settledY(dim, this.key, loc, this.sz) : terrainTop(dim, loc);
      if (this.gTarget !== undefined && this.gY === undefined) this.gY = bound ? this.gTarget : Math.max(loc.y, this.gTarget - 1.5);
    }
    if (this.gTarget === undefined) {
      if (this.gY === undefined) return loc;
      // back in the open: ease from the lifted height to the requested one
      this.gY += (loc.y - this.gY) * 0.35;
      if (Math.abs(loc.y - this.gY) < 0.05) { this.gY = undefined; return loc; }
      return { x: loc.x, y: this.gY, z: loc.z };
    }
    const cur = this.gY ?? this.gTarget;
    const next = cur + (this.gTarget - cur) * (this.gTarget > cur ? 0.6 : 0.3);   // climb fast, descend gently
    this.gY = Math.abs(this.gTarget - next) < 0.02 ? this.gTarget : next;
    return { x: loc.x, y: this.gY, z: loc.z };
  }
  private gTarget: number | undefined;

  get valid(): boolean {
    return this.entity !== undefined && this.entity.isValid;
  }
  get loc(): Vector3 {
    return this.valid ? this.entity!.location : { x: 0, y: 0, z: 0 };
  }
  get yaw(): number {
    return this.lastYaw;
  }
  prop(name: string, value: number | boolean | string): this {
    if (!this.valid) return this;
    try {
      this.entity!.setProperty(`${NS}:${name}`, value);
    } catch (e) {
      warnOnce(`${this.typeId}.${name}`, `cannot set ${name}=${value} on ${this.typeId}: ${e}`);
    }
    return this;
  }
  state(n: number): this { return this.prop("state", n); }
  kind(n: number): this { return this.prop("kind", n); }
  size(n: number): this { this.sz = n; return this.prop("size", n); }
  skin(n: number): this { return this.prop("skin", n); }
  /**
   * The facing the model is drawn with.  The entity rotation alone is not enough (the game steers a
   * mob's body yaw by its own rules), so the wanted yaw is also sent as the synced property
   * grimoire:yaw, which the client uses to turn the model (see kit/pack.py, "Facing").
   */
  private sentYaw = 0;
  private setYaw(yaw: number): void {
    this.lastYaw = yaw;
    let y = ((yaw + 180) % 360 + 360) % 360 - 180;
    if (y === -180) y = 180;
    y = Math.round(y * 100) / 100;
    if (y !== this.sentYaw) { this.sentYaw = y; this.prop("yaw", y); }
  }
  /** Teleport (and optionally face a yaw).  Called every tick this gives smooth motion. */
  move(loc: Vector3, yaw?: number): this {
    if (!this.valid) return this;
    if (yaw !== undefined) this.setYaw(yaw);
    try {
      this.entity!.teleport(inWorld(this.entity!.dimension, this.settle(loc)), { rotation: { x: 0, y: this.lastYaw } });
    } catch {
      /* unloaded chunk: ignore */
    }
    return this;
  }
  face(yaw: number): this {
    if (!this.valid) return this;
    this.setYaw(yaw);
    // teleport-in-place: unlike setRotation this also sets the body yaw on the server
    try {
      this.entity!.teleport(this.entity!.location, { rotation: { x: 0, y: yaw } });
    } catch { /* ignore */ }
    return this;
  }
  anim(name: string): this {
    if (!this.valid) return this;
    try {
      this.entity!.playAnimation(name);
    } catch { /* ignore */ }
    return this;
  }
  remove(): void {
    if (!this.valid) return;
    try {
      this.entity!.remove();
    } catch { /* ignore */ }
  }
}

type Loop = { from: number; to: number; every: number; fn: (elapsed: number) => void };

/**
 * One activated spell.  Owns every entity, timer and temporary block the spell creates so
 * that ending or aborting the scene always leaves the world clean.
 */
export class Scene {
  tick = 0;
  ended = false;
  readonly dim: Dimension;
  readonly dimId: string;
  readonly origin: Vector3;
  readonly actors = new Set<Actor>();
  private timeline: { t: number; fn: () => void }[] = [];
  private loops: Loop[] = [];
  private endHooks: (() => void)[] = [];
  private endTick = Number.POSITIVE_INFINITY;

  constructor(public readonly spellId: string, public readonly caster: Player) {
    this.dim = caster.dimension;
    this.dimId = caster.dimension.id;
    this.origin = { ...caster.location };
  }

  /** Run fn once at an absolute scene tick. */
  at(t: number, fn: () => void): this {
    this.timeline.push({ t: Math.max(Math.round(t), this.tick), fn });
    return this;
  }
  /** Run fn once `delay` ticks from now. */
  after(delay: number, fn: () => void): this {
    return this.at(this.tick + Math.max(0, Math.round(delay)), fn);
  }
  /** Run fn every `every` ticks while from <= tick < to.  fn receives ticks elapsed since `from`. */
  every(every: number, fn: (elapsed: number) => void, from = 0, to = Number.POSITIVE_INFINITY): this {
    this.loops.push({ from: Math.round(from), to: Math.round(to), every: Math.max(1, Math.round(every)), fn });
    return this;
  }
  /** Run fn each tick in [from, to) with progress 0..1. */
  span(from: number, to: number, fn: (p: number, elapsed: number) => void): this {
    const a = Math.round(from), b = Math.max(a + 1, Math.round(to));
    return this.every(1, (e) => fn(Math.min(1, e / (b - a - 1 || 1)), e), a, b);
  }
  /** Spawn a spell entity that is removed automatically when the scene ends. */
  spawn(typeId: string, loc: Vector3, opts: SpawnOpts = {}): Actor {
    const id = typeId.includes(":") ? typeId : `${NS}:${typeId}`;
    if (this.ended || Scenes.actorCount() >= CONFIG.limits.maxActors) return new Actor(undefined, id);
    let e: Entity | undefined;
    try {
      const key = id.slice(NS.length + 1);
      const gy = isBound(key) ? settledY(this.dim, key, loc, opts.size ?? 1) : FLOOR_ACTORS.has(key) ? terrainTop(this.dim, loc) : undefined;
      if (gy !== undefined) loc = { x: loc.x, y: gy, z: loc.z };
    } catch { /* keep the requested height */ }
    loc = inWorld(this.dim, loc);
    try {
      e = this.dim.spawnEntity(id, loc, opts.yaw !== undefined ? { initialRotation: opts.yaw } : undefined);
    } catch (err) {
      warnOnce(`spawn.${id}`, `cannot spawn ${id}: ${err}`);
    }
    const a = new Actor(e, id);
    if (e) {
      this.actors.add(a);
      try { e.addTag("grimoire_scene"); } catch { /* ignore */ }
      if (opts.kind !== undefined) a.kind(opts.kind);
      if (opts.size !== undefined) a.size(opts.size);
      if (opts.skin !== undefined) a.skin(opts.skin);
      if (opts.state !== undefined) a.state(opts.state);
      if (opts.yaw !== undefined) a.move(loc, opts.yaw);
    }
    return a;
  }
  /** Remove one actor now. */
  despawn(a: Actor): void {
    a.remove();
    this.actors.delete(a);
  }
  /** Keep an actor glued to a moving entity; the actor is removed when the target is gone. */
  follow(a: Actor, target: Entity, dy = 0, until = Number.POSITIVE_INFINITY): this {
    return this.every(1, () => {
      if (!a.valid) return;
      if (!target.isValid) { this.despawn(a); return; }
      const l = target.location;
      a.move({ x: l.x, y: l.y + dy, z: l.z });
    }, this.tick, until);
  }
  onEnd(fn: () => void): this {
    this.endHooks.push(fn);
    return this;
  }
  /** Schedule the scene to finish (and clean up) at an absolute tick. */
  endAt(t: number): this {
    this.endTick = Math.round(t);
    return this;
  }
  get casterOk(): boolean {
    return this.caster.isValid && this.caster.dimension.id === this.dimId;
  }

  /** Finish now: runs end hooks, removes every actor. Safe to call repeatedly. */
  end(): void {
    if (this.ended) return;
    this.ended = true;
    for (const h of this.endHooks) {
      try { h(); } catch (e) { console.warn(`[grimoire] ${this.spellId} end hook: ${e}`); }
    }
    for (const a of this.actors) a.remove();
    this.actors.clear();
    this.timeline.length = 0;
    this.loops.length = 0;
    Scenes.active.delete(this);
  }

  /** @internal advance one tick */
  step(): void {
    if (this.ended) return;
    if (!this.casterOk || this.tick >= this.endTick) { this.end(); return; }
    try {
      for (const l of this.loops) {
        if (this.tick >= l.from && this.tick < l.to && (this.tick - l.from) % l.every === 0) l.fn(this.tick - l.from);
        if (this.ended) return;
      }
      if (this.timeline.length) {
        const due = this.timeline.filter((e) => e.t <= this.tick);
        if (due.length) {
          this.timeline = this.timeline.filter((e) => e.t > this.tick);
          due.sort((a, b) => a.t - b.t);
          for (const e of due) { e.fn(); if (this.ended) return; }
        }
      }
      this.loops = this.loops.filter((l) => this.tick < l.to);
    } catch (e) {
      console.warn(`[grimoire] ${this.spellId} failed at tick ${this.tick}: ${e} ${(e as Error)?.stack ?? ""}`);
      this.end();
      return;
    }
    this.tick++;
  }
}

export const Scenes = {
  active: new Set<Scene>(),
  start(spellId: string, caster: Player): Scene {
    const s = new Scene(spellId, caster);
    this.active.add(s);
    return s;
  },
  actorCount(): number {
    let n = 0;
    for (const s of this.active) n += s.actors.size;
    return n;
  },
  tickAll(): void {
    for (const s of [...this.active]) s.step();
  },
  endFor(player: Player): void {
    for (const s of [...this.active]) if (s.caster.id === player.id) s.end();
  },
  endAll(): void {
    for (const s of [...this.active]) s.end();
  },
  /** Remove spell entities left behind by a previous script session. */
  sweepOrphans(): void {
    for (const id of ["overworld", "nether", "the_end"]) {
      try {
        for (const e of world.getDimension(id).getEntities({ families: ["grimoire_construct"] })) {
          try { e.remove(); } catch { /* ignore */ }
        }
      } catch { /* dimension not ready */ }
    }
  },
};
