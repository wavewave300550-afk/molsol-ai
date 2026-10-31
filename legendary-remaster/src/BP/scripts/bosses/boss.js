/**
 * Boss = Being + phases, arena, ultimate scheduling, entrance / transition /
 * death sequences and the HP gates that keep phases from being skipped.
 *
 * Damage handling (main.ts, world.beforeEvents.entityHurt):
 *   - invulnerable windows (entrance, transformations, death) cancel damage;
 *   - damage is scaled by takenMul (shields, exhaustion) and party size;
 *   - HP can never drop below the current phase gate, so every phase and its
 *     transformation is always seen, however hard the boss is hit.
 */
import { EntityDamageCause, ItemStack } from "@minecraft/server";
import { allPlayersNear, fightersNear } from "../core/combat.js";
import { cutIn, cutOut } from "../core/cinema.js";
import { ascend, burst, C, chargeUp, crack, dome, flare, flash, lightning, nova, rays, sigil, sound, starRain, vortex } from "../core/fx.js";
import { clearProps } from "../core/hazards.js";
import { notify, Pri } from "../core/notice.js";
import { add, dirOfYaw, dist, flatDist, scale } from "../core/vec.js";
import { Being } from "./being.js";
/** The pose each legend strikes during its ultimate cut-in. */
const CUT_ACT = { taotie: "roar", nidhogg: "roar", hanuman: "taunt", alicorn: "rear", tenko: "howl", logos: "speak" };
export class Boss extends Being {
    constructor(entity, key) {
        super(entity);
        this.phase = 0;
        this.dying = false;
        this.finalBlow = false;
        this.noPlayers = 0;
        this.maxFighters = 1;
        this.ultAt = 0;
        this.ultPhase = 3;
        this.ultCooldown = 900;
        this.arena = 44;
        this.sigil = "";
        this.key = key;
        this.home = { ...entity.location };
    }
    /** Called by the registry right after construction (subclass fields are ready by then). */
    init(adopted) {
        const saved = this.entity.getDynamicProperty("legends:home");
        if (typeof saved === "string") {
            try {
                this.home = JSON.parse(saved);
            }
            catch {
                // keep current location
            }
        }
        else {
            this.entity.setDynamicProperty("legends:home", JSON.stringify(this.home));
        }
        if (adopted) {
            let ph = 1;
            try {
                ph = Math.max(1, Number(this.entity.getProperty("legends:phase")) || 1);
            }
            catch {
                ph = 1;
            }
            this.phase = Math.min(ph, this.thresholds.length + 1);
            this.ultAt = this.t + 200;
            this.prop("act", 0);
            this.prop("fx", 0);
        }
        else {
            this.invuln = true;
            this.start("entrance", this.wrapEntrance());
        }
        this.onInit(adopted);
        return this;
    }
    /** Subclass hook after init (e.g. restore flight / forms for adopted bosses). */
    onInit(adopted) { }
    // ---------------------------------------------------------------- text (minimal, see notice.ts)
    audience() {
        return allPlayersNear(this.dim, this.pos, 72);
    }
    say(text, pri) {
        notify(this.audience(), text, pri);
    }
    /** A very short first-time hint for a brand-new mechanic (once per fight). */
    hint(key, text) {
        this.hinted ??= new Set();
        if (this.hinted.has(key))
            return;
        this.hinted.add(key);
        notify(this.audience(), text, Pri.Phase);
    }
    // ---------------------------------------------------------------- damage model
    /** Lowest HP the boss may currently be brought to. */
    gateHp() {
        if (this.finalBlow)
            return 0;
        if (this.phase >= 1 && this.phase <= this.thresholds.length)
            return this.maxHp * this.thresholds[this.phase - 1];
        return 1;
    }
    partyMul() {
        return 1 / Math.min(3, 1 + 0.5 * (this.maxFighters - 1));
    }
    setPhase(n) {
        this.phase = n;
        this.prop("phase", n);
    }
    // ---------------------------------------------------------------- sequences
    /** Signature colour of the boss's light (ultimates, phase changes, death). */
    get aura() {
        return this.vfxColor ?? C.gold;
    }
    centre(h = 3) {
        return { x: this.pos.x, y: this.pos.y + h, z: this.pos.z };
    }
    *wrapEntrance() {
        this.invuln = true;
        this.fx(0);
        const g0 = this.ground(this.pos);
        this.rune(g0, 9, 90, this.aura, 18);
        ascend(this.dim, g0, this.aura, 5, 14, 70, 9);
        yield* this.entrance();
        const g = this.ground(this.pos);
        nova(this.dim, this.centre(), this.aura, 7);
        crack(this.dim, g, 8, this.aura, 70);
        this.rune(g, 11, 50, this.aura, -30);
        this.setPhase(1);
        this.invuln = false;
        this.rest = 30;
    }
    *wrapTransition(to) {
        this.invuln = true;
        this.fx(1);
        this.say(`§c◆ ${this.phaseNames[to] ?? ""}`, Pri.Phase);
        const g = this.ground(this.pos);
        chargeUp(this.dim, this.centre(), this.aura, 30, 6);
        this.rune(g, 10, 90, this.aura, 26);
        this.rune(g, 6, 90, C.white, -44);
        ascend(this.dim, g, this.aura, 6, 16, 70, 12);
        vortex(this.dim, g, this.aura, 7, 14, 60, 26);
        yield* this.transition(to);
        const c = this.centre();
        nova(this.dim, c, this.aura, 9);
        crack(this.dim, this.ground(this.pos), 10, this.aura, 80);
        rays(this.dim, c, this.aura, 16, 30, 16);
        flash(this.audience(), this.aura);
        for (let i = 0; i < 6; i++)
            lightning(this.dim, this.ground(add(this.pos, scale(dirOfYaw(i * 60 + this.t * 7), 9))), this.aura, 20);
        sound(this.dim, "ambient.weather.thunder", this.pos, 3, 1.1);
        this.setPhase(to);
        this.fx(0);
        this.invuln = false;
        if (to >= this.ultPhase)
            this.ultAt = this.t + 40;
        this.rest = 20;
    }
    *wrapUlt() {
        this.ultAt = this.t + this.ultCooldown;      // set first: an interrupted ultimate never loops
        this.say(`§4⚠ ${this.ultName}`, Pri.Ultimate);
        yield* this.ultCutIn();
        yield* this.ultimate();
        nova(this.dim, this.centre(), this.aura, 8);
        this.ultAt = this.t + this.ultCooldown;
        this.rest = 40;
    }
    /**
     * Ultimate cut-in (about 2 s): the legend roars inside its own unfolding sigil while the
     * camera frames it; light, wind and lightning gather; then a detonation and the view returns.
     */
    *ultCutIn() {
        const was = this.invuln;
        this.invuln = true;
        const T = 38;
        const g = this.ground(this.pos);
        const cut = CUT_ACT[this.key];
        if (cut && this.acts[cut])
            this.act(cut);
        const shot = cutIn(this, this.audience(), T);
        sound(this.dim, "beacon.activate", this.pos, 4, 0.6);
        sound(this.dim, "mob.warden.roar", this.pos, 3, 0.7);
        chargeUp(this.dim, this.centre(4), this.aura, T, 10);
        this.rune(g, 14, 140, this.aura, 18);
        this.rune(g, 8.5, 140, C.white, -34);
        ascend(this.dim, g, this.aura, 7, 18, T + 10, 12);
        vortex(this.dim, g, this.aura, 9, 16, T, 36);
        rays(this.dim, this.centre(4), this.aura, 12, T + 6, 10);
        for (let k = 0; k < T; k++) {
            if (k % 9 === 4) {
                const a = k * 47 + this.t;
                lightning(this.dim, this.ground(add(this.pos, scale(dirOfYaw(a), 7 + (k % 3) * 3))), this.aura, 22);
                sound(this.dim, "ambient.weather.lightning.impact", this.pos, 2, 1.2);
            }
            yield 1;
        }
        const c = this.centre(3);
        nova(this.dim, c, this.aura, 10);
        dome(this.dim, c, C.white, 12, 12);
        flare(this.dim, c, C.white, 18, 14);
        crack(this.dim, g, 12, this.aura, 120);
        flash(this.audience(), this.aura);
        sound(this.dim, "ambient.weather.thunder", this.pos, 4, 0.8);
        cutOut(shot);
        this.invuln = was;
        yield 6;
    }
    /** The legend's own rune circle on the ground. */
    rune(at, radius, ticks, col, spin = 24) {
        sigil(this.dim, at, this.key, radius, ticks, col, spin);
    }
    /** Hook: return a coroutine to run instead of dying (Hanuman's revival). */
    beforeDeath() {
        return undefined;
    }
    deathCo() {
        return this.wrapDeath();
    }
    *wrapDeath() {
        this.dying = true;
        this.invuln = true;
        this.fx(1);
        this.say(this.defeatText, Pri.Ultimate);
        const a = this.act("death");
        sound(this.dim, "mob.enderdragon.death", this.pos, 3, 0.8);
        const g = this.ground(this.pos);
        this.rune(g, 11, a.ticks + 20, this.aura, 14);
        this.rune(g, 6, a.ticks + 20, C.white, -30);
        ascend(this.dim, g, C.holy, 5, 22, a.ticks, 14);
        vortex(this.dim, g, this.aura, 6, 18, a.ticks, 22, 220);
        for (let k = 0; k < a.ticks; k += 10) {
            burst(this.dim, { x: this.pos.x, y: this.pos.y + 2, z: this.pos.z }, C.holy, 18, 5, 0.3, 1.2);
            if (k === a.ticks - 30)
                chargeUp(this.dim, this.centre(), this.aura, 30, 7);
            if (k % 20 === 0)
                rays(this.dim, this.centre(), this.aura, 8 + k * 0.06, 14, 20);
            yield 10;
        }
        nova(this.dim, this.centre(), this.aura, 12);
        nova(this.dim, this.centre(1), C.white, 6);
        flare(this.dim, this.centre(), C.white, 26, 18);
        starRain(this.dim, g, C.holy, 10, 40, 24);
        crack(this.dim, g, 12, this.aura, 100);
        flash(this.audience(), C.white);
        burst(this.dim, { x: this.pos.x, y: this.pos.y + 2, z: this.pos.z }, C.gold, 40, 9, 0.4, 1.5);
        clearProps(this.id);
        this.finalBlow = true;
        this.invuln = false;
        const killer = this.lastAttacker && this.lastAttacker.isValid ? this.lastAttacker : undefined;
        try {
            if (killer)
                this.entity.applyDamage(this.hp + 100, { cause: EntityDamageCause.entityAttack, damagingEntity: killer });
            if (this.entity.isValid)
                this.entity.kill();
        }
        catch {
            // already gone
        }
    }
    depart() {
        this.say(`§7${this.title} departs…`, Pri.Phase);
        clearProps(this.id);
        if (this.sigil) {
            try {
                this.dim.spawnItem(new ItemStack(this.sigil, 1), this.home);
            }
            catch {
                // unloaded
            }
        }
        try {
            this.entity.remove();
        }
        catch {
            // gone
        }
        this.dispose();
    }
    // ---------------------------------------------------------------- main loop
    tick() {
        if (!this.valid) {
            this.cleanup();
            return;
        }
        this.t++;
        this.pos = { ...this.entity.location };
        if (this.t % 10 === 0)
            this.refreshArena();
        if (this.removed)
            return;
        const h = this.entity.getComponent("minecraft:health");
        if (h) {
            this.hp = h.currentValue;
            this.maxHp = h.effectiveMax;
        }
        if (!this.dying && this.phase >= 1) {
            const busyUlt = this.coName === "ultimate";
            if (this.phase <= this.thresholds.length && this.hp <= this.gateHp() + 0.6 && this.coName !== "transition" && !busyUlt) {
                this.interrupt();
                this.start("transition", this.wrapTransition(this.phase + 1));
            }
            else if (this.phase > this.thresholds.length && this.hp <= 1.6 && this.coName !== "death" && this.coName !== "revive" && !busyUlt) {
                const alt = this.beforeDeath();
                this.interrupt();
                if (alt)
                    this.start("revive", alt);
                else
                    this.start("death", this.wrapDeath());
            }
        }
        this.pickTarget();
        if (!this.co && !this.dying) {
            if (this.rest > 0) {
                this.rest--;
                this.idle();
            }
            else {
                this.chooseNext();
            }
        }
        this.stepCo();
        this.phaseAura();
        this.onTick();
        this.syncMove();
    }
    /** From phase II the legend stands inside its own turning sigil (re-laid when it has settled). */
    phaseAura() {
        if (this.phase < 2 || this.dying || this.t % 50 !== 0)
            return;
        const here = this.ground(this.pos);
        const last = this.runeAt;
        this.runeAt = here;
        if (last && flatDist(last, here) > 2.5)
            return;
        this.rune(here, this.phase >= 3 ? 7.5 : 5.5, 56, this.aura, this.phase >= 3 ? 40 : 24);
    }
    /** Per-tick extra behaviour (auras, followers...). */
    onTick() { }
    onCoDone() {
        if (this.rest <= 0)
            this.rest = [0, 30, 24, 18][Math.min(3, this.phase)] ?? 18;
    }
    refreshArena() {
        const near = fightersNear(this.dim, this.home, this.arena + 12);
        const close = fightersNear(this.dim, this.pos, 40);
        const map = new Map();
        for (const p of [...near, ...close])
            map.set(p.id, p);
        this.fighters = [...map.values()];
        this.maxFighters = Math.max(this.maxFighters, this.fighters.length);
        if (this.fighters.length === 0 && !this.dying) {
            this.noPlayers += 10;
            if (this.noPlayers >= 1200)
                this.depart();
        }
        else {
            this.noPlayers = 0;
        }
    }
    chooseNext() {
        const tgt = this.target;
        if (!tgt) {
            this.idle();
            return;
        }
        if (this.phase >= this.ultPhase && this.t >= this.ultAt) {
            this.start("ultimate", this.wrapUlt());
            return;
        }
        this.skillList ??= this.skills();
        const d = dist(this.pos, tgt.location);
        const ok = this.skillList.filter((s) => s.phases.includes(this.phase) && this.cdReady(s.name) &&
            (s.min === undefined || d >= s.min) && (s.max === undefined || d <= s.max) && (!s.when || s.when()));
        if (!ok.length) {
            this.rest = 6;
            this.idle();
            return;
        }
        let r = Math.random() * ok.reduce((a, s) => a + s.weight, 0);
        let chosen = ok[0];
        for (const s of ok) {
            r -= s.weight;
            if (r <= 0) {
                chosen = s;
                break;
            }
        }
        this.setCd(chosen.name, chosen.cd);
        this.start(chosen.name, chosen.run(tgt));
    }
    /** Is the boss too far from home? (idle movement brings it back) */
    leashed() {
        return flatDist(this.pos, this.home) > this.arena;
    }
    cleanup() {
        clearProps(this.id);
        this.dispose();
    }
}
