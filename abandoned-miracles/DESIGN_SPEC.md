# The Abandoned Miracles — design specification

*Four perfect miracles. Four catastrophic successes.*

This document is the finalized specification of what the add-on does: the shared encounter rules, the technical
approach and its trade-offs, and the tuning surface. Each boss has its own chapter with its seven attacks:

| # | Boss | Concept | Chapter |
|---|---|---|---|
| 001 | Vesperra, The Ivory Succession | immortality through perpetual biological replacement | [docs/bosses/vesperra.md](docs/bosses/vesperra.md) |
| 002 | Cantor XIII, The Walking Requiem | harmony turned into destructive musical control | [docs/bosses/cantor.md](docs/bosses/cantor.md) |
| 003 | Nomos, The Unmapped Sovereign | a living map that restructures space | [docs/bosses/nomos.md](docs/bosses/nomos.md) |
| 004 | Orison, The Witness of Tomorrow | an entity that attacks through remembered and predicted events | [docs/bosses/orison.md](docs/bosses/orison.md) |

What has and has not been verified is stated in [TEST_REPORT.md](TEST_REPORT.md). In short: everything here is
implemented, statically validated and exercised in a headless simulation; **nothing has been observed running in
Minecraft itself.**

---

## The four encounters at a glance

Every boss has exactly two phases and exactly seven attacks. Phase II never adds an eighth attack: it changes how the
same seven behave (more beats, mirrored or recombined patterns, shorter cooldowns). Full timings, damage and weights
are in the boss chapters.

| | Vesperra | Cantor XIII | Nomos | Orison |
|---|---|---|---|---|
| Base health | 480 | 520 | 560 | 600 |
| Phase II at | 45 % — *The True Empress* | 50 % — *The Broken Symphony* | 40 % — *There Is No North* | 35 % — *Tomorrow Has Already Happened* |
| Signature system | three breakable armour regions hit by aim | a beat the whole fight is played on | an 8 × 8 logical survey grid | a bounded history of where players stood |
| Arena | The Hall of Endless Succession | The Basilica of the Last Note | The Observatory of Unwritten Borders | The Court of Unlived Hours |
| Trophy | Ivory Diadem of Succession | Fragment of the Thirteenth Bell | Needle of the Unmapped Sovereign | Hourglass of the Unlived Future |
| Helpers | Heirs (max 2), cocoon anchors | detached bells | none | shadows, hourglasses |

**Vesperra, The Ivory Succession**

| # | Attack | What it is | Counterplay |
|---|---|---|---|
| 1 | Ivory Scythe | two-beat frontal sweep; the second beat is aimed at where the target went | leave the sector, or get behind her |
| 2 | Needle Procession | three parallel lanes fired in a marked order | step to a lane that has already fired |
| 3 | Royal Molting | eight shell plates ejected along drawn flight paths | stand between two paths |
| 4 | Cocoon Edict | three anchors raise a silk triangle that constricts | break an anchor or walk out |
| 5 | False Submission | a feigned stagger, then a lunge down a lane | read the cue (needles cocked, crown glint) and stay off the lane |
| 6 | The Heirs | up to two Heirs guard her exposed flanks | kill them, or wait out their 25 s |
| 7 | Coronation of Fracture | seven fracture chords laid through the players, one after another | keep walking; never stand on a marked chord |

**Cantor XIII, The Walking Requiem**

| # | Attack | What it is | Counterplay |
|---|---|---|---|
| 1 | Prime Downbeat | a ring rolls outward from the bell across the hall | stand in a marked door and let it pass |
| 2 | Counterpoint | two wave fronts at right angles, each with marked corridors | take a corridor of the first, then of the second |
| 3 | Glass Aria | volleys of glass shards in fixed fans | stand between lanes, change lane between volleys |
| 4 | Held Note | a sustained cone from the organ pipes | sidestep, or stand under the pipes |
| 5 | The Silent Measure | the pulse stops; the owed beat arrives late from the walls inward | the silence is the warning: find a door |
| 6 | Twin Resonance | two detached bells toll discs on their own intervals | leave the disc or strike the bell to reset it |
| 7 | The Final Requiem | four measures over the floor's cells; safe cells are lit | read the lit cells and walk |

**Nomos, The Unmapped Sovereign**

| # | Attack | What it is | Counterplay |
|---|---|---|---|
| 1 | Meridian Incision | a line ruled across the whole map cuts, then a second through where you went | step off the line and do not stop where you landed |
| 2 | Latitude Shear | two curved bands close on the arena centre | go to the marked lane or behind a band |
| 3 | Ink Borders | borders stamped on the grid; the stamp wounds, the standing ink only slows | step off the marked lines before the stamp; route around wet ink |
| 4 | Unmapped Gate | folds away and unfolds at a marked coordinate with a cross | leave the disc and its row and column |
| 5 | Compass Darts | needles take a bearing, lock, and fly | move until the lock, then step off the path |
| 6 | Folded Country | alternate corridors of the floor are folded away | sidestep into the neighbouring corridor on the beat |
| 7 | The Great Recalculation | the whole floor is re-projected three times | read the preview; solve one state at a time |

**Orison, The Witness of Tomorrow**

| # | Attack | What it is | Counterplay |
|---|---|---|---|
| 1 | Footstep Echo | the target's last footprints detonate, newest first | do not retrace your own path |
| 2 | Pendulum Verdict | a pendulum blade sweeps a drawn arc (Phase II: and swings back through the outer band) | step under the swing, beyond its reach, or behind Orison |
| 3 | Deferred Wound | marks set where players stand go off after a countdown | walk away from each mark |
| 4 | Hourglass Drain | hourglasses set beside players slow and pulse | leave the circles, or break one (which also staggers Orison) |
| 5 | Tomorrow's Witness | a shadow strikes where the target is predicted to be | change direction after the prediction locks |
| 6 | Secondhand Exchange | Orison swaps places with a marked spot; both ends strike | leave the arrival circle; do not hide where it leaves |
| 7 | The Hour That Never Occurred | three arena-wide patterns are previewed, then happen in the same order | remember the order; the third is the first inverted |

---

## 1. Platform

| | |
|---|---|
| Game | Minecraft: Bedrock Edition **1.26.60** (latest stable at build time) or newer; `min_engine_version` 1.26.60 |
| Script modules | `@minecraft/server` **2.11.0**, `@minecraft/server-ui` **2.3.0** — the stable versions for 1.26.60 |
| Experiments | none. No Beta APIs, no experimental toggles, no custom blocks |
| Namespace | `abm:` for every identifier |
| Packs | one behaviour pack + one resource pack in `The_Abandoned_Miracles.mcaddon` |

How the versions were established: the npm dist-tags of the Script API packages (`latest` = 2.11.0 / 2.3.0, with
1.26.60 shipping 2.12.0 only as beta), Mojang's `bedrock-samples` `version.json` (1.26.60.5, 27 Oct 2026), and the
typings themselves, against which every line of script is type-checked. Component and block names were checked
against vanilla 1.26 entity files from `bedrock-samples` and the `@minecraft/vanilla-data` 1.26.60 catalogue.

## 2. Architecture

```
src/
  main.ts, boot.ts, registry.ts     wiring; which boss modules are present
  config.ts                         the central tuning file
  items.ts, ui.ts, commands.ts, scriptevents.ts   seals, trophies, Codex, /abm:* and /scriptevent abm:*
  core/
    manager.ts        EncounterManager   create / adopt / release encounters; one tick loop for all of them
    encounter.ts      Encounter          one fight: owns every piece of its transient state
    stateMachine.ts   BossStateMachine   INTRO → PHASE_1 → PHASE_TRANSITION → PHASE_2 → DEATH (+ substates)
    scheduler.ts      AttackScheduler    weighted, cooldown- and history-aware attack choice
    targeting.ts      TargetingSystem    participants, threat, focus with hysteresis
    arena.ts          ArenaController    logical arena, leash, placement scan (never edits blocks)
    hazards.ts        HazardSystem       telegraph + strike from one Shape; sweeps; projectiles
    shapes.ts                            circles, rings with gaps, sectors, lanes, polygons, unions, "everything except"
    damage.ts         DamageSystem       deterministic player damage
    locomotion.ts                        script-driven movement and turning
    helpers.ts                           capped, tagged, expiring helper entities
    visuals.ts        VisualEventController   parametric telegraph particles, decorative density
    audio.ts          AudioEventController
    hud.ts, rewards.ts (RewardManager), persistence.ts (PersistenceManager), timeline.ts, trace.ts
  bosses/<boss>/      one module per boss: controller, seven attacks, special systems, tuning
shared/<boss>.timings.json          beat timings used by BOTH the script and the animation generator
tools/                              asset generators, build, validator, previews, simulation
```

Game logic is separate from presentation triggers: attacks are scheduled on an encounter timeline and call the
hazard, visual and audio controllers; nothing in `core` knows what any boss looks like. Attack definitions are data
plus one `run` function each; the four bosses share utilities, not implementations — each has its own special system
(armour regions, rhythm scheduling, a coordinate grid, a position history).

## 3. The encounter model

### 3.1 States

```
INTRO → PHASE_1 → PHASE_TRANSITION → PHASE_2 → DEATH
```

Exactly two combat phases. Inside a phase the boss is in one behavioural substate:
`IDLE, POSITIONING, TELEGRAPH, ATTACK, RECOVERY, STAGGER, RESET`. Both levels have an explicit table of legal
transitions; an illegal one is refused and reported, so overlapping requests (a stagger during a phase change, a death
during an attack) cannot produce an impossible state. Only one attack runs at a time.

* **INTRO** — the boss is untouchable; the introduction plays; then PHASE_1.
* **Phase gate** — in PHASE_1 the boss's health cannot go below its Phase II threshold: the hit that would cross it is
  trimmed to land exactly on it. The transition begins as soon as the running attack ends (immediately, if it is
  interruptible). Phase II can therefore never be skipped by burst damage.
* **PHASE_TRANSITION** — untouchable; bespoke choreography; then PHASE_2 with the boss's Phase II parameters, shortened
  remaining cooldowns and a 20 % shorter gap between attacks.
* **DEATH** — the lethal hit is refused and the entity is kept alive at its last health point, untouchable, so the death
  sequence plays on the real entity. Every pending hazard and helper is removed first. Afterwards rewards are granted and
  the entity becomes a **remnant**: a native timer despawns it 30 s later.
* **RESET** — with no participant left, the boss walks back to the centre and waits; after 20 s the encounter is
  abandoned: the boss is removed and its Seal is dropped at the arena centre.

### 3.2 Arena

An encounter's arena is pure data: the summoning point, a floor height and a radius (or half-size for Nomos's square
arena). **No block is ever placed, removed or changed by an encounter.**

* A Seal first scans the location: a grid of samples must find solid floor at one level with two blocks of air above
  it over at least 70 % of the footprint, plus the boss's head room at the centre, with all chunks loaded. If not, the
  summon is refused with the reason and the required size, and the Seal is kept.
* A second encounter cannot be started so close that the arenas could interfere.
* The boss is leashed inside the arena; a per-second safety check returns it if it ever leaves the volume.
* Players are *participants* while they are alive, not spectators, inside the arena (plus a 5-block margin) and within
  4 blocks below / 14 above the floor. Hazards only ever affect participants.
* Damage dealt to the boss by a player who is not a participant is ignored (and the player is told why).
* The optional demonstration arenas are ordinary structures placed only by an explicit, confirmed operator action.

### 3.3 Players and multiplayer

* One server-side tick loop advances every encounter, so nothing is scheduled per player.
* **Health scaling**: effective health = base × (1 + 0.45 × (players − 1)), capped at four players. It follows the peak
  number of simultaneous participants — it grows when someone joins mid-fight and never shrinks when someone leaves or
  dies. It is implemented by scaling incoming damage, so the native health bar stays truthful as a fraction.
* **Focus**: threat accrues from damage dealt and decays ~3 % per second. The focus changes only when another player
  exceeds the current one by 30 % and at least 5 s have passed, or when the focus dies, leaves or disconnects. Several
  attacks deliberately pick other participants (each boss chapter says which).
* Area hazards hit each participant at most once per strike, and a participant cannot be damaged by the same encounter
  more than once per 10 ticks, so overlapping hazards never multiply damage.
* Players joining mid-fight see the correct state because pose, phase and armour are synced entity properties.
* Encounters are keyed by boss entity and confined to their own arena; any number can run in different places or
  dimensions.

### 3.4 Damage dealt to the boss

Processed in `world.beforeEvents.entityHurt` (stable in 2.11.0), in this order:

1. refused while untouchable (intro, transition, death) and for environmental causes (fall, fire, lava, suffocation,
   drowning, cactus, lightning, …); explosions count 30 %;
2. refused from non-participants and from the boss's own helpers;
3. boss-specific handling (Vesperra's armour, etc.);
4. `damageTaken` (see §5) and the multiplayer / difficulty scale;
5. capped at 4 % of maximum health per hit;
6. the phase gate and the death hold described above.

### 3.5 Damage dealt to players

Vanilla Bedrock mitigation removes about 96 % of a hit for a player in Protection IV diamond, which would make every
telegraphed attack irrelevant for the reference loadout and lethal for everyone else at the same number. Hazard damage
is therefore computed by the add-on and applied exactly:

```
final = design damage × difficulty × (1 − mitigation)
mitigation = min(40 %, 2 % × armour points) + min(20 %, 1.25 % × total Protection levels), then Resistance (15 % / level, max 60 %)
             — never more than 75 % in total
```

Full enchanted diamond therefore takes 40 % of the design damage, iron about 70 %, no armour 100 %.

Application: a one-point native hit first supplies what the engine does well (hurt flash and sound, attribution to the
boss, shields for *blockable* attacks, invulnerability frames, armour wear); health is then set to
`before − final`. A hit that would kill is delivered as a single overwhelming native hit instead, so death messages
and Totems of Undying behave normally. Creative and spectator players are never damaged.
Known consequence: absorption hearts are bypassed by the exact-health step (the Script API does not expose them).

### 3.6 Telegraphs and hazards

Every hazard is a `Shape`. The telegraph is drawn from the shape and, when the warning ends, the *same* shape is
tested against the participants — a marked region and a damaging region cannot disagree.

* **Danger** marks are solid, pulsing marks in the boss's own colour and sprite, drawn as outlines plus a fill that
  grows until the strike. **Safe** marks ("stand here") are pale, hollow, non-pulsing lozenges. The two differ in
  shape, motion and fill as well as colour.
* The name of the attack being telegraphed is shown on the action bar.
* Moving hazards (waves, sweeping limbs, projectiles) are re-evaluated every 1–2 ticks at the position the visual has
  reached; projectile sprites fly at the same constant velocity the server uses.
* Nothing depends on sound: every audio cue has a visual counterpart.
* Fairness rule, enforced by test: for every attack in both phases, a player who walks (4.3 blocks/s, no sprinting,
  no jumping) and reacts 0.3 s after a telegraph appears can avoid all damage.
* Telegraphs are parametric particle emitters — one network message draws a whole line or arc — so even the
  largest pattern costs a few dozen particle calls.

### 3.7 Cancellation and cleanup

Everything delayed is a task on the owning encounter's timeline, tagged with the attack that created it. There is no
`system.runTimeout` anywhere in the fight code. Consequently:

* interrupting an attack removes every strike of it that has not happened yet;
* the boss's death, a reset, abandonment, the boss unloading or being killed by command each end the encounter by
  cancelling the whole timeline, removing helpers and clearing per-player state;
* helper entities are capped (12 per encounter, lower per kind), tagged, expire on a script timer, carry a native
  despawn timer as well, and a 10-second sweep removes any helper whose encounter no longer exists.

### 3.8 Persistence

The boss entity is the save file: one JSON dynamic property holds arena centre, phase, scale and boss-specific
values (e.g. plate health). In-flight attacks are deliberately not persisted — after a reload or a chunk reload the
boss resumes idle in the correct phase with no hazard pending. World settings are one world dynamic property.

### 3.9 Movement

Bosses carry no native AI goals; the encounter steers them (`core/locomotion.ts`): the horizontal velocity is set each
tick and the engine's physics handles gravity, stepping and collision; the body turns at a limited rate and walks
along its facing. A stepwise teleport mode is selectable in the Codex as a fallback. Leg animation is driven on the
client by distance travelled and yaw turned, so it matches whatever the server actually did.

### 3.10 Health display

* **Native**: each boss has the engine's `minecraft:boss` component, which shows the boss bar with its name.
* **Scripted**: an action-bar line — name, phase, health, current attack — refreshed twice a second for participants.
  It is a scripted indicator, not a boss bar, and can be turned off in the Codex.

## 4. Access

| | |
|---|---|
| Seals | four items in the Creative inventory and craftable; use one on a level, open floor |
| Codex | `abm:codex` — reads about each Miracle; for operators: settings, optional arena placement, dismiss |
| Commands (operator, cheats) | `/abm:summon <boss>`, `/abm:arena <boss>`, `/abm:dismiss`, `/abm:debug <on\|off\|phase2\|kill\|attack n\|info>` |
| Script events | `/scriptevent abm:summon <boss> [force]`, `abm:dismiss`, `abm:arena <boss>` — for command blocks and NPCs |
| Entities | `/summon abm:vesperra`, `abm:cantor_xiii`, `abm:nomos`, `abm:orison` are adopted into an encounter automatically |

Bosses never spawn naturally (no spawn rules, `is_spawnable: false`).

## 5. Tuning

`src/config.ts` is the central file. Per-attack numbers live in `src/bosses/<boss>/tuning.ts`; beat timings in
`shared/<boss>.timings.json`.

| Parameter | Value | Meaning |
|---|---|---|
| base health | 480 / 520 / 560 / 600 | Vesperra / Cantor XIII / Nomos / Orison (native entity health) |
| Phase II threshold | 45 % / 50 % / 40 % / 35 % | |
| `damageTaken` | 0.10 / 0.125 / 0.125 / 0.128 | share of incoming weapon damage that reaches the boss (Vesperra / Cantor XIII / Nomos / Orison) |
| `hpPerExtraPlayer` | 0.45 | health scaling per additional participant (max 4) |
| `maxHitFraction` | 0.04 | largest share of health one hit can remove |
| difficulty | story / **normal** / hard | damage ×0.6 / 1 / 1.3, health ×0.75 / 1 / 1.25, attack gap ×1.35 / 1 / 0.8 |
| `baseAttackGap` | 26 ticks | idle time between attacks (×0.8 in Phase II) |
| `playerHitIntervalTicks` | 10 | minimum time between hits on one player |
| `resetGraceTicks` | 400 | time with no participants before the encounter is abandoned |
| `minFloorCoverage` | 0.7 | floor quality needed to summon |
| `vfx.density` | 1.0 (0.5 reduced) | decorative particles only; telegraphs are never reduced |

**Why `damageTaken` exists.** The brief's base health (480–600) and its 4–7 minute target are not reachable together
for the reference loadout without it: an enchanted diamond sword removes roughly 25 health per second from an
undefended target, so 480 health would last about twenty seconds. `damageTaken` scales incoming damage so that the
health numbers stay as specified while the simulated solo fight lands in the intended range. It is one number per boss.

**Caveat for multiplayer.** Bedrock entities ignore hits for half a second after being hurt, so several players
hitting at once do not add their damage linearly. The health scaling above follows the brief's formula; it may need
lowering after real four-player tests.

## 6. Asset pipeline

Everything in the packs is generated by code in `tools/` and is original.

* **Geometry** (`kit/geo.py`): bones and cubes described in Python, per-face UVs packed into an atlas, written as
  `minecraft:geometry` 1.12.0 and as an editable Blockbench `.bbmodel` (`assets/blockbench/`). Axis and UV conventions
  follow Blockbench's Bedrock exporter (checked against its source).
* **Textures** (`kit/paint.py`): painters receive both face coordinates and the 3-D position of every texel, so glaze
  streaks, patina and grime continue across neighbouring faces.
* **Animation** (`kit/anim.py`, `kit/molang.py`): procedural motion is written in a small Molang DSL that both
  serialises to the game's syntax and evaluates numerically, so previews show the pose the game computes; keyframed
  motion is authored against the shared beat timings and baked to linear keys.
* **Particles** (`kit/particles.py`): each boss has its own sprite sheet and effects; telegraph emitters are
  parameterised by the script.
* **Audio** (`kit/sfx.py`): every sound is synthesised (oscillators, noise, FFT filters, synthetic reverb) and encoded
  as mono Ogg Vorbis.
* **Arenas** (`kit/arena.py`, `kit/nbt.py`): `.mcstructure` files limited to long-stable blocks, validated against the
  vanilla catalogue.
* **Previews** (`kit/render.py`, `kit/iso.py`): a software renderer; its images are asset previews, not screenshots.

Budgets enforced by the validator: ≤ 480 cubes and ≤ 120 bones per model, textures ≤ 512², audio ≤ 12 MB,
steady emitters ≤ 600 particles.

## 7. Decisions worth knowing about

| Topic | Decision | Why |
|---|---|---|
| Body-part damage (Vesperra) | scripted ray / point classification against oriented boxes | the engine reports no hit location; attached hitbox entities lag, desync and can be orphaned |
| Death sequence | lethal hit held in the before-event, sequence plays on the live entity, native timer removes the remnant | a natively dying mob cannot play a multi-second staged collapse |
| Phase gate | health trimmed to the threshold | guarantees the transformation is seen and gives it a protected window |
| Boss movement | script-steered velocity, no pathfinding | deterministic positioning; large mobs path poorly |
| Player damage | add-on-computed mitigation, exact application | vanilla armour makes boss damage either irrelevant or lethal |
| Telegraph rendering | parametric emitters | exact agreement with hit shapes at minimal network cost |
| Hourglass transparency (Orison) | `entity_alphablend` material on dedicated bones | genuinely supported; no PBR or shader claims |
| "Shifting space" (Nomos) | a logical coordinate grid of hazards | the world is never rotated, rewritten or re-mapped |
| "Time" (Orison) | bounded position history + scheduled events | nothing reverses or pauses the simulation |
