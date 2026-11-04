import { MolangVariableMap } from "@minecraft/server";
/**
 * Particle and sound helpers.  Every particle the scripts emit goes through `particle()`, which keeps a
 * per-tick budget (phones stay smooth even when several attacks overlap) and counters the smoke test reads.
 */
export const FX_BUDGET_PER_TICK = 14;
export const fxStats = { tick: -1, thisTick: 0, maxPerTick: 0, total: 0, dropped: 0 };
export function fxTick(tick) {
    if (fxStats.tick !== tick) {
        fxStats.tick = tick;
        fxStats.thisTick = 0;
    }
}
export const PFX = {
    spark: "esb:gold_spark",
    steam: "esb:steam_puff",
    pages: "esb:page_burst",
    shockwave: "esb:shockwave",
    dust: "esb:dust_ring",
    sigilEdge: "esb:sigil_edge",
    sigilBurst: "esb:sigil_burst",
    pillar: "esb:summon_pillar",
};
export function particle(dim, id, at, radius) {
    if (fxStats.thisTick >= FX_BUDGET_PER_TICK) {
        fxStats.dropped++;
        return false;
    }
    try {
        if (radius !== undefined) {
            const m = new MolangVariableMap();
            m.setFloat("variable.radius", radius);
            dim.spawnParticle(id, at, m);
        }
        else {
            dim.spawnParticle(id, at);
        }
    }
    catch {
        return false; // chunk not loaded / outside the world
    }
    fxStats.thisTick++;
    fxStats.total++;
    if (fxStats.thisTick > fxStats.maxPerTick)
        fxStats.maxPerTick = fxStats.thisTick;
    return true;
}
/** Vanilla sound events only (no custom audio files in the pack). */
export const SND = {
    shot: "mob.blaze.shoot",
    click: "random.click",
    boom: "random.explode",
    anvil: "random.anvil_land",
    anvilBreak: "random.anvil_break",
    charge: "beacon.activate",
    totem: "random.totem",
    flap: "mob.enderdragon.flap",
    bell: "block.bell.hit",
    page: "item.book.page_turn",
    levelup: "random.levelup",
    spell: "mob.evocation_illager.cast_spell",
    summon: "mob.evocation_illager.prepare_summon",
};
export function sound(dim, id, at, volume = 1, pitch = 1) {
    try {
        dim.playSound(id, at, { volume, pitch });
    }
    catch {
        /* ignore */
    }
}
