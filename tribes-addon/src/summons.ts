import { Entity, EntityTameableComponent, Player, Vector3, world } from "@minecraft/server";
import { enemiesNear, heal, hurt } from "./core/combat.js";
import { beam, burst, center, flare, noodleLine, sound } from "./core/fx.js";
import { now } from "./core/state.js";
import { add, v } from "./core/vec.js";

/**
 * Guardians summoned by ultimates. Walking guardians (raptor, lamassu) use
 * their own behaviour-pack AI and are tamed to their owner; floating ones
 * (drone, noodle avatar) are puppeted every tick by this module.
 */
type Kind = "raptor" | "lamassu" | "drone" | "noodle_avatar";

interface Summon {
  entity: Entity;
  kind: Kind;
  ownerId: string;
  expires: number;
  index: number;
  nextAction: number;
}

const summons = new Map<string, Summon>();

export function spawnSummon(owner: Player, kind: Kind, at: Vector3, lifetimeTicks: number, index = 0): Entity | undefined {
  let e: Entity;
  try {
    e = owner.dimension.spawnEntity(`tribes:${kind}`, at);
  } catch (err) {
    console.warn(`[tribes] could not spawn ${kind}: ${err}`);
    return undefined;
  }
  e.setDynamicProperty("tribes:owner", owner.id);
  e.nameTag = `${owner.name}'s ${kindLabel(kind)}`;
  if (kind === "raptor" || kind === "lamassu") {
    try {
      e.getComponent(EntityTameableComponent.componentId)?.tame(owner);
    } catch {
      // tame() unavailable: the summon still fights monsters on its own
    }
    try {
      e.triggerEvent("tribes:on_tame");
    } catch {
      // already tamed through the tame event
    }
  }
  summons.set(e.id, { entity: e, kind, ownerId: owner.id, expires: now() + lifetimeTicks, index, nextAction: now() + 20 + index * 10 });
  burst(owner.dimension, kind === "drone" ? "cyan" : kind === "noodle_avatar" ? "noodle" : kind === "lamassu" ? "gold" : "green", add(at, v(0, 1, 0)));
  return e;
}

function kindLabel(kind: Kind): string {
  switch (kind) {
    case "raptor":
      return "Raptor";
    case "lamassu":
      return "Lamassu";
    case "drone":
      return "Drone";
    default:
      return "Noodly Avatar";
  }
}

function dismiss(s: Summon): void {
  summons.delete(s.entity.id);
  if (!s.entity.isValid) return;
  try {
    burst(s.entity.dimension, "white", center(s.entity));
    s.entity.remove();
  } catch {
    // already gone
  }
}

function ownerOf(s: Summon): Player | undefined {
  const p = world.getEntity(s.ownerId);
  return p instanceof Player && p.isValid ? p : undefined;
}

/** Called every tick. */
export function tickSummons(): void {
  const t = now();
  for (const s of [...summons.values()]) {
    if (!s.entity.isValid) {
      summons.delete(s.entity.id);
      continue;
    }
    const owner = ownerOf(s);
    if (t >= s.expires || (!owner && (s.kind === "drone" || s.kind === "noodle_avatar"))) {
      dismiss(s);
      continue;
    }
    if (!owner) continue;
    switch (s.kind) {
      case "drone":
        tickDrone(s, owner, t);
        break;
      case "noodle_avatar":
        tickAvatar(s, owner, t);
        break;
      default:
        if (t % 20 === 0) leash(s, owner);
    }
  }
}

/** Walking guardians teleport back if they fall too far behind or change dimension. */
function leash(s: Summon, owner: Player): void {
  const e = s.entity;
  const far = e.dimension.id !== owner.dimension.id || distance(e.location, owner.location) > 28;
  if (far) {
    e.teleport(add(owner.location, v(Math.random() * 2 - 1, 0.2, Math.random() * 2 - 1)), { dimension: owner.dimension });
  }
}

function distance(a: Vector3, b: Vector3): number {
  return Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
}

function tickDrone(s: Summon, owner: Player, t: number): void {
  const a = t * 0.06 + s.index * Math.PI;
  const target = add(owner.location, v(Math.cos(a) * 2.4, 2.3 + Math.sin(t * 0.1 + s.index) * 0.25, Math.sin(a) * 2.4));
  const enemies = t >= s.nextAction ? enemiesNear(owner.dimension, owner.location, 16, owner, 1) : [];
  const facing = enemies[0]?.location ?? add(owner.location, add(owner.getViewDirection(), v(0, 1.6, 0)));
  s.entity.teleport(target, { dimension: owner.dimension, facingLocation: facing });
  if (t >= s.nextAction) {
    s.nextAction = t + 20;
    const foe = enemies[0];
    if (foe) {
      const from = add(target, v(0, 0.3, 0));
      beam(owner.dimension, "cyan", from, center(foe), 0.3);
      flare(owner.dimension, "cyan", center(foe));
      sound(owner.dimension, "mob.shulker.shoot", from, 0.6, 1.8);
      hurt(foe, 5, owner);
    }
  }
}

function tickAvatar(s: Summon, owner: Player, t: number): void {
  const yaw = (owner.getRotation().y * Math.PI) / 180;
  const behind = v(Math.sin(yaw) * 2.2, 3.6, -Math.cos(yaw) * 2.2);
  const target = add(owner.location, behind);
  s.entity.teleport(target, { dimension: owner.dimension, rotation: { x: 0, y: owner.getRotation().y } });
  if (t >= s.nextAction) {
    s.nextAction = t + 30;
    const grab = enemiesNear(owner.dimension, target, 14, owner, 2);
    for (const foe of grab) {
      noodleLine(owner.dimension, add(target, v(0, 0.5, 0)), center(foe), t * 0.3);
      burst(owner.dimension, "sauce", center(foe));
      try {
        foe.addEffect("levitation", 20, { amplifier: 3, showParticles: false });
      } catch {
        // immune
      }
      hurt(foe, 6, owner);
      heal(owner, 2);
    }
    if (grab.length) sound(owner.dimension, "mob.slime.big", target, 1, 0.6);
  }
}

export function summonCount(owner: Player, kind: Kind): number {
  let n = 0;
  for (const s of summons.values()) if (s.ownerId === owner.id && s.kind === kind && s.entity.isValid) n++;
  return n;
}

export function dismissAll(owner: Player): void {
  for (const s of [...summons.values()]) if (s.ownerId === owner.id) dismiss(s);
}

/** After a reload, script-driven summons lose their puppeteer; clean them up. */
export function sweepOrphans(): void {
  for (const dimId of ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"]) {
    let dim;
    try {
      dim = world.getDimension(dimId);
    } catch {
      continue;
    }
    for (const type of ["tribes:drone", "tribes:noodle_avatar"]) {
      for (const e of dim.getEntities({ type })) {
        if (!summons.has(e.id)) {
          try {
            e.remove();
          } catch {
            // ignore
          }
        }
      }
    }
  }
}
