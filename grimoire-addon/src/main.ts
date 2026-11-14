import { CONFIG } from "./config/global";
import { VERSION } from "./config/version";
import { CommandPermissionLevel, CustomCommandStatus, ItemStack, Player, system, world } from "@minecraft/server";
import { RUNTIME } from "./config/global";
import { installInput, tickInput } from "./core/input";
import { GRIMOIRES, getSpell, META_BY_ID } from "./core/registry";
import { clearCooldowns, startCooldown } from "./core/state";
import { installBooks } from "./core/books";
import { installWards } from "./lib/combat";
import { Scenes } from "./lib/scene";
import { groundBelow, takeAim } from "./lib/targeting";
import { anySetOwns, flushLedger, restoreLedger, retryOrphans } from "./lib/tempblocks";
import { registerAllSpells } from "./spells/index";

registerAllSpells();

function giveBooks(p: Player): void {
  const inv = p.getComponent("minecraft:inventory")?.container;
  if (!inv) return;
  for (const g of Object.values(GRIMOIRES)) inv.addItem(new ItemStack(g.item, 1));
}

/** Force-cast for testing (bypasses input and cooldown checks, still starts the cooldown). */
function forceCast(p: Player, id: string): string {
  const spell = getSpell(id);
  if (!spell) return `unknown spell '${id}' (use dw01..dw06, dn01..dn06, ed01..ed06)`;
  const scene = Scenes.start(spell.id, p);
  let ok: boolean | void;
  try { ok = spell.cast({ caster: p, scene, aim: takeAim(p), heldTicks: 20 }); } catch (e) { scene.end(); return `error: ${e}`; }
  if (ok === false) { scene.end(); return `${id}: no valid target`; }
  startCooldown(p, spell.id, spell.cooldown);
  return `cast ${id} (${META_BY_ID[id].name})`;
}

system.beforeEvents.startup.subscribe((ev) => {
  const reg = ev.customCommandRegistry;
  reg.registerCommand(
    { name: "grimoire:give", description: "Give yourself the three Grimoires", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: true },
    (origin) => {
      const p = origin.sourceEntity;
      if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only" };
      system.run(() => giveBooks(p));
      return { status: CustomCommandStatus.Success, message: "Three Grimoires added to your inventory" };
    },
  );
  reg.registerCommand(
    { name: "grimoire:reset", description: "Clear all of your Grimoire spell cooldowns", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: true },
    (origin) => {
      const p = origin.sourceEntity;
      if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only" };
      system.run(() => clearCooldowns(p));
      return { status: CustomCommandStatus.Success, message: "Grimoire cooldowns cleared" };
    },
  );
  reg.registerCommand(
    { name: "grimoire:cleanup", description: "End every active Grimoire spell and remove its constructs", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
    () => {
      system.run(() => { Scenes.endAll(); Scenes.sweepOrphans(); });
      return { status: CustomCommandStatus.Success, message: "Grimoire spells ended" };
    },
  );
});

// /scriptevent grimoire:give | grimoire:reset | grimoire:cast <id> | grimoire:cleanup | grimoire:config heartbeat on|off | pvp on|off
system.afterEvents.scriptEventReceive.subscribe((ev) => {
  const p = ev.sourceEntity instanceof Player ? ev.sourceEntity : undefined;
  const arg = ev.message.trim().toLowerCase();
  switch (ev.id) {
    case "grimoire:give": if (p) giveBooks(p); break;
    case "grimoire:reset": if (p) { clearCooldowns(p); p.sendMessage("Grimoire cooldowns cleared"); } break;
    case "grimoire:cast": if (p) p.sendMessage(`[grimoire] ${forceCast(p, arg)}`); break;
    case "grimoire:cleanup": Scenes.endAll(); Scenes.sweepOrphans(); break;
    case "grimoire:show": {
      // /scriptevent grimoire:show <actor> [state] [kind] [skin] [size]  -- display one model for 20 s
      if (!p) break;
      const [id, st, kd, sk, sz] = ev.message.trim().split(/\s+/);
      if (!id) { p.sendMessage("[grimoire] usage: /scriptevent grimoire:show <actor> [state] [kind] [skin] [size]"); break; }
      const sc = Scenes.start("show", p);
      const a = takeAim(p);
      const at = groundBelow(p.dimension, { x: p.location.x + a.forward.x * 8, y: p.location.y + 1, z: p.location.z + a.forward.z * 8 });
      const actor = sc.spawn(id, at, { yaw: a.yaw + 180, state: st !== undefined ? Number(st) : 1,
        kind: kd !== undefined ? Number(kd) : undefined, skin: sk !== undefined ? Number(sk) : undefined,
        size: sz !== undefined ? Number(sz) : undefined });
      sc.endAt(400);
      p.sendMessage(actor.valid ? `[grimoire] showing ${id} for 20 s` : `[grimoire] cannot spawn '${id}'`);
      if (!actor.valid) sc.end();
      break;
    }
    case "grimoire:config": {
      const [key, val] = arg.split(/\s+/);
      const on = val === "on" || val === "true" || val === "1";
      if (key === "heartbeat") RUNTIME.input.heartbeatFallback = on;
      else if (key === "pvp") RUNTIME.targeting.pvp = on;
      p?.sendMessage(`[grimoire] ${key} = ${on}`);
      break;
    }
  }
}, { namespaces: ["grimoire"] });

// Say which version is running when a player joins: an update that did not take effect is the first
// thing to rule out when something still looks wrong.
world.afterEvents.playerSpawn.subscribe((ev) => {
  if (!ev.initialSpawn) return;
  const p = ev.player;
  system.runTimeout(() => {
    try {
      if (!p.isValid) return;
      p.sendMessage(`§6Grimoire: Rebirth of the Arcane §f${VERSION}`);
      // starter kit: the three Grimoires once per player, so nobody has to type a command to begin
      if (CONFIG.starterKit && p.getDynamicProperty("grim:kit") !== 1) {
        p.setDynamicProperty("grim:kit", 1);
        giveBooks(p);
        p.sendMessage("§7The three Grimoires are in your inventory.  Crouch: next spell.  Hold Use, release: cast.");
      }
    } catch { /* left */ }
  }, 60);
});

world.afterEvents.worldLoad.subscribe(() => {
  installWards();
  installInput();
  installBooks();
  restoreLedger();
  Scenes.sweepOrphans();
  let n = 0;
  system.runInterval(() => {
    tickInput();
    Scenes.tickAll();
    flushLedger();
    if (++n % 100 === 0) retryOrphans(anySetOwns);
  }, 1);
});
