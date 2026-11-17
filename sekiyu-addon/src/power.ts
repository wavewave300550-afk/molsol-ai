import { EquipmentSlot, ItemStack, Player } from "@minecraft/server";
import { DP, ENT, Form, IDS, PROP } from "./config.js";
import { center, P, particle, S, shake, sound } from "./core/fx.js";
import { add, v } from "./core/vec.js";
import { removeOwned, spawnConstruct } from "./constructs.js";
import { later } from "./core/tasks.js";
import { isOwner, now, OilState, state } from "./state.js";

/** Push form / burning into the client-synced player properties (only when changed). */
export function syncProperties(p: Player, s?: OilState): void {
  const owner = isOwner(p);
  const st = s ?? (owner ? state(p) : undefined);
  const form = owner && st ? st.form : Form.None;
  const burning = owner && st ? st.burningUntil > now() : false;
  try {
    if (st && st.synced.form === form && st.synced.burning === burning) return;
    if (p.getProperty(PROP.form) !== form) p.setProperty(PROP.form, form);
    if (p.getProperty(PROP.burning) !== burning) p.setProperty(PROP.burning, burning);
    if (st) st.synced = { form, burning };
  } catch (e) {
    if (st) st.synced = { form, burning };
    console.warn(`[sekiyu] cannot set player properties (is the behaviour pack player.json active?): ${e}`);
  }
}

export function holdingCore(p: Player): boolean {
  try {
    return p.getComponent("minecraft:inventory")?.container?.getItem(p.selectedSlotIndex)?.typeId === IDS.core;
  } catch {
    return false;
  }
}

export function hasCore(p: Player): boolean {
  const inv = p.getComponent("minecraft:inventory")?.container;
  if (!inv) return false;
  for (let i = 0; i < inv.size; i++) if (inv.getItem(i)?.typeId === IDS.core) return true;
  try {
    return p.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Offhand)?.typeId === IDS.core;
  } catch {
    return false;
  }
}

export function giveCore(p: Player): boolean {
  if (hasCore(p)) return false;
  const left = p.getComponent("minecraft:inventory")?.container?.addItem(new ItemStack(IDS.core, 1));
  if (left) p.dimension.spawnItem(left, p.location);
  return true;
}

/** Clear everything transient (death, revoke). Ownership is untouched. */
export function resetRuntime(p: Player): void {
  const s = state(p);
  s.form = Form.Human;
  s.burningUntil = 0;
  s.followUp = undefined;
  s.dissolvedUntil = 0;
  s.fallGuardUntil = 0;
  s.activeSkill = "";
  s.sealed = false;
  s.synced = { form: -1, burning: false };
  for (const id of ["invisibility", "speed", "resistance"] as const) {
    try {
      const e = p.getEffect(id);
      if (e && e.duration <= 60) p.removeEffect(id);
    } catch {
      // dead
    }
  }
  removeOwned(p.id, ENT.serpent);
  removeOwned(p.id, ENT.prison);
  removeOwned(p.id, ENT.tide);
  syncProperties(p, s);
}

/** Eating the fruit. Returns false if this player already owns the power. */
export function grantPower(p: Player): boolean {
  if (isOwner(p)) return false;
  p.setDynamicProperty(DP.owner, true);
  resetRuntime(p);
  giveCore(p);
  const dim = p.dimension;
  // the fruit rises out of the player as a 3D relic and melts into oil
  const relic = spawnConstruct(dim, ENT.relic, add(p.location, v(0, 0.6, 0)), p.id, p.getRotation().y);
  later(36, () => {
    if (relic?.isValid) {
      particle(dim, P.splash, center(relic));
      relic.remove();
    }
  });
  particle(dim, P.column, p.location);
  particle(dim, P.drip, center(p));
  sound(dim, S.awaken, p.location, 1, 1);
  shake(p, 0.2, 1.0);
  p.onScreenDisplay.setTitle("§l§6Sekiyu Sekiyu no Mi", {
    subtitle: "§7Logia: §8Petroleum §7- your body turns to crude oil",
    fadeInDuration: 5,
    stayDuration: 70,
    fadeOutDuration: 15,
  });
  p.sendMessage(
    "§6§lSekiyu Sekiyu no Mi§r §7- Logia: Petroleum\n" +
      "§7You received the §6Crude Core§7. Hold it and:\n" +
      "§f - Use§7 (tap & hold / right-click) = cast the selected ability\n" +
      "§f - Use again§7 while it is active = §cignite§7 it (or reform / afterburn)\n" +
      "§f - Press Sneak§7 = next ability §8(looking up = previous)\n" +
      "§f - Sneak + Use§7 = §6Oil Console§7 (abilities, Logia form, HUD)\n" +
      "§7Physical blows flow through your oily body. §bWater§7 and §btridents§7 are your weakness; fire hurts more as oil.\n" +
      "§8Lost the core? /sekiyu:core",
  );
  state(p).hudUntil = now() + 200;
  return true;
}

export function revokePower(p: Player): void {
  resetRuntime(p);
  p.setDynamicProperty(DP.owner, undefined);
  syncProperties(p);
}
