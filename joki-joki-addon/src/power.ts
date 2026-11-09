import { EquipmentSlot, ItemStack, Player } from "@minecraft/server";
import { DP, IDS, Mode, PROP } from "./config.js";
import { chest, P, particle, S, shake, sound } from "./core/fx.js";
import { isOwner, now, state, SteamState } from "./state.js";

/** Push mode / heat / overheat into the client-synced actor properties (only when changed). */
export function syncProperties(p: Player, s?: SteamState): void {
  const owner = isOwner(p);
  const st = s ?? (owner ? state(p) : undefined);
  const mode = owner && st ? st.mode : 0;
  const heat = owner && st ? Math.max(0, Math.min(10, Math.round(st.heat / 10))) : 0;
  const over = owner && st ? st.overheatUntil > now() : false;
  try {
    if (st && st.synced.mode === mode && st.synced.heat === heat && st.synced.overheat === over) return;
    if (p.getProperty(PROP.mode) !== mode) p.setProperty(PROP.mode, mode);
    if (p.getProperty(PROP.heat) !== heat) p.setProperty(PROP.heat, heat);
    if (p.getProperty(PROP.overheat) !== over) p.setProperty(PROP.overheat, over);
    if (st) st.synced = { mode, heat, overheat: over };
  } catch (e) {
    if (st) st.synced = { mode, heat, overheat: over };
    console.warn(`[joki] cannot set player properties (is the behaviour pack's player.json active?): ${e}`);
  }
}

export function hasValve(p: Player): boolean {
  const inv = p.getComponent("minecraft:inventory")?.container;
  if (!inv) return false;
  for (let i = 0; i < inv.size; i++) if (inv.getItem(i)?.typeId === IDS.valve) return true;
  try {
    const off = p.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Offhand);
    if (off?.typeId === IDS.valve) return true;
  } catch {
    // no equippable on this platform
  }
  return false;
}

export function giveValve(p: Player): boolean {
  if (hasValve(p)) return false;
  const inv = p.getComponent("minecraft:inventory")?.container;
  const stack = new ItemStack(IDS.valve, 1);
  const left = inv?.addItem(stack);
  if (left) p.dimension.spawnItem(left, p.location);
  return true;
}

/** Clear everything transient (death, revoke, reload). Ownership is untouched. */
export function resetRuntime(p: Player): void {
  const s = state(p);
  s.heat = 0;
  s.mode = Mode.Normal;
  s.overheatUntil = 0;
  s.boostUntil = 0;
  s.redlineUntil = 0;
  s.igniting = false;
  s.knucklePrimedUntil = 0;
  s.fallGuardUntil = 0;
  s.airJumpsUsed = 0;
  s.activeSkill = "";
  s.synced = { mode: -1, heat: -1, overheat: false };
  syncProperties(p, s);
}

/** Eating the fruit: bind the power to this player. Returns false if they already own it. */
export function grantPower(p: Player): boolean {
  if (isOwner(p)) return false;
  p.setDynamicProperty(DP.owner, true);
  resetRuntime(p);
  giveValve(p);
  const dim = p.dimension;
  particle(dim, P.fruitAura, chest(p));
  particle(dim, P.ventRelease, p.location);
  sound(dim, S.awaken, p.location, 1, 1);
  shake(p, 0.25, 0.8);
  p.onScreenDisplay.setTitle("§l§cJōki Jōki no Mi", {
    subtitle: "§fYour blood boils... §7Steam Pressure awakened",
    fadeInDuration: 5,
    stayDuration: 60,
    fadeOutDuration: 15,
  });
  p.sendMessage(
    "§c§lJōki Jōki no Mi§r §7- Paramecia: Steam Pressure\n" +
      "§7You received a §6Steam Valve§7. Hold it and:\n" +
      "§f - Use§7 (tap & hold / right-click) = fire the selected ability\n" +
      "§f - Sneak + Use§7 = next ability §8(never fires)§7, looking up = previous\n" +
      "§f - Sneak + Use looking down§7 = §6Steam Console§7 (abilities, gears, HUD)\n" +
      "§7Watch the §cheat gauge§7: at 100% you §4OVERHEAT§7 and lose your powers for 10s.\n" +
      "§8Lost the valve? Type /joki:valve",
  );
  state(p).hudUntil = now() + 200;
  return true;
}

export function revokePower(p: Player): void {
  resetRuntime(p);
  p.setDynamicProperty(DP.owner, undefined);
  syncProperties(p);
}
