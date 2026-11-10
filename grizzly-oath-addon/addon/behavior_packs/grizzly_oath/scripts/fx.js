// Particle + sound helpers. Every call is wrapped: a particle in an unloaded chunk must never
// break a skill half-way through. Art lives in textures/particle/grizzly_oath_fx.png (see
// tools/fx_assets.py for what each particle looks like).
import { MolangVariableMap } from "@minecraft/server";
export const RED = { red: 1, green: 0.1, blue: 0.07, alpha: 1 };
export const HOT = { red: 1, green: 0.62, blue: 0.45, alpha: 1 };
export const WHITE_HOT = { red: 1, green: 0.9, blue: 0.82, alpha: 1 };
export const DEEP_RED = { red: 0.62, green: 0.02, blue: 0.04, alpha: 0.95 };
export const BLACK = { red: 0.05, green: 0.01, blue: 0.015, alpha: 0.8 };
export const BLACK_FLAME = { red: 0.16, green: 0.02, blue: 0.03, alpha: 0.9 };
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
/** Anime 4-point impact sparkle. */
export const star = (dim, at, size, color = HOT, life = 0.16) => emit(dim, "star", at, (m) => {
    m.setFloat("variable.size", size);
    m.setFloat("variable.life", life);
    m.setFloat("variable.rot", Math.random() * 90);
    m.setColorRGBA("variable.color", color);
});
/** Burst of hot spark streaks flying outward. */
export const sparks = (dim, at, count = 8, speed = 1) => emit(dim, "sparks", at, (m) => {
    m.setFloat("variable.count", count);
    m.setFloat("variable.speed", speed);
});
/** Crescent slash that draws itself in (two layers: red rim + hot core). */
export function slash(dim, at, size, rot, color = RED, life = 0.2) {
    emit(dim, "slash", at, (m) => {
        m.setFloat("variable.size", size);
        m.setFloat("variable.rot", rot);
        m.setFloat("variable.life", life);
        m.setColorRGBA("variable.color", color);
    });
    emit(dim, "slash", at, (m) => {
        m.setFloat("variable.size", size * 0.78);
        m.setFloat("variable.rot", rot);
        m.setFloat("variable.life", life * 0.9);
        m.setColorRGBA("variable.color", WHITE_HOT);
    });
}
export const clawFlash = (dim, at, size, rot, color = RED) => emit(dim, "claw_flash", at, (m) => {
    m.setFloat("variable.size", size);
    m.setFloat("variable.rot", rot);
    m.setFloat("variable.life", 0.28);
    m.setColorRGBA("variable.color", color);
});
/** Glowing streak stretched along a direction (energy trails, claw paths, afterimages). */
export const streak = (dim, at, dir, len, wid, color, life = 0.3) => emit(dim, "streak", at, (m) => {
    m.setVector3("variable.dir", dir);
    m.setFloat("variable.len", len);
    m.setFloat("variable.wid", wid);
    m.setFloat("variable.life", life);
    m.setColorRGBA("variable.color", color);
});
/** Flat shockwave ring on the ground. */
export const ring = (dim, at, radius, life, color) => emit(dim, "ring", at, (m) => {
    m.setFloat("variable.radius", radius);
    m.setFloat("variable.life", life);
    m.setColorRGBA("variable.color", color);
});
/** Flat radial ground cracks (visual only, blocks are untouched). */
export const crack = (dim, at, radius, color, life = 1.2) => emit(dim, "crack", at, (m) => {
    m.setFloat("variable.radius", radius);
    m.setFloat("variable.life", life);
    m.setColorRGBA("variable.color", color);
});
export const smoke = (dim, at, size, color = BLACK) => emit(dim, "smoke", at, (m) => {
    m.setFloat("variable.size", size);
    m.setColorRGBA("variable.color", color);
});
/** Dust kicked outward along a direction. */
export const dust = (dim, at, dir, speed, size) => emit(dim, "dust", at, (m) => {
    m.setVector3("variable.dir", dir);
    m.setFloat("variable.speed", speed);
    m.setFloat("variable.size", size);
});
/** Upright dark-crimson flame tongue. */
export const flame = (dim, at, size, color = BLACK_FLAME) => emit(dim, "flame", at, (m) => {
    m.setFloat("variable.size", size);
    m.setColorRGBA("variable.color", color);
});
export const ember = (dim, at) => emit(dim, "ember", at);
export const blood = (dim, at) => emit(dim, "blood", at);
export const shard = (dim, at, count = 8) => emit(dim, "shard", at, (m) => m.setFloat("variable.count", count));
export function sound(dim, id, at, volume = 1, pitch = 1) {
    try {
        dim.playSound(id, at, { volume, pitch });
    }
    catch {
        // ignore
    }
}
