import { system } from "@minecraft/server";

/**
 * Per-tick cooperative tasks. A task is a generator that yields once per tick;
 * it finishes when the generator returns. Used for multi-tick sequences
 * (environment changes, cinematics, fragment flights...).
 */
type Task = { name: string; gen: Generator<void, void, void> };

const tasks: Task[] = [];

export function spawnTask(name: string, gen: Generator<void, void, void>): void {
  tasks.push({ name, gen });
}

export function runTasks(): void {
  for (let i = tasks.length - 1; i >= 0; i--) {
    const t = tasks[i];
    let done = true;
    try {
      done = !!t.gen.next().done;
    } catch (e) {
      console.warn(`[porcelain] task ${t.name} failed: ${e}`);
      done = true;
    }
    if (done) tasks.splice(i, 1);
  }
}

export function cancelTasks(prefix: string): void {
  for (let i = tasks.length - 1; i >= 0; i--) {
    if (tasks[i].name.startsWith(prefix)) {
      try {
        tasks[i].gen.return();
      } catch {
        // ignore
      }
      tasks.splice(i, 1);
    }
  }
}

export const taskCount = (prefix = ""): number => tasks.filter((t) => t.name.startsWith(prefix)).length;

/** Yield for `n` ticks inside a generator. */
export function* wait(n: number): Generator<void, void, void> {
  for (let i = 0; i < n; i++) yield;
}

/** Run `fn` after `ticks`, swallowing errors from entities that vanished meanwhile. */
export function later(ticks: number, fn: () => void): void {
  system.runTimeout(() => {
    try {
      fn();
    } catch (e) {
      console.warn(`[porcelain] delayed action failed: ${e}`);
    }
  }, ticks);
}
