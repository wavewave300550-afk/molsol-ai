/**
 * Race 006 - Nurariten (นูราริเทน), the Uninvited Sovereign.  UNIQUE lineage.
 *
 * Built on the yokai Nurarihyon - the elder who walks into a house at its busiest hour,
 * sits down, drinks the tea and is taken for the master - and turned into a celestial
 * aristocrat: it does not ask, it arrives.  Its system is Divine Jurisdiction:
 *
 *   Sovereign Presence   passive authority (Royal Presence, Master of the House, Celestial Bearing)
 *   Celestial Edicts     abilities that judge: creatures gain 1-3 golden judgment marks
 *   The Hundred Heavens  the unique ultimate HYAKUTEN CHUKO (百天昼行), a daytime procession of
 *                        heaven that marches through any place it was not invited to
 *
 * Its relationship with the sun is mechanical, not cosmetic: daylight speeds its edicts,
 * midday empowers the Final Edict, dusk is its visiting hour and at night it shines.  It never
 * changes the world's time, sky or weather; the ultimate's golden haze is a per-player fog
 * that is removed afterwards.
 */
import { EntityHurtBeforeEvent, InputPermissionCategory, Player, Vector3, system, world } from "@minecraft/server";
import { ENTITY_GATE, ENTITY_HERALD, ENTITY_PROCESSION } from "../config.js";
import { endChannel, message, refreshForm, startChannel, tempForm } from "../core/abilities.js";
import { effect, hurt, knock, knockFrom } from "../core/combat.js";
import { isOverworld, skyExposed, timeOfDay } from "../core/env.js";
import { particle, pose, privateSound, sound } from "../core/fx.js";
import { EndReason, Session, clearFlag, flag, hasFlag, save } from "../core/session.js";
import { settings } from "../core/settings.js";
import { aimTarget, chest, enemiesNear, eye, groundSpot, lineOfSight, rayPoint } from "../core/targets.js";
import { add, angleBetween, dist, flat, hdist, mul, sub, v3 } from "../core/util.js";
import { consumeMarks, courtOf, courtSecondsLeft, declareCourt, endCourt, exile, inCourtOf, inOwnCourt, judge, judgedBy, marksOn,
  releaseJurisdiction, tickJurisdiction } from "../systems/jurisdiction.js";
import { Proxy, endProxy, proxiesOf, removeProxiesOf, spawnProxy } from "../systems/proxies.js";
import { AbilityDef, RaceDef } from "./types.js";

// ------------------------------------------------------------------ the sun

type Phase = "midday" | "day" | "dusk" | "night" | "sunless";

/** Where the sun stands for this player (the Nether and the End have none). */
export function phase(p: Player): Phase {
  if (!isOverworld(p)) return "sunless";
  const t = timeOfDay();
  if (t >= 4500 && t < 7500) return "midday";
  if (t >= 11500 && t < 13500) return "dusk";
  if (t < 11500 || t >= 23000) return "day";
  return "night";
}

const PHASE_HUD: Record<Phase, string> = {
  midday: "§eMidday Mandate",
  day: "§6Solar Mandate",
  dusk: "§cHour of Visiting",
  night: "§9Nocturne",
  sunless: "§8Sunless Realm",
};

const online = (id: string): Player | undefined => world.getPlayers().find((x) => x.id === id);

function yawOf(d: Vector3): number {
  return (Math.atan2(-d.x, d.z) * 180) / Math.PI;
}

/** Halve what is left of an ability's cooldown (an interrupted preparation). */
function refundHalf(s: Session, id: string): void {
  const now = system.currentTick;
  const at = s.readyAt.get(id);
  if (at !== undefined && at > now) s.readyAt.set(id, now + Math.round((at - now) * 0.5));
  s.dirty = true;
}

function lockStep(p: Player, s: Session, locked: boolean): void {
  const c = InputPermissionCategory.LateralMovement;
  try {
    p.inputPermissions.setPermissionCategory(c, !locked);
  } catch {
    /* permissions unavailable */
  }
  if (locked && !s.data.locks.includes(c)) s.data.locks.push(c);
  if (!locked) s.data.locks = s.data.locks.filter((x) => x !== c);
  s.dirty = true;
  save(p, s, true);
}

/** A spot the Sovereign can stand on: solid floor, two open blocks, no fire, lava or cactus. */
function safeSpot(p: Player, target: Vector3): Vector3 | undefined {
  const dim = p.dimension;
  const from = p.location;
  const d = sub(target, from);
  const bad = /(lava|fire|powder_snow|cactus|magma|sweet_berry|wither_rose|campfire|pointed_dripstone|cobweb)/;
  for (let k = 0; k < 7; k++) {
    const probe = add(from, mul(d, 1 - k * 0.12));
    const g = groundSpot(dim, probe, 6, 2, 1);
    if (!g) continue;
    try {
      const feet = dim.getBlock(g);
      const below = dim.getBlock({ x: g.x, y: g.y - 1, z: g.z });
      if ((feet && bad.test(feet.typeId)) || (below && bad.test(below.typeId))) continue;
    } catch {
      continue;
    }
    if (!lineOfSight(dim, eye(p), add(g, v3(0, 1.2, 0)))) continue;
    return g;
  }
  return undefined;
}

// ------------------------------------------------------------------ 1. Unannounced Arrival

const arrival: AbilityDef = {
  id: "unannounced_arrival",
  name: "Unannounced Arrival",
  short: "Arrival",
  cooldown: 18,
  range: 12,
  original: "Cooldown 18 s; appears without warning at a nearby location; safe teleport (no walls, no unsafe blocks) and a push on arrival.",
  desc: "You are simply there: step up to 12 blocks along your gaze to a safe spot you can see (never through walls, never onto lava, fire or into the void). A gate of light marks where you left and where you arrive; creatures within 3.5 blocks of your arrival are pushed aside and slowed. Arriving under a roof that is not yours, you are received as its master (Absorption, 8 s). At dusk - the hour of visiting - you hold 2 charges.",
  maxCharges({ p }) {
    return phase(p) === "dusk" ? 2 : 1;
  },
  cast({ p, s }) {
    const spot = safeSpot(p, rayPoint(p, 12));
    if (!spot) return "No place there will receive you";
    if (hdist(spot, p.location) < 2.2) return "Too close to be an arrival";
    const from = { ...p.location };
    const rot = p.getRotation();
    let ok = false;
    try {
      ok = p.tryTeleport(spot, { checkForBlocks: true, keepVelocity: false, rotation: rot });
    } catch {
      ok = false;
    }
    if (!ok) return "The way is barred";
    particle(p.dimension, "plrace:arrival_gate", add(from, v3(0, 1.2, 0)));
    particle(p.dimension, "plrace:dissolve_light", add(from, v3(0, 0.6, 0)));
    sound(p.dimension, "mob.shulker.teleport", from, 0.8, 0.7);
    system.run(() => {
      if (!p.isValid) return;
      particle(p.dimension, "plrace:arrival_gate", add(p.location, v3(0, 1.2, 0)));
      particle(p.dimension, "plrace:royal_mote", add(p.location, v3(0, 1.0, 0)));
      sound(p.dimension, "block.bell.hit", p.location, 0.5, 1.6);
      for (const e of enemiesNear(p, p.location, 3.5)) {
        knockFrom(e, p.location, 1.3, 0.3);
        effect(e, "slowness", 30, 1);
      }
      if (!skyExposed(p)) {
        effect(p, "absorption", 160, 0, false);
        message(s, "§6You are received as the master of this house", 40);
      }
      pose(p, "nur_arrival");
    });
    return true;
  },
};

// ------------------------------------------------------------------ 2. Edict of the Lowered Gaze

const gaze: AbilityDef = {
  id: "lowered_gaze",
  name: "Edict of the Lowered Gaze",
  short: "Lowered Gaze",
  cooldown: 25,
  range: 9,
  cone: 70,
  original: "Cooldown 25 s; forward decree that makes enemies lower their eyes: stagger and weaken; no prolonged forced camera control and no excessive flashing.",
  desc: "Two fingers leave the sleeve and the edict is spoken: every enemy in a 70 degree cone within 9 blocks bows its head - it is staggered back, Weakened (II, 5 s; 7 s at midday), Slowed (II, 2.5 s) and receives one judgment mark. Creatures are made to look at the ground for a moment; players are never camera-locked (they only feel the weight).",
  cast({ p, s }) {
    const from = eye(p);
    const view = p.getViewDirection();
    const hits = enemiesNear(p, p.location, 9.5).filter((e) => angleBetween(view, sub(chest(e), from)) <= 38 && lineOfSight(p.dimension, from, chest(e)));
    if (!hits.length) return "No one stands before you to bow";
    const noon = phase(p) === "midday";
    tempForm(p, s, "edict", 26);
    pose(p, "nur_edict");
    particle(p.dimension, "plrace:decree_burst", add(from, add(mul(flat(view), 0.9), v3(0, -0.35, 0))));
    sound(p.dimension, "block.bell.hit", p.location, 0.8, 1.35);
    for (const e of hits) {
      knockFrom(e, p.location, 0.45, 0.1);
      effect(e, "weakness", noon ? 140 : 100, 1);
      effect(e, "slowness", 50, 1);
      judge(e, p, 1);
      if (e.typeId !== "minecraft:player") {
        try {
          e.setRotation({ x: 55, y: e.getRotation().y }); // the head bows (the AI looks up again on its own)
        } catch {
          /* ignore */
        }
      }
      particle(e.dimension, "plrace:decree_burst", add(e.location, v3(0, 1.7, 0)));
    }
    message(s, `§6${hits.length} lower${hits.length === 1 ? "s its" : " their"} gaze`, 30);
    return true;
  },
};

// ------------------------------------------------------------------ 3. The Uninvited Temple

const TEMPLE_WINDUP = 20;
const TEMPLE_RADIUS = 7;

const temple: AbilityDef = {
  id: "uninvited_temple",
  name: "The Uninvited Temple",
  short: "Temple",
  cooldown: 35,
  original: "Cooldown 35 s; declares a temporary celestial court; enemies inside slowed and marked; no land seizure, no griefing, no permanent blocks.",
  desc: "The architecture on your back unfolds and you declare the ground your court: a 7-block circle of pillars of light with a gate at its edge, for 10 s (13 s at dusk). Enemies inside are slowed and gain a judgment mark every 3 s; you inside it deal 20% more damage, take 15% less and recover cooldowns 20% faster. The 1 s declaration is interrupted by a heavy blow (4+ damage, or 6 in total: half the cooldown is refunded). The court changes no blocks - and if you leave it, the mandate breaks (Weakness, 4 s).",
  check({ p }) {
    return p.isOnGround || p.isInWater ? undefined : "You must stand on the ground to hold court";
  },
  cast({ p, s }) {
    tempForm(p, s, "court", TEMPLE_WINDUP + 10);
    pose(p, "nur_claim");
    s.num.set("prep_dmg", 0);
    sound(p.dimension, "beacon.activate", p.location, 0.7, 0.8);
    particle(p.dimension, "plrace:heaven_ring", add(p.location, v3(0, 0.1, 0)));
    startChannel(p, s, {
      ability: "uninvited_temple",
      mode: "block",
      until: system.currentTick + TEMPLE_WINDUP,
      tick: (_s2, p2, t) => {
        if (t % 5 === 0) particle(p2.dimension, "plrace:court_pillar", add(p2.location, v3(Math.cos(t) * 1.2, 0.1, Math.sin(t) * 1.2)));
      },
      end: (s2, p2, reason) => {
        if (reason === "complete" && p2.isValid) {
          openCourt(p2, s2);
          return;
        }
        if (reason === "interrupt") {
          refundHalf(s2, "uninvited_temple");
          if (p2.isValid) {
            s2.tempVariant = undefined;
            refreshForm(p2, s2);
            message(s2, "§cThe declaration was interrupted §7(Judicial Weakness)", 50);
            sound(p2.dimension, "random.break", p2.location, 0.6, 1.4);
          }
        }
      },
    });
    return true;
  },
};

function openCourt(p: Player, s: Session): void {
  const ticks = 200 + (phase(p) === "dusk" ? 60 : 0);
  const dim = p.dimension;
  const center = { ...p.location };
  declareCourt(p, "temple", center, TEMPLE_RADIUS, ticks, (court, reason) => {
    removeProxiesOf(s.id, "temple_gate");
    particle(dim, "plrace:dissolve_light", add(court.center, v3(0, 0.6, 0)));
    const pl = online(s.id);
    if (!pl) return;
    if (reason === "broken") {
      effect(pl, "weakness", 80, 0);
      flag(s, "broken", 80);
      message(s, "§cBroken Mandate: you left your own court", 60);
      privateSound(pl, "random.break", 0.7, 0.7);
    } else if (reason === "expired") message(s, "§7The court is dismissed", 40);
    refreshForm(pl, s);
  });
  // the gate stands at the edge behind the master, facing into the court
  const fwd = flat(p.getViewDirection());
  const at = add(center, mul(fwd, -(TEMPLE_RADIUS - 0.6)));
  const g = groundSpot(dim, add(at, v3(0, 2, 0)), 6, 1, 0) ?? at;
  spawnProxy(p, ENTITY_GATE, g, { kind: "temple_gate", ticks: ticks + 10, yaw: yawOf(fwd) });
  particle(dim, "plrace:heaven_ring", add(center, v3(0, 0.1, 0)));
  particle(dim, "plrace:court_ring", add(center, v3(0, 0.08, 0)), { size: TEMPLE_RADIUS * 2 });
  sound(dim, "block.bell.hit", center, 1, 0.75);
  for (const e of enemiesNear(p, center, TEMPLE_RADIUS)) judge(e, p, 1);
  s.tempVariant = undefined;
  refreshForm(p, s);
  message(s, "§6This ground is your court", 40);
}

// ------------------------------------------------------------------ 4. Imperial Expulsion

const expulsion: AbilityDef = {
  id: "imperial_expulsion",
  name: "Imperial Expulsion",
  short: "Expulsion",
  cooldown: 40,
  range: 12,
  cone: 20,
  needsTarget: true,
  original: "Cooldown 40 s; casts a target out of the Sovereign's presence; synergy with the Uninvited Temple and judgment marks.",
  desc: "Point at one creature within 12 blocks and it is thrown out of your presence: 5 damage +3 per judgment mark (marks are consumed), knocked far away (farther per mark) and Slowed. Expelled from inside your court it takes +3 damage and is barred from re-entering for 6 s - it is turned back at the threshold. Aim assist prefers judged creatures.",
  cast({ p, s }) {
    const t = aimTarget(p, 12, 20, (e) => marksOn(e, p.id) > 0);
    if (!t) return "No one here to expel";
    const marks = consumeMarks(t, p.id);
    const court = inCourtOf(p.id, t);
    hurt(t, 5 + 3 * marks + (court ? 3 : 0), p);
    knockFrom(t, p.location, 2.2 + 0.6 * marks, 0.45 + 0.08 * marks);
    effect(t, "slowness", 50, 1);
    if (court) exile(court, t, 120);
    tempForm(p, s, "edict", 18);
    pose(p, "nur_point");
    particle(t.dimension, "plrace:arrival_gate", chest(t));
    particle(t.dimension, "plrace:decree_burst", chest(t));
    sound(p.dimension, "block.bell.hit", t.location, 0.9, 0.55);
    sound(p.dimension, "mob.shulker.shoot", t.location, 0.6, 0.6);
    message(s, `§6Expelled${marks ? ` §7(${marks} mark${marks > 1 ? "s" : ""})` : ""}${court ? " §7- barred from your court" : ""}`, 40);
    return true;
  },
};

// ------------------------------------------------------------------ 5. HYAKUTEN CHUKO (百天昼行) - unique ultimate

/** Stage boundaries (ticks from the cast). */
const H = { proclaim: 40, march: 70, throne: 130, edict: 160, strike: 172, dissolve: 182, end: 200 };
const HEAVEN_RADIUS = 11;
const FOG_ID = "plrace:heaven_light";
const FOG_USER = "plrace_hh";

const STAGE_NAMES = ["I The Sky Must Open", "II The Proclamation", "III The Hundred Heavens March", "IV The Throne Without Permission", "V The Final Edict"];

interface Heaven {
  center: Vector3;
  fwd: Vector3;
  gate: Vector3; // the gate's centre point (heralds come out of it)
  sky: boolean;
  fogged: Set<string>;
  trampled: Map<string, number>;
  stage: number;
}
const heavens = new Map<string, Heaven>();

function stageOf(t: number): number {
  return t < H.proclaim ? 0 : t < H.march ? 1 : t < H.throne ? 2 : t < H.edict ? 3 : 4;
}

/** A golden haze only for the witnesses (never the sky, time or weather of the world). */
function pushFog(h: Heaven, pl: Player): void {
  if (h.fogged.has(pl.id) || !settings().heavenFx) return;
  try {
    pl.runCommand(`fog @s push ${FOG_ID} ${FOG_USER}`);
    h.fogged.add(pl.id);
  } catch {
    /* ignore */
  }
}

/** Remove the haze from a player (also used on join / reload as a safety net). */
export function clearHeavenFog(pl: Player): void {
  try {
    pl.runCommand(`fog @s remove ${FOG_USER}`);
  } catch {
    /* nothing to remove */
  }
}

function popFogs(h: Heaven): void {
  for (const id of h.fogged) {
    const pl = online(id);
    if (pl) clearHeavenFog(pl);
  }
  h.fogged.clear();
}

/** End everything the ultimate created (any reason, idempotent). */
function dissolveHeaven(ownerId: string): void {
  const h = heavens.get(ownerId);
  for (const px of proxiesOf(ownerId, "heaven")) endProxy(px, "owner");
  endCourt(ownerId, "heaven", "owner");
  if (h) popFogs(h);
  heavens.delete(ownerId);
}

const hyakuten: AbilityDef = {
  id: "hyakuten_chuko",
  name: "HYAKUTEN CHŪKŌ",
  short: "百天昼行",
  cooldown: 180,
  ultimate: true,
  original: "Unique ultimate, cooldown 180 s, five stages: The Sky Must Open; The Proclamation; The Hundred Heavens March; The Throne Without Permission; The Final Edict. Real combat consequences, full restoration; no hundred AI mobs (shared geometry); day/night relationship without changing world time or sky.",
  desc: "The Hundred Heavens' daytime procession (a heavenly answer to the Night Parade of a Hundred Demons) marches through a place no one invited it to. 10 s, you stand still:\n I The Sky Must Open (2 s): a vast gate opens in the sky ahead - a heavy blow (5+ damage, or 8 in total) now interrupts you (half the cooldown back).\n II The Proclamation: two heralds descend with the decree; every enemy within 16 blocks is judged (+1 mark) and slowed.\n III The Hundred Heavens March: eight columns of attendants - 96 figures, two heralds, the gate and you make one hundred - circle and close in, trampling (2 damage) and herding enemies toward you.\n IV The Throne Without Permission: your court becomes a throne-palace: you gain Resistance and Regeneration; enemies within 12 are Weakened, slowed and judged.\n V The Final Edict: one finger rises and the seals converge: every enemy within 14 takes 4 +4 per mark (max 16; +25% at midday) and is thrown down.\nEverything then dissolves and the world is left exactly as it was. Under a roof the gate enters through the door instead of the sky; at night the procession brings a private daylight haze to those who witness it.",
  check({ p }) {
    if (heavens.has(p.id)) return "The Hundred Heavens are already marching";
    return p.isOnGround || p.isInWater ? undefined : "You must stand on the ground";
  },
  cast({ p, s }) {
    const center = { ...p.location };
    const fwd = flat(p.getViewDirection());
    const sky = skyExposed(p);
    const dim = p.dimension;
    let gateBase: Vector3;
    let gate: Vector3;
    if (sky) {
      gateBase = add(center, add(mul(fwd, 9), v3(0, 2.5, 0)));
      gate = add(gateBase, v3(0, 5.4, 0));
    } else {
      const at = add(center, mul(fwd, 4));
      gateBase = groundSpot(dim, add(at, v3(0, 1, 0)), 4, 1, 0) ?? at;
      gate = add(gateBase, v3(0, 1.5, 0));
    }
    const h: Heaven = { center, fwd, gate, sky, fogged: new Set(), trampled: new Map(), stage: 0 };
    dissolveHeaven(p.id);
    heavens.set(p.id, h);
    lockStep(p, s, true);
    s.num.set("prep_dmg", 0);
    flag(s, "heaven", H.end + 20);
    tempForm(p, s, "edict", H.throne);
    pose(p, "nur_claim");
    spawnProxy(p, ENTITY_GATE, gateBase, {
      kind: "heaven",
      ticks: H.end + 10,
      yaw: yawOf(mul(fwd, -1)),
      event: sky ? "plrace:huge" : undefined,
      data: { role: "gate" },
      tick: (px, age) => {
        if (age < H.proclaim && age % 6 === 0) particle(px.entity.dimension, "plrace:sky_fracture", gate);
        if (age % 20 === 0 && age < H.dissolve) particle(px.entity.dimension, "plrace:gate_shadow", v3(gateBase.x, center.y + 0.06, gateBase.z));
      },
      end: () => particle(dim, "plrace:dissolve_light", gate),
    });
    declareCourt(p, "heaven", center, HEAVEN_RADIUS, H.end);
    try {
      p.onScreenDisplay.setTitle("§6百天昼行", { subtitle: "§eHYAKUTEN CHŪKŌ §7- the sky must open", fadeInDuration: 8, stayDuration: 50, fadeOutDuration: 20 });
    } catch {
      /* ignore */
    }
    for (const pl of dim.getPlayers({ location: center, maxDistance: 40 })) {
      pushFog(h, pl);
      if (settings().heavenFx && dist(pl.location, center) <= 18) {
        try {
          pl.camera.fade({ fadeTime: { fadeInTime: 0.35, holdTime: 0.1, fadeOutTime: 1.1 }, fadeColor: { red: 1, green: 0.93, blue: 0.72 } });
        } catch {
          /* ignore */
        }
      }
      if (pl.id !== p.id) {
        try {
          pl.onScreenDisplay.setActionBar(`§6The sky opens above ${p.name}...`);
        } catch {
          /* ignore */
        }
      }
    }
    particle(dim, "plrace:heaven_ring", add(center, v3(0, 0.1, 0)));
    sound(dim, "block.bell.hit", center, 1.4, 0.5);
    sound(dim, "beacon.activate", center, 1, 0.6);
    startChannel(p, s, {
      ability: "hyakuten_chuko",
      mode: "block",
      cancelable: true,
      until: system.currentTick + H.end,
      tick: (s2, p2, t) => heavenTick(p2, s2, h, t),
      end: (s2, p2, reason) => heavenEnd(p2, s2, h, reason),
    });
    return true;
  },
};

function heavenTick(p: Player, s: Session, h: Heaven, t: number): void {
  const dim = p.dimension;
  const st = stageOf(t);
  if (st !== h.stage) {
    h.stage = st;
    message(s, `§6${STAGE_NAMES[st]}`, 50);
  }
  // late witnesses also see the haze
  if (t % 20 === 10) for (const pl of dim.getPlayers({ location: h.center, maxDistance: 32 })) pushFog(h, pl);

  // ---- I: the sky must open (interruptible preparation)
  if (t === 10) sound(dim, "beacon.power", h.center, 0.9, 0.7);
  if (t === 20) {
    sound(dim, "block.bell.hit", h.center, 1.4, 0.6);
    particle(dim, "plrace:heaven_ring", add(h.center, v3(0, 0.1, 0)));
  }
  if (t === 36) sound(dim, "random.levelup", h.center, 0.7, 0.5);

  // ---- II: the proclamation
  if (t === H.proclaim) {
    const dest = add(h.center, add(mul(h.fwd, 2.6), v3(0, 1.4, 0)));
    const start = { ...h.gate };
    spawnProxy(p, ENTITY_HERALD, start, {
      kind: "heaven",
      ticks: H.end - H.proclaim + 6,
      yaw: yawOf(h.fwd),
      data: { role: "herald" },
      tick: (px, age) => {
        if (age > 26) return;
        const k = Math.min(1, age / 24);
        const e = 1 - (1 - k) * (1 - k);
        const pos = add(start, mul(sub(dest, start), e));
        try {
          px.entity.teleport(pos, { facingLocation: add(pos, mul(h.fwd, 6)) });
        } catch {
          /* ignore */
        }
      },
      end: (px) => particle(dim, "plrace:dissolve_light", px.entity.isValid ? px.entity.location : dest),
    });
    sound(dim, "block.bell.hit", h.center, 1.2, 0.8);
  }
  if (t === H.proclaim + 12) {
    const judged = enemiesNear(p, h.center, 16);
    for (const e of judged) {
      judge(e, p, 1);
      effect(e, "slowness", 40, 1);
      particle(e.dimension, "plrace:decree_burst", add(e.location, v3(0, 1.8, 0)));
    }
    particle(dim, "plrace:decree_burst", add(h.center, add(mul(h.fwd, 2.6), v3(0, 2.2, 0))));
    sound(dim, "random.orb", h.center, 1, 0.5);
    message(s, `§6By decree of the Hundred Heavens: §f${judged.length}§6 stand judged`, 50);
  }

  // ---- III: the hundred heavens march
  if (t === H.march) {
    const base = yawOf(h.fwd);
    for (let k = 0; k < 8; k++) spawnColumn(p, h, k, base + k * 45);
    sound(dim, "block.bell.hit", h.center, 1.2, 1.0);
  }
  if (t >= H.march && t < H.throne) {
    if (t % 10 === 0) sound(dim, "note.bd", h.center, 1.2, 0.6);
    if (t % 20 === 5) sound(dim, "note.bell", h.center, 0.8, 0.5);
  }

  // ---- IV: the throne without permission
  if (t === H.throne) {
    tempForm(p, s, "throne", H.end - H.throne + 4);
    pose(p, "nur_enthrone", "!q.is_item_name_any('slot.armor.head', 0, 'plrace:form_nurariten_throne')");
    effect(p, "resistance", 70, 1, false);
    effect(p, "regeneration", 60, 0, false);
    for (const e of enemiesNear(p, h.center, 12)) {
      judge(e, p, 1);
      effect(e, "weakness", 80, 0);
      effect(e, "slowness", 40, 2);
    }
    for (const px of proxiesOf(p.id, "heaven")) if (px.data.role === "column") px.data.halt = true;
    particle(dim, "plrace:heaven_ring", add(h.center, v3(0, 0.1, 0)));
    sound(dim, "beacon.power", h.center, 1.2, 0.5);
    message(s, "§6IV The Throne Without Permission §7- the house is yours", 50);
  }

  // ---- V: the final edict
  if (t === H.edict) {
    pose(p, "nur_final");
    const finger = add(eye(p), v3(0, 1.1, 0));
    for (const e of enemiesNear(p, h.center, 14)) {
      const d = sub(chest(e), finger);
      particle(dim, "plrace:seal_converge", finger, { dx: d.x, dy: d.y, dz: d.z });
    }
    sound(dim, "block.bell.hit", h.center, 1.4, 0.45);
  }
  if (t === H.strike) {
    const noon = phase(p) === "midday";
    let n = 0;
    for (const e of enemiesNear(p, h.center, 14)) {
      const marks = consumeMarks(e, p.id);
      const dmg = Math.min(16, 4 + 4 * marks) * (noon ? 1.25 : 1);
      hurt(e, dmg, p);
      knockFrom(e, h.center, 0.7, 0.55);
      particle(e.dimension, "plrace:judgment_seal", add(e.location, v3(0, 1.2, 0)), { stacks: 3 });
      particle(e.dimension, "plrace:decree_burst", chest(e));
      n++;
    }
    particle(dim, "plrace:heaven_ring", add(h.center, v3(0, 0.15, 0)));
    particle(dim, "plrace:dissolve_light", add(h.center, v3(0, 1, 0)));
    sound(dim, "random.explode", h.center, 0.6, 1.5);
    sound(dim, "block.bell.hit", h.center, 1.6, 0.4);
    message(s, `§6V The Final Edict §7- ${n} judged${noon ? " §e(midday)" : ""}`, 60);
  }
  if (t === H.dissolve) {
    for (const px of proxiesOf(p.id, "heaven")) if (px.data.role !== "gate") endProxy(px, "expired");
  }
  if (t === H.end - 6) popFogs(h);
}

function spawnColumn(p: Player, h: Heaven, k: number, angle0: number): void {
  const dim = p.dimension;
  const R0 = 12;
  const at = (ang: number, r: number): Vector3 => {
    const a = (ang * Math.PI) / 180;
    return add(h.center, v3(-Math.sin(a) * r, 0, Math.cos(a) * r));
  };
  const first = at(angle0, R0);
  const g = groundSpot(dim, add(first, v3(0, 3, 0)), 8, 1, 0);
  spawnProxy(p, ENTITY_PROCESSION, g ?? first, {
    kind: "heaven",
    ticks: H.end - H.march + 6,
    data: { role: "column", halt: false, y: (g ?? first).y, ang: angle0 },
    tick: (px, age) => columnTick(p, h, px, age, k, at),
    end: (px) => {
      if (!px.entity.isValid) return;
      particle(dim, "plrace:dissolve_light", add(px.entity.location, v3(0, 0.8, 0)));
      particle(dim, "plrace:procession_shadow", px.entity.location);
    },
  });
  particle(dim, "plrace:arrival_gate", add(g ?? first, v3(0, 1.2, 0)));
}

function columnTick(p: Player, h: Heaven, px: Proxy, age: number, k: number, at: (ang: number, r: number) => Vector3): void {
  if (!p.isValid) return;
  const d = px.data as { halt: boolean; y: number; ang: number };
  const e = px.entity;
  const dim = e.dimension;
  if (d.halt) {
    if (age % 10 === 0) {
      try {
        e.teleport(e.location, { facingLocation: v3(h.center.x, e.location.y, h.center.z) });
      } catch {
        /* ignore */
      }
    }
    return;
  }
  const frac = Math.min(1, age / (H.throne - H.march));
  d.ang += 1.6;
  const r = 12 - 5 * frac;
  const pos = at(d.ang, r);
  if (age % 4 === k % 4) {
    const g = groundSpot(dim, v3(pos.x, d.y + 2, pos.z), 5, 1, 0);
    if (g) d.y = g.y;
  }
  const here = v3(pos.x, d.y, pos.z);
  const ahead = at(d.ang + 8, r);
  try {
    e.teleport(here, { facingLocation: v3(ahead.x, d.y, ahead.z) });
  } catch {
    return;
  }
  if (age % 20 === k % 20) particle(dim, "plrace:procession_shadow", add(here, v3(0, 0.05, 0)));
  if (age % 4 !== k % 4) return;
  const now = system.currentTick;
  for (const victim of enemiesNear(p, here, 2.2)) {
    if ((h.trampled.get(victim.id) ?? 0) > now) continue;
    h.trampled.set(victim.id, now + 12);
    hurt(victim, 2, p);
    knock(victim, mul(flat(sub(h.center, victim.location)), 0.55), 0.18);
    effect(victim, "slowness", 20, 0);
  }
}

function heavenEnd(p: Player, s: Session, h: Heaven, reason: EndReason): void {
  const early = h.stage === 0 && (reason === "interrupt" || reason === "cancel");
  dissolveHeaven(s.id);
  clearFlag(s, "heaven");
  if (p.isValid) {
    lockStep(p, s, false);
    s.tempVariant = undefined;
    refreshForm(p, s);
  }
  if (early) {
    refundHalf(s, "hyakuten_chuko");
    flag(s, "broken", 100);
    if (p.isValid) {
      effect(p, "weakness", 100, 0);
      sound(p.dimension, "random.break", p.location, 0.8, 0.6);
    }
    message(s, reason === "interrupt" ? "§cThe sky closed: the procession was interrupted §7(Broken Mandate - half the cooldown returned)"
      : "§7You withdraw the procession §8(half the cooldown returned)", 70);
  } else if (reason === "complete") message(s, "§6The Hundred Heavens withdraw. The house is as it was.", 60);
  else if (reason === "cancel") message(s, "§7You withdraw the procession", 50);
}

// ------------------------------------------------------------------ race

const presence = new Map<string, number>(); // creature id -> tick when Royal Presence may touch it again

export const nurariten: RaceDef = {
  code: "006",
  key: "nurariten",
  name: "Nurariten",
  thai: "นูราริเทน",
  title: "The Uninvited Sovereign",
  color: "§6",
  rarity: "unique",
  tagline: "It was never invited. It was always expected.",
  lore: [
    "Folklore tells of Nurarihyon, the gourd-headed elder who slips into a house at its busiest hour, sits in the best seat, drinks the tea and is taken for the master - and is gone before anyone thinks to ask who he was.",
    "Nurariten is what that story becomes in heaven: a sovereign of the celestial courts with an ivory mask of a face, narrow golden eyes, a halo broken into drifting fragments and a gate folded on its back. It does not knock. It does not ask. When it wishes, the sky opens and the Hundred Heavens march - by day, through any place that never invited them.",
  ],
  strengths: ["Area authority: courts, judgment marks and a five-stage ultimate", "Safe repositioning (Unannounced Arrival)", "Strongest in daylight; cooldowns run faster in the sun and in its court", "Turns marks into heavy single-target and area damage"],
  weaknesses: ["Judicial Weakness: preparations can be interrupted by heavy blows", "Arrogant Posture: +15% damage from behind; it never dodges like a jackalope or endures like a golem", "Broken Mandate: leaving its own court breaks it (Weakness)", "Its ultimate roots it in place for 10 s", "Unique: only one may hold it in a world"],
  passives: [
    { name: "Royal Presence", desc: "Hostile creatures that come within 5 blocks (6 at midday, 4 at night) falter for a moment (Slowness I, 1.5 s, at most once per creature every 8 s). Subtle on purpose: never a lasting control effect, never on players." },
    { name: "Celestial Bearing", desc: "It descends with composure (fall damage -40%) and is never dizzied (Nausea is removed)." },
    { name: "Uninvited Authority", desc: "Inside its own court: +20% damage dealt, -15% damage taken, cooldowns 20% faster. Indoors near villagers it is received as the master of the house (Hero of the Village I)." },
    { name: "Solar Mandate", desc: "Daylight: cooldowns 15% faster. Midday: Lowered Gaze lasts longer and the Final Edict deals +25%. Dusk, the hour of visiting: Unannounced Arrival holds 2 charges and the Temple stands 3 s longer. Night: the Nocturne Radiance form - its presence reaches less far. The world's time is never changed." },
    { name: "Divine Jurisdiction", desc: "Judgment marks (1-3, a golden seal above the creature, 12 s) come from edicts, courts and the procession, and are consumed by Imperial Expulsion and the Final Edict." },
  ],
  abilities: [arrival, gaze, temple, expulsion, hyakuten],
  focusItem: "plrace:focus_nurariten",
  focusName: "Mandate Shaku Focus",
  controls: [
    "Nurariten: §fHYAKUTEN CHŪKŌ§7 is the fifth ability - cycle to it like the others. You stand still for its 10 s; use it again in the first 2 s to withdraw it (half the cooldown returns).",
    "Nurariten: stay inside your own court - leaving it breaks the mandate.",
  ],
  variant(p, s) {
    if (courtOf(s.id, "temple") && inOwnCourt(p, "temple")) return "court";
    if (phase(p) === "night") return "nocturne";
    return "";
  },
  cooldownMul(p, s) {
    const ph = phase(p);
    let m = ph === "day" || ph === "midday" ? 0.85 : 1;
    if (inOwnCourt(p, "temple")) m *= 0.8; // the Temple's authority (the ultimate's court never shortens its own cooldown)
    if (hasFlag(s, "broken")) m *= 1.15;
    return m;
  },
  init(p, _s, first) {
    clearHeavenFog(p);
    if (first) {
      try {
        world.sendMessage(`§6✦ The Uninvited Sovereign has arrived: §f${p.name}§6 is now Nurariten. ✦`);
      } catch {
        /* ignore */
      }
    }
  },
  cleanup(p, s) {
    if (s.data.locks.includes(InputPermissionCategory.LateralMovement) && !s.channel) lockStep(p, s, false);
  },
  release(s) {
    dissolveHeaven(s.id);
    releaseJurisdiction(s.id);
    clearFlag(s, "heaven");
  },
  tick20(p, s) {
    const ph = phase(p);
    const radius = ph === "midday" ? 6 : ph === "night" ? 4 : 5;
    const now = system.currentTick;
    for (const e of enemiesNear(p, p.location, radius)) {
      if (e.typeId === "minecraft:player") continue;
      if ((presence.get(e.id) ?? 0) > now) continue;
      presence.set(e.id, now + 160);
      effect(e, "slowness", 30, 0, false);
      particle(e.dimension, "plrace:royal_mote", add(e.location, v3(0, 0.3, 0)));
    }
    if (presence.size > 256) for (const [id, at] of presence) if (at <= now) presence.delete(id);
    try {
      if (p.getEffect("nausea")) p.removeEffect("nausea");
    } catch {
      /* ignore */
    }
    // Master of the House: indoors, with the household around it
    if (!skyExposed(p)) {
      let household = 0;
      try {
        household = p.dimension.getEntities({ families: ["villager"], location: p.location, maxDistance: 8 }).length;
      } catch {
        household = 0;
      }
      if (household) effect(p, "village_hero", 100, 0, false);
    }
  },
  tick5(p, s) {
    if (!s.tempVariant && !s.data.veiled && nurariten.variant(p, s) !== s.shownVariant) refreshForm(p, s);
  },
  hud(p, s) {
    const parts = [PHASE_HUD[phase(p)]];
    const c = courtOf(s.id, "temple");
    if (c) parts.push(`§6Court §f${Math.ceil(courtSecondsLeft(c))}s${inOwnCourt(p) ? "" : " §c(outside!)"}`);
    const h = heavens.get(s.id);
    if (h) parts.push(`§e百天昼行 ${["I", "II", "III", "IV", "V"][h.stage]}`);
    const judged = judgedBy(s.id).length;
    if (judged) parts.push(`§6Judged §f${judged}`);
    if (hasFlag(s, "broken")) parts.push("§cBroken Mandate");
    return parts.join(" §8| ");
  },
  onHurt(p, s, ev: EntityHurtBeforeEvent) {
    const cause = ev.damageSource.cause as string;
    if (cause === "fall") ev.damage *= 0.6;
    const src = ev.damageSource.damagingEntity ?? ev.damageSource.damagingProjectile;
    if (src && src.isValid) {
      const to = sub(src.location, p.location);
      if (angleBetween(flat(p.getViewDirection()), v3(to.x, 0, to.z)) > 110) ev.damage *= 1.15; // Arrogant Posture
    }
    if (inOwnCourt(p)) ev.damage *= 0.85;
    if (s.channel?.ability === "hyakuten_chuko" && hasFlag(s, "heaven") && (heavens.get(s.id)?.stage ?? 0) >= 3) ev.damage *= 0.9;
  },
  onDealDamage(p, _s, ev: EntityHurtBeforeEvent) {
    if (inOwnCourt(p)) ev.damage *= 1.2;
  },
  afterHurt(p, s, _cause, amount) {
    const ch = s.channel;
    if (!ch) return;
    // Judicial Weakness: one heavy blow, or enough small ones, interrupts a preparation
    const temple = ch.ability === "uninvited_temple";
    const sky = ch.ability === "hyakuten_chuko" && (heavens.get(s.id)?.stage ?? 0) === 0;
    if (!temple && !sky) return;
    const total = (s.num.get("prep_dmg") ?? 0) + amount;
    s.num.set("prep_dmg", total);
    if (temple ? amount >= 4 || total >= 6 : amount >= 5 || total >= 8) endChannel(p, s, "interrupt");
  },
  worldTick4() {
    tickJurisdiction();
  },
};

