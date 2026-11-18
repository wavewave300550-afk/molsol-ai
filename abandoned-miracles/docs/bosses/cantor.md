# Boss 002 — Cantor XIII, The Walking Requiem

| | |
|---|---|
| Entity | `abm:cantor_xiii` (family `abm_cantor`), helper `abm:cantor_bell` |
| Arena | The Basilica of the Last Note — `abm:basilica_of_the_last_note`, 51 × 16 × 51, fighting circle radius 19 |
| Summon | Seal of the Last Note `abm:seal_cantor` (4 copper blocks, 4 gold ingots, 1 bell; unlocked by holding a bell) |
| Trophy | Fragment of the Thirteenth Bell `abm:bell_fragment` + loot table `abm/cantor` |
| Health | 520, damage taken × 0.125, Phase II at 50 % |
| Source | `tools/bosses/cantor/` (model, animations, effects, arena), `src/bosses/cantor/` (combat), `shared/cantor.timings.json` |
| Previews | `docs/previews/cantor/` |

Everything on this page was produced by the build and exercised in the headless simulation
(`tools/sim`). Nothing here has been run inside Minecraft: see *Not verified* at the end.

## Design

A cathedral that got up and walked. A bronze and charcoal reliquary on three jointed legs, the nave
windows lit from inside, ranks of organ pipes on folding wings at its back, four small bells on
chains, and for a head the thirteenth bell — hung upside down, mouth to the sky, clapper pointing up.
Oxidised bronze with verdigris, gilt bands, a rose window on the front and lancets on both sides.

- Model: 45 bones, 190 cubes, one 512 × 256 texture, about 10 blocks to the tip of the clapper.
  Collision 3.2 × 8.2. Emissive layer on every bone ending `_glow` (core, windows, bell crack).
- Phase II is a different silhouette, not a recolour: a third of the bell's lip is gone
  (`bell_chunk` hidden), the crack burns (`bell_crack_glow` shown), the pipe wings hang open and
  splayed, the body lists, and the windows stutter instead of pulsing.
- The stained glass is "lit" by moving a glowing pane in front of its dark backing, driven by the
  beat. During the Silent Measure (`abm:silent` = 1) every window is forced dark.

### Locomotion

Three legs, each a thigh / shin / foot chain at 0°, 125° and 235°. The gait is distance-driven
(`q.modified_distance_moved × 0.411` phase), one leg in the air at a time, each stroke split into a
tangential hip swing and a radial shin reach so the feet travel straight under a round body. A turn
in place uses the same three-beat lift with 21.6° of yaw compensation per step. Footfall sound and
dust are fired from the animation timeline, per foot.

Cantor holds the centre of its hall. Phase I: it only walks if pushed more than 5 blocks off the
centre, otherwise it turns (2.6°/tick) to face its target. Phase II: it drifts up to 5 blocks towards
the target (speed 0.085, turn 3.6°/tick). All patterns that use the floor's rings and spokes are
centred on the hall, not on Cantor, so drifting never moves the answer away from the floor marks.

## Signature system — the beat

One beat is 10 ticks, one measure 40 (`shared/cantor.timings.json`).

- **Attacks start on a beat.** The controller rounds the scheduler's next start up to a multiple of
  10 ticks every tick it is idle. Tested: `cantor: every attack begins on a beat`.
- **The beat is visible.** A floor pulse (`abm:cantor_beat`) is drawn under Cantor on every beat in
  Phase I and on the broken pattern 0-12-20-32 of each measure in Phase II; the windows flash with
  it. The pulse stops during the transition, the death and the Silent Measure.
- **Readable with the sound off.** Every hazard is drawn on the floor before it lands, and every
  moving wave is drawn from the same shape, on the same ticks, as the collision test. Safe doors and
  corridors are marked in a second colour (`abm:cantor_safe_line` / `safe_arc`).
- **Patterns, not reactions.** Rings have doors, wave fronts have doors, the ultimate is a sequence
  of floor cells. Nothing is aimed at where a player will be after the telegraph appears, except
  the Phase II echo of Held Note, which re-aims once and is telegraphed again.

Two synced properties are specific to this boss: `abm:silent` (0/1, windows dark, pulse off) and
`abm:bells_out` (0/1, two of the four small bells are hidden on the model while they are on the
floor as `abm:cantor_bell` entities).

## AI

- Target: the framework's primary target (re-evaluated with hysteresis), read between attacks.
- Selection: weighted random among eligible attacks; the framework multiplies the weight of the
  attack just used by 0.12, so repeats are rare. Per-attack cooldowns and conditions are below.
- After each attack Cantor waits for its recovery window, then for the next beat.
- Leash and reset are the framework's: no living player in the arena → attack cancelled, helpers
  removed, properties cleared, health restored, Cantor returns to the centre.

## The seven attacks

Ticks are 1/20 s and are counted from the start of the attack. Damage is design damage in health
points before the multiplayer scale and before armour. "I / II" are Phase I / Phase II values.
All attacks except the ultimate are cancelled by a phase change, a stagger, a reset or death; on
cancel the framework removes every pending strike and wave with the attack's tag.

### 01 — Prime Downbeat

The clapper is drawn back and the great bell tolls: a ring rolls outward from Cantor across the
whole hall.

| | |
|---|---|
| Eligibility | always; weight 3.2 if the target is within 11 blocks, else 2.0 |
| Cooldown | 70 / 60 |
| Telegraph | 30 ticks; the three doors are marked on the floor from tick 0 |
| Active | ring from radius 2 to the far wall at 0.3 blocks/tick, 1.6 thick, 3 doors of 40° |
| Damage | 13, knockback 0.6 away from Cantor; a player is hit once per ring |
| Recovery | until tick 110 / 134 |
| Counterplay | stand in a marked door and let the ring pass, or be far enough away to walk to one |
| Phase II | a second, weaker toll (6) on the off-beat at tick 54; its doors are turned 20° and are 44° wide, so each door of the second ring overlaps a door of the first by 22° |
| Interruptible | yes (stagger, phase change) |

Doors never pinch shut at close range: within about 5 blocks of the centre a door is widened so it is at least
3.4 blocks across (the floor mark is the narrower, always-safe wedge).

### 02 — Counterpoint

Two voices. A wave front enters at one wall and crosses the hall; a second front enters at right
angles to it a measure later. Each front has doors, and each door's whole path is marked as a safe
corridor before the front moves.

| | |
|---|---|
| Eligibility | always; weight 2.6 if the target is more than 7 blocks away, else 1.6; +0.8 with more than one player |
| Cooldown | 220 / 190 |
| Telegraph | 40 ticks before the first front moves; both sets of corridors are visible from tick 0. The fronts then need about another 60–67 ticks to reach the middle of the hall |
| Active | fronts 1.4 thick at 0.3 / 0.34 blocks/tick; doors 5 blocks wide, 13 apart; first direction one of eight compass directions, second at ±90° |
| Target rule | doors are placed so the target is never already standing in one |
| Damage | 9 per front, knockback 0.9 |
| Recovery | until tick 220 / 204 |
| Counterplay | walk to a corridor of the first front, then to a corridor of the second; where two corridors cross, both fronts miss |
| Phase II | the second voice enters after 24 ticks instead of 40 and both are faster |
| Interruptible | yes |

### 03 — Glass Aria

The shutters open and the windows sing: volleys of glass shards in fixed fans.

| | |
|---|---|
| Eligibility | always; weight 2.8 with the target 4–17 blocks away, else 1.2 |
| Cooldown | 160 / 130 |
| Telegraph | Cantor faces its target once at the start; each volley's lanes are drawn 24 ticks before it flies |
| Active | I: 3 volleys at ticks 40, 60, 80; II: 4 volleys at 36, 52, 68, 84. Fans alternate 5 lanes (−40…+40°) and 4 lanes (−30…+30°) so the second volley flies through the gaps of the first. Shards travel 20 blocks at 0.55 blocks/tick, radius 0.55 |
| Damage | 9, blockable with a shield, knockback 0.5. Volleys 1+3 and 2+4 are one hazard each, so one aria wounds a player at most twice |
| Recovery | until tick 130 / 144 |
| Counterplay | stand between lanes and change lane between volleys; behind Cantor is clear |
| Phase II | under the second volley a 200° half-ring wave leaves Cantor towards the aim (0.3 blocks/tick, reach 16) with two 34° doors at ±50° |
| Interruptible | yes |

### 04 — Held Note

The pipe wings swing forward and the organ holds one note until it breaks.

| | |
|---|---|
| Eligibility | always; weight 2.4 with the target 3–15 blocks away, else 0.6 |
| Cooldown | 200 / 170 |
| Telegraph | 60 / 52 ticks; the cone outline is drawn at once and fills from its axis outwards one step per beat |
| Active | one strike on a cone ±42° wide from radius 3.2 to 15, fixed when the attack starts |
| Damage | 18, knockback 1.5 |
| Recovery | until tick 100 / 120 |
| Counterplay | step out of the cone sideways, or stand under the pipes: the disc inside radius 3.2 is marked safe |
| Phase II | an echo: at the blast the cone is re-aimed at the current target, ±30°, 14 damage, and lands 32 ticks later with its own telegraph |
| Interruptible | yes |

### 05 — The Silent Measure

The bell is caught mid-swing. The pulse stops, the windows go dark, a rest sign hangs over the
bell — and the beat that was owed arrives late, from the walls inward.

| | |
|---|---|
| Eligibility | only after at least two other attacks since the last Silent Measure (there has to be a rhythm before it can be withheld); weight 2.2 |
| Cooldown | 300 / 260 |
| Telegraph | silence from tick 20 / 16 to tick 80 / 72 (`abm:silent` = 1); the four doors are marked from tick 0 |
| Active | ring contracting from the far wall to Cantor at 0.4 blocks/tick, 1.6 thick, 4 doors of 34° (widened near the centre like the Downbeat's) |
| Damage | 14, knockback 0.6 |
| Recovery | until tick 160 / 176 |
| Counterplay | the silence is the warning: find a door before the bell is released |
| Phase II | a second, weaker ring (5) 24 ticks later with doors turned 14° and 40° wide (23° of overlap) |
| Interruptible | yes; if it is cancelled the silence ends at once (tested) |

### 06 — Twin Resonance

Two of the small bells are cast off their chains and stand on the floor, each tolling on its own
interval.

| | |
|---|---|
| Eligibility | not while any detached bell still stands; weight 2.0 |
| Cooldown | 480 / 400 |
| Telegraph | detach at tick 30 / 24; the first warnings begin 20 and 40 ticks after landing |
| Placement | one bell beside the primary target (a fifth of the way towards the centre), one diametrically opposite; never within 4 blocks of Cantor, always 2.5 blocks inside the wall |
| Active | each bell: 34 ticks of warning (swinging bell + filling disc), then a strike on a disc of radius 4.5. Intervals 70 and 90 ticks (II: 50 and 70). Lifetime 320 / 400 ticks |
| Damage | 9 per pulse, knockback 0.7 |
| Recovery | until tick 60 / 52 — Cantor keeps attacking while the bells toll |
| Counterplay | leave the disc; or strike the bell — any hit cancels the pulse it is winding up and restarts its count. A bell has 24 health |
| Reward | destroying **both** bells staggers Cantor for 40 ticks. Letting them expire does not |
| Cap and cleanup | never more than two; removed on expiry, at the phase change, on reset and on death (all tested); `abm:bells_out` follows |
| Interruptible | yes (the bells already on the floor stay) |

### 07 — The Final Requiem (ultimate)

The whole hall is the score. The floor's six spokes and three rings divide it into cells; four
measures are struck, and for each one the *safe* cells are drawn while everything else is marked.
Only one measure is on the floor at a time: the next is shown when the last one lands.

| | |
|---|---|
| Eligibility | below 90 % health; weight 5 |
| Cooldown | 720 / 680 |
| Telegraph | first measure 59 ticks, then one measure (40–44 ticks) each |
| Strikes | I: ticks 60, 100, 140, 180; II: 60, 104, 144, 188 |
| Phase I | alternate sixths (full length) → the middle band (radius 6–12) → the other sixths (inside 12) → under the bell (inside 6) |
| Phase II | the middle band → alternate sixths, short (inside 12) → the other sixths, far half only (beyond 9) → the walls (beyond 13) |
| Damage | 17 per measure, small knock-up, not blockable |
| Recovery | until tick 224 / 232 |
| Counterplay | read the lit cells and walk; every answer is reachable at walking speed from anywhere inside the previous answer (tested on a half-block grid: worst case uses 89 % / 92 % of the time available) |
| Interruptible | **no** — not by stagger; a phase change or death still ends it |

## Phase II — The Broken Symphony (50 %)

Trigger: health reaches 50 %. The framework blocks all damage for the 140-tick transition.
Detached bells are recalled, the pulse stops, the bell cracks (tick 30), a third of its lip falls
(tick 60: knockback only, no damage, within 6 blocks), the pipe wings unfold (tick 100).

Afterwards: the broken pulse pattern, shorter cooldowns, faster movement with drift, a second toll
on Prime Downbeat and The Silent Measure, a tighter Counterpoint, a fourth Glass Aria volley with a
wave under it, the Held Note echo, faster bells, and the Requiem played outward instead of inward.

## Death

220 ticks, no hazards. The great bell falls (tick 30), the pipes drop rank by rank (from tick 60,
every 8 ticks), the legs give way one at a time (from tick 150, every 16 ticks) with dust at each.
The framework then awards the trophy to every participant, rolls the loot table once and turns the
body into a remnant that despawns.

## Tuning

All numbers live in `src/bosses/cantor/tuning.ts` (damage, speeds, door sizes, cooldowns),
`shared/cantor.timings.json` (beats — shared with the animations, so a changed strike tick moves
the animation with it) and the `cantor:` line of `src/config.ts` (health, phase threshold, arena
radius, damage taken).

Simulated solo fight (perfect-information bot in full protection-IV diamond-class armour, sword
swing every 12 ticks): 221–238 s over six seeds, 0 deaths, 0–1 hits taken. A bot that stands still
is hit by all 14 attack/phase combinations; a bot that walks avoids all 14.

## Not verified

- Nothing was run in Minecraft. Rendering of the model, emissive layer, particles and sounds,
  entity-property driven animation states, and structure placement are validated only by the
  project's static validator, Minecraft Creator Tools, software previews and the simulation's mock
  of the Script API.
- The software previews use the project's own renderer, not the game's; lighting and the emissive
  look will differ.
- Sounds are synthesised and were checked only by the validator (format, length, level), not by ear.
- Balance figures come from a bot with perfect knowledge of every telegraph. A person will be hit
  more often; Counterpoint and the Phase II double rings are the patterns most likely to need
  loosening after real play.
