/** Custom slash commands (registered at startup). Ordinary play never needs them. */
import { CommandPermissionLevel, CustomCommandOrigin, CustomCommandParamType, CustomCommandRegistry, CustomCommandResult, CustomCommandStatus, Entity, Player, StartupEvent, system } from "@minecraft/server";
import { resetCooldowns } from "./core/abilities.js";
import { get, save } from "./core/session.js";
import { assignRace, removeRace } from "./lineage.js";
import { RACES, raceByKey } from "./races/registry.js";
import { bloodMoonStatus, end, forceNext, start } from "./systems/bloodmoon.js";
import { openCodex } from "./ui/menu.js";

const ok = (message?: string): CustomCommandResult => ({ status: CustomCommandStatus.Success, message });
const bad = (message: string): CustomCommandResult => ({ status: CustomCommandStatus.Failure, message });

function sourcePlayer(o: CustomCommandOrigin): Player | undefined {
  const e: Entity | undefined = o.initiator ?? o.sourceEntity;
  return e instanceof Player ? e : undefined;
}

export function registerCommands(ev: StartupEvent): void {
  const reg: CustomCommandRegistry = ev.customCommandRegistry;
  reg.registerEnum("plrace:race", [...RACES.map((r) => r.key), ...RACES.map((r) => r.code), "none"]);
  reg.registerEnum("plrace:moon_action", ["start", "stop", "next", "status"]);

  reg.registerCommand({ name: "plrace:codex", description: "Open the Lineage Codex (race selection and abilities)", permissionLevel: CommandPermissionLevel.Any }, (origin) => {
    const p = sourcePlayer(origin);
    if (!p) return bad("Only players can open the codex.");
    system.run(() => void openCodex(p));
    return ok();
  });

  reg.registerCommand(
    {
      name: "plrace:setrace",
      description: "Set a player's lineage (001 salamander, 002 golem, 003 jackalope, none)",
      permissionLevel: CommandPermissionLevel.GameDirectors,
      mandatoryParameters: [{ name: "plrace:race", type: CustomCommandParamType.Enum }],
      optionalParameters: [{ name: "players", type: CustomCommandParamType.PlayerSelector }],
    },
    (origin, raceArg: unknown, playersArg?: unknown) => {
      const key = String(raceArg);
      const targets = (Array.isArray(playersArg) ? (playersArg as Player[]) : [sourcePlayer(origin)]).filter((x): x is Player => !!x);
      if (targets.length === 0) return bad("No target players.");
      const race = key === "none" ? undefined : raceByKey(key);
      if (key !== "none" && !race) return bad(`Unknown race ${key}`);
      system.run(() => {
        for (const p of targets) {
          if (race) assignRace(p, race.code);
          else removeRace(p);
        }
      });
      return ok(`Lineage ${race ? race.name : "removed"} for ${targets.length} player(s).`);
    },
  );

  reg.registerCommand(
    {
      name: "plrace:resetcooldowns",
      description: "Reset ability cooldowns (testing)",
      permissionLevel: CommandPermissionLevel.GameDirectors,
      optionalParameters: [{ name: "players", type: CustomCommandParamType.PlayerSelector }],
    },
    (origin, playersArg?: unknown) => {
      const targets = (Array.isArray(playersArg) ? (playersArg as Player[]) : [sourcePlayer(origin)]).filter((x): x is Player => !!x);
      system.run(() => {
        for (const p of targets) {
          const s = get(p);
          resetCooldowns(s);
          save(p, s, true);
        }
      });
      return ok(`Cooldowns reset for ${targets.length} player(s).`);
    },
  );

  reg.registerCommand(
    {
      name: "plrace:bloodmoon",
      description: "Blood Moon control: start | stop | next (force the next full moon) | status",
      permissionLevel: CommandPermissionLevel.GameDirectors,
      mandatoryParameters: [{ name: "plrace:moon_action", type: CustomCommandParamType.Enum }],
    },
    (_origin, action: unknown) => {
      const a = String(action);
      if (a === "status") return ok(bloodMoonStatus());
      system.run(() => {
        if (a === "start") start(true);
        else if (a === "stop") end("command");
        else if (a === "next") forceNext();
      });
      return ok(a === "next" ? "The next full moon will be a Blood Moon." : `Blood Moon ${a}.`);
    },
  );
}
