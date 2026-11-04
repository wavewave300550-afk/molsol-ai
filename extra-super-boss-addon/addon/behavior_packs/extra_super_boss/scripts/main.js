/**
 * Extra Super Boss - Boss 1: Leonardo da Vinci (esb:da_vinci)
 *
 * Vanilla AI walks him around and swings the compass (minecraft:behavior.delayed_attack); this script
 * adds the boss fight on top: intro, gear volley, gauntlet quake, Vitruvian judgement, the phase 2
 * transformation at 50% health with the ornithopter dive, and a scripted death.  Visual state reaches the
 * client through the synced properties esb:action and esb:phase, which drive the animation controllers.
 */
import { EntityDamageCause, EntityInitializationCause, system, world } from "@minecraft/server";
import { beginDying, endAction, forceGround, removeSigil, startAction } from "./abilities.js";
import { think } from "./brain.js";
import { BOSS_IDS, bosses, event, isBoss, newState, safe, setProp } from "./boss.js";
import { beginDyingE, bulbBurst, endE, isStunned, onDynamoDestroyed, releaseChair, startIntroE } from "./edison.js";
import { fxTick } from "./fx.js";
import { registerItems } from "./items.js";
import { BALANCE } from "./balance.js";
import { BOSS_ID, DYNAMO_ID, EDISON_ID, VOLT_BULB_ID } from "./spec.js";
function dying(s) {
    if (s.kind === "edison")
        beginDyingE(s);
    else
        beginDying(s);
}
function cleanup(s) {
    removeSigil(s);
    if (s.kind === "edison") {
        releaseChair(s);
        if (s.dynamo?.isValid)
            safe(() => s.dynamo.remove());
    }
}
const INTRO_FLAG = "esb:intro_done";
function register(e, fresh = false) {
    if (!e.isValid || !BOSS_IDS.includes(e.typeId))
        return undefined;
    const known = bosses.get(e.id);
    if (known) {
        known.entity = e;
        return known;
    }
    const s = newState(e, e.typeId === EDISON_ID ? "edison" : "da_vinci");
    bosses.set(e.id, s);
    const phase = safe(() => e.getProperty("esb:phase"));
    s.phase = phase === 2 ? 2 : 1;
    const action = safe(() => e.getProperty("esb:action"));
    // normalise after a reload: on the ground, free to move, no half-finished action
    event(s, "esb:to_ground");
    s.locked = true;
    for (const [k, v] of [["esb:action", "none"], ["esb:phase", s.phase]]) {
        s.props[k] = "__unset__";
        setProp(s, k, v);
    }
    if (action === "death") {
        dying(s);
        return s;
    }
    if (fresh && !safe(() => e.getDynamicProperty(INTRO_FLAG))) {
        safe(() => e.setDynamicProperty(INTRO_FLAG, true));
        s.locked = false; // so startAction really sends esb:lock (a fresh spawn starts in the free group)
        if (s.kind === "edison")
            startIntroE(s);
        else
            startAction(s, "intro");
        return s;
    }
    s.locked = true;
    if (s.kind === "edison") {
        // a reloaded Edison finds his Dynamo again (the nearest one within 32 blocks)
        const d = safe(() => e.dimension.getEntities({ type: DYNAMO_ID, location: e.location, maxDistance: 32, closest: 1 }))?.[0];
        if (d)
            s.dynamo = d;
        endE(s);
    }
    else
        endAction(s);
    return s;
}
function scan() {
    for (const id of ["overworld", "nether", "the_end"]) {
        const dim = safe(() => world.getDimension(id));
        for (const type of [BOSS_ID, EDISON_ID]) {
            const list = dim ? safe(() => dim.getEntities({ type })) ?? [] : [];
            for (const e of list)
                register(e);
        }
    }
}
world.afterEvents.entitySpawn.subscribe(({ entity, cause }) => {
    if (BOSS_IDS.includes(entity.typeId))
        register(entity, cause !== EntityInitializationCause.Loaded);
});
world.afterEvents.entityLoad.subscribe(({ entity }) => {
    if (BOSS_IDS.includes(entity.typeId))
        register(entity);
});
world.afterEvents.entityRemove.subscribe(({ removedEntityId }) => {
    const s = bosses.get(removedEntityId);
    if (s)
        cleanup(s);
    bosses.delete(removedEntityId);
});
world.afterEvents.entityDie.subscribe(({ deadEntity }) => {
    const id = deadEntity.id;
    const s = bosses.get(id);
    if (s) {
        cleanup(s);
        bosses.delete(id);
        return;
    }
    // Edison's Dynamo destroyed: he is unplugged
    for (const b of bosses.values())
        if (b.dynamo && b.dynamo.id === id)
            onDynamoDestroyed(b);
});
// Edison's thrown bulbs shatter into a small electric burst
world.afterEvents.projectileHitBlock.subscribe((ev) => {
    if (ev.projectile?.typeId !== VOLT_BULB_ID)
        return;
    bulbBurst(ev.source ? bosses.get(ev.source.id) : undefined, ev.dimension, ev.location);
});
world.afterEvents.projectileHitEntity.subscribe((ev) => {
    if (ev.projectile?.typeId !== VOLT_BULB_ID)
        return;
    bulbBurst(ev.source ? bosses.get(ev.source.id) : undefined, ev.dimension, ev.location);
});
// whoever hurts him becomes his target; the last player to hit him gets the kill
world.afterEvents.entityHurt.subscribe(({ hurtEntity, damageSource }) => {
    const s = register(hurtEntity);
    const by = damageSource.damagingEntity;
    if (!s || s.dying || !by || !by.isValid || isBoss(by))
        return;
    if (by.typeId === "minecraft:player")
        s.killer = by;
    s.target = by;
}, { entityTypes: [BOSS_ID, EDISON_ID] });
// a hit that would kill him is cancelled and turned into the death sequence; he cannot be hurt while
// dying, during the intro or while transforming.  (restricted mode: changes are deferred)
world.beforeEvents.entityHurt.subscribe((ev) => {
    const e = ev.hurtEntity;
    const s = bosses.get(e.id);
    if (!s || s.allowKill)
        return;
    if (s.dying || s.invulnerable) {
        ev.cancel = true;
        return;
    }
    if (ev.damageSource.cause === EntityDamageCause.void)
        return;
    if (isStunned(s))
        ev.damage *= BALANCE.edison.dynamo.stun_damage_mult; // unplugged: he takes extra damage
    const hp = safe(() => e.getComponent("minecraft:health").currentValue);
    if (hp !== undefined && ev.damage >= hp) {
        ev.cancel = true;
        const id = e.id;
        const by = ev.damageSource.damagingEntity;
        system.run(() => {
            const st = bosses.get(id) ?? (e.isValid ? register(e) : undefined);
            if (!st)
                return;
            if (by && by.isValid && by.typeId === "minecraft:player")
                st.killer = by;
            dying(st);
        });
    }
});
registerItems();
let ticks = 0;
system.runInterval(() => {
    ticks++;
    fxTick(system.currentTick);
    if (ticks === 1 || ticks % 40 === 0)
        scan();
    for (const [id, s] of bosses) {
        if (!s.entity.isValid) {
            cleanup(s);
            bosses.delete(id);
            continue;
        }
        try {
            think(s);
        }
        catch (err) {
            // never let one bad tick stop the loop: put him back in a safe state
            console.warn(`[Extra Super Boss] ${String(err)}`);
            forceGround(s);
            if (!s.dying) {
                s.run = undefined;
                s.invulnerable = false;
                s.locked = true;
                if (s.kind === "edison")
                    endE(s);
                else
                    endAction(s);
            }
        }
    }
}, 1);
