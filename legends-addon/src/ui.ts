/**
 * Codex of Legends: a small out-of-combat book (server-ui forms). All lore and
 * instructions live here, so the fights themselves need almost no text.
 */
import { Player } from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";
import { BossKey } from "./bosses/boss.js";

interface Entry {
  key: BossKey;
  title: string;
  lore: string;
  summon: string;
  tips: string;
}

const ENTRIES: Entry[] = [
  {
    key: "taotie",
    title: "§6Taotie — The Devouring Maw",
    lore: "One of the Four Fiends. A hunger cast in ritual bronze; in the end it devours even its own body.",
    summon: "Bronze Ding of Gluttony: nether star, gold & copper blocks, cakes, golden carrots.",
    tips: "Jump the bronze quake rings. Never stand in front of its open maw. When the Maw of Ten Thousand Feasts opens, hide behind a fallen ding vessel. It eats dropped items to heal.",
  },
  {
    key: "nidhogg",
    title: "§2Níðhöggr — Gnawer of the World-Root",
    lore: "The dread wyrm beneath Yggdrasil, malice-striker of Náströnd, who flies at Ragnarök.",
    summon: "Gnawed Root of Yggdrasil: nether star, mangrove roots, echo shards, dragon's breath.",
    tips: "Do not stand behind it. Cracks in the ground mean it is coming up beneath you. In Ragnarök, flee the great circle — then strike while it lies exhausted.",
  },
  {
    key: "hanuman",
    title: "§fHanuman — Son of the Wind",
    lore: "The white monkey champion of the Ramakien: diamond-haired, crystal-fanged, master of the trident.",
    summon: "Wind-Crystal Trident: nether star, diamonds, gold blocks, breeze rod.",
    tips: "When he glows gold, stop attacking or he will counter. A sudden gust means he steps behind you. When he falls, break the four wind wisps quickly or the wind revives him.",
  },
  {
    key: "alicorn",
    title: "§dAlicorn — Dawnstar Sovereign",
    lore: "Pegasus and unicorn made one: the morning star given wings.",
    summon: "Horn of the Dawnstar: nether star, amethyst, phantom membranes, feather, glowstone.",
    tips: "Read the horn: RED = ground strike, BLUE = projectiles, GOLD = charge. Break the prisms to lower her barrier. Interrupt her healing. At Dawnbreak, stand in a golden sigil.",
  },
  {
    key: "tenko",
    title: "§bTenko — The Ten-Tailed Fox",
    lore: "A celestial fox beyond the nine tails; the tenth tail holds the moon in eclipse.",
    summon: "Ten-Tailed Star Pearl: nether star, eye of ender, soul lanterns, blaze powder, glow berries.",
    tips: "Lanterns burst clockwise in rhythm. Illusions are paler — the real fox may swap places. Jump the kagura rings on the bell. During the Eclipse, run with the gaps between the rays.",
  },
  {
    key: "logos",
    title: "§eThe Word of God",
    lore: "In the beginning was the Word. Attended by the Seraph, the Cherub and the Ophan of the Thrones.",
    summon: "The Unspoken Word: the five Legend cores, nether star, book, gold blocks.",
    tips: "Break the Cherub's ward by hurting the Cherub. Step onto the unlit squares of Fiat Lux. Jump the trumpet rings. At the Final Word, reach the flaming sword of Eden.",
  },
];

export async function openCodex(p: Player): Promise<void> {
  const f = new ActionFormData().title("Codex of Legends").body(
    "Six legends answer the sigils. Craft a sigil, hold it and use it on open ground.\n\n" +
      "Colour language of every fight:\n§cRED§r = damage will land here\n§6GOLD§r = safe ground\n" +
      "Bosses only speak on the action bar: awakening, phase, ultimate.",
  );
  for (const e of ENTRIES) f.button(e.title);
  try {
    const r = await f.show(p);
    if (r.canceled || r.selection === undefined) return;
    const e = ENTRIES[r.selection];
    const d = new ActionFormData().title(e.title).body(`${e.lore}\n\n§lSummon§r\n${e.summon}\n\n§lSurvival notes§r\n${e.tips}`).button("Back");
    const r2 = await d.show(p);
    if (!r2.canceled) await openCodex(p);
  } catch {
    // player busy / form closed
  }
}
