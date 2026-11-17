import { MolangVariableMap } from "@minecraft/server";
/**
 * Particle and sound helpers.  Every particle the scripts emit goes through `particle()`, which
 * enforces a per-tick budget so the fire breath can never flood an iPhone with emitters, and
 * keeps counters the smoke test reads back.
 */
export const FX_BUDGET_PER_TICK = 12;
export const fxStats = { tick: -1, thisTick: 0, maxPerTick: 0, total: 0, dropped: 0 };
export function fxTick(tick) {
    if (fxStats.tick !== tick) {
        fxStats.tick = tick;
        fxStats.thisTick = 0;
    }
}
export function particle(dim, id, at, vars) {
    if (fxStats.thisTick >= FX_BUDGET_PER_TICK) {
        fxStats.dropped++;
        return false;
    }
    try {
        if (vars)
            dim.spawnParticle(id, at, vars);
        else
            dim.spawnParticle(id, at);
    }
    catch {
        return false; // chunk not loaded / out of world: ignore
    }
    fxStats.thisTick++;
    fxStats.total++;
    if (fxStats.thisTick > fxStats.maxPerTick)
        fxStats.maxPerTick = fxStats.thisTick;
    return true;
}
export function jetParticle(dim, at, dir, speed) {
    const m = new MolangVariableMap();
    m.setSpeedAndDirection("variable.jet", speed, dir);
    particle(dim, "dod:fire_jet", at, m);
}
export function sound(dim, id, at, volume = 1, pitch = 1) {
    try {
        dim.playSound(id, at, { volume, pitch });
    }
    catch {
        /* ignore */
    }
}
export const SND = {
    roarLayer: "mob.dod.red_dragon.roar_layer",
    hit: "mob.dod.red_dragon.hit",
    fireLoop: "mob.dod.red_dragon.fire_loop",
    fireHit: "mob.dod.red_dragon.fire_hit",
    flap: "mob.dod.red_dragon.flap",
    growl: "mob.dod.red_dragon.growl",
};
