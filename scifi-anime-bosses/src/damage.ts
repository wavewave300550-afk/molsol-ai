import { Entity, EntityDamageCause, EntityHurtBeforeEvent, system, world } from "@minecraft/server";
import { PHASE } from "./generated/ids.js";
import { bosses, clock, ledgerTake, minions, parts, throttle } from "./registry.js";
import type { Vesper } from "./boss/controller.js";
import { particle, sound } from "./util/fx.js";
import { add, mul, norm, sub } from "./util/vec.js";

const PASS_THROUGH = new Set<string>([EntityDamageCause.override, EntityDamageCause.selfDestruct, "void"]);

function isOwnSource(src: Entity | undefined): boolean {
  return !!src && src.typeId.startsWith("sab:");
}

function feedback(v: Vesper, kind: "shield" | "hull" | "heart", attacker: Entity | undefined, at?: { x: number; y: number; z: number }): void {
  const key = `${attacker?.id ?? "env"}|${kind}`;
  if (!throttle(key, clock.now, kind === "heart" ? 4 : 8)) return;
  system.run(() => {
    if (!v.boss.isValid) return;
    let p = at ?? v.core();
    if (!at && attacker && attacker.isValid) {
      // put the spark on the side facing the attacker
      p = add(p, mul(norm(sub(attacker.location, p)), 3));
    }
    if (kind === "shield") {
      particle(v.dim, "shield_spark", p);
      sound(v.dim, "shield", p, 1.0, 1.0 + Math.random() * 0.2);
    } else if (kind === "heart") {
      particle(v.dim, "heart_hit", p);
      sound(v.dim, "hurt_flesh", p, 1.0, 1.2);
    } else {
      particle(v.dim, "hull_spark", p);
      sound(v.dim, v.phase >= PHASE.p2 ? "hurt_flesh" : "hurt_hull", p, 0.9, 0.9 + Math.random() * 0.2);
    }
  });
}

function onHurt(ev: EntityHurtBeforeEvent): void {
  const e = ev.hurtEntity;
  const src = ev.damageSource;
  const cause = src.cause;
  const attacker = src.damagingEntity;

  // ---- the boss itself (direct hull hits)
  const v = bosses.get(e.id);
  if (v) {
    if (PASS_THROUGH.has(cause)) return;
    if (ledgerTake(v.id, ev.damage, clock.now)) return; // forwarded & already scaled
    if (v.invulnerable || v.dying || isOwnSource(attacker)) {
      ev.cancel = true;
      if (!isOwnSource(attacker)) feedback(v, "shield", attacker);
      return;
    }
    // every hit is pooled and applied by the controller (see Vesper.queueDamage)
    ev.cancel = true;
    const dmg = v.queueDamage(ev.damage * v.multiplierFor("hull", cause), attacker, cause);
    if (dmg > 0) feedback(v, "hull", attacker);
    return;
  }

  // ---- proxy hitboxes: cancel and forward to the owner
  const part = parts.get(e.id);
  if (part) {
    ev.cancel = true;
    const owner = part.owner;
    if (!owner.boss.isValid || isOwnSource(attacker) || PASS_THROUGH.has(cause)) return;
    if (owner.invulnerable || owner.dying) {
      feedback(owner, "shield", attacker, e.location);
      return;
    }
    const amount = ev.damage * owner.multiplierFor(part.kind, cause);
    const exposed = part.kind === "heart" && owner.heartOpen;
    const at = { x: e.location.x, y: e.location.y + 1.5, z: e.location.z };
    if (owner.queueDamage(amount, attacker, cause) > 0) feedback(owner, exposed ? "heart" : "hull", attacker, at);
    return;
  }

  // ---- helpers (drones, orbs, censers, seraphs, cover plates ...)
  const m = minions.get(e.id);
  if (m) {
    if (PASS_THROUGH.has(cause)) return;
    const r = m.hurt(ev.damage, attacker, cause);
    ev.cancel = r.cancel;
    if (!r.cancel && r.damage !== undefined) ev.damage = r.damage;
    return;
  }

  // ---- unknown/orphaned add-on entities are never harmed except by /kill or the void
  if (e.typeId.startsWith("sab:") && !PASS_THROUGH.has(cause)) ev.cancel = true;
}

export function registerDamage(): void {
  world.beforeEvents.entityHurt.subscribe(onHurt, { entityFilter: { families: ["sab_vesper"] } });
}
