/**
 * Boss parts that survive chunk loading.
 *
 * spawnEntity throws in chunks that are not loaded, and an Entity handle goes
 * stale whenever its chunk unloads. A Parts registry therefore:
 *   - spawns every part as soon as its chunk is loaded (and keeps retrying),
 *   - re-acquires handles by entity id after a chunk unloads and reloads,
 *   - keeps the desired entity properties and re-applies them on reload,
 *   - re-creates a part whose entity disappeared while its chunk was loaded,
 *   - removes stale parts of earlier fights when they load (onLoad).
 * When the engine refuses a spawn although the chunk is loaded, the /summon
 * command is tried as well, the reason is kept for diagnostics, and a part
 * that appears away from its place is moved back.
 */
import { Entity, EntityTypes, world } from "@minecraft/server";
import { pointLoaded } from "./chunks.js";
import { V3 } from "./vec.js";

type PropValue = boolean | number | string;

export interface PartSpec {
  type: string;
  pos: V3;
  yaw?: number;
  /** Entity properties to keep applied. */
  props?: Record<string, PropValue>;
  /** Runs once for every newly created entity (e.g. restore health). */
  init?: (e: Entity) => void;
}

interface Part extends PartSpec {
  key: string;
  props: Record<string, PropValue>;
  id?: string;
  handle?: Entity;
  tries: number;
  lookupTick: number;
  missingSince: number;
  /** Why the last attempt in a loaded chunk failed (diagnostics). */
  lastError?: string;
  failures: number;
  /** Earliest tick for the next attempt after a failure in a loaded chunk. */
  nextTry: number;
  /** /summon created an entity that could not be found: do not try it again for this part. */
  noSummon?: boolean;
  via?: "api" | "command";
  /** Distance from its place at which the engine created it (moved back). */
  offsite?: number;
}

/** Diagnostic state of one part. */
export interface PartReport {
  key: string;
  type: string;
  state: "ok" | "unloaded" | "waiting" | "failed";
  at?: V3;
  error?: string;
  via?: string;
  offsite?: number;
}

export function describeError(err: unknown): string {
  const s = err instanceof Error ? `${err.name && err.name !== "Error" ? err.name + ": " : ""}${err.message}` : String(err);
  return s.replace(/\s+/g, " ").slice(0, 160);
}

/** Entity types of `types` the game has not registered (their behaviour file did not load). */
export function missingEntityTypes(types: string[]): string[] {
  return types.filter((t) => {
    try {
      return !EntityTypes.get(t);
    } catch {
      return false;
    }
  });
}

export class Parts {
  private parts = new Map<string, Part>();
  private owner = new Map<string, string>();
  private now = 0;
  /** Entities created / re-created (diagnostics). */
  spawns = 0;
  respawns = 0;

  constructor(
    private readonly dim: import("@minecraft/server").Dimension,
    private readonly tag: string,
  ) {}

  /** Track a part; spawns it now if its chunk is loaded. */
  want(key: string, spec: PartSpec): Entity | undefined {
    this.drop(key);
    const p: Part = { ...spec, key, props: { ...(spec.props ?? {}) }, tries: 0, lookupTick: -999, missingSince: -1, failures: 0, nextTry: 0 };
    this.parts.set(key, p);
    return this.spawn(p);
  }

  has(key: string): boolean {
    return this.parts.has(key);
  }

  /** A valid handle (undefined while the part is not spawned or its chunk is unloaded). */
  get(key: string): Entity | undefined {
    const p = this.parts.get(key);
    return p ? this.resolve(p) : undefined;
  }

  /** Valid handles of every part whose key starts with `prefix`. */
  list(prefix: string): Entity[] {
    const out: Entity[] = [];
    for (const p of this.parts.values()) {
      if (!p.key.startsWith(prefix)) continue;
      const e = this.resolve(p);
      if (e) out.push(e);
    }
    return out;
  }

  /** The part key of an entity (by id, so reloaded handles are recognised). */
  keyOf(e: Entity): string | undefined {
    try {
      return this.owner.get(e.id);
    } catch {
      return undefined;
    }
  }

  /** Set a property now and keep it applied after reloads/respawns. */
  prop(key: string, name: string, value: PropValue): void {
    const p = this.parts.get(key);
    if (!p) return;
    p.props[name] = value;
    const e = this.resolve(p);
    if (e)
      try {
        e.setProperty(name, value);
      } catch {
        /* stale */
      }
  }

  /** prop() for every part with the prefix. */
  propAll(prefix: string, name: string, value: PropValue): void {
    for (const k of [...this.parts.keys()]) if (k.startsWith(prefix)) this.prop(k, name, value);
  }

  /** prop() for an entity that may be a part (falls back to a plain setProperty). */
  propOf(e: Entity, name: string, value: PropValue): void {
    const k = this.keyOf(e);
    if (k) this.prop(k, name, value);
    else
      try {
        if (e.isValid) e.setProperty(name, value);
      } catch {
        /* ignore */
      }
  }

  /** Stop tracking a part without removing its entity (it plays a death animation and removes itself). */
  release(key: string): Entity | undefined {
    const p = this.parts.get(key);
    if (!p) return undefined;
    const e = this.resolve(p, true);
    this.parts.delete(key);
    if (p.id) this.owner.delete(p.id);
    return e;
  }

  /** Stop tracking a part and remove its entity. */
  drop(key: string): void {
    const e = this.release(key);
    try {
      if (e?.isValid) e.remove();
    } catch {
      /* ignore */
    }
  }

  clear(): void {
    for (const k of [...this.parts.keys()]) this.drop(k);
  }

  summary(prefix: string): { total: number; spawned: number; loaded: number } {
    let total = 0;
    let spawned = 0;
    let loaded = 0;
    for (const p of this.parts.values()) {
      if (!p.key.startsWith(prefix)) continue;
      total++;
      if (p.id) spawned++;
      if (this.resolve(p)) loaded++;
    }
    return { total, spawned, loaded };
  }

  /** Per-part diagnostic state for parts whose key starts with `prefix`. */
  report(prefix = ""): PartReport[] {
    const out: PartReport[] = [];
    for (const p of this.parts.values()) {
      if (!p.key.startsWith(prefix)) continue;
      const e = this.resolve(p);
      let state: PartReport["state"];
      if (e) state = "ok";
      else if (p.id) state = "unloaded";
      else if (p.lastError && pointLoaded(this.dim, p.pos)) state = "failed";
      else state = "waiting";
      let at: V3 | undefined;
      try {
        at = e ? { ...e.location } : undefined;
      } catch {
        at = undefined;
      }
      out.push({ key: p.key, type: p.type, state, at, error: p.lastError, via: p.via, offsite: p.offsite });
    }
    return out;
  }

  /** Retry pending spawns and re-create parts that vanished (call every few ticks). */
  tick(now: number): void {
    this.now = now;
    for (const p of this.parts.values()) {
      if (!p.id) {
        if (now >= p.nextTry && pointLoaded(this.dim, p.pos)) this.spawn(p);
        continue;
      }
      if (p.handle?.isValid || this.resolve(p, true)) {
        p.missingSince = -1;
        continue;
      }
      if (!pointLoaded(this.dim, p.pos)) {
        p.missingSince = -1;
        continue;
      }
      if (p.missingSince < 0) p.missingSince = now;
      else if (now - p.missingSince >= 60) {
        // its chunk has been loaded for 3 s but the entity is gone: re-create it
        this.owner.delete(p.id);
        p.id = undefined;
        p.handle = undefined;
        p.missingSince = -1;
        this.respawns++;
        this.spawn(p);
      }
    }
  }

  /** world.afterEvents.entityLoad: re-bind our parts, remove stale parts of earlier fights. */
  onLoad(e: Entity): void {
    let key: string | undefined;
    try {
      key = this.owner.get(e.id);
    } catch {
      return;
    }
    const p = key ? this.parts.get(key) : undefined;
    if (p) {
      p.handle = e;
      p.missingSince = -1;
      this.apply(p, e);
      return;
    }
    try {
      if (e.isValid && e.hasTag(this.tag)) e.remove();
    } catch {
      /* ignore */
    }
  }

  private resolve(p: Part, force = false): Entity | undefined {
    if (p.handle?.isValid) return p.handle;
    if (!p.id) return undefined;
    if (!force && this.now - p.lookupTick < 10) return undefined;
    p.lookupTick = this.now;
    let e: Entity | undefined;
    try {
      e = world.getEntity(p.id);
    } catch {
      e = undefined;
    }
    if (e?.isValid) {
      p.handle = e;
      this.apply(p, e);
      return e;
    }
    p.handle = undefined;
    return undefined;
  }

  private apply(p: Part, e: Entity): void {
    for (const [n, v] of Object.entries(p.props))
      try {
        e.setProperty(n, v);
      } catch (err) {
        console.warn(`[anatomy] ${p.key}: property ${n} not applied (${String(err)})`);
      }
  }

  private spawn(p: Part): Entity | undefined {
    p.tries++;
    let e: Entity | undefined;
    let apiError: string | undefined;
    try {
      e = this.dim.spawnEntity(p.type, p.pos, { initialRotation: p.yaw ?? 0 });
      p.via = "api";
    } catch (err) {
      apiError = describeError(err);
    }
    if (!e) {
      // not loaded yet is the usual reason (tick() retries); with the chunk loaded something else is wrong
      if (!pointLoaded(this.dim, p.pos)) return undefined;
      e = p.noSummon ? undefined : this.summon(p);
      if (!e) {
        p.lastError = `spawnEntity: ${apiError ?? "?"} | summon: ${p.noSummon ? "skipped" : (p.lastError ?? "?")}`;
        p.failures++;
        p.nextTry = this.now + 100;
        if (p.failures === 1 || p.failures % 120 === 0) console.warn(`[anatomy] ${p.key} (${p.type}) could not be created: ${p.lastError}`);
        return undefined;
      }
      p.via = "command";
      console.warn(`[anatomy] ${p.key} created with /summon after spawnEntity failed: ${apiError}`);
    }
    p.id = e.id;
    p.handle = e;
    p.missingSince = -1;
    p.lastError = undefined;
    this.owner.set(e.id, p.key);
    this.spawns++;
    try {
      e.addTag(this.tag);
    } catch {
      /* ignore */
    }
    // a part the engine placed somewhere else is moved back to its place
    try {
      const l = e.location;
      const d = Math.hypot(l.x - p.pos.x, l.y - p.pos.y, l.z - p.pos.z);
      if (d > 1.5) {
        p.offsite = Math.round(d);
        console.warn(`[anatomy] ${p.key} appeared ${p.offsite} blocks from its place (${Math.round(l.x)},${Math.round(l.y)},${Math.round(l.z)}); moving it back`);
        e.teleport(p.pos);
      }
    } catch {
      /* ignore */
    }
    this.apply(p, e);
    try {
      p.init?.(e);
    } catch (err) {
      console.warn(`[anatomy] ${p.key}: init failed (${String(err)})`);
    }
    return e;
  }

  /** Fallback: the /summon command, then adopt the new entity. Sets p.lastError on failure. */
  private summon(p: Part): Entity | undefined {
    const f = (v: number) => (Math.round(v * 100) / 100).toString();
    try {
      const r = this.dim.runCommand(`summon ${p.type} ${f(p.pos.x)} ${f(p.pos.y)} ${f(p.pos.z)}`);
      if (!r.successCount) {
        p.lastError = "no entity created";
        return undefined;
      }
    } catch (err) {
      p.lastError = describeError(err);
      return undefined;
    }
    try {
      const found = this.dim.getEntities({ type: p.type, location: p.pos, maxDistance: 4 }).filter((x) => !this.owner.has(x.id));
      if (found.length) return found[0];
      // created, but not where it was asked to be: take the nearest unowned one
      const any = this.dim.getEntities({ type: p.type }).filter((x) => !this.owner.has(x.id));
      any.sort((a, b) => Math.hypot(a.location.x - p.pos.x, a.location.z - p.pos.z) - Math.hypot(b.location.x - p.pos.x, b.location.z - p.pos.z));
      if (any.length) return any[0];
      p.lastError = "summon reported success but no entity was found";
      p.noSummon = true;
    } catch (err) {
      p.lastError = describeError(err);
    }
    return undefined;
  }
}
