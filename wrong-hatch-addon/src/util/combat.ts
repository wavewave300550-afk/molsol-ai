import { Difficulty, Dimension, Entity, EntityDamageCause, GameMode, Player, Vector3, world } from "@minecraft/server";
import { hdist, hnorm, sub } from "./vec.js";

/** Players that can be hurt (survival / adventure, alive) within a radius. */
export function targetsNear(dim: Dimension, at: Vector3, radius: number): Player[] {
  try {
    return dim
      .getPlayers({ location: at, maxDistance: radius, excludeGameModes: [GameMode.Creative, GameMode.Spectator] })
      .filter((p) => p.isValid);
  } catch {
    return [];
  }
}

/** Every player (any game mode) in range - used for HUD messages. */
export function viewersNear(dim: Dimension, at: Vector3, radius: number): Player[] {
  try {
    return dim.getPlayers({ location: at, maxDistance: radius });
  } catch {
    return [];
  }
}

export function difficultyMul(): number {
  switch (world.getDifficulty()) {
    case Difficulty.Easy:
      return 0.7;
    case Difficulty.Hard:
      return 1.3;
    default:
      return 1;
  }
}

export interface HitOptions {
  knock?: number; // horizontal knockback strength away from `from`
  lift?: number; // vertical knockback
  from?: Vector3;
  cause?: EntityDamageCause;
  fire?: number; // seconds
}

/** Damage an entity on behalf of `attacker` with difficulty scaling and optional knockback. */
export function hit(attacker: Entity | undefined, victim: Entity, amount: number, mul: number, opt: HitOptions = {}): boolean {
  if (!victim.isValid) return false;
  let ok = false;
  try {
    const dmg = Math.max(1, Math.round(amount * mul * difficultyMul()));
    ok = victim.applyDamage(dmg, {
      cause: opt.cause ?? EntityDamageCause.entityAttack,
      damagingEntity: attacker && attacker.isValid ? attacker : undefined,
    });
    if (opt.fire) victim.setOnFire(opt.fire, true);
    if ((opt.knock || opt.lift) && opt.from) {
      const d = hnorm(sub(victim.location, opt.from));
      victim.applyKnockback({ x: d.x * (opt.knock ?? 0), z: d.z * (opt.knock ?? 0) }, opt.lift ?? 0.2);
    }
  } catch {
    // victim died mid-call or was unloaded
  }
  return ok;
}

export function horizontalWithin(a: Vector3, b: Vector3, r: number, dy = 3): boolean {
  return hdist(a, b) <= r && Math.abs(a.y - b.y) <= dy;
}
