import { BlockPermutation, Dimension, Vector3, system, world } from "@minecraft/server";

/**
 * Temporary terrain edits (Titan constructions, Parasite infection) with guaranteed restoration.
 * Every change is journaled in a world dynamic property so that even after a crash or reload the
 * original blocks are put back the next time the world loads.
 */

interface Edit {
  dim: string;
  x: number;
  y: number;
  z: number;
  original: string;
  until: number;
  perm?: BlockPermutation;
}

const JOURNAL = "fb:block_journal";
const edits = new Map<string, Edit>();
let dirty = false;

const NATURAL = new Set([
  "minecraft:grass_block", "minecraft:dirt", "minecraft:coarse_dirt", "minecraft:podzol", "minecraft:sand", "minecraft:red_sand",
  "minecraft:gravel", "minecraft:stone", "minecraft:andesite", "minecraft:diorite", "minecraft:granite", "minecraft:deepslate",
  "minecraft:mycelium", "minecraft:moss_block", "minecraft:snow_block", "minecraft:netherrack", "minecraft:end_stone",
  "minecraft:dirt_with_roots", "minecraft:mud", "minecraft:clay", "minecraft:sandstone", "minecraft:tuff", "minecraft:calcite",
]);

const key = (dim: string, p: Vector3) => `${dim}|${Math.floor(p.x)}|${Math.floor(p.y)}|${Math.floor(p.z)}`;

/** Place `typeId` at `p` for `ticks` ticks. mode "air": only into air. mode "natural": only over natural terrain. */
export function placeTemp(dim: Dimension, p: Vector3, typeId: string, ticks: number, mode: "air" | "natural"): boolean {
  const k = key(dim.id, p);
  const until = system.currentTick + ticks;
  const prior = edits.get(k);
  if (prior) {
    prior.until = Math.max(prior.until, until);
    return true;
  }
  try {
    const b = dim.getBlock(p);
    if (!b) return false;
    if (mode === "air" && !b.isAir) return false;
    if (mode === "natural" && !NATURAL.has(b.typeId)) return false;
    const e: Edit = { dim: dim.id, x: Math.floor(p.x), y: Math.floor(p.y), z: Math.floor(p.z), original: b.typeId, until, perm: b.permutation };
    dim.setBlockType(b.location, typeId);
    edits.set(k, e);
    dirty = true;
    return true;
  } catch {
    return false;
  }
}

function restore(e: Edit): void {
  try {
    const dim = world.getDimension(e.dim);
    const at = { x: e.x, y: e.y, z: e.z };
    if (e.perm) dim.setBlockPermutation(at, e.perm);
    else dim.setBlockType(at, e.original);
  } catch {
    return; // chunk unloaded: keep it journaled for the next load
  }
  edits.delete(key(e.dim, e));
  dirty = true;
}

export function tickBlocks(): void {
  const t = system.currentTick;
  for (const e of [...edits.values()]) if (e.until <= t) restore(e);
  if (dirty && t % 20 === 0) saveJournal();
}

export function restoreAllNow(): void {
  for (const e of [...edits.values()]) restore(e);
  saveJournal();
}

export function editsActive(): number {
  return edits.size;
}

export function isTempBlock(dim: string, p: Vector3): boolean {
  return edits.has(key(dim, p));
}

function saveJournal(): void {
  dirty = false;
  const rows = [...edits.values()].map((e) => [e.dim, e.x, e.y, e.z, e.original]);
  try {
    world.setDynamicProperty(JOURNAL, JSON.stringify(rows));
  } catch {
    // journal too large: keep in memory only
  }
}

/** On world load: restore anything left over from a previous session. */
export function recoverJournal(): number {
  const raw = world.getDynamicProperty(JOURNAL);
  if (typeof raw !== "string") return 0;
  let n = 0;
  try {
    for (const [dim, x, y, z, original] of JSON.parse(raw) as [string, number, number, number, string][]) {
      try {
        world.getDimension(dim).setBlockType({ x, y, z }, original);
        n++;
      } catch {
        // ignore
      }
    }
  } catch {
    // corrupt journal
  }
  world.setDynamicProperty(JOURNAL, "[]");
  return n;
}
