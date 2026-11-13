import { defineSpell } from "../core/registry";

// STUB -- replaced by the real implementation.
export default defineSpell("dn01", (ctx) => {
  ctx.caster.sendMessage("dn01 is not implemented yet");
  ctx.scene.endAt(1);
});
