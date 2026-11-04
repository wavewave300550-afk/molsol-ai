import { BALANCE } from "./balance.js";
import { startAction, startDive, tickDying, tickRun, vitruvianRadius } from "./abilities.js";
import { centerOf, hpFrac, isLiving, isProtectedPlayer, now, playersNear, rayClear, safe, sec, } from "./boss.js";
import { add, dist, hdist, norm, sub, v3 } from "./vec.js";
/** How often (ticks) the boss reconsiders its special attacks while chasing. */
const DECIDE_EVERY = 8;
function validTarget(s, t) {
    if (!isLiving(t) || isProtectedPlayer(t))
        return false;
    if (t.dimension.id !== s.entity.dimension.id)
        return false;
    return dist(t.location, s.entity.location) <= BALANCE.boss.leash_range;
}
function nearestPlayer(s) {
    let best;
    let bd = Infinity;
    for (const p of playersNear(s, BALANCE.boss.aggro_range)) {
        if (isProtectedPlayer(p))
            continue;
        const d = dist(p.location, s.entity.location);
        if (d < bd) {
            bd = d;
            best = p;
        }
    }
    return best;
}
function ready(s, a) {
    return now() >= s.ready[a];
}
function lineOfSight(s, t) {
    const from = add(s.entity.location, v3(0, 3.0, 0));
    const to = centerOf(t);
    const d = sub(to, from);
    const l = Math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z);
    return rayClear(s, from, norm(d), l) >= l - 0.6;
}
function pick(options) {
    const total = options.reduce((a, [, w]) => a + w, 0);
    if (total <= 0)
        return undefined;
    let r = Math.random() * total;
    for (const [a, w] of options) {
        r -= w;
        if (r <= 0)
            return a;
    }
    return options[options.length - 1][0];
}
export function think(s) {
    if (s.dying) {
        tickDying(s);
        return;
    }
    if (s.run) {
        tickRun(s);
        return;
    }
    if (!validTarget(s, s.target))
        s.target = nearestPlayer(s);
    // phase change has priority over everything else
    if (s.phase === 1 && hpFrac(s) <= BALANCE.boss.phase2_at) {
        startAction(s, "transform");
        return;
    }
    const t = s.target;
    if (!validTarget(s, t)) {
        s.target = undefined;
        if (now() >= s.nextFlourish && safe(() => s.entity.isOnGround) !== false)
            startAction(s, "flourish");
        return;
    }
    if (now() < s.gapUntil || now() < s.nextDecision)
        return;
    s.nextDecision = now() + DECIDE_EVERY;
    const d = hdist(t.location, s.entity.location);
    const g = BALANCE.gear_volley;
    const options = [];
    if (d <= BALANCE.quake.range && ready(s, "quake"))
        options.push(["quake", 3]);
    if (s.phase === 2 && d >= BALANCE.dive.range_min && d <= BALANCE.dive.range_max && ready(s, "dive"))
        options.push(["dive", 3]);
    if (d <= BALANCE.vitruvian.range && d <= vitruvianRadius(s) + 3 && ready(s, "vitruvian"))
        options.push(["vitruvian", 2]);
    if (d >= g.range_min && d <= g.range_max && ready(s, "gear_volley") && lineOfSight(s, t)) {
        options.push(["gear_volley", d > 9 ? 4 : 1]);
    }
    // at melee range the vanilla compass slash does most of the work: specials only sometimes
    if (!options.length || (d < 3.2 && Math.random() < 0.5))
        return;
    const a = pick(options);
    if (!a)
        return;
    if (a === "dive")
        startDive(s);
    else
        startAction(s, a);
}
export { sec };
