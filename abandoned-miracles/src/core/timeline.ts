/**
 * Encounter-local scheduler.
 *
 * Every delayed effect of a fight (telegraph -> strike, beat -> beat) is a task
 * on the owning encounter's Timeline. Nothing uses system.runTimeout, so when an
 * encounter ends, resets or its boss unloads, cancelAll() provably leaves no
 * pending hazard behind.
 */
import { report } from "./trace";

interface Task {
  at: number;
  seq: number;
  tag: string;
  fn: () => void;
}

export class Timeline {
  /** Ticks processed by this encounter (not world time). */
  now = 0;
  private tasks: Task[] = [];
  private seq = 0;

  at(tick: number, fn: () => void, tag = ""): void {
    const t: Task = { at: Math.max(this.now + 1, Math.round(tick)), seq: this.seq++, tag, fn };
    // insertion sort keeps the queue ordered by (at, seq); queues are short
    let i = this.tasks.length;
    while (i > 0 && (this.tasks[i - 1].at > t.at)) i--;
    this.tasks.splice(i, 0, t);
  }

  after(delay: number, fn: () => void, tag = ""): void {
    this.at(this.now + Math.max(1, Math.round(delay)), fn, tag);
  }

  /** Cancel every task whose tag equals `tag` or starts with `tag + ":"`. */
  cancel(tag: string): number {
    const before = this.tasks.length;
    const prefix = tag + ":";
    this.tasks = this.tasks.filter((t) => t.tag !== tag && !t.tag.startsWith(prefix));
    return before - this.tasks.length;
  }

  cancelAll(): number {
    const n = this.tasks.length;
    this.tasks = [];
    return n;
  }

  pending(tag?: string): number {
    if (tag === undefined) return this.tasks.length;
    const prefix = tag + ":";
    return this.tasks.filter((t) => t.tag === tag || t.tag.startsWith(prefix)).length;
  }

  /** Advance one tick and run everything that is due. */
  step(): void {
    this.now++;
    let guard = 4096;
    while (this.tasks.length > 0 && this.tasks[0].at <= this.now && guard-- > 0) {
      const t = this.tasks.shift() as Task;
      try {
        t.fn();
      } catch (e) {
        report(`timeline task ${t.tag}`, e);
      }
    }
  }
}
