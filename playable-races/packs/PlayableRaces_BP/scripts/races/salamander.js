import { InputPermissionCategory, system } from "@minecraft/server";
import { endChannel, message, refreshForm, startChannel } from "../core/abilities.js";
import { effect, heal, healthFrac, hurt, knock, knockFrom } from "../core/combat.js";
import { biome, headInWater, inWater, isDay, isDryBiome, isHumidBiome, isOverworld, onFire, raining, skyExposed, soilUnderfoot, wetGround } from "../core/env.js";
import { particle, pose, privateSound, sound } from "../core/fx.js";
import { flag, hasFlag, save } from "../core/session.js";
import { aimTarget, chest, enemiesNear, eye } from "../core/targets.js";
import { repeat } from "../core/tasks.js";
import { add, angleBetween, clamp, dist, flat, len, meter, mul, norm, sub, v3 } from "../core/util.js";
const STATE_NAME = { stable: "§2Stable", bloom: "§aBlooming", dormant: "§6Dormant" };
const hyd = (s) => s.data.res.hyd ?? 80;
const state = (s) => s.data.st.sal ?? "stable";
const ensnared = new Map();
export const isEnsnared = (id, by) => {
    const e = ensnared.get(id);
    return !!e && e.until > system.currentTick && (by === undefined || e.by === by);
};
function hand(p) {
    const f = flat(p.getViewDirection());
    const right = v3(-f.z, 0, f.x);
    return add(add(p.location, v3(0, 1.25, 0)), add(mul(right, 0.38), mul(f, 0.35)));
}
const boostUntil = new Map();
export function swimBoost(p, value, ticks) {
    try {
        const c = p.getComponent("minecraft:underwater_movement");
        if (!c)
            return;
        const now = system.currentTick;
        if (ticks > 0)
            boostUntil.set(p.id, now + ticks);
        else if ((boostUntil.get(p.id) ?? 0) > now)
            return;
        if (value <= 0) {
            if (Math.abs(c.currentValue - c.defaultValue) > 1e-6)
                c.resetToDefaultValue();
        }
        else if (Math.abs(c.currentValue - value) > 1e-6)
            c.setCurrentValue(value);
    }
    catch {
    }
}
function setState(p, s, st) {
    if (state(s) === st)
        return;
    const prev = state(s);
    s.data.st.sal = st;
    s.dirty = true;
    refreshForm(p, s);
    const loc = add(p.location, v3(0, 1.4, 0));
    if (st === "bloom") {
        particle(p.dimension, "plrace:dew_burst", loc);
        sound(p.dimension, "tilt_up.big_dripleaf", loc, 0.8, 1.3);
        message(s, "§aYour plates unfurl - Blooming", 50);
    }
    else if (st === "dormant") {
        particle(p.dimension, "plrace:dry_flake", loc);
        sound(p.dimension, "tilt_down.big_dripleaf", loc, 0.8, 0.7);
        message(s, "§6Parched... your body curls into dormancy. Find water or rain.", 70);
    }
    else if (prev === "dormant") {
        sound(p.dimension, "bubble.up", loc, 0.8, 1.2);
        message(s, "§2Moisture returns - Stable", 50);
    }
}
const snare = {
    id: "sundew_snare",
    name: "Sundew Snare",
    short: "Snare",
    cooldown: 14,
    range: 8,
    needsTarget: true,
    aim: (p, s) => aimTarget(p, state(s) === "bloom" ? 10 : 8, 14),
    original: "Cooldown 15 s, ~8 blocks, slows ~4 s.",
    desc: "Fling glandular filaments at prey up to 8 blocks away (10 while Blooming). It is slowed (Slowness III, 4 s), dragged toward you and ENSNARED: your next Carnivorous Embrace on it bites 50% harder.",
    cast({ p, s }) {
        const range = state(s) === "bloom" ? 10 : 8;
        const t = snare.aim(p, s);
        if (!t)
            return `No prey within ${range} blocks`;
        const from = hand(p);
        const d = sub(chest(t), from);
        const n = norm(d);
        particle(p.dimension, "plrace:snare_strand", from, { dx: n.x, dy: n.y, dz: n.z, len: len(d) });
        sound(p.dimension, "mob.frog.tongue", from, 1, 0.8);
        sound(p.dimension, "mob.slime.small", chest(t), 0.8, 0.7);
        hurt(t, 2, p);
        effect(t, "slowness", 80, 2);
        knock(t, mul(flat(sub(p.location, t.location)), 0.8), 0.12);
        ensnared.set(t.id, { by: p.id, until: system.currentTick + 100 });
        const target = t;
        repeat(10, 8, () => {
            if (target.isValid)
                particle(target.dimension, "plrace:ensnared", target.location);
        }, p.id, "snare_fx");
        flag(s, "predatory", 60);
        refreshForm(p, s);
        pose(p, "sal_snare");
        return true;
    },
};
const embrace = {
    id: "carnivorous_embrace",
    name: "Carnivorous Embrace",
    short: "Embrace",
    cooldown: 22,
    range: 3.5,
    cone: 70,
    needsTarget: true,
    aim: (p) => aimTarget(p, 3.6, 70, (e) => isEnsnared(e.id, p.id)),
    original: "Cooldown 25 s, close-range bite that restores some health.",
    desc: "The trap-lobes on your forearms snap shut on a creature within 3.5 blocks: 6 damage (9 if Ensnared), it is held in place for a second, and you absorb 40% of the damage dealt as health (min 1 heart).",
    cast({ p, s }) {
        const t = embrace.aim(p, s);
        if (!t)
            return "Nothing within reach (3.5 blocks)";
        const caught = isEnsnared(t.id, p.id);
        const dmg = caught ? 9 : 6;
        let before = 0;
        try {
            before = t.getComponent("minecraft:health")?.currentValue ?? 0;
        }
        catch {
            before = 0;
        }
        hurt(t, dmg, p);
        let after = 0;
        try {
            after = t.isValid ? t.getComponent("minecraft:health")?.currentValue ?? 0 : 0;
        }
        catch {
            after = 0;
        }
        const dealt = Math.max(0, before - after) || dmg * 0.5;
        heal(p, Math.max(2, dealt * 0.4));
        effect(t, "slowness", 20, 4);
        ensnared.delete(t.id);
        particle(p.dimension, "plrace:trap_snap", chest(t));
        particle(p.dimension, "plrace:heal_leaf", add(p.location, v3(0, 1, 0)));
        sound(p.dimension, "mob.frog.eat", chest(t), 1, 0.7);
        sound(p.dimension, "block.sweet_berry_bush.pick", chest(t), 0.8, 0.6);
        flag(s, "predatory", 50);
        refreshForm(p, s);
        pose(p, "sal_embrace");
        if (caught)
            message(s, "§cEnsnared prey devoured!", 30);
        return true;
    },
};
const ROOT_TICKS = 120;
const root = {
    id: "root_metamorphosis",
    name: "Root Metamorphosis",
    short: "Root",
    cooldown: 30,
    original: "Cooldown 35 s; stationary; regeneration and resistance; root/unroot animation.",
    desc: "Drive roots into the ground for up to 6 s: heal 1.5 HP per second, take 40% less damage, ignore knockback and draw groundwater (+5 hydration/s on soil). You cannot walk while rooted - press JUMP (or use the focus again) to uproot early.",
    check({ p }) {
        if (!p.isOnGround)
            return "You must stand on the ground to take root";
        return undefined;
    },
    cast({ p, s }) {
        const anchor = { ...p.location };
        try {
            p.inputPermissions.setPermissionCategory(InputPermissionCategory.LateralMovement, false);
            if (!s.data.locks.includes(InputPermissionCategory.LateralMovement))
                s.data.locks.push(InputPermissionCategory.LateralMovement);
            s.dirty = true;
            save(p, s, true);
        }
        catch {
        }
        startChannel(p, s, {
            ability: "root_metamorphosis",
            mode: "keep",
            cancelable: true,
            until: system.currentTick + ROOT_TICKS,
            tick: (s2, p2, t) => {
                if (!p2.isValid)
                    return;
                if (dist(p2.location, anchor) > 0.45) {
                    try {
                        p2.teleport(anchor, { keepVelocity: false });
                    }
                    catch {
                    }
                }
                if (t % 20 === 0 && t > 0) {
                    heal(p2, 1.5);
                    if (soilUnderfoot(p2)) {
                        s2.data.res.hyd = clamp(hyd(s2) + 5, 0, 100);
                        s2.dirty = true;
                    }
                    particle(p2.dimension, "plrace:heal_leaf", add(p2.location, v3(0, 1.2, 0)));
                }
            },
            end: (s2, p2, reason) => {
                try {
                    p2.inputPermissions.setPermissionCategory(InputPermissionCategory.LateralMovement, true);
                }
                catch {
                }
                s2.data.locks = s2.data.locks.filter((c) => c !== InputPermissionCategory.LateralMovement);
                s2.dirty = true;
                if (reason !== "leave" && p2.isValid) {
                    refreshForm(p2, s2);
                    particle(p2.dimension, "plrace:root_burst", p2.location);
                    sound(p2.dimension, "block.mangrove_roots.break", p2.location, 1, 0.9);
                }
            },
        });
        refreshForm(p, s);
        particle(p.dimension, "plrace:root_burst", p.location);
        sound(p.dimension, "block.mangrove_roots.place", p.location, 1, 0.7);
        sound(p.dimension, "dig.roots", p.location, 1, 0.6);
        pose(p, "sal_root", "!q.is_item_name_any('slot.armor.head', 0, 'plrace:form_salamander_rooted')");
        message(s, "§2Rooted - press JUMP to uproot", 50);
        return true;
    },
};
const jet = {
    id: "bladder_jet",
    name: "Bladder Jet",
    short: "Jet",
    cooldown: 16,
    original: "Cooldown 18 s; propels the player through water, pushes nearby creatures away.",
    desc: "Underwater: a pressurised bladder blast rockets you ~10 blocks where you look, shoving and slowing every creature within 3.5 blocks. On land it costs 20% hydration for a shorter hop-dash that douses fire and sprays enemies in front of you back.",
    cast({ p, s }) {
        const dir = p.getViewDirection();
        const water = inWater(p);
        if (water) {
            knock(p, v3(dir.x * 3.2, 0, dir.z * 3.2), dir.y * 1.4 + 0.12);
            swimBoost(p, 0.06, 50);
            particle(p.dimension, "plrace:jet_ring", add(p.location, v3(0, 0.8, 0)));
            repeat(2, 6, () => {
                if (p.isValid)
                    particle(p.dimension, "plrace:jet_trail", add(p.location, v3(0, 0.6, 0)));
            }, p.id, "jet_fx");
            for (const e of enemiesNear(p, p.location, 3.5)) {
                knockFrom(e, p.location, 1.4, 0.25);
                effect(e, "slowness", 40, 1);
            }
            sound(p.dimension, "item.trident.riptide_1", p.location, 1, 1.2);
            sound(p.dimension, "mob.axolotl.splash", p.location, 1, 0.8);
        }
        else {
            if (hyd(s) < 20)
                return "Bladder empty - needs 20% hydration (find water)";
            s.data.res.hyd = hyd(s) - 20;
            s.dirty = true;
            const f = flat(dir);
            knock(p, v3(f.x * 1.7, 0, f.z * 1.7), 0.45);
            try {
                p.extinguishFire(true);
            }
            catch {
            }
            const from = eye(p);
            for (const e of enemiesNear(p, p.location, 4.5)) {
                if (angleBetween(f, sub(e.location, p.location)) < 55)
                    knockFrom(e, p.location, 1.1, 0.25);
            }
            particle(p.dimension, "plrace:dew_burst", from);
            sound(p.dimension, "bucket.empty_water", p.location, 1, 1.3);
        }
        pose(p, "sal_jet");
        return true;
    },
};
export const salamander = {
    code: "001",
    key: "salamander",
    name: "Aberrant Flora Salamander",
    thai: "เผ่าสลาแมนเดอร์พืชประหลาด",
    title: "The Mirefold",
    color: "§a",
    tagline: "Half amphibian, half carnivorous garden - a living ecosystem that hunts.",
    lore: [
        "In the drowned mangrove sinks a cave salamander lineage swallowed the seeds of a carnivorous bog-bloom, and the seeds did not die. Generations later the two organisms share one bloodstream: purple-red sap runs beside amphibian blood, the back grows photosynthetic plates, and the forearms carry sundew glands and snapping trap-lobes.",
        "The Mirefold measure wealth in water. Wet, they bloom - vivid, quick to heal, quick to strike. Dry, they curl into dormancy and wait for rain, armoured but slow. Their gills are fern-like fronds; their tail ends in a flower that opens toward the sun.",
    ],
    strengths: ["Breathes water and swims fast", "Self-healing (photosynthesis, Embrace, Root)", "Prey control: snare, hold, drag", "Excellent in rain, swamps, rivers and oceans"],
    weaknesses: ["Dries out in deserts, the Nether and fire", "Dormant: slower and weaker abilities", "Root Metamorphosis leaves you stationary", "Takes extra fire damage"],
    passives: [
        { name: "Fern Gills", desc: "Conduit Power underwater (breath, underwater vision, haste) and +70% swim speed (+100% while Blooming) with at least 30% hydration." },
        { name: "Hydration", desc: "Water +10/s, rain +4/s, wet ground +1.2/s, humid biomes +0.4/s; dry land drains (deserts and the Nether fastest, fire drains 3/s). Drinking a water bottle restores 40%." },
        { name: "Blooming (hydration 70%+ and water, rain or sunlight)", desc: "Plates unfurl: cooldowns 20% faster, Snare reaches 10 blocks, photosynthesis heals 1 HP every 4 s in sunlight." },
        { name: "Dormant (hydration 15% or less, recovers at 32%)", desc: "Leaves contract and the skin dulls: Slowness I, cooldowns 40% slower and no photosynthesis - but the hardened skin takes 15% less damage." },
        { name: "Photosynthesis", desc: "Standing in daylight under open sky (not Dormant) slowly heals and restores hunger." },
        { name: "Adhesive Pads", desc: "Fall damage reduced by 40%." },
    ],
    abilities: [snare, embrace, root, jet],
    focusItem: "plrace:focus_salamander",
    focusName: "Dewheart Focus",
    controls: ["Salamander: §fJUMP§7 uproots Root Metamorphosis early."],
    variant(_p, s) {
        if (s.channel?.ability === "root_metamorphosis")
            return "rooted";
        if (hasFlag(s, "predatory"))
            return "predatory";
        const st = state(s);
        return st === "bloom" ? "bloom" : st === "dormant" ? "dormant" : "";
    },
    cooldownMul(_p, s) {
        const st = state(s);
        return st === "bloom" ? 0.8 : st === "dormant" ? 1.4 : 1;
    },
    init(_p, s, first) {
        if (first) {
            s.data.res.hyd = 85;
            s.data.st.sal = "stable";
            s.dirty = true;
        }
    },
    cleanup(p, s) {
        swimBoost(p, 0, 0);
        ensnared.forEach((v, k) => {
            if (v.by === p.id)
                ensnared.delete(k);
        });
        delete s.data.st.sal;
    },
    tick20(p, s) {
        const b = biome(p);
        const water = inWater(p);
        const rain = raining(p, b);
        const sky = skyExposed(p);
        const day = isDay() && isOverworld(p);
        const rooted = s.channel?.ability === "root_metamorphosis";
        let d = 0;
        if (water)
            d += 10;
        else if (rain)
            d += 4;
        else if (wetGround(p))
            d += 1.2;
        else if (isHumidBiome(b))
            d += 0.4;
        else if (p.dimension.id === "minecraft:nether")
            d -= 2.5;
        else if (isDryBiome(b))
            d -= day && sky ? 1.8 : 1.2;
        else
            d -= day && sky ? 0.45 : 0.3;
        if (onFire(p))
            d -= 3;
        const old = hyd(s);
        const h = clamp(old + d, 0, 100);
        if (Math.abs(h - old) > 1e-6) {
            s.data.res.hyd = h;
            s.dirty = true;
        }
        const bright = day && sky && !rain;
        let st = state(s);
        if (st === "dormant") {
            if (h >= 32)
                st = "stable";
        }
        else if (h <= 15)
            st = "dormant";
        else if (h >= 70 && (water || bright || rain || rooted))
            st = "bloom";
        else if (st === "bloom" && (h < 60 || !(water || bright || rain || rooted)))
            st = "stable";
        setState(p, s, st);
        if (water || headInWater(p))
            effect(p, "conduit_power", 70, 0, false);
        swimBoost(p, water && h >= 30 ? (st === "bloom" ? 0.04 : 0.034) : 0, 0);
        if (st === "dormant")
            effect(p, "slowness", 50, 0, false);
        if (bright && st !== "dormant") {
            const n = (s.num.get("photo") ?? 0) + 1;
            s.num.set("photo", n);
            const every = st === "bloom" ? 4 : 8;
            if (n % every === 0 && healthFrac(p) < 1) {
                heal(p, 1);
                particle(p.dimension, "plrace:heal_leaf", add(p.location, v3(0, 1.6, 0)));
            }
            if (n % 24 === 0) {
                try {
                    const hunger = p.getComponent("minecraft:player.hunger");
                    if (hunger && hunger.currentValue < hunger.effectiveMax)
                        hunger.setCurrentValue(Math.min(hunger.effectiveMax, hunger.currentValue + 1));
                }
                catch {
                }
            }
        }
        if (h <= 30 && old > 30) {
            message(s, "§6Your skin is drying (30% hydration)", 50);
            privateSound(p, "random.fizz", 0.4, 1.4);
        }
        if (rooted && s.channel && !p.isOnGround && !water)
            endChannel(p, s, "interrupt");
    },
    hud(p, s) {
        const h = hyd(s);
        const col = h > 60 ? "§b" : h > 25 ? "§3" : "§6";
        const tags = [];
        if (inWater(p))
            tags.push("§3gills");
        if (s.channel?.ability === "root_metamorphosis")
            tags.push("§2rooted");
        return `${col}Hydration ${meter(h / 100, 12)} ${Math.round(h)}% ${STATE_NAME[state(s)]}${tags.length ? " §7" + tags.join(" ") : ""}`;
    },
    onHurt(_p, s, ev) {
        const cause = ev.damageSource.cause;
        if (cause === "fall")
            ev.damage *= 0.6;
        if (cause === "fire" || cause === "fireTick" || cause === "lava" || cause === "magma")
            ev.damage *= 1.25;
        if (state(s) === "dormant")
            ev.damage *= 0.85;
        if (s.channel?.ability === "root_metamorphosis")
            ev.damage *= 0.6;
    },
};
export function salamanderDrink(p, s) {
    s.data.res.hyd = clamp(hyd(s) + 40, 0, 100);
    s.dirty = true;
    particle(p.dimension, "plrace:hydrate", add(p.location, v3(0, 1, 0)));
    message(s, "§bYou drink deep - +40% hydration", 40);
}
export function cleanupEnsnared() {
    const now = system.currentTick;
    for (const [k, v] of ensnared)
        if (v.until <= now)
            ensnared.delete(k);
}
