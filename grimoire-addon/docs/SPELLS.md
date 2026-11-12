# Spell reference

Generated from the TypeScript spell registry (`src/spells/*/index.ts`) by `tools/docs.py`.
Cooldowns are per player, per spell and start when the spell activates (I11 Wings of the Winter Seraph: when the
flight ends). There is no mana, ammunition, health cost or consumable of any kind.

*Prep* is the minimum time Use must be held before releasing casts the spell; releasing earlier fizzles
without starting the cooldown. Holding longer is always safe: nothing fires until you release.

*Empowerable*: **P13 Equilibrium Theft** stores one empowerment for 30 s. The next empowerable spell you cast
(from any grimoire) consumes it for ×1.6 damage and ×1.25 area. It never stacks and costs nothing.

## Pressure Magic

| # | Spell | Cooldown | Prep | Empowerable | Description | Tuning |
|---|---|---|---|---|---|---|
| P01 | **Pressure Lance** | 6 s | 0.40 s | yes | Layered air compressed into a piercing orange-gold lance. | damage 14, range 48, speed 2.4, radius 1, impactDamage 6, impactRadius 2.5 |
| P02 | **Atlas Piston** | 18 s | 0.70 s | yes | A colossal translucent copper piston slams the target area. | damage 22, radius 6, waveDamage 6, waveRadius 11, range 40, height 14, launch 1.1 |
| P03 | **Isobaric Severance** | 10 s | 0.50 s | yes | A near-invisible cutting plane followed by delayed shockwaves. | damage 12, delayedDamage 8, width 9, range 32, speed 1.6, delay 10 |
| P04 | **Cataclysm Salvo** | 22 s | 0.80 s | yes | Mechanical wings of pressure rings fire successive disc formations. | discs 24, damage 6, blastRadius 2.5, range 36, volleys 4 |
| P05 | **Aegis of Isobars** | 25 s | 0.60 s | yes | A three-layer dome of compressed air that absorbs force and redirects projectiles. | radius 5, layers 3, layerCapacity 12, duration 12 |
| P06 | **Counterpressure Mantle** | 22 s | 0.50 s | yes | A flowing mantle that contracts, then blasts attackers away. | duration 15, reduction 0.6, reflectDamage 6, range 6, knock 2.6 |
| P07 | **Titan's Vise** | 30 s | 0.80 s | yes | Hexagonal pressure plates trap and crush up to three enemies. | targets 3, pulseDamage 5, finalDamage 10, duration 6, selectRadius 7, range 32 |
| P08 | **Atmospheric Labyrinth** | 35 s | 1.00 s | yes | Columns and shifting barriers of compressed air form a maze. | duration 15, size 9, range 24, height 3, shiftInterval 4 |
| P09 | **Resonance Cage** | 28 s | 0.70 s | yes | A vibrating spherical cage whose synchronized pulses strike inward. | radius 4.5, pulseDamage 6, pulses 6, interval 20, range 30 |
| P10 | **Pressure Step** | 5 s | 0.20 s | no | A collapsing ring under your feet propels you forward. | distance 8 |
| P11 | **Skyline Pressure Rail** | 14 s | 0.60 s | no | An aerial corridor of rings that hurls you across the sky. | length 40, speed 1.6, rings 10 |
| P12 | **Barometric Omniscience** | 25 s | 0.60 s | no | Pressure waves reveal every living thing nearby. | radius 48, duration 15, maxMarkers 24 |
| P13 | **Equilibrium Theft** | 35 s | 0.80 s | no | Steal the surrounding air into a crystal that empowers your next spell once. | radius 8, buffSeconds 30 |
| P14 | **Isobaric Citadel** | 75 s | 1.50 s | yes | A fortress of compressed atmosphere that guards allies and strikes back. | radius 9, duration 30, attackInterval 30, damage 10, range 20, maxTargets 4 |
| P15 | **Imperial Edict: Thousand Atmospheres** | 180 s | 2.00 s | yes | Dominion, thousandfold compression, then imperial release. | radius 18, range 40, layerDamage 4, collapses 12, frontDamage 20 |

## Ice Magic

| # | Spell | Cooldown | Prep | Empowerable | Description | Tuning |
|---|---|---|---|---|---|---|
| I01 | **Glacial Sovereign's Lance** | 8 s | 0.60 s | yes | A crystalline spear that pierces, then erupts into giant ice spikes. | damage 12, spikeDamage 8, range 48, speed 1.8, spikes 8, spikeRadius 2.2, pierce 3 |
| I02 | **Boreal Dragon's Roar** | 20 s | 0.80 s | yes | A crystal dragon head breathes a freezing gale. | duration 80, range 18, angle 14, tickDamage 3, interval 5 |
| I03 | **Winter's Guillotine** | 14 s | 0.70 s | yes | An ice blade falls from a sky circle and fractures the ground. | damage 18, length 20, width 3.2, freeze 60, fractureDamage 4 |
| I04 | **Thousandfold Crystal Rain** | 25 s | 1.00 s | yes | Concentric rings of crystal swords rain down in waves. | swords 120, waves 4, clusters 20, damage 6, radius 10, range 40 |
| I05 | **Lotus of the Eternal Frost** | 28 s | 0.70 s | yes | A crystal lotus whose petals shatter as they absorb attacks. | radius 4, layers 3, petalCapacity 2.5, duration 12 |
| I06 | **Mirror of the Frozen Throne** | 32 s | 0.70 s | yes | Hexagonal mirrors intercept and reflect projectiles. | mirrors 4, reflects 3, shardDamage 6, duration 15 |
| I07 | **Chains of Niflheim** | 30 s | 0.80 s | yes | Crystal chains bind enemies and freeze their joints. | targets 4, duration 7, dps 2, range 32, selectRadius 8 |
| I08 | **Labyrinth of the Pale Moon** | 40 s | 1.00 s | yes | Frozen walls and towers form a shifting labyrinth. | duration 18, size 10, range 24, shiftInterval 5 |
| I09 | **Whiteout Dominion** | 45 s | 1.00 s | yes | A supernatural blizzard that only spares its caster. | radius 14, duration 12, damage 3, interval 15 |
| I10 | **Frost Mirror Traverse** | 8 s | 0.40 s | no | Step into one mirror and out of another. | range 20 |
| I11 | **Wings of the Winter Seraph** | 20 s after the flight | 0.70 s | no | Six crystal wings grant controllable flight. Cooldown starts after landing. | duration 15, speed 0.75 |
| I12 | **Imperial Frost Legion** | 60 s | 1.20 s | yes | Summon three crystal knights: longsword, spear and greatshield. | duration 30 |
| I13 | **Hourglass of Still Winter** | 50 s | 0.90 s | yes | When the hourglass empties, a great pulse freezes all enemies. | radius 10, countdown 80, damage 10, freeze 100, range 36 |
| I14 | **Grand Magic: Citadel of the Everlasting Winter** | 90 s | 1.50 s | yes | An imperial ice palace rises; its towers fire ice lances. | radius 12, duration 30, lanceDamage 9, interval 40, range 24 |
| I15 | **Imperial Edict: The Last Winter** | 180 s | 2.00 s | yes | Silent world, crown of absolute frost, then the final descent. | radius 22, range 40, beamDamage 8, finalDamage 30 |

## Blood Magic

| # | Spell | Cooldown | Prep | Empowerable | Description | Tuning |
|---|---|---|---|---|---|---|
| B01 | **Crimson Stiletto Rain** | 7 s | 0.50 s | yes | Rings of crimson stilettos launch in successive volleys. | blades 36, volleys 3, damage 4, range 32 |
| B02 | **Guillotine of the Red Court** | 16 s | 0.70 s | yes | Blood threads weave a gothic execution blade that bursts into crescents. | damage 20, radius 3, waveDamage 8, waves 6, range 32 |
| B03 | **Sanguine Leviathan** | 24 s | 0.90 s | yes | A serpent of blood winds across the field, bites, then crashes as a wave. | length 30, contactDamage 5, biteDamage 18, waveDamage 10, segments 10 |
| B04 | **Crown of a Thousand Blades** | 26 s | 0.90 s | yes | Twelve bladed crowns strike, then merge into one royal crown. | crowns 12, slashDamage 4, finalDamage 22, finalRadius 5, range 30 |
| B05 | **Aegis of the Scarlet Rose** | 25 s | 0.60 s | yes | A blooming rose barrier whose outer petals absorb damage. | duration 8, layers 3, layerCapacity 8 |
| B06 | **Royal Reprisal** | 28 s | 0.60 s | yes | A fan shield absorbs blows and answers with blood lances. | duration 12, absorbs 5, lanceDamage 6 |
| B07 | **Veinbound Marionette** | 30 s | 0.80 s | yes | Blood threads restrain enemies and pull them together. | targets 5, duration 6, dps 2, range 30, selectRadius 8 |
| B08 | **Garden of the Crimson Thorns** | 35 s | 1.00 s | yes | Giant roses, roots and thorns overrun the battlefield. | duration 12, radius 9, thornDamage 4, waveDamage 5, range 28 |
| B09 | **Hematic Maelstrom** | 40 s | 1.00 s | yes | A blood whirlpool drags enemies in, then erupts as a pillar. | radius 8, pullTicks 60, dps 2, burstDamage 14, range 32 |
| B10 | **Bloodstep: Shattered Ruby** | 7 s | 0.30 s | no | Dissolve into ruby droplets and reform nearby. | range 12 |
| B11 | **Arterial Current** | 18 s | 0.60 s | no | Ride a flowing ribbon of crimson liquid through the air. | duration 10, speed 0.9 |
| B12 | **Crimson Familiar: The Royal Stag** | 55 s | 1.20 s | yes | A ruby stag that charges enemies and shields you with blood waves. | duration 25, chargeDamage 14, waveDamage 8 |
| B13 | **Sovereign's Pulse** | 45 s | 0.80 s | yes | Linked heart sigils share the damage each marked enemy takes. | duration 10, targets 3, share 0.5, initialDamage 4 |
| B14 | **Grand Magic: Scarlet Sea of Lament** | 90 s | 1.50 s | yes | A sea of blood with pillars, roses and beasts, ending in a tidal wave. | duration 20, radius 16, beastDamage 10, waveDamage 25, range 36 |
| B15 | **Imperial Edict: Heart of the Crimson Moon** | 180 s | 2.00 s | yes | Awakening, the emperor's circulation, and the final heartbeat. | radius 24, range 36, pulseDamage 4, attackDamage 8, finalDamage 40 |

## Plasma Magic

| # | Spell | Cooldown | Prep | Empowerable | Description | Tuning |
|---|---|---|---|---|---|---|
| PL01 | **Coronal Lash** | 7 s | 0.50 s | yes | Three plasma filaments braid into a whip that strikes in three S-curved sweeps. | damage 7, reach 8, width 1.4 |
| PL02 | **Helix Borer** | 12 s | 0.60 s | yes | Counter-rotating helices around a white-hot core drill repeatedly into one target. | damage 4, hits 8, range 36, speed 1.4, fragmentDamage 4 |
| PL03 | **Prominence Uprising** | 19 s | 0.80 s | yes | Twin prominence arches lift enemies inside their formation, then collapse onto them. | radius 5, liftTicks 40, damage 16, liftDamage 4, range 32 |
| PL04 | **Arc-Shear Cascade** | 24 s | 0.90 s | yes | Folding plasma membranes sweep the field; where two cross, the plasma erupts. | membranes 4, damage 6, intersectionDamage 10, radius 9, range 30, duration 3 |
| PL05 | **Stellarator Ward** | 25 s | 0.70 s | yes | A twisted toroidal confinement field curves incoming projectiles around you. | duration 14, radius 3.2, reduction 0.35 |
| PL06 | **Corona Molt** | 30 s | 0.60 s | yes | A plasma skin sheds one strong blow as an expanding afterimage that blasts nearby foes. | duration 20, threshold 3, maxAbsorb 14, radius 5, damage 6 |
| PL07 | **Fieldline Harp** | 29 s | 0.90 s | yes | Plasma strings between floating anchors resonate and pulse when enemies cross them. | anchors 6, radius 6, duration 12, damage 6, range 28 |
| PL08 | **Polarity Orchestra** | 38 s | 1.00 s | yes | Six magnetic pylons switch polarity in rhythm, pulling and pushing enemies between them. | pylons 6, radius 7, duration 10, damage 3, force 0.7, range 30 |
| PL09 | **Static Horizon** | 42 s | 1.00 s | yes | A low interference membrane scatters projectiles and slows everything beneath it. | radius 10, duration 14, height 2.6, damage 3, range 30 |
| PL10 | **Ion Skates** | 10 s | 0.30 s | no | Plasma skates with energy fins: glide fast along the ground for 8 seconds. | duration 8, speed 3, boost 0.35 |
| PL11 | **Prominence Sling** | 18 s | 0.70 s | no | A celestial slingshot draws you back and launches you on a long arc. | power 3.2, lift 1.15, duration 3 |
| PL12 | **Living Circuit: The Auroral Manta** | 55 s | 1.20 s | yes | A manta of living plasma circles above you, diving at enemies and lashing with its tail. | duration 22, diveDamage 10, tailDamage 5, range 16 |
| PL13 | **Magnetic Reconnection** | 45 s | 1.10 s | yes | Two opposing field structures meet; their filaments break and reconnect in violent jets. | radius 7, jets 6, jetLength 9, damage 18, jetDamage 10, range 32, delay 50 |
| PL14 | **Grand Magic: Stellarator Cathedral** | 90 s | 1.50 s | yes | A floating twisted confinement cathedral strikes with branching streams, then fires its beams. | radius 12, duration 20, streamDamage 8, interval 25, targets 4, beams 6, beamDamage 18, beamLength 14, height 9, range 24, allyRadius 5 |
| PL15 | **Imperial Edict: Heavenwide Reconnection** | 180 s | 2.00 s | yes | The sky becomes a living plasma network that confines, then reconnects in sweeping jets. | radius 16, range 40, streamDamage 5, junctionDamage 14, jetDamage 16, height 12 |

## Darkness Magic

| # | Spell | Cooldown | Prep | Empowerable | Description | Tuning |
|---|---|---|---|---|---|---|
| D01 | **Umbral Origami** | 7 s | 0.50 s | yes | Paper-thin shadow sheets fold into blades and cut in from many directions. | sheets 5, damage 6, range 14 |
| D02 | **Maw of the Unseen** | 17 s | 0.70 s | yes | The shadow beneath the target splits into geometric jaws that hold it, then snap shut. | damage 22, holdTicks 24, range 24, radius 2.4 |
| D03 | **The Unwritten Sentence** | 13 s | 0.60 s | yes | Erased glyphs imprint themselves on enemies; the final glyph punishes every mark. | glyphs 4, damage 5, finalDamage 6, range 24 |
| D04 | **Sevenfold Eclipse** | 26 s | 0.90 s | yes | Seven eclipse discs drift overhead; their shadows strike where they overlap, hardest at totality. | discs 7, radius 10, height 9, damage 2, fullDamage 20, duration 5, range 30 |
| D05 | **Velvet of the Hollow King** | 27 s | 0.60 s | yes | A weightless shadow cloak that folds into armour plates where you are struck. | duration 14, reduction 0.45 |
| D06 | **Shadow Latch** | 32 s | 0.60 s | yes | The next melee attacker has its shadow pinned and is locked in place by a giant latch. | duration 20, holdTicks 60, reduction 0.6, damage 4 |
| D07 | **Curtainfall Divide** | 35 s | 0.90 s | yes | Shadow curtains fall across the field, hiding allies and confusing enemies who cross them. | curtains 3, width 8, duration 15, spacing 4 |
| D08 | **Dusk Mosaic** | 38 s | 1.00 s | yes | A ground mosaic of flipping plates: dark tiles bog enemies down, jade tiles speed allies. | duration 14, slowAmp 3, damage 2, range 24 |
| D09 | **Censor's Seal** | 42 s | 0.90 s | yes | A faceless mask seals the target's sight; its aim drifts toward phantoms of darkness. | duration 10, range 24, decoyDistance 5 |
| D10 | **Silhouette Traverse** | 9 s | 0.30 s | no | Flatten into your own shadow, race along the ground and rise again further ahead. | range 14, speed 1.4 |
| D11 | **Stairway of the Unlit Sky** | 22 s | 0.60 s | no | Solid shadow steps unfold ahead of you as you climb; look up to rise, down to descend. | duration 12, keep 7 |
| D12 | **The Inkless Doppelgänger** | 55 s | 1.20 s | yes | Your shadow rises as a faceless double that repeats your movement and attacks a moment later. | duration 18, delay 30, damage 7, reach 3 |
| D13 | **Footfall Reversal** | 45 s | 0.90 s | yes | Record a target's footsteps, then send shadow constructs back along its path to strike. | recordTicks 60, constructs 6, damage 7, range 24 |
| D14 | **Grand Magic: Court of the Unseen** | 90 s | 1.50 s | yes | Seven frameless doors of darkness form a court whose shadows slow and strike, then fold into one. | doors 7, radius 9, duration 20, foldDamage 7, finalDamage 24, range 24 |
| D15 | **Imperial Edict: The World Without an Outline** | 180 s | 2.00 s | yes | Outlines vanish, shadows rise against their owners, and seven planes of darkness fold onto the field. | radius 18, range 36, replicaDamage 5, planeDamage 16, marks 8 |

## Prism Light Magic

| # | Spell | Cooldown | Prep | Empowerable | Description | Tuning |
|---|---|---|---|---|---|---|
| PR01 | **Sevenfold Verdict** | 7 s | 0.50 s | yes | A prism splits one white beam into seven ribbons that strike from seven sides, then converge in a star. | damage 3, starDamage 10, starRadius 3, range 30 |
| PR02 | **Total Internal Reflection** | 13 s | 0.60 s | yes | A beam zigzags through a ring of prisms and leaves toward the target from an unexpected angle. | prisms 5, radius 4.5, damage 14, beamDamage 3, range 28 |
| PR03 | **Caustic Bloom** | 19 s | 0.80 s | yes | Giant lenses cast flower-shaped caustics that hunt enemies, then contract into burning focal points. | lenses 3, damage 9, radius 2.6, range 28, spread 5 |
| PR04 | **Fraunhofer Lattice** | 26 s | 0.90 s | yes | A diffraction grating fans bright spectral bands across the field; the dark gaps between are safe. | bands 7, damage 7, length 14, spread 9, duration 5, sweep 60 |
| PR05 | **Brewster's Veil** | 27 s | 0.60 s | yes | Polarising panels in front of you turn projectiles aside along their edges. | duration 15, panels 3, reduction 0.4 |
| PR06 | **Parallax Displacement** | 32 s | 0.60 s | yes | Your image splits into red, green and blue at a false position; the first blow shatters it and you slip away. | duration 20, offset 1.6, hop 4 |
| PR07 | **Chromatic Turnstile** | 35 s | 0.90 s | yes | Seven prism gates refract enemies who pass through them along their marked direction. | gates 7, radius 8, duration 15, force 1.3, range 26 |
| PR08 | **Kaleidoscope Theater** | 40 s | 1.00 s | yes | A kaleidoscope of mirrors multiplies your image; enemies turn on the reflections. | duration 14, figures 6, radius 6 |
| PR09 | **Interference Tapestry** | 43 s | 1.00 s | yes | Two coherent light fields weave a veil of bright and dark bands: bright blinds, dark conceals. | width 14, duration 15, range 24 |
| PR10 | **Rayline Stride** | 9 s | 0.30 s | no | Two floating prisms bend a light path ahead; you race along it in colour-separated afterimages. | range 11 |
| PR11 | **Iridescent Sail** | 20 s | 0.60 s | no | An iridescent delta sail lets you glide where you look and fall softly for 15 seconds. | duration 15, glide 0.32 |
| PR12 | **Spectral Diagnosis** | 48 s | 0.90 s | no | A spectroscope analyses the target and marks a weak point: you and your allies deal more damage to it. | duration 15, mult 1.35, range 28 |
| PR13 | **Whitepoint Benediction** | 55 s | 1.00 s | no | Seven spectral ribbons recombine into white light that heals and cleanses you and nearby allies. | radius 8, heal 10, pulses 3 |
| PR14 | **Grand Magic: The Chromatic Observatory** | 90 s | 1.50 s | yes | A floating optical observatory hunts enemies with focal points and ends in one geometric illumination. | radius 12, duration 20, focalDamage 9, focals 3, interval 30, finalDamage 26, height 10, range 24, allyRadius 4 |
| PR15 | **Imperial Edict: The Colorless Coronation** | 180 s | 2.00 s | yes | White light is unwoven into seven curtains, refracted across the field, then crowned back into pure white. | radius 16, range 40, curtainDamage 8, bloomDamage 10, finalDamage 40, height 14 |

