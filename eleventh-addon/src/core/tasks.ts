import { system } from "@minecraft/server";

/**
 * Lightweight per-tick task runner used by abilities that last several ticks
 * (zones, leaps, singularities...). A task returns `false` when finished.
 */
type Task = { name: string; step: (age: number) => boolean; age: number };

const tasks: Task[] = [];

export function addTask(name: string, step: (age: number) => boolean): void {
  tasks.push({ name, step, age: 0 });
}

export function runTasks(): void {
  for (let i = tasks.length - 1; i >= 0; i--) {
    const t = tasks[i];
    let keep = false;
    try {
      keep = t.step(t.age++);
    } catch (e) {
      console.warn(`[tribes] task ${t.name} failed: ${e}`);
      keep = false;
    }
    if (!keep) tasks.splice(i, 1);
  }
}

/** Run `fn` after `ticks` ticks, swallowing errors from entities that vanished meanwhile. */
export function later(ticks: number, fn: () => void): void {
  system.runTimeout(() => {
    try {
      fn();
    } catch (e) {
      console.warn(`[tribes] delayed action failed: ${e}`);
    }
  }, ticks);
}

export const taskCount = (): number => tasks.length;
