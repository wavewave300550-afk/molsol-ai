import { InputPermissionCategory, system } from "@minecraft/server";
import { ENTITY_ECHO } from "../config.js";
import { message, startChannel, tempForm } from "../core/abilities.js";
import { effect, hurt, knockFrom } from "../core/combat.js";
import { inWater, onFire, raining } from "../core/env.js";
import { particle, pose, privateParticle, sound } from "../core/fx.js";
import { flag, hasFlag } from "../core/session.js";
import { aimTarget, chest, enemiesNear, eye, isOpen, isSolid, lineOfSight } from "../core/targets.js";
import { add, dist, flat, mul, norm, sub, v3 } from "../core/util.js";
import { spawnProxy } from "../systems/proxies.js";
import { allWithStatus, clearStatusesBy, hasStatus, setStatus, statusBy, withStatus } from "../systems/status.js";
const IMMUNE = new Set(["minecraft:warden", "minecraft:iron_golem", "minecraft:wither", "minecraft:ender_dragon", "minecraft:elder_guardian", "minecraft:creaking"]);
const records = new Map();
const ghosts = new Map();
const OBSERVE_TICKS = 100;
const KEEP_TICKS = 600;
function infect(p, e, ticks) {
    if (IMMUNE.has(e.typeId))
        return false;
    setStatus(e, "parallax", ticks, p.id);
    effect(e, "slowness", ticks, 0);
    return true;
}
function record(p) {
    const r = records.get(p.id);
    return r && r.keepUntil > system.currentTick ? r : undefined;
}
const sporeveil = {
    id: "parallax_sporeveil",
    name: "Parallax Sporeveil",
    short: "Sporeveil",
    cooldown: 18,
    original: "Cooldown 18 s, radius 6; geometric fungal spores; affected enemies experience a temporary perceptual disturbance: targeting hesitation, movement disruption, misleading afterimages, temporary combat debuffs. Cap gills unfold, mycelial strands vibrate, spores spread in a controlled field. Real mechanics, not purely client-side tricks.",
    desc: "The gills unfold in sequence and release a controlled field of geometric spores 6 blocks around you. Every creature caught is PARALLAX-INFECTED for 6 s: Slowness I, it leaves false afterimages of where it just stood, and 40% of its blows against you land on a version of you that is not there (25% for players). Wardens, iron golems, withers, ender dragons, elder guardians and creakings perceive differently and are not affected.",
    cast({ p, s }) {
        tempForm(p, s, "sporeveil", 32);
        pose(p, "oct_spore");
        particle(p.dimension, "plrace:sporeveil_cloud", add(p.location, v3(0, 1.0, 0)));
        sound(p.dimension, "block.sniffer_egg.crack", p.location, 1, 1.6);
        sound(p.dimension, "mob.glow_squid.ink_squirt", p.location, 0.8, 1.5);
        let n = 0;
        let immune = 0;
        for (const e of enemiesNear(p, p.location, 6)) {
            if (infect(p, e, 120))
                n++;
            else
                immune++;
        }
        message(s, `§5${n} infected${immune ? ` §8(${immune} unaffected)` : ""}`, 40);
        return true;
    },
};
const recordEye = {
    id: "the_eye_that_records",
    name: "The Eye That Records",
    short: "Record",
    cooldown: 22,
    range: 16,
    cone: 10,
    needsTarget: true,
    aim(p) {
        return aimTarget(p, 16, 10);
    },
    original: "Cooldown 22 s, observation 5 s; the central eye focuses on a selected enemy, its movement path is recorded temporarily, the target receives an Observed state; supports later attacks with an understandable tactical advantage.",
    desc: "The Undecimal Eye locks onto a creature up to 16 blocks away and OBSERVES it for 5 s: the eye's sigil hangs over it, you deal it 20% more damage, and every step it takes is recorded - 25 points of its path, kept for 30 s. The Eleventh Frame strikes along that path.",
    cast({ p, s }) {
        const t = recordEye.aim(p, s);
        if (!t)
            return "The eye finds nothing to record";
        if (!lineOfSight(p.dimension, eye(p), chest(t)))
            return "The eye cannot see it";
        setStatus(t, "observed", OBSERVE_TICKS, p.id);
        const now = system.currentTick;
        records.set(p.id, { target: t.id, dim: t.dimension.id, points: [{ ...t.location }], recordUntil: now + OBSERVE_TICKS, keepUntil: now + KEEP_TICKS });
        tempForm(p, s, "record", OBSERVE_TICKS);
        pose(p, "oct_record");
        particle(t.dimension, "plrace:observed_mark", add(chest(t), v3(0, 1.0, 0)));
        sound(p.dimension, "block.eyeblossom.open_long", p.location, 1, 0.7);
        sound(p.dimension, "mob.warden.clicking", p.location, 0.5, 1.6);
        message(s, `§5Recording §f${t.typeId.replace("minecraft:", "")}`, 50);
        return true;
    },
};
const ECHO_TICKS = 60;
const BAD = /(lava|fire|powder_snow|cactus|magma|sweet_berry|wither_rose|campfire|pointed_dripstone|cobweb)/;
function offsetSpot(p, dir, maxDist) {
    const dim = p.dimension;
    const from = p.location;
    let best;
    for (let d = 0.5; d <= maxDist + 1e-6; d += 0.5) {
        const at = add(from, mul(dir, d));
        let ok = true;
        for (const dy of [0.1, 1.1, 1.8]) {
            try {
                const b = dim.getBlock(add(at, v3(0, dy, 0)));
                if (!isOpen(b) || (b && BAD.test(b.typeId)))
                    ok = false;
            }
            catch {
                ok = false;
            }
        }
        if (!ok)
            break;
        best = at;
    }
    if (!best || dist(best, from) < 1.5)
        return undefined;
    for (let k = 0; k < 4; k++) {
        try {
            const below = dim.getBlock(add(best, v3(0, -1 - k, 0)));
            if (below && BAD.test(below.typeId))
                return undefined;
            if (isSolid(below))
                break;
        }
        catch {
            break;
        }
    }
    return best;
}
const offset = {
    id: "hyphal_offset",
    name: "Hyphal Offset",
    short: "Offset",
    cooldown: 26,
    original: "Cooldown 26 s; the mycelial network resonates; rapid short repositioning; a positional afterimage remains at the previous location - two slightly different realities overlapping; reliable collision checks and safe movement.",
    desc: "The eight mycelial groups resonate and you are simply somewhere else: up to 6 blocks in the direction you move (forward when still), never through walls, into lava or fire. An ECHO of you lingers where you were for 3 s; creatures near the old position become PARALLAX-INFECTED for 2.5 s, and when the echo collapses it bursts into spores (3 blocks). Fire destabilises the network: no offset while burning.",
    check({ p }) {
        return onFire(p) ? "The burning mycelium cannot resonate" : undefined;
    },
    cast({ p, s }) {
        let dir = flat(p.getViewDirection());
        try {
            const vel = p.getVelocity();
            if (Math.hypot(vel.x, vel.z) > 0.05)
                dir = flat(vel);
        }
        catch {
        }
        dir = norm(dir);
        const to = offsetSpot(p, dir, 6);
        if (!to)
            return "No room to resonate into";
        const from = { ...p.location };
        tempForm(p, s, "offset", 18);
        pose(p, "oct_offset");
        particle(p.dimension, "plrace:offset_rift", add(from, v3(0, 1.0, 0)));
        for (const e of enemiesNear(p, from, 4))
            infect(p, e, 50);
        const echo = spawnProxy(p, ENTITY_ECHO, from, {
            kind: "echo",
            ticks: ECHO_TICKS,
            yaw: p.getRotation().y,
            end: (px) => {
                const at = px.entity.isValid ? px.entity.location : from;
                particle(px.entity.dimension, "plrace:geo_spores", add(at, v3(0, 1.0, 0)));
                if (p.isValid)
                    for (const e of enemiesNear(p, at, 3))
                        infect(p, e, 80);
            },
        });
        if (!echo)
            particle(p.dimension, "plrace:parallax_echo", add(from, v3(0, 1.0, 0)));
        try {
            p.teleport(to, { keepVelocity: false, checkForBlocks: true });
        }
        catch {
            return "No room to resonate into";
        }
        particle(p.dimension, "plrace:offset_rift", add(to, v3(0, 1.0, 0)));
        sound(p.dimension, "mob.shulker.teleport", to, 1, 0.6);
        sound(p.dimension, "chime.amethyst_block", to, 1, 0.5);
        flag(s, "nofall", 40);
        return true;
    },
};
const FRAME_TICKS = 70;
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
function thin(points, n) {
    if (points.length <= n)
        return points.slice();
    const out = [];
    for (let i = 0; i < n; i++)
        out.push(points[Math.round((i * (points.length - 1)) / (n - 1))]);
    return out;
}
const frame = {
    id: "the_eleventh_frame",
    name: "The Eleventh Frame",
    short: "Frame",
    cooldown: 48,
    original: "Cooldown 48 s; signature attack: the eye abruptly stops; its eleven rings open sequentially; recorded target positions appear as layered afterimages; mycelial filaments extend toward them; a geometric network connects the recorded path; the network delivers timed attacks along the trajectory; all images collapse back into the eye. Must interact with The Eye That Records; not a generic beam or explosion.",
    desc: "3.5 s, rooted. The eye stops; its eleven rings open one by one; every point of the path you RECORDED appears as an afterimage; filaments reach out to them and knit the path into one geometric network - then the network fires along it in order: each point strikes everything within 1.8 blocks for 4 damage (the OBSERVED creature takes 6; a creature is struck at most 4 times), and the observed creature takes a final 4 as the images collapse into the eye. With no recording, the Frame strikes the current positions of up to 5 hostile creatures within 12 blocks (4 damage each).",
    check({ s }) {
        return s.channel?.ability === "the_eleventh_frame" ? "The Frame is already open" : undefined;
    },
    cast({ p, s }) {
        const rec = record(p);
        let points = [];
        let observed;
        if (rec && rec.dim === p.dimension.id && rec.points.length) {
            points = thin(rec.points, 12);
            observed = rec.target;
        }
        else {
            points = enemiesNear(p, p.location, 12).slice(0, 5).map((e) => ({ ...e.location }));
            if (!points.length)
                return "Nothing recorded and nothing in sight";
            message(s, "§7No recorded path - the Frame strikes what it sees now", 50);
        }
        tempForm(p, s, "frame", FRAME_TICKS + 4);
        pose(p, "oct_frame");
        lockStep(p, s, true);
        sound(p.dimension, "block.eyeblossom.close_long", p.location, 1, 0.5);
        sound(p.dimension, "mob.warden.sonic_charge", p.location, 0.4, 1.8);
        const hits = new Map();
        startChannel(p, s, {
            ability: "the_eleventh_frame",
            mode: "block",
            cancelable: false,
            until: system.currentTick + FRAME_TICKS,
            tick: (_s2, p2, t) => frameTick(p2, t, points, observed, hits),
            end: (s2, p2) => {
                lockStep(p2, s2, false);
                records.delete(s2.id);
            },
        });
        return true;
    },
};
function frameTick(p, t, points, observed, hits) {
    const dim = p.dimension;
    const e0 = eye(p);
    if (t % 6 === 0 && t < 36)
        particle(dim, "plrace:frame_ring", add(e0, mul(flat(p.getViewDirection()), 0.6)));
    if (t === 4)
        sound(dim, "chime.amethyst_block", p.location, 1, 0.5);
    const show = t - 6;
    if (show >= 0 && show % 2 === 0 && show / 2 < points.length)
        particle(dim, "plrace:record_point", add(points[show / 2], v3(0, 0.9, 0)));
    if (t === 26 || t === 32) {
        for (let i = 0; i < points.length; i++) {
            const a = t === 26 ? e0 : add(points[Math.max(0, i - 1)], v3(0, 0.9, 0));
            const b = add(points[i], v3(0, 0.9, 0));
            const d = sub(b, a);
            if (t === 26 || i > 0)
                particle(dim, "plrace:frame_thread", a, { dx: d.x, dy: d.y, dz: d.z });
        }
        sound(dim, "mob.warden.clicking", p.location, 0.7, 1.4);
    }
    const k = (t - 36) / 2;
    if (t >= 36 && (t - 36) % 2 === 0 && k < points.length) {
        const at = points[k];
        particle(dim, "plrace:frame_strike", add(at, v3(0, 0.7, 0)));
        sound(dim, "hit.amethyst_cluster", at, 0.9, 0.6 + k * 0.05);
        for (const e of enemiesNear(p, at, 1.8)) {
            const isObs = e.id === observed;
            const n = hits.get(e.id) ?? 0;
            if (n >= 4)
                continue;
            hits.set(e.id, n + 1);
            hurt(e, isObs ? 6 : 4, p);
        }
    }
    if (t === 62) {
        particle(dim, "plrace:frame_collapse", e0);
        sound(dim, "block.eyeblossom.close", p.location, 1, 0.6);
        if (observed) {
            const tgt = enemiesNear(p, p.location, 24).find((e) => e.id === observed);
            if (tgt) {
                hurt(tgt, 4, p);
                knockFrom(tgt, p.location, -0.4, 0.1);
            }
        }
    }
}
export const octamyces = {
    code: "009",
    key: "octamyces",
    name: "Octamyces Undecimus",
    thai: "ออคทา-ไมซีส แห่งรอยแยกที่ 11",
    title: "The Witness of Eleven Realities",
    color: "§5",
    tagline: "Something is observing you from a reality you cannot observe in return.",
    lore: [
        "What stands in the world is only part of it: a mushroom-shaped fruiting body, eight groups of mycelium, and an immense geometric eye whose eleven rings each watch a different version of what is happening.",
        "It does not seem malicious. It does not seem anything. It watches - and when it stops moving, only the eye keeps going.",
    ],
    strengths: [
        "Control through perception: infected enemies miss their blows and leave false afterimages",
        "Observation turns into damage: the Eleventh Frame strikes along a recorded path",
        "Hyphal Offset: a safe, collision-checked reposition that leaves an echo",
        "Floats: half fall damage, glides when sneaking in the air",
    ],
    weaknesses: [
        "Fire destabilises it: +50% fire damage, a scorched body and no Hyphal Offset while burning",
        "Fragile: takes 10% more damage from everything",
        "Some senses are not fooled (wardens, iron golems, withers, dragons, elder guardians, creakings)",
        "Floating grants no immunity to hazards",
    ],
    passives: [
        { name: "Resonant Levitation", desc: "Hovers above the ground on resonant mycelium: fall damage halved; hold SNEAK in the air to drift down. Not flight." },
        { name: "Panoptic Witness", desc: "The eye tracks on its own. Invisible creatures within 12 blocks are revealed to you; blindness and darkness cannot close it." },
        { name: "Spore Affinity", desc: "In damp or dark places - rain, water, low light - a regeneration pulse every 10 s." },
        { name: "Dimensional Afterimage", desc: "While sprinting, faint echoes of you trail behind." },
    ],
    abilities: [sporeveil, recordEye, offset, frame],
    focusItem: "plrace:focus_octamyces",
    focusName: "Undecimal Lens Focus",
    controls: ["Octamyces: RECORD a creature first - The Eleventh Frame strikes along the path it walked."],
    variant(p) {
        return onFire(p) ? "unstable" : "";
    },
    cooldownMul() {
        return 1;
    },
    init() {
    },
    cleanup(p) {
        clearStatusesBy(p.id);
        records.delete(p.id);
    },
    release(s) {
        clearStatusesBy(s.id);
        records.delete(s.id);
    },
    tick20(p) {
        const now = system.currentTick;
        for (const bad of ["blindness", "darkness"]) {
            try {
                if (p.getEffect(bad))
                    p.removeEffect(bad);
            }
            catch {
            }
        }
        try {
            for (const e of p.dimension.getEntities({ location: p.location, maxDistance: 12 })) {
                if (e.id === p.id)
                    continue;
                try {
                    if (e.getEffect("invisibility"))
                        privateParticle(p, "plrace:parallax_motes", add(e.location, v3(0, 1.0, 0)));
                }
                catch {
                }
            }
        }
        catch {
        }
        let damp = inWater(p) || raining(p);
        if (!damp) {
            try {
                damp = p.dimension.getLightLevel(add(p.location, v3(0, 1, 0))) < 7;
            }
            catch {
                damp = false;
            }
        }
        if (damp && now % 200 < 20)
            effect(p, "regeneration", 60, 0, false);
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
            if (vy < -0.12)
                effect(p, "slow_falling", 10, 0, false);
        }
        if (p.isSprinting && system.currentTick % 10 < 5 && !hasFlag(s, "echo_cd")) {
            flag(s, "echo_cd", 10);
            particle(p.dimension, "plrace:parallax_echo", add(p.location, v3(0, 1.0, 0)));
        }
    },
    hud(p, s) {
        const r = record(p);
        const rec = r ? `§5recorded §f${r.points.length}§7 points §8(${Math.ceil((r.keepUntil - system.currentTick) / 20)} s)` : "§8no recording";
        const inf = withStatus("parallax", s.id).length;
        return `${rec} §8| §7infected §d${inf}`;
    },
    onHurt(_p, _s, ev) {
        const cause = ev.damageSource.cause;
        if (cause === "fall") {
            ev.damage *= 0.5;
            return;
        }
        if (cause === "fire" || cause === "fireTick" || cause === "lava")
            ev.damage *= 1.5;
        else
            ev.damage *= 1.1;
        const src = ev.damageSource.damagingEntity;
        if (src && hasStatus(src, "parallax") && (cause === "entityAttack" || cause === "projectile")) {
            const miss = src.typeId === "minecraft:player" ? 0.25 : 0.4;
            if (Math.random() < miss)
                ev.cancel = true;
        }
    },
    onDealDamage(p, _s, ev) {
        if (statusBy(ev.hurtEntity, "observed") === p.id)
            ev.damage *= 1.2;
    },
    worldTick4() {
        const now = system.currentTick;
        for (const [pid, r] of records) {
            if (r.keepUntil <= now) {
                records.delete(pid);
                continue;
            }
            if (r.recordUntil <= now)
                continue;
            for (const e of withStatus("observed", pid)) {
                if (e.id !== r.target)
                    continue;
                const last = r.points[r.points.length - 1];
                if (!last || dist(last, e.location) > 0.25)
                    r.points.push({ ...e.location });
                if (r.points.length > 25)
                    r.points.shift();
            }
        }
        if (now % 8 === 0) {
            const seen = new Set();
            for (const e of allWithStatus("parallax")) {
                seen.add(e.id);
                const trail = ghosts.get(e.id) ?? [];
                trail.push({ ...e.location });
                if (trail.length > 3)
                    trail.shift();
                ghosts.set(e.id, trail);
                if (trail.length >= 3 && dist(trail[0], e.location) > 0.6)
                    particle(e.dimension, "plrace:parallax_echo", add(trail[0], v3(0, 0.9, 0)));
            }
            for (const id of ghosts.keys())
                if (!seen.has(id))
                    ghosts.delete(id);
        }
    },
};
