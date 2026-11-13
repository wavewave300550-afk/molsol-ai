import { defineSpell } from "../core/registry";

// STUB -- replaced by the real implementation.
export default defineSpell("dn02", (ctx) => {
  ctx.caster.sendMessage("dn02 is not implemented yet");
  ctx.scene.endAt(1);
});
