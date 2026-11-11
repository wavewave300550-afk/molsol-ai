import { Player, system, world } from "@minecraft/server";
import { fxCount } from "./fx";
import { liveTempBlocks } from "./blocks";
import { activeRoutines } from "./tasks";
import { clearCooldowns, remainingTicks, save, stateOf } from "./state";
import { allSpells } from "../spells/registry";
import { setRule } from "../config";

/**
 * Read-only diagnostics over script events (used by the BDS test harness and by operators):
 *   /scriptevent grimoire:debug state <playerName>   -> reply with selection / cooldown snapshot
 *   /scriptevent grimoire:debug world                -> construct / routine / temp block counts
 *   /scriptevent grimoire:debug reset <playerName>   -> clear that player's cooldowns (testing)
 *   /scriptevent grimoire:config <rule> <value>      -> same as /grimoire:config
 * Replies are sent as the script event "grimoire:debug_reply" and printed to the content log.
 */
function reply(payload: unknown): void {
  const text = JSON.stringify(payload);
  system.sendScriptEvent("grimoire:debug_reply", text);
}

function findPlayer(name: string): Player | undefined {
  return world.getAllPlayers().find((p) => p.name === name);
}

export function initDiagnostics(): void {
  system.afterEvents.scriptEventReceive.subscribe(
    (e) => {
      if (e.id === "grimoire:config") {
        const [rule, value] = e.message.trim().split(/\s+/);
        if (rule && value !== undefined) reply({ kind: "config", result: setRule(rule, value) });
        return;
      }
      if (e.id !== "grimoire:debug") return;
      const [cmd, ...rest] = e.message.trim().split(/\s+/);
      const name = rest.join(" ");
      if (cmd === "state") {
        const p = findPlayer(name);
        if (!p) return reply({ kind: "state", name, error: "no such player" });
        const st = stateOf(p);
        const cooldowns: Record<string, number> = {};
        for (const sp of allSpells()) {
          const r = remainingTicks(st, sp.id);
          if (r > 0) cooldowns[sp.id] = Number.isFinite(r) ? r : -1;
        }
        reply({
          kind: "state",
          name,
          tick: system.currentTick,
          selected: st.selected,
          cooldowns,
          preparing: st.prep ? { spell: st.prep.spellId, ticks: system.currentTick - st.prep.startTick } : null,
          empowered: !!st.empowered && st.empowered.until > system.currentTick,
        });
      } else if (cmd === "world") {
        reply({ kind: "world", tick: system.currentTick, fx: fxCount(), tempBlocks: liveTempBlocks(), routines: activeRoutines().map((r) => r.label) });
      } else if (cmd === "reset") {
        const p = findPlayer(name);
        if (!p) return;
        const st = stateOf(p);
        clearCooldowns(st);
        save(p, st);
        reply({ kind: "reset", name });
      }
    },
    { namespaces: ["grimoire"] },
  );
}
