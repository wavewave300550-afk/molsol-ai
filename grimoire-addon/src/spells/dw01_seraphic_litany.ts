import { defineSpell } from "../core/registry";

// STUB -- replaced by the real implementation.
export default defineSpell("dw01", (ctx) => {
  ctx.caster.sendMessage("dw01 is not implemented yet");
  ctx.scene.endAt(1);
});
