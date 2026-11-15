/**
 * Lightweight tick scheduler for multi-stage abilities.  Tasks are owned by a player id
 * so everything a player started can be cancelled at once (death, logout, race change).
 * A single runInterval drives all tasks; when no task is pending it costs one array check.
 */
import { system } from "@minecraft/server";
import { warn } from "./util.js";

interface Task {
  at: number;
  fn: () => void;
  owner?: string;
  tag?: string;
  alive: boolean;
}

let queue: Task[] = [];

export function after(ticks: number, fn: () => void, owner?: string, tag?: string): Task {
  const t: Task = { at: system.currentTick + Math.max(1, Math.floor(ticks)), fn, owner, tag, alive: true };
  queue.push(t);
  return t;
}

/** Run fn(i) `times` times, every `every` ticks, starting after `delay`. */
export function repeat(every: number, times: number, fn: (i: number) => void, owner?: string, tag?: string, delay = 0): void {
  for (let i = 0; i < times; i++) {
    const k = i;
    after(Math.max(1, delay + every * i), () => fn(k), owner, tag);
  }
}

export function cancel(owner: string, tag?: string): number {
  let n = 0;
  for (const t of queue) {
    if (t.alive && t.owner === owner && (tag === undefined || t.tag === tag)) {
      t.alive = false;
      n++;
    }
  }
  return n;
}

export function pending(owner: string, tag?: string): boolean {
  return queue.some((t) => t.alive && t.owner === owner && (tag === undefined || t.tag === tag));
}

export function startScheduler(): void {
  system.runInterval(() => {
    if (queue.length === 0) return;
    const now = system.currentTick;
    const due = queue.filter((t) => t.alive && t.at <= now);
    if (due.length === 0) {
      if (queue.length > 64) queue = queue.filter((t) => t.alive);
      return;
    }
    queue = queue.filter((t) => t.alive && t.at > now);
    for (const t of due) {
      try {
        t.fn();
      } catch (e) {
        warn(`task ${t.tag ?? "?"} failed`, e);
      }
    }
  }, 1);
}
