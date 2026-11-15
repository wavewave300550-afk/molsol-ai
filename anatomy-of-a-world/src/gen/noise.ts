/**
 * Deterministic, dependency-free noise + RNG used by the world generators.
 * Pure module: no @minecraft imports, so the exact same code runs inside the
 * game (Script API) and in the Node preview / simulation tools.
 */

/** Mulberry32 PRNG. */
export class Rng {
  private s: number;
  constructor(seed: number) {
    this.s = seed >>> 0 || 0x9e3779b9;
  }
  next(): number {
    let t = (this.s = (this.s + 0x6d2b79f5) >>> 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  range(a: number, b: number): number {
    return a + (b - a) * this.next();
  }
  int(a: number, bInclusive: number): number {
    return a + Math.floor(this.next() * (bInclusive - a + 1));
  }
  pick<T>(arr: readonly T[]): T {
    return arr[Math.floor(this.next() * arr.length)];
  }
  chance(p: number): boolean {
    return this.next() < p;
  }
}

/** Stateless integer hash -> [0,1). */
export function hash3(x: number, y: number, z: number, seed = 0): number {
  let h = Math.imul(x | 0, 374761393) ^ Math.imul(y | 0, 668265263) ^ Math.imul(z | 0, 2147483647) ^ Math.imul(seed | 0, 1274126177);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}

export function hash2(x: number, z: number, seed = 0): number {
  return hash3(x, 0, z, seed);
}

const GRAD3: ReadonlyArray<readonly [number, number, number]> = [
  [1, 1, 0], [-1, 1, 0], [1, -1, 0], [-1, -1, 0],
  [1, 0, 1], [-1, 0, 1], [1, 0, -1], [-1, 0, -1],
  [0, 1, 1], [0, -1, 1], [0, 1, -1], [0, -1, -1],
];

function fade(t: number): number {
  return t * t * t * (t * (t * 6 - 15) + 10);
}

/** Classic gradient (Perlin) noise in 2D and 3D, output roughly in [-1, 1]. */
export class Perlin {
  private readonly perm = new Uint8Array(512);
  constructor(seed: number) {
    const rng = new Rng(seed);
    const p = new Uint8Array(256);
    for (let i = 0; i < 256; i++) p[i] = i;
    for (let i = 255; i > 0; i--) {
      const j = Math.floor(rng.next() * (i + 1));
      const t = p[i];
      p[i] = p[j];
      p[j] = t;
    }
    for (let i = 0; i < 512; i++) this.perm[i] = p[i & 255];
  }

  noise2(x: number, y: number): number {
    const P = this.perm;
    const xi = Math.floor(x);
    const yi = Math.floor(y);
    const xf = x - xi;
    const yf = y - yi;
    const X = xi & 255;
    const Y = yi & 255;
    const u = fade(xf);
    const v = fade(yf);
    const aa = P[P[X] + Y] % 12;
    const ab = P[P[X] + Y + 1] % 12;
    const ba = P[P[X + 1] + Y] % 12;
    const bb = P[P[X + 1] + Y + 1] % 12;
    const g = GRAD3;
    const n00 = g[aa][0] * xf + g[aa][1] * yf;
    const n10 = g[ba][0] * (xf - 1) + g[ba][1] * yf;
    const n01 = g[ab][0] * xf + g[ab][1] * (yf - 1);
    const n11 = g[bb][0] * (xf - 1) + g[bb][1] * (yf - 1);
    const nx0 = n00 + u * (n10 - n00);
    const nx1 = n01 + u * (n11 - n01);
    return (nx0 + v * (nx1 - nx0)) * 0.9;
  }

  noise3(x: number, y: number, z: number): number {
    const P = this.perm;
    const xi = Math.floor(x);
    const yi = Math.floor(y);
    const zi = Math.floor(z);
    const xf = x - xi;
    const yf = y - yi;
    const zf = z - zi;
    const X = xi & 255;
    const Y = yi & 255;
    const Z = zi & 255;
    const u = fade(xf);
    const v = fade(yf);
    const w = fade(zf);
    const A = P[X] + Y;
    const AA = P[A] + Z;
    const AB = P[A + 1] + Z;
    const B = P[X + 1] + Y;
    const BA = P[B] + Z;
    const BB = P[B + 1] + Z;
    const g = GRAD3;
    const d = (h: number, a: number, b: number, c: number) => {
      const gg = g[h % 12];
      return gg[0] * a + gg[1] * b + gg[2] * c;
    };
    const x1 = d(P[AA], xf, yf, zf) + u * (d(P[BA], xf - 1, yf, zf) - d(P[AA], xf, yf, zf));
    const x2 = d(P[AB], xf, yf - 1, zf) + u * (d(P[BB], xf - 1, yf - 1, zf) - d(P[AB], xf, yf - 1, zf));
    const y1 = x1 + v * (x2 - x1);
    const x3 = d(P[AA + 1], xf, yf, zf - 1) + u * (d(P[BA + 1], xf - 1, yf, zf - 1) - d(P[AA + 1], xf, yf, zf - 1));
    const x4 = d(P[AB + 1], xf, yf - 1, zf - 1) + u * (d(P[BB + 1], xf - 1, yf - 1, zf - 1) - d(P[AB + 1], xf, yf - 1, zf - 1));
    const y2 = x3 + v * (x4 - x3);
    return y1 + w * (y2 - y1);
  }

  fbm2(x: number, y: number, octaves: number, lacunarity = 2, gain = 0.5): number {
    let amp = 1;
    let freq = 1;
    let sum = 0;
    let norm = 0;
    for (let i = 0; i < octaves; i++) {
      sum += amp * this.noise2(x * freq + i * 17.3, y * freq - i * 9.1);
      norm += amp;
      amp *= gain;
      freq *= lacunarity;
    }
    return sum / norm;
  }

  /** Ridged multifractal in [0, 1]: sharp crests where the base noise crosses zero. */
  ridged2(x: number, y: number, octaves: number): number {
    let amp = 0.6;
    let freq = 1;
    let sum = 0;
    let norm = 0;
    let weight = 1;
    for (let i = 0; i < octaves; i++) {
      let n = 1 - Math.abs(this.noise2(x * freq + i * 31.7, y * freq + i * 11.3));
      n *= n;
      n *= weight;
      weight = Math.min(1, Math.max(0, n * 1.6));
      sum += n * amp;
      norm += amp;
      amp *= 0.5;
      freq *= 2.1;
    }
    return sum / norm;
  }
}

export function clamp(v: number, lo: number, hi: number): number {
  return v < lo ? lo : v > hi ? hi : v;
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function smoothstep(e0: number, e1: number, x: number): number {
  const t = clamp((x - e0) / (e1 - e0), 0, 1);
  return t * t * (3 - 2 * t);
}

/** Smallest signed difference between two angles (radians), in (-PI, PI]. */
export function angleDiff(a: number, b: number): number {
  let d = (a - b) % (Math.PI * 2);
  if (d > Math.PI) d -= Math.PI * 2;
  if (d <= -Math.PI) d += Math.PI * 2;
  return d;
}
