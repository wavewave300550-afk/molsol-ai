import { Player, Vector3 } from "@minecraft/server";
import { aim, alliesNear, enemiesNear, heal, hurt } from "../core/combat.js";
import { burst, center, flare, mote, noodleLine, ring, sound } from "../core/fx.js";
import { PlayerState, Race } from "../core/state.js";
import { addTask, later } from "../core/tasks.js";
import { add, norm, scale, sub, v, yawRotate } from "../core/vec.js";
import { spawnSummon } from "../summons.js";
import { Tribe } from "./types.js";

export function meatballSplash(dim: Player["dimension"], at: Vector3, owner: Player | undefined): void {
  burst(dim, "sauce", at);
  burst(dim, "noodle", at);
  sound(dim, "mob.slime.big", at, 0.8, 0.8);
  if (!owner || !owner.isValid) return;
  for (const e of enemiesNear(dim, at, 2.5, owner)) {
    hurt(e, 4, owner);
    e.addEffect("slowness", 60, { amplifier: 0 });
  }
}

/** Holding JUMP in the air spends Holy Sauce to fly. */
function noodleFlight(player: Player, state: PlayerState): void {
  if (player.isOnGround || !player.isJumping || player.isGliding || state.energy < 1) return;
  player.addEffect("levitation", 4, { amplifier: 1, showParticles: false });
  state.energy = Math.max(0, state.energy - 0.5);
  if (Math.random() < 0.5) mote(player.dimension, "noodle", add(player.location, v(Math.random() - 0.5, 0.1, Math.random() - 0.5)));
}

export const pastafarian: Tribe = {
  race: Race.Pastafarian,
  key: "pastafarian",
  name: "Flying Spaghetti Monster",
  epithet: "Children of His Noodly Appendage",
  color: "§e",
  energyName: "Holy Sauce",
  regen: 1.2,
  relic: "tribes:holy_colander",
  icon: "textures/items/tribes/holy_colander",
  lore:
    "Touched by His Noodly Appendage, these Pastafarians wear the Holy Colander, sprout wriggling noodly tentacles " +
    "from their backs and stare out through meatball-crowned eye stalks. They float, they fly on faith and sauce, " +
    "they revere pirates, and they fight with lashing noodles and holy meatballs. R'Amen.",
  passiveText: [
    "Noodly Flight - hold JUMP in the air to fly upward (drains Holy Sauce)",
    "Al Dente Landing - immune to fall damage",
    "Pirate's Blessing - permanent Water Breathing",
    "Carb Loading - eating any food grants Absorption I (30s) and +20 Holy Sauce",
    "Holy Sauce: +1.2/s, +3 per melee hit",
  ],
  passiveEffects: [{ effect: "water_breathing", amplifier: 0 }],
  hitGain: 3,
  killGain: 6,
  fastPassive: noodleFlight,
  abilities: [
    {
      id: "noodly_lash",
      name: "Noodly Lash",
      short: "Lash",
      cost: 15,
      cooldown: 40,
      description: "A noodle snaps out (18 blocks), grabs the first enemy, deals 4 damage, slows it and yanks it to you.",
      cast({ player, dim, tick }) {
        const hit = aim(player, 18);
        const from = add(player.getHeadLocation(), v(0, -0.3, 0));
        noodleLine(dim, from, hit.point, tick * 0.5);
        sound(dim, "mob.slime.small", from, 1, 0.7);
        if (!hit.entity) return true;
        const e = hit.entity;
        const d = sub(player.location, e.location);
        const l = Math.hypot(d.x, d.z) || 1;
        const pull = Math.min(2.8, Math.max(0.8, l * 0.2));
        hurt(e, 4, player);
        try {
          e.applyKnockback({ x: (d.x / l) * pull, z: (d.z / l) * pull }, 0.45);
        } catch {
          // ignore
        }
        e.addEffect("slowness", 60, { amplifier: 1 });
        burst(dim, "noodle", hit.point);
        return true;
      },
    },
    {
      id: "meatball_barrage",
      name: "Meatball Barrage",
      short: "Meatballs",
      cost: 25,
      cooldown: 100,
      description: "Fire three holy meatballs. Each explodes in sauce: 4 impact + 4 splash damage and Slowness.",
      cast({ player }) {
        [-9, 0, 9].forEach((deg, i) =>
          later(i * 4, () => {
            if (!player.isValid) return;
            const dir = yawRotate(player.getViewDirection(), deg);
            const start = add(player.getHeadLocation(), scale(dir, 1.1));
            const ball = player.dimension.spawnEntity("tribes:meatball", start);
            const proj = ball.getComponent("minecraft:projectile");
            if (proj) {
              proj.owner = player;
              proj.shoot({ x: dir.x * 1.6, y: dir.y * 1.6 + 0.1, z: dir.z * 1.6 });
            }
            sound(player.dimension, "random.bow", start, 0.8, 0.6);
          }),
        );
        return true;
      },
    },
    {
      id: "marinara_flood",
      name: "Marinara Flood",
      short: "Marinara",
      cost: 30,
      cooldown: 280,
      description: "Flood the ground you look at (20 blocks) with holy marinara for 7s: enemies are slowed (III) and scalded, allies are healed.",
      cast({ player, dim }) {
        const hit = aim(player, 20);
        const centerAt = hit.distance < 20 ? hit.point : add(player.location, scale(norm({ ...player.getViewDirection(), y: 0 }), 8));
        const at: Vector3 = { x: centerAt.x, y: Math.floor(centerAt.y) + 0.15, z: centerAt.z };
        sound(dim, "bucket.empty_lava", at, 1, 0.7);
        addTask("marinara", (age) => {
          for (let i = 0; i < 8; i++) {
            const a = Math.random() * Math.PI * 2;
            const r = Math.sqrt(Math.random()) * 5;
            mote(dim, "sauce", add(at, v(Math.cos(a) * r, 0, Math.sin(a) * r)));
          }
          if (age % 10 === 0) {
            ring(dim, "sauce", at, 5, 30);
            if (!player.isValid) return age < 140;
            for (const e of enemiesNear(dim, at, 5, player)) {
              if (Math.abs(e.location.y - at.y) > 3) continue;
              e.addEffect("slowness", 30, { amplifier: 2 });
              hurt(e, 1.5, player);
            }
            if (age % 20 === 0) {
              for (const p of alliesNear(dim, at, 5, player)) {
                heal(p, 1);
                flare(dim, "noodle", center(p));
              }
            }
          }
          return age < 140;
        });
        return true;
      },
    },
    {
      id: "noodly_appendage",
      name: "Touched by His Noodly Appendage",
      short: "R'Amen",
      cost: 100,
      cooldown: 1500,
      ultimate: true,
      description: "ULTIMATE - The Flying Spaghetti Monster itself hovers over you for 30s, snatching up to two enemies every 1.5s (6 damage, lifted) and healing you.",
      cast({ player, dim }) {
        const at = add(player.location, v(0, 3.6, 0));
        spawnSummon(player, "noodle_avatar", at, 600);
        for (let i = 0; i < 4; i++) noodleLine(dim, at, add(player.location, v(Math.cos(i * 1.6) * 1.5, 0.2, Math.sin(i * 1.6) * 1.5)), i);
        sound(dim, "random.totem", player.location, 0.8, 1.3);
        player.onScreenDisplay.setTitle("§eR'AMEN!", { subtitle: "§6His Noodly Appendage is upon you", fadeInDuration: 5, stayDuration: 40, fadeOutDuration: 10 });
        return true;
      },
    },
  ],
};

export function carbLoading(player: Player, state: PlayerState): void {
  player.addEffect("absorption", 600, { amplifier: 0 });
  state.energy = Math.min(100, state.energy + 20);
  flare(player.dimension, "noodle", center(player));
}
