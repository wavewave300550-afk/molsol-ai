# Ability & Control Reference

## Controls (identical on touch, keyboard/mouse and controller)

| Action | Touch | Keyboard & mouse | Controller |
|---|---|---|---|
| **Cast** the selected ability | Hold the **Focus** item, tap / hold on the screen (*use*) | Right-click | Left trigger |
| **Select next** ability | Sneak, then use the Focus | Shift + right-click | Sneak (right stick) + left trigger |
| Open the **Lineage Codex** | Use the Codex item | Right-click the Codex | Left trigger |
| Uproot early (Salamander) | Jump | Space | A / Cross |
| Thump & Listen (Jackalope) | Sneak and stand still 1 s | Hold Shift, don't move | Sneak, don't move |
| Stillness (Xenentoma) | Sneak and stand still 2 s | Hold Shift, don't move | Sneak, don't move |
| Noodle Parachute (Spaghetti Monster) | Hold sneak while falling | Hold Shift while falling | Hold sneak while falling |
| End Root / Bastion early; withdraw HYAKUTEN CHŪKŌ (half the cooldown back during its first 2 s) | Press use again (after 0.6 s) | Right-click again | Left trigger again |

* **Five abilities for the Unique lineage.** Nurariten cycles through five (the fifth is its ultimate); everything else is the same.
* **One action per press.** Holding the button does nothing extra; it never re-casts and never interrupts an ability in progress.
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
| **Runic Bastion** | 28 s | Slabs lock in front (**Bastion**) for **5 s**: hits from the front 150° **-70%**, frontal **projectiles blocked**; other hits -30%; no knockback; slowed while braced. Press again (after 0.6 s) to drop it. Strain 8. | 30 s, frontal defence |
| **Glyph Dominion** | 34 s | Stones form an **Arcane** formation and inscribe a **6-block rune circle** for **8 s**: enemies inside Slowness III + 1 damage/s; enemies crossing the rim from outside are hurled back (2 damage); you (and friendly players when PvP is off) are **Warded** (-15% damage). Needs aligned runes. Strain 15. | 35 s, slow inside, repel approach |
| **Colossus Reassembly** | 38 s | Burst into fragments (**untouchable**), stream up to **12 blocks** toward your aim (straight ahead along the ground if you aim at the sky or at your feet), reform on solid footing; the reconstruction blast hits within 4 blocks for 6 + knockback. Needs aligned runes. Strain 18. | 40 s, separate + reconstruct + burst |

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

## 004 · Xenentoma — เซเนนโทมา

*"It does not see the world. It feels it move."* An eyeless six-limbed arthropod (~1.75 blocks) after the real proturans: sensory forelimbs held up like antennae, manipulative middle limbs that hold items, segmented walking legs, twelve abdominal segments, false eyes (pseudoculi) and a retractable feeding stylet. Resource: **Sensory Clarity**. Crest armour 2.

| Ability | Cooldown | Effect | Original brief |
|---|---|---|---|
| **Foretarsal Survey** | 15 s | Forelimbs raised: read every vibration within **12 blocks for 5 s**. Moving creatures ping clearly at their *approximate* position, still ones only within 5 blocks (7 in darkness), sneaking players within 3. Felt creatures are **sensed** for 7 s (Surge +25%). In the air the radius halves and positions blur. Not while Overloaded. | 15 s, ~12 blocks, ~5 s, approximate positions |
| **Exuvia Proxy** | 28 s | Step out of your own exoskeleton: the **shed exuvia** (your shape) stays 8 s, provokes nearby hostiles and soaks up to 16 damage; whatever strikes it is sensed. You spring away with **Speed II** as a soft **teneral** body (+20% damage for 4 s), then the new cuticle hardens (**Resistance I 6 s**). | 28 s, functional shell decoy, molting escape |
| **Interstitial Glide** | 18 s | Flatten and slide **~5 blocks** along the ground where you look; creatures slipped past are tripped (2 damage, Slowness II 2 s); half damage while flat. Real movement: walls, doors and builds stop it. Needs ground or water. | 18 s, ~5 blocks, flattened, no wall clipping |
| **Anamorphic Surge** | 40 s | The twelve segments telescope out one by one, the abdomen arches over the back and strikes **three times** along your aim (6.5-block reach): **4, 4, 6** damage, +25% vs sensed; the last strike injects through the stylet (Weakness 4 s, Slowness 2 s, knockback). | 40 s, sequential extension, reach, multiple timed impacts |

**Passives**
* **Vibration Sense:** on ground or in water, moving creatures within 8 blocks (10 standing still, +4 in darkness) send faint rings only you see; the HUD names the strongest tremor's direction. Airborne creatures and sneaking players are hard to feel. *Not a wallhack:* close range, approximate, ground-borne only, nothing is outlined.
* **Eyeless:** Blindness and Darkness have no effect (your screen never goes permanently dark).
* **Stillness:** sneak motionless 2 s → perfectly still (Invisibility while you stay still) — quieter than any other lineage.
* **Six-Point Landing:** fall damage −30%.
* **Sensory Clarity 0–100%:** explosions within 14 blocks and nearby lightning scramble it; **below 25% you are Overloaded** (no Vibration Sense, no Survey, cooldowns +20%) until it recovers to 60%. Recovers 4%/s (8%/s standing still).
* **Weaknesses:** explosions hurt 15% more and overload the senses; senses fail in the air; fragile right after moulting.

---

## 005 · Flying Spaghetti Monster — สปาเกตตีมอนสเตอร์บินได้

*"Ridiculous. Impossible. Extremely well engineered."* A hovering mass of living spaghetti (~1.1 blocks wide, ~1.7 tall with its eyestalks), exactly two meatballs, two eyes on independent stalks, sauce that flows where it pleases (including up), and noodle appendages that braid into arms only when it holds something. Resource: **Sauce**. Crest armour 1.

| Ability | Cooldown | Effect | Original brief |
|---|---|---|---|
| **His Noodly Touch** | 15 s | Noodles lash out up to **7 blocks** (5 while brittle). An enemy is wrapped: 3 damage, **pulled in** and held (Slowness IV 1.5 s). A friendly player (PvP off) is **blessed**: Regeneration 4 s, Slowness/Weakness/Poison/Mining Fatigue removed. Nothing alive in reach: the strands **gather dropped items** in front of you. SAUCY: 5 damage, 2.5 s hold. | 15 s, ~7 blocks, grab/restrain/pull items, extend & retract |
| **Al Dente Reversal** | 22 s | Every strand snaps rigid into a lattice of dry spaghetti for 2.5 s: **−60% damage**, **projectiles stopped outright**, the first melee attacker is **countered** (4 damage + thrown back). SAUCY: 3.5 s, 6-damage counter. | 22 s, rigid block + counter |
| **Meatball Ricochet** | 28 s | Both meatballs tear free (tethered by noodles) and ricochet between enemies within 10 blocks: up to **3 strikes each** (4 damage, sauce splash), preferring different targets, then return. While they are away you take **+20% damage**. SAUCY: 4 strikes each. | 28 s, bounce between targets & return, defensive trade-off |
| **The Great Pasta Revelation** | 50 s | The body unfolds into **three rotating spiral layers**, meatballs orbiting in opposite directions, eyestalks raised. For 3.3 s enemies within 9 blocks are **dragged in** and lashed (1 damage / 0.5 s); then a **sauce shockwave**: 8 damage within 5.5 blocks, thrown outward, Slowness II + Weakness 3 s. You are slowed but take −30% damage while unfolded. SAUCY: 11 damage. | 50 s, spiral vortex, opposite-orbit meatballs, pull + shockwave, anatomical not generic |

**Passives**
* **Noodly Float:** hovers a hand's breadth above the ground (visual; *not* flight). Hold **sneak while falling** to spread the strands and drift down (**Noodle Parachute**).
* **Elastic Form:** fall damage −50%.
* **Dual-Eye Awareness:** one eye always watches your back — a hostile creature behind you within 6 blocks is pointed out.
* **Flexible Appendages:** tools, weapons, shields and food work normally; strands braid into arms only while you hold something.
* **Sauce 0–100%:** +2%/s, +15% for any meal, +40% for stews, soups, bread, baked potatoes and cooked meat. At 100% the next ability is **SAUCY** (empowered). Burning boils it away.
* **Weaknesses:** fire makes the pasta **brittle** (+25% fire damage, 25% slower cooldowns, shorter reach); softer while the meatballs are away; lightest armour.

---

## 006 · Nurariten — นูราริเทน · ✦ UNIQUE ✦

*"It was never invited. It was always expected."* The Uninvited Sovereign (~1.95 blocks): the yokai Nurarihyon — who walks into a house at its busiest hour and is taken for its master — as an imperious celestial aristocrat. Elongated cranium curving back, an ivory mask of a face with narrow golden slit-pupil eyes, a fragmented floating halo, layered collars, long sleeves that hide slender fingers, ivory / aged gold / vermilion robes, and an architecture of halos and a gate folded on its back that unfolds into a court or a throne-palace. Crest armour 2.

**Unique lineage:** by default **only one player per world** can hold it (operators can change this). Becoming Nurariten is announced to the world; the claim is stored with the world and released by the Rite of Unbecoming, by assigning another lineage, or by `/plrace:unique release nurariten`. It is the only lineage with **five abilities** (the fifth is its unique ultimate), a full system of its own (**Divine Jurisdiction**) and a relationship with the sun.

### Divine Jurisdiction
* **Judgment marks (1–3):** a golden seal above a creature's head (its size shows the count), 12 s after the last refresh. Applied by the Edict, the Temple (every 3 s inside), the Proclamation and the Throne; consumed by **Imperial Expulsion** and the **Final Edict**. Each Nurariten sees and consumes only its own marks.
* **Courts:** temporary circles of authority (the Temple, and the ultimate's court). A court **never changes or claims blocks**, protects nothing and lasts seconds. Inside its own court the Sovereign deals +20% and takes −15% damage.

| Ability | Cooldown | Effect | Original brief |
|---|---|---|---|
| **Unannounced Arrival** | 18 s | You are simply there: step up to **12 blocks** along your gaze to a safe spot you can see (never through walls, never onto lava/fire/cactus/powder snow or into the void). Gates of light mark departure and arrival; creatures within 3.5 blocks of the arrival are **pushed aside** and slowed. Arriving **under a roof that is not yours**, you are received as its master (Absorption 8 s). **Dusk: 2 charges.** | 18 s, safe teleport + push |
| **Edict of the Lowered Gaze** | 25 s | Two fingers leave the sleeve: every enemy in a **70° cone within 9 blocks** bows — staggered back, **Weakness II** 5 s (7 s at midday), **Slowness II** 2.5 s, **+1 mark**. Creatures are made to look at the ground for a moment; **players are never camera-locked** and there is no flashing. | 25 s, forward stagger/weaken, no prolonged forced camera |
| **The Uninvited Temple** | 35 s | The back architecture unfolds (1 s declaration) and the ground becomes your **court**: a 7-block circle of walking pillars of light with a gate at its edge, for 10 s (13 s at dusk). Enemies inside are slowed and gain a mark every 3 s; inside it you deal +20%, take −15% and cooldowns run 20% faster. **Interrupted** by a 4+ damage hit (or 6 in total) during the declaration → half the cooldown returned. Leaving the court **breaks** it (Weakness 4 s). | 35 s, temporary court, slow + marks, no land seizure/griefing |
| **Imperial Expulsion** | 40 s | Point at one creature within 12 blocks (aim assist prefers judged ones): **5 damage +3 per mark** (consumed), knocked far away (farther per mark), slowed. Expelled from inside your court: **+3 damage** and **barred from re-entering for 6 s** (turned back at the threshold). | 40 s, synergy with temple and marks |
| **HYAKUTEN CHŪKŌ** 百天昼行 *(unique ultimate)* | 180 s | ขบวนร้อยสวรรค์ยาตรายามทิวา — the Hundred Heavens' **daytime procession**, a heavenly answer to the Night Parade of a Hundred Demons. 10 s, you stand still: **I The Sky Must Open** (0–2 s) a vast gate opens in the sky ahead; a 5+ damage hit (or 8 in total) interrupts you (half the cooldown back, Broken Mandate) — or press use again to withdraw. **II The Proclamation** two heralds descend with the decree: every enemy within 16 blocks is judged (+1) and bows (Slowness II). **III The Hundred Heavens March** eight columns of attendants (96 figures; with the two heralds, the gate and you: one hundred) circle and close in, trampling (2 damage) and herding enemies toward you. **IV The Throne Without Permission** your court becomes a throne-palace: Resistance II + Regeneration for you; enemies within 12 Weakened, slowed, judged. **V The Final Edict** one finger rises, the seals converge: every enemy within 14 takes **4 +4 per mark (max 16; +25% at midday)** and is thrown down. Then everything dissolves; the world is exactly as it was. | 180 s, five stages, real combat consequences, full restoration, no 100 AI mobs, day/night relationship without changing world time |

**Passives**
* **Royal Presence:** hostile creatures that come within 5 blocks (6 at midday, 4 at night) falter (Slowness I 1.5 s, once per creature per 8 s). Subtle on purpose — never lasting control, never on players.
* **Celestial Bearing:** fall damage −40%; never dizzied (Nausea removed).
* **Uninvited Authority:** the court bonuses above; **indoors near villagers it is received as the master of the house** (Hero of the Village I).
* **Solar Mandate (the sun):**

| Time | Effect |
|---|---|
| Day | cooldowns −15% |
| Midday (game time 4500–7500) | cooldowns −15%, Lowered Gaze lasts 7 s, the Final Edict +25%, Royal Presence reaches 6 blocks |
| Dusk (11500–13500) — *the hour of visiting* | Unannounced Arrival holds 2 charges; the Temple stands 3 s longer |
| Night | the **Nocturne Radiance** form (the halo glows); Royal Presence reaches only 4 blocks; HYAKUTEN CHŪKŌ brings a private daylight haze to its witnesses |
| Nether / End | no sun: no solar bonuses |

  The world's time, sky and weather are **never** changed. The ultimate's golden haze is a vanilla `/fog` entry pushed only for players within 40 blocks and removed afterwards (also on logout, reload and death), plus one soft golden screen fade for players within 18 blocks — both can be switched off in World Settings.
* **Weaknesses:** **Judicial Weakness** (its preparations can be interrupted), **Arrogant Posture** (+15% damage from behind; it does not dodge like a jackalope or endure like a golem), **Broken Mandate** (leaving its own court, or an interrupted ultimate: Weakness and 15% slower cooldowns for a few seconds), the ultimate roots it for 10 s.

---

## Commands and operator settings

| Command | Who | Purpose |
|---|---|---|
| `/plrace:codex` | everyone | Open the Lineage Codex |
| `/plrace:setrace <salamander\|golem\|jackalope\|xenentoma\|spaghetti\|nurariten\|001…006\|none> [players]` | operators | Assign or remove a lineage (a Unique lineage already held by someone else is refused) |
| `/plrace:resetcooldowns [players]` | operators | Testing |
| `/plrace:bloodmoon <start\|stop\|next\|status>` | operators | Start/stop now, force the next full moon, show the schedule |
| `/plrace:unique <status\|release> [race]` | operators | Show who holds each Unique lineage / free a Unique lineage (e.g. after its holder left the server for good) |

Codex > **World Settings** (operators): abilities can harm players (also requires the `pvp` game rule) · lineage changes *Free / Cooldown (days) / Operators only* (default: once every 3 in-game days) · Blood Moon chance · Blood Moon fog · auto-open selection for new players · always-on HUD · **Unique lineages: one holder per world** (default on) · **HYAKUTEN CHŪKŌ screen effects** (golden haze + one soft fade; default on).

Other Codex pages: **Veil / Manifest Form** (hide your racial body to wear a normal helmet; powers stay), **Infuse Crest** (dissolve an enchanted book with a helmet enchantment into your crest; it keeps the enchantment through every transformation), **Rite of Unbecoming** (change lineage or return to an ordinary body), **Lineage Archive**.
