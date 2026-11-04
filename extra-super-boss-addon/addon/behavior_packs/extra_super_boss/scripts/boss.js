import { EntityDamageCause, GameMode, system } from "@minecraft/server";
import { BALANCE } from "./balance.js";
import { BOSS_ID } from "./spec.js";
import { add, angleDiff, clamp, localToWorld, turnToward, v3, yawTo } from "./vec.js";
export const BOSS_FAMILY = "esb_boss";
export const EXCLUDE_FAMILIES = ["esb_boss", "esb_fx", "esb_projectile", "inanimate"];
export const EXCLUDE_TYPES = ["minecraft:item", "minecraft:xp_orb", "minecraft:arrow", "minecraft:snowball",
    "minecraft:armor_stand", "minecraft:painting", "minecraft:leash_knot", "minecraft:boat", "minecraft:chest_boat",
    "minecraft:minecart", "minecraft:ender_pearl", "minecraft:fireball", "minecraft:small_fireball"];
export const sec = (s) => Math.round(s * 20);
export const now = () => system.currentTick;
export function safe(fn) {
    try {
        return fn();
    }
    catch {
        return undefined;
    }
}
export const bosses = new Map();
export function newState(e) {
    const t = now();
    return {
        entity: e,
        id: e.id,
        phase: 1,
        ready: { gear_volley: t + sec(3), quake: t + sec(2), vitruvian: t + sec(8), dive: t + sec(4) },
        gapUntil: t,
        nextDecision: t,
        locked: false,
        inAir: false,
        dying: false,
        dyingTick: 0,
        allowKill: false,
        invulnerable: false,
        nextFlourish: t + sec(BALANCE.flourish.every_min),
        yaw: safe(() => e.getRotation().y) ?? 0,
        props: {},
    };
}
// ------------------------------------------------------------------------------------------ properties & events
export function setProp(s, key, value) {
    if (s.props[key] === value)
        return;
    s.props[key] = value;
    safe(() => s.entity.setProperty(key, value));
}
export function event(s, name) {
    safe(() => s.entity.triggerEvent(name));
}
export function setAction(s, a) {
    setProp(s, "esb:action", a);
}
export function lock(s) {
    if (!s.locked) {
        s.locked = true;
        event(s, "esb:lock");
    }
}
/** Back to walking / melee. Phase 2 uses the faster group. Never while airborne or dying. */
export function unlock(s) {
    if (s.locked && !s.inAir && !s.dying) {
        s.locked = false;
        event(s, s.phase === 2 ? "esb:unlock_fast" : "esb:unlock");
    }
}
export function face(s, yaw) {
    s.yaw = yaw;
    safe(() => s.entity.setRotation({ x: 0, y: yaw }));
}
/** Turn toward a point by at most `step` degrees this tick. */
export function turnTo(s, p, step) {
    s.yaw = safe(() => s.entity.getRotation().y) ?? s.yaw;
    const goal = yawTo(s.entity.location, p);
    if (Math.abs(angleDiff(s.yaw, goal)) < 0.5)
        return;
    face(s, turnToward(s.yaw, goal, step));
}
export function at(s, o) {
    return localToWorld(s.entity.location, s.yaw, o.fwd, o.up, o.left);
}
// ------------------------------------------------------------------------------------------ queries
export function health(e) {
    return safe(() => e.getComponent("minecraft:health"));
}
export function hpFrac(s) {
    const h = health(s.entity);
    return h ? h.currentValue / Math.max(1, h.effectiveMax) : 1;
}
export function isLiving(e) {
    if (!e || !e.isValid)
        return false;
    const h = health(e);
    return !!h && h.currentValue > 0;
}
export function isProtectedPlayer(t) {
    if (t.typeId !== "minecraft:player")
        return false;
    const gm = safe(() => t.getGameMode());
    return gm === GameMode.Creative || gm === GameMode.Spectator;
}
export function isBoss(e) {
    return !!e && e.typeId === BOSS_ID;
}
export function centerOf(t) {
    return add(t.location, v3(0, t.typeId === "minecraft:player" ? 0.9 : 0.6, 0));
}
/** Living things the boss may hurt within a horizontal radius and a vertical band. */
export function victims(s, center, radius, below = 2, above = 3) {
    const list = safe(() => s.entity.dimension.getEntities({
        location: center, maxDistance: radius + above + 2, excludeFamilies: EXCLUDE_FAMILIES, excludeTypes: EXCLUDE_TYPES,
    })) ?? [];
    return list.filter((t) => {
        if (t.id === s.id || !isLiving(t) || isProtectedPlayer(t))
            return false;
        const dx = t.location.x - center.x;
        const dz = t.location.z - center.z;
        const dy = t.location.y - center.y;
        return Math.sqrt(dx * dx + dz * dz) <= radius && dy >= -below && dy <= above;
    });
}
export function playersNear(s, radius) {
    const list = safe(() => s.entity.dimension.getPlayers({ location: s.entity.location, maxDistance: radius })) ?? [];
    return list.filter((p) => isLiving(p));
}
export function hurt(s, t, amount) {
    return safe(() => t.applyDamage(amount, { cause: EntityDamageCause.entityAttack, damagingEntity: s.entity })) ?? false;
}
export function knockFrom(t, from, strength, lift) {
    const dx = t.location.x - from.x;
    const dz = t.location.z - from.z;
    const h = Math.sqrt(dx * dx + dz * dz) || 1;
    safe(() => t.applyKnockback({ x: (dx / h) * strength, z: (dz / h) * strength }, lift));
}
/** Y of the first solid block surface below `p` (searching `depth` blocks), or undefined. */
export function groundBelow(s, p, depth = 24) {
    const hit = safe(() => s.entity.dimension.getBlockFromRay(p, v3(0, -1, 0), {
        maxDistance: depth, includeLiquidBlocks: true, includePassableBlocks: false,
    }));
    return hit ? hit.block.location.y + 1 : undefined;
}
/** Free distance along a ray before a solid block (or maxD). */
export function rayClear(s, from, dir, maxD) {
    const hit = safe(() => s.entity.dimension.getBlockFromRay(from, dir, {
        maxDistance: maxD, includeLiquidBlocks: false, includePassableBlocks: false,
    }));
    if (!hit)
        return maxD;
    const p = add(hit.block.location, hit.faceLocation);
    const d = { x: p.x - from.x, y: p.y - from.y, z: p.z - from.z };
    return clamp(Math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z), 0, maxD);
}
export function message(players, key, withArgs) {
    for (const p of players)
        safe(() => p.sendMessage({ rawtext: [{ translate: key, with: withArgs }] }));
}
export function actionBar(players, key) {
    for (const p of players)
        safe(() => p.onScreenDisplay.setActionBar({ rawtext: [{ translate: key }] }));
}
