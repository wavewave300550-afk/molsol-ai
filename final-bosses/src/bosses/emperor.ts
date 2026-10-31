import { EntityDamageCause, Player, Vector3 } from "@minecraft/server";
import {
  blackhole, burst, column, danger, dangerLine, debris, fade, flash, groundWave, mote, moteRing, safe, shake, smoke, sound,
  sphereWave, title,
} from "../core/fx.js";
import { addTask } from "../core/tasks.js";
import { chest, effect, hurt, knock, playersNear, predict, victimsNear } from "../core/targets.js";
import { add, dist, lerp, v } from "../core/vec.js";
import { BossDef, Move, S } from "../engine.js";
import { act, blast, crowd, exhaust, flatDir, ground, looksAt, up } from "./common.js";

/**
 * THE VOID EMPEROR - a living throne whose emperor is absent.
 * Fights like a monarch: it barely moves, its detached gauntlets do the work, it issues decrees
 * (do not meet its gaze), opens rifts of nothing and, at the end, crowns nothingness itself:
 * the whole arena becomes void except for a few candles of existence that go out one by one.
 */

const slam: Move = {
  id: "hand_slam",
  name: "Hand of Dominion",
  cooldown: 70,
  score: ({ distance }) => (distance > 2 && distance < 26 ? 14 : 0),
  start: ({ boss, target }) => {
    const at = ground(boss, predict(target, 18));
    return act("Hand of Dominion", S.AtkA, (age) => {
      if (age === 0) {
        danger(boss.dim, at, 6.6, 1.25);
        sound(boss.dim, "mob.evocation_illager.prepare_attack", at, 1, 0.6);
      }
      if (age < 24) {
        if (age % 4 === 0) moteRing(boss.dim, "void", up(at, 0.2), 3.3 - age * 0.05, 16, age);
        return true;
      }
      if (age === 24) {
        blast(boss, up(at, 1), 3.3, 11);
        for (const e of victimsNear(boss.dim, at, 4.5)) knock(e, at, 1.2, 0.5);
        groundWave(boss.dim, "void", up(at, 0.2));
        debris(boss.dim, at);
        smoke(boss.dim, "void", up(at, 0.5));
        sound(boss.dim, "random.anvil_land", at, 1.5, 0.5);
        for (const p of playersNear(boss.dim, at, 10)) shake(p, 0.2, 0.4);
      }
      return age < 34;
    });
  },
};

const grasp: Move = {
  id: "imperial_grasp",
  name: "Imperial Grasp",
  cooldown: 320,
  score: ({ distance, boss }) => (distance > 6 && distance < 28 && boss.losLost === 0 ? 11 + Math.min(10, distance * 0.3) : 0),
  start: ({ boss, target }) => {
    let held: Player | undefined;
    let freedAt = 0;
    const hpAtGrab = { v: 0 };
    return act("Imperial Grasp", S.AtkB, (age) => {
      const hand = add(boss.entity.location, v(0, 4.5, 0));
      if (age < 14) {
        if (target.isValid && age % 2 === 0) {
          mote(boss.dim, "void", lerp(hand, chest(target), age / 14));
          moteRing(boss.dim, "void", up(target.location, 1), 1.2, 10, age);
        }
        return true;
      }
      if (age === 14) {
        if (!target.isValid || dist(target.location, boss.entity.location) > 30) return false;
        held = target;
        hpAtGrab.v = boss.hpFrac;
        boss.say(`Rise, ${target.name}. Your emperor wishes to look at you.`);
        sound(boss.dim, "mob.wither.shoot", hand, 1, 0.5);
      }
      if (held && age > 14 && age < 50) {
        try {
          held.teleport(add(hand, v(0, 0.5, 0)));
        } catch {
          // ignore
        }
        effect(held, "slow_falling", 10, 0);
        if (age % 10 === 0) hurt(held, 2, boss.entity, EntityDamageCause.magic);
        smoke(boss.dim, "void", chest(held));
        // fighting back frees you: deal 8% of its health while held
        if (hpAtGrab.v - boss.hpFrac > 0.08 && !freedAt) {
          freedAt = age;
          boss.say("Insolent!", true);
          burst(boss.dim, "gold", chest(held));
          held = undefined;
          exhaust(boss, 40);
          return false;
        }
        return true;
      }
      if (age === 50 && held) {
        const d = flatDir(boss.entity.location, held.location);
        try {
          held.applyKnockback({ x: d.x * 3.0 + 0.01, z: d.z * 3.0 + 0.01 }, 0.9);
        } catch {
          // ignore
        }
        hurt(held, 6, boss.entity);
        burst(boss.dim, "void", chest(held));
      }
      return age < 56;
    }, { hold: true });
  },
};

const rifts: Move = {
  id: "void_rifts",
  name: "Void Rifts",
  cooldown: 260,
  score: ({ boss, target }) => 10 + crowd(boss, target.location, 6) * 4,
  start: ({ boss }) => {
    const spots: Vector3[] = playersNear(boss.dim, boss.entity.location, 30).slice(0, 3).map((p) => ground(boss, predict(p, 20)));
    while (spots.length < 3) spots.push(ground(boss, add(boss.entity.location, v(Math.random() * 16 - 8, 0, Math.random() * 16 - 8))));
    return act("Void Rifts", S.Channel, (age) => {
      if (age === 0) {
        for (const s of spots) danger(boss.dim, s, 5, 1.0);
        sound(boss.dim, "mob.endermen.portal", boss.entity.location, 2, 0.4);
      }
      if (age === 20) {
        for (const s of spots) {
          blackhole(boss.dim, up(s, 1.2), 3.5, 6);
          addTask("void-rift", (a) => {
            if (a % 3 === 0) smoke(boss.dim, "void", up(s, 0.8 + Math.random()));
            if (a % 2 === 0) {
              for (const e of victimsNear(boss.dim, s, 6)) {
                knock(e, s, -0.34, 0.02);
                if (a % 10 === 0 && dist(e.location, s) < 2.2) hurt(e, 3, boss.entity.isValid ? boss.entity : undefined, EntityDamageCause.magic);
              }
            }
            return a < 120;
          });
        }
      }
      return age < 24;
    });
  },
};

const decree: Move = {
  id: "decree_kneel",
  name: "Decree: Kneel",
  cooldown: 420,
  minPhase: 2,
  score: () => 18,
  start: ({ boss }) =>
    act("Decree: Kneel", S.Channel, (age) => {
      const eye = boss.eye;
      if (age === 0) {
        for (const p of playersNear(boss.dim, boss.entity.location, 26)) title(p, "§5§lKNEEL", "§7do NOT meet the Emperor's gaze", 40);
        sound(boss.dim, "mob.elderguardian.curse", eye, 1.5, 0.5);
      }
      if (age < 40) {
        if (age % 4 === 0) moteRing(boss.dim, "void", eye, 2 + age * 0.08, 18, age * 0.2);
        return true;
      }
      if (age === 40) {
        flash(boss.dim, eye);
        for (const p of playersNear(boss.dim, boss.entity.location, 26)) {
          try {
            p.applyKnockback({ x: 0.001, z: 0.001 }, -1.2);
          } catch {
            // ignore
          }
          if (looksAt(p, eye, 0.45)) {
            hurt(p, 9, boss.entity, EntityDamageCause.magic);
            effect(p, "blindness", 60, 0);
            effect(p, "slowness", 60, 2);
            burst(boss.dim, "void", chest(p));
          } else {
            mote(boss.dim, "gold", up(p.location, 2.2));
          }
        }
      }
      return age < 46;
    }, { hold: true }),
};

const charge: Move = {
  id: "throne_charge",
  name: "Throne Charge",
  cooldown: 220,
  score: ({ distance }) => (distance > 9 && distance < 30 ? 14 : 0),
  start: ({ boss, target }) => {
    const start = { ...boss.entity.location };
    const d = flatDir(start, target.location);
    const end = ground(boss, add(target.location, v(d.x * 8, 0, d.z * 8)));
    const hit = new Set<string>();
    return act("Throne Charge", S.AtkD, (age) => {
      if (age === 0) {
        dangerLine(boss.dim, ground(boss, start), end, 3, 1.1);
        sound(boss.dim, "mob.ravager.roar", start, 1.5, 0.6);
      }
      if (age < 22) return true;
      const k = Math.min(1, (age - 22) / 12);
      const p = lerp(start, { ...end, y: end.y + 0.5 }, k);
      boss.glide(p, add(p, v(d.x, 0, d.z)), 3);
      debris(boss.dim, p);
      for (const e of victimsNear(boss.dim, up(p, 1), 3.4)) {
        if (hit.has(e.id)) continue;
        hit.add(e.id);
        hurt(e, 12, boss.entity);
        knock(e, p, 2.4, 0.6);
      }
      return k < 1;
    }, { hold: true });
  },
};

const coronation: Move = {
  id: "coronation",
  name: "Coronation of Nothing",
  cooldown: 900,
  score: () => 0,
  start: ({ boss }) => {
    const center = ground(boss, boss.home);
    const candles: Vector3[] = [];
    for (let k = 0; k < 4; k++) {
      const a = Math.random() * Math.PI * 2;
      const r = 6 + Math.random() * 10;
      candles.push(ground(boss, add(center, v(Math.cos(a) * r, 0, Math.sin(a) * r))));
    }
    let lit = 4;
    const R = 2.8;
    return act("Coronation of Nothing", S.Ultimate, (age) => {
      const dim = boss.dim;
      boss.glide(up(center, 6), undefined, 0.25);
      if (age === 0) {
        for (const p of playersNear(dim, center, 48)) {
          title(p, "§5§lCORONATION OF NOTHING", "§7stand inside the candles of existence", 80);
          fade(p, [0.12, 0.0, 0.2], 0.4, 0.6, 1.0);
          effect(p, "darkness", 80, 0);
          shake(p, 0.15, 3);
        }
        sound(dim, "mob.wither.spawn", center, 2, 0.5);
      }
      for (let i = 0; i < 5; i++) {
        const a = Math.random() * Math.PI * 2;
        const r = Math.random() * 24;
        smoke(dim, "void", up(add(center, v(Math.cos(a) * r, 0, Math.sin(a) * r)), 0.3 + Math.random() * 2));
      }
      if (age % 20 === 0) {
        for (let k = 0; k < lit; k++) {
          safe(dim, candles[k], R * 2, 1.1);
          column(dim, "gold", candles[k]);
        }
      }
      if (age === 100 || age === 140 || age === 180) {
        lit--;
        burst(dim, "void", up(candles[lit], 1));
        sound(dim, "random.fizz", candles[lit], 2, 0.5);
        for (const p of playersNear(dim, center, 40)) p.onScreenDisplay.setActionBar(`§5A candle goes out. §7${lit} remain.`);
      }
      if (age >= 40 && age < 220 && age % 10 === 0) {
        for (const p of playersNear(dim, center, 30)) {
          const safeNow = candles.slice(0, lit).some((c) => Math.hypot(p.location.x - c.x, p.location.z - c.z) <= R);
          if (!safeNow) {
            hurt(p, 3, boss.entity, EntityDamageCause.magic);
            smoke(dim, "void", chest(p));
          }
        }
      }
      if (age === 220) {
        flash(dim, up(center, 3));
        sphereWave(dim, "void", up(center, 3));
        sphereWave(dim, "white", up(center, 3));
        sound(dim, "random.explode", center, 2, 0.4);
        for (const p of playersNear(dim, center, 32)) {
          const safeNow = Math.hypot(p.location.x - candles[0].x, p.location.z - candles[0].z) <= R;
          fade(p, safeNow ? [1, 1, 1] : [0, 0, 0], 0.05, 0.4, 1.0);
          if (!safeNow) {
            hurt(p, 18, boss.entity, EntityDamageCause.magic);
            title(p, "§5§lERASED", "§7you stood in nothing", 30);
          }
        }
        exhaust(boss, 90);
      }
      return age < 226;
    }, { hold: true });
  },
};

export const EMPEROR: BossDef = {
  typeId: "fb:void_emperor",
  key: "void_emperor",
  name: "The Void Emperor",
  epithet: "Throne of the Absent King",
  color: "§5",
  hue: "void",
  fade: [0.2, 0.02, 0.35],
  speed: 0.16,
  mode: "hover",
  eyeHeight: 3.2,
  spawnTicks: 70,
  loot: "fb:crown_of_absence",
  hover(b, target, t) {
    const c = target ? target.location : b.home;
    const away = target ? flatDir(target.location, b.home) : v(0, 0, 1);
    const p = add(c, v(away.x * 10, 0, away.z * 10));
    const g = b.groundBelow(p);
    return { x: p.x, y: g.y + 0.6 + Math.sin(t * 0.05) * 0.3, z: p.z };
  },
  mechanic(b, t) {
    if (t % 20 !== 0) return;
    for (const p of playersNear(b.dim, b.entity.location, 6)) {
      effect(p, "slowness", 30, 0);
      mote(b.dim, "void", up(p.location, 0.3));
    }
  },
  moves: [slam, grasp, rifts, decree, charge],
  ultimate: coronation,
  ambient(b, t) {
    if (t % 5 === 0) smoke(b.dim, "void", add(b.entity.location, v(Math.random() * 3 - 1.5, 0.4 + Math.random() * 4, Math.random() * 3 - 1.5)));
    if (t % 30 === 0) mote(b.dim, "void", add(b.entity.location, v(0, 3.2, -0.3)));
  },
  deathFx(b, age) {
    if (age % 10 === 0) groundWave(b.dim, "void", up(b.groundBelow(b.entity.location), 0.2));
    if (age % 4 === 0) smoke(b.dim, "void", add(b.entity.location, v(Math.random() * 4 - 2, Math.random() * 5, Math.random() * 4 - 2)));
  },
  lines: {
    intro: ["Kneel. The throne is occupied by what you cannot see.", "There is no emperor. There is only the throne. And the throne remembers."],
    phase2: ["You scratch the gilding. The void beneath does not bleed."],
    phase3: ["Then witness the coronation of nothing."],
    ultimate: ["Let nothing be crowned!", "The candles of existence are few. Choose quickly."],
    kill: ["{name} has been excused from existence.", "Another subject returns to the void."],
    taunt: ["{name}. You approach the throne with {weapon}? Kneel first.", "I see you, {name}. The mask always sees."],
    death: ["The throne... is... empty... at last..."],
  },
};
