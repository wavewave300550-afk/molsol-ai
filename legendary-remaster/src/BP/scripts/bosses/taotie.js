/**
 * TAOTIE (饕餮) — the Devouring Maw.
 *
 * Identity: hunger. It pulls, swallows and eats — dropped items heal it — and
 * players survive by keeping distance, jumping its quake rings and hiding
 * behind the bronze ding vessels it calls down.
 *
 *   I   The Feast Begins   claw, charge, inhale, quake (jumpable ring), pounce
 *   II  Endless Hunger     Paoxiao's armpit eyes open: sweeping eye-beams,
 *                          falling ding vessels (shelters!), bile spit
 *   III The Self-Devourer  it eats its own body; a flying head on a vortex:
 *                          head-ram, bite chains, leiwen bullet spiral
 *   ULT Maw of Ten Thousand Feasts — a world-swallowing pull; only the dings
 *                          block it; then the jaws snap shut.
 */
import { EntityDamageCause } from "@minecraft/server";
import { TAOTIE_ACTS } from "../generated/data.js";
import { effect, fightersNear, grounded, hurt, inCircle, inCone, inLine, inRingBand, knock } from "../core/combat.js";
import { burst, C, deco, flash, glint, mote, shake, shock, sound, teleCircle, teleCone, teleLine, beam, bullet } from "../core/fx.js";
import { fire, moveProp, particleBullet, propAct, removeProp, spawnProp, zone } from "../core/hazards.js";
import { blocked } from "../core/terrain.js";
import { add, dirOfYaw, dist, flatDir, flatDist, norm, randIn, scale, segDist, sub } from "../core/vec.js";
import { Boss } from "./boss.js";
import { ahead, lead, strike } from "./kit.js";
const A = TAOTIE_ACTS;
const SCALE = 1.6;
export class Taotie extends Boss {
    constructor(e) {
        super(e, "taotie");
        this.acts = A;
        this.walkSpeed = 0.19;
        this.title = "饕餮 Taotie";
        this.ultName = "Maw of Ten Thousand Feasts";
        this.phaseNames = ["", "", "Endless Hunger", "The Self-Devourer"];
        this.thresholds = [0.66, 0.33];
        this.defeatText = "§e✦ Taotie's hunger is stilled";
        this.ultPhase = 3;
        this.ultCooldown = 920;
        this.sigil = "legends:sigil_taotie";
        this.dings = [];
    }
    onInit() {
        if (this.phase >= 3)
            this.flying = true;
    }
    mouth() {
        return this.phase >= 3 ? ahead(this, 1.6 * SCALE, 1.2 * SCALE) : ahead(this, 3.5 * SCALE, 1.9 * SCALE);
    }
    // ---------------------------------------------------------------- idle movement
    idle() {
        const t = this.target;
        if (this.leashed() || !t) {
            if (this.flying)
                this.fly({ x: this.home.x, y: this.ground(this.home).y + 3, z: this.home.z }, 0.25);
            else
                this.walk(this.home, this.walkSpeed, 2);
            return;
        }
        if (this.flying) {
            const g = this.ground(t.location).y;
            const ang = this.t * 1.2;
            const p = add(t.location, scale(dirOfYaw(ang), 6));
            this.fly({ x: p.x, y: g + 3.2, z: p.z }, 0.22);
            this.face(t.location, 12);
        }
        else {
            this.walk(t.location, this.walkSpeed, 5.5);
        }
    }
    onTick() {
        // gluttony: dropped items close to the maw are devoured and heal it
        if (this.t % 20 === 0 && !this.invuln) {
            try {
                const items = this.dim.getEntities({ type: "minecraft:item", location: this.mouth(), maxDistance: 4.5 });
                for (const it of items.slice(0, 4)) {
                    burst(this.dim, it.location, C.hunger, 8, 2);
                    it.remove();
                    this.heal(this.maxHp * 0.008);
                }
            }
            catch {
                // ignore
            }
        }
        if (this.phase >= 3 && this.t % 6 === 0)
            deco(this.dim, "smoke", { x: this.pos.x, y: this.pos.y + 0.5, z: this.pos.z }, C.hunger, 2, 1.2, 0.6, 0.3);
        this.dings = this.dings.filter((d) => d.isValid);
    }
    heal(amount) {
        const h = this.entity.getComponent("minecraft:health");
        if (h)
            h.setCurrentValue(Math.min(h.effectiveMax, h.currentValue + amount));
    }
    // ---------------------------------------------------------------- entrance / transitions
    *entrance() {
        const g = this.ground(this.pos);
        this.place(g, this.yaw);
        const a = this.act("emerge");
        for (let k = 0; k < a.ticks; k += 4) {
            deco(this.dim, "smoke", add(g, { x: 0, y: 0.5, z: 0 }), C.hunger, 6, 3.5, 0.9, 0.6);
            deco(this.dim, "shard", add(g, { x: 0, y: 0.3, z: 0 }), C.bronze, 3, 3, 0.3, 4);
            if (k === a.marks[0] - (a.marks[0] % 4)) {
                sound(this.dim, "mob.ravager.roar", g, 4, 0.55);
                shake(this.audience(), 0.5, 1.2);
                shock(this.dim, g, 14, 16, C.bronze);
            }
            yield 4;
        }
        this.endAct();
        this.say("§6饕餮 Taotie awakens", 0);
    }
    *transition(to) {
        if (to === 2) {
            this.setPhase(2);
            const a = this.act("roar");
            sound(this.dim, "mob.ravager.roar", this.pos, 4, 0.5);
            yield a.marks[0];
            shake(this.audience(), 0.45, 1.0);
            shock(this.dim, this.pos, 16, 14, C.ember);
            for (const s of [-1, 1])
                glint(this.dim, ahead(this, 1.2 * SCALE, 2.2, s * 2.6), C.ember, 2.5);
            yield a.ticks - a.marks[0];
            this.endAct();
            return;
        }
        // to 3: it devours its own body
        const a = this.act("devour");
        let last = 0;
        for (const m of a.marks) {
            yield m - last;
            last = m;
            sound(this.dim, "mob.ravager.bite", this.pos, 3, 0.6);
            deco(this.dim, "smoke", add(this.pos, { x: 0, y: 2.5, z: 0 }), C.hunger, 14, 2.5, 1.0, 1.2);
            burst(this.dim, add(this.pos, { x: 0, y: 2.5, z: 0 }), C.bronze, 16, 4, 0.3, 1.5);
        }
        this.setPhase(3);
        this.flying = true;
        this.prop("fly", 1);
        shake(this.audience(), 0.6, 1.4);
        sound(this.dim, "mob.wither.spawn", this.pos, 3, 0.7);
        deco(this.dim, "smoke", add(this.pos, { x: 0, y: 1.5, z: 0 }), C.hunger, 30, 3.5, 1.4, 2);
        const rise = a.ticks - last;
        const g = this.ground(this.pos).y;
        for (let k = 0; k < rise; k++) {
            this.place({ x: this.pos.x, y: this.pos.y + (g + 3.2 - this.pos.y) * 0.12, z: this.pos.z });
            yield 1;
        }
        this.endAct();
    }
    // ---------------------------------------------------------------- skills
    skills() {
        return [
            { name: "claw", phases: [1, 2], cd: 50, weight: 4, max: 7.5, run: (t) => this.claw(t) },
            { name: "charge", phases: [1, 2], cd: 160, weight: 3, min: 8, max: 28, run: (t) => this.charge(t) },
            { name: "inhale", phases: [1, 2, 3], cd: 300, weight: 2, max: 16, run: (t) => this.inhale(t) },
            { name: "quake", phases: [1, 2], cd: 180, weight: 3, max: 12, run: () => this.quake() },
            { name: "pounce", phases: [1, 2], cd: 140, weight: 3, min: 7, max: 18, run: (t) => this.pounce(t) },
            { name: "gaze", phases: [2], cd: 240, weight: 3, max: 16, run: (t) => this.gaze(t) },
            { name: "dings", phases: [2, 3], cd: 380, weight: 2, run: () => this.dingDrop(3) },
            { name: "spit", phases: [2], cd: 160, weight: 3, min: 5, run: (t) => this.spit(t) },
            { name: "ram", phases: [3], cd: 90, weight: 4, min: 5, max: 26, run: (t) => this.ram(t) },
            { name: "bites", phases: [3], cd: 70, weight: 4, max: 6, run: (t) => this.bites(t) },
            { name: "spiral", phases: [3], cd: 260, weight: 3, run: () => this.spiral() },
        ];
    }
    *approach(t, range, maxTicks = 40) {
        for (let k = 0; k < maxTicks && flatDist(this.pos, t.location) > range; k++) {
            if (this.flying)
                this.fly({ x: t.location.x, y: this.pos.y, z: t.location.z }, 0.3, range);
            else
                this.walk(t.location, this.walkSpeed * 1.3, range);
            yield 1;
        }
    }
    *claw(t) {
        yield* this.approach(t, 6.5, 20);
        this.faceNow(t.location);
        const a = this.act("claw");
        const reach = 8;
        teleCone(this.dim, this.ground(this.pos), dirOfYaw(this.yaw), 110, reach, a.marks[0]);
        yield a.marks[0];
        sound(this.dim, "mob.ravager.bite", this.pos, 2, 0.7);
        strike(this, this.pos, reach + 1, (p) => inCone(p, this.pos, dirOfYaw(this.yaw), 110, reach), 14, { knock: 0.9, up: 0.25 });
        this.face(t.location, 40);
        teleCone(this.dim, this.ground(this.pos), dirOfYaw(this.yaw), 110, reach, a.marks[1] - a.marks[0]);
        yield a.marks[1] - a.marks[0];
        sound(this.dim, "mob.ravager.bite", this.pos, 2, 0.6);
        strike(this, this.pos, reach + 1, (p) => inCone(p, this.pos, dirOfYaw(this.yaw), 110, reach), 14, { knock: 1.1, up: 0.3 });
        yield a.ticks - a.marks[1];
    }
    *charge(t) {
        this.faceNow(t.location);
        const w = this.act("windup");
        const dir = flatDir(this.pos, t.location);
        const len = Math.min(30, flatDist(this.pos, t.location) + 6);
        teleLine(this.dim, this.ground(this.pos), dir, len, 4, w.ticks);
        sound(this.dim, "mob.ravager.roar", this.pos, 2, 0.9);
        yield w.ticks;
        this.act("charge");
        const dest = add(this.pos, scale(dir, len));
        const hit = new Set();
        yield* this.dash(dest, 0.95, () => {
            deco(this.dim, "shard", this.pos, C.bronze, 3, 1.5, 0.3, 3);
            strike(this, this.pos, 5, (p) => flatDist(p.location, this.pos) < 3.2 * SCALE, 18, { knock: 1.8, up: 0.55, once: hit });
        });
        shock(this.dim, this.pos, 6, 8, C.bronze);
        sound(this.dim, "mob.ravager.stun", this.pos, 2, 0.8);
        this.endAct();
        yield 14;
    }
    /** Shelter test: a ding standing between the player and the maw blocks the pull and the snap. */
    sheltered(p, from) {
        for (const d of this.dings) {
            if (!d.isValid)
                continue;
            const s = segDist(d.location, from, p.location);
            if (s.t > 0.05 && s.t < 0.98 && flatDist(d.location, add(from, scale(sub(p.location, from), s.t))) < 1.9)
                return true;
        }
        return blocked(this.dim, from, add(p.location, { x: 0, y: 1, z: 0 }));
    }
    *inhale(t) {
        this.faceNow(t.location);
        const a = this.act("inhale");
        const range = 17;
        const dir = dirOfYaw(this.yaw);
        teleCone(this.dim, this.ground(this.pos), dir, 80, range, a.marks[0], C.warn);
        const m0 = this.mouth();
        teleCircle(this.dim, this.ground(m0), 4.2, a.marks[0]);
        sound(this.dim, "mob.warden.sonic_charge", this.pos, 3, 0.5);
        for (let k = 0; k < a.marks[0]; k++) {
            const mouth = this.mouth();
            if (k > 8) {
                for (const p of fightersNear(this.dim, mouth, range + 2)) {
                    if (!inCone(p, this.pos, dir, 80, range))
                        continue;
                    if (this.sheltered(p, mouth))
                        continue;
                    knock(p, mouth, -0.32, 0.02);
                    if (k % 20 === 0)
                        effect(p, "hunger", 100, 1);
                }
            }
            if (k % 3 === 0) {
                const off = add(mouth, scale(dirOfYaw(this.yaw + randIn(-40, 40)), randIn(6, range)));
                bullet(this.dim, off, norm(sub(mouth, off)), 18, 8, C.hunger, 0.3);
            }
            yield 1;
        }
        const mouth = this.mouth();
        sound(this.dim, "mob.ravager.bite", mouth, 4, 0.5);
        shake(this.audience(), 0.35, 0.5);
        burst(this.dim, mouth, C.hunger, 24, 5, 0.35, 1);
        strike(this, mouth, 6, (p) => flatDist(p.location, mouth) <= 4.2 && Math.abs(p.location.y - mouth.y) < 4, 26, { knock: 1.4, up: 0.5, effects: [["hunger", 200, 2]] });
        yield a.ticks - a.marks[0];
    }
    *quake() {
        const a = this.act("quake");
        const c = this.ground(ahead(this, 2.5));
        teleCircle(this.dim, c, 4.5, a.marks[0]);
        yield a.marks[0];
        sound(this.dim, "mob.warden.attack", c, 4, 0.5);
        shake(this.audience(), 0.5, 0.8);
        shock(this.dim, c, 15, 12, C.bronze);
        strike(this, c, 6, (p) => inCircle(p, c, 4.5), 18, { knock: 1.2, up: 0.6, from: c });
        const hit = new Set();
        // expanding shockwave ring: jump over it!
        for (let k = 1; k <= 12; k++) {
            const r = 4.5 + k * 0.9;
            strike(this, c, r + 2, (p) => grounded(p) && inRingBand(p, c, r - 0.9, r + 0.4, 2), 12, { knock: 0.8, up: 0.5, from: c, once: hit });
            yield 1;
        }
        yield Math.max(1, a.ticks - a.marks[0] - 12);
    }
    *pounce(t) {
        this.faceNow(t.location);
        const a = this.act("pounce");
        const dest = this.ground(lead(t, 10));
        teleCircle(this.dim, dest, 3.6, a.marks[0] + 14);
        yield a.marks[0];
        sound(this.dim, "mob.ravager.roar", this.pos, 2, 1.2);
        yield* this.leap(dest, 14, 4.5);
        shock(this.dim, dest, 7, 10, C.bronze);
        shake(this.audience(), 0.35, 0.5);
        strike(this, dest, 5, (p) => inCircle(p, dest, 3.6), 16, { knock: 1.2, up: 0.5, from: dest });
        yield Math.max(4, a.ticks - a.marks[0] - 14);
    }
    *gaze(t) {
        this.faceNow(t.location);
        const a = this.act("gaze");
        const start = a.marks[0];
        const sweep = a.ticks - start - 8;
        for (const s of [-1, 1])
            teleCone(this.dim, this.ground(this.pos), dirOfYaw(this.yaw + s * 95), 130, 17, start, C.warn);
        sound(this.dim, "mob.elderguardian.curse", this.pos, 3, 0.8);
        yield start;
        const hit = new Map();
        for (let k = 0; k < sweep; k++) {
            const ang = 30 + (120 * k) / sweep;
            for (const s of [-1, 1]) {
                const eye = ahead(this, 1.2 * SCALE, 1.9, s * 2.6);
                const dir = dirOfYaw(this.yaw + s * ang);
                const end = add(eye, scale(dir, 17));
                if (k % 2 === 0)
                    beam(this.dim, eye, end, C.ember, 0.5);
                for (const p of fightersNear(this.dim, eye, 19)) {
                    if (!inLine(p, eye, dir, 17, 1.8, 3))
                        continue;
                    if ((hit.get(p.id) ?? -99) > k - 10)
                        continue;
                    hit.set(p.id, k);
                    hurt(p, 9, this.entity, EntityDamageCause.magic);
                    try {
                        p.setOnFire(3, true);
                    }
                    catch {
                        // ignore
                    }
                }
            }
            yield 1;
        }
        yield 8;
    }
    /** Bronze ding vessels crash down near players and remain as shelters. */
    *dingDrop(n) {
        const a = this.act("summon");
        yield a.marks[0];
        sound(this.dim, "mob.ravager.roar", this.pos, 3, 0.7);
        const spots = [];
        const targets = this.fighters.length ? this.fighters : [];
        for (let i = 0; i < n; i++) {
            const base = targets.length ? targets[i % targets.length].location : this.home;
            const p = this.ground(add(base, { x: randIn(-5, 5), y: 0, z: randIn(-5, 5) }));
            spots.push(p);
            teleCircle(this.dim, p, 2.6, 26);
        }
        for (const p of spots)
            this.dropDing(p);
        yield Math.max(6, a.ticks - a.marks[0]);
    }
    dropDing(p) {
        while (this.dings.length >= 5)
            removeProp(this.dings.shift());
        const e = spawnProp(this.dim, "ding", add(p, { x: 0, y: 14, z: 0 }), randIn(0, 360), this.entity);
        if (!e)
            return;
        fire({
            dim: this.dim, pos: add(p, { x: 0, y: 14, z: 0 }), vel: { x: 0, y: -0.55, z: 0 }, life: 40, radius: 2.4, dmg: 0,
            owner: this.entity, entity: undefined, ground: true,
            trail: (s) => moveProp(e, s.pos),
            onEnd: (s) => {
                const at = this.ground(s.pos);
                moveProp(e, at);
                sound(this.dim, "random.anvil_land", at, 2, 0.5);
                shock(this.dim, at, 5, 8, C.bronze);
                deco(this.dim, "shard", add(at, { x: 0, y: 0.5, z: 0 }), C.bronze, 10, 2, 0.35, 5);
                strike(this, at, 4, (pl) => inCircle(pl, at, 2.6), 20, { knock: 1.2, up: 0.4, from: at });
                this.dings.push(e);
                propAct(e, 0);
            },
        });
    }
    *spit(t) {
        this.faceNow(t.location);
        const a = this.act("spit");
        const goals = [0, 1, 2].map((i) => this.ground(add(lead(t, 14), { x: randIn(-3.5, 3.5), y: 0, z: randIn(-3.5, 3.5) })));
        for (const g of goals)
            teleCircle(this.dim, g, 2.6, a.marks[0] + 18);
        yield a.marks[0];
        sound(this.dim, "mob.llama.spit", this.pos, 3, 0.5);
        for (const g of goals) {
            const from = this.mouth();
            const T = 18;
            const vel = { x: (g.x - from.x) / T, y: (g.y - from.y) / T + 0.03 * T * 0.5, z: (g.z - from.z) / T };
            fire({
                dim: this.dim, pos: from, vel, life: T + 4, radius: 0.8, dmg: 8, owner: this.entity, gravity: 0.03, ground: true,
                trail: (s) => mote(this.dim, s.pos, C.venom, 0.45, 0.4),
                onEnd: (s) => {
                    const at = this.ground(s.pos);
                    burst(this.dim, at, C.venom, 14, 3);
                    zone(this.dim, at, 2.6, 120, { dmg: 3, every: 10, col: C.venom, owner: this.entity, kind: "acid",
                        onTick: (p) => effect(p, "hunger", 60, 1) });
                },
            });
        }
        yield a.ticks - a.marks[0];
    }
    // ---------------------------------------------------------------- phase III skills
    *ram(t) {
        this.faceNow(t.location);
        const a = this.act("ram");
        const dir = flatDir(this.pos, t.location);
        const len = Math.min(28, flatDist(this.pos, t.location) + 5);
        teleLine(this.dim, this.ground(this.pos), dir, len, 3.4, a.marks[0]);
        yield a.marks[0];
        sound(this.dim, "mob.ravager.roar", this.pos, 3, 1.1);
        const dest = add(this.pos, scale(dir, len));
        dest.y = this.ground(dest).y + 1.2;
        const hit = new Set();
        for (let k = 0; k < 40 && dist(this.pos, dest) > 0.6; k++) {
            this.fly(dest, 1.05, 0, 40);
            deco(this.dim, "smoke", this.pos, C.hunger, 2, 0.8, 0.5, 0.3);
            strike(this, this.pos, 4, (p) => dist(p.location, this.pos) < 2.8, 20, { knock: 1.8, up: 0.6, once: hit });
            yield 1;
        }
        shock(this.dim, this.ground(this.pos), 6, 8, C.bronze);
        yield Math.max(6, a.ticks - a.marks[0] - 10);
    }
    *bites(t) {
        yield* this.approach(t, 3.5, 16);
        const a = this.act("bites");
        let last = 0;
        for (const m of a.marks) {
            this.face(t.location, 60);
            teleCone(this.dim, this.ground(this.pos), dirOfYaw(this.yaw), 90, 5.5, m - last);
            yield m - last;
            last = m;
            sound(this.dim, "mob.ravager.bite", this.pos, 2, 0.8);
            strike(this, this.pos, 7, (p) => inCone(p, this.pos, dirOfYaw(this.yaw), 90, 5.5, 5), 12, { knock: 0.7, up: 0.2 });
        }
        yield a.ticks - last;
    }
    *spiral() {
        const a = this.act("spiral");
        yield a.marks[0];
        sound(this.dim, "mob.evocation_illager.cast_spell", this.pos, 3, 0.6);
        const total = a.ticks - a.marks[0] - 6;
        for (let k = 0; k < total; k += 2) {
            for (let arm = 0; arm < 3; arm++) {
                const yaw = k * 7 + arm * 120;
                const from = add(this.pos, { x: 0, y: 1.0, z: 0 });
                particleBullet(this.dim, from, dirOfYaw(yaw), 0.42, 44, 7, C.gold, this.entity, 0.55, 0.75);
            }
            yield 2;
        }
        yield 6;
    }
    // ---------------------------------------------------------------- ultimate
    *ultimate() {
        const center = this.ground(this.home);
        const top = { x: center.x, y: center.y + 7, z: center.z };
        for (let k = 0; k < 30 && dist(this.pos, top) > 0.5; k++) {
            this.fly(top, 0.45, 0, 30);
            yield 1;
        }
        if (this.target)
            this.faceNow(this.target.location);
        const a = this.act("maw");
        sound(this.dim, "mob.wither.spawn", this.pos, 4, 0.5);
        shake(this.audience(), 0.4, 2);
        // dings rain down: the only shelter
        const n = Math.max(3, Math.min(6, this.fighters.length + 2));
        for (let i = 0; i < n; i++) {
            const ang = (i / n) * 360 + randIn(-20, 20);
            const p = this.ground(add(center, scale(dirOfYaw(ang), randIn(7, 13))));
            teleCircle(this.dim, p, 2.6, 30, { red: 1, green: 0.86, blue: 0.32 });
            this.dropDing(p);
        }
        const snap = a.marks[0];
        for (let k = 0; k < snap; k++) {
            const mouth = this.mouth();
            if (k === 30)
                teleCircle(this.dim, this.ground(mouth), 7, snap - 30);
            if (k > 30) {
                const pull = 0.12 + 0.3 * ((k - 30) / (snap - 30));
                for (const p of fightersNear(this.dim, mouth, 30)) {
                    if (this.sheltered(p, mouth)) {
                        if (k % 10 === 0)
                            glint(this.dim, add(p.location, { x: 0, y: 2.2, z: 0 }), C.safe, 0.6);
                        continue;
                    }
                    knock(p, mouth, -pull, 0.03);
                    if (k % 20 === 0)
                        effect(p, "hunger", 100, 2);
                }
            }
            if (k % 2 === 0) {
                const off = add(mouth, scale(dirOfYaw(randIn(0, 360)), randIn(10, 22)));
                off.y = center.y + randIn(0.5, 4);
                bullet(this.dim, off, norm(sub(mouth, off)), 22, 16, k % 4 ? C.hunger : C.gold, 0.4);
            }
            if (k % 20 === 0)
                sound(this.dim, "mob.warden.sonic_charge", mouth, 3, 0.5);
            yield 1;
        }
        const mouth = this.mouth();
        sound(this.dim, "mob.ravager.bite", mouth, 6, 0.35);
        sound(this.dim, "random.explode", mouth, 4, 0.6);
        shake(this.audience(), 0.8, 1.2);
        flash(this.audience(), { red: 0.25, green: 0.12, blue: 0.3 });
        burst(this.dim, mouth, C.gold, 40, 8, 0.45, 2);
        for (const p of fightersNear(this.dim, mouth, 26)) {
            if (this.sheltered(p, mouth))
                continue;
            const d = flatDist(p.location, mouth);
            if (d <= 7) {
                hurt(p, 40, this.entity);
                hurt(p, 12, this.entity, EntityDamageCause.magic);
                knock(p, mouth, 2.2, 0.7);
            }
            else {
                hurt(p, 10, this.entity, EntityDamageCause.magic);
            }
        }
        yield a.ticks - snap;
    }
}
