import { BUDGET, ENT, TUNING } from "../config.js";
import { enemiesInCone, enemyInSight, hurt, ignite, knockFrom, oilSlow } from "../core/combat.js";
import { anim, center, P, particle, S, sound } from "../core/fx.js";
import { addTask, later } from "../core/tasks.js";
import { dist, v } from "../core/vec.js";
import { ownedConstructs, removeConstruct, setBurning, spawnConstruct } from "../constructs.js";
import { ignitePoolsNear, spawnPool } from "../pools.js";
import { clearFollowUp, setActive, setFollowUp } from "../state.js";
import { CastResult, Ctx } from "./types.js";

/**
 * 4 - Tar Prison: viscous tar tendrils (3D model) close over the target for 4s. The target is
 * held in place (moved back to the anchor whenever it slips), slowed and suffocates in the tar.
 * Surrounding oil spreads into a slick. Tap again to ignite the prison: a burst of fire, then it
 * collapses. It always dissolves on its own after the duration.
 */
export function castPrison(c: Ctx): CastResult {
  const { p, s, dim } = c;
  const T = TUNING.prison;
  if (ownedConstructs(p.id, ENT.prison).length >= BUDGET.prisonsPerPlayer) return "Too many prisons at once";
  const target = enemyInSight(p, T.range) ?? enemiesInCone(p, 8, 0.5)[0];
  if (!target) return "No target in reach";
  const anchor = { ...target.location };
  const e = spawnConstruct(dim, ENT.prison, anchor, p.id, Math.random() * 360);
  if (!e) return "The tar could not form here";
  let done = false;
  const finish = (burst: boolean) => {
    if (done) return;
    done = true;
    clearFollowUp(s, "prison");
    if (burst) {
      setBurning(e, true);
      particle(dim, P.fireColumn, anchor);
      particle(dim, P.flash, v(anchor.x, anchor.y + 1, anchor.z));
      sound(dim, S.ignite, anchor, 1.2, 0.9);
      if (target.isValid) {
        hurt(target, T.igniteDamage, p);
        ignite(target, T.igniteFireSeconds);
        knockFrom(target, v(anchor.x + 0.01, anchor.y, anchor.z), 0.2, 0.45);
      }
      ignitePoolsNear(dim, anchor, T.poolRadius);
      later(10, () => removeConstruct(e));
    } else {
      particle(dim, P.drip, v(anchor.x, anchor.y + 1.5, anchor.z));
      removeConstruct(e);
    }
  };
  setFollowUp(s, "prison", T.duration, () => finish(true));
  setActive(s, "Tar Prison", T.duration);
  anim(p, "prison");
  sound(dim, S.squelch, anchor, 1.2, 1);
  particle(dim, P.tendril, anchor);
  spawnPool(dim, anchor, T.poolRadius, p.id, { ticks: 200 });
  addTask("tar_prison", (age) => {
    if (done) return false;
    if (!target.isValid || !e.isValid || age >= T.duration) {
      finish(false);
      return false;
    }
    if (dist(target.location, anchor) > 0.35) {
      try {
        target.teleport(anchor, { keepVelocity: false });
      } catch {
        // cannot be moved
      }
    }
    if (age % 10 === 0) oilSlow(target, 20, T.slowAmp);
    if (age > 0 && age % T.dotEvery === 0) {
      hurt(target, T.dot, p);
      particle(dim, P.drip, center(target));
    }
    if (age % 8 === 0) particle(dim, P.tendril, anchor);
    return true;
  });
  return true;
}
