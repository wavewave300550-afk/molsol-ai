import { EntityDamageCause, Player, Vector3, system, world } from "@minecraft/server";
import { isTempBlock, placeTemp } from "../core/blocks.js";
import {
  beam, burst, danger, dangerLine, debris, fade, flash, groundWave, mote, ringWave, shake, smoke, sound, sphereWave, title,
} from "../core/fx.js";
import { addTask } from "../core/tasks.js";
import { chest, effect, healthOf, hurt, playersNear, predict, victimsNear } from "../core/targets.js";
import { add, dist, lerp, v } from "../core/vec.js";
import { Boss, BossDef, Move, S } from "../engine.js";
import { act, crowd, exhaust, flatDir, ground, up } from "./common.js";

/**
 * THE WORLD PARASITE - a hill that is alive.
 * Summoned dormant: it looks like a grassy mound with a tree until you come too close or strike it.
 * Signature: it burrows (untouchable underground) and erupts beneath you, and it roots parasitic
 * tethers into players that drain them to heal itself - break them by running away. Ultimate:
 * Continental Bite - it erupts as a gigantic maw and infects the surrounding terrain (real blocks,
 * restored later): stay off the infected earth.
 */

const INFECTION = "minecraft:crimson_nylium";
interface Tether {
  playerId: string;
  until: number;
}
const tethers = new Map<string, Tether[]>();

function heal(b: Boss, amount: number): void {
  const h = healthOf(b.entity);
  if (h) h.setCurrentValue(Math.min(h.effectiveMax, h.currentValue + amount));
}

const burrow: Move = {
  id: "burrow_ambush",
  name: "Burrow Ambush",
  cooldown: 260,
  score: ({ distance, boss }) => (boss.losLost > 40 ? 40 : distance > 9 ? 16 : 0),
  start: ({ boss, target }) => {
    let aim: Vector3 = target.location;
    const start = { ...boss.entity.location };
    return act("Burrow Ambush", S.Burrow, (age) => {
      if (age < 20) {
        boss.glide(add(start, v(0, -4.5 * (age / 20), 0)), target.location, 0.4);
        if (age % 3 === 0) debris(boss.dim, up(start, 0.5));
        if (age === 0) sound(boss.dim, "dig.gravel", start, 2, 0.5);
        return true;
      }
      if (age < 56) {
        if (age < 48 && target.isValid) aim = ground(boss, target.location);
        const under = add(lerp(start, aim, (age - 20) / 36), v(0, -4.5, 0));
        boss.glide(under, aim, 2);
        if (age % 3 === 0) debris(boss.dim, up(ground(boss, under), 0.3));
        if (age % 8 === 0) danger(boss.dim, aim, 8, 0.45);
        return true;
      }
      if (age === 56) {
        boss.glide(aim, undefined, 9);
        flash(boss.dim, up(aim, 1));
        for (let k = 0; k < 4; k++) debris(boss.dim, add(aim, v(Math.random() * 4 - 2, 1, Math.random() * 4 - 2)));
        groundWave(boss.dim, "green", up(aim, 0.3));
        sound(boss.dim, "random.explode", aim, 1.5, 0.6);
        for (const e of victimsNear(boss.dim, aim, 4.2)) {
          hurt(e, 14, boss.entity);
          try {
            e.applyKnockback({ x: 0.001, z: 0.001 }, 1.2);
          } catch {
            // ignore
          }
        }
        for (const p of playersNear(boss.dim, aim, 16)) shake(p, 0.4, 0.8);
      }
      return age < 62;
    }, { hold: true, invulnerable: true });
  },
};

const roots: Move = {
  id: "root_spikes",
  name: "Root Spikes",
  cooldown: 120,
  score: ({ distance }) => (distance < 22 ? 14 : 0),
  start: ({ boss, target }) => {
    const from = ground(boss, boss.entity.location);
    const d = flatDir(from, predict(target, 10));
    const spots: Vector3[] = [];
    for (let k = 1; k <= 9; k++) spots.push(ground(boss, add(from, v(d.x * k * 2.2, 0, d.z * k * 2.2))));
    return act("Root Spikes", S.AtkA, (age) => {
      if (age === 0) dangerLine(boss.dim, spots[0], spots[spots.length - 1], 2.8, 1.4);
      const k = Math.floor((age - 14) / 3);
      if (age >= 14 && (age - 14) % 3 === 0 && k < spots.length) {
        const s = spots[k];
        debris(boss.dim, up(s, 0.5));
        mote(boss.dim, "green", up(s, 1.5));
        sound(boss.dim, "dig.wood", s, 1, 0.6);
        for (const e of victimsNear(boss.dim, s, 1.7)) {
          hurt(e, 7, boss.entity);
          effect(e, "slowness", 50, 1);
        }
      }
      return age < 14 + spots.length * 3 + 4;
    });
  },
};

const tether: Move = {
  id: "parasitic_tethers",
  name: "Parasitic Tethers",
  cooldown: 420,
  score: ({ boss }) => ((tethers.get(boss.entity.id)?.length ?? 0) === 0 ? 11 + playersNear(boss.dim, boss.entity.location, 14).length * 3 : 0),
  start: ({ boss }) =>
    act("Parasitic Tethers", S.Channel, (age) => {
      if (age === 16) {
        const list = playersNear(boss.dim, boss.entity.location, 14).slice(0, 3);
        tethers.set(boss.entity.id, list.map((p) => ({ playerId: p.id, until: system.currentTick + 220 })));
        for (const p of list) title(p, "§2§lTETHERED", "§7run more than 16 blocks away to tear the root", 40);
        sound(boss.dim, "mob.warden.heartbeat", boss.entity.location, 2, 0.8);
      }
      return age < 20;
    }),
};

const spores: Move = {
  id: "spore_cloud",
  name: "Spore Cloud",
  cooldown: 240,
  score: ({ boss, target }) => 10 + crowd(boss, target.location, 6) * 3,
  start: ({ boss, target }) => {
    const at = ground(boss, predict(target, 10));
    return act("Spore Cloud", S.AtkB, (age) => {
      if (age === 10) {
        sound(boss.dim, "mob.breeze.inhale", at, 2, 0.4);
        addTask("spores", (a) => {
          for (let i = 0; i < 3; i++) smoke(boss.dim, "spore", add(at, v(Math.random() * 10 - 5, 0.3 + Math.random() * 2.5, Math.random() * 10 - 5)));
          if (a % 20 === 0) {
            for (const p of playersNear(boss.dim, at, 6)) {
              effect(p, "poison", 60, 0);
              effect(p, "nausea", 80, 0);
              hurt(p, 1, undefined, EntityDamageCause.magic);
            }
          }
          return a < 110;
        });
      }
      return age < 14;
    });
  },
};

const quake: Move = {
  id: "tectonic_slam",
  name: "Tectonic Slam",
  cooldown: 140,
  score: ({ boss }) => (playersNear(boss.dim, boss.entity.location, 9).length ? 20 : 0),
  start: ({ boss }) =>
    act("Tectonic Slam", S.AtkC, (age) => {
      const at = ground(boss, boss.entity.location);
      if (age === 0) danger(boss.dim, at, 18, 1.2);
      if (age === 24) {
        ringWave(boss.dim, "green", up(at, 0.3), 10, 0.5);
        groundWave(boss.dim, "green", up(at, 0.3));
        for (let k = 0; k < 6; k++) debris(boss.dim, add(at, v(Math.cos(k) * 5, 0.5, Math.sin(k) * 5)));
        sound(boss.dim, "random.explode", at, 2, 0.4);
        for (const p of playersNear(boss.dim, at, 9.5)) {
          shake(p, 0.5, 0.8);
          if (!p.isOnGround) continue; // jumped the quake
          hurt(p, 10, boss.entity);
          try {
            p.applyKnockback({ x: 0.001, z: 0.001 }, 0.9);
          } catch {
            // ignore
          }
        }
      }
      return age < 30;
    }, { hold: true }),
};

/** ULTIMATE: Continental Bite. */
const bite: Move = {
  id: "continental_bite",
  name: "Continental Bite",
  cooldown: 900,
  score: () => 0,
  start: ({ boss }) => {
    const start = { ...boss.entity.location };
    let center = start;
    let infected = 0;
    return act("Continental Bite", S.Ultimate, (age) => {
      const dim = boss.dim;
      if (age === 0) {
        for (const p of playersNear(dim, start, 50)) {
          title(p, "§2§lCONTINENTAL BITE", "§7the ground is its mouth - stay off the infected earth", 80);
          fade(p, [0.1, 0.25, 0.05], 0.4, 0.4, 0.8);
        }
        sound(dim, "mob.warden.roar", start, 2, 0.5);
      }
      if (age < 30) {
        boss.glide(add(start, v(0, -6 * (age / 30), 0)), undefined, 0.5);
        if (age % 3 === 0) debris(dim, up(start, 0.5));
        return true;
      }
      if (age === 30) {
        const ps = playersNear(dim, start, 40);
        if (ps.length) {
          const c = ps.reduce((a, p) => add(a, p.location), v(0, 0, 0));
          center = ground(boss, { x: c.x / ps.length, y: c.y / ps.length, z: c.z / ps.length });
        } else center = ground(boss, start);
      }
      if (age > 30 && age < 80) {
        if (age % 10 === 0) danger(dim, center, 12, 0.6);
        if (age % 4 === 0) debris(dim, add(center, v(Math.cos(age) * 6, 0.3, Math.sin(age) * 6)));
        if (age % 10 === 0) for (const p of playersNear(dim, center, 30)) shake(p, 0.2 + (age - 30) * 0.006, 0.6);
        boss.glide(add(center, v(0, -6, 0)), undefined, 3);
        return true;
      }
      if (age === 80) {
        boss.glide(center, undefined, 10);
        flash(dim, up(center, 2));
        sphereWave(dim, "green", up(center, 2));
        for (let k = 0; k < 8; k++) debris(dim, add(center, v(Math.random() * 10 - 5, 1, Math.random() * 10 - 5)));
        sound(dim, "random.explode", center, 3, 0.4);
        for (const e of victimsNear(dim, center, 6.5)) {
          hurt(e, 22, boss.entity);
          try {
            e.applyKnockback({ x: (e.location.x - center.x) * 0.2 + 0.01, z: (e.location.z - center.z) * 0.2 + 0.01 }, 1.6);
          } catch {
            // ignore
          }
        }
        // infection: the surface around the bite turns into living tissue
        const c = { x: Math.floor(center.x), z: Math.floor(center.z) };
        for (let dx = -12; dx <= 12; dx++) {
          for (let dz = -12; dz <= 12; dz++) {
            if (dx * dx + dz * dz > 144) continue;
            const g = boss.groundBelow({ x: c.x + dx + 0.5, y: center.y + 4, z: c.z + dz + 0.5 });
            if (placeTemp(dim, { x: g.x, y: g.y - 1, z: g.z }, INFECTION, 230, "natural")) infected++;
          }
        }
        boss.say(infected ? "Your world is my flesh now." : "No soil to take root in? Then I will take you.");
      }
      if (age > 90 && age < 230 && age % 10 === 0) {
        for (const p of playersNear(dim, center, 18)) {
          const below = { x: p.location.x, y: p.location.y - 0.5, z: p.location.z };
          if (isTempBlock(dim.id, below) || (!infected && Math.hypot(p.location.x - center.x, p.location.z - center.z) < 10)) {
            hurt(p, 2, boss.entity, EntityDamageCause.magic);
            effect(p, "poison", 40, 0);
            smoke(dim, "spore", up(p.location, 0.3));
            heal(boss, 2);
          }
        }
      }
      if (age === 230) exhaust(boss, 90);
      return age < 234;
    }, { hold: true });
  },
};

export const PARASITE: BossDef = {
  typeId: "fb:world_parasite",
  key: "world_parasite",
  name: "The World Parasite",
  epithet: "the Hill that Eats",
  color: "§2",
  hue: "green",
  fade: [0.1, 0.3, 0.05],
  speed: 0.075,
  mode: "walk",
  eyeHeight: 1.6,
  spawnTicks: 60,
  startsDormant: true,
  loot: "fb:parasite_seed",
  hover(b, target) {
    if (!target) return b.home;
    if (dist(b.entity.location, target.location) < 9) return b.entity.location;
    const d = flatDir(b.entity.location, target.location);
    return add(b.entity.location, v(d.x * 2, 0, d.z * 2));
  },
  mechanic(b, t) {
    const list = tethers.get(b.entity.id);
    if (!list?.length) return;
    const keep: Tether[] = [];
    for (const tt of list) {
      const p = world.getEntity(tt.playerId);
      if (!(p instanceof Player) || !p.isValid || t >= tt.until) continue;
      if (dist(p.location, b.entity.location) > 16) {
        p.sendMessage("§2You tear the parasitic root out of your flesh!");
        burst(b.dim, "green", chest(p));
        continue;
      }
      if (t % 3 === 0) beam(b.dim, t % 6 ? "green" : "red", up(b.entity.location, 1.5), chest(p), 1.1);
      if (t % 20 === 0) {
        hurt(p, 2, b.entity, EntityDamageCause.magic);
        heal(b, 4);
        mote(b.dim, "red", up(b.entity.location, 2));
      }
      keep.push(tt);
    }
    tethers.set(b.entity.id, keep);
  },
  hudInfo(b) {
    const n = tethers.get(b.entity.id)?.length ?? 0;
    return n ? `§2${n} tether${n > 1 ? "s" : ""} draining` : "§2rooted";
  },
  onAwaken(b) {
    const at = b.entity.location;
    for (let k = 0; k < 6; k++) debris(b.dim, add(at, v(Math.random() * 8 - 4, 1, Math.random() * 8 - 4)));
    sound(b.dim, "mob.warden.emerge", at, 2, 0.6);
    groundWave(b.dim, "green", up(at, 0.2));
  },
  moves: [burrow, roots, tether, spores, quake],
  ultimate: bite,
  ambient(b, t) {
    if (!b.dormant && t % 8 === 0) smoke(b.dim, "spore", add(b.entity.location, v(Math.random() * 6 - 3, 2 + Math.random() * 3, Math.random() * 6 - 3)));
  },
  deathFx(b, age) {
    if (age % 5 === 0) debris(b.dim, add(b.entity.location, v(Math.random() * 6 - 3, Math.random() * 3, Math.random() * 6 - 3)));
  },
  lines: {
    intro: ["...you stepped on me. Everyone always steps on me.", "This hill is hungry."],
    phase2: ["I have roots under your whole world."],
    phase3: ["Then I will swallow the ground you stand on."],
    ultimate: ["Open wide, little world."],
    kill: ["{name} becomes fertiliser.", "{name} feeds the roots."],
    taunt: ["{name}, I tasted you through the soil.", "That {weapon} smells of the mines I grew under."],
    death: ["The hill... is... only a hill... again..."],
  },
};

export const PARASITE_TEST = { tethers };
