import { defineSpell } from "../core/registry";

// STUB -- replaced by the real implementation.
export default defineSpell("dw02", (ctx) => {
  ctx.caster.sendMessage("dw02 is not implemented yet");
  ctx.scene.endAt(1);
});
