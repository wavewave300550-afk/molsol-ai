import { defineSpell } from "../core/registry";

// STUB -- replaced by the real implementation.
export default defineSpell("ed02", (ctx) => {
  ctx.caster.sendMessage("ed02 is not implemented yet");
  ctx.scene.endAt(1);
});
