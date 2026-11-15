/**
 * The Anatomical Atlas: in-game codex of every specimen (boss), with
 * summoning, joining/leaving the active encounter and creative test tools.
 */
import { GameMode, ItemStack, Player, PlayerPermissionLevel, system } from "@minecraft/server";
import { ActionFormData, MessageFormData } from "@minecraft/server-ui";
import { leaveArena } from "./arena.js";
import { langOf, setLang } from "./lang.js";
import { manager } from "./manager.js";
import { allBosses, BossDefinition } from "./registry.js";

function isOperator(p: Player): boolean {
  try {
    return p.getGameMode() === GameMode.Creative || p.playerPermissionLevel >= PlayerPermissionLevel.Operator;
  } catch {
    return false;
  }
}

export function openAtlas(p: Player): void {
  const bosses = allBosses();
  const form = new ActionFormData().title("§lTHE ANATOMY OF A WORLD").body(atlasIntro());
  const actions: (() => void)[] = [];
  const active = manager.active;
  if (active && !active.isFinished()) {
    if (p.dimension.id === active.def.dimensionId) {
      form.button("§cLeave the encounter\n§8return to where you came from");
      actions.push(() => {
        manager.cancelReturn(p);
        leaveArena(p);
      });
      if (active.checkReport) {
        form.button(langOf(p) === "th" ? "§eตรวจสอบการต่อสู้\n§8บอสครบไหม / มีปัญหาอะไร" : "§eCheck the fight\n§8are all boss parts there?");
        actions.push(() => p.sendMessage(active.checkReport!(p)));
      }
    } else {
      form.button("§aJoin the encounter\n§8" + active.def.atlas.title);
      actions.push(() => manager.rejoin(p));
    }
  }
  for (const b of bosses) {
    form.button(`§l${b.atlas.number}§r  ${b.atlas.title}\n§8${b.atlas.subtitle}`);
    actions.push(() => specimenPage(p, b));
  }
  if (isOperator(p)) {
    form.button("§6Test tools §8(operators)");
    actions.push(() => testTools(p));
  }
  // in-fight guidance language (HUD, titles, briefings)
  const th = langOf(p) === "th";
  form.button(th ? "§9Language: ภาษาไทย\n§8switch to English" : "§9Language: English\n§8เปลี่ยนเป็นภาษาไทย");
  actions.push(() => {
    setLang(p, th ? "en" : "th");
    p.sendMessage(th ? "§7In-fight guidance is now in §fEnglish§7." : "§7คำแนะนำระหว่างการต่อสู้จะแสดงเป็น§fภาษาไทย§7แล้ว");
  });
  show(p, form, actions);
}

function atlasIntro(): string {
  return "§7Field notes on colossal organisms whose bodies are the battlefield.\n\n§fEach specimen lives in its own pocket of the world. Use its summoning relic to be drawn in; your companions within 32 blocks come with you.";
}

function specimenPage(p: Player, b: BossDefinition): void {
  const a = b.atlas;
  const s = manager.stats()[b.id];
  const record = s ? `§7Attempts §f${s.attempts}§7 · Victories §f${s.victories}${s.bestSeconds ? `§7 · Best §f${Math.floor(s.bestSeconds / 60)}m ${s.bestSeconds % 60}s` : ""}` : "§7No recorded encounters.";
  const body = [
    `§l${a.number} — ${a.title}§r`,
    `§o§7${a.subtitle}§r`,
    "",
    a.overview,
    "",
    "§6§lAnatomy§r",
    ...a.anatomy,
    "",
    "§6§lBoss flow§r",
    ...a.phases.map((ph) => `§e${ph.name}§r\n${ph.text}`),
    "",
    "§6§lAbilities§r",
    ...a.abilities.map((ab) => `§c${ab.name}§r — ${ab.text}`),
    "",
    `§6Scale§r ${a.scale}`,
    `§6Arena§r ${a.arena}`,
    `§6Summoning§r ${a.summon}`,
    "",
    record,
  ].join("\n");
  const form = new ActionFormData().title(`${a.number} · ${a.title}`).body(body);
  const actions: (() => void)[] = [];
  const hasItem = carries(p, b.summonItem);
  if (!manager.active) {
    if (hasItem || p.getGameMode() === GameMode.Creative) {
      form.button("§aBegin the encounter");
      actions.push(() => confirmStart(p, b, hasItem && p.getGameMode() !== GameMode.Creative));
    } else {
      form.button("§8Begin the encounter\n§8requires its summoning relic");
      actions.push(() => p.sendMessage("§7You need a §fRestless Lodestone§7 to call this specimen."));
    }
  }
  form.button("Back");
  actions.push(() => openAtlas(p));
  show(p, form, actions);
}

function confirmStart(p: Player, b: BossDefinition, consume: boolean): void {
  new MessageFormData()
    .title(b.atlas.title)
    .body(`Draw yourself and everyone within 32 blocks into the ${b.atlas.title}'s domain?\n\n§7You can leave at any time from this Atlas.`)
    .button1("Not yet")
    .button2("§aBegin")
    .show(p)
    .then((r) => {
      if (r.canceled || r.selection !== 1) return;
      startFor(p, b, consume);
    })
    .catch(() => undefined);
}

export function startFor(p: Player, b: BossDefinition, consume: boolean): void {
  if (consume && !takeOne(p, b.summonItem)) {
    p.sendMessage("§cThe summoning relic is missing.");
    return;
  }
  const err = manager.start(b, p);
  if (err) {
    p.sendMessage("§c" + err);
    if (consume) giveBack(p, b.summonItem);
  }
}

function testTools(p: Player): void {
  const form = new ActionFormData().title("Test tools").body(manager.active ? manager.active.status() : "No active encounter.");
  const actions: (() => void)[] = [];
  const a = manager.active;
  if (!a) {
    for (const b of allBosses()) {
      form.button(`Start ${b.atlas.number} (free)`);
      actions.push(() => startFor(p, b, false));
    }
  } else {
    form.button("Skip to next phase");
    actions.push(() => p.sendMessage(a.forcePhase(2) ? "§aPhase skip requested" : "§7Not possible right now"));
    for (const id of a.def.abilities) {
      form.button(`Force ${id.replace(/_/g, " ")}`);
      actions.push(() => p.sendMessage(a.forceAbility(id) ? `§aForced ${id}` : "§7Not possible right now"));
    }
    form.button("Defeat the boss now");
    actions.push(() => p.sendMessage(a.killBoss() ? "§aDone" : "§7Not possible right now"));
    form.button("§cAbort and clean up");
    actions.push(() => manager.stop("abort"));
  }
  form.button("Back");
  actions.push(() => openAtlas(p));
  show(p, form, actions);
}

function show(p: Player, form: ActionFormData, actions: (() => void)[], tries = 0): void {
  form
    .show(p)
    .then((r) => {
      if (r.canceled) {
        // the player was busy (e.g. chat open): retry a few times
        if (String(r.cancelationReason) === "UserBusy" && tries < 8) system.runTimeout(() => show(p, form, actions, tries + 1), 10);
        return;
      }
      const fn = actions[r.selection ?? -1];
      if (fn) system.run(fn);
    })
    .catch((e) => console.warn(`[anatomy] atlas form failed: ${String(e)}`));
}

function carries(p: Player, item: string): boolean {
  const inv = p.getComponent("minecraft:inventory")?.container;
  if (!inv) return false;
  for (let i = 0; i < inv.size; i++) if (inv.getItem(i)?.typeId === item) return true;
  return false;
}

function takeOne(p: Player, item: string): boolean {
  const inv = p.getComponent("minecraft:inventory")?.container;
  if (!inv) return false;
  for (let i = 0; i < inv.size; i++) {
    const it = inv.getItem(i);
    if (it?.typeId !== item) continue;
    if (it.amount > 1) {
      it.amount--;
      inv.setItem(i, it);
    } else inv.setItem(i, undefined);
    return true;
  }
  return false;
}

function giveBack(p: Player, item: string): void {
  try {
    p.getComponent("minecraft:inventory")?.container?.addItem(new ItemStack(item, 1));
  } catch {
    /* ignore */
  }
}
