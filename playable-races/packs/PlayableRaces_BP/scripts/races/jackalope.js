import { MoonPhase, system, world } from "@minecraft/server";
import { endChannel, message, refreshForm, refund, startChannel } from "../core/abilities.js";
import { effect, heal, hurt, knock } from "../core/combat.js";
import { isDay, isOverworld, isMoving } from "../core/env.js";
import { particle, pose, privateParticle, privateSound, rgb, RGB, sound } from "../core/fx.js";
import { flag, get, hasFlag } from "../core/session.js";
import { aimTarget, alive, chest, enemiesAlongSegment, enemiesNear, groundSpot } from "../core/targets.js";
import { repeat } from "../core/tasks.js";
import { add, angleBetween, dist, flat, mul, rotY, sub, v3 } from "../core/util.js";
import { bloodMoonActive } from "../systems/bloodmoon.js";
import { brand, consume, markedBy } from "../systems/marks.js";
import { spawnMirage } from "../systems/mirage.js";
const PHASE_NAME = {
    [MoonPhase.FullMoon]: "Full Moon", [MoonPhase.WaningGibbous]: "Waning Gibbous", [MoonPhase.FirstQuarter]: "First Quarter",
    [MoonPhase.WaningCrescent]: "Waning Crescent", [MoonPhase.NewMoon]: "New Moon", [MoonPhase.WaxingCrescent]: "Waxing Crescent",
    [MoonPhase.LastQuarter]: "Last Quarter", [MoonPhase.WaxingGibbous]: "Waxing Gibbous",
};
function moonPhase() {
    try {
        return world.getMoonPhase();
    }
    catch {
        return MoonPhase.FirstQuarter;
    }
}
export function awakened(p) {
    return bloodMoonActive() && isOverworld(p);
}
export function resonance(p) {
    if (!isOverworld(p))
        return 0;
    if (bloodMoonActive())
        return 4;
    if (isDay())
        return 0;
    switch (moonPhase()) {
        case MoonPhase.FullMoon:
            return 3;
        case MoonPhase.WaningGibbous:
        case MoonPhase.WaxingGibbous:
            return 2;
        case MoonPhase.NewMoon:
            return 0;
        default:
            return 1;
    }
}
const isNewMoonNight = (p) => isOverworld(p) && !isDay() && moonPhase() === MoonPhase.NewMoon;
const bound = {
    id: "lunar_bound",
    name: "Lunar Bound",
    short: "Bound",
    cooldown: 10,
    maxCharges: ({ p }) => (awakened(p) ? 2 : 1),
    original: "Cooldown 12 s; directional airborne leap/dash leaving a crescent trail.",
    desc: "Coil the hind legs and spring ~7 blocks in the direction you are moving (forward if standing still), leaving a crescent moon trail. No fall damage from the leap, and the next hit within 0.7 s is halved. Distance grows with Lunar Resonance; the Blood Moon grants 2 charges.",
    cast({ p }) {
        const res = resonance(p);
        let dir = flat(p.getViewDirection());
        try {
            const vel = p.getVelocity();
            if (Math.hypot(vel.x, vel.z) > 0.06)
                dir = flat(vel);
        }
        catch {
        }
        const s = sessionOf(p);
        pose(p, "jak_bound");
        knock(p, mul(dir, 2.3 * (1 + 0.07 * res)), 0.5 + (res >= 4 ? 0.1 : 0));
        if (s) {
            flag(s, "nofall", 70);
            flag(s, "evade", 14);
        }
        const col = rgb(res >= 4 ? RGB.crimson : RGB.silver);
        repeat(2, 8, () => {
            if (p.isValid)
                particle(p.dimension, "plrace:crescent_trail", add(p.location, v3(0, 0.5, 0)), col);
        }, p.id, "bound_fx");
        sound(p.dimension, "mob.rabbit.hop", p.location, 1, 0.9);
        sound(p.dimension, "item.trident.riptide_1", p.location, 0.4, 1.7);
        return true;
    },
};
const brandAbility = {
    id: "antler_brand",
    name: "Antler Brand",
    short: "Brand",
    cooldown: 18,
    original: "Cooldown 20 s; antler charge that marks an enemy with a lunar sigil for ~8 s.",
    desc: "Lower the antlers and charge ~5 blocks. The first enemy struck takes 5 damage and is branded with a LUNAR SIGIL for 8 s: your melee hits on it deal +3, Crimson Waltz targets it first and slashes it 50% harder, and if it dies branded your other cooldowns drop by 4 s and you gain Speed II (Moonhunt). Under the Blood Moon the sigil detonates when it expires.",
    cast({ p, s }) {
        flag(s, "hunt", 40);
        refreshForm(p, s);
        pose(p, "jak_brand");
        sound(p.dimension, "mob.goat.prepare_ram", p.location, 1, 1.35);
        let done = false;
        let last = { ...p.location };
        startChannel(p, s, {
            ability: "antler_brand",
            mode: "block",
            until: system.currentTick + 16,
            tick: (s2, p2, t) => {
                const f = flat(p2.getViewDirection());
                if (t === 5) {
                    last = { ...p2.location };
                    knock(p2, mul(f, 2.6), 0.18);
                }
                if (t >= 5 && !done) {
                    const from = add(last, v3(0, 0.9, 0));
                    const to = add(add(p2.location, mul(f, 0.9)), v3(0, 0.9, 0));
                    last = { ...p2.location };
                    for (const e of enemiesAlongSegment(p2, from, to, 1.6)) {
                        done = true;
                        hurt(e, 5, p2);
                        brand(e, p2, 160, awakened(p2));
                        knock(e, mul(f, 0.8), 0.3);
                        particle(p2.dimension, "plrace:moon_sigil", add(e.location, v3(0, 2.2, 0)), rgb(awakened(p2) ? RGB.crimson : RGB.silver));
                        sound(p2.dimension, "mob.goat.ram_impact", e.location, 1, 1.2);
                        message(s2, "§fLunar Sigil branded", 30);
                        break;
                    }
                }
            },
            end: () => undefined,
        });
        return true;
    },
};
const mirage = {
    id: "velvet_mirage",
    name: "Velvet Mirage",
    short: "Mirage",
    cooldown: 28,
    original: "Cooldown 30 s; illusory rabbit-like duplicate for ~5 s that diverts attention or attacks.",
    desc: "Shed an illusory duplicate and spring away. Hostile mobs nearby are provoked into chasing it (and mobs that hunt players will pursue it). Anything that strikes it is dazzled (Blindness + Slowness II, 3 s). You gain Velvet Step: the next attack within 2 s misses you. Lasts 5 s (7 s under a new moon or the Blood Moon).",
    cast({ p, s }) {
        const ticks = isNewMoonNight(p) || awakened(p) ? 140 : 100;
        const e = spawnMirage(p, ticks);
        if (!e)
            return "No room for the illusion here";
        const f = flat(p.getViewDirection());
        const side = v3(-f.z, 0, f.x);
        knock(p, add(mul(f, -1.2), mul(side, (system.currentTick % 2 === 0 ? 1 : -1) * 0.8)), 0.42);
        flag(s, "velvet_step", 40);
        flag(s, "nofall", 50);
        pose(p, "jak_mirage");
        message(s, "§dVelvet Step - the next blow will miss", 35);
        return true;
    },
};
const WALTZ_RADIUS = 2.7;
const waltz = {
    id: "crimson_waltz",
    name: "Crimson Waltz",
    short: "Waltz",
    cooldown: 42,
    range: 10,
    cone: 60,
    needsTarget: true,
    aim: (p) => aimTarget(p, 10, 60, (e) => markedBy(e) === p.id),
    original: "Cooldown 45 s; consecutive high-speed leaps around a target with crimson crescent attacks from the antlers.",
    desc: "Choose a target within 10 blocks (branded enemies first) and dance around it: 4 blinding leaps (6 under the Blood Moon), each ending in a crimson antler crescent (4 damage, 6 vs branded), then a full-moon cross slash (6, 9 vs branded) that launches it. You take 50% less damage while waltzing. Blood Moon slashes also heal you for 20% of their damage.",
    cast({ p, s }) {
        const target = waltz.aim(p, s);
        if (!target)
            return "No target within 10 blocks";
        const blood = awakened(p);
        const leaps = blood ? 6 : 4;
        const total = leaps * 5 + 10;
        flag(s, "hunt", total + 6);
        flag(s, "waltz", total + 4);
        flag(s, "nofall", total + 40);
        refreshForm(p, s);
        pose(p, "jak_waltz", "!q.is_item_name_any('slot.armor.head', 0, 'plrace:form_jackalope_hunt', 'plrace:form_jackalope_awakened_hunt')");
        sound(p.dimension, "mob.fox.screech", p.location, 0.6, 1.4);
        const base = (Math.atan2(p.location.x - target.location.x, p.location.z - target.location.z) * 180) / Math.PI;
        let step = 0;
        let finished = false;
        startChannel(p, s, {
            ability: "crimson_waltz",
            mode: "block",
            until: system.currentTick + total,
            tick: (s2, p2, t) => {
                if (finished)
                    return;
                if (!alive(target) || target.dimension.id !== p2.dimension.id || dist(target.location, p2.location) > 16) {
                    finished = true;
                    endChannel(p2, s2, "complete");
                    return;
                }
                const marked = markedBy(target) === p2.id;
                if (t % 5 === 0 && step < leaps) {
                    const ang = -base + step * (360 / leaps) + (step % 2 ? 22 : -22);
                    const want = add(target.location, rotY(v3(0, 0, WALTZ_RADIUS), ang));
                    const spot = groundSpot(p2.dimension, add(want, v3(0, 1.5, 0)), 4, 2, 0) ?? want;
                    try {
                        p2.tryTeleport(spot, { checkForBlocks: true, facingLocation: chest(target), keepVelocity: false });
                    }
                    catch {
                    }
                    slash(p2, target, marked ? 6 : 4, blood, 1 + step * 0.12, 1);
                    step++;
                }
                else if (step >= leaps && t >= leaps * 5 + 4) {
                    finished = true;
                    slash(p2, target, marked ? 9 : 6, blood, 0.7, 1.6);
                    knock(target, v3(0, 0, 0), 0.65);
                    if (marked)
                        consume(target);
                    endChannel(p2, s2, "complete");
                }
            },
            end: (s2, p2, reason) => {
                if (reason !== "leave" && p2.isValid)
                    refreshForm(p2, s2);
            },
        });
        return true;
    },
};
function slash(p, target, dmg, blood, pitch, scale) {
    particle(p.dimension, "plrace:crimson_slash", chest(target), { spin: Math.floor(Math.random() * 360), scale });
    sound(p.dimension, "item.trident.hit", target.location, 1, pitch);
    let before = 0;
    try {
        before = target.getComponent("minecraft:health")?.currentValue ?? 0;
    }
    catch {
        before = 0;
    }
    hurt(target, dmg, p);
    if (blood) {
        effect(target, "wither", 40, 0);
        let after = 0;
        try {
            after = target.isValid ? target.getComponent("minecraft:health")?.currentValue ?? 0 : 0;
        }
        catch {
            after = 0;
        }
        heal(p, Math.max(0, before - after) * 0.2);
    }
}
const sessionOf = (p) => get(p);
function sense(p, s, radius, all) {
    const res = resonance(p);
    const col = rgb(res >= 4 ? RGB.crimson : RGB.silver);
    let n = 0;
    const view = flat(p.getViewDirection());
    let behind;
    for (const e of enemiesNear(p, p.location, radius)) {
        if (e.typeId === "minecraft:player")
            continue;
        let monster = all;
        try {
            monster = monster || !!e.getComponent("minecraft:type_family")?.hasTypeFamily("monster");
        }
        catch {
        }
        if (!monster)
            continue;
        if (n++ < 12)
            privateParticle(p, "plrace:sense_ping", add(e.location, v3(0, 2.3, 0)), col);
        const to = sub(e.location, p.location);
        if (!behind && Math.hypot(to.x, to.z) < 8 && angleBetween(view, v3(to.x, 0, to.z)) > 115)
            behind = e;
    }
    const now = system.currentTick;
    if (behind && (s.num.get("warn") ?? 0) < now) {
        s.num.set("warn", now + 120);
        message(s, "§7Your ears twitch - something is behind you", 40);
        privateSound(p, "mob.rabbit.idle", 0.6, 1.6);
    }
}
export const jackalope = {
    code: "003",
    key: "jackalope",
    name: "Blood Moon Jackalope",
    thai: "เผ่าแจ็คคาโลปดวงจันทร์สีเลือด",
    title: "The Hollow-Moon Kin",
    color: "§c",
    tagline: "Swift, eerie and lunar - antlers that are living organs of the moon.",
    lore: [
        "Hare-folk say the moon was once a hollow antler, and that their ancestors licked its marrow. Whatever the truth, a Jackalope's antlers are not bone: they are obsidian-black lunar organs threaded with blood-red channels that brighten as the moon swells.",
        "They are hunters of the edge of the light, listening with ears longer than their forearms and moving in sudden, impossible bounds. Once in a long while the full moon rises red. Then the antlers branch, the veins under the fur ignite, the dorsal fur stands on end - and for one night the Jackalopes remember what they were.",
    ],
    strengths: ["Fastest race: Speed and Jump Boost, bounding leaps", "Deception and evasion (Mirage, Velvet Step)", "Senses hostile mobs at night", "Grows stronger with the moon; awakens under the Blood Moon"],
    weaknesses: ["Fragile: lightest crest armour, +10% melee damage taken", "Weakest by day and in the Nether / End (no moon)", "Relies on positioning - Waltz needs a target", "Blood Moon is rare"],
    passives: [
        { name: "Hare Legs", desc: "Speed I and Jump Boost (II at night); falls deal 50% damage minus 2, and none just after a leap." },
        { name: "Lunar Resonance", desc: "0 by day; 1-3 at night by moon phase (full moon 3); 4 under the Blood Moon. Each level speeds cooldowns by 6% and lengthens Lunar Bound." },
        { name: "Moonlit Hearing", desc: "At night (and in the Nether/End) hostile mobs within 18-30 blocks are revealed to you with silver pings; your ears warn you when something lurks behind." },
        { name: "Thump & Listen", desc: "Sneak still for 1 s: the Listening pose reveals every hostile within 40 blocks for 6 s (12 s internal cooldown)." },
        { name: "Blood Moon Awakening", desc: "During the Blood Moon: extra antler tines, crimson veins, raised fur, red eyes; Speed II, resonance 4, 2 Bound charges, blood sigils, longer mirages and life-stealing waltz slashes." },
        { name: "Fragile Frame", desc: "Takes 10% more melee damage." },
    ],
    abilities: [bound, brandAbility, mirage, waltz],
    focusItem: "plrace:focus_jackalope",
    focusName: "Moonbone Focus",
    controls: ["Jackalope: §fsneak and stand still§7 for 1 s to Thump & Listen."],
    variant(p, s) {
        const aw = awakened(p);
        const hunt = hasFlag(s, "hunt");
        return aw ? (hunt ? "awakened_hunt" : "awakened") : hunt ? "hunt" : "";
    },
    cooldownMul(p) {
        return 1 - 0.06 * resonance(p);
    },
    init(_p, s, first) {
        if (first) {
            s.data.st.jak = "lunar";
            s.dirty = true;
        }
    },
    cleanup(_p, s) {
        delete s.data.st.jak;
    },
    tick20(p, s) {
        const aw = awakened(p);
        const night = !isDay() || !isOverworld(p);
        effect(p, "speed", 50, aw ? 1 : 0, false);
        effect(p, "jump_boost", 50, night ? 1 : 0, false);
        const want = aw ? "awakened" : "lunar";
        if ((s.data.st.jak ?? "lunar") !== want) {
            s.data.st.jak = want;
            s.dirty = true;
            refreshForm(p, s);
            if (aw) {
                pose(p, "jak_howl");
                try {
                    p.camera.fade({ fadeColor: { red: 0.45, green: 0.02, blue: 0.05 }, fadeTime: { fadeInTime: 0.3, holdTime: 0.2, fadeOutTime: 0.9 } });
                }
                catch {
                }
                sound(p.dimension, "mob.hoglin.howl", p.location, 0.7, 1.5);
                message(s, "§4Blood Moon Awakening - antlers branch, veins ignite", 80);
            }
            else
                message(s, "§7The awakening fades with the crimson moon", 60);
        }
        const res = resonance(p);
        if (night)
            sense(p, s, 18 + res * 3, false);
        const reveal = s.num.get("reveal") ?? 0;
        if (reveal > system.currentTick)
            sense(p, s, 40, false);
    },
    tick5(p, s) {
        const still = p.isSneaking && !isMoving(p) && p.isOnGround;
        const n = still ? (s.num.get("listen") ?? 0) + 1 : 0;
        s.num.set("listen", n);
        if (n === 4 && (s.num.get("listen_cd") ?? 0) < system.currentTick) {
            s.num.set("listen_cd", system.currentTick + 240);
            s.num.set("reveal", system.currentTick + 120);
            sound(p.dimension, "mob.rabbit.hop", p.location, 1, 0.5);
            particle(p.dimension, "plrace:impact_ring", add(p.location, v3(0, 0.1, 0)));
            message(s, "§fThump... you listen to the dark (6 s)", 40);
            sense(p, s, 40, false);
        }
    },
    hud(p) {
        const res = resonance(p);
        const label = !isOverworld(p) ? "§8no moon here" : bloodMoonActive() ? "§4§lBLOOD MOON" : isDay() ? "§7daylight" : `§f${PHASE_NAME[moonPhase()] ?? "Moon"}`;
        const pips = "§c" + "o".repeat(res) + "§8" + "o".repeat(4 - res);
        return `§fLunar ${pips} §f${res} ${label}`;
    },
    onHurt(_p, s, ev) {
        const cause = ev.damageSource.cause;
        if (cause === "fall") {
            if (hasFlag(s, "nofall")) {
                ev.cancel = true;
                return;
            }
            ev.damage = Math.max(0, ev.damage * 0.5 - 2);
            if (ev.damage <= 0) {
                ev.cancel = true;
                return;
            }
        }
        if (hasFlag(s, "velvet_step") && cause !== "fall" && cause !== "void") {
            s.flags.delete("velvet_step");
            ev.cancel = true;
            return;
        }
        if (cause === "entityAttack")
            ev.damage *= 1.1;
        if (hasFlag(s, "evade")) {
            s.flags.delete("evade");
            ev.damage *= 0.5;
        }
        if (hasFlag(s, "waltz"))
            ev.damage *= 0.5;
    },
    onDealDamage(p, _s, ev) {
        if (ev.damageSource.cause === "entityAttack" && markedBy(ev.hurtEntity) === p.id)
            ev.damage += 3;
    },
};
export function moonhunt(p, s) {
    refund(s, 80);
    effect(p, "speed", 60, 1, false);
    message(s, "§cMoonhunt! Cooldowns -4 s", 40);
    privateSound(p, "random.orb", 0.7, 0.6);
}
