import { Entity } from "@minecraft/server";
import { TUNING } from "../config.js";
import { enemiesNear, hurt, knockAlong, knockFrom } from "../core/combat.js";
import { addTask } from "../core/tasks.js";
import { add, flat, scale, v } from "../core/vec.js";
import { anim, center, directed, P, particle, S, shake, sized, sound } from "../core/fx.js";
import { setActive } from "../state.js";
import { CastResult, Ctx } from "./types.js";

/**
 * Ability 7 - Jet Kick: a short, low jet-propelled lunge (one impulse, ~4 blocks) with an active
 * hitbox in front of the legs for 8 ticks. The first enemy touched takes the kick (damage + big horizontal knockback + shockwave)
 * and the player rebounds. Unlike Pressure Dash it is short, stays low and is an attack.
 */
export function castKick(c: Ctx): CastResult {
  const { p, s, dim, tick, power } = c;
  const T = TUNING.kick;
  const f = flat(p.getViewDirection());
  const pf = Math.sqrt(power);
  s.fallGuardUntil = Math.max(s.fallGuardUntil, tick + T.fallGuard);
  setActive(s, "Jet Kick", 15);
  anim(p, "kick");
  sound(dim, S.kick, p.location, 1, 1);
  sized(dim, P.ring, add(p.location, v(0, 0.1, 0)), 1.0);
  const back = scale(f, -1);
  let landed = false;
  try {
    p.applyKnockback({ x: f.x * T.speed * pf, z: f.z * T.speed * pf }, T.lift);
  } catch {
    return "The steam could not move you";
  }
  addTask("jet_kick", (age) => {
    if (!p.isValid || landed || age > T.activeTicks) return false;
    if (age < T.jetTicks) directed(dim, P.dashJet, add(p.location, v(0, 0.5, 0)), add(back, v(0, -0.1, 0)), 1);
    const foot = add(add(p.location, scale(f, 0.9)), v(0, 0.8, 0));
    const victim: Entity | undefined = enemiesNear(dim, foot, T.hitRadius, p, 1)[0];
    if (!victim) return true;
    landed = true;
    hurt(victim, T.damage * power, p);
    knockAlong(victim, f, T.knockback * pf, T.lift2);
    const at = center(victim);
    particle(dim, P.impact, at);
    directed(dim, P.cone, at, f, power);
    sized(dim, P.ring, add(victim.location, v(0, 0.1, 0)), 1.8);
    sound(dim, S.impact, at, 1.2, 0.9);
    shake(p, 0.2, 0.3);
    for (const e of enemiesNear(dim, victim.location, 2.2, p)) {
      if (e.id === victim.id) continue;
      hurt(e, T.damage * power * 0.4, p);
      knockFrom(e, victim.location, 1.4 * pf, 0.3);
    }
    try {
      p.applyKnockback({ x: -f.x * 0.35, z: -f.z * 0.35 }, 0.22);
    } catch {
      // rebound is cosmetic
    }
    return false;
  });
  return true;
}
