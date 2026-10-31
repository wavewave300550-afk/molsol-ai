/**
 * Tiny per-tick task runner for multi-tick effects (zones, falling hazards,
 * rituals). A task returns false when it is finished. Errors are contained.
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
      console.warn(`[legends] task ${t.name} failed: ${e}`);
      keep = false;
    }
    if (!keep) tasks.splice(i, 1);
  }
}

export const taskCount = (): number => tasks.length;
export const clearTasks = (): void => {
  tasks.length = 0;
};
