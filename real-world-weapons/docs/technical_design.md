# Technical design (Bedrock 26.60)

## 1. Platform research: what was verified, and how

| Topic | Finding | Source checked |
|---|---|---|
| Current stable release | Bedrock **26.60** (hotfixes 26.62 / 26.63). 26.70 is preview only | minecraft.wiki changelogs (via search), Mojang/bedrock-samples tag `v1.26.60.5` |
| Script API | `@minecraft/server` **2.11.0** is the newest stable module (2.12.0 is RC, 2.13.0 beta) | npm registry dist-tags; bedrock-samples `metadata/script_modules` |
| Item format | Latest item schema is 1.26.50; Creator Tools expects 1.26.60, which is used | `metadata/json_schemas/server/item`; Creator Tools validator |
| Attack speed | **Functional:** `minecraft:cooldown` with `"type": "attack"` blocks attacks for `duration` seconds, and custom cooldowns show on the hotbar since 26.10. Vanilla spears use exactly this | item schema; vanilla `iron_spear.json`; Microsoft Creator docs (Update 1.21.130 / 1.26.10) |
| Swing speed | **Visual only:** `minecraft:swing_duration` "affects visuals only and does not impact attack frequency". It is set equal to the cooldown, as Mojang does for spears | item schema description; MS Learn |
| Reach | **Functional:** `minecraft:piercing_weapon` `reach {min,max}` / `creative_reach` / `hitbox_margin`. It hits every entity on the view line and the item can no longer mine blocks | item schema; vanilla spears; Bedrock Wiki item format history |
| Damage | `minecraft:damage` is *added* to the player's base attack damage of 1 | MS Learn component reference |
| Vanilla sword baseline (Bedrock) | Damage 5/6/6/7/5/8/9 and durability 60/132/191/251/33/1562/2032 for wood/stone/copper/iron/gold/diamond/netherite. No attack cooldown | Minecraft Wiki "Sword" (via search) |
| Hurt immunity | 10 ticks (0.5 s); a weaker or equal hit during immunity is ignored | Minecraft Wiki "Damage" (via search) |
| Spear arm poses | Triggered by the `minecraft:is_spear` item tag, not by `piercing_weapon`. Our items do not carry that tag | vanilla `zombie.entity.json` etc. (`v.melee_spear_equipped = q.equipped_item_any_tag(..., 'minecraft:is_spear')`); Bedrock Wiki |
| Swing sounds | Since 26.60, custom `sound_definitions.json` names work in `minecraft:swing_sounds` for item format ≥ 1.26.50 | Bedrock Wiki item format history (1.26.60) |
| First-person arm | The vanilla render controller shows the right arm in first person only when the hand is **empty** (or holds a map). Holding a sword shows only the item | vanilla `player.render_controllers.json` |
| Player animation hooks | `Entity.playAnimation(name, {controller, stopExpression, blendOutTime, players})` is stable. Runtime controllers live on the client copy of the entity and reset when it unloads | MS Learn API docs; Bedrock Wiki "playanimation" |
| Script events | `world.afterEvents.playerSwingStart`, `world.beforeEvents.entityHurt` (damage is writable), custom item components with `onHitEntity` / `onBeforeDurabilityDamage`, and `ItemCooldownComponent.startCooldown` are all stable in 2.11.0 | `server-bindings_2.11.0.json`, `@minecraft/server@2.11.0` typings |
| Geometry / animation conventions | Mirrored X axis, ZYX Euler order with (−x, −y, z) conversion, additive Euler animation channels, `override_previous_animation`, up/down per-face UV flip, bound bones at `item pivot − 24 y` | Blockbench source (Bedrock codec, attachable preview); calibrated by rendering Mojang's trident with its vanilla animations |

## 2. Combat design

### Native item behaviour (JSON only)

| | Rapier | Zweihänder | Katana |
|---|---|---|---|
| Damage per hit | = vanilla sword of the tier (S) | 2 S | 1.4 S |
| Attack cooldown (= swing) | 0.55 s | 1.00 s | 0.70 s |
| Reach | 3.6 (piercing line, margin 0.15) | 4.0 (piercing line, margin 0.35) | vanilla 3.0 (normal targeting, can mine) |
| Durability | 0.9 × sword | 1.25 × sword | = sword |
| Enchanting | `sword` slot, vanilla tier enchantability | same | same |

Single-target damage per second, using the 0.5 s hurt immunity that also caps vanilla swords:
rapier 0.91×, Zweihänder 1.00× and katana 0.95–1.03× of the vanilla sword of the same tier. The
trade-offs are reach, rhythm and the rules below. Full table: [README](../README.md#weapons-and-stats).

### Script rules (`src/combat.ts`)

* **Rapier: stoccata at long measure.** A melee hit whose target stands ≥ 2.5 blocks away
  (horizontally) does +25 %. This rewards fencing at the edge of reach.
* **Katana: iai draw-cut.** The first hit within 1 s of drawing the katana does +50 %. It recharges
  4 s after use, and one re-draw is needed per cut.
* **Zweihänder: sweep, knock-back and heft.**
  * After a successful hit, other targets within 3.6 blocks and ±60° of the view take 50 % of the
    weapon's damage, plus knock-back.
  * The sweep skips players unless the `pvp` game rule is on, all tamed animals, villagers, wandering
    traders, golems, allays and armor stands.
  * The primary target gets extra knock-back.
  * Drawing the sword starts its 1 s attack cooldown (hefting time).
* **Durability:** a piercing thrust or cut that passes through several mobs costs 1 point, not one
  per mob.

Damage is applied by the engine at the moment of the click. The animations therefore strike within
the first ~22 % of the swing and spend the rest in a visible recovery. That recovery lasts exactly as
long as the functional cooldown.

## 3. Rendering and animation architecture

### Item models: attachables

There are three geometries (`geometry.rww.rapier|zweihander|katana`, 66 / 63 / 26 cubes,
per-face UV, 8 px per unit) and 21 textures sharing each geometry's UV layout. Each item has an
attachable whose root bone binds to `q.item_slot_to_bone_name(c.item_slot)`. Two static animations
place the sword in the hand:

* `hold_tp`: the blade is perpendicular to the forearm, like any held sword.
* `hold_fp`: solved so the hilt sits in the lower right of the view and the blade rises toward the
  crosshair.

Enchanted items use the vanilla glint material and texture.

### Player animation: why not override `player.entity.json`

Animating the player's arms normally means replacing the vanilla player client entity. That
breaks every other add-on doing the same, including this repository's Tribes of the Cosmos add-on,
and freezes the player at today's vanilla until the pack is updated. Instead,
`src/animation.ts` starts two looping animations per weapon with `Entity.playAnimation`, in
dedicated runtime controllers:

| Animation | Bones | Mode | Contents |
|---|---|---|---|
| `animation.rww.<w>.arms` | rightArm, leftArm, rightItem | `override_previous_animation` | Guard; walk / sprint / sneak / airborne / landing / swim / (carry); equip draw; 3 attacks; first-person branch |
| `animation.rww.<w>.body` | body, rightLeg, leftLeg | additive | Torso twist and lean, lunges and steps; cancels the vanilla attack body twist |

* **Client-side state machine.** All per-frame logic runs on the client in Molang. That covers
  smoothed state weights using `q.delta_time` (walk, sprint, sneak, air, swim, landing dip),
  attack progress from the engine's own `variable.attack_time` (so animation and cooldown cannot
  drift apart), a combo counter that cycles the 3 variants on each new swing (rising edge of
  `attack_time`, reset after 2.5 s), and the equip intro (a per-weapon heartbeat, so re-sending
  never replays the draw). The server only sends the two animations when a weapon is drawn.
* **Lifecycle.**
  * Each animation stops itself through its stop expression
    (`!q.equipped_item_any_tag('slot.weapon.mainhand','rww:<w>') || q.is_sleeping || q.is_emoting`).
  * The script re-sends on equip, respawn, dimension change and waking up.
  * It sends targeted copies (`players: [...]`) to players who join or come back within 48 blocks,
    because the client drops runtime controllers when an entity unloads.
* **Two-handed grips without elbows.** Minecraft arms are rigid 12-unit boxes.
  * For each key pose, the sword (grip centre, blade and edge directions) is solved with inverse
    kinematics (`tools/rww/posing.py`) into arm and wrist (rightItem) angles, plus small shoulder
    offsets (≤ 1.0 unit for two-handers, ≤ 2.2 for the rapier).
  * The torso twist of each key is compensated, so the sword lands where authored even while the
    body turns.
  * Keys are interpolated with quaternion slerp and IK-resolved sub-keys. Euler forms are picked by
    dynamic programming so no bone ever winds through a full turn. The result is baked into
    Catmull-Rom curves of `attack_time`.
* **First person.** Holding an item hides the arm in vanilla first person, but the vanilla
  first-person swing still moves the item. The arms animation therefore re-creates the vanilla
  first-person arm pose (including the equip lowering and walk bob) without that swing, and adds
  weapon-specific first-person motions authored in camera space.

### Assumption that could not be tested here

The runtime controllers are assumed to evaluate **after** the player's own animation controllers.
That is how controllers created by `/playanimation` behave in community usage, and the override
animation relies on it to replace the vanilla arm swing. If a future engine evaluated them first,
the vanilla swing and walk would be added on top of these poses, which would still look plausible
rather than broken. The additive torso and leg animation is order-independent.

## 4. Limitations

1. **No in-game test was possible in this environment.** There is no Minecraft client, and starting
   the Bedrock Dedicated Server through Creator Tools requires accepting the Minecraft EULA, which is
   the user's decision. Rendering was checked with an offline emulator that matches Mojang's data;
   see the [testing report](testing_report.md) for the in-game checklist.
2. **Piercing reach.** `minecraft:piercing_weapon` hits every entity on the view line, and the rapier
   and Zweihänder cannot mine blocks. The component is the same one Mojang ships on spears for every
   platform. How a *classic* touch tap on an off-centre mob is resolved for piercing items is
   **not verified**, so test it on iOS (checklist item M3). The crosshair touch layout aims exactly
   like a mouse. The katana keeps vanilla targeting.
3. **Elbow-less two-handed grips.** Stiff Minecraft arms keep the hands at chest height. The left hand
   is solved onto the grip (worst-case error 0.41 units) but cannot bend around it.
4. **Off-hand items** (shield, torch) still render in the left hand while a two-hander is held.
   The pose does not hide them, and Bedrock offers no stable way to do so without overriding vanilla.
5. **Pose start latency.** The player pose starts about 2 ticks plus network latency after drawing.
   The first frames use the vanilla pose.
6. **Hilt scale.** Grips and guards are enlarged (documented in
   [historical_references.md](historical_references.md)) so the 4-unit Minecraft fist can hold them.
7. **Mobs holding these items** use the same attachable. Their third-person grip is tuned for the
   player skeleton.
