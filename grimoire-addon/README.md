# Grimoire: Imperial Magic

A Minecraft **Bedrock Edition** add-on with three grimoires (**Pressure**, **Ice** and **Blood**), each holding
**15 spells** (45 in total), all available from the start.

**No mana.** There is no MP, gauge, ammunition, stamina, health or blood cost, charge counter or consumable. The only
limit is a **per-spell cooldown**, tracked separately for every player, grimoire and spell.

![The three grimoires](docs/images/grimoires.png)

| | |
|---|---|
| Add-on version | 1.0.0 |
| Minimum game version | **1.26.60** (`min_engine_version`) |
| Tested on | Bedrock Dedicated Server **1.26.63.1**, the latest stable release when it was built (preview 1.26.70.x is not targeted) |
| Script API | `@minecraft/server` **2.11.0** (stable). No beta modules, no experimental toggles |
| Platforms | Every Bedrock platform that runs 1.26.60+ (Windows, Android, iOS, consoles), with no platform-specific code. Only a server was available for testing (see [Testing](#testing)) |

## Install

1. Download `dist/Grimoire_Imperial_Magic.mcaddon`.
   * **Windows:** double-click it.
   * **Android / iOS:** open it with Minecraft. On iOS that means Files → Share → Minecraft.

   Minecraft imports both packs. The separate `_BP.mcpack` and `_RP.mcpack` files are there if you need them.
2. Create or edit a world. Under **Behavior Packs**, activate **Grimoire: Imperial Magic BP**. The resource pack is
   added automatically because the behavior pack depends on it. **No experiments are needed.**
3. Get the books:
   * **Craft them** at a crafting table. Each recipe unlocks once you hold a book.

     | Grimoire | Recipe |
     |---|---|
     | Pressure | book in the center, blaze powder left/right, breeze rods top/bottom, copper ingots in the corners |
     | Ice | book in the center, amethyst shards left/right, blue ice top/bottom, diamonds in the corners |
     | Blood | book in the center, ghast tears left/right, nether wart blocks top/bottom, redstone blocks in the corners |
   * **Or, as an operator with cheats on:** `/grimoire:getbook all` (or `pressure`, `ice`, `blood`).

## Controls

| Action | Keyboard & mouse | Touch | Controller |
|---|---|---|---|
| **Select the next spell** (01 → 15 → 01) | Press Sneak (Shift) once while holding a grimoire | Tap the sneak button | Press sneak |
| **Prepare** | Stop sneaking, then **hold** right mouse | Press and hold (use) | Hold the use trigger |
| **Cast** | **Release** right mouse | Lift your finger | Release the trigger |

* One crouch press advances **exactly one** spell. Holding crouch never keeps cycling. Every player keeps a separate
  selection for each of the three grimoires.
* **Nothing is cast when you press Use, and nothing is cast when preparation finishes.** The spell fires once, on
  release.
  * Releasing before the spell's minimum preparation time *fizzles*: nothing is cast and no cooldown starts.
  * Holding longer is always safe.
* Preparation is cancelled safely (no cast, no cooldown) when you:
  * crouch,
  * switch items or move the book,
  * die,
  * change dimension,
  * or disconnect.
* A cooldown starts **after** the spell activates. Switching items, dying, relogging or picking up another copy of the
  same grimoire does **not** reset it.
* The **I11 Wings of the Winter Seraph** cooldown starts when the flight ends. It is the only exception.
* The grimoire is never eaten, used up or damaged. It works with a full hunger bar, in Survival and in Creative.

**HUD** (the action bar, readable on phones). Line 1 shows the school, number and spell, e.g. `Ice Magic | 07/15 Chains of Niflheim`. Line 2 shows one of:

* `READY`
* `Cooldown 12.4s / 30s`
* a preparation bar
* `Release to cast`
* `Active (cooldown starts when it ends)`

`/grimoire:guide` lists the 15 spells of the book you are holding.

## Spells and cooldowns

<!-- COOLDOWNS -->
| # | Pressure (orange) | CD | # | Ice (sapphire) | CD | # | Blood (crimson) | CD |
|---|---|---|---|---|---|---|---|---|
| P01 | Pressure Lance | 6 s | I01 | Glacial Sovereign's Lance | 8 s | B01 | Crimson Stiletto Rain | 7 s |
| P02 | Atlas Piston | 18 s | I02 | Boreal Dragon's Roar | 20 s | B02 | Guillotine of the Red Court | 16 s |
| P03 | Isobaric Severance | 10 s | I03 | Winter's Guillotine | 14 s | B03 | Sanguine Leviathan | 24 s |
| P04 | Cataclysm Salvo | 22 s | I04 | Thousandfold Crystal Rain | 25 s | B04 | Crown of a Thousand Blades | 26 s |
| P05 | Aegis of Isobars | 25 s | I05 | Lotus of the Eternal Frost | 28 s | B05 | Aegis of the Scarlet Rose | 25 s |
| P06 | Counterpressure Mantle | 22 s | I06 | Mirror of the Frozen Throne | 32 s | B06 | Royal Reprisal | 28 s |
| P07 | Titan's Vise | 30 s | I07 | Chains of Niflheim | 30 s | B07 | Veinbound Marionette | 30 s |
| P08 | Atmospheric Labyrinth | 35 s | I08 | Labyrinth of the Pale Moon | 40 s | B08 | Garden of the Crimson Thorns | 35 s |
| P09 | Resonance Cage | 28 s | I09 | Whiteout Dominion | 45 s | B09 | Hematic Maelstrom | 40 s |
| P10 | Pressure Step | 5 s | I10 | Frost Mirror Traverse | 8 s | B10 | Bloodstep: Shattered Ruby | 7 s |
| P11 | Skyline Pressure Rail | 14 s | I11 | Wings of the Winter Seraph | 20 s* | B11 | Arterial Current | 18 s |
| P12 | Barometric Omniscience | 25 s | I12 | Imperial Frost Legion | 60 s | B12 | Crimson Familiar: The Royal Stag | 55 s |
| P13 | Equilibrium Theft | 35 s | I13 | Hourglass of Still Winter | 50 s | B13 | Sovereign's Pulse | 45 s |
| P14 | Isobaric Citadel | 75 s | I14 | Grand Magic: Citadel of the Everlasting Winter | 90 s | B14 | Grand Magic: Scarlet Sea of Lament | 90 s |
| P15 | Imperial Edict: Thousand Atmospheres | 180 s | I15 | Imperial Edict: The Last Winter | 180 s | B15 | Imperial Edict: Heart of the Crimson Moon | 180 s |

\* I11's cooldown starts when the flight ends (the only exception).
<!-- /COOLDOWNS -->

[docs/SPELLS.md](docs/SPELLS.md) is the full reference: what each spell does, its preparation time and its tuning
values (damage, radius, duration).

Constructs and summons are offline renders of the shipped models. They are **not** in-game screenshots.

* [Pressure constructs](docs/images/constructs_pressure.png)
* [Ice constructs](docs/images/constructs_ice.png)
* [Blood constructs](docs/images/constructs_blood.png)
* [Summons: the Frost Legion and the Royal Stag](docs/images/summons.png)

## Rules for operators

`/grimoire:config <rule> <value>` (or `/scriptevent grimoire:config <rule> <value>`). Rules are saved in the world.

| Rule | Default | Effect |
|---|---|---|
| `pvp` | `false` | Spells may damage other players and other players' summons |
| `friendlyFire` | `false` | With PvP on, players sharing a `grimoire_team:<name>` tag are still allies unless this is on |
| `harmPassiveMobs` | `false` | Area spells also hit passive animals |
| `temporaryBlocks` | `true` | Labyrinths and citadels may raise temporary walls. Walls are placed only into air and always removed |
| `damagePvE` | `1` | Multiplier for spell damage against mobs (0–10) |
| `damagePvP` | `0.5` | Multiplier for spell damage against players, used only when PvP is on (0–10) |
| `cameraEffects` | `true` | Camera shake and screen fades near big spells |

`/grimoire:resetcooldowns` clears your own cooldowns (operators; a testing aid).

## Who gets hit

* Spells damage **hostile mobs** and **anyone who attacked you or your summons**.
* They never damage:
  * you,
  * your summons or your allies' summons,
  * villagers, wandering traders, iron and snow golems, allays,
  * tamed or named mobs.
* Other players can be hit only when `pvp` is on. Passive animals can be hit only when `harmPassiveMobs` is on.

Each construct, ward, bind, temporary block and summon belongs to the cast that created it. It is removed when:

* the spell ends,
* the caster disconnects,
* or the caster changes dimension.

If the world was closed mid-spell, leftovers are swept the next time their chunk loads. Temporary blocks also carry a
self-check that removes them if they are ever orphaned.

## Building from source

Requirements:

* Node 20+
* Python 3.10+ with `numpy` and `Pillow`
* `ffmpeg` with libvorbis (to synthesize the sounds)

```sh
npm ci
npm run typecheck                  # tsc --noEmit
python3 tools/build.py             # packs/ + dist/*.mcaddon (all models, textures, animations, particles, sounds)
python3 tools/validate.py          # static cross-reference checks (see docs/TESTING.md)
python3 tools/preview.py books     # offline renders: books | fx [prefix] | mobs  (needs Chromium + Playwright)
python3 tests/run_bds.py --bds <bedrock_server dir> controls pressure ice blood robustness cleanup
python3 tools/docs.py docs/test-evidence/final_run.json   # regenerate docs/SPELLS.md, docs/TESTING.md
```

Everything in the packs is generated by `tools/gen/`:

* geometry and textures are painted in code,
* the 67 sounds are synthesized,
* the particle sprites are drawn procedurally.

No third-party art or audio is included. three.js and Playwright are used only by the offline preview tool.

| Path | Contents |
|---|---|
| `src/core/` | Controls state machine, cooldown state, HUD, damage bus, wards, binds, temporary blocks, FX constructs, routines scheduler, diagnostics |
| `src/spells/{pressure,ice,blood}/` | Spell definitions (`index.ts`) and implementations (`spells.ts`) |
| `tools/gen/` | Model kit, texture painters, the three books, 75 construct models, 4 mobs, particles, sounds, fogs, player poses |
| `tests/` | BDS runner, world generator, development-only harness pack with the test suites |
| `packs/`, `dist/` | Built behavior and resource packs, `.mcaddon` and `.mcpack` files |
| `docs/` | Spell reference, testing matrix, test evidence, offline renders |

## How it works (key decisions)

* **Hold-to-prepare without eating.** The items use `minecraft:use_modifiers` with a one-hour use duration.
  * This makes them usable (Use can be held), but not food, not throwable and not consumable.
  * The scripts react to the item-use events this way:

    | Event | Effect |
    |---|---|
    | `itemStartUse` | Start preparing (ignored while sneaking) |
    | `itemReleaseUse` | Cast |
    | `itemStopUse` without a release (slot switch) | Cancel |
    | `itemCompleteUse` | Cancel; it never auto-casts |
  * All four were measured on the real server.
* **Cooldowns live in the script, not in item cooldown categories.**
  * They are stored per player in a dynamic property, so they survive death, relogging, item switches and duplicate
    books.
  * I11's timer starts from the end of its routine.
* **Spell behaviour runs as coroutine routines** owned by the cast.
  * Every sub-effect is registered with the cast and torn down by one cleanup path, whichever way the spell ends:
    expiry, disconnect, dimension change or world shutdown.
* **Damage** goes through one damage bus that respects Bedrock's hurt cooldown (hits in the same 10 ticks are merged).
  * Spells deal `magic` damage.
  * Counterattacks use `thorns` damage, so two reflective wards cannot bounce damage forever.
* **Constructs** are invulnerable, non-colliding entities. Synced properties (phase, yaw, pitch, size, length,
  variant) drive their animation controllers.
  * Each one has a self-despawn timer.
  * Each one carries a session id so that leftovers are removable.

## Testing

[docs/TESTING.md](docs/TESTING.md) has the full per-spell matrix and every check. The raw harness output is in
`docs/test-evidence/`.

* **Verified in-engine (automated):** all of the following were run on Bedrock Dedicated Server 1.26.63.1 by
  simulated players using the real inputs (crouch, hold Use, release, switch slots):
  * the 45 spells,
  * the controls and cancellation rules,
  * cooldown independence,
  * PvP and team rules,
  * two simultaneous casters,
  * disconnects and dimension changes mid-spell,
  * temporary blocks,
  * cleanup.
* **Not verified in a game client:** no Bedrock client was available, so everything the client draws or plays has only
  passed static validation and offline renders. That covers:
  * models in first and third person,
  * animations, particles, sounds, fog and camera effects,
  * the feel of knockback-driven movement.
* **No performance figures are claimed.** Frame rate was not measured on any device.

## Version research

The target versions were checked when the add-on was built:

* **Game:** the official Bedrock Dedicated Server download listing showed **1.26.63.1** as the latest stable release
  (the preview channel was at 1.26.70.24).
* **Script API:** the npm registry showed `@minecraft/server` **2.11.0** as the latest stable script module (newer
  versions were beta only) and `@minecraft/vanilla-data` at 1.26.60.
* **File formats:** item, block and recipe files use format **1.26.60**; behavior entities use **1.26.30**. These
  follow Mojang's `bedrock-samples` repository at 1.26.60.5.
* **Engine behavior:** the item-use event order, sneaking, knockback and the hurt cooldown were measured on the server
  itself instead of being assumed.

## Known issues and limitations

* **Client presentation is unverified.** This covers:
  * the book's first-person and third-person placement (tuned from vanilla attachables and offline renders),
  * every animation, particle, sound and fog,
  * how the HUD fits on small screens.

  These need a pass on real devices.
* **The engine ignores a new Use press for about 0.35 s after a release** (measured on BDS: about 7 ticks). If you
  release and immediately press again, the second press may not start preparing until that window has passed.
* **P11, I11 and B11 movement uses knockback impulses.** Simulated players ignore knockback, so the flight and riding
  feel, and how it behaves under network latency, is untested.
* **Summoned knights and the stag use vanilla mob AI** (melee, follow owner). Pathing in cluttered terrain is
  vanilla-quality.
* **Heavy constructs exist.** The largest are 840, 600 and 501 cubes (the Pressure layered field, the Ice crystal sword
  rain and the Pressure dome). They appear in limited numbers and for limited durations, but no device benchmark was
  done.
* **The test worlds were flat.** Line of sight, ground snapping and teleport safety were checked on flat ground with
  walls. Caves, water and steep terrain were not covered by automated tests.
* `/grimoire:getbook`, `/grimoire:config` and `/grimoire:resetcooldowns` need operator permission and cheats.
  Survival players without cheats use the crafting recipes.
