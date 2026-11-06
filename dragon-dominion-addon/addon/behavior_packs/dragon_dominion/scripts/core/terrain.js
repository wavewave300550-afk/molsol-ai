// Read-only terrain queries. Nothing here ever places, breaks or changes a block.
import { safe } from "./util.js";
import { dirOf } from "./vec.js";

// blocks a giant walks through or over without them counting as an obstacle
const PASSABLE = /(grass|fern|flower|tulip|orchid|allium|bluet|daisy|poppy|dandelion|lily|rose_bush|peony|lilac|sunflower|sapling|torch|vine|snow_layer|carpet|button|lever|rail|pressure_plate|sign|banner|mushroom|deadbush|dead_bush|seagrass|kelp|sugar_cane|reeds|wheat|carrots|potatoes|beetroot|sweet_berry|tripwire|redstone_wire|frame|pumpkin_stem|melon_stem|cobweb|web|light_block|structure_void|moss_carpet|pink_petals|leaf_litter|bush|short_|tall_|cave_vines|glow_lichen|sculk_vein|candle)/;
// soft obstacles stop a charge but are not hard enough to stun the dragon
const SOFT = /(leaves|wool|hay|slime|honey|sponge|scaffolding|snow|powder_snow|cactus|bamboo|azalea|chorus|sculk)/;

export function blockAt(dim, x, y, z) {
  return safe(() => dim.getBlock({ x: Math.floor(x), y: Math.floor(y), z: Math.floor(z) }));
}

/** true when the block physically blocks a giant (not air, liquid, plant or decoration). */
export function isSolid(b) {
  if (!b) return false;
  if (b.isAir || b.isLiquid) return false;
  return !PASSABLE.test(b.typeId);
}

export function isHard(b) {
  return isSolid(b) && !SOFT.test(b.typeId);
}

/** Loaded and safe to stand in? undefined when the chunk is not loaded. */
export function loadedAt(dim, x, y, z) {
  return blockAt(dim, x, y, z) !== undefined;
}

/**
 * Height of the walkable surface under (x, z), searching from yRef + up down to yRef - down.
 * Returns undefined if no ground (cliff edge / void / unloaded) or the column is liquid.
 */
export function groundAt(dim, x, z, yRef, up = 2, down = 6) {
  const top = Math.floor(yRef) + up;
  for (let y = top; y >= Math.floor(yRef) - down; y--) {
    const b = blockAt(dim, x, y, z);
    if (b === undefined) return undefined;
    if (b.isLiquid) return undefined;
    if (isSolid(b)) {
      const above = blockAt(dim, x, y + 1, z);
      if (above && !isSolid(above)) return y + 1;
      return undefined; // buried column, no headroom
    }
  }
  return undefined;
}

/** Free vertical space (air/plants) of `h` blocks above (x, y, z). */
export function clearAbove(dim, x, y, z, h) {
  for (let k = 0; k < h; k++) {
    const b = blockAt(dim, x, y + k, z);
    if (b === undefined || isSolid(b)) return false;
  }
  return true;
}

/**
 * Probe the wall in front of a body: a `width` wide, `height` tall slab `ahead` blocks in front of `pos`.
 * Returns { solid, hard } block counts.
 */
export function probeFront(dim, pos, yaw, ahead, width = 3, height = 3, from = 1) {
  const f = dirOf(yaw);
  const r = { x: -f.z, z: f.x };
  let solid = 0;
  let hard = 0;
  for (let w = 0; w < width; w++) {
    const off = w - (width - 1) / 2;
    const x = pos.x + f.x * ahead + r.x * off;
    const z = pos.z + f.z * ahead + r.z * off;
    for (let h = from; h < from + height; h++) {
      const b = blockAt(dim, x, pos.y + h, z);
      if (isSolid(b)) {
        solid++;
        if (isHard(b)) hard++;
      }
    }
  }
  return { solid, hard };
}

/** A footprint of radius r (square) with `h` blocks of clearance, standing on ground at height y. */
export function footprintClear(dim, x, y, z, r, h) {
  for (let dx = -r; dx <= r; dx += Math.max(1, r)) {
    for (let dz = -r; dz <= r; dz += Math.max(1, r)) {
      if (!clearAbove(dim, x + dx, y, z + dz, h)) return false;
      const g = blockAt(dim, x + dx, y - 1, z + dz);
      if (!g || g.isLiquid) return false;
    }
  }
  return true;
}
