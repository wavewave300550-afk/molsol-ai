import { Player, system } from "@minecraft/server";
import { ActionFormData, ActionFormResponse, FormCancelationReason, MessageFormData, MessageFormResponse } from "@minecraft/server-ui";
import { fight } from "./session.js";

type AnyForm = ActionFormData | MessageFormData;
type AnyResponse = ActionFormResponse | MessageFormResponse;

/** Show a form, retrying while the player is busy (e.g. chat or inventory still closing). */
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

const LORE =
  "§7An emperor-dragon had its body remade in imperial porcelain so it could rule forever. " +
  "When its Mandate of Heaven cracked, the court filled every crack with gold - and every break made it stronger.\n\n" +
  "§6Breaking this seal opens §lThe Fractured Mandate§r§6, the Emperor's own dimension.§r\n" +
  "§7Players within 12 blocks are taken with you. You return to this spot when you leave.\n\n" +
  "§eTips:§r §7shatter embedded shards before the Emperor reclaims them, read the red seals on the floor, " +
  "kneel (sneak) when the third gong falls.";

/** Using the Cracked Imperial Seal (or the join/leave commands) opens the right menu. */
export async function sealMenu(p: Player): Promise<void> {
  if (fight.inMandate(p)) {
    if (fight.state === "victory") {
      const res = await show<ActionFormResponse>(p, new ActionFormData()
        .title("§6The Mended Mandate")
        .body("§7The Emperor is at peace. Walk through the Moon Gate or return now.")
        .button("§2Return home")
        .button("§8Stay a while"));
      if (res && !res.canceled && res.selection === 0) fight.returnHome(p, "§6You leave the mended Mandate.");
      return;
    }
    const res = await show<MessageFormResponse>(p, new MessageFormData()
      .title("§cLeave the Mandate?")
      .body("§7Leaving now forfeits your place in the battle. Your companions fight on.\n\n§7If no one remains, the Emperor mends itself and the Mandate closes.")
      .button1("§cLeave the battle")
      .button2("§aStay and fight"));
    if (res && !res.canceled && res.selection === 0) fight.returnHome(p, "§7You fled the Fractured Mandate.");
    return;
  }
  if (fight.state === "battle" || fight.state === "intro") {
    const res = await show<ActionFormResponse>(p, new ActionFormData()
      .title("§6The Mandate is open")
      .body("§7The Porcelain Emperor is already fighting. Join the battle? (The seal is not used.)")
      .button("§6Join the battle")
      .button("§8Not now"));
    if (res && !res.canceled && res.selection === 0) fight.join(p);
    return;
  }
  if (fight.state !== "idle") {
    p.sendMessage("§7The Mandate is unfolding... try again in a moment.");
    return;
  }
  const res = await show<MessageFormResponse>(p, new MessageFormData()
    .title("§6Cracked Imperial Seal")
    .body(LORE)
    .button1("§6Break the seal")
    .button2("§8Not yet"));
  if (res && !res.canceled && res.selection === 0) await fight.start(p, true);
}

export async function respawnPrompt(p: Player): Promise<void> {
  if (fight.state !== "battle" && fight.state !== "intro") return;
  const res = await show<ActionFormResponse>(p, new ActionFormData()
    .title("§6The Mandate still stands")
    .body("§7You fell, but the battle goes on. Return to the Fractured Mandate?\n§8(Your dropped items were sent to where you entered.)")
    .button("§6Return to the battle")
    .button("§8Stay here"));
  if (res && !res.canceled && res.selection === 0) fight.join(p);
}

fight.respawnPrompt = (p) => void respawnPrompt(p);
