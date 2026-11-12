# Dragon Dominion — Minecraft Bedrock Add-on

**Status: Phase 0 (foundation).** This build contains the technical foundation only:
packs, manifests, the script runtime, the tier/encounter/ability frameworks, tooling and
validation. It contains **no creatures, bosses, models, attacks or tiers**. Those arrive
one approved design specification at a time.

| | |
|---|---|
| Target | Minecraft Bedrock **1.26.60** or newer (`min_engine_version` [1, 26, 60]); all platforms including iOS/iPadOS |
| Script API | `@minecraft/server` **2.11.0** (latest stable). No beta APIs and no Experiments toggles needed |
| Namespace | `dragon_dominion` (permanent) |
| Version | 0.1.0 |
| Download | [`dist/Dragon_Dominion_v0.1.0.mcaddon`](dist/Dragon_Dominion_v0.1.0.mcaddon), plus a separate `.mcpack` for each pack and `SHA256SUMS` |

## Install and smoke test

1. **Import:** open the `.mcaddon` on a device with Minecraft installed.
   * Windows and Android: open or double-tap the file; Minecraft imports both packs.
   * iOS/iPadOS: save the file to the Files app, then tap it (or use *Share → Minecraft*).
2. **Activate:** create or edit a world → *Behavior Packs* → activate **Dragon Dominion [BP]**.
   The resource pack **Dragon Dominion [RP]** is added automatically because the packs depend on each other.
   No experimental toggles are required.
3. **Check:** in the world, run `/dragon_dominion:status` (cheats not required). Expected output:
   ```
   Dragon Dominion v0.1.0
   tiers: 0, creatures: 0, loaded creature entities: 0
   ```
   With the Content Log enabled (*Settings → Creator*), the log shows
   `[Dragon Dominion] v0.1.0 loaded (...)` and no errors.

## Build from source

Requirements: Node.js ≥ 20.6 and Python ≥ 3.8 (standard library only).

```bash
cd dragon-dominion
npm ci                 # pinned: @minecraft/server 2.11.0, TypeScript 5.9.3
npm test               # typecheck → build → validate → validator tests → runtime tests
npm run package        # build + validate, then write dist/*.mcaddon, *.mcpack, SHA256SUMS
npm run validate:mct   # optional second opinion: Microsoft Creator Tools 0.21.0 (needs network)
npm run set-version -- 0.2.0   # bump the version everywhere (required before every release)
```

Packaging refuses to run if validation fails. Archives are deterministic: the same sources
produce byte-identical files, so `SHA256SUMS` identifies a build exactly.

## Project layout

```
dragon-dominion/
├─ behavior_packs/dragon_dominion/   BP source: manifest, icon, entities/, loot_tables/, spawn_rules/
├─ resource_packs/dragon_dominion/   RP source: manifest, icon, texts/, entity/, models/, textures/,
│                                    animations/, animation_controllers/, render_controllers/, particles/, sounds/
├─ src/                              TypeScript compiled into BP scripts/ (Script API 2.11.0)
│  ├─ main.ts, config.ts, commands.ts
│  ├─ core/        logging + error isolation, cooldowns
│  ├─ tiers/       tier contract, registry, tiers.ts (empty, owned by the design team)
│  ├─ creatures/   creature contract, registry, runtime (lifecycle + tick loop), index.ts (empty)
│  ├─ abilities/   ability contract + useAbility() (cooldown-gated)
│  └─ encounters/  multi-phase boss encounters, encounter HUD helpers
├─ design/creatures/                 approved specs, concept art, Blockbench sources (not shipped)
├─ tools/          build.py, validate.py, mct_validate.py, version.py, tests/
├─ docs/           ARCHITECTURE.md, ADDING_A_CREATURE.md, VALIDATION.md
└─ dist/           release archives (committed)
```

## Documentation

* [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): how the packs, runtime, tiers, abilities and encounters fit together.
* [docs/ADDING_A_CREATURE.md](docs/ADDING_A_CREATURE.md): the asset intake workflow from approved spec to release.
* [docs/VALIDATION.md](docs/VALIDATION.md): what has been verified, what still needs in-game testing, and the known limitations.
