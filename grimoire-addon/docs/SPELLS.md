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

