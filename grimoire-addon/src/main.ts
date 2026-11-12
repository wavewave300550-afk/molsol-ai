import {
  CommandPermissionLevel,
  CustomCommandOrigin,
  CustomCommandParamType,
  CustomCommandStatus,
  Entity,
  EntityInitializationCause,
  ItemStack,
  Player,
  StartupEvent,
  system,
  world,
} from "@minecraft/server";
import { setRule, rules } from "./config";
import { registerBlockComponents } from "./core/blocks";
import {
  cancelPreparation,
  heldSchool,
  onCompleteUse,
  onReleaseUse,
  onSneakEdge,
  onStartUse,
  onStopUse,
  tickPreparation,
} from "./core/casting";
import { FX_FAMILY, SUMMON_FAMILY, clearVulnerableOf, flushDamage, noteAggressor, pruneAggressors, vulnerabilityBonus } from "./core/combat";
import { initDefense, removeWardsOf } from "./core/defense";
import { isStaleConstruct, removeAllFxOf } from "./core/fx";
import { renderHud } from "./core/hud";
import { log } from "./core/log";
import { clearCooldowns, forget, save, stateOf } from "./core/state";
import { cancelOwned, tickRoutines } from "./core/tasks";
import { allSpells, spellsOf } from "./spells/registry";
import { GRIMOIRE_ITEMS, SCHOOLS, School, schoolOfItem } from "./spells/types";
import { initHooks } from "./spells/hooks";
import { initDiagnostics } from "./core/diagnostics";
import { endBindsOf, tickBinds } from "./core/status";

// ------------------------------------------------------------------------------- startup

system.beforeEvents.startup.subscribe((ev: StartupEvent) => {
  registerBlockComponents(ev);
  const reg = ev.customCommandRegistry;
  reg.registerEnum("grimoire:book", ["pressure", "ice", "blood", "plasma", "darkness", "prism_light", "all"]);
  reg.registerCommand(
    {
      name: "grimoire:getbook",
      description: "Give yourself a Grimoire (pressure, ice, blood, plasma, darkness, prism_light or all).",
      permissionLevel: CommandPermissionLevel.GameDirectors,
      optionalParameters: [{ name: "grimoire:book", type: CustomCommandParamType.Enum }],
    },
    (origin: CustomCommandOrigin, book?: string) => {
      const p = origin.sourceEntity;
      if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Run this as a player." };
      const which: School[] = !book || book === "all" ? SCHOOLS : [book as School];
      system.run(() => {
        const inv = p.getComponent("minecraft:inventory")?.container;
        for (const s of which) inv?.addItem(new ItemStack(GRIMOIRE_ITEMS[s], 1));
      });
      return { status: CustomCommandStatus.Success, message: `Given: ${which.join(", ")}` };
    },
  );
  reg.registerCommand(
    {
      name: "grimoire:config",
      description: "Set a Grimoire rule: pvp, friendlyFire, harmPassiveMobs, temporaryBlocks, damagePvE, damagePvP, cameraEffects.",
      permissionLevel: CommandPermissionLevel.GameDirectors,
      optionalParameters: [
        { name: "rule", type: CustomCommandParamType.String },
        { name: "value", type: CustomCommandParamType.String },
      ],
    },
    (_o: CustomCommandOrigin, rule?: string, value?: string) => {
      if (!rule || value === undefined) return { status: CustomCommandStatus.Success, message: JSON.stringify(rules()) };
      let msg = "";
      system.run(() => {
        msg = setRule(rule, value);
        world.sendMessage(`§6[Grimoire]§r ${msg}`);
      });
      return { status: CustomCommandStatus.Success, message: `Updating ${rule}...` };
    },
  );
  reg.registerCommand(
    {
      name: "grimoire:resetcooldowns",
      description: "Clear your own spell cooldowns (testing aid for operators).",
      permissionLevel: CommandPermissionLevel.GameDirectors,
      cheatsRequired: true,
    },
    (origin: CustomCommandOrigin) => {
      const p = origin.sourceEntity;
      if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Run this as a player." };
      system.run(() => {
        const st = stateOf(p);
        clearCooldowns(st);
        save(p, st);
      });
      return { status: CustomCommandStatus.Success, message: "Cooldowns cleared." };
    },
  );
  reg.registerCommand(
    {
      name: "grimoire:guide",
      description: "List the 15 spells of the Grimoire you are holding (or all books).",
      permissionLevel: CommandPermissionLevel.Any,
    },
    (origin: CustomCommandOrigin) => {
      const p = origin.sourceEntity;
      if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure };
      system.run(() => showGuide(p));
      return { status: CustomCommandStatus.Success };
    },
  );
});

function showGuide(p: Player): void {
  const held = heldSchool(p);
  const schools = held ? [held.school] : SCHOOLS;
  for (const s of schools) {
    const lines = spellsOf(s).map((sp) => `§7${sp.code} §f${sp.name} §8(${sp.cooldown}s) §7- ${sp.blurb}`);
    p.sendMessage([`§l${s.toUpperCase()} GRIMOIRE§r`, ...lines].join("\n"));
  }
  p.sendMessage("§eCrouch§7 = next spell · §eHold Use§7 (standing) = prepare · §eRelease§7 = cast. No mana: only cooldowns.");
}

// ------------------------------------------------------------------------------- item use

world.afterEvents.itemStartUse.subscribe((e) => {
  if (schoolOfItem(e.itemStack?.typeId)) onStartUse(e.source, e.itemStack);
});
world.afterEvents.itemReleaseUse.subscribe((e) => {
  if (schoolOfItem(e.itemStack?.typeId) || stateOf(e.source).prep) onReleaseUse(e.source);
});
world.afterEvents.itemStopUse.subscribe((e) => {
  onStopUse(e.source);
});
world.afterEvents.itemCompleteUse.subscribe((e) => {
  if (schoolOfItem(e.itemStack?.typeId)) onCompleteUse(e.source);
});

// ------------------------------------------------------------------------------- crouch selection

world.afterEvents.entityStartSneaking.subscribe(
  (e) => {
    if (e.entity instanceof Player) onSneakEdge(e.entity, true);
  },
  { entityFilter: { type: "minecraft:player" } },
);
world.afterEvents.entityStopSneaking.subscribe(
  (e) => {
    if (e.entity instanceof Player) onSneakEdge(e.entity, false);
  },
  { entityFilter: { type: "minecraft:player" } },
);

// ------------------------------------------------------------------------------- lifecycle

world.afterEvents.playerSpawn.subscribe((e) => {
  const st = stateOf(e.player);
  st.sneaking = e.player.isSneaking;
  if (e.initialSpawn) {
    system.runTimeout(() => {
      if (!e.player.isValid) return;
      e.player.sendMessage("§6[Grimoire]§r §7Hold a Grimoire: §eCrouch§7 to select, §eHold Use§7 standing to prepare, §eRelease§7 to cast. §8/grimoire:guide");
    }, 60);
  }
});

function endPlayer(id: string, reason: string): void {
  cancelOwned(id, reason);
  clearVulnerableOf(id);
  endBindsOf(id);
  removeWardsOf(id);
  removeAllFxOf(id);
}

world.beforeEvents.playerLeave.subscribe((e) => {
  const p = e.player;
  const id = p.id;
  try {
    const st = stateOf(p);
    st.prep = undefined;
    save(p, st);
  } catch {
    /* restricted: saved on next change anyway */
  }
  system.run(() => {
    endPlayer(id, "owner left");
    forget(id);
    lastDimension.delete(id);
  });
});

/** Last known dimension per player: the main loop detects changes the event may miss (e.g. scripted teleports). */
const lastDimension = new Map<string, string>();

function onDimensionChanged(p: Player): void {
  lastDimension.set(p.id, p.dimension.id);
  cancelPreparation(p, "Preparation cancelled (dimension changed)");
  // constructs, wards, binds and summons stay behind in the old dimension, whose chunks may unload:
  // end every active cast of this player now, exactly like a disconnect (I11 starts its cooldown).
  endPlayer(p.id, "dimension changed");
}

world.afterEvents.playerDimensionChange.subscribe((e) => {
  if (lastDimension.get(e.player.id) !== e.player.dimension.id) onDimensionChanged(e.player);
});

world.afterEvents.entityDie.subscribe((e) => {
  const d = e.deadEntity;
  if (d instanceof Player) {
    cancelPreparation(d);
  }
});

world.afterEvents.entityHurt.subscribe((e) => {
  const victim = e.hurtEntity;
  const attacker = e.damageSource.damagingEntity;
  if (attacker && victim.isValid && (victim.typeId === "minecraft:player" || victim.hasTag("grimoire_summon"))) noteAggressor(victim, attacker);
  if (victim.isValid) vulnerabilityBonus(victim, e.damage, attacker);
});

/** Remove constructs/summons left over from a previous session (crash, /reload, world reopen). */
function sweepStale(e: Entity): void {
  try {
    const fam = e.getComponent("minecraft:type_family");
    if (!fam) return;
    if ((fam.hasTypeFamily(FX_FAMILY) || fam.hasTypeFamily(SUMMON_FAMILY)) && isStaleConstruct(e)) e.remove();
  } catch {
    /* ignore */
  }
}

world.afterEvents.entityLoad.subscribe((e) => sweepStale(e.entity));
world.afterEvents.entitySpawn.subscribe((e) => {
  // constructs restored from disk fire entitySpawn with cause "Loaded"
  if (e.cause === EntityInitializationCause.Loaded) sweepStale(e.entity);
});
world.afterEvents.worldLoad.subscribe(() => {
  for (const id of ["overworld", "nether", "the_end"]) {
    try {
      for (const e of world.getDimension(id).getEntities({ families: [FX_FAMILY] })) sweepStale(e);
      for (const e of world.getDimension(id).getEntities({ families: [SUMMON_FAMILY] })) sweepStale(e);
    } catch {
      /* dimension not loaded */
    }
  }
  log.warn(`loaded: ${allSpells().length} spells, PvP ${rules().pvp ? "on" : "off"}`);
});

initDefense();
initHooks();
initDiagnostics();

// ------------------------------------------------------------------------------- main loop

system.runInterval(() => {
  const now = system.currentTick;
  tickRoutines(now);
  tickBinds(now);
  flushDamage(now);
  for (const p of world.getAllPlayers()) {
    if (!p.isValid) continue;
    const dimId = p.dimension.id;
    const known = lastDimension.get(p.id);
    if (known === undefined) lastDimension.set(p.id, dimId);
    else if (known !== dimId) onDimensionChanged(p); // backup if the event was missed
    const st = stateOf(p);
    const sneaking = p.isSneaking;
    if (sneaking !== st.sneaking) onSneakEdge(p, sneaking); // backup if an event was missed
    if (st.prep) tickPreparation(p, st);
    if (now % 2 === 0) {
      const held = heldSchool(p);
      if (held) renderHud(p, st, held.school);
    }
    if (st.dirty && now % 100 === 0) save(p, st);
  }
  if (now % 100 === 0) pruneAggressors();
}, 1);
