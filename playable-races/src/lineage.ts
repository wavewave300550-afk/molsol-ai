/** Assigning, removing and restoring lineages (race) on players; manifest / veil of the form. */
import { InputPermissionCategory, Player, system, world } from "@minecraft/server";
import { endChannel, raceOf, refreshForm, resetCooldowns } from "./core/abilities.js";
import { captureEnchantments, ensureFocus, headItem, hideForm, isCrest, purgeFoci, purgeStrayCrests, showForm } from "./core/forms.js";
import { particle, pose, rgb, sound } from "./core/fx.js";
import { Session, get, save } from "./core/session.js";
import { settings } from "./core/settings.js";
import { cancel } from "./core/tasks.js";
import { add, v3, warn } from "./core/util.js";
import { raceByCode } from "./races/registry.js";
import { RaceDef } from "./races/types.js";
import { applyFog } from "./systems/bloodmoon.js";
import { clearMarksBy } from "./systems/marks.js";
import { removeMiragesOf } from "./systems/mirage.js";
import { removeProxiesOf } from "./systems/proxies.js";
import { claim, isUnique, releasePlayer, uniqueBlocked } from "./systems/unique.js";

const RACE_RGB: Record<string, { red: number; green: number; blue: number }> = {
  "001": { red: 0.45, green: 1, blue: 0.4 },
  "002": { red: 1, green: 0.78, blue: 0.3 },
  "003": { red: 1, green: 0.18, blue: 0.25 },
  "004": { red: 0.78, green: 0.66, blue: 1 },
  "005": { red: 1, green: 0.86, blue: 0.45 },
  "006": { red: 1, green: 0.92, blue: 0.62 },
};

export function worldDay(): number {
  try {
    return world.getDay();
  } catch {
    return 0;
  }
}

/** Why the player may not take `race` (Unique lineages can be held by one player at a time). */
export function raceBlocked(p: Player, race: RaceDef): string | undefined {
  return uniqueBlocked(p, race);
}

/** Why the player may not change lineage right now (undefined = allowed). */
export function changeBlocked(p: Player, s: Session): string | undefined {
  if (!s.data.race) return undefined;
  const set = settings();
  const op = isOperator(p);
  if (set.change === "operators" && !op) return "Only operators can change lineages in this world.";
  if (set.change === "cooldown" && !op) {
    const left = s.data.lastChange + set.changeDays - worldDay();
    if (left > 0) return `The Rite of Unbecoming needs ${left} more in-game day${left > 1 ? "s" : ""}.`;
  }
  return undefined;
}

export function isOperator(p: Player): boolean {
  try {
    return (p.playerPermissionLevel as number) >= 2 || (p.commandPermissionLevel as number) >= 1;
  } catch {
    return false;
  }
}

/** Strip everything the current race added (effects expire on their own within 3 s). */
export function stripRace(p: Player, s: Session): void {
  const race = raceOf(s);
  if (s.channel) endChannel(p, s, "race");
  cancel(p.id);
  clearMarksBy(p.id);
  removeMiragesOf(p.id);
  removeProxiesOf(p.id);
  restoreInput(p, s);
  if (race) {
    try {
      race.release?.(s, "race");
    } catch (e) {
      warn("race release failed", e);
    }
    try {
      race.cleanup(p, s);
    } catch (e) {
      warn("race cleanup failed", e);
    }
  }
  hideForm(p);
  purgeFoci(p);
  s.tempVariant = undefined;
  s.flags.clear();
  s.num.clear();
  resetCooldowns(s);
  s.data.res = {};
  s.data.st = {};
}

export function assignRace(p: Player, code: string, ceremony = true, force = false): boolean {
  const race = raceByCode(code);
  if (!race) return false;
  const s = get(p);
  const blocked = force ? undefined : raceBlocked(p, race);
  if (blocked) {
    p.sendMessage(`§c${blocked}`);
    return false;
  }
  captureEnchantments(p, s);
  stripRace(p, s);
  s.data.race = race.code;
  s.data.sel = 0;
  s.data.veiled = false;
  s.data.lastChange = worldDay();
  s.data.stats.changes = (s.data.stats.changes ?? 0) + 1;
  releasePlayer(p.id);
  if (isUnique(race)) claim(p, race, worldDay());
  race.init(p, s, true);
  ensureFocus(p, race);
  const shown = showForm(p, race, s, race.variant(p, s));
  if (!shown) {
    s.data.veiled = true;
    p.sendMessage("§eYour head slot is occupied and your inventory is full - your form stays veiled. Make room, then choose 'Manifest Form' in the Lineage Codex.");
  }
  s.dirty = true;
  save(p, s, true);
  applyFog(p);
  if (ceremony) rite(p, race);
  return true;
}

export function removeRace(p: Player): void {
  const s = get(p);
  stripRace(p, s);
  releasePlayer(p.id);
  s.data.race = "";
  s.data.veiled = false;
  s.dirty = true;
  save(p, s, true);
}

function rite(p: Player, race: RaceDef): void {
  const c = RACE_RGB[race.code] ?? { red: 1, green: 1, blue: 1 };
  particle(p.dimension, "plrace:rite_aura", add(p.location, v3(0, 0.1, 0)), rgb(c));
  sound(p.dimension, "beacon.activate", p.location, 1, 1.2);
  sound(p.dimension, "random.levelup", p.location, 0.5, 0.7);
  pose(p, "rite");
  try {
    p.onScreenDisplay.setTitle(`${race.color}${race.name}`, { subtitle: `§7${race.title} - Race ${race.code}`, fadeInDuration: 10, stayDuration: 50, fadeOutDuration: 20 });
  } catch {
    /* ignore */
  }
}

export function setVeiled(p: Player, veiled: boolean): string {
  const s = get(p);
  const race = raceOf(s);
  if (!race) return "You have no lineage.";
  if (veiled) {
    captureEnchantments(p, s);
    s.data.veiled = true;
    hideForm(p);
    s.dirty = true;
    save(p, s, true);
    return "§7Form veiled. Your powers remain; your head slot is free for a helmet.";
  }
  s.data.veiled = false;
  const ok = showForm(p, race, s, race.variant(p, s));
  if (!ok) {
    s.data.veiled = true;
    return "§cNo room: free an inventory slot so your helmet can be stored, then try again.";
  }
  s.dirty = true;
  save(p, s, true);
  return `${race.color}Your ${race.name} form is manifest.`;
}

/** Re-enable any input category we disabled (e.g. rooted when the player logged out). */
export function restoreInput(p: Player, s: Session): void {
  for (const c of s.data.locks) {
    try {
      p.inputPermissions.setPermissionCategory(c as InputPermissionCategory, true);
    } catch {
      /* ignore */
    }
  }
  if (s.data.locks.length) {
    s.data.locks = [];
    s.dirty = true;
  }
}

/** Join / respawn / reload: make sure the player's lineage is fully in place. */
export function restore(p: Player, s: Session): void {
  restoreInput(p, s);
  try {
    p.camera.clear(); // a display check interrupted by a logout
  } catch {
    /* ignore */
  }
  const race = raceOf(s);
  if (!race) {
    // no lineage: remove anything left over from removed races
    const it = headItem(p);
    if (it && isCrest(it)) hideForm(p);
    purgeFoci(p);
    releasePlayer(p.id);
    return;
  }
  // keep Unique claims consistent with what the player actually holds
  releasePlayer(p.id, isUnique(race) ? race.code : undefined);
  if (isUnique(race)) claim(p, race, worldDay());
  race.init(p, s, false);
  purgeFoci(p, race.focusItem);
  purgeStrayCrests(p);
  ensureFocus(p, race);
  if (!s.data.veiled) refreshForm(p, s);
  applyFog(p);
}

/** Periodic integrity check (1 Hz): crest still worn, focus still owned. */
export function integrity(p: Player, s: Session): void {
  const race = raceOf(s);
  if (!race) return;
  if (!s.data.veiled) {
    const it = headItem(p);
    if (!it || !isCrest(it)) {
      // crest removed (e.g. /clear, /replaceitem, another add-on): restore it
      system.run(() => {
        if (p.isValid) refreshForm(p, s);
      });
    }
  }
}

export function giveFocus(p: Player): void {
  const race = raceOf(get(p));
  if (race) ensureFocus(p, race);
}
