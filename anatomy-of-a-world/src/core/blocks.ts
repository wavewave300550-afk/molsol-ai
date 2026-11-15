/**
 * Budgeted block editing. All terrain changes in the arenas go through a
 * BlockWriter so a single tick never stalls the server: operations are queued
 * and flushed with a per-tick budget, newer writes to the same position win.
 */
import { BlockPermutation, BlockVolume, Dimension } from "@minecraft/server";
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

export class BlockWriter {
  private queue = new Map<string, number>();
  private order: string[] = [];
  failures = 0;
  written = 0;

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

  /** Write immediately (bypasses the queue, still counts as a write). */
  now(x: number, y: number, z: number, b: number): boolean {
    if (b === KEEP) return true;
    const k = key(x, y, z);
    if (this.queue.has(k)) this.queue.delete(k);
    return this.put(x, y, z, b);
  }

  private put(x: number, y: number, z: number, b: number): boolean {
    try {
      this.dim.setBlockPermutation({ x, y, z }, perm(b));
      this.written++;
      return true;
    } catch {
      this.failures++;
      return false;
    }
  }

  /** Flush up to `budget` queued writes. Returns how many were written. */
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

  clear(): void {
    this.queue.clear();
    this.order = [];
  }
}

/**
 * Fill a box with air (or a palette block) in chunks of at most 32768 blocks.
 * Returns the number of fill calls that failed (unloaded chunks).
 */
export function fillBox(dim: Dimension, x0: number, y0: number, z0: number, x1: number, y1: number, z1: number, b = AIR): number {
  let failed = 0;
  const p = perm(b);
  const sx = x1 - x0 + 1;
  const sz = z1 - z0 + 1;
  const layer = sx * sz;
  const maxLayers = Math.max(1, Math.floor(32768 / Math.max(1, layer)));
  if (layer > 32768) {
    // split along x
    const stepX = Math.max(1, Math.floor(32768 / (sz * (y1 - y0 + 1))));
    for (let x = x0; x <= x1; x += stepX) failed += fillBox(dim, x, y0, z0, Math.min(x1, x + stepX - 1), y1, z1, b);
    return failed;
  }
  for (let y = y0; y <= y1; y += maxLayers) {
    try {
      dim.fillBlocks(new BlockVolume({ x: x0, y, z: z0 }, { x: x1, y: Math.min(y1, y + maxLayers - 1), z: z1 }), p, { ignoreChunkBoundErrors: true });
    } catch {
      failed++;
    }
  }
  return failed;
}
