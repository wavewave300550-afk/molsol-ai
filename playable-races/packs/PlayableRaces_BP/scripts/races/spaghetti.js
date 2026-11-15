import { system, world } from "@minecraft/server";
import { ENTITY_MEATBALL, FIRE_CAUSES } from "../config.js";
import { message, refreshForm, startChannel, tempForm } from "../core/abilities.js";
import { effect, hurt, knock, knockFrom } from "../core/combat.js";
import { onFire } from "../core/env.js";
import { particle, pose, privateParticle, privateSound, sound } from "../core/fx.js";
import { clearFlag, flag, hasFlag } from "../core/session.js";
import { aimTarget, ally, alive, chest, enemiesNear, eye } from "../core/targets.js";
import { add, angleBetween, dist, flat, meter, mul, norm, sub, v3 } from "../core/util.js";
import { endProxy, proxiesOf, spawnProxy } from "../systems/proxies.js";
const PASTA_FOODS = /(mushroom_stew|beetroot_soup|rabbit_stew|suspicious_stew|bread|baked_potato|cooked_beef|cooked_porkchop)/;
function sauce(s) {
    return s.data.res.sauce ?? 50;
}
function addSauce(s, n) {
    const before = sauce(s);
    s.data.res.sauce = Math.max(0, Math.min(100, before + n));
    s.dirty = true;
    if (before < 100 && sauce(s) >= 100)
        message(s, "§c§lSAUCY! §r§eyour next ability is empowered", 50);
}
function saucy(s) {
    if (sauce(s) < 100)
        return false;
    s.data.res.sauce = 0;
    s.dirty = true;
    return true;
}
const brittle = (s) => hasFlag(s, "brittle");
const meatballsOut = (s) => hasFlag(s, "meatballs");
function strand(p, a, b) {
    const d = sub(b, a);
    particle(p.dimension, "plrace:noodle_strand", a, { dx: d.x, dy: d.y, dz: d.z });
}
const touch = {
    id: "noodly_touch",
    name: "His Noodly Touch",
    short: "Touch",
    cooldown: 15,
    range: 7,
    cone: 18,
    needsTarget: false,
    original: "Cooldown 15 s, reach ~7 blocks; spaghetti strands extend to a target: grab, restrain or reposition enemies, or pull dropped items; visible extension and retraction; respects collision, line of sight and multiplayer.",
    desc: "Noodles lash out up to 7 blocks (5 while brittle). An enemy is wrapped: 3 damage, pulled toward you and held (Slowness IV, 1.5 s). A friendly player (PvP off) is BLESSED instead: Regeneration for 4 s and Slowness, Weakness, Poison and Mining Fatigue are wiped away. Nothing alive in reach? The strands gather dropped items from in front of you. SAUCY: 5 damage and a 2.5 s hold.",
    cast({ p, s }) {
        const reach = brittle(s) ? 5 : 7;
        const from = add(eye(p), v3(0, -0.4, 0));
        const target = aimTarget(p, reach, 18);
        if (target) {
            const big = saucy(s);
            strand(p, from, chest(target));
            hurt(target, big ? 5 : 3, p);
            const toMe = flat(sub(p.location, target.location));
            knock(target, mul(toMe, 1.1), 0.22);
            effect(target, "slowness", big ? 50 : 30, 3);
            sound(p.dimension, "mob.slime.attack", target.location, 1, 0.8);
            pose(p, "fsm_touch");
            return true;
        }
        let friend;
        for (const pl of p.dimension.getPlayers({ location: p.location, maxDistance: reach + 1 })) {
            if (!ally(p, pl))
                continue;
            if (angleBetween(p.getViewDirection(), sub(chest(pl), eye(p))) < 25)
                friend = pl;
        }
        if (friend) {
            strand(p, from, chest(friend));
            effect(friend, "regeneration", 80, 0);
            for (const bad of ["slowness", "weakness", "poison", "mining_fatigue"]) {
                try {
                    friend.removeEffect(bad);
                }
                catch {
                }
            }
            try {
                friend.onScreenDisplay.setActionBar("§eTouched by His Noodly Appendage");
            }
            catch {
            }
            sound(p.dimension, "random.orb", friend.location, 0.8, 1.4);
            pose(p, "fsm_touch");
            return true;
        }
        let items = [];
        try {
            items = p.dimension.getEntities({ type: "minecraft:item", location: p.location, maxDistance: reach });
        }
        catch {
            items = [];
        }
        const view = p.getViewDirection();
        items = items.filter((it) => angleBetween(view, sub(it.location, eye(p))) < 50).slice(0, 16);
        if (items.length) {
            for (const it of items) {
                strand(p, from, it.location);
                try {
                    it.teleport(add(p.location, v3(0, 0.6, 0)));
                }
                catch {
                }
            }
            sound(p.dimension, "random.pop", p.location, 0.8, 0.8);
            pose(p, "fsm_touch");
            message(s, `§eThe noodles bring you ${items.length} item${items.length > 1 ? "s" : ""}`, 30);
            return true;
        }
        return "Nothing within reach of your noodles";
    },
};
const dente = {
    id: "al_dente_reversal",
    name: "Al Dente Reversal",
    short: "Al Dente",
    cooldown: 22,
    original: "Cooldown 22 s; the flexible mass becomes rigid; strands interlock into a defensive structure; blocks or reduces an incoming attack and releases a reactive counterforce; distinct soft-to-rigid transition.",
    desc: "Every strand snaps rigid into a lattice of dry spaghetti for 2.5 s: you take 60% less damage, projectiles are stopped outright, and the first creature to strike you in melee is countered for 4 damage and thrown back. SAUCY: 3.5 s and a 6-damage counter.",
    cast({ p, s }) {
        const big = saucy(s);
        const t = big ? 70 : 50;
        flag(s, "dente", t);
        flag(s, "dente_counter", t);
        s.num.set("dente_power", big ? 6 : 4);
        refreshForm(p, s);
        sound(p.dimension, "random.anvil_land", p.location, 0.25, 1.9);
        particle(p.dimension, "plrace:dente_crack", add(p.location, v3(0, 1, 0)));
        return true;
    },
};
const RICOCHET_HITS = 3;
const ricochet = {
    id: "meatball_ricochet",
    name: "Meatball Ricochet",
    short: "Meatballs",
    cooldown: 28,
    original: "Cooldown 28 s; both meatballs separate and bounce between nearby targets, then return; distinct trajectories, target acquisition, damage, return, cleanup; temporary defensive trade-off while detached.",
    desc: "Both meatballs tear free (still tethered by noodles) and ricochet between enemies within 10 blocks: each strikes up to 3 times (4 damage, a splash of sauce), preferring different targets, then flies home. While they are away you take 20% more damage. If a target vanishes they pick another or return; if you die, leave or change dimension they are gone. SAUCY: 4 strikes each.",
    check({ p }) {
        return enemiesNear(p, p.location, 10).length ? undefined : "No targets for the meatballs";
    },
    cast({ p, s }) {
        const big = saucy(s);
        flag(s, "meatballs", 200);
        refreshForm(p, s);
        const side = v3(-p.getViewDirection().z, 0, p.getViewDirection().x);
        for (const k of [-1, 1]) {
            const start = add(add(p.location, v3(0, 1.0, 0)), mul(norm(side), 0.7 * k));
            const px = spawnProxy(p, ENTITY_MEATBALL, start, {
                kind: "meatball",
                ticks: 160,
                data: { hits: 0, max: big ? 4 : RICOCHET_HITS, side: k, visited: [], phase: "out", target: "" },
                tick: (m, age) => meatballTick(p, s, m, age),
            });
            if (!px)
                continue;
        }
        sound(p.dimension, "mob.slime.big", p.location, 1, 1.4);
        particle(p.dimension, "plrace:sauce_splash", add(p.location, v3(0, 1, 0)));
        return true;
    },
};
function meatballTick(p, s, m, age) {
    const e = m.entity;
    if (!p.isValid) {
        endProxy(m, "owner");
        return;
    }
    const d = m.data;
    const here = e.location;
    if (age % 4 === 0)
        strand(p, chest(p), here);
    let goal;
    if (d.phase === "out") {
        let t = d.target ? world.getEntity(d.target) : undefined;
        if (!alive(t)) {
            t = pick(p, here, d.visited, m);
            d.target = t ? t.id : "";
            if (!t)
                d.phase = "home";
        }
        goal = t ? chest(t) : here;
        if (t && dist(here, goal) < 0.9) {
            hurt(t, 4, p);
            knock(t, mul(flat(sub(t.location, p.location)), 0.5), 0.2);
            particle(e.dimension, "plrace:sauce_splash", goal);
            sound(e.dimension, "mob.goat.ram_impact", goal, 0.7, 1.6);
            d.hits++;
            d.visited.push(t.id);
            d.target = "";
            if (d.hits >= d.max)
                d.phase = "home";
        }
    }
    else
        goal = add(add(p.location, v3(0, 1.0, 0)), mul(v3(-p.getViewDirection().z, 0, p.getViewDirection().x), 0.7 * d.side));
    if (d.phase === "home" && dist(here, goal) < 1.0) {
        endProxy(m, "expired");
        if (proxiesOf(p.id, "meatball").length === 0) {
            clearFlag(s, "meatballs");
            refreshForm(p, s);
            message(s, "§eThe meatballs return", 30);
            sound(p.dimension, "mob.slime.small", p.location, 1, 1.2);
        }
        return;
    }
    const step = sub(goal, here);
    const L = Math.hypot(step.x, step.y, step.z);
    const speed = d.phase === "home" ? 1.1 : 0.85;
    const next = L <= speed ? goal : add(here, mul(step, speed / L));
    try {
        e.teleport(next, { facingLocation: goal });
    }
    catch {
        endProxy(m, "removed");
    }
}
function pick(p, from, visited, self) {
    const others = proxiesOf(p.id, "meatball").filter((x) => x.id !== self.id).map((x) => String(x.data.target));
    let best;
    let bestD = Infinity;
    for (const e of enemiesNear(p, from, 8)) {
        if (visited.includes(e.id))
            continue;
        if (dist(e.location, p.location) > 12)
            continue;
        const dd = dist(chest(e), from) + (others.includes(e.id) ? 4 : 0);
        if (dd < bestD) {
            bestD = dd;
            best = e;
        }
    }
    return best;
}
const REVEAL = 72;
const revelation = {
    id: "great_pasta_revelation",
    name: "The Great Pasta Revelation",
    short: "Revelation",
    cooldown: 50,
    original: "Cooldown 50 s; the whole body expands into a giant spiral of living spaghetti: rotating layers, meatballs orbiting in opposite directions, eyestalks rising; enemies pulled inward; a final sauce-powered shockwave; telegraphed area control; not a generic particle explosion.",
    desc: "Unfold into three rotating spiral layers of living spaghetti with both meatballs orbiting in opposite directions and your eyes raised above the vortex. For 3.3 s enemies within 9 blocks are dragged toward you and lashed (1 damage per 0.5 s, Slowness); then a sauce shockwave erupts: 8 damage within 5.5 blocks, thrown outward, Slowness II and Weakness for 3 s. You are slowed but take 30% less damage while unfolded. SAUCY: 11 damage.",
    cast({ p, s }) {
        const big = saucy(s);
        tempForm(p, s, "revelation", REVEAL + 6);
        flag(s, "revelation", REVEAL + 4);
        effect(p, "slowness", REVEAL, 2, false);
        sound(p.dimension, "mob.evocation_illager.prepare_summon", p.location, 0.8, 1.3);
        startChannel(p, s, {
            ability: "great_pasta_revelation",
            mode: "block",
            until: system.currentTick + REVEAL,
            tick: (_s2, p2, t) => {
                const c = p2.location;
                if (t % 8 === 0)
                    particle(p2.dimension, "plrace:pasta_vortex", add(c, v3(0, 0.1, 0)));
                if (t >= 4 && t < 66 && t % 4 === 0) {
                    for (const e of enemiesNear(p2, c, 9)) {
                        const dd = Math.max(1, dist(e.location, c));
                        knock(e, mul(flat(sub(c, e.location)), 0.42 + 0.04 * (9 - dd)), 0.05);
                        effect(e, "slowness", 20, 0);
                        if (t % 10 === 0)
                            hurt(e, 1, p2);
                    }
                }
                if (t === 66) {
                    for (const e of enemiesNear(p2, c, 5.5)) {
                        hurt(e, big ? 11 : 8, p2);
                        knockFrom(e, c, 1.6, 0.5);
                        effect(e, "slowness", 60, 1);
                        effect(e, "weakness", 60, 0);
                    }
                    particle(p2.dimension, "plrace:sauce_wave", add(c, v3(0, 0.2, 0)));
                    particle(p2.dimension, "plrace:sauce_splash", add(c, v3(0, 1.2, 0)));
                    sound(p2.dimension, "random.explode", c, 0.6, 1.4);
                    sound(p2.dimension, "mob.slime.big", c, 1, 0.6);
                }
            },
            end: (s2, p2, reason) => {
                clearFlag(s2, "revelation");
                if (reason !== "leave" && p2.isValid)
                    refreshForm(p2, s2);
            },
        });
        return true;
    },
};
export const spaghetti = {
    code: "005",
    key: "spaghetti",
    name: "Flying Spaghetti Monster",
    thai: "สปาเกตตีมอนสเตอร์บินได้",
    title: "The Noodly Existence",
    color: "§e",
    tagline: "Ridiculous. Impossible. Extremely well engineered.",
    lore: [
        "In 2005 a letter to a school board described a deity made of spaghetti and meatballs, invisible to science because it touches every measurement with His Noodly Appendage. Somewhere, it seems, the joke was taken literally.",
        "This one hovers a hand's breadth above the ground: a tangle of living pasta that knots itself into arms when it needs to hold something, two meatballs that are not entirely attached, two eyes that never agree on where to look, and sauce that flows wherever it pleases - including up.",
    ],
    strengths: ["Long-reach grabs, rescues and item gathering", "Hard counter to melee and arrows (Al Dente)", "Area control: pulls enemies in, then blasts them", "Elastic: halves fall damage; sneak in the air to parachute"],
    weaknesses: ["Fire makes it brittle (+25% fire damage, slower abilities, shorter reach)", "Softer while the meatballs are away (+20% damage)", "Lightest crest armour", "Ultimate needs time and roots it"],
    passives: [
        { name: "Noodly Float", desc: "Hovers a little above the ground. Not flight: hold SNEAK while falling to spread your strands and drift down slowly (Noodle Parachute)." },
        { name: "Elastic Form", desc: "Fall damage -50%." },
        { name: "Dual-Eye Awareness", desc: "One eye always watches your back: a hostile creature sneaking up behind you within 6 blocks is pointed out." },
        { name: "Flexible Appendages", desc: "Strands braid into arms only when you hold an item, so tools, weapons, shields and food work normally." },
        { name: "Sauce", desc: "0-100%: +2%/s, +15% for any meal and +40% for stews, soups, bread, baked potatoes and cooked meat. At 100% your next ability is SAUCY (empowered). Burning boils it away." },
    ],
    abilities: [touch, dente, ricochet, revelation],
    focusItem: "plrace:focus_spaghetti",
    focusName: "Holy Colander Focus",
    controls: ["Flying Spaghetti Monster: hold §fSNEAK§7 while falling for the Noodle Parachute."],
    variant(_p, s) {
        if (hasFlag(s, "dente"))
            return "rigid";
        if (meatballsOut(s))
            return "detached";
        if (brittle(s))
            return "brittle";
        return "";
    },
    cooldownMul(_p, s) {
        return brittle(s) ? 1.25 : 1;
    },
    init(_p, s, first) {
        if (first) {
            s.data.res.sauce = 50;
            s.dirty = true;
        }
    },
    cleanup(_p, s) {
        delete s.data.res.sauce;
    },
    release(s) {
        clearFlag(s, "meatballs");
        clearFlag(s, "revelation");
    },
    tick20(p, s) {
        if (onFire(p)) {
            flag(s, "brittle", 160);
            addSauce(s, -5);
        }
        else
            addSauce(s, 2);
        const view = flat(p.getViewDirection());
        const now = system.currentTick;
        for (const e of enemiesNear(p, p.location, 6)) {
            if (e.typeId === "minecraft:player")
                continue;
            const to = sub(e.location, p.location);
            if (angleBetween(view, v3(to.x, 0, to.z)) < 120)
                continue;
            privateParticle(p, "plrace:sense_ping", add(e.location, v3(0, 2.2, 0)), { red: 1, green: 0.85, blue: 0.4 });
            if ((s.num.get("eyewarn") ?? 0) < now) {
                s.num.set("eyewarn", now + 120);
                message(s, "§eYour back eye spots something behind you", 40);
                privateSound(p, "mob.slime.small", 0.5, 1.8);
            }
            break;
        }
    },
    tick5(p, s) {
        if (!p.isOnGround && p.isSneaking && !p.isInWater) {
            let vy = 0;
            try {
                vy = p.getVelocity().y;
            }
            catch {
                vy = 0;
            }
            if (vy < -0.15)
                effect(p, "slow_falling", 10, 0, false);
        }
    },
    hud(_p, s) {
        const sc = Math.round(sauce(s));
        const st = meatballsOut(s) ? "§6meatballs away" : hasFlag(s, "dente") ? "§eAL DENTE" : brittle(s) ? "§cbrittle" : "§7meatballs home";
        return `§cSauce §f${meter(sc / 100, 10)} ${sc}%${sc >= 100 ? " §c§lSAUCY" : ""} §8| ${st}`;
    },
    onHurt(_p, s, ev) {
        const cause = ev.damageSource.cause;
        if (cause === "fall")
            ev.damage *= 0.5;
        if (FIRE_CAUSES.has(cause)) {
            ev.damage *= 1.25;
            flag(s, "brittle", 160);
        }
        if (hasFlag(s, "dente")) {
            if (cause === "projectile") {
                ev.cancel = true;
                return;
            }
            ev.damage *= 0.4;
        }
        if (meatballsOut(s))
            ev.damage *= 1.2;
        if (hasFlag(s, "revelation"))
            ev.damage *= 0.7;
    },
    afterHurt(p, s, cause, _amount, attackerId) {
        if (!hasFlag(s, "dente_counter") || cause !== "entityAttack" || !attackerId)
            return;
        const a = world.getEntity(attackerId);
        if (!alive(a) || a.id === p.id)
            return;
        clearFlag(s, "dente_counter");
        hurt(a, s.num.get("dente_power") ?? 4, p);
        knockFrom(a, p.location, 1.4, 0.35);
        particle(p.dimension, "plrace:dente_crack", chest(a));
        sound(p.dimension, "random.anvil_land", p.location, 0.4, 1.6);
        message(s, "§eAl Dente counter!", 30);
    },
    onItemComplete(_p, s, typeId) {
        if (typeId === "minecraft:potion" || typeId === "minecraft:milk_bucket")
            return;
        addSauce(s, PASTA_FOODS.test(typeId) ? 40 : 15);
    },
};
