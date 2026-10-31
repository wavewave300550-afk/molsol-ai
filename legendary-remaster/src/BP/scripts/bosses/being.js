import { fightersNear, healthOf, isFighter } from "../core/combat.js";
import { groundY } from "../core/terrain.js";
import { add, angleDiff, clamp, dist, flatDir, flatDist, lerp, norm, scale, sub, yawOf, pitchOf } from "../core/vec.js";
export const beings = new Map();
export class Being {
    constructor(entity) {
        this.yaw = 0;
        this.pitch = 0;
        this.t = 0;
        this.coName = "";
        this.wait = 0;
        this.rest = 20;
        this.cds = new Map();
        this.fighters = [];
        this.flying = false;
        this.hp = 1;
        this.maxHp = 1;
        this.invuln = false;
        this.takenMul = 1;
        this.removed = false;
        this.moving = 0;
        this.lastMove = -1;
        this.lastAct = 0;
        this.pendingAct = 0;
        this.entity = entity;
        this.id = entity.id;
        this.dim = entity.dimension;
        this.pos = { ...entity.location };
        try {
            this.yaw = entity.getRotation().y;
        }
        catch {
            this.yaw = 0;
        }
        const h = healthOf(entity);
        this.hp = h.cur;
        this.maxHp = h.max;
        beings.set(this.id, this);
    }
    get valid() {
        return !this.removed && this.entity.isValid;
    }
    // ---------------------------------------------------------------- properties & acts
    prop(name, value) {
        try {
            this.entity.setProperty(`legends:${name}`, value);
        }
        catch {
            // entity gone
        }
    }
    act(name) {
        const a = this.acts[name];
        if (!a)
            throw new Error(`${this.entity.typeId}: unknown act ${name}`);
        if (this.lastAct === a.id) {
            // re-trigger the same animation: drop to 0 for one tick, re-apply next tick
            this.prop("act", 0);
            this.pendingAct = a.id;
        }
        else {
            this.prop("act", a.id);
        }
        this.lastAct = a.id;
        return a;
    }
    endAct() {
        if (this.lastAct !== 0)
            this.prop("act", 0);
        this.lastAct = 0;
        this.pendingAct = 0;
    }
    /** Play an act to its end. */
    *play(name) {
        const a = this.act(name);
        yield a.ticks;
        this.endAct();
    }
    fx(state) {
        this.prop("fx", state);
    }
    // ---------------------------------------------------------------- movement
    place(p, yaw = this.yaw, pitch = this.pitch) {
        this.pos = p;
        this.yaw = yaw;
        this.pitch = pitch;
        try {
            this.entity.teleport(p, { rotation: { x: pitch, y: yaw }, keepVelocity: false });
        }
        catch {
            // unloaded chunk
        }
    }
    face(p, maxTurn = 25) {
        const want = yawOf(flatDir(this.pos, p));
        const d = clamp(angleDiff(this.yaw, want), -maxTurn, maxTurn);
        if (Math.abs(d) > 0.5)
            this.place(this.pos, this.yaw + d, this.pitch);
    }
    faceNow(p) {
        this.place(this.pos, yawOf(flatDir(this.pos, p)), this.pitch);
    }
    ground(p) {
        return { x: p.x, y: groundY(this.dim, p.x, p.z, p.y), z: p.z };
    }
    /** One tick of ground movement towards goal at `speed` blocks/tick. Returns remaining distance. */
    walk(goal, speed = this.walkSpeed, stopAt = 0, turn = 18) {
        const d = flatDist(this.pos, goal);
        if (d <= stopAt + 0.05) {
            this.face(goal, turn);
            return d;
        }
        const step = Math.min(speed, d - stopAt);
        const dir = flatDir(this.pos, goal);
        const nx = this.pos.x + dir.x * step;
        const nz = this.pos.z + dir.z * step;
        const ny = groundY(this.dim, nx, nz, this.pos.y);
        const want = yawOf(dir);
        const yaw = this.yaw + clamp(angleDiff(this.yaw, want), -turn, turn);
        this.place({ x: nx, y: ny, z: nz }, yaw, 0);
        this.moving = Math.min(1, speed / Math.max(0.01, this.walkSpeed));
        return d - step;
    }
    /** One tick of free flight towards goal. */
    fly(goal, speed, stopAt = 0, turn = 14) {
        const d = dist(this.pos, goal);
        if (d <= stopAt + 0.05) {
            this.face(goal, turn);
            return d;
        }
        const dir = norm(sub(goal, this.pos));
        const step = Math.min(speed, d - stopAt);
        const np = add(this.pos, scale(dir, step));
        const fd = flatDist(this.pos, goal) > 0.3 ? yawOf(flatDir(this.pos, goal)) : this.yaw;
        this.place(np, this.yaw + clamp(angleDiff(this.yaw, fd), -turn, turn), clamp(pitchOf(dir) * 0.5, -35, 35));
        this.moving = Math.min(1, speed / Math.max(0.01, this.walkSpeed));
        return d - step;
    }
    /** Parabolic leap to dest over `ticks`, `height` blocks apex. */
    *leap(dest, ticks, height, onTick) {
        const from = { ...this.pos };
        const yaw = yawOf(flatDir(from, dest));
        for (let k = 1; k <= ticks; k++) {
            const s = k / ticks;
            const p = lerp(from, dest, s);
            p.y += Math.sin(s * Math.PI) * height;
            this.place(p, yaw, 0);
            onTick?.(k);
            yield 1;
        }
    }
    /** Straight dash along the ground. */
    *dash(dest, speed, onTick) {
        let guard = 200;
        while (guard-- > 0 && flatDist(this.pos, dest) > 0.4) {
            const before = flatDist(this.pos, dest);
            this.walk(dest, speed, 0, 40);
            onTick?.();
            if (flatDist(this.pos, dest) >= before - 0.01)
                break;
            yield 1;
        }
    }
    // ---------------------------------------------------------------- targeting
    refreshFighters(center, radius) {
        this.fighters = fightersNear(this.dim, center, radius);
    }
    pickTarget() {
        const t = this.target;
        if (t && t.isValid && isFighter(t) && this.fighters.some((p) => p.id === t.id) && Math.random() > 0.004)
            return t;
        let best;
        let bd = 1e9;
        for (const p of this.fighters) {
            const d = dist(p.location, this.pos) * (p === this.lastAttacker ? 0.7 : 1);
            if (d < bd) {
                bd = d;
                best = p;
            }
        }
        this.target = best;
        return best;
    }
    // ---------------------------------------------------------------- coroutine runner
    start(name, co) {
        this.co = co;
        this.coName = name;
        this.wait = 0;
    }
    interrupt() {
        if (this.co) {
            try {
                this.co.return();
            }
            catch {
                // ignore
            }
        }
        this.co = undefined;
        this.coName = "";
        this.endAct();
    }
    stepCo() {
        if (this.pendingAct) {
            this.prop("act", this.pendingAct);
            this.pendingAct = 0;
        }
        if (!this.co)
            return;
        if (this.wait > 0) {
            this.wait--;
            return;
        }
        let r;
        try {
            r = this.co.next();
        }
        catch (e) {
            console.warn(`[legends] ${this.entity.typeId} ${this.coName} failed: ${e}`);
            r = { done: true, value: undefined };
        }
        if (r.done) {
            this.co = undefined;
            this.coName = "";
            this.endAct();
            this.onCoDone();
        }
        else {
            this.wait = Math.max(0, (typeof r.value === "number" ? r.value : 1) - 1);
        }
    }
    onCoDone() { }
    syncMove() {
        const m = Math.round(this.moving * 10) / 10;
        if (m !== this.lastMove) {
            this.lastMove = m;
            this.prop("move", m);
        }
        this.moving = 0;
    }
    onDamaged(amount, by) {
        if (by)
            this.lastAttacker = by;
    }
    dispose() {
        this.removed = true;
        beings.delete(this.id);
    }
    cdReady(name) {
        return (this.cds.get(name) ?? 0) <= this.t;
    }
    setCd(name, ticks) {
        this.cds.set(name, this.t + ticks);
    }
}
