import { Entity, EntityDamageCause, Vector3, system } from "@minecraft/server";
import {
  beam, danger, dangerLine, fade, flash, mote, moteRing, ringWave, shake, shards, sound, sphereWave, title,
} from "../core/fx.js";
import { addTask } from "../core/tasks.js";
import { chest, effect, hurt, knock, playersNear, predict, victimsNear, victimsOnLine } from "../core/targets.js";
import { add, scale, v } from "../core/vec.js";
import { Boss, BossDef, Move, S } from "../engine.js";
import { illusionOf, illusionsOf, shatter, spawnIllusion } from "../minions.js";
import { act, crowd, exhaust, flatDir, ground, rotY, up } from "./common.js";

/**
 * THE CHOIR OF MIRRORS - a cathedral of reflections that sings.
 * Signature: MIRROR WARD - every few seconds its halo flares silver; while it does, most damage
 * dealt to it is reflected back at the attacker. Mirror images fight beside it and punish anyone
 * who strikes a reflection. Ultimate: Hall of Infinite Reflections - six mirrors, one true. Find
 * and break the true one (it sings in gold) before the Requiem.
 */

const ECHO = "fb:choir_echo";
const reflectQueue: { attacker: Entity; amount: number; at: Vector3 }[] = [];
const mirrorHits: { mirror: Entity; attacker: Entity | undefined }[] = [];

function wardActive(b: Boss, t: number): boolean {
  return (b.memo.wardUntil ?? 0) > t;
}

/** Called from main (before-event) when an illusion of the choir is struck. */
export function mirrorStruck(mirror: Entity, attacker: Entity | undefined): void {
  mirrorHits.push({ mirror, attacker });
}

const chord: Move = {
  id: "harmonic_chord",
  name: "Harmonic Chord",
  cooldown: 110,
  score: ({ distance }) => (distance < 26 ? 14 : 0),
  start: ({ boss, target }) => {
    const base = flatDir(boss.entity.location, predict(target, 8));
    const dirs = [-22, 0, 22].map((d) => rotY(base, d));
    return act("Harmonic Chord", S.AtkA, (age) => {
      const from = up(boss.entity.location, 3.5);
      dirs.forEach((d, i) => {
        const to = add(from, v(d.x * 24, -2.5, d.z * 24));
        if (age === i * 8) {
          dangerLine(boss.dim, ground(boss, from), ground(boss, to), 3, 0.65);
          sound(boss.dim, "note.harp", from, 2, 0.6 + i * 0.3);
        }
        if (age === i * 8 + 13) {
          for (let k = 0; k <= 24; k += 2) ringWave(boss.dim, "silver", add(from, v(d.x * k, -2.5 * (k / 24), d.z * k)), 1.4, 0.3);
          sound(boss.dim, "note.bell", from, 2, 0.5 + i * 0.25);
          for (const e of victimsOnLine(boss.dim, from, to, 1.7)) {
            hurt(e, 6, boss.entity, EntityDamageCause.magic);
            effect(e, "slowness", 40, 1);
          }
        }
      });
      return age < 34;
    });
  },
};

const reflections: Move = {
  id: "reflections",
  name: "Reflections",
  cooldown: 420,
  score: ({ boss }) => (illusionsOf(boss, "image").length === 0 ? 13 : 0),
  start: ({ boss, tick }) =>
    act("Reflections", S.Channel, (age) => {
      if (age === 12) {
        const ps = playersNear(boss.dim, boss.entity.location, 30);
        for (let k = 0; k < 4; k++) {
          const anchor = ps[k % Math.max(1, ps.length)]?.location ?? boss.entity.location;
          const a = (k / 4) * Math.PI * 2 + Math.random();
          spawnIllusion(boss, ECHO, add(anchor, v(Math.cos(a) * 7, 2.5, Math.sin(a) * 7)), 180, tick + age, "image");
        }
        boss.say("Which of us is the reflection? Strike carefully.");
        sound(boss.dim, "random.glass", boss.entity.location, 2, 1.5);
      }
      return age < 16;
    }),
};

const swap: Move = {
  id: "reflection_swap",
  name: "Reflection Swap",
  cooldown: 200,
  score: ({ boss }) => (playersNear(boss.dim, boss.entity.location, 28).length ? 11 : 0),
  start: ({ boss, target }) =>
    act("Reflection Swap", S.AtkB, (age) => {
      if (age === 0) moteRing(boss.dim, "silver", up(target.location, 1), 1.4, 14);
      if (age === 14) {
        const ps = playersNear(boss.dim, boss.entity.location, 28);
        const c = ground(boss, boss.entity.location);
        if (ps.length >= 2) {
          const [a, b2] = [ps[0].location, ps[1].location];
          try {
            ps[0].teleport(b2);
            ps[1].teleport(a);
          } catch {
            // ignore
          }
          for (const p of ps.slice(0, 2)) {
            effect(p, "slowness", 30, 1);
            shards(boss.dim, chest(p));
          }
        } else if (target.isValid) {
          const mirrored = ground(boss, { x: 2 * c.x - target.location.x, y: target.location.y, z: 2 * c.z - target.location.z });
          shards(boss.dim, chest(target));
          try {
            target.teleport(mirrored);
          } catch {
            // ignore
          }
          effect(target, "slowness", 30, 1);
          shards(boss.dim, up(mirrored, 1));
        }
        sound(boss.dim, "mob.endermen.portal", c, 2, 1.6);
      }
      return age < 18;
    }),
};

const glassRain: Move = {
  id: "shattered_choir",
  name: "Shattered Choir",
  cooldown: 180,
  score: ({ boss, target }) => 12 + crowd(boss, target.location, 6) * 3,
  start: ({ boss }) =>
    act("Shattered Choir", S.AtkC, (age) => {
      if (age % 4 === 0 && age < 40) {
        const ps = playersNear(boss.dim, boss.entity.location, 30);
        const p = ps[Math.floor(Math.random() * ps.length)];
        if (p) {
          const at = ground(boss, add(predict(p, 18), v(Math.random() * 3 - 1.5, 0, Math.random() * 3 - 1.5)));
          danger(boss.dim, at, 3.4, 0.9);
          addTask("glass", (a) => {
            if (a === 18) {
              shards(boss.dim, up(at, 0.5));
              beam(boss.dim, "silver", up(at, 9), up(at, 0.2), 0.6);
              sound(boss.dim, "random.glass", at, 1, 1.2);
              for (const e of victimsNear(boss.dim, at, 1.8)) hurt(e, 5, boss.entity.isValid ? boss.entity : undefined);
            }
            return a < 18;
          });
        }
      }
      return age < 44;
    }),
};

const orbit: Move = {
  id: "chorister_orbit",
  name: "Chorister Orbit",
  cooldown: 130,
  score: ({ boss }) => (playersNear(boss.dim, boss.entity.location, 9).length ? 22 : 0),
  start: ({ boss }) =>
    act("Chorister Orbit", S.AtkD, (age) => {
      const at = boss.entity.location;
      if (age < 12) {
        moteRing(boss.dim, "silver", up(at, 3), 3 + age * 0.5, 18, age * 0.5);
        return true;
      }
      if (age === 12) {
        ringWave(boss.dim, "silver", up(ground(boss, at), 0.3), 9.5, 0.4);
        sound(boss.dim, "note.chime", at, 2, 0.6);
        for (const e of victimsNear(boss.dim, at, 9.5)) {
          hurt(e, 8, boss.entity);
          knock(e, at, 1.9, 0.4);
        }
      }
      return age < 18;
    }, { hold: true }),
};

/** ULTIMATE: Hall of Infinite Reflections. */
const hall: Move = {
  id: "hall_of_reflections",
  name: "Hall of Infinite Reflections",
  cooldown: 900,
  score: () => 0,
  start: ({ boss, tick }) => {
    const center = ground(boss, boss.home);
    const mirrors: (Entity | undefined)[] = [];
    let trueIdx = 0;
    let solved = false;
    return act("Hall of Infinite Reflections", S.Ultimate, (age) => {
      const dim = boss.dim;
      boss.glide(up(center, 9), undefined, 0.3);
      if (age === 0) {
        for (const p of playersNear(dim, center, 50)) {
          title(p, "§f§lHALL OF INFINITE REFLECTIONS", "§7one mirror is true - it sings in gold. Break it.", 90);
          fade(p, [0.75, 0.85, 1], 0.3, 0.4, 0.9);
        }
        sound(dim, "beacon.activate", center, 2, 1.6);
        trueIdx = Math.floor(Math.random() * 6);
        for (let k = 0; k < 6; k++) {
          const a = (k / 6) * Math.PI * 2;
          mirrors.push(spawnIllusion(boss, ECHO, add(center, v(Math.cos(a) * 12, 2.5, Math.sin(a) * 12)), 260, tick, k === trueIdx ? "true" : "false"));
        }
        boss.memo.hallActive = 1;
      }
      if (boss.memo.hallSolved) {
        solved = true;
        boss.memo.hallSolved = 0;
      }
      if (solved) {
        for (const m of mirrors) shatter(m);
        flash(dim, up(center, 4));
        sphereWave(dim, "gold", up(center, 4));
        for (const p of playersNear(dim, center, 50)) title(p, "§6§lTHE TRUE MIRROR BREAKS", "§7the Choir falls silent - strike now!", 50);
        boss.memo.hallActive = 0;
        exhaust(boss, 140);
        return false;
      }
      mirrors.forEach((m, k) => {
        if (!m?.isValid) return;
        if (age % 10 === k % 10) mote(dim, k === trueIdx ? "gold" : "silver", up(m.location, 3.6));
        if (k === trueIdx && age % 20 === 0) sound(dim, "note.bell", m.location, 0.8, 1.8);
      });
      // refraction: light beams bounce between the mirrors in a star pattern
      const phase = age % 30;
      const live = mirrors.filter((m): m is Entity => !!m && m.isValid);
      if (live.length >= 2) {
        const off = Math.floor(age / 30) % 2 ? 2 : 3;
        for (let k = 0; k < live.length; k++) {
          const a = up(live[k].location, 2);
          const b2 = up(live[(k + off) % live.length].location, 2);
          if (phase === 0) dangerLine(dim, ground(boss, a), ground(boss, b2), 2.2, 0.6);
          if (phase === 13) {
            beam(dim, "white", a, b2, 0.6);
            for (const e of victimsOnLine(dim, { ...a, y: center.y + 0.5 }, { ...b2, y: center.y + 0.5 }, 1.4)) hurt(e, 6, boss.entity, EntityDamageCause.magic);
          }
        }
      }
      if (age === 240) {
        flash(dim, up(center, 5));
        sphereWave(dim, "silver", up(center, 5));
        sound(dim, "mob.wither.death", center, 1.5, 1.8);
        for (const p of playersNear(dim, center, 32)) {
          hurt(p, 16, boss.entity, EntityDamageCause.magic);
          effect(p, "blindness", 50, 0);
          title(p, "§f§lREQUIEM", "§7the choir sings your ending", 30);
          shake(p, 0.4, 1);
        }
        for (const m of mirrors) shatter(m);
        boss.memo.hallActive = 0;
        exhaust(boss, 60);
      }
      return age < 244;
    }, { hold: true, invulnerable: true });
  },
};

export const CHOIR: BossDef = {
  typeId: "fb:choir",
  key: "choir",
  name: "The Choir of Mirrors",
  epithet: "Requiem in Glass",
  color: "§f",
  hue: "silver",
  fade: [0.8, 0.88, 1],
  speed: 0.28,
  mode: "hover",
  eyeHeight: 3.6,
  spawnTicks: 70,
  loot: "fb:shard_of_truth",
  hover(b, target, t) {
    const c = target ? target.location : b.home;
    const away = target ? flatDir(target.location, b.home) : v(1, 0, 0);
    const side = rotY(away, Math.sin(t * 0.01) * 60);
    const p = add(c, scale(side, 10));
    return { x: p.x, y: b.groundBelow(p).y + 1.5 + Math.sin(t * 0.06) * 0.5, z: p.z };
  },
  incoming(b, amount, _cause, attacker) {
    if (!wardActive(b, system.currentTick)) return amount;
    if (attacker) reflectQueue.push({ attacker, amount: amount * 0.6, at: { ...b.entity.location } });
    return amount * 0.4;
  },
  mechanic(b, t) {
    // ward cycle: telegraph 30 ticks, active 80 ticks, every 240 ticks
    const cyc = (t + (b.memo.wardSeed ??= Math.floor(Math.random() * 240))) % 240;
    if (cyc === 0) {
      sound(b.dim, "beacon.power", b.entity.location, 1.5, 1.8);
      for (const p of playersNear(b.dim, b.entity.location, 40)) p.onScreenDisplay.setTitle(" ", { subtitle: "§fThe mirrors turn towards you...", fadeInDuration: 0, stayDuration: 25, fadeOutDuration: 5 });
    }
    if (cyc < 30 && cyc % 4 === 0) moteRing(b.dim, "silver", up(b.entity.location, 3.6), 3.5, 16, t * 0.3);
    if (cyc === 30) b.memo.wardUntil = t + 80;
    if (wardActive(b, t) && t % 3 === 0) moteRing(b.dim, "white", up(b.entity.location, 3.6), 4.2, 20, t * 0.2);
    while (reflectQueue.length) {
      const r = reflectQueue.shift()!;
      if (r.attacker.isValid) {
        beam(b.dim, "silver", up(r.at, 3.6), chest(r.attacker), 0.8);
        hurt(r.attacker, r.amount, b.entity, EntityDamageCause.magic);
      }
    }
    // strikes on mirrors (from main's before-event)
    while (mirrorHits.length) {
      const h = mirrorHits.shift()!;
      const il = h.mirror.isValid ? illusionOf(h.mirror) : undefined;
      if (!il) continue;
      if (il.tag === "true") {
        b.memo.hallSolved = 1;
      } else {
        if (h.attacker?.isValid) {
          hurt(h.attacker, 6, b.entity, EntityDamageCause.magic);
          beam(b.dim, "silver", up(h.mirror.location, 2), chest(h.attacker), 0.8);
        }
        shatter(h.mirror);
      }
    }
    // mirror images shoot light at the nearest player
    if (t % 40 === 0) {
      for (const il of illusionsOf(b, "image")) {
        const p = playersNear(b.dim, il.entity.location, 18)[0];
        if (!p) continue;
        const from = up(il.entity.location, 2.5);
        beam(b.dim, "silver", from, chest(p), 0.7);
        hurt(p, 4, b.entity, EntityDamageCause.magic);
      }
    }
    // keep images facing the players
    if (t % 5 === 0) {
      for (const il of illusionsOf(b)) {
        const p = playersNear(b.dim, il.entity.location, 30)[0];
        if (p) {
          try {
            il.entity.teleport(il.entity.location, { facingLocation: { x: p.location.x, y: il.entity.location.y + 2, z: p.location.z } });
          } catch {
            // ignore
          }
        }
      }
    }
  },
  hudInfo(b) {
    return wardActive(b, system.currentTick) ? "§f§lMIRROR WARD§r §7(damage reflected)" : "§7ward down";
  },
  moves: [chord, reflections, swap, glassRain, orbit],
  ultimate: hall,
  ambient(b, t) {
    if (t % 6 === 0) shards(b.dim, add(b.entity.location, v(Math.random() * 4 - 2, 2 + Math.random() * 4, Math.random() * 4 - 2)));
  },
  deathFx(b, age) {
    if (age % 4 === 0) shards(b.dim, add(b.entity.location, v(Math.random() * 6 - 3, 1 + Math.random() * 5, Math.random() * 6 - 3)));
    if (age % 20 === 0) sound(b.dim, "random.glass", b.entity.location, 2, 0.6 + age * 0.01);
  },
  lines: {
    intro: ["We are many. We are one. We are what you see when you look at us.", "Sing with us. Everyone sings, in the end."],
    phase2: ["You broke a pane. We have a thousand more."],
    phase3: ["Let the hall stretch on forever."],
    ultimate: ["Which of us is real? Choose. Choose quickly."],
    kill: ["{name}'s reflection remains. That will do.", "{name} joins the choir."],
    taunt: ["{name}, we have seen that {weapon} in every mirror.", "Look at yourself, {name}. Look closer."],
    death: ["The... song... ends..."],
  },
};

export const CHOIR_TEST = { reflectQueue, mirrorHits, wardActive };
