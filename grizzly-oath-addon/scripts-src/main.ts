// Grizzly's Oath - Historical Artifacts 001 (Hugh Glass)
//
// Controls (designed for touch screens / iPhone, work the same with mouse or controller):
//   attack (tap a mob / left click)   -> Frontier Cleave, the normal heavy axe attack
//   use    (tap the screen / right click / tap a block) -> cast the selected special skill
//   sneak + use                       -> select the next special skill (1 -> 2 -> 3 -> 4 -> 1)
// While the axe is held, the action bar shows the selected skill and every cooldown.
import { Block, EntitySwingSource, ItemStack, Player, system, world } from "@minecraft/server";
import { restore } from "./awaken.js";
import { removeOrphanFx, sweepFx, tickBleeds } from "./combat.js";
import { AWAKENED_ID, AXE_ID, PROP_HINT, PROP_SKILL, SKILLS } from "./config.js";
import { sound } from "./fx.js";
import { castSelected, cleaveImpact, flash, frontierCleave, tickWill } from "./skills.js";
import { dropState, now, state } from "./state.js";

const USE_DEBOUNCE = 6;

export const isOathItem = (item?: ItemStack): boolean => !!item && (item.typeId === AXE_ID || item.typeId === AWAKENED_ID);

function mainHand(p: Player): ItemStack | undefined {
  try {
    return p.getComponent("minecraft:inventory")?.container?.getItem(p.selectedSlotIndex);
  } catch {
    return undefined;
  }
}

function onUse(p: Player): void {
  const st = state(p);
  const t = now();
  if (t - st.lastUse < USE_DEBOUNCE) return;
  st.lastUse = t;
  if (p.isSneaking) {
    st.skill = (st.skill + 1) % SKILLS.length;
    try {
      p.setDynamicProperty(PROP_SKILL, st.skill);
    } catch {
      // ignore
    }
    const def = SKILLS[st.skill];
    flash(st, `§7Skill §8» ${def.color}§l${st.skill + 1}. ${def.name}`, 30);
    sound(p.dimension, "grizzly_oath.select", p.location, 1, 0.9 + st.skill * 0.1);
    showHud(p, t);
    return;
  }
  castSelected(p);
  showHud(p, t);
}

// Interactive blocks keep working normally while the axe is held.
const INTERACTIVE = /door|gate|trapdoor|button|lever|chest|barrel|shulker|table|furnace|smoker|anvil|bed|bell|lectern|crafter|hopper|dispenser|dropper|loom|stonecutter|grindstone|cartography|enchant|brewing|beacon|noteblock|jukebox|cake|campfire|cauldron|composter|respawn|sign|frame|repeater|comparator|daylight|vault|spawner|bookshelf/;

function isInteractive(block: Block): boolean {
  try {
    if (block.getComponent("minecraft:inventory")) return true;
    return INTERACTIVE.test(block.typeId);
  } catch {
    return true;
  }
}

// ---------------------------------------------------------------- events

world.afterEvents.itemUse.subscribe((ev) => {
  if (isOathItem(ev.itemStack)) onUse(ev.source);
});

// On touch screens a tap on the ground is "use on block", not "use": treat it the same.
world.beforeEvents.playerInteractWithBlock.subscribe((ev) => {
  if (!ev.isFirstEvent || !isOathItem(ev.itemStack) || isInteractive(ev.block)) return;
  const p = ev.player;
  system.run(() => {
    if (p.isValid) onUse(p);
  });
});

world.afterEvents.playerSwingStart.subscribe((ev) => {
  if (ev.swingSource === EntitySwingSource.Attack && isOathItem(ev.heldItemStack)) frontierCleave(ev.player);
});

world.afterEvents.entityHitEntity.subscribe((ev) => {
  const p = ev.damagingEntity;
  if (p.typeId !== "minecraft:player" || !ev.hitEntity.isValid) return;
  if (isOathItem(mainHand(p as Player))) cleaveImpact(p as Player, ev.hitEntity);
});

world.afterEvents.playerLeave.subscribe((ev) => {
  sweepFx(now(), { owner: ev.playerId });
  dropState(ev.playerId);
});

world.afterEvents.playerSpawn.subscribe((ev) => {
  // e.g. died during the Ultimate: hand back the normal axe
  if (state(ev.player).ultUntil < now() || !ev.initialSpawn) restore(ev.player);
});

world.afterEvents.worldLoad.subscribe(() => {
  removeOrphanFx();
});

// ---------------------------------------------------------------- HUD

function showHud(p: Player, t: number): void {
  const st = state(p);
  const sel = SKILLS[st.skill];
  const left = st.readyAt[st.skill] - t;
  let top = `${sel.color}§l${st.skill + 1}. ${sel.name}§r ${left > 0 ? `§7${(left / 20).toFixed(1)}s` : "§aREADY"}`;
  if (st.flashUntil > t) top = st.flashText;
  const slots = SKILLS.map((s, i) => {
    const l = st.readyAt[i] - t;
    const label = l > 0 ? `${Math.ceil(l / 20)}s` : "OK";
    if (i === st.skill) return `§f§l[${i + 1}:${l > 0 ? "§7" : "§a"}${label}§f]§r`;
    return `§8${i + 1}:${l > 0 ? "§7" : "§2"}${label}`;
  }).join(" ");
  const will = st.willUntil > t ? `  §4§lWILL ${"I".repeat(Math.max(1, st.willTier))}§r §7${Math.ceil((st.willUntil - t) / 20)}s` : "";
  try {
    p.onScreenDisplay.setActionBar(`${top}\n${slots}${will}`);
  } catch {
    // ignore
  }
}

function hintOnce(p: Player): void {
  try {
    if (p.getDynamicProperty(PROP_HINT)) return;
    p.setDynamicProperty(PROP_HINT, true);
    p.sendMessage(
      "§4§lGrizzly's Oath§r §7- §fAttack§7 = Frontier Cleave · §fUse§7 (tap) = cast skill · §fSneak + Use§7 = next skill",
    );
  } catch {
    // ignore
  }
}

// ---------------------------------------------------------------- main loop

system.runInterval(() => {
  const t = now();
  tickBleeds(t);
  for (const p of world.getPlayers()) {
    const st = state(p);
    tickWill(p, st, t);
    if (t % 4 === 0 && isOathItem(mainHand(p))) {
      hintOnce(p);
      showHud(p, t);
    }
    if (t % 20 === 0 && st.ultUntil < t) restore(p);
  }
  if (t % 10 === 0) sweepFx(t);
}, 1);

system.run(() => {
  removeOrphanFx();
});
