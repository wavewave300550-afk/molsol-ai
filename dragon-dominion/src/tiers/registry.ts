import { LOCAL_ID_PATTERN } from "../config.js";
import type { TierDefinition } from "./types.js";

/** Validated, rank-ordered view of the tier hierarchy. Invalid entries are skipped and listed in `problems`. */
export class TierRegistry {
  readonly problems: string[] = [];
  private readonly byId = new Map<string, TierDefinition>();
  private readonly ordered: readonly TierDefinition[];

  constructor(tiers: readonly TierDefinition[]) {
    for (const tier of tiers) {
      const label = `tier "${tier.id}"`;
      if (!LOCAL_ID_PATTERN.test(tier.id)) this.problems.push(`${label}: id must be lowercase snake_case`);
      else if (this.byId.has(tier.id)) this.problems.push(`${label}: defined more than once`);
      else if (!Number.isFinite(tier.rank)) this.problems.push(`${label}: rank must be a finite number`);
      else if (!tier.nameKey) this.problems.push(`${label}: nameKey is empty`);
      else this.byId.set(tier.id, tier);
    }
    this.ordered = [...this.byId.values()].sort((a, b) => a.rank - b.rank);
  }

  get size(): number {
    return this.byId.size;
  }

  get(id: string): TierDefinition | undefined {
    return this.byId.get(id);
  }

  /** Every tier, lowest rank first. */
  all(): readonly TierDefinition[] {
    return this.ordered;
  }

  /** Negative when tier `a` ranks below tier `b`, 0 when equal, positive when above. */
  compare(a: string, b: string): number {
    return this.require(a).rank - this.require(b).rank;
  }

  private require(id: string): TierDefinition {
    const tier = this.byId.get(id);
    if (!tier) throw new Error(`unknown tier "${id}"`);
    return tier;
  }
}
