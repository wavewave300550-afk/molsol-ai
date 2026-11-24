import { Entity, Player } from "@minecraft/server";
import { COLORS, STAKE, TUNING, WAYSTONE } from "../../config.js";
import { emit, shake, sound, title } from "../../core/fx.js";
import { burn, fightersNear, foesNear, hurt, isPlayer, push } from "../../core/targets.js";
import { groundY } from "../../core/terrain.js";
import { add, flatDir, hdist, scale, v, V3 } from "../../core/vec.js";
import { Path } from "../../paths/path.js";
import { spiral } from "../../paths/shapes.js";
import type { JoanBoss, SkillGen } from "../joan.js";
import { setProp, spawnMinion } from "../minions.js";

interface Arm {
  path: Path;
  stone?: Entity;
  turned: boolean;
}

/** Active ultimates by waystone id, so hits can be routed here. */
export const waystoneArms = new Map<string, { arm: Arm; boss: JoanBoss; state: UltState }>();

interface UltState {
  arms: Arm[];
  allTurned: boolean;
}

/**
 * ULTIMATE - ROAD TO THE STAKE (Phase II).
 * The pyre of Rouen rises in the middle of the arena and five spiral roads
 * coil inward to it, dragging everything towards the stake. A Lily Waystone
 * floats at the mouth of every road: strike it and that road REVERSES - it
 * turns white (purified), stops burning and carries people OUT. Flame runs
 * race along the roads that are still burning. When the countdown ends the
 * pyre erupts; anyone standing on a purified road is spared.
 * If every road is reversed in time, all roads lead away from the stake ... and
 * back into Joan: she is dragged down and bound to her own pyre (Martyr's Echo,
 * a long stun in which she takes +50% damage).
 */
export function* roadToTheStake(b: JoanBoss, _t: Player): SkillGen {
  b.flags.ultCount++;
  b.flags.lastUlt = b.now;
  b.flags.pendingUlt = false;
  const g = groundY(b.dim, b.home.x, b.home.z, b.home.y + 2) ?? b.home.y;
  const c = v(b.home.x, g, b.home.z);
  const players = b.fighters(48);
  title(players, "§c§lRoad to the Stake", "§6Strike the Lily Waystones to turn the roads", 70);
  sound(b.dim, "joan.choir.dark", c, 1, 0.9);
  b.invulnerable = true;
  b.anim("ult_rise");
  const state: UltState = { arms: [], allTurned: false };
  let stake: Entity | undefined;
  try {
    // rise above the pyre
    const above = add(c, v(0, 5.5, 0));
    for (let i = 0; i < 40; i++) {
      const vel = scale(add(above, scale(b.pos, -1)), 0.12);
      b.drive(add(vel, v(0, 0.08, 0)));
      if (i === 10) {
        stake = b.track(spawnMinion(b.dim, STAKE, c, b.id));
        sound(b.dim, "joan.stake.rise", c, 1, 1);
        shake(players, 0.25, 1.5);
      }
      yield 1;
    }
    b.invulnerable = false;
    b.anim("ult_channel");
    // five burning spiral roads coiling into the stake
    const n = 5;
    const form = b.tel(2.2);
    const countdown = Math.round(240 * (b.tel() / 12));
    for (let k = 0; k < n; k++) {
      const a0 = (k / n) * Math.PI * 2;
      const pts = spiral(c, 17, 1.6, a0, 1.15, true);
      const path = b.groundRoad(pts, {
        kind: "stake", speed: 0.34, radius: 1.05, form, life: form + countdown + 40, burning: true, damage: 1.5,
        crossings: false, switching: false, restless: 0, memory: false, tag: "stake",
      });
      if (!path) continue;
      const mouth = path.pointAt(0);
      const stone = b.track(spawnMinion(b.dim, WAYSTONE, add(mouth, v(0, 1.4, 0)), b.id));
      setProp(stone, "joan:fire", true);
      const arm: Arm = { path, stone, turned: false };
      state.arms.push(arm);
      if (stone) waystoneArms.set(stone.id, { arm, boss: b, state });
    }
    yield form;
    // countdown with flame runs on the burning arms
    let nextRun = 30;
    for (let i = 0; i < countdown; i++) {
      const left = countdown - i;
      setProp(stake, "joan:stake", Math.min(1, i / countdown));
      if (b.now % 4 === 0) b.drive(scale(add(above, scale(b.pos, -1)), 0.2));
      else b.drive(v(0, 0.08, 0));
      if (state.arms.length && state.arms.every((a) => a.turned)) {
        state.allTurned = true;
        break;
      }
      if (i === nextRun) {
        const burning = state.arms.filter((a) => !a.turned);
        if (burning.length) flameRun(b, burning[Math.floor(Math.random() * burning.length)].path);
        nextRun += 52;
      }
      if (left % 40 === 0 && left <= 120) {
        sound(b.dim, "joan.bell.toll", c, 1, 0.8 + (120 - left) / 400);
        for (const p of b.fighters(48)) {
          try {
            p.onScreenDisplay.setActionBar(`§6The pyre ignites in §c${Math.ceil(left / 20)}§6...`);
          } catch {
            // ignore
          }
        }
      }
      yield 1;
    }
    if (state.allTurned) {
      // MARTYR'S ECHO - every road now leads into Joan herself
      b.flags.martyrEcho = true;
      setProp(stake, "joan:state", 2);
      title(b.fighters(48), "§f§lMartyr's Echo", "§7All roads lead away from the stake... and into her", 70);
      sound(b.dim, "joan.death", c, 0.8, 1.3);
      b.anim("ult_bound");
      const bindAt = add(c, v(0, 0.2, 1.6));
      for (let i = 0; i < 20; i++) {
        b.drive(scale(add(bindAt, scale(b.pos, -1)), 0.3));
        yield 1;
      }
      b.teleport(bindAt, c);
      b.stunUntil = b.now + 130;
      b.vulnerableUntil = b.now + 130;
      for (const arm of state.arms) b.field.retire(arm.path, b.now, 20);
      for (let i = 0; i < 130; i += 10) {
        emit(b.dim, "joan:mote", add(b.pos, v(0, 1.2, 0)), { color: COLORS.white, life: 0.6, size: 1, speed: 1 });
        yield 10;
      }
    } else {
      // THE PYRE
      setProp(stake, "joan:state", 1);
      setProp(stake, "joan:stake", 1);
      sound(b.dim, "joan.verdict", c, 1.2, 1);
      shake(b.fighters(48), 0.6, 1.2);
      emit(b.dim, "joan:pillar", c, { h: 16, color: COLORS.burning, life: 1.0, size: 3 });
      emit(b.dim, "joan:ember", add(c, v(0, 2, 0)), { size: 4, life: 2.0 });
      emit(b.dim, "joan:smoke", add(c, v(0, 3, 0)), { size: 3, life: 2.5 });
      const purified = state.arms.filter((a) => a.turned).map((a) => a.path);
      for (const e of foesNear(b.dim, c, 11.5)) {
        const onWhite = purified.some((p) => {
          const nn = p.nearest(e.location);
          return nn.dh < 1.6 && Math.abs(nn.dy) < 2.5;
        });
        if (onWhite) continue;
        const d = hdist(e.location, c);
        if (d <= 7) {
          hurt(e, 20, b.e);
          burn(e, 5);
          push(e, add(scale(flatDir(c, e.location), 1.0), v(0, 0.6, 0)));
        } else {
          hurt(e, 6, b.e);
          burn(e, 2);
        }
      }
      for (const arm of state.arms) b.field.retire(arm.path, b.now, 6);
      yield 30;
    }
  } finally {
    for (const arm of state.arms) {
      if (arm.stone) waystoneArms.delete(arm.stone.id);
      b.untrack(arm.stone);
      b.field.retire(arm.path, b.now, 6);
    }
    if (stake && stake.isValid) {
      setProp(stake, "joan:sinking", true);
      const st = stake;
      b.later(32, () => b.untrack(st));
    }
    b.invulnerable = false;
  }
  b.anim("surge_slam");
  yield 18;
  b.cooldown("stake", TUNING.ultimateRepeat);
}

/** A player struck a Lily Waystone: its road turns, goes white and carries people out. */
export function strikeWaystone(stone: Entity, by?: Entity): void {
  const rec = waystoneArms.get(stone.id);
  if (!rec || rec.arm.turned) return;
  if (by && !isPlayer(by) && by.typeId !== "minecraft:arrow" && by.typeId !== "minecraft:thrown_trident") return;
  const { arm, boss } = rec;
  arm.turned = true;
  boss.field.reverse(arm.path, 4, boss.now);
  arm.path.o.burning = false;
  arm.path.o.damage = 0;
  arm.path.o.color = COLORS.purified;
  arm.path.o.chevron = COLORS.white;
  setProp(stone, "joan:fire", false);
  sound(stone.dimension, "joan.waystone.turn", stone.location, 1.2, 1);
  emit(stone.dimension, "joan:pillar", stone.location, { h: 6, color: COLORS.purified, life: 0.5, size: 0.5 });
  const left = rec.state.arms.filter((a) => !a.turned).length;
  for (const p of fightersNear(stone.dimension, stone.location, 48)) {
    try {
      p.onScreenDisplay.setActionBar(left ? `§bA road turns white. §f${left} §bstill burn.` : "§f§lEvery road is purified!");
    } catch {
      // ignore
    }
  }
}

/** A wave of fire running out along a burning arm (telegraphed by a 20-tick flare). */
function flameRun(b: JoanBoss, path: Path): void {
  const start = b.now + 20;
  emit(b.dim, "joan:pillar", path.pointAt(path.length - 1), { h: 5, color: COLORS.warn, life: 1.0, size: 0.5 });
  sound(b.dim, "joan.fire.ignite", path.pointAt(path.length - 1), 1, 0.8);
  let s = path.length;
  const hit = new Set<string>();
  b.addTask({
    name: "flame-run",
    step: (now) => {
      if (now < start) {
        if ((start - now) % 4 === 0) {
          for (let k = 0; k < path.length; k += 3) {
            const p = path.pointAt(k);
            emit(b.dim, "joan:ember", p, { size: 0.4, life: 0.3 });
          }
        }
        return true;
      }
      if (!path.alive) return false;
      s -= 0.95;
      const p = path.pointAt(Math.max(0, s));
      emit(b.dim, "joan:road_fire", p, { life: 0.5, size: 2.2 }, path.dirAt(s), 1.2);
      emit(b.dim, "joan:flash", add(p, v(0, 0.6, 0)), { size: 1.4, life: 0.2, color: COLORS.burning });
      for (const e of foesNear(b.dim, p, 1.6)) {
        if (hit.has(e.id)) continue;
        hit.add(e.id);
        hurt(e, 6, b.e);
        burn(e, 3);
      }
      return s > 0;
    },
  });
}

export function arenaPoint(b: JoanBoss): V3 {
  return b.home;
}
