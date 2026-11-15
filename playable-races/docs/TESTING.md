# Testing Report

**Bottom line:** everything that can be verified without a Minecraft client was verified and passes. What only a real client or server can show — visuals, timing, and "feel" — has **not** been verified in game, and is listed separately below.

## What was executed (all passing)

| Check | Tool | Result |
|---|---|---|
| TypeScript strict typecheck against the official **@minecraft/server 2.11.0** and **@minecraft/server-ui 2.3.0** typings | `npx tsc --noEmit` | **0 errors** |
| Minecraft Creator Tools 0.21.0 validation (the "Add-On Best Practices" suite Mojang points creators to) | `mct validate` via the debug-addon skill | **0 errors**, 3 warnings, 7 noise, 23 recommendations (below) |
| Project static validator: manifests, every geometry/texture/animation/render-controller/particle/locator link, animation bone names, UV bounds, attachable skeleton pivots = vanilla player skeleton, player/armour render-controller overrides = vanilla + one condition, items/icons/lang, every identifier string in the compiled scripts (particles, vanilla sound events, effect ids, items, entities, pose animations), texture memory budget; **since v1.0.2 also every Molang expression** in animations, controllers and attachable scripts parses, uses only known queries, and every variable it reads is set in `pre_animation` or exposed by the player; controller transitions point at existing states | `python3 tools/validate.py` | **24,283 checks, 0 errors** |
| Runtime smoke test: the **compiled behavior-pack scripts** run on a strict mock of the Script API, driven through real gameplay scenarios (table below) | `node tests/run.mjs` | **136 / 136 assertions** |
| **Animation runtime (v1.0.2):** the shipped attachables (animate lists, blend conditions, `pre_animation`, Molang, Catmull-Rom keyframes, animation controllers) are executed by an offline interpreter on top of the vanilla player skeleton (walk swing, arm bob, head look, attack swing from Mojang's `player.animation.json`) through idle, walk, sprint, jump/landing, attack and hurt scenarios; idle-behaviour controllers cycle through all their behaviours; no query used by the packs is left unsimulated | `python3 tools/anim_gifs.py` (+ `--fidgets`) | GIFs in `docs/images` |
| **Feet on the ground (v1.0.2):** lowest leg point sampled every tick through walk and sprint cycles of the final packs | runtime above | Salamander −0.04…+0.26, Golem −0.04…+0.11, Jackalope walk −0.08…+0.07 model px from the ground; Jackalope sprint −0.12 at contact, up to +1.57 in the deliberate flight phase |
| Visual previews rendered from the exact shipped geometry and textures, including posed states | `python3 tools/previews.py` | images in `docs/images` |

The mock is deliberately strict: unknown particle, sound, effect, item, entity or animation ids **throw**, using a removed or dead entity throws (like `InvalidEntityError`), world-modifying calls inside before-events throw (restricted execution), and any exception inside an event listener or scheduled job fails the run. It simulates time of day, days and moon phases, biomes, water, a flat world with block ray-casts, damage events (before/after), deaths and respawns, logout/login, dimension changes, inventories, equipment, item lock modes, enchantments, input permissions and forms with scripted answers.

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
| golem: Glyph Dominion | 4/4 | rune circle inscribed; enemy inside is slowed (Slowness III); approaching enemy is repelled; golem inside its own circle is Warded (-15%, x0.9 if in Monolith Stance): took 7.65 |
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
| script health | 1/1 | no listener/job exceptions () |

### Creator Tools findings and why they remain
* **3 warnings — "texture not used by any item"** for `textures/plrace/races/ui/portrait_00X.png`. They are the race portraits shown on the selection-form buttons (`ActionFormData.button(text, iconPath)`); the validator cannot see references made from scripts.
* **7 "likely noise"** — `item_texture.json` entries use a single string for `textures`, which Bedrock accepts.
* **23 recommendations** — newer `format_version` numbers are available for items (1.21.90 is kept because it is the version that introduced data-driven custom components v2), recipe, fog and client entity. Optional; nothing is wrong with the current versions.

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
9. **Living motion (v1.0.2)** — what the offline runtime cannot prove about the real client:
   * the attachable reads the player's swing variable (`v.attack_time`) and owner queries such as `q.is_item_equipped`, `q.vertical_speed` and `q.yaw_speed` (if one is not resolved, that one reaction is simply absent — the expressions fall back to 0);
   * `pre_animation` variables, controller `blend_transition` cross-fades and `q.all_animations_finished` on the idle-behaviour timer behave as in the interpreter (idle behaviours should start after ~6–8 s of standing still and stop instantly when you move);
   * feet stay on the ground in game for walk and sprint, including with Speed/Slowness effects (the fit assumes the vanilla limb-swing model, `modified_move_speed` 0…1);
   * held items stay in the hands during walking, attacking and idle behaviours.

## Reproduce
```bash
cd playable-races
npm install          # official typings + TypeScript (no game files)
npm test             # typecheck -> build -> validate -> smoke
python3 tools/previews.py
python3 tools/anim_gifs.py && python3 tools/anim_gifs.py --fidgets   # animated previews
npx -y @minecraft/creator-tools@0.21.0 validate -i packs
```
