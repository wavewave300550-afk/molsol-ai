// Gharvok, the Cliffbreaker - the boss brain.
//
// AI states: IDLE, ALERT, PURSUE, REPOSITION, ATTACK_WINDUP, ATTACK_ACTIVE, RECOVERY, STAGGERED, AIRBORNE,
// LANDING, RESET, DEAD.  Outside a fight the vanilla stroll AI moves it; in a fight the script owns movement
// (ground-snapped steps with obstacle probes) so charges, leaps and dives follow exact, testable paths.
import { EntityDamageCause, ItemStack } from "@minecraft/server";
import { CONFIG, GHARVOK_ID, REWARD_ID, hpFor } from "./config.js";
import { ANIM, FLIGHT, GAIT } from "./timings.js";
import { ATTACKS, BY_NAME, MOVES, diveSpot, skyClear } from "./moves.js";
import { playersNear, validTarget, viewersNear } from "../../core/combat.js";
import { actionbar, message, particle, sound, title } from "../../core/fx.js";
import { blockAt, groundAt, isSolid, probeFront } from "../../core/terrain.js";
import { clamp, now, rand, safe, sec, weighted } from "../../core/util.js";
import { angleDiff, dirOf, distXZ, local, relAngle, turnToward, yawTo } from "../../core/vec.js";

const NS = "dragon_dominion";
const C = CONFIG;
const DP = { home: `${NS}:home`, fight: `${NS}:fight`, tier: `${NS}:tier`, phase: `${NS}:phase`, skull: `${NS}:skull`,
  skullPts: `${NS}:skull_pts`, dying: `${NS}:dying` };
const MAJOR = new Set(["crushing_charge", "cliff_dive", "skullbreaker", "charge_impact"]);

export class Gharvok {
  constructor(entity) {
    this.typeId = GHARVOK_ID;
    this.e = entity;
    this.id = entity.id;
    this.dim = entity.dimension;
    this.yaw = safe(() => entity.getRotation().y, 0);
    this.state = "IDLE";
    this.stateSince = now();
    this.move = undefined;
    this.queued = [];
    this.cool = {};
    this.history = [];
    this.target = undefined;
    this.lostSince = undefined;
    this.nextDecision = now() + sec(1);
    this.nextRetarget = 0;
    this.nextScan = 0;
    this.nextIdleAct = now() + sec(rand(...C.idle.actEvery));
    this.aggro = new Map(); // player id -> damage dealt this fight
    this.dmgByPlayers = 0;
    this.props = {};
    this.inAir = false;
    this.flightCode = 0;
    this.scripted = false;
    this.lastProgress = { t: now(), p: this.pos() };
    this.deathAt = undefined;
    this.disposed = false;
    // persisted fight state (survives chunk unloads / world reloads)
    const home = safe(() => entity.getDynamicProperty(DP.home));
    this.home = home ? JSON.parse(home) : { ...this.pos() };
    if (!home) safe(() => entity.setDynamicProperty(DP.home, JSON.stringify(this.home)));
    this.fight = !!safe(() => entity.getDynamicProperty(DP.fight));
    this.tier = safe(() => entity.getDynamicProperty(DP.tier)) ?? 1;
    this.phase = safe(() => entity.getDynamicProperty(DP.phase)) ?? 1;
    this.skull = safe(() => entity.getDynamicProperty(DP.skull)) ?? 0;
    this.skullPts = safe(() => entity.getDynamicProperty(DP.skullPts)) ?? 0;
    this.prop("phase", this.phase);
    this.prop("skull", this.skull);
    this.prop("anim", 0);
    this.prop("flight", 0);
    this.prop("gait", 0);
    if (safe(() => entity.getDynamicProperty(DP.dying))) {
      // it was mid-death when its chunk unloaded: finish the defeat now
      this.state = "DEAD";
      this.deathAt = now() - sec(10);
      this.legit = true;
    } else if (this.fight) {
      this.toScripted();
      this.setState("PURSUE");
    } else {
      this.event("to_roam");
      this.event("to_ground");
    }
  }

  // ---------------------------------------------------------------------------------------------- plumbing
  isValid() {
    return !this.disposed && safe(() => this.e.isValid, false);
  }
  dispose() {
    this.disposed = true;
  }
  pos() {
    return safe(() => ({ ...this.e.location }), this.lastPos ?? { x: 0, y: 0, z: 0 });
  }
  event(name) {
    safe(() => this.e.triggerEvent(`${NS}:${name}`));
  }
  prop(key, value) {
    if (this.props[key] === value) return;
    this.props[key] = value;
    safe(() => this.e.setProperty(`${NS}:${key}`, value));
  }
  anim(name) {
    this.prop("anim", ANIM[name] ?? 0);
  }
  flight(code) {
    this.flightCode = code;
    this.prop("flight", code);
  }
  gait(code) {
    this.prop("gait", code);
  }
  setState(s) {
    if (this.state === s) return;
    this.state = s;
    this.stateSince = now();
  }
  save(key, v) {
    safe(() => this.e.setDynamicProperty(DP[key], v));
  }
  health() {
    return safe(() => this.e.getComponent("minecraft:health"));
  }
  hpRatio() {
    const h = this.health();
    return h ? h.currentValue / Math.max(1, h.effectiveMax) : 1;
  }
  viewers(r = 48) {
    return viewersNear(this.dim, this.pos(), r);
  }
  players(r) {
    return playersNear(this.dim, this.pos(), r);
  }
  headPoint() {
    return local(this.pos(), this.yaw, C.geometry.headForward, 0, C.geometry.headHeight);
  }
  mouth() {
    return local(this.pos(), this.yaw, C.geometry.mouthForward, 0, C.geometry.headHeight - 0.6);
  }
  toScripted() {
    if (this.scripted) return;
    this.scripted = true;
    this.event("to_scripted");
  }
  toRoam() {
    if (!this.scripted) return;
    this.scripted = false;
    this.event("to_roam");
    this.gait(0);
  }
  toAir() {
    this.inAir = true;
    this.airSince = now();
    this.event("to_air");
  }
  toGround() {
    this.inAir = false;
    this.event("to_ground");
  }
  cooldown(name, seconds) {
    this.cool[name] = now() + sec(seconds * C.phases.cooldownScale[this.phase - 1]);
  }
  ready(name) {
    return now() >= (this.cool[name] ?? 0);
  }

  // ---------------------------------------------------------------------------------------------- motion
  /** Turn the body toward a point by at most `rate` degrees this tick. */
  face(point, rate) {
    if (!point) return;
    const want = yawTo(this.pos(), point);
    this.yaw = turnToward(this.yaw, want, rate);
    safe(() => this.e.setRotation({ x: 0, y: this.yaw }));
  }
  /** Place the body (used while airborne). */
  place(p) {
    this.lastPos = p;
    safe(() => this.e.teleport(p, { rotation: { x: 0, y: this.yaw }, keepVelocity: false }));
  }
  /**
   * Walk `dist` blocks along `yaw`, snapping to the ground. Never passes through solid blocks or off cliffs.
   * Returns { moved, blocked, hard, drop }.
   */
  step(dist, yaw, opts = {}) {
    const o = this.pos();
    if (dist <= 0) return { moved: 0, blocked: false, hard: false, drop: false };
    const f = dirOf(yaw);
    const nx = o.x + f.x * dist;
    const nz = o.z + f.z * dist;
    // the body front must have room (2 blocks ahead of the centre, at body heights 1..3)
    const wall = probeFront(this.dim, o, yaw, C.geometry.bodyRadius + 0.6, 3, 3, 1);
    if (wall.solid >= 3) return { moved: 0, blocked: true, hard: wall.hard >= 3, drop: false };
    const g = groundAt(this.dim, nx, nz, o.y, 1, opts.maxDrop ?? 3);
    if (g === undefined) return { moved: 0, blocked: false, hard: false, drop: true }; // ledge, water, unloaded
    if (g - o.y > 1.1) return { moved: 0, blocked: true, hard: false, drop: false };
    this.place({ x: nx, y: g + (opts.hop ?? 0), z: nz });
    return { moved: dist, blocked: false, hard: false, drop: false };
  }
  /** Snap to the ground under the current position. */
  settle() {
    const o = this.pos();
    const g = groundAt(this.dim, o.x, o.z, o.y, 2, 8);
    if (g !== undefined && Math.abs(g - o.y) > 0.01) this.place({ x: o.x, y: g, z: o.z });
  }
  /** Walk toward a point (pursuit / reset), running when far away. Returns the step result. */
  approach(point, run) {
    const speed = (run ? C.phases.runSpeed[this.phase - 1] : C.phases.walkSpeed) / 20;
    this.face(point, C.phases.turnRate[this.phase - 1]);
    const off = Math.abs(angleDiff(this.yaw, yawTo(this.pos(), point)));
    if (off > 60) {
      this.gait(0); // turn on the spot first (turn animation plays from the body rotation)
      return { moved: 0 };
    }
    this.gait(run ? GAIT.run : GAIT.walk);
    return this.step(speed * (off > 30 ? 0.5 : 1), this.yaw, { maxDrop: 2 });
  }

  // ---------------------------------------------------------------------------------------------- moves
  startMove(name, args) {
    const mv = BY_NAME[name];
    if (!mv) return;
    this.endMove(true);
    this.move = { mv, t: 0, args };
    this.gait(0);
    mv.start(this, this.move);
    if (ATTACKS.includes(name)) {
      this.history.push(name);
      if (this.history.length > 3) this.history.shift();
    }
  }
  endMove(interrupted) {
    const m = this.move;
    if (!m) return;
    this.move = undefined;
    safe(() => m.mv.end?.(this, m, interrupted));
    this.anim("none");
    this.gait(0);
  }
  /** Reactions (stagger, fracture) run after the current move; interruptible moves are cut short. */
  queueReaction(name) {
    if (this.state === "DEAD") return;
    if (this.move && this.move.mv.name === name) return;
    if (this.move && !this.move.mv.interruptible) {
      if (!this.queued.includes(name)) this.queued.push(name);
      return;
    }
    if (this.move) this.endMove(true);
    this.startMove(name);
  }
  majorAttackDone() {
    // exhaustion: phase III and a damaged crown make the big attacks costly
    const chance = Math.max(C.skull.exhaustAfterMajor[this.skull], this.phase >= 3 ? 0.5 : 0);
    if (Math.random() < chance && !this.queued.includes("exhausted")) this.queued.push("exhausted");
  }
  /** Is the head currently a vulnerable target (stunned, exhausted, recovering from a slam)? */
  vulnerable() {
    const m = this.move;
    if (!m) return false;
    if (m.mv.vulnerableAll) return true;
    return !!m.mv.vulnerable?.(m);
  }

  // ---------------------------------------------------------------------------------------------- skull fracture
  addSkull(points, why) {
    if (this.skull >= 2 || points <= 0) return;
    this.skullPts += points;
    this.save("skullPts", this.skullPts);
    const next = this.skullPts >= C.skull.broken ? 2 : this.skullPts >= C.skull.cracked ? 1 : 0;
    if (next > this.skull) {
      this.skull = next;
      this.prop("skull", next);
      this.save("skull", next);
      const viewers = this.viewers(48);
      actionbar(viewers, next === 1 ? "§6Gharvok's crownshield CRACKS!" : "§cGharvok's crownshield BREAKS - its skull is exposed!");
      if (why !== "wall") this.queueReaction("skull_fracture");
      else this.queued.push("skull_fracture");
    }
  }
  /** Approximate head-hit test: Bedrock gives no per-bone hit data, so we use attacker position vs. the head. */
  isHeadHit(source) {
    const atk = source?.damagingProjectile ?? source?.damagingEntity;
    const l = safe(() => atk?.location);
    if (!l) return false;
    const o = this.pos();
    if (Math.abs(relAngle(o, this.yaw, l)) > C.skull.headHalfAngle) return false;
    const head = this.headPoint();
    const low = this.vulnerable(); // head is lowered / on the ground in these windows
    const hy = low ? o.y + 1.2 : head.y;
    const dxz = distXZ(head, l);
    if (source.damagingProjectile) return dxz <= 2.4 && Math.abs(l.y - hy) <= 2.2;
    return dxz <= C.skull.headRange && l.y + 1.6 >= hy - 2.6;
  }

  // ---------------------------------------------------------------------------------------------- damage events
  onBeforeHurt(ev) {
    const cause = ev.damageSource.cause;
    // commands / void must still be able to remove it (no reward is given for those)
    if (cause === EntityDamageCause.selfDestruct || cause === EntityDamageCause.override || cause === "void") return;
    if (this.state === "DEAD" || this.state === "RESET" || this.deathAt !== undefined) {
      ev.cancel = true;
      return;
    }
    const atk = ev.damageSource.damagingEntity;
    const byPlayer = safe(() => atk?.typeId) === "minecraft:player";
    let dmg = ev.damage;
    if (byPlayer) {
      const head = this.isHeadHit(ev.damageSource);
      if (head && this.skull >= 2) dmg *= C.skull.brokenHeadBonus;
      if (this.state === "STAGGERED" && this.skull >= 1) dmg *= C.skull.staggerDamageBonus;
    }
    const hp = safe(() => ev.hurtEntity.getComponent("minecraft:health").currentValue, 1);
    if (dmg >= hp - 0.5) {
      // never let the engine kill it: play the death sequence instead (rewards, cleanup)
      dmg = Math.max(0, hp - 1);
      this.pendingDeath = { byPlayer };
    }
    if (dmg <= 0) ev.cancel = true;
    else ev.damage = dmg;
  }

  onHurt(ev) {
    const atk = ev.damageSource.damagingEntity;
    const byPlayer = safe(() => atk?.typeId) === "minecraft:player";
    if (byPlayer) {
      this.dmgByPlayers += ev.damage;
      this.aggro.set(atk.id, (this.aggro.get(atk.id) ?? 0) + ev.damage);
      if (this.state === "IDLE" && validTarget(atk, this.dim)) this.engage(atk);
      if (this.isHeadHit(ev.damageSource)) {
        const rate = this.vulnerable() ? C.skull.vulnerableRate : C.skull.headRate;
        this.addSkull(ev.damage * rate, "head");
        particle(this.dim, `${NS}:impact_burst`, this.headPoint());
      }
    }
    if (this.pendingDeath) {
      const pd = this.pendingDeath;
      this.pendingDeath = undefined;
      this.startDeath(pd.byPlayer);
      return;
    }
    this.checkPhase();
  }

  onPlayerLeave(playerId) {
    if (this.target && safe(() => this.target.id) === playerId) this.target = undefined;
    this.aggro.delete(playerId);
  }

  checkPhase() {
    if (!this.fight || this.state === "DEAD") return;
    const r = this.hpRatio();
    let want = 1;
    if (r < C.phases.thresholds[0]) want = 2;
    if (r < C.phases.thresholds[1]) want = 3;
    if (want > this.phase) {
      this.phase = want; // phases only go up, each transition fires once
      this.prop("phase", want);
      this.save("phase", want);
      const v = this.viewers(56);
      title(v, `§6Phase ${want === 2 ? "II" : "III"}`, `§7${C.phases.names[want - 1]}`);
      if (!this.queued.includes("roar")) this.queued.push("roar");
    }
  }

  // ---------------------------------------------------------------------------------------------- fight lifecycle
  engage(target) {
    this.target = target;
    this.lostSince = undefined;
    this.toScripted();
    if (!this.fight) {
      // the participant count (and therefore max HP) is fixed when the fight begins
      const n = clamp(this.players(C.health.participationRadius).length, 1, C.health.maxPlayers);
      this.tier = n;
      this.fight = true;
      this.home = { ...this.pos() };
      this.dmgByPlayers = 0;
      this.save("tier", n);
      this.save("fight", true);
      this.save("home", JSON.stringify(this.home));
      this.event(`hp_tier_${n}`);
      safe(() => this.health()?.resetToMaxValue());
      const v = this.viewers(56);
      title(v, "§6Gharvok", "§7The Cliffbreaker");
      message(v, `§6Gharvok, the Cliffbreaker §7awakens. §8(${n} hunter${n > 1 ? "s" : ""}, ${hpFor(n)} HP)`);
    }
    this.startMove("roar");
    this.nextDecision = now() + sec(2.6);
  }

  startReset(why) {
    this.endMove(true);
    this.queued = [];
    if (this.inAir) {
      this.settle();
      this.toGround();
      this.flight(0);
    }
    this.setState("RESET");
    this.resetSince = now();
    this.target = undefined;
    this.resetWhy = why;
  }

  finishReset() {
    const o = this.pos();
    if (distXZ(o, this.home) > 3) this.place(this.home);
    this.event("hp_tier_1");
    safe(() => this.health()?.resetToMaxValue());
    this.fight = false;
    this.phase = 1;
    this.skull = 0;
    this.skullPts = 0;
    this.tier = 1;
    this.cool = {};
    this.history = [];
    this.aggro.clear();
    this.prop("phase", 1);
    this.prop("skull", 0);
    for (const k of ["fight", "phase", "skull", "skullPts", "tier"]) this.save(k, undefined);
    this.toRoam();
    this.setState("IDLE");
    this.nextScan = now() + sec(4);
    actionbar(this.viewers(56), "§7Gharvok returns to its cliff.");
  }

  startDeath(byPlayer) {
    this.endMove(true);
    this.queued = [];
    if (this.inAir) {
      this.settle();
      this.toGround();
    }
    this.flight(0);
    this.gait(0);
    this.toScripted();
    this.setState("DEAD");
    this.deathAt = now();
    this.legit = byPlayer || this.dmgByPlayers >= C.rewards.minPlayerDamageShare * (this.health()?.effectiveMax ?? 500);
    this.save("dying", true);
    this.anim("death");
    sound(this.dim, "mob.ravager.death", this.pos(), 3, 0.6);
    sound(this.dim, "mob.enderdragon.growl", this.pos(), 2, 0.5);
  }

  tickDeath() {
    const t = now() - this.deathAt;
    if (t === sec(2.2)) particle(this.dim, `${NS}:dust_ring`, this.pos());
    if (t < sec(4.6)) return true;
    const o = this.pos();
    particle(this.dim, `${NS}:defeat_dust`, { x: o.x, y: o.y + 1, z: o.z });
    sound(this.dim, "random.explode", o, 0.8, 0.5);
    if (this.legit) this.reward(o);
    else actionbar(this.viewers(56), "§7Gharvok collapses... (no reward: the hunters did not defeat it)");
    safe(() => this.e.remove());
    return false;
  }

  reward(o) {
    const n = C.rewards.crownplates + (this.skull >= 2 ? C.rewards.bonusIfBroken : 0);
    safe(() => this.dim.spawnItem(new ItemStack(REWARD_ID, n), { x: o.x, y: o.y + 1, z: o.z }));
    for (let i = 0; i < C.rewards.xpOrbs; i++) {
      safe(() => this.dim.spawnEntity("minecraft:xp_orb", { x: o.x + rand(-2, 2), y: o.y + 1, z: o.z + rand(-2, 2) }));
    }
    const v = this.viewers(64);
    title(v, "§6Gharvok has fallen", `§7Fractured Crownplate x${n}`);
    message(v, `§6Gharvok, the Cliffbreaker §7has been defeated. It dropped §eFractured Crownplate x${n}§7.`);
  }

  // ---------------------------------------------------------------------------------------------- per tick
  tick() {
    const t = now();
    this.lastPos = this.pos();
    if (this.state === "DEAD") return this.tickDeath();
    this.unstick(t);
    if (this.state === "RESET") return this.tickReset(t);
    if (!this.fight || this.state === "IDLE") return this.tickIdle(t);
    return this.tickCombat(t);
  }

  /** Never stay buried or stuck in the air. */
  unstick(t) {
    if (this.inAir && !this.move?.mv.airborne && t - (this.airSince ?? t) > sec(2)) {
      this.settle();
      this.toGround();
      this.flight(0);
    }
    if (t % 20 === 0) {
      const o = this.pos();
      if (isSolid(blockAt(this.dim, o.x, o.y + 1.5, o.z)) && isSolid(blockAt(this.dim, o.x, o.y + 0.5, o.z))) {
        const g = groundAt(this.dim, o.x, o.z, o.y + 8, 0, 10);
        if (g !== undefined) this.place({ x: o.x, y: g, z: o.z });
      }
    }
  }

  tickIdle(t) {
    if (this.move) {
      if (this.runMove()) {
        this.toRoam();
        this.setState("IDLE");
      }
      return true;
    }
    if (t >= this.nextScan) {
      this.nextScan = t + 10;
      const near = this.players(C.detection.radius);
      if (near.length) {
        near.sort((a, b) => distXZ(a.location, this.pos()) - distXZ(b.location, this.pos()));
        this.engage(near[0]);
        return true;
      }
    }
    if (t >= this.nextIdleAct) {
      // natural behaviour: look around or roar at its territory, standing still while it does
      this.nextIdleAct = t + sec(rand(...C.idle.actEvery));
      this.toScripted();
      this.startMove(Math.random() < C.idle.roarChance ? "roar" : "idle_head_scan", { idle: true });
      this.setState("IDLE");
    }
    return true;
  }

  tickReset(t) {
    const o = this.pos();
    const far = distXZ(o, this.home) > 3;
    if (far && t - this.resetSince < sec(C.reset.walkBack)) {
      const res = this.approach(this.home, false);
      if (res.blocked || res.drop) this.resetSince -= sec(C.reset.walkBack); // can't walk back: teleport now
      return true;
    }
    this.finishReset();
    return true;
  }

  pickTarget(t) {
    const o = this.pos();
    const valid = (p) => validTarget(p, this.dim) && distXZ(p.location, o) <= C.detection.targetRadius &&
      distXZ(p.location, this.home) <= C.detection.boundary + 8;
    if (this.target && !valid(this.target)) this.target = undefined;
    const cands = this.players(C.detection.targetRadius).filter(valid);
    if (!this.target || t >= this.nextRetarget) {
      this.nextRetarget = t + sec(C.detection.retargetEvery);
      if (cands.length) {
        // multiplayer: mostly keep pressure on the biggest threat, sometimes switch to someone else
        const sorted = [...cands].sort((a, b) => (this.aggro.get(b.id) ?? 0) - (this.aggro.get(a.id) ?? 0) ||
          distXZ(a.location, o) - distXZ(b.location, o));
        let next = sorted[0];
        if (this.target && cands.length > 1 && Math.random() < C.detection.switchChance) {
          const others = cands.filter((p) => p.id !== this.target.id);
          next = others[Math.floor(Math.random() * others.length)];
        }
        if (!this.target || next.id !== this.target.id) this.target = next;
      }
    }
    if (this.target) this.lostSince = undefined;
    else if (this.lostSince === undefined) this.lostSince = t;
  }

  runMove() {
    const m = this.move;
    if (!m) return true;
    let done = false;
    try {
      done = m.mv.tick(this, m);
    } catch (err) {
      console.warn(`[dragon_dominion] move ${m.mv.name} failed: ${err}`);
      done = true;
    }
    m.t++;
    if (done && this.move === m) {
      this.endMove(false);
      this.nextDecision = now() + sec(C.phases.gapAfterMove[this.phase - 1]);
      return true;
    }
    return false;
  }

  tickCombat(t) {
    if (t % 10 === 0 || !this.target) this.pickTarget(t);
    if (this.move) {
      if (!this.runMove()) return true;
    }
    // queued reactions (fracture, exhaustion, phase roar) run first
    if (this.queued.length) {
      const q = this.queued.shift();
      this.startMove(q === "roar" ? "roar" : q);
      return true;
    }
    if (!this.target) {
      this.gait(0);
      this.setState("PURSUE");
      if (this.lostSince !== undefined && t - this.lostSince > sec(C.detection.loseTargetAfter)) this.startReset("no target");
      return true;
    }
    const o = this.pos();
    if (distXZ(o, this.home) > C.detection.boundary) {
      this.startReset("left the combat boundary");
      return true;
    }
    const tl = this.target.location;
    const d = distXZ(o, tl);
    const ang = Math.abs(relAngle(o, this.yaw, tl));
    if (t >= this.nextDecision) {
      const pick = this.chooseAttack(d, ang);
      if (pick) {
        this.startMove(pick);
        return true;
      }
    }
    // pursue: close in to claw range, facing the target
    this.setState("PURSUE");
    if (d > 5.2) {
      const res = this.approach(tl, d > 11);
      this.trackProgress(t, res);
    } else {
      this.gait(0);
      this.face(tl, C.phases.turnRate[this.phase - 1]);
      this.lastProgress = { t, p: o };
    }
    return true;
  }

  /** Stuck pursuing (wall, pit): leap aside, and as a last resort reset. */
  trackProgress(t, res) {
    const o = this.pos();
    if (distXZ(o, this.lastProgress.p) > 1.5) {
      this.lastProgress = { t, p: o };
      return;
    }
    if (t - this.lastProgress.t > sec(4) && this.phase >= 1 && this.ready("reposition_leap")) {
      this.lastProgress = { t, p: o };
      this.startMove("reposition_leap");
    } else if (t - this.lastProgress.t > sec(12)) {
      this.startReset("stuck");
    }
  }

  chooseAttack(d, ang) {
    const A = C.attacks;
    const ph = this.phase;
    const o = this.pos();
    const near = this.players(9);
    const behind = near.filter((p) => Math.abs(relAngle(o, this.yaw, p.location)) >= A.rudder_sweep.minAngle &&
      distXZ(o, p.location) <= A.rudder_sweep.radius);
    const list = [];
    const add = (item, w) => {
      if (w <= 0 || !this.ready(item)) return;
      const last = this.history[this.history.length - 1];
      if (last === item) w *= 0.15; // avoid repeating the same attack
      else if (this.history.includes(item)) w *= 0.6;
      list.push({ item, w });
    };
    if (d <= A.twin_claw.range && ang <= A.twin_claw.halfAngle) add("twin_claw", 3);
    if (d >= A.crushing_charge.minRange && d <= A.crushing_charge.maxRange && ang <= 80) add("crushing_charge", ph === 1 ? 3 : 2.5);
    if (behind.length && (ang >= 70 || behind.length >= 1)) add("rudder_sweep", 3 + behind.length);
    if (ph >= A.wing_pressure.minPhase && ((d <= 9 && ang <= 70) || near.length >= 2)) add("wing_pressure", near.length >= 2 ? 4 : 2);
    if (ph >= A.cliff_dive.minPhase && d >= A.cliff_dive.minRange && d <= A.cliff_dive.maxRange && skyClear(this) &&
      diveSpot(this, this.target)) add("cliff_dive", 2.5);
    if (ph >= A.skullbreaker.minPhase && d <= A.skullbreaker.range && ang <= A.skullbreaker.halfAngle) add("skullbreaker", 4);
    if (ph >= A.reposition_leap.minPhase && d < 4 && ang > 50 && !list.length) add("reposition_leap", 1);
    return weighted(list);
  }
}

export { MOVES };
