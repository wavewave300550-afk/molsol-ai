import type { EntityDieAfterEvent, Player } from "@minecraft/server";
import { nsId } from "../config.js";
import { guarded, reportContentError } from "../core/log.js";
import type { ManagedCreature } from "../creatures/types.js";
import type { EncounterDefinition, EncounterPhase, EncounterState } from "./types.js";

/** Dynamic property holding the current phase id, so a boss resumes its phase after a reload. */
export const PHASE_DYNAMIC_PROPERTY = nsId("encounter_phase");

/** Drives the phases of one boss. Created and ticked by the creature runtime. */
export class EncounterRuntime implements EncounterState {
  private current: EncounterPhase;

  constructor(
    private readonly creature: ManagedCreature,
    private readonly definition: EncounterDefinition,
  ) {
    this.current = definition.phases[0];
  }

  get phase(): EncounterPhase {
    return this.current;
  }

  participants(): Player[] {
    const { entity } = this.creature;
    if (!entity.isValid) return [];
    return entity.dimension.getPlayers({ location: entity.location, maxDistance: this.definition.participantRadius });
  }

  /** Starts the encounter from its first phase (new boss). */
  begin(): void {
    this.current = this.definition.phases[0];
    this.persist();
    const { onStart } = this.definition;
    if (onStart) guarded(this.source("onStart"), () => onStart(this.creature, this));
    this.enter(this.current);
  }

  /** Restores the saved phase of a boss loaded from disk, or starts over if none was saved. */
  resume(): void {
    const stored = this.creature.entity.getDynamicProperty(PHASE_DYNAMIC_PROPERTY);
    const phase = typeof stored === "string" ? this.find(stored) : undefined;
    if (!phase) {
      this.begin();
      return;
    }
    this.current = phase;
    this.mirror();
  }

  tick(): void {
    const phase = this.current;
    if (phase.onTick) guarded(this.source(`phase "${phase.id}" onTick`), () => phase.onTick!(this.creature, this));
    if (!phase.next || !this.creature.entity.isValid) return;
    const nextId = guarded(this.source(`phase "${phase.id}" next`), () => phase.next!(this.creature, this));
    if (nextId === undefined || nextId === phase.id) return;
    const next = this.find(nextId);
    if (!next) {
      reportContentError(this.source(`phase "${phase.id}" next`), new Error(`unknown phase "${nextId}"`));
      return;
    }
    if (phase.onExit) guarded(this.source(`phase "${phase.id}" onExit`), () => phase.onExit!(this.creature, this));
    this.current = next;
    this.persist();
    this.enter(next);
  }

  defeat(event: EntityDieAfterEvent): void {
    const { onDefeat } = this.definition;
    if (onDefeat) guarded(this.source("onDefeat"), () => onDefeat(this.creature, this, event));
  }

  private enter(phase: EncounterPhase): void {
    if (phase.onEnter) guarded(this.source(`phase "${phase.id}" onEnter`), () => phase.onEnter!(this.creature, this));
  }

  private find(id: string): EncounterPhase | undefined {
    return this.definition.phases.find((p) => p.id === id);
  }

  private persist(): void {
    guarded(this.source("save phase"), () => this.creature.entity.setDynamicProperty(PHASE_DYNAMIC_PROPERTY, this.current.id));
    this.mirror();
  }

  private mirror(): void {
    const property = this.definition.phaseProperty;
    if (!property) return;
    const index = this.definition.phases.indexOf(this.current);
    guarded(this.source(`set property ${property}`), () => this.creature.entity.setProperty(property, index));
  }

  private source(what: string): string {
    return `${this.creature.definition.typeId} encounter ${what}`;
  }
}
