/**
 * ALICORN — Dawnstar Sovereign.
 *
 * Identity: speed and colour-coded magic. The horn's glow announces what is
 * coming, with no text: RED = ground strike (get off the marked ground),
 * BLUE = projectiles (keep moving sideways), GOLD = charge (sidestep the line).
 *
 *   I   Celestial Steed     triple charge, rear-and-stomp + jumpable ring,
 *                           homing star lances, feather gust
 *   II  Wings of Aurora     takes to the sky: aurora curtain (find the gap),
 *                           comet dive, prism barrier (break the crystals),
 *                           moonlit healing (interrupt it!)
 *   III Dawnstar Ascendant  star crown: hyper-dashes, rainbow spiral
 *   ULT Dawnbreak Nova — golden sigils appear; when the star breaks, only
 *                           those standing inside a sigil are spared.
 */
import { Entity, EntityDamageCause, Player, Vector3 } from "@minecraft/server";
import { ALICORN_ACTS } from "../generated/data.js";
import { grounded, hurt, inCircle, inRingBand } from "../core/combat.js";
import { beam, bullet, burst, C, Col, deco, flash, glint, pillar, shake, shock, sound, teleCircle, teleCone, teleLine, teleSafe, mote } from "../core/fx.js";
import { fire, spawnProp } from "../core/hazards.js";
import { add, dirOfYaw, dist, flatDir, flatDist, norm, randIn, rotY, scale, sub, yawOf } from "../core/vec.js";
import { Co, SkillDef } from "./being.js";
import { Boss } from "./boss.js";
import { ahead, lead, strike } from "./kit.js";

const A = ALICORN_ACTS;
const HUE = { none: 0, red: 1, blue: 2, gold: 3 } as const;
const RAINBOW: Col[] = [C.pink, C.aurora, C.sky, { red: 0.6, green: 1, blue: 0.75 }, C.safe];

export class Alicorn extends Boss {
  readonly acts = A;
  readonly walkSpeed = 0.3;
  readonly title = "Alicorn";
  readonly ultName = "Dawnbreak Nova";
  readonly phaseNames = ["", "", "Wings of Aurora", "Dawnstar Ascendant"];
  readonly thresholds = [0.66, 0.33];
  readonly defeatText = "§e✦ The Dawnstar dims… and yields";
  readonly ultPhase = 3;
  readonly ultCooldown = 1000;
  readonly sigil = "legends:sigil_alicorn";
  prisms: Entity[] = [];
  channelDmg = 0;

  constructor(e: Entity) {
    super(e, "alicorn");
  }

  protected onInit(): void {
    if (this.phase >= 2) this.wings(true);
  }

  wings(on: boolean): void {
    this.flying = on;
    this.prop("fly", on ? 1 : 0);
  }

  hue(h: number): void {
    this.prop("var", h);
  }

  horn(): Vector3 {
    return ahead(this, 5.2, 5.5);
  }

  idle(): void {
    const t = this.target;
    if (this.leashed() || !t) {
      if (this.flying) this.fly({ x: this.home.x, y: this.ground(this.home).y + 6, z: this.home.z }, 0.35);
      else this.walk(this.home, this.walkSpeed, 2);
      return;
    }
    if (this.flying) {
      const g = this.ground(t.location).y;
      const p = add(t.location, scale(dirOfYaw(this.t * 1.6), 10));
      this.fly({ x: p.x, y: g + 6, z: p.z }, 0.34, 0, 10);
      if (this.t % 24 === 0) sound(this.dim, "mob.enderdragon.flap", this.pos, 1.5, 1.4);
    } else {
      const d = flatDist(this.pos, t.location);
      if (d > 9) this.walk(t.location, this.walkSpeed, 8);
      else this.walk(add(t.location, scale(rotY(flatDir(t.location, this.pos), 30), 9)), this.walkSpeed * 0.7, 0.3);
    }
  }

  onDamaged(amount: number, by?: Player): void {
    super.onDamaged(amount, by);
    this.channelDmg += amount;
  }

  protected onTick(): void {
    this.prisms = this.prisms.filter((p) => p.isValid);
    if (this.prisms.length) {
      this.takenMul = 0.2;
      if (this.t % 5 === 0) for (const p of this.prisms) beam(this.dim, add(p.location, { x: 0, y: 2, z: 0 }), add(this.pos, { x: 0, y: 2.5, z: 0 }), C.aurora, 0.4);
    } else if (this.takenMul === 0.2) {
      this.takenMul = 1;
      shock(this.dim, this.pos, 6, 8, C.aurora);
      sound(this.dim, "random.glass", this.pos, 3, 0.7);
    }
    if (this.phase >= 3 && this.t % 8 === 0) mote(this.dim, add(this.pos, { x: randIn(-2, 2), y: randIn(2, 5), z: randIn(-2, 2) }), C.star, 0.3, 0.8);
    if (this.flying && this.t % 10 === 0) deco(this.dim, "feather", add(this.pos, { x: 0, y: 2, z: 0 }), C.white, 1, 2, 0.3, 0.2);
  }

  // ---------------------------------------------------------------- entrance / transitions
  *entrance(): Co {
    const g = this.ground(this.pos);
    pillar(this.dim, g, 30, 3, 60, C.aurora);
    const a = this.act("descend");
    this.wings(true);
    for (let k = 0; k < a.ticks; k++) {
      const s = Math.min(1, k / a.marks[0]);
      this.place(add(g, { x: 0, y: 26 * (1 - s) ** 2, z: 0 }), this.yaw);
      if (k % 4 === 0) deco(this.dim, "feather", this.pos, C.white, 3, 1.5, 0.35, 0.4);
      if (k === a.marks[0]) {
        sound(this.dim, "beacon.activate", g, 4, 1.2);
        shock(this.dim, g, 12, 12, C.aurora);
        this.wings(false);
      }
      yield 1;
    }
    this.endAct();
    this.say("§dThe Dawnstar Alicorn descends", 0);
  }

  *transition(to: number): Co {
    if (to === 2) {
      const a = this.act("takeoff");
      this.hue(HUE.none);
      sound(this.dim, "beacon.power", this.pos, 4, 1.4);
      yield a.marks[0];
      this.wings(true);
      this.setPhase(2);
      const g = this.ground(this.pos).y;
      for (let k = 0; k < 30; k++) {
        this.place({ x: this.pos.x, y: this.pos.y + (g + 6 - this.pos.y) * 0.12, z: this.pos.z });
        if (k % 4 === 0) pillar(this.dim, { x: this.pos.x, y: g, z: this.pos.z }, 10, 1.4, 12, RAINBOW[k % 5]);
        yield 1;
      }
      this.endAct();
      return;
    }
    const a = this.act("curtain");
    yield a.marks[0];
    this.setPhase(3);
    sound(this.dim, "beacon.activate", this.pos, 5, 1.6);
    flash(this.audience(), C.holy);
    shock(this.dim, this.ground(this.pos), 18, 14, C.safe);
    burst(this.dim, add(this.pos, { x: 0, y: 4, z: 0 }), C.star, 40, 8, 0.4, 2);
    yield a.ticks - a.marks[0];
  }

  // ---------------------------------------------------------------- skills
  skills(): SkillDef[] {
    return [
      { name: "charge", phases: [1], cd: 160, weight: 4, min: 5, run: (t) => this.charge(t, 3) },
      { name: "stomp", phases: [1], cd: 140, weight: 3, max: 9, run: () => this.stomp() },
      { name: "lance", phases: [1, 2, 3], cd: 170, weight: 3, min: 4, run: () => this.lances(5) },
      { name: "gust", phases: [1, 2], cd: 130, weight: 3, max: 15, run: (t) => this.gust(t) },
      { name: "curtain", phases: [2, 3], cd: 320, weight: 3, run: (t) => this.curtain(t) },
      { name: "comet", phases: [2, 3], cd: 120, weight: 4, run: (t) => this.comet(t) },
      { name: "prism", phases: [2, 3], cd: 900, weight: 3, when: () => this.prisms.length === 0, run: () => this.prism() },
      { name: "heal", phases: [2, 3], cd: 700, weight: 2, when: () => this.hp < this.maxHp * 0.62, run: () => this.heal() },
      { name: "hyper", phases: [3], cd: 260, weight: 3, run: (t) => this.hyper(t) },
      { name: "spiral", phases: [3], cd: 240, weight: 3, run: () => this.spiral() },
    ];
  }

  *land(): Co {
    if (!this.flying) return;
    const g = this.ground(this.pos);
    const a = this.act("land");
    for (let k = 0; k < 14; k++) {
      this.place({ x: this.pos.x, y: this.pos.y + (g.y - this.pos.y) * 0.3, z: this.pos.z });
      yield 1;
    }
    this.wings(false);
    yield Math.max(1, a.ticks - 14);
  }

  *rise(h = 6): Co {
    if (this.flying) return;
    const a = this.act("takeoff");
    yield a.marks[0];
    this.wings(true);
    const g = this.ground(this.pos).y;
    for (let k = 0; k < 16; k++) {
      this.place({ x: this.pos.x, y: this.pos.y + (g + h - this.pos.y) * 0.2, z: this.pos.z });
      yield 1;
    }
  }

  *charge(t: Player, n: number): Co {
    this.hue(HUE.gold);
    for (let i = 0; i < n && t.isValid; i++) {
      this.faceNow(t.location);
      const dir = flatDir(this.pos, t.location);
      const len = Math.min(26, flatDist(this.pos, t.location) + 8);
      teleLine(this.dim, this.ground(this.pos), dir, len, 3, 16);
      sound(this.dim, "mob.horse.angry", this.pos, 3, 0.7);
      glint(this.dim, this.horn(), C.gold, 1.6);
      yield 16;
      this.act("charge");
      const dest = add(this.pos, scale(dir, len));
      const hit = new Set<string>();
      yield* this.dash(dest, 1.1, () => {
        if (this.t % 2 === 0) mote(this.dim, add(this.pos, { x: 0, y: 2, z: 0 }), C.gold, 0.5, 0.5);
        strike(this, this.pos, 5, (p) => flatDist(p.location, this.pos) < 2.6, 16, { knock: 1.6, up: 0.5, once: hit });
      });
      this.endAct();
      yield 6;
    }
    this.hue(HUE.none);
  }

  *stomp(): Co {
    this.hue(HUE.red);
    const a = this.act("stomp");
    const c = this.ground(ahead(this, 2));
    teleCircle(this.dim, c, 6, a.marks[0]);
    sound(this.dim, "mob.horse.angry", this.pos, 3, 0.6);
    yield a.marks[0];
    sound(this.dim, "random.anvil_land", c, 3, 0.6);
    shake(this.audience(), 0.35, 0.5);
    strike(this, c, 7, (p) => inCircle(p, c, 6), 17, { knock: 1.2, up: 0.6, from: c });
    shock(this.dim, c, 14, 10, C.aurora);
    const hit = new Set<string>();
    for (let k = 1; k <= 10; k++) {
      const r = 5 + k * 0.9;
      strike(this, c, r + 2, (p) => grounded(p) && inRingBand(p, c, r - 0.9, r + 0.4, 2), 11, { up: 0.5, from: c, once: hit });
      yield 1;
    }
    this.hue(HUE.none);
    yield Math.max(1, a.ticks - a.marks[0] - 10);
  }

  *lances(n: number): Co {
    this.hue(HUE.blue);
    const a = this.act("lance");
    glint(this.dim, this.horn(), C.sky, 2);
    sound(this.dim, "beacon.power", this.pos, 2, 1.8);
    yield a.marks[0];
    const tgts = this.fighters.length ? this.fighters : [];
    for (let i = 0; i < n; i++) {
      const tg = tgts.length ? tgts[i % tgts.length] : undefined;
      const from = this.horn();
      const d0 = rotY(dirOfYaw(this.yaw), -50 + (100 * i) / Math.max(1, n - 1));
      const e = spawnProp(this.dim, "star_lance", from, yawOf(d0), this.entity);
      fire({
        dim: this.dim, pos: from, vel: scale({ x: d0.x, y: 0.15, z: d0.z }, 0.55), life: 60, radius: 0.8, dmg: 10, owner: this.entity,
        entity: e, homing: tg ? { target: tg, turn: 0.09, until: 40 } : undefined, cause: EntityDamageCause.magic,
        trail: (s) => {
          if ((s.age ?? 0) % 2 === 0) mote(this.dim, s.pos, C.sky, 0.3, 0.4);
        },
        onEnd: (s) => burst(this.dim, s.pos, C.sky, 10, 3),
      });
      yield 3;
    }
    yield Math.max(1, a.ticks - a.marks[0] - n * 3);
    this.hue(HUE.none);
  }

  *gust(t: Player): Co {
    this.hue(HUE.blue);
    this.faceNow(t.location);
    const a = this.act("wing_gust");
    teleCone(this.dim, this.ground(this.pos), dirOfYaw(this.yaw), 70, 15, a.marks[0], C.warn);
    yield a.marks[0];
    sound(this.dim, "mob.enderdragon.flap", this.pos, 3, 1.3);
    for (let w = 0; w < 2; w++) {
      for (let i = 0; i < 9; i++) {
        const d = rotY(dirOfYaw(this.yaw), -35 + i * 8.75 + (w ? 4 : 0));
        const from = add(this.pos, { x: 0, y: this.flying ? 1.5 : 2.2, z: 0 });
        const dd = this.flying ? norm({ x: d.x, y: -0.35, z: d.z }) : d;
        bullet(this.dim, from, dd, 14, 22, C.white, 0.4);
        fire({ dim: this.dim, pos: from, vel: scale(dd, 0.7), life: 22, radius: 0.7, dmg: 7, owner: this.entity });
      }
      yield 6;
    }
    this.hue(HUE.none);
    yield Math.max(1, a.ticks - a.marks[0] - 12);
  }

  *curtain(t: Player): Co {
    this.hue(HUE.red);
    const center = this.ground(t.location);
    const travel = flatDir(this.pos, t.location);
    const across = rotY(travel, 90);
    const a = this.act("curtain");
    const half = 20;
    const gapAt = randIn(-12, 12);
    const gap = 2.6;
    const start = add(center, scale(travel, -16));
    sound(this.dim, "beacon.activate", center, 4, 0.8);
    const showWall = (base: Vector3, ticks: number): void => {
      for (let s = -half; s <= half; s += 1.6) {
        const p = add(base, scale(across, s));
        if (Math.abs(s - gapAt) < gap) teleCircle(this.dim, p, 0.6, ticks, C.safe);
        else teleCircle(this.dim, p, 0.45, ticks);
      }
    };
    showWall(start, 24);
    yield Math.max(1, a.marks[0]);
    const lastHit = new Map<string, number>();
    const T = 76;
    for (let k = 0; k < T; k++) {
      const base = add(start, scale(travel, (32 * k) / T));
      if (k % 4 === 0) {
        for (let s = -half; s <= half; s += 2.2) {
          if (Math.abs(s - gapAt) < gap) continue;
          pillar(this.dim, this.ground(add(base, scale(across, s))), 5, 0.9, 6, RAINBOW[(Math.round(s) + 40) % 5]);
        }
      }
      for (const p of this.fighters) {
        const rel = sub(p.location, base);
        const along = rel.x * travel.x + rel.z * travel.z;
        const side = rel.x * across.x + rel.z * across.z;
        if (Math.abs(along) < 0.9 && Math.abs(side) <= half && Math.abs(side - gapAt) >= gap && (lastHit.get(p.id) ?? -99) < k - 15) {
          lastHit.set(p.id, k);
          hurt(p, 16, this.entity, EntityDamageCause.magic);
        }
      }
      yield 1;
    }
    this.hue(HUE.none);
    yield Math.max(1, a.ticks - a.marks[0] - T);
  }

  *comet(t: Player): Co {
    this.hue(HUE.gold);
    yield* this.rise(8);
    const g = this.ground(t.location);
    const high = { x: this.pos.x, y: g.y + 12, z: this.pos.z };
    for (let k = 0; k < 16 && dist(this.pos, high) > 1; k++) {
      this.fly(high, 0.6, 0, 30);
      yield 1;
    }
    const spot = this.ground(lead(t, 12));
    const a = this.act("comet");
    teleCircle(this.dim, spot, 4.5, a.marks[0]);
    this.faceNow(spot);
    yield a.marks[0] - 8;
    const from = { ...this.pos };
    for (let k = 1; k <= 8; k++) {
      this.place(add(from, scale(sub(add(spot, { x: 0, y: 0.5, z: 0 }), from), k / 8)), this.yaw, 40);
      deco(this.dim, "feather", this.pos, C.gold, 2, 0.5, 0.3, 0.4);
      yield 1;
    }
    sound(this.dim, "random.explode", spot, 3, 1.2);
    shake(this.audience(), 0.45, 0.6);
    shock(this.dim, spot, 9, 10, C.gold);
    burst(this.dim, spot, C.star, 24, 6, 0.35, 0.6);
    strike(this, spot, 6, (p) => inCircle(p, spot, 4.5, 5), 22, { knock: 1.6, up: 0.6, from: spot });
    this.place(this.pos, this.yaw, 0);
    this.hue(HUE.none);
    yield a.ticks - a.marks[0];
  }

  *prism(): Co {
    const a = this.act("barrier");
    sound(this.dim, "chime.amethyst_block", this.pos, 4, 0.6);
    yield a.marks[0];
    const c = this.ground(this.home);
    const base = randIn(0, 360);
    for (let i = 0; i < 3; i++) {
      const p = this.ground(add(c, scale(dirOfYaw(base + i * 120), 12)));
      const e = spawnProp(this.dim, "prism", add(p, { x: 0, y: 0.5, z: 0 }), 0, this.entity);
      if (e) this.prisms.push(e);
      pillar(this.dim, p, 12, 1.5, 20, C.aurora);
    }
    yield a.ticks - a.marks[0];
  }

  *heal(): Co {
    yield* this.land();
    const a = this.act("heal");
    this.channelDmg = 0;
    const limit = 50 + 25 * this.maxFighters;
    sound(this.dim, "beacon.ambient", this.pos, 4, 1.2);
    for (let k = 0; k < a.ticks; k++) {
      if (k % 10 === 0) {
        const h = this.entity.getComponent("minecraft:health");
        if (h) h.setCurrentValue(Math.min(h.effectiveMax, this.gateCap(h.currentValue + this.maxHp * 0.007)));
        deco(this.dim, "rune", add(this.pos, { x: 0, y: 0.5, z: 0 }), C.sky, 4, 2.5, 0.35, 0.8);
      }
      if (this.channelDmg >= limit) {
        // interrupted: staggered and vulnerable
        sound(this.dim, "random.glass", this.pos, 3, 0.6);
        burst(this.dim, add(this.pos, { x: 0, y: 3, z: 0 }), C.sky, 30, 6, 0.4, 1);
        this.fx(3);
        this.takenMul = 1.4;
        this.act("land");
        yield 50;
        this.takenMul = 1;
        this.fx(0);
        break;
      }
      yield 1;
    }
    yield* this.rise(6);
  }

  /** Healing never lifts the boss above the HP of the phase it is in. */
  gateCap(v: number): number {
    const ceil = this.phase >= 2 && this.phase - 2 < this.thresholds.length ? this.maxHp * this.thresholds[this.phase - 2] : this.maxHp;
    return Math.min(v, ceil);
  }

  *hyper(t: Player): Co {
    this.hue(HUE.gold);
    for (let i = 0; i < 5 && t.isValid; i++) {
      const c = this.ground(t.location);
      const dir = dirOfYaw(randIn(0, 360));
      const start = add(c, scale(dir, -15));
      const end = add(c, scale(dir, 15));
      teleLine(this.dim, this.ground(start), dir, 30, 3, 14);
      yield 6;
      deco(this.dim, "feather", this.pos, C.gold, 6, 1, 0.3, 1);
      this.place({ x: start.x, y: c.y + 1.5, z: start.z }, yawOf(dir));
      yield 8;
      this.act("hyper");
      const hit = new Set<string>();
      for (let k = 0; k < 24 && flatDist(this.pos, end) > 1; k++) {
        this.fly({ x: end.x, y: c.y + 1.5, z: end.z }, 1.4, 0, 90);
        if (k % 2 === 0) bullet(this.dim, this.pos, flatDir(end, start), 4, 10, RAINBOW[k % 5], 0.6);
        strike(this, this.pos, 5, (p) => flatDist(p.location, this.pos) < 2.4, 16, { knock: 1.4, up: 0.5, once: hit });
        yield 1;
      }
    }
    this.endAct();
    this.hue(HUE.none);
  }

  *spiral(): Co {
    this.hue(HUE.blue);
    const a = this.act("spiral");
    yield a.marks[0];
    sound(this.dim, "beacon.power", this.pos, 3, 1.5);
    const total = a.ticks - a.marks[0] - 6;
    for (let k = 0; k < total; k += 2) {
      for (let arm = 0; arm < 4; arm++) {
        const yaw = k * 6 + arm * 90;
        const from = this.flying ? add(this.pos, { x: 0, y: 1, z: 0 }) : add(this.pos, { x: 0, y: 1.6, z: 0 });
        const d = this.flying ? norm({ ...dirOfYaw(yaw), y: -0.18 }) : dirOfYaw(yaw);
        const col = RAINBOW[(arm + Math.floor(k / 6)) % 5];
        bullet(this.dim, from, d, 9, 40, col, 0.5);
        fire({ dim: this.dim, pos: from, vel: scale(d, 0.45), life: 40, radius: 0.75, dmg: 6, owner: this.entity, cause: EntityDamageCause.magic });
      }
      yield 2;
    }
    this.hue(HUE.none);
    yield 6;
  }

  // ---------------------------------------------------------------- ultimate
  *ultimate(): Co {
    const center = this.ground(this.home);
    yield* this.rise(6);
    const top = { x: center.x, y: center.y + 12, z: center.z };
    for (let k = 0; k < 30 && dist(this.pos, top) > 0.5; k++) {
      this.fly(top, 0.5, 0, 30);
      yield 1;
    }
    this.hue(HUE.gold);
    const a = this.act("nova");
    sound(this.dim, "beacon.activate", center, 6, 0.5);
    yield a.marks[0];
    const n = Math.max(3, Math.min(6, this.fighters.length + 2));
    const sigils: Vector3[] = [];
    const base = randIn(0, 360);
    for (let i = 0; i < n; i++) sigils.push(this.ground(add(center, scale(dirOfYaw(base + (i * 360) / n), randIn(6, 14)))));
    const life = a.marks[1] - a.marks[0];
    for (const s of sigils) {
      teleSafe(this.dim, s, 2.6, life);
      pillar(this.dim, s, 10, 1.2, 30, C.safe);
    }
    sound(this.dim, "chime.amethyst_block", center, 5, 0.8);
    for (let k = 0; k < life; k++) {
      if (k % 3 === 0) {
        const p = add(center, scale(dirOfYaw(randIn(0, 360)), randIn(0, 18)));
        const from = { x: p.x, y: center.y + 16, z: p.z };
        bullet(this.dim, from, { x: 0, y: -1, z: 0 }, 12, 26, RAINBOW[k % 5], 0.45);
        fire({ dim: this.dim, pos: from, vel: { x: 0, y: -0.6, z: 0 }, life: 26, radius: 0.8, dmg: 5, owner: this.entity, cause: EntityDamageCause.magic });
      }
      if (k === life - 40) teleCircle(this.dim, center, 24, 40);
      if (k % 30 === 0) for (const s of sigils) pillar(this.dim, s, 10, 1.2, 30, C.safe);
      if (k > life - 40 && k % 4 === 0) glint(this.dim, this.horn(), C.white, 3 + (k - life + 40) * 0.1);
      yield 1;
    }
    sound(this.dim, "random.explode", center, 6, 1.5);
    sound(this.dim, "beacon.deactivate", center, 6, 0.6);
    flash(this.audience(), C.white);
    shake(this.audience(), 0.7, 1.0);
    shock(this.dim, center, 28, 16, C.safe);
    for (const p of this.fighters) {
      const safe = sigils.some((s) => flatDist(s, p.location) <= 2.7);
      if (safe) {
        glint(this.dim, add(p.location, { x: 0, y: 1, z: 0 }), C.safe, 1.2);
        continue;
      }
      hurt(p, 50, this.entity);
      hurt(p, 15, this.entity, EntityDamageCause.magic);
    }
    this.hue(HUE.none);
    yield a.ticks - a.marks[1];
  }
}
