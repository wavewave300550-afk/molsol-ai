/**
 * AudioEventController - world-positioned sound cues.
 * Every cue has a visual counterpart elsewhere; nothing in the fight depends on hearing it.
 */
import { Dimension } from "@minecraft/server";
import { V3 } from "./math";

export class Audio {
  constructor(private readonly dim: Dimension) {}

  play(id: string, pos: V3, volume = 1, pitch = 1): void {
    try {
      this.dim.playSound(id, pos, { volume, pitch });
    } catch {
      /* unloaded chunk: ignore */
    }
  }
}
