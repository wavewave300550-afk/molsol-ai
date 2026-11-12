/**
 * One level of the dragon power hierarchy.
 *
 * Tier names, the number of tiers, their order and any tier-wide rules belong to
 * the design team. This interface only fixes what the engine needs to reference a
 * tier. When the design team defines tier-wide attributes, add them here as typed
 * fields. Tiers never imply a size or an appearance: those stay in each
 * creature's own behavior/resource files.
 */
export interface TierDefinition {
  /** Permanent identifier referenced by creature definitions (lowercase snake_case). */
  readonly id: string;
  /** Position in the hierarchy: a higher rank is a higher power level. */
  readonly rank: number;
  /** Resource-pack lang key of the display name, e.g. "tier.dragon_dominion.<id>.name". */
  readonly nameKey: string;
}
