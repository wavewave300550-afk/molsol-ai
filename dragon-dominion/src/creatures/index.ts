import type { CreatureDefinition } from "./types.js";

/**
 * Every creature shipped by the add-on.
 *
 * Intentionally empty until the design team approves the first creature. Each
 * creature lives in its own folder, src/creatures/<creature_name>/, and is listed
 * here with one import, for example:
 *   import { CREATURE } from "./<creature_name>/definition.js";
 *   export const CREATURES = [CREATURE];
 * See docs/ADDING_A_CREATURE.md.
 */
export const CREATURES: readonly CreatureDefinition[] = [];
