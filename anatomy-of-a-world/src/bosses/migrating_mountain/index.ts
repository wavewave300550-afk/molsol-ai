/** Boss 001 definition: THE MIGRATING MOUNTAIN. */
import { Player } from "@minecraft/server";
import { BossDefinition, registerBoss } from "../../core/registry.js";
import { ABILITY_IDS } from "./abilities.js";
import { MigratingMountainEncounter } from "./encounter.js";
import { DIMENSION } from "./ids.js";

export const MIGRATING_MOUNTAIN: BossDefinition = {
  id: "migrating_mountain",
  dimensionId: DIMENSION,
  summonItem: "anatomy:restless_lodestone",
  abilities: ABILITY_IDS,
  atlas: {
    number: "001",
    title: "THE MIGRATING MOUNTAIN",
    subtitle: "The Mountain That Never Belonged to the Earth",
    overview:
      "A colossal geological organism whose entire body is a mountain range: living strata, forests, rivers, waterfalls and minerals, all organs of one living system. It wanders the cloud sea, slowly, in search of geological balance.\n\nHeight 60–80 blocks · Length 100–140 blocks\nBody plan: Geological Organism\nLocomotion: Lithic Peristalsis (contraction and expansion of rock layers)",
    anatomy: [
      "§lMountain Shell§r — stratified rock and minerals; its dorsal biome is a forest you can walk on.",
      "§lMineral Circulation§r — glowing red veins carrying minerals and energy to every organ.",
      "§lLithic Heart§r — the amethyst core inside the Organ Cavern; shielded by the Resonance Network.",
      "§lMantle Musculature§r — maroon rock-muscle that moves the body and contracts its cavities.",
      "§lAnchorage Roots§r — fourteen root-legs that balance the body and carry it across the clouds.",
    ],
    abilities: [
      { name: "01 Continental Fold", text: "Fault lines glow, then the strata buckle into new ridges — paths on its back change." },
      { name: "02 Lithic Peristalsis", text: "The roots stomp and rolling waves of rock sweep the surface. Jump each wave in rhythm." },
      { name: "03 Geological Shedding", text: "The rock skin peels away and huge slabs fall on the marked rings." },
      { name: "04 Resonance Network", text: "Rings of resonance pulse from a node or the heart. Stand inside the green gaps." },
      { name: "05 Inverted Strata", text: "A walkway tears free and flips into a wall, or rolls overhead into a ceiling." },
      { name: "06 Mantle Contraction", text: "A cavity squeezes shut. Reach a glowing pocket (or the heart's ring) before it closes." },
      { name: "07 The Great Unfolding", text: "With its network broken the whole body opens like a flower and the arena becomes Phase 2; at low health it refolds again." },
    ],
    phases: [
      {
        name: "Phase 1 · The Sleeping Continent",
        text: "Climb and explore the body. Destroy the three Resonance Nodes: on the summit crag, inside the Organ Cavern (front tunnel), and hanging beneath the body (spiral shaft from the cavern down to the underbelly gallery).",
      },
      {
        name: "Phase 2 · The Unfolded World",
        text: "The shell unfolds, exposing the Lithic Heart on a disk of shifting ribs. Survive its attacks; after Resonance Network or Mantle Contraction its iris opens — strike then. Steam vents throw you back up if you fall onto the mantle floor.",
      },
    ],
    scale: "≈78 blocks tall, 116 long, 92 wide; a player is 1.8 blocks.",
    arena: "Its own void dimension: the boss's body is the arena, drifting over a sea of clouds.",
    summon: "Use a Restless Lodestone (tuff, amethyst shards, a compass and mossy cobblestone). Players within 32 blocks are drawn in with you.\n§6Reward§r Lithic Heart Shards — use one for Mountain's Resolve (Health Boost II + Resistance I for 5 minutes).",
  },
  create(party: Player[]) {
    return new MigratingMountainEncounter(MIGRATING_MOUNTAIN, party);
  },
};

registerBoss(MIGRATING_MOUNTAIN);
