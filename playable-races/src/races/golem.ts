/**
 * Race 002 - Runic Titan Golem (เผ่าไททันรูนโกเลม)
 * Rune Stability (0-100) is the golem's mind holding its stones together.
 * Magic, lightning, thunderstorms, wither and overcasting erode it; below 25% the
 * runes are DISRUPTED (arcane abilities locked, cooldowns slower) until it recovers to 50%.
 */
import { Dimension, EntityHurtBeforeEvent, Player, Vector3, system } from "@minecraft/server";
import { MAGIC_CAUSES, PHYSICAL_CAUSES } from "../config.js";
import { message, refreshForm, startChannel, tempForm } from "../core/abilities.js";
import { effect, hurt, knock, knockFrom } from "../core/combat.js";
import { headInWater, isOverworld, isMoving, skyExposed, weather } from "../core/env.js";
import { particle, pose, privateSound, sound } from "../core/fx.js";
import { pvpAllowed } from "../core/settings.js";
import { Session, clearFlag, flag, hasFlag } from "../core/session.js";
import { enemiesNear, eye, groundSpot, rayPoint } from "../core/targets.js";
import { after, repeat } from "../core/tasks.js";
import { add, angleBetween, clamp, dist, flat, hdist, len, meter, mul, norm, rotY, sub, v3 } from "../core/util.js";
import { AbilityDef, RaceDef } from "./types.js";

const stab = (s: Session) => s.data.res.rune ?? 100;
const disrupted = (s: Session) => s.data.st.gol === "disrupted";

function strain(p: Player, s: Session, amount: number): void {
  setStability(p, s, stab(s) - amount);
}

export function setStability(p: Player, s: Session, v: number): void {
  const val = clamp(v, 0, 100);
  s.data.res.rune = val;
  s.dirty = true;
  const was = disrupted(s);
  if (!was && val < 25) {
    s.data.st.gol = "disrupted";
    refreshForm(p, s);
    message(s, "§cRUNES DISRUPTED - Glyph Dominion and Reassembly unavailable", 70);
    sound(p.dimension, "mob.irongolem.crack", p.location, 1, 0.6);
    particle(p.dimension, "plrace:rune_spark", add(p.location, v3(0, 1.6, 0)));
  } else if (was && val >= 50) {
    s.data.st.gol = "aligned";
    refreshForm(p, s);
    message(s, "§6Runes realigned", 50);
    sound(p.dimension, "beacon.power", p.location, 0.8, 1.4);
    particle(p.dimension, "plrace:rune_pulse", add(p.location, v3(0, 1.6, 0)));
  }
}

/** Golem glyph circles: active zones, used by Glyph Dominion and the "Warded" check. */
interface Zone {
  owner: string;
  dim: Dimension;
  center: Vector3;
  until: number;
  last: Map<string, number>;
  zap: Map<string, number>;
}
const zones: Zone[] = [];
/** Inside an active glyph circle owned by this player (or by anyone when PvP is off). */
export function inWard(p: Player): boolean {
  const now = system.currentTick;
  const friendly = !pvpAllowed();
  return zones.some((z) => z.until > now && (z.owner === p.id || friendly) && z.dim.id === p.dimension.id && hdist(z.center, p.location) <= 6.2);
}

// ------------------------------------------------------------------ abilities

const edict: AbilityDef = {
  id: "titans_edict",
  name: "Titan's Edict",
  short: "Edict",
  cooldown: 18,
  original: "Cooldown 20 s; arms reassemble into a giant hammer, strike the ground, directional shockwave.",
  desc: "Your arm-stones fuse into a colossal hammer (Siege Configuration) and slam the ground. A shockwave rips forward 8 blocks: 9 damage close (falling to 5 at the far end), launches and slows everything in its path. Strains runes (-12).",
  cast({ p, s }) {
    tempForm(p, s, "siege", 30);
    pose(p, "gol_edict");
    strain(p, s, 12);
    sound(p.dimension, "mob.irongolem.repair", p.location, 1, 0.6);
    startChannel(p, s, {
      ability: "titans_edict",
      mode: "block",
      until: system.currentTick + 24,
      tick: (_s, p2, t) => {
        if (t === 12) slam(p2);
      },
      end: () => undefined,
    });
    return true;
  },
};

function slam(p: Player): void {
  const origin = { ...p.location };
  const f = flat(p.getViewDirection());
  const dim = p.dimension;
  const hit = new Set<string>();
  sound(dim, "mace.heavy_smash_ground", origin, 1.2, 0.7);
  sound(dim, "random.explode", origin, 0.6, 0.6);
  particle(dim, "plrace:impact_ring", add(origin, v3(f.x * 1.5, 0.1, f.z * 1.5)));
  for (let k = 0; k < 7; k++) {
    after(1 + k * 2, () => {
      if (!p.isValid) return;
      const c = add(origin, mul(f, 1.6 + k * 1.1));
      const g = groundSpot(dim, add(c, v3(0, 2, 0)), 5, 1, 0) ?? c;
      particle(dim, "plrace:shock_rupture", add(g, v3(0, 0.1, 0)));
      particle(dim, "plrace:shock_glow", add(g, v3(0, 0.05, 0)));
      if (k % 2 === 0) sound(dim, "dig.basalt", g, 1, 0.5 + k * 0.05);
      for (const e of enemiesNear(p, add(g, v3(0, 1, 0)), 2.0, dim)) {
        if (hit.has(e.id) || Math.abs(e.location.y - g.y) > 2.4) continue;
        hit.add(e.id);
        hurt(e, Math.max(5, 9 - k * 0.65), p);
        knock(e, mul(f, 0.9), 0.55);
        effect(e, "slowness", 40, 1);
      }
    }, p.id, "edict");
  }
}

const bastion: AbilityDef = {
  id: "runic_bastion",
  name: "Runic Bastion",
  short: "Bastion",
  cooldown: 28,
  original: "Cooldown 30 s; shoulder/back plates form a frontal wall that reduces incoming damage.",
  desc: "Shoulder and back slabs lock together in front of you for 5 s (Bastion Configuration): attacks from the front (150° arc) deal 70% less and projectiles from the front are stopped outright; other hits deal 30% less; no knockback. You move slower while braced. Cast again to drop the wall.",
  cast({ p, s }) {
    startChannel(p, s, {
      ability: "runic_bastion",
      mode: "interrupt",
      until: system.currentTick + 100,
      tick: () => undefined,
      end: (s2, p2, reason) => {
        if (reason !== "leave" && p2.isValid) {
          refreshForm(p2, s2);
          sound(p2.dimension, "random.anvil_land", p2.location, 0.5, 1.6);
        }
      },
    });
    refreshForm(p, s);
    effect(p, "slowness", 100, 1, false);
    pose(p, "gol_bastion", "!q.is_item_name_any('slot.armor.head', 0, 'plrace:form_golem_bastion')");
    sound(p.dimension, "block.end_portal_frame.fill", p.location, 1, 0.6);
    sound(p.dimension, "random.anvil_use", p.location, 0.6, 0.5);
    strain(p, s, 8);
    return true;
  },
};

const dominion: AbilityDef = {
  id: "glyph_dominion",
  name: "Glyph Dominion",
  short: "Glyph",
  cooldown: 34,
  original: "Cooldown 35 s; inscribed rune circle slows enemies inside and repels those approaching.",
  desc: "Stones lift into an Arcane Configuration and inscribe a 6-block rune circle at your feet for 8 s. Enemies inside are slowed (Slowness III) and burned 1 HP/s; enemies trying to cross the rim from outside are hurled back (2 damage). You and friendly players inside are Warded (15% less damage). Needs aligned runes.",
  check({ s }) {
    return disrupted(s) ? "Runes disrupted - let them realign first" : undefined;
  },
  cast({ p, s }) {
    tempForm(p, s, "arcane", 34);
    pose(p, "gol_glyph");
    strain(p, s, 15);
    const center = { ...p.location };
    const dim = p.dimension;
    sound(dim, "block.enchanting_table.use", center, 1, 0.6);
    after(16, () => {
      const z: Zone = { owner: p.id, dim, center, until: system.currentTick + 160, last: new Map(), zap: new Map() };
      zones.push(z);
      particle(dim, "plrace:glyph_circle", add(center, v3(0, 0.06, 0)), { radius: 6.2, life: 8 });
      sound(dim, "beacon.activate", center, 1, 0.7);
      repeat(5, 32, (i) => zoneTick(p, z, i), p.id, "glyph");
    }, p.id, "glyph");
    return true;
  },
};

function zoneTick(p: Player, z: Zone, i: number): void {
  if (!p.isValid) return;
  const now = system.currentTick;
  if (i % 4 === 0) {
    for (let k = 0; k < 8; k++) {
      const pt = add(z.center, rotY(v3(0, 0, 6.2), k * 45 + i * 3));
      particle(z.dim, "plrace:glyph_pillar", add(pt, v3(0, 0.1, 0)));
    }
  }
  for (const e of enemiesNear(p, z.center, 9.2, z.dim)) {
    const d = hdist(e.location, z.center);
    if (Math.abs(e.location.y - z.center.y) > 4) continue;
    const prev = z.last.get(e.id);
    z.last.set(e.id, d);
    if (d <= 6.2) {
      effect(e, "slowness", 16, 2);
      if (i % 4 === 0) hurt(e, 1, p);
    } else if (prev !== undefined && d < prev - 0.04) {
      if ((z.zap.get(e.id) ?? 0) <= now) {
        z.zap.set(e.id, now + 20);
        knockFrom(e, z.center, 1.25, 0.35);
        hurt(e, 2, p);
        particle(z.dim, "plrace:rune_spark", add(e.location, v3(0, 1, 0)));
        sound(z.dim, "mob.breeze.deflect", e.location, 0.8, 0.8);
      }
    }
  }
}

const reassembly: AbilityDef = {
  id: "colossus_reassembly",
  name: "Colossus Reassembly",
  short: "Reform",
  cooldown: 38,
  range: 12,
  original: "Cooldown 40 s; fragments separate and reconstruct at a nearby destination, releasing a burst.",
  desc: "Your body bursts into orbiting fragments (untouchable while scattered), streams up to 12 blocks toward where you look, and reassembles on solid footing - the reconstruction releases a 4-block shockwave (6 damage, knockback). Needs aligned runes.",
  check({ s }) {
    return disrupted(s) ? "Runes disrupted - you cannot hold a scattered form" : undefined;
  },
  cast({ p, s }) {
    const dest = destination(p);
    if (!dest) return "No footing within 12 blocks";
    const from = add(p.location, v3(0, 1, 0));
    const d = sub(add(dest, v3(0, 1, 0)), from);
    const n = norm(d);
    tempForm(p, s, "scattered", 26);
    flag(s, "scattered", 24);
    pose(p, "gol_reassemble");
    strain(p, s, 18);
    particle(p.dimension, "plrace:shard_stream", from, { dx: n.x, dy: n.y, dz: n.z, len: len(d) });
    particle(p.dimension, "plrace:rune_burst", from);
    sound(p.dimension, "mob.irongolem.crack", p.location, 1, 0.8);
    sound(p.dimension, "mob.breeze.whirl", p.location, 1, 0.6);
    startChannel(p, s, {
      ability: "colossus_reassembly",
      mode: "block",
      until: system.currentTick + 22,
      tick: (_s2, p2, t) => {
        if (t === 10) {
          let ok = false;
          try {
            ok = p2.tryTeleport(dest, { checkForBlocks: true, keepVelocity: false });
          } catch {
            ok = false;
          }
          if (!ok) message(s, "§7The fragments could not pass - reformed in place", 40);
        }
        if (t === 20) {
          const c = p2.location;
          particle(p2.dimension, "plrace:rune_burst", add(c, v3(0, 1, 0)));
          particle(p2.dimension, "plrace:impact_ring", add(c, v3(0, 0.1, 0)));
          sound(p2.dimension, "mace.smash_ground", c, 1, 0.7);
          sound(p2.dimension, "beacon.power", c, 0.8, 0.8);
          for (const e of enemiesNear(p2, c, 4)) {
            hurt(e, 6, p2);
            knockFrom(e, c, 1.15, 0.45);
          }
        }
      },
      end: (s2, p2, reason) => {
        clearFlag(s2, "scattered");
        if (reason !== "leave" && p2.isValid) refreshForm(p2, s2);
      },
    });
    return true;
  },
};

function destination(p: Player): Vector3 | undefined {
  const dim = p.dimension;
  const target = rayPoint(p, 12);
  let spot = groundSpot(dim, target, 6, 2, 1);
  if (spot && dist(spot, p.location) >= 2.5) return spot;
  const from = eye(p);
  const dir = p.getViewDirection();
  for (let k = 11; k >= 3; k--) {
    spot = groundSpot(dim, add(from, mul(dir, k)), 6, 2, 1);
    if (spot && dist(spot, p.location) >= 2.5) return spot;
  }
  return undefined;
}

// ------------------------------------------------------------------ race

export const golem: RaceDef = {
  code: "002",
  key: "golem",
  name: "Runic Titan Golem",
  thai: "เผ่าไททันรูนโกเลม",
  title: "The Unsleeping Masonry",
  color: "§6",
  tagline: "Living architecture: separate stones held in formation by a mind made of runes.",
  lore: [
    "Before the first villages, an empire carved its laws into basalt so that they could never be forgotten. The laws remembered themselves instead. The glyphs began to rearrange their own stones, and a Titan stood up out of the ruin.",
    "A Runic Titan has no heart: three concentric rune rings turn around a suspended crystal where its thoughts are written and rewritten every moment. Its limbs are disconnected fragments that the runes hold in place, so in battle it does not swing an arm - it rebuilds its body into a hammer, a wall, or a circle of law.",
  ],
  strengths: ["+4 hearts and 25% less physical damage", "Near-immune to knockback", "Needs no air; walks the seabed", "Devastating area control"],
  weaknesses: ["Slower on land, sinks and swims poorly", "Magic, lightning, wither and storms disrupt its runes", "Disrupted runes lock its arcane abilities", "Large and deliberate: no quick escapes except Reassembly"],
  passives: [
    { name: "Basalt Body", desc: "+8 max health (Health Boost II). Conventional physical damage (melee, projectiles, falling blocks, contact) -25%, explosions -15%, falls -50%." },
    { name: "Rune-Bound Mass", desc: "Knockback from hits is cancelled. Falls of 4+ blocks crack the ground: nearby enemies take 3 damage and are thrown back." },
    { name: "No Breath", desc: "Never drowns. Heavy: Slowness I on land, Slowness II and steady sinking in water." },
    { name: "Rune Stability", desc: "Regenerates 2%/s (4%/s in Monolith Stance). Magic/wither/lightning damage (x4 per point), thunderstorms under open sky, a nearby lightning strike and every ability cast (8-18) erode it. Below 25% the runes are DISRUPTED until they recover to 50% (about 6-12 s)." },
    { name: "Monolith Stance", desc: "Stand still for 3 s: take 10% less damage and stability regenerates twice as fast." },
  ],
  abilities: [edict, bastion, dominion, reassembly],
  focusItem: "plrace:focus_golem",
  variant(_p, s) {
    if (s.channel?.ability === "runic_bastion") return "bastion";
    if (disrupted(s)) return "disrupted";
    return "";
  },
  cooldownMul(_p, s) {
    return disrupted(s) ? 1.25 : 1;
  },
  init(_p, s, first) {
    if (first) {
      s.data.res.rune = 100;
      s.data.st.gol = "aligned";
      s.dirty = true;
    }
  },
  cleanup(p, s) {
    for (let i = zones.length - 1; i >= 0; i--) if (zones[i].owner === p.id) zones.splice(i, 1);
    delete s.data.st.gol;
    try {
      p.removeEffect("health_boost");
    } catch {
      /* ignore */
    }
  },
  tick20(p, s) {
    // passives
    try {
      const hb = p.getEffect("health_boost");
      if (!hb || hb.amplifier !== 1 || hb.duration < 1200) effect(p, "health_boost", 2400, 1, false);
    } catch {
      effect(p, "health_boost", 2400, 1, false);
    }
    const water = p.isInWater;
    effect(p, "slowness", 50, water ? 1 : 0, false);
    if (headInWater(p)) effect(p, "water_breathing", 60, 0, false);
    // monolith stance
    const still = !isMoving(p) && p.isOnGround;
    const n = still ? (s.num.get("still") ?? 0) + 1 : 0;
    s.num.set("still", n);
    if (n >= 3) {
      flag(s, "monolith", 25);
      if (n % 3 === 0) particle(p.dimension, "plrace:rune_pulse", add(p.location, v3(0, 0.2, 0)));
    }
    // rune stability
    let d = n >= 3 ? 4 : 2;
    if (isOverworld(p) && weather() === "Thunder" && skyExposed(p)) d -= 3.5;
    try {
      if (p.getEffect("wither")) d -= 5;
    } catch {
      /* ignore */
    }
    if (Math.abs(d) > 0 && (stab(s) < 100 || d < 0)) setStability(p, s, stab(s) + d);
    // expire zones
    const now = system.currentTick;
    for (let i = zones.length - 1; i >= 0; i--) if (zones[i].until <= now) zones.splice(i, 1);
  },
  tick5(p) {
    // heavy body: sink while in water
    try {
      if (p.isInWater && !p.isOnGround) knock(p, v3(0, 0, 0), p.isSwimming ? -0.35 : -0.16);
    } catch {
      /* ignore */
    }
  },
  hud(_p, s) {
    const v = stab(s);
    const col = disrupted(s) ? "§c" : v > 60 ? "§6" : "§e";
    const tags: string[] = [];
    if (hasFlag(s, "monolith")) tags.push("§8monolith");
    if (s.channel?.ability === "runic_bastion") tags.push("§ebastion");
    return `${col}Runes ${meter(v / 100, 12)} ${Math.round(v)}% ${disrupted(s) ? "§cDISRUPTED" : "§6Aligned"}${tags.length ? " " + tags.join(" ") : ""}`;
  },
  onHurt(p, s, ev: EntityHurtBeforeEvent) {
    const cause = ev.damageSource.cause as string;
    if (hasFlag(s, "scattered")) {
      ev.cancel = true;
      return;
    }
    if (cause === "drowning") {
      ev.cancel = true;
      return;
    }
    if (PHYSICAL_CAUSES.has(cause)) ev.damage *= 0.75;
    else if (cause === "blockExplosion" || cause === "entityExplosion") ev.damage *= 0.85;
    else if (cause === "fall") ev.damage *= 0.5;
    if (s.channel?.ability === "runic_bastion") {
      const src = ev.damageSource.damagingEntity ?? ev.damageSource.damagingProjectile;
      let front = false;
      if (src && src.isValid) {
        const to = sub(src.location, p.location);
        front = angleBetween(flat(p.getViewDirection()), v3(to.x, 0, to.z)) <= 75;
      }
      if (front && cause === "projectile") {
        ev.cancel = true;
        system.run(() => {
          if (p.isValid) {
            particle(p.dimension, "plrace:bastion_flash", add(eye(p), mul(flat(p.getViewDirection()), 1.2)));
            sound(p.dimension, "item.shield.block", p.location, 1, 0.6);
          }
        });
        return;
      }
      ev.damage *= front ? 0.3 : 0.7;
      if (front) {
        system.run(() => {
          if (p.isValid) particle(p.dimension, "plrace:bastion_flash", add(eye(p), mul(flat(p.getViewDirection()), 1.2)));
        });
      }
    }
    if (hasFlag(s, "monolith")) ev.damage *= 0.9;
  },
  afterHurt(p, s, cause, amount) {
    if (MAGIC_CAUSES.has(cause)) strain(p, s, amount * 4);
    if (cause === "entityAttack" || cause === "projectile" || s.channel?.ability === "runic_bastion") {
      system.run(() => {
        if (!p.isValid) return;
        try {
          p.clearVelocity();
        } catch {
          try {
            p.applyKnockback({ x: 0, z: 0 }, 0);
          } catch {
            /* immovable */
          }
        }
      });
    }
    if (cause === "fall" && amount >= 1) {
      const c = { ...p.location };
      particle(p.dimension, "plrace:impact_ring", add(c, v3(0, 0.1, 0)));
      particle(p.dimension, "plrace:shock_rupture", c);
      sound(p.dimension, "mace.smash_ground", c, 1, 0.8);
      for (const e of enemiesNear(p, c, 2.8)) {
        hurt(e, 3, p);
        knockFrom(e, c, 0.8, 0.35);
      }
    }
    s.num.set("still", 0);
  },
};

/** A lightning bolt struck nearby. */
export function golemLightning(p: Player, s: Session, distance: number): void {
  if (distance > 8) return;
  strain(p, s, distance < 3 ? 70 : 45);
  privateSound(p, "mob.irongolem.crack", 1, 0.5);
}
