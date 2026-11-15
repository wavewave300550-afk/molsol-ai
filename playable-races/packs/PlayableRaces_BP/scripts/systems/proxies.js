import { system, world } from "@minecraft/server";
import { FAMILY_PROXY } from "../config.js";
import { warn } from "../core/util.js";
const proxies = new Map();
export function spawnProxy(owner, typeId, loc, o) {
    let e;
    try {
        e = (o.dim ?? owner.dimension).spawnEntity(typeId, loc, { initialRotation: o.yaw ?? 0, spawnEvent: o.event });
    }
    catch {
        return undefined;
    }
    const now = system.currentTick;
    const px = { id: e.id, entity: e, owner: owner.id, kind: o.kind, born: now, until: now + Math.max(1, o.ticks),
        tick: o.tick, hurt: o.hurt, end: o.end, data: o.data ?? {} };
    proxies.set(e.id, px);
    return px;
}
export function endProxy(px, reason) {
    if (!proxies.delete(px.id))
        return;
    try {
        px.end?.(px, reason);
    }
    catch (err) {
        warn(`proxy ${px.kind} end failed`, err);
    }
    const e = px.entity;
    system.run(() => {
        try {
            if (e.isValid)
                e.remove();
        }
        catch {
        }
    });
}
export function isProxy(e) {
    return proxies.has(e.id);
}
export function proxyOf(e) {
    return proxies.get(e.id);
}
export function proxiesOf(owner, kind) {
    return [...proxies.values()].filter((px) => px.owner === owner && (kind === undefined || px.kind === kind));
}
export function removeProxiesOf(owner, kind) {
    for (const px of proxiesOf(owner, kind))
        endProxy(px, "owner");
}
export function tickProxies() {
    if (proxies.size === 0)
        return;
    const now = system.currentTick;
    for (const px of [...proxies.values()]) {
        if (!px.entity.isValid) {
            endProxy(px, "removed");
            continue;
        }
        if (px.until <= now) {
            endProxy(px, "expired");
            continue;
        }
        try {
            px.tick?.(px, now - px.born);
        }
        catch (err) {
            warn(`proxy ${px.kind} tick failed`, err);
            endProxy(px, "removed");
        }
    }
}
export function proxyHurt(e, damage, attacker) {
    const px = proxies.get(e.id);
    if (!px)
        return;
    try {
        if (px.hurt?.(px, damage, attacker))
            endProxy(px, "killed");
    }
    catch (err) {
        warn(`proxy ${px.kind} hurt failed`, err);
    }
}
export function proxyDied(e) {
    const px = proxies.get(e.id);
    if (px)
        endProxy(px, "killed");
}
export function purgeOrphans() {
    let n = 0;
    for (const id of ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"]) {
        let list = [];
        try {
            list = world.getDimension(id).getEntities({ families: [FAMILY_PROXY] });
        }
        catch {
            continue;
        }
        for (const e of list) {
            if (proxies.has(e.id))
                continue;
            try {
                e.remove();
                n++;
            }
            catch {
            }
        }
    }
    return n;
}
