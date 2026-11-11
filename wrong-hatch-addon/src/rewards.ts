/**
 * Boss rewards and the summoning ritual.
 *
 *  Suspicious Egg     - use on a block: 5 s hatching ritual, then the boss emerges
 *  Guillotine Pinion  - 9 damage feather-blade; 25 % "feather bleed" on hit;
 *                       sneak + use fires a fan of 5 feather darts (6 s cooldown)
 *  Golden Yolk        - food: Regeneration II, Absorption II, Fire Resistance
 *  Hatch Core         - use: hatch a loyal golden Wrong Chick companion (max 2)
 */
import { Entity, EntityTameableComponent, GameMode, ItemCooldownComponent, ItemStack, Player, Vector3, system, world } from "@minecraft/server";
import { BOSS_ID, CHICK_ID } from "./config.js";
import { hit } from "./util/combat.js";
import { particle, sound } from "./util/fx.js";
import { add, norm, rotY, v3 } from "./util/vec.js";
import { addHazard, Dart } from "./boss/hazards.js";

interface Ritual {
  at: Vector3;
  dimId: string;
  t: number;
}
const rituals: Ritual[] = [];

function consume(p: Player, typeId: string): boolean {
  if (p.getGameMode() === GameMode.Creative) return true;
  try {
    const inv = p.getComponent("minecraft:inventory");
    const cont = inv?.container;
    if (!cont) return false;
    const slot = p.selectedSlotIndex;
    const it = cont.getItem(slot);
    if (!it || it.typeId !== typeId) return false;
    if (it.amount > 1) {
      it.amount -= 1;
      cont.setItem(slot, it);
    } else {
      cont.setItem(slot, undefined);
    }
    return true;
  } catch {
    return false;
  }
}

export function startRitual(p: Player, at: Vector3): void {
  const dim = p.dimension;
  const near = dim.getEntities({ type: BOSS_ID, location: at, maxDistance: 96 });
  if (near.length || rituals.some((r) => Math.abs(r.at.x - at.x) + Math.abs(r.at.z - at.z) < 32)) {
    p.onScreenDisplay.setActionBar("§cSomething in the area is already hatching...");
    return;
  }
  if (!consume(p, "wh:suspicious_egg")) return;
  rituals.push({ at, dimId: dim.id, t: 0 });
  sound(dim, "wrong_hatch.crack", at, 1.5, 0.6);
  p.onScreenDisplay.setActionBar("§6The egg twitches. Step back...");
}

export function tickRituals(): void {
  for (let i = rituals.length - 1; i >= 0; i--) {
    const r = rituals[i];
    r.t++;
    const dim = world.getDimension(r.dimId);
    const k = r.t / 100;
    if (r.t % 3 === 0) {
      const a = r.t * 0.4;
      particle(dim, "wh:gold_mote", add(r.at, v3(Math.sin(a) * (2.5 - k * 2), 0.3 + k * 3, Math.cos(a) * (2.5 - k * 2))));
    }
    if (r.t % 10 === 0) {
      particle(dim, "wh:shell_chip", add(r.at, v3(0, 0.5, 0)));
      sound(dim, "wrong_hatch.crack", r.at, 1 + k, 0.6 + k * 0.8);
    }
    if (r.t % 20 === 0) particle(dim, "wh:gold_ring", r.at, 1 + k * 3);
    if (r.t >= 100) {
      rituals.splice(i, 1);
      particle(dim, "wh:flash", add(r.at, v3(0, 1.5, 0)));
      particle(dim, "wh:shell_burst", add(r.at, v3(0, 1, 0)));
      try {
        dim.spawnEntity(BOSS_ID, r.at);
      } catch (e) {
        console.warn(`[wrong_hatch] ritual spawn failed: ${e}`);
      }
    }
  }
}

// --------------------------------------------------------------------------- items

const fanReady = new Map<string, number>();

export function onItemUse(p: Player, item: ItemStack): void {
  if (item.typeId === "wh:guillotine_pinion" && p.isSneaking) {
    const now = system.currentTick;
    if (now < (fanReady.get(p.id) ?? 0)) return;
    fanReady.set(p.id, now + 120);
    try {
      (item.getComponent("minecraft:cooldown") as ItemCooldownComponent | undefined)?.startCooldown(p);
    } catch {
      // ignore
    }
    const from = add(p.getHeadLocation(), v3(0, -0.2, 0));
    const look = norm(p.getViewDirection());
    for (let k = -2; k <= 2; k++) {
      const d = rotY(look, k * 8);
      const h = Math.sqrt(Math.max(0, 1 - look.y * look.y));
      addHazard(new Dart(p.id, p, p.dimension, from, v3(d.x * h, look.y, d.z * h), 1.6, 6, 1, false, 24));
    }
    sound(p.dimension, "wrong_hatch.wing_whoosh", from, 1, 1.6);
    return;
  }
  if (item.typeId === "wh:hatch_core") {
    const mine = p.dimension.getEntities({ type: CHICK_ID, location: p.location, maxDistance: 128, families: ["wrong_hatch_pet"] })
      .filter((e) => e.getDynamicProperty("wh:owner") === p.id);
    if (mine.length >= 2) {
      p.onScreenDisplay.setActionBar("§eYou already have two golden companions.");
      return;
    }
    if (!consume(p, "wh:hatch_core")) return;
    const at = add(p.location, v3(0, 0.2, 0));
    let chick: Entity | undefined;
    try {
      chick = p.dimension.spawnEntity(CHICK_ID, at);
      chick.triggerEvent("wh:become_friendly");
      chick.setDynamicProperty("wh:owner", p.id);
      chick.nameTag = `§6${p.name}'s Hatchling`;
    } catch {
      chick = undefined;
    }
    const c = chick;
    if (c) {
      system.runTimeout(() => {
        if (!c.isValid) return;
        try {
          (c.getComponent("minecraft:tameable") as EntityTameableComponent | undefined)?.tame(p);
        } catch {
          // ignore
        }
      }, 2);
    }
    particle(p.dimension, "wh:gold_burst", add(at, v3(0, 0.5, 0)));
    sound(p.dimension, "wrong_hatch.crack_big", at, 1, 1.5);
  }
}

export function onItemCompleteUse(p: Player, item: ItemStack): void {
  if (item.typeId !== "wh:golden_yolk") return;
  try {
    p.addEffect("regeneration", 160, { amplifier: 1 });
    p.addEffect("absorption", 1200, { amplifier: 1 });
    p.addEffect("fire_resistance", 600, { amplifier: 0 });
  } catch {
    // ignore
  }
  particle(p.dimension, "wh:heal", add(p.location, v3(0, 1, 0)));
}

export function onPlayerHit(p: Player, victim: Entity): void {
  try {
    const held = p.getComponent("minecraft:inventory")?.container?.getItem(p.selectedSlotIndex);
    if (!held || held.typeId !== "wh:guillotine_pinion") return;
  } catch {
    return;
  }
  if (Math.random() < 0.25 && victim.isValid) {
    system.run(() => {
      if (!victim.isValid) return;
      hit(p, victim, 3, 1, {});
      particle(victim.dimension, "wh:feather_burst", add(victim.location, v3(0, 1, 0)));
    });
  }
}
