/**
 * Facing for scripted entities.
 *
 * Entity.setRotation alone is not enough: in the game a mob's rendered body does not reliably follow
 * it. Every scripted entity therefore also publishes the yaw it wants in the synced property
 * `abm:yaw`, and its client animation turns the model's root bone by the difference between that and
 * the body yaw the engine actually renders (see add_facing in tools/kit/anim.py).
 */
import { Entity } from "@minecraft/server";
import { wrapDeg } from "./math";

const published = new WeakMap<Entity, number>();

/** The value stored in abm:yaw for a yaw in degrees (one decimal, inside the property's range). */
export function yawProperty(yaw: number): number {
  const y = Math.round(wrapDeg(yaw) * 10) / 10;
  return Math.max(-180, Math.min(180, y));
}

/** Turn a helper entity: engine rotation plus the published yaw. Never throws. */
export function setYaw(e: Entity, yaw: number): void {
  const y = yawProperty(yaw);
  try {
    e.setRotation({ x: 0, y });
  } catch {
    /* invalid entity */
  }
  if (published.get(e) === y) return;
  try {
    e.setProperty("abm:yaw", y);
    published.set(e, y);
  } catch {
    /* invalid entity, or an entity without the property */
  }
}
