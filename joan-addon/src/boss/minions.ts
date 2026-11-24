import { Dimension, Entity, world } from "@minecraft/server";
import { MINIONS } from "../config.js";
import { V3 } from "../core/vec.js";

/** Spawn a helper entity owned by a boss (tagged so orphans can be cleaned after reloads). */
export function spawnMinion(dim: Dimension, type: string, at: V3, ownerId: string): Entity | undefined {
  try {
    const e = dim.spawnEntity(type, at);
    e.setDynamicProperty("joan:owner", ownerId);
    return e;
  } catch {
    return undefined;
  }
}

export function ownerOf(e: Entity): string | undefined {
  try {
    const o = e.getDynamicProperty("joan:owner");
    return typeof o === "string" ? o : undefined;
  } catch {
    return undefined;
  }
}

export function removeQuietly(e: Entity | undefined): void {
  if (!e || !e.isValid) return;
  try {
    e.remove();
  } catch {
    // already gone
  }
}

/** Remove every helper entity whose owner is not in `alive` (after reloads or a finished fight). */
export function sweepOrphans(alive: Set<string>): number {
  let n = 0;
  for (const dimId of ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"]) {
    let dim: Dimension;
    try {
      dim = world.getDimension(dimId);
    } catch {
      continue;
    }
    for (const type of MINIONS) {
      let list: Entity[] = [];
      try {
        list = dim.getEntities({ type });
      } catch {
        continue;
      }
      for (const e of list) {
        const o = ownerOf(e);
        if (!o || !alive.has(o)) {
          removeQuietly(e);
          n++;
        }
      }
    }
  }
  return n;
}

export function setProp(e: Entity | undefined, id: string, value: boolean | number | string): void {
  if (!e || !e.isValid) return;
  try {
    e.setProperty(id, value);
  } catch {
    // property missing on this entity type
  }
}
