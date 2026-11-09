import { TUNING } from "../config.js";
import { add, flat, rightOf, scale, v } from "../core/vec.js";
import { anim, chest, directed, P, particle, S, sized, sound } from "../core/fx.js";
import { refreshEffects } from "../modes.js";
import { setActive } from "../state.js";
import { CastResult, Ctx } from "./types.js";

/** Ability 1 - Steam Boost: 8s of raised internal pressure (+1 speed, +1 strength, trail, fast pulses). */
export function castBoost(c: Ctx): CastResult {
  const { p, s, dim, tick } = c;
  s.boostUntil = tick + TUNING.boost.duration;
  refreshEffects(p, s);
  setActive(s, "Steam Boost", TUNING.boost.duration);
  anim(p, "boost");
  sound(dim, S.boost, p.location, 1, 1);
  sized(dim, P.ring, add(p.location, v(0, 0.1, 0)), 2.0);
  particle(dim, P.puff, chest(p));
  // twin jets from the shoulders, angled up and back
  const f = flat(p.getViewDirection());
  const r = rightOf(f);
  for (const side of [-1, 1]) {
    const at = add(add(p.location, v(0, 1.4, 0)), scale(r, 0.38 * side));
    directed(dim, P.jet, at, add(add(scale(f, -0.6), v(0, 0.8, 0)), scale(r, 0.4 * side)), 0.7);
  }
  return true;
}
