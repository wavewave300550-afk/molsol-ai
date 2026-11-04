import { Entity, EntityDamageCause, EntityProjectileComponent, Vector3 } from "@minecraft/server";
import { BALANCE } from "./balance.js";
import {
  Ability, BossState, actionBar, at, centerOf, event, face, groundBelow, hurt, isLiving, knockFrom, lock, message, now,
  playersNear, rayClear, safe, sec, setAction, setProp, turnTo, unlock, victims,
} from "./boss.js";
import { PFX, SND, particle, sound } from "./fx.js";
import { CHEST, CORE, PALM_DIVE, PALM_QUAKE, PALM_SHOT } from "./offsets.js";
import { ACTIONS, Action, GEAR_ID, SIGIL_ID } from "./spec.js";
import { DEG, add, clamp, hdist, lerp, mul, norm, sub, v3, yawTo } from "./vec.js";

const COOLDOWN: Record<Ability, number> = {
  gear_volley: BALANCE.gear_volley.cooldown,
  quake: BALANCE.quake.cooldown,
  vitruvian: BALANCE.vitruvian.cooldown,
  dive: BALANCE.dive.cooldown,
};

function ticksOf(kind: Action): number {
  return kind === "none" ? 0 : sec(ACTIONS[kind].length);
}

function moment(kind: Action, name: string): number {
  if (kind === "none") return 0;
  const m = ACTIONS[kind].moments as Record<string, number>;
  return sec(m[name]);
}

/** Start a scripted action: movement is locked and the client plays the matching animation. */
export function startAction(s: BossState, kind: Action): void {
  lock(s);
  s.run = { kind, tick: 0, length: ticksOf(kind), fired: new Set() };
  setAction(s, kind);
  const dim = s.entity.dimension;
  const pos = s.entity.location;
  if (kind === "gear_volley") sound(dim, SND.click, pos, 1, 0.6);
  if (kind === "quake") sound(dim, SND.spell, pos, 0.8, 1.4);
  if (kind === "vitruvian") sound(dim, SND.charge, pos, 1.2, 1.1);
  if (kind === "transform") {
    s.invulnerable = true;
    s.phase = 2;
    setProp(s, "esb:phase", 2);
    sound(dim, SND.summon, pos, 1.4, 0.8);
  }
  if (kind === "intro") {
    s.invulnerable = true;
    sound(dim, SND.bell, pos, 1.6, 0.7);
  }
}

/** Ends the current action and frees the boss (cooldowns and the global gap start here). */
export function endAction(s: BossState, ability?: Ability): void {
  const kind = s.run?.kind;
  s.run = undefined;
  removeSigil(s);
  if (kind === "intro" || kind === "transform") s.invulnerable = false;
  if (kind === "flourish") s.nextFlourish = now() + sec(lerp(BALANCE.flourish.every_min, BALANCE.flourish.every_max, Math.random()));
  setAction(s, "none");
  s.gapUntil = now() + sec(BALANCE.global_gap);
  if (ability) s.ready[ability] = now() + sec(COOLDOWN[ability] * (s.phase === 2 ? 0.8 : 1));
  unlock(s);
}

function fire(s: BossState, name: string): boolean {
  const run = s.run;
  if (!run || run.fired.has(name)) return false;
  if (run.tick < moment(run.kind as Action, name)) return false;
  run.fired.add(name);
  return true;
}

function targetPoint(s: BossState): Vector3 | undefined {
  return isLiving(s.target) ? centerOf(s.target) : undefined;
}

// ------------------------------------------------------------------------------------------ per-tick driver

export function tickRun(s: BossState): void {
  const run = s.run;
  if (!run) return;
  run.tick++;
  switch (run.kind) {
    case "intro":
      tickIntro(s);
      break;
    case "gear_volley":
      tickGears(s);
      break;
    case "quake":
      tickQuake(s);
      break;
    case "vitruvian":
      tickVitruvian(s);
      break;
    case "transform":
      tickTransform(s);
      break;
    case "dive_rise":
    case "dive_hover":
    case "dive_strike":
      tickDive(s);
      return; // the dive manages its own end
    case "flourish":
      break;
    default:
      break;
  }
  if (s.run && s.run.tick >= s.run.length) {
    const ab: Ability | undefined = run.kind === "gear_volley" || run.kind === "quake" || run.kind === "vitruvian"
      ? run.kind : undefined;
    endAction(s, ab);
  }
}

// ------------------------------------------------------------------------------------------ intro

function tickIntro(s: BossState): void {
  const dim = s.entity.dimension;
  const pos = s.entity.location;
  if (fire(s, "burst")) {
    particle(dim, PFX.pillar, pos);
    particle(dim, PFX.pages, at(s, CHEST));
    sound(dim, SND.page, pos, 1.2, 0.8);
    for (const p of playersNear(s, 48)) {
      safe(() => p.onScreenDisplay.setTitle({ rawtext: [{ translate: "esb.title.boss" }] }, {
        subtitle: { rawtext: [{ translate: "esb.subtitle.boss" }] }, fadeInDuration: 10, stayDuration: 50, fadeOutDuration: 20,
      }));
    }
  }
  if (fire(s, "rise")) message(playersNear(s, 48), "esb.msg.intro");
  if (fire(s, "flex")) {
    particle(dim, PFX.steam, at(s, CORE));
    particle(dim, PFX.spark, at(s, PALM_SHOT));
    sound(dim, SND.anvil, pos, 0.6, 1.6);
  }
  const tp = targetPoint(s);
  if (tp && s.run && s.run.tick > moment("intro", "rise")) turnTo(s, tp, 6);
}

// ------------------------------------------------------------------------------------------ gear volley

const SHOTS = ["shot1", "shot2", "shot3"];

function tickGears(s: BossState): void {
  const tp = targetPoint(s);
  const run = s.run!;
  if (tp && run.tick <= moment("gear_volley", "shot3")) turnTo(s, tp, 12);
  for (const name of SHOTS) {
    if (!fire(s, name)) continue;
    const dim = s.entity.dimension;
    const palm = at(s, PALM_SHOT);
    const goal = tp ?? add(palm, v3(-Math.sin(s.yaw * DEG) * 10, -1, Math.cos(s.yaw * DEG) * 10));
    const base = norm(sub(goal, palm));
    const n = s.phase === 2 ? BALANCE.gear_volley.gears_phase2 : BALANCE.gear_volley.gears_phase1;
    for (let i = 0; i < n; i++) {
      const a = (i - (n - 1) / 2) * BALANCE.gear_volley.spread_deg * DEG;
      const dir = v3(base.x * Math.cos(a) - base.z * Math.sin(a), base.y, base.x * Math.sin(a) + base.z * Math.cos(a));
      shootGear(s, palm, mul(dir, BALANCE.gear_volley.speed));
    }
    particle(dim, PFX.spark, palm);
    sound(dim, SND.shot, palm, 1, 1.5);
    sound(dim, SND.click, palm, 1, 0.8);
  }
}

export function shootGear(s: BossState, from: Vector3, velocity: Vector3): Entity | undefined {
  const g = safe(() => s.entity.dimension.spawnEntity(GEAR_ID, from));
  if (!g) return undefined;
  const proj = safe(() => g.getComponent("minecraft:projectile")) as EntityProjectileComponent | undefined;
  if (!proj) {
    safe(() => g.remove());
    return undefined;
  }
  safe(() => {
    proj.owner = s.entity;
  });
  safe(() => proj.shoot(velocity, { uncertainty: 0 }));
  return g;
}

// ------------------------------------------------------------------------------------------ gauntlet quake

function tickQuake(s: BossState): void {
  const tp = targetPoint(s);
  if (tp && s.run!.tick < moment("quake", "impact") - 4) turnTo(s, tp, 10);
  if (!fire(s, "impact")) return;
  const dim = s.entity.dimension;
  const q = BALANCE.quake;
  const fist = at(s, PALM_QUAKE);
  const center = v3(fist.x, s.entity.location.y, fist.z);
  for (const t of victims(s, center, q.radius, 2, 3)) {
    const d = hdist(t.location, center);
    const k = d <= 2.5 ? 1 : lerp(1, 0.5, clamp((d - 2.5) / (q.radius - 2.5), 0, 1));
    if (hurt(s, t, q.damage * k)) knockFrom(t, center, q.knockback, q.lift);
  }
  particle(dim, PFX.shockwave, add(center, v3(0, 0.15, 0)), q.radius);
  particle(dim, PFX.dust, add(center, v3(0, 0.3, 0)));
  particle(dim, PFX.spark, add(center, v3(0, 0.5, 0)));
  sound(dim, SND.boom, center, 1.2, 0.9);
  sound(dim, SND.anvil, center, 1, 0.6);
}

// ------------------------------------------------------------------------------------------ vitruvian judgement

export function vitruvianRadius(s: BossState): number {
  return s.phase === 2 ? BALANCE.vitruvian.radius_phase2 : BALANCE.vitruvian.radius_phase1;
}

function spawnSigil(s: BossState, p: Vector3, radius: number): Entity | undefined {
  const e = safe(() => s.entity.dimension.spawnEntity(SIGIL_ID, p));
  if (e) safe(() => e.setProperty("esb:radius", Math.round(clamp(radius, 1, 12))));
  return e;
}

export function removeSigil(s: BossState): void {
  if (s.sigil && s.sigil.isValid) safe(() => s.sigil!.remove());
  s.sigil = undefined;
  if (s.dive?.marker && s.dive.marker.isValid) safe(() => s.dive!.marker!.remove());
  if (s.dive) s.dive.marker = undefined;
}

function tickVitruvian(s: BossState): void {
  const dim = s.entity.dimension;
  const R = vitruvianRadius(s);
  const pos = s.entity.location;
  const feet = v3(pos.x, (groundBelow(s, add(pos, v3(0, 0.5, 0)), 4) ?? pos.y) + 0.02, pos.z);
  if (fire(s, "sigil")) {
    removeSigil(s);
    s.sigil = spawnSigil(s, feet, R);
    actionBar(playersNear(s, R + 8), "esb.msg.vitruvian");
    sound(dim, SND.spell, pos, 1.2, 0.7);
  }
  const run = s.run!;
  const sig = moment("vitruvian", "sigil");
  const det = moment("vitruvian", "detonate");
  if (run.tick > sig && run.tick < det && (run.tick - sig) % 5 === 0) particle(dim, PFX.sigilEdge, add(feet, v3(0, 0.1, 0)), R);
  if (!fire(s, "detonate")) return;
  const v = BALANCE.vitruvian;
  for (const t of victims(s, feet, R, 2, 4)) {
    if (hurt(s, t, v.damage)) knockFrom(t, feet, 0.5, v.lift);
  }
  particle(dim, PFX.sigilBurst, add(feet, v3(0, 0.1, 0)), R);
  particle(dim, PFX.spark, add(feet, v3(0, 1.2, 0)));
  sound(dim, SND.boom, feet, 1.3, 0.8);
  sound(dim, SND.totem, feet, 0.7, 1.4);
  removeSigil(s);
}

// ------------------------------------------------------------------------------------------ transform (phase 2)

function tickTransform(s: BossState): void {
  if (!fire(s, "burst")) return;
  const dim = s.entity.dimension;
  const pos = s.entity.location;
  particle(dim, PFX.pages, at(s, CHEST));
  particle(dim, PFX.shockwave, add(pos, v3(0, 0.15, 0)), 7);
  particle(dim, PFX.spark, at(s, CORE));
  sound(dim, SND.totem, pos, 1.2, 0.8);
  sound(dim, SND.flap, pos, 1.4, 0.8);
  message(playersNear(s, 64), "esb.msg.phase2");
  for (const t of victims(s, pos, 7, 2, 4)) knockFrom(t, pos, 1.4, 0.5);
  // phase 2 opens with the ornithopter dive soon after
  s.ready.dive = now() + sec(3);
}

// ------------------------------------------------------------------------------------------ ornithopter dive (phase 2)

const RISE_TICKS = 12;
const STRIKE_TICKS = moment("dive_strike", "impact");

function teleport(s: BossState, p: Vector3): void {
  safe(() => s.entity.teleport(p, { rotation: { x: 0, y: s.yaw }, keepVelocity: false, checkForBlocks: false }));
}

export function startDive(s: BossState): void {
  startAction(s, "dive_rise");
  const pos = s.entity.location;
  s.dive = { stage: "rise", stageTick: 0, from: { ...pos }, peak: { ...pos }, landing: { ...pos }, lockAt: 0, hoverTicks: 0 };
  sound(s.entity.dimension, SND.flap, pos, 1.2, 1.1);
}

function landingFor(s: BossState): Vector3 {
  const t = s.target;
  const p = isLiving(t) ? t.location : add(s.entity.location, v3(-Math.sin(s.yaw * DEG) * 6, 0, Math.cos(s.yaw * DEG) * 6));
  const y = groundBelow(s, add(p, v3(0, 2, 0)), 30);
  return v3(p.x, y ?? p.y, p.z);
}

function tickDive(s: BossState): void {
  const d = s.dive;
  const run = s.run!;
  if (!d) {
    endAction(s, "dive");
    return;
  }
  const dim = s.entity.dimension;
  const tp = targetPoint(s);
  if (tp && d.stage !== "strike") turnTo(s, tp, 10);

  if (d.stage === "rise") {
    if (run.tick < moment("dive_rise", "leap")) return;
    if (run.tick === moment("dive_rise", "leap")) {
      const pos = s.entity.location;
      const head = add(pos, v3(0, 3.6, 0));
      const room = rayClear(s, head, v3(0, 1, 0), BALANCE.dive.height + 1);
      const h = Math.min(BALANCE.dive.height, room - 1);
      if (h < 3) {
        // no head room: cancel the dive cleanly
        s.dive = undefined;
        endAction(s, "dive");
        return;
      }
      event(s, "esb:to_air");
      s.inAir = true;
      s.locked = true;
      d.from = { ...pos };
      d.peak = add(pos, v3(0, h, 0));
      particle(dim, PFX.dust, add(pos, v3(0, 0.3, 0)));
      sound(dim, SND.flap, pos, 1.4, 0.9);
    }
    d.stageTick++;
    const k = clamp(d.stageTick / RISE_TICKS, 0, 1);
    const e = 1 - (1 - k) * (1 - k);
    teleport(s, v3(d.from.x, lerp(d.from.y, d.peak.y, e), d.from.z));
    if (d.stageTick >= RISE_TICKS) {
      d.stage = "hover";
      d.stageTick = 0;
      d.hoverTicks = sec(BALANCE.dive.hover);
      d.lockAt = d.hoverTicks - sec(0.6);
      d.landing = landingFor(s);
      d.marker = spawnSigil(s, v3(d.landing.x, d.landing.y + 0.02, d.landing.z), BALANCE.dive.radius);
      s.run = { kind: "dive_hover", tick: 0, length: d.hoverTicks, fired: new Set() };
      setAction(s, "dive_hover");
      actionBar(playersNear(s, 40), "esb.msg.dive");
    }
    return;
  }

  if (d.stage === "hover") {
    d.stageTick++;
    if (d.stageTick % 6 === 0) sound(dim, SND.flap, s.entity.location, 0.9, 1.2);
    teleport(s, v3(d.peak.x, d.peak.y + Math.sin(d.stageTick * 0.3) * 0.15, d.peak.z));
    if (d.stageTick < d.lockAt) {
      d.landing = landingFor(s);
      if (d.marker?.isValid) safe(() => d.marker!.teleport(v3(d.landing.x, d.landing.y + 0.02, d.landing.z)));
    }
    if (d.stageTick >= d.hoverTicks) {
      // keep the landing point if the straight path is clear, otherwise drop straight down
      const path = sub(d.landing, d.peak);
      const len = Math.sqrt(path.x * path.x + path.y * path.y + path.z * path.z);
      if (len > 0.5 && rayClear(s, add(d.peak, v3(0, 1, 0)), norm(path), len) < len - 1.5) {
        const y = groundBelow(s, d.peak, 40);
        d.landing = v3(d.peak.x, y ?? d.from.y, d.peak.z);
      }
      face(s, yawTo(d.peak, d.landing));
      d.stage = "strike";
      d.stageTick = 0;
      s.run = { kind: "dive_strike", tick: 0, length: ticksOf("dive_strike"), fired: new Set() };
      setAction(s, "dive_strike");
    }
    return;
  }

  // strike: straight line from the peak to the landing point, arriving exactly on the impact frame
  d.stageTick++;
  run.tick = d.stageTick;
  if (d.stageTick <= STRIKE_TICKS) {
    const k = d.stageTick / STRIKE_TICKS;
    const e = k * k;
    teleport(s, v3(lerp(d.peak.x, d.landing.x, e), lerp(d.peak.y, d.landing.y, e), lerp(d.peak.z, d.landing.z, e)));
  }
  if (d.stageTick === STRIKE_TICKS) {
    event(s, "esb:to_ground");
    s.inAir = false;
    const dv = BALANCE.dive;
    const fist = at(s, PALM_DIVE);
    const center = v3(fist.x, d.landing.y, fist.z);
    for (const t of victims(s, center, dv.radius, 2, 3)) {
      if (hurt(s, t, dv.damage)) knockFrom(t, center, 1.2, dv.lift);
    }
    particle(dim, PFX.shockwave, add(center, v3(0, 0.15, 0)), dv.radius);
    particle(dim, PFX.dust, add(center, v3(0, 0.3, 0)));
    particle(dim, PFX.sigilBurst, add(center, v3(0, 0.1, 0)), dv.radius);
    sound(dim, SND.boom, center, 1.3, 0.8);
    if (d.marker?.isValid) safe(() => d.marker!.remove());
    d.marker = undefined;
  }
  if (d.stageTick >= ticksOf("dive_strike")) {
    s.dive = undefined;
    endAction(s, "dive");
  }
}

/** Emergency: back on the ground with gravity, wherever it is. */
export function forceGround(s: BossState): void {
  if (s.inAir) {
    event(s, "esb:to_ground");
    s.inAir = false;
  }
  removeSigil(s);
  s.dive = undefined;
}

// ------------------------------------------------------------------------------------------ death

export function beginDying(s: BossState): void {
  if (s.dying) return;
  forceGround(s);
  s.run = undefined;
  s.dying = true;
  s.dyingTick = now();
  s.invulnerable = true;
  event(s, "esb:dying");
  s.locked = true;
  setAction(s, "death");
  safe(() => s.entity.clearVelocity());
  sound(s.entity.dimension, SND.anvilBreak, s.entity.location, 1, 0.7);
}

export function tickDying(s: BossState): void {
  const t = now() - s.dyingTick;
  const dim = s.entity.dimension;
  const kneel = sec(ACTIONS.death.moments.kneel);
  const pages = sec(ACTIONS.death.moments.pages);
  if (t === kneel) sound(dim, SND.anvil, s.entity.location, 0.7, 0.5);
  if (t === pages) {
    particle(dim, PFX.pages, at(s, CHEST));
    sound(dim, SND.page, s.entity.location, 1.2, 0.7);
    message(playersNear(s, 64), "esb.msg.death");
  }
  if (t >= sec(ACTIONS.death.length) && !s.allowKill) {
    s.allowKill = true;
    const h = s.entity.getComponent("minecraft:health") as unknown as { currentValue: number } | undefined;
    const amount = (h?.currentValue ?? 1) + 1000;
    const killer = s.killer && s.killer.isValid ? s.killer : undefined;
    const done = killer
      ? safe(() => s.entity.applyDamage(amount, { cause: EntityDamageCause.entityAttack, damagingEntity: killer }))
      : false;
    if (!done) safe(() => s.entity.kill());
  }
}
