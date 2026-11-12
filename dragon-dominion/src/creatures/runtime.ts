import {
  EntityInitializationCause,
  EntityTypes,
  system,
  world,
  type DataDrivenEntityTriggerAfterEvent,
  type Entity,
  type EntityDieAfterEvent,
  type EntityHurtAfterEvent,
} from "@minecraft/server";
import { Cooldowns } from "../core/cooldowns.js";
import { guarded, logError } from "../core/log.js";
import { EncounterRuntime } from "../encounters/runtime.js";
import type { TierDefinition } from "../tiers/types.js";
import type { CreatureRegistry } from "./registry.js";
import type { CreatureDefinition, ManagedCreature } from "./types.js";

const DIMENSIONS = ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"];

class Creature implements ManagedCreature {
  readonly cooldowns = new Cooldowns(() => system.currentTick);
  encounter: EncounterRuntime | undefined;

  constructor(
    readonly entity: Entity,
    readonly definition: CreatureDefinition,
    readonly tier: TierDefinition,
    /** Spreads creatures with the same tickInterval over different ticks. */
    readonly tickOffset: number,
  ) {}
}

/**
 * Connects registered creature definitions to the world: tracks loaded entities
 * of registered types, dispatches lifecycle hooks, runs the tick loop and drives
 * encounters. With no creatures registered it subscribes to nothing.
 */
export class CreatureRuntime {
  private readonly active = new Map<string, Creature>();
  private nextOffset = 0;
  private started = false;

  constructor(
    private readonly creatures: CreatureRegistry,
    private readonly tierOf: (id: string) => TierDefinition | undefined,
  ) {}

  get activeCount(): number {
    return this.active.size;
  }

  /** The managed handle for an entity, if it is a loaded creature of a registered type. */
  get(entity: Entity): ManagedCreature | undefined {
    return this.active.get(entity.id);
  }

  start(): void {
    const entityTypes = this.creatures.typeIds();
    if (this.started || entityTypes.length === 0) return;
    this.started = true;
    world.afterEvents.worldLoad.subscribe(() => this.onWorldLoad(entityTypes));
    world.afterEvents.entitySpawn.subscribe((e) => this.onEntitySpawn(e.entity, e.cause));
    world.afterEvents.entityLoad.subscribe((e) => this.track(e.entity, undefined));
    world.afterEvents.entityRemove.subscribe((e) => this.active.delete(e.removedEntityId), { entityTypes });
    world.afterEvents.entityHurt.subscribe((e) => this.onHurt(e), { entityTypes });
    world.afterEvents.entityDie.subscribe((e) => this.onDie(e), { entityTypes });
    world.afterEvents.dataDrivenEntityTrigger.subscribe((e) => this.onEntityEvent(e), { entityTypes });
    system.runInterval(() => this.tick(), 1);
  }

  private onWorldLoad(entityTypes: string[]): void {
    for (const typeId of entityTypes) {
      if (!EntityTypes.get(typeId)) {
        logError(`creature "${typeId}" is registered in scripts but the behavior pack defines no such entity`);
      }
    }
    // Entities in chunks loaded before the subscriptions were active.
    for (const dimensionId of DIMENSIONS) {
      const dimension = world.getDimension(dimensionId);
      for (const typeId of entityTypes) {
        for (const entity of dimension.getEntities({ type: typeId })) this.track(entity, undefined);
      }
    }
  }

  private onEntitySpawn(entity: Entity, cause: EntityInitializationCause): void {
    if (!entity.isValid) return;
    this.track(entity, cause === EntityInitializationCause.Loaded ? undefined : cause);
  }

  /** `spawnCause` is undefined for entities loaded from disk. */
  private track(entity: Entity, spawnCause: EntityInitializationCause | undefined): void {
    const definition = this.creatures.get(entity.typeId);
    if (!definition || this.active.has(entity.id)) return;
    const tier = this.tierOf(definition.tier);
    if (!tier) return; // unreachable: the registry rejects unknown tiers
    const creature = new Creature(entity, definition, tier, this.nextOffset++);
    if (definition.encounter) creature.encounter = new EncounterRuntime(creature, definition.encounter);
    this.active.set(entity.id, creature);

    if (spawnCause === undefined) {
      creature.encounter?.resume();
      return;
    }
    const { onSpawn } = definition;
    if (onSpawn) guarded(`${definition.typeId} onSpawn`, () => onSpawn(creature, spawnCause));
    if (entity.isValid) creature.encounter?.begin();
  }

  private tick(): void {
    const now = system.currentTick;
    for (const [id, creature] of this.active) {
      if (!creature.entity.isValid) {
        this.active.delete(id);
        continue;
      }
      const { definition } = creature;
      if ((now + creature.tickOffset) % (definition.tickInterval ?? 1) !== 0) continue;
      creature.encounter?.tick();
      const { onTick } = definition;
      if (onTick && creature.entity.isValid) guarded(`${definition.typeId} onTick`, () => onTick(creature));
    }
  }

  private onHurt(event: EntityHurtAfterEvent): void {
    const creature = this.active.get(event.hurtEntity.id);
    const onHurt = creature?.definition.onHurt;
    if (creature && onHurt) guarded(`${creature.definition.typeId} onHurt`, () => onHurt(creature, event));
  }

  private onDie(event: EntityDieAfterEvent): void {
    const creature = this.active.get(event.deadEntity.id);
    if (!creature) return;
    this.active.delete(event.deadEntity.id); // no more ticks while the death animation plays
    const { onDeath } = creature.definition;
    if (onDeath) guarded(`${creature.definition.typeId} onDeath`, () => onDeath(creature, event));
    creature.encounter?.defeat(event);
  }

  private onEntityEvent(event: DataDrivenEntityTriggerAfterEvent): void {
    const creature = this.active.get(event.entity.id);
    const onEntityEvent = creature?.definition.onEntityEvent;
    if (creature && onEntityEvent) {
      guarded(`${creature.definition.typeId} onEntityEvent`, () => onEntityEvent(creature, event.eventId));
    }
  }
}
