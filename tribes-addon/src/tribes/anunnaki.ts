import { EntityDamageCause } from "@minecraft/server";
import { aim, alliesNear, enemiesNear, heal, hurt } from "../core/combat.js";
import { beam, burst, center, column, flare, sound, sphere } from "../core/fx.js";
import { isDaylight } from "../core/env.js";
import { Race } from "../core/state.js";
import { addTask, later } from "../core/tasks.js";
import { add, dist, v } from "../core/vec.js";
import { spawnSummon } from "../summons.js";
import { Tribe } from "./types.js";

const NEGATIVE_EFFECTS = ["poison", "wither", "weakness", "slowness", "mining_fatigue", "blindness", "nausea", "hunger", "darkness", "levitation"];

export const anunnaki: Tribe = {
  race: Race.Anunnaki,
  key: "anunnaki",
  name: "Anunnaki",
  epithet: "Sky-Lords of Nibiru",
  color: "§6",
  energyName: "Divine Me",
  regen: 1.0,
  relic: "tribes:tablet_of_destinies",
  icon: "textures/items/tribes/tablet_of_destinies",
  lore:
    "Tall, golden-crowned sky-lords who descended from the wandering planet Nibiru. They wear the horned crown of " +
    "divinity, curled lapis beards and four feathered wings, and they rule through the 'Me' - divine decrees " +
    "carved into the Tablet of Destinies. Sunlight is their power source: their Divine Me flows fastest under open sky.",
  passiveText: [
    "Blood of Nibiru - +8 max health (Health Boost II)",
    "Solar Grace - heal 1 heart every 2s while in daylight",
    "Celestial Wings - hold JUMP while falling to glide (Slow Falling)",
    "Divine Aura - undead within 5 blocks are seared for 2 damage every 2s",
    "Divine Me: +1/s, x2.5 under open daylight sky",
  ],
  passiveEffects: [{ effect: "health_boost", amplifier: 1 }],
  hitGain: 2,
  killGain: 6,
  regenMultiplier: (player) => (isDaylight(player) ? 2.5 : 1),
  slowPassive(player) {
    if (isDaylight(player)) heal(player, 2);
    for (const e of player.dimension.getEntities({ location: player.location, maxDistance: 5, families: ["undead"] })) {
      hurt(e, 2, player, EntityDamageCause.magic);
      flare(player.dimension, "gold", center(e));
    }
  },
  fastPassive(player) {
    if (!player.isOnGround && player.isFalling && player.isJumping && !player.isGliding) {
      player.addEffect("slow_falling", 6, { amplifier: 0, showParticles: false });
    }
  },
  abilities: [
    {
      id: "solar_lance",
      name: "Solar Lance",
      short: "Lance",
      cost: 20,
      cooldown: 30,
      description: "A beam of concentrated sunlight (28 blocks): 9 damage and sets the target ablaze. Undead take 50% more.",
      cast({ player, dim }) {
        const hit = aim(player, 28);
        const from = add(player.getHeadLocation(), v(0, -0.2, 0));
        beam(dim, "gold", from, hit.point, 0.3);
        beam(dim, "white", from, hit.point, 0.9);
        flare(dim, "gold", hit.point);
        sound(dim, "mob.evocation_illager.cast_spell", from, 1, 1.6);
        if (hit.entity) {
          const undead = hit.entity.matches({ families: ["undead"] });
          hurt(hit.entity, undead ? 13.5 : 9, player);
          hit.entity.setOnFire(4, true);
          burst(dim, "gold", hit.point);
        }
        return true;
      },
    },
    {
      id: "edict",
      name: "Edict of Ascension",
      short: "Edict",
      cost: 35,
      cooldown: 200,
      description: "Decree that gravity no longer applies: enemies within 10 blocks float up for 2s, then are hurled down for 5 damage (+ fall damage).",
      cast({ player, dim }) {
        const foes = enemiesNear(dim, player.location, 10, player, 24);
        if (!foes.length) {
          player.sendMessage("§6[Tablet] §7No one is here to judge.");
          return false;
        }
        sound(dim, "beacon.activate", player.location, 1, 1.3);
        for (const e of foes) {
          try {
            e.addEffect("levitation", 40, { amplifier: 2, showParticles: false });
          } catch {
            // immune
          }
          column(dim, "gold", e.location, 3);
        }
        addTask("edict-glow", (age) => {
          for (const e of foes) if (e.isValid) sphere(dim, "gold", center(e), 0.8, 10);
          return age < 40;
        });
        later(42, () => {
          for (const e of foes) {
            if (!e.isValid) continue;
            try {
              e.removeEffect("levitation");
              e.applyKnockback({ x: 0, z: 0 }, -2.5);
            } catch {
              // ignore
            }
            hurt(e, 5, player.isValid ? player : undefined, EntityDamageCause.magic);
            burst(e.dimension, "gold", center(e));
          }
          sound(dim, "random.anvil_land", player.location, 0.6, 0.6);
        });
        return true;
      },
    },
    {
      id: "aegis",
      name: "Aegis of Anu",
      short: "Aegis",
      cost: 30,
      cooldown: 400,
      description: "A golden ward on you and allies within 8 blocks: Absorption II for 15s and Resistance II for 6s. Cleanses your negative effects.",
      cast({ player, dim }) {
        for (const id of NEGATIVE_EFFECTS) player.removeEffect(id);
        for (const p of alliesNear(dim, player.location, 8, player)) {
          p.addEffect("absorption", 300, { amplifier: 1 });
          p.addEffect("resistance", 120, { amplifier: 1 });
          sphere(dim, "gold", center(p), 1.3, 36);
        }
        sound(dim, "random.levelup", player.location, 0.8, 1.4);
        return true;
      },
    },
    {
      id: "descent",
      name: "Descent of Nibiru",
      short: "Descent",
      cost: 100,
      cooldown: 1200,
      ultimate: true,
      description: "ULTIMATE - A Lamassu, winged guardian of the gods, descends for 45s, and lightning judges up to 5 enemies within 18 blocks.",
      cast({ player, dim }) {
        const d = player.getViewDirection();
        const l = Math.hypot(d.x, d.z) || 1;
        const at = add(player.location, v((d.x / l) * 3, 0.1, (d.z / l) * 3));
        column(dim, "gold", at, 8);
        spawnSummon(player, "lamassu", at, 900);
        const foes = enemiesNear(dim, player.location, 18, player, 12).filter((e) => dist(e.location, player.location) > 4).slice(0, 5);
        foes.forEach((e, i) =>
          later(10 + i * 6, () => {
            if (!e.isValid) return;
            try {
              e.dimension.spawnEntity("minecraft:lightning_bolt", e.location);
            } catch {
              // ignore
            }
            hurt(e, 6, player.isValid ? player : undefined, EntityDamageCause.lightning);
          }),
        );
        sound(dim, "ambient.weather.thunder", player.location, 1, 1.2);
        player.onScreenDisplay.setTitle("§6THE GODS DESCEND", { subtitle: "§eA Lamassu answers the Tablet", fadeInDuration: 5, stayDuration: 40, fadeOutDuration: 10 });
        return true;
      },
    },
  ],
};
