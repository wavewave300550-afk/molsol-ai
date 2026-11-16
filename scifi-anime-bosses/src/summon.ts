import {
  Dimension, EquipmentSlot, GameMode, ItemComponentCompleteUseEvent, Player, Vector3,
} from "@minecraft/server";
import { Vesper } from "./boss/controller.js";
import { startArrival } from "./boss/sequences.js";
import { ENT } from "./generated/ids.js";
import { bosses } from "./registry.js";
import { COLORS, particle, sound } from "./util/fx.js";
import { hdist } from "./util/vec.js";
import { groundY, isPeaceful, spectators } from "./util/world.js";

interface Ritual {
  dim: Dimension;
  at: Vector3;
  t: number;
  by: string;
}

const rituals: Ritual[] = [];
export const RITUAL_TICKS = 160;

function deny(p: Player, msg: string): void {
  try {
    p.onScreenDisplay.setActionBar(`§c${msg}`);
    p.playSound("note.bass", { volume: 0.8, pitch: 0.6 });
  } catch {
    /* ignore */
  }
}

/** Reasons the hymn cannot be played here (undefined = allowed). */
export function summonBlocker(p: Player, at: Vector3): string | undefined {
  if (p.dimension.id !== "minecraft:overworld") return "The Psalter's hymn only reaches the stars from the Overworld.";
  if (isPeaceful()) return "VESPER-0 does not answer in Peaceful difficulty.";
  for (const v of bosses.values()) {
    if (v.dim.id === p.dimension.id && hdist(v.pos, at) < 256) return "VESPER-0 is already listening nearby.";
  }
  for (const r of rituals) if (hdist(r.at, at) < 64) return "A hymn is already being sung here.";
  try {
    const top = p.dimension.getTopmostBlock({ x: at.x, z: at.z });
    if (top && top.location.y > at.y + 1.5) return "You must stand beneath the open sky.";
  } catch {
    return "The sky here cannot be reached.";
  }
  return undefined;
}

export function onPsalterComplete(ev: ItemComponentCompleteUseEvent): void {
  const p = ev.source;
  if (!(p instanceof Player)) return;
  const at = { x: Math.floor(p.location.x) + 0.5, y: p.location.y, z: Math.floor(p.location.z) + 0.5 };
  const why = summonBlocker(p, at);
  if (why) {
    deny(p, why);
    return;
  }
  // consume one Psalter (not in creative)
  try {
    if (p.getGameMode() !== GameMode.Creative) {
      const eq = p.getComponent("minecraft:equippable");
      const item = eq?.getEquipment(EquipmentSlot.Mainhand);
      if (item && item.typeId === ev.itemStack.typeId) {
        if (item.amount > 1) {
          item.amount -= 1;
          eq!.setEquipment(EquipmentSlot.Mainhand, item);
        } else {
          eq!.setEquipment(EquipmentSlot.Mainhand, undefined);
        }
      }
    }
  } catch {
    /* ignore */
  }
  rituals.push({ dim: p.dimension, at, t: 0, by: p.name });
  sound(p.dimension, "psalter", at, 2.0);
  for (const s of spectators(p.dimension, at, 96)) {
    try {
      s.sendMessage(`§b${p.name} §7plays the Astral Psalter. §oA hymn climbs toward the stars...`);
    } catch {
      /* ignore */
    }
  }
}

export function summonNow(dim: Dimension, at: Vector3): Vesper | undefined {
  const gy = groundY(dim, at.x, at.z, at.y);
  const spawnAt = { x: at.x, y: Math.min(dim.heightRange.max - 20, gy + 46), z: at.z };
  try {
    const boss = dim.spawnEntity(ENT.boss, spawnAt, { initialRotation: Math.random() * 360 });
    const v = new Vesper(boss, { x: at.x, y: gy, z: at.z });
    v.persist();
    startArrival(v);
    return v;
  } catch (e) {
    console.warn(`[VESPER-0] summon failed: ${e}`);
    return undefined;
  }
}

export function tickRituals(): void {
  for (const r of rituals) {
    r.t++;
    const t = r.t;
    if (t % 20 === 1) particle(r.dim, "summon_pillar", r.at);
    if (t % 25 === 5) particle(r.dim, "glyph_rise", { x: r.at.x, y: r.at.y + 0.5, z: r.at.z });
    if (t === 60) sound(r.dim, "choir", r.at, 1.6, 1.2);
    if (t === 110) {
      particle(r.dim, "summon_flash", { x: r.at.x, y: r.at.y + 40, z: r.at.z });
      particle(r.dim, "light_pillar", r.at, { height: 40, life: 2.5 }, COLORS.cyan);
      sound(r.dim, "arrive", r.at, 1.2, 1.3);
    }
    if (t === RITUAL_TICKS) summonNow(r.dim, r.at);
  }
  for (let i = rituals.length - 1; i >= 0; i--) if (rituals[i].t >= RITUAL_TICKS) rituals.splice(i, 1);
}

export function activeRituals(): number {
  return rituals.length;
}

