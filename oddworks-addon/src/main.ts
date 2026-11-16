// ODDWORKS - Fantasy Equipment, Set 01
// Solar Frost Goggles · Endless Handline · Bamboo Sword Cane
import {
  CommandPermissionLevel, CustomCommandStatus, EntityComponentTypes, ItemStack, Player, system, world,
} from "@minecraft/server";
import { FX_ENTITIES, ID, ODD_ITEMS } from "./config.js";
import { initWeather } from "./core/env.js";
import { container, convertStack, ensureLore, heldType, LORE } from "./core/items.js";
import { allStates, dropState, hint, now, PlayerState, stateOf } from "./core/state.js";
import { forgetEntity } from "./core/targets.js";
import * as cane from "./items/cane.js";
import * as goggles from "./items/goggles.js";
import * as line from "./items/handline.js";
import { clearWounds, countBleeding, tickBleed } from "./systems/bleed.js";
import { clearSkips, hooks, initDamagePipeline } from "./systems/damage.js";
import { clearDazzle, tickDazzle } from "./systems/dazzle.js";
import { forgetFrost, tickFrost } from "./systems/frost.js";
import { secs } from "./items/goggles.js";

// ------------------------------------------------------------------ startup: custom command

const GUIDE = [
  "§6§lODDWORKS §r§7- Fantasy Equipment, Set 01",
  "§b Solar Frost Goggles§7: hold Use to drink sunlight, release for a §bGlacial Beam§7 (freezes mobs, water, lava).",
  "§7   Sneak+Use: §fSnowblind§7 glare. Sneak+hold Use while staring at the sun: catch a §6Sun Dog§7 (portable noon).",
  "§a Endless Handline§7: hold Use to whirl overhead, release to cast up to 96 blocks.",
  "§7   Line out: hold Use to reel/haul (weight decides who moves), Sneak pays out, Sneak+Use §cSnaps§7.",
  "§7   Hooks blocks (grapple, swing), mobs, boats (tow / kedge), dropped items, fish (float in water).",
  "§f Bamboo Sword Cane§7: hold Use, release on the glint for an §fIai§7 draw-cut dash.",
  "§7   Drawn: Use to §bDeflect§7 (riposte), Sneak+Use for §cNoto§7: sheathe and open every wound at once.",
  "§8 Cuts bleed by creature; armour, bone, metal and fire resist. Full guide: README in the add-on folder.",
];

system.beforeEvents.startup.subscribe((ev) => {
  try {
    ev.customCommandRegistry.registerCommand(
      { name: "oddworks:guide", description: "How to use the ODDWORKS equipment", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: false },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
        system.run(() => {
          for (const l of GUIDE) p.sendMessage(l);
        });
        return { status: CustomCommandStatus.Success };
      },
    );
  } catch {
    /* command registry unavailable */
  }
});

// ------------------------------------------------------------------ wiring

initWeather();
initDamagePipeline();
hooks.deflectWindow = cane.deflectWindow;
hooks.onDeflect = cane.onDeflect;
hooks.onHeavyBlow = cane.onHeavyBlow;
hooks.onCut = cane.onCut;
hooks.tethered = line.tethered;
hooks.onMiss = (attacker) => {
  if (!attacker.isValid) return;
  try {
    attacker.dimension.spawnParticle("oddworks:dazzle_stars", attacker.getHeadLocation());
  } catch {
    /* cosmetic */
  }
};

world.afterEvents.itemStartUse.subscribe((ev) => {
  const p = ev.source;
  const id = ev.itemStack?.typeId;
  if (!id || !ODD_ITEMS.has(id)) return;
  const s = stateOf(p);
  s.using = true;
  s.usingItem = id;
  if (id === ID.goggles) goggles.startUse(p, s);
  else if (id === ID.handline || id === ID.handlineCast) line.startUse(p, s, id);
  else cane.startUse(p, s, id);
});

function doRelease(p: Player, s: PlayerState, id: string): void {
  s.using = false;
  if (id === ID.goggles) goggles.release(p, s);
  else if (id === ID.handline || id === ID.handlineCast) line.release(p, s, id);
  else cane.release(p, s, id);
}

function doCancel(p: Player, s: PlayerState, id: string | undefined): void {
  s.using = false;
  if (id === ID.goggles) goggles.endUse(p, s);
  else if (id === ID.handline || id === ID.handlineCast) line.stopUse(p, s);
  else if (id === ID.cane || id === ID.caneDrawn) cane.stopUse(p, s);
}

world.afterEvents.itemReleaseUse.subscribe((ev) => {
  const p = ev.source;
  const s = stateOf(p);
  const id = ev.itemStack?.typeId ?? s.usingItem;
  if (!s.using || !id || !ODD_ITEMS.has(id)) {
    s.using = false;
    return;
  }
  doRelease(p, s, id);
});

// itemStopUse arrives on release as well as on interruptions. If no release event has been
// handled by the next tick and the same item is still in hand, the use ended by letting go.
world.afterEvents.itemStopUse.subscribe((ev) => {
  const p = ev.source;
  const s = stateOf(p);
  const id = ev.itemStack?.typeId ?? s.usingItem;
  if (!s.using || !id || !ODD_ITEMS.has(id)) return;
  const slot = p.selectedSlotIndex;
  system.run(() => {
    if (!s.using || !p.isValid) return;
    if (p.selectedSlotIndex === slot && heldType(p) === id) doRelease(p, s, id);
    else doCancel(p, s, id);
  });
});

world.afterEvents.projectileHitBlock.subscribe((ev) => line.onHookHitBlock(ev));
world.afterEvents.projectileHitEntity.subscribe((ev) => line.onHookHitEntity(ev));

world.afterEvents.entityDie.subscribe((ev) => {
  const id = ev.deadEntity.id;
  forgetFrost(id);
  clearWounds(id);
  clearDazzle(id);
  forgetEntity(id);
  if (ev.deadEntity instanceof Player) teardown(ev.deadEntity, stateOf(ev.deadEntity));
});

world.afterEvents.playerDimensionChange.subscribe((ev) => {
  const s = stateOf(ev.player);
  teardown(ev.player, s);
});

world.beforeEvents.playerLeave.subscribe((ev) => {
  const id = ev.player.id;
  system.run(() => {
    for (const s of allStates()) {
      if (s.id !== id) continue;
      teardown(undefined, s);
    }
    dropState(id);
  });
});

/** Dropped drawn canes / line-out reels revert to their resting form. */
world.afterEvents.entitySpawn.subscribe((ev) => {
  const e = ev.entity;
  if (e.typeId !== "minecraft:item") return;
  let stack: ItemStack | undefined;
  try {
    stack = e.getComponent(EntityComponentTypes.Item)?.itemStack;
  } catch {
    return;
  }
  const base = stack?.typeId === ID.caneDrawn ? ID.cane : stack?.typeId === ID.handlineCast ? ID.handline : undefined;
  if (!stack || !base) return;
  const st = stack;
  system.run(() => {
    try {
      if (!e.isValid) return;
      const at = e.location;
      const dim = e.dimension;
      e.remove();
      dim.spawnItem(convertStack(st, base), at);
    } catch {
      /* ignore */
    }
  });
});

function teardown(p: Player | undefined, s: PlayerState): void {
  if (s.line.phase !== "idle") line.retract(p, s, true);
  if (s.sunDog) goggles.dismissSunDog(p, s);
  s.using = false;
  s.goggles.mode = "none";
  s.cane.gripping = false;
  s.cane.notoAt = -1;
}

// ------------------------------------------------------------------ per tick

/** Drawn blades sheathe themselves and line-out reels wind in when not in hand. */
function normaliseInventory(p: Player, s: PlayerState): void {
  const inv = container(p);
  if (!inv) return;
  for (let i = 0; i < inv.size; i++) {
    if (i === p.selectedSlotIndex) continue;
    const it = inv.getItem(i);
    if (!it) continue;
    if (it.typeId === ID.caneDrawn) inv.setItem(i, convertStack(it, ID.cane));
    else if (it.typeId === ID.handlineCast && s.line.phase === "idle") inv.setItem(i, convertStack(it, ID.handline));
  }
}

function onSlotChange(p: Player, s: PlayerState, from: number): void {
  s.using = false;
  if (s.goggles.mode !== "none") goggles.endUse(p, s);
  if (s.cane.gripping) cane.stopUse(p, s);
  s.cane.notoAt = -1;
  const inv = container(p);
  const old = inv?.getItem(from);
  if (old?.typeId === ID.caneDrawn) {
    inv?.setItem(from, convertStack(old, ID.cane));
    try {
      p.dimension.playSound("oddworks.cane.sheathe", p.location, { volume: 0.6, pitch: 1.1 });
    } catch {
      /* ignore */
    }
  }
}

function hud(p: Player, s: PlayerState, held: string | undefined): void {
  const t = now();
  let text = "";
  if (s.hint && s.hint.until >= t) text = s.hint.text;
  else if (held === ID.goggles) {
    const inf = goggles.info(p, s);
    const tag = { sun: "§eclear sun", snow: "§bsnow glare", overcast: "§7overcast", moon: "§9moonlight", torch: "§6torchlight", dark: "§8darkness", sundog: "§6sun dog" }[inf.source];
    const g = s.goggles;
    const beam = g.mode === "charge"
      ? `§bBeam ${"|".repeat(Math.round(g.charge * 10))}§8${"|".repeat(10 - Math.round(g.charge * 10))} §f${Math.round(g.charge * 100)}%`
      : (s.cd.get("beam") ?? 0) <= t ? "§bBeam ready" : `§8Beam ${secs((s.cd.get("beam") ?? 0) - t)}`;
    const flash = (s.cd.get("flash") ?? 0) <= t ? "§fGlare ready" : `§8Glare ${secs((s.cd.get("flash") ?? 0) - t)}`;
    text = `§eLight §f${Math.round(inf.power * 100)}%§7 (${tag}§7) §8| ${beam} §8| ${flash} §8| ${goggles.sunDogStatus(s)}`;
  } else if (held === ID.handline || held === ID.handlineCast || s.line.phase !== "idle") {
    text = line.lineStatus(p, s);
  } else if (held === ID.cane || held === ID.caneDrawn) {
    text = cane.caneStatus(s, held, countBleeding(p.id));
  } else if (s.sunDog) {
    text = goggles.sunDogStatus(s);
  }
  if (!text) return;
  if (text === s.lastHud && t - s.lastHudTick < 30) return;
  s.lastHud = text;
  s.lastHudTick = t;
  try {
    p.onScreenDisplay.setActionBar(text);
  } catch {
    /* ignore */
  }
}

let started = false;

function startupCleanup(): void {
  started = true;
  goggles.restoreLights();
  for (const d of ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"]) {
    try {
      const dim = world.getDimension(d);
      for (const type of FX_ENTITIES) for (const e of dim.getEntities({ type })) e.remove();
    } catch {
      /* ignore */
    }
  }
}

system.runInterval(() => {
  if (!started) startupCleanup();
  const t = now();
  const players = world.getAllPlayers();
  const byId = new Map<string, Player>();
  for (const p of players) {
    byId.set(p.id, p);
    try {
      const s = stateOf(p);
      const held = heldType(p);
      hooks.held.set(p.id, held ?? "");
      if (p.selectedSlotIndex !== s.lastSlot) {
        onSlotChange(p, s, s.lastSlot);
        s.lastSlot = p.selectedSlotIndex;
      }
      if (held && ODD_ITEMS.has(held) && !s.loreChecked.has(held) && LORE[held]) {
        ensureLore(p);
        s.loreChecked.add(held);
      }
      if (t % 20 === (p.id.length % 20)) normaliseInventory(p, s);
      const using = s.using && s.usingItem === held;
      if (held === ID.goggles) goggles.tickHeld(p, s, using);
      else if (s.goggles.mode === "charge" || s.goggles.mode === "sundog") goggles.endUse(p, s);
      if (s.line.phase !== "idle") line.tickLine(p, s, held === ID.handlineCast || (held === ID.handline && s.line.phase === "whirl"), using);
      if (held === ID.cane || held === ID.caneDrawn) cane.tickHeld(p, s, held, using);
      if (s.sunDog) goggles.tickSunDog(p, s);
      if (t % 2 === 0) hud(p, s, held);
    } catch (e) {
      console.warn(`[ODDWORKS] tick error: ${e}`);
    }
  }
  try {
    tickFrost();
    tickBleed(byId);
    tickDazzle();
  } catch (e) {
    console.warn(`[ODDWORKS] system tick error: ${e}`);
  }
  clearSkips();
}, 1);

world.afterEvents.playerSpawn.subscribe((ev) => {
  if (!ev.initialSpawn) return;
  const s = stateOf(ev.player);
  hint(s, "§6ODDWORKS§7 loaded - type §f/oddworks:guide§7 for controls", 80);
});
