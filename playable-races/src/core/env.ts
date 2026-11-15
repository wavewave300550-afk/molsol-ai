/** Cheap environment probes used by race passives (called at most 1-4 times per second per player). */
import { Player, WeatherType, world } from "@minecraft/server";
import { WORLD_WEATHER } from "../config.js";

let overworldWeather: WeatherType | undefined;

export function weather(): WeatherType {
  if (overworldWeather === undefined) {
    try {
      const w = world.getDynamicProperty(WORLD_WEATHER);
      overworldWeather = w === "Rain" ? WeatherType.Rain : w === "Thunder" ? WeatherType.Thunder : WeatherType.Clear;
    } catch {
      overworldWeather = WeatherType.Clear;
    }
  }
  return overworldWeather;
}

export function setWeather(w: WeatherType): void {
  overworldWeather = w;
  try {
    world.setDynamicProperty(WORLD_WEATHER, w);
  } catch {
    /* ignore */
  }
}

export function timeOfDay(): number {
  try {
    return world.getTimeOfDay();
  } catch {
    return 6000;
  }
}

/** Daylight (sun above the horizon). */
export function isDay(): boolean {
  const t = timeOfDay();
  return t < 12542 || t >= 23460;
}

export function isOverworld(p: Player): boolean {
  return p.dimension.id === "minecraft:overworld";
}

export function biome(p: Player): string {
  try {
    return p.dimension.getBiome(p.location).id;
  } catch {
    return "";
  }
}

const DRY = /(desert|badlands|savanna|mesa|eroded|wooded_badlands)/;
const HUMID = /(swamp|mangrove|jungle|lush_caves|river|beach|ocean|bamboo)/;
export const isDryBiome = (b: string) => DRY.test(b);
export const isHumidBiome = (b: string) => HUMID.test(b);

export function skyExposed(p: Player): boolean {
  try {
    const head = p.getHeadLocation();
    const top = p.dimension.getTopmostBlock({ x: Math.floor(head.x), z: Math.floor(head.z) });
    return !top || top.location.y < Math.floor(head.y);
  } catch {
    return false;
  }
}

export function raining(p: Player, b = biome(p)): boolean {
  const w = weather();
  return isOverworld(p) && w !== WeatherType.Clear && !isDryBiome(b) && skyExposed(p);
}

export function headInWater(p: Player): boolean {
  try {
    const b = p.dimension.getBlock(p.getHeadLocation());
    return !!b && (b.typeId === "minecraft:water" || b.typeId === "minecraft:flowing_water" || b.isWaterlogged);
  } catch {
    return false;
  }
}

export function inWater(p: Player): boolean {
  try {
    return p.isInWater || p.isSwimming;
  } catch {
    return false;
  }
}

export function onFire(p: Player): boolean {
  try {
    return !!p.getComponent("minecraft:onfire");
  } catch {
    return false;
  }
}

/** Is there water touching the player's feet (shore, puddle, rain-soaked ground)? */
export function wetGround(p: Player): boolean {
  const l = p.location;
  const offs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  try {
    for (const [dx, dz] of offs) {
      const b = p.dimension.getBlock({ x: Math.floor(l.x) + dx, y: Math.floor(l.y), z: Math.floor(l.z) + dz });
      if (b && (b.typeId.includes("water") || b.isWaterlogged)) return true;
    }
    const under = p.dimension.getBlock({ x: Math.floor(l.x), y: Math.floor(l.y) - 1, z: Math.floor(l.z) });
    if (under && /(mud|clay|moss|wet_sponge|farmland)/.test(under.typeId)) return true;
  } catch {
    return false;
  }
  return false;
}

export function soilUnderfoot(p: Player): boolean {
  try {
    const l = p.location;
    const b = p.dimension.getBlock({ x: Math.floor(l.x), y: Math.floor(l.y - 0.1), z: Math.floor(l.z) });
    return !!b && /(dirt|grass_block|podzol|mycelium|mud|moss|clay|farmland|rooted|coarse|soul_soil|sand)/.test(b.typeId);
  } catch {
    return false;
  }
}

export function isMoving(p: Player): boolean {
  try {
    const v = p.getVelocity();
    return Math.hypot(v.x, v.z) > 0.03;
  } catch {
    return false;
  }
}
