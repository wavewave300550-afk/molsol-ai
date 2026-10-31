import { Dimension, Entity, EquipmentSlot, ItemStack, Player, Vector3, system, world } from "@minecraft/server";
import { burst, column, fade, flash, Hue, mote, shake, sound, sphereWave, title } from "./core/fx.js";
import { chest, healthOf, isCombatPlayer, lineOfSight, playersNear } from "./core/targets.js";
import { add, dist, v } from "./core/vec.js";

/**
 * Final-boss runtime shared by all five bosses. Each boss supplies its own moves, ultimate,
 * movement style and signature mechanic through hooks; the engine provides:
 *   - spawn intro / dormant state, three phases with forced ultimates on transitions
 *   - threat-based target selection and utility-scored move choice
 *   - movement modes (hover, walk on terrain) with an arena leash
 *   - invulnerability windows, exposed windows after ultimates, scripted death + loot
 */

export enum S {
  Idle = 0,
  Move = 1,
  AtkA = 2,
  AtkB = 3,
  AtkC = 4,
  Channel = 5,
  Ultimate = 6,
  Stagger = 7,
  Death = 8,
  Spawn = 9,
  Dormant = 10,
  Burrow = 11,
  AtkD = 12,
}

export interface Action {
  name: string;
  state: S;
  step(age: number): boolean;
  holdsPosition?: boolean;
  invulnerable?: boolean;
}

export interface MoveCtx {
  boss: Boss;
  target: Player;
  dim: Dimension;
  tick: number;
  distance: number;
}

export interface Move {
  id: string;
  name: string;
  cooldown: number;
  minPhase?: number;
  score(ctx: MoveCtx): number;
  start(ctx: MoveCtx): Action;
}

export interface Lines {
  intro: string[];
  phase2: string[];
  phase3: string[];
  ultimate: string[];
  kill: string[];
  taunt: string[];
  death: string[];
}

export interface BossDef {
  typeId: string;
  key: string;
  name: string;
  epithet: string;
  color: string;
  hue: Hue;
  fade: [number, number, number];
  speed: number;
  mode: "hover" | "walk";
  /** Height of the "eye" above the entity origin, used for line of sight and beams. */
  eyeHeight: number;
  spawnTicks: number;
  startsDormant?: boolean;
  hover(b: Boss, target: Player | undefined, tick: number): Vector3;
  moves: Move[];
  ultimate: Move;
  lines: Lines;
  loot: string;
  /** Signature damage rule (before-event, restricted mode: no world edits). */
  incoming?(b: Boss, amount: number, cause: string, attacker: Entity | undefined): number;
  damaged?(b: Boss, amount: number, attacker: Entity | undefined): void;
  mechanic?(b: Boss, tick: number): void;
  hudInfo?(b: Boss): string;
  ambient?(b: Boss, tick: number): void;
  deathFx?(b: Boss, age: number): void;
  onAwaken?(b: Boss): void;
}

const bosses = new Map<string, Boss>();
const DEFS = new Map<string, BossDef>();
const pick = <T>(a: T[]): T => a[Math.floor(Math.random() * a.length)];

export function registerDef(d: BossDef): void {
  DEFS.set(d.typeId, d);
}
export const defFor = (typeId: string) => DEFS.get(typeId);
export const allBosses = () => [...bosses.values()];
export const bossOf = (e: Entity) => bosses.get(e.id);

export class Boss {
  readonly entity: Entity;
  readonly def: BossDef;
  home: Vector3;
  phase = 1;
  threat = new Map<string, number>();
  cooldowns = new Map<string, number>();
  action?: Action;
  actionAge = 0;
  ultCharge = 0;
  pendingUltimate = false;
  exhaustedUntil = 0;
  shiftUntil = 0;
  spawnUntil = 0;
  nextDecision = 0;
  targetId?: string;
  losLost = 0;
  dormant = false;
  dying = false;
  deathAge = 0;
  lonely = 0;
  lastSpeech = -1000;
  lastTaunt = -1000;
  lastPos: Vector3;
  memo: Record<string, number> = {};
  private stateCache = -1;

  constructor(entity: Entity, def: BossDef, home: Vector3) {
    this.entity = entity;
    this.def = def;
    this.home = home;
    this.lastPos = { ...entity.location };
  }

  get dim(): Dimension {
    return this.entity.dimension;
  }
  get hpFrac(): number {
    const h = healthOf(this.entity);
    return h ? h.currentValue / h.effectiveMax : 1;
  }
  get eye(): Vector3 {
    return add(this.entity.location, v(0, this.def.eyeHeight, 0));
  }
  get target(): Player | undefined {
    if (!this.targetId) return undefined;
    const p = world.getEntity(this.targetId);
    return p instanceof Player && isCombatPlayer(p) && p.dimension.id === this.dim.id ? p : undefined;
  }

  say(text: string, force = false): void {
    const t = system.currentTick;
    if (!force && t - this.lastSpeech < 60) return;
    this.lastSpeech = t;
    for (const p of this.dim.getPlayers({ location: this.entity.location, maxDistance: 72 })) {
      p.sendMessage(`${this.def.color}§l${this.def.name}§r§7: ${text.replace(/\{name\}/g, p.name)}`);
    }
  }

  setState(s: S): void {
    if (s === this.stateCache) return;
    this.stateCache = s;
    try {
      this.entity.setProperty("fb:state", s);
    } catch {
      // visuals only
    }
  }

  setPhaseProperty(): void {
    try {
      this.entity.setProperty("fb:phase", this.phase);
    } catch {
      // ignore
    }
  }

  ready(id: string, t: number): boolean {
    return (this.cooldowns.get(id) ?? 0) <= t;
  }

  groundBelow(at: Vector3): Vector3 {
    try {
      const hit = this.dim.getBlockFromRay(add(at, v(0, 2, 0)), { x: 0, y: -1, z: 0 }, { maxDistance: 40, includeLiquidBlocks: true });
      if (hit) return { x: at.x, y: hit.block.location.y + 1, z: at.z };
    } catch {
      // outside world
    }
    return at;
  }

  /** Smooth teleport towards `to`, keeping the body level while facing `look`. */
  glide(to: Vector3, look: Vector3 | undefined, maxStep: number): void {
    const cur = this.entity.location;
    const d = dist(cur, to);
    const k = d > maxStep ? maxStep / d : 1;
    const next = { x: cur.x + (to.x - cur.x) * k, y: cur.y + (to.y - cur.y) * k, z: cur.z + (to.z - cur.z) * k };
    const face = look ? { x: look.x, y: next.y + this.def.eyeHeight, z: look.z } : undefined;
    try {
      this.entity.teleport(next, face ? { facingLocation: face } : undefined);
    } catch {
      // chunk unloaded
    }
  }

  blink(to: Vector3, look?: Vector3): void {
    burst(this.dim, this.def.hue, add(this.entity.location, v(0, 2, 0)));
    sound(this.dim, "mob.endermen.portal", this.entity.location, 1.5, 0.5);
    try {
      this.entity.teleport(to, look ? { facingLocation: { x: look.x, y: to.y + this.def.eyeHeight, z: look.z } } : undefined);
    } catch {
      // ignore
    }
    burst(this.dim, this.def.hue, add(to, v(0, 2, 0)));
  }

  // ------------------------------------------------------------------ main loop
  tick(t: number): void {
    if (this.dying) return this.tickDeath();
    const here = this.entity.location;
    const players = playersNear(this.dim, here, 64);
    this.def.ambient?.(this, t);

    if (this.dormant) {
      this.setState(S.Dormant);
      if (playersNear(this.dim, here, 9).length) this.awaken();
      return;
    }
    if (this.spawnUntil > t) {
      this.setState(S.Spawn);
      return;
    }
    if (!players.length) {
      this.action = undefined;
      this.setState(S.Idle);
      if (++this.lonely > 1600) this.depart();
      return;
    }
    this.lonely = 0;
    this.updatePhase(t);
    if (t % 20 === 0 || !this.target) this.chooseTarget(players, t);
    const target = this.target;
    if (!target) return;
    this.losLost = lineOfSight(this.dim, this.eye, add(target.location, v(0, 1.5, 0))) ? 0 : this.losLost + 1;
    this.ultCharge = Math.min(100, this.ultCharge + (this.phase === 3 ? 0.05 : 0.03));
    try {
      this.def.mechanic?.(this, t);
    } catch (e) {
      console.warn(`[fb] ${this.def.key} mechanic failed: ${e}`);
    }

    if (this.action) {
      this.setState(this.action.state);
      let keep = false;
      try {
        keep = this.action.step(this.actionAge++);
      } catch (e) {
        console.warn(`[fb] ${this.def.key}/${this.action.name} failed: ${e}`);
      }
      if (this.action && !this.action.holdsPosition) this.drift(target, t, false);
      if (!keep) {
        this.action = undefined;
        this.nextDecision = t + (this.phase === 3 ? 14 : this.phase === 2 ? 22 : 30);
      }
      return;
    }
    if (this.shiftUntil > t) {
      this.setState(S.Channel);
      return;
    }
    if (this.exhaustedUntil > t) {
      this.setState(S.Stagger);
      if (this.def.mode === "hover") this.glide(add(this.groundBelow(here), v(0, 0.4, 0)), chest(target), 0.3);
      if (t % 8 === 0) mote(this.dim, "white", add(here, v(Math.random() * 3 - 1.5, 3 + Math.random() * 2, Math.random() * 3 - 1.5)));
      return;
    }
    const moved = this.drift(target, t, true);
    this.setState(moved ? S.Move : S.Idle);
    if (t >= this.nextDecision) this.decide(target, t);
  }

  /** Returns true when the boss actually travelled this tick. */
  private drift(target: Player, t: number, allowMove: boolean): boolean {
    if (!allowMove) return false;
    let want = this.def.hover(this, target, t);
    const off = Math.hypot(want.x - this.home.x, want.z - this.home.z);
    if (off > 32) {
      const k = 32 / off;
      want = { x: this.home.x + (want.x - this.home.x) * k, y: want.y, z: this.home.z + (want.z - this.home.z) * k };
    }
    if (this.def.mode === "walk") want = this.groundBelow(want);
    const before = this.entity.location;
    this.glide(want, target.location, this.def.speed * (this.phase === 3 ? 1.3 : 1));
    const after = this.entity.location;
    return Math.hypot(after.x - before.x, after.z - before.z) > 0.03;
  }

  private decide(target: Player, t: number): void {
    const ctx: MoveCtx = { boss: this, target, dim: this.dim, tick: t, distance: dist(this.entity.location, target.location) };
    if (this.pendingUltimate || (this.ultCharge >= 100 && this.ready(this.def.ultimate.id, t))) {
      this.pendingUltimate = false;
      this.ultCharge = 0;
      this.say(pick(this.def.lines.ultimate), true);
      return this.begin(this.def.ultimate, ctx);
    }
    let best: Move | undefined;
    let bestScore = 0;
    for (const m of this.def.moves) {
      if ((m.minPhase ?? 1) > this.phase || !this.ready(m.id, t)) continue;
      const s = m.score(ctx) * (0.85 + Math.random() * 0.3);
      if (s > bestScore) {
        bestScore = s;
        best = m;
      }
    }
    if (best) this.begin(best, ctx);
    else this.nextDecision = t + 10;
  }

  begin(m: Move, ctx: MoveCtx): void {
    this.cooldowns.set(m.id, ctx.tick + Math.round(m.cooldown * (this.phase === 3 ? 0.72 : 1)));
    this.action = m.start(ctx);
    this.actionAge = 0;
    this.setState(this.action.state);
  }

  private chooseTarget(players: Player[], t: number): void {
    const here = this.entity.location;
    let best: Player | undefined;
    let bestScore = -Infinity;
    for (const p of players) {
      let s = (this.threat.get(p.id) ?? 0) + (64 - dist(p.location, here)) * 1.5;
      if (this.phase === 3) {
        const h = healthOf(p);
        if (h) s += (1 - h.currentValue / h.effectiveMax) * 40;
      }
      if (p.id === this.targetId) s *= 1.25;
      if (s > bestScore) {
        bestScore = s;
        best = p;
      }
    }
    if (best && best.id !== this.targetId) {
      this.targetId = best.id;
      if (t - this.lastTaunt > 400) {
        this.lastTaunt = t;
        const held = best.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Mainhand);
        const weapon = held ? held.typeId.split(":")[1].replace(/_/g, " ") : "bare hands";
        this.say(pick(this.def.lines.taunt).replace(/\{weapon\}/g, weapon).replace(/\{name\}/g, best.name), true);
      }
    }
    for (const [k, val] of this.threat) this.threat.set(k, val * 0.97);
  }

  private updatePhase(t: number): void {
    const f = this.hpFrac;
    const want = f <= 0.33 ? 3 : f <= 0.66 ? 2 : 1;
    if (want <= this.phase) return;
    this.phase = want;
    this.setPhaseProperty();
    this.pendingUltimate = true;
    if (this.action?.state !== S.Ultimate) {
      this.shiftUntil = t + 45;
      this.action = undefined;
    }
    this.say(pick(want === 2 ? this.def.lines.phase2 : this.def.lines.phase3), true);
    const at = add(this.entity.location, v(0, this.def.eyeHeight, 0));
    sphereWave(this.dim, this.def.hue, at);
    sphereWave(this.dim, "white", at);
    sound(this.dim, "mob.wither.spawn", at, 1.2, 1.3);
    for (const p of playersNear(this.dim, at, 56)) {
      title(p, `${this.def.color}§l${want === 2 ? "PHASE II" : "FINAL PHASE"}`, `§7${this.def.name} ${want === 2 ? "grows stronger" : "unleashes its true power"}`, 40);
      shake(p, 0.25, 1.5);
    }
  }

  awaken(): void {
    if (!this.dormant) return;
    this.dormant = false;
    this.spawnUntil = system.currentTick + this.def.spawnTicks;
    try {
      this.entity.triggerEvent("fb:awaken");
    } catch {
      // ignore
    }
    try {
      this.entity.setDynamicProperty("fb:awake", true);
    } catch {
      // ignore
    }
    this.def.onAwaken?.(this);
    this.say(pick(this.def.lines.intro), true);
    for (const p of playersNear(this.dim, this.entity.location, 56)) {
      title(p, `${this.def.color}§l${this.def.name.toUpperCase()}`, `§7${this.def.epithet}`, 60);
      shake(p, 0.4, 2.5);
    }
  }

  // ------------------------------------------------------------------ damage (called from events)
  incoming(amount: number, cause: string, attacker: Entity | undefined): number {
    const t = system.currentTick;
    if (this.dying || this.spawnUntil > t || this.shiftUntil > t || this.action?.invulnerable) return 0;
    if (this.dormant) {
      this.memo.wakeHit = 1;
      return 0;
    }
    let dmg = this.def.incoming ? this.def.incoming(this, amount, cause, attacker) : amount;
    if (this.exhaustedUntil > t) dmg *= 1.5;
    const h = healthOf(this.entity);
    if (h && dmg >= h.currentValue) {
      this.dying = true;
      this.deathAge = 0;
      return 0;
    }
    return dmg;
  }

  damaged(amount: number, attacker: Entity | undefined): void {
    this.ultCharge = Math.min(100, this.ultCharge + amount * 0.12);
    if (attacker instanceof Player) this.threat.set(attacker.id, (this.threat.get(attacker.id) ?? 0) + amount);
    this.def.damaged?.(this, amount, attacker);
  }

  // ------------------------------------------------------------------ endings
  private tickDeath(): void {
    const age = this.deathAge++;
    this.setState(S.Death);
    this.action = undefined;
    const at = add(this.entity.location, v(0, this.def.eyeHeight, 0));
    if (age === 0) {
      this.say(pick(this.def.lines.death), true);
      sound(this.dim, "mob.enderdragon.death", at, 1, 1.2);
      for (const p of playersNear(this.dim, at, 72)) shake(p, 0.35, 5);
    }
    this.def.deathFx?.(this, age);
    if (age % 7 === 0) {
      burst(this.dim, this.def.hue, add(at, v(Math.random() * 6 - 3, Math.random() * 4 - 2, Math.random() * 6 - 3)));
      column(this.dim, this.def.hue, add(this.entity.location, v(Math.random() * 10 - 5, 0, Math.random() * 10 - 5)));
    }
    if (age === 100) this.finishDeath();
  }

  private finishDeath(): void {
    const at = add(this.entity.location, v(0, this.def.eyeHeight, 0));
    const dim = this.dim;
    flash(dim, at);
    sphereWave(dim, this.def.hue, at);
    sphereWave(dim, "white", at);
    sound(dim, "random.explode", at, 2, 0.6);
    sound(dim, "random.totem", at, 1.5, 0.8);
    for (const p of playersNear(dim, at, 72)) {
      fade(p, this.def.fade, 0.1, 0.4, 1.4);
      title(p, `${this.def.color}§l${this.def.name.toUpperCase()}`, "§7has fallen", 80);
    }
    try {
      dim.spawnItem(new ItemStack(this.def.loot, 1), add(this.entity.location, v(0, 1, 0)));
      for (let i = 0; i < 30; i++) dim.spawnEntity("minecraft:xp_orb", add(this.entity.location, v(Math.random() * 4 - 2, 1 + Math.random() * 2, Math.random() * 4 - 2)));
    } catch (e) {
      console.warn(`[fb] loot failed: ${e}`);
    }
    bosses.delete(this.entity.id);
    try {
      this.entity.remove();
    } catch {
      // gone
    }
  }

  depart(): void {
    this.say("No challengers remain. I withdraw.", true);
    flash(this.dim, add(this.entity.location, v(0, 2, 0)));
    bosses.delete(this.entity.id);
    try {
      this.entity.remove();
    } catch {
      // ignore
    }
  }

  onKill(p: Player): void {
    this.say(pick(this.def.lines.kill).replace(/\{name\}/g, p.name), true);
    this.threat.delete(p.id);
    if (this.targetId === p.id) this.targetId = undefined;
  }
}

export function adopt(e: Entity, intro: boolean): Boss | undefined {
  const def = DEFS.get(e.typeId);
  if (!def) return undefined;
  if (bosses.has(e.id)) return bosses.get(e.id);
  const saved = e.getDynamicProperty("fb:home");
  const home = typeof saved === "object" && saved ? (saved as Vector3) : { ...e.location };
  e.setDynamicProperty("fb:home", home);
  const b = new Boss(e, def, home);
  const f = b.hpFrac;
  b.phase = f <= 0.33 ? 3 : f <= 0.66 ? 2 : 1;
  b.setPhaseProperty();
  bosses.set(e.id, b);
  if (def.startsDormant && e.getDynamicProperty("fb:awake") !== true) {
    b.dormant = true;
    b.setState(S.Dormant);
    return b;
  }
  if (intro) {
    b.spawnUntil = system.currentTick + def.spawnTicks;
    b.setState(S.Spawn);
    b.say(pick(def.lines.intro), true);
  }
  return b;
}

export function tickBosses(t: number): void {
  for (const b of [...bosses.values()]) {
    if (!b.entity.isValid) {
      bosses.delete(b.entity.id);
      continue;
    }
    if (b.dormant && b.memo.wakeHit) {
      b.memo.wakeHit = 0;
      b.awaken();
    }
    try {
      b.tick(t);
    } catch (e) {
      console.warn(`[fb] ${b.def.key} tick failed: ${e}`);
    }
  }
}

export function hud(t: number): void {
  for (const b of bosses.values()) {
    if (!b.entity.isValid || b.dying || b.dormant) continue;
    const roman = ["", "I", "II", "III"][b.phase];
    const gauge = Math.round(b.ultCharge / 10);
    const extra = b.def.hudInfo?.(b) ?? "";
    const state = b.exhaustedUntil > t ? " §e§lEXPOSED" : b.action?.state === S.Ultimate ? " §c§lULTIMATE" : "";
    const text = `${b.def.color}§l${b.def.name}§r §8| §7Phase §f${roman}${extra ? ` §8| ${extra}` : ""} §8| §7Ultimate ${b.def.color}${"|".repeat(gauge)}§8${"|".repeat(10 - gauge)}${state}`;
    for (const p of b.dim.getPlayers({ location: b.entity.location, maxDistance: 56 })) p.onScreenDisplay.setActionBar(text);
  }
}
