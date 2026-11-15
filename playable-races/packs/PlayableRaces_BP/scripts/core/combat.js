import { EntityDamageCause } from "@minecraft/server";
import { alive } from "./targets.js";
import { flat, sub, v3 } from "./util.js";
export function hurt(target, amount, caster, cause = EntityDamageCause.entityAttack) {
    if (!alive(target) || amount <= 0)
        return false;
    try {
        return target.applyDamage(amount, { cause, damagingEntity: caster });
    }
    catch {
        return false;
    }
}
export function knockFrom(target, from, strength, lift) {
    if (!target.isValid)
        return;
    const d = flat(sub(target.location, from));
    knock(target, v3(d.x * strength, 0, d.z * strength), lift);
}
export function knock(target, horizontal, lift) {
    if (!target.isValid)
        return;
    try {
        target.applyKnockback({ x: horizontal.x, z: horizontal.z }, lift);
    }
    catch {
        try {
            target.applyImpulse({ x: horizontal.x * 0.5, y: lift * 0.5, z: horizontal.z * 0.5 });
        }
        catch {
        }
    }
}
export function effect(target, id, ticks, amp = 0, particles = true) {
    if (!target.isValid)
        return;
    try {
        target.addEffect(id, Math.max(1, Math.floor(ticks)), { amplifier: amp, showParticles: particles });
    }
    catch {
    }
}
export function heal(target, amount) {
    try {
        const h = target.getComponent("minecraft:health");
        if (!h)
            return 0;
        const before = h.currentValue;
        h.setCurrentValue(Math.min(h.effectiveMax, before + amount));
        return h.currentValue - before;
    }
    catch {
        return 0;
    }
}
export function healthFrac(e) {
    try {
        const h = e.getComponent("minecraft:health");
        return h ? h.currentValue / Math.max(1, h.effectiveMax) : 1;
    }
    catch {
        return 1;
    }
}
