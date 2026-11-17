import { Entity, Player } from "@minecraft/server";
import { TUNING } from "../config.js";
import { hurt, isEnemy, knockAlong } from "../core/combat.js";
import { addTask, later } from "../core/tasks.js";
import { add, dist, lerp, norm, scale, segmentDistance, sub, v } from "../core/vec.js";
import { anim, center, directed, P, particle, rightHand, S, sized, sound, stream } from "../core/fx.js";
import { setActive } from "../state.js";
import { CastResult, Ctx } from "./types.js";

/**
 * Ability 4 - Steam Cannon: a concentrated superheated steam bolt from the right hand.
 * The bolt is aimed at the crosshair point (eye ray, blocks included), travels 3 blocks/tick
 * up to 24 blocks, and hits the first enemy whose body is within 1.1 blocks of its path.
 * Higher gears fire a rapid 2- or 3-bolt burst (the "continuous fire" variant).
 */
export function castCannon(c: Ctx): CastResult {
  const { p, s, mode, power } = c;
  const T = TUNING.cannon;
  const bolts = T.bolts[mode] ?? 1;
  const damage = T.damage * power * (bolts > 1 ? T.multiBoltDamage : 1);
  setActive(s, bolts > 1 ? `Steam Cannon x${bolts}` : "Steam Cannon", 10 + bolts * T.burstDelay);
  anim(p, "cannon");
  for (let i = 0; i < bolts; i++) {
    if (i === 0) fireBolt(p, damage, power);
    else later(i * T.burstDelay, () => p.isValid && fireBolt(p, damage, power));
  }
  return true;
}

function fireBolt(p: Player, damage: number, power: number): void {
  const T = TUNING.cannon;
  const dim = p.dimension;
  const eye = p.getHeadLocation();
  const look = p.getViewDirection();
  // what the crosshair points at (block-limited)
  let aimDist: number = T.range;
  try {
    const hit = dim.getBlockFromRay(eye, look, { maxDistance: T.range, includeLiquidBlocks: false, includePassableBlocks: false });
    if (hit) aimDist = Math.min(T.range, dist(eye, add(hit.block.location, hit.faceLocation)));
  } catch {
    // ray left the loaded area
  }
  const origin = rightHand(p);
  const target = add(eye, scale(look, aimDist));
  const dir = norm(sub(target, origin));
  const total = Math.max(0.5, dist(origin, target));
  const blocked = aimDist < T.range - 0.01;

  directed(dim, P.jet, origin, dir, power);
  sound(dim, S.cannon, origin, 1, 0.95 + Math.random() * 0.1);

  let travelled = 0;
  const hitIds = new Set<string>();
  addTask("steam_bolt", () => {
    const a = add(origin, scale(dir, travelled));
    const step = Math.min(T.speedPerTick, total - travelled);
    const b = add(a, scale(dir, step));
    travelled += step;

    // entity collision along this tick's segment
    let victim: Entity | undefined;
    let best = Infinity;
    try {
      const mid = lerp(a, b, 0.5);
      for (const e of dim.getEntities({ location: mid, maxDistance: step / 2 + T.hitRadius + 1.2, excludeFamilies: ["inanimate"] })) {
        if (hitIds.has(e.id) || !isEnemy(e, p)) continue;
        const c = center(e);
        if (segmentDistance(c, a, b) > T.hitRadius) continue;
        const d = dist(a, c);
        if (d < best) {
          best = d;
          victim = e;
        }
      }
    } catch {
      // unloaded chunk
    }
    stream(dim, P.boltTrail, a, victim ? center(victim) : b, 1.0, dir, power);
    if (victim) {
      hitIds.add(victim.id);
      const at = center(victim);
      hurt(victim, damage, p.isValid ? p : undefined);
      knockAlong(victim, dir, T.knockback * Math.sqrt(power), 0.25);
      particle(dim, P.impact, at);
      directed(dim, P.cone, at, dir, power);
      sound(dim, S.impact, at, 1, 1.1);
      return false;
    }
    particle(dim, P.boltCore, b);
    if (travelled >= total - 1e-6) {
      if (blocked) {
        particle(dim, P.impact, b);
        sized(dim, P.ring, b, 0.9);
        sound(dim, S.hiss, b, 0.7, 1.4);
      } else {
        particle(dim, P.puff, b);
      }
      return false;
    }
    return true;
  });
  // muzzle back-blast so the shot reads as pressure leaving the arm
  particle(dim, P.puff, add(origin, v(0, 0.05, 0)));
}
