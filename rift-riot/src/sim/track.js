// Track geometry + queries. Pure math (no rendering) so it runs headless in tests.
import { BALANCE } from '../data/balance.js';
import { lerp, wrapAngle } from './math.js';

function cr1(p0, p1, p2, p3, t) {
  const t2 = t * t;
  const t3 = t2 * t;
  return 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3);
}

// Centripetal Catmull-Rom on the ground plane (no overshoot on uneven spacing).
function crCentripetal(p0, p1, p2, p3, t, out) {
  const d01 = Math.sqrt(Math.hypot(p1.x - p0.x, p1.z - p0.z)) || 1e-4;
  const d12 = Math.sqrt(Math.hypot(p2.x - p1.x, p2.z - p1.z)) || 1e-4;
  const d23 = Math.sqrt(Math.hypot(p3.x - p2.x, p3.z - p2.z)) || 1e-4;
  const t0 = 0;
  const t1 = t0 + d01;
  const t2 = t1 + d12;
  const t3 = t2 + d23;
  const tt = t1 + (t2 - t1) * t;
  const mix = (a, b, ta, tb, key) => ((tb - tt) / (tb - ta)) * a[key] + ((tt - ta) / (tb - ta)) * b[key];
  for (const key of ['x', 'z']) {
    const a1 = mix(p0, p1, t0, t1, key);
    const a2 = mix(p1, p2, t1, t2, key);
    const a3 = mix(p2, p3, t2, t3, key);
    const b1 = ((t2 - tt) / (t2 - t0)) * a1 + ((tt - t0) / (t2 - t0)) * a2;
    const b2 = ((t3 - tt) / (t3 - t1)) * a2 + ((tt - t1) / (t3 - t1)) * a3;
    out[key] = ((t2 - tt) / (t2 - t1)) * b1 + ((tt - t1) / (t2 - t1)) * b2;
  }
  return out;
}

export class Track {
  constructor(def) {
    this.def = def;
    this.step = BALANCE.track.sampleStep;
    this._buildMain();
    this._buildBranch();
    this._buildGates();
    this._buildTeacups();
  }

  _buildMain() {
    const P = this.def.points;
    const n = P.length;
    const dense = [];
    const SUB = 48;
    for (let i = 0; i < n; i++) {
      const p0 = P[(i - 1 + n) % n];
      const p1 = P[i];
      const p2 = P[(i + 1) % n];
      const p3 = P[(i + 2) % n];
      for (let k = 0; k < SUB; k++) {
        const t = k / SUB;
        const q = crCentripetal(p0, p1, p2, p3, t, {});
        q.y = cr1(p0.y, p1.y, p2.y, p3.y, t);
        q.hw = cr1(p0.hw, p1.hw, p2.hw, p3.hw, t);
        q.u = i + t;
        q.sec = t < 0.5 ? p1.sec : p2.sec;
        dense.push(q);
      }
    }
    // cumulative arc length
    const cum = [0];
    for (let i = 1; i <= dense.length; i++) {
      const a = dense[i - 1];
      const b = dense[i % dense.length];
      cum.push(cum[i - 1] + Math.hypot(b.x - a.x, b.z - a.z));
    }
    const total = cum[dense.length];
    const count = Math.round(total / this.step);
    const step = total / count;
    this.step = step;
    this.length = total;
    this.n = count;
    const S = [];
    let j = 0;
    for (let i = 0; i < count; i++) {
      const s = i * step;
      while (cum[j + 1] < s) j++;
      const a = dense[j];
      const b = dense[(j + 1) % dense.length];
      const f = (s - cum[j]) / (cum[j + 1] - cum[j] || 1);
      let bu = b.u;
      if (bu < a.u) bu += n;
      S.push({
        i,
        s,
        x: lerp(a.x, b.x, f),
        y: lerp(a.y, b.y, f),
        z: lerp(a.z, b.z, f),
        hw: lerp(a.hw, b.hw, f),
        u: lerp(a.u, bu, f) % n,
        sec: f < 0.5 ? a.sec : b.sec,
        tx: 0,
        tz: 1,
        rx: -1,
        rz: 0,
        heading: 0,
        curv: 0,
        wall: true,
      });
    }
    const open = this.def.open;
    for (let i = 0; i < count; i++) {
      const a = S[(i - 1 + count) % count];
      const b = S[(i + 1) % count];
      const s = S[i];
      const dx = b.x - a.x;
      const dz = b.z - a.z;
      const l = Math.hypot(dx, dz) || 1;
      s.tx = dx / l;
      s.tz = dz / l;
      // right-hand side of travel (matches camera right when looking along the tangent)
      s.rx = -s.tz;
      s.rz = s.tx;
      s.heading = Math.atan2(s.tx, s.tz);
      s.slope = (b.y - a.y) / (2 * step);
      s.wall = !(open && s.u >= open.from && s.u <= open.to);
    }
    // signed curvature (positive = bends to the right), lightly smoothed
    const raw = new Array(count);
    for (let i = 0; i < count; i++) {
      const a = S[(i - 1 + count) % count];
      const b = S[(i + 1) % count];
      raw[i] = -wrapAngle(b.heading - a.heading) / (2 * step);
    }
    for (let i = 0; i < count; i++) {
      let acc = 0;
      for (let k = -2; k <= 2; k++) acc += raw[(i + k + count) % count];
      S[i].curv = acc / 5;
    }
    this.samples = S;
  }

  uToIndex(u) {
    const S = this.samples;
    let best = 0;
    let bd = 1e9;
    const n = this.def.points.length;
    for (let i = 0; i < S.length; i++) {
      let d = Math.abs(S[i].u - u);
      d = Math.min(d, n - d);
      if (d < bd) {
        bd = d;
        best = i;
      }
    }
    return best;
  }

  _buildBranch() {
    const b = this.def.branch;
    if (!b) {
      this.branch = null;
      return;
    }
    const iA = this.uToIndex(b.from);
    const iB = this.uToIndex(b.to);
    const A = this.samples[iA];
    const B = this.samples[iB];
    const len = Math.hypot(B.x - A.x, B.z - A.z);
    const count = Math.round(len / this.step);
    const step = len / count;
    const tx = (B.x - A.x) / len;
    const tz = (B.z - A.z) / len;
    const samples = [];
    for (let i = 0; i <= count; i++) {
      const f = i / count;
      samples.push({ i, s: i * step, x: lerp(A.x, B.x, f), y: lerp(A.y, B.y, f), z: lerp(A.z, B.z, f) });
    }
    const gapLen = BALANCE.track.bridge.gapLength;
    const gapMid = len * b.gapCenter;
    this.branch = {
      iA,
      iB,
      sA: A.s,
      sB: B.s,
      ax: A.x,
      az: A.z,
      ay: A.y,
      by: B.y,
      tx,
      tz,
      rx: -tz,
      rz: tx,
      heading: Math.atan2(tx, tz),
      length: len,
      step,
      samples,
      hw: b.hw,
      gap0: gapMid - gapLen / 2,
      gap1: gapMid + gapLen / 2,
      mainLength: B.s - A.s,
    };
  }

  _buildGates() {
    this.gates = this.def.gates.map((u) => {
      const i = this.uToIndex(u);
      return { i, s: this.samples[i].s };
    });
    this.gates[0] = { i: 0, s: 0 };
  }

  _buildTeacups() {
    this.teacups = (this.def.teacups || []).map((c) => {
      const i = this.uToIndex(c.u);
      return { ...c, i, s: this.samples[i].s };
    });
  }

  // ── queries ────────────────────────────────────────────────────────────────

  /** Project a point onto the main loop. `hint` is the last known sample index. */
  projectMain(x, z, hint, out) {
    const S = this.samples;
    const n = this.n;
    let best = -1;
    let bd = Infinity;
    if (hint >= 0) {
      for (let k = -12; k <= 12; k++) {
        const i = (hint + k + n) % n;
        const dx = x - S[i].x;
        const dz = z - S[i].z;
        const d2 = dx * dx + dz * dz;
        if (d2 < bd) {
          bd = d2;
          best = i;
        }
      }
    }
    if (best < 0 || bd > 26 * 26) {
      for (let i = 0; i < n; i++) {
        const dx = x - S[i].x;
        const dz = z - S[i].z;
        const d2 = dx * dx + dz * dz;
        if (d2 < bd) {
          bd = d2;
          best = i;
        }
      }
    }
    const a = S[best];
    const dx = x - a.x;
    const dz = z - a.z;
    const along = dx * a.tx + dz * a.tz;
    const nb = S[(best + (along >= 0 ? 1 : n - 1)) % n];
    const f = Math.min(1, Math.abs(along) / this.step);
    out.i = best;
    out.d = dx * a.rx + dz * a.rz;
    out.along = along;
    let s = a.s + along;
    if (s < 0) s += this.length;
    else if (s >= this.length) s -= this.length;
    out.s = s;
    out.hw = lerp(a.hw, nb.hw, f);
    out.y = lerp(a.y, nb.y, f);
    out.wall = a.wall;
    out.dist2 = bd;
    return out;
  }

  /** Project onto the shortcut span. out.valid is false when outside its length. */
  projectBranch(x, z, out) {
    const b = this.branch;
    if (!b) {
      out.valid = false;
      return out;
    }
    const dx = x - b.ax;
    const dz = z - b.az;
    const s = dx * b.tx + dz * b.tz;
    out.s = s;
    out.d = dx * b.rx + dz * b.rz;
    out.valid = s >= 0 && s <= b.length;
    out.y = lerp(b.ay, b.by, s / b.length);
    out.inGap = s > b.gap0 && s < b.gap1;
    return out;
  }

  sampleAt(s) {
    const n = this.n;
    let i = Math.floor(s / this.step) % n;
    if (i < 0) i += n;
    return this.samples[i];
  }

  /** World position on the main loop at arc length s with a lateral offset. */
  pointAt(s, lat, out) {
    const L = this.length;
    s = ((s % L) + L) % L;
    const fi = s / this.step;
    const i0 = Math.floor(fi) % this.n;
    const i1 = (i0 + 1) % this.n;
    const f = fi - Math.floor(fi);
    const a = this.samples[i0];
    const b = this.samples[i1];
    out.x = lerp(a.x, b.x, f) + a.rx * lat;
    out.z = lerp(a.z, b.z, f) + a.rz * lat;
    out.y = lerp(a.y, b.y, f);
    out.heading = a.heading;
    out.hw = lerp(a.hw, b.hw, f);
    return out;
  }

  branchPointAt(sb, lat, out) {
    const b = this.branch;
    out.x = b.ax + b.tx * sb + b.rx * lat;
    out.z = b.az + b.tz * sb + b.rz * lat;
    out.y = lerp(b.ay, b.by, sb / b.length);
    out.heading = b.heading;
    out.hw = b.hw;
    return out;
  }

  /** Shortcut span state at race time t (deterministic cycle). */
  bridgeState(t, out = {}) {
    const c = BALANCE.track.bridge;
    const ph = ((t % c.period) + c.period) % c.period;
    out.phase = ph;
    out.solid = ph < c.solidTime;
    out.warn = out.solid && ph > c.solidTime - c.warnTime;
    out.timeToChange = out.solid ? c.solidTime - ph : c.period - ph;
    return out;
  }

  /** Will the span be solid for the whole interval [t0, t1]? */
  bridgeSolidDuring(t0, t1) {
    const c = BALANCE.track.bridge;
    const ph = ((t0 % c.period) + c.period) % c.period;
    return ph < c.solidTime && ph + (t1 - t0) < c.solidTime;
  }

  teacupLateral(cup, t) {
    return cup.amp * Math.sin((t / cup.period) * Math.PI * 2 + cup.phase);
  }

  teacupPos(cup, t, out) {
    const a = this.samples[cup.i];
    const lat = this.teacupLateral(cup, t);
    out.x = a.x + a.rx * lat;
    out.z = a.z + a.rz * lat;
    out.y = a.y;
    out.lat = lat;
    return out;
  }
}
