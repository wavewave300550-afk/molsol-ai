# The Abandoned Miracles — progress log

Status legend: **done** (built, validated, simulated) · **incomplete** · **blocked** · **unverified** (cannot be checked in this environment).

_Last updated: version 1.0.2 — fixes for what the first real play session showed (see below); those fixes are not yet confirmed in the game._

## Finished

### Stage A — technical foundation

| Item | Status | Evidence |
|---|---|---|
| Target versions verified (built against Bedrock 1.26.60; requires 1.26.10+, `@minecraft/server` 2.6.0, `@minecraft/server-ui` 2.0.0 — the lowest stable versions with everything used; no beta APIs, no experiments) | done | npm dist-tags, Mojang `bedrock-samples` `version.json`, typings |
| Asset toolkit (`tools/kit`): geometry + UV atlas, texture painters, software renderer, Molang DSL, animations, particles, audio synthesis, NBT/structures | done | used by all four bosses |
| Build pipeline (`tools/build.py`) → packs, `.mcaddon`, `.mcpack`, `.bbmodel` | done | `npm run build` |
| Encounter framework (`src/core`): manager, state machine, scheduler, targeting, arena, hazards, damage, locomotion, helpers, HUD, rewards, persistence | done | strict type-check; simulation |
| Static validator (`tools/validate.py`) + Mojang Creator Tools validator | done | 16,895 checks, 0 failed; Creator Tools 0 errors / 0 warnings |
| Headless simulation (`tools/sim`) | done | 210/210 scenarios; 840/840 over 4 seeds |
| Summoning Seals, Codex UI, `/abm:` commands, `/scriptevent` API, settings | done | simulation |

### Stage B — the four bosses

| Boss | Model / textures / rig | Animations | 7 attacks × 2 phases | Arena | Audio / VFX | Trophy | Simulated | In game |
|---|---|---|---|---|---|---|---|---|
| 001 Vesperra, The Ivory Succession | done (58 bones, 182 cubes) | done | done | done (45×14×45) | done | done | 51/51 | **unverified** |
| 002 Cantor XIII, The Walking Requiem | done (45 bones, 190 cubes) | done | done | done (51×16×51) | done | done | 53/53 | **unverified** |
| 003 Nomos, The Unmapped Sovereign | done (64 bones, 195 cubes) | done | done | done (47×15×47) | done | done | 53/53 | **unverified** |
| 004 Orison, The Witness of Tomorrow | done (55 bones, 159 cubes) | done | done | done (47×14×47) | done | done | 53/53 | **unverified** |

For each of the 28 attacks, in both phases, the simulation shows that it is chosen by the AI, executes, can hit a
stationary player, and can be avoided by a bot that walks, reacts after 0.3 s and knows only what was telegraphed.

### Stage C/D — integration, testing, packaging

| Item | Status |
|---|---|
| All four bosses in one add-on (`dist/The_Abandoned_Miracles.mcaddon`) | done |
| Test world with the four arenas (`dist/The_Abandoned_Miracles_Test_World.mcworld`) | done (built and statically validated; **unverified** in game) |
| `README.md`, `DESIGN_SPEC.md`, boss chapters in `docs/bosses/` | done |
| `TEST_REPORT.md` (generated from the validator and simulation results) | done |
| Visual previews for all four bosses (`docs/previews/`) — rendered offline, not screenshots | done |
| Editable Blockbench sources (`assets/blockbench/`) | done (generated; **unverified** — not opened in Blockbench) |

## After the first real play session

The project owner opened the add-on on an iOS device and sent the Content Log and a screenshot.

**What that session showed working:** the packs load; entity, geometry, render-controller, animation-controller,
particle, sound, item, recipe and structure files raise no errors; Vesperra's model and textures render; using a Seal
summons her; the summon line, the boss bar and the action-bar HUD appear.

**What it showed broken — fixed in 1.0.2, fixes not yet confirmed in the game:**

| Seen in the game | Cause | Fix |
|---|---|---|
| "can't find animation …" for every animation; bosses frozen | each boss's sound-only `footfalls` animation had an empty `bones` object; the schema needs at least one bone and the game then discards the whole animation file | the animation carries one no-op bone channel; the build refuses an animation without one; validator rule |
| "Function abmtw/tick failed to load"; no arenas, nothing handed out | score holder `#t` is a syntax error in `execute if score`, and one bad line unloads the function | plain name `abmtwclock`; validator rule for score holders |
| "Custom Command alias [summon] already in use" | the game also registers the bare alias, and `/summon` is its own | the command is now `/abm:wake`; the simulator rejects vanilla aliases |
| boss bar reads "Unknown" | a custom entity's bar is not named from the lang file | `minecraft:boss` carries the name |

None of these was caught by the project's validator, by Minecraft Creator Tools or by the simulation.

Before the log arrived, the build had also been audited against Mojang's vanilla sample packs and the Script API
documentation (1.0.1):

| Found | Fixed |
|---|---|
| Heir, Cocoon Anchor and Resonant Bell used the shared render controller, which names `Material.glass`, without declaring it | every client entity now declares all three layer materials; the validator requires it |
| Three helper controllers left their first state on `q.anim_time`, which is 0 outside an animation | `q.all_animations_finished`; the validator rejects animation-only queries in transitions |
| Seals, Codex and trophies only listened to the block-interaction *after* event, which does not fire for a plain floor | the *before* event (fires for any block) is handled too; the simulator now models both the way the game fires them |
| The packs asked for `@minecraft/server` 2.11.0 / 1.26.60 | lowered to the true minimum, 2.6.0 / 1.26.10; type-checked against those typings |
| Bosses and helpers had the `monster` family | removed: they no longer vanish on Peaceful |
| The test world was in Creative (bosses cannot hurt creative players) | Survival, keep-inventory, with the reference kit handed out on arrival |
| A failure in a per-tick path logged twenty lines a second | each distinct failure is logged once (then every 200th), shown once in chat, and an encounter that keeps failing folds away and refunds its Seal |
| Turning and walking relied on untested engine behaviour | each boss now checks that its yaw and position actually changed and switches itself to teleport-based turning / stepwise walking if not |
| `manifest.json` carried `product_type: addon` (a Marketplace flag) | removed |

These were not the errors that had been seen, but each is a real defect.

## Blocked

* **In-game runtime verification by the build itself.** The only way to run Bedrock here is Bedrock Dedicated Server through Minecraft
  Creator Tools, which requires accepting the Minecraft EULA. Only the project owner may do that
  (`npx -y @minecraft/creator-tools@0.21.0 eula`); it was not accepted on their behalf. No Minecraft client is
  available either, so rendering, animation, particles and audio could not be observed in any case.

## Unverified (needs a real game)

* That the packs load without Content Log errors on a real client.
* How models, emissive layers, animations, particle telegraphs and sounds actually look and sound.
* Script-driven boss movement on real physics (a teleport fallback is in the Codex settings).
* The test world's first-run arena construction.
* Difficulty, pacing and the 4–7 minute target with human players (simulated perfect-play time is 3 min 48 s – 4 min 04 s, a lower bound).
* Four-player balance (Bedrock hurt immunity makes several attackers add up less than linearly).
* Performance on phones, especially during the ultimates.

A checklist for the first real session is in `TEST_REPORT.md` §1.

## Incomplete / worth improving

* The simulation bot does not model Slowness or knockback, so slow-plus-hazard combinations (Nomos' wet ink,
  Orison's hourglasses) and recovery after being knocked back are argued from timings, not proven.
* Peak telegraph particle calls (about 75 in one tick for Nomos' and Cantor's ultimates) are unmeasured on devices.
