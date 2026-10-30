import { EntityDamageCause, EquipmentSlot, Player, system, Vector3 } from "@minecraft/server";
import {
  beam, burst, column, danger, fade, flash, glyphs, mote, moteRing, ringWave, shake, sigil, sound, sphereWave, title,
} from "../core/fx.js";
import { later } from "../core/tasks.js";
import { chest, effect, healthOf, hurt, knock, lineOfSight, playersNear, predict, victimsNear, victimsOnLine } from "../core/targets.js";
import { add, dist, norm, scale, sub, v } from "../core/vec.js";
import { AnimState, Being, BeingDef, Move } from "../engine.js";
import { dismiss, spawnIllusion } from "../minions.js";
import { act, blast, crowd, groundAt } from "./common.js";

/**
 * The Ophanim of the Eleventh Axis.
 * A hypercube folded around a single eye, wrapped in wheels covered with eyes. It perceives time as
 * a spatial direction: it records where you were, predicts where you will be, and can turn the axis
 * backwards. Ultimate: Rewind - everyone is dragged back eight seconds, then judged in every possible future.
 */

function gazeFrom(being: Being, eye: Vector3, aimAt: Vector3, damage: number): void {
  const far = add(eye, scale(norm(sub(aimAt, eye)), 34));
  beam(being.dim, "red", eye, far, 0.45);
  beam(being.dim, "gold", eye, far, 0.9);
  for (const e of victimsOnLine(being.dim, eye, far, 1.15)) {
    hurt(e, damage, being.entity);
    e.setOnFire(3, true);
    burst(being.dim, "gold", chest(e));
  }
}

function shielding(p: Player): boolean {
  if (!p.isSneaking) return false;
  try {
    const off = p.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Offhand);
    const main = p.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Mainhand);
    return off?.typeId === "minecraft:shield" || main?.typeId === "minecraft:shield";
  } catch {
    return false;
  }
}

const gaze: Move = {
  id: "gaze",
  name: "Gaze of Judgement",
  cooldown: 70,
  score: ({ distance, being, target }) => (being.losLost === 0 && distance < 34 && !shielding(target) ? 15 : 0),
  start: ({ being, target }) => {
    let locked: Vector3 | undefined;
    return act("Gaze of Judgement", AnimState.Cast, (age) => {
      const eye = add(being.entity.location, v(0, 2, 0));
      if (age < 20) {
        if (age % 2 === 0 && target.isValid) beam(being.dim, "red", eye, chest(target), 1.0);
        if (age === 0) sound(being.dim, "mob.guardian.attack_loop", eye, 1.5, 1.6);
        return true;
      }
      if (age === 20) locked = target.isValid ? add(predict(target, 4), v(0, 1, 0)) : undefined;
      if (age === 26 && locked) {
        gazeFrom(being, eye, locked, 9);
        sound(being.dim, "mob.warden.sonic_boom", eye, 1, 1.9);
      }
      return age < 30;
    }, true);
  },
};

const echoes: Move = {
  id: "timeline_echoes",
  name: "Timeline Echoes",
  cooldown: 300,
  score: ({ distance }) => (distance < 30 ? 14 : 0),
  start: ({ being, target, tick }) => {
    const ids: ReturnType<typeof spawnIllusion>[] = [];
    const locks: (Vector3 | undefined)[] = [];
    return act("Timeline Echoes", AnimState.Channel, (age) => {
      if (age === 0) {
        being.say("These are the moments I already lived. They all remember where you will stand.");
        sound(being.dim, "mob.evocation_illager.prepare_summon", being.entity.location, 1.5, 1.6);
        for (let k = 0; k < 3; k++) {
          const a = (k / 3) * Math.PI * 2 + Math.random();
          const at = add(target.location, v(Math.cos(a) * 9, 4, Math.sin(a) * 9));
          ids.push(spawnIllusion(being, "dim11:echo", at, target.location, 110, tick));
        }
      }
      ids.forEach((e, k) => {
        if (!e?.isValid) return;
        const start = 12 + k * 14;
        const eye = add(e.location, v(0, 2, 0));
        if (age >= start && age < start + 14 && age % 2 === 0 && target.isValid) beam(being.dim, "red", eye, chest(target), 1.2);
        if (age === start + 14) locks[k] = target.isValid ? add(predict(target, 4), v(0, 1, 0)) : undefined;
        if (age === start + 19 && locks[k]) {
          gazeFrom(being, eye, locks[k] as Vector3, 7);
          sound(being.dim, "mob.shulker.shoot", eye, 1, 0.6);
        }
      });
      if (age === 80) ids.forEach(dismiss);
      return age < 82;
    });
  },
};

const lock: Move = {
  id: "causality_lock",
  name: "Causality Lock",
  cooldown: 320,
  score: ({ distance, being }) => (distance < 26 ? 11 + (being.phase - 1) * 4 : 0),
  start: ({ being, target }) => {
    let rooted: Player[] = [];
    let at: Vector3 = target.location;
    return act("Causality Lock", AnimState.Channel, (age) => {
      const eye = add(being.entity.location, v(0, 2, 0));
      if (age === 0) {
        at = target.location;
        sigil(being.dim, add(groundAt(being, at), v(0, 0.1, 0)), 5, 1.2);
        sound(being.dim, "apply_effect.bad_omen", at, 1, 1.4);
      }
      if (age < 22) {
        if (target.isValid) {
          at = target.location;
          mote(being.dim, "gold", add(at, v(0, 2.6 + Math.sin(age * 0.5) * 0.2, 0)));
        }
        return true;
      }
      if (age === 22) {
        if (!target.isValid || !lineOfSight(being.dim, eye, chest(target))) {
          being.say("You stepped out of my sight. Clever. Causality forgives you - this once.");
          return false;
        }
        rooted = playersNear(being.dim, target.location, 3.5);
        for (const p of rooted) {
          effect(p, "slowness", 45, 255);
          effect(p, "mining_fatigue", 45, 2);
          effect(p, "weakness", 45, 1);
          moteRing(being.dim, "gold", add(p.location, v(0, 0.3, 0)), 1.2, 12);
          moteRing(being.dim, "gold", add(p.location, v(0, 1.3, 0)), 1.0, 10);
        }
        sound(being.dim, "random.anvil_land", at, 1, 0.5);
      }
      if (age > 22 && age <= 46) {
        for (const p of rooted) if (p.isValid && age % 3 === 0) beam(being.dim, "gold", eye, chest(p), 0.9);
        if (age % 6 === 0) {
          for (const p of rooted) {
            if (!p.isValid) continue;
            column(being.dim, "gold", p.location);
            hurt(p, 3, being.entity, EntityDamageCause.magic);
          }
        }
      }
      return age < 48;
    }, true);
  },
};

const revelation: Move = {
  id: "revelation",
  name: "Revelation Blink",
  cooldown: 160,
  score: ({ being, target }) => (being.losLost > 40 ? 70 : shielding(target) ? 45 : 0),
  start: ({ being, target }) =>
    act("Revelation Blink", AnimState.Cast, (age) => {
      if (age === 0) {
        const view = target.getViewDirection();
        const behind = add(target.location, v(-view.x * 6, 3, -view.z * 6));
        being.blink(behind, chest(target));
        being.say(shielding(target) ? "A shield faces one direction. I face all of them." : "There is no 'behind' for a being that sees every side.");
      }
      if (age === 10 && target.isValid) {
        const eye = add(being.entity.location, v(0, 2, 0));
        gazeFrom(being, eye, chest(target), 8);
        sound(being.dim, "mob.warden.sonic_boom", eye, 1, 2);
      }
      return age < 14;
    }, true),
};

const spin: Move = {
  id: "ophanim_spin",
  name: "Ophanim Spin",
  cooldown: 110,
  score: ({ distance, being, target }) => (distance < 9 ? 24 + crowd(being, target.location, 6) * 5 : 0),
  start: ({ being }) =>
    act("Ophanim Spin", AnimState.Cast, (age) => {
      const at = being.entity.location;
      if (age < 10) {
        moteRing(being.dim, "gold", add(at, v(0, 2, 0)), 3 + age * 0.3, 20, age * 0.6);
        return true;
      }
      if (age === 10) {
        ringWave(being.dim, "gold", add(groundAt(being, at), v(0, 0.3, 0)), 8, 0.4);
        sphereWave(being.dim, "gold", add(at, v(0, 2, 0)));
        sound(being.dim, "item.trident.riptide_3", at, 1.5, 0.7);
        for (const e of victimsNear(being.dim, at, 8)) {
          hurt(e, 7, being.entity);
          knock(e, at, 1.7, 0.4);
        }
      }
      return age < 14;
    }),
};

/** ULTIMATE: The Eleventh Axis - Rewind. */
const rewind: Move = {
  id: "eleventh_axis",
  name: "The Eleventh Axis",
  cooldown: 900,
  score: () => 0,
  start: ({ being, tick }) => {
    let frozen: Player[] = [];
    return act("The Eleventh Axis", AnimState.Ultimate, (age) => {
      const dim = being.dim;
      const here = being.entity.location;
      if (age === 0) {
        frozen = playersNear(dim, here, 44);
        for (const p of frozen) {
          title(p, "§6§lTHE ELEVENTH AXIS", "§7time is a direction - and it is turning", 70);
          fade(p, [0.45, 0.32, 0.12], 0.3, 1.4, 0.8);
          shake(p, 0.12, 3);
          effect(p, "slowness", 50, 255);
          effect(p, "mining_fatigue", 50, 3);
          sigil(dim, add(groundAt(being, p.location), v(0, 0.1, 0)), 4, 2.4);
        }
        sound(dim, "beacon.deactivate", here, 2, 0.5);
        sound(dim, "mob.wither.spawn", here, 1.2, 1.8);
      }
      if (age < 40) {
        for (const p of frozen) {
          if (!p.isValid) continue;
          const a = -age * 0.35;
          mote(dim, "gold", add(p.location, v(Math.cos(a) * 1.4, 1, Math.sin(a) * 1.4)));
          mote(dim, "white", add(p.location, v(Math.cos(a + Math.PI) * 1.4, 1.6, Math.sin(a + Math.PI) * 1.4)));
        }
        if (age % 8 === 0) glyphs(dim, add(here, v(0, 2, 0)));
        return true;
      }
      if (age === 40) {
        let undone = 0;
        for (const p of frozen) {
          if (!p.isValid) continue;
          const hist = being.history.get(p.id) ?? [];
          const past = hist.find((s) => tick + 40 - s.tick <= 200 && s.dimId === p.dimension.id) ?? hist[0];
          if (!past) continue;
          burst(dim, "gold", chest(p));
          beam(dim, "gold", chest(p), add(past.pos, v(0, 1, 0)), 0.6);
          try {
            p.teleport(past.pos);
          } catch {
            // ignore
          }
          burst(dim, "gold", add(past.pos, v(0, 1, 0)));
        }
        const own = healthOf(being.entity);
        const pastSelf = being.selfHistory.find((s) => tick + 40 - s.tick <= 200) ?? being.selfHistory[0];
        if (own && pastSelf && pastSelf.hp > own.currentValue) {
          undone = Math.min(pastSelf.hp - own.currentValue, own.effectiveMax * 0.15);
          own.setCurrentValue(own.currentValue + undone);
        }
        flash(dim, add(here, v(0, 2, 0)));
        sound(dim, "random.totem", here, 1.5, 0.5);
        being.say(undone > 0 ? `I have un-happened ${Math.round(undone)} points of your victory. Now - every future at once.` : "Rewound. Now - every future at once.", true);
      }
      if (age >= 50 && age <= 130 && (age - 50) % 7 === 0) {
        const pool = playersNear(dim, here, 44);
        const p = pool[Math.floor(Math.random() * pool.length)];
        if (p) {
          const at = groundAt(being, predict(p, 16));
          danger(dim, at, 5, 1.0);
          later(20, () => {
            column(dim, "gold", at);
            column(dim, "white", at);
            ringWave(dim, "gold", add(at, v(0, 0.2, 0)), 3, 0.35);
            sound(dim, "item.trident.thunder", at, 0.7, 1.4);
            blast(being, add(at, v(0, 1, 0)), 2.6, 8);
          });
        }
      }
      if (age === 155) being.exhaustedUntil = system.currentTick + 80;
      return age < 156;
    }, true);
  },
};

export const OBSERVER: BeingDef = {
  typeId: "dim11:observer",
  name: "The Ophanim",
  epithet: "Observer of the Eleventh Axis",
  color: "§6",
  hue: "gold",
  fade: [0.5, 0.36, 0.1],
  speed: 0.25,
  loot: "dim11:eye_of_the_axis",
  hover(b, target, t) {
    const anchor = target && dist(target.location, b.home) < 26 ? b.home : target?.location ?? b.home;
    const g = groundAt(b, target ? target.location : b.home);
    const a = t * 0.01;
    return { x: anchor.x + Math.cos(a) * 3, y: g.y + 2.8 + Math.sin(t * 0.06) * 0.5, z: anchor.z + Math.sin(a) * 3 };
  },
  moves: [gaze, echoes, lock, revelation, spin],
  ultimate: rewind,
  ambient(b, t) {
    if (t % 6 === 0) mote(b.dim, "gold", add(b.entity.location, v(Math.random() * 4 - 2, 1 + Math.random() * 4, Math.random() * 4 - 2)));
  },
  deathFx(b, age) {
    if (age % 6 === 0) {
      const a = age * 0.5;
      beam(b.dim, "gold", add(b.entity.location, v(0, 2, 0)), add(b.entity.location, v(Math.cos(a) * 14, 12, Math.sin(a) * 14)), 0.7);
    }
  },
  lines: {
    intro: [
      "I have already watched this fight. All of its versions. You lose in most of them.",
      "Be not afraid. That is the traditional greeting. It has never once been accurate.",
    ],
    phase2: ["A branch where you wound me. Rare. I will prune it."],
    phase3: ["Then I will stop watching time and start turning it."],
    adapt: {
      melee: "I have seen this swing nine thousand times. My wheels already turn to meet it.",
      projectile: "I watched that arrow leave your bow yesterday. I moved. Tomorrow.",
      arcane: "Your spells were written by observers like me. I have read the ending.",
    },
    ultimate: ["Time is the eleventh axis. Let me turn it for you."],
    kill: ["{name} has reached the end of every timeline at once.", "I saw {name} fall before {name} was born."],
    taunt: ["{name}. In 97% of futures you drop that {weapon}.", "I see you, {name}. I always did."],
    hide: ["You cannot hide from a being that sees every side of every surface.", "Out of sight is still inside my timeline."],
    death: ["I... did not... see... this one..."],
  },
};
