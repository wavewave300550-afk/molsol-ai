import { defineSpell } from "../core/registry";

// STUB -- replaced by the real implementation.
export default defineSpell("ed01", (ctx) => {
  ctx.caster.sendMessage("ed01 is not implemented yet");
  ctx.scene.endAt(1);
});
