/**
 * Lunar Sigils (Jackalope "Antler Brand").  A marked enemy:
 *  - takes +3 damage from the branding jackalope's melee hits,
 *  - is prioritised by Crimson Waltz, whose slashes deal +50% to it,
 *  - if it dies while marked, the jackalope's other cooldowns drop by 4 s and it gains Speed II (Moonhunt),
 *  - during the Blood Moon the sigil detonates when it expires (4 damage).
 */
import { Entity, Player, system, world } from "@minecraft/server";
import { hurt } from "../core/combat.js";
import { particle, rgb, RGB } from "../core/fx.js";
import { add, v3 } from "../core/util.js";

interface Mark {
  by: string;
  until: number;
  blood: boolean;
}
const marks = new Map<string, Mark>();

export function brand(e: Entity, by: Player, ticks: number, blood: boolean): void {
  marks.set(e.id, { by: by.id, until: system.currentTick + ticks, blood });
}

export function markedBy(e: Entity | string): string | undefined {
  const id = typeof e === "string" ? e : e.id;
  const m = marks.get(id);
  return m && m.until > system.currentTick ? m.by : undefined;
}

export function consume(e: Entity): void {
  marks.delete(e.id);
}

export function clearMarksBy(playerId: string): void {
  for (const [k, m] of marks) if (m.by === playerId) marks.delete(k);
}

/** Every 8 ticks: sigil visuals, expiry and Blood Moon detonations. */
export function tickMarks(): void {
  if (marks.size === 0) return;
  const now = system.currentTick;
  for (const [id, m] of marks) {
    let e: Entity | undefined;
    try {
      e = world.getEntity(id);
    } catch {
      e = undefined;
    }
    if (!e || !e.isValid) {
      marks.delete(id);
      continue;
    }
    const head = add(e.location, v3(0, 2.2, 0));
    if (m.until <= now) {
      marks.delete(id);
      if (m.blood) {
        const owner = world.getPlayers().find((p) => p.id === m.by);
        particle(e.dimension, "plrace:crimson_slash", head, { spin: 0, scale: 0.8 });
        if (owner) hurt(e, 4, owner);
      }
      continue;
    }
    particle(e.dimension, "plrace:moon_sigil", head, rgb(m.blood ? RGB.crimson : RGB.silver));
  }
}
