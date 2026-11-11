import { EntityHealthComponent, ItemStack, Player, system, world } from "@minecraft/server";
import { Cast, Prep } from "../spells/context";
import { spellAt, spellById } from "../spells/registry";
import { Fizzle, GRIMOIRE_ITEMS, School, SpellDef, schoolOfItem } from "../spells/types";
import { log } from "./log";
import { PlayerState, flash, remainingTicks, save, startCooldown, stateOf } from "./state";
import { start } from "./tasks";
import { particle, sound, COLORS } from "./fx";
import { schoolColor } from "./hud";

/**
 * Control scheme (verified against BDS 1.26.63 event behaviour):
 *  - entering the crouch state while holding a Grimoire advances that Grimoire's selection by one;
 *  - holding Use while standing starts preparation (itemStartUse);
 *  - releasing Use (itemReleaseUse) activates the prepared spell exactly once;
 *  - itemStopUse without a release (slot switch, item change), itemCompleteUse, crouching,
 *    death, dimension change or leaving all cancel the preparation without casting.
 */

export const EMPOWER = 1.6;

export function heldSchool(p: Player): { school: School; item: ItemStack; slot: number } | undefined {
  try {
    const inv = p.getComponent("minecraft:inventory");
    const slot = p.selectedSlotIndex;
    const item = inv?.container?.getItem(slot);
    const school = schoolOfItem(item?.typeId);
    if (!school || !item) return undefined;
    return { school, item, slot };
  } catch {
    return undefined;
  }
}

const prepScopes = new Map<string, Prep>();

function cancelPrep(p: Player, st: PlayerState, reason: string | undefined): void {
  if (!st.prep) return;
  st.prep = undefined;
  const scope = prepScopes.get(p.id);
  prepScopes.delete(p.id);
  scope?.cleanup(6);
  if (reason) {
    flash(st, `§7${reason}`, 30);
    try {
      p.playSound("grimoire.ui.fizzle", { volume: 0.6 });
    } catch {
      /* ignore */
    }
  }
}

export function cancelPreparation(p: Player, reason?: string): void {
  cancelPrep(p, stateOf(p), reason);
}

// --------------------------------------------------------------------------------- selection

export function onSneakEdge(p: Player, sneaking: boolean): void {
  const st = stateOf(p);
  if (st.sneaking === sneaking) return; // dedupe event + poll
  st.sneaking = sneaking;
  if (!sneaking) return;
  if (st.prep) cancelPrep(p, st, "Preparation cancelled (crouched)");
  const held = heldSchool(p);
  if (!held) return;
  const next = (st.selected[held.school] + 1) % 15;
  st.selected[held.school] = next;
  st.hudKey = "";
  save(p, st);
  const spell = spellAt(held.school, next);
  try {
    p.playSound("grimoire.ui.page", { volume: 0.8, pitch: 0.9 + (next % 5) * 0.05 });
  } catch {
    /* ignore */
  }
  flash(st, `${schoolColor(held.school)}${spell.code} §f${spell.name}`, 40);
}

// --------------------------------------------------------------------------------- preparation

export function onStartUse(p: Player, item: ItemStack): void {
  const school = schoolOfItem(item.typeId);
  if (!school) return;
  const st = stateOf(p);
  if (st.prep) cancelPrep(p, st, undefined);
  if (p.isSneaking) {
    flash(st, "§eStand up (stop crouching) to cast", 40);
    return;
  }
  const spell = spellAt(school, st.selected[school]);
  const rem = remainingTicks(st, spell.id);
  if (rem > 0) {
    flash(st, Number.isFinite(rem) ? `§c${spell.name} §7is on cooldown §c${(rem / 20).toFixed(1)}s` : `§c${spell.name} §7is still active`, 40);
    try {
      p.playSound("grimoire.ui.fizzle", { volume: 0.5, pitch: 1.2 });
    } catch {
      /* ignore */
    }
    return;
  }
  st.prep = {
    school,
    spellIndex: st.selected[school],
    spellId: spell.id,
    slot: p.selectedSlotIndex,
    itemType: item.typeId,
    dimensionId: p.dimension.id,
    startTick: system.currentTick,
    readyAnnounced: false,
  };
  st.hudKey = "";
  try {
    p.playAnimation("animation.grimoire.player.channel", { stopExpression: "!query.is_using_item", blendOutTime: 0.2, controller: "grimoire_channel" });
  } catch {
    /* ignore */
  }
  p.dimension.playSound(`grimoire.${school}.charge`, p.location, { volume: 0.7 });
  if (spell.prepare) {
    const scope = new Prep(p, spell);
    prepScopes.set(p.id, scope);
    try {
      spell.prepare(scope);
    } catch (e) {
      log.error(`${spell.code} prepare failed`, e);
    }
  }
}

function prepValid(p: Player, st: PlayerState): string | undefined {
  const prep = st.prep;
  if (!prep) return "no preparation";
  if (!p.isValid) return "left";
  const hp = p.getComponent(EntityHealthComponent.componentId) as EntityHealthComponent | undefined;
  if (hp && hp.currentValue <= 0) return "Preparation cancelled";
  if (p.dimension.id !== prep.dimensionId) return "Preparation cancelled (dimension changed)";
  if (p.isSneaking) return "Preparation cancelled (crouched)";
  if (p.selectedSlotIndex !== prep.slot) return "Preparation cancelled (item switched)";
  const held = heldSchool(p);
  if (!held || held.item.typeId !== prep.itemType) return "Preparation cancelled (item switched)";
  return undefined;
}

/** Called every tick for each player with an active preparation. */
export function tickPreparation(p: Player, st: PlayerState): void {
  const prep = st.prep;
  if (!prep) return;
  const bad = prepValid(p, st);
  if (bad) {
    cancelPrep(p, st, bad);
    return;
  }
  const spell = spellById(prep.spellId);
  if (!spell) {
    cancelPrep(p, st, undefined);
    return;
  }
  const t = system.currentTick - prep.startTick;
  const k = Math.min(1, t / Math.max(1, spell.charge));
  if (t % 3 === 0) {
    const head = p.getHeadLocation();
    const dir = p.getViewDirection();
    const at = { x: head.x + dir.x * 0.9, y: head.y - 0.35 + dir.y * 0.9, z: head.z + dir.z * 0.9 };
    const c = prep.school === "pressure" ? COLORS.orange : prep.school === "ice" ? COLORS.ice : COLORS.crimson;
    particle(p.dimension, `grimoire:${prep.school}_charge`, at, { color: c, size: 0.4 + k * 0.6, radius: 1.4 - k * 0.8 });
  }
  if (t % 20 === 0 && t > 0) {
    try {
      p.dimension.playSound(`grimoire.${prep.school}.charge`, p.location, { volume: 0.35, pitch: 1 + k * 0.4 });
    } catch {
      /* ignore */
    }
  }
  if (!prep.readyAnnounced && t >= spell.charge) {
    prep.readyAnnounced = true;
    st.hudKey = "";
    try {
      p.playSound("grimoire.ui.ready", { volume: 0.7 });
    } catch {
      /* ignore */
    }
  }
}

// --------------------------------------------------------------------------------- release

export function onReleaseUse(p: Player): void {
  const st = stateOf(p);
  const prep = st.prep;
  if (!prep) return; // a release without our preparation (e.g. started while crouching) casts nothing
  const bad = prepValid(p, st);
  if (bad) {
    cancelPrep(p, st, bad);
    return;
  }
  const spell = spellById(prep.spellId);
  st.prep = undefined;
  const scope = prepScopes.get(p.id);
  prepScopes.delete(p.id);
  if (!spell) {
    scope?.cleanup();
    return;
  }
  const held = system.currentTick - prep.startTick;
  if (held < spell.charge) {
    scope?.cleanup(6);
    flash(st, `§7Hold longer to prepare §f${spell.name}`, 40);
    try {
      p.playSound("grimoire.ui.fizzle", { volume: 0.6 });
    } catch {
      /* ignore */
    }
    return;
  }
  activate(p, st, spell, scope);
}

export function onStopUse(p: Player): void {
  // itemStopUse also follows a normal release in the same tick; by then st.prep was consumed.
  const st = stateOf(p);
  if (st.prep) cancelPrep(p, st, "Preparation cancelled");
}

export function onCompleteUse(p: Player): void {
  const st = stateOf(p);
  if (st.prep) cancelPrep(p, st, "Preparation expired (release to cast)");
}

/** Activate a spell: the cooldown starts here (or, for Wings of the Winter Seraph, when it ends). */
export function activate(p: Player, st: PlayerState, spell: SpellDef, scope?: Prep): boolean {
  const now = system.currentTick;
  const empowered = spell.enhanceable && !!st.empowered && st.empowered.until > now;
  const ctx = new Cast(p, spell, empowered ? EMPOWER : 1, empowered);
  if (scope) ctx.adopted = scope.adopt();
  scope?.cleanup(6);
  let routine;
  try {
    routine = spell.cast(ctx);
  } catch (e) {
    ctx.cleanup(4);
    if (e instanceof Fizzle) {
      flash(st, `§7${e.reason}`, 50);
      try {
        p.playSound("grimoire.ui.fizzle", { volume: 0.7 });
      } catch {
        /* ignore */
      }
      return false;
    }
    log.error(`${spell.code} cast failed`, e);
    flash(st, `§c${spell.name} failed`, 40);
    return false;
  }
  if (empowered) st.empowered = undefined;
  if (spell.cooldownAfterEnd) st.activeUntilEnd.add(spell.id);
  else startCooldown(st, spell.id, spell.cooldown);
  st.hudKey = "";
  save(p, st);
  try {
    p.playAnimation("animation.grimoire.player.release", { blendOutTime: 0.25, controller: "grimoire_release" });
  } catch {
    /* ignore */
  }
  sound(p.dimension, `grimoire.${spell.school}.release`, p.location, 1, 1);
  world.getDimension(p.dimension.id); // keep dimension handle warm
  const playerId = p.id;
  const handle = start(routine ?? emptyRoutine(), `${spell.code}:${p.name}`, playerId, 20 * 200);
  ctx.handle = handle;
  handle.onEnd(() => {
    ctx.cleanup();
    if (spell.cooldownAfterEnd) {
      const pl = world.getEntity(playerId) as Player | undefined;
      startCooldown(st, spell.id, spell.cooldown);
      if (pl?.isValid) save(pl, st);
    }
  });
  if (empowered) flash(st, "§6Empowered by stolen equilibrium!", 40);
  return true;
}

function* emptyRoutine() {
  /* instant spell */
}

export const _test = { GRIMOIRE_ITEMS };
