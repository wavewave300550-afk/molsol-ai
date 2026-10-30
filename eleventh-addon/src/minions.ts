import { Entity, Player, Vector3, world } from "@minecraft/server";
import { burst, mote, sound, sphereWave } from "./core/fx.js";
import { chest, hurt, isVictim, playersNear, victimsNear } from "./core/targets.js";
import { add, dist, v } from "./core/vec.js";
import { Being } from "./engine.js";

/**
 * Script-driven helpers of the beings:
 *   dim11:wisp     - a closed string that hunts a player and detonates (can be killed)
 *   dim11:echo     - an invulnerable past-self of the Observer (timeline echo)
 *   dim11:phantom  - the mirrored brane-image of the Sovereign during Genesis Collision
 */

interface Wisp {
  entity: Entity;
  owner: Entity;
  born: number;
}

const wisps = new Map<string, Wisp>();
const illusions = new Map<string, { entity: Entity; expires: number }>();

export function spawnWisp(b: Being, at: Vector3, tick: number): void {
  try {
    const e = b.dim.spawnEntity("dim11:wisp", at);
    wisps.set(e.id, { entity: e, owner: b.entity, born: tick });
    burst(b.dim, "cyan", add(at, v(0, 0.5, 0)));
  } catch (err) {
    console.warn(`[dim11] wisp spawn failed: ${err}`);
  }
}

export function wispCount(b: Being): number {
  let n = 0;
  for (const w of wisps.values()) if (w.owner.id === b.entity.id && w.entity.isValid) n++;
  return n;
}

export function spawnIllusion(b: Being, type: "dim11:echo" | "dim11:phantom", at: Vector3, look: Vector3, life: number, tick: number): Entity | undefined {
  try {
    const e = b.dim.spawnEntity(type, at);
    e.teleport(at, { facingLocation: look });
    illusions.set(e.id, { entity: e, expires: tick + life });
    burst(b.dim, b.def.hue, add(at, v(0, 2, 0)));
    return e;
  } catch (err) {
    console.warn(`[dim11] illusion spawn failed: ${err}`);
    return undefined;
  }
}

export function dismiss(e: Entity | undefined): void {
  if (!e) return;
  illusions.delete(e.id);
  if (!e.isValid) return;
  try {
    burst(e.dimension, "white", add(e.location, v(0, 2, 0)));
    e.remove();
  } catch {
    // ignore
  }
}

function detonate(w: Wisp): void {
  wisps.delete(w.entity.id);
  if (!w.entity.isValid) return;
  const at = chest(w.entity);
  const dim = w.entity.dimension;
  sphereWave(dim, "cyan", at);
  sound(dim, "breeze_wind_charge.burst", at, 1.2, 0.8);
  for (const e of victimsNear(dim, at, 2.8)) hurt(e, 6, w.owner.isValid ? w.owner : undefined);
  try {
    w.entity.remove();
  } catch {
    // ignore
  }
}

export function tickMinions(tick: number): void {
  for (const w of [...wisps.values()]) {
    if (!w.entity.isValid) {
      wisps.delete(w.entity.id);
      continue;
    }
    const age = tick - w.born;
    if (age > 160 || !w.owner.isValid) {
      detonate(w);
      continue;
    }
    const prey = playersNear(w.entity.dimension, w.entity.location, 32).sort((a, b) => dist(a.location, w.entity.location) - dist(b.location, w.entity.location))[0];
    if (!prey) continue;
    const goal = add(prey.location, v(0, 1.1, 0));
    const here = w.entity.location;
    const d = dist(here, goal);
    if (d < 1.4 && age > 20) {
      detonate(w);
      continue;
    }
    const step = Math.min(d, 0.26 + age * 0.0015);
    const next = { x: here.x + ((goal.x - here.x) / d) * step, y: here.y + ((goal.y - here.y) / d) * step + Math.sin(age * 0.3) * 0.05, z: here.z + ((goal.z - here.z) / d) * step };
    try {
      w.entity.teleport(next, { facingLocation: goal });
    } catch {
      // ignore
    }
    if (age % 3 === 0) mote(w.entity.dimension, "cyan", here);
  }
  for (const [id, il] of [...illusions]) {
    if (!il.entity.isValid) illusions.delete(id);
    else if (il.expires <= tick) dismiss(il.entity);
  }
}

/** After a reload script state is lost: remove orphaned helpers. */
export function sweepOrphans(): void {
  for (const id of ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"]) {
    let dim;
    try {
      dim = world.getDimension(id);
    } catch {
      continue;
    }
    for (const type of ["dim11:wisp", "dim11:echo", "dim11:phantom"]) {
      for (const e of dim.getEntities({ type })) {
        if (!wisps.has(e.id) && !illusions.has(e.id)) {
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

export const isWisp = (e: Entity) => wisps.has(e.id);
export const victimFilter = (e: Entity) => isVictim(e) && !(e instanceof Player && !e.isValid);
