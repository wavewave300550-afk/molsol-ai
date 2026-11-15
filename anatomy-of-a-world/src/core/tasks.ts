/**
 * Tick-driven coroutines. Encounter logic (telegraph -> strike -> recover) is
 * written as generator functions that `yield n` to wait n ticks.
 */
export type Co = Generator<number | void, void, void>;

export interface Task {
  readonly name: string;
  done: boolean;
  cancel(): void;
}

interface Running extends Task {
  gen: Co;
  wait: number;
  onError?: (e: unknown) => void;
}

export class TaskRunner {
  private tasks: Running[] = [];

  start(name: string, gen: Co, onError?: (e: unknown) => void): Task {
    const t: Running = {
      name,
      gen,
      wait: 0,
      done: false,
      onError,
      cancel() {
        if (this.done) return;
        this.done = true;
        try {
          gen.return(undefined);
        } catch {
          /* generator cleanup errors are ignored */
        }
      },
    };
    this.tasks.push(t);
    return t;
  }

  /** Advance every task by one tick. Tasks started during the tick run from the next tick. */
  tick(): void {
    const list = this.tasks.slice();
    for (let i = 0; i < list.length; i++) {
      const t = list[i];
      if (t.done) continue;
      if (t.wait > 0) {
        t.wait--;
        continue;
      }
      try {
        const r = t.gen.next();
        if (r.done) t.done = true;
        else t.wait = Math.max(0, (typeof r.value === "number" ? r.value : 1) - 1);
      } catch (e) {
        t.done = true;
        if (t.onError) t.onError(e);
        else console.error(`[anatomy] task ${t.name} failed: ${String(e)}${e instanceof Error && e.stack ? "\n" + e.stack : ""}`);
      }
    }
    if (this.tasks.some((t) => t.done)) this.tasks = this.tasks.filter((t) => !t.done);
  }

  count(prefix?: string): number {
    return this.tasks.filter((t) => !t.done && (!prefix || t.name.startsWith(prefix))).length;
  }

  /** Cancel tasks (they are pruned at the end of the current/next tick). */
  cancelAll(prefix?: string): void {
    for (const t of this.tasks.slice()) if (!prefix || t.name.startsWith(prefix)) t.cancel();
  }
}

/** Wait helper for readability inside coroutines: `yield* wait(20)`. */
export function* wait(ticks: number): Co {
  if (ticks > 0) yield ticks;
}
