import { Player, system, Vector3 } from "@minecraft/server";
import { ActionFormData, ActionFormResponse, FormCancelationReason, MessageFormData, MessageFormResponse } from "@minecraft/server-ui";
import { ARCHON } from "./beings/archon.js";
import { OBSERVER } from "./beings/observer.js";
import { SOVEREIGN } from "./beings/sovereign.js";
import { burst, column, fade, flash, glyphs, ringWave, SEVEN, shake, sigil, sound, sphereWave, starfield, title } from "./core/fx.js";
import { addTask } from "./core/tasks.js";
import { add, v } from "./core/vec.js";
import { adopt, allBeings, BeingDef } from "./engine.js";

export interface Entry {
  def: BeingDef;
  icon: string;
  threat: string;
  summary: string;
  moves: [string, string][];
  ultimate: [string, string];
  reward: string;
}

export const BESTIARY: Entry[] = [
  {
    def: ARCHON,
    icon: "textures/items/dim11/folded_petal",
    threat: "Archon-class geometry",
    summary:
      "In M-theory six of the eleven dimensions are curled into a Calabi-Yau manifold too small to see. AEON-7 is a mind that evolved INSIDE that fold. " +
      "It appears as a porcelain-masked sovereign inside three gyroscopic rings, a cage of crystal around a burning core, six orbiting petals and a crown of seven shards - one per hidden dimension.",
    moves: [
      ["Manifold Lance", "Three helix beams aimed where you WILL be. Strafe unpredictably."],
      ["Spatial Fold", "Folds space to drag a distant or hiding target in front of it, then crushes them."],
      ["Compactification", "A sigil marks the ground; 1.5s later space collapses inward (10 dmg, rooted)."],
      ["Petal Storm (Phase II)", "Six petals spiral outward as blades."],
      ["Calabi Blink", "If you crowd it, it simply is somewhere else."],
    ],
    ultimate: ["THE SEVEN UNFOLD", "Rises and releases seven coloured dimension-waves - fire, force, levitation, poison, stasis, entropy, void. JUMP each wave. Then Recompactification drags everything back for a 14-damage implosion: run outward."],
    reward: "Folded Petal - fold-step through space (12-block blink).",
  },
  {
    def: SOVEREIGN,
    icon: "textures/items/dim11/string_of_creation",
    threat: "Bulk-class membrane",
    summary:
      "Our universe may be a membrane (a 'brane') floating through an eleven-dimensional bulk. The M5 Sovereign IS such a membrane - a vast leviathan whose glowing wings ripple like spacetime and whose crown is made of vibrating open strings.",
    moves: [
      ["String Resonance", "A vibrating string pierces everything in a 32-block line."],
      ["Brane Dive", "Telegraphed swoop through you and beyond (10 dmg, huge knockback)."],
      ["Brane Wall", "A moving membrane plane shoves everyone back."],
      ["Harmonic Chorus (Phase II)", "Releases closed-string wisps that hunt and detonate. Kill them."],
      ["Tidal Shear", "Wing sweep against anyone close."],
    ],
    ultimate: ["GENESIS COLLISION", "Two brane-images close in from both sides, pushing everyone to the middle. When they touch: a Big Bang (up to 26 dmg by distance) and a short cosmic inflation. Escape around the edges of the branes."],
    reward: "String of Creation - a piercing string lance.",
  },
  {
    def: OBSERVER,
    icon: "textures/items/dim11/eye_of_the_axis",
    threat: "Omniscient-class observer",
    summary:
      "If time is just another axis, a being outside it could look along it like a road. The Ophanim is a rotating hypercube folded around one great eye, circled by two wheels covered in eyes and six seraphic wings. It records where you were and predicts where you will be.",
    moves: [
      ["Gaze of Judgement", "Tracks you with a red line, locks, then fires. Change direction at the lock."],
      ["Timeline Echoes", "Three past-selves appear around you and fire in sequence."],
      ["Causality Lock", "Marks you; if it still sees you, you are rooted and struck. Break line of sight!"],
      ["Revelation Blink", "Shields and walls do not work: it appears behind you."],
      ["Ophanim Spin", "Its wheels lash out at close range."],
    ],
    ultimate: ["THE ELEVENTH AXIS", "Freezes everyone, REWINDS every player to where they were 8 seconds ago and un-happens up to 15% of its own damage, then judges 12 predicted futures with pillars of light. Keep moving."],
    reward: "Eye of the Axis - rewind yourself 5 seconds (position and health).",
  },
];

type AnyForm = ActionFormData | MessageFormData;

async function show<T extends ActionFormResponse | MessageFormResponse>(p: Player, form: AnyForm): Promise<T | undefined> {
  for (let i = 0; i < 20; i++) {
    const res = (await form.show(p)) as T;
    if (res.canceled && res.cancelationReason === FormCancelationReason.UserBusy) {
      await new Promise<void>((r) => system.runTimeout(() => r(), 5));
      continue;
    }
    return res;
  }
  return undefined;
}

function entryText(e: Entry): string {
  return (
    `${e.def.color}§l${e.def.name}§r §7- ${e.def.epithet}\n§8Threat: ${e.threat}\n\n§f${e.summary}\n\n` +
    `${e.def.color}§lABILITIES§r\n` +
    e.moves.map(([n, d]) => `§f${n}§7 - ${d}`).join("\n") +
    `\n\n§c§lULTIMATE: ${e.ultimate[0]}§r\n§7${e.ultimate[1]}\n\n§a§lINTELLIGENCE§r\n§7Learns the damage type you rely on and resists it for 30s, hunts whoever threatens it most, punishes hiding and fleeing, and grows stronger in Phase II (66%) and its True Form (33%). After each ultimate it is §eEXPOSED§7 for 4s (+50% damage taken).\n\n§d§lREWARD§r\n§7${e.reward}`
  );
}

export async function openResonator(p: Player, allowSummon = true): Promise<void> {
  const form = new ActionFormData()
    .title("§lEleventh-Dimensional Resonator")
    .body("§7The Resonator vibrates at the frequency of the hidden dimensions. Choose a being to study - or to call.\n§8Summoning needs open ground in front of you. Bring armour.");
  for (const e of BESTIARY) form.button(`${e.def.color}§l${e.def.name}\n§r§8${e.def.epithet}`, e.icon);
  const res = await show<ActionFormResponse>(p, form);
  if (!res || res.canceled || res.selection === undefined) return;
  const entry = BESTIARY[res.selection];
  const page = new ActionFormData().title(`${entry.def.color}§l${entry.def.name}`).body(entryText(entry));
  if (allowSummon) page.button(`§4§lSUMMON ${entry.def.name.toUpperCase()}`, entry.icon);
  page.button("§8Back");
  const r2 = await show<ActionFormResponse>(p, page);
  if (!r2 || r2.canceled || r2.selection === undefined) return;
  if (!allowSummon || r2.selection === 1) return openResonator(p, allowSummon);
  const confirm = await show<MessageFormResponse>(
    p,
    new MessageFormData()
      .title("§c§lOpen the Eleventh Dimension?")
      .body(`§7${entry.def.name} is a high-tier being with roughly 700 health and abilities that can kill an unprepared player.\n\nBegin the ritual?`)
      .button1("§c§lBegin the ritual")
      .button2("§7Not yet"),
  );
  if (!confirm || confirm.canceled || confirm.selection !== 0) return;
  ritual(p, entry.def);
}

function groundInFront(p: Player): Vector3 {
  const d = p.getViewDirection();
  const l = Math.hypot(d.x, d.z) || 1;
  const at = add(p.location, v((d.x / l) * 9, 0, (d.z / l) * 9));
  try {
    const hit = p.dimension.getBlockFromRay(add(at, v(0, 6, 0)), { x: 0, y: -1, z: 0 }, { maxDistance: 16 });
    if (hit) return { x: at.x, y: hit.block.location.y + 1.05, z: at.z };
  } catch {
    // ignore
  }
  return at;
}

export function ritual(p: Player, def: BeingDef): void {
  if (allBeings().some((b) => b.dim.id === p.dimension.id && Math.hypot(b.entity.location.x - p.location.x, b.entity.location.z - p.location.z) < 96)) {
    p.sendMessage("§c[Resonator] §7The eleventh dimension is already open nearby. Defeat the being that is here first.");
    return;
  }
  const at = groundInFront(p);
  const dim = p.dimension;
  sound(dim, "block.end_portal_frame.fill", at, 1.5, 0.6);
  p.sendMessage(`§d[Resonator] §7The air begins to fold... ${def.color}${def.name}§7 is listening.`);
  addTask("ritual", (age) => {
    if (age === 0) sigil(dim, add(at, v(0, 0.05, 0)), 9, 5.2);
    if (age % 10 === 0) glyphs(dim, add(at, v(0, 1.5, 0)));
    if (age % 14 === 0) {
      const k = (age / 14) % 7;
      const a = (k / 7) * Math.PI * 2;
      column(dim, SEVEN[k], add(at, v(Math.cos(a) * 4.5, 0, Math.sin(a) * 4.5)));
      sound(dim, "respawn_anchor.charge", at, 1, 0.6 + k * 0.12);
    }
    if (age === 60) starfield(dim, add(at, v(0, 4, 0)));
    if (age === 80) sound(dim, "mob.warden.sonic_charge", at, 2, 0.7);
    if (age < 100) return true;
    flash(dim, add(at, v(0, 3, 0)));
    sphereWave(dim, def.hue, add(at, v(0, 3, 0)));
    ringWave(dim, def.hue, add(at, v(0, 0.3, 0)), 14, 0.8);
    burst(dim, "white", add(at, v(0, 3, 0)));
    sound(dim, "mob.wither.spawn", at, 2, 0.8);
    try {
      const e = dim.spawnEntity(def.typeId, add(at, v(0, 3, 0)));
      e.setDynamicProperty("dim11:home", at);
      const b = adopt(e);
      b?.say(b.def.lines.intro[Math.floor(Math.random() * b.def.lines.intro.length)], true);
    } catch (err) {
      p.sendMessage(`§c[Resonator] The ritual failed: ${err}`);
    }
    for (const q of dim.getPlayers({ location: at, maxDistance: 64 })) {
      title(q, `${def.color}§l${def.name.toUpperCase()}`, `§7${def.epithet}`, 70);
      fade(q, def.fade, 0.2, 0.3, 1.2);
      shake(q, 0.3, 2);
    }
    return false;
  });
}
