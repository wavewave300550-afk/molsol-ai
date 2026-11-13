import { Player } from "@minecraft/server";
import { GrimoireDef, SpellMeta } from "./registry";
import { PrepHandle, setPresenter } from "./presentation";
import { particle, sound } from "../lib/fx";

/** Selection / preparation presentation for the three Grimoires (placeholder until books are built). */
export function installBooks(): void {
  setPresenter({
    select(p: Player, g: GrimoireDef, _m: SpellMeta) { sound(p.dimension, `${g.id}.select`, p.location, 0.8); },
    prepStart(p: Player, g: GrimoireDef, _m: SpellMeta): PrepHandle {
      sound(p.dimension, `${g.id}.charge`, p.location, 0.8);
      return {
        tick(t) { if (t % 4 === 0 && p.isValid) particle(p.dimension, `${g.id}_charge`, { x: p.location.x, y: p.location.y + 1.6, z: p.location.z }); },
        release() { if (p.isValid) sound(p.dimension, `${g.id}.release`, p.location, 1); },
        cancel() {},
      };
    },
    deny(p: Player, g: GrimoireDef) { sound(p.dimension, `${g.id}.deny`, p.location, 0.6); },
  });
}
