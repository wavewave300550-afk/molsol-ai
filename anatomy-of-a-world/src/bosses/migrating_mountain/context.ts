/** Shared encounter state that abilities read and act upon. */
import { Dimension, Entity, EntityDamageCause, Player } from "@minecraft/server";
import { BlockWriter } from "../../core/blocks.js";
import { Co, TaskRunner } from "../../core/tasks.js";
import { V3 } from "../../core/vec.js";
import { MountainModel, NodeSite } from "../../gen/mountain.js";
import { Island } from "./runtime.js";
import { DorsalTerrain } from "./terrain.js";

export type Zone = "dorsal" | "cavern" | "under" | "arrival" | "disk" | "mantle" | "shelf" | "other";

/** What the players stand on: the mountain (Phase 1), the unfolded disk (Phase 2 and 3A), the floating islands (3B). */
export type ArenaKind = "body" | "disk" | "islands";

/** A remaining Anchorage Root of Phase 3A. */
export interface AnchorInfo {
  k: number;
  pos: V3;
  entity?: Entity;
}

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
  readonly phase: 1 | 2 | 3;
  arena(): ArenaKind;
  /** Anchorage Roots still standing (Phase 3A). */
  anchors(): AnchorInfo[];
  /** The floating islands (Phase 3B; empty before). */
  islands(): Island[];
  /** Phase 3B: the heart is down on the centre island (melee window). */
  heartSlamming(): boolean;
  /** Direction the mountain walks in Phase 3A (unit vector in x/z). */
  readonly walkDir: { x: number; z: number };
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
  /** Set a property on a boss part and keep it applied when the part's chunk reloads. */
  partProp(e: Entity, name: string, value: boolean | number): void;
  /** Pose of every Anchorage Root (0 walk, 1 splayed, 2 collapsed). */
  setLegPose(pose: number): void;
  /** Ensure petal `k` exists and set its state (0 closed, 1 open, 2 folded, 3 dead). */
  petal(k: number, state: number): Entity | undefined;
  /** Set the state of every petal. */
  setPetals(state: number): void;
  /** Set a property of the Lithic Heart (kept while its chunk is unloaded). */
  heartProp(name: string, value: boolean | number): void;
  /** Remove the Lithic Heart for good (end of the victory sequence). */
  removeHeart(): void;
  /** Wait until queued and deferred block edits inside a rectangle are applied (loading it briefly if needed). */
  settleArea(x0: number, z0: number, x1: number, z1: number, timeout: number): Co;
  readonly rng: () => number;
}
