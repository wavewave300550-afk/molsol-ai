# Extra Super Boss: rules for every boss

These rules come from the project owner and apply to every boss added to this add-on.

1. **Every boss has an ULTIMATE.** It must be spectacular: a titled screen moment, an arena-scale telegraph,
   camera shake, and an extra additive render layer that appears only while it runs (Da Vinci's Vitruvian halo,
   Edison's sun aura). It also needs clear counterplay: Da Vinci's golden sanctuaries; Edison's breakable Sun Bulbs and
   line-of-sight cover. The boss is invulnerable during it, triggers it below 35% health, and can repeat it on a 45 s
   cooldown. `tools/validate.mjs` fails the build if any `esb_boss` entity lacks an `ultimate` action, animation,
   controller state, conditional render layer or script trigger.
2. **Faces must look good, not goofy.** Use `handsome_face()` in `tools/gen_model.py` (anime-style almond eyes with a
   heavy upper lash line, clean brows, minimal nose, short mouth, soft jaw). Male characters must read as male. Check
   close-up renders before shipping.
3. **Docs and chat are in English.** In-game text is English too, because Bedrock has no Thai UI language.
4. Every boss follows the reference art the owner sends, keeps the shared pipeline (spec.py timings, balance.json,
   offsets measured from the model), and ships with smoke tests for every ability, including the Ultimate.
5. Build with `npm run build` (Creator Tools 0 errors, all cross-checks, all smoke checks) and re-render previews
   with `npm run preview`. Say plainly that nothing has been tested in the real game until it has.
