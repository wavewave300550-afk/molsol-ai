# Adding a creature

Work starts only from an **approved design specification with approved multi-angle concept
art**. Don't use placeholder models or generic dragon assets, and don't invent abilities or tiers
that aren't in the spec. In the examples below, `<name>` is the creature's permanent snake_case
id (for example, the id in `dragon_dominion:<name>`).

## 1. Intake (not shipped)

```
design/creatures/<name>/
├─ spec.md            the approved specification (stats, tier, behavior, attacks, encounter)
├─ reference/         approved concept art (all angles), unedited
└─ source/            working files: <name>.bbmodel, layered textures (.psd/.kra), audio masters
```

`design/` is never copied into the packs, and the validator rejects source formats
(`.bbmodel`, `.psd`, `.ts`, ...) that end up inside a pack.

## 2. Export assets into the packs

All pack paths must be **lowercase ASCII with no spaces**. iOS and Android file systems are case
sensitive, so a texture referenced as `Dragon.png` but saved as `dragon.png` works on Windows and
fails on iOS. The validator compares paths by exact case.

| Asset | Location | Identifier / rules |
|---|---|---|
| Geometry (Blockbench → *Export Bedrock Geometry*) | `RP/models/entity/<name>/<name>.geo.json` | `geometry.dragon_dominion.<name>`; format 1.12.0+ |
| Textures (PNG) | `RP/textures/entity/<name>/*.png` | referenced without extension |
| Animations (Blockbench → *Export Animations*) | `RP/animations/<name>/*.animation.json` | `animation.dragon_dominion.<name>.<anim>` |
| Animation controllers | `RP/animation_controllers/<name>.animation_controllers.json` | `controller.animation.dragon_dominion.<name>.<ctl>` |
| Render controllers | `RP/render_controllers/<name>.render_controllers.json` | `controller.render.dragon_dominion.<name>` |
| Client entity | `RP/entity/<name>.entity.json` | `dragon_dominion:<name>` |
| Particles | `RP/particles/<name>/*.particle.json`, textures in `RP/textures/particle/<name>/` | `dragon_dominion:<name>_<effect>` |
| Sounds | `RP/sounds/<name>/*.ogg`; register in `RP/sounds/sound_definitions.json`; hook up entity events in `RP/sounds.json` | sound names `dragon_dominion.<name>.<event>` |
| Behavior entity | `BP/entities/<name>.json` | `dragon_dominion:<name>`; stats, size, AI goals, `minecraft:boss`, `minecraft:loot` |
| Loot table | `BP/loot_tables/entities/<name>.json` | |
| Spawn rules (only if the spec has natural spawning) | `BP/spawn_rules/<name>.json` | |
| Names | `RP/texts/en_US.lang` | `entity.dragon_dominion:<name>.name=...` and, if spawnable, `item.spawn_egg.entity.dragon_dominion:<name>.name=...` |

`sound_definitions.json`, `sounds.json` and `en_US.lang` are shared, single files: add one block
per creature, keep creatures in alphabetical order, and don't touch other creatures' entries.

**Format versions:** use current versions for new files. `npm run validate:mct` lists outdated
ones as recommendations. With Creator Tools 0.21.0 on 1.26.60, that means 1.26.60 for BP entity
and RP client entity files, 1.12.0 for spawn rules, and 1.10.0 for animations.

**Size vs tier vs look:** set size with `minecraft:scale` / `minecraft:collision_box` in the BP
entity, appearance in the RP and tier in the script definition. Never derive one from another.

## 3. Scripts (only for what JSON cannot do)

```
src/creatures/<name>/
├─ definition.ts      export const CREATURE: CreatureDefinition = { typeId, tier, ... }
├─ abilities.ts       AbilityDefinition[] (if the spec defines abilities)
└─ encounter.ts       EncounterDefinition (if the creature is a boss)
```

Register the creature in `src/creatures/index.ts` (one import and one array entry). Its `tier`
must already exist in `src/tiers/tiers.ts`; tiers come from the design team. Keep per-instance
state in a `WeakMap<ManagedCreature, State>` inside the creature's module. If phases drive client
animations, declare an int property `dragon_dominion:phase` (with `client_sync: true` and a range
covering every phase index) in the BP entity, and set `phaseProperty: "dragon_dominion:phase"`.

## 4. Validate and release

```bash
npm test                          # typecheck, build, static validation, tests
npm run validate:mct              # Microsoft Creator Tools second opinion
npm run set-version -- 0.2.0      # every release needs a higher version
npm run package                   # dist/*.mcaddon + SHA256SUMS
```

Then test in-game on Windows **and** iOS/Android (see [VALIDATION.md](VALIDATION.md)): the
entity renders with no missing-texture checkerboard, animations play, the name isn't shown as a
raw `entity.dragon_dominion:...` key, `/dragon_dominion:status` counts the creature, and the
Content Log shows no errors.

### Checklist

- [ ] Spec and concept art approved and stored in `design/creatures/<name>/`
- [ ] Every pack file is lowercase and namespaced; no source files in the packs
- [ ] BP entity, RP client entity, geometry, textures, animations, lang name
- [ ] Tier exists; creature registered in `src/creatures/index.ts`
- [ ] `npm test` and `npm run validate:mct` are clean
- [ ] Version bumped and dist/ rebuilt
- [ ] In-game check on at least one desktop and one mobile device
