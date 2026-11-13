import { Entity, Vector3 } from "@minecraft/server";
import { DW06 as C } from "../config/dw06";
import { CONFIG } from "../config/global";
import { defineSpell } from "../core/registry";
import { addWard, damage, dissolveProjectiles, effect, heal, knockback, restrain, shove } from "../lib/combat";
import { burst, line, particle, ring, sound } from "../lib/fx";
import { Actor, secs } from "../lib/scene";
import { allies, focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { LIGHT, blocksFor } from "../lib/tempblocks";
import { add, bezier, dist, distXZ, flat, lerp, mul, norm, right, sub, up, yawOf } from "../lib/vec";

// ---- animation states (mirrors tools/assets/dw6_*.py; lengths in ticks)
const BOOK = { hidden: 0, arrive: 1, open: 2, unbind: 3, layered: 4, gather: 5, close: 6 }; // arrive 60, unbind 40, gather 30, close 50
const PAGE = { hidden: 0, manifest: 1, idle: 2, split: 3, reform: 4, fold: 5, slip: 6 }; // manifest 50, split 24, reform 30, fold 100, slip 16
const GLYPH = { draw: 1, fall: 2, land: 3 }; // draw 24, fall 16, land 10
const ED = { assemble: 1, hold: 2, swing: 3, strike: 4, unwrite: 5 }; // assemble 32, swing 28 (lands at 21), strike 16, unwrite 40
const WALL = { rise: 1, hold: 2, sink: 3 }; // rise 20, sink 20
const DOME = { form: 1, hold: 2, fade: 3 }; // form 24, fade 20
const BOUND = { inscribe: 1, hold: 2, unwrite: 3 }; // inscribe 40, unwrite 30
const TAB = { form: 1, idle: 2, declare: 3, shed: 4, ret: 5 }; // form 20, declare 32, shed 28, return 20
const LINE = { assemble: 1, hold: 2, strike: 3, unwrite: 4 }; // assemble 30, strike 12, unwrite 20
const PAGE_TILT = 32 * (Math.PI / 180);
const PAGE_SCALE = 4 / 16; // page model units -> blocks
const ED_SCALE = 2 / 16;
// structure kinds: 0 column, 1 arch, 2 bridge, 3 gate, 4 platform, 5 celestial
const COLUMN = 0, ARCH = 1, BRIDGE = 2, GATE = 3, PLATFORM = 4, CELESTIAL = 5;

interface Edifice { a: Actor; kind: number; at: Vector3; yaw: number; cells: Vector3[]; h: number }

/**
 * DW06 - The Word Before Creation (Extra Ultimate, ~65 s).
 * I   The Grimoire's great codex rises; its pages lift away blank; a vast ivory page hangs over the domain.
 * II  Ten golden letters are drawn on the page; each falls out as 3D and lands as written marble architecture.
 * III The page parts into seven tablets; each declares a local law (containment, station, direction,
 *     stillness, refuge, sequence, judgment).
 * IV  The tablets rise, their letters assemble into lines of sacred text that descend one by one,
 *     ending in an immense white-gold formation upon the judged region.
 * V   Everything is unwritten: structures flow back as text, the page folds down and slips into the codex.
 */
export default defineSpell("dw06", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center: C0, target } = focus(caster, aim, C.focusSnap);
  const center = groundBelow(dim, C0);
  const c0 = caster.location;
  let fwd = norm(flat(sub(center, c0)));
  if (distXZ(center, c0) < 3) fwd = norm(flat(aim.forward));
  const rt = right(fwd);
  const tb = blocksFor(scene);
  const P = (a: number, b: number, h = 0): Vector3 => up(add(add(center, mul(rt, a)), mul(fwd, b)), h);
  const ground = (p: Vector3): Vector3 => groundBelow(dim, up(p, 3), 12);
  const faceCaster = (p: Vector3): number => yawOf(sub(caster.isValid ? caster.location : c0, p));
  const domain = (): Entity[] => hostiles(dim, center, C.domainRadius, caster);
  const isAlly = (e: Entity): boolean => e.typeId === "minecraft:player" && (e.id === caster.id || !CONFIG.targeting.pvp);

  // ------------------------------------------------------------------ marks
  const marks = new Map<string, { e: Entity; a: Actor }>();
  function mark(e: Entity, skin = 0): void {
    let m = marks.get(e.id);
    if (!m || !m.a.valid) {
      if (marks.size >= C.maxMarks || !isAlive(e)) return;
      const a = scene.spawn("dw_mark", up(e.location, 2.4), { state: 1 });
      scene.follow(a, e, 2.4);
      m = { e, a };
      marks.set(e.id, m);
      sound(dim, "dw_mark", e.location, 0.6, 0.9 + skin * 0.1);
    }
    m.a.skin(skin);
  }

  // ================================================================== PHASE I -- the silence before all things
  const bookAt = up(add(add(c0, mul(rt, 3.4)), mul(fwd, 1.6)), 1.3);
  const book = scene.spawn("dw6_book", bookAt, { yaw: faceCaster(bookAt), state: BOOK.arrive });
  sound(dim, "dw6_silence", c0, 1.0);
  sound(dim, "dw6_book", bookAt, 0.9);
  const boundary = scene.spawn("dw6_boundary", up(center, 0.05), { state: BOUND.inscribe });
  scene.at(40, () => boundary.state(BOUND.hold));
  scene.every(20, () => particle(dim, "dw6_motes", P(0, 0, 6)), 0, 140);
  scene.at(18, () => particle(dim, "dw6_bell", P(0, 0, 10)));
  tb.place(up(bookAt, 1), LIGHT);
  scene.at(14, () => { for (const e of domain()) mark(e); });
  scene.at(60, () => book.state(BOOK.open));
  scene.at(70, () => {
    book.state(BOOK.unbind).skin(1); // the inscriptions vanish from the pages
    sound(dim, "dw6_unbind", bookAt, 0.9);
  });
  scene.every(5, () => burst(dim, "dw6_letters", up(bookAt, 1.2), 1.4, 2), 72, 104);
  scene.at(110, () => book.state(BOOK.layered));

  // the giant page: ~30 x 22 blocks, high over the domain, leaning its face toward the caster
  const pageO = P(0, 5, 9);
  const pd = norm(flat(sub(c0, pageO)));
  const pageYaw = yawOf(pd);
  const pr = right(pd);
  const pageUp = add(mul(up({ x: 0, y: 0, z: 0 }, 1), Math.cos(PAGE_TILT)), mul(pd, -Math.sin(PAGE_TILT)));
  const pageN = add(mul(pd, Math.cos(PAGE_TILT)), up({ x: 0, y: 0, z: 0 }, Math.sin(PAGE_TILT)));
  /** a = viewer's left -> right in page units (-60..60), y = page units up (0..88). */
  const pagePt = (a: number, y: number, off = 0): Vector3 =>
    add(add(add(pageO, mul(pr, -a * PAGE_SCALE)), mul(pageUp, y * PAGE_SCALE)), mul(pageN, off));
  let page = scene.spawn("dw6_page", pageO, { yaw: pageYaw, state: PAGE.hidden });
  scene.at(75, () => {
    page.state(PAGE.manifest);
    sound(dim, "dw6_page", pagePt(0, 44), 1.2);
    line(dim, "dw6_seam", pagePt(0, 0, 0.3), pagePt(0, 88, 0.3), 10);
  });
  scene.at(125, () => page.state(PAGE.idle));

  // ================================================================== PHASE II -- the first utterance
  const tWrite0 = 140, tWriteStep = 28;
  const plan: { kind: number; a: number; b: number }[] = [
    { kind: COLUMN, a: -7, b: 1 }, { kind: COLUMN, a: 7, b: 1 }, { kind: ARCH, a: 0, b: -5 },
    { kind: PLATFORM, a: -4.5, b: -99 }, { kind: BRIDGE, a: 0, b: 4.5 }, { kind: GATE, a: 0, b: 13 },
    { kind: COLUMN, a: -11, b: 9 }, { kind: CELESTIAL, a: 6, b: 9 }, { kind: PLATFORM, a: 4.5, b: -99 },
    { kind: ARCH, a: 12, b: 3 },
  ];
  const edifices: Edifice[] = [];
  const claimed = new Set<string>();
  const cover: Vector3[] = [];
  addWard({
    scene, factor: C.coverFactor,
    protects: (e) => isAlly(e) && cover.some((p) => distXZ(p, e.location) <= C.coverRadius),
  });

  function landingSpot(i: number): Vector3 {
    const s = plan[i];
    let p = s.b === -99 ? up(add(add(c0, mul(rt, s.a)), mul(fwd, 2.5)), 0) : P(s.a, s.b);
    if (s.kind === COLUMN || s.kind === CELESTIAL) {
      const near = hostiles(dim, p, C.seekRadius, caster).filter((e) => !claimed.has(e.id) && dist(e.location, center) <= C.domainRadius);
      if (near.length) { claimed.add(near[0].id); p = near[0].location; }
    }
    return ground(p);
  }

  function cellsFor(kind: number, at: Vector3): Vector3[] {
    const r = right(norm(flat(sub(c0, at))));
    const offs = kind === COLUMN ? [0] : kind === ARCH ? [-22 * ED_SCALE, 22 * ED_SCALE] : kind === GATE ? [-3.9, -2.9, 2.9, 3.9] : [];
    return offs.map((o) => add(at, mul(r, o)));
  }

  function raiseBarriers(ed: Edifice): void {
    for (const c of ed.cells) {
      for (const e of hostiles(dim, c, 1.3, caster)) knockback(e, c, 0.8, 0.2);
      scene.after(2, () => tb.column(Math.floor(c.x), Math.floor(c.y), Math.floor(c.z), ed.h));
    }
  }
  function dropBarriers(ed: Edifice): void {
    for (const c of ed.cells) tb.removeColumn(Math.floor(c.x), Math.floor(c.y), Math.floor(c.z), ed.h);
  }

  function impact(kind: number, at: Vector3, cellPts: Vector3[]): void {
    const spots = kind === ARCH ? cellPts : [at];
    particle(dim, "dw6_quake", up(at, 0.2));
    particle(dim, "dw6_dust", up(at, 0.4));
    particle(dim, "dw6_flare", up(at, 2));
    burst(dim, "dw6_ink", up(at, 3), 2.5, 3);
    sound(dim, "dw6_land", at, 1.3, 1 - kind * 0.03);
    if (C.landDamage[kind] <= 0 && kind !== PLATFORM) return;
    const hit = new Set<string>();
    for (const s of spots) {
      for (const e of hostiles(dim, s, C.landRadius[kind], caster)) {
        if (hit.has(e.id)) continue;
        hit.add(e.id);
        if (C.landDamage[kind] > 0) damage(e, C.landDamage[kind], caster);
        knockback(e, s, C.landKnock[kind], 0.4);
      }
    }
  }

  function writeLetter(i: number): void {
    const t0 = tWrite0 + i * tWriteStep;
    const s = plan[i];
    const slotA = -36 + (i % 5) * 19, slotY = i < 5 ? 63 : 25;
    let land = P(0, 0);
    let warn: Actor | undefined;
    let glyph: Actor | undefined;
    scene.at(t0, () => {
      land = landingSpot(i);
      const at = pagePt(slotA, slotY, 0.6);
      glyph = scene.spawn("dw6_glyph", at, { yaw: pageYaw, kind: s.kind, state: GLYPH.draw });
      sound(dim, "dw6_stroke", at, 1.2);
      warn = scene.spawn("telegraph", land, { kind: 0, size: s.kind === BRIDGE ? C.landRadius[BRIDGE] : Math.max(2, C.landRadius[s.kind]), state: 4 });
    });
    scene.every(4, (e) => particle(dim, "dw6_ink", pagePt(slotA + (e % 8) - 4, slotY + 12 - e * 1.1, 0.8)), t0 + 2, t0 + 24);
    scene.at(t0 + 24, () => { glyph?.state(GLYPH.fall); sound(dim, "dw6_fall", pagePt(slotA, slotY), 1.0); });
    scene.span(t0 + 24, t0 + 40, (p) => {
      const from = pagePt(slotA, slotY, 0.6);
      const to = up(land, 3.5);
      const mid = up(lerp(from, to, 0.5), 3);
      glyph?.move(bezier(from, mid, to, p * p), pageYaw);
      if (glyph && scene.tick % 2 === 0) particle(dim, "dw6_stream", glyph.loc);
    });
    scene.at(t0 + 40, () => {
      if (glyph) { glyph.state(GLYPH.land); const g = glyph; scene.after(10, () => scene.despawn(g)); }
      if (warn) { warn.state(3); const w = warn; scene.after(8, () => scene.despawn(w)); }
      const yaw = faceCaster(land);
      const a = scene.spawn("dw6_edifice", land, { yaw, kind: s.kind, state: s.kind === BRIDGE ? ED.swing : ED.assemble });
      const ed: Edifice = { a, kind: s.kind, at: land, yaw, cells: cellsFor(s.kind, land), h: C.barrierHeight[s.kind] };
      edifices.push(ed);
      if (s.kind === BRIDGE) {
        sound(dim, "dw6_swing", land, 1.2);
        scene.after(21, () => impact(BRIDGE, land, []));
      } else impact(s.kind, land, ed.cells);
      if (ed.cells.length) raiseBarriers(ed);
      if (s.kind === PLATFORM || s.kind === BRIDGE) cover.push(land);
      if (s.kind === CELESTIAL) {
        scene.every(C.celestialPulseEvery, () => {
          if (!a.valid) return;
          particle(dim, "dw6_rays", up(ed.at, 0.3));
          for (const e of hostiles(dim, ed.at, C.celestialPulseRadius, caster)) damage(e, C.celestialPulseDamage, caster);
        }, scene.tick + 20, tPhase5);
      }
      scene.after(s.kind === BRIDGE ? 28 : 32, () => a.state(ED.hold));
      // the letter is spoken: a mark for every enemy the landing reached
      for (const e of hostiles(dim, land, C.landRadius[s.kind] + 1, caster)) if (dist(e.location, center) <= C.domainRadius) mark(e);
    });
  }
  for (let i = 0; i < plan.length; i++) writeLetter(i);

  // ================================================================== PHASE III -- the laws written in heaven
  const tSplit = tWrite0 + tWriteStep * plan.length + 30; // 470
  const tablets: Actor[] = [];
  const stations: Vector3[] = [];
  for (let k = 0; k < 7; k++) {
    const th = ((-66 + 22 * k) * Math.PI) / 180;
    const dir = add(mul(fwd, Math.cos(th)), mul(rt, Math.sin(th)));
    stations.push(up(add(center, mul(dir, 17)), 7));
  }
  const ruleA = (k: number): number => -45 + (102 / 7) * (k + 0.5);
  scene.at(tSplit, () => {
    page.state(PAGE.split);
    sound(dim, "dw6_split", pagePt(0, 44), 1.3);
    for (let k = 1; k < 7; k++) line(dim, "dw6_seam", pagePt(-45 + (102 / 7) * k, 6, 0.5), pagePt(-45 + (102 / 7) * k, 82, 0.5), 6);
  });
  scene.at(tSplit + 6, () => {
    for (let k = 0; k < 7; k++) {
      const from = pagePt(ruleA(k), 44, 0.4);
      tablets.push(scene.spawn("dw6_tablet", from, { yaw: pageYaw, kind: k, state: TAB.form }));
    }
  });
  scene.span(tSplit + 6, tSplit + 36, (p) => {
    tablets.forEach((t, k) => {
      const from = pagePt(ruleA(k), 44, 0.4);
      const to = stations[k];
      t.move(bezier(from, up(lerp(from, to, 0.5), 4), to, p * p * (3 - 2 * p)), faceCaster(to));
    });
  });
  scene.at(tSplit + 30, () => { scene.despawn(page); });
  scene.at(tSplit + 36, () => tablets.forEach((t) => t.state(TAB.idle)));

  const tLaw0 = tSplit + 50, tLawStep = 34;
  const walls: Actor[] = [];
  let refuge: Actor | undefined;
  let refugeAt = c0;
  let refugeOn = false;
  addWard({ scene, factor: C.refugeFactor, protects: (e) => refugeOn && isAlly(e) && distXZ(e.location, refugeAt) <= C.refugeRadius });
  let finalAt = center;
  let finalWarn: Actor | undefined;
  const judged = new Set<string>();
  const judgedWarn: Actor[] = [];

  function centroid(es: Entity[], fallback: Vector3): Vector3 {
    if (!es.length) return fallback;
    let s = { x: 0, y: 0, z: 0 };
    for (const e of es) s = add(s, e.location);
    return mul(s, 1 / es.length);
  }

  function declare(k: number, at: Vector3): void {
    const t = tablets[k];
    t.state(TAB.declare);
    sound(dim, `dw6_law${k + 1}`, t.loc, 1.4);
    line(dim, "dw6_stream", up(t.loc, 3), up(at, 1), 10);
    particle(dim, "dw6_quake", up(at, 0.3));
    scene.after(34, () => t.state(TAB.idle));
  }

  const laws: (() => void)[] = [
    // I Containment: a ring of written walls closes around the densest hostile region and draws it in
    () => {
      const es = domain();
      const H = ground(centroid(es, P(0, 5)));
      declare(0, H);
      const R = C.containRadius;
      const players = allies(dim, H, R + 1.5, caster);
      const door = yawOf(sub(c0, H));
      for (let i = 0; i < 8; i++) {
        const ang = i * 45 + 22.5;
        const rad = (ang * Math.PI) / 180;
        const p = ground({ x: H.x + Math.cos(rad) * R, y: H.y, z: H.z + Math.sin(rad) * R });
        walls.push(scene.spawn("dw6_wall", p, { yaw: yawOf(sub(H, p)), kind: 0, size: 1.2, state: WALL.rise }));
      }
      scene.after(20, () => walls.forEach((w) => w.state(WALL.hold)));
      for (const d of [2, 8]) {
        scene.after(d, () => {
          for (const e of hostiles(dim, H, C.containPull, caster)) if (distXZ(e.location, H) > R - 1.5) shove(e, sub(H, e.location), C.containPullStrength, 0.25);
        });
      }
      scene.after(16, () => {
        for (let s = 0; s < 64; s++) {
          const a = (s * 360) / 64;
          if (players.length && Math.abs((((a - (door + 90)) % 360) + 540) % 360 - 180) < 22) continue; // doorway toward the caster
          const rad = (a * Math.PI) / 180;
          const p = ground({ x: H.x + Math.cos(rad) * R, y: H.y, z: H.z + Math.sin(rad) * R });
          tb.column(Math.floor(p.x), Math.floor(p.y), Math.floor(p.z), 3);
        }
      });
    },
    // II Station: written structures slide between the allies and the enemy
    () => {
      const E = centroid(domain(), center);
      const A = caster.isValid ? caster.location : c0;
      const toE = norm(flat(sub(E, A)));
      const side = right(toE);
      const d = Math.min(C.stationDistance, Math.max(3, distXZ(E, A) / 2));
      const movers = edifices.filter((e) => e.kind === COLUMN || e.kind === ARCH).slice(0, C.stationCount);
      declare(1, add(A, mul(toE, d)));
      movers.forEach((ed, j) => {
        const dest = ground(add(add(A, mul(toE, d)), mul(side, (j - (movers.length - 1) / 2) * 4.5)));
        const from = ed.at;
        dropBarriers(ed);
        ed.a.state(ED.strike);
        scene.span(scene.tick + 2, scene.tick + 32, (p) => {
          const q = p * p * (3 - 2 * p);
          ed.a.move(up(lerp(from, dest, q), Math.sin(q * Math.PI) * 1.5));
          if (scene.tick % 3 === 0) particle(dim, "dw6_dust", up(lerp(from, dest, q), 0.3));
        });
        scene.after(33, () => {
          ed.at = dest;
          ed.cells = cellsFor(ed.kind, dest);
          ed.a.state(ED.hold);
          raiseBarriers(ed);
          particle(dim, "dw6_quake", up(dest, 0.2));
        });
      });
    },
    // III Direction: three lines of text fire across the field as moving walls
    () => {
      declare(2, P(0, 4));
      const lanes = [-2, 4, 10];
      lanes.forEach((b, j) => {
        const from = ground(P(-17, b)), to = ground(P(17, b));
        line(dim, "dw6_ink", up(from, 0.5), up(to, 0.5), 8);
        const w = scene.spawn("dw6_wall", from, { yaw: yawOf(rt), kind: 1, size: 1.4, state: WALL.rise });
        walls.push(w);
        const hit = new Set<string>();
        const t0 = scene.tick + 14 + j * 6;
        scene.at(t0, () => w.state(WALL.hold));
        scene.span(t0, t0 + C.directionTicks, (p) => {
          const at = lerp(from, to, p);
          w.move(at);
          for (const e of hostiles(dim, at, C.directionHalfWidth + 1, caster)) {
            const rel = sub(e.location, at);
            const along = rel.x * rt.x + rel.z * rt.z;
            const lat = rel.x * fwd.x + rel.z * fwd.z;
            if (Math.abs(along) > C.directionBand || Math.abs(lat) > C.directionHalfWidth || hit.has(e.id)) continue;
            hit.add(e.id);
            damage(e, C.directionDamage, caster);
            shove(e, rt, 1.1, 0.3);
            particle(dim, "dw6_seam", up(e.location, 1));
          }
        });
        scene.at(t0 + C.directionTicks, () => { w.state(WALL.sink); scene.after(20, () => scene.despawn(w)); });
      });
    },
    // IV Stillness: hostile movement is bound in place, then dragged slow
    () => {
      declare(3, center);
      let n = 0;
      for (const e of domain()) {
        restrain(scene, e, C.stillTicks);
        effect(e, "slowness", C.stillTicks + C.stillSlowTicks, C.stillSlowAmp);
        particle(dim, "dw6_blue", up(e.location, 1));
        if (n++ < 8) {
          const g = ground(e.location);
          const ci = scene.spawn("dw_circle", g, { size: 0.6, state: 1 });
          scene.after(8, () => ci.state(2));
          scene.after(C.stillTicks, () => ci.state(3));
          scene.after(C.stillTicks + 14, () => scene.despawn(ci));
        }
      }
    },
    // V Refuge: the allied zone is shielded and restored
    () => {
      refugeAt = ground(caster.isValid ? caster.location : c0);
      declare(4, refugeAt);
      refuge = scene.spawn("dw6_dome", refugeAt, { state: DOME.form });
      refugeOn = true;
      scene.after(24, () => refuge?.state(DOME.hold));
      for (const p of allies(dim, refugeAt, C.refugeRadius, caster)) heal(p, C.refugeHeal);
      ring(dim, "dw6_letters", up(refugeAt, 0.5), C.refugeRadius, 8);
    },
    // VI Sequence: each written structure strikes in turn
    () => {
      declare(5, center);
      edifices.forEach((ed, j) => {
        scene.after(6 + j * 5, () => {
          ed.a.state(ED.strike);
          scene.after(16, () => ed.a.state(ED.hold));
          const at = ed.at;
          if (ed.kind === COLUMN || ed.kind === GATE) particle(dim, "dw_pillar_burst", up(at, 0.3));
          else if (ed.kind === ARCH) ring(dim, "dw_glyph_fall", up(at, 6), 2.5, 5);
          else particle(dim, "dw6_rays", up(at, 0.3));
          particle(dim, "dw6_quake", up(at, 0.2));
          sound(dim, "dw6_strike", at, 0.7, 1.1 + j * 0.04);
          for (const e of hostiles(dim, at, C.sequenceRadius, caster)) { damage(e, C.sequenceDamage, caster); knockback(e, at, 0.6, 0.3); }
        });
      });
    },
    // VII Judgment: every surviving enemy is marked and the finale's telegraphs are raised
    () => {
      const es = domain();
      finalAt = ground(target && isAlive(target) && dist(target.location, center) <= C.domainRadius ? target.location : centroid(es, center));
      declare(6, finalAt);
      for (const e of es) { mark(e, 2); judged.add(e.id); }
      finalWarn = scene.spawn("telegraph", finalAt, { kind: 0, size: C.finalRadius, state: 4 });
      scene.after(40, () => finalWarn?.state(2));
      for (const e of es.slice(0, 6)) {
        const w = scene.spawn("telegraph", ground(e.location), { kind: 0, size: 1.6, state: 1 });
        scene.after(20, () => w.state(2));
        scene.follow(w, e, 0.05);
        judgedWarn.push(w);
      }
    },
  ];
  laws.forEach((fn, k) => scene.at(tLaw0 + k * tLawStep, fn));
  scene.every(40, () => {
    if (!refugeOn) return;
    for (const p of allies(dim, refugeAt, C.refugeRadius, caster)) heal(p, C.refugeRegen);
  }, tLaw0 + 4 * tLawStep + 40, tLaw0 + 4 * tLawStep + 600);
  scene.every(10, () => { if (refugeOn) dissolveProjectiles(scene, up(refugeAt, 2), C.refugeRadius); }, tLaw0 + 4 * tLawStep, tLaw0 + 4 * tLawStep + 600);

  // ================================================================== PHASE IV -- let it be written
  const tRise = tLaw0 + 7 * tLawStep + 26; // ~ 780
  scene.at(tRise, () => {
    tablets.forEach((t) => t.state(TAB.shed));
    sound(dim, "dw6_rise", P(0, 10, 10), 1.4);
  });
  scene.span(tRise, tRise + 40, (p) => tablets.forEach((t, k) => t.move(up(stations[k], 10 * p * p * (3 - 2 * p)))));
  scene.every(4, (e) => { const t = tablets[(e / 4) % 7]; if (t) particle(dim, "dw6_letters", t.loc); }, tRise, tRise + 40);
  scene.at(tRise + 40, () => tablets.forEach((t) => t.state(TAB.idle)));

  function spawnLine(kind: number, at: Vector3, size = 1): Actor {
    const a = scene.spawn("dw6_line", at, { yaw: faceCaster(at), kind, size, state: LINE.assemble });
    sound(dim, "dw6_form", at, 1.2, 1 + kind * 0.06);
    tablets.forEach((tab, k) => { if (k % 2 === kind % 2) line(dim, "dw6_stream", tab.loc, at, 4); });
    scene.after(30, () => a.state(LINE.hold));
    return a;
  }
  function descend(a: Actor, from: Vector3, to: Vector3, t0: number, t1: number): void {
    scene.span(t0, t1, (p) => a.move(lerp(from, to, p * p)));
  }

  // line 1: a sweeping line crosses the field from far to near
  const L1 = { form: tRise + 10, desc: tRise + 50 };
  let l1: Actor = new Actor(undefined, "");
  const l1Hi = P(0, 16, 15), l1Lo = up(ground(P(0, 16)), 1.6);
  scene.at(L1.form, () => { l1 = spawnLine(0, l1Hi); });
  const sweepWarn: Actor[] = [];
  scene.at(L1.desc - 20, () => { for (const b of [12, 4, -4]) sweepWarn.push(scene.spawn("telegraph", ground(P(0, b)), { kind: 0, size: 3, state: 1 })); });
  scene.at(L1.desc, () => descend(l1, l1Hi, l1Lo, L1.desc, L1.desc + 16));
  scene.at(L1.desc + 16, () => { l1.state(LINE.strike); sound(dim, "dw6_strike", l1Lo, 1.3); particle(dim, "dw6_quake", l1Lo); });
  {
    const hit = new Set<string>();
    scene.span(L1.desc + 16, L1.desc + 52, (p) => {
      const at = up(ground(P(0, 16 - 23 * p)), 1.6);
      l1.move(at);
      if (scene.tick % 3 === 0) line(dim, "dw6_seam", add(at, mul(rt, -C.sweepHalfLength)), add(at, mul(rt, C.sweepHalfLength)), 5);
      for (const e of hostiles(dim, at, C.sweepHalfLength + 1, caster)) {
        const rel = sub(e.location, at);
        if (hit.has(e.id) || Math.abs(rel.x * fwd.x + rel.z * fwd.z) > 1.6 || Math.abs(rel.x * rt.x + rel.z * rt.z) > C.sweepHalfLength) continue;
        hit.add(e.id);
        damage(e, C.sweepDamage, caster);
        shove(e, mul(fwd, -1), 0.9, 0.35);
      }
    });
  }
  scene.at(L1.desc + 52, () => sweepWarn.forEach((w) => { w.state(3); scene.after(8, () => scene.despawn(w)); }));
  scene.at(L1.desc + 54, () => { l1.state(LINE.unwrite); burst(dim, "dw6_letters", l1.loc, 3, 4); });
  scene.at(L1.desc + 74, () => scene.despawn(l1));

  // line 2: an expanding ring of text
  const L2 = { form: tRise + 20, desc: L1.desc + 50 };
  let l2: Actor = new Actor(undefined, "");
  const l2Hi = P(0, 2, 19), l2Lo = up(center, 1.2);
  let ringWarn: Actor | undefined;
  scene.at(L2.form, () => { l2 = spawnLine(1, l2Hi, 0.6); });
  scene.at(L2.desc - 20, () => { ringWarn = scene.spawn("telegraph", center, { kind: 0, size: C.ringMaxRadius, state: 1 }); });
  scene.at(L2.desc, () => descend(l2, l2Hi, l2Lo, L2.desc, L2.desc + 16));
  scene.at(L2.desc + 16, () => { l2.state(LINE.strike); sound(dim, "dw6_strike", center, 1.3, 0.85); particle(dim, "dw6_quake", up(center, 0.2)); });
  {
    const hit = new Set<string>();
    scene.span(L2.desc + 16, L2.desc + 46, (p) => {
      const rad = 2 + (C.ringMaxRadius - 2) * p;
      l2.size(rad / 7.5);
      if (scene.tick % 4 === 0) ring(dim, "dw6_seam", up(center, 0.6), rad, 10, scene.tick * 7);
      for (const e of hostiles(dim, center, rad + 1.5, caster)) {
        if (hit.has(e.id) || Math.abs(distXZ(e.location, center) - rad) > 1.6) continue;
        hit.add(e.id);
        damage(e, C.ringDamage, caster);
        knockback(e, center, 1.0, 0.4);
      }
    });
  }
  scene.at(L2.desc + 46, () => { if (ringWarn) { ringWarn.state(3); const w = ringWarn; scene.after(8, () => scene.despawn(w)); } });
  scene.at(L2.desc + 48, () => { l2.state(LINE.unwrite); });
  scene.at(L2.desc + 68, () => scene.despawn(l2));

  // line 3: a lattice whose letters fall as a checkerboard of columns
  const L3 = { form: tRise + 30, desc: L2.desc + 50 };
  let l3: Actor = new Actor(undefined, "");
  const l3Hi = P(0, 3, 21), l3Lo = P(0, 3, 9);
  scene.at(L3.form, () => { l3 = spawnLine(2, l3Hi); });
  scene.at(L3.desc, () => descend(l3, l3Hi, l3Lo, L3.desc, L3.desc + 16));
  const cell = (gx: number, gz: number): Vector3 => {
    const d = norm(flat(sub(c0, l3Lo)));
    return ground(add(add(l3Lo, mul(right(d), gx * 6)), mul(d, -gz * 6)));
  };
  const waves = [[[-1, -1], [1, -1], [0, 0], [-1, 1], [1, 1]], [[0, -1], [-1, 0], [1, 0], [0, 1]]];
  waves.forEach((cells, w) => {
    const tw = L3.desc + 20 + w * 22;
    const spots: Vector3[] = [];
    const warns: Actor[] = [];
    scene.at(tw - 20, () => {
      for (const [gx, gz] of cells) { const s = cell(gx, gz); spots.push(s); warns.push(scene.spawn("telegraph", s, { kind: 0, size: C.latticeRadius, state: 1 })); }
    });
    scene.at(tw - 6, () => {
      l3.state(LINE.strike);
      for (const s of spots) {
        const col = scene.spawn("dw_column", s, { kind: w === 0 ? 0 : 2, size: 1.5, state: 1 });
        scene.after(10, () => col.state(2));
        scene.after(22, () => col.state(3));
        scene.after(36, () => scene.despawn(col));
      }
      sound(dim, "dw6_strike", l3Lo, 1.3, 1.1 + w * 0.15);
    });
    scene.at(tw, () => {
      const hit = new Set<string>();
      warns.forEach((x) => { x.state(3); scene.after(8, () => scene.despawn(x)); });
      for (const s of spots) {
        particle(dim, "dw_ring", up(s, 0.2));
        particle(dim, "dw_pillar_burst", up(s, 0.3));
        for (const e of hostiles(dim, s, C.latticeRadius, caster)) {
          if (hit.has(e.id)) continue;
          hit.add(e.id);
          damage(e, C.latticeDamage, caster);
          knockback(e, s, 0.8, 0.5);
        }
      }
    });
  });
  scene.at(L3.desc + 66, () => l3.state(LINE.unwrite));
  scene.at(L3.desc + 86, () => scene.despawn(l3));

  // line 4: a converging spiral gathers the field toward its centre
  const L4 = { form: tRise + 40, desc: L3.desc + 62 };
  let l4: Actor = new Actor(undefined, "");
  const l4Hi = P(0, 0, 23), l4Lo = up(center, 1.4);
  let spiralWarn: Actor | undefined;
  scene.at(L4.form, () => { l4 = spawnLine(3, l4Hi, 1.8); });
  scene.at(L4.desc - 20, () => { spiralWarn = scene.spawn("telegraph", center, { kind: 0, size: 15, state: 1 }); });
  scene.at(L4.desc, () => descend(l4, l4Hi, l4Lo, L4.desc, L4.desc + 16));
  scene.at(L4.desc + 16, () => { l4.state(LINE.strike); sound(dim, "dw6_strike", center, 1.2, 0.75); });
  scene.span(L4.desc + 16, L4.desc + 56, (p, el) => {
    const rad = 15 * (1 - p) + 1;
    l4.size(rad / 8.6);
    if (el % 5 === 0) {
      ring(dim, "dw6_stream", up(center, 0.8), rad, 8, el * 21);
      for (const e of hostiles(dim, center, rad + 1, caster)) {
        shove(e, sub(center, e.location), C.spiralPull, 0.1);
        if (el % 10 === 0) damage(e, C.spiralTickDamage, caster);
      }
    }
  });
  scene.at(L4.desc + 56, () => {
    l4.state(LINE.strike);
    spiralWarn?.state(3);
    particle(dim, "dw6_flare", up(center, 1.5));
    particle(dim, "dw6_quake", up(center, 0.3));
    for (const e of hostiles(dim, center, 3.5, caster)) damage(e, C.spiralFinalDamage, caster);
  });
  scene.at(L4.desc + 64, () => { if (spiralWarn) scene.despawn(spiralWarn); l4.state(LINE.unwrite); });
  scene.at(L4.desc + 84, () => scene.despawn(l4));

  // the final line: the immense white-gold formation strikes the judged region
  const tFinal = L4.desc + 76; // impact tick
  let form: Actor = new Actor(undefined, "");
  let formHi = up(finalAt, 26);
  scene.at(tRise + 60, () => {
    formHi = up(finalAt, 26);
    form = spawnLine(4, formHi, 1.0);
    sound(dim, "dw6_form", formHi, 1.6, 0.7);
  });
  scene.at(tFinal - 40, () => { if (!finalWarn?.valid) finalWarn = scene.spawn("telegraph", finalAt, { kind: 0, size: C.finalRadius, state: 4 }); else finalWarn.state(1); });
  scene.at(tFinal - 24, () => {
    const from = formHi, to = up(finalAt, 1.2);
    descend(form, from, to, tFinal - 24, tFinal);
    sound(dim, "dw6_finale", finalAt, 2.0);
  });
  scene.every(3, () => ring(dim, "dw6_ink", up(finalAt, 0.4), C.finalRadius, 6, scene.tick * 9), tFinal - 24, tFinal);
  scene.at(tFinal, () => {
    form.state(LINE.strike);
    finalWarn?.state(3);
    for (const w of judgedWarn) w.state(3);
    particle(dim, "dw6_flare", up(finalAt, 2));
    particle(dim, "dw6_quake", up(finalAt, 0.3));
    particle(dim, "fx_shock", up(finalAt, 0.4));
    burst(dim, "dw6_rays", up(finalAt, 0.5), C.finalRadius * 0.6, 6);
    ring(dim, "dw6_dust", up(finalAt, 0.4), C.finalRadius * 0.7, 8);
    for (const e of hostiles(dim, finalAt, C.finalRadius, caster)) {
      damage(e, C.finalDamage + (judged.has(e.id) ? C.judgedBonus : 0), caster);
      knockback(e, finalAt, C.finalKnockback, 0.7);
    }
    for (const m of marks.values()) { m.a.state(3); const a = m.a; scene.after(8, () => scene.despawn(a)); }
  });
  scene.at(tFinal + 10, () => { if (finalWarn) scene.despawn(finalWarn); judgedWarn.forEach((w) => scene.despawn(w)); });
  scene.at(tFinal + 26, () => { form.state(LINE.unwrite); burst(dim, "dw6_letters", up(finalAt, 3), 5, 8); });
  scene.at(tFinal + 46, () => scene.despawn(form));

  // ================================================================== PHASE V -- the final amen
  const tPhase5 = tFinal + 20;
  scene.at(tPhase5, () => {
    refugeOn = false;
    refuge?.state(DOME.fade);
    for (const w of walls) if (w.valid) w.state(WALL.sink);
    tb.clearAll();
    tb.place(up(bookAt, 1), LIGHT);
    sound(dim, "dw6_unwrite", center, 1.4);
  });
  scene.at(tPhase5 + 20, () => { if (refuge) scene.despawn(refuge); walls.forEach((w) => scene.despawn(w)); });
  scene.at(tPhase5 + 2, () => {
    edifices.forEach((ed, j) => {
      scene.after(j * 4, () => ed.a.state(ED.unwrite));
      scene.after(j * 4 + 40, () => scene.despawn(ed.a));
      // the structure streams back to the codex as a line of floating text
      const from = up(ed.at, 4), mid = up(lerp(ed.at, bookAt, 0.5), 9);
      scene.span(scene.tick + j * 4 + 14, scene.tick + j * 4 + 44, (p) => {
        particle(dim, "dw6_stream", bezier(from, mid, up(bookAt, 1), p));
      });
    });
  });
  // the tablets return from the sky and re-form the page
  scene.at(tPhase5 + 6, () => tablets.forEach((t) => t.state(TAB.ret)));
  scene.span(tPhase5 + 6, tPhase5 + 34, (p) => {
    tablets.forEach((t, k) => {
      const from = up(stations[k], 10);
      const to = pagePt(ruleA(k), 44, 0.3);
      t.move(bezier(from, up(lerp(from, to, 0.5), 5), to, p * p * (3 - 2 * p)), pageYaw);
    });
  });
  const tReform = tPhase5 + 32;
  scene.at(tReform, () => {
    page = scene.spawn("dw6_page", pageO, { yaw: pageYaw, state: PAGE.reform });
    sound(dim, "dw6_page", pagePt(0, 44), 0.9, 1.2);
  });
  scene.at(tReform + 6, () => tablets.forEach((t) => scene.despawn(t)));
  const tFold = tReform + 30;
  scene.at(tFold, () => page.state(PAGE.fold));
  [16, 36, 56, 74].forEach((d, k) => scene.at(tFold + d, () => {
    sound(dim, "dw6_fold", page.loc, 1.2, 1 + k * 0.08);
    burst(dim, "dw6_ink", pagePt(-30 + k * 7, 44 - k * 9, 0.5), 2, 3);
  }));
  scene.at(tFold + 60, () => { book.state(BOOK.gather).skin(0); burst(dim, "dw6_letters", up(bookAt, 1.5), 1.5, 4); }); // inscriptions return
  scene.at(tPhase5 + 40, () => boundary.state(BOUND.unwrite));
  scene.at(tPhase5 + 70, () => scene.despawn(boundary));
  const tSlide = tFold + 100;
  scene.span(tSlide, tSlide + 20, (p) => page.move(lerp(pageO, up(bookAt, 0.8), p * p * (3 - 2 * p)), pageYaw));
  scene.at(tSlide + 20, () => { page.state(PAGE.slip); particle(dim, "dw6_flare", up(bookAt, 1)); });
  scene.at(tSlide + 36, () => scene.despawn(page));
  scene.at(tSlide + 30, () => { book.state(BOOK.close); sound(dim, "dw6_close", bookAt, 1.1); });
  scene.at(tSlide + 40, () => sound(dim, "dw6_amen", bookAt, 1.2));
  scene.at(tSlide + 76, () => { burst(dim, "dw6_letters", up(bookAt, 1), 1.2, 6); particle(dim, "dw6_bell", up(bookAt, 1)); });
  scene.at(tSlide + 80, () => scene.despawn(book));
  scene.endAt(tSlide + secs(4.3));
});
