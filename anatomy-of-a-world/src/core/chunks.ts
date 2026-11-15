/**
 * Chunk loading. spawnEntity, setBlockPermutation and fillBlocks only work in
 * loaded, ticking chunks, and script ticking areas share an undocumented
 * per-pack chunk budget (TickingAreaManager.maxChunkCount). Arenas therefore
 * never assume their whole area can be kept loaded:
 *   - AreaKeeper keeps regions ticking in priority order as far as the budget
 *     allows, always leaving a reserve for short-lived areas;
 *   - sweepDeferred() briefly loads the regions where block edits are still
 *     waiting (BlockWriter defers edits in unloaded chunks).
 */
import { Dimension, system, world } from "@minecraft/server";
import { Co } from "./tasks.js";
import { V3 } from "./vec.js";

/** Inclusive rectangle of chunk coordinates. */
export interface ChunkRect {
  cx0: number;
  cz0: number;
  cx1: number;
  cz1: number;
}

export const chunkOf = (v: number): number => Math.floor(v / 16);

/** Chunks touched by a block-coordinate rectangle. */
export function rectOf(x0: number, z0: number, x1: number, z1: number): ChunkRect {
  return { cx0: chunkOf(Math.min(x0, x1)), cz0: chunkOf(Math.min(z0, z1)), cx1: chunkOf(Math.max(x0, x1)), cz1: chunkOf(Math.max(z0, z1)) };
}

export const rectChunks = (r: ChunkRect): number => (r.cx1 - r.cx0 + 1) * (r.cz1 - r.cz0 + 1);

export function chunkLoaded(dim: Dimension, cx: number, cz: number): boolean {
  try {
    return dim.isChunkLoaded({ x: cx * 16 + 8, y: 100, z: cz * 16 + 8 });
  } catch {
    return false;
  }
}

export function pointLoaded(dim: Dimension, p: V3): boolean {
  try {
    return dim.isChunkLoaded({ x: Math.floor(p.x), y: Math.floor(p.y), z: Math.floor(p.z) });
  } catch {
    return false;
  }
}

export function rectLoaded(dim: Dimension, r: ChunkRect): boolean {
  for (let cx = r.cx0; cx <= r.cx1; cx++) for (let cz = r.cz0; cz <= r.cz1; cz++) if (!chunkLoaded(dim, cx, cz)) return false;
  return true;
}

function areaOptions(dim: Dimension, r: ChunkRect) {
  return { dimension: dim, from: { x: r.cx0 * 16, y: 0, z: r.cz0 * 16 }, to: { x: r.cx1 * 16 + 15, y: 255, z: r.cz1 * 16 + 15 } };
}

/** The engine's chunk budget for this pack's ticking areas (undefined when not reported). */
export function chunkBudget(): { used: number; max: number | undefined } {
  try {
    const tam = world.tickingAreaManager;
    const max = tam.maxChunkCount;
    return { used: tam.chunkCount, max: Number.isFinite(max) && max > 0 ? max : undefined };
  } catch {
    return { used: 0, max: undefined };
  }
}

/** Chunks always left free for short-lived areas. */
function reserveChunks(): number {
  const { max } = chunkBudget();
  if (max === undefined) return 4;
  return Math.max(1, Math.min(16, Math.floor(max / 5)));
}

function split(r: ChunkRect): [ChunkRect, ChunkRect] {
  if (r.cx1 - r.cx0 >= r.cz1 - r.cz0) {
    const m = Math.floor((r.cx0 + r.cx1) / 2);
    return [
      { ...r, cx1: m },
      { ...r, cx0: m + 1 },
    ];
  }
  const m = Math.floor((r.cz0 + r.cz1) / 2);
  return [
    { ...r, cz1: m },
    { ...r, cz0: m + 1 },
  ];
}

/** Keeps a prioritised list of regions ticking for the duration of an encounter, as far as the budget allows. */
export class AreaKeeper {
  private ids: string[] = [];
  private covered = new Set<string>();
  private requested = new Set<string>();
  private serial = 0;
  private reserve = 0;
  /** Chunks kept ticking. */
  kept = 0;

  /** Distinct chunks asked for. */
  get wanted(): number {
    return this.requested.size;
  }

  constructor(
    readonly prefix: string,
    readonly dim: Dimension,
  ) {}

  /** Drop every ticking area this pack created (stale areas from an interrupted session included). */
  static releaseAll(): void {
    try {
      world.tickingAreaManager.removeAllTickingAreas();
    } catch {
      /* ignore */
    }
  }

  /**
   * Keep `rects` ticking, highest priority first. Regions that do not fit are
   * split until single chunks; whatever still does not fit is skipped.
   * Resolves once every created area has loaded.
   */
  keep(rects: ChunkRect[]): Promise<void> {
    const waits: Promise<unknown>[] = [];
    // no reserve is needed when everything fits: nothing will wait for a chunk then
    const all = new Set<string>();
    for (const r of rects) for (let cx = r.cx0; cx <= r.cx1; cx++) for (let cz = r.cz0; cz <= r.cz1; cz++) all.add(`${cx},${cz}`);
    const { used, max } = chunkBudget();
    this.reserve = max !== undefined && used + all.size <= max ? 0 : reserveChunks();
    for (const r of rects) for (const piece of this.uncovered(r)) this.request(piece, waits);
    return Promise.all(waits).then(() => undefined);
  }

  private request(r: ChunkRect, waits: Promise<unknown>[]): void {
    const n = rectChunks(r);
    for (let cx = r.cx0; cx <= r.cx1; cx++) for (let cz = r.cz0; cz <= r.cz1; cz++) this.requested.add(`${cx},${cz}`);
    if (this.fits(r)) {
      const id = `${this.prefix}_${this.serial++}`;
      try {
        const tam = world.tickingAreaManager;
        if (tam.hasTickingArea(id)) tam.removeTickingArea(id);
        waits.push(tam.createTickingArea(id, areaOptions(this.dim, r)).catch((e) => console.warn(`[anatomy] ticking area ${id} did not load: ${String(e)}`)));
        this.ids.push(id);
        for (let cx = r.cx0; cx <= r.cx1; cx++) for (let cz = r.cz0; cz <= r.cz1; cz++) this.covered.add(`${cx},${cz}`);
        this.kept += n;
        return;
      } catch (e) {
        console.warn(`[anatomy] ticking area ${id} refused: ${String(e)}`);
      }
    }
    if (n === 1) return;
    const [a, b] = split(r);
    this.request(a, waits);
    this.request(b, waits);
  }

  private fits(r: ChunkRect): boolean {
    try {
      if (!world.tickingAreaManager.hasCapacity(areaOptions(this.dim, r))) return false;
    } catch {
      return false;
    }
    const { used, max } = chunkBudget();
    return max === undefined || used + rectChunks(r) + this.reserve <= max;
  }

  /** The chunks of `r` not covered yet, as row runs merged into rectangles. */
  private uncovered(r: ChunkRect): ChunkRect[] {
    const out: ChunkRect[] = [];
    let open: ChunkRect[] = [];
    for (let cz = r.cz0; cz <= r.cz1; cz++) {
      const runs: [number, number][] = [];
      let start: number | undefined;
      for (let cx = r.cx0; cx <= r.cx1 + 1; cx++) {
        const free = cx <= r.cx1 && !this.covered.has(`${cx},${cz}`);
        if (free && start === undefined) start = cx;
        if (!free && start !== undefined) {
          runs.push([start, cx - 1]);
          start = undefined;
        }
      }
      const next: ChunkRect[] = [];
      for (const [a, b] of runs) {
        const prev = open.find((o) => o.cx0 === a && o.cx1 === b);
        if (prev) {
          prev.cz1 = cz;
          next.push(prev);
        } else next.push({ cx0: a, cx1: b, cz0: cz, cz1: cz });
      }
      for (const o of open) if (!next.includes(o)) out.push(o);
      open = next;
    }
    return out.concat(open);
  }

  release(): void {
    const tam = world.tickingAreaManager;
    for (const id of this.ids.splice(0))
      try {
        if (tam.hasTickingArea(id)) tam.removeTickingArea(id);
      } catch {
        /* ignore */
      }
    this.covered.clear();
    this.requested.clear();
    this.kept = 0;
  }
}

/** Wait (inside a coroutine) for a promise, at most `timeout` ticks. */
export function* awaitPromise<T>(p: Promise<T>, timeout: number): Generator<number, { done: boolean; value?: T }, void> {
  const r: { done: boolean; value?: T } = { done: false };
  p.then(
    (v) => {
      r.done = true;
      r.value = v;
    },
    () => {
      r.done = true;
    },
  );
  for (let t = 0; t < timeout && !r.done; t += 2) yield 2;
  return r;
}

/** Anything that can report and replay deferred block edits (BlockWriter). */
export interface DeferredWork {
  readonly dim: Dimension;
  /** Chunks that still have deferred edits, oldest first. */
  deferredChunks(): [number, number][];
  /** Replay deferred edits in chunks that are loaded now (at most `budget` edits). */
  retryDeferred(budget?: number): number;
}

export interface SweepOptions {
  /** Only sweep chunks inside this rectangle (returns once none of them waits). */
  focus?: ChunkRect;
  /** Give up early (releasing the area), e.g. when a more urgent sweep needs the capacity. */
  abort?: () => boolean;
}

/**
 * Load the chunks that still have deferred block edits, a few at a time, with a
 * short-lived ticking area, and replay the edits. Returns when nothing is left
 * or after `timeout` ticks. Chunks that cannot be loaded are left for later
 * (they replay as soon as a player comes close).
 */
export function* sweepDeferred(work: DeferredWork, id: string, timeout = 1200, opts: SweepOptions = {}): Co {
  const tam = world.tickingAreaManager;
  const skip = new Set<string>();
  const t0 = system.currentTick;
  const focus = opts.focus;
  const stop = () => opts.abort?.() ?? false;
  const inFocus = ([x, z]: [number, number]) => !focus || (x >= focus.cx0 && x <= focus.cx1 && z >= focus.cz0 && z <= focus.cz1);
  while (system.currentTick - t0 < timeout && !stop()) {
    work.retryDeferred();
    const todo = work.deferredChunks().filter(inFocus);
    if (!todo.length) return;
    const next = todo.find(([x, z]) => !skip.has(`${x},${z}`));
    if (!next) {
      // everything left failed to load once: wait a little (players or freed areas may load it)
      skip.clear();
      yield 40;
      continue;
    }
    const [cx, cz] = next;
    let rect: ChunkRect | undefined;
    for (const s of [4, 3, 2, 1]) {
      const r = { cx0: cx, cz0: cz, cx1: cx + s - 1, cz1: cz + s - 1 };
      try {
        if (tam.hasCapacity(areaOptions(work.dim, r))) {
          rect = r;
          break;
        }
      } catch {
        /* try smaller */
      }
    }
    if (!rect) {
      yield 40;
      continue;
    }
    let started: Promise<void> | undefined;
    try {
      if (tam.hasTickingArea(id)) tam.removeTickingArea(id);
      started = tam.createTickingArea(id, areaOptions(work.dim, rect));
    } catch (e) {
      console.warn(`[anatomy] sweep area refused: ${String(e)}`);
    }
    if (started) {
      yield* awaitPromise(started, 200);
      // replay what is reachable now, spread over ticks (a chunk can hold thousands of edits)
      const inRect = () => work.deferredChunks().some(([x, z]) => x >= rect!.cx0 && x <= rect!.cx1 && z >= rect!.cz0 && z <= rect!.cz1);
      for (let k = 0; k < 400 && inRect() && !stop(); k++) {
        if (work.retryDeferred(2000) === 0) break;
        yield 1;
      }
      try {
        if (tam.hasTickingArea(id)) tam.removeTickingArea(id);
      } catch {
        /* ignore */
      }
    }
    if (work.deferredChunks().some(([x, z]) => x === cx && z === cz)) skip.add(`${cx},${cz}`);
    yield 1;
  }
}
