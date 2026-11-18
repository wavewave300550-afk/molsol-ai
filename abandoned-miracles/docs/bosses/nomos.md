# Boss 003 — Nomos, The Unmapped Sovereign

*Living cartography. A surveying engine that was asked to draw a country which did not exist, and has been correcting the ground ever since.*

| | |
|---|---|
| Entity | `abm:nomos` (family `abm_nomos`) |
| Summon | Seal of the Unmapped Sovereign, `abm:seal_nomos` (4 paper, 4 compasses, 1 empty map) |
| Arena | The Observatory of Unwritten Borders, `abm:observatory_of_unwritten_borders`, 47 × 15 × 47, square, 40 × 40 fighting floor |
| Health | 560 (× player scaling), Phase II at 40 % |
| Trophy | Needle of the Unmapped Sovereign, `abm:sovereign_needle` |
| Source | `src/bosses/nomos/`, `tools/bosses/nomos/`, `shared/nomos.timings.json`, `tools/sim/specific/nomos.mjs` |

All times below are in ticks (20 per second) and come from `shared/nomos.timings.json`, the one file read by both the animations and the script. All numbers come from `src/bosses/nomos/tuning.ts`.

## Design

Nomos is a quadrupedal arthropod built out of antique surveying machinery, about 6.5 blocks tall.

- **Body**: a plane table (drawing board) carried level on four long divider legs — brass upper sections with drilled adjustment holes, graphite shanks, steel points. It does not look like a horse or a mechanical spider: the mass is a flat table held high, not an abdomen slung between the legs.
- **Head**: a compass assembly on a short neck — an armillary of four nested rings (`ind_1` … `ind_4`), each with its own needle and glowing tip, each rotating independently.
- **Spine**: five segmented ruler sections along the table, with a protractor, a sighting scope, a spirit level (the bubble glows) and a plumb line and bob hanging from the tail.
- **Map surfaces**: four pleated map sheets, three panels each, folded against the flanks in Phase I and opened flat in Phase II.
- **Scribing appendages**: two three-jointed scribe arms under the front of the table, ending in nibs.
- **Rig**: 64 bones, 195 cubes, one 256 × 128 texture, three render layers (opaque, emissive `_glow` bones, translucent `_glass` bones). Its own skeleton and locators (`compass`, `needle_1..4`, `sheet_*`, `foot_*`, `nib_l/r`, `plumb`, `core`).
- **Animations**: idle, walk, turn, compass spin, footfalls, intro, stagger, phase transition, death, the Phase II pose and compass, and one animation per attack per phase (14) — all keyed from the shared timings file.

### Locomotion

A lateral-sequence four-beat walk (back-left, front-left, back-right, front-right) driven by distance moved, so the points never slide; each footfall plays `abm.nomos.step` and a puff of dust at the foot locator. Turning is a separate stepping-in-place cycle driven by body yaw. Movement is script-driven (`enc.loco`): Phase I 0.07 blocks/tick and 3.2°/tick, Phase II 0.10 and 4.6°.

## Signature system — the survey grid

The arena floor is a map, and every attack is drawn on it. `src/bosses/nomos/grid.ts` (`SurveyGrid`) is a purely logical grid: nothing is ever written to the world.

- 8 × 8 cells of 5 blocks, centred on the arena centre; ruled lines every 5 blocks; four quadrants (0 NW, 1 NE, 2 SW, 3 SE) with centres at (±10, ±10).
- The structure's floor pattern (`tools/bosses/nomos/arena.py`) is laid out on the same ruling: dark ruled lines every 5 blocks, a copper meridian and parallel through the lodestone origin, emerald benchmarks at the quadrant centres.
- `chord(p, θ, w)` builds an edge-to-edge line through a point; `snapLine` finds the nearest ruled line; `cellOf / cellCentre / quadrantOf` convert both ways.
- **Safe-path validation**: `maxDistanceToSafety(danger)` runs a two-pass chamfer distance transform over a one-block lattice and returns the furthest any point in the arena is from ground the pattern does not cover. `reachable(danger, warn, walk, reaction)` compares it with what a walking player (4.317 blocks/s) can cover after a 0.4 s reaction. Arena-wide patterns are validated with it before they are shown; one that fails is replaced by a pattern known to pass and an `unsafe_pattern` trace is emitted.

Patterns (`patterns.ts`) are ordinary shapes for the shared hazard system: `Stripes` (parallel corridors at any bearing, clipped to a box), `Checker` (a shifted chessboard clipped to a box) and `Marks` (drawing only — it covers nothing and can never deal damage).

## AI

- **Stations, not pursuit.** Nomos keeps its distance. When the target is closer than 6.5 blocks or further than 12.5 (6 / 13 in Phase II) it picks a *station*: the centre of the grid cell about 9 blocks from the target on the arena-centre side, walks there and turns to face. It never walks a station for more than 8 s.
- **Attack choice** is the shared weighted scheduler with per-attack cooldowns counted from the end of each attack. Weights depend on distance (darts and Folded Country at range, Unmapped Gate when the target is far or Nomos is cornered) and on state (Ink Borders has weight 0 while borders are standing).
- **Poise.** 110 points of player damage inside 5 s staggers it for 36 ticks (once every 21 s at most). The ultimate ignores staggers.
- **Folded out of the map.** Between the fold and the arrival of Unmapped Gate, Nomos cannot be damaged.
- **Targets.** Single-target lines use the shared threat-based primary target; multi-part attacks (Phase II incisions, darts) cycle through the participants so every player is addressed.

## The seven attacks

Every hazard is created through the shared hazard system at the moment it is telegraphed, drawn on the floor in Nomos's ink style (`abm:nomos_tg_*`, with separate `abm:nomos_safe_*` marks for safe ground) and resolved against player positions on the server.

### 01 — Meridian Incision

A scribe arm rules a line across the whole map and the line cuts.

- **Phase I**: tick 4 — a 2.8-block-wide line from Nomos through the target, edge to edge; it cuts at tick 36 (1.6 s). Tick 40 — a second line at right angles through wherever the target now stands; it cuts at tick 70. Ends at 96.
- **Phase II**: three incisions drawn at ticks 4, 18, 32, each cutting 28 ticks later, on three bearings 60° apart (the first is a random multiple of 45°), each through a participant's position. None of them needs to pass through Nomos.
- **Hit**: `Lane` across the arena, 14 damage, small pop-up. Cooldown 150 / 120.
- **Counterplay**: step 1.4 blocks sideways off the line. The second cut is why you do not stop where you landed.

### 02 — Latitude Shear

The scribe arms open like calipers and two curved bands close on the arena centre.

- **Geometry**: two arcs, 2.4 blocks wide, 15 blocks either side of the centre along the axis on which the target stands (Phase II: snapped to 45°), closing at 3.6 blocks/s.
- **Phase I**: marked at tick 2 together with the safe lane between the positions where the bands will stop; they start moving at tick 36 and travel for 60 ticks. Ends at 122.
- **Phase II**: first pair starts at tick 30; at the same moment a second pair is marked at right angles and starts at tick 56. What remains is a square at the centre, or the ground behind where both pairs started.
- **Hit**: a moving `Ring` segment checked every 2 ticks, each band once per player, 12 damage. Cooldown 230 / 200.
- **Counterplay**: the bands are slower than a walk. Go to the marked lane, or step behind a band's starting line before it moves.

### 03 — Ink Borders

Nomos stamps borders onto the map.

- **Phase I**: two borders (1.2 wide, up to 24 long) marked at tick 6 and stamped at tick 40: one straight through the target's position across Nomos's line of approach, one along the nearest ruled line beyond the target — a corner of new territory.
- **Phase II**: four borders stamped at tick 36: a corridor with two staggered half-gates. The layout is never a closed cell; the simulation flood-fills the floor to prove it stays one connected region.
- **The stamp** is the strike: 10 damage and Slowness I for 2 s to anyone on a line when it is inked.
- **Standing borders** last 8 s (Phase I) / 11 s (Phase II). They never block and never wound: touching wet ink applies Slowness I (Phase II: Slowness II) for 2 s, refreshed while you stand in it. That is the arena control — the next attack has to be walked out of along routes that do not cross ink, or more slowly.
- Never stacked (weight 0 while borders stand); wiped at the phase change, on death, on reset and if the stamp is interrupted. Cooldown 340 / 300.

### 04 — Unmapped Gate

Nomos folds itself into a coordinate and unfolds at another.

- **Destination**: 3.5 blocks beyond the target on the line from Nomos; if that is not valid, positions rotated round the target in 30° steps; if the target hugs a wall, the nearest coordinate Nomos may occupy. A destination must be at least 4.5 blocks inside the walls, at least 6 blocks from where Nomos stands and pass `loco.canStand`; the move itself is `loco.relocate`, which validates again. With no valid destination Nomos stays where it is and the strike lands around itself.
- **Phase I**: tick 6 — a benchmark ring at the departure point and the arrival disc (radius 5) at the destination; tick 24 — it folds away (no damage can be dealt to it); tick 38 — it relocates; tick 44 — arrival. Ends at 76.
- **Phase II**: arrival at tick 38, then a second gate marked at 42 and arriving at 74 as a cross: two edge-to-edge lines, 3.2 wide, through the arrival point along both grid axes.
- **Hit**: 15 damage, knock-back from the arrival point. Cooldown 260 / 210.
- **Counterplay**: the arrival mark is on the floor for 1.9 s (1.6 s in Phase II); walk out of the disc, or off the row and column of the cross.

### 05 — Compass Darts

Needles take a bearing, lock, and fly.

- **Phase I**: four needles in a row in front of Nomos. A thin sight-line follows the target; the needles lock one after another at ticks 30, 39, 48, 57. At the lock the whole flight path is drawn and the bearing is final; the dart flies 15 ticks later at 18 blocks/s until it pins into the edge of the map. Ends at 100.
- **Phase II**: the needles stand at the four quadrant centres (locks from tick 26, 7 apart), then a second volley from the four wall midpoints (locks from tick 68). 14 ticks between lock and flight. With several players each needle takes a different target.
- **Hit**: 0.7-radius collision moving at the same velocity as the sprite, 9 damage, blockable with a shield, hits each player once. The needle's mount also snaps as it releases (radius 1.1, 5 damage) — do not stand on a station.
- **No re-aim**: the bearing is stored at the lock and the simulation checks every tick of every flight against it. Cooldown 200 / 170.
- **Counterplay**: keep moving until the lock, then step off the drawn path; one step per dart.

### 06 — Folded Country

The map sheets slam shut along their pleats: alternate corridors of the floor are folded away.

- **Geometry**: corridors 2.5 blocks wide running along the line from Nomos to its target (so backing away never leaves them), across the whole arena. The first set struck is always the one the target is standing in. The centre lines of the safe corridors are drawn in the safe style.
- **Phase I**: three strikes at ticks 34, 52, 70 — this set, the other set, this set again — each marked 30 ticks ahead. Ends at 96.
- **Phase II**: four strikes at ticks 32, 48, 64, 80, each marked 28 ticks ahead, and the pleats turn 90° on every beat.
- **Hit**: `Stripes`, 13 damage. Cooldown 220 / 190.
- **Counterplay**: a sidestep of at most 2.5 blocks into the neighbouring corridor, on the beat.

### 07 — The Great Recalculation (ultimate)

Nomos re-projects the whole floor three times. Cannot be interrupted.

- **Three coordinate systems**, shown in a random order:
  - *Cartesian* — a chessboard of 10-block squares with alternate squares struck out. The board is shifted half a square on at least one axis so that the squares along the walls are only 5 blocks deep.
  - *Polar* — a disc of radius 4 round the arena centre and a ring from 9 to 14.
  - *Oblique* — diagonal corridors 5 blocks wide.
- **Phase I**: the three states are previewed one after another at ticks 10, 24, 38. Then each is applied in the same order at ticks 96, 142, 188; for the 40 ticks before each strike its danger region and its safe marks are on the floor. Ends at 214.
- **Phase II**: previews at 8, 20, 32; strikes at 82, 122, 162 with 34 ticks of warning — and every quadrant is drawn in a *different* system each time, shown on that quadrant's indicator.
- **Validation**: every state is checked with `SurveyGrid.reachable` before anything is shown. The worst case a player can be asked to walk is 5.0 blocks; 6.9 (Phase I) / 5.6 (Phase II) are possible in the warning time after a 0.4 s reaction.
- **Hit**: 18 damage per state. Cooldown 780 / 720.
- **Counterplay**: read the preview, then solve one state at a time; only one state is ever pending.

## Phase II — THERE IS NO NORTH (40 %)

Damage is gated at 40 % and the transition runs for 150 ticks: the compass shudders and scatters, the table rises 14 units on its legs, the four map sheets open flat and the four rings leave the hub — each lies down over one sheet as that quadrant's own indicator. From then on each needle is driven by an entity property (`abm:q1` … `abm:q4`, eight bearings) and shows what its quadrant is about to do; between attacks all four watch the target. Standing ink borders are wiped. Nomos moves and turns faster, every attack uses its Phase II form and cooldowns shorten.

## Death

190 ticks: the rings lose alignment and drift apart (40), the body tries to fold itself into a map and fails (90), the parchment collapses and the legs give way (140), the last needle slows and stops (170). The trophy is granted with the encounter's normal reward flow; loot is one Needle of the Unmapped Sovereign plus emeralds, paper, copper, a compass and 2–4 diamonds.

## Tuning

| | |
|---|---|
| Health / Phase II | 560 / 40 % |
| `damageTaken` | 0.125 (simulated solo kill 227–232 s over four seeds) |
| Damage | Incision 14 · Shear 12 · Border stamp 10 · Gate 15 · Dart 9 (mount 5) · Folded Country 13 · Recalculation 18 |
| Cooldowns P1 / P2 | 150/120 · 230/200 · 340/300 · 260/210 · 200/170 · 220/190 · 780/720 |
| Stagger | 110 damage in 5 s → 36 ticks, at most every 21 s |

## Simulation coverage

`tools/sim/specific/nomos.mjs` adds seven scenarios to the generic suite: the grid is the arena; every Great Recalculation state leaves a walkable safe route (240 states, checked against an independent brute-force search); the ultimate runs three validated strikes and ignores a stagger; Unmapped Gate only lands on validated ground and holds position when nowhere is standable; Compass Darts never re-aim after the lock; Ink Borders slow but never wound, block or enclose and are wiped with the phase; Phase II indicators stay in range and a reset leaves no arena state.

## Not verified

Nothing here has been run inside Minecraft. The build passes the project validator and the script passes the headless simulation; the model and poses have been checked only in the project's own offline renderer. In particular, unverified in game: the look and timing of the animations and the phase controller blend, the needle bearings driven by `abm:q1..q4` relative to body rotation, the alignment of the dart sprite with its flight direction, particle density of the chessboard telegraph (up to 77 particle calls in one tick in simulation), sound mix, and whether Slowness from wet ink feels fair against Phase II patterns.
