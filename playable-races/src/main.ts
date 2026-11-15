/**
 * Playable Races - Foundation Release (races 001-003).
 * Entry point: wires world events, the tick loops and the custom item components.
 * The vanilla player entity is NOT overridden; everything is driven from here.
 */
import { ButtonState, Entity, EntityHurtBeforeEvent, InputButton, ItemStack, Player, system, world } from "@minecraft/server";
import { ENTITY_MIRAGE, FRESH_PRESS_GAP, INPUT_DEBOUNCE, ITEM_CODEX, SAVE_INTERVAL } from "./config.js";
import { cast, cycle, endChannel, raceOf, refreshForm, selected, tickChannel } from "./core/abilities.js";
import { setWeather } from "./core/env.js";
import { holdingFocus } from "./core/forms.js";
import { privateParticle, rgb, RGB } from "./core/fx.js";
import { updateHud } from "./core/hud.js";
import { Session, all, drop, get, load, peek, save } from "./core/session.js";
import { settings } from "./core/settings.js";
import { aimTarget, chest } from "./core/targets.js";
import { cancel, startScheduler } from "./core/tasks.js";
import { warn } from "./core/util.js";
import { registerCommands } from "./commands.js";
import { integrity, restore } from "./lineage.js";
import { golemLightning, inWard } from "./races/golem.js";
import { moonhunt } from "./races/jackalope.js";
import { cleanupEnsnared, salamanderDrink } from "./races/salamander.js";
import { applyFog, bloodMoonTick, onBloodMoonChange } from "./systems/bloodmoon.js";
import { consume, markedBy, tickMarks } from "./systems/marks.js";
import { isMirage, pop, removeMiragesOf, tickMirages } from "./systems/mirage.js";
import { openCodex } from "./ui/menu.js";

const INTERACTIVE = /(door|chest|barrel|button|lever|gate|table|furnace|smoker|anvil|shulker|bed|hopper|dispenser|dropper|crafter|lectern|loom|grindstone|stonecutter|cartography|smithing|brewing|beacon|bell|cake|noteblock|repeater|comparator|daylight|jukebox|campfire|composter|cauldron|respawn_anchor|lodestone|trapdoor|sign|frame|decorated_pot|chiseled_bookshelf|vault|trial_spawner)/;

function players(): Player[] {
  try {
    return world.getPlayers();
  } catch {
    return [];
  }
}

function playerById(id: string): Player | undefined {
  return players().find((p) => p.id === id);
}

// ------------------------------------------------------------------ input

/**
 * One action per press: use events that keep arriving without a gap are a held button
 * (or a platform re-sending "use") and are ignored, so holding the button can never
 * re-cast, re-cycle or cancel an ability that is in progress.
 */
function useFocus(p: Player): void {
  const s = get(p);
  const now = system.currentTick;
  const fresh = now - s.lastRawInput >= FRESH_PRESS_GAP;
  s.lastRawInput = now;
  if (!fresh) return;
  if (now - s.lastInput < INPUT_DEBOUNCE) return; // debounce duplicate use packets
  s.lastInput = now;
  if (!raceOf(s)) {
    void openCodex(p);
    return;
  }
  if (p.isSneaking) cycle(p, s);
  else cast(p, s);
}

system.beforeEvents.startup.subscribe((ev) => {
  try {
    registerCommands(ev);
  } catch (e) {
    warn("command registration failed", e);
  }
  ev.itemComponentRegistry.registerCustomComponent("plrace:focus", {
    onUse: (e) => {
      const p = e.source;
      system.run(() => {
        if (p.isValid) useFocus(p);
      });
    },
  });
  ev.itemComponentRegistry.registerCustomComponent("plrace:codex", {
    onUse: (e) => {
      const p = e.source;
      system.run(() => {
        if (p.isValid) void openCodex(p);
      });
    },
  });
});

world.beforeEvents.playerInteractWithBlock.subscribe((ev) => {
  const it = ev.itemStack;
  if (!it || !it.hasTag("plrace:focus") || !ev.isFirstEvent) return;
  if (INTERACTIVE.test(ev.block.typeId)) return;
  ev.cancel = true;
  const p = ev.player;
  system.run(() => {
    if (p.isValid) useFocus(p);
  });
});

world.afterEvents.playerButtonInput.subscribe(
  (ev) => {
    const s = peek(ev.player.id);
    if (s?.channel?.ability === "root_metamorphosis") endChannel(ev.player, s, "cancel");
  },
  { buttons: [InputButton.Jump], state: ButtonState.Pressed },
);

// ------------------------------------------------------------------ players

function onJoin(p: Player, first: boolean): void {
  const s = load(p);
  restore(p, s);
  if (!s.data.joined) {
    s.data.joined = true;
    s.dirty = true;
    giveCodex(p);
    p.sendMessage("§dPlayable Races: §7open the §fLineage Codex");
    if (settings().autoOpen && !s.data.race) system.runTimeout(() => {
      if (p.isValid) void openCodex(p, 6);
    }, 60);
  }
  save(p, s, true);
  if (first) applyFog(p);
}

function giveCodex(p: Player): void {
  const codex = new ItemStack(ITEM_CODEX, 1);
  const inv = p.getComponent("minecraft:inventory")?.container;
  try {
    const left = inv?.addItem(codex);
    if (left || !inv) p.dimension.spawnItem(codex, p.location);
  } catch {
    /* ignore */
  }
}

world.afterEvents.playerSpawn.subscribe((ev) => {
  const p = ev.player;
  system.runTimeout(() => {
    if (!p.isValid) return;
    if (ev.initialSpawn) onJoin(p, true);
    else {
      const s = get(p);
      restore(p, s);
    }
  }, 10);
});

world.beforeEvents.playerLeave.subscribe((ev) => {
  const id = ev.player.id;
  system.run(() => {
    const s = peek(id);
    if (s) {
      s.channel = undefined; // locks are restored on next join from persisted data
      cancel(id);
      removeMiragesOf(id);
      drop(id);
    }
  });
});

world.afterEvents.playerDimensionChange.subscribe((ev) => {
  const p = ev.player;
  const s = get(p);
  if (s.channel) endChannel(p, s, "dimension");
  cancel(p.id);
  system.runTimeout(() => {
    if (!p.isValid) return;
    applyFog(p);
    refreshForm(p, s);
  }, 5);
});

// ------------------------------------------------------------------ combat hooks

world.beforeEvents.entityHurt.subscribe((ev: EntityHurtBeforeEvent) => {
  const victim = ev.hurtEntity;
  if (victim.typeId === "minecraft:player") {
    const s = peek(victim.id);
    const race = s && raceOf(s);
    if (s && race?.onHurt) race.onHurt(victim as Player, s, ev);
    if (!ev.cancel && inWard(victim as Player)) ev.damage *= 0.85; // Glyph Dominion "Warded"
  }
  const src = ev.damageSource.damagingEntity;
  if (src && src.typeId === "minecraft:player" && !ev.cancel) {
    const s = peek(src.id);
    const race = s && raceOf(s);
    if (s && race?.onDealDamage) race.onDealDamage(src as Player, s, ev);
  }
});

world.afterEvents.entityHurt.subscribe((ev) => {
  const e = ev.hurtEntity;
  if (e.typeId === ENTITY_MIRAGE) {
    pop(e, true, playerById, ev.damageSource.damagingEntity);
    return;
  }
  if (e.typeId === "minecraft:player") {
    const s = peek(e.id);
    const race = s && raceOf(s);
    if (s && race?.afterHurt) {
      try {
        race.afterHurt(e as Player, s, ev.damageSource.cause as string, ev.damage, ev.damageSource.damagingEntity?.id);
      } catch (err) {
        warn("afterHurt failed", err);
      }
    }
  }
});

world.afterEvents.entityDie.subscribe((ev) => {
  const e = ev.deadEntity;
  if (e.typeId === "minecraft:player") {
    const s = peek(e.id);
    if (s) {
      if (s.channel) endChannel(e as Player, s, "death");
      cancel(e.id);
      s.tempVariant = undefined;
      s.flags.clear();
      removeMiragesOf(e.id);
    }
    return;
  }
  if (isMirage(e)) return;
  const by = markedBy(e.id);
  if (by) {
    consume(e);
    const p = playerById(by);
    const s = p && peek(p.id);
    if (p && s && raceOf(s)?.key === "jackalope") moonhunt(p, s);
  }
});

world.afterEvents.itemCompleteUse.subscribe((ev) => {
  if (ev.itemStack.typeId !== "minecraft:potion") return;
  const s = peek(ev.source.id);
  if (s && raceOf(s)?.key === "salamander") salamanderDrink(ev.source, s);
});

world.afterEvents.weatherChange.subscribe((ev) => {
  if (ev.dimension === "minecraft:overworld" || ev.dimension === "overworld") setWeather(ev.newWeather);
});

world.afterEvents.entitySpawn.subscribe((ev) => {
  const e: Entity = ev.entity;
  if (!e.isValid || e.typeId !== "minecraft:lightning_bolt") return;
  for (const p of players()) {
    const s = peek(p.id);
    if (!s || raceOf(s)?.key !== "golem" || p.dimension.id !== e.dimension.id) continue;
    const d = Math.hypot(p.location.x - e.location.x, p.location.y - e.location.y, p.location.z - e.location.z);
    golemLightning(p, s, d);
  }
});

onBloodMoonChange(() => {
  for (const p of players()) {
    const s = peek(p.id);
    if (s && raceOf(s)?.key === "jackalope") refreshForm(p, s);
  }
});

// ------------------------------------------------------------------ loops

function reticle(p: Player, s: Session): void {
  const race = raceOf(s);
  if (!race) return;
  const a = selected(s, race);
  if (!a.needsTarget || !a.range) return;
  const t = aimTarget(p, a.range, a.id === "carnivorous_embrace" ? 70 : a.id === "crimson_waltz" ? 60 : 14);
  if (t) privateParticle(p, "plrace:target_reticle", chest(t), rgb(RGB.green));
}

function startLoops(): void {
  startScheduler();
  system.runInterval(() => {
    for (const s of all()) {
      if (!s.channel) continue;
      const p = playerById(s.id);
      if (p) tickChannel(p, s);
    }
  }, 1);
  let phase = 0;
  system.runInterval(() => {
    phase++;
    for (const p of players()) {
      const s = peek(p.id);
      const race = s && raceOf(s);
      if (!s || !race) continue;
      try {
        if (s.tempVariant && s.tempVariant.until <= system.currentTick) refreshForm(p, s);
        else if (s.flags.size) refreshForm(p, s);
        race.tick5?.(p, s);
        updateHud(p, s);
        if (phase % 2 === 0 && holdingFocus(p, race)) reticle(p, s);
      } catch (e) {
        warn("tick5 failed", e);
      }
    }
    if (phase % 2 === 0) {
      tickMarks();
      tickMirages();
    }
  }, 4);
  system.runInterval(() => {
    for (const p of players()) {
      const s = peek(p.id);
      const race = s && raceOf(s);
      if (!s || !race) continue;
      try {
        race.tick20(p, s);
        integrity(p, s);
      } catch (e) {
        warn("tick20 failed", e);
      }
    }
    cleanupEnsnared();
  }, 20);
  system.runInterval(() => {
    try {
      bloodMoonTick();
    } catch (e) {
      warn("blood moon tick failed", e);
    }
  }, 40);
  system.runInterval(() => {
    for (const p of players()) {
      const s = peek(p.id);
      if (s) save(p, s);
    }
  }, SAVE_INTERVAL);
}

world.afterEvents.worldLoad.subscribe(() => {
  startLoops();
  // scripts reloaded while players are online (/reload): restore them
  for (const p of players()) onJoin(p, false);
});
