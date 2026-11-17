/**
 * Sekiyu Sekiyu no Mi — balance sheet. Every gameplay number lives here.
 * Times are in ticks (20 ticks = 1 s). There is deliberately NO fuel / oil gauge:
 * petroleum is generated without limit; only cooldowns and performance budgets apply.
 */

export const IDS = {
  fruit: "sekiyu:sekiyu_fruit",
  core: "sekiyu:crude_core",
} as const;

/** Entities the power creates (all temporary, all cleaned up automatically). */
export const ENT = {
  pool: "sekiyu:oil_pool",
  tide: "sekiyu:black_tide",
  geyser: "sekiyu:black_geyser",
  prison: "sekiyu:tar_prison",
  serpent: "sekiyu:black_serpent",
  relic: "sekiyu:fruit_relic",
} as const;
export const CONSTRUCT_FAMILY = "sekiyu_construct";

export const DP = {
  owner: "sekiyu:owner",
  selected: "sekiyu:selected",
  hud: "sekiyu:hud",
  welcomed: "sekiyu:welcomed",
  constructOwner: "sekiyu:owner_id",
} as const;

/** Client-synced actor properties. */
export const PROP = {
  /** player: 0 no power, 1 human, 2 Petroleum Body, 3 dissolved (Infiltration) */
  form: "sekiyu:form",
  /** player and constructs: ignited oil */
  burning: "sekiyu:burning",
  /** oil pool: radius in blocks */
  radius: "sekiyu:radius",
} as const;

export enum Form {
  None = 0,
  Human = 1,
  Body = 2,
  Dissolved = 3,
}

export const WORLD_PVP = "sekiyu:pvp";

export interface AbilitySpec {
  id: string;
  name: string;
  short: string;
  cooldown: number;
  /** What a second Use does while the ability is active (shown on the HUD). */
  followUp?: string;
  description: string;
}

export const ABILITIES = {
  tide: {
    id: "tide", name: "Black Tide", short: "TID", cooldown: 240, followUp: "IGNITE",
    description: "A 6-block-wide wave of heavy crude rolls 18 blocks forward: damage, knockback, heavy-oil Slowness, oil slicks behind it. Tap again to ignite the wave.",
  },
  body: {
    id: "body", name: "Petroleum Body", short: "BDY", cooldown: 80, followUp: "REFORM",
    description: "Become living petroleum: physical attacks pass through you, moving = light crude (Speed II), standing = heavy crude (Resistance). Your melee hits flare with fire. Use again to reform.",
  },
  geyser: {
    id: "geyser", name: "Black Geyser", short: "GEY", cooldown: 200, followUp: "IGNITE",
    description: "Three high-pressure geysers erupt where you aim (22 blocks): damage, launch, thick oil covers the ground. Tap again within 3s to ignite it.",
  },
  prison: {
    id: "prison", name: "Tar Prison", short: "TAR", cooldown: 280, followUp: "IGNITE",
    description: "Viscous tar tendrils engulf the target for 4s: held in place, slowed, suffocating damage. Tap again to ignite the prison for a burst of fire.",
  },
  jet: {
    id: "jet", name: "Oil Jet", short: "JET", cooldown: 50, followUp: "AFTERBURN",
    description: "High-pressure light crude hurls you ~8 blocks where you look (ground or air). Tap again within 1.2s for an ignited afterburner jet in your new direction.",
  },
  serpent: {
    id: "serpent", name: "Black Serpent", short: "SRP", cooldown: 360, followUp: "IGNITE",
    description: "A 9-block oil serpent hunts your target for 10s: bites (heavy-oil Slowness), constricts, tail-sweeps groups. Tap again to set it ablaze.",
  },
  seep: {
    id: "seep", name: "Petroleum Infiltration", short: "SEP", cooldown: 160, followUp: "REFORM",
    description: "Dissolve into a fast puddle for 3s: physical attacks pass through, Speed IV, seep through 1-block-high gaps. Use again to reform early.",
  },
  inferno: {
    id: "inferno", name: "Black Inferno", short: "INF", cooldown: 1500,
    description: "ULTIMATE: a massive oil eruption floods 12 blocks around you, then ignites: huge fire damage, burning pools, smoke-dark sky for 12s.",
  },
} satisfies Record<string, AbilitySpec>;

export type AbilityId = keyof typeof ABILITIES;
export const spec = (id: AbilityId): AbilitySpec => ABILITIES[id];
export const ABILITY_ORDER: AbilityId[] = ["tide", "body", "geyser", "prison", "jet", "serpent", "seep", "inferno"];

export const TUNING = {
  tide: { speed: 0.5, distance: 18, halfWidth: 3.2, height: 3.8, depth: 1.8, damage: 6, fireBonus: 4, knock: 1.6, lift: 0.35, slowTicks: 60, slowAmp: 1, poolEvery: 4, poolRadius: 2.2, fireSeconds: 4 },
  body: { flareCooldown: 20, flareDamage: 3, flareFireSeconds: 3, trailEvery: 40, trailRadius: 1.3 },
  geyser: { range: 22, telegraph: 12, radius: 2.0, damage: 8, launch: 1.15, spread: 2.4, poolRadius: 3.0, igniteWindow: 60, fireDamage: 5, fireRadius: 3.5, fireSeconds: 5, slowTicks: 50 },
  prison: { range: 18, duration: 80, dotEvery: 20, dot: 1.5, slowAmp: 3, igniteDamage: 7, igniteFireSeconds: 5, poolRadius: 2.5 },
  jet: { speed: 1.15, lift: 0.3, airLift: 0.15, chainWindow: 24, afterburnSpeed: 1.0, afterburnDamage: 4, fireSeconds: 3, fallGuard: 70, slickRadius: 1.5 },
  serpent: { duration: 200, speed: 0.5, thickSpeed: 0.28, reach: 2.8, biteEvery: 26, biteDamage: 7, fireBonus: 3, constrictEvery: 3, constrictTicks: 30, sweepRadius: 4, sweepDamage: 5, seek: 24, collapseDamage: 5 },
  seep: { duration: 60, speedAmp: 3, seepDistance: 4 },
  inferno: { windup: 24, radius: 12, damage: 14, fireSeconds: 6, burnTicks: 160, knock: 1.5, fogTicks: 240 },
} as const;

/** Logia defence and weaknesses. */
export const LOGIA = {
  /** Human form: one physical hit flows through you every `reflexTicks`. */
  reflexTicks: 80,
  /** Fire / lava damage multiplier while your body is petroleum (Body or Infiltration). */
  fireVulnerability: 1.6,
  /** Explosions only half pass through liquid. */
  explosionFactor: 0.5,
  /** Human form fall damage multiplier (forms take none). */
  fallFactor: 0.5,
  /** Seawater-like weakness: powers sealed while submerged. */
  waterSlowAmp: 0,
};

export const POOLS = {
  /** Global cap of oil pool entities (oldest evaporate first). */
  max: 24,
  lifetime: 240,
  /** A burning pool burns this long, then the oil is consumed. */
  burnTicks: 120,
  burnDamage: 2,
  burnEvery: 20,
  slowAmp: 0,
};

/** Hard caps that keep big fights playable on phones. */
export const BUDGET = {
  serpentsPerPlayer: 1,
  tidesPerPlayer: 2,
  prisonsPerPlayer: 2,
  maxConstructs: 24,
};

export const CONTROLS = {
  /** Ticks after a skill switch / closing the console during which plain Use is ignored. */
  castGuard: 10,
  /** View-direction Y at or above which a Sneak press goes to the PREVIOUS skill. */
  lookUp: 0.8,
};

export const HUD = { period: 4, linger: 80 };

export const PROTECTED_TYPES = new Set<string>([
  "minecraft:item", "minecraft:xp_orb", "minecraft:armor_stand", "minecraft:villager", "minecraft:villager_v2",
  "minecraft:wandering_trader", "minecraft:iron_golem", "minecraft:snow_golem", "minecraft:copper_golem",
  "minecraft:allay", "minecraft:npc", "minecraft:agent", "minecraft:painting", "minecraft:leash_knot",
  "minecraft:ender_crystal", "minecraft:arrow", "minecraft:xp_bottle", "minecraft:thrown_trident",
]);

/** Blocks a dissolved player can flow through when seeping (besides air and liquids). */
export const PASSABLE = new Set<string>([
  "minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern", "minecraft:large_fern", "minecraft:dead_bush",
  "minecraft:snow_layer", "minecraft:torch", "minecraft:redstone_wire", "minecraft:rail", "minecraft:carpet",
  "minecraft:dandelion", "minecraft:poppy", "minecraft:seagrass", "minecraft:vine", "minecraft:light_block",
]);

/** Blocks that ignite oil they touch. */
export const IGNITERS = new Set<string>(["minecraft:fire", "minecraft:soul_fire", "minecraft:lava", "minecraft:magma", "minecraft:campfire", "minecraft:soul_campfire"]);
