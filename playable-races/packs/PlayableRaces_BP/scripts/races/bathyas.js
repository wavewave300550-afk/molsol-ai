import { EquipmentSlot, InputPermissionCategory, ItemLockMode, ItemStack, system, world } from "@minecraft/server";
import { endChannel, message, refreshForm, startChannel, tempForm } from "../core/abilities.js";
import { effect, heal, hurt, knock, knockFrom } from "../core/combat.js";
import { isOverworld, isDay, skyExposed, headInWater, inWater } from "../core/env.js";
import { particle, pose, sound } from "../core/fx.js";
import { clearFlag, flag, hasFlag, save } from "../core/session.js";
import { settings } from "../core/settings.js";
import { after, cancel, repeat } from "../core/tasks.js";
import { aimTarget, alive, chest, enemiesNear } from "../core/targets.js";
import { add, dist, flat, mul, norm, rotY, sub, v3 } from "../core/util.js";
import { clearStatus, clearStatusesBy, hasStatus, setStatus } from "../systems/status.js";
export const SUN_SWORD = "plrace:sun_sword";
export const FOG_ABYSS = "plrace:abyss";
const FOG_USER = "plrace_ab";
const drawn = (s) => s.data.st.sun === "drawn";
const stability = (s) => s.data.res.stab ?? 100;
const strain = (s) => s.data.res.strain ?? 0;
const daybreak = (s) => hasFlag(s, "daybreak");
function setStab(s, v) {
    s.data.res.stab = Math.max(0, Math.min(100, v));
    s.dirty = true;
}
function addStrain(p, s, n) {
    const v = Math.max(0, Math.min(100, strain(s) + n));
    s.data.res.strain = v;
    s.dirty = true;
    if (v >= 100) {
        s.data.res.strain = 40;
        flag(s, "misery", 60);
        effect(p, "blindness", 40, 0, false);
        effect(p, "slowness", 60, 1, false);
        message(s, "§eToo much light... §7(Photic Misery)", 60);
        sound(p.dimension, "mob.warden.heartbeat", p.location, 0.8, 1.6);
    }
}
function inventory(p) {
    try {
        return p.getComponent("minecraft:inventory")?.container;
    }
    catch {
        return undefined;
    }
}
export function purgeSwords(p) {
    let n = 0;
    const inv = inventory(p);
    if (inv) {
        for (let i = 0; i < inv.size; i++) {
            const it = inv.getItem(i);
            if (it?.typeId === SUN_SWORD) {
                try {
                    inv.setItem(i, undefined);
                    n++;
                }
                catch {
                }
            }
        }
    }
    try {
        const eq = p.getComponent("minecraft:equippable");
        if (eq?.getEquipment(EquipmentSlot.Offhand)?.typeId === SUN_SWORD) {
            eq.setEquipment(EquipmentSlot.Offhand, undefined);
            n++;
        }
    }
    catch {
    }
    try {
        for (const e of p.dimension.getEntities({ type: "minecraft:item", location: p.location, maxDistance: 12 })) {
            if (e.getComponent("minecraft:item")?.itemStack.typeId === SUN_SWORD)
                e.remove();
        }
    }
    catch {
    }
    return n;
}
function swordCount(p) {
    const inv = inventory(p);
    let n = 0;
    if (inv)
        for (let i = 0; i < inv.size; i++)
            if (inv.getItem(i)?.typeId === SUN_SWORD)
                n++;
    return n;
}
function giveSword(p) {
    const inv = inventory(p);
    if (!inv)
        return false;
    const slot = p.selectedSlotIndex;
    const cur = inv.getItem(slot);
    if (cur) {
        if (inv.emptySlotsCount === 0)
            return false;
        let moved = false;
        for (let i = 0; i < inv.size && !moved; i++) {
            if (i !== slot && !inv.getItem(i)) {
                inv.setItem(i, cur);
                moved = true;
            }
        }
        if (!moved)
            return false;
    }
    const sword = new ItemStack(SUN_SWORD, 1);
    sword.lockMode = ItemLockMode.inventory;
    sword.keepOnDeath = true;
    inv.setItem(slot, sword);
    return true;
}
function setDrawn(p, s, on) {
    s.data.st.sun = on ? "drawn" : "";
    s.dirty = true;
    if (on) {
        s.data.res.safe = 300;
        try {
            p.removeEffect("health_boost");
        }
        catch {
        }
    }
    refreshForm(p, s);
    save(p, s, true);
}
function reimpale(p, s, how) {
    purgeSwords(p);
    if (!drawn(s))
        return;
    setDrawn(p, s, false);
    if (how === "cleanup")
        return;
    pose(p, "bat_return");
    particle(p.dimension, "plrace:sun_return", add(p.location, v3(0, 1.2, 0)));
    sound(p.dimension, "item.trident.return", p.location, 1, 0.6);
    sound(p.dimension, "mob.warden.heartbeat", p.location, 1, 0.8);
    if (how === "forced") {
        effect(p, "slowness", 120, 1, false);
        effect(p, "weakness", 120, 1, false);
        setStab(s, 15);
        s.readyAt.set("draw_the_sun", system.currentTick + 900);
        message(s, "§cThe body drags the sun back into itself. §7(forced re-impalement)", 80);
    }
    else {
        effect(p, "slowness", 40, 1, false);
        effect(p, "mining_fatigue", 60, 0, false);
        setStab(s, stability(s) + 20);
        message(s, "§eThe sun is home again. §7It hurts the way it always has.", 50);
    }
}
const lure = {
    id: "lure_of_the_impaled_sun",
    name: "Lure of the Impaled Sun",
    short: "Lure",
    cooldown: 18,
    original: "Cooldown 18 s; while the sword is embedded Bathyas intensifies its light: briefly distracts nearby enemies, influences attention where supported, a localised pressure/light pulse, Sun-Marked on suitable targets. The sword pulses violently, Bathyas squints, a hand shields his eyes, a distorted radial wave. Uncomfortable and unnatural, not holy.",
    desc: "The impaled sun flares like an anglerfish lure. Bathyas squints and shields his eyes while a warped ring of white-gold light rolls out 10 blocks: every hostile creature caught is drawn a step toward the light and SUN-MARKED for 8 s (a sun sigil burns over its head; Slowness I, Weakness I). Maw Rush and the ultimate hit the marked harder. Raises Photic Strain by 30. Needs the sun in your chest.",
    check({ s }) {
        return drawn(s) ? "The sun is in your hand, not in your chest" : undefined;
    },
    cast({ p, s }) {
        tempForm(p, s, "lure", 32);
        pose(p, "bat_lure");
        const c = add(p.location, v3(0, 1.2, 0));
        particle(p.dimension, "plrace:lure_pulse", c);
        sound(p.dimension, "beacon.power", p.location, 1, 0.5);
        sound(p.dimension, "mob.elderguardian.curse", p.location, 0.25, 1.7);
        let n = 0;
        for (const e of enemiesNear(p, p.location, 10)) {
            setStatus(e, "sunmarked", 160, p.id);
            effect(e, "slowness", 160, 0);
            effect(e, "weakness", 160, 0);
            const toward = flat(sub(p.location, e.location));
            if (dist(e.location, p.location) > 2.5)
                knock(e, mul(norm(toward), 0.55), 0.1);
            n++;
        }
        addStrain(p, s, 30);
        message(s, n ? `§e${n} creature${n > 1 ? "s" : ""} drawn to the light` : "§7The light finds nothing worth luring", 40);
        return true;
    },
};
const maw = {
    id: "goblin_maw_rush",
    name: "Goblin Maw Rush",
    short: "Maw",
    cooldown: 20,
    range: 9,
    cone: 20,
    needsTarget: false,
    aim(p) {
        return aimTarget(p, 9, 20, (e) => hasStatus(e, "sunmarked"));
    },
    original: "Cooldown 20 s; lowers the body and surges toward a target; the jaw protrudes dramatically (goblin shark); rapid close-range attack, strong bite, enhanced against Sun-Marked enemies. Low predatory acceleration, head-led, jaw extension, sudden bite, recovery into the hunch.",
    desc: "Bathyas drops low and surges head-first up to 9 blocks; the goblin-shark jaw shoots out and snaps shut: 7 damage. A SUN-MARKED victim takes 11, loses the mark and feeds you (4 health). With nobody in front, the rush covers 5 blocks and bites whatever it meets.",
    cast({ p, s }) {
        const t = maw.aim(p, s);
        const from = p.location;
        const dir = t ? flat(sub(t.location, from)) : flat(p.getViewDirection());
        const far = t ? Math.min(9, dist(t.location, from)) : 5;
        tempForm(p, s, "maw", 18);
        pose(p, "bat_maw");
        sound(p.dimension, "mob.guardian.attack_loop", p.location, 0.6, 1.8);
        knock(p, mul(norm(dir), 0.55 + far * 0.24), 0.12);
        flag(s, "nofall", 40);
        let bitten = false;
        repeat(1, 12, (i) => {
            if (bitten || !p.isValid)
                return;
            if (i % 2 === 0)
                particle(p.dimension, "plrace:maw_streak", add(p.location, v3(0, 1.0, 0)), { dx: dir.x, dy: 0, dz: dir.z });
            const victims = t && alive(t) ? [t] : enemiesNear(p, add(p.location, mul(norm(dir), 1.2)), 1.8);
            const v = victims.find((e) => alive(e) && dist(e.location, p.location) <= 2.6);
            if (!v && i < 11)
                return;
            bitten = true;
            const hit = v ?? enemiesNear(p, add(p.location, mul(norm(dir), 1.2)), 2.0)[0];
            sound(p.dimension, "mob.ravager.bite", p.location, 1, 0.7);
            if (!hit)
                return;
            const marked = hasStatus(hit, "sunmarked");
            hurt(hit, marked ? 11 : 7, p);
            particle(hit.dimension, "plrace:maw_bite", chest(hit));
            if (marked) {
                clearStatus(hit, "sunmarked");
                heal(p, 4);
                sound(p.dimension, "mob.phantom.bite", p.location, 1, 0.6);
            }
            knockFrom(hit, p.location, 0.5, 0.15);
        }, p.id, "maw");
        return true;
    },
};
const BASTION_TICKS = 120;
const bastion = {
    id: "isopod_bastion",
    name: "Isopod Bastion",
    short: "Bastion",
    cooldown: 28,
    original: "Cooldown 28 s; dorsal and shoulder armour plates interlock: temporary damage mitigation, reduced knockback or partial impact resistance, a possible defensive counterpulse; with the sword embedded light escapes through the gaps. Body curls, segments overlap, thin white-gold lines, plates reopen.",
    desc: "The isopod plates slide together and Bathyas curls behind them for 6 s: Resistance II, knockback mostly absorbed, and Slowness I while curled. Each melee blow on the plates (at most once per second) answers with a COUNTERPULSE: 3 damage, the attacker is thrown back and, with the sun in your chest, SUN-MARKED by the light that leaks through the seams.",
    cast({ p, s }) {
        flag(s, "bastion", BASTION_TICKS);
        tempForm(p, s, "bastion", BASTION_TICKS);
        pose(p, "bat_bastion");
        effect(p, "resistance", BASTION_TICKS, 1, false);
        effect(p, "slowness", BASTION_TICKS, 0, false);
        particle(p.dimension, "plrace:bastion_seams", add(p.location, v3(0, 1.1, 0)));
        sound(p.dimension, "mob.armadillo.roll", p.location, 1, 0.6);
        sound(p.dimension, "mob.shulker.close", p.location, 1, 0.7);
        return true;
    },
};
function counterpulse(p, s, attackerId) {
    if (!attackerId || !hasFlag(s, "bastion") || hasFlag(s, "pulse_cd"))
        return;
    const a = enemiesNear(p, p.location, 6).find((e) => e.id === attackerId);
    if (!a)
        return;
    flag(s, "pulse_cd", 20);
    hurt(a, 3, p);
    knockFrom(a, p.location, 1.2, 0.3);
    if (!drawn(s)) {
        setStatus(a, "sunmarked", 160, p.id);
    }
    particle(p.dimension, "plrace:bastion_seams", add(p.location, v3(0, 1.1, 0)));
    sound(p.dimension, "mob.shulker.close.hurt", p.location, 1, 0.8);
}
const draw = {
    id: "draw_the_sun",
    name: "Draw the Sun",
    short: "Draw",
    cooldown: 45,
    original: "Cooldown 45 s; the signature transformation: grip the hilt, tense, hesitate, extract by force, white-gold light bursts from the chest, the embedded geometry withdraws, the sword becomes a functional held weapon, a different combat posture; Unshackled State with a stability timer. Re-Impalement: a dedicated restoration with its own animation, model transition, state restoration and sound; no permanent corruption; reliable recovery after interruption or death.",
    desc: "DRAW: grip, hesitate, tear the sun out of your chest. It becomes THE IMPALED SUN in your hand - a real sword (it cannot be dropped and never duplicates) - and you are UNSHACKLED: Strength I and Speed I, the predator's stance, the body's light bleeding from the open wound. Stability now drains (slowly for 15 s, then fast); at zero your body fails (Wither) until you RETURN. Use again to RETURN THE SUN: the blade slides back home, Stability +20, a moment of misery. The 45 s cooldown starts on the return. At 2 hearts with no Stability left the body forces the sword back itself (heavy penalty). Death, logout and lineage change always put it back.",
    check({ p, s }) {
        if (daybreak(s))
            return "Not during Abyssal Daybreak";
        if (!drawn(s)) {
            const inv = inventory(p);
            if (inv && inv.getItem(p.selectedSlotIndex) && inv.emptySlotsCount === 0)
                return "Free an inventory slot - your hand must be empty for the sun";
        }
        return undefined;
    },
    freeCast({ s }) {
        return !drawn(s);
    },
    cast({ p, s }) {
        if (drawn(s)) {
            reimpale(p, s, "return");
            return true;
        }
        pose(p, "bat_draw");
        sound(p.dimension, "mob.warden.heartbeat", p.location, 1, 1.2);
        message(s, "§7...", 20);
        after(14, () => {
            if (!p.isValid)
                return;
            if (!giveSword(p)) {
                message(s, "§cNo room in your hands for the sun", 40);
                return;
            }
            setDrawn(p, s, true);
            particle(p.dimension, "plrace:sun_extract", add(p.location, v3(0, 1.25, 0)));
            sound(p.dimension, "item.trident.riptide_3", p.location, 1, 0.6);
            sound(p.dimension, "beacon.activate", p.location, 0.8, 1.4);
            message(s, "§f§lUNSHACKLED §r§7- return the sun before Stability runs out", 70);
        }, p.id, "draw");
        return true;
    },
};
const D = { extinction: 30, sunrise: 60, leviathan: 90, execution: 130, erupt: 150, end: 180 };
const STAGES = ["I Solar Overload", "II Abyssal Extinction", "III Impossible Sunrise", "IV Leviathan Silhouettes", "V Solar Execution", "VI Abyssal Daybreak"];
const dawns = new Map();
function lockStep(p, s, locked) {
    const c = InputPermissionCategory.LateralMovement;
    try {
        p.inputPermissions.setPermissionCategory(c, !locked);
    }
    catch {
    }
    if (locked && !s.data.locks.includes(c))
        s.data.locks.push(c);
    if (!locked)
        s.data.locks = s.data.locks.filter((x) => x !== c);
    s.dirty = true;
}
export function clearAbyssFog(pl) {
    try {
        pl.runCommand(`fog @s remove ${FOG_USER}`);
    }
    catch {
    }
}
function stageOf(t) {
    return t < D.extinction ? 0 : t < D.sunrise ? 1 : t < D.leviathan ? 2 : t < D.execution ? 3 : t < D.erupt ? 4 : 5;
}
const daybreakAbility = {
    id: "abyssal_daybreak",
    name: "ABYSSAL DAYBREAK",
    short: "Daybreak",
    cooldown: 180,
    ultimate: true,
    original: "Unique ultimate, cooldown 180 s; an impossible sunrise in the deepest abyss, six stages: Solar Overload; Abyssal Extinction; Impossible Sunrise; Leviathan Silhouettes (cinematic, not mobs); Solar Execution; Abyssal Daybreak (area damage, pressure waves, Sun-Marked interactions, temporary hazard zones). Afterwards weakness or the sword must be restored. Localised: no permanent world-lighting change. Not Nurariten's procession - biological suffering turned into force.",
    desc: "9 s, standing still:\n I Solar Overload: the sun swells in your chest and you fight it (a hit of 6+ now interrupts: half the cooldown back).\n II Abyssal Extinction: the light around you dies - everyone within 24 blocks sees the deep ocean close in (a dark local haze, never the world's sky or time).\n III Impossible Sunrise: a pillar of white-gold daylight erupts up and down through you.\n IV Leviathan Silhouettes: vast shapes of unknown deep-sea things pass through the light.\n V Solar Execution: you tear the sun out and sweep it through the dark.\n VI Abyssal Daybreak: the field erupts - every enemy within 9 blocks takes 10 damage (15 if SUN-MARKED), is thrown outward and marked; for 6 s more the ground burns with deep-sea daylight (2 damage per second inside 6 blocks).\nThen the sun goes back into your chest, the haze lifts, and you are spent (Slowness II, Weakness I for 6 s). Photic Strain +60.",
    check({ p }) {
        if (dawns.has(p.id))
            return "Daybreak is already breaking";
        return p.isOnGround || p.isInWater ? undefined : "You must stand on something";
    },
    cast({ p, s }) {
        const h = { center: { ...p.location }, fogged: new Set(), stage: 0, wasDrawn: drawn(s), dmg: 0 };
        dawns.set(p.id, h);
        flag(s, "daybreak", D.end + 10);
        lockStep(p, s, true);
        if (h.wasDrawn)
            reimpale(p, s, "cleanup");
        tempForm(p, s, "lure", D.execution);
        pose(p, "bat_overload");
        try {
            p.onScreenDisplay.setTitle("§fABYSSAL DAYBREAK", { subtitle: "§7the sun refuses to stay buried", fadeInDuration: 8, stayDuration: 50, fadeOutDuration: 20 });
        }
        catch {
        }
        sound(p.dimension, "beacon.power", p.location, 1.2, 0.5);
        startChannel(p, s, {
            ability: "abyssal_daybreak",
            mode: "block",
            cancelable: false,
            until: system.currentTick + D.end,
            tick: (s2, p2, t) => dawnTick(p2, s2, h, t),
            end: (s2, p2, reason) => dawnEnd(p2, s2, h, reason),
        });
        addStrain(p, s, 60);
        return true;
    },
};
function pushFog(h, pl) {
    if (h.fogged.has(pl.id) || !settings().heavenFx)
        return;
    try {
        pl.runCommand(`fog @s push ${FOG_ABYSS} ${FOG_USER}`);
        h.fogged.add(pl.id);
    }
    catch {
    }
}
function dawnTick(p, s, h, t) {
    const dim = p.dimension;
    const st = stageOf(t);
    if (st !== h.stage) {
        h.stage = st;
        message(s, `§f${STAGES[st]}`, 50);
    }
    const c = h.center;
    if (st === 0 && t % 4 === 0)
        particle(dim, "plrace:daybreak_overload", add(c, v3(0, 1.25, 0)));
    if (st === 0 && t % 10 === 0)
        sound(dim, "beacon.ambient", c, 1, 0.6 + t / 50);
    if (t === D.extinction) {
        for (const pl of dim.getPlayers({ location: c, maxDistance: 24 }))
            pushFog(h, pl);
        sound(dim, "mob.warden.sonic_charge", c, 0.8, 0.5);
        sound(dim, "conduit.deactivate", c, 1.2, 0.5);
    }
    if (st >= 1 && t % 5 === 0) {
        for (let k = 0; k < 3; k++) {
            const a = Math.random() * 360;
            particle(dim, "plrace:abyss_dark", add(c, add(rotY(v3(0, 0, 3 + Math.random() * 6), a), v3(0, 0.2, 0))));
        }
    }
    if (t === D.sunrise) {
        particle(dim, "plrace:sunrise_pillar", c);
        sound(dim, "beacon.activate", c, 1.4, 0.5);
        sound(dim, "mob.warden.sonic_boom", c, 0.5, 1.6);
    }
    if (t >= D.leviathan && t < D.execution && (t - D.leviathan) % 10 === 0) {
        const k = (t - D.leviathan) / 10;
        const a = k * 97 + 30;
        const pos = add(c, add(rotY(v3(0, 0, 8 + (k % 2) * 2), a), v3(0, 3.2 + (k % 3) * 0.8, 0)));
        const d = rotY(v3(1, 0, 0), a);
        particle(dim, "plrace:leviathan", pos, { dx: d.x, dy: 0, dz: d.z });
        if (k % 2 === 0)
            sound(dim, "mob.elderguardian.idle", c, 1.2, 0.45);
    }
    if (t === D.execution) {
        tempForm(p, s, "daybreak", D.end - D.execution + 10);
        pose(p, "bat_execution");
        particle(dim, "plrace:sun_extract", add(c, v3(0, 1.25, 0)));
        sound(dim, "item.trident.riptide_3", c, 1.2, 0.5);
    }
    if (t === D.execution + 10) {
        particle(dim, "plrace:solar_execution", add(c, v3(0, 1.0, 0)));
        sound(dim, "item.trident.thunder", c, 0.9, 1.3);
    }
    if (t === D.erupt)
        erupt(p, s, h);
}
function erupt(p, s, h) {
    const dim = p.dimension;
    particle(dim, "plrace:daybreak_field", add(h.center, v3(0, 0.1, 0)));
    sound(dim, "mob.warden.sonic_boom", h.center, 1.2, 0.8);
    sound(dim, "random.explode", h.center, 0.8, 0.7);
    let n = 0;
    for (const e of enemiesNear(p, h.center, 9)) {
        const marked = hasStatus(e, "sunmarked");
        hurt(e, marked ? 15 : 10, p);
        knockFrom(e, h.center, 1.4, 0.45);
        setStatus(e, "sunmarked", 160, p.id);
        n++;
    }
    message(s, `§f§lDAYBREAK §r§7- ${n} caught in the light`, 60);
    const c = { ...h.center };
    const ownerId = p.id;
    repeat(20, 6, () => {
        if (!p.isValid)
            return;
        particle(dim, "plrace:daybreak_field", add(c, v3(0, 0.1, 0)));
        for (const e of enemiesNear(p, c, 6, dim)) {
            hurt(e, 2, p);
            effect(e, "slowness", 30, 0);
        }
    }, ownerId, "daybreak_field", 20);
}
function dawnEnd(p, s, h, reason) {
    dawns.delete(s.id);
    for (const pl of world.getPlayers())
        if (h.fogged.has(pl.id))
            clearAbyssFog(pl);
    h.fogged.clear();
    clearFlag(s, "daybreak");
    if (!p.isValid)
        return;
    lockStep(p, s, false);
    refreshForm(p, s);
    if (reason === "interrupt") {
        s.readyAt.set("abyssal_daybreak", system.currentTick + 1800);
        message(s, "§7The sun gutters. §8(interrupted - half the cooldown back)", 60);
        return;
    }
    if (reason === "complete") {
        effect(p, "slowness", 120, 1, false);
        effect(p, "weakness", 120, 0, false);
        pose(p, "bat_return");
        particle(p.dimension, "plrace:sun_return", add(p.location, v3(0, 1.2, 0)));
    }
}
export const bathyas = {
    code: "008",
    key: "bathyas",
    name: "Bathyas, the Sun-Impaled",
    thai: "บาธีอัส ผู้แบกสุริยะ",
    title: "The Creature That Lives by an Unbearable Light",
    color: "§f",
    rarity: "unique",
    tagline: "It survives because of the thing that is killing it - and it is sick of all of you.",
    lore: [
        "Something drove a white-gold sword through the chest of a creature of the deepest abyss - black as the water it came from, jaws like a goblin shark, armour like a giant isopod - and the creature did not die. The sword became its heart.",
        "Bathyas is old, tired and constantly annoyed, mostly by his own light. He squints at it. He covers it with his hand. And when he finally pulls it out, he goes very quiet.",
    ],
    strengths: [
        "Draw the Sun: a real sword in the hand, Strength and Speed - devastating while it lasts",
        "Isopod Bastion: Resistance II with a punishing counterpulse",
        "Lure and Maw Rush: pull enemies into the light, then bite and heal",
        "Abyssal Daybreak: a six-stage ultimate that empties the area around him",
        "At home in deep water: water breathing, conduit power, regeneration in the dark",
    ],
    weaknesses: [
        "Unshackled Risk: drawing the sun drains Stability; at zero the body fails",
        "Photic Misery: too much light (the Lure, the ultimate, bright sun) blinds and slows him",
        "Large Target: projectiles hit 15% harder; no sprinting advantage",
        "The Lure needs the sun in his chest",
    ],
    passives: [
        { name: "Sun-Impaled Core", desc: "While impaled: +2 hearts (Health Boost), a regeneration pulse every 12 s, Stability regenerates, darkness and blindness are burned away." },
        { name: "Abyssal Constitution", desc: "Breathes water; in water Conduit Power (sight, breath, haste); with the head under water, regeneration in the deep." },
        { name: "Irritated Luminary", desc: "In bright open sunlight he squints and gets angry: Strength I, but Photic Strain creeps up." },
        { name: "Harpoon Vitality", desc: "The sword is life support: drawn, the Health Boost is gone and Stability drains; returned, it all comes back." },
    ],
    abilities: [lure, maw, bastion, draw, daybreakAbility],
    focusItem: "plrace:focus_bathyas",
    focusName: "Abyssal Hilt Focus",
    controls: ["Bathyas: the fourth ability DRAWS the sun (a real sword in your hand) and, used again, RETURNS it. Watch the Stability meter."],
    variant(_p, s) {
        if (daybreak(s))
            return "lure";
        return drawn(s) ? "unshackled" : "";
    },
    cooldownMul() {
        return 1;
    },
    init(p, s, first) {
        if (first) {
            s.data.res.stab = 100;
            s.data.res.strain = 0;
        }
        if (drawn(s) || swordCount(p) > 0)
            reimpale(p, s, "cleanup");
        clearAbyssFog(p);
        s.dirty = true;
        save(p, s, true);
    },
    cleanup(p, s) {
        reimpale(p, s, "cleanup");
        purgeSwords(p);
        try {
            p.removeEffect("health_boost");
        }
        catch {
        }
        clearStatusesBy(p.id);
        clearAbyssFog(p);
        delete s.data.res.stab;
        delete s.data.res.strain;
        delete s.data.res.safe;
        delete s.data.st.sun;
    },
    release(s) {
        clearStatusesBy(s.id);
        cancel(s.id, "daybreak_field");
        dawns.delete(s.id);
        if (s.data.st.sun === "drawn") {
            s.data.st.sun = "";
            s.dirty = true;
        }
    },
    tick20(p, s) {
        const now = system.currentTick;
        const isDrawn = drawn(s);
        const swords = swordCount(p);
        if (!isDrawn && swords > 0 && !daybreak(s))
            purgeSwords(p);
        if (isDrawn && swords === 0)
            reimpale(p, s, "cleanup");
        if (isDrawn && swords > 1) {
            purgeSwords(p);
            giveSword(p);
        }
        if (!isDrawn) {
            setStab(s, stability(s) + 5);
            effect(p, "health_boost", 40, 0, false);
            for (const bad of ["darkness", "blindness"]) {
                if (bad === "blindness" && hasFlag(s, "misery"))
                    continue;
                try {
                    if (p.getEffect(bad))
                        p.removeEffect(bad);
                }
                catch {
                }
            }
            if (now % 240 < 20)
                effect(p, "regeneration", 60, 0, false);
        }
        else {
            const safe = s.data.res.safe ?? 0;
            s.data.res.safe = Math.max(0, safe - 20);
            setStab(s, stability(s) - (safe > 0 ? 1.5 : 6));
            effect(p, "strength", 30, 0, false);
            effect(p, "speed", 30, 0, false);
            if (stability(s) <= 0) {
                effect(p, "wither", 40, 1, false);
                effect(p, "slowness", 30, 0, false);
                message(s, "§c§lRETURN THE SUN §r§7- the body is failing", 25);
                let hp = 20;
                try {
                    hp = p.getComponent("minecraft:health")?.currentValue ?? 20;
                }
                catch {
                    hp = 20;
                }
                if (hp <= 4)
                    reimpale(p, s, "forced");
            }
            else if (stability(s) <= 25 && now % 60 < 20) {
                message(s, "§eStability low §7- return the sun soon", 30);
                sound(p.dimension, "mob.warden.heartbeat", p.location, 0.6, 1.4);
            }
        }
        effect(p, "water_breathing", 40, 0, false);
        if (inWater(p))
            effect(p, "conduit_power", 40, 0, false);
        if (headInWater(p) && now % 200 < 20)
            effect(p, "regeneration", 60, 0, false);
        const glare = isOverworld(p) && isDay() && skyExposed(p) && !inWater(p);
        if (glare) {
            effect(p, "strength", 30, 0, false);
            addStrain(p, s, 1);
        }
        else
            addStrain(p, s, -4);
    },
    hud(_p, s) {
        const st = Math.round(stability(s));
        const sr = Math.round(strain(s));
        const state = drawn(s) ? "§f§lUNSHACKLED" : "§7impaled";
        const col = st > 50 ? "§a" : st > 25 ? "§e" : "§c";
        return `${state} §8| §7Stability ${col}${st}% §8| §7Strain §e${sr}%`;
    },
    onHurt(_p, s, ev) {
        const cause = ev.damageSource.cause;
        if (cause === "fall" && hasFlag(s, "nofall")) {
            ev.cancel = true;
            return;
        }
        if (cause === "projectile")
            ev.damage *= 1.15;
        if (hasFlag(s, "bastion") && cause === "entityAttack")
            ev.damage *= 0.85;
    },
    afterHurt(p, s, cause, amount, attackerId) {
        if (cause === "entityAttack")
            counterpulse(p, s, attackerId);
        const ch = s.channel;
        if (ch && ch.ability === "abyssal_daybreak" && system.currentTick - ch.started < D.sunrise) {
            const h = dawns.get(p.id);
            if (h) {
                h.dmg += amount;
                if (amount >= 6 || h.dmg >= 9)
                    endChannel(p, s, "interrupt");
            }
        }
        if (hasFlag(s, "bastion")) {
            try {
                const v = p.getVelocity();
                p.clearVelocity();
                p.applyImpulse({ x: v.x * 0.2, y: Math.min(0, v.y), z: v.z * 0.2 });
            }
            catch {
            }
        }
    },
    onDealDamage(p, s, ev) {
        if (!drawn(s) || ev.damageSource.cause !== "entityAttack")
            return;
        let holding = false;
        try {
            holding = p.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Mainhand)?.typeId === SUN_SWORD;
        }
        catch {
            holding = false;
        }
        if (!holding)
            return;
        const e = ev.hurtEntity;
        system.run(() => {
            if (!p.isValid || !alive(e))
                return;
            particle(p.dimension, "plrace:sun_slash", chest(e));
            if (hasStatus(e, "sunmarked"))
                sound(p.dimension, "item.trident.hit", e.location, 0.8, 1.4);
        });
        if (hasStatus(e, "sunmarked"))
            ev.damage += 3;
    },
};
