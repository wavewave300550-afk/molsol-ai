/**
 * Tick-based cooldown tracker (20 game ticks = 1 second).
 *
 * Every managed creature owns one instance (ManagedCreature.cooldowns); ability ids
 * are used as its keys. Create separate instances for cooldowns that are shared
 * across entities. State lives in memory only and resets when the entity unloads.
 */
export class Cooldowns {
  private readonly readyAt = new Map<string, number>();

  constructor(private readonly now: () => number) {}

  isReady(key: string): boolean {
    return this.remaining(key) === 0;
  }

  /** Ticks left before `key` is ready; 0 when it is ready. */
  remaining(key: string): number {
    const at = this.readyAt.get(key);
    if (at === undefined) return 0;
    const left = at - this.now();
    if (left > 0) return left;
    this.readyAt.delete(key);
    return 0;
  }

  /** Puts `key` on cooldown for `ticks` game ticks, replacing any running cooldown. */
  start(key: string, ticks: number): void {
    if (!Number.isInteger(ticks) || ticks < 0) {
      throw new RangeError(`cooldown "${key}" needs a non-negative integer tick count, got ${ticks}`);
    }
    if (ticks === 0) this.readyAt.delete(key);
    else this.readyAt.set(key, this.now() + ticks);
  }

  /** Clears one cooldown, or every cooldown when no key is given. */
  clear(key?: string): void {
    if (key === undefined) this.readyAt.clear();
    else this.readyAt.delete(key);
  }
}
