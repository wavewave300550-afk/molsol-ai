import { Entity, Player, Vector3 } from "@minecraft/server";
import { DN03 as C } from "../config/dn03";
import { defineSpell } from "../core/registry";
import { damage, drag, effect, shove } from "../lib/combat";
import { burst, line, particle, ring, sound } from "../lib/fx";
import { Actor, secs } from "../lib/scene";
import { allies, focus, groundBelow, hostiles, isAlive, plateau } from "../lib/targeting";
import { blocksFor } from "../lib/tempblocks";
import { V3, add, angleDelta, bezier, clamp, distXZ, flat, lerp, mul, norm, smooth, sub, up, yawOf } from "../lib/vec";

// ---- animation states (tools/assets/dn_house.py HOUSE_STATES / WALL_STATES / FURN_STATES / DOOR_STATES)
const HS = { hidden: 0, land: 1, closed: 2, open: 3, opened: 4, unfold: 5, spread: 6, shiftA: 7, shiftB: 8, fold: 9, close: 10, vanish: 11 };
const WS = { hidden: 0, rise: 1, idle: 2, slide: 3, settle: 4, fold: 5, fly: 6 };
const FS = { hidden: 0, appear: 1, idle: 2, move: 3, act: 4, vanish: 5 };
const DS = { hidden: 0, hop: 1, pop: 2 };
/** Wall kinds: 0 plain wallpaper, 1 door, 2 window, 3 stairs fragment. */
const KIND_DOOR = 1;
const BASE_KINDS = [0, 2, 0, 3];
// ---- animation lengths in seconds (dn_house.py L_*)
const L = { land: 1.0, open: 1.6, unfold: 1.0, shift: 0.8, fold: 1.0, close: 1.0, vanish: 0.8, wRise: 0.8, wSettle: 0.5, wFold: 0.5,
  fAppear: 0.6, fAct: 0.8, fVanish: 0.5, doorPop: 0.4 };

type Edge = { o: 0 | 1; i: number; j: number }; // o 0: along X on grid line z=j; o 1: along Z on grid line x=i
type Cell = [number, number];
interface Wall { a: Actor; key: string | null; e: Edge | null; door: boolean; base: number; cols: string[]; pos: V3; yaw: number; arrived: boolean }
interface Furn { a: Actor; id: string; pos: V3; cell: Cell | null }
interface Plan { walls: Map<string, { e: Edge; door: boolean }>; loopKey: string; start: Cell; score: Map<string, number> }

const ek = (e: Edge): string => `${e.o},${e.i},${e.j}`;
const pk = (e: string): Edge => { const [o, i, j] = e.split(",").map(Number); return { o: o as 0 | 1, i, j }; };
function hash01(a: number, s: string): number {
  let h = (2166136261 ^ (a * 7919)) >>> 0;
  for (let k = 0; k < s.length; k++) h = Math.imul(h ^ s.charCodeAt(k), 16777619) >>> 0;
  return (h % 1000) / 1000;
}

/**
 * DN03 - House of Shifting Sleep.
 * A gigantic dollhouse lands on the battlefield, swings its facade open on the six contradictory
 * rooms inside, then unfolds: its walls fly out as pop-up pages and stand up as a maze of real
 * barrier walls around the enemies.  Every 2.5 s the house rearranges itself - walls slide along
 * the grid or turn a quarter around a corner, doors hop between walls, the looping corridor moves -
 * always splitting hostile groups, closing the caster's side, funnelling enemies down a corridor
 * that leads away and loops them back to its start, and always leaving every player a way out.
 * After 12 s everything folds back into the house, which closes and shrinks into a toy.
 */
export default defineSpell("dn03", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const N = C.gridCells, CS = C.cellSize, HALF = (N * CS) / 2, GAP = CS / 2, H = C.wallBlocks;
  const tb = blocksFor(scene);

  // ---- place the grid: centred on the fight, pushed away so the caster starts outside it
  const { center } = focus(caster, aim, 12);
  let away = norm(flat(sub(center, caster.location)));
  if (distXZ(center, caster.location) < 0.5) away = aim.forward;
  const d0 = distXZ(center, caster.location);
  const shift = clamp(HALF + C.casterMargin - d0, 0, C.maxGridShift);
  const gc = plateau(dim, up(add(center, mul(away, shift)), 4), HALF);   // on a slope: sit on the high side, never buried
  const gy = gc.y;
  const X0 = Math.floor(gc.x) - HALF, Z0 = Math.floor(gc.z) - HALF;
  const mid = (gx: number, gz: number): V3 => ({ x: X0 + gx * CS + GAP + 0.5, y: gy, z: Z0 + gz * CS + GAP + 0.5 });
  const gridMid = mid(N / 2 - 0.5, N / 2 - 0.5);
  const hover = up(gridMid, C.hoverHeight);

  // ---- grid geometry
  const inside = (c: Cell): boolean => c[0] >= 0 && c[0] < N && c[1] >= 0 && c[1] < N;
  const cellCenter = (c: Cell): V3 => ({ x: X0 + c[0] * CS + GAP + 0.5, y: gy, z: Z0 + c[1] * CS + GAP + 0.5 });
  const cellOf = (p: V3): Cell => [Math.floor((p.x - X0) / CS), Math.floor((p.z - Z0) / CS)];
  const ck = (c: Cell): string => `${c[0]},${c[1]}`;
  const edgeMid = (e: Edge): V3 => e.o === 0 ? { x: X0 + e.i * CS + GAP + 0.5, y: gy, z: Z0 + e.j * CS + 0.5 }
    : { x: X0 + e.i * CS + 0.5, y: gy, z: Z0 + e.j * CS + GAP + 0.5 };
  const edgeCells = (e: Edge): [Cell, Cell] => e.o === 0 ? [[e.i, e.j - 1], [e.i, e.j]] : [[e.i - 1, e.j], [e.i, e.j]];
  const edgeNormal = (e: Edge): V3 => e.o === 0 ? { x: 0, y: 0, z: 1 } : { x: 1, y: 0, z: 0 };
  const colsOf = (e: Edge, door: boolean): string[] => {
    const out: string[] = [];
    for (let k = 0; k <= CS; k++) {
      if (door && k === GAP) continue;
      out.push(e.o === 0 ? `${X0 + e.i * CS + k},${Z0 + e.j * CS}` : `${X0 + e.i * CS},${Z0 + e.j * CS + k}`);
    }
    return out;
  };
  const gapCenter = (e: Edge): V3 => { const [x, z] = colsOf(e, false)[GAP].split(",").map(Number); return { x: x + 0.5, y: gy, z: z + 0.5 }; };
  const between = (a: Cell, b: Cell): Edge => a[0] === b[0] ? { o: 0, i: a[0], j: Math.max(a[1], b[1]) } : { o: 1, i: Math.max(a[0], b[0]), j: a[1] };
  const ALL: Edge[] = [];
  for (let i = 0; i < N; i++) for (let j = 0; j <= N; j++) ALL.push({ o: 0, i, j });
  for (let i = 0; i <= N; i++) for (let j = 0; j < N; j++) ALL.push({ o: 1, i, j });
  /** The two yaws a wall on this edge may face; front (dream wallpaper) toward a point when given. */
  const yawsOf = (e: Edge): [number, number] => e.o === 0 ? [0, 180] : [-90, 90];
  const frontYaw = (e: Edge, toward: V3): number => {
    const m = edgeMid(e);
    return e.o === 0 ? (toward.z > m.z ? 0 : 180) : (toward.x > m.x ? -90 : 90);
  };
  const nearestYaw = (e: Edge, cur: number): number => {
    const [a, b] = yawsOf(e);
    return Math.abs(angleDelta(cur, a)) <= Math.abs(angleDelta(cur, b)) ? a : b;
  };

  // ---- corridor frame: "dep" 0 is the row on the far side of the grid (away from the caster)
  const alongZ = Math.abs(away.z) >= Math.abs(away.x);
  const farPos = alongZ ? away.z > 0 : away.x > 0;
  const cellAt = (lat: number, dep: number): Cell => {
    const d = farPos ? N - 1 - dep : dep;
    return alongZ ? [lat, d] : [d, lat];
  };
  const farEdge = (lat: number, dep: number): Edge => {
    const g = farPos ? N - dep : dep;
    return alongZ ? { o: 0, i: lat, j: g } : { o: 1, i: g, j: lat };
  };
  const sideEdges = (lat: number, dep: number): Edge[] => {
    const c = cellAt(lat, dep);
    return alongZ ? [{ o: 1, i: c[0], j: c[1] }, { o: 1, i: c[0] + 1, j: c[1] }] : [{ o: 0, i: c[0], j: c[1] }, { o: 0, i: c[0], j: c[1] + 1 }];
  };

  // ---- temporary collision: reference-counted barrier columns (corners are shared between walls)
  const refs = new Map<string, number>();
  const placed = new Set<string>();
  const pending = new Set<string>();
  const colY = new Map<string, number | null>();
  function baseY(k: string): number | null {
    if (colY.has(k)) return colY.get(k)!;
    const [x, z] = k.split(",").map(Number);
    const y = groundBelow(dim, { x: x + 0.5, y: gy + 4, z: z + 0.5 }, 12).y;
    const v = Math.abs(y - gy) > C.maxColumnStep ? null : Math.floor(y);
    colY.set(k, v);
    return v;
  }
  function occupants(k: string): Entity[] {
    const [x, z] = k.split(",").map(Number);
    let found: Entity[] = [];
    try {
      found = dim.getEntities({ location: { x: x + 0.5, y: gy + 1, z: z + 0.5 }, maxDistance: 3, excludeFamilies: ["grimoire_construct"] });
    } catch { return []; }
    return found.filter((e) => isAlive(e) && e.typeId !== "minecraft:item" &&
      Math.abs(e.location.x - (x + 0.5)) < C.occupyRadius + 0.3 && Math.abs(e.location.z - (z + 0.5)) < C.occupyRadius + 0.3);
  }
  function tryPlace(k: string): void {
    const y = baseY(k);
    if (y === null || placed.has(k)) { pending.delete(k); return; }
    const occ = occupants(k);
    if (occ.length) {
      pending.add(k);
      const [x, z] = k.split(",").map(Number);
      for (const e of occ) if (e.typeId !== "minecraft:player") shove(e, sub(e.location, { x: x + 0.5, y: e.location.y, z: z + 0.5 }), C.pushH, C.pushV);
      return;
    }
    const [x, z] = k.split(",").map(Number);
    tb.column(x, y, z, H);
    placed.add(k);
    pending.delete(k);
  }
  function claim(k: string): void {
    const n = (refs.get(k) ?? 0) + 1;
    refs.set(k, n);
    if (n === 1) tryPlace(k);
  }
  function release(k: string): void {
    const n = (refs.get(k) ?? 0) - 1;
    if (n > 0) { refs.set(k, n); return; }
    refs.delete(k);
    pending.delete(k);
    if (placed.delete(k)) {
      const [x, z] = k.split(",").map(Number);
      tb.removeColumn(x, baseY(k) ?? gy, z, H);
    }
  }
  function setCols(w: Wall, cols: string[]): void {
    const next = new Set(cols);
    for (const k of w.cols) if (!next.has(k)) release(k);
    const prev = new Set(w.cols);
    for (const k of cols) if (!prev.has(k)) claim(k);
    w.cols = cols;
  }
  /** Enemies standing on an arriving wall's line are pushed off to the side they already stand on. */
  function clearLine(e: Edge): void {
    const m = edgeMid(e), n = edgeNormal(e);
    for (const h of hostiles(dim, m, GAP + 1.5, caster)) {
      const rel = sub(h.location, m);
      const along = e.o === 0 ? Math.abs(rel.x) : Math.abs(rel.z);
      const perp = e.o === 0 ? rel.z : rel.x;
      if (along > GAP + 0.8 || Math.abs(perp) > 1.4) continue;
      shove(h, mul(n, perp >= 0 ? 1 : -1), C.pushH, C.pushV);
    }
  }

  // ---- reading the battlefield
  function survey(): { foes: Entity[]; foeCells: Map<string, number>; allyCells: Set<string>; players: Player[] } {
    const foes = hostiles(dim, gridMid, C.radius, caster).filter((e) => inside(cellOf(e.location)));
    const foeCells = new Map<string, number>();
    for (const e of foes) { const k = ck(cellOf(e.location)); foeCells.set(k, (foeCells.get(k) ?? 0) + 1); }
    const players = allies(dim, gridMid, C.radius, caster);
    const allyCells = new Set<string>();
    for (const p of players) {
      const c = cellOf(p.location);
      if (inside(c)) allyCells.add(ck(c));
      // a player standing on a grid line touches both neighbouring cells
      for (const [dx, dz] of [[0.9, 0], [-0.9, 0], [0, 0.9], [0, -0.9]]) {
        const c2 = cellOf({ x: p.location.x + dx, y: 0, z: p.location.z + dz });
        if (inside(c2)) allyCells.add(ck(c2));
      }
    }
    return { foes, foeCells, allyCells, players };
  }

  /** The purposeful layout for one rearrangement. */
  function plan(round: number): Plan {
    const { foeCells, allyCells, players } = survey();
    const W = C.score;
    // hostile groups: farthest-point seeds over occupied cells, Voronoi regions over the grid
    const occ = [...foeCells.keys()].map((k) => k.split(",").map(Number) as Cell);
    const seeds: Cell[] = [];
    if (occ.length) {
      occ.sort((a, b) => distXZ(cellCenter(a), caster.location) - distXZ(cellCenter(b), caster.location));
      seeds.push(occ[0]);
      while (seeds.length < C.maxGroups) {
        let best: Cell | null = null, bd = 2.5;
        for (const c of occ) {
          const d = Math.min(...seeds.map((s) => Math.abs(s[0] - c[0]) + Math.abs(s[1] - c[1])));
          if (d > bd) { bd = d; best = c; }
        }
        if (!best) break;
        seeds.push(best);
      }
    }
    const region = (c: Cell): number => {
      let r = -1, bd = 1e9;
      seeds.forEach((s, k) => { const d = Math.abs(s[0] - c[0]) + Math.abs(s[1] - c[1]); if (d < bd) { bd = d; r = k; } });
      return r;
    };
    // the controllable corridor, its looping door and its start; it alternates sides every rearrangement
    const lat = clamp(Math.floor(N / 2) - 1 + (round % 2), 0, N - 1);
    const loopEdge = farEdge(lat, 0);
    const start = cellAt(lat, C.routeLen - 1);
    const corridor = new Set<string>(), keepOpen = new Set<string>();
    for (let d = 0; d < C.routeLen; d++) for (const s of sideEdges(lat, d)) corridor.add(ek(s));
    for (let d = 1; d <= C.routeLen; d++) keepOpen.add(ek(farEdge(lat, d)));
    const toCaster = mul(away, -1);

    const score = new Map<string, number>();
    const cand: { e: Edge; s: number }[] = [];
    for (const e of ALL) {
      const key = ek(e);
      if (keepOpen.has(key)) continue;
      // never bring a wall onto a player's column
      const nearPlayer = colsOf(e, false).some((k) => {
        const [x, z] = k.split(",").map(Number);
        return players.some((p) => Math.abs(p.location.x - (x + 0.5)) < C.playerClear + 0.5 && Math.abs(p.location.z - (z + 0.5)) < C.playerClear + 0.5);
      });
      if (nearPlayer) continue;
      const [a, b] = edgeCells(e);
      const n = edgeNormal(e);
      let s = hash01(round + 1, key) * W.jitter;
      if (inside(a) && inside(b) && seeds.length > 1 && region(a) !== region(b)) s += W.separate;
      for (const [c, sign] of [[a, 1], [b, -1]] as [Cell, number][]) {
        if (!inside(c) || !foeCells.has(ck(c))) continue;
        const out = mul(n, sign);
        if (out.x * toCaster.x + out.z * toCaster.z > 0.5) s += W.blockApproach;
      }
      if (corridor.has(key)) s += W.corridor;
      if (!inside(a) || !inside(b)) {
        const out = inside(a) ? n : mul(n, -1);
        s += out.x * toCaster.x + out.z * toCaster.z > 0.7 ? W.frontLine : W.perimeter;
      }
      if ((inside(a) && allyCells.has(ck(a))) || (inside(b) && allyCells.has(ck(b)))) s += W.nearAlly;
      if (key === ek(loopEdge)) s = 1000;
      score.set(key, s);
      cand.push({ e, s });
    }
    cand.sort((p, q) => q.s - p.s);
    const walls = new Map<string, { e: Edge; door: boolean }>();
    for (const c of cand.slice(0, C.wallCount)) walls.set(ek(c.e), { e: c.e, door: false });
    return { walls, loopKey: ek(loopEdge), start, score };
  }

  /** Doors: the looping door, every wall touching a player's cell, and enough doors that no cell is sealed. */
  function assignDoors(walls: Map<string, { e: Edge; door: boolean }>, loopKey: string): void {
    const { allyCells } = survey();
    for (const [key, w] of walls) {
      const [a, b] = edgeCells(w.e);
      w.door = key === loopKey || (inside(a) && allyCells.has(ck(a))) || (inside(b) && allyCells.has(ck(b)));
    }
    for (let guard = 0; guard < 40; guard++) {
      const blocked = (e: Edge): boolean => { const w = walls.get(ek(e)); return !!w && !w.door; };
      const seen = new Set<string>();
      const queue: Cell[] = [];
      for (let k = 0; k < N; k++) {
        const per: [Cell, Edge][] = [[[k, 0], { o: 0, i: k, j: 0 }], [[k, N - 1], { o: 0, i: k, j: N }], [[0, k], { o: 1, i: 0, j: k }], [[N - 1, k], { o: 1, i: N, j: k }]];
        for (const [c, e] of per) if (!blocked(e) && !seen.has(ck(c))) { seen.add(ck(c)); queue.push(c); }
      }
      while (queue.length) {
        const c = queue.pop()!;
        for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const n: Cell = [c[0] + dx, c[1] + dz];
          if (!inside(n) || seen.has(ck(n)) || blocked(between(c, n))) continue;
          seen.add(ck(n));
          queue.push(n);
        }
      }
      if (seen.size >= N * N) return;
      // open the sealed pocket on the side that leads away from the caster
      let best: { w: { e: Edge; door: boolean }; s: number } | null = null;
      for (const w of walls.values()) {
        if (w.door) continue;
        const [a, b] = edgeCells(w.e);
        const ia = inside(a) && !seen.has(ck(a)), ib = inside(b) && !seen.has(ck(b));
        if (ia === ib) continue;
        const out = mul(edgeNormal(w.e), ia ? 1 : -1);
        const s = out.x * away.x + out.z * away.z;
        if (!best || s > best.s) best = { w, s };
      }
      if (!best) return;
      best.w.door = true;
    }
  }

  // ======================================================================================= actors
  const T = {
    open: secs(L.land),
    opened: secs(L.land + L.open),
    unfold: secs(L.land + L.open) + 4,
    wallsOut: secs(L.land + L.open) + 8,
    active: secs(L.land + L.open) + 24,
  };
  T.active = Math.max(T.active, T.wallsOut + Math.ceil(C.wallCount / 2) + 18);
  const tFold = T.active + C.activeTicks;
  const tClose = tFold + 34;
  const tVanish = tClose + secs(L.close);
  const tEnd = tVanish + secs(L.vanish) + 4;

  const faceCaster = yawOf(sub(caster.location, gc));
  const house = scene.spawn("dn_house_doll", gc, { yaw: faceCaster, state: HS.land });
  let houseYaw = faceCaster;
  let housePos: V3 = { ...gc };
  sound(dim, "dn_house_land", gc, 1.2);
  scene.at(9, () => { particle(dim, "fx_dust", up(gc, 0.3)); burst(dim, "dn_house_dust", up(gc, 0.5), 3, 6); });
  scene.at(T.open, () => {
    house.state(HS.open);
    sound(dim, "dn_house_windup", gc, 1.0);
    sound(dim, "dn_house_open", gc, 1.0);
  });
  scene.at(T.open + 18, () => burst(dim, "dn_house_key", up(gc, 5), 3, 8));
  scene.at(T.opened, () => house.state(HS.opened));
  scene.at(T.unfold, () => {
    house.state(HS.unfold);
    sound(dim, "dn_house_unfold", gc, 1.2);
    burst(dim, "dn_house_scrap", up(gc, 5), 3, 6);
  });
  scene.at(T.unfold + secs(L.unfold), () => house.state(HS.spread));
  scene.span(T.unfold, T.unfold + 24, (p) => { housePos = lerp(gc, hover, smooth(p)); house.move(housePos); });

  // ---- walls fly out of the house as flat pages and pop up on the grid
  const first = plan(0);
  assignDoors(first.walls, first.loopKey);
  let loopKey = first.loopKey;
  let loopStart: Cell = first.start;
  const walls: Wall[] = [];
  [...first.walls.values()].forEach((t, k) => {
    const at = T.wallsOut + Math.floor(k / 2);
    scene.at(at, () => {
      const base = BASE_KINDS[k % BASE_KINDS.length];
      const yaw = frontYaw(t.e, caster.isValid ? caster.location : gc);
      const a = scene.spawn("dn_house_wall", housePos, { yaw, state: WS.fly, kind: t.door ? KIND_DOOR : base });
      const w: Wall = { a, key: ek(t.e), e: t.e, door: t.door, base, cols: [], pos: { ...housePos }, yaw, arrived: false };
      walls.push(w);
      const from = { ...housePos }, to = edgeMid(t.e);
      const ctrl = up(lerp(from, to, 0.5), 5);
      scene.span(at, at + 16, (p) => { w.pos = bezier(from, ctrl, to, smooth(p)); w.a.move(w.pos, yaw + (1 - p) * 360); });
      scene.at(at + 13, () => clearLine(t.e));
      scene.at(at + 16, () => {
        w.a.state(WS.rise);
        w.arrived = true;
        setCols(w, colsOf(t.e, t.door));
        line(dim, "dn_house_dust", up(edgeMid(t.e), 0.2), up(edgeMid(t.e), 0.3), 1);
        if (k % 3 === 0) sound(dim, "dn_house_settle", to, 0.8, 0.9 + (k % 5) * 0.06);
      });
      scene.at(at + 16 + secs(L.wRise), () => { if (!w.a.valid) return; w.a.state(WS.idle); });
    });
  });

  // ---- living furniture tumbles out of the rooms
  const FURN = ["dn_house_bed", "dn_house_clock", "dn_house_chandelier", "dn_house_table"];
  const furn: Furn[] = [];
  function furnitureCells(round: number): Cell[] {
    const { foeCells, allyCells } = survey();
    const used = new Set<string>(allyCells);
    const pick = (c: Cell | null): Cell | null => (c && inside(c) && !used.has(ck(c)) ? (used.add(ck(c)), c) : null);
    const busy = [...foeCells.entries()].sort((a, b) => b[1] - a[1]).map(([k]) => k.split(",").map(Number) as Cell);
    const pattern: Cell[] = [];
    for (let k = 0; k < N * N; k++) {
      const h = Math.floor(hash01(round * 31 + k, "furn") * N * N);
      pattern.push([h % N, Math.floor(h / N)]);
    }
    const next = (): Cell => { for (const c of pattern) { const p = pick(c); if (p) return p; } return [0, 0]; };
    const chand = pick(busy[0] ?? null) ?? next();
    const bed = pick(busy[1] ?? null) ?? next();
    const clock = pick(loopStart) ?? next();
    const table = next();
    return [bed, clock, chand, table];
  }
  const fcells0 = furnitureCells(0);
  FURN.forEach((id, k) => {
    const at = T.wallsOut + 10 + k * 3;
    scene.at(at, () => {
      const f: Furn = { a: scene.spawn(id, housePos, { yaw: faceCaster, state: FS.appear }), id, pos: { ...housePos }, cell: fcells0[k] };
      furn.push(f);
      const from = { ...housePos }, to = cellCenter(fcells0[k]);
      scene.at(at + 8, () => f.a.state(FS.move));
      scene.span(at, at + 22, (p) => { f.pos = bezier(from, up(lerp(from, to, 0.5), 6), to, smooth(p)); f.a.move(f.pos, faceCaster + p * 180); });
      scene.at(at + 22, () => { f.a.state(FS.idle); particle(dim, "dn_house_glow", up(to, 1)); burst(dim, "dn_house_dust", up(to, 0.4), 1, 2); });
    });
  });
  const F = (id: string): Furn | undefined => furn.find((f) => f.id === id);

  // ======================================================================================= rearrangements
  function moveWall(w: Wall, to: Edge, door: boolean, t0: number): void {
    const from = { ...w.pos }, fromYaw = w.yaw, dest = edgeMid(to);
    let pivot: V3 | null = null;
    if (w.e && w.e.o !== to.o) {      // perpendicular and sharing a corner: the room turns a quarter around it
      const corners = (e: Edge): Cell[] => e.o === 0 ? [[e.i, e.j], [e.i + 1, e.j]] : [[e.i, e.j], [e.i, e.j + 1]];
      const shared = corners(w.e).find((c) => corners(to).some((d) => d[0] === c[0] && d[1] === c[1]));
      if (shared) pivot = { x: X0 + shared[0] * CS + 0.5, y: gy, z: Z0 + shared[1] * CS + 0.5 };
    }
    const toYaw = nearestYaw(to, fromYaw);
    const dist = distXZ(from, dest);
    const dur = pivot ? 14 : Math.round(clamp(10 + dist * 1.1, 12, 26));
    let a0 = 0, da = 0;
    if (pivot) {
      a0 = Math.atan2(from.z - pivot.z, from.x - pivot.x);
      da = Math.atan2(dest.z - pivot.z, dest.x - pivot.x) - a0;
      while (da > Math.PI) da -= 2 * Math.PI;
      while (da < -Math.PI) da += 2 * Math.PI;
    }
    const yawSpan = pivot ? (da * 180) / Math.PI : angleDelta(fromYaw, toYaw);
    w.arrived = false;
    scene.at(t0 - C.telegraphTicks, () => line(dim, "dn_house_chalk", up(edgeMid(to), 0.15), up(gapCenter(to), 0.15), 2));
    scene.at(t0 - C.telegraphTicks, () => {
      const cs = colsOf(to, false);
      const [x1, z1] = cs[0].split(",").map(Number), [x2, z2] = cs[cs.length - 1].split(",").map(Number);
      line(dim, "dn_house_chalk", { x: x1 + 0.5, y: gy + 0.15, z: z1 + 0.5 }, { x: x2 + 0.5, y: gy + 0.15, z: z2 + 0.5 }, 4);
    });
    scene.at(t0, () => {
      setCols(w, []);
      w.a.state(WS.slide);
      sound(dim, "dn_house_slide", from, 0.9, 0.9 + hash01(t0, "s") * 0.25);
      particle(dim, "dn_house_dust", up(from, 0.3));
    });
    scene.span(t0, t0 + dur, (p) => {
      const q = smooth(p);
      if (pivot) {
        const ang = a0 + da * q;
        w.pos = { x: pivot.x + Math.cos(ang) * GAP, y: gy, z: pivot.z + Math.sin(ang) * GAP };
      } else {
        w.pos = up(lerp(from, dest, q), Math.sin(Math.PI * q) * (dist > CS + 1 ? 0.8 : 0));
      }
      w.yaw = fromYaw + yawSpan * q;
      w.a.move(w.pos, w.yaw);
    });
    scene.at(t0 + dur - 3, () => clearLine(to));
    scene.at(t0 + dur, () => {
      w.yaw = toYaw;
      w.pos = dest;
      w.a.move(dest, toYaw);
      w.door = door;
      w.a.kind(door ? KIND_DOOR : w.base);
      setCols(w, colsOf(to, door));
      w.arrived = true;
      w.a.state(WS.settle);
      sound(dim, "dn_house_settle", dest, 0.9, 0.9 + hash01(t0, "k") * 0.3);
      particle(dim, "dn_house_dust", up(dest, 0.3));
    });
    scene.at(t0 + dur + secs(L.wSettle), () => { if (w.arrived) w.a.state(WS.idle); });
  }

  /** A door leaves one wall and hops to another. */
  function hopDoor(fromW: Wall, toW: Wall, t0: number): void {
    scene.at(t0, () => {
      if (!fromW.e || !toW.e) return;
      const a = gapCenter(fromW.e), b = gapCenter(toW.e);
      fromW.door = false;
      fromW.a.kind(fromW.base);
      setCols(fromW, colsOf(fromW.e, false));
      sound(dim, "dn_house_pop", a, 1.0, 1.1);
      particle(dim, "dn_house_glow", up(a, 1.4));
      const d = scene.spawn("dn_house_door", a, { yaw: fromW.yaw, state: DS.hop });
      const dur = Math.round(clamp(10 + distXZ(a, b) * 0.6, 12, 20));
      const ctrl = up(lerp(a, b, 0.5), 4 + distXZ(a, b) * 0.2);
      scene.span(scene.tick, scene.tick + dur, (p) => d.move(bezier(a, ctrl, b, p), fromW.yaw + p * 180));
      scene.after(dur, () => {
        if (toW.e) {
          toW.door = true;
          toW.a.kind(KIND_DOOR);
          setCols(toW, colsOf(toW.e, true));
        }
        d.state(DS.pop);
        sound(dim, "dn_house_pop", b, 1.0, 0.85);
        burst(dim, "dn_house_key", up(b, 1.2), 0.8, 3);
      });
      scene.after(dur + secs(L.doorPop), () => scene.despawn(d));
    });
  }

  function rearrange(round: number, t: number): void {
    const p = plan(round);
    // pair walls that must leave with places that need a wall
    const target = p.walls;
    let leaving = walls.filter((w) => w.key === null || !target.has(w.key));
    const occupied = new Set(walls.map((w) => w.key));
    let arriving = [...target.keys()].filter((k) => !occupied.has(k));
    arriving.sort((a, b) => (p.score.get(b) ?? 0) - (p.score.get(a) ?? 0));
    leaving.sort((a, b) => (p.score.get(a.key ?? "") ?? -99) - (p.score.get(b.key ?? "") ?? -99));
    const nMoves = Math.min(leaving.length, arriving.length, C.maxMovesPerShift);
    arriving = arriving.slice(0, nMoves);
    leaving = leaving.slice(0, nMoves);
    const moves: { w: Wall; e: Edge }[] = [];
    for (const key of arriving) {
      const e = pk(key), m = edgeMid(e);
      let bi = 0, bd = 1e9;
      leaving.forEach((w, k) => {
        let d = distXZ(w.pos, m);
        if (w.e && w.e.o !== e.o && d < GAP * 1.5 + 0.1) d -= 2; // favour quarter turns
        if (d < bd) { bd = d; bi = k; }
      });
      moves.push({ w: leaving[bi], e });
      leaving.splice(bi, 1);
    }
    // the final layout decides the doors
    const final = new Map<string, { e: Edge; door: boolean }>();
    for (const w of walls) if (w.e && !moves.some((m) => m.w === w)) final.set(w.key!, { e: w.e, door: false });
    for (const m of moves) final.set(ek(m.e), { e: m.e, door: false });
    assignDoors(final, p.loopKey);
    loopKey = final.has(p.loopKey) ? p.loopKey : loopKey;
    loopStart = p.start;
    // walls that stay but open or close a door: a door hops between them
    const gain = walls.filter((w) => !moves.some((m) => m.w === w) && w.key && final.get(w.key)!.door && !w.door);
    const lose = walls.filter((w) => !moves.some((m) => m.w === w) && w.key && !final.get(w.key)!.door && w.door);
    for (let k = 0; k < Math.max(gain.length, lose.length); k++) {
      const g = gain[k], l = lose[k];
      if (g && l) { hopDoor(l, g, t + 4 + k * 3); continue; }
      const w = (g ?? l)!;
      scene.at(t + 4 + k * 3, () => {
        if (!w.e) return;
        w.door = !!g;
        w.a.kind(w.door ? KIND_DOOR : w.base);
        setCols(w, colsOf(w.e, w.door));
        sound(dim, "dn_house_pop", gapCenter(w.e), 0.8, w.door ? 1.2 : 0.8);
        particle(dim, "dn_house_glow", up(gapCenter(w.e), 1.4));
      });
    }
    moves.forEach((m, k) => {
      m.w.key = ek(m.e);
      moveWall(m.w, m.e, final.get(ek(m.e))!.door, t + k * C.moveStagger);
      m.w.e = m.e;
    });
  }

  const shiftTicks: number[] = [];
  for (let t = T.active + C.shiftEvery; t < tFold - 10; t += C.shiftEvery) shiftTicks.push(t);
  scene.at(T.active, () => {
    sound(dim, "dn_house_lullaby", hover, 1.0);
    ring(dim, "dn_house_note", up(hover, 2), 4, 6);
  });
  shiftTicks.forEach((t, r) => {
    scene.at(t - C.telegraphTicks, () => rearrange(r + 1, t));
    scene.at(t, () => {
      house.state(r % 2 === 0 ? HS.shiftA : HS.shiftB);
      sound(dim, "dn_house_lullaby_warp", hover, 1.0, 1 - r * 0.05);
      burst(dim, "dn_house_scrap", up(hover, 3), 3, 6);
    });
    const y0 = houseYaw;
    houseYaw += 90;
    scene.span(t, t + 14, (p) => house.move(hover, y0 + 90 * smooth(p)));
    // furniture changes rooms too
    scene.at(t, () => {
      const cells = furnitureCells(r + 1);
      FURN.forEach((id, k) => relocate(F(id), cells[k], t + k * 2));
      F("dn_house_bed")?.a.state(FS.act);
      const clock = F("dn_house_clock");
      if (clock) sound(dim, "dn_house_chime", clock.pos, 0.9);
    });
    // the chandelier lets its crystals fall where it now hangs
    scene.at(t + 20, () => {
      const ch = F("dn_house_chandelier");
      if (!ch?.a.valid) return;
      const at = { ...ch.pos };
      const warn = scene.spawn("telegraph", up(at, 0.05), { kind: 1, size: C.crystalRadius, state: 1 });
      scene.after(10, () => ch.a.state(FS.act));
      scene.after(19, () => {
        warn.state(3);
        sound(dim, "dn_house_crystal", at, 1.0);
        particle(dim, "dn_house_crystal", up(at, 0.6));
        particle(dim, "dn_house_tick", up(at, 0.1));
        for (const e of hostiles(dim, at, C.crystalRadius + 0.5, caster)) damage(e, C.crystalDamage, caster);
      });
      scene.after(27, () => scene.despawn(warn));
      scene.after(10 + secs(L.fAct), () => ch.a.state(FS.idle));
    });
  });

  function relocate(f: Furn | undefined, cell: Cell, t0: number): void {
    if (!f) return;
    const dur = 18;
    scene.at(t0, () => {
      if (!f.a.valid) return;
      const from = { ...f.pos }, to = cellCenter(cell);
      const dir = sub(to, from);
      const yaw = distXZ(from, to) > 0.3 ? yawOf(dir) : undefined;
      f.cell = cell;
      f.a.state(FS.move);
      if (f.id === "dn_house_table") sound(dim, "dn_house_scuttle", from, 0.9);
      const bumped = new Set<string>();
      scene.span(scene.tick, scene.tick + dur, (p) => {
        f.pos = up(lerp(from, to, smooth(p)), f.id === "dn_house_clock" ? 0 : Math.sin(Math.PI * p) * 0.6);
        f.a.move(f.pos, yaw);
        if (f.id !== "dn_house_table") return;
        for (const e of hostiles(dim, f.pos, C.tableRadius, caster)) {
          if (bumped.has(e.id)) continue;
          bumped.add(e.id);
          damage(e, C.tableDamage, caster);
          shove(e, dir, C.tablePush, 0.3);
        }
      });
      scene.after(dur, () => { if (f.a.valid) f.a.state(FS.idle); });
    });
  }

  // ---- furniture auras and the clock that drifts out of time
  scene.every(20, (el) => {
    const bed = F("dn_house_bed");
    if (bed?.a.valid) {
      for (const e of hostiles(dim, bed.pos, C.bedRadius, caster)) effect(e, "slowness", C.bedSlowTicks, C.bedSlowAmp);
      particle(dim, "dn_house_sleep", up(bed.pos, 2.2));
      if (el % 60 === 0) sound(dim, "dn_house_bed", bed.pos, 0.7, 0.9 + (el % 120 === 0 ? 0.1 : 0));
    }
    const clock = F("dn_house_clock");
    if (clock?.a.valid) for (const e of hostiles(dim, clock.pos, C.clockRadius, caster)) effect(e, "slowness", C.clockSlowTicks, 0);
  }, T.active, tFold);
  for (let t = T.active, k = 0; t < tFold; k++) {
    const tick = t;
    scene.at(tick, () => {
      const clock = F("dn_house_clock");
      if (!clock?.a.valid) return;
      sound(dim, "dn_house_tick", clock.pos, 0.7, 1 - (k % 7) * 0.03);
      if (k % 3 === 0) particle(dim, "dn_house_tick", up(clock.pos, 0.1));
    });
    t += 10 + Math.round(4 * Math.sin(k * 0.9));
  }

  // ---- the corridor that loops: enemies stepping through its door come out at its start again
  const looped = new Map<string, number>();
  scene.every(2, () => {
    const w = walls.find((x) => x.key === loopKey && x.arrived && x.door && x.e);
    if (!w || !w.e) return;
    const g = gapCenter(w.e);
    for (const e of hostiles(dim, up(g, 1), C.loopRadius + 1, caster)) {
      if (distXZ(e.location, g) > C.loopRadius || Math.abs(e.location.y - gy) > 2.5) continue;
      if ((looped.get(e.id) ?? -999) > scene.tick - C.loopCooldown) continue;
      let dest = cellCenter(loopStart);
      if (allies(dim, dest, 2, caster).length) dest = cellCenter(cellOf(gridMid));
      looped.set(e.id, scene.tick);
      particle(dim, "dn_house_loop", up(g, 1));
      drag(e, up(dest, 0.1));
      effect(e, "slowness", C.loopSlowTicks, 1);
      particle(dim, "dn_house_loop", up(dest, 1));
      sound(dim, "dn_house_loop", dest, 1.0);
      sound(dim, "dn_house_loop", g, 0.7, 1.15);
    }
    if (scene.tick % 10 === 0) particle(dim, "dn_house_chalk", up(g, 1.5));
  }, T.active, tFold);

  // ---- deferred barrier columns (something was standing there) are retried
  scene.every(C.retryEvery, () => { for (const k of [...pending]) if (refs.has(k)) tryPlace(k); else pending.delete(k); }, T.wallsOut, tFold);

  // ======================================================================================= fold away
  scene.at(tFold, () => {
    for (const w of walls) { setCols(w, []); w.arrived = false; w.a.state(WS.fold); }
    pending.clear();
    house.state(HS.fold);
    sound(dim, "dn_house_fold", hover, 1.2);
    sound(dim, "dn_house_lullaby", hover, 0.8, 0.9);
    for (const f of furn) f.a.state(FS.move);
  });
  scene.span(tFold + 4, tClose - 2, (p) => { housePos = lerp(hover, gc, smooth(p)); house.move(housePos); });
  scene.at(tFold + secs(L.wFold), () => {
    walls.forEach((w, k) => {
      const t0 = tFold + secs(L.wFold) + Math.floor(k / 2);
      scene.at(t0, () => w.a.state(WS.fly));
      const from = { ...w.pos };
      scene.span(t0, t0 + 14, (p) => w.a.move(bezier(from, up(lerp(from, housePos, 0.5), 5), up(housePos, 3), smooth(p)), w.yaw + p * 270));
      scene.at(t0 + 14, () => { particle(dim, "dn_house_scrap", up(housePos, 3)); scene.despawn(w.a); });
    });
    furn.forEach((f, k) => {
      const t0 = tFold + 2 + k * 2;
      const from = { ...f.pos };
      scene.span(t0, t0 + 18, (p) => f.a.move(bezier(from, up(lerp(from, housePos, 0.5), 6), up(housePos, 2), smooth(p))));
      scene.at(t0 + 18 - secs(L.fVanish), () => f.a.state(FS.vanish));
      scene.at(t0 + 18, () => scene.despawn(f.a));
    });
  });
  scene.at(tClose, () => {
    house.move(gc, faceCaster);
    house.state(HS.close);
    sound(dim, "dn_house_open", gc, 0.8, 0.85);
  });
  scene.at(tClose + 13, () => { sound(dim, "dn_house_clack", gc, 1.2); particle(dim, "fx_dust", up(gc, 0.3)); });
  scene.at(tVanish, () => { house.state(HS.vanish); burst(dim, "dn_house_note", up(gc, 3), 2.5, 6); });
  scene.at(tVanish + secs(L.vanish) - 2, () => { particle(dim, "dn_house_glow", up(gc, 1.5)); burst(dim, "dn_house_key", up(gc, 1.5), 1.2, 5); });
  scene.endAt(tEnd);
});
