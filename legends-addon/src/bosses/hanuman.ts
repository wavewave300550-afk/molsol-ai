/**
 * HANUMAN (หนุมาน) — Son of the Wind.
 *
 * Identity: speed, technique and versatility. A duelist who reads the
 * player: trident combos, a wind-step behind you, and a Vajra guard that
 * punishes button-mashing (he glows gold - stop attacking!).
 *
 *   I   Son of the Wind     trident combo, moon-leap slam, tail whip,
 *                           wind step, Vajra guard + counter
 *   II  Burning of Lanka     tail ablaze: fire spin, Lanka fire-lines,
 *                           shrink-and-dart then grow giant
 *   III สี่หน้าแปดกร          four faces, eight arms: weapon barrage, discus
 *                           boomerangs, a hurled mountain
 *   ULT หาวเป็นดาวเป็นเดือน (Yawning Stars and Moon) — star rain, two crescent
 *                           blades sweeping round him, then the Wind-Father's breath.
 *   Vayu's Breath: when struck down the first time, four wind wisps gather -
 *                           destroy them all in 8 s or the wind revives him.
 */
import { Entity, EntityDamageCause, Player, Vector3 } from "@minecraft/server";
import { HANUMAN_ACTS } from "../generated/data.js";
import { fightersNear, hurt, inCircle, inCone, inLine, knock, setHealth } from "../core/combat.js";
import { burst, C, deco, flash, glint, pillar, shake, shock, sound, teleCircle, teleCone, teleLine, bullet, mote } from "../core/fx.js";
import { fire, moveProp, removeProp, spawnProp, zone } from "../core/hazards.js";
import { addTask } from "../core/tasks.js";
import { add, dirOfYaw, dist, flatDir, flatDist, flatSegDist, randIn, rotY, scale, sub, yawOf } from "../core/vec.js";
import { Co, SkillDef } from "./being.js";
import { Boss } from "./boss.js";
import { ahead, lead, strike } from "./kit.js";
import { Pri } from "../core/notice.js";

const A = HANUMAN_ACTS;

export class Hanuman extends Boss {
  readonly acts = A;
  readonly walkSpeed = 0.26;
  readonly title = "หนุมาน Hanuman";
  readonly ultName = "Yawning Stars and Moon";
  readonly phaseNames = ["", "", "The Burning of Lanka", "Four Faces, Eight Arms"];
  readonly thresholds = [0.65, 0.3];
  readonly defeatText = "§e✦ Hanuman bows to a worthy foe";
  readonly ultPhase = 3;
  readonly ultCooldown = 900;
  readonly sigil = "legends:sigil_hanuman";
  guarding = false;
  countered?: Player;
  revived = false;
  wrath = 1;

  constructor(e: Entity) {
    super(e, "hanuman");
  }

  protected onInit(): void {
    if (this.phase >= 3) this.form("legends:form_divine");
  }

  reach(): number {
    return this.phase >= 3 ? 1.4 : 1;
  }

  form(ev: string): void {
    try {
      this.entity.triggerEvent(ev);
    } catch {
      // ignore
    }
  }

  idle(): void {
    const t = this.target;
    if (this.leashed() || !t) {
      this.walk(this.home, this.walkSpeed, 2);
      return;
    }
    const d = flatDist(this.pos, t.location);
    if (d > 4) this.walk(t.location, this.walkSpeed, 3.5);
    else {
      // circle-strafe like a duelist
      const side = add(t.location, scale(rotY(flatDir(t.location, this.pos), 25), 4));
      this.walk(side, this.walkSpeed * 0.6, 0.2);
      this.face(t.location, 30);
    }
  }

  onDamaged(amount: number, by?: Player): void {
    super.onDamaged(amount, by);
    if (this.guarding && by && !this.countered) this.countered = by;
  }

  protected onTick(): void {
    if (this.phase >= 2 && this.t % 6 === 0) deco(this.dim, "flame", ahead(this, -2.5, 3.2), C.fire, 2, 0.6, 0.35, 0.6);
    if (this.phase >= 3 && this.t % 10 === 0) mote(this.dim, add(this.pos, { x: randIn(-1.5, 1.5), y: randIn(1, 6), z: randIn(-1.5, 1.5) }), C.star, 0.25, 0.8);
  }

  // ---------------------------------------------------------------- entrance / transitions
  *entrance(): Co {
    const g = this.ground(this.pos);
    const sky = add(g, { x: 0, y: 24, z: 0 });
    this.place(sky, this.yaw);
    for (let k = 0; k < 24; k++) {
      this.place(add(g, { x: 0, y: 24 * (1 - (k + 1) / 24) ** 2, z: 0 }), this.yaw);
      if (k % 3 === 0) deco(this.dim, "feather", this.pos, C.wind, 3, 1, 0.3, 0.6);
      yield 1;
    }
    const a = this.act("descend");
    yield a.marks[0];
    sound(this.dim, "mob.breeze.land", g, 4, 0.5);
    sound(this.dim, "random.explode", g, 2, 0.8);
    shake(this.audience(), 0.5, 0.8);
    shock(this.dim, g, 12, 12, C.wind);
    yield a.ticks - a.marks[0];
    const tt = this.act("taunt");
    sound(this.dim, "mob.evocation_illager.prepare_attack", g, 3, 0.8);
    yield tt.ticks;
    this.endAct();
    this.say("§fหนุมาน Hanuman descends", 0);
  }

  *transition(to: number): Co {
    if (to === 2) {
      const a = this.act("ignite");
      yield a.marks[0];
      this.setPhase(2);
      sound(this.dim, "mob.blaze.shoot", this.pos, 3, 0.6);
      sound(this.dim, "fire.ignite", this.pos, 3, 0.8);
      burst(this.dim, ahead(this, -2, 3), C.fire, 30, 6, 0.35, 0.8);
      shock(this.dim, this.pos, 10, 10, C.fire);
      yield a.ticks - a.marks[0];
      return;
    }
    const a = this.act("awaken");
    for (let k = 0; k < a.marks[0]; k += 4) {
      deco(this.dim, "feather", add(this.pos, { x: 0, y: 2, z: 0 }), C.wind, 4, 2.5, 0.35, 1.5);
      yield 4;
    }
    this.setPhase(3);
    this.form("legends:form_divine");
    sound(this.dim, "mob.evocation_illager.cast_spell", this.pos, 4, 0.5);
    sound(this.dim, "beacon.power", this.pos, 4, 0.7);
    shake(this.audience(), 0.6, 1.2);
    flash(this.audience(), { red: 1, green: 0.95, blue: 0.8 });
    shock(this.dim, this.pos, 18, 14, C.gold);
    burst(this.dim, add(this.pos, { x: 0, y: 4, z: 0 }), C.star, 40, 8, 0.4, 2);
    yield a.ticks - a.marks[0];
  }

  // ---------------------------------------------------------------- skills
  skills(): SkillDef[] {
    return [
      { name: "combo", phases: [1, 2, 3], cd: 60, weight: 5, max: 7, run: (t) => this.combo(t) },
      { name: "leap", phases: [1, 2], cd: 150, weight: 3, min: 6, run: (t) => this.leapSlam(t) },
      { name: "whip", phases: [1, 2], cd: 120, weight: 3, max: 7, run: () => this.tailWhip() },
      { name: "windstep", phases: [1, 2, 3], cd: 200, weight: 3, min: 4, max: 20, run: (t) => this.windStep(t) },
      { name: "guard", phases: [1, 2, 3], cd: 360, weight: 2, max: 10, run: () => this.guard() },
      { name: "firespin", phases: [2], cd: 160, weight: 3, max: 8, run: () => this.fireSpin() },
      { name: "lanka", phases: [2], cd: 320, weight: 3, run: (t) => this.lanka(t) },
      { name: "shrink", phases: [2], cd: 420, weight: 2, run: (t) => this.shrink(t) },
      { name: "barrage", phases: [3], cd: 140, weight: 4, max: 10, run: (t) => this.barrage(t) },
      { name: "discus", phases: [3], cd: 160, weight: 3, min: 5, run: (t) => this.discus(t) },
      { name: "mountain", phases: [3], cd: 300, weight: 2, min: 6, run: (t) => this.mountain(t) },
      { name: "leap3", phases: [3], cd: 200, weight: 2, min: 8, run: (t) => this.leapSlam(t) },
    ];
  }

  dmg(n: number): number {
    return n * this.wrath;
  }

  *approach(t: Player, range: number, max = 24): Co {
    for (let k = 0; k < max && flatDist(this.pos, t.location) > range; k++) {
      this.walk(t.location, this.walkSpeed * 1.5, range);
      yield 1;
    }
  }

  *combo(t: Player): Co {
    yield* this.approach(t, 3.5 * this.reach());
    this.faceNow(t.location);
    const a = this.act("combo");
    const r = this.reach();
    const g = () => this.ground(this.pos);
    teleLine(this.dim, g(), dirOfYaw(this.yaw), 6.5 * r, 2.2, a.marks[0]);
    yield a.marks[0];
    sound(this.dim, "item.trident.throw", this.pos, 2, 0.8);
    strike(this, this.pos, 8 * r, (p) => inLine(p, this.pos, dirOfYaw(this.yaw), 6.5 * r, 2.2), this.dmg(16), { knock: 0.8 });
    this.face(t.location, 35);
    teleCone(this.dim, g(), dirOfYaw(this.yaw), 170, 5.2 * r, a.marks[1] - a.marks[0]);
    yield a.marks[1] - a.marks[0];
    sound(this.dim, "item.trident.riptide_1", this.pos, 2, 1.2);
    strike(this, this.pos, 7 * r, (p) => inCone(p, this.pos, dirOfYaw(this.yaw), 170, 5.2 * r), this.dmg(14), { knock: 1.2 });
    this.face(t.location, 35);
    const slam = this.ground(ahead(this, 3 * r));
    teleCircle(this.dim, slam, 3.4 * r, a.marks[2] - a.marks[1]);
    yield a.marks[2] - a.marks[1];
    sound(this.dim, "item.trident.thunder", slam, 2, 1.3);
    shock(this.dim, slam, 6 * r, 8, C.wind);
    strike(this, slam, 5 * r, (p) => inCircle(p, slam, 3.4 * r), this.dmg(20), { knock: 1.0, up: 0.7, from: slam });
    yield a.ticks - a.marks[2];
  }

  *leapSlam(t: Player): Co {
    this.faceNow(t.location);
    const j = this.act("jump");
    const dest = this.ground(lead(t, 16));
    const r = 4.2 * this.reach();
    teleCircle(this.dim, dest, r, j.marks[0] + 20);
    yield j.marks[0];
    sound(this.dim, "mob.breeze.jump", this.pos, 3, 0.6);
    this.act("air");
    yield* this.leap(dest, 20, 9, (k) => {
      if (k % 3 === 0) deco(this.dim, "feather", this.pos, C.wind, 2, 0.5, 0.25, 0.3);
    });
    const s = this.act("slam");
    yield s.marks[0];
    sound(this.dim, "mob.breeze.land", dest, 4, 0.6);
    sound(this.dim, "random.explode", dest, 2, 1.0);
    shake(this.audience(), 0.45, 0.6);
    shock(this.dim, dest, 9 * this.reach(), 10, this.phase >= 2 ? C.fire : C.wind);
    strike(this, dest, r + 2, (p) => inCircle(p, dest, r), this.dmg(18), { knock: 1.3, up: 0.8, from: dest });
    yield s.ticks - s.marks[0];
  }

  *tailWhip(): Co {
    const a = this.act("tail_whip");
    const c = this.ground(this.pos);
    teleCircle(this.dim, c, 6.5, a.marks[0]);
    yield a.marks[0];
    sound(this.dim, "mob.breeze.whirl", c, 3, 0.7);
    shock(this.dim, c, 7, 8, C.wind);
    strike(this, c, 8, (p) => inCircle(p, c, 6.5), this.dmg(15), { knock: 1.6, up: 0.4, from: c });
    yield a.ticks - a.marks[0];
  }

  *windStep(t: Player): Co {
    // the gust sound and swirl at the destination are the tell: turn around!
    let behind: Vector3;
    try {
      const v = t.getViewDirection();
      behind = this.ground(add(t.location, { x: -v.x * 2.6, y: 0, z: -v.z * 2.6 }));
    } catch {
      behind = this.ground(t.location);
    }
    sound(this.dim, "mob.breeze.charge", t.location, 3, 1.2);
    deco(this.dim, "feather", add(behind, { x: 0, y: 1, z: 0 }), C.wind, 6, 0.8, 0.3, 1.2);
    teleCircle(this.dim, behind, 1.4, 12, C.warn);
    yield 12;
    deco(this.dim, "feather", add(this.pos, { x: 0, y: 1, z: 0 }), C.wind, 8, 1, 0.3, 1.5);
    this.place(behind, yawOf(flatDir(behind, t.location)));
    const a = this.act("dash");
    teleLine(this.dim, behind, dirOfYaw(this.yaw), 4.5, 2.2, a.marks[0]);
    yield a.marks[0];
    sound(this.dim, "item.trident.throw", this.pos, 2, 1.1);
    strike(this, this.pos, 6, (p) => inLine(p, this.pos, dirOfYaw(this.yaw), 4.5, 2.2), this.dmg(14), { knock: 1.0 });
    yield a.ticks - a.marks[0];
  }

  *guard(): Co {
    const a = this.act("guard");
    this.fx(4);
    this.guarding = true;
    this.countered = undefined;
    this.takenMul = 0.2;
    sound(this.dim, "random.anvil_use", this.pos, 2, 1.6);
    for (let k = 0; k < a.ticks - 6 && !this.countered; k++) {
      if (k % 8 === 0) glint(this.dim, add(this.pos, { x: 0, y: 2.5, z: 0 }), C.gold, 1.4);
      yield 1;
    }
    this.guarding = false;
    this.takenMul = 1;
    this.fx(0);
    const who = this.countered as Player | undefined;
    if (who && who.isValid) {
      const c = this.act("counter");
      const at = this.ground(add(who.location, scale(flatDir(who.location, this.pos), 1.8)));
      this.place(at, yawOf(flatDir(at, who.location)));
      sound(this.dim, "item.trident.thunder", at, 3, 1.4);
      yield c.marks[0];
      glint(this.dim, add(who.location, { x: 0, y: 1, z: 0 }), C.gold, 2);
      hurt(who, this.dmg(22), this.entity);
      knock(who, this.pos, 2.2, 0.6);
      yield c.ticks - c.marks[0];
    }
  }

  *fireSpin(): Co {
    const a = this.act("fire_spin");
    const c = this.ground(this.pos);
    teleCircle(this.dim, c, 6.3, a.marks[0]);
    yield a.marks[0];
    sound(this.dim, "mob.blaze.shoot", c, 3, 0.7);
    shock(this.dim, c, 7, 8, C.fire);
    strike(this, c, 8, (p) => inCircle(p, c, 6.3), this.dmg(16), { knock: 1.3, up: 0.4, from: c, fire: 4 });
    zone(this.dim, c, 6.3, 100, { dmg: 3, every: 10, col: C.fire, owner: this.entity, kind: "fire", cause: EntityDamageCause.fire });
    yield a.ticks - a.marks[0];
  }

  *lanka(t: Player): Co {
    const pts: Vector3[] = [];
    const base = randIn(0, 360);
    for (let i = 0; i < 3; i++) pts.push(this.ground(add(t.location, scale(dirOfYaw(base + i * 120), 7))));
    for (const p of pts) {
      teleCircle(this.dim, p, 3, 26);
      const j = this.act("jump");
      yield j.marks[0];
      this.act("air");
      yield* this.leap(p, 12, 5);
      const s = this.act("slam");
      yield s.marks[0];
      sound(this.dim, "mob.blaze.shoot", p, 3, 0.6);
      pillar(this.dim, p, 7, 1.4, 20, C.fire);
      shock(this.dim, p, 5, 8, C.fire);
      strike(this, p, 4.5, (pl) => inCircle(pl, p, 3), this.dmg(14), { knock: 1, up: 0.6, from: p, fire: 4 });
      yield 4;
    }
    this.endAct();
    // the burning tail drew lines of fire between the landings
    for (let i = 0; i < 3; i++) teleLine(this.dim, pts[i], flatDir(pts[i], pts[(i + 1) % 3]), flatDist(pts[i], pts[(i + 1) % 3]), 1.8, 16, C.fire);
    yield 16;
    addTask("lanka", (age) => {
      for (let i = 0; i < 3; i++) {
        const a = pts[i];
        const b = pts[(i + 1) % 3];
        if (age % 8 === 0) {
          const L = flatDist(a, b);
          for (let s = 0; s < L; s += 2.2) deco(this.dim, "flame", add(a, scale(flatDir(a, b), s)), C.fire, 1, 0.3, 0.45, 0.8);
        }
        if (age % 10 === 0) {
          for (const p of fightersNear(this.dim, a, flatDist(a, b) + 3)) {
            if (flatSegDist(p.location, a, b).d < 1.0 && Math.abs(p.location.y - a.y) < 2.5) hurt(p, 5, this.entity, EntityDamageCause.fire);
          }
        }
      }
      return age < 140 && this.valid;
    });
    yield 10;
  }

  *shrink(t: Player): Co {
    this.prop("var", 1);
    this.form("legends:form_tiny");
    this.act("shrunk");
    sound(this.dim, "mob.breeze.idle_air", this.pos, 3, 2);
    this.takenMul = 0.6;
    for (let k = 0; k < 70; k++) {
      const goal = add(t.location, scale(dirOfYaw(k * 23 + (k % 7) * 40), 3 + (k % 5)));
      this.walk(goal, 0.55, 0.2, 90);
      if (k % 4 === 0) deco(this.dim, "feather", this.pos, C.wind, 1, 0.2, 0.2, 0.3);
      yield 1;
    }
    this.takenMul = 1;
    const c = this.ground(this.pos);
    const a = this.act("grow");
    this.prop("var", 0);
    this.form(this.phase >= 3 ? "legends:form_divine" : "legends:form_base");
    teleCircle(this.dim, c, 7, a.marks[0]);
    yield a.marks[0];
    sound(this.dim, "random.explode", c, 3, 0.6);
    shake(this.audience(), 0.6, 0.8);
    shock(this.dim, c, 12, 12, C.fire);
    strike(this, c, 9, (p) => inCircle(p, c, 7), this.dmg(20), { knock: 1.8, up: 0.8, from: c, fire: 3 });
    yield a.ticks - a.marks[0];
  }

  *barrage(t: Player): Co {
    yield* this.approach(t, 5, 16);
    this.faceNow(t.location);
    const a = this.act("barrage");
    const offs = [0, 60, -60, 120, -120, 180];
    let last = 0;
    a.marks.forEach((m, i) => teleCone(this.dim, this.ground(this.pos), dirOfYaw(this.yaw + offs[i]), 62, 8, m));
    for (let i = 0; i < a.marks.length; i++) {
      yield a.marks[i] - last;
      last = a.marks[i];
      const dir = dirOfYaw(this.yaw + offs[i]);
      sound(this.dim, "item.trident.hit", this.pos, 2, 0.8 + i * 0.08);
      strike(this, this.pos, 10, (p) => inCone(p, this.pos, dir, 62, 8, 6), this.dmg(12), { knock: 0.9 });
    }
    yield a.ticks - last;
  }

  *discus(t: Player): Co {
    this.faceNow(t.location);
    const a = this.act("discus");
    const dirs = [-14, 14].map((o) => rotY(flatDir(this.pos, t.location), o));
    for (const d of dirs) teleLine(this.dim, this.ground(this.pos), d, 19, 2, a.marks[0] + 10, C.warn);
    yield a.marks[0];
    sound(this.dim, "item.trident.throw", this.pos, 3, 0.6);
    for (const d of dirs) {
      const start = ahead(this, 1.5, 2.5);
      const e = spawnProp(this.dim, "discus", start, 0, this.entity);
      const hitOut = new Set<string>();
      const hitBack = new Set<string>();
      let k = 0;
      addTask("discus", () => {
        k++;
        if (!this.valid) {
          removeProp(e);
          return false;
        }
        const out = k <= 22;
        const s = out ? k / 22 : Math.max(0, 1 - (k - 22) / 22);
        const home = add(this.pos, { x: 0, y: 2.5, z: 0 });
        const p = add(out ? start : home, scale(d, 19 * s));
        p.y = start.y;
        moveProp(e, p);
        if (k % 2 === 0) mote(this.dim, p, C.gold, 0.35, 0.3);
        strike(this, p, 3, (pl) => dist(add(pl.location, { x: 0, y: 1, z: 0 }), p) < 1.8, this.dmg(14),
          { knock: 0.8, once: out ? hitOut : hitBack });
        if (k >= 44) {
          removeProp(e);
          return false;
        }
        return true;
      });
    }
    yield a.ticks - a.marks[0];
  }

  *mountain(t: Player): Co {
    this.faceNow(t.location);
    const a = this.act("mountain");
    const lift = add(this.pos, { x: 0, y: 9, z: 0 });
    const e = spawnProp(this.dim, "boulder", add(this.pos, { x: 0, y: -2, z: 0 }), 0, this.entity);
    sound(this.dim, "mob.warden.emerge", this.pos, 4, 0.8);
    for (let k = 0; k < 18; k++) {
      moveProp(e, add(this.pos, { x: 0, y: -2 + (11 * (k + 1)) / 18, z: 0 }));
      if (k % 3 === 0) deco(this.dim, "shard", this.pos, C.root, 6, 2.5, 0.35, 3);
      yield 1;
    }
    const spot = this.ground(lead(t, 20));
    teleCircle(this.dim, spot, 6, a.marks[0] - 18 + 18);
    yield a.marks[0] - 18;
    sound(this.dim, "mob.ravager.roar", this.pos, 3, 1.2);
    const T = 18;
    fire({
      dim: this.dim, pos: lift, vel: { x: (spot.x - lift.x) / T, y: (spot.y - lift.y) / T + 0.04 * T * 0.5, z: (spot.z - lift.z) / T },
      life: T + 3, radius: 0.1, dmg: 0, owner: this.entity, gravity: 0.04, entity: e, ground: true,
      trail: (s) => moveProp(e, s.pos),
      onEnd: () => {
        sound(this.dim, "random.explode", spot, 4, 0.6);
        shake(this.audience(), 0.7, 1.0);
        shock(this.dim, spot, 11, 12, C.root);
        deco(this.dim, "shard", add(spot, { x: 0, y: 1, z: 0 }), C.root, 24, 3, 0.45, 8);
        strike(this, spot, 8, (p) => inCircle(p, spot, 6, 5), this.dmg(24), { knock: 1.8, up: 0.8, from: spot });
      },
    });
    yield a.ticks - a.marks[0];
  }

  // ---------------------------------------------------------------- ultimate
  *ultimate(): Co {
    const center = this.ground(this.pos);
    const a = this.act("yawn");
    for (let k = 0; k < 24; k++) {
      this.place(add(center, { x: 0, y: (3 * (k + 1)) / 24, z: 0 }), this.yaw);
      yield 1;
    }
    sound(this.dim, "mob.evocation_illager.prepare_summon", center, 4, 0.6);
    yield a.marks[0] - 24;
    // stars pour out
    let tick = a.marks[0];
    let i = 0;
    while (tick < a.marks[1] - 8) {
      const tgt = this.fighters.length && i % 2 === 0 ? this.fighters[i % this.fighters.length].location
        : add(center, scale(dirOfYaw(randIn(0, 360)), randIn(2, 14)));
      const spot = this.ground(tgt);
      teleCircle(this.dim, spot, 2.2, 16);
      bullet(this.dim, add(spot, { x: 0, y: 14, z: 0 }), { x: 0, y: -1, z: 0 }, 17, 16, C.star, 0.8);
      const s = { ...spot };
      addTask("star", (age) => {
        if (age < 16) return true;
        glint(this.dim, add(s, { x: 0, y: 0.5, z: 0 }), C.star, 1.8);
        sound(this.dim, "random.orb", s, 1, 0.5);
        strike(this, s, 3.5, (p) => inCircle(p, s, 2.2), this.dmg(12), { cause: EntityDamageCause.magic, up: 0.3, from: s });
        return false;
      });
      i++;
      tick += 4;
      yield 4;
    }
    yield Math.max(1, a.marks[1] - tick);
    // two crescent blades sweep around him
    const moons = [spawnProp(this.dim, "crescent", center, 0, this.entity), spawnProp(this.dim, "crescent", center, 180, this.entity)];
    const sweepT = a.marks[2] - a.marks[1] - 24;
    let ang = randIn(0, 360);
    for (const off of [0, 180]) teleLine(this.dim, center, dirOfYaw(ang + off), 16, 1.6, 14);
    sound(this.dim, "beacon.activate", center, 4, 0.6);
    const lastHit = new Map<string, number>();
    for (let k = 0; k < sweepT; k++) {
      ang += 2.2;
      moons.forEach((m, j) => {
        const dir = dirOfYaw(ang + j * 180);
        moveProp(m, add(add(center, scale(dir, 9)), { x: 0, y: 1.5, z: 0 }), ang + j * 180 + 90);
        if (k % 3 === 0) bullet(this.dim, add(add(center, scale(dir, 3)), { x: 0, y: 1, z: 0 }), dir, 40, 7, C.moon, 0.5);
        if (k < 14) return;
        for (const p of fightersNear(this.dim, center, 18)) {
          const end = add(center, scale(dir, 16));
          const sd = flatSegDist(p.location, center, end);
          if (sd.d < 0.9 && sd.t * 16 > 2.5 && Math.abs(p.location.y - center.y) < 3 && (lastHit.get(p.id) ?? -99) < k - 10) {
            lastHit.set(p.id, k);
            hurt(p, this.dmg(10), this.entity, EntityDamageCause.magic);
            knock(p, center, 0.8, 0.3);
          }
        }
      });
      yield 1;
    }
    moons.forEach((m) => removeProp(m));
    // the Wind-Father's breath
    teleCircle(this.dim, center, 9, 24);
    sound(this.dim, "mob.breeze.inhale", center, 5, 0.5);
    for (let k = 0; k < 24; k++) {
      if (k > 14) for (const p of fightersNear(this.dim, center, 14)) knock(p, center, -0.3, 0);
      yield 1;
    }
    sound(this.dim, "breeze_wind_charge.burst", center, 5, 0.5);
    shake(this.audience(), 0.7, 1.0);
    shock(this.dim, center, 16, 14, C.wind);
    strike(this, center, 11, (p) => inCircle(p, center, 9, 6), this.dmg(26), { knock: 2.6, up: 0.8, from: center });
    yield Math.max(1, a.ticks - a.marks[2]);
    for (let k = 0; k < 10; k++) {
      this.place(add(this.pos, { x: 0, y: (center.y - this.pos.y) * 0.4, z: 0 }), this.yaw);
      yield 1;
    }
  }

  // ---------------------------------------------------------------- Vayu's breath (one revival chance)
  protected beforeDeath(): Co | undefined {
    if (this.revived) return undefined;
    this.revived = true;
    return this.vayu();
  }

  *vayu(): Co {
    this.invuln = true;
    this.fx(1);
    const c = this.act("collapse");
    sound(this.dim, "mob.breeze.death", this.pos, 4, 0.5);
    yield c.ticks;
    this.say("§bThe wind gathers… break the wisps!", Pri.Ultimate);
    const center = { ...this.pos };
    const wisps: (Entity | undefined)[] = [];
    for (let i = 0; i < 4; i++) wisps.push(spawnProp(this.dim, "wind_wisp", add(center, scale(dirOfYaw(i * 90), 6)), 0, this.entity));
    for (let k = 0; k < 170; k++) {
      wisps.forEach((w, i) => {
        if (!w || !w.isValid) return;
        const p = add(add(center, scale(dirOfYaw(i * 90 + k * 2.4), 6)), { x: 0, y: 1.2 + Math.sin((k + i * 20) * 0.15) * 0.6, z: 0 });
        moveProp(w, p);
        if (k % 5 === 0) bullet(this.dim, p, sub(add(center, { x: 0, y: 1, z: 0 }), p), 12, 8, C.wind, 0.35);
      });
      if (wisps.every((w) => !w || !w.isValid)) break;
      yield 1;
    }
    const alive = wisps.filter((w) => w && w.isValid);
    alive.forEach((w) => removeProp(w));
    if (!alive.length) {
      yield* this.deathCo();
      return;
    }
    // the wind revives him
    const r = this.act("revive");
    yield r.marks[0];
    setHealth(this.entity, this.maxHp * (0.12 + 0.06 * alive.length));
    this.wrath = 1.2;
    this.fx(2);
    flash(this.audience(), { red: 0.75, green: 1, blue: 0.9 });
    sound(this.dim, "mob.breeze.charge", this.pos, 5, 0.5);
    shock(this.dim, this.pos, 16, 12, C.wind);
    this.say("§c◆ Vayu's Breath — Hanuman rises!", Pri.Phase);
    yield r.ticks - r.marks[0];
    this.invuln = false;
    this.ultAt = this.t + 200;
  }
}
