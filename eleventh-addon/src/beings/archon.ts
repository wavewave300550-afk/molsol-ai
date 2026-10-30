import { EntityDamageCause, Player, system } from "@minecraft/server";
import {
  beam, burst, column, danger, fade, flash, glyphs, groundWave, helix, mote, moteRing, ringWave, SEVEN, shake, sigil,
  sound, sphereWave, starfield, title,
} from "../core/fx.js";
import { chest, effect, hurt, knock, playersNear, predict, victimsNear, victimsOnLine } from "../core/targets.js";
import { add, dist, norm, scale, sub, v } from "../core/vec.js";
import { AnimState, BeingDef, Move } from "../engine.js";
import { act, blast, crowd, groundAt } from "./common.js";

/**
 * AEON-7, the Calabi-Yau Archon.
 * A mind that lives folded inside six curled-up dimensions. It fights by bending space:
 * lances that coil through hidden axes, folds that drag you to it, and compactification fields
 * that crush a region of space into a point. Its ultimate unfolds all seven hidden dimensions.
 */

const lance: Move = {
  id: "manifold_lance",
  name: "Manifold Lance",
  cooldown: 70,
  score: ({ distance, being }) => (distance > 4 && distance < 30 && being.losLost === 0 ? 10 + distance * 0.2 : 0),
  start: ({ being, target }) => {
    const hitThisCast = new Set<string>();
    return act("Manifold Lance", AnimState.Cast, (age) => {
      const shot = Math.floor(age / 10);
      if (shot >= 3 || !target.isValid) return age < 32;
      const phase = age % 10;
      const from = add(being.entity.location, v(0, 3.4, 0));
      const aim = predict(target, 6);
      const to = add(aim, v(0, 1, 0));
      const far = add(from, scale(norm(sub(to, from)), 30));
      if (phase === 0) {
        beam(being.dim, "magenta", from, far, 1.5);
        sound(being.dim, "beacon.power", from, 0.7, 1.8);
      } else if (phase === 6) {
        helix(being.dim, "violet", "white", from, far, age * 0.7);
        sound(being.dim, "mob.warden.sonic_boom", from, 0.5, 1.6);
        for (const e of victimsOnLine(being.dim, from, far, 1.3)) {
          if (hitThisCast.has(`${e.id}:${shot}`)) continue;
          hitThisCast.add(`${e.id}:${shot}`);
          hurt(e, 6, being.entity);
          burst(being.dim, "violet", chest(e));
        }
      }
      return true;
    });
  },
};

const fold: Move = {
  id: "spatial_fold",
  name: "Spatial Fold",
  cooldown: 260,
  score: ({ distance, being }) => (being.losLost > 60 ? 60 : distance > 16 ? 25 : distance > 10 ? 8 : 0),
  start: ({ being, target }) =>
    act("Spatial Fold", AnimState.Channel, (age) => {
      const here = add(being.entity.location, v(0, 1.5, 0));
      if (age < 20) {
        if (target.isValid) {
          moteRing(being.dim, "violet", target.location, 1.6 - age * 0.06, 14, age * 0.4);
          beam(being.dim, "violet", here, chest(target), 1.2);
        }
        return true;
      }
      if (age === 20 && target.isValid) {
        const front = add(being.entity.location, scale(norm({ ...sub(target.location, being.entity.location), y: 0 }), 3));
        const landing = groundAt(being, front);
        burst(being.dim, "violet", chest(target));
        glyphs(being.dim, chest(target));
        try {
          target.teleport(landing, { facingLocation: here });
        } catch {
          // target in unloaded area
        }
        burst(being.dim, "violet", add(landing, v(0, 1, 0)));
        effect(target, "slowness", 40, 2);
        sound(being.dim, "mob.endermen.portal", landing, 1.2, 0.5);
        being.say(`Distance is a courtesy of three dimensions, ${target.name}. I do not extend it.`);
      }
      if (age === 30 && target.isValid) {
        blast(being, chest(target), 3, 7);
        groundWave(being.dim, "violet", target.location);
        sound(being.dim, "random.explode", target.location, 0.8, 1.4);
      }
      return age < 34;
    }, true),
};

const compactify: Move = {
  id: "compactification",
  name: "Compactification",
  cooldown: 180,
  score: ({ being, target, distance }) => (distance < 26 ? 12 + crowd(being, target.location, 5) * 8 : 0),
  start: ({ being, target }) => {
    const center = groundAt(being, predict(target, 14));
    const R = 5.5;
    return act("Compactification", AnimState.Channel, (age) => {
      if (age === 0) {
        danger(being.dim, center, R * 2, 1.6);
        sigil(being.dim, add(center, v(0, 0.1, 0)), R * 2.2, 1.8);
        sound(being.dim, "mob.evocation_illager.prepare_attack", center, 1, 0.7);
      }
      if (age < 30) {
        moteRing(being.dim, "violet", add(center, v(0, 0.2, 0)), R * (1 - age / 40), 26, age * 0.3);
        return true;
      }
      if (age === 30) {
        for (const e of victimsNear(being.dim, center, R + 0.5)) {
          if (Math.abs(e.location.y - center.y) > 4) continue;
          knock(e, center, -Math.min(2.5, dist(e.location, center) * 0.45), 0.2);
          effect(e, "slowness", 70, 2);
          hurt(e, 10, being.entity);
        }
        sphereWave(being.dim, "violet", add(center, v(0, 1, 0)));
        burst(being.dim, "white", add(center, v(0, 1, 0)));
        sound(being.dim, "mob.warden.sonic_boom", center, 1, 0.7);
        for (const p of playersNear(being.dim, center, 12)) shake(p, 0.2, 0.6);
      }
      return age < 36;
    });
  },
};

const petalStorm: Move = {
  id: "petal_storm",
  name: "Petal Storm",
  cooldown: 240,
  minPhase: 2,
  score: ({ distance }) => (distance < 15 ? 22 : 6),
  start: ({ being }) => {
    const origin = { ...being.entity.location };
    const hit = new Set<string>();
    sound(being.dim, "mob.breeze.whirl", origin, 1.5, 0.8);
    return act("Petal Storm", AnimState.Cast, (age) => {
      const r = 2 + age * 0.22;
      const y = origin.y + 1.2;
      for (let k = 0; k < 6; k++) {
        const a = age * 0.16 + (k * Math.PI) / 3;
        const p = { x: origin.x + Math.cos(a) * r, y, z: origin.z + Math.sin(a) * r };
        mote(being.dim, k % 2 ? "violet" : "cyan", p);
        mote(being.dim, "white", add(p, v(0, 0.3, 0)));
        for (const e of victimsNear(being.dim, p, 1.6)) {
          const key = `${e.id}:${k}`;
          if (hit.has(key)) continue;
          hit.add(key);
          hurt(e, 5, being.entity);
          knock(e, origin, 0.9, 0.25);
        }
      }
      return age < 60;
    }, true);
  },
};

const blink: Move = {
  id: "calabi_blink",
  name: "Calabi Blink",
  cooldown: 160,
  score: ({ distance, being, tick }) => {
    const close = playersNear(being.dim, being.entity.location, 4).length;
    return close >= 2 ? 40 : distance < 4 && (being.memo.closeSince ?? tick) < tick - 40 ? 30 : 0;
  },
  start: ({ being, target }) =>
    act("Calabi Blink", AnimState.Cast, (age) => {
      if (age === 0) {
        const ang = Math.random() * Math.PI * 2;
        const to = add(target.location, v(Math.cos(ang) * 10, 6, Math.sin(ang) * 10));
        being.blink(to, chest(target));
        being.say("You stand where I was. I am where you are not.");
      }
      return age < 8;
    }, true),
};

/** ULTIMATE: The Seven Unfold. */
const sevenUnfold: Move = {
  id: "seven_unfold",
  name: "The Seven Unfold",
  cooldown: 900,
  score: () => 0,
  start: ({ being }) => {
    const center = groundAt(being, being.entity.location);
    const top = add(center, v(0, 9, 0));
    const waves: { k: number; born: number; hit: Set<string> }[] = [];
    const EFFECTS: ((p: Player) => void)[] = [
      (p) => p.setOnFire(4, true),
      (p) => knock(p, center, 2.6, 0.5),
      (p) => effect(p, "levitation", 30, 1),
      (p) => effect(p, "poison", 80, 1),
      (p) => effect(p, "slowness", 70, 3),
      (p) => {
        effect(p, "mining_fatigue", 120, 2);
        effect(p, "weakness", 120, 1);
      },
      (p) => {
        effect(p, "blindness", 40, 0);
        hurt(p, 6, being.entity, EntityDamageCause.magic);
      },
    ];
    return act("The Seven Unfold", AnimState.Ultimate, (age) => {
      const dim = being.dim;
      if (age === 0) {
        for (const p of playersNear(dim, center, 48)) {
          title(p, "§5§lTHE SEVEN UNFOLD", "§7jump the waves - resist the collapse", 70);
          fade(p, [0.25, 0.05, 0.4], 0.3, 0.4, 0.8);
          shake(p, 0.2, 3);
          effect(p, "darkness", 60, 0);
        }
        sound(dim, "mob.wither.spawn", center, 2, 0.6);
        starfield(dim, top);
      }
      if (age < 30) {
        being.glide(top, undefined, 0.35);
        column(dim, SEVEN[age % 7], add(center, v(Math.cos(age) * 6, 0, Math.sin(age) * 6)));
        return true;
      }
      being.glide(top, undefined, 0.2);
      const rel = age - 30;
      if (rel % 14 === 0 && rel / 14 < 7) {
        const k = rel / 14;
        waves.push({ k, born: age, hit: new Set() });
        ringWave(dim, SEVEN[k], add(center, v(0, 0.3, 0)), 26, 2.1);
        groundWave(dim, SEVEN[k], add(center, v(0, 0.2, 0)));
        burst(dim, SEVEN[k], add(being.entity.location, v(0, 3, 0)));
        sound(dim, "block.end_portal.spawn", center, 0.6, 0.6 + k * 0.15);
      }
      // advance the seven wavefronts (12 blocks/s); airborne players hop over them
      for (const w of waves) {
        const r = (age - w.born) * 0.6;
        if (r > 26) continue;
        moteRing(dim, SEVEN[w.k], add(center, v(0, 0.4, 0)), r, Math.floor(10 + r * 3), age * 0.1);
        for (const p of playersNear(dim, center, r + 2)) {
          const d = Math.hypot(p.location.x - center.x, p.location.z - center.z);
          if (Math.abs(d - r) > 1.4 || w.hit.has(p.id) || p.location.y - center.y > 3) continue;
          w.hit.add(p.id);
          if (!p.isOnGround) {
            mote(dim, "white", chest(p));
            continue; // dodged by jumping
          }
          hurt(p, 4, being.entity, EntityDamageCause.magic);
          EFFECTS[w.k](p);
          burst(dim, SEVEN[w.k], chest(p));
        }
      }
      // recompactification: everything is dragged back to the Archon, then the fold snaps shut
      if (age >= 140 && age < 180) {
        if (age === 140) {
          sound(dim, "mob.warden.sonic_charge", center, 2, 0.6);
          for (const p of playersNear(dim, center, 40)) title(p, "§d§lRECOMPACTIFICATION", "§7run outward!", 40);
        }
        for (const e of victimsNear(dim, center, 26)) {
          knock(e, center, -0.55, 0.0);
        }
        moteRing(dim, "white", add(center, v(0, 1, 0)), 26 - (age - 140) * 0.5, 40, age * 0.2);
        return true;
      }
      if (age === 180) {
        flash(dim, add(center, v(0, 2, 0)));
        sphereWave(dim, "violet", add(center, v(0, 2, 0)));
        sphereWave(dim, "white", add(center, v(0, 2, 0)));
        for (let k = 0; k < 7; k++) ringWave(dim, SEVEN[k], add(center, v(0, 0.3 + k * 0.4, 0)), 8 + k * 2, 0.8);
        blast(being, add(center, v(0, 1, 0)), 7, 14, true);
        sound(dim, "random.explode", center, 2, 0.5);
        for (const p of playersNear(dim, center, 40)) {
          fade(p, [0.9, 0.85, 1], 0.05, 0.2, 0.9);
          shake(p, 0.5, 1.2);
        }
        being.exhaustedUntil = system.currentTick + 80;
      }
      return age < 195;
    }, true);
  },
};

export const ARCHON: BeingDef = {
  typeId: "dim11:archon",
  name: "AEON-7",
  epithet: "the Calabi-Yau Archon",
  color: "§d",
  hue: "violet",
  fade: [0.35, 0.1, 0.55],
  speed: 0.35,
  loot: "dim11:folded_petal",
  hover(b, target, t) {
    if (!target) return add(b.home, v(0, 5, 0));
    const ang = (b.memo.orbit = (b.memo.orbit ?? Math.random() * 6) + 0.006);
    const d = 8.5;
    const g = groundAt(b, target.location);
    if (dist(b.entity.location, target.location) < 4) b.memo.closeSince = b.memo.closeSince ?? t;
    else delete b.memo.closeSince;
    return { x: target.location.x + Math.cos(ang) * d, y: g.y + 1.2 + Math.sin(t * 0.05) * 0.6, z: target.location.z + Math.sin(ang) * d };
  },
  moves: [lance, fold, compactify, petalStorm, blink],
  ultimate: sevenUnfold,
  ambient(b, t) {
    if (t % 4 === 0) {
      const a = t * 0.11;
      const k = Math.floor(t / 4) % 7;
      mote(b.dim, SEVEN[k], add(b.entity.location, v(Math.cos(a) * 1.4, 4.4, Math.sin(a) * 1.4)));
    }
    if (t % 40 === 0) glyphs(b.dim, add(b.entity.location, v(0, 2.5, 0)));
  },
  deathFx(b, age) {
    if (age % 10 === 0) ringWave(b.dim, SEVEN[(age / 10) % 7], add(b.entity.location, v(0, 2.5, 0)), 6 + age * 0.05, 0.6);
    if (age % 3 === 0) {
      const k = age % 7;
      const a = age * 0.4;
      beam(b.dim, SEVEN[k], add(b.entity.location, v(0, 2.5, 0)), add(b.entity.location, v(Math.cos(a) * 9, 2.5 + Math.sin(a * 0.7) * 5, Math.sin(a) * 9)), 0.8);
    }
  },
  lines: {
    intro: [
      "I am AEON-7. I was folded into six curled dimensions before your sun ignited.",
      "You summoned a geometry, not a creature. Geometry does not negotiate.",
    ],
    phase2: ["You have unfolded my first layer. There are six more, and all of them are sharp."],
    phase3: ["Enough. I will show you what lies between the dimensions you can name."],
    adapt: {
      melee: "Your blades travel along three axes. I now exist along eleven. Blades will glance off.",
      projectile: "Arrows follow straight lines. Space around me no longer contains straight lines.",
      arcane: "Your sorcery is borrowed from my geometry. I have taken it back.",
    },
    ultimate: ["Witness the seven hidden dimensions - all of them, at once."],
    kill: ["{name} has been compactified to a point smaller than regret.", "One fewer dimension of {name}."],
    taunt: ["{name}. You hold {weapon} as if it were an argument.", "I will fold the space you stand on, {name}."],
    hide: ["Walls are a three-dimensional idea. I can fold around them.", "Hiding? I can see the other side of every surface."],
    death: ["I... unfold... into... everything..."],
  },
};
