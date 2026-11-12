import { isOwnId, LOCAL_ID_PATTERN, NAMESPACE } from "../config.js";
import type { TierRegistry } from "../tiers/registry.js";
import type { CreatureDefinition } from "./types.js";

/** Validated lookup of creature definitions by entity type id. Invalid definitions are skipped and listed in `problems`. */
export class CreatureRegistry {
  readonly problems: string[] = [];
  private readonly byType = new Map<string, CreatureDefinition>();

  constructor(definitions: readonly CreatureDefinition[], tiers: TierRegistry) {
    for (const definition of definitions) {
      const found = checkDefinition(definition, tiers);
      if (this.byType.has(definition.typeId)) found.push(`creature "${definition.typeId}": defined more than once`);
      if (found.length > 0) this.problems.push(...found);
      else this.byType.set(definition.typeId, definition);
    }
  }

  get size(): number {
    return this.byType.size;
  }

  get(typeId: string): CreatureDefinition | undefined {
    return this.byType.get(typeId);
  }

  typeIds(): string[] {
    return [...this.byType.keys()];
  }
}

function checkDefinition(definition: CreatureDefinition, tiers: TierRegistry): string[] {
  const label = `creature "${definition.typeId}"`;
  const problems: string[] = [];
  if (!isOwnId(definition.typeId)) problems.push(`${label}: typeId must be "${NAMESPACE}:<snake_case_name>"`);
  if (!tiers.get(definition.tier)) problems.push(`${label}: unknown tier "${definition.tier}"`);
  const interval = definition.tickInterval;
  if (interval !== undefined && (!Number.isInteger(interval) || interval < 1)) {
    problems.push(`${label}: tickInterval must be a positive integer`);
  }

  const abilityIds = new Set<string>();
  for (const ability of definition.abilities ?? []) {
    if (!LOCAL_ID_PATTERN.test(ability.id)) problems.push(`${label}: ability id "${ability.id}" must be lowercase snake_case`);
    if (abilityIds.has(ability.id)) problems.push(`${label}: ability "${ability.id}" is defined more than once`);
    abilityIds.add(ability.id);
    if (!Number.isInteger(ability.cooldownTicks) || ability.cooldownTicks < 0) {
      problems.push(`${label}: ability "${ability.id}" cooldownTicks must be a non-negative integer`);
    }
  }

  const encounter = definition.encounter;
  if (encounter) {
    if (encounter.phases.length === 0) problems.push(`${label}: encounter needs at least one phase`);
    const phaseIds = new Set<string>();
    for (const phase of encounter.phases) {
      if (!LOCAL_ID_PATTERN.test(phase.id)) problems.push(`${label}: phase id "${phase.id}" must be lowercase snake_case`);
      if (phaseIds.has(phase.id)) problems.push(`${label}: phase "${phase.id}" is defined more than once`);
      phaseIds.add(phase.id);
    }
    if (!Number.isFinite(encounter.participantRadius) || encounter.participantRadius <= 0) {
      problems.push(`${label}: encounter participantRadius must be a positive number`);
    }
    if (encounter.phaseProperty !== undefined && !isOwnId(encounter.phaseProperty)) {
      problems.push(`${label}: encounter phaseProperty must be "${NAMESPACE}:<snake_case_name>"`);
    }
  }
  return problems;
}
