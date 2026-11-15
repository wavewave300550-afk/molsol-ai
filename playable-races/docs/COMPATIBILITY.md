# Technical Compatibility Report

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

## How the playable bodies work (and why)

Mojang's *Guidelines for Building Cooperative Add-Ons* say add-ons should **not override `minecraft:player`**, should not change vanilla files, and should not override a player's skin. A playable-race add-on fundamentally changes how players look, so the design minimises the footprint instead of taking the usual "replace `player.json` + `player.entity.json`" route:

1. **No player override at all in the behavior pack.** All race logic is Script API driven (stable 2.11.0): effects, attribute tweaks, damage hooks (`entityHurt` before-event), input events, item custom components, dynamic properties.
2. **The racial body is an attachable.** Each race form is a custom head-slot item ("crest") with an attachable whose geometry copies the vanilla player's bone names and pivots (`root, waist, body, head, rightArm, leftArm, rightLeg, leftLeg`). Attachable bones bind to the wearer's animated skeleton exactly like vanilla armour, so the creature inherits **every** vanilla pose — walking, sprinting, sneaking, swimming, crawling, riding, sleeping, gliding, bow/crossbow/trident/shield/spyglass/brush poses, attack swings, first-person — with zero risk of falling out of date when Mojang changes player animations. Race-specific motion (tails, gills, plates, ears, antlers, floating stones, rune rings, digitigrade legs) lives on child bones animated by the attachable's own Molang animations.
3. **Visual states are item swaps.** `plrace:form_golem_siege`, `..._bastion`, `..._salamander_dormant`, `..._jackalope_awakened`, … Swapping the crest swaps the attachable, whose intro animation plays the transformation. 15 form items in total.
4. **Ability poses** are vanilla `/playanimation` (`Entity.playAnimation`) clips on the player skeleton, so held items and armour move with them.
5. **The only vanilla overrides** are two *render controllers*, each byte-for-byte vanilla except one added condition:
   * `controller.render.player.third_person` — every part gets `&& !<a race crest is worn>`, hiding the player's own skin **only while a race form is manifested**;
   * `controller.render.armor` — vanilla armour is hidden on manifested forms (it does not fit non-human anatomy). Instead, **armour assimilation** plates on the creature appear for each worn slot, tinted by the armour material (leather, chain, iron, gold, copper, diamond, netherite, turtle).
   These are defined in separate files under `render_controllers/plrace/`, so no vanilla *file* is replaced, and they are verified against the vanilla 1.26.60 definitions by `tools/validate.py`.

**Consequences, stated plainly**
* The head armour slot holds the locked crest while the form is manifest. To compensate, crests give helmet-level armour (Salamander 2, Golem 3, Jackalope 1), accept helmet enchantments through **Infuse Crest**, and can be **veiled** (form hidden, powers kept, head slot free for a normal helmet, turtle shell or carved pumpkin).
* If another add-on overrides the same two render controllers, pack order decides; the loser shows either the player skin under the creature or vanilla armour on it. Gameplay is unaffected.
* Add-ons that override `player.entity.json` with a *different render controller name* still work; the creature is drawn, but that add-on decides whether the human skin is also drawn.
* Not changed (by design, the engine does not support it safely): **hitbox** (0.6 × 1.8), **eye height/camera**, **name-tag height**. The Golem is drawn 2.4 blocks tall but is hit like a normal player; the Jackalope's ears and antlers are not hittable.

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
| Size budget (< 25 MB, < 3,500 files): ~1 MB packaged, 3.9 MB unpacked, 142 files; every texture ≤ 256 KB memory | ✅ |

## Performance

* One 1-tick loop only does work while a channel (multi-stage ability) is active; a 4-tick loop drives HUD/temporary forms; a 20-tick loop runs passives (a handful of block probes per player, one entity query for jackalope senses); Blood Moon checks every 2 s; persistence every 5 s and on important changes.
* Ambient creature effects (spores, rune motes, embers, bubbles) are emitted **client-side by the attachables**, costing no server work or network packets; burst limits are small (2–4 particles per emission).
* Ability VFX use one `spawnParticle` call per visual event (the snare strand, shard stream and rune circle are single emitters driven by Molang variables).
* Geometry: Salamander 82 bones / 175 cubes, Golem 68 / 108, Jackalope 56 / 91; textures 256×256 or 256×128 RGBA.
* Mobile/iOS: no shader changes, no custom materials, only vanilla entity materials (`entity_emissive_alpha` for glowing runes/veins, `entity_alphatest` for leaves and fur fringes, `entity_alphablend` for the mirage).

## Known limitations (engine level)

* **First-person arms:** the attachable also binds in first person; a slightly larger first-person-only sleeve encloses the vanilla arm. If a future version stops drawing armour attachables in first person you will simply see your normal arm.
* Molang owner queries inside attachables (`q.target_x_rotation`, `q.hurt_time`, `q.modified_move_speed`, …) are used for the Golem's head look, flinches and gait details. If a platform does not resolve an owner query in attachable context, that detail is static; nothing breaks.
* `query.is_item_name_any('slot.armor.head', …)` (client-side) controls skin hiding; it is documented for all equipment slots.
* Input permission categories (`LateralMovement`) are used for rooting; they are restored on uproot, death, dimension change, and on the next join if the player disconnects while rooted.
