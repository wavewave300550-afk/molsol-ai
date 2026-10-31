/**
 * NIDHOGG (Níðhöggr) — Gnawer of the World-Root.
 *
 * Identity: the ground is never safe. It burrows and erupts under players,
 * roots of Yggdrasil snare them, venom pools spread, and from the air it
 * strafes, breathes Niflheim frost and beats players into the pools.
 *
 *   I   Gnawer of Roots   bite lunge, tail sweep (punishes standing behind),
 *                         root snare, burrow + eruption, coil
 *   II  Dark Wings        takes flight: venom strafe, frost breath sweep,
 *                         wing gale, dive bomb
 *   III Ragnarök          veins and spines blaze; everything faster
 *   ULT Ragnarök: Fall of the World-Tree — corpse-fire rain, the world-root
 *                         rupture (run out of the great circle), then it lies
 *                         exhausted and takes +60% damage: the reward window.
 */
import { EntityDamageCause } from "@minecraft/server";
import { NIDHOGG_ACTS } from "../generated/data.js";
import { effect, fightersNear, hurt, inCircle, inCone, inLine } from "../core/combat.js";
import { burst, C, deco, flash, shake, shock, sound, spiralMark, teleCircle, teleCone, teleLine, bullet, glint } from "../core/fx.js";
import { fire, moveProp, removeProp, spawnProp, zone } from "../core/hazards.js";
import { addTask } from "../core/tasks.js";
import { add, angleDiff, dirOfYaw, dist, flatDir, flatDist, norm, randIn, rotY, scale, sub, yawOf } from "../core/vec.js";
import { Boss } from "./boss.js";
import { ahead, lead, strike } from "./kit.js";
const A = NIDHOGG_ACTS;
const POISON = (amp = 0) => ["poison", 80, amp];
export class Nidhogg extends Boss {
    constructor(e) {
        super(e, "nidhogg");
        this.acts = A;
        this.walkSpeed = 0.21;
        this.title = "Níðhöggr";
        this.ultName = "Ragnarök: World-Tree Falls";
        this.phaseNames = ["", "", "Dark Wings of Náströnd", "Ragnarök"];
        this.thresholds = [0.7, 0.35];
        this.defeatText = "§e✦ Níðhöggr sinks beneath the roots";
        this.ultPhase = 3;
        this.ultCooldown = 1000;
        this.sigil = "legends:sigil_nidhogg";
    }
    onInit() {
        if (this.phase >= 2)
            this.takeWing(true);
    }
    takeWing(on) {
        this.flying = on;
        this.prop("var", on ? 1 : 0);
    }
    mouth() {
        return this.flying ? ahead(this, 8, 1.2) : ahead(this, 8.6, 3.0);
    }
    hover(t) {
        const g = this.ground(t.location).y;
        const ang = this.t * 0.9;
        const p = add(t.location, scale(dirOfYaw(ang), 13));
        return { x: p.x, y: g + 7, z: p.z };
    }
    idle() {
        const t = this.target;
        if (this.leashed() || !t) {
            if (this.flying)
                this.fly({ x: this.home.x, y: this.ground(this.home).y + 7, z: this.home.z }, 0.35);
            else
                this.walk(this.home, this.walkSpeed, 2);
            return;
        }
        if (this.flying) {
            this.fly(this.hover(t), 0.32, 0, 8);
            if (this.t % 30 === 0)
                sound(this.dim, "mob.enderdragon.flap", this.pos, 2, 0.6);
        }
        else {
            this.walk(t.location, this.walkSpeed, 7);
        }
    }
    onTick() {
        if (this.phase >= 3 && this.t % 8 === 0)
            deco(this.dim, "drip", add(this.pos, { x: 0, y: 2, z: 0 }), C.venom, 2, 2.5, 0.25, 0.2);
    }
    // ---------------------------------------------------------------- entrance / transitions
    *entrance() {
        const g = this.ground(this.pos);
        this.place(g, this.yaw);
        const a = this.act("emerge");
        for (let k = 0; k < a.ticks; k += 4) {
            deco(this.dim, "shard", add(g, { x: 0, y: 0.4, z: 0 }), C.root, 4, 4, 0.35, 5);
            spiralMark(this.dim, g, C.venom, 7, 6);
            if (k === 44) {
                sound(this.dim, "mob.enderdragon.growl", g, 5, 0.6);
                shake(this.audience(), 0.6, 1.5);
                shock(this.dim, g, 16, 16, C.venom);
                this.rootRing(g, 6, 7);
            }
            yield 4;
        }
        this.endAct();
        this.say("§2Níðhöggr rises from the roots", 0);
    }
    *transition(to) {
        if (to === 2) {
            const a = this.act("takeoff");
            sound(this.dim, "mob.enderdragon.growl", this.pos, 5, 0.7);
            yield a.marks[0];
            this.takeWing(true);
            const g = this.ground(this.pos).y;
            for (let k = 0; k < a.ticks - a.marks[0]; k++) {
                this.place({ x: this.pos.x, y: this.pos.y + (g + 7 - this.pos.y) * 0.15, z: this.pos.z });
                if (k % 5 === 0)
                    shock(this.dim, { x: this.pos.x, y: g, z: this.pos.z }, 9, 8, C.wind);
                yield 1;
            }
            this.endAct();
            return;
        }
        const a = this.act("roar");
        yield a.marks[0];
        this.setPhase(3);
        sound(this.dim, "mob.enderdragon.growl", this.pos, 6, 0.45);
        sound(this.dim, "ambient.weather.thunder", this.pos, 4, 0.6);
        shake(this.audience(), 0.55, 1.6);
        burst(this.dim, this.pos, C.venom, 40, 8, 0.45, 2);
        yield a.ticks - a.marks[0];
    }
    // ---------------------------------------------------------------- skills
    skills() {
        const behind = () => !!this.target &&
            Math.abs(angleDiff(this.yaw, yawOf(flatDir(this.pos, this.target.location)))) > 100 && flatDist(this.pos, this.target.location) < 13;
        return [
            { name: "bite", phases: [1], cd: 50, weight: 4, max: 10, run: (t) => this.bite(t) },
            { name: "tail", phases: [1], cd: 70, weight: 6, when: behind, run: () => this.tail() },
            { name: "snare", phases: [1, 3], cd: 220, weight: 3, run: () => this.snare() },
            { name: "burrow", phases: [1], cd: 320, weight: 3, min: 6, run: (t) => this.burrow(t) },
            { name: "coil", phases: [1], cd: 260, weight: 2, max: 14, run: (t) => this.coil(t) },
            { name: "strafe", phases: [2, 3], cd: 220, weight: 3, run: (t) => this.strafe(t) },
            { name: "breath", phases: [2, 3], cd: 200, weight: 3, run: (t) => this.breath(t) },
            { name: "gale", phases: [2, 3], cd: 220, weight: 2, max: 20, run: (t) => this.gale(t) },
            { name: "dive", phases: [2, 3], cd: 120, weight: 4, run: (t) => this.dive(t) },
        ];
    }
    *bite(t) {
        for (let k = 0; k < 20 && flatDist(this.pos, t.location) > 8; k++) {
            this.walk(t.location, this.walkSpeed * 1.4, 7.5);
            yield 1;
        }
        this.faceNow(t.location);
        const a = this.act("bite");
        const dir = dirOfYaw(this.yaw);
        teleLine(this.dim, this.ground(this.pos), dir, 12.5, 3.6, a.marks[0]);
        yield a.marks[0];
        this.place(this.ground(add(this.pos, scale(dir, 2.5))), this.yaw);
        sound(this.dim, "mob.ravager.bite", this.pos, 3, 0.6);
        strike(this, this.pos, 14, (p) => inLine(p, this.pos, dir, 12.5, 3.6), 16, { knock: 1.0, up: 0.3, effects: [POISON()] });
        yield a.ticks - a.marks[0];
    }
    *tail() {
        const a = this.act("tail_sweep");
        const back = dirOfYaw(this.yaw + 180);
        teleCone(this.dim, this.ground(this.pos), back, 170, 13, a.marks[0]);
        sound(this.dim, "mob.enderdragon.flap", this.pos, 2, 0.5);
        yield a.marks[0];
        sound(this.dim, "mob.ravager.stun", this.pos, 3, 0.6);
        strike(this, this.pos, 14, (p) => inCone(p, this.pos, back, 170, 13), 14, { knock: 1.6, up: 0.45 });
        yield a.ticks - a.marks[0];
    }
    rootRing(center, n, r) {
        for (let i = 0; i < n; i++) {
            const p = this.ground(add(center, scale(dirOfYaw((i / n) * 360), r)));
            const e = spawnProp(this.dim, "root_spike", p, randIn(0, 360), this.entity);
            addTask("root", (age) => {
                if (age > 70) {
                    removeProp(e);
                    return false;
                }
                return true;
            });
        }
    }
    *snare() {
        const a = this.act(this.flying ? "roar" : "root_snare");
        const spots = this.fighters.slice(0, 5).map((p) => this.ground(p.location));
        for (const s of spots)
            teleCircle(this.dim, s, 2.3, a.marks[0] + 6);
        yield a.marks[0] + 6;
        sound(this.dim, "mob.evocation_fangs.attack", this.pos, 3, 0.5);
        for (const s of spots) {
            const e = spawnProp(this.dim, "root_spike", s, randIn(0, 360), this.entity);
            deco(this.dim, "shard", s, C.root, 8, 1.5, 0.3, 4);
            strike(this, s, 3.5, (p) => inCircle(p, s, 2.3), 10, { up: 0.6, effects: [["slowness", 50, 4], POISON()] });
            addTask("root", (age) => {
                if (age > 60) {
                    removeProp(e);
                    return false;
                }
                return true;
            });
        }
        yield Math.max(4, a.ticks - a.marks[0] - 6);
    }
    *burrow(t) {
        const a = this.act("burrow");
        sound(this.dim, "mob.warden.dig", this.pos, 4, 0.6);
        for (let k = 0; k < a.ticks; k += 4) {
            deco(this.dim, "shard", this.pos, C.root, 6, 3, 0.35, 5);
            yield 4;
        }
        this.act("underground");
        this.invuln = true;
        // travel underground towards the target; the ground cracks along the way
        for (let k = 0; k < 44; k++) {
            this.walk(t.location, 0.42, 0.5, 60);
            if (k % 2 === 0)
                deco(this.dim, "shard", add(this.ground(this.pos), { x: 0, y: 0.2, z: 0 }), C.root, 3, 1, 0.3, 3);
            if (k % 6 === 0)
                sound(this.dim, "mob.warden.dig", this.pos, 2, 0.8);
            if (flatDist(this.pos, t.location) < 1 || k === 43)
                break;
            yield 1;
        }
        const spot = this.ground(t.location);
        teleCircle(this.dim, spot, 3.8, 22);
        spiralMark(this.dim, spot, C.venom, 4, 22);
        for (let k = 0; k < 22; k++) {
            if (k % 4 === 0)
                deco(this.dim, "shard", spot, C.root, 5, 2.5, 0.3, 4);
            yield 1;
        }
        this.place(spot, this.yaw);
        this.invuln = false;
        const e = this.act("erupt");
        yield e.marks[0];
        sound(this.dim, "mob.enderdragon.growl", spot, 5, 0.8);
        shake(this.audience(), 0.5, 0.8);
        shock(this.dim, spot, 10, 10, C.venom);
        strike(this, spot, 6, (p) => inCircle(p, spot, 3.8, 6), 22, { knock: 1.0, up: 1.1, from: spot, effects: [POISON(1)] });
        this.rootRing(spot, 6, 5.5);
        yield e.ticks - e.marks[0];
    }
    *coil(t) {
        const a = this.act("coil");
        const c = this.ground(t.location);
        teleCircle(this.dim, c, 7, a.marks[0]);
        for (let k = 0; k < a.marks[0]; k += 6) {
            for (let i = 0; i < 10; i++) {
                const p = add(c, scale(dirOfYaw(i * 36 + k * 4), 7));
                deco(this.dim, "drip", add(p, { x: 0, y: 0.5, z: 0 }), C.venom, 1, 0.2, 0.25, 0.1);
            }
            yield 6;
        }
        sound(this.dim, "mob.ravager.stun", c, 4, 0.5);
        shock(this.dim, c, 7, 8, C.venom);
        strike(this, c, 9, (p) => inCircle(p, c, 7), 18, { up: 0.4, effects: [["slowness", 60, 2], POISON(1)] });
        yield Math.max(2, a.ticks - a.marks[0] - (a.marks[0] % 6));
    }
    *strafe(t) {
        const across = flatDir(this.pos, t.location);
        const side = rotY(across, 90);
        const g = this.ground(t.location).y;
        const start = add(add(t.location, scale(across, -18)), scale(side, randIn(-3, 3)));
        start.y = g + 6;
        for (let k = 0; k < 40 && dist(this.pos, start) > 1; k++) {
            this.fly(start, 0.6, 0, 30);
            yield 1;
        }
        const end = add(start, scale(across, 36));
        teleLine(this.dim, { x: start.x, y: g, z: start.z }, across, 36, 5, 26);
        this.act("strafe");
        sound(this.dim, "mob.enderdragon.growl", this.pos, 4, 0.9);
        yield 14;
        const hit = new Set();
        let lastPool = -10;
        for (let k = 0; k < 70 && dist(this.pos, end) > 1; k++) {
            this.fly(end, 0.75, 0, 40);
            deco(this.dim, "drip", this.mouth(), C.venom, 3, 0.6, 0.3, 0.2);
            strike(this, this.pos, 9, (p) => flatDist(p.location, this.pos) < 2.6 && p.location.y < this.pos.y + 1, 14, { knock: 0.6, up: 0.3, effects: [POISON(1)], once: hit });
            if (k - lastPool >= 6) {
                lastPool = k;
                zone(this.dim, this.ground(this.pos), 2.4, 140, { dmg: 3, every: 10, col: C.venom, owner: this.entity, kind: "venom",
                    onTick: (p) => effect(p, "poison", 60, 0) });
            }
            yield 1;
        }
        this.endAct();
        yield 10;
    }
    *breath(t) {
        const g = this.ground(t.location).y;
        const spot = add(t.location, scale(flatDir(t.location, this.pos), 10));
        spot.y = g + 5;
        for (let k = 0; k < 30 && dist(this.pos, spot) > 1; k++) {
            this.fly(spot, 0.5, 0, 30);
            yield 1;
        }
        this.faceNow(t.location);
        const a = this.act("breath");
        const base = this.yaw;
        teleCone(this.dim, { x: this.pos.x, y: g, z: this.pos.z }, dirOfYaw(base), 90, 17, a.marks[0], C.danger);
        sound(this.dim, "mob.enderdragon.growl", this.pos, 3, 1.3);
        yield a.marks[0];
        const sweep = a.ticks - a.marks[0] - 8;
        const hit = new Map();
        for (let k = 0; k < sweep; k++) {
            const ang = base - 45 + (90 * k) / sweep;
            const dir = dirOfYaw(ang);
            const m = this.mouth();
            for (let j = 0; j < 2; j++) {
                const d = norm({ x: dir.x + randIn(-0.15, 0.15), y: -0.32 + randIn(-0.1, 0.1), z: dir.z + randIn(-0.15, 0.15) });
                bullet(this.dim, m, d, 24, 14, j ? C.frost : C.venom, 0.6);
            }
            for (const p of fightersNear(this.dim, this.pos, 20)) {
                if (!inCone(p, { x: this.pos.x, y: g, z: this.pos.z }, dir, 34, 17, 8))
                    continue;
                if ((hit.get(p.id) ?? -99) > k - 8)
                    continue;
                hit.set(p.id, k);
                hurt(p, 6, this.entity, EntityDamageCause.freezing);
                effect(p, "slowness", 50, 2);
                effect(p, "poison", 60, 0);
            }
            if (k % 10 === 0)
                sound(this.dim, "mob.breeze.whirl", m, 2, 0.6);
            yield 1;
        }
        yield 8;
    }
    *gale(t) {
        this.faceNow(t.location);
        const a = this.act("gale");
        const g = this.ground(this.pos);
        let last = 0;
        for (const m of a.marks) {
            teleCone(this.dim, g, dirOfYaw(this.yaw), 140, 18, m - last, C.warn);
            yield m - last;
            last = m;
            sound(this.dim, "mob.enderdragon.flap", this.pos, 5, 0.5);
            shake(this.audience(), 0.25, 0.4);
            for (let i = 0; i < 6; i++)
                bullet(this.dim, this.pos, rotY(dirOfYaw(this.yaw), -60 + i * 24), 30, 12, C.wind, 0.8);
            strike(this, this.pos, 20, (p) => inCone(p, { x: this.pos.x, y: g.y, z: this.pos.z }, dirOfYaw(this.yaw), 140, 18, 10), 8, { knock: 2.6, up: 0.4 });
        }
        yield a.ticks - last;
    }
    *dive(t) {
        const g = this.ground(t.location);
        const high = { x: this.pos.x, y: g.y + 12, z: this.pos.z };
        for (let k = 0; k < 20 && dist(this.pos, high) > 1; k++) {
            this.fly(high, 0.6, 0, 30);
            yield 1;
        }
        const spot = this.ground(lead(t, 12));
        const a = this.act("dive");
        teleCircle(this.dim, spot, 4.2, a.marks[0]);
        this.faceNow(spot);
        const wind = a.marks[0] - 10;
        yield wind;
        const from = { ...this.pos };
        for (let k = 1; k <= 10; k++) {
            const p = add(from, scale(sub(add(spot, { x: 0, y: 1, z: 0 }), from), k / 10));
            this.place(p, this.yaw, 40);
            yield 1;
        }
        sound(this.dim, "random.explode", spot, 3, 0.7);
        shake(this.audience(), 0.5, 0.7);
        shock(this.dim, spot, 9, 10, C.venom);
        strike(this, spot, 6, (p) => inCircle(p, spot, 4.2, 5), 24, { knock: 1.6, up: 0.7, from: spot, effects: [POISON(1)] });
        this.place(this.pos, this.yaw, 0);
        yield a.ticks - a.marks[0];
    }
    // ---------------------------------------------------------------- ultimate
    *ultimate() {
        const center = this.ground(this.home);
        const top = { x: center.x, y: center.y + 18, z: center.z };
        this.takeWing(true);
        const asc = this.act("ascend");
        sound(this.dim, "mob.enderdragon.growl", this.pos, 6, 0.4);
        for (let k = 0; k < asc.ticks; k++) {
            this.fly(top, 0.7, 0, 20);
            yield 1;
        }
        const rg = this.act("ragnarok");
        shake(this.audience(), 0.3, 3);
        sound(this.dim, "ambient.weather.thunder", center, 5, 0.5);
        const meteors = 16;
        for (let i = 0; i < meteors; i++) {
            const tgt = this.fighters.length && i % 2 === 0 ? this.fighters[i % this.fighters.length].location
                : add(center, scale(dirOfYaw(randIn(0, 360)), randIn(3, 16)));
            const spot = this.ground(tgt);
            teleCircle(this.dim, spot, 3, 24);
            this.meteor(spot);
            yield Math.floor((rg.ticks - 10) / meteors);
        }
        yield 10;
        // the rupture: run out of the great circle
        const ru = this.act("rupture");
        teleCircle(this.dim, center, 10, ru.marks[0]);
        spiralMark(this.dim, center, C.venom, 10, ru.marks[0]);
        sound(this.dim, "mob.warden.sonic_charge", center, 6, 0.4);
        const from = { ...this.pos };
        for (let k = 1; k <= ru.marks[0]; k++) {
            const s = Math.max(0, (k - (ru.marks[0] - 10)) / 10);
            this.place(add(from, scale(sub(add(center, { x: 0, y: 1, z: 0 }), from), s)), this.yaw, s > 0 ? 45 : 0);
            yield 1;
        }
        sound(this.dim, "random.explode", center, 6, 0.4);
        sound(this.dim, "mob.enderdragon.growl", center, 6, 0.6);
        flash(this.audience(), { red: 0.2, green: 0.6, blue: 0.15 });
        shake(this.audience(), 0.9, 1.5);
        shock(this.dim, center, 20, 18, C.venom);
        strike(this, center, 12, (p) => inCircle(p, center, 10, 8), 38, { knock: 1.6, up: 1.2, from: center, effects: [POISON(2), ["wither", 60, 0]] });
        this.rootRing(center, 9, 11);
        yield ru.ticks - ru.marks[0];
        // exhausted: the reward window
        this.takeWing(false);
        this.place(center, this.yaw, 0);
        const ex = this.act("exhausted");
        this.fx(3);
        this.takenMul = 1.6;
        for (let k = 0; k < ex.ticks; k += 10) {
            glint(this.dim, add(this.pos, { x: 0, y: 3, z: 0 }), C.sky, 1.5);
            yield 10;
        }
        this.takenMul = 1;
        this.fx(0);
        this.endAct();
        if (this.phase >= 2) {
            const a = this.act("takeoff");
            yield a.marks[0];
            this.takeWing(true);
            yield a.ticks - a.marks[0];
        }
    }
    meteor(spot) {
        const from = add(spot, { x: randIn(-8, 8), y: 24, z: randIn(-8, 8) });
        const e = spawnProp(this.dim, "nid_meteor", from, 0, this.entity);
        const T = 24;
        fire({
            dim: this.dim, pos: from, vel: scale(sub(spot, from), 1 / T), life: T + 2, radius: 0.1, dmg: 0, owner: this.entity, entity: e,
            trail: (s) => {
                if ((s.age ?? 0) % 2 === 0)
                    deco(this.dim, "flame", s.pos, C.venom, 2, 0.4, 0.4, 0.5);
                moveProp(e, s.pos, yawOf(s.vel), 60);
            },
            onEnd: () => {
                sound(this.dim, "random.explode", spot, 2, 1.1);
                burst(this.dim, spot, C.venom, 20, 6, 0.35, 0.5);
                shock(this.dim, spot, 5, 8, C.venom);
                strike(this, spot, 4.5, (p) => inCircle(p, spot, 3, 5), 18, { knock: 0.8, up: 0.5, from: spot, effects: [POISON(1)] });
                zone(this.dim, spot, 2.4, 100, { dmg: 3, every: 10, col: C.venom, owner: this.entity, kind: "venom" });
            },
        });
    }
}
