# Testing Report

*Version 1.4.0 (races 001–009: Expansion 02 adds races 007–009; races 004–006 redrawn in 1.2.0, the in-game hotfixes 1.2.1 and 1.3.1 below, and new ability effects for every race in 1.3.0 — see [CREATIVE.md](CREATIVE.md#expansion-02-v140-races-007009)).*

**Bottom line:** everything that can be verified without a Minecraft client was verified and passes. What only a real client or server can show — visuals, timing, and "feel" — has **not** been verified in game, and is listed separately below as **proposed** in-game tests. Nothing in this report claims an in-game result that did not happen.

## v1.4.0 — Expansion 02: races 007–009
* **`npm test`: 372 / 372 assertions** (87 new: the three lineages, all thirteen of their abilities, the Bathyas sword's recovery after death and logout, Display Check across nine bodies, and its new still-body fallback), **validator 98,876 checks, 0 errors**, TypeScript strict 0 errors, **Creator Tools 0.21.0: 0 errors**, 9 warnings (the nine race portraits, used from scripts), 85 recommendations, 41 test suites passed.
* **Budgets (from the build):** Dinosauroid 86 bones / 171 cubes (≤ 180 in its display forms), Bathyas 71 / 145, Octamyces 89 / 214 (218 in Sporeveil) — all under the 90-bone budget; longest Molang expression in the new animation files 358 characters; no sign pairs, no scientific notation, every ternary in parentheses. Feet on the ground: the fitted body bob is within 0.18 px (Dinosauroid sprint) and 0.15 px (Bathyas sprint) of the measured foot floor; the Octamyces floats.
* **Effects:** 37 new particle identifiers, at most 31 particles per cast; the Lure of the Impaled Sun was redrawn after its first preview showed camera-facing rings large enough to wash over the screen (the rings now roll along the ground and no camera-facing layer is larger than the body).
* **Art review (offline renders of the shipped geometry, textures and animations):** turnarounds on white, every form, walk / sprint / jump / attack / hurt and idle behaviours were rendered and looked at; problems found and fixed before release: Bathyas' *Lure* pose raised the hand above the head instead of shading the eyes, his *Isopod Bastion* pose swung the arms outward instead of crossing them; three ability poses and the rite of transformation tilted the player's head bone, which would part the Dinosauroid's skull and the Octamyces' cap from their neck / stalk rigs (those poses no longer move the head for these bodies); the hyphal echo lacked the Octamyces' alpha-tested parts.
* **Display Check fallback:** if a player's own body was invisible only while animated (visible as its still twin), the check now offers to wear the still twin — the same geometry, texture and materials without animation — and *Use the animated body again* switches back; the choice is saved per lineage.
* **Not verified in game** (no client here): see the proposed tests in item 13 below. The Spaghetti Monster's files are unchanged since 1.3.1 — please run *Codex → Display Check* and send the line it prints.

## v1.3.1 hotfix — the Spaghetti Monster still invisible, plus a display check
The player reported that **the Flying Spaghetti Monster was still invisible** on 1.3.0 (in the ready-made test world). Everything in the pack was compared again, file by file, with the races that do show up: attachable, items, render controllers, materials, geometry (bones, cubes, bounds, pivots, UVs, number formats, bone and locator names against the player skeleton), textures (PNG chunks, the alpha its faces sample), animations (every channel's structure and Molang syntax, values at extreme in-game states — days of play, long walks, creative-flight speeds — never NaN, never huge, never collapsing), controllers, particles, identifiers. Nothing invalid was found, and vanilla files show that a scale animation with weight 0 does not shrink a bone. What remains are three things only the Spaghetti Monster does:

* it was the only race with **no geometry under its head bone** (everything hung from the body);
* 115 of its 131 cubes hang from **one bone that eleven animations scaled** (landing, hurt, airborne, intro, idle behaviours...); every other race scales its large parts in at most two;
* together with the Xenentoma it computed its eye **saccades in `pre_animation`** variables.

**Changes:** the Holy Colander halo now rides the head group (it follows a fifth of the player's look — still above the eyes; `docs` renders unchanged otherwise); the body bone is scaled only by the breathing and the entry pop (the squash of landing, hurt, airborne and the forms became small dips); the eyes dart with a self-contained quantised-sine expression (`anims/life.py: dart`) instead of `pre_animation` saccades. Motion and look are otherwise the same.

**A display check, so the next report is exact:** *Lineage Codex → Display Check* shows every lineage's body for 3 s with a camera in front of the player, asks which ones could not be seen, then shows those again as a **still twin** (`plrace:form_<race>_static`: the same geometry, texture, materials and render controllers, with no animation, script or particle — the validator checks the twin is identical otherwise). The chat line it prints says, per race, whether the body is missing *with* animation only (a script/animation problem) or *without* it too (the device cannot draw that model), and it names **the resource-pack version the client really uses**: that text comes from the pack's own lang file (`plrace.rp_version`), so an older copy of the pack active in *Settings → Global Resources* shows up as a wrong number (or the raw key). The Codex front page shows the same line.

`npm test` **285/285** (8 new: the check shows every body in turn, re-shows a reported one as its twin, puts a camera in front and clears it, restores the player's own form and movement, and names the hidden races and the resource-pack version). Validator 59,243 checks, 0 errors.

**Still to be confirmed in game:** that the Spaghetti Monster is visible. If it is not, the Display Check line (and *Settings → Creator → Content Log GUI*) say exactly where it fails.

## v1.3.0 — new ability effects for every race
* **Validator, new checks for layered effects:** every child effect an event starts exists; every event a creation/expiration/timeline entry names is defined; flipbook frames stay inside their texture; particle Molang parses, has no sign pairs, and reads only built-in particle variables or variables the scripts pass in; particle atlases may use up to 1 MB of texture memory (the new 512×512 atlas), other textures keep the 256 KB budget.
* **Budget:** `tools/vfx/lib.py: particle_count` sums an entry effect and every layer it fires: the largest is the rite of transformation (68 particles); the largest ability is Sundew Snare (53); none is over 80.
* **Previews:** `python3 tools/vfx_gifs.py` re-enacts each ability's script calls (identifiers, positions, timing, variables) with the race's model and simulates the pack's particle files (rates, lifetimes, shapes, motion, collision with the floor, Molang sizes, facing modes, flipbooks, gradients, add/blend, and the events that start the layers) → `docs/images/vfx_*.gif`. This is our simulator, not the game's renderer.
* **Scripts:** the reticle now uses each ability's own `aim()` (the same call the cast uses); the court boundary fires once per 8- / 20-tick window; Root / Bloom / Dormant no longer play their burst twice; the meatball entity fires its sauce trail. `npm test` 277/277.

## v1.2.1 hotfix — found in game by the player
After installing v1.2.0 the player reported that **the Flying Spaghetti Monster was completely invisible** in third person and that **some forms did not animate at all**. Nothing in the static checks had failed, so the files were compared against what Bedrock itself is known to accept:

* The Spaghetti Monster's attachable was byte-identical to v1.1.0 and its geometry and texture were sound (no NaN, every face samples opaque texels, bounds cover the body, every animation/controller reference resolves). Its **v1.2.0 animation file was the only file in the pack containing Molang of the form `a - -90`** (ten expressions from travelling waves with a negative phase). Mojang's own files write `* -15`, `+ -8`, `(-this` and `, -40`, but never a minus followed by a negated operand. Our own parser accepted it; Bedrock's evidently is stricter.
* The new races also carried unusually long expressions (up to 895 characters, from the eye/head saccades and the 12-harmonic ground fit).

**Changes (motion unchanged):**
* Every Molang string the build writes is folded to the proven sign form (`a + -b` → `a - b`, `a - -b` → `a + b`), and pack JSON is written strictly (no NaN/Infinity).
* Long sub-expressions are computed once per frame in `pre_animation` and referenced as variables (saccade clocks, steps, eases and targets; the fitted body bob in short partial sums), so the longest expression is now 699 characters in an old-style locomotion channel and 385 in the Spaghetti Monster.
* Locator names no longer repeat bone names in races 004–006, and cube angles stay within (−180°, 180°].
* The validator now also rejects a sign pair (`+ -`/`- -`), expressions over 700 characters, non-strict JSON, locator/bone name clashes and out-of-range cube angles in races 004–006, checks the bound bones of every race against the player skeleton (004–006 were not covered before), and warns about expressions over 400 characters and ternaries without parentheses.
* **Proof that nothing moves differently:** `python3 tools/molang_equiv.py <v1.2.0 packs>` evaluates every attachable's `pre_animation` and every animation channel of both builds under random player states — 934,600 evaluations, worst relative difference 8.9e-16 (floating point only).

**Still to be confirmed in game:** that the Spaghetti Monster is visible and every form animates. If anything is still missing, *Settings > Creator > Content Log GUI* shows the exact error on screen.

## What was executed (all passing)

| Check | Tool | Result |
|---|---|---|
| TypeScript strict typecheck against the official **@minecraft/server 2.11.0** and **@minecraft/server-ui 2.3.0** typings | `npx tsc --noEmit` | **0 errors** |
| Minecraft Creator Tools 0.21.0 validation (the "Add-On Best Practices" suite Mojang points creators to) | `npx @minecraft/creator-tools@0.21.0 validate -i packs` | **0 errors**, 9 warnings, 85 recommendations, 41 test suites passed (v1.4.0; below) |
| Project static validator: manifests, every geometry/texture/animation/render-controller/particle/locator link, animation bone names, UV bounds, attachable skeleton pivots = vanilla player skeleton, player/armour render-controller overrides = vanilla + one condition, items/icons/lang, every identifier string in the compiled scripts (particles, vanilla sound events, effect ids, items, entities, pose animations), texture memory budget; **since v1.0.2 also every Molang expression** in animations, controllers and attachable scripts parses, uses only known queries, and every variable it reads is set in `pre_animation` or exposed by the player; controller transitions point at existing states | `python3 tools/validate.py` | **98,876 checks, 0 errors** (v1.4.0; 60,577 in v1.3.0; 59,521 in v1.2.1; 48,774 in v1.2.0; 63,151 in v1.1.0 — the count follows the number of cubes and faces, and the redrawn models use far fewer cubes, e.g. the Spaghetti Monster 131 instead of 588; since v1.2.0 it also rejects numbers in scientific notation inside Molang, and parses every Molang string in the particle effects, which may read only the particle's built-in variables or variables the scripts pass in) |
| Runtime smoke test: the **compiled behavior-pack scripts** run on a strict mock of the Script API, driven through real gameplay scenarios (table below) | `node tests/run.mjs` | **372 / 372 assertions** (v1.4.0; 285 in v1.3.1, 277 in v1.3.0) |
| **Animation runtime (v1.0.2):** the shipped attachables (animate lists, blend conditions, `pre_animation`, Molang, Catmull-Rom keyframes, animation controllers) are executed by an offline interpreter on top of the vanilla player skeleton (walk swing, arm bob, head look, attack swing from Mojang's `player.animation.json`) through idle, walk, sprint, jump/landing, attack and hurt scenarios; idle-behaviour controllers cycle through all their behaviours; no query used by the packs is left unsimulated | `python3 tools/anim_gifs.py` (+ `--fidgets`) | GIFs in `docs/images` |
| **Feet on the ground (v1.0.2):** lowest leg point sampled every tick through walk and sprint cycles of the final packs | runtime above | Salamander −0.04…+0.26, Golem −0.04…+0.11, Jackalope walk −0.08…+0.07 model px from the ground; Jackalope sprint −0.12 at contact, up to +1.57 in the deliberate flight phase |
| **Gait fit for races 004–006 (v1.2.0 bodies):** body bob fitted to the measured foot floor (lowest foot point, sampled 48× per stride) | `tools/build.py` report | Xenentoma walk 0.10 px, six-legged sprint 0.16 px max error (12-harmonic fit; with the default 4 harmonics it was 0.33 / 0.56 px, so the fit was refined); Nurariten walk 0.08 px, sprint 0.10 px; the Spaghetti Monster hovers (no feet to fit). Foot **slide** was not measured offline (see the in-game list) |
| **Races 001–003 unchanged (v1.2.0):** every generated pack file compared with the v1.1.0 release (`git archive bc0a9e4`) | sha256 per file | identical, except the manifests (version 1.2.0), the two pack icons (they show the new art), and the shared render-controller file, in which only the Xenentoma armour-accent entries differ; the nine 001–003 render controllers are identical |
| **Budgets (v1.2.0):** per form, from the shipped geometry | script over `models/entity/plrace` | bones ≤ 74 (limit 90); cubes: base forms 90 / 131 / 90, largest temporary form 167 (the Revelation; limit 300); textures ≤ 256×256; one new 256×256 particle atlas |
| **Animated previews of races 004–006** from the shipped files (idle, walk, sprint, jump, attack, hurt + idle behaviours) | `python3 tools/anim_gifs.py --races xenentoma,spaghetti,nurariten` (+ `--fidgets`) | `docs/images/anim_*.gif`, `fidgets_*.gif` |
| **HYAKUTEN CHŪKŌ staging** rendered with the shipped models placed exactly as the script places them (gate 9 blocks ahead and ×3.6, heralds, eight columns on the 8.4-block circle) | `python3 tools/previews.py` | `docs/images/hyakuten_chuko.png` |
| Visual previews rendered from the exact shipped geometry and textures, including posed states | `python3 tools/previews.py` | images in `docs/images` |

The mock is deliberately strict (and was made stricter for 1.1.0: fog ids must exist in the pack, spawn events must exist on the entity, `getPlayers` honours distance filters, and a weaker effect never replaces a stronger one, as in Bedrock): unknown particle, sound, effect, item, entity or animation ids **throw**, using a removed or dead entity throws (like `InvalidEntityError`), world-modifying calls inside before-events throw (restricted execution), and any exception inside an event listener or scheduled job fails the run. It simulates time of day, days and moon phases, biomes, water, a flat world with block ray-casts, damage events (before/after), deaths and respawns, logout/login, dimension changes, inventories, equipment, item lock modes, enchantments, input permissions and forms with scripted answers.

### Runtime smoke test coverage

| Area | Passed | Assertions |
|---|---|---|
| boot | 6/6 | custom item components registered; command plrace:codex registered; command plrace:setrace registered; command plrace:resetcooldowns registered; command plrace:bloodmoon registered; race enum has keys and permanent codes |
| first join & selection | 11/11 | Lineage Codex given on first join; codex auto-opened for a new player; selection list shows race portraits; confirmation dialog shown before assigning; race 001 persisted; salamander form crest worn in head slot (stable or blooming in the sun); crest locked in slot; crest kept on death; focus given, locked to inventory; transformation title shown; rite aura particle |
| salamander: Sundew Snare | 6/6 | snare damages the target; snare applies Slowness III; snare strand particle; predatory form shown after snare; snare cooldown persisted; predatory form reverts after it expires |
| salamander: cooldown & failure feedback | 4/4 | recasting during the cooldown shows 'recovering'; nothing is cast while on cooldown; no target -> clear failure message; a failed cast does not spend the cooldown |
| salamander: Carnivorous Embrace | 4/4 | selection cycled to ability 2; embrace deals at least 6 damage; embrace heals the salamander; trap snap particle |
| salamander: Root Metamorphosis | 7/7 | selection cycled to Root; walking disabled while rooted; rooted form worn; rooting pose played; knockback / displacement re-anchored while rooted; JUMP uproots and restores movement; rooted form removed after uprooting |
| salamander: Bladder Jet | 3/3 | land jet consumes 20% hydration (78.2 -> 58.2); jet on cooldown after land use; jet does not kill |
| salamander: hydration states | 10/10 | hydration drains in the desert; becomes dormant when parched; dormant form shown; dormant: slight slowness; water rehydrates; gills: conduit power in water; aquatic agility raises swim speed; blooms in water; bloom form shown; swim speed restored on land |
| golem: assignment via command | 3/3 | golem assigned by command; golem form crest; Health Boost II |
| golem: Titan's Edict | 5/5 | siege hammer configuration during the edict; shockwave hits enemies along its path; villagers are never hurt; shockwave travels (rupture particles); form reassembles after the edict |
| golem: Runic Bastion | 5/5 | bastion configuration while braced; frontal melee reduced by bastion and stone body; rear hits only partially reduced; frontal projectiles blocked outright; bastion ends after 5 s |
| golem: Glyph Dominion | 4/4 | rune circle inscribed; enemy inside is slowed (Slowness III); approaching enemy is repelled; golem inside its own circle is Warded (-15%, x0.9 if in Monolith Stance): took 7.649999999999999 |
| golem: rune disruption | 5/5 | disrupted form shown; Glyph Dominion blocked while disrupted; disruption explained on the HUD; magic damage disrupts runes (persisted); runes realign over time |
| golem: Colossus Reassembly | 5/5 | selection on Reassembly; scattered configuration; untouchable while scattered; teleported toward the view (9.5); reconstruction burst hits nearby enemies |
| held use button does not cancel channels | 7/7 | Runic Bastion survives a held use button (2 s of repeats); bastion still reduces frontal damage while the button is held; a deliberate second press drops the bastion (toggle); Bastion can be cast right after Titan's Edict (no lingering Busy); Colossus Reassembly completes with a held use button (z 0.5 -> 9.5); Reassembly still works when looking at the sky (z 0.5 -> 12.5); Reassembly still works when looking down (z 12.5 -> 24.5) |
| jackalope: selection & passives | 2/2 | jackalope form; speed and jump boost |
| jackalope: Lunar Bound | 3/3 | leap moves the jackalope; crescent trail; no fall damage right after a leap |
| jackalope: Antler Brand & sigil | 3/3 | brand charge strikes for 5; branded target takes +3 melee damage; lunar sigil shown over the target |
| jackalope: Velvet Mirage | 5/5 | illusion spawned; nearby hostiles are provoked by the illusion; Velvet Step evades the next blow; struck illusion bursts; attacker dazzled (blindness) |
| jackalope: Crimson Waltz | 3/3 | waltz: 4 leaps + finale (5 hits); crimson crescent slashes; the jackalope ends the waltz beside its target |
| blood moon: lifecycle | 13/13 | full moon dusk rolls the forced Blood Moon (omen); Blood Moon rises at moonrise; crimson fog pushed for overworld players; jackalope awakens; awakening camera fade; Speed II while awakened; two Lunar Bound charges under the Blood Moon; fog removed in the Nether; awakening suspended away from the moon; fog restored back in the overworld; Blood Moon ends at dawn; fog removed for everyone at dawn; jackalope returns to the ordinary lunar form |
| death during a channel | 3/3 | still rooted after holding the button for 2 s; death ends rooting and restores movement; form restored after respawn |
| disconnect mid-ability & relog persistence | 4/4 | rooted before logout; movement restored on rejoin; race restored after relog; cooldowns survive relog |
| multiplayer independence | 2/2 | three players keep three different races; each wears their own form |
| pvp rules | 1/1 | abilities do not hurt players when pvp is off |
| race change policy & cleanup | 4/4 | lineage change gated by the cooldown policy; removing a lineage removes the form; removing a lineage removes the focus; no stray illusions after removal |
| crest infusion keeps enchantments across swaps | 3/3 | crest absorbed Protection IV; configuration swap during edict; enchantment carried across the swap |
| veil and manifest | 4/4 | veiled: head slot free; veiled golem can wear a real helmet; manifest restores the form; the helmet is moved to the inventory, not lost |
| xenentoma: assignment & form | 4/4 | race 004 persisted; xenentoma crest worn; Sensillum Focus given; HUD shows Sensory Clarity |
| xenentoma: eyeless & vibration sense | 4/4 | Blindness and Darkness are removed (no eyes); a moving creature on the ground sends a private vibration ping; vibration pings are private (never broadcast); HUD counts the tremor |
| xenentoma: Foretarsal Survey | 4/4 | survey form raises the forelimbs; survey reports vibrations on the HUD; a still creature close by is felt faintly; survey cooldown spent |
| xenentoma: sensory overload | 4/4 | an explosion 2 blocks away overloads the senses; survey refuses while overloaded; refused cast spends no cooldown; clarity recovers over time |
| xenentoma: Exuvia Proxy | 9/9 | selected ability 2; the shed exuvia stays behind; the shell is a decoy hostile mobs hunt; nearby hostiles are provoked by the shell (it strikes them first); teneral (freshly moulted) form; springs free with Speed II; teneral body takes +20% damage; the new cuticle hardens (Resistance); the exuvia expires and is removed |
| xenentoma: Interstitial Glide | 3/3 | slides several blocks along the ground; a creature slipped past is tripped; glide refuses in mid-air |
| xenentoma: Anamorphic Surge | 3/3 | surge form: the abdomen extends and arches; three timed strikes at range (4 + 4 + 6); the final strike injects through the stylet (Weakness) |
| xenentoma: cleanup | 2/2 | shell present; the exuvia is removed when its owner dies |
| spaghetti: assignment & form | 4/4 | race 005 persisted; spaghetti crest worn; Holy Colander Focus given; HUD shows Sauce |
| spaghetti: His Noodly Touch | 6/6 | the noodles wrap the target (3 damage); the target is held (Slowness IV); the target is pulled toward the monster; a noodle strand extends to the target; with no creature in reach the noodles gather dropped items; nothing to touch -> clear failure, no cooldown |
| spaghetti: Al Dente Reversal | 5/5 | the strands lock into the al dente lattice; projectiles are stopped outright; melee damage reduced by 60%; the first melee attacker is countered; the lattice relaxes afterwards |
| spaghetti: Meatball Ricochet | 7/7 | both meatballs detach; the body shows its empty meatball sockets; softer while the meatballs are away (+20%); the meatballs ricochet between targets (several 4-damage hits); sauce splashes on impact; the meatballs return and are removed; meatballs back in place |
| spaghetti: The Great Pasta Revelation | 5/5 | the body unfolds into the spiral vortex; enemies are dragged toward the vortex; the sauce shockwave lands; sauce shockwave ring; the vortex folds back up |
| spaghetti: sauce, fire and falling | 3/3 | stews fill the sauce to SAUCY; fire makes the pasta brittle; sneaking in the air opens the noodle parachute |
| nurariten: assignment & unique claim | 8/8 | race 006 persisted; Nurariten crest worn; Mandate Shaku Focus given; the arrival of a Unique is announced to the world; the Unique claim is stored with the world; HUD shows the sun's mandate (midday); a second player cannot take a Unique lineage that is already held; the refusal is explained |
| nurariten: Unannounced Arrival | 5/5 | the Sovereign steps 12 blocks along its gaze; gates of light mark departure and arrival; creatures at the arrival are pushed aside and slowed; arriving under a roof it is received as the master of the house; never through walls |
| nurariten: Edict of the Lowered Gaze | 6/6 | enemies in the cone are weakened (II); and staggered (Slowness II); the creature bows its head; nothing behind the Sovereign is affected; a judgment seal appears above the judged; no one in front -> clear failure, no cooldown |
| nurariten: Imperial Expulsion (marks) | 3/3 | 5 damage +3 for its judgment mark; thrown out of the Sovereign's presence; no target -> clear failure |
| nurariten: The Uninvited Temple | 18/18 | the architecture on its back unfolds; a heavy blow interrupts the declaration (Judicial Weakness); half of the cooldown is returned; no court was declared; the court's gate stands at its edge; inside its court it keeps the court form; HUD shows the court timer; enemies inside the court are slowed; +20% damage dealt inside its own court; -15% damage taken inside its own court; pillars of light and a ring mark the boundary; the boundary keeps drawing: 8 pillars every 0.4 s and the ring every second, whatever tick the court opened on; the court changes no blocks and summons nothing hostile; expelled out of the court; an exiled creature is turned back at the threshold; leaving the court breaks it (gate dissolves); Broken Mandate: the Sovereign is weakened; the back architecture folds away |
| nurariten: HYAKUTEN CHUKO - interruption | 12/12 | the title 百天昼行 is shown; one soft golden fade for those near; a golden haze for the caster and witnesses only (no world sky change); the world's time, weather and rules are untouched; a gate opens in the sky; the sky gate is the vast form; the Sovereign stands still; a heavy blow during Stage I interrupts it; the sky closes; every haze is removed; movement restored; half of the 180 s cooldown is returned (73 s left) |
| nurariten: HYAKUTEN CHUKO - five stages | 15/15 | II: two heralds descend with the decree; II: every enemy within 16 is judged (judgment mark); II: and bows (Slowness II); III: eight columns (96 attendants) march - one entity per column, no AI; III: the columns circle the Sovereign; III: the procession tramples whoever stands in its way; IV: the throne without permission; IV: the enthroned Sovereign is protected; IV: all within 12 are weakened; V: the Final Edict strikes 4 +4 per judgment mark; V: the seals converge on the judged; everything dissolves afterwards; the haze is lifted for everyone; movement restored; the Sovereign returns to its usual form |
| nurariten: logout during the procession | 6/6 | procession under way; the caster's helpers are removed when it leaves; the witness' haze is lifted; movement restored on rejoin; no haze left on rejoin; the lineage and its Unique claim survive the relog |
| nurariten: the sun | 5/5 | at night it shines (Nocturne Radiance); HUD shows the night (Nocturne); dusk is the hour of visiting: two arrivals in a row; taking the Rite of Unbecoming releases the Unique claim; then another player may become Nurariten |
| dinosauroid: lineage | 8/8 | race 007 persisted; dinosauroid crest worn; Fossil Quill Focus given; drift follows world time: Plumed at 0; drift follows world time: Webbed at 1500; drift follows world time: Toothed at 3000; drift follows world time: Fanned at 4500; in the dark the display skin glows (night form) |
| dinosauroid: Hindwing Veer | 3/3 | the hindwings throw the body forward; feathers and dust burst at take-off; no fall damage from the leap |
| dinosauroid: Crest of Misclassification | 5/5 | crest, pouch and fans open (display form); the witness is misclassified (Slowness II); and weakened; display wave and the broken cladogram mark; a misclassified creature's blow can miss outright |
| dinosauroid: Sickle Testament | 3/3 | the misclassified victim is opened up (10 damage); and pinned (Slowness IV); an ordinary target takes the plain strike |
| dinosauroid: Taxonomic Error | 5/5 | every structure activates (overflow form); enhanced mobility; the aura misclassifies creatures that come close; the body folds back afterwards; and is spent (Slowness, Weakness) |
| bathyas: lineage | 5/5 | race 008 persisted; the Unique claim is recorded; impaled form worn; HUD shows Stability and Photic Strain; the impaled core: Health Boost; breathes water |
| bathyas: Lure of the Impaled Sun | 4/4 | the sun blazes, a hand shields the eyes (lure form); the lured creature is Sun-Marked (slowed, weakened); and drawn toward the light; a warped ring of light |
| bathyas: Goblin Maw Rush | 3/3 | the jaw shoots out: a Sun-Marked victim takes 11; and the bite feeds Bathyas; teeth and a dark splash |
| bathyas: Isopod Bastion | 3/3 | the plates close (bastion form); Resistance II; a blow on the plates answers with a counterpulse |
| bathyas: Draw the Sun | 11/11 | the sun is in the hand: a real weapon item; it cannot be dropped; the focus moved to a free slot; the open wound glows (unshackled form); drawing is free - the cooldown waits for the return; unshackled: Strength and Speed; Stability drains while the sun is out; a second sun never survives; Return the Sun: the blade goes home; the impaled form is back; the cooldown starts on the return |
| bathyas: recovery | 4/4 | drawn again; death returns the sun to the chest (no sword left); and the state is impaled again; logout returns the sun as well |
| bathyas: Abyssal Daybreak | 10/10 | Bathyas stands his ground; Abyssal Extinction: the deep closes in (a local dark haze); Impossible Sunrise: a pillar of daylight; Leviathan silhouettes pass through the light; Solar Execution; Abyssal Daybreak: 10+ damage to everything within 9 blocks; the haze lifts afterwards; movement restored; and Bathyas is spent; leaving the lineage releases the Unique claim |
| octamyces: lineage | 2/2 | race 009 persisted; octamyces crest worn |
| octamyces: Parallax Sporeveil | 5/5 | the gills unfold (sporeveil form); the zombie is parallax-infected; an iron golem's senses are not fooled; an infected creature strikes a version of you that is not there; the infected leave false afterimages where they stood |
| octamyces: The Eye That Records | 2/2 | the eye focuses (record form); the path is recorded point by point |
| octamyces: Hyphal Offset | 4/4 | the body is elsewhere, stopped short of the wall (z -2.00); an echo lingers where it was; the echo collapses after 3 s; no offset while burning |
| octamyces: The Eleventh Frame | 6/6 | the eye stops; the body is still; the eleven rings open (frame form); the network strikes along the recorded path; the observed creature is struck where it walked; movement restored; the recording is spent |
| display check | 8/8 | the Spaghetti Monster's crest is worn; every lineage's body is shown in turn (plrace:form_salamander > plrace:form_golem > plrace:form_jackalope > plrace:form_xenentoma > plrace:form_spaghetti > plrace:form_nurariten > plrace:form_dinosauroid > plrace:form_bathyas > plrace:form_octamyces > plrace:form_spaghetti_static > plrace:form_spaghetti); a body reported missing is shown again as its still twin; a camera in front of the player, cleared afterwards; the player's own form is back; movement restored after the check; the result names what was hidden, with and without animation; the result names the resource-pack version the client resolves |
| display check: still body fallback | 4/4 | the player now wears the still body; it stays on (no form refresh swaps it back); the choice is saved with the player; and the animated body comes back on request |
| script health | 1/1 | no listener/job exceptions () |

### Creator Tools findings and why they remain
* **9 warnings — "texture not used by any item"** for `textures/plrace/races/ui/portrait_001…009.png`. They are the race portraits shown on the selection-form buttons (`ActionFormData.button(text, iconPath)`); the validator cannot see references made from scripts.
* The 13 `item_texture.json` structure warnings it raised for 1.1.0 (single string instead of a list) were fixed by writing one-element lists.
* **85 recommendations** — newer `format_version` numbers are available for items (1.21.90 is kept because it is the version that introduced data-driven custom components v2), entities, recipe, fogs and client entities. Optional; nothing is wrong with the current versions, and changing them would only add risk to an update that must keep old worlds working.

### Bugs the tests caught and that were fixed during development
* `dolphins_grace` is not a Bedrock effect → the Salamander's aquatic agility now uses the underwater-movement attribute.
* Two sound event names were wrong (`tilt_up.big_dripleaf` is the vanilla name).
* Antler Brand could pass *through* a target at dash speed → swept (segment) hit detection.
* Ability selection/cooldowns and the "rooted" input lock were only saved every 5 s → saved immediately, so a quick logout cannot leave a player unable to walk.
* Velvet Mirage did not dazzle a ranged attacker → the striker is always dazzled.
* Glyph Dominion's "Warded" bonus was defined but not applied → now applied.
* Rune Stability regenerated so fast that disruption lasted ~3 s → rebalanced (2%/s, 4%/s in Monolith Stance).
* Swimming put the Salamander's tail straight up in the vanilla horizontal swim pose (seen in a preview render) → the swim animation swings it back along the body.
* **Reported in game (v1.0.0): Runic Bastion and Colossus Reassembly "did not work."** Cause: the Focus had a 0.05 s use duration, so a held button or a touch long-press re-sent "use" every few ticks, and the engine treated a repeated use of a running ability as "cancel". Bastion ended a few ticks after starting; Reassembly was cancelled before its teleport. Root, Antler Brand, Crimson Waltz and Titan's Edict were exposed to the same flaw. Fixed in v1.0.1:
  - One action per press (the Focus/Codex use lasts while the button is held, and use events without a release gap are ignored).
  - Only Root and Bastion can be ended by a deliberate second press, and only after 0.6 s.
  - Titan's Edict no longer blocks other casts after its slam ("Busy" now names the ability).
  - Reassembly finds footing when you aim at the sky or at your feet.
  The *held use button* scenarios above reproduce the report and now pass.
* **Reported (v1.0.1): the creatures looked stiff and lifeless** → v1.0.2 animation rebuild ([CREATIVE.md](CREATIVE.md#living-motion-v102)). The new previews caught three problems in the new code before release:
  - The Salamander's long feet pitched with the leg swing and sank up to 3.5 px into the ground → soles are counter-rotated to stay flat, then the body bob is fitted to the measured foot height.
  - Offsets applied to parts that hang from the player's swinging limbs (legs, arms) or turning head were rotated with that limb, so a vertical bob partly became a forward slide → offsets are now counter-rotated by the parent's swing / look pitch.
  - The Golem's bob was fitted before its flat-foot correction was added (body floated up to 1.6 px) and measured its sole runes, which are hidden on the ground → fit runs after every leg contribution and ignores the runes.

### Bugs the tests caught during Expansion 01 (fixed before release)
* `world.afterEvents.explosion` was missing from the mock → added, so the Xenentoma's sensory overload is exercised by a real explosion event.
* A sprite named `glyph` collided with the existing `glyph_a…d` sprite family in the particle atlas generator (the build crashed) → renamed `decree`.
* The validator flagged the gate's `plrace:huge` spawn event and the `plrace:heaven_light` fog as unknown ids → it now reads entity events and fog definitions and checks the script's references against them.
* **Nurariten's ultimate could not be interrupted** in the test although the description promised it: its own court (−15% damage taken) turned a 7-damage blow into 5.95, under the 6-damage threshold → the threshold applies to the reduced hit (5+) or to the total damage taken during the preparation (8+); the Temple likewise (4+ / 6 total).
* **The ultimate's court shortened its own cooldown** (noticed in the test output: the refunded cooldown was 61 s instead of 76 s; the court was declared before the cooldown was spent, and courts speed up cooldowns) → only the Temple's court speeds up cooldowns.
* Found in code review before the first run: the court containment check used a helper that normalises vectors (every creature would have been "1 block" from the centre) → horizontal distance.
* The mock replaced a strong effect with a weaker, longer one; Bedrock does not → the mock now behaves like Bedrock, and the court's Slowness I no longer hides the Proclamation's Slowness II in the tests.
* Renders showed the procession's attendants as glowing pegs and the decree scroll as a ladder of black bars → robed attendants with masks, collars and sleeves; brushed text columns and a vermilion seal on the decree.

### Problems the review renders caught during the v1.2.0 redraw (fixed before release)
* A Molang constant came out as `1.225e-16` (the sine of 180° in floating point) — Bedrock's Molang cannot parse scientific notation → the generator rounds it, and the validator now rejects any number in scientific notation.
* Nurariten: forehead brows read as a second pair of eyes and the stacked cranium as a chef's hat; the walk opened the robe like a pair of doors; the ground fit treated the hem panels as feet (the body floated) → soft court brows and one sweeping cranium; the hems follow half of the leg swing; hems are excluded from the foot measurement.
* Xenentoma: the abdomen read as a lizard tail; the six-legged sprint broke because the trunk group pivots at the shoulders (a small-angle lean moved the forelimbs off the body) → a short curled gaster; the forelimbs ride on the thorax and the lean offsets are computed exactly.
* Spaghetti Monster: dithered strands read as straw, the hanging strands as spider legs and the side appendages as crab claws; the meatball sauce caps made brownies of the meatballs → wound strands painted continuously across faces, U-loops underneath, streaming appendages, glaze painted onto rounder meatballs.
* The celestial gate's light read as a ladder → staggered golden mist bands.

### Bugs the tests caught during Expansion 02 (fixed before release)
* **Draw the Sun spent its cooldown on the draw.** The engine charged the cooldown after the cast, but the sword only leaves the chest 0.7 s later, so the "first half is free" check still saw an impaled Bathyas: the draw cost 45 s and the sun could then not be returned (the test's *Return the Sun* failed with the sword still in hand) → whether a use is free is now decided *before* the cast (`freeCast`).
* **After death the sword was gone but the saved state still said "drawn"** until the next 5-second save → Bathyas' state is saved as soon as he is restored (join, respawn, reload).
* The first draft gave marked creatures the `glowing` effect; Bedrock has none (the strict mock rejects unknown effect ids) → statuses are shown by sigils over the head.
* Forms that follow the world (the Dinosauroid's night skin, its four drift configurations) changed only when an ability ran → the visible form is re-synchronised every quarter second.
* `Block.isSolid` does not exist in `@minecraft/server` 2.11.0 (typecheck) → the framework's own solidity helper.
* Test-harness fixes: a duplicated variable in the 009 section, and removing a zombie the Abyssal Daybreak had already killed (the mock throws like `InvalidEntityError`, as the game would).

## Not tested — needs a real game (please check these)

The sandbox has no Minecraft client. A **Bedrock Dedicated Server** test was attempted through Minecraft Creator Tools, but the server requires the **Minecraft EULA to be accepted by you**; I did not accept it on your behalf, so no real-engine run happened. Recommended in-game checklist:

1. **Import & load** on 1.26.60+ with no experiments; Content Log (Settings > Creator > Content Log) shows no `plrace` errors.
2. **Form rendering:** pick each race; the creature replaces your skin in third person (F5) and in the inventory preview; held items sit in the creature's hands; vanilla armour is hidden and the assimilation plates appear with the right tint; first-person shows the creature's arm.
3. **Animation conventions:** tail/gill/ear/antler motion goes the intended way (rotation signs follow the Blockbench Bedrock convention; previews were rendered with that convention).
4. **State swaps:** casting abilities swaps the crest variant (Siege hammer, Bastion wall, Arcane ring, Reassembly burst, Predatory, Rooted, Dormant, Bloom, Hunt, Awakened) without equip sounds becoming annoying.
5. **Controls on iOS/touch:** tapping with the Focus casts; sneak + tap cycles; using it on doors/chests still opens them.
6. **Feel and balance:** dash/leap distances (knockback values), shockwave reach, Blood Moon fog density, swim speed.
7. **Multiplayer:** other players see your form and VFX; PvP setting respected.
8. **Blood Moon:** `/plrace:bloodmoon start` at night; fog + awakening; dawn or `stop` cleans up; reload the world during it.
9. **Races 004–006 (v1.1.0) — proposed in-game tests** (none of these were run in a real game):
   * **Selection:** the Codex lists six lineages with portraits; Nurariten shows **✦ UNIQUE ✦**; a second player sees it as *already held*; `/plrace:unique status` names the holder; a player who had chosen a race in 1.0.x still has it after updating.
   * **Xenentoma:** vibration rings appear only for you and only for moving creatures on the ground; Survey's pings drift (approximate); an explosion or lightning nearby overloads (HUD "OVERLOADED"); the exuvia keeps your shape and mobs attack it; Glide stops at walls and doors; the Surge's segments extend one by one and the three hits land where you aim; Stillness makes you invisible only while motionless.
   * **Flying Spaghetti Monster:** the strand reaches the target and retracts; dropped items fly to you; Al Dente blocks arrows; the meatballs leave their sockets (empty sockets visible), ricochet and come back, and never remain after death/logout; the Revelation's three spiral layers turn in alternating directions with the meatballs orbiting oppositely; Noodle Parachute slows falls; fire makes the body look burnt.
   * **Nurariten:** Arrival never lands inside walls, on lava or in the void, including in caves and on slopes; Lowered Gaze tilts mob heads down for a moment and never moves player cameras; the Temple's pillars and gate appear and vanish without touching blocks; leaving the court breaks it; Expulsion turns exiled mobs back at the edge.
   * **HYAKUTEN CHŪKŌ:** in daylight, at night (local golden haze only for players nearby; the sky and time unchanged for everyone else), under a roof (gate at the door instead of the sky) and in the Nether; all five stage messages; a hit of 5+ damage in the first 2 s interrupts it; the fade is soft and happens once; after the Final Edict, nothing is left behind (`/testfor @e[family=plrace_proxy]` finds nothing) and the haze is gone; on an iPhone the frame rate stays acceptable during stage III.
   * **Dusk / midday:** two Arrival charges at dusk; the Final Edict's midday bonus.
10. **v1.2.0 redraw of races 004–006 — proposed in-game tests** (none of these were run in a real game):
   * **Xenentoma:** sprinting with both hands empty drops it onto all six limbs (tripod scuttle); holding anything, it sprints upright and the item stays in its claw; walking upright, the hind feet do not visibly slide; the curled gaster never clips the ground; the sensilla fans (alpha-tested) look right from all angles.
   * **Flying Spaghetti Monster:** the pupils slide and the lids blink independently; the halo turns slowly above the eyes; the braided arms appear only while a hand holds something; nothing z-fights on the nest (it is built so that no two cubes share a face plane).
   * **Nurariten:** the hem panels swing behind the legs without opening the robe; the six halo arcs and four seals turn as one ring; the court and throne forms unfold behind it without clipping the head.
   * **New particle atlas:** every effect of 004–006 shows its full-colour sprite (no missing-texture squares); `particles_blend` effects (steam, sauce, petals, flakes) fade softly; additive effects (motes, rings, gate, glyphs) glow without hiding the world; an iPhone keeps an acceptable frame rate during HYAKUTEN CHŪKŌ.
11. **v1.3.0 ability effects — proposed in-game tests** (none of these were run in a real game):
   * Every ability of every race shows its layered effect (flash, ring, sparks, debris...) with no missing-texture squares; flipbooks animate (rings expand, circles draw themselves, slashes sweep).
   * Sparks streak along their motion (`lookat_direction`); if any appear sideways, the long and short sides need swapping.
   * Rocks bounce on the ground and stop (collision); effects under a roof are not cut by the ceiling.
   * The court's pillars walk around the circle the whole time (Temple and HYAKUTEN), the ring repeats every second.
   * The aim reticle sits on the creature the ability will actually take (Snare reaches 10 blocks while Blooming).
   * Frame rate on an iPhone while several players cast at once.
12. **Living motion (v1.0.2)** — what the offline runtime cannot prove about the real client:
   * the attachable reads the player's swing variable (`v.attack_time`) and owner queries such as `q.is_item_equipped`, `q.vertical_speed` and `q.yaw_speed` (if one is not resolved, that one reaction is simply absent — the expressions fall back to 0);
   * `pre_animation` variables, controller `blend_transition` cross-fades and `q.all_animations_finished` on the idle-behaviour timer behave as in the interpreter (idle behaviours should start after ~6–8 s of standing still and stop instantly when you move);
   * feet stay on the ground in game for walk and sprint, including with Speed/Slowness effects (the fit assumes the vanilla limb-swing model, `modified_move_speed` 0…1);
   * held items stay in the hands during walking, attacking and idle behaviours.

13. **Expansion 02 (v1.4.0): races 007–009 — proposed in-game tests** (none of these were run in a real game):
   * **Selection:** the Codex lists nine lineages; Bathyas shows **✦ UNIQUE ✦** and can be held at the same time as Nurariten by a different player; *Codex → Display Check* shows all nine bodies.
   * **Unknown Dinosauroid:** the HUD's *Drift* name changes about every 75 s of world time and the body changes with it (plumed / webbed / toothed / fanned); at night or in darkness the display skin glows; Hindwing Veer launches you about 7 blocks along your movement, the hindlimb membranes open, sneaking in the air glides and the landing does no damage; Crest of Misclassification puts a broken-cladogram sigil over creatures nearby and they visibly slow; Sickle Testament pins a misclassified target; Taxonomic Error ends in a short exhaustion; under a two-block ceiling you are slowed.
   * **Bathyas:** the embedded sword glows through the chest; Lure of the Impaled Sun marks creatures with a sun sigil and pulls them a step; Goblin Maw Rush's jaw shoots forward; Isopod Bastion's plates close and leak light; **Draw the Sun** puts *The Impaled Sun* in your hand as a real sword (check it cannot be dropped, put in a chest, a hopper or an item frame, and that there is never a second one — also after death, logout, reload, `/kill` and a lineage change), the unshackled form shows the open wound, Stability drains on the HUD, Return the Sun puts it back and starts the 45 s cooldown; **Abyssal Daybreak**: the dark haze appears only for players within 24 blocks and lifts at the end (also if you log out during it), the pillar, leviathan silhouettes and eruption are visible, an iPhone keeps an acceptable frame rate; the *Unique ultimate screen effects* world setting turns the haze off.
   * **Octamyces Undecimus:** the eye's rings turn independently and the blink folds the polygon shut; the body floats a little above the ground and drifts down when sneaking in the air; Parallax Sporeveil leaves false afterimages around infected creatures and some of their blows miss; The Eye That Records shows an eye sigil and the HUD counts recorded points; Hyphal Offset never ends inside a wall, lava or fire and leaves a translucent echo that bursts after 3 s (`/testfor @e[type=plrace:hyphal_echo]` finds nothing afterwards); The Eleventh Frame strikes along the path the observed creature walked; while burning, Offset is refused and the scorched form shows.
   * **Iridescence and glow:** no flashing, nothing strobes, the impaled sun and the eye glow softly in the dark without lighting the world.

## Reproduce
```bash
cd playable-races
npm install          # official typings + TypeScript (no game files)
npm test             # typecheck -> build -> validate -> smoke
python3 tools/molang_equiv.py <older packs dir>   # same motion as an older build?
python3 tools/previews.py
python3 tools/anim_gifs.py && python3 tools/anim_gifs.py --fidgets   # animated previews
npx -y @minecraft/creator-tools@0.21.0 validate -i packs
python3 tools/anim_gifs.py --races xenentoma,spaghetti,nurariten --clips idle,walk,sprint,jump,attack,hurt && python3 tools/anim_gifs.py --races xenentoma,spaghetti,nurariten --fidgets
python3 tools/review.py spaghetti --out /tmp/review --variants base,rigid,detached,revelation,brittle   # design review sheets
python3 tools/vfx_gifs.py   # ability effect previews (docs/images/vfx_*.gif)
```
