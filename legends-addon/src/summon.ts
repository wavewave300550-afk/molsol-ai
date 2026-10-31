/**
 * Summoning rituals: using a sigil starts a short, wordless ritual at the spot
 * the player is looking at (≤ 10 blocks), then the boss makes its entrance.
 */
import { Difficulty, Dimension, Entity, ItemStack, Player, Vector3, system, world, GameMode } from "@minecraft/server";
import { BossKey } from "./bosses/boss.js";
import { activeBoss, controlBoss } from "./bosses/registry.js";
import { burst, C, deco, glint, pillar, shake, shock, sound, spiralMark } from "./core/fx.js";
import { propAct, removeProp, spawnProp } from "./core/hazards.js";
import { notify, Pri } from "./core/notice.js";
import { addTask } from "./core/tasks.js";
import { groundY } from "./core/terrain.js";
import { add, dirOfYaw, scale } from "./core/vec.js";

export const SIGILS: Record<string, BossKey> = {
  "legends:sigil_taotie": "taotie",
  "legends:sigil_nidhogg": "nidhogg",
  "legends:sigil_hanuman": "hanuman",
  "legends:sigil_alicorn": "alicorn",
  "legends:sigil_tenko": "tenko",
  "legends:sigil_logos": "logos",
};

const rituals = new Set<string>();

function ritualSpot(p: Player): Vector3 {
  try {
    const hit = p.getBlockFromViewDirection({ maxDistance: 10 });
    if (hit) {
      const b = hit.block.location;
      return { x: b.x + 0.5, y: b.y + 1, z: b.z + 0.5 };
    }
  } catch {
    // fall back below
  }
  const d = p.getViewDirection();
  const at = { x: p.location.x + d.x * 7, y: p.location.y, z: p.location.z + d.z * 7 };
  return { x: at.x, y: groundY(p.dimension, at.x, at.z, at.y), z: at.z };
}

function consume(p: Player, itemId: string): void {
  if (p.getGameMode() === GameMode.Creative) return;
  try {
    const inv = p.getComponent("minecraft:inventory")?.container;
    if (!inv) return;
    const slot = p.selectedSlotIndex;
    const it = inv.getItem(slot);
    if (it && it.typeId === itemId) {
      if (it.amount > 1) {
        it.amount -= 1;
        inv.setItem(slot, it);
      } else inv.setItem(slot, undefined);
    }
  } catch {
    // ignore
  }
}

export function useSigil(p: Player, itemId: string): void {
  const key = SIGILS[itemId];
  if (!key) return;
  let diff = Difficulty.Normal;
  try {
    diff = world.getDifficulty();
  } catch {
    // ignore
  }
  if (diff === Difficulty.Peaceful) {
    notify([p], "§7Legends do not answer in Peaceful", Pri.Info);
    return;
  }
  if (activeBoss(key) || rituals.has(key)) {
    notify([p], "§7This legend is already present", Pri.Info);
    return;
  }
  consume(p, itemId);
  startRitual(p.dimension, ritualSpot(p), key, p);
}

/** Spawn a boss right away with its entrance (commands / tests). */
export function summonNow(dim: Dimension, at: Vector3, key: BossKey, yaw = 0): Entity | undefined {
  try {
    const e = dim.spawnEntity(`legends:${key}`, at);
    try {
      e.setRotation({ x: 0, y: yaw });
    } catch {
      // ignore
    }
    controlBoss(e, false);
    return e;
  } catch (err) {
    console.warn(`[legends] summon ${key} failed: ${err}`);
    return undefined;
  }
}

export function startRitual(dim: Dimension, at: Vector3, key: BossKey, by?: Player): void {
  rituals.add(key);
  const yaw = by ? by.getRotation().y + 180 : 0;
  const duration = 100;
  let ding: Entity | undefined;
  if (key === "taotie") ding = spawnProp(dim, "ding", at, 0);
  sound(dim, "block.end_portal.spawn", at, 2, 0.5);
  addTask(`ritual-${key}`, (age) => {
    const f = age / duration;
    switch (key) {
      case "taotie":
        if (age === 10) propAct(ding, 1);
        if (age % 6 === 0) deco(dim, "smoke", add(at, { x: 0, y: 2, z: 0 }), C.hunger, 4, 1.2, 0.6, 0.8);
        if (age % 20 === 0) sound(dim, "mob.ravager.ambient", at, 2, 0.5);
        break;
      case "nidhogg":
        if (age % 4 === 0) spiralMark(dim, at, C.venom, 2 + f * 6, 6);
        if (age % 10 === 0) deco(dim, "shard", at, C.root, 6, 3 * f + 1, 0.3, 3);
        if (age % 25 === 0) sound(dim, "mob.warden.dig", at, 3, 0.6);
        break;
      case "hanuman":
        if (age % 3 === 0) for (let i = 0; i < 3; i++) deco(dim, "feather", add(at, add(scale(dirOfYaw(age * 12 + i * 120), 3 - f * 2), { x: 0, y: age * 0.08, z: 0 })), C.wind, 1, 0.2, 0.3, 0.4);
        if (age % 20 === 0) sound(dim, "mob.breeze.whirl", at, 3, 0.7);
        break;
      case "alicorn":
        if (age % 10 === 0) pillar(dim, at, 20, 1 + f * 2, 12, [C.pink, C.aurora, C.sky][Math.floor(age / 10) % 3]);
        if (age % 25 === 0) sound(dim, "chime.amethyst_block", at, 3, 0.8 + f);
        break;
      case "tenko":
        if (age % 4 === 0) for (let i = 0; i < 10; i++) if (i < 1 + Math.floor(f * 10)) deco(dim, "flame", add(at, scale(dirOfYaw(i * 36), 4)), C.fox, 1, 0.1, 0.45, 0.5);
        if (age % 10 === 0) sound(dim, "note.bell", at, 2, 0.5 + f);
        break;
      case "logos":
        if (age % 8 === 0) deco(dim, "rune", at, C.holy, 6, 3, 0.4, 1.2);
        if (age % 20 === 0) pillar(dim, at, 40, 1 + f * 3, 20, C.holy);
        if (age % 30 === 0) sound(dim, "beacon.power", at, 3, 0.5 + f);
        break;
    }
    if (age === duration - 20) shake(dim.getPlayers({ location: at, maxDistance: 40 }), 0.3, 1.0);
    if (age < duration) return true;
    removeProp(ding);
    burst(dim, add(at, { x: 0, y: 1, z: 0 }), C.gold, 30, 6, 0.4, 1);
    shock(dim, at, 10, 10, C.gold);
    glint(dim, add(at, { x: 0, y: 2, z: 0 }), C.white, 3);
    rituals.delete(key);
    summonNow(dim, at, key, yaw);
    return false;
  });
}

export function giveItem(p: Player, id: string, n = 1): void {
  try {
    const inv = p.getComponent("minecraft:inventory")?.container;
    const left = inv?.addItem(new ItemStack(id, n));
    if (left) p.dimension.spawnItem(left, p.location);
  } catch {
    system.run(() => {
      try {
        p.dimension.spawnItem(new ItemStack(id, n), p.location);
      } catch {
        // ignore
      }
    });
  }
}
