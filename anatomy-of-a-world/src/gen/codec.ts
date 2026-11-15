/**
 * Compact codecs shared by the build-time exporter and the in-game loader:
 * base64 <-> bytes, and per-column run-length encoding of voxel columns.
 */
const B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
const LOOKUP = (() => {
  const t = new Uint8Array(128);
  for (let i = 0; i < B64.length; i++) t[B64.charCodeAt(i)] = i;
  return t;
})();

export function bytesToBase64(bytes: Uint8Array): string {
  let out = "";
  let i = 0;
  for (; i + 2 < bytes.length; i += 3) {
    const n = (bytes[i] << 16) | (bytes[i + 1] << 8) | bytes[i + 2];
    out += B64[(n >> 18) & 63] + B64[(n >> 12) & 63] + B64[(n >> 6) & 63] + B64[n & 63];
  }
  const rem = bytes.length - i;
  if (rem === 1) {
    const n = bytes[i] << 16;
    out += B64[(n >> 18) & 63] + B64[(n >> 12) & 63] + "==";
  } else if (rem === 2) {
    const n = (bytes[i] << 16) | (bytes[i + 1] << 8);
    out += B64[(n >> 18) & 63] + B64[(n >> 12) & 63] + B64[(n >> 6) & 63] + "=";
  }
  return out;
}

export function base64ToBytes(s: string): Uint8Array {
  let len = (s.length / 4) * 3;
  if (s.endsWith("==")) len -= 2;
  else if (s.endsWith("=")) len -= 1;
  const out = new Uint8Array(len);
  let o = 0;
  for (let i = 0; i < s.length; i += 4) {
    const n = (LOOKUP[s.charCodeAt(i)] << 18) | (LOOKUP[s.charCodeAt(i + 1)] << 12) | (LOOKUP[s.charCodeAt(i + 2)] << 6) | LOOKUP[s.charCodeAt(i + 3)];
    if (o < len) out[o++] = (n >> 16) & 255;
    if (o < len) out[o++] = (n >> 8) & 255;
    if (o < len) out[o++] = n & 255;
  }
  return out;
}

/** A vertical run of identical blocks inside one column. */
export interface Run {
  y0: number;
  len: number;
  b: number;
}

/**
 * Column runs: [nRuns][dy len b]... per column, columns ordered x-major then z.
 * Only blocks with palette index >= 2 (not KEEP / AIR) are stored.
 */
export function encodeColumns(sx: number, sz: number, sy: number, get: (cx: number, cz: number, cy: number) => number): Uint8Array {
  const out: number[] = [];
  for (let cx = 0; cx < sx; cx++)
    for (let cz = 0; cz < sz; cz++) {
      const runs: number[] = [];
      let y = 0;
      while (y < sy) {
        const b = get(cx, cz, y);
        if (b < 2) {
          y++;
          continue;
        }
        let l = 1;
        while (y + l < sy && l < 255 && get(cx, cz, y + l) === b) l++;
        runs.push(y, l, b);
        y += l;
      }
      out.push(runs.length / 3, ...runs);
    }
  return Uint8Array.from(out);
}

/** Iterate decoded runs: cb(cx, cz, run). */
export function forEachRun(data: Uint8Array, sx: number, sz: number, cb: (cx: number, cz: number, y0: number, len: number, b: number) => void): void {
  let i = 0;
  for (let cx = 0; cx < sx; cx++)
    for (let cz = 0; cz < sz; cz++) {
      const n = data[i++];
      for (let r = 0; r < n; r++) {
        cb(cx, cz, data[i], data[i + 1], data[i + 2]);
        i += 3;
      }
    }
}

// ----------------------------------------------------------------------------- LZ77
function writeVar(out: number[], v: number): void {
  while (v >= 0x80) {
    out.push((v & 0x7f) | 0x80);
    v >>>= 7;
  }
  out.push(v);
}

/** Greedy LZ77 with a hash chain. Format: (litLen var, literals, matchLen var [, offset var])* ; matchLen 0 ends. */
export function lzCompress(src: Uint8Array): Uint8Array {
  const out: number[] = [];
  writeVar(out, src.length);
  const HASH = 1 << 16;
  const head = new Int32Array(HASH).fill(-1);
  const prev = new Int32Array(src.length).fill(-1);
  const h3 = (i: number) => ((src[i] * 506832829) ^ (src[i + 1] * 2654435761) ^ (src[i + 2] * 40503)) >>> 16;
  let lit = 0;
  let i = 0;
  const flushLiterals = (end: number, mlen: number, off: number) => {
    writeVar(out, end - lit);
    for (let k = lit; k < end; k++) out.push(src[k]);
    writeVar(out, mlen);
    if (mlen) writeVar(out, off);
  };
  while (i + 3 <= src.length) {
    const h = h3(i);
    let best = 0;
    let bestOff = 0;
    let cand = head[h];
    let chain = 48;
    while (cand >= 0 && chain-- > 0 && i - cand < 1 << 20) {
      let l = 0;
      while (i + l < src.length && src[cand + l] === src[i + l] && l < 4096) l++;
      if (l > best) {
        best = l;
        bestOff = i - cand;
      }
      cand = prev[cand];
    }
    prev[i] = head[h];
    head[h] = i;
    if (best >= 4) {
      flushLiterals(i, best, bestOff);
      for (let k = 1; k < best && i + k + 3 <= src.length; k++) {
        const hh = h3(i + k);
        prev[i + k] = head[hh];
        head[hh] = i + k;
      }
      i += best;
      lit = i;
    } else i++;
  }
  flushLiterals(src.length, 0, 0);
  return Uint8Array.from(out);
}

export function lzDecompress(data: Uint8Array): Uint8Array {
  let p = 0;
  const readVar = () => {
    let v = 0;
    let shift = 0;
    for (;;) {
      const b = data[p++];
      v |= (b & 0x7f) << shift;
      if (b < 0x80) break;
      shift += 7;
    }
    return v >>> 0;
  };
  const n = readVar();
  const out = new Uint8Array(n);
  let o = 0;
  while (p < data.length) {
    const lit = readVar();
    for (let k = 0; k < lit; k++) out[o++] = data[p++];
    const mlen = readVar();
    if (!mlen) break;
    const off = readVar();
    for (let k = 0; k < mlen; k++, o++) out[o] = out[o - off];
  }
  return out;
}

/** base64(lz(bytes)) and back. */
export function pack(bytes: Uint8Array): string {
  return bytesToBase64(lzCompress(bytes));
}
export function unpack(s: string): Uint8Array {
  return lzDecompress(base64ToBytes(s));
}
