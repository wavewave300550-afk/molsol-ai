/**
 * Budgeted block editing. All terrain changes in the arenas go through a
 * BlockWriter so a single tick never stalls the server: operations are queued
 * and flushed with a per-tick budget, newer writes to the same position win.
 *
 * Edits that land in chunks which are not loaded (the engine refuses them) are
 * deferred per chunk, in order, and replayed as soon as the chunk is loaded
 * again, so nothing is silently lost when a player is far away. Later edits to
 * a chunk with deferred work queue behind it, which keeps the order intact.
 */
import { BlockPermutation, BlockVolume, Dimension, system } from "@minecraft/server";
import { chunkLoaded } from "./chunks.js";
import { AIR, KEEP, paletteEntries } from "../gen/palette.js";

const permCache: (BlockPermutation | undefined)[] = [];

export function perm(index: number): BlockPermutation {
  let p = permCache[index];
  if (!p) {
    const e = paletteEntries()[index];
    p = BlockPermutation.resolve(e.id, e.states as Record<string, string | number | boolean> | undefined);
    permCache[index] = p;
  }
  return p;
}

const key = (x: number, y: number, z: number) => `${x},${y},${z}`;
/** Replay cost of one deferred fill (a chunk column) in block writes. */
const FILL_COST = 400;
const ck = (cx: number, cz: number) => `${cx},${cz}`;

/** Deferred operations of one chunk: [0,x,y,z,b] block writes and [1,x0,y0,z0,x1,y1,z1,b] fills, flattened. */
type OpList = number[];

export class BlockWriter {
  private queue = new Map<string, number>();
  private order: string[] = [];
  private deferred = new Map<string, OpList>();
  private loadedCache = new Map<string, boolean>();
  private cacheTick = -1;
  failures = 0;
  written = 0;
  /** Edits currently waiting for their chunk. */
  deferredOps = 0;

  constructor(
    readonly dim: Dimension,
    public budget = 1400,
  ) {}

  get pending(): number {
    return this.queue.size;
  }

  /** Queue a write (palette index). KEEP is ignored. */
  set(x: number, y: number, z: number, b: number): void {
    if (b === KEEP) return;
    const k = key(x, y, z);
    if (!this.queue.has(k)) this.order.push(k);
    this.queue.set(k, b);
  }

  /** Write immediately (bypasses the queue). Returns false when the edit had to be deferred or failed. */
  now(x: number, y: number, z: number, b: number): boolean {
    if (b === KEEP) return true;
    const k = key(x, y, z);
    if (this.queue.has(k)) this.queue.delete(k);
    return this.put(x, y, z, b);
  }

  /** Fill a box now (split at chunk borders; unloaded parts are deferred). */
  fill(x0: number, y0: number, z0: number, x1: number, y1: number, z1: number, b = AIR): void {
    if (x0 > x1) [x0, x1] = [x1, x0];
    if (y0 > y1) [y0, y1] = [y1, y0];
    if (z0 > z1) [z0, z1] = [z1, z0];
    for (let cx = x0 >> 4; cx <= x1 >> 4; cx++)
      for (let cz = z0 >> 4; cz <= z1 >> 4; cz++) {
        const ax = Math.max(x0, cx * 16);
        const bx = Math.min(x1, cx * 16 + 15);
        const az = Math.max(z0, cz * 16);
        const bz = Math.min(z1, cz * 16 + 15);
        if (!this.ready(cx, cz) || !this.fillNow(ax, y0, az, bx, y1, bz, b)) this.defer(cx, cz, [1, ax, y0, az, bx, y1, bz, b]);
      }
  }

  /** Flush up to `budget` queued writes. Returns how many were attempted. */
  flush(budget = this.budget): number {
    let n = 0;
    let i = 0;
    const order = this.order;
    while (i < order.length && n < budget) {
      const k = order[i++];
      const b = this.queue.get(k);
      if (b === undefined) continue;
      this.queue.delete(k);
      const [xs, ys, zs] = k.split(",");
      this.put(+xs, +ys, +zs, b);
      n++;
    }
    this.order = i >= order.length ? [] : order.slice(i);
    return n;
  }

  /** Flush everything synchronously (used for small, time-critical edits). */
  flushAll(): number {
    return this.flush(Number.MAX_SAFE_INTEGER);
  }

  /** Drop queued and deferred edits. */
  clear(): void {
    this.queue.clear();
    this.order = [];
    this.deferred.clear();
    this.deferredOps = 0;
  }

  // ------------------------------------------------------------------ deferred edits
  deferredChunks(): [number, number][] {
    return [...this.deferred.keys()].map((k) => k.split(",").map(Number) as [number, number]);
  }

  /** Is any deferred edit waiting inside this block rectangle? */
  hasDeferredIn(x0: number, z0: number, x1: number, z1: number): boolean {
    for (let cx = x0 >> 4; cx <= x1 >> 4; cx++) for (let cz = z0 >> 4; cz <= z1 >> 4; cz++) if (this.deferred.has(ck(cx, cz))) return true;
    return false;
  }

  /**
   * Replay deferred edits of chunks that are loaded now, at most `budget`
   * block writes (a fill counts as FILL_COST). Returns the cost replayed.
   */
  retryDeferred(budget = 1500, first: [number, number][] = []): number {
    let n = 0;
    // chunks asked for first (where players stand), then the rest in order
    const order: [string, OpList][] = [];
    const firstKeys = new Set(first.map(([cx, cz]) => ck(cx, cz)));
    for (const k of firstKeys) {
      const ops = this.deferred.get(k);
      if (ops) order.push([k, ops]);
    }
    for (const e of this.deferred) if (!firstKeys.has(e[0])) order.push(e);
    for (const [k, ops] of order) {
      if (n >= budget) break;
      const [cx, cz] = k.split(",").map(Number);
      if (!this.isLoaded(cx, cz)) continue;
      let i = 0;
      while (i < ops.length && n < budget) {
        const t = ops[i];
        let ok: boolean;
        if (t === 0) {
          ok = this.write(ops[i + 1], ops[i + 2], ops[i + 3], ops[i + 4]);
          n += 1;
        } else {
          ok = this.fillNow(ops[i + 1], ops[i + 2], ops[i + 3], ops[i + 4], ops[i + 5], ops[i + 6], ops[i + 7]);
          n += FILL_COST;
        }
        if (!ok && !this.isLoaded(cx, cz, true)) break; // unloaded again: keep the rest in order
        i += t === 0 ? 5 : 8;
        this.deferredOps--;
      }
      if (i >= ops.length) this.deferred.delete(k);
      else if (i > 0) this.deferred.set(k, ops.slice(i));
    }
    return n;
  }

  // ------------------------------------------------------------------ internals
  private put(x: number, y: number, z: number, b: number): boolean {
    const cx = x >> 4;
    const cz = z >> 4;
    if (!this.ready(cx, cz)) {
      this.defer(cx, cz, [0, x, y, z, b]);
      return false;
    }
    if (this.write(x, y, z, b)) return true;
    // the chunk unloaded during this tick: keep the edit for later
    if (!this.isLoaded(cx, cz, true)) this.defer(cx, cz, [0, x, y, z, b]);
    return false;
  }

  /** The chunk is loaded and no earlier edit waits there (a new edit queues behind waiting ones, keeping the order). */
  private ready(cx: number, cz: number): boolean {
    return !this.deferred.has(ck(cx, cz)) && this.isLoaded(cx, cz);
  }

  private write(x: number, y: number, z: number, b: number): boolean {
    try {
      this.dim.setBlockPermutation({ x, y, z }, perm(b));
      this.written++;
      return true;
    } catch {
      if (this.isLoaded(x >> 4, z >> 4, true)) this.failures++;
      return false;
    }
  }

  private fillNow(x0: number, y0: number, z0: number, x1: number, y1: number, z1: number, b: number): boolean {
    const p = perm(b);
    const layer = (x1 - x0 + 1) * (z1 - z0 + 1);
    const step = Math.max(1, Math.floor(32768 / Math.max(1, layer)));
    for (let y = y0; y <= y1; y += step) {
      try {
        this.dim.fillBlocks(new BlockVolume({ x: x0, y, z: z0 }, { x: x1, y: Math.min(y1, y + step - 1), z: z1 }), p);
      } catch {
        if (this.isLoaded(x0 >> 4, z0 >> 4, true)) {
          this.failures++;
          continue;
        }
        // unloaded mid-way: the remaining layers are deferred by the caller (refilling the done ones is harmless)
        return false;
      }
    }
    return true;
  }

  private defer(cx: number, cz: number, op: number[]): void {
    const k = ck(cx, cz);
    let ops = this.deferred.get(k);
    if (!ops) this.deferred.set(k, (ops = []));
    for (const v of op) ops.push(v);
    this.deferredOps++;
  }

  private isLoaded(cx: number, cz: number, fresh = false): boolean {
    const t = system.currentTick;
    if (t !== this.cacheTick) {
      this.loadedCache.clear();
      this.cacheTick = t;
    }
    const k = ck(cx, cz);
    let v = fresh ? undefined : this.loadedCache.get(k);
    if (v === undefined) {
      v = chunkLoaded(this.dim, cx, cz);
      this.loadedCache.set(k, v);
    }
    return v;
  }
}
