import { Entity, EntityDamageCause, EntityDamageSource, Player, system, world } from "@minecraft/server";
import { CANE, ID } from "../config.js";
import { alive, cachedArmor, constitutionOf } from "../core/targets.js";
import { angleBetween, clamp, flat, sub } from "../core/vec.js";
import { isDazzled } from "./dazzle.js";
import { isFrozen, shatter } from "./frost.js";

// ------------------------------------------------------------------ script-applied damage bypasses the pipeline
const skipping = new Map<string, number>();

export function scriptDamage(e: Entity, amount: number, cause: EntityDamageCause, by?: Entity): boolean {
  if (amount <= 0 || !alive(e)) return false;
  skipping.set(e.id, (skipping.get(e.id) ?? 0) + 1);
  try {
    return by && alive(by) ? e.applyDamage(amount, { cause, damagingEntity: by }) : e.applyDamage(amount, { cause });
  } catch {
    return false;
  }
}

export function clearSkips(): void {
  skipping.clear();
}

// ------------------------------------------------------------------ hooks filled in by the item modules
export interface CutInfo {
  vital: boolean;
  armorFactor: number;
  armorPoints: number;
}

export const hooks = {
  /** held item type per player, refreshed every tick (no inventory reads inside before-events) */
  held: new Map<string, string>(),
  deflectWindow: (_p: Player): { active: boolean; start: number } => ({ active: false, start: 0 }),
  onDeflect: (_p: Player, _attacker: Entity | undefined, _projectile: Entity | undefined, _perfect: boolean): void => undefined,
  onHeavyBlow: (_p: Player, _attacker: Entity): void => undefined,
  onCut: (_p: Player, _target: Entity, _info: CutInfo): void => undefined,
  onMiss: (_attacker: Entity, _target: Entity): void => undefined,
  tethered: (_p: Player): boolean => false,
};

/** Is the attacker's crosshair on the target's head/neck? (precise cut) */
export function vitalAim(p: Player, target: Entity): boolean {
  try {
    const eye = p.getHeadLocation();
    const dir = p.getViewDirection();
    const head = target.getHeadLocation();
    const to = sub(head, eye);
    const along = to.x * dir.x + to.y * dir.y + to.z * dir.z;
    if (along <= 0) return false;
    const closest = { x: eye.x + dir.x * along, y: eye.y + dir.y * along, z: eye.z + dir.z * along };
    const d = Math.hypot(closest.x - head.x, closest.y - head.y, closest.z - head.z);
    return d < 0.38;
  } catch {
    return false;
  }
}

/** Cutting damage after constitution and armour (the slender blade glances off plate). */
export function cutMultiplier(p: Player, target: Entity, vital: boolean, armorIgnore = 0): CutInfo & { mult: number } {
  const con = constitutionOf(target);
  const armor = cachedArmor(target) ?? { points: 0, toughness: 0 };
  const pts = armor.points * (vital ? 0.5 : 1) * (1 - armorIgnore);
  const armorFactor = clamp(1 - 0.03 * pts - 0.01 * armor.toughness * (1 - armorIgnore), 0.25, 1);
  return { mult: con.cut * armorFactor * (vital ? 1.15 : 1), vital, armorFactor, armorPoints: pts };
}

function deflect(p: Player, src: EntityDamageSource, damage: number): "cancel" | number | undefined {
  if (hooks.held.get(p.id) !== ID.caneDrawn) return undefined;
  const w = hooks.deflectWindow(p);
  if (!w.active) return undefined;
  if (src.cause !== EntityDamageCause.entityAttack && src.cause !== EntityDamageCause.projectile) return undefined;
  const from = src.damagingProjectile?.location ?? src.damagingEntity?.location;
  if (!from) return undefined;
  try {
    if (angleBetween(flat(p.getViewDirection()), flat(sub(from, p.location))) > 100) return undefined;
  } catch {
    return undefined;
  }
  const att = src.damagingEntity;
  if (att && src.cause === EntityDamageCause.entityAttack && constitutionOf(att).heavy) {
    system.run(() => hooks.onHeavyBlow(p, att));
    return damage * 0.5;
  }
  const perfect = system.currentTick - w.start <= CANE.deflectPerfect;
  const proj = src.damagingProjectile;
  system.run(() => hooks.onDeflect(p, att, proj, perfect));
  return "cancel";
}

export function initDamagePipeline(): void {
  world.beforeEvents.entityHurt.subscribe((ev) => {
    const target = ev.hurtEntity;
    const n = skipping.get(target.id);
    if (n) {
      if (n <= 1) skipping.delete(target.id);
      else skipping.set(target.id, n - 1);
      return;
    }
    const src = ev.damageSource;
    const attacker = src.damagingEntity;
    // 1) dazzled by Snowblind glare: most blows and shots go wide
    if (attacker && isDazzled(attacker) && Math.random() < 0.7) {
      ev.cancel = true;
      system.run(() => hooks.onMiss(attacker, target));
      return;
    }
    // 2) Kaeshi deflect window of the bamboo sword cane; the handline arrests falls
    if (target instanceof Player) {
      if (src.cause === EntityDamageCause.fall && hooks.tethered(target)) {
        ev.damage *= 0.3;
        return;
      }
      const r = deflect(target, src, ev.damage);
      if (r === "cancel") {
        ev.cancel = true;
        return;
      }
      if (typeof r === "number") ev.damage = r;
    }
    if (!(attacker instanceof Player) || src.cause !== EntityDamageCause.entityAttack) return;
    // 3) shatter: melee on a frozen target breaks the ice for bonus damage
    if (isFrozen(target)) {
      ev.damage += 3;
      system.run(() => {
        if (alive(target)) shatter(target);
      });
    }
    // 4) drawn sword-cane cuts: constitution + armour, precision on the neck
    if (hooks.held.get(attacker.id) === ID.caneDrawn) {
      const vital = vitalAim(attacker, target);
      const info = cutMultiplier(attacker, target, vital);
      ev.damage = Math.max(0.5, ev.damage * info.mult);
      system.run(() => hooks.onCut(attacker, target, info));
    }
  });
}
