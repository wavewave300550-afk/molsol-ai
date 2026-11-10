import { Entity } from "@minecraft/server";
import { BUDGET, ENT, TUNING } from "../config.js";
import { enemiesNear, enemyInSight, hurt, ignite, knockFrom, oilSlow } from "../core/combat.js";
import { anim, center, directed, entityAnim, P, particle, S, sized, sound } from "../core/fx.js";
import { addTask } from "../core/tasks.js";
import { add, dist, flat, norm, rightOf, scale, sub, v } from "../core/vec.js";
import { ownedConstructs, removeConstruct, setBurning, spawnConstruct } from "../constructs.js";
import { groundAt, ignitePoolsNear, spawnPool } from "../pools.js";
import { clearFollowUp, setActive, setFollowUp } from "../state.js";
import { CastResult, Ctx } from "./types.js";
import { yawOf } from "./util.js";

/**
 * 6 - Black Serpent: a 9-block petroleum serpent (3D model, 10 articulated segments that slither)
 * hunts for 10s. It targets what you aim at (else the nearest enemy near you, else circles you).
 * Light crude: it races in a sinuous path. Heavy crude: every 3rd bite it coils and holds its
 * prey. It tail-sweeps groups. Tap again to set it ablaze (burning bites, fiery collapse).
 */
export function castSerpent(c: Ctx): CastResult {
  const { p, s, dim } = c;
  const T = TUNING.serpent;
  if (ownedConstructs(p.id, ENT.serpent).length >= BUDGET.serpentsPerPlayer) return "Your serpent is still out";
  const f = flat(p.getViewDirection());
  const g = groundAt(dim, add(p.location, scale(f, 3)));
  if (!g) return "No ground for the serpent (water)";
  let yaw = yawOf(f);
  const e = spawnConstruct(dim, ENT.serpent, g.loc, p.id, yaw);
  if (!e) return "The serpent could not form here";
  let pos = g.loc;
  let target: Entity | undefined = enemyInSight(p, T.seek);
  let burning = false;
  let bites = 0;
  let nextBite = 10;
  let coilUntil = -1;
  let coilAnchor = pos;
  let nextSweep = 40;
  const ignition = () => {
    if (burning) return;
    burning = true;
    setBurning(e, true);
    particle(dim, P.flash, add(pos, v(0, 2.5, 0)));
    sound(dim, S.ignite, pos, 1.3, 0.7);
    clearFollowUp(s, "serpent");
  };
  setFollowUp(s, "serpent", T.duration, ignition);
  setActive(s, "Black Serpent", T.duration);
  anim(p, "serpent");
  sound(dim, S.hiss, pos, 1.3, 0.9);
  sized(dim, P.ring, pos, 2.5);
  entityAnim(e, "animation.sekiyu.serpent.rise");
  const end = () => {
    clearFollowUp(s, "serpent");
    spawnPool(dim, pos, 2.5, p.id, { burning });
    if (burning) {
      particle(dim, P.fireColumn, pos);
      for (const t of enemiesNear(dim, pos, 3, p)) {
        hurt(t, T.collapseDamage, p);
        ignite(t, 4);
      }
      ignitePoolsNear(dim, pos, 3);
    } else sized(dim, P.ring, pos, 3);
    removeConstruct(e);
  };
  addTask("black_serpent", (age) => {
    if (!e.isValid) return false;
    if (age >= T.duration || !p.isValid) {
      end();
      return false;
    }
    const head = add(pos, scale(fwd(yaw), 2.2));
    // targeting
    if (age % 10 === 0 || !target || !target.isValid) {
      const aimed = p.isValid ? enemyInSight(p, T.seek) : undefined;
      if (aimed) target = aimed;
      else if (!target || !target.isValid || dist(target.location, p.location) > T.seek) target = enemiesNear(dim, p.location, 16, p)[0];
    }
    const coiling = age < coilUntil && target?.isValid;
    let goal: { x: number; y: number; z: number };
    if (target && target.isValid) goal = target.location;
    else goal = add(p.location, v(Math.cos(age * 0.05) * 4, 0, Math.sin(age * 0.05) * 4));
    const toGoal = sub(goal, head);
    const d = Math.hypot(toGoal.x, toGoal.z);
    const dir = d > 0.05 ? norm(v(toGoal.x, 0, toGoal.z)) : fwd(yaw);
    const near = target?.isValid && d < 6;
    const speed = coiling ? 0 : near ? T.thickSpeed : T.speed;
    if (speed > 0 && d > 1.2) {
      const sway = scale(rightOf(dir), Math.sin(age * 0.35) * 0.12);
      const next = add(add(pos, scale(dir, speed)), sway);
      if (age % 2 === 0) {
        const gg = groundAt(dim, next);
        if (gg) next.y = gg.loc.y;
        else next.y = pos.y;
      } else next.y = pos.y;
      pos = next;
      yaw = yawOf(dir);
    }
    try {
      e.teleport(pos, { rotation: { x: 0, y: yaw } });
    } catch {
      return false;
    }
    // heavy crude: coil and hold
    if (coiling && target) {
      if (dist(target.location, coilAnchor) > 0.4) {
        try {
          target.teleport(coilAnchor, { keepVelocity: false });
        } catch {
          // immovable
        }
      }
      if ((coilUntil - age) % 10 === 0) hurt(target, 1, p);
    }
    // bite
    if (target && target.isValid && age >= nextBite && dist(head, center(target)) <= T.reach + 1) {
      nextBite = age + T.biteEvery;
      bites++;
      entityAnim(e, "animation.sekiyu.serpent.bite");
      hurt(target, T.biteDamage + (burning ? T.fireBonus : 0), p);
      oilSlow(target, 40, 2);
      if (burning) ignite(target, 4);
      particle(dim, burning ? P.fire : P.splash, center(target));
      sound(dim, S.bite, head, 1.1, 1);
      if (bites % T.constrictEvery === 0) {
        coilUntil = age + T.constrictTicks;
        coilAnchor = { ...target.location };
        sound(dim, S.squelch, coilAnchor, 1, 0.8);
      }
    }
    // tail sweep when surrounded
    if (age >= nextSweep) {
      const around = enemiesNear(dim, pos, T.sweepRadius, p);
      if (around.length >= 2) {
        nextSweep = age + 40;
        entityAnim(e, "animation.sekiyu.serpent.sweep");
        sized(dim, burning ? P.fireRing : P.ring, pos, T.sweepRadius);
        for (const t of around) {
          hurt(t, T.sweepDamage, p);
          knockFrom(t, pos, 1.4, 0.35);
          if (burning) ignite(t, 3);
        }
      }
    }
    if (age % 3 === 0) directed(dim, P.spray, add(pos, v(0, 0.3, 0)), scale(fwd(yaw), -1), 0.5);
    if (burning && age % 5 === 0) particle(dim, P.fire, add(head, v(0, 1.5, 0)));
    if (age % 50 === 0) sound(dim, S.hiss, head, 0.7, 1.1);
    return true;
  });
  return true;
}

const fwd = (yaw: number) => v(-Math.sin((yaw * Math.PI) / 180), 0, Math.cos((yaw * Math.PI) / 180));

