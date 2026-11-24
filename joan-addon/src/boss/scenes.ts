import { system } from "@minecraft/server";
import { COLORS } from "../config.js";
import { emit, shake, sound, title } from "../core/fx.js";
import { allPlayersNear } from "../core/targets.js";
import { groundY } from "../core/terrain.js";
import { add, flatDir, scale, v } from "../core/vec.js";
import { skyArc } from "../paths/shapes.js";
import { arenaRing } from "./arena.js";
import type { JoanBoss, SkillGen } from "./joan.js";
import { dropRewards } from "../rewards.js";

/**
 * INTRO - a road of light descends from the sky; Joan rides it down, lands on
 * one knee, plants the standard, rises and unfurls it. The Processional Ring
 * (arena boundary) is written around her: arrows fired into the arena from
 * outside are swept along the ring instead of reaching her.
 */
export function* intro(b: JoanBoss): SkillGen {
  b.invulnerable = true;
  b.mode = "intro";
  b.setPhase(0);
  try {
    b.e.nameTag = "Joan of Arc";
  } catch {
    // ignore
  }
  const land = { ...b.pos };
  const g = groundY(b.dim, land.x, land.z, land.y + 1);
  if (g !== undefined) land.y = g;
  b.home = { ...land };
  b.e.setDynamicProperty("joan:home", b.home);
  const watchers = allPlayersNear(b.dim, land, 48);
  const back = flatDir(watchers[0]?.location ?? add(land, v(0, 0, 5)), land);
  const sky = add(land, add(scale(back, 7), v(0, 14, 0)));
  if (b.airAbove(land, 15) && b.airAbove(sky, 2)) {
    b.teleport(sky, land);
    b.anim("spawn_descend");
    const road = b.airRoad(skyArc(sky, add(land, v(0, 0.1, 0)), 2), { kind: "arc", speed: 0.6, form: 26, life: 80,
      carryPlayers: false, carryMobs: false, carryProjectiles: false, memory: false, burning: false, damage: 0,
      color: COLORS.white, chevron: COLORS.roadGold });
    emit(b.dim, "joan:pillar", land, { h: 14, color: COLORS.roadGold, life: 1.2, size: 0.6 });
    sound(b.dim, "joan.choir.light", land, 1, 1);
    for (let i = 0; i < 26; i++) {
      b.drive(v(0, 0.08, 0));
      yield 1;
    }
    if (road) yield* b.ride(road, 0, road.length, 0.55, 0, true);
  } else {
    sound(b.dim, "joan.choir.light", land, 1, 1);
  }
  b.anim("spawn_land");
  b.impactFx(land, 3, COLORS.roadGold);
  shake(allPlayersNear(b.dim, land, 24), 0.35, 0.6);
  title(allPlayersNear(b.dim, land, 48), "§6§lBOSS 001 - Joan of Arc", "§fThe Banner of Divine Paths", 70);
  yield 44;
  sound(b.dim, "joan.bell.toll", land, 1, 1);
  // the Processional Ring - arena boundary that deflects outside projectiles
  arenaRing(b);
  yield 24;
  b.setPhase(1);
  b.mode = "fight";
  b.invulnerable = false;
  b.gcdUntil = b.now + 20;
  b.anim("none");
}

/**
 * PHASE TRANSITION - The Maiden falls to one knee. Every road on the field is
 * set alight (warned first), the standard catches fire, the halo becomes a
 * ring of flame, the sky darkens, and the Saint of the Burning Road rises.
 */
export function* transition(b: JoanBoss): SkillGen {
  b.mode = "transition";
  b.invulnerable = true;
  b.flags.pendingTransition = false;
  const players = b.fighters(48);
  b.anim("phase_kneel");
  sound(b.dim, "joan.phase", b.pos, 1.2, 1);
  title(players, "§c§lPhase II", "§6The Saint of the Burning Road", 80);
  for (const p of b.field.activePaths()) {
    if (p.o.kind === "ring") continue;
    // warn: embers run along every existing road, then it burns
    for (let k = 0; k < p.length; k += 3) emit(b.dim, "joan:ember", p.pointAt(k), { size: 0.5, life: 0.8 });
    const road = p;
    b.later(20, () => {
      if (!road.alive) return;
      road.o.burning = true;
      road.o.damage = 2;
      road.o.restless = 70;
      road.nextRestless = b.now + 70;
      road.o.switching = true;
    });
  }
  yield 30;
  b.setPhase(2);
  try {
    b.e.triggerEvent("joan:darken");
    b.e.nameTag = "Joan of Arc, Saint of the Burning Road";
  } catch {
    // ignore
  }
  emit(b.dim, "joan:ember", add(b.pos, v(0, 1, 0)), { size: 2.5, life: 2.5 });
  shake(players, 0.4, 1.0);
  yield 10;
  b.anim("phase_rise");
  sound(b.dim, "joan.fire.roar", b.pos, 1, 0.9);
  emit(b.dim, "joan:pillar", b.pos, { h: 10, color: COLORS.burning, life: 1.2, size: 1.2 });
  yield 48;
  b.mode = "fight";
  b.invulnerable = false;
  b.gcdUntil = b.now + 14;
  b.anim("none");
}

/**
 * DEFEAT - she sinks to her knees, the fire goes out and the standard turns
 * white. Every road becomes light flowing up into the sky, her figure
 * dissolves into petals, and the rewards fall where she knelt.
 */
export function* death(b: JoanBoss): SkillGen {
  b.mode = "dying";
  b.invulnerable = true;
  b.flags.pendingDeath = false;
  b.clearTasks();
  const players = b.fighters(64);
  b.anim("death");
  sound(b.dim, "joan.death", b.pos, 1.2, 1);
  try {
    b.e.triggerEvent("joan:brighten");
  } catch {
    // ignore
  }
  // every road ascends as light
  const roads = b.field.livePaths();
  b.field.retireAll(b.now, 60);
  let pillars = 0;
  for (const p of roads) {
    if (p.o.tag === "arena") continue;
    for (let k = 0; k < p.length && pillars < 48; k += 4, pillars++) emit(b.dim, "joan:pillar", p.pointAt(k), { h: 7, color: COLORS.white, life: 1.2, size: 0.2 });
  }
  yield 28;
  b.setPhase(3); // purified (white) texture
  title(players, "§fJoan of Arc", "§7Freed from the Road", 90);
  yield 40;
  emit(b.dim, "joan:petals", add(b.pos, v(0, 1.4, 0)), { size: 1.5, life: 3.0, color: COLORS.white });
  emit(b.dim, "joan:mote", add(b.pos, v(0, 1.2, 0)), { size: 1.2, life: 3.0, color: COLORS.roadGold, speed: 2 });
  yield 36;
  emit(b.dim, "joan:pillar", b.pos, { h: 24, color: COLORS.white, life: 1.6, size: 0.8 });
  sound(b.dim, "joan.bell.high", b.pos, 1, 1.2);
  yield 14;
  dropRewards(b);
  b.mode = "dead";
  const e = b.e;
  system.run(() => {
    try {
      if (e.isValid) e.remove();
    } catch {
      // ignore
    }
  });
}
