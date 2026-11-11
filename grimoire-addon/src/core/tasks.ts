import { system } from "@minecraft/server";
import { log } from "./log";

/**
 * Tick-synchronised coroutines. A routine is a generator that yields the number of
 * ticks to wait (undefined/0 = next tick). Every spell is written as a routine, which
 * makes multi-phase spells read as a timeline while staying bounded and cancellable.
 */
export type Routine = Generator<number | void, void, unknown>;

export interface RoutineHandle {
  readonly id: number;
  readonly label: string;
  readonly ownerId?: string;
  alive: boolean;
  cancel(reason?: string): void;
  onEnd(fn: (reason: string) => void): void;
}

interface Entry {
  handle: RoutineHandle;
  gen: Routine;
  wake: number;
  ends: ((reason: string) => void)[];
  started: number;
  maxTicks: number;
}

const entries = new Map<number, Entry>();
let nextId = 1;

/** Start a routine. maxTicks is a hard safety bound so that no routine can run forever. */
export function start(gen: Routine, label: string, ownerId?: string, maxTicks = 20 * 240): RoutineHandle {
  const id = nextId++;
  const entry: Entry = {
    gen,
    wake: system.currentTick,
    ends: [],
    started: system.currentTick,
    maxTicks,
    handle: {
      id,
      label,
      ownerId,
      alive: true,
      cancel: (reason = "cancelled") => finish(entry, reason, true),
      onEnd: (fn) => {
        if (!entry.handle.alive) fn("already-ended");
        else entry.ends.push(fn);
      },
    },
  };
  entries.set(id, entry);
  // Run the first step right away so spells react on the same tick as the release.
  step(entry, system.currentTick);
  return entry.handle;
}

function finish(entry: Entry, reason: string, interrupt: boolean): void {
  if (!entry.handle.alive) return;
  entry.handle.alive = false;
  entries.delete(entry.handle.id);
  if (interrupt) {
    try {
      entry.gen.return(undefined);
    } catch (e) {
      log.error(`routine ${entry.handle.label} failed while cancelling`, e);
    }
  }
  for (const fn of entry.ends) {
    try {
      fn(reason);
    } catch (e) {
      log.error(`cleanup of ${entry.handle.label} failed`, e);
    }
  }
}

function step(entry: Entry, tick: number): void {
  if (!entry.handle.alive || tick < entry.wake) return;
  if (tick - entry.started > entry.maxTicks) {
    finish(entry, "timeout", true);
    return;
  }
  try {
    const r = entry.gen.next();
    if (r.done) {
      finish(entry, "done", false);
      return;
    }
    const w = typeof r.value === "number" && r.value > 0 ? Math.floor(r.value) : 1;
    entry.wake = tick + w;
  } catch (e) {
    log.error(`routine ${entry.handle.label} crashed`, e);
    finish(entry, "error", false);
  }
}

export function tickRoutines(tick: number): void {
  for (const entry of [...entries.values()]) step(entry, tick);
}

export function cancelOwned(ownerId: string, reason: string): void {
  for (const entry of [...entries.values()]) if (entry.handle.ownerId === ownerId) finish(entry, reason, true);
}

export function activeRoutines(): RoutineHandle[] {
  return [...entries.values()].map((e) => e.handle);
}

/** Helper for `yield* wait(n)` inside routines. */
export function* wait(ticks: number): Routine {
  if (ticks > 0) yield ticks;
}

/** Run a callback every tick for `ticks` ticks (inside a routine: `yield* every(20, t => ...)`). */
export function* repeat(ticks: number, fn: (i: number) => boolean | void, interval = 1): Routine {
  for (let i = 0; i < ticks; i += interval) {
    if (fn(i) === false) return;
    yield interval;
  }
}
