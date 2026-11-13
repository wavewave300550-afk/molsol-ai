/**
 * Book presentation (core/books.ts): the selection vision and the charge construct shown for all
 * three Grimoires.  Distances are in blocks, times in ticks (20 ticks = 1 s).  The actor ids, kinds
 * and states below are the shared contract with the asset modules tools/assets/books_<g>.py.
 */
import type { GrimoireId } from "../core/registry";

/** States of grimoire:book_<g>_vision (kind = spell index 0-5). */
export const VISION_STATE = { hidden: 0, show: 1 } as const;
/** States of grimoire:book_<g>_charge (kind = spell index 0-5). */
export const CHARGE_STATE = { hidden: 0, form: 1, loop: 2, release: 3, cancel: 4 } as const;

export const BOOKS = {
  /** Asset prefix per Grimoire: actors book_<g>_vision / book_<g>_charge, sounds and particles book_<g>_*. */
  prefix: { divine_word: "dw", dream_nightmare: "dn", elemental_dragon: "ed" } as Record<GrimoireId, string>,
  vision: {
    /** Life of the selection vision; its one-shot "show" animation lasts exactly 1.2 s. */
    ticks: 24,
    /** Placement from the eyes: along the view, to the right, and vertical offset.  Sits above the book hand. */
    ahead: 1.3,
    right: 0.55,
    up: -0.2,
    /** Volume of the page-turn + motif sound. */
    volume: 0.8,
  },
  charge: {
    /** Ticks of the one-shot "form" animation (1.5 s) before switching to the "loop" state. */
    formTicks: 30,
    /** The release flare (0.5 s) and the quiet cancel fold (0.4 s) before the construct is removed. */
    releaseTicks: 10,
    cancelTicks: 8,
    /** Placement from the eyes: ahead along the view, to the right (keeps the crosshair clear), above eye line. */
    ahead: 2.2,
    right: 0.8,
    up: 0.4,
    /** The view direction's vertical part is clamped so the construct stays in front when looking up or down. */
    minDirY: -0.45,
    maxDirY: 0.55,
    /** Fraction of the way to the new place moved each tick (1 = rigid, lower = floats behind the view). */
    follow: 0.5,
    /** Ambient mote particle every N ticks while held. */
    moteEvery: 4,
    /** The ~2 s charge swell is retriggered every N held ticks (quieter after the first time). */
    soundEvery: 44,
    soundVolume: 0.75,
    soundRepeatVolume: 0.5,
    /** Particle bursts on release (spread around the construct). */
    burstCount: 3,
    burstRadius: 0.6,
    /** Watchdog: a preparation that receives no tick for this many ticks folds itself away. */
    stallTicks: 10,
  },
  deny: {
    volume: 0.7,
  },
};
