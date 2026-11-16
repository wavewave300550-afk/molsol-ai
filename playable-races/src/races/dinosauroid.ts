/**
 * Race 007 - The Unknown Dinosauroid (Expansion 02, v1.4.0)
 *
 * A taxonomic impossibility: an intelligent, quiet theropod-shaped organism assembled from
 * incompatible prehistoric lineages - beak and teeth, feathers and osteoderms, running legs
 * that are also wings and display organs.  Its system is TAXONOMIC COLLAPSE:
 *  - Morphological Drift: the body slowly cycles through four configurations (Plumed,
 *    Webbed, Toothed, Fanned).  The animation reads the same clock (world time), so what you
 *    see is the bonus you get.
 *  - Ancestral Misprint: creatures that witness its displays become MISCLASSIFIED - slowed,
 *    weakened, and their blows against it often miss.  (Bedrock gives scripts no handle on a
 *    mob's target selection, so the misreading is expressed through these real effects.)
 *  - Evolutionary Overflow: Taxonomic Error activates every contradictory structure at once.
 */
import { Entity, EntityHurtBeforeEvent, Player, system, world } from "@minecraft/server";
import { message, tempForm } from "../core/abilities.js";
import { effect, hurt, knock, knockFrom } from "../core/combat.js";
import { particle, pose, privateParticle, sound } from "../core/fx.js";
import { Session, flag, hasFlag } from "../core/session.js";
import { after, repeat } from "../core/tasks.js";
import { aimTarget, alive, chest, enemiesNear, isSolid } from "../core/targets.js";
import { add, angleBetween, dist, flat, mul, norm, sub, v3 } from "../core/util.js";
import { clearStatus, clearStatusesBy, hasStatus, setStatus } from "../systems/status.js";
import { AbilityDef, RaceDef } from "./types.js";

// ------------------------------------------------------------------ morphological drift

export const DRIFTS = ["Plumed", "Webbed", "Toothed", "Fanned"] as const;
const DRIFT_HINT = ["Hindwing Veer carries 25% farther", "a sneaking glide and half fall damage", "+1 melee damage", "displays reach 3 blocks farther"];

/** Same phase as the animation: math.mod(q.time_of_day * 16, 4) (q.time_of_day: midnight = 0). */
export function drift(): number {
  let ticks = 0;
  try {
    ticks = world.getTimeOfDay();
  } catch {
    ticks = 0;
  }
  const tod = ((ticks + 6000) % 24000) / 24000;
  return Math.floor((tod * 16) % 4);
}

const overflow = (s: Session) => hasFlag(s, "overflow");
const staring = new Map<string, { id: string; since: number }>();
const NIGHT_LIGHT = 6;

function dark(p: Player): boolean {
  try {
    const at = add(p.location, v3(0, 1, 0));
    return p.dimension.getLightLevel(at) < NIGHT_LIGHT;
  } catch {
    try {
      const t = world.getTimeOfDay();
      return t >= 13000 && t <= 23000;
    } catch {
      return false;
    }
  }
}

/** Ornamental anatomy in confined spaces: a solid block right above the head. */
function cramped(p: Player): boolean {
  try {
    const b = p.dimension.getBlock(add(p.location, v3(0, 2.05, 0)));
    return isSolid(b);
  } catch {
    return false;
  }
}

const ROUGH = /(stone|cobble|gravel|andesite|diorite|granite|deepslate|tuff|basalt|blackstone|calcite|dripstone|sandstone|terracotta|bone_block|_ore|obsidian|netherrack|mud_bricks|packed_mud|end_stone|magma|sand$|red_sand)/;

function onRough(p: Player): boolean {
  try {
    const b = p.dimension.getBlock(add(p.location, v3(0, -0.2, 0)));
    return !!b && ROUGH.test(b.typeId);
  } catch {
    return false;
  }
}

/** Misclassify a creature (slowed, weakened, its blows on the Dinosauroid may miss). */
function misclassify(p: Player, e: Entity, ticks: number): void {
  setStatus(e, "misclassified", ticks, p.id);
  effect(e, "slowness", ticks, 1);
  effect(e, "weakness", ticks, 0);
  try {
    const h = e.getHeadLocation();
    particle(e.dimension, "plrace:misclass_mark", v3(h.x, h.y + 0.55, h.z));
  } catch {
    /* ignore */
  }
}

function displayRadius(s: Session): number {
  return 7 + (drift() === 3 ? 3 : 0) + (overflow(s) ? 2 : 0);
}

// ------------------------------------------------------------------ 1. Hindwing Veer

const veer: AbilityDef = {
  id: "hindwing_veer",
  name: "Hindwing Veer",
  short: "Veer",
  cooldown: 14,
  original: "Cooldown 14 s; hindlimb membranes and feathered secondary wings deploy; sudden directional leap, evasive movement or short controlled glide (evasion, repositioning, closing distance, limited aerial manoeuvring) - never unrestricted sustained flight. Lower, compress, push off, unfold, change trajectory, tail corrects, fold back.",
  desc: "Crouch, compress and burst ~7 blocks in the direction you are moving (forward when standing), hindwings and membranes snapping open; the tail steers. Hold SNEAK in the air to glide down on them (about 1.5 s, then they fold). No fall damage from the leap, and a blow landing in the next 0.6 s is halved. Plumed drift: 25% farther. During Taxonomic Error it recovers twice as fast.",
  cast({ p, s }) {
    let dir = flat(p.getViewDirection());
    try {
      const vel = p.getVelocity();
      if (Math.hypot(vel.x, vel.z) > 0.06) dir = flat(vel);
    } catch {
      /* standing */
    }
    const far = drift() === 0 ? 1.25 : 1;
    tempForm(p, s, "veer", 40);
    pose(p, "dino_veer");
    sound(p.dimension, "mob.phantom.flap", p.location, 1, 0.75);
    sound(p.dimension, "mob.breeze.jump", p.location, 0.6, 1.3);
    particle(p.dimension, "plrace:veer_burst", add(p.location, v3(0, 0.1, 0)));
    after(3, () => {
      if (!p.isValid) return;
      knock(p, mul(norm(dir), 2.1 * far), 0.55);
    }, p.id, "veer");
    flag(s, "nofall", 80);
    flag(s, "evade", 12);
    flag(s, "glide", 50);
    repeat(3, 7, () => {
      if (p.isValid) particle(p.dimension, "plrace:veer_trail", add(p.location, v3(0, 0.6, 0)));
    }, p.id, "veer_fx", 4);
    return true;
  },
};

// ------------------------------------------------------------------ 2. Crest of Misclassification

const crest: AbilityDef = {
  id: "crest_of_misclassification",
  name: "Crest of Misclassification",
  short: "Crest",
  cooldown: 24,
  original: "Cooldown 24 s; cranial crest, throat pouch and ornamental feathers activate together in a spectacular biological display; brief enemy hesitation, disrupted targeting, misread movement, a Misclassification status. An extreme animal display, not magical energy.",
  desc: "Crest raised, throat pouch swollen, every feather fan and the tail fan spread: an impossible display. Every hostile creature within 7 blocks (10 when Fanned, +2 in Taxonomic Error) flinches back and is MISCLASSIFIED for 7 s: Slowness II and Weakness, and half of its blows on you miss. Hostile players in PvP are misclassified for 3 s. Sickle Testament punishes the misclassified.",
  cast({ p, s }) {
    const r = displayRadius(s);
    tempForm(p, s, "display", 50);
    pose(p, "dino_display");
    particle(p.dimension, "plrace:crest_wave", add(p.location, v3(0, 0.15, 0)));
    sound(p.dimension, "mob.parrot.idle", p.location, 1.2, 0.45);
    sound(p.dimension, "mob.sniffer.long_sniff", p.location, 0.9, 1.6);
    sound(p.dimension, "mob.warden.clicking", p.location, 0.6, 1.8);
    let n = 0;
    for (const e of enemiesNear(p, p.location, r)) {
      const isPlayer = e.typeId === "minecraft:player";
      misclassify(p, e, isPlayer ? 60 : 140);
      knockFrom(e, p.location, 0.45, 0.12);
      n++;
    }
    message(s, n ? `§3${n} creature${n > 1 ? "s" : ""} misread what they see` : "§7Nothing here to be confused", 40);
    return true;
  },
};

// ------------------------------------------------------------------ 3. Sickle Testament

const sickle: AbilityDef = {
  id: "sickle_testament",
  name: "Sickle Testament",
  short: "Sickle",
  cooldown: 20,
  range: 4,
  cone: 60,
  original: "Cooldown 20 s; a specialised attack with the enlarged sickle claws of the hindlimbs: swift diagonal or rotational strike; enemies under Misclassification receive an enhanced follow-up interaction. Its own readable, biologically inspired animation.",
  desc: "A pivoting hindlimb strike: the raised sickle claw rakes everything in a 120-degree arc 4 blocks in front of you for 6 damage (+1 when Toothed). A MISCLASSIFIED creature is opened up instead: 10 damage, pinned in place (Slowness IV, 1.5 s) and the misclassification is spent. During Taxonomic Error the strike spins all the way round.",
  cast({ p, s }) {
    pose(p, "dino_sickle");
    sound(p.dimension, "mob.ravager.bite", p.location, 0.6, 1.6);
    sound(p.dimension, "item.trident.throw", p.location, 0.8, 0.7);
    const full = overflow(s);
    after(4, () => {
      if (!p.isValid) return;
      const view = flat(p.getViewDirection());
      particle(p.dimension, "plrace:sickle_arc", add(p.location, add(mul(view, 1.4), v3(0, 0.7, 0))), { spin: full ? 1 : 0 });
      const base = 6 + (drift() === 2 ? 1 : 0);
      let hits = 0;
      for (const e of enemiesNear(p, p.location, 4.2)) {
        const to = flat(sub(e.location, p.location));
        if (!full && dist(e.location, p.location) > 1.2 && angleBetween(view, to) > 60) continue;
        const marked = hasStatus(e, "misclassified");
        if (marked) {
          hurt(e, base + 4, p);
          effect(e, "slowness", 30, 3);
          clearStatus(e, "misclassified");
          particle(e.dimension, "plrace:misclass_mark", add(chest(e), v3(0, 0.6, 0)));
        } else hurt(e, base, p);
        knockFrom(e, p.location, marked ? 0.2 : 0.7, 0.2);
        hits++;
      }
      if (hits) sound(p.dimension, "item.trident.hit", p.location, 1, 0.8);
    }, p.id, "sickle");
    return true;
  },
};

// ------------------------------------------------------------------ 4. Taxonomic Error

const OVERFLOW_TICKS = 240;

const error: AbilityDef = {
  id: "taxonomic_error",
  name: "Taxonomic Error",
  short: "Error",
  cooldown: 42,
  original: "Cooldown 42 s; maximum anatomical display state: cranial crest, throat pouch, hindlimb membranes, tail fan, dorsal bristles, distinctive ocular appearance; enhanced mobility, modified attacks, stronger Ancestral Misprint, interactions with the other three skills. A catastrophic-looking expression of impossible anatomy, not a magic transformation.",
  desc: "For 12 s every contradictory structure activates at once: Speed I and Jump Boost II, your other abilities recover 40% faster, Sickle Testament spins full circle, displays reach 2 blocks farther, and every 2 s each hostile creature within 5 blocks becomes MISCLASSIFIED. Your melee blows misclassify too. Afterwards the body is spent: Slowness and Weakness for 4 s.",
  check({ s }) {
    return overflow(s) ? "Taxonomic Error is already unfolding" : undefined;
  },
  cast({ p, s }) {
    flag(s, "overflow", OVERFLOW_TICKS);
    tempForm(p, s, "overflow", OVERFLOW_TICKS);
    pose(p, "dino_error");
    effect(p, "speed", OVERFLOW_TICKS, 0, false);
    effect(p, "jump_boost", OVERFLOW_TICKS, 1, false);
    particle(p.dimension, "plrace:overflow_aura", add(p.location, v3(0, 0.1, 0)));
    sound(p.dimension, "mob.warden.roar", p.location, 0.35, 1.9);
    sound(p.dimension, "mob.parrot.imitate_creaking", p.location, 1, 0.6);
    repeat(40, OVERFLOW_TICKS / 40, () => {
      if (!p.isValid) return;
      for (const e of enemiesNear(p, p.location, 5)) misclassify(p, e, 80);
      particle(p.dimension, "plrace:dino_display", add(p.location, v3(0, 1.6, 0)));
    }, p.id, "overflow", 20);
    after(OVERFLOW_TICKS, () => {
      if (!p.isValid) return;
      effect(p, "slowness", 80, 0, false);
      effect(p, "weakness", 80, 0, false);
      message(s, "§7The body folds back into something nameable... exhausted", 50);
    }, p.id, "overflow_end");
    message(s, "§3§lTAXONOMIC ERROR", 50);
    return true;
  },
};

// ------------------------------------------------------------------ race

export const dinosauroid: RaceDef = {
  code: "007",
  key: "dinosauroid",
  name: "The Unknown Dinosauroid",
  thai: "ไดโนซอรอยด์นิรนาม",
  title: "The Taxonomic Impossibility",
  color: "§3",
  tagline: "An anatomical contradiction that should not exist - and is watching you.",
  lore: [
    "Beak and teeth, feathers and armour, running legs that are also wings: no single lineage of the Mesozoic could have produced this body. It is as if several incompatible evolutionary histories had been assembled into one organism and left to walk.",
    "It is quiet. It is patient. It stares at other creatures for far too long, and nobody has ever learned what it concludes.",
  ],
  strengths: [
    "Hindwing Veer: a fast, steerable leap-glide for evasion and closing distance",
    "Crowd control through MISCLASSIFICATION: slowed, weakened enemies whose blows often miss",
    "Sickle Testament punishes misclassified enemies hard",
    "Fast on rough, rocky ground",
  ],
  weaknesses: [
    "Lightly armoured - nothing like the Runic Titan Golem",
    "No sprint advantage on open ground (the Jackalope is faster)",
    "Ornamental anatomy is clumsy under low ceilings (Slowness I in 2-block tunnels)",
    "Taxonomic Error is temporary and leaves the body spent",
  ],
  passives: [
    { name: "Morphological Drift", desc: "Every ~75 s the body drifts to another configuration: PLUMED (Veer 25% farther), WEBBED (sneak in the air to glide; fall damage halved), TOOTHED (+1 melee damage), FANNED (displays reach 3 blocks farther). The HUD shows the current one; the body shows it too." },
    { name: "Fossil Memory", desc: "On rough ground - stone, gravel, sand, tuff, deepslate, basalt, terracotta - the old legs remember: Speed I." },
    { name: "Unreadable Posture", desc: "Its telegraphs make no sense to other animals: 15% of melee blows from creatures miss outright (50% from the MISCLASSIFIED)." },
    { name: "Display Organism", desc: "At night (and in the deep dark) the display skin glows and every display reaches 2 blocks farther." },
    { name: "Primitive Intelligence", desc: "Look at a creature without moving for 2 s and you have studied it: its health is shown and it counts as MISCLASSIFIED for your next Sickle Testament." },
  ],
  abilities: [veer, crest, sickle, error],
  focusItem: "plrace:focus_dinosauroid",
  focusName: "Fossil Quill Focus",
  controls: ["Unknown Dinosauroid: hold §fSNEAK§7 in the air after Hindwing Veer to glide (always possible while WEBBED)."],
  variant(p, s) {
    if (overflow(s)) return "overflow";
    return dark(p) ? "night" : "";
  },
  cooldownMul(_p, s) {
    return overflow(s) ? 0.6 : 1;
  },
  init() {
    /* stateless */
  },
  cleanup(p) {
    clearStatusesBy(p.id);
    staring.delete(p.id);
  },
  release(s) {
    clearStatusesBy(s.id);
    staring.delete(s.id);
  },
  tick20(p, s) {
    if (onRough(p) && p.isOnGround) effect(p, "speed", 30, 0, false);
    if (cramped(p) && !overflow(s)) effect(p, "slowness", 30, 0, false);
    // Primitive Intelligence: a long stare reads the creature
    let moving = false;
    try {
      const v = p.getVelocity();
      moving = Math.hypot(v.x, v.z) > 0.03;
    } catch {
      moving = false;
    }
    const t = moving ? undefined : aimTarget(p, 16, 6);
    const prev = staring.get(p.id);
    if (!t || !alive(t)) {
      staring.delete(p.id);
      return;
    }
    if (!prev || prev.id !== t.id) {
      staring.set(p.id, { id: t.id, since: system.currentTick });
      return;
    }
    if (system.currentTick - prev.since >= 40 && !hasStatus(t, "misclassified", p.id)) {
      setStatus(t, "misclassified", 200, p.id);
      let hp = "";
      try {
        const h = t.getComponent("minecraft:health");
        if (h) hp = ` §f${Math.ceil(h.currentValue)}/${Math.ceil(h.effectiveMax)} HP`;
      } catch {
        /* ignore */
      }
      message(s, `§3Studied:§7 ${t.typeId.replace("minecraft:", "")}${hp}`, 60);
      privateParticle(p, "plrace:misclass_mark", add(chest(t), v3(0, 0.9, 0)));
    }
  },
  tick5(p, s) {
    // Webbed drift (or a fresh Veer): sneak in the air to glide on the hindwings
    if (!p.isOnGround && p.isSneaking && !p.isInWater && (drift() === 1 || hasFlag(s, "glide") || overflow(s))) {
      let vy = 0;
      try {
        vy = p.getVelocity().y;
      } catch {
        vy = 0;
      }
      if (vy < -0.12) effect(p, "slow_falling", 10, 0, false);
    }
  },
  hud(_p, s) {
    const d = drift();
    const st = overflow(s) ? "§3§lTAXONOMIC ERROR" : `§7${DRIFT_HINT[d]}`;
    return `§3Drift §f${DRIFTS[d]} §8| ${st}`;
  },
  onHurt(p, s, ev: EntityHurtBeforeEvent) {
    const cause = ev.damageSource.cause as string;
    if (cause === "fall" && (hasFlag(s, "nofall") || drift() === 1)) {
      ev.damage *= hasFlag(s, "nofall") ? 0 : 0.5;
      if (ev.damage <= 0) ev.cancel = true;
      return;
    }
    if (hasFlag(s, "evade")) ev.damage *= 0.5;
    const src = ev.damageSource.damagingEntity;
    if (src && cause === "entityAttack" && src.typeId !== "minecraft:player") {
      const miss = hasStatus(src, "misclassified") ? 0.5 : 0.15;
      if (Math.random() < miss) {
        ev.cancel = true;
        system.run(() => {
          if (p.isValid) particle(p.dimension, "plrace:dino_feathers", add(p.location, v3(0, 1.1, 0)));
        });
      }
    }
  },
  onDealDamage(p, s, ev: EntityHurtBeforeEvent) {
    if (ev.damageSource.cause !== "entityAttack") return;
    if (drift() === 2) ev.damage += 1;
    if (overflow(s)) {
      const e = ev.hurtEntity;
      system.run(() => {
        if (p.isValid && alive(e)) misclassify(p, e, 80);
      });
    }
  },
  onItemComplete() {
    /* nothing special */
  },
};

/** For tests and the Codex: the drift names, in phase order. */
export function driftName(): string {
  return DRIFTS[drift()];
}
