import { EquipmentSlot, ItemStack, Player, system, world } from "@minecraft/server";
import { CONFIG } from "../config/global";
import { Scenes } from "../lib/scene";
import { takeAim } from "../lib/targeting";
import { drawHud } from "./hud";
import { PrepHandle, present } from "./presentation";
import { GRIMOIRE_BY_ITEM, GrimoireDef, SpellMeta, getSpell, metaFor } from "./registry";
import { cooldownLeft, forget, getSelection, setSelection, startCooldown } from "./state";

/**
 * Input state machine.
 *
 *   crouch (transition into sneaking, Grimoire in main hand) ... select next spell
 *   press + HOLD Use (not sneaking) ............................ prepare selected spell
 *   RELEASE Use ................................................ cast exactly once
 *
 * The Grimoire items carry minecraft:use_modifiers with a very long use_duration, which makes
 * them "chargeable": the engine raises itemStartUse on press-and-hold, itemReleaseUse when the
 * button is let go, and itemStopUse whenever using ends for any reason.  Only a genuine
 * itemReleaseUse casts.  A stop without a release (hotbar switch, item swap, death, dimension
 * change, completing the charge...) cancels the preparation and starts no cooldown.
 *
 * Engine order inside a tick is start -> complete -> release -> stop, but the machine does not
 * depend on it: a stop only marks the preparation, and it is cancelled on the following tick
 * unless a release has consumed it first.
 */
interface Prep {
  g: GrimoireDef;
  meta: SpellMeta;
  startTick: number;
  slot: number;
  session: number;
  handle: PrepHandle;
  stopTick?: number;
  mode: "charge" | "heartbeat";
  lastBeat: number;
}

interface PState {
  wasSneaking: boolean;
  prep?: Prep;
  rearmAt: number;
  session: number;
  lastHud: number;
  hudDirty: boolean;
  note?: { text: string; until: number };
  lastStartTick: number;
  pendingBeat?: number;
  held?: GrimoireDef;
}

const states = new Map<string, PState>();

function st(p: Player): PState {
  let s = states.get(p.id);
  if (!s) {
    s = { wasSneaking: p.isSneaking, rearmAt: 0, session: 0, lastHud: -999, hudDirty: true, lastStartTick: -999 };
    states.set(p.id, s);
  }
  return s;
}

function heldGrimoire(p: Player): GrimoireDef | undefined {
  try {
    const it = p.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Mainhand);
    return it ? GRIMOIRE_BY_ITEM[it.typeId] : undefined;
  } catch {
    return undefined;
  }
}

function note(s: PState, text: string, ticks = 30): void {
  s.note = { text, until: system.currentTick + ticks };
  s.hudDirty = true;
}

function cancel(s: PState, why: string, quiet = false): void {
  const prep = s.prep;
  if (!prep) return;
  s.prep = undefined;
  s.rearmAt = system.currentTick + CONFIG.input.rearmTicks;
  try { prep.handle.cancel(); } catch (e) { console.warn(`[grimoire] cancel fx: ${e}`); }
  if (!quiet) note(s, `§7${why}`);
}

function begin(p: Player, g: GrimoireDef, mode: Prep["mode"]): void {
  const s = st(p);
  const now = system.currentTick;
  if (s.prep) {
    if (s.prep.mode === "heartbeat" && mode === "charge") { s.prep.mode = "charge"; return; } // upgrade
    cancel(s, "Interrupted", true);
  }
  if (now < s.rearmAt) return;
  if (p.isSneaking) { note(s, "§7Stand up to cast"); return; }
  const meta = metaFor(g.id, getSelection(p, g.id));
  if (cooldownLeft(p, meta.id) > 0) {
    s.hudDirty = true;
    try { present().deny(p, g); } catch { /* ignore */ }
    return;
  }
  if (!getSpell(meta.id)) { note(s, "§cSpell unavailable"); return; }
  let handle: PrepHandle;
  try {
    handle = present().prepStart(p, g, meta);
  } catch (e) {
    console.warn(`[grimoire] prep fx: ${e}`);
    handle = { tick() {}, release() {}, cancel() {} };
  }
  s.prep = { g, meta, startTick: now, slot: p.selectedSlotIndex, session: ++s.session, handle, mode, lastBeat: now };
  note(s, "§bPreparing... §7release to cast", 60);
}

function release(p: Player): void {
  const s = st(p);
  const prep = s.prep;
  if (!prep) return;
  const now = system.currentTick;
  const held = now - prep.startTick;
  if (heldGrimoire(p)?.id !== prep.g.id || p.selectedSlotIndex !== prep.slot) { cancel(s, "Cancelled"); return; }
  if (p.isSneaking) { cancel(s, "Cancelled (crouching)"); return; }
  if (held < CONFIG.input.minHoldTicks) { cancel(s, "Hold Use longer, then release"); return; }
  if (cooldownLeft(p, prep.meta.id) > 0) { cancel(s, "On cooldown"); return; }
  // consume the preparation first: nothing below can run twice for this hold
  s.prep = undefined;
  s.rearmAt = now + CONFIG.input.rearmTicks;
  const spell = getSpell(prep.meta.id);
  if (!spell) { try { prep.handle.cancel(); } catch { /* ignore */ } return; }
  const scene = Scenes.start(spell.id, p);
  let ok: boolean | void = false;
  try {
    ok = spell.cast({ caster: p, scene, aim: takeAim(p), heldTicks: held });
  } catch (e) {
    console.warn(`[grimoire] ${spell.id} cast failed: ${e} ${(e as Error)?.stack ?? ""}`);
    ok = false;
  }
  if (ok === false) {
    scene.end();
    try { prep.handle.cancel(); } catch { /* ignore */ }
    note(s, "§7No valid target");
    return;
  }
  startCooldown(p, spell.id, spell.cooldown); // cooldown begins only on successful activation
  try { prep.handle.release(); } catch (e) { console.warn(`[grimoire] release fx: ${e}`); }
  s.note = undefined;
  s.hudDirty = true;
}

function tickPlayer(p: Player, now: number): void {
  const s = st(p);
  const g = heldGrimoire(p);
  if (g?.id !== s.held?.id) { s.held = g; s.hudDirty = true; }
  const sneaking = p.isSneaking;
  const entered = sneaking && !s.wasSneaking;
  s.wasSneaking = sneaking;

  if (s.prep) {
    const prep = s.prep;
    if (sneaking) cancel(s, "Cancelled (crouching)");
    else if (!g || g.id !== prep.g.id || p.selectedSlotIndex !== prep.slot) cancel(s, "Cancelled");
    else if (prep.stopTick !== undefined && now > prep.stopTick) cancel(s, "Cancelled");
    else if (prep.mode === "heartbeat" && now - prep.lastBeat > CONFIG.input.heartbeatGapTicks) release(p);
    else {
      try { prep.handle.tick(now - prep.startTick); } catch (e) { console.warn(`[grimoire] prep tick: ${e}`); }
    }
  } else if (entered && g) {
    // one crouch press = advance exactly one spell (holding crouch does nothing more)
    const next = (getSelection(p, g.id) + 1) % 6;
    setSelection(p, g.id, next);
    s.note = undefined;
    s.hudDirty = true;
    try { present().select(p, g, metaFor(g.id, next)); } catch (e) { console.warn(`[grimoire] select fx: ${e}`); }
  }

  // heartbeat fallback: an itemUse that was not followed by itemStartUse starts a hold
  if (s.pendingBeat !== undefined && now > s.pendingBeat) {
    const beat = s.pendingBeat;
    s.pendingBeat = undefined;
    if (CONFIG.input.heartbeatFallback && s.lastStartTick < beat && g) {
      if (s.prep?.mode === "heartbeat") s.prep.lastBeat = beat;
      else if (!s.prep) begin(p, g, "heartbeat");
    }
  }

  if (g) {
    if (s.note && now > s.note.until) { s.note = undefined; s.hudDirty = true; }
    if (s.hudDirty || now - s.lastHud >= CONFIG.hud.refreshTicks) {
      s.lastHud = now;
      s.hudDirty = false;
      drawHud(p, g, getSelection(p, g.id), s.note?.text);
    }
  }
}

function isGrimoire(item: ItemStack | undefined): GrimoireDef | undefined {
  return item ? GRIMOIRE_BY_ITEM[item.typeId] : undefined;
}

export function installInput(): void {
  world.afterEvents.itemStartUse.subscribe((ev) => {
    const g = isGrimoire(ev.itemStack);
    if (!g) return;
    st(ev.source).lastStartTick = system.currentTick;
    begin(ev.source, g, "charge");
  });
  world.afterEvents.itemReleaseUse.subscribe((ev) => {
    const s = states.get(ev.source.id);
    if (s?.prep?.mode === "charge") release(ev.source);
  });
  const stop = (p: Player) => {
    const s = states.get(p.id);
    if (s?.prep && s.prep.mode === "charge" && s.prep.stopTick === undefined) s.prep.stopTick = system.currentTick;
  };
  world.afterEvents.itemStopUse.subscribe((ev) => stop(ev.source));
  world.afterEvents.itemCompleteUse.subscribe((ev) => stop(ev.source));
  world.afterEvents.itemUse.subscribe((ev) => {
    if (!CONFIG.input.heartbeatFallback || !isGrimoire(ev.itemStack)) return;
    st(ev.source).pendingBeat = system.currentTick;
  });
  world.afterEvents.entityDie.subscribe((ev) => {
    if (ev.deadEntity.typeId !== "minecraft:player") return;
    const s = states.get(ev.deadEntity.id);
    if (s) cancel(s, "Cancelled", true);
    Scenes.endFor(ev.deadEntity as Player);
  });
  world.afterEvents.playerDimensionChange.subscribe((ev) => {
    const s = states.get(ev.player.id);
    if (s) cancel(s, "Cancelled", true);
    Scenes.endFor(ev.player);
  });
  world.beforeEvents.playerLeave.subscribe((ev) => {
    const id = ev.player.id;
    const s = states.get(id);
    system.run(() => {
      if (s) cancel(s, "Cancelled", true);
      states.delete(id);
      forget(id);
      for (const sc of [...Scenes.active]) if (!sc.caster.isValid) sc.end();
    });
  });
}

/** Called once per tick from main. */
export function tickInput(): void {
  const now = system.currentTick;
  for (const p of world.getAllPlayers()) {
    try {
      if (p.isValid) tickPlayer(p, now);
    } catch (e) {
      console.warn(`[grimoire] input tick: ${e}`);
    }
  }
}

/** Test hook: is this player currently preparing a spell? */
export function isPreparing(p: Player): boolean {
  return states.get(p.id)?.prep !== undefined;
}
