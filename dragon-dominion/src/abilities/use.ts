import { reportContentError } from "../core/log.js";
import type { ManagedCreature } from "../creatures/types.js";
import type { AbilityResult } from "./types.js";

/**
 * Uses one of the creature's abilities if it is off cooldown and its canUse()
 * passes. The cooldown starts before execute() runs, so an ability that throws
 * still waits out its cooldown instead of failing again every tick.
 */
export function useAbility(creature: ManagedCreature, abilityId: string): AbilityResult {
  const ability = creature.definition.abilities?.find((a) => a.id === abilityId);
  if (!ability) return "unknown";
  if (!creature.cooldowns.isReady(ability.id)) return "on_cooldown";
  try {
    if (ability.canUse && !ability.canUse(creature)) return "blocked";
    creature.cooldowns.start(ability.id, ability.cooldownTicks);
    ability.execute(creature);
    return "used";
  } catch (error) {
    reportContentError(`${creature.definition.typeId} ability "${ability.id}"`, error);
    return "failed";
  }
}
