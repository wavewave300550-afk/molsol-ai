import { EntityDamageCause, Vector3 } from "@minecraft/server";
import { aim, enemiesNear, hurt } from "../core/combat.js";
import { beam, burst, center, flare, mote, particle, sound, sphere, spiral } from "../core/fx.js";
import { isDaylight } from "../core/env.js";
import { Race } from "../core/state.js";
import { addTask, later } from "../core/tasks.js";
import { add, dist, flatDir, v } from "../core/vec.js";
import { spawnSummon } from "../summons.js";
import { Tribe } from "./types.js";

export const spacer: Tribe = {
  race: Race.Spacer,
  key: "spacer",
  name: "Spacer",
  epithet: "Wardens of the Outer Colonies",
  color: "§b",
  energyName: "Power Cells",
  regen: 2.0,
  relic: "tribes:omni_gauntlet",
  icon: "textures/items/tribes/omni_gauntlet",
  lore:
    "Descendants of the first interstellar colonists, raised in zero gravity and never seen without their sealed " +
    "exosuits, glowing visors and fusion jetpacks. Where other tribes trust instinct or gods, Spacers trust " +
    "engineering: plasma, gravity manipulation and autonomous drones powered by solar cells.",
  passiveText: [
    "Sealed Exosuit - permanent Night Vision and Water Breathing",
    "Servo Arms - permanent Haste I",
    "Inertial Dampers - fall damage halved",
    "Solar Cells - Power Cells regenerate 50% faster in daylight",
    "Power Cells: +2/s, +2 per melee hit",
  ],
  passiveEffects: [
    { effect: "night_vision", amplifier: 0 },
    { effect: "water_breathing", amplifier: 0 },
    { effect: "haste", amplifier: 0 },
  ],
  hitGain: 2,
  killGain: 5,
  regenMultiplier: (player) => (isDaylight(player) ? 1.5 : 1),
  abilities: [
    {
      id: "plasma_bolt",
      name: "Plasma Bolt",
      short: "Plasma",
      cost: 10,
      cooldown: 12,
      description: "Rapid-fire plasma beam (32 blocks) dealing 6 damage. Cheap and fast.",
      cast({ player, dim }) {
        const hit = aim(player, 32);
        const from = add(player.getHeadLocation(), v(0, -0.25, 0));
        beam(dim, "cyan", from, hit.point, 0.3);
        flare(dim, "cyan", hit.point);
        sound(dim, "mob.shulker.shoot", from, 0.8, 2);
        if (hit.entity) {
          hurt(hit.entity, 6, player);
          burst(dim, "cyan", hit.point);
        }
        return true;
      },
    },
    {
      id: "jetpack",
      name: "Jetpack Burst",
      short: "Jetpack",
      cost: 20,
      cooldown: 80,
      description: "Fire the fusion jetpack towards where you look, then drift down safely (Slow Falling 3s, no fall damage).",
      cast({ player, state, dim, tick }) {
        const d = player.getViewDirection();
        const l = Math.hypot(d.x, d.z) || 1;
        const h = 2.6 * Math.min(1, l + 0.2);
        player.applyKnockback({ x: (d.x / l) * h, z: (d.z / l) * h }, Math.max(0.55, d.y * 1.6 + 0.7));
        state.fallImmuneUntil = tick + 120;
        sound(dim, "firework.launch", player.location, 1, 0.8);
        addTask("jet-trail", (age) => {
          if (!player.isValid) return false;
          const p = add(player.location, v(0, 0.4, 0));
          mote(player.dimension, "cyan", p);
          mote(player.dimension, "orange", add(p, v((Math.random() - 0.5) * 0.4, -0.2, (Math.random() - 0.5) * 0.4)));
          if (age === 10) player.addEffect("slow_falling", 60, { amplifier: 0, showParticles: false });
          return age < 16;
        });
        return true;
      },
    },
    {
      id: "singularity",
      name: "Singularity Grenade",
      short: "Singularity",
      cost: 35,
      cooldown: 240,
      description: "Deploy a micro black hole where you look (24 blocks). It drags enemies within 7 blocks inwards for 4s, then implodes for 10 damage.",
      cast({ player, dim }) {
        const hit = aim(player, 24);
        const at: Vector3 = add(hit.point, v(0, 0.8, 0));
        sound(dim, "mob.endermen.portal", at, 1, 0.5);
        addTask("singularity", (age) => {
          spiral(dim, "purple", at, 2.2, age);
          if (age % 4 === 0) sphere(dim, "white", at, 0.35, 8);
          if (player.isValid && age % 2 === 0) {
            for (const e of enemiesNear(dim, at, 7, player)) {
              const d = flatDir(e.location, at);
              const k = Math.min(0.9, dist(e.location, at) * 0.18);
              try {
                e.applyKnockback({ x: d.x * k, z: d.z * k }, e.location.y < at.y - 0.5 ? 0.12 : 0.02);
              } catch {
                // ignore
              }
            }
          }
          if (age >= 80) {
            particle(dim, "minecraft:huge_explosion_emitter", at);
            burst(dim, "purple", at);
            burst(dim, "cyan", at);
            sound(dim, "random.explode", at, 1, 1.4);
            if (player.isValid) for (const e of enemiesNear(dim, at, 4.5, player)) hurt(e, 10, player, EntityDamageCause.magic);
            return false;
          }
          return true;
        });
        return true;
      },
    },
    {
      id: "drone_wing",
      name: "Orbital Drone Wing",
      short: "Drones",
      cost: 100,
      cooldown: 1200,
      ultimate: true,
      description: "ULTIMATE - Deploy two combat drones that orbit you for 40s and shoot plasma (5 damage) at the nearest enemy every second.",
      cast({ player, dim }) {
        for (let i = 0; i < 2; i++) {
          const at = add(player.location, v(i ? 1.5 : -1.5, 2.2, 0));
          spawnSummon(player, "drone", at, 800, i);
        }
        later(1, () => sphere(dim, "cyan", center(player), 1.6, 30));
        sound(dim, "beacon.power", player.location, 1, 1.5);
        player.onScreenDisplay.setTitle("§bDRONE WING ONLINE", { subtitle: "§3Targeting hostiles...", fadeInDuration: 5, stayDuration: 40, fadeOutDuration: 10 });
        return true;
      },
    },
  ],
};
