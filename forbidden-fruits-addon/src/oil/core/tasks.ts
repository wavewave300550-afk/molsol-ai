import { system } from "@minecraft/server";

/**
 * Per-tick task runner for multi-tick abilities (thrusts, bolts, clouds...).
 * A task returns `false` when it is finished; errors end the task instead of the loop.
 */
type Task = { name: string; step: (age: number) => boolean; age: number };

const tasks: Task[] = [];
/** Hard cap so a misbehaving script can never pile up unbounded work. */
const MAX_TASKS = 256;

export function addTask(name: string, step: (age: number) => boolean): boolean {
  if (tasks.length >= MAX_TASKS) {
    console.warn(`[sekiyu] task limit reached, dropping ${name}`);
    return false;
  }
  tasks.push({ name, step, age: 0 });
  return true;
}

export function runTasks(): void {
  for (let i = tasks.length - 1; i >= 0; i--) {
    const t = tasks[i];
    let keep = false;
    try {
      keep = t.step(t.age++);
    } catch (e) {
      console.warn(`[sekiyu] task ${t.name} failed: ${e}`);
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
      console.warn(`[sekiyu] delayed action failed: ${e}`);
    }
  }, ticks);
}

export const taskCount = (): number => tasks.length;
