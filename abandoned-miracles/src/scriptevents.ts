/**
 * `/scriptevent` interface for map makers, command blocks and NPCs.
 *
 *   /scriptevent abm:summon <boss> [force]   summon at the sender's position (floor check applies unless "force")
 *   /scriptevent abm:dismiss                 end the nearest encounter
 *   /scriptevent abm:arena <boss>            raise that boss's demonstration arena around the sender (REPLACES blocks)
 *
 * <boss> is one of: vesperra, cantor, nomos, orison. The command itself already
 * requires operator permission.
 */
import { Dimension, Player, system } from "@minecraft/server";
import { BOSS_KEYS, BossKey } from "./config";
import { manager } from "./core/manager";
import { V3 } from "./core/math";
import { report } from "./core/trace";
import { giveKit } from "./kit";
import { arenaOf } from "./registry";
import { raiseArenaAt } from "./ui";

function parseBoss(word: string | undefined): BossKey | undefined {
  return BOSS_KEYS.find((k) => k === word);
}

export function initScriptEvents(): void {
  system.afterEvents.scriptEventReceive.subscribe(
    (ev) => {
      try {
        const words = ev.message.trim().split(/\s+/).filter((w) => w.length > 0);
        let dim: Dimension;
        let at: V3;
        let name = "command";
        if (ev.sourceEntity && ev.sourceEntity.isValid) {
          dim = ev.sourceEntity.dimension;
          at = ev.sourceEntity.location;
          if (ev.sourceEntity instanceof Player) name = ev.sourceEntity.name;
        } else if (ev.sourceBlock) {
          dim = ev.sourceBlock.dimension;
          at = { x: ev.sourceBlock.x + 0.5, y: ev.sourceBlock.y + 1, z: ev.sourceBlock.z + 0.5 };
        } else {
          return;
        }
        const floor = { x: Math.floor(at.x) + 0.5, y: Math.floor(at.y), z: Math.floor(at.z) + 0.5 };
        if (ev.id === "abm:summon") {
          const key = parseBoss(words[0]);
          if (!key || !manager.has(key)) return;
          const res = manager.trySummon({ dimension: dim, location: at, name }, key, floor, words[1] === "force");
          if (!res.ok && ev.sourceEntity instanceof Player) {
            ev.sourceEntity.sendMessage({ rawtext: [{ translate: `abm.summon.fail.${res.reason ?? "unknown"}`, with: [String(Math.round((res.coverage ?? 0) * 100))] }] });
          }
        } else if (ev.id === "abm:dismiss") {
          const enc = manager.nearest(dim, at);
          if (enc) manager.cancel(enc);
        } else if (ev.id === "abm:kit") {
          if (ev.sourceEntity instanceof Player) giveKit(ev.sourceEntity);
        } else if (ev.id === "abm:arena") {
          const key = parseBoss(words[0]);
          if (key && arenaOf(key)) raiseArenaAt(dim, floor, key);
        }
      } catch (e) {
        report("scriptevent", e);
      }
    },
    { namespaces: ["abm"] },
  );
}
