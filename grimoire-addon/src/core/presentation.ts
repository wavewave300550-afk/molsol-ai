import { Player } from "@minecraft/server";
import { GrimoireDef, SpellMeta } from "./registry";

/** Visual/audio feedback for selecting and preparing spells.  Implemented in core/books.ts. */
export interface PrepHandle {
  /** Called every tick while Use is held. */
  tick(heldTicks: number): void;
  /** The cast went through: play the release flourish, then clean up. */
  release(): void;
  /** The preparation was cancelled: dissolve quietly. */
  cancel(): void;
}

export interface Presenter {
  select(player: Player, g: GrimoireDef, meta: SpellMeta): void;
  prepStart(player: Player, g: GrimoireDef, meta: SpellMeta): PrepHandle;
  deny(player: Player, g: GrimoireDef): void;
}

const NOOP: PrepHandle = { tick() {}, release() {}, cancel() {} };
let presenter: Presenter = { select() {}, prepStart: () => NOOP, deny() {} };

export function setPresenter(p: Presenter): void { presenter = p; }
export function present(): Presenter { return presenter; }
