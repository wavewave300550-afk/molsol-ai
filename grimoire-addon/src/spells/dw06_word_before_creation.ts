import { Entity, Vector3 } from "@minecraft/server";
import { DW06 as C } from "../config/dw06";
import { CONFIG } from "../config/global";
import { defineSpell } from "../core/registry";
import { addWard, damage, dissolveProjectiles, effect, heal, knockback, restrain, shove } from "../lib/combat";
import { particle, sound } from "../lib/fx";
import { Actor } from "../lib/scene";
import { allies, focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { LIGHT, blocksFor } from "../lib/tempblocks";
import { add, angleDelta, bezier, clamp, dist, distXZ, easeIn, easeOut, flat, lerp, mul, norm, right, smooth, sub, up, yawOf } from "../lib/vec";

// ---- animation states (mirror tools/assets/dw6_*.py; lengths in ticks)
const BOOK = { arrive: 1, open: 2, unbind: 3, layered: 4, gather: 5, close: 6, vanish: 7 }; // arrive 56, unbind 40, gather 30, close 32, vanish 30
const PAGE = { manifest: 1, idle: 2, split: 3, reform: 4, fold: 5, slip: 6 };        // manifest 50, split 24, reform 22, fold 52, slip 16
const GLYPH = { draw: 1, fall: 2, land: 3 };                                          // draw 20, fall 18, land 10
const ED = { assemble: 1, hold: 2, swing: 3, strike: 4, unwrite: 5 };                 // assemble 32, swing 28 (sweeps at 21), strike 16, unwrite 40
const WALL = { rise: 1, hold: 2, sink: 3 };                                           // rise 20, sink 20
const DOME = { form: 1, hold: 2, fade: 3 };                                           // form 24, fade 20
const BOUND = { inscribe: 1, hold: 2, unwrite: 3 };                                   // inscribe 40, unwrite 30
const TAB = { form: 1, idle: 2, declare: 3, shed: 4, ret: 5 };                        // form 20, declare 32, shed 28, return 20
const LINE = { assemble: 1, hold: 2, strike: 3, unwrite: 4 };                         // assemble 30, strike 12, unwrite 20
// shared actors (dw_common / a_fx_common)
const TEL = { warn: 1, hold: 2, flash: 3, slow: 4 };
const LIGHTCOL = { descend: 1, hold: 2, dissolve: 3 };
const CIRCLE = { form: 1, hold: 2, fade: 3 };
const MARK = { appear: 1, burst: 3 };

const DEG = Math.PI / 180;
const UPV: Vector3 = { x: 0, y: 1, z: 0 };
const EYE = 1.62;
const PAGE_U = 2.4 / 16;            // page model unit -> blocks (dw6_codex PAGE_SCALE)
const PAGE_TILT = 7 * DEG;          // dw6_codex PAGE_TILT
const ED_U = 2 / 16;                // edifice model unit -> blocks at size 1
// structure kinds: 0 column, 1 arch, 2 bridge, 3 gate, 4 platform, 5 celestial
const COLUMN = 0, ARCH = 1, BRIDGE = 2, GATE = 3, PLATFORM = 4, CELESTIAL = 5;
/** Full height (blocks, size 1) of each structure kind, crowning letter included. */
const ED_H = [11.0, 11.4, 7.0, 13.9, 6.0, 11.0];

// ---- staging (caster's eye on a phone: ~60 degrees vertical, looking ~12 degrees down, so the view reaches only
// ~18 degrees above the horizon: the temple stays below ~12 degrees, page / tablets / lines between 0 and 17)
const STAGE_MIN = 14, STAGE_MAX = 20;   // the domain centre is kept this far ahead of the caster
const PAGE_BACK = 26, PAGE_LIFT = 0.6;  // the giant page hangs beyond the domain, its lower edge this high
const BOOK_HOVER = 1.2, BOOK_START = 0.8, BOOK_LECTERN = 1.0, BOOK_FINAL = 1.0;
const TAB_LIFT = 3.4, TAB_RISE = 15, TAB_BACK = 6;   // Phase IV: the tablets rise out of the view into the sky
const FX_CAP = 88;

// ---- timeline (ticks)
const T_OPEN = 56, T_UNBIND = 64, T_SEAM = 84, T_LAYERED = 104, T_GLIDE = 100, GLIDE = 46;
const T_WRITE0 = 140;
const WRITE_AT = [0, 26, 50, 72, 92, 110, 126, 141, 155, 168];   // accelerando
const DRAW = 20, FALL = 18;
const T_SPLIT = 384, T_TAB = T_SPLIT + 8, TAB_FLY = 28;
const T_LAW0 = 444, LAW_STEP = 22;
const T_RISE = T_LAW0 + 7 * LAW_STEP;          // 598
const T_FINAL = T_RISE + 238;                  // 836: the white-gold formation strikes
const T_UNW = T_FINAL + 14;
const T_TABRET = T_FINAL + 12, TAB_RET = 24;
const T_REFORM = T_TABRET + TAB_RET - 2;
const T_FOLD = T_REFORM + 22;
const T_FLY = T_FOLD + 50, FLY = 20;
const T_SLIP = T_FLY + FLY;
const T_CLOSE = T_SLIP + 2;
const T_VANISH = T_CLOSE + 36;
const T_END = T_VANISH + 40;                   // ~52 s

interface Edifice { a: Actor; kind: number; at: Vector3; yaw: number; size: number; cells: Vector3[]; h: number; alive: boolean }
/** u = blocks right of the domain centre, v = blocks beyond it; elev = highest angle (deg) its top may reach from the
 *  caster's eye; (a, b) = where its letter is written on the page (page units). */
interface Slot { kind: number; u: number; v: number; elev: number; cap: number; seek?: boolean; a: number; b: number }

/** Ten letters -> a written temple 12-26 blocks ahead: tall pieces frame an open centre (the page / tablets stay
 *  visible above it), the bridge closes the back, the platforms guard the near flanks. */
const PLAN: Slot[] = [
  { kind: COLUMN, u: -5.0, v: 0.5, elev: 13, cap: 0.7, seek: true, a: -14, b: 34 },
  { kind: COLUMN, u: 5.0, v: 0.5, elev: 13, cap: 0.7, seek: true, a: 26, b: 34 },
  { kind: ARCH, u: -9.8, v: 4.0, elev: 12, cap: 0.75, a: -34, b: 34 },
  { kind: ARCH, u: 9.8, v: 4.0, elev: 12, cap: 0.75, a: 46, b: 34 },
  { kind: GATE, u: -9.0, v: 10.5, elev: 12, cap: 0.75, a: 6, b: 34 },
  { kind: BRIDGE, u: 0, v: 13.0, elev: 7, cap: 0.7, a: 6, b: 63 },
  { kind: PLATFORM, u: -8.8, v: -3.6, elev: 10, cap: 0.55, a: -34, b: 63 },
  { kind: PLATFORM, u: 8.8, v: -3.6, elev: 10, cap: 0.55, a: 46, b: 63 },
  { kind: CELESTIAL, u: 8.0, v: 10.0, elev: 11, cap: 0.75, seek: true, a: 26, b: 63 },
  { kind: COLUMN, u: 13.0, v: 8.0, elev: 12, cap: 0.75, seek: true, a: -14, b: 63 },
];

/** Deterministic hash noise in [0, 1). */
const rnd = (k: number): number => { const x = Math.sin(k * 12.9898 + 78.233) * 43758.5453; return x - Math.floor(x); };

/**
 * DW06 - The Word Before Creation (Extra Ultimate, ~52 s).  Staged for the caster's own eyes: a clear zone around
 * the caster, the written temple 10-26 blocks ahead, the giant page / tablets hanging beyond the domain.
 * I   The great codex rises out of its seal ahead of the caster, opens, its pages lift into layers; the inscriptions
 *     fly off into the far sky where a vast ivory page unfolds; the codex glides back beneath it like a lectern.
 * II  Ten golden letters are written on the page, stroke by stroke; each falls out as 3D and lands as architecture.
 * III The page parts into seven tablets that take station in a wide arc; each declares its own local law.
 * IV  The tablets shed their letters and rise out of sight; the letters assemble into lines of text over the field
 *     that descend one by one (sweep, ring, lattice, spiral); the last becomes the white-gold formation that gathers
 *     everything written and strikes the judged region.
 * V   Everything is unwritten: the temple streams back as text into the codex as it returns to the centre, the
 *     tablets re-form the page, the page folds down to a leaf and slips inside, the codex closes and dissolves.
 */
export default defineSpell("dw06", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center: aimC0, target } = focus(caster, aim, C.focusSnap);
  const c0 = { ...caster.location };
  const aimC = groundBelow(dim, aimC0);
  let fwd = norm(flat(sub(aimC, c0)));
  if (distXZ(aimC, c0) < 3) fwd = norm(flat(aim.forward));
  const rt = right(fwd);
  const tb = blocksFor(scene);
  const ground = (p: Vector3): Vector3 => groundBelow(dim, up(p, 3), 12);
  const Ds = clamp(distXZ(aimC, c0), STAGE_MIN, STAGE_MAX);
  /** Caster frame: f blocks ahead, r blocks to the right, at height y. */
  const at = (f: number, r: number, y = c0.y): Vector3 => ({ x: c0.x + fwd.x * f + rt.x * r, y, z: c0.z + fwd.z * f + rt.z * r });
  const G = (f: number, r: number, h = 0): Vector3 => up(ground(at(f, r)), h);
  const center = G(Ds, 0);
  const yb = Math.max(c0.y, center.y);
  const SKY = (f: number, r: number, h: number): Vector3 => at(f, r, yb + h);
  const faceOrigin = (p: Vector3): number => yawOf(sub(c0, p));
  const casterPos = (): Vector3 => (caster.isValid ? caster.location : c0);
  const domain = (): Entity[] => hostiles(dim, center, C.domainRadius, caster);
  const isAlly = (e: Entity): boolean => e.typeId === "minecraft:player" && (e.id === caster.id || !CONFIG.targeting.pvp);
  const lateral = (p: Vector3): number => (p.x - c0.x) * rt.x + (p.z - c0.z) * rt.z;
  const depth = (p: Vector3): number => (p.x - c0.x) * fwd.x + (p.z - c0.z) * fwd.z;
  /** A point kept at least minD blocks (horizontally) from where the caster stood. */
  const awayFrom = (p: Vector3, minD: number): Vector3 => {
    const d = distXZ(p, c0);
    if (d >= minD) return p;
    const dir = d < 0.5 ? fwd : norm(flat(sub(p, c0)));
    return ground(add(c0, mul(dir, minD)));
  };
  const centroid = (es: Entity[], fallback: Vector3): Vector3 => {
    if (!es.length) return fallback;
    let s = { x: 0, y: 0, z: 0 };
    for (const e of es) s = add(s, e.location);
    return mul(s, 1 / es.length);
  };
  /** Where the enemy stands now: their centroid, and how far ahead the nearest of them is (the stage when none). */
  const enemyFront = (): { E: Vector3; near: number } => {
    const es = domain();
    if (!es.length) return { E: G(Ds + 2, 0), near: Ds };
    return { E: ground(centroid(es, center)), near: Math.min(...es.map((e) => depth(e.location))) };
  };
  /** A point on the line from the caster toward p, pulled to a distance within [lo, hi]. */
  const clampDist = (p: Vector3, lo: number, hi: number): Vector3 => {
    const d = distXZ(p, c0);
    const dir = d < 0.5 ? fwd : norm(flat(sub(p, c0)));
    return ground(add(c0, mul(dir, clamp(d, lo, hi))));
  };

  // ---------------------------------------------------------------- effects (own per-tick budget)
  let fxT = -1, fxN = 0;
  const fx = (id: string, p: Vector3): void => {
    if (scene.tick !== fxT) { fxT = scene.tick; fxN = 0; }
    if (fxN >= FX_CAP) return;
    fxN++;
    particle(dim, id, p);
  };
  const fxLine = (id: string, a: Vector3, b: Vector3, n: number): void => {
    for (let i = 0; i < n; i++) fx(id, lerp(a, b, n === 1 ? 0.5 : i / (n - 1)));
  };
  const fxRing = (id: string, c: Vector3, r: number, n: number, phase = 0): void => {
    for (let i = 0; i < n; i++) {
      const a = (phase + (360 * i) / n) * DEG;
      fx(id, { x: c.x + Math.cos(a) * r, y: c.y, z: c.z + Math.sin(a) * r });
    }
  };
  const fxBurst = (id: string, c: Vector3, r: number, n: number): void => {
    for (let i = 0; i < n; i++) {
      const y = 1 - (2 * (i + 0.5)) / n, rr = Math.sqrt(1 - y * y) * r, a = i * 2.39996;
      fx(id, { x: c.x + Math.cos(a) * rr, y: c.y + y * r, z: c.z + Math.sin(a) * rr });
    }
  };
  /** A flowing ribbon of particles along a curve: n particles whose positions advance with time. */
  const fxFlow = (id: string, path: (q: number) => Vector3, e: number, n: number, speed = 0.05): void => {
    for (let j = 0; j < n; j++) fx(id, path((e * speed + j / n) % 1));
  };
  const snd = (id: string, p: Vector3, vol = 1, pitch = 1): void => sound(dim, id, p, vol, pitch);

  // ---------------------------------------------------------------- shared state
  const edifices: Edifice[] = [];
  const tablets: Actor[] = [];
  const hovering: Actor[] = [];          // lines of text waiting in the sky
  let page: Actor | undefined;
  let pageGlitter = false;
  let tabletsShown = true;
  let boundaryOn = false;
  let refugeOn = false;
  let refugeAt = c0;
  let finalAt = awayFrom(center, C.finalMinDist);
  let stD = Ds - 2;                       // depth of the Station line (Law II)

  // the giant page: beyond the domain, its face toward the caster's eye
  const Lp = clamp(Ds + PAGE_BACK, 38, 46);
  const pageO = SKY(Lp, 0, PAGE_LIFT);
  const pd = norm(flat(sub(c0, pageO)));
  const pageYaw = yawOf(pd);
  const pr = right(pd);
  const pageUp = add(mul(UPV, Math.cos(PAGE_TILT)), mul(pd, -Math.sin(PAGE_TILT)));
  const pageN = add(mul(pd, Math.cos(PAGE_TILT)), mul(UPV, Math.sin(PAGE_TILT)));
  /** a = page units from the viewer's left to right (-60..60), b = page units up (0..88), off = toward the viewer. */
  const pagePt = (a: number, b: number, off = 0): Vector3 =>
    add(add(add(pageO, mul(pr, -a * PAGE_U)), mul(pageUp, b * PAGE_U)), mul(pageN, off));

  // the domain boundary (actor faces the caster: its bb +Z is the far side, bb +X the caster's left)
  const BR = 18.75;
  const ringPt = (bbDeg: number, h = 0.4): Vector3 => {
    const a = bbDeg * DEG;
    return up(add(add(center, mul(rt, -Math.cos(a) * BR)), mul(fwd, Math.sin(a) * BR)), h);
  };

  // the great codex
  const b1 = G(Ds - 1, 0, BOOK_HOVER);
  const b2 = SKY(Lp - 3.2, 0, 0.9);
  const bF = G(Ds + 0.5, 0, 1.6);
  let bookAt = b1;
  let bookShows = true;

  // ================================================================== ambient director (runs first every tick)
  // A continuous layer of living script over the whole spell: motes and drifting letters fill the domain, every
  // written thing sheds letters and glints.  It keeps to ~40 spawns a tick so the beats' accents always fit.
  scene.every(1, () => {
    const t = scene.tick;
    const lively = t >= T_WRITE0 && t < T_UNW;
    // motes drifting over the whole domain, and letters adrift higher up
    const nm = t < T_WRITE0 ? 9 : lively ? 13 : 8;
    for (let i = 0; i < nm; i++) {
      const k = t * 13 + i * 3.7;
      const a = rnd(k) * 2 * Math.PI, r = Math.sqrt(rnd(k + 1.3)) * C.domainRadius;
      const p = { x: center.x + Math.cos(a) * r, y: center.y + 0.5 + rnd(k + 2.1) * 7, z: center.z + Math.sin(a) * r };
      if (distXZ(p, c0) > 3) fx("dw6_motes", p);
    }
    if (lively) {
      for (let i = 0; i < 6; i++) {
        const k = t * 5.3 + i * 1.9;
        fx("dw6_script", { x: center.x + (rnd(k) - 0.5) * 28, y: center.y + 4 + rnd(k + 0.7) * 6, z: center.z + (rnd(k + 1.4) - 0.2) * 22 });
      }
    }
    // the boundary breathes letters
    if (boundaryOn) {
      fx("dw6_script", ringPt(rnd(t * 3.1) * 360, 0.3));
      if (lively) fx("dw6_script", ringPt(rnd(t * 4.3 + 0.5) * 360, 0.3));
      if (t % 3 === 0) fx("dw6_glint", ringPt(rnd(t * 5.7) * 360, 1.0));
    }
    // the written architecture sheds script from its whole height
    for (let j = 0; j < edifices.length; j++) {
      const ed = edifices[j];
      if (!ed.alive) continue;
      const hgt = ED_H[ed.kind] * ed.size, k = t * 1.7 + j * 9.1, w = 2.6 * ed.size;
      fx("dw6_script", { x: ed.at.x + (rnd(k) - 0.5) * w, y: ed.at.y + 0.3 + rnd(k + 0.4) * hgt, z: ed.at.z + (rnd(k + 0.8) - 0.5) * w });
      if ((t + j) % 2 === 0) fx("dw6_motes", { x: ed.at.x + (rnd(k + 3) - 0.5) * w * 1.6, y: ed.at.y + 0.4, z: ed.at.z + (rnd(k + 3.5) - 0.5) * w * 1.6 });
      if ((t + j * 3) % 7 === 0) fx("dw6_glint", up(ed.at, hgt * (0.55 + rnd(k + 2) * 0.4)));
    }
    // the page and the tablets glitter
    if (pageGlitter && page && page.valid) {
      for (let i = 0; i < 3; i++) {
        const k = t * 2.3 + i * 0.37;
        fx(i ? "dw6_glint" : "dw6_script", pagePt(-58 + rnd(k) * 116, 3 + rnd(k + 0.5) * 82, 0.4));
      }
    }
    for (let k = 0; k < tablets.length && tabletsShown; k++) {
      const tab = tablets[k];
      if (!tab.valid) continue;
      fx((t + k) % 3 ? "dw6_script" : "dw6_glint", add(tab.loc, { x: (rnd(t + k) - 0.5) * 4, y: 1 + rnd(t * 1.1 + k) * 7, z: (rnd(t * 0.7 + k) - 0.5) * 3 }));
    }
    // the codex
    if (bookShows) {
      for (let i = 0; i < 2; i++) {
        const k = t * 1.9 + i * 0.41;
        fx((t + i) % 5 ? "dw6_script" : "dw6_glint", add(bookAt, { x: (rnd(k) - 0.5) * 4.5, y: 0.2 + rnd(k + 0.3) * 3.5, z: (rnd(k + 0.6) - 0.5) * 4 }));
      }
    }
    // lines of text hanging over the field
    for (let j = 0; j < hovering.length; j++) {
      const ln = hovering[j];
      if (ln.valid) fx((t + j) % 3 ? "dw6_glint" : "dw6_stream", add(ln.loc, { x: (rnd(t + j * 3) - 0.5) * 10, y: (rnd(t * 1.3 + j) - 0.5) * 1.5, z: (rnd(t * 0.9 + j) - 0.5) * 10 }));
    }
    // the refuge: a curtain of rising letters, motes and feathers at its fence, around the caster's sides and back
    // (the 70 degrees in front of them stay clear)
    if (refugeOn && t % 2 === 0) {
      const a = (35 + rnd(t * 0.77) * 290) * DEG;           // measured from straight ahead
      const dir = add(mul(fwd, Math.cos(a)), mul(rt, Math.sin(a)));
      const p = add(refugeAt, add(mul(dir, 6.4), { x: 0, y: 0.3 + rnd(t + 1) * 1.6, z: 0 }));
      fx(t % 6 === 0 ? "dw6_feather" : t % 4 === 0 ? "dw6_letters" : "dw6_motes", p);
    }
  }, 0, T_END - 4);
  // a soft choir bed under the long middle of the spell (it never goes silent)
  scene.every(90, () => snd("dw6_bed", center, 0.85), T_WRITE0 - 20, T_FINAL - 60);

  // ------------------------------------------------------------------ marks
  const marks = new Map<string, { e: Entity; a: Actor }>();
  function mark(e: Entity, skin = 0): void {
    let m = marks.get(e.id);
    if (!m || !m.a.valid) {
      let live = 0;
      for (const x of marks.values()) if (x.a.valid) live++;
      if (live >= C.maxMarks || !isAlive(e)) return;
      const a = scene.spawn("dw_mark", up(e.location, 2.4), { state: MARK.appear });
      scene.follow(a, e, 2.4);
      m = { e, a };
      marks.set(e.id, m);
      fx("dw6_quill", up(e.location, 2.4));
    }
    m.a.skin(skin);
  }

  // ================================================================== PHASE I -- the silence before all things
  const book = scene.spawn("dw6_book", b1, { yaw: faceOrigin(b1), state: BOOK.arrive, size: BOOK_START });
  snd("dw6_silence", c0, 1.0);
  scene.at(4, () => snd("dw6_book", b1, 1.1));
  tb.place(G(Ds - 1, 0, 0.5), LIGHT);
  const boundary = scene.spawn("dw6_boundary", up(center, 0.05), { yaw: faceOrigin(center), state: BOUND.inscribe });
  scene.at(40, () => { boundary.state(BOUND.hold); boundaryOn = true; });
  // the inscription is written from the far point of the ring around both sides toward the caster
  scene.every(1, (e) => {
    const off = clamp((e / 20 - 0.1) / 0.36, 0, 4) * 45;
    for (const s of [-1, 1]) {
      fx("dw6_quill", ringPt(90 + s * off, 0.5));
      fx("dw6_script", ringPt(90 + s * (off - 8), 0.3));
    }
  }, 2, 34);
  // the codex rises out of its seal: letters spiral up around it
  scene.every(1, (e) => {
    for (const ph of [0, 180]) {
      const a = (e * 19 + ph) * DEG;
      fx("dw6_stream", add(b1, { x: Math.cos(a) * 2.6, y: -1.2 + (e / T_OPEN) * 2.8, z: Math.sin(a) * 2.6 }));
    }
    if (e % 3 === 0) fx("dw6_motes", up(b1, -1.2));
    if (e % 8 === 0) fx("dw6_halo", up(b1, -1.0));
  }, 4, T_OPEN);
  scene.at(12, () => domain().slice(0, C.maxMarks).forEach((e, i) => scene.after(i * 3, () => mark(e))));
  scene.at(T_OPEN, () => { book.state(BOOK.open); fx("dw6_halo", up(b1, 0.6)); });
  scene.at(T_UNBIND, () => {
    book.state(BOOK.unbind).skin(1); // the inscriptions vanish from the pages...
    snd("dw6_unbind", b1, 1.1);
    fxBurst("dw6_letters", up(b1, 1.0), 1.6, 6);
  });
  scene.at(T_LAYERED, () => book.state(BOOK.layered));
  // ...and fly off as a ribbon of letters into the far sky, where the page will open
  const pageMid = pagePt(6, 40, 0.5);
  const inkPath = (q: number): Vector3 => bezier(up(b1, 1.2), up(lerp(b1, pageMid, 0.35), 9), pageMid, q);
  scene.every(1, (e) => {
    fxFlow("dw6_stream", inkPath, e, 5, 0.045);
    if (e % 3 === 0) fx("dw6_trail", inkPath((e * 0.045) % 1));
    if (e < 36 && e % 2 === 0) fx("dw6_letters", add(b1, { x: (rnd(e) - 0.5) * 4.5, y: 0.6, z: (rnd(e + 0.5) - 0.5) * 3 }));
  }, T_UNBIND, T_SEAM + 14);
  scene.at(T_SEAM, () => {
    page = scene.spawn("dw6_page", pageO, { yaw: pageYaw, state: PAGE.manifest });
    snd("dw6_page", pagePt(0, 44), 1.8);
    fxLine("dw6_trail", pagePt(0, 0, 0.4), pagePt(0, 88, 0.4), 12);
    fx("dw6_flare", pagePt(0, 44, 1));
    fx("dw6_bell", pagePt(0, 44, 1));
  });
  // the seam of light opens sideways into the page: its edges spark as they travel
  scene.every(1, (e) => {
    const w = 60 * clamp((e - 12) / 22, 0, 1);
    for (const s of [-1, 1]) {
      fx("dw6_glint", pagePt(s * w, 4 + rnd(e * 1.3 + s) * 80, 0.4));
      fx("dw6_quill", pagePt(s * w, 4 + rnd(e * 2.1 + s) * 80, 0.4));
    }
    fx("dw6_seam", pagePt((rnd(e) - 0.5) * 2 * w, 2 + rnd(e + 3) * 84, 0.5));
  }, T_SEAM + 4, T_SEAM + 44);
  scene.at(T_SEAM + 50, () => { page?.state(PAGE.idle); pageGlitter = true; });
  // the codex glides back beneath the page, where it will serve as the lectern of the writing
  scene.at(T_GLIDE, () => snd("dw6_glide", b1, 1.3));
  scene.span(T_GLIDE, T_GLIDE + GLIDE, (p) => {
    const q = smooth(p);
    bookAt = bezier(b1, up(lerp(b1, b2, 0.5), 5), b2, q);
    book.move(bookAt, faceOrigin(bookAt));
    if (scene.tick % 2 === 0) book.size(BOOK_START + (BOOK_LECTERN - BOOK_START) * q);
    fx("dw6_stream", up(bookAt, -0.6));
    fx("dw6_script", add(bookAt, { x: (rnd(scene.tick) - 0.5) * 4, y: rnd(scene.tick + 0.5) * 2, z: (rnd(scene.tick + 0.9) - 0.5) * 4 }));
    if (scene.tick % 3 === 0) fx("dw6_trail", up(bookAt, 0.8));
  });

  // ================================================================== PHASE II -- the first utterance
  const claimed = new Set<string>();
  const cover: { p: Vector3; r: number }[] = [];
  addWard({
    scene, factor: C.coverFactor,
    protects: (e) => isAlly(e) && cover.some((z) => distXZ(z.p, e.location) <= z.r),
  });

  /** Largest size (<= cap) at which a structure at p stays below elevDeg as seen from the caster's eye. */
  function fitSize(kind: number, p: Vector3, elevDeg: number, cap: number): number {
    const d = Math.max(6, distXZ(p, c0));
    return clamp((c0.y + EYE + d * Math.tan(elevDeg * DEG) - p.y) / ED_H[kind], 0.42, cap);
  }

  function landingSpot(i: number): Vector3 {
    const s = PLAN[i];
    let p = G(Ds + s.v, s.u);
    if (s.seek) {
      const near = hostiles(dim, p, C.seekRadius, caster).filter((e) => !claimed.has(e.id)
        && distXZ(e.location, c0) >= C.seekMinDist && dist(e.location, center) <= C.domainRadius
        && edifices.every((ed) => distXZ(ed.at, e.location) >= 4.5));
      if (near.length) { claimed.add(near[0].id); p = ground(near[0].location); }
    }
    return p;
  }

  function cellsFor(kind: number, p: Vector3, size: number): Vector3[] {
    const r = right(norm(flat(sub(c0, p))));
    const offs = kind === COLUMN ? [0]
      : kind === ARCH ? [-22 * ED_U * size, 22 * ED_U * size]
        : kind === GATE ? [-1, 1].flatMap((s) => [s * (27 * ED_U * size - 0.5), s * (27 * ED_U * size + 0.5)]) : [];
    return offs.map((o) => add(p, mul(r, o)));
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

  function impact(kind: number, p: Vector3, size: number, cellPts: Vector3[]): void {
    const spots = kind === ARCH ? cellPts : [p];
    fx("dw6_quake", up(p, 0.2));
    fx("dw6_wave", up(p, 0.15));
    fx("dw6_dust", up(p, 0.4));
    fx("dw6_flare", up(p, 2));
    fx("dw6_pillar", up(p, 6));
    fx("dw6_fountain", up(p, 0.3));
    fxBurst("dw6_ink", up(p, 2.5), 2.2, 6);
    fxRing("dw6_letters", up(p, 0.4), 2.6 * size + 0.8, 5, p.x * 31);
    snd("dw6_land", p, 1.4, 1 - kind * 0.03);
    const hit = new Set<string>();
    // the shock of the landing runs out along the ground (the wide ring of light)
    scene.after(3, () => {
      for (const e of hostiles(dim, p, C.landShockRadius, caster)) {
        if (distXZ(e.location, p) <= C.landRadius[kind]) continue;
        damage(e, C.landShockDamage, caster);
        knockback(e, p, 0.5, 0.2);
      }
    });
    if (C.landDamage[kind] <= 0 && kind !== PLATFORM) return;
    for (const s of spots) {
      for (const e of hostiles(dim, s, C.landRadius[kind], caster)) {
        if (hit.has(e.id)) continue;
        hit.add(e.id);
        if (C.landDamage[kind] > 0) damage(e, C.landDamage[kind], caster);
        knockback(e, s, C.landKnock[kind], 0.4);
      }
    }
  }

  function writeLetter(i: number, t0: number): void {
    const s = PLAN[i];
    let land = G(Ds + s.v, s.u);
    let size = 0.8;
    let warn: Actor | undefined;
    let glyph: Actor | undefined;
    const slot = pagePt(s.a, s.b, 0.6);
    scene.at(t0, () => {
      land = landingSpot(i);
      size = fitSize(s.kind, land, s.elev, s.cap);
      glyph = scene.spawn("dw6_glyph", slot, { yaw: pageYaw, kind: s.kind, state: GLYPH.draw });
      snd("dw6_stroke", slot, 1.6, 0.95 + i * 0.02);
      warn = scene.spawn("telegraph", land, { kind: 0, size: Math.max(2, C.landRadius[s.kind] * (s.kind === BRIDGE ? 1 : 0.9)), state: TEL.slow });
    });
    // the letter is written stroke by stroke (top to bottom), a quill of light from the lectern below
    scene.every(1, (e) => {
      const k = Math.min(4, Math.floor(e / 4));
      const sp = pagePt(s.a + (rnd(t0 + e) - 0.5) * 14, s.b + 12 - k * 6, 0.8);
      fx("dw6_quill", sp);
      fx(e % 2 ? "dw6_glint" : "dw6_ink", sp);
      fxFlow("dw6_stream", (q) => bezier(up(bookAt, 1.5), up(lerp(bookAt, sp, 0.5), 3), sp, q), e, 3, 0.12);
    }, t0 + 1, t0 + DRAW);
    scene.at(t0 + DRAW - 2, () => { fx("dw6_halo", slot); fxBurst("dw6_letters", slot, 2.2, 5); });
    scene.at(t0 + DRAW, () => { glyph?.state(GLYPH.fall); snd("dw6_fall", slot, 1.4); });
    scene.span(t0 + DRAW, t0 + DRAW + FALL, (p) => {
      const to = up(land, 2.4 * size + 1);
      const mid = up(lerp(slot, to, 0.45), 6);
      const q = 0.25 * p + 0.75 * p * p;             // it tips out of the page and accelerates as it falls
      const pos = bezier(slot, mid, to, q);
      glyph?.move(pos, pageYaw);
      fx("dw6_trail", pos);
      fx("dw6_stream", bezier(slot, mid, to, Math.max(0, q - 0.06)));
      fx("dw6_stream", bezier(slot, mid, to, Math.max(0, q - 0.13)));
      if (scene.tick % 3 === 0) fx("dw6_letters", bezier(slot, mid, to, Math.max(0, q - 0.1)));
    });
    scene.at(t0 + DRAW + FALL, () => {
      if (glyph) { glyph.state(GLYPH.land); const g = glyph; scene.after(10, () => scene.despawn(g)); }
      if (warn) { warn.state(TEL.flash); const w = warn; scene.after(8, () => scene.despawn(w)); }
      const yaw = faceOrigin(land);
      const a = scene.spawn("dw6_edifice", land, { yaw, kind: s.kind, size, state: s.kind === BRIDGE ? ED.swing : ED.assemble });
      const ed: Edifice = { a, kind: s.kind, at: land, yaw, size, cells: cellsFor(s.kind, land, size),
        h: Math.max(3, Math.round(C.barrierHeight[s.kind] * size)), alive: true };
      edifices.push(ed);
      tb.place(up(add(land, mul(norm(flat(sub(c0, land))), 2)), 0.6), LIGHT);
      // the letter becomes marble: a spiral of script climbs the structure while its courses are laid
      const hgt = ED_H[s.kind] * size;
      scene.every(1, (e) => {
        for (const ph of [0, 120, 240]) {
          const a = (e * 23 + ph) * DEG, r = 1.9 * size + 0.6;
          fx("dw6_stream", { x: land.x + Math.cos(a) * r, y: land.y + 0.3 + (e / 30) * hgt, z: land.z + Math.sin(a) * r });
        }
      }, scene.tick + 1, scene.tick + 30);
      if (s.kind === BRIDGE) {
        snd("dw6_swing", land, 1.3);
        scene.after(21, () => impact(BRIDGE, land, size, []));
      } else impact(s.kind, land, size, ed.cells);
      if (ed.cells.length) raiseBarriers(ed);
      if (s.kind === PLATFORM || s.kind === BRIDGE) cover.push({ p: land, r: C.coverRadius });
      if (s.kind === CELESTIAL) {
        // the armillary turns over the field and fires a ray of script at the nearest enemies
        scene.every(C.celestialPulseEvery, () => {
          if (!ed.alive) return;
          const core = up(ed.at, 46 * ED_U * ed.size);
          fx("dw6_rays", up(ed.at, 0.3));
          fx("dw6_halo", core);
          for (const e of hostiles(dim, ed.at, C.celestialPulseRadius, caster).slice(0, 2)) {
            fxLine("dw6_trail", core, up(e.location, 1), 6);
            fx("dw6_seam", up(e.location, 1));
            damage(e, C.celestialPulseDamage, caster);
          }
        }, scene.tick + 20, T_UNW);
      }
      scene.after(s.kind === BRIDGE ? 28 : 32, () => { if (ed.alive) a.state(ED.hold); });
      // the letter is spoken: a mark for every enemy the landing reached
      for (const e of hostiles(dim, land, C.landRadius[s.kind] + 1, caster)) if (dist(e.location, center) <= C.domainRadius) mark(e);
    });
  }
  PLAN.forEach((_, i) => writeLetter(i, T_WRITE0 + WRITE_AT[i]));

  // ================================================================== PHASE III -- the laws written in heaven
  const TAB_D = Lp - 7;                                                    // a wide arc between the temple and the page
  const tabAng = [-30, -20, -10, 0, 10, 20, 30];
  const stations = tabAng.map((ang) => SKY(TAB_D * Math.cos(ang * DEG), TAB_D * Math.sin(ang * DEG), TAB_LIFT + 0.5 * Math.cos(ang * 3 * DEG)));
  const ruleA = (k: number): number => -45 + (102 / 7) * (k + 0.5);
  const tabLoc = (k: number): Vector3 => (tablets[k]?.valid ? tablets[k].loc : stations[k]);
  const emblem = (k: number): Vector3 => up(tabLoc(k), 3.1);
  scene.at(T_SPLIT, () => {
    page?.state(PAGE.split);
    pageGlitter = false;
    snd("dw6_split", pagePt(0, 44), 1.8);
    fx("dw6_flash", pagePt(6, 44, 1));
    for (let k = 1; k < 7; k++) fxLine("dw6_seam", pagePt(-45 + (102 / 7) * k, 4, 0.5), pagePt(-45 + (102 / 7) * k, 84, 0.5), 7);
  });
  scene.at(T_TAB, () => {
    for (let k = 0; k < 7; k++) {
      const from = pagePt(ruleA(k), 18, 0.4);
      tablets.push(scene.spawn("dw6_tablet", from, { yaw: pageYaw, kind: k, state: TAB.form }));
    }
  });
  scene.at(T_TAB + 24, () => { if (page) scene.despawn(page); page = undefined; });
  for (let k = 0; k < 7; k++) {
    const t0 = T_TAB + 2 + k * 3;
    scene.span(t0, t0 + TAB_FLY, (p) => {
      const tab = tablets[k];
      if (!tab) return;
      const from = pagePt(ruleA(k), 18, 0.4), to = stations[k];
      const pos = bezier(from, up(lerp(from, to, 0.5), 3), to, smooth(p));
      tab.move(pos, faceOrigin(pos));
      if (scene.tick % 2 === 0) fx("dw6_trail", up(pos, 4.5));
      if (scene.tick % 3 === 0) fx("dw6_stream", up(pos, 2 + rnd(scene.tick + k) * 6));
    });
    scene.at(t0 + TAB_FLY, () => { tablets[k]?.state(TAB.idle); fx("dw6_halo", emblem(k)); });
  }

  const walls: Actor[] = [];
  let refuge: Actor | undefined;
  addWard({ scene, factor: C.refugeFactor, protects: (e) => refugeOn && isAlly(e) && distXZ(e.location, refugeAt) <= C.refugeRadius });
  let finalWarn: Actor | undefined;
  const judged = new Set<string>();
  const judgedWarn: Actor[] = [];

  /** A tablet declares its law: it lifts and flares, its light pours down onto the field. */
  function declare(k: number, target: Vector3): void {
    const t = tablets[k];
    if (!t) return;
    t.state(TAB.declare);
    snd(`dw6_law${k + 1}`, target, 1.6);
    // a law declared on the caster's own place (Refuge) lands just in front of them, never in their face
    const onto = distXZ(target, c0) < 7 ? G(7, 0) : target;
    const from = emblem(k);
    fx("dw6_halo", from);
    fx("dw6_flare", from);
    scene.span(scene.tick, scene.tick + 12, (p, e) => {
      const path = (q: number): Vector3 => bezier(from, up(lerp(from, onto, 0.5), 5), up(onto, 1), q);
      fxFlow("dw6_stream", path, e, 3, 0.07);
      fx("dw6_trail", path(Math.min(1, p * 1.1)));
    });
    scene.after(10, () => { fx("dw6_quake", up(onto, 0.3)); fx("dw6_halo", up(onto, 1.5)); });
    scene.after(32, () => { if (scene.tick < T_RISE) t.state(TAB.idle); });
  }

  const laws: (() => void)[] = [
    // I Containment: written walls close the far side of the densest hostile region and draw it in; the side facing
    // the caster is closed by a low line of script (and barriers), so the view into the region stays open
    () => {
      const H = awayFrom(ground(centroid(domain(), G(Ds + 3, 0))), C.containMinDist);
      declare(0, H);
      const R = C.containRadius;
      const inside = allies(dim, H, R + 1.5, caster).length > 0;
      const toC = yawOf(sub(c0, H));
      for (let i = 0; i < 6; i++) {
        const ang = i * 60 + 30;
        const p = ground({ x: H.x + Math.cos(ang * DEG) * R, y: H.y, z: H.z + Math.sin(ang * DEG) * R });
        if (Math.abs(angleDelta(ang - 90, toC)) < 50) continue;
        const w = scene.spawn("dw6_wall", p, { yaw: yawOf(sub(H, p)), kind: 0, size: 1.0, state: WALL.rise });
        walls.push(w);
        scene.after(20, () => w.state(WALL.hold));
        scene.after(C.containTicks, () => { w.state(WALL.sink); scene.after(20, () => scene.despawn(w)); });
        scene.after(2, () => { fx("dw6_dust", up(p, 0.3)); fx("dw6_fountain", up(p, 0.3)); });
      }
      fxRing("dw6_quill", up(H, 0.3), R, 12);
      fx("dw6_wave", up(H, 0.2));
      for (const d of [2, 8]) {
        scene.after(d, () => {
          for (const e of hostiles(dim, H, C.containPull, caster)) if (distXZ(e.location, H) > R - 1.5) shove(e, sub(H, e.location), C.containPullStrength, 0.25);
        });
      }
      const cells: Vector3[] = [];
      scene.after(16, () => {
        for (let s = 0; s < 48; s++) {
          const a = (s * 360) / 48;
          if (inside && Math.abs(angleDelta(a - 90, toC)) < 30) continue;   // a doorway when a player stands inside
          const p = ground({ x: H.x + Math.cos(a * DEG) * R, y: H.y, z: H.z + Math.sin(a * DEG) * R });
          tb.column(Math.floor(p.x), Math.floor(p.y), Math.floor(p.z), 3);
          cells.push(p);
        }
      });
      // the near arc glows with a line of script for as long as the containment holds
      scene.every(2, (e) => {
        const a = (toC + 90 + (rnd(e * 1.7) - 0.5) * 100) * DEG;
        const p = { x: H.x + Math.cos(a) * R, y: H.y + 0.3, z: H.z + Math.sin(a) * R };
        fx(e % 4 ? "dw6_script" : "dw6_quill", p);
      }, scene.tick + 16, scene.tick + C.containTicks);
      scene.after(C.containTicks + 4, () => { for (const p of cells) tb.removeColumn(Math.floor(p.x), Math.floor(p.y), Math.floor(p.z), 3); });
    },
    // II Station: the two platforms glide in from the flanks and settle low across the front of the enemy, a written
    // bar (barriers two high) spans the line between them, and allies behind it are covered
    () => {
      const { E, near } = enemyFront();
      const toE = distXZ(E, c0) < 1 ? fwd : norm(flat(sub(E, c0)));
      const side = right(toE);
      stD = clamp(near - 1.5, C.stationMin, Ds - 1);
      const mid = ground(add(c0, mul(toE, stD)));
      declare(1, mid);
      cover.push({ p: c0, r: C.stationCover });
      for (const ed of edifices.filter((e) => e.kind === PLATFORM && e.alive)) {
        const dest = ground(add(mid, mul(side, (lateral(ed.at) < 0 ? -1 : 1) * C.stationSpread)));
        const from = ed.at, s0 = ed.size, cv = cover.find((z) => z.p === from);
        ed.a.state(ED.strike);
        scene.span(scene.tick + 4, scene.tick + 34, (p) => {
          const q = smooth(p);
          const pos = up(lerp(from, dest, q), Math.sin(q * Math.PI) * 0.8);
          ed.a.move(pos, faceOrigin(pos));
          ed.at = lerp(from, dest, q);
          if (scene.tick % 2 === 0) { ed.size = s0 + (C.stationSize - s0) * q; ed.a.size(ed.size); fx("dw6_dust", up(ed.at, 0.3)); }
        });
        scene.after(35, () => {
          ed.at = dest;
          ed.size = C.stationSize;
          ed.a.size(ed.size);
          if (ed.alive) ed.a.state(ED.hold);
          fx("dw6_quake", up(dest, 0.2));
          fx("dw6_halo", up(dest, 1.5));
          if (cv) cv.p = dest;
          for (const e of hostiles(dim, dest, 2.4, caster)) knockback(e, dest, 0.9, 0.3);
        });
      }
      scene.after(36, () => {
        const half = C.stationSpread + 2;
        for (let j = -half; j <= half; j++) {
          const c = ground(add(mid, mul(side, j)));
          tb.column(Math.floor(c.x), Math.floor(c.y), Math.floor(c.z), 2);
        }
        fxLine("dw6_seam", add(up(mid, 0.6), mul(side, -half)), add(up(mid, 0.6), mul(side, half)), 12);
      });
      scene.every(2, (e) => {
        const p = add(up(mid, 0.4 + (e % 3) * 0.5), mul(side, (rnd(e * 2.9) - 0.5) * 2 * (C.stationSpread + 2)));
        fx(e % 6 ? "dw6_script" : "dw6_glint", p);
      }, scene.tick + 36, T_UNW);
    },
    // III Direction: three banners of text are fired across the field, one lane after another
    () => {
      const ed0 = clamp(depth(enemyFront().E), 13, Ds + 4);
      declare(2, G(ed0, 0));
      const lanes = [{ d: ed0 - 2.5, dir: 1 }, { d: ed0 + 0.5, dir: -1 }, { d: ed0 + 4, dir: 1 }];
      lanes.forEach((ln, j) => {
        const from = G(ln.d, -16 * ln.dir), to = G(ln.d, 16 * ln.dir);
        const along = mul(rt, ln.dir);
        const w = scene.spawn("dw6_wall", from, { yaw: faceOrigin(from), kind: 1, size: 0.9, state: WALL.rise });
        walls.push(w);
        const hit = new Set<string>();
        const t0 = scene.tick + 12 + j * 8;
        scene.at(t0 - 10, () => fxLine("dw6_seam", up(from, 0.4), up(to, 0.4), 12));
        scene.at(t0, () => w.state(WALL.hold));
        scene.span(t0, t0 + C.directionTicks, (p) => {
          const pos = lerp(from, to, smooth(p));
          w.move(pos, faceOrigin(pos));
          fx("dw6_trail", up(pos, 1.4));
          if (scene.tick % 2 === 0) fx("dw6_ink", up(pos, 1.2));
          for (const e of hostiles(dim, pos, C.directionHalfWidth + 2, caster)) {
            const rel = sub(e.location, pos);
            const al = rel.x * rt.x + rel.z * rt.z, lat = rel.x * fwd.x + rel.z * fwd.z;
            if (Math.abs(al) > C.directionHalfWidth || Math.abs(lat) > C.directionBand || hit.has(e.id)) continue;
            hit.add(e.id);
            damage(e, C.directionDamage, caster);
            shove(e, along, 1.1, 0.3);
            fx("dw6_seam", up(e.location, 1));
          }
        });
        scene.at(t0 + C.directionTicks, () => { w.state(WALL.sink); scene.after(20, () => scene.despawn(w)); });
      });
    },
    // IV Stillness: hostile movement is bound in place, then dragged slow
    () => {
      declare(3, center);
      fx("dw6_wave_s", up(center, 0.3));
      scene.after(6, () => fx("dw6_wave_s", up(center, 0.5)));
      let n = 0;
      for (const e of domain()) {
        restrain(scene, e, C.stillTicks);
        effect(e, "slowness", C.stillTicks + C.stillSlowTicks, C.stillSlowAmp);
        fx("dw6_blue", up(e.location, 1));
        fx("dw6_silver", up(e.location, 2.2));
        if (n++ < 6) {
          const g = ground(e.location);
          const ci = scene.spawn("dw_circle", g, { size: 0.6, state: CIRCLE.form });
          scene.after(16, () => ci.state(CIRCLE.hold));
          scene.after(C.stillTicks, () => ci.state(CIRCLE.fade));
          scene.after(C.stillTicks + 14, () => scene.despawn(ci));
          scene.every(6, () => { if (isAlive(e)) fx("dw6_silver", up(e.location, 2.1)); }, scene.tick + 6, scene.tick + C.stillTicks);
        }
      }
    },
    // V Refuge: the allied zone is shielded and restored
    () => {
      refugeAt = ground(casterPos());
      declare(4, refugeAt);
      refuge = scene.spawn("dw6_dome", refugeAt, { state: DOME.form });
      refugeOn = true;
      scene.after(24, () => refuge?.state(DOME.hold));
      for (const p of allies(dim, refugeAt, C.refugeRadius, caster)) heal(p, C.refugeHeal);
      fxRing("dw6_letters", up(refugeAt, 0.4), C.refugeRadius + 0.6, 10);
      fxRing("dw6_feather", up(refugeAt, 3.2), C.refugeRadius, 6, 15);
    },
    // VI Sequence: each written structure strikes in turn, read from left to right
    () => {
      declare(5, center);
      [...edifices].filter((e) => e.alive).sort((a, b) => lateral(a.at) - lateral(b.at)).forEach((ed, j) => {
        scene.after(6 + j * 4, () => {
          if (!ed.alive) return;
          ed.a.state(ED.strike);
          scene.after(16, () => { if (ed.alive) ed.a.state(ED.hold); });
          const p = ed.at, hgt = ED_H[ed.kind] * ed.size, top = up(p, hgt * 0.8);
          fx("dw6_pillar", up(p, 6));
          fx("dw6_quake", up(p, 0.2));
          fx("dw6_flare", top);
          fx("dw6_halo", up(p, hgt * 0.5));
          fxBurst("dw6_ink", up(p, hgt * 0.6), 1.8, 5);
          snd("dw6_strike", p, 0.8, 1.0 + j * 0.05);
          const hit = new Set<string>();
          for (const e of hostiles(dim, p, C.sequenceRadius, caster)) { hit.add(e.id); damage(e, C.sequenceDamage, caster); knockback(e, p, 0.6, 0.3); }
          // ...and looses a bolt of script at the nearest enemy beyond its reach
          const far = hostiles(dim, p, C.sequenceReach, caster).find((e) => !hit.has(e.id));
          if (far) {
            fxLine("dw6_trail", top, up(far.location, 1), 8);
            fxLine("dw6_stream", top, up(far.location, 1), 5);
            fx("dw6_flare", up(far.location, 1));
            damage(far, C.sequenceDamage, caster);
            knockback(far, p, 0.5, 0.25);
          }
        });
      });
    },
    // VII Judgment: every surviving enemy is marked and the finale's region is designated
    () => {
      const es = domain();
      const fa = target && isAlive(target) && dist(target.location, center) <= C.domainRadius ? target.location : centroid(es, G(Ds + 2, 0));
      finalAt = awayFrom(ground(fa), C.finalMinDist);
      declare(6, finalAt);
      for (const e of es) { mark(e, 2); judged.add(e.id); }
      finalWarn = scene.spawn("telegraph", finalAt, { kind: 0, size: C.finalRadius, state: TEL.slow });
      scene.after(40, () => finalWarn?.state(TEL.hold));
      fx("dw6_pillar", up(finalAt, 6));
      fx("dw6_rays", up(finalAt, 0.3));
      for (const e of es.slice(0, 4)) {
        const w = scene.spawn("telegraph", ground(e.location), { kind: 0, size: 1.6, state: TEL.warn });
        scene.after(20, () => w.state(TEL.hold));
        scene.follow(w, e, 0.05);
        judgedWarn.push(w);
      }
    },
  ];
  laws.forEach((fn, k) => scene.at(T_LAW0 + k * LAW_STEP, fn));
  const T_REF = T_LAW0 + 4 * LAW_STEP;
  scene.every(40, () => { if (refugeOn) for (const p of allies(dim, refugeAt, C.refugeRadius, caster)) heal(p, C.refugeRegen); }, T_REF + 40, T_UNW);
  scene.every(10, () => { if (refugeOn) dissolveProjectiles(scene, up(refugeAt, 2), C.refugeRadius); }, T_REF, T_UNW);

  // ================================================================== PHASE IV -- let it be written
  // the tablets shed their letters (which fly down toward the field) and rise away into the sky, one after another
  scene.at(T_RISE, () => {
    tablets.forEach((t) => t.state(TAB.shed));
    snd("dw6_rise", SKY(TAB_D, 0, 8), 1.8);
    fx("dw6_flash", SKY(TAB_D, 0, 11));
    fx("dw6_wave", up(center, 0.3));
    fxLine("dw6_seam", SKY(TAB_D, -16, 9), SKY(TAB_D, 16, 9), 14);
  });
  const raised = (k: number): Vector3 => up(add(stations[k], mul(norm(flat(sub(stations[k], c0))), TAB_BACK)), TAB_RISE);
  for (let k = 0; k < 7; k++) {
    const t0 = T_RISE + 8 + Math.abs(k - 3) * 4;
    scene.span(t0, t0 + 44, (p) => {
      const tab = tablets[k];
      if (!tab) return;
      const pos = lerp(stations[k], raised(k), easeIn(p) * 0.7 + smooth(p) * 0.3);
      tab.move(pos);
      if (scene.tick % 2 === 0) fx("dw6_trail", up(pos, 2));
      if (scene.tick % 3 === 0) fx("dw6_letters", up(pos, 1));
    });
    scene.at(t0, () => { fx("dw6_halo", emblem(k)); fxBurst("dw6_ink", emblem(k), 2.5, 5); });
  }
  scene.at(T_RISE + 40, () => tablets.forEach((t) => t.state(TAB.idle)));
  scene.at(T_RISE + 56, () => { tabletsShown = false; });

  /** A line of text assembles in the sky out of letters streaming from the tablets. */
  function spawnLine(kind: number, p: Vector3, size: number): Actor {
    const a = scene.spawn("dw6_line", p, { yaw: faceOrigin(p), kind, size, state: LINE.assemble });
    snd("dw6_form", p, 1.4, 1 + kind * 0.06);
    hovering.push(a);
    scene.span(scene.tick, scene.tick + 24, (_q, e) => {
      for (let k = (e % 2); k < tablets.length; k += 2) {
        const from = up(tabLoc(k), 6);
        fxFlow("dw6_stream", (q) => bezier(from, up(lerp(from, p, 0.5), 2), p, q), e + k * 2, 1, 0.08);
      }
    });
    scene.after(30, () => a.state(LINE.hold));
    return a;
  }
  const descend = (a: Actor, from: Vector3, to: Vector3, t0: number, t1: number): void => {
    scene.span(t0, t1, (p) => a.move(lerp(from, to, easeIn(p) * 0.6 + smooth(p) * 0.4)));
  };
  const leave = (a: Actor): void => { const i = hovering.indexOf(a); if (i >= 0) hovering.splice(i, 1); };

  // line 1: a straight line slams down at the enemy's near edge (beyond the Station line) and rolls away, sweeping them back
  const L1 = { form: T_RISE + 14, desc: T_RISE + 42 };
  let l1: Actor | undefined;
  const l1Hi = SKY(Ds + 4, 0, 5.0);
  let sweepD = Ds;
  const sweepAt = (p: number): Vector3 => G(sweepD + C.sweepTravel * smooth(p), 0, 0.95);
  scene.at(L1.form, () => { l1 = spawnLine(0, l1Hi, (C.sweepHalfLength * 2) / 24.4); });
  const sweepWarn: Actor[] = [];
  scene.at(L1.desc - 22, () => {
    sweepD = clamp(Math.max(enemyFront().near - 1, stD + 2.2), 12, Ds + 3);
    for (const v of [0.5, 3.5, 6.5]) sweepWarn.push(scene.spawn("telegraph", G(sweepD + v, 0), { kind: 0, size: 2.6, state: TEL.warn }));
  });
  scene.at(L1.desc, () => { if (l1) { leave(l1); descend(l1, l1Hi, sweepAt(0), L1.desc, L1.desc + 16); } });
  scene.at(L1.desc + 16, () => {
    const lo = sweepAt(0);
    l1?.state(LINE.strike);
    snd("dw6_strike", lo, 1.5);
    fx("dw6_flare", lo);
    for (let j = -2; j <= 2; j++) { fx("dw6_quake", add(up(lo, -0.8), mul(rt, j * 2.6))); fx("dw6_dust", add(up(lo, -0.7), mul(rt, j * 2.6))); }
  });
  {
    const hit = new Set<string>();
    scene.span(L1.desc + 16, L1.desc + 48, (p) => {
      const pos = sweepAt(p);
      l1?.move(pos);
      if (scene.tick % 2 === 0) fxLine("dw6_seam", add(pos, mul(rt, -C.sweepHalfLength)), add(pos, mul(rt, C.sweepHalfLength)), 6);
      fx("dw6_dust", add(up(pos, -0.7), mul(rt, (rnd(scene.tick) - 0.5) * 2 * C.sweepHalfLength)));
      for (const e of hostiles(dim, pos, C.sweepHalfLength + 1.5, caster)) {
        const rel = sub(e.location, pos);
        if (hit.has(e.id) || Math.abs(rel.x * fwd.x + rel.z * fwd.z) > 1.8 || Math.abs(rel.x * rt.x + rel.z * rt.z) > C.sweepHalfLength) continue;
        hit.add(e.id);
        damage(e, C.sweepDamage, caster);
        shove(e, fwd, 1.0, 0.35);
      }
    });
  }
  scene.at(L1.desc + 48, () => sweepWarn.forEach((w) => { w.state(TEL.flash); scene.after(8, () => scene.despawn(w)); }));
  scene.at(L1.desc + 50, () => { l1?.state(LINE.unwrite); if (l1) fxBurst("dw6_letters", up(l1.loc, 1), 3, 6); });
  scene.at(L1.desc + 70, () => { if (l1) scene.despawn(l1); });

  // line 2: a ring of text lands among the enemy and expands outward
  const L2 = { form: T_RISE + 26, desc: T_RISE + 78 };
  let l2: Actor | undefined;
  let ringC = G(Ds + 2, 0);
  let ringMax = 6;
  const l2Hi = SKY(Ds + 5, 0, 6.0);
  let ringWarn: Actor | undefined;
  scene.at(L2.form, () => { l2 = spawnLine(1, l2Hi, 0.5); });
  scene.at(L2.desc - 20, () => {
    ringC = clampDist(enemyFront().E, 13, Ds + 5);
    ringMax = clamp(distXZ(ringC, c0) - 7.5, 4.5, C.ringMaxRadius);
    ringWarn = scene.spawn("telegraph", ringC, { kind: 0, size: ringMax, state: TEL.warn });
  });
  scene.at(L2.desc, () => { if (l2) { leave(l2); descend(l2, l2Hi, up(ringC, 1.0), L2.desc, L2.desc + 16); } });
  scene.at(L2.desc + 16, () => { l2?.state(LINE.strike); snd("dw6_strike", ringC, 1.5, 0.85); fx("dw6_quake", up(ringC, 0.2)); fx("dw6_flare", up(ringC, 1)); });
  {
    const hit = new Set<string>();
    scene.span(L2.desc + 16, L2.desc + 44, (p) => {
      const rad = 2.5 + (ringMax - 2.5) * easeOut(p);
      l2?.size(rad / 7.5);
      if (scene.tick % 2 === 0) fxRing("dw6_seam", up(ringC, 0.6), rad, 12, scene.tick * 7);
      if (scene.tick % 4 === 0) fxRing("dw6_ink", up(ringC, 1.4), rad, 6, scene.tick * 11);
      for (const e of hostiles(dim, ringC, rad + 1.5, caster)) {
        if (hit.has(e.id) || Math.abs(distXZ(e.location, ringC) - rad) > 1.8) continue;
        hit.add(e.id);
        damage(e, C.ringDamage, caster);
        knockback(e, ringC, 1.0, 0.4);
      }
    });
  }
  scene.at(L2.desc + 44, () => { if (ringWarn) { ringWarn.state(TEL.flash); const w = ringWarn; scene.after(8, () => scene.despawn(w)); } fx("dw6_wave", up(ringC, 0.3)); });
  scene.at(L2.desc + 46, () => l2?.state(LINE.unwrite));
  scene.at(L2.desc + 66, () => { if (l2) scene.despawn(l2); });

  // line 3: a lattice hovers over the enemy and its letters fall as a checkerboard of columns of light
  const L3 = { form: T_RISE + 84, desc: T_RISE + 118 };
  let l3: Actor | undefined;
  let latC = G(Ds + 3, 0);
  const l3Hi = SKY(Ds + 7, 0, 6.6);
  scene.at(L3.form, () => { l3 = spawnLine(2, l3Hi, 0.83); });
  scene.at(L3.desc - 2, () => { latC = clampDist(enemyFront().E, 15, Ds + 6); });
  scene.at(L3.desc, () => { if (l3) { leave(l3); descend(l3, l3Hi, up(latC, 4.6), L3.desc, L3.desc + 16); } });
  const cell = (gx: number, gz: number): Vector3 => ground(add(add(latC, mul(rt, gx * 5)), mul(fwd, gz * 5)));
  const waves = [[[-1, -1], [1, -1], [0, 0], [-1, 1], [1, 1]], [[0, -1], [-1, 0], [1, 0], [0, 1]]];
  waves.forEach((cells, w) => {
    const tw = L3.desc + 32 + w * 22;
    const spots: Vector3[] = [];
    const warns: Actor[] = [];
    scene.at(tw - 20, () => {
      for (const [gx, gz] of cells) { const s = cell(gx, gz); spots.push(s); warns.push(scene.spawn("telegraph", s, { kind: 0, size: C.latticeRadius, state: TEL.warn })); }
    });
    scene.at(tw - 6, () => {
      l3?.state(LINE.strike);
      for (const s of spots) {
        const col = scene.spawn("dw_column", s, { kind: w === 0 ? 0 : 2, size: 0.85, state: LIGHTCOL.descend });
        scene.after(10, () => col.state(LIGHTCOL.hold));
        scene.after(22, () => col.state(LIGHTCOL.dissolve));
        scene.after(36, () => scene.despawn(col));
      }
      snd("dw6_strike", latC, 1.4, 1.1 + w * 0.15);
    });
    scene.at(tw, () => {
      const hit = new Set<string>();
      warns.forEach((x) => { x.state(TEL.flash); scene.after(8, () => scene.despawn(x)); });
      for (const s of spots) {
        fx("dw6_quake", up(s, 0.2));
        fx("dw6_rays", up(s, 0.3));
        fx("dw6_flare", up(s, 1));
        for (const e of hostiles(dim, s, C.latticeRadius, caster)) {
          if (hit.has(e.id)) continue;
          hit.add(e.id);
          damage(e, C.latticeDamage, caster);
          knockback(e, s, 0.8, 0.5);
        }
      }
    });
  });
  scene.at(L3.desc + 70, () => l3?.state(LINE.unwrite));
  scene.at(L3.desc + 90, () => { if (l3) scene.despawn(l3); });

  // line 4: a spiral settles on the judged region and draws the field into it
  const L4 = { form: T_RISE + 102, desc: T_RISE + 150 };
  let l4: Actor | undefined;
  const l4Hi = SKY(Ds + 9, 0, 7.4);
  let spiralWarn: Actor | undefined;
  let spiralR = 9;
  scene.at(L4.form, () => { l4 = spawnLine(3, l4Hi, 0.7); });
  scene.at(L4.desc - 20, () => {
    spiralR = clamp(distXZ(finalAt, c0) - 8.5, 4.5, 10);     // its outer turn stays > 7 blocks from the caster
    spiralWarn = scene.spawn("telegraph", finalAt, { kind: 0, size: spiralR, state: TEL.warn });
  });
  scene.at(L4.desc, () => { if (l4) { leave(l4); descend(l4, l4Hi, up(finalAt, 1.4), L4.desc, L4.desc + 16); } });
  scene.at(L4.desc + 16, () => { l4?.state(LINE.strike); snd("dw6_strike", finalAt, 1.4, 0.75); fx("dw6_quake", up(finalAt, 0.2)); });
  scene.span(L4.desc + 16, L4.desc + 56, (p, el) => {
    const rad = spiralR * (1 - smooth(p)) + 1.2;
    l4?.size(Math.max(0.15, rad / 8.6));
    if (el % 2 === 0) fxRing("dw6_stream", up(finalAt, 0.8 + p * 1.5), rad, 8, el * 21);
    if (el % 5 === 0) {
      for (const e of hostiles(dim, finalAt, rad + 1, caster)) {
        shove(e, sub(finalAt, e.location), C.spiralPull, 0.1);
        if (el % 10 === 0) damage(e, C.spiralTickDamage, caster);
      }
    }
  });
  scene.at(L4.desc + 56, () => {
    l4?.state(LINE.strike);
    spiralWarn?.state(TEL.flash);
    fx("dw6_flare", up(finalAt, 1.5));
    fx("dw6_quake", up(finalAt, 0.3));
    for (const e of hostiles(dim, finalAt, 3.5, caster)) damage(e, C.spiralFinalDamage, caster);
  });
  scene.at(L4.desc + 64, () => { if (spiralWarn) scene.despawn(spiralWarn); l4?.state(LINE.unwrite); });
  scene.at(L4.desc + 84, () => { if (l4) scene.despawn(l4); });

  // the final line: the immense white-gold formation gathers everything written, then strikes the judged region
  const T_FORM = T_RISE + 160;                   // after the lattice has fallen
  const fSize = C.finalRadius / 12.4;              // its seal covers exactly the judged region
  let form: Actor | undefined;
  let formAt = up(finalAt, 4.3);
  scene.at(T_FORM, () => {
    formAt = up(finalAt, 4.3);
    form = spawnLine(4, formAt, fSize);
    leave(form);
    snd("dw6_form", formAt, 1.8, 0.7);
    fx("dw6_halo", formAt);
  });
  // build-up: the formation sinks a little and turns while every structure and tablet pours its letters into it
  scene.at(T_FINAL - 68, () => snd("dw6_gather", finalAt, 2.0));
  scene.at(T_FINAL - 44, () => { if (finalWarn?.valid) finalWarn.state(TEL.warn); else finalWarn = scene.spawn("telegraph", finalAt, { kind: 0, size: C.finalRadius, state: TEL.warn }); });
  scene.span(T_FINAL - 44, T_FINAL - 8, (p, e) => {
    const pos = up(finalAt, 4.3 - 0.7 * smooth(p));
    form?.move(pos);
    formAt = pos;
    if (e % 4 === 0) fx("dw6_converge", pos);
    if (e % 3 === 0) fxRing("dw6_ink", up(finalAt, 0.4), C.finalRadius, 6, e * 9);
    const srcs = edifices.filter((x) => x.alive);
    for (let j = e % 3; j < srcs.length; j += 3) {
      const s = up(srcs[j].at, ED_H[srcs[j].kind] * srcs[j].size * 0.7);
      fxFlow("dw6_stream", (q) => bezier(s, up(lerp(s, pos, 0.5), 3), pos, q), e + j, 1, 0.06);
    }
    for (let k = e % 2; k < tablets.length; k += 2) {
      const s = up(tabLoc(k), 6);
      fxFlow("dw6_trail", (q) => bezier(s, up(lerp(s, pos, 0.5), 4), pos, q), e + k, 1, 0.05);
    }
  });
  scene.at(T_FINAL - 40, () => tablets.forEach((t) => t.state(TAB.declare)));
  scene.at(T_FINAL - 16, () => snd("dw6_finale", finalAt, 2.4));
  // anticipation, then the strike
  scene.span(T_FINAL - 8, T_FINAL, (p) => {
    const pos = p < 0.5 ? up(finalAt, 3.6 + 0.6 * smooth(p * 2)) : up(finalAt, 4.2 - 2.4 * easeIn((p - 0.5) * 2));
    form?.move(pos);
    formAt = pos;
  });
  scene.at(T_FINAL, () => {
    form?.state(LINE.strike);
    finalWarn?.state(TEL.flash);
    for (const w of judgedWarn) w.state(TEL.flash);
    fx("dw6_flash", up(finalAt, 2));
    fx("dw6_flare", up(finalAt, 1));
    fx("dw6_pillar", up(finalAt, 6));
    fx("dw6_wave", up(finalAt, 0.2));
    fx("dw6_quake", up(finalAt, 0.3));
    fx("dw6_fountain", up(finalAt, 0.4));
    fxRing("dw6_rays", up(finalAt, 0.4), C.finalRadius * 0.55, 8);
    fxRing("dw6_dust", up(finalAt, 0.4), C.finalRadius * 0.75, 10);
    fxBurst("dw6_ink", up(finalAt, 2.5), C.finalRadius * 0.5, 16);
    fxRing("dw6_pillar", up(finalAt, 6), C.finalRadius * 0.9, 8, 30);
    fxRing("dw6_letters", up(finalAt, 1.0), C.finalRadius, 12, 15);
    fxRing("dw6_halo", up(finalAt, 2.0), C.finalRadius * 0.6, 6);
    for (let i = 0; i < 6; i++) tb.place(up(add(finalAt, { x: Math.cos(i) * 3, y: 0, z: Math.sin(i) * 3 }), 1), LIGHT);
    for (const e of hostiles(dim, finalAt, C.finalRadius, caster)) {
      damage(e, C.finalDamage + (judged.has(e.id) ? C.judgedBonus : 0), caster);
      knockback(e, finalAt, C.finalKnockback, 0.7);
    }
    for (const m of marks.values()) { m.a.state(MARK.burst); const a = m.a; scene.after(8, () => scene.despawn(a)); }
  });
  scene.at(T_FINAL + 3, () => { fx("dw6_wave", up(finalAt, 0.3)); fxRing("dw6_letters", up(finalAt, 0.6), C.finalRadius * 0.6, 8); });
  scene.at(T_FINAL + 7, () => { fx("dw6_wave", up(finalAt, 0.4)); fx("dw6_flare", up(finalAt, 3)); });
  // aftermath: golden embers and letters rain over the judged region
  scene.every(1, (e) => {
    const k = e * 7.3;
    const a = rnd(k) * 2 * Math.PI, r = Math.sqrt(rnd(k + 0.5)) * C.finalRadius;
    fx("dw6_ember", { x: finalAt.x + Math.cos(a) * r, y: finalAt.y + 4 + rnd(k + 1) * 4, z: finalAt.z + Math.sin(a) * r });
    if (e % 2 === 0) fx("dw6_script", { x: finalAt.x - Math.cos(a) * r, y: finalAt.y + 0.5 + rnd(k + 2) * 3, z: finalAt.z - Math.sin(a) * r });
  }, T_FINAL + 1, T_FINAL + 50);
  scene.at(T_FINAL + 10, () => { if (finalWarn) scene.despawn(finalWarn); judgedWarn.forEach((w) => scene.despawn(w)); });
  scene.at(T_FINAL + 24, () => { form?.state(LINE.unwrite); fxBurst("dw6_letters", up(finalAt, 3), 5, 8); });
  scene.at(T_FINAL + 44, () => { if (form) scene.despawn(form); });

  // ================================================================== PHASE V -- the final amen
  scene.at(T_UNW, () => {
    refugeOn = false;
    refuge?.state(DOME.fade);
    for (const w of walls) if (w.valid) w.state(WALL.sink);
    tb.clearAll();
    snd("dw6_unwrite", center, 1.6);
  });
  scene.at(T_UNW + 20, () => { if (refuge) scene.despawn(refuge); walls.forEach((w) => scene.despawn(w)); });
  // the temple is unwritten nearest first: each structure becomes rising text that streams into the codex
  scene.at(T_UNW + 2, () => {
    [...edifices].sort((a, b) => distXZ(a.at, c0) - distXZ(b.at, c0)).forEach((ed, j) => {
      const t0 = scene.tick + j * 3;
      scene.at(t0, () => {
        ed.alive = false;
        ed.a.state(ED.unwrite);
        fx("dw6_fountain", up(ed.at, 0.5));
        fx("dw6_halo", up(ed.at, ED_H[ed.kind] * ed.size * 0.5));
        if (j % 3 === 0) snd("dw6_unwrite", ed.at, 0.9, 1.1 + j * 0.03);
      });
      scene.at(t0 + 42, () => scene.despawn(ed.a));
      const top = up(ed.at, ED_H[ed.kind] * ed.size * 0.6);
      scene.every(1, (e) => {
        const to = up(bookAt, 1.0);
        const path = (q: number): Vector3 => bezier(top, up(lerp(top, to, 0.5), 7), to, q);
        fxFlow("dw6_stream", path, e, 2, 0.04);
        if (e % 3 === 0) fx("dw6_script", path(rnd(e + j) * 0.3));
      }, t0 + 10, t0 + 40);
    });
  });
  // the codex returns from its lectern to the centre of the field
  scene.at(T_FINAL + 10, () => { snd("dw6_glide", b2, 1.4, 0.9); bookShows = true; });
  scene.span(T_FINAL + 10, T_FINAL + 54, (p) => {
    const q = smooth(p);
    bookAt = bezier(b2, up(lerp(b2, bF, 0.5), 8), bF, q);
    book.move(bookAt, faceOrigin(bookAt));
    if (scene.tick % 2 === 0) book.size(BOOK_LECTERN + (BOOK_FINAL - BOOK_LECTERN) * q);
    fx("dw6_stream", up(bookAt, -0.6));
  });
  scene.at(T_FINAL + 56, () => tb.place(up(bF, -1.4), LIGHT));
  // the tablets come down from the sky and lie together again as the page
  scene.at(T_TABRET, () => { tablets.forEach((t) => t.state(TAB.ret)); tabletsShown = true; });
  scene.span(T_TABRET, T_TABRET + TAB_RET, (p) => {
    tablets.forEach((t, k) => {
      const from = raised(k), to = pagePt(ruleA(k), 18, 0.3);
      const pos = bezier(from, up(lerp(from, to, 0.5), 3), to, smooth(p));
      t.move(pos, pageYaw);
      if (scene.tick % 2 === 0) fx("dw6_trail", up(pos, 4));
    });
  });
  scene.at(T_REFORM, () => {
    page = scene.spawn("dw6_page", pageO, { yaw: pageYaw, state: PAGE.reform });
    snd("dw6_page", pagePt(0, 44), 1.4, 1.2);
    fx("dw6_flash", pagePt(6, 44, 1));
    for (let k = 0; k < 7; k++) fx("dw6_halo", pagePt(ruleA(k), 40, 0.6));
  });
  scene.at(T_REFORM + 8, () => tablets.forEach((t) => scene.despawn(t)));
  // the page folds in halves, four times, down to a single leaf
  scene.at(T_FOLD, () => page?.state(PAGE.fold));
  [14, 25, 36, 47].forEach((d, k) => scene.at(T_FOLD + d, () => {
    snd("dw6_fold", pageO, 1.6, 1 + k * 0.08);
    const edge = [pagePt(0, 44, 0.5), pagePt(0, 44, 0.5), pagePt(-30, 22, 0.5), pagePt(-45, 22, 0.5)][k];
    fxBurst("dw6_ink", edge, 3 - k * 0.5, 7);
    fx("dw6_halo", edge);
  }));
  // the folding sheet sparkles along its shrinking extent
  scene.every(1, (e) => {
    const p = Math.min(1, e / 48), w = 58 * (1 - 0.86 * p), h = 42 * (1 - 0.86 * p), bc = 44 * (1 - p) + 4 * p;
    for (let i = 0; i < 3; i++) {
      const k = e * 3.3 + i;
      fx(i ? "dw6_glint" : "dw6_script", pagePt((rnd(k) - 0.5) * 2 * w, bc + (rnd(k + 0.4) - 0.5) * 2 * h, 0.6));
    }
  }, T_FOLD + 2, T_FOLD + 50);
  // the leaf glides down into the codex
  const leafAt = (): Vector3 => up(bookAt, 1.2);
  scene.at(T_FLY - 12, () => { book.state(BOOK.gather).skin(0); fxBurst("dw6_letters", up(bookAt, 1.5), 1.6, 5); }); // the inscriptions return
  scene.span(T_FLY, T_FLY + FLY, (p) => {
    const from = pageO, to = leafAt();
    const pos = bezier(from, up(lerp(from, to, 0.5), 4), to, smooth(p));
    page?.move(pos, faceOrigin(pos));
    fx("dw6_trail", up(pos, 0.6));
    fx("dw6_stream", up(pos, 0.6));
    fx("dw6_stream", bezier(from, up(lerp(from, to, 0.5), 4), to, Math.max(0, smooth(p) - 0.05)));
    if (scene.tick % 2 === 0) fx("dw6_script", up(pos, 0.3 + rnd(scene.tick)));
  });
  // the inscriptions return: letters spiral in from all around and settle into the open codex
  scene.every(1, (e) => {
    for (const ph of [0, 120, 240]) {
      const r = 4.5 * (1 - ((e % 20) / 20)) + 0.6, a = (e * 17 + ph) * DEG;
      fx("dw6_stream", add(bookAt, { x: Math.cos(a) * r, y: 0.3 + (r / 5) * 2, z: Math.sin(a) * r }));
    }
  }, T_FLY - 12, T_CLOSE + 18);
  scene.at(T_SLIP, () => { page?.state(PAGE.slip); fx("dw6_flare", up(bookAt, 1)); fx("dw6_halo", up(bookAt, 1.2)); });
  scene.at(T_SLIP + 16, () => { if (page) scene.despawn(page); page = undefined; });
  scene.at(T_CLOSE, () => { book.state(BOOK.close); snd("dw6_close", bookAt, 1.3); });
  scene.at(T_CLOSE + 19, () => {
    fx("dw6_flare", bookAt);
    fx("dw6_wave", up(bookAt, -2.2));
    fxRing("dw6_letters", up(bookAt, -1.6), 3, 6);
    snd("dw6_amen", bookAt, 1.5);
    boundary.state(BOUND.unwrite);
    boundaryOn = false;
  });
  // the boundary letters lift away all around the domain
  scene.every(1, (e) => { for (let i = 0; i < 4; i++) fx("dw6_letters", ringPt(rnd(e * 3 + i) * 360, 0.4)); }, T_CLOSE + 19, T_CLOSE + 49);
  // all the written things return to the Grimoire: six streams of letters converge on it from the far side and flanks
  const returnSrc = [-100, -60, -20, 20, 60, 100].map((th) => G(Ds + 15 * Math.cos(th * DEG), 15 * Math.sin(th * DEG), 1));
  scene.every(1, (e) => {
    returnSrc.forEach((src, j) => {
      const to = up(bookAt, 0.8);
      fx("dw6_stream", bezier(src, up(lerp(src, to, 0.5), 6), to, ((e * 0.035) + j * 0.17) % 1));
    });
  }, T_FOLD - 30, T_CLOSE + 10);
  scene.at(T_CLOSE + 51, () => scene.despawn(boundary));
  // the closed codex lifts and dissolves into light: the last word of the spell
  scene.at(T_VANISH, () => {
    book.state(BOOK.vanish);
    bookShows = false;
    snd("dw6_seal", bookAt, 1.6);
    fx("dw6_pillar", up(bookAt, 4));
    fx("dw6_fountain", up(bookAt, -1));
    fx("dw6_halo", up(bookAt, 1));
  });
  scene.every(1, (e) => {
    const h = 0.6 + e * 0.09;
    fxRing("dw6_stream", up(bookAt, h), 1.4 + e * 0.035, 4, e * 23);
    if (e % 3 === 0) fx("dw6_glint", up(bookAt, h + 1.2));
  }, T_VANISH + 2, T_VANISH + 30);
  scene.at(T_VANISH + 24, () => { fx("dw6_flare", up(bookAt, 3)); fx("dw6_wave", up(bF, -2.4)); fxBurst("dw6_letters", up(bookAt, 3), 2.5, 8); });
  scene.at(T_VANISH + 30, () => scene.despawn(book));

  // afterglow: a soft golden rain and the last letters settle over the domain while the light fades
  scene.every(1, (e) => {
    const n = e < 30 ? 4 : 2;
    for (let i = 0; i < n; i++) {
      const k = e * 5.1 + i * 1.7;
      const a = rnd(k) * 2 * Math.PI, r = 2 + Math.sqrt(rnd(k + 1)) * 14;
      const p = { x: bF.x + Math.cos(a) * r, y: bF.y + 1 + rnd(k + 2) * 6, z: bF.z + Math.sin(a) * r };
      if (distXZ(p, c0) > 6) fx(i % 2 ? "dw6_ember" : (e + i) % 3 ? "dw6_motes" : "dw6_script", p);
    }
  }, T_CLOSE + 20, T_END - 2);
  scene.endAt(T_END);
});
