import { Entity, Vector3 } from "@minecraft/server";
import { DW04 as C } from "../config/dw04";
import { CONFIG } from "../config/global";
import { defineSpell } from "../core/registry";
import { addWard, damage, dissolveProjectiles, effect, heal, shove } from "../lib/combat";
import { burst, line, particle, ring, sound } from "../lib/fx";
import { Actor } from "../lib/scene";
import { allies, groundBelow, hostiles } from "../lib/targeting";
import { LIGHT, blocksFor } from "../lib/tempblocks";
import { add, bezier, dist, distXZ, easeOut, flat, lerp, mul, norm, polar, sub, up, yawOf } from "../lib/vec";

// Piece life cycle (tools/assets/dw_sanctuary.py PIECE_STATES) and script-line states (SCRIPT_STATES)
const P = { hidden: 0, letter: 1, form: 2, stand: 3, break: 4, unwrite: 5, flare: 6 };
const LS = { hidden: 0, write: 1, hold: 2, peel: 3, fade: 4 };
// Animation lengths in ticks (LETTER_T, FORM_T, BREAK_T, UNWRITE_T, FLARE_T, WRITE_T, FADE_T)
const FLY = 14, FORM = 20, BREAK = 26, UNWRITE = 30, FLARE = 10, WRITE = 24, FADE = 14;

type Kind = "pillar" | "gate" | "wall" | "bridge" | "rib" | "crown";
const ACTOR: Record<Kind, string> = {
  pillar: "dw_sanct_pillar", gate: "dw_sanct_gate", wall: "dw_sanct_wall", bridge: "dw_sanct_bridge",
  rib: "dw_sanct_rib", crown: "dw_sanct_crown",
};
/** Where each piece's giant letter sits relative to its origin, in blocks: [up, toward the centre]. */
const LETTER_REST: Record<Kind, [number, number]> = {
  pillar: [6, 0], wall: [4.25, 0], gate: [6.25, 0], bridge: [1.5, 0], rib: [2, 0.75], crown: [0.25, 0],
};
/** Which line of writing each course peels its letters from (0 low, 1 middle, 2 high). */
const LINE_OF: Record<Kind, number> = { pillar: 0, wall: 1, gate: 1, bridge: 1, rib: 2, crown: 2 };
/** The three lines of writing: script size (radius 3.5 blocks x size) and height above the floor. */
const LINES = [{ size: 1.0, h: 1.7 }, { size: 1.25, h: 2.9 }, { size: 1.5, h: 4.1 }];
/** Visual centre of each piece above its origin (for particles). */
const MID: Record<Kind, number> = { pillar: 6, wall: 4.5, gate: 6, bridge: 1.5, rib: 2.5, crown: 0 };

interface Cell { x: number; z: number; y?: number; h?: number }
interface Piece {
  kind: Kind;
  pos: Vector3;
  angle: number;
  launch: number;
  variant: number;
  yaw: number;
  actor?: Actor;
  cells: Cell[];
  standing: boolean;
  broken: boolean;
  bridge?: Piece;
  flareUntil: number;
}

/**
 * DW04 - Divine Edict: Let There Be Sanctuary.
 * Three lines of sacred writing circle the caster; letter after letter peels away, flies to its
 * place and is redrawn into marble: pillars, then walls, gates and galleries, then the vault ribs
 * and the keystone crown.  The finished octagonal cathedral stands for 12 s: barrier walls, a
 * threshold law that repels intruders, a ward with finite durability and projectile dissolution.
 * Damage breaks wall sections back into letters; at the end everything is unwritten.
 */
export default defineSpell("dw04", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const center = groundBelow(dim, caster.location);
  const fwd = aim.forward;
  const base = (Math.atan2(fwd.z, fwd.x) * 180) / Math.PI; // polar angle the caster faces: a gate opens there
  const book = add(up(caster.location, 1.2), mul(fwd, 0.7));
  const walls = blocksFor(scene);
  const lights = blocksFor(scene);
  const R = C.cornerRadius;
  const apothem = R * Math.cos(Math.PI / 8);

  // ------------------------------------------------------------------ plan of the cathedral
  const pieces: Piece[] = [];
  const mk = (kind: Kind, pos: Vector3, angle: number, launch: number, variant = 0): Piece => {
    const pc: Piece = { kind, pos, angle, launch, variant, yaw: 0, cells: [], standing: false, broken: false, flareUntil: 0 };
    pieces.push(pc);
    return pc;
  };
  const claimed = new Set<string>();
  const claim = (pc: Piece, x: number, z: number): void => {
    const key = `${x},${z}`;
    if (claimed.has(key)) return;
    claimed.add(key);
    pc.cells.push({ x, z });
  };
  const opposite = [0, 4, 2, 6, 1, 5, 3, 7]; // pillars rise in opposed pairs
  const pillars: Piece[] = [];
  for (let k = 0; k < 8; k++) {
    const a = base + 22.5 + 45 * k;
    const pc = mk("pillar", polar(center, R, a), a, C.pillarsAt + C.pillarGap * opposite.indexOf(k), k % 2);
    claim(pc, Math.floor(pc.pos.x), Math.floor(pc.pos.z));
    pillars.push(pc);
  }
  const gates: Piece[] = [];
  const sides: Piece[] = [];
  let bi = 0;
  for (let k = 0; k < 8; k++) {
    const a = base + 45 * k;
    const isGate = k % 2 === 0;
    const pc = mk(isGate ? "gate" : "wall", polar(center, apothem, a), a, C.wallsAt + C.wallGap * k);
    (isGate ? gates : sides).push(pc);
    // barrier cells along this side of the octagon (the doorway of a gate stays open)
    const ca = polar(center, R, a - 22.5), cb = polar(center, R, a + 22.5);
    const len = dist(ca, cb);
    const n = Math.ceil(len / 0.25);
    for (let i = 0; i <= n; i++) {
      const p = lerp(ca, cb, i / n);
      const x = Math.floor(p.x), z = Math.floor(p.z);
      const along = ((x + 0.5 - ca.x) * (cb.x - ca.x) + (z + 0.5 - ca.z) * (cb.z - ca.z)) / len;
      if (isGate && Math.abs(along - len / 2) < C.doorHalf) continue;
      claim(pc, x, z);
    }
    if (!isGate) pc.bridge = mk("bridge", polar(center, apothem, a, C.bridgeHeight), a, C.bridgesAt + C.bridgeGap * bi++);
  }
  const ribs: Piece[] = [];
  for (let k = 0; k < 8; k++) {
    const a = base + 22.5 + 45 * k;
    ribs.push(mk("rib", polar(center, R, a, C.ribSpring), a, C.ribsAt + C.ribGap * opposite.indexOf(k)));
  }
  const crown = mk("crown", up(center, C.crownHeight), base, C.crownAt);

  const tDefend = C.pillarsAt + FLY + FORM;      // first pillar stands: the law is in force
  const tComplete = C.crownAt + FLY + FORM;      // keystone set: the sanctuary is complete
  const tUnwrite = tComplete + C.activeTicks;
  const unwriteOrder = [crown, ...ribs, ...pieces.filter((p) => p.kind === "bridge"), ...gates, ...sides, ...pillars];
  scene.endAt(tUnwrite + unwriteOrder.length * C.unwriteGap + UNWRITE + 10);

  let active = false, collapsed = false, finished = false;

  // ------------------------------------------------------------------ the writing
  const circle = scene.spawn("dw_circle", up(center, 0.05), { size: R / 2, state: 1 });
  scene.at(16, () => circle.state(2));
  sound(dim, "dw_sanct_write", book, 1.1);
  const lines: Actor[] = [];
  const firstOf = [C.pillarsAt, C.wallsAt, C.ribsAt];
  LINES.forEach((ln, i) => {
    scene.at(i * 3, () => {
      const at = up(center, ln.h);
      lines[i] = scene.spawn("dw_sanct_script", at, { yaw: aim.yaw + i * 40, size: ln.size, state: LS.write });
      line(dim, "dw_sanct_ink", book, polar(center, 3.5 * ln.size, base + 180 + i * 30, ln.h), 4);
    });
    scene.at(i * 3 + WRITE, () => lines[i]?.state(LS.hold));
    scene.at(firstOf[i], () => lines[i]?.state(LS.peel));
    scene.at(C.crownAt + 2, () => lines[i]?.state(LS.fade));
    scene.at(C.crownAt + 2 + FADE, () => { if (lines[i]) scene.despawn(lines[i]); });
  });
  scene.every(5, () => particle(dim, "dw_sanct_ink", book), 0, C.crownAt);

  for (const pc of pieces) scene.at(pc.launch, () => launch(pc));

  function launch(pc: Piece): void {
    if (collapsed || pc.broken) return;
    const ln = LINES[LINE_OF[pc.kind]];
    const yaw = pc.kind === "crown" ? aim.yaw : yawOf(sub(center, pc.pos));
    pc.yaw = yaw;
    const toward = pc.kind === "crown" ? { x: 0, y: 0, z: 0 } : norm(flat(sub(center, pc.pos)));
    const [ru, rf] = LETTER_REST[pc.kind];
    const off = add({ x: 0, y: ru, z: 0 }, mul(toward, rf));
    const glyphAt = polar(center, 3.5 * ln.size, pc.angle, ln.h);
    const start = sub(glyphAt, off);
    const end = pc.pos;
    const ctrl = up(lerp(start, end, 0.45), 3 + (end.y - center.y) * 0.25);
    const a = scene.spawn(ACTOR[pc.kind], start, { yaw, state: P.letter, kind: pc.kind === "pillar" ? pc.variant : undefined });
    pc.actor = a;
    particle(dim, "dw_sanct_peel", glyphAt);
    sound(dim, "dw_sanct_letter", glyphAt, 0.7, 0.9 + (pc.launch % 5) * 0.05);
    const t0 = scene.tick;
    scene.span(t0, t0 + FLY, (p) => { if (!pc.broken) a.move(bezier(start, ctrl, end, easeOut(p)), yaw); });
    scene.every(3, () => { if (!pc.broken && a.valid) particle(dim, "dw_sanct_ink", add(a.loc, off)); }, t0 + 1, t0 + FLY);
    scene.at(t0 + FLY, () => {
      if (pc.broken) return;
      a.move(end, yaw).state(P.form);
      particle(dim, "dw_sanct_quill", up(end, pc.kind === "rib" || pc.kind === "crown" ? 0.5 : 0.3));
    });
    scene.at(t0 + FLY + FORM, () => {
      if (pc.broken) return;
      a.state(P.stand);
      pc.standing = true;
      const mid = add(up(end, MID[pc.kind]), mul(toward, pc.kind === "rib" ? 3 : 0));
      if (pc.kind === "pillar" || pc.kind === "wall" || pc.kind === "gate") particle(dim, "dw_sanct_settle", up(end, 0.2));
      particle(dim, "dw_sanct_gild", mid);
      const pitch = { pillar: 0.95, wall: 1.0, gate: 0.85, bridge: 1.1, rib: 1.15, crown: 0.8 }[pc.kind];
      sound(dim, "dw_sanct_settle", mid, 0.9, pitch);
      raise(pc);
    });
  }

  // ------------------------------------------------------------------ real walls: barrier columns
  function occupied(x: number, z: number, y: number): boolean {
    let found: Entity[] = [];
    try {
      found = dim.getEntities({ location: { x: x + 0.5, y: y + 1, z: z + 0.5 }, maxDistance: 2.2, excludeFamilies: ["grimoire_construct"],
        excludeTypes: ["minecraft:item", "minecraft:xp_orb", "minecraft:player"] });
    } catch { return false; }
    return found.some((e) => {
      const l = e.location;
      return Math.abs(l.x - (x + 0.5)) < 0.95 && Math.abs(l.z - (z + 0.5)) < 0.95;
    });
  }
  function raise(pc: Piece): void {
    for (const c of pc.cells) {
      const floor = groundBelow(dim, { x: c.x + 0.5, y: center.y + 2.5, z: c.z + 0.5 }, 8).y;
      if (Math.abs(floor - center.y) > 3 || occupied(c.x, c.z, floor)) continue;
      c.y = Math.floor(floor);
      c.h = C.barrierHeight;
      walls.column(c.x, c.y, c.z, c.h);
    }
  }
  function lower(pc: Piece): void {
    for (const c of pc.cells) if (c.y !== undefined && c.h) { walls.removeColumn(c.x, c.y, c.z, c.h); c.y = undefined; }
  }

  // ------------------------------------------------------------------ the ward and the threshold law
  const inside = (l: Vector3): boolean =>
    distXZ(l, center) <= C.innerRadius && l.y >= center.y - C.insideBelow && l.y <= center.y + C.insideAbove;
  const safeLoc = (e: Entity | undefined): Vector3 | undefined => {
    try { return e && e.isValid ? { ...e.location } : undefined; } catch { return undefined; }
  };
  const ward = addWard({
    scene,
    factor: C.wardFactor,
    pool: C.durability,
    protects: (e) => active && e.typeId === "minecraft:player" && (!CONFIG.targeting.pvp || e.id === caster.id) && inside(e.location),
    onAbsorb: (_amount, attacker, victim) => {
      const vl = safeLoc(victim);
      if (vl) {
        particle(dim, "dw_sanct_ward", up(vl, 1));
        sound(dim, "dw_sanct_absorb", vl, 0.8);
        flare(nearest([...sides, ...gates], vl));
      }
      checkDurability(safeLoc(attacker) ?? vl ?? center);
    },
    onBreak: () => collapse(),
  });

  function spend(cost: number, at: Vector3): void {
    ward.pool = Math.max(0, (ward.pool ?? 0) - cost);
    checkDurability(at);
  }
  let nextBreak = 0;
  function checkDurability(at: Vector3): void {
    if (collapsed || finished) return;
    const frac = (ward.pool ?? 0) / C.durability;
    while (nextBreak < C.breakAt.length && frac <= C.breakAt[nextBreak]) { nextBreak++; breakSection(at); }
    if ((ward.pool ?? 0) <= 0.0001) { ward.broken = true; collapse(); }
  }

  function nearest(list: Piece[], at: Vector3): Piece | undefined {
    let best: Piece | undefined, bd = Infinity;
    for (const p of list) { const d = distXZ(p.pos, at); if (d < bd) { bd = d; best = p; } }
    return best;
  }
  function flare(pc: Piece | undefined): void {
    if (!pc || !pc.standing || pc.broken || !pc.actor?.valid) return;
    pc.actor.state(P.flare);
    pc.flareUntil = scene.tick + FLARE;
    const a = pc.actor;
    scene.after(FLARE, () => { if (pc.standing && !pc.broken && scene.tick >= pc.flareUntil) a.state(P.stand); });
  }
  function breakPiece(pc: Piece, loud = true): void {
    if (pc.broken) return;
    pc.broken = true;
    pc.standing = false;
    lower(pc);
    const a = pc.actor;
    if (!a || !a.valid) return;
    a.state(P.break);
    const mid = up(pc.pos, MID[pc.kind]);
    particle(dim, "dw_sanct_shard", mid);
    if (loud) sound(dim, "dw_sanct_break", mid, 1.0);
    scene.after(BREAK, () => scene.despawn(a));
  }
  /** Durability feedback: one wall section (wall + its gallery, or a gate) falls back into letters. */
  function breakSection(at: Vector3): void {
    const pick = nearest(sides.filter((p) => p.standing), at) ?? nearest(gates.filter((p) => p.standing), at);
    if (!pick) return;
    breakPiece(pick);
    if (pick.bridge) { const b = pick.bridge; scene.after(4, () => breakPiece(b, false)); }
  }
  function collapse(): void {
    if (collapsed || finished) return;
    collapsed = true;
    active = false;
    ward.broken = true;
    sound(dim, "dw_sanct_break", up(center, 6), 1.4, 0.8);
    const order = unwriteOrder.filter((p) => !p.broken);
    order.forEach((pc, i) => { if (!pc.actor) { pc.broken = true; return; } scene.after(i, () => breakPiece(pc, i % 6 === 0)); });
    scene.after(order.length + 6, () => { circle.state(3); sound(dim, "dw_sanct_unwrite", up(center, 4), 1.0, 0.9); lights.clearAll(); });
    scene.after(order.length + 18, () => scene.despawn(circle));
    scene.endAt(scene.tick + order.length + BREAK + 22);
  }

  // threshold law: hostiles that cross into the sanctuary are thrown back out through the nearest gate
  const lastRepel = new Map<string, number>();
  scene.every(C.thresholdEvery, () => {
    if (!active) return;
    for (const e of hostiles(dim, center, C.thresholdRadius + 2, caster)) {
      const l = e.location;
      if (!inside(l) || distXZ(l, center) > C.thresholdRadius) continue;
      if (scene.tick - (lastRepel.get(e.id) ?? -999) < C.repelCooldown) continue;
      lastRepel.set(e.id, scene.tick);
      const gate = nearest(gates, l)!;
      const dir = distXZ(l, gate.pos) < 1.6 ? sub(l, center) : sub(gate.pos, l);
      shove(e, dir, C.repelH, C.repelV);
      effect(e, "slowness", C.repelSlowTicks, C.repelSlowAmp);
      damage(e, C.repelDamage, caster);
      particle(dim, "dw_sanct_edict", up(l, 0.15));
      particle(dim, "dw_sanct_law", up(l, 1.0));
      particle(dim, "dw_sanct_edict", up(gate.pos, 0.2));
      flare(gate);
      sound(dim, "dw_sanct_repel", l, 1.0);
      spend(C.repelCost, l);
      if (!active) return;
    }
  }, tDefend, tUnwrite);

  // hostile projectiles entering the sanctuary dissolve into letters
  scene.every(C.projectileEvery, () => {
    if (!active) return;
    const gone = dissolveProjectiles(scene, up(center, 6), R + 2);
    if (!gone.length) return;
    for (const l of gone.slice(0, 4)) particle(dim, "dw_sanct_dissolve", l);
    sound(dim, "dw_sanct_dissolve", gone[0], 0.8);
    flare(nearest([...sides, ...gates], gone[0]));
    spend(C.projectileCost * gone.length, gone[0]);
  }, tDefend, tUnwrite);

  // gentle regeneration for allies inside
  scene.every(C.regenEvery, () => {
    if (!active) return;
    for (const p of allies(dim, center, C.innerRadius + 3, caster)) {
      if (inside(p.location) && heal(p, C.regenAmount) > 0) particle(dim, "dw_sanct_gild", up(p.location, 0.6));
    }
  }, tDefend, tUnwrite);

  scene.at(tDefend, () => {
    active = true;
    lights.place(up(center, 2), LIGHT);
    for (let k = 0; k < 4; k++) lights.place(polar(center, 5, base + 45 + 90 * k, 3), LIGHT);
  });

  // ------------------------------------------------------------------ completion: "Let there be sanctuary"
  scene.at(tComplete, () => {
    if (collapsed) return;
    sound(dim, "dw_sanct_complete", up(center, 8), 1.4);
    for (const pc of [...gates, ...sides]) flare(pc);
    ring(dim, "dw_sanct_beam", up(center, 0.2), R, 8, base + 22.5);
    burst(dim, "dw_sanct_gild", up(center, C.crownHeight), 2, 6);
    particle(dim, "dw_sanct_edict", up(center, 0.3));
  });
  scene.every(8, () => { if (active) particle(dim, "dw_sanct_mote", up(center, 2.5)); }, tComplete, tUnwrite);
  scene.every(60, () => { if (active) sound(dim, "dw_sanct_bed", up(center, 4), 0.6); }, tComplete, tUnwrite);

  // ------------------------------------------------------------------ ending: the cathedral is unwritten
  scene.at(tUnwrite, () => {
    if (collapsed) return;
    finished = true;
    active = false;
    ward.broken = true;
    sound(dim, "dw_sanct_unwrite", up(center, 6), 1.3);
    unwriteOrder.forEach((pc, i) => {
      scene.after(i * C.unwriteGap, () => {
        if (pc.broken) return;
        pc.standing = false;
        lower(pc);
        const a = pc.actor;
        if (!a || !a.valid) return;
        a.state(P.unwrite);
        if (i % 2 === 0) particle(dim, "dw_sanct_stream", up(pc.pos, MID[pc.kind]));
        scene.after(UNWRITE, () => scene.despawn(a));
      });
    });
    const n = unwriteOrder.length * C.unwriteGap;
    scene.after(n + 12, () => { circle.state(3); lights.clearAll(); burst(dim, "dw_sanct_stream", up(center, 3), 3, 6); });
    scene.after(n + 24, () => scene.despawn(circle));
  });
});
