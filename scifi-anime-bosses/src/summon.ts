import {
  Dimension, EquipmentSlot, GameMode, ItemComponentUseEvent, ItemStack, Player, Vector3, world,
} from "@minecraft/server";
import { Vesper } from "./boss/controller.js";
import { startArrival } from "./boss/sequences.js";
import { ENT, ITEMS } from "./generated/ids.js";
import { bosses } from "./registry.js";
import { COLORS, particle, sound } from "./util/fx.js";
import { hdist } from "./util/vec.js";
import { groundY, isPeaceful, spectators } from "./util/world.js";

interface Ritual {
  dim: Dimension;
  at: Vector3;
  t: number;
  by: string; // summoner name
  pid: string; // summoner id: the Psalter is taken from them only once VESPER-0 has actually arrived
}

const rituals: Ritual[] = [];
export const RITUAL_TICKS = 160;

function deny(p: Player, msg: string): void {
  if (!msg) return;
  try {
    p.onScreenDisplay.setActionBar(`§c${msg}`);
    p.sendMessage(`§c[VESPER-0] §f${msg}`);
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

/** Using the Astral Psalter (tap on touch screens, right-click with a mouse, LT on a controller) starts the hymn. */
export function onPsalterUse(ev: ItemComponentUseEvent): void {
  const p = ev.source;
  if (!(p instanceof Player)) return;
  const at = { x: Math.floor(p.location.x) + 0.5, y: p.location.y, z: Math.floor(p.location.z) + 0.5 };
  const why = summonBlocker(p, at);
  if (why) {
    deny(p, why);
    return;
  }
  rituals.push({ dim: p.dimension, at, t: 0, by: p.name, pid: p.id });
  sound(p.dimension, "psalter", at, 2.0);
  for (const s of spectators(p.dimension, at, 96)) {
    try {
      s.sendMessage(`§b${p.name} §7plays the Astral Psalter. §oA hymn climbs toward the stars...`);
    } catch {
      /* ignore */
    }
  }
}

/** Take one Astral Psalter from the player (main hand first, then the inventory). */
function takePsalter(p: Player): boolean {
  try {
    const eq = p.getComponent("minecraft:equippable");
    const hand = eq?.getEquipment(EquipmentSlot.Mainhand);
    if (eq && hand && hand.typeId === ITEMS.psalter) {
      if (hand.amount > 1) {
        hand.amount -= 1;
        eq.setEquipment(EquipmentSlot.Mainhand, hand);
      } else {
        eq.setEquipment(EquipmentSlot.Mainhand, undefined);
      }
      return true;
    }
    const c = p.getComponent("minecraft:inventory")?.container;
    if (!c) return false;
    for (let i = 0; i < c.size; i++) {
      const it = c.getItem(i);
      if (!it || it.typeId !== ITEMS.psalter) continue;
      if (it.amount > 1) {
        it.amount -= 1;
        c.setItem(i, it);
      } else {
        c.setItem(i, undefined);
      }
      return true;
    }
  } catch {
    /* ignore */
  }
  return false;
}

/** The hymn ends without an answer; nothing is consumed. */
function fizzle(r: Ritual, p: Player | undefined, why: string): void {
  particle(r.dim, "dust", r.at);
  if (p) deny(p, why);
}

/** End of the ritual: VESPER-0 arrives, and only then is the Psalter consumed (never in creative). */
function completeRitual(r: Ritual): void {
  const e = world.getEntity(r.pid);
  const p = e && e.isValid && e.typeId === "minecraft:player" ? (e as Player) : undefined;
  if (!p) return fizzle(r, undefined, "");
  let loaded = true;
  try {
    loaded = r.dim.isChunkLoaded(r.at);
  } catch {
    loaded = false;
  }
  if (!loaded) return fizzle(r, p, "The hymn faded: you left the ritual site.");
  let creative = false;
  try {
    creative = p.getGameMode() === GameMode.Creative;
  } catch {
    /* ignore */
  }
  if (!creative && !takePsalter(p)) return fizzle(r, p, "The hymn falters: the Astral Psalter is gone.");
  if (summonNow(r.dim, r.at)) return;
  // the boss could not be spawned: give the Psalter back
  if (!creative) {
    try {
      const left = p.getComponent("minecraft:inventory")?.container?.addItem(new ItemStack(ITEMS.psalter, 1));
      if (left) p.dimension.spawnItem(left, p.location);
    } catch {
      /* ignore */
    }
  }
  fizzle(r, p, "The stars did not answer. Your Psalter is returned.");
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
    if (t === RITUAL_TICKS) completeRitual(r);
  }
  for (let i = rituals.length - 1; i >= 0; i--) if (rituals[i].t >= RITUAL_TICKS) rituals.splice(i, 1);
}

export function activeRituals(): number {
  return rituals.length;
}

// ------------------------------------------------------------------ held-item hints
// While a player holds the Psalter, the action bar says whether the hymn can be played right here (and why not);
// picking up the Orison Halo explains its throw. This also makes it obvious in game that the scripts are running.
const lastHeld = new Map<string, string>();
const haloHintAt = new Map<string, number>();

function heldItem(p: Player): string | undefined {
  try {
    return p.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Mainhand)?.typeId;
  } catch {
    return undefined;
  }
}

function busyNear(p: Player): boolean {
  for (const v of bosses.values()) if (v.dim.id === p.dimension.id && hdist(v.pos, p.location) < 96) return true;
  for (const r of rituals) if (r.dim.id === p.dimension.id && hdist(r.at, p.location) < 64) return true;
  return false;
}

export function tickHeldHints(now: number): void {
  if (now % 20 !== 0) return;
  let players: Player[] = [];
  try {
    players = world.getAllPlayers();
  } catch {
    return;
  }
  for (const p of players) {
    if (!p.isValid) continue;
    const id = heldItem(p);
    const was = lastHeld.get(p.id);
    if (id) lastHeld.set(p.id, id);
    else lastHeld.delete(p.id);
    try {
      if (id === ITEMS.psalter && now % 40 === 0 && !busyNear(p)) {
        const at = { x: Math.floor(p.location.x) + 0.5, y: p.location.y, z: Math.floor(p.location.z) + 0.5 };
        const why = summonBlocker(p, at);
        p.onScreenDisplay.setActionBar(why ? `§c${why}` : "§bAstral Psalter §f— use it to call VESPER-0 §7(tap / right-click)");
      } else if (id === ITEMS.halo && was !== id && now - (haloHintAt.get(p.id) ?? -99999) > 1200) {
        haloHintAt.set(p.id, now);
        p.onScreenDisplay.setActionBar("§eOrison Halo §f— use it to throw §7(tap / right-click); it flies back to you");
      }
    } catch {
      /* ignore */
    }
  }
  if (lastHeld.size > 256) lastHeld.clear();
}

