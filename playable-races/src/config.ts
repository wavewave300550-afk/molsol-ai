/** Shared identifiers and tuning constants. Identifiers are permanent: worlds depend on them. */
export const NS = "plrace";

export const PROP_DATA = `${NS}:data`;
export const WORLD_SETTINGS = `${NS}:settings`;
export const WORLD_BLOODMOON = `${NS}:bloodmoon`;
export const WORLD_WEATHER = `${NS}:weather`;

export const ITEM_CODEX = `${NS}:codex`;
export const TAG_FORM = `${NS}:form`;
export const TAG_FOCUS = `${NS}:focus`;
export const ENTITY_MIRAGE = `${NS}:velvet_mirage`;
export const FAMILY_MIRAGE = `${NS}_mirage`;
export const FOG_BLOOD_MOON = `${NS}:blood_moon`;
export const FOG_USER = `${NS}_bm`;

export const TPS = 20;
export const SAVE_INTERVAL = 100; // ticks between persistence flushes
export const GLOBAL_CAST_LOCK = 8; // ticks between any two casts
export const INPUT_DEBOUNCE = 8;
/** Use events closer together than this are a held/repeating button, not a new press. */
export const FRESH_PRESS_GAP = 8;
/** A channel can only be cancelled by re-using its ability after this many ticks (ignores held/duplicate input). */
export const CANCEL_GRACE = 12;

/** Entity types abilities must never damage or push. */
export const PROTECTED_TYPES = [
  "minecraft:villager_v2",
  "minecraft:villager",
  "minecraft:wandering_trader",
  "minecraft:iron_golem",
  "minecraft:snow_golem",
  "minecraft:armor_stand",
  "minecraft:item",
  "minecraft:xp_orb",
  "minecraft:painting",
  "minecraft:leash_knot",
  "minecraft:npc",
  "minecraft:allay",
  "minecraft:copper_golem",
  "minecraft:happy_ghast",
  ENTITY_MIRAGE,
];
export const PROTECTED_FAMILIES = ["inanimate", "villager", "npc", "projectile", FAMILY_MIRAGE];

/** Damage causes treated as "conventional physical attacks" (golem stone body). */
export const PHYSICAL_CAUSES = new Set([
  "entityAttack",
  "projectile",
  "contact",
  "fallingBlock",
  "piston",
  "ramAttack",
  "maceSmash",
  "anvil",
  "stalactite",
  "stalagmite",
  "flyIntoWall",
]);
export const MAGIC_CAUSES = new Set(["magic", "lightning", "sonicBoom", "wither" as string]);
export const FIRE_CAUSES = new Set(["fire", "fireTick", "lava", "magma", "campfire", "soulCampfire"]);
