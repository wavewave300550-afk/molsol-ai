// Particle + sound helpers. Every call is wrapped: a particle in an unloaded chunk must never
// break a skill half-way through.
import { MolangVariableMap } from "@minecraft/server";
export const RED = { red: 1, green: 0.12, blue: 0.08, alpha: 1 };
export const HOT = { red: 1, green: 0.55, blue: 0.4, alpha: 1 };
export const DEEP_RED = { red: 0.6, green: 0.02, blue: 0.04, alpha: 0.95 };
export const BLACK = { red: 0.05, green: 0.01, blue: 0.015, alpha: 0.8 };
export function emit(dim, name, at, setup) {
    try {
        const m = new MolangVariableMap();
        if (setup)
            setup(m);
        dim.spawnParticle(`grizzly_oath:${name}`, at, m);
    }
    catch {
        // chunk unloaded / out of world bounds: skip this particle
    }
}
export const glow = (dim, at, size, life, color, rise = 0) => emit(dim, "glow", at, (m) => {
    m.setFloat("variable.size", size);
    m.setFloat("variable.life", life);
    m.setFloat("variable.rise", rise);
    m.setColorRGBA("variable.color", color);
});
export const slash = (dim, at, size, rot, color) => emit(dim, "slash", at, (m) => {
    m.setFloat("variable.size", size);
    m.setFloat("variable.rot", rot);
    m.setColorRGBA("variable.color", color);
});
export const clawFlash = (dim, at, size, rot, color) => emit(dim, "claw_flash", at, (m) => {
    m.setFloat("variable.size", size);
    m.setFloat("variable.rot", rot);
    m.setColorRGBA("variable.color", color);
});
export const clawStreak = (dim, at, dir, color, life = 0.5) => emit(dim, "claw_streak", at, (m) => {
    m.setVector3("variable.dir", dir);
    m.setFloat("variable.life", life);
    m.setColorRGBA("variable.color", color);
});
export const ring = (dim, at, radius, life, color) => emit(dim, "ring", at, (m) => {
    m.setFloat("variable.radius", radius);
    m.setFloat("variable.life", life);
    m.setColorRGBA("variable.color", color);
});
export const smoke = (dim, at, size, color = BLACK) => emit(dim, "smoke", at, (m) => {
    m.setFloat("variable.size", size);
    m.setColorRGBA("variable.color", color);
});
export const spark = (dim, at) => emit(dim, "spark", at);
export const ember = (dim, at) => emit(dim, "ember", at);
export const blood = (dim, at) => emit(dim, "blood", at);
export const shard = (dim, at) => emit(dim, "shard", at);
export function sound(dim, id, at, volume = 1, pitch = 1) {
    try {
        dim.playSound(id, at, { volume, pitch });
    }
    catch {
        // ignore
    }
}
