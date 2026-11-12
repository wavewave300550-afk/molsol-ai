import type { TierDefinition } from "./types.js";

/**
 * The dragon tier hierarchy.
 *
 * Intentionally empty: tier names, count, ranks and balancing are decided by the
 * design team. Add one entry per approved tier, for example
 *   { id: "<tier_id>", rank: <number>, nameKey: "tier.dragon_dominion.<tier_id>.name" }
 * and add the matching name to resource_packs/dragon_dominion/texts/en_US.lang.
 */
export const TIERS: readonly TierDefinition[] = [];
