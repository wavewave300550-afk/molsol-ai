import { WeatherType, world } from "@minecraft/server";
import { WORLD_WEATHER } from "../config.js";
let overworldWeather;
export function weather() {
    if (overworldWeather === undefined) {
        try {
            const w = world.getDynamicProperty(WORLD_WEATHER);
            overworldWeather = w === "Rain" ? WeatherType.Rain : w === "Thunder" ? WeatherType.Thunder : WeatherType.Clear;
        }
        catch {
            overworldWeather = WeatherType.Clear;
        }
    }
    return overworldWeather;
}
export function setWeather(w) {
    overworldWeather = w;
    try {
        world.setDynamicProperty(WORLD_WEATHER, w);
    }
    catch {
    }
}
export function timeOfDay() {
    try {
        return world.getTimeOfDay();
    }
    catch {
        return 6000;
    }
}
export function isDay() {
    const t = timeOfDay();
    return t < 12542 || t >= 23460;
}
export function isOverworld(p) {
    return p.dimension.id === "minecraft:overworld";
}
export function biome(p) {
    try {
        return p.dimension.getBiome(p.location).id;
    }
    catch {
        return "";
    }
}
const DRY = /(desert|badlands|savanna|mesa|eroded|wooded_badlands)/;
const HUMID = /(swamp|mangrove|jungle|lush_caves|river|beach|ocean|bamboo)/;
export const isDryBiome = (b) => DRY.test(b);
export const isHumidBiome = (b) => HUMID.test(b);
export function skyExposed(p) {
    try {
        const head = p.getHeadLocation();
        const top = p.dimension.getTopmostBlock({ x: Math.floor(head.x), z: Math.floor(head.z) });
        return !top || top.location.y < Math.floor(head.y);
    }
    catch {
        return false;
    }
}
export function raining(p, b = biome(p)) {
    const w = weather();
    return isOverworld(p) && w !== WeatherType.Clear && !isDryBiome(b) && skyExposed(p);
}
export function headInWater(p) {
    try {
        const b = p.dimension.getBlock(p.getHeadLocation());
        return !!b && (b.typeId === "minecraft:water" || b.typeId === "minecraft:flowing_water" || b.isWaterlogged);
    }
    catch {
        return false;
    }
}
export function inWater(p) {
    try {
        return p.isInWater || p.isSwimming;
    }
    catch {
        return false;
    }
}
export function onFire(p) {
    try {
        return !!p.getComponent("minecraft:onfire");
    }
    catch {
        return false;
    }
}
export function wetGround(p) {
    const l = p.location;
    const offs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    try {
        for (const [dx, dz] of offs) {
            const b = p.dimension.getBlock({ x: Math.floor(l.x) + dx, y: Math.floor(l.y), z: Math.floor(l.z) + dz });
            if (b && (b.typeId.includes("water") || b.isWaterlogged))
                return true;
        }
        const under = p.dimension.getBlock({ x: Math.floor(l.x), y: Math.floor(l.y) - 1, z: Math.floor(l.z) });
        if (under && /(mud|clay|moss|wet_sponge|farmland)/.test(under.typeId))
            return true;
    }
    catch {
        return false;
    }
    return false;
}
export function soilUnderfoot(p) {
    try {
        const l = p.location;
        const b = p.dimension.getBlock({ x: Math.floor(l.x), y: Math.floor(l.y - 0.1), z: Math.floor(l.z) });
        return !!b && /(dirt|grass_block|podzol|mycelium|mud|moss|clay|farmland|rooted|coarse|soul_soil|sand)/.test(b.typeId);
    }
    catch {
        return false;
    }
}
export function isMoving(p) {
    try {
        const v = p.getVelocity();
        return Math.hypot(v.x, v.z) > 0.03;
    }
    catch {
        return false;
    }
}
