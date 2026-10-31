/**
 * TEN-TAILED FOX (十尾の天狐) — Tenko of the Tenfold Moon.
 *
 * Identity: illusion and rhythm. Foxfire hunts you, lanterns burst in a
 * readable clockwise beat, illusions swap places with the real fox, and the
 * kagura dance sends rings you must jump on the bell.
 *
 *   I   Foxfire Courtesan    pounce, swipe, tail lash, foxfire volley, lanterns
 *   II  Hundred Illusions    illusions (and a swap!), torii corridor, tail spikes
 *   III Tenfold Eclipse      the tenth tail unseals: kagura dance (jump the rings)
 *   ULT Ten-Tail Eclipse — ten foxfire rays wheel around her (run with the gaps,
 *                           mind the reversal), then the eclipse implodes.
 */
import { Entity, EntityDamageCause, Player, Vector3 } from "@minecraft/server";
import { TENKO_ACTS } from "../generated/data.js";
import { fightersNear, grounded, hurt, inCircle, inCone, inLine, inRingBand, knock } from "../core/combat.js";
import { bullet, burst, C, deco, flash, glint, shake, shock, sound, spiralMark, teleCircle, teleCone, teleLine, mote } from "../core/fx.js";
import { fire, moveProp, removeProp, spawnProp } from "../core/hazards.js";
import { addTask } from "../core/tasks.js";
import { add, dirOfYaw, flatDir, flatDist, norm, randIn, rotY, scale, sub, yawOf } from "../core/vec.js";
import { Co, SkillDef } from "./being.js";
import { Boss } from "./boss.js";
import { ahead, lead, strike } from "./kit.js";

const A = TENKO_ACTS;

interface Illusion {
  e: Entity;
  next: number;
}

export class Tenko extends Boss {
  readonly acts = A;
  readonly walkSpeed = 0.27;
  readonly title = "Tenko";
  readonly ultName = "Ten-Tail Eclipse";
  readonly phaseNames = ["", "", "Hundred Illusions", "Tenfold Eclipse"];
  readonly thresholds = [0.7, 0.4];
  readonly defeatText = "§e✦ The ten tails fold into moonlight";
  readonly ultPhase = 3;
  readonly ultCooldown = 900;
  readonly sigil = "legends:sigil_tenko";
  illusions: Illusion[] = [];

  constructor(e: Entity) {
    super(e, "tenko");
  }

  idle(): void {
    const t = this.target;
    if (this.leashed() || !t) {
      this.walk(this.home, this.walkSpeed, 2);
      return;
    }
    const d = flatDist(this.pos, t.location);
    // keeps a graceful distance and circles
    if (d > 10) this.walk(t.location, this.walkSpeed, 8);
    else this.walk(add(t.location, scale(rotY(flatDir(t.location, this.pos), 35), 8)), this.walkSpeed * 0.75, 0.3);
  }

  protected onTick(): void {
    if (this.t % 7 === 0) deco(this.dim, "petal", add(this.pos, { x: 0, y: 3, z: 0 }), C.pink, 1, 2.5, 0.25, 0.3);
    this.stepIllusions();
  }

  // ---------------------------------------------------------------- illusions (cheap shadow AIs)
  stepIllusions(): void {
    this.illusions = this.illusions.filter((il) => {
      if (il.e.isValid) return true;
      return false;
    });
    for (const il of this.illusions) {
      const t = this.fighters.length ? this.fighters[Math.floor(il.next) % this.fighters.length] : undefined;
      if (!t) continue;
      const p = il.e.location;
      const d = flatDist(p, t.location);
      const dir = flatDir(p, t.location);
      if (d > 4) {
        const np = add(p, scale(dir, Math.min(0.24, d - 4)));
        np.y = this.ground({ x: np.x, y: p.y, z: np.z }).y;
        moveProp(il.e, np, yawOf(dir));
        try {
          il.e.setProperty("legends:move", 0.8);
        } catch {
          // ignore
        }
      }
      if (this.t >= il.next) {
        il.next = this.t + 70 + Math.floor(randIn(0, 30));
        try {
          il.e.setProperty("legends:act", A.foxfire.id);
        } catch {
          // ignore
        }
        const from = add(p, { x: 0, y: 2, z: 0 });
        const tgt = add(t.location, { x: 0, y: 1, z: 0 });
        bullet(this.dim, from, norm(sub(tgt, from)), 12, 30, C.fox, 0.6);
        fire({ dim: this.dim, pos: from, vel: scale(norm(sub(tgt, from)), 0.6), life: 30, radius: 0.8, dmg: 7, owner: this.entity, cause: EntityDamageCause.magic });
        addTask("ill-reset", (age) => {
          if (age < 30) return true;
          try {
            if (il.e.isValid) il.e.setProperty("legends:act", 0);
          } catch {
            // ignore
          }
          return false;
        });
      }
    }
  }

  clearIllusions(): void {
    for (const il of this.illusions) {
      if (il.e.isValid) burst(this.dim, add(il.e.location, { x: 0, y: 1.5, z: 0 }), C.fox, 16, 4);
      removeProp(il.e);
    }
    this.illusions = [];
  }

  // ---------------------------------------------------------------- entrance / transitions
  *entrance(): Co {
    const g = this.ground(this.pos);
    this.place(g, this.yaw);
    const a = this.act("manifest");
    for (let k = 0; k < a.ticks; k += 3) {
      for (let i = 0; i < 6; i++) deco(this.dim, "flame", add(g, scale(dirOfYaw(i * 60 + k * 6), 4)), C.fox, 1, 0.2, 0.45, 0.6);
      if (k === 39) {
        sound(this.dim, "note.bell", g, 4, 0.5);
        sound(this.dim, "mob.fox.screech", g, 4, 0.7);
        shock(this.dim, g, 12, 12, C.fox);
      }
      yield 3;
    }
    this.endAct();
    this.say("§bThe Ten-Tailed Fox manifests", 0);
  }

  *transition(to: number): Co {
    if (to === 2) {
      const a = this.act("howl");
      yield a.marks[0];
      this.setPhase(2);
      sound(this.dim, "mob.fox.screech", this.pos, 5, 0.6);
      for (let i = 0; i < 9; i++) glint(this.dim, add(ahead(this, -3, 3), scale(dirOfYaw(this.yaw + 90 + i * 20), 3)), C.fox, 1.5);
      shock(this.dim, this.pos, 14, 12, C.fox);
      yield a.ticks - a.marks[0];
      return;
    }
    this.clearIllusions();
    const a = this.act("unseal");
    for (let k = 0; k < a.marks[0]; k += 5) {
      deco(this.dim, "rune", add(this.pos, { x: 0, y: 2, z: 0 }), C.moon, 3, 2, 0.35, 0.6);
      yield 5;
    }
    this.setPhase(3);
    sound(this.dim, "note.bell", this.pos, 5, 0.4);
    sound(this.dim, "mob.fox.screech", this.pos, 5, 0.5);
    flash(this.audience(), { red: 0.12, green: 0.15, blue: 0.4 });
    shake(this.audience(), 0.5, 1.0);
    shock(this.dim, this.pos, 18, 14, C.moon);
    burst(this.dim, ahead(this, -3, 5), C.moon, 40, 7, 0.4, 1.5);
    yield a.ticks - a.marks[0] - (a.marks[0] % 5);
  }

  // ---------------------------------------------------------------- skills
  skills(): SkillDef[] {
    return [
      { name: "pounce", phases: [1, 2, 3], cd: 120, weight: 3, min: 5, max: 17, run: (t) => this.pounce(t) },
      { name: "swipe", phases: [1, 2, 3], cd: 50, weight: 4, max: 5.5, run: (t) => this.swipe(t) },
      { name: "lash", phases: [1, 2], cd: 110, weight: 3, max: 7, run: () => this.lash() },
      { name: "foxfire", phases: [1, 2, 3], cd: 170, weight: 4, run: () => this.foxfire() },
      { name: "lanterns", phases: [1, 2], cd: 260, weight: 3, run: (t) => this.lanterns(t) },
      { name: "illusion", phases: [2], cd: 500, weight: 4, when: () => this.illusions.length === 0, run: () => this.illusion() },
      { name: "torii", phases: [2, 3], cd: 300, weight: 3, run: (t) => this.torii(t) },
      { name: "spikes", phases: [2, 3], cd: 220, weight: 3, run: (t) => this.spikes(t) },
      { name: "kagura", phases: [3], cd: 300, weight: 4, run: () => this.kagura() },
    ];
  }

  *pounce(t: Player): Co {
    this.faceNow(t.location);
    const a = this.act("pounce");
    const dest = this.ground(lead(t, 10));
    teleCircle(this.dim, dest, 3, a.marks[0] + 12);
    yield a.marks[0];
    sound(this.dim, "mob.fox.screech", this.pos, 2, 1.2);
    yield* this.leap(dest, 12, 4, (k) => {
      if (k % 2 === 0) mote(this.dim, this.pos, C.fox, 0.4, 0.4);
    });
    shock(this.dim, dest, 6, 8, C.fox);
    strike(this, dest, 4.5, (p) => inCircle(p, dest, 3), 14, { knock: 1.1, up: 0.5, from: dest });
    yield Math.max(4, a.ticks - a.marks[0] - 12);
  }

  *swipe(t: Player): Co {
    this.faceNow(t.location);
    const a = this.act("swipe");
    teleCone(this.dim, this.ground(this.pos), dirOfYaw(this.yaw), 110, 5, a.marks[0]);
    yield a.marks[0];
    sound(this.dim, "mob.fox.bite", this.pos, 2, 0.8);
    strike(this, this.pos, 7, (p) => inCone(p, this.pos, dirOfYaw(this.yaw), 110, 5), 12, { knock: 0.8 });
    yield a.ticks - a.marks[0];
  }

  *lash(): Co {
    const a = this.act("tail_lash");
    const c = this.ground(this.pos);
    teleCircle(this.dim, c, 6.5, a.marks[0]);
    yield a.marks[0];
    sound(this.dim, "mob.breeze.whirl", c, 3, 1.1);
    shock(this.dim, c, 7, 8, C.fox);
    strike(this, c, 8, (p) => inCircle(p, c, 6.5), 14, { knock: 1.5, up: 0.4, from: c });
    yield a.ticks - a.marks[0];
  }

  *foxfire(): Co {
    const a = this.act("foxfire");
    const orbs: (Entity | undefined)[] = [];
    for (let i = 0; i < 5; i++) orbs.push(spawnProp(this.dim, "foxfire", add(this.pos, { x: 0, y: 3, z: 0 }), 0, this.entity));
    sound(this.dim, "mob.blaze.shoot", this.pos, 2, 1.6);
    for (let k = 0; k < 26; k++) {
      orbs.forEach((o, i) => moveProp(o, add(this.pos, add(scale(dirOfYaw(i * 72 + k * 9), 3), { x: 0, y: 3.2 + Math.sin(k * 0.3 + i) * 0.4, z: 0 }))));
      yield 1;
    }
    for (let i = 0; i < orbs.length; i++) {
      const o = orbs[i];
      const tg = this.fighters.length ? this.fighters[i % this.fighters.length] : undefined;
      if (!o || !tg) {
        removeProp(o);
        continue;
      }
      const from = { ...o.location };
      const d = norm(sub(add(tg.location, { x: 0, y: 1, z: 0 }), from));
      sound(this.dim, "mob.blaze.shoot", from, 1, 1.8);
      fire({
        dim: this.dim, pos: from, vel: scale(d, 0.48), life: 60, radius: 0.8, dmg: 9, owner: this.entity, entity: o,
        homing: { target: tg, turn: 0.06, until: 30 }, cause: EntityDamageCause.magic,
        trail: (s) => {
          if ((s.age ?? 0) % 2 === 0) mote(this.dim, s.pos, C.fox, 0.35, 0.35);
        },
        onHit: (p) => {
          try {
            p.setOnFire(3, true);
          } catch {
            // ignore
          }
        },
        onEnd: (s) => burst(this.dim, s.pos, C.fox, 10, 3),
      });
      yield 6;
    }
    yield Math.max(1, a.ticks - 26 - orbs.length * 6);
  }

  *lanterns(t: Player): Co {
    const a = this.act("lanterns");
    const c = this.ground(t.location);
    const spots: Vector3[] = [];
    const base = randIn(0, 360);
    for (let i = 0; i < 8; i++) spots.push(this.ground(add(c, scale(dirOfYaw(base + i * 45), 5))));
    spots.push(c);
    const first = 26;
    spots.forEach((s, i) => teleCircle(this.dim, s, 2.4, first + i * 6));
    sound(this.dim, "note.bell", c, 3, 1.0);
    let last = 0;
    for (let i = 0; i < spots.length; i++) {
      const at = first + i * 6;
      yield at - last;
      last = at;
      const s = spots[i];
      sound(this.dim, "note.bell", s, 2, 0.6 + i * 0.1);
      burst(this.dim, add(s, { x: 0, y: 0.8, z: 0 }), C.fox, 14, 4, 0.35, 0.5);
      strike(this, s, 3.5, (p) => inCircle(p, s, 2.4), 12, { up: 0.5, from: s, fire: 3 });
    }
    yield Math.max(1, a.ticks - last);
  }

  *illusion(): Co {
    const a = this.act("illusion");
    sound(this.dim, "mob.evocation_illager.prepare_summon", this.pos, 3, 1.3);
    yield a.marks[0];
    const spots = [-1, 1].map((s) => this.ground(add(this.pos, scale(dirOfYaw(this.yaw + 90 * s), 6))));
    spots.push({ ...this.pos });
    // shuffle: the real fox takes one of the three places
    const real = Math.floor(Math.random() * 3);
    for (let i = 0; i < 3; i++) {
      burst(this.dim, add(spots[i], { x: 0, y: 1.5, z: 0 }), C.fox, 18, 5, 0.35, 0.8);
      if (i === real) continue;
      try {
        const e = this.dim.spawnEntity("legends:tenko_illusion", spots[i]);
        e.setDynamicProperty("legends:owner", this.id);
        e.setProperty("legends:phase", 2);
        e.setRotation({ x: 0, y: this.yaw });
        this.illusions.push({ e, next: this.t + 40 + i * 15 });
      } catch (err) {
        console.warn(`[legends] illusion failed: ${err}`);
      }
    }
    this.place(spots[real], this.yaw);
    yield a.ticks - a.marks[0];
  }

  *torii(t: Player): Co {
    this.faceNow(t.location);
    const a = this.act("torii");
    const dir = flatDir(this.pos, t.location);
    const start = this.ground(add(t.location, scale(dir, -9)));
    const gates: (Entity | undefined)[] = [];
    teleLine(this.dim, start, dir, 20, 5, a.marks[0] + 24);
    yield a.marks[0];
    for (let i = 0; i < 5; i++) {
      const p = this.ground(add(start, scale(dir, i * 4.5)));
      gates.push(spawnProp(this.dim, "torii", p, yawOf(dir) + 90, this.entity));
      sound(this.dim, "note.bell", p, 2, 0.5 + i * 0.12);
      yield 4;
    }
    yield 4;
    sound(this.dim, "mob.blaze.shoot", start, 4, 0.6);
    for (let k = 0; k < 16; k++) {
      for (const off of [-1.6, 0, 1.6]) bullet(this.dim, add(add(start, scale(rotY(dir, 90), off)), { x: 0, y: 1, z: 0 }), dir, 40, 10, C.fox, 0.7);
      if (k === 0) strike(this, start, 24, (p) => inLine(p, start, dir, 20, 5), 18, { knock: 1.2, up: 0.4, fire: 4 });
      yield 1;
    }
    yield 20;
    gates.forEach((g) => removeProp(g));
    yield Math.max(1, a.ticks - a.marks[0] - 60);
  }

  *spikes(t: Player): Co {
    const a = this.act("tail_spikes");
    const c = this.ground(t.location);
    const spots: Vector3[] = [c];
    for (let i = 0; i < 8; i++) spots.push(this.ground(add(c, scale(dirOfYaw(i * 45 + 22), 3.6))));
    spots.forEach((s, i) => teleCircle(this.dim, s, 1.8, a.marks[0] + (i === 0 ? 14 : 0)));
    yield a.marks[0];
    const props: (Entity | undefined)[] = [];
    for (let i = 1; i < spots.length; i++) props.push(this.spike(spots[i]));
    yield 14;
    props.push(this.spike(spots[0]));
    addTask("spikes", (age) => {
      if (age < 40) return true;
      props.forEach((p) => removeProp(p));
      return false;
    });
    yield Math.max(1, a.ticks - a.marks[0] - 14);
  }

  spike(s: Vector3): Entity | undefined {
    const e = spawnProp(this.dim, "tail_spike", s, randIn(0, 360), this.entity);
    deco(this.dim, "shard", s, C.root, 5, 1, 0.3, 4);
    sound(this.dim, "mob.evocation_fangs.attack", s, 2, 1.2);
    strike(this, s, 3, (p) => inCircle(p, s, 1.8), 14, { up: 0.9, from: s });
    return e;
  }

  *kagura(): Co {
    const a = this.act("kagura");
    const c = this.ground(this.pos);
    let last = 0;
    for (const m of a.marks) {
      // the bell rings just before each beat: jump on the ring!
      yield Math.max(1, m - last - 6);
      sound(this.dim, "note.bell", c, 4, 1.2);
      spiralMark(this.dim, c, C.fox, 3, 6);
      yield 6;
      last = m;
      shock(this.dim, c, 16, 14, C.fox);
      const hit = new Set<string>();
      addTask("kagura-ring", (age) => {
        const r = 1 + age * 1.1;
        strike(this, c, r + 2, (p) => grounded(p) && inRingBand(p, c, r - 1.1, r + 0.3, 2), 12, { up: 0.45, from: c, once: hit });
        return age < 14;
      });
    }
    yield a.ticks - last;
  }

  // ---------------------------------------------------------------- ultimate
  *ultimate(): Co {
    this.clearIllusions();
    const center = this.ground(this.pos);
    const a = this.act("eclipse");
    sound(this.dim, "note.bell", center, 5, 0.4);
    for (let k = 0; k < a.marks[0]; k++) {
      this.place(add(center, { x: 0, y: (3 * Math.min(1, (k + 1) / 20)), z: 0 }), this.yaw);
      if (k % 6 === 0) spiralMark(this.dim, center, C.moon, 6, 8);
      yield 1;
    }
    const origin = add(center, { x: 0, y: 1.2, z: 0 });
    let ang = this.yaw;
    let speed = 1.6;
    const lastHit = new Map<string, number>();
    const end = a.marks[1] - 16;
    const reverseAt = Math.floor(a.marks[0] + (end - a.marks[0]) * 0.55);
    for (let k = a.marks[0]; k < end; k++) {
      if (k === reverseAt - 12) {
        sound(this.dim, "note.bell", center, 5, 2.0);
        glint(this.dim, add(this.pos, { x: 0, y: 4, z: 0 }), C.white, 3);
      }
      if (k === reverseAt) speed = -2.1;
      ang += speed;
      const armed = k >= a.marks[0] + 16;
      for (let i = 0; i < 10; i++) {
        const dir = dirOfYaw(ang + i * 36);
        if (k % 2 === 0) bullet(this.dim, add(origin, scale(dir, 1.5)), dir, 44, 10, armed ? (i === 9 ? C.moon : C.fox) : C.warn, armed ? 0.7 : 0.4);
        if (!armed) continue;
        for (const p of fightersNear(this.dim, center, 24)) {
          if ((lastHit.get(p.id) ?? -99) > k - 8) continue;
          if (!inLine(p, add(center, scale(dir, 1.5)), dir, 21, 2.0, 4)) continue;
          lastHit.set(p.id, k);
          hurt(p, 7, this.entity, EntityDamageCause.magic);
          try {
            p.setOnFire(2, true);
          } catch {
            // ignore
          }
        }
      }
      if (k === end - 32) teleCircle(this.dim, center, 6.5, 48);
      yield 1;
    }
    // implosion
    sound(this.dim, "mob.warden.sonic_charge", center, 5, 0.6);
    for (let k = 0; k < 16; k++) {
      for (const p of fightersNear(this.dim, center, 14)) knock(p, center, -0.28, 0);
      yield 1;
    }
    sound(this.dim, "random.explode", center, 5, 0.8);
    flash(this.audience(), { red: 0.08, green: 0.1, blue: 0.3 });
    shake(this.audience(), 0.7, 1.0);
    shock(this.dim, center, 14, 12, C.moon);
    burst(this.dim, origin, C.fox, 40, 8, 0.45, 1.5);
    strike(this, center, 9, (p) => inCircle(p, center, 6.5, 5), 34, { knock: 2.2, up: 0.8, from: center });
    yield Math.max(1, a.ticks - a.marks[1]);
    for (let k = 0; k < 10; k++) {
      this.place(add(this.pos, { x: 0, y: (center.y - this.pos.y) * 0.4, z: 0 }), this.yaw);
      yield 1;
    }
  }

  cleanup(): void {
    this.clearIllusions();
    super.cleanup();
  }
}
