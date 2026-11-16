# Technical Compatibility Report

*Version 1.3.1 — foundation races 001–003 plus Expansion 01 (races 004–006), with the bodies, animations and effects of races 004–006 redrawn in 1.2.0, the generated Molang rewritten into the forms vanilla files use in 1.2.1 (same motion), new ability effects for every race in 1.3.0, and in 1.3.1 a restructured Spaghetti Monster body plus six display-check items (`plrace:form_<race>_static`, never given in play). Nothing about how any race is stored changed: same pack ids, item ids, race codes, form names, saved player data and world settings. Races 001–003 keep their models and textures; their animation text was only rewritten, with identical values (checked by `tools/molang_equiv.py`).*

## Target

| Item | Value | How it was determined |
|---|---|---|
| Minecraft Bedrock | **1.26.60** (released 27 Oct 2026; hotfixes 1.26.61–1.26.63) | `Mojang/bedrock-samples` `version.json` (latest 1.26.60.5) and npm publish dates |
| `min_engine_version` | `[1, 26, 60]` on both packs | required by the script module versions below |
| `@minecraft/server` | **2.11.0** (latest *stable*; 2.12/2.13 are rc/beta for 1.26.70 previews) | `npm view @minecraft/server dist-tags` |
| `@minecraft/server-ui` | **2.3.0** (latest stable) | `npm view @minecraft/server-ui dist-tags` |
| Experimental toggles | **None required** | only stable APIs/components are used; scripts typecheck against the official stable typings |
| Manifest | `format_version` 2, RP `pack_scope: "world"`, BP ↔ RP dependencies, `product_type: addon` | Cooperative Add-On guidelines |

Not used on purpose: manifest v3 / pack settings (documented as preview), JSON UI overrides, dimension/biome files, beta script modules, custom materials/shaders.

**Script API surface added for races 004–006** (all present in the stable 2.11.0 typings the scripts are compiled against — the typecheck would fail otherwise): `Dimension.spawnEntity` with `initialRotation` / `spawnEvent`, `Entity.teleport` with `facingLocation`, `Player.tryTeleport` (`checkForBlocks`), `Entity.setRotation` (mobs only), `Camera.fade`, `world.afterEvents.explosion`, `MolangVariableMap` for particle variables, `world.getTimeOfDay` (read only), the `/fog` command per player, input permission categories, world dynamic properties (the Unique claim).

## How the playable bodies work (and why)

Mojang's *Guidelines for Building Cooperative Add-Ons* say add-ons should **not override `minecraft:player`**, should not change vanilla files, and should not override a player's skin. A playable-race add-on fundamentally changes how players look, so the design minimises the footprint instead of taking the usual "replace `player.json` + `player.entity.json`" route:

1. **No player override at all in the behavior pack.** All race logic is Script API driven (stable 2.11.0): effects, attribute tweaks, damage hooks (`entityHurt` before-event), input events, item custom components, dynamic properties.
2. **The racial body is an attachable.** Each race form is a custom head-slot item ("crest") with an attachable whose geometry copies the vanilla player's bone names and pivots (`root, waist, body, head, rightArm, leftArm, rightLeg, leftLeg`). Attachable bones bind to the wearer's animated skeleton exactly like vanilla armour, so the creature inherits **every** vanilla pose — walking, sprinting, sneaking, swimming, crawling, riding, sleeping, gliding, bow/crossbow/trident/shield/spyglass/brush poses, attack swings, first-person — with zero risk of falling out of date when Mojang changes player animations. Race-specific motion (tails, gills, plates, ears, antlers, floating stones, rune rings, digitigrade legs) lives on child bones animated by the attachable's own Molang animations.
3. **Visual states are item swaps.** `plrace:form_golem_siege`, `..._bastion`, `..._salamander_dormant`, `..._jackalope_awakened`, `..._xenentoma_surge`, `..._spaghetti_revelation`, `..._nurariten_throne`, … Swapping the crest swaps the attachable, whose intro animation plays the transformation. 30 form items in total (15 before 1.1.0).
4. **Ability poses** are vanilla `/playanimation` (`Entity.playAnimation`) clips on the player skeleton, so held items and armour move with them.
5. **The only vanilla overrides** are two *render controllers*, each byte-for-byte vanilla except one added condition:
   * `controller.render.player.third_person` — every part gets `&& !<a race crest is worn>`, hiding the player's own skin **only while a race form is manifested**;
   * `controller.render.armor` — vanilla armour is hidden on manifested forms (it does not fit non-human anatomy). Instead, **armour assimilation** plates on the creature appear for each worn slot, tinted by the armour material (leather, chain, iron, gold, copper, diamond, netherite, turtle).
   These are defined in separate files under `render_controllers/plrace/`, so no vanilla *file* is replaced, and they are verified against the vanilla 1.26.60 definitions by `tools/validate.py`.

**Consequences, stated plainly**
* The head armour slot holds the locked crest while the form is manifest. To compensate, crests give helmet-level armour (Salamander 2, Golem 3, Jackalope 1, Xenentoma 2, Spaghetti Monster 1, Nurariten 2), accept helmet enchantments through **Infuse Crest**, and can be **veiled** (form hidden, powers kept, head slot free for a normal helmet, turtle shell or carved pumpkin).
* If another add-on overrides the same two render controllers, pack order decides; the loser shows either the player skin under the creature or vanilla armour on it. Gameplay is unaffected.
* Add-ons that override `player.entity.json` with a *different render controller name* still work; the creature is drawn, but that add-on decides whether the human skin is also drawn.
* Not changed (by design, the engine does not support it safely): **hitbox** (0.6 × 1.8), **eye height/camera**, **name-tag height**. The Golem is drawn 2.4 blocks tall but is hit like a normal player; the Jackalope's ears and antlers, the Xenentoma's abdomen and the Nurariten's halo and gate are not hittable. The Spaghetti Monster's hover is visual (the body is drawn a little above the feet); it is not flight.

## Helper entities (races 004–006)

Some abilities need a real object in the world. Every such object is a **script-owned helper entity** with no AI, no loot, no XP and no spawn egg (`is_spawnable: false`):

| Entity | Used by | Health / collision | Lifetime (script) | Safety-net despawn timer |
|---|---|---|---|---|
| `plrace:exuvia` | Xenentoma, Exuvia Proxy (a decoy hostile mobs attack; family `player`) | 16 HP, collides | 8 s | 16 s |
| `plrace:meatball` | Spaghetti Monster, Meatball Ricochet | invulnerable, no physics | until it returns (≤ 8 s) | 14 s |
| `plrace:celestial_gate` | Nurariten, Uninvited Temple (normal) and HYAKUTEN CHŪKŌ (`plrace:huge` event, ×3.6 in the sky) | invulnerable, no physics | 10–13.5 s | 20 s |
| `plrace:herald` | HYAKUTEN CHŪKŌ, stage II | invulnerable, no physics | ≤ 8.3 s | 20 s |
| `plrace:procession` | HYAKUTEN CHŪKŌ, stage III–IV (one entity = one column of 12 attendants) | invulnerable, no physics | ≤ 6.8 s | 20 s |

All carry the family `plrace_proxy`. They are removed when their owner dies, leaves, changes dimension or lineage; anything left after a crash or `/reload` is purged on load and every minute; and the behavior-pack timer despawns them even if scripts stop. Abilities never target them, and `/kill @e` removes them like any entity.

**The Hundred Heavens without a hundred mobs.** The brief asked for a procession of one hundred without one hundred AI mobs. The ultimate uses **ten entities**: one gate, one pair of heralds (one model), and eight column entities whose single geometry holds twelve attendants each, marching by script teleports along a shared path — 96 attendants + 2 heralds + the gate + the Sovereign = one hundred. No pathfinding, no physics, no per-figure ticking; the attendants' walking is client-side animation.

## World, sky and time

* Nothing in the add-on changes the world's **time, weather, sky or lighting**, claims land, or places/breaks blocks. Nurariten's day/night relationship only *reads* the time of day.
* Courts (Uninvited Temple, the ultimate's court) are script-side circles drawn with particles; no blocks, no protection, no persistence.
* The ultimate's golden haze is a vanilla fog entry (`plrace:heaven_light`, user id `plrace_hh`) pushed on each nearby player's own fog stack and removed afterwards — also on logout (cleared on the next join), death, dimension change and `/reload` (cleared on load). One soft golden screen fade (`Camera.fade`, 1.5 s) plays for players within 18 blocks. Both can be disabled in World Settings (*HYAKUTEN CHUKO screen effects*).
* Edict of the Lowered Gaze tilts a *mob's* head down once (`setRotation`); the mob's AI resumes immediately. Players' cameras are never moved.
* Unannounced Arrival uses `tryTeleport` with block checks after a line-of-sight ray and a safe-floor search (no walls, no void, no lava/fire/cactus/powder snow/magma/campfire/dripstone/cobweb).

## Unique lineages

* `rarity: "unique"` in a race definition makes it Unique: one holder per world by default (`uniqueExclusive` setting), a fifth ultimate ability, its own Codex styling and a world announcement.
* The claim is a world dynamic property (`plrace:unique`), kept consistent with what the player actually holds on every join, release and lineage change. Operators can inspect or release claims with `/plrace:unique status|release <race>`.
* Future Unique races need no framework change: set `rarity: "unique"` and add a fifth ability flagged `ultimate: true`.

## Cooperative-guideline checklist

| Guideline | Status |
|---|---|
| Unique namespace for every identifier (`plrace:`) — items, entity, particles, fog, animations (`animation.plrace.*`), controllers, geometry (`geometry.plrace.*`), lang keys, dynamic properties, commands | ✅ |
| Textures two folders deep (`textures/plrace/races/...`) | ✅ |
| No `minecraft:player` override, no vanilla file replacements | ✅ (two render-controller *definitions* overridden, see above) |
| No experimental features, both manifests have `min_engine_version`, BP and RP depend on each other, RP `pack_scope: world` | ✅ |
| No JSON UI/font overrides; HUD uses the action bar | ✅ |
| No dimension/biome files; no vanilla sound/lang overrides | ✅ |
| Guide book given once per player (Lineage Codex), short chat message, recipe uses vanilla items (book + lapis + bone meal) | ✅ |
| No terrain destruction; no ticking areas | ✅ |
| Size budget (< 25 MB, < 3,500 files): 1.9 MB packaged, ~7.8 MB unpacked, 374 files (v1.3.0); every model texture ≤ 256 KB of texture memory, the particle atlases ≤ 1 MB | ✅ |

## Performance

* One 1-tick loop only does work while a channel (multi-stage ability) is active; a 4-tick loop drives HUD/temporary forms; a 20-tick loop runs passives (a handful of block probes per player, one entity query for jackalope senses); Blood Moon checks every 2 s; persistence every 5 s and on important changes.
* Ambient creature effects (spores, rune motes, embers, bubbles) are emitted **client-side by the attachables**, costing no server work or network packets; burst limits are small (2–4 particles per emission).
* Ability VFX use one `spawnParticle` call per visual event (the snare strand, shard stream and rune circle are single emitters driven by Molang variables).
* Geometry (base forms, bones / cubes incl. cut-out and accent layers): Salamander 87 / 179, Golem 70 / 110, Jackalope 61 / 93, Xenentoma 74 / 103 (154 before 1.2.0), Flying Spaghetti Monster 68 / 136 (593 before 1.2.0), Nurariten 64 / 97 (court 96, throne 105); textures 256×256 or 256×128 RGBA.
* HYAKUTEN CHŪKŌ adds ten entities for ≤ 10 s: ~1,050 cubes in total (eight 124-cube columns, a 36-cube gate, a 21-cube herald pair) and ~150 animated bones, driven by short looping client animations. Script cost per tick: one teleport per column, ground probes every 4 ticks per column, one small entity query per column every 4 ticks. Particle emitters are single bursts (seals, rings, fractures) — never per-figure.
* New race ambient effects (sensilla motes, sauce drips, royal motes) are client-side attachable particles with 1–3 particles per emission, like the foundation races.
* Since 1.3.0 every ability effect is an entry effect (same identifier as before) that starts its layers through particle **events** (`emitter_lifetime_events` → `particle_effect` of type `emitter`), all in particle format 1.10.0, using flipbook UVs, `lookat_direction` with a velocity or custom direction, `emitter_transform_xz` ground decals, `lookat_y` pillars and `particle_motion_collision`. They draw from a third texture, `textures/plrace/races/particles/particles_vfx.png` (512×512, 1 MB of texture memory). One cast creates at most 68 particles (the rite of transformation; the heaviest ability is 53), all client-side.
* Since 1.2.0 the effects of races 004–006 use a second particle texture, `textures/plrace/races/particles/particles_ex.png` (256×256, full colour, 76 KB on disk), with the standard `particles_add`, `particles_blend` and `particles_alpha` materials; their identifiers are unchanged, so the scripts did not change. Races 001–003 keep the original 128×128 atlas.
* Animation (v1.0.2): each form runs ~10 layers. Values shared by every layer — stride phase, the vanilla swing, speed, sprint and the fitted body bob — are computed **once per frame** in the attachable's `pre_animation` script and read as variables (`v.plr_*`), which halves the Molang work; the longest single channel expression is ~650 characters. Layers that only matter in third person are switched off in first person, idle behaviours and landings are short keyframed clips run by tiny controllers, and footfall dust is a 6-particle client-side burst.
* Mobile/iOS: no shader changes, no custom materials, only vanilla entity materials (`entity_emissive_alpha` for glowing runes/veins, `entity_alphatest` for leaves and fur fringes, `entity_alphablend` for the mirage).

## Known limitations (engine level)

* **First-person arms:** the attachable also binds in first person; a slightly larger first-person-only sleeve encloses the vanilla arm. If a future version stops drawing armour attachables in first person you will simply see your normal arm.
* Molang owner queries inside attachables (`q.target_x_rotation`, `q.hurt_time`, `q.modified_move_speed`, `q.vertical_speed`, `q.is_item_equipped`, `q.yaw_speed`, …) and the player's public `v.attack_time` drive gaits, look-follow, flinches and attack reactions. If a platform does not resolve one of them in attachable context, that detail is static; nothing breaks (`q.yaw_speed` units are not documented, so its effect is clamped).
* `query.is_item_name_any('slot.armor.head', …)` (client-side) controls skin hiding; it is documented for all equipment slots.
* Input permission categories (`LateralMovement`) are used for rooting and for HYAKUTEN CHŪKŌ; they are restored on the end of the ability, death, dimension change, lineage change, and on the next join if the player disconnects during it.
* If two Unique holders are allowed (operators turned exclusivity off) and both use the ultimate near the same witness, the first to finish lifts that witness' haze early (both use the same fog user id). Cosmetic only.
* `q.time_of_day` drives one Nurariten idle behaviour; the gameplay day/night logic is server-side and does not depend on it.
