import { CommandPermissionLevel, Player, system, world } from "@minecraft/server";
import { ActionFormData, ActionFormResponse, FormCancelationReason, MessageFormData, MessageFormResponse } from "@minecraft/server-ui";
import { PVP_PROPERTY, pvpEnabled } from "./core/combat.js";
import { getRace, Race, state } from "./core/state.js";
import { giveRelic, joinTribe } from "./membership.js";
import { TRIBES, tribeOf } from "./tribes/index.js";
import { Tribe } from "./tribes/types.js";

type AnyForm = ActionFormData | MessageFormData;
type AnyResponse = ActionFormResponse | MessageFormResponse;

/** Show a form, retrying while the player is busy (e.g. chat still closing). */
async function show<T extends AnyResponse>(player: Player, form: AnyForm, tries = 20): Promise<T | undefined> {
  for (let i = 0; i < tries; i++) {
    const res = (await form.show(player)) as T;
    if (res.canceled && res.cancelationReason === FormCancelationReason.UserBusy) {
      await new Promise<void>((r) => system.runTimeout(() => r(), 5));
      continue;
    }
    return res;
  }
  return undefined;
}

function abilityBlock(tribe: Tribe): string {
  return tribe.abilities
    .map((a) => `${a.ultimate ? "§d" : tribe.color}§l${a.name}§r §8- ${a.cost} ${tribe.energyName}, ${(a.cooldown / 20).toFixed(a.cooldown % 20 ? 1 : 0)}s\n§f${a.description}`)
    .join("\n\n");
}

function tribeText(tribe: Tribe): string {
  return (
    `${tribe.color}§l${tribe.name}§r §7- ${tribe.epithet}\n\n` +
    `§f${tribe.lore}\n\n` +
    `${tribe.color}§lPASSIVES§r\n§7- ${tribe.passiveText.join("\n§7- ")}\n\n` +
    `${tribe.color}§lABILITIES§r §7(hold relic: Use = cast, Sneak+Use = next)\n${abilityBlock(tribe)}`
  );
}

export async function openCodex(player: Player): Promise<void> {
  const tribe = tribeOf(getRace(player));
  if (!tribe) return chooseTribe(player);

  const s = state(player);
  const isAdmin = player.commandPermissionLevel >= CommandPermissionLevel.GameDirectors;
  const form = new ActionFormData()
    .title("§lTribal Codex")
    .body(`You are ${tribe.color}§l${tribe.name}§r §7(${tribe.epithet})\n§7${tribe.energyName}: §f${Math.floor(s.energy)}/100`)
    .button(`${tribe.color}Tribe Guide\n§8passives & abilities`, tribe.icon)
    .button("§2Summon my Relic\n§8if it was lost", tribe.icon)
    .button("§5Study / Change Tribe\n§8all four tribes", "textures/items/tribes/tribal_codex")
    .button(`§3Ability HUD: ${s.hudEnabled ? "§aON" : "§cOFF"}\n§8energy bar while holding relic`);
  if (isAdmin) form.button(`§4PvP abilities: ${pvpEnabled() ? "§aON" : "§cOFF"}\n§8world rule (operators)`);

  const res = await show<ActionFormResponse>(player, form);
  if (!res || res.canceled || res.selection === undefined) return;
  switch (res.selection) {
    case 0:
      await guide(player, tribe, false);
      break;
    case 1:
      giveRelic(player, tribe);
      break;
    case 2:
      await chooseTribe(player);
      break;
    case 3:
      s.hudEnabled = !s.hudEnabled;
      player.setDynamicProperty("tribes:hud", s.hudEnabled);
      player.sendMessage(`§7Ability HUD ${s.hudEnabled ? "§aenabled" : "§cdisabled"}§7.`);
      break;
    case 4:
      world.setDynamicProperty(PVP_PROPERTY, !pvpEnabled());
      world.sendMessage(`§4[Tribes] §7Abilities ${pvpEnabled() ? "§ccan now hurt other tribes' players" : "§ano longer hurt players"}§7.`);
      break;
  }
}

async function chooseTribe(player: Player): Promise<void> {
  const current = getRace(player);
  const form = new ActionFormData()
    .title("§lChoose your Tribe")
    .body("§7Four peoples walk this world. Study each one, then swear yourself to a tribe.\n§8You can change later, but your relic and summons are lost.");
  for (const t of TRIBES) {
    form.button(`${t.color}§l${t.name}${t.race === current ? " §r§8(yours)" : ""}\n§r§8${t.epithet}`, t.icon);
  }
  if (current !== Race.None) form.button("§8Leave my tribe");
  const res = await show<ActionFormResponse>(player, form);
  if (!res || res.canceled || res.selection === undefined) return;
  if (res.selection >= TRIBES.length) {
    const ok = await confirm(player, "Leave tribe", "§7Abandon your tribe and lose its powers?");
    if (ok) joinTribe(player, undefined);
    return;
  }
  await guide(player, TRIBES[res.selection], true);
}

async function guide(player: Player, tribe: Tribe, offerJoin: boolean): Promise<void> {
  const current = getRace(player);
  const form = new ActionFormData().title(`${tribe.color}§l${tribe.name}`).body(tribeText(tribe));
  const canJoin = offerJoin && current !== tribe.race;
  if (canJoin) form.button(`${tribe.color}§lJoin the ${tribe.name}`, tribe.icon);
  form.button("§8Back");
  const res = await show<ActionFormResponse>(player, form);
  if (!res || res.canceled || res.selection === undefined) return;
  if (canJoin && res.selection === 0) {
    if (current !== Race.None) {
      const prev = tribeOf(current);
      const ok = await confirm(player, "Change tribe", `§7Leave the ${prev?.color ?? ""}${prev?.name ?? "tribe"}§7 and join the ${tribe.color}${tribe.name}§7?`);
      if (!ok) return;
    }
    joinTribe(player, tribe);
    return;
  }
  return offerJoin ? chooseTribe(player) : openCodex(player);
}

async function confirm(player: Player, title: string, body: string): Promise<boolean> {
  const res = await show<MessageFormResponse>(
    player,
    new MessageFormData().title(title).body(body).button1("§aYes").button2("§cNo"),
  );
  return !!res && !res.canceled && res.selection === 0;
}
