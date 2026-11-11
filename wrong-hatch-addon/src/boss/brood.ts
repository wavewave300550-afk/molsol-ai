/**
 * The boss's brood: hatch eggs (mortar + rotten), Wrong Chicks and golden
 * Yolkling bombers. Eggs carry a hidden outcome that is revealed shortly
 * before hatching (colour + particles), so players can react: smash gilded
 * eggs, flee red-sparking ones, burst rotten ones early.
 */
import { Dimension, Entity, Player, Vector3 } from "@minecraft/server";
import { CHICK_ID, DMG, EGG_ID } from "../config.js";
import { hit, targetsNear } from "../util/combat.js";
import { particle, ring, sound } from "../util/fx.js";
import { add, dist, v3 } from "../util/vec.js";
import { addHazard, RotCloud } from "./hazards.js";

/** Minimal view of a boss controller used by brood logic (avoids an import cycle). */
export interface BossLink {
  readonly id: string;
  readonly entity: Entity;
  readonly phase: number;
  dim(): Dimension;
  dmgMul(): number;
  chickCap(): number;
  healFraction(f: number): void;
}

export type EggOutcome = "chick" | "yolkling" | "blast" | "rotten" | "gilded";
type EggKind = "mortar" | "rotten";

interface EggRec {
  ent: Entity;
  boss: BossLink;
  kind: EggKind;
  outcome: EggOutcome;
  hatchAt: number;
  revealed: boolean;
  bornAt: number;
}

const eggs = new Map<string, EggRec>();
const chicks = new Map<string, { ent: Entity; owner: string; yolkling: boolean; fuseAt: number }>();

export function chickCount(owner: string): number {
  let n = 0;
  for (const c of chicks.values()) if (c.owner === owner && c.ent.isValid) n++;
  return n;
}

export function eggCount(owner: string): number {
  let n = 0;
  for (const e of eggs.values()) if (e.boss.id === owner) n++;
  return n;
}

function rollOutcome(phase: number): EggOutcome {
  const r = Math.random();
  if (r < 0.4) return phase >= 2 && Math.random() < 0.35 ? "yolkling" : "chick";
  if (r < 0.65) return "blast";
  if (r < 0.82) return "rotten";
  return "gilded";
}

export function spawnChick(boss: BossLink, at: Vector3, yolkling = false): Entity | undefined {
  if (chickCount(boss.id) >= boss.chickCap()) return undefined;
  try {
    const e = boss.dim().spawnEntity(CHICK_ID, at);
    if (yolkling) e.triggerEvent("wh:become_yolkling");
    chicks.set(e.id, { ent: e, owner: boss.id, yolkling, fuseAt: -1 });
    particle(boss.dim(), "wh:shell_chip", at);
    sound(boss.dim(), "wrong_hatch.chick", at, 1, yolkling ? 1.3 : 1);
    return e;
  } catch {
    return undefined;
  }
}

/** A mortar egg with a hidden outcome, hatching after `delay` ticks. */
export function layEgg(boss: BossLink, at: Vector3, now: number, kind: EggKind, delay: number): Entity | undefined {
  try {
    const e = boss.dim().spawnEntity(EGG_ID, at);
    if (kind === "rotten") {
      e.triggerEvent("wh:rotten");
      e.setProperty("wh:kind", 1);
    }
    eggs.set(e.id, {
      ent: e,
      boss,
      kind,
      outcome: kind === "rotten" ? "rotten" : rollOutcome(boss.phase),
      hatchAt: now + delay,
      revealed: kind === "rotten",
      bornAt: now,
    });
    return e;
  } catch {
    return undefined;
  }
}

function blast(boss: BossLink, at: Vector3, radius: number, dmg: number): void {
  const dim = boss.dim();
  particle(dim, "wh:gold_burst", add(at, v3(0, 0.5, 0)));
  particle(dim, "wh:ember", add(at, v3(0, 0.5, 0)));
  particle(dim, "minecraft:huge_explosion_emitter", at);
  sound(dim, "random.explode", at, 1.2, 1.4);
  for (const p of targetsNear(dim, at, radius)) {
    if (dist(p.location, at) <= radius) hit(boss.entity, p, dmg, boss.dmgMul(), { from: at, knock: 0.9, lift: 0.45 });
  }
}

function hatch(rec: EggRec): void {
  const dim = rec.boss.dim();
  const at = rec.ent.location;
  sound(dim, "wrong_hatch.crack_big", at, 1, 1.3);
  particle(dim, "wh:shell_burst", add(at, v3(0, 0.4, 0)));
  switch (rec.outcome) {
    case "chick":
    case "yolkling":
      if (!spawnChick(rec.boss, at, rec.outcome === "yolkling")) blast(rec.boss, at, 2.5, DMG.eggBlast * 0.6);
      break;
    case "blast":
      blast(rec.boss, at, 3.2, DMG.eggBlast);
      break;
    case "rotten":
      addHazard(new RotCloud(rec.boss.id, dim, at, rec.kind === "rotten" ? 4.0 : 2.6, rec.kind === "rotten" ? 120 : 90, rec.kind === "rotten" ? 1 : 0));
      if (rec.kind === "rotten") spawnChick(rec.boss, at, false);
      break;
    case "gilded":
      // an un-smashed gilded egg feeds the boss
      rec.boss.healFraction(0.02);
      particle(dim, "wh:heal", add(at, v3(0, 0.5, 0)));
      if (rec.boss.entity.isValid) particle(dim, "wh:heal", add(rec.boss.entity.location, v3(0, 2.5, 0)));
      break;
  }
}

/** Called when a player breaks an egg before it hatches. */
export function smashEgg(id: string, killer: Entity | undefined): void {
  const rec = eggs.get(id);
  if (!rec) return;
  eggs.delete(id);
  const dim = rec.boss.dim();
  const at = rec.ent.isValid ? rec.ent.location : killer?.location;
  if (!at) return;
  particle(dim, "wh:shell_chip", add(at, v3(0, 0.4, 0)));
  sound(dim, "wrong_hatch.crack", at, 1, 1.4);
  switch (rec.outcome) {
    case "gilded":
      if (killer instanceof Player) {
        try {
          killer.addEffect("regeneration", 100, { amplifier: 1 });
          killer.addEffect("absorption", 1200, { amplifier: 1 });
          killer.onScreenDisplay.setActionBar("§6Gilded egg smashed! §e+Regeneration +Absorption");
        } catch {
          // ignore
        }
      }
      particle(dim, "wh:heal", add(at, v3(0, 0.5, 0)));
      break;
    case "blast":
      blast(rec.boss, at, 2.2, DMG.eggBlast * 0.5); // a smaller pop: still dangerous up close
      break;
    case "rotten":
      if (killer instanceof Player) {
        try {
          killer.addEffect("nausea", 60, { amplifier: 0 });
        } catch {
          // ignore
        }
      }
      particle(dim, "wh:rot_cloud", at);
      break;
    default:
      particle(dim, "wh:feather_fall", at);
  }
}

export function tickBrood(now: number): void {
  for (const [id, rec] of eggs) {
    if (!rec.ent.isValid) {
      eggs.delete(id);
      continue;
    }
    const dim = rec.boss.dim();
    const at = rec.ent.location;
    // reveal ~0.9 s before hatching
    if (!rec.revealed && now >= rec.hatchAt - 18) {
      rec.revealed = true;
      const kind = rec.outcome === "rotten" ? 1 : rec.outcome === "gilded" ? 2 : rec.outcome === "blast" ? 3 : 0;
      try {
        rec.ent.setProperty("wh:kind", kind);
      } catch {
        // ignore
      }
    }
    if (rec.revealed && now % 4 === 0) {
      const id2 = { blast: "wh:ember", gilded: "wh:gold_mote", rotten: "wh:stink", chick: "wh:feather_fall", yolkling: "wh:gold_burst" }[rec.outcome];
      particle(dim, id2, add(at, v3(0, 0.9, 0)));
      if (rec.outcome === "blast") ring(dim, at, 3.2, true);
    }
    if (rec.kind === "rotten" && now % 20 === 0) {
      particle(dim, "wh:stink", add(at, v3(0, 1, 0)));
      for (const p of targetsNear(dim, at, 2.6)) {
        try {
          p.addEffect("poison", 40, { amplifier: 0 });
        } catch {
          // ignore
        }
      }
    }
    if (now >= rec.hatchAt) {
      eggs.delete(id);
      try {
        hatch(rec);
      } catch (e) {
        console.warn(`[wrong_hatch] hatch failed: ${e}`);
      }
      try {
        rec.ent.remove();
      } catch {
        // ignore
      }
    }
  }
  // yolkling fuses
  for (const [id, c] of chicks) {
    if (!c.ent.isValid) {
      chicks.delete(id);
      continue;
    }
    if (!c.yolkling) continue;
    const dim = c.ent.dimension;
    if (c.fuseAt < 0) {
      const near = targetsNear(dim, c.ent.location, 2.4);
      if (near.length) {
        c.fuseAt = now + 24;
        try {
          c.ent.setProperty("wh:fuse", true);
        } catch {
          // ignore
        }
        sound(dim, "random.fuse", c.ent.location, 1, 1.6);
      }
    } else if (now >= c.fuseAt) {
      const at = c.ent.location;
      chicks.delete(id);
      particle(dim, "wh:gold_burst", add(at, v3(0, 0.4, 0)));
      particle(dim, "minecraft:huge_explosion_emitter", at);
      sound(dim, "random.explode", at, 1, 1.5);
      const owner = c.ent;
      for (const p of targetsNear(dim, at, 3.2)) hit(owner, p, DMG.yolklingBlast, 1, { from: at, knock: 1.0, lift: 0.5 });
      try {
        c.ent.remove();
      } catch {
        // ignore
      }
    } else if (now % 4 === 0) {
      particle(dim, "wh:ember", add(c.ent.location, v3(0, 0.6, 0)));
    }
  }
}

/** Remove every egg and chick that belongs to a boss (death / reset / despawn). */
export function clearBrood(owner: string): void {
  for (const [id, rec] of eggs) {
    if (rec.boss.id !== owner) continue;
    eggs.delete(id);
    if (rec.ent.isValid) {
      try {
        particle(rec.ent.dimension, "wh:shell_chip", rec.ent.location);
        rec.ent.remove();
      } catch {
        // ignore
      }
    }
  }
  for (const [id, c] of chicks) {
    if (c.owner !== owner) continue;
    chicks.delete(id);
    if (c.ent.isValid) {
      try {
        particle(c.ent.dimension, "wh:feather_burst", c.ent.location);
        c.ent.triggerEvent("wh:despawn");
      } catch {
        // ignore
      }
    }
  }
}

export function isTrackedEgg(id: string): boolean {
  return eggs.has(id);
}
