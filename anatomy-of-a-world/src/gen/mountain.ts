/**
 * THE MIGRATING MOUNTAIN — procedural body generator.
 *
 * Pure module (no @minecraft imports). Produces the block body of the boss in
 * its own void dimension: dorsal biome (forest terraces, snow crags,
 * waterfalls), living strata cliffs, the Organ Cavern with the Lithic Heart
 * cradle, the Lithic Musculature underside, the three Resonance Node sites,
 * and the Phase 2 "Unfolded World" disk. The encounter script also uses the
 * column functions here to re-render terrain while abilities deform it.
 *
 * Axes: +X is the mountain's front (direction of migration), Y up, Z width.
 */
import { Perlin, Rng, hash2, hash3, clamp, lerp, smoothstep } from "./noise.js";
import * as P from "./palette.js";

export interface V3 {
  x: number;
  y: number;
  z: number;
}

export const MM = {
  dimensionId: "anatomy:migration_path",
  seed: 1001,
  /** Ellipse semi-axes of the body footprint (length 116, width 92). */
  A: 58,
  B: 46,
  /** Height reference: dorsal heights are measured from here. */
  baseY: 118,
  /** Underside height at the rim. */
  rimUnderY: 121,
  /** Cloud sea / leg tips. */
  cloudY: 100,
  /** Voxel grid bounds (inclusive min, size). */
  grid: { x0: -72, y0: 100, z0: -84, sx: 144, sy: 90, sz: 144 },
  cavern: { x: 0, y: 151, z: 0, rx: 24, ry: 11, rz: 20, floorY: 141 },
  /** Lithic Heart entity feet position (its model is centred ~3 blocks above). */
  heart: { x: 0.5, y: 148.5, z: 0.5 },
  /** Phase 2 disk. */
  disk: { y: 146, wellR: 4, periR: 9, ring2: 18, ribEnd: 30, outerR: 34, mantleY: 138, ribs: 10 },
  legCount: 14,
  arrival: { x: -4, y: 125, z: -68, r: 8 },
  shaft: { x: -10, z: -8, r: 3 },
  gallery: { y: 124, rIn: 5, rOut: 8 },
  /** Snow line (absolute Y). */
  snowY: 171,
} as const;

export const enum ColFlag {
  BODY = 1,
  STATIC = 2, // never deformed by abilities (water, node sites, bridge)
  PATH = 4,
  TREE = 8,
  WATER = 16,
  SNOW = 32,
  NODE = 64,
  CAVE = 128, // cavern / tunnel below: limited deformation
}

export interface TreeInfo {
  x: number;
  z: number;
  /** y of the ground block under the trunk. */
  groundY: number;
  kind: 0 | 1 | 2; // spruce, oak, azalea
  height: number;
  seed: number;
}

export interface NodeSite {
  id: "dorsal" | "cavern" | "root";
  name: string;
  /** Entity feet position. */
  pos: V3;
  /** Where players are teleported to if they need a safe spot near it. */
  safe: V3;
}

export interface LegSite {
  index: number;
  /** Attachment point (entity position). */
  pos: V3;
  /** Yaw in degrees (Bedrock convention: 0 = +Z, 90 = -X). */
  yaw: number;
  /** Outward unit direction. */
  dir: { x: number; z: number };
  /** Ellipse parameter angle in radians. */
  t: number;
}

export interface WaterfallSite {
  source: V3;
  kind: "basin" | "void";
}

/** Pre-generated mountain data (decoded byte arrays + metadata lists). */
export interface MountainData {
  seed: number;
  top: Uint8Array;
  under: Uint8Array;
  caveTop: Uint8Array;
  flags: Uint8Array;
  trees: TreeInfo[];
  nodes: NodeSite[];
  legs: LegSite[];
  waterfalls: WaterfallSite[];
  pathPoints: V3[];
  summit: V3;
  tunnelMouth: V3;
}

const gauss = (x: number, z: number, cx: number, cz: number, s: number) => Math.exp(-((x - cx) * (x - cx) + (z - cz) * (z - cz)) / (2 * s * s));

/** A generated mountain: voxel grid + column metadata used at runtime. */
export class MountainModel {
  readonly g = MM.grid;
  readonly grid: Uint8Array;
  /** Base (undeformed) top solid y per column, or -32768 outside the body. */
  readonly top: Int16Array;
  /** Underside (lowest solid y) per column. */
  readonly under: Int16Array;
  readonly flags: Uint8Array;
  /** Highest y of the cavern/tunnel void under a column (or -32768). */
  readonly caveTop: Int16Array;
  readonly trees: TreeInfo[] = [];
  readonly nodes: NodeSite[] = [];
  readonly legs: LegSite[] = [];
  readonly waterfalls: WaterfallSite[] = [];
  /** Ordered list of spiral path centre points (for guidance particles). */
  readonly pathPoints: V3[] = [];
  /** Dense path samples (x, z, y) used to join the tunnel onto the path. */
  private readonly pathSamples: V3[] = [];
  summit: V3 = { x: 0, y: 0, z: 0 };
  tunnelMouth: V3 = { x: 0, y: 0, z: 0 };
  readonly noise: Perlin;
  readonly noise2: Perlin;

  constructor(readonly seed: number = MM.seed) {
    const g = this.g;
    this.grid = new Uint8Array(g.sx * g.sy * g.sz);
    this.top = new Int16Array(g.sx * g.sz).fill(-32768);
    this.under = new Int16Array(g.sx * g.sz).fill(-32768);
    this.caveTop = new Int16Array(g.sx * g.sz).fill(-32768);
    this.flags = new Uint8Array(g.sx * g.sz);
    this.noise = new Perlin(seed);
    this.noise2 = new Perlin(seed * 7 + 13);
  }

  /**
   * Rebuild the column metadata from pre-generated data (see tools/export_mountain.mjs)
   * without running the expensive generation in-game.
   */
  static fromData(d: MountainData): MountainModel {
    const m = new MountainModel(d.seed);
    m.top.set(new Int16Array(d.top.buffer, d.top.byteOffset, d.top.byteLength / 2));
    m.under.set(new Int16Array(d.under.buffer, d.under.byteOffset, d.under.byteLength / 2));
    m.caveTop.set(new Int16Array(d.caveTop.buffer, d.caveTop.byteOffset, d.caveTop.byteLength / 2));
    m.flags.set(d.flags);
    m.trees.push(...d.trees);
    m.nodes.push(...d.nodes);
    m.legs.push(...d.legs);
    m.waterfalls.push(...d.waterfalls);
    m.pathPoints.push(...d.pathPoints);
    m.summit = d.summit;
    m.tunnelMouth = d.tunnelMouth;
    return m;
  }

  // ----------------------------------------------------------------- indexing
  inGrid(x: number, y: number, z: number): boolean {
    const g = this.g;
    return x >= g.x0 && x < g.x0 + g.sx && y >= g.y0 && y < g.y0 + g.sy && z >= g.z0 && z < g.z0 + g.sz;
  }
  col(x: number, z: number): number {
    return (x - this.g.x0) * this.g.sz + (z - this.g.z0);
  }
  inCols(x: number, z: number): boolean {
    const g = this.g;
    return x >= g.x0 && x < g.x0 + g.sx && z >= g.z0 && z < g.z0 + g.sz;
  }
  idx(x: number, y: number, z: number): number {
    return this.col(x, z) * this.g.sy + (y - this.g.y0);
  }
  get(x: number, y: number, z: number): number {
    return this.inGrid(x, y, z) ? this.grid[this.idx(x, y, z)] : P.KEEP;
  }
  set(x: number, y: number, z: number, b: number): void {
    if (this.inGrid(x, y, z)) this.grid[this.idx(x, y, z)] = b;
  }
  /** Solid = anything that is not void/air/plant/water. */
  isSolid(x: number, y: number, z: number): boolean {
    const b = this.get(x, y, z);
    return b !== P.KEEP && b !== P.AIR && !NON_SOLID.has(b);
  }
  topAt(x: number, z: number): number {
    return this.inCols(x, z) ? this.top[this.col(x, z)] : -32768;
  }
  flagAt(x: number, z: number): number {
    return this.inCols(x, z) ? this.flags[this.col(x, z)] : 0;
  }

  // ----------------------------------------------------------------- shape fields
  /** Normalised elliptical radius with a wobbling rim. */
  rimRadius(x: number, z: number): number {
    const nx = x / MM.A;
    const nz = z / MM.B;
    const re = Math.sqrt(nx * nx + nz * nz);
    const a = Math.atan2(nz, nx);
    const wob = 1 + 0.05 * this.noise.noise2(Math.cos(a) * 1.7 + 3.1, Math.sin(a) * 1.7 - 7.7) + 0.02 * this.noise.noise2(x * 0.09, z * 0.09);
    return re / wob;
  }

  /** Raw dorsal height above baseY (float), NaN outside the body. */
  dorsalHeight(x: number, z: number): number {
    const re = this.rimRadius(x, z);
    if (re >= 1) return NaN;
    // Stacked mesas: each level is bounded by its own warped contour, giving
    // tall stratified cliffs with flat forested ledges between them.
    let h = 13 + 3 * (1 - re) + this.noise2.fbm2(x * 0.045 - 30, z * 0.045 + 12, 2) * 3.5;
    for (let i = 0; i < MESA_LEVELS.length; i++) {
      const L = MESA_LEVELS[i];
      const warp = this.noise.fbm2(x * 0.035 + i * 13.1, z * 0.035 - i * 7.7, 3) * L.warp + this.noise2.noise2(x * 0.11 + i * 3, z * 0.11) * 0.025;
      const k = smoothstep(L.edge + 0.012, L.edge - 0.01, re + warp);
      h += L.rise * k;
    }
    // gentle ledge relief
    h += this.noise.fbm2(x * 0.06 + 70, z * 0.06, 2) * 1.6;
    // rock spires (the snow-capped crags of the concept sheet)
    for (const S of SPIRES) {
      const d = Math.hypot(x - S.x, z - S.z) / S.r;
      if (d >= 1) continue;
      const crag = this.noise.ridged2(x * 0.16 + S.x, z * 0.16 + S.z, 3);
      const shape = Math.pow(1 - d, 0.65);
      h = Math.max(h, S.base + (S.top - S.base) * shape + (crag - 0.5) * 3.5 * shape);
    }
    // small crags along the upper ledges
    const crag = this.noise2.ridged2(x * 0.09 + 11, z * 0.09 - 4, 3);
    if (crag > 0.62) h += (crag - 0.62) * 18 * smoothstep(0.8, 0.45, re) * smoothstep(0.1, 0.3, re);
    // the front brow above the cavern tunnel
    h += gauss(x, z, 47, 0, 7) * 6;
    return h;
  }

  /** Underside height (absolute y, float) including the radial musculature ribs. */
  undersideHeight(x: number, z: number): number {
    const re = this.rimRadius(x, z);
    let u = MM.rimUnderY + 11 * (1 - Math.min(1, re * re));
    let rib = 0;
    for (const leg of this.legs) {
      const px = Math.cos(leg.t) * MM.A;
      const pz = Math.sin(leg.t) * MM.B;
      const len2 = px * px + pz * pz;
      const s = (x * px + z * pz) / len2;
      if (s < 0.15 || s > 1.08) continue;
      const qx = x - s * px;
      const qz = z - s * pz;
      const dist2 = qx * qx + qz * qz;
      rib = Math.max(rib, Math.exp(-dist2 / (2 * 2.0 * 2.0)) * smoothstep(0.15, 0.45, s));
    }
    u -= rib * 4.5;
    u += (1 - rib) * 1.5 * smoothstep(1.0, 0.6, re);
    u += this.noise2.noise2(x * 0.11, z * 0.11) * 1.2;
    return u;
  }

  /** Living strata band material at absolute (x,y,z). */
  strata(x: number, y: number, z: number): number {
    const w = y + Math.round(this.noise2.noise2(x * 0.055, z * 0.055) * 2.4);
    const band = ((w % 11) + 11) % 11;
    const h = hash3(x, y, z, 77);
    let b: number;
    switch (band) {
      case 0:
      case 1:
        b = P.STONE;
        break;
      case 2:
        b = P.ANDESITE;
        break;
      case 3:
        b = h < 0.5 ? P.STONE : P.COBBLE;
        break;
      case 4:
        b = P.TUFF;
        break;
      case 5:
        b = P.STONE;
        break;
      case 6:
        b = P.ANDESITE;
        break;
      case 7:
        b = P.CALCITE;
        break;
      case 8:
        b = P.STONE;
        break;
      case 9:
        b = y < 136 ? P.DEEPSLATE : P.TUFF;
        break;
      default:
        b = P.COBBLE;
    }
    if (h > 0.965) b = P.COBBLE;
    else if (h < 0.025) b = P.ANDESITE;
    return b;
  }

  /** Lithic musculature material near the underside / cavern walls. */
  muscle(x: number, y: number, z: number, glowChance: number): number {
    const h = hash3(x, y, z, 31);
    const n = this.noise.noise3(x * 0.15, y * 0.15, z * 0.15);
    if (h < glowChance) return h < glowChance * 0.45 ? P.VEIN_HOT : P.VEIN_GLOW;
    if (n > 0.32) return P.FLESH;
    if (n > 0.05) return P.MUSCLE;
    if (n > -0.2) return P.MANTLE_ROCK;
    return h < 0.5 ? P.GRANITE : P.DRIPSTONE;
  }

  /**
   * Material for a dorsal column at height y given the column's current top and
   * its drop to the lowest neighbour (cliff edges show bare strata, no dirt).
   * Used by the generator and by the runtime terrain renderer.
   */
  dorsalBlock(x: number, y: number, z: number, curTop: number, drop = 0): number {
    const c = this.col(x, z);
    const fl = this.flags[c];
    const d = curTop - y;
    const snowy = curTop >= MM.snowY + Math.round(this.noise2.noise2(x * 0.1, z * 0.1) * 3);
    if (d === 0) {
      if (fl & ColFlag.PATH) return P.PATH;
      if (snowy) return P.SNOW;
      if (drop >= 7 && hash2(x, z, 5) < 0.55) return this.strata(x, y, z);
      const n = this.noise.noise2(x * 0.08 + 100, z * 0.08);
      const h = hash2(x, z, 5);
      if (n > 0.45) return P.MOSS;
      if (n < -0.55) return h < 0.6 ? P.COARSE_DIRT : P.PODZOL;
      return h < 0.03 ? P.COARSE_DIRT : P.GRASS;
    }
    if (snowy) return d <= 2 ? P.SNOW : this.strata(x, y, z);
    if (fl & ColFlag.PATH) return d <= 2 ? P.DIRT : this.strata(x, y, z);
    if (drop >= 2) return this.strata(x, y, z);
    if (d <= 2) return P.DIRT;
    return this.strata(x, y, z);
  }

  /** Drop from a column's top to its lowest 4-neighbour (outside the body counts as a big drop). */
  dropAt(x: number, z: number, topOf: (x: number, z: number) => number = (a, b) => this.topAt(a, b)): number {
    const t = topOf(x, z);
    let lo = t;
    for (const [ox, oz] of NEIGH4) {
      const n = topOf(x + ox, z + oz);
      lo = Math.min(lo, n === -32768 ? t - 12 : n);
    }
    return t - lo;
  }

  // ----------------------------------------------------------------- generation
  /** Run the whole generation synchronously. */
  generate(): this {
    const it = this.generateSteps();
    while (!it.next().done) {
      /* exhaust */
    }
    return this;
  }

  /** Generation as a cooperative job (yields regularly; used with system.runJob). */
  *generateSteps(): Generator<void, void, void> {
    this.placeLegs();
    yield* this.buildHeightfields();
    this.carvePath();
    yield;
    this.placeWaterfalls();
    yield* this.fillColumns();
    this.mossifyCliffs();
    yield;
    yield* this.carveCavern();
    this.buildTunnel();
    this.buildShaftAndGallery();
    yield;
    this.buildHeartCradle();
    this.buildNodeSites();
    this.buildArrival();
    yield;
    this.writeWater();
    this.plantTrees();
    yield;
    this.decorateSurface();
  }

  private placeLegs(): void {
    for (let k = 0; k < MM.legCount; k++) {
      const t = (((360 / MM.legCount) * k) * Math.PI) / 180;
      const ex = Math.cos(t) * MM.A;
      const ez = Math.sin(t) * MM.B;
      // outward normal of the ellipse
      let nx = Math.cos(t) / MM.A;
      let nz = Math.sin(t) / MM.B;
      const nl = Math.hypot(nx, nz);
      nx /= nl;
      nz /= nl;
      const yaw = (Math.atan2(-nx, nz) * 180) / Math.PI;
      this.legs.push({
        index: k,
        pos: { x: ex * 0.9, y: MM.rimUnderY + 1.5, z: ez * 0.9 },
        yaw,
        dir: { x: nx, z: nz },
        t,
      });
    }
  }

  private *buildHeightfields(): Generator<void, void, void> {
    const g = this.g;
    for (let x = g.x0; x < g.x0 + g.sx; x++) {
      for (let z = g.z0; z < g.z0 + g.sz; z++) {
        const h = this.dorsalHeight(x, z);
        if (Number.isNaN(h)) continue;
        const c = this.col(x, z);
        const top = Math.round(MM.baseY + h);
        let u = Math.round(this.undersideHeight(x, z));
        if (u > top - 4) u = top - 4;
        this.top[c] = top;
        this.under[c] = u;
        this.flags[c] = ColFlag.BODY;
      }
      if ((x & 7) === 0) yield;
    }
  }

  /** The spiral pilgrim path from the arrival bridge to the summit crag. */
  private carvePath(): void {
    // summit: highest point near the main crag
    let best = { x: -8, z: 6, y: -1 };
    for (let x = -18; x <= 2; x++)
      for (let z = -4; z <= 16; z++) {
        const t = this.topAt(x, z);
        if (t > best.y) best = { x, z, y: t };
      }
    const plateauY = best.y - 2;
    this.summit = { x: best.x, y: plateauY, z: best.z };

    const turns = 1.5;
    const steps = 900;
    const startY = this.topAt(-4, -44) > 0 ? this.topAt(-4, -44) : 131;
    let prevY = startY;
    let px = NaN;
    let pz = NaN;
    const heights: number[] = [];
    const pts: { x: number; z: number }[] = [];
    for (let i = 0; i <= steps; i++) {
      const u = i / steps;
      const th = -Math.PI / 2 + turns * Math.PI * 2 * u;
      const re = 0.93 - 0.8 * Math.pow(u, 0.92);
      let x = Math.cos(th) * MM.A * re;
      let z = Math.sin(th) * MM.B * re;
      // pull the last stretch onto the summit plateau
      const pull = smoothstep(0.9, 1.0, u);
      x = lerp(x, best.x, pull);
      z = lerp(z, best.z, pull);
      let y = lerp(startY, plateauY, u);
      const ct = this.ceilingAbove(Math.round(x), Math.round(z));
      if (ct > -32768) y = Math.max(y, ct + 4);
      pts.push({ x, z });
      heights.push(y);
      px = x;
      pz = z;
    }
    void px;
    void pz;
    // limit slope: at most 1 block rise per 1.6 blocks of travel (forward pass)
    let dist = 0;
    for (let i = 1; i < pts.length; i++) {
      dist = Math.hypot(pts[i].x - pts[i - 1].x, pts[i].z - pts[i - 1].z);
      heights[i] = Math.max(heights[i], heights[i - 1]);
      heights[i] = Math.min(heights[i], heights[i - 1] + dist / 1.6);
    }
    // backward pass so we still arrive at the plateau
    for (let i = pts.length - 2; i >= 0; i--) {
      dist = Math.hypot(pts[i + 1].x - pts[i].x, pts[i + 1].z - pts[i].z);
      heights[i] = Math.max(heights[i], heights[i + 1] - dist / 1.6);
    }
    for (let i = 0; i < pts.length; i++) {
      prevY = Math.round(heights[i]);
      this.stampPath(pts[i].x, pts[i].z, prevY, 1.6);
      this.pathSamples.push({ x: pts[i].x, y: prevY, z: pts[i].z });
      if (i % 12 === 0) this.pathPoints.push({ x: pts[i].x, y: prevY + 1, z: pts[i].z });
    }
    // plateau
    for (let x = best.x - 5; x <= best.x + 5; x++)
      for (let z = best.z - 5; z <= best.z + 5; z++) {
        if (Math.hypot(x - best.x, z - best.z) > 4.6 || !this.inCols(x, z)) continue;
        const c = this.col(x, z);
        if (!(this.flags[c] & ColFlag.BODY)) continue;
        this.top[c] = plateauY;
        this.flags[c] |= ColFlag.NODE | ColFlag.STATIC;
      }
  }

  private stampPath(cx: number, cz: number, y: number, halfW: number): void {
    for (let x = Math.floor(cx - halfW - 2); x <= Math.ceil(cx + halfW + 2); x++)
      for (let z = Math.floor(cz - halfW - 2); z <= Math.ceil(cz + halfW + 2); z++) {
        if (!this.inCols(x, z)) continue;
        const c = this.col(x, z);
        if (!(this.flags[c] & ColFlag.BODY)) {
          // causeway out over the rim: extend the body
          const dd = Math.hypot(x - cx, z - cz);
          if (dd > halfW) continue;
          this.flags[c] = ColFlag.BODY;
          this.top[c] = y;
          this.under[c] = y - 4;
        }
        const dd = Math.hypot(x - cx, z - cz);
        if (dd <= halfW) {
          this.top[c] = y;
          this.flags[c] |= ColFlag.PATH;
          if (this.under[c] > y - 4) this.under[c] = y - 4;
        } else if (dd <= halfW + 2 && !(this.flags[c] & ColFlag.PATH)) {
          // soften the banks: no 1-block lips that trap players
          const t = this.top[c];
          if (t > y + 3) continue; // a real cliff wall beside the path is fine
          if (t > y) this.top[c] = y + (dd > halfW + 1 ? 1 : 0);
          else if (t < y - 2) this.top[c] = y - (dd > halfW + 1 ? 2 : 1);
        }
      }
  }

  /** Top of the cavern / tunnel void under a column (before carving: analytic). */
  ceilingAbove(x: number, z: number): number {
    const cv = MM.cavern;
    const dx = (x - cv.x) / cv.rx;
    const dz = (z - cv.z) / cv.rz;
    const r2 = dx * dx + dz * dz;
    if (r2 >= 1.25) return -32768;
    const dy = Math.sqrt(Math.max(0, 1.25 - r2)) * cv.ry;
    return Math.round(cv.y + dy);
  }

  private placeWaterfalls(): void {
    // Southern Falls: the tallest cliff on the arrival-facing side, into a basin on the ledge below.
    this.makeFallAt(this.findCliff(-150, -60, 8), "basin");
    // Western Falls: a second cascade on the rear flank.
    this.makeFallAt(this.findCliff(150, 215, 7), "basin");
    // Rim Falls: a spring on the north-east rim spills into the cloud sea.
    this.makeFallAt(this.findRim(25, 75), "void");
  }

  /** Best cliff edge in an angular sector (degrees of atan2(z, x), may exceed 180). */
  private findCliff(a0: number, a1: number, minDrop: number): { x: number; z: number; ox: number; oz: number } | undefined {
    let best: { x: number; z: number; ox: number; oz: number; score: number } | undefined;
    const g = this.g;
    for (let x = g.x0 + 2; x < g.x0 + g.sx - 2; x++)
      for (let z = g.z0 + 2; z < g.z0 + g.sz - 2; z++) {
        const c = this.col(x, z);
        if (!(this.flags[c] & ColFlag.BODY) || this.flags[c] & (ColFlag.PATH | ColFlag.STATIC)) continue;
        let a = (Math.atan2(z, x) * 180) / Math.PI;
        if (a < a0) a += 360;
        if (a < a0 || a > a1) continue;
        const t = this.top[c];
        const len = Math.hypot(x, z) || 1;
        const ix = -x / len;
        const iz = -z / len;
        let flat = true;
        for (let k = 1; k <= 4; k++) {
          const qx = Math.round(x + ix * k);
          const qz = Math.round(z + iz * k);
          if (Math.abs(this.topAt(qx, qz) - t) > 1 || this.flagAt(qx, qz) & (ColFlag.PATH | ColFlag.STATIC)) flat = false;
        }
        if (!flat) continue;
        for (const [ox, oz] of NEIGH4) {
          const n1 = this.topAt(x + ox, z + oz);
          const nt = this.topAt(x + ox * 2, z + oz * 2);
          if (n1 === -32768 || nt === -32768) continue;
          const drop = t - nt;
          if (drop < minDrop || t - n1 < minDrop - 2 || ox * x + oz * z <= 0) continue;
          const lx = x + ox * 3;
          const lz = z + oz * 3;
          if (Math.abs(this.topAt(lx, lz) - nt) > 1 || this.flagAt(lx, lz) & ColFlag.PATH) continue;
          const score = drop * 2 + t * 0.15;
          if (!best || score > best.score) best = { x, z, ox, oz, score };
        }
      }
    return best;
  }

  private findRim(a0: number, a1: number): { x: number; z: number; ox: number; oz: number } | undefined {
    let best: { x: number; z: number; ox: number; oz: number; score: number } | undefined;
    const g = this.g;
    for (let x = g.x0 + 2; x < g.x0 + g.sx - 2; x++)
      for (let z = g.z0 + 2; z < g.z0 + g.sz - 2; z++) {
        const c = this.col(x, z);
        if (!(this.flags[c] & ColFlag.BODY) || this.flags[c] & (ColFlag.PATH | ColFlag.STATIC)) continue;
        const a = (Math.atan2(z, x) * 180) / Math.PI;
        if (a < a0 || a > a1) continue;
        for (const [ox, oz] of NEIGH4) {
          if (this.topAt(x + ox, z + oz) !== -32768 || ox * x + oz * z <= 0) continue;
          const score = this.top[c];
          if (!best || score > best.score) best = { x, z, ox, oz, score };
        }
      }
    return best;
  }

  private makeFallAt(edge: { x: number; z: number; ox: number; oz: number } | undefined, kind: "basin" | "void"): void {
    if (!edge) return;
    const chanY = this.top[this.col(edge.x, edge.z)];
    const chan: { x: number; z: number }[] = [];
    for (let k = 0; k < 4; k++) chan.push({ x: edge.x - edge.ox * k, z: edge.z - edge.oz * k });
    for (const c of chan)
      for (let a = -2; a <= 2; a++)
        for (let b = -2; b <= 2; b++) {
          const x = c.x + a;
          const z = c.z + b;
          if (!this.inCols(x, z) || !(this.flagAt(x, z) & ColFlag.BODY)) continue;
          const ci = this.col(x, z);
          this.flags[ci] |= ColFlag.STATIC | ColFlag.WATER;
          if (Math.abs(a) <= 1 && Math.abs(b) <= 1) this.top[ci] = Math.max(this.top[ci], chanY);
        }
    const head = chan[chan.length - 1];
    this.waterfalls.push({ source: { x: head.x, y: chanY, z: head.z }, kind });
    this._channels.push({ cells: chan, y: chanY });
    if (kind === "basin") {
      const bx = edge.x + edge.ox * 2;
      const bz = edge.z + edge.oz * 2;
      const by = this.topAt(bx, bz);
      for (let a = -4; a <= 4; a++)
        for (let b = -4; b <= 4; b++) {
          const x = bx + a;
          const z = bz + b;
          if (!this.inCols(x, z) || !(this.flagAt(x, z) & ColFlag.BODY)) continue;
          const ci = this.col(x, z);
          this.flags[ci] |= ColFlag.STATIC | ColFlag.WATER;
          const dd = Math.hypot(a, b);
          if (dd <= 1.6) this._basins.push({ x, z, y: by });
          else if (dd <= 3.2) this.top[ci] = Math.max(this.top[ci], by);
        }
    }
  }

  private _channels: { cells: { x: number; z: number }[]; y: number }[] = [];
  private _basins: { x: number; z: number; y: number }[] = [];

  private *fillColumns(): Generator<void, void, void> {
    const g = this.g;
    for (let x = g.x0; x < g.x0 + g.sx; x++) {
      for (let z = g.z0; z < g.z0 + g.sz; z++) {
        const c = this.col(x, z);
        if (!(this.flags[c] & ColFlag.BODY)) continue;
        const top = this.top[c];
        const u = this.under[c];
        const base = c * g.sy - g.y0;
        const re = this.rimRadius(x, z);
        const ribGlow = re < 0.97 ? 0.035 : 0.015;
        const drop = this.dropAt(x, z);
        for (let y = Math.max(u, g.y0); y <= Math.min(top, g.y0 + g.sy - 1); y++) {
          const e = y - u;
          let b: number;
          if (e <= 1) b = this.muscle(x, y, z, ribGlow);
          else if (e <= 3) b = hash3(x, y, z, 3) < 0.55 ? this.muscle(x, y, z, 0.01) : this.strata(x, y, z);
          else b = this.dorsalBlock(x, y, z, top, drop);
          this.grid[base + y] = b;
        }
        if (top >= MM.snowY + 2) this.flags[c] |= ColFlag.SNOW;
      }
      if ((x & 3) === 0) yield;
    }
  }

  /** Exposed strata on cliff faces gets moss and mossy cobble patches. */
  private mossifyCliffs(): void {
    const g = this.g;
    for (let x = g.x0 + 1; x < g.x0 + g.sx - 1; x++)
      for (let z = g.z0 + 1; z < g.z0 + g.sz - 1; z++) {
        const c = this.col(x, z);
        if (!(this.flags[c] & ColFlag.BODY)) continue;
        const top = this.top[c];
        const wet = this.noise.noise2(x * 0.07 - 50, z * 0.07) * 0.5 + 0.5;
        for (let y = top - 9; y < top; y++) {
          const b = this.get(x, y, z);
          if (b === P.KEEP || b === P.AIR || b === P.SNOW || b === P.CALCITE) continue;
          const exposed =
            this.get(x + 1, y, z) === P.KEEP || this.get(x - 1, y, z) === P.KEEP || this.get(x, y, z + 1) === P.KEEP || this.get(x, y, z - 1) === P.KEEP;
          if (!exposed) continue;
          const h = hash3(x, y, z, 41);
          if (h < 0.1 + wet * 0.22) this.set(x, y, z, h < 0.06 + wet * 0.08 ? P.MOSS : P.MOSSY_COBBLE);
        }
      }
  }

  private *carveCavern(): Generator<void, void, void> {
    const cv = MM.cavern;
    for (let x = cv.x - cv.rx - 4; x <= cv.x + cv.rx + 4; x++) {
      for (let z = cv.z - cv.rz - 4; z <= cv.z + cv.rz + 4; z++) {
        let hiAir = -32768;
        for (let y = cv.floorY - 2; y <= cv.y + cv.ry + 4; y++) {
          const dx = (x - cv.x) / cv.rx;
          const dy = (y - cv.y) / cv.ry;
          const dz = (z - cv.z) / cv.rz;
          let q = dx * dx + dy * dy + dz * dz;
          q -= 0.16 * this.noise.noise3(x * 0.13, y * 0.13, z * 0.13);
          // vertical muscle ribs on the walls
          const phi = Math.atan2(z - cv.z, x - cv.x);
          const rib = Math.cos(phi * 14);
          if (rib > 0.72) q += 0.12;
          if (q < 1 && y > cv.floorY) {
            this.set(x, y, z, P.AIR);
            if (y > hiAir) hiAir = y;
          } else if (q < 1.32 && this.get(x, y, z) !== P.KEEP) {
            // cavern lining: musculature low, dripstone/tuff high
            const lining = y <= cv.floorY + 4 || rib > 0.72 ? this.muscle(x, y, z, 0.05) : hash3(x, y, z, 12) < 0.5 ? P.DRIPSTONE : P.TUFF;
            this.set(x, y, z, y === cv.floorY && q < 1 ? this.floorMat(x, z) : lining);
          }
        }
        if (hiAir > -32768 && this.inCols(x, z)) {
          const c = this.col(x, z);
          this.caveTop[c] = Math.max(this.caveTop[c], hiAir);
          this.flags[c] |= ColFlag.CAVE;
        }
      }
      if ((x & 3) === 0) yield;
    }
    // floor: flat walkable crimson nylium with glowing veins radiating from the heart
    for (let x = cv.x - cv.rx; x <= cv.x + cv.rx; x++)
      for (let z = cv.z - cv.rz; z <= cv.z + cv.rz; z++) {
        if (this.get(x, cv.floorY + 1, z) === P.AIR) this.set(x, cv.floorY, z, this.floorMat(x, z));
      }
    // ceiling dressing: stalactites, glow-berry vines, spore blossoms, hidden light
    const rng = new Rng(this.seed + 99);
    for (let i = 0; i < 520; i++) {
      const x = Math.round(cv.x + rng.range(-cv.rx, cv.rx));
      const z = Math.round(cv.z + rng.range(-cv.rz, cv.rz));
      let y = cv.y + cv.ry + 3;
      while (y > cv.floorY + 6 && this.get(x, y, z) !== P.AIR) y--;
      if (y <= cv.floorY + 6 || this.get(x, y + 1, z) === P.AIR || this.get(x, y + 1, z) === P.KEEP) continue;
      const r = rng.next();
      if (r < 0.34) {
        const len = rng.int(1, 4);
        for (let k = 0; k < len; k++) {
          if (this.get(x, y - k, z) !== P.AIR) break;
          this.set(x, y - k, z, k === len - 1 ? P.DRIP_DOWN_TIP : k === 0 ? P.DRIP_DOWN_BASE : P.DRIP_DOWN_FRUSTUM);
        }
      } else if (r < 0.62) {
        const len = rng.int(2, 6);
        for (let k = 0; k < len; k++) {
          if (this.get(x, y - k, z) !== P.AIR) break;
          this.set(x, y - k, z, k === len - 1 ? P.CAVE_VINES_HEAD : P.CAVE_VINES_BERRIES);
        }
      } else if (r < 0.68) {
        this.set(x, y, z, P.SPORE_BLOSSOM);
      } else if (r < 0.8) {
        this.set(x, y + 1, z, P.VEIN_GLOW);
      }
    }
    for (let i = 0; i < 26; i++) {
      const x = Math.round(cv.x + rng.range(-cv.rx * 0.7, cv.rx * 0.7));
      const z = Math.round(cv.z + rng.range(-cv.rz * 0.7, cv.rz * 0.7));
      if (this.get(x, cv.floorY + 5, z) === P.AIR) this.set(x, cv.floorY + 5, z, P.LIGHT_12);
    }
  }

  private floorMat(x: number, z: number): number {
    const cv = MM.cavern;
    const phi = Math.atan2(z - cv.z, x - cv.x);
    const r = Math.hypot(x - cv.x, z - cv.z);
    const vein = Math.abs(Math.sin(phi * 5 + r * 0.08)) < 0.06 && r > 6;
    if (vein) return P.VEIN_GLOW;
    const h = hash2(x, z, 17);
    return h < 0.7 ? P.MANTLE_FLOOR : h < 0.85 ? P.FLESH : P.MANTLE_ROCK;
  }

  /** Front tunnel: from the Organ Cavern out to where the pilgrim path crosses the front slope. */
  private buildTunnel(): void {
    const cv = MM.cavern;
    // where does the path cross the tunnel line (z ~ cavern z, in front of the cavern)?
    let cross: V3 | undefined;
    for (const p of this.pathSamples) {
      if (p.x < cv.x + cv.rx + 4 || Math.abs(p.z - cv.z) > 1.2) continue;
      if (!cross || p.x < cross.x) cross = p;
    }
    if (!cross) cross = { x: cv.x + cv.rx + 16, y: cv.floorY, z: cv.z };
    const xStart = cv.x + 14;
    const xEnd = Math.round(cross.x) - 1;
    for (let x = xStart; x <= xEnd + 1; x++) {
      const t = clamp((x - (cv.x + cv.rx - 2)) / Math.max(1, xEnd - (cv.x + cv.rx - 2)), 0, 1);
      const floor = Math.round(lerp(cv.floorY, cross.y, t));
      const width = 3.2 + t * 1.3;
      for (let z = -7; z <= 7; z++) {
        const zz = cv.z + z;
        if (!this.inCols(x, zz)) continue;
        const c = this.col(x, zz);
        if (!(this.flags[c] & ColFlag.BODY)) continue;
        const dz = Math.abs(z) + this.noise.noise2(x * 0.2, z * 0.2) * 0.7;
        if (dz > width + 1.3) continue;
        const ceil = floor + 5 + Math.round(1.5 * Math.cos((z / (width + 1)) * 1.5));
        const inside = dz <= width;
        for (let y = floor - 1; y <= ceil + 1; y++) {
          if (y > this.top[c]) break;
          if (y === floor && inside) this.set(x, y, zz, hash2(x, zz, 4) < 0.85 ? P.MANTLE_FLOOR : P.VEIN_GLOW);
          else if (y > floor && y <= ceil && inside) this.set(x, y, zz, P.AIR);
          else if (this.get(x, y, zz) !== P.KEEP && this.get(x, y, zz) !== P.AIR) this.set(x, y, zz, this.muscle(x, y, zz, 0.04));
        }
        if (inside) {
          if (this.top[c] <= ceil + 2) {
            // too thin for a roof: open it up into a trench down to the floor
            for (let y = floor + 1; y <= this.top[c] + 1; y++) this.set(x, y, zz, P.AIR);
            this.top[c] = floor;
            this.flags[c] |= ColFlag.STATIC;
          } else {
            this.caveTop[c] = Math.max(this.caveTop[c], ceil);
            this.flags[c] |= ColFlag.CAVE;
          }
        }
      }
    }
    this.tunnelMouth = { x: xEnd, y: Math.round(cross.y) + 1, z: cv.z };
  }

  /** Peristaltic shaft: spiral stair from the cavern floor down to the underbelly gallery. */
  private buildShaftAndGallery(): void {
    const sh = MM.shaft;
    const cv = MM.cavern;
    const ga = MM.gallery;
    const yTop = cv.floorY;
    const yBot = ga.y;
    const node0 = this.rootNodeCenter();
    const exitA = Math.atan2(node0.z - sh.z, node0.x - sh.x);
    for (let y = yBot + 1; y <= yTop; y++) {
      for (let x = sh.x - sh.r - 2; x <= sh.x + sh.r + 2; x++)
        for (let z = sh.z - sh.r - 2; z <= sh.z + sh.r + 2; z++) {
          const d = Math.hypot(x - sh.x, z - sh.z);
          if (d <= sh.r + 0.45) this.set(x, y, z, P.AIR);
          else if (d <= sh.r + 1.6) {
            // door at the bottom facing the gallery
            const a = Math.atan2(z - sh.z, x - sh.x);
            let da = a - exitA;
            while (da > Math.PI) da -= Math.PI * 2;
            while (da < -Math.PI) da += Math.PI * 2;
            if (y <= yBot + 3 && Math.abs(da) < 0.55) this.set(x, y, z, P.AIR);
            else this.set(x, y, z, this.muscle(x, y, z, 0.06));
          }
        }
    }
    // spiral steps: each level covers 40 degrees, next level 40 degrees further, one block lower
    const levels = yTop - yBot;
    for (let k = 0; k < levels; k++) {
      const y = yTop - k;
      const a0 = exitA + ((levels - 1 - k) * -40 * Math.PI) / 180;
      for (let s = 0; s <= 8; s++) {
        const a = a0 + (s * 5 * Math.PI) / 180;
        for (const rr of [1.0, 1.7, 2.4, 3.1]) {
          const x = Math.round(sh.x + Math.cos(a) * rr);
          const z = Math.round(sh.z + Math.sin(a) * rr);
          this.set(x, y, z, k % 3 === 0 ? P.SINEW : P.MUSCLE);
        }
      }
    }
    // central spine with glowing veins
    for (let y = yBot + 1; y <= yTop; y++) this.set(sh.x, y, sh.z, (y & 3) === 0 ? P.VEIN_GLOW : P.SINEW);
    for (let x = sh.x - sh.r - 1; x <= sh.x + sh.r + 1; x++)
      for (let z = sh.z - sh.r - 1; z <= sh.z + sh.r + 1; z++) {
        if (!this.inCols(x, z)) continue;
        const c = this.col(x, z);
        this.flags[c] |= ColFlag.STATIC | ColFlag.CAVE;
      }

    // underbelly gallery around the Root Node
    const node = this.rootNodeCenter();
    for (let x = node.x - ga.rOut - 1; x <= node.x + ga.rOut + 1; x++)
      for (let z = node.z - ga.rOut - 1; z <= node.z + ga.rOut + 1; z++) {
        const d = Math.hypot(x - node.x, z - node.z);
        if (d >= ga.rIn && d <= ga.rOut) {
          this.set(x, ga.y, z, hash2(x, z, 8) < 0.15 ? P.VEIN_GLOW : P.MANTLE_FLOOR);
          this.set(x, ga.y - 1, z, P.MUSCLE);
          if (d > ga.rOut - 0.8 && hash2(x, z, 2) < 0.5) this.set(x, ga.y - 2, z, P.HANGING_ROOTS);
        }
      }
    // bridge from shaft bottom to the gallery
    const bx0 = sh.x;
    const bz0 = sh.z;
    const steps = Math.ceil(Math.hypot(node.x - bx0, node.z - bz0));
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const cx = lerp(bx0, node.x, t);
      const cz = lerp(bz0, node.z, t);
      if (Math.hypot(cx - node.x, cz - node.z) < ga.rIn) break;
      for (let ox = -1; ox <= 1; ox++)
        for (let oz = -1; oz <= 1; oz++) {
          const x = Math.round(cx + ox);
          const z = Math.round(cz + oz);
          this.set(x, ga.y, z, P.MANTLE_FLOOR);
          this.set(x, ga.y - 1, z, P.MUSCLE);
        }
    }
    // hanging musculature pillars tie the gallery to the underside
    for (let k = 0; k < 6; k++) {
      const a = (k / 6) * Math.PI * 2 + 0.3;
      const x = Math.round(node.x + Math.cos(a) * (ga.rOut + 0.2));
      const z = Math.round(node.z + Math.sin(a) * (ga.rOut + 0.2));
      const u = this.topAt(x, z) > -32768 ? this.under[this.col(x, z)] : ga.y + 6;
      for (let y = ga.y + 1; y < u; y++) this.set(x, y, z, (y & 3) === 1 ? P.VEIN_GLOW : P.MUSCLE);
    }
    // carve a dome into the underside above the node so it can hang from it
    for (let x = node.x - 6; x <= node.x + 6; x++)
      for (let z = node.z - 6; z <= node.z + 6; z++) {
        if (!this.inCols(x, z)) continue;
        const c = this.col(x, z);
        if (!(this.flags[c] & ColFlag.BODY)) continue;
        const d = Math.hypot(x - node.x, z - node.z);
        if (d > 5.5) continue;
        const lift = Math.round(3 * Math.cos((d / 5.5) * (Math.PI / 2)));
        for (let y = this.under[c]; y < this.under[c] + lift; y++) this.set(x, y, z, P.AIR);
        this.under[c] += lift;
        this.set(x, this.under[c], z, this.muscle(x, this.under[c], z, 0.12));
        this.flags[c] |= ColFlag.STATIC | ColFlag.NODE;
      }
  }

  rootNodeCenter(): { x: number; z: number } {
    return { x: -22, z: 12 };
  }

  /** Rib-cage cradle around the Lithic Heart in the cavern centre. */
  private buildHeartCradle(): void {
    const cv = MM.cavern;
    const hx = Math.floor(MM.heart.x);
    const hz = Math.floor(MM.heart.z);
    const floor = cv.floorY;
    // floor ring of crying obsidian and amethyst
    for (let x = hx - 8; x <= hx + 8; x++)
      for (let z = hz - 8; z <= hz + 8; z++) {
        const d = Math.hypot(x - hx, z - hz);
        if (d >= 6.2 && d <= 7.4) this.set(x, floor, z, hash2(x, z, 3) < 0.5 ? P.CRYING_OBSIDIAN : P.AMETHYST);
        else if (d < 6.2 && this.get(x, floor + 1, z) === P.AIR) this.set(x, floor, z, d < 2 ? P.VEIN_GLOW : P.FLESH);
      }
    // eight curved ribs converging above the heart
    for (let k = 0; k < 8; k++) {
      const a = (k / 8) * Math.PI * 2;
      for (let s = 0; s <= 40; s++) {
        const t = s / 40;
        const y = floor + 1 + t * 19;
        const rad = 7 - 1.5 * t - 4 * t * t * t;
        const x = Math.round(hx + Math.cos(a) * rad);
        const z = Math.round(hz + Math.sin(a) * rad);
        const yy = Math.round(y);
        if (this.get(x, yy, z) === P.AIR) this.set(x, yy, z, s % 9 === 4 ? P.VEIN_GLOW : P.MUSCLE);
      }
    }
  }

  private buildNodeSites(): void {
    const cv = MM.cavern;
    // Dorsal Node: crystal outcrop on the summit plateau
    const s = this.summit;
    const rng = new Rng(this.seed + 5);
    for (let k = 0; k < 9; k++) {
      const a = (k / 9) * Math.PI * 2 + rng.range(-0.2, 0.2);
      const r = 4.2 + rng.range(0, 1.2);
      const x = Math.round(s.x + Math.cos(a) * r);
      const z = Math.round(s.z + Math.sin(a) * r);
      const h = rng.int(2, 5);
      for (let y = s.y + 1; y <= s.y + h; y++) this.set(x, y, z, y === s.y + h ? P.AMETHYST : k % 3 === 0 ? P.CALCITE : P.AMETHYST);
      this.set(x, s.y + h + 1, z, P.AMETHYST_CLUSTER_UP);
    }
    for (let x = s.x - 1; x <= s.x + 1; x++) for (let z = s.z - 1; z <= s.z + 1; z++) this.set(x, s.y, z, P.CRYING_OBSIDIAN);
    this.nodes.push({
      id: "dorsal",
      name: "Dorsal Node",
      pos: { x: s.x + 0.5, y: s.y + 1, z: s.z + 0.5 },
      safe: { x: s.x + 0.5, y: s.y + 1, z: s.z + 3.5 },
    });

    // Cavern Node: pedestal by the north-east wall of the Organ Cavern
    const cx = cv.x + 15;
    const cz = cv.z + 9;
    for (let x = cx - 3; x <= cx + 3; x++)
      for (let z = cz - 3; z <= cz + 3; z++) {
        const d = Math.hypot(x - cx, z - cz);
        if (d > 3.2) continue;
        this.set(x, cv.floorY, z, d < 1.5 ? P.CRYING_OBSIDIAN : P.AMETHYST);
        if (d < 2.2) this.set(x, cv.floorY + 1, z, d < 1.2 ? P.BUDDING : P.MUSCLE);
        for (let y = cv.floorY + 2; y <= cv.floorY + 7; y++) if (this.get(x, y, z) !== P.AIR && d < 2.6) this.set(x, y, z, P.AIR);
      }
    this.nodes.push({
      id: "cavern",
      name: "Cavern Node",
      pos: { x: cx + 0.5, y: cv.floorY + 2, z: cz + 0.5 },
      safe: { x: cx - 3.5, y: cv.floorY + 1, z: cz - 2.5 },
    });

    // Root Node: hangs below the underside over the underbelly gallery
    const rn = this.rootNodeCenter();
    const ga = MM.gallery;
    this.nodes.push({
      id: "root",
      name: "Root Node",
      pos: { x: rn.x + 0.5, y: ga.y + 2, z: rn.z + 0.5 },
      safe: { x: rn.x + 0.5 + ga.rIn + 1.5, y: ga.y + 1, z: rn.z + 0.5 },
    });
  }

  /** Floating arrival shelf and the anchorage-root bridge onto the south rim. */
  private buildArrival(): void {
    const ar = MM.arrival;
    const rng = new Rng(this.seed + 21);
    for (let x = ar.x - ar.r - 2; x <= ar.x + ar.r + 2; x++)
      for (let z = ar.z - ar.r - 2; z <= ar.z + ar.r + 2; z++) {
        const d = Math.hypot(x - ar.x, z - ar.z) + this.noise.noise2(x * 0.3, z * 0.3) * 1.3;
        if (d > ar.r) continue;
        const depth = Math.round((1 - d / ar.r) * 12 + 2);
        for (let y = ar.y - depth; y <= ar.y; y++) {
          const fromTop = ar.y - y;
          let b: number;
          if (fromTop === 0) b = hash2(x, z, 1) < 0.85 ? P.GRASS : P.MOSS;
          else if (fromTop <= 2) b = P.DIRT;
          else if (y - (ar.y - depth) <= 1) b = this.muscle(x, y, z, 0.05);
          else b = this.strata(x, y, z);
          this.set(x, y, z, b);
        }
        if (d > ar.r - 1.5 && rng.chance(0.4)) this.set(x, ar.y - depth - 1, z, P.HANGING_ROOTS);
        if (rng.chance(0.25) && d < ar.r - 1) this.set(x, ar.y + 1, z, rng.chance(0.8) ? P.SHORT_GRASS : P.FERN);
      }
    // the anchorage-root bridge: a living root arching up to the rim
    const landing = { x: ar.x, z: -45 };
    let rimTop = this.topAt(landing.x, landing.z);
    let lz = landing.z;
    while (rimTop === -32768 && lz < -20) {
      lz++;
      rimTop = this.topAt(landing.x, lz);
    }
    const z0 = ar.z + ar.r - 1;
    const z1 = lz + 2;
    const y0 = ar.y;
    const y1 = rimTop;
    for (let z = z0; z <= z1; z++) {
      const t = (z - z0) / (z1 - z0);
      const yc = Math.round(lerp(y0, y1, t) + Math.sin(t * Math.PI) * 1.5);
      const xc = ar.x + Math.sin(t * Math.PI * 1.3) * 2.2;
      for (let x = Math.floor(xc - 3); x <= Math.ceil(xc + 3); x++) {
        const dx = Math.abs(x - xc);
        if (dx > 2.4) continue;
        this.set(x, yc, z, dx < 1.6 ? (hash2(x, z, 6) < 0.7 ? P.MOSS : P.GRASS) : P.ROOT_WOOD_Z);
        this.set(x, yc - 1, z, P.ROOT_WOOD_Z);
        if (dx < 1.2) this.set(x, yc - 2, z, P.MUSCLE_Z);
        this.set(x, yc + 1, z, P.AIR);
        this.set(x, yc + 2, z, P.AIR);
        if (dx >= 1.6 && hash2(x, z, 12) < 0.35) this.set(x, yc - 2, z, P.HANGING_ROOTS);
        if (this.inCols(x, z)) {
          const c = this.col(x, z);
          if (this.flags[c] & ColFlag.BODY) {
            this.flags[c] |= ColFlag.STATIC;
            if (this.top[c] < yc) this.top[c] = yc;
          }
        }
      }
    }
  }

  private writeWater(): void {
    for (const ch of this._channels) {
      for (let i = 0; i < ch.cells.length; i++) {
        const c = ch.cells[i];
        // carve a 1-deep groove with banks, water in the groove
        this.set(c.x, ch.y, c.z, P.WATER);
        this.set(c.x, ch.y - 1, c.z, P.MOSS);
        for (let y = ch.y + 1; y <= ch.y + 4; y++) this.set(c.x, y, c.z, P.AIR);
      }
    }
    for (const b of this._basins) {
      this.set(b.x, b.y, b.z, P.WATER);
      this.set(b.x, b.y - 1, b.z, P.WATER);
      this.set(b.x, b.y - 2, b.z, P.MOSS);
      for (let y = b.y + 1; y <= b.y + 3; y++) this.set(b.x, y, b.z, P.AIR);
    }
  }

  private plantTrees(): void {
    const g = this.g;
    const cell = 3;
    for (let cx = g.x0; cx < g.x0 + g.sx; cx += cell)
      for (let cz = g.z0; cz < g.z0 + g.sz; cz += cell) {
        const h = hash2(cx, cz, 404);
        const x = cx + Math.floor(hash2(cx, cz, 405) * cell);
        const z = cz + Math.floor(hash2(cx, cz, 406) * cell);
        if (!this.inCols(x, z)) continue;
        const c = this.col(x, z);
        const fl = this.flags[c];
        if (!(fl & ColFlag.BODY) || fl & (ColFlag.PATH | ColFlag.WATER | ColFlag.NODE | ColFlag.SNOW)) continue;
        const top = this.top[c];
        if (this.get(x, top, z) !== P.GRASS && this.get(x, top, z) !== P.PODZOL && this.get(x, top, z) !== P.MOSS) continue;
        // flat enough
        let ok = true;
        for (const [ox, oz] of NEIGH4) if (Math.abs(this.topAt(x + ox, z + oz) - top) > 1) ok = false;
        if (!ok) continue;
        // not hugging the path
        let nearPath = false;
        for (let ox = -2; ox <= 2 && !nearPath; ox++) for (let oz = -2; oz <= 2; oz++) if (this.flagAt(x + ox, z + oz) & ColFlag.PATH) nearPath = true;
        if (nearPath) continue;
        const forest = this.noise.noise2(x * 0.06 - 20, z * 0.06 + 11) * 0.5 + 0.5;
        const rimFade = smoothstep(1.0, 0.9, this.rimRadius(x, z));
        if (h > (0.25 + forest * 0.75) * rimFade) continue;
        const kind: 0 | 1 | 2 = top > 154 ? 0 : hash2(x, z, 7) < 0.55 ? 0 : hash2(x, z, 8) < 0.82 ? 1 : 2;
        const height = kind === 0 ? 7 + Math.floor(hash2(x, z, 9) * 5) : 5 + Math.floor(hash2(x, z, 9) * 3);
        const tree: TreeInfo = { x, z, groundY: top, kind, height, seed: Math.floor(hash2(x, z, 10) * 1e6) };
        if (!this.treeFits(tree)) continue;
        this.trees.push(tree);
        this.flags[c] |= ColFlag.TREE;
        if (kind === 0) this.set(x, top, z, P.PODZOL);
        for (const b of treeBlocks(tree)) {
          const cur = this.get(b.x, b.y, b.z);
          if (cur === P.KEEP || cur === P.AIR) this.set(b.x, b.y, b.z, b.b);
        }
      }
  }

  private treeFits(t: TreeInfo): boolean {
    let blocked = 0;
    let total = 0;
    for (const b of treeBlocks(t)) {
      if (!this.inGrid(b.x, b.y, b.z)) return false;
      const cur = this.get(b.x, b.y, b.z);
      const free = cur === P.KEEP || cur === P.AIR;
      if (!free && (b.b === P.SPRUCE_LOG || b.b === P.OAK_LOG)) return false;
      total++;
      if (!free) blocked++;
    }
    return blocked <= total * 0.25;
  }

  private decorateSurface(): void {
    const g = this.g;
    for (let x = g.x0; x < g.x0 + g.sx; x++)
      for (let z = g.z0; z < g.z0 + g.sz; z++) {
        const c = this.col(x, z);
        const fl = this.flags[c];
        if (!(fl & ColFlag.BODY) || fl & (ColFlag.PATH | ColFlag.WATER | ColFlag.TREE)) continue;
        const top = this.top[c];
        const above = this.get(x, top + 1, z);
        if (above !== P.KEEP) continue;
        const tb = this.get(x, top, z);
        const h = hash2(x, z, 600);
        if (tb === P.SNOW) {
          if (h < 0.45) this.set(x, top + 1, z, h < 0.15 ? P.SNOW_LAYER_2 : P.SNOW_LAYER_1);
        } else if (tb === P.GRASS) {
          if (h < 0.22) this.set(x, top + 1, z, P.SHORT_GRASS);
          else if (h < 0.27) this.set(x, top + 1, z, P.FERN);
          else if (h < 0.285) this.set(x, top + 1, z, P.CORNFLOWER);
          else if (h < 0.295) this.set(x, top + 1, z, P.AZURE_BLUET);
          else if (h < 0.3) this.set(x, top + 1, z, P.POPPY);
        } else if (tb === P.MOSS) {
          if (h < 0.3) this.set(x, top + 1, z, P.MOSS_CARPET);
        }
      }
  }

  // ----------------------------------------------------------------- Phase 2
  /**
   * Block for the Phase 2 "Unfolded World" disk at (x,y,z), or -1 when the
   * position is outside the rebuilt cylinder (keep whatever the cut body has).
   * The rib layout rotates with `layoutTurn` (0 or 1 = half a rib spacing).
   */
  phase2Block(x: number, y: number, z: number, layoutTurn = 0): number {
    const D = MM.disk;
    const hx = MM.heart.x - 0.5;
    const hz = MM.heart.z - 0.5;
    const r = Math.hypot(x - hx, z - hz);
    if (r > D.outerR + 0.5) return -1;
    if (y > D.y + 14 || y < D.mantleY - 6) return -1;
    if (y > D.y) return P.AIR;
    const phi = Math.atan2(z - hz, x - hx);
    const ribPitch = (Math.PI * 2) / D.ribs;
    const off = layoutTurn * ribPitch * 0.5;
    let a = (phi - off) / ribPitch;
    a = (a - Math.round(a)) * ribPitch; // angular offset to nearest rib
    const perp = Math.abs(Math.sin(a) * r);
    const onRib = perp <= 1.6 && r >= D.periR - 0.5 && r <= D.ribEnd + 0.5;
    const onPeri = r >= D.wellR && r < D.periR;
    const ring2Gap = Math.cos(phi * 3 + 0.7) > 0.86;
    const onRing2 = r >= D.ring2 && r < D.ring2 + 2 && !ring2Gap;
    const onOuter = r >= D.ribEnd && r <= D.outerR + 0.5;
    const walk = onRib || onPeri || onRing2 || onOuter;
    if (y === D.y) {
      if (!walk) return P.AIR;
      if (onRib && perp <= 0.5 && r > D.periR + 1) return P.VEIN_GLOW; // circulation line
      if (onPeri && r >= D.periR - 1.2) return P.CRYING_OBSIDIAN;
      if (onPeri) return hash2(x, z, 70) < 0.5 ? P.AMETHYST : P.MANTLE_ROCK;
      return onOuter ? (hash2(x, z, 71) < 0.7 ? P.MANTLE_FLOOR : P.FLESH) : hash2(x, z, 72) < 0.6 ? P.MUSCLE : P.MANTLE_ROCK;
    }
    if (y > D.mantleY && y < D.y) {
      // structural depth under walkways
      if (onOuter) return this.muscle(x, y, z, 0.03);
      if ((onRib || onPeri || onRing2) && y >= D.y - 3) return onRib ? (Math.abs(Math.sin(a) * r) < 0.6 ? P.SINEW : P.MUSCLE) : P.MUSCLE;
      return P.AIR;
    }
    if (y === D.mantleY) {
      if (r < D.wellR) return P.VEIN_HOT;
      const h = hash2(x, z, 73);
      const vein = Math.abs(Math.sin(phi * 7 + r * 0.25)) < 0.12;
      return vein ? (h < 0.5 ? P.VEIN_HOT : P.VEIN_GLOW) : h < 0.65 ? P.MANTLE_FLOOR : P.FLESH;
    }
    // below the mantle floor: solid musculature (keeps the body sealed)
    return this.muscle(x, y, z, 0.04);
  }

  /** Heights of the Phase 2 rim shelf: every body column is cut down to this. */
  phase2CutY(): number {
    return MM.disk.y;
  }
}

/** Mesa levels: contour (normalised radius) and the height each adds. */
const MESA_LEVELS: ReadonlyArray<{ edge: number; rise: number; warp: number }> = [
  { edge: 0.87, rise: 10, warp: 0.08 },
  { edge: 0.71, rise: 9, warp: 0.1 },
  { edge: 0.55, rise: 8, warp: 0.08 },
  { edge: 0.38, rise: 7, warp: 0.07 },
];

/** Rock spires: centre, radius, absolute height above baseY at the foot and the tip. */
const SPIRES: ReadonlyArray<{ x: number; z: number; r: number; base: number; top: number }> = [
  { x: -10, z: 6, r: 15, base: 44, top: 56 }, // main summit (Dorsal Node)
  { x: 19, z: -13, r: 11, base: 38, top: 52 },
  { x: -33, z: -11, r: 10, base: 33, top: 49 },
  { x: -38, z: 17, r: 8, base: 30, top: 45 },
  { x: 30, z: 18, r: 9, base: 32, top: 47 },
  { x: 8, z: 24, r: 7, base: 36, top: 49 },
  { x: -22, z: -27, r: 6, base: 30, top: 42 },
  { x: 40, z: -16, r: 6, base: 27, top: 38 },
  { x: -46, z: -2, r: 6, base: 24, top: 36 },
  { x: 2, z: -30, r: 5, base: 28, top: 38 },
];

const NEIGH4: ReadonlyArray<readonly [number, number]> = [
  [1, 0],
  [-1, 0],
  [0, 1],
  [0, -1],
];

const NON_SOLID = new Set<number>([
  P.SHORT_GRASS,
  P.FERN,
  P.POPPY,
  P.CORNFLOWER,
  P.AZURE_BLUET,
  P.MOSS_CARPET,
  P.SNOW_LAYER_1,
  P.SNOW_LAYER_2,
  P.WATER,
  P.CAVE_VINES_BERRIES,
  P.CAVE_VINES_HEAD,
  P.SPORE_BLOSSOM,
  P.HANGING_ROOTS,
  P.LIGHT_12,
  P.DRIP_DOWN_TIP,
  P.DRIP_DOWN_FRUSTUM,
  P.DRIP_DOWN_BASE,
  P.AMETHYST_CLUSTER_UP,
]);

export function isNonSolid(b: number): boolean {
  return b === P.KEEP || b === P.AIR || NON_SOLID.has(b);
}

export interface PlacedBlock {
  x: number;
  y: number;
  z: number;
  b: number;
}

/** Deterministic tree template (absolute coordinates). */
export function treeBlocks(t: TreeInfo): PlacedBlock[] {
  const out: PlacedBlock[] = [];
  const rng = new Rng(t.seed + 1);
  const y0 = t.groundY + 1;
  const H = t.height;
  if (t.kind === 0) {
    // spruce: conical, alternating ring radii
    for (let i = 0; i < H - 1; i++) out.push({ x: t.x, y: y0 + i, z: t.z, b: P.SPRUCE_LOG });
    const topY = y0 + H;
    out.push({ x: t.x, y: topY, z: t.z, b: P.SPRUCE_LEAVES });
    out.push({ x: t.x, y: topY - 1, z: t.z, b: P.SPRUCE_LEAVES });
    let radius = 1;
    for (let y = topY - 1; y >= y0 + 2; y--) {
      const k = topY - 1 - y;
      radius = k === 0 ? 1 : k % 2 === 1 ? Math.min(3, 1 + Math.floor(k / 2)) : Math.max(1, Math.floor(k / 2));
      for (let ox = -radius; ox <= radius; ox++)
        for (let oz = -radius; oz <= radius; oz++) {
          if (ox === 0 && oz === 0) continue;
          if (Math.abs(ox) === radius && Math.abs(oz) === radius && radius > 1) continue;
          if (Math.abs(ox) + Math.abs(oz) > radius + 1) continue;
          out.push({ x: t.x + ox, y, z: t.z + oz, b: P.SPRUCE_LEAVES });
        }
    }
  } else {
    const log = P.OAK_LOG;
    const leaf = t.kind === 2 ? P.AZALEA_LEAVES : P.OAK_LEAVES;
    for (let i = 0; i < H - 1; i++) out.push({ x: t.x, y: y0 + i, z: t.z, b: log });
    const cy = y0 + H - 2;
    for (let oy = -1; oy <= 2; oy++) {
      const r = oy === 2 ? 1 : oy === -1 ? 2 : 2;
      for (let ox = -r; ox <= r; ox++)
        for (let oz = -r; oz <= r; oz++) {
          if (ox === 0 && oz === 0 && oy < 1) continue;
          const corner = Math.abs(ox) === r && Math.abs(oz) === r;
          if (corner && (oy === 2 || oy === -1 || rng.chance(0.5))) continue;
          out.push({ x: t.x + ox, y: cy + oy, z: t.z + oz, b: leaf });
        }
    }
  }
  return out;
}
