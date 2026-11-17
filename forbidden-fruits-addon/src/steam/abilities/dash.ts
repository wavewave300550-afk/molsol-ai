import { TUNING } from "../config.js";
import { addTask } from "../core/tasks.js";
import { add, clamp, flat, scale, v } from "../core/vec.js";
import { anim, directed, P, S, sized, sound } from "../core/fx.js";
import { setActive } from "../state.js";
import { CastResult, Ctx } from "./types.js";

/**
 * Ability 2 - Pressure Dash: steam from legs and back propels the player ~7 blocks where they look.
 * A single velocity impulse (never a teleport), so walls stop the dash; the leg and back jets keep
 * firing for a few ticks so the thrust reads as continuous propulsion. Works on the ground and in the air.
 */
export function castDash(c: Ctx): CastResult {
  const { p, s, dim, tick } = c;
  const T = TUNING.dash;
  const look = p.getViewDirection();
  const f = flat(look);
  const pf = Math.sqrt(c.power);
  const speed = T.speed * pf;
  const grounded = p.isOnGround;
  // look up -> rise a little, look down in the air -> dive a little
  const lift = (grounded ? T.lift : T.airLift) + clamp(look.y, -0.4, 0.6) * 0.35;
  s.fallGuardUntil = Math.max(s.fallGuardUntil, tick + T.fallGuard);
  setActive(s, "Pressure Dash", 12);
  anim(p, "dash");
  sound(dim, S.dash, p.location, 1, 1.0 + (c.mode - 2) * 0.06);
  if (grounded) sized(dim, P.ring, add(p.location, v(0, 0.1, 0)), 1.3);
  const back = scale(f, -1);
  try {
    p.applyKnockback({ x: f.x * speed, z: f.z * speed }, lift);
  } catch {
    return "The steam could not move you";
  }
  addTask("dash_jets", (age) => {
    if (!p.isValid || age >= T.jetTicks) return false;
    const l = p.location;
    directed(dim, P.dashJet, add(l, v(0, 1.15, 0)), add(back, v(0, 0.15, 0)), 1);
    directed(dim, P.dashJet, add(l, v(0, 0.45, 0)), add(back, v(0, -0.35, 0)), 1);
    return true;
  });
  return true;
}
