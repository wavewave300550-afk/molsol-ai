import { EntityDamageCause, Player, Vector3 } from "@minecraft/server";
import { placeTemp } from "../core/blocks.js";
import {
  beam, burst, column, danger, dangerLine, debris, embers, fade, flash, groundWave, mote, moteRing, ringWave, shake, sigil, smoke,
  sound, title,
} from "../core/fx.js";
import { addTask } from "../core/tasks.js";
import { chest, hurt, knock, lineOfSight, playersNear, predict, victimsNear } from "../core/targets.js";
import { add, dist, v } from "../core/vec.js";
import { Boss, BossDef, Move, S } from "../engine.js";
import { act, arc, crowd, exhaust, flatDir, ground, rotY, up } from "./common.js";

/**
 * THE TITAN OF CREATION - a walking world-forge.
 * The only boss that edits the world: it builds prisons around you, raises pillars under your
 * feet and, for its ultimate, erects real cover pillars and sweeps a beam of pure creation around
 * the arena - hide behind what it built or be unmade. Every block it places is journaled and
 * restored afterwards.
 */

const PRISON_BLOCK = "minecraft:polished_blackstone_bricks";
const PILLAR_BLOCK = "minecraft:smooth_stone";
const COVER_BLOCK = "minecraft:polished_deepslate";

const hammer: Move = {
  id: "forge_hammer",
  name: "Forge Hammer",
  cooldown: 80,
  score: ({ distance }) => (distance < 12 ? 18 : 0),
  start: ({ boss, target }) => {
    const from = ground(boss, boss.entity.location);
    const d = flatDir(from, target.location);
    const to = add(from, v(d.x * 13, 0, d.z * 13));
    return act("Forge Hammer", S.AtkA, (age) => {
      if (age === 0) {
        dangerLine(boss.dim, from, to, 3.4, 1.2);
        sound(boss.dim, "mob.irongolem.throw", from, 1.5, 0.5);
      }
      if (age === 24) {
        for (let k = 1; k <= 12; k++) {
          const p = add(from, v(d.x * k, 0.2, d.z * k));
          groundWave(boss.dim, "orange", p);
          if (k % 2 === 0) debris(boss.dim, p);
        }
        for (const e of victimsNear(boss.dim, add(from, v(d.x * 6.5, 1, d.z * 6.5)), 8)) {
          const rel = { x: e.location.x - from.x, z: e.location.z - from.z };
          const along = rel.x * d.x + rel.z * d.z;
          const across = Math.abs(rel.x * -d.z + rel.z * d.x);
          if (along > -1 && along < 13.5 && across < 2.6) {
            hurt(e, 13, boss.entity);
            try {
              e.applyKnockback({ x: d.x * 0.6, z: d.z * 0.6 }, 0.8);
            } catch {
              // ignore
            }
          }
        }
        sound(boss.dim, "random.anvil_land", from, 2, 0.4);
        sound(boss.dim, "random.explode", to, 1, 0.8);
        for (const p of playersNear(boss.dim, from, 16)) shake(p, 0.3, 0.6);
      }
      return age < 34;
    }, { hold: true });
  },
};

function ringOfBlocks(b: Boss, center: Vector3, r: number, height: number, type: string, ticks: number): number {
  let n = 0;
  const c = { x: Math.floor(center.x), y: Math.floor(center.y), z: Math.floor(center.z) };
  for (let dx = -r; dx <= r; dx++) {
    for (let dz = -r; dz <= r; dz++) {
      const d = Math.hypot(dx, dz);
      if (d < r - 0.5 || d > r + 0.5) continue;
      for (let h = 0; h < height; h++) if (placeTemp(b.dim, { x: c.x + dx, y: c.y + h, z: c.z + dz }, type, ticks, "air")) n++;
    }
  }
  return n;
}

const prison: Move = {
  id: "blueprint_prison",
  name: "Blueprint Prison",
  cooldown: 380,
  score: ({ distance, boss }) => (distance < 28 ? 12 + (boss.losLost > 40 ? 10 : 0) : 0),
  start: ({ boss, target }) => {
    let at = target.location;
    return act("Blueprint Prison", S.Channel, (age) => {
      if (age === 0) {
        at = ground(boss, target.location);
        sigil(boss.dim, up(at, 0.1), 8, 1.2);
        sound(boss.dim, "block.end_portal_frame.fill", at, 1.5, 0.6);
      }
      if (age < 22) {
        if (age % 3 === 0) moteRing(boss.dim, "blue", up(at, 0.3 + age * 0.12), 3, 18, age);
        return true;
      }
      if (age === 22) {
        const n = ringOfBlocks(boss, at, 3, 3, PRISON_BLOCK, 120);
        sound(boss.dim, "random.anvil_use", at, 1.5, 0.8);
        if (n) boss.say("Every work of mine begins with a frame.");
      }
      if (age === 34 || age === 42 || age === 50) {
        column(boss.dim, "orange", at);
        embers(boss.dim, up(at, 1));
        for (const e of victimsNear(boss.dim, at, 2.7)) {
          hurt(e, 4, boss.entity);
          e.setOnFire(2, true);
        }
      }
      return age < 54;
    });
  },
};

const pillars: Move = {
  id: "pillars_of_creation",
  name: "Pillars of Creation",
  cooldown: 240,
  score: ({ boss, target }) => 12 + crowd(boss, target.location, 8) * 4,
  start: ({ boss }) => {
    const spots = playersNear(boss.dim, boss.entity.location, 26).slice(0, 4).map((p) => ground(boss, predict(p, 16)));
    for (let k = spots.length; k < 5; k++) spots.push(ground(boss, add(boss.entity.location, v(Math.random() * 18 - 9, 0, Math.random() * 18 - 9))));
    return act("Pillars of Creation", S.AtkB, (age) => {
      if (age === 0) for (const s of spots) danger(boss.dim, s, 3, 1.0);
      if (age === 20) {
        for (const s of spots) {
          for (let h = 0; h < 4; h++) placeTemp(boss.dim, { x: s.x, y: s.y + h, z: s.z }, PILLAR_BLOCK, 100, "air");
          debris(boss.dim, up(s, 1));
          column(boss.dim, "orange", s);
          for (const e of victimsNear(boss.dim, s, 1.7)) {
            hurt(e, 6, boss.entity);
            try {
              e.applyKnockback({ x: 0.001, z: 0.001 }, 1.4);
            } catch {
              // ignore
            }
          }
        }
        sound(boss.dim, "random.explode", boss.entity.location, 1, 1.4);
      }
      return age < 26;
    });
  },
};

const rivets: Move = {
  id: "molten_rivets",
  name: "Molten Rivets",
  cooldown: 160,
  score: ({ distance }) => (distance > 7 ? 15 : 4),
  start: ({ boss, target }) =>
    act("Molten Rivets", S.AtkC, (age) => {
      if (age % 5 === 0 && age < 30) {
        const from = up(boss.entity.location, 6.5);
        const p = playersNear(boss.dim, boss.entity.location, 30);
        const victim = (p[Math.floor(Math.random() * p.length)] as Player | undefined) ?? target;
        const to = ground(boss, add(predict(victim, 20), v(Math.random() * 3 - 1.5, 0, Math.random() * 3 - 1.5)));
        danger(boss.dim, to, 4, 1.0);
        sound(boss.dim, "mob.blaze.shoot", from, 1, 0.6);
        addTask("rivet", arc(boss, from, up(to, 0.5), 20, "orange", 6, (at) => {
          embers(boss.dim, at);
          groundWave(boss.dim, "orange", at);
          for (const e of victimsNear(boss.dim, at, 2.2)) {
            hurt(e, 5, boss.entity.isValid ? boss.entity : undefined);
            e.setOnFire(2, true);
          }
          sound(boss.dim, "random.explode", at, 0.6, 1.6);
        }));
      }
      return age < 34;
    }),
};

const sweep: Move = {
  id: "gear_sweep",
  name: "Gear Halo Sweep",
  cooldown: 120,
  score: ({ boss }) => (playersNear(boss.dim, boss.entity.location, 7).length ? 24 : 0),
  start: ({ boss }) =>
    act("Gear Halo Sweep", S.AtkD, (age) => {
      const at = ground(boss, boss.entity.location);
      if (age < 12) {
        if (age % 3 === 0) moteRing(boss.dim, "gold", up(at, 2), 7, 28, age * 0.4);
        return true;
      }
      if (age === 12) {
        ringWave(boss.dim, "orange", up(at, 0.3), 8, 0.4);
        groundWave(boss.dim, "gold", up(at, 0.3));
        sound(boss.dim, "item.trident.riptide_3", at, 1.5, 0.5);
        for (const e of victimsNear(boss.dim, at, 8)) {
          hurt(e, 9, boss.entity);
          knock(e, at, 2.0, 0.5);
        }
      }
      return age < 18;
    }, { hold: true }),
};

/** ULTIMATE: Prime Mover - real cover pillars and a sweeping beam of creation. */
const primeMover: Move = {
  id: "prime_mover",
  name: "Prime Mover",
  cooldown: 900,
  score: () => 0,
  start: ({ boss }) => {
    const center = ground(boss, boss.entity.location);
    const hits = new Map<string, number>();
    return act("Prime Mover", S.Ultimate, (age) => {
      const dim = boss.dim;
      const eye = boss.eye;
      if (age === 0) {
        for (const p of playersNear(dim, center, 48)) {
          title(p, "§6§lPRIME MOVER", "§7hide behind what it builds", 80);
          fade(p, [0.35, 0.18, 0.02], 0.3, 0.4, 0.8);
          shake(p, 0.2, 2);
        }
        sound(dim, "block.end_portal.spawn", center, 2, 0.6);
      }
      // build four cover walls (3 wide x 6 tall) on the diagonals
      if (age >= 4 && age < 28 && age % 4 === 0) {
        const layer = (age - 4) / 4;
        for (let k = 0; k < 4; k++) {
          const a = Math.PI / 4 + (k * Math.PI) / 2;
          const c = { x: center.x + Math.cos(a) * 9, y: center.y + layer, z: center.z + Math.sin(a) * 9 };
          const tx = -Math.sin(a);
          const tz = Math.cos(a);
          for (let w = -1; w <= 1; w++) placeTemp(dim, { x: c.x + tx * w, y: c.y, z: c.z + tz * w }, COVER_BLOCK, 260 - age, "air");
          mote(dim, "blue", up(c, 0.5));
          debris(dim, c);
        }
        sound(dim, "random.anvil_use", center, 1, 0.6 + layer * 0.1);
      }
      if (age >= 30 && age < 60) {
        if (age % 3 === 0) moteRing(dim, "white", eye, 3 - (age - 30) * 0.08, 16, age);
        if (age === 30) sound(dim, "mob.warden.sonic_charge", center, 2, 0.7);
        return true;
      }
      if (age >= 60 && age < 200) {
        const ang = ((age - 60) / 140) * Math.PI * 4;
        const dir = { x: Math.cos(ang), y: 0, z: Math.sin(ang) };
        const tip = add(eye, v(dir.x * 26, -3, dir.z * 26));
        if (age % 2 === 0) beam(dim, age % 4 ? "white" : "blue", eye, tip, 0.7);
        for (const p of playersNear(dim, center, 27)) {
          const bear = Math.atan2(p.location.z - center.z, p.location.x - center.x);
          let diff = Math.abs(((bear - ang) % (2 * Math.PI) + 3 * Math.PI) % (2 * Math.PI) - Math.PI);
          diff = Math.abs(diff);
          if (diff > 0.16) continue;
          const last = hits.get(p.id) ?? -100;
          if (age - last < 10) continue;
          if (!lineOfSight(dim, eye, chest(p))) {
            mote(dim, "gold", up(p.location, 2.3));
            continue; // sheltered behind real blocks
          }
          hits.set(p.id, age);
          hurt(p, 7, boss.entity, EntityDamageCause.magic);
          p.setOnFire(3, true);
          burst(dim, "white", chest(p));
        }
        if (age % 20 === 0) sound(dim, "beacon.ambient", center, 2, 1.6);
        return true;
      }
      if (age === 200) {
        flash(dim, eye);
        groundWave(dim, "orange", up(center, 0.2));
        exhaust(boss, 90);
      }
      return age < 206;
    }, { hold: true });
  },
};

export const TITAN: BossDef = {
  typeId: "fb:titan",
  key: "titan",
  name: "The Titan of Creation",
  epithet: "the Walking World-Forge",
  color: "§6",
  hue: "orange",
  fade: [0.4, 0.2, 0.02],
  speed: 0.11,
  mode: "walk",
  eyeHeight: 5.6,
  spawnTicks: 80,
  loot: "fb:forge_heart",
  hover(b, target) {
    if (!target) return b.home;
    const d = dist(b.entity.location, target.location);
    if (d < 7) return b.entity.location;
    const dir = flatDir(b.entity.location, target.location);
    return add(b.entity.location, v(dir.x * 2, 0, dir.z * 2));
  },
  moves: [hammer, prison, pillars, rivets, sweep],
  ultimate: primeMover,
  ambient(b, t) {
    if (t % 6 === 0) {
      for (const x of [-0.56, 0, 0.56]) smoke(b.dim, "ash", add(b.entity.location, rotY(v(x, 5.7, 0.75), 0)));
    }
    if (t % 10 === 0) embers(b.dim, add(b.entity.location, v(0, 3.6, -0.8)));
  },
  deathFx(b, age) {
    if (age % 6 === 0) debris(b.dim, add(b.entity.location, v(Math.random() * 4 - 2, Math.random() * 6, Math.random() * 4 - 2)));
    if (age % 15 === 0) groundWave(b.dim, "orange", up(b.groundBelow(b.entity.location), 0.2));
  },
  lines: {
    intro: ["I am the hand that assembled the mountains. You are an unfinished draft.", "Every world begins in a forge. This one ends in mine."],
    phase2: ["Damage is only a revision. I will rebuild."],
    phase3: ["Then I will build your tomb, and stand guard over it."],
    ultimate: ["Behold the Prime Mover - the first light that shaped the world!"],
    kill: ["{name} has been melted down for parts.", "Scrap. Reforged later, perhaps."],
    taunt: ["{name}, that {weapon} was forged in a lesser fire.", "Your blueprint is flawed, {name}."],
    death: ["The forge... grows... cold..."],
  },
};
