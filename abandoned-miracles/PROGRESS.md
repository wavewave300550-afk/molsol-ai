# The Abandoned Miracles — progress log

Status legend: **done** (built, validated, simulated) · **in progress** · **not started** · **unverified** (cannot be checked in this environment).

_Last updated: foundation and Boss 001 complete; Bosses 002–004 in production._

## Stage A — technical foundation: done

| Item | Status | Evidence |
|---|---|---|
| Target versions verified (Bedrock 1.26.60, `@minecraft/server` 2.11.0, `@minecraft/server-ui` 2.3.0, no beta APIs) | done | npm dist-tags, Mojang `bedrock-samples` `version.json`, typings |
| Asset toolkit (`tools/kit`): geometry + UV atlas, texture painters, software renderer, Molang DSL, animations, particles, audio synthesis, NBT/structures | done | used by Boss 001 |
| Build pipeline (`tools/build.py`) → packs + `.mcaddon` | done | `npm run build` |
| Encounter framework (`src/core`): manager, state machine, scheduler, targeting, arena, hazards, damage, locomotion, helpers, HUD, rewards, persistence | done | type-checks against stable typings; simulation |
| Static validator (`tools/validate.py`) + Mojang Creator Tools validator | done | 3,943 checks, 0 failures; Creator Tools 0 errors / 0 warnings |
| Headless simulation (`tools/sim`) | done | 51/51 scenarios for Boss 001 |
| Summoning seals, Codex UI, commands, settings | done | simulation |

## Stage B — bosses

| Boss | Model / textures | Animations | 7 attacks ×2 phases | Arena | Audio / VFX | Simulated | In game |
|---|---|---|---|---|---|---|---|
| 001 Vesperra | done | done | done | done | done | 51/51 | unverified |
| 002 Cantor XIII | not started | not started | not started | not started | not started | – | unverified |
| 003 Nomos | not started | not started | not started | not started | not started | – | unverified |
| 004 Orison | not started | not started | not started | not started | not started | – | unverified |

## Stage C/D — integration, testing, packaging

| Item | Status |
|---|---|
| All four bosses in one add-on | in progress (1/4) |
| Test world `.mcworld` | not started |
| README / DESIGN_SPEC / TEST_REPORT | not started |
| Visual previews | Boss 001 done (`docs/previews/vesperra`) |

## Blocked / unverified

* **In-game runtime verification is not possible here.** Running Bedrock Dedicated Server through
  Minecraft Creator Tools requires accepting the Minecraft EULA, which only the project owner may do
  (`npx -y @minecraft/creator-tools@0.21.0 eula`). No Minecraft client is available either. Everything
  marked *unverified* above has been validated statically and in simulation only.
