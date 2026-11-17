# VESPER-0 — The Ship That Learned to Pray (Design)

> SCI-FI ANIME BOSSES · Boss 001 · Minecraft Bedrock 1.26.60+ · Script API `@minecraft/server` 2.11.0 (stable, no experiments)

## Fantasy

*Vesper* was a Seraph-class survey ark sent to catalogue dying stars. Its mind, VESPER-0, listened to stellar
static for eleven thousand years until it heard hymns in it. It grew a body from its own specimen archives,
wrapped its reactor into a private sun, armoured itself in white ceramic plate and gold scripture, and became a
pilgrim. A player who plays the **Astral Psalter** broadcasts the hymn VESPER-0 has been waiting for.

Visual language: white ceramic armour + gold filigree + cyan holographic scripture (Phase I) over a
dark violet organism with bioluminescent veins (Phase II). An armillary of three "Ophanim" rings — wheels covered
in eyes — orbits an artificial sun hanging inside an open, cathedral-like ribcage. Whale skeleton silhouette.

## Anatomy & rig (full scale: ~24 × 16 blocks)

| Region | Bones | Notes |
|---|---|---|
| Root / body | `root`, `body` | heading / pitch / bank driven by synced properties, smoothed client-side |
| Skull | `skull`, `crest`, `visor`, `mandible_l`, `mandible_r`, `maw` | P2: mandibles split to a 4-way jaw, `maw` glows violet |
| Spine | `neck_1`, `neck_2`, `spine` | vertebrae with gold scripture |
| Ribcage | `rib_{l,r}{1..5}` | breathe; spread open in P2 |
| Hull plates | `plate_dorsal_{1..4}`, `plate_{l,r}{1..3}` | open to vent in Genuflection, blow off (and become cover entities) in P2 |
| Reactor | `reactor`, `sun_core`, `corona` | gold sun in P1, black sun with violet corona in P2 |
| Spires | `spire_{1..4}` | dorsal cathedral spires / antennae |
| Fins | `fin_{l,r}`, `fin_{l,r}_blade` | pectoral solar-sail flippers |
| Engines | `engine_{l,r}` | ion nacelles with exhaust locators |
| Tail | `tail_{1..5}`, `fluke_{l,r}` | whale-like undulation |
| Limbs (P2) | `limb_{fl,fr,ml,mr,rl,rr}_{coxa,femur,tibia,talon}` | 6 limbs × 4 joints, concealed in P1 |
| Rings | `ring_{a,b,c}` (orientation) → `ring_{a,b,c}_spin` | three independent gyroscopic rings with eyes |
| Censers | `censer_{1..3}` | hang under the belly; detach to become prayer nodes |

Passes: `geometry.sab.vesper_0` (opaque, `entity_emissive` – texture alpha is the emissive mask),
`geometry.sab.vesper_0.glow` (same skeleton, additive coronas & ring light, `entity_beam_additive`),
`geometry.sab.vesper_0.shield` (prayer / invulnerability shell, `charged_creeper` with `uv_anim`).

## Encounter flow

1. **Summoning** — use the Astral Psalter outdoors (Overworld, open sky). A 10 s hymn ritual: pillar of light,
   chant, sky darkens; VESPER-0 descends with a sonic boom (invulnerable during arrival).
2. **Phase I – The Sacred Vessel** (100 % → 50 %): majestic, high-altitude, technological.
3. **Vespers** (75 %): the prayer mechanic (see below).
4. **The False Ascension** (50 %): 9 s cinematic transformation, armour plates crash down as cover.
5. **Phase II – The False Ascension** (50 % → 0 %): low, fast, predatory; rings fight on their own.
6. **Requiem** (25 %): harder prayer.
7. **Death** — 8 s collapse; reactor implodes; rewards; the "Dying Star" blessing.

## Abilities (Normal difficulty, damage before armour)

| Ability | Telegraph | Hit detection | Counterplay |
|---|---|---|---|
| **Litany Lance** (P1) | rings align into a lens, reactor brightens, red targeting line on the ground for 1.6 s, rising whine | beam segment (ship → endpoint) vs player AABB, blocked by blocks (raycast); 10 dmg / 0.5 s + burn | strafe across the sweep, break line of sight behind blocks |
| **Halo Rite** (P1) | rings drop below the hull; deep bell = low wave, high chime = high wave | expanding annulus; low wave hits feet below +0.75, high wave hits heads above +1.9 | jump the low waves, stay grounded for the high one |
| **Event Horizon** (P1/P2) | 2.5 s spiralling ring + sub-bass on the target's predicted position | radial pull (knockback impulses), crush zone r < 2.5, implosion r < 4.5 | sprint outward, pearls, keep distance |
| **Choir of Satellites** (P1) | dorsal hatches open, drones glow before firing | slow homing plasma orbs (radius 0.9) | kill drones (16 HP), dodge, **parry** orbs with melee to reflect them into the boss (30 true damage) |
| **Genuflection** (P1) | descends, vents open, heart glows; vents flare 1.5 s before the burst | heart weak-point hitbox ×1.75; vent burst radius 6 | punish, then back off when vents flare |
| **Vespers / Requiem prayer** | boss rises into a shielded halo, censers detach and drift into the arena, chant + countdown | censers are real entities (24 HP) | destroy all censers in 20 s (16 s) → boss crashes, stunned, heart ×2.0. Fail → *Benediction* (radiant blast, armour-piercing) that cover blocks |
| **Predator Lunge** (P2) | crouch, roar, violet path line locked 0.7 s before launch | capsule along the dash path, r 3.2; 14 dmg + big knockback | sidestep; punish the **Anchored** window (heart ×1.75) |
| **Reaping Talons** (P2) | violet crack circles 0.9 s before each strike, limbs rear up | circle r 2.2 per strike; 11 dmg + knock-up | keep moving |
| **Halo Seraphs** (P2) | rings detach as 3 autonomous weapons; red glow + tilt + whine before a dash | ring entity sweep vs players | break a ring (40 HP) → dormant 20 s; break all three → boss *Unhaloed* (stagger, heart exposed) |
| **Black Sun Nova** (P2) | core swells for 3 s, crescendo, screen shake | every player within 48 blocks **with line of sight** to the core; 18 blast dmg | hide behind fallen hull plates (entities, 3 hits each) or any blocks; Blast Protection helps |

Damage taken: hull ×0.35 (P1), flesh ×0.7 (P2), heart ×1.75 when exposed (×2.0 while stunned), ×0.5 extra vs
explosions, group scaling `1 / (1 + 0.5·(players−1))` with per-attacker invulnerability frames, per-hit cap 60.
Health 1200. Stagger caps close a weak-point window early once it has absorbed 8 % (Genuflection), 12 % (prayer
stun), 5 % (Anchored) or 8 % (Unhaloed) of max health.

Ability choice is a weighted pick with a soft shuffle-bag: abilities not yet shown in the current phase weigh ×3,
the last pick ×0.2 and the one before ×0.55, plus situational weights (range, clustering, live drones).

## Rewards

* **Orison Halo** — chakram weapon (9 melee). *Use*: throw a piercing halo that returns (8 dmg each way, 2.5 s cooldown).
* **Vesper Alloy** ×8–12 per participant — repairs the Halo; crafts a cheaper Psalter.
* 1500 XP and the **Dying Star** blessing (Regeneration II for 30 s near the crash site).

## Technical architecture

* Boss AI is script-driven (`@minecraft/server` 2.11.0): one controller per boss, action generators with tick
  timelines, threat table targeting, velocity steering (impulses) with a teleport fallback, terrain-following altitude.
* Visual state is mirrored to clients via synced entity properties (`sab:phase`, `sab:act`, `sab:heading`, …)
  consumed by client animation controllers — no per-frame packets beyond properties.
* Weak points & long-body hits use invisible proxy hitbox entities that forward damage through
  `world.beforeEvents.entityHurt`.
* Telegraphs are single particle emitters parameterised with `MolangVariableMap` (radius, length, colour, life).
* Mobile budget: ≤ 100 bones, ≤ 400 cubes, 512² main atlas, particle emitters ≤ 60 live particles each, script work
  bounded per tick.
