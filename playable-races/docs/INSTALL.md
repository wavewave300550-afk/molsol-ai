# Installation Guide

**File to install:** [`dist/PlayableRaces.mcaddon`](../dist/PlayableRaces.mcaddon) (about 1 MB).
It contains the behavior pack *Playable Races: Foundation* and the resource pack *Playable Races: Foundation (Resources)*.
The two `.mcpack` files in `dist/` are the same packs, separated, for servers or manual installs.

| Requirement | Value |
|---|---|
| Minecraft Bedrock Edition | **1.26.60 or newer** (iOS, iPadOS, Android, Windows, Xbox, PlayStation, Switch, dedicated server) |
| Experimental toggles | **None** — leave every experiment off |
| Script API | `@minecraft/server` 2.11.0, `@minecraft/server-ui` 2.3.0 (built into the game, nothing to download) |
| Cheats | Not needed to play (only for the operator test commands) |

---

## iPhone / iPad (iOS & iPadOS)

1. Get `PlayableRaces.mcaddon` onto the device. AirDrop, iCloud Drive, a download in Safari, or an email attachment all work.
2. Open the **Files** app and find the file. In Safari: tap the download arrow, then the file.
3. Tap the file once. If iOS shows a preview page instead of opening Minecraft, tap the **Share** button (square with an up arrow) and choose **Minecraft**. If Minecraft is not listed, scroll the app row to **More** and enable it.
4. Minecraft opens and shows *Import Started...* and then *Successfully imported "Playable Races: Foundation"* (twice, once per pack).
5. Continue with [Activate in a world](#activate-in-a-world).

Troubleshooting on iOS:
* *"Unsupported file"* or the file opens as a ZIP: the name lost its extension. Rename it so it ends in `.mcaddon` (long-press the file > Rename), then try again.
* *"Duplicate pack detected"*: an older version is already installed. Delete it in Settings > Storage > Cached Data / Resource Packs / Behavior Packs, then import again.
* Nothing happens: update Minecraft from the App Store; versions older than 1.26.60 refuse the pack.

## Android

Tap the downloaded `.mcaddon` in your browser's downloads or a file manager and choose **Minecraft**. If Android offers "Open with", pick Minecraft and *Always*.

## Windows 10 / 11

Double-click `PlayableRaces.mcaddon`. Minecraft starts and imports both packs.

## Xbox, PlayStation, Nintendo Switch

Consoles cannot open `.mcaddon` files directly. Either play in a world hosted from a phone/PC with the add-on enabled (friends who join download the packs automatically), or upload a world that already contains the packs to a **Realm** from a PC or phone.

---

## Activate in a world

1. **Create New World** (or edit an existing world — make a backup first).
2. Open **Behavior Packs** > **Available** > select **Playable Races: Foundation** > **Activate**.
   Minecraft asks to also activate the resource pack it depends on — accept. (Activating the resource pack first does the same.)
3. Do **not** enable any experiments. The add-on uses only stable features.
4. Create / play the world.

On first join every player gets a **Lineage Codex** and the selection screen opens once. Pick a lineage, read it, and press **Embrace**. You receive your race's **Focus** item, and your racial body appears.

## Multiplayer and Realms

All players in the world use the same packs; joining players download the resource pack automatically (accept the download prompt). Every player chooses their own lineage; they are completely independent.

## Bedrock Dedicated Server

1. Unzip the two `.mcpack` files into `behavior_packs/PlayableRaces_BP` and `resource_packs/PlayableRaces_RP`.
2. Add them to the world's `world_behavior_packs.json` and `world_resource_packs.json`:
   ```json
   [{ "pack_id": "6a3f2c1e-8d4b-4f7a-9c2e-1b5d7e9f0a21", "version": [1, 0, 2] }]
   ```
   ```json
   [{ "pack_id": "9d6a5f4b-b07e-4cad-8f5b-4e8a0b2c3d54", "version": [1, 0, 2] }]
   ```
3. Set `texturepack-required=true` in `server.properties` so clients receive the resource pack.

## Updating and uninstalling

* A newer version with a higher pack version replaces the old one on import (current: **1.0.2**). If Minecraft reports a duplicate pack, delete the old *Playable Races* packs from Settings > Storage first. Lineages, cooldowns, hydration and other progress are stored on the players and the world and survive updates.
* To uninstall, deactivate both packs in the world. Racial effects are short, continuously refreshed effects, so they run out on their own (Health Boost within 2 minutes, everything else within seconds) and players return to normal. The crest and focus items belong to the add-on; once its item types are gone the game removes them (or shows them as unknown items, depending on version). The Salamander's swim-speed attribute returns to normal when the player next leaves water while the add-on is active, or on death. The player's own skin is shown again immediately.
