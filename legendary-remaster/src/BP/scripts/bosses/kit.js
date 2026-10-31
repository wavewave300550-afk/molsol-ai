import { effect, fightersNear, hurt, knock } from "../core/combat.js";
import { add, dirOfYaw, scale } from "../core/vec.js";
/** Damage every fighter near `center` (radius `reach`) for whom `test` holds. Returns the players hit. */
export function strike(b, center, reach, test, dmg, o = {}) {
    const out = [];
    for (const p of fightersNear(b.dim, center, reach)) {
        if (o.once?.has(p.id))
            continue;
        if (!test(p))
            continue;
        o.once?.add(p.id);
        hurt(p, dmg, b.entity, o.cause);
        if (o.knock || o.up)
            knock(p, o.from ?? b.pos, o.knock ?? 0, o.up ?? 0);
        for (const [id, ticks, amp] of o.effects ?? [])
            effect(p, id, ticks, amp);
        if (o.fire) {
            try {
                p.setOnFire(o.fire, true);
            }
            catch {
                // ignore
            }
        }
        out.push(p);
    }
    return out;
}
/** Point `d` blocks in front of the being (plus height h). */
export function ahead(b, d, h = 0, side = 0) {
    const f = dirOfYaw(b.yaw);
    const s = dirOfYaw(b.yaw + 90);
    return add(add({ x: b.pos.x, y: b.pos.y + h, z: b.pos.z }, scale(f, d)), scale(s, side));
}
/** Predict where a player will be in `ticks` ticks (linear). */
export function lead(p, ticks) {
    try {
        const v = p.getVelocity();
        return { x: p.location.x + v.x * ticks, y: p.location.y, z: p.location.z + v.z * ticks };
    }
    catch {
        return { ...p.location };
    }
}
