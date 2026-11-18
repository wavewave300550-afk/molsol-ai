/**
 * AttackScheduler - weighted, cooldown-aware attack selection.
 *
 * Each boss supplies its own tactical weights (distance, arena position, phase,
 * helpers alive...). The scheduler adds what is common to all of them: per-attack
 * cooldowns, a penalty for recent repeats so sequences do not degenerate, a small
 * boost for attacks that have not been seen for a while, and the rule that the
 * signature ultimate never opens a fight.
 */
import { difficulty } from "../config";
import type { AttackDef } from "./boss";
import type { Encounter } from "./encounter";
import { trace } from "./trace";

const HISTORY = 4;
/** Ticks an available attack may go unused before the starvation guard starts to favour it. */
const STARVED = 900;

export class AttackScheduler {
  private readyAt = new Map<string, number>();
  private lastUsed = new Map<string, number>();
  private recent: string[] = [];
  /** Executions per attack id (asserted on by tests). */
  readonly usage = new Map<string, number>();
  /** Force the next pick (debug command / tests). */
  forced: string | undefined;

  constructor(private readonly enc: Encounter) {}

  cooldownOf(a: AttackDef): number {
    const cd = typeof a.cooldown === "number" ? a.cooldown : a.cooldown[this.enc.phase - 1];
    return Math.round(cd * (a.ultimate ? 1 : difficulty().attackGap));
  }

  ready(a: AttackDef): boolean {
    return this.enc.timeline.now >= (this.readyAt.get(a.id) ?? 0);
  }

  /** Delay the first use of an attack (e.g. ultimates at fight start and after a phase change). */
  hold(a: AttackDef, ticks: number): void {
    this.readyAt.set(a.id, Math.max(this.readyAt.get(a.id) ?? 0, this.enc.timeline.now + ticks));
  }

  choose(attacks: readonly AttackDef[]): AttackDef | undefined {
    const now = this.enc.timeline.now;
    if (this.forced) {
      const f = attacks.find((a) => a.id === this.forced);
      this.forced = undefined;
      if (f) return f;
    }
    const pick = this.enc.rng.weighted(attacks, (a) => {
      if (!this.ready(a)) return 0;
      let w = a.weight(this.enc);
      if (w <= 0) return 0;
      const last = this.recent[this.recent.length - 1];
      if (a.id === last) w *= 0.12;
      else if (this.recent.includes(a.id)) w *= 0.55;
      const idle = now - (this.lastUsed.get(a.id) ?? -600);
      w *= 1 + Math.min(1.5, idle / 800);
      // starvation guard: an attack that has waited a long time moves to the front of the queue,
      // so every fight shows the whole move set however the players happen to stand
      if (idle > STARVED) w *= 1 + (idle - STARVED) / 150;
      return w;
    });
    return pick;
  }

  commit(a: AttackDef): void {
    const now = this.enc.timeline.now;
    this.readyAt.set(a.id, now + this.cooldownOf(a));
    this.lastUsed.set(a.id, now);
    this.recent.push(a.id);
    if (this.recent.length > HISTORY) this.recent.shift();
    this.usage.set(a.id, (this.usage.get(a.id) ?? 0) + 1);
    trace("attack", { boss: this.enc.key, id: a.id, phase: this.enc.phase, tick: now });
  }

  /** The attack has ended (finished or cancelled): its cooldown runs from now. */
  release(a: AttackDef): void {
    this.readyAt.set(a.id, this.enc.timeline.now + this.cooldownOf(a));
  }

  /** After a phase change: shorten remaining cooldowns so the new phase opens actively. */
  refresh(maxRemaining: number): void {
    const now = this.enc.timeline.now;
    for (const [id, at] of this.readyAt) this.readyAt.set(id, Math.min(at, now + maxRemaining));
    this.recent = [];
  }
}
