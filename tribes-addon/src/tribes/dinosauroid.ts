import { alliesNear, enemiesNear, hurt, knockFrom } from "../core/combat.js";
import { burst, center, flare, mote, privateParticle, ring, sound } from "../core/fx.js";
import { isDaylight } from "../core/env.js";
import { now, Race } from "../core/state.js";
import { addTask } from "../core/tasks.js";
import { add, v } from "../core/vec.js";
import { spawnSummon } from "../summons.js";
import { Tribe } from "./types.js";

export const dinosauroid: Tribe = {
  race: Race.Dinosauroid,
  key: "dinosauroid",
  name: "Dinosauroid",
  epithet: "Heirs of the Cretaceous",
  color: "§a",
  energyName: "Primal Fury",
  regen: 1.5,
  relic: "tribes:primal_fang",
  icon: "textures/items/tribes/primal_fang",
  lore:
    "Sixty-six million years ago a clever line of troodonts survived the impact in deep caves and kept evolving: " +
    "upright, big-brained, scaled reptilian people with slit pupils and a balancing tail. They are ambush hunters " +
    "who fight with claws, leaps and a terrifying roar, and their Fury grows with every blow they land.",
  passiveText: [
    "Predator's Stride - permanent Speed I and Jump Boost I",
    "Scaled Hide - permanent Resistance I",
    "Sun-Basking - Strength I while standing in daylight (cold-blooded)",
    "Carnivore - raw meat heals (Regeneration II), never causes Hunger and restores Fury",
    "Predator Senses - you see a green scent trail above nearby monsters",
    "Fury: +1.5/s, +4 per melee hit, +12 per kill",
  ],
  passiveEffects: [
    { effect: "speed", amplifier: 0 },
    { effect: "jump_boost", amplifier: 0 },
    { effect: "resistance", amplifier: 0 },
  ],
  hitGain: 4,
  killGain: 12,
  slowPassive(player) {
    if (isDaylight(player)) player.addEffect("strength", 60, { amplifier: 0, showParticles: false });
    // Predator senses: private scent particles above monsters within 24 blocks.
    for (const e of player.dimension.getEntities({ location: player.location, maxDistance: 24, families: ["monster"] })) {
      privateParticle(player, "tribes:green_mote", add(e.location, v(0, 2.3, 0)));
      privateParticle(player, "tribes:green_mote", add(e.location, v(0, 2.6, 0)));
    }
  },
  abilities: [
    {
      id: "pounce",
      name: "Raptor Pounce",
      short: "Pounce",
      cost: 20,
      cooldown: 60,
      description: "Leap far in the direction you look. Landing sends out a shockwave: 7 damage and knockback in 3.5 blocks. No fall damage.",
      cast({ player, state, dim, tick }) {
        const d = player.getViewDirection();
        const l = Math.hypot(d.x, d.z) || 1;
        player.applyKnockback({ x: (d.x / l) * 2.4, z: (d.z / l) * 2.4 }, 0.8);
        state.fallImmuneUntil = tick + 80;
        burst(dim, "green", player.location);
        sound(dim, "mob.ravager.stun", player.location, 0.8, 1.6);
        addTask("pounce", (age) => {
          if (!player.isValid) return false;
          mote(player.dimension, "green", add(player.location, v(0, 0.6, 0)));
          if (age > 4 && player.isOnGround) {
            const at = player.location;
            ring(player.dimension, "green", add(at, v(0, 0.2, 0)), 1.5);
            ring(player.dimension, "green", add(at, v(0, 0.2, 0)), 3.0);
            burst(player.dimension, "green", at);
            sound(player.dimension, "mob.zombie.woodbreak", at, 0.8, 0.7);
            for (const e of enemiesNear(player.dimension, at, 3.5, player)) {
              hurt(e, 7, player);
              knockFrom(e, at, 1.1, 0.45);
            }
            state.fallImmuneUntil = now() + 5;
            return false;
          }
          return age < 60;
        });
        return true;
      },
    },
    {
      id: "roar",
      name: "Primal Roar",
      short: "Roar",
      cost: 30,
      cooldown: 240,
      description: "Enemies in 10 blocks are knocked back, weakened and slowed. Allies (and you) gain Strength I and Speed II for 10s.",
      cast({ player, dim }) {
        const at = player.location;
        sound(dim, "mob.ravager.roar", at, 1.2, 1.15);
        for (let i = 1; i <= 5; i++) {
          addTask("roar-ring", (age) => {
            if (age < i * 2) return true;
            ring(dim, "green", add(at, v(0, 1, 0)), i * 2, 10 + i * 8);
            return false;
          });
        }
        for (const e of enemiesNear(dim, at, 10, player)) {
          knockFrom(e, at, 1.6, 0.35);
          e.addEffect("weakness", 160, { amplifier: 0 });
          e.addEffect("slowness", 80, { amplifier: 1 });
        }
        for (const p of alliesNear(dim, at, 10, player)) {
          p.addEffect("strength", 200, { amplifier: 0 });
          p.addEffect("speed", 200, { amplifier: 1 });
          flare(dim, "green", center(p));
        }
        return true;
      },
    },
    {
      id: "tail_sweep",
      name: "Tail Sweep",
      short: "Sweep",
      cost: 15,
      cooldown: 80,
      description: "Spin and lash with your tail: 6 damage to everything within 4 blocks and a strong knockback.",
      cast({ player, dim }) {
        const at = player.location;
        sound(dim, "mob.enderdragon.flap", at, 1, 1.4);
        addTask("sweep", (age) => {
          const a0 = age * 1.2;
          for (let k = 0; k < 10; k++) {
            const a = a0 + (k / 10) * 1.3;
            mote(dim, "green", add(at, v(Math.cos(a) * 3.5, 0.6, Math.sin(a) * 3.5)));
            mote(dim, "white", add(at, v(Math.cos(a) * 2.5, 0.6, Math.sin(a) * 2.5)));
          }
          return age < 5;
        });
        for (const e of enemiesNear(dim, at, 4, player)) {
          hurt(e, 6, player);
          knockFrom(e, at, 1.5, 0.4);
        }
        return true;
      },
    },
    {
      id: "pack_call",
      name: "Call of the Pack",
      short: "Pack",
      cost: 100,
      cooldown: 1200,
      ultimate: true,
      description: "ULTIMATE - Three loyal Pack Raptors answer your call for 40s. They hunt monsters and attack whatever you attack.",
      cast({ player, dim }) {
        const yaw = (player.getRotation().y * Math.PI) / 180;
        for (let i = 0; i < 3; i++) {
          const a = yaw + Math.PI / 2 + (i - 1) * 0.9;
          const at = add(player.location, v(-Math.sin(a) * 2.2, 0.1, Math.cos(a) * 2.2));
          spawnSummon(player, "raptor", at, 800, i);
        }
        sound(dim, "mob.ravager.roar", player.location, 1.4, 1.5);
        player.onScreenDisplay.setTitle("§aCALL OF THE PACK", { subtitle: "§2The raptors hunt with you", fadeInDuration: 5, stayDuration: 40, fadeOutDuration: 10 });
        return true;
      },
    },
  ],
};
