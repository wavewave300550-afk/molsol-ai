import { Entity } from "@minecraft/server";
import { ENT, TUNING } from "../config.js";
import { enemiesNear, hurt, ignite, knockFrom, oilSlow } from "../core/combat.js";
import { anim, P, particle, S, shake, sized, sound } from "../core/fx.js";
import { addTask, later } from "../core/tasks.js";
import { add, dist, scale, v } from "../core/vec.js";
import { removeConstruct, setBurning, spawnConstruct } from "../constructs.js";
import { burningPoolAt, groundAt, ignitePoolsNear, spawnPool } from "../pools.js";
import { clearFollowUp, setActive, setFollowUp } from "../state.js";
import { CastResult, Ctx } from "./types.js";

/**
 * 3 - Black Geyser: the ground bubbles where you aim (22 blocks), then three high-pressure
 * geysers erupt: damage, strong launch, heavy-oil Slowness, a thick slick over the area.
 * Tap again (during the build-up or within 3s after) to ignite: fire columns and a burning field.
 */
export function castGeyser(c: Ctx): CastResult {
  const { p, s, dim } = c;
  const T = TUNING.geyser;
  const eye = p.getHeadLocation();
  const look = p.getViewDirection();
  let aim = add(eye, scale(look, 12));
  try {
    const hit = dim.getBlockFromRay(eye, look, { maxDistance: T.range, includeLiquidBlocks: true, includePassableBlocks: false });
    if (hit) aim = add(hit.block.location, hit.faceLocation);
  } catch {
    // out of range: 12 blocks ahead
  }
  const g = groundAt(dim, aim);
  if (!g) return "Nothing to erupt from there (water or void)";
  const at = g.loc;
  let ignited = g.igniter || burningPoolAt(dim, at);
  let erupted = false;
  const spouts: Entity[] = [];
  const points = [at];
  const a0 = Math.random() * Math.PI * 2;
  for (const k of [0, 1]) {
    const a = a0 + k * Math.PI * 0.9;
    const q = groundAt(dim, add(at, v(Math.cos(a) * T.spread, 0, Math.sin(a) * T.spread)));
    if (q) points.push(q.loc);
  }
  const fireBurst = () => {
    ignitePoolsNear(dim, at, T.poolRadius + T.spread);
    for (const q of points) particle(dim, P.fireColumn, q);
    particle(dim, P.flash, add(at, v(0, 1, 0)));
    sound(dim, S.ignite, at, 1.3, 0.8);
    for (const sp of spouts) setBurning(sp, true);
    for (const t of enemiesNear(dim, at, T.fireRadius, p)) {
      hurt(t, T.fireDamage, p);
      ignite(t, T.fireSeconds);
    }
  };
  setFollowUp(s, "geyser", T.telegraph + T.igniteWindow, () => {
    if (ignited) return;
    ignited = true;
    if (erupted) {
      fireBurst();
      clearFollowUp(s, "geyser");
    } else sound(dim, S.ignite, at, 0.8, 1.3);
  });
  setActive(s, "Black Geyser", T.telegraph + 20);
  anim(p, "geyser");
  sound(dim, S.rumble, at, 1.2, 1);
  spawnPool(dim, at, 1.2, p.id, { ticks: 60 });
  addTask("geyser_telegraph", (age) => {
    if (age % 2 === 0) for (const q of points) particle(dim, P.bubble, add(q, v(0, 0.2, 0)));
    if (age === 6) sized(dim, P.ring, at, 1.5);
    if (age < T.telegraph) return true;
    erupted = true;
    sound(dim, S.erupt, at, 1.4, 1);
    if (p.isValid) shake(p, 0.18, 0.5);
    const hitIds = new Set<string>();
    for (const q of points) {
      const sp = spawnConstruct(dim, ENT.geyser, q, p.id, Math.random() * 360);
      if (sp) {
        spouts.push(sp);
        setBurning(sp, ignited);
        later(30, () => removeConstruct(sp));
      }
      particle(dim, ignited ? P.fireColumn : P.column, q);
      sized(dim, P.ring, q, 2.2);
      for (const t of enemiesNear(dim, q, T.radius, p)) {
        if (hitIds.has(t.id) || Math.abs(t.location.y - q.y) > 3) continue;
        hitIds.add(t.id);
        hurt(t, T.damage, p);
        knockFrom(t, q, 0.25, T.launch);
        oilSlow(t, T.slowTicks, 1);
        if (ignited) ignite(t, T.fireSeconds);
      }
    }
    spawnPool(dim, at, T.poolRadius, p.id, { burning: ignited });
    for (const q of points.slice(1)) if (dist(q, at) > 1.5) spawnPool(dim, q, 1.6, p.id, { burning: ignited });
    if (ignited) {
      fireBurst();
      clearFollowUp(s, "geyser");
    }
    return false;
  });
  return true;
}
