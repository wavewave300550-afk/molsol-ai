/**
 * The Codex: an in-game guide and control panel (touch-friendly, no commands needed).
 * Players read about the four Miracles; operators can also change settings,
 * raise a demonstration arena (explicit, confirmed, destructive) or dismiss an encounter.
 */
import { Player, PlayerPermissionLevel, world } from "@minecraft/server";
import { ActionFormData, MessageFormData, ModalFormData } from "@minecraft/server-ui";
import { BOSS_KEYS, BossKey, CONFIG, applySettings } from "./config";
import { manager } from "./core/manager";
import { arenaOf } from "./registry";
import { saveSettings } from "./core/persistence";
import { report } from "./core/trace";

const DIFFICULTIES = ["story", "normal", "hard"] as const;
const tr = (key: string, ...w: string[]) => ({ rawtext: [{ translate: key, with: w }] });

export function isOperator(p: Player): boolean {
  try {
    return p.playerPermissionLevel >= PlayerPermissionLevel.Operator;
  } catch {
    return false;
  }
}

/** Place a demonstration arena centred on the player, floor at their feet. Destructive by design. */
export function raiseArena(p: Player, key: BossKey): boolean {
  const info = arenaOf(key);
  if (!info) return false;
  const l = p.location;
  const half = Math.floor(info.size / 2);
  try {
    world.structureManager.place(info.structure, p.dimension, {
      x: Math.floor(l.x) - half, y: Math.floor(l.y) - 1, z: Math.floor(l.z) - half,
    });
    p.sendMessage(tr("abm.arena.built"));
    return true;
  } catch (e) {
    report("raiseArena", e);
    return false;
  }
}

async function arenaMenu(p: Player): Promise<void> {
  const keys = BOSS_KEYS.filter((k) => arenaOf(k));
  const form = new ActionFormData().title(tr("abm.ui.arena"));
  for (const k of keys) form.button(tr(arenaOf(k)!.nameKey));
  const r = await form.show(p);
  if (r.canceled || r.selection === undefined) return;
  const key = keys[r.selection];
  const info = arenaOf(key)!;
  const ok = await new MessageFormData()
    .title(tr(info.nameKey))
    .body(tr("abm.ui.arena.warn", String(info.size), String(info.size)))
    .button1(tr("abm.ui.cancel"))
    .button2(tr("abm.ui.confirm"))
    .show(p);
  if (!ok.canceled && ok.selection === 1) raiseArena(p, key);
}

async function settingsMenu(p: Player): Promise<void> {
  const r = await new ModalFormData()
    .title(tr("abm.ui.settings"))
    .dropdown(tr("abm.ui.difficulty"), ["Story", "Normal", "Hard"], { defaultValueIndex: DIFFICULTIES.indexOf(CONFIG.difficulty) })
    .toggle(tr("abm.ui.vfx"), { defaultValue: CONFIG.vfx.density < 1 })
    .toggle(tr("abm.ui.actionbar"), { defaultValue: CONFIG.hud.actionBar })
    .toggle(tr("abm.ui.movement"), { defaultValue: CONFIG.movement.mode === "teleport" })
    .show(p);
  if (r.canceled || !r.formValues) return;
  const [d, vfx, bar, tele] = r.formValues;
  applySettings({
    difficulty: DIFFICULTIES[typeof d === "number" ? d : 1],
    vfxDensity: vfx ? 0.5 : 1,
    actionBar: !!bar,
    movementMode: tele ? "teleport" : "impulse",
  });
  saveSettings();
  p.sendMessage(tr("abm.ui.saved"));
}

export async function openCodex(p: Player): Promise<void> {
  try {
    const op = isOperator(p);
    const keys = BOSS_KEYS.filter((k) => manager.has(k));
    const form = new ActionFormData().title(tr("abm.ui.title"))
      .body({ rawtext: [{ translate: "abm.ui.body1" }, { text: "\n\n" }, { translate: "abm.ui.body2" }] });
    for (const k of keys) form.button(tr(`entity.${bossType(k)}.name`));
    if (op) form.button(tr("abm.ui.settings")).button(tr("abm.ui.arena")).button(tr("abm.ui.dismiss"));
    const r = await form.show(p);
    if (r.canceled || r.selection === undefined) return;
    if (r.selection < keys.length) {
      const k = keys[r.selection];
      const s = CONFIG.bosses[k];
      await new MessageFormData()
        .title(tr(`entity.${bossType(k)}.name`))
        .body({ rawtext: [{ translate: `abm.lore.${k}` }, { text: "\n\n" }, { translate: "abm.summon.need", with: [String(s.arenaRadius * 2 + 1), String(s.clearance)] }] })
        .button1(tr("abm.ui.cancel"))
        .button2(tr("abm.ui.title"))
        .show(p);
      return;
    }
    const extra = r.selection - keys.length;
    if (extra === 0) await settingsMenu(p);
    else if (extra === 1) await arenaMenu(p);
    else if (extra === 2) {
      const enc = manager.nearest(p.dimension, p.location);
      if (enc) manager.cancel(enc);
      p.sendMessage(tr("abm.msg.cancelled"));
    }
  } catch (e) {
    report("codex", e);
  }
}

function bossType(k: BossKey): string {
  return { vesperra: "abm:vesperra", cantor: "abm:cantor_xiii", nomos: "abm:nomos", orison: "abm:orison" }[k];
}
