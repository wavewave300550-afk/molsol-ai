// Grizzly's Oath - Historical Artifacts 001
// All tuning numbers live here. Times are in game ticks (20 ticks = 1 second).

export const AXE_ID = "grizzly_oath:grizzlys_oath";
export const AWAKENED_ID = "grizzly_oath:grizzlys_oath_awakened";
export const OATH_GRIZZLY_ID = "grizzly_oath:oath_grizzly";
export const SHADE_ID = "grizzly_oath:grizzly_shade";
export const FX_FAMILY = "grizzly_oath_fx";

export const PROP_SKILL = "grizzly_oath:skill";
export const PROP_HINT = "grizzly_oath:hint_shown";

export const ANIM = {
  cleaveRight: "animation.grizzly_oath.player.cleave_r",
  cleaveLeft: "animation.grizzly_oath.player.cleave_l",
  rend: "animation.grizzly_oath.player.rend",
  pursuit: "animation.grizzly_oath.player.pursuit",
  will: "animation.grizzly_oath.player.will",
  ult: "animation.grizzly_oath.player.ult",
};

export const TUNING = {
  rend: {
    range: 12,
    lateral: 0.85, // spacing between the three claw lines
    fanDegrees: 6,
    blocksPerTick: 2,
    hitRadius: 1.3,
    damage: 8,
    bleedTicks: 60, // short bleed: 3 s
    bleedDamage: 2, // per second
  },
  pursuit: {
    distance: 7,
    dashTicks: 5,
    slamDelay: 2, // ticks after arriving
    slamRadius: 3.5,
    damage: 10,
    waveRadius: 4.5,
    knockback: 1.8,
    lift: 0.45,
  },
  will: {
    durationTicks: 160, // 8 s
    shadeTicks: 60,
    pulseTicks: 20,
  },
  oath: {
    spawnDelay: 4, // grizzly appears behind the player
    roarTick: 21,
    slamTick: 39, // = spawnDelay + 1.75 s of the grizzly animation
    grizzlyTicks: 64, // grizzly animation is 3.2 s
    awakenTicks: 72, // axe glows crimson until here
    radius: 8,
    maxDamage: 18,
    minDamage: 10,
    knockback: 2.4,
    lift: 0.65,
  },
};

export type SkillId = "rend" | "pursuit" | "will" | "oath";

export interface SkillDef {
  id: SkillId;
  name: string;
  color: string;
  cooldownTicks: number;
  busyTicks: number; // other skills are locked while this one plays out
}

export const SKILLS: SkillDef[] = [
  { id: "rend", name: "Grizzly Rend", color: "§c", cooldownTicks: 7 * 20, busyTicks: 8 },
  { id: "pursuit", name: "Relentless Pursuit", color: "§6", cooldownTicks: 12 * 20, busyTicks: 14 },
  { id: "will", name: "Unbroken Will", color: "§4", cooldownTicks: 25 * 20, busyTicks: 20 },
  { id: "oath", name: "Oath of the Grizzly", color: "§d", cooldownTicks: 60 * 20, busyTicks: 60 },
];

// Entities that skills never hurt (besides the caster, tamed pets and the add-on's own visuals).
export const PROTECTED_TYPES = new Set<string>([
  "minecraft:villager",
  "minecraft:villager_v2",
  "minecraft:wandering_trader",
  "minecraft:iron_golem",
  "minecraft:snow_golem",
  "minecraft:allay",
  "minecraft:armor_stand",
  "minecraft:npc",
  "minecraft:item",
  "minecraft:xp_orb",
]);
