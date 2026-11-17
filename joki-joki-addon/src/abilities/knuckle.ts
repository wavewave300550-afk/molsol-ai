import { Entity, Player } from "@minecraft/server";
import { MODES, TUNING } from "../config.js";
import { enemiesInCone, enemyInSight, hurt, knockAlong } from "../core/combat.js";
import { addTask } from "../core/tasks.js";
import { add, dist, flat, flatDir, scale, sub, v } from "../core/vec.js";
import { anim, center, directed, P, particle, rightHand, S, shake, sized, sound } from "../core/fx.js";
import { notice, now, setActive, SteamState } from "../state.js";
import { CastResult, Ctx } from "./types.js";

/**
 * Ability 6 - Steam Knuckle.
 * Target in reach (crosshair ray, or the nearest enemy in a narrow cone) -> pressure punch now.
 * Nobody in reach -> the fist stays primed for 3s and the next real melee hit (entityHitEntity)
 * detonates it on whatever was struck.
 */
export function castKnuckle(c: Ctx): CastResult {
  const { p, s, dim, tick } = c;
  const T = TUNING.knuckle;
  const target = enemyInSight(p, T.reach) ?? enemiesInCone(p, T.reach, 0.8)[0];
  if (target) {
    knucklePunch(p, s, target);
    return true;
  }
  s.knucklePrimedUntil = tick + T.primeTicks;
  setActive(s, "Knuckle primed", T.primeTicks);
  notice(s, "§6Fist primed §7- land a melee hit within 3s", 40);
  sound(dim, S.shift, p.location, 0.7, 1.4);
  addTask("knuckle_prime", (age) => {
    if (!p.isValid || now() >= s.knucklePrimedUntil) return false;
    if (age % 3 === 0) particle(dim, P.handSteam, rightHand(p, 0.35));
    return true;
  });
  return true;
}

export function knucklePunch(p: Player, s: SteamState, target: Entity): void {
  const T = TUNING.knuckle;
  const dim = p.dimension;
  const power = MODES[s.mode].power;
  const pf = Math.sqrt(power);
  s.knucklePrimedUntil = 0;
  setActive(s, "Steam Knuckle", 15);
  const dir = dist(target.location, p.location) > 0.2 ? flatDir(p.location, target.location) : flat(p.getViewDirection());
  anim(p, "knuckle");
  hurt(target, T.damage * power, p);
  knockAlong(target, dir, T.knockback * pf, T.lift);
  const contact = sub(center(target), scale(dir, 0.35));
  particle(dim, P.impact, contact);
  directed(dim, P.cone, contact, dir, power);
  sized(dim, P.ring, add(target.location, v(0, 0.1, 0)), 1.6);
  sound(dim, S.punch, contact, 1.2, 1);
  sound(dim, S.impact, contact, 0.9, 0.85);
  shake(p, 0.2, 0.3);
  // short-range pressure shockwave behind the fist
  for (const e of enemiesInCone(p, T.coneRange, T.coneDot)) {
    if (e.id === target.id) continue;
    hurt(e, T.damage * power * T.coneDamage, p);
    knockAlong(e, flatDir(p.location, e.location), T.knockback * 0.6 * pf, T.lift * 0.7);
  }
}
