import type { EntityDieAfterEvent, Player } from "@minecraft/server";
import type { ManagedCreature } from "../creatures/types.js";

/** One phase of a boss encounter. All hooks are optional. */
export interface EncounterPhase {
  /** Unique within the encounter (lowercase snake_case). Persisted on the entity. */
  readonly id: string;
  /** Called when the phase is entered through a transition or at encounter start (not when a saved boss reloads). */
  onEnter?(creature: ManagedCreature, encounter: EncounterState): void;
  onTick?(creature: ManagedCreature, encounter: EncounterState): void;
  onExit?(creature: ManagedCreature, encounter: EncounterState): void;
  /** Checked every encounter tick, after onTick: return a phase id to switch to, or undefined to stay. */
  next?(creature: ManagedCreature, encounter: EncounterState): string | undefined;
}

/**
 * Multi-phase encounter rules attached to a creature definition.
 *
 * The boss health bar itself is the vanilla `minecraft:boss` component in the
 * behavior pack entity file. Use encounters/hud.ts for extra on-screen messages.
 */
export interface EncounterDefinition {
  /** Ordered phases; the first one starts when the boss spawns. */
  readonly phases: readonly EncounterPhase[];
  /** Players within this many blocks of the boss (same dimension) are participants. */
  readonly participantRadius: number;
  /**
   * Optional integer entity property (e.g. "dragon_dominion:phase") that mirrors the
   * current phase index to the client, so animations and render controllers can
   * react to it with query.property(). It must be declared in the behavior pack
   * entity with client_sync: true and a range covering every phase index.
   */
  readonly phaseProperty?: string;
  /** Called once when a new boss spawns, before the first phase's onEnter. */
  onStart?(creature: ManagedCreature, encounter: EncounterState): void;
  /** Called when the boss dies; the place to hand out rewards to participants(). */
  onDefeat?(creature: ManagedCreature, encounter: EncounterState, event: EntityDieAfterEvent): void;
}

/** Live encounter state of one boss, available as ManagedCreature.encounter. */
export interface EncounterState {
  readonly phase: EncounterPhase;
  /** Players currently within participantRadius (computed on each call). */
  participants(): Player[];
}
