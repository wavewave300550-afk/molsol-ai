import { TUNING } from "../config.js";
import { enemiesNear, hurt, ignite } from "../core/combat.js";
import { anim, directed, P, particle, S, sound } from "../core/fx.js";
import { addTask } from "../core/tasks.js";
import { add, clamp, flat, scale, v } from "../core/vec.js";
import { ignitePoolsNear, spawnPool } from "../pools.js";
import { clearFollowUp, now, setActive, setFollowUp } from "../state.js";
import { syncProperties } from "../power.js";
import { CastResult, Ctx } from "./types.js";

/**
 * 5 - Oil Jet: one high-pressure light-crude impulse (~8 blocks on the ground, never a
 * teleport, walls stop you) leaving an oil slick and trail. Tap again within 1.2s for an ignited
 * AFTERBURNER in whatever direction you now look: a second burst that scorches anything you pass
 * and ignites the slick behind you.
 */
export function castJet(c: Ctx): CastResult {
  const { p, s, dim, tick } = c;
  const T = TUNING.jet;
  const look = p.getViewDirection();
  const f = flat(look);
  const lift = (p.isOnGround ? T.lift : T.airLift) + clamp(look.y, -0.4, 0.6) * 0.35;
  try {
    p.applyKnockback({ x: f.x * T.speed, z: f.z * T.speed }, lift);
  } catch {
    return "The oil could not move you";
  }
  s.fallGuardUntil = Math.max(s.fallGuardUntil, tick + T.fallGuard);
  const start = { ...p.location };
  spawnPool(dim, start, T.slickRadius, p.id, { ticks: 140 });
  anim(p, "jet");
  sound(dim, S.jet, start, 1, 1);
  setActive(s, "Oil Jet", 12);
  const back = scale(f, -1);
  addTask("oil_jet_trail", (age) => {
    if (!p.isValid || age > 7) return false;
    directed(dim, P.spray, add(p.location, v(0, 0.6, 0)), add(back, v(0, 0.1, 0)), 1);
    if (age % 2 === 0) particle(dim, P.trail, p.location);
    return true;
  });
  setFollowUp(s, "jet", T.chainWindow, () => afterburn(c, start));
  return true;
}

function afterburn(c: Ctx, start: { x: number; y: number; z: number }): void {
  const { p, s, dim } = c;
  const T = TUNING.jet;
  clearFollowUp(s, "jet");
  const f = flat(p.getViewDirection());
  try {
    p.applyKnockback({ x: f.x * T.afterburnSpeed, z: f.z * T.afterburnSpeed }, 0.25);
  } catch {
    return;
  }
  s.fallGuardUntil = Math.max(s.fallGuardUntil, now() + T.fallGuard);
  s.burningUntil = Math.max(s.burningUntil, now() + 24);
  syncProperties(p, s);
  sound(dim, S.ignite, p.location, 1.1, 1.2);
  particle(dim, P.flash, add(p.location, v(0, 0.8, 0)));
  ignitePoolsNear(dim, start, T.slickRadius + 1);
  setActive(s, "Afterburner", 12);
  const scorched = new Set<string>();
  const back = scale(f, -1);
  addTask("oil_jet_afterburn", (age) => {
    if (!p.isValid || age > 9) return false;
    directed(dim, P.fire, add(p.location, v(0, 0.6, 0)), back, 1);
    for (const t of enemiesNear(dim, p.location, 1.8, p)) {
      if (scorched.has(t.id)) continue;
      scorched.add(t.id);
      hurt(t, T.afterburnDamage, p);
      ignite(t, T.fireSeconds);
    }
    return true;
  });
}
