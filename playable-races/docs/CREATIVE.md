# Creative Development Report

This report maps every part of the original brief to what was built, and lists additions and every significant change with its reason. Nothing from the brief was silently dropped; where something could not be done literally, the replacement is named.

---

## The big decision: bodies without overriding the player

The brief asked for genuinely playable creatures *and* warned that Mojang's cooperative guidelines discourage overriding `minecraft:player` or player skins. The usual "morph" approach (replacing `player.json` and `player.entity.json`) conflicts with other add-ons and silently breaks whenever Mojang changes player animations.

**What was built instead:** each racial body is a **head-slot crest whose attachable copies the player's skeleton**. The creature rides on the player's real animated bones, so it automatically walks, swims, sneaks, rides, sleeps, glides and draws bows exactly as the player does — today and after future updates — while its own anatomy (tails, gills, plates, ears, antlers, rune rings) is animated on top. The player's skin is hidden by a one-condition override of a single vanilla render controller, only while a form is manifested. (Details and trade-offs: [COMPATIBILITY.md](COMPATIBILITY.md).)

Turning that constraint into design:
* **States are bodies.** Every biological state or configuration is a different crest item with its own geometry and transition animation (15 forms). Abilities physically rebuild the creature rather than just playing particles.
* **Veil / Manifest.** Because the form lives in the helmet slot, players can *veil* it — keep their powers and wear a turtle shell or a carved pumpkin — and manifest it again later. It turned a limitation into a disguise mechanic.
* **Crest Infusion.** The crest can absorb enchanted books (Protection, Respiration, Thorns …), so late-game players lose nothing by keeping their form manifested.
* **Armour Assimilation** *(addition)*. Vanilla armour does not fit a 2.4-block stone titan or a digitigrade hare, so it is hidden on manifested forms and the creature grows its own plates per worn slot, tinted by the armour's material (leather, chain, iron, gold, copper, diamond, netherite, turtle). The armour still protects normally.

---

## 001 · Aberrant Flora Salamander — เผ่าสลาแมนเดอร์พืชประหลาด

**Identity kept:** an organism that is simultaneously amphibian, photosynthesiser, predator and ecosystem; plant organs are working anatomy, not decoration.

| Brief element | Delivered |
|---|---|
| ~1.8 blocks | 30.7 model units → 1.8 blocks after the player scale |
| Broad flattened skull, large amber eyes, wide mouth to the cheeks | 11-wide flat cranium with an overhanging snout, dorsolateral bulging amber eyes (glowing irises, slit pupils), a dark lip line wrapping to the cheeks, hinged lower jaw with small teeth and a pale gular pouch |
| Moist, glossy, translucent skin; dark green-black; purple-red vascular patterns | Procedural 3-D skin: mottled green-black, wet specular glints on top surfaces, ridged-noise purple-red vein network running continuously across body parts, sparse yellow-green **algae spots** (spotted-salamander nod) |
| Branching gills like carnivorous leaves, responsive | Three feathery gill stalks per side with cross-plane fronds and red glandular filaments; they pulse with breathing, stream back when moving or swimming, flare when hurt, tuck when dormant |
| Thick photosynthetic back plates that move with meaning | Eight hinged plates (two rows) that **roll open by state** (dormant 8° → stable 34° → bloom 62° → rooted 70°), **track the sun's elevation through the day**, and open further when the creature stands still in sunlight (sunbathing) |
| Arms with adhesive glands, tendrils, prey organs | Glands along the forearm, two **Venus-trap lobes** with ciliated rims (snap open in the Predatory state), hanging sticky tendrils with dew drops that **extend** when hunting, broad digit pads |
| Translucent abdomen with fluid sacs and vascular channels | Real depth: a cut-out membrane over a recessed cavity containing glowing fluid sacs and vascular channels |
| Broad digits, adhesive pads, retractable roots | Splayed toes with pale pads that spread on ground contact; roots that grow out of the soles in the Rooted form |
| ~1-block tail with leaf fins and an opening flower | Four-segment tail (~1.1 blocks) with dorsal/ventral leaf fins and a five-petal flower that opens (bloom) and closes (dormant) |
| Blooming / Predatory / Dormant states | Implemented as visual forms **and** gameplay states (see ABILITIES.md). Predatory is a short combat state after Snare/Embrace; Bloom/Stable/Dormant follow a **hydration** meter with hysteresis so states do not flicker |
| Snare / Embrace / Root / Jet | All four, values close to the brief (cooldowns trimmed slightly for pace) |
| Animations: idle, walk, run, swim, sunbathing, hunting, rooting, dormancy | Idle breathing and gill pulse; tail sway and torso flex scaled by speed; toe spread on contact; travelling tail wave while swimming; sun tracking/sunbathing; snapping lobes/jaw and extending tendrils (predatory); root growth intro; 2.2 s wilting intro for dormancy; bloom unfurling intro; flinch; cast poses for every ability |

**Additions:** the **Ensnared** combo (Snare → Embrace bites 50% harder), photosynthesis that also restores hunger, Conduit Power gills, rain/wet-ground/humid-biome hydration, drinking water bottles, Rooted hydration from soil, a land version of Bladder Jet that costs hydration and douses fire, adhesive pads (fall damage -40%), fire weakness, "Dormant Resilience" (-15% damage so dormancy is a trade-off, not just a punishment), ambient spores, pollen and dew drips from the creature itself.

**Changed:** *Dolphin's Grace* does not exist in Bedrock — swimming speed uses the underwater-movement attribute instead (+70%, +100% Blooming). Root Metamorphosis' cooldown starts when you root (30 s) so its effective downtime matches the brief's 35 s.

## 002 · Runic Titan Golem — เผ่าไททันรูนโกเลม

**Identity kept:** living architecture whose mind is its runes; stones are organs; movement and combat are acts of rebuilding.

| Brief element | Delivered |
|---|---|
| ~2.4 blocks | 2.4–2.6 blocks to the crest stones; hitbox stays vanilla (engine limit) |
| Sculpted head, rune-shaped glowing eye openings, no human face | Monolith head with brow ridge, cheek plates and crest stones; eyes are glowing rune glyphs (slit + stem + tick), a faint mouth seam; it follows your look direction from its own neck pivot |
| Massive asymmetrical basalt torso with empty space around the chest | Separated pillars (the right side heavier), arch, lintel and back masses frame an open chest cavity |
| Core: three concentric rotating rune rings + suspended crystal | Three ring bones built from rotated segments spinning on X, Y and Z at different speeds around a bobbing double crystal; rune wall glyphs behind it |
| Oversized asymmetrical arms of disconnected floating stones | Shoulder boulders, floating upper-arm fragments, massive forearms and knuckled fists, separated by glowing rune seams, with pebbles orbiting each forearm; the fist encloses the vanilla grip so held items sit in it |
| Heavy stone-column legs | Stacked hip/thigh/knee/shin/plinth stones with glowing seams and foot runes |
| Dark basalt, aged gold fractures, glyphs, weathering | Columnar-jointed basalt, weathered edges, pits, moss in crevices, *kintsugi* gold fractures, procedurally generated rune glyphs (emissive) |
| Siege / Bastion / Arcane configurations | Real geometry configurations with transition animations: the right arm's stones (plus the absorbed left forearm) **become a hammer**; back slabs and shoulders **swing to the front and interlock**; slabs, satellites and eight glyph tablets **lift into an orbiting rune ring** |
| Edict / Bastion / Dominion / Reassembly | All four. The shockwave visibly travels; Bastion is directional; Dominion's circle is readable (ground decal + glyph pillars) and actually repels; Reassembly scatters the whole body |
| Animations: idle hover & rings, heavy walk, streamlined run, jump runes, attack reconstruction, damage flicker, reassembly | Rings/crystal/satellites/slabs hover; pelvis and hips settle with each step; sprinting tucks shoulders/satellites/slabs back; foot runes appear and fragments rise when airborne; the arms rebuild into the hammer; hits make fragments lose alignment; the 1-second burst-and-converge reassembly |

**Rune disruption (designed, as requested):** a **Rune Stability** meter that everyone can read on the HUD. Magic-type damage, lightning, thunderstorms under open sky, wither and the golem's own ability strain erode it; below 25% the runes are **Disrupted** (arcane abilities locked, slower cooldowns, misaligned body and red glyphs) until they recover to 50%. It makes witches, lightning and spamming abilities meaningful counterplay without ever disabling the physical kit.

**Additions:** Monolith Stance (stand still: tougher, faster rune recovery), heavy landing shockwave, cancelled knockback, sinking and seabed walking, water breathing underwater, glyph burn inside the circle and "Warded" allies, invulnerability while scattered, armour bands for assimilation, rune motes and sparks from the core.

**Changed:** the brief listed "strong resistance to physical attacks" and "high durability" — implemented as +4 hearts and -25% physical damage rather than permanent Resistance, so magic remains a real threat and the golem never trivialises survival.

## 003 · Blood Moon Jackalope — เผ่าแจ็คคาโลปดวงจันทร์สีเลือด

**Identity kept:** unmistakably a jackalope even with every effect off; agile, eerie, lunar; locomotion is identity.

| Brief element | Delivered |
|---|---|
| ~1.65 blocks | head top ≈ 1.6 blocks; ears and antlers rise above it |
| Elongated hare face, small nose, prominent front teeth | Long lavender-grey muzzle, twitching nose (its own bone), two incisors, cheek fur, whiskers |
| Two branching obsidian antlers with deep-red channels that can change | Three-segment beams with brow and outer tines and a glowing red channel; **four extra tines grow** during the Blood Moon |
| Long, independently animated ears with crimson inner veins | Two-segment ears with separate idle rhythms, random twitches, a listening pose, streaming back when running, pinned when hunting; inner surfaces with glowing crimson vein patterns |
| Silver eyes, red when empowered | Silver emissive irises; red while hunting and under the Blood Moon |
| Slender black-indigo body with curved silver markings | Directional fur strands; silver **crescent** markings on the haunches; chest ruff |
| Functional hands | Paws with digits at the vanilla grip point |
| Powerful hare hind legs | Digitigrade thigh/shin/long-foot chain (forward-kinematics solved so the feet plant) |
| Round fluffy tail with red markings | Scut with a ring marking that ignites when hunting/awakened |
| Ordinary vs Blood Moon Awakening | Four forms (base, hunt, awakened, awakened-hunt) and a world event with a defined rarity, duration and activation (ABILITIES.md) |
| Bound / Brand / Mirage / Waltz | All four, with mechanics that make each matter (see below) |
| Animations: idle ears/nose, cautious walk, bounding run, jump crouch & push-off, landing compression, listening, antler attack, Blood Moon transformation | Idle ears/nose/tail; walking reduces the human stride and leans the torso; **sprinting cancels the human leg swing and replaces it with a synchronised bound** (thighs, shins and feet flex together, body rises and pitches); push-off extension when rising, legs reach when falling; a landing controller compresses the legs; the Listening pose (sneak still); head-down antler charge pose; 1.8 s awakening: tines grow one after another, dorsal fur rises, head tilts back to the moon, crimson spiral |

**Mechanics that give each ability real function:**
* **Lunar Sigil** (Antler Brand): +3 melee damage, Waltz priority and +50%, **Moonhunt** cooldown refund on kill, Blood Moon detonation.
* **Velvet Mirage:** a real 1-HP decoy entity with the `player` family, so mobs that hunt players pursue it; nearby hostiles are provoked into attacking it; whoever strikes it is dazzled; the caster gets a guaranteed dodge.
* **Crimson Waltz:** blink-leaps that land on safe ground around the target, ending in a launching cross slash; damage reduction while dancing.
* **Lunar Resonance:** a 0–4 scale tied to the real moon phase, not just day/night.

**Additions:** Moonlit Hearing pings and the "something is behind you" ear warning, Thump & Listen reveal, new-moon "umbral" longer mirages, two Bound charges under the Blood Moon, life-stealing blood slashes, red camera fade and howl pose on awakening, a crimson fog during the event (vanilla fog stack, removed afterwards — never touches biome lighting).

**Blood Moon decision:** vanilla's full moon is not an eclipse, so the Blood Moon is an add-on event: only on full moons, 34% chance (configurable), guaranteed after three misses, moonrise to dawn, persisted across reloads, operator commands to test it.

---

## Living motion (v1.0.2)

Feedback on v1.0.1 was that the creatures looked *flat, stiff and not alive*: the bodies rode the player's
human walk cycle with only small ambient wiggles on gills, ears and rings. v1.0.2 rebuilds every animation
as a stack of layers that run together on each form (see `tools/anims/life.py` and `tools/anims/races.py`):

| Layer | What it adds |
|---|---|
| **life** | breathing (chest, shoulders, head), heartbeat, blinking with real eyelids, slow weight shifts, small head moves and curious tilts while standing |
| **locomotion** | a race-specific gait on top of the player's own stride: shorter strides, knees and ankles, hip bob, roll toward the stance leg, shoulder twist against the hips, forward lean, follow-through on tails, ears, gills and loose stones |
| **airborne / landing** | take-off stretch and fall reach driven by vertical speed; a soft or hard landing squash (with dust) chosen by how fast the fall was |
| **attack / hurt** | a reaction to every melee swing; a keyframed flinch on every hit (eyes squeezed shut, ears pinned, stones jolted) |
| **idle behaviours** | after a few seconds standing still the creature does something on its own, picked at random |
| **turning** | the body twists toward where the player looks and leans into turns; tails and ears drag behind |

**Per race**

* **Salamander (001):** slow amphibian breaths and a fluttering **throat pouch** with a deep gulp every few seconds; visible **heartbeat** of the fluid sacs behind the belly membrane; upper eyelids blink (heavy-lidded when Dormant, shut when asleep). Walks with bent knees, flat feet that roll off the toes, a sinuous body roll and a travelling wave down the tail; sprints with arms splayed and the tail lifted. Idle: **tastes the air with its sticky tongue**, **shakes its head** (gills slap, spores fly), **curls its tail round to admire its flower** (petals open, pollen drifts), **stretches and yawns** (empty hands only). States: Predatory lashes its tail and twitches its jaw, Bloom breathes its petals, Rooted sways like a plant in a breeze.
* **Titan Golem (002):** a six-second **stone breath** in which the blocks part and rejoin, a lub-dub **rune heartbeat** in the crystal, slow **stone eye shutters**. Walks stiff-legged and lumbering with a heavy roll; every footfall drops the trunk onto the hips, jolts the shoulder boulders and back slabs in sequence, flares the core and kicks up **dust from the soles**. Idle: **stones lift and re-seat** bottom to top, **grinds its crown** left and right (sparks), **spins up its core**, **raises a fist and turns it over to look at it** (empty hand only).
* **Jackalope (003):** fast shallow breaths, a **twitching nose with whiskers**, bouts of **chewing**, ears that swivel independently and point where it looks, quick bird-like head moves and blinks. Walks with springy steps and bouncing ears; sprints as a real **two-footed hare bound** with a flight phase, paws tucked and ears pinned. Idle: **washes its face and pulls an ear down to clean it**, **rears up as a sentinel** and scans the horizon, **thumps a hind foot** in warning (dust), **stretches, yawns and shakes**. Hunt and Blood Moon states add trembling, coiled stances and sharper twitches.

**Engineering decisions**

* **Stateless and identical everywhere.** Everything is Molang of the player's own queries (stride distance, speed, vertical speed, look direction, life time, hurt time); no persistent variables, so the motion is the same on every device and survives the form changing. Idle behaviours use a timer-animation state machine (`q.all_animations_finished`), not stored timestamps.
* **Feet stay on the ground.** The build plays each gait through a Molang/keyframe interpreter on top of the vanilla walk cycle, measures the lowest point of the legs at every stride phase and fits a short Fourier series for the body bob (`tools/anims/fit.py`). Feet stay within about 0.1 pixel of the ground through the whole walk and sprint of all three races; only the Jackalope's sprint deliberately leaves the ground.
* **Held items stay in the hands.** Arms only take the race's own arm motion when that hand is empty (`q.is_item_equipped`), so swords, shields and the Focus never drift away from the hand; arm-using idle behaviours only play with empty hands.
* **No fighting the vanilla poses.** Gaits switch off while riding or gliding, idle behaviours stop for any movement, sneaking, sleeping, swimming or a hit, and everything is third-person only.
* **Cheap on phones.** Values every layer needs (stride phase, swing, speed, the fitted bob) are computed once per frame in the attachable's `pre_animation` script.
* **Seen before shipped.** `tools/anim_gifs.py` renders GIFs from the shipped files (the previews below are not mock-ups), and the validator now parses every Molang expression and rejects unknown queries or unset variables.

| | | |
|---|---|---|
| ![Salamander motion](images/anim_salamander.gif) | ![Golem motion](images/anim_golem.gif) | ![Jackalope motion](images/anim_jackalope.gif) |
| ![Salamander idle behaviours](images/fidgets_salamander.gif) | ![Golem idle behaviours](images/fidgets_golem.gif) | ![Jackalope idle behaviours](images/fidgets_jackalope.gif) |

**New anatomy for it:** eyelids (all three), a throat pouch, a tongue and pulsing viscera (Salamander), a hinged chewing jaw and whiskers (Jackalope), stone eye shutters and footfall dust points (Golem); the Golem's trunk now pivots at the hips.

## Expansion 01 (v1.1.0): races 004–006

The expansion was built into the existing add-on, not beside it: same packs and pack ids, the same race framework, and races 001–003 preserved: their generated models, textures, animations, attachables and items are byte-for-byte identical to v1.0.2 (checked file by file), their item ids, race codes and saved data are unchanged, their scripts only gained the fields the new Codex needs (focus names, control hints, reticle cones), and all 136 of their runtime assertions still pass. Permanent codes **004**, **005** and **006** were added.

*The tables below record the expansion as built in v1.1.0; the bodies, motion and effects of 004–006 were redrawn in v1.2.0 with the same gameplay — see [the v1.2.0 section](#visual-overhaul-v120-races-004006-redrawn).*

### Research behind the designs
* **Protura** (the real "coneheads"): tiny soil hexapods with **no eyes and no antennae**; they walk on four legs and hold the **front legs up as sensory organs**; the head carries a pair of **pseudoculi** of uncertain function; mouthparts are internal **stylets**; development is **anamorphic** — abdominal segments are added at moults until the adult has **twelve**. ([Wikipedia: Protura](https://en.wikipedia.org/wiki/Protura))
* **The Flying Spaghetti Monster**: the deity of Pastafarianism, introduced in Bobby Henderson's **2005 open letter to the Kansas State Board of Education**; usually drawn as a tangle of spaghetti with **two meatballs and two eyes on stalks**; believers are "touched by His Noodly Appendage". ([Wikipedia: Flying Spaghetti Monster](https://en.wikipedia.org/wiki/Flying_Spaghetti_Monster))
* **Nurarihyon**: a yokai pictured as an elderly gentleman with an **elongated, gourd-shaped head** in fine clothes who **walks into homes at the busy evening hour, sits down, drinks the tea and is taken for the master of the house**; later popular culture made him the **commander of the yokai** (and, in modern fiction, the leader of the Night Parade of One Hundred Demons, *hyakki yagyō* 百鬼夜行). ([Wikipedia: Nurarihyon](https://en.wikipedia.org/wiki/Nurarihyon), [yokai.com: Nurarihyon](https://yokai.com/nurarihyon/))

### 004 · Xenentoma — เซเนนโทมา

**Identity kept:** an alien arthropod that *does not see*: it reads the world through the ground, and its body changes by moulting and adding segments.

| Brief element | Delivered |
|---|---|
| ~1.75 blocks, eyeless, Protura-inspired, six limbs | 1.75-block hexapod built on the proturan blueprint; three limb pairs with three jobs (below) |
| Conical head, false eyes (pseudoculi), retractable needle feeding apparatus | Conical head with two glowing pseudoculi, palps, and a **stylet that extends** to probe (idle behaviour) and to inject (Anamorphic Surge) |
| Translucent ivory / pale grey / muted violet chitin; sensory hairs | Procedural chitin with translucent edges, a violet **nerve cord glowing through the body**, sensilla bristles on the forelimbs and head |
| Anterior sensory limbs, middle manipulative limbs (hold items), posterior segmented locomotor legs | Forelimbs held forward ending in glowing sensilla (raised in Survey); middle limbs bound to the player's arms so **items are held normally**; posterior legs with pretarsal claws that carry the gait |
| 12 abdominal segments; overlapping dorsal plates (not wings) | Twelve articulated segments with intersegmental membranes that show when the abdomen stretches; split dorsal **tergites** that open when it moults — never wings |
| Vibration Mapping (not a wallhack), Ecdysis (shell decoy), Anamorphic Expansion | **Vibration Sense** (private, approximate, ground-borne, close range) + **Sensory Clarity** resource; **Exuvia Proxy** with a real shed-shell entity; **Anamorphic Surge** extending the twelve segments one after another |
| Survey 15 s / Exuvia 28 s / Glide 18 s / Surge 40 s | All four at the brief's cooldowns and ranges (see ABILITIES.md) |
| Passives: darkness awareness without a dark screen, quieter movement, vibration detection | **Eyeless** (Blindness/Darkness removed, the screen is never darkened), **Stillness** (motionless → invisible), Vibration Sense, Six-Point Landing |
| Weaknesses: explosions/vibrations overwhelm senses; airborne reduces detection | Explosions within 14 blocks and lightning **overload** it (no senses, no Survey, slower cooldowns, +15% explosion damage); in the air the senses shrink and blur |
| Animations: idle, walk, run, jump, scanning, molting, gliding, surge, sleeping, combat, swim, damage, recovery | Restless sensing idle; a six-limbed walk and a scuttling run with posterior legs carrying the gait; jump tuck; **Survey** pose with forelimbs raised and sensilla flicking; **teneral** form after moulting (soft, pale) and the shell left behind; flattened **glide** with folded legs; segment-by-segment **surge**; asleep, the sensory limbs fold and the abdomen curls; a stylet stab on every attack, a curl-and-retract flinch when hurt, soft and hard landing recovery; swimming uses the player's own swim pose (the gait layer steps aside); idle behaviours: stylet probe, sensilla grooming, listening to the ground, an anamorphic ripple down the segments |

**Additions:** Sensory Clarity as a readable resource with hysteresis, "sensed" creatures that the Surge strikes harder, the exuvia provoking nearby hostiles, Speed II escape then Resistance as the cuticle hardens, tripping enemies during the glide.
**Changed:** "vibration mapping" is deliberately *not* an outline/X-ray effect: it is a few private, jittered rings at approximate positions, because a wallhack would break survival and PvP.

![Xenentoma](images/race_004_xenentoma.png)

### 005 · Flying Spaghetti Monster — สปาเกตตีมอนสเตอร์บินได้

**Identity kept:** absurd on purpose, engineered seriously — every power is a property of its pasta anatomy.

| Brief element | Delivered |
|---|---|
| Floating spaghetti mass ~1.1 blocks wide, ~1.7 tall with eyestalks | Dense asymmetric mass of ~40 curved noodle strands in slowly circulating twist groups, dangling and trailing strands, hovering a hand's breadth above the ground |
| Exactly two meatballs | Two meatballs on orbit pivots — they leave (Ricochet), circle (Revelation) and come back |
| Two independent eyes on stalks | Two noodle eyestalks with their own lids; they look and blink independently (one watches your back: Dual-Eye Awareness) |
| Sauce that flows, even against gravity | Sauce on the strands, a sauce crown and drips that sometimes **run upward**; Sauce is also its resource |
| Temporary noodle appendages for items | Braided noodle arms that only form while a hand holds something or strikes, so tools sit in a "hand" of strands |
| Hovering visual without unrestricted flight | Visual hover + **Noodle Parachute** (sneak while falling) — no flight |
| Touch 15 s / Al Dente 22 s / Ricochet 28 s / Revelation 50 s | All four at the brief's cooldowns; the Revelation is three rotating spiral layers of the body itself with opposite-orbit meatballs and raised eyestalks, not a particle burst |
| Passives & weaknesses: Noodly Float, Flexible Appendages, Elastic Form, Dual-Eye Awareness; fire brittleness; meatballs detached | All, plus **SAUCY** empowerment; fire leaves a visibly singed **brittle** form |

**Additions:** blessing allies with the Touch, gathering dropped items, projectile-proof Al Dente with a counter, meatball tethers and target sharing, pasta-themed food bonuses.
**Changed:** none of the brief's numbers; the hover is purely visual (Bedrock cannot give a player a free-floating hitbox without flight).

![Flying Spaghetti Monster](images/race_005_spaghetti.png)

### 006 · Nurariten — นูราริเทน (UNIQUE)

**Identity kept:** *The Uninvited Sovereign* — it does not ask, it arrives; it treats every place as its house and every crowd as its court.

| Brief element | Delivered |
|---|---|
| ~1.95 blocks; elongated cranium curving back; ivory mask face; narrow golden slit-pupil eyes | Gourd-like cranium sweeping back under a gold diadem; ivory mask face with vermilion court marks; narrow golden eyes with vertical pupils that shift while the face stays still; slow, heavy blinks |
| Fragmented floating golden halo | Eight halo fragments (arcs and glyph tablets) that each drift on their own around the head and flare when it attacks |
| Layered collars, long sleeves, slender fingers | Stacked ceremonial collars on an elongated neck; sleeves that **hide the hands** — slender long-fingered hands slide out only to hold an item, strike or issue a decree (two fingers for an edict, one finger for the Final Edict) |
| Ivory, aged gold, vermilion garments | Ivory silk with a faint gold cloud-scroll damask, aged gold trims, vermilion hakama and lacquered clogs |
| Architectural back halos / heavenly gates that unfold; procession-like shadow | A folded gate and rings on the back that **unfold into a court** (Temple) and rise into a **throne-palace** (ultimate); an idle behaviour where it stands perfectly still while its shadow becomes a procession |
| Divine Jurisdiction (Sovereign Presence, Celestial Edicts, The Hundred Heavens), shared judgment marks | Implemented as a system (`src/systems/jurisdiction.ts`): **courts** (temporary, block-free) and **judgment marks** (1–3, shared by all its abilities) |
| Arrival 18 s / Lowered Gaze 25 s / Temple 35 s / Expulsion 40 s | All four at the brief's cooldowns, with the requested safety rules (safe teleport, no forced camera, no flashing, no land seizure) |
| HYAKUTEN CHŪKŌ 百天昼行 (ขบวนร้อยสวรรค์ยาตรายามทิวา), 180 s, five stages, real consequences, full restoration, no 100 AI mobs, iPhone-friendly | All five stages (below), each with combat consequences; ten script-owned entities in total; everything dissolves and every temporary state (fog, movement lock, forms, courts, marks) is restored — also on interruption, death, logout and reload |
| Day / midday / dusk / night relationship without changing world time or sky | **Solar Mandate** (day/midday bonuses), **dusk = the hour of visiting** (Nurarihyon's hour: 2 Arrival charges, longer Temple), **Nocturne Radiance** at night; at night the ultimate brings a *private* daylight haze to its witnesses; world time/sky never touched |
| Passives: Celestial Bearing, Royal Presence (subtle, not permanent CC), Uninvited Authority; weaknesses: Judicial Weakness, Arrogant Posture, Broken Mandate | All six, with numbers in ABILITIES.md; Royal Presence never affects players and never stacks |
| Unique classification must be meaningful and extensible | One holder per world (operator-configurable, `/plrace:unique`), world announcement, a fifth ability, its own world system and presentation; `rarity: "unique"` + `ultimate: true` is all a future Unique needs |

**HYAKUTEN CHŪKŌ — the five stages as built**
1. **The Sky Must Open** — a gate (the Temple's gate at ×3.6) opens 9 blocks ahead in the sky with fractures of light, a ground shadow, a bell and one soft golden fade; the Sovereign stands still. *Interruptible* (Judicial Weakness): a heavy hit returns half the cooldown and breaks the mandate.
2. **The Proclamation** — two heralds descend from the gate carrying the decree; every enemy within 16 blocks is judged and bows.
3. **The Hundred Heavens March** — eight columns (standard bearers, guards, heralds with horns, judges with scrolls, palanquin bearers, parasol bearers; an empty palanquin reserved for the Sovereign in each) emerge in a ring and march around it, spiralling inward, trampling and herding enemies toward the centre. 96 attendants + 2 heralds + the gate + the Sovereign = **one hundred**.
4. **The Throne Without Permission** — the court rises into a throne-palace behind it; the columns halt and face inward; the Sovereign is protected and everything within 12 blocks is weakened and judged.
5. **The Final Edict** — one finger rises; golden seals converge on every judged creature and the judgment lands (4 +4 per mark, +25% at midday). Then the procession dissolves into light, the gate closes and the haze lifts.

**Additions:** Master of the House (Hero of the Village indoors among villagers — the yokai who is taken for the master), the exile rule that turns expelled creatures back at the court's edge, accessibility toggle for the ultimate's screen effects, cancel-in-preparation with a partial refund.
**Changed (and why):** the brief's "Hundred Heavens March" is not a hundred separate mobs — that would cost pathfinding, collision and network traffic on every phone in range; columns of shared geometry marching on a script path keep the image (one hundred figures) at the cost of ten entities. The brief's "sky must open" uses a giant gate and a private fog instead of changing the sky, which Bedrock cannot do per player. When cast under a roof, the gate enters "through the door" (ground level, normal size) instead of the sky — a deliberate nod to a yokai who walks into houses.

![Nurariten](images/race_006_nurariten.png)
![HYAKUTEN CHŪKŌ](images/hyakuten_chuko.png)

### Motion for 004–006
The three new bodies use the same layered, stateless animation system as v1.0.2 (life, locomotion, airborne/landing, attack, hurt, idle behaviours, form transitions), with gaits fitted to the measured foot floor (Xenentoma within 0.02 px, Nurariten within 0.16 px; the Spaghetti Monster hovers):

| | | |
|---|---|---|
| ![Xenentoma motion](images/anim_xenentoma.gif) | ![Spaghetti motion](images/anim_spaghetti.gif) | ![Nurariten motion](images/anim_nurariten.gif) |
| ![Xenentoma idle behaviours](images/fidgets_xenentoma.gif) | ![Spaghetti idle behaviours](images/fidgets_spaghetti.gif) | ![Nurariten idle behaviours](images/fidgets_nurariten.gif) |

* **Xenentoma:** constant small sensing (sensilla flicking, forelimbs tasting the air), a six-legged gait, the stylet that slides out to probe, grooming of the sensilla, freezing to listen to the ground, a ripple running down the twelve segments.
* **Flying Spaghetti Monster:** strands circulating in twist groups, meatballs bobbing, eyes looking and blinking separately, trailing strands streaming back when it moves, sauce running uphill; idle behaviours: it doodles shapes with a noodle, its eyes look in two directions, a meatball does a lap around the body, sauce defies gravity.
* **Nurariten:** serene and minimal — the face barely moves while the halo fragments and the architecture do; slow ceremonial steps with almost still arms; a brief pause and a slow turn toward whoever struck it; idle behaviours: it surveys its "court", settles its sleeves with a flick, two fingers emerge to write a glyph in the air, and (by day) it stands utterly still while its shadow becomes a procession.

## Visual overhaul (v1.2.0): races 004–006 redrawn

**Why:** after v1.1.0 the three new lineages were judged to look funny and cheap — models, textures, motion and effects alike. v1.2.0 redraws all of it. Direction chosen with the player: **elegant, Marketplace-style** (clear silhouettes, clean pixel art with a limited lit palette that sits next to Minecraft and races 001–003); the Spaghetti Monster as an **appetising pasta deity**; the Xenentoma **standing and walking upright with elegance, dropping onto all six limbs to sprint**.

**Scope:** visuals only. Models, textures, animations, particles and the helper entities (exuvia, meatball, celestial gate, heralds, procession) were rebuilt; every item id, form/variant name, pose name, particle, entity and geometry id, locator the scripts use and all gameplay are unchanged, so worlds and saved players carry over. Races 001–003 are byte-for-byte identical to v1.1.0 (checked file by file).

**What looked wrong (read off renders of v1.1.0) → what changed**

| | v1.1.0 | v1.2.0 |
|---|---|---|
| **004 Xenentoma** | a "robot with a tail": boxy chest, human limbs, forelimbs held out like a zombie, a screen-like box head, twelve equal segments dragging like a lizard tail, grey stone-like texture with purple stripes, a human walk | an upright S-curve: digitigrade hind legs, a wasp waist, a thorax leaning forward under three overlapping tergites, a conical head with glossy pseudoculi and the stylet sheath; sensory forelimbs raised in a tall V ending in glowing sensilla fans; mantis-like middle limbs at the hands (they fold against the chest when empty); a short teardrop **gaster curled under the body** (twelve overlapping segments with glowing membranes) instead of a tail. Smooth translucent ivory chitin with pearl edges and a violet nerve cord. 90 cubes (125 before) |
| **005 Flying Spaghetti Monster** | a haystack of 588 thick strands, dirt-block meatballs, box eyes, a red brick of sauce, hanging strands that read as spider legs and turned into sticks at speed | a round **nest of glossy golden spaghetti** — twelve staggered slices (no shared face planes, no z-fighting) painted with strands wound continuously across every face, four loose loops lifting off the surface; two **seared, glazed meatballs** on its shoulders; a ladle of marinara poured over the top and running down the sides (one bead creeps upward); big round eyes with **sliding pupils** and their own lids on noodle stalks; His Noodly Appendages curling out and streaming back; drooping U-loops underneath (they can only swing, never read as legs); the **Holy Colander's rim as a perforated golden halo**. 131 cubes |
| **006 Nurariten** | a white box head under a stacked "chef's hat", a flat face, box sleeves, paper-card hems with random dots, a scattered halo of sticks, a toy-like gate, a stiff walk | a Heian court sovereign: closed A-line robe with a vermilion hakama and six weighted hem panels, wide sleeves, a long gourd cranium sweeping back in one continuous curve, an ivory mask with golden slit-pupil eyes, high court brows (*hikimayu*) and a vermilion mouth; a complete **halo of six arcs and four glyph seals**; slender pillars that unfold into a torii court and rise into a throne; ivory, aged gold, vermilion and lacquer black with gold cloud scrolls and kasane edges. 90 cubes (107 before) |
| **all three** | per-pixel random noise ("dirty"), no palette discipline, no edge light, 16 px particle sprites, pure sine motion with no timing or holds | quantised palette ramps lit from each face's real rest-pose normal, 1-texel rims, pixel-exact decals (faces, pupils, seals); a second full-colour **particle atlas** (256×256) for races 004–006; motion built on timing — anticipation, follow-through, holds, eased moves, per-race rhythm |

**Shared tools added** (all offline, in `tools/`): `kit/pixel.py` (palettes, lighting, rims, decals — no random noise); shape builders in `models/common.py` (`chain`, `ellipsoid`, `drape`, `arc`, `segment`); animation helpers in `anims/life.py` (`chain_wave` travelling waves, `saccade` move-and-hold, `smooth_pulse`); `review.py` sheets (turnaround, black silhouettes, in-game distance next to the vanilla player and races 001–003); `fx_ex.py` (the new particle atlas and effects). The validator now also rejects numbers in scientific notation inside Molang (Bedrock cannot parse them).

**Motion language per race**
* **Xenentoma — stillness, then precise jerks.** Sensory limbs sweep and freeze (0.08–0.15 s snaps, 0.5–1.5 s holds) with a fine tremble at the tips; the head ticks between directions; the gaster breathes as a wave running segment by segment. It stalks upright on its hind legs with high careful steps; **sprinting with empty hands it drops onto all six limbs and scuttles in a tripod gait** (holding an item it sprints upright, so the item stays in its hand). Idle: stylet probe, sensilla grooming, listening to the ground, an anamorphic ripple.
* **Flying Spaghetti Monster — soft and buoyant.** The nest floats on a slow 2.5 s swell and breathes with it; everything that hangs follows a beat late; loops slide around the nest; the pupils dart and hold independently and each lid blinks on its own clock; it leans and banks into its path while the appendages stream back in travelling waves; it squashes on landing and the meatballs bounce a beat later; attacks are a whip-like lash. Idle: a noodle twirls itself like pasta on a fork, the eyes study sky and ground and then each other, the meatballs take a lap around the nest, a bead of sauce climbs into the air while both eyes watch.
* **Nurariten — slow and ceremonial.** *Suriashi* steps (short, no bounce, hem panels swinging behind the legs), almost still arms with heavy sleeves, a head that turns slowly, a halo that turns and breathes. Idle: surveys its court, settles its sleeves, writes a glyph with two fingers, stands still while its shadow becomes a procession.

**Effects (new atlas, same particle ids):** Xenentoma — violet sensilla motes, flat double ripples on the ground, pale moult fluid, translucent spinning chitin flakes, a violet star burst for the surge. Spaghetti Monster — glossy marinara drops and splats, soft steam wisps, golden al dente splinters, a golden noodle spiral for the Revelation, a sauce ring on the ground. Nurariten — soft gold motes, a gold decree glyph (令) in a ring, a vermilion hanko seal (王), a court ring with ticks and cardinal marks, a glowing torii, branching light fractures, petals rising as the procession dissolves, and a shadow-play procession strip.

**Helper entities:** the meatball is now a round seared, glazed meatball; the celestial gate's light became staggered bands of golden mist (*suyari-gasumi*) instead of rungs; the shed exuvia comes straight from the new body (hollow, split along the back, its sensory limbs drooping); heralds and processions use the new Heian palette.

![Flying Spaghetti Monster v1.2](images/race_005_spaghetti.png)
![Helper entities](images/helper_entities.png)

## Ability effects overhaul (v1.3.0): every race

**Why:** in game the player found the skill effects "extremely not beautiful" and asked for all of them to be redone, for all six races, in the direction they chose: **spectacular glow** — flashes, magic circles drawn on the ground, beams and streaking sparks, shockwaves, debris; a charge → release → impact → linger rhythm; still at home in Minecraft.

**How it is built (identifiers unchanged, gameplay unchanged):**
* A third particle atlas, `particles_vfx.png` (512×512), holds **white, animated sprites**: 8-frame flipbooks of a starburst flash, a shockwave ring, a magic circle that draws itself, a sword-arc slash, a smoke puff, a liquid splash and a branching crack, plus 20 static sprites (streak, star, petal, leaf, droplet, shard, four runes, crescent, hexagon, rock chunk, glyph ring, spiral...). The particle tint gives each race its colour, so one sprite serves every race.
* Every identifier the scripts spawn became an **entry effect that fires layers through particle events** on a timeline (`tools/vfx/lib.py: compose`). One script call now gives, for example, a converging charge, a flash, an expanding ring, streaking sparks and falling debris, each its own small effect (`plrace:vx_*`, 106 layers). Layers that need what the script passes in (beam direction and length, circle radius and duration, slash angle and size, the race colour) are drawn by the entry effect itself, since child emitters do not inherit variables.
* New Bedrock particle features in use: flipbooks, `lookat_direction` sparks stretched along their velocity (or along the aimed direction), ground decals (`emitter_transform_xz`), pillars of light (`lookat_y`), rocks that **bounce on blocks** (collision), and soft fades on `particles_blend`/`particles_add` (no more cut-out sprites for anything that fades).
* Budget: one cast is at most 68 particles (the rite of transformation; the heaviest ability is 53), checked for every entry effect.

| Race | Effects |
|---|---|
| 001 Salamander | Sundew Snare: spores gather, a glowing nectar filament streaks to the prey, a sundew blossom opens on the ground under it · Carnivorous Embrace: two green jaws snap, a pink burst, leaves · Root Metamorphosis: roots crack the ground in a ring, sap rises in columns, leaves fall · Bladder Jet: a water shock ring, streaking spray, bubbles · dew and hydration splashes |
| 002 Golem | Titan's Edict: each step of the shockwave tears a molten crack with rocks, dust and a rune pillar · Runic Bastion: hexagonal rune shields flash where blows land · Glyph Dominion: the great circle draws itself, runes rise, pillars of light walk its rim · Colossus Reassembly: glowing stone streams along the path and reforms with a blast |
| 003 Jackalope | Lunar Bound: crescent afterimages and glints along the leap · Antler Brand: a turning moon sigil · Velvet Mirage: silver-violet smoke and stars · Crimson Waltz: huge crimson arcs with flashes and sparks, a full-moon finisher |
| 004 Xenentoma | violet sonar rings on the ground · a moulting shimmer with fluid and spinning chitin flakes · violet impacts for the Surge |
| 005 Spaghetti Monster | golden noodles reaching out · Al Dente's crack of light and splinters · marinara crowns and drops · the Revelation's turning golden spiral and a sauce shockwave with a holy pillar and steam · the meatball's sauce trail |
| 006 Nurariten | torii gates of light with petals · decree glyphs bursting with a golden ring · the court circle drawing itself with pillars of light along its rim · light tearing the sky · petals and gold dust as everything dissolves |
| Shared | the rite of transformation (a magic circle in the race colour, a pillar of light, falling stars) · a sharper aim reticle |

**Visual bugs fixed on the way:** the court's walking pillars and ring (Temple and HYAKUTEN) only drew for about one court in four (the court loop runs every 4 ticks but tested `age % 8` / `% 20`); the aim reticle could mark a different creature than the cast would take and ignored the Bloom range (abilities now expose `aim()`, which both the cast and the reticle use); Root / Bloom / Dormant played their burst twice; the detached meatball's sauce trail never fired; shadows drawn with the cut-out material could vanish.

**Tooling:** `tools/vfx/` (atlas, layer builders, effect definitions per race, an offline particle simulator) and `tools/vfx_gifs.py`, which re-enacts what each ability's script spawns — identifiers, positions, timing and variables — next to the race's model and renders it from the pack's own particle files.

| | | |
|---|---|---|
| ![006 effects](images/vfx_nurariten.gif) | ![005 effects](images/vfx_spaghetti.gif) | ![004 effects](images/vfx_xenentoma.gif) |
| ![001 effects](images/vfx_salamander.gif) | ![002 effects](images/vfx_golem.gif) | ![003 effects](images/vfx_jackalope.gif) |

## Expansion 02 (v1.4.0): races 007–009

Built into the existing add-on like Expansion 01: same packs and pack ids, the same framework, races 001–006 kept (their files only change where the shared lists grow — the nine-race player/armour visibility lists, the Codex, the HUD), permanent codes **007**, **008** and **009** added, every saved race assignment untouched. Nothing here claims an in-game result: see [TESTING.md](TESTING.md) for what was run and what is left for a real client.

### Research behind the designs

The brief asked to keep three kinds of statement apart. Below, **A** = direct fossil / specimen evidence, **B** = scientific inference or uncertain reconstruction, **C** = this add-on's deliberate fiction.

**007 – prehistoric anatomy**
* *Microraptor* (Early Cretaceous, Jehol Biota): **A** long pennaceous flight feathers on the forelimbs **and** hindlimbs ("four wings"); **B** iridescent black plumage from fossil melanosomes; **B** how the hindwings were held in flight. ([NHM Dino Directory: Microraptor](https://www.nhm.ac.uk/discover/dino-directory/microraptor.html))
* *Yi qi* (Late Jurassic scansoriopterygid): **A** a rod-like *styliform element* projecting from the wrist and patches of membranous tissue near the forelimb; **B** a bat-like membranous wing; **C** membranes along the *hindlimbs* — that is our synthesis, not a claim about any fossil.
* *Psittacosaurus*: **A** a row of long bristle-like integumentary structures on the tail (Mayr et al. 2002, Naturwissenschaften — [PubMed 12435037](https://pubmed.ncbi.nlm.nih.gov/12435037/)); **A** the parrot-like beak.
* *Therizinosaurus*: **A** enormous manual claw cores; **B** their length with the keratin sheath.
* Oviraptorosaurs: **A** toothless beaks, cranial crests, feathered bodies (*Caudipteryx*), brooding postures (*Citipati*).
* Hadrosaurs (*Parasaurolophus*): **A** a hollow tubular crest carrying the nasal passage; **B** its use as a resonator/display.
* Ceratopsians: **A** horns and frills; **B** display / recognition.
* Dromaeosaurids: **A** the enlarged, raised claw of pedal digit II; **B** its use (prey restraint is one hypothesis).
* Ankylosaurs: **A** osteoderms; the nodosaur *Borealopelta* preserves keratin and pigment.
* Further oddities we drew on: *Kulindadromeus* (**A** scales *and* filaments on one ornithischian — feathers and scales coexisting), *Epidexipteryx* (**A** an elongated third finger and ribbon tail feathers), *Balaur* (**A** paired enlarged foot claws), *Halszkaraptor* (**A** swan-like neck and flipper-like forelimbs, **B** amphibious habits — our swimming style).
* The brief's second link (`PMC12020036`) could not be opened from the build environment (the host is blocked there), so nothing in this report is attributed to it.

**008 – deep-sea anatomy**
* Anglerfishes (Ceratioidei): **A** the illicium and luminous esca (a lure lit by symbiotic bacteria); **A** some deep-sea fishes have "ultra-black" skin that reflects under 0.5 % of light (Davis et al. 2020). Bathyas' skin, and his lure being a sun rather than a bacterium, follow from this (**C** for the sun).
* Goblin shark (*Mitsukurina owstoni*): **A** "slingshot" jaws that shoot forward on elastic ligaments when it bites (Nakaya et al. 2016).
* Giant isopods (*Bathynomus*): **A** a segmented dorsal armour of tergites that lets the body curl.
* Also: needle teeth (viperfish, fangtooth), photophores, gills.
* **C:** the humanoid chimera, the sword through the chest, its life-support role and everything solar.

**009 – fungal biology**
* **A** bioluminescent fungi (*Mycena*, *Armillaria*, *Omphalotus*; fungal luciferin), mycelial networks of branching hyphae and rhizomorphs, photoreceptors (the white-collar complex; *Phycomyces* sporangiophores bend toward light), spore dispersal (ballistospory, puffballs, *Pilobolus* aiming its spore capsules at light), labyrinthine and spiral gill/pore patterns (*Daedalea*, *Lenzites*).
* **B** spiking electrical activity reported in mycelia — measured, its meaning disputed; claims about network "communication" between plants are contested.
* **C:** the extradimensional consciousness, the geometric eye, floating, perception-altering spores.

### 007 · The Unknown Dinosauroid

**Identity kept:** a calm, quiet, disturbingly observant organism whose body is a list of things that should not coexist. **Taxonomic Collapse** is its system.

| Brief element | Delivered |
|---|---|
| Morphological Drift (structures change subtly; intentional states, not geometry corruption) | Four configurations cycling every ~75 s on **world time** (PLUMED, WEBBED, TOOTHED, FANNED); the animation and the script read the same clock, so each visible configuration is a real bonus (Veer distance, gliding, +1 melee, display reach). Shown on the HUD |
| Ancestral Misprint (hesitation, disrupted timing, misleading cues; never claim AI control the API lacks) | **MISCLASSIFIED** status: Slowness II, Weakness, and 50% of its blows on the Dinosauroid miss (cancelled). Bedrock scripts cannot rewrite a mob's target selection, so the "misreading" is expressed through these real effects; a broken-cladogram mark floats over the creature |
| Evolutionary Overflow | Taxonomic Error's form: every display structure active at once, luminous eyes |
| Hindwing Veer 14 s — leap/evade/glide, no sustained flight | 14 s: crouch-compress-launch ~7 blocks along your movement, hindwings and membranes unfold, the tail steers; sneak in the air for a short glide; no fall damage; a blow in the next 0.6 s is halved |
| Crest of Misclassification 24 s | 24 s: crest raised, pouch swollen, fans spread; everything hostile within 7 (+3 FANNED, +2 Overflow) flinches and is MISCLASSIFIED for 7 s |
| Sickle Testament 20 s, enhanced vs Misclassified | 20 s: a pivoting hindlimb strike (120° arc, 6 damage); a misclassified target takes 10, is pinned (Slowness IV) and the status is spent; full circle during Taxonomic Error |
| Taxonomic Error 42 s | 42 s: 12 s of Speed I, Jump Boost II, 40% faster recovery of the other abilities, a misclassifying aura (every 2 s within 5 blocks), misclassifying melee; then 4 s of exhaustion |
| Passives: Fossil Memory, Unreadable Posture, Display Organism, Primitive Intelligence | Speed I on rough ground (stone, gravel, sand, tuff, deepslate, basalt, terracotta...); 15% of creatures' melee blows miss; the display skin glows in low light (the *night* form) and displays reach farther; staring at a creature for 2 s studies it (health shown, counts as misclassified for the next Sickle Testament) |
| Weaknesses | Light protection, no sprint bonus, Slowness I under low ceilings (2-block tunnels), Taxonomic Error exhaustion |

**Body (model and animation).** A theropod silhouette — trunk pitched 30° forward, an S-neck carrying a large skull ahead of the chest, digitigrade legs and a long barred tail — about 31 px tall (33 to the crest), 86 bones and 171 cubes in the base form.

| Required element | Built |
|---|---|
| Beak *and* teeth | a deep, hooked oviraptorosaur beak (slate fading to a pale horn tip) with small white teeth behind it along the jaw line and an irregular inner second row; a hinged lower jaw |
| Asymmetric supraorbital horns | the right horn long and curving forward, the left a blunt stump |
| Hollow crest | a tubular hadrosaur crest sweeping back from the brow — bone with growth rings and a line of display skin; its open end shows a dark lumen that glows in Overflow |
| Throat pouch | a small tucked sac that fills and flutters with the breath and balloons in Display and Overflow |
| Feather tufts | downy plumes behind the eyes, pale bristles down the nape, quills along the back that stand up in Display |
| Nocturnal pupils | large amber eyes turned 28° forward; slit pupils (their own bones) that narrow and widen; sideways nictitating membranes |
| Distinct integument materials | countershaded downy plumage with bold dark bars; iridescent black-teal flight feathers with a violet sheen; bone-pale bristles; olive coarse scales on shins, feet and hands; two rows of osteoderms; dusky-rose bare skin on face and throat; wine-red membranes on ivory rods; teal / amber / violet display skin |
| Three-digit forelimbs, styliform digit, feather panels | two clawed fingers plus an elongated styliform digit — a pale spike from the wrist past the elbow carrying a membrane; covert and radial feather panels that fold as a wing and fan out in Display |
| **Hindlimbs** | a raised sickle talon on digit II; *Microraptor*-like feathers on the shank and a metatarsal fan; membranes from hip to knee and knee to ankle on jointed rods — a folded strip at rest, wide sails swung out about 70° in Veer and Overflow, half open at a sprint, opening when falling; the fan folds up in each step |
| Tail | five segments, stiff *Psittacosaurus*-like bristles at the base, embedded plates, side feather vanes and a seven-feather fan with eye spots that spreads in Fanned, rolls upright as a rudder in Veer and is preened by the beak |
| Morphological Drift, visible | the attachable reads the same world clock as the script (`q.time_of_day`): **Plumed** fuller tufts and longer arm feathers, **Webbed** leg membranes 60 % wider, **Toothed** jaw dropped and pupils narrowed, **Fanned** tail fan spread 26° per side; ~4 s crossfades |
| Calm, observant personality | the head follows your look through its own neck rig (it stays attached); pigeon-like head steadying when walking; darting glances only when standing still; idle behaviours: the long stare (pupils narrow to threads), slow throat pulses, preening the fan, a slow head tilt that snaps to the other side |

![007 turnaround and forms on white](images/race_007_dinosauroid.png)

### 008 · Bathyas, the Sun-Impaled — บาธีอัส ผู้แบกสุริยะ (UNIQUE)

**Identity kept:** an irritable, exhausted old abyssal chimera kept alive by the sword that torments it; quiet and terrifying once the sword is out. **Solar Impalement** is its system.

| Brief element | Delivered |
|---|---|
| Impaled State: life support, regeneration/resilience, solar energy, lure | Stability regenerates; +2 hearts (Health Boost); a regeneration pulse every 12 s; darkness and blindness are burned away; the Lure is only available impaled |
| Unshackled State: sword combat, aggression, mobility; declining stability, a safe window, must return | **The Impaled Sun** becomes a real weapon item in your hand (7 attack damage, +3 against the Sun-Marked) with Strength I and Speed I; Stability drains slowly for 15 s, then fast; at 0 the body fails (Wither) until you return it; at 2 hearts with no Stability left the body forces the sword back (heavy penalty) |
| Sword must not duplicate; death, interruption, reload must recover | The item is locked to the inventory (cannot be dropped or stored), checked every second (never two, never one while impaled), removed and the state reset on death, logout, reload, dimension change and lineage change |
| Lure of the Impaled Sun 18 s | 18 s (impaled only): squint and shield the eyes while a warped ring of light rolls 10 blocks; hostile creatures are drawn a step closer and SUN-MARKED for 8 s (a sun sigil over the head, Slowness I, Weakness I) |
| Goblin Maw Rush 20 s | 20 s: a low head-first surge up to 9 blocks, the jaw shoots out: 7 damage, 11 to the Sun-Marked (who lose the mark and feed you 4 health) |
| Isopod Bastion 28 s | 28 s: plates close for 6 s: Resistance II, knockback absorbed, light leaking through the seams; each melee blow (once per second) answers with a counterpulse (3 damage, knockback, Sun-Marked when impaled) |
| Draw the Sun 45 s + Re-Impalement | The fourth ability is a toggle: DRAW (grip, hesitate, tear it out — free) and RETURN (the blade slides home, Stability +20, a moment of misery — the 45 s cooldown starts here) |
| ABYSSAL DAYBREAK 180 s, six stages, localised, not Nurariten's procession | 9 s, standing: **I** Solar Overload (a 6+ hit interrupts, half the cooldown back) · **II** Abyssal Extinction — a dark local haze for players within 24 blocks (never the world's sky or time; the same world setting as HYAKUTEN's haze turns it off) · **III** Impossible Sunrise — a pillar of light up and down · **IV** Leviathan Silhouettes — vast deep-sea shapes pass through the light (particles, no mobs) · **V** Solar Execution · **VI** the field erupts: 10 damage within 9 blocks (15 to the Sun-Marked), knockback, marks, then 6 s of burning deep-sea daylight (2/s within 6). Afterwards the sun is back in the chest and Bathyas is spent |
| Passives: Sun-Impaled Core, Abyssal Constitution, Irritated Luminary, Harpoon Vitality | As above; water breathing always, Conduit Power in water, regeneration with the head under water; bright open sunlight gives Strength I but raises Photic Strain |
| Weaknesses: Photic Misery, Unshackled Risk, Large Target | **Photic Strain** (Lure +30, Daybreak +60, sunlight +1/s): at 100, brief blindness and slowness; projectiles hit 15% harder; no sprint bonus |

**Body (model and animation).** 71 bones and 145 cubes, about 30 px tall but hunched.

| Required element | Built |
|---|---|
| Exhausted, irritable old man | the chest pitched 18° forward, the head hanging low between uneven shoulders, long webbed arms reaching the knee, bent knees; half-closed heavy lids, shaggy frowning brows and two scraggly barbels like a beard; a slow 5-second breath and a muttering jaw. Idle behaviours: shields his eyes from his own light, grumbling; a long sigh with bubbles; dozes off and jerks awake; pokes the wound and wiggles the hilt |
| Anglerfish | the sun *is* his lure: no forehead illicium — instead an atrophied light organ (three cold light spots along the crown), glowing barbel tips and a needle-toothed underbite |
| Goblin shark | a flat snout over a protrusible jaw with irregular needle teeth; in Maw the jaws shoot 5.5 px forward, the red sling showing; gill flaps flutter on each exhale |
| Giant isopod | seven tergite plates with side flanges and keels down the back, plates on the shoulders, segmented shells on forearms and shins; in Bastion they slide together from the bottom up with seams of light between them |
| Near-black but legible | near-black skin with wet rim highlights, a green-grey sheen, pits and bumps, and cold cyan light spots on the crown, flanks and middle back plates |
| The sword through the chest | hilt and sunburst guard below the sternum, the blade climbing 30° and leaving through the third back plate (left of the spine, so it reads from behind); charred rings at entry and exit, glowing cracks along the ribs, the face lit warm from below. Light shells at both wounds pulse *lub-dub* at about 52 bpm and the hilt knocks once per beat: **life support** you can see; **light** and **lure** (the Lure form blazes); **torment** (he squints at it, flinches when it settles back, grimaces when he pokes it) |
| Unshackled | no sword in the body: a blazing cross of light in a charred ring, the predator's crouch (chest pitched 26°, head low and forward, eyes open), only the breath and a faster heart |
| Abyssal Daybreak | bronze-black skin with glowing veins, light under every back plate, gold eyes; he strains back with the jaw open, everything trembling |
| The drawn sword | in the hand the game draws the item's icon like any sword — a white-gold blade with a sunburst guard, the same design as the embedded blade; a 3D model of that blade (`build_sword()`) is used for the previews only |

![008 turnaround and forms on white](images/race_008_bathyas.png)

![The Impaled Sun](images/race_008_sword.png)

**Why not Golem, Nurariten or Jackalope again:** no permanent armour bonus (only the 6-second Bastion), no territory or judgement, no speed race — its identity is the decision of when to take the sun out and how long to keep it.

### 009 · Octamyces Undecimus — ออคทา-ไมซีส แห่งรอยแยกที่ 11

**Identity kept:** a fungal surveillance organism from elsewhere; the eye carries the personality. **Eleventh Parallax** is its system.

| Brief element | Delivered |
|---|---|
| Observation (records positions and paths) | **The Eye That Records** (22 s, 16 blocks, line of sight): OBSERVED for 5 s (an eye sigil over it, +20% damage from you) and 25 points of its path kept for 30 s (HUD: points and seconds left) |
| Parallax Infection (misleading positional information; real mechanics for mobs) | **Parallax Sporeveil** (18 s, radius 6): infected for 6 s — Slowness I, false afterimages where it stood a moment ago, and 40% of its blows against you miss (25% for players). Wardens, iron golems, withers, dragons, elder guardians and creakings are not fooled |
| Rift Resonance (apparent position changes, positional echoes) | **Hyphal Offset** (26 s): up to 6 blocks along your movement, checked half a block at a time (never through walls, into lava, fire or other hazards); an **echo** entity — a translucent copy of the body — stays 3 s and bursts into spores; creatures near the old position are infected |
| The Eleventh Frame 48 s — stop, eleven rings open, afterimages of recorded positions, filaments, a network, timed attacks along the trajectory, collapse; must use the recording | 3.5 s rooted: rings open, every recorded point appears, filaments reach out and knit the path, then the network strikes along it in order (4 damage per point, 6 to the observed creature, at most 4 strikes per creature) and a final hit as the images collapse; without a recording it strikes up to 5 creatures where they stand |
| Passives: Resonant Levitation, Panoptic Witness, Spore Affinity, Dimensional Afterimage | Half fall damage and a sneaking drift; invisible creatures within 12 blocks are revealed to you, blindness and darkness are removed; a regeneration pulse in rain, water or low light; faint echoes behind you while sprinting |
| Weaknesses: fire, hazards, some senses not fooled, fragile | +50% fire damage, a scorched *unstable* form and no Offset while burning; +10% damage taken; the immune list above |
| Accessibility: no strobing, full-screen flashes, forced camera, persistent distortion | Iridescence is painted in gradients and slow hue shifts; effects are local and short; no camera control, no screen effects |

**Body (model and animation).** 89 bones and 214 cubes (the most detailed body in the add-on), about 31.5 px to the crown; nothing touches the ground — the stalk's bulb ends 6 px above it and the body hovers with a ±0.8 px bob.

| Required element | Built |
|---|---|
| Asymmetric cap | a wide brim (27 × 24.5 px) lifted 6° on one side with a cyan margin, glowing spiral lamellae beneath it and a fringe of glowing threads; above it a lopsided seven-band dome swelling to one side, each band a layer of tissue with its own hue (blue-violet at the brim through violet and magenta to pink at the crown), gold spore pits on the crown terraces; two shelves at the back pass through each other in an impossible X |
| The Undecimal Eye — 11 concentric polygons rotating independently | a void pupil (a starfield octagon with a black singularity) inside **eleven polygon rings with 3, 4, 5 … 13 sides** — 88 bars, each ring 0.25 px further forward, so the eye is a funnel into the void; pale and saturated rings alternate so each reads on its own; every ring turns at its own speed and direction (21, −15, 12, −9.5 … 2 °/s) |
| Polygonal blink | eight trapezoid plates stand open round the eye as an eight-pointed crown and fold shut in sequence into a flat seamed octagon, then rebuild; the eye glances with quantised darts |
| Gills | a three-vane rotor under the cap turning continuously, pore pads that open and close, spiral lamellae painted under the brim |
| Twisted stalk | a glowing pink-cyan spiral core inside three translucent lattice tiers twisted 0°, 22.5° and 45°, on a bulb (volva) |
| **Eight mycelial groups, eight functions** | **1–2 manipulators** — braided strands ending in three-finger grips that hold your items; **3–4 propulsion fans** — scalloped fin membranes on the back that fold into one propulsor beating at a sprint; **5 sensor** — three fine glowing feelers that probe the air; **6 spore emitter** — curls up into an earthstar (a puffball in a star of rays); **7 stabiliser** — a curtain of four luminous filaments trailing like a kite tail; **8 resonance antenna** — a floating triangle above the crown |
| Iridescent "impossible" colour without strobing | limited hue-shifted palettes per material and glow fixed in the textures (rings, lamellae, filament tips, spore pits, core); no texture changes over time and nothing flashes |
| Surveillance Idle | after 7 s of stillness the creature *settles*: the hover drops to almost nothing, the mycelia hang still, glances and blinks stop, the crown narrows and the pupil shrinks while the iris scans slowly and now and then fixes on an empty spot; any movement, hit, attack or item use wakes it |
| Forms | **sporeveil** gill pads hang open, the brim flares, four glowing spore pearls, the mycelia vibrate; **record** the rings click into alignment one by one and stay aligned and tightened, the pupil shrinks, it follows your look harder; **offset** the upper cap layers slide off the lower ones and the mycelia stand out like fins; **frame** the eye stops and the eleven rings open outward one after another into a telescope, then collapse back; **unstable** (burning) an ash palette with ember edges, a sagging brim, drooping mycelia, ring stutter and an irregular hover |
| Idle behaviours | the crown folds shut plate by plate and rebuilds; the rings click round one sector each, inside out; a wave lifts the brim and the pores breathe out spores; the sensor probes and the eye follows its tip |

![009 turnaround and forms on white](images/race_009_octamyces.png)

### Expansion 02 at a glance: retained, improved, replaced, new

**Retained exactly as briefed:** every ability name and cooldown (007: 14 / 24 / 20 / 42 s; 008: 18 / 20 / 28 / 45 / 180 s; 009: 18 / 22 / 26 / 48 s, Parallax Sporeveil's radius 6, the Eye's 5-second observation), every passive and weakness by name, the three mechanics of Taxonomic Collapse and of Eleventh Parallax, the six named stages of Abyssal Daybreak, the Impaled / Unshackled states with Re-Impalement, a sword that never duplicates and always comes back, Bathyas as a Unique lineage, and each creature's personality.

**Improved:**
* Morphological Drift runs on the **world clock**, read identically by the animation and the script, so the configuration you *see* is always the one granting its bonus — and every player sees the same one.
* Draw the Sun is a toggle whose cooldown starts on the **return**, so the risk is the decision of how long to keep the sun out.
* Statuses (Misclassified, Sun-Marked, Observed, Parallax) are one shared system with owners, timers and sigils, so they interact across abilities (e.g. Maw Rush feeds on Sun-Marked prey, the Frame hits Observed creatures harder).
* Hyphal Offset walks its path half a block at a time and refuses hazards, so it can never end inside a wall, lava or fire.

**Replaced (and why):**
* "Hesitation", "misreading", "influencing attention", "perceptual disturbance" → measurable effects (slowness, weakness, blows against the caster that miss), because the Script API cannot change a mob's target choice.
* Glowing marked creatures → floating sigils (Bedrock has no Glowing effect).
* Bathyas' anglerfish lure on the forehead → **the impaled sun is the lure**; the anglerfish shows in an atrophied crown light organ, glowing barbels and a needle underbite. Two lures would have competed for the same role.
* The drawn sword in the hand is the item's icon, drawn by the game like any sword, rather than a 3D held-item attachable whose placement in the hand could not be verified without a client.
* Abyssal Daybreak's darkness → a local dark haze for players within 24 blocks, never the world's lighting or time; the leviathans are particles, not mobs.
* Octamyces' levitation is visual (a hovering body) plus slow falling while sneaking in the air — not free flight, which would undermine the balance of every other race.

**New:** the Dinosauroid's neck rig (the skull follows your look without detaching); Bathyas' idle life — shielding his eyes from his own light, sighing, dozing off, poking the wound; the Octamyces' *Surveillance Idle* (after 7 s of stillness only the eye keeps working); the hyphal echo entity; Codex → Display Check, which now also offers a **still body** (the same body without animation) to a player whose own body was invisible only while animated — a workaround they can use at once while the cause is found.

**Limitations:** nothing was tested in a real game (see [TESTING.md](TESTING.md)); alpha-tested parts (membranes, feathers, crown plates, fins) cannot glow; the Dinosauroid and the Octamyces use 86 and 89 of the 90 bones a form may have; Morphological Drift stops when the daylight cycle is off and jumps with `/time set`; poses that turn the whole body (e.g. the Sickle Testament's pivot) can open a small gap at the hips for a moment, as with the other races.

### Technical limits and how they were met
* **Players' bodies:** like every race, the creatures are attachables worn in the head slot and following the player's skeleton; `minecraft:player` is not overridden, the hitbox is the player's.
* **Mob perception:** the Script API has no hook into a mob's target choice, so "hesitation" and "misreading" are slowness, weakness and blows that miss *the player who caused it* — effects you can measure.
* **"Glowing" marks:** Bedrock has no Glowing effect; statuses are shown by sigils over the creature's head.
* **The drawn sword** is a real item (rendered like any held weapon); the embedded sword is part of the 3D body. A 3D held-item attachable was not used because its placement in the hand cannot be verified without a client.
* **Heads on necks:** the Dinosauroid's skull and the Octamyces' cap sit on their own neck / stalk rigs that cancel the player's head look and re-apply part of it lower down, so the head never detaches when you look around. Player poses that would tilt the head bone (their ability poses, the rite of transformation) leave the head still for these two bodies.
* **The hyphal echo** is a helper entity rendering the Octamyces body (with its alpha-tested crown plates, fins and lattice) translucent with `entity_alphablend`; glowing parts are fainter in it because the texture's alpha also encodes glow.

## Shared systems built for this release

* **Lineage Codex** — selection with race portraits, detail pages (lore, strengths, weaknesses, passives, abilities with the original brief values), a confirmation step, the Rite of Unbecoming (policy-controlled race change), Veil/Manifest, Crest Infusion, Recall Focus, an archive of all races and operator settings. Opens once automatically for new players and never nags.
* **Rite ceremony** on transformation (rune aura in the race colour, arms-raised pose, title).
* **Ability engine** — cooldowns, charges, channels with explicit interruption rules, failure reasons that never waste a cooldown, a green aim reticle for targeted abilities, an action-bar HUD.
* **Persistence & safety** — per-player data (race, selection, cooldowns as remaining time, resources, enchantments, input locks) and world data (settings, Blood Moon); clean-up on death, logout, dimension change and race change; villagers, golems, pets, armour stands and (unless PvP is enabled) players are never hit; no terrain is modified.
* **Expansion-ready** — permanent race codes 001–009; a new race is one model module, one animation set and one `RaceDef` registered in `src/races/registry.ts` (see the README).
* **Added for Expansion 01:** helper entities with owners, lifetimes and guaranteed cleanup (`src/systems/proxies.ts`); Unique lineages with world-level claims (`src/systems/unique.ts`); Divine Jurisdiction (`src/systems/jurisdiction.ts`); explosion and item-use hooks for races; a race-wide 4-tick world hook; five-ability support in the engine, HUD and Codex; the Codex shows six lineages with the Unique badge and who holds it.
* **Added for Expansion 02:** creature statuses with owners, timers and floating sigils (`src/systems/status.ts`: MISCLASSIFIED, SUN-MARKED, OBSERVED, parallax-infected), shared by every race that wants them; toggle abilities whose first half costs no cooldown (`freeCast`, used by Draw the Sun); a real held weapon item owned by a lineage, with duplicate and recovery checks; forms that follow the environment (time of day, light) re-synchronised every quarter second; the translucent *hyphal echo* helper entity; and **Codex > Display Check**, which shows every body in front of the camera and asks which ones you could not see.

## Lore summary

* **The Mirefold (001):** a cave salamander lineage that swallowed the seeds of a carnivorous bog-bloom; the two organisms now share one bloodstream. Wet, they bloom; dry, they wait for rain.
* **The Unsleeping Masonry (002):** an empire carved its laws into basalt so they could never be forgotten; the laws remembered themselves and stood up. Its thoughts are written and rewritten on three turning rings.
* **The Hollow-Moon Kin (003):** hare-folk whose antlers are organs of the moon. When the full moon rises red, they remember what they were.
* **The Eyeless Choir (004):** a lineage of soil-dwellers that never needed eyes; they sing to each other through the ground, and they hear everything that walks on it.
* **The Noodly Existence (005):** in 2005 a letter described a deity of spaghetti and meatballs, invisible to science because it touches every measurement. Somewhere, it seems, the joke was taken literally.
* **The Uninvited Sovereign (006):** what the old yokai who walks into houses becomes in heaven — a sovereign of the celestial courts. It was never invited. It was always expected.
* **The Unclassified (007):** beak and teeth, feathers and armour, running legs that are also wings — no single lineage of the Mesozoic could have produced this body. It stares at other creatures for far too long, and nobody has ever learned what it concludes.
* **The Sun-Impaled (008):** something drove a white-gold sword through a creature of the deepest abyss, and the creature did not die; the sword became its heart. Bathyas is old, tired and constantly annoyed, mostly by his own light — and when he finally pulls it out, he goes very quiet.
* **The Eleventh Rift (009):** what stands in the world is only part of it — a fruiting body, eight groups of mycelium and an eye whose eleven rings each watch a different version of what is happening. It does not seem malicious. It watches.
