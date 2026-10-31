/**
 * THE WORD OF GOD (Logos) and its Choir — Seraph, Cherub and Ophan (Thrones).
 *
 * Identity: order and judgement. The Word attacks in perfect geometry (grids,
 * rings, lines) while the Choir circles it and fights on its own:
 *   SERAPH  burning dives, the live coal, "Sanctus" rings; signature TRISAGION
 *           (three great fire rings: holy, holy, holy - jump each one).
 *   CHERUB  the flaming sword that turns every way, the four-faced gaze, and a
 *           WARD that halves the Word's damage taken (hurt the Cherub to break
 *           it); signature GATE OF EDEN: plants the sword - the only refuge
 *           during the Word's ultimate.
 *   OPHAN   rolling wheel, eyes of judgement (beams), restoring the Word;
 *           signature WHEELS WITHIN WHEELS: a gravity well of fiery spokes.
 *
 *   I   In the Beginning       Fiat Lux checkerboard, light lances, judgement line
 *   II  The Seven Seals        wings unfold; trumpet rings, Babel spiral, seals
 *                              break one by one (tablets fall)
 *   III Alpha and Omega        the eye opens; fallen Choir members are re-spoken
 *   ULT The Final Word — the Cherub plants Eden, the Seraph closes a ring of fire,
 *                              the Ophan's eyes hunt; at the last syllable only
 *                              Eden is spared.
 */
import { Entity, EntityDamageCause, Player, Vector3 } from "@minecraft/server";
import { CHERUB_ACTS, LOGOS_ACTS, OPHAN_ACTS, SERAPH_ACTS } from "../generated/data.js";
import { fightersNear, grounded, hurt, inCircle, inCone, inLine, inRingBand, knock } from "../core/combat.js";
import { beam, bullet, burst, C, deco, flash, glint, mote, pillar, shake, shock, sound, spiralMark, teleCircle, teleCone, teleLine, teleSafe } from "../core/fx.js";
import { fire, moveProp, removeProp, spawnProp, zone } from "../core/hazards.js";
import { notify, Pri } from "../core/notice.js";
import { addTask } from "../core/tasks.js";
import { add, dirOfYaw, dist, flatDir, flatDist, norm, randIn, scale, sub, yawOf } from "../core/vec.js";
import { Being, beings, Co, SkillDef } from "./being.js";
import { Boss } from "./boss.js";
import { lead, strike } from "./kit.js";

const A = LOGOS_ACTS;
type Role = "seraph" | "cherub" | "ophan";

// =========================================================================== Choir follower

abstract class Choir extends Being {
  readonly role: Role;
  readonly owner: Logos;
  orbitR: number;
  orbitH: number;
  orbitSpeed: number;
  orbitPhase: number;
  nextSkill = 60;
  signatureAt = 400;
  takenSince = 0;
  command?: Co;

  constructor(e: Entity, role: Role, owner: Logos, r: number, h: number, speed: number, phase: number) {
    super(e);
    this.role = role;
    this.owner = owner;
    this.orbitR = r;
    this.orbitH = h;
    this.orbitSpeed = speed;
    this.orbitPhase = phase;
    this.flying = true;
    e.setDynamicProperty("legends:owner", owner.id);
  }

  abstract kit(): ((t: Player) => Co)[];
  abstract signature(t: Player): Co;

  orbitPoint(): Vector3 {
    const c = this.owner.pos;
    const a = this.orbitPhase + this.owner.t * this.orbitSpeed;
    return add(c, add(scale(dirOfYaw(a), this.orbitR), { x: 0, y: this.orbitH + Math.sin(this.owner.t * 0.05 + this.orbitPhase) * 0.6, z: 0 }));
  }

  onDamaged(amount: number, by?: Player): void {
    super.onDamaged(amount, by);
    this.takenSince += amount;
  }

  tick(): void {
    if (!this.valid) {
      this.dispose();
      return;
    }
    if (!this.owner.valid) {
      try {
        this.entity.remove();
      } catch {
        // ignore
      }
      this.dispose();
      return;
    }
    this.t++;
    this.pos = { ...this.entity.location };
    this.fighters = this.owner.fighters;
    this.invuln = this.owner.invuln && this.owner.phase === 0;
    this.pickTarget();
    if (this.command && !this.co) {
      this.start("command", this.command);
      this.command = undefined;
    }
    if (!this.co && !this.owner.dying) {
      this.fly(this.orbitPoint(), 0.45, 0, 20);
      if (this.target) this.face(this.target.location, 10);
      const t = this.target;
      if (t && this.owner.phase >= 1 && this.owner.coName !== "ultimate") {
        if (this.t >= this.signatureAt) {
          this.signatureAt = this.t + 620 + Math.floor(randIn(0, 160));
          this.nextSkill = this.t + 120;
          this.start("signature", this.signature(t));
        } else if (this.t >= this.nextSkill) {
          const k = this.kit();
          this.nextSkill = this.t + 130 + Math.floor(randIn(0, 90)) - this.owner.phase * 10;
          this.start("skill", k[Math.floor(Math.random() * k.length)](t));
        }
      }
    }
    this.stepCo();
    this.syncMove();
  }

  /** Fly to a point (keeps orbiting height), returns when close. */
  *goTo(p: Vector3, speed = 0.6, max = 40): Co {
    for (let k = 0; k < max && dist(this.pos, p) > 0.8; k++) {
      this.fly(p, speed, 0, 30);
      yield 1;
    }
  }

  ground2(p: Vector3): Vector3 {
    return this.ground(p);
  }
}

class Seraph extends Choir {
  readonly acts = SERAPH_ACTS;
  readonly walkSpeed = 0.4;
  constructor(e: Entity, owner: Logos) {
    super(e, "seraph", owner, 11, 7.5, 2.2, 0);
    this.signatureAt = 300;
  }
  kit(): ((t: Player) => Co)[] {
    return [(t) => this.dive(t), (t) => this.coal(t), () => this.sanctus()];
  }

  *dive(t: Player): Co {
    const g = this.ground(t.location);
    const dir = flatDir(this.pos, t.location);
    const start = add(add(g, scale(dir, -10)), { x: 0, y: 5, z: 0 });
    yield* this.goTo(start, 0.7);
    teleLine(this.dim, add(g, scale(dir, -10)), dir, 20, 2.6, 16);
    const a = this.act("dive");
    yield 16;
    const end = add(add(g, scale(dir, 10)), { x: 0, y: 1, z: 0 });
    const hit = new Set<string>();
    for (let k = 0; k < 26 && dist(this.pos, end) > 1; k++) {
      this.fly(end, 1.0, 0, 60);
      deco(this.dim, "flame", this.pos, C.fire, 2, 0.4, 0.4, 0.5);
      strike(this, this.pos, 4, (p) => dist(p.location, this.pos) < 2.4, 12, { knock: 1.2, up: 0.4, fire: 4, once: hit });
      yield 1;
    }
    yield Math.max(1, a.ticks - 16 - 26);
  }

  *coal(t: Player): Co {
    this.faceNow(t.location);
    const a = this.act("coal");
    const spot = this.ground(lead(t, 16));
    teleCircle(this.dim, spot, 2.6, a.marks[0] + 16);
    yield a.marks[0];
    const from = add(this.pos, { x: 0, y: 0.5, z: 0 });
    const T = 16;
    const e = spawnProp(this.dim, "coal", from, 0, this.entity);
    fire({
      dim: this.dim, pos: from, vel: { x: (spot.x - from.x) / T, y: (spot.y - from.y) / T + 0.04 * T * 0.5, z: (spot.z - from.z) / T },
      life: T + 3, radius: 0.1, dmg: 0, owner: this.entity, gravity: 0.04, entity: e, ground: true,
      trail: (s) => moveProp(e, s.pos),
      onEnd: () => {
        sound(this.dim, "fire.ignite", spot, 3, 0.7);
        burst(this.dim, spot, C.fire, 16, 4);
        strike(this, spot, 4, (p) => inCircle(p, spot, 2.6), 12, { up: 0.4, from: spot, fire: 4 });
        zone(this.dim, spot, 2.6, 120, { dmg: 3, every: 10, col: C.fire, owner: this.entity, kind: "fire", cause: EntityDamageCause.fire });
      },
    });
    yield a.ticks - a.marks[0];
  }

  *rings(marks: readonly number[], maxR: number, dmg: number): Co {
    let last = 0;
    for (const m of marks) {
      yield m - last;
      last = m;
      const c = this.ground(this.pos);
      sound(this.dim, "mob.blaze.shoot", c, 3, 0.7);
      shock(this.dim, c, maxR, 14, C.fire);
      const hit = new Set<string>();
      addTask("seraph-ring", (age) => {
        const r = 1 + age * (maxR / 14);
        strike(this, c, r + 2, (p) => grounded(p) && inRingBand(p, c, r - 1, r + 0.3, 3), dmg, { up: 0.4, from: c, fire: 3, once: hit });
        return age < 14;
      });
    }
  }

  *sanctus(): Co {
    const a = this.act("sanctus");
    sound(this.dim, "mob.blaze.breathe", this.pos, 3, 0.6);
    yield* this.rings(a.marks, 9, 8);
    yield 12;
  }

  *signature(): Co {
    // TRISAGION: holy, holy, holy — three great rings, jump each one
    const a = this.act("trisagion");
    notify(this.owner.audience(), "§6Seraph: Trisagion", Pri.Phase);
    sound(this.dim, "mob.evocation_illager.prepare_attack", this.pos, 4, 0.6);
    yield* this.rings(a.marks, 15, 14);
    yield a.ticks - a.marks[a.marks.length - 1];
  }

  /** Ultimate role: close a ring of holy fire around the arena. */
  *fireRing(center: Vector3, ticks: number): Co {
    yield* this.goTo(add(center, { x: 0, y: 12, z: 0 }), 0.8);
    this.act("sanctus");
    for (let k = 0; k < ticks; k++) {
      const R = 20 - (7 * k) / ticks;
      if (k % 8 === 0) {
        for (let i = 0; i < 30; i++) deco(this.dim, "flame", add(center, scale(dirOfYaw(i * 12 + k), R)), C.fire, 1, 0.3, 0.5, 0.8);
      }
      if (k % 10 === 0) {
        for (const p of fightersNear(this.dim, center, 34)) {
          if (flatDist(p.location, center) > R) hurt(p, 6, this.entity, EntityDamageCause.fire);
        }
      }
      yield 1;
    }
    this.endAct();
  }
}

class Cherub extends Choir {
  readonly acts = CHERUB_ACTS;
  readonly walkSpeed = 0.35;
  warding = 0;
  constructor(e: Entity, owner: Logos) {
    super(e, "cherub", owner, 8, 1.5, 1.2, 120);
  }
  kit(): ((t: Player) => Co)[] {
    return [(t) => this.sweep(t), () => this.ward(), (t) => this.gaze4(t)];
  }

  tick(): void {
    super.tick();
    if (this.warding > 0 && this.valid) {
      this.warding--;
      if (this.warding % 4 === 0) beam(this.dim, add(this.pos, { x: 0, y: 2, z: 0 }), add(this.owner.pos, { x: 0, y: 4, z: 0 }), C.gold, 0.45);
      if (this.takenSince >= 40) {
        this.warding = 0;
        sound(this.dim, "random.glass", this.pos, 3, 0.8);
        burst(this.dim, add(this.pos, { x: 0, y: 2, z: 0 }), C.gold, 20, 5);
      }
    }
  }

  *sweep(t: Player): Co {
    yield* this.goTo(add(t.location, { x: randIn(-2, 2), y: 1.5, z: randIn(-2, 2) }), 0.6, 30);
    const c = this.ground(this.pos);
    const a = this.act("sweep");
    teleCircle(this.dim, c, 4.8, a.marks[0]);
    yield a.marks[0];
    sound(this.dim, "item.trident.riptide_2", c, 3, 0.8);
    shock(this.dim, c, 5, 8, C.fire);
    strike(this, c, 6, (p) => inCircle(p, c, 4.8, 4), 14, { knock: 1.5, up: 0.4, from: c, fire: 3 });
    yield a.ticks - a.marks[0];
  }

  *ward(): Co {
    const a = this.act("ward");
    this.takenSince = 0;
    this.warding = 140;
    sound(this.dim, "beacon.activate", this.pos, 3, 1.1);
    yield a.ticks;
  }

  *gaze4(t: Player): Co {
    this.faceNow(t.location);
    const a = this.act("gaze4");
    const c = this.ground(this.pos);
    a.marks.forEach((m, i) => teleCone(this.dim, c, dirOfYaw(this.yaw + i * 90), 70, 9, m));
    let last = 0;
    const faces = ["man", "lion", "eagle", "ox"];
    for (let i = 0; i < a.marks.length; i++) {
      yield a.marks[i] - last;
      last = a.marks[i];
      const dir = dirOfYaw(this.yaw + i * 90);
      sound(this.dim, faces[i] === "lion" ? "mob.ravager.roar" : "mob.enderdragon.flap", c, 2, 1.0 + i * 0.1);
      strike(this, c, 11, (p) => inCone(p, c, dir, 70, 9, 5), 10, faces[i] === "lion" ? { knock: 2.2, up: 0.4, from: c } :
        faces[i] === "ox" ? { effects: [["slowness", 50, 2]] } : { knock: 0.6 });
    }
    yield a.ticks - last;
  }

  *signature(t: Player): Co {
    yield* this.sweep(t);
  }

  /** Ultimate role: plant the flaming sword. Returns the Eden spot through `out`. */
  *gate(spot: Vector3): Co {
    yield* this.goTo(add(spot, { x: 0, y: 2, z: 0 }), 0.8, 50);
    const a = this.act("gate");
    yield a.marks[0];
    sound(this.dim, "item.trident.thunder", spot, 4, 0.9);
    yield a.ticks - a.marks[0];
  }
}

class Ophan extends Choir {
  readonly acts = OPHAN_ACTS;
  readonly walkSpeed = 0.35;
  constructor(e: Entity, owner: Logos) {
    super(e, "ophan", owner, 13.5, 3.5, -1.6, 240);
    this.signatureAt = 500;
  }
  kit(): ((t: Player) => Co)[] {
    return [(t) => this.roll(t), () => this.eyes(), () => this.restore()];
  }

  *roll(t: Player): Co {
    const g = this.ground(t.location);
    const dir = flatDir(this.pos, t.location);
    const start = add(add(g, scale(dir, -12)), { x: 0, y: 1.6, z: 0 });
    yield* this.goTo(start, 0.7);
    teleLine(this.dim, add(g, scale(dir, -12)), dir, 24, 3.2, 14);
    const a = this.act("roll");
    yield 14;
    const end = add(add(g, scale(dir, 12)), { x: 0, y: 1.6, z: 0 });
    const hit = new Set<string>();
    for (let k = 0; k < 30 && dist(this.pos, end) > 1; k++) {
      this.fly(end, 0.95, 0, 60);
      deco(this.dim, "flame", this.ground(this.pos), C.beryl, 2, 0.6, 0.4, 0.3);
      strike(this, this.pos, 4, (p) => dist(p.location, add(this.pos, { x: 0, y: -1, z: 0 })) < 2.6, 14, { knock: 1.6, up: 0.5, once: hit });
      yield 1;
    }
    yield Math.max(1, a.ticks - 14 - 30);
  }

  *eyes(): Co {
    const a = this.act("eyes");
    const tgts = this.fighters.slice(0, 3);
    const lines = tgts.map((p) => ({ from: { ...this.pos }, dir: norm(sub(add(p.location, { x: 0, y: 1, z: 0 }), this.pos)) }));
    for (const l of lines) teleLine(this.dim, this.ground(l.from), { x: l.dir.x, y: 0, z: l.dir.z }, 20, 1.6, a.marks[0]);
    yield a.marks[0];
    sound(this.dim, "mob.elderguardian.curse", this.pos, 3, 1.4);
    for (const l of lines) {
      beam(this.dim, l.from, add(l.from, scale(l.dir, 20)), C.beryl, 0.5);
      const g = this.ground(l.from);
      strike(this, g, 22, (p) => inLine(p, g, l.dir, 20, 1.6, 12), 10, { cause: EntityDamageCause.magic });
    }
    yield a.ticks - a.marks[0];
  }

  *restore(): Co {
    const a = this.act("restore");
    this.takenSince = 0;
    sound(this.dim, "beacon.ambient", this.pos, 3, 1.4);
    for (let k = 0; k < a.ticks && this.takenSince < 40; k++) {
      if (k % 4 === 0) beam(this.dim, this.pos, add(this.owner.pos, { x: 0, y: 4, z: 0 }), C.beryl, 0.4);
      if (k % 10 === 0) this.owner.healBy(this.owner.maxHp * 0.004);
      yield 1;
    }
  }

  *signature(): Co {
    // WHEELS WITHIN WHEELS: gravity well of fiery spokes
    const a = this.act("wheels");
    notify(this.owner.audience(), "§bOphan: Wheels within Wheels", Pri.Phase);
    const c = this.ground(this.pos);
    teleCircle(this.dim, c, 9, a.marks[0]);
    yield a.marks[0];
    const lastHit = new Map<string, number>();
    for (let k = 0; k < a.ticks - a.marks[0] - 4; k++) {
      for (const p of fightersNear(this.dim, c, 12)) knock(p, c, -0.12, 0);
      for (let i = 0; i < 6; i++) {
        const dir = dirOfYaw(k * 5 + i * 60);
        if (k % 3 === 0) bullet(this.dim, add(c, { x: 0, y: 1, z: 0 }), dir, 30, 6, C.ember, 0.5);
        for (const p of fightersNear(this.dim, c, 9)) {
          if ((lastHit.get(p.id) ?? -99) > k - 8) continue;
          if (inLine(p, c, dir, 8, 1.4, 4)) {
            lastHit.set(p.id, k);
            hurt(p, 6, this.entity, EntityDamageCause.fire);
          }
        }
      }
      yield 1;
    }
    yield 4;
  }

  /** Ultimate role: hunting eye-beams. */
  *hunt(ticks: number): Co {
    for (let k = 0; k < ticks; k += 30) {
      yield* this.eyes();
    }
  }
}

// =========================================================================== The Word

export class Logos extends Boss {
  readonly acts = A;
  readonly walkSpeed = 0.3;
  readonly title = "The Word";
  readonly ultName = "The Final Word";
  readonly phaseNames = ["", "", "The Seven Seals", "Alpha and Omega"];
  readonly thresholds = [0.7, 0.35];
  readonly defeatText = "§e✦ The Word falls silent";
  readonly ultPhase = 3;
  readonly ultCooldown = 1100;
  readonly arena = 46;
  readonly sigil = "legends:sigil_logos";
  choir = new Map<Role, Choir>();
  seals = 0;

  constructor(e: Entity) {
    super(e, "logos");
  }

  protected onInit(adopted: boolean): void {
    this.flying = true;
    if (adopted) {
      try {
        this.seals = Number(this.entity.getProperty("legends:var")) || 0;
      } catch {
        this.seals = 0;
      }
      this.rebindChoir();
    }
  }

  // ---------------------------------------------------------------- choir management
  rebindChoir(): void {
    for (const role of ["seraph", "cherub", "ophan"] as Role[]) {
      let found: Entity | undefined;
      try {
        found = this.dim.getEntities({ type: `legends:${role}`, location: this.pos, maxDistance: 64 })
          .find((e) => e.getDynamicProperty("legends:owner") === this.id);
      } catch {
        found = undefined;
      }
      if (found) this.choir.set(role, this.makeChoir(role, found));
      else this.speak(role, false);
    }
  }

  makeChoir(role: Role, e: Entity): Choir {
    const existing = beings.get(e.id);
    if (existing instanceof Choir) return existing;
    return role === "seraph" ? new Seraph(e, this) : role === "cherub" ? new Cherub(e, this) : new Ophan(e, this);
  }

  speak(role: Role, withAnim = true): void {
    const at = add(this.pos, add(scale(dirOfYaw(randIn(0, 360)), 6), { x: 0, y: 3, z: 0 }));
    try {
      const e = this.dim.spawnEntity(`legends:${role}`, at);
      const c = this.makeChoir(role, e);
      this.choir.set(role, c);
      if (withAnim) c.start("spawn", c.play("spawn"));
      burst(this.dim, at, C.holy, 24, 5, 0.35, 1);
      sound(this.dim, "beacon.activate", at, 3, 1.5);
    } catch (err) {
      console.warn(`[legends] choir ${role} failed: ${err}`);
    }
  }

  alive(role: Role): Choir | undefined {
    const c = this.choir.get(role);
    return c && c.valid ? c : undefined;
  }

  healBy(amount: number): void {
    const h = this.entity.getComponent("minecraft:health");
    if (!h) return;
    const ceil = this.phase >= 2 && this.phase - 2 < this.thresholds.length ? this.maxHp * this.thresholds[this.phase - 2] : this.maxHp;
    h.setCurrentValue(Math.min(ceil, h.effectiveMax, h.currentValue + amount));
  }

  // ---------------------------------------------------------------- movement / passives
  idle(): void {
    const t = this.target;
    const g = this.ground(t ? t.location : this.home).y;
    if (this.leashed() || !t) {
      this.fly({ x: this.home.x, y: g + 1, z: this.home.z }, 0.25);
      return;
    }
    const want = add(t.location, scale(flatDir(t.location, this.pos), 12));
    this.fly({ x: want.x, y: g + 1, z: want.z }, 0.12, 0, 6);
    this.face(t.location, 4);
  }

  protected onTick(): void {
    const cherub = this.alive("cherub") as Cherub | undefined;
    this.takenMul = cherub && cherub.warding > 0 ? 0.5 : 1;
    if (this.t % 12 === 0) deco(this.dim, "rune", add(this.pos, { x: 0, y: 3, z: 0 }), C.holy, 2, 3, 0.35, 0.4);
  }

  cleanup(): void {
    for (const c of this.choir.values()) {
      try {
        if (c.entity.isValid) c.entity.remove();
      } catch {
        // ignore
      }
      c.dispose();
    }
    super.cleanup();
  }

  setSeals(n: number): void {
    this.seals = Math.max(0, Math.min(7, n));
    this.prop("var", this.seals);
  }

  // ---------------------------------------------------------------- entrance / transitions
  *entrance(): Co {
    const g = this.ground(this.pos);
    this.place(add(g, { x: 0, y: 1, z: 0 }), this.yaw);
    const a = this.act("advent");
    pillar(this.dim, g, 40, 4, 80, C.holy);
    sound(this.dim, "beacon.activate", g, 6, 0.5);
    for (let k = 0; k < a.ticks; k += 5) {
      deco(this.dim, "rune", add(g, { x: 0, y: 1, z: 0 }), C.holy, 6, 4, 0.4, 1.2);
      if (k === 60) {
        sound(this.dim, "random.totem", g, 4, 0.6);
        flash(this.audience(), C.holy);
        shake(this.audience(), 0.4, 1.0);
        shock(this.dim, g, 18, 16, C.gold);
      }
      yield 5;
    }
    this.endAct();
    for (const role of ["seraph", "cherub", "ophan"] as Role[]) {
      this.speak(role);
      yield 10;
    }
    this.say("§fThe Word is spoken", 0);
  }

  *transition(to: number): Co {
    if (to === 2) {
      const a = this.act("unseal");
      yield a.marks[0];
      this.setPhase(2);
      this.setSeals(1);
      sound(this.dim, "random.glass", this.pos, 4, 0.5);
      sound(this.dim, "beacon.power", this.pos, 4, 0.8);
      shock(this.dim, this.ground(this.pos), 16, 14, C.crimson);
      yield a.ticks - a.marks[0];
      return;
    }
    const a = this.act("speak");
    yield a.marks[0];
    this.setPhase(3);
    this.setSeals(7);
    sound(this.dim, "random.totem", this.pos, 5, 0.5);
    flash(this.audience(), C.holy);
    shake(this.audience(), 0.5, 1.2);
    shock(this.dim, this.ground(this.pos), 22, 16, C.gold);
    yield a.ticks - a.marks[0];
    for (const role of ["seraph", "cherub", "ophan"] as Role[]) if (!this.alive(role)) {
      this.speak(role);
      yield 8;
    }
  }

  // ---------------------------------------------------------------- skills
  skills(): SkillDef[] {
    const deadChoir = (): Role | undefined => (["seraph", "cherub", "ophan"] as Role[]).find((r) => !this.alive(r));
    return [
      { name: "fiat", phases: [1, 2, 3], cd: 220, weight: 4, run: (t) => this.fiat(t) },
      { name: "lances", phases: [1, 2, 3], cd: 160, weight: 3, run: () => this.lances() },
      { name: "judgement", phases: [1, 2, 3], cd: 240, weight: 3, run: (t) => this.judgement(t) },
      { name: "trumpet", phases: [2, 3], cd: 220, weight: 3, run: () => this.trumpet() },
      { name: "babel", phases: [2, 3], cd: 260, weight: 3, run: () => this.babel() },
      { name: "unseal", phases: [2], cd: 300, weight: 4, when: () => this.seals < 6, run: () => this.unseal() },
      { name: "reforge", phases: [3], cd: 800, weight: 5, when: () => deadChoir() !== undefined, run: () => this.reforge(deadChoir()) },
    ];
  }

  eye(): Vector3 {
    return add(this.pos, { x: 0, y: 5.5, z: 0 });
  }

  *fiat(t: Player): Co {
    const a = this.act("fiat");
    const c = this.ground(t.location);
    const cells: { p: Vector3; w: number }[] = [];
    for (let i = -2; i <= 2; i++) for (let j = -2; j <= 2; j++) cells.push({ p: this.ground(add(c, { x: i * 3, y: 0, z: j * 3 })), w: (i + j + 4) % 2 });
    for (const cell of cells) teleCircle(this.dim, cell.p, 1.5, cell.w === 0 ? 26 : 50);
    sound(this.dim, "beacon.activate", c, 3, 1.6);
    for (let wave = 0; wave < 2; wave++) {
      yield wave === 0 ? 26 : 24;
      sound(this.dim, "random.orb", c, 3, 0.6 + wave * 0.3);
      for (const cell of cells) {
        if (cell.w !== wave) continue;
        pillar(this.dim, cell.p, 9, 1.4, 12, C.holy);
        strike(this, cell.p, 3, (p) => inCircle(p, cell.p, 1.55, 6), 14, { cause: EntityDamageCause.magic, up: 0.3, from: cell.p });
      }
    }
    yield Math.max(1, a.ticks - 50);
  }

  *lances(): Co {
    const a = this.act("lances");
    yield a.marks[0];
    const n = 8;
    for (let i = 0; i < n; i++) {
      const tg = this.fighters.length ? this.fighters[i % this.fighters.length] : undefined;
      if (!tg) break;
      const from = add(this.eye(), scale(dirOfYaw(this.yaw + 90 + i * 22.5), 3.5));
      from.y += Math.sin(i) * 1.5;
      const d = norm(sub(add(lead(tg, 8), { x: 0, y: 1, z: 0 }), from));
      const e = spawnProp(this.dim, "light_spear", from, yawOf(d), this.entity);
      sound(this.dim, "item.trident.throw", from, 2, 1.6);
      fire({ dim: this.dim, pos: from, vel: scale(d, 0.75), life: 40, radius: 0.8, dmg: 10, owner: this.entity, entity: e, cause: EntityDamageCause.magic,
        trail: (s) => {
          if ((s.age ?? 0) % 2 === 0) mote(this.dim, s.pos, C.holy, 0.3, 0.3);
        },
        onEnd: (s) => burst(this.dim, s.pos, C.holy, 8, 3) });
      yield 4;
    }
    yield Math.max(1, a.ticks - a.marks[0] - n * 4);
  }

  *judgement(t: Player): Co {
    const a = this.act("gaze");
    let p = this.ground(t.location);
    spiralMark(this.dim, p, C.holy, 3, a.marks[0]);
    teleCircle(this.dim, p, 2, a.marks[0]);
    sound(this.dim, "beacon.power", this.pos, 3, 0.6);
    yield a.marks[0];
    const lastHit = new Map<string, number>();
    for (let k = 0; k < a.ticks - a.marks[0] - 4; k++) {
      if (t.isValid) {
        const d = flatDist(p, t.location);
        if (d > 0.1) p = this.ground(add(p, scale(flatDir(p, t.location), Math.min(0.3, d))));
      }
      if (k % 2 === 0) beam(this.dim, this.eye(), add(p, { x: 0, y: 0.2, z: 0 }), C.holy, 0.55);
      if (k % 6 === 0) zone(this.dim, p, 1.4, 60, { dmg: 3, every: 10, col: C.holy, owner: this.entity, kind: "holy" });
      for (const pl of fightersNear(this.dim, p, 3)) {
        if (inCircle(pl, p, 1.8, 4) && (lastHit.get(pl.id) ?? -99) < k - 10) {
          lastHit.set(pl.id, k);
          hurt(pl, 9, this.entity, EntityDamageCause.magic);
        }
      }
      yield 1;
    }
    yield 4;
  }

  *trumpet(): Co {
    const a = this.act("trumpet");
    const c = this.ground(this.pos);
    let last = 0;
    for (const m of a.marks) {
      yield m - last;
      last = m;
      sound(this.dim, "note.bell", c, 5, 0.5);
      sound(this.dim, "mob.warden.sonic_boom", c, 2, 1.6);
      shock(this.dim, c, 17, 15, C.gold);
      const hit = new Set<string>();
      addTask("trumpet", (age) => {
        const r = 2 + age * 1.05;
        strike(this, c, r + 2, (p) => grounded(p) && inRingBand(p, c, r - 1.05, r + 0.3, 3), 12, { up: 0.5, from: c, once: hit, cause: EntityDamageCause.magic });
        return age < 15;
      });
    }
    yield a.ticks - last;
  }

  *babel(): Co {
    const a = this.act("babel");
    yield a.marks[0];
    sound(this.dim, "mob.evocation_illager.cast_spell", this.pos, 4, 0.7);
    const from = add(this.pos, { x: 0, y: 1.4, z: 0 });
    for (let k = 0; k < a.ticks - a.marks[0] - 6; k += 2) {
      for (let arm = 0; arm < 3; arm++) {
        const d = dirOfYaw(k * 6.5 + arm * 120);
        bullet(this.dim, from, d, 8, 46, C.holy, 0.55);
        fire({ dim: this.dim, pos: from, vel: scale(d, 0.4), life: 46, radius: 0.75, dmg: 6, owner: this.entity, cause: EntityDamageCause.magic });
      }
      if (k % 8 === 0) deco(this.dim, "rune", from, C.gold, 3, 1, 0.35, 1);
      yield 2;
    }
    yield 6;
  }

  *unseal(): Co {
    const a = this.act("unseal");
    yield a.marks[0];
    this.setSeals(this.seals + 1);
    sound(this.dim, "random.glass", this.pos, 4, 0.6);
    burst(this.dim, add(this.pos, { x: 0, y: 4, z: 0 }), C.crimson, 24, 6, 0.35, 1);
    // seal judgement: stone tablets fall on everyone
    const spots = this.fighters.map((p) => this.ground(lead(p, 10)));
    for (const s of spots) {
      teleCircle(this.dim, s, 2.8, 26);
      const from = add(s, { x: 0, y: 16, z: 0 });
      const e = spawnProp(this.dim, "tablet", from, randIn(0, 360), this.entity);
      fire({ dim: this.dim, pos: from, vel: { x: 0, y: -16 / 26, z: 0 }, life: 26, radius: 0.1, dmg: 0, owner: this.entity, entity: e,
        trail: (sh) => moveProp(e, sh.pos),
        onEnd: () => {
          sound(this.dim, "random.anvil_land", s, 3, 0.5);
          shock(this.dim, s, 5, 8, C.holy);
          deco(this.dim, "shard", s, C.white, 10, 1.5, 0.35, 5);
          strike(this, s, 4, (p) => inCircle(p, s, 2.8), 16, { up: 0.5, from: s, effects: [["slowness", 40, 1]] });
        } });
    }
    yield a.ticks - a.marks[0];
  }

  *reforge(role: Role | undefined): Co {
    if (!role) return;
    const a = this.act("reforge");
    sound(this.dim, "beacon.power", this.pos, 4, 1.2);
    for (let k = 0; k < a.marks[0]; k += 6) {
      deco(this.dim, "rune", add(this.pos, { x: 0, y: 4, z: 0 }), C.holy, 4, 2, 0.35, 0.8);
      yield 6;
    }
    this.speak(role);
    notify(this.audience(), "§fThe Word speaks again", Pri.Phase);
    yield a.ticks - a.marks[0];
  }

  // ---------------------------------------------------------------- ultimate
  *ultimate(): Co {
    const center = this.ground(this.home);
    const a = this.act("apocalypse");
    sound(this.dim, "random.totem", center, 6, 0.4);
    shake(this.audience(), 0.3, 3);
    for (let k = 0; k < 30; k++) {
      this.fly({ x: center.x, y: center.y + 1, z: center.z }, 0.5, 0, 8);
      yield 1;
    }
    const eden = this.ground(add(center, scale(dirOfYaw(randIn(0, 360)), randIn(7, 12))));
    const cherub = this.alive("cherub") as Cherub | undefined;
    const seraph = this.alive("seraph") as Seraph | undefined;
    const ophan = this.alive("ophan") as Ophan | undefined;
    const edenAt = a.marks[0];
    const ringT = a.marks[1] - a.marks[0];
    const finalAt = a.marks[2];
    if (cherub) {
      cherub.interrupt();
      cherub.command = cherub.gate(eden);
    }
    if (seraph) {
      seraph.interrupt();
      seraph.command = seraph.fireRing(center, ringT + 40);
    }
    if (ophan) {
      ophan.interrupt();
      ophan.command = ophan.hunt(ringT + 40);
    }
    yield edenAt - 30;
    // Eden: the only refuge
    const sword = spawnProp(this.dim, "eden_sword", eden, 0, cherub ? cherub.entity : this.entity);
    sound(this.dim, "item.trident.thunder", eden, 5, 0.8);
    pillar(this.dim, eden, 14, 2.2, 40, C.safe);
    const edenLife = finalAt - edenAt;
    teleSafe(this.dim, eden, 3.6, edenLife);
    if (!cherub) notify(this.audience(), "§6Seek the flaming sword", Pri.Phase);
    for (let k = edenAt; k < finalAt; k++) {
      if ((k - edenAt) % 40 === 0) pillar(this.dim, eden, 14, 2.2, 40, C.safe);
      if (k === finalAt - 44) teleCircle(this.dim, center, 26, 44);
      if (k > a.marks[1] && k % 6 === 0) pillar(this.dim, this.ground(add(center, scale(dirOfYaw(randIn(0, 360)), randIn(4, 22)))), 8, 1, 10, C.holy);
      if (k > finalAt - 30 && k % 5 === 0) glint(this.dim, this.eye(), C.white, 3 + (k - finalAt + 30) * 0.15);
      yield 1;
    }
    // The Final Word
    sound(this.dim, "random.totem", center, 8, 0.5);
    sound(this.dim, "random.explode", center, 6, 0.4);
    flash(this.audience(), C.white);
    shake(this.audience(), 0.9, 1.4);
    shock(this.dim, center, 28, 18, C.holy);
    for (const p of this.fighters) {
      if (flatDist(p.location, eden) <= 3.7) {
        glint(this.dim, add(p.location, { x: 0, y: 1, z: 0 }), C.safe, 1.2);
        continue;
      }
      hurt(p, 55, this.entity);
      hurt(p, 22, this.entity, EntityDamageCause.magic);
    }
    yield Math.max(1, a.ticks - finalAt);
    removeProp(sword);
  }
}
