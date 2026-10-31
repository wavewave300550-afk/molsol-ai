import { Player, Vector3, system } from "@minecraft/server";
import { ActionFormData, ActionFormResponse, FormCancelationReason, MessageFormData, MessageFormResponse } from "@minecraft/server-ui";
import { CHOIR } from "./bosses/choir.js";
import { EMPEROR } from "./bosses/emperor.js";
import { PARASITE } from "./bosses/parasite.js";
import { STAR } from "./bosses/star.js";
import { TITAN } from "./bosses/titan.js";
import { burst, column, debris, fade, flash, Hue, ringWave, shake, sigil, sound, sphereWave, title } from "./core/fx.js";
import { addTask } from "./core/tasks.js";
import { add, v } from "./core/vec.js";
import { adopt, allBosses, BossDef } from "./engine.js";

export interface Entry {
  def: BossDef;
  icon: string;
  size: string;
  look: string;
  signature: string;
  moves: [string, string][];
  ultimate: [string, string];
  reward: string;
}

export const BESTIARY: Entry[] = [
  {
    def: EMPEROR, icon: "textures/items/fb/crown_of_absence", size: "3.5 blocks tall, 4-block shard halo",
    look: "A living gothic throne on four clawed legs. No one sits on it: the seat is a hole of nothing that still holds the outline of its king. Two gauntlets float free beside it and a crowned porcelain mask hovers where a face should be.",
    signature: "Imperial Presence slows anyone who comes close. Its decrees punish those who look at it.",
    moves: [["Hand of Dominion", "a gauntlet slams the marked circle (11)"], ["Imperial Grasp", "lifts you into its hand - deal damage to break free"], ["Void Rifts", "three black holes that pull and burn"], ["Decree: Kneel (II)", "LOOK AWAY when it ends or be blinded (9)"], ["Throne Charge", "the throne gallops along the red line (12)"]],
    ultimate: ["CORONATION OF NOTHING", "The arena becomes void (3 dmg/0.5s). Only four golden candles of existence are safe and they go out one by one; whoever is outside the last candle is erased (18)."],
    reward: "Crown of Absence - turn invisible and step through the void.",
  },
  {
    def: TITAN, icon: "textures/items/fb/forge_heart", size: "6.5 blocks tall",
    look: "A walking temple-foundry: fluted marble shins, a brick chest with a colonnade and a blazing forge behind a turning gear, a domed observatory head with a lens and astrolabe, smoking chimneys, a gear halo, a forge hammer and an architect's caliper claw.",
    signature: "It builds: real blocks rise from the ground and are restored afterwards.",
    moves: [["Forge Hammer", "a 13-block shockwave line (13)"], ["Blueprint Prison", "walls you in, then drops molten rivets"], ["Pillars of Creation", "stone pillars erupt under you"], ["Molten Rivets", "six burning arcs"], ["Gear Halo Sweep", "punishes anyone close"]],
    ultimate: ["PRIME MOVER", "Builds four cover walls, charges, then sweeps a beam of creation twice around the arena. Keep a wall between you and its lens."],
    reward: "Forge Heart - raise a temporary stone wall.",
  },
  {
    def: STAR, icon: "textures/items/fb/star_heart", size: "8 blocks long",
    look: "A skeletal deep-sea leviathan: a charred skull inside a burning corona of spikes, rows of amber eyes, three nested mouths, an angler lure holding a tiny sun, an open ribcage around a living star, solar-flare wings and a comet tail.",
    signature: "Stellar gravity drags you towards it. DEVOUR swallows a player - mash SNEAK to tear free.",
    moves: [["Solar Flare Breath", "a sweeping fire beam"], ["Devour", "lunges and swallows; 5 sneaks escape"], ["Meteor Spit", "burning craters"], ["Hypnotic Lure (II)", "hold SNEAK to resist the pull"], ["Comet Tail", "spins against anyone close"]],
    ultimate: ["EVENT HORIZON", "It collapses into a black hole: everything is dragged towards the ring while solar flares strike. Anyone inside the ring when it goes supernova is devoured (24)."],
    reward: "Star Heart - a lance of solar fire.",
  },
  {
    def: PARASITE, icon: "textures/items/fb/parasite_seed", size: "7x6 blocks of 'terrain'",
    look: "A grassy hill with an oak tree. Until it wakes. Then the front of the hill opens into a maw of stalactite teeth, boulder eyelids roll back from two slit-pupilled eyes, fossil ribs flex, root-tentacles writhe and a heart beats in its torn-open back.",
    signature: "Dormant disguise; burrows (untouchable) and erupts beneath you; parasitic tethers drain you to heal it - run 16 blocks away to tear them.",
    moves: [["Burrow Ambush", "erupts under you (14)"], ["Root Spikes", "a line of erupting roots"], ["Parasitic Tethers", "drains up to three players"], ["Spore Cloud", "poison and nausea"], ["Tectonic Slam", "JUMP to avoid it"]],
    ultimate: ["CONTINENTAL BITE", "It sinks, the ground trembles, then it erupts as a giant maw under the group (22) and infects the surrounding earth (real blocks, restored after ~11s). Standing on infected earth hurts you and heals it."],
    reward: "Parasite Seed - drain nearby creatures to heal.",
  },
  {
    def: CHOIR, icon: "textures/items/fb/shard_of_truth", size: "6 blocks tall, 8-block wingspan",
    look: "A huge porcelain mask cracked with gold, one shard floating free, singing light from its open mouth. A halo of mirror fragments, a crown of glass, three tiers of framed mirror wings, lace ribbons, a column of glass rings and six orbiting choir masks.",
    signature: "MIRROR WARD: when the halo flares, 60% of your damage is reflected back. Its mirror images punish whoever strikes a reflection.",
    moves: [["Harmonic Chord", "three sung beams"], ["Reflections", "four mirror images that shoot"], ["Reflection Swap", "swaps players' positions"], ["Shattered Choir", "glass rains on predicted spots"], ["Chorister Orbit", "the masks sweep around it"]],
    ultimate: ["HALL OF INFINITE REFLECTIONS", "Six mirrors surround the arena and fire refraction beams. One mirror is true - it glows and chimes in gold. Break it to end the song and expose the Choir; strike a false one and it reflects. If time runs out: the Requiem (16)."],
    reward: "Shard of Truth - reflect damage back at attackers for a few seconds.",
  },
];

type Form = ActionFormData | MessageFormData;

async function show<T extends ActionFormResponse | MessageFormResponse>(p: Player, f: Form): Promise<T | undefined> {
  for (let i = 0; i < 20; i++) {
    const r = (await f.show(p)) as T;
    if (r.canceled && r.cancelationReason === FormCancelationReason.UserBusy) {
      await new Promise<void>((res) => system.runTimeout(() => res(), 5));
      continue;
    }
    return r;
  }
  return undefined;
}

function page(e: Entry): string {
  return `${e.def.color}§l${e.def.name}§r §7- ${e.def.epithet}\n§8${e.size}\n\n§f${e.look}\n\n§e§lSIGNATURE§r\n§7${e.signature}\n\n` +
    `${e.def.color}§lABILITIES§r\n${e.moves.map(([n, d]) => `§f${n}§7 - ${d}`).join("\n")}\n\n` +
    `§c§lULTIMATE: ${e.ultimate[0]}§r\n§7${e.ultimate[1]}\n\n§7Three phases (66% / 33%); each phase change triggers its ultimate. After an ultimate it is §eEXPOSED§7 (+50% damage).\n\n§d§lREWARD§r §7${e.reward}`;
}

export async function openSigil(p: Player, allowSummon: boolean): Promise<void> {
  const f = new ActionFormData().title("§lSigil of the Final Hour").body("§7Five final bosses answer this sigil. Study them - and call one, if you dare.\n§8Fight in open ground with full armour and potions.");
  for (const e of BESTIARY) f.button(`${e.def.color}§l${e.def.name}\n§r§8${e.def.epithet}`, e.icon);
  const r = await show<ActionFormResponse>(p, f);
  if (!r || r.canceled || r.selection === undefined) return;
  const e = BESTIARY[r.selection];
  const pg = new ActionFormData().title(`${e.def.color}§l${e.def.name}`).body(page(e));
  if (allowSummon) pg.button(`§4§lSUMMON`, e.icon);
  pg.button("§8Back");
  const r2 = await show<ActionFormResponse>(p, pg);
  if (!r2 || r2.canceled || r2.selection === undefined) return;
  if (!allowSummon || r2.selection === 1) return openSigil(p, allowSummon);
  const c = await show<MessageFormResponse>(p, new MessageFormData().title("§c§lSummon a Final Boss?").body(`§7${e.def.name} is a final boss. It can kill an unprepared player in seconds.\n\nBegin the ritual?`).button1("§c§lBegin").button2("§7Not yet"));
  if (c && !c.canceled && c.selection === 0) ritual(p, e.def);
}

function groundAt(dim: Player["dimension"], at: Vector3): Vector3 {
  try {
    const hit = dim.getBlockFromRay(add(at, v(0, 8, 0)), { x: 0, y: -1, z: 0 }, { maxDistance: 24 });
    if (hit) return { x: at.x, y: hit.block.location.y + 1, z: at.z };
  } catch {
    // ignore
  }
  return at;
}

function groundAhead(p: Player, dist: number): Vector3 {
  const d = p.getViewDirection();
  const l = Math.hypot(d.x, d.z) || 1;
  return groundAt(p.dimension, add(p.location, v((d.x / l) * dist, 0, (d.z / l) * dist)));
}

export function ritual(p: Player, def: BossDef): void {
  if (allBosses().some((b) => b.dim.id === p.dimension.id && Math.hypot(b.entity.location.x - p.location.x, b.entity.location.z - p.location.z) < 100)) {
    p.sendMessage("§c[Sigil] §7Another final boss already walks nearby. Defeat it first.");
    return;
  }
  const dim = p.dimension;
  if (def.startsDormant) {
    const a = Math.random() * Math.PI * 2;
    const g = groundAt(dim, { x: p.location.x + Math.cos(a) * 14, y: p.location.y, z: p.location.z + Math.sin(a) * 14 });
    sound(dim, "mob.warden.heartbeat", p.location, 2, 0.6);
    for (const q of dim.getPlayers({ location: p.location, maxDistance: 40 })) shake(q, 0.25, 2);
    p.sendMessage("§2[Sigil] §7The ground shudders... a hill nearby was not there a moment ago.");
    try {
      const e = dim.spawnEntity(def.typeId, g);
      e.setDynamicProperty("fb:home", g);
      adopt(e, false);
    } catch (err) {
      p.sendMessage(`§c[Sigil] The ritual failed: ${err}`);
    }
    return;
  }
  const at = groundAhead(p, 12);
  p.sendMessage(`§d[Sigil] §7The sigil burns. ${def.color}${def.name}§7 is coming.`);
  sound(dim, "block.end_portal_frame.fill", at, 1.5, 0.5);
  addTask("ritual", (age) => {
    if (age === 0) sigil(dim, add(at, v(0, 0.05, 0)), 12, 5.5);
    if (age % 12 === 0) {
      const k = age / 12;
      column(dim, def.hue as Hue, add(at, v(Math.cos(k) * 6, 0, Math.sin(k) * 6)));
      sound(dim, "respawn_anchor.charge", at, 1, 0.5 + k * 0.08);
    }
    if (age % 20 === 0) debris(dim, add(at, v(Math.random() * 6 - 3, 0.3, Math.random() * 6 - 3)));
    if (age === 80) sound(dim, "mob.warden.sonic_charge", at, 2, 0.6);
    if (age < 100) return true;
    flash(dim, add(at, v(0, 3, 0)));
    sphereWave(dim, def.hue as Hue, add(at, v(0, 3, 0)));
    ringWave(dim, def.hue as Hue, add(at, v(0, 0.3, 0)), 16, 0.8);
    burst(dim, "white", add(at, v(0, 3, 0)));
    sound(dim, "mob.wither.spawn", at, 2, 0.7);
    try {
      const e = dim.spawnEntity(def.typeId, at);
      e.setDynamicProperty("fb:home", at);
      adopt(e, true);
    } catch (err) {
      p.sendMessage(`§c[Sigil] The ritual failed: ${err}`);
    }
    for (const q of dim.getPlayers({ location: at, maxDistance: 72 })) {
      title(q, `${def.color}§l${def.name.toUpperCase()}`, `§7${def.epithet}`, 80);
      fade(q, def.fade, 0.2, 0.3, 1.2);
      shake(q, 0.35, 2.5);
    }
    return false;
  });
}
