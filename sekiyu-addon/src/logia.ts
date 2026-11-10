import { Entity, EntityDamageCause, EquipmentSlot, Player, system, Vector3 } from "@minecraft/server";
import { Form, LOGIA, PASSABLE, TUNING } from "./config.js";
import { isEnemy, oilSlow } from "./core/combat.js";
import { center, P, particle, S, sound, line } from "./core/fx.js";
import { add, flat, v } from "./core/vec.js";
import { spawnPool } from "./pools.js";
import { syncProperties } from "./power.js";
import { isLiquidForm, isOwner, notice, now, OilState, state } from "./state.js";

/** Damage that a liquid body lets pass through (physical / kinetic). */
const PHYSICAL = new Set<string>([
  EntityDamageCause.entityAttack, EntityDamageCause.projectile, EntityDamageCause.contact, EntityDamageCause.fallingBlock,
  EntityDamageCause.anvil, EntityDamageCause.flyIntoWall, EntityDamageCause.piston, EntityDamageCause.ramAttack,
  EntityDamageCause.thorns, EntityDamageCause.maceSmash, EntityDamageCause.stalactite, EntityDamageCause.stalagmite,
]);
const EXPLOSION = new Set<string>([EntityDamageCause.blockExplosion, EntityDamageCause.entityExplosion]);
const FIRE = new Set<string>([
  EntityDamageCause.fire, EntityDamageCause.fireTick, EntityDamageCause.lava, EntityDamageCause.campfire,
  EntityDamageCause.soulCampfire, EntityDamageCause.lightning, EntityDamageCause.magma,
]);

export const DAMAGE_RULES = { physical: [...PHYSICAL], explosion: [...EXPLOSION], fire: [...FIRE] };

/** Sea-forged weapons (tridents, drowned) carry the sea's weakness: they hit a Logia for real. */
function seaForged(src: Entity | undefined): boolean {
  if (!src || !src.isValid) return false;
  if (src.typeId === "minecraft:thrown_trident" || src.typeId === "minecraft:drowned" || src.typeId === "minecraft:guardian" || src.typeId === "minecraft:elder_guardian") return true;
  try {
    return src.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Mainhand)?.typeId === "minecraft:trident";
  } catch {
    return false;
  }
}

export type HurtDecision = { cancel: boolean; damage?: number; dodge?: "form" | "reflex"; seaForged?: boolean; burn?: boolean };

/** Decide what happens to damage on a petroleum user (pure; called from the before-event). */
export function judgeDamage(p: Player, cause: string, damage: number, source: Entity | undefined, projectile: Entity | undefined): HurtDecision {
  if (!isOwner(p)) return { cancel: false };
  const s = state(p);
  const t = now();
  const liquid = isLiquidForm(s);
  if (cause === EntityDamageCause.fall) {
    if (liquid || s.fallGuardUntil >= t) return { cancel: true };
    return { cancel: false, damage: damage * LOGIA.fallFactor };
  }
  if (FIRE.has(cause)) return liquid ? { cancel: false, damage: damage * LOGIA.fireVulnerability, burn: true } : { cancel: false };
  if (s.sealed) return { cancel: false }; // submerged: the body cannot turn to oil
  if (seaForged(source) || seaForged(projectile)) return { cancel: false, seaForged: true };
  if (PHYSICAL.has(cause)) {
    if (liquid) return { cancel: true, dodge: "form" };
    if (t >= s.reflexReadyAt) {
      s.reflexReadyAt = t + LOGIA.reflexTicks; // set now: a second blow in the same tick must land
      return { cancel: true, dodge: "reflex" };
    }
    return { cancel: false };
  }
  if (EXPLOSION.has(cause) && liquid) return { cancel: false, damage: damage * LOGIA.explosionFactor };
  return { cancel: false };
}

/** Effects of a decision (runs after the before-event, outside restricted mode). */
export function applyDecision(p: Player, d: HurtDecision, source: Entity | undefined): void {
  if (!p.isValid) return;
  const s = state(p);
  const dim = p.dimension;
  if (d.dodge) {
    particle(dim, P.dodge, center(p));
    sound(dim, S.dodge, p.location, 0.9, 0.9 + Math.random() * 0.2);
    // the attacker comes away coated in heavy oil
    if (source && source.isValid && source.id !== p.id && isEnemy(source, p)) oilSlow(source, 40, 1);
    if (d.dodge === "reflex") notice(s, "§8Your body flowed around the blow §7(Flow recharging 4s)", 30);
  }
  if (d.seaForged && isLiquidForm(s)) {
    setForm(p, s, Form.Human);
    notice(s, "§bSea-forged weapon! §7You are forced back into flesh.", 50);
  }
  if (d.burn) {
    s.burningUntil = Math.max(s.burningUntil, now() + 40);
    syncProperties(p, s);
  }
}

// --------------------------------------------------------------------------- forms

/** Change the petroleum form with its transition effects. */
export function setForm(p: Player, s: OilState, form: Form): void {
  if (s.form === form) return;
  const prev = s.form;
  s.form = form;
  const dim = p.dimension;
  if (form === Form.Body) {
    particle(dim, P.drip, center(p));
    particle(dim, P.splash, add(p.location, v(0, 0.2, 0)));
    sound(dim, S.melt, p.location, 1, 1);
  } else if (form === Form.Dissolved) {
    particle(dim, P.dissolve, p.location);
    sound(dim, S.slurp, p.location, 1, 1);
    s.dissolvedUntil = now() + TUNING.seep.duration;
  } else if (form === Form.Human && (prev === Form.Body || prev === Form.Dissolved)) {
    particle(dim, P.reform, p.location);
    sound(dim, S.reform, p.location, 1, 1);
    for (const id of ["invisibility", "speed", "resistance"] as const) {
      try {
        const e = p.getEffect(id);
        if (e && e.duration <= 40) p.removeEffect(id);
      } catch {
        // dead
      }
    }
    s.dissolvedUntil = 0;
  }
  refreshFormEffects(p, s);
  syncProperties(p, s);
}

/** Light crude while moving, heavy crude while standing; dissolved = fast and unseen. Short, self-refreshing effects. */
export function refreshFormEffects(p: Player, s: OilState): void {
  try {
    if (s.form === Form.Body) {
      if (s.speed > 0.06) p.addEffect("speed", 15, { amplifier: 1, showParticles: false });
      else p.addEffect("resistance", 15, { amplifier: 0, showParticles: false });
    } else if (s.form === Form.Dissolved) {
      p.addEffect("speed", 15, { amplifier: TUNING.seep.speedAmp, showParticles: false });
      p.addEffect("invisibility", 15, { amplifier: 0, showParticles: false });
    }
  } catch {
    // dead / respawning
  }
}

// --------------------------------------------------------------------------- per-tick logia upkeep

function open(dim: Player["dimension"], at: Vector3): boolean {
  try {
    const b = dim.getBlock(at);
    if (!b) return false;
    if (b.isAir) return true;
    if (b.isLiquid) return false;
    return PASSABLE.has(b.typeId);
  } catch {
    return false;
  }
}

/**
 * Seeping: a dissolved player pushing into a 1-block-high opening flows through it to the
 * first spot with room to stand (max TUNING.seep.seepDistance blocks). Every block on the way
 * must be open at foot level, so walls are never clipped through and nothing leaves the world.
 */
export function trySeep(p: Player, s: OilState): boolean {
  const dim = p.dimension;
  const f = flat(p.getViewDirection());
  const y = Math.floor(p.location.y + 0.01);
  const range = dim.heightRange;
  if (y <= range.min || y + 2 >= range.max) return false;
  const cell = (k: number) => ({ x: Math.floor(p.location.x + f.x * (0.8 + k)), z: Math.floor(p.location.z + f.z * (0.8 + k)) });
  const c0 = cell(0);
  if (!open(dim, v(c0.x, y, c0.z)) || open(dim, v(c0.x, y + 1, c0.z))) return false; // not a 1-high gap
  for (let k = 1; k <= TUNING.seep.seepDistance; k++) {
    const c = cell(k);
    if (!open(dim, v(c.x, y, c.z))) return false;
    if (open(dim, v(c.x, y + 1, c.z))) {
      const to = v(c.x + 0.5, y, c.z + 0.5);
      line(dim, P.trail, p.location, to, 0.6);
      try {
        p.teleport(to, { keepVelocity: false });
      } catch {
        return false;
      }
      sound(dim, S.slurp, to, 0.7, 1.3);
      notice(s, "§8Seeped through the gap", 25);
      return true;
    }
  }
  return false;
}

/** Called every 2 ticks for each petroleum user. */
export function tickLogia(p: Player, s: OilState, t: number): void {
  const loc = p.location;
  if (s.lastPos) s.speed = s.speed * 0.5 + (Math.hypot(loc.x - s.lastPos.x, loc.z - s.lastPos.z) / 2) * 0.5;
  s.lastPos = { x: loc.x, y: loc.y, z: loc.z };

  // seawater-like weakness: submerged = no oil body, no powers
  const wet = p.isInWater;
  const entered = wet && !s.sealed;
  if (wet !== s.sealed) {
    s.sealed = wet;
    if (wet) {
      if (isLiquidForm(s)) setForm(p, s, Form.Human);
      notice(s, "§bSubmerged! §7Your powers are sealed.", 50);
      sound(p.dimension, S.sealed, loc, 0.8, 1);
    }
  }
  if (wet && (entered || t % 10 === 0)) {
    try {
      p.addEffect("weakness", 20, { amplifier: 0, showParticles: false });
      p.addEffect("slowness", 20, { amplifier: LOGIA.waterSlowAmp, showParticles: false });
    } catch {
      // dead
    }
  }

  if (s.form === Form.Dissolved) {
    if (t >= s.dissolvedUntil) setForm(p, s, Form.Human);
    else {
      if (t % 4 === 0) particle(p.dimension, P.trail, add(loc, v(0, 0.1, 0)));
      if (s.speed < 0.04) trySeep(p, s);
    }
  }
  if (s.form === Form.Body && s.speed > 0.08 && t - s.lastTrail >= TUNING.body.trailEvery) {
    s.lastTrail = t;
    spawnPool(p.dimension, loc, TUNING.body.trailRadius, p.id, { ticks: 160 });
  }
  if (t % 10 === 0) refreshFormEffects(p, s);
  syncProperties(p, s);
}

export function deferDecision(p: Player, d: HurtDecision, source: Entity | undefined): void {
  if (!d.dodge && !d.seaForged && !d.burn) return;
  system.run(() => applyDecision(p, d, source));
}
