import { TUNING } from "../config.js";
import { addTask } from "../core/tasks.js";
import { add, v } from "../core/vec.js";
import { anim, directed, P, particle, S, sized, sound } from "../core/fx.js";
import { now, setActive } from "../state.js";
import { CastResult, Ctx } from "./types.js";

/**
 * Ability 3 - Boiler Jump: a downward steam blast (one vertical impulse, not a teleport, with
 * jets firing under the feet for a few ticks) launches the player ~6.7-9.7 blocks up. One extra use in mid-air per landing; no fall damage.
 */
export function castJump(c: Ctx): CastResult {
  const { p, s, dim, tick } = c;
  const T = TUNING.jump;
  if (!p.isOnGround) {
    if (s.airJumpsUsed >= T.airUses) return "Boiler Jump needs footing (1 mid-air use per landing)";
    s.airJumpsUsed++;
  }
  const pf = Math.sqrt(c.power);
  let carry = { x: 0, z: 0 };
  try {
    const vel = p.getVelocity();
    carry = { x: vel.x * T.carryHorizontal, z: vel.z * T.carryHorizontal };
  } catch {
    // velocity unavailable: straight up
  }
  s.fallGuardUntil = Math.max(s.fallGuardUntil, tick + T.fallGuard);
  setActive(s, "Boiler Jump", 20);
  anim(p, "jump");
  sound(dim, S.jump, p.location, 1, 1);
  sized(dim, P.ring, add(p.location, v(0, 0.1, 0)), 1.8);
  const down = v(0, -1, 0);
  try {
    p.applyKnockback(carry, T.lift * pf);
  } catch {
    return "The steam could not lift you";
  }
  addTask("boiler_jets", (age) => {
    if (!p.isValid || age >= T.jetTicks) return false;
    const l = p.location;
    directed(dim, P.downjet, add(l, v(0.18, 0.05, 0)), down, 1);
    directed(dim, P.downjet, add(l, v(-0.18, 0.05, 0)), down, 1);
    return true;
  });
  // landing: steam cushion, reset the mid-air charge, end the fall guard shortly after
  addTask("boiler_landing", (age) => {
    if (!p.isValid || age > 300) return false;
    if (age < 8) return true;
    if (age % 3 === 0) particle(dim, P.wake, add(p.location, v(0, 0.2, 0)));
    if (!p.isOnGround) return true;
    s.airJumpsUsed = 0;
    s.fallGuardUntil = now() + 10;
    particle(dim, P.land, add(p.location, v(0, 0.05, 0)));
    sound(dim, S.land, p.location, 0.8, 1);
    return false;
  });
  return true;
}
