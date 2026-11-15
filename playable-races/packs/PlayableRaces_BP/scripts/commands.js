import { CommandPermissionLevel, CustomCommandParamType, CustomCommandStatus, Player, system } from "@minecraft/server";
import { resetCooldowns } from "./core/abilities.js";
import { get, save } from "./core/session.js";
import { assignRace, removeRace } from "./lineage.js";
import { releaseCode, uniqueStatus } from "./systems/unique.js";
import { RACES, raceByKey } from "./races/registry.js";
import { bloodMoonStatus, end, forceNext, start } from "./systems/bloodmoon.js";
import { openCodex } from "./ui/menu.js";
const ok = (message) => ({ status: CustomCommandStatus.Success, message });
const bad = (message) => ({ status: CustomCommandStatus.Failure, message });
function sourcePlayer(o) {
    const e = o.initiator ?? o.sourceEntity;
    return e instanceof Player ? e : undefined;
}
export function registerCommands(ev) {
    const reg = ev.customCommandRegistry;
    reg.registerEnum("plrace:race", [...RACES.map((r) => r.key), ...RACES.map((r) => r.code), "none"]);
    reg.registerEnum("plrace:moon_action", ["start", "stop", "next", "status"]);
    reg.registerEnum("plrace:unique_action", ["status", "release"]);
    reg.registerCommand({ name: "plrace:codex", description: "Open the Lineage Codex (race selection and abilities)", permissionLevel: CommandPermissionLevel.Any }, (origin) => {
        const p = sourcePlayer(origin);
        if (!p)
            return bad("Only players can open the codex.");
        system.run(() => void openCodex(p));
        return ok();
    });
    reg.registerCommand({
        name: "plrace:setrace",
        description: "Set a player's lineage (001-006 or salamander, golem, jackalope, xenentoma, spaghetti, nurariten, none)",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        mandatoryParameters: [{ name: "plrace:race", type: CustomCommandParamType.Enum }],
        optionalParameters: [{ name: "players", type: CustomCommandParamType.PlayerSelector }],
    }, (origin, raceArg, playersArg) => {
        const key = String(raceArg);
        const targets = (Array.isArray(playersArg) ? playersArg : [sourcePlayer(origin)]).filter((x) => !!x);
        if (targets.length === 0)
            return bad("No target players.");
        const race = key === "none" ? undefined : raceByKey(key);
        if (key !== "none" && !race)
            return bad(`Unknown race ${key}`);
        system.run(() => {
            for (const p of targets) {
                if (race) {
                    if (!assignRace(p, race.code))
                        p.sendMessage(`§cCould not assign ${race.name} (Unique lineage already held? See /plrace:unique status).`);
                }
                else
                    removeRace(p);
            }
        });
        return ok(`Lineage ${race ? race.name : "removed"} requested for ${targets.length} player(s).`);
    });
    reg.registerCommand({
        name: "plrace:resetcooldowns",
        description: "Reset ability cooldowns (testing)",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        optionalParameters: [{ name: "players", type: CustomCommandParamType.PlayerSelector }],
    }, (origin, playersArg) => {
        const targets = (Array.isArray(playersArg) ? playersArg : [sourcePlayer(origin)]).filter((x) => !!x);
        system.run(() => {
            for (const p of targets) {
                const s = get(p);
                resetCooldowns(s);
                save(p, s, true);
            }
        });
        return ok(`Cooldowns reset for ${targets.length} player(s).`);
    });
    reg.registerCommand({
        name: "plrace:unique",
        description: "Unique lineages: status | release <race> (frees a Unique lineage held by an absent player)",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        mandatoryParameters: [{ name: "plrace:unique_action", type: CustomCommandParamType.Enum }],
        optionalParameters: [{ name: "plrace:race", type: CustomCommandParamType.Enum }],
    }, (_origin, action, raceArg) => {
        if (String(action) === "status")
            return ok(uniqueStatus());
        const race = raceArg === undefined ? undefined : raceByKey(String(raceArg));
        if (!race)
            return bad("Name the Unique lineage to release, e.g. /plrace:unique release nurariten");
        let done = false;
        system.run(() => {
            done = releaseCode(race.code);
        });
        return ok(`${race.name}: claim released${done ? "" : " (if it was held)"}.`);
    });
    reg.registerCommand({
        name: "plrace:bloodmoon",
        description: "Blood Moon control: start | stop | next (force the next full moon) | status",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        mandatoryParameters: [{ name: "plrace:moon_action", type: CustomCommandParamType.Enum }],
    }, (_origin, action) => {
        const a = String(action);
        if (a === "status")
            return ok(bloodMoonStatus());
        system.run(() => {
            if (a === "start")
                start(true);
            else if (a === "stop")
                end("command");
            else if (a === "next")
                forceNext();
        });
        return ok(a === "next" ? "The next full moon will be a Blood Moon." : `Blood Moon ${a}.`);
    });
}
