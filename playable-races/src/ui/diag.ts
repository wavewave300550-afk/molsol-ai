/**
 * Display check (v1.3.1): shows every lineage's body in turn through a camera placed in
 * front of the player, then asks which ones could not be seen.  Anything reported missing
 * is shown again as a "still" variant (the same geometry, texture and materials with no
 * animation or script at all), which separates "the model cannot be drawn on this device"
 * from "an animation or script hides it".  The result line also names the resource-pack
 * version the client actually uses (translated by the client from the pack's own lang
 * file), which exposes an old copy of the pack overriding the new one.
 */
import { EquipmentSlot, InputPermissionCategory, ItemLockMode, ItemStack, Player, RawMessage, system } from "@minecraft/server";
import { ActionFormData, ModalFormData } from "@minecraft/server-ui";
import { add, flat, mul, v3 } from "../core/util.js";
import { headItem, isCrest, wantsStill } from "../core/forms.js";
import { raceOf, refreshForm } from "../core/abilities.js";
import { get, save, Session } from "../core/session.js";
import { NS, RP_VERSION_KEY, VERSION } from "../config.js";
import { RACES } from "../races/registry.js";
import { RaceDef } from "../races/types.js";

const SHOW_TICKS = 60;

function wait(ticks: number): Promise<void> {
  return new Promise((res) => system.runTimeout(() => res(), ticks));
}

/** "Resource pack x.y.z" as the client resolves it (the raw key if the pack is missing it). */
export function rpVersionLine(prefix: string): RawMessage {
  return { rawtext: [{ text: prefix }, { translate: RP_VERSION_KEY }, { text: ` §8(behavior pack ${VERSION})` }] };
}

function setHead(p: Player, id: string | undefined): void {
  const eq = p.getComponent("minecraft:equippable");
  if (!eq) return;
  if (!id) {
    eq.setEquipment(EquipmentSlot.Head, undefined);
    return;
  }
  const it = new ItemStack(id, 1);
  it.lockMode = ItemLockMode.slot;
  eq.setEquipment(EquipmentSlot.Head, it);
}

function aimCamera(p: Player): void {
  const fwd = flat(p.getViewDirection());
  const len = Math.hypot(fwd.x, fwd.z) || 1;
  const f = v3(fwd.x / len, 0, fwd.z / len);
  const base = p.location;
  p.camera.setCamera("minecraft:free", {
    location: add(add(base, mul(f, 3.4)), v3(0, 1.45, 0)),
    facingLocation: add(base, v3(0, 1.0, 0)),
  });
}

function lock(p: Player, s: Session, on: boolean): void {
  for (const c of [InputPermissionCategory.LateralMovement, InputPermissionCategory.Jump]) {
    try {
      p.inputPermissions.setPermissionCategory(c, !on);
    } catch {
      /* ignore */
    }
    if (on && !s.data.locks.includes(c)) s.data.locks.push(c);
    if (!on) s.data.locks = s.data.locks.filter((x) => x !== c);
  }
  s.dirty = true;
}

/** Show each id for SHOW_TICKS with the camera in front; returns false if the player left. */
async function parade(p: Player, ids: { race: RaceDef; id: string }[], label: string): Promise<boolean> {
  for (let i = 0; i < ids.length; i++) {
    if (!p.isValid) return false;
    const { race, id } = ids[i];
    try {
      setHead(p, id);
      aimCamera(p);
      p.onScreenDisplay.setActionBar(`${race.color}${race.code} ${race.name} §7- ${label} (${i + 1}/${ids.length})`);
    } catch {
      /* keep going: a failure to equip shows up as "not visible" */
    }
    await wait(SHOW_TICKS);
  }
  return p.isValid;
}

async function ask(p: Player, title: string, question: string, races: RaceDef[]): Promise<RaceDef[] | undefined> {
  const f = new ModalFormData().title(title).label(question);
  for (const r of races) f.toggle(`${r.color}${r.code} ${r.name}`, { defaultValue: false });
  f.submitButton("Done");
  const res = await f.show(p);
  if (res.canceled || !res.formValues) return undefined;
  const vals = res.formValues.filter((v) => typeof v === "boolean");
  return races.filter((_, i) => vals[i] === true);
}

export async function displayCheck(p: Player): Promise<void> {
  const s = get(p);
  if (s.diag) return;
  if (s.channel) {
    p.sendMessage("§cFinish your current ability first.");
    return;
  }
  const before = headItem(p);
  if (before && !isCrest(before)) {
    p.sendMessage("§eTake off your helmet first (or veil nothing) - the check needs your head slot.");
    return;
  }
  const intro = new ActionFormData()
    .title("§lDisplay Check")
    .body({ rawtext: [
      { text: `§7Every lineage's body is shown for 3 seconds with a camera in front of you (${RACES.length} in all, about ${Math.round((RACES.length * SHOW_TICKS) / 20)} s). Stand still. Afterwards, tick the ones you could §lnot§r§7 see.\n\n§7Resource pack in use: §f` },
      { translate: RP_VERSION_KEY },
      { text: `\n§7Behavior pack: §f${VERSION}` },
    ] })
    .button("§lStart")
    .button("Cancel");
  const mine = raceOf(s);
  const usingStill = !!mine && wantsStill(s, mine);
  if (usingStill) intro.button("Use the §lanimated§r body again");
  const go = await intro.show(p);
  if (!go.canceled && go.selection === 2 && usingStill && mine) {
    s.data.still = (s.data.still ?? []).filter((c) => c !== mine.code);
    s.dirty = true;
    refreshForm(p, s);
    save(p, s, true);
    p.sendMessage(`§7Your ${mine.color}${mine.name}§7 body is animated again.`);
    return;
  }
  if (go.canceled || go.selection !== 0) return;

  s.diag = true;
  lock(p, s, true);
  let hidden: RaceDef[] = [];
  let still: RaceDef[] | undefined;
  try {
    const okRun = await parade(p, RACES.map((r) => ({ race: r, id: `${NS}:form_${r.key}` })), "moving body");
    endShow(p, s, before);
    if (!okRun) return;
    hidden = (await ask(p, "§lDisplay Check", "§7Tick every lineage you could NOT see:", RACES)) ?? [];
    if (hidden.length) {
      s.diag = true;
      lock(p, s, true);
      const ok2 = await parade(p, hidden.map((r) => ({ race: r, id: `${NS}:form_${r.key}_static` })), "still body, no animation");
      endShow(p, s, before);
      if (!ok2) return;
      still = await ask(p, "§lDisplay Check (2)", "§7These were shown again without any animation. Tick the ones you STILL could not see:", hidden);
    }
  } finally {
    endShow(p, s, before);
  }
  const code = (rs: RaceDef[] | undefined) => (rs && rs.length ? rs.map((r) => r.code).join(",") : "none");
  const summary = `§6[Display check]§r hidden: §f${code(hidden)}§r` + (hidden.length ? `, still hidden without animation: §f${code(still)}` : "");
  p.sendMessage({ rawtext: [{ text: summary + "\n" }, ...rpVersionLine("§7resource pack ").rawtext!] });
  if (!hidden.length) p.sendMessage("§aEvery body was visible.");
  else p.sendMessage("§7Send a screenshot of the line above to the add-on author - it says exactly which part fails.");
  // Workaround the player can use at once: their own body was invisible while animated but
  // visible as the still twin -> offer to wear the still twin (same body, no animation).
  const own = raceOf(s);
  if (p.isValid && own && hidden.includes(own) && still && !still.includes(own) && !wantsStill(s, own)) {
    const offer = await new ActionFormData()
      .title("§lDisplay Check")
      .body(`§7Your ${own.color}${own.name}§7 body could not be seen while animated, but could be seen without animation.\n\n§fWear the still body for now?§7 It is the same body without any animation (forms and idle motion are not shown). You can switch back here at any time.`)
      .button("§lWear the still body")
      .button("Keep the animated body")
      .show(p);
    if (!offer.canceled && offer.selection === 0 && p.isValid) {
      s.data.still = [...(s.data.still ?? []).filter((c) => c !== own.code), own.code];
      s.dirty = true;
      refreshForm(p, s);
      save(p, s, true);
      p.sendMessage(`§aYou now wear the still ${own.color}${own.name}§a body. §7Codex > Display Check > "Use the animated body again" switches back.`);
    }
  }
}

function endShow(p: Player, s: Session, before: ItemStack | undefined): void {
  if (!s.diag) return;
  s.diag = false;
  if (!p.isValid) return;
  try {
    p.camera.clear();
  } catch {
    /* ignore */
  }
  lock(p, s, false);
  try {
    const eq = p.getComponent("minecraft:equippable");
    eq?.setEquipment(EquipmentSlot.Head, before);
  } catch {
    /* ignore */
  }
  refreshForm(p, s);
  save(p, s, true);
}
