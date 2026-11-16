# Testing report — Real-World Weapons, Base Release 01

Target: Minecraft Bedrock **26.60** (`min_engine_version` 1.26.60), `@minecraft/server` **2.11.0**,
no experimental toggles. Run everything with `npm test`, plus `python3 tools/previews.py` for the images.

## Automated results (this build)

| Stage | Tool | Result |
|---|---|---|
| Script type safety | `tsc --strict` against the official `@minecraft/server@2.11.0` typings | **0 errors** |
| Pack validation (Microsoft) | Minecraft Creator Tools 0.21.0 `validate` (debug-addon summary) | **0 errors, 0 warnings**. The remaining notes are by design: 42 optional recommendations about linking the vanilla glint texture and vanilla sounds, and 21 "likely noise" notes about the single-string `textures` form in `item_texture.json`, which Bedrock accepts |
| Static validation (ours) | `tools/validate.py` | **2,762 checks, 0 errors** (list below) |
| Runtime smoke test | `tools/smoke/smoke.mjs`: compiled script against a strict mock of `@minecraft/server` | **94 / 94 assertions** |
| Animation verification | Molang evaluator + Bedrock transform emulation (`tools/rww`) | see below |
| Visual verification | Software renderer, calibrated on Mojang's trident | `docs/images/*` |

### What `tools/validate.py` checks

* **Manifests:** valid UUIDs, mutual BP / RP dependencies, `@minecraft/server` 2.11.0 equals the
  installed typings, no beta modules, `min_engine_version` 1.26.60.
* **All 21 items:**
  * damage, durability and enchantability equal the balance table;
  * the attack cooldown is `type: "attack"` and `swing_duration` equals it;
  * piercing reach for the rapier and Zweihänder only; the katana keeps vanilla targeting;
  * fire resistance only on netherite, fuel only on wooden;
  * custom-component parameters, tags (and the absence of `minecraft:is_spear`), the icon (32×32
    RGBA, registered in `item_texture.json`), the display name in `en_US.lang`, repair items and
    Molang, and swing-sound events.
* **Recipes:** each pattern's keys match its key map, every ingredient and tag exists in vanilla
  1.26.60.5, every non-netherite item is craftable, every netherite item has a smithing upgrade from
  diamond, no two recipes collide, and furnace recycling outputs exist.
* **Creative catalog:** all 21 items listed exactly once, and the group names are localised.
* **Geometry:** every face UV is inside its texture, the bone hierarchy is consistent, and each model
  has a single root bound to the item slot.
* **Attachables:** one per item; geometry, texture (size matches the geometry), material, render
  controller and animations all resolve. Animated bones exist (case-insensitive).
* **Animations:**
  * All 69 generated Molang expressions parse.
  * Only known math functions with correct arity are used, and only vanilla queries (the 318 of
    1.26.60.5).
  * Player-animation bones exist in the vanilla rig, the arms animation overrides, and the body
    animation is additive.
* **Numeric sweep:** every bone stays finite and in range for 9 player states × (idle + 18 attack
  frames) × 3 weapons.
* **IK quality:**
  * Two-handed grip (left hand vs the grip axis) over 4 stances and 117 attack frames per weapon:
    **katana worst 0.29 / mean 0.027 units**, **Zweihänder worst 0.41 / mean 0.054 units**. The
    Minecraft fist is 4 units.
  * Shoulder offsets: ≤ 0.87 / 1.01 / 2.24 units (katana / Zweihänder / rapier).
  * No bone winds a full turn.
  * Largest per-frame change is 13–24° per 1/200 of a swing, i.e. no snaps.
* **Sounds:** every file referenced by `sound_definitions.json` exists in vanilla, and every swing
  sound event is defined.
* **Script ↔ packs:** the custom component name, every animation, controller and stop expression,
  every sound event and every particle the script uses exist.

### What the smoke test exercises

* Start-up registration of `rww:weapon`.
* All 21 items equip and start `arms` + `body` with the correct controllers and stop expressions.
* **Rapier:** +25 % at 3.0 blocks; none at 1.4 blocks or for projectiles; feedback particle.
* **Katana:** +50 % on the first strike after drawing; none on the second; none before the 4 s
  recharge; available again after it; window closes after 1 s.
* **Zweihänder:**
  * the cooldown starts when hefted;
  * the sweep hits only the hostile inside the 60° arc and range — not the villager, tamed wolf,
    armor stand, mob behind, far mob, or another player while PvP is off;
  * it does hit that player when PvP is on;
  * damage is 50 %, attributed to the player, and unaffected by other rules;
  * no sweep when the hit had no effect; extra knock-back on the primary target; sweep sound.
* **Durability:** one point per swing through several targets.
* **Animation lifecycle:** joiners receive existing poses; viewers re-entering range get targeted
  re-sends; re-sends after waking, respawn and dimension change; switching weapons; no traffic for
  vanilla items; clean leave.

The mock fails the run on any unknown animation, sound, particle, component id, damage cause, slot,
or world mutation inside a before-event (restricted execution).

## Calibration of the offline renderer

The emulator (mirrored X axis, ZYX Euler order, additive animation channels, bound bones at
`item pivot − 24 y`, per-face UV orientation) follows Blockbench's Bedrock codec. It was checked by
rendering **Mojang's own trident** with its vanilla attachable animations. Third person shows the
spear grip pointing forward and first person shows it prongs-up in the lower right, as in game. The
first-person camera (eye height 27.41 px, FOV 70.25°) is Blockbench's multi-file attachable preset.

## Not tested here: please verify in game

This environment has no Minecraft client. Bedrock Dedicated Server sessions through Creator Tools
need the user to accept the Minecraft EULA themselves. Checklist:

| # | Check | Expected |
|---|---|---|
| G1 | Import `dist/Real_World_Weapons.mcaddon`, enable the behaviour pack, no experiments | The Content Log shows no errors |
| G2 | Creative inventory → Equipment | Three groups (Rapiers, Zweihänder, Katanas), 7 items each, with icons |
| G3 | Craft each tier; upgrade diamond → netherite at a smithing table; smelt iron, gold and copper weapons | Recipes as in the README |
| G4 | Hold each weapon in third person (F5) and look at another player | Swept-hilt cage at the fist; two hands on the katana and Zweihänder grips; equip draw plays |
| G5 | Walk, sprint, sneak, jump, fall from 4+ blocks, swim, ride a horse, sleep | Matching poses; landing dip; the pose ends while sleeping or emoting and returns afterwards |
| G6 | Attack repeatedly | Three attacks cycle; the hotbar shows the cooldown; attacks are blocked until it ends (0.55 / 0.70 / 1.00 s) |
| G7 | First person, all three weapons | Hilt in the lower right; weapon-specific thrusts and cuts instead of the vanilla swing |
| G8 | Rapier against a mob at maximum reach (~3.5 blocks) | Hit lands; critical particles at ≥ 2.5 blocks |
| G9 | Draw the katana and strike within 1 s | Blue magic-critical particles, higher damage |
| G10 | Zweihänder into a group of zombies | Secondary zombies take damage and knock-back; villagers and pets are untouched |
| M1 | iOS / Android with the default touch layout | Normal tap / attack button works; no extra buttons |
| M2 | Mobile third-person view of another player | Poses render (runtime animations are client-side) |
| M3 | Mobile classic layout: tap a mob off-centre with the rapier or Zweihänder | Records whether piercing items resolve taps the way spears do (see technical design §4.2) |
| C1 | Use together with another add-on that edits the player (e.g. Tribes of the Cosmos in this repository) | Both work: this pack does not override any vanilla file |
