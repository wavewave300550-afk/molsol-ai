import { Entity, system } from "@minecraft/server";
import {
  branePlane, burst, danger, fade, flash, groundWave, mote, ringWave, shake, sound, sphereWave, starfield, stringWave, title,
} from "../core/fx.js";
import { chest, effect, hurt, knock, playersNear, predict, victimsNear, victimsOnLine } from "../core/targets.js";
import { add, dist, lerp, norm, scale, sub, v } from "../core/vec.js";
import { AnimState, BeingDef, Move } from "../engine.js";
import { dismiss, spawnIllusion, spawnWisp, wispCount } from "../minions.js";
import { act, crowd, groundAt } from "./common.js";

/**
 * The M5 Sovereign, a Brane-Leviathan.
 * In M-theory our universe may be a membrane drifting through the bulk. The Sovereign IS a membrane:
 * it swims between universes, its wings ripple like spacetime and its crown is made of open strings.
 * Ultimate: it collides two branes - the event many cosmologists propose as the origin of a Big Bang.
 */

function flatDir(from: { x: number; z: number }, to: { x: number; z: number }) {
  const dx = to.x - from.x;
  const dz = to.z - from.z;
  const l = Math.hypot(dx, dz) || 1;
  return { x: dx / l, y: 0, z: dz / l };
}

const resonance: Move = {
  id: "string_resonance",
  name: "String Resonance",
  cooldown: 80,
  score: ({ distance, being }) => (distance > 5 && distance < 32 && being.losLost === 0 ? 14 : 0),
  start: ({ being, target }) => {
    let from = being.eye;
    let to = add(from, v(0, 0, 1));
    return act("String Resonance", AnimState.Cast, (age) => {
      if (age < 16) {
        from = add(being.entity.location, v(0, 1.6, 0));
        const aim = add(predict(target, 10), v(0, 1, 0));
        to = add(from, scale(norm(sub(aim, from)), 32));
        if (age % 3 === 0) stringWave(being.dim, "cyan", from, to, 0, 0);
        if (age === 0) sound(being.dim, "resonate.amethyst_block", from, 2, 0.5);
        return true;
      }
      if (age < 24) {
        stringWave(being.dim, age % 2 ? "cyan" : "white", from, to, age * 1.3, 0.8);
        if (age === 16) {
          sound(being.dim, "mob.warden.sonic_boom", from, 1, 1.3);
          for (const e of victimsOnLine(being.dim, from, to, 1.4)) {
            hurt(e, 8, being.entity);
            effect(e, "slowness", 40, 1);
            burst(being.dim, "cyan", chest(e));
          }
        }
        return true;
      }
      return false;
    }, true);
  },
};

const dive: Move = {
  id: "brane_dive",
  name: "Brane Dive",
  cooldown: 200,
  score: ({ distance, being }) => (being.losLost > 60 ? 50 : distance > 8 ? 18 : 6),
  start: ({ being, target }) => {
    const start = { ...being.entity.location };
    const dir = flatDir(start, target.location);
    const goal = add(target.location, v(dir.x * 12, 1.5, dir.z * 12));
    const hit = new Set<string>();
    return act("Brane Dive", AnimState.Channel, (age) => {
      if (age < 18) {
        being.glide(add(start, v(0, 4, 0)), goal, 0.4);
        if (age % 3 === 0) {
          for (let k = 0; k <= 10; k++) danger(being.dim, groundAt(being, lerp(start, goal, k / 10)), 2.4, 0.3);
        }
        if (age === 0) sound(being.dim, "mob.phantom.swoop", start, 2, 0.5);
        return true;
      }
      const k = Math.min(1, (age - 18) / 12);
      const p = lerp(add(start, v(0, 4, 0)), goal, k);
      try {
        being.entity.teleport(p, { facingLocation: add(goal, scale(dir, 5)) });
      } catch {
        // ignore
      }
      mote(being.dim, "cyan", p);
      groundWave(being.dim, "cyan", groundAt(being, p));
      for (const e of victimsNear(being.dim, p, 3.8)) {
        if (hit.has(e.id)) continue;
        hit.add(e.id);
        hurt(e, 10, being.entity);
        knock(e, p, 2.2, 0.6);
      }
      if (k >= 1) {
        sphereWave(being.dim, "cyan", p);
        sound(being.dim, "random.explode", p, 0.8, 1.6);
      }
      return k < 1;
    }, true);
  },
};

const chorus: Move = {
  id: "harmonic_chorus",
  name: "Harmonic Chorus",
  cooldown: 360,
  minPhase: 2,
  score: ({ being }) => (wispCount(being) < 3 ? 20 : 0),
  start: ({ being, tick }) =>
    act("Harmonic Chorus", AnimState.Channel, (age) => {
      if (age === 0) {
        sound(being.dim, "mob.evocation_illager.prepare_summon", being.entity.location, 1.5, 1.4);
        being.say("Sing, little strings. Close around them.");
      }
      if (age === 14) {
        for (let k = 0; k < 3; k++) {
          const a = (k / 3) * Math.PI * 2;
          spawnWisp(being, add(being.entity.location, v(Math.cos(a) * 3, 1.5, Math.sin(a) * 3)), tick + age);
        }
      }
      return age < 20;
    }),
};

const wall: Move = {
  id: "brane_wall",
  name: "Brane Wall",
  cooldown: 240,
  score: ({ distance }) => (distance > 6 && distance < 22 ? 12 : 0),
  start: ({ being, target }) => {
    const dir = flatDir(being.entity.location, target.location);
    const axis = { x: -dir.z, y: 0, z: dir.x };
    let c = groundAt(being, add(being.entity.location, scale(dir, 3)));
    const hit = new Set<string>();
    sound(being.dim, "beacon.activate", c, 1.5, 0.6);
    return act("Brane Wall", AnimState.Cast, (age) => {
      c = add(c, scale(dir, 0.42));
      if (age % 2 === 0) branePlane(being.dim, "cyan", c, axis, 14, 6, age * 0.4);
      for (const e of victimsNear(being.dim, add(c, v(0, 3, 0)), 9)) {
        const rel = sub(e.location, c);
        const along = rel.x * dir.x + rel.z * dir.z;
        const across = rel.x * axis.x + rel.z * axis.z;
        if (Math.abs(along) > 1.3 || Math.abs(across) > 7 || rel.y < -1 || rel.y > 6.5) continue;
        try {
          e.applyKnockback({ x: dir.x * 1.6, z: dir.z * 1.6 }, 0.3);
        } catch {
          // ignore
        }
        if (!hit.has(e.id)) {
          hit.add(e.id);
          hurt(e, 4, being.entity);
        }
      }
      return age < 50;
    });
  },
};

const shear: Move = {
  id: "tidal_shear",
  name: "Tidal Shear",
  cooldown: 100,
  score: ({ distance, being, target }) => (distance < 9 ? 26 + crowd(being, target.location, 6) * 5 : 0),
  start: ({ being }) =>
    act("Tidal Shear", AnimState.Cast, (age) => {
      if (age === 8) {
        const at = being.entity.location;
        groundWave(being.dim, "cyan", groundAt(being, at));
        ringWave(being.dim, "cyan", add(groundAt(being, at), v(0, 0.3, 0)), 9, 0.5);
        sound(being.dim, "mob.enderdragon.flap", at, 2, 0.6);
        for (const e of victimsNear(being.dim, at, 9)) {
          hurt(e, 7, being.entity);
          knock(e, at, 1.9, 0.45);
        }
      }
      return age < 14;
    }),
};

/** ULTIMATE: Genesis Collision. */
const genesis: Move = {
  id: "genesis_collision",
  name: "Genesis Collision",
  cooldown: 900,
  score: () => 0,
  start: ({ being, target, tick }) => {
    const center = groundAt(being, lerp(being.entity.location, target.location, 0.5));
    const dir = flatDir(being.entity.location, target.location);
    const axis = { x: -dir.z, y: 0, z: dir.x };
    const START = 20;
    let phantoms: (Entity | undefined)[] = [];
    const pushed = new Map<string, number>();
    return act("Genesis Collision", AnimState.Ultimate, (age) => {
      const dim = being.dim;
      being.glide(add(center, v(0, 13, 0)), add(center, v(0, 0, 0)), 0.45);
      if (age === 0) {
        for (const p of playersNear(dim, center, 56)) {
          title(p, "§b§lGENESIS COLLISION", "§7two universes are about to touch - get out of the bulk", 80);
          fade(p, [0.02, 0.15, 0.22], 0.4, 0.5, 1.0);
          shake(p, 0.15, 5);
        }
        sound(dim, "mob.warden.emerge", center, 2, 0.5);
        phantoms = [-1, 1].map((s) => spawnIllusion(being, "dim11:phantom", add(center, v(dir.x * 20 * s, 6, dir.z * 20 * s)), center, 160, tick));
      }
      if (age < START) return true;
      if (age <= 100) {
        const off = 20 * (1 - (age - START) / 80);
        [-1, 1].forEach((s, i) => {
          const c = add(center, v(dir.x * off * s, 0, dir.z * off * s));
          if (age % 2 === 0) branePlane(dim, i ? "cyan" : "magenta", c, axis, 34, 14, age * 0.3);
          const ph = phantoms[i];
          if (ph?.isValid) {
            try {
              ph.teleport(add(c, v(0, 6, 0)), { facingLocation: center });
            } catch {
              // ignore
            }
          }
          for (const e of victimsNear(dim, add(c, v(0, 7, 0)), 18)) {
            const rel = sub(e.location, c);
            const along = rel.x * dir.x + rel.z * dir.z;
            const across = rel.x * axis.x + rel.z * axis.z;
            if (Math.abs(along) > 1.6 || Math.abs(across) > 17 || rel.y < -2 || rel.y > 14) continue;
            try {
              e.applyKnockback({ x: -dir.x * s * 1.3, z: -dir.z * s * 1.3 }, 0.25);
            } catch {
              // ignore
            }
            const last = pushed.get(e.id) ?? -100;
            if (age - last > 20) {
              pushed.set(e.id, age);
              hurt(e, 2, being.entity);
            }
          }
        });
        if (age % 20 === 0) sound(dim, "mob.warden.heartbeat", center, 2, 0.6 + (age - START) / 100);
        return true;
      }
      if (age === 101) {
        const at = add(center, v(0, 3, 0));
        flash(dim, at);
        sphereWave(dim, "white", at);
        sphereWave(dim, "cyan", at);
        sphereWave(dim, "magenta", at);
        ringWave(dim, "white", add(center, v(0, 0.3, 0)), 24, 0.7);
        starfield(dim, at);
        sound(dim, "random.explode", center, 3, 0.4);
        sound(dim, "mob.wither.death", center, 1.5, 1.5);
        for (const e of victimsNear(dim, center, 18)) {
          const d = dist(e.location, center);
          hurt(e, Math.max(2, 26 * (1 - d / 18)), being.entity);
          knock(e, center, 3.2, 0.9);
        }
        for (const p of playersNear(dim, center, 56)) {
          fade(p, [1, 1, 1], 0.05, 0.3, 1.4);
          shake(p, 0.6, 1.5);
          title(p, "§f§lBIG BANG", "§7a new universe begins to inflate", 50);
        }
        phantoms.forEach(dismiss);
        return true;
      }
      if (age < 160) {
        if (age % 10 === 0) ringWave(dim, age % 20 ? "gold" : "cyan", add(center, v(0, 0.3 + (age - 100) * 0.05, 0)), 12 + (age - 100) * 0.3, 1.2);
        if (age === 110) {
          for (const p of playersNear(dim, center, 26)) {
            effect(p, "levitation", 24, 0);
            effect(p, "slow_falling", 120, 0);
          }
        }
        return true;
      }
      being.exhaustedUntil = system.currentTick + 80;
      return false;
    }, true);
  },
};

export const SOVEREIGN: BeingDef = {
  typeId: "dim11:sovereign",
  name: "The M5 Sovereign",
  epithet: "Brane-Leviathan of the Bulk",
  color: "§b",
  hue: "cyan",
  fade: [0.05, 0.35, 0.45],
  speed: 0.6,
  loot: "dim11:string_of_creation",
  hover(b, target, t) {
    const c = target ? target.location : b.home;
    const g = groundAt(b, c);
    const ang = (b.memo.orbit = (b.memo.orbit ?? 0) + (b.phase === 3 ? 0.024 : 0.016));
    const r = 13;
    return { x: c.x + Math.cos(ang) * r, y: g.y + 2.2 + Math.sin(t * 0.04) * 0.8, z: c.z + Math.sin(ang) * r };
  },
  moves: [resonance, dive, chorus, wall, shear],
  ultimate: genesis,
  ambient(b, t) {
    if (t % 5 === 0) {
      const a = t * 0.2;
      mote(b.dim, "cyan", add(b.entity.location, v(Math.cos(a) * 4, 1.4, Math.sin(a) * 4)));
    }
  },
  deathFx(b, age) {
    if (age % 8 === 0) {
      const dir = { x: Math.cos(age), y: 0, z: Math.sin(age) };
      branePlane(b.dim, age % 16 ? "cyan" : "white", add(groundAt(b, b.entity.location), v(0, 0, 0)), dir, 10 + age * 0.1, 6, age);
    }
  },
  lines: {
    intro: [
      "Your universe is a thin membrane. I am the ocean it floats on.",
      "Every particle you are made of is a string. I can hear all of them. Shall I change the note?",
    ],
    phase2: ["You have wounded a membrane. You have only made it ripple."],
    phase3: ["I will let you witness how universes are born. It is a violent kind of beauty."],
    adapt: {
      melee: "Your blade cuts in three dimensions. My membrane bends in the fourth. It slides through me now.",
      projectile: "Arrows are point particles. I have stretched my surface - they slip off.",
      arcane: "That magic hums at a frequency I already sing. It harmonises with me now.",
    },
    ultimate: ["Two branes. One collision. Let there be light."],
    kill: ["{name}'s strings have stopped vibrating.", "The note that was {name} has ended."],
    taunt: ["{name}, your {weapon} vibrates at such a small frequency.", "I hear your heartbeat, {name}. It is out of tune."],
    hide: ["I do not need to see you. I hear the strings you are made of.", "Hiding inside matter? Matter is made of me."],
    death: ["My membrane... tears... a new universe... without me..."],
  },
};
