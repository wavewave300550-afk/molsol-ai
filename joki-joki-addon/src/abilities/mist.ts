import { TUNING } from "../config.js";
import { enemiesNear } from "../core/combat.js";
import { addTask } from "../core/tasks.js";
import { add, dist, v } from "../core/vec.js";
import { anim, chest, P, particle, S, sized, sound } from "../core/fx.js";
import { setActive } from "../state.js";
import { CastResult, Ctx } from "./types.js";

/**
 * Ability 8 - Mist Veil: a stationary steam cloud (radius 5, 8s) that thins out at the end.
 * Mechanics (all vanilla effects, refreshed every 0.5s while inside):
 *   enemies: Slowness II + Blindness (Blindness obstructs players' view; mobs mostly ignore it)
 *   caster:  Invisibility (vanilla invisibility shrinks how far mobs notice you) - helps escape.
 * The add-on does not alter mob AI or vision directly.
 */
export function castMist(c: Ctx): CastResult {
  const { p, s, dim, power } = c;
  const T = TUNING.mist;
  const r = T.radius * (1 + (power - 1) * 0.4);
  const origin = { ...p.location };
  const mid = add(origin, v(0, 0.9, 0));
  setActive(s, "Mist Veil", T.duration);
  anim(p, "veil");
  sound(dim, S.mist, origin, 1.1, 1);
  particle(dim, P.ventRelease, origin);
  particle(dim, P.puff, chest(p));
  sized(dim, P.mistCloud, mid, r);
  addTask("mist_veil", (age) => {
    if (age > T.duration) return false;
    if (age % T.pulse !== 0) return true;
    const left = T.duration - age;
    sized(dim, left > 40 ? P.mistCloud : P.mistFade, mid, r * (left > 40 ? 1 : 0.6 + 0.4 * (left / 40)));
    if (age % 40 === 0 && left > 20) sound(dim, S.hiss, origin, 0.35, 0.6);
    for (const e of enemiesNear(dim, mid, r, p)) {
      try {
        e.addEffect("slowness", 30, { amplifier: T.slowAmp, showParticles: false });
        e.addEffect("blindness", 30, { amplifier: 0, showParticles: false });
      } catch {
        // immune / dead
      }
    }
    if (p.isValid && dist(p.location, origin) <= r) {
      try {
        p.addEffect("invisibility", 30, { amplifier: 0, showParticles: false });
      } catch {
        // dead
      }
    }
    return true;
  });
  return true;
}
