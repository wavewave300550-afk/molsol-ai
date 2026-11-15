/**
 * Boss registry. Every boss of THE ANATOMY OF A WORLD plugs into the shared
 * encounter framework through a BossDefinition.
 */
import { Entity, EntityHurtAfterEvent, EntityHurtBeforeEvent, Player, ProjectileHitBlockAfterEvent, ProjectileHitEntityAfterEvent } from "@minecraft/server";
import { V3 } from "./vec.js";

export interface AtlasPage {
  number: string;
  title: string;
  subtitle: string;
  overview: string;
  anatomy: string[];
  abilities: { name: string; text: string }[];
  phases: { name: string; text: string }[];
  scale: string;
  arena: string;
  summon: string;
}

export interface SavedEncounter {
  boss: string;
  phase: number;
  data: Record<string, unknown>;
}

export interface BossEncounter {
  readonly def: BossDefinition;
  /** Human-readable state for /anatomy:boss status. */
  status(): string;
  /** Called once after construction (or with saved data when resuming after a reload). */
  begin(saved?: SavedEncounter): void;
  tick(): void;
  /** Tear everything down (blocks, entities, music, players returned). */
  stop(reason: "victory" | "defeat" | "abort"): void;
  isFinished(): boolean;
  /** Where a (re)joining player should be placed. */
  entryPoint(): { pos: V3; facing: V3 };
  serialize(): SavedEncounter;
  forcePhase(phase: number): boolean;
  forceAbility(id: string): boolean;
  killBoss(): boolean;
  onHurtBefore?(ev: EntityHurtBeforeEvent): void;
  onHurt?(ev: EntityHurtAfterEvent): void;
  onProjectileHitBlock?(ev: ProjectileHitBlockAfterEvent): void;
  onProjectileHitEntity?(ev: ProjectileHitEntityAfterEvent): void;
  onPlayerJoin?(p: Player): void;
  /** An entity was loaded from a chunk (re-bind boss parts, remove stale ones). */
  onEntityLoad?(e: Entity): void;
}

export interface BossDefinition {
  id: string;
  dimensionId: string;
  summonItem: string;
  /** Ability ids accepted by the test command. */
  abilities: readonly string[];
  atlas: AtlasPage;
  create(party: Player[]): BossEncounter;
}

const bosses = new Map<string, BossDefinition>();

export function registerBoss(def: BossDefinition): void {
  bosses.set(def.id, def);
}

export function getBoss(id: string): BossDefinition | undefined {
  return bosses.get(id);
}

export function allBosses(): BossDefinition[] {
  return [...bosses.values()];
}

export function bossForItem(itemId: string): BossDefinition | undefined {
  for (const b of bosses.values()) if (b.summonItem === itemId) return b;
  return undefined;
}
