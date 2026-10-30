import { Dimension, Entity, EntityDamageCause, EquipmentSlot, ItemStack, Player, Vector3, system, world } from "@minecraft/server";
import { burst, column, fade, flash, Hue, mote, shake, sound, sphereWave, title } from "./core/fx.js";
import { chest, healthOf, isCombatPlayer, lineOfSight, playersNear } from "./core/targets.js";
import { add, dist, v } from "./core/vec.js";

/**
 * The "mind" shared by every Intelligent Being:
 *   - threat table and deliberate target selection
 *   - three combat phases with a phase-shift (brief invulnerability + forced ultimate)
 *   - adaptive defence: learns which damage type the players rely on and resists it
 *   - utility-scored move selection (distance, crowding, line of sight, phase, cooldowns)
 *   - anti-cheese reactions (hiding, pillaring, fleeing the arena)
 *   - scripted death sequence, loot, and dialogue
 */

export enum AnimState {
  Idle = 0,
  Cast = 1,
  Channel = 2,
  Ultimate = 3,
  Stagger = 4,
  Dying = 5,
  Shift = 6,
}

export type DamageKind = "melee" | "projectile" | "arcane";
export const KIND_LABEL: Record<DamageKind, string> = { melee: "BLADES", projectile: "ARROWS", arcane: "SORCERY" };

export interface Action {
  name: string;
  state: AnimState;
  /** Return false when the action has finished. */
  step(age: number): boolean;
  /** While true the being does not drift towards its hover point. */
  holdsPosition?: boolean;
}

export interface MoveCtx {
  being: Being;
  target: Player;
  dim: Dimension;
  tick: number;
  distance: number;
}

export interface Move {
  id: string;
  name: string;
  /** Cooldown in ticks. */
  cooldown: number;
  minPhase?: number;
  /** Utility score; 0 means "not now". */
  score(ctx: MoveCtx): number;
  start(ctx: MoveCtx): Action;
}

export interface Dialogue {
  intro: string[];
  phase2: string[];
  phase3: string[];
  adapt: Record<DamageKind, string>;
  ultimate: string[];
  kill: string[];
  taunt: string[];
  hide: string[];
  death: string[];
}

export interface BeingDef {
  typeId: string;
  name: string;
  epithet: string;
  /** Formatting code used for chat / HUD. */
  color: string;
  hue: Hue;
  fade: [number, number, number];
  /** Max drift speed (blocks per tick). */
  speed: number;
  hover(b: Being, target: Player | undefined, tick: number): Vector3;
  moves: Move[];
  ultimate: Move;
  lines: Dialogue;
  loot: string;
  ambient?(b: Being, tick: number): void;
  deathFx?(b: Being, age: number): void;
}

const beings = new Map<string, Being>();
const DEFS = new Map<string, BeingDef>();

export function registerDef(def: BeingDef): void {
  DEFS.set(def.typeId, def);
}

export function defFor(typeId: string): BeingDef | undefined {
  return DEFS.get(typeId);
}

export function allBeings(): Being[] {
  return [...beings.values()];
}

export function beingOf(e: Entity): Being | undefined {
  return beings.get(e.id);
}

const pick = <T>(arr: T[]): T => arr[Math.floor(Math.random() * arr.length)];

interface Snapshot {
  tick: number;
  pos: Vector3;
  dimId: string;
  hp: number;
}

export class Being {
  readonly entity: Entity;
  readonly def: BeingDef;
  home: Vector3;
  phase = 1;
  threat = new Map<string, number>();
  damageLog: { tick: number; kind: DamageKind; amount: number }[] = [];
  adapted?: { kind: DamageKind; until: number };
  cooldowns = new Map<string, number>();
  action?: Action;
  actionAge = 0;
  ultCharge = 0;
  pendingUltimate = false;
  exhaustedUntil = 0;
  shiftUntil = 0;
  nextDecision = 0;
  targetId?: string;
  losLost = 0;
  dying = false;
  deathAge = 0;
  lonely = 0;
  lastSpeech = -1000;
  lastTargetCall = -1000;
  history = new Map<string, Snapshot[]>();
  selfHistory: { tick: number; hp: number }[] = [];
  private stateCache = -1;
  /** Free-form scratch space for being-specific mechanics. */
  memo: Record<string, number> = {};

  constructor(entity: Entity, def: BeingDef, home: Vector3) {
    this.entity = entity;
    this.def = def;
    this.home = home;
  }

  get dim(): Dimension {
    return this.entity.dimension;
  }

  get hpFrac(): number {
    const h = healthOf(this.entity);
    return h ? h.currentValue / h.effectiveMax : 1;
  }

  get target(): Player | undefined {
    if (!this.targetId) return undefined;
    const p = world.getEntity(this.targetId);
    return p instanceof Player && isCombatPlayer(p) && p.dimension.id === this.dim.id ? p : undefined;
  }

  get eye(): Vector3 {
    return add(this.entity.location, v(0, 2.6, 0));
  }

  /** Message every player within range, prefixed with the being's name. */
  say(text: string, force = false): void {
    const t = system.currentTick;
    if (!force && t - this.lastSpeech < 60) return;
    this.lastSpeech = t;
    for (const p of this.dim.getPlayers({ location: this.entity.location, maxDistance: 64 })) {
      p.sendMessage(`${this.def.color}§l<${this.def.name}>§r §7${text.replace(/\{name\}/g, p.name)}`);
    }
  }

  setState(s: AnimState): void {
    if (s === this.stateCache) return;
    this.stateCache = s;
    try {
      this.entity.setProperty("dim11:state", s);
    } catch {
      // property missing (old pack) - visuals only
    }
  }

  setPhaseProperty(): void {
    try {
      this.entity.setProperty("dim11:phase", this.phase);
    } catch {
      // ignore
    }
  }

  ready(moveId: string, tick: number): boolean {
    return (this.cooldowns.get(moveId) ?? 0) <= tick;
  }

  /** Teleport smoothly towards `to` while looking at `look`. */
  glide(to: Vector3, look: Vector3 | undefined, maxStep: number): void {
    const cur = this.entity.location;
    const d = dist(cur, to);
    const k = d > maxStep ? maxStep / d : 1;
    const next = { x: cur.x + (to.x - cur.x) * k, y: cur.y + (to.y - cur.y) * k, z: cur.z + (to.z - cur.z) * k };
    try {
      this.entity.teleport(next, look ? { facingLocation: look } : undefined);
    } catch {
      // chunk not loaded
    }
  }

  groundBelow(at: Vector3): Vector3 {
    try {
      const hit = this.dim.getBlockFromRay(add(at, v(0, 0.5, 0)), { x: 0, y: -1, z: 0 }, { maxDistance: 32 });
      if (hit) return { x: at.x, y: hit.block.location.y + 1, z: at.z };
    } catch {
      // outside world
    }
    return at;
  }

  blink(to: Vector3, look?: Vector3): void {
    burst(this.dim, this.def.hue, add(this.entity.location, v(0, 2, 0)));
    sound(this.dim, "mob.endermen.portal", this.entity.location, 1.5, 0.6);
    try {
      this.entity.teleport(to, look ? { facingLocation: look } : undefined);
    } catch {
      // ignore
    }
    burst(this.dim, this.def.hue, add(to, v(0, 2, 0)));
  }

  // ------------------------------------------------------------------ main loop

  tick(t: number): void {
    if (this.dying) return this.tickDeath();
    const here = this.entity.location;
    const players = playersNear(this.dim, here, 56);
    this.def.ambient?.(this, t);

    if (!players.length) {
      this.lonely++;
      this.action = undefined;
      this.setState(AnimState.Idle);
      this.glide(add(this.home, v(0, 5 + Math.sin(t * 0.03), 0)), undefined, this.def.speed * 0.5);
      if (this.lonely > 1200) this.depart();
      return;
    }
    this.lonely = 0;
    if (t % 20 === 0) this.record(players, t);
    this.updatePhase(t);
    if (t % 20 === 0 || !this.target) this.chooseTarget(players, t);
    const target = this.target;
    if (!target) return;

    this.losLost = lineOfSight(this.dim, this.eye, add(target.location, v(0, 1.5, 0))) ? 0 : this.losLost + 1;
    if (this.losLost === 120) this.say(pick(this.def.lines.hide));
    this.ultCharge = Math.min(100, this.ultCharge + (this.phase === 3 ? 0.05 : 0.03));
    if (this.adapted && this.adapted.until <= t) {
      this.say(`My adaptation to ${KIND_LABEL[this.adapted.kind].toLowerCase()} fades. Try again.`, true);
      this.adapted = undefined;
    }

    if (this.action) {
      this.setState(this.action.state);
      let keep = false;
      try {
        keep = this.action.step(this.actionAge++);
      } catch (e) {
        console.warn(`[dim11] ${this.def.name}/${this.action.name} failed: ${e}`);
      }
      if (!this.action?.holdsPosition) this.drift(target, t);
      if (!keep) {
        this.action = undefined;
        this.nextDecision = t + (this.phase === 3 ? 12 : this.phase === 2 ? 20 : 28);
      }
      return;
    }

    if (this.shiftUntil > t) {
      this.setState(AnimState.Shift);
      this.drift(target, t);
      return;
    }
    if (this.exhaustedUntil > t) {
      // exposed: the being sinks to the ground where blades can reach it
      this.setState(AnimState.Stagger);
      this.glide(add(this.groundBelow(here), v(0, 0.3, 0)), chest(target), 0.3);
      if (t % 10 === 0) mote(this.dim, "white", add(here, v(Math.random() * 2 - 1, 3 + Math.random(), Math.random() * 2 - 1)));
      return;
    }
    this.setState(AnimState.Idle);
    this.drift(target, t);
    if (t < this.nextDecision) return;
    this.decide(target, t);
  }

  private drift(target: Player, t: number): void {
    let want = this.def.hover(this, target, t);
    // leash: never wander more than 30 blocks from the place it manifested
    const off = dist({ ...want, y: this.home.y }, this.home);
    if (off > 30) {
      const k = 30 / off;
      want = { x: this.home.x + (want.x - this.home.x) * k, y: want.y, z: this.home.z + (want.z - this.home.z) * k };
    }
    this.glide(want, chest(target), this.def.speed * (this.phase === 3 ? 1.35 : 1));
  }

  private decide(target: Player, t: number): void {
    const ctx: MoveCtx = { being: this, target, dim: this.dim, tick: t, distance: dist(this.entity.location, target.location) };
    // a phase transition always earns an ultimate; a full gauge only when off cooldown
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

  begin(move: Move, ctx: MoveCtx): void {
    this.cooldowns.set(move.id, ctx.tick + Math.round(move.cooldown * (this.phase === 3 ? 0.7 : 1)));
    this.action = move.start(ctx);
    this.actionAge = 0;
    this.setState(this.action.state);
  }

  private chooseTarget(players: Player[], t: number): void {
    const here = this.entity.location;
    let best: Player | undefined;
    let bestScore = -Infinity;
    for (const p of players) {
      const d = dist(p.location, here);
      let s = (this.threat.get(p.id) ?? 0) * 1.0 + (48 - d) * 1.5;
      if (this.phase === 3) {
        const h = healthOf(p);
        if (h) s += (1 - h.currentValue / h.effectiveMax) * 40; // finish the wounded
      }
      if (p.id === this.targetId) s *= 1.25; // commitment: avoid erratic switching
      if (s > bestScore) {
        bestScore = s;
        best = p;
      }
    }
    if (best && best.id !== this.targetId) {
      this.targetId = best.id;
      if (t - this.lastTargetCall > 300) {
        this.lastTargetCall = t;
        const held = best.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Mainhand);
        const weapon = held ? held.typeId.split(":")[1].replace(/_/g, " ") : "bare hands";
        this.say(pick(this.def.lines.taunt).replace(/\{weapon\}/g, weapon).replace(/\{name\}/g, best.name), true);
      }
    }
    // threat decays so the fight stays dynamic
    for (const [k, val] of this.threat) this.threat.set(k, val * 0.97);
  }

  private record(players: Player[], t: number): void {
    for (const p of players) {
      const h = healthOf(p);
      const list = this.history.get(p.id) ?? [];
      list.push({ tick: t, pos: { ...p.location }, dimId: p.dimension.id, hp: h ? h.currentValue : 20 });
      while (list.length > 12) list.shift();
      this.history.set(p.id, list);
    }
    const own = healthOf(this.entity);
    if (own) {
      this.selfHistory.push({ tick: t, hp: own.currentValue });
      while (this.selfHistory.length > 12) this.selfHistory.shift();
    }
  }

  private updatePhase(t: number): void {
    const f = this.hpFrac;
    const want = f <= 0.33 ? 3 : f <= 0.66 ? 2 : 1;
    if (want <= this.phase) return;
    this.phase = want;
    this.setPhaseProperty();
    this.pendingUltimate = true;
    // never cut an ultimate short; otherwise shift phase with a brief invulnerable flourish
    if (this.action?.state !== AnimState.Ultimate) {
      this.shiftUntil = t + 50;
      this.action = undefined;
    }
    this.say(pick(want === 2 ? this.def.lines.phase2 : this.def.lines.phase3), true);
    const at = add(this.entity.location, v(0, 2.5, 0));
    sphereWave(this.dim, this.def.hue, at);
    sphereWave(this.dim, "white", at);
    sound(this.dim, "mob.wither.spawn", at, 1.2, 1.4);
    for (const p of playersNear(this.dim, at, 48)) {
      title(p, `${this.def.color}§l${want === 2 ? "PHASE II" : "TRUE FORM"}`, `§7${this.def.name} ascends further into the 11th dimension`, 40);
      shake(p, 0.25, 1.5);
    }
  }

  // ------------------------------------------------------------------ damage intake (called from events)

  classify(cause: string): DamageKind {
    if (cause === EntityDamageCause.entityAttack || cause === EntityDamageCause.maceSmash) return "melee";
    if (cause === EntityDamageCause.projectile) return "projectile";
    return "arcane";
  }

  /** Before-event: returns the modified damage (0 cancels). Runs in restricted mode: no world edits here. */
  incoming(amount: number, cause: string): number {
    const t = system.currentTick;
    if (this.dying || this.shiftUntil > t) return 0;
    let dmg = amount;
    const kind = this.classify(cause);
    if (this.adapted && this.adapted.kind === kind) dmg *= 0.35;
    if (this.exhaustedUntil > t) dmg *= 1.5;
    const h = healthOf(this.entity);
    if (h && dmg >= h.currentValue) {
      this.dying = true;
      this.deathAge = 0;
      return 0;
    }
    return dmg;
  }

  /** After-event bookkeeping: threat, ultimate charge, adaptation learning. */
  damaged(amount: number, cause: string, by: Entity | undefined): void {
    const t = system.currentTick;
    const kind = this.classify(cause);
    this.damageLog.push({ tick: t, kind, amount });
    this.damageLog = this.damageLog.filter((d) => t - d.tick < 400);
    this.ultCharge = Math.min(100, this.ultCharge + amount * 0.12);
    if (by instanceof Player) this.threat.set(by.id, (this.threat.get(by.id) ?? 0) + amount);
    if (this.adapted) return;
    const total = this.damageLog.reduce((s, d) => s + d.amount, 0);
    const mine = this.damageLog.filter((d) => d.kind === kind).reduce((s, d) => s + d.amount, 0);
    if (total >= 45 && mine / total >= 0.65) {
      this.adapted = { kind, until: t + 600 };
      this.damageLog = [];
      this.say(this.def.lines.adapt[kind], true);
      const at = add(this.entity.location, v(0, 2.5, 0));
      sphereWave(this.dim, "white", at);
      sound(this.dim, "mob.elderguardian.curse", at, 1, 1.6);
    }
  }

  // ------------------------------------------------------------------ endings

  private tickDeath(): void {
    const age = this.deathAge++;
    this.setState(AnimState.Dying);
    this.action = undefined;
    const at = add(this.entity.location, v(0, 2.5, 0));
    if (age === 0) {
      this.say(pick(this.def.lines.death), true);
      sound(this.dim, "mob.enderdragon.death", at, 1, 1.3);
      for (const p of playersNear(this.dim, at, 64)) shake(p, 0.35, 4);
    }
    this.def.deathFx?.(this, age);
    if (age % 6 === 0) {
      burst(this.dim, this.def.hue, add(at, v(Math.random() * 6 - 3, Math.random() * 4 - 1, Math.random() * 6 - 3)));
      column(this.dim, this.def.hue, add(this.entity.location, v(Math.random() * 8 - 4, 0, Math.random() * 8 - 4)));
    }
    if (age === 90) this.finishDeath();
  }

  private finishDeath(): void {
    const at = add(this.entity.location, v(0, 2.5, 0));
    const dim = this.dim;
    flash(dim, at);
    sphereWave(dim, this.def.hue, at);
    sphereWave(dim, "white", at);
    sound(dim, "random.explode", at, 2, 0.6);
    sound(dim, "random.totem", at, 1.5, 0.8);
    for (const p of playersNear(dim, at, 64)) {
      fade(p, this.def.fade, 0.1, 0.4, 1.2);
      title(p, `${this.def.color}§l${this.def.name.toUpperCase()}`, "§7has been unmade - the eleventh dimension closes", 70);
    }
    try {
      dim.spawnItem(new ItemStack(this.def.loot, 1), add(this.entity.location, v(0, 1, 0)));
      for (let i = 0; i < 24; i++) dim.spawnEntity("minecraft:xp_orb", add(this.entity.location, v(Math.random() * 4 - 2, 1 + Math.random() * 2, Math.random() * 4 - 2)));
    } catch (e) {
      console.warn(`[dim11] loot failed: ${e}`);
    }
    beings.delete(this.entity.id);
    try {
      this.entity.remove();
    } catch {
      // already gone
    }
  }

  depart(): void {
    this.say("No observers remain. I return to the folded dark.", true);
    flash(this.dim, add(this.entity.location, v(0, 2, 0)));
    beings.delete(this.entity.id);
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

/** Register (or re-register after a reload) a being entity. */
export function adopt(e: Entity): Being | undefined {
  const def = DEFS.get(e.typeId);
  if (!def || beings.has(e.id)) return beings.get(e.id);
  const saved = e.getDynamicProperty("dim11:home");
  const home = typeof saved === "object" && saved ? (saved as Vector3) : { ...e.location };
  e.setDynamicProperty("dim11:home", home);
  const b = new Being(e, def, home);
  const f = b.hpFrac;
  b.phase = f <= 0.33 ? 3 : f <= 0.66 ? 2 : 1;
  b.setPhaseProperty();
  b.setState(AnimState.Idle);
  beings.set(e.id, b);
  return b;
}

export function forget(id: string): void {
  beings.delete(id);
}

export function tickBeings(t: number): void {
  for (const b of [...beings.values()]) {
    if (!b.entity.isValid) {
      beings.delete(b.entity.id);
      continue;
    }
    try {
      b.tick(t);
    } catch (e) {
      console.warn(`[dim11] ${b.def.name} tick failed: ${e}`);
    }
  }
}

/** Boss HUD for nearby players: phase, adaptation and the ultimate gauge. */
export function hud(t: number): void {
  for (const b of beings.values()) {
    if (!b.entity.isValid || b.dying) continue;
    const roman = ["", "I", "II", "III"][b.phase];
    const gauge = Math.round(b.ultCharge / 10);
    const adapt = b.adapted ? `§cresists ${KIND_LABEL[b.adapted.kind]}` : "§8no adaptation";
    const state = b.exhaustedUntil > t ? " §e§lEXPOSED" : b.shiftUntil > t ? " §f§lSHIFTING" : "";
    const text = `${b.def.color}§l${b.def.name}§r §8| §7Phase §f${roman} §8| ${adapt} §8| §7Ultimate ${b.def.color}${"|".repeat(gauge)}§8${"|".repeat(10 - gauge)}${state}`;
    for (const p of b.dim.getPlayers({ location: b.entity.location, maxDistance: 48 })) p.onScreenDisplay.setActionBar(text);
  }
}
