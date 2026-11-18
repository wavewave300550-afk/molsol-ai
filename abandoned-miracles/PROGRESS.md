# The Abandoned Miracles — progress log

Status legend: **done** (built, validated, simulated) · **incomplete** · **blocked** · **unverified** (cannot be checked in this environment).

_Last updated: all four bosses integrated into one add-on; static validation and simulation pass; in-game verification blocked._

## Finished

### Stage A — technical foundation

| Item | Status | Evidence |
|---|---|---|
| Target versions verified (Bedrock 1.26.60, `@minecraft/server` 2.11.0, `@minecraft/server-ui` 2.3.0, no beta APIs, no experiments) | done | npm dist-tags, Mojang `bedrock-samples` `version.json`, typings |
| Asset toolkit (`tools/kit`): geometry + UV atlas, texture painters, software renderer, Molang DSL, animations, particles, audio synthesis, NBT/structures | done | used by all four bosses |
| Build pipeline (`tools/build.py`) → packs, `.mcaddon`, `.mcpack`, `.bbmodel` | done | `npm run build` |
| Encounter framework (`src/core`): manager, state machine, scheduler, targeting, arena, hazards, damage, locomotion, helpers, HUD, rewards, persistence | done | strict type-check; simulation |
| Static validator (`tools/validate.py`) + Mojang Creator Tools validator | done | 13,823 checks, 0 failed; Creator Tools 0 errors / 0 warnings |
| Headless simulation (`tools/sim`) | done | 210/210 scenarios; 1,680/1,680 over 8 seeds |
| Summoning Seals, Codex UI, `/abm:` commands, `/scriptevent` API, settings | done | simulation |

### Stage B — the four bosses

| Boss | Model / textures / rig | Animations | 7 attacks × 2 phases | Arena | Audio / VFX | Trophy | Simulated | In game |
|---|---|---|---|---|---|---|---|---|
| 001 Vesperra, The Ivory Succession | done (58 bones, 182 cubes) | done | done | done (45×14×45) | done | done | 51/51 | **unverified** |
| 002 Cantor XIII, The Walking Requiem | done (45 bones, 190 cubes) | done | done | done (51×16×51) | done | done | 53/53 | **unverified** |
| 003 Nomos, The Unmapped Sovereign | done (64 bones, 195 cubes) | done | done | done (47×15×47) | done | done | 53/53 | **unverified** |
| 004 Orison, The Witness of Tomorrow | done (51 bones, 132 cubes) | done | done | done (47×14×47) | done | done | 53/53 | **unverified** |

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

## Blocked

* **In-game runtime verification.** The only way to run Bedrock here is Bedrock Dedicated Server through Minecraft
  Creator Tools, which requires accepting the Minecraft EULA. Only the project owner may do that
  (`npx -y @minecraft/creator-tools@0.21.0 eula`); it was not accepted on their behalf. No Minecraft client is
  available either, so rendering, animation, particles and audio could not be observed in any case.

## Unverified (needs a real game)

* That the packs load without Content Log errors on a real 1.26.60 client.
* How models, emissive layers, animations, particle telegraphs and sounds actually look and sound.
* Script-driven boss movement on real physics (a teleport fallback is in the Codex settings).
* The test world's first-run arena construction.
* Difficulty, pacing and the 4–7 minute target with human players (simulated perfect-play time is 3 min 48 s – 4 min 04 s, a lower bound).
* Four-player balance (Bedrock hurt immunity makes several attackers add up less than linearly).
* Performance on phones, especially during the ultimates.

A checklist for the first real session is in `TEST_REPORT.md` §1.

## Incomplete / worth improving

* Orison's Phase II silhouette differs from Phase I less than the other bosses' do.
* The simulation bot does not model Slowness or knockback, so slow-plus-hazard combinations (Nomos' wet ink,
  Orison's hourglasses) and recovery after being knocked back are argued from timings, not proven.
* Peak telegraph particle calls (about 75 in one tick for Nomos' and Cantor's ultimates) are unmeasured on devices.
