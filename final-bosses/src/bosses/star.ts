import { EntityDamageCause, Player, Vector3, system } from "@minecraft/server";
import {
  beam, blackhole, burst, column, danger, dangerLine, embers, fade, flash, groundWave, mote, moteRing, ringWave, shake, sound,
  sphereWave, title,
} from "../core/fx.js";
import { addTask } from "../core/tasks.js";
import { chest, effect, hurt, knock, playersNear, predict, victimsNear, victimsOnLine } from "../core/targets.js";
import { add, dist, lerp, norm, scale, sub, v } from "../core/vec.js";
import { Boss, BossDef, Move, S } from "../engine.js";
import { act, arc, crowd, exhaust, flatDir, ground, up } from "./common.js";

/**
 * THE DEVOURING STAR - a skeletal leviathan with a sun for a heart.
 * Signature: stellar gravity (everyone near it slides towards it) and DEVOUR: it can swallow a
 * player whole - mash SNEAK to tear your way out. Ultimate: Event Horizon - it collapses, pulling
 * the whole arena towards a ring where anything left inside is eaten, then goes supernova.
 */

interface Meal {
  playerId: string;
  until: number;
  struggles: number;
}
const meals = new Map<string, Meal>(); // boss entity id -> meal

/** Called from main on entityStartSneaking. */
export function struggle(p: Player): void {
  for (const m of meals.values()) if (m.playerId === p.id) m.struggles++;
}

function mouth(b: Boss): Vector3 {
  const r = b.entity.getRotation();
  const yaw = (r.y * Math.PI) / 180;
  return add(b.entity.location, v(-Math.sin(yaw) * 3.6, 2.0, Math.cos(yaw) * 3.6));
}

const breath: Move = {
  id: "flare_breath",
  name: "Solar Flare Breath",
  cooldown: 120,
  score: ({ distance }) => (distance > 3 && distance < 20 ? 15 : 0),
  start: ({ boss, target }) => {
    let aim = target.location;
    const hitAt = new Map<string, number>();
    return act("Solar Flare Breath", S.AtkA, (age) => {
      const from = mouth(boss);
      if (age === 0) {
        aim = predict(target, 10);
        dangerLine(boss.dim, ground(boss, from), ground(boss, add(from, scale(norm(sub(aim, from)), 18))), 2.6, 1.0);
        sound(boss.dim, "mob.ghast.charge", from, 1.5, 0.6);
      }
      if (age < 18) return true;
      const sweepAim = add(aim, v(Math.sin(age * 0.25) * 2, 0, Math.cos(age * 0.25) * 2));
      const to = add(from, scale(norm(sub(sweepAim, from)), 19));
      if (age % 2 === 0) {
        beam(boss.dim, "flame", from, to, 0.6);
        embers(boss.dim, to);
        for (const e of victimsOnLine(boss.dim, from, to, 1.8)) {
          if (age - (hitAt.get(e.id) ?? -10) < 6) continue;
          hitAt.set(e.id, age);
          hurt(e, 3, boss.entity, EntityDamageCause.fire);
          e.setOnFire(3, true);
        }
      }
      if (age === 18) sound(boss.dim, "mob.blaze.shoot", from, 2, 0.5);
      return age < 40;
    });
  },
};

const devour: Move = {
  id: "devour",
  name: "Devour",
  cooldown: 380,
  score: ({ distance, boss, target }) => (distance < 22 && !meals.has(boss.entity.id) ? 13 + (crowd(boss, target.location, 6) <= 1 ? 6 : 0) : 0),
  start: ({ boss, target }) => {
    const start = { ...boss.entity.location };
    let goal = target.location;
    let swallowed: Player | undefined;
    return act("Devour", S.AtkB, (age) => {
      if (age === 0) {
        goal = add(predict(target, 12), v(0, 0.5, 0));
        danger(boss.dim, ground(boss, goal), 5, 0.8);
        sound(boss.dim, "mob.ravager.roar", start, 1.5, 0.5);
      }
      if (age < 14) return true;
      if (!swallowed && age < 30) {
        const p = lerp(start, goal, Math.min(1, (age - 14) / 14));
        boss.glide(p, goal, 2.5);
        const prey = playersNear(boss.dim, mouth(boss), 3.6)[0];
        if (prey) {
          swallowed = prey;
          meals.set(boss.entity.id, { playerId: prey.id, until: system.currentTick + 70, struggles: 0 });
          title(prey, "§6§lDEVOURED", "§7mash SNEAK to tear your way out!", 40);
          fade(prey, [0.5, 0.15, 0.0], 0.1, 0.6, 0.4);
          sound(boss.dim, "mob.ravager.bite", mouth(boss), 2, 0.6);
          boss.say(`${prey.name} tastes of iron and fear.`);
        }
        return true;
      }
      if (!swallowed) return age < 34;
      const meal = meals.get(boss.entity.id);
      if (!meal || !swallowed.isValid) {
        meals.delete(boss.entity.id);
        return false;
      }
      try {
        swallowed.teleport(add(mouth(boss), v(0, -0.6, 0)));
      } catch {
        // ignore
      }
      effect(swallowed, "darkness", 20, 0);
      if (age % 10 === 0) {
        hurt(swallowed, 2, boss.entity, EntityDamageCause.fire);
        embers(boss.dim, chest(swallowed));
      }
      const escaped = meal.struggles >= 5;
      if (escaped || system.currentTick >= meal.until) {
        meals.delete(boss.entity.id);
        const d = flatDir(boss.entity.location, swallowed.location);
        try {
          swallowed.applyKnockback({ x: d.x * 2.6 + 0.01, z: d.z * 2.6 + 0.01 }, 0.7);
        } catch {
          // ignore
        }
        if (escaped) {
          boss.say("It... it bites back!", true);
          burst(boss.dim, "white", chest(swallowed));
          exhaust(boss, 50);
        } else {
          hurt(swallowed, 6, boss.entity);
        }
        burst(boss.dim, "flame", chest(swallowed));
        return false;
      }
      return true;
    }, { hold: true });
  },
};

const meteors: Move = {
  id: "meteor_spit",
  name: "Meteor Spit",
  cooldown: 180,
  score: ({ distance }) => (distance > 8 ? 14 : 5),
  start: ({ boss, target }) =>
    act("Meteor Spit", S.AtkC, (age) => {
      if (age % 6 === 0 && age < 24) {
        const from = mouth(boss);
        const ps = playersNear(boss.dim, boss.entity.location, 30);
        const victim = ps[Math.floor(Math.random() * ps.length)] ?? target;
        const to = ground(boss, add(predict(victim, 22), v(Math.random() * 4 - 2, 0, Math.random() * 4 - 2)));
        danger(boss.dim, to, 5, 1.1);
        sound(boss.dim, "mob.ghast.fireball", from, 1, 0.8);
        addTask("meteor", arc(boss, from, up(to, 0.5), 22, "flame", 5, (at) => {
          sphereWave(boss.dim, "flame", at);
          for (const e of victimsNear(boss.dim, at, 2.6)) {
            hurt(e, 7, boss.entity.isValid ? boss.entity : undefined, EntityDamageCause.fire);
            e.setOnFire(3, true);
          }
          sound(boss.dim, "random.explode", at, 0.8, 1.2);
          addTask("burning-patch", (a) => {
            if (a % 4 === 0) embers(boss.dim, at);
            if (a % 10 === 0) for (const e of victimsNear(boss.dim, at, 1.6)) hurt(e, 1, undefined, EntityDamageCause.fire);
            return a < 60;
          });
        }));
      }
      return age < 30;
    }),
};

const lure: Move = {
  id: "hypnotic_lure",
  name: "Hypnotic Lure",
  cooldown: 300,
  minPhase: 2,
  score: () => 14,
  start: ({ boss }) =>
    act("Hypnotic Lure", S.Channel, (age) => {
      const m = mouth(boss);
      const bulb = add(boss.entity.location, v(0, 3.4, 0));
      if (age === 0) {
        for (const p of playersNear(boss.dim, m, 24)) title(p, "§6§lTHE LURE", "§7hold SNEAK to resist the pull", 40);
        sound(boss.dim, "beacon.activate", bulb, 1.5, 1.8);
      }
      if (age % 3 === 0) {
        flash(boss.dim, bulb);
        for (const p of playersNear(boss.dim, m, 24)) {
          if (p.isSneaking) {
            mote(boss.dim, "white", up(p.location, 0.3));
            continue;
          }
          knock(p, m, -0.55, 0.05);
          if (age % 9 === 0) beam(boss.dim, "star", m, chest(p), 1.4);
        }
      }
      if (age === 44) {
        sound(boss.dim, "mob.ravager.bite", m, 2, 0.5);
        for (const e of victimsNear(boss.dim, m, 5)) hurt(e, 10, boss.entity);
        sphereWave(boss.dim, "flame", m);
      }
      return age < 48;
    }, { hold: true }),
};

const comet: Move = {
  id: "comet_tail",
  name: "Comet Tail",
  cooldown: 140,
  score: ({ boss }) => (playersNear(boss.dim, boss.entity.location, 8).length ? 22 : 0),
  start: ({ boss }) =>
    act("Comet Tail", S.AtkD, (age) => {
      const at = boss.entity.location;
      if (age === 10) {
        ringWave(boss.dim, "flame", up(ground(boss, at), 0.3), 9, 0.4);
        groundWave(boss.dim, "flame", up(ground(boss, at), 0.3));
        sound(boss.dim, "mob.enderdragon.flap", at, 2, 0.7);
        for (const e of victimsNear(boss.dim, at, 9)) {
          hurt(e, 9, boss.entity);
          knock(e, at, 2.2, 0.5);
        }
      }
      return age < 18;
    }, { hold: true }),
};

/** ULTIMATE: Event Horizon. */
const horizon: Move = {
  id: "event_horizon",
  name: "Event Horizon",
  cooldown: 900,
  score: () => 0,
  start: ({ boss }) => {
    const center = ground(boss, boss.entity.location);
    const R = 7;
    return act("Event Horizon", S.Ultimate, (age) => {
      const dim = boss.dim;
      const core = up(center, 10);
      boss.glide(core, undefined, 0.35);
      if (age === 0) {
        for (const p of playersNear(dim, center, 50)) {
          title(p, "§6§lEVENT HORIZON", "§7RUN - whatever is inside the ring is devoured", 80);
          fade(p, [0.5, 0.18, 0.0], 0.3, 0.4, 0.8);
          shake(p, 0.25, 8);
        }
        sound(dim, "mob.warden.emerge", center, 2, 0.5);
      }
      if (age % 20 === 0) {
        danger(dim, center, R * 2, 1.1);
        blackhole(dim, core, 4 + age * 0.02, 1.1);
      }
      if (age >= 20 && age < 160) {
        if (age % 2 === 0) {
          for (const e of victimsNear(dim, center, 42)) knock(e, center, -0.3, 0.0);
          moteRing(dim, "flame", up(center, 0.3), 40 - (age - 20) * 0.22, 40, age * 0.05);
        }
        if (age % 20 === 10) {
          for (const p of playersNear(dim, center, 40).slice(0, 3)) {
            const aimAt = chest(p);
            beam(dim, "red", core, aimAt, 1.6);
            addTask("flare", (a) => {
              if (a === 8) {
                beam(dim, "flame", core, aimAt, 0.5);
                for (const e of victimsOnLine(dim, core, aimAt, 1.3)) hurt(e, 4, boss.entity.isValid ? boss.entity : undefined, EntityDamageCause.fire);
              }
              return a < 8;
            });
          }
        }
        return true;
      }
      if (age === 160) {
        flash(dim, core);
        sphereWave(dim, "flame", core);
        sphereWave(dim, "star", core);
        sphereWave(dim, "white", core);
        ringWave(dim, "flame", up(center, 0.3), 30, 0.8);
        sound(dim, "random.explode", center, 3, 0.3);
        sound(dim, "mob.wither.death", center, 1.5, 1.4);
        for (const e of victimsNear(dim, center, 32)) {
          const inside = Math.hypot(e.location.x - center.x, e.location.z - center.z) <= R;
          hurt(e, inside ? 24 : 6, boss.entity, inside ? EntityDamageCause.magic : EntityDamageCause.fire);
          knock(e, center, 2.8, 0.9);
          if (e instanceof Player) {
            fade(e, [1, 0.95, 0.8], 0.05, 0.3, 1.2);
            if (inside) title(e, "§6§lDEVOURED", "§7by a dying star", 30);
          }
        }
        exhaust(boss, 90);
      }
      return age < 166;
    }, { hold: true });
  },
};

export const STAR: BossDef = {
  typeId: "fb:devouring_star",
  key: "devouring_star",
  name: "The Devouring Star",
  epithet: "Leviathan of the Last Light",
  color: "§6",
  hue: "flame",
  fade: [0.55, 0.22, 0.02],
  speed: 0.42,
  mode: "hover",
  eyeHeight: 2.2,
  spawnTicks: 70,
  loot: "fb:star_heart",
  hover(b, target, t) {
    const c = target ? target.location : b.home;
    const ang = (b.memo.orbit = (b.memo.orbit ?? 0) + (b.phase === 3 ? 0.02 : 0.013));
    const g = b.groundBelow(c);
    return { x: c.x + Math.cos(ang) * 12, y: g.y + 3.5 + Math.sin(t * 0.05) * 0.8, z: c.z + Math.sin(ang) * 12 };
  },
  mechanic(b, t) {
    if (t % 5 === 0) {
      for (const p of playersNear(b.dim, b.entity.location, 12)) {
        if (dist(p.location, b.entity.location) > 3) knock(p, b.entity.location, -0.1, 0);
      }
    }
  },
  hudInfo(b) {
    const meal = meals.get(b.entity.id);
    return meal ? `§c${meal.struggles}/5 struggles` : "§6gravity well";
  },
  moves: [breath, devour, meteors, lure, comet],
  ultimate: horizon,
  ambient(b, t) {
    if (t % 3 === 0) embers(b.dim, add(b.entity.location, v(Math.random() * 2 - 1, 1.6 + Math.random(), Math.random() * 2 - 1)));
    if (t % 25 === 0) column(b.dim, "star", up(b.entity.location, -2));
  },
  deathFx(b, age) {
    if (age % 5 === 0) sphereWave(b.dim, age % 10 ? "flame" : "star", up(b.entity.location, 2));
  },
  lines: {
    intro: ["I have eaten eleven suns. Your little world is a snack.", "Light is just food that has not been caught yet."],
    phase2: ["Wounded stars burn hotter."],
    phase3: ["I will collapse - and take your sky with me."],
    ultimate: ["Cross the horizon. Nothing comes back."],
    kill: ["{name} was a brief, bright morsel.", "Digested."],
    taunt: ["{name}, I can smell your heartbeat.", "That {weapon} will not even reach my teeth, {name}."],
    death: ["My light... goes... out..."],
  },
};

export const STAR_TEST = { meals };
