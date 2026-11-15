# Ability & Control Reference

## Controls (identical on touch, keyboard/mouse and controller)

| Action | Touch | Keyboard & mouse | Controller |
|---|---|---|---|
| **Cast** the selected ability | Hold the **Focus** item, tap / hold on the screen (*use*) | Right-click | Left trigger |
| **Select next** ability | Sneak, then use the Focus | Shift + right-click | Sneak (right stick) + left trigger |
| Open the **Lineage Codex** | Use the Codex item | Right-click the Codex | Left trigger |
| Uproot early (Salamander) | Jump | Space | A / Cross |
| Thump & Listen (Jackalope) | Sneak and stand still 1 s | Hold Shift, don't move | Sneak, don't move |
| Cancel a channel (Root, Bastion) | Use the same ability again | | |

* The Focus is locked to your inventory (cannot be dropped or stored) and kept on death. Lost it anyway? Codex > **Recall Focus**.
* Using the Focus on a block casts too, except on interactive blocks (doors, chests, crafting tables, levers ...), which open normally.
* `/plrace:codex` opens the Codex anywhere.

**Why this scheme:** it needs one hotbar slot, never replaces attack/mine/place/eat, works the same on every input device, and needs no JSON-UI changes (cooperative add-ons may not modify the HUD). Mining, block placing, combat, eating, shields, bows, elytra and every other vanilla action keep their normal controls.

### HUD (action bar, while holding the Focus)

```
[Snare] | Embrace 12s | Root | Jet          <- abilities: green = ready, grey + seconds = recovering,
Hydration ||||||||||.. 84% Blooming gills       [brackets] = selected, pink = active channel
```
Line 2 is the race resource. Failed casts show the reason in red (no target, conditions) and **never spend the cooldown**. Targeted abilities draw a green reticle on the creature they will hit (only you see it).

---

## 001 · Aberrant Flora Salamander — เผ่าสลาแมนเดอร์พืชประหลาด

| Ability | Cooldown | Effect | Original brief |
|---|---|---|---|
| **Sundew Snare** | 14 s | Glandular filaments hit the aimed creature up to **8 blocks** (10 while Blooming): 2 damage, **Slowness III 4 s**, dragged toward you, **Ensnared 5 s**. | 15 s, ~8 blocks, slow ~4 s |
| **Carnivorous Embrace** | 22 s | Forearm trap-lobes snap on a creature within 3.5 blocks: **6 damage, 9 if Ensnared**, held (Slowness V 1 s); you heal **40% of damage dealt** (min 1 heart). | 25 s, close bite, heals a little |
| **Root Metamorphosis** | 30 s | Rooted up to **6 s**: heal 1.5 HP/s, **-40% damage**, no knockback, +5 hydration/s on soil; cannot walk. **JUMP** uproots early. | 35 s, stationary regen + resistance |
| **Bladder Jet** | 16 s | **In water:** rocket ~10 blocks where you look; creatures within 3.5 blocks are shoved and slowed. **On land:** costs 20% hydration — hop-dash, douse fire, spray enemies in front back. | 18 s, water propulsion + push |

Cooldowns are **20% faster while Blooming** and **40% slower while Dormant**.

**Passives**
* **Hydration 0-100%:** water +10/s · rain under open sky +4/s · water/mud/moss underfoot +1.2/s · humid biomes (swamp, mangrove, jungle, lush caves, river, beach, ocean) +0.4/s · normal land −0.3/s (−0.45 in direct sun) · deserts/badlands/savanna −1.2/s (−1.8 in sun) · Nether −2.5/s · burning −3/s extra · water bottle (any potion) +40%.
* **Blooming:** hydration ≥ 70% **and** in water, rain, sunlight or rooted. Plates unfurl, faster cooldowns, longer Snare, photosynthesis heals 1 HP every 4 s.
* **Stable:** photosynthesis 1 HP every 8 s in daylight under open sky; +1 hunger every 24 s in the sun.
* **Dormant:** hydration ≤ 15% (recovers at 32%). Slowness I, no photosynthesis, slower cooldowns, but **-15% damage taken**.
* **Fern Gills:** Conduit Power when submerged (breathing, underwater vision, haste); **+70% swim speed** (+100% Blooming) with ≥ 30% hydration.
* **Adhesive Pads:** fall damage -40%. **Weakness:** fire/lava damage +25%.
* Crest armour: 2 (iron-helmet equivalent).

---

## 002 · Runic Titan Golem — เผ่าไททันรูนโกเลม

| Ability | Cooldown | Effect | Original brief |
|---|---|---|---|
| **Titan's Edict** | 18 s | Arm-stones fuse into a hammer (**Siege**), slam at 0.6 s: a shockwave travels **~8 blocks forward**, 9 damage near → 5 far, launches and pushes, Slowness II 2 s. Rune strain 12. | 20 s, hammer, directional shockwave |
| **Runic Bastion** | 28 s | Slabs lock in front (**Bastion**) for **5 s**: hits from the front 150° **-70%**, frontal **projectiles blocked**; other hits -30%; no knockback; slowed while braced. Use again to drop it. Strain 8. | 30 s, frontal defence |
| **Glyph Dominion** | 34 s | Stones form an **Arcane** formation and inscribe a **6-block rune circle** for **8 s**: enemies inside Slowness III + 1 damage/s; enemies crossing the rim from outside are hurled back (2 damage); you (and friendly players when PvP is off) are **Warded** (-15% damage). Needs aligned runes. Strain 15. | 35 s, slow inside, repel approach |
| **Colossus Reassembly** | 38 s | Burst into fragments (**untouchable**), stream up to **12 blocks** toward your aim, reform on solid footing; the reconstruction blast hits within 4 blocks for 6 + knockback. Needs aligned runes. Strain 18. | 40 s, separate + reconstruct + burst |

**Passives**
* **Basalt Body:** +4 hearts (Health Boost II); melee, projectile, contact, falling-block damage **-25%**; explosions -15%; falls -50%.
* **Rune-Bound Mass:** knockback from hits is cancelled; landing from 4+ blocks cracks the ground (3 damage + throw, radius 2.8).
* **No Breath:** never drowns; heavy — Slowness I on land, Slowness II in water and steady sinking (walks the seabed).
* **Rune Stability 0-100%** (the golem's mind): regenerates **2%/s** (4%/s in Monolith Stance). Lost to magic/wither/lightning/sonic damage (×4 per point), thunderstorms under open sky (−3.5/s), a lightning strike within 8 blocks (−45 to −70), and ability strain. **Below 25% the runes are DISRUPTED** until they recover to **50%**: Glyph Dominion and Reassembly are locked, cooldowns +25%, the body visibly misaligns and the glyphs burn red.
* **Monolith Stance:** stand still 3 s: -10% damage, faster stability recovery.
* Crest armour: 3 (diamond-helmet equivalent).

---

## 003 · Blood Moon Jackalope — เผ่าแจ็คคาโลปดวงจันทร์สีเลือด

| Ability | Cooldown | Effect | Original brief |
|---|---|---|---|
| **Lunar Bound** | 10 s | Spring ~7 blocks in the direction you are moving (forward if still), crescent-moon trail; no fall damage from it; next hit within 0.7 s halved. Distance +7% per resonance level. **2 charges** under the Blood Moon. | 12 s, directional leap, crescent trail |
| **Antler Brand** | 18 s | Lower the antlers and charge ~5 blocks: the first enemy hit takes 5 and gets a **Lunar Sigil for 8 s**. | 20 s, charge, mark ~8 s |
| **Velvet Mirage** | 28 s | Shed an illusory duplicate and spring away. Nearby hostile mobs are provoked into chasing it; whatever strikes it is **dazzled** (Blindness + Slowness II, 3 s). **Velvet Step:** the next attack within 2 s misses you. Lasts 5 s (7 s under a new moon or Blood Moon). | 30 s, duplicate ~5 s, diverts attacks |
| **Crimson Waltz** | 42 s | Target within 10 blocks (sigil-marked first): **4 blink-leaps** around it (6 under the Blood Moon), each a crimson antler crescent (4 damage, 6 vs marked), then a full-moon cross slash (6, 9 vs marked) that launches it. You take **-50% damage** while waltzing. Blood Moon: slashes also wither and heal you 20%. | 45 s, leaps around target, crescent attacks |

**Lunar Sigil:** your melee hits on the marked enemy deal **+3**; Crimson Waltz prefers it and deals +50%; if it **dies marked**: your other cooldowns **-4 s** and **Speed II 3 s** (*Moonhunt*); under the Blood Moon the sigil **detonates** for 4 when it expires.

**Passives**
* **Lunar Resonance 0-4:** day 0 · night by moon phase — crescent/quarter 1, gibbous 2, full 3, new moon 0 · Blood Moon 4 · Nether/End 0 (no moon). Each level: cooldowns -6%, Lunar Bound +7%.
* **Hare Legs:** Speed I; Jump Boost I by day / II at night; falls deal 50% − 2 (none right after a leap).
* **Moonlit Hearing:** at night (and in the Nether/End) hostile mobs within 18-30 blocks show a silver ping only you see; your ears warn you when something is behind you.
* **Thump & Listen:** sneak still for 1 s → the Listening pose reveals every hostile within 40 blocks for 6 s (12 s internal cooldown).
* **Fragile Frame:** melee damage taken +10%. Crest armour: 1.
* **Blood Moon Awakening:** see below.

### The Blood Moon event
* **When:** only on **full moon** nights. Each full moon rolls the world's chance (default **34%**); after **3 full moons without one, the next is guaranteed**. Full moons come every 8 in-game days, so a Blood Moon appears about every 24 in-game days (≈ 8 real hours of play), at most every 32.
* **Duration:** from moonrise (time 13000) until dawn (23460) — about 8.7 real minutes. Sleeping through the night or `/time` ends it cleanly.
* **Omen:** at dusk players see *"The full moon is rising... red"*; at moonrise *"THE BLOOD MOON RISES"*.
* **Effects:** a crimson distance fog for overworld players (vanilla `/fog` stack, removed afterwards; can be disabled), and every Jackalope in the overworld **awakens**: extra antler tines, raised dorsal fur, crimson veins and red eyes; Speed II, resonance 4, two Bound charges, blood sigils, longer mirages, life-stealing waltz.
* **Persistence:** the event state is saved with the world; reloading during a Blood Moon resumes it, and it still ends at dawn.

---

## Commands and operator settings

| Command | Who | Purpose |
|---|---|---|
| `/plrace:codex` | everyone | Open the Lineage Codex |
| `/plrace:setrace <salamander\|golem\|jackalope\|001\|002\|003\|none> [players]` | operators | Assign or remove a lineage |
| `/plrace:resetcooldowns [players]` | operators | Testing |
| `/plrace:bloodmoon <start\|stop\|next\|status>` | operators | Start/stop now, force the next full moon, show the schedule |

Codex > **World Settings** (operators): abilities can harm players (also requires the `pvp` game rule) · lineage changes *Free / Cooldown (days) / Operators only* (default: once every 3 in-game days) · Blood Moon chance · Blood Moon fog · auto-open selection for new players · always-on HUD.

Other Codex pages: **Veil / Manifest Form** (hide your racial body to wear a normal helmet; powers stay), **Infuse Crest** (dissolve an enchanted book with a helmet enchantment into your crest; it keeps the enchantment through every transformation), **Rite of Unbecoming** (change lineage or return to an ordinary body), **Lineage Archive**.
