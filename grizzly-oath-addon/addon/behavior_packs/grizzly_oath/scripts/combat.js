// Targeting, damage, knockback, bleeding and the add-on's temporary visual entities.
import { EntityDamageCause, GameMode, system, world } from "@minecraft/server";
import { FX_FAMILY, PROTECTED_TYPES, TUNING } from "./config.js";
import { blood } from "./fx.js";
import { fxEntities, now } from "./state.js";
import { len, sub, up, v } from "./vec.js";
export function isEnemy(caster, e) {
    try {
        if (!e.isValid || e.id === caster.id)
            return false;
        if (PROTECTED_TYPES.has(e.typeId) || e.typeId.startsWith("grizzly_oath:"))
            return false;
        if (!e.getComponent("minecraft:health"))
            return false;
        if (e.typeId === "minecraft:player") {
            if (!world.gameRules.pvp)
                return false;
            const mode = e.getGameMode();
            return mode !== GameMode.Creative && mode !== GameMode.Spectator;
        }
        const tame = e.getComponent("minecraft:tameable");
        if (tame && tame.isTamed)
            return false; // never hurt pets (anyone's)
        return true;
    }
    catch {
        return false;
    }
}
export function enemiesNear(caster, center, radius) {
    try {
        return caster.dimension
            .getEntities({
            location: center,
            maxDistance: radius,
            excludeFamilies: ["inanimate", FX_FAMILY],
            excludeTypes: ["minecraft:item", "minecraft:xp_orb"],
        })
            .filter((e) => isEnemy(caster, e));
    }
    catch {
        return [];
    }
}
/** Point roughly at the middle of an entity's body. */
export function bodyCenter(e) {
    try {
        const head = e.getHeadLocation();
        return v(e.location.x, (e.location.y + head.y) / 2, e.location.z);
    }
    catch {
        return up(e.location, 0.8);
    }
}
export function hurt(caster, e, amount) {
    try {
        e.applyDamage(amount, { cause: EntityDamageCause.entityAttack, damagingEntity: caster });
    }
    catch {
        // entity died / unloaded this tick
    }
}
export function push(e, from, horizontal, vertical) {
    const d = sub(e.location, from);
    const l = Math.max(0.001, len(v(d.x, 0, d.z)));
    try {
        e.applyKnockback({ x: (d.x / l) * horizontal, z: (d.z / l) * horizontal }, vertical);
    }
    catch {
        // some entities (e.g. riding) reject knockback
    }
}
const bleeds = new Map();
export function addBleed(caster, e) {
    const t = now();
    const old = bleeds.get(e.id);
    bleeds.set(e.id, {
        entity: e,
        caster,
        until: t + TUNING.rend.bleedTicks,
        nextHit: old ? old.nextHit : t + 20,
        nextDrip: t,
    });
}
export function isBleeding(e) {
    return bleeds.has(e.id);
}
export function tickBleeds(t) {
    for (const [id, b] of bleeds) {
        if (!b.entity.isValid || t > b.until) {
            bleeds.delete(id);
            continue;
        }
        if (t >= b.nextDrip) {
            b.nextDrip = t + 5;
            blood(b.entity.dimension, bodyCenter(b.entity));
        }
        if (t >= b.nextHit) {
            b.nextHit = t + 20;
            try {
                if (b.caster.isValid) {
                    b.entity.applyDamage(TUNING.rend.bleedDamage, { cause: EntityDamageCause.magic, damagingEntity: b.caster });
                }
                else {
                    b.entity.applyDamage(TUNING.rend.bleedDamage, { cause: EntityDamageCause.magic });
                }
            }
            catch {
                bleeds.delete(id);
            }
        }
    }
}
// ---------------------------------------------------------------- temporary visual entities
export function spawnFx(owner, id, at, yaw, lifeTicks) {
    let e;
    try {
        e = owner.dimension.spawnEntity(id, at, { initialRotation: yaw });
    }
    catch {
        return undefined;
    }
    const rec = { entity: e, owner: owner.id, removeAt: now() + lifeTicks };
    fxEntities.set(e.id, rec);
    // exact removal when the animation ends; sweepFx() and the entity's own despawn timer are backups
    system.runTimeout(() => {
        try {
            if (e.isValid)
                e.remove();
        }
        catch {
            // already gone
        }
        fxEntities.delete(e.id);
    }, lifeTicks);
    return e;
}
/** Removes every visual entity whose time is up (or all of an owner's, or all). */
export function sweepFx(t, opts = {}) {
    for (const [id, rec] of fxEntities) {
        if (opts.all || (opts.owner && rec.owner === opts.owner) || t >= rec.removeAt || !rec.entity.isValid) {
            try {
                if (rec.entity.isValid)
                    rec.entity.remove();
            }
            catch {
                // already gone
            }
            fxEntities.delete(id);
        }
    }
}
/** Removes leftovers from a previous session (e.g. the world was closed mid-Ultimate). */
export function removeOrphanFx() {
    let n = 0;
    for (const dimId of ["overworld", "nether", "the_end"]) {
        let dim;
        try {
            dim = world.getDimension(dimId);
        }
        catch {
            continue;
        }
        try {
            for (const e of dim.getEntities({ families: [FX_FAMILY] })) {
                if (fxEntities.has(e.id))
                    continue;
                e.remove();
                n++;
            }
        }
        catch {
            // dimension not ready yet
        }
    }
    return n;
}
