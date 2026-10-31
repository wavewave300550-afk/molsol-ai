import { EntityDamageCause, Player, system } from "@minecraft/server";
import { placeTemp } from "./core/blocks.js";
import { beam, burst, embers, shards, smoke, sound } from "./core/fx.js";
import { chest, healthOf, hurt, victimsNear, victimsOnLine } from "./core/targets.js";
import { add, scale, v } from "./core/vec.js";

/** Boss trophies: each grants a fragment of its boss's power. */
export const TROPHIES: Record<string, [string, number]> = {
  "fb:crown_of_absence": ["fb_crown", 600],
  "fb:forge_heart": ["fb_forge", 400],
  "fb:star_heart": ["fb_star", 100],
  "fb:parasite_seed": ["fb_seed", 600],
  "fb:shard_of_truth": ["fb_shard", 900],
};

const mirrorUntil = new Map<string, number>();

export const isTrophy = (id: string) => id in TROPHIES;

/** Shard of Truth: reflect half of incoming damage while active (called from the hurt before-event). */
export function reflecting(p: Player): boolean {
  return (mirrorUntil.get(p.id) ?? 0) > system.currentTick;
}

export function useTrophy(p: Player, id: string): void {
  const [cat, ticks] = TROPHIES[id];
  try {
    if (p.getItemCooldown(cat) > 0) return;
    p.startItemCooldown(cat, ticks);
  } catch {
    // cooldown API unavailable
  }
  const dim = p.dimension;
  const eye = p.getHeadLocation();
  const dir = p.getViewDirection();
  if (id === "fb:crown_of_absence") {
    smoke(dim, "void", chest(p));
    let d = 10;
    try {
      const hit = p.getBlockFromViewDirection({ maxDistance: 10 });
      if (hit) d = Math.max(0, Math.hypot(hit.block.location.x + 0.5 - eye.x, hit.block.location.z + 0.5 - eye.z) - 1.2);
    } catch {
      // ignore
    }
    const to = add(p.location, v(dir.x * d, 0, dir.z * d));
    p.teleport(to);
    p.addEffect("invisibility", 120, { amplifier: 0, showParticles: false });
    smoke(dim, "void", add(to, v(0, 1, 0)));
    sound(dim, "mob.endermen.portal", to, 1, 0.5);
  } else if (id === "fb:forge_heart") {
    const l = Math.hypot(dir.x, dir.z) || 1;
    const fx = dir.x / l;
    const fz = dir.z / l;
    const base = add(p.location, v(fx * 3, 0, fz * 3));
    for (let w = -2; w <= 2; w++) for (let h = 0; h < 3; h++) placeTemp(dim, { x: base.x - fz * w, y: base.y + h, z: base.z + fx * w }, "minecraft:polished_blackstone_bricks", 200, "air");
    embers(dim, add(base, v(0, 1, 0)));
    sound(dim, "random.anvil_use", base, 1, 0.8);
  } else if (id === "fb:star_heart") {
    const to = add(eye, scale(dir, 22));
    beam(dim, "flame", eye, to, 0.5);
    sound(dim, "mob.blaze.shoot", eye, 1, 0.7);
    for (const e of victimsOnLine(dim, eye, to, 1.3)) {
      if (e instanceof Player) continue;
      hurt(e, 9, p, EntityDamageCause.fire);
      e.setOnFire(3, true);
    }
  } else if (id === "fb:parasite_seed") {
    let drained = 0;
    for (const e of victimsNear(dim, p.location, 7)) {
      if (e instanceof Player) continue;
      hurt(e, 4, p, EntityDamageCause.magic);
      beam(dim, "green", chest(e), chest(p), 0.6);
      drained += 3;
    }
    const h = healthOf(p);
    if (h) h.setCurrentValue(Math.min(h.effectiveMax, h.currentValue + Math.min(10, drained)));
    burst(dim, "green", chest(p));
  } else if (id === "fb:shard_of_truth") {
    mirrorUntil.set(p.id, system.currentTick + 120);
    shards(dim, chest(p));
    sound(dim, "random.glass", p.location, 1, 1.6);
    p.sendMessage("§f[Shard of Truth] §7For six seconds, harm turns back on whoever deals it.");
  }
}
