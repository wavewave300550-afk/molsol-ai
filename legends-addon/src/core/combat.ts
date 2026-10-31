/**
 * Who bosses can hit, how hard, and the hit-shape tests shared by every skill.
 */
import {
  Difficulty,
  Dimension,
  Entity,
  EntityDamageCause,
  EntityHealthComponent,
  GameMode,
  Player,
  Vector3,
  system,
  world,
} from "@minecraft/server";
import { add, dirOfYaw, flatDir, flatSegDist, scale, yawOf, angleDiff } from "./vec.js";

export function isFighter(p: Player): boolean {
  if (!p.isValid) return false;
  try {
    const gm = p.getGameMode();
    if (gm === GameMode.Creative || gm === GameMode.Spectator) return false;
    const h = p.getComponent(EntityHealthComponent.componentId);
    return !h || h.currentValue > 0;
  } catch {
    return false;
  }
}

export function fightersNear(dim: Dimension, at: Vector3, radius: number): Player[] {
  try {
    return dim.getPlayers({ location: at, maxDistance: radius }).filter(isFighter);
  } catch {
    return [];
  }
}

export function allPlayersNear(dim: Dimension, at: Vector3, radius: number): Player[] {
  try {
    return dim.getPlayers({ location: at, maxDistance: radius });
  } catch {
    return [];
  }
}

let diffTick = -1000;
let diffMul = 1;
/** Boss damage multiplier from world difficulty. */
export function difficultyMul(): number {
  if (system.currentTick - diffTick > 100) {
    diffTick = system.currentTick;
    let d: Difficulty = Difficulty.Normal;
    try {
      d = world.getDifficulty();
    } catch {
      // keep normal
    }
    diffMul = d === Difficulty.Easy ? 0.6 : d === Difficulty.Hard ? 1.35 : d === Difficulty.Peaceful ? 0.35 : 1.0;
  }
  return diffMul;
}

export function hurt(p: Entity, amount: number, src?: Entity, cause: EntityDamageCause = EntityDamageCause.entityAttack): void {
  if (!p.isValid) return;
  const dmg = Math.max(0.5, amount * difficultyMul());
  try {
    if (src && src.isValid) p.applyDamage(dmg, { cause, damagingEntity: src });
    else p.applyDamage(dmg, { cause });
  } catch {
    // cannot be damaged right now (respawning etc.)
  }
}

/** Knock away from `from` (negative strength pulls towards it). */
export function knock(p: Entity, from: Vector3, strength: number, vertical: number): void {
  if (!p.isValid) return;
  const d = flatDir(from, p.location);
  try {
    p.applyKnockback({ x: d.x * strength, z: d.z * strength }, vertical);
  } catch {
    // some entities refuse knockback
  }
}

export function effect(p: Entity, id: string, ticks: number, amplifier = 0): void {
  if (!p.isValid) return;
  try {
    p.addEffect(id, Math.max(1, Math.round(ticks)), { amplifier, showParticles: false });
  } catch {
    // ignore
  }
}

// ------------------------------------------------------------------ shapes (feet position based)

const feet = (p: Entity): Vector3 => p.location;

export function inCircle(p: Entity, c: Vector3, r: number, height = 4): boolean {
  const l = feet(p);
  return Math.hypot(l.x - c.x, l.z - c.z) <= r && l.y >= c.y - 1.5 && l.y <= c.y + height;
}

export function inRingBand(p: Entity, c: Vector3, rIn: number, rOut: number, height = 4): boolean {
  const l = feet(p);
  const d = Math.hypot(l.x - c.x, l.z - c.z);
  return d >= rIn && d <= rOut && l.y >= c.y - 1.5 && l.y <= c.y + height;
}

export function inCone(p: Entity, apex: Vector3, dir: Vector3, angle: number, range: number, height = 4): boolean {
  const l = feet(p);
  const d = Math.hypot(l.x - apex.x, l.z - apex.z);
  if (d > range || l.y < apex.y - 2 || l.y > apex.y + height) return false;
  if (d < 1.2) return true;
  return Math.abs(angleDiff(yawOf(dir), yawOf(flatDir(apex, l)))) <= angle / 2;
}

export function inLine(p: Entity, from: Vector3, dir: Vector3, length: number, width: number, height = 4): boolean {
  const l = feet(p);
  const to = add(from, scale(dirOfYaw(yawOf(dir)), length));
  const { d } = flatSegDist(l, from, to);
  return d <= width / 2 && l.y >= Math.min(from.y, to.y) - 2 && l.y <= Math.max(from.y, to.y) + height;
}

/** Is the player standing on the ground (used for jumpable shockwaves)? */
export function grounded(p: Player): boolean {
  try {
    return p.isOnGround;
  } catch {
    return true;
  }
}

export function healthOf(e: Entity): { cur: number; max: number } {
  try {
    const h = e.getComponent(EntityHealthComponent.componentId);
    if (h) return { cur: h.currentValue, max: h.effectiveMax };
  } catch {
    // ignore
  }
  return { cur: 0, max: 1 };
}

export function setHealth(e: Entity, value: number): void {
  try {
    const h = e.getComponent(EntityHealthComponent.componentId);
    if (h) h.setCurrentValue(Math.max(1, Math.min(h.effectiveMax, value)));
  } catch {
    // ignore
  }
}
