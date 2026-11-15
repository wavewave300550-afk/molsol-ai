import { EntityDamageCause, Player, system } from "@minecraft/server";
import { ENTITY_EXUVIA, EXPLOSION_CAUSES, FAMILY_PROXY } from "../config.js";
import { message, refreshForm, startChannel, tempForm } from "../core/abilities.js";
import { effect, hurt, knock } from "../core/combat.js";
import { isMoving } from "../core/env.js";
import { particle, privateParticle, privateSound, sound } from "../core/fx.js";
import { flag, get, hasFlag } from "../core/session.js";
import { alive, enemiesAlongSegment, enemiesNear, eye } from "../core/targets.js";
import { after } from "../core/tasks.js";
import { add, angleBetween, flat, meter, mul, sub, v3 } from "../core/util.js";
import { spawnProxy } from "../systems/proxies.js";
const OVERLOAD_AT = 25;
const RECOVER_AT = 60;
const sensed = new Map();
function clarity(s) {
    return s.data.res.clarity ?? 100;
}
function setClarity(s, v) {
    s.data.res.clarity = Math.max(0, Math.min(100, v));
    s.dirty = true;
}
export function overloaded(s) {
    return s.data.st.xen === "overloaded";
}
function coupled(p) {
    return p.isOnGround || p.isInWater;
}
function dark(p) {
    try {
        return p.dimension.getLightLevel(eye(p)) < 7;
    }
    catch {
        return false;
    }
}
function speedOf(e) {
    try {
        const v = e.getVelocity();
        return Math.hypot(v.x, v.z) + Math.abs(v.y) * 0.3;
    }
    catch {
        return 0;
    }
}
function feel(p, s, radius, opts) {
    const view = flat(p.getViewDirection());
    let list = [];
    try {
        list = p.dimension.getEntities({ location: p.location, maxDistance: radius, excludeFamilies: ["inanimate", FAMILY_PROXY],
            excludeTypes: ["minecraft:item", "minecraft:xp_orb", "minecraft:arrow", "minecraft:painting"] });
    }
    catch {
        return { count: 0, arrow: "", dist: 0 };
    }
    let count = 0;
    let best;
    const airborne = !coupled(p);
    for (const e of list) {
        if (e.id === p.id || !alive(e))
            continue;
        const to = sub(e.location, p.location);
        const d = Math.hypot(to.x, to.y, to.z);
        let strength = 0;
        const moving = speedOf(e) > 0.03;
        let grounded = true;
        try {
            grounded = e.isOnGround || e.isInWater;
        }
        catch {
            grounded = true;
        }
        if (e instanceof Player && e.isSneaking && d > 3)
            continue;
        if (moving && grounded)
            strength = 1;
        else if (moving && d < 4)
            strength = 0.5;
        else if (d < opts.stillToo)
            strength = 0.35;
        if (strength === 0)
            continue;
        count++;
        if (count > 14)
            continue;
        const jitter = (1 - strength) * 1.4 + (airborne ? 1.4 : 0.35);
        const at = add(e.location, v3((Math.random() * 2 - 1) * jitter, 0.06, (Math.random() * 2 - 1) * jitter));
        privateParticle(p, strength >= 1 ? "plrace:vibration_ping" : "plrace:vibration_trace", at);
        if (opts.survey)
            sensed.set(e.id, { by: p.id, until: system.currentTick + 140 });
        if (strength >= 1 && (!best || d < best.d))
            best = { d, to };
    }
    let arrow = "";
    if (best) {
        const ang = angleBetween(view, v3(best.to.x, 0, best.to.z));
        const cross = view.x * best.to.z - view.z * best.to.x;
        arrow = ang < 45 ? "▲" : ang > 135 ? "▼" : cross > 0 ? "►" : "◄";
    }
    return { count, arrow, dist: best ? Math.round(best.d) : 0 };
}
function overload(p, s, loss, why) {
    setClarity(s, clarity(s) - loss);
    if (clarity(s) < OVERLOAD_AT && !overloaded(s)) {
        s.data.st.xen = "overloaded";
        s.dirty = true;
        effect(p, "slowness", 60, 0, false);
        message(s, `§c${why} - senses overloaded`, 60);
        privateSound(p, "mob.warden.clicking", 0.8, 0.6);
    }
}
const survey = {
    id: "foretarsal_survey",
    name: "Foretarsal Survey",
    short: "Survey",
    cooldown: 15,
    original: "Cooldown 15 s; raise the sensory forelimbs and analyse movement within ~12 blocks for ~5 s; approximate positions; movement and ground contact affect accuracy.",
    desc: "Raise the sensory forelimbs and read every vibration within 12 blocks for 5 s: moving creatures ping clearly at their approximate position, still ones only within 5 blocks (7 in darkness), sneaking players only within 3. Creatures you feel are 'sensed' for 7 s (Anamorphic Surge strikes them 25% harder). Off the ground the radius halves and positions blur. Impossible while Overloaded.",
    check({ s }) {
        return overloaded(s) ? "Senses overloaded - wait for clarity" : undefined;
    },
    cast({ p, s }) {
        tempForm(p, s, "survey", 100);
        flag(s, "survey", 100);
        privateSound(p, "mob.warden.listening", 0.7, 1.3);
        sound(p.dimension, "power.on.sculk_sensor", p.location, 0.5, 1.4);
        for (let i = 0; i < 10; i++) {
            after(i * 10 + 1, () => {
                if (!p.isValid || overloaded(s))
                    return;
                const r = feel(p, s, coupled(p) ? 12 : 6, { survey: true, stillToo: dark(p) ? 7 : 5 });
                message(s, `§dSurvey: §f${r.count} §7vibration${r.count === 1 ? "" : "s"}${r.arrow ? ` §8| §fstrongest ${r.arrow} ${r.dist}m` : ""}`, 14);
            }, p.id, "survey");
        }
        return true;
    },
};
const exuvia = {
    id: "exuvia_proxy",
    name: "Exuvia Proxy",
    short: "Exuvia",
    cooldown: 28,
    original: "Cooldown 28 s; shed the exoskeleton; the shell keeps the character's look, diverts hostile creatures or absorbs attacks; the character escapes with a molting animation.",
    desc: "Split your dorsal plates and step out of your own exoskeleton. The shed exuvia stays behind for 8 s with your shape: hostile mobs nearby are provoked into attacking it and it soaks up to 16 damage; whatever strikes it is sensed. You spring free with Speed II as a soft TENERAL body (+20% damage taken for 4 s), after which the new cuticle hardens (Resistance I for 6 s).",
    cast({ p, s }) {
        const yaw = p.getRotation().y;
        const px = spawnProxy(p, ENTITY_EXUVIA, p.location, {
            kind: "exuvia",
            ticks: 160,
            yaw,
            hurt: (_px, _dmg, attacker) => {
                if (attacker && attacker.id !== p.id)
                    sensed.set(attacker.id, { by: p.id, until: system.currentTick + 140 });
                particle(_px.entity.dimension, "plrace:chitin_shards", add(_px.entity.location, v3(0, 1, 0)));
            },
            end: (dead, reason) => {
                try {
                    const loc = dead.entity.isValid ? dead.entity.location : undefined;
                    if (loc) {
                        particle(dead.entity.dimension, "plrace:chitin_shards", add(loc, v3(0, 0.9, 0)));
                        sound(dead.entity.dimension, reason === "killed" ? "mob.armadillo.scute_drop" : "mob.silverfish.step", loc, 1, 0.7);
                    }
                }
                catch {
                }
            },
        });
        if (!px)
            return "No room to shed here";
        for (const m of enemiesNear(p, p.location, 14)) {
            if (m.typeId === "minecraft:player")
                continue;
            try {
                m.applyDamage(1, { cause: EntityDamageCause.entityAttack, damagingEntity: px.entity });
            }
            catch {
            }
        }
        particle(p.dimension, "plrace:molt_fluid", add(p.location, v3(0, 1.2, 0)));
        sound(p.dimension, "mob.armadillo.scute_drop", p.location, 1, 0.6);
        sound(p.dimension, "mob.silverfish.say", p.location, 0.6, 0.6);
        const back = mul(flat(p.getViewDirection()), -1);
        knock(p, mul(back, 1.15), 0.36);
        tempForm(p, s, "teneral", 80);
        flag(s, "teneral", 80);
        effect(p, "speed", 80, 1, false);
        after(80, () => {
            if (!p.isValid)
                return;
            effect(p, "resistance", 120, 0, false);
            message(s, "§dThe new cuticle hardens", 40);
            privateSound(p, "mob.armadillo.roll", 0.8, 1.2);
        }, p.id, "harden");
        message(s, "§dYou slip out of your own shell", 40);
        return true;
    },
};
const glide = {
    id: "interstitial_glide",
    name: "Interstitial Glide",
    short: "Glide",
    cooldown: 18,
    original: "Cooldown 18 s; compress the body and move rapidly along the ground ~5 blocks; body flattens, legs fold; must not pass through walls.",
    desc: "Flatten your segmented body, fold your legs and slide ~5 blocks along the ground where you look. Creatures you slip past are tripped (2 damage, Slowness II for 2 s) and you take half damage while flat. The slide is real movement: walls, doors and protected builds stop it; nothing is ever passed through.",
    check({ p }) {
        return p.isOnGround || p.isInWater ? undefined : "Needs ground contact";
    },
    cast({ p, s }) {
        const dir = flat(p.getViewDirection());
        tempForm(p, s, "glide", 16);
        flag(s, "glide", 16);
        const hit = new Set();
        let last = { ...p.location };
        sound(p.dimension, "mob.silverfish.step", p.location, 1, 0.6);
        sound(p.dimension, "item.trident.riptide_1", p.location, 0.35, 1.8);
        startChannel(p, s, {
            ability: "interstitial_glide",
            mode: "block",
            until: system.currentTick + 11,
            tick: (_s2, p2, t) => {
                if (t < 9)
                    knock(p2, mul(dir, 0.62), 0);
                const now = { ...p2.location };
                for (const e of enemiesAlongSegment(p2, add(last, v3(0, 0.5, 0)), add(now, v3(0, 0.5, 0)), 1.3)) {
                    if (hit.has(e.id))
                        continue;
                    hit.add(e.id);
                    hurt(e, 2, p2);
                    effect(e, "slowness", 40, 1);
                }
                last = now;
                if (t % 2 === 0)
                    particle(p2.dimension, "plrace:step_dust", p2.location);
            },
            end: () => undefined,
        });
        return true;
    },
};
const SURGE_HITS = [12, 18, 24];
const surge = {
    id: "anamorphic_surge",
    name: "Anamorphic Surge",
    short: "Surge",
    cooldown: 40,
    original: "Cooldown 40 s; the articulated abdominal segments extend in sequence; the extended body strikes with increased reach and multiple timed impacts; progressive transformation, not a scale-up.",
    desc: "Your twelve abdominal segments telescope out one after another and the abdomen arches over your back, then strikes three times along your aim (6.5 block reach): 4, 4 and 6 damage, +25% against sensed creatures. The last strike injects through the stylet: Weakness for 4 s and Slowness for 2 s, and knocks targets back. You are slowed while the abdomen is extended.",
    cast({ p, s }) {
        tempForm(p, s, "surge", 34);
        effect(p, "slowness", 32, 1, false);
        sound(p.dimension, "mob.armadillo.roll", p.location, 1, 0.5);
        sound(p.dimension, "mob.spider.say", p.location, 0.7, 0.6);
        let n = 0;
        startChannel(p, s, {
            ability: "anamorphic_surge",
            mode: "block",
            until: system.currentTick + 32,
            tick: (_s2, p2, t) => {
                if (!SURGE_HITS.includes(t))
                    return;
                const last = n === SURGE_HITS.length - 1;
                n++;
                const from = eye(p2);
                const dir = p2.getViewDirection();
                const to = add(from, mul(dir, 6.5));
                let struck = 0;
                for (const e of enemiesAlongSegment(p2, from, to, 1.4)) {
                    const bonus = sensed.get(e.id)?.by === p2.id && (sensed.get(e.id)?.until ?? 0) > system.currentTick ? 1.25 : 1;
                    hurt(e, (last ? 6 : 4) * bonus, p2);
                    particle(p2.dimension, "plrace:surge_strike", add(e.location, v3(0, 1.1, 0)));
                    if (last) {
                        effect(e, "weakness", 80, 0);
                        effect(e, "slowness", 40, 0);
                        knock(e, mul(flat(dir), 1.1), 0.3);
                    }
                    struck++;
                }
                sound(p2.dimension, struck ? "mob.silverfish.hit" : "mob.spider.step", p2.location, 1, 0.8 + n * 0.15);
                if (last && struck)
                    message(_s2, `§dSurge: ${struck} struck`, 30);
            },
            end: (s2, p2, reason) => {
                if (reason !== "leave" && p2.isValid)
                    refreshForm(p2, s2);
            },
        });
        return true;
    },
};
export const xenentoma = {
    code: "004",
    key: "xenentoma",
    name: "Xenentoma",
    thai: "เซเนนโทมา",
    title: "The Eyeless Choir",
    color: "§d",
    tagline: "It does not see the world. It feels it move.",
    lore: [
        "The Xenentoma come from an undersoil lineage that never grew eyes or antennae. Their conical heads carry two false eyes - pale iridescent discs that see nothing - and their first pair of legs is held up like antennae, fringed with sensilla that read every footfall through stone.",
        "They grow by moulting: each shed skin adds a segment, and an adult drags twelve behind it. A Xenentoma that steps out of its own shell is soft and pale for a few heartbeats, then hardens again - and the empty exuvia it leaves behind is so perfect a likeness that predators keep attacking it long after the creature itself is gone.",
    ],
    strengths: ["Feels movement through the ground (no wallhack: approximate, close range, ground only)", "Immune to Blindness and Darkness", "Escapes by moulting; slides under danger", "Long-reach multi-hit abdomen strike"],
    weaknesses: ["Explosions and lightning overload its senses (and hurt 15% more)", "Senses fail in the air", "Soft and fragile right after moulting", "Abilities need clear senses"],
    passives: [
        { name: "Vibration Sense", desc: "On solid ground or in water, moving creatures within 8 blocks (10 when you stand still, +4 in darkness) send faint vibration rings only you can see, and the HUD shows the strongest tremor's direction. Airborne creatures and sneaking players are hard to feel." },
        { name: "Eyeless", desc: "No eyes to blind: Blindness and Darkness have no effect on you." },
        { name: "Stillness", desc: "Sneak motionless for 2 s: you go perfectly still (Invisibility while you stay still)." },
        { name: "Six-Point Landing", desc: "Fall damage -30%." },
        { name: "Sensory Clarity", desc: "0-100%. Explosions within 14 blocks and nearby lightning scramble it; below 25% you are Overloaded (no Vibration Sense, no Survey, cooldowns +20%) until it recovers to 60%. Recovers 4%/s (8%/s standing still)." },
    ],
    abilities: [survey, exuvia, glide, surge],
    focusItem: "plrace:focus_xenentoma",
    focusName: "Sensillum Focus",
    controls: ["Xenentoma: §fsneak and stand still§7 for 2 s to go still (Stillness)."],
    variant() {
        return "";
    },
    cooldownMul(_p, s) {
        return overloaded(s) ? 1.2 : 1;
    },
    init(_p, s, first) {
        if (first) {
            s.data.res.clarity = 100;
            s.data.st.xen = "clear";
            s.dirty = true;
        }
    },
    cleanup(_p, s) {
        delete s.data.res.clarity;
        delete s.data.st.xen;
    },
    release(s, _reason) {
        for (const [id, m] of sensed)
            if (m.by === s.id)
                sensed.delete(id);
    },
    tick20(p, s) {
        for (const id of ["blindness", "darkness"]) {
            try {
                if (p.getEffect(id))
                    p.removeEffect(id);
            }
            catch {
            }
        }
        const still = !isMoving(p) && p.isOnGround;
        setClarity(s, clarity(s) + (still ? 8 : 4));
        if (overloaded(s) && clarity(s) >= RECOVER_AT) {
            s.data.st.xen = "clear";
            s.dirty = true;
            message(s, "§dClarity returns - the ground speaks again", 40);
        }
        if (!overloaded(s) && coupled(p) && !hasFlag(s, "survey")) {
            const r = feel(p, s, 8 + (still ? 2 : 0) + (dark(p) ? 4 : 0), { survey: false, stillToo: dark(p) ? 4 : 0 });
            s.num.set("tremors", r.count);
            s.num.set("tremor_dir", "▲►▼◄".indexOf(r.arrow));
        }
        else
            s.num.set("tremors", -1);
        const now = system.currentTick;
        for (const [id, m] of sensed)
            if (m.until <= now)
                sensed.delete(id);
    },
    tick5(p, s) {
        const still = p.isSneaking && !isMoving(p) && p.isOnGround;
        const n = still ? (s.num.get("still") ?? 0) + 1 : 0;
        s.num.set("still", n);
        if (n >= 8) {
            effect(p, "invisibility", 12, 0, false);
            if (n === 8)
                message(s, "§7Still as the soil...", 30);
        }
    },
    hud(_p, s) {
        const c = Math.round(clarity(s));
        const head = overloaded(s) ? "§c§lOVERLOADED" : `§dClarity §f${meter(c / 100, 10)} ${c}%`;
        const tremors = s.num.get("tremors") ?? -1;
        const dir = "▲►▼◄"[s.num.get("tremor_dir") ?? -1] ?? "";
        const tail = tremors < 0 ? "§8senses off" : tremors === 0 ? "§8no tremors" : `§fTremors ${tremors} ${dir}`;
        return `${head} §8| ${tail}`;
    },
    onHurt(_p, s, ev) {
        const cause = ev.damageSource.cause;
        if (cause === "fall")
            ev.damage *= 0.7;
        if (EXPLOSION_CAUSES.has(cause))
            ev.damage *= 1.15;
        if (hasFlag(s, "teneral") && cause !== "fall")
            ev.damage *= 1.2;
        if (hasFlag(s, "glide"))
            ev.damage *= 0.5;
    },
    onExplosion(p, s, distance) {
        overload(p, s, Math.round(25 + 60 * (1 - distance / 14)), "The blast shakes the ground");
    },
};
export function isSensedBy(e, p) {
    const m = sensed.get(e.id);
    return !!m && m.by === p.id && m.until > system.currentTick;
}
export function xenentomaSession(p) {
    return get(p);
}
