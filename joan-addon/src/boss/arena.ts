import { Entity } from "@minecraft/server";
import { TUNING } from "../config.js";
import { hdist, sub } from "../core/vec.js";
import { circle } from "../paths/shapes.js";
import type { JoanBoss } from "./joan.js";

/**
 * The Processional Ring: the arena boundary Joan writes when she lands.
 * It only takes projectiles that come flying IN from outside the arena (so
 * sniping her from afar is swept along the ring), never the shots of players
 * standing inside or on the edge.
 */
export function arenaRing(b: JoanBoss): void {
  if (b.field.livePaths().some((p) => p.o.tag === "arena" && p.endAt > b.now + 20)) return;
  const R = TUNING.arenaRadius;
  b.field.add(circle(b.home, R, 0, 1, false), {
    kind: "ring", owner: b.id, loop: true, speed: 0.8, radius: 1.6, aerial: true, form: 20, life: 20 * 60 * 30,
    carryPlayers: false, carryMobs: false, carryProjectiles: true, memory: false, burning: false, damage: 0,
    color: { red: 1, green: 0.88, blue: 0.5, alpha: 0.45 }, chevron: { red: 1, green: 0.9, blue: 0.6, alpha: 0.5 },
    tag: "arena", renderEvery: 40, chevrons: false,
    accept: (e: Entity) => {
      try {
        const vel = e.getVelocity();
        const inward = sub(b.home, e.location);
        return hdist(e.location, b.home) >= R - 0.4 && vel.x * inward.x + vel.z * inward.z > 0;
      } catch {
        return false;
      }
    },
  }, b.now);
}
