# Validation results (Phase 0, v0.1.0)

## Verified (automated, reproducible with `npm test` and `npm run validate:mct`)

| Check | Result |
|---|---|
| TypeScript `strict` typecheck against the official `@minecraft/server` 2.11.0 typings (TypeScript 5.9.3) | 0 errors |
| Static validation of the built packs (`tools/validate.py`): JSON syntax, manifests, permanent UUIDs, BP↔RP dependencies, Script API version = typings, version sync, file naming, namespace, asset cross-references, script imports | 200 checks, 0 errors, 0 warnings |
| Validator self-tests: a complete synthetic entity covering geometry, texture, animation, controllers, particle, sound, loot, spawn rule and lang passes; 26 deliberate defects are each detected; the version bump keeps the project valid | 29/29 pass |
| Runtime tests: compiled scripts run against a strict `@minecraft/server` mock (world APIs throw during early execution, as in the engine) covering startup, status command, registries, lifecycle, tick interval, reload/resume, phase transitions and persistence, client phase property, defeat participants, error isolation and rate limiting, ability cooldowns | 12/12 pass; two deliberate regressions were each caught by the intended test |
| Microsoft Minecraft Creator Tools 0.21.0 on `build/` (54 rule sets, 120 results) | 0 errors, 0 warnings, 0 recommendations |
| Creator Tools on the contents extracted from the packaged `.mcaddon` | 0 errors, 0 warnings, 0 recommendations |
| Creator Tools on the synthetic entity fixture | 0 errors, 0 warnings; 4 recommendations, all about newer `format_version`s (reflected in ADDING_A_CREATURE.md) |
| Packaging: zip integrity (CRC), `.mcaddon` = two pack folders, each `.mcpack` has `manifest.json` at its root, no dotfiles or sources included | OK |
| Reproducibility: two clean builds and a fresh `npm ci` rebuild give identical SHA-256 for all three archives | OK |

**How the targets were confirmed.** Microsoft Learn (learn.microsoft.com) is not reachable from
the build environment, so compatibility was checked against official Microsoft/Mojang packages
instead:

* npm `latest` tags: `@minecraft/server` 2.11.0 and `@minecraft/vanilla-data` 1.26.60; 1.26.70 is
  still preview/RC.
* Mojang's `@minecraft/bedrock-schemas` 1.26.60.
* The manifest conventions in Microsoft's Script API samples bundled with Creator Tools 0.21.0
  (`format_version` 2, `@minecraft/server` 2.x).
* Creator Tools' version rules, which accept `min_engine_version` [1, 26, 60] and Script API
  2.11.0 without "outdated" findings.

## Requires in-game testing

None of the following can be proven without running Minecraft:

1. **Import** of the `.mcaddon` on Windows, Android and **iOS/iPadOS**: both packs appear and
   there is no import error.
2. **Activation** on 1.26.60+: activating the BP pulls in the RP, and no Experiments toggle is
   requested.
3. **Script load:** the Content Log shows `[Dragon Dominion] v0.1.0 loaded (...)` and no errors.
4. **`/dragon_dominion:status`** registers (namespace with underscore) and prints the expected
   text without cheats.
5. **Real engine event order** (spawn vs load, world-load scan, death/removal) matches the mock.
   This must be re-checked with the first real creature.
6. **Format versions** recommended by Creator Tools for new asset files, checked with the first
   creature.
7. **Performance on mobile** (iOS/Android) once creatures exist.

A Bedrock Dedicated Server session through Creator Tools could automate items 3–5, but it
requires accepting the Minecraft EULA. Only the project owner can do that, by running
`npx -y @minecraft/creator-tools@0.21.0 eula`; it was not accepted on their behalf.

## Known limitations

* **Pack icon:** a neutral geometric placeholder (no creature imagery). Replace it with approved
  art (square PNG).
* **Cooldowns** are in memory and reset when an entity unloads. Encounter phases are persisted.
* **Validator scope** is the entity asset pipeline. Server-side BP animations/controllers are
  rejected until the validator is extended. Items and blocks are checked for namespace only.
  Vanilla references (materials, `animation.common.*`, vanilla items in loot tables) are not
  checked.
* **Manifest format 2:** moving to format 3 (string versions, required for pack settings) is a
  mechanical change if a future design needs it.
* `npm run validate:mct` needs network access to download Creator Tools on first use.
