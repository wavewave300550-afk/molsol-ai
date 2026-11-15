/**
 * The Anatomical Atlas: in-game codex of every specimen (boss), with
 * summoning, joining/leaving the active encounter and creative test tools.
 */
import { GameMode, ItemStack, Player, PlayerPermissionLevel, system } from "@minecraft/server";
import { ActionFormData, MessageFormData } from "@minecraft/server-ui";
import { leaveArena } from "./arena.js";
import { langOf, setLang, tr } from "./lang.js";
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
  const th = langOf(p) === "th";
  const form = new ActionFormData().title("§lTHE ANATOMY OF A WORLD").body(atlasIntro(p));
  const actions: (() => void)[] = [];
  const active = manager.active;
  if (active && !active.isFinished()) {
    if (p.dimension.id === active.def.dimensionId) {
      form.button(tr(p, "§cLeave the encounter\n§8return to where you came from", "§cออกจากการต่อสู้\n§8กลับไปที่เดิม"));
      actions.push(() => {
        manager.cancelReturn(p);
        leaveArena(p);
      });
      if (active.checkReport) {
        form.button(langOf(p) === "th" ? "§eตรวจสอบการต่อสู้\n§8บอสครบไหม / มีปัญหาอะไร" : "§eCheck the fight\n§8are all boss parts there?");
        actions.push(() => p.sendMessage(active.checkReport!(p)));
      }
    } else {
      form.button(tr(p, "§aJoin the encounter\n§8", "§aเข้าร่วมการต่อสู้\n§8") + active.def.atlas.title);
      actions.push(() => manager.rejoin(p));
    }
  }
  for (const b of bosses) {
    form.button(`§l${b.atlas.number}§r  ${b.atlas.title}\n§8${(th && b.atlas.th ? b.atlas.th : b.atlas).subtitle}`);
    actions.push(() => specimenPage(p, b));
  }
  if (isOperator(p)) {
    form.button("§6Test tools §8(operators)");
    actions.push(() => testTools(p));
  }
  // language of the Atlas pages and the in-fight guidance (HUD, titles, briefings)
  form.button(th ? "§9Language: ภาษาไทย\n§8switch to English" : "§9Language: English\n§8เปลี่ยนเป็นภาษาไทย");
  actions.push(() => {
    setLang(p, th ? "en" : "th");
    p.sendMessage(th ? "§7The Atlas and the in-fight guidance are now in §fEnglish§7." : "§7Atlas และคำแนะนำระหว่างการต่อสู้จะแสดงเป็น§fภาษาไทย§7แล้ว");
  });
  show(p, form, actions);
}

function atlasIntro(p: Player): string {
  return tr(
    p,
    "§7Field notes on colossal organisms whose bodies are the battlefield.\n\n§fEach specimen lives in its own pocket of the world. Use its summoning relic to be drawn in; your companions within 32 blocks come with you.",
    "§7บันทึกภาคสนามของสิ่งมีชีวิตยักษ์ ที่ร่างกายของมันคือสนามรบ\n\n§fบอสแต่ละตัวอยู่ในมิติของมันเอง ใช้ไอเท็มเรียกบอสเพื่อเข้าไป เพื่อนที่อยู่ในระยะ 32 บล็อกจะเข้าไปด้วย",
  );
}

function specimenPage(p: Player, b: BossDefinition): void {
  const a = b.atlas;
  const th = langOf(p) === "th";
  const t = th && a.th ? a.th : a;
  const s = manager.stats()[b.id];
  const best = s?.bestSeconds ? tr(p, `§7 · Best §f${Math.floor(s.bestSeconds / 60)}m ${s.bestSeconds % 60}s`, `§7 · เร็วสุด §f${Math.floor(s.bestSeconds / 60)} นาที ${s.bestSeconds % 60} วินาที`) : "";
  const record = s
    ? tr(p, `§7Attempts §f${s.attempts}§7 · Victories §f${s.victories}`, `§7เข้าสู้ §f${s.attempts}§7 ครั้ง · ชนะ §f${s.victories}§7 ครั้ง`) + best
    : tr(p, "§7No recorded encounters.", "§7ยังไม่มีบันทึกการต่อสู้");
  const body = [
    `§l${a.number} — ${a.title}§r`,
    `§o§7${t.subtitle}§r`,
    "",
    t.overview,
    "",
    tr(p, "§6§lAnatomy§r", "§6§lกายวิภาค§r"),
    ...t.anatomy,
    "",
    tr(p, "§6§lBoss flow§r", "§6§lลำดับการต่อสู้§r"),
    ...t.phases.map((ph) => `§e${ph.name}§r\n${ph.text}`),
    "",
    tr(p, "§6§lAbilities§r", "§6§lความสามารถ§r"),
    ...t.abilities.map((ab) => `§c${ab.name}§r — ${ab.text}`),
    "",
    tr(p, "§6§lRewards§r", "§6§lของรางวัล§r"),
    ...t.rewards,
    "",
    `${tr(p, "§6Scale§r", "§6ขนาด§r")} ${t.scale}`,
    `${tr(p, "§6Arena§r", "§6สนาม§r")} ${t.arena}`,
    `${tr(p, "§6Summoning§r", "§6การเรียกบอส§r")} ${t.summon}`,
    "",
    record,
  ].join("\n");
  const form = new ActionFormData().title(`${a.number} · ${a.title}`).body(body);
  const actions: (() => void)[] = [];
  const hasItem = carries(p, b.summonItem);
  if (!manager.active) {
    if (hasItem || p.getGameMode() === GameMode.Creative) {
      form.button(tr(p, "§aBegin the encounter", "§aเริ่มการต่อสู้"));
      actions.push(() => confirmStart(p, b, hasItem && p.getGameMode() !== GameMode.Creative));
    } else {
      form.button(tr(p, "§8Begin the encounter\n§8requires its summoning relic", "§8เริ่มการต่อสู้\n§8ต้องมีไอเท็มเรียกบอส"));
      actions.push(() => p.sendMessage(tr(p, "§7You need a §fRestless Lodestone§7 to call this specimen.", "§7ต้องมี §fRestless Lodestone§7 ถึงจะเรียกบอสตัวนี้ได้")));
    }
  }
  form.button(tr(p, "Back", "กลับ"));
  actions.push(() => openAtlas(p));
  show(p, form, actions);
}

function confirmStart(p: Player, b: BossDefinition, consume: boolean): void {
  new MessageFormData()
    .title(b.atlas.title)
    .body(
      tr(
        p,
        `Draw yourself and everyone within 32 blocks into the ${b.atlas.title}'s domain?\n\n§7You can leave at any time from this Atlas.`,
        `พาตัวคุณและทุกคนในระยะ 32 บล็อกเข้าไปในอาณาเขตของ ${b.atlas.title} เลยไหม?\n\n§7ออกได้ทุกเมื่อจาก Atlas เล่มนี้`,
      ),
    )
    .button1(tr(p, "Not yet", "ยังก่อน"))
    .button2(tr(p, "§aBegin", "§aเริ่มเลย"))
    .show(p)
    .then((r) => {
      if (r.canceled || r.selection !== 1) return;
      startFor(p, b, consume);
    })
    .catch(() => undefined);
}

export function startFor(p: Player, b: BossDefinition, consume: boolean): void {
  if (consume && !takeOne(p, b.summonItem)) {
    p.sendMessage(tr(p, "§cThe summoning relic is missing.", "§cไม่พบไอเท็มเรียกบอส"));
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
    actions.push(() => p.sendMessage(a.forcePhase(0) ? "§aPhase skip requested" : "§7Not possible right now"));
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
