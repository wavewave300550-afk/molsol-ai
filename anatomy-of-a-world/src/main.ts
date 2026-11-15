/**
 * THE ANATOMY OF A WORLD — behaviour pack entry point.
 *
 * Registers item components and slash commands, wires engine events to the
 * encounter manager and runs the encounter loop every tick.
 */
import {
  CommandPermissionLevel,
  CustomCommandOrigin,
  CustomCommandParamType,
  CustomCommandStatus,
  ItemStack,
  Player,
  system,
  world,
} from "@minecraft/server";
import "./bosses/migrating_mountain/index.js";
import { leaveArena } from "./core/arena.js";
import { openAtlas, startFor } from "./core/atlas.js";
import { manager } from "./core/manager.js";
import { allBosses, bossForItem, getBoss } from "./core/registry.js";

const ATLAS_ITEM = "anatomy:anatomical_atlas";
const GOT_ATLAS = "anatomy:got_atlas";
const recentUse = new Map<string, number>();

function useItem(p: Player, typeId: string): void {
  // de-duplicate the custom-component and itemUse paths
  const last = recentUse.get(p.id) ?? -10;
  if (system.currentTick - last < 4) return;
  recentUse.set(p.id, system.currentTick);
  if (typeId === ATLAS_ITEM) {
    system.run(() => openAtlas(p));
    return;
  }
  const boss = bossForItem(typeId);
  if (!boss) return;
  system.run(() => {
    if (manager.active && !manager.active.isFinished()) {
      p.sendMessage("§7An encounter is already running — open the Anatomical Atlas to join it.");
      return;
    }
    startFor(p, boss, p.getGameMode() !== "Creative");
  });
}

system.beforeEvents.startup.subscribe((ev) => {
  ev.itemComponentRegistry.registerCustomComponent("anatomy:atlas", {
    onUse: (e) => useItem(e.source, ATLAS_ITEM),
  });
  ev.itemComponentRegistry.registerCustomComponent("anatomy:summoner", {
    onUse: (e) => {
      if (e.itemStack) useItem(e.source, e.itemStack.typeId);
    },
  });

  const reg = ev.customCommandRegistry;
  reg.registerEnum("anatomy:action", ["start", "stop", "skip", "kill", "status", "join", "leave"]);
  reg.registerEnum("anatomy:specimen", allBosses().map((b) => b.id));
  reg.registerEnum("anatomy:ability", [...new Set(allBosses().flatMap((b) => [...b.abilities]))]);

  reg.registerCommand(
    { name: "anatomy:atlas", description: "Open (or receive) the Anatomical Atlas", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: false },
    (origin: CustomCommandOrigin) => {
      const p = origin.sourceEntity;
      if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
      system.run(() => {
        giveAtlas(p, true);
        openAtlas(p);
      });
      return { status: CustomCommandStatus.Success };
    },
  );

  reg.registerCommand(
    {
      name: "anatomy:boss",
      description: "Control boss encounters (testing)",
      permissionLevel: CommandPermissionLevel.GameDirectors,
      cheatsRequired: true,
      mandatoryParameters: [{ name: "anatomy:action", type: CustomCommandParamType.Enum }],
      optionalParameters: [{ name: "anatomy:specimen", type: CustomCommandParamType.Enum }],
    },
    (origin: CustomCommandOrigin, action: string, specimen?: string) => {
      const p = origin.sourceEntity instanceof Player ? origin.sourceEntity : undefined;
      let message = "";
      system.run(() => {
        const r = bossAction(p, action, specimen);
        if (p && r) p.sendMessage(r);
        else if (r) console.warn(`[anatomy] ${r}`);
      });
      message = `anatomy: ${action} requested`;
      return { status: CustomCommandStatus.Success, message };
    },
  );

  reg.registerCommand(
    {
      name: "anatomy:ability",
      description: "Force the active boss to use an ability (testing)",
      permissionLevel: CommandPermissionLevel.GameDirectors,
      cheatsRequired: true,
      mandatoryParameters: [{ name: "anatomy:ability", type: CustomCommandParamType.Enum }],
    },
    (origin: CustomCommandOrigin, ability: string) => {
      system.run(() => {
        const ok = manager.active?.forceAbility(ability) ?? false;
        const p = origin.sourceEntity;
        if (p instanceof Player) p.sendMessage(ok ? `§aForced ${ability}` : "§7No active fight can use that right now.");
      });
      return { status: CustomCommandStatus.Success };
    },
  );
});

function bossAction(p: Player | undefined, action: string, specimen?: string): string {
  const def = getBoss(specimen ?? "migrating_mountain") ?? allBosses()[0];
  const a = manager.active;
  switch (action) {
    case "start":
      if (!p) return "start needs a player";
      if (a && !a.isFinished()) return "an encounter is already running";
      return manager.start(def, p) ?? `starting ${def.id}`;
    case "stop":
      if (!a) return "no active encounter";
      manager.stop("abort");
      return "stopping";
    case "skip":
      return a?.forcePhase(2) ? "skipping to Phase 2" : "cannot skip now";
    case "kill":
      return a?.killBoss() ? "boss defeated" : "cannot kill now";
    case "status":
      return a ? a.status() : "no active encounter";
    case "join":
      if (p && a) manager.rejoin(p);
      return a ? "joining" : "no active encounter";
    case "leave":
      if (p) {
        manager.cancelReturn(p);
        leaveArena(p);
      }
      return "leaving";
  }
  return "unknown action";
}

function giveAtlas(p: Player, force: boolean): void {
  if (!force && p.getDynamicProperty(GOT_ATLAS)) return;
  const inv = p.getComponent("minecraft:inventory")?.container;
  if (!inv) return;
  for (let i = 0; i < inv.size; i++) if (inv.getItem(i)?.typeId === ATLAS_ITEM) return;
  inv.addItem(new ItemStack(ATLAS_ITEM, 1));
  p.setDynamicProperty(GOT_ATLAS, true);
  if (!force) p.sendMessage("§dYou received the §lAnatomical Atlas§r§d. Use it to read about the colossal specimens of this world.");
}

world.afterEvents.worldLoad.subscribe(() => {
  manager.restore();
  system.runInterval(() => manager.tick(), 1);
});

world.afterEvents.playerSpawn.subscribe((ev) => {
  const p = ev.player;
  if (ev.initialSpawn) {
    system.runTimeout(() => {
      if (!p.isValid) return;
      giveAtlas(p, false);
      if (p.dimension.id.startsWith("anatomy:") && (!manager.active || manager.active.def.dimensionId !== p.dimension.id)) leaveArena(p);
    }, 40);
  } else manager.onPlayerRespawn(p);
});

world.afterEvents.itemUse.subscribe((ev) => {
  const id = ev.itemStack.typeId;
  if (id === ATLAS_ITEM || bossForItem(id)) useItem(ev.source, id);
});

world.beforeEvents.entityHurt.subscribe((ev) => manager.onHurtBefore(ev));
world.afterEvents.entityHurt.subscribe((ev) => manager.onHurt(ev));
world.afterEvents.projectileHitBlock.subscribe((ev) => manager.onProjectileHitBlock(ev));
world.afterEvents.projectileHitEntity.subscribe((ev) => manager.onProjectileHitEntity(ev));
world.beforeEvents.playerBreakBlock.subscribe((ev) => manager.onBreakBefore(ev));
world.afterEvents.playerPlaceBlock.subscribe((ev) => manager.onPlace(ev));
world.beforeEvents.explosion.subscribe((ev) => manager.onExplosionBefore(ev));
world.afterEvents.entitySpawn.subscribe((ev) => manager.onEntitySpawn(ev));

system.afterEvents.scriptEventReceive.subscribe((ev) => {
  if (!ev.id.startsWith("anatomy:")) return;
  const p = ev.sourceEntity instanceof Player ? ev.sourceEntity : undefined;
  const cmd = ev.id.slice("anatomy:".length);
  const arg = ev.message.trim();
  let out: string;
  if (cmd === "ability") out = manager.active?.forceAbility(arg) ? `forced ${arg}` : "cannot force that now";
  else out = bossAction(p, cmd, arg || undefined);
  if (p) p.sendMessage(`§7[anatomy] ${out}`);
  else console.warn(`[anatomy] ${out}`);
});
