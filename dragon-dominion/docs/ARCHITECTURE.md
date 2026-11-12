# Architecture

## Principles

* **Bedrock-native first.** Anything the game supports in JSON stays in JSON: entity stats, size,
  movement and vanilla AI goals, the boss health bar (`minecraft:boss`), loot tables, spawn rules,
  models, animations, sounds and particles. Scripts only add what JSON cannot express.
* **Shared infrastructure, isolated creatures.** `src/core`, `src/tiers`, `src/abilities` and
  `src/encounters` know nothing about any specific creature. Each creature lives in its own
  folders and depends on the shared layer, never on another creature.
* **No speculative systems.** Frameworks exist only for the requirements listed in the Phase 0
  brief. Everything else waits for an approved specification.

## Packs, identity and versions

| | Behavior pack | Resource pack |
|---|---|---|
| Name | Dragon Dominion [BP] | Dragon Dominion [RP] |
| Header UUID | `207ddd61-776d-4c01-89be-5babddf6d88b` | `87494967-a706-43dc-91fc-2704ce550f10` |
| Modules | data `a6d0d735-…7988`, script `5bfabe09-…d0d3` | resources `50560be4-…e5c8` |

* **UUIDs are permanent.** They are listed in `tools/validate.py` (`PERMANENT_UUIDS`), so a
  regenerated UUID fails validation. Changing one would orphan the packs in existing worlds.
* The packs depend on each other (uuid + version), so activating either one brings in the other.
* Manifest `format_version` 2, the format used by Microsoft's current Script API samples.
  Format 3 (all versions written as strings) is only needed for pack settings; switching later is
  a mechanical change and leaves the UUIDs as they are.
* **Version:** one value, set with `npm run set-version -- X.Y.Z`. It updates package.json, the
  lockfile, `src/config.ts` and both manifests, and the validator rejects any drift between them.
  Bedrock only replaces an installed pack when its version increases, so bump before every
  release.
* **Script API:** the manifest's `@minecraft/server` version must equal the installed typings
  (validated), so the typecheck always matches the runtime. Beta versions are rejected.
* **Namespace `dragon_dominion`**, enforced by the validator: entity/item/block/particle ids
  `dragon_dominion:<name>`, `geometry.dragon_dominion.*`, `animation.dragon_dominion.*`,
  `controller.animation.dragon_dominion.*`, `controller.render.dragon_dominion.*`, sound names
  `dragon_dominion.*`, entity properties `dragon_dominion:*`. Vanilla entities are never overridden.

## Script runtime

```
main.ts ─┬─ TierRegistry(TIERS)                    validates tiers.ts
         ├─ CreatureRegistry(CREATURES, tiers)     validates every creature definition
         ├─ CreatureRuntime.start()                only when there are no configuration problems
         └─ /dragon_dominion:status                read-only diagnostic command
```

If any tier or creature definition is invalid, every problem is logged and the creature runtime
is not started. With zero creatures registered (Phase 0), the runtime subscribes to nothing and
runs no tick loop, so it costs nothing.

**CreatureRuntime** (`src/creatures/runtime.ts`) tracks every loaded entity of a registered type
and gives each one a stable `ManagedCreature` handle (`entity`, `definition`, `tier`,
`cooldowns`, `encounter`). Lifecycle:

| World event | Creature hook | Notes |
|---|---|---|
| new entity spawned | `onSpawn(creature, cause)` then encounter start | not called for entities loaded from disk |
| entity loaded from disk / world load | none (encounter resumes its saved phase) | world-load scan picks up entities that loaded before scripts |
| every `tickInterval` ticks | encounter tick, then `onTick` | creatures are spread across ticks |
| hurt | `onHurt` | |
| BP entity event fired | `onEntityEvent(creature, eventId)` | bridge from JSON (components, timers, animation controllers) to scripts |
| death | `onDeath`, then encounter `onDefeat` | ticking stops at death |
| removed / unloaded | handle dropped | |

Every hook runs through `guarded()`, so one creature's errors are logged (at most 3 times per
source) and never stop other creatures. At world load, the runtime also checks that every
registered `typeId` exists in the behavior pack.

Transient per-creature state belongs in the creature's own module as a
`WeakMap<ManagedCreature, State>`, which is released automatically when the entity unloads.

## Tiers (`src/tiers`)

`TierDefinition` = `{ id, rank, nameKey }`. Tiers are ordered by `rank` (higher = more powerful);
`TierRegistry` provides `get`, `all()` (rank order) and `compare`. `src/tiers/tiers.ts` is
**empty on purpose**: tier names, count, ranks and balancing belong to the design team.

* Every creature definition must name a registered tier; an unknown tier is a configuration error.
* **Tier, size and appearance are independent.** Size lives in the BP entity
  (`minecraft:scale`, `minecraft:collision_box`), appearance in the RP, and tier in the script
  definition. None of them derives from another.
* Creature stats stay creature-specific (BP components and the creature's own module). When the
  design team defines tier-wide attributes, add them as typed fields on `TierDefinition`.

## Abilities (`src/abilities`)

`AbilityDefinition` = `{ id, cooldownTicks, canUse?, execute }`, listed on the creature
definition. `useAbility(creature, id)` returns `used | on_cooldown | blocked | unknown | failed`;
the cooldown starts before `execute`, so a failing ability cannot retry every tick. When to use
which ability on which target is the creature's own AI (`onTick`, `onEntityEvent`, phase hooks).

## Encounters (`src/encounters`)

`EncounterDefinition` = ordered `phases`, `participantRadius`, optional `phaseProperty`, and
`onStart` / `onDefeat` hooks. Each phase has optional `onEnter`, `onTick`, `onExit` and
`next()` (return a phase id to transition).

* The current phase is saved in the entity dynamic property `dragon_dominion:encounter_phase`,
  so a boss resumes its phase after a chunk reload or a world restart.
* `phaseProperty` mirrors the phase index into an integer entity property (declared in the BP
  entity with `client_sync: true`), so animations and render controllers can use
  `query.property('dragon_dominion:phase')`.
* **Boss health UI** is the vanilla `minecraft:boss` component. For encounter messages, use
  `showTitle` / `showActionBar` (`encounters/hud.ts`) with `encounter.participants()`.
* **Rewards:** `onDefeat(creature, encounter, event)` receives the participants, plus the BP loot
  table for drops.

## Summoning, spawning and loot

These are all Bedrock-native and validated by the build: spawn rules in `spawn_rules/`, loot in
`loot_tables/` (referenced by `minecraft:loot`), and summoning through `dimension.spawnEntity` or
entity events. A spawned entity goes through the same `onSpawn` → encounter start path whatever
created it. Summoning items or altars will be built once a design specifies them.
