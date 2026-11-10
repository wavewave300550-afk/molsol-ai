import { Dimension, Entity, Player, Vector3, world } from "@minecraft/server";
import { BUDGET, CONSTRUCT_FAMILY, DP, PROP } from "./config.js";

/** Every temporary petroleum entity (pools, waves, geysers, prisons, serpents, relics). */
interface Tracked {
  e: Entity;
  type: string;
  ownerId: string;
  born: number;
}

const tracked = new Map<string, Tracked>();
let born = 0;

export function spawnConstruct(dim: Dimension, typeId: string, at: Vector3, ownerId: string, yaw?: number): Entity | undefined {
  // global budget: the oldest construct makes room
  if (tracked.size >= BUDGET.maxConstructs) {
    const oldest = [...tracked.values()].sort((a, b) => a.born - b.born)[0];
    if (oldest) removeConstruct(oldest.e);
  }
  let e: Entity;
  try {
    e = dim.spawnEntity(typeId, at);
  } catch {
    return undefined; // unloaded chunk / outside the world
  }
  try {
    e.setDynamicProperty(DP.constructOwner, ownerId);
    if (yaw !== undefined) e.setRotation({ x: 0, y: yaw });
  } catch {
    // property / rotation failed: still usable
  }
  tracked.set(e.id, { e, type: typeId, ownerId, born: born++ });
  return e;
}

export function removeConstruct(e: Entity | undefined): void {
  if (!e) return;
  tracked.delete(e.id);
  try {
    if (e.isValid) e.remove();
  } catch {
    // already gone
  }
}

export function setBurning(e: Entity | undefined, burning: boolean): void {
  if (!e || !e.isValid) return;
  try {
    if (e.getProperty(PROP.burning) !== burning) e.setProperty(PROP.burning, burning);
  } catch {
    // entity without the property
  }
}

export function ownedConstructs(ownerId: string, type: string): Entity[] {
  const out: Entity[] = [];
  for (const [id, t] of tracked) {
    if (!t.e.isValid) {
      tracked.delete(id);
      continue;
    }
    if (t.ownerId === ownerId && t.type === type) out.push(t.e);
  }
  return out;
}

export function removeOwned(ownerId: string, type?: string): void {
  for (const t of [...tracked.values()]) if (t.ownerId === ownerId && (!type || t.type === type)) removeConstruct(t.e);
}

export const constructCount = (): number => {
  for (const [id, t] of tracked) if (!t.e.isValid) tracked.delete(id);
  return tracked.size;
};

/** World load: constructs never survive a reload (they would be orphaned without their scripts). */
export function sweepOrphans(): number {
  let n = 0;
  for (const dimId of ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"]) {
    try {
      for (const e of world.getDimension(dimId).getEntities({ families: [CONSTRUCT_FAMILY] })) {
        if (!tracked.has(e.id)) {
          e.remove();
          n++;
        }
      }
    } catch {
      // dimension not loaded
    }
  }
  return n;
}

export const ownerOf = (e: Entity): Player | undefined => {
  try {
    const id = e.getDynamicProperty(DP.constructOwner);
    const p = typeof id === "string" ? world.getEntity(id) : undefined;
    return p instanceof Player ? p : undefined;
  } catch {
    return undefined;
  }
};
