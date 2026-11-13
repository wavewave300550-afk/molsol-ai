import { Player } from "@minecraft/server";
import { GrimoireDef, SpellMeta } from "./registry";
import { PrepHandle, setPresenter } from "./presentation";
import { particle, sound } from "../lib/fx";

/** Selection / preparation presentation for the three Grimoires (placeholder until books are built). */
export function installBooks(): void {
  setPresenter({
    select(p: Player, g: GrimoireDef, _m: SpellMeta) { void g; },
    prepStart(p: Player, g: GrimoireDef, _m: SpellMeta): PrepHandle {
      void g;
      return {
        tick(t) { if (t % 4 === 0 && p.isValid) particle(p.dimension, "dw_mote", { x: p.location.x, y: p.location.y + 1.6, z: p.location.z }); },
        release() { if (p.isValid) void 0; },
        cancel() {},
      };
    },
    deny(p: Player, g: GrimoireDef) { void g; void p; },
  });
}
