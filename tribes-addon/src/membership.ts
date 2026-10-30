import { EntityInventoryComponent, ItemStack, Player } from "@minecraft/server";
import { burst, center, ring, sound } from "./core/fx.js";
import { getRace, now, Race, setRace, state, syncRaceProperty } from "./core/state.js";
import { add, v } from "./core/vec.js";
import { dismissAll } from "./summons.js";
import { ALL_PASSIVE_EFFECTS, CODEX_ITEM, TRIBES, tribeOf } from "./tribes/index.js";
import { Tribe } from "./tribes/types.js";

const PERMANENT = 20000000;
const PERMANENT_THRESHOLD = 1000000;

function inventory(player: Player) {
  return player.getComponent(EntityInventoryComponent.componentId)?.container;
}

export function hasItem(player: Player, typeId: string): boolean {
  const inv = inventory(player);
  if (!inv) return false;
  for (let i = 0; i < inv.size; i++) if (inv.getItem(i)?.typeId === typeId) return true;
  return false;
}

export function giveItem(player: Player, typeId: string, lore?: string[]): void {
  const stack = new ItemStack(typeId, 1);
  if (lore) stack.setLore(lore);
  const left = inventory(player)?.addItem(stack);
  if (left) player.dimension.spawnItem(left, player.location);
}

export function giveRelic(player: Player, tribe: Tribe): void {
  if (hasItem(player, tribe.relic)) {
    player.sendMessage(`${tribe.color}[${tribe.name}] §7You already carry your relic.`);
    return;
  }
  giveItem(player, tribe.relic, [
    `${tribe.color}Relic of the ${tribe.name}`,
    "§7Use: cast selected ability",
    "§7Sneak + Use: next ability",
  ]);
}

export function giveCodex(player: Player): void {
  if (!hasItem(player, CODEX_ITEM)) giveItem(player, CODEX_ITEM, ["§dChoose and study your tribe", "§7Use to open"]);
}

/** Remove relics that belong to other tribes so a player never carries a dead relic. */
function removeForeignRelics(player: Player, keep?: string): void {
  const inv = inventory(player);
  if (!inv) return;
  const relics = new Set(TRIBES.map((t) => t.relic));
  for (let i = 0; i < inv.size; i++) {
    const it = inv.getItem(i);
    if (it && relics.has(it.typeId) && it.typeId !== keep) inv.setItem(i, undefined);
  }
}

/** Keep the current tribe's permanent effects; strip permanent passives left by other tribes. */
export function applyPassives(player: Player): void {
  const tribe = tribeOf(getRace(player));
  const wanted = new Map((tribe?.passiveEffects ?? []).map((p) => [p.effect, p.amplifier]));
  for (const id of ALL_PASSIVE_EFFECTS) {
    const cur = player.getEffect(id);
    const amp = wanted.get(id);
    if (amp === undefined) {
      if (cur && cur.duration > PERMANENT_THRESHOLD) player.removeEffect(id);
      continue;
    }
    if (!cur || cur.amplifier < amp || (cur.amplifier === amp && cur.duration < PERMANENT_THRESHOLD)) {
      player.addEffect(id, PERMANENT, { amplifier: amp, showParticles: false });
    }
  }
}

export function joinTribe(player: Player, tribe: Tribe | undefined): void {
  const previous = getRace(player);
  dismissAll(player);
  setRace(player, tribe ? tribe.race : Race.None);
  applyPassives(player);
  removeForeignRelics(player, tribe?.relic);
  const s = state(player);
  s.hudUntil = now() + 100;
  if (!tribe) {
    player.sendMessage("§7You walk alone again. Your tribal powers fade.");
    return;
  }
  giveRelic(player, tribe);
  player.onScreenDisplay.setTitle(`${tribe.color}${tribe.name}`, {
    subtitle: `§7${tribe.epithet}`,
    fadeInDuration: 10,
    stayDuration: 60,
    fadeOutDuration: 20,
  });
  const dim = player.dimension;
  const color = tribe.key === "dinosauroid" ? "green" : tribe.key === "anunnaki" ? "gold" : tribe.key === "pastafarian" ? "noodle" : "cyan";
  burst(dim, color, center(player));
  ring(dim, color, add(player.location, v(0, 0.2, 0)), 1.5);
  ring(dim, color, add(player.location, v(0, 1.2, 0)), 1.0);
  sound(dim, "random.totem", player.location, 0.6, 1.2);
  player.sendMessage(
    `${tribe.color}§l${tribe.name}§r §7- ${previous !== Race.None ? "you have changed allegiance." : "welcome to your tribe."}\n` +
      `§7Hold your relic (${tribe.color}${tribe.relic.split(":")[1].replace(/_/g, " ")}§7): §fUse§7 casts, §fSneak+Use§7 selects the next ability.`,
  );
}

export function resyncPlayer(player: Player): void {
  syncRaceProperty(player);
  applyPassives(player);
}
