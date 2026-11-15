/** Shared encounter state that abilities read and act upon. */
import { Dimension, Entity, EntityDamageCause, Player } from "@minecraft/server";
import { BlockWriter } from "../../core/blocks.js";
import { TaskRunner } from "../../core/tasks.js";
import { V3 } from "../../core/vec.js";
import { MountainModel, NodeSite } from "../../gen/mountain.js";
import { DorsalTerrain } from "./terrain.js";

export type Zone = "dorsal" | "cavern" | "under" | "arrival" | "disk" | "mantle" | "shelf" | "other";

export interface LivingNode {
  site: NodeSite;
  entity: Entity;
}

export interface MMContext {
  readonly dim: Dimension;
  readonly m: MountainModel;
  readonly terrain: DorsalTerrain;
  readonly writer: BlockWriter;
  readonly tasks: TaskRunner;
  readonly phase: 1 | 2;
  /** Encounter-relative tick counter. */
  readonly now: number;
  readonly heart: Entity | undefined;
  readonly legs: Entity[];
  readonly petals: Entity[];
  /** Rib layout of the Phase 2 disk (0 or 1, changes on the re-bloom). */
  readonly layout: number;
  livingNodes(): LivingNode[];
  /** Survival/adventure players in the arena. */
  combatants(): Player[];
  /** Everyone in the arena dimension (for effects). */
  audience(): Player[];
  zoneOf(p: Player): Zone;
  /** Damage scaled by world difficulty; the heart is credited as the source. */
  hurt(p: Player, amount: number, cause: EntityDamageCause): void;
  enraged(): boolean;
  /** Open the Lithic Heart for `ticks` (Phase 2 vulnerability window). */
  exposeHeart(ticks: number): void;
  /** Is (x,z) a walkway cell of the Phase 2 disk (current layout)? */
  isWalkway(x: number, z: number): boolean;
  /** Block value of the pristine body at a position (palette index) - used to restore edits. */
  originalBlock(x: number, y: number, z: number): number;
  /** Register a slab in flight so the impact handler can resolve it. */
  trackSlab(e: Entity, target: V3, landTick: number, power: number): void;
  readonly rng: () => number;
}
