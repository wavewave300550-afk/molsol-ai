import { MolangVariableMap } from "@minecraft/server";
function molang(vars) {
    if (!vars)
        return undefined;
    const m = new MolangVariableMap();
    for (const [k, v] of Object.entries(vars))
        m.setFloat(`variable.${k}`, v);
    return m;
}
export function particle(dim, id, loc, vars) {
    try {
        dim.spawnParticle(id, loc, molang(vars));
    }
    catch {
    }
}
export function privateParticle(p, id, loc, vars) {
    try {
        p.spawnParticle(id, loc, molang(vars));
    }
    catch {
    }
}
export function sound(dim, id, loc, volume = 1, pitch = 1) {
    try {
        dim.playSound(id, loc, { volume, pitch });
    }
    catch {
    }
}
export function privateSound(p, id, volume = 1, pitch = 1) {
    try {
        p.playSound(id, { volume, pitch });
    }
    catch {
    }
}
export const RGB = {
    silver: { red: 0.85, green: 0.88, blue: 1.0 },
    crimson: { red: 1.0, green: 0.16, blue: 0.24 },
    gold: { red: 1.0, green: 0.8, blue: 0.3 },
    green: { red: 0.45, green: 1.0, blue: 0.45 },
    red: { red: 1.0, green: 0.3, blue: 0.3 },
};
export function rgb(c) {
    return { red: c.red, green: c.green, blue: c.blue };
}
export function pose(p, anim, stopExpression) {
    try {
        p.playAnimation(`animation.plrace.pose.${anim}`, stopExpression ? { stopExpression, blendOutTime: 0.15 } : { blendOutTime: 0.15 });
    }
    catch {
    }
}
