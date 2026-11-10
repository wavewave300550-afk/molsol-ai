import { TUNING } from "../config.js";
import { enemiesNear, hurt, knockFrom } from "../core/combat.js";
import { addTask } from "../core/tasks.js";
import { add, dist, v } from "../core/vec.js";
import { anim, center, chest, P, particle, S, shake, sized, sound } from "../core/fx.js";
import { setActive } from "../state.js";
import { CastResult, Ctx } from "./types.js";

/**
 * Ability 5 - Scald Burst: explosive pressure release around the body.
 * Area damage with distance falloff and strong outward knockback. No explosion is created,
 * so terrain is never damaged. The lingering cloud is the "visual obstruction".
 */
export function castScald(c: Ctx): CastResult {
  const { p, s, dim, power } = c;
  const T = TUNING.scald;
  const r = T.radius * (1 + (power - 1) * 0.5);
  const at = chest(p);
  setActive(s, "Scald Burst", 20);
  anim(p, "burst");
  sound(dim, S.explode, at, 1.3, 1);
  shake(p, 0.3, 0.5);
  particle(dim, P.impact, at);
  particle(dim, P.scaldCloud, at);
  sized(dim, P.ring, add(p.location, v(0, 0.15, 0)), r);
  sized(dim, P.ring, add(p.location, v(0, 1.0, 0)), r * 0.7);
  for (const e of enemiesNear(dim, center(p), r, p)) {
    const d = dist(center(e), at);
    const fall = Math.max(0, 1 - 0.4 * (d / r));
    hurt(e, T.damage * power * fall, p);
    knockFrom(e, p.location, T.knockback * Math.sqrt(power) * (0.7 + 0.3 * fall), T.lift);
    particle(dim, P.puff, center(e));
  }
  try {
    p.extinguishFire(true);
  } catch {
    // not burning
  }
  const origin = { ...p.location };
  addTask("scald_cloud", (age) => {
    if (age > T.cloudTicks) return false;
    if (age > 0 && age % 10 === 0) sized(dim, P.cloudLinger, add(origin, v(0, 0.9, 0)), r * 0.75);
    return true;
  });
  return true;
}
