import { Dimension, EntityInventoryComponent, GameMode, ItemStack, Player, system } from "@minecraft/server";
import { COLORS, ITEM_BANNER, ITEM_HEART, ITEM_STANDARD, JOAN } from "./config.js";
import { actionbar, emit, sound } from "./core/fx.js";
import { allPlayersNear } from "./core/targets.js";
import { add, dirOfYaw, flatDir, scale, v, V3 } from "./core/vec.js";
import { PathField } from "./paths/field.js";
import { circle, conform, line, spiral } from "./paths/shapes.js";
import type { JoanBoss } from "./boss/joan.js";

// =========================================================================== loot
export function dropRewards(b: JoanBoss): void {
  const at = add(b.pos, v(0, 0.6, 0));
  const dim = b.dim;
  const nearby = allPlayersNear(dim, b.home, 64);
  const earned = nearby.filter((p) => b.participants.has(p.id));
  const winners = earned.length ? earned : nearby;
  const spawn = (id: string, n: number) => {
    try {
      dim.spawnItem(new ItemStack(id, n), at);
    } catch {
      // unloaded
    }
  };
  for (let i = 0; i < Math.max(1, Math.min(4, winners.length)); i++) spawn(ITEM_BANNER, 1);
  if (b.flags.martyrEcho) spawn(ITEM_HEART, 1);
  spawn("minecraft:gold_ingot", 12);
  spawn("minecraft:diamond", 3);
  spawn("minecraft:lapis_lazuli", 16);
  spawn("minecraft:golden_apple", 2);
  for (let i = 0; i < 10; i++) {
    try {
      dim.spawnEntity("minecraft:xp_orb", add(at, v((Math.random() - 0.5) * 2, 0.5, (Math.random() - 0.5) * 2)));
    } catch {
      // ignore
    }
  }
  for (const p of winners) {
    try {
      p.addExperience(320);
    } catch {
      // ignore
    }
    p.sendMessage("§6Joan of Arc rests. §fThe §eBanner of Divine Paths §fnow answers to you.");
    if (b.flags.martyrEcho) p.sendMessage("§7Her heart did not burn. §cThe Unburnt Heart §7remains in the ashes.");
  }
}

// =========================================================================== relics (player roads)
const playerFields = new Map<string, PathField>();
const lastUse = new Map<string, number>();

function fieldOf(p: Player): PathField {
  let f = playerFields.get(p.id);
  if (!f || f.dim.id !== p.dimension.id) {
    f = new PathField(p.dimension, p.id, true);
    playerFields.set(p.id, f);
  }
  return f;
}

export function tickPlayerFields(now: number): void {
  for (const [id, f] of playerFields) {
    f.tick(now);
    if (!f.livePaths().length && !f.scars.length) playerFields.delete(id);
  }
}

/**
 * Banner of Divine Paths (reward):
 *   use          - write a Pilgrim Road ahead: it carries you and your allies
 *                  forward and sweeps hostile projectiles along with it
 *   sneak + use  - Heaven's Detour sanctuary: an orbit around you for 6 s that
 *                  swings hostile projectiles and mobs around and throws them out
 */
export function useBanner(p: Player, now: number): void {
  const sneaking = p.isSneaking;
  const key = `${p.id}:${sneaking ? "orbit" : "road"}`;
  const cd = sneaking ? 300 : 80;
  const last = lastUse.get(key) ?? -99999;
  if (now - last < cd) {
    actionbar(p, `§7The banner rests... §f${Math.ceil((cd - (now - last)) / 20)}s`);
    return;
  }
  lastUse.set(key, now);
  const f = fieldOf(p);
  const feet = { ...p.location };
  if (!sneaking) {
    const dir = dirOfYaw(p.getRotation().y);
    const pts = conform(p.dimension, line(add(feet, scale(dir, 0.5)), add(feet, scale(dir, 13))), feet.y);
    f.add(pts, { kind: "player", owner: p.id, ownerIsPlayer: true, speed: 0.55, radius: 1.0, band: [-0.8, 1.0], form: 4,
      life: 70, carryPlayers: true, carryMobs: false, carryProjectiles: true, memory: false, fling: 1.2 }, now);
    try {
      p.startItemCooldown("joan:road", cd);
    } catch {
      // ignore
    }
    sound(p.dimension, "joan.banner.swing", feet, 1, 1.2);
  } else {
    const c = add(feet, v(0, 1.1, 0));
    f.add(circle(c, 2.4, 0, 1, true), { kind: "orbit", owner: p.id, ownerIsPlayer: true, loop: true, aerial: true,
      speed: 0.6, radius: 1.2, form: 4, life: 120, carryPlayers: false, carryMobs: true, carryProjectiles: true,
      memory: false, maxRide: 12, fling: 1.6, aim: (e) => add(e.location, scale(flatDir(c, e.location), 6)) }, now);
    sound(p.dimension, "joan.choir.light", feet, 0.6, 1.4);
  }
}

// =========================================================================== summoning
export function joanNear(dim: Dimension, at: V3, radius: number): boolean {
  try {
    return dim.getEntities({ type: JOAN, location: at, maxDistance: radius }).length > 0;
  } catch {
    return false;
  }
}

/** Pilgrim's Standard / Unburnt Heart: write a spiral of light, then Joan descends upon it. */
export function useSummonItem(p: Player, itemId: string, now: number): void {
  const dim = p.dimension;
  const dir = dirOfYaw(p.getRotation().y);
  const at = add(p.location, scale(dir, 6));
  if (joanNear(dim, at, 96)) {
    p.sendMessage("§7Joan of Arc is already on the field.");
    return;
  }
  if (!consume(p, itemId)) return;
  const f = fieldOf(p);
  f.add(conform(dim, spiral(at, 5, 0.6, 0, 1.6, true), at.y), { kind: "procession", owner: p.id, ownerIsPlayer: true,
    speed: 0.25, radius: 0.6, form: 36, life: 20, carryPlayers: false, carryMobs: false, carryProjectiles: false,
    memory: false, color: COLORS.roadGold }, now);
  sound(dim, "joan.bell.toll", at, 1, 1);
  for (const q of allPlayersNear(dim, at, 48)) q.sendMessage("§6A road of light is being written... §fJoan of Arc answers the call.");
  system.runTimeout(() => {
    try {
      emit(dim, "joan:pillar", at, { h: 18, color: COLORS.roadGold, life: 1.2, size: 0.8 });
      dim.spawnEntity(JOAN, at);
    } catch (err) {
      console.warn(`[joan] summon failed: ${err}`);
    }
  }, 50);
}

function consume(p: Player, itemId: string): boolean {
  try {
    if (p.getGameMode() === GameMode.Creative) return true;
    const inv = p.getComponent(EntityInventoryComponent.componentId);
    const c = inv?.container;
    if (!c) return false;
    const slot = p.selectedSlotIndex;
    const it = c.getItem(slot);
    if (!it || it.typeId !== itemId) return false;
    if (it.amount > 1) {
      it.amount -= 1;
      c.setItem(slot, it);
    } else c.setItem(slot, undefined);
    return true;
  } catch {
    return false;
  }
}

export const SUMMON_ITEMS = new Set([ITEM_STANDARD, ITEM_HEART]);
