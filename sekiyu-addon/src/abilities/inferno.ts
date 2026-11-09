import { Player } from "@minecraft/server";
import { ENT, TUNING } from "../config.js";
import { enemiesNear, hurt, ignite, knockFrom } from "../core/combat.js";
import { anim, center, P, particle, S, shake, sized, sound } from "../core/fx.js";
import { addTask, later } from "../core/tasks.js";
import { add, dist, v } from "../core/vec.js";
import { removeConstruct, setBurning, spawnConstruct } from "../constructs.js";
import { ignitePoolsNear, spawnPool } from "../pools.js";
import { syncProperties } from "../power.js";
import { now, setActive } from "../state.js";
import { CastResult, Ctx } from "./types.js";

const FOG_ID = "sekiyu:inferno_fog";
const FOG_TAG = "sekiyu_inferno";

function fog(p: Player, on: boolean): void {
  try {
    p.runCommand(on ? `fog @s push ${FOG_ID} ${FOG_TAG}` : `fog @s remove ${FOG_TAG}`);
  } catch {
    // fog unavailable: cosmetic only
  }
}

/**
 * 8 - Black Inferno (ultimate): 1.2s eruption - geysers burst in a ring, an oil flood spreads
 * 12 blocks and leaves pools everywhere - then everything ignites: heavy fire damage with
 * falloff, burning pools for 8s, smoke-dark fog for nearby players for 12s. The caster's own fire
 * never burns them (controlled ignition). Blocks are never destroyed.
 */
export function castInferno(c: Ctx): CastResult {
  const { p, s, dim } = c;
  const T = TUNING.inferno;
  const at = { ...p.location };
  anim(p, "inferno");
  sound(dim, S.infernoRise, at, 1.5, 1);
  setActive(s, "BLACK INFERNO", T.windup + 40);
  s.fallGuardUntil = now() + T.windup + 60;
  const spouts: ReturnType<typeof spawnConstruct>[] = [];
  const fogged: Player[] = [];
  for (const other of dim.getPlayers({ location: at, maxDistance: 40 })) {
    fog(other, true);
    fogged.push(other);
  }
  later(T.fogTicks, () => {
    for (const other of fogged) if (other.isValid) fog(other, false);
  });
  addTask("black_inferno", (age) => {
    if (!p.isValid) return false;
    if (age % 4 === 0 && age < T.windup) {
      const k = age / 4;
      const a = k * (Math.PI / 3);
      const r = 5;
      const q = add(at, v(Math.cos(a) * r, 0, Math.sin(a) * r));
      const sp = spawnConstruct(dim, ENT.geyser, q, p.id, Math.random() * 360);
      if (sp) {
        spouts.push(sp);
        later(T.windup + 30 - age, () => removeConstruct(sp));
      }
      particle(dim, P.column, q);
      sized(dim, P.ring, at, 2 + k * 1.7);
      spawnPool(dim, q, 2.6, p.id, { ticks: T.burnTicks + 40 });
      if (k % 2 === 0) spawnPool(dim, add(at, v(Math.cos(a + 0.5) * 9, 0, Math.sin(a + 0.5) * 9)), 3.0, p.id, { ticks: T.burnTicks + 40 });
      sound(dim, S.erupt, q, 0.9, 0.8 + k * 0.05);
    }
    if (age === 0) {
      spawnPool(dim, at, 3.2, p.id, { ticks: T.burnTicks + 40 });
      try {
        p.addEffect("slowness", T.windup, { amplifier: 3, showParticles: false });
      } catch {
        // dead
      }
    }
    if (age < T.windup) {
      if (age % 3 === 0) particle(dim, P.drip, add(at, v(0, 1.2, 0)));
      return true;
    }
    // IGNITION
    s.burningUntil = now() + 60;
    syncProperties(p, s);
    for (const sp of spouts) setBurning(sp, true);
    ignitePoolsNear(dim, at, T.radius + 3);
    particle(dim, P.flash, add(at, v(0, 1.5, 0)));
    particle(dim, P.fireColumn, at);
    sized(dim, P.fireRing, at, T.radius);
    sized(dim, P.fireRing, add(at, v(0, 1, 0)), T.radius * 0.6);
    particle(dim, P.ember, add(at, v(0, 2, 0)));
    particle(dim, P.smoke, add(at, v(0, 3, 0)));
    sound(dim, S.infernoBlast, at, 2, 1);
    for (const other of dim.getPlayers({ location: at, maxDistance: 30 })) shake(other, other.id === p.id ? 0.6 : 0.35, 1.0);
    for (const t of enemiesNear(dim, at, T.radius, p, 48)) {
      const fall = 1 - 0.5 * Math.min(1, dist(t.location, at) / T.radius);
      hurt(t, T.damage * fall, p);
      ignite(t, T.fireSeconds);
      knockFrom(t, at, T.knock * fall, 0.5);
      particle(dim, P.fire, center(t));
    }
    return false;
  });
  return true;
}

export function clearInfernoFog(p: Player): void {
  fog(p, false);
}

