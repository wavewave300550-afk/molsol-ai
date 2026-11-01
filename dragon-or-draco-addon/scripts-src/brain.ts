import { Entity, Player } from "@minecraft/server";
import { BALANCE } from "./balance.js";
import {
  chooseAttack, centerOf, endAction, isProtectedPlayer, lineOfSight, startAction, startAttack, tickAction, victims,
} from "./combat.js";
import {
  ACTION_TICKS, DragonState, event, isLiving, lock, now, safe, sec, setAction, setFlight, setProp,
} from "./dragon.js";
import { beginLanding, canTakeOff, startTakeoff, tickFlight } from "./flight.js";
import { add, dist, hdist, v3 } from "./vec.js";

const TR = BALANCE.territory;

/** One tick of a dragon's life. */
export function think(s: DragonState): void {
  if (s.dying) {
    tickDying(s);
    return;
  }
  const t = now();
  if ((t + s.id.length) % 5 === 0) perceive(s);
  if (s.run) tickAction(s);
  if (s.flight !== "ground") tickFlight(s);
  updateRunFlag(s);
  if (s.run || t < s.gapUntil) return;
  if (s.flight === "takeoff" || s.flight === "landing") return;
  const target = isLiving(s.target) ? s.target : undefined;
  if (target) combat(s, target);
  else if (s.flight === "ground") idle(s);
}

// ------------------------------------------------------------------------------------------------ perception

function players(s: DragonState, radius: number): Player[] {
  const e = s.entity;
  const list = safe(() => e.dimension.getPlayers({ location: e.location, maxDistance: radius })) ?? [];
  return list.filter((p) => isLiving(p) && !isProtectedPlayer(p));
}

const nearCountCache = new Map<string, number>();

function perceive(s: DragonState): void {
  const e = s.entity;
  const pos = e.location;
  const t = now();

  // keep or drop the current target
  if (s.target) {
    const tg = s.target;
    const valid = isLiving(tg) && tg.dimension.id === e.dimension.id && !isProtectedPlayer(tg);
    if (valid && dist(tg.location, pos) <= TR.warn_radius + 8 && hdist(tg.location, s.home) <= TR.leash_radius + 16) {
      s.lastTargetSeen = t;
    }
    if (!valid || t - s.lastTargetSeen > sec(TR.forget_after)) calmDown(s);
  }

  const near = players(s, TR.warn_radius);
  near.sort((a, b) => dist(a.location, pos) - dist(b.location, pos));
  if (!s.target && near.length) {
    const p = near[0];
    const d = dist(p.location, pos);
    const eye = add(pos, v3(0, 4, 0));
    const seen = lineOfSight(s, eye, centerOf(p));
    if (d <= TR.danger_radius && seen) {
      becomeHostile(s, p);
    } else if (seen && s.flight === "ground" && !s.run) {
      const warnedAt = s.warned.get(p.id);
      if (warnedAt !== undefined && t - warnedAt >= sec(TR.linger_before_attack) && t - warnedAt < sec(TR.warn_cooldown * 2)) {
        becomeHostile(s, p);
      } else if (t - s.lastWarn >= sec(TR.warn_cooldown) && t >= s.gapUntil) {
        // warning roar: face the intruder and roar, no damage
        s.lastWarn = t;
        s.warned.set(p.id, t);
        startAction(s, "roar", p);
      }
    }
  }
  for (const [id, at] of s.warned) if (t - at > sec(TR.warn_cooldown * 3)) s.warned.delete(id);
  nearCountCache.set(s.id, s.target ? victims(s, pos, BALANCE.buffet.max_range).length : 0);
}

export function becomeHostile(s: DragonState, who: Entity): void {
  if (!isLiving(who) || isProtectedPlayer(who)) return;
  const fresh = !s.target;
  s.target = who;
  s.lastTargetSeen = now();
  s.chaseBest = 1e9;
  s.chaseBestTick = now();
  if (!s.enraged && dist(who.location, s.entity.location) > TR.danger_radius - 1) {
    s.enraged = true;
    event(s, "dod:enrage");
  }
  if (fresh && s.flight === "ground" && !s.run) s.combatRoarPending = true;
}

function calmDown(s: DragonState): void {
  s.target = undefined;
  s.combatRoarPending = false;
  if (s.enraged) {
    s.enraged = false;
    event(s, "dod:calm");
  }
}

function updateRunFlag(s: DragonState): void {
  const tg = s.target;
  const run = !!tg && isLiving(tg) && s.flight === "ground" && !s.locked && hdist(tg.location, s.entity.location) > 8;
  setProp(s, "dod:run", run);
}

// ------------------------------------------------------------------------------------------------ decisions

function combat(s: DragonState, target: Entity): void {
  const pos = s.entity.location;
  const t = now();
  const d = hdist(pos, target.location);
  const dy = target.location.y - pos.y;

  if (s.flight === "ground") {
    if (s.combatRoarPending && t - s.lastCombatRoar >= sec(BALANCE.roar.combat_roar_cooldown) && d > 5) {
      s.combatRoarPending = false;
      s.lastCombatRoar = t;
      startAction(s, "roar", target);
      return;
    }
    s.combatRoarPending = false;
    // out of reach on foot: on a ledge / in the air, or no progress while chasing
    if (d > 9) {
      if (d < s.chaseBest - 1) {
        s.chaseBest = d;
        s.chaseBestTick = t;
      }
    } else {
      s.chaseBest = d;
      s.chaseBestTick = t;
    }
    const stuck = t - s.chaseBestTick > sec(8);
    if ((dy > BALANCE.flight.takeoff_when_target_above && d < 32) || stuck) {
      if (canTakeOff(s)) {
        startTakeoff(s, "combat");
        s.chaseBestTick = t;
        return;
      }
      s.chaseBestTick = t; // cannot fly here: keep trying on foot
    }
    const k = chooseAttack(s, target, nearCountCache.get(s.id) ?? 0);
    if (!k) return;
    if (k === "fire" && d > 12 && Math.random() < 0.3 && canTakeOff(s)) {
      startTakeoff(s, "combat"); // fight from the air for a while
      return;
    }
    startAttack(s, k);
    return;
  }
  if (s.flight === "fly" || s.flight === "glide") {
    if (s.landingGoal) return;
    const k = chooseAttack(s, target, 0);
    if (k) startAttack(s, k);
  }
}

function idle(s: DragonState): void {
  const t = now();
  if (t < s.nextIdle) return;
  const I = BALANCE.idle;
  s.nextIdle = t + sec(I.action_interval_min + Math.random() * (I.action_interval_max - I.action_interval_min));
  const r = Math.random();
  const fly = BALANCE.flight.patrol_flight_chance;
  if (r < fly) {
    if (canTakeOff(s)) startTakeoff(s, "patrol");
  } else if (r < fly + 0.35) {
    startAction(s, "look");
  } else if (r < fly + 0.6) {
    startAction(s, "stretch");
  }
}

// ------------------------------------------------------------------------------------------------ death

/** Called (deferred) when a hit would kill the dragon: play the 2.8 s death, then really die. */
export function beginDying(s: DragonState): void {
  if (s.dying) return;
  s.dying = true;
  s.dyingTick = now();
  s.run = undefined;
  s.target = undefined;
  s.landingGoal = undefined;
  event(s, "dod:dying");
  s.inAir = false;
  s.locked = true;
  setFlight(s, "ground");
  setProp(s, "dod:aim", 0);
  setProp(s, "dod:run", false);
  setAction(s, "death");
  safe(() => s.entity.clearVelocity());
}

function tickDying(s: DragonState): void {
  if (now() - s.dyingTick >= ACTION_TICKS.death && !s.allowKill) {
    s.allowKill = true;
    safe(() => s.entity.kill());
  }
}

export { lock, endAction, beginLanding };
