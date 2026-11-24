import { Entity, EntityDamageCause, Player } from "@minecraft/server";
import { COLORS, TUNING } from "../config.js";
import { actionbar, emit, ring, sigil, sound } from "../core/fx.js";
import { burn, fightersNear, foesNear, hurt, isPlayer, push } from "../core/targets.js";
import { add, flatDir, hdist, v, V3 } from "../core/vec.js";
import { Path } from "../paths/path.js";
import { skyArc } from "../paths/shapes.js";
import { arenaRing } from "./arena.js";
import { JoanBoss, SkillGen } from "./joan.js";
import { death, transition } from "./scenes.js";
import { skillByName } from "./skills/index.js";

/** Advance one boss by one tick. Returns false once the boss is gone. */
export function tickBoss(b: JoanBoss, now: number): boolean {
  if (!b.valid) return false;
  b.now = now;
  b.field.tick(now);
  b.runTasks();
  if (b.mode === "dead") return false;
  if (b.mode === "fight") {
    b.brain.observe(now);
    if (b.flags.pendingDeath) {
      b.start("death", death(b), false);
    } else if (b.flags.pendingTransition && b.phase === 1) {
      b.start("transition", transition(b), false);
    } else if (shouldUlt(b, now) && ultTarget(b)) {
      const def = skillByName("stake");
      const t = ultTarget(b);
      if (def && t) b.start("stake", wrap(b, def.name, def.run(b, t, undefined), true), false);
    } else {
      leash(b, now);
      if (!b.action && now >= b.stunUntil) {
        const c = b.brain.choose(now);
        if (c) b.start(c.def.name, wrap(b, c.def.name, c.gen, c.def.big));
        else idle(b, now);
      }
    }
  } else if (b.mode === "dying" && !b.action) {
    // safety net: a death scene that was interrupted by a reload
    b.start("death", death(b), false);
  }
  b.stepAction();
  return true;
}

function ultTarget(b: JoanBoss): Player | undefined {
  const t = b.brain.target;
  if (t && t.isValid) return t;
  return b.fighters()[0];
}

function shouldUlt(b: JoanBoss, now: number): boolean {
  if (b.phase !== 2) return false;
  if (b.action && (!b.action.interruptible || b.action.name === "stake")) return false;
  if (b.hpFrac > TUNING.ultimateAt) return false;
  if (b.flags.ultCount === 0) return true;
  return now - b.flags.lastUlt > TUNING.ultimateRepeat;
}

/** Wrap a skill so the global cooldown applies when it ends (and Phase II can chain). */
function* wrap(b: JoanBoss, name: string, gen: SkillGen, big: boolean): SkillGen {
  yield* gen;
  const gcd = TUNING.gcd[b.phase >= 2 ? 2 : 1] ?? 30;
  b.gcdUntil = Math.max(b.gcdUntil, b.now + Math.round(gcd * (big ? 1.3 : 0.6)));
  if (b.phase >= 2) phaseTwoChain(b, name);
}

/**
 * Phase II only: the Saint does not pause between roads. After a skill she may
 * chain straight into a follow-up chosen from the situation it created:
 *   target dragged close         -> Banner Wrap / strikes
 *   target riding one of her roads -> she surges along that very road
 *   after a trap (halo / siege)  -> Crossroads Judgment (burning trail)
 *   target far and in the open   -> Burning Pilgrimage (surge)
 * At most two links per chain, so a breathing window always follows.
 */
function phaseTwoChain(b: JoanBoss, last: string): void {
  if (b.brain.combo || b.chainLinks >= 2) {
    b.chainLinks = 0;
    return;
  }
  const t = b.brain.target;
  if (!t || !t.isValid || Math.random() > 0.55) {
    b.chainLinks = 0;
    return;
  }
  const d = hdist(b.pos, t.location);
  const road = b.field.riderPath(t);
  let next: string | undefined;
  let data: unknown;
  if (d < 4 && last !== "melee" && b.ready("melee")) next = "melee";
  else if (road && last !== "surge") {
    next = "surge";
    data = road;
  } else if ((last === "salvation" || last === "orleans" || last === "convergence") && b.ready("trail")) next = "trail";
  else if (d > 10 && last !== "surge" && b.ready("surge")) next = "surge";
  if (!next) {
    b.chainLinks = 0;
    return;
  }
  b.chainLinks++;
  b.gcdUntil = b.now; // the chain skips the breathing room...
  b.brain.queueCombo(next, `phase II chain after ${last}`, 12, data);
}

/** Between skills: walk in (native AI), face the target, keep the standard aloft. */
function idle(b: JoanBoss, now: number): void {
  const t = b.brain.target;
  if (!t || !t.isValid) {
    if (b.noTargetSince < 0) b.noTargetSince = now;
    return;
  }
  b.noTargetSince = -1;
  if (now % 10 === 0 && t.isValid && hdist(b.pos, t.location) < 5) b.face(t.location);
}

/** Stay near the arena; reset the encounter when everyone has left. */
function leash(b: JoanBoss, now: number): void {
  // she always walks the road back when pulled out of her arena
  if (!b.action && hdist(b.pos, b.home) > TUNING.leashRadius) {
    b.start("return", returnHome(b), true);
    return;
  }
  const engaged = b.fighters(TUNING.leashRadius + 8).length + fightersNear(b.dim, b.pos, 24).length;
  if (!engaged) {
    if (b.noTargetSince < 0) b.noTargetSince = now;
    if (now - b.noTargetSince > TUNING.resetAfterTicks) resetFight(b);
    return;
  }
  b.noTargetSince = -1;
}

function resetFight(b: JoanBoss): void {
  b.noTargetSince = -1;
  b.interrupt();
  for (const p of b.field.livePaths()) if (p.o.tag !== "arena") b.field.retire(p, b.now, 10);
  b.field.scars = [];
  b.participants.clear();
  try {
    b.e.getComponent("minecraft:health")?.resetToMaxValue();
    if (b.phase >= 2) b.e.triggerEvent("joan:brighten");
    b.e.nameTag = "Joan of Arc";
  } catch {
    // ignore
  }
  b.setPhase(1);
  b.flags.ultCount = 0;
  b.flags.martyrEcho = false;
  b.flags.bell.clear();
  b.teleport(b.home);
  arenaRing(b);
}

/** She returns to the arena along a road through the sky. */
function* returnHome(b: JoanBoss): SkillGen {
  const road = b.airRoad(skyArc(add(b.pos, v(0, 0.2, 0)), b.home, 6), { kind: "arc", speed: 0.7, form: b.tel(), life: 80,
    carryPlayers: false, memory: false, crossings: false });
  b.anim("surge_windup");
  if (road && hdist(road.pointAt(road.length), b.home) < 4) {
    yield b.tel();
    b.anim("surge_ride");
    yield* b.ride(road, 0, road.length, 1.2, 4, true);
  } else {
    if (road) b.field.retire(road, b.now, 1);
    yield 10;
  }
  if (hdist(b.pos, b.home) > 4) {
    // trees, hills or houses blocked the sky road: she steps through the light instead
    emit(b.dim, "joan:pillar", b.pos, { h: 8, color: COLORS.roadGold, life: 0.6, size: 0.6 });
    b.teleport(b.home);
    emit(b.dim, "joan:pillar", b.home, { h: 8, color: COLORS.roadGold, life: 0.6, size: 0.6 });
  }
  b.anim("surge_slam");
  b.impactFx(b.pos, 2.5);
  yield 12;
}

// =========================================================================== reactions & secrets
/** The bells of Domremy: once per phase, a rung bell makes her stop and listen. */
export function bellRung(b: JoanBoss, by: Player): boolean {
  if (b.mode !== "fight" || b.invulnerable) return false;
  if (b.flags.bell.has(b.phase)) return false;
  if (b.action && !b.action.interruptible) return false;
  b.flags.bell.add(b.phase);
  b.start("listen", listen(b), false);
  for (const p of b.fighters(48)) p.sendMessage("§eThe bells of Domremy ring... §fJoan stops to hear her Voices.");
  return true;
}

function* listen(b: JoanBoss): SkillGen {
  b.anim("listen");
  b.stunUntil = b.now + 72;
  b.vulnerableUntil = b.now + 72;
  sound(b.dim, "joan.bell.high", b.pos, 1, 1);
  emit(b.dim, "joan:mote", add(b.pos, v(0, 2, 0)), { size: 1.2, life: 3.4, color: COLORS.white, speed: 1 });
  yield 72;
  b.anim("taunt");
  yield 20;
}

/** A projectile that rode one of her own roads struck her: the road turns against its maker. */
export function turnedRoad(b: JoanBoss, shooter?: Entity): void {
  if (b.mode !== "fight") return;
  if (b.now - b.flags.turnedRoadAt > 2) return; // filterDamage marked this hit
  if (shooter && isPlayer(shooter) && !b.flags.tutorial.has(`turned:${shooter.id}`)) {
    b.flags.tutorial.add(`turned:${shooter.id}`);
    shooter.sendMessage("§6The road turns against its maker! §7(projectiles carried by her roads hit twice as hard)");
  }
  if (b.action && b.action.interruptible && b.now >= b.stunUntil) b.start("stagger", stagger(b), false);
}

function* stagger(b: JoanBoss): SkillGen {
  b.anim("stagger");
  b.stunUntil = b.now + 18;
  emit(b.dim, "joan:burst", add(b.pos, v(0, 1.4, 0)), { color: COLORS.white, size: 1 });
  yield 18;
}

/** Phase II: where two roads cross, a pyre waits (warned by a ring of embers). */
export function crossingPyre(b: JoanBoss, at: V3): void {
  if (b.phase < 2) return;
  const warn = Math.max(24, b.tel(2.2));
  ring(b.dim, at, 2.2, 0.4, warn / 20, COLORS.burning);
  sigil(b.dim, at, 3.4, warn / 20, COLORS.warn);
  b.later(warn, () => {
    if (!b.valid || b.mode === "dying") return;
    emit(b.dim, "joan:pillar", at, { h: 7, color: COLORS.burning, life: 0.7, size: 0.8 });
    emit(b.dim, "joan:ember", add(at, v(0, 0.5, 0)), { size: 1.2, life: 1.0 });
    sound(b.dim, "joan.fire.ignite", at, 1, 1);
    for (const e of foesNear(b.dim, at, 2.2)) {
      if (hdist(e.location, at) > 1.9) continue;
      hurt(e, 7, b.e, EntityDamageCause.fire);
      burn(e, 3);
      push(e, add(flatDir(at, e.location), v(0, 0.55, 0)));
    }
  });
}

/** First-time hints so players learn the rules of the roads. */
export function tutorial(b: JoanBoss, e: Entity, p: Path): void {
  if (!isPlayer(e)) return;
  const tip = (key: string, text: string) => {
    const k = `${key}:${e.id}`;
    if (b.flags.tutorial.has(k)) return;
    b.flags.tutorial.add(k);
    actionbar(e, text);
  };
  b.brain.noteCaught(e);
  if (p.o.kind === "stake") tip("stake", "§6Strike the Lily Waystones to turn these roads white!");
  else if (p.o.kind === "loop") tip("loop", b.phase >= 2 ? "§6The halo is too tall to jump - ride it to a TRUE exit." : "§eJump the halo, or ride it to an exit - beware the inverted lily.");
  else if (p.o.kind === "false") tip("false", "§cThe inverted lily marks a lie.");
  else if (p.o.burning) tip("burn", "§6The roads burn now. §7Step off them, or sneak to fight the current.");
  else tip("road", "§eA Divine Road carries you. §7Sneak to resist the current, jump to cross it.");
}

