import { EntityHurtBeforeEvent, Player } from "@minecraft/server";
import { EndReason, Session } from "../core/session.js";

export interface CastContext {
  p: Player;
  s: Session;
  race: RaceDef;
  ability: AbilityDef;
}

/** Returning a string means "failed: <reason>" (no cooldown is spent). */
export type CastResult = true | string;

export interface AbilityDef {
  id: string; // stable id, used for persisted cooldowns
  name: string;
  short: string; // HUD label
  cooldown: number; // seconds (balance baseline)
  charges?: number; // max stored charges (default 1)
  desc: string;
  original?: string; // what the creator's brief specified (for the in-game codex)
  range?: number; // for the targeting reticle
  cone?: number; // aim-assist cone for the reticle (degrees, default 14)
  needsTarget?: boolean;
  /** Unique ultimate (shown with its own styling in the Codex and HUD). */
  ultimate?: boolean;
  /** Pre-check; return a reason string to block casting. */
  check?(c: CastContext): string | undefined;
  cast(c: CastContext): CastResult;
  /** Extra charges (e.g. Blood Moon). */
  maxCharges?(c: CastContext): number;
}

export interface Passive {
  name: string;
  desc: string;
}

/** "unique" lineages have more elaborate systems, a signature ultimate and (by default) one holder per world. */
export type Rarity = "normal" | "unique";

export interface RaceDef {
  code: string; // permanent identifier "001", "002", ...
  key: string; // salamander | golem | jackalope | xenentoma | spaghetti | nurariten
  name: string;
  thai: string; // original Thai name from the design brief (shown in docs)
  title: string; // short epithet
  color: string; // § colour code
  tagline: string;
  lore: string[];
  strengths: string[];
  weaknesses: string[];
  passives: Passive[];
  abilities: AbilityDef[];
  focusItem: string;
  focusName: string; // display name of the focus item
  rarity?: Rarity; // default "normal"
  /** Extra control hints for the Codex (race-specific inputs). */
  controls?: string[];
  /** Visual form variant the race shows right now (crest item suffix, "" = base). */
  variant(p: Player, s: Session): string;
  /** Cooldown speed multiplier (1 = normal, <1 faster). */
  cooldownMul(p: Player, s: Session): number;
  init(p: Player, s: Session, first: boolean): void; // on assign / join / respawn
  cleanup(p: Player, s: Session): void; // on removal / race change
  tick20(p: Player, s: Session): void; // environment & passives (1 Hz)
  tick5?(p: Player, s: Session): void; // faster checks (4 Hz)
  hud(p: Player, s: Session): string; // resource line
  /** Damage taken (before). Runs in restricted mode: only mutate ev.damage / ev.cancel. */
  onHurt?(p: Player, s: Session, ev: EntityHurtBeforeEvent): void;
  /** Damage dealt by this player (before). */
  onDealDamage?(p: Player, s: Session, ev: EntityHurtBeforeEvent): void;
  /** After-event hook when this player was hurt. */
  afterHurt?(p: Player, s: Session, cause: string, amount: number, attackerId?: string): void;
  /**
   * Remove temporary zones, summons and states the race created. Called on death, logout,
   * dimension change and lineage change (the player may already be gone: use the session id).
   */
  release?(s: Session, reason: EndReason): void;
  /** An explosion went off `distance` blocks away (within 14). */
  onExplosion?(p: Player, s: Session, distance: number): void;
  /** The player finished using an item (eating, drinking...). */
  onItemComplete?(p: Player, s: Session, typeId: string): void;
  /** Race-wide systems (zones, marks): called every 4 ticks whether or not anyone holds the race. */
  worldTick4?(): void;
}
