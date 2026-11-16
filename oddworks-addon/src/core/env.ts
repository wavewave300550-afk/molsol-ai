import { Player, Vector3, WeatherType, world } from "@minecraft/server";
import { v } from "./vec.js";

// ------------------------------------------------------------------ weather tracking
// The Script API reports weather changes but has no getter, so the last known value per
// dimension is remembered (and persisted across reloads).
const weather = new Map<string, WeatherType>();

export function initWeather(): void {
  try {
    const saved = world.getDynamicProperty("oddworks:weather");
    if (typeof saved === "string") {
      for (const [dim, w] of Object.entries(JSON.parse(saved) as Record<string, WeatherType>)) weather.set(dim, w);
    }
  } catch {
    /* fresh world */
  }
  world.afterEvents.weatherChange.subscribe((ev) => {
    weather.set(ev.dimension, ev.newWeather);
    try {
      world.setDynamicProperty("oddworks:weather", JSON.stringify(Object.fromEntries(weather)));
    } catch {
      /* ignore */
    }
  });
}

export function weatherIn(dimId: string): WeatherType {
  return weather.get(dimId) ?? WeatherType.Clear;
}

// ------------------------------------------------------------------ sun geometry

/** Sun elevation factor: 1 at noon, 0 at sunrise/sunset, negative at night. */
export function sunElevation(): number {
  const t = world.getTimeOfDay();
  return Math.sin((t / 24000) * Math.PI * 2);
}

/** Direction from the observer towards the sun (Minecraft sun travels east -> west through the zenith). */
export function sunDirection(): Vector3 {
  const a = (world.getTimeOfDay() / 24000) * Math.PI * 2;
  return v(Math.cos(a), Math.sin(a), 0);
}

const MOON_FULLNESS = [1, 0.75, 0.5, 0.25, 0, 0.25, 0.5, 0.75];

// ------------------------------------------------------------------ surroundings

const SNOWY_BLOCKS = new Set([
  "minecraft:snow", "minecraft:snow_layer", "minecraft:powder_snow", "minecraft:ice", "minecraft:packed_ice",
  "minecraft:blue_ice", "minecraft:frosted_ice",
]);
const SANDY_BLOCKS = new Set(["minecraft:sand", "minecraft:red_sand", "minecraft:sandstone", "minecraft:white_concrete"]);
const SNOW_BIOME_TAGS = ["frozen", "ice", "ice_plains", "snowy_slopes", "frozen_peaks", "jagged_peaks", "grove"];
const HOT_BIOME_WORDS = ["desert", "mesa", "badlands", "savanna_mutated", "basalt", "crimson", "warped", "hell", "soulsand"];

export interface Surroundings {
  snow: number; // 0..1 fraction of reflective snow/ice around
  sand: number;
  snowyBiome: boolean;
  coldBiome: boolean;
  hot: boolean;
  biomeId: string;
}

const surroundCache = new Map<string, { tick: number; data: Surroundings }>();

export function surroundings(p: Player, tick: number): Surroundings {
  const c = surroundCache.get(p.id);
  if (c && tick - c.tick < 10) return c.data;
  const dim = p.dimension;
  const base = p.location;
  let snow = 0;
  let sand = 0;
  let n = 0;
  for (let dx = -4; dx <= 4; dx += 2) {
    for (let dz = -4; dz <= 4; dz += 2) {
      n++;
      for (const dy of [0, -1, -2]) {
        try {
          const b = dim.getBlock({ x: base.x + dx, y: base.y + dy, z: base.z + dz });
          if (!b || b.isAir) continue;
          if (SNOWY_BLOCKS.has(b.typeId)) snow++;
          else if (SANDY_BLOCKS.has(b.typeId)) sand++;
          break;
        } catch {
          break;
        }
      }
    }
  }
  let biomeId = "";
  let snowyBiome = false;
  let coldBiome = false;
  try {
    const biome = dim.getBiome(base);
    biomeId = biome.id;
    const tags = biome.getTags();
    snowyBiome = SNOW_BIOME_TAGS.some((t) => tags.includes(t));
    coldBiome = tags.includes("cold");
  } catch {
    /* biome API unavailable for this location */
  }
  const hot = dim.id === "minecraft:nether" || HOT_BIOME_WORDS.some((w) => biomeId.includes(w));
  const data: Surroundings = {
    snow: Math.max(snow / n, snowyBiome ? 0.5 : coldBiome ? 0.25 : 0),
    sand: sand / n,
    snowyBiome,
    coldBiome,
    hot,
    biomeId,
  };
  surroundCache.set(p.id, { tick, data });
  return data;
}

// ------------------------------------------------------------------ solar power

export interface SolarInfo {
  power: number; // effective light the lenses can drink (0 .. 1.6)
  sun: number; // direct sunlight component (0 .. 1)
  albedo: number; // reflection multiplier from snow/sand (>= 1)
  snowy: boolean;
  hot: boolean;
  source: "sun" | "snow" | "overcast" | "moon" | "torch" | "dark" | "sundog";
  sky: number;
}

export function solarInfo(p: Player, tick: number, sunDogNear: boolean): SolarInfo {
  const dim = p.dimension;
  const eye = p.getHeadLocation();
  const env = surroundings(p, tick);
  let sky = 0;
  let block = 0;
  try {
    sky = dim.getSkyLightLevel(eye);
    block = dim.getLightLevel(eye);
  } catch {
    /* out of world */
  }
  const overworld = dim.id === "minecraft:overworld";
  const w = weatherIn(dim.id);
  const wf = w === WeatherType.Thunder ? 0.3 : w === WeatherType.Rain ? 0.55 : 1;
  const exposure = Math.pow(sky / 15, 2);
  const e = overworld ? sunElevation() : -1;
  const day = e > 0 ? Math.pow(e, 0.55) : 0;
  let fullness = 0.5;
  try {
    fullness = MOON_FULLNESS[world.getMoonPhase()] ?? 0.5;
  } catch {
    /* ignore */
  }
  const moon = overworld && e < 0 ? (0.06 + 0.14 * fullness) * Math.min(1, -e * 3) : 0;
  const sun = day * wf * exposure;
  const albedo = 1 + 0.6 * env.snow + 0.15 * env.sand;
  const torch = 0.12 * (block / 15);
  let power = Math.max(sun * albedo, moon * wf * exposure * (1 + 0.3 * env.snow), torch);
  let source: SolarInfo["source"] = sun * albedo >= power - 1e-6 && sun > 0.02
    ? (env.snow >= 0.3 ? "snow" : wf < 1 ? "overcast" : "sun")
    : moon * wf * exposure > torch ? "moon" : torch > 0.01 ? "torch" : "dark";
  if (sunDogNear && power < 1) {
    power = 1;
    source = "sundog";
  }
  return { power: Math.min(1.6, power), sun, albedo, snowy: env.snow >= 0.3, hot: env.hot, source, sky };
}
