import { BlockComponentTickEvent, Dimension, StartupEvent, world } from "@minecraft/server";
import { rules } from "../config";
import { V3, floor3 } from "./vec";

/**
 * Temporary spell blocks (labyrinth walls, citadel ramparts). Rules:
 *  - placed only into air, so player constructions are never replaced;
 *  - every placement is tracked and reverted to air when the spell ends;
 *  - each spell block carries the "grimoire:temporary" custom component whose tick handler
 *    deletes any block that is no longer owned by a live spell (crash / reload safety net).
 */
export const TEMP_BLOCK_IDS = [
  "grimoire:pressure_barrier",
  "grimoire:frost_wall",
  "grimoire:blood_thornwall",
  "grimoire:shadow_step_low",
  "grimoire:shadow_step_high",
];

const live = new Map<string, string>(); // key -> owner set id

const key = (dimId: string, l: V3): string => `${dimId}|${Math.floor(l.x)}|${Math.floor(l.y)}|${Math.floor(l.z)}`;

let nextSet = 1;

export class TempBlockSet {
  readonly id = `s${nextSet++}`;
  readonly placed = new Map<string, V3>();
  constructor(readonly dim: Dimension) {}

  get enabled(): boolean {
    return rules().temporaryBlocks;
  }

  /** Try to place a temporary block; returns false if the space is not air or unloaded. */
  place(loc: V3, typeId: string): boolean {
    if (!this.enabled) return false;
    const l = floor3(loc);
    const k = key(this.dim.id, l);
    if (live.has(k)) return false;
    try {
      const b = this.dim.getBlock(l);
      if (!b || !b.isValid || !b.isAir) return false;
      b.setType(typeId);
      live.set(k, this.id);
      this.placed.set(k, l);
      return true;
    } catch {
      return false;
    }
  }

  has(loc: V3): boolean {
    return this.placed.has(key(this.dim.id, floor3(loc)));
  }

  /** Remove one of this set's blocks (only if it is still our block). */
  remove(loc: V3): void {
    const l = floor3(loc);
    const k = key(this.dim.id, l);
    if (!this.placed.has(k)) return;
    this.placed.delete(k);
    live.delete(k);
    try {
      const b = this.dim.getBlock(l);
      if (b && b.isValid && TEMP_BLOCK_IDS.includes(b.typeId)) b.setType("minecraft:air");
    } catch {
      /* unloaded: the tick component will clean it later */
    }
  }

  clear(): void {
    for (const l of [...this.placed.values()]) this.remove(l);
  }

  positions(): V3[] {
    return [...this.placed.values()];
  }
}

export function registerBlockComponents(ev: StartupEvent): void {
  ev.blockComponentRegistry.registerCustomComponent("grimoire:temporary", {
    onTick(e: BlockComponentTickEvent) {
      const b = e.block;
      if (!live.has(key(e.dimension.id, b.location))) {
        try {
          b.setType("minecraft:air");
        } catch {
          /* ignore */
        }
      }
    },
  });
}

export function liveTempBlocks(): number {
  return live.size;
}

/** Used by tests/diagnostics. */
export function anyTempBlockAt(dimId: string, l: V3): boolean {
  return live.has(key(dimId, l));
}

export const overworld = () => world.getDimension("overworld");
