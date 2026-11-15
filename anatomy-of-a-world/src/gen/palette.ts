/**
 * Shared block palette for all generators. Index 0 means "leave the world
 * untouched" (structure void); index 1 is explicit air.
 *
 * Every id here is checked against @minecraft/vanilla-data 1.26.60 by the
 * build's validator, and every state name against the vanilla state table.
 */

export type BlockStates = Record<string, string | number | boolean>;

export interface PaletteEntry {
  readonly id: string;
  readonly states?: BlockStates;
}

const entries: PaletteEntry[] = [];
const byKey = new Map<string, number>();

function key(id: string, states?: BlockStates): string {
  if (!states) return id;
  return id + "[" + Object.keys(states).sort().map((k) => `${k}=${String(states[k])}`).join(",") + "]";
}

export function pal(id: string, states?: BlockStates): number {
  const k = key(id, states);
  const found = byKey.get(k);
  if (found !== undefined) return found;
  const idx = entries.length;
  if (idx > 254) throw new Error("palette overflow");
  entries.push(states ? { id, states } : { id });
  byKey.set(k, idx);
  return idx;
}

export function paletteEntries(): readonly PaletteEntry[] {
  return entries;
}

export function paletteKey(index: number): string {
  const e = entries[index];
  return key(e.id, e.states);
}

// Index 0 = structure void / keep, index 1 = air.
export const KEEP = pal("minecraft:structure_void");
export const AIR = pal("minecraft:air");

// --- living strata -----------------------------------------------------------
export const STONE = pal("minecraft:stone");
export const ANDESITE = pal("minecraft:andesite");
export const TUFF = pal("minecraft:tuff");
export const COBBLE = pal("minecraft:cobblestone");
export const MOSSY_COBBLE = pal("minecraft:mossy_cobblestone");
export const CALCITE = pal("minecraft:calcite");
export const DEEPSLATE = pal("minecraft:deepslate");
export const COBBLED_DEEPSLATE = pal("minecraft:cobbled_deepslate");
export const SMOOTH_BASALT = pal("minecraft:smooth_basalt");
export const GRANITE = pal("minecraft:granite");
export const DRIPSTONE = pal("minecraft:dripstone_block");

// --- dorsal biome --------------------------------------------------------------
export const GRASS = pal("minecraft:grass_block");
export const DIRT = pal("minecraft:dirt");
export const COARSE_DIRT = pal("minecraft:coarse_dirt");
export const PODZOL = pal("minecraft:podzol");
export const MOSS = pal("minecraft:moss_block");
export const MOSS_CARPET = pal("minecraft:moss_carpet");
export const PATH = pal("minecraft:grass_path");
export const SNOW = pal("minecraft:snow");
export const SNOW_LAYER_1 = pal("minecraft:snow_layer", { height: 0, covered_bit: false });
export const SNOW_LAYER_2 = pal("minecraft:snow_layer", { height: 1, covered_bit: false });
export const SHORT_GRASS = pal("minecraft:short_grass");
export const FERN = pal("minecraft:fern");
export const POPPY = pal("minecraft:poppy");
export const CORNFLOWER = pal("minecraft:cornflower");
export const AZURE_BLUET = pal("minecraft:azure_bluet");
export const SPRUCE_LOG = pal("minecraft:spruce_log", { pillar_axis: "y" });
export const SPRUCE_LEAVES = pal("minecraft:spruce_leaves", { persistent_bit: true, update_bit: false });
export const OAK_LOG = pal("minecraft:oak_log", { pillar_axis: "y" });
export const OAK_LEAVES = pal("minecraft:oak_leaves", { persistent_bit: true, update_bit: false });
export const AZALEA_LEAVES = pal("minecraft:azalea_leaves_flowered", { persistent_bit: true, update_bit: false });
export const WATER = pal("minecraft:water", { liquid_depth: 0 });

// --- lithic musculature / mineral circulation ---------------------------------------
export const MUSCLE = pal("minecraft:crimson_hyphae", { pillar_axis: "y" });
export const MUSCLE_X = pal("minecraft:crimson_hyphae", { pillar_axis: "x" });
export const MUSCLE_Z = pal("minecraft:crimson_hyphae", { pillar_axis: "z" });
export const SINEW = pal("minecraft:stripped_crimson_hyphae", { pillar_axis: "y" });
export const FLESH = pal("minecraft:nether_wart_block");
export const MANTLE_ROCK = pal("minecraft:red_terracotta");
export const MANTLE_FLOOR = pal("minecraft:crimson_nylium");
export const PACKED_MUD = pal("minecraft:packed_mud");
export const VEIN_GLOW = pal("minecraft:shroomlight");
export const VEIN_HOT = pal("minecraft:magma");
export const OCHRE_LIGHT = pal("minecraft:ochre_froglight", { pillar_axis: "y" });
export const PEARL_LIGHT = pal("minecraft:pearlescent_froglight", { pillar_axis: "y" });
export const ROOT_WOOD = pal("minecraft:mangrove_wood", { pillar_axis: "y" });
export const ROOT_WOOD_X = pal("minecraft:mangrove_wood", { pillar_axis: "x" });
export const ROOT_WOOD_Z = pal("minecraft:mangrove_wood", { pillar_axis: "z" });
export const MANGROVE_ROOTS = pal("minecraft:mangrove_roots");
export const HANGING_ROOTS = pal("minecraft:hanging_roots");

// --- lithic heart / resonance ------------------------------------------------------
export const AMETHYST = pal("minecraft:amethyst_block");
export const BUDDING = pal("minecraft:budding_amethyst");
export const CRYING_OBSIDIAN = pal("minecraft:crying_obsidian");
export const AMETHYST_CLUSTER_UP = pal("minecraft:amethyst_cluster", { "minecraft:block_face": "up" });

// --- organ cavern decoration ----------------------------------------------------
export const DRIP_DOWN_TIP = pal("minecraft:pointed_dripstone", { hanging: true, dripstone_thickness: "tip" });
export const DRIP_DOWN_FRUSTUM = pal("minecraft:pointed_dripstone", { hanging: true, dripstone_thickness: "frustum" });
export const DRIP_DOWN_BASE = pal("minecraft:pointed_dripstone", { hanging: true, dripstone_thickness: "base" });
export const CAVE_VINES_BERRIES = pal("minecraft:cave_vines_body_with_berries", { growing_plant_age: 25 });
export const CAVE_VINES_HEAD = pal("minecraft:cave_vines_head_with_berries", { growing_plant_age: 25 });
export const SPORE_BLOSSOM = pal("minecraft:spore_blossom");
export const LIGHT_12 = pal("minecraft:light_block_12");
