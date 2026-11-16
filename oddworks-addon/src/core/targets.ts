import { Entity, EntityComponentTypes, Player, Vector3, world } from "@minecraft/server";
import { ID } from "../config.js";
import { Rgba } from "./fx.js";
import { add, angleBetween, dist, norm, sub, v } from "./vec.js";

const NEVER = new Set<string>([
  "minecraft:item", "minecraft:xp_orb", "minecraft:arrow", "minecraft:area_effect_cloud", "minecraft:lightning_bolt",
  "minecraft:painting", "minecraft:leash_knot", "minecraft:fishing_hook", "minecraft:ender_crystal", "minecraft:falling_block",
  "minecraft:eye_of_ender_signal", "minecraft:fireworks_rocket", "minecraft:thrown_trident", "minecraft:ominous_item_spawner",
  ID.hook, ID.bobber, ID.sunDog, ID.iceShell,
]);
const PEACEFUL_KEEP = new Set<string>(["minecraft:villager", "minecraft:villager_v2", "minecraft:wandering_trader", "minecraft:npc"]);
const VEHICLES = new Set<string>([
  "minecraft:boat", "minecraft:chest_boat", "minecraft:minecart", "minecraft:chest_minecart", "minecraft:hopper_minecart",
  "minecraft:tnt_minecart", "minecraft:command_block_minecart", "minecraft:armor_stand", "minecraft:tnt",
]);

export const isBoat = (e: Entity): boolean => e.typeId === "minecraft:boat" || e.typeId === "minecraft:chest_boat";
export const isVehicle = (e: Entity): boolean => VEHICLES.has(e.typeId);

export function alive(e: Entity | undefined): e is Entity {
  try {
    return !!e && e.isValid;
  } catch {
    return false;
  }
}

export function pvpOn(): boolean {
  try {
    return world.gameRules.pvp;
  } catch {
    return true;
  }
}

export function ownedBy(e: Entity, p: Player): boolean {
  try {
    const t = e.getComponent(EntityComponentTypes.Tameable);
    return !!t && t.isTamed && t.tamedToPlayerId === p.id;
  } catch {
    return false;
  }
}

/** Can a skill of `p` hurt `e`? `area` = indirect/AoE effect (protects villagers too). */
export function canHurt(p: Player, e: Entity, area: boolean): boolean {
  if (!alive(e) || e.id === p.id) return false;
  if (NEVER.has(e.typeId) || isVehicle(e)) return false;
  if (e instanceof Player) {
    if (!pvpOn()) return false;
    try {
      return e.getGameMode() !== "Creative" && e.getGameMode() !== "Spectator";
    } catch {
      return true;
    }
  }
  if (ownedBy(e, p)) return false;
  if (area && PEACEFUL_KEEP.has(e.typeId)) return false;
  try {
    if (!e.getComponent(EntityComponentTypes.Health)) return false;
  } catch {
    return false;
  }
  return true;
}

export function heightOf(e: Entity): number {
  try {
    const bb = e.getAABB();
    return Math.max(0.2, bb.extent.y * 2);
  } catch {
    return 1.8;
  }
}

export function widthOf(e: Entity): number {
  try {
    const bb = e.getAABB();
    return Math.max(0.2, Math.max(bb.extent.x, bb.extent.z) * 2);
  } catch {
    return 0.6;
  }
}

export function centerOf(e: Entity): Vector3 {
  try {
    const bb = e.getAABB();
    return bb.center;
  } catch {
    return add(e.location, v(0, 0.9, 0));
  }
}

/** Entities in a view cone from `origin` (degrees), nearest first. */
export function inCone(p: Player, origin: Vector3, dir: Vector3, range: number, halfAngle: number, area = true): Entity[] {
  const out: { e: Entity; d: number }[] = [];
  for (const e of p.dimension.getEntities({ location: origin, maxDistance: range })) {
    if (!canHurt(p, e, area)) continue;
    const c = centerOf(e);
    if (angleBetween(dir, sub(c, origin)) > halfAngle) continue;
    if (!lineOfSight(p, origin, c)) continue;
    out.push({ e, d: dist(origin, c) });
  }
  return out.sort((a, b) => a.d - b.d).map((x) => x.e);
}

export function lineOfSight(p: Entity, from: Vector3, to: Vector3): boolean {
  const d = sub(to, from);
  const l = Math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z);
  if (l < 0.5) return true;
  try {
    const hit = p.dimension.getBlockFromRay(from, norm(d), { maxDistance: l - 0.3, includeLiquidBlocks: false, includePassableBlocks: false });
    return !hit;
  } catch {
    return true;
  }
}

// ------------------------------------------------------------------ physical weight (handline tug-of-war)

const WEIGHT: Record<string, number> = {
  "minecraft:chicken": 0.4, "minecraft:rabbit": 0.3, "minecraft:bat": 0.2, "minecraft:parrot": 0.3, "minecraft:cod": 0.3,
  "minecraft:salmon": 0.35, "minecraft:tropicalfish": 0.25, "minecraft:pufferfish": 0.3, "minecraft:bee": 0.2,
  "minecraft:allay": 0.3, "minecraft:vex": 0.3, "minecraft:silverfish": 0.3, "minecraft:endermite": 0.3,
  "minecraft:frog": 0.5, "minecraft:axolotl": 0.5, "minecraft:tadpole": 0.1, "minecraft:item": 0.15, "minecraft:xp_orb": 0.1,
  "minecraft:armor_stand": 1.0, "minecraft:cat": 0.6, "minecraft:ocelot": 0.6, "minecraft:fox": 0.8, "minecraft:wolf": 1.2,
  "minecraft:pig": 1.6, "minecraft:sheep": 1.6, "minecraft:goat": 1.8, "minecraft:cow": 2.6, "minecraft:mooshroom": 2.6,
  "minecraft:player": 2.0, "minecraft:enderman": 2.4, "minecraft:horse": 4.5, "minecraft:donkey": 4.0, "minecraft:mule": 4.5,
  "minecraft:llama": 4.0, "minecraft:trader_llama": 4.0, "minecraft:camel": 6.0, "minecraft:camel_husk": 6.0,
  "minecraft:polar_bear": 5.0, "minecraft:panda": 4.5, "minecraft:hoglin": 5.0, "minecraft:zoglin": 5.0,
  "minecraft:ravager": 9.0, "minecraft:iron_golem": 10.0, "minecraft:sniffer": 8.0, "minecraft:warden": 40,
  "minecraft:wither": 60, "minecraft:ender_dragon": 200, "minecraft:elder_guardian": 12, "minecraft:guardian": 3,
  "minecraft:ghast": 6, "minecraft:happy_ghast": 8, "minecraft:shulker": 60, "minecraft:creaking": 50,
  "minecraft:boat": 2.0, "minecraft:chest_boat": 3.0, "minecraft:minecart": 2.0, "minecraft:chest_minecart": 3.0,
  "minecraft:hopper_minecart": 3.0, "minecraft:tnt_minecart": 2.5, "minecraft:tnt": 0.8, "minecraft:turtle": 3.0,
  "minecraft:dolphin": 2.5, "minecraft:squid": 1.2, "minecraft:glow_squid": 1.2, "minecraft:piglin_brute": 3.0,
  "minecraft:breeze": 1.5, "minecraft:blaze": 1.6, "minecraft:phantom": 1.2, "minecraft:nautilus": 1.5,
  "minecraft:zombie_nautilus": 1.8, "minecraft:copper_golem": 2.5,
};

export function weightOf(e: Entity): number {
  let w = WEIGHT[e.typeId];
  if (w === undefined) {
    const h = heightOf(e);
    const wd = widthOf(e);
    w = Math.max(0.3, wd * wd * h * 1.25);
  }
  if (isBoat(e)) {
    try {
      const riders = e.getComponent(EntityComponentTypes.Rideable)?.getRiders() ?? [];
      for (const r of riders) w += weightOf(r) * 0.6;
    } catch {
      /* ignore */
    }
  }
  return w;
}

export function vehicleOf(e: Entity): Entity | undefined {
  try {
    return e.getComponent(EntityComponentTypes.Riding)?.entityRidingOn;
  } catch {
    return undefined;
  }
}

// ------------------------------------------------------------------ constitution (bamboo sword cane)

export interface Constitution {
  kind: string; // shown in the HUD
  bleed: number; // 0 = cannot bleed
  cut: number; // multiplier on cutting damage before armour
  color: Rgba; // blood / ichor colour
  heavy?: boolean; // blows too heavy to deflect
  metal?: boolean; // blade rings off it
}

const RED: Rgba = { r: 0.62, g: 0.04, b: 0.06, a: 1 };
const C = (kind: string, bleed: number, cut: number, color: Rgba, extra: Partial<Constitution> = {}): Constitution => ({ kind, bleed, cut, color, ...extra });

const BONE = C("bone", 0, 0.75, { r: 0.85, g: 0.83, b: 0.76, a: 1 });
const ROT = C("congealed flesh", 0.45, 1.0, { r: 0.3, g: 0.11, b: 0.07, a: 1 });
const ICHOR = C("ichor", 0.8, 1.0, { r: 0.33, g: 0.62, b: 0.32, a: 1 });

const TABLE: Record<string, Constitution> = {
  "minecraft:skeleton": BONE, "minecraft:stray": BONE, "minecraft:bogged": BONE, "minecraft:parched": BONE,
  "minecraft:skeleton_horse": BONE, "minecraft:wither_skeleton": C("bone", 0, 0.7, { r: 0.2, g: 0.2, b: 0.22, a: 1 }),
  "minecraft:wither": C("bone", 0, 0.5, { r: 0.18, g: 0.18, b: 0.2, a: 1 }, { heavy: true }),
  "minecraft:iron_golem": C("iron", 0, 0.35, { r: 0.75, g: 0.75, b: 0.75, a: 1 }, { heavy: true, metal: true }),
  "minecraft:copper_golem": C("copper", 0, 0.4, { r: 0.8, g: 0.5, b: 0.3, a: 1 }, { metal: true }),
  "minecraft:snow_golem": C("packed snow", 0, 1.3, { r: 0.95, g: 0.97, b: 1, a: 1 }),
  "minecraft:blaze": C("living flame", 0, 0.7, { r: 1, g: 0.6, b: 0.15, a: 1 }),
  "minecraft:breeze": C("wind", 0, 0.6, { r: 0.75, g: 0.8, b: 1, a: 1 }),
  "minecraft:slime": C("gel", 0, 0.9, { r: 0.45, g: 0.85, b: 0.4, a: 1 }),
  "minecraft:magma_cube": C("magma", 0, 0.75, { r: 1, g: 0.45, b: 0.1, a: 1 }),
  "minecraft:sulfur_cube": C("gel", 0, 0.85, { r: 0.9, g: 0.85, b: 0.3, a: 1 }),
  "minecraft:vex": C("spirit", 0, 1.0, { r: 0.8, g: 0.85, b: 1, a: 1 }),
  "minecraft:allay": C("spirit", 0, 1.0, { r: 0.6, g: 0.85, b: 1, a: 1 }),
  "minecraft:ghast": C("ectoplasm", 0, 1.0, { r: 0.9, g: 0.9, b: 0.95, a: 1 }),
  "minecraft:happy_ghast": C("ectoplasm", 0, 1.0, { r: 0.9, g: 0.9, b: 0.95, a: 1 }),
  "minecraft:shulker": C("shell", 0, 0.3, { r: 0.6, g: 0.45, b: 0.65, a: 1 }, { metal: true }),
  "minecraft:warden": C("sculk", 0, 0.6, { r: 0.1, g: 0.35, b: 0.4, a: 1 }, { heavy: true }),
  "minecraft:creaking": C("heartwood", 0, 0.4, { r: 0.45, g: 0.3, b: 0.2, a: 1 }, { heavy: true }),
  "minecraft:zombie": ROT, "minecraft:husk": ROT, "minecraft:drowned": ROT, "minecraft:zombie_villager": ROT,
  "minecraft:zombie_villager_v2": ROT, "minecraft:zombie_pigman": ROT, "minecraft:zombie_horse": ROT,
  "minecraft:camel_husk": ROT, "minecraft:zombie_nautilus": ROT,
  "minecraft:zoglin": C("congealed flesh", 0.45, 0.85, ROT.color, { heavy: true }),
  "minecraft:phantom": C("ectoplasm", 0.45, 1.0, { r: 0.45, g: 0.55, b: 0.62, a: 1 }),
  "minecraft:spider": ICHOR, "minecraft:cave_spider": ICHOR, "minecraft:bee": ICHOR, "minecraft:silverfish": ICHOR,
  "minecraft:endermite": C("ender ichor", 0.8, 1.0, { r: 0.55, g: 0.2, b: 0.8, a: 1 }),
  "minecraft:enderman": C("ender blood", 1.0, 1.0, { r: 0.6, g: 0.22, b: 0.85, a: 1 }),
  "minecraft:ender_dragon": C("ender blood", 0.5, 0.6, { r: 0.6, g: 0.22, b: 0.85, a: 1 }, { heavy: true }),
  "minecraft:creeper": C("sap", 0.6, 1.0, { r: 0.42, g: 0.76, b: 0.25, a: 1 }),
  "minecraft:squid": C("ink", 0.8, 1.0, { r: 0.06, g: 0.06, b: 0.1, a: 1 }),
  "minecraft:glow_squid": C("glowing ink", 0.8, 1.0, { r: 0.3, g: 0.95, b: 0.9, a: 1 }),
  "minecraft:guardian": C("scaled flesh", 0.7, 0.7, RED),
  "minecraft:elder_guardian": C("scaled flesh", 0.6, 0.6, RED, { heavy: true }),
  "minecraft:turtle": C("shell", 0.5, 0.5, RED),
  "minecraft:armadillo": C("scutes", 0.6, 0.5, RED),
  "minecraft:nautilus": C("shell", 0.6, 0.6, RED),
  "minecraft:ravager": C("thick hide", 0.6, 0.6, RED, { heavy: true }),
  "minecraft:hoglin": C("bristled hide", 0.9, 0.8, RED, { heavy: true }),
  "minecraft:polar_bear": C("fur and fat", 0.9, 0.8, RED),
  "minecraft:piglin_brute": C("flesh", 1.0, 1.0, RED, { heavy: true }),
  "minecraft:strider": C("molten blood", 0.5, 0.9, { r: 1, g: 0.55, b: 0.15, a: 1 }),
};

export function constitutionOf(e: Entity): Constitution {
  return TABLE[e.typeId] ?? C("flesh", 1.0, 1.0, RED);
}

// ------------------------------------------------------------------ worn armour (players + armour-wearing mobs)

const ARMOR_MOBS = new Set<string>([
  "minecraft:zombie", "minecraft:husk", "minecraft:drowned", "minecraft:zombie_villager", "minecraft:zombie_villager_v2",
  "minecraft:skeleton", "minecraft:stray", "minecraft:bogged", "minecraft:parched", "minecraft:wither_skeleton",
  "minecraft:piglin", "minecraft:piglin_brute", "minecraft:zombie_pigman", "minecraft:pillager", "minecraft:vindicator",
]);
const MATERIALS: [string, number, number][] = [
  // material, chest+head armour points (estimated whole set scales from this), toughness
  ["netherite", 20, 12], ["diamond", 20, 8], ["iron", 15, 0], ["chainmail", 12, 0], ["golden", 11, 0], ["leather", 7, 0],
];

export interface ArmorInfo {
  points: number;
  toughness: number;
}
const armorCache = new Map<string, { tick: number; info: ArmorInfo }>();

/** Armour of an entity. Must be called outside before-events (may run commands). */
export function armorOf(e: Entity, tick: number): ArmorInfo {
  const c = armorCache.get(e.id);
  if (c && tick - c.tick < 200) return c.info;
  let info: ArmorInfo = { points: 0, toughness: 0 };
  try {
    const eq = e.getComponent(EntityComponentTypes.Equippable);
    if (eq) info = { points: eq.totalArmor, toughness: eq.totalToughness };
    else if (ARMOR_MOBS.has(e.typeId)) {
      let pts = 0;
      let tough = 0;
      for (const [slot, part] of [["slot.armor.chest", "chestplate"], ["slot.armor.head", "helmet"]] as const) {
        for (const [mat, set, t] of MATERIALS) {
          const r = e.runCommand(`testfor @s[hasitem={item=minecraft:${mat}_${part},location=${slot}}]`);
          if (r.successCount > 0) {
            pts += set * (part === "chestplate" ? 0.55 : 0.25);
            tough += t * 0.4;
            break;
          }
        }
      }
      info = { points: Math.round(pts), toughness: Math.round(tough) };
    }
  } catch {
    /* unknown -> unarmoured */
  }
  armorCache.set(e.id, { tick, info });
  return info;
}

/** Cached armour only (safe inside before-events). */
export function cachedArmor(e: Entity): ArmorInfo | undefined {
  return armorCache.get(e.id)?.info;
}

export function forgetEntity(id: string): void {
  armorCache.delete(id);
}
