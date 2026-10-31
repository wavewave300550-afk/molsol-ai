import { Entity, Vector3, world } from "@minecraft/server";
import { shards, sound } from "./core/fx.js";
import { add, v } from "./core/vec.js";
import { Boss } from "./engine.js";

/** Invulnerable script-driven helpers (mirror images of the Choir). */

interface Illusion {
  entity: Entity;
  owner: Boss;
  expires: number;
  tag: string;
}

const illusions = new Map<string, Illusion>();

export function spawnIllusion(b: Boss, type: string, at: Vector3, life: number, tick: number, tag = ""): Entity | undefined {
  try {
    const e = b.dim.spawnEntity(type, at);
    illusions.set(e.id, { entity: e, owner: b, expires: tick + life, tag });
    shards(b.dim, add(at, v(0, 2, 0)));
    return e;
  } catch (err) {
    console.warn(`[fb] illusion spawn failed: ${err}`);
    return undefined;
  }
}

export function illusionOf(e: Entity): Illusion | undefined {
  return illusions.get(e.id);
}

export function illusionsOf(b: Boss, tag?: string): Illusion[] {
  return [...illusions.values()].filter((i) => i.owner === b && i.entity.isValid && (tag === undefined || i.tag === tag));
}

export function shatter(e: Entity | undefined): void {
  if (!e) return;
  illusions.delete(e.id);
  if (!e.isValid) return;
  try {
    shards(e.dimension, add(e.location, v(0, 2, 0)));
    sound(e.dimension, "random.glass", e.location, 1.5, 0.8);
    e.remove();
  } catch {
    // ignore
  }
}

export function tickIllusions(tick: number): void {
  for (const [id, il] of [...illusions]) {
    if (!il.entity.isValid) illusions.delete(id);
    else if (il.expires <= tick || !il.owner.entity.isValid) shatter(il.entity);
  }
}

export function sweepOrphans(types: string[]): void {
  for (const id of ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"]) {
    let dim;
    try {
      dim = world.getDimension(id);
    } catch {
      continue;
    }
    for (const type of types) {
      for (const e of dim.getEntities({ type })) {
        if (!illusions.has(e.id)) {
          try {
            e.remove();
          } catch {
            // ignore
          }
        }
      }
    }
  }
}
