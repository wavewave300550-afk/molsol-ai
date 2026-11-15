# THE ANATOMY OF A WORLD — Minecraft Bedrock Add-on

Experimental colossal bosses whose **bodies are the battlefield**. Each specimen lives in its own
pocket dimension, is built from real blocks you climb and fight on, and is animated by multipart
entities, a deformable terrain system and a scripted encounter director.

**Install:** [`dist/The_Anatomy_of_a_World.mcaddon`](dist/The_Anatomy_of_a_World.mcaddon)
(separate `_BP.mcpack` / `_RP.mcpack` are in the same folder).

| | |
|---|---|
| Game version | Bedrock **26.60** (engine `1.26.60`) or newer |
| Script API | `@minecraft/server` **2.11.0**, `@minecraft/server-ui` **2.3.0** (latest stable) |
| Experiments | **none required** — stable APIs only; the arena dimension is a JSON dimension (format 1.26.50) |
| Status | **Specimen 001 — The Migrating Mountain: complete.** Specimens 002–004 are waiting for their concept sheets. |

> **สรุปภาษาไทย:** แอดออนบอสยักษ์ที่ "ร่างกายของบอสคือสนามรบ" บอสตัวแรก **The Migrating Mountain (เทือกเขาอพยพ)** สร้างเสร็จสมบูรณ์แล้ว
> มี 2 เฟส (The Sleeping Continent / The Unfolded World) และ 7 ความสามารถตามแผ่นคอนเซปต์ เรียกบอสได้ด้วย *Restless Lodestone*
> (คราฟต์จากทัฟฟ์ เศษอะเมทิสต์ เข็มทิศ และหินมอส) หรือจาก *Anatomical Atlas* ที่ได้ตอนเข้าโลกครั้งแรก
> เฟส 1 ต้องทำลาย **ผลึกสีม่วง 3 จุด (Resonance Node)**: บนยอดเขา · ในถ้ำอวัยวะ (อุโมงค์ด้านหน้า) · ห้อยอยู่ใต้ตัวภูเขา (ลงบันไดวนจากถ้ำ)
> มีเสาแสงสีม่วง เครื่องหมาย ★ บนแถบระบุตำแหน่ง และแถบข้อความบอกระยะ กดปุ่ม **Language** ใน Atlas เพื่อให้คำแนะนำระหว่างสู้เป็นภาษาไทย
> ชื่อภาษาไทยของไอเท็มและเอนทิตีอยู่ใน `docs/th_TH.reference.lang` (Bedrock ไม่โหลดไฟล์ภาษาไทยจากแพ็ก)

![The Migrating Mountain](docs/images/boss001_hero.png)

---

## Playing

1. Import the `.mcaddon`, then enable **THE ANATOMY OF A WORLD** behaviour pack on a world (the resource pack follows).
2. On first join you receive the **Anatomical Atlas** (lost it? `/anatomy:atlas`, or craft *book + amethyst shard*).
   The Atlas is the in-game codex: anatomy, abilities, phase flow and your records for every specimen.
3. Craft a **Restless Lodestone** and use it (or press *Begin the encounter* in the Atlas). You and every player within
   32 blocks are drawn into the Migration Path dimension.

```
Restless Lodestone        T = tuff   A = amethyst shard
   T A T                  C = compass
   A C A                  M = mossy cobblestone
   T M T
```

The Atlas' **Language** button switches the in-fight guidance (HUD, titles, briefings) between English and ภาษาไทย.
During a fight the Atlas offers **Leave the encounter** / **Join the encounter**. Players who die are pulled back in a
moment after respawning. If nobody is left fighting for 30 s the mountain wanders on and the arena is cleaned up.
Your world is never modified — the whole fight happens in its own dimension and is erased afterwards; anything left on
the ground is carried home with you.

### Testing / spawning (cheats on, operator)

| Command | Effect |
|---|---|
| `/anatomy:boss start` | start Specimen 001 for you and nearby players (no lodestone needed) |
| `/anatomy:boss skip` | destroy the remaining Resonance Nodes → The Great Unfolding → Phase 2 |
| `/anatomy:ability <id>` | force an ability: `continental_fold`, `lithic_peristalsis`, `geological_shedding`, `resonance_network`, `inverted_strata`, `mantle_contraction`, `great_unfolding` |
| `/anatomy:boss kill` · `stop` · `status` · `join` · `leave` | finish the fight · abort and clean up · print state (incl. which parts are loaded/spawned, the remaining nodes' coordinates and chunk coverage) · join · leave |
| `/scriptevent anatomy:start` (also `stop`, `skip`, `kill`, `status`, `ability <id>`) | same actions without custom commands |

The Atlas also has a **Test tools** page for operators and creative players.

---

## Specimen 001 — THE MIGRATING MOUNTAIN

*The Mountain That Never Belonged to the Earth* — a geological organism ~78 blocks tall and 116 long, its back a forest
of stratified cliffs, snow crags and waterfalls, walking on fourteen Anchorage Roots across a sea of clouds.

| Concept anatomy | In the add-on |
|---|---|
| Mountain Shell / Living Strata | ~200 000 real blocks: terraced grey strata cliffs, forest ledges, snow spires, two waterfalls (one falls into the cloud sea) |
| Dorsal Biome | 110 trees, flowers, moss; a pilgrim path spirals from the arrival shelf to the summit crag |
| Mineral Circulation | glowing shroomlight / magma veins through the musculature; animated vein strips on every entity |
| Organ Cavern | a ribbed cavern of red musculature with stalactites and glow-berry vines, reached by the front tunnel |
| Lithic Heart | animated entity: amethyst core, 8-plate iris, gyroscope rings and a 12-spoke wheel; carries the boss bar |
| Mantle / Lithic Musculature | the underside arches and the underbelly gallery (spiral shaft down from the cavern) |
| Anchorage Roots | 14 animated root-leg entities with a peristaltic walking gait, stomps, flinches, splay and collapse |

![Underbelly](docs/images/boss001_underbelly.png)
![Cutaway: Organ Cavern, heart cradle, shaft and underbelly gallery](docs/images/boss001_cutaway.png)

### Phase 1 — The Sleeping Continent
Climb and explore the body to find and destroy the three **Resonance Nodes** (the purple crystals) — on the summit
crag, inside the Organ Cavern, and hanging beneath the body over the underbelly gallery. A chat briefing lists where they
are (with coordinates); a tall purple light pillar stands over each one (pointing down for the hanging node), a purple ★
marks each on the locator bar, purple beams link them to the shielded heart, golden motes mark the path, and the action
bar shows the nearest one with distance and direction. Each destroyed node strips 13% of the mountain's health and makes
it more aggressive.

### Phase 2 — The Unfolded World
**07 The Great Unfolding**: the shell peels open sector by sector; each sector becomes a giant petal that swings
outward into a crown around the exposed heart, and the arena becomes a disk of radial ribs over a mantle floor (steam
vents throw fallen players back up). The heart is sealed until it vents after **Resonance Network** or squeezes
everyone in with **Mantle Contraction** — then its iris opens for ~8 s. At low health the world refolds: the petals
slam shut and the ribs re-bloom rotated.

![Phase 2 crown](docs/images/boss001_phase2.png)
![Phase 2 from the heart's ring](docs/images/boss001_phase2_heart.png)

### Abilities (7)

| # | Ability | Phase 1 | Phase 2 | Counter |
|---|---|---|---|---|
| 01 | **Continental Fold** | a glowing fault buckles into a 9–11 block ridge, re-routing paths for 9 s | a petal folds over its sector and leaves rubble ridges | leave the fault / sector |
| 02 | **Lithic Peristalsis** | roots stomp; 3–4 waves of rock roll across the back | waves run inward along the ribs | jump each crest |
| 03 | **Geological Shedding** | rock skin peels (exposed musculature scars) and slabs are flung at marked rings | slabs thrown from the petals | leave the rings |
| 04 | **Resonance Network** | rings expand from a node, each with two green gaps | rings from the heart; then the heart opens | stand in the gaps |
| 05 | **Inverted Strata** | a 5×11 walkway levels into a slab and flips into a wall or rolls overhead into a ceiling | a rib segment flips, cutting a route | step off the outlined strip |
| 06 | **Mantle Contraction** | the Organ Cavern fills with flesh except glowing pockets | the disk contracts to the heart's ring; the heart opens | reach a pocket / the ring |
| 07 | **The Great Unfolding** | phase transition (cinematic) | the refold / re-bloom at low health | stay on the inner rings |

**Rewards:** Lithic Heart Shards (use one for *Mountain's Resolve*: Health Boost II + Resistance I for 5 min), amethyst,
diamonds, emeralds, experience. Victories and best time are recorded in the Atlas.

![Models](docs/images/boss001_models.png)

---

## How it works

* **Its own world.** `BP/dimensions/migration_path.json` defines a void dimension with a cloud layer at Y 100; the
  encounter loads it with the `TickingAreaManager`, builds the arena, and erases it afterwards. Players get a custom
  fog (`anatomy:migration_mist`), music, and a remembered return point.
* **A body you stand on.** The mountain is generated procedurally (`src/gen/mountain.ts`) at build time, then shipped as
  a compact LZ77 + base64 run-length column stream (`mm_data.js`, ~330 KB) and placed in-game through in-memory
  structure tiles (≤ 48×90×48) with the native layer-by-layer animation (falls back to budgeted writes).
* **Living strata.** `terrain.ts` keeps the dorsal surface as a height field. Abilities add deformation fields (folds,
  travelling waves, scars, levelled strips); each tick only changed columns are re-rendered through a 1 500-blocks-per-tick
  writer. Players are carried up by rising rock, trees uproot and regrow, and settled columns are restored exactly from the
  pristine data.
* **Multipart entities.** 14 legs, 3 nodes, the heart, 12 petals, flipping strata plates and slab projectiles are separate
  animated entities driven by client-synced properties and animation controllers.
* **Encounter director.** `director.ts` reads each player's zone (dorsal, cavern, underbelly, disk, mantle), cooldowns,
  enrage and how long the heart has stayed shut, and picks one main ability at a time plus a Geological Shedding barrage.
* **Chunk loading.** `spawnEntity` and block edits only work in loaded, ticking chunks, and script ticking areas share a
  per-pack chunk budget the engine does not document. The arena (100 chunks) is kept ticking region by region in priority
  order — the nodes and the heart, the arrival shelf, the Organ Cavern, the Phase 2 disk, the rest — as far as the budget
  allows (`src/core/chunks.ts`). Boss parts go through a registry (`src/core/parts.ts`): each one spawns as soon as its
  chunk is loaded, is re-acquired by entity id when its chunk unloads and reloads (with its state re-applied), is
  re-created if it vanishes, and stale parts of earlier fights are removed when they load. Block edits in unloaded chunks
  are deferred per chunk, in order, and replayed when the chunk loads; short-lived ticking areas sweep the rest, and
  structure tiles are only placed over loaded chunks. The Content Log reports `[anatomy] arena: N/100 chunks kept
  ticking` when the budget is smaller than the arena.
* **Robustness.** The fight is saved every 5 s and rebuilt deterministically at its phase after a reload; arena blocks
  can't be broken (player-placed blocks excepted), explosions don't damage the arena, natural mob spawns are removed,
  falls into the cloud sea are caught.

```
anatomy-of-a-world/
├─ src/                    TypeScript (strict) → BP/scripts
│  ├─ core/                shared boss framework: registry, manager, arena, blocks, tasks, fx, atlas UI
│  ├─ gen/                 pure generators/codecs (run in-game and in Node)
│  └─ bosses/migrating_mountain/   encounter, abilities, unfolding, director, terrain, runtime
├─ tools/
│  ├─ build.py             full build → build/packs + dist/*.mcaddon
│  ├─ packdefs.py          BP/RP JSON (entities, client entities, controllers, items, dimension, sounds, fog)
│  ├─ models/              procedural model kit + Boss 001 models and baked animations
│  ├─ fx/particles.py      18 particle effects + atlas
│  ├─ audio/synth.py       21 synthesised sound effects + 3 music tracks (OGG)
│  ├─ export_mountain.mjs  pre-generates the mountain data module
│  ├─ validate.py          cross-file validation
│  ├─ sim/                 strict Script API mock + end-to-end encounter simulation
│  └─ preview/             three.js renderer for voxels + Bedrock geometry (docs images)
└─ dist/                   The_Anatomy_of_a_World.mcaddon (+ .mcpack)
```

Build: `npm install && npm test` (TypeScript check → build → validation → simulation). Needs Python 3 with
Pillow, numpy and scipy, and ffmpeg with libvorbis.

---

## Verification

| Check | Result |
|---|---|
| TypeScript `strict` against the official `@minecraft/server` 2.11.0 / `server-ui` 2.3.0 typings | 0 errors |
| Minecraft Creator Tools 0.21 validation (both packs) | 0 errors, 0 warnings |
| `tools/validate.py` — geometry ↔ animations ↔ controllers ↔ client entities ↔ scripts, block ids + states vs vanilla 1.26.60, sounds, particles, fog, items, lang | 2 827 checks, 0 errors |
| `tools/sim/run.mjs` — the compiled scripts run against a strict API mock with a voxel world: summoning, intro, all 7 abilities in both phases, node destruction, the Great Unfolding, heart windows, re-bloom, victory, loot, cleanup, resume after reload (both phases), respawn pull-back, defeat, commands, Atlas UI | 112 checks, 0 failures, 0 API issues (repeated runs with random seeds) |
| Chunk loading in the same simulation — chunks load only inside ticking areas and around players; spawns, block edits and lookups fail in unloaded chunks, entities unload/reload with new handles, structure placements queue. A whole fight with a pack budget of 1–40 chunks and a simulation distance of 2–10: parts wait and appear, nodes stay destroyable after reloading, markers/HUD point to unloaded nodes, the whole shell is cut, the arena is fully cleared | passes for every budget/distance combination tried |
| Visual review | models, the assembled creature, cavern cutaway and the Phase 2 crown rendered from the real geometry/textures (images above) |

**Not verifiable in this environment:** I could not run the Minecraft client or a dedicated server here, so these still
need a first in-game look: frame-rate and tick cost of large block edits on your hardware, the exact look of particles
and emissive textures, and animation feel (bone rotation signs follow Bedrock/Blockbench conventions and every
flip/fold end state was made direction-independent). The Content Log (Settings → Creator) is the first place to look if
anything misbehaves.

## Roadmap
Specimens **002 The Inverted Ocean**, **003 The Thousand-Mouthed Labyrinth** and **004 The Hungry Absence** plug into the
same framework (registry, void dimension, director, terrain/structure systems) and will be built from their concept sheets.
