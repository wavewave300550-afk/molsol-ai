import type {
  Entity,
  EntityDieAfterEvent,
  EntityHurtAfterEvent,
  EntityInitializationCause,
} from "@minecraft/server";
import type { AbilityDefinition } from "../abilities/types.js";
import type { Cooldowns } from "../core/cooldowns.js";
import type { EncounterDefinition, EncounterState } from "../encounters/types.js";
import type { TierDefinition } from "../tiers/types.js";

/**
 * Script-side definition of one dragon or boss.
 *
 * The entity itself (health, movement, vanilla AI goals, size, loot, spawning) is
 * defined in the behavior pack JSON, and its look in the resource pack. This
 * object adds what JSON cannot express. Every hook is optional, and errors thrown
 * by hooks are caught and reported per creature.
 */
export interface CreatureDefinition {
  /** Entity identifier, "dragon_dominion:<name>"; must match the behavior pack entity file. */
  readonly typeId: string;
  /** Id of a tier from src/tiers/tiers.ts. Independent of size and appearance. */
  readonly tier: string;
  /** Run onTick (and the encounter tick) every N game ticks. Default 1. */
  readonly tickInterval?: number;
  /** Abilities this creature can use through useAbility(); ids double as cooldown keys. */
  readonly abilities?: readonly AbilityDefinition[];
  /** Multi-phase encounter rules, for bosses. */
  readonly encounter?: EncounterDefinition;

  /** A new entity entered the world (not called when a saved entity is loaded from disk). */
  onSpawn?(creature: ManagedCreature, cause: EntityInitializationCause): void;
  /** Called every `tickInterval` ticks while the entity is loaded and alive. */
  onTick?(creature: ManagedCreature): void;
  onHurt?(creature: ManagedCreature, event: EntityHurtAfterEvent): void;
  onDeath?(creature: ManagedCreature, event: EntityDieAfterEvent): void;
  /**
   * A behavior-pack entity event fired on this entity (from a component, an
   * animation controller, a timer...). This bridges JSON-driven AI and scripts.
   */
  onEntityEvent?(creature: ManagedCreature, eventId: string): void;
}

/**
 * Runtime handle for one loaded entity of a registered creature type. Its object
 * identity is stable while the entity stays loaded, so creature modules can keep
 * transient per-instance state in a WeakMap<ManagedCreature, State>.
 */
export interface ManagedCreature {
  readonly entity: Entity;
  readonly definition: CreatureDefinition;
  readonly tier: TierDefinition;
  readonly cooldowns: Cooldowns;
  /** Present when the definition has an encounter. */
  readonly encounter: EncounterState | undefined;
}
