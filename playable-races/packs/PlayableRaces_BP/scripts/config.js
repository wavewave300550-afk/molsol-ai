export const NS = "plrace";
export const VERSION = "1.4.0";
export const RP_VERSION_KEY = `${NS}.rp_version`;
export const PROP_DATA = `${NS}:data`;
export const WORLD_SETTINGS = `${NS}:settings`;
export const WORLD_BLOODMOON = `${NS}:bloodmoon`;
export const WORLD_WEATHER = `${NS}:weather`;
export const WORLD_UNIQUE = `${NS}:unique`;
export const ITEM_CODEX = `${NS}:codex`;
export const TAG_FORM = `${NS}:form`;
export const TAG_FOCUS = `${NS}:focus`;
export const ENTITY_MIRAGE = `${NS}:velvet_mirage`;
export const FAMILY_MIRAGE = `${NS}_mirage`;
export const FAMILY_PROXY = `${NS}_proxy`;
export const ENTITY_EXUVIA = `${NS}:exuvia`;
export const ENTITY_MEATBALL = `${NS}:meatball`;
export const ENTITY_GATE = `${NS}:celestial_gate`;
export const ENTITY_HERALD = `${NS}:herald`;
export const ENTITY_PROCESSION = `${NS}:procession`;
export const ENTITY_ECHO = `${NS}:hyphal_echo`;
export const FOG_BLOOD_MOON = `${NS}:blood_moon`;
export const FOG_USER = `${NS}_bm`;
export const TPS = 20;
export const SAVE_INTERVAL = 100;
export const GLOBAL_CAST_LOCK = 8;
export const INPUT_DEBOUNCE = 8;
export const FRESH_PRESS_GAP = 8;
export const CANCEL_GRACE = 12;
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
    ENTITY_EXUVIA,
    ENTITY_MEATBALL,
    ENTITY_GATE,
    ENTITY_HERALD,
    ENTITY_PROCESSION,
];
export const PROTECTED_FAMILIES = ["inanimate", "villager", "npc", "projectile", FAMILY_MIRAGE, FAMILY_PROXY];
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
export const MAGIC_CAUSES = new Set(["magic", "lightning", "sonicBoom", "wither"]);
export const FIRE_CAUSES = new Set(["fire", "fireTick", "lava", "magma", "campfire", "soulCampfire"]);
export const EXPLOSION_CAUSES = new Set(["blockExplosion", "entityExplosion", "fireworks"]);
