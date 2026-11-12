import type { ManagedCreature } from "../creatures/types.js";

/**
 * An attack or ability. When and on whom it is used is decided by the creature's
 * own AI (onTick, onEntityEvent, encounter phases). The framework only enforces
 * the cooldown and isolates errors.
 */
export interface AbilityDefinition {
  /** Unique within its creature (lowercase snake_case). Also the cooldown key. */
  readonly id: string;
  /** Cooldown started each time the ability is used, in game ticks (20 = 1 second). */
  readonly cooldownTicks: number;
  /** Optional extra condition (range, phase, line of sight...). Not called while on cooldown. */
  canUse?(creature: ManagedCreature): boolean;
  execute(creature: ManagedCreature): void;
}

export type AbilityResult = "used" | "on_cooldown" | "blocked" | "unknown" | "failed";
