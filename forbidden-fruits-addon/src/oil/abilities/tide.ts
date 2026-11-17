import { BUDGET, ENT, TUNING } from "../config.js";
import { enemiesNear, hurt, ignite, knockAlong, oilSlow } from "../core/combat.js";
import { anim, directed, P, particle, S, sized, sound } from "../core/fx.js";
import { addTask } from "../core/tasks.js";
import { add, dot, flat, rightOf, scale, v } from "../core/vec.js";
import { ownedConstructs, removeConstruct, setBurning, spawnConstruct } from "../constructs.js";
import { burningPoolAt, groundAt, ignitePoolsNear, spawnPool } from "../pools.js";
import { clearFollowUp, setActive, setFollowUp } from "../state.js";
import { CastResult, Ctx } from "./types.js";
import { yawOf } from "./util.js";

/**
 * 1 - Black Tide: a 6-block-wide wave of heavy crude (3D model) rolls 18 blocks forward.
 * Heavy oil: damage, knockback, Slowness, oil slicks left behind. Ignition: tap again (or roll
 * it over burning oil) and the whole wave burns, igniting everything it touches.
 */
export function castTide(c: Ctx): CastResult {
  const { p, s, dim } = c;
  const T = TUNING.tide;
  if (ownedConstructs(p.id, ENT.tide).length >= BUDGET.tidesPerPlayer) return "Your tides are still rolling";
  const f = flat(p.getViewDirection());
  const r = rightOf(f);
  const yaw = yawOf(f);
  const g = groundAt(dim, add(p.location, scale(f, 2)));
  if (!g) return "No ground to flood (water)";
  const e = spawnConstruct(dim, ENT.tide, g.loc, p.id, yaw);
  if (!e) return "The wave could not form here";
  let pos = g.loc;
  let travelled = 0;
  let burning = false;
  let lastPool = 0;
  const hit = new Set<string>();
  const ignition = () => {
    if (burning) return;
    burning = true;
    setBurning(e, true);
    sound(dim, S.ignite, pos, 1.2, 0.8);
    particle(dim, P.flash, add(pos, v(0, 1.5, 0)));
    ignitePoolsNear(dim, pos, T.halfWidth);
  };
  const life = Math.ceil(T.distance / T.speed);
  setFollowUp(s, "tide", life, ignition);
  setActive(s, "Black Tide", life);
  anim(p, "tide");
  sound(dim, S.tide, g.loc, 1.3, 1);
  sized(dim, P.ring, g.loc, 2.5);
  const collapse = () => {
    sized(dim, burning ? P.fireRing : P.ring, pos, T.halfWidth);
    spawnPool(dim, pos, T.poolRadius + 0.6, p.id, { burning });
    removeConstruct(e);
    clearFollowUp(s, "tide");
  };
  addTask("black_tide", (age) => {
    if (!e.isValid) {
      clearFollowUp(s, "tide");
      return false;
    }
    travelled += T.speed;
    const next = add(pos, scale(f, T.speed));
    if (age % 3 === 0) {
      const gg = groundAt(dim, next);
      if (!gg) {
        collapse();
        return false;
      }
      next.y = gg.loc.y;
    } else next.y = pos.y;
    // a wall stops the wave (it crashes against it)
    try {
      const wall = dim.getBlock(add(next, add(scale(f, 1.2), v(0, 1.2, 0))));
      if (wall && !wall.isAir && !wall.isLiquid) {
        collapse();
        return false;
      }
    } catch {
      // unloaded
    }
    pos = next;
    try {
      e.teleport(pos, { rotation: { x: 0, y: yaw } });
    } catch {
      return false;
    }
    if (!burning && burningPoolAt(dim, pos)) ignition();
    for (const t of enemiesNear(dim, pos, T.halfWidth + T.depth + 1, p)) {
      if (hit.has(t.id)) continue;
      const d = { x: t.location.x - pos.x, y: t.location.y - pos.y, z: t.location.z - pos.z };
      const fwd = dot(d, f);
      if (Math.abs(dot(d, r)) > T.halfWidth || fwd < -T.depth || fwd > T.depth + 0.8 || d.y < -1.5 || d.y > T.height) continue;
      hit.add(t.id);
      hurt(t, T.damage + (burning ? T.fireBonus : 0), p);
      knockAlong(t, f, T.knock, T.lift);
      oilSlow(t, T.slowTicks, T.slowAmp);
      if (burning) ignite(t, T.fireSeconds);
      particle(dim, burning ? P.fire : P.splash, add(t.location, v(0, 1, 0)));
    }
    if (travelled - lastPool >= T.poolEvery) {
      lastPool = travelled;
      spawnPool(dim, add(pos, scale(f, -1.5)), T.poolRadius, p.id, { burning });
    }
    if (burning && age % 4 === 0) ignitePoolsNear(dim, pos, T.halfWidth);
    if (age % 2 === 0) {
      for (const side of [-1, 0, 1]) {
        const at = add(add(pos, scale(r, side * T.halfWidth * 0.75)), add(scale(f, 1.2), v(0, 2.6, 0)));
        directed(dim, P.spray, at, add(f, v(0, 0.6, 0)), 0.8);
      }
      if (burning) particle(dim, P.fire, add(pos, v(0, 2.2, 0)));
    }
    if (age % 6 === 0) particle(dim, burning ? P.smoke : P.drip, add(pos, v(0, 3, 0)));
    if (age % 12 === 0) sound(dim, burning ? S.crackle : S.gurgle, pos, 0.8, 1);
    if (travelled >= T.distance) {
      collapse();
      return false;
    }
    return true;
  });
  return true;
}
