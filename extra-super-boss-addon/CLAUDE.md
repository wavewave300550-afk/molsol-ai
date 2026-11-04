# Extra Super Boss: rules for every boss

These rules come from the project owner and apply to every boss added to this add-on.

1. **Every boss has an ULTIMATE, and it comes from his real history.** Research the person and build the Ultimate
   on something they actually made or did, so it is unmistakably theirs. Da Vinci's is **Il Gran Cavallo**, the clay
   horse of Milan that French archers destroyed in 1499. Edison's is **Mary Had a Little Lamb**, the first recording
   ever, made on his tinfoil phonograph. **Never assemble an Ultimate from the boss's regular skills**: the owner
   rejected that ("don't just stuff other skills in"). It must be stylish and spectacular, with a signature
   showpiece entity, an on-screen title naming it, camera shake and clear counterplay. Weave a historical detail into
   the counterplay where possible (shooting the clay horse like the archers did). It triggers below 35% health and
   repeats on a cooldown. `tools/validate.mjs` fails the build if a boss lacks an `ultimate` action, animation,
   controller state, script trigger, or a showpiece registered in `SHOWPIECE`.
2. **Faces must look good, not goofy.** Use `handsome_face()` in `tools/gen_model.py` (anime-style almond eyes with a
   heavy upper lash line, clean brows, minimal nose, short mouth, soft jaw). Male characters must read as male. Check
   close-up renders before shipping.
3. **Docs and chat are in English.** In-game text is English too, because Bedrock has no Thai UI language.
4. Every boss follows the reference art the owner sends, keeps the shared pipeline (spec.py timings, balance.json,
   offsets measured from the model), and ships with smoke tests for every ability, including the Ultimate.
5. Build with `npm run build` (Creator Tools 0 errors, all cross-checks, all smoke checks) and re-render previews
   with `npm run preview`. Say plainly that nothing has been tested in the real game until it has.
